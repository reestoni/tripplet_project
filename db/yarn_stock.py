# db/yarn_stock.py
"""Yarn Stock - Qt-free, shared by the desktop (ui/screen_yarn_stock.py) and the web app.

Moved out of the screen on 2026-11-13 without behaviour change (same SQL, same rules, same change
log in tblYarnSpoolLog); the screen keeps its widgets, dialogs and file pickers.

    can_write(user)                 AccessLevel >= 2 (check in / out / adjust)
    load_stock()                    yarns, producers, all spools, overview (yarn x batch) + status per yarn
    rack_groups(stock, prefix)      in-stock spools of a rack ("C") grouped by yarn / batch
    parse_spool_input(text)         "213", "#213" or a scanned label QR -> spool id
    used_in(spool_ids)              trials that used the spools (tbltrialsettings.SpoolID)
    history(spool_ids), describe_history(row)
    create_producer(name), new_spools(values, user_id), discard_spools(ids)
    save_spool_changes(changes, rows_by_id, producer_map)   weight / location / tube colour / producer
    update_group_batch(...), update_group_producer(...), set_min_stock(yarn_id, value)
    label queue: queue_items(names), queue_labels(ids, user_id), remove_from_queue(ids), mark_printed(ids)
    labels_pdf(items, template, start_index)  bytes; draw_yarn_label_cell
    overview_xlsx(rows) / rack_xlsx(rows, prefix)   bytes
    refresh_notifications(stock)    low / empty stock bell messages per yarn
"""
from __future__ import annotations

import io
import re
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from db import yarn_spool_log
from db.connection import execute, execute_insert, fetch_all, get_columns_map, new_global_id, table_exists

YARN_TABLE = "tblYarn"
SPOOL_TABLE = "tblYarnSpool"
LABEL_QUEUE_TABLE = "tblYarnLabelQueue"
PRODUCER_TABLE = "tblYarnProducer"
STATUS_COLOR = {"Empty": "#FCEBEB", "Low": "#FAEEDA", "OK": "#EAF3DE"}
OV_HEADERS = ["Yarn", "Batch", "Producer", "Spools", "Total (kg)", "Yarn total (kg)", "Min. stock (kg)",
              "Status", "Locations"]
RACK_HEADERS = ["Yarn", "Batch", "Producer", "Spools", "Total (kg)", "Locations"]


# ---------------------------------------------------------------- rights / small helpers
def can_write(user: Optional[dict] = None) -> bool:
    if user is None:
        import app_meta
        try:
            return int(app_meta.access_level() or 0) >= 2
        except Exception:
            return False
    try:
        return int((user or {}).get("access_level") or 0) >= 2
    except Exception:
        return False


def _resolve_field(cands: List[str], cmap: Dict[str, str]) -> Optional[str]:
    for c in cands:
        key = c.strip().lower().replace(" ", "")
        if key in cmap:
            return cmap[key]
    return None


# Spool number at the end of the QR content ("...;S:213"); tolerant separator because hand scanners
# send with a US layout and ":" arrives differently on CH/DE keyboards ("SÖ213").
_QR_SPOOL_RE = re.compile(r"[sS][^0-9A-Za-z]{1,3}#?(\d+)\s*$")


def parse_spool_input(text: str) -> Optional[int]:
    """Spool id from "213", "#213" or a full label QR ("Y:...;B:...;L:...;S:213"); None otherwise."""
    raw = (text or "").strip()
    plain = raw.lstrip("#").strip()
    if plain.isascii() and plain.isdigit():
        return int(plain)
    m = _QR_SPOOL_RE.search(raw)
    return int(m.group(1)) if m else None


def qr_content(item: Dict) -> str:
    """Compact QR content (upper case, short keys); weight deliberately not included."""
    yarn = str(item.get("Yarn") or "").upper()
    batch = str(item.get("Batch") or "").upper()
    loc = str(item.get("Location") or "").upper()
    return f"Y:{yarn};B:{batch};L:{loc};S:{item['SpoolID']}"


