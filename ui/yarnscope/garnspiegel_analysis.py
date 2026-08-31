"""
garnspiegel_analysis.py -- image-based yarn evenness proxy from "wrap test" /
"black board" photos (yarn wound many times around a card, photographed once).

Independent from the TDMS-based ATY/DTY analysis paths (aty_core_analysis.py,
dty_analysis.py) - this reads a plain photo instead of a photocell signal.
Separates the wound strands via Otsu thresholding + connected components,
measures each strand's local width in pixels along its length, and pools
that into a single width-CV% per image.

Validated 2026-08 against real ATY/VISOTEC measurements for TrialSeries
270+288 (n=38, the same calibration set used in aty_core_analysis.py):
width-CV% correlates with the real BulkIndexPct at r=+0.94 *within* a single
consistent photo session, but only r=+0.47 when combining two different
photo sessions (270+288) - most likely because a session-to-session
brightness/distance offset isn't corrected for. Treat CVPct as reliable for
comparing images from the SAME photo session; treat cross-session absolute
comparisons as unvalidated until more sessions get checked against real
measurements. No other candidate axis (peak frequency, spacing-CV,
short/long-peak split, P99/median outlier ratio) showed a usable
correlation (r=0.03-0.39) with this simple pixel-based approach - not
persisted here.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

# Bumped whenever the algorithm below changes in a way that would make old
# results not directly comparable to new ones (mirrors aty_core_analysis.PARAMS_VERSION).
PARAMS_VERSION = "v1-2026-08-19"

# Not every image attached to a TrialSeries is a Garnspiegel wrap-test photo
# (defect photos, setup photos, ... also get uploaded through the same
# dialog) - gate on the lab's existing "V<n>.jpg" filename convention for
# wrap-test cards (V = Versuchsnummer) rather than trying to analyze every
# upload, which risks a false-positive "ok" reading on some unrelated photo
# that happens to have a few roughly-parallel lines (ruled paper, fabric
# weave, a ruler, ...). 741 of 816 images in the existing library already
# follow this convention (2026-08-19 survey); the rest are presumed to be
# something else and are skipped entirely - no analysis attempted, no row
# written for them.
GARNSPIEGEL_FILENAME_RE = re.compile(r"^V(\d+)", re.IGNORECASE)


def parse_versuchsnummer(original_filename: str) -> Optional[int]:
    """Extracts the Versuchsnummer from a "V<n>[...].jpg"-style filename, or
    None if it doesn't look like a Garnspiegel wrap-test photo at all."""
    m = GARNSPIEGEL_FILENAME_RE.match(original_filename or "")
    return int(m.group(1)) if m else None


def looks_like_garnspiegel_filename(original_filename: str) -> bool:
    return parse_versuchsnummer(original_filename) is not None

EDGE_TRIM_FRAC = 0.04          # drop this fraction of each strand's profile at both ends (card-wrap artifact)
MIN_STRAND_COMPONENT_AREA = 2000
MIN_STRAND_SPAN_FRAC = 0.5     # a valid strand component must span at least this fraction of the image's long axis
CLOSE_KERNEL_LEN = 25          # directional closing kernel length (px), bridges small gaps along a strand
ILLUM_BLUR_SIGMA = 51          # Gaussian sigma used to estimate + remove slow lighting gradients


def flatten_illumination(img: np.ndarray, sigma: float = ILLUM_BLUR_SIGMA) -> np.ndarray:
    """Removes slow lighting gradients/vignetting (some photo sessions have a
    visible brightness falloff across the card) by subtracting a heavily
    blurred estimate of the background before thresholding. Without this,
    global Otsu can pick a threshold that sits inside the background
    gradient itself instead of between background and yarn (found on
    TrialSeries 272: 28% of the image misclassified as "foreground" vs. a
    healthy ~5-6% elsewhere)."""
    bg = cv2.GaussianBlur(img, (0, 0), sigmaX=sigma)
    flat = cv2.subtract(img, bg)
    flat = cv2.normalize(flat, None, 0, 255, cv2.NORM_MINMAX)
    return flat.astype(np.uint8)


