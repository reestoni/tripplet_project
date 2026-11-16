from __future__ import annotations
# db/report_service.py
"""Series report (ui/report_html_template.py) - every DB/compute part, Qt-free.

Moved out of ui/screen_report.py (2026-11-13) so the desktop (QWebChannel
bridge) and the web version (tripplet_web, FastAPI) run the same code. The
page talks to Python through ``_bridge.<slot>(...)`` and gets its answer
through a global ``receiveXxx(...)`` function; this module knows both sides:

* plain functions with explicit arguments (``series_list()``,
  ``save_report(data, user)``, ...) that return the Python value the page's
  receive function gets - see the table in ``SLOTS``;
* ``handle(slot, args, user=..., series_pk=...)`` = the complete slot as the
  page calls it (string arguments exactly as JS sends them, JSON parsing,
  error fallbacks, logging) -> ``(receiver, [args])`` or ``None`` when the
  page gets no answer. The desktop bridge is a thin wrapper around it;
  ``js_call(receiver, args)`` turns the result into the JS the desktop runs.

Nothing here reads ``app_meta.current_user``: whatever depends on the user
takes a ``user`` dict with the keys of app_meta.current_user (id, username,
first_name, last_name, access_level). Must import without PySide6
(tests/test_report_service.py checks that).
"""

import datetime
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from db.trial_reference import exclude_references_sql
from ui.report_queries import (
    Y_AXES, X_AXES,
    _get_known_tables, _load_axes_from_db,
    _fetch_y_values, _fetch_table_columns, _fetch_series_data,
    _fetch_infobox_data, with_category_axes,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# User helpers (instead of app_meta.current_user)
# ---------------------------------------------------------------------------

def _user(user) -> dict:
    return user or {}


def _access_level(user) -> int:
    # same rule as app_meta.access_level()
    try:
        return int(_user(user).get("access_level") or 0)
    except Exception:
        return 0


def is_superuser(user) -> bool:
    """Same rule as app_meta.is_superuser_level() (AccessLevel >= 4)."""
    return _access_level(user) >= 4


# ---------------------------------------------------------------------------
# Smart Chart: advanced filters
# ---------------------------------------------------------------------------
# Machine of a trial - joined once per query under the alias MC (filter,
# group by and the machine_name column all use this one join).
MACHINE_JOIN = ("LEFT JOIN tblTrialSeries AS TSR_MC ON TSR_MC.ID = T.TrialSeriesID "
                "LEFT JOIN tblMaschine AS MC ON MC.ID = TSR_MC.MachineID")
_ADV_OPS = {"=", "!=", "<>", ">", "<", ">=", "<=", "LIKE", "NOT LIKE", "IN", "IS NULL", "IS NOT NULL"}
_ADV_DIRECT = {"tbltrial": "T", "tbljets": "J", "tblmaschine": "MC"}  # already in every query
_ADV_JOINED = {"tbljetrohling": "LEFT JOIN tbljetrohling AS adv_tbljetrohling ON adv_tbljetrohling.ID = J.Rohling"}


def value_notes_text(notes) -> str:
    """Plain text lines for the PDF: "V7 · Tenacity: text (Name, 30.10.2026)"."""
    lines = []
    for n in notes or []:
        who = ", ".join(x for x in (str(n.get("by") or "").strip(), str(n.get("at") or "").strip()) if x)
        lines.append(f"{n.get('trial', '')} · {n.get('what', '')}: {str(n.get('t') or '').strip()}"
                     + (f" ({who})" if who else ""))
    return "\n".join(lines)


def _is_ident(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name or ""))


def _adv_allowed_fields() -> Optional[set]:
    """(table lower, field lower) of tblSmartChartAllowedField, None if unknown."""
    try:
        from db.connection import fetch_all
        return {(str(r["TableName"]).lower(), str(r["FieldName"]).lower())
                for r in fetch_all("SELECT TableName, FieldName FROM tblSmartChartAllowedField")}
    except Exception:
        return None


def advanced_filter_sql(filters, allowed: Optional[set] = None):
    """Advanced filters of the Smart Chart -> (where_parts, params, joins).

    tbltrial / tbljets / tblmaschine use the joins every query has (T, J, MC),
    tbljetrohling goes via the jet. Every other table (the lab tables) is
    matched per trial with EXISTS on TrialID - a trial with several
    measurements (e.g. 6 ITEMAT LAB rows) then shows up once, not 6 times;
    "IS NULL" there means "no value measured". Table/field must be a plain
    name and, if the list is known, in tblSmartChartAllowedField; unknown
    operators are dropped - nothing from the page goes into the SQL unchecked.
    """
    where, params, joins = [], [], []
    for af in filters or []:
        tbl = str(af.get("table") or "")
        fld = str(af.get("field") or "")
        op = str(af.get("op") or "=").upper()
        val = af.get("value")
        vals = af.get("values") or []
        if not (_is_ident(tbl) and _is_ident(fld)) or op not in _ADV_OPS:
            logger.warning("Smart Chart: advanced filter ignored: %r", af)
            continue
        key = tbl.lower()
        if allowed is not None and (key, fld.lower()) not in allowed:
            logger.warning("Smart Chart: field not allowed: %s.%s", tbl, fld)
            continue

        def cond(col):
            if op in ("IS NULL", "IS NOT NULL"):
                return f"{col} {op}", []
            if op == "IN":
                return (f"{col} IN ({','.join('?' for _ in vals)})", list(vals)) if vals else (None, [])
            if val is None or str(val).strip() == "":
                return None, []
            if op in ("LIKE", "NOT LIKE"):
                return f"{col} {op} ?", [f"%{val}%"]
            try:
                v = float(val)
            except (TypeError, ValueError):
                v = val
            return f"{col} {op} ?", [v]

        if key in _ADV_DIRECT or key in _ADV_JOINED:
            if key in _ADV_JOINED and _ADV_JOINED[key] not in joins:
                joins.append(_ADV_JOINED[key])
            alias = _ADV_DIRECT.get(key) or f"adv_{key}"
            sql, p = cond(f"{alias}.{fld}")
            if sql:
                where.append(sql)
                params.extend(p)
            continue
        sub = f"SELECT 1 FROM {tbl} AS adv WHERE adv.TrialID = T.ID"
        if op == "IS NULL":
            where.append(f"NOT EXISTS ({sub} AND adv.{fld} IS NOT NULL)")
            continue
        sql, p = cond(f"adv.{fld}")
        if sql:
            where.append(f"EXISTS ({sub} AND {sql})")
            params.extend(p)
    return where, params, joins


# ---------------------------------------------------------------------------
# The page itself
# ---------------------------------------------------------------------------

def series_report_page(series_pk: int, initial_report_id: Optional[int] = None,
                       user: Optional[dict] = None) -> Dict[str, Any]:
    """Series report page -> {"html", "n_trials", "n_refs"}.

    html = ui/report_html_template.py with every placeholder filled; the
    desktop shows it with setHtml(html, web_base_url()). n_trials/n_refs =
    trials and reference samples in DATA (desktop status text).
    """
    from ui.report_html_template import _HTML_TEMPLATE

    data     = _fetch_series_data(series_pk)
    tbl_cols = _fetch_table_columns()
    infobox  = _fetch_infobox_data(series_pk)

    # Load axes from DB, fallback to hardcoded
    db_y_axes, db_x_axes, db_g_axes = _load_axes_from_db()
    active_y_axes = db_y_axes if db_y_axes else Y_AXES
    active_x_axes = db_x_axes if db_x_axes else X_AXES

    n_refs = sum(1 for r in data if r.get("is_reference"))

    y_axes_js = [{"key": y["key"], "title": y["title"], "unit": y.get("unit", "")} for y in active_y_axes]
    tbl_opts  = "\n".join(
        f'<option value="{t}">{t}</option>' for t in _get_known_tables()
    )
    x_axes_js = [{"id": x.get("id"), "key": x["key"], "title": x["title"], "unit": x.get("unit", ""), "field": x["field"], "sub_axis_id": x.get("sub_axis_id"), "is_group_by": x.get("is_group_by", False)} for x in active_x_axes]
    html = (
        _HTML_TEMPLATE
        .replace("{data_json}",     json.dumps(data))
        .replace("{y_axes_json}",   json.dumps(y_axes_js))
        .replace("{x_axes_json}",   json.dumps(with_category_axes(x_axes_js)))
        .replace("{tbl_cols_json}", json.dumps(tbl_cols))
        .replace("{table_options}", tbl_opts)
        .replace("{infobox_json}",  json.dumps(infobox))
        .replace("{primary_series_pk}", str(series_pk))
        .replace("{current_user_json}", json.dumps(str(_user(user).get("username", "") or "")))
        .replace("{is_superuser_json}", "true" if is_superuser(user) else "false")
        .replace("{initial_report_id_json}", json.dumps(initial_report_id))
    )
    return {"html": html, "n_trials": len(data) - n_refs, "n_refs": n_refs}


