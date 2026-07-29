"""
thick_spot_analysis.py – Dickstellen-Analyse fuer ATY-Garn + DB-Speicherung

Datei gehört nach ui/yarnscope/thick_spot_analysis.py

Bin-Logik: height_um / length_mm > BIN_THRESHOLD → Bin1 (Kurzhocker), sonst Bin2 (Langwelle)
Features:  F01 Laenge [mm], F02 Hoehe [um], F03 Flaeche [um*mm]
Histogramm: je Feature × je Bin → 20 Intervalle (Anzahl/100m)
DB:        tblLaborATYoMat – INSERT oder UPDATE per Knopfdruck
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
# DB-Werte zusammenstellen
# ---------------------------------------------------------------------------

def compute_db_values(spots: List[Dict[str, Any]],
                      total_length_mm: float) -> Dict[str, Any]:
    """
    Gibt alle Werte fuer tblLaborATYoMat als Dict zurueck.
    Schluessel = Spaltenname.
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
# DB-Hilfsfunktionen (analog dty_knots_view.py)
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


def _lookup_trial_id(trial_series_id: int, versuchsnummer: int) -> Optional[int]:
    try:
        from db.connection import fetch_all
    except Exception:
        return None
    # tblTrial (ohne s) laut Rueckmeldung
    for tbl in ("tblTrial", "tblTrials"):
        try:
            rows = fetch_all(
                f"SELECT ID FROM {tbl} WHERE TrialSeriesID = ? AND Versuchsnummer = ?",
                (trial_series_id, versuchsnummer))
            if rows:
                r = rows[0]
                for key in ("ID", "Id", "id"):
                    if key in r:
                        return int(r[key])
                return int(list(r.values())[0])
        except Exception:
            continue
    return None


def _lookup_global_id(trial_id: int) -> Optional[str]:
    try:
        from db.connection import fetch_all
    except Exception:
        return None
    for tbl in ("tblTrial", "tblTrials"):
        try:
            rows = fetch_all(f"SELECT GlobalID FROM {tbl} WHERE ID = ?", (trial_id,))
            if rows:
                r = rows[0]
                v = r.get("GlobalID") if isinstance(r, dict) else r[0]
                return str(v) if v else None
        except Exception:
            continue
    return None


def _atyomat_exists(trial_id: int) -> bool:
    try:
        from db.connection import fetch_all
    except Exception:
        return False
    try:
        rows = fetch_all("SELECT 1 AS x FROM tblLaborATYoMat WHERE TrialID = ?", (trial_id,))
        return bool(rows)
    except Exception:
        return False


def _do_execute(sql, params):
    from db.connection import execute
    execute(sql, params)


# ---------------------------------------------------------------------------
# Speichern (INSERT / UPDATE)
# ---------------------------------------------------------------------------

