# db/recycle_bin.py
"""Recycle bin for deleted trial series, Nutzerwunsch 2026-10-15.

Deleting a series (Backlog / All Experiments) first stores a complete copy
of everything that belongs to it in tblRecycleBin (JSON), then deletes it.
Who may delete: whoever may move the series in the Backlog
(db/series_permissions.py). A superuser can restore it within RETENTION_DAYS (Sidebar -> Superuser ->
"Recycle Bin", ui/widgets/recycle_bin_dialog.py). Rows are restored with
their original IDs (MySQL never reuses AUTO_INCREMENT values), so all links
(lab values, plies, images, notifications, ...) are intact again.

No soft-delete flag on purpose: every query of the app would have to filter
it. Instead the rows really leave the tables and come back on restore.

What belongs to a series (collected in this order = restore order, deleted
in reverse):
  tblExperimente   only if this is its last series
  tblTrialSeries   the series
  tblTrial         its trials
  every table with a TrialID column        (plies, lab tables, retest flags)
  every table with a TrialSeriesID column  (images, PDFs, jet air, notes...)
  every table with a SeriesPK column       (saved Smart Chart reports)
  rows referencing those via real foreign keys (e.g. image analyses)
Logs/tracking tables are left alone. Yarns made from a trial (tblYarn.
SourceTrialID) block the delete, as before.

MySQL only (uses information_schema); offline the screens keep their old
direct delete.
"""
from __future__ import annotations

import base64
import datetime
import decimal
import json
from typing import Any, Dict, List, Optional, Sequence, Tuple

