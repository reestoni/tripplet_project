from __future__ import annotations
# ui/screen_report.py
"""Report-Screen für TrippleT – Visualisierung einer TrialSeries."""

import json
import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QSizePolicy, QMessageBox, QFrame,
)
from PySide6.QtCore import QSize

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineScript
    from PySide6.QtWebChannel import QWebChannel
    from PySide6.QtCore import QObject, Slot
    _WEB_ENGINE_AVAILABLE = True
except ImportError:
    _WEB_ENGINE_AVAILABLE = False
    QObject = object
    def Slot(*a, **kw):
        def dec(f): return f
        return dec

from ui.pathutil import resource_path, web_base_url
from ui.report_html_template import _HTML_TEMPLATE
from ui.report_queries import (
    Y_AXES, X_AXES, KNOWN_TABLES,
    _get_known_tables, _load_axes_from_db,
    _fetch_y_values, _fetch_table_columns, _fetch_series_data,
    _fetch_infobox_data, with_category_axes,
)
from ui.report_pdf_layout import (
    _PDF_TEMPLATE_DEFAULTS,
    _meta_cell, _section_hdr, _infobox_table, _note_block, _load_pdf_template,
)
from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from db.trial_reference import exclude_references_sql
import app_meta

logger = logging.getLogger(__name__)

# ── Smart Chart: advanced filters ─────────────────────────────────────────
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
    import re
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
# Bridge: Python <-> JavaScript fuer Freifeld-Nachladen
# ---------------------------------------------------------------------------

