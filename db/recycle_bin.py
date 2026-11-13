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

Single trials (Show Experiment, right-click a trial number, Nutzerwunsch
2026-11-11) go in as their own entry, ObjectType "trials" (ObjectID = series
ID): the trials, every table with a TrialID column and FK children of those
rows - nothing of the series itself. The other trials keep their numbers
(nothing moves up); new trials always come after the highest remaining
number, so gaps are never filled - numbers deleted at the end may be given
out again (Nutzerentscheid 2026-11-11), which is why a restore checks that
its numbers are still free.

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
    groups, add = _collector()
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
    frontier: List[str] = ["tblTrial", "tblTrialSeries"]
    _add_trial_children(cur, add, frontier, [r["ID"] for r in trials], "this series")
    for t in _tables_with_column(cur, "TrialSeriesID"):
        if t.lower() not in ("tbltrial",):
            if add(t, _select(cur, t, "TrialSeriesID", [series_id])):
                frontier.append(t)
    for t in _tables_with_column(cur, "SeriesPK"):
        if add(t, _select(cur, t, "SeriesPK", [series_id])):
            frontier.append(t)
    _add_fk_children(cur, add, frontier, groups)
    return groups


def _collector():
    """(groups, add) - add(table, rows) appends rows not collected yet and
    returns the new ones."""
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
            for _t, existing in groups:
                if _t.lower() == key:
                    existing.extend(new)
                    break
            else:
                groups.append((table, new))
        return new
    return groups, add


def _add_trial_children(cur, add, frontier: List[str], trial_ids: List[Any], what: str) -> None:
    """Every table with a TrialID column; yarns made from a trial block."""
    for t in _BLOCKING_TABLES:
        for child, col, _ref in _fk_children(cur, "tblTrial"):
            if child.lower() == t and trial_ids and _select(cur, child, col, trial_ids):
                raise RecycleBinError(
                    f"Yarns were created from trials of {what} (half-finished products). "
                    "Delete or relink these yarns first.")
    for t in _tables_with_column(cur, "TrialID"):
        if t.lower() not in ("tbltrial",) and t.lower() not in _BLOCKING_TABLES:
            if add(t, _select(cur, t, "TrialID", trial_ids)):
                frontier.append(t)


def _add_fk_children(cur, add, frontier: List[str], groups) -> None:
    """Rows referencing collected rows via real FKs (e.g. image analyses)."""
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


def collect_trials(cur, series_id: int, trial_ids: Sequence[int]) -> List[Tuple[str, List[Dict[str, Any]]]]:
    """Everything that belongs to some trials of a series (not the series
    itself), parents first."""
    groups, add = _collector()
    ids = sorted({int(t) for t in trial_ids})
    if not ids:
        raise RecycleBinError("No trials selected.")
    trials = _select(cur, "tblTrial", "ID", ids)
    if len(trials) != len(ids):
        raise RecycleBinError("Some of these trials don't exist any more - reload the series.")
    if any(int(r.get("TrialSeriesID") or 0) != int(series_id) for r in trials):
        raise RecycleBinError("These trials don't all belong to this series.")
    add("tblTrial", trials)
    frontier: List[str] = ["tblTrial"]
    _add_trial_children(cur, add, frontier, ids, "these trials")
    _add_fk_children(cur, add, frontier, groups)
    return groups


def preview_trials(series_id: int, trial_ids: Sequence[int]) -> List[Tuple[str, int]]:
    """Read only: [(table, rows)] that delete_trials() would delete, trials
    first. Raises RecycleBinError (e.g. yarns made from a trial)."""
    from db.connection import get_connection
    with get_connection() as cn:
        groups = collect_trials(cn.cursor(), int(series_id), trial_ids)
    return [(t, len(rows)) for t, rows in groups]


# shown names of the tables a trial delete takes along ("Also deleted: ...")
TABLE_LABELS = {"tbltrial": "trials", "tbltrialsettings": "ply settings", "tblnote": "notes",
                "tbltrialretestflag": "retest flags", "tbllabortiter": "Titer",
                "tbllaboratyomat": "ATYoMat", "tbllaboratyshrinkage": "ATY shrinkage",
                "tbllabordtyomat": "DTYoMat", "tbllaborekb": "EKB",
                "tbllaborheissluftschrumpf": "Hot air shrinkage", "tbllaboritematlab": "Itemat",
                "tbllaboritematplus": "Itemat Plus", "tbllaborkochschrumpf": "Hot water shrinkage",
                "tbllaborrapid600": "Rapid 600", "tbllaborstatimatds": "Statimat DS",
                "tbllaborstatimatm": "Statimat", "tbllaborwaterbath": "Water bath"}


