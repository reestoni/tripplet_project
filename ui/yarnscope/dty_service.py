"""dty_service.py - Qt-free logic of the DTY "YarnScope" tab (Show Experiment).

Everything the tab in ``ui/dty_yarnscope_tab.py`` computes lives here, so the
desktop tab and the web API (tripplet_web) run the same code. The desktop tab
keeps only widgets, matplotlib drawing and the QThreadPool workers; the web
uses the ``*_json`` helpers, which turn the same results into plain
JSON-friendly dicts (numpy arrays -> lists, NaN/inf -> None, long traces
min/max-decimated).

Moved from ``ui/dty_yarnscope_tab.py`` / ``ui/screen_tdms_batch.py`` /
``ui/yarnscope/garngraf_canvas.py`` (pure code move, no behaviour change).
Must stay importable without PySide6 (test: tests/test_dty_yarnscope_service.py).

Units: positions in metres (m) unless a name says mm; yarn thickness in µm
(the raw TDMS values; the Signal and Garnspiegel views multiply by 1000 when
the median is < 50, i.e. when the file stores mm); ``dx_mm`` = sample spacing
in mm.
"""
from __future__ import annotations

import math
import os
from datetime import datetime as _dt
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ENV_TDMS_DIR = "TRIPPLET_YARNSCOPE_DTY_DIR"
DEFAULT_TDMS_DIR = r"H:\Technik\TrippleT\YarnScopeTDMS"

MIN_SEG_PTS = 3          # analyze_series(..., min_seg_pts) as used by the tab
DEFAULT_DX_MM = 0.25     # fallback sample spacing when the TDMS has none
MAX_TRACE_POINTS = 8000  # default limit for decimated web traces

# Colours used by the desktop drawing (also handed to the web)
COLOR_ABC = {"A": "#e05050", "B": "#f0a030", "C": "#9060c0"}
COLOR_OPEN_SEGMENT = "#39A650"     # green open-spot segment means
COLOR_SIGNAL_LINE = "#c9d2e3"      # smoothed signal line / signal bars
COLOR_GARNSPIEGEL_OPEN = "#3a6a4a"  # passed to the canvas, which draws open parts white
TREND_COLOURS = {"open_knot": "#56d7d0", "peak_valley": "#ff6bb5", "opening": "#8de6a0"}
TREND_TITLES = {"open_knot": "Centre open spot–knot", "peak_valley": "Centre peak–valley",
                "opening": "Open spot trend"}
PROCESS_WAVE_COLOURS = {"binned": "#ffd166", "fitted": "#ff9f1c"}
COMPARE_COLOURS = ["#56d7d0", "#ff6bb5", "#ffd166", "#9b8cff", "#7ddf9a", "#ff9f1c"]
VERDICT_COLOURS = {
    "robust wave evidence": "#7ddf9a",
    "inconsistent evidence": "#ffd166",
    "not supported": "#ff7b7b",
}
COMPARE_TABLE_HEADERS = [
    "👁", "Farbe", "Trial", "Median [µm]", "λ [m]", "A [µm]", "R²", "Spektrum", "Drift [µm/m]", "Rest-RMS [µm]",
    "10 m sign.", "10 m λ-CV", "10 m A med. [µm]", "10 m R² med.", "Wave verdict",
]
# (label, vals key, decimals, unit) of the green metrics box below the tabs
METRICS_CARD = [
    ("FP/m", "FPm", 1, ""), ("CV", "CV_FP", 1, "%"),
    ("Ø KL", "AvgKL", 2, " mm"), ("CV", "CV_KL", 1, "%"),
    ("Ø OL", "AvgOL", 2, " mm"), ("CV", "CV_OL", 1, "%"),
    ("A", "AKnots", 1, "%"), ("B", "BKnots", 1, "%"), ("C", "CKnots", 1, "%"),
]
STAB_KEYS = [("Stab_03", "0.3"), ("Stab_06", "0.6"), ("Stab_10", "1.0"), ("Stab_13", "1.3")]
GARNSPIEGEL_SEGMENT_LEN_MM = 200.0
GARNSPIEGEL_TURNS = 20


# ===========================================================================
# TDMS files
# ===========================================================================

def tdms_base() -> Path:
    """Folder with the DTY TDMS files (env TRIPPLET_YARNSCOPE_DTY_DIR, else the H: share)."""
    return Path(os.environ.get(ENV_TDMS_DIR) or DEFAULT_TDMS_DIR)


def parse_tdms_ids(stem: str):
    """(TrialSeriesID, Versuchsnummer) from a file stem ``...<SeriesID>_<VersuchNr>_...``.

    Returns None if the stem does not match. (Moved from
    ``TDMSFolderScanner._parse_ids`` in screen_tdms_batch.py.)
    """
    try:
        first_us = stem.index("_")
    except ValueError:
        return None
    i = first_us - 1
    while i >= 0 and stem[i].isdigit():
        i -= 1
    num1 = stem[i + 1:first_us]
    if not num1:
        return None
    try:
        second_us = stem.index("_", first_us + 1)
    except ValueError:
        return None
    j = second_us - 1
    while j > first_us and stem[j].isdigit():
        j -= 1
    num2 = stem[j + 1:second_us]
    if not num2:
        return None
    try:
        return int(num1), int(num2)
    except ValueError:
        return None


def series_has_tdms(series_id: int, base=None) -> bool:
    """True if the folder holds at least one ``{series_id}_*.tdms`` (tab is shown then)."""
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
    """Path of the TDMS file of one trial (``{series}_{vno}_*.tdms``) or None."""
    base = Path(base) if base is not None else tdms_base()
    if not base.exists():
        return None
    try:
        for f in base.iterdir():
            if f.suffix.lower() == ".tdms" and f.stem.startswith(f"{series_id}_{versuch_no}_"):
                return f
    except Exception:
        pass
    try:
        for f in base.iterdir():
            if f.suffix.lower() == ".tdms":
                ids = parse_tdms_ids(f.stem)
                if ids == (series_id, versuch_no):
                    return f
    except Exception:
        pass
    return None


def trial_files(series_id, trials, reference_ids=(), with_analysed: bool = False, base=None) -> list:
    """The trial list of the tab.

    ``trials``: rows with ``ID`` and ``Versuchsnummer`` (as ShowExperiment's
    ``_trials``); reference samples (``reference_ids``, ids or {id: name}) are
    skipped - they never have a TDMS file.

    Returns ``[{"trial_id", "vno" (int), "tdms" (Path or None)[, "analysed" (bool)]}]``
    in trial order. ``analysed`` = a tbllabordtyomat row with Timestamp exists
    (desktop: ✅ analysed, ⏳ file but not analysed, nothing = no file).
    """
    out = []
    for t in trials:
        tid = t.get("ID")
        if tid is not None and int(tid) in reference_ids:
            continue
        vno = t.get("Versuchsnummer") or t.get("versuchsnummer") or 0
        tdms = find_tdms(series_id, int(vno), base) if series_id else None
        entry = {"trial_id": tid, "vno": int(vno), "tdms": tdms}
        if with_analysed:
            entry["analysed"] = is_trial_analysed(tid)
        out.append(entry)
    return out


# ===========================================================================
# Database
# ===========================================================================

def is_trial_analysed(trial_id) -> bool:
    """True if tbllabordtyomat already holds a saved analysis (Timestamp set)."""
    from db.connection import fetch_all
    try:
        rows = fetch_all("SELECT 1 FROM tbllabordtyomat WHERE TrialID = ? AND Timestamp IS NOT NULL", (trial_id,))
        return bool(rows)
    except Exception:
        return False


def analysed_trial_ids(trial_ids) -> set:
    """Set of the given trial ids that have a saved analysis (one query; for the web)."""
    from db.connection import fetch_all
    ids = [int(t) for t in trial_ids if t is not None]
    if not ids:
        return set()
    marks = ",".join("?" * len(ids))
    rows = fetch_all(
        f"SELECT DISTINCT TrialID FROM tbllabordtyomat WHERE Timestamp IS NOT NULL AND TrialID IN ({marks})",
        ids)
    return {int(r["TrialID"]) for r in rows}


