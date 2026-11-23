"""sensor_pair.py - two YarnScope sensors on the same yarn, one behind the other (Nutzerwunsch 2026-11-23).

With "📏 Measure" both sensors are read in ONE task of the NI box, so sample n of sensor 1 and sample n of sensor 2
were taken at the same instant. The yarn reaches the second sensor later; finding that delay gives
  a) the speed:    v = distance between the sensors / delay      (distance typed by the user, not fixed)
     - without a distance the other way round: distance = nominal speed x delay,
     - per window (e.g. every 10 m) as well, so a fluctuating speed shows,
  b) the same knots: the knots of both signals (dty_analysis.knot_runs = exactly the YarnScope detection) are
     shifted by the delay and paired; how many both sensors found, how many only one, how much their lengths differ.

Delay = maximum of the normalised cross-correlation (FFT) within +-max_delay_s, refined between samples with a
parabola. Signals are detrended first (minus a running mean of ~20 cm), so a different empty value / thickness
level of the two heads does not matter. corr < MIN_CORR -> "no reliable match" (no speed, no knot pairing).
Files of two separately started measurements (Sensoft) have no common clock: the delay then also contains the
start difference - only the knot pairing means something there (pair_report(..., synced=False)).

Qt-free; used by sensor_measure.measure()/measure_free() and the live measurement (sensor_live.py).
Tests: tests/test_sensor_pair.py (synthetic yarn signals with a built-in delay).
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

MIN_CORR = 0.3              # below: the two signals do not show the same yarn (or a sensor sees nothing)
DETREND_MM = 200.0          # running mean removed before correlating (thickness level / empty value)
DEFAULT_MAX_DELAY_S = 0.5   # 0.5 s = ~100 mm at 12 m/min ... 6 m at 764 m/min - far beyond any real distance
WINDOW_M = 10.0             # speed profile: one value per 10 m
DEFAULT_DISTANCE_MM = 160.0 # distance between the two sensors on the user's test setup (2026-11-23: "about 16 cm")


def combined(axes: Sequence[np.ndarray]) -> np.ndarray:
    """One signal per sensor like the DTY reader: 1 axis as it is, 2 axes (x + y) / 2."""
    if len(axes) == 1:
        return np.asarray(axes[0], dtype=float)
    n = min(len(axes[0]), len(axes[1]))
    return (np.asarray(axes[0][:n], dtype=float) + np.asarray(axes[1][:n], dtype=float)) / 2.0


def _detrend(y: np.ndarray, k: int) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    if k > 1 and len(y) > k:
        c = np.cumsum(np.insert(y, 0, 0.0))
        m = (c[k:] - c[:-k]) / k
        pad_l = (len(y) - len(m)) // 2
        m = np.concatenate([np.full(pad_l, m[0]), m, np.full(len(y) - len(m) - pad_l, m[-1])])
        y = y - m
    s = np.std(y)
    return (y - np.mean(y)) / s if s > 0 else y * 0.0


def find_delay(a: np.ndarray, b: np.ndarray, spacing_mm: float = 0.25, max_lag: Optional[int] = None,
               center: Optional[float] = None) -> Dict[str, Any]:
    """Delay of b behind a in samples (float, + = b sees the yarn later) and the correlation at that point.
    max_lag limits the search to +-max_lag samples (around `center` if given)."""
    n = min(len(a), len(b))
    if n < 64:
        return {"lag": None, "corr": None}
    k = max(3, int(round(DETREND_MM / max(spacing_mm, 1e-6))))
    x, y = _detrend(a[:n], k), _detrend(b[:n], k)
    size = 1 << int(math.ceil(math.log2(2 * n)))
    xc = np.fft.irfft(np.conj(np.fft.rfft(x, size)) * np.fft.rfft(y, size), size)
    lags = np.concatenate([np.arange(0, n), np.arange(-n + 1, 0)])          # xc[i] belongs to lag lags[i]
    vals = np.concatenate([xc[:n], xc[size - n + 1:]])
    overlap = n - np.abs(lags)                                              # unbiased: per overlapping sample
    vals = vals / np.maximum(overlap, 1)
    ok = overlap >= max(64, n // 4)                                         # at least a quarter overlapping
    if max_lag is not None:
        c = 0.0 if center is None else float(center)
        ok &= np.abs(lags - c) <= max_lag
    if not ok.any():
        return {"lag": None, "corr": None}
    idx = np.flatnonzero(ok)
    best = idx[int(np.argmax(vals[idx]))]
    lag, corr = float(lags[best]), float(vals[best])
    # parabola through the neighbours -> between samples
    order = {int(l): i for i, l in zip(idx, lags[idx])}
    lo, hi = order.get(int(lags[best]) - 1), order.get(int(lags[best]) + 1)
    if lo is not None and hi is not None:
        y0, y1, y2 = vals[lo], vals[best], vals[hi]
        den = y0 - 2 * y1 + y2
        if den < 0:
            lag += float(np.clip(0.5 * (y0 - y2) / den, -0.5, 0.5))
    return {"lag": lag, "corr": corr}


def speed_m_min(distance_mm: float, delay_s: float) -> Optional[float]:
    """Speed from the distance and the delay - the sign of the delay (which sensor sees the yarn first) does not
    matter, the yarn may run either way through the two heads."""
    if not distance_mm or not delay_s:
        return None
    return distance_mm / 1000.0 / abs(delay_s) * 60.0


def speed_profile(a: np.ndarray, b: np.ndarray, rate: float, lag: float, spacing_mm: float, window_m: float,
                  distance_mm: Optional[float]) -> List[Dict[str, Any]]:
    """Delay (and speed) per window of window_m metres, searched around the overall delay (+-25 %)."""
    n = min(len(a), len(b))
    w = int(window_m * 1000.0 / spacing_mm)
    if w < 256 or n < w:
        return []
    out = []
    span = max(8, int(abs(lag) * 0.25))
    for i, s in enumerate(range(0, n - w + 1, w)):
        r = find_delay(a[s:s + w], b[s:s + w], spacing_mm, max_lag=span, center=lag)
        d = (r["lag"] / rate) if r["lag"] is not None else None
        out.append({"from_m": round(i * window_m, 1), "to_m": round((i + 1) * window_m, 1),
                    "delay_ms": round(d * 1000.0, 3) if d is not None else None,
                    "corr": round(r["corr"], 3) if r["corr"] is not None else None,
                    "speed": (round(speed_m_min(distance_mm, d), 1) if d and distance_mm and r["corr"] and
                              r["corr"] >= MIN_CORR else None)})
    return out


def match_knots(runs_a: Sequence[Tuple[int, int]], runs_b: Sequence[Tuple[int, int]], lag: float,
                n_a: int, n_b: int, spacing_mm: float) -> Dict[str, Any]:
    """Pair the knots of a and b (b shifted back by lag). Only the part both sensors saw counts. A knot pairs
    with the nearest one whose centre is within half the median knot length (at least 1 mm)."""
    sh = [((s - lag), (e - lag)) for s, e in runs_b]
    lo, hi = max(0.0, -lag) if lag < 0 else 0.0, min(float(n_a), n_b - lag)
    a = [(s, e) for s, e in runs_a if s >= lo and e <= hi]
    b = [(s, e) for s, e in sh if s >= lo and e <= hi]
    if not a or not b:
        return {"knots_a": len(a), "knots_b": len(b), "matched": 0}
    lens = np.array([e - s for s, e in a + b], dtype=float)
    tol = max(1.0 / spacing_mm, 0.5 * float(np.median(lens)))
    ca = np.array([(s + e) / 2 for s, e in a])
    cb = np.array([(s + e) / 2 for s, e in b])
    used = np.zeros(len(b), dtype=bool)
    pairs = []
    j0 = 0
    for i, c in enumerate(ca):                                  # both lists are in order: walk along
        while j0 < len(cb) and cb[j0] < c - tol:
            j0 += 1
        best, bd = -1, tol + 1
        j = j0
        while j < len(cb) and cb[j] <= c + tol:
            if not used[j] and abs(cb[j] - c) < bd:
                best, bd = j, abs(cb[j] - c)
            j += 1
        if best >= 0:
            used[best] = True
            pairs.append((i, best))
    m = len(pairs)
    dl = np.array([(b[j][1] - b[j][0]) - (a[i][1] - a[i][0]) for i, j in pairs], dtype=float) * spacing_mm
    dc = np.array([cb[j] - ca[i] for i, j in pairs], dtype=float) * spacing_mm
    return {"knots_a": len(a), "knots_b": len(b), "matched": m,
            "pct_a": round(100.0 * m / len(a), 1), "pct_b": round(100.0 * m / len(b), 1),
            "only_a": len(a) - m, "only_b": len(b) - m,
            "len_diff_mm": round(float(dl.mean()), 3) if m else None,
            "len_diff_sd_mm": round(float(dl.std()), 3) if m else None,
            "pos_sd_mm": round(float(dc.std()), 3) if m else None,
            "overlap_m": round((hi - lo) * spacing_mm / 1000.0, 2)}


def pair_report(axes_a: Sequence[np.ndarray], axes_b: Sequence[np.ndarray], rate: float, spacing_mm: float = 0.25,
                distance_mm: Optional[float] = None, nominal_speed: Optional[float] = None, synced: bool = True,
                window_m: float = WINDOW_M, max_delay_s: float = DEFAULT_MAX_DELAY_S) -> Dict[str, Any]:
    """Everything for the page: delay, correlation, speed (synced + distance), distance from the nominal speed,
    speed per window, knot pairing. reliable = False -> the signals do not match (no speed / pairing)."""
    from ui.yarnscope.dty_analysis import knot_runs
    a, b = combined(axes_a), combined(axes_b)
    max_lag = int(max_delay_s * rate) if rate else None
    r = find_delay(a, b, spacing_mm, max_lag=max_lag)
    lag, corr = r["lag"], r["corr"]
    out: Dict[str, Any] = {"synced": synced, "corr": round(corr, 3) if corr is not None else None,
                           "lag_samples": round(lag, 2) if lag is not None else None,
                           "distance_mm": distance_mm, "reliable": bool(corr is not None and corr >= MIN_CORR)}
    if lag is None or not out["reliable"]:
        return out
    delay = lag / rate if rate else None
    out["delay_ms"] = round(delay * 1000.0, 3) if delay is not None else None
    if synced and delay:
        if distance_mm:
            out["speed"] = round(speed_m_min(distance_mm, delay), 1)
            if nominal_speed:
                out["speed_dev_pct"] = round((out["speed"] / nominal_speed - 1) * 100.0, 2)
        if nominal_speed:
            out["distance_from_speed_mm"] = round(nominal_speed / 60.0 * abs(delay) * 1000.0, 1)
        out["first"] = "main" if delay > 0 else "second"      # which sensor the yarn passes first
        out["profile"] = speed_profile(a, b, rate, lag, spacing_mm, window_m, distance_mm)
    ra, _ = knot_runs(a)
    rb, _ = knot_runs(b)
    out["knots"] = match_knots(ra, rb, lag, len(a), len(b), spacing_mm)
    return out
