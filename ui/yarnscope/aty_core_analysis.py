"""
aty_core_analysis.py – core-baseline and loop analysis for ATY yarn.

Independent algorithm path, separate from thick_spot_analysis.py (existing
method: global mean as core) and completely separate from the DTY analysis
(dty_analysis.py, Otsu threshold/hysteresis) – this module changes neither
of the two existing paths.

Core definition: rolling lower percentile (local lower envelope) instead of
a global mean, since loops only ever push the shadow width up. Loop
detection via scipy.signal.find_peaks with a prominence + minimum-distance
criterion (more robust than a simple threshold-run, which counts unstably
around notches within a single loop).

Default parameters derived/validated in conversation on 2026-08-12
(TrialSeries 288, trials 1 + 12).
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np
from scipy.ndimage import percentile_filter
from scipy.signal import find_peaks, peak_prominences

# Default parameters (see module docstring)
CORE_WINDOW_MM = 40.0
CORE_PERCENTILE = 10.0
PEAK_PROMINENCE_MM = 0.03
PEAK_MIN_DIST_MM = 1.0

# Bumped whenever any of the constants above (or the core loop-detection
# logic itself) changes in a way that would make old results not directly
# comparable to new ones. Persisted alongside saved DB rows (tblLaborATYoMat.
# ParamsVersion) so a future recalibration or historical comparison can tell
# which analysis version produced a given row instead of silently mixing
# incompatible numbers.
PARAMS_VERSION = "v1-2026-08-13"

# Loop-shape bin split -- same threshold/terminology as the existing
# Bin1 "Kurzhocker" (short & steep) / Bin2 "Langwelle" (long & flat) split
# in thick_spot_analysis.py, so the two tabs speak the same language. Numbers
# won't match exactly between the two tabs though: this module detects loops
# via find_peaks on the core baseline, thick_spot_analysis.py via a
# threshold-run against the global mean.
BIN_THRESHOLD_UM_PER_MM = 100.0

# Bin widths for the two-scale core-unevenness metric (a simplified take on
# the classic textile "CV at different cut lengths" idea): how much the core
# diameter drifts meter-to-meter vs. over tens of meters.
SHORT_WAVE_BIN_MM = 1_000.0    # 1 m
LONG_WAVE_BIN_MM = 20_000.0    # 20 m


def _binned_cv(baseline_mm: np.ndarray, mm_per_point: float, bin_mm: float) -> float:
    """CV (%) of the core baseline's mean value across bin_mm-wide segments.

    Small bin_mm -> meter-to-meter unevenness; large bin_mm -> long-range
    drift. NaN if the trial isn't long enough for at least 2 full bins.
    """
    bin_pts = max(1, int(round(bin_mm / mm_per_point)))
    n_full = (baseline_mm.size // bin_pts) * bin_pts
    if n_full < 2 * bin_pts:
        return float("nan")
    means = baseline_mm[:n_full].reshape(-1, bin_pts).mean(axis=1)
    if means.mean() == 0:
        return float("nan")
    return float(100 * means.std() / means.mean())


def compute_core_baseline(arr_mm: np.ndarray, mm_per_point: float,
                           window_mm: float = CORE_WINDOW_MM,
                           percentile: float = CORE_PERCENTILE) -> np.ndarray:
    """Local core baseline (lower envelope) via rolling percentile.

    Window width should be well above the longest expected loop, so that
    individual long loops don't pull the baseline upward (default 40mm
    covers even P99 outliers on TrialSeries 288).
    """
    win_pts = max(3, int(round(window_mm / mm_per_point)))
    if win_pts % 2 == 0:
        win_pts += 1
    return percentile_filter(arr_mm, percentile=percentile, size=win_pts, mode="nearest")


def get_zoom_segment(arr_mm: np.ndarray, mm_per_point: float, start_mm: float,
                      window_mm: float = 40.0,
                      core_window_mm: float = CORE_WINDOW_MM,
                      core_percentile: float = CORE_PERCENTILE):
    """Returns (pos_mm, raw_mm, baseline_mm) for a short window starting at start_mm.

    Computes the core baseline on a locally padded slice (padded by
    core_window_mm on each side) instead of requiring the full-length
    baseline for the whole trial in memory -- cheap enough to call per
    render, avoids caching multi-million-point arrays per trial.
    """
    arr = np.asarray(arr_mm, dtype=float)
    n = arr.size
    start_idx = max(0, min(n - 1, int(round(start_mm / mm_per_point))))
    win_pts = max(1, int(round(window_mm / mm_per_point)))
    pad_pts = max(1, int(round(core_window_mm / mm_per_point)))
    lo = max(0, start_idx - pad_pts)
    hi = min(n, start_idx + win_pts + pad_pts)
    local = arr[lo:hi]
    local_baseline = compute_core_baseline(local, mm_per_point, core_window_mm, core_percentile)
    off = start_idx - lo
    end = min(len(local), off + win_pts)
    raw_seg = local[off:end]
    base_seg = local_baseline[off:end]
    pos_mm = (np.arange(len(raw_seg)) + start_idx) * mm_per_point
    return pos_mm, raw_seg, base_seg


def analyze_trial(arr_mm: np.ndarray, mm_per_point: float,
                   window_mm: float = CORE_WINDOW_MM,
                   percentile: float = CORE_PERCENTILE,
                   prominence_mm: float = PEAK_PROMINENCE_MM,
                   min_dist_mm: float = PEAK_MIN_DIST_MM,
                   ellipticity_pct: np.ndarray | None = None) -> Dict[str, Any]:
    """Core and loop metrics for a single ATY trial.

    Returns a dict with scalar metrics (for tables) plus the raw
    distribution arrays (for histograms): spacing_mm, rel_height_pct.

    ellipticity_pct: optional, same length as arr_mm - per-point relative
    asymmetry between a dual-axis device's two 90°-offset sensors (see
    dty_tdms_reader.read_aty_signal()). None for a standard single-axis
    trial (the vast majority today), in which case the ellipticity_* result
    keys are NaN. When provided, split into "inside a detected loop" vs.
    "core" using the same peak regions (left_bases/right_bases) already
    computed below for the bulk-index calculation - a genuinely new signal a
    single-axis device can't provide: whether loops are measurably more
    asymmetric than the surrounding core, not just a smoothed/combined
    diameter reading.
    """
    arr = np.asarray(arr_mm, dtype=float)
    baseline = compute_core_baseline(arr, mm_per_point, window_mm, percentile)

    global_mean_mm = float(arr.mean())
    core_mean_mm = float(baseline.mean())
    core_cv_pct = float(100 * baseline.std() / baseline.mean()) if core_mean_mm else float("nan")
    delta_pct = (100 * (core_mean_mm - global_mean_mm) / global_mean_mm) if global_mean_mm else float("nan")

    excess = arr - baseline
    excess_um = excess * 1000.0
    min_dist_pts = max(1, int(round(min_dist_mm / mm_per_point)))
    idx, _ = find_peaks(excess, prominence=prominence_mm, distance=min_dist_pts)

    length_m = arr.size * mm_per_point / 1000.0
    peak_pos_mm = idx * mm_per_point
    heights_um = excess[idx] * 1000.0
    local_core_um = baseline[idx] * 1000.0
    rel_height_pct = np.divide(heights_um, local_core_um, out=np.zeros_like(heights_um),
                                where=local_core_um > 0) * 100.0
    spacing_mm = np.diff(peak_pos_mm)

    n_peaks = int(len(idx))
    has_peaks = n_peaks > 0
    has_spacing = len(spacing_mm) > 0

    # Loop extent (length/area/shape) -- peak_prominences' left/right bases
    # approximate where each loop rises out of / returns to the surrounding
    # signal, giving a usable "loop boundary" without a separate detector.
    # For closely-spaced peaks these bases can extend well past the midpoint
    # to the next peak (the "reference level" search keeps going until it
    # clears a taller neighbour), so adjacent loops' extents can overlap --
    # observed as >1000% "length coverage" before this fix. Clip each base to
    # the midpoint with its neighbour so loop extents never overlap.
    if has_peaks:
        _prom, left_bases, right_bases = peak_prominences(excess, idx)
        left_bases = left_bases.astype(np.int64)
        right_bases = right_bases.astype(np.int64)
        if n_peaks > 1:
            mids = (idx[:-1] + idx[1:]) // 2
            right_bases[:-1] = np.minimum(right_bases[:-1], mids)
            left_bases[1:] = np.maximum(left_bases[1:], mids)
        length_per_peak_mm = np.maximum(
            (right_bases - left_bases) * mm_per_point, mm_per_point)
        area_per_peak_um_mm = np.array([
            float(np.trapezoid(excess_um[l:r + 1]) * mm_per_point)
            for l, r in zip(left_bases, right_bases)
        ])
        steepness_um_per_mm = np.divide(
            heights_um, length_per_peak_mm,
            out=np.zeros_like(heights_um), where=length_per_peak_mm > 0)
        bin_id = np.where(steepness_um_per_mm > BIN_THRESHOLD_UM_PER_MM, 1, 2)
        n_bin1 = int(np.sum(bin_id == 1))
        n_bin2 = int(np.sum(bin_id == 2))
        # % of loop area vs. the area a perfectly flat core of the same
        # length would have -- unit-independent, self-normalizing (no
        # arbitrary scaling constant), and lands in a readable range (roughly
        # 0-100 for typical ATY yarn) once loop extents don't overlap.
        core_area_equiv_um_mm = core_mean_mm * 1000.0 * arr.size * mm_per_point
        bulk_index_pct = (100.0 * area_per_peak_um_mm.sum() / core_area_equiv_um_mm
                           if core_area_equiv_um_mm else float("nan"))

        # Count alone conflates "many small loops" with "few big ones" --
        # per-bin height tells the two apart, and per-bin bulk contribution
        # (count AND size fused into one number, same idea as the overall
        # Bulk Index but split by loop type) shows which loop type actually
        # drives a yarn's bulk.
        def _bin_stats(mask):
            n = int(mask.sum())
            return {
                "n": n,
                "height_median_um": float(np.median(heights_um[mask])) if n else float("nan"),
                "rel_height_median_pct": float(np.median(rel_height_pct[mask])) if n else float("nan"),
                "bulk_pct": (100.0 * area_per_peak_um_mm[mask].sum() / core_area_equiv_um_mm
                             if n and core_area_equiv_um_mm else 0.0),
            }
        bin1_stats = _bin_stats(bin_id == 1)
        bin2_stats = _bin_stats(bin_id == 2)
    else:
        length_per_peak_mm = np.array([])
        area_per_peak_um_mm = np.array([])
        bin_id = np.array([])
        n_bin1 = n_bin2 = 0
        bulk_index_pct = 0.0
        bin1_stats = bin2_stats = {"n": 0, "height_median_um": float("nan"),
                                    "rel_height_median_pct": float("nan"), "bulk_pct": 0.0}

    core_cv_short_pct = _binned_cv(baseline, mm_per_point, SHORT_WAVE_BIN_MM)
    core_cv_long_pct = _binned_cv(baseline, mm_per_point, LONG_WAVE_BIN_MM)

    if ellipticity_pct is not None:
        ell = np.asarray(ellipticity_pct, dtype=float)
        ellipticity_mean_pct = float(np.nanmean(ell)) if ell.size else float("nan")
        if has_peaks:
            in_loop = np.zeros(arr.size, dtype=bool)
            for l, r in zip(left_bases, right_bases):
                in_loop[l:r + 1] = True
            loop_vals = ell[in_loop]
            core_vals = ell[~in_loop]
            ellipticity_loop_mean_pct = float(np.nanmean(loop_vals)) if loop_vals.size else float("nan")
            ellipticity_core_mean_pct = float(np.nanmean(core_vals)) if core_vals.size else float("nan")
            ellipticity_loop_vs_core_ratio = (
                ellipticity_loop_mean_pct / ellipticity_core_mean_pct
                if ellipticity_core_mean_pct else float("nan")
            )
        else:
            ellipticity_loop_mean_pct = float("nan")
            ellipticity_core_mean_pct = ellipticity_mean_pct
            ellipticity_loop_vs_core_ratio = float("nan")
    else:
        ellipticity_mean_pct = float("nan")
        ellipticity_loop_mean_pct = float("nan")
        ellipticity_core_mean_pct = float("nan")
        ellipticity_loop_vs_core_ratio = float("nan")

    def _pct(v):
        return round(v, 1) if np.isfinite(v) else float("nan")

    return {
        "params_version": PARAMS_VERSION,
        "n_points": int(arr.size),
        "length_m": length_m,
        "global_mean_um": round(global_mean_mm * 1000, 1),
        "core_mean_um": round(core_mean_mm * 1000, 1),
        "core_cv_pct": round(core_cv_pct, 2) if np.isfinite(core_cv_pct) else float("nan"),
        "delta_pct": round(delta_pct, 1) if np.isfinite(delta_pct) else float("nan"),
        "n_peaks": n_peaks,
        "density_per_m": round(n_peaks / length_m, 1) if length_m else float("nan"),
        "spacing_mean_mm": round(float(spacing_mm.mean()), 3) if has_spacing else float("nan"),
        "spacing_cv_pct": round(float(100 * spacing_mm.std() / spacing_mm.mean()), 1) if has_spacing else float("nan"),
        "height_median_um": round(float(np.median(heights_um)), 1) if has_peaks else float("nan"),
        "height_mean_um": round(float(heights_um.mean()), 1) if has_peaks else float("nan"),
        "height_p95_um": round(float(np.percentile(heights_um, 95)), 1) if has_peaks else float("nan"),
        "height_p99_um": round(float(np.percentile(heights_um, 99)), 1) if has_peaks else float("nan"),
        "height_max_um": round(float(heights_um.max()), 1) if has_peaks else float("nan"),
        "rel_height_median_pct": round(float(np.median(rel_height_pct)), 1) if has_peaks else float("nan"),
        "rel_height_mean_pct": round(float(rel_height_pct.mean()), 1) if has_peaks else float("nan"),
        "rel_height_p90_pct": round(float(np.percentile(rel_height_pct, 90)), 1) if has_peaks else float("nan"),
        "rel_height_p95_pct": round(float(np.percentile(rel_height_pct, 95)), 1) if has_peaks else float("nan"),
        "rel_height_p99_pct": round(float(np.percentile(rel_height_pct, 99)), 1) if has_peaks else float("nan"),
        "rel_height_max_pct": round(float(rel_height_pct.max()), 1) if has_peaks else float("nan"),
        # Loop shape / bulk:
        "bulk_index_pct": round(bulk_index_pct, 1) if np.isfinite(bulk_index_pct) else float("nan"),
        "bin1_pct": round(100.0 * n_bin1 / n_peaks, 1) if has_peaks else float("nan"),
        "bin2_pct": round(100.0 * n_bin2 / n_peaks, 1) if has_peaks else float("nan"),
        "bin1_density_per_m": round(n_bin1 / length_m, 1) if length_m else float("nan"),
        "bin2_density_per_m": round(n_bin2 / length_m, 1) if length_m else float("nan"),
        # Per-bin "quality" (size), not just count -- tells apart "many small
        # loops" from "few big ones" within each loop type:
        "bin1_height_median_um": _pct(bin1_stats["height_median_um"]),
        "bin1_rel_height_median_pct": _pct(bin1_stats["rel_height_median_pct"]),
        "bin1_bulk_pct": _pct(bin1_stats["bulk_pct"]),
        "bin2_height_median_um": _pct(bin2_stats["height_median_um"]),
        "bin2_rel_height_median_pct": _pct(bin2_stats["rel_height_median_pct"]),
        "bin2_bulk_pct": _pct(bin2_stats["bulk_pct"]),
        # Two-scale core unevenness:
        "core_cv_short_pct": _pct(core_cv_short_pct),
        "core_cv_long_pct": _pct(core_cv_long_pct),
        # Dual-axis ellipticity (NaN for a single-axis trial, see the
        # ellipticity_pct parameter docstring above):
        "ellipticity_mean_pct": _pct(ellipticity_mean_pct),
        "ellipticity_loop_mean_pct": _pct(ellipticity_loop_mean_pct),
        "ellipticity_core_mean_pct": _pct(ellipticity_core_mean_pct),
        "ellipticity_loop_vs_core_ratio": (
            round(ellipticity_loop_vs_core_ratio, 2)
            if np.isfinite(ellipticity_loop_vs_core_ratio) else float("nan")
        ),
        # Raw data for histograms:
        "spacing_mm": spacing_mm,
        "rel_height_pct": rel_height_pct,
        "length_per_peak_mm": length_per_peak_mm,
        "area_per_peak_um_mm": area_per_peak_um_mm,
        "bin_id": bin_id,
    }


# ---------------------------------------------------------------------------
# tblLaborATYoMat persistence -- scalar-only subset of analyze_trial()'s
# output (no raw per-loop arrays), one row per trial. Single source of truth
# for the DB column mapping so ui/aty_yarnscope_tab.py (single-trial "In DB
# speichern") and ui/screen_aty_batch.py (batch save) can't drift apart.
# ---------------------------------------------------------------------------

# Python dict key -> tblLaborATYoMat column name. Deliberately excludes the
# 5 radar-axis scores (volume/frequency/character/evenness/outliers): those
# are derived from RADAR_BOUNDS, which gets recalibrated over time (see
# suggest_radar_bounds) -- storing them would freeze old rows to whatever
# calibration was active when saved. Recompute via compute_radar_scores()
# from the stored raw metrics instead, using the calibration that's current
# whenever you need them.
DB_COLUMN_MAP: Dict[str, str] = {
    "params_version": "ParamsVersion",
    "length_m": "LengthM",
    "global_mean_um": "GlobalMeanUm",
    "core_mean_um": "CoreMeanUm",
    "core_cv_pct": "CoreCVPct",
    "delta_pct": "DeltaPct",
    "core_cv_short_pct": "CoreCVShortPct",
    "core_cv_long_pct": "CoreCVLongPct",
    "n_peaks": "NPeaks",
    "density_per_m": "DensityPerM",
    "spacing_mean_mm": "SpacingMeanMm",
    "spacing_cv_pct": "SpacingCVPct",
    "height_median_um": "HeightMedianUm",
    "height_mean_um": "HeightMeanUm",
    "height_p95_um": "HeightP95Um",
    "height_p99_um": "HeightP99Um",
    "height_max_um": "HeightMaxUm",
    "rel_height_median_pct": "RelHeightMedianPct",
    "rel_height_mean_pct": "RelHeightMeanPct",
    "rel_height_p90_pct": "RelHeightP90Pct",
    "rel_height_p95_pct": "RelHeightP95Pct",
    "rel_height_p99_pct": "RelHeightP99Pct",
    "rel_height_max_pct": "RelHeightMaxPct",
    "bulk_index_pct": "BulkIndexPct",
    "bin1_pct": "Bin1Pct",
    "bin2_pct": "Bin2Pct",
    "bin1_density_per_m": "Bin1DensityPerM",
    "bin2_density_per_m": "Bin2DensityPerM",
    "bin1_height_median_um": "Bin1HeightMedianUm",
    "bin1_rel_height_median_pct": "Bin1RelHeightMedianPct",
    "bin1_bulk_pct": "Bin1BulkPct",
    "bin2_height_median_um": "Bin2HeightMedianUm",
    "bin2_rel_height_median_pct": "Bin2RelHeightMedianPct",
    "bin2_bulk_pct": "Bin2BulkPct",
    "ellipticity_mean_pct": "EllipticityMeanPct",
    "ellipticity_loop_mean_pct": "EllipticityLoopMeanPct",
    "ellipticity_core_mean_pct": "EllipticityCoreMeanPct",
    "ellipticity_loop_vs_core_ratio": "EllipticityLoopVsCoreRatio",
}
DB_COLUMNS: List[str] = list(DB_COLUMN_MAP.values())


def to_db_row(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Converts an analyze_trial() result to {DB column name: value},
    ready to INSERT/UPDATE into tblLaborATYoMat (plus TrialID/Timestamp,
    which the caller supplies)."""
    return {db_col: stats.get(py_key) for py_key, db_col in DB_COLUMN_MAP.items()}


