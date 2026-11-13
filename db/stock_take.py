# db/stock_take.py
"""Stock take rounds for Yarn Stock, Nutzerwunsch 2026-10-16.

A round ("Stock take autumn 2026") covers every storage location; a
superuser starts it (and may leave out single locations) and closes it.
Everybody with write access checks locations one by one with the scan
dialog (ui/widgets/stock_take_dialog.py, location mode); each check stores
its outcome per spool. The overview (ui/widgets/stock_take_round_dialog.py)
shows which locations are still open, which were fine and where something
was off, plus a result list and an Excel export.

Tables (MySQL only - offline the round mode is not available, the single
location check without a round still works):
  tblStockTakeRound     one row per round (Name, Started*, Closed*)
  tblStockTakeLocation  one row per round + location: Excluded, last check
                        (CheckedAt/By, Expected, Found)
  tblStockTakeItem      outcome per spool of the last check of a location
                        (re-checking a location replaces its items)

Locations = every location a spool was ever registered at (any status, so
also empty ones - an unregistered spool may lie there), normalised to upper
case. Locations that appear during a round (spool moved to a new slot) are
added to the open round automatically.

The spool changes themselves (move, put back, discard) are still written
and logged by the scan dialog (tblYarnSpool + db/yarn_spool_log.py); this
module only records what the stock take found.
"""
from __future__ import annotations

import datetime
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ROUND_TABLE = "tblStockTakeRound"
LOCATION_TABLE = "tblStockTakeLocation"
ITEM_TABLE = "tblStockTakeItem"

CREATE_SQL = [
    """
    CREATE TABLE IF NOT EXISTS tblStockTakeRound (
        ID INT AUTO_INCREMENT PRIMARY KEY,
        Name VARCHAR(120) NOT NULL,
        StartedAt DATETIME NOT NULL,
        StartedBy INT NULL,
        ClosedAt DATETIME NULL,
        ClosedBy INT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tblStockTakeLocation (
        ID INT AUTO_INCREMENT PRIMARY KEY,
        RoundID INT NOT NULL,
        Location VARCHAR(50) NOT NULL,
        Excluded TINYINT NOT NULL DEFAULT 0,
        CheckedAt DATETIME NULL,
        CheckedBy INT NULL,
        Expected INT NULL,
        Found INT NULL,
        UNIQUE KEY ux_stocktake_round_loc (RoundID, Location),
        INDEX ix_stocktake_loc_round (RoundID)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tblStockTakeItem (
        ID INT AUTO_INCREMENT PRIMARY KEY,
        RoundID INT NOT NULL,
        Location VARCHAR(50) NOT NULL,
        SpoolID INT NULL,
        Result VARCHAR(30) NOT NULL,
        Detail VARCHAR(255) NULL,
        CheckedAt DATETIME NOT NULL,
        CheckedBy INT NULL,
        INDEX ix_stocktake_item_round (RoundID, Location)
    )
    """,
]

# ── results per spool ────────────────────────────────────────────────────
FOUND = "found"                        # expected here and found
MOVED_HERE = "moved_here"              # registered elsewhere, moved to this location
MOVED_ELSEWHERE = "moved_elsewhere"    # scanned here, moved to another location (Detail)
ELSEWHERE_UNCHANGED = "elsewhere"      # registered elsewhere, left unchanged
RESTOCKED = "restocked"                # was discarded, put back in stock
DISCARDED_UNCHANGED = "discarded"      # was discarded, left discarded
UNKNOWN = "unknown"                    # number does not exist
MISSING_KEPT = "missing_kept"          # expected, not found, kept in stock
MISSING_DISCARDED = "missing_discarded"  # expected, not found, discarded