class _ReportBridge(QObject):

    def __init__(self, screen):
        super().__init__(screen)
        self._screen = screen

    @Slot(str)
    def copyImageToClipboard(self, b64_png: str) -> None:
        try:
            import base64
            from PySide6.QtGui import QImage, QClipboard
            from PySide6.QtWidgets import QApplication
            img_bytes = base64.b64decode(b64_png)
            img = QImage()
            img.loadFromData(img_bytes, "PNG")
            if not img.isNull():
                QApplication.clipboard().setImage(img, QClipboard.Clipboard)
        except Exception as e:
            logger.error("copyImageToClipboard: %s", e)

    @Slot()
    def getSeriesList(self):
        try:
            from db.connection import fetch_all
            rows = fetch_all(
                "SELECT TS.ID AS pk, TS.SeriesName AS name, "
                "E.[Experiment ID] AS exp_id "
                "FROM tblTrialSeries AS TS "
                "LEFT JOIN tblExperimente AS E ON E.ID = TS.ExperimentID "
                "LIMIT 500",
                []
            )
            import json as _json
            series_list = []
            for r in rows:
                pk   = int(r.get("pk") or 0)
                name = str(r.get("name") or "")
                exp  = str(r.get("exp_id") or "")
                label = f"{exp}.{name}" if exp else name
                series_list.append({"pk": pk, "name": label})
            # Absteigend nach Label sortieren (neueste Experiment-ID zuerst)
            series_list.sort(key=lambda x: x["name"], reverse=True)
            js = f"receiveSeriesList({_json.dumps(series_list)});"
            if self._screen._web:
                self._screen._web.page().runJavaScript(js)
        except Exception as e:
            logger.error("getSeriesList: %s", e)

    @Slot(str, str)
    def loadSeriesData(self, series_pk_str, color):
        try:
            series_pk = int(series_pk_str)
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
            import json as _json
            meta = {"machine": machine, "material": material}
            js = f"receiveSeriesData({series_pk}, {_json.dumps(series_name)}, {_json.dumps(color)}, {_json.dumps(data)}, {_json.dumps(meta)});"
            if self._screen._web:
                self._screen._web.page().runJavaScript(js)
        except Exception as e:
            logger.error("loadSeriesData %s: %s", series_pk_str, e)


    @Slot(str, str, str, str)
    def runVisualQuery(self, series_pks_json, group_by, filters_json, adv_filters_json='[]'):
        try:
            import json as _json
            from db.connection import fetch_all

            series_pks = _json.loads(series_pks_json) or []
            filters    = _json.loads(filters_json) or []

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
                    _g_axes_map[_g['key']] = {'expr': _expr, 'alias': _alias, 'join_sql': _g.get('join_sql')}
            # Collect all is_group_by X-axis keys so we can store group_label under them too
            _group_x_keys = [x['key'] for x in (db_x or []) if x.get('is_group_by')]

            if group_by in _g_axes_map:
                _ginfo = _g_axes_map[group_by]
                if _ginfo['join_sql']:
                    # JOIN-SQL: Alias einsetzen
                    _join = _ginfo['join_sql'].replace(_ginfo['join_sql'].split()[2], _ginfo['alias'])
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
            adv_filters = _json.loads(adv_filters_json) if adv_filters_json else []
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
                if self._screen._web:
                    self._screen._web.page().runJavaScript("receiveQueryResult([], 0);")
                return

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

            js = "receiveQueryResult(" + _json.dumps(rows) + ", " + str(len(rows)) + ");"
            if self._screen._web:
                self._screen._web.page().runJavaScript(js)
        except Exception as e:
            logger.exception("runVisualQuery: %s", e)
            # don't leave the page on "Loading..." with an old chart
            if self._screen._web:
                self._screen._web.page().runJavaScript("receiveQueryResult([], 0);")


    @Slot(str)
    def saveReport(self, report_json: str) -> None:
        """Save or update a SmartChart report with block-based structure."""
        try:
            import json as _json
            from db.connection import fetch_all, execute, execute_insert
            import app_meta

            data        = _json.loads(report_json)
            report_id   = data.get("id")
            title       = data.get("title", "").strip()
            author      = data.get("author", "").strip()
            source_type = data.get("sourceType", "visual")
            series_pk   = data.get("seriesPK")
            query_cfg   = _json.dumps(data.get("queryConfig", {}))
            show_info   = int(data.get("showInfobox", 1))
            info_pos    = data.get("infoboxPosition", "left")
            blocks      = data.get("blocks", [])
            global_note = data.get("globalNote", "").strip()
            user_id     = (app_meta.current_user or {}).get("id")

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
                        author = str((app_meta.current_user or {}).get("username") or author)

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
                # execute_insert() statt execute()+separatem fetch_all('SELECT
                # LAST_INSERT_ID()'): Letzteres zieht sich unabhängig eine
                # (nicht notwendigerweise dieselbe) Connection aus dem Pool,
                # wodurch LAST_INSERT_ID() gelegentlich 0/NULL liefert, obwohl
                # der Insert erfolgreich war - der bisherige "Title+Author,
                # ORDER BY ID DESC"-Fallback direkt darunter war vermutlich
                # genau dafür gedacht, ist aber selbst nicht robust (trifft bei
                # gleichzeitig laufenden Speichervorgängen mit identischem
                # Title/Author potenziell die falsche Zeile). execute_insert()
                # liest die ID stattdessen über cur.lastrowid auf derselben
                # Session wie der Insert selbst - siehe CLAUDE.md.
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
            js = ("receiveSaveResult(" + str(report_id) + ", true, "
                  + _json.dumps(msg) + ", " + ("true" if forked else "false") + ");")
            if self._screen._web:
                self._screen._web.page().runJavaScript(js)

        except Exception as e:
            logger.error("saveReport: %s", e)
            import json as _json2
            js = "receiveSaveResult(null, false, " + _json2.dumps(str(e)) + ", false);"
            if self._screen._web:
                self._screen._web.page().runJavaScript(js)

    @Slot()
    def loadReportList(self) -> None:
        """Load list of saved reports."""
        try:
            import json as _json
            from db.connection import fetch_all
            rows = fetch_all(
                "SELECT ID, Title, Author, SourceType, "
                "DATE_FORMAT(UpdatedAt, '%d.%m.%Y %H:%i') AS UpdatedStr "
                "FROM tblSmartChartReport WHERE IsTemplate=0 "
                "ORDER BY UpdatedAt DESC LIMIT 100", []
            )
            reports = [
                {"id": int(r["ID"]), "title": str(r["Title"] or ""),
                 "author": str(r["Author"] or ""), "sourceType": str(r["SourceType"] or ""),
                 "updated": str(r["UpdatedStr"] or "")}
                for r in rows
            ]
            js = "receiveReportList(" + _json.dumps(reports) + ");"
            if self._screen._web:
                self._screen._web.page().runJavaScript(js)
        except Exception as e:
            logger.error("loadReportList: %s", e)

    @Slot(str)
    def loadReport(self, report_id_str: str) -> None:
        """Load a full report including all blocks."""
        try:
            import json as _json
            from db.connection import fetch_all

            rid = int(report_id_str)
            rows = fetch_all("SELECT * FROM tblSmartChartReport WHERE ID=?", [rid])
            if not rows:
                return
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

            import json as _json2
            report = {
                "id":              rid,
                "title":           str(r["Title"] or ""),
                "author":          str(r["Author"] or ""),
                "sourceType":      str(r["SourceType"] or "visual"),
                "seriesPK":        r["SeriesPK"],
                "queryConfig":     _json2.loads(r["QueryConfigJSON"] or "{}"),
                "showInfobox":     bool(r["ShowInfobox"]),
                "infoboxPosition": str(r["InfoboxPosition"] or "left"),
                "globalNote":      global_note,
                "blocks":          blocks,
            }
            js = "receiveReport(" + _json2.dumps(report) + ");"
            if self._screen._web:
                self._screen._web.page().runJavaScript(js)
        except Exception as e:
            logger.error("loadReport: %s", e)

    @Slot(str)
    def deleteReport(self, report_id_str: str) -> None:
        """Delete a report (CASCADE deletes blocks + notes)."""
        try:
            from db.connection import execute
            execute("DELETE FROM tblSmartChartReport WHERE ID=?", [int(report_id_str)])
            js = "receiveDeleteResult(" + report_id_str + ");"
            if self._screen._web:
                self._screen._web.page().runJavaScript(js)
        except Exception as e:
            logger.error("deleteReport: %s", e)


    @Slot(str, str)
    def addImage(self, insert_after_str: str, width: str) -> None:
        """Open file dialog and send image as base64 to JS."""
        try:
            import base64, os
            from PySide6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getOpenFileName(
                self._screen, "Select image", "",
                "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
            )
            if not path:
                return
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            ext = os.path.splitext(path)[1].lower().lstrip(".")
            mime = {"jpg":"jpeg","jpeg":"jpeg","png":"png","bmp":"bmp","gif":"gif","webp":"webp"}.get(ext,"png")
            data_url = f"data:image/{mime};base64,{b64}"
            title = os.path.splitext(os.path.basename(path))[0]
            import json as _json
            js = f"receiveImage({insert_after_str}, {_json.dumps(data_url)}, {_json.dumps(title)}, {_json.dumps(width)});"
            if self._screen._web:
                self._screen._web.page().runJavaScript(js)
        except Exception as e:
            logger.error("addImage: %s", e)


    @Slot(str)
    def exportPdf(self, payload_json: str) -> None:
        """Generate a Heberlein-branded SmartChart PDF report using reportlab.

        Replaces the old QWebEngineView + printToPdf + fitz pipeline with a
        pure-Python reportlab implementation — no browser, no fitz dependency,
        native page numbers, crisp vector layout.
        """
        from db.usage_log import log_usage_event
        log_usage_event("feature", "pdf_export")
        try:
            import json as _json
            import base64, datetime, re, io, os
            from PySide6.QtWidgets import QFileDialog

            payload   = _json.loads(payload_json)
            charts    = payload.get("charts", [])
            infobox   = payload.get("infobox", {})
            now       = datetime.datetime.now()
            date_str  = now.strftime("%d.%m.%Y")
            gen_str   = now.strftime("%d.%m.%Y %H:%M")
            T         = _load_pdf_template(payload.get("pdfTemplateId"))

            # ── Save dialog ───────────────────────────────────────────────
            import pathlib as _pl
            _docs = str(_pl.Path.home() / "Documents")
            safe  = re.sub(r'[^\w\s-]', '', payload.get("reportTitle", "SmartChart")).strip()
            safe  = re.sub(r'\s+', '_', safe)
            dflt  = f"SmartChart_{safe}_{now.strftime('%Y%m%d')}.pdf"
            out_path, _ = QFileDialog.getSaveFileName(
                self._screen, "Save PDF report",
                str(_pl.Path(_docs) / dflt), "PDF Files (*.pdf)"
            )
            if not out_path:
                js = "receivePdfResult(false, 'cancelled');"
                if self._screen._web: self._screen._web.page().runJavaScript(js)
                return

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

            doc = _RL_Doc(
                out_path, pagesize=A4,
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
                            iw = chart_w * 0.5 if ch.get("imageWidth") == "half"                                  else chart_w * 0.8
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

            js = "receivePdfResult(true, " + _json.dumps(out_path) + ");"
            if self._screen._web: self._screen._web.page().runJavaScript(js)

        except Exception as e:
            logger.error("exportPdf: %s", e)
            import json as _json2
            js = "receivePdfResult(false, " + _json2.dumps(str(e)) + ");"
            if self._screen._web: self._screen._web.page().runJavaScript(js)


    @Slot(str, str, str, str, str)
    def loadFreeField(self, table, field, condition, chart_idx, y_key):
        try:
            series_pk = self._screen._series_pk
            if series_pk is None:
                return

            from db.connection import fetch_all, table_exists
            if not table_exists(table):
                return

            base = fetch_all(
                "SELECT ID AS trial_id FROM tblTrial WHERE TrialSeriesID = ?",
                [series_pk]
            )
            trial_ids = [int(r["trial_id"]) for r in base]
            if not trial_ids:
                return

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

            import json as _json
            data_js = _json.dumps(values)
            js = f"receiveFreeFieldData({chart_idx}, {_json.dumps(y_key)}, {data_js});"
            if self._screen._web:
                self._screen._web.page().runJavaScript(js)

        except Exception as e:
            logger.error("loadFreeField %s.%s: %s", table, field, e)


    @Slot(str)
    def jsError(self, message: str) -> None:
        logger.error("JS ERROR: %s", message)
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self._screen, "JS error", message)

    @Slot()
    def getLayoutTemplates(self) -> None:
        import json as _json
        try:
            from db.connection import fetch_all, table_exists
            if not table_exists("tblSmartChartTemplate"):
                js = "receiveLayoutTemplates([]);"
                if self._screen._web: self._screen._web.page().runJavaScript(js)
                return
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
            js = "receiveLayoutTemplates(" + _json.dumps(result) + ");"
            if self._screen._web: self._screen._web.page().runJavaScript(js)
        except Exception as e:
            logger.error("getLayoutTemplates: %s", e)
            if self._screen._web: self._screen._web.page().runJavaScript("receiveLayoutTemplates([]);")

    @Slot(str)
    def saveLayoutTemplate(self, payload_json: str) -> None:
        import json as _json
        try:
            from db.connection import get_connection, table_exists
            if not table_exists("tblSmartChartTemplate"):
                if self._screen._web: self._screen._web.page().runJavaScript('receiveLayoutTemplateSaved(false,"Table not found");')
                return
            p = _json.loads(payload_json)
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
            if self._screen._web: self._screen._web.page().runJavaScript('receiveLayoutTemplateSaved(true,"");')
        except Exception as e:
            logger.error("saveLayoutTemplate: %s", e)
            js = 'receiveLayoutTemplateSaved(false,' + _json.dumps(str(e)) + ');'
            if self._screen._web: self._screen._web.page().runJavaScript(js)

    @Slot(str)
    def deleteLayoutTemplate(self, template_id_str: str) -> None:
        import json as _json
        try:
            from db.connection import execute, fetch_all
            tid = int(template_id_str)
            # IsDefault-Templates nicht löschbar
            rows = fetch_all("SELECT IsDefault FROM tblSmartChartTemplate WHERE ID = ?", [tid])
            if rows and rows[0].get("IsDefault"):
                if self._screen._web: self._screen._web.page().runJavaScript(
                    'receiveLayoutTemplateDeleted(false,' + str(tid) + ');')
                return
            execute("DELETE FROM tblSmartChartTemplate WHERE ID = ?", [tid])
            logger.info("deleteLayoutTemplate: ID=%d gelöscht", tid)
            if self._screen._web: self._screen._web.page().runJavaScript(
                'receiveLayoutTemplateDeleted(true,' + str(tid) + ');')
        except Exception as e:
            logger.error("deleteLayoutTemplate: %s", e)
            if self._screen._web: self._screen._web.page().runJavaScript(
                'receiveLayoutTemplateDeleted(false,0);')

    @Slot(str)
    def overwriteLayoutTemplate(self, payload_json: str) -> None:
        import json as _json
        try:
            from db.connection import get_connection, fetch_all
            p = _json.loads(payload_json)
            tid = int(p["id"])
            rows = fetch_all("SELECT IsDefault FROM tblSmartChartTemplate WHERE ID = ?", [tid])
            if rows and rows[0].get("IsDefault") and not app_meta.is_superuser_level():
                if self._screen._web: self._screen._web.page().runJavaScript('receiveLayoutTemplateSaved(false,"Only superusers can edit the default template");')
                return
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
            if self._screen._web: self._screen._web.page().runJavaScript('receiveLayoutTemplateSaved(true,"");')
        except Exception as e:
            logger.error("overwriteLayoutTemplate: %s", e)
            js = 'receiveLayoutTemplateSaved(false,' + _json.dumps(str(e)) + ');'
            if self._screen._web: self._screen._web.page().runJavaScript(js)

    @Slot()
    def getPdfTemplates(self) -> None:
        import json as _json
        try:
            from db.connection import fetch_all, table_exists
            if not table_exists("tblSmartChartPdfTemplate"):
                logger.warning("getPdfTemplates: table not found - sending default")
                js = 'receivePdfTemplates([{"id":null,"name":"Heberlein Standard (Default)","description":"","isDefault":true}]);'
                if self._screen._web: self._screen._web.page().runJavaScript(js)
                return
            rows = fetch_all(
                "SELECT ID, Name, Description, IsDefault "
                "FROM tblSmartChartPdfTemplate "
                "WHERE IsActive = 1 ORDER BY IsDefault DESC, ID ASC",
                []
            )
            if not rows:
                logger.warning("getPdfTemplates: no active templates found")
                js = 'receivePdfTemplates([{"id":null,"name":"Heberlein Standard (Default)","description":"","isDefault":true}]);'
                if self._screen._web: self._screen._web.page().runJavaScript(js)
                return
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
            js = "receivePdfTemplates(" + _json.dumps(templates) + ");"
            if self._screen._web: self._screen._web.page().runJavaScript(js)
        except Exception as e:
            logger.error("getPdfTemplates: %s", e)
            # Fehler ans JS melden damit Modal nicht hängt
            fallback = [{"id": None, "name": "Heberlein Standard (Default)", "description": str(e), "isDefault": True}]
            try:
                js = "receivePdfTemplates(" + _json.dumps(fallback) + ");"
                if self._screen._web: self._screen._web.page().runJavaScript(js)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Screen