def save_to_db(panel) -> Tuple[bool, str]:
    """
    Liest Dateiname aus panel.current_file_path, bestimmt TrialID,
    und schreibt INSERT oder UPDATE in tblLaborATYoMat.
    Gibt (success: bool, message: str) zurueck.
    """
    from datetime import datetime

    # Datenpruefung
    series = getattr(panel, "series_mm_full", None)
    if series is None or len(series) == 0:
        return False, "Keine Daten geladen."

    file_path = getattr(panel, "current_file_path", None)
    if not file_path:
        return False, "Kein Dateipfad bekannt."

    ids = _parse_ids_from_filename(file_path)
    if ids is None:
        return False, f"TrialSeriesID/Versuchsnummer konnte nicht aus Dateiname geparst werden.\n({Path(file_path).name})"

    ts_id, vnr = ids
    trial_id = _lookup_trial_id(ts_id, vnr)
    if trial_id is None:
        return False, f"Kein Trial gefunden fuer TrialSeriesID={ts_id}, Versuchsnummer={vnr}."

    global_id = _lookup_global_id(trial_id)

    # Berechnung
    mm_step      = float(panel._mm_step())
    total_len_mm = len(series) * mm_step
    spots = detect_thick_spots(series, mm_step)
    db_vals = compute_db_values(spots, total_len_mm)

    ts  = datetime.now()
    try:
        from core.app_meta import current_user
        uid = current_user.get("id")
    except Exception:
        uid = None

    exists = _atyomat_exists(trial_id)

    # Spalten und Werte in fixer Reihenfolge aufbauen
    COL_SUMMARY = [
        "TotalLen_m", "BinThreshold",
        "N_B1", "N_B2",
        "AvgLen_B1", "AvgLen_B2",
        "AvgHeight_B1", "AvgHeight_B2",
        "AvgArea_B1", "AvgArea_B2",
    ]
    COL_HIST = []
    for fk, prefix in FEATURE_DB_PREFIX.items():
        for bid in (1, 2):
            for i in range(N_HIST_BINS):
                COL_HIST.append(f"{prefix}_b{'1' if bid==1 else '2'}_bin_{i+1}")

    all_data_cols = COL_SUMMARY + COL_HIST   # 10 + 120 = 130 Datenspalten
    data_params   = [db_vals.get(c) for c in all_data_cols]

    try:
        if exists:
            set_clause = ", ".join(f"{c} = ?" for c in all_data_cols)
            set_clause += ", Timestamp = ?, UserID = ?"
            sql    = f"UPDATE tblLaborATYoMat SET {set_clause} WHERE TrialID = ?"
            params = data_params + [ts, uid, trial_id]
            _do_execute(sql, params)
            return True, f"Aktualisiert: TrialID={trial_id} (TS={ts_id}, V{vnr})"
        else:
            col_names  = ["GlobalID", "TrialID"] + all_data_cols + ["Timestamp", "UserID"]
            placeholders = ", ".join("?" for _ in col_names)
            sql    = f"INSERT INTO tblLaborATYoMat ({', '.join(col_names)}) VALUES ({placeholders})"
            params = [global_id, trial_id] + data_params + [ts, uid]
            _do_execute(sql, params)
            return True, f"Gespeichert: TrialID={trial_id} (TS={ts_id}, V{vnr})"
    except Exception as e:
        return False, f"DB-Fehler: {e}"


# ---------------------------------------------------------------------------
# Qt-Tab-Setup
# ---------------------------------------------------------------------------