RESULT_LABELS = {
    FOUND: "Found",
    MOVED_HERE: "Found here, moved here",
    MOVED_ELSEWHERE: "Found here, moved elsewhere",
    ELSEWHERE_UNCHANGED: "Found here, registered elsewhere (unchanged)",
    RESTOCKED: "Was discarded, put back in stock",
    DISCARDED_UNCHANGED: "Was discarded, left discarded",
    UNKNOWN: "Unknown spool number",
    MISSING_KEPT: "Missing - kept in stock",
    MISSING_DISCARDED: "Missing - discarded",
}
# Detail of a FOUND item that was double-clicked in the list instead of
# scanned (ui/widgets/stock_take_dialog.py) - shown in results/Excel
BY_HAND_NOTE = "marked by hand (not scanned)"

# results that mean "this spool was seen somewhere in this round"
_SEEN = {FOUND, MOVED_HERE, MOVED_ELSEWHERE, ELSEWHERE_UNCHANGED, RESTOCKED, DISCARDED_UNCHANGED}
_MISSING = {MISSING_KEPT, MISSING_DISCARDED}

# location states (overview tiles)
ST_OPEN, ST_OK, ST_DEVIATION, ST_EXCLUDED = "open", "ok", "deviation", "excluded"


class StockTakeError(Exception):
    pass


# ── pure helpers (tested without DB) ─────────────────────────────────────
def norm_location(loc: Any) -> str:
    return str(loc or "").strip().upper()


_LOC_RE = re.compile(r"^([A-Z]+)(\d)?(\d*)(.*)$")


def parse_location(loc: str) -> Tuple[str, str, str]:
    """'C21' -> ('C', '2', '1'); 'E' -> ('E', '', ''); '12X' -> ('', '', '12X').
    Rack = leading letters, level = first digit, rest = slot (+ suffix)."""
    loc = norm_location(loc)
    m = _LOC_RE.match(loc)
    if not m:
        return "", "", loc
    return m.group(1), m.group(2) or "", (m.group(3) or "") + (m.group(4) or "")


def location_sort_key(loc: str):
    rack, level, rest = parse_location(loc)
    m = re.match(r"^(\d+)(.*)$", rest)
    slot = (int(m.group(1)), m.group(2)) if m else (10 ** 6, rest)
    return (rack == "", rack, int(level) if level else -1, slot, loc)


def group_locations(locations: Iterable[str]) -> List[Tuple[str, List[Tuple[str, List[str]]]]]:
    """[(rack, [(level, [locations])])], naturally sorted; locations
    without a rack letter end up in rack ''."""
    out: Dict[str, Dict[str, List[str]]] = {}
    for loc in sorted({norm_location(l) for l in locations if norm_location(l)}, key=location_sort_key):
        rack, level, _ = parse_location(loc)
        out.setdefault(rack, {}).setdefault(level, []).append(loc)
    racks = sorted(out, key=lambda r: (r == "", r))
    return [(r, [(lv, out[r][lv]) for lv in sorted(out[r], key=lambda x: (x == "", x))]) for r in racks]


def is_deviation(result: str) -> bool:
    return result != FOUND


def location_status(loc_row: Dict[str, Any], items: Sequence[Dict[str, Any]]) -> str:
    if loc_row.get("Excluded"):
        return ST_EXCLUDED
    if not loc_row.get("CheckedAt"):
        return ST_OPEN
    return ST_DEVIATION if any(is_deviation(i.get("Result") or "") for i in items) else ST_OK


def resolve_missing(items: Sequence[Dict[str, Any]]) -> Dict[int, str]:
    """Missing spools that were seen at another location in the same round:
    {item index: "seen at C21"}. Shown in the results instead of a plain
    'missing' - a spool missing at A11 and found at C21 is not lost."""
    seen_at: Dict[int, str] = {}
    for it in items:
        sid = it.get("SpoolID")
        if sid is not None and it.get("Result") in _SEEN:
            seen_at.setdefault(int(sid), norm_location(it.get("Location")))
    out = {}
    for n, it in enumerate(items):
        sid = it.get("SpoolID")
        if it.get("Result") in _MISSING and sid is not None and int(sid) in seen_at:
            out[n] = f"seen at {seen_at[int(sid)]}"
    return out


