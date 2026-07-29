from __future__ import annotations
# ui/yarnscope/dty_analysis.py
"""Kern-Algorithmen für die DTY-Intermingling-Analyse (YarnScope).

Dieses Modul enthält alle Berechnungen für die Knoten-Erkennung und
statistische Auswertung von DTY-Dickenmessungen aus TDMS-Dateien.

Hauptfunktion:
    ``analyze_series(y, step_mm, ...)``  → vollständige Analyse eines Signals

Pipeline:
    1. Glättung des Rohsignals (3-Punkt gleitender Durchschnitt)
    2. Otsu-Schwellwert-Bestimmung (adaptiv, 256 Bins)
    3. Labeling mit Hysterese (verhindert Flatttern um den Schwellwert)
    4. Zusammenführen kurzer Runs (Mindestlänge konfigurierbar)
    5. Klassifizierung: DTY-Knoten vs. Nicht-Knoten
    6. Statistische Kennzahlen: Knoten/m, Rapport-CV, Stabilität, Schiefe, Kurtosis

ML-Integration:
    ``run_stab_models(vals)``  → lädt XGBoost-Modelle und sagt Stabilitätswerte vorher
    Modelle liegen in ``models/`` neben der ausführbaren Datei oder im App-Root.

Abhängigkeiten:
    numpy, scipy (optional für Autocorrelation), xgboost (optional für ML)
"""

# ui/yarnscope/dty_analysis.py
"""
DTY Garn-Analyse Backend fuer TrippleT.
Extrahiert aus dty_knots_view.py (YarnScope) – nur reine Analyse-Funktionen,
keine GUI-, DB- oder ML-Abhaengigkeiten.
"""
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
import re

# ---------------------------------------------------------------------------
# Optionaler Numba-JIT für performance-kritische Loops (~50-100x schneller)
# ---------------------------------------------------------------------------
try:
    from numba import njit as _njit
    _NUMBA_AVAILABLE = True
except ImportError:
    def _njit(*args, **kwargs):  # No-Op Fallback
        def _wrap(fn): return fn
        return _wrap if (args and callable(args[0])) else _wrap
    _NUMBA_AVAILABLE = False

# Modul-Level Konstanten (aus dty_knots_view.py)
SEGMENT_CV_ENABLED = False   # Segmentiertes CV deaktiviert (kein UI-Toggle noetig)
SEG_LEN_M          = 0.10    # 10 cm Segmentlaenge (Default)

try:
    from ui.yarnscope.dty_tdms_reader import (
        read_first_numeric_channel, read_step_mm_from_tdms, points_per_meter
    )
except Exception:
    read_first_numeric_channel = None
    read_step_mm_from_tdms = None
    points_per_meter = None


def _moving_average(y: np.ndarray, k: int = 3) -> np.ndarray:
    """Berechnet einen zentrierten gleitenden Durchschnitt der Breite k.

    Verwendet scipy.ndimage.uniform_filter1d (schneller als np.convolve,
    kein manuelles Padding nötig).

    Args:
        y: Eingangssignal als numpy-Array.
        k: Fensterbreite (Standard: 3 Punkte).

    Returns:
        Geglättetes Array gleicher Länge (Randeffekte durch 'nearest'-Padding).
    """
    if k <= 1:
        return y.astype(float, copy=True)
    k = int(k)
    if k % 2 == 0:
        k += 1
    try:
        from scipy.ndimage import uniform_filter1d
        return uniform_filter1d(y.astype(float), size=k, mode='nearest')
    except ImportError:
        # Fallback auf np.convolve wenn scipy nicht verfügbar
        pad = k // 2
        ypad = np.pad(y.astype(float), (pad, pad), mode='edge')
        kernel = np.ones(k) / k
        return np.convolve(ypad, kernel, mode='valid')


def _linear_crossing(y0: float, y1: float, level: float) -> float:
    """Berechnet den interpolierten Kreuzungspunkt eines Signals mit einem Level.

    Gibt 0.0 zurück wenn y0 == y1 (kein Übergang).
    """
    dy = (y1 - y0)
    if dy == 0:
        return 0.0
    t = (level - y0) / dy
    if t < 0.0:
        t = 0.0
    if t > 1.0:
        t = 1.0
    return t

# -------------------- Analyse-Logik --------------------


def _otsu_threshold(x: np.ndarray, bins: int = 256) -> float:
    """Bestimmt den optimalen Schwellwert via Otsu-Methode.

    Minimiert die intra-Klassen-Varianz zwischen zwei Klassen
    (Nicht-Knoten und Knoten-Bereiche).

    Args:
        x:    Eingangssignal (numpy-Array).
        bins: Anzahl Histogramm-Bins (Standard: 256).

    Returns:
        Optimaler Schwellwert als float.
    """
    hist, edges = np.histogram(x, bins=bins)
    p = hist.astype(float) / max(hist.sum(), 1)
    omega = np.cumsum(p)
    centers = (edges[:-1] + edges[1:]) / 2.0
    mu = np.cumsum(p * centers)
    mu_t = mu[-1]
    denom = omega * (1 - omega)
    denom[denom == 0] = np.nan
    sigma_b2 = (mu_t * omega - mu) ** 2 / denom
    k = np.nanargmax(sigma_b2)
    return float((edges[k] + edges[k + 1]) / 2.0)


@_njit(cache=True)
def _label_with_hysteresis_jit(x: np.ndarray, T_low: float, T_high: float) -> np.ndarray:
    """JIT-kompilierter Kern für Hysterese-Labeling (Numba)."""
    n = len(x)
    labels = np.zeros(n, dtype=np.uint8)
    state = np.uint8(1) if x[0] > (T_low + T_high) * 0.5 else np.uint8(0)
    for i in range(n):
        v = x[i]
        if state == 0 and v > T_high:
            state = np.uint8(1)
        elif state == 1 and v < T_low:
            state = np.uint8(0)
        labels[i] = state
    return labels


def _label_with_hysteresis(x: np.ndarray, T: float, h: float) -> np.ndarray:
    """Labelt Signalpunkte mit Hysterese: 1 = Knoten, 0 = kein Knoten.

    Hysterese verhindert Flattern um den Schwellwert T:
    - Knoten beginnt bei x >= T + h
    - Knoten endet bei x <= T - h

    Args:
        x: Signal-Array.
        T: Schwellwert (z.B. Otsu-Threshold).
        h: Hysterese-Breite (halbe Bandbreite um T).
    """
    T_low, T_high = T - h, T + h
    if _NUMBA_AVAILABLE:
        return _label_with_hysteresis_jit(np.ascontiguousarray(x, dtype=np.float64), T_low, T_high)
    # Fallback: pure Python
    labels = np.zeros(len(x), dtype=np.uint8)
    state = 1 if x[0] > T else 0
    for i, v in enumerate(x):
        if state == 0 and v > T_high:
            state = 1
        elif state == 1 and v < T_low:
            state = 0
        labels[i] = state
    return labels


@_njit(cache=True)
def _merge_short_runs_jit(lab: np.ndarray, min_pts: int) -> np.ndarray:
    """JIT-kompilierter Kern für Run-Merge (Numba)."""
    n = len(lab)
    i = 0
    while i < n:
        j = i
        while j < n and lab[j] == lab[i]:
            j += 1
        run_len = j - i
        if run_len < min_pts:
            if i > 0:
                fill = lab[i - 1]
            elif j < n:
                fill = lab[j]
            else:
                fill = lab[i]
            for k in range(i, j):
                lab[k] = fill
        i = j
    return lab


