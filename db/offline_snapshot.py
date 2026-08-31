"""Snapshot pull: copies rows from MySQL (whichever backend the current
session is running against - prod when launched normally, see
db.offline_schema._ALLOWED_SOURCE_MODE) into the local offline SQLite file.
Pure pull direction (MySQL -> SQLite), independent of the later merge step
(SQLite -> MySQL for newly created rows, which stays hard-restricted to
dev_local regardless of the pull source - see pull_snapshot()'s
merge_target_mode parameter and db/offline_merge.py's module docstring).

PoC simplification: copies EVERY row of all OFFLINE_TABLES (no filtering by
e.g. "only the last N months" or similar) - unproblematic at dev_local's
size (~2.8s for ~110k rows). Against prod (real network, not localhost) this
is unmeasured - scoping this down would be a sensible next step if it turns
out too slow, but isn't built yet.
"""

from __future__ import annotations

import datetime
import decimal
from typing import Any, Dict, List

from db.offline_schema import build_offline_schema, get_offline_table_closure, _ALLOWED_SOURCE_MODE


_META_TABLE = "_offline_meta"


def get_snapshot_source_mode(sqlite_path: str | None = None) -> str | None:
    """Which MySQL mode (prod/dev/dev_local) this offline copy was last
    pulled from, stamped by pull_snapshot() below. None if the file has
    never been pulled, or pre-dates this stamp (older local copy).

    This is how offline_merge.py decides where to write offline changes
    back to - explicit user decision (2026-08-13): merge must write to the
    SAME backend the snapshot actually came from, not a separately
    hardcoded guess that could silently drift out of sync with it (e.g. a
    snapshot pulled from prod must merge back into prod, not dev_local).
    """
    from db.connection import raw_sqlite_connect

    with raw_sqlite_connect(sqlite_path) as cn:
        cur = cn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (_META_TABLE,))
        if not cur.fetchone():
            return None
        cur.execute(f'SELECT source_mode FROM "{_META_TABLE}" LIMIT 1')
        row = cur.fetchone()
        return row[0] if row else None


class UnmergedChangesError(RuntimeError):
    """Raised by pull_snapshot() when refreshing would silently destroy local
    offline work (new or edited rows not yet merged into the target).

    Carries `at_risk: {table: count}` (see offline_merge.find_unmerged_local_changes)
    so callers/UI can show exactly what would be lost, and offer merging
    first or an explicit force=True to discard it deliberately.
    """

    def __init__(self, at_risk: Dict[str, int]):
        self.at_risk = at_risk
        total = sum(at_risk.values())
        super().__init__(
            f"Refusing to refresh the offline copy: {total} row(s) across "
            f"{len(at_risk)} table(s) are new or edited offline and not yet "
            f"merged - refreshing now would silently discard them. Merge "
            f"first, or call pull_snapshot(force=True) to discard them "
            f"deliberately. Detail: {at_risk}"
        )


def _sanitize_value(v: Any) -> Any:
    """Converts MySQL-connector values into SQLite-compatible Python types."""
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (datetime.datetime, datetime.date, datetime.time)):
        return v.isoformat()
    return v


def _fetch_mysql_rows(table: str, source_mode: str, _conn=None) -> tuple[List[str], List[tuple]]:
    from db.connection import raw_mysql_connect

    cn = _conn or raw_mysql_connect(source_mode)
    try:
        cur = cn.cursor()
        cur.execute(f"SELECT * FROM `{table}`")
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        cur.close()
    finally:
        if _conn is None:
            cn.close()
    return cols, rows