# ---------------------------------------------------------------- loading
def producers() -> List[Tuple[int, str]]:
    if not table_exists(PRODUCER_TABLE):
        return []
    try:
        return [(int(r["ID"]), str(r.get("Name") or "")) for r in fetch_all(f"SELECT ID, Name FROM {PRODUCER_TABLE} ORDER BY Name")]
    except Exception:
        return []


def load_stock() -> Optional[Dict[str, Any]]:
    """Everything the screen shows. None if tblYarn / tblYarnSpool are missing.

    Status is per YARN (sum over all batches; user decision 2026-10-13): Empty (0 kg), Low (< MinStock), OK.
    Batches without a spool in stock are not shown in the overview."""
    if not table_exists(YARN_TABLE) or not table_exists(SPOOL_TABLE):
        return None
    cmap = get_columns_map(YARN_TABLE)
    id_col = _resolve_field(["ID"], cmap) or "ID"
    name_col = _resolve_field(["Name", "Bezeichnung", "YarnName", "Material"], cmap)
    minstock_col = _resolve_field(["MinStock"], cmap)
    src_col = _resolve_field(["SourceTrialID"], cmap)
    if not name_col:
        return None
    where = f" WHERE [{src_col}] IS NULL" if src_col else ""     # shadow yarns are no real stock
    yrows = fetch_all(
        f"SELECT [{id_col}] AS YarnID, [{name_col}] AS YarnName"
        + (f", [{minstock_col}] AS MinStock" if minstock_col else "")
        + f" FROM {YARN_TABLE}{where} ORDER BY [{name_col}]")
    yarn_names: Dict[int, str] = {}
    minstock: Dict[int, float] = {}
    choices: List[Tuple[int, str]] = []
    for r in yrows:
        yid = int(r["YarnID"])
        yname = str(r.get("YarnName") or f"Yarn {yid}")
        yarn_names[yid] = yname
        choices.append((yid, yname))
        if r.get("MinStock") is not None:
            try:
                minstock[yid] = float(r["MinStock"])
            except Exception:
                pass
    prod = producers()
    pmap = dict(prod)

    spool_cmap = get_columns_map(SPOOL_TABLE)
    extra = ""
    if "colour" in spool_cmap:
        extra += ", [Colour]"
    if "producerid" in spool_cmap:
        extra += ", [ProducerID]"
    spools = fetch_all(f"SELECT [ID], [YarnID], [Charge], [WeightKg], [Status], [Location], "
                       f"[ReceivedDate], [DiscardedDate]{extra} FROM {SPOOL_TABLE}")

    groups: Dict[Tuple[int, str], List[Dict]] = {}
    for s in spools:
        if s.get("YarnID") is None:
            continue
        groups.setdefault((int(s["YarnID"]), s.get("Charge") or ""), []).append(s)

    yarn_total: Dict[int, float] = {}
    for (yid, _c), sp in groups.items():
        yarn_total[yid] = yarn_total.get(yid, 0.0) + sum(float(s.get("WeightKg") or 0) for s in sp
                                                          if s.get("Status") == "in stock")
    yarn_status: Dict[int, str] = {}
    for yid, kg in yarn_total.items():
        ms = minstock.get(yid)
        yarn_status[yid] = "Empty" if kg <= 0 else ("Low" if ms is not None and kg < ms else "OK")

    overview = []
    for (yid, charge), sp in sorted(groups.items(), key=lambda kv: (yarn_names.get(kv[0][0], ""), kv[0][1])):
        active = [s for s in sp if s.get("Status") == "in stock"]
        if not active:
            continue
        locs = sorted({(s.get("Location") or "").strip() for s in active if s.get("Location")})
        pids = sorted({int(s["ProducerID"]) for s in active if s.get("ProducerID")})
        status = yarn_status[yid]
        overview.append({
            "YarnID": yid, "Charge": charge, "YarnName": yarn_names.get(yid, f"Yarn {yid}"),
            "Count": len(active), "TotalKg": sum(float(s.get("WeightKg") or 0) for s in active),
            "YarnTotalKg": yarn_total[yid], "MinStock": minstock.get(yid),
            "Locations": " / ".join(locs) if locs else "–",
            "Producers": " / ".join(pmap.get(p, f"#{p}") for p in pids) if pids else "–",
            "ProducerIDs": set(pids), "Status": status, "Color": STATUS_COLOR[status],
        })
    return {"yarn_choices": choices, "yarn_names": yarn_names, "minstock": minstock,
            "minstock_col": minstock_col, "id_col": id_col, "producers": prod, "producer_map": pmap,
            "spools": spools, "overview": overview, "yarn_status": yarn_status, "yarn_total": yarn_total}


