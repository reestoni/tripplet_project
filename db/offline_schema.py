"""Offline schema generator: derives the SQLite DDL for the offline copy from
the MySQL schema (SHOW COLUMNS), instead of hand-building ~90-column tables
like tblTrial. Introspection source follows whichever MySQL backend the
current process is actually running against (db.connection.MODE - prod, dev,
or dev_local) - see raw_mysql_connect() in db/connection.py, which can open
its own MySQL connection to an arbitrary mode independent of the currently
active TRIPPLET_MODE. Explicit user decision (2026-08-13): "Prepare/refresh"
in the compiled .exe normally runs against prod, so the snapshot must be
pulled from prod there too - a snapshot sourced from dev_local would be
stale/pointless for real offline work. This only affects the READ/pull
direction (schema introspection + row copy); the WRITE/merge direction
(offline_merge.py's target_mode) is a separate, still-restricted decision -
see its own module docstring.

Deliberate simplification for the offline copy: no FOREIGN KEY constraints in
the generated DDL (only PRIMARY KEY). The offline file is a local working
copy for a single user, not an integrity authority - enforcing FKs would only
complicate snapshot-fill ordering without real benefit (the merge back into
MySQL remains the instance that actually enforces FK integrity).

ROOT_TABLES are the entities the user can actually create new rows for
offline (currently: yarns, jets, trial series, trials, ATY lab results).
Everything else needed to support them (manufacturers, materials, process
types, ...) is discovered automatically by walking the real FK graph in
information_schema.KEY_COLUMN_USAGE (compute_dependency_closure()) rather
than hand-maintained - tblJets alone pulls in ~11 reference tables
(Hersteller, Serie, Airchannelshape, ...), enumerating that by hand would
drift out of sync with schema changes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from db.connection import MODE as _CURRENT_MODE

# Entities the user can create brand-new rows for while offline. Everything
# else in OFFLINE_TABLES is pulled in transitively as read-only reference/
# lookup data via compute_dependency_closure().
ROOT_TABLES: List[str] = [
    "tblyarn",
    "tbljets",
    "tbltrialseries",
    "tbltrial",
    "tbllaboratyomat",
    # The other per-lab-machine result tables ShowExperimentScreen builds a
    # tab for (see the _ensure_*_tab/_build_*_tab pairs) - user explicitly
    # wants these editable+mergeable offline, not just viewable, same as ATY.
    "tbllabortiter",
    "tbllaborstatimatm",
    "tbllaborstatimatds",
    "tbllaborekb",
    "tbllaboritematlab",
    "tbllaboritematplus",
    "tbllabordtyomat",
    "tbllaborrapid600",
    "tbllaborjetairconsumption",
    "tbllaborheissluftschrumpf",
    "tbllaborkochschrumpf",
    "tbllaboratyshrinkage",
    "tbllaborwaterbath",
    # Ply-specific settings, entered via CreateExperimentScreen or copied on
    # trial-clone (_clone_trial_settings_rows()) - has a real declared FK on
    # TrialID (unlike the 13 lab tables above), no MANUAL_FK_EDGES needed.
    # Was reference-only (EXTRA_REFERENCE_TABLES) until the user reported it
    # not round-tripping - Ply settings entered for a trial created offline
    # in the same session were never merged at all (only ROOT_TABLES rows
    # get pushed back), so they were permanently stuck locally.
    "tbltrialsettings",
]

# Some legacy lab tables reference tbltrial by column-naming convention
# ("TrialID") WITHOUT a declared FK constraint - unlike tblLaborATYoMat,
# which does have one. information_schema.KEY_COLUMN_USAGE won't surface
# these (confirmed by checking each table's actual FK constraints, not
# assumed), so compute_dependency_closure()'s fk_map would never know to
# GlobalID-remap TrialID during merge, silently corrupting it for any lab
# result attached to a trial that was ALSO created offline in the same
# session. Injected manually here, merged into the real FK edges in
# fetch_fk_edges(). tbllaborjetairconsumption is excluded - it has a real
# declared FK on TrialSeriesID instead, no TrialID column at all.
MANUAL_FK_EDGES: Dict[str, Dict[str, str]] = {
    t: {"TrialID": "tbltrial"}
    for t in (
        "tbllabortiter", "tbllaborstatimatm", "tbllaborstatimatds", "tbllaborekb",
        "tbllaboritematlab", "tbllaboritematplus", "tbllabordtyomat", "tbllaborrapid600",
        "tbllaborheissluftschrumpf", "tbllaborkochschrumpf", "tbllaboratyshrinkage",
        "tbllaborwaterbath",
    )
}

# Tables real screen code depends on that compute_dependency_closure() can't
# discover on its own: the FK-graph walk only finds tables REACHABLE FROM
# ROOT_TABLES by following "X references Y" edges outward - it can't find a
# table that nothing in the closure points AT, even if that table itself
# points back INTO the closure (tblmachinefields.MachineID -> tblmaschine is
# a real, declared FK, but nothing in ROOT_TABLES references
# tblmachinefields itself, so it's otherwise invisible to the walk).
# Found by actually exercising offline screens (CreateExperimentScreen's
# per-machine dynamic field layout), not guessed - see CLAUDE.md. Added as
# extra BFS seeds (still pure reference data, never "mergeable" - see
# ROOT_TABLES vs. this list in offline_merge.get_merge_plan_inputs()).
EXTRA_REFERENCE_TABLES: List[str] = [
    "tblmachinefields",
    "tbllabmachines",
    "tblproject",
    # BacklogScreen's main query LEFT JOINs these to flag "has image"/"has
    # PDF" per series (screen_backlog.py::_load_status_into()) - missing
    # tables there aren't graceful: the query itself throws, caught by a
    # blanket except that silently returns an empty result set, making a
    # working Backlog look like an EMPTY one instead of erroring (found by
    # actually reloading the screen and comparing row counts against
    # dev_local, not by reading the exception path and assuming). Offline
    # image/PDF upload itself stays out of scope - view-only is enough to
    # unblock the query.
    "tbltrialseriesimage",
    "tbltrialseriespdf",
    # Retest flags (db/retest_flags.py) already no-op gracefully via
    # table_exists() when absent, but including it lets Backlog show the
    # actual flag badges offline instead of silently hiding them.
    "tbltrialretestflag",
    # Login itself (check_credentials()/get_user_password_hash() in
    # db/connection.py) queries tblUser via get_connection() like everything
    # else - without it here, nobody can even reach the login screen while
    # genuinely disconnected (no online round-trip first). Pure reference
    # data, deliberately NOT mergeable: an offline password/profile edit
    # must never silently overwrite the row on merge. tblUser.AccessRights
    # is a real declared FK to tblaccessright, so that table is pulled in
    # automatically by the closure walk - no separate entry needed here.
    "tbluser",
]

# Real MySQL modes that raw_mysql_connect() can actually reach (excludes
# "offline" - there's no MySQL to introspect while already offline; passing
# it fails naturally in raw_mysql_connect() anyway, mode not in _SECRETS).
# Default source_mode follows whichever backend the CURRENT process is
# connected to (prod when launched normally, dev_local when launched with
# TRIPPLET_MODE=dev_local, ...) - a snapshot pulled from a different mode
# than the one you're actually running against would be stale/pointless for
# real offline work. offline_merge.py's target_mode (the WRITE direction) is
# a separate, still-restricted decision and explicitly passes its own
# source_mode - see its module docstring - so callers there are unaffected
# by this default and validated the same way (must be a real MySQL mode).
_VALID_MYSQL_MODES = {"prod", "dev", "dev_local"}
_ALLOWED_SOURCE_MODE = _CURRENT_MODE


def fetch_fk_edges(source_mode: str = _ALLOWED_SOURCE_MODE) -> Dict[str, Dict[str, str]]:
    """{table: {column: referenced_table}} for the given MySQL backend's schema.

    Single query against information_schema.KEY_COLUMN_USAGE - cheap, so no
    caching here; callers that need it repeatedly can cache themselves.
    """
    if source_mode not in _VALID_MYSQL_MODES:
        raise ValueError(
            f"Schema introspection only allowed against a real MySQL mode "
            f"{sorted(_VALID_MYSQL_MODES)}, not '{source_mode}'."
        )
    from db.connection import raw_mysql_connect

    cn = raw_mysql_connect(source_mode)
    try:
        cur = cn.cursor(dictionary=True)
        cur.execute(
            "SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME "
            "FROM information_schema.KEY_COLUMN_USAGE "
            "WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL",
            (cn.database,),
        )
        rows = cur.fetchall()
        cur.close()
    finally:
        cn.close()

    edges: Dict[str, Dict[str, str]] = {}
    for r in rows:
        t = r["TABLE_NAME"].lower()
        edges.setdefault(t, {})[r["COLUMN_NAME"]] = r["REFERENCED_TABLE_NAME"].lower()

    # Merge in undeclared-but-real FKs (see MANUAL_FK_EDGES docstring) -
    # never overrides a real declared edge, only fills gaps.
    for t, cols in MANUAL_FK_EDGES.items():
        merged = dict(cols)
        merged.update(edges.get(t, {}))
        edges[t] = merged

    return edges


def compute_dependency_closure(
    root_tables: List[str],
    source_mode: str = _ALLOWED_SOURCE_MODE,
) -> Tuple[List[str], Dict[str, Dict[str, str]]]:
    """Walks the FK graph outward from root_tables and returns a dependency-ordered
    table list (referenced tables before the tables that reference them) plus
    the FK map for exactly those tables.

    Cycle-safe (e.g. tblsmartchartaxis.SubAxisID self-references) via the
    temp-mark guard in the DFS below, even though no cycle currently exists
    within the closure reachable from ROOT_TABLES.
    """
    all_edges = fetch_fk_edges(source_mode=source_mode)

    fk_map: Dict[str, Dict[str, str]] = {}
    visited: Set[str] = set()
    stack = list(root_tables)
    while stack:
        t = stack.pop()
        if t in visited:
            continue
        visited.add(t)
        edges = all_edges.get(t, {})
        fk_map[t] = edges
        for ref_table in edges.values():
            if ref_table not in visited:
                stack.append(ref_table)

    order: List[str] = []
    temp_mark: Set[str] = set()
    perm_mark: Set[str] = set()

    def visit(node: str) -> None:
        if node in perm_mark or node in temp_mark:
            return
        temp_mark.add(node)
        for ref in fk_map.get(node, {}).values():
            visit(ref)
        temp_mark.discard(node)
        perm_mark.add(node)
        order.append(node)

    for t in visited:
        visit(t)

    return order, fk_map


def get_offline_table_closure(
    source_mode: str = _ALLOWED_SOURCE_MODE,
) -> Tuple[List[str], Dict[str, Dict[str, str]]]:
    """Full set of tables to create/populate in the offline copy: ROOT_TABLES'
    FK closure plus EXTRA_REFERENCE_TABLES. This is what build_offline_schema()/
    pull_snapshot() default to - NOT the same as offline_merge.get_merge_plan_inputs(),
    which filters this down to just ROOT_TABLES for merge-target eligibility.
    """
    return compute_dependency_closure(ROOT_TABLES + EXTRA_REFERENCE_TABLES, source_mode=source_mode)


def mysql_type_to_sqlite(mysql_type: str) -> str:
    """Maps a MySQL column type (from SHOW COLUMNS) to a SQLite type affinity."""
    t = (mysql_type or "").lower()
    if any(t.startswith(p) for p in ("int", "tinyint", "smallint", "mediumint", "bigint", "year")):
        return "INTEGER"
    if any(t.startswith(p) for p in ("decimal", "float", "double", "numeric")):
        return "REAL"
    if any(t.startswith(p) for p in ("blob", "binary", "varbinary")):
        return "BLOB"
    # datetime/date/time/timestamp/varchar/char/text/enum/... -> TEXT
    return "TEXT"


def fetch_mysql_columns(table: str, source_mode: str = _ALLOWED_SOURCE_MODE, _conn=None) -> List[Dict[str, Any]]:
    """SHOW COLUMNS FROM <table> against the current session's MySQL backend.

    Uses its own raw connection (see raw_mysql_connect), independent of
    get_connection()/the pooled connection - this is only ever called from an
    online process (pull_snapshot() is a "prepare while online" step, run
    before the separate offline-mode process start), never while the process
    itself is actually running with TRIPPLET_MODE=offline.

    `_conn`: reuse an already-open raw_mysql_connect() instead of opening (and
    closing) a fresh one - build_offline_schema()/pull_snapshot() call this
    once per table, and against a real network (not localhost) 31 separate
    TCP+auth handshakes add up (profiled: dominant remaining cost after fixing
    the SQLite transaction-per-row issue, see offline_snapshot.pull_snapshot).
    Internal parameter, not part of the stable public API.
    """
    if source_mode not in _VALID_MYSQL_MODES:
        raise ValueError(
            f"Schema introspection only allowed against a real MySQL mode "
            f"{sorted(_VALID_MYSQL_MODES)}, not '{source_mode}'."
        )
    from db.connection import raw_mysql_connect

    cn = _conn or raw_mysql_connect(source_mode)
    try:
        cur = cn.cursor(dictionary=True)
        cur.execute(f"SHOW COLUMNS FROM `{table}`")
        rows = cur.fetchall()
        cur.close()
    finally:
        if _conn is None:
            cn.close()

    out = []
    for r in rows:
        out.append({
            "name": r["Field"],
            "mysql_type": r["Type"],
            "nullable": r["Null"] == "YES",
            "is_pk": r["Key"] == "PRI",
            "is_autoincrement": "auto_increment" in (r["Extra"] or ""),
        })
    return out


# Local-only column (never exists in MySQL, never sent there): stamped by
# generate_update_trigger_sql()'s trigger whenever a mergeable row already
# present at snapshot time gets edited offline. Lets the merge tool detect
# "this pre-existing row needs pushing back" without requiring a Timestamp
# column in MySQL - most ROOT_TABLES don't have one (only tbltrial and
# tbllaboratyomat do; tblyarn/tbljets/tbltrialseries don't).
LOCAL_TRACKING_COLUMN = "_offline_modified_at"


def generate_create_table_sql(table: str, columns: List[Dict[str, Any]], track_edits: bool = False) -> str:
    """Builds a SQLite CREATE TABLE statement from the (MySQL-sourced) columns.

    track_edits=True (only for ROOT_TABLES) adds the local-only
    LOCAL_TRACKING_COLUMN, populated by the trigger from
    generate_update_trigger_sql() - never part of the MySQL column list, so
    pull_snapshot()'s explicit INSERT column list naturally leaves it NULL.
    """
    col_defs = []
    for c in columns:
        name = c["name"]
        if c["is_pk"] and c["is_autoincrement"]:
            col_defs.append(f'"{name}" INTEGER PRIMARY KEY AUTOINCREMENT')
            continue
        sqlite_type = mysql_type_to_sqlite(c["mysql_type"])
        suffix = " PRIMARY KEY" if c["is_pk"] else ""
        col_defs.append(f'"{name}" {sqlite_type}{suffix}')
    if track_edits:
        col_defs.append(f'"{LOCAL_TRACKING_COLUMN}" TEXT')
    cols_sql = ",\n  ".join(col_defs)
    return f'CREATE TABLE IF NOT EXISTS "{table}" (\n  {cols_sql}\n)'


def generate_update_trigger_sql(table: str) -> str:
    """AFTER UPDATE trigger that stamps LOCAL_TRACKING_COLUMN whenever an
    already-existing row is edited offline.

    Deliberately NOT an AFTER INSERT trigger: pull_snapshot() re-inserts every
    row on each refresh via DELETE+INSERT, which would otherwise mark the
    whole table "modified" right after a clean sync. A brand-new row created
    offline doesn't need this flag either - it's already detected as new via
    an absent GlobalID in the merge target, regardless of this column.

    WHEN NEW.<tracking> IS OLD.<tracking>: only re-stamp when the UPDATE did
    NOT itself touch the tracking column. A normal field edit leaves it
    untouched (NEW == OLD), so the trigger fires and stamps it. offline_merge's
    post-merge cleanup explicitly sets it to NULL (NEW != OLD), so the WHEN
    guard skips firing - without this, that cleanup UPDATE would immediately
    re-stamp the very flag it's trying to clear. This also makes the trigger
    naturally recursion-safe on its own (the trigger's own bookkeeping UPDATE
    changes the tracking column, so it fails its own WHEN check on any nested
    re-evaluation) - PRAGMA recursive_triggers = OFF (see
    db.connection._get_sqlite_connection) is kept as defense in depth, not as
    the thing actually preventing recursion.
    """
    return (
        f'CREATE TRIGGER IF NOT EXISTS "trg_{table}_touch" '
        f'AFTER UPDATE ON "{table}" '
        f'WHEN NEW."{LOCAL_TRACKING_COLUMN}" IS OLD."{LOCAL_TRACKING_COLUMN}" '
        f"BEGIN "
        f'UPDATE "{table}" SET "{LOCAL_TRACKING_COLUMN}" = strftime(\'%Y-%m-%dT%H:%M:%f\', \'now\') '
        f"WHERE rowid = NEW.rowid; "
        f"END"
    )


def build_offline_schema(
    tables: List[str] | None = None,
    source_mode: str = _ALLOWED_SOURCE_MODE,
    sqlite_path: str | None = None,
    _mysql_conn=None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Creates the offline table set in the local offline SQLite file.

    Targets the offline file via raw_sqlite_connect(), INDEPENDENT of the
    currently active TRIPPLET_MODE - this can run while the process itself is
    online (dev_local/prod), which is the realistic "prepare offline copy"
    flow (see db.connection.raw_sqlite_connect() docstring). The column
    structure is read over a dev_local connection (fetch_mysql_columns).
    If `tables` isn't given, the full dependency closure from ROOT_TABLES is
    computed and used. `sqlite_path` overrides the default offline file
    (mainly for tests).

    `_mysql_conn`: reuse an already-open raw_mysql_connect() across all tables
    instead of opening one per SHOW COLUMNS call (internal parameter, used by
    pull_snapshot() - see fetch_mysql_columns() docstring for why this matters
    once source_mode targets a real network instead of localhost).

    Returns: {table: [columns]} - reusable for the subsequent snapshot fill,
    so SHOW COLUMNS doesn't run twice.
    """
    from db.connection import raw_sqlite_connect, raw_mysql_connect

    if tables is None:
        tables, _ = get_offline_table_closure(source_mode=source_mode)

    owns_mysql_conn = _mysql_conn is None
    mysql_conn = _mysql_conn or raw_mysql_connect(source_mode)

    root_set = set(ROOT_TABLES)
    schema: Dict[str, List[Dict[str, Any]]] = {}
    try:
        with raw_sqlite_connect(sqlite_path) as cn:
            cur = cn.cursor()
            for t in tables:
                cols = fetch_mysql_columns(t, source_mode=source_mode, _conn=mysql_conn)
                schema[t] = cols
                track_edits = t in root_set

                # Migration case: a table promoted from EXTRA_REFERENCE_TABLES
                # to ROOT_TABLES (or newly needing tracking for any reason)
                # may already exist in an older offline file WITHOUT
                # LOCAL_TRACKING_COLUMN - "CREATE TABLE IF NOT EXISTS" below
                # is a no-op for an already-existing table, so it would never
                # retroactively add the column, silently disabling edit
                # detection on that table forever. ALTER TABLE ADD COLUMN
                # patches it in place, preserving existing data.
                if track_edits:
                    cur.execute(f'PRAGMA table_info("{t}")')
                    existing_cols = {r[1] for r in cur.fetchall()}
                    if existing_cols and LOCAL_TRACKING_COLUMN not in existing_cols:
                        cur.execute(f'ALTER TABLE "{t}" ADD COLUMN "{LOCAL_TRACKING_COLUMN}" TEXT')

                ddl = generate_create_table_sql(t, cols, track_edits=track_edits)
                cur.execute(ddl)

                # Same no-op problem for columns added to MySQL after the
                # offline file was created (e.g. tblTrial.IsReference,
                # 2026-10-15): pull_snapshot() INSERTs with the full MySQL
                # column list and would fail on an older file. Add them.
                cur.execute(f'PRAGMA table_info("{t}")')
                have = {r[1] for r in cur.fetchall()}
                for c in cols:
                    if c["name"] not in have:
                        cur.execute(
                            f'ALTER TABLE "{t}" ADD COLUMN "{c["name"]}" '
                            f'{mysql_type_to_sqlite(c["mysql_type"])}'
                        )
                if track_edits:
                    cur.execute(generate_update_trigger_sql(t))
    finally:
        if owns_mysql_conn:
            mysql_conn.close()
    return schema