def summarize(locations: Sequence[Dict[str, Any]], items: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    """Counts for the header / Excel: locations by state, spools by result."""
    by_loc: Dict[str, List[Dict[str, Any]]] = {}
    for it in items:
        by_loc.setdefault(norm_location(it.get("Location")), []).append(it)
    s = {ST_OPEN: 0, ST_OK: 0, ST_DEVIATION: 0, ST_EXCLUDED: 0}
    for l in locations:
        s[location_status(l, by_loc.get(norm_location(l.get("Location")), []))] += 1
    s["locations"] = len(locations)
    s["to_check"] = len(locations) - s[ST_EXCLUDED]
    s["checked"] = s[ST_OK] + s[ST_DEVIATION]
    for code in RESULT_LABELS:
        s[code] = sum(1 for it in items if it.get("Result") == code)
    s["missing_seen_elsewhere"] = len(resolve_missing(items))
    s["found_by_hand"] = sum(1 for it in items if it.get("Result") == FOUND and it.get("Detail") == BY_HAND_NOTE)
    return s


# ── DB ───────────────────────────────────────────────────────────────────
def create_tables() -> None:
    """Only call deliberately - dev/prod only with explicit permission."""
    from db import connection
    for sql in CREATE_SQL:
        connection.execute(sql)
    connection._COLUMNS_MAP_CACHE.clear()


def available() -> bool:
    try:
        from db.connection import get_columns_map, is_offline_mode
        if is_offline_mode():
            return False
        return all("id" in get_columns_map(t) for t in (ROUND_TABLE, LOCATION_TABLE, ITEM_TABLE))
    except Exception:
        return False


def _uid() -> Optional[int]:
    import app_meta
    return (app_meta.current_user or {}).get("id")


def _now() -> datetime.datetime:
    return datetime.datetime.now().replace(microsecond=0)


_USER_NAME = "TRIM(CONCAT(COALESCE(u.FirstName,''), ' ', COALESCE(u.LastName,'')))"


def list_rounds() -> List[Dict[str, Any]]:
    from db.connection import fetch_all
    return fetch_all(
        f"SELECT r.ID, r.Name, r.StartedAt, r.ClosedAt, {_USER_NAME} AS StartedByName "
        "FROM tblStockTakeRound r LEFT JOIN tblUser u ON u.ID = r.StartedBy ORDER BY r.StartedAt DESC, r.ID DESC")


def get_round(round_id: int) -> Optional[Dict[str, Any]]:
    from db.connection import fetch_all
    rows = fetch_all(
        f"SELECT r.ID, r.Name, r.StartedAt, r.ClosedAt, {_USER_NAME} AS StartedByName "
        "FROM tblStockTakeRound r LEFT JOIN tblUser u ON u.ID = r.StartedBy WHERE r.ID = ?", [int(round_id)])
    return rows[0] if rows else None


def open_round() -> Optional[Dict[str, Any]]:
    for r in list_rounds():
        if r.get("ClosedAt") is None:
            return r
    return None


def all_locations() -> List[str]:
    """Every location a spool was ever registered at (any status)."""
    from db.connection import fetch_all
    rows = fetch_all("SELECT DISTINCT [Location] AS L FROM tblYarnSpool WHERE [Location] IS NOT NULL")
    return sorted({norm_location(r["L"]) for r in rows if norm_location(r["L"])}, key=location_sort_key)


def start_round(name: str, locations: Sequence[str], excluded: Iterable[str] = ()) -> int:
    from db.connection import get_connection
    if open_round() is not None:
        raise StockTakeError("A stock take round is already open. Close it first.")
    name = (name or "").strip()[:120] or f"Stock take {datetime.date.today():%B %Y}"
    excl = {norm_location(l) for l in excluded}
    locs = sorted({norm_location(l) for l in locations if norm_location(l)}, key=location_sort_key)
    with get_connection() as cn:
        cur = cn.cursor()
        try:
            cur.execute("INSERT INTO tblStockTakeRound (Name, StartedAt, StartedBy) VALUES (?,?,?)",
                        (name, _now(), _uid()))
            rid = int(cur.lastrowid)
            for loc in locs:
                cur.execute("INSERT INTO tblStockTakeLocation (RoundID, Location, Excluded) VALUES (?,?,?)",
                            (rid, loc, 1 if loc in excl else 0))
            cn.commit()
        except Exception:
            try:
                cn.rollback()
            except Exception:
                pass
            raise
    _log("stock_take_round_start", f"{rid}: {len(locs)} locations, {len(excl & set(locs))} excluded")
    return rid


def round_locations(round_id: int, add_new: bool = True) -> List[Dict[str, Any]]:
    """Locations of a round, naturally sorted. For an open round, locations
    that appeared since the start are added first (not excluded)."""
    from db.connection import execute, fetch_all
    rnd = get_round(round_id)
    if add_new and rnd is not None and rnd.get("ClosedAt") is None:
        have = {norm_location(r["Location"]) for r in
                fetch_all("SELECT Location FROM tblStockTakeLocation WHERE RoundID = ?", [int(round_id)])}
        for loc in all_locations():
            if loc not in have:
                execute("INSERT IGNORE INTO tblStockTakeLocation (RoundID, Location, Excluded) VALUES (?,?,0)",
                        [int(round_id), loc])
    rows = fetch_all(
        f"SELECT l.ID, l.Location, l.Excluded, l.CheckedAt, l.CheckedBy, l.Expected, l.Found, "
        f"{_USER_NAME} AS CheckedByName FROM tblStockTakeLocation l LEFT JOIN tblUser u ON u.ID = l.CheckedBy "
        "WHERE l.RoundID = ?", [int(round_id)])
    for r in rows:
        r["Location"] = norm_location(r["Location"])
        r["Excluded"] = bool(int(r.get("Excluded") or 0))
    return sorted(rows, key=lambda r: location_sort_key(r["Location"]))


def set_excluded(round_id: int, location: str, excluded: bool) -> None:
    from db.connection import execute
    execute("UPDATE tblStockTakeLocation SET Excluded = ? WHERE RoundID = ? AND Location = ?",
            [1 if excluded else 0, int(round_id), norm_location(location)])


def round_items(round_id: int) -> List[Dict[str, Any]]:
    from db.connection import fetch_all
    rows = fetch_all(
        f"SELECT i.ID, i.Location, i.SpoolID, i.Result, i.Detail, i.CheckedAt, {_USER_NAME} AS CheckedByName "
        "FROM tblStockTakeItem i LEFT JOIN tblUser u ON u.ID = i.CheckedBy "
        "WHERE i.RoundID = ? ORDER BY i.CheckedAt, i.ID", [int(round_id)])
    for r in rows:
        r["Location"] = norm_location(r["Location"])
    return rows


def save_check(round_id: int, location: str, expected: int, items: Sequence[Dict[str, Any]]) -> None:
    """Stores the outcome of one location check (replaces an earlier check
    of the same location in this round). items: [{SpoolID, Result, Detail}]."""
    from db.connection import get_connection
    loc = norm_location(location)
    now, uid = _now(), _uid()
    found = sum(1 for i in items if i.get("Result") == FOUND)
    with get_connection() as cn:
        cur = cn.cursor()
        try:
            cur.execute("SELECT ClosedAt FROM tblStockTakeRound WHERE ID = ?", (int(round_id),))
            row = cur.fetchone()
            if not row:
                raise StockTakeError("The stock take round does not exist any more.")
            if row[0] is not None:
                raise StockTakeError("The stock take round was closed in the meantime - the result was not saved.")
            cur.execute("DELETE FROM tblStockTakeItem WHERE RoundID = ? AND Location = ?", (int(round_id), loc))
            for it in items:
                cur.execute(
                    "INSERT INTO tblStockTakeItem (RoundID, Location, SpoolID, Result, Detail, CheckedAt, CheckedBy) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (int(round_id), loc, it.get("SpoolID"), it["Result"], (it.get("Detail") or "")[:255] or None,
                     now, uid))
            cur.execute(
                "INSERT INTO tblStockTakeLocation (RoundID, Location, Excluded, CheckedAt, CheckedBy, Expected, Found) "
                "VALUES (?,?,0,?,?,?,?) ON DUPLICATE KEY UPDATE CheckedAt = VALUES(CheckedAt), "
                "CheckedBy = VALUES(CheckedBy), Expected = VALUES(Expected), Found = VALUES(Found)",
                (int(round_id), loc, now, uid, int(expected), found))
            cn.commit()
        except Exception:
            try:
                cn.rollback()
            except Exception:
                pass
            raise