# Column order of tbllabordtyomat written by save_analysis()
SAVE_COLUMNS = (
    "FPm, CV_FP, AvgFP, StdDevFP, "
    "CV_KL, AvgKL, StdDevKL, "
    "CV_OL, AvgOL, StdDevOL, maxOL, maxKL, "
    "kl_bin_1,kl_bin_2,kl_bin_3,kl_bin_4,kl_bin_5,"
    "kl_bin_6,kl_bin_7,kl_bin_8,kl_bin_9,kl_bin_10,"
    "ol_bin_1,ol_bin_2,ol_bin_3,ol_bin_4,ol_bin_5,"
    "ol_bin_6,ol_bin_7,ol_bin_8,ol_bin_9,ol_bin_10,"
    "AKnots, BKnots, CKnots,"
    "a_knots,b_knots,c_knots,d_knots,e_knots,f_knots,g_knots,h_knots,i_knots,j_knots,"
    "k_knots,l_knots,m_knots,n_knots,o_knots,p_knots,q_knots,r_knots,s_knots,t_knots,"
    "[Fallhöhe1],[Fallhöhe2],[Fallhöhe3],[Fallhöhe4],[Fallhöhe5],"
    "[Fallhöhe6],[Fallhöhe7],[Fallhöhe8],[Fallhöhe9],[Fallhöhe10],"
    "[Winkelsegment1],[Winkelsegment2],[Winkelsegment3],[Winkelsegment4],[Winkelsegment5],"
    "[Winkelsegment6],[Winkelsegment7],[Winkelsegment8],[Winkelsegment9],[Winkelsegment10],"
    "Stab_03, Stab_06, Stab_10, Stab_13,"
    "Stab_03_model, Stab_06_model, Stab_10_model, Stab_13_model,"
    "SkewKL, SkewOL, RapportCV, RapportCVLocal,"
    "ka_bin_1,ka_bin_2,ka_bin_3,ka_bin_4,ka_bin_5,ka_bin_6,ka_bin_7,ka_bin_8,ka_bin_9,ka_bin_10,"
    "ka_bin_11,ka_bin_12,ka_bin_13,ka_bin_14,ka_bin_15,ka_bin_16,ka_bin_17,ka_bin_18,ka_bin_19,ka_bin_20,"
    "oa_bin_1,oa_bin_2,oa_bin_3,oa_bin_4,oa_bin_5,oa_bin_6,oa_bin_7,oa_bin_8,oa_bin_9,oa_bin_10,"
    "oa_bin_11,oa_bin_12,oa_bin_13,oa_bin_14,oa_bin_15,oa_bin_16,oa_bin_17,oa_bin_18,oa_bin_19,oa_bin_20,"
    "KL_AC1, KL_AC2, KL_AC3, KL_TailRatio, OL_TailRatio, KA_OA_Ratio,"
    "KL_AsymMean, KL_AsymCV, KurtKL, KurtOL, ThicknessDrift,"
    "SpectralEnergyLow, SpectralEnergyMid, SpectralEnergyHigh,"
    "CKnot_ClusterMean, CKnot_ClusterMax, UserID, Timestamp"
)


def save_analysis(trial_id: int, vals: dict, user: dict) -> bool:
    """Writes all analysis values into tbllabordtyomat (UPDATE, else INSERT).

    ``vals`` = dict from extract_values()/full_extract_vals(); ``user`` = the
    logged-in user dict (``user["id"]`` -> UserID, as app_meta.current_user).
    Returns True on success, False on a DB error (moved from
    screen_tdms_batch._save_analysis_to_db).
    """
    from db.connection import fetch_all, execute

    def _v(key):
        v = vals.get(key)
        try:
            return float(v) if v is not None else None
        except Exception:
            return None

    def _s(key):
        v = vals.get(key)
        return str(v) if v is not None else None

    ts = _dt.now().strftime("%Y-%m-%d %H:%M:%S")

    params = [
        _v("FPm"), _v("CV_FP"), _v("AvgFP"), _v("StdDevFP"),
        _v("CV_KL"), _v("AvgKL"), _v("StdDevKL"),
        _v("CV_OL"), _v("AvgOL"), _v("StdDevOL"),
        _v("maxOL"), _v("maxKL"),
        *[_v(f"kl_bin_{i+1}") for i in range(10)],
        *[_v(f"ol_bin_{i+1}") for i in range(10)],
        _v("AKnots"), _v("BKnots"), _v("CKnots"),
        *[_v(f"{c}_knots") for c in "abcdefghijklmnopqrst"],
        *[_v(f"Fallhöhe{i+1}") for i in range(10)],
        *[_v(f"Winkelsegment{i+1}") for i in range(10)],
        _v("Stab_03"), _v("Stab_06"), _v("Stab_10"), _v("Stab_13"),
        _s("Stab_03_model"), _s("Stab_06_model"),
        _s("Stab_10_model"), _s("Stab_13_model"),
        _v("SkewKL"), _v("SkewOL"), _v("RapportCV"), _v("RapportCVLocal"),
        *[_v(f"ka_bin_{i+1}") for i in range(20)],
        *[_v(f"oa_bin_{i+1}") for i in range(20)],
        _v("KL_AC1"), _v("KL_AC2"), _v("KL_AC3"),
        _v("KL_TailRatio"), _v("OL_TailRatio"), _v("KA_OA_Ratio"),
        _v("KL_AsymMean"), _v("KL_AsymCV"),
        _v("KurtKL"), _v("KurtOL"), _v("ThicknessDrift"),
        _v("SpectralEnergyLow"), _v("SpectralEnergyMid"), _v("SpectralEnergyHigh"),
        _v("CKnot_ClusterMean"), _v("CKnot_ClusterMax"),
        int(user.get("id") or 0),
        ts,
    ]

    _QM = ",".join(["?"] * len(params))

    try:
        rows = fetch_all("SELECT 1 FROM tbllabordtyomat WHERE TrialID = ?", (trial_id,))
        exists = bool(rows)
    except Exception:
        exists = False

    col_list = [c.strip() for c in SAVE_COLUMNS.split(",") if c.strip()]

    try:
        if exists:
            set_parts = [f"{c}=?" for c in col_list]
            sql = f"UPDATE tbllabordtyomat SET {', '.join(set_parts)} WHERE TrialID=?"
            execute(sql, params + [trial_id])
        else:
            cols_str = ", ".join(col_list)
            sql = (
                f"INSERT INTO tbllabordtyomat (TrialID, {cols_str}) "
                f"VALUES (?, {_QM})"
            )
            execute(sql, [trial_id] + params)
        return True
    except Exception as e:
        print(f"[DTY Batch] DB-Fehler TrialID={trial_id}: {e}")
        return False


# ===========================================================================
# Pure computations (rolling means, trends, process wave, value extraction)
# ===========================================================================

