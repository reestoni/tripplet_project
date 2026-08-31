"""
thick_spot_analysis.py – Dickstellen-Analyse fuer ATY-Garn (globaler Mittelwert
als Kern). Reine Berechnungsfunktionen, keine DB-/Qt-Abhaengigkeiten.

Datei gehört nach ui/yarnscope/thick_spot_analysis.py

Bin-Logik: height_um / length_mm > BIN_THRESHOLD → Bin1 (Kurzhocker), sonst Bin2 (Langwelle)
Features:  F01 Laenge [mm], F02 Hoehe [um], F03 Flaeche [um*mm]
Histogramm: je Feature × je Bin → 20 Intervalle (Anzahl/100m)

Genutzt vom bestehenden Single-Trial-ATY-Flow (ui/aty_yarnscope_tab.py) fuer
die Verteilung/Garnspiegel/Fabric/Knitted-Visuals -- NICHT mehr fuer den
DB-Save (tblLaborATYoMat schreibt seit 2026-08-13 ausschliesslich ueber
ui/yarnscope/aty_core_analysis.py, die neue Kern-Baseline-Methode, siehe
CLAUDE.md). Die frueheren save_to_db()/setup_thick_spot_tab()/
_on_save_clicked()-Funktionen hier waren ohnehin nur ueber das nirgends
importierte ui/yarnscope/garngraf.py erreichbar (totes Restcode aus dem
urspruenglichen eigenstaendigen YarnScope-Tool) und wurden am selben Tag
entfernt, da sie nach der Spaltenumstellung auf ein nicht mehr existierendes
DB-Schema verwiesen haetten.
"""

from __future__ import annotations
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

BIN_THRESHOLD = 100.0   # um/mm
N_HIST_BINS   = 20

BIN1_COLOR = "#e07b00"
BIN2_COLOR = "#0e8a8a"
BIN1_FILL  = "#ffcc88"
BIN2_FILL  = "#88dddd"

# Nur die 3 relevanten Features
FEATURE_KEYS = ["F01_length_mm", "F02_height_um", "F03_area_um_mm"]
FEATURE_LABELS = {
    "F01_length_mm":  "Laenge [mm]",
    "F02_height_um":  "Hoehe [um]",
    "F03_area_um_mm": "Flaeche [um*mm]",
}

# DB-Spaltenpräfixe je Feature
FEATURE_DB_PREFIX = {
    "F01_length_mm":  "len",
    "F02_height_um":  "hgt",
    "F03_area_um_mm": "area",
}


# ---------------------------------------------------------------------------
# Detektion (nur F01/F02/F03 – schnell)
# ---------------------------------------------------------------------------

def detect_thick_spots(arr_mm: np.ndarray, mm_per_point: float,
                       min_length_mm: float = 1.0) -> List[Dict[str, Any]]:
    """Findet alle Dickstellen über dem Mittelwert – vollständig vektorisiert.

    Ersetzt die frühere Python-while-Schleife durch np.diff/np.where,
    was bei 2 Mio. Punkten ~100× schneller ist.

    Args:
        arr_mm:        Garndicke-Array in mm.
        mm_per_point:  Messabstand in mm pro Datenpunkt.
        min_length_mm: Minimale Dickstellenlänge (Standard: 0.25 mm = 1 Punkt).

    Returns:
        Liste von Feature-Dicts, je eine Dickstelle.
    """
    arr = np.asarray(arr_mm, dtype=float)
    n   = arr.size
    if n < 2:
        return []
    mean_mm = float(np.mean(arr))
    if not np.isfinite(mean_mm) or mean_mm <= 0:
        return []

    min_pts = max(1, int(np.ceil(min_length_mm / mm_per_point)))

    # Vektorisierte Segmentgrenzen-Erkennung via np.diff
    # above[i] = True wenn arr[i] > mean_mm
    above = (arr > mean_mm).view(np.uint8)

    # Flanken: +1 = Beginn einer Dickstelle, -1 = Ende
    diff = np.diff(above, prepend=0, append=0)
    starts = np.where(diff ==  1)[0]   # Indizes wo Dickstelle beginnt
    ends   = np.where(diff == -1)[0]   # Indizes wo Dickstelle endet (exklusiv)

    spots: List[Dict[str, Any]] = []
    for s, e in zip(starts, ends):
        if (e - s) < min_pts:
            continue
        spots.append(_compute_features(arr[s:e], int(s), mm_per_point, mean_mm))

    return spots