def _merge_short_runs(labels: np.ndarray, min_pts: int) -> np.ndarray:
    """Entfernt Runs die kürzer als min_pts Punkte sind (Rauschen-Unterdrückung).

    Zu kurze Runs werden auf 0 gesetzt (kein Knoten).
    """
    if min_pts <= 1:
        return labels
    lab = labels.copy()
    if _NUMBA_AVAILABLE:
        return _merge_short_runs_jit(lab, int(min_pts))
    # Fallback: pure Python
    i = 0
    n = len(lab)
    while i < n:
        j = i
        while j < n and lab[j] == lab[i]:
            j += 1
        run_len = j - i
        if run_len < min_pts:
            if i > 0:
                lab[i:j] = lab[i - 1]
            elif j < n:
                lab[i:j] = lab[j]
        i = j
    return lab


def _runs_from_labels(labels: np.ndarray) -> list[tuple[int, int, int]]:
    """Extrahiert zusammenhängende Runs aus einem Label-Array.

    Returns:
        Liste von (start_idx, end_idx, label)-Tupeln.
    """
    runs = []
    i = 0
    n = len(labels)
    while i < n:
        j = i
        while j < n and labels[j] == labels[i]:
            j += 1
        runs.append((int(labels[i]), i, j))
        i = j
    return runs


def _pairwise_rapport_lengths_mm(runs: List[Tuple[int, int, int]], dx_mm: float) -> List[float]:
    """Berechnet die Rapport-Längen (Knoten-zu-Knoten-Abstände) in mm.

    Args:
        runs:  Liste von (start, end, label)-Runs (nur Knoten-Runs = label 1).
        dx_mm: Messschrittweite in mm.

    Returns:
        Liste von Rapport-Längen in mm.
    """
    rl = []
    for idx in range(len(runs) - 1):
        cls_i, s_i, e_i = runs[idx]
        cls_j, s_j, e_j = runs[idx + 1]
        if cls_i == 0 and cls_j == 1:
            len_k = (e_i - s_i) * dx_mm
            len_o = (e_j - s_j) * dx_mm
            rl.append(len_k + len_o)
    return rl


def _knot_starts_interpolated(y_det: np.ndarray, labels: np.ndarray, T: float) -> List[float]:
    """Berechnet interpolierte Startpositionen der Knoten (sub-sample Präzision)."""
    starts = []
    for i in range(1, len(labels)):
        if labels[i - 1] == 1 and labels[i] == 0:
            t = _linear_crossing(y_det[i - 1], y_det[i], T)
            starts.append((i - 1) + t)
    return starts


def _classify_knot_runs(
    # Klassifiziert Runs als Knoten oder Nicht-Knoten anhand von Tiefe, Breite und Flanken.
    # Hauptklassifizierung für die Standard DTY-Analyse.
    x: np.ndarray,
    runs: List[Tuple[int, int, int]],
    T: float,
    ab_pct: float,
    bc_pct: float,
) -> Dict[str, Any]:
    """
    Classify knot runs by mean of the run:
    - D_ref from 95th percentile of distances (T - x[knot])
    - tA = ab_pct% of D_ref, tB = bc_pct% of D_ref
    - For each knot run: y_mean = mean(x[s:e]); d_mean = T - y_mean
    A if d_mean <= tA; B if <= tB; else C
    """
    knot_mask = x < T
    if not np.any(knot_mask):
        return dict(ref_distance=np.nan, thresholds=(np.nan, np.nan), per_run=[], counts=dict(A=0, B=0, C=0))

    d_all = (T - x[knot_mask]).astype(float)
    D_ref = float(np.percentile(d_all, 95)) if d_all.size else np.nan
    if D_ref <= 0 or not np.isfinite(D_ref):
        D_ref = float(np.max(d_all)) if d_all.size else np.nan

    tA = (ab_pct / 100.0) * D_ref if np.isfinite(D_ref) else np.nan
    tB = (bc_pct / 100.0) * D_ref if np.isfinite(D_ref) else np.nan

    per_run: List[Tuple[int, int, int, str, float]] = []
    counts = dict(A=0, B=0, C=0)

    for cls, s, e in runs:
        if cls != 0:
            continue
        segment = x[s:e].astype(float)
        if segment.size == 0:
            klasse = "A"
            metric = 0.0
        else:
            y_mean = float(np.mean(segment))
            d_mean = float(T - y_mean)
            metric = d_mean
            if not np.isfinite(tA) or not np.isfinite(tB):
                klasse = "C"
            elif d_mean <= tA:
                klasse = "C"
            elif d_mean <= tB:
                klasse = "B"
            else:
                klasse = "A"
        per_run.append((s, e, 0, klasse, metric))
        counts[klasse] += 1

    return dict(ref_distance=D_ref, thresholds=(tA, tB), per_run=per_run, counts=counts)



def _classify_knot_runs_20(
    # Klassifizierung für den erweiterten 20-Spannungsstufen-Modus.
    x: np.ndarray,
    runs: List[Tuple[int, int, int]],
    T: float,
) -> Dict[str, Any]:
    """20-stufige Klassifikation (a–t) nach derselben Prozent-Schwellenlogik wie A/B/C.

    Referenz:
    - D_ref = 95%-Perzentil der Distanzen d = (T - x) im Knotenbereich (x < T)
    - Schwellen = 5%, 10%, ..., 95% von D_ref (19 Schwellen)

    Zuordnung (schwach → stark):
      d_mean <=  5%  -> t
      d_mean <= 10%  -> s
      ...
      d_mean <= 95%  -> b
      d_mean >  95%  -> a

    Für jeden Knoten-Run wird d_mean = T - mean(x[s:e]) berechnet.
    """
    classes = list("abcdefghijklmnopqrst")  # a = stärkste, t = schwächste

    knot_mask = x < T
    if not np.any(knot_mask):
        return dict(ref_distance=np.nan, thresholds=[np.nan] * 19, per_run=[], counts={c: 0 for c in classes})

    d_all = (T - x[knot_mask]).astype(float)
    D_ref = float(np.percentile(d_all, 95)) if d_all.size else np.nan
    if not np.isfinite(D_ref) or D_ref <= 0:
        D_ref = float(np.max(d_all)) if d_all.size else np.nan

    thresholds = [(i / 20.0) * D_ref for i in range(1, 20)] if np.isfinite(D_ref) else [np.nan] * 19

    # Schwellen-Index k (1..19) -> Buchstabe:
    # 1->t, 2->s, ..., 19->b, >19->a
    idx_to_letter = {
        1: "t",
        2: "s",
        3: "r",
        4: "q",
        5: "p",
        6: "o",
        7: "n",
        8: "m",
        9: "l",
        10: "k",
        11: "j",
        12: "i",
        13: "h",
        14: "g",
        15: "f",
        16: "e",
        17: "d",
        18: "c",
        19: "b",
    }

    per_run: List[Tuple[int, int, int, str, float]] = []
    counts = {c: 0 for c in classes}

    for cls, s, e in runs:
        if cls != 0:
            continue

        segment = x[s:e].astype(float)
        if segment.size == 0 or not np.isfinite(D_ref):
            letter = "t"
            metric = 0.0
        else:
            y_mean = float(np.mean(segment))
            d_mean = float(T - y_mean)
            metric = d_mean

            # Default: stärkste Klasse (a) wenn > 95%
            letter = "a"
            if all(np.isfinite(t) for t in thresholds):
                for k, t in enumerate(thresholds, start=1):
                    if d_mean <= t:
                        letter = idx_to_letter[k]
                        break
            else:
                letter = "t"

        per_run.append((s, e, 0, letter, metric))
        counts[letter] += 1

    return dict(ref_distance=D_ref, thresholds=thresholds, per_run=per_run, counts=counts)

