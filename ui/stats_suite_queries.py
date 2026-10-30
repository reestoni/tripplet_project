"""stats_suite_queries.py - aggregation queries for the Statistics Suite
(superuser-only dashboard, see ui/screen_stats_suite.py).

Same style/conventions as ui/report_queries.py (lazy `db.connection` import
per function, `?` placeholders translated by db.connection._to_mysql_sql()).

Counts Experiments / TrialSeries / Trials, optionally grouped by a category
(Order Type / Product Group / Machine) and/or split into time periods
(Year / Month), with a shared filter set (machines/product groups/order
types/date range).

Schema notes (see CLAUDE.md "Statistics Suite" bullet for the full writeup):
- "Order status" maps to tblexperimente.Bestellungstyp -> tblbestellungstyp;
  there is no separate lifecycle-status field on tblexperimente, this is the
  closest matching concept.
- tblexperimente has no own date column. Its date is derived as
  MIN(tbltrialseries.CreationDate) across the experiment's series - an
  experiment with zero series simply has no date and drops out of any
  time-split chart (still counted in pure category charts).
- Product group / order type only exist on tblexperimente, so TrialSeries/
  Trial-level charts join up through tbltrialseries -> tblexperimente to
  reach them.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from db.trial_reference import exclude_references_sql

logger = logging.getLogger(__name__)

ENTITY_LABELS = {
    "experiment": "Experiments",
    "trialseries": "Trial Series",
    "trial": "Trials",
}

GROUP_BY_LABELS = {
    "ordertype": "Order Type",
    "productgroup": "Product Group",
    "project": "Project",
    "machine": "Machine",
    "owner": "Owner",
    "labmachine": "Lab Machine",
}

# "Lab Machine" (e.g. "how many trials were processed on the Itemat Lab")
# has no meaningful 1:1 row semantics for Experiments/TrialSeries - a trial
# can appear under several lab machines (Titer AND Statimat AND ...), which
# would multiply an Experiment's/TrialSeries' own row count in a way none of
# the other dimensions do. Restricted to entity='trial', both here (drives
# the JS add-panel's Group-by options per selected Entity) and validated
# server-side in run_stats_query().
GROUP_BY_ENTITY_RESTRICTIONS = {
    "labmachine": ["trial"],
}

TIME_GRANULARITY_LABELS = {
    "year": "Year",
    "month": "Month",
}

# tblLab* tables that carry a TrialID (one row of lab measurement data per
# trial, sometimes several e.g. per tension level - DISTINCT TrialID per
# table avoids double-counting those). Display names match the existing tab
# titles in ShowExperimentScreen for recognizability. tblLaborJetAirConsumption
# is deliberately excluded - it has no TrialID column at all, it's scoped to
# TrialSeriesID/physical jet instead (calibration measurement, not per-trial).
# shared with the Smart Chart field "Tested on" (db/trial_explorer.py)
from db.trial_explorer import LAB_MACHINE_TABLES as _LAB_MACHINE_TABLES  # noqa: E402

_LAB_MACHINE_UNION_SQL = " UNION ALL ".join(
    f"SELECT DISTINCT TrialID, '{name}' AS LabMachine FROM {table} WHERE TrialID IS NOT NULL"
    for table, name in _LAB_MACHINE_TABLES
)

# Per-entity FROM/JOIN clause plus the column aliases every clause makes
# available. Deliberately uniform (entity id / date / product-group id+name /
# order-type id+name / machine id+name) so the rest of run_stats_query() can
# stay entity-agnostic.
_ENTITY_FROM = {
    "experiment": {
        "from_sql": (
            "FROM tblexperimente e "
            # Experiment date + owner are both derived from its EARLIEST
            # TrialSeries (tblexperimente has neither column itself) - a
            # window function picks that one row per experiment so date and
            # owner always come from the same row, rather than two
            # independent MIN()/MAX() aggregates that could theoretically
            # disagree if two series tie on date. BacklogOwner (not
            # CreatedBy) - see tblTrialSeries: it's set once a series leaves
            # the Backlog column (whoever moved it out) and then stays put
            # through later status changes, so it reads as "who's
            # responsible for this", not "who typed it in".
            "LEFT JOIN (SELECT ExperimentID, CreationDate AS MinDate, BacklogOwner AS FirstOwner "
            "           FROM (SELECT ExperimentID, CreationDate, BacklogOwner, "
            "                        ROW_NUMBER() OVER (PARTITION BY ExperimentID "
            "                                            ORDER BY CreationDate ASC, ID ASC) AS rn "
            "                 FROM tbltrialseries) ranked "
            "           WHERE rn = 1) ts_date "
            "       ON ts_date.ExperimentID = e.ID "
            "LEFT JOIN tblproduktgruppe pg ON pg.ID = e.Produktgruppe "
            "LEFT JOIN tblbestellungstyp bt ON bt.ID = e.Bestellungstyp "
            "LEFT JOIN tblproject p ON p.ID = e.Projekt "
            "LEFT JOIN tblmaschine m ON m.ID = e.Maschine "
            "LEFT JOIN tbluser u ON u.ID = ts_date.FirstOwner"
        ),
        "date_col": "ts_date.MinDate",
        "year_fallback_col": "e.Jahr",
    },
    "trialseries": {
        "from_sql": (
            "FROM tbltrialseries ts "
            "JOIN tblexperimente e ON e.ID = ts.ExperimentID "
            "LEFT JOIN tblproduktgruppe pg ON pg.ID = e.Produktgruppe "
            "LEFT JOIN tblbestellungstyp bt ON bt.ID = e.Bestellungstyp "
            "LEFT JOIN tblproject p ON p.ID = e.Projekt "
            "LEFT JOIN tblmaschine m ON m.ID = ts.MachineID "
            "LEFT JOIN tbluser u ON u.ID = ts.BacklogOwner"
        ),
        "date_col": "ts.CreationDate",
        "year_fallback_col": "e.Jahr",
    },
    "trial": {
        "from_sql": (
            "FROM tbltrial t "
            "JOIN tbltrialseries ts ON ts.ID = t.TrialSeriesID "
            "JOIN tblexperimente e ON e.ID = ts.ExperimentID "
            "LEFT JOIN tblproduktgruppe pg ON pg.ID = e.Produktgruppe "
            "LEFT JOIN tblbestellungstyp bt ON bt.ID = e.Bestellungstyp "
            "LEFT JOIN tblproject p ON p.ID = e.Projekt "
            "LEFT JOIN tblmaschine m ON m.ID = ts.MachineID "
            "LEFT JOIN tbluser u ON u.ID = ts.BacklogOwner"
        ),
        # t.Timestamp is only reliably set once a trial's machine data has
        # actually been edited (see screen_show_experiment.py::_save_all())
        # or its series reached "Done" (screen_backlog.py fallback) - both
        # 2026-08-20 fixes, forward-looking only. For everything before that
        # (and any trial that still slips through), fall back to its own
        # series' CreationDate, which is set at series-creation time and
        # therefore far more complete (only 113/352 series lack it, all
        # legacy Archived rows - see year_fallback_col below for those).
        "date_col": "COALESCE(t.Timestamp, ts.CreationDate)",
        "year_fallback_col": "e.Jahr",
    },
}

# Category (group-by) column pairs, shared across all three entities since
# the JOINs above always expose pg/bt/m/u under the same aliases. "owner" is
# tblTrialSeries.BacklogOwner (set once a series first leaves the Backlog
# column, stays put through later status changes) of the (earliest, for
# experiment) TrialSeries - tblexperimente/tbltrial have no such column of
# their own. Deliberately BacklogOwner, not CreatedBy: "who's responsible",
# not "who typed it in" (2026-08-19, explicit user correction).
_GROUP_BY_COLS = {
    "ordertype": {"id_col": "bt.ID", "name_col": "bt.Bestellungstyp"},
    "productgroup": {"id_col": "pg.ID", "name_col": "pg.Produktgruppe"},
    "project": {"id_col": "p.ID", "name_col": "CONCAT(p.ProjectNumber, ' - ', p.ProjectName)"},
    "machine": {"id_col": "m.ID", "name_col": "m.Maschine"},
    "owner": {"id_col": "u.ID", "name_col": "CONCAT(u.FirstName, ' ', u.LastName)"},
}


def _period_expr(date_col: str, granularity: str, year_fallback_col: Optional[str] = None) -> str:
    if granularity == "year":
        expr = f"YEAR({date_col})"
        if year_fallback_col:
            # Rows with no real date at all (e.g. legacy Archived TrialSeries
            # migrated from Access, never given a CreationDate) still have a
            # reliable tblexperimente.Jahr - falls back to that so they land
            # in their real year bucket instead of a catch-all "(no date)"
            # bucket. Year-only, deliberately NOT applied to month
            # granularity (no day/month info to synthesize) or to the
            # dateFrom/dateTo WHERE filter (would silently invent a Jan-1
            # date for range comparisons - see run_stats_query()).
            expr = f"COALESCE({expr}, {year_fallback_col})"
        return expr
    if granularity == "month":
        return f"DATE_FORMAT({date_col}, '%Y-%m')"
    raise ValueError(f"Unknown time granularity: {granularity!r}")


def run_stats_query(
    entity: str,
    group_by: Optional[str],
    time_granularity: Optional[str],
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Returns rows shaped like {"Period": ..., "Category": ..., "Cnt": ...}
    (Period/Category omitted when not requested) for one dashboard card.

    `entity` must be one of ENTITY_LABELS' keys, `group_by` one of
    GROUP_BY_LABELS' keys or None, `time_granularity` one of
    TIME_GRANULARITY_LABELS' keys or None - all validated against the
    whitelists above before touching SQL, since these values ultimately come
    from the JS bridge (untrusted input).
    """
    from db.connection import fetch_all

    if entity not in _ENTITY_FROM:
        raise ValueError(f"Unknown entity: {entity!r}")
    if group_by is not None and group_by not in GROUP_BY_LABELS:
        raise ValueError(f"Unknown group_by: {group_by!r}")
    if time_granularity is not None and time_granularity not in TIME_GRANULARITY_LABELS:
        raise ValueError(f"Unknown time_granularity: {time_granularity!r}")
    allowed_entities = GROUP_BY_ENTITY_RESTRICTIONS.get(group_by)
    if allowed_entities is not None and entity not in allowed_entities:
        raise ValueError(f"group_by {group_by!r} is not available for entity {entity!r}")

    filters = filters or {}
    cfg = _ENTITY_FROM[entity]
    date_col = cfg["date_col"]
    from_sql = cfg["from_sql"]

    lab_machines = filters.get("labMachines") or []
    # Same entity restriction as group_by="labmachine" (see
    # GROUP_BY_ENTITY_RESTRICTIONS) and for the same reason: the lm join only
    # has a `t` alias to hang off in the trial entity's FROM clause, and a
    # trial measured on several lab machines would multiply an Experiment's/
    # TrialSeries' own row count. Unlike group_by, this filter comes from the
    # *global* filter bar (applies to every card regardless of its own
    # entity) - rather than erroring out for non-trial cards, it's silently
    # a no-op there, same as picking a Lab Machine group-by would simply not
    # be offered for them in the add-panel.
    apply_lab_filter = bool(lab_machines) and entity == "trial"
    if group_by == "labmachine" or apply_lab_filter:
        # One row per (TrialID, LabMachine) match, so a trial measured on
        # several lab machines is correctly counted once per machine, not
        # once overall.
        from_sql += f" LEFT JOIN ({_LAB_MACHINE_UNION_SQL}) lm ON lm.TrialID = t.ID"

    select_cols = []
    group_cols = []
    order_cols = []

    if time_granularity:
        period_sql = _period_expr(date_col, time_granularity, cfg.get("year_fallback_col"))
        select_cols.append(f"{period_sql} AS Period")
        group_cols.append(period_sql)
        order_cols.append("Period ASC")

    if group_by:
        name_col = "lm.LabMachine" if group_by == "labmachine" else _GROUP_BY_COLS[group_by]["name_col"]
        select_cols.append(f"{name_col} AS Category")
        group_cols.append(name_col)
        order_cols.append("Category ASC" if time_granularity else None)

    select_cols.append("COUNT(*) AS Cnt")
    if not group_cols and not order_cols:
        order_cols = []
    if not time_granularity and group_by:
        # Pure category breakdown (no time axis) reads better sorted by size.
        order_cols = ["Cnt DESC"]

    where_parts = []
    params: List[Any] = []

    if entity == "trial":
        # Reference samples (customer originals) are not trials.
        where_parts.append(exclude_references_sql("t"))

    machines = filters.get("machines") or []
    if machines:
        where_parts.append(f"m.ID IN ({','.join(['?'] * len(machines))})")
        params.extend(machines)

    if apply_lab_filter:
        where_parts.append(f"lm.LabMachine IN ({','.join(['?'] * len(lab_machines))})")
        params.extend(lab_machines)

    product_groups = filters.get("productGroups") or []
    if product_groups:
        where_parts.append(f"pg.ID IN ({','.join(['?'] * len(product_groups))})")
        params.extend(product_groups)

    order_types = filters.get("orderTypes") or []
    if order_types:
        where_parts.append(f"bt.ID IN ({','.join(['?'] * len(order_types))})")
        params.extend(order_types)

    # Rows with no real date at all (see year_fallback_col) would otherwise
    # be dropped by this WHERE filter before ever reaching _period_expr()'s
    # fallback - a row with only Jahr=2026 known has no real date_col to
    # compare against a dateFrom/dateTo range, so a plain "date_col >= ?"
    # excludes it even when it plainly belongs in a 2026 range. Substitute
    # Jan-1-of-Jahr for those rows (year precision only - matches what
    # year_fallback_col already promises elsewhere); a real date_col value
    # always wins via COALESCE, this only kicks in when there truly is none.
    year_fallback_col = cfg.get("year_fallback_col")
    filter_date_col = (
        f"COALESCE({date_col}, MAKEDATE({year_fallback_col}, 1))"
        if year_fallback_col else date_col
    )

    date_from = filters.get("dateFrom")
    if date_from:
        where_parts.append(f"{filter_date_col} >= ?")
        params.append(date_from)
    date_to = filters.get("dateTo")
    if date_to:
        where_parts.append(f"{filter_date_col} <= ?")
        params.append(date_to)

    sql = f"SELECT {', '.join(select_cols)} {from_sql}"
    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)
    if group_cols:
        sql += " GROUP BY " + ", ".join(group_cols)
    order_cols = [c for c in order_cols if c]
    if order_cols:
        sql += " ORDER BY " + ", ".join(order_cols)

    rows = fetch_all(sql, params)
    for r in rows:
        if "Category" in r and r["Category"] is None:
            r["Category"] = "—"  # em dash, matches project's "no value" convention
        if "Period" in r:
            # Many legacy rows migrated from Access have no CreationDate/
            # Timestamp - keep them visible as their own "(no date)" bucket
            # instead of silently dropping them from the chart.
            r["Period"] = str(r["Period"]) if r["Period"] is not None else "(no date)"
    return rows


def fetch_filter_options() -> Dict[str, List[Dict[str, Any]]]:
    """Machines/product groups/order types for the dashboard's global filter
    bar dropdowns."""
    from db.connection import fetch_all

    machines = fetch_all(
        "SELECT ID, Maschine AS Name FROM tblmaschine ORDER BY Maschine ASC"
    )
    product_groups = fetch_all(
        "SELECT ID, Produktgruppe AS Name FROM tblproduktgruppe ORDER BY Produktgruppe ASC"
    )
    order_types = fetch_all(
        "SELECT ID, Bestellungstyp AS Name FROM tblbestellungstyp ORDER BY Bestellungstyp ASC"
    )
    return {
        "machines": [{"id": int(r["ID"]), "name": str(r["Name"] or "")} for r in machines],
        "productGroups": [{"id": int(r["ID"]), "name": str(r["Name"] or "")} for r in product_groups],
        "orderTypes": [{"id": int(r["ID"]), "name": str(r["Name"] or "")} for r in order_types],
        # Not a DB table (see _LAB_MACHINE_TABLES) - the display name doubles
        # as its own id, unlike the numeric-ID filters above.
        "labMachines": [{"id": name, "name": name} for _, name in _LAB_MACHINE_TABLES],
    }
