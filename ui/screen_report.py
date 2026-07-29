from __future__ import annotations
# ui/screen_report.py
"""Report-Screen für TrippleT – Visualisierung einer TrialSeries."""

import json
import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QSizePolicy, QMessageBox,
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

from ui.pathutil import resource_path
from ui.report_html_template import _HTML_TEMPLATE
from ui.report_queries import (
    Y_AXES, X_AXES, KNOWN_TABLES,
    _get_known_tables, _load_axes_from_db,
    _fetch_y_values, _fetch_table_columns, _fetch_series_data,
    _fetch_infobox_data,
)
from ui.report_pdf_layout import (
    _PDF_TEMPLATE_DEFAULTS,
    _meta_cell, _section_hdr, _infobox_table, _note_block, _load_pdf_template,
)
from ui.widgets.header import HeaderBar
from ui.widgets.footer import FooterBar
import app_meta

logger = logging.getLogger(__name__)


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

    @Slot(str)
    def getFilterValues(self, field_key: str) -> None:
        try:
            import json as _json
            from db.connection import fetch_all
            QUERIES = {
                'jet':     "SELECT DISTINCT Jet AS val FROM tbljets WHERE Jet IS NOT NULL ORDER BY Jet",
                'yarn':    "SELECT DISTINCT Name AS val FROM tblyarn WHERE Name IS NOT NULL ORDER BY Name",
                'machine': "SELECT DISTINCT Maschine AS val FROM tblMaschine WHERE Maschine IS NOT NULL ORDER BY Maschine",
            }
            if field_key not in QUERIES:
                return
            rows   = fetch_all(QUERIES[field_key], [])
            values = [str(r["val"]) for r in rows if r.get("val")]
            js = "receiveFilterValues(" + _json.dumps(field_key) + ", " + _json.dumps(values) + ");"
            if self._screen._web:
                self._screen._web.page().runJavaScript(js)
        except Exception as e:
            logger.error("getFilterValues %s: %s", field_key, e)

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
                trials = fetch_all("SELECT ID FROM tblTrial WHERE TrialSeriesID = ?", [series_pk])
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
                'machine': (
                    "LEFT JOIN tblTrialSeries AS TSR2 ON TSR2.ID = T.TrialSeriesID "
                    "LEFT JOIN tblMaschine AS MC ON MC.ID = TSR2.MachineID"
                ),
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

            joins_sql = "LEFT JOIN tbljets AS J ON J.ID = T.JetID"
            if extra_joins:
                joins_sql += " " + " ".join(extra_joins)
            where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
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
            elif group_by == 'machine' and not any('tblMaschine AS MC' in j for j in extra_joins):
                extra_joins.append(
                    "LEFT JOIN tblTrialSeries AS TSR2 ON TSR2.ID = T.TrialSeriesID "
                    "LEFT JOIN tblMaschine AS MC ON MC.ID = TSR2.MachineID"
                )
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

            # Advanced Filters verarbeiten
            adv_filters = _json.loads(adv_filters_json) if adv_filters_json else []
            _adv_join_tables = set()
            for af in adv_filters:
                tbl = str(af.get('table',''))
                fld = str(af.get('field',''))
                op  = str(af.get('op','='))
                val = af.get('value')
                vals = af.get('values',[])
                if not tbl or not fld: continue
                # JOIN für Fremdtabellen (nicht tbltrial) hinzufügen
                if tbl.lower() not in ('tbltrial','') and tbl not in _adv_join_tables:
                    _adv_join_tables.add(tbl)
                    id_col = 'TrialID' if tbl.lower() != 'tbltrial' else 'ID'
                    extra_joins.append(f"LEFT JOIN {tbl} AS adv_{tbl} ON adv_{tbl}.{id_col} = T.ID")
                tbl_alias = f"adv_{tbl}" if tbl.lower() != 'tbltrial' else 'T'
                col_ref = f"{tbl_alias}.{fld}"
                if op == 'IS NULL':
                    where_parts.append(f"{col_ref} IS NULL")
                elif op == 'IN' and vals:
                    ph = ','.join(['?' for _ in vals])
                    where_parts.append(f"{col_ref} IN ({ph})")
                    params.extend(vals)
                elif op == 'LIKE' and val is not None:
                    where_parts.append(f"{col_ref} LIKE ?")
                    params.append(f"%{val}%")
                elif val is not None:
                    where_parts.append(f"{col_ref} {op} ?")
                    try: params.append(float(val))
                    except: params.append(val)

            joins_sql = "LEFT JOIN tbljets AS J ON J.ID = T.JetID"
            # machine_name JOIN immer dabei
            _mc_join = "LEFT JOIN tblTrialSeries AS TSR_MC ON TSR_MC.ID = T.TrialSeriesID LEFT JOIN tblMaschine AS MC ON MC.ID = TSR_MC.MachineID"
            if _mc_join not in (extra_joins or []):
                extra_joins.append(_mc_join)
            if extra_joins:
                joins_sql += " " + " ".join(extra_joins)

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
                    "air_cons":      _f(r.get("air_cons")),
                    "air_cons_real": (_f(r.get("air_cons")) * (_f(r.get("air_pressure")) + 1))
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

            labels = list(set(r.get("jet_name","?") for r in rows))
            raw_labels = list(set(r.get("group_label","NULL") for r in base_rows[:5]))
            print("SC_LABELS:", group_by, labels[:10], "RAW:", raw_labels, flush=True)
            print("SC_SQL:", sql[:400], flush=True)
            print("SC_KEYS:", list(base_rows[0].keys()) if base_rows else [], flush=True)
            js = "receiveQueryResult(" + _json.dumps(rows) + ", " + str(len(rows)) + ");"
            if self._screen._web:
                self._screen._web.page().runJavaScript(js)
        except Exception as e:
            logger.error("runVisualQuery: %s", e)


    @Slot(str)
    def saveReport(self, report_json: str) -> None:
        """Save or update a SmartChart report with block-based structure."""
        try:
            import json as _json
            from db.connection import fetch_all, execute
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
                execute(
                    "INSERT INTO tblSmartChartReport "
                    "(Title, Author, SourceType, SeriesPK, QueryConfigJSON, "
                    "ShowInfobox, InfoboxPosition, UserID) VALUES (?,?,?,?,?,?,?,?)",
                    [title, author, source_type, series_pk, query_cfg,
                     show_info, info_pos, user_id]
                )
                rows = fetch_all("SELECT LAST_INSERT_ID() AS new_id", [])
                report_id = int(rows[0]["new_id"]) if rows and rows[0].get("new_id") else None
                if not report_id:
                    rows = fetch_all(
                        "SELECT ID FROM tblSmartChartReport WHERE Title=? AND Author=? "
                        "ORDER BY ID DESC LIMIT 1", [title, author]
                    )
                    report_id = int(rows[0]["ID"]) if rows else None

            if not report_id:
                raise Exception("Could not determine report ID after save")

            # Save blocks
            for b in blocks:
                execute(
                    "INSERT INTO tblSmartChartBlock "
                    "(ReportID, BlockType, SortOrder, ChartIndex, XField, YKey, ZField, "
                    "ChartMode, ImageData, ImageTitle, ImageWidth, NoteTitle, NoteText, NoteVisible) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
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
                    ]
                )

            # Save global note
            if global_note:
                execute(
                    "INSERT INTO tblSmartChartNote "
                    "(ReportID, NoteType, NoteTitle, NoteText, IsVisible) VALUES (?,?,?,?,?)",
                    [report_id, "global", "Summary", global_note, 1]
                )

            js = f"receiveSaveResult({report_id}, true, 'Report saved successfully');"
            if self._screen._web:
                self._screen._web.page().runJavaScript(js)

        except Exception as e:
            logger.error("saveReport: %s", e)
            import json as _json2
            js = "receiveSaveResult(null, false, " + _json2.dumps(str(e)) + ");"
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
                self._screen, "PDF Report speichern",
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
                has_note = bool(ch.get("noteVisible") and ch.get("noteText","").strip())
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
        QMessageBox.critical(self._screen, "JS Fehler", message)

    @Slot()
    def getFreeQueryMeta(self) -> None:
        import json as _json
        try:
            from db.connection import fetch_all, table_exists
            if not table_exists('tblSmartChartFreeTable'):
                logger.warning('getFreeQueryMeta: tblSmartChartFreeTable nicht gefunden')
                if self._screen._web: self._screen._web.page().runJavaScript('receiveFreeQueryMeta([],{},[]);')
                return
            tbl_rows = fetch_all(
                "SELECT TableName, DisplayLabel FROM tblSmartChartFreeTable "
                "WHERE IsActive=1 ORDER BY SortOrder, DisplayLabel", []
            )
            tables = [{"tableName": r["TableName"], "displayLabel": r["DisplayLabel"]} for r in tbl_rows]
            join_rows = fetch_all(
                "SELECT FromTable, ToTable, JoinSQL FROM tblSmartChartJoinPath "
                "WHERE IsActive=1 ORDER BY SortOrder", []
            )
            join_paths = {}
            for r in join_rows:
                ft = r["FromTable"]
                if ft not in join_paths: join_paths[ft] = []
                join_paths[ft].append({"toTable": r["ToTable"], "joinSQL": r["JoinSQL"]})
            columns = {}
            skip_lower = {"id","globalid","userid","timestamp","createdat","createdby"}
            for t in tbl_rows:
                tname = t["TableName"]
                try:
                    col_rows = fetch_all(
                        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = ? "
                        "ORDER BY ORDINAL_POSITION", [tname]
                    )
                    columns[tname] = [
                        r["COLUMN_NAME"] for r in col_rows
                        if r["COLUMN_NAME"].lower() not in skip_lower
                        and not r["COLUMN_NAME"].lower().endswith("id")
                    ]
                except Exception as col_e:
                    logger.warning("getFreeQueryMeta columns %s: %s", tname, col_e)
                    columns[tname] = []
            logger.info("getFreeQueryMeta: %d tables, %d join_paths", len(tables), len(join_rows))
            js = (f'receiveFreeQueryMeta('
                  f'{_json.dumps(tables)},'
                  f'{_json.dumps(join_paths)},'
                  f'{_json.dumps(columns)});')
            if self._screen._web: self._screen._web.page().runJavaScript(js)
        except Exception as e:
            logger.error('getFreeQueryMeta: %s', e, exc_info=True)
            if self._screen._web: self._screen._web.page().runJavaScript('receiveFreeQueryMeta([],{},[]);')

    @Slot(str)
    def runFreeQuery(self, config_json: str) -> None:
        import json as _json
        try:
            from db.connection import fetch_all
            cfg = _json.loads(config_json)
            base   = cfg.get('baseTable','')
            joins  = cfg.get('joinTables',[])
            x_fld  = cfg.get('xField','').split('::')
            y_fld  = cfg.get('yField','').split('::')
            c_fld  = cfg.get('colorField','').split('::') if cfg.get('colorField') else None
            l_fld  = cfg.get('labelField','').split('::') if cfg.get('labelField') else None
            filters= cfg.get('filters',[])
            limit  = int(cfg.get('limit',500))

            if not base or len(x_fld)<2 or len(y_fld)<2:
                if self._screen._web: self._screen._web.page().runJavaScript('receiveFreeQueryResult([],0,{});')
                return

            # JoinPaths direkt aus DB
            jp_rows = fetch_all("SELECT FromTable, ToTable, JoinSQL FROM tblSmartChartJoinPath WHERE IsActive=1", [])
            join_paths = {}
            for r in jp_rows:
                ft = r["FromTable"]
                if ft not in join_paths: join_paths[ft] = []
                join_paths[ft].append({"toTable": r["ToTable"], "joinSQL": r["JoinSQL"]})
            logger.info("runFreeQuery: base=%s joins=%s", base, joins)

            # SELECT
            sel_parts = [
                f"`{x_fld[0]}`.`{x_fld[1]}` AS `__fqb_x`",
                f"`{y_fld[0]}`.`{y_fld[1]}` AS `__fqb_y`",
            ]
            if c_fld: sel_parts.append(f"`{c_fld[0]}`.`{c_fld[1]}` AS `__fqb_color`")
            if l_fld: sel_parts.append(f"`{l_fld[0]}`.`{l_fld[1]}` AS `__fqb_label`")

            # JOINs
            join_sql_parts = []
            for jt in joins:
                paths = join_paths.get(base, [])
                path = next((p for p in paths if p['toTable']==jt), None)
                if not path:
                    for at in joins:
                        if at == jt: continue
                        p2 = next((p for p in join_paths.get(at,[]) if p['toTable']==jt), None)
                        if p2: path = p2; break
                if path: join_sql_parts.append(path['joinSQL'])

            # WHERE — auto-JOIN für Tabellen die im Filter aber nicht in joins sind
            where_parts, params = [], []
            for f in filters:
                tbl = f.get('table',''); fld = f.get('field','')
                op  = f.get('op','=');   val = f.get('value')
                if not tbl or not fld: continue
                # Auto-JOIN falls Tabelle nicht explizit gejoint
                if tbl != base and tbl not in joins:
                    paths = join_paths.get(base, [])
                    auto_path = next((p for p in paths if p['toTable']==tbl), None)
                    if auto_path and auto_path['joinSQL'] not in join_sql_parts:
                        join_sql_parts.append(auto_path['joinSQL'])
                col_ref = f"`{tbl}`.`{fld}`"
                if op == 'IS NULL':
                    where_parts.append(f"{col_ref} IS NULL")
                elif op in ('LIKE', 'NOT LIKE') and val:
                    like_val = val if '%' in val else f'%{val}%'
                    where_parts.append(f"{col_ref} {op} ?")
                    params.append(like_val)
                elif op == 'IS NOT NULL':
                    where_parts.append(f"{col_ref} IS NOT NULL")
                elif val is not None:
                    where_parts.append(f"{col_ref} {op} ?")
                    try: params.append(float(val))
                    except: params.append(str(val))

            sql = (f"SELECT {', '.join(sel_parts)} FROM `{base}` "
                   + (' '.join(join_sql_parts) + ' ' if join_sql_parts else '')
                   + ('WHERE ' + ' AND '.join(where_parts) + ' ' if where_parts else '')
                   + f"LIMIT {limit}")

            logger.info("runFreeQuery SQL: %s | params: %s", sql[:300], params)
            rows = fetch_all(sql, params)
            import decimal as _dec
            def _safe(v):
                if v is None: return None
                if isinstance(v, _dec.Decimal): return float(v)
                return v
            result = []
            for r in rows:
                row = {'__fqb_x': _safe(r.get('__fqb_x')), '__fqb_y': _safe(r.get('__fqb_y'))}
                if c_fld: row['__fqb_color'] = str(r.get('__fqb_color') or '')
                if l_fld: row['__fqb_label'] = str(r.get('__fqb_label') or '')
                result.append(row)
            logger.info("runFreeQuery: %d rows", len(result))
            js = (f'receiveFreeQueryResult('
                  f'{_json.dumps(result)},'
                  f'{len(result)},'
                  f'{_json.dumps(cfg)});')
            if self._screen._web: self._screen._web.page().runJavaScript(js)
        except Exception as e:
            logger.error('runFreeQuery FEHLER: %s', e, exc_info=True)
            if self._screen._web: self._screen._web.page().runJavaScript('receiveFreeQueryResult([],0,{});')

    @Slot()
    def getAdvancedFilterFields(self) -> None:
        import json as _json
        try:
            from db.connection import fetch_all, table_exists
            if not table_exists('tblSmartChartAllowedField'):
                if self._screen._web: self._screen._web.page().runJavaScript('receiveAdvancedFilterFields([]);')
                return
            rows = fetch_all(
                "SELECT TableName, FieldName, DisplayLabel, FieldType, LookupQuery "
                "FROM tblSmartChartAllowedField WHERE IsActive=1 ORDER BY SortOrder, DisplayLabel",
                []
            )
            result = [
                {
                    'table':        str(r['TableName']),
                    'field':        str(r['FieldName']),
                    'label':        str(r['DisplayLabel']),
                    'type':         str(r['FieldType'] or 'numeric'),
                    'lookupQuery':  str(r['LookupQuery'] or '') if r.get('LookupQuery') else '',
                    'lookupVals':   [],
                }
                for r in rows
            ]
            js = 'receiveAdvancedFilterFields(' + _json.dumps(result) + ');'
            if self._screen._web: self._screen._web.page().runJavaScript(js)
        except Exception as e:
            logger.error('getAdvancedFilterFields: %s', e)
            if self._screen._web: self._screen._web.page().runJavaScript('receiveAdvancedFilterFields([]);')

    @Slot(str, str)
    def getAdvancedFieldValues(self, table_name: str, field_name: str) -> None:
        import json as _json
        try:
            from db.connection import fetch_all, table_exists
            if not table_exists(table_name):
                return
            rows = fetch_all(
                f"SELECT DISTINCT `{field_name}` AS val FROM `{table_name}` "
                f"WHERE `{field_name}` IS NOT NULL ORDER BY `{field_name}` LIMIT 200",
                []
            )
            values = [str(r['val']) for r in rows if r.get('val') is not None]
            key = f"{table_name}::{field_name}"
            js = f"receiveAdvancedFieldValues({_json.dumps(key)}, {_json.dumps(values)});"
            if self._screen._web: self._screen._web.page().runJavaScript(js)
        except Exception as e:
            logger.error('getAdvancedFieldValues %s.%s: %s', table_name, field_name, e)

    @Slot()
    def getQueryTemplates(self) -> None:
        import json as _json
        try:
            from db.connection import fetch_all, table_exists
            import app_meta
            username = str(getattr(app_meta, 'current_user', {}).get('username','') or '')
            if not table_exists('tblSmartChartQueryTemplate'):
                if self._screen._web: self._screen._web.page().runJavaScript('receiveQueryTemplates([]);')
                return
            rows = fetch_all(
                "SELECT ID, Name, Description, VisibilityLevel, GroupBy, "
                "FiltersJSON, SeriesPKsJSON, CreatedBy, CertifiedBy "
                "FROM tblSmartChartQueryTemplate "
                "WHERE IsActive=1 AND (VisibilityLevel>=2 OR CreatedBy=?) "
                "ORDER BY VisibilityLevel ASC, Name ASC",
                [username]
            )
            result = []
            for r in rows:
                try: filters = _json.loads(r.get('FiltersJSON') or '[]')
                except: filters = []
                try: series_pks = _json.loads(r.get('SeriesPKsJSON') or '[]')
                except: series_pks = []
                result.append({
                    'id':              int(r['ID']),
                    'name':            str(r.get('Name') or ''),
                    'description':     str(r.get('Description') or ''),
                    'visibilityLevel': int(r.get('VisibilityLevel') or 1),
                    'groupBy':         str(r.get('GroupBy') or 'jet'),
                    'filters':         filters,
                    'seriesPKs':       series_pks,
                    'createdBy':       str(r.get('CreatedBy') or ''),
                    'certifiedBy':     str(r.get('CertifiedBy') or ''),
                })
            js = 'receiveQueryTemplates(' + _json.dumps(result) + ');'
            if self._screen._web: self._screen._web.page().runJavaScript(js)
        except Exception as e:
            logger.error('getQueryTemplates: %s', e)
            if self._screen._web: self._screen._web.page().runJavaScript('receiveQueryTemplates([]);')

    @Slot()
    def checkSuperuser(self) -> None:
        try:
            import app_meta
            from db.connection import is_superuser
            username = str(getattr(app_meta, 'current_user', {}).get('username','') or '')
            val = is_superuser(username) if username else False
            js = f'receiveIsSuperuser({str(val).lower()});'
            if self._screen._web: self._screen._web.page().runJavaScript(js)
        except Exception as e:
            logger.error('checkSuperuser: %s', e)
            if self._screen._web: self._screen._web.page().runJavaScript('receiveIsSuperuser(false);')

    @Slot(str)
    def saveQueryTemplate(self, payload_json: str) -> None:
        import json as _json
        try:
            from db.connection import get_connection, table_exists
            if not table_exists('tblSmartChartQueryTemplate'):
                if self._screen._web: self._screen._web.page().runJavaScript('receiveQueryTemplateSaved(false,"Table not found");')
                return
            p = _json.loads(payload_json)
            with get_connection() as cn:
                cur = cn.cursor()
                cur.execute(
                    "INSERT INTO tblSmartChartQueryTemplate "
                    "(Name, Description, VisibilityLevel, GroupBy, FiltersJSON, SeriesPKsJSON, CreatedBy) "
                    "VALUES (?,?,?,?,?,?,?)",
                    [p['name'], p.get('description',''), int(p.get('visibilityLevel',1)),
                     p.get('groupBy','jet'),
                     _json.dumps(p.get('filters',[])),
                     _json.dumps(p.get('seriesPKs',[])),
                     p.get('createdBy','')]
                )
            logger.info("saveQueryTemplate: '%s' gespeichert", p['name'])
            if self._screen._web: self._screen._web.page().runJavaScript('receiveQueryTemplateSaved(true,"");')
        except Exception as e:
            logger.error('saveQueryTemplate: %s', e)
            js = 'receiveQueryTemplateSaved(false,' + _json.dumps(str(e)) + ');'
            if self._screen._web: self._screen._web.page().runJavaScript(js)

    @Slot(str)
    def certifyQueryTemplate(self, tpl_id_str: str) -> None:
        import json as _json
        try:
            from db.connection import execute
            import app_meta
            from datetime import datetime
            username = str(getattr(app_meta, 'current_user', {}).get('username','') or '')
            tid = int(tpl_id_str)
            execute(
                "UPDATE tblSmartChartQueryTemplate "
                "SET VisibilityLevel=3, CertifiedBy=?, CertifiedAt=? WHERE ID=?",
                [username, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), tid]
            )
            logger.info("certifyQueryTemplate: ID=%d zertifiziert von %s", tid, username)
            if self._screen._web: self._screen._web.page().runJavaScript('receiveQueryTemplateCertified(true);')
        except Exception as e:
            logger.error('certifyQueryTemplate: %s', e)
            if self._screen._web: self._screen._web.page().runJavaScript('receiveQueryTemplateCertified(false);')

    @Slot(str)
    def deleteQueryTemplate(self, tpl_id_str: str) -> None:
        import json as _json
        try:
            from db.connection import execute
            tid = int(tpl_id_str)
            execute("UPDATE tblSmartChartQueryTemplate SET IsActive=0 WHERE ID=?", [tid])
            logger.info("deleteQueryTemplate: ID=%d deaktiviert", tid)
            if self._screen._web: self._screen._web.page().runJavaScript('receiveQueryTemplateDeleted(true);')
        except Exception as e:
            logger.error('deleteQueryTemplate: %s', e)
            if self._screen._web: self._screen._web.page().runJavaScript('receiveQueryTemplateDeleted(false);')

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
            if rows and rows[0].get("IsDefault"):
                if self._screen._web: self._screen._web.page().runJavaScript('receiveLayoutTemplateSaved(false,"Cannot overwrite default template");')
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
                logger.warning("getPdfTemplates: Tabelle nicht gefunden — sende Default")
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
                logger.warning("getPdfTemplates: keine aktiven Templates gefunden")
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

    def __init__(self, on_back=None, mode="series", parent=None):
        super().__init__(parent)
        self.on_back = on_back
        self.mode = mode  # "series" = from ShowExperiment | "visual" = from Home (Visual SQL)
        self._series_pk: Optional[int] = None
        self._experiment_request_id: Optional[Any] = None
        self._expreq_popup = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._header = HeaderBar(title="Smart Chart", show_home=False, show_back=True)
        self._header.connect_back(self._go_back)
        root.addWidget(self._header)

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
        try:
            hlay = self._header.layout()
            hlay.insertWidget(hlay.count() - 1, self.btn_experiment_request, 0)
        except Exception:
            pass

        self.lbl_series = QLabel()  # kept for internal use, not shown
        self.lbl_status = QLabel()  # kept for internal use, not shown

        if _WEB_ENGINE_AVAILABLE:
            self._web = QWebEngineView()
            self._web.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._bridge = _ReportBridge(self)
            self._channel = QWebChannel()
            self._channel.registerObject("bridge", self._bridge)
            self._web.page().setWebChannel(self._channel)
            root.addWidget(self._web)
        else:
            fallback = QLabel("⚠️  PySide6-WebEngine nicht installiert.\npip install PySide6-WebEngine")
            fallback.setAlignment(Qt.AlignCenter)
            fallback.setStyleSheet("font-size:14px; color:#c0392b; padding:40px;")
            root.addWidget(fallback)
            self._web = None

        root.addWidget(FooterBar())

    def load_series(self, series_pk: int) -> None:
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

        self.lbl_status.setText(f"{len(data)} trial(s) loaded")

        if self._web is not None:
            y_axes_js = [{"key": y["key"], "title": y["title"], "unit": y.get("unit", "")} for y in active_y_axes]
            tbl_opts  = "\n".join(
                f'<option value="{t}">{t}</option>' for t in _get_known_tables()
            )
            x_axes_js = [{"id": x.get("id"), "key": x["key"], "title": x["title"], "unit": x.get("unit", ""), "field": x["field"], "sub_axis_id": x.get("sub_axis_id"), "is_group_by": x.get("is_group_by", False)} for x in active_x_axes]
            g_axes_js = [{"key": g["key"], "title": g["title"], "join_sql": g.get("join_sql")} for g in (db_g_axes or [])]
            html = (
                _HTML_TEMPLATE
                .replace("{data_json}",     json.dumps(data))
                .replace("{y_axes_json}",   json.dumps(y_axes_js))
                .replace("{x_axes_json}",   json.dumps(x_axes_js))
                .replace("{g_axes_json}",   json.dumps(g_axes_js))
                .replace("{tbl_cols_json}", json.dumps(tbl_cols))
                .replace("{table_options}", tbl_opts)
                .replace("{infobox_json}",  json.dumps(infobox))
                .replace("{primary_series_pk}", str(series_pk))
                .replace("{is_visual_mode}", "false")
                .replace("{current_user_json}", json.dumps(str(getattr(__import__("app_meta"), "current_user", {}).get("username","") or "")))
            )
            try:
                import tempfile as _tmp, os as _os
                _p = _os.path.join(_tmp.gettempdir(), "tripplet_debug.html")
                open(_p, "w", encoding="utf-8").write(html)
                logger.info("DEBUG HTML: %s", _p)
            except Exception as _e:
                logger.error("DEBUG: %s", _e)
            self._web.setHtml(html, QUrl("about:blank"))


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

    def load_visual(self) -> None:
        """Load Smart Chart in Visual SQL mode — no series_pk needed."""
        self._series_pk = None
        db_y_axes, db_x_axes, db_g_axes = _load_axes_from_db()
        active_y = db_y_axes if db_y_axes else Y_AXES
        active_x = db_x_axes if db_x_axes else X_AXES
        tbl_cols = _fetch_table_columns()

        if self._web is not None:
            y_axes_js = [{"key": y["key"], "title": y["title"], "unit": y.get("unit", "")} for y in active_y]
            x_axes_js = [{"id": x.get("id"), "key": x["key"], "title": x["title"], "unit": x.get("unit", ""), "field": x["field"], "sub_axis_id": x.get("sub_axis_id"), "is_group_by": x.get("is_group_by", False)} for x in active_x]
            g_axes_js = [{"key": g["key"], "title": g["title"], "join_sql": g.get("join_sql")} for g in (db_g_axes or [])]
            tbl_opts  = "\n".join(f'<option value="{t}">{t}</option>' for t in _get_known_tables())
            infobox   = {
                "series_name": "", "material": "", "machine": "",
                "air_pressures": [], "overfeeds": [], "speeds": [],
                "n_trials": 0, "jets": [],
            }
            html = (
                _HTML_TEMPLATE
                .replace("{data_json}",       json.dumps([]))
                .replace("{y_axes_json}",     json.dumps(y_axes_js))
                .replace("{x_axes_json}",     json.dumps(x_axes_js))
                .replace("{tbl_cols_json}",   json.dumps(tbl_cols))
                .replace("{table_options}",   tbl_opts)
                .replace("{g_axes_json}",     json.dumps(g_axes_js))
                .replace("{infobox_json}",    json.dumps(infobox))
                .replace("{primary_series_pk}", "0")
                .replace("{is_visual_mode}", "true")
                .replace("{current_user_json}", json.dumps(str(getattr(__import__("app_meta"), "current_user", {}).get("username","") or "")))
            )
            # DEBUG: HTML in Datei schreiben
            try:
                import tempfile, os
                _dbg_path = os.path.join(tempfile.gettempdir(), "tripplet_debug.html")
                with open(_dbg_path, "w", encoding="utf-8") as _dbg:
                    _dbg.write(html)
                logger.info("DEBUG HTML: %s", _dbg_path)
            except Exception as _de:
                logger.error("DEBUG write failed: %s", _de)
            try:
                import tempfile as _tmp, os as _os
                _p = _os.path.join(_tmp.gettempdir(), "tripplet_debug.html")
                open(_p, "w", encoding="utf-8").write(html)
                logger.info("DEBUG HTML: %s", _p)
            except Exception as _e:
                logger.error("DEBUG: %s", _e)
            self._web.setHtml(html, QUrl("about:blank"))

    def _go_back(self) -> None:
        if callable(self.on_back):
            self.on_back()