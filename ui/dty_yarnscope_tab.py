"""dty_yarnscope_tab.py - YarnScope (DTY) Tab fuer TrippleT.

Enthaelt alle Funktionen, die am Ende von screen_show_experiment.py via
Monkey-Patching auf ShowExperimentScreen registriert werden (siehe dort
_patch_show_experiment_yarnscope()). Ausgelagert aus screen_show_experiment.py
(reiner Code-Move, keine Verhaltensaenderung) - analog zu aty_yarnscope_tab.py,
das denselben Aufbau fuer den ATY-Tab bereits verwendet.

fetch_all wird bewusst lazy aus ui.screen_show_experiment importiert (nicht neu
implementiert), damit exakt derselbe DB-Wrapper wie vorher verwendet wird.
"""
from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QScrollArea,
    QFrame,
)

from ui.yarnscope.garngraf_canvas import GarnCanvas
from ui.pathutil import resource_path


# ===========================================================================
# YarnScope – Hilfsfunktionen (Modul-Level)
# ===========================================================================

# Dark-Theme-Style fuer QComboBox-Felder (Rollung-Auswahl etc.) - ohne
# explizite Farben erbt die Combo die App-Palette und zeigt schwarzen Text
# auf schwarzem Grund (Kontrast-Bug, Nutzerfeedback 2026-09-08). Popup-Liste
# (QAbstractItemView) braucht ihre eigene Regel, sonst bleibt NUR das
# geschlossene Feld lesbar, das aufgeklappte Dropdown aber weiterhin schwarz.
_YS_DARK_FIELD_STYLE = (
    "QComboBox{background:#222;color:#ddd;border:1px solid #444;}"
    "QComboBox QAbstractItemView{background:#222;color:#ddd;selection-background-color:#39A650;}"
)


def _ys_tdms_base():
    from pathlib import Path
    return Path(r"H:\Technik\TrippleT\YarnScopeTDMS")


def _ys_open_knot_midpoints(open_segs, knot_segs, x_axis):
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