def _stats(arr: List[float]) -> Dict[str, float]:
    """Berechnet Basis-Statistiken (mean, std, cv, min, max) für eine Liste von Werten."""
    """Simple stats helper.

    Returns dict with:
        mean, sd (sample, ddof=1), cv (%), n, max
    """
    if len(arr) == 0:
        return dict(mean=np.nan, sd=np.nan, cv=np.nan, n=0, max=np.nan)
    a = np.asarray(arr, float)
    m = float(a.mean())
    sd = float(a.std(ddof=1)) if a.size > 1 else 0.0
    cv = 100.0 * sd / m if m > 0 else np.nan
    mx = float(a.max()) if a.size else np.nan
    return dict(mean=m, sd=sd, cv=cv, n=int(a.size), max=mx)


def _skewness(arr: List[float]) -> float:
    """Berechnet die Schiefe (Skewness) einer Verteilung."""
    """Biased skewness (3rd standardised moment) ohne scipy-Abhängigkeit.

    Interpretationshilfe (für KL/OL-Längen):
        > 0  : rechts-schief – viele kurze Segmente, wenige sehr lange (üblich)
        ~ 0  : symmetrisch
        < 0  : links-schief – ungewöhnlich, deutet auf bimodale Verteilung hin
    Gibt np.nan zurück wenn n < 3 oder StdAbw == 0.
    """
    a = np.asarray(arr, dtype=float)
    a = a[np.isfinite(a)]
    if a.size < 3:
        return np.nan
    m = float(a.mean())
    s = float(a.std(ddof=1))
    if s == 0.0:
        return 0.0
    return float(np.mean(((a - m) / s) ** 3))


def _rapport_cv_local(periods_mm: List[float], window: int = 10) -> float:
    """Berechnet den lokalen Rapport-CV (gleitender CV über window Rapporte)."""
    """Lokaler Rapport-CV: Median aller CVs über gleitendes Fenster von `window` aufeinanderfolgenden Perioden.

    Warum das wichtiger ist als der globale CV:
    Ein globaler CV von 8 % kann entstehen durch gleichmässige Streuung ODER
    durch lokale Cluster (Maschinenschwingungen, Fadenspannungsdrifts).
    Der lokale CV deckt Letzteres auf: wenn er >> globalem CV ist, gibt es
    periodische Störungen die im Gesamtmittel verschwinden.

    Rückgabe: np.nan wenn weniger als `window` Perioden vorhanden.
    """
    a = np.asarray(periods_mm, dtype=float)
    a = a[np.isfinite(a)]
    if a.size < window:
        return np.nan
    local_cvs: List[float] = []
    for i in range(int(a.size) - window + 1):
        seg = a[i:i + window]
        m = float(seg.mean())
        if m <= 0.0:
            continue
        cv = 100.0 * float(seg.std(ddof=1)) / m
        if np.isfinite(cv):
            local_cvs.append(cv)
    if not local_cvs:
        return np.nan
    return float(np.median(local_cvs))


def _trim_percentiles(values: List[float], lo_pct: float = 5.0, hi_pct: float = 95.0) -> List[float]:
    """Entfernt Ausreisser durch Percentil-Trimming (Standard: 5%–95%)."""
    if len(values) == 0:
        return []
    a = np.asarray(values, float)
    lo = np.percentile(a, lo_pct)
    hi = np.percentile(a, hi_pct)
    return a[(a >= lo) & (a <= hi)].tolist()