def close_round(round_id: int) -> None:
    from db.connection import execute
    execute("UPDATE tblStockTakeRound SET ClosedAt = ?, ClosedBy = ? WHERE ID = ? AND ClosedAt IS NULL",
            [_now(), _uid(), int(round_id)])
    _log("stock_take_round_close", str(round_id))


# ── spool corrections during a check (written at once, logged) ───────────
def move_spool(spool_id: int, new_location: str, old_location: Any) -> None:
    """Spool found here but registered elsewhere -> moved to ``new_location`` (logged)."""
    from db.connection import execute
    from db import yarn_spool_log
    new = norm_location(new_location)
    execute("UPDATE tblYarnSpool SET [Location] = ? WHERE [ID] = ?", [new, int(spool_id)])
    yarn_spool_log.log_spool_changes([{"SpoolID": int(spool_id), "Action": yarn_spool_log.UPDATED,
                                       "Field": "Location", "Old": old_location, "New": f"{new} (stock take)"}])


def restock_spool(spool_id: int, new_location: str, old_location: Any) -> None:
    """Discarded spool found -> back in stock at ``new_location`` (logged)."""
    from db.connection import execute
    from db import yarn_spool_log
    new = norm_location(new_location)
    execute("UPDATE tblYarnSpool SET [Status] = 'in stock', [DiscardedDate] = NULL, [Location] = ? WHERE [ID] = ?",
            [new, int(spool_id)])
    yarn_spool_log.log_spool_changes([
        {"SpoolID": int(spool_id), "Action": yarn_spool_log.UPDATED, "Field": "Status",
         "Old": "discarded", "New": "in stock (stock take)"},
        {"SpoolID": int(spool_id), "Action": yarn_spool_log.UPDATED, "Field": "Location",
         "Old": old_location, "New": f"{new} (stock take)"},
    ])