def group_spools(stock: Dict[str, Any], yarn_id: int, charge: str, in_stock_only: bool = True) -> List[Dict]:
    out = [s for s in stock["spools"] if int(s.get("YarnID") or -1) == int(yarn_id)
           and (s.get("Charge") or "") == (charge or "") and (not in_stock_only or s.get("Status") == "in stock")]
    return sorted(out, key=lambda s: s.get("ID"))


def rack_groups(stock: Dict[str, Any], prefix: str) -> List[Dict]:
    """In-stock spools whose location starts with ``prefix`` (case-insensitive), by yarn / batch."""
    prefix = (prefix or "").strip().upper()
    if not prefix:
        return []
    names, pmap = stock["yarn_names"], stock["producer_map"]
    groups: Dict[Tuple[int, str], Dict] = {}
    for s in stock["spools"]:
        if s.get("Status") != "in stock" or s.get("YarnID") is None:
            continue
        if not (s.get("Location") or "").strip().upper().startswith(prefix):
            continue
        yid = int(s["YarnID"])
        g = groups.setdefault((yid, s.get("Charge") or ""), {
            "YarnID": yid, "Yarn": names.get(yid, f"Yarn {yid}"), "Batch": s.get("Charge") or "",
            "Count": 0, "Weight": 0.0, "Locations": set(), "ProducerIDs": set()})
        g["Count"] += 1
        g["Weight"] += float(s.get("WeightKg") or 0)
        if s.get("Location"):
            g["Locations"].add(s["Location"].strip())
        if s.get("ProducerID"):
            g["ProducerIDs"].add(int(s["ProducerID"]))
    for g in groups.values():
        g["LocationsDisp"] = " / ".join(sorted(g["Locations"]))
        g["ProducersDisp"] = " / ".join(pmap.get(p, f"#{p}") for p in sorted(g["ProducerIDs"])) or "–"
    return sorted(groups.values(), key=lambda g: (g["Yarn"], g["Batch"]))


# ---------------------------------------------------------------- reading details
def used_in(spool_ids: List[int]) -> List[Dict]:
    """Trials that used the spools (traceability)."""
    if not spool_ids or not table_exists("tbltrialsettings") or not table_exists("tbltrial"):
        return []
    ph = ",".join(["?"] * len(spool_ids))
    try:
        return fetch_all(
            f"SELECT ts.SpoolID, ts.Ply, t.Versuchsnummer, t.TrialSeriesID, e.ExperimentID AS ExperimentIDTxt "
            f"FROM tbltrialsettings ts JOIN tbltrial t ON t.ID = ts.TrialID "
            f"LEFT JOIN tbltrialseries s ON s.ID = t.TrialSeriesID "
            f"LEFT JOIN tblexperimente e ON e.ID = s.ExperimentID "
            f"WHERE ts.SpoolID IN ({ph}) ORDER BY ts.SpoolID, t.Versuchsnummer", list(spool_ids))
    except Exception:
        return []


def history(spool_ids: List[int]) -> List[Dict]:
    try:
        return yarn_spool_log.fetch_spool_history(spool_ids)
    except Exception:
        return []