def series_report_html(series_pk: int, initial_report_id: Optional[int] = None,
                       user: Optional[dict] = None) -> str:
    """Full HTML of the series report (see series_report_page())."""
    return series_report_page(series_pk, initial_report_id, user)["html"]


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def series_list() -> List[dict]:
    """[{pk, name}] for "Add series" -> receiveSeriesList(list)."""
    from db.connection import fetch_all
    rows = fetch_all(
        "SELECT TS.ID AS pk, TS.SeriesName AS name, "
        "E.[Experiment ID] AS exp_id "
        "FROM tblTrialSeries AS TS "
        "LEFT JOIN tblExperimente AS E ON E.ID = TS.ExperimentID "
        "LIMIT 500",
        []
    )
    out = []
    for r in rows:
        pk   = int(r.get("pk") or 0)
        name = str(r.get("name") or "")
        exp  = str(r.get("exp_id") or "")
        label = f"{exp}.{name}" if exp else name
        out.append({"pk": pk, "name": label})
    # Absteigend nach Label sortieren (neueste Experiment-ID zuerst)
    out.sort(key=lambda x: x["name"], reverse=True)
    return out


def series_data(series_pk: int) -> Dict[str, Any]:
    """A further series for the chart -> {"name", "data", "meta"}.

    The page gets receiveSeriesData(pk, name, color, data, meta) - color is
    only echoed back (see handle("loadSeriesData")).
    """
    from db.connection import fetch_all

    # Series name with ExperimentID prefix
    ts = fetch_all(
        "SELECT TS.SeriesName, E.[Experiment ID] AS exp_id "
        "FROM tblTrialSeries AS TS "
        "LEFT JOIN tblExperimente AS E ON E.ID = TS.ExperimentID "
        "WHERE TS.ID = ?", [series_pk]
    )
    if ts:
        sname = str(ts[0].get("SeriesName") or "")
        exp   = str(ts[0].get("exp_id") or "")
        series_name = f"{exp}.{sname}" if exp else sname
    else:
        series_name = f"Series {series_pk}"

    # Machine
    machine = ""
    try:
        ts2 = fetch_all("SELECT MachineID FROM tblTrialSeries WHERE ID = ?", [series_pk])
        if ts2 and ts2[0].get("MachineID"):
            m = fetch_all("SELECT Maschine FROM tblMaschine WHERE ID = ?", [ts2[0]["MachineID"]])
            if m: machine = str(m[0].get("Maschine") or "")
    except Exception: pass

    # Material
    material = ""
    try:
        trials = fetch_all(
            f"SELECT ID FROM tblTrial WHERE TrialSeriesID = ? AND {exclude_references_sql('')}",
            [series_pk])
        tids = [int(r["ID"]) for r in trials]
        if tids:
            ph = ",".join(["?" for _ in tids])
            yarn_rows = fetch_all(
                "SELECT DISTINCT Y.Name AS YarnName, TS2.Ply "
                "FROM tblTrialSettings AS TS2 "
                "INNER JOIN tblYarn AS Y ON Y.ID = TS2.YarnID "
                f"WHERE TS2.TrialID IN ({ph}) ORDER BY TS2.Ply",
                tids
            )
            if yarn_rows:
                parts = []
                for r in yarn_rows:
                    yn  = str(r.get("YarnName") or "").strip()
                    ply = str(r.get("Ply") or "").strip()
                    parts.append(f"{ply}: {yn}" if ply else yn)
                material = " • ".join(parts)
    except Exception: pass

    data = _fetch_series_data(series_pk)
    return {"name": series_name, "data": data,
            "meta": {"machine": machine, "material": material}}


# Known relations for group-by tables whose join in tblSmartChartAxis is wrong: tbljetrohling has
# no JetID - the jet points to its blank via tbljets.Rohling (as _ADV_JOINED does).
_GROUP_JOIN_ON = {"tbljetrohling": "{a}.ID = J.Rohling"}


def group_join_sql(table: str, alias: str, join_sql: str) -> str:
    """JOIN for a group-by axis under its own alias. Before 2026-11-13 the alias replaced the
    table NAME too ("LEFT JOIN gb_rohling ON ...") and the query always failed."""
    import re as _re
    tl = str(table).lower()
    if tl in _GROUP_JOIN_ON:
        on = _GROUP_JOIN_ON[tl].format(a=alias)
    else:
        m = _re.search(r"\bON\b(.*)$", join_sql, flags=_re.I | _re.S)
        on = m.group(1).strip() if m else "1=0"
        on = _re.sub(rf"\b{_re.escape(table)}\.", f"{alias}.", on, flags=_re.I)
    return f"LEFT JOIN {table} AS {alias} ON {on}"


