"""report_queries.py - Datenbankabfragen fuer den ReportScreen "Smart Chart" Builder.

Ausgelagert aus ui/screen_report.py (reiner Code-Move, keine
Verhaltensaenderung). Enthaelt die X-/Y-Achsen-Definitionen sowie alle
DB-Abfrage-Funktionen, die von _ReportBridge/ReportScreen (weiterhin in
screen_report.py) zum Laden der Chart- und Infobox-Daten genutzt werden.

db.connection wird bewusst lazy in jeder Funktion importiert (nicht neu
implementiert), damit exakt derselbe DB-Wrapper wie vorher verwendet wird.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from db.trial_reference import (
    IS_REFERENCE_COL,
    REFERENCE_NAME_COL,
    exclude_references_sql,
    has_reference_columns,
    is_reference_value,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Y-Achsen-Definition
# ---------------------------------------------------------------------------
Y_AXES = [
    {"key": "titer",        "title": "Titer",                        "unit": "dtex",     "main_table": "tbllabortiter",       "alt_table": None,                  "field": "Titer",                "condition": None},
    {"key": "elongation",   "title": "Elongation",                   "unit": "%",        "main_table": "tbllaborstatimatds",  "alt_table": "tbllaborstatimatm",    "field": "Elongation",           "condition": None},
    {"key": "elongation_cv","title": "Elongation CV",                "unit": "%",        "main_table": "tbllaborstatimatds",  "alt_table": "tbllaborstatimatm",    "field": "ElongationCV",         "condition": None},
    {"key": "tenacity",     "title": "Tenacity",                     "unit": "cN/dtex",  "main_table": "tbllaborstatimatds",  "alt_table": "tbllaborstatimatm",    "field": "Tenacity",             "condition": None},
    {"key": "tenacity_cv",  "title": "Tenacity CV",                  "unit": "%",        "main_table": "tbllaborstatimatds",  "alt_table": "tbllaborstatimatm",    "field": "TenacityCV",           "condition": None},
    {"key": "fpm",          "title": "Intermingling Points",         "unit": "FP/m",     "main_table": "tbllaboritematlab",   "alt_table": "tbllaboritematplus",   "field": "FPm",                  "condition": "Tension = 0"},
    {"key": "fpm_cv",       "title": "Intermingling Points CV",      "unit": "%",        "main_table": "tbllaboritematlab",   "alt_table": "tbllaboritematplus",   "field": "FPmCV",                "condition": "Tension = 0"},
    {"key": "stab_03",      "title": "FPm Stability@0.3cN/dtex",    "unit": "%",        "main_table": "tbllaboritematlab",   "alt_table": "tbllaboritematplus",   "field": "Stability",            "condition": "Tension = 0.3"},
    {"key": "stab_06",      "title": "FPm Stability@0.6cN/dtex",    "unit": "%",        "main_table": "tbllaboritematlab",   "alt_table": "tbllaboritematplus",   "field": "Stability",            "condition": "Tension = 0.6"},
    {"key": "stab_10",      "title": "FPm Stability@1.0cN/dtex",    "unit": "%",        "main_table": "tbllaboritematlab",   "alt_table": "tbllaboritematplus",   "field": "Stability",            "condition": "Tension = 1"},
    {"key": "stab_13",      "title": "FPm Stability@1.3cN/dtex",    "unit": "%",        "main_table": "tbllaboritematlab",   "alt_table": "tbllaboritematplus",   "field": "Stability",            "condition": "Tension = 1.3"},
    {"key": "fpm_dtyomat",  "title": "FP/m DTYoMat",                "unit": "FP/m",     "main_table": "tbllabordtyomat",     "alt_table": None,                  "field": "FPm",                  "condition": None},
    {"key": "cv_fp_dtyomat","title": "FP/m CV DTYoMat",             "unit": "%",        "main_table": "tbllabordtyomat",     "alt_table": None,                  "field": "CV_FP",                "condition": None},
    {"key": "yarn_ten_bef", "title": "Yarn Tension before Jet",     "unit": "cN",       "main_table": "tbltrial",            "alt_table": None,                  "field": "YarnTensionBeforeJet", "condition": None},
    {"key": "yarn_ten_aft", "title": "Yarn Tension after Jet",      "unit": "cN",       "main_table": "tbltrial",            "alt_table": None,                  "field": "YarnTensionAfterJet",  "condition": None},
    {"key": "waterbath_fpm","title": "Waterbath FP/m",              "unit": "FP/m",     "main_table": "tbllaborwaterbath",   "alt_table": None,                  "field": "FPm",                  "condition": None},
    {"key": "yarn_ten_t1",   "title": "Yarn Tension T1",              "unit": "cN",       "main_table": "tbltrialsettings",    "alt_table": None,                  "field": "YarnTensionT1",        "condition": None},
    {"key": "yarn_ten_t2",   "title": "Yarn Tension T2",              "unit": "cN",       "main_table": "tbltrialsettings",    "alt_table": None,                  "field": "YarnTensionT2",        "condition": None},
    {"key": "olt",           "title": "OLT",                          "unit": "",         "main_table": "tbltrialsettings",    "alt_table": None,                  "field": "OLT",                  "condition": None},
    # Jet Air Consumption (Kalibrier-Messung, series-scoped, siehe
    # tblLaborJetAirConsumption). Wird NICHT ueber die generische
    # trial-basierte _fetch_y_values geholt (kein TrialID auf dieser Tabelle) -
    # daher in _COMPUTED_Y_KEYS gelistet und in _fetch_series_data manuell
    # als zusaetzliche Pseudo-Zeilen (eine pro physischer Duese x Druckstufe)
    # ins Datenpaket gemischt.
    {"key": "jet_air_consumption", "title": "Air Consumption (Jet Cal)", "unit": "Nm³/h", "main_table": "tblLaborJetAirConsumption", "alt_table": None, "field": "AirConsumption", "condition": None},
]

# X-Achsen-Definition
X_AXES = [
    {"key": "air_pressure",  "title": "Air Pressure",    "unit": "bar",   "field": "air_pressure"},
    {"key": "overfeed",      "title": "Overfeed",         "unit": "%",     "field": "overfeed"},
    {"key": "speed",         "title": "Speed",            "unit": "m/min", "field": "speed"},
    {"key": "trial_nr",      "title": "Trial Number",     "unit": "",      "field": "trial_nr"},
    {"key": "jet_plate",     "title": "Jet Plate Number", "unit": "",      "field": "jet_plate"},
    {"key": "air_cons",      "title": "Air Consumption",  "unit": "m³/h",  "field": "air_cons"},
    {"key": "custom_group",  "title": "Custom Group",     "unit": "",      "field": "custom_group", "is_group_by": True},
    # Jet Air Consumption (Kalibrier-Messung, siehe tblLaborJetAirConsumption):
    # eigener Key, bewusst NICHT "air_pressure" wiederverwendet, da das den
    # Betriebsdruck (T.AirPressure) waehrend eines Yarn-Trials meint - ein
    # anderes Konzept als der hier definierte Kalibrier-Druck pro physischer Duese.
    {"key": "jetcal_pressure", "title": "Air Pressure (Jet Cal)", "unit": "bar", "field": "jetcal_pressure",
     "main_table": "tblLaborJetAirConsumption"},
]

# Fallback-Liste falls tblSmartChartAxis nicht verfügbar
_KNOWN_TABLES_FALLBACK = [
    "tbllabortiter",
    "tbllaborstatimatds",
    "tbllaborstatimatm",
    "tbllaboritematlab",
    "tbllaboritematplus",
    "tbllabordtyomat",
    "tbllaborwaterbath",
    "tbltrial",
    "tbltrialsettings",
]

def _get_known_tables() -> list:
    """Gibt alle Tabellen zurück die als MainTable in Y-Einträgen von
    tblSmartChartAxis vorkommen. Fallback auf hardcodierte Liste."""
    try:
        from db.connection import fetch_all, table_exists
        if not table_exists("tblSmartChartAxis"):
            return _KNOWN_TABLES_FALLBACK
        rows = fetch_all(
            "SELECT DISTINCT MainTable FROM tblSmartChartAxis "
            "WHERE AxisType = 'Y' AND IsActive = 1 AND MainTable IS NOT NULL",
            []
        )
        tables = [str(r["MainTable"]) for r in rows if r.get("MainTable")]
        # tbltrial immer dabei (wird für X-Achsen und Freifeld benötigt)
        if "tbltrial" not in tables:
            tables.append("tbltrial")
        return tables if tables else _KNOWN_TABLES_FALLBACK
    except Exception as e:
        logger.warning("_get_known_tables: %s — nutze Fallback", e)
        return _KNOWN_TABLES_FALLBACK

# Modul-Level Alias für Rückwärtskompatibilität
KNOWN_TABLES = _KNOWN_TABLES_FALLBACK


def _load_axes_from_db():
    """Lädt X- und Y-Achsen aus tblSmartChartAxis.
    Fallback auf hardcodierte Listen wenn Tabelle nicht existiert.
    """
    from db.connection import fetch_all, table_exists

    if not table_exists("tblSmartChartAxis"):
        logger.warning("tblSmartChartAxis not found - using built-in axes")
        return None, None

    try:
        rows = fetch_all(
            "SELECT ID, AxisType, KeyName, Title, Unit, MainTable, AltTable, "
            "Field, FilterCondition, SortOrder, SubAxisID, IsGroupBy, JoinSQL "
            "FROM tblSmartChartAxis "
            "WHERE IsActive = 1 "
            "ORDER BY AxisType, SortOrder",
            []
        )
        y_axes, x_axes, g_axes = [], [], []
        for r in rows:
            entry = {
                "id":          r["ID"],
                "key":         r["KeyName"],
                "title":       r["Title"],
                "unit":        r["Unit"] or "",
                "main_table":  r["MainTable"],
                "alt_table":   r["AltTable"] or None,
                "field":       r["Field"],
                "condition":   r["FilterCondition"] or None,
                "sub_axis_id": r["SubAxisID"] if r.get("SubAxisID") is not None else None,
                "is_group_by": bool(r.get("IsGroupBy")),
                "join_sql":    str(r["JoinSQL"]) if r.get("JoinSQL") else None,
            }
            if r["AxisType"] == "Y":
                y_axes.append(entry)
            elif r["AxisType"] == "X":
                x_axes.append(entry)
            elif r["AxisType"] == "G":
                g_axes.append(entry)
        logger.info("SmartChart: %d Y-Achsen, %d X-Achsen, %d G-Achsen aus DB geladen",
                    len(y_axes), len(x_axes), len(g_axes))
        return y_axes or None, x_axes or None, g_axes or None
    except Exception as e:
        logger.error("_load_axes_from_db: %s", e)
        return None, None, None


# ---------------------------------------------------------------------------
# Datenbankabfrage — Y-Werte
# ---------------------------------------------------------------------------

def _fetch_y_values(
    trial_ids: List[int],
    main_table: str,
    alt_table: Optional[str],
    field: str,
    condition: Optional[str],
) -> Dict[int, Optional[float]]:
    from db.connection import fetch_all, table_exists

    if not trial_ids:
        return {}

    def _query(table: str) -> Dict[int, Optional[float]]:
        if not table_exists(table):
            return {}
        # tblTrial hat keinen TrialID FK — es IS die Trial-Table
        id_col  = "ID" if table.lower() == "tbltrial" else "TrialID"
        cond    = f" AND {condition}" if condition else ""
        ph      = ",".join(["?" for _ in trial_ids])
        # AVG statt Einzelwert: manche Tabellen (z.B. tbltrialsettings) haben
        # pro Trial mehrere Zeilen (eine pro Ply), nicht 1:1 wie tbltrial.
        # 0 und NULL werden dabei nicht mitgezaehlt (0 = "kein Messwert",
        # nicht "Messwert 0"). Fuer Tabellen mit ohnehin nur einer Zeile pro
        # Trial (Titer, tbltrial, ...) aendert das nichts am Ergebnis.
        sql = (
            f"SELECT {id_col} AS tid, AVG({field}) AS val "
            f"FROM {table} "
            f"WHERE {id_col} IN ({ph}) AND {field} IS NOT NULL AND {field} <> 0{cond} "
            f"GROUP BY {id_col}"
        )
        try:
            rows = fetch_all(sql, trial_ids)
            return {
                int(r["tid"]): (float(r["val"]) if r["val"] not in (None, "") else None)
                for r in rows
            }
        except Exception as e:
            logger.warning("_fetch_y_values %s.%s: %s", table, field, e)
            return {}

    result = _query(main_table)
    if alt_table:
        missing = [tid for tid in trial_ids if result.get(tid) is None]
        if missing:
            for tid, val in _query(alt_table).items():
                if result.get(tid) is None:
                    result[tid] = val
    return result


def _fetch_table_columns() -> Dict[str, List[str]]:
    """Gibt {tabellenname: [spaltennamen]} für alle bekannten Tablen zurück."""
    from db.connection import get_columns_map, table_exists
    result: Dict[str, List[str]] = {}
    for tbl in _get_known_tables():
        try:
            if table_exists(tbl):
                cols_map = get_columns_map(tbl)
                # Nur numerisch sinnvolle Spalten — ID/FK-Spalten weglassen
                skip = {"id", "trialid", "globalid", "trialserieid", "trialsid",
                        "createdby", "createdat", "timestamp", "user"}
                cols = [v for k, v in sorted(cols_map.items())
                        if k not in skip and not k.endswith("id")]
                result[tbl] = cols
        except Exception as e:
            logger.warning("_fetch_table_columns %s: %s", tbl, e)
    return result


def _fetch_series_data(series_pk: int) -> List[Dict[str, Any]]:
    from db.connection import fetch_all, table_exists

    rows: List[Dict[str, Any]] = []
    try:
        # Use DB axes if available, fallback to hardcoded
        db_y, db_x, db_g = _load_axes_from_db()
        axes_to_load = db_y if db_y else Y_AXES
        active_x     = db_x if db_x else X_AXES

        # Extra tbltrial columns needed for DB-defined X-axes that aren't
        # already covered by the hardcoded SELECT (field from tbltrial only).
        _hardcoded_keys = {"air_pressure", "overfeed", "speed", "trial_nr",
                           "jet_plate", "air_cons"}
        _extra_x = [
            xdef for xdef in active_x
            if xdef.get("main_table", "tbltrial").lower() == "tbltrial"
            and xdef["key"] not in _hardcoded_keys
        ]
        _extra_selects = "".join(
            f", T.{xdef['field']} AS {xdef['key']}"
            for xdef in _extra_x
        )
        # Reference samples (db/trial_reference.py) come along flagged - the
        # report JS draws them as benchmark lines, never as data points.
        _has_refs = has_reference_columns()
        if _has_refs:
            _extra_selects += (f", T.{IS_REFERENCE_COL} AS is_reference"
                               f", T.{REFERENCE_NAME_COL} AS reference_name")

        sql_base = f"""
            SELECT T.ID AS trial_id, T.Versuchsnummer AS trial_nr,
                   T.AirPressure AS air_pressure, T.Shaft2x_OF AS overfeed,
                   T.SpeedShaft2 AS speed, T.Versuchsnummer AS trial_nr2,
                   T.JetPlate AS jet_plate,
                   J.Jet AS jet_name,
                   J.Luftverbrauch AS air_cons,
                   MC.Maschine AS machine_name,
                   YarnSub.yarn_label AS yarn_name
                   {_extra_selects}
            FROM tblTrial AS T
            LEFT JOIN tbljets AS J ON J.ID = T.JetID
            LEFT JOIN tblTrialSeries AS TS ON TS.ID = T.TrialSeriesID
            LEFT JOIN tblMaschine AS MC ON MC.ID = TS.MachineID
            LEFT JOIN (
                SELECT GTS.TrialID,
                       GROUP_CONCAT(DISTINCT GY.Name ORDER BY GY.Name SEPARATOR ' / ') AS yarn_label
                FROM tblTrialSettings AS GTS
                INNER JOIN tblYarn AS GY ON GY.ID = GTS.YarnID
                GROUP BY GTS.TrialID
            ) AS YarnSub ON YarnSub.TrialID = T.ID
            WHERE T.TrialSeriesID = ?
            ORDER BY T.Versuchsnummer ASC
        """
        base_rows = fetch_all(sql_base, [series_pk])
        if not base_rows:
            return []

        trial_ids = [int(r["trial_id"]) for r in base_rows]

        # Keys that are computed in Python — skip DB fetch for these
        _COMPUTED_Y_KEYS = {"air_cons_real", "jet_air_consumption"}

        y_data: Dict[str, Dict[int, Optional[float]]] = {}
        for ydef in axes_to_load:
            if ydef["key"] in _COMPUTED_Y_KEYS:
                continue
            y_data[ydef["key"]] = _fetch_y_values(
                trial_ids  = trial_ids,
                main_table = ydef["main_table"],
                alt_table  = ydef["alt_table"],
                field      = ydef["field"],
                condition  = ydef["condition"],
            )

        def _f(v):
            if v is None or v == "": return None
            try: return float(v)
            except: return None

        for r in base_rows:
            tid = int(r["trial_id"])
            row: Dict[str, Any] = {
                "trial_id":     tid,
                "trial_nr":     int(r.get("trial_nr") or 0),
                "air_pressure": _f(r.get("air_pressure")),
                "overfeed":     _f(r.get("overfeed")),
                "speed":        _f(r.get("speed")),
                "jet_plate":    _f(r.get("jet_plate")),
                # Realer Luftverbrauch = Jet-Faktor * (gefahrener Betriebsdruck
                # dieses Trials + 1), nicht der reine Jet-Faktor - der Faktor
                # allein sagt nichts ueber den tatsaechlich gefahrenen Druck aus.
                "air_cons":      round(_f(r.get("air_cons")) * (_f(r.get("air_pressure")) + 1), 2)
                                 if _f(r.get("air_cons")) is not None and _f(r.get("air_pressure")) is not None
                                 else None,
                # Separater Y-Achsen-Eintrag (tblSmartChartAxis ID 45, "air_cons_real")
                # nutzt dieselbe Formel wie die X-Achse oben - eigener Key, da als
                # eigenstaendige Y-Achse ueber die generische Achsen-Iteration
                # (axes_to_load) auswaehlbar, nicht nur als X-Feld.
                "air_cons_real": round(_f(r.get("air_cons")) * (_f(r.get("air_pressure")) + 1), 2)
                                 if _f(r.get("air_cons")) is not None and _f(r.get("air_pressure")) is not None
                                 else None,
                "jet_name":     str(r.get("jet_name") or "Unbekannt"),
                "machine_name": str(r.get("machine_name") or ""),
                "yarn_name":    str(r.get("yarn_name") or ""),
            }
            # Extra X-axis fields from tbltrial
            for xdef in _extra_x:
                row[xdef["key"]] = _f(r.get(xdef["key"]))
            if _has_refs and is_reference_value(r.get("is_reference")):
                row["is_reference"] = True
                row["reference_name"] = str(r.get("reference_name") or "")
            # Y-axis values (skip computed keys — already set in row dict above)
            for ydef in axes_to_load:
                if ydef["key"] in _COMPUTED_Y_KEYS:
                    continue
                val = y_data[ydef["key"]].get(tid)
                row[ydef["key"]] = float(val) if val is not None else None
            rows.append(row)

        # ── Jet Air Consumption: eigene Messpunkte (physische Duese x Druck)
        # als zusaetzliche Pseudo-Zeilen anhaengen. Kein echter Trial-Bezug -
        # trial_id ist eine synthetische negative ID (kollisionsfrei mit
        # echten Trial-IDs), andere Y-Felder bleiben bewusst leer, damit sie
        # in normalen (trial-basierten) Charts nicht auftauchen.
        try:
            if table_exists("tblLaborJetAirConsumption"):
                ja_rows = fetch_all(
                    "SELECT ja.[ID] AS ja_id, ja.[JetID] AS jet_id, ja.[JetPlate] AS jet_plate, "
                    "ja.[AirPressure] AS jetcal_pressure, ja.[AirConsumption] AS jet_air_consumption, "
                    "J.Jet AS jet_name "
                    "FROM tblLaborJetAirConsumption ja "
                    "LEFT JOIN tbljets J ON J.ID = ja.[JetID] "
                    "WHERE ja.[TrialSeriesID] = ?",
                    [series_pk],
                )
                for jr in ja_rows:
                    plate = jr.get("jet_plate")
                    jname = str(jr.get("jet_name") or f"Jet {jr.get('jet_id')}")
                    rows.append({
                        "trial_id": -int(jr["ja_id"]),
                        "trial_nr": 0,
                        # Legende/Gruppierung nur nach Jet-Typ (nicht Jet+Plate) -
                        # dadurch werden die Plaettchen desselben Jets von der
                        # bestehenden Mittelwert/SD-Logik automatisch gemittelt.
                        "jet_name": jname,
                        "jet_plate": _f(plate),
                        "jetcal_pressure": _f(jr.get("jetcal_pressure")),
                        "jet_air_consumption": _f(jr.get("jet_air_consumption")),
                    })
        except Exception as e:
            logger.error("screen_report: Fehler beim Laden der Jet Air Consumption Daten: %s", e)

    except Exception as e:
        logger.error("screen_report: Fehler beim Laden: %s", e)

    return rows


def series_short_title(series_pk: int) -> Optional[str]:
    """Builds "<ExperimentID>.<NN>" (e.g. "2026-73-033.02") from the
    leading number of SeriesName plus the trial series' experiment ID -
    a compact SmartChart tab/window title so several SmartChart tabs open
    at once stay distinguishable (see main.py::_smartchart_title()).
    Returns None if the series no longer exists."""
    import re
    from db.connection import fetch_all

    try:
        rows = fetch_all(
            "SELECT TS.SeriesName, E.[Experiment ID] AS exp_id "
            "FROM tblTrialSeries AS TS "
            "LEFT JOIN tblExperimente AS E ON E.ID = TS.ExperimentID "
            "WHERE TS.ID = ?",
            [series_pk],
        )
    except Exception as e:
        logger.error("series_short_title: %s", e)
        return None

    if not rows:
        return None

    exp_id = str(rows[0].get("exp_id") or "").strip()
    sname = str(rows[0].get("SeriesName") or "").strip()
    m = re.match(r"(\d+)", sname)
    nn = m.group(1) if m else ""

    if exp_id and nn:
        return f"{exp_id}.{nn}"
    return exp_id or (sname or None)


def _fetch_infobox_data(series_pk: int) -> Dict[str, Any]:
    from db.connection import fetch_all, table_exists

    info: Dict[str, Any] = {
        "series_name":   "",
        "material":      "",
        "machine":       "",
        "air_pressures": [],
        "overfeeds":     [],
        "speeds":        [],
        "n_trials":      0,
    }
    # Series + Machine
    try:
        ts = fetch_all(
            "SELECT TS.SeriesName, TS.MachineID, E.[Experiment ID] AS exp_id "
            "FROM tblTrialSeries AS TS "
            "LEFT JOIN tblExperimente AS E ON E.ID = TS.ExperimentID "
            "WHERE TS.ID = ?",
            [series_pk]
        )
        if ts:
            sname = str(ts[0].get("SeriesName") or "")
            exp   = str(ts[0].get("exp_id") or "")
            info["series_name"] = f"{exp}.{sname}" if exp else sname
            machine_id = ts[0].get("MachineID")
            if machine_id:
                m = fetch_all("SELECT Maschine FROM tblMaschine WHERE ID = ?", [machine_id])
                if m:
                    info["machine"] = str(m[0].get("Maschine") or "")
    except Exception as e:
        logger.error("_fetch_infobox_data series/machine: %s", e)

    # Trials + Material
    try:
        trials = fetch_all(
            f"SELECT ID FROM tblTrial WHERE TrialSeriesID = ? AND {exclude_references_sql('')}",
            [series_pk])
        info["n_trials"] = len(trials)
        trial_ids = [int(r["ID"]) for r in trials]
        if trial_ids:
            ph = ",".join(["?" for _ in trial_ids])
            yarn_rows = fetch_all(
                "SELECT DISTINCT Y.Name AS YarnName, TS.Ply "
                "FROM tblTrialSettings AS TS "
                "INNER JOIN tblYarn AS Y ON Y.ID = TS.YarnID "
                f"WHERE TS.TrialID IN ({ph}) ORDER BY TS.Ply",
                trial_ids
            )
            if yarn_rows:
                parts = []
                for r in yarn_rows:
                    yn  = str(r.get("YarnName") or "").strip()
                    ply = str(r.get("Ply") or "").strip()
                    parts.append(f"{ply}: {yn}" if ply else yn)
                info["material"] = " • ".join(parts)
    except Exception as e:
        logger.error("_fetch_infobox_data trials/material: %s", e)

    # Dimensions
    try:
        dims = fetch_all(
            "SELECT DISTINCT AirPressure, Shaft2x_OF AS overfeed, SpeedShaft2 AS speed "
            f"FROM tblTrial WHERE TrialSeriesID = ? AND {exclude_references_sql('')}", [series_pk]
        )
        info["air_pressures"] = sorted(set(
            float(r["AirPressure"]) for r in dims if r["AirPressure"] is not None))
        info["overfeeds"] = sorted(set(
            float(r["overfeed"]) for r in dims if r["overfeed"] is not None))
        info["speeds"] = sorted(set(
            float(r["speed"]) for r in dims if r["speed"] is not None))
    except Exception as e:
        logger.error("_fetch_infobox_data dims: %s", e)

    # Jets
    try:
        jet_rows = fetch_all(
            "SELECT DISTINCT J.Jet AS jet_name FROM tblTrial AS T "
            "LEFT JOIN tbljets AS J ON J.ID = T.JetID "
            f"WHERE T.TrialSeriesID = ? AND {exclude_references_sql('T')} ORDER BY J.Jet",
            [series_pk]
        )
        info["jets"] = [str(r["jet_name"]) for r in jet_rows if r.get("jet_name")]
    except Exception as e:
        logger.error("_fetch_infobox_data jets: %s", e)

    return info