def from_db_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Reverse of to_db_row(): converts a {DB column name: value} dict (e.g.
    a row fetched from tblLaborATYoMat) back to the python-key shape that
    suggest_radar_bounds()/compute_radar_scores() expect - lets a
    recalibration batch reuse already-saved trials instead of re-reading
    their TDMS file. Only the scalar subset DB_COLUMN_MAP covers comes back;
    the raw per-loop arrays analyze_trial() also returns (spacing_mm,
    rel_height_pct, ...) aren't persisted, so a DB-sourced result can't feed
    anything that needs those (e.g. histograms) - fine for
    suggest_radar_bounds()/compute_radar_scores(), which only touch scalars.
    """
    return {py_key: row.get(db_col) for py_key, db_col in DB_COLUMN_MAP.items()}


# ---------------------------------------------------------------------------
# Radar chart -- 5-axis "yarn fingerprint"
# ---------------------------------------------------------------------------
# Chosen from a correlation check across the 5+ candidate characteristics
# discussed in conversation on 2026-08-12 (n=38 real trials, TrialSeries
# 270+288): most texture metrics (bulk, Kurzhocker-bulk-share, core CV,
# P99 height) move together in that sample -- likely because process
# parameters (pressure/jet) dominate. Density-per-metre was the one clearly
# independent axis; Kurzhocker-COUNT-share, Spacing-CV, and the P99/median
# height ratio were the least redundant of the rest, so those five became
# the axes rather than e.g. Kurzhocker-bulk-share or a Core-CV composite.
RADAR_AXES = ["volume", "frequency", "character", "evenness", "outliers"]

RADAR_LABELS = {
    "volume": "Volume",
    "frequency": "Frequency",
    "character": "Character",
    "evenness": "Evenness",
    "outliers": "Outliers",
}

# Fixed calibration "v1", derived 2026-08-12 from n=38 real ATY trials
# (TrialSeries 270 + 288) via suggest_radar_bounds() with a generous ~50-70%
# padding on top of the observed min/max (deliberately more headroom than a
# tight percentile pad, since n=38 from two series is a narrow starting
# sample) -- so an axis doesn't already sit at the 0/100 edge for every
# trial seen so far, leaving room for genuinely more extreme future yarns.
# Recalibrate via suggest_radar_bounds() once a larger/more varied batch of
# trials is available (see that function's docstring) and update these
# constants by hand -- deliberately not automatic, so a rescale is a
# reviewed, visible change rather than one that silently shifts what
# earlier radar charts meant.
RADAR_BOUNDS: Dict[str, Tuple[float, float]] = {
    "volume": (5.0, 40.0),        # Bulk Index [%]
    "frequency": (250.0, 600.0),  # loops / m
    "character": (5.0, 95.0),     # Kurzhocker share of loop COUNT [%]
    "evenness": (25.0, 55.0),     # Spacing CV [%] -- inverted: low CV -> high score
    "outliers": (1.5, 4.0),       # P99 / median relative-height ratio
}


def _radar_score(value: float, lo: float, hi: float, invert: bool = False) -> float:
    if value is None or not np.isfinite(value):
        return float("nan")
    frac = (value - lo) / (hi - lo) if hi != lo else 0.0
    frac = min(1.0, max(0.0, frac))
    if invert:
        frac = 1.0 - frac
    return round(100.0 * frac, 1)


def compute_radar_scores(stats: Dict[str, Any],
                          bounds: Dict[str, Tuple[float, float]] = None) -> Dict[str, float]:
    """Maps an analyze_trial() result to 5 normalized 0-100 axis scores.

    Pass a custom `bounds` dict (same shape as RADAR_BOUNDS) to score against
    a different calibration than the current default, e.g. one freshly
    produced by suggest_radar_bounds(). A NaN axis (e.g. too few loops for a
    meaningful P99/median ratio) stays NaN -- callers should skip/gray out
    that axis rather than plot it as 0.
    """
    b = bounds or RADAR_BOUNDS
    median = stats.get("rel_height_median_pct")
    p99 = stats.get("rel_height_p99_pct")
    outlier_ratio = (p99 / median) if median else float("nan")

    lo, hi = b["volume"]
    lo_f, hi_p = b["frequency"]
    lo_c, hi_c = b["character"]
    lo_e, hi_e = b["evenness"]
    lo_o, hi_o = b["outliers"]
    return {
        "volume": _radar_score(stats.get("bulk_index_pct"), lo, hi),
        "frequency": _radar_score(stats.get("density_per_m"), lo_f, hi_p),
        "character": _radar_score(stats.get("bin1_pct"), lo_c, hi_c),
        "evenness": _radar_score(stats.get("spacing_cv_pct"), lo_e, hi_e, invert=True),
        "outliers": _radar_score(outlier_ratio, lo_o, hi_o),
    }


def format_radar_raw_values(stats: Dict[str, Any]) -> Dict[str, str]:
    """The un-normalized number behind each of the 5 radar axes, formatted
    with its unit (e.g. "22.4%", "412/m", "2.1x") -- for display next to the
    0-100 score, since that score alone doesn't tell you the actual reading.
    "-" for an axis that couldn't be computed (e.g. too few loops for a
    meaningful P99/median ratio), mirroring compute_radar_scores()' NaN.
    """
    median = stats.get("rel_height_median_pct")
    p99 = stats.get("rel_height_p99_pct")
    outlier_ratio = (p99 / median) if median else float("nan")

    def _fmt(value, suffix: str, decimals: int = 1) -> str:
        if value is None or not np.isfinite(value):
            return "-"
        return f"{value:.{decimals}f}{suffix}"

    return {
        "volume": _fmt(stats.get("bulk_index_pct"), "%"),
        "frequency": _fmt(stats.get("density_per_m"), "/m", decimals=0),
        "character": _fmt(stats.get("bin1_pct"), "%"),
        "evenness": _fmt(stats.get("spacing_cv_pct"), "% CV"),
        "outliers": _fmt(outlier_ratio, "x", decimals=2),
    }


def suggest_radar_bounds(results: List[Dict[str, Any]],
                          pad_frac: float = 0.3) -> Dict[str, Tuple[float, float]]:
    """Recalibration helper: given analyze_trial() results from a
    larger/newer batch of trials, suggests updated RADAR_BOUNDS entries.

    Returns {axis: (lo, hi)} from the observed min/max, padded by pad_frac
    of the observed span on each side (default 30%). Inspect the result and
    update RADAR_BOUNDS by hand -- intentionally not applied automatically
    (see RADAR_BOUNDS docstring for why).

    Example (run from a scratch script, not part of the app UI):
        from ui.yarnscope.aty_core_analysis import analyze_trial, suggest_radar_bounds
        results = [analyze_trial(arr, mm_pp) for arr, mm_pp in <every trial you have>]
        print(suggest_radar_bounds(results))
    """
    raw: Dict[str, List[float]] = {axis: [] for axis in RADAR_AXES}
    for r in results:
        median = r.get("rel_height_median_pct")
        p99 = r.get("rel_height_p99_pct")
        raw["volume"].append(r.get("bulk_index_pct"))
        raw["frequency"].append(r.get("density_per_m"))
        raw["character"].append(r.get("bin1_pct"))
        raw["evenness"].append(r.get("spacing_cv_pct"))
        raw["outliers"].append((p99 / median) if median else float("nan"))

    bounds: Dict[str, Tuple[float, float]] = {}
    for axis, vals in raw.items():
        arr = np.array([v for v in vals if v is not None and np.isfinite(v)])
        if arr.size == 0:
            continue
        lo, hi = float(arr.min()), float(arr.max())
        span = hi - lo
        bounds[axis] = (round(lo - pad_frac * span, 2), round(hi + pad_frac * span, 2))
    return bounds


# ---------------------------------------------------------------------------
# Plain-language yarn description, one sentence per trial
# ---------------------------------------------------------------------------
# Rule-based: each radar axis score (0-100, see compute_radar_scores) maps to
# one of 5 bands, each with its own wording. Deliberately a single flowing
# sentence, not "axis: value" -- the whole point is to read like someone
# describing the yarn, not reciting the chart.

_VOLUME_WORDS = [
    "a very flat, minimal-bulk",
    "a fairly delicate",
    "a moderately voluminous",
    "a voluminous",
    "an extremely voluminous, very fluffy",
]
_FREQUENCY_WORDS = [
    "sparse", "loosely spaced", "moderately dense", "densely packed", "extremely densely packed",
]
_CHARACTER_WORDS = [
    "clearly dominated by long, gentle arcs",
    "leaning toward long, gentle arcs",
    "a balanced mix of sharp spikes and gentle arcs",
    "leaning toward sharp, short spikes",
    "clearly dominated by sharp, short spikes",
]
_EVENNESS_WORDS = [
    "very irregular", "somewhat irregular", "moderately even", "fairly even", "very even",
]
_OUTLIER_WORDS = [
    "virtually no outlier loops",
    "only mild outlier loops",
    "a few outlier loops",
    "several notably larger outlier loops",
    "occasional dramatic, oversized outlier loops",
]


def _band(score: float, n: int = 5) -> int:
    if not np.isfinite(score):
        return n // 2  # treat unknown as "moderate" rather than crashing the sentence
    return min(n - 1, max(0, int(score // (100.0 / n))))


def describe_yarn(scores: Dict[str, float]) -> str:
    """Turns 5 radar-axis scores (0-100, from compute_radar_scores) into a
    single plain-language descriptive sentence, e.g.:

        "A voluminous yarn with densely packed loops, leaning toward sharp,
        short spikes, moderately even spacing, and only mild outlier loops."

    Purely a rule-based mapping of score bands to wording (see the _*_WORDS
    lists above) -- tune the wording there, not the sentence structure, if
    it reads awkwardly for some combination.
    """
    v = _band(scores.get("volume", float("nan")))
    f = _band(scores.get("frequency", float("nan")))
    c = _band(scores.get("character", float("nan")))
    e = _band(scores.get("evenness", float("nan")))
    o = _band(scores.get("outliers", float("nan")))
    volume_phrase = _VOLUME_WORDS[v][0].upper() + _VOLUME_WORDS[v][1:]
    return (
        f"{volume_phrase} yarn with {_FREQUENCY_WORDS[f]} loops, "
        f"{_CHARACTER_WORDS[c]}, {_EVENNESS_WORDS[e]} spacing, "
        f"and {_OUTLIER_WORDS[o]}."
    )
