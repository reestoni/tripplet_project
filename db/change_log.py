# db/change_log.py
"""Change history of values edited in Show Experiment, Nutzerwunsch
2026-10-15 ("wer hat wann welchen Wert von x auf y geändert").

PivotEditModel.save_dirty() reads the old DB values of all changed cells in
one query per (table, field), writes the updates and then logs one row per
changed cell here (old -> new, user, time). Right-click on a value in Show
Experiment -> "Change history…" shows it (ui/change_history_dialog.py).

Best-effort like db/usage_log.py: without the table (not migrated, offline
SQLite copy) nothing is logged and saving works as before.
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

TABLE = "tblChangeLog"

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS tblChangeLog (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    ChangedAt DATETIME NOT NULL,
    UserID INT NULL,
    TableName VARCHAR(64) NOT NULL,
    RowID INT NOT NULL,
    FieldName VARCHAR(64) NOT NULL,
    OldValue VARCHAR(255) NULL,
    NewValue VARCHAR(255) NULL,
    TrialID INT NULL,
    SeriesID INT NULL,
    Source VARCHAR(30) NULL,
    INDEX ix_changelog_cell (TableName, RowID, FieldName),
    INDEX ix_changelog_series (SeriesID, ChangedAt)
)
"""


def create_table() -> None:
    """Only call deliberately - dev/prod only with explicit permission."""
    from db import connection
    connection.execute(CREATE_SQL)
    connection._COLUMNS_MAP_CACHE.clear()


def table_ready() -> bool:
    try:
        from db.connection import get_columns_map
        return "rowid" in get_columns_map(TABLE)
    except Exception:
        return False


def _text(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    # numbers compare by value: 3.50 (DB decimal) == "3.5" (typed)
    return s[:255]


def same_value(a: Any, b: Any) -> bool:
    a, b = _text(a), _text(b)
    if a == b:
        return True
    if a is None or b is None:
        return False
    try:
        return float(a.replace(",", ".")) == float(b.replace(",", "."))
    except ValueError:
        return False


def read_current(table: str, field: str, ids: Sequence[Any]) -> Dict[int, Dict[str, Any]]:
    """{row id: {"value": current value, "trial_id": TrialID or None}} -
    one query for all ids of one (table, field)."""
    from db.connection import fetch_all, get_columns_map
    ids = sorted({int(i) for i in ids if i is not None})
    if not ids:
        return {}
    cols = get_columns_map(table)
    real = cols.get(str(field).lower(), field)
    trial_expr = "ID" if table.lower() == "tbltrial" else (cols.get("trialid") or None)
    sel = f"ID AS _id, `{real}` AS _v" + (f", `{trial_expr}` AS _t" if trial_expr else "")
    out: Dict[int, Dict[str, Any]] = {}
    for k in range(0, len(ids), 500):
        chunk = ids[k:k + 500]
        ph = ",".join(["?"] * len(chunk))
        for r in fetch_all(f"SELECT {sel} FROM {table} WHERE ID IN ({ph})", chunk):
            out[int(r["_id"])] = {"value": r.get("_v"), "trial_id": r.get("_t")}
    return out


def row_before(cur, table: str, rec_id: Any, cols: Sequence[str]) -> Dict[str, Any]:
    """Values of `cols` of one row before an UPDATE (inside the caller's
    transaction). {} when there is no row / on error."""
    if rec_id is None or not cols:
        return {}
    try:
        cur.execute(f"SELECT {', '.join('`' + c + '`' for c in cols)} FROM {table} WHERE ID = ?", (rec_id,))
        row = cur.fetchone()
        return dict(zip(cols, row)) if row else {}
    except Exception:
        return {}


def upsert_entries(table: str, rec_id: Any, before: Dict[str, Any], after: Dict[str, Any],
                   trial_id: Any) -> List[Dict[str, Any]]:
    """Log entries for direct UPDATEs/INSERTs (e.g. PDF imports)."""
    if rec_id is None:
        return []
    return [{"table": table, "row_id": rec_id, "field": f, "old": before.get(f), "new": v,
             "trial_id": trial_id} for f, v in after.items()]


_APP_USER = object()


def log_changes(entries: Iterable[Dict[str, Any]], series_id: Any = None, source: str = "edit",
                user_id: Any = _APP_USER) -> int:
    """entries: dicts with table, row_id, field, old, new, trial_id.
    Unchanged values are skipped. Never raises. user_id: default =
    app_meta.current_user["id"] (desktop); the web passes its user."""
    rows: List[Tuple] = []
    if user_id is not _APP_USER:
        uid = user_id
    else:
        try:
            import app_meta
            uid = (app_meta.current_user or {}).get("id")
        except Exception:
            uid = None
    now = datetime.datetime.now().replace(microsecond=0)
    for e in entries:
        if same_value(e.get("old"), e.get("new")):
            continue
        rows.append((now, uid, str(e["table"]), int(e["row_id"]), str(e["field"]),
                     _text(e.get("old")), _text(e.get("new")),
                     int(e["trial_id"]) if e.get("trial_id") not in (None, "") else None,
                     int(series_id) if series_id not in (None, "") else None, source))
    if not rows or not table_ready():
        return 0
    try:
        from db.connection import get_connection
        with get_connection() as cn:
            cur = cn.cursor()
            cur.executemany(
                "INSERT INTO tblChangeLog (ChangedAt, UserID, TableName, RowID, FieldName, OldValue, "
                "NewValue, TrialID, SeriesID, Source) VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
            cn.commit()
        return len(rows)
    except Exception:
        return 0


def history_for_cell(table: str, ids: Sequence[Any], field: str) -> List[Dict[str, Any]]:
    """All logged changes of one cell (several ids for grouped ply cells)."""
    if not table_ready():
        return []
    from db.connection import fetch_all
    ids = sorted({int(i) for i in ids if i is not None})
    if not ids:
        return []
    ph = ",".join(["?"] * len(ids))
    return fetch_all(
        f"SELECT c.ChangedAt, c.OldValue, c.NewValue, c.RowID, c.Source, "
        f"TRIM(CONCAT(COALESCE(u.FirstName,''), ' ', COALESCE(u.LastName,''))) AS UserName "
        f"FROM tblChangeLog c LEFT JOIN tblUser u ON u.ID = c.UserID "
        f"WHERE LOWER(c.TableName) = ? AND LOWER(c.FieldName) = ? AND c.RowID IN ({ph}) "
        f"ORDER BY c.ChangedAt DESC, c.ID DESC",
        [table.lower(), str(field).lower()] + ids)


def history_for_series(series_id: Any, limit: int = 2000) -> List[Dict[str, Any]]:
    if not table_ready() or series_id in (None, ""):
        return []
    from db.connection import fetch_all
    return fetch_all(
        f"SELECT c.ChangedAt, c.TableName, c.FieldName, c.OldValue, c.NewValue, c.TrialID, c.Source, "
        f"t.Versuchsnummer, "
        f"TRIM(CONCAT(COALESCE(u.FirstName,''), ' ', COALESCE(u.LastName,''))) AS UserName "
        f"FROM tblChangeLog c LEFT JOIN tblUser u ON u.ID = c.UserID "
        f"LEFT JOIN tblTrial t ON t.ID = c.TrialID "
        f"WHERE c.SeriesID = ? ORDER BY c.ChangedAt DESC, c.ID DESC LIMIT {int(limit)}",
        [int(series_id)])
