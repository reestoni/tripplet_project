# db/label_sheets.py
"""Label sheets as PDF (PyMuPDF) - Qt-free, shared by the desktop label
printing (ui/widgets/label_printing.py re-exports everything) and the web
app. Moved out of ui/widgets/label_printing.py on 2026-11-13 without
behaviour change; label_sheet_pdf_bytes() is new (same layout, bytes
instead of a file).

Templates are told apart by `Name` in tblLabelTemplate ('Default' for spools,
'TrialLabel' for trial numbers, ...) - different sheet formats.

Lessons (see the comments in the code):
- QR modules ALWAYS batched in one page.new_shape(), never one draw_rect()
  per module (minutes instead of milliseconds otherwise).
- Text is ALWAYS scaled to the available cell height, never fixed mm offsets.
- Too many items for one sheet: further pages are added, nothing is cut off.
"""
from typing import Callable, Dict, List

from db.connection import execute, fetch_all, table_exists

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None
try:
    import qrcode
except Exception:
    qrcode = None

MM = 72.0 / 25.4  # PDF-Punkte pro mm

LABEL_TEMPLATE_TABLE = "tblLabelTemplate"

TEMPLATE_FIELDS = [
    ("PageWidthMm", "Page width (mm)"), ("PageHeightMm", "Page height (mm)"),
    ("ColumnCount", "Columns"), ("RowCount", "Rows"),
    ("LabelWidthMm", "Label width (mm)"), ("LabelHeightMm", "Label height (mm)"),
    ("MarginTopMm", "Top margin (mm)"), ("MarginLeftMm", "Left margin (mm)"),
    ("HGapMm", "Horizontal gap (mm)"), ("VGapMm", "Vertical gap (mm)"),
]

DEFAULT_TEMPLATE = {
    "PageWidthMm": 210.0, "PageHeightMm": 297.0,
    "ColumnCount": 3, "RowCount": 8,
    "LabelWidthMm": 63.5, "LabelHeightMm": 33.9,
    "MarginTopMm": 13.0, "MarginLeftMm": 7.0,
    "HGapMm": 2.5, "VGapMm": 0.0,
}


def load_label_template(template_name: str = "Default") -> Dict:
    """Laedt das benannte Template. Existiert es nicht, werden Default-Werte
    zurueckgegeben (noch nicht gespeichert - erst bei save_label_template)."""
    if table_exists(LABEL_TEMPLATE_TABLE):
        rows = fetch_all(
            f"SELECT * FROM {LABEL_TEMPLATE_TABLE} WHERE [Name] = ? ORDER BY [ID] LIMIT 1",
            [template_name])
        if rows:
            return rows[0]
    return dict(DEFAULT_TEMPLATE, Name=template_name)


def save_label_template(template_name: str, values: Dict) -> None:
    """Speichert (Insert oder Update) das benannte Template."""
    if not table_exists(LABEL_TEMPLATE_TABLE):
        return
    existing = fetch_all(
        f"SELECT [ID] FROM {LABEL_TEMPLATE_TABLE} WHERE [Name] = ? LIMIT 1", [template_name])
    cols = [k for k, _ in TEMPLATE_FIELDS]
    if existing:
        sets = ", ".join(f"[{k}] = ?" for k in cols)
        execute(f"UPDATE {LABEL_TEMPLATE_TABLE} SET {sets} WHERE [ID] = ?",
                [values[k] for k in cols] + [existing[0]["ID"]])
    else:
        all_cols = ["Name"] + cols
        ph = ", ".join(["?"] * len(all_cols))
        execute(f"INSERT INTO {LABEL_TEMPLATE_TABLE} ({', '.join(f'[{c}]' for c in all_cols)}) "
                f"VALUES ({ph})",
                [template_name] + [values[k] for k in cols])


def fit_text(text: str, fontsize: float, max_width_mm: float, fontname: str = "helv") -> str:
    """Kuerzt `text` mit '…', falls er bei `fontsize` breiter als
    `max_width_mm` waere."""
    if fitz is None or not text:
        return text
    max_width_pt = max_width_mm * MM
    if fitz.get_text_length(text, fontname=fontname, fontsize=fontsize) <= max_width_pt:
        return text
    ell = "…"
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        candidate = text[:mid].rstrip() + ell
        if fitz.get_text_length(candidate, fontname=fontname, fontsize=fontsize) <= max_width_pt:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo].rstrip() + ell if lo > 0 else ell