def _ys_opening_segment_series(per_run, y_smooth, x_axis):
    """Liefert (Positionen, Segmentmittelwerte) je Öffnungsstelle (Nicht-Knoten-
    Segment) über das komplette Signal - dieselben grünen Öffnungsstellen-
    Segmentmittel, die im Segmentmittel-Plot gezeichnet werden (siehe
    open_segs dort), aber OHNE die Knoten-Mischung von
    _ys_open_knot_midpoints - Grundlage für die reine "Öffnungsstellen-Trend"-
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


def _ys_rolling_mean(values, window_size: int):
    """Gleitender (rückblickender) Mittelwert ohne künstliche Randwerte."""
    window_size = max(1, int(window_size))
    result = []
    for end in range(1, len(values) + 1):
        start = max(0, end - window_size)
        result.append(sum(values[start:end]) / (end - start))
    return result


def _ys_rolling_mean_by_distance(positions, values, window_m: float):
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


def _ys_roll_trend(positions, values, mode: str, amount: float):
    """Wendet die in der UI gewählte Rollung an und liefert deren Beschriftung."""
    if mode == "Meter":
        return _ys_rolling_mean_by_distance(positions, values, amount), f"{amount:.1f} m"
    pairs = max(1, int(round(amount)))
    return _ys_rolling_mean(values, pairs), f"{pairs} Paare"


def _ys_local_extrema(values):
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


def _ys_trend_metrics(positions, values):
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

    extrema = _ys_local_extrema(y)
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


def _ys_analyze_process_wave(x_values, y_values, bin_width_m: float = 0.05):
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


def _ys_process_wave_reality_check(x_values, y_values, bin_width_m: float = 0.05,
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
        analysis = _ys_analyze_process_wave(x[mask], y[mask], bin_width_m)
        if analysis is None:
            continue
        surrogate_shares = []
        for _ in range(n_surrogates):
            shuffled = rng.permutation(analysis["binned"])
            surrogate = _ys_analyze_process_wave(
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
        verdict = "robuster Wellenhinweis"
    elif fraction_significant >= 0.30:
        verdict = "uneinheitlicher Hinweis"
    else:
        verdict = "nicht belegt"
    return {
        "windows": len(windows), "significant": significant,
        "lambda_median": float(np.median(wavelengths)), "lambda_cv": lambda_cv,
        "amplitude_median": float(np.median(amplitudes)), "r2_median": median_r2,
        "verdict": verdict,
    }


def _ys_update_process_wave_card(label, analysis, enabled):
    if label is None:
        return
    label.setVisible(bool(enabled))
    if not enabled:
        return
    if analysis is None:
        label.setText("<b style=\"color:#ffd166\">Prozesswelle</b><br>"
                      "Für diese Fenstergröße sind nicht genügend Daten vorhanden.")
        return
    label.setText(
        '<b style="color:#ffd166">Prozesswelle</b> &nbsp; '
        f'<span style="color:#aaa">Raster {analysis["bin_width"]:.2f} m · '
        f'Fenster {analysis["span"]:.1f} m</span><br>'
        f'Dominante Wellenlänge <b>{analysis["wavelength"]:.2f} m</b> &nbsp; '
        f'Sinusamplitude <b>{analysis["amplitude"]:.2f} µm</b> &nbsp; '
        f'Sinus-Fit R² <b>{analysis["r_squared"]:.2f}</b> &nbsp; '
        f'Spektralanteil <b>{analysis["spectral_share"] * 100:.0f} %</b><br>'
        f'Drift <b>{analysis["drift"]:.2f} µm/m</b> &nbsp; '
        f'Rest-RMS <b>{analysis["residual_rms"]:.2f} µm</b>')


def _ys_update_trend_metric_card(label, title, color, enabled, positions, values):
    """Aktualisiert eine kompakte, vergleichbare Kennzahlenkarte im UI."""
    if label is None:
        return
    label.setVisible(bool(enabled))
    if not enabled:
        return
    metrics = _ys_trend_metrics(positions, values)
    if metrics is None:
        label.setText(f'<b style="color:{color}">{title}</b><br>Keine Trendwerte im sichtbaren Fenster.')
        return

    def _number(value, decimals=1, suffix=""):
        return "—" if value is None else f"{value:.{decimals}f}{suffix}"

    wave_cv = (None if metrics["wavelength_cv"] is None
               else metrics["wavelength_cv"] * 100.0)
    label.setText(
        f'<b style="color:{color}">{title}</b> &nbsp; '
        f'<span style="color:#aaa">n={metrics["count"]}</span><br>'
        f'Median <b>{_number(metrics["median"])} µm</b> &nbsp; '
        f'P5–P95 <b>{_number(metrics["p5_p95"])} µm</b> &nbsp; '
        f'MAD <b>{_number(metrics["mad"])} µm</b><br>'
        f'Drift <b>{_number(metrics["slope"], 2, " µm/m")}</b> &nbsp; '
        f'Δ Ende <b>{_number(metrics["end_delta"])} µm</b> &nbsp; '
        f'Wellenlänge <b>{_number(metrics["wavelength"], 2, " m")}</b> &nbsp; '
        f'Wellen-CV <b>{_number(wave_cv, 0, " %")}</b><br>'
        f'Peak–Tal Median <b>{_number(metrics["peak_to_peak"])} µm</b> &nbsp; '
        f'P95 <b>{_number(metrics["peak_to_peak_p95"])} µm</b>')


def _ys_peak_valley_midpoints(y_values, x_axis):
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
    extrema = _ys_local_extrema(values)

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


def _ys_series_has_tdms(series_id: int) -> bool:
    base = _ys_tdms_base()
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


def _ys_find_tdms(series_id: int, versuch_no: int):
    base = _ys_tdms_base()
    if not base.exists():
        return None
    try:
        for f in base.iterdir():
            if f.suffix.lower() == ".tdms" and f.stem.startswith(f"{series_id}_{versuch_no}_"):
                return f
    except Exception:
        pass
    try:
        from ui.screen_tdms_batch import TDMSFolderScanner
        for f in base.iterdir():
            if f.suffix.lower() == ".tdms":
                ids = TDMSFolderScanner._parse_ids(f.stem)
                if ids == (series_id, versuch_no):
                    return f
    except Exception:
        pass
    return None


def _ys_extract_vals(res: dict) -> dict:
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
# YarnScope – Methoden auf ShowExperimentScreen
# ===========================================================================

def _build_yarnscope_tab(self):
    sid = self._series_pk
    if sid is None or not _ys_series_has_tdms(sid):
        _remove_yarnscope_tab_if_exists(self)
        return
    _create_yarnscope_tab_if_needed(self)
    _ys_populate_trial_list(self)


def _remove_yarnscope_tab_if_exists(self):
    if self.tab_yarnscope is None:
        return
    timer = getattr(self, "_ys_auto_timer", None)
    if timer is not None:
        timer.stop()
    self._ys_auto_timer = None
    idx = self.tabs.indexOf(self.tab_yarnscope)
    if idx != -1:
        self.tabs.removeTab(idx)
    self.tab_yarnscope.deleteLater()
    self.tab_yarnscope = None
    self._ys_trial_list = None


def _create_yarnscope_tab_if_needed(self):
    from PySide6.QtWidgets import (
        QSplitter, QListWidget, QListWidgetItem, QDoubleSpinBox, QCheckBox, QComboBox,
        QTableWidget, QTableWidgetItem, QAbstractItemView,
    )
    from PySide6.QtCore import Qt, QTimer
    if self.tab_yarnscope is not None:
        return

    self.tab_yarnscope = QWidget()
    root = QVBoxLayout(self.tab_yarnscope)
    root.setContentsMargins(8, 8, 8, 8);
    root.setSpacing(6)

    splitter = QSplitter(Qt.Horizontal)

    # ── Links: Trial-Liste ────────────────────────────────────
    left = QWidget();
    left.setMaximumWidth(210)
    lv = QVBoxLayout(left);
    lv.setContentsMargins(0, 0, 0, 0);
    lv.setSpacing(4)
    lbl_t = QLabel("Trials")
    lbl_t.setStyleSheet("font-weight:bold; color:#7ddf9a; font-size:13px;")
    lv.addWidget(lbl_t)
    self._ys_trial_list = QListWidget()
    self._ys_trial_list.setStyleSheet("""
        QListWidget { background:#1a1a1a; color:#ddd; border:1px solid #333; font-size:12px; }
        QListWidget::item { padding:4px 6px; }
        QListWidget::item:selected { background:#39A650; color:#fff; }
        QListWidget::item:hover { background:#2a2a2a; }
    """)
    self._ys_trial_list.currentRowChanged.connect(
        lambda row: _ys_on_trial_selected(self, row))
    lv.addWidget(self._ys_trial_list, 1)
    splitter.addWidget(left)

    # Auto-refresh: re-scans the (often network-share) TDMS folder while this
    # tab is visible AND at least one trial is still missing a file - stops
    # itself once every trial has one (see _ys_update_auto_refresh_state()),
    # so it never polls indefinitely for a series that is already complete.
    self._ys_auto_timer = QTimer()
    self._ys_auto_timer.setInterval(20000)
    self._ys_auto_timer.timeout.connect(lambda: _ys_populate_trial_list(self))
    if not getattr(self, "_ys_tab_watch_connected", False):
        self.tabs.currentChanged.connect(lambda idx: _ys_update_auto_refresh_state(self))
        self._ys_tab_watch_connected = True

    # ── Rechts: Analyse ───────────────────────────────────────
    right = QWidget()
    rv = QVBoxLayout(right);
    rv.setContentsMargins(4, 0, 0, 0);
    rv.setSpacing(4)

    # Datei-Info
    self._ys_lbl_file = QLabel("No trial selected")
    self._ys_lbl_file.setStyleSheet("color:#aaa; font-size:11px;")
    rv.addWidget(self._ys_lbl_file)

    # Fenster-Steuerung (relevant für Segmentmittel-Tab; bleibt immer sichtbar)
    ctrl_row = QHBoxLayout();
    ctrl_row.setSpacing(8)
    ctrl_row.addWidget(QLabel("Start [m]:"))
    self._ys_spin_start = QDoubleSpinBox()
    self._ys_spin_start.setRange(0.0, 9999.0);
    self._ys_spin_start.setSingleStep(0.1)
    self._ys_spin_start.setDecimals(2);
    self._ys_spin_start.setValue(0.0)
    self._ys_spin_start.setFixedWidth(80)
    self._ys_spin_start.setStyleSheet("background:#222; color:#ddd; border:1px solid #444;")
    # Debounce-Timer: 1s nach letzter Eingabe, sofort bei FocusOut
    from PySide6.QtCore import QTimer as _QTimer, QEvent as _QEvent
    self._ys_replot_timer = _QTimer()
    self._ys_replot_timer.setSingleShot(True)
    self._ys_replot_timer.timeout.connect(lambda: _ys_replot(self))

    class _FocusOutFilter(QWidget):
        def __init__(ff_self, target_self):
            super().__init__()
            ff_self._s = target_self

        def eventFilter(ff_self, obj, ev):
            if ev.type() == _QEvent.FocusOut:
                ff_self._s._ys_replot_timer.stop()
                _ys_replot(ff_self._s)
            return False

    self._ys_focus_filter = _FocusOutFilter(self)
    self._ys_spin_start.valueChanged.connect(
        lambda v: self._ys_replot_timer.start(1000))
    self._ys_spin_start.installEventFilter(self._ys_focus_filter)
    ctrl_row.addWidget(self._ys_spin_start)

    ctrl_row.addWidget(QLabel("Fenster [m]:"))
    self._ys_spin_window = QDoubleSpinBox()
    self._ys_spin_window.setRange(0.1, 100.0);
    self._ys_spin_window.setSingleStep(0.1)
    self._ys_spin_window.setDecimals(1);
    self._ys_spin_window.setValue(3.0)
    self._ys_spin_window.setFixedWidth(70)
    self._ys_spin_window.setStyleSheet("background:#222; color:#ddd; border:1px solid #444;")
    self._ys_spin_window.valueChanged.connect(
        lambda v: self._ys_replot_timer.start(1000))
    self._ys_spin_window.installEventFilter(self._ys_focus_filter)
    ctrl_row.addWidget(self._ys_spin_window)
    ctrl_row.addStretch()
    rv.addLayout(ctrl_row)

    def _replot_roll_after_edit():
        self._ys_replot_timer.stop()
        _ys_replot(self)

    # Alle drei Trend-Auswahlen nebeneinander in EINER Zeile statt drei
    # separaten Zeilen (Nutzerwunsch 2026-09-08: spart vertikalen Platz fuer
    # die Grafik). addSpacing() trennt die drei Gruppen optisch voneinander.
    trend_row = QHBoxLayout()
    trend_row.setSpacing(8)

    self._ys_chk_delta_trend = QCheckBox("Mitte Offenstelle–Knoten")
    self._ys_chk_delta_trend.setToolTip(
        "Zeigt die rollende Mittellinie zwischen Offenstellenhöhe und der Höhe "
        "des jeweils folgenden Knotens im Segmentmittel-Plot.")
    self._ys_chk_delta_trend.setChecked(False)
    trend_row.addWidget(self._ys_chk_delta_trend)
    trend_row.addWidget(QLabel("Rollung:"))
    self._ys_combo_delta_roll_mode = QComboBox()
    self._ys_combo_delta_roll_mode.addItems(["Meter", "Paare"])
    self._ys_combo_delta_roll_mode.setCurrentText("Meter")
    self._ys_combo_delta_roll_mode.setStyleSheet(_YS_DARK_FIELD_STYLE)
    trend_row.addWidget(self._ys_combo_delta_roll_mode)
    self._ys_spin_delta_roll = QDoubleSpinBox()
    self._ys_spin_delta_roll.setRange(0.1, 50.0)
    self._ys_spin_delta_roll.setDecimals(1)
    self._ys_spin_delta_roll.setSuffix(" m")
    self._ys_spin_delta_roll.setValue(1.0)
    self._ys_spin_delta_roll.setFixedWidth(70)
    self._ys_spin_delta_roll.setStyleSheet("background:#222; color:#ddd; border:1px solid #444;")
    self._ys_spin_delta_roll.setToolTip(
        "Breite des gleitenden Mittelwerts – wahlweise in Metern oder "
        "in aufeinanderfolgenden Offenstelle–Knoten-Paaren.")
    self._ys_spin_delta_roll.setEnabled(False)
    self._ys_combo_delta_roll_mode.setEnabled(False)
    self._ys_spin_delta_roll.valueChanged.connect(
        lambda _value: self._ys_replot_timer.start(1000))
    self._ys_spin_delta_roll.editingFinished.connect(_replot_roll_after_edit)
    def _on_delta_roll_mode_changed(mode):
        is_meters = mode == "Meter"
        self._ys_spin_delta_roll.blockSignals(True)
        self._ys_spin_delta_roll.setRange(0.1, 50.0) if is_meters else self._ys_spin_delta_roll.setRange(1, 500)
        self._ys_spin_delta_roll.setDecimals(1 if is_meters else 0)
        self._ys_spin_delta_roll.setSuffix(" m" if is_meters else "")
        self._ys_spin_delta_roll.setValue(1.0 if is_meters else 10)
        self._ys_spin_delta_roll.blockSignals(False)
        self._ys_replot_timer.start(1000)
    self._ys_combo_delta_roll_mode.currentTextChanged.connect(_on_delta_roll_mode_changed)
    def _on_delta_trend_toggled(enabled):
        self._ys_spin_delta_roll.setEnabled(enabled)
        self._ys_combo_delta_roll_mode.setEnabled(enabled)
        _ys_replot(self)
    self._ys_chk_delta_trend.toggled.connect(_on_delta_trend_toggled)
    trend_row.addWidget(self._ys_spin_delta_roll)
    trend_row.addSpacing(14)

    self._ys_chk_peak_valley_trend = QCheckBox("Mitte Peak–Tal")
    self._ys_chk_peak_valley_trend.setToolTip(
        "Zeigt die rollende Mittellinie zwischen einem lokalen Peak und dem "
        "direkt darauffolgenden Tal im Segmentmittel-Plot.")
    self._ys_chk_peak_valley_trend.setChecked(False)
    trend_row.addWidget(self._ys_chk_peak_valley_trend)
    trend_row.addWidget(QLabel("Rollung:"))
    self._ys_combo_peak_valley_roll_mode = QComboBox()
    self._ys_combo_peak_valley_roll_mode.addItems(["Meter", "Paare"])
    self._ys_combo_peak_valley_roll_mode.setCurrentText("Meter")
    self._ys_combo_peak_valley_roll_mode.setStyleSheet(_YS_DARK_FIELD_STYLE)
    trend_row.addWidget(self._ys_combo_peak_valley_roll_mode)
    self._ys_spin_peak_valley_roll = QDoubleSpinBox()
    self._ys_spin_peak_valley_roll.setRange(0.1, 50.0)
    self._ys_spin_peak_valley_roll.setDecimals(1)
    self._ys_spin_peak_valley_roll.setSuffix(" m")
    self._ys_spin_peak_valley_roll.setValue(1.0)
    self._ys_spin_peak_valley_roll.setFixedWidth(70)
    self._ys_spin_peak_valley_roll.setStyleSheet("background:#222; color:#ddd; border:1px solid #444;")
    self._ys_spin_peak_valley_roll.setToolTip(
        "Breite des gleitenden Mittelwerts – wahlweise in Metern oder "
        "in aufeinanderfolgenden Peak–Tal-Paaren.")
    self._ys_spin_peak_valley_roll.setEnabled(False)
    self._ys_combo_peak_valley_roll_mode.setEnabled(False)
    self._ys_spin_peak_valley_roll.valueChanged.connect(
        lambda _value: self._ys_replot_timer.start(1000))
    self._ys_spin_peak_valley_roll.editingFinished.connect(_replot_roll_after_edit)
    def _on_peak_valley_roll_mode_changed(mode):
        is_meters = mode == "Meter"
        self._ys_spin_peak_valley_roll.blockSignals(True)
        self._ys_spin_peak_valley_roll.setRange(0.1, 50.0) if is_meters else self._ys_spin_peak_valley_roll.setRange(1, 500)
        self._ys_spin_peak_valley_roll.setDecimals(1 if is_meters else 0)
        self._ys_spin_peak_valley_roll.setSuffix(" m" if is_meters else "")
        self._ys_spin_peak_valley_roll.setValue(1.0 if is_meters else 10)
        self._ys_spin_peak_valley_roll.blockSignals(False)
        self._ys_replot_timer.start(1000)
    self._ys_combo_peak_valley_roll_mode.currentTextChanged.connect(
        _on_peak_valley_roll_mode_changed)
    def _on_peak_valley_trend_toggled(enabled):
        self._ys_spin_peak_valley_roll.setEnabled(enabled)
        self._ys_combo_peak_valley_roll_mode.setEnabled(enabled)
        _ys_replot(self)
    self._ys_chk_peak_valley_trend.toggled.connect(_on_peak_valley_trend_toggled)
    trend_row.addWidget(self._ys_spin_peak_valley_roll)
    trend_row.addSpacing(14)

    self._ys_chk_opening_trend = QCheckBox("Öffnungsstellen-Trend")
    self._ys_chk_opening_trend.setToolTip(
        "Zeigt die rollende Mittellinie NUR über die grünen Öffnungsstellen-"
        "Segmentmittel im Segmentmittel-Plot, ohne Knoten-Anteil (anders als "
        "'Mitte Offenstelle–Knoten', das Offenstelle UND Knoten mischt).")
    self._ys_chk_opening_trend.setChecked(False)
    trend_row.addWidget(self._ys_chk_opening_trend)
    trend_row.addWidget(QLabel("Rollung:"))
    self._ys_combo_opening_roll_mode = QComboBox()
    self._ys_combo_opening_roll_mode.addItems(["Meter", "Paare"])
    self._ys_combo_opening_roll_mode.setCurrentText("Meter")
    self._ys_combo_opening_roll_mode.setStyleSheet(_YS_DARK_FIELD_STYLE)
    trend_row.addWidget(self._ys_combo_opening_roll_mode)
    self._ys_spin_opening_roll = QDoubleSpinBox()
    self._ys_spin_opening_roll.setRange(0.1, 50.0)
    self._ys_spin_opening_roll.setDecimals(1)
    self._ys_spin_opening_roll.setSuffix(" m")
    self._ys_spin_opening_roll.setValue(1.0)
    self._ys_spin_opening_roll.setFixedWidth(70)
    self._ys_spin_opening_roll.setStyleSheet("background:#222; color:#ddd; border:1px solid #444;")
    self._ys_spin_opening_roll.setToolTip(
        "Breite des gleitenden Mittelwerts – wahlweise in Metern oder in "
        "aufeinanderfolgenden Öffnungsstellen.")
    self._ys_spin_opening_roll.setEnabled(False)
    self._ys_combo_opening_roll_mode.setEnabled(False)
    self._ys_spin_opening_roll.valueChanged.connect(
        lambda _value: self._ys_replot_timer.start(1000))
    self._ys_spin_opening_roll.editingFinished.connect(_replot_roll_after_edit)
    def _on_opening_roll_mode_changed(mode):
        is_meters = mode == "Meter"
        self._ys_spin_opening_roll.blockSignals(True)
        self._ys_spin_opening_roll.setRange(0.1, 50.0) if is_meters else self._ys_spin_opening_roll.setRange(1, 500)
        self._ys_spin_opening_roll.setDecimals(1 if is_meters else 0)
        self._ys_spin_opening_roll.setSuffix(" m" if is_meters else "")
        self._ys_spin_opening_roll.setValue(1.0 if is_meters else 10)
        self._ys_spin_opening_roll.blockSignals(False)
        self._ys_replot_timer.start(1000)
    self._ys_combo_opening_roll_mode.currentTextChanged.connect(_on_opening_roll_mode_changed)
    def _on_opening_trend_toggled(enabled):
        self._ys_spin_opening_roll.setEnabled(enabled)
        self._ys_combo_opening_roll_mode.setEnabled(enabled)
        _ys_replot(self)
    self._ys_chk_opening_trend.toggled.connect(_on_opening_trend_toggled)
    trend_row.addWidget(self._ys_spin_opening_roll)
    trend_row.addStretch()
    rv.addLayout(trend_row)

    # Kennzahlen der aktivierten Linien: bewusst direkt oberhalb des Charts,
    # damit zwei Trials mit denselben Einstellungen schnell vergleichbar sind.
    trend_metrics_row = QHBoxLayout()
    trend_metrics_row.setSpacing(8)
    self._ys_lbl_open_knot_metrics = QLabel()
    self._ys_lbl_peak_valley_metrics = QLabel()
    self._ys_lbl_opening_metrics = QLabel()
    for label, color in (
        (self._ys_lbl_open_knot_metrics, "#56d7d0"),
        (self._ys_lbl_peak_valley_metrics, "#ff6bb5"),
        (self._ys_lbl_opening_metrics, "#8de6a0"),
    ):
        label.setWordWrap(True)
        label.setTextFormat(Qt.RichText)
        label.setStyleSheet(
            f"background:#202a2d; color:#ddd; border:1px solid {color}; "
            "border-radius:4px; padding:5px 8px; font-size:11px;")
        label.setVisible(False)
        trend_metrics_row.addWidget(label, 1)
    rv.addLayout(trend_metrics_row)

    process_wave_row = QHBoxLayout()
    process_wave_row.setSpacing(8)
    self._ys_chk_process_wave = QCheckBox("Prozesswelle analysieren")
    self._ys_chk_process_wave.setToolTip(
        "Ermittelt eine räumlich gebinnte Mittellinie, deren dominante Welle "
        "und einen Sinus-Fit. Für einen belastbaren Vergleich ein längeres "
        "Fenster (z. B. 30–100 m) verwenden.")
    self._ys_chk_process_wave.setChecked(False)
    process_wave_row.addWidget(self._ys_chk_process_wave)
    process_wave_row.addWidget(QLabel("Raster [m]:"))
    self._ys_spin_process_wave_bin = QDoubleSpinBox()
    self._ys_spin_process_wave_bin.setRange(0.02, 1.0)
    self._ys_spin_process_wave_bin.setDecimals(2)
    self._ys_spin_process_wave_bin.setSingleStep(0.01)
    self._ys_spin_process_wave_bin.setValue(0.05)
    self._ys_spin_process_wave_bin.setSuffix(" m")
    self._ys_spin_process_wave_bin.setFixedWidth(75)
    self._ys_spin_process_wave_bin.setStyleSheet("background:#222; color:#ddd; border:1px solid #444;")
    self._ys_spin_process_wave_bin.setEnabled(False)
    self._ys_spin_process_wave_bin.setToolTip(
        "Räumliche Binbreite für die Prozessmittel-Linie. Kleinere Werte "
        "zeigen mehr Details, größere Werte glätten stärker.")
    self._ys_spin_process_wave_bin.valueChanged.connect(
        lambda _value: self._ys_replot_timer.start(1000))
    self._ys_spin_process_wave_bin.editingFinished.connect(_replot_roll_after_edit)
    process_wave_row.addWidget(self._ys_spin_process_wave_bin)
    process_wave_row.addStretch()
    rv.addLayout(process_wave_row)

    self._ys_lbl_process_wave_metrics = QLabel()
    self._ys_lbl_process_wave_metrics.setWordWrap(True)
    self._ys_lbl_process_wave_metrics.setTextFormat(Qt.RichText)
    self._ys_lbl_process_wave_metrics.setStyleSheet(
        "background:#302b20; color:#ddd; border:1px solid #ffd166; "
        "border-radius:4px; padding:5px 8px; font-size:11px;")
    self._ys_lbl_process_wave_metrics.setVisible(False)
    rv.addWidget(self._ys_lbl_process_wave_metrics)

    def _on_process_wave_toggled(enabled):
        self._ys_spin_process_wave_bin.setEnabled(enabled)
        _ys_replot(self)
    self._ys_chk_process_wave.toggled.connect(_on_process_wave_toggled)

    # ── Unterreiter: Segmentmittel | Garnspiegel ──────────────────────────
    self._ys_sub_tabs = QTabWidget()
    self._ys_sub_tabs.setStyleSheet("""
        QTabWidget::pane { border:1px solid #333; background:#2a2a2a; }
        QTabBar::tab { background:#1e1e1e; color:#aaa; padding:4px 14px;
                       border:1px solid #333; border-bottom:none; font-size:12px; }
        QTabBar::tab:selected { background:#2a2a2a; color:#7ddf9a;
                                border-bottom:1px solid #2a2a2a; }
        QTabBar::tab:hover { background:#2e2e2e; color:#ddd; }
    """)

    # --- Unterreiter 1: Segmentmittel ---
    seg_widget = QWidget()
    seg_widget.setStyleSheet("background:#2a2a2a;")
    self._ys_plot_layout = QVBoxLayout(seg_widget)
    self._ys_plot_layout.setContentsMargins(0, 0, 0, 0)
    self._ys_sub_tabs.addTab(seg_widget, "Segmentmittel")

    # --- Unterreiter 2: Garnspiegel ---
    gs_widget = QWidget()
    gs_widget.setStyleSheet("background:#000;")
    gs_layout = QVBoxLayout(gs_widget)
    gs_layout.setContentsMargins(0, 0, 0, 0)
    self._ys_garn_canvas = None
    try:
        self._ys_garn_canvas = GarnCanvas(gs_widget)
        self._ys_garn_canvas._no_scroll = True
        gs_layout.addWidget(self._ys_garn_canvas)
    except Exception as _e_gc:
        _lbl_gc = QLabel(f"Yarn profile not available:\n{_e_gc}")
        _lbl_gc.setStyleSheet("color:#ff6060; padding:12px;")
        gs_layout.addWidget(_lbl_gc)
    self._ys_sub_tabs.addTab(gs_widget, "Garnspiegel")

    # --- Unterreiter 3: Signal ---
    sig_widget = QWidget()
    sig_widget.setStyleSheet("background:#1e1e1e;")
    sig_layout = QVBoxLayout(sig_widget)
    sig_layout.setContentsMargins(0, 0, 0, 0)
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as _FCA
    from matplotlib.figure import Figure as _Fig
    _sig_fig = _Fig(facecolor="#1e1e1e")
    self._ys_ax_signal = _sig_fig.add_subplot(111)
    self._ys_canvas_signal = _FCA(_sig_fig)
    self._ys_canvas_signal.setStyleSheet("background:#1e1e1e;")
    sig_layout.addWidget(self._ys_canvas_signal)
    self._ys_sub_tabs.addTab(sig_widget, "Signal")

    # --- Unterreiter 4: Prozessvergleich mehrerer Trials ---
    compare_widget = QWidget()
    compare_widget.setStyleSheet("background:#1e1e1e;")
    compare_layout = QHBoxLayout(compare_widget)
    compare_layout.setContentsMargins(8, 8, 8, 8)
    compare_layout.setSpacing(10)

    compare_left = QWidget()
    compare_left.setMaximumWidth(225)
    compare_left_layout = QVBoxLayout(compare_left)
    compare_left_layout.setContentsMargins(0, 0, 0, 0)
    compare_left_layout.addWidget(QLabel("Trials vergleichen"))
    self._ys_compare_trial_list = QListWidget()
    self._ys_compare_trial_list.setStyleSheet(
        "QListWidget{background:#242424;color:#ddd;border:1px solid #444;}"
        "QListWidget::item{padding:3px 5px;}")
    compare_left_layout.addWidget(self._ys_compare_trial_list, 1)
    self._ys_chk_compare_normalized = QCheckBox("Auf Median normieren")
    self._ys_chk_compare_normalized.setChecked(True)
    self._ys_chk_compare_normalized.setToolTip(
        "Zentriert jeden Trial auf seinen Prozessmittel-Median, damit die "
        "Form und nicht der absolute Dickenunterschied verglichen wird.")
    self._ys_chk_compare_normalized.setStyleSheet("QCheckBox,QCheckBox:disabled{color:#fff;}")
    compare_left_layout.addWidget(self._ys_chk_compare_normalized)
    self._ys_chk_compare_show_process_mean = QCheckBox("Prozessmittel anzeigen")
    self._ys_chk_compare_show_process_mean.setChecked(False)
    self._ys_chk_compare_show_process_mean.setToolTip(
        "Blendet die gebinnte Ausgangslinie zusätzlich ein. Für einen klaren "
        "Vergleich mehrerer Trials ist sie standardmäßig ausgeblendet.")
    self._ys_chk_compare_show_process_mean.setStyleSheet("QCheckBox,QCheckBox:disabled{color:#fff;}")
    compare_left_layout.addWidget(self._ys_chk_compare_show_process_mean)
    self._ys_chk_compare_show_drift = QCheckBox("Driftlinien anzeigen")
    self._ys_chk_compare_show_drift.setChecked(False)
    self._ys_chk_compare_show_drift.setToolTip(
        "Zeigt pro Trial die lineare Regression über das gesamte sichtbare "
        "Fenster. Sie entspricht der Kennzahl Drift in µm/m.")
    self._ys_chk_compare_show_drift.setStyleSheet("QCheckBox,QCheckBox:disabled{color:#fff;}")
    compare_left_layout.addWidget(self._ys_chk_compare_show_drift)
    self._ys_chk_compare_open_trend = QCheckBox("Öffnungsstellen-Trend")
    self._ys_chk_compare_open_trend.setChecked(False)
    self._ys_chk_compare_open_trend.setToolTip(
        "Zeigt pro Trial die rollende Mittellinie NUR über die grünen "
        "Öffnungsstellen-Segmentmittel (wie im Segmentmittel-Tab), ohne "
        "Knoten-Anteil. Für Trials, die noch nicht im Segmentmittel-Tab "
        "analysiert wurden, wird die Klassifikation beim Vergleichen "
        "einmalig nachgerechnet (kann etwas dauern).")
    self._ys_chk_compare_open_trend.setStyleSheet("QCheckBox,QCheckBox:disabled{color:#fff;}")
    compare_left_layout.addWidget(self._ys_chk_compare_open_trend)
    open_trend_roll_row = QHBoxLayout()
    open_trend_roll_row.setSpacing(4)
    open_trend_roll_row.addWidget(QLabel("Rollung:"))
    self._ys_combo_compare_open_roll_mode = QComboBox()
    self._ys_combo_compare_open_roll_mode.addItems(["Meter", "Paare"])
    self._ys_combo_compare_open_roll_mode.setCurrentText("Meter")
    self._ys_combo_compare_open_roll_mode.setStyleSheet(_YS_DARK_FIELD_STYLE)
    open_trend_roll_row.addWidget(self._ys_combo_compare_open_roll_mode)
    self._ys_spin_compare_open_roll = QDoubleSpinBox()
    self._ys_spin_compare_open_roll.setRange(0.1, 50.0)
    self._ys_spin_compare_open_roll.setDecimals(1)
    self._ys_spin_compare_open_roll.setSuffix(" m")
    self._ys_spin_compare_open_roll.setValue(1.0)
    self._ys_spin_compare_open_roll.setFixedWidth(70)
    self._ys_spin_compare_open_roll.setStyleSheet("background:#222; color:#ddd; border:1px solid #444;")
    self._ys_spin_compare_open_roll.setToolTip(
        "Breite des gleitenden Mittelwerts – wahlweise in Metern oder in "
        "aufeinanderfolgenden Öffnungsstellen.")
    open_trend_roll_row.addWidget(self._ys_spin_compare_open_roll)
    compare_left_layout.addLayout(open_trend_roll_row)

    def _on_compare_open_roll_mode_changed(mode):
        is_meters = mode == "Meter"
        self._ys_spin_compare_open_roll.blockSignals(True)
        if is_meters:
            self._ys_spin_compare_open_roll.setRange(0.1, 50.0)
        else:
            self._ys_spin_compare_open_roll.setRange(1, 500)
        self._ys_spin_compare_open_roll.setDecimals(1 if is_meters else 0)
        self._ys_spin_compare_open_roll.setSuffix(" m" if is_meters else "")
        self._ys_spin_compare_open_roll.setValue(1.0 if is_meters else 10)
        self._ys_spin_compare_open_roll.blockSignals(False)
        _ys_draw_process_comparison(self, self._ys_compare_results)
    self._ys_combo_compare_open_roll_mode.currentTextChanged.connect(
        _on_compare_open_roll_mode_changed)
    self._ys_btn_run_comparison = QPushButton("▶ Vergleichen")
    self._ys_btn_run_comparison.setObjectName("GreenBtn")
    self._ys_btn_run_comparison.clicked.connect(lambda: _ys_run_process_comparison(self))
    compare_left_layout.addWidget(self._ys_btn_run_comparison)
    self._ys_lbl_compare_status = QLabel("Wähle zwei bis sechs Trials – Auswertung immer über die gesamte Messstrecke.")
    self._ys_lbl_compare_status.setWordWrap(True)
    self._ys_lbl_compare_status.setStyleSheet("color:#aaa;font-size:11px;")
    compare_left_layout.addWidget(self._ys_lbl_compare_status)
    compare_layout.addWidget(compare_left)

    compare_right = QWidget()
    compare_right_layout = QVBoxLayout(compare_right)
    compare_right_layout.setContentsMargins(0, 0, 0, 0)
    _compare_fig = _Fig(facecolor="#1e1e1e")
    self._ys_compare_ax = _compare_fig.add_subplot(111)
    self._ys_compare_canvas = _FCA(_compare_fig)
    self._ys_compare_canvas.setStyleSheet("background:#1e1e1e;")
    compare_right_layout.addWidget(self._ys_compare_canvas, 3)
    self._ys_compare_table = QTableWidget(0, 15)
    self._ys_compare_table.setHorizontalHeaderLabels([
        "👁", "Farbe", "Trial", "Median [µm]", "λ [m]", "A [µm]", "R²", "Spektrum", "Drift [µm/m]", "Rest-RMS [µm]",
        "10 m sign.", "10 m λ-CV", "10 m A med. [µm]", "10 m R² med.", "Wellenbefund",
    ])
    self._ys_compare_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    self._ys_compare_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    self._ys_compare_table.setStyleSheet(
        "QTableWidget{background:#242424;color:#ddd;gridline-color:#444;}"
        "QHeaderView::section{background:#303030;color:#ddd;padding:3px;border:1px solid #444;}")
    self._ys_compare_table.horizontalHeader().setStretchLastSection(True)
    compare_right_layout.addWidget(self._ys_compare_table, 1)
    compare_layout.addWidget(compare_right, 1)
    self._ys_compare_results = []
    self._ys_chk_compare_normalized.toggled.connect(
        lambda _checked: _ys_draw_process_comparison(self, self._ys_compare_results))
    self._ys_chk_compare_show_process_mean.toggled.connect(
        lambda _checked: _ys_draw_process_comparison(self, self._ys_compare_results))
    self._ys_chk_compare_show_drift.toggled.connect(
        lambda _checked: _ys_draw_process_comparison(self, self._ys_compare_results))
    self._ys_chk_compare_open_trend.toggled.connect(
        lambda _checked: _ys_draw_process_comparison(self, self._ys_compare_results))
    self._ys_spin_compare_open_roll.valueChanged.connect(
        lambda _value: _ys_draw_process_comparison(self, self._ys_compare_results))
    self._ys_sub_tabs.addTab(compare_widget, "Prozessvergleich")

    def _on_ys_subtab_changed(idx):
        if not getattr(self, "_ys_last_res", None):
            return
        if idx == 1:
            _ys_draw_garnspiegel(self, self._ys_last_res, getattr(self, "_ys_last_vals", {}))
        elif idx == 2:
            _ys_draw_signal(self, self._ys_last_res)

    self._ys_sub_tabs.currentChanged.connect(_on_ys_subtab_changed)

    rv.addWidget(self._ys_sub_tabs, 3)

    # ── Kennzahlen (ausserhalb der Unterreiter, immer sichtbar) ──────────
    self._ys_lbl_metrics = QLabel("")
    self._ys_lbl_metrics.setStyleSheet(
        "color:#ffffff; font-size:14px; font-weight:bold; font-family:monospace;"
        "background:#1e3a28; padding:10px 12px; border-radius:6px;"
        "border:1px solid #39A650;")
    self._ys_lbl_metrics.setWordWrap(True)
    rv.addWidget(self._ys_lbl_metrics)

    # Buttons
    brow = QHBoxLayout();
    brow.setSpacing(8)
    self._ys_btn_analyze = QPushButton("▶ Analyse")
    self._ys_btn_analyze.setObjectName("GreenBtn")
    self._ys_btn_analyze.setFixedHeight(30);
    self._ys_btn_analyze.setEnabled(False)
    self._ys_btn_analyze.clicked.connect(lambda: _ys_on_analyze(self))
    brow.addWidget(self._ys_btn_analyze)
    self._ys_btn_refresh = None
    self._ys_btn_save = QPushButton("💾 Save to DB")
    self._ys_btn_save.setObjectName("GreenBtn")
    self._ys_btn_save.setFixedHeight(30);
    self._ys_btn_save.setEnabled(False)
    self._ys_btn_save.clicked.connect(lambda: _ys_on_save(self))
    brow.addWidget(self._ys_btn_save)
    self._ys_btn_batch = QPushButton("⚡ Batch")
    self._ys_btn_batch.setFixedHeight(30)
    self._ys_btn_batch.setStyleSheet(
        "QPushButton{background:#2a4a6a;color:#8cf;border-radius:4px;"
        "font-size:12px;border:1px solid #4a7aaa;}"
        "QPushButton:hover{background:#3a5a7a;}")
    self._ys_btn_batch.clicked.connect(lambda: _ys_open_batch(self))
    brow.addWidget(self._ys_btn_batch)
    self._ys_lbl_status = QLabel("")
    self._ys_lbl_status.setStyleSheet("color:#aaa; font-size:11px;")
    brow.addWidget(self._ys_lbl_status, 1)
    rv.addLayout(brow)

    splitter.addWidget(right)
    splitter.setStretchFactor(0, 0);
    splitter.setStretchFactor(1, 1)
    splitter.setSizes([200, 900])

    # Auf kleinen/niedrig aufgelösten Laptop-Bildschirmen quetschen sich
    # Trial-Liste, Sub-Tabs (Charts) und Bedienelemente sonst ineinander
    # (Nutzerfeedback 2026-08-27, "sehen schlecht aus... wenn die Auflösung
    # noch sehr niedrig eingestellt ist") - eine QScrollArea um den ganzen
    # Tab-Inhalt sorgt dafür, dass unterhalb dieser Mindestgrösse gescrollt
    # statt gequetscht wird (gleiches Muster wie beim ATY-"Compare"-Sub-Tab,
    # siehe aty_yarnscope_tab.py). Die Mindestgrösse muss auf dem Splitter
    # selbst sitzen (nicht auf der QScrollArea) - sonst hätte die
    # QScrollArea nichts, das ihre Sichtfläche tatsächlich überschreiten
    # könnte, und würde nie Scrollbalken zeigen.
    splitter.setMinimumSize(950, 650)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setWidget(splitter)
    root.addWidget(scroll, 1)
    self.tabs.addTab(self.tab_yarnscope, "YarnScope")


def _ys_populate_trial_list(self):
    from PySide6.QtWidgets import QListWidgetItem
    from PySide6.QtCore import Qt
    # Lazy import (vermeidet Zirkularimport, screen_show_experiment importiert
    # dieses Modul selbst) - derselbe fetch_all-Wrapper wie vorher.
    from ui.screen_show_experiment import fetch_all
    if self._ys_trial_list is None:
        return
    # Aktuelle Auswahl (Trial-ID statt Zeilenindex) merken, damit ein
    # automatischer Refresh (siehe _ys_update_auto_refresh_state()) die
    # laufende Analyse/Auswahl des Nutzers nicht zuruecksetzt.
    prev_row = self._ys_trial_list.currentRow()
    prev_tid = None
    if prev_row >= 0:
        prev_item = self._ys_trial_list.item(prev_row)
        if prev_item:
            prev_tid = (prev_item.data(Qt.UserRole) or {}).get("trial_id")
    self._ys_trial_list.blockSignals(True)
    self._ys_trial_list.clear()
    sid = self._series_pk
    all_have_tdms = True
    restore_row = -1
    refs = getattr(self, "_reference_names", {}) or {}
    for t in self._trials:
        tid = t.get("ID")
        # Reference samples (customer originals) never have a TDMS file -
        # listing them would also keep the auto-refresh timer running forever.
        if tid is not None and int(tid) in refs:
            continue
        vno = t.get("Versuchsnummer") or t.get("versuchsnummer") or 0
        tdms = _ys_find_tdms(sid, int(vno)) if sid else None
        if not tdms:
            all_have_tdms = False
        icon = "📄" if tdms else "—"
        db_ok = False
        try:
            rows = fetch_all("SELECT 1 FROM tbllabordtyomat WHERE TrialID = ? AND Timestamp IS NOT NULL", (tid,))
            db_ok = bool(rows)
        except Exception:
            pass
        status = "✅" if db_ok else ("⏳" if tdms else "")
        label = f"{icon} V{int(vno):03d}  {status}"
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, {"trial_id": tid, "vno": vno, "tdms": tdms})
        if not tdms:
            item.setForeground(QColor("#555"))
        self._ys_trial_list.addItem(item)
        if tid is not None and tid == prev_tid:
            restore_row = self._ys_trial_list.count() - 1
    if restore_row >= 0:
        self._ys_trial_list.setCurrentRow(restore_row)
    self._ys_trial_list.blockSignals(False)
    # Stoppt den Auto-Refresh-Timer, sobald fuer jeden Trial ein TDMS-File
    # gefunden wurde - siehe _ys_update_auto_refresh_state().
    self._ys_all_tdms_present = all_have_tdms
    _ys_populate_compare_trial_list(self)
    _ys_update_auto_refresh_state(self)


def _ys_populate_compare_trial_list(self):
    """Synchronisiert die Trial-Auswahl des Prozessvergleichs mit der Serie."""
    from PySide6.QtWidgets import QListWidgetItem
    from PySide6.QtCore import Qt

    widget = getattr(self, "_ys_compare_trial_list", None)
    if widget is None:
        return
    checked_ids = set()
    for row in range(widget.count()):
        item = widget.item(row)
        if item.checkState() == Qt.Checked:
            data = item.data(Qt.UserRole) or {}
            checked_ids.add(data.get("trial_id"))
    widget.blockSignals(True)
    widget.clear()
    sid = getattr(self, "_series_pk", None)
    refs = getattr(self, "_reference_names", {}) or {}
    for trial in getattr(self, "_trials", []):
        trial_id = trial.get("ID")
        if trial_id is not None and int(trial_id) in refs:
            continue
        vno = trial.get("Versuchsnummer") or trial.get("versuchsnummer") or 0
        tdms = _ys_find_tdms(sid, int(vno)) if sid else None
        item = QListWidgetItem(f"V{int(vno):03d}" + ("" if tdms else "  (kein TDMS)"))
        item.setData(Qt.UserRole, {"trial_id": trial_id, "vno": int(vno), "tdms": tdms})
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked if trial_id in checked_ids else Qt.Unchecked)
        if not tdms:
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            item.setForeground(QColor("#666"))
        widget.addItem(item)
    widget.blockSignals(False)


def _ys_run_process_comparison(self):
    """Lädt die ausgewählten TDMS-Dateien und berechnet ihre Prozesswellen."""
    from PySide6.QtCore import Qt, QRunnable, QThreadPool, QObject
    from PySide6.QtCore import Signal as _Signal

    widget = getattr(self, "_ys_compare_trial_list", None)
    selected = []
    if widget is not None:
        for row in range(widget.count()):
            item = widget.item(row)
            if item.checkState() == Qt.Checked:
                selected.append(item.data(Qt.UserRole) or {})
    if len(selected) < 2:
        self._ys_lbl_compare_status.setText("Bitte mindestens zwei Trials auswählen.")
        return
    if len(selected) > 6:
        self._ys_lbl_compare_status.setText("Bitte maximal sechs Trials gleichzeitig vergleichen.")
        return

    bin_width = float(self._ys_spin_process_wave_bin.value()
                      if self._ys_spin_process_wave_bin else 0.05)
    self._ys_btn_run_comparison.setEnabled(False)
    self._ys_lbl_compare_status.setText("Lade und analysiere vollständige Messstrecken…")

    class _Sigs(QObject):
        done = _Signal(object, str)

    class _Worker(QRunnable):
        def __init__(self, trials, bin_m, cache, sigs):
            super().__init__()
            self._trials, self._bin_m = trials, bin_m
            self._cache, self._sigs = cache, sigs
            self.setAutoDelete(True)

        def run(self):
            import numpy as np
            from ui.yarnscope.dty_analysis import _moving_average, analyze_series
            from ui.yarnscope.dty_tdms_reader import read_dty_signal, read_step_mm_from_tdms

            results, errors = [], []
            for trial in self._trials:
                try:
                    trial_id = trial.get("trial_id")
                    cached = self._cache.get(trial_id)
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
                        raise ValueError("Kein Signal")
                    y = np.asarray(y_raw, dtype=float)
                    # Vergleichswerte sind absichtlich unabhängig von der
                    # aktuellen Fensteransicht: immer die ganze Messstrecke.
                    yseg = _moving_average(y, 3)
                    x = np.arange(len(y)) * dx_mm / 1000.0
                    analysis = _ys_analyze_process_wave(x, yseg, self._bin_m)
                    if analysis is None:
                        raise ValueError("Fenster zu kurz oder unvollständige Daten")
                    reality = _ys_process_wave_reality_check(x, yseg, self._bin_m)

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
                    open_seg_x, open_seg_y = _ys_opening_segment_series(per_run, yseg, x)

                    results.append({
                        "trial_id": trial_id, "vno": trial.get("vno"),
                        "label": f'V{int(trial.get("vno") or 0):03d}',
                        "median": float(np.median(analysis["binned"])),
                        "analysis": analysis, "reality": reality, "visible": True,
                        "open_seg_x": open_seg_x, "open_seg_y": open_seg_y,
                    })
                except Exception as exc:
                    errors.append(f'V{int(trial.get("vno") or 0):03d}: {exc}')
            self._sigs.done.emit(results, "; ".join(errors))

    self._ys_compare_sigs = _Sigs()
    self._ys_compare_sigs.done.connect(
        lambda results, errors: _ys_on_process_comparison_done(self, results, errors))
    QThreadPool.globalInstance().start(_Worker(
        selected, bin_width, getattr(self, "_ys_cache", {}),
        self._ys_compare_sigs))


def _ys_on_process_comparison_done(self, results, errors: str):
    self._ys_btn_run_comparison.setEnabled(True)
    self._ys_compare_results = results
    _ys_draw_process_comparison(self, results)
    if results:
        status = (f"{len(results)} Trial(s) verglichen – Kennzahlen über die gesamte "
                  "Messstrecke, Robustheitscheck in unabhängigen 10-m-Abschnitten.")
        if errors:
            status += f" Übersprungen: {errors}"
    else:
        status = "Keine vergleichbaren Ergebnisse. " + errors
    self._ys_lbl_compare_status.setText(status)


def _ys_draw_process_comparison(self, results):
    """Zeichnet Prozessmittel und Sinus-Fits überlagert sowie die Kennzahlentabelle."""
    import numpy as np
    from PySide6.QtWidgets import QTableWidgetItem, QPushButton, QLabel
    from PySide6.QtCore import Qt

    ax = getattr(self, "_ys_compare_ax", None)
    canvas = getattr(self, "_ys_compare_canvas", None)
    table = getattr(self, "_ys_compare_table", None)
    if ax is None or canvas is None or table is None:
        return
    ax.clear()
    ax.set_facecolor("#242424")
    ax.figure.patch.set_facecolor("#1e1e1e")
    table.setRowCount(0)
    colors = ["#56d7d0", "#ff6bb5", "#ffd166", "#9b8cff", "#7ddf9a", "#ff9f1c"]
    normalized = bool(getattr(self, "_ys_chk_compare_normalized", None)
                      and self._ys_chk_compare_normalized.isChecked())
    show_process_mean = bool(getattr(self, "_ys_chk_compare_show_process_mean", None)
                             and self._ys_chk_compare_show_process_mean.isChecked())
    show_drift = bool(getattr(self, "_ys_chk_compare_show_drift", None)
                      and self._ys_chk_compare_show_drift.isChecked())
    show_open_trend = bool(getattr(self, "_ys_chk_compare_open_trend", None)
                           and self._ys_chk_compare_open_trend.isChecked())
    open_roll_mode = (self._ys_combo_compare_open_roll_mode.currentText()
                      if getattr(self, "_ys_combo_compare_open_roll_mode", None) else "Meter")
    open_roll_amount = float(self._ys_spin_compare_open_roll.value()
                             if getattr(self, "_ys_spin_compare_open_roll", None) else 1.0)

    for row, result in enumerate(results):
        analysis = result["analysis"]
        color = colors[row % len(colors)]
        offset = result["median"] if normalized else 0.0
        visible = result.get("visible", True)
        if visible and show_process_mean:
            ax.plot(analysis["x"], analysis["binned"] - offset, color=color,
                    linewidth=1.0, alpha=0.45, label=f'{result["label"]} Prozessmittel')
        if visible and show_drift:
            ax.plot(analysis["x"], analysis["drift_line"] - offset, color=color,
                    linewidth=1.25, alpha=0.9, label=f'{result["label"]} Drift')
        if visible:
            ax.plot(analysis["x"], analysis["fitted"] - offset, color=color,
                    linewidth=2.1, linestyle="--", label=f'{result["label"]} Sinus-Fit')
        if visible and show_open_trend:
            seg_x, seg_y = result.get("open_seg_x") or [], result.get("open_seg_y") or []
            if seg_x:
                trend_y, _roll_label = _ys_roll_trend(seg_x, seg_y, open_roll_mode, open_roll_amount)
                ax.plot(seg_x, np.asarray(trend_y) - offset, color=color,
                        linewidth=1.6, linestyle=":",
                        label=f'{result["label"]} Öffnungsstellen-Trend')

        table.insertRow(row)
        visibility_icon = "assets/images/visible_on.png" if visible else "assets/images/visible_off.png"
        visibility_button = QPushButton()
        visibility_button.setFixedWidth(30)
        visibility_button.setIcon(QIcon(resource_path(visibility_icon)))
        visibility_button.setIconSize(QSize(18, 18))
        visibility_button.setToolTip(
            "Trial im Diagramm ausblenden" if visible else "Trial im Diagramm einblenden")
        visibility_button.setStyleSheet(
            "QPushButton{background:#303030;color:#ddd;border:1px solid #555;border-radius:3px;}"
            "QPushButton:hover{background:#444;}")
        trial_id = result["trial_id"]
        visibility_button.clicked.connect(
            lambda _checked=False, tid=trial_id: _ys_toggle_process_comparison_trial(self, tid))
        table.setCellWidget(row, 0, visibility_button)
        color_swatch = QLabel()
        color_swatch.setFixedSize(22, 12)
        color_swatch.setToolTip(f'{result["label"]}: {color}')
        color_swatch.setStyleSheet(
            f"background:{color}; border:1px solid #ddd; border-radius:2px;")
        table.setCellWidget(row, 1, color_swatch)
        reality = result.get("reality")
        if reality:
            reality_values = [
                f'{reality["significant"]}/{reality["windows"]}',
                f'{reality["lambda_cv"] * 100:.0f} %' if reality["lambda_cv"] is not None else "—",
                f'{reality["amplitude_median"]:.2f}', f'{reality["r2_median"]:.2f}',
                reality["verdict"],
            ]
        else:
            reality_values = ["—", "—", "—", "—", "zu wenig Daten"]
        values = [
            result["label"], f'{result["median"]:.1f}',
            f'{analysis["wavelength"]:.2f}', f'{analysis["amplitude"]:.2f}',
            f'{analysis["r_squared"]:.2f}', f'{analysis["spectral_share"] * 100:.0f} %',
            f'{analysis["drift"]:.2f}', f'{analysis["residual_rms"]:.2f}',
        ] + reality_values
        for col, value in enumerate(values, start=2):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignCenter)
            if col == 2:
                item.setForeground(QColor(color))
            elif col == 14:
                verdict_colors = {
                    "robuster Wellenhinweis": "#7ddf9a",
                    "uneinheitlicher Hinweis": "#ffd166",
                    "nicht belegt": "#ff7b7b",
                }
                item.setForeground(QColor(verdict_colors.get(value, "#aaa")))
            table.setItem(row, col, item)

    if results:
        ax.set_title("Sinus-Fits der Prozesswellen" if not show_process_mean
                     else "Prozessmittel und Sinus-Fits", color="#ddd", fontsize=11)
        ax.set_xlabel("Position [m]", color="#aaa", fontsize=9)
        ax.set_ylabel("Abweichung vom Median [µm]" if normalized else "Garndicke [µm]",
                      color="#aaa", fontsize=9)
        start_m = float(self._ys_spin_start.value() if self._ys_spin_start else 0.0)
        window_m = float(self._ys_spin_window.value() if self._ys_spin_window else 3.0)
        ax.set_xlim(start_m, start_m + window_m)
        ax.tick_params(colors="#aaa", labelsize=8)
        for spine in ax.spines.values():
            spine.set_color("#555")
        ax.grid(True, alpha=0.18, color="#666")
        ax.legend(loc="upper right", fontsize=7, ncol=2,
                  facecolor="#202020", edgecolor="#555", labelcolor="#ddd")
    else:
        ax.text(0.5, 0.5, "Mindestens zwei Trials auswählen und vergleichen.",
                transform=ax.transAxes, ha="center", va="center", color="#888")
    table.resizeColumnsToContents()
    canvas.draw_idle()


def _ys_toggle_process_comparison_trial(self, trial_id):
    for result in getattr(self, "_ys_compare_results", []):
        if result.get("trial_id") == trial_id:
            result["visible"] = not result.get("visible", True)
            break
    _ys_draw_process_comparison(self, getattr(self, "_ys_compare_results", []))


def _ys_update_auto_refresh_state(self):
    """Startet/stoppt den YarnScope-Auto-Refresh-Timer.

    Laeuft nur, waehrend der YarnScope-Tab tatsaechlich der aktive Tab ist
    (kein Hintergrund-Pollen ausserhalb des Reiters) UND mindestens ein
    Trial noch ohne TDMS-File dasteht (kein Pollen mehr, sobald alles da
    ist). Wird sowohl nach jedem _ys_populate_trial_list()-Lauf als auch bei
    jedem Tab-Wechsel aufgerufen (siehe _create_yarnscope_tab_if_needed()).
    """
    timer = getattr(self, "_ys_auto_timer", None)
    if timer is None:
        return
    should_run = (
        self.tab_yarnscope is not None
        and self.tabs.currentWidget() is self.tab_yarnscope
        and not getattr(self, "_ys_all_tdms_present", False)
    )
    if should_run and not timer.isActive():
        timer.start()
    elif not should_run and timer.isActive():
        timer.stop()


def _ys_on_trial_selected(self, row: int):
    from PySide6.QtCore import Qt
    if self._ys_trial_list is None or row < 0:
        return
    item = self._ys_trial_list.item(row)
    if not item:
        return
    from db.usage_log import log_usage_event
    log_usage_event("feature", "yarnscope_dty")
    data = item.data(Qt.UserRole)
    tdms = data.get("tdms");
    tid = data.get("trial_id");
    vno = data.get("vno")
    self._ys_current_trial_id = tid
    self._ys_current_tdms = tdms
    if tdms:
        self._ys_lbl_file.setText(f"📄 {tdms.name}")
        self._ys_btn_analyze.setEnabled(True)
    else:
        self._ys_lbl_file.setText(f"V{vno} – kein TDMS-File im Ordner")
        self._ys_btn_analyze.setEnabled(False)
    # Cache-Treffer: sofort anzeigen, kein Klick auf Analysieren noetig
    if tid is not None and tid in self._ys_cache:
        res, vals = self._ys_cache[tid]
        self._ys_last_res = res
        self._ys_last_vals = vals
        self._ys_lbl_status.setText("Analyse aus Cache.")
        self._ys_btn_save.setEnabled(tid is not None)
        _ys_update_metrics(self, vals)
        _ys_replot(self)
    else:
        self._ys_last_res = {}
        self._ys_last_vals = {}
        self._ys_btn_save.setEnabled(False)
        self._ys_lbl_status.setText("")
        self._ys_lbl_metrics.setText("")
        _ys_clear_plot(self)


def _ys_clear_plot(self):
    layout = self._ys_plot_layout
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()


def _ys_on_analyze(self):
    if not self._ys_current_tdms:
        return
    # Cache-Treffer: sofort anzeigen ohne neu zu analysieren
    tid = self._ys_current_trial_id
    if tid is not None and tid in self._ys_cache:
        res, vals = self._ys_cache[tid]
        self._ys_last_res = res
        self._ys_last_vals = vals
        self._ys_lbl_status.setText("Analyse aus Cache.")
        self._ys_btn_save.setEnabled(True)
        _ys_update_metrics(self, vals)
        _ys_replot(self)
        return
    self._ys_btn_analyze.setEnabled(False)
    self._ys_btn_save.setEnabled(False)
    self._ys_lbl_status.setText("Analysiere…")

    from PySide6.QtCore import QRunnable, QThreadPool, QObject
    from PySide6.QtCore import Signal as _Sig

    class _Sigs(QObject):
        done = _Sig(dict, str)

    class _Worker(QRunnable):
        def __init__(self, path, sigs):
            super().__init__();
            self._p = path;
            self._s = sigs
            self.setAutoDelete(True)

        def run(self):
            try:
                import numpy as np
                from ui.yarnscope.dty_analysis import analyze_series
                from ui.yarnscope.dty_tdms_reader import (
                    read_dty_signal, read_step_mm_from_tdms)
                y = read_dty_signal(str(self._p))
                dx_mm = read_step_mm_from_tdms(str(self._p)) or 0.25
                if y is None or len(y) == 0:
                    self._s.done.emit({}, "Kein Signal im TDMS-File.")
                    return
                res = analyze_series(np.asarray(y, dtype=float), float(dx_mm), 3)
                res["_y_raw"] = y  # numpy-Array direkt behalten (kein .tolist() → kein teurer Copy)
                res["_dx_mm"] = float(dx_mm)
                self._s.done.emit(res, "")
            except Exception as e:
                self._s.done.emit({}, str(e))

    self._ys_sigs = _Sigs()
    self._ys_sigs.done.connect(lambda res, err: _ys_on_analysis_done(self, res, err))
    QThreadPool.globalInstance().start(_Worker(self._ys_current_tdms, self._ys_sigs))


def _ys_on_analysis_done(self, res: dict, err: str):
    self._ys_btn_analyze.setEnabled(True)
    if err:
        self._ys_lbl_status.setText(f"Fehler: {err}");
        return
    self._ys_last_res = res
    self._ys_lbl_status.setText("Extrahiere Kennzahlen…")
    # Vollständige Extraktion inkl. Flächen-Bins, Fallhöhen, Stab-Predictions
    from PySide6.QtCore import QRunnable, QThreadPool, QObject
    from PySide6.QtCore import Signal as _Sig2
    class _ESigs(QObject):
        done = _Sig2(dict)
        progress = _Sig2(str)

    class _ExtractWorker(QRunnable):
        def __init__(self, res, sigs, trial_id=None):
            super().__init__();
            self._r = res;
            self._s = sigs
            self._tid = trial_id
            self.setAutoDelete(True)

        def run(self):
            try:
                from ui.yarnscope.dty_analysis import full_extract_vals
                y_raw = self._r.get("_y_raw")
                dx_mm = float(self._r.get("_dx_mm") or 0.25)
                vals = full_extract_vals(
                    self._r, y_raw, dx_mm, 3, trial_id=self._tid,
                    progress_cb=lambda msg: self._s.progress.emit(msg))
            except Exception as e:
                from ui.dty_yarnscope_tab import _ys_extract_vals
                vals = _ys_extract_vals(self._r)
            self._s.done.emit(vals)

    self._ys_esigs = _ESigs()
    self._ys_esigs.done.connect(lambda vals: _ys_on_extract_done(self, vals))
    self._ys_esigs.progress.connect(lambda msg: self._ys_lbl_status.setText(msg))
    QThreadPool.globalInstance().start(
        _ExtractWorker(res, self._ys_esigs, getattr(self, "_ys_current_trial_id", None)))


def _ys_on_extract_done(self, vals: dict):
    self._ys_last_vals = vals
    # Ergebnis cachen (alle Trials der aktuellen Series)
    tid = getattr(self, "_ys_current_trial_id", None)
    if tid is not None and self._ys_last_res:
        self._ys_cache[tid] = (self._ys_last_res, vals)
    stab_info = []
    for key, label in [("Stab_03", "0.3"), ("Stab_06", "0.6"),
                       ("Stab_10", "1.0"), ("Stab_13", "1.3")]:
        v = vals.get(key)
        if v is not None:
            stab_info.append(f"{label}: {v:.1f}%")
    stab_str = "   ".join(stab_info) if stab_info else ""
    status = "Analyse fertig." + (f"  |  Stab: {stab_str}" if stab_str else "")
    self._ys_lbl_status.setText(status)
    self._ys_btn_save.setEnabled(self._ys_current_trial_id is not None)
    _ys_update_metrics(self, vals)
    _ys_replot(self)


def _ys_replot(self):
    """Zeichnet Plots neu – wird auch bei Aenderung von Start/Fenster aufgerufen."""
    active = getattr(self, "_ys_sub_tabs", None)
    active_idx = active.currentIndex() if active else 0
    if not self._ys_last_res:
        if active_idx == 3:
            _ys_draw_process_comparison(self, getattr(self, "_ys_compare_results", []))
        return
    # Segmentmittel immer
    _ys_draw_plots(self, self._ys_last_res, self._ys_last_vals)
    # Garnspiegel + Signal nur wenn Tab sichtbar, sonst lazy beim Tab-Wechsel
    if active_idx == 1:
        _ys_draw_garnspiegel(self, self._ys_last_res, getattr(self, "_ys_last_vals", {}))
    elif active_idx == 2:
        _ys_draw_signal(self, self._ys_last_res)
    elif active_idx == 3:
        # Start/Fenster steuern im Vergleich nur den sichtbaren Ausschnitt.
        _ys_draw_process_comparison(self, getattr(self, "_ys_compare_results", []))
    # Flag setzen damit Tab-Wechsel weiss was noch gezeichnet werden muss
    self._ys_plots_dirty = True


def _ys_update_metrics(self, vals: dict):
    from PySide6.QtCore import Qt
    def _f(key, dec=1, unit=""):
        v = vals.get(key)
        return f"{v:.{dec}f}{unit}" if v is not None else "—"

    html = (
        f'<span style="color:#ff4444; font-size:15px; font-weight:bold;">'
        f'FP/m: {_f("FPm", 1)}&nbsp;&nbsp;&nbsp;CV: {_f("CV_FP", 1, "%")}</span><br>'
        f'Ø KL: {_f("AvgKL", 2, " mm")}&nbsp;&nbsp;CV: {_f("CV_KL", 1, "%")}<br>'
        f'Ø OL: {_f("AvgOL", 2, " mm")}&nbsp;&nbsp;CV: {_f("CV_OL", 1, "%")}<br>'
        f'A: {_f("AKnots", 1, "%")}&nbsp;&nbsp;B: {_f("BKnots", 1, "%")}&nbsp;&nbsp;C: {_f("CKnots", 1, "%")}'
    )
    self._ys_lbl_metrics.setTextFormat(Qt.RichText)
    self._ys_lbl_metrics.setText(html)


def _ys_draw_plots(self, res: dict, vals: dict):
    _ys_clear_plot(self)
    try:
        import numpy as np
        import math
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.figure import Figure

        y_raw = res.get("_y_raw")
        dx_mm = float(res.get("_dx_mm") or 0.25)
        if y_raw is None:
            lbl = QLabel("No signal available.")
            lbl.setStyleSheet("color:#ff6060; padding:8px;")
            self._ys_plot_layout.addWidget(lbl)
            return

        y_arr = np.asarray(y_raw, dtype=float)
        total_m = len(y_arr) * dx_mm / 1000.0

        # Start/Fenster aus Spinboxes
        start_m = float(self._ys_spin_start.value() if self._ys_spin_start else 0.0)
        window_m = float(self._ys_spin_window.value() if self._ys_spin_window else 3.0)
        start_m = max(0.0, min(start_m, total_m))
        window_m = max(0.1, min(window_m, 100.0, total_m - start_m))

        pts_per_m = int(round(1000.0 / dx_mm))
        start_idx = int(round(start_m * pts_per_m))
        count = max(1, int(round(window_m * pts_per_m)))
        end_idx = min(start_idx + count, len(y_arr))

        # Spinbox-Max anpassen
        if self._ys_spin_start:
            self._ys_spin_start.blockSignals(True)
            self._ys_spin_start.setMaximum(max(0.0, total_m - 0.1))
            self._ys_spin_start.blockSignals(False)

        yseg = y_arr[start_idx:end_idx]
        x_axis = np.arange(start_idx, end_idx) * dx_mm / 1000.0

        # Glätten
        from ui.yarnscope.dty_analysis import _moving_average
        y_smooth = _moving_average(yseg, 3)

        # Threshold + Klassengrenzen
        T = res.get("threshold")
        cls_info = res.get("classes") or {}
        thr = cls_info.get("thresholds", (None, None))
        try:
            tA, tB = thr if not isinstance(thr, dict) else (thr.get("tA"), thr.get("tB"))
        except Exception:
            tA, tB = None, None
        y_cb = (float(T) - tA) if (T is not None and tA is not None) else None
        y_ba = (float(T) - tB) if (T is not None and tB is not None) else None

        def _class_from_mean(mv):
            lo = y_cb if y_cb is not None else float("nan")
            hi = y_ba if y_ba is not None else float("nan")
            if not math.isfinite(lo) or not math.isfinite(hi):
                lo, hi = (min(lo, hi), max(lo, hi)) if (math.isfinite(lo) and math.isfinite(hi)) else (float("nan"),
                                                                                                       float("nan"))
            lo2, hi2 = (min(lo, hi), max(lo, hi))
            if math.isfinite(lo2) and mv <= lo2: return "A"
            if math.isfinite(hi2) and mv <= hi2: return "B"
            return "C"

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
        open_knot_enabled = bool(getattr(self, "_ys_chk_delta_trend", None)
                                 and self._ys_chk_delta_trend.isChecked())
        if open_knot_enabled:
            open_knot_trend_x, raw_midpoints = _ys_open_knot_midpoints(
                open_segs, knot_segs, x_axis)
            roll_mode = (self._ys_combo_delta_roll_mode.currentText()
                         if self._ys_combo_delta_roll_mode else "Meter")
            roll_amount = float(self._ys_spin_delta_roll.value() if self._ys_spin_delta_roll else 1.0)
            open_knot_trend_y, open_knot_roll_label = _ys_roll_trend(
                open_knot_trend_x, raw_midpoints, roll_mode, roll_amount)

        peak_valley_trend_x, peak_valley_trend_y, peak_valley_roll_label = [], [], ""
        peak_valley_enabled = bool(getattr(self, "_ys_chk_peak_valley_trend", None)
                                  and self._ys_chk_peak_valley_trend.isChecked())
        if peak_valley_enabled:
            peak_valley_trend_x, raw_midpoints = _ys_peak_valley_midpoints(y_smooth, x_axis)
            roll_mode = (self._ys_combo_peak_valley_roll_mode.currentText()
                         if self._ys_combo_peak_valley_roll_mode else "Meter")
            roll_amount = float(self._ys_spin_peak_valley_roll.value()
                                if self._ys_spin_peak_valley_roll else 1.0)
            peak_valley_trend_y, peak_valley_roll_label = _ys_roll_trend(
                peak_valley_trend_x, raw_midpoints, roll_mode, roll_amount)

        # Öffnungsstellen-Trend (Nutzerwunsch 2026-09-08): rollender Mittelwert
        # NUR über die grünen Öffnungsstellen-Segmentmittel (open_segs, siehe
        # unten), ohne Knoten-Mischung wie bei open_knot_trend.
        opening_trend_x, opening_trend_y, opening_roll_label = [], [], ""
        opening_enabled = bool(getattr(self, "_ys_chk_opening_trend", None)
                               and self._ys_chk_opening_trend.isChecked())
        if opening_enabled:
            opening_trend_x = [float(x_axis[int(g[len(g) // 2])]) for g, _mv in open_segs if len(g)]
            raw_values = [mv for g, mv in open_segs if len(g)]
            roll_mode = (self._ys_combo_opening_roll_mode.currentText()
                         if self._ys_combo_opening_roll_mode else "Meter")
            roll_amount = float(self._ys_spin_opening_roll.value()
                                if self._ys_spin_opening_roll else 1.0)
            opening_trend_y, opening_roll_label = _ys_roll_trend(
                opening_trend_x, raw_values, roll_mode, roll_amount)

        process_wave_enabled = bool(getattr(self, "_ys_chk_process_wave", None)
                                    and self._ys_chk_process_wave.isChecked())
        process_wave = None
        if process_wave_enabled:
            bin_width = float(self._ys_spin_process_wave_bin.value()
                              if self._ys_spin_process_wave_bin else 0.05)
            process_wave = _ys_analyze_process_wave(x_axis, y_smooth, bin_width)

        _ys_update_trend_metric_card(
            getattr(self, "_ys_lbl_open_knot_metrics", None), "Mitte Öffnung–Knoten",
            "#56d7d0", open_knot_enabled, open_knot_trend_x, open_knot_trend_y)
        _ys_update_trend_metric_card(
            getattr(self, "_ys_lbl_peak_valley_metrics", None), "Mitte Peak–Tal",
            "#ff6bb5", peak_valley_enabled, peak_valley_trend_x, peak_valley_trend_y)
        _ys_update_trend_metric_card(
            getattr(self, "_ys_lbl_opening_metrics", None), "Öffnungsstellen-Trend",
            "#8de6a0", opening_enabled, opening_trend_x, opening_trend_y)
        _ys_update_process_wave_card(
            getattr(self, "_ys_lbl_process_wave_metrics", None), process_wave,
            process_wave_enabled)

        # ── Figure: Segmentmittel (gross) + ABC-Pie (klein rechts) ────────
        fig = Figure(facecolor="#242424")
        # 2 Spalten: Segmentmittel 82%, Pie 18%
        gs = fig.add_gridspec(1, 2, width_ratios=[5, 1],
                              left=0.05, right=0.98, top=0.90, bottom=0.12, wspace=0.05)
        ax = fig.add_subplot(gs[0])
        axp = fig.add_subplot(gs[1])

        ax.set_facecolor("#2e2e2e")
        ax.plot(x_axis, y_smooth, color="#c9d2e3", linewidth=0.7, alpha=0.7)
        if process_wave is not None:
            ax.plot(process_wave["x"], process_wave["binned"], color="#ffd166",
                    linewidth=1.0, alpha=0.8,
                    label=f'Prozessmittel ({process_wave["bin_width"]:.2f} m)')
            ax.plot(process_wave["x"], process_wave["fitted"], color="#ff9f1c",
                    linewidth=2.0,
                    label=f'Sinus-Fit ({process_wave["wavelength"]:.2f} m)')

        A_cnt = B_cnt = C_cnt = 0
        seen = set()
        COLOR = {"A": "#e05050", "B": "#f0a030", "C": "#9060c0"}

        for g, mv in open_segs:
            lbl = "Opening: medium" if "Opening: medium" not in seen else None
            ax.plot(x_axis[g], [mv] * len(g), color="#39A650", linewidth=1.8, label=lbl)
            if lbl: seen.add(lbl)

        for g, mv in knot_segs:
            cls = _class_from_mean(mv)
            col = COLOR[cls]
            lbl_key = f"Knoten {cls}: Mittel"
            lbl = lbl_key if lbl_key not in seen else None
            ax.plot(x_axis[g], [mv] * len(g), color=col, linewidth=2.0, label=lbl)
            if lbl: seen.add(lbl)
            if cls == "A":
                A_cnt += 1
            elif cls == "B":
                B_cnt += 1
            else:
                C_cnt += 1

        if T is not None and math.isfinite(float(T)):
            ax.axhline(float(T), color="#888", ls="--", lw=0.9, label="Schwelle T")
        if y_cb is not None and math.isfinite(y_cb):
            ax.axhline(y_cb, color="magenta", ls=":", lw=0.9, label="C/B-Grenze")
        if y_ba is not None and math.isfinite(y_ba):
            ax.axhline(y_ba, color="#b080ff", ls="-.", lw=0.9, label="B/A-Grenze")

        ax.text(0.99, 0.02, f"A: {A_cnt}  B: {B_cnt}  C: {C_cnt}",
                transform=ax.transAxes, ha="right", va="bottom", fontsize=8,
                color="#ddd", bbox=dict(facecolor="#222", alpha=0.7, edgecolor="#555"))
        ax.set_xlim(start_m, start_m + window_m)
        ax.set_xlabel("Position [m]", color="#888", fontsize=8)
        ax.set_ylabel("Garndicke [µm]", color="#888", fontsize=8)
        ax.set_title("Segmentmittel", color="#ddd", fontsize=10)
        ax.tick_params(colors="#888", labelsize=7)
        for sp in ax.spines.values(): sp.set_color("#333")
        ax.grid(True, axis="y", alpha=0.2, color="#444")

        if open_knot_trend_x or peak_valley_trend_x or opening_trend_x:
            if open_knot_trend_x:
                ax.plot(
                    open_knot_trend_x, open_knot_trend_y, color="#56d7d0", linewidth=1.8,
                    label=f"Mitte Öffnung–Knoten (roll. Ø {open_knot_roll_label})")
            if peak_valley_trend_x:
                ax.plot(
                    peak_valley_trend_x, peak_valley_trend_y, color="#ff6bb5", linewidth=1.8,
                    label=f"Mitte Peak–Tal (roll. Ø {peak_valley_roll_label})")
            if opening_trend_x:
                ax.plot(
                    opening_trend_x, opening_trend_y, color="#8de6a0", linewidth=1.8,
                    label=f"Öffnungsstellen-Trend (roll. Ø {opening_roll_label})")

        handles, labels = ax.get_legend_handles_labels()
        seen2 = set();
        h2 = [];
        l2 = []
        for h, l in zip(handles, labels):
            if l and l not in seen2:
                seen2.add(l);
                h2.append(h);
                l2.append(l)
        if h2:
            ax.legend(h2, l2, loc="upper left", fontsize=7,
                      facecolor="#222", edgecolor="#555", labelcolor="#ddd")

        # ── ABC-Pie ────────────────────────────────────────────────────────
        axp.set_facecolor("#242424")
        a = vals.get("AKnots") or 0.0
        b = vals.get("BKnots") or 0.0
        c = vals.get("CKnots") or 0.0
        if a + b + c > 0:
            axp.pie([a, b, c],
                    labels=[f"A\n{a:.0f}%", f"B\n{b:.0f}%", f"C\n{c:.0f}%"],
                    colors=["#e05050", "#f0a030", "#9060c0"],
                    textprops={"color": "#ddd", "fontsize": 7},
                    startangle=90)
        else:
            axp.text(0.5, 0.5, "—", ha="center", va="center",
                     color="#555", transform=axp.transAxes, fontsize=14)
        axp.set_title("ABC", color="#ddd", fontsize=8)

        canvas = FigureCanvasQTAgg(fig)
        canvas.setStyleSheet("background:#2a2a2a;")
        self._ys_plot_layout.addWidget(canvas)
        canvas.draw()

    except Exception as e:
        import traceback
        lbl = QLabel(f"Plot-Fehler: {e}")
        lbl.setStyleSheet("color:#ff6060; padding:8px;")
        self._ys_plot_layout.addWidget(lbl)


def _ys_on_save(self):
    tid = self._ys_current_trial_id
    vals = getattr(self, "_ys_last_vals", {})
    if not tid or not vals:
        return
    try:
        from ui.screen_tdms_batch import _save_analysis_to_db
        ok = _save_analysis_to_db(tid, vals)
    except Exception as e:
        self._ys_lbl_status.setText(f"Fehler: {e}");
        return
    if ok:
        self._ys_lbl_status.setText("Gespeichert.")
        self._ys_btn_save.setEnabled(False)
        _ys_populate_trial_list(self)
    else:
        self._ys_lbl_status.setText("Speichern fehlgeschlagen.")


def _ys_open_batch(self):
    """Öffnet TDMSBatchScreen gefiltert auf die aktuelle TrialSeries."""
    try:
        from ui.screen_tdms_batch import TDMSBatchScreen
        sid = self._series_pk
        sname = ""
        # Series-Name aus Label holen
        try:
            sname = self.lbl_small_title.text() if hasattr(self, "lbl_small_title") else ""
        except Exception:
            pass
        # Screen lazy-init auf dem MainWindow
        mw = self.window()
        if not hasattr(mw, "tdms_batch") or mw.tdms_batch is None:
            _sb_kwargs = mw._sidebar_nav_kwargs() if hasattr(mw, "_sidebar_nav_kwargs") else None
            mw.tdms_batch = TDMSBatchScreen(
                on_back_home=lambda: mw.stack.setCurrentWidget(self),
                locked_series_id=sid,
                locked_series_name=sname,
                sidebar_callbacks=_sb_kwargs,
            )
            mw.stack.addWidget(mw.tdms_batch)
        else:
            # Bestehenden Screen neu konfigurieren
            mw.tdms_batch._locked_series_id = sid
            mw.tdms_batch._locked_series_name = sname
            mw.tdms_batch._insider_mode = False
            mw.tdms_batch._on_back_home = lambda: mw.stack.setCurrentWidget(self)
        mw.setWindowTitle(f"TrippleT – YarnScope Batch")
        mw.stack.setCurrentWidget(mw.tdms_batch)
        # Init-State neu setzen (Dropdown verstecken + auto-scan)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, mw.tdms_batch._init_series_state)
    except Exception as e:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Batch", f"Fehler: {e}")


def _ys_draw_garnspiegel(self, res: dict, vals: dict = None):
    """Zeichnet den Garnspiegel mit ABC-Knoten-Einfaerbung ab aktuellem Startpunkt."""
    canvas = getattr(self, "_ys_garn_canvas", None)
    if canvas is None:
        return
    try:
        import numpy as np
        import math
        from ui.yarnscope.dty_analysis import _moving_average

        y_raw = res.get("_y_raw")
        dx_mm = float(res.get("_dx_mm") or 0.25)
        if y_raw is None or len(y_raw) == 0:
            return

        y_um_full = np.asarray(y_raw, dtype=float)
        if float(np.median(y_um_full)) < 50.0:
            y_um_full = y_um_full * 1000.0

        # ── Startpunkt aus Spinbox (identisch zum Segmentmittel-Plot) ────────
        total_m = len(y_um_full) * dx_mm / 1000.0
        start_m = float(getattr(self, "_ys_spin_start", None) and self._ys_spin_start.value() or 0.0)
        start_m = max(0.0, min(start_m, total_m))
        pts_per_m = int(round(1000.0 / dx_mm))
        start_idx = int(round(start_m * pts_per_m))

        # Ab Startpunkt schneiden – per_run Indizes entsprechend verschieben
        y_um = y_um_full[start_idx:]
        y_smooth = _moving_average(y_um, 3)

        # ── Schwellenwerte ───────────────────────────────────────────────────
        T = res.get("threshold")
        cls_info = res.get("classes") or {}
        thr = cls_info.get("thresholds", (None, None))
        try:
            tA, tB = thr if not isinstance(thr, dict) else (thr.get("tA"), thr.get("tB"))
        except Exception:
            tA, tB = None, None
        y_cb = (float(T) - tA) if (T is not None and tA is not None) else None
        y_ba = (float(T) - tB) if (T is not None and tB is not None) else None

        def _class_from_mean(mv):
            lo = y_cb if y_cb is not None else float("nan")
            hi = y_ba if y_ba is not None else float("nan")
            lo2, hi2 = min(lo, hi), max(lo, hi)
            if math.isfinite(lo2) and mv <= lo2: return "A"
            if math.isfinite(hi2) and mv <= hi2: return "B"
            return "C"

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

        COLOR_ABC = {"A": "#e05050", "B": "#f0a030", "C": "#9060c0"}
        COLOR_OPEN = "#3a6a4a"  # gedaempftes Dunkelgruen fuer Oeffnungen

        # Bandbreite direkt aus absolutem Signal normiert auf Segment-Mittelwert.
        # Duennstellen (Knoten) -> kleiner Wert -> schmaleres Band.
        # Dickstellen (Oeffnungen) -> groesserer Wert -> breiteres Band.
        seg_mean = float(np.mean(y_smooth))
        clip = seg_mean  # Normierungsreferenz

        canvas.plot_garnspiegel_dty(
            y_dev=y_smooth,  # absolutes Signal, nicht Abweichung
            clip_um=clip,
            per_run=per_run,
            class_fn=_class_from_mean,
            color_abc=COLOR_ABC,
            color_open=COLOR_OPEN,
            dx_mm=dx_mm,
            y_um=y_um,
            num_turns=20,
        )
    except Exception as _e:
        import traceback
        traceback.print_exc()


def _ys_draw_signal(self, res: dict):
    """Zeichnet das Signal-Tab: Garndicke als Balken ueber Position [m],
    mit Schwelle T, A/B- und B/C-Grenzen. Reagiert auf Start + Fenster."""
    ax = getattr(self, "_ys_ax_signal", None)
    canvas = getattr(self, "_ys_canvas_signal", None)
    if ax is None or canvas is None:
        return
    try:
        import numpy as np
        import math
        from ui.yarnscope.dty_analysis import _moving_average

        y_raw = res.get("_y_raw")
        dx_mm = float(res.get("_dx_mm") or 0.25)
        if y_raw is None or len(y_raw) == 0:
            ax.clear();
            canvas.draw_idle();
            return

        y_um = np.asarray(y_raw, dtype=float)
        if float(np.median(y_um)) < 50.0:
            y_um = y_um * 1000.0

        # Glaetten wie Segmentmittel (k=3)
        y_smooth = _moving_average(y_um, 3)

        total_m = len(y_smooth) * dx_mm / 1000.0
        start_m = float(self._ys_spin_start.value() if self._ys_spin_start else 0.0)
        window_m = float(self._ys_spin_window.value() if self._ys_spin_window else 3.0)
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
        T = res.get("threshold")
        cls_info = res.get("classes") or {}
        thr = cls_info.get("thresholds", (None, None))
        try:
            tA, tB = thr if not isinstance(thr, dict) else (thr.get("tA"), thr.get("tB"))
        except Exception:
            tA, tB = None, None
        y_ab = (float(T) - tA) if (T is not None and tA is not None) else None
        y_bc = (float(T) - tB) if (T is not None and tB is not None) else None

        ax.clear()
        ax.set_facecolor("#1e1e1e")
        ax.figure.patch.set_facecolor("#1e1e1e")

        # Signal als Balken
        ax.bar(x_abs, yseg, width=step_m, align='edge',
               color="#c9d2e3", linewidth=0)

        # Schwellenlinien
        if T is not None and math.isfinite(float(T)):
            ax.axhline(float(T), color='#ff4444', linestyle='--',
                       linewidth=1.5, label=f"T = {T:.1f} µm")
        if y_ab is not None and math.isfinite(y_ab):
            ax.axhline(y_ab, color='#ff88cc', linestyle=':',
                       linewidth=1.2, label=f"A/B = {y_ab:.1f} µm")
        if y_bc is not None and math.isfinite(y_bc):
            ax.axhline(y_bc, color='#aa66ff', linestyle='-.',
                       linewidth=1.2, label=f"B/C = {y_bc:.1f} µm")

        # Y-Limits: nicht bei 0 beginnen
        candidates = [float(np.min(yseg)), float(np.max(yseg))]
        for v in (T, y_ab, y_bc):
            if v is not None and math.isfinite(float(v)):
                candidates.append(float(v))
        y_min, y_max = min(candidates), max(candidates)
        rng = max(y_max - y_min, 1.0)
        ax.set_ylim(y_min - rng * 0.05, y_max + rng * 0.05)
        ax.set_xlim(x_abs[0], x_abs[0] + window_m)

        ax.set_xlabel("Position [m]", color="#888", fontsize=8)
        ax.set_ylabel("Garndicke [µm]", color="#888", fontsize=8)
        ax.tick_params(colors="#888", labelsize=7)
        for sp in ax.spines.values(): sp.set_color("#333")
        ax.grid(True, axis="y", alpha=0.2, color="#444")
        if T is not None or y_ab is not None:
            ax.legend(loc="best", fontsize=7,
                      facecolor="#222", edgecolor="#555", labelcolor="#ddd")

        canvas.draw_idle()
    except Exception as _e:
        import traceback;
        traceback.print_exc()


def _ys_on_refresh(self):
    """Aktualisiert den gesamten show_experiment Screen."""
    try:
        exp_pk = getattr(self, '_exp_pk', None)
        series_pk = getattr(self, '_series_pk', None)
        exp_id = getattr(self, '_experiment_id_txt', '')
        if exp_pk is not None and series_pk is not None:
            self.load_record(exp_pk, series_pk, exp_id)
    except Exception as e:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(self, 'Fehler', str(e))