def run_visual_query(series_pks, group_by: str, filters, adv_filters=None) -> List[dict]:
    """Rows over several series (X axis with is_group_by) -> receiveQueryResult(rows, len(rows)).

    series_pks/filters/adv_filters = the parsed JSON the page sends. Raises
    on DB errors (the slot then answers with an empty result).
    """
    from db.connection import fetch_all

    series_pks = series_pks or []
    filters    = filters or []

    where_parts, params, extra_joins = [], [], []

    # Map filterKey → (optional extra JOIN, WHERE clause, bound value)
    LOOKUP_JOINS = {
        'jet':     None,
        'yarn':    (
            "LEFT JOIN ("
            "SELECT GTS.TrialID, GROUP_CONCAT(DISTINCT GY.Name ORDER BY GY.Name SEPARATOR ' / ') AS yarn_label2 "
            "FROM tblTrialSettings AS GTS "
            "INNER JOIN tblYarn AS GY ON GY.ID = GTS.YarnID "
            "GROUP BY GTS.TrialID"
            ") AS YarnFilter ON YarnFilter.TrialID = T.ID"
        ),
        'machine': MACHINE_JOIN,
    }
    LOOKUP_FIELDS  = {'jet': 'J.Jet', 'yarn': 'YarnFilter.yarn_label2', 'machine': 'MC.Maschine'}
    NUMERIC_FIELDS = {'air_pressure': 'T.AirPressure', 'overfeed': 'T.Shaft2x_OF', 'speed': 'T.SpeedShaft2', 'jet_plate': 'T.JetPlate'}

    for f in filters:
        fkey   = f.get("filterKey", "")
        op     = f.get("op", "=")
        value  = f.get("value", "")
        values = f.get("values", [])
        if not fkey: continue
        if op == "IN" and values:
            join_sql = LOOKUP_JOINS.get(fkey)
            if join_sql and join_sql not in extra_joins:
                extra_joins.append(join_sql)
            field = LOOKUP_FIELDS.get(fkey, "J.Jet")
            ph = ",".join(["?" for _ in values])
            where_parts.append(field + " IN (" + ph + ")")
            params.extend(values)
        elif fkey in LOOKUP_FIELDS and value:
            join_sql = LOOKUP_JOINS.get(fkey)
            if join_sql and join_sql not in extra_joins:
                extra_joins.append(join_sql)
            where_parts.append(LOOKUP_FIELDS[fkey] + " " + op + " ?")
            params.append(value)
        elif fkey in NUMERIC_FIELDS and value:
            try:
                where_parts.append(NUMERIC_FIELDS[fkey] + " " + op + " ?")
                params.append(float(value))
            except (ValueError, TypeError):
                continue

    if series_pks:
        ph = ",".join(["?" for _ in series_pks])
        where_parts.append("T.TrialSeriesID IN (" + ph + ")")
        params.extend(series_pks)

    # Cross-series query: reference samples (customer originals,
    # db/trial_reference.py) are not trials - never part of it.
    where_parts.append(exclude_references_sql("T"))

    # Map group_by key to SQL expression
    # Add required JOINs for group_by field
    # Yarn uses a subquery to avoid TrialSettings duplicate rows
    if group_by == 'yarn' and not any('YarnSub' in j for j in extra_joins):
        extra_joins.append(
            "LEFT JOIN ("
            "SELECT GTS.TrialID, GROUP_CONCAT(DISTINCT GY.Name ORDER BY GY.Name SEPARATOR ' / ') AS yarn_label "
            "FROM tblTrialSettings AS GTS "
            "INNER JOIN tblYarn AS GY ON GY.ID = GTS.YarnID "
            "GROUP BY GTS.TrialID"
            ") AS YarnSub ON YarnSub.TrialID = T.ID"
        )
    elif group_by == 'machine' and MACHINE_JOIN not in extra_joins:
        extra_joins.append(MACHINE_JOIN)
    elif group_by == 'series_name':
        extra_joins.append("LEFT JOIN tblTrialSeries AS TS3 ON TS3.ID = T.TrialSeriesID")

    GROUP_BY_MAP = {
        'jet':          'J.Jet',
        'yarn':         'YarnSub.yarn_label',
        'machine':      'MC.Maschine',
        'series_name':  'TS3.SeriesName',
        'custom_group': 'T.CustomGroup',
    }

    # Dynamische G-Achsen und is_group_by X-Achsen aus DB
    __, db_x, db_g = _load_axes_from_db()
    _g_axes_map = {}
    for _g in (db_g or []):
        if _g.get('is_group_by') and _g.get('main_table') and _g.get('field'):
            _alias = f"gb_{_g['key']}"
            _expr  = f"{_alias}.{_g['field']}"
            _g_axes_map[_g['key']] = {'expr': _expr, 'alias': _alias, 'join_sql': _g.get('join_sql'),
                                      'table': _g['main_table']}
    # Collect all is_group_by X-axis keys so we can store group_label under them too
    _group_x_keys = [x['key'] for x in (db_x or []) if x.get('is_group_by')]

    if group_by in _g_axes_map:
        _ginfo = _g_axes_map[group_by]
        if _ginfo['join_sql']:
            _join = group_join_sql(_ginfo['table'], _ginfo['alias'], _ginfo['join_sql'])
            if _join not in extra_joins:
                extra_joins.append(_join)
            group_expr = _ginfo['expr']
        else:
            # No JOIN needed — fall back to GROUP_BY_MAP (uses existing aliases)
            group_expr = GROUP_BY_MAP.get(group_by, 'J.Jet')
    else:
        group_expr = GROUP_BY_MAP.get(group_by, 'J.Jet')

    # Always add yarn subquery for infobox slicer
    if not any('YarnSub' in j for j in extra_joins):
        extra_joins.append(
            "LEFT JOIN ("
            "SELECT GTS.TrialID, GROUP_CONCAT(DISTINCT GY.Name ORDER BY GY.Name SEPARATOR ' / ') AS yarn_label "
            "FROM tblTrialSettings AS GTS "
            "INNER JOIN tblYarn AS GY ON GY.ID = GTS.YarnID "
            "GROUP BY GTS.TrialID"
            ") AS YarnSub ON YarnSub.TrialID = T.ID"
        )

    # Advanced filters (were added after the WHERE was already built -
    # their values had no placeholder and the query failed, 2026-10-16)
    adv_filters = adv_filters or []
    if adv_filters:
        adv_where, adv_params, adv_joins = advanced_filter_sql(adv_filters, _adv_allowed_fields())
        where_parts.extend(adv_where)
        params.extend(adv_params)
        extra_joins.extend(j for j in adv_joins if j not in extra_joins)

    joins_sql = "LEFT JOIN tbljets AS J ON J.ID = T.JetID"
    if MACHINE_JOIN not in extra_joins:  # machine_name column - always
        extra_joins.append(MACHINE_JOIN)
    joins_sql += " " + " ".join(extra_joins)
    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    sql = (
        "SELECT T.ID AS trial_id, T.Versuchsnummer AS trial_nr, "
        "T.AirPressure AS air_pressure, T.Shaft2x_OF AS overfeed, "
        "T.SpeedShaft2 AS speed, T.JetPlate AS jet_plate, "
        "J.Jet AS jet_name, J.Luftverbrauch AS air_cons, "
        "YarnSub.yarn_label AS yarn_label, "
        "MC.Maschine AS machine_name, "
        "T.CustomGroup AS custom_group_raw, "
        + group_expr + " AS group_label "
        "FROM tblTrial AS T "
        + joins_sql + " "
        + where_sql + " "
        "ORDER BY T.TrialSeriesID, T.Versuchsnummer ASC "
        "LIMIT 5000"
    )
    base_rows = fetch_all(sql, params)
    if not base_rows:
        return []

    trial_ids = [int(r["trial_id"]) for r in base_rows]
    db_y, _, db_g = _load_axes_from_db()
    axes = db_y if db_y else Y_AXES
    # Keys that are computed in Python — skip DB fetch for these
    _COMPUTED_Y_KEYS = {"air_cons_real"}

    y_data = {}
    for ydef in axes:
        if ydef["key"] in _COMPUTED_Y_KEYS:
            continue
        y_data[ydef["key"]] = _fetch_y_values(
            trial_ids=trial_ids,
            main_table=ydef["main_table"],
            alt_table=ydef["alt_table"],
            field=ydef["field"],
            condition=ydef["condition"],
        )

    def _f(v):
        if v is None or v == "": return None
        try: return float(v)
        except: return None

    rows = []
    for r in base_rows:
        tid = int(r["trial_id"])
        row = {
            "trial_id":     tid,
            "trial_nr":     int(r.get("trial_nr") or 0),
            "air_pressure": _f(r.get("air_pressure")),
            "overfeed":     _f(r.get("overfeed")),
            "speed":        _f(r.get("speed")),
            "jet_plate":    _f(r.get("jet_plate")),
            # Realer Luftverbrauch = Jet-Faktor * (gefahrener Betriebsdruck
            # dieses Trials + 1), nicht der reine Jet-Faktor.
            "air_cons":      round(_f(r.get("air_cons")) * (_f(r.get("air_pressure")) + 1), 2)
                             if _f(r.get("air_cons")) is not None and _f(r.get("air_pressure")) is not None
                             else None,
            # Separater Y-Achsen-Eintrag (tblSmartChartAxis ID 45, "air_cons_real").
            "air_cons_real": round(_f(r.get("air_cons")) * (_f(r.get("air_pressure")) + 1), 2)
                             if _f(r.get("air_cons")) is not None and _f(r.get("air_pressure")) is not None
                             else None,
            "real_jet":     str(r.get("jet_name") or "Unknown"),
            "yarn_name":    str(r.get("yarn_label") or ""),
            "machine_name": str(r.get("machine_name") or ""),
            "jet_name":     str(r.get("group_label") or r.get("jet_name") or "Unknown"),
            "custom_group": str(r.get("custom_group_raw") or ""),
        }
        # Store group_label under every non-standard X-axis key
        # Standard numeric keys that already have their own values:
        _STANDARD_X_KEYS = {'air_pressure','overfeed','speed','trial_nr','jet_plate','air_cons'}
        _gl = r.get("group_label")
        if _gl is not None:
            _gl_val = str(_gl)
            # Under all is_group_by X-axis keys from DB
            for _xk in _group_x_keys:
                row[_xk] = _gl_val
            # Under ALL X-axis keys that are not standard numeric ones
            # (catch-all so any custom X-axis works regardless of IsGroupBy flag)
            for _xdef in (db_x or []):
                if _xdef['key'] not in _STANDARD_X_KEYS:
                    row[_xdef['key']] = _gl_val
            # Also under group_by itself
            row[group_by] = _gl_val
        for ydef in axes:
            if ydef["key"] in _COMPUTED_Y_KEYS:
                continue
            val = y_data[ydef["key"]].get(tid)
            row[ydef["key"]] = float(val) if val is not None else None
        rows.append(row)
    return rows


