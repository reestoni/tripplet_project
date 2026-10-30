# db/cell_notes.py
"""Notes on values in Show Experiment (Nutzerwunsch 2026-10-30).

A note belongs to one cell = (table, record ID, field) of a CellBinding, e.g.
("tblLaborStatimatM", 1234, "Tenacity"), plus TrialID/SeriesID for the list
in the Notes tab. A trial-wide note uses ("tblTrial", <TrialID>, "") .
Notes stick to the cell, not to the value: when the value is corrected later
the note stays. Only information, no "done" state (Nutzerentscheid).

Rules (Nutzerentscheid 2026-10-30): everybody may write notes; editing only
by the author; deleting by the author or a superuser. Notes are internal -
they never appear in reports.

Because the table has a TrialID column, db/recycle_bin.delete_series() takes
the notes of a deleted series along (and restores them). Not available in
offline mode (no merge path for a cell reference into other tables).
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

TABLE = "tblNote"
TRIAL_FIELD = ""  # FieldName of a note on the whole trial (TableName tblTrial)

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS tblNote (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    TableName VARCHAR(64) NOT NULL,
    RowID INT NOT NULL,
    FieldName VARCHAR(64) NOT NULL DEFAULT '',
    TrialID INT NOT NULL,
    SeriesID INT NULL,
    NoteText TEXT NOT NULL,
    CreatedAt DATETIME NOT NULL,
    CreatedBy INT NULL,
    UpdatedAt DATETIME NULL,
    INDEX ix_note_cell (TableName, RowID, FieldName),
    INDEX ix_note_series (SeriesID),
    INDEX ix_note_trial (TrialID)
)
"""

CellKey = Tuple[str, int, str]  # (table lower, row id, field lower)


def create_table() -> None:
    """Only call deliberately - dev/prod only with explicit permission."""
    from db import connection
    connection.execute(CREATE_SQL)
    connection._COLUMNS_MAP_CACHE.clear()


def available() -> bool:
    """Table exists and we are online (offline copies have no notes)."""
    try:
        from db.connection import get_columns_map, is_offline_mode
        if is_offline_mode():
            return False
        return "notetext" in get_columns_map(TABLE)
    except Exception:
        return False


def cell_key(table: str, row_id: Any, field: str) -> CellKey:
    return (str(table).lower(), int(row_id), str(field or "").lower())


def _user() -> Tuple[Optional[int], int]:
    try:
        import app_meta
        return (app_meta.current_user or {}).get("id"), int(app_meta.access_level() or 0)
    except Exception:
        return None, 0


def can_edit(note: Dict[str, Any]) -> bool:
    uid, _lvl = _user()
    return uid is not None and note.get("CreatedBy") is not None and int(note["CreatedBy"]) == int(uid)


def can_delete(note: Dict[str, Any]) -> bool:
    _uid, lvl = _user()
    return can_edit(note) or lvl >= 4


def trial_id_of(table: str, row_id: Any) -> Optional[int]:
    """TrialID of a record (tblTrial: the ID itself; other tables: their TrialID)."""
    if str(table).lower() == "tbltrial":
        return int(row_id)
    from db.connection import fetch_all, get_columns_map
    col = get_columns_map(table).get("trialid")
    if not col:
        return None
    rows = fetch_all(f"SELECT `{col}` AS t FROM {table} WHERE ID = ?", [int(row_id)])
    return int(rows[0]["t"]) if rows and rows[0].get("t") is not None else None


_SELECT = (
    "SELECT n.ID, n.TableName, n.RowID, n.FieldName, n.TrialID, n.SeriesID, n.NoteText, "
    "n.CreatedAt, n.CreatedBy, n.UpdatedAt, "
    "TRIM(CONCAT(COALESCE(u.FirstName,''), ' ', COALESCE(u.LastName,''))) AS UserName "
    "FROM tblNote n LEFT JOIN tblUser u ON u.ID = n.CreatedBy "
)


def notes_for_series(series_id: Any, trial_ids: Sequence[int] = ()) -> List[Dict[str, Any]]:
    """All notes of the series, oldest first. Also finds notes whose SeriesID
    is stale (trial moved to another series) via `trial_ids`."""
    if series_id in (None, "") or not available():
        return []
    from db.connection import fetch_all
    ids = sorted({int(t) for t in trial_ids if t is not None})
    where, params = "n.SeriesID = ?", [int(series_id)]
    if ids:
        where = f"(n.SeriesID = ? OR n.TrialID IN ({','.join(['?'] * len(ids))}))"
        params += ids
    try:
        return fetch_all(_SELECT + f"WHERE {where} ORDER BY n.CreatedAt, n.ID", params)
    except Exception:
        return []


def by_cell(notes: Iterable[Dict[str, Any]]) -> Dict[CellKey, List[Dict[str, Any]]]:
    out: Dict[CellKey, List[Dict[str, Any]]] = {}
    for n in notes:
        try:
            out.setdefault(cell_key(n["TableName"], n["RowID"], n.get("FieldName")), []).append(n)
        except Exception:
            pass
    return out


def add_note(table: str, row_id: Any, field: str, text: str,
             trial_id: Optional[int] = None, series_id: Any = None) -> int:
    """Insert a note, returns its ID. Raises on DB errors (caller shows them)."""
    text = (text or "").strip()
    if not text:
        raise ValueError("empty note")
    if trial_id is None:
        trial_id = trial_id_of(table, row_id)
    if trial_id is None:
        raise ValueError(f"no trial for {table} #{row_id}")
    uid, _lvl = _user()
    now = datetime.datetime.now().replace(microsecond=0)
    from db.connection import execute_insert
    return int(execute_insert(
        "INSERT INTO tblNote (TableName, RowID, FieldName, TrialID, SeriesID, NoteText, CreatedAt, CreatedBy) "
        "VALUES (?,?,?,?,?,?,?,?)",
        [str(table), int(row_id), str(field or ""), int(trial_id),
         int(series_id) if series_id not in (None, "") else None, text, now, uid]))


def update_note(note_id: int, text: str) -> None:
    text = (text or "").strip()
    if not text:
        raise ValueError("empty note")
    from db.connection import execute
    execute("UPDATE tblNote SET NoteText = ?, UpdatedAt = ? WHERE ID = ?",
            [text, datetime.datetime.now().replace(microsecond=0), int(note_id)])


def delete_note(note_id: int) -> None:
    from db.connection import execute
    execute("DELETE FROM tblNote WHERE ID = ?", [int(note_id)])


def value_changed_since(note: Dict[str, Any]) -> bool:
    """True if the change log has a change of the note's cell after the note
    was written (shown as "value changed since this note")."""
    if not note.get("FieldName"):
        return False
    try:
        from db import change_log
        hist = change_log.history_for_cell(note["TableName"], [note["RowID"]], note["FieldName"])
    except Exception:
        return False
    t = note.get("CreatedAt")
    return any(h.get("ChangedAt") is not None and t is not None and h["ChangedAt"] > t for h in hist)


def format_when(dt: Any) -> str:
    if isinstance(dt, datetime.datetime):
        return dt.strftime("%d.%m.%Y %H:%M")
    return str(dt or "")[:16]
