"""aty_service.py - ATY YarnScope without Qt (desktop tab + web app).

Everything the ATY YarnScope tab (ui/aty_yarnscope_tab.py) computes or writes,
without widgets/matplotlib: TDMS files of a series, the single-trial analysis
(thick places, histograms, Garnspiegel/Fabric/Knitted geometry), the
"Compare" sub tab (core analysis, tables, radar, histograms, signal zoom),
saving to tblLaborATYoMat and the batch analysis. The desktop draws with
matplotlib/QPainter, the web (tripplet_web backend/app/yarnscope_aty.py) with
Plotly/canvas - both from the same data.

Two analyses (as in the desktop since 2026-08-13):
- ``analyse_file`` = thick_spot_analysis (global mean as core) -> the
  Distribution/Garnspiegel/Fabric/Knitted views and the metrics line;
- ``aty_core_analysis.analyze_trial`` (rolling core baseline) -> Compare and
  the values written to tblLaborATYoMat (Save, Batch).
"""
from __future__ import annotations

import math
import os
from datetime import datetime as _dt
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from ui.yarnscope import thickness_classes as tc

ENV_TDMS_DIR = "TRIPPLET_YARNSCOPE_ATY_DIR"
DEFAULT_TDMS_DIR = r"H:\Technik\TrippleT\ATYtdms"

# Distribution sub tab: (feature key, label) as in the desktop combo box
HIST_FEATURES = [("F01_length_mm", "Laenge [mm]"), ("F02_height_um", "Hoehe [um]"),
                 ("F03_area_um_mm", "Flaeche [um*mm]")]
HIST_COLOURS = {"bin1": "#e07b00", "bin2": "#0e8a8a"}
# Defaults of the control panel (desktop spin boxes: value, min, max)
CONTROLS = {"start_m": (0.0, 0.0, 9999.0), "turns": (10, 1, 20), "gap": (2.0, 1.0, 10.0),
            "bands": (250, 10, 2500), "rows": (50, 10, 250)}
# Compare: fixed categorical palette (desktop _CMP_COLORS)
COMPARE_COLOURS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
                   "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
ZOOM_WINDOW_MM = 40.0
SPACING_BINS = np.arange(0, 16.5, 0.5)
RELHEIGHT_BINS = np.arange(0, 105, 5)
# Batch result columns (desktop screen_aty_batch: header, DB column, decimals)
BATCH_COLUMNS = [("Length [m]", "LengthM", 1), ("Core [µm]", "CoreMeanUm", 1),
                 ("Bulk Index [%]", "BulkIndexPct", 1), ("Freq [1/m]", "DensityPerM", 1),
                 ("Bin1 % (Kurzhocker)", "Bin1Pct", 1), ("Core CV [%]", "CoreCVPct", 2)]


# ===========================================================================
# TDMS files
# ===========================================================================

def tdms_base() -> Path:
    """Folder with the ATY TDMS files (env TRIPPLET_YARNSCOPE_ATY_DIR, else the H: share)."""
    return Path(os.environ.get(ENV_TDMS_DIR) or DEFAULT_TDMS_DIR)


def series_has_tdms(series_id: int, base=None) -> bool:
    """True if the folder holds a ``{series_id}_*.tdms`` - the tab "YarnScope ATY" is shown then."""
    base = Path(base) if base is not None else tdms_base()
    if not base.exists():
        return False
    prefix = f"{series_id}_"
    try:
        for f in base.iterdir():
            if f.suffix.lower() == ".tdms" and f.stem.startswith(prefix):
                return True
    except Exception:
        pass
    return False


def find_tdms(series_id: int, versuch_no: int, base=None):
    """TDMS file of one trial (``{series}_{vno}_*.tdms``) or None."""
    base = Path(base) if base is not None else tdms_base()
    if not base.exists():
        return None
    prefix = f"{series_id}_{versuch_no}_"
    try:
        for f in base.iterdir():
            if f.suffix.lower() == ".tdms" and f.stem.startswith(prefix):
                return f
    except Exception:
        pass
    return None


# "Analysed" = the row holds analysis values, not just a Timestamp (new trials get an
# empty ATYoMat row; a Timestamp alone marked trials without TDMS as analysed).
# save_db_row() always writes ParamsVersion; CoreMeanUm keeps older rows counted.
ANALYSED_SQL = "Timestamp IS NOT NULL AND (ParamsVersion IS NOT NULL OR CoreMeanUm IS NOT NULL)"