def _compute_features(seg: np.ndarray, start_idx: int,
                      mm_per_point: float, mean_mm: float) -> Dict[str, Any]:
    """Berechnet die drei Features (F01/F02/F03) und Bin-Zuweisung für eine Dickstelle.

    Args:
        seg:          Garndicke-Segment der Dickstelle in mm.
        start_idx:    Startindex im Gesamt-Array.
        mm_per_point: Messabstand in mm.
        mean_mm:      Globaler Mittelwert des Garnprofils in mm.

    Returns:
        Dict mit start_idx, n_pts, F01–F03, F04_bin.
    """
    n         = len(seg)
    length_mm = n * mm_per_point
    peak_mm   = float(np.max(seg))
    height_um = (peak_mm - mean_mm) * 1000.0
    # Fläche = Integral der Überhöhung über dem Mittelwert (µm·mm)
    excess_um = (seg - mean_mm) * 1000.0
    area      = float(np.trapezoid(excess_um) * mm_per_point)
    # Bin-Zuweisung: Steigung height_um/length_mm
    # > BIN_THRESHOLD → Bin 1 (Kurzhocker), sonst Bin 2 (Langwelle)
    steigung  = height_um / max(1e-9, length_mm)
    bin_id    = 1 if steigung > BIN_THRESHOLD else 2
    return {
        "start_idx":      start_idx,
        "n_pts":          n,
        "F01_length_mm":  length_mm,
        "F02_height_um":  height_um,
        "F03_area_um_mm": area,
        "F04_bin":        bin_id,
    }


# ---------------------------------------------------------------------------
# Aggregation: Mittelwerte je Bin
# ---------------------------------------------------------------------------

def aggregate_per_100m(spots: List[Dict[str, Any]],
                       total_length_mm: float) -> Dict[int, Dict[str, Any]]:
    scale = (100_000.0 / total_length_mm) if total_length_mm > 0 else 0.0
    result = {}
    for bin_id in (1, 2):
        grp = [s for s in spots if s["F04_bin"] == bin_id]
        feat_means: Dict[str, float] = {}
        for k in FEATURE_KEYS:
            vals = [s[k] for s in grp if np.isfinite(float(s[k]))]
            feat_means[k] = float(np.mean(vals)) if vals else float('nan')
        result[bin_id] = {
            "count_per_100m": len(grp) * scale,
            "n_abs":          len(grp),
            "features":       feat_means,
        }
    return result


# ---------------------------------------------------------------------------
# Histogramme: 3 Features × 2 Bins × 20 Felder
# ---------------------------------------------------------------------------

def compute_histograms(spots: List[Dict[str, Any]],
                       total_length_mm: float,
                       n_bins: int = N_HIST_BINS) -> Dict[str, Any]:
    """Berechnet 20-Bin-Histogramme für alle drei Features (F01/F02/F03).

    Vektorisiert: alle Feature-Werte werden einmalig als NumPy-Arrays
    extrahiert, dann per np.histogram ausgewertet.

    Args:
        spots:            Liste von Dickstellen-Dicts.
        total_length_mm:  Gesamtlänge der Serie in mm (für /100m-Normierung).
        n_bins:           Anzahl Histogramm-Bins (Standard: 20).

    Returns:
        Dict {feature_key: {edges, counts_1, counts_2}}.
    """
    scale = (100_000.0 / total_length_mm) if total_length_mm > 0 else 0.0

    if not spots:
        result = {}
        for fk in FEATURE_KEYS:
            edges = np.linspace(0.0, 1.0, n_bins + 1)
            result[fk] = {"edges": edges,
                          "counts_1": np.zeros(n_bins),
                          "counts_2": np.zeros(n_bins)}
        return result

    # Alle Werte einmalig als Arrays extrahieren (schneller als pro-Feature-Listcomp)
    bins_arr = np.array([s["F04_bin"] for s in spots], dtype=np.int8)
    mask1    = bins_arr == 1
    mask2    = bins_arr == 2

    result = {}
    for fk in FEATURE_KEYS:
        vals = np.array([s[fk] for s in spots], dtype=float)
        v1   = vals[mask1]
        v2   = vals[mask2]
        all_v = vals  # gemeinsame Grenzen über beide Bins
        fin   = all_v[np.isfinite(all_v)]
        if fin.size == 0:
            edges = np.linspace(0.0, 1.0, n_bins + 1)
            result[fk] = {"edges": edges,
                          "counts_1": np.zeros(n_bins),
                          "counts_2": np.zeros(n_bins)}
            continue
        vmin, vmax = float(fin.min()), float(fin.max())
        if vmin == vmax:
            vmax = vmin + 1.0
        edges = np.linspace(vmin, vmax, n_bins + 1)
        c1 = np.histogram(v1[np.isfinite(v1)], bins=edges)[0].astype(float) * scale
        c2 = np.histogram(v2[np.isfinite(v2)], bins=edges)[0].astype(float) * scale
        result[fk] = {"edges": edges, "counts_1": c1, "counts_2": c2}
    return result