def wrap_text_lines(text: str, fontsize: float, max_width_mm: float, max_lines: int = 2,
                     fontname: str = "helv") -> List[str]:
    """Bricht `text` auf bis zu `max_lines` Zeilen um (an Wortgrenzen)."""
    if fitz is None or not text:
        return [text] if text else []
    max_width_pt = max_width_mm * MM
    if fitz.get_text_length(text, fontname=fontname, fontsize=fontsize) <= max_width_pt:
        return [text]
    words = text.split(" ")
    lines: List[str] = []
    current = ""
    i = 0
    while i < len(words) and len(lines) < max_lines - 1:
        candidate = (current + " " + words[i]).strip()
        if fitz.get_text_length(candidate, fontname=fontname, fontsize=fontsize) <= max_width_pt:
            current = candidate
            i += 1
        elif current:
            lines.append(current)
            current = ""
        else:
            current = fit_text(words[i], fontsize, max_width_mm, fontname)
            i += 1
            lines.append(current)
            current = ""
    remainder = (current + " " + " ".join(words[i:])).strip()
    if remainder:
        lines.append(fit_text(remainder, fontsize, max_width_mm, fontname))
    return lines[:max_lines] if lines else [text]


def draw_qr(page, x_mm: float, y_mm: float, size_mm: float, text: str) -> None:
    """Zeichnet einen QR-Code als gefuellte Rechtecke, gebatcht in EINEM
    page.new_shape() (siehe Modul-Docstring - Performance-kritisch)."""
    from qrcode.constants import ERROR_CORRECT_L
    qr = qrcode.QRCode(border=0, box_size=1, error_correction=ERROR_CORRECT_L)
    qr.add_data(text)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    n = len(matrix)
    if n == 0:
        return
    cell = size_mm / n
    shape = page.new_shape()
    # Winziger Overlap (0.15pt) zwischen benachbarten Modulen, damit bei der
    # Rasterung/beim Druck keine Haarlinien-Luecken durch Rundungsfehler
    # entstehen - unsichtbar klein im Verhaeltnis zur Modulgroesse.
    overlap = 0.15
    for r, row in enumerate(matrix):
        for c, val in enumerate(row):
            if not val:
                continue
            x0 = (x_mm + c * cell) * MM
            y0 = (y_mm + r * cell) * MM
            rect = fitz.Rect(x0 - overlap, y0 - overlap, x0 + cell * MM + overlap, y0 + cell * MM + overlap)
            shape.draw_rect(rect)
    # width=0: kein Konturstrich - sonst bekommt jedes der u.U. hunderten
    # Module zusaetzlich eine Standard-Umrandung, was beim Druck koernig/
    # unsauber statt als glatte, klare Flaechen aussieht.
    shape.finish(color=(0, 0, 0), fill=(0, 0, 0), width=0)
    shape.commit()


def _layout_label_sheet(items: List[Dict], template: Dict, start_index: int,
                        draw_cell: Callable[..., None]):
    """Places `items` row by row from `start_index` (0-based) on one or more
    sheets and calls `draw_cell(page, x0_mm, y0_mm, label_w_mm, label_h_mm,
    item)` per cell. Returns (fitz document, placed)."""
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed.")

    cols = int(template["ColumnCount"])
    rows = int(template["RowCount"])
    per_page = max(1, cols * rows)
    doc = fitz.open()

    placed = 0
    current_page_num = -1
    page = None
    for i, item in enumerate(items):
        absolute_slot = start_index + i
        page_num = absolute_slot // per_page
        slot_on_page = absolute_slot % per_page
        if page_num != current_page_num:
            page = doc.new_page(width=template["PageWidthMm"] * MM, height=template["PageHeightMm"] * MM)
            current_page_num = page_num

        col = slot_on_page % cols
        row = slot_on_page // cols
        x0 = template["MarginLeftMm"] + col * (template["LabelWidthMm"] + template["HGapMm"])
        y0 = template["MarginTopMm"] + row * (template["LabelHeightMm"] + template["VGapMm"])
        draw_cell(page, x0, y0, template["LabelWidthMm"], template["LabelHeightMm"], item)
        placed += 1
    return doc, placed


def generate_label_sheet_pdf(items: List[Dict], template: Dict, start_index: int,
                              out_path: str,
                              draw_cell: Callable[..., None]) -> int:
    """Generischer Bogen-Layouter: platziert `items` zeilenweise ab
    `start_index` (0-basiert) auf einem/mehreren Boegen und ruft fuer jede
    Zelle `draw_cell(page, x0_mm, y0_mm, label_w_mm, label_h_mm, item)` auf.

    Passen nicht alle Items auf einen Bogen, werden automatisch weitere
    Seiten angehaengt (jeweils ab Zelle 0) - kein stilles Abschneiden mehr.
    Gibt zurueck, wie viele Items platziert wurden (immer len(items), da nie
    abgebrochen wird).
    """
    doc, placed = _layout_label_sheet(items, template, start_index, draw_cell)
    doc.save(out_path)
    doc.close()
    return placed


def label_sheet_pdf_bytes(items: List[Dict], template: Dict, start_index: int,
                          draw_cell: Callable[..., None]) -> bytes:
    """Same sheet as generate_label_sheet_pdf(), as PDF bytes (web download)."""
    doc, _placed = _layout_label_sheet(items, template, start_index, draw_cell)
    try:
        return doc.tobytes()
    finally:
        doc.close()