def setup_thick_spot_tab(panel) -> None:
    from PySide6 import QtWidgets, QtGui
    from PySide6.QtCore import Qt
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
    from matplotlib.figure import Figure

    tab   = QtWidgets.QWidget()
    outer = QtWidgets.QVBoxLayout(tab)
    outer.setContentsMargins(4, 4, 4, 4)
    outer.setSpacing(4)

    # ---- Kopfzeile: Info + Speichern-Button ----
    head_row = QtWidgets.QHBoxLayout()
    panel._ts_info_label = QtWidgets.QLabel("Keine Daten geladen.")
    panel._ts_info_label.setStyleSheet("color: #444; font-size: 11px;")
    head_row.addWidget(panel._ts_info_label, 1)

    panel._ts_save_btn = QtWidgets.QPushButton("In DB speichern")
    panel._ts_save_btn.setEnabled(False)
    panel._ts_save_btn.setFixedWidth(130)
    panel._ts_save_btn.setStyleSheet(
        "QPushButton { background: #2e7d32; color: white; border-radius: 4px; padding: 4px 8px; }"
        "QPushButton:disabled { background: #aaa; }"
        "QPushButton:hover:enabled { background: #1b5e20; }"
    )
    panel._ts_save_btn.clicked.connect(lambda: _on_save_clicked(panel))
    head_row.addWidget(panel._ts_save_btn)

    panel._ts_save_status = QtWidgets.QLabel("")
    panel._ts_save_status.setStyleSheet("font-size: 11px;")
    panel._ts_save_status.setMinimumWidth(260)
    head_row.addWidget(panel._ts_save_status)

    outer.addLayout(head_row)

    # ---- Haupt-Splitter ----
    splitter = QtWidgets.QSplitter(Qt.Horizontal)

    # Links: Profil + Scatter
    left_w = QtWidgets.QWidget()
    left_v = QtWidgets.QVBoxLayout(left_w)
    left_v.setContentsMargins(0, 0, 0, 0)
    left_v.setSpacing(2)

    panel._ts_fig        = Figure(figsize=(5, 4), dpi=100)
    panel._ts_ax_profile = panel._ts_fig.add_subplot(211)
    panel._ts_ax_scatter = panel._ts_fig.add_subplot(212)
    panel._ts_fig.subplots_adjust(left=0.12, right=0.97, top=0.93, bottom=0.12, hspace=0.55)
    panel._ts_canvas  = FigureCanvas(panel._ts_fig)
    panel._ts_canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
    panel._ts_toolbar = NavigationToolbar(panel._ts_canvas, left_w)
    try:
        panel._ts_toolbar.coordinates.setVisible(False)
    except Exception:
        pass
    left_v.addWidget(panel._ts_toolbar)
    left_v.addWidget(panel._ts_canvas, 1)

    # Rechts: Dropdown + Histogramm-Plot + Histogramm-Tabelle
    right_w = QtWidgets.QWidget()
    right_v = QtWidgets.QVBoxLayout(right_w)
    right_v.setContentsMargins(4, 0, 0, 0)
    right_v.setSpacing(4)

    dd_row = QtWidgets.QHBoxLayout()
    dd_row.addWidget(QtWidgets.QLabel("Feature:"))
    panel._ts_feature_combo = QtWidgets.QComboBox()
    for fk in FEATURE_KEYS:
        panel._ts_feature_combo.addItem(FEATURE_LABELS[fk], fk)
    dd_row.addWidget(panel._ts_feature_combo, 1)
    right_v.addLayout(dd_row)

    panel._ts_hist_fig = Figure(figsize=(4, 2.5), dpi=100)
    panel._ts_hist_ax  = panel._ts_hist_fig.add_subplot(111)
    panel._ts_hist_fig.subplots_adjust(left=0.14, right=0.97, top=0.88, bottom=0.20)
    panel._ts_hist_canvas = FigureCanvas(panel._ts_hist_fig)
    panel._ts_hist_canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
    right_v.addWidget(panel._ts_hist_canvas, 1)

    panel._ts_hist_table = QtWidgets.QTableWidget(N_HIST_BINS, 3)
    panel._ts_hist_table.setHorizontalHeaderLabels(["Intervall", "Bin 1 /100m", "Bin 2 /100m"])
    panel._ts_hist_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    panel._ts_hist_table.setAlternatingRowColors(True)
    panel._ts_hist_table.setStyleSheet(
        "QTableWidget { background: white; alternate-background-color: #f0f8f0; }"
        "QTableWidget::item:selected { background: #c8e8c8; color: black; }"
    )
    panel._ts_hist_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
    panel._ts_hist_table.verticalHeader().setDefaultSectionSize(22)
    panel._ts_hist_table.verticalHeader().setVisible(False)
    try:
        QtGui.QShortcut(QtGui.QKeySequence.Copy, panel._ts_hist_table,
                        activated=lambda: _copy_ts_table(panel._ts_hist_table))
    except Exception:
        pass
    right_v.addWidget(panel._ts_hist_table, 1)

    splitter.addWidget(left_w)
    splitter.addWidget(right_w)
    splitter.setStretchFactor(0, 3)
    splitter.setStretchFactor(1, 2)
    outer.addWidget(splitter, 3)

    # ---- Untere Übersichts-Tabelle ----
    lbl_ov = QtWidgets.QLabel("Overview: mean values per bin")
    lbl_ov.setStyleSheet("font-weight: bold; font-size: 11px; margin-top: 4px;")
    outer.addWidget(lbl_ov)

    n_rows = 1 + len(FEATURE_KEYS)
    panel._ts_table = QtWidgets.QTableWidget(n_rows, 2)
    panel._ts_table.setHorizontalHeaderLabels([
        "Bin 1 – Kurzhocker (Stg > 100 um/mm)",
        "Bin 2 – Langwelle  (Stg <= 100 um/mm)",
    ])
    row_labels = ["Anzahl / 100 m"] + [FEATURE_LABELS[k] for k in FEATURE_KEYS]
    panel._ts_table.setVerticalHeaderLabels(row_labels)
    panel._ts_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    panel._ts_table.setAlternatingRowColors(True)
    panel._ts_table.setStyleSheet(
        "QTableWidget { background: white; alternate-background-color: #fff3e0; }"
        "QTableWidget::item:selected { background: #ffe0b2; color: black; }"
    )
    panel._ts_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
    panel._ts_table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
    for col, bg in ((0, "#ffe8cc"), (1, "#ccf0f0")):
        it = QtWidgets.QTableWidgetItem("-")
        it.setTextAlignment(Qt.AlignCenter)
        it.setBackground(QtGui.QColor(bg))
        f = it.font(); f.setBold(True); it.setFont(f)
        panel._ts_table.setItem(0, col, it)
    try:
        QtGui.QShortcut(QtGui.QKeySequence.Copy, panel._ts_table,
                        activated=lambda: _copy_ts_table(panel._ts_table))
    except Exception:
        pass
    outer.addWidget(panel._ts_table, 1)

    panel.tabs.addTab(tab, "Dickst.-Analyse")
    panel._ts_tab_widget = tab
    panel._ts_histograms = {}

    panel._ts_feature_combo.currentIndexChanged.connect(
        lambda _: _redraw_histogram(panel))