def is_trial_analysed(trial_id) -> bool:
    """True if tblLaborATYoMat holds a saved analysis (ANALYSED_SQL) - desktop ✅."""
    from db.connection import fetch_all
    try:
        return bool(fetch_all(f"SELECT 1 FROM tblLaborATYoMat WHERE TrialID=? AND {ANALYSED_SQL}",
                              (trial_id,)))
    except Exception:
        return False


def analysed_trial_ids(trial_ids) -> set:
    """The given trial ids with a saved analysis (one query)."""
    from db.connection import fetch_all
    ids = [int(t) for t in trial_ids if t is not None]
    if not ids:
        return set()
    marks = ",".join("?" * len(ids))
    try:
        rows = fetch_all(f"SELECT DISTINCT TrialID FROM tblLaborATYoMat "
                         f"WHERE {ANALYSED_SQL} AND TrialID IN ({marks})", ids)
    except Exception:
        return set()
    return {int(r["TrialID"]) for r in rows}


def trial_files(series_id, trials, reference_ids=(), with_analysed: bool = False, base=None) -> list:
    """Trial list of the tab: [{trial_id, vno, tdms (Path|None)[, analysed]}] in
    trial order, reference samples skipped (they never have a file)."""
    out = []
    for t in trials:
        tl = {str(k).lower(): v for k, v in t.items()}
        tid = tl.get("id")
        if tid is not None and int(tid) in reference_ids:
            continue
        vno = int(tl.get("versuchsnummer") or 0)
        tdms = find_tdms(series_id, vno, base) if series_id else None
        out.append({"trial_id": tid, "vno": vno, "tdms": tdms})
    if with_analysed:
        done = analysed_trial_ids([e["trial_id"] for e in out])
        for e in out:
            e["analysed"] = e["trial_id"] is not None and int(e["trial_id"]) in done
    return out


def trial_label(vno) -> str:
    return f"V{vno:03d}" if isinstance(vno, int) else "?"


# ===========================================================================
# Single trial (thick-spot analysis + views)
# ===========================================================================

def read_signal(path):
    """(arr_mm, mm_per_point, ellipticity_pct) of a TDMS file; arr None if no signal."""
    from ui.yarnscope.dty_tdms_reader import read_aty_signal, read_step_mm_from_tdms
    arr, ell = read_aty_signal(str(path))
    mm_pp = float(read_step_mm_from_tdms(str(path)) or 0.25)
    if arr is None or len(arr) == 0:
        return None, mm_pp, ell
    return arr, mm_pp, ell


def analyse_arrays(arr, mm_pp: float, ell=None) -> Dict[str, Any]:
    """Thick-spot analysis of a signal = desktop "Analysieren".

    Returns {arr, mm_pp, ell, spots, db_vals (metrics line), hists (Distribution)}."""
    from ui.yarnscope.thick_spot_analysis import detect_thick_spots, compute_db_values, compute_histograms
    spots = detect_thick_spots(arr, mm_pp)
    total_mm = float(len(arr) * mm_pp)
    return {"arr": arr, "mm_pp": float(mm_pp), "ell": ell, "spots": spots,
            "db_vals": compute_db_values(spots, total_mm), "hists": compute_histograms(spots, total_mm)}


def analyse_file(path) -> Dict[str, Any]:
    """read_signal + analyse_arrays; ValueError if the file has no signal."""
    arr, mm_pp, ell = read_signal(path)
    if arr is None:
        raise ValueError("No signal in the TDMS file.")
    return analyse_arrays(arr, mm_pp, ell)


def fmt_metric(v, dec: int = 1) -> str:
    """Number as in the desktop metrics line (thousands with ', '-' if missing)."""
    try:
        vv = float(v)
        return f"{vv:,.{dec}f}".replace(",", "'") if math.isfinite(vv) else "-"
    except Exception:
        return "-"


# (label, db_vals key, decimals, unit) - the two lines of the desktop metrics label
METRICS = [
    [("Length", "TotalLen_m", 1, " m"), ("Kurzhocker", "N_B1", 1, " /100m"), ("Langwelle", "N_B2", 1, " /100m")],
    [("Ø Len B1", "AvgLen_B1", 2, " mm"), ("Ø Len B2", "AvgLen_B2", 2, " mm"),
     ("Ø Hgt B1", "AvgHeight_B1", 1, " um"), ("Ø Hgt B2", "AvgHeight_B2", 1, " um")],
]