def discard_missing(spool_ids: Sequence[int]) -> int:
    """Missing spools discarded at Finish (only on an explicit click; logged)."""
    from db.connection import execute
    from db import yarn_spool_log
    today = datetime.date.today().isoformat()
    n = 0
    for sid in spool_ids:
        n += execute("UPDATE tblYarnSpool SET [Status] = 'discarded', [DiscardedDate] = ? WHERE [ID] = ?",
                     [today, int(sid)]) or 0
    yarn_spool_log.log_spool_changes(
        {"SpoolID": int(sid), "Action": yarn_spool_log.DISCARDED, "Field": "Status",
         "Old": "in stock", "New": "discarded (stock take)"} for sid in spool_ids)
    return n


# ── overview layout + Excel (shared by the desktop dialog and the web app) ─
def when_text(v) -> str:
    return v.strftime("%d.%m.%Y %H:%M") if hasattr(v, "strftime") else str(v or "")


def tile_columns(locs: List[str]) -> List[Tuple[str, int]]:
    """Column per location within one level: by slot number (C21 -> 0, C23 -> 2), so the slots of all
    levels line up even with gaps; locations without a plain slot number follow after the numbered ones."""
    out, used = [], set()
    rest_locs = []
    for loc in locs:
        _r, _lv, slot = parse_location(loc)
        if slot.isdigit() and 0 < int(slot) <= 40 and int(slot) - 1 not in used:
            out.append((loc, int(slot) - 1))
            used.add(int(slot) - 1)
        else:
            rest_locs.append(loc)
    nxt = max(used) + 1 if used else 0
    for loc in rest_locs:
        out.append((loc, nxt))
        nxt += 1
    return out