def analyze_series(
    # Hauptfunktion: vollständige DTY-Knoten-Analyse eines Mess-Signals.
    # Gibt ein umfangreiches Result-Dict zurück (Knoten/m, Rapport-CV, Stabilitäts-Score usw.).
    # Für vollständige Signatur siehe Funktionskörper.
    y: np.ndarray,
    dx_mm: float,
    min_seg_pts: int,
    ab_pct: float = 33.0,
    bc_pct: float = 66.0,
    itemat_mode: bool = False,
    manual_T: Optional[float] = None,
    thr_method: str = 'yen',
) -> Dict[str, Any]:
    """Analysiert das Signal und liefert Kennzahlen/Segmente/Schwellwerte.
    Wenn manual_T gesetzt ist, ersetzt dieser Wert die automatische Otsu-Schwelle.
    Die Parameter itemat_mode und thr_method werden aus Kompatibilitätsgründen ignoriert.
    """

    # RAW-Pipeline (nur für optionale Auswertungen; Zählung basiert auf der robusten Pipeline)
    y_raw = y.astype(float, copy=True)

    # Robust-Pipeline: glätten und Schwellwert bestimmen
    y_det = _moving_average(y_raw, max(1, int(min_seg_pts)))
    x = np.asarray(y_det, dtype=float)

    # Schwellwert: manuell oder Otsu
    if manual_T is not None and np.isfinite(manual_T):
        T = float(manual_T)
    else:
        T = _otsu_threshold(x)

    # Für die RAW-Zählung verwenden wir dieselbe Schwelle (aus dem geglätteten Signal)
    x_count = y_raw
    T_raw = T
    knot_side_raw = x_count[x_count < T_raw]
    h_count_base = np.std(knot_side_raw) if knot_side_raw.size > 1 else (
        0.1 * np.std(x_count) + 1e-9)
    h_count = 0.25 * h_count_base
    labels_count = _label_with_hysteresis(x_count, T_raw, h_count)
    labels_count = _merge_short_runs(labels_count, 2)
    starts_count = _knot_starts_interpolated(x_count, labels_count, T_raw)

    # Robust-Pipeline (für Längen, Klassen, OL usw.)
    knot_side = x[x < T]
    h_base = np.std(knot_side) if knot_side.size > 1 else (
        0.1 * np.std(x) + 1e-9)
    h = 0.25 * h_base

    labels = _label_with_hysteresis(x, T, h)
    labels = _merge_short_runs(labels, min_seg_pts)
    runs = _runs_from_labels(labels)

    # Längen
    len_knot = [(end - start) * dx_mm for cls, start, end in runs if cls == 0]
    len_open = [(end - start) * dx_mm for cls, start, end in runs if cls == 1]
    rapport_mm = _pairwise_rapport_lengths_mm(runs, dx_mm)

    total_len_m = len(x) * dx_mm / 1000.0

    # Kennzahlen
    s_knot = _stats(len_knot)
    s_open = _stats(len_open)
    s_rapport = _stats(rapport_mm)

    # OL: Start->Start (robust)
    starts_det = _knot_starts_interpolated(x, labels, T)
    ol_periods_mm: List[float] = []
    if len(starts_det) >= 2:
        diffs = np.diff(starts_det)
        ol_periods_mm = (diffs * dx_mm).tolist()

    s_ol = _stats(ol_periods_mm)

    # --- Neue Metrik: CV basierend auf Zählungen pro 10 cm (0.10 m Segmente) ---
    # Wir verwenden für die Zählung dieselben Starts wie für knots_per_m (robuste Pipeline).
    starts_src = starts_det
    starts_pos_m = [(s * dx_mm) / 1000.0 for s in starts_src]
    counts_per_seg: List[float] = []
    if SEGMENT_CV_ENABLED and SEG_LEN_M > 0.0 and total_len_m >= SEG_LEN_M:
        n_full = int(total_len_m // SEG_LEN_M)
        if n_full > 0:
            import numpy as _np
            bins = _np.arange(0.0, n_full * SEG_LEN_M + SEG_LEN_M, SEG_LEN_M)
            counts, _ = _np.histogram(
                _np.asarray(starts_pos_m, float), bins=bins)
            counts_per_seg = counts.astype(float).tolist()
    s_ol_counts = _stats(counts_per_seg)

    # Knoten pro Meter
    knots_per_m_raw = (len(starts_count) /
                       total_len_m) if total_len_m > 0 else np.nan
    knots_per_m_det = (
        len(len_knot) / total_len_m) if total_len_m > 0 else np.nan
    knots_per_m = knots_per_m_det

    # A/B/C
    cls_info = _classify_knot_runs(x, runs, T, ab_pct=ab_pct, bc_pct=bc_pct)
    counts = cls_info.get('counts', {'A': 0, 'B': 0, 'C': 0})
    abc_per_m = {k: (v / total_len_m) if total_len_m > 0 else np.nan for k, v in counts.items()}

    # a–t (Knotenstärke)
    strength_info = _classify_knot_runs_20(x, runs, T)
    strength_counts = strength_info.get('counts', {c: 0 for c in "abcdefghijklmnopqrst"})
    strength_per_m = {k: (v / total_len_m) if total_len_m > 0 else np.nan for k, v in strength_counts.items()}

    # --- Neue Metriken: Skewness KL/OL + Rapport-CV ---
    skew_kl = _skewness(len_knot)
    skew_ol = _skewness(len_open)
    rapport_cv_global = s_ol.get('cv', np.nan)
    rapport_cv_local = _rapport_cv_local(ol_periods_mm, window=10)

    # --- Erweiterte Metriken (Prio 1–3) ---

    # Prio 1a: Autokorrelation KL (Lag 1–3)
    def _autocorr(arr: List[float], lag: int) -> float:
        a = np.asarray(arr, dtype=float)
        a = a[np.isfinite(a)]
        if a.size < lag + 2:
            return np.nan
        m = float(a.mean())
        var = float(np.var(a, ddof=0))
        if var <= 0:
            return np.nan
        return float(np.mean((a[:-lag] - m) * (a[lag:] - m)) / var)

    kl_ac1 = _autocorr(len_knot, 1)
    kl_ac2 = _autocorr(len_knot, 2)
    kl_ac3 = _autocorr(len_knot, 3)

    # Prio 1b: Tail-Ratio (95. Perzentil / Median)
    def _tail_ratio(arr: List[float]) -> float:
        a = np.asarray(arr, dtype=float)
        a = a[np.isfinite(a)]
        if a.size < 4:
            return np.nan
        med = float(np.median(a))
        if med <= 0:
            return np.nan
        return float(np.percentile(a, 95)) / med

    kl_tail_ratio = _tail_ratio(len_knot)
    ol_tail_ratio = _tail_ratio(len_open)

    # Prio 1c: KA/OA-Verhältnis (mittlere Knotenfläche / mittlere Öffnungsfläche)
    def _mean_area(lengths_mm: List[float], T_val: float,
                   x_sig: np.ndarray, runs_list, cls_val: int, dx: float) -> float:
        areas = []
        for cls_, s_, e_ in runs_list:
            if cls_ != cls_val:
                continue
            seg = x_sig[s_:e_].astype(float)
            if seg.size == 0:
                continue
            length_um = float(e_ - s_) * dx * 1000.0
            area = length_um * abs(T_val - float(np.mean(seg)))
            if np.isfinite(area) and area >= 0:
                areas.append(area)
        if not areas:
            return np.nan
        return float(np.mean(areas))

    ka_mean = _mean_area(len_knot, T, x, runs, 0, dx_mm)
    oa_mean = _mean_area(len_open, T, x, runs, 1, dx_mm)
    ka_oa_ratio = (ka_mean / oa_mean) if (
        np.isfinite(ka_mean) and np.isfinite(oa_mean) and oa_mean > 0) else np.nan

    # Prio 2a: Flanken-Asymmetrie (linke vs. rechte Hälfte jedes Knotens)
    asym_vals: List[float] = []
    for cls_, s_, e_ in runs:
        if cls_ != 0:
            continue
        seg = x[s_:e_].astype(float)
        n_seg = seg.size
        if n_seg < 4:
            continue
        mid = n_seg // 2
        left_slope = float(np.mean(np.diff(seg[:mid]))) if mid > 1 else np.nan
        right_slope = float(np.mean(np.diff(seg[mid:]))) if (n_seg - mid) > 1 else np.nan
        if np.isfinite(left_slope) and np.isfinite(right_slope):
            # Asymmetrie = |linke Flanke| - |rechte Flanke|, normiert auf Summe
            denom = abs(left_slope) + abs(right_slope)
            if denom > 0:
                asym_vals.append((abs(left_slope) - abs(right_slope)) / denom)
    kl_asym_mean = float(np.mean(asym_vals)) if asym_vals else np.nan
    kl_asym_cv = float(
        100.0 * np.std(asym_vals, ddof=1) / abs(np.mean(asym_vals))
    ) if len(asym_vals) > 1 and abs(np.mean(asym_vals)) > 1e-9 else np.nan

    # Prio 2b: Kurtosis KL / OL
    def _kurtosis(arr: List[float]) -> float:
        a = np.asarray(arr, dtype=float)
        a = a[np.isfinite(a)]
        if a.size < 4:
            return np.nan
        m = float(a.mean())
        s = float(a.std(ddof=1))
        if s <= 0:
            return np.nan
        return float(np.mean(((a - m) / s) ** 4)) - 3.0  # excess kurtosis

    kurt_kl = _kurtosis(len_knot)
    kurt_ol = _kurtosis(len_open)

    # Prio 2c: Thickness Drift (lineare Regression des gleitenden 50-Punkte-Mittelwerts)
    thickness_drift = np.nan
    try:
        win_drift = max(10, min(200, len(x) // 20))
        from scipy.ndimage import uniform_filter1d as _uf1d
        y_ma = _uf1d(x.astype(float), size=win_drift, mode='nearest')
        if y_ma.size >= 4:
            xi = np.arange(y_ma.size, dtype=float) * dx_mm / 1000.0  # in m
            slope = float(np.polyfit(xi, y_ma, 1)[0])  # µm/m
            thickness_drift = slope
    except Exception:
        pass

    # Prio 3a: Spektrale Energie der Knotenabstände (3 Bänder)
    spectral_low = spectral_mid = spectral_high = np.nan
    try:
        if len(ol_periods_mm) >= 16:
            from numpy.fft import rfft, rfftfreq
            sig_fft = np.asarray(ol_periods_mm, dtype=float)
            sig_fft = sig_fft - sig_fft.mean()
            freqs = rfftfreq(sig_fft.size, d=1.0)  # normierte Frequenz 0..0.5
            power = np.abs(rfft(sig_fft)) ** 2
            total_p = float(power.sum())
            if total_p > 0:
                spectral_low  = float(power[freqs <= 0.1].sum())  / total_p * 100.0
                spectral_mid  = float(power[(freqs > 0.1) & (freqs <= 0.3)].sum()) / total_p * 100.0
                spectral_high = float(power[freqs > 0.3].sum())   / total_p * 100.0
    except Exception:
        pass

    # Prio 3b: C-Knoten Cluster (Lauflängen aufeinanderfolgender C-Knoten = schwächste Knoten)
    aknot_cluster_mean = aknot_cluster_max = np.nan
    try:
        per_run_abc = cls_info.get('per_run', [])
        cluster_lens: List[int] = []
        run_len = 0
        for entry in per_run_abc:
            if not isinstance(entry, (list, tuple)) or len(entry) < 4:
                continue
            klasse = entry[3]
            if klasse == 'C':
                run_len += 1
            else:
                if run_len > 0:
                    cluster_lens.append(run_len)
                run_len = 0
        if run_len > 0:
            cluster_lens.append(run_len)
        if cluster_lens:
            aknot_cluster_mean = float(np.mean(cluster_lens))
            aknot_cluster_max  = float(np.max(cluster_lens))
    except Exception:
        pass

    return dict(
        threshold=T,
        h_low=T - h,
        h_high=T + h,
        knots_per_m=knots_per_m,
        knots_per_m_det=knots_per_m_det,
        knots_per_m_raw=knots_per_m_raw,
        knot=s_knot,
        open=s_open,
        knot_lengths_mm=len_knot,
        open_lengths_mm=len_open,
        rapport=s_rapport,
        classes=cls_info,
        abc_per_m=abc_per_m,
        knot_strength=strength_info,
        knot_strength_per_m=strength_per_m,
        ol_period_mm_stats=s_ol,
        ol_counts_stats=s_ol_counts,
        skew_kl=skew_kl,
        skew_ol=skew_ol,
        rapport_cv_global=rapport_cv_global,
        rapport_cv_local=rapport_cv_local,
        # Erweiterte Metriken
        kl_ac1=kl_ac1, kl_ac2=kl_ac2, kl_ac3=kl_ac3,
        kl_tail_ratio=kl_tail_ratio, ol_tail_ratio=ol_tail_ratio,
        ka_oa_ratio=ka_oa_ratio,
        kl_asym_mean=kl_asym_mean, kl_asym_cv=kl_asym_cv,
        kurt_kl=kurt_kl, kurt_ol=kurt_ol,
        thickness_drift=thickness_drift,
        spectral_low=spectral_low, spectral_mid=spectral_mid, spectral_high=spectral_high,
        aknot_cluster_mean=aknot_cluster_mean, aknot_cluster_max=aknot_cluster_max,
    )


# ===========================================================================
# Flächen-Bins (ka/oa, je 20) – standalone Version von _compute_area_bins
# ===========================================================================

def compute_area_bins(
    # Berechnet Flächen-Bins für alle erkannten Knoten (Integral unter der Kurve).
    # Wird für ML-Feature-Engineering verwendet.
    res: dict,
    y: "np.ndarray",
    step_mm: float,
    min_seg_pts: int = 3,
    y_smooth_ext: "np.ndarray | None" = None,
) -> tuple:
    """
    Berechnet Knoten- und Öffnungs-Flächen-Histogramm (je 20 Bins, in %).
    Gibt (ka_bins, oa_bins) zurück – je 20 Werte oder None.

    y_smooth_ext: optional vorberechnetes geglättetes Signal (aus analyze_series),
                  vermeidet doppelte Berechnung des gleitenden Durchschnitts.
    """
    if not isinstance(res, dict) or y is None or step_mm <= 0:
        return [None] * 20, [None] * 20

    import math
    T = res.get("threshold")
    if T is None or not math.isfinite(float(T)):
        return [None] * 20, [None] * 20
    T = float(T)

    k = max(1, int(min_seg_pts))
    if y_smooth_ext is not None and len(y_smooth_ext) == len(y):
        y_smooth = np.asarray(y_smooth_ext, dtype=float)
    else:
        y_smooth = _moving_average(np.asarray(y, dtype=float), k)
    n = len(y_smooth)

    per_run = (res.get("classes") or {}).get("per_run", [])
    mask_knot = np.zeros(n, dtype=bool)
    knot_runs = []
    for run in per_run:
        if not isinstance(run, (list, tuple)) or len(run) < 2:
            continue
        s, e = max(0, int(run[0])), min(n, int(run[1]))
        if e > s:
            mask_knot[s:e] = True
            knot_runs.append((s, e))

    knot_areas = []
    for s, e in knot_runs:
        seg = y_smooth[s:e]
        if seg.size == 0:
            continue
        mean_val = float(np.mean(seg))
        length_um = float(e - s) * step_mm * 1000.0
        area = length_um * abs(T - mean_val)
        if math.isfinite(area) and area >= 0:
            knot_areas.append(area)

    open_areas = []
    open_idx = np.where(~mask_knot)[0]
    if open_idx.size:
        splits = np.where(np.diff(open_idx) > 1)[0] + 1
        for grp in np.split(open_idx, splits):
            if grp.size == 0:
                continue
            seg = y_smooth[grp]
            mean_val = float(np.mean(seg))
            length_um = float(grp.size) * step_mm * 1000.0
            area = length_um * abs(T - mean_val)
            if math.isfinite(area) and area >= 0:
                open_areas.append(area)

    def _to_bins20(areas):
        if not areas:
            return [None] * 20
        arr = np.asarray(areas, dtype=float)
        arr = arr[np.isfinite(arr) & (arr >= 0)]
        if arr.size == 0:
            return [None] * 20
        vmin, vmax = float(arr.min()), float(arr.max())
        if vmax <= vmin:
            r = [0.0] * 20; r[0] = 100.0; return r
        bounds = np.linspace(vmin, vmax, 21)
        n_total = float(arr.size)
        result = []
        for i in range(20):
            if i < 19:
                count = float(np.sum((arr >= bounds[i]) & (arr < bounds[i+1])))
            else:
                count = float(np.sum((arr >= bounds[i]) & (arr <= bounds[i+1])))
            result.append(100.0 * count / n_total if n_total > 0 else None)
        return result

    return _to_bins20(knot_areas), _to_bins20(open_areas)


# ===========================================================================
# Fallhöhen + Winkelsegmente – standalone Extraktion aus per_run
# ===========================================================================

def compute_kgeo_segments(
    # Berechnet geometrische Knoten-Kennzahlen (Tiefe, Breite, Flanken) segmentweise.
    # Wird für ML-Feature-Engineering verwendet.
    res: dict,
    y: "np.ndarray",
    step_mm: float,
    min_seg_pts: int = 3,
    y_smooth_ext: "np.ndarray | None" = None,
) -> tuple:
    """
    Berechnet Fallhöhen- und Winkelsegment-Anteile (je 10 Bins, in %).
    Gibt (fall_pct, wink_pct) zurück – je 10 Werte oder None.

    y_smooth_ext: optional vorberechnetes geglättetes Signal (aus analyze_series),
                  vermeidet doppelte Berechnung des gleitenden Durchschnitts.
    """
    import math

    if not isinstance(res, dict) or y is None or step_mm <= 0:
        return [None] * 10, [None] * 10

    k = max(1, int(min_seg_pts))
    if y_smooth_ext is not None and len(y_smooth_ext) == len(y):
        y_smooth = np.asarray(y_smooth_ext, dtype=float)
    else:
        y_smooth = _moving_average(np.asarray(y, dtype=float), k)
    n = len(y_smooth)
    pts_per_m = 1000.0 / step_mm

    per_run = (res.get("classes") or {}).get("per_run", [])
    mask_knot = np.zeros(n, dtype=bool)
    knot_segs = []
    for run in per_run:
        if not isinstance(run, (list, tuple)) or len(run) < 2:
            continue
        s, e = max(0, int(run[0])), min(n, int(run[1]))
        if e > s:
            mask_knot[s:e] = True
            g = np.arange(s, e)
            mv = float(np.mean(y_smooth[g]))
            knot_segs.append((g, mv))

    open_segs = []
    open_idx = np.where(~mask_knot)[0]
    if open_idx.size:
        splits = np.where(np.diff(open_idx) > 1)[0] + 1
        for grp in np.split(open_idx, splits):
            if grp.size == 0:
                continue
            mv = float(np.mean(y_smooth[grp]))
            open_segs.append((grp, mv))

    # Segmente zusammenführen und sortieren
    seg_all = []
    for g, mv in open_segs:
        if g.size:
            seg_all.append(("open", int(g[0]), int(np.round(np.mean(g))), mv, g))
    for g, mv in knot_segs:
        if g.size:
            seg_all.append(("knot", int(g[0]), int(np.round(np.mean(g))), mv, g))
    seg_all.sort(key=lambda t: t[1])

    distances = []
    angles = []
    for (typ1, _s1, c1, m1, g1), (typ2, _s2, c2, m2, g2) in zip(seg_all, seg_all[1:]):
        if typ1 == typ2:
            continue
        d = abs(m1 - m2)
        if math.isfinite(d):
            distances.append(d)
        if typ1 == "open" and typ2 == "knot" and pts_per_m > 0:
            try:
                ys_open = y_smooth[g1]
                ys_knot = y_smooth[g2]
                idx_open = int(g1[int(np.nanargmax(ys_open))])
                idx_knot = int(g2[int(np.nanargmin(ys_knot))])
                y_open = float(ys_open[int(np.nanargmax(ys_open))])
                y_knot = float(ys_knot[int(np.nanargmin(ys_knot))])
                dx_pts = float(idx_knot - idx_open)
                if dx_pts != 0.0:
                    dx_um = (dx_pts / pts_per_m) * 1e6
                    dy = float(y_knot - y_open)
                    ang_deg = abs(float(np.arctan2(dy, dx_um)) * 180.0 / np.pi)
                    if math.isfinite(ang_deg):
                        angles.append(ang_deg)
            except Exception:
                pass

    def _to_bins10_pct(values):
        if not values:
            return [None] * 10
        arr = np.asarray(values, dtype=float)
        arr = arr[np.isfinite(arr)]
        if arr.size == 0:
            return [None] * 10
        dmin, dmax = float(arr.min()), float(arr.max())
        if dmax <= dmin:
            r = [0.0] * 10; r[0] = 100.0; return r
        bounds = np.linspace(dmin, dmax, 11)
        n_total = float(arr.size)
        result = []
        for i in range(10):
            if i < 9:
                count = float(np.sum((arr >= bounds[i]) & (arr < bounds[i+1])))
            else:
                count = float(np.sum((arr >= bounds[i]) & (arr <= bounds[i+1])))
            result.append(100.0 * count / n_total if n_total > 0 else None)
        return result

    return _to_bins10_pct(distances), _to_bins10_pct(angles)


# ===========================================================================
# ML Stabilitäts-Predictions
# ===========================================================================

_STAB_MODEL_FILES = [
    "stab_03.joblib", "stab_06.joblib",
    "stab_10.joblib", "stab_13.joblib",
]
_STAB_FEATURE_ORDER = [
    "FPm","CV_FP","AvgFP","StdDevFP","CV_KL","AvgKL","StdDevKL","CV_OL","AvgOL","StdDevOL",
    "AKnots","BKnots","CKnots",
    "a_knots","b_knots","c_knots","d_knots","e_knots","f_knots","g_knots","h_knots","i_knots","j_knots",
    "k_knots","l_knots","m_knots","n_knots","o_knots","p_knots","q_knots","r_knots","s_knots","t_knots",
    "Fallhöhe1","Fallhöhe2","Fallhöhe3","Fallhöhe4","Fallhöhe5",
    "Fallhöhe6","Fallhöhe7","Fallhöhe8","Fallhöhe9","Fallhöhe10",
    "Winkelsegment1","Winkelsegment2","Winkelsegment3","Winkelsegment4","Winkelsegment5",
    "Winkelsegment6","Winkelsegment7","Winkelsegment8","Winkelsegment9","Winkelsegment10",
]

_MODEL_CACHE: dict = {}
import threading as _threading
_MODEL_CACHE_LOCK = _threading.RLock()


def _local_models_dir() -> "Path":
    """Gibt das Verzeichnis für lokale ML-Modelle zurück (neben der ausführbaren Datei)."""
    """Lokaler Mirror-Ordner: %LOCALAPPDATA%/TrippleT/models"""
    import os
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or ""
    p = Path(base) / "TrippleT" / "models"
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


_MODELS_DIR_CACHE: "Path | None" = None  # wird von sync_models_async gesetzt

def _models_dir() -> "Path":
    """Gibt das lokale Modell-Verzeichnis zurück – KEIN Netzwerkzugriff.

    Gibt immer den lokalen Mirror-Pfad zurück (auch wenn leer).
    sync_models_async() befüllt ihn im Hintergrund beim App-Start.
    Kein central.exists() hier – das würde bei langsamen Netzwerken
    mehrere Minuten blockieren.
    """
    if _MODELS_DIR_CACHE is not None:
        return _MODELS_DIR_CACHE
    # Fallback: lokaler Pfad ohne jede Netzwerkprüfung
    return _local_models_dir()


def _get_model_sync_logger():
    """Logger fuer den Modell-Sync, schreibt nach %TEMP%\\tripplet_model_sync.log
    (gleiches Muster wie beim Statimat-Import) - sonst ist der Sync
    komplett lautlos und man kann nie nachvollziehen, ob/warum er
    fehlgeschlagen ist."""
    import logging
    import tempfile
    import os
    log_path = os.path.join(tempfile.gettempdir(), "tripplet_model_sync.log")
    logger = logging.getLogger("tripplet.model_sync")
    if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "").endswith(
            "tripplet_model_sync.log") for h in logger.handlers):
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(fh)
        logger.setLevel(logging.INFO)
    return logger


def sync_models_async(force: bool = False, blocking: bool = False) -> None:
    """Startet den Modell-Sync (H: → lokal) einmalig im Background-Thread.

    Aufruf beim App-Start (main.py). Blockiert die UI nicht (ausser
    blocking=True, z.B. fuer einen manuellen "Jetzt synchronisieren"-Button).
    central.exists() läuft mit Timeout, damit ein nicht erreichbares
    Netzlaufwerk nicht ewig haengt (15s statt vorher 5s - ein "kaltes"
    Netzlaufwerk beim allerersten Zugriff nach Windows-Start kann laenger
    brauchen als 5s, der Sync ist dann faelschlich leise fehlgeschlagen).

    Ergebnis (erreichbar/Fehler/kopierte Dateien) wird nach
    %TEMP%\\tripplet_model_sync.log geloggt.
    """
    import threading as _threading

    def _sync():
        global _MODELS_DIR_CACHE
        import shutil as _shutil
        log = _get_model_sync_logger()

        # Lokalen Pfad sofort als Cache setzen – Workers können schon starten
        local = _local_models_dir()
        _MODELS_DIR_CACHE = local
        log.info("Sync gestartet. Lokaler Mirror: %s", local)

        # Dann Netzwerk-Sync versuchen (darf scheitern)
        central = Path(r"H:\Technik\YarnScope\models")
        try:
            # central.exists() kann auf langsamen/kalten Netzwerken laenger
            # blockieren – darum in eigenem Thread mit Timeout
            central_ok = [False]
            def _check():
                central_ok[0] = central.exists()
            ct = _threading.Thread(target=_check, daemon=True)
            ct.start()
            ct.join(timeout=15.0)   # max 15 Sekunden für Netzwerk-Ping

            if not central_ok[0]:
                log.warning(
                    "Zentraler Pfad %s nicht erreichbar (Timeout oder existiert nicht) "
                    "- lokaler Mirror bleibt unveraendert.", central)
                return

            log.info("Zentraler Pfad erreichbar: %s", central)
            copied = []
            failed = []
            for fn in _STAB_MODEL_FILES:
                src_f = central / fn
                if not src_f.exists():
                    log.warning("Quelldatei fehlt: %s", src_f)
                    continue
                dst_f = local / fn
                # Bewusst IMMER kopieren, keine Mtime-basierte "ist eh schon
                # aktuell"-Pruefung mehr: Netzlaufwerke (SMB/CIFS) koennen
                # Datei-Metadaten clientseitig zwischenspeichern, wodurch die
                # Mtime veraltet erscheint, obwohl der Inhalt laengst neu ist
                # (siehe Chat - genau das ist hier passiert). Bei 4 kleinen
                # Dateien einmal pro App-Start ist der Mehraufwand irrelevant.
                try:
                    _shutil.copy2(str(src_f), str(dst_f))
                    copied.append(fn)
                except Exception as ce:
                    failed.append(f"{fn} ({ce})")
            log.info("Sync fertig. Kopiert: %s%s", copied or "-",
                     f" | Fehlgeschlagen: {failed}" if failed else "")
        except Exception as e:
            log.error("Sync fehlgeschlagen: %s", e, exc_info=True)

    t = _threading.Thread(target=_sync, daemon=True, name="ModelSync")
    t.start()
    if blocking:
        t.join(timeout=20.0)


def _fetch_trial_process_and_jet_features(trial_id: int) -> dict:
    """Laedt Duesengeometrie (tbljets) + Prozessparameter (AirPressure,
    Overfeed) fuer einen Trial.

    Hintergrund: das Stab-Prediction-Modell wurde u.a. mit Duesengeometrie
    und Prozessparametern trainiert (siehe ModelCreator-SQL-Query), aber
    full_extract_vals() liefert bisher NUR die aus dem YarnScope-Signal
    berechneten Statistiken (FPm, Knoten-Verteilung etc.). Ohne diese
    Ergaenzung fehlen Duesengeometrie/AirPressure/Overfeed bei JEDER
    Vorhersage lautlos (werden vom Modell-Pipeline-Imputer stillschweigend
    mit dem Trainings-Median aufgefuellt statt mit den echten Werten).

    WICHTIG: Luftkanalform/Wirbelkammer/KonusForm werden hier auf ihre
    Klartext-Namen (z.B. 'V'/'U'/'PolyJet') gejoint, NICHT die rohen FK-IDs
    zurueckgegeben - muss exakt zur Trainings-Query im ModelCreator passen
    (dort wird jetzt ebenfalls der Name statt der FK-ID exportiert), sonst
    bekommt das Modell bei der Vorhersage eine Zahl, wo es eine Kategorie
    wie 'V' erwartet.
    """
    if not trial_id:
        return {}
    try:
        from db.connection import fetch_all
        rows = fetch_all(
            "SELECT t.AirPressure, t.Shaft2x_OF AS Overfeed, "
            "j.Luftbohrung, j.AnzahlLuftbohrungen, j.WinkelLuftbohrung, acs.AirChannelShape AS Luftkanalform, "
            "j.GarnkanalBreite, j.GarnkanalTiefe, j.GarnkanalRadius, "
            "j.GarnkanalLängeEingang, j.GarnkanalLängeAusgang, "
            "wk.Wirbelkammer AS Wirbelkammer, j.WirbelkammerBreite, j.WirbelkammerRadius, j.WirbelkammerKreissehne, "
            "j.GebogenerKanal, "
            "j.WinkelKonusI, j.WinkelKonusII, j.RadiusKonus, j.AbstandLBKonus, "
            "j.AbstandEinlaufKonusZuLB, j.Konuslänge, j.LängeDK, kf.KonusForm AS KonusForm, "
            "j.AbstandSchlitzEingang, j.AbstandSchlitzAusgang, "
            "j.SchlitzbreiteEingang, j.SchlitzbreiteAusgang, j.Luftverbrauch "
            "FROM tbltrial t "
            "LEFT JOIN tbljets j ON j.ID = t.JetID "
            "LEFT JOIN tblAirChannelShape acs ON acs.ID = j.Luftkanalform "
            "LEFT JOIN tblWirbelkammer wk ON wk.ID = j.Wirbelkammer "
            "LEFT JOIN tblKonusform kf ON kf.ID = j.KonusForm "
            "WHERE t.ID = ?", [trial_id])
        if not rows:
            return {}
        return dict(rows[0])
    except Exception:
        return {}


def run_stab_models(vals: dict, progress_cb=None) -> dict:
    """Lädt XGBoost-Stabilitätsmodelle und berechnet Vorhersagen für alle Spannungsstufen.

    Modelle: je ein Modell pro Spannungsstufe (0.3, 0.6, 1.0, 1.3 cN/dtex).
    Gibt leeres Dict zurück wenn xgboost nicht installiert oder Modelle fehlen.

    Args:
        vals: Feature-Dict aus ``full_extract_vals()``.
        progress_cb: optionales Callable(str), wird aufgerufen, wenn ein
            Modell tatsächlich von der Platte geladen werden muss (Cache-Miss)
            - die erste Vorhersage nach App-Start/Modell-Update kann dadurch
            spürbar laenger dauern als Folge-Vorhersagen (die aus dem Cache
            kommen). Damit kann der Aufrufer waehrenddessen eine Statusmeldung
            anzeigen, statt dass es aussieht, als waere nichts los.

    Returns:
        Dict {'stab_03': float, 'stab_06': float, 'stab_10': float, 'stab_13': float}.
    """
    """
    Führt alle stab_*.joblib Modelle aus und gibt Predictions zurück.
    vals: extrahiertes Feature-Dict (Ausgabe von ys_extract_vals).
    Gibt {filename: {"pred": "12.345", "meta": "ModelName v1"}} zurück.
    """
    try:
        import joblib
        import pandas as pd
    except ImportError:
        return {}

    model_dir = _models_dir()
    out = {}

    for fn in _STAB_MODEL_FILES:
        p = model_dir / fn
        if not p.exists():
            continue
        try:
            mtime = p.stat().st_mtime
            with _MODEL_CACHE_LOCK:
                hit = _MODEL_CACHE.get(str(p))
                if hit and abs(hit[0] - mtime) < 1e-6:
                    model, meta, meta_str = hit[1], hit[2], hit[3]
                else:
                    if progress_cb:
                        try:
                            progress_cb(f"Lade Modell {fn}…")
                        except Exception:
                            pass
                    pkg = joblib.load(str(p))
                    if isinstance(pkg, dict) and "model" in pkg:
                        model = pkg["model"]
                        md = pkg.get("metadata") or {}
                        meta = md if isinstance(md, dict) else {}
                        mn = meta.get("model_name"); mv = meta.get("model_version")
                        meta_str = (f"{mn} v{mv}" if mn and mv else
                                    str(mv or mn or fn))
                    else:
                        model = pkg; meta = {}; meta_str = fn
                    _MODEL_CACHE[str(p)] = (mtime, model, meta, meta_str)

            # Feature-Reihenfolge aus Modell-Metadata oder Default
            features = meta.get("features") if meta else None
            if not (isinstance(features, (list, tuple)) and
                    all(isinstance(x, str) for x in features)):
                features = list(_STAB_FEATURE_ORDER)

            row = {c: vals.get(c) for c in features}
            X = pd.DataFrame([row], columns=features)
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                yhat = model.predict(X)[0]
            out[fn] = {
                "pred": f"{float(yhat):.3f}" if yhat is not None else None,
                "meta": meta_str,
            }
        except Exception as e:
            # Nicht mehr lautlos ueberspringen - sonst sieht man nur "leere
            # Vorhersage" ohne jeden Hinweis, warum (z.B. Versions-
            # Inkompatibilitaet des neu trainierten Modells mit der hier
            # installierten sklearn/xgboost-Version, fehlendes Feature etc.)
            try:
                _get_model_sync_logger().error(
                    "Vorhersage fehlgeschlagen fuer %s: %s", fn, e, exc_info=True)
            except Exception:
                pass
            continue

    return out


def full_extract_vals(res: dict, y_raw=None, step_mm: float = 0.25,
    # Extrahiert alle ML-Features aus einem analyze_series()-Ergebnis.
    # Gibt ein flaches Dict mit allen Feature-Werten zurück.
                       min_seg_pts: int = 3, trial_id: "int | None" = None,
                       progress_cb=None) -> dict:
    """
    Vollständige Extraktion aller DB-Felder aus analyze_series-Ergebnis.
    Zusätzlich zu den Basis-Werten: Flächen-Bins, Fallhöhen, Winkelsegmente, Stab-Predictions.

    trial_id (optional): falls bekannt, werden zusaetzlich Duesengeometrie
    und Prozessparameter (AirPressure, Overfeed) aus der DB nachgeladen und
    vor der Stab-Vorhersage ergaenzt - sonst fehlen diese dem Modell immer
    lautlos, falls es damit trainiert wurde (siehe
    _fetch_trial_process_and_jet_features).

    progress_cb (optional): Callable(str), wird an run_stab_models
    durchgereicht - zeigt an, wenn gerade ein Modell von der Platte geladen
    wird (nur beim ersten Mal bzw. nach einem Modell-Update spuerbar).
    """
    import math

    # Basis-Werte (bereits implementiert in _ys_extract_vals – hier nochmals inline)
    def _safe(v):
        if v is None: return None
        try:
            f = float(v)
            return f if math.isfinite(f) else None
        except Exception:
            return None

    out = {}
    out["FPm"]      = _safe(res.get("knots_per_m"))
    ol_p = res.get("ol_period_mm_stats") or {}
    mm = _safe(ol_p.get("mean")); sd = _safe(ol_p.get("sd"))
    out["AvgFP"]    = mm / 10.0 if mm is not None else None
    out["StdDevFP"] = sd / 10.0 if sd is not None else None
    out["CV_FP"]    = _safe(ol_p.get("cv"))
    knot = res.get("knot") or {}
    out["CV_KL"]    = _safe(knot.get("cv"))
    out["AvgKL"]    = _safe(knot.get("mean"))
    out["StdDevKL"] = _safe(knot.get("sd"))
    out["maxKL"]    = _safe(knot.get("max"))
    open_ = res.get("open") or {}
    out["CV_OL"]    = _safe(open_.get("cv"))
    out["AvgOL"]    = _safe(open_.get("mean"))
    out["StdDevOL"] = _safe(open_.get("sd"))
    out["maxOL"]    = _safe(open_.get("max"))

    abc_per_m = res.get("abc_per_m") or {}
    total_abc = sum(float(v) for v in abc_per_m.values()
                    if v is not None and math.isfinite(float(v)))
    if total_abc > 0:
        out["AKnots"] = _safe(100.0 * abc_per_m.get("A", 0.0) / total_abc)
        out["BKnots"] = _safe(100.0 * abc_per_m.get("B", 0.0) / total_abc)
        out["CKnots"] = _safe(100.0 * abc_per_m.get("C", 0.0) / total_abc)
    else:
        out["AKnots"] = out["BKnots"] = out["CKnots"] = None

    spm = res.get("knot_strength_per_m") or {}
    # nan-sicher: nur finite Werte summieren; NaN-Einträge als 0 behandeln
    valid_spm = {k: float(v) for k, v in spm.items()
                 if v is not None and math.isfinite(float(v))}
    total_str = sum(valid_spm.values())
    for c in "abcdefghijklmnopqrst":
        v = valid_spm.get(c, 0.0)
        out[f"{c}_knots"] = _safe(100.0 * v / total_str) if total_str > 0 else None

    # KL/OL Bins (10)
    def _bins10(lengths):
        if not lengths: return [None]*10
        arr = np.array(lengths, dtype=float)
        lo, hi = np.percentile(arr, 2), np.percentile(arr, 98)
        if hi <= lo: return [None]*10
        counts, _ = np.histogram(arr, bins=np.linspace(lo, hi, 11))
        total = counts.sum()
        return [float(c/total*100) if total > 0 else None for c in counts]

    kl_b = _bins10(res.get("knot_lengths_mm") or [])
    ol_b = _bins10(res.get("open_lengths_mm") or [])
    for i in range(10):
        out[f"kl_bin_{i+1}"] = kl_b[i]
        out[f"ol_bin_{i+1}"] = ol_b[i]

    out["SkewKL"]         = _safe(res.get("skew_kl"))
    out["SkewOL"]         = _safe(res.get("skew_ol"))
    out["RapportCV"]      = _safe(res.get("rapport_cv_global"))
    out["RapportCVLocal"] = _safe(res.get("rapport_cv_local"))
    out["KL_AC1"]         = _safe(res.get("kl_ac1"))
    out["KL_AC2"]         = _safe(res.get("kl_ac2"))
    out["KL_AC3"]         = _safe(res.get("kl_ac3"))
    out["KL_TailRatio"]   = _safe(res.get("kl_tail_ratio"))
    out["OL_TailRatio"]   = _safe(res.get("ol_tail_ratio"))
    out["KA_OA_Ratio"]    = _safe(res.get("ka_oa_ratio"))
    out["KL_AsymMean"]    = _safe(res.get("kl_asym_mean"))
    out["KL_AsymCV"]      = _safe(res.get("kl_asym_cv"))
    out["KurtKL"]         = _safe(res.get("kurt_kl"))
    out["KurtOL"]         = _safe(res.get("kurt_ol"))
    out["ThicknessDrift"] = _safe(res.get("thickness_drift"))
    out["SpectralEnergyLow"]  = _safe(res.get("spectral_low"))
    out["SpectralEnergyMid"]  = _safe(res.get("spectral_mid"))
    out["SpectralEnergyHigh"] = _safe(res.get("spectral_high"))
    out["CKnot_ClusterMean"]  = _safe(res.get("aknot_cluster_mean"))
    out["CKnot_ClusterMax"]   = _safe(res.get("aknot_cluster_max"))

    # Flächen-Bins (ka/oa, je 20) + Geo-Segmente – braucht y_raw
    if y_raw is not None:
        y_arr = y_raw if (isinstance(y_raw, np.ndarray) and y_raw.dtype == np.float64) \
                else np.asarray(y_raw, dtype=float)
        k = max(1, int(min_seg_pts))
        y_smooth_shared = _moving_average(y_arr, k)
        ka_bins, oa_bins   = compute_area_bins(res, y_arr, step_mm, min_seg_pts,
                                                y_smooth_ext=y_smooth_shared)
        fall_pct, wink_pct = compute_kgeo_segments(res, y_arr, step_mm, min_seg_pts,
                                                    y_smooth_ext=y_smooth_shared)
    else:
        ka_bins = oa_bins = [None] * 20
        fall_pct = wink_pct = [None] * 10

    for i in range(20):
        out[f"ka_bin_{i+1}"] = _safe(ka_bins[i]) if ka_bins[i] is not None else None
        out[f"oa_bin_{i+1}"] = _safe(oa_bins[i]) if oa_bins[i] is not None else None
    for i in range(10):
        out[f"Fallhöhe{i+1}"]      = _safe(fall_pct[i])
        out[f"Winkelsegment{i+1}"] = _safe(wink_pct[i])

    # Duesengeometrie + Prozessparameter ergaenzen (siehe Docstring) - erst
    # NACH den YarnScope-Signalwerten, damit ein evtl. vorhandener trial_id
    # nichts ueberschreibt, aber VOR run_stab_models, damit die Werte bei
    # der Vorhersage tatsaechlich zur Verfuegung stehen.
    tid = trial_id if trial_id is not None else (res.get("TrialID") or res.get("_trial_id"))
    if tid is not None:
        try:
            extra = _fetch_trial_process_and_jet_features(int(tid))
            for k, v in extra.items():
                out.setdefault(k, v)
        except Exception:
            pass

    # Stab-Predictions (ML)
    preds = run_stab_models(out, progress_cb=progress_cb)
    model_map = {
        "stab_03.joblib": ("Stab_03", "Stab_03_model"),
        "stab_06.joblib": ("Stab_06", "Stab_06_model"),
        "stab_10.joblib": ("Stab_10", "Stab_10_model"),
        "stab_13.joblib": ("Stab_13", "Stab_13_model"),
    }
    for fn, (val_key, meta_key) in model_map.items():
        info = preds.get(fn)
        if isinstance(info, dict):
            try:
                out[val_key] = float(info["pred"]) if info.get("pred") else None
            except Exception:
                out[val_key] = None
            out[meta_key] = info.get("meta")
        else:
            out[val_key] = None
            out[meta_key] = None

    return out