def report_list() -> List[dict]:
    """Saved reports (newest first, max 100) -> receiveReportList(list)."""
    from db.connection import fetch_all
    rows = fetch_all(
        "SELECT ID, Title, Author, SourceType, "
        "DATE_FORMAT(UpdatedAt, '%d.%m.%Y %H:%i') AS UpdatedStr "
        "FROM tblSmartChartReport WHERE IsTemplate=0 "
        "ORDER BY UpdatedAt DESC LIMIT 100", []
    )
    return [
        {"id": int(r["ID"]), "title": str(r["Title"] or ""),
         "author": str(r["Author"] or ""), "sourceType": str(r["SourceType"] or ""),
         "updated": str(r["UpdatedStr"] or "")}
        for r in rows
    ]


def load_report(report_id: int) -> Optional[dict]:
    """A full report incl. blocks -> receiveReport(report); None = not found (no answer)."""
    from db.connection import fetch_all

    rid = int(report_id)
    rows = fetch_all("SELECT * FROM tblSmartChartReport WHERE ID=?", [rid])
    if not rows:
        return None
    r = rows[0]

    # Load blocks ordered by SortOrder
    block_rows = fetch_all(
        "SELECT * FROM tblSmartChartBlock WHERE ReportID=? ORDER BY SortOrder",
        [rid]
    )
    blocks = []
    for b in block_rows:
        blocks.append({
            "id":         int(b["ID"]),
            "blockType":  str(b["BlockType"]),
            "sortOrder":  int(b["SortOrder"] or 0),
            "chartIndex": b["ChartIndex"],
            "xField":     str(b["XField"] or ""),
            "yKey":       str(b["YKey"] or ""),
            "zField":     str(b["ZField"] or ""),
            "chartMode":  str(b["ChartMode"] or "2d"),
            "chartType":  str(b.get("ChartType") or b["ChartMode"] or "bar"),
            "imageData":  b["ImageData"],
            "imageTitle": str(b["ImageTitle"] or ""),
            "imageWidth": str(b["ImageWidth"] or "full"),
            "noteTitle":  str(b["NoteTitle"] or ""),
            "noteText":   str(b["NoteText"] or ""),
            "noteVisible":bool(b["NoteVisible"]),
            "gridlinesY":       str(b.get("GridlinesY") or ""),
            "gridlinesVisible": bool(b.get("GridlinesVisible")),
        })

    # Global note
    note_rows = fetch_all(
        "SELECT NoteText FROM tblSmartChartNote "
        "WHERE ReportID=? AND NoteType='global' LIMIT 1", [rid]
    )
    global_note = str(note_rows[0]["NoteText"] or "") if note_rows else ""

    return {
        "id":              rid,
        "title":           str(r["Title"] or ""),
        "author":          str(r["Author"] or ""),
        "sourceType":      str(r["SourceType"] or "visual"),
        "seriesPK":        r["SeriesPK"],
        "queryConfig":     json.loads(r["QueryConfigJSON"] or "{}"),
        "showInfobox":     bool(r["ShowInfobox"]),
        "infoboxPosition": str(r["InfoboxPosition"] or "left"),
        "globalNote":      global_note,
        "blocks":          blocks,
    }


def free_field_values(series_pk: Optional[int], table: str, field: str,
                      condition: str) -> Optional[Dict[int, float]]:
    """{TrialID: value} of a free field (table.field [AND condition]) for the
    trials of the series -> receiveFreeFieldData(chartIdx, yKey, values).

    None = no answer (no series, unknown table, series without trials).
    NOTE: table/field/condition go into the SQL as the page sends them
    (only table_exists() is checked) - unchanged from the desktop.
    """
    if series_pk is None:
        return None

    from db.connection import fetch_all, table_exists
    if not table_exists(table):
        return None

    base = fetch_all(
        "SELECT ID AS trial_id FROM tblTrial WHERE TrialSeriesID = ?",
        [series_pk]
    )
    trial_ids = [int(r["trial_id"]) for r in base]
    if not trial_ids:
        return None

    id_col = "ID" if table.lower() == "tbltrial" else "TrialID"
    cond   = f" AND {condition}" if condition.strip() else ""
    ph     = ",".join(["?" for _ in trial_ids])
    sql    = f"SELECT {id_col} AS tid, {field} AS val FROM {table} WHERE {id_col} IN ({ph}){cond}"

    rows = fetch_all(sql, trial_ids)
    values = {}
    for r in rows:
        tid = int(r["tid"])
        val = r["val"]
        if val not in (None, "", 0):
            try:
                values[tid] = float(val)
            except (TypeError, ValueError):
                pass
    return values


def layout_templates() -> List[dict]:
    """Chart layout templates -> receiveLayoutTemplates(list); [] without the table."""
    from db.connection import fetch_all, table_exists
    if not table_exists("tblSmartChartTemplate"):
        return []
    tpls = fetch_all(
        "SELECT ID, Name, Description, IsDefault FROM tblSmartChartTemplate "
        "ORDER BY IsDefault DESC, SortOrder ASC, ID ASC", []
    )
    result = []
    for t in tpls:
        blocks = fetch_all(
            "SELECT ChartType, XAxisKey, YAxisKey, ZAxisKey, SortOrder "
            "FROM tblSmartChartTemplateBlock WHERE TemplateID = ? "
            "ORDER BY SortOrder ASC", [int(t["ID"])]
        )
        result.append({
            "id":          int(t["ID"]),
            "name":        str(t["Name"] or ""),
            "description": str(t["Description"] or ""),
            "isDefault":   bool(t["IsDefault"]),
            "blocks": [
                {
                    "chartType": str(b["ChartType"] or "bar"),
                    "xKey":      str(b["XAxisKey"]  or ""),
                    "yKey":      str(b["YAxisKey"]  or ""),
                    "zKey":      str(b["ZAxisKey"]  or ""),
                } for b in blocks
            ],
        })
    return result


_PDF_TEMPLATE_FALLBACK = {"id": None, "name": "Heberlein Standard (Default)", "description": "", "isDefault": True}