def _strand_profiles_one_orientation(img: np.ndarray) -> List[np.ndarray]:
    """img: grayscale array where strands are expected to run roughly
    HORIZONTALLY (i.e. wide, short connected components).

    Uses a directional closing kernel (wide along the strand direction, 1px
    across) instead of an isotropic open+close: some photo sessions have
    much thinner strands (~2-3px) than others (~10-13px) - an isotropic
    MORPH_OPEN erodes a 2-3px line into nothing before it ever becomes one
    connected component, fragmenting it into hundreds of speckles instead of
    the ~20-25 real strands (found on TrialSeries 165, 100% failure under an
    isotropic 3x3 kernel)."""
    h, w = img.shape
    img = flatten_illumination(img)
    _, mask = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (CLOSE_KERNEL_LEN, 1))
    mask_clean = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel, iterations=1)
    mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8), iterations=1)
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask_clean, connectivity=8)

    profiles = []
    for i in range(1, n_labels):
        x, y, cw, ch, area = stats[i]
        if cw < MIN_STRAND_SPAN_FRAC * w or area < MIN_STRAND_COMPONENT_AREA:
            continue
        comp_mask = (labels[y:y + ch, x:x + cw] == i)
        width_per_col = comp_mask.sum(axis=0).astype(float)
        nz = np.nonzero(width_per_col)[0]
        if len(nz) < 200:
            continue
        width_per_col = width_per_col[nz[0]:nz[-1] + 1]
        n = len(width_per_col)
        trim = int(n * EDGE_TRIM_FRAC)
        profiles.append(width_per_col[trim: n - trim])
    return profiles


def strand_profiles(img_gray: np.ndarray) -> Tuple[List[np.ndarray], Optional[str]]:
    """Tries horizontal strands first, then vertical (transposed) if that
    doesn't find enough. Returns (profiles, orientation) - orientation is
    None and profiles is [] if neither works (not a wrap-test photo, or a
    case this algorithm can't handle - e.g. low-luminance-contrast colored
    yarn on a dark card, a known unresolved gap, see module docstring)."""
    profiles = _strand_profiles_one_orientation(img_gray)
    if len(profiles) >= 3:
        return profiles, "horizontal"
    profiles_v = _strand_profiles_one_orientation(img_gray.T)
    if len(profiles_v) >= 3:
        return profiles_v, "vertical"
    return [], None


def analyze_image(path: str) -> Dict[str, Any]:
    """Loads a wrap-test photo and returns its pooled width-CV% and related
    stats. Always returns a dict (never raises for a normal "couldn't find
    strands" case) - check status == "ok" before trusting the numeric
    fields, which are None otherwise."""
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return {"status": "unreadable", "orientation": None, "n_strands": 0,
                "mean_width_px": None, "std_width_px": None, "cv_pct": None}

    profiles, orientation = strand_profiles(img)
    if not profiles:
        return {"status": "no_strands_detected", "orientation": None, "n_strands": 0,
                "mean_width_px": None, "std_width_px": None, "cv_pct": None}

    pooled = np.concatenate(profiles)
    mean = float(pooled.mean())
    std = float(pooled.std())
    cv_pct = round(100 * std / mean, 2) if mean else None
    return {
        "status": "ok",
        "orientation": orientation,
        "n_strands": len(profiles),
        "mean_width_px": round(mean, 2),
        "std_width_px": round(std, 2),
        "cv_pct": cv_pct,
    }


# ---------------------------------------------------------------------------
# tblTrialSeriesImageAnalysis persistence -- single source of truth for the
# python-key -> DB-column mapping (mirrors aty_core_analysis.DB_COLUMN_MAP).
# ---------------------------------------------------------------------------
DB_COLUMN_MAP: Dict[str, str] = {
    "status": "Status",
    "orientation": "Orientation",
    "n_strands": "NStrands",
    "mean_width_px": "MeanWidthPx",
    "std_width_px": "StdWidthPx",
    "cv_pct": "CVPct",
}
DB_COLUMNS: List[str] = list(DB_COLUMN_MAP.values())


def to_db_row(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Converts an analyze_image() result to {DB column name: value}, ready
    to INSERT into tblTrialSeriesImageAnalysis (plus TrialSeriesImageID/
    GlobalID/UserID/Timestamp/ParamsVersion, which the caller supplies)."""
    return {db_col: stats.get(py_key) for py_key, db_col in DB_COLUMN_MAP.items()}