def table_label(table: str) -> str:
    key = str(table).lower()
    return TABLE_LABELS.get(key) or (str(table)[8:] if key.startswith("tbllabor") else str(table))


def can_delete_trials_now(series_id: Any) -> bool:
    """Same rule as deleting the whole series (db/series_permissions.py),
    and only with the recycle bin."""
    from db.series_permissions import can_delete_series, can_move_series_now
    if not available():
        return False
    return can_move_series_now(series_id, _rule=can_delete_series)


def delete_trials(series_id: int, trial_ids: Sequence[int], label: str = "") -> int:
    """Copies the trials (with lab rows, plies, notes ...) into the recycle
    bin and deletes them - one transaction. The numbers of the other
    trials are not touched. Returns the recycle bin ID."""
    from db.connection import get_connection
    import app_meta
    if not can_delete_trials_now(series_id):
        raise RecycleBinError("You may only delete trials of a series you are allowed to move in the Backlog "
                              "(in To Be Cleaned: superusers only).")
    uid = (app_meta.current_user or {}).get("id")
    when = datetime.datetime.now().replace(microsecond=0)
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute("START TRANSACTION")   # the pool is autocommit=True
        try:
            groups = collect_trials(cur, int(series_id), trial_ids)
            trials = next(rows for t, rows in groups if t.lower() == "tbltrial")
            payload = json.dumps({"version": 1, "groups": [
                {"table": t, "rows": [{k: _enc(v) for k, v in r.items()} for r in rows]} for t, rows in groups]})
            cur.execute(
                "INSERT INTO tblRecycleBin (DeletedAt, DeletedBy, ObjectType, ObjectID, Label, Summary, Payload) "
                "VALUES (?,?,?,?,?,?,?)",
                (when, uid, "trials", int(series_id), (label or "")[:255], _summary(groups), payload))
            bin_id = cur.lastrowid
            for table, rows in reversed(groups):
                ids = [r["ID"] for r in rows if r.get("ID") is not None]
                if len(ids) != len(rows):
                    raise RecycleBinError(f"Rows without ID in {table} - nothing was deleted.")
                for k in range(0, len(ids), 500):
                    chunk = ids[k:k + 500]
                    cur.execute(f"DELETE FROM `{table}` WHERE ID IN ({','.join(['?'] * len(chunk))})", chunk)
            cn.commit()
        except Exception:
            try:
                cn.rollback()
            except Exception:
                pass
            raise
    try:
        from db.usage_log import log_usage_event
        log_usage_event("feature", "trial_delete", f"{series_id}: {len(trials)}")
    except Exception:
        pass
    return int(bin_id) if bin_id is not None else 0


def _summary(groups) -> str:
    counts = {t.lower(): len(rows) for t, rows in groups}
    n_trials = counts.get("tbltrial", 0)
    n_lab = sum(n for t, n in counts.items() if t.startswith("tbllabor"))
    return f"{n_trials} trial{'s' if n_trials != 1 else ''}, {n_lab} lab row{'s' if n_lab != 1 else ''}"