def pdf_templates() -> List[dict]:
    """PDF layouts for the export dialog -> receivePdfTemplates(list).

    Never empty: without the table, without active rows or on an error the
    page gets the built-in "Heberlein Standard (Default)" (error text in its
    description) - otherwise the modal would hang.
    """
    try:
        from db.connection import fetch_all, table_exists
        if not table_exists("tblSmartChartPdfTemplate"):
            logger.warning("getPdfTemplates: table not found - sending default")
            return [dict(_PDF_TEMPLATE_FALLBACK)]
        rows = fetch_all(
            "SELECT ID, Name, Description, IsDefault "
            "FROM tblSmartChartPdfTemplate "
            "WHERE IsActive = 1 ORDER BY IsDefault DESC, ID ASC",
            []
        )
        if not rows:
            logger.warning("getPdfTemplates: no active templates found")
            return [dict(_PDF_TEMPLATE_FALLBACK)]
        templates = [
            {
                "id":          int(r["ID"]),
                "name":        str(r["Name"] or ""),
                "description": str(r["Description"] or ""),
                "isDefault":   bool(r["IsDefault"]),
            }
            for r in rows
        ]
        logger.info("getPdfTemplates: %d Templates geladen", len(templates))
        return templates
    except Exception as e:
        logger.error("getPdfTemplates: %s", e)
        return [dict(_PDF_TEMPLATE_FALLBACK, description=str(e))]


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def save_report(data: dict, user: Optional[dict]) -> Dict[str, Any]:
    """Save or update a report with its blocks -> {"id", "forked", "message"}.

    Page: receiveSaveResult(id, true, message, forked). Only the original
    author (by UserID) may overwrite a report; anybody else gets a new,
    independent copy with himself as author (forked=True). Raises on errors
    (page: receiveSaveResult(null, false, str(e), false)).
    """
    from db.connection import fetch_all, execute, execute_insert

    report_id   = data.get("id")
    title       = data.get("title", "").strip()
    author      = data.get("author", "").strip()
    source_type = data.get("sourceType", "visual")
    series_pk   = data.get("seriesPK")
    query_cfg   = json.dumps(data.get("queryConfig", {}))
    show_info   = int(data.get("showInfobox", 1))
    info_pos    = data.get("infoboxPosition", "left")
    blocks      = data.get("blocks", [])
    global_note = data.get("globalNote", "").strip()
    user_id     = _user(user).get("id")

    # Nur der urspruengliche Autor (per UserID, NICHT dem frei
    # editierbaren "Author"-Textfeld - das zeigt bei jedem geladenen
    # Report erstmal den ORIGINAL-Autor an, siehe report_html_template.py
    # openReport()/loadReport()) darf einen bestehenden Report
    # ueberschreiben (2026-08-27, Nutzerwunsch: "so kann man nicht
    # reports von jemand anderem zerstoeren"). Oeffnet ein ANDERER
    # Nutzer einen fremden Report, aendert etwas und speichert, wird
    # daraus automatisch eine neue, unabhaengige Kopie mit ihm selbst
    # als Autor - der Original-Report bleibt unangetastet. Reports
    # ohne UserID (aeltere Zeilen von vor dieser Spalte, aktuell auf
    # dev_local nicht vorhanden, aber die Spalte ist nullable) haben
    # keinen erkennbaren Besitzer und bleiben frei ueberschreibbar.
    forked = False
    if report_id:
        owner_rows = fetch_all(
            "SELECT UserID FROM tblSmartChartReport WHERE ID=?", [report_id])
        if not owner_rows:
            report_id = None  # Report existiert nicht mehr - wie neu behandeln
        else:
            owner_id = owner_rows[0]["UserID"]
            if owner_id is not None and user_id is not None and int(owner_id) != int(user_id):
                forked = True
                report_id = None
                # Client-seitiges Author-Feld ignorieren (zeigt evtl.
                # noch den ORIGINAL-Autor) - die neue Kopie gehört
                # eindeutig dem aktuell eingeloggten Nutzer.
                author = str(_user(user).get("username") or author)

    if report_id:
        execute(
            "UPDATE tblSmartChartReport SET Title=?, Author=?, SourceType=?, "
            "SeriesPK=?, QueryConfigJSON=?, ShowInfobox=?, InfoboxPosition=?, "
            "UpdatedAt=NOW() WHERE ID=?",
            [title, author, source_type, series_pk, query_cfg,
             show_info, info_pos, report_id]
        )
        execute("DELETE FROM tblSmartChartBlock WHERE ReportID=? AND ID > 0", [report_id])
        execute("DELETE FROM tblSmartChartNote WHERE ReportID=? AND ID > 0", [report_id])
    else:
        # execute_insert(): liest die ID über cur.lastrowid auf derselben
        # Session wie der Insert selbst (siehe CLAUDE.md) - das frühere
        # execute()+SELECT LAST_INSERT_ID() traf gelegentlich eine andere
        # Pool-Connection und lieferte 0/NULL.
        report_id = execute_insert(
            "INSERT INTO tblSmartChartReport "
            "(Title, Author, SourceType, SeriesPK, QueryConfigJSON, "
            "ShowInfobox, InfoboxPosition, UserID) VALUES (?,?,?,?,?,?,?,?)",
            [title, author, source_type, series_pk, query_cfg,
             show_info, info_pos, user_id]
        )

    if not report_id:
        raise Exception("Could not determine report ID after save")

    # Save blocks
    for b in blocks:
        execute(
            "INSERT INTO tblSmartChartBlock "
            "(ReportID, BlockType, SortOrder, ChartIndex, XField, YKey, ZField, "
            "ChartMode, ImageData, ImageTitle, ImageWidth, NoteTitle, NoteText, NoteVisible, "
            "GridlinesY, GridlinesVisible) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                report_id,
                b.get("blockType", "chart"),
                b.get("sortOrder", 0),
                b.get("chartIndex"),
                b.get("xField"),
                b.get("yKey"),
                b.get("zField"),
                b.get("chartMode", "2d"),
                b.get("imageData"),
                b.get("imageTitle"),
                b.get("imageWidth", "full"),
                b.get("noteTitle"),
                b.get("noteText"),
                int(b.get("noteVisible", True)),
                b.get("gridlinesY", ""),
                int(b.get("gridlinesVisible", False)),
            ]
        )

    # Save global note
    if global_note:
        execute(
            "INSERT INTO tblSmartChartNote "
            "(ReportID, NoteType, NoteTitle, NoteText, IsVisible) VALUES (?,?,?,?,?)",
            [report_id, "global", "Summary", global_note, 1]
        )

    msg = ("Report saved successfully" if not forked else
           "You are not the author of this report - your changes were "
           "saved as a new, independent report instead.")
    # The desktop wrote the id unquoted into the JS - an int here keeps
    # "12" and 12 the same number on the page.
    return {"id": int(report_id), "forked": forked, "message": msg}


class ReportPermissionError(Exception):
    """The user may not delete this report."""


def can_delete_report(report_id: int, user: Optional[dict]) -> bool:
    """Same owner rule as overwriting (save_report): the author (by UserID) or a
    superuser; old reports without UserID stay free (2026-11-13 - before, anybody
    could delete any report)."""
    from db.connection import fetch_all
    u = _user(user)
    try:
        if int(u.get("access_level") or 0) >= 4:
            return True
    except (TypeError, ValueError):
        pass
    rows = fetch_all("SELECT UserID FROM tblSmartChartReport WHERE ID=?", [int(report_id)])
    if not rows:
        return True                     # already gone - deleting is a no-op
    owner = rows[0].get("UserID")
    if owner is None:
        return True
    try:
        return u.get("id") is not None and int(owner) == int(u.get("id"))
    except (TypeError, ValueError):
        return False


def delete_report(report_id: int, user: Optional[dict] = None) -> int:
    """Delete a report (CASCADE deletes blocks + notes) -> receiveDeleteResult(id).
    ReportPermissionError if `user` is not the author or a superuser."""
    from db.connection import execute
    rid = int(report_id)
    if not can_delete_report(rid, user):
        raise ReportPermissionError("Only the author or a superuser can delete this report.")
    execute("DELETE FROM tblSmartChartReport WHERE ID=?", [rid])
    return rid


class TemplateError(Exception):
    """Layout template not saved for a reason the page shows as message."""


def save_layout_template(payload: dict) -> int:
    """New layout template {name, description, createdBy, blocks} -> new ID.

    Page: receiveLayoutTemplateSaved(true, ""); TemplateError/other errors
    -> receiveLayoutTemplateSaved(false, message).
    """
    from db.connection import get_connection, table_exists
    if not table_exists("tblSmartChartTemplate"):
        raise TemplateError("Table not found")
    p = payload
    # Alles in EINER Connection → lastrowid zuverlässig
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            "INSERT INTO tblSmartChartTemplate (Name, Description, IsDefault, SortOrder, CreatedBy) "
            "VALUES (?, ?, 0, 99, ?)",
            [p["name"], p.get("description",""), p.get("createdBy","")]
        )
        new_id = cur.lastrowid
        for i, b in enumerate(p.get("blocks",[])):
            cur.execute(
                "INSERT INTO tblSmartChartTemplateBlock "
                "(TemplateID, SortOrder, ChartType, XAxisKey, YAxisKey, ZAxisKey) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [new_id, i, b.get("chartType","bar"),
                 b.get("xKey",""), b.get("yKey",""), b.get("zKey","")]
            )
    logger.info("saveLayoutTemplate: '%s' gespeichert (ID=%s)", p["name"], new_id)
    return new_id


def overwrite_layout_template(payload: dict, user: Optional[dict]) -> int:
    """Overwrite layout template payload["id"] (name, description, blocks).

    The default template only for superusers (TemplateError otherwise).
    Page: receiveLayoutTemplateSaved(true, "") / (false, message).
    """
    from db.connection import get_connection, fetch_all
    p = payload
    tid = int(p["id"])
    rows = fetch_all("SELECT IsDefault FROM tblSmartChartTemplate WHERE ID = ?", [tid])
    if rows and rows[0].get("IsDefault") and not is_superuser(user):
        raise TemplateError("Only superusers can edit the default template")
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute("UPDATE tblSmartChartTemplate SET Name=?, Description=? WHERE ID=?",
                    [p["name"], p.get("description",""), tid])
        cur.execute("DELETE FROM tblSmartChartTemplateBlock WHERE TemplateID=?", [tid])
        for i, b in enumerate(p.get("blocks",[])):
            cur.execute(
                "INSERT INTO tblSmartChartTemplateBlock "
                "(TemplateID, SortOrder, ChartType, XAxisKey, YAxisKey, ZAxisKey) "
                "VALUES (?,?,?,?,?,?)",
                [tid, i, b.get("chartType","bar"),
                 b.get("xKey",""), b.get("yKey",""), b.get("zKey","")]
            )
    logger.info("overwriteLayoutTemplate: ID=%d überschrieben", tid)
    return tid