# ---------------------------------------------------------------------------
# Speichern-Knopf Handler
# ---------------------------------------------------------------------------

def _on_save_clicked(panel) -> None:
    from PySide6 import QtWidgets
    panel._ts_save_btn.setEnabled(False)
    panel._ts_save_status.setText("Speichere…")
    QtWidgets.QApplication.processEvents()
    try:
        ok, msg = save_to_db(panel)
        if ok:
            panel._ts_save_status.setStyleSheet("color: #2e7d32; font-size: 11px;")
        else:
            panel._ts_save_status.setStyleSheet("color: #c62828; font-size: 11px;")
        panel._ts_save_status.setText(msg)
    except Exception as e:
        panel._ts_save_status.setStyleSheet("color: #c62828; font-size: 11px;")
        panel._ts_save_status.setText(f"Fehler: {e}")
    finally:
        panel._ts_save_btn.setEnabled(True)


# ---------------------------------------------------------------------------
# Histogramm neu zeichnen
# ---------------------------------------------------------------------------

def _redraw_histogram(panel) -> None:
    from PySide6 import QtWidgets, QtGui
    from PySide6.QtCore import Qt
    import numpy as _np

    hists = getattr(panel, "_ts_histograms", {})
    if not hists:
        return
    fk    = panel._ts_feature_combo.currentData()
    label = panel._ts_feature_combo.currentText()
    if fk not in hists:
        return

    h      = hists[fk]
    edges  = h["edges"]
    c1     = h["counts_1"]
    c2     = h["counts_2"]
    width  = (edges[1] - edges[0]) * 0.42
    centers = 0.5 * (edges[:-1] + edges[1:])

    ax = panel._ts_hist_ax
    ax.clear()
    ax.bar(centers - width/2, c1, width=width, color=BIN1_COLOR, alpha=0.85, label="Bin 1")
    ax.bar(centers + width/2, c2, width=width, color=BIN2_COLOR, alpha=0.85, label="Bin 2")
    ax.set_xlabel(label, fontsize=7)
    ax.set_ylabel("Anzahl / 100 m", fontsize=7)
    ax.set_title(f"Verteilung: {label}", fontsize=8)
    ax.tick_params(labelsize=6)
    ax.legend(fontsize=6, framealpha=0.7)
    panel._ts_hist_canvas.draw_idle()

    def _fmt(v):
        try:
            vv = float(v)
            if not _np.isfinite(vv): return "-"
            if abs(vv) >= 10000:     return f"{vv:,.0f}".replace(",", "'")
            elif abs(vv) >= 100:     return f"{vv:.1f}"
            elif abs(vv) >= 1:       return f"{vv:.2f}"
            else:                    return f"{vv:.4f}"
        except Exception:
            return "-"

    tbl = panel._ts_hist_table
    tbl.blockSignals(True)
    try:
        for i in range(N_HIST_BINS):
            lo, hi = edges[i], edges[i+1]
            for col, val, bg in (
                (0, f"{_fmt(lo)} – {_fmt(hi)}", None),
                (1, c1[i], "#fff0e0"),
                (2, c2[i], "#e0f8f8"),
            ):
                from PySide6 import QtWidgets as _qw, QtGui as _qg
                it = _qw.QTableWidgetItem(val if isinstance(val, str) else _fmt(val))
                it.setTextAlignment(Qt.AlignCenter)
                if bg:
                    it.setBackground(_qg.QColor(bg))
                tbl.setItem(i, col, it)
    finally:
        tbl.blockSignals(False)


# ---------------------------------------------------------------------------
# Tabelle kopieren
# ---------------------------------------------------------------------------

