"""Merge tool: writes rows created OR edited offline in the local SQLite copy
back into MySQL. Opposite direction of offline_snapshot.pull_snapshot()
(MySQL -> SQLite).

Two categories of rows get pushed:
  - "new": GlobalID doesn't exist yet in the target -> INSERT.
  - "changed": GlobalID already exists in the target, but the row was edited
    offline after the snapshot was taken (see offline_schema.LOCAL_TRACKING_COLUMN,
    stamped by a local SQLite trigger) -> UPDATE, unconditionally overwriting
    whatever's currently in the target. This is a deliberate "whoever merges
    last wins" policy, not a real conflict-detection scheme - reasonable given
    how few concurrent offline users there are; not worth building more for.

FK columns are resolved differently depending on which table they reference:
  - ROOT_TABLES (can themselves contain new/changed offline rows, see
    offline_schema.ROOT_TABLES): resolved via GlobalID indirection, because
    local IDs can change when inserted into the target (MySQL assigns a new
    AUTO_INCREMENT ID on INSERT; on UPDATE the row already has a stable target
    ID, but the FK VALUE being written might itself point at another
    just-inserted row).
  - everything else (pure reference/lookup data, not offline-creatable):
    1:1 ID identity, because offline_snapshot.pull_snapshot() copies MySQL
    IDs unchanged into the SQLite copy (no autoincrement during the snapshot
    pull, real INSERT values including the ID column).

The mergeable table list and FK map are derived from the same FK-graph
discovery as offline_schema.compute_dependency_closure(), not hand-maintained
- see get_merge_plan_inputs() below.

NEVER run write operations against target_mode='prod' without explicit user
confirmation - see the plan_merge()/execute_merge() split.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from db.offline_schema import (
    ROOT_TABLES, compute_dependency_closure, _ALLOWED_SOURCE_MODE, LOCAL_TRACKING_COLUMN,
)

_NON_MYSQL_COLUMNS = {"ID", LOCAL_TRACKING_COLUMN}


def get_merge_plan_inputs(source_mode: str = _ALLOWED_SOURCE_MODE) -> Tuple[List[str], Dict[str, Dict[str, str]]]:
    """Dependency-ordered ROOT_TABLES (the tables that can receive new/changed
    offline rows) plus the full FK map for the whole closure (needed to resolve
    FK columns on those tables, including ones pointing at reference-only tables).
    """
    closure_order, fk_map = compute_dependency_closure(ROOT_TABLES, source_mode=source_mode)
    root_set = set(ROOT_TABLES)
    mergeable_ordered = [t for t in closure_order if t in root_set]
    return mergeable_ordered, fk_map


def _read_sqlite_rows(table: str, sqlite_path: str | None = None) -> List[Dict[str, Any]]:
    """Reads all rows of the table from the local offline SQLite file.

    Uses raw_sqlite_connect(), INDEPENDENT of the currently active
    TRIPPLET_MODE - merging typically runs from a later online session,
    reading a file written by a separate, earlier offline session.
    """
    from db.connection import raw_sqlite_connect

    with raw_sqlite_connect(sqlite_path) as cn:
        cur = cn.cursor()
        cur.execute(f'SELECT * FROM "{table}"')
        cols = [c[0] for c in cur.description]
        rows = cur.fetchall()
        return [dict(zip(cols, r)) for r in rows]


def _mysql_globalid_to_id(table: str, target_mode: str) -> Dict[str, int]:
    """{GlobalID: ID} for all rows with a GlobalID set in the MySQL target."""
    from db.connection import raw_mysql_connect

    cn = raw_mysql_connect(target_mode)
    try:
        cur = cn.cursor()
        cur.execute(f"SELECT ID, GlobalID FROM `{table}` WHERE GlobalID IS NOT NULL")
        rows = cur.fetchall()
        cur.close()
    finally:
        cn.close()
    return {gid: id_ for id_, gid in rows if gid}


def find_unmerged_local_changes(
    target_mode: str,
    tables: Optional[List[str]] = None,
    source_mode: str = _ALLOWED_SOURCE_MODE,
    sqlite_path: str | None = None,
) -> Dict[str, int]:
    """Rows in the local offline copy that a naive DELETE+INSERT refresh
    (offline_snapshot.pull_snapshot()) would silently destroy: locally
    created rows not yet merged (GlobalID not yet known to target) and
    locally edited rows not yet merged (LOCAL_TRACKING_COLUMN set).

    Returns {table: count_at_risk}, empty if nothing would be lost. Used as a
    safety gate before pull_snapshot() wipes and re-populates ROOT_TABLES -
    without this, clicking "Prepare/refresh" a second time before merging
    silently discards any offline work in progress.
    """
    from db.connection import raw_sqlite_connect

    if tables is None:
        tables, _ = get_merge_plan_inputs(source_mode=source_mode)

    at_risk: Dict[str, int] = {}
    with raw_sqlite_connect(sqlite_path) as cn:
        cur = cn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {r[0] for r in cur.fetchall()}

        for t in tables:
            if t not in existing_tables:
                continue  # nothing pulled yet for this table - nothing to lose
            target_gids = set(_mysql_globalid_to_id(t, target_mode).keys())

            # A table just promoted to ROOT_TABLES may still be missing
            # LOCAL_TRACKING_COLUMN in an older local file (pre-migration -
            # see build_offline_schema()'s ALTER TABLE step, which only runs
            # later, when pull_snapshot() actually proceeds). Referencing a
            # nonexistent quoted column in a SELECT list doesn't error in
            # SQLite - it silently falls back to treating it as a STRING
            # LITERAL, which is truthy for every row and would flag the
            # entire table as "at risk". Guard against that explicitly
            # rather than trusting the query to fail loudly.
            cur.execute(f'PRAGMA table_info("{t}")')
            has_tracking_col = any(r[1] == LOCAL_TRACKING_COLUMN for r in cur.fetchall())

            if has_tracking_col:
                cur.execute(f'SELECT "GlobalID", "{LOCAL_TRACKING_COLUMN}" FROM "{t}"')
                rows = [(gid, bool(touched)) for gid, touched in cur.fetchall()]
            else:
                cur.execute(f'SELECT "GlobalID" FROM "{t}"')
                rows = [(gid, False) for (gid,) in cur.fetchall()]

            n_at_risk = 0
            for gid, touched in rows:
                if not gid:
                    continue
                if gid not in target_gids or touched:
                    n_at_risk += 1
            if n_at_risk:
                at_risk[t] = n_at_risk
    return at_risk


class MergePlan:
    """Result of plan_merge(): per table, the rows that would be inserted or updated."""

    def __init__(self, tables: List[str]) -> None:
        self.tables = tables
        self.new_rows: Dict[str, List[Dict[str, Any]]] = {}
        self.changed_rows: Dict[str, List[Dict[str, Any]]] = {}
        self.unchanged_count: Dict[str, int] = {}

    def summary(self) -> str:
        lines = []
        for t in self.tables:
            n_new = len(self.new_rows.get(t, []))
            n_changed = len(self.changed_rows.get(t, []))
            n_unchanged = self.unchanged_count.get(t, 0)
            lines.append(f"{t}: {n_new} new, {n_changed} changed, {n_unchanged} unchanged")
        return "\n".join(lines)

    def is_empty(self) -> bool:
        return all(
            not self.new_rows.get(t) and not self.changed_rows.get(t)
            for t in self.tables
        )


def plan_merge(target_mode: str, tables: Optional[List[str]] = None,
               source_mode: str = _ALLOWED_SOURCE_MODE,
               sqlite_path: str | None = None) -> MergePlan:
    """Dry run: determines which rows would be inserted/updated - writes nothing."""
    if tables is None:
        tables, _ = get_merge_plan_inputs(source_mode=source_mode)
    plan = MergePlan(tables)
    for t in tables:
        target_gid_to_id = _mysql_globalid_to_id(t, target_mode)
        rows = _read_sqlite_rows(t, sqlite_path)
        new_rows = []
        changed_rows = []
        n_unchanged = 0
        for r in rows:
            gid = r.get("GlobalID")
            if not gid:
                continue
            if gid not in target_gid_to_id:
                new_rows.append(r)
            elif r.get(LOCAL_TRACKING_COLUMN):
                changed_rows.append(r)
            else:
                n_unchanged += 1
        plan.new_rows[t] = new_rows
        plan.changed_rows[t] = changed_rows
        plan.unchanged_count[t] = n_unchanged
    return plan


def execute_merge(target_mode: str, plan: Optional[MergePlan] = None,
                   tables: Optional[List[str]] = None,
                   source_mode: str = _ALLOWED_SOURCE_MODE,
                   sqlite_path: str | None = None) -> Dict[str, Dict[str, int]]:
    """Actually writes the new/changed rows from plan_merge() into the MySQL target.

    A single transaction across all tables - if one write fails, everything
    is rolled back (no half-merged state in the target). On success, clears
    LOCAL_TRACKING_COLUMN in the local SQLite copy for every row that was
    pushed as "changed", so a repeated plan_merge() doesn't report it again.

    Returns: {table: {"inserted": n, "updated": n}}
    """
    from db.connection import raw_mysql_connect, raw_sqlite_connect

    root_ordered, fk_map = get_merge_plan_inputs(source_mode=source_mode)
    tables = tables or root_ordered
    root_set = set(root_ordered)
    plan = plan or plan_merge(target_mode, tables, source_mode=source_mode, sqlite_path=sqlite_path)

    # local_globalid[table][local_id] = GlobalID (from the SQLite source)
    local_globalid: Dict[str, Dict[Any, str]] = {}
    for t in tables:
        rows = _read_sqlite_rows(t, sqlite_path)
        local_globalid[t] = {r["ID"]: r["GlobalID"] for r in rows if r.get("GlobalID")}

    # target_id_by_globalid[table][GlobalID] = ID in the target (extended as the merge proceeds)
    target_id_by_globalid: Dict[str, Dict[str, int]] = {
        t: _mysql_globalid_to_id(t, target_mode) for t in tables
    }

    def resolve_fk(fk_table: str, local_fk_id: Any) -> Any:
        if local_fk_id is None:
            return None
        if fk_table in root_set:
            local_gid = local_globalid.get(fk_table, {}).get(local_fk_id)
            if local_gid is None:
                raise RuntimeError(
                    f"FK resolution failed: {fk_table} ID={local_fk_id} has no GlobalID in the offline copy."
                )
            target_id = target_id_by_globalid.get(fk_table, {}).get(local_gid)
            if target_id is None:
                raise RuntimeError(
                    f"FK resolution failed: {fk_table} GlobalID={local_gid} not yet in the target "
                    f"(wrong merge order? {fk_table} must be merged before its children)."
                )
            return target_id
        # Reference/lookup table: snapshot copies IDs 1:1, so identity applies.
        return local_fk_id

    cn = raw_mysql_connect(target_mode)
    stats: Dict[str, Dict[str, int]] = {}
    merged_changed_globalids: Dict[str, List[str]] = {}
    try:
        cur = cn.cursor()
        for t in tables:
            fk_cols = fk_map.get(t, {})
            n_inserted = 0
            n_updated = 0
            merged_changed_globalids[t] = []

            for row in plan.new_rows.get(t, []):
                cols = [c for c in row.keys() if c not in _NON_MYSQL_COLUMNS]
                vals = [resolve_fk(fk_cols[c], row[c]) if c in fk_cols else row[c] for c in cols]
                col_sql = ", ".join(f"`{c}`" for c in cols)
                ph = ", ".join(["%s"] * len(cols))
                cur.execute(f"INSERT INTO `{t}` ({col_sql}) VALUES ({ph})", vals)
                new_id = cur.lastrowid
                target_id_by_globalid.setdefault(t, {})[row["GlobalID"]] = new_id
                n_inserted += 1

            for row in plan.changed_rows.get(t, []):
                cols = [c for c in row.keys() if c not in _NON_MYSQL_COLUMNS and c != "GlobalID"]
                vals = [resolve_fk(fk_cols[c], row[c]) if c in fk_cols else row[c] for c in cols]
                set_sql = ", ".join(f"`{c}`=%s" for c in cols)
                cur.execute(f"UPDATE `{t}` SET {set_sql} WHERE `GlobalID`=%s", vals + [row["GlobalID"]])
                n_updated += 1
                merged_changed_globalids[t].append(row["GlobalID"])

            stats[t] = {"inserted": n_inserted, "updated": n_updated}
        cn.commit()
    except Exception:
        cn.rollback()
        raise
    finally:
        cn.close()

    # Only reached on a successful commit - clear the local dirty flag for
    # every row just pushed, so a repeated plan_merge() sees it as unchanged.
    with raw_sqlite_connect(sqlite_path) as local_cn:
        local_cur = local_cn.cursor()
        for t, gids in merged_changed_globalids.items():
            for gid in gids:
                local_cur.execute(
                    f'UPDATE "{t}" SET "{LOCAL_TRACKING_COLUMN}" = NULL WHERE "GlobalID" = ?', (gid,)
                )

    return stats