def delete_layout_template(template_id: int) -> bool:
    """Delete a layout template; False for the default template (kept).

    Page: receiveLayoutTemplateDeleted(ok, id) - (false, 0) on an error.
    """
    from db.connection import execute, fetch_all
    tid = int(template_id)
    # IsDefault-Templates nicht löschbar
    rows = fetch_all("SELECT IsDefault FROM tblSmartChartTemplate WHERE ID = ?", [tid])
    if rows and rows[0].get("IsDefault"):
        return False
    execute("DELETE FROM tblSmartChartTemplate WHERE ID = ?", [tid])
    logger.info("deleteLayoutTemplate: ID=%d gelöscht", tid)
    return True


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def pdf_default_filename(payload: dict, now: Optional[datetime.datetime] = None) -> str:
    """Suggested file name: SmartChart_<title>_<yyyymmdd>.pdf."""
    now = now or datetime.datetime.now()
    safe  = re.sub(r'[^\w\s-]', '', payload.get("reportTitle", "SmartChart")).strip()
    safe  = re.sub(r'\s+', '_', safe)
    return f"SmartChart_{safe}_{now.strftime('%Y%m%d')}.pdf"


def build_report_pdf(payload: dict, now: Optional[datetime.datetime] = None) -> bytes:
    """Heberlein-branded report PDF (reportlab) from the page's export payload.

    payload = what the page sends to exportPdf (reportTitle, author,
    sourceType, reportId, infobox, showInfobox, globalNote, pdfTemplateId,
    charts = [{title, xLabel, yLabel, b64 (PNG), blockType, imageWidth,
    noteVisible, noteTitle, noteText, valueNotes}]). Returns the PDF bytes.
    """
    import base64, io
    from ui.report_pdf_layout import (
        _meta_cell, _section_hdr, _infobox_table, _note_block, _load_pdf_template,
    )

    charts    = payload.get("charts", [])
    infobox   = payload.get("infobox", {})
    now       = now or datetime.datetime.now()
    date_str  = now.strftime("%d.%m.%Y")
    gen_str   = now.strftime("%d.%m.%Y %H:%M")
    T         = _load_pdf_template(payload.get("pdfTemplateId"))

    # ── reportlab imports ─────────────────────────────────────────
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm, mm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
    from reportlab.platypus import (
        BaseDocTemplate, PageTemplate, Frame,
        Paragraph, Spacer, Table, TableStyle,
        HRFlowable, Image as RLImage, PageBreak, NextPageTemplate,
        KeepTogether,
    )
    from reportlab.platypus.flowables import Flowable

    # ── Colours ───────────────────────────────────────────────────
    HEB_GREEN  = colors.HexColor(T.get("accentColor",  "#39A650"))
    HEB_NAVY   = colors.HexColor(T.get("navyColor",    "#1D3557"))
    ROW_LIGHT  = colors.HexColor("#F2F9F3")
    GREY_TEXT  = colors.HexColor("#555555")
    LIGHT_GREY = colors.HexColor("#AAAAAA")

    PW, PH = A4
    ml = mr = 1.6 * cm
    mt = 1.4 * cm
    mb = 1.8 * cm

    report_title = payload.get("reportTitle", "SmartChart Report")
    author       = payload.get("author", "")

    def _x(s):
        """Escape user strings for reportlab XML paragraph parser."""
        return str(s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    valid_charts = [ch for ch in charts if ch]

    # ── Logo helper ───────────────────────────────────────────────
    def _logo_img(h_cm=1.4):
        try:
            import pathlib
            proj = pathlib.Path(__file__).resolve().parents[1]
            lp   = proj / "assets" / "images" / "heb_logo.png"
            if lp.exists():
                return RLImage(str(lp), width=5*cm, height=h_cm*cm,
                               kind="proportional")
        except Exception:
            pass
        return Paragraph(
            '<font color="#39A650"><b>HEBERLEIN</b></font>',
            ParagraphStyle("logo", fontSize=14, fontName="Helvetica-Bold")
        )

    def _logo_r_img(h_cm=1.4):
        try:
            import pathlib
            proj = pathlib.Path(__file__).resolve().parents[1]
            lp   = proj / "assets" / "images" / "header_logo_big.png"
            if lp.exists():
                return RLImage(str(lp), width=2*cm, height=h_cm*cm,
                               kind="proportional")
        except Exception:
            pass
        return Paragraph("")

    # ── Styles ────────────────────────────────────────────────────
    def _s(name, **kw):
        return ParagraphStyle(name, **kw)

    s_normal = _s("n", fontSize=9,  fontName="Helvetica",
                  textColor=GREY_TEXT, leading=13)
    s_small  = _s("sm", fontSize=8, fontName="Helvetica",
                  textColor=GREY_TEXT, leading=11)
    s_h1     = _s("h1", fontSize=12, fontName="Helvetica-Bold",
                  textColor=HEB_NAVY, spaceBefore=6, spaceAfter=3)
    s_h2     = _s("h2", fontSize=10, fontName="Helvetica-Bold",
                  textColor=HEB_NAVY, spaceBefore=4, spaceAfter=2)
    s_label  = _s("lbl", fontSize=7, fontName="Helvetica",
                  textColor=LIGHT_GREY, leading=10)
    s_value  = _s("val", fontSize=9, fontName="Helvetica-Bold",
                  textColor=HEB_NAVY, leading=12)
    s_tag    = _s("tag", fontSize=8, fontName="Helvetica",
                  textColor=GREY_TEXT, leading=11)
    s_note   = _s("note", fontSize=8.5, fontName="Helvetica",
                  textColor=GREY_TEXT, leading=13, leftIndent=6)

    # ── Page templates ────────────────────────────────────────────
    # Cover: full bleed, no header/footer frame
    cover_frame = Frame(0, 0, PW, PH, leftPadding=0, rightPadding=0,
                        topPadding=0, bottomPadding=0)

    # Content pages: header + footer drawn in onPage callback
    content_frame = Frame(ml, mb + 0.6*cm, PW - ml - mr,
                          PH - mt - mb - 1.2*cm,
                          leftPadding=0, rightPadding=0,
                          topPadding=0, bottomPadding=0)

    class _RL_Doc(BaseDocTemplate):
        def __init__(self, path, **kw):
            super().__init__(path, **kw)
            self._page_count = 0

    def _cover_page(canvas, doc):
        """Draw cover page — green bottom bar, no top bar."""
        canvas.saveState()
        # Green bar bottom
        canvas.setFillColor(HEB_GREEN)
        canvas.rect(0, 0, PW, 8*mm, fill=1, stroke=0)
        # Bottom text in white
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.white)
        canvas.drawString(ml, 2.5*mm,
            "Heberlein Technology AG · Wattwil, Switzerland")
        canvas.drawRightString(PW - mr, 2.5*mm, f"Generated: {gen_str}")
        canvas.restoreState()

    def _content_page(canvas, doc):
        """Draw header + footer on content pages."""
        canvas.saveState()
        # Header: logo left, title center, logo-r right
        try:
            import pathlib
            proj = pathlib.Path(__file__).resolve().parents[1]
            lp   = proj / "assets" / "images" / "heb_logo.png"
            if lp.exists():
                canvas.drawImage(str(lp), ml, PH - mt - 3*mm,
                                 width=3.5*cm, height=10*mm,
                                 preserveAspectRatio=True, mask='auto')
        except Exception:
            canvas.setFont("Helvetica-Bold", 9)
            canvas.setFillColor(HEB_GREEN)
            canvas.drawString(ml, PH - mt, "HEBERLEIN")
        try:
            import pathlib
            proj = pathlib.Path(__file__).resolve().parents[1]
            rp   = proj / "assets" / "images" / "header_logo_big.png"
            if rp.exists():
                canvas.drawImage(str(rp), PW - mr - 1.8*cm,
                                 PH - mt - 3*mm,
                                 width=1.8*cm, height=10*mm,
                                 preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
        # Report title center
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GREY_TEXT)
        canvas.drawCentredString(PW / 2, PH - mt + 1*mm, report_title)
        # Green header line
        canvas.setStrokeColor(HEB_GREEN)
        canvas.setLineWidth(1.2)
        canvas.line(ml, PH - mt - 4*mm, PW - mr, PH - mt - 4*mm)
        # Footer line
        canvas.setStrokeColor(colors.HexColor("#E0E0E0"))
        canvas.setLineWidth(0.5)
        canvas.line(ml, mb - 2*mm, PW - mr, mb - 2*mm)
        # Footer text
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(GREY_TEXT)
        canvas.drawString(ml, mb - 6*mm, f"Calculation date: {date_str}")
        canvas.drawRightString(PW - mr, mb - 6*mm,
                               f"Page {doc.page}")
        canvas.restoreState()

    out = io.BytesIO()
    doc = _RL_Doc(
        out, pagesize=A4,
        leftMargin=ml, rightMargin=mr,
        topMargin=mt, bottomMargin=mb,
        title=report_title,
        author="Heberlein Technology AG",
    )
    doc.addPageTemplates([
        PageTemplate(id="Cover",   frames=[cover_frame],
                     onPage=_cover_page),
        PageTemplate(id="Content", frames=[content_frame],
                     onPage=_content_page),
    ])

    # ── Story ─────────────────────────────────────────────────────
    story = []

    # ── COVER ─────────────────────────────────────────────────────
    story.append(NextPageTemplate("Content"))

    story.append(Spacer(1, 10*mm))

    # Logo on cover
    logo_tbl = Table(
        [[_logo_img(1.8), ""]],
        colWidths=[10*cm, PW - 10*cm]
    )
    logo_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), ml),
    ]))
    story.append(logo_tbl)
    story.append(Spacer(1, 20*mm))

    # Cover kicker
    story.append(Spacer(1, 0))
    p_kicker = Paragraph(
        "HEBERLEIN TECHNOLOGY AG",
        _s("kicker", fontSize=8, fontName="Helvetica",
           textColor=LIGHT_GREY, leftIndent=ml,
           charSpace=2)
    )
    story.append(p_kicker)
    story.append(Spacer(1, 3*mm))

    # Green divider
    story.append(HRFlowable(width=12*mm, thickness=2,
                            color=HEB_GREEN, hAlign="LEFT"))
    story.append(Spacer(1, 4*mm))

    # Title
    story.append(Paragraph(
        f'<font color="#1D3557"><b>{_x(report_title)}</b></font>',
        _s("cvtitle", fontSize=26, fontName="Helvetica-Bold",
           leading=30, leftIndent=ml)
    ))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "SmartChart Analysis Report · TrippleT",
        _s("cvsub", fontSize=10, fontName="Helvetica",
           textColor=LIGHT_GREY, leftIndent=ml)
    ))
    story.append(Spacer(1, 10*mm))

    # Cover meta grid
    meta_rows = [
        [
            _meta_cell("Author",   author,           s_label, s_value),
            _meta_cell("Date",     date_str,         s_label, s_value),
            _meta_cell("Source",   payload.get("sourceType",""), s_label, s_value),
        ],
        [
            _meta_cell("Series",   infobox.get("seriesName",""), s_label, s_value),
            _meta_cell("Charts",   str(len(valid_charts)), s_label, s_value),
            _meta_cell("Report ID", f"#{payload.get('reportId','—')}", s_label, s_value),
        ],
    ]
    col_w = (PW - ml - mr) / 3
    meta_tbl = Table(meta_rows,
                     colWidths=[col_w, col_w, col_w])
    meta_tbl.setStyle(TableStyle([
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), ml),
        ("TOPPADDING",  (0,0), (-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ]))
    story.append(meta_tbl)

    # ── OVERVIEW page ─────────────────────────────────────────────
    story.append(PageBreak())
    story.append(_section_hdr("Overview", HEB_GREEN, HEB_NAVY, s_h1))

    # Infobox
    if payload.get("showInfobox", True):
        story.append(_infobox_table(infobox, HEB_GREEN, HEB_NAVY,
                                    s_label, s_value, s_tag, PW, ml, mr))
        story.append(Spacer(1, 4*mm))

    # Global note
    if payload.get("globalNote","").strip():
        story.append(_note_block(
            "Observations", payload["globalNote"],
            s_h2, s_note, HEB_NAVY
        ))
        story.append(Spacer(1, 4*mm))

    # Conclusion of the series (button "✅ Conclusion" on the page) - read fresh from the database,
    # the page only says which series
    if payload.get("conclusionSeries"):
        try:
            from db import series_conclusion as _sc
            if _sc.table_ready():
                for _c in _sc.for_report(payload.get("conclusionSeries") or []):
                    _title = f"Conclusion – {_c['name']}" + (f" ({_c['outcome_label']})" if _c.get("outcome_label") else "")
                    story.append(_note_block(_title, _sc.report_text(_c), s_h2, s_note, HEB_NAVY))
                    story.append(Spacer(1, 3*mm))
        except Exception as _e:
            logger.error("PDF conclusion: %s", _e)

    # ── CHART pages ───────────────────────────────────────────────
    chart_w   = PW - ml - mr
    content_h = PH - mt - mb - 1.2*cm
    usable_h  = content_h - 14*mm

    # Group: 2 charts per page if both have no note, else 1
    chart_pages = []
    buf = []
    for ch in valid_charts:
        if not ch:
            continue
        has_note = bool(ch.get("noteVisible") and ch.get("noteText", "").strip()) \
            or bool(ch.get("valueNotes"))
        is_image = ch.get("blockType") == "image"
        if is_image and ch.get("imageWidth") != "half":
            if buf: chart_pages.append(buf); buf = []
            chart_pages.append([ch])
        elif has_note:
            if buf: chart_pages.append(buf); buf = []
            chart_pages.append([ch])
        else:
            buf.append(ch)
            if len(buf) >= 2:
                chart_pages.append(buf); buf = []
    if buf:
        chart_pages.append(buf)

    # First page: merge section header + first chart group so they
    # always land on the same page (no orphan header)
    first_chart_page = True
    for pg_idx, pg_charts in enumerate(chart_pages):
        if first_chart_page:
            first_chart_page = False
            # Header on new page, charts follow immediately (no extra PageBreak)
            story.append(PageBreak())
            story.append(_section_hdr("Analysis Charts", HEB_GREEN, HEB_NAVY, s_h1))
        else:
            story.append(PageBreak())

        n_on_page = len(pg_charts)
        # Height per chart: split usable height equally, min 80mm, max 130mm
        h_per = max(80*mm, min(130*mm, usable_h / n_on_page - 8*mm))

        for ch in pg_charts:
            x_lbl = ch.get("xLabel","")
            y_lbl = ch.get("yLabel","")
            sub   = f"X: {_x(x_lbl)}  ·  Y: {_x(y_lbl)}" if x_lbl or y_lbl else ""

            block = []
            block.append(Paragraph(
                f'<font color="#1D3557"><b>{_x(ch.get("title",""))}</b></font>'
                + (f'  <font size="7" color="#aaaaaa">{_x(sub)}</font>' if sub else ""),
                _s("chtitle", fontSize=10, fontName="Helvetica-Bold",
                   textColor=HEB_NAVY, spaceAfter=2)
            ))

            if ch.get("b64"):
                img_bytes = base64.b64decode(ch["b64"])
                img_buf   = io.BytesIO(img_bytes)
                if ch.get("blockType") == "image":
                    iw = chart_w * 0.5 if ch.get("imageWidth") == "half" else chart_w * 0.8
                    block.append(RLImage(img_buf, width=iw,
                                         height=iw * 0.6, kind="proportional"))
                else:
                    block.append(RLImage(img_buf, width=chart_w, height=h_per))

            if ch.get("noteVisible") and ch.get("noteText","").strip():
                block.append(_note_block(
                    ch.get("noteTitle",""), ch["noteText"],
                    s_h2, s_note, HEB_NAVY
                ))

            # Notes on values - only present when "Include notes on
            # values" was ticked in the export dialog (db/cell_notes.py)
            if ch.get("valueNotes"):
                block.append(_note_block(
                    "Notes on values", value_notes_text(ch["valueNotes"]),
                    s_h2, s_note, HEB_NAVY
                ))

            block.append(Spacer(1, 4*mm))
            story.append(KeepTogether(block))

    # ── Build ─────────────────────────────────────────────────────
    doc.build(story)
    return out.getvalue()