def _copy_ts_table(table) -> None:
    from PySide6 import QtWidgets
    sel = table.selectedIndexes()
    if not sel:
        return
    rows = sorted({i.row() for i in sel})
    cols = sorted({i.column() for i in sel})
    hdr  = [""] + [
        (table.horizontalHeaderItem(c).text().replace("\n", " ")
         if table.horizontalHeaderItem(c) else "") for c in cols]
    lines = ["\t".join(hdr)]
    for r in rows:
        vi    = table.verticalHeaderItem(r)
        parts = [vi.text() if vi else ""]
        for c in cols:
            it = table.item(r, c)
            parts.append(it.text() if it else "")
        lines.append("\t".join(parts))
    QtWidgets.QApplication.clipboard().setText("\n".join(lines))


# ---------------------------------------------------------------------------
# Update (wird von GarnPanel.recompute_and_plot aufgerufen)
# ---------------------------------------------------------------------------

def update_thick_spot_tab(panel) -> None:
    if not hasattr(panel, "_ts_fig"):
        return

    from PySide6 import QtWidgets, QtGui
    from PySide6.QtCore import Qt
    import numpy as _np

    series = getattr(panel, "series_mm_full", None)
    if series is None or len(series) == 0:
        panel._ts_info_label.setText("Keine Daten geladen.")
        panel._ts_ax_profile.clear()
        panel._ts_ax_scatter.clear()
        panel._ts_canvas.draw_idle()
        try:
            panel._ts_save_btn.setEnabled(False)
            panel._ts_save_status.setText("")
        except Exception:
            pass
        return

    mm_step      = float(panel._mm_step())
    total_len_mm = len(series) * mm_step

    spots = detect_thick_spots(series, mm_step)
    agg   = aggregate_per_100m(spots, total_len_mm)
    n1, n2 = agg[1]["n_abs"], agg[2]["n_abs"]

    panel._ts_histograms = compute_histograms(spots, total_len_mm)

    # Speichern-Button aktivieren + TrialID-Vorschau
    try:
        fp = getattr(panel, "current_file_path", None)
        ids = _parse_ids_from_filename(fp) if fp else None
        if ids:
            tid = _lookup_trial_id(ids[0], ids[1])
            if tid:
                exists = _atyomat_exists(tid)
                lbl = "Aktualisieren" if exists else "In DB speichern"
                panel._ts_save_btn.setText(lbl)
                panel._ts_save_btn.setEnabled(True)
                panel._ts_save_status.setStyleSheet("color: #555; font-size: 11px;")
                panel._ts_save_status.setText(
                    f"TrialID={tid}  ({'UPDATE' if exists else 'INSERT'})")
            else:
                panel._ts_save_btn.setEnabled(False)
                panel._ts_save_status.setStyleSheet("color: #c62828; font-size: 11px;")
                panel._ts_save_status.setText(
                    f"Kein Trial gefunden (TS={ids[0]}, V{ids[1]})")
        else:
            panel._ts_save_btn.setEnabled(False)
            panel._ts_save_status.setText("")
    except Exception:
        pass

    panel._ts_info_label.setText(
        f"Laenge: {total_len_mm/1000:.1f} m  |  Dickstellen: {n1+n2}  |  "
        f"Bin 1 Kurzhocker: {n1} ({agg[1]['count_per_100m']:.1f}/100m)  |  "
        f"Bin 2 Langwelle: {n2} ({agg[2]['count_per_100m']:.1f}/100m)"
    )

    # ---- Profil-Plot ----
    ax1 = panel._ts_ax_profile
    ax1.clear()
    start_pt      = int(getattr(panel, "current_start_points", 0))
    needed        = panel._needed_points()
    view_arr      = series[start_pt: start_pt + needed]
    x_pos         = _np.arange(len(view_arr)) * mm_step
    mean_mm       = float(_np.mean(series))
    view_start_mm = start_pt * mm_step
    view_end_mm   = view_start_mm + len(view_arr) * mm_step

    ax1.plot(x_pos, view_arr * 1000, color="#bbbbbb", linewidth=0.5, zorder=1)
    ax1.axhline(mean_mm * 1000, color="#666", linewidth=0.8, linestyle="--", zorder=2)

    for sp in spots:
        sp_s = sp["start_idx"] * mm_step
        sp_e = (sp["start_idx"] + sp["n_pts"]) * mm_step
        if sp_e < view_start_mm or sp_s > view_end_mm:
            continue
        sl_s = max(0, sp["start_idx"] - start_pt)
        seg  = view_arr[sl_s: sl_s + sp["n_pts"]]
        if len(seg) < 2:
            continue
        xs     = _np.linspace(sp_s - view_start_mm, sp_e - view_start_mm, len(seg))
        c_fill = BIN1_FILL  if sp["F04_bin"] == 1 else BIN2_FILL
        c_edge = BIN1_COLOR if sp["F04_bin"] == 1 else BIN2_COLOR
        ax1.fill_between(xs, mean_mm*1000, seg*1000, color=c_fill, alpha=0.75, linewidth=0, zorder=3)
        ax1.plot(xs, seg*1000, color=c_edge, linewidth=0.8, zorder=4)

    from matplotlib.patches import Patch
    ax1.legend(handles=[
        Patch(color=BIN1_FILL, label=f"Bin 1 Kurzhocker (n={n1})"),
        Patch(color=BIN2_FILL, label=f"Bin 2 Langwelle (n={n2})"),
    ], fontsize=6, loc="upper right", framealpha=0.7)
    ax1.set_ylabel("Dicke [um]",    fontsize=7)
    ax1.set_xlabel("Position [mm]", fontsize=7)
    ax1.set_title("Garnprofil – Bins (Ausschnitt 2 m)", fontsize=8)
    ax1.tick_params(labelsize=6)

    # ---- Scatter-Plot ----
    ax2 = panel._ts_ax_scatter
    ax2.clear()
    if spots:
        lengths = _np.array([s["F01_length_mm"] for s in spots])
        heights = _np.array([s["F02_height_um"]  for s in spots])
        areas   = _np.array([s["F03_area_um_mm"] for s in spots])
        bins    = _np.array([s["F04_bin"]         for s in spots])
        a_min, a_max = areas.min(), areas.max()
        sizes = (10 + 190*(areas-a_min)/(a_max-a_min)
                 if a_max > a_min else _np.full(len(areas), 30.0))
        for bid, col in ((1, BIN1_COLOR), (2, BIN2_COLOR)):
            m = bins == bid
            if _np.any(m):
                ax2.scatter(lengths[m], heights[m], s=sizes[m], c=col,
                            alpha=0.55, linewidths=0.3, edgecolors="white",
                            label=f"Bin {bid} (n={int(m.sum())})", zorder=3)
        x_line = _np.array([0.0, lengths.max()*1.05])
        ax2.plot(x_line, x_line*BIN_THRESHOLD, "--", color="#999", linewidth=1.0,
                 label=f"Schwelle {BIN_THRESHOLD:.0f} um/mm", zorder=2)
        ax2.set_xlim(left=0); ax2.set_ylim(bottom=0)
        ax2.legend(fontsize=6, loc="upper left", framealpha=0.7)
    ax2.set_xlabel("Laenge [mm]", fontsize=7)
    ax2.set_ylabel("Hoehe [um]",  fontsize=7)
    ax2.set_title(f"Laenge vs. Hoehe (Schwelle {BIN_THRESHOLD:.0f} um/mm)", fontsize=8)
    ax2.tick_params(labelsize=6)
    panel._ts_canvas.draw_idle()

    _redraw_histogram(panel)

    # ---- Übersichts-Tabelle ----
    def _fmt(v):
        try:
            vv = float(v)
            if not _np.isfinite(vv): return "-"
            if abs(vv) >= 10000:     return f"{vv:,.0f}".replace(",", "'")
            elif abs(vv) >= 100:     return f"{vv:.1f}"
            elif abs(vv) >= 1:       return f"{vv:.2f}"
            else:                    return f"{vv:.4f}"
        except Exception:
            return "-"

    tbl = panel._ts_table
    tbl.blockSignals(True)
    try:
        for col, bid, bg in ((0, 1, "#ffe8cc"), (1, 2, "#ccf0f0")):
            cnt = agg[bid]["count_per_100m"]
            it  = QtWidgets.QTableWidgetItem(f"{cnt:.1f}" if _np.isfinite(cnt) else "-")
            it.setTextAlignment(Qt.AlignCenter)
            it.setBackground(QtGui.QColor(bg))
            f = it.font(); f.setBold(True); it.setFont(f)
            tbl.setItem(0, col, it)
        for row_idx, fk in enumerate(FEATURE_KEYS, start=1):
            for col, bid in ((0, 1), (1, 2)):
                val = agg[bid]["features"].get(fk, float('nan'))
                it  = QtWidgets.QTableWidgetItem(_fmt(val))
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                tbl.setItem(row_idx, col, it)
    finally:
        tbl.blockSignals(False)