def pull_snapshot(
    tables: List[str] | None = None,
    source_mode: str = _ALLOWED_SOURCE_MODE,
    ensure_schema: bool = True,
    sqlite_path: str | None = None,
    force: bool = False,
) -> Dict[str, int]:
    """Fills the local offline SQLite file with rows from MySQL (source_mode).

    Targets the offline file via raw_sqlite_connect(), INDEPENDENT of the
    currently active TRIPPLET_MODE - meant to be called from a normal online
    session, which is the realistic "prepare offline copy" flow. `source_mode`
    defaults to whichever backend the current process is actually running
    against (prod when launched normally) - explicit user decision
    (2026-08-13): a snapshot pulled from a different mode than the one you're
    actually running against would be stale/pointless for real offline work.
    Clears the affected tables first (DELETE, not DROP - schema stays), so a
    repeated snapshot pull is idempotent - PROVIDED there's no unmerged
    offline work sitting in them (see UnmergedChangesError below).

    On success, stamps the file with `source_mode` (see get_snapshot_source_mode())
    so offline_merge.py knows which backend to write changes back to later,
    without a separately hardcoded (and potentially out-of-sync) guess.

    The unmerged-changes safety check below deliberately checks against the
    EXISTING file's current stamp (i.e. wherever the PREVIOUS pull came from,
    which is also where a not-yet-run merge would write to) - NOT against the
    new `source_mode` about to be pulled. A first-ever pull (no stamp yet)
    always proceeds, since there's nothing in the file yet to risk losing.

    Unless `force=True`, refuses to run (raises UnmergedChangesError) if the
    existing local file has new or edited ROOT_TABLES rows not yet merged -
    otherwise a second "Prepare/refresh" click before merging would silently
    wipe any offline work in progress via the DELETE+INSERT below.

    Returns: {table: rows_copied}
    """
    from db.connection import raw_sqlite_connect, raw_mysql_connect
    from db.offline_merge import find_unmerged_local_changes

    if tables is None:
        tables, _ = get_offline_table_closure(source_mode=source_mode)

    if not force:
        existing_stamp = get_snapshot_source_mode(sqlite_path) or source_mode
        at_risk = find_unmerged_local_changes(target_mode=existing_stamp, source_mode=source_mode, sqlite_path=sqlite_path)
        if at_risk:
            raise UnmergedChangesError(at_risk)

    # One MySQL connection reused for schema introspection AND row fetching
    # across all tables, instead of ~2 fresh TCP+auth handshakes per table -
    # barely matters on localhost/dev_local, but would add up meaningfully
    # once source_mode targets a real network (prod).
    mysql_conn = raw_mysql_connect(source_mode)
    try:
        if ensure_schema:
            build_offline_schema(
                tables=tables, source_mode=source_mode, sqlite_path=sqlite_path, _mysql_conn=mysql_conn,
            )

        stats: Dict[str, int] = {}
        with raw_sqlite_connect(sqlite_path) as cn:
            cur = cn.cursor()
            # get_connection()/raw_sqlite_connect() use isolation_level=None
            # (autocommit) to match the MySQL pool's autocommit=True - correct
            # for normal single-statement app usage, but it means each row of
            # a bulk executemany() becomes its own disk-synced transaction if
            # left unguarded (profiled: 75 of 79s total pull time was inside
            # sqlite3.Cursor.executemany() alone, dominated by tbltrial's ~12k
            # rows). Wrapping the whole pull in one explicit transaction turns
            # ~13,000 fsyncs into one.
            cur.execute("BEGIN")
            for t in tables:
                cur.execute(f'DELETE FROM "{t}"')

                mysql_cols, rows = _fetch_mysql_rows(t, source_mode, _conn=mysql_conn)
                if not rows:
                    stats[t] = 0
                    continue

                placeholders = ",".join(["?"] * len(mysql_cols))
                col_list = ",".join(f'"{c}"' for c in mysql_cols)
                insert_sql = f'INSERT INTO "{t}" ({col_list}) VALUES ({placeholders})'

                sanitized = [tuple(_sanitize_value(v) for v in row) for row in rows]
                cur.executemany(insert_sql, sanitized)
                stats[t] = len(sanitized)

            # Stamp which backend this pull actually came from (see
            # get_snapshot_source_mode()) - same transaction as the data
            # above, so a failed/rolled-back pull never leaves a stale stamp.
            cur.execute(
                f'CREATE TABLE IF NOT EXISTS "{_META_TABLE}" '
                f'(source_mode TEXT NOT NULL, pulled_at TEXT NOT NULL)'
            )
            cur.execute(f'DELETE FROM "{_META_TABLE}"')
            cur.execute(
                f'INSERT INTO "{_META_TABLE}" (source_mode, pulled_at) VALUES (?, ?)',
                (source_mode, datetime.datetime.utcnow().isoformat()),
            )
            cn.commit()
    finally:
        mysql_conn.close()

    return stats