# ---------------------------------------------------------------------------
# Slot protocol (desktop bridge and web app)
# ---------------------------------------------------------------------------

def _num_or_raw(s):
    """JS sends ids as String(n); the desktop wrote them unquoted into the
    JS call - an int keeps that (a non-number stays the string)."""
    try:
        return int(s)
    except (TypeError, ValueError):
        return s


def _slot_getSeriesList(*, user, series_pk):
    try:
        return "receiveSeriesList", [series_list()]
    except Exception as e:
        logger.error("getSeriesList: %s", e)
        return None


def _slot_loadSeriesData(series_pk_str, color, *, user, series_pk):
    try:
        spk = int(series_pk_str)
        d = series_data(spk)
        return "receiveSeriesData", [spk, d["name"], color, d["data"], d["meta"]]
    except Exception as e:
        logger.error("loadSeriesData %s: %s", series_pk_str, e)
        return None


def _slot_runVisualQuery(series_pks_json, group_by, filters_json, adv_filters_json='[]',
                         *, user, series_pk):
    try:
        series_pks = json.loads(series_pks_json) or []
        filters    = json.loads(filters_json) or []
        adv        = json.loads(adv_filters_json) if adv_filters_json else []
        rows = run_visual_query(series_pks, group_by, filters, adv)
    except Exception as e:
        logger.exception("runVisualQuery: %s", e)
        # don't leave the page on "Loading..." with an old chart
        rows = []
    return "receiveQueryResult", [rows, len(rows)]


