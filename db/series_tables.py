"""series_tables.py - the data behind the Show Experiment tabs, without Qt.

Moved out of ui/screen_show_experiment.py (2026-11-13) so that the desktop
screen and the web app (tripplet_web) show the same cells. The desktop turns
a LabPivot into a PivotEditModel (ShowExperimentScreen._model_from_pivot);
the web app sends it as JSON. Queries and cell rules are unchanged - only
moved. Verified cell by cell (all roles) against the desktop on dev_local.

Covered: trial columns, the jet info rows on top of the lab tabs, every lab
tab with trial columns (LAB_TABS: Titer, Statimat M, Statimat DS, Waterbath,
EKB, Hot Air / Hot Water / ATY Shrinkage, Rapid 600, Itemat Lab, Itemat Plus,
DTYoMat, ATYoMat) and Jet Air Consumption (build_jet_air: rows = physical jets,
columns = pressure steps, hence not in LAB_TABS). Machine Data is in
db/machine_data.py.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from db.connection import fetch_all
from db.connection import get_columns_map as _db_get_columns_map
from db.connection import table_exists as _db_table_exists
from db.trial_reference import (
    IS_REFERENCE_COL,
    REFERENCE_NAME_COL,
    has_reference_columns,
    is_reference_value,
    reference_label,
)
from ui.text_normalize import resolve_field


def table_exists(name: str) -> bool:
    return _db_table_exists(name.lower())


def get_columns_map(table: str) -> Dict[str, str]:
    return _db_get_columns_map(table.lower())


# --------------------------------------------------------------------------- cell bindings
@dataclass
class CellBinding:
    """Verbindet eine Pivot-Tabellen-Zelle mit einem konkreten DB-Datensatz.

    Enthält: Tabelle, Spalte, Primärschlüssel – genug um einen einzelnen UPDATE auszuführen.
    """
    table: str
    id_field: str
    id_value: Any
    field: str


@dataclass
class GroupCellBinding:
    """Wie CellBinding, aber für YarnUse-Gruppen: schreibt denselben Wert
    in mehrere tblTrialSettings-Zeilen gleichzeitig.
    """
    table: str
    id_field: str
    id_values: List[int]  # alle Settings-IDs der Gruppe
    field: str


# --------------------------------------------------------------------------- trials (columns)
@dataclass
class SeriesTrials:
    series_id: Any
    trials: List[Dict[str, Any]]
    trial_ids: List[Any]
    trial_vnos: List[Any]
    reference_names: Dict[int, str]      # TrialID -> name, only reference samples
    labels: List[str]                    # column titles: "V12" or the reference label


def load_trials(series_pk: Any) -> SeriesTrials:
    """Trials of a series in column order. Reference samples (customer originals,
    see db/trial_reference.py) come first, so the benchmark is always the leftmost column(s)."""
    if has_reference_columns():
        rows = fetch_all(
            f"""
            SELECT ID, Versuchsnummer, {IS_REFERENCE_COL}, {REFERENCE_NAME_COL}
            FROM tblTrial
            WHERE TrialSeriesID = ?
            ORDER BY COALESCE({IS_REFERENCE_COL}, 0) DESC,
                     CASE WHEN COALESCE({IS_REFERENCE_COL}, 0) = 1 THEN ABS(Versuchsnummer)
                          ELSE Versuchsnummer END
            """,
            [series_pk],
        )
    else:
        rows = fetch_all(
            """
            SELECT ID, Versuchsnummer
            FROM tblTrial
            WHERE TrialSeriesID = ?
            ORDER BY Versuchsnummer
            """,
            [series_pk],
        )
    reference_names = {
        int(r["ID"]): str(r.get(REFERENCE_NAME_COL) or "")
        for r in rows if is_reference_value(r.get(IS_REFERENCE_COL))
    }
    labels = [
        reference_label(r["Versuchsnummer"]) if int(r["ID"]) in reference_names
        else f"V{r['Versuchsnummer']}"
        for r in rows
    ]
    return SeriesTrials(series_id=series_pk, trials=rows, trial_ids=[r["ID"] for r in rows],
                        trial_vnos=[r["Versuchsnummer"] for r in rows],
                        reference_names=reference_names, labels=labels)


def jet_info_rows(trial_ids: List[Any]) -> list:
    """3 Zeilen (label, [wert_pro_trial]) für Jet / Jet Plate / Air Pressure -
    read-only on top of every lab tab."""
    if not trial_ids:
        return [("Jet", []), ("Jet Plate", []), ("Air Pressure", [])]
    try:
        placeholders = ",".join(["?"] * len(trial_ids))
        # Jet name via JOIN auf tblDTYJets
        jet_rows = fetch_all(
            f"SELECT T.ID, T.Versuchsnummer, J.Jet AS JetName, "
            f"T.JetPlate, T.AirPressure "
            f"FROM tblTrial AS T "
            f"LEFT JOIN tblDTYJets AS J ON J.ID = T.JetID "
            f"WHERE T.ID IN ({placeholders}) "
            f"ORDER BY T.Versuchsnummer",
            trial_ids,
        )
        by_id = {int(r["ID"]): r for r in jet_rows}
        # Preserve order of trial_ids
        ordered = [by_id.get(int(tid), {}) for tid in trial_ids]
        jets = [str(r.get("JetName") or "") for r in ordered]
        plates = [str(r.get("JetPlate") or "") for r in ordered]
        airs = [str(r.get("AirPressure") or "") for r in ordered]
        return [("Jet", jets), ("Jet Plate", plates), ("Air Pressure", airs)]
    except Exception:
        n = len(trial_ids)
        return [("Jet", [""] * n), ("Jet Plate", [""] * n), ("Air Pressure", [""] * n)]


# --------------------------------------------------------------------------- lab pivots
@dataclass
class LabPivot:
    """One lab tab: rows = measurements, columns = trials (same order as SeriesTrials) -
    or, with col_titles, other columns (Jet Air). extra holds per-tab facts (Titer:
    out_of_tolerance/has_target/target; Itemat Lab/Plus: tensions; Jet Air l/min:
    unit_scale/unit_field)."""
    key: str                                   # "titer", "stat", ...
    row_titles: List[str]
    validators: List[Optional[str]]
    cells: List[List[Tuple[Any, Optional[CellBinding]]]]   # [row][col] = (value, binding)
    alerts: Dict[Tuple[int, int], str] = field(default_factory=dict)   # (data row, col) -> "red"/"orange"
    extra: Dict[str, Any] = field(default_factory=dict)
    # Column titles when the columns are NOT the trials (Jet Air: pressure steps);
    # None = the trial columns (titles = SeriesTrials.labels).
    col_titles: Optional[List[str]] = None


def _empty(n_rows: int, n_cols: int) -> List[List[Tuple[Any, Optional[CellBinding]]]]:
    return [[(None, None) for _ in range(n_cols)] for _ in range(n_rows)]


def _first_table(candidates) -> Optional[str]:
    for _cand in candidates:
        if table_exists(_cand):
            return _cand
    return None


def _one_record_per_trial(key: str, st: SeriesTrials, table: Optional[str], fields: List[Tuple[str, List[str]]],
                          *, int_keys: bool) -> Optional[LabPivot]:
    """Common shape: one record per trial, one row per field. fields = [(row title, column candidates)].
    int_keys: whether the original grouped by int(TrialID) (it matters only for the dict key type)."""
    if not table or not st.trial_ids:
        return None
    cmap = get_columns_map(table)
    cols = [resolve_field(cands, cmap) for _title, cands in fields]
    if not all(cols):
        return None
    sel = ", ".join(f"[{c}] AS F{i}" for i, c in enumerate(cols))
    rows = fetch_all(
        f"SELECT ID, TrialID, {sel} FROM {table} WHERE TrialID IN ({','.join(['?'] * len(st.trial_ids))})",
        st.trial_ids,
    )
    if not rows:
        return None
    by_trial = {(int(r["TrialID"]) if int_keys else r["TrialID"]): r for r in rows}
    titles = [t for t, _c in fields]
    cells = _empty(len(titles), len(st.trials))
    for c_idx, trial in enumerate(st.trials):
        rec = by_trial.get(trial["ID"])
        if rec:
            for i, col in enumerate(cols):
                cells[i][c_idx] = (rec.get(f"F{i}"), CellBinding(table, "ID", rec["ID"], col))
    return LabPivot(key, titles, ["onlyDoubles"] * len(titles), cells)


_STATIMAT_FIELDS = [
    ("Elongation (%)", ["Elongation (%)", "Elongation%", "Elongation"]),
    ("Elongation CV (%)", ["Elongation CV (%)", "ElongationCV%", "ElongationCV"]),
    ("Tenacity (cN/dtex)", ["Tenacity (cN/dtex)", "Tenacity", "Tenacity(cN/dtex)"]),
    ("Tenacity CV (%)", ["Tenacity CV (%)", "TenacityCV%", "TenacityCV"]),
]


def build_stat(st: SeriesTrials) -> Optional[LabPivot]:
    table = _first_table(("tbllaborstatimatm", "tblLaborStatimat", "tbllaborstatimat"))
    return _one_record_per_trial("stat", st, table, _STATIMAT_FIELDS, int_keys=False)


def build_stat_ds(st: SeriesTrials) -> Optional[LabPivot]:
    table = _first_table(("tbllaborstatimatds", "tblLaborStatimatDS"))
    return _one_record_per_trial("stat_ds", st, table, _STATIMAT_FIELDS, int_keys=False)


def build_ekb(st: SeriesTrials) -> Optional[LabPivot]:
    table = "tblLaborEKB" if table_exists("tblLaborEKB") else None
    return _one_record_per_trial("ekb", st, table, [
        ("Einkräuselung X", ["EinkräuselungX", "Einkräuselung X"]),
        ("Einkräuselung CV", ["EinkräuselungCV", "Einkräuselung CV"]),
        ("Kennkräuselung X", ["KennkräuselungX", "Kennkräuselung X"]),
        ("Kennkräuselung CV", ["KennkräuselungCV", "Kennkräuselung CV"]),
        ("Kräuselbeständigkeit X", ["KräuselbeständigkeitX", "Kräuselbeständigkeit X"]),
        ("Kräuselbeständigkeit CV", ["KräuselbeständigkeitCV", "Kräuselbeständigkeit CV"]),
    ], int_keys=True)


_SHRINKAGE_FIELDS = [("Shrinkage X", ["ShrinkageX", "Shrinkage X"]),
                     ("Shrinkage CV", ["ShrinkageCV", "Shrinkage CV"])]


def build_hot_air_shrinkage(st: SeriesTrials) -> Optional[LabPivot]:
    t = "tblLaborHeissLuftSchrumpf"
    return _one_record_per_trial("hot_air_shrinkage", st, t if table_exists(t) else None, _SHRINKAGE_FIELDS,
                                 int_keys=True)


def build_hot_water_shrinkage(st: SeriesTrials) -> Optional[LabPivot]:
    t = "tblLaborKochSchrumpf"
    return _one_record_per_trial("hot_water_shrinkage", st, t if table_exists(t) else None, _SHRINKAGE_FIELDS,
                                 int_keys=True)


def build_aty_shrinkage(st: SeriesTrials) -> Optional[LabPivot]:
    t = "tblLaborATYShrinkage"
    return _one_record_per_trial("aty_shrinkage", st, t if table_exists(t) else None, _SHRINKAGE_FIELDS,
                                 int_keys=True)


def build_titer(st: SeriesTrials) -> Optional[LabPivot]:
    titer_table = _first_table(("tbltiter", "tblLaborTiter"))
    if not titer_table or not st.trial_ids:
        return None
    col_titer = resolve_field(["Titer", "Titer (dtex)", "Titer(dtex)"], get_columns_map(titer_table))
    if not col_titer:
        return None
    rows = fetch_all(
        f"""
        SELECT LT.ID, LT.TrialID, LT.[{col_titer}] AS Titer
        FROM {titer_table} AS LT
        WHERE LT.TrialID IN ({",".join(["?"] * len(st.trial_ids))})
        """,
        st.trial_ids,
    )
    if not rows:
        return None
    by_trial = defaultdict(dict)
    for r in rows:
        by_trial[int(r["TrialID"])] = r
    cells = _empty(1, len(st.trials))
    for c_idx, trial in enumerate(st.trials):
        rec = by_trial.get(trial["ID"])
        if rec:
            cells[0][c_idx] = (rec.get("Titer"), CellBinding(titer_table, "ID", rec["ID"], col_titer))
    p = LabPivot("titer", ["Titer (dtex)"], ["onlyDoubles"], cells)

    # ── Soll-Titer aus Trial 1 berechnen (einmalig für die ganze Series) ──
    # out_of_tolerance = columns whose titer is outside +-5 % of the target (red here,
    # orange Tenacity in Statimat DS); has_target = a target could be computed
    out: set = set()
    p.extra["out_of_tolerance"] = out
    p.extra["has_target"] = False
    try:
        # First real trial - a reference sample (listed first) is
        # the customer's yarn and says nothing about our target titer.
        first_trial_id = next(
            (t["ID"] for t in st.trials if int(t["ID"]) not in st.reference_names),
            None,
        )
        if first_trial_id is not None:
            yarn_rows = fetch_all("SELECT YarnID FROM tbltrialsettings WHERE TrialID = ?", [first_trial_id])
            yarn_ids = [r["YarnID"] for r in yarn_rows if r.get("YarnID") is not None]
            soll_titer = None
            if yarn_ids:
                # Lookup: eindeutige YarnIDs -> Endtiter
                unique_ids = list(set(yarn_ids))
                placeholders = ",".join(["?"] * len(unique_ids))
                titer_rows = fetch_all(f"SELECT ID, Endtiter FROM tblyarn WHERE ID IN ({placeholders})", unique_ids)
                endtiter_by_id = {}
                for tr in titer_rows:
                    try:
                        endtiter_by_id[int(tr["ID"])] = float(tr["Endtiter"] or 0)
                    except Exception:
                        pass
                # Summiere pro Vorkommen in yarn_ids (Duplikate = mehrere Plies desselben Garns)
                total = 0.0
                for yid in yarn_ids:
                    total += endtiter_by_id.get(int(yid), 0.0)
                soll_titer = total if total > 0 else None
            if soll_titer:
                p.extra["has_target"] = True
                p.extra["target"] = soll_titer
                lo = soll_titer * 0.95
                hi = soll_titer * 1.05
                for c_idx, trial in enumerate(st.trials):
                    rec = by_trial.get(trial["ID"])
                    if not rec:
                        continue
                    raw = rec.get("Titer")
                    if raw in (None, ""):
                        continue
                    try:
                        val = float(str(raw).replace(",", "."))
                    except Exception:
                        continue
                    if val < lo or val > hi:
                        out.add(c_idx)
                        p.alerts[(0, c_idx)] = "red"
    except Exception:
        pass
    return p


def build_water(st: SeriesTrials) -> Optional[LabPivot]:
    if not st.trial_ids:
        return None
    table_name = "tblLaborWaterbath"
    id_col = "ID"
    trial_col = "TrialID"
    inter_col = "Intermingling Points (FP/m)"
    placeholders = ",".join(["?"] * len(st.trial_ids))
    rows = fetch_all(
        f"""
        SELECT [{id_col}] AS RecID,
               [{trial_col}] AS WBTrialID,
               [{inter_col}] AS WBValue
        FROM {table_name}
        WHERE [{trial_col}] IN ({placeholders})
        ORDER BY [{trial_col}], [{id_col}]
        """,
        st.trial_ids,
    )
    if not rows:
        return None
    row_titles = ["Intermingling 1", "Intermingling 2", "Intermingling 3"]
    per_trial: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        per_trial[int(r["WBTrialID"])].append(r)
    cells = _empty(3, len(st.trials))
    for c_idx, trial in enumerate(st.trials):
        vals = per_trial.get(trial["ID"], [])
        for i in range(3):
            if i < len(vals):
                rec = vals[i]
                cells[i][c_idx] = (rec.get("WBValue"), CellBinding(table_name, id_col, rec["RecID"], inter_col))
    return LabPivot("water", row_titles, ["onlyDoubles"] * 3, cells)


def build_rapid600(st: SeriesTrials) -> Optional[LabPivot]:
    """Pro Trial höchstens ein Datensatz; bei mehreren gilt der erste."""
    if not st.trial_ids or not table_exists("tblLaborRapid600"):
        return None
    rows = fetch_all(
        f"""
        SELECT
            R.ID         AS RecID,
            R.TrialID    AS TrialID,
            R.SPD        AS SPD,
            R.[SPD Avg]  AS SPD_Avg,
            R.[SPD Dev]  AS SPD_Dev
        FROM tblLaborRapid600 AS R
        WHERE R.TrialID IN ({",".join(["?"] * len(st.trial_ids))})
        ORDER BY R.TrialID, R.ID
        """,
        st.trial_ids,
    )
    if not rows:
        return None
    by_trial: Dict[int, Dict[str, Any]] = {}
    for r in rows:
        tid = int(r["TrialID"])
        if tid not in by_trial:
            by_trial[tid] = r
    row_titles = ["SPD", "SPD Avg", "SPD Dev"]
    cells = _empty(3, len(st.trials))
    for c_idx, trial in enumerate(st.trials):
        rec = by_trial.get(trial["ID"])
        if not rec:
            continue
        rec_id = rec["RecID"]
        cells[0][c_idx] = (rec.get("SPD"), CellBinding("tblLaborRapid600", "ID", rec_id, "SPD"))
        cells[1][c_idx] = (rec.get("SPD_Avg"), CellBinding("tblLaborRapid600", "ID", rec_id, "SPD Avg"))
        cells[2][c_idx] = (rec.get("SPD_Dev"), CellBinding("tblLaborRapid600", "ID", rec_id, "SPD Dev"))
    return LabPivot("rapid600", row_titles, ["onlyDoubles"] * 3, cells)


# --------------------------------------------------------------------------- Itemat Lab / Itemat Plus
# Rows: the values at tension 0 first, then "Stability@t" for every tension t > 0 found in the series.
ITEMAT_ROW_IP0 = 0
ITEMAT_ROW_STAB_START = 2
ITEMAT_PLUS_ROW_IP0 = 0
ITEMAT_PLUS_ROW_OLX0 = 1
ITEMAT_PLUS_ROW_OLS0 = 2
ITEMAT_PLUS_ROW_KLX0 = 3
ITEMAT_PLUS_ROW_KLS0 = 4
ITEMAT_PLUS_ROW_STAB_START = 5


def _itemat_by_trial(rows) -> Tuple[Dict[int, List[Dict[str, Any]]], List[float]]:
    """Records per trial + the sorted tensions > 0 (rounded to 2 decimals)."""
    by_trial: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    tensions_set: set[float] = set()
    for r in rows:
        by_trial[int(r["TrialID"])].append(r)
        try:
            t = float(str(r["Tension"]).replace(",", "."))
        except Exception:
            t = 0.0
        if t != 0.0:
            tensions_set.add(round(t, 2))
    return by_trial, sorted(tensions_set)


def _find_tension_record(trial_list: List[Dict[str, Any]], tension_value: float) -> Optional[Dict[str, Any]]:
    for rr in trial_list:
        try:
            tt = float(str(rr["Tension"]).replace(",", "."))
        except Exception:
            tt = 0.0
        if abs(tt - tension_value) < 1e-6:
            return rr
    return None


def build_itemat(st: SeriesTrials) -> Optional[LabPivot]:
    """Itemat Lab. extra["tensions"] = the tensions > 0 of the Stability rows (in row order)."""
    if not st.trial_ids or not table_exists("tblLaborItematLab"):
        return None

    rows = fetch_all(
        f"""
        SELECT
            IL.ID AS RecID,
            IL.TrialID,
            IL.[Tension (cN/dtex)]     AS Tension,
            IL.[Intermingling Points (FP/m)]     AS IP,
            IL.[Intermingling Points CV (%)]     AS IPCV,
            IL.[Stability (%)]                   AS Stability
        FROM tblLaborItematLab AS IL
        WHERE IL.TrialID IN ({",".join(["?"] * len(st.trial_ids))})
        ORDER BY IL.TrialID, IL.[Tension (cN/dtex)], IL.ID
        """,
        st.trial_ids,
    )
    if not rows:
        return None

    by_trial, tensions_sorted = _itemat_by_trial(rows)
    row_titles: List[str] = [
                                "Intermingling Points (FP/m) @0.0 cN/dtex",
                                "Intermingling Points CV (%) @0.0 cN/dtex",
                            ] + [f"Stability@{t:.1f} cN/dtex" for t in tensions_sorted]

    cells = _empty(len(row_titles), len(st.trials))
    for c_idx, trial in enumerate(st.trials):
        tid = trial["ID"]
        recs = by_trial.get(tid, [])
        r0 = _find_tension_record(recs, 0.0)
        if r0:
            cells[0][c_idx] = (r0.get("IP"), CellBinding("tblLaborItematLab", "ID",
                                                         r0["RecID"], "Intermingling Points (FP/m)"))
            cells[1][c_idx] = (r0.get("IPCV"), CellBinding("tblLaborItematLab", "ID",
                                                           r0["RecID"], "Intermingling Points CV (%)"))
        for idx, tval in enumerate(tensions_sorted, start=ITEMAT_ROW_STAB_START):
            rr = _find_tension_record(recs, tval)
            if rr:
                cells[idx][c_idx] = (rr.get("Stability"), CellBinding("tblLaborItematLab", "ID",
                                                                       rr["RecID"], "Stability (%)"))
    p = LabPivot("itemat", row_titles, ["onlyDoubles"] * len(row_titles), cells)
    p.extra["tensions"] = tensions_sorted
    return p


_ITEMAT_PLUS_AT0 = [   # (SELECT alias, column) of the rows at tension 0, in row order
    ("InterP", "Intermingling Points (FP/m)"),
    ("OLX", "OL X (mm)"),
    ("OLS", "OL S (mm)"),
    ("KLX", "KL X (mm)"),
    ("KLS", "KL S (mm)"),
]


def build_itemat_plus(st: SeriesTrials) -> Optional[LabPivot]:
    """Itemat Plus: IP, OL X/S, KL X/S at tension 0, then Stability@t.
    extra["tensions"] = the tensions > 0 of the Stability rows (in row order)."""
    if not st.trial_ids or not table_exists("tblLaborItematPlus"):
        return None

    rows = fetch_all(
        f"""
        SELECT
            IP.ID AS RecID,
            IP.TrialID,
            IP.[Tension (cN/dtex)]                AS Tension,
            IP.[Intermingling Points (FP/m)]      AS InterP,
            IP.[Intermingling Points CV (%)]      AS InterCV,
            IP.[Stability (%)]                    AS Stability,
            IP.[OL X (mm)]                        AS OLX,
            IP.[OL S (mm)]                        AS OLS,
            IP.[KL X (mm)]                        AS KLX,
            IP.[KL S (mm)]                        AS KLS
        FROM tblLaborItematPlus AS IP
        WHERE IP.TrialID IN ({",".join(["?"] * len(st.trial_ids))})
        ORDER BY IP.TrialID, IP.[Tension (cN/dtex)], IP.ID
        """,
        st.trial_ids,
    )
    if not rows:
        return None

    by_trial, tensions_sorted = _itemat_by_trial(rows)
    # Zeilen: IP@0, OLX@0, OLS@0, KLX@0, KLS@0, dann Stability@t für alle t>0
    row_titles: List[str] = [
                                "Intermingling Points (FP/m) @0.0 cN/dtex",
                                "OL X (mm) @0.0 cN/dtex",
                                "OL S (mm) @0.0 cN/dtex",
                                "KL X (mm) @0.0 cN/dtex",
                                "KL S (mm) @0.0 cN/dtex",
                            ] + [f"Stability@{t:.1f} cN/dtex" for t in tensions_sorted]

    cells = _empty(len(row_titles), len(st.trials))
    for c_idx, trial in enumerate(st.trials):
        tid = trial["ID"]
        recs = by_trial.get(tid, [])
        r0 = _find_tension_record(recs, 0.0)
        if r0:
            for r_idx, (alias, col) in enumerate(_ITEMAT_PLUS_AT0):
                cells[r_idx][c_idx] = (r0.get(alias), CellBinding("tblLaborItematPlus", "ID", r0["RecID"], col))
        # Stability@t für jede Spannung > 0
        for idx, tval in enumerate(tensions_sorted, start=ITEMAT_PLUS_ROW_STAB_START):
            rr = _find_tension_record(recs, tval)
            if rr:
                cells[idx][c_idx] = (rr.get("Stability"), CellBinding("tblLaborItematPlus", "ID",
                                                                       rr["RecID"], "Stability (%)"))
    p = LabPivot("itemat_plus", row_titles, ["onlyDoubles"] * len(row_titles), cells)
    p.extra["tensions"] = tensions_sorted
    return p


def itemat_ip_at_tension(ip0: float, stability: float) -> float:
    """Save step of Itemat Lab and Itemat Plus: IP(t) = IP(0) * Stability(t) / 100,
    written into the record of Stability(t)."""
    return ip0 * (stability / 100.0)


def itemat_plus_cv0(olx: Optional[float], ols: Optional[float], klx: Optional[float],
                    kls: Optional[float]) -> Optional[float]:
    """Save step of Itemat Plus: CV@0 = ((KL S)^2 + (OL S)^2)^0.5 / (KL X + OL X) * 100,
    written into [Intermingling Points CV (%)] of the tension-0 record. None = not computable."""
    if None in (olx, ols, klx, kls):
        return None
    denom = (olx or 0.0) + (klx or 0.0)
    if denom <= 0:
        return None
    return math.sqrt((kls or 0.0) ** 2 + (ols or 0.0) ** 2) / denom * 100


# --------------------------------------------------------------------------- DTYoMat / ATYoMat
_DTYOMAT_FIELDS = [   # (row title, SELECT alias, column)
    ("Intermingling Points per Meter (FP/m)", "FPm", "FP/m"),
    ("Intermingling Points CV (%)", "CV_FP", "CV_FP"),
    ("Average FP Length (mm)", "AvgFP", "AvgFP"),
    ("Standard Deviation FP Length (mm)", "StdDevFP", "StdDevFP"),
    ("Knot Length CV (%)", "CV_KL", "CV_KL"),
    ("Average Knot Length (mm)", "AvgKL", "AvgKL"),
    ("Standard Deviation Knot Length (mm)", "StdDevKL", "StdDevKL"),
    ("Open Length CV (%)", "CV_OL", "CV_OL"),
    ("Average Open Length (mm)", "AvgOL", "AvgOL"),
    ("Standard Deviation Open Length (mm)", "StdDevOL", "StdDevOL"),
    ("A-Knots (%)", "AKnots", "AKnots"),
    ("B-Knots (%)", "BKnots", "BKnots"),
    ("C-Knots (%)", "CKnots", "CKnots"),
]


def build_dtyomat(st: SeriesTrials) -> Optional[LabPivot]:
    """DTYoMat from tblLaborDTYoMat. Pro Trial höchstens ein Datensatz; bei mehreren gilt der erste."""
    if not st.trial_ids or not table_exists("tblLaborDTYoMat"):
        return None

    rows = fetch_all(
        f"""
        SELECT
            D.ID         AS RecID,
            D.TrialID    AS TrialID,
            D.[FP/m]     AS FPm,
            D.CV_FP      AS CV_FP,
            D.AvgFP      AS AvgFP,
            D.StdDevFP   AS StdDevFP,
            D.CV_KL      AS CV_KL,
            D.AvgKL      AS AvgKL,
            D.StdDevKL   AS StdDevKL,
            D.CV_OL      AS CV_OL,
            D.AvgOL      AS AvgOL,
            D.StdDevOL   AS StdDevOL,
            D.AKnots     AS AKnots,
            D.BKnots     AS BKnots,
            D.CKnots     AS CKnots
        FROM tblLaborDTYoMat AS D
        WHERE D.TrialID IN ({",".join(["?"] * len(st.trial_ids))})
        ORDER BY D.TrialID, D.ID
        """,
        st.trial_ids,
    )
    if not rows:
        return None

    # Pro Trial den ersten Datensatz verwenden
    by_trial: Dict[int, Dict[str, Any]] = {}
    for r in rows:
        tid = int(r["TrialID"])
        if tid not in by_trial:
            by_trial[tid] = r

    row_titles = [t for t, _a, _c in _DTYOMAT_FIELDS]
    cells = _empty(len(row_titles), len(st.trials))
    for c_idx, trial in enumerate(st.trials):
        rec = by_trial.get(trial["ID"])
        if not rec:
            continue
        rec_id = rec["RecID"]
        for r_idx, (_title, alias, col) in enumerate(_DTYOMAT_FIELDS):
            cells[r_idx][c_idx] = (rec.get(alias), CellBinding("tblLaborDTYoMat", "ID", rec_id, col))
    return LabPivot("dtyomat", row_titles, ["onlyDoubles"] * len(row_titles), cells)


_ATYOMAT_ROW_TITLES: List[str] = [
    "Laenge (m)", "Global mean (um)", "Kern (um)", "Kern-CV (%)",
    "Difference core vs. mean (%)", "Kern-CV @1m (%)", "Kern-CV @20m (%)",
    "Number of loops", "Frequenz (1/m)", "Ø Abstand (mm)", "Abstand-CV (%)",
    "Hoehe Median (um)", "Height mean (um)", "Hoehe P95 (um)", "Hoehe P99 (um)", "Hoehe Max (um)",
    "Rel. Hoehe Median (%)", "Rel. height mean (%)", "Rel. Hoehe P90 (%)",
    "Rel. Hoehe P95 (%)", "Rel. Hoehe P99 (%)", "Rel. Hoehe Max (%)",
    "Bulk Index (%)", "Kurzhocker Anteil (%)", "Langwelle Anteil (%)",
    "Kurzhocker Dichte (1/m)", "Langwelle Dichte (1/m)",
    "Kurzhocker Hoehe Median (um)", "Kurzhocker Rel. Hoehe Median (%)", "Kurzhocker Bulk-Beitrag (%)",
    "Langwelle Hoehe Median (um)", "Langwelle Rel. Hoehe Median (%)", "Langwelle Bulk-Beitrag (%)",
    "Ellipticity Mittel (%)", "Ellipticity Schlaufen (%)", "Ellipticity Kern (%)",
    "Ellipticity Schlaufe/Kern-Verhaeltnis",
]


def build_atyomat(st: SeriesTrials) -> Optional[LabPivot]:
    """ATYoMat from tblLaborATYoMat: core/loop figures of the ATY analysis
    (ui/yarnscope/aty_core_analysis.py, since 2026-08-13). Pro Trial wird der
    neueste Datensatz verwendet (MAX(ID))."""
    if not st.trial_ids or not table_exists("tblLaborATYoMat"):
        return None

    # lazy: the analysis module pulls in numpy/scipy (Qt-free, but heavy)
    from ui.yarnscope.aty_core_analysis import DB_COLUMN_MAP

    # DB_COLUMN_MAP keys are analyze_trial()'s python field names;
    # ParamsVersion (a string) is metadata, not a numeric row to edit here.
    col_db = [c for k, c in DB_COLUMN_MAP.items() if k != "params_version"]
    row_titles: List[str] = list(_ATYOMAT_ROW_TITLES)
    assert len(row_titles) == len(col_db), "ATYoMat row_titles/col_db out of sync with DB_COLUMN_MAP"

    cols_sql = ", ".join(f"D.{c} AS {c}" for c in col_db)
    rows = fetch_all(
        f"""
        SELECT
            D.ID            AS RecID,
            D.TrialID       AS TrialID,
            {cols_sql}
        FROM tblLaborATYoMat AS D
        INNER JOIN (
            SELECT TrialID, MAX(ID) AS MaxID
            FROM tblLaborATYoMat
            WHERE TrialID IN ({",".join(["?"] * len(st.trial_ids))})
            GROUP BY TrialID
        ) AS Latest ON D.ID = Latest.MaxID
        ORDER BY D.TrialID
        """,
        st.trial_ids,
    )
    if not rows:
        return None

    by_trial: Dict[int, Dict[str, Any]] = {}
    for r in rows:
        tid = int(r["TrialID"])
        if tid not in by_trial:
            by_trial[tid] = r

    cells = _empty(len(row_titles), len(st.trials))
    for c_idx, trial in enumerate(st.trials):
        rec = by_trial.get(trial["ID"])
        if not rec:
            continue
        rec_id = rec["RecID"]
        for r_idx, col_name in enumerate(col_db):
            cells[r_idx][c_idx] = (rec.get(col_name), CellBinding("tblLaborATYoMat", "ID", rec_id, col_name))
    return LabPivot("atyomat", row_titles, ["onlyDoubles"] * len(row_titles), cells)


@dataclass(frozen=True)
class LabTab:
    key: str
    title: str             # tab title on the desktop
    lab_source: str        # retest flags (db/retest_flags.py)
    build: Callable[[SeriesTrials], Optional[LabPivot]]


# in desktop tab order (ShowExperimentScreen._build_lab_tabs). Jet Air Consumption
# comes between Titer and Statimat M on the desktop (JET_AIR_TAB_INDEX) but has
# other columns - see build_jet_air().
LAB_TABS: List[LabTab] = [
    LabTab("titer", "Titer", "Titer", build_titer),
    LabTab("stat", "Statimat M", "Statimat", build_stat),
    LabTab("stat_ds", "Statimat DS", "StatimatDS", build_stat_ds),
    LabTab("water", "Waterbath", "Waterbath", build_water),
    LabTab("ekb", "EKB", "EKB", build_ekb),
    LabTab("hot_air_shrinkage", "Hot Air Shrinkage", "HotAirShrinkage", build_hot_air_shrinkage),
    LabTab("hot_water_shrinkage", "Hot Water Shrinkage", "HotWaterShrinkage", build_hot_water_shrinkage),
    LabTab("aty_shrinkage", "ATY Shrinkage", "ATYShrinkage", build_aty_shrinkage),
    LabTab("rapid600", "Rapid 600", "Rapid600", build_rapid600),
    LabTab("itemat", "Itemat Lab", "ItematLab", build_itemat),
    LabTab("itemat_plus", "Itemat Plus", "ItematPlus", build_itemat_plus),
    LabTab("dtyomat", "DTYoMat", "DTYoMat", build_dtyomat),
    LabTab("atyomat", "ATYoMat", "ATYoMat", build_atyomat),
]


# --------------------------------------------------------------------------- Jet Air Consumption
JET_AIR_TABLE = "tblLaborJetAirConsumption"
JET_AIR_TITLE = "Jet Air Consumption"
JET_AIR_TAB_INDEX = 1        # desktop order: right after Titer, before Statimat M
# 1 Nm3/h = 1000 l / 60 min = 16.6667 l/min
LMIN_PER_NM3H = 1000.0 / 60.0
JET_AIR_UNITS = {"Nm3h": "Nm³/h", "lmin": "l/min"}   # unit key -> label of the desktop unit switch


@dataclass
class JetAirTables:
    """Tab "Jet Air Consumption": three grids with the same rows and columns, per
    series (tblLaborJetAirConsumption.TrialSeriesID, not per trial). Rows = physical
    jets (JetID + JetPlate), columns = pressure steps - the three LabPivots carry
    col_titles ("2 bar", ...). No jet info rows on top, no retest flags."""
    jets: List[Tuple[int, str]]     # (JetID, plate) per row; plate "" = none
    pressures: List[float]          # bar, per column
    unit: str                       # "Nm3h" or "lmin" = display unit of `consumption`
    consumption: LabPivot           # key "jet_air": Air Consumption, values "%.2f" in `unit`
    atm: LabPivot                   # key "jet_air_atm": Atmospheric Pressure (mbar)
    temp: LabPivot                  # key "jet_air_temp": Air Temperature (°C)


def build_jet_air(series_pk: Any, unit: str = "Nm3h") -> Optional[JetAirTables]:
    """Reiter 'Jet Air Consumption': Zeilen = physische Duesen (JetID + JetPlate),
    Spalten = Druckstufen. Air Consumption is stored in Nm3/h; with unit "lmin" the
    values are shown in l/min and consumption.extra["unit_scale"] / ["unit_field"]
    tell how to store an entered value (stored = entered / unit_scale, only for
    cells of that field - PivotEditModel.set_unit_scale). Eine Series-gemeinsame
    Druck-Liste wird mit allen physischen Duesen der Series gekreuzt (siehe
    _save_jet_air_consumption_rows in screen_create_experiment.py)."""
    table = JET_AIR_TABLE
    series_id = series_pk
    if not table_exists(table) or not series_id:
        return None

    rows = fetch_all(
        f"SELECT [ID], [JetID], [JetPlate], [AirPressure], [AirConsumption], "
        f"[AtmosphericPressure], [AirTemperature] "
        f"FROM {table} WHERE [TrialSeriesID] = ?",
        [series_id],
    )
    if not rows:
        return None

    # Jet-Namen nachladen (gleiche Quelle wie jet_info_rows)
    jet_ids = sorted({int(r["JetID"]) for r in rows if r.get("JetID") is not None})
    jet_name_map: Dict[int, str] = {}
    try:
        if jet_ids and table_exists("tblDTYJets"):
            ph = ",".join(["?"] * len(jet_ids))
            for jr in fetch_all(
                    f"SELECT [ID], [Jet] AS JName FROM tblDTYJets WHERE [ID] IN ({ph})", jet_ids):
                jet_name_map[int(jr["ID"])] = str(jr.get("JName") or "")
    except Exception:
        pass

    def _plate_key(p):
        return "" if p is None else str(p)

    physical_jets = sorted(
        {(int(r["JetID"]), _plate_key(r.get("JetPlate")))
         for r in rows if r.get("JetID") is not None},
        key=lambda t: (jet_name_map.get(t[0], ""), t[1]),
    )
    pressures = sorted({float(r["AirPressure"]) for r in rows if r.get("AirPressure") is not None})

    if not physical_jets or not pressures:
        return None

    row_titles = []
    for jid, plate in physical_jets:
        jname = jet_name_map.get(jid, f"Jet {jid}")
        row_titles.append(f"{jname} / Plate {plate}" if plate else jname)

    col_titles = [f"{p:g} bar" for p in pressures]

    by_key: Dict[Tuple[int, str, float], dict] = {}
    for r in rows:
        if r.get("JetID") is None or r.get("AirPressure") is None:
            continue
        key = (int(r["JetID"]), _plate_key(r.get("JetPlate")), round(float(r["AirPressure"]), 6))
        by_key[key] = r

    use_lmin = (unit == "lmin")

    def _grid(field_name: str, value_of) -> List[List[Tuple[Any, Optional[CellBinding]]]]:
        cells = _empty(len(row_titles), len(col_titles))
        for r_idx, (jid, plate) in enumerate(physical_jets):
            for c_idx, p in enumerate(pressures):
                rec = by_key.get((jid, plate, round(p, 6)))
                if rec:
                    cells[r_idx][c_idx] = (value_of(rec), CellBinding(table, "ID", rec["ID"], field_name))
        return cells

    def _consumption(rec):
        val = rec.get("AirConsumption")
        disp = None
        if val is not None:
            v = float(val) * LMIN_PER_NM3H if use_lmin else float(val)
            disp = f"{v:.2f}"
        return disp

    def validators():
        return ["onlyDoubles"] * len(row_titles)   # one list per grid, as before

    consumption = LabPivot("jet_air", row_titles, validators(), _grid("AirConsumption", _consumption),
                           col_titles=col_titles)
    if use_lmin:
        consumption.extra["unit_scale"] = LMIN_PER_NM3H
        consumption.extra["unit_field"] = "AirConsumption"
    atm = LabPivot("jet_air_atm", row_titles, validators(),
                   _grid("AtmosphericPressure", lambda rec: rec.get("AtmosphericPressure")),
                   col_titles=col_titles)
    temp = LabPivot("jet_air_temp", row_titles, validators(),
                    _grid("AirTemperature", lambda rec: rec.get("AirTemperature")),
                    col_titles=col_titles)
    return JetAirTables(jets=physical_jets, pressures=pressures, unit="lmin" if use_lmin else "Nm3h",
                        consumption=consumption, atm=atm, temp=temp)


# --------------------------------------------------------------------------- presentation rules
def cv_limit_alert(row_title: str, raw: Any) -> bool:
    """Elongation CV / Tenacity CV >= 10 -> red + bold (PivotEditModel.data)."""
    if "Elongation CV" not in row_title and "Tenacity CV" not in row_title:
        return False
    try:
        fval = float(str(raw).replace(",", ".")) if raw not in (None, "") else None
    except Exception:
        return False
    return fval is not None and fval >= 10.0


def apply_titer_to_stat_ds(titer: Optional[LabPivot], stat_ds: Optional[LabPivot]) -> None:
    """Trials whose titer is out of tolerance: Tenacity (data row 2) of Statimat DS orange
    (desktop: ShowExperimentScreen._apply_titer_alert_to_stat_ds)."""
    if titer is None or stat_ds is None:
        return
    for c_idx in titer.extra.get("out_of_tolerance", ()):
        stat_ds.alerts.setdefault((2, c_idx), "orange")


# --------------------------------------------------------------------------- series header
def series_header(series_id: Any) -> Optional[Dict[str, Any]]:
    """Experiment + series facts for the head of Show Experiment (web app)."""
    rows = fetch_all(
        """
        SELECT e.[ID] AS ExperimentPK, e.[Experiment ID] AS ExperimentID,
               s.[ID] AS SeriesID, s.[SeriesName] AS SeriesName, s.[CreationDate] AS CreationDate,
               s.[BacklogStatusID] AS StatusID, s.[Notes] AS Notes,
               m.[ID] AS MachineID, m.[Maschine] AS Machine, m.[Maschinentyp] AS MachineType,
               u.[Username] AS Owner
        FROM ((tblTrialSeries AS s
            INNER JOIN tblExperimente AS e ON e.[ID] = s.[ExperimentID])
            LEFT JOIN tblMaschine AS m ON m.[ID] = s.[MachineID])
            LEFT JOIN tblUser AS u ON u.[ID] = s.[BacklogOwner]
        WHERE s.[ID] = ?
        """,
        [series_id],
    )
    return rows[0] if rows else None