def metrics_text(db_vals: dict) -> str:
    """The two-line metrics text below the sub tabs."""
    return "\n".join("  |  ".join(f"{lb}: {fmt_metric(db_vals.get(k), d)}{u}" for lb, k, d, u in line)
                     for line in METRICS)


def metrics_json(db_vals: dict) -> list:
    return [[{"label": lb, "key": k, "decimals": d, "unit": u.strip(), "value": db_vals.get(k),
              "text": fmt_metric(db_vals.get(k), d)} for lb, k, d, u in line] for line in METRICS]


def hist_fmt(v) -> str:
    """Number format of the Distribution table."""
    try:
        vv = float(v)
        if not np.isfinite(vv):
            return "-"
        if abs(vv) >= 10000:
            return f"{vv:,.0f}".replace(",", "'")
        elif abs(vv) >= 100:
            return f"{vv:.1f}"
        elif abs(vv) >= 1:
            return f"{vv:.2f}"
        else:
            return f"{vv:.4f}"
    except Exception:
        return "-"


def histogram_view(hists: dict, feature: str) -> Optional[dict]:
    """Distribution sub tab for one feature: bar data (centres, width = 0.42 x bin)
    and the 20 table rows [interval, bin 1 /100m, bin 2 /100m]."""
    if not hists or feature not in hists:
        return None
    h = hists[feature]
    edges = np.asarray(h["edges"], dtype=float)
    c1 = np.asarray(h["counts_1"], dtype=float)
    c2 = np.asarray(h["counts_2"], dtype=float)
    width = (edges[1] - edges[0]) * 0.42
    centers = 0.5 * (edges[:-1] + edges[1:])
    rows = [[f"{hist_fmt(edges[i])} – {hist_fmt(edges[i + 1])}", hist_fmt(c1[i]), hist_fmt(c2[i])]
            for i in range(min(20, len(c1)))]
    return {"feature": feature, "label": dict(HIST_FEATURES).get(feature, feature),
            "edges": edges, "centers": centers, "width": width, "counts_1": c1, "counts_2": c2,
            "rows": rows, "colours": HIST_COLOURS}


def window(arr, spots, mm_pp: float, start_m: float = 0.0, num_turns: int = 10):
    """Garnspiegel window from ``start_m``: num_turns x 200 mm (desktop _aty_get_window).

    Returns (arr_view, spots_view, row_spacing_ref = max of the whole signal);
    arr_view None if empty."""
    start_idx = max(0, min(int(start_m * 1000.0 / mm_pp), len(arr) - 1))
    needed = int(num_turns * 200.0 / mm_pp)
    arr_view = arr[start_idx:start_idx + needed]
    if len(arr_view) == 0:
        return None, [], float(np.max(arr))
    spots_view = []
    for sp in (spots or []):
        s = int(sp["start_idx"]) - start_idx
        e = s + int(sp["n_pts"])
        if e <= 0 or s >= len(arr_view):
            continue
        sp2 = dict(sp)
        sp2["start_idx"] = max(0, s)
        sp2["n_pts"] = min(e, len(arr_view)) - sp2["start_idx"]
        if sp2["n_pts"] > 0:
            spots_view.append(sp2)
    return arr_view, spots_view, float(np.max(arr))


def garnspiegel_view(entry: dict, start_m: float = 0.0, turns: int = 10, gap: float = 2.0) -> Optional[dict]:
    """Garnspiegel of an analysed trial (desktop: GarnCanvas.plot_garnspiegel on the window)."""
    arr_view, _sp, ref = window(entry["arr"], entry.get("spots"), entry["mm_pp"], start_m, turns)
    if arr_view is None or len(arr_view) == 0:
        return None
    return tc.garnspiegel_layout(arr_view, gap_factor=gap, show_colors=True,
                                 row_spacing_ref=ref, num_turns=turns)


