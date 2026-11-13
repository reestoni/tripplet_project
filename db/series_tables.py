"""series_tables.py - the data behind the Show Experiment tabs, without Qt.

Moved out of ui/screen_show_experiment.py (2026-11-13) so that the desktop
screen and the web app (tripplet_web) show the same cells. The desktop turns
a LabPivot into a PivotEditModel (ShowExperimentScreen._model_from_pivot);
the web app sends it as JSON. Queries and cell rules are unchanged - only
moved. Verified cell by cell (all roles) against the desktop on dev_local.

So far: trial columns, the jet info rows on top of the lab tabs, and the lab
tabs Titer, Statimat M, Statimat DS, Waterbath, EKB, Hot Air / Hot Water /
ATY Shrinkage, Rapid 600. Machine Data, Itemat, DTYoMat, ATYoMat and Jet Air
still build inside the screen.
"""
from __future__ import annotations

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
    """One lab tab: rows = measurements, columns = trials (same order as SeriesTrials)."""
    key: str                                   # "titer", "stat", ...
    row_titles: List[str]
    validators: List[Optional[str]]
    cells: List[List[Tuple[Any, Optional[CellBinding]]]]   # [row][col] = (value, binding)
    alerts: Dict[Tuple[int, int], str] = field(default_factory=dict)   # (data row, col) -> "red"/"orange"
    extra: Dict[str, Any] = field(default_factory=dict)


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


@dataclass(frozen=True)
class LabTab:
    key: str
    title: str             # tab title on the desktop
    lab_source: str        # retest flags (db/retest_flags.py)
    build: Callable[[SeriesTrials], Optional[LabPivot]]


# in desktop tab order (ShowExperimentScreen._build_lab_tabs) - only the extracted ones
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
]


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