def describe_history(r: Dict) -> str:
    """One change line of the spool history (desktop SpoolHistoryDialog)."""
    action = r.get("Action")
    if action == yarn_spool_log.CREATED:
        return f"Created: {r.get('NewValue') or ''}".rstrip(": ")
    if action == yarn_spool_log.DISCARDED:
        new = (r.get("NewValue") or "").strip()
        note = new[len("discarded"):].strip() if new.lower().startswith("discarded") else ""
        return f"Discarded {note}".strip()
    return f"{r.get('FieldName') or 'Value'}: {r.get('OldValue') or '–'} → {r.get('NewValue') or '–'}"


# ---------------------------------------------------------------- writing
def create_producer(name: str) -> Optional[int]:
    name = (name or "").strip()
    if not name or not table_exists(PRODUCER_TABLE):
        return None
    execute(f"INSERT INTO {PRODUCER_TABLE} ([Name],[GlobalID]) VALUES (?,?)", [name, new_global_id()])
    rows = fetch_all(f"SELECT ID FROM {PRODUCER_TABLE} WHERE [Name] = ? ORDER BY ID DESC LIMIT 1", [name])
    return int(rows[0]["ID"]) if rows else None


def new_spools(values: Dict[str, Any], user_id: Any) -> Tuple[List[int], Optional[Exception]]:
    """Inserts ``Count`` spools (YarnID, Charge, WeightKg, Location, Colour, ProducerID), logs them as
    created. Returns (new ids, error) - after an error the spools inserted so far stay (like the desktop)."""
    today = date.today().isoformat()
    spool_cmap = get_columns_map(SPOOL_TABLE)
    cols = ["YarnID", "Charge", "WeightKg", "Status", "Location", "ReceivedDate", "UserID"]
    base: List[Any] = [values["YarnID"], values.get("Charge"), values["WeightKg"], "in stock",
                       values.get("Location"), today, user_id]
    if "colour" in spool_cmap:
        cols.append("Colour")
        base.append(values.get("Colour"))
    if "producerid" in spool_cmap:
        cols.append("ProducerID")
        base.append(values.get("ProducerID"))
    cols.append("GlobalID")
    ph = ",".join(["?"] * len(cols))
    new_ids: List[int] = []
    error = None
    try:
        for _ in range(int(values.get("Count") or 1)):
            nid = execute_insert(f"INSERT INTO {SPOOL_TABLE} ({','.join('[' + c + ']' for c in cols)}) VALUES ({ph})",
                                 base + [new_global_id()])
            if nid:
                new_ids.append(int(nid))
    except Exception as e:      # partial insert: report, keep what exists
        error = e
    summary = (f"{float(values['WeightKg']):.2f} kg, location {values.get('Location') or '–'}, "
               f"batch {values.get('Charge') or '–'}")
    yarn_spool_log.log_spool_changes(
        {"SpoolID": sid, "Action": yarn_spool_log.CREATED, "New": summary} for sid in new_ids)
    return new_ids, error


def discard_spools(ids: List[int]) -> int:
    today = date.today().isoformat()
    n = 0
    for sid in ids:
        n += execute(f"UPDATE {SPOOL_TABLE} SET [Status] = 'discarded', [DiscardedDate] = ? WHERE [ID] = ?",
                     [today, sid]) or 0
    yarn_spool_log.log_spool_changes(
        {"SpoolID": sid, "Action": yarn_spool_log.DISCARDED, "Field": "Status", "Old": "in stock", "New": "discarded"}
        for sid in ids)
    return n