def export_excel_bytes(rnd: Dict, locs: List[Dict], items: List[Dict],
                       spools: Dict[int, Dict], yarn_names: Dict[int, str]) -> bytes:
    """Three sheets: Summary, Locations, Results (every spool, not only differences)."""
    import io
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    bold = Font(bold=True)
    summary = summarize(locs, items)
    ws = wb.active
    ws.title = "Summary"
    rows = [("Round", rnd["Name"]), ("Started", when_text(rnd.get("StartedAt"))),
            ("Started by", rnd.get("StartedByName") or ""), ("Closed", when_text(rnd.get("ClosedAt")) or "open"),
            ("", ""), ("Locations in round", summary["to_check"]), ("Locations checked", summary["checked"]),
            ("  all fine", summary[ST_OK]), ("  with differences", summary[ST_DEVIATION]),
            ("Locations not checked", summary[ST_OPEN]), ("Locations left out", summary[ST_EXCLUDED]),
            ("", "")]
    rows += [(RESULT_LABELS[c], summary[c]) for c in RESULT_LABELS]
    rows.append(("Missing, but seen at another location", summary["missing_seen_elsewhere"]))
    rows.append(("Found, marked by hand (not scanned)", summary["found_by_hand"]))
    for r in rows:
        ws.append(list(r))
    for c in ws["A"]:
        c.font = bold
    ws.column_dimensions["A"].width = 44
    ws.column_dimensions["B"].width = 28

    by_loc: Dict[str, List[Dict]] = {}
    for it in items:
        by_loc.setdefault(it["Location"], []).append(it)
    label = {ST_OPEN: "not checked", ST_OK: "all fine", ST_DEVIATION: "differences", ST_EXCLUDED: "left out"}
    fills = {ST_OK: "EAF3DE", ST_DEVIATION: "FAEEDA", ST_OPEN: "F2F2F2"}
    ws2 = wb.create_sheet("Locations")
    ws2.append(["Location", "Status", "Expected", "Found", "Differences", "Checked by", "Checked at"])
    for l in locs:
        its = by_loc.get(l["Location"], [])
        state = location_status(l, its)
        ws2.append([l["Location"], label[state],
                    l.get("Expected") if l.get("CheckedAt") else None, l.get("Found") if l.get("CheckedAt") else None,
                    sum(1 for i in its if is_deviation(i.get("Result") or "")) if l.get("CheckedAt") else None,
                    l.get("CheckedByName") or "", when_text(l.get("CheckedAt"))])
        if state in fills:
            ws2.cell(ws2.max_row, 2).fill = PatternFill("solid", fgColor=fills[state])

    resolved = resolve_missing(items)
    ws3 = wb.create_sheet("Results")
    ws3.append(["Location", "Spool", "Yarn", "Batch", "Weight (kg)", "Result", "Detail", "Checked by", "Checked at"])
    for n, it in enumerate(items):
        sid = it.get("SpoolID")
        s = spools.get(int(sid)) if sid is not None else None
        detail = it.get("Detail") or ""
        if n in resolved:
            detail = (detail + "; " if detail else "") + resolved[n]
        w = s.get("WeightKg") if s else None
        ws3.append([it["Location"], sid, yarn_names.get(int(s.get("YarnID") or -1), "") if s else "",
                    (s.get("Charge") or "") if s else "", float(w) if w is not None else None,
                    RESULT_LABELS.get(it["Result"], it["Result"]), detail,
                    it.get("CheckedByName") or "", when_text(it.get("CheckedAt"))])
    for sheet in (ws2, ws3):
        for c in sheet[1]:
            c.font = bold
        for col in sheet.columns:
            width = max(len(str(c.value or "")) for c in col)
            sheet.column_dimensions[col[0].column_letter].width = min(max(10, width + 2), 50)
        sheet.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _log(name: str, detail: str) -> None:
    try:
        from db.usage_log import log_usage_event
        log_usage_event("feature", name, detail)
    except Exception:
        pass
