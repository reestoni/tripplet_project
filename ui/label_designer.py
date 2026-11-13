"""label_designer.py - Label Generator (ui/screen_label_generator.py), the part without Qt (2026-11-13, for the
web version; the desktop screen uses it).

Element schema (text with parts static / field / counter, logo, table), the saved designs (tblLabelDesign),
rendering an element list onto a PDF page (make_draw_cell - the same code for the preview and the sheet PDF),
the preview as PNG, the trial data of a series (ui/label_generator_fields.py) and the label list for a PDF.
The sheet geometry lives in tblLabelTemplate (db/label_sheets.py) under TEMPLATE_NAME.
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

import fitz  # PyMuPDF

from db.connection import execute, fetch_all, get_connection, table_exists
from db.label_sheets import MM, fit_text
from ui.label_generator_fields import (
    FIELD_REGISTRY, build_fields, build_machine_fields, list_trials_for_series, machine_field_registry,
    machine_id_for_series, series_header, trial_ids_by_number,
)

TEMPLATE_NAME = "CustomLabel"
DESIGN_TABLE = "tblLabelDesign"
LOGO_ASSET = "assets/images/heb_logo.png"
PX_PER_MM = 8.0
ENSURE_TABLE = True       # the web sets False: never creates tblLabelDesign


def _normalize_element(el: Dict) -> Dict:
    """Wandelt ein Element im alten Einzel-Quelle-Format (source/static_text/
    field_key auf oberster Ebene) in das neue parts-Format um. Logo-Elemente
    und bereits parts-basierte Elemente bleiben unveraendert - macht
    fruehere Designs in tblLabelDesign weiterhin ladbar."""
    el = dict(el)
    if el.get("type") == "text" and "parts" not in el:
        if el.get("source") == "field":
            el["parts"] = [{"source": "field", "field_key": el.get("field_key")}]
        else:
            el["parts"] = [{"source": "static", "text": el.get("static_text", "")}]
        el.pop("source", None)
        el.pop("static_text", None)
        el.pop("field_key", None)
    return el


# ---------------------------------------------------------------------------
# DB-Helfer fuer tblLabelDesign (auto-erstellt, analog zu anderen Tools -
# siehe z.B. ui/screen_air_supply.py::_ensure_tables)
# ---------------------------------------------------------------------------

def _ensure_design_table() -> None:
    if not ENSURE_TABLE:
        return
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {DESIGN_TABLE} (
                    ID           INT AUTO_INCREMENT PRIMARY KEY,
                    Name         VARCHAR(120) NOT NULL UNIQUE,
                    TemplateName VARCHAR(120) NOT NULL,
                    ElementsJson LONGTEXT NOT NULL,
                    UpdatedAt    DATETIME DEFAULT CURRENT_TIMESTAMP
                                 ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
    except Exception as e:
        print(f"[LabelGenerator] Could not ensure {DESIGN_TABLE}: {e}")


def _db_list_designs() -> List[str]:
    if not table_exists(DESIGN_TABLE):
        return []
    try:
        rows = fetch_all(f"SELECT [Name] FROM {DESIGN_TABLE} ORDER BY [Name]")
        return [r["Name"] for r in rows]
    except Exception:
        return []


def _db_load_design(name: str) -> Optional[List[Dict]]:
    if not table_exists(DESIGN_TABLE):
        return None
    try:
        rows = fetch_all(
            f"SELECT [ElementsJson] FROM {DESIGN_TABLE} WHERE [Name] = ? LIMIT 1", [name])
        if not rows:
            return None
        return json.loads(rows[0]["ElementsJson"])
    except Exception:
        return None


def _db_save_design(name: str, elements: List[Dict]) -> None:
    _ensure_design_table()
    ejson = json.dumps(elements)
    existing = fetch_all(f"SELECT [ID] FROM {DESIGN_TABLE} WHERE [Name] = ? LIMIT 1", [name])
    if existing:
        execute(
            f"UPDATE {DESIGN_TABLE} SET [TemplateName] = ?, [ElementsJson] = ? WHERE [ID] = ?",
            [TEMPLATE_NAME, ejson, existing[0]["ID"]])
    else:
        execute(
            f"INSERT INTO {DESIGN_TABLE} ([Name], [TemplateName], [ElementsJson]) "
            f"VALUES (?, ?, ?)", [name, TEMPLATE_NAME, ejson])


# ---------------------------------------------------------------------------
# Rendering: Element-Liste -> draw_cell-Funktion (fuer PrintLabelsDialog /
# generate_label_sheet_pdf UND fuer die Live-Vorschau - derselbe Code, damit
# Vorschau und PDF nie auseinanderlaufen koennen).
# ---------------------------------------------------------------------------

def _resolve_text(parts: List[Dict], item: Optional[Dict]) -> str:
    out = []
    for p in parts:
        source = p.get("source")
        if source == "field":
            out.append(str((item or {}).get(p.get("field_key") or "", "") or ""))
        elif source == "counter":
            index = int((item or {}).get("__label_index__") or 0)
            start = int(p.get("start") if p.get("start") is not None else 1)
            step = int(p.get("step") if p.get("step") is not None else 1)
            digits = int(p.get("digits") or 0)
            value = start + index * step
            out.append(str(value).zfill(digits) if digits > 0 else str(value))
        else:
            out.append(str(p.get("text") or ""))
    return "".join(out)


def _draw_text_in_box(page, text: str, x_mm: float, y_mm: float, w_mm: float, h_mm: float,
                       fontsize: float, fontname: str, align: str) -> None:
    """Schreibt `text` vertikal zentriert / horizontal ausgerichtet in die Box
    (x_mm,y_mm,w_mm,h_mm) - gemeinsame Text-Platzierung fuer normale
    Text-Elemente UND Tabellenzellen (siehe make_draw_cell)."""
    if not text:
        return
    text = fit_text(text, fontsize, w_mm, fontname=fontname)
    tw_mm = fitz.get_text_length(text, fontname=fontname, fontsize=fontsize) / MM
    if align == "center":
        tx = x_mm + max(0.0, (w_mm - tw_mm) / 2)
    elif align == "right":
        tx = x_mm + max(0.0, w_mm - tw_mm)
    else:
        tx = x_mm
    ty = y_mm + h_mm / 2 + fontsize * 0.35 / MM
    try:
        page.insert_text(
            fitz.Point(tx * MM, ty * MM), text,
            fontsize=fontsize, fontname=fontname, color=(0, 0, 0))
    except Exception:
        pass


def _draw_table(page, el: Dict, ex: float, ey: float, ew: float, eh: float, item: Dict) -> None:
    """Gleichmaessiges Raster (rows x cols, jede Zelle ew/cols x eh/rows breit/hoch)
    - keine individuellen Spalten-/Zeilenbreiten. Gitterlinien optional
    (el['show_borders']), Zellinhalt wie ein normales Text-Element ueber
    'parts' (static/field/counter), ausgewertet mit _resolve_text()."""
    rows = max(1, int(el.get("rows") or 1))
    cols = max(1, int(el.get("cols") or 1))
    row_h = eh / rows
    col_w = ew / cols
    fontsize = float(el.get("font_size") or 9.0)
    fontname = "hebo" if el.get("bold") else "helv"
    align = el.get("align") or "left"

    if el.get("show_borders", True):
        try:
            shape = page.new_shape()
            for r in range(rows + 1):
                y = (ey + r * row_h) * MM
                shape.draw_line(fitz.Point(ex * MM, y), fitz.Point((ex + ew) * MM, y))
            for c in range(cols + 1):
                x = (ex + c * col_w) * MM
                shape.draw_line(fitz.Point(x, ey * MM), fitz.Point(x, (ey + eh) * MM))
            shape.finish(color=(0, 0, 0), width=0.5)
            shape.commit()
        except Exception:
            pass

    cells = el.get("cells") or []
    for r in range(rows):
        row_cells = cells[r] if r < len(cells) else []
        for c in range(cols):
            cell = row_cells[c] if c < len(row_cells) else {}
            text = _resolve_text(cell.get("parts") or [], item)
            _draw_text_in_box(
                page, text, ex + c * col_w, ey + r * row_h, col_w, row_h,
                fontsize, fontname, align)


def make_draw_cell(elements: List[Dict]) -> Callable:
    from ui.pathutil import resource_path
    logo_path = resource_path(LOGO_ASSET)
    logo_available = os.path.isfile(logo_path)

    def draw_cell(page, x0_mm: float, y0_mm: float, w_mm: float, h_mm: float, item: Dict) -> None:
        for el in elements:
            ex = x0_mm + float(el.get("x_mm") or 0.0)
            ey = y0_mm + float(el.get("y_mm") or 0.0)
            ew = float(el.get("w_mm") or 10.0)
            eh = float(el.get("h_mm") or 6.0)
            el_type = el.get("type")

            if el_type == "logo":
                if not logo_available:
                    continue
                rect = fitz.Rect(ex * MM, ey * MM, (ex + ew) * MM, (ey + eh) * MM)
                try:
                    page.insert_image(rect, filename=logo_path, keep_proportion=True)
                except Exception:
                    pass
                continue

            if el_type == "table":
                _draw_table(page, el, ex, ey, ew, eh, item)
                continue

            parts = el.get("parts")
            if parts is None:
                el = _normalize_element(el)
                parts = el.get("parts") or []
            text = _resolve_text(parts, item)
            fontsize = float(el.get("font_size") or 9.0)
            fontname = "hebo" if el.get("bold") else "helv"
            align = el.get("align") or "left"
            _draw_text_in_box(page, text, ex, ey, ew, eh, fontsize, fontname, align)

    return draw_cell


normalize_element = _normalize_element
list_designs = _db_list_designs
load_design = _db_load_design
save_design = _db_save_design
resolve_text = _resolve_text


def blank_table_cells(rows: int, cols: int) -> List[List[Dict]]:
    return [[{"parts": [{"source": "static", "text": ""}]} for _ in range(cols)] for _ in range(rows)]


def resize_table_cells(el: Dict) -> Dict:
    """Fit el["cells"] to el["rows"] x el["cols"] (content kept, new cells empty)."""
    rows = max(1, int(el.get("rows") or 1))
    cols = max(1, int(el.get("cols") or 1))
    old_cells = el.get("cells") or []
    new_cells = []
    for r in range(rows):
        old_row = old_cells[r] if r < len(old_cells) else []
        new_row = []
        for c in range(cols):
            cell = old_row[c] if c < len(old_row) else None
            if not cell or not cell.get("parts"):
                cell = {"parts": [{"source": "static", "text": ""}]}
            new_row.append(cell)
        new_cells.append(new_row)
    el["rows"], el["cols"], el["cells"] = rows, cols, new_cells
    return el


def new_element(kind: str, n: int = 0, data: Optional[Dict] = None) -> Dict:
    """A new element with the desktop defaults (n = how many there are already, for the offset)."""
    d = _normalize_element(dict(data or {"type": kind}))
    d.setdefault("type", kind)
    d.setdefault("x_mm", 2.0 + (n % 5) * 3.0)
    d.setdefault("y_mm", 2.0 + (n % 5) * 3.0)
    if d["type"] == "table":
        d.setdefault("w_mm", 40.0)
        d.setdefault("h_mm", 20.0)
        d.setdefault("rows", 2)
        d.setdefault("cols", 2)
        d.setdefault("show_borders", True)
        d.setdefault("cells", blank_table_cells(int(d["rows"]), int(d["cols"])))
    else:
        d.setdefault("w_mm", 15.0 if d["type"] == "logo" else 30.0)
        d.setdefault("h_mm", 10.0 if d["type"] == "logo" else 8.0)
    if d["type"] == "text":
        d.setdefault("parts", [{"source": "static", "text": ""}])
    return d


def caption_text(el: Dict) -> str:
    """Short caption of an element (canvas / anchor list)."""
    el_type = el.get("type")
    if el_type == "logo":
        return "Logo"
    if el_type == "table":
        return f"Table {int(el.get('rows') or 1)}×{int(el.get('cols') or 1)}"
    bits = []
    for p in el.get("parts") or []:
        source = p.get("source")
        if source == "field":
            bits.append(f"{{{p.get('field_key')}}}")
        elif source == "counter":
            bits.append(f"{{#{p.get('start', 1)}}}")
        else:
            bits.append(p.get("text") or "")
    return "".join(bits)[:24] or "Text"


def new_anchor_group() -> str:
    return uuid.uuid4().hex[:8]


def preview_png(elements: List[Dict], w_mm: float, h_mm: float, item: Dict, px_per_mm: float = PX_PER_MM) -> bytes:
    """One label rendered like the PDF (same make_draw_cell), as PNG."""
    doc = fitz.open()
    try:
        page = doc.new_page(width=w_mm * MM, height=h_mm * MM)
        make_draw_cell(elements)(page, 0.0, 0.0, w_mm, h_mm, item)
        zoom = (px_per_mm * 25.4) / 72.0
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csRGB, alpha=False)
        return pix.tobytes("png")
    finally:
        doc.close()


def series_context(series_id: int) -> Dict[str, Any]:
    """The trial series for the labels: header, trial numbers, trial ids, machine and the fields it offers."""
    header = series_header(series_id)
    trials = list_trials_for_series(series_id) if header else []
    machine_id = machine_id_for_series(series_id) if header else None
    fields = dict(FIELD_REGISTRY)
    fields.update(machine_field_registry(machine_id))
    return {"header": header, "trials": trials, "trial_ids": trial_ids_by_number(series_id) if header else {},
            "machine_id": machine_id, "fields": fields}


def trial_values(ctx: Dict[str, Any], trial_nr: int) -> Dict[str, str]:
    """Field values of one trial (static fields + the trial-wide Machine Data fields)."""
    h = ctx["header"]
    values = build_fields(h["experiment_id"], h["series_name"], trial_nr)
    trial_id = ctx["trial_ids"].get(trial_nr)
    if trial_id is not None:
        values.update(build_machine_fields(trial_id, ctx["machine_id"]))
    return values


def preview_item(loaded: Optional[Dict], fields: Dict[str, str]) -> Dict:
    """What the preview shows: the loaded trial, else <field name> placeholders."""
    item = dict(loaded) if loaded else {k: f"<{v}>" for k, v in fields.items()}
    item.setdefault("__label_index__", 0)
    return item


def uses_fields(elements: List[Dict]) -> bool:
    return any(p.get("source") == "field" for el in elements if el.get("type") == "text" for p in (el.get("parts") or []))


def build_items(elements: List[Dict], mode: str, copies: int, ctx: Optional[Dict], loaded: Optional[Dict],
                frm: int = 0, to: int = 0) -> Tuple[List[Dict], Optional[str]]:
    """The labels of a PDF: mode "copies" (the loaded trial x N) or "range" (one per trial from-to).
    Returns (items, None) or ([], code): no_elements, no_series, empty_range, need_trial."""
    if not elements:
        return [], "no_elements"
    if mode == "range":
        if not ctx or not ctx.get("header") or not ctx.get("trials"):
            return [], "no_series"
        f, t = (frm, to) if frm <= to else (to, frm)
        nrs = [n for n in ctx["trials"] if f <= n <= t]
        if not nrs:
            return [], "empty_range"
        items = []
        for i, nr in enumerate(nrs):
            it = trial_values(ctx, nr)
            it["__label_index__"] = i
            items.append(it)
        return items, None
    if uses_fields(elements) and not loaded:
        return [], "need_trial"
    return [{**dict(loaded or {}), "__label_index__": i} for i in range(max(1, min(500, int(copies or 1))))], None