TABLE = "tblRecycleBin"
RETENTION_DAYS = 90

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS tblRecycleBin (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    DeletedAt DATETIME NOT NULL,
    DeletedBy INT NULL,
    ObjectType VARCHAR(30) NOT NULL,
    ObjectID INT NOT NULL,
    Label VARCHAR(255) NULL,
    Summary VARCHAR(255) NULL,
    Payload LONGTEXT NOT NULL,
    RestoredAt DATETIME NULL,
    RestoredBy INT NULL,
    INDEX ix_recyclebin_deleted (DeletedAt)
)
"""

# never copied/deleted as part of a series (logs, tracking, the bin itself)
_SKIP_TABLES = {"tblchangelog", "tblusagelog", "tblrecyclebin", "tblfeatureusage",
                "tblyarnspoollog", "tbltrial_backup_migration"}
# master data that may point at a trial - their rows block the delete
_BLOCKING_TABLES = {"tblyarn"}


class RecycleBinError(Exception):
    pass


def create_table() -> None:
    """Only call deliberately - dev/prod only with explicit permission."""
    from db import connection
    connection.execute(CREATE_SQL)
    connection._COLUMNS_MAP_CACHE.clear()


def available() -> bool:
    try:
        from db.connection import get_columns_map, is_offline_mode
        if is_offline_mode():
            return False
        return "payload" in get_columns_map(TABLE)
    except Exception:
        return False


# ── JSON with DB types ───────────────────────────────────────────────────
def _enc(v: Any) -> Any:
    if isinstance(v, (bytes, bytearray)):
        return {"__b64__": base64.b64encode(bytes(v)).decode("ascii")}
    if isinstance(v, decimal.Decimal):
        return str(v)
    if isinstance(v, (datetime.datetime, datetime.date, datetime.time)):
        return str(v)
    if isinstance(v, datetime.timedelta):
        return str(v)
    return v


def _dec(v: Any) -> Any:
    if isinstance(v, dict) and "__b64__" in v:
        return base64.b64decode(v["__b64__"])
    return v


# ── schema helpers ───────────────────────────────────────────────────────
def _tables_with_column(cur, column: str) -> List[str]:
    cur.execute(
        "SELECT TABLE_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND LOWER(COLUMN_NAME) = ? ORDER BY TABLE_NAME",
        (column.lower(),))
    return [r[0] for r in cur.fetchall() or []]


def _fk_children(cur, table: str) -> List[Tuple[str, str, str]]:
    """[(child table, child column, referenced column)] via real FKs."""
    cur.execute(
        "SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE "
        "WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_SCHEMA = DATABASE() "
        "AND LOWER(REFERENCED_TABLE_NAME) = ?", (table.lower(),))
    return [(r[0], r[1], r[2]) for r in cur.fetchall() or []]


def _select(cur, table: str, column: str, values: Sequence[Any]) -> List[Dict[str, Any]]:
    values = list(values)
    if not values:
        return []
    out: List[Dict[str, Any]] = []
    for k in range(0, len(values), 500):
        chunk = values[k:k + 500]
        ph = ",".join(["?"] * len(chunk))
        cur.execute(f"SELECT * FROM `{table}` WHERE `{column}` IN ({ph})", chunk)
        names = [d[0] for d in cur.description]
        out.extend(dict(zip(names, row)) for row in cur.fetchall() or [])
    return out


def collect_series(cur, series_id: int) -> List[Tuple[str, List[Dict[str, Any]]]]:
    """Everything that belongs to a series, parents first (see module doc)."""
    groups: List[Tuple[str, List[Dict[str, Any]]]] = []
    seen: Dict[str, set] = {}

    def add(table: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        key = table.lower()
        if key in _SKIP_TABLES:
            return []
        ids = seen.setdefault(key, set())
        new = [r for r in rows if r.get("ID") is None or r.get("ID") not in ids]
        ids.update(r.get("ID") for r in new if r.get("ID") is not None)
        if new:
            for i, (t, existing) in enumerate(groups):
                if t.lower() == key:
                    existing.extend(new)
                    break
            else:
                groups.append((table, new))
        return new

    series = _select(cur, "tblTrialSeries", "ID", [series_id])
    if not series:
        raise RecycleBinError("Trial series not found.")
    exp_id = series[0].get("ExperimentID")
    if exp_id is not None:
        cur.execute("SELECT COUNT(*) FROM tblTrialSeries WHERE ExperimentID = ? AND ID <> ?", (exp_id, series_id))
        if int((cur.fetchone() or [0])[0] or 0) == 0:
            add("tblExperimente", _select(cur, "tblExperimente", "ID", [exp_id]))
    add("tblTrialSeries", series)
    trials = add("tblTrial", _select(cur, "tblTrial", "TrialSeriesID", [series_id]))
    trial_ids = [r["ID"] for r in trials]

    for t in _BLOCKING_TABLES:
        for child, col, _ref in _fk_children(cur, "tblTrial"):
            if child.lower() == t and trial_ids and _select(cur, child, col, trial_ids):
                raise RecycleBinError(
                    "Yarns were created from trials of this series (half-finished products). "
                    "Delete or relink these yarns first.")

    frontier: List[str] = ["tblTrial", "tblTrialSeries"]
    for t in _tables_with_column(cur, "TrialID"):
        if t.lower() not in ("tbltrial",) and t.lower() not in _BLOCKING_TABLES:
            if add(t, _select(cur, t, "TrialID", trial_ids)):
                frontier.append(t)
    for t in _tables_with_column(cur, "TrialSeriesID"):
        if t.lower() not in ("tbltrial",):
            if add(t, _select(cur, t, "TrialSeriesID", [series_id])):
                frontier.append(t)
    for t in _tables_with_column(cur, "SeriesPK"):
        if add(t, _select(cur, t, "SeriesPK", [series_id])):
            frontier.append(t)

    # rows referencing collected rows via real FKs (e.g. image analyses)
    done = {"tblexperimente"}
    while frontier:
        parent = frontier.pop(0)
        if parent.lower() in done:
            continue
        done.add(parent.lower())
        parent_rows = next((rows for t, rows in groups if t.lower() == parent.lower()), [])
        for child, col, ref in _fk_children(cur, parent):
            if child.lower() in _SKIP_TABLES or child.lower() in _BLOCKING_TABLES:
                continue
            vals = [r.get(ref) for r in parent_rows if r.get(ref) is not None]
            if vals and add(child, _select(cur, child, col, vals)):
                frontier.append(child)
    return groups


def _summary(groups) -> str:
    counts = {t.lower(): len(rows) for t, rows in groups}
    n_trials = counts.get("tbltrial", 0)
    n_lab = sum(n for t, n in counts.items() if t.startswith("tbllabor"))
    return f"{n_trials} trial{'s' if n_trials != 1 else ''}, {n_lab} lab row{'s' if n_lab != 1 else ''}"


def delete_series(series_id: int, label: str = "") -> int:
    """Copies the series into the recycle bin and deletes it - one
    transaction. Returns the recycle bin ID. Raises on error (nothing
    deleted then)."""
    from db.connection import get_connection
    from db.series_permissions import can_delete_series, can_move_series_now
    import app_meta
    if not can_move_series_now(series_id, _rule=can_delete_series):
        # last line of defence - the screens check this before already
        raise RecycleBinError("You may only delete a series you are allowed to move in the Backlog "
                              "(in To Be Cleaned: superusers only).")
    uid = (app_meta.current_user or {}).get("id")
    with get_connection() as cn:
        cur = cn.cursor()
        try:
            groups = collect_series(cur, int(series_id))
            payload = json.dumps({"version": 1, "groups": [
                {"table": t, "rows": [{k: _enc(v) for k, v in r.items()} for r in rows]} for t, rows in groups]})
            cur.execute(
                "INSERT INTO tblRecycleBin (DeletedAt, DeletedBy, ObjectType, ObjectID, Label, Summary, Payload) "
                "VALUES (?,?,?,?,?,?,?)",
                (datetime.datetime.now().replace(microsecond=0), uid, "trial series", int(series_id),
                 (label or "")[:255], _summary(groups), payload))
            bin_id = cur.lastrowid
            for table, rows in reversed(groups):
                ids = [r["ID"] for r in rows if r.get("ID") is not None]
                for k in range(0, len(ids), 500):
                    chunk = ids[k:k + 500]
                    ph = ",".join(["?"] * len(chunk))
                    cur.execute(f"DELETE FROM `{table}` WHERE ID IN ({ph})", chunk)
            cn.commit()
        except Exception:
            try:
                cn.rollback()
            except Exception:
                pass
            raise
    try:
        from db.usage_log import log_usage_event
        log_usage_event("feature", "recycle_bin_delete", str(series_id))
    except Exception:
        pass
    return int(bin_id) if bin_id is not None else 0


def purge_expired() -> int:
    from db.connection import execute
    limit = datetime.datetime.now() - datetime.timedelta(days=RETENTION_DAYS)
    return execute("DELETE FROM tblRecycleBin WHERE DeletedAt < ? OR RestoredAt IS NOT NULL", [limit])


def list_entries() -> List[Dict[str, Any]]:
    from db.connection import fetch_all
    return fetch_all(
        "SELECT b.ID, b.DeletedAt, b.ObjectType, b.ObjectID, b.Label, b.Summary, "
        "TRIM(CONCAT(COALESCE(u.FirstName,''), ' ', COALESCE(u.LastName,''))) AS UserName "
        "FROM tblRecycleBin b LEFT JOIN tblUser u ON u.ID = b.DeletedBy "
        "WHERE b.RestoredAt IS NULL ORDER BY b.DeletedAt DESC")


def restore(bin_id: int) -> str:
    """Puts everything back with the original IDs - one transaction.
    Returns the restored label. Raises RecycleBinError with a readable
    message if something is in the way."""
    from db.connection import get_connection
    import app_meta
    uid = (app_meta.current_user or {}).get("id")
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute("SELECT Payload, Label, RestoredAt FROM tblRecycleBin WHERE ID = ?", (int(bin_id),))
        row = cur.fetchone()
        if not row:
            raise RecycleBinError("Entry not found.")
        if row[2] is not None:
            raise RecycleBinError("This entry was already restored.")
        data = json.loads(row[0])
        try:
            for g in data.get("groups", []):
                table = g["table"]
                rows = g.get("rows") or []
                if not rows:
                    continue
                if table.lower() == "tblexperimente":
                    # the experiment may exist again (or still) - keep it
                    cur.execute("SELECT COUNT(*) FROM tblExperimente WHERE ID = ?", (rows[0].get("ID"),))
                    if int((cur.fetchone() or [0])[0] or 0):
                        continue
                cur.execute(f"SELECT * FROM `{table}` LIMIT 0")
                existing_cols = {d[0].lower(): d[0] for d in cur.description}
                cur.fetchall()
                for r in rows:
                    cols = [c for c in r if c.lower() in existing_cols]
                    ph = ",".join(["?"] * len(cols))
                    cur.execute(
                        f"INSERT INTO `{table}` ({', '.join('`' + existing_cols[c.lower()] + '`' for c in cols)}) "
                        f"VALUES ({ph})", [_dec(r[c]) for c in cols])
            cur.execute("UPDATE tblRecycleBin SET RestoredAt = ?, RestoredBy = ? WHERE ID = ?",
                        (datetime.datetime.now().replace(microsecond=0), uid, int(bin_id)))
            cn.commit()
        except Exception as e:
            try:
                cn.rollback()
            except Exception:
                pass
            msg = str(e)
            if "Duplicate entry" in msg:
                raise RecycleBinError("Some of the rows exist again (same ID) - nothing was restored.\n\n" + msg)
            if "foreign key constraint" in msg.lower():
                raise RecycleBinError("Something this series refers to (e.g. a yarn, jet or user) was deleted "
                                      "in the meantime - nothing was restored.\n\n" + msg)
            raise
    try:
        from db.usage_log import log_usage_event
        log_usage_event("feature", "recycle_bin_restore", str(bin_id))
    except Exception:
        pass
    return str(row[1] or "")


def delete_permanently(bin_id: int) -> None:
    from db.connection import execute
    execute("DELETE FROM tblRecycleBin WHERE ID = ?", [int(bin_id)])