def garnspiegel_json(lay: Optional[dict]) -> Optional[dict]:
    """For the web: per row base, half (= signal / 2, one value per sample at x_mm)
    and spans [[s, e, key]] (e inclusive) - the browser applies colours/visibility."""
    if lay is None:
        return None
    return {"rows": [{"base": b, "half": (seg / 2.0), "spans": [list(s) for s in sp]}
                     for seg, b, sp in zip(lay["segments"], lay["bases"], lay["spans"])],
            "x_mm": lay["x_mm"], "mm_step": lay["mm_step"], "xlim": lay["xlim"], "ylim": lay["ylim"],
            "alpha": 0.9}


def fabric_view(entry: dict, n_bands: int = 250) -> dict:
    spans, seg_mm = tc.fabric_spans(entry["arr"], entry["mm_pp"], int(n_bands))
    return {"bands": spans, "seg_mm": seg_mm}


def knitted_view(entry: dict, n_rows: int = 50) -> dict:
    return {"rows": tc.knitted_spans(entry["arr"], entry["mm_pp"], int(n_rows)),
            "x_range_mm": [0.0, tc.KNITTED_DISPLAY_MM], "row_len_mm": tc.KNITTED_ROW_LEN_MM}


# ===========================================================================
# Compare (core analysis)
# ===========================================================================

def core_analysis(arr, mm_pp: float, ell=None) -> Dict[str, Any]:
    from ui.yarnscope.aty_core_analysis import analyze_trial
    return analyze_trial(arr, float(mm_pp), ellipticity_pct=ell)


def _fmt(v, dec: int = 1) -> str:
    try:
        vv = float(v)
        return f"{vv:.{dec}f}" if math.isfinite(vv) else "–"
    except Exception:
        return "–"


COMPARE_TABLE_HEADERS = [
    ["Trial", "Global Mean [µm]", "Core [µm]", "Δ [%]", "Core CV [%]",
     "Freq [1/m]", "Spacing CV [%]", "Height median [µm]", "Height median rel. [%]"],
    ["Trial", "Bulk Index [%]", "Garnspiegel CV [%]", "Bin1 % (Kurzhocker)", "Bin2 % (Langwelle)",
     "Bin1 [1/m]", "Bin2 [1/m]", "Core CV @1m [%]", "Core CV @20m [%]", "Rel. height P99 [%]",
     "Rel. height max [%]"],
    ["Trial", "Kurzhocker height med. [µm]", "Kurzhocker height rel. [%]", "Kurzhocker bulk contrib. [%]",
     "Langwelle height med. [µm]", "Langwelle height rel. [%]", "Langwelle bulk contrib. [%]"],
]


def compare_table_values(vno, r: dict, garnspiegel_cv=None) -> List[List[str]]:
    """Cell texts of the three Compare tables for one trial."""
    lb = trial_label(vno)
    t1 = [lb, _fmt(r["global_mean_um"]), _fmt(r["core_mean_um"]), _fmt(r["delta_pct"]),
          _fmt(r["core_cv_pct"], 2), _fmt(r["density_per_m"]), _fmt(r["spacing_cv_pct"]),
          _fmt(r["height_median_um"]), _fmt(r["rel_height_median_pct"])]
    t2 = [lb, _fmt(r["bulk_index_pct"]), (_fmt(garnspiegel_cv) if garnspiegel_cv is not None else "–"),
          _fmt(r["bin1_pct"]), _fmt(r["bin2_pct"]),
          _fmt(r["bin1_density_per_m"]), _fmt(r["bin2_density_per_m"]),
          _fmt(r["core_cv_short_pct"]), _fmt(r["core_cv_long_pct"]),
          _fmt(r["rel_height_p99_pct"]), _fmt(r["rel_height_max_pct"])]
    t3 = [lb, _fmt(r["bin1_height_median_um"]), _fmt(r["bin1_rel_height_median_pct"]), _fmt(r["bin1_bulk_pct"]),
          _fmt(r["bin2_height_median_um"]), _fmt(r["bin2_rel_height_median_pct"]), _fmt(r["bin2_bulk_pct"])]
    return [t1, t2, t3]


def radar_bands(scores: Dict[str, float]) -> Dict[str, int]:
    """Word band (0-4) per axis as used by aty_core_analysis.describe_yarn()."""
    from ui.yarnscope.aty_core_analysis import _band, RADAR_AXES
    return {a: _band(scores.get(a, float("nan"))) for a in RADAR_AXES}