def delete_series(series_id: int, label: str = "", *, deleted_at: Optional[datetime.datetime] = None,
                  deleted_by: Optional[int] = None, replaces_bin_id: Optional[int] = None) -> int:
    """Copies the series into the recycle bin and deletes it - one
    transaction. Returns the recycle bin ID. Raises on error (nothing
    deleted then).

    Back into the bin after a preview (ui/recycle_preview.py): deleted_at/
    deleted_by keep the original values (the 90 days don't start again) and
    replaces_bin_id removes the old, meanwhile restored entry."""
    from db.connection import get_connection
    from db.series_permissions import can_delete_series, can_move_series_now
    import app_meta
    if not can_move_series_now(series_id, _rule=can_delete_series):
        # last line of defence - the screens check this before already
        raise RecycleBinError("You may only delete a series you are allowed to move in the Backlog "
                              "(in To Be Cleaned: superusers only).")
    uid = deleted_by if deleted_by is not None else (app_meta.current_user or {}).get("id")
    when = deleted_at or datetime.datetime.now().replace(microsecond=0)
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute("START TRANSACTION")   # the pool is autocommit=True - make rollback real
        try:
            groups = collect_series(cur, int(series_id))
            payload = json.dumps({"version": 1, "groups": [
                {"table": t, "rows": [{k: _enc(v) for k, v in r.items()} for r in rows]} for t, rows in groups]})
            cur.execute(
                "INSERT INTO tblRecycleBin (DeletedAt, DeletedBy, ObjectType, ObjectID, Label, Summary, Payload) "
                "VALUES (?,?,?,?,?,?,?)",
                (when, uid, "trial series", int(series_id), (label or "")[:255], _summary(groups), payload))
            bin_id = cur.lastrowid
            if replaces_bin_id is not None:
                cur.execute("DELETE FROM tblRecycleBin WHERE ID = ?", (int(replaces_bin_id),))
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
        log_usage_event("feature", "recycle_bin_rebin" if replaces_bin_id is not None else "recycle_bin_delete",
                        str(series_id))
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


def entry_info(bin_id: int) -> Optional[Dict[str, Any]]:
    """Everything a preview needs about an entry, without the payload rows:
    ID, DeletedAt, DeletedBy, ObjectID (series ID), Label, RestoredAt,
    ExperimentPK (from the stored series row)."""
    from db.connection import fetch_all
    rows = fetch_all("SELECT ID, DeletedAt, DeletedBy, ObjectID, Label, RestoredAt, Payload "
                     "FROM tblRecycleBin WHERE ID = ?", [int(bin_id)])
    if not rows:
        return None
    r = rows[0]
    info = {k: r.get(k) for k in ("ID", "DeletedAt", "DeletedBy", "ObjectID", "Label", "RestoredAt")}
    info["ExperimentPK"] = None
    try:
        for g in json.loads(r.get("Payload") or "{}").get("groups", []):
            if g.get("table", "").lower() == "tbltrialseries" and g.get("rows"):
                row = {k.lower(): v for k, v in g["rows"][0].items()}
                info["ExperimentPK"] = _dec(row.get("experimentid"))
                break
    except Exception:
        pass
    return info


def restore(bin_id: int) -> str:
    """Puts everything back with the original IDs - one transaction.
    Returns the restored label. Raises RecycleBinError with a readable
    message if something is in the way."""
    from db.connection import get_connection
    import app_meta
    uid = (app_meta.current_user or {}).get("id")
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute("SELECT Payload, Label, RestoredAt, ObjectType, ObjectID FROM tblRecycleBin WHERE ID = ?",
                    (int(bin_id),))
        row = cur.fetchone()
        if not row:
            raise RecycleBinError("Entry not found.")
        if row[2] is not None:
            raise RecycleBinError("This entry was already restored.")
        data = json.loads(row[0])
        if (row[3] or "") == "trials":
            _check_trials_restorable(cur, int(row[4]), data)
        cur.execute("START TRANSACTION")   # the pool is autocommit=True - make rollback real
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


def _check_trials_restorable(cur, series_id: int, data: Dict[str, Any]) -> None:
    """Trials go back into their series - it must exist and their numbers
    must still be free."""
    cur.execute("SELECT COUNT(*) FROM tblTrialSeries WHERE ID = ?", (series_id,))
    if not int((cur.fetchone() or [0])[0] or 0):
        raise RecycleBinError("The trial series of these trials was deleted - restore the series first.")
    rows = next((g.get("rows") or [] for g in data.get("groups", [])
                 if (g.get("table") or "").lower() == "tbltrial"), [])
    nos = [int(r["Versuchsnummer"]) for r in rows if r.get("Versuchsnummer") is not None]
    if nos:
        cur.execute("SELECT Versuchsnummer FROM tblTrial WHERE TrialSeriesID = ? "
                    f"AND Versuchsnummer IN ({','.join(['?'] * len(nos))})", [series_id] + nos)
        taken = sorted({int(r[0]) for r in cur.fetchall() or []})
        if taken:
            from db.trial_reference import format_number_list
            raise RecycleBinError("These trial numbers are used again in the series: "
                                  + format_number_list(taken) + " - nothing was restored.")


def delete_permanently(bin_id: int) -> None:
    from db.connection import execute
    execute("DELETE FROM tblRecycleBin WHERE ID = ?", [int(bin_id)])
