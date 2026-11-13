"""thickness_classes.py - thick/thin place classes (Di/Dü) of the yarn mirror views, Qt-free.

Shared by the desktop (GarnCanvas.plot_garnspiegel, ATY Fabric/Knitted in
ui/aty_yarnscope_tab.py) and the web (tripplet_web backend/app/yarnscope_aty.py).
The functions return class KEYS ("Di11".."Dü33"); colours and visibility are
applied by the caller (desktop: COLOR_STATE / VISIBILITY_STATE in
garngraf_canvas.py, web: in the browser) via ``colourize()``.

Class rule: a run of samples above (1 + pct/100) x mean (Di) or below
(1 - pct/100) x mean (Dü) is a thick/thin place if it is at least
CLASS_THRESHOLDS[..]["mm"][0] long; row digit = height step, column digit =
length step.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

SEGMENT_LEN_MM = 200.0
NUM_TURNS = 20
MM_PER_POINT = 0.25

# Thick places (pink/red)
DI_COLORS = {
    "Di11": "#ffd1e6", "Di12": "#ffb3d1", "Di13": "#ff94bd",
    "Di21": "#ff7aa9", "Di22": "#ff5c94", "Di23": "#ff3d80",
    "Di31": "#ff1f6b", "Di32": "#e60057", "Di33": "#b30045",
}
# Thin places (blue)
DUE_COLORS = {
    "Dü11": "#d6ecff", "Dü12": "#b9e0ff", "Dü13": "#9cd4ff",
    "Dü21": "#7fc8ff", "Dü22": "#62bbff", "Dü23": "#45afff",
    "Dü31": "#279fff", "Dü32": "#0f87e6", "Dü33": "#065da8",
}
DI_KEYS = list(DI_COLORS)
DUE_KEYS = list(DUE_COLORS)

CLASS_THRESHOLDS = {
    "Di": {"pct": [10.0, 20.0, 30.0], "mm": [1.0, 2.0, 3.0]},
    "Dü": {"pct": [10.0, 20.0, 30.0], "mm": [1.0, 2.0, 3.0]},
}


def colour_of(key: str, di_colors=None, due_colors=None, fallback: Optional[str] = None) -> str:
    """Colour of a class key; ``di_colors``/``due_colors`` = current (edited) colours."""
    if key.startswith("Di"):
        return (di_colors or DI_COLORS).get(key, DI_COLORS.get(key, fallback or "#ff0000"))
    return (due_colors or DUE_COLORS).get(key, DUE_COLORS.get(key, fallback or "#0000ff"))


def colourize(spans_per_row, di_colors=None, due_colors=None, enabled=None):
    """[[(x0, x1, key)]] -> [[(x0, x1, colour)]] without hidden keys (enabled[key] False)."""
    enabled = enabled or {}
    return [[(x0, x1, colour_of(k, di_colors, due_colors)) for x0, x1, k in row if enabled.get(k, True)]
            for row in spans_per_row]


def _needs(mm_step: float):
    di_len = CLASS_THRESHOLDS["Di"]["mm"]
    due_len = CLASS_THRESHOLDS["Dü"]["mm"]
    di = [max(1, int((v + 1e-9) / mm_step)) for v in di_len]
    due = [max(1, int((v + 1e-9) / mm_step)) for v in due_len]
    return di, due


def _masks(seg, mean_all):
    di_pct = CLASS_THRESHOLDS["Di"]["pct"]
    due_pct = CLASS_THRESHOLDS["Dü"]["pct"]
    b1 = (seg >= (1.0 + di_pct[0] / 100.0) * mean_all) & (seg < (1.0 + di_pct[1] / 100.0) * mean_all)
    b2 = (seg >= (1.0 + di_pct[1] / 100.0) * mean_all) & (seg < (1.0 + di_pct[2] / 100.0) * mean_all)
    b3 = (seg >= (1.0 + di_pct[2] / 100.0) * mean_all)
    t1 = (seg <= (1.0 - due_pct[0] / 100.0) * mean_all) & (seg > (1.0 - due_pct[1] / 100.0) * mean_all)
    t2 = (seg <= (1.0 - due_pct[1] / 100.0) * mean_all) & (seg > (1.0 - due_pct[2] / 100.0) * mean_all)
    t3 = (seg <= (1.0 - due_pct[2] / 100.0) * mean_all)
    return ((b1, "1"), (b2, "2"), (b3, "3")), ((t1, "1"), (t2, "2"), (t3, "3"))


def _runs_np(mask):
    """Runs of True as (starts, inclusive ends)."""
    if not mask.any():
        return np.empty(0, int), np.empty(0, int)
    padded = np.concatenate(([0], mask.view(np.uint8), [0]))
    diff = np.diff(padded)
    return np.where(diff == 1)[0], (np.where(diff == -1)[0] - 1)


def _classify_np(seg, mean_all, mm_step, x_mm, n_pts, scale=1.0):
    """Spans [(x0, x1, key)] of one band/row (ATY Fabric/Knitted rule)."""
    (need1_di, need2_di, need3_di), (need1_due, need2_due, need3_due) = _needs(mm_step)
    di_masks, due_masks = _masks(seg, mean_all)
    spans = []
    for fam, masks, n1, n2, n3 in (("Di", di_masks, need1_di, need2_di, need3_di),
                                   ("Dü", due_masks, need1_due, need2_due, need3_due)):
        for mask, row in masks:
            ss, ee = _runs_np(mask)
            for s, e in zip(ss, ee):
                L = int(e) - int(s) + 1
                if L < n1:
                    continue
                col = '1' if L < n2 else '2' if L < n3 else '3'
                spans.append((float(x_mm[s]) * scale,
                              float(x_mm[min(int(e), n_pts - 1)] + mm_step) * scale,
                              f"{fam}{row}{col}"))
    return spans


def fabric_spans(arr, mm_pp: float, n_bands: int) -> Tuple[List[list], float]:
    """ATY "Fabric": the whole yarn cut into ``n_bands`` equal bands.

    Returns ``(spans_per_band [[(x0_mm, x1_mm, key)]], seg_mm)``; x within a
    band (0..seg_mm). Mean = mean over all used samples."""
    arr = np.asarray(arr, dtype=float)
    total_mm = float(len(arr)) * mm_pp
    seg_mm = total_mm / max(1, n_bands)
    pts_seg = max(1, int(round(seg_mm / mm_pp)))
    actual = min(n_bands, len(arr) // pts_seg)
    if actual == 0:
        return [[] for _ in range(n_bands)], seg_mm
    mean_all = float(np.mean(arr[:actual * pts_seg]))
    mm_step = seg_mm / pts_seg
    x_mm = np.linspace(0.0, seg_mm, pts_seg, endpoint=False)
    out = []
    for b in range(actual):
        seg = np.asarray(arr[b * pts_seg:(b + 1) * pts_seg], dtype=float)
        out.append(_classify_np(seg, mean_all, mm_step, x_mm, pts_seg))
    while len(out) < n_bands:
        out.append([])
    return out, seg_mm


KNITTED_ROW_LEN_MM = 400.0
KNITTED_DISPLAY_MM = 200.0


def knitted_spans(arr, mm_pp: float, n_rows: int, row_len_mm: float = KNITTED_ROW_LEN_MM) -> List[list]:
    """ATY "Knitted": consecutive rows of ``row_len_mm``; x scaled to 0..200 mm."""
    arr = np.asarray(arr, dtype=float)
    pts_row = max(1, int(round(row_len_mm / mm_pp)))
    actual = min(n_rows, len(arr) // pts_row)
    if actual == 0:
        return [[] for _ in range(n_rows)]
    mean_all = float(np.mean(arr[:actual * pts_row]))
    mm_step = row_len_mm / pts_row
    scale = KNITTED_DISPLAY_MM / row_len_mm
    x_mm = np.linspace(0.0, row_len_mm, pts_row, endpoint=False)
    out = []
    for r in range(actual):
        seg = np.asarray(arr[r * pts_row:(r + 1) * pts_row], dtype=float)
        out.append(_classify_np(seg, mean_all, mm_step, x_mm, pts_row, scale))
    while len(out) < n_rows:
        out.append([])
    return out


def _runs_loop(mask):
    """Runs as in the original GarnCanvas.plot_garnspiegel: a run that ends
    before the last sample ends ON the first sample after it (inclusive end =
    one past the run) - kept as is, the Garnspiegel always looked like this."""
    res = []
    s = None
    for idx, flag in enumerate(mask):
        if flag and s is None:
            s = idx
        if (not flag or idx == len(mask) - 1) and s is not None:
            e = idx if not flag else idx
            res.append((s, e))
            s = None
    return res


def garnspiegel_layout(data_mm_all, gap_factor: float = 2.0, show_colors: bool = True,
                       row_spacing_ref: Optional[float] = None, num_turns: Optional[int] = None,
                       mm_per_point: Optional[float] = None) -> Optional[Dict]:
    """Geometry of the raw-signal Garnspiegel (GarnCanvas.plot_garnspiegel; ATY tab).

    The signal is cut into ``num_turns`` rows of 200 mm drawn below each other
    (row distance = row_spacing_ref (else max) x gap_factor), each a white band
    of +-signal/2 around its base. Returns None if there is too little data,
    else {turns, segments [array], bases [float], x_mm (array), mm_step,
    spans [[(s, e, key)]] (sample indices into the row, e inclusive),
    xlim, ylim, global_max}.
    """
    turns = int(num_turns) if num_turns is not None else NUM_TURNS
    turns = max(1, min(NUM_TURNS, turns))
    if data_mm_all is None or len(data_mm_all) < turns:
        return None
    if mm_per_point is not None and mm_per_point > 0:
        mm_step = float(mm_per_point)
        points_per_segment = max(1, int(round(SEGMENT_LEN_MM / mm_step)))
    else:
        points_per_segment = max(1, len(data_mm_all) // turns)
        mm_step = SEGMENT_LEN_MM / float(points_per_segment) if points_per_segment > 0 else MM_PER_POINT
    segments = np.split(data_mm_all[:points_per_segment * turns], turns)
    global_max = float(np.max(data_mm_all))
    row_spacing_base = float(row_spacing_ref) if row_spacing_ref is not None else global_max
    row_spacing = row_spacing_base * float(gap_factor)
    x_mm = np.linspace(0.0, SEGMENT_LEN_MM, points_per_segment, endpoint=False)
    segments = [np.asarray(seg, dtype=float) for seg in segments]
    bases = [-i * row_spacing for i in range(turns)]

    spans = [[] for _ in range(turns)]
    if show_colors:
        mean_all = float(np.mean(data_mm_all))
        (need1_di, need2_di, need3_di), (need1_due, need2_due, need3_due) = _needs(mm_step)
        for i, seg in enumerate(segments):
            di_masks, due_masks = _masks(seg, mean_all)
            for fam, masks, n1, n2, n3 in (("Di", di_masks, need1_di, need2_di, need3_di),
                                           ("Dü", due_masks, need1_due, need2_due, need3_due)):
                for mask, row in masks:
                    for s, e in _runs_loop(mask):
                        L = e - s + 1
                        if L < n1:
                            continue
                        col = '1' if L < n2 else '2' if L < n3 else '3'
                        spans[i].append((s, e, f"{fam}{row}{col}"))

    y_top_first = 0 + np.max(segments[0]) / 2.0
    y_bottom_last = -(turns - 1) * row_spacing - np.max(segments[-1]) / 2.0
    y_margin = 0.05 * global_max
    return {
        "turns": turns, "segments": segments, "bases": bases, "x_mm": x_mm, "mm_step": mm_step,
        "spans": spans, "global_max": global_max,
        "xlim": (0.0, SEGMENT_LEN_MM),
        "ylim": (y_bottom_last - y_margin, y_top_first + y_margin),
    }