# ---------------------------------------------------------------------------

class ReportScreen(QWidget):

    def __init__(self, on_back=None, mode="series", parent=None, sidebar_callbacks: Optional[dict] = None):
        super().__init__(parent)
        self.on_back = on_back
        self.mode = mode  # immer "series" (aus Show Experiment); der Visual-SQL-Modus ist entfernt
        self._series_pk: Optional[int] = None
        self._experiment_request_id: Optional[Any] = None
        self._expreq_popup = None
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring). Der frühere
        # Header-Back-Button lebt als kontextueller Back-Chip weiter (gleiches
        # Muster wie ShowExperimentScreen) - zurück zu Show Experiment.
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        tools = QFrame()
        tl = QHBoxLayout(tools)
        tl.setContentsMargins(24, 12, 24, 0)
        tl.setSpacing(8)

        self.btn_back_chip = QPushButton("← Show Experiment")
        self.btn_back_chip.setCursor(Qt.PointingHandCursor)
        self.btn_back_chip.setStyleSheet(
            "QPushButton{background:transparent;color:#39a650;border:1px solid #39a650;"
            "border-radius:4px;padding:5px 10px;font-weight:600;}"
            "QPushButton:hover{background:#e8f5e9;}"
        )
        self.btn_back_chip.clicked.connect(self._go_back)
        self.btn_back_chip.setVisible(callable(self.on_back))
        tl.addWidget(self.btn_back_chip)
        tl.addStretch(1)

        # Experiment Request Button (analog zu screen_show_experiment)
        self.btn_experiment_request = QPushButton()
        self.btn_experiment_request.setObjectName("IconBtn")
        self.btn_experiment_request.setToolTip("Show linked Experiment Request")
        self.btn_experiment_request.setFlat(True)
        self.btn_experiment_request.setFixedSize(34, 34)
        self.btn_experiment_request.setStyleSheet(
            "QPushButton{border:none;background:transparent;padding:0px;}"
            "QPushButton:hover{background:rgba(0,0,0,0.06);border-radius:6px;}"
        )
        import os as _os2
        _icon_candidates = [
            resource_path("assets/images/experiment_request.png"),
            resource_path("assets/experiment_request.png"),
            resource_path("ui/icons/experiment_request.png"),
        ]
        _icon_set = False
        for _p in _icon_candidates:
            try:
                if _p and _os2.path.exists(_p):
                    self.btn_experiment_request.setIcon(QIcon(_p))
                    self.btn_experiment_request.setIconSize(QSize(22, 22))
                    _icon_set = True
                    break
            except Exception:
                continue
        if not _icon_set:
            self.btn_experiment_request.setText("ER")
        self.btn_experiment_request.setVisible(False)
        self.btn_experiment_request.clicked.connect(self._open_experiment_request_popup)
        tl.addWidget(self.btn_experiment_request)
        # Kontext-Hilfe EN/DE/ES (Nutzerwunsch 2026-10-13, ui/widgets/multilang_help.py);
        # im Smart-Chart-Modus direkt auf dem Smart-Chart-Tab
        from ui.widgets.multilang_help import make_help_button
        tl.addWidget(make_help_button("How does the Report work?", self._open_help))
        content_layout.addWidget(tools)

        self.lbl_series = QLabel()  # kept for internal use, not shown
        self.lbl_status = QLabel()  # kept for internal use, not shown

        if _WEB_ENGINE_AVAILABLE:
            self._web = QWebEngineView()
            self._web.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._bridge = _ReportBridge(self)
            self._channel = QWebChannel()
            self._channel.registerObject("bridge", self._bridge)
            self._web.page().setWebChannel(self._channel)
            content_layout.addWidget(self._web)
        else:
            fallback = QLabel("⚠️  PySide6-WebEngine is not installed.\npip install PySide6-WebEngine")
            fallback.setAlignment(Qt.AlignCenter)
            fallback.setStyleSheet("font-size:14px; color:#c0392b; padding:40px;")
            content_layout.addWidget(fallback)
            self._web = None

        root.addWidget(FooterBar())

    def _refresh_sidebar(self):
        """Baut die Sidebar-Navigation neu auf, falls sich der Access-Level
        seit dem letzten Aufbau geändert hat, sonst nur die Badges (siehe
        ui/widgets/sidebar_nav.py::refresh_lazy_sidebar())."""
        import app_meta
        try:
            level = int((app_meta.current_user or {}).get("access_level") or 0)
        except Exception:
            level = 0
        sidebar_nav.refresh_lazy_sidebar(self, level)

    def showEvent(self, event):
        try:
            self._refresh_sidebar()
        except Exception:
            pass
        super().showEvent(event)
        # Bugreport 2026-09-02: with a SECOND ReportScreen (own QWebEngineView)
        # opened in its own new tab while a FIRST one already exists elsewhere
        # (see main.py::_open_report_in_new_tab(), 2026-09-01), the new tab's
        # QWebEngineView sometimes never actually paints - the tab title/stack
        # switch to it correctly, but the previously visible screen (e.g. Show
        # Experiment) stays on screen underneath, because this view's native
        # render surface got set up at 0x0 geometry (new tab, layout not yet
        # settled) before it was ever shown. A no-op resize-to-current-size
        # AFTER the event loop has settled the real geometry nudges Chromium's
        # compositor into actually painting - same class of QtWebEngine/
        # QStackedWidget gotcha as the well-known "webview stays blank until
        # resized" issue.
        if self._web is not None:
            QTimer.singleShot(0, lambda w=self._web: w.resize(w.size()))

    def load_series(self, series_pk: int, initial_report_id: Optional[int] = None) -> None:
        self._series_pk = series_pk
        self.lbl_series.setText(f"TrialSeries: {series_pk}")
        self.lbl_status.setText("Loading data...")
        self._refresh_experiment_request_link()
        self._sync_experiment_request_icon()

        data     = _fetch_series_data(series_pk)
        tbl_cols = _fetch_table_columns()
        infobox  = _fetch_infobox_data(series_pk)

        # Load axes from DB, fallback to hardcoded
        db_y_axes, db_x_axes, db_g_axes = _load_axes_from_db()
        active_y_axes = db_y_axes if db_y_axes else Y_AXES
        active_x_axes = db_x_axes if db_x_axes else X_AXES

        n_refs = sum(1 for r in data if r.get("is_reference"))
        self.lbl_status.setText(
            f"{len(data) - n_refs} trial(s) loaded"
            + (f" + {n_refs} reference sample(s)" if n_refs else ""))

        if self._web is not None:
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
                .replace("{current_user_json}", json.dumps(str(getattr(__import__("app_meta"), "current_user", {}).get("username","") or "")))
                .replace("{is_superuser_json}", "true" if app_meta.is_superuser_level() else "false")
                .replace("{initial_report_id_json}", json.dumps(initial_report_id))
            )
            try:
                import tempfile as _tmp, os as _os
                _p = _os.path.join(_tmp.gettempdir(), "tripplet_debug.html")
                open(_p, "w", encoding="utf-8").write(html)
                logger.info("DEBUG HTML: %s", _p)
            except Exception as _e:
                logger.error("DEBUG: %s", _e)
            self._web.setHtml(html, web_base_url())


    def _refresh_experiment_request_link(self) -> None:
        """Laedt die verknuepfte ExperimentRequest-ID ueber series_pk -> ExperimentID."""
        self._experiment_request_id = None
        if not self._series_pk:
            return
        try:
            from db.connection import fetch_all
            # series_pk -> tblTrialSeries.ExperimentID -> tblExperimente.ExperimentRequest
            rows = fetch_all(
                """
                SELECT er.ID AS req_id
                FROM tblTrialSeries ts
                JOIN tblExperimente e ON e.ID = ts.ExperimentID
                JOIN tblExperimentRequests er ON er.ID = e.ExperimentRequestID
                WHERE ts.ID = ?
                LIMIT 1
                """,
                [self._series_pk],
            )
            if rows:
                self._experiment_request_id = rows[0].get("req_id")
        except Exception:
            self._experiment_request_id = None

    def _sync_experiment_request_icon(self) -> None:
        """Zeigt/versteckt den ER-Button je nach verlinktem Request."""
        try:
            rid = self._experiment_request_id
            visible = rid not in (None, "", 0, "0")
            if hasattr(self, "btn_experiment_request") and self.btn_experiment_request:
                self.btn_experiment_request.setVisible(bool(visible))
        except Exception:
            pass

    def _open_experiment_request_popup(self) -> None:
        """Oeffnet den ExperimentRequest als nicht-modalen Read-Only-Dialog."""
        rid = self._experiment_request_id
        if rid in (None, "", 0, "0"):
            return
        try:
            # Bereits offen -> nach vorne holen
            if self._expreq_popup is not None and self._expreq_popup.isVisible():
                self._expreq_popup.raise_()
                self._expreq_popup.activateWindow()
                return
            from ui.screen_show_experiment import _ExperimentRequestReadOnlyDialog
            dlg = _ExperimentRequestReadOnlyDialog(self, request_id=rid)
            dlg.setWindowModality(Qt.NonModal)
            dlg.setModal(False)
            dlg.setAttribute(Qt.WA_DeleteOnClose, True)
            dlg.finished.connect(lambda: setattr(self, "_expreq_popup", None))
            self._expreq_popup = dlg
            dlg.show()
        except Exception as e:
            QMessageBox.critical(self, "Experiment Request", str(e))

    def _open_help(self) -> None:
        from ui.widgets.multilang_help import show_help
        from ui.widgets.help_texts_report import TEXTS
        show_help(TEXTS, self)

    def _go_back(self) -> None:
        if callable(self.on_back):
            self.on_back()