def save_spool_changes(weights: Dict[int, float], locations: Dict[int, str], colours: Dict[int, str],
                       producers_: Dict[int, Optional[int]], rows_by_id: Dict[int, Dict],
                       producer_map: Dict[int, str]) -> int:
    """Writes the edited spool fields and logs the real changes. Returns the number of updated fields."""
    n = 0
    for sid, w in weights.items():
        n += execute(f"UPDATE {SPOOL_TABLE} SET [WeightKg] = ? WHERE [ID] = ?", [w, sid]) or 0
    for sid, loc in locations.items():
        n += execute(f"UPDATE {SPOOL_TABLE} SET [Location] = ? WHERE [ID] = ?", [loc or None, sid]) or 0
    for sid, col in colours.items():
        n += execute(f"UPDATE {SPOOL_TABLE} SET [Colour] = ? WHERE [ID] = ?", [col or None, sid]) or 0
    for sid, pid in producers_.items():
        n += execute(f"UPDATE {SPOOL_TABLE} SET [ProducerID] = ? WHERE [ID] = ?", [pid, sid]) or 0

    entries = []

    def add(sid, field, old, new):
        if (old or None) != (new or None):
            entries.append({"SpoolID": sid, "Action": yarn_spool_log.UPDATED, "Field": field, "Old": old, "New": new})

    for sid, w in weights.items():
        old = rows_by_id.get(sid, {}).get("WeightKg")
        old_f = float(old) if old is not None else None
        if old_f is None or abs(old_f - float(w)) > 1e-9:
            entries.append({"SpoolID": sid, "Action": yarn_spool_log.UPDATED, "Field": "Weight (kg)",
                            "Old": old_f, "New": float(w)})
    for sid, loc in locations.items():
        add(sid, "Location", rows_by_id.get(sid, {}).get("Location"), loc)
    for sid, col in colours.items():
        add(sid, "Tube Colour", rows_by_id.get(sid, {}).get("Colour"), col)
    for sid, pid in producers_.items():
        old_pid = rows_by_id.get(sid, {}).get("ProducerID")
        if old_pid != pid:
            entries.append({"SpoolID": sid, "Action": yarn_spool_log.UPDATED, "Field": "Producer",
                            "Old": producer_map.get(old_pid) if old_pid else None,
                            "New": producer_map.get(pid) if pid else None})
    yarn_spool_log.log_spool_changes(entries)
    return n


_GROUP_WHERE = "WHERE [YarnID] = ? AND ([Charge] = ? OR (? = '' AND ([Charge] IS NULL OR [Charge] = '')))"


def _group_all(stock_spools: Iterable[Dict], yarn_id: int, charge: str) -> List[Dict]:
    return [sp for sp in stock_spools if int(sp.get("YarnID") or -1) == int(yarn_id) and (sp.get("Charge") or "") == charge]


def update_group_batch(yarn_id: int, old_charge: str, new_charge: str, stock_spools: Iterable[Dict]) -> None:
    """Renames the batch for ALL spools of this yarn with the old batch (also discarded ones)."""
    old_charge = old_charge or ""
    new_charge = (new_charge or "").strip()
    affected = _group_all(stock_spools, yarn_id, old_charge)
    execute(f"UPDATE {SPOOL_TABLE} SET [Charge] = ? {_GROUP_WHERE}", [new_charge or None, yarn_id, old_charge, old_charge])
    if new_charge != old_charge:
        yarn_spool_log.log_spool_changes(
            {"SpoolID": sp["ID"], "Action": yarn_spool_log.UPDATED, "Field": "Batch",
             "Old": old_charge or None, "New": new_charge or None} for sp in affected)


def update_group_producer(yarn_id: int, charge: str, new_pid: Optional[int], stock_spools: Iterable[Dict],
                          producer_map: Dict[int, str]) -> None:
    """Sets the producer for ALL spools of this yarn / batch (also discarded ones)."""
    charge = charge or ""
    affected = _group_all(stock_spools, yarn_id, charge)
    execute(f"UPDATE {SPOOL_TABLE} SET [ProducerID] = ? {_GROUP_WHERE}", [new_pid, yarn_id, charge, charge])
    yarn_spool_log.log_spool_changes(
        {"SpoolID": sp["ID"], "Action": yarn_spool_log.UPDATED, "Field": "Producer",
         "Old": producer_map.get(sp.get("ProducerID")) if sp.get("ProducerID") else None,
         "New": producer_map.get(new_pid) if new_pid else None}
        for sp in affected if sp.get("ProducerID") != new_pid)


def set_min_stock(yarn_id: int, value: Optional[float]) -> None:
    """tblYarn.MinStock for the whole yarn (rights are checked by the caller: superusers only)."""
    cmap = get_columns_map(YARN_TABLE)
    col = _resolve_field(["MinStock"], cmap)
    id_col = _resolve_field(["ID"], cmap) or "ID"
    if not col:
        raise ValueError("tblYarn has no MinStock column")
    execute(f"UPDATE {YARN_TABLE} SET [{col}] = ? WHERE [{id_col}] = ?", [value, yarn_id])