def radar_entry(vno, r: dict) -> dict:
    """Radar polygon + sentence of one trial: {label, scores, values (NaN -> 0),
    sentence, bands, score_line}."""
    from ui.yarnscope.aty_core_analysis import (compute_radar_scores, describe_yarn,
                                                RADAR_AXES, RADAR_LABELS)
    scores = compute_radar_scores(r)
    return {
        "label": trial_label(vno), "scores": scores,
        "values": [scores[a] if math.isfinite(scores[a]) else 0.0 for a in RADAR_AXES],
        "sentence": describe_yarn(scores), "bands": radar_bands(scores),
        "score_line": " · ".join(f"{RADAR_LABELS[a]} {(f'{scores[a]:.1f}' if math.isfinite(scores[a]) else '–')}"
                                 for a in RADAR_AXES),
    }


def compare_histograms(results) -> Dict[str, list]:
    """Spacing / relative height histograms of the Compare tab: per trial
    (label, colour, bin edges, % of loops per bin); ``results`` =
    [(vno, core stats, ...)] in display order."""
    out = {"spacing": [], "relheight": []}
    for i, item in enumerate(results):
        vno, r = item[0], item[1]
        color = COMPARE_COLOURS[i % len(COMPARE_COLOURS)]
        label = trial_label(vno)
        for key, field, bins in (("spacing", "spacing_mm", SPACING_BINS),
                                 ("relheight", "rel_height_pct", RELHEIGHT_BINS)):
            vals = r.get(field)
            if vals is not None and len(vals):
                w = np.full(len(vals), 100.0 / len(vals))
                counts, _e = np.histogram(vals, bins=bins, weights=w)
                out[key].append((label, color, bins, counts))
    return out


def zoom_view(arr, mm_pp: float, r: dict, start_mm: float, window_mm: float = ZOOM_WINDOW_MM) -> dict:
    """"Signal & core" card: raw signal + core baseline (mm) + old global mean line."""
    from ui.yarnscope.aty_core_analysis import get_zoom_segment
    pos_mm, raw_mm, base_mm = get_zoom_segment(arr, mm_pp, start_mm, window_mm)
    return {"pos_mm": pos_mm, "raw_mm": raw_mm, "base_mm": base_mm,
            "global_mean_mm": r["global_mean_um"] / 1000.0, "start_m": start_mm / 1000.0}


def garnspiegel_cv_by_vno(series_id) -> dict:
    """{Versuchsnummer: CVPct} from the photo-based Garnspiegel analysis
    (tblTrialSeriesImageAnalysis); {} if the table is missing. The newest
    analysis of a trial wins."""
    from db.connection import fetch_all, table_exists
    if series_id is None or not table_exists("tblTrialSeriesImageAnalysis"):
        return {}
    try:
        from ui.yarnscope.garnspiegel_analysis import parse_versuchsnummer
        rows = fetch_all(
            "SELECT img.OriginalFilename, a.CVPct, a.Timestamp "
            "FROM tblTrialSeriesImageAnalysis a "
            "JOIN tblTrialSeriesImage img ON img.ID = a.TrialSeriesImageID "
            "WHERE img.TrialSeriesID = ? AND a.Status = 'ok' "
            "ORDER BY a.Timestamp ASC",
            [series_id],
        )
        result = {}
        for r in rows:
            vno = parse_versuchsnummer(r.get("OriginalFilename") or "")
            if vno is not None and r.get("CVPct") is not None:
                result[vno] = float(r["CVPct"])
        return result
    except Exception:
        return {}


def compare_json(results, series_id=None, zoom_start_mm: float = 0.0, garnspiegel_cv=None) -> dict:
    """Everything of the Compare sub tab for the web. ``results`` =
    [(vno, core stats, arr, mm_pp)] sorted like the desktop (by trial number)."""
    from ui.yarnscope.aty_core_analysis import RADAR_AXES, RADAR_LABELS
    cv = garnspiegel_cv if garnspiegel_cv is not None else garnspiegel_cv_by_vno(series_id)
    tables = [[], [], []]
    trials = []
    for i, (vno, r, arr, mm_pp) in enumerate(results):
        for k, vals in enumerate(compare_table_values(vno, r, cv.get(vno))):
            tables[k].append(vals)
        z = zoom_view(arr, mm_pp, r, zoom_start_mm)
        trials.append({"label": trial_label(vno), "vno": vno,
                       "colour": COMPARE_COLOURS[i % len(COMPARE_COLOURS)],
                       "radar": radar_entry(vno, r), "zoom": z})
    hists = compare_histograms(results)
    return {
        "trials": trials,
        "tables": [{"headers": COMPARE_TABLE_HEADERS[k], "rows": tables[k]} for k in range(3)],
        "radar_axes": [{"key": a, "label": RADAR_LABELS[a]} for a in RADAR_AXES],
        "hists": {k: [{"label": lb, "colour": c, "edges": e, "pct": v} for lb, c, e, v in hs]
                  for k, hs in hists.items()},
        "zoom_window_mm": ZOOM_WINDOW_MM,
    }