def open_knot_midpoints(open_segs, knot_segs, x_axis):
    """Liefert (Position, Mittelpunkt zwischen Offenstelle und Knoten) pro Paar.

    Ein Paar ist eine Offenstelle mit dem direkt folgenden Knoten. Die Höhen
    sind die gleichen Segmentmittelwerte, die im Segmentmittel-Plot gezeichnet
    werden; die Position liegt genau zwischen den beiden Segmentmitten. Der
    Höhenwert ist jeweils ``Tal + (Peak - Tal) / 2``.
    """
    import math

    segments = [("open", g, mean) for g, mean in open_segs]
    segments.extend(("knot", g, mean) for g, mean in knot_segs)
    segments.sort(key=lambda item: int(item[1][0]) if len(item[1]) else -1)

    positions, midpoints = [], []
    for (kind_a, group_a, mean_a), (kind_b, group_b, mean_b) in zip(segments, segments[1:]):
        if kind_a != "open" or kind_b != "knot" or not len(group_a) or not len(group_b):
            continue
        try:
            lower, upper = sorted((float(mean_a), float(mean_b)))
            midpoint = lower + (upper - lower) / 2.0
            pos = (float(x_axis[int(group_a[len(group_a) // 2])]) +
                   float(x_axis[int(group_b[len(group_b) // 2])])) / 2.0
        except (IndexError, TypeError, ValueError):
            continue
        if math.isfinite(midpoint) and math.isfinite(pos):
            positions.append(pos)
            midpoints.append(midpoint)
    return positions, midpoints


def opening_segment_series(per_run, y_smooth, x_axis):
    """Liefert (Positionen, Segmentmittelwerte) je Öffnungsstelle (Nicht-Knoten-
    Segment) über das komplette Signal - dieselben grünen Öffnungsstellen-
    Segmentmittel, die im Segmentmittel-Plot gezeichnet werden (siehe
    open_segs dort), aber OHNE die Knoten-Mischung von
    open_knot_midpoints - Grundlage für die reine "Öffnungsstellen-Trend"-
    Linie im Prozessvergleich (Nutzerwunsch 2026-09-08).

    `per_run` sind die (start, end, ...)-Knotensegmente aus
    analyze_series()["classes"]["per_run"] (Indizes im vollen, ungefensterten
    Signal) - alles ausserhalb dieser Segmente zaehlt als Öffnungsstelle.
    """
    import numpy as np

    n = len(y_smooth)
    mask_knot = np.zeros(n, dtype=bool)
    for run in per_run or []:
        if not isinstance(run, (list, tuple)) or len(run) < 2:
            continue
        s, e = max(0, int(run[0])), min(n, int(run[1]))
        if e > s:
            mask_knot[s:e] = True

    positions, values = [], []
    idx = np.where(~mask_knot)[0]
    if idx.size:
        splits = np.where(np.diff(idx) > 1)[0] + 1
        for g in np.split(idx, splits):
            if g.size == 0:
                continue
            values.append(float(np.mean(y_smooth[g])))
            positions.append(float(x_axis[int(g[len(g) // 2])]))
    return positions, values


def rolling_mean(values, window_size: int):
    """Gleitender (rückblickender) Mittelwert ohne künstliche Randwerte."""
    window_size = max(1, int(window_size))
    result = []
    for end in range(1, len(values) + 1):
        start = max(0, end - window_size)
        result.append(sum(values[start:end]) / (end - start))
    return result


def rolling_mean_by_distance(positions, values, window_m: float):
    """Rückblickender gleitender Mittelwert über eine physische Länge in m."""
    window_m = max(0.001, float(window_m))
    if len(positions) != len(values):
        return []
    result = []
    left = 0
    running_sum = 0.0
    for right, (position, value) in enumerate(zip(positions, values)):
        running_sum += float(value)
        while left < right and float(position) - float(positions[left]) > window_m:
            running_sum -= float(values[left])
            left += 1
        result.append(running_sum / (right - left + 1))
    return result


def roll_trend(positions, values, mode: str, amount: float):
    """Wendet die in der UI gewählte Rollung an und liefert deren Beschriftung."""
    if mode == "Meter":
        return rolling_mean_by_distance(positions, values, amount), f"{amount:.1f} m"
    pairs = max(1, int(round(amount)))
    return rolling_mean(values, pairs), f"{pairs} pairs"


def local_extrema(values):
    """Lokale Peaks und Täler; flache Plateaus zählen als ein Ereignis."""
    values = [float(value) for value in values]
    if len(values) < 3:
        return []
    directions = [1 if right > left else (-1 if right < left else 0)
                  for left, right in zip(values, values[1:])]
    last = 0
    for i, direction in enumerate(directions):
        if direction:
            last = direction
        elif last:
            directions[i] = last
    last = 0
    for i in range(len(directions) - 1, -1, -1):
        if directions[i]:
            last = directions[i]
        elif last:
            directions[i] = last
    extrema = []
    for i in range(1, len(directions)):
        before, after = directions[i - 1], directions[i]
        if before > 0 and after < 0:
            extrema.append(("peak", i))
        elif before < 0 and after > 0:
            extrema.append(("valley", i))
    return extrema


def trend_metrics(positions, values):
    """Kennzahlen einer sichtbaren Trendlinie für die Versuchsvergleichsansicht."""
    import numpy as np

    if len(positions) != len(values) or not values:
        return None
    x = np.asarray(positions, dtype=float)
    y = np.asarray(values, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    x, y = x[valid], y[valid]
    if y.size == 0:
        return None

    median = float(np.median(y))
    p5, p95 = (float(value) for value in np.percentile(y, [5, 95]))
    mad = float(np.median(np.abs(y - median)))
    metrics = {
        "count": int(y.size), "median": median, "p5_p95": p95 - p5, "mad": mad,
        "slope": None, "end_delta": None, "wavelength": None,
        "wavelength_cv": None, "peak_to_peak": None, "peak_to_peak_p95": None,
    }
    if y.size >= 2 and float(np.ptp(x)) > 0:
        centered_x = x - float(np.mean(x))
        metrics["slope"] = float(np.dot(centered_x, y - float(np.mean(y))) /
                                 np.dot(centered_x, centered_x))
        left_cut = float(np.min(x) + np.ptp(x) * 0.10)
        right_cut = float(np.max(x) - np.ptp(x) * 0.10)
        start_mean = float(np.mean(y[x <= left_cut]))
        end_mean = float(np.mean(y[x >= right_cut]))
        metrics["end_delta"] = end_mean - start_mean

    extrema = local_extrema(y)
    peak_indices = [index for kind, index in extrema if kind == "peak"]
    if len(peak_indices) >= 2:
        distances = np.diff(x[peak_indices])
        distances = distances[distances > 0]
        if distances.size:
            metrics["wavelength"] = float(np.median(distances))
            mean_distance = float(np.mean(distances))
            metrics["wavelength_cv"] = (float(np.std(distances, ddof=0)) / mean_distance
                                          if mean_distance > 0 else None)
    amplitudes = []
    for (kind_a, index_a), (kind_b, index_b) in zip(extrema, extrema[1:]):
        if kind_a == "peak" and kind_b == "valley":
            amplitudes.append(float(y[index_a] - y[index_b]))
    if amplitudes:
        metrics["peak_to_peak"] = float(np.median(amplitudes))
        metrics["peak_to_peak_p95"] = float(np.percentile(amplitudes, 95))
    return metrics


def analyze_process_wave(x_values, y_values, bin_width_m: float = 0.05):
    """Quantifiziert eine niederfrequente, räumlich periodische Prozesswelle.

    Das hochaufgelöste Signal wird zunächst in gleich breite Meter-Bins
    gemittelt. Anschließend wird ein linearer Drift entfernt und die stärkste
    Frequenz im physikalisch sinnvollen Bereich (0.25 m bis mindestens drei
    Zyklen im sichtbaren Fenster) gesucht. Ein Sinus-Fit liefert Amplitude
    und R² als direkt interpretierbare Kenngrößen.
    """
    import numpy as np

    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    x, y = x[valid], y[valid]
    bin_width_m = max(0.01, float(bin_width_m))
    if x.size < 4 or float(np.ptp(x)) < bin_width_m * 6:
        return None

    start = float(np.min(x))
    stop = float(np.max(x))
    edges = np.arange(start, stop + bin_width_m, bin_width_m)
    if edges[-1] < stop:
        edges = np.append(edges, edges[-1] + bin_width_m)
    bin_index = np.clip(np.digitize(x, edges) - 1, 0, len(edges) - 2)
    counts = np.bincount(bin_index, minlength=len(edges) - 1)
    sums = np.bincount(bin_index, weights=y, minlength=len(edges) - 1)
    keep = counts > 0
    bx = (edges[:-1] + edges[1:]) / 2.0
    bx, by = bx[keep], (sums[keep] / counts[keep])
    if bx.size < 6:
        return None

    # Gleichmäßiges Raster ist Voraussetzung für das Spektrum. Bei sehr
    # kurzen Lücken wird linear interpoliert; TDMS hat normalerweise keine.
    grid = np.arange(bx[0], bx[-1] + bin_width_m * 0.5, bin_width_m)
    gy = np.interp(grid, bx, by)
    span = float(grid[-1] - grid[0])
    if grid.size < 8 or span < bin_width_m * 6:
        return None

    design_drift = np.column_stack((np.ones_like(grid), grid - np.mean(grid)))
    drift_coef, *_ = np.linalg.lstsq(design_drift, gy, rcond=None)
    drift = design_drift @ drift_coef
    residual = gy - drift

    frequencies = np.fft.rfftfreq(grid.size, d=bin_width_m)
    powers = np.abs(np.fft.rfft(residual)) ** 2
    min_wavelength = max(0.25, bin_width_m * 4.0)
    max_wavelength = span / 3.0  # mindestens drei beobachtete Zyklen
    wavelengths = np.full_like(frequencies, np.inf)
    np.divide(1.0, frequencies, out=wavelengths, where=frequencies > 0)
    allowed = (frequencies > 0) & (wavelengths >= min_wavelength) & (
        wavelengths <= max_wavelength)
    if not np.any(allowed):
        return None
    candidate_indices = np.flatnonzero(allowed)
    best_index = candidate_indices[int(np.argmax(powers[candidate_indices]))]
    frequency = float(frequencies[best_index])
    wavelength = 1.0 / frequency

    omega = 2.0 * np.pi * frequency
    design = np.column_stack((
        np.ones_like(grid), grid - np.mean(grid),
        np.sin(omega * grid), np.cos(omega * grid),
    ))
    coef, *_ = np.linalg.lstsq(design, gy, rcond=None)
    fitted = design @ coef
    amplitude = float(np.hypot(coef[2], coef[3]))
    ss_total = float(np.sum((gy - np.mean(gy)) ** 2))
    ss_residual = float(np.sum((gy - fitted) ** 2))
    r_squared = max(0.0, 1.0 - ss_residual / ss_total) if ss_total > 0 else 0.0
    allowed_power = float(np.sum(powers[candidate_indices]))
    spectral_share = float(powers[best_index] / allowed_power) if allowed_power > 0 else 0.0

    return {
        "x": grid, "binned": gy, "fitted": fitted, "drift_line": drift,
        "bin_width": bin_width_m, "span": span,
        "wavelength": wavelength, "amplitude": amplitude,
        "r_squared": r_squared, "spectral_share": spectral_share,
        "drift": float(drift_coef[1]),
        "residual_rms": float(np.sqrt(np.mean((gy - fitted) ** 2))),
    }


def process_wave_reality_check(x_values, y_values, bin_width_m: float = 0.05,
                                   segment_m: float = 10.0, n_surrogates: int = 30):
    """Prüft, ob eine Prozesswelle über unabhängige Abschnitte reproduzierbar ist.

    Jeder 10-m-Abschnitt wird separat ausgewertet. Für die Zufallskontrolle
    wird seine gebinnte Mittellinie räumlich gemischt; so bleiben Verteilung
    und Streuung erhalten, aber jede räumliche Periodik geht verloren.
    """
    import numpy as np

    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    x, y = x[valid], y[valid]
    if x.size == 0 or float(np.ptp(x)) < segment_m:
        return None
    # Der letzte Datenpunkt liegt üblicherweise knapp vor dem nominellen
    # Messende (z. B. 99.998 m bei 100 m). Eine Binbreite Toleranz nimmt den
    # vollständigen letzten Abschnitt deshalb noch mit.
    starts = np.arange(float(np.min(x)),
                       float(np.max(x)) - segment_m + bin_width_m + 1e-9,
                       segment_m)
    rng = np.random.default_rng(20260907)
    windows = []
    for start in starts:
        mask = (x >= start) & (x < start + segment_m)
        analysis = analyze_process_wave(x[mask], y[mask], bin_width_m)
        if analysis is None:
            continue
        surrogate_shares = []
        for _ in range(n_surrogates):
            shuffled = rng.permutation(analysis["binned"])
            surrogate = analyze_process_wave(
                analysis["x"], shuffled, bin_width_m)
            if surrogate is not None:
                surrogate_shares.append(surrogate["spectral_share"])
        p_value = ((1 + sum(value >= analysis["spectral_share"] for value in surrogate_shares)) /
                   (1 + len(surrogate_shares))) if surrogate_shares else None
        windows.append({"analysis": analysis, "p_value": p_value})
    if not windows:
        return None

    wavelengths = np.asarray([item["analysis"]["wavelength"] for item in windows], dtype=float)
    amplitudes = np.asarray([item["analysis"]["amplitude"] for item in windows], dtype=float)
    r_squared = np.asarray([item["analysis"]["r_squared"] for item in windows], dtype=float)
    significant = sum(item["p_value"] is not None and item["p_value"] < 0.05 for item in windows)
    lambda_mean = float(np.mean(wavelengths))
    lambda_cv = float(np.std(wavelengths, ddof=0) / lambda_mean) if lambda_mean > 0 else None
    fraction_significant = significant / len(windows)
    median_r2 = float(np.median(r_squared))
    if (len(windows) >= 5 and fraction_significant >= 0.70 and lambda_cv is not None
            and lambda_cv <= 0.20 and median_r2 >= 0.20):
        verdict = "robust wave evidence"
    elif fraction_significant >= 0.30:
        verdict = "inconsistent evidence"
    else:
        verdict = "not supported"
    return {
        "windows": len(windows), "significant": significant,
        "lambda_median": float(np.median(wavelengths)), "lambda_cv": lambda_cv,
        "amplitude_median": float(np.median(amplitudes)), "r2_median": median_r2,
        "verdict": verdict,
    }


def peak_valley_midpoints(y_values, x_axis):
    """Liefert (Talposition, Mittelpunkt von Peak und folgendem Tal) je Paar.

    Flache Plateaus werden als ein Extrem behandelt. Die Funktion arbeitet auf
    dem bereits für die Anzeige geglätteten Signal, damit Messrauschen nicht
    als eigene Peak–Tal-Bewegung in die Trendlinie eingeht.
    """
    import math

    n = min(len(y_values), len(x_axis))
    if n < 3:
        return [], []
    values = [float(y_values[i]) for i in range(n)]
    extrema = local_extrema(values)

    positions, midpoints = [], []
    for (kind_a, index_a), (kind_b, index_b) in zip(extrema, extrema[1:]):
        if kind_a != "peak" or kind_b != "valley":
            continue
        valley, peak = values[index_b], values[index_a]
        midpoint = valley + (peak - valley) / 2.0
        position = float(x_axis[index_b])  # Trend gilt, sobald das Tal erreicht ist.
        if math.isfinite(midpoint) and math.isfinite(position):
            positions.append(position)
            midpoints.append(midpoint)
    return positions, midpoints


def extract_basic_vals(res: dict) -> dict:
    """Extrahiert DB-Feldnamen aus dem analyze_series-Ergebnis."""
    import numpy as np
    import math

    def _safe(v):
        if v is None: return None
        try:
            f = float(v)
            return f if math.isfinite(f) else None
        except Exception:
            return None

    out = {}
    out["FPm"] = _safe(res.get("knots_per_m"))
    ol_p = res.get("ol_period_mm_stats") or {}
    mm = _safe(ol_p.get("mean"));
    sd = _safe(ol_p.get("sd"))
    out["AvgFP"] = mm / 10.0 if mm is not None else None
    out["StdDevFP"] = sd / 10.0 if sd is not None else None
    out["CV_FP"] = _safe(ol_p.get("cv"))

    knot = res.get("knot") or {}
    out["CV_KL"] = _safe(knot.get("cv"))
    out["AvgKL"] = _safe(knot.get("mean"))
    out["StdDevKL"] = _safe(knot.get("sd"))
    out["maxKL"] = _safe(knot.get("max"))

    open_ = res.get("open") or {}
    out["CV_OL"] = _safe(open_.get("cv"))
    out["AvgOL"] = _safe(open_.get("mean"))
    out["StdDevOL"] = _safe(open_.get("sd"))
    out["maxOL"] = _safe(open_.get("max"))

    abc_per_m = res.get("abc_per_m") or {}
    total_abc = sum(float(v) for v in abc_per_m.values() if v is not None and math.isfinite(float(v)))
    if total_abc > 0:
        out["AKnots"] = _safe(100.0 * abc_per_m.get("A", 0.0) / total_abc)
        out["BKnots"] = _safe(100.0 * abc_per_m.get("B", 0.0) / total_abc)
        out["CKnots"] = _safe(100.0 * abc_per_m.get("C", 0.0) / total_abc)
    else:
        out["AKnots"] = out["BKnots"] = out["CKnots"] = None

    strength_per_m = res.get("knot_strength_per_m") or {}
    total_str = sum(float(v) for v in strength_per_m.values() if v is not None and math.isfinite(float(v)))
    for c in "abcdefghijklmnopqrst":
        v = strength_per_m.get(c)
        out[f"{c}_knots"] = _safe(100.0 * float(v) / total_str) if (total_str > 0 and v is not None) else None

    def _bins10(lengths):
        if not lengths: return [None] * 10
        arr = np.array(lengths, dtype=float)
        lo, hi = np.percentile(arr, 2), np.percentile(arr, 98)
        if hi <= lo: return [None] * 10
        counts, _ = np.histogram(arr, bins=np.linspace(lo, hi, 11))
        total = counts.sum()
        return [float(c / total * 100) if total > 0 else None for c in counts]

    kl_b = _bins10(res.get("knot_lengths_mm") or [])
    ol_b = _bins10(res.get("open_lengths_mm") or [])
    for i in range(10):
        out[f"kl_bin_{i + 1}"] = kl_b[i]
        out[f"ol_bin_{i + 1}"] = ol_b[i]

    out["SkewKL"] = _safe(res.get("skew_kl"))
    out["SkewOL"] = _safe(res.get("skew_ol"))
    out["RapportCV"] = _safe(res.get("rapport_cv_global"))
    out["RapportCVLocal"] = _safe(res.get("rapport_cv_local"))
    out["KL_AC1"] = _safe(res.get("kl_ac1"))
    out["KL_AC2"] = _safe(res.get("kl_ac2"))
    out["KL_AC3"] = _safe(res.get("kl_ac3"))
    out["KL_TailRatio"] = _safe(res.get("kl_tail_ratio"))
    out["OL_TailRatio"] = _safe(res.get("ol_tail_ratio"))
    out["KA_OA_Ratio"] = _safe(res.get("ka_oa_ratio"))
    out["KL_AsymMean"] = _safe(res.get("kl_asym_mean"))
    out["KL_AsymCV"] = _safe(res.get("kl_asym_cv"))
    out["KurtKL"] = _safe(res.get("kurt_kl"))
    out["KurtOL"] = _safe(res.get("kurt_ol"))
    out["ThicknessDrift"] = _safe(res.get("thickness_drift"))
    out["SpectralEnergyLow"] = _safe(res.get("spectral_low"))
    out["SpectralEnergyMid"] = _safe(res.get("spectral_mid"))
    out["SpectralEnergyHigh"] = _safe(res.get("spectral_high"))
    out["CKnot_ClusterMean"] = _safe(res.get("aknot_cluster_mean"))
    out["CKnot_ClusterMax"] = _safe(res.get("aknot_cluster_max"))
    return out


# ===========================================================================
# Analysis of one trial
# ===========================================================================

def analyse_signal_file(path) -> dict:
    """Reads the TDMS file and runs analyze_series (step 1 of "▶ Analyse").

    Returns the analyze_series result plus ``_y_raw`` (signal as read, numpy
    array) and ``_dx_mm`` (sample spacing, mm). Raises ValueError("No signal
    in the TDMS file.") for an empty file.
    """
    import numpy as np
    from ui.yarnscope.dty_analysis import analyze_series
    from ui.yarnscope.dty_tdms_reader import (
        read_dty_signal, read_step_mm_from_tdms)
    y = read_dty_signal(str(path))
    dx_mm = read_step_mm_from_tdms(str(path)) or 0.25
    if y is None or len(y) == 0:
        raise ValueError("No signal in the TDMS file.")
    res = analyze_series(np.asarray(y, dtype=float), float(dx_mm), 3)
    res["_y_raw"] = y  # numpy-Array direkt behalten (kein .tolist() → kein teurer Copy)
    res["_dx_mm"] = float(dx_mm)
    return res


def extract_values(res: dict, trial_id=None, progress_cb=None) -> dict:
    """Step 2: all DB values (tbllabordtyomat column -> value) incl. stability
    predictions; falls back to extract_basic_vals() if the full extraction fails."""
    try:
        from ui.yarnscope.dty_analysis import full_extract_vals
        y_raw = res.get("_y_raw")
        dx_mm = float(res.get("_dx_mm") or 0.25)
        vals = full_extract_vals(
            res, y_raw, dx_mm, 3, trial_id=trial_id,
            progress_cb=progress_cb)
    except Exception as e:
        vals = extract_basic_vals(res)
    return vals


def analyse_trial(path, trial_id=None, progress_cb=None):
    """Full analysis of one TDMS file -> ``(res, vals)`` (= the desktop's ``_ys_cache[tid]``)."""
    res = analyse_signal_file(path)
    return res, extract_values(res, trial_id=trial_id, progress_cb=progress_cb)


def analysis_status_text(vals: dict) -> str:
    """Status line after an analysis ("Analysis finished.  |  Stab: 0.3: 12.3%   …")."""
    stab_info = []
    for key, label in [("Stab_03", "0.3"), ("Stab_06", "0.6"),
                       ("Stab_10", "1.0"), ("Stab_13", "1.3")]:
        v = vals.get(key)
        if v is not None:
            stab_info.append(f"{label}: {v:.1f}%")
    stab_str = "   ".join(stab_info) if stab_info else ""
    return "Analysis finished." + (f"  |  Stab: {stab_str}" if stab_str else "")


def pie_values(vals: dict) -> dict:
    """A/B/C knot shares in % for the ABC pie (0.0 when missing)."""
    return {"A": vals.get("AKnots") or 0.0,
            "B": vals.get("BKnots") or 0.0,
            "C": vals.get("CKnots") or 0.0}


def thresholds(res: dict):
    """``(T, T - tA, T - tB)``: threshold T and the two class limits in µm.

    Segment plot labels them "C/B-Grenze" (T - tA) and "B/A-Grenze" (T - tB);
    the Signal tab calls the same two values "A/B" and "B/C".
    """
    T = res.get("threshold")
    cls_info = res.get("classes") or {}
    thr = cls_info.get("thresholds", (None, None))
    try:
        tA, tB = thr if not isinstance(thr, dict) else (thr.get("tA"), thr.get("tB"))
    except Exception:
        tA, tB = None, None
    y_cb = (float(T) - tA) if (T is not None and tA is not None) else None
    y_ba = (float(T) - tB) if (T is not None and tB is not None) else None
    return T, y_cb, y_ba


def segment_class(mv, y_cb, y_ba) -> str:
    """Knot class A/B/C of a segment mean (segment mean plot)."""
    lo = y_cb if y_cb is not None else float("nan")
    hi = y_ba if y_ba is not None else float("nan")
    if not math.isfinite(lo) or not math.isfinite(hi):
        lo, hi = (min(lo, hi), max(lo, hi)) if (math.isfinite(lo) and math.isfinite(hi)) else (float("nan"),
                                                                                               float("nan"))
    lo2, hi2 = (min(lo, hi), max(lo, hi))
    if math.isfinite(lo2) and mv <= lo2: return "A"
    if math.isfinite(hi2) and mv <= hi2: return "B"
    return "C"


def garnspiegel_class(mv, y_cb, y_ba) -> str:
    """Knot class A/B/C of a knot mean (Garnspiegel; differs from
    segment_class() only when exactly one limit is missing/NaN)."""
    lo = y_cb if y_cb is not None else float("nan")
    hi = y_ba if y_ba is not None else float("nan")
    lo2, hi2 = min(lo, hi), max(lo, hi)
    if math.isfinite(lo2) and mv <= lo2: return "A"
    if math.isfinite(hi2) and mv <= hi2: return "B"
    return "C"


# ===========================================================================
# Views (the data behind the sub tabs)
# ===========================================================================

def segment_view(res: dict, vals: dict, start_m: float = 0.0, window_m: float = 3.0, *,
                 open_knot=None, peak_valley=None, opening=None,
                 process_wave_bin=None, with_metrics: bool = False):
    """Data of the "Segmentmittel" sub tab (and the cards above it).

    ``open_knot`` / ``peak_valley`` / ``opening``: None = trend line off, else
    ``(mode, amount)`` with mode "Meter" (amount = window in m) or "Paare"
    (amount = number of pairs). ``process_wave_bin``: None = off, else bin
    width in m. Returns None if the result holds no signal.

    Keys: ``total_m``; ``start_m``/``window_m`` (clamped, = x range of the
    plot); ``start_idx``/``end_idx`` (sample indices); ``x`` (m) and
    ``y_smooth`` (moving average k=3 of the window, grey line); ``open_segments``
    [(index array into x, mean)] (green); ``knot_segments`` [(index array, mean)]
    with ``knot_classes`` ["A"|"B"|"C"] (COLOR_ABC); ``counts`` {A, B, C} in the
    window; ``threshold``/``y_cb``/``y_ba`` (horizontal lines); ``trends``
    {open_knot|peak_valley|opening: {enabled, x, y, roll_label[, metrics]}};
    ``process_wave`` (analyze_process_wave() or None) + ``process_wave_enabled``;
    ``pie`` (pie_values()).
    """
    import numpy as np
    from ui.yarnscope.dty_analysis import _moving_average

    y_raw = res.get("_y_raw")
    dx_mm = float(res.get("_dx_mm") or 0.25)
    if y_raw is None:
        return None

    y_arr = np.asarray(y_raw, dtype=float)
    total_m = len(y_arr) * dx_mm / 1000.0

    start_m = float(start_m)
    window_m = float(window_m)
    start_m = max(0.0, min(start_m, total_m))
    window_m = max(0.1, min(window_m, 100.0, total_m - start_m))

    pts_per_m = int(round(1000.0 / dx_mm))
    start_idx = int(round(start_m * pts_per_m))
    count = max(1, int(round(window_m * pts_per_m)))
    end_idx = min(start_idx + count, len(y_arr))

    yseg = y_arr[start_idx:end_idx]
    x_axis = np.arange(start_idx, end_idx) * dx_mm / 1000.0

    # Glätten
    y_smooth = _moving_average(yseg, 3)

    # Threshold + Klassengrenzen
    T, y_cb, y_ba = thresholds(res)
    cls_info = res.get("classes") or {}

    # per_run aus res
    per_run = cls_info.get("per_run", [])

    # Knoten- und Öffnungssegmente berechnen
    mask_knot = np.zeros(len(y_smooth), dtype=bool)
    knot_segs = []
    for run in per_run:
        if not isinstance(run, (list, tuple)) or len(run) < 2:
            continue
        s, e = int(run[0]), int(run[1])
        if e <= start_idx or s >= end_idx:
            continue
        ls = max(s, start_idx) - start_idx
        le = min(e, end_idx) - start_idx
        if le <= ls: continue
        g = np.arange(ls, le)
        mask_knot[ls:le] = True
        mv = float(np.mean(y_smooth[g])) if g.size else float("nan")
        knot_segs.append((g, mv))

    open_segs = []
    ii = np.where(~mask_knot)[0]
    if ii.size:
        splits = np.where(np.diff(ii) > 1)[0] + 1
        for g in np.split(ii, splits):
            if g.size == 0: continue
            mv = float(np.mean(y_smooth[g]))
            open_segs.append((g, mv))

    # Optional: pro Offenstelle mit direkt folgendem Knoten die Mitte
    # zwischen beiden Höhen bilden und als gleitenden Mittelwert darstellen.
    open_knot_trend_x, open_knot_trend_y, open_knot_roll_label = [], [], ""
    if open_knot is not None:
        open_knot_trend_x, raw_midpoints = open_knot_midpoints(
            open_segs, knot_segs, x_axis)
        roll_mode, roll_amount = open_knot
        open_knot_trend_y, open_knot_roll_label = roll_trend(
            open_knot_trend_x, raw_midpoints, roll_mode, float(roll_amount))

    peak_valley_trend_x, peak_valley_trend_y, peak_valley_roll_label = [], [], ""
    if peak_valley is not None:
        peak_valley_trend_x, raw_midpoints = peak_valley_midpoints(y_smooth, x_axis)
        roll_mode, roll_amount = peak_valley
        peak_valley_trend_y, peak_valley_roll_label = roll_trend(
            peak_valley_trend_x, raw_midpoints, roll_mode, float(roll_amount))

    # Öffnungsstellen-Trend (Nutzerwunsch 2026-09-08): rollender Mittelwert
    # NUR über die grünen Öffnungsstellen-Segmentmittel (open_segs), ohne
    # Knoten-Mischung wie bei open_knot_trend.
    opening_trend_x, opening_trend_y, opening_roll_label = [], [], ""
    if opening is not None:
        opening_trend_x = [float(x_axis[int(g[len(g) // 2])]) for g, _mv in open_segs if len(g)]
        raw_values = [mv for g, mv in open_segs if len(g)]
        roll_mode, roll_amount = opening
        opening_trend_y, opening_roll_label = roll_trend(
            opening_trend_x, raw_values, roll_mode, float(roll_amount))

    process_wave = None
    if process_wave_bin is not None:
        process_wave = analyze_process_wave(x_axis, y_smooth, float(process_wave_bin))

    knot_classes = []
    counts = {"A": 0, "B": 0, "C": 0}
    for g, mv in knot_segs:
        cls = segment_class(mv, y_cb, y_ba)
        knot_classes.append(cls)
        counts[cls] += 1

    trends = {
        "open_knot": {"enabled": open_knot is not None, "x": open_knot_trend_x,
                      "y": open_knot_trend_y, "roll_label": open_knot_roll_label},
        "peak_valley": {"enabled": peak_valley is not None, "x": peak_valley_trend_x,
                        "y": peak_valley_trend_y, "roll_label": peak_valley_roll_label},
        "opening": {"enabled": opening is not None, "x": opening_trend_x,
                    "y": opening_trend_y, "roll_label": opening_roll_label},
    }
    if with_metrics:
        for trend in trends.values():
            trend["metrics"] = (trend_metrics(trend["x"], trend["y"])
                                if trend["enabled"] else None)

    return {
        "total_m": total_m, "start_m": start_m, "window_m": window_m, "dx_mm": dx_mm,
        "start_idx": start_idx, "end_idx": end_idx,
        "x": x_axis, "y_smooth": y_smooth,
        "threshold": T, "y_cb": y_cb, "y_ba": y_ba,
        "open_segments": open_segs, "knot_segments": knot_segs,
        "knot_classes": knot_classes, "counts": counts,
        "trends": trends,
        "process_wave": process_wave, "process_wave_enabled": process_wave_bin is not None,
        "pie": pie_values(vals or {}),
    }


def smoothed_signal_um(res: dict):
    """``(y_smooth, dx_mm)``: whole signal in µm (x1000 if the median is < 50,
    i.e. stored in mm), moving average k=3; None without signal."""
    import numpy as np
    from ui.yarnscope.dty_analysis import _moving_average

    y_raw = res.get("_y_raw")
    dx_mm = float(res.get("_dx_mm") or 0.25)
    if y_raw is None or len(y_raw) == 0:
        return None

    y_um = np.asarray(y_raw, dtype=float)
    if float(np.median(y_um)) < 50.0:
        y_um = y_um * 1000.0

    # Glaetten wie Segmentmittel (k=3)
    y_smooth = _moving_average(y_um, 3)
    return y_smooth, dx_mm


def signal_view(res: dict, start_m: float = 0.0, window_m: float = 3.0):
    """Data of the "Signal" sub tab (bars of the smoothed signal in µm).

    Returns None without signal. Keys: ``x`` (bar left edges, m), ``y`` (µm,
    moving average k=3 over the whole signal, then windowed), ``step_m`` (bar
    width), ``window_m``/``start_m`` (clamped), ``total_m``, ``threshold``,
    ``y_ab`` (= T - tA), ``y_bc`` (= T - tB). Axis limits: signal_limits().
    """
    import numpy as np

    smoothed = smoothed_signal_um(res)
    if smoothed is None:
        return None
    y_smooth, dx_mm = smoothed

    total_m = len(y_smooth) * dx_mm / 1000.0
    start_m = float(start_m)
    window_m = float(window_m)
    start_m = max(0.0, min(start_m, total_m))
    window_m = max(0.1, min(window_m, total_m - start_m))

    pts_per_m = int(round(1000.0 / dx_mm))
    start_idx = int(round(start_m * pts_per_m))
    count = max(1, int(round(window_m * pts_per_m)))
    end_idx = min(start_idx + count, len(y_smooth))

    yseg = y_smooth[start_idx:end_idx]
    x_abs = np.arange(start_idx, end_idx) * dx_mm / 1000.0
    step_m = dx_mm / 1000.0

    # Schwellenwerte
    T, y_ab, y_bc = thresholds(res)
    return {"x": x_abs, "y": yseg, "step_m": step_m, "start_m": start_m,
            "window_m": window_m, "total_m": total_m, "dx_mm": dx_mm,
            "threshold": T, "y_ab": y_ab, "y_bc": y_bc}


def signal_limits(view: dict):
    """``(ylim, xlim)`` of the Signal tab: y not starting at 0 (5 % margin
    around signal + threshold lines), x = window. Raises on an empty window."""
    import numpy as np
    yseg, x_abs = view["y"], view["x"]
    T, y_ab, y_bc = view["threshold"], view["y_ab"], view["y_bc"]
    candidates = [float(np.min(yseg)), float(np.max(yseg))]
    for v in (T, y_ab, y_bc):
        if v is not None and math.isfinite(float(v)):
            candidates.append(float(v))
    y_min, y_max = min(candidates), max(candidates)
    rng = max(y_max - y_min, 1.0)
    return (y_min - rng * 0.05, y_max + rng * 0.05), (x_abs[0], x_abs[0] + view["window_m"])


def garnspiegel_inputs(res: dict, start_m: float = 0.0):
    """Keyword arguments for ``GarnCanvas.plot_garnspiegel_dty`` (Garnspiegel
    sub tab, from ``start_m`` to the end of the signal); None without signal."""
    import numpy as np
    from ui.yarnscope.dty_analysis import _moving_average

    y_raw = res.get("_y_raw")
    dx_mm = float(res.get("_dx_mm") or 0.25)
    if y_raw is None or len(y_raw) == 0:
        return None

    y_um_full = np.asarray(y_raw, dtype=float)
    if float(np.median(y_um_full)) < 50.0:
        y_um_full = y_um_full * 1000.0

    # ── Startpunkt (identisch zum Segmentmittel-Plot) ────────
    total_m = len(y_um_full) * dx_mm / 1000.0
    start_m = max(0.0, min(start_m, total_m))
    pts_per_m = int(round(1000.0 / dx_mm))
    start_idx = int(round(start_m * pts_per_m))

    # Ab Startpunkt schneiden – per_run Indizes entsprechend verschieben
    y_um = y_um_full[start_idx:]
    y_smooth = _moving_average(y_um, 3)

    # ── Schwellenwerte ───────────────────────────────────────────────────
    T, y_cb, y_ba = thresholds(res)
    cls_info = res.get("classes") or {}

    def _class_from_mean(mv):
        return garnspiegel_class(mv, y_cb, y_ba)

    # per_run: Indizes relativ zum vollen Signal -> auf geschnittenes verschieben
    per_run_raw = cls_info.get("per_run", [])
    per_run = []
    for run in per_run_raw:
        if not isinstance(run, (list, tuple)) or len(run) < 2:
            continue
        s, e = int(run[0]) - start_idx, int(run[1]) - start_idx
        if e <= 0 or s >= len(y_um):
            continue
        per_run.append((max(0, s), min(len(y_um), e)))

    # Bandbreite direkt aus absolutem Signal normiert auf Segment-Mittelwert.
    # Duennstellen (Knoten) -> kleiner Wert -> schmaleres Band.
    # Dickstellen (Oeffnungen) -> groesserer Wert -> breiteres Band.
    seg_mean = float(np.mean(y_smooth))
    clip = seg_mean  # Normierungsreferenz

    return dict(
        y_dev=y_smooth,  # absolutes Signal, nicht Abweichung
        clip_um=clip,
        per_run=per_run,
        class_fn=_class_from_mean,
        color_abc=dict(COLOR_ABC),
        color_open=COLOR_GARNSPIEGEL_OPEN,
        dx_mm=dx_mm,
        y_um=y_um,
        num_turns=GARNSPIEGEL_TURNS,
    )


def garnspiegel_dty_geometry(y_dev, per_run, class_fn, dx_mm: float = 0.25, y_um=None,
                             num_turns: int = 10, gap_factor: float = 2.0,
                             segment_len_mm: float = GARNSPIEGEL_SEGMENT_LEN_MM):
    """Geometry of the DTY Garnspiegel (moved out of GarnCanvas.plot_garnspiegel_dty).

    The signal is cut into ``turns`` rows of ``segment_len_mm`` each. Per row:
    ``base`` (y centre), ``x`` (mm from the row start), ``half`` (half band
    width per sample, the band is base ± half), ``knot_mask`` (bool per sample)
    and ``knot_class`` ("" = open spot, drawn white; "A"/"B"/"C" = knot, drawn
    in COLOR_ABC). Returns None for an empty signal, else
    ``{rows, turns, pts_per_row, seg_len_mm, row_h, xlim, ylim}``.
    """
    import numpy as np

    # Rohdaten: absolutes Signal in µm
    src = y_um if y_um is not None else (y_dev + np.mean(y_dev))
    n_total = len(src)
    if n_total == 0:
        return None

    pts_per_row = max(1, int(round(segment_len_mm / dx_mm)))
    turns = max(1, min(int(num_turns), n_total // pts_per_row))
    use   = turns * pts_per_row

    seg_len_mm = pts_per_row * dx_mm
    x_mm  = np.linspace(0.0, seg_len_mm, pts_per_row, endpoint=False)

    # Globaler Mittelwert als Referenz fuer Zeilenabstand
    global_mean = float(np.mean(src[:use]))
    row_h = global_mean * gap_factor

    # Knoten-Maske + Klasse
    knot_mask  = np.zeros(use, dtype=bool)
    knot_class = np.full(use, "", dtype=object)
    for run in per_run:
        if not isinstance(run, (list, tuple)) or len(run) < 2:
            continue
        s, e = int(run[0]), int(run[1])
        if e <= s or s >= use:
            continue
        e = min(e, use)
        mv  = float(np.mean(src[s:e])) if e > s else 0.0
        cls = class_fn(mv)
        knot_mask[s:e]  = True
        knot_class[s:e] = cls

    rows = []
    for row in range(turns):
        s    = row * pts_per_row
        e    = s + pts_per_row
        seg  = src[s:e].copy()
        km   = knot_mask[s:e]
        kc   = knot_class[s:e]
        base = -row * row_h
        xr   = x_mm[:len(seg)]

        # Normalisierung: Segment-Mittelwert = 1.0
        seg_mean = float(np.mean(seg)) if len(seg) > 0 else global_mean
        seg_norm = seg / max(seg_mean, 1e-9)  # ~1.0 ueberall, Knoten etwas kleiner

        # Verstärkung der Variation fuer Sichtbarkeit
        # Abweichung vom 1.0 wird stark verstaerkt
        amp = 20.0
        seg_vis = 1.0 + (seg_norm - 1.0) * amp
        seg_vis = np.clip(seg_vis, 0.05, 3.0)

        half = seg_vis * global_mean * 0.12
        rows.append({"base": base, "x": xr, "half": half,
                     "knot_mask": km, "knot_class": kc})

    y_top = row_h * 0.5
    y_bot = -(turns - 1) * row_h - row_h * 0.5
    return {"rows": rows, "turns": turns, "pts_per_row": pts_per_row,
            "seg_len_mm": seg_len_mm, "row_h": row_h,
            "xlim": (0.0, seg_len_mm), "ylim": (y_bot, y_top)}


def garnspiegel_view(res: dict, start_m: float = 0.0):
    """Garnspiegel geometry for a trial (garnspiegel_dty_geometry() of
    garnspiegel_inputs()), or None without signal."""
    kw = garnspiegel_inputs(res, start_m)
    if kw is None:
        return None
    return garnspiegel_dty_geometry(
        kw["y_dev"], kw["per_run"], kw["class_fn"], dx_mm=kw["dx_mm"],
        y_um=kw["y_um"], num_turns=kw["num_turns"])


# ===========================================================================
# Process comparison (sub tab "Prozessvergleich")
# ===========================================================================

def run_process_comparison(trials, bin_width: float, cache=None):
    """Process wave of each selected trial over its whole measured length.

    ``trials``: [{"trial_id", "vno", "tdms" (path)}]; ``cache``: {trial_id:
    (res, vals)} (the desktop's _ys_cache; analysed trials are not re-read).
    Returns ``(results, errors)``: results = [{trial_id, vno, label ("V001"),
    median (µm, of the binned line), analysis (analyze_process_wave() over the
    whole signal), reality (process_wave_reality_check() or None), visible,
    open_seg_x/open_seg_y (open-spot segment means: position m, µm)}];
    errors = "V003: reason; …" for skipped trials.
    """
    import numpy as np
    from ui.yarnscope.dty_analysis import _moving_average, analyze_series
    from ui.yarnscope.dty_tdms_reader import read_dty_signal, read_step_mm_from_tdms

    cache = cache if cache is not None else {}
    results, errors = [], []
    for trial in trials:
        try:
            trial_id = trial.get("trial_id")
            cached = cache.get(trial_id)
            if cached:
                res, _vals = cached
                y_raw = res.get("_y_raw")
                dx_mm = float(res.get("_dx_mm") or 0.25)
            else:
                res = None
                path = trial.get("tdms")
                y_raw = read_dty_signal(str(path))
                dx_mm = float(read_step_mm_from_tdms(str(path)) or 0.25)
            if y_raw is None or len(y_raw) == 0:
                raise ValueError("No signal")
            y = np.asarray(y_raw, dtype=float)
            # Vergleichswerte sind absichtlich unabhängig von der
            # aktuellen Fensteransicht: immer die ganze Messstrecke.
            yseg = _moving_average(y, 3)
            x = np.arange(len(y)) * dx_mm / 1000.0
            analysis = analyze_process_wave(x, yseg, bin_width)
            if analysis is None:
                raise ValueError("Window too short or incomplete data")
            reality = process_wave_reality_check(x, yseg, bin_width)

            # Öffnungsstellen-Trend (Nutzerwunsch 2026-09-08): braucht
            # dieselbe Knoten/Öffnung-Klassifikation wie der
            # Segmentmittel-Tab (analyze_series()["classes"]) - liegt
            # nur vor, wenn der Trial dort schon einmal analysiert
            # wurde (Cache-Treffer). Sonst hier einmalig nachrechnen,
            # exakt dieselbe Pipeline wie beim "Analyze"-Button.
            cls_info = res.get("classes") if res else None
            if not cls_info:
                cls_info = analyze_series(y, dx_mm, 3).get("classes")
            per_run = (cls_info or {}).get("per_run", [])
            open_seg_x, open_seg_y = opening_segment_series(per_run, yseg, x)

            results.append({
                "trial_id": trial_id, "vno": trial.get("vno"),
                "label": f'V{int(trial.get("vno") or 0):03d}',
                "median": float(np.median(analysis["binned"])),
                "analysis": analysis, "reality": reality, "visible": True,
                "open_seg_x": open_seg_x, "open_seg_y": open_seg_y,
            })
        except Exception as exc:
            errors.append(f'V{int(trial.get("vno") or 0):03d}: {exc}')
    return results, "; ".join(errors)


def comparison_status_text(results, errors: str) -> str:
    """Status line under the comparison button after a run."""
    if results:
        status = (f"{len(results)} trial(s) compared – values over the whole measured "
                  "length, robustness check in independent 10 m sections.")
        if errors:
            status += f" Skipped: {errors}"
    else:
        status = "No comparable results. " + errors
    return status


def comparison_traces(results, normalized: bool = True, show_process_mean: bool = False,
                      show_drift: bool = False, show_open_trend: bool = False,
                      open_roll_mode: str = "Meter", open_roll_amount: float = 1.0) -> list:
    """Lines of the comparison chart, in drawing order.

    Each: {row, trial_id, kind, colour, label, x (m), y (µm, minus the trial's
    median when ``normalized``)}. kind: "process_mean" (binned line, thin
    alpha .45), "drift" (linear drift, lw 1.25), "sine_fit" (dashed, lw 2.1,
    always for visible trials), "open_trend" (dotted, lw 1.6, rolling mean of
    the open-spot segment means). Hidden trials (visible False) have none.
    """
    import numpy as np
    traces = []
    for row, result in enumerate(results):
        analysis = result["analysis"]
        color = COMPARE_COLOURS[row % len(COMPARE_COLOURS)]
        offset = result["median"] if normalized else 0.0
        visible = result.get("visible", True)
        base = {"row": row, "trial_id": result["trial_id"], "colour": color}
        if visible and show_process_mean:
            traces.append(dict(base, kind="process_mean", x=analysis["x"],
                               y=analysis["binned"] - offset,
                               label=f'{result["label"]} process mean'))
        if visible and show_drift:
            traces.append(dict(base, kind="drift", x=analysis["x"],
                               y=analysis["drift_line"] - offset,
                               label=f'{result["label"]} Drift'))
        if visible:
            traces.append(dict(base, kind="sine_fit", x=analysis["x"],
                               y=analysis["fitted"] - offset,
                               label=f'{result["label"]} sine fit'))
        if visible and show_open_trend:
            seg_x, seg_y = result.get("open_seg_x") or [], result.get("open_seg_y") or []
            if seg_x:
                trend_y, _roll_label = roll_trend(seg_x, seg_y, open_roll_mode, open_roll_amount)
                traces.append(dict(base, kind="open_trend", x=seg_x,
                                   y=np.asarray(trend_y) - offset,
                                   label=f'{result["label"]} open spot trend'))
    return traces


def comparison_table_values(result: dict) -> list:
    """Texts of the comparison table from column "Trial" on (13 strings, see
    COMPARE_TABLE_HEADERS[2:]); the last one is the verdict (VERDICT_COLOURS)."""
    analysis = result["analysis"]
    reality = result.get("reality")
    if reality:
        reality_values = [
            f'{reality["significant"]}/{reality["windows"]}',
            f'{reality["lambda_cv"] * 100:.0f} %' if reality["lambda_cv"] is not None else "—",
            f'{reality["amplitude_median"]:.2f}', f'{reality["r2_median"]:.2f}',
            reality["verdict"],
        ]
    else:
        reality_values = ["—", "—", "—", "—", "not enough data"]
    values = [
        result["label"], f'{result["median"]:.1f}',
        f'{analysis["wavelength"]:.2f}', f'{analysis["amplitude"]:.2f}',
        f'{analysis["r_squared"]:.2f}', f'{analysis["spectral_share"] * 100:.0f} %',
        f'{analysis["drift"]:.2f}', f'{analysis["residual_rms"]:.2f}',
    ] + reality_values
    return values


def comparison_axis_labels(normalized: bool, show_process_mean: bool) -> dict:
    """Title and axis labels of the comparison chart."""
    return {"title": ("Sine fits of the process waves" if not show_process_mean
                      else "Process mean and sine fits"),
            "xlabel": "Position [m]",
            "ylabel": "Deviation from median [µm]" if normalized else "Garndicke [µm]"}


# ===========================================================================
# Web helpers: decimation + JSON
# ===========================================================================

def minmax_decimate(x, y, max_points: int = MAX_TRACE_POINTS):
    """Min/max decimation for plotting: at most ``max_points`` points.

    The trace is cut into max_points // 2 equal buckets; each bucket keeps its
    minimum and maximum sample (in original order), so every peak and valley
    stays visible. Shorter traces are returned unchanged. NaN samples are
    ignored (an all-NaN bucket is dropped). Returns ``(x, y)`` numpy arrays.
    """
    import numpy as np
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = min(len(x), len(y))
    x, y = x[:n], y[:n]
    max_points = max(2, int(max_points))
    if n <= max_points:
        return x, y
    buckets = max_points // 2
    edges = np.linspace(0, n, buckets + 1).astype(np.int64)
    nan = np.isnan(y)
    y_lo = np.where(nan, np.inf, y)
    y_hi = np.where(nan, -np.inf, y)
    keep = []
    for s, e in zip(edges[:-1], edges[1:]):
        if e <= s:
            continue
        i_lo = int(s + np.argmin(y_lo[s:e]))
        i_hi = int(s + np.argmax(y_hi[s:e]))
        if nan[i_lo] and nan[i_hi]:
            continue
        a, b = (i_lo, i_hi) if i_lo <= i_hi else (i_hi, i_lo)
        keep.append(a)
        if b != a:
            keep.append(b)
    idx = np.asarray(keep, dtype=np.int64)
    return x[idx], y[idx]


def window_indices(x, x_from=None, x_to=None):
    """``(i0, i1)`` slice of an ascending x array covering [x_from, x_to]."""
    import numpy as np
    x = np.asarray(x, dtype=float)
    i0 = 0 if x_from is None else int(np.searchsorted(x, float(x_from), side="left"))
    i1 = len(x) if x_to is None else int(np.searchsorted(x, float(x_to), side="right"))
    return i0, max(i0, i1)


def trace_json(x, y, x_from=None, x_to=None, max_points: int = MAX_TRACE_POINTS) -> dict:
    """One plot trace for the web: optional [x_from, x_to] window at full
    resolution, then min/max decimation. ``{x, y, n_source, decimated}``."""
    import numpy as np
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    i0, i1 = window_indices(x, x_from, x_to)
    xs, ys = x[i0:i1], y[i0:i1]
    dx, dy = minmax_decimate(xs, ys, max_points)
    return {"x": _floats(dx), "y": _floats(dy), "n_source": int(len(xs)),
            "decimated": bool(len(dx) < len(xs))}


def signal_trace(res: dict, x_from=None, x_to=None, max_points: int = MAX_TRACE_POINTS):
    """Whole smoothed signal (as the Signal tab: µm, k=3 over the full
    length) for overview/zoom: x in m (sample i at i * dx), windowed to
    [x_from, x_to] at full resolution, then decimated (trace_json()).
    Adds ``dx_mm`` and ``total_m``. None without signal."""
    import numpy as np
    smoothed = smoothed_signal_um(res)
    if smoothed is None:
        return None
    y_smooth, dx_mm = smoothed
    x = np.arange(len(y_smooth)) * dx_mm / 1000.0
    out = trace_json(x, y_smooth, x_from, x_to, max_points)
    out.update({"dx_mm": dx_mm, "total_m": len(y_smooth) * dx_mm / 1000.0})
    return out


def jsonable(obj):
    """numpy -> Python, NaN/inf -> None, Path -> str, recursively."""
    import numpy as np
    if obj is None or isinstance(obj, (bool, str)):
        return obj
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        f = float(obj)
        return f if math.isfinite(f) else None
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, np.ndarray):
        return [jsonable(v) for v in obj.tolist()]
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    return str(obj)


def _floats(arr):
    return [(float(v) if math.isfinite(v) else None) for v in (float(a) for a in arr)]


def result_json(res: dict, vals: dict) -> dict:
    """JSON summary of one analysed trial (numbers/texts of the tab).

    ``vals``: tbllabordtyomat column -> value (what "Save to DB" writes);
    ``metrics_card``: the green box [{label, key, decimals, unit, value}];
    ``stab``: [{key, label (load), value %}] for predictions present;
    ``status_text``; ``thresholds`` {T, cb (= T - tA), ba (= T - tB)} in µm;
    ``n_points``, ``dx_mm``, ``total_m``; ``pie`` {A, B, C} %;
    ``res``: scalar entries of the analyze_series result (arrays left out).
    """
    T, y_cb, y_ba = thresholds(res)
    y_raw = res.get("_y_raw")
    n = 0 if y_raw is None else len(y_raw)
    dx_mm = float(res.get("_dx_mm") or 0.25)
    import numpy as np
    scalars = {k: v for k, v in res.items()
               if not str(k).startswith("_")
               and (v is None or isinstance(v, (bool, int, float, str, np.generic)))}
    return jsonable({
        "vals": vals,
        "metrics_card": [{"label": lb, "key": k, "decimals": d, "unit": u, "value": vals.get(k)}
                         for lb, k, d, u in METRICS_CARD],
        "stab": [{"key": k, "label": lb, "value": vals.get(k)} for k, lb in STAB_KEYS
                 if vals.get(k) is not None],
        "status_text": analysis_status_text(vals),
        "thresholds": {"T": T, "cb": y_cb, "ba": y_ba},
        "n_points": n, "dx_mm": dx_mm, "total_m": n * dx_mm / 1000.0,
        "pie": pie_values(vals),
        "res": scalars,
    })


def segment_view_json(view: dict, max_points: int = MAX_TRACE_POINTS) -> dict:
    """segment_view() for the web. ``line`` = grey smoothed signal (decimated);
    ``open_segments`` [[x0, x1, mean]] and ``knot_segments`` [[x0, x1, mean,
    class]] = horizontal segment lines from first to last sample (m, µm);
    ``x_range`` = [start, start + window] (the desktop's x limits)."""
    if view is None:
        return None
    x = view["x"]

    def _seg(g):
        return float(x[int(g[0])]), float(x[int(g[-1])])

    out = {
        "total_m": view["total_m"], "start_m": view["start_m"], "window_m": view["window_m"],
        "dx_mm": view["dx_mm"],
        "x_range": [view["start_m"], view["start_m"] + view["window_m"]],
        "line": trace_json(x, view["y_smooth"], max_points=max_points),
        "open_segments": [[*_seg(g), mv] for g, mv in view["open_segments"] if len(g)],
        "knot_segments": [[*_seg(g), mv, cls] for (g, mv), cls
                          in zip(view["knot_segments"], view["knot_classes"]) if len(g)],
        "counts": view["counts"],
        "thresholds": {"T": view["threshold"], "cb": view["y_cb"], "ba": view["y_ba"]},
        "trends": {k: dict(t, colour=TREND_COLOURS[k], title=TREND_TITLES[k])
                   for k, t in view["trends"].items()},
        "process_wave": view["process_wave"],
        "pie": view["pie"],
        "colours": {"line": COLOR_SIGNAL_LINE, "open": COLOR_OPEN_SEGMENT, "abc": COLOR_ABC,
                    "process_mean": PROCESS_WAVE_COLOURS["binned"],
                    "sine_fit": PROCESS_WAVE_COLOURS["fitted"]},
    }
    return jsonable(out)


def signal_view_json(view: dict, max_points: int = MAX_TRACE_POINTS) -> dict:
    """signal_view() for the web: bars (left edge x, width step_m) decimated
    with min/max, threshold lines and the desktop's axis limits."""
    if view is None:
        return None
    try:
        ylim, xlim = signal_limits(view)
    except Exception:
        ylim, xlim = None, None
    return jsonable({
        "bars": trace_json(view["x"], view["y"], max_points=max_points),
        "step_m": view["step_m"], "start_m": view["start_m"], "window_m": view["window_m"],
        "total_m": view["total_m"], "dx_mm": view["dx_mm"],
        "thresholds": {"T": view["threshold"], "ab": view["y_ab"], "bc": view["y_bc"]},
        "ylim": ylim, "xlim": xlim,
    })


def garnspiegel_json(geom: dict) -> dict:
    """garnspiegel_dty_geometry() for the web: per row ``base``, ``half``
    (list, one value per sample, x = i * dx in mm) and ``spans`` [[i0, i1,
    class]] (i1 exclusive; class "" = open = white, A/B/C = COLOR_ABC)."""
    if geom is None:
        return None
    rows = []
    for r in geom["rows"]:
        kc = list(r["knot_class"])
        spans, i0 = [], 0
        for i in range(1, len(kc) + 1):
            if i == len(kc) or kc[i] != kc[i0]:
                spans.append([i0, i, kc[i0]])
                i0 = i
        rows.append({"base": r["base"], "half": r["half"], "spans": spans})
    x0 = geom["rows"][0]["x"] if geom["rows"] else []
    return jsonable({
        "rows": rows, "turns": geom["turns"], "pts_per_row": geom["pts_per_row"],
        "x_step_mm": (float(x0[1] - x0[0]) if len(x0) > 1 else geom["seg_len_mm"]),
        "seg_len_mm": geom["seg_len_mm"], "row_h": geom["row_h"],
        "xlim": geom["xlim"], "ylim": geom["ylim"],
        "colours": {"open": "white", "open_alpha": 0.88, "abc": COLOR_ABC, "abc_alpha": 0.92,
                    "background": "black"},
    })


def comparison_json(results, normalized: bool = True, show_process_mean: bool = False,
                    show_drift: bool = False, show_open_trend: bool = False,
                    open_roll_mode: str = "Meter", open_roll_amount: float = 1.0,
                    max_points: int = MAX_TRACE_POINTS) -> dict:
    """Comparison chart + table for the web (same options as the desktop)."""
    traces = comparison_traces(results, normalized, show_process_mean, show_drift,
                               show_open_trend, open_roll_mode, open_roll_amount)
    rows = []
    for row, result in enumerate(results):
        a = result["analysis"]
        rows.append({
            "trial_id": result["trial_id"], "vno": result["vno"], "label": result["label"],
            "colour": COMPARE_COLOURS[row % len(COMPARE_COLOURS)],
            "visible": result.get("visible", True), "median": result["median"],
            "analysis": {k: a[k] for k in ("wavelength", "amplitude", "r_squared", "spectral_share",
                                           "drift", "residual_rms", "bin_width", "span")},
            "reality": result.get("reality"),
            "table": comparison_table_values(result),
        })
    return jsonable({
        "rows": rows,
        "headers": COMPARE_TABLE_HEADERS[2:],
        "verdict_colours": VERDICT_COLOURS,
        "traces": [dict({k: t[k] for k in ("row", "trial_id", "kind", "colour", "label")},
                        **trace_json(t["x"], t["y"], max_points=max_points)) for t in traces],
        "axis": comparison_axis_labels(normalized, show_process_mean),
    })