# ---------------------------------------------------------------- label queue
def queue_items(yarn_names: Dict[int, str]) -> List[Dict]:
    if not table_exists(LABEL_QUEUE_TABLE):
        return []
    rows = fetch_all(
        f"SELECT q.[ID] AS QueueID, q.[SpoolID], s.[YarnID], s.[Charge], s.[WeightKg], s.[Location] "
        f"FROM {LABEL_QUEUE_TABLE} q JOIN {SPOOL_TABLE} s ON s.[ID] = q.[SpoolID] "
        f"WHERE q.[PrintedDate] IS NULL ORDER BY q.[QueuedDate]")
    out = []
    for r in rows:
        yid = r.get("YarnID")
        out.append({"QueueID": r["QueueID"], "SpoolID": r["SpoolID"],
                    "Yarn": yarn_names.get(int(yid), f"Yarn {yid}") if yid is not None else "",
                    "Batch": r.get("Charge") or "", "Weight": float(r.get("WeightKg") or 0),
                    "Location": r.get("Location") or ""})
    return out


def queue_labels(ids: List[int], user_id: Any, already_queued: Iterable[int]) -> int:
    """Adds spools to the label queue (spools already waiting are skipped). Returns the number added."""
    if not table_exists(LABEL_QUEUE_TABLE):
        return 0
    skip = set(already_queued)
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    added = 0
    for sid in ids:
        if sid in skip:
            continue
        execute(f"INSERT INTO {LABEL_QUEUE_TABLE} ([SpoolID],[QueuedDate],[UserID],[GlobalID]) VALUES (?,?,?,?)",
                [sid, now, user_id, new_global_id()])
        skip.add(sid)
        added += 1
    return added


def remove_from_queue(queue_ids: List[int]) -> None:
    for qid in queue_ids:
        execute(f"DELETE FROM {LABEL_QUEUE_TABLE} WHERE [ID] = ?", [qid])


def mark_printed(queue_ids: List[int]) -> None:
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    for qid in queue_ids:
        execute(f"UPDATE {LABEL_QUEUE_TABLE} SET [PrintedDate] = ? WHERE [ID] = ?", [now, qid])


def draw_yarn_label_cell(page, x0: float, y0: float, lw: float, lh: float, item: Dict) -> None:
    """One spool label: yarn name bold on top, QR + location / spool id large + batch small."""
    from db.label_sheets import MM, draw_qr, fit_text, wrap_text_lines
    header_max_w = lw - 4
    HEADER_FS = 9.0
    ty = y0 + 5.0
    for yl in wrap_text_lines(str(item.get("Yarn") or ""), HEADER_FS, header_max_w, max_lines=2, fontname="hebo"):
        page.insert_text(((x0 + 2) * MM, ty * MM), yl, fontsize=HEADER_FS, fontname="hebo")
        ty += HEADER_FS * 0.48
    divider_y = ty + 0.5
    page.draw_line(((x0 + 2) * MM, divider_y * MM), ((x0 + lw - 2) * MM, divider_y * MM),
                   color=(0.75, 0.75, 0.75), width=0.4)
    content_top = divider_y + 1.2
    content_h = (y0 + lh) - content_top - 1.5
    qr_size = min(content_h, lw * 0.42)
    draw_qr(page, x0 + 2, content_top, qr_size, qr_content(item))
    rx = x0 + 2 + qr_size + 3
    r_max_w = max(4.0, (x0 + lw) - rx - 2)
    # the loc / id / batch block needs ~20.5mm; scaled down proportionally so it always fits the cell
    IDEAL_BLOCK_H = 20.5
    scale = min(1.0, max(0.55, content_h / IDEAL_BLOCK_H)) if content_h > 0 else 0.55
    big_fs = max(8.0, 15.0 * scale)
    batch_fs = max(5.0, 8.0 * scale)
    off1, off2, off3 = 6.5 * scale, 7.5 * scale, 6.5 * scale
    loc_txt = fit_text(str(item.get("Location") or "-"), big_fs, r_max_w, fontname="hebo")
    id_txt = fit_text(f"#{item['SpoolID']}", big_fs, r_max_w, fontname="hebo")
    batch_txt = fit_text(str(item.get("Batch") or "-"), batch_fs, r_max_w)
    ry = content_top + off1
    page.insert_text((rx * MM, ry * MM), loc_txt, fontsize=big_fs, fontname="hebo")
    ry += off2
    page.insert_text((rx * MM, ry * MM), id_txt, fontsize=big_fs, fontname="hebo")
    ry += off3
    page.insert_text((rx * MM, ry * MM), batch_txt, fontsize=batch_fs, color=(0.45, 0.45, 0.45))


def labels_pdf(items: List[Dict], template: Dict, start_index: int) -> bytes:
    from db.label_sheets import label_sheet_pdf_bytes
    return label_sheet_pdf_bytes(items, template, start_index, draw_yarn_label_cell)


# ---------------------------------------------------------------- Excel
def _xlsx(title: str, headers: List[str], rows: List[List[Any]], widths: List[int], right_cols: Iterable[int],
          fills: Optional[List[Optional[str]]] = None) -> bytes:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = title[:31]
    ws.append(headers)
    hdr_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = hdr_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
    thin = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    right = set(right_cols)
    for i, vals in enumerate(rows):
        ws.append(vals)
        r = ws.max_row
        fill = PatternFill(start_color=fills[i], end_color=fills[i], fill_type="solid") if fills and fills[i] else None
        for c in range(1, len(headers) + 1):
            cell = ws.cell(row=r, column=c)
            cell.border = border
            if fill:
                cell.fill = fill
            if c in right:
                cell.alignment = Alignment(horizontal="right")
    for c, w in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + c)].width = w
    ws.freeze_panes = "A2"
    ws.print_options.horizontalCentered = True
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def overview_xlsx(rows: List[Dict]) -> bytes:
    """The (filtered) overview as Excel, status colour per row."""
    return _xlsx("Yarn Stock", OV_HEADERS,
                 [[g["YarnName"], g["Charge"] or "–", g["Producers"], g["Count"], round(g["TotalKg"], 2),
                   round(g["YarnTotalKg"], 2), g.get("MinStock"), g["Status"], g["Locations"]] for g in rows],
                 [30, 16, 20, 10, 12, 14, 14, 10, 24], (4, 5, 6, 7),
                 [STATUS_COLOR.get(g["Status"], "").lstrip("#") or None for g in rows])


def rack_xlsx(rows: List[Dict], prefix: str) -> bytes:
    return _xlsx(f"Rack {prefix}", RACK_HEADERS,
                 [[it["Yarn"], it["Batch"] or "–", it["ProducersDisp"], it["Count"], round(it["Weight"], 2),
                   it["LocationsDisp"]] for it in rows],
                 [30, 16, 20, 10, 12, 24], (4, 5))


# ---------------------------------------------------------------- notifications
def refresh_notifications(stock: Dict[str, Any]) -> None:
    """Bell messages per yarn for Low / Empty, expire them for yarns that are OK again. Never raises."""
    try:
        from ui.notifications import (create_yarn_stock_notifications, expire_yarn_stock_notifications_for_yarns,
                                      remove_legacy_batch_yarn_stock_notifications)
        status, names = stock["yarn_status"], stock["yarn_names"]
        remove_legacy_batch_yarn_stock_notifications()
        low = [y for y, s in status.items() if s in ("Low", "Empty")]
        ok = [y for y, s in status.items() if s == "OK"]
        if low:
            create_yarn_stock_notifications([{"YarnID": y, "YarnName": names.get(y, f"Yarn {y}"), "Charge": None,
                                              "Status": status[y]} for y in low])
        if ok:
            expire_yarn_stock_notifications_for_yarns(ok)
    except Exception:
        pass