# ---------------------------------------------------------------------------
# DB-Werte zusammenstellen (fuer die Verteilung/Garnspiegel-Visuals im
# Single-Trial-ATY-Tab -- NICHT fuer tblLaborATYoMat-Persistenz, siehe
# Modul-Docstring)
# ---------------------------------------------------------------------------

def compute_db_values(spots: List[Dict[str, Any]],
                      total_length_mm: float) -> Dict[str, Any]:
    """
    Gibt Zusammenfassungs-Kennzahlen zurueck (fuer die on-screen-Metrikanzeige
    im Single-Trial-ATY-Tab). Schluessel folgen der alten tblLaborATYoMat-
    Spaltenbenennung aus historischen Gruenden, werden aber seit 2026-08-13
    nicht mehr dorthin geschrieben.
    """
    agg  = aggregate_per_100m(spots, total_length_mm)
    hist = compute_histograms(spots, total_length_mm)

    vals: Dict[str, Any] = {
        "TotalLen_m":   total_length_mm / 1000.0,
        "BinThreshold": BIN_THRESHOLD,
        "N_B1":         agg[1]["count_per_100m"],
        "N_B2":         agg[2]["count_per_100m"],
        "AvgLen_B1":    agg[1]["features"].get("F01_length_mm"),
        "AvgLen_B2":    agg[2]["features"].get("F01_length_mm"),
        "AvgHeight_B1": agg[1]["features"].get("F02_height_um"),
        "AvgHeight_B2": agg[2]["features"].get("F02_height_um"),
        "AvgArea_B1":   agg[1]["features"].get("F03_area_um_mm"),
        "AvgArea_B2":   agg[2]["features"].get("F03_area_um_mm"),
    }

    # 3 Features × 2 Bins × 20 Felder
    for fk, prefix in FEATURE_DB_PREFIX.items():
        h = hist[fk]
        for i in range(N_HIST_BINS):
            vals[f"{prefix}_b1_bin_{i+1}"] = float(h["counts_1"][i])
            vals[f"{prefix}_b2_bin_{i+1}"] = float(h["counts_2"][i])

    return vals


# ---------------------------------------------------------------------------
# Dateiname-Parsing (analog dty_knots_view.py)
# ---------------------------------------------------------------------------

def _parse_ids_from_filename(path) -> Optional[Tuple[int, int]]:
    """Erste Zahl vor erstem '_' = TrialSeriesID, zweite = Versuchsnummer."""
    stem = Path(path).stem
    try:
        first_us = stem.index("_")
    except ValueError:
        return None
    i = first_us - 1
    while i >= 0 and stem[i].isdigit():
        i -= 1
    num1 = stem[i+1:first_us]
    if not num1:
        return None
    try:
        second_us = stem.index("_", first_us + 1)
    except ValueError:
        return None
    j = second_us - 1
    while j > first_us and stem[j].isdigit():
        j -= 1
    num2 = stem[j+1:second_us]
    if not num2:
        return None
    try:
        return int(num1), int(num2)
    except ValueError:
        return None