# ===========================================================================
# Save / batch (core analysis -> tblLaborATYoMat)
# ===========================================================================

def core_db_row(arr, mm_pp: float, ell=None) -> Dict[str, Any]:
    """Core analysis as {tblLaborATYoMat column: value} (what Save / Batch write)."""
    from ui.yarnscope.aty_core_analysis import to_db_row
    return to_db_row(core_analysis(arr, mm_pp, ell))


def analyse_core_file(path) -> Dict[str, Any]:
    """Batch step: read the TDMS + core analysis -> DB row values."""
    arr, mm_pp, ell = read_signal(path)
    if arr is None:
        raise ValueError("No signal in the TDMS file.")
    if mm_pp is None or mm_pp <= 0:
        mm_pp = 0.25
    return core_db_row(arr, float(mm_pp), ell)


def save_db_row(trial_id: int, db_vals: Dict[str, Any], user: Optional[dict] = None) -> bool:
    """Writes ATY results into tblLaborATYoMat (UPDATE, else INSERT); True on success.

    GlobalID identifies this one row across merges: new on INSERT, on UPDATE
    only set if still empty (COALESCE) - never overwritten. UserID = the
    logged-in user (``user`` or app_meta.current_user). NaN/inf -> NULL
    (mysql-connector would send a bare ``nan``). (Moved from
    screen_aty_batch._save_aty_to_db.)
    """
    from db.connection import fetch_all, execute, new_global_id
    from ui.yarnscope.aty_core_analysis import DB_COLUMNS

    def _v(key):
        v = db_vals.get(key)
        if key == "ParamsVersion":  # only non-numeric column -- keep as string
            return str(v) if v is not None else None
        try:
            f = float(v) if v is not None else None
        except Exception:
            return None
        if f is not None and not np.isfinite(f):
            return None
        return f

    if user is None:
        import app_meta
        user = getattr(app_meta, "current_user", {}) or {}
    ts = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
    params = [_v(c) for c in DB_COLUMNS]
    user_id = (user or {}).get("id")

    try:
        exists = bool(fetch_all("SELECT 1 FROM tblLaborATYoMat WHERE TrialID = ?", (trial_id,)))
    except Exception:
        exists = False

    try:
        if exists:
            set_parts = [f"{c}=?" for c in DB_COLUMNS]
            sql = (f"UPDATE tblLaborATYoMat SET {', '.join(set_parts)}, "
                   f"Timestamp=?, UserID=?, GlobalID=COALESCE(GlobalID, ?) WHERE TrialID=?")
            execute(sql, params + [ts, user_id, new_global_id(), trial_id])
        else:
            cols_str = ", ".join(DB_COLUMNS)
            ph = ", ".join(["?"] * len(DB_COLUMNS))
            sql = (f"INSERT INTO tblLaborATYoMat (TrialID, GlobalID, {cols_str}, Timestamp, UserID) "
                   f"VALUES (?, ?, {ph}, ?, ?)")
            execute(sql, [trial_id, new_global_id()] + params + [ts, user_id])
        return True
    except Exception as e:
        print(f"[ATY Batch] DB-Fehler TrialID={trial_id}: {e}")
        return False


def save_trial(trial_id: int, arr, mm_pp: float, ell=None, user: Optional[dict] = None) -> bool:
    """Desktop "Save to DB": core analysis of the loaded signal, then save_db_row()."""
    if arr is None:
        return False
    return save_db_row(trial_id, core_db_row(arr, float(mm_pp), ell), user)


# ===========================================================================
# JSON
# ===========================================================================

def jsonable(obj):
    """numpy -> Python, NaN/inf -> None, Path -> str (same as dty_service.jsonable)."""
    from ui.yarnscope.dty_service import jsonable as _j
    return _j(obj)