def _slot_loadConclusions(series_pks_json, *, user, series_pk):
    """Conclusion block (button "✅ Conclusion"): the conclusions of the shown series (db/series_conclusion)."""
    try:
        from db import series_conclusion as sc
        if not sc.table_ready():
            return "receiveConclusions", [[], False]
        pks = json.loads(series_pks_json or "[]") or []
        return "receiveConclusions", [sc.for_report(pks), True]
    except Exception as e:
        logger.error("loadConclusions: %s", e)
        return "receiveConclusions", [[], False]


def _slot_saveReport(report_json, *, user, series_pk):
    try:
        r = save_report(json.loads(report_json), user)
        return "receiveSaveResult", [r["id"], True, r["message"], r["forked"]]
    except Exception as e:
        logger.error("saveReport: %s", e)
        return "receiveSaveResult", [None, False, str(e), False]


def _slot_loadReportList(*, user, series_pk):
    try:
        return "receiveReportList", [report_list()]
    except Exception as e:
        logger.error("loadReportList: %s", e)
        return None


def _slot_loadReport(report_id_str, *, user, series_pk):
    try:
        rep = load_report(int(report_id_str))
        return ("receiveReport", [rep]) if rep is not None else None
    except Exception as e:
        logger.error("loadReport: %s", e)
        return None


def _slot_deleteReport(report_id_str, *, user, series_pk):
    try:
        return "receiveDeleteResult", [delete_report(int(report_id_str), user)]
    except ReportPermissionError as e:
        return "receiveDeleteDenied", [str(e)]
    except Exception as e:
        logger.error("deleteReport: %s", e)
        return None


def _slot_loadFreeField(table, field, condition, chart_idx, y_key, *, user, series_pk):
    try:
        values = free_field_values(series_pk, table, field, condition)
        if values is None:
            return None
        return "receiveFreeFieldData", [_num_or_raw(chart_idx), y_key, values]
    except Exception as e:
        logger.error("loadFreeField %s.%s: %s", table, field, e)
        return None


def _slot_getLayoutTemplates(*, user, series_pk):
    try:
        return "receiveLayoutTemplates", [layout_templates()]
    except Exception as e:
        logger.error("getLayoutTemplates: %s", e)
        return "receiveLayoutTemplates", [[]]


def _slot_saveLayoutTemplate(payload_json, *, user, series_pk):
    try:
        save_layout_template(json.loads(payload_json))
        return "receiveLayoutTemplateSaved", [True, ""]
    except TemplateError as e:
        return "receiveLayoutTemplateSaved", [False, str(e)]
    except Exception as e:
        logger.error("saveLayoutTemplate: %s", e)
        return "receiveLayoutTemplateSaved", [False, str(e)]


def _slot_overwriteLayoutTemplate(payload_json, *, user, series_pk):
    try:
        overwrite_layout_template(json.loads(payload_json), user)
        return "receiveLayoutTemplateSaved", [True, ""]
    except TemplateError as e:
        return "receiveLayoutTemplateSaved", [False, str(e)]
    except Exception as e:
        logger.error("overwriteLayoutTemplate: %s", e)
        return "receiveLayoutTemplateSaved", [False, str(e)]


def _slot_deleteLayoutTemplate(template_id_str, *, user, series_pk):
    try:
        tid = int(template_id_str)
        return "receiveLayoutTemplateDeleted", [delete_layout_template(tid), tid]
    except Exception as e:
        logger.error("deleteLayoutTemplate: %s", e)
        return "receiveLayoutTemplateDeleted", [False, 0]


def _slot_getPdfTemplates(*, user, series_pk):
    return "receivePdfTemplates", [pdf_templates()]


# slot name (as the page calls _bridge.<slot>) -> (handler, receive function, read/write)
SLOTS = {
    "getSeriesList":           (_slot_getSeriesList,           "receiveSeriesList",          "read"),
    "loadSeriesData":          (_slot_loadSeriesData,          "receiveSeriesData",          "read"),
    "runVisualQuery":          (_slot_runVisualQuery,          "receiveQueryResult",         "read"),
    "loadReportList":          (_slot_loadReportList,          "receiveReportList",          "read"),
    "loadReport":              (_slot_loadReport,              "receiveReport",              "read"),
    "loadFreeField":           (_slot_loadFreeField,           "receiveFreeFieldData",       "read"),
    "getLayoutTemplates":      (_slot_getLayoutTemplates,      "receiveLayoutTemplates",     "read"),
    "getPdfTemplates":         (_slot_getPdfTemplates,         "receivePdfTemplates",        "read"),
    "loadConclusions":         (_slot_loadConclusions,         "receiveConclusions",         "read"),
    "saveReport":              (_slot_saveReport,              "receiveSaveResult",          "write"),
    "deleteReport":            (_slot_deleteReport,            "receiveDeleteResult",        "write"),
    "saveLayoutTemplate":      (_slot_saveLayoutTemplate,      "receiveLayoutTemplateSaved", "write"),
    "overwriteLayoutTemplate": (_slot_overwriteLayoutTemplate, "receiveLayoutTemplateSaved", "write"),
    "deleteLayoutTemplate":    (_slot_deleteLayoutTemplate,    "receiveLayoutTemplateDeleted", "write"),
}

# Qt-only slots (no DB): copyImageToClipboard (clipboard), addImage (file
# dialog -> receiveImage), exportPdf (save dialog around build_report_pdf ->
# receivePdfResult), jsError (log + message box).


def handle(slot: str, args, *, user: Optional[dict] = None,
           series_pk: Optional[int] = None) -> Optional[Tuple[str, list]]:
    """Run one bridge slot exactly as the page calls it.

    args = the slot's arguments as the page sends them (strings, JSON as
    text); user = the logged-in user (dict like app_meta.current_user);
    series_pk = the primary series of the open report (loadFreeField).
    Returns (receive function, [arguments]) or None (the page gets no
    answer). Errors never raise - they become the answer the page expects.
    """
    fn = SLOTS[slot][0]
    return fn(*args, user=user, series_pk=series_pk)


# receive functions the desktop always wrote without a space after the comma
_COMPACT = {"receiveLayoutTemplateSaved", "receiveLayoutTemplateDeleted"}


def js_call(receiver: str, args) -> str:
    """JS the desktop runs for a handle() result: receiveX(arg1, arg2);"""
    sep = "," if receiver in _COMPACT else ", "
    return f"{receiver}({sep.join(json.dumps(a) for a in args)});"
