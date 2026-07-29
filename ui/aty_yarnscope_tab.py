"""
aty_yarnscope_tab.py – vollständiger ATY YarnScope-Tab für TrippleT

Enthält alle Funktionen die am Ende von screen_show_experiment.py
via Monkey-Patching auf ShowExperimentScreen registriert werden.

Sub-Tabs:
  [0] Verteilung  – Feature-Dropdown + Histogramm + Tabelle
  [1] Garnspiegel – GarnCanvas.plot_garnspiegel (Di/Dü-Farbcodierung)
  [2] Fabric      – ATYFabricCanvas (horizontale Bänder, Di/Dü-Farbcodierung)

Gemeinsame Steuerung (gilt für alle visuellen Sub-Tabs):
  - Startpunkt [m]
  - Garnspiegel: Anzahl Zeilen (num_turns), Gap-Faktor
  - Fabric: Anzahl Bänder
  - Farb-Editor: Di11..Di33, Dü11..Dü33 per Farbpicker änderbar
  - Sichtbarkeit: Checkboxen je Klasse
  - «Anzeigen»-Button: rendert Garnspiegel + Fabric neu

Alle Visualisierungen nutzen COLOR_STATE / VISIBILITY_STATE aus
garngraf_canvas.py – identisch zu YarnScope.
"""

from __future__ import annotations

import math
import sys
import traceback
from pathlib import Path
from typing import Optional

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSplitter, QTabWidget, QComboBox,
    QTableWidget, QHeaderView, QAbstractItemView, QTableWidgetItem,
    QSizePolicy, QDoubleSpinBox, QSpinBox, QGroupBox, QGridLayout,
    QCheckBox, QScrollArea, QFrame, QColorDialog,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as _FCA
from matplotlib.figure import Figure as _Fig

from db.connection import fetch_all
from ui.yarnscope.garngraf_canvas import (
    GarnCanvas, CLASS_THRESHOLDS, COLOR_STATE, VISIBILITY_STATE,
    DI_COLORS, DUE_COLORS,
)
from ui.yarnscope.aty_canvas import ATYFabricCanvas, ATYKnittedCanvas
from ui.yarnscope.dty_tdms_reader import (
    read_first_numeric_channel, read_step_mm_from_tdms,
)
from ui.yarnscope.thick_spot_analysis import (
    detect_thick_spots, compute_db_values,
    aggregate_per_100m, compute_histograms,
)

# ---------------------------------------------------------------------------
# TDMS-Ordner-Helpers
# ---------------------------------------------------------------------------

def _aty_tdms_base():
    return Path(r"H:\Technik\TrippleT\ATYtdms")

def _aty_series_has_tdms(series_id: int) -> bool:
    base = _aty_tdms_base()
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

def _aty_find_tdms(series_id: int, versuch_no: int):
    base = _aty_tdms_base()
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

# ---------------------------------------------------------------------------
# Tab aufbauen / entfernen
# ---------------------------------------------------------------------------

def _build_aty_yarnscope_tab(self):
    """Einstiegspunkt: wird nach load_record() aufgerufen."""
    sid = self._series_pk
    if sid is None or not _aty_series_has_tdms(sid):
        _remove_aty_yarnscope_tab_if_exists(self)
        return
    _create_aty_yarnscope_tab_if_needed(self)
    _aty_populate_trial_list(self)

def _remove_aty_yarnscope_tab_if_exists(self):
    if self.tab_aty_yarnscope is None:
        return
    idx = self.tabs.indexOf(self.tab_aty_yarnscope)
    if idx != -1:
        self.tabs.removeTab(idx)
    self.tab_aty_yarnscope.deleteLater()
    self.tab_aty_yarnscope = None
    self._aty_trial_list = None

def _create_aty_yarnscope_tab_if_needed(self):
    """Baut den kompletten ATY-Tab einmalig auf."""
    if self.tab_aty_yarnscope is not None:
        return

    # ── Haupt-Widget ──────────────────────────────────────────────────────
    self.tab_aty_yarnscope = QWidget()
    root = QVBoxLayout(self.tab_aty_yarnscope)
    root.setContentsMargins(8, 8, 8, 8)
    root.setSpacing(6)

    splitter = QSplitter(Qt.Horizontal)

    # ══════════════════════════════════════════════════════════════════════
    # LINKS: Trial-Liste
    # ══════════════════════════════════════════════════════════════════════
    left = QWidget(); left.setMaximumWidth(210)
    lv = QVBoxLayout(left); lv.setContentsMargins(0,0,0,0); lv.setSpacing(4)
    lbl_t = QLabel("Trials")
    lbl_t.setStyleSheet("font-weight:bold; color:#88dddd; font-size:13px;")
    lv.addWidget(lbl_t)
    self._aty_trial_list = QListWidget()
    self._aty_trial_list.setStyleSheet("""
        QListWidget{background:#1a1a1a;color:#ddd;border:1px solid #333;font-size:12px;}
        QListWidget::item{padding:4px 6px;}
        QListWidget::item:selected{background:#0e6e6e;color:#fff;}
        QListWidget::item:hover{background:#2a2a2a;}
    """)
    self._aty_trial_list.currentRowChanged.connect(
        lambda row: _aty_on_trial_selected(self, row))
    lv.addWidget(self._aty_trial_list, 1)
    splitter.addWidget(left)

    # ══════════════════════════════════════════════════════════════════════
    # RECHTS: Analyse-Bereich
    # ══════════════════════════════════════════════════════════════════════
    right = QWidget()
    rv = QVBoxLayout(right); rv.setContentsMargins(4,0,0,0); rv.setSpacing(4)

    # Datei-Info
    self._aty_lbl_file = QLabel("No trial selected")
    self._aty_lbl_file.setStyleSheet("color:#aaa; font-size:11px;")
    rv.addWidget(self._aty_lbl_file)

    # ── Sub-Tabs ──────────────────────────────────────────────────────────
    self._aty_sub_tabs = QTabWidget()
    self._aty_sub_tabs.setStyleSheet("""
        QTabWidget::pane{border:1px solid #333;background:#1e1e1e;}
        QTabBar::tab{background:#1a1a1a;color:#aaa;padding:4px 12px;
                     border:1px solid #333;border-bottom:none;font-size:12px;}
        QTabBar::tab:selected{background:#1e1e1e;color:#88dddd;}
        QTabBar::tab:hover{background:#2a2a2a;color:#ddd;}
    """)

    # ── Sub-Tab 0: Verteilung ─────────────────────────────────────────────
    dist_w = QWidget(); dist_w.setStyleSheet("background:#1e1e1e;")
    dist_v = QVBoxLayout(dist_w); dist_v.setContentsMargins(4,4,4,4); dist_v.setSpacing(4)
    dd_row = QHBoxLayout()
    dd_row.addWidget(QLabel("Feature:"))
    self._aty_feature_combo = QComboBox()
    self._aty_feature_combo.setStyleSheet(
        "QComboBox{background:#2a2a2a;color:#ddd;border:1px solid #444;padding:2px 6px;font-size:12px;}"
        "QComboBox QAbstractItemView{background:#2a2a2a;color:#ddd;selection-background-color:#0e6e6e;}")
    for fk, label in (("F01_length_mm","Laenge [mm]"),("F02_height_um","Hoehe [um]"),("F03_area_um_mm","Flaeche [um*mm]")):
        self._aty_feature_combo.addItem(label, fk)
    dd_row.addWidget(self._aty_feature_combo, 1)
    dist_v.addLayout(dd_row)
    _fig = _Fig(figsize=(6,2.5), facecolor="#1e1e1e")
    _fig.subplots_adjust(left=0.12, right=0.97, top=0.88, bottom=0.20)
    self._aty_hist_ax     = _fig.add_subplot(111)
    self._aty_hist_canvas = _FCA(_fig)
    self._aty_hist_canvas.setStyleSheet("background:#1e1e1e;")
    self._aty_hist_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    dist_v.addWidget(self._aty_hist_canvas, 2)
    self._aty_hist_table = QTableWidget(20, 3)
    self._aty_hist_table.setHorizontalHeaderLabels(["Intervall","Bin 1 /100m","Bin 2 /100m"])
    self._aty_hist_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    self._aty_hist_table.setAlternatingRowColors(True)
    self._aty_hist_table.setStyleSheet(
        "QTableWidget{background:#1e1e1e;alternate-background-color:#242424;color:#ddd;gridline-color:#333;}"
        "QHeaderView::section{background:#2a2a2a;color:#aaa;border:1px solid #333;padding:2px 4px;}"
        "QTableWidget::item:selected{background:#0e6e6e;color:#fff;}")
    self._aty_hist_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    self._aty_hist_table.verticalHeader().setDefaultSectionSize(22)
    self._aty_hist_table.verticalHeader().setVisible(False)
    dist_v.addWidget(self._aty_hist_table, 1)
    self._aty_sub_tabs.addTab(dist_w, "Verteilung")
    self._aty_feature_combo.currentIndexChanged.connect(lambda _: _aty_redraw_histogram(self))

    # ── Sub-Tab 1: Garnspiegel ────────────────────────────────────────────
    class _GsWidget(QWidget):
        """Wrapper mit showEvent-Trick: Canvas wird erst gezeichnet wenn sichtbar."""
        def __init__(self, parent, panel):
            super().__init__(parent); self._p = panel
            self.setStyleSheet("background:#000;")
        def showEvent(self, e):
            super().showEvent(e)
            QTimer.singleShot(60, lambda: _aty_draw_garnspiegel(self._p))

    gs_w = _GsWidget(right, self)
    gs_v = QVBoxLayout(gs_w); gs_v.setContentsMargins(0,0,0,0)
    try:
        self._aty_garn_canvas = GarnCanvas(gs_w)
        self._aty_garn_canvas._no_scroll = True
        gs_v.addWidget(self._aty_garn_canvas)
    except Exception as _e:
        lbl_e = QLabel(f"YarnCanvas not available: {_e}")
        lbl_e.setStyleSheet("color:#ff6060;padding:12px;")
        gs_v.addWidget(lbl_e)
        self._aty_garn_canvas = None
    self._aty_sub_tabs.addTab(gs_w, "Garnspiegel")

    # ── Sub-Tab 2: Fabric ─────────────────────────────────────────────────
    class _FabWidget(QWidget):
        """Wrapper mit showEvent-Trick für Fabric."""
        def __init__(self, parent, panel):
            super().__init__(parent); self._p = panel
            self.setStyleSheet("background:#000;")
        def showEvent(self, e):
            super().showEvent(e)
            QTimer.singleShot(60, lambda: _aty_draw_fabric(self._p))

    fab_w = _FabWidget(right, self)
    fab_v = QVBoxLayout(fab_w); fab_v.setContentsMargins(0,0,0,0)
    try:
        self._aty_fabric_canvas = ATYFabricCanvas(fab_w)
        fab_v.addWidget(self._aty_fabric_canvas)
    except Exception as _e:
        lbl_e = QLabel(f"ATYFabricCanvas not available: {_e}")
        lbl_e.setStyleSheet("color:#ff6060;padding:12px;")
        fab_v.addWidget(lbl_e)
        self._aty_fabric_canvas = None
    self._aty_sub_tabs.addTab(fab_w, "Fabric")

    # ── Sub-Tab 3: Knitted ────────────────────────────────────────────────
    class _KntWidget(QWidget):
        """Wrapper mit showEvent-Trick für Knitted."""
        def __init__(self, parent, panel):
            super().__init__(parent); self._p = panel
            self.setStyleSheet("background:#000;")
        def showEvent(self, e):
            super().showEvent(e)
            QTimer.singleShot(60, lambda: _aty_draw_knitted(self._p))

    knt_w = _KntWidget(right, self)
    knt_v = QVBoxLayout(knt_w); knt_v.setContentsMargins(0,0,0,0)
    try:
        self._aty_knitted_canvas = ATYKnittedCanvas(knt_w, rows=50)
        knt_v.addWidget(self._aty_knitted_canvas)
    except Exception as _e:
        lbl_e = QLabel(f"ATYKnittedCanvas not available: {_e}")
        lbl_e.setStyleSheet("color:#ff6060;padding:12px;")
        knt_v.addWidget(lbl_e)
        self._aty_knitted_canvas = None
    self._aty_sub_tabs.addTab(knt_w, "Knitted")

    rv.addWidget(self._aty_sub_tabs, 3)

    # ── Kennzahlen-Label ──────────────────────────────────────────────────
    self._aty_lbl_metrics = QLabel("")
    self._aty_lbl_metrics.setStyleSheet(
        "color:#fff;font-size:12px;font-weight:bold;font-family:monospace;"
        "background:#0d3333;padding:8px 12px;border-radius:6px;border:1px solid #0e8a8a;")
    self._aty_lbl_metrics.setWordWrap(True)
    rv.addWidget(self._aty_lbl_metrics)

    # ── Bin-Erklärung ─────────────────────────────────────────────────────
    lbl_bin_info = QLabel(
        "<b>Kurzhocker (Bin 1):</b> kurze, steile Dickstelle – das Garn ist auf "
        "wenigen Millimetern deutlich dicker als normal. Entsteht typischerweise "
        "durch Schlaufen oder Knoten im ATY-Prozess.  "
        "<b>Langwelle (Bin 2):</b> lange, flache Dickstelle – das Garn ist über "
        "a longer section slightly thicker. Typical for irregularities "
        "im Garnzug oder Luftdruck."
    )
    lbl_bin_info.setStyleSheet(
        "color:#999; font-size:10px; background:#181818;"
        "padding:5px 10px; border-radius:4px; border:1px solid #2a2a2a;")
    lbl_bin_info.setWordWrap(True)
    lbl_bin_info.setTextFormat(Qt.RichText)
    rv.addWidget(lbl_bin_info)

    # ── Steuerungs-Panel (Startpunkt / Linien / Gap / Farben) ─────────────
    ctrl = _aty_build_control_panel(self)
    rv.addWidget(ctrl)

    # ── Buttons ───────────────────────────────────────────────────────────
    brow = QHBoxLayout(); brow.setSpacing(8)
    self._aty_btn_analyze = QPushButton("Analysieren")
    self._aty_btn_analyze.setStyleSheet(
        "QPushButton{background:#0e5f5f;color:#fff;border-radius:4px;"
        "font-size:12px;padding:4px 12px;border:1px solid #0e8a8a;}"
        "QPushButton:hover{background:#0a4444;}"
        "QPushButton:disabled{background:#333;color:#666;}")
    self._aty_btn_analyze.setFixedHeight(30); self._aty_btn_analyze.setEnabled(False)
    self._aty_btn_analyze.clicked.connect(lambda: _aty_on_analyze(self))
    brow.addWidget(self._aty_btn_analyze)
    self._aty_btn_save = QPushButton("In DB speichern")
    self._aty_btn_save.setStyleSheet(
        "QPushButton{background:#2e7d32;color:#fff;border-radius:4px;"
        "font-size:12px;padding:4px 12px;border:none;}"
        "QPushButton:hover{background:#1b5e20;}"
        "QPushButton:disabled{background:#333;color:#666;}")
    self._aty_btn_save.setFixedHeight(30); self._aty_btn_save.setEnabled(False)
    self._aty_btn_save.clicked.connect(lambda: _aty_on_save(self))
    brow.addWidget(self._aty_btn_save)
    self._aty_btn_batch = QPushButton("Batch")
    self._aty_btn_batch.setFixedHeight(30)
    self._aty_btn_batch.setStyleSheet(
        "QPushButton{background:#1a3a5a;color:#8cf;border-radius:4px;"
        "font-size:12px;border:1px solid #2a5a8a;}"
        "QPushButton:hover{background:#2a4a6a;}")
    self._aty_btn_batch.clicked.connect(lambda: _aty_open_batch(self))
    brow.addWidget(self._aty_btn_batch)
    self._aty_lbl_status = QLabel("")
    self._aty_lbl_status.setStyleSheet("color:#aaa; font-size:11px;")
    brow.addWidget(self._aty_lbl_status, 1)
    rv.addLayout(brow)

    splitter.addWidget(right)
    splitter.setStretchFactor(0,0); splitter.setStretchFactor(1,1)
    splitter.setSizes([200, 900])
    root.addWidget(splitter, 1)
    self._aty_histograms: dict = {}
    self.tabs.addTab(self.tab_aty_yarnscope, "YarnScope ATY")


def _aty_build_control_panel(self):
    """Baut das Steuerungs-Panel mit Spinboxen und Farb-Editor.

    Spinboxen (immer sichtbar):
        Start [m], Zeilen (Garnspiegel), Gap, Bänder (Fabric), Reihen (Knitted)
        → «Anzeigen»-Button rendert alle Canvases neu

    Collapsible Farb-Panel:
        ATY-Bin-Farben (Bin1 orange, Bin2 blaugrün) per QColorDialog änderbar
        Checkboxen: Bin1 / Bin2 ein-/ausblenden
    """

    outer = QWidget()
    outer.setStyleSheet("background:#1a1a1a; border:1px solid #333; border-radius:4px;")
    ov = QVBoxLayout(outer); ov.setContentsMargins(6,4,6,4); ov.setSpacing(4)

    def _lbl(t):
        l = QLabel(t); l.setStyleSheet("color:#bbb;font-size:11px;"); return l

    # ── Steuerungs-Zeile ─────────────────────────────────────────────────
    row1 = QHBoxLayout(); row1.setSpacing(6)

    row1.addWidget(_lbl("Start [m]:"))
    self._aty_spin_start = QDoubleSpinBox()
    self._aty_spin_start.setRange(0.0,9999.0); self._aty_spin_start.setSingleStep(1.0)
    self._aty_spin_start.setDecimals(1); self._aty_spin_start.setValue(0.0)
    self._aty_spin_start.setFixedWidth(75)
    self._aty_spin_start.setStyleSheet("QDoubleSpinBox{background:#2a2a2a;color:#ddd;border:1px solid #444;padding:2px 4px;font-size:11px;}")
    row1.addWidget(self._aty_spin_start)

    row1.addWidget(_lbl("Zeilen:"))
    self._aty_spin_turns = QSpinBox()
    self._aty_spin_turns.setRange(1,20); self._aty_spin_turns.setValue(10)
    self._aty_spin_turns.setFixedWidth(50)
    self._aty_spin_turns.setStyleSheet("QSpinBox{background:#2a2a2a;color:#ddd;border:1px solid #444;padding:2px 4px;font-size:11px;}")
    row1.addWidget(self._aty_spin_turns)

    row1.addWidget(_lbl("Gap:"))
    self._aty_spin_gap = QDoubleSpinBox()
    self._aty_spin_gap.setRange(1.0,10.0); self._aty_spin_gap.setSingleStep(0.5)
    self._aty_spin_gap.setDecimals(1); self._aty_spin_gap.setValue(2.0)
    self._aty_spin_gap.setFixedWidth(60)
    self._aty_spin_gap.setStyleSheet("QDoubleSpinBox{background:#2a2a2a;color:#ddd;border:1px solid #444;padding:2px 4px;font-size:11px;}")
    row1.addWidget(self._aty_spin_gap)

    row1.addWidget(_lbl("Bands:"))
    self._aty_spin_bands = QSpinBox()
    self._aty_spin_bands.setRange(10,2500); self._aty_spin_bands.setValue(250)
    self._aty_spin_bands.setFixedWidth(65)
    self._aty_spin_bands.setStyleSheet("QSpinBox{background:#2a2a2a;color:#ddd;border:1px solid #444;padding:2px 4px;font-size:11px;}")
    row1.addWidget(self._aty_spin_bands)

    row1.addWidget(_lbl("Reihen:"))
    self._aty_spin_rows = QSpinBox()
    self._aty_spin_rows.setRange(10,250); self._aty_spin_rows.setValue(50)
    self._aty_spin_rows.setFixedWidth(60)
    self._aty_spin_rows.setStyleSheet("QSpinBox{background:#2a2a2a;color:#ddd;border:1px solid #444;padding:2px 4px;font-size:11px;}")
    row1.addWidget(self._aty_spin_rows)

    btn_show = QPushButton("Anzeigen")
    btn_show.setFixedHeight(26); btn_show.setFixedWidth(75)
    btn_show.setStyleSheet(
        "QPushButton{background:#0e5f5f;color:#fff;border-radius:3px;font-size:11px;border:1px solid #0e8a8a;}"
        "QPushButton:hover{background:#0a4444;}")
    btn_show.clicked.connect(lambda: _aty_refresh_visuals(self))
    row1.addWidget(btn_show)

    btn_colors = QPushButton("Farben / Sichtbarkeit ▼")
    btn_colors.setFixedHeight(26)
    btn_colors.setStyleSheet(
        "QPushButton{background:#2a2a2a;color:#aaa;border-radius:3px;font-size:11px;border:1px solid #444;}"
        "QPushButton:hover{background:#333;color:#ddd;}")
    btn_colors.setCheckable(True); btn_colors.setChecked(False)
    row1.addWidget(btn_colors)
    row1.addStretch()
    ov.addLayout(row1)

    # ── Collapsible Farb-Panel ────────────────────────────────────────────
    color_panel = QWidget(); color_panel.setVisible(False)
    cp_v = QVBoxLayout(color_panel); cp_v.setContentsMargins(0,4,0,0); cp_v.setSpacing(4)

    try:
        di_keys  = ["Di11","Di12","Di13","Di21","Di22","Di23","Di31","Di32","Di33"]
        due_keys = ["Dü11","Dü12","Dü13","Dü21","Dü22","Dü23","Dü31","Dü32","Dü33"]

        def _style_btn(btn, hexcol):
            """Färbt Button-Hintergrund mit der gewählten Farbe."""
            btn.setStyleSheet(
                f"QPushButton{{background:{hexcol};border:1px solid #888;"
                f"border-radius:2px;min-width:38px;height:20px;}}")
            btn.setToolTip(hexcol)

        def _make_color_btn(family, key):
            """Erstellt Farbbutton der QColorDialog öffnet."""
            hexcol = (COLOR_STATE.di_colors if family=="Di"
                      else COLOR_STATE.due_colors).get(key, "#ffffff")
            btn = QPushButton()
            btn.setFixedSize(40, 22)
            _style_btn(btn, hexcol)
            def _pick(_, fam=family, k=key, b=btn):
                cur = (COLOR_STATE.di_colors if fam=="Di"
                       else COLOR_STATE.due_colors).get(k, "#ffffff")
                col = QColorDialog.getColor(QColor(cur), outer, f"Farbe – {k}")
                if col.isValid():
                    COLOR_STATE.set_color(fam, k, col.name())
                    _style_btn(b, col.name())
                    _aty_invalidate_spans(self)
                    _aty_refresh_visuals(self)
            btn.clicked.connect(_pick)
            return btn

        # ── Sichtbarkeit ──────────────────────────────────────────────────
        vis_box = QGroupBox("Sichtbarkeit (Di/Dü ein-/ausschalten)")
        vis_box.setStyleSheet(
            "QGroupBox{color:#aaa;font-size:11px;border:1px solid #444;"
            "border-radius:3px;margin-top:4px;}"
            "QGroupBox::title{subcontrol-origin:margin;left:6px;}")
        vg = QGridLayout(vis_box); vg.setSpacing(3)
        lbl_di = QLabel("Dick:"); lbl_di.setStyleSheet("color:#ffaaaa;font-size:10px;")
        vg.addWidget(lbl_di, 0, 0)
        lbl_du = QLabel("Dünn:"); lbl_du.setStyleSheet("color:#aaaaff;font-size:10px;")
        vg.addWidget(lbl_du, 1, 0)
        for i, k in enumerate(di_keys):
            chk = QCheckBox(k)
            chk.setChecked(VISIBILITY_STATE.is_enabled(k))
            chk.setStyleSheet("color:#ddd;font-size:10px;")
            chk.toggled.connect(lambda on, kk=k: (
                VISIBILITY_STATE.set_enabled(kk, on),
                _aty_invalidate_spans(self),
                _aty_refresh_visuals(self)))
            vg.addWidget(chk, 0, i+1)
        for i, k in enumerate(due_keys):
            chk = QCheckBox(k)
            chk.setChecked(VISIBILITY_STATE.is_enabled(k))
            chk.setStyleSheet("color:#ddd;font-size:10px;")
            chk.toggled.connect(lambda on, kk=k: (
                VISIBILITY_STATE.set_enabled(kk, on),
                _aty_invalidate_spans(self),
                _aty_refresh_visuals(self)))
            vg.addWidget(chk, 1, i+1)
        cp_v.addWidget(vis_box)

        # ── Farben ────────────────────────────────────────────────────────
        col_box = QGroupBox("Colours (click on colour field to change)")
        col_box.setStyleSheet(
            "QGroupBox{color:#aaa;font-size:11px;border:1px solid #444;"
            "border-radius:3px;margin-top:4px;}"
            "QGroupBox::title{subcontrol-origin:margin;left:6px;}")
        cg = QGridLayout(col_box); cg.setSpacing(3)

        # Di-Zeile
        cg.addWidget(QLabel("Di:"), 0, 0)
        for i, k in enumerate(di_keys):
            lbl = QLabel(k); lbl.setStyleSheet("color:#ccc;font-size:9px;")
            cg.addWidget(lbl, 0, 1 + i*2)
            cg.addWidget(_make_color_btn("Di", k), 0, 2 + i*2)

        # Dü-Zeile
        cg.addWidget(QLabel("Dü:"), 1, 0)
        for i, k in enumerate(due_keys):
            lbl = QLabel(k); lbl.setStyleSheet("color:#ccc;font-size:9px;")
            cg.addWidget(lbl, 1, 1 + i*2)
            cg.addWidget(_make_color_btn("Dü", k), 1, 2 + i*2)

        # Reset-Button
        btn_reset = QPushButton("Standardfarben")
        btn_reset.setFixedHeight(24)
        btn_reset.setStyleSheet(
            "QPushButton{background:#333;color:#aaa;border:1px solid #555;"
            "border-radius:3px;font-size:11px;}"
            "QPushButton:hover{background:#444;color:#fff;}")
        btn_reset.clicked.connect(lambda: (
            COLOR_STATE.reset_colors(),
            _aty_invalidate_spans(self),
            _aty_refresh_visuals(self)))
        cg.addWidget(btn_reset, 2, 0, 1, 4)
        cp_v.addWidget(col_box)

    except Exception as _e:
        traceback.print_exc()
        cp_v.addWidget(QLabel(f"Colour editor not available: {_e}"))

    ov.addWidget(color_panel)
    btn_colors.toggled.connect(lambda on: (
        color_panel.setVisible(on),
        btn_colors.setText("Farben / Sichtbarkeit ▲" if on else "Farben / Sichtbarkeit ▼"),
    ))
    return outer


def _aty_invalidate_spans(self):
    """Löscht gecachte Spans damit sie mit neuen Farben neu berechnet werden."""
    tid = getattr(self, "_aty_current_trial_id", None)
    if tid is None or tid not in self._aty_cache:
        return
    entry = list(self._aty_cache[tid])
    if len(entry) > 5: entry[5] = None
    if len(entry) > 6: entry[6] = None
    self._aty_cache[tid] = tuple(entry)


# ---------------------------------------------------------------------------
# Trial-Liste
# ---------------------------------------------------------------------------

def _aty_populate_trial_list(self):
    if self._aty_trial_list is None:
        return
    self._aty_trial_list.blockSignals(True)
    self._aty_trial_list.clear()
    sid = self._series_pk
    for t in self._trials:
        tl = {k.lower(): v for k, v in t.items()}
        tid = tl.get("id")
        vno = int(tl.get("versuchsnummer") or 0)
        tdms = _aty_find_tdms(sid, vno) if sid else None
        db_ok = False
        try:
            rows = fetch_all("SELECT 1 FROM tblLaborATYoMat WHERE TrialID=? AND Timestamp IS NOT NULL",(tid,))
            db_ok = bool(rows)
        except Exception:
            pass
        icon   = "📄" if tdms else "—"
        status = "✅" if db_ok else ("⏳" if tdms else "")
        item   = QListWidgetItem(f"{icon} V{vno:03d}  {status}")
        item.setData(Qt.UserRole, {"trial_id": tid, "vno": vno, "tdms": tdms})
        if not tdms:
            item.setForeground(QColor("#555"))
        self._aty_trial_list.addItem(item)
    self._aty_trial_list.blockSignals(False)


# ---------------------------------------------------------------------------
# Trial-Auswahl
# ---------------------------------------------------------------------------

def _aty_on_trial_selected(self, row: int):
    if self._aty_trial_list is None or row < 0:
        return
    item = self._aty_trial_list.item(row)
    if not item:
        return
    data = item.data(Qt.UserRole)
    tdms = data.get("tdms"); tid = data.get("trial_id"); vno = data.get("vno")
    self._aty_current_trial_id = tid
    self._aty_current_tdms     = tdms
    if tdms:
        self._aty_lbl_file.setText(f"📄 {tdms.name}")
        self._aty_btn_analyze.setEnabled(True)
    else:
        self._aty_lbl_file.setText(f"V{vno} – kein TDMS-File")
        self._aty_btn_analyze.setEnabled(False)
    if tid is not None and tid in self._aty_cache:
        entry = self._aty_cache[tid]
        self._aty_histograms = entry[1]
        self._aty_btn_save.setEnabled(True)
        self._aty_lbl_status.setText("Aus Cache.")
        _aty_update_metrics(self, entry[0])
        _aty_redraw_histogram(self)
        _aty_draw_garnspiegel(self)
        _aty_draw_fabric(self)
        _aty_draw_knitted(self)
    else:
        self._aty_btn_save.setEnabled(False)
        self._aty_lbl_status.setText("")
        self._aty_lbl_metrics.setText("")
        self._aty_histograms = {}


# ---------------------------------------------------------------------------
# Analyse – synchron im UI-Thread (wie YarnScope)
# ---------------------------------------------------------------------------

def _aty_on_analyze(self):
    """Synchrone ATY-Analyse – exakt wie YarnScope garngraf.py."""
    tdms = getattr(self, "_aty_current_tdms", None)
    if not tdms:
        return
    tid = self._aty_current_trial_id
    if tid is not None and tid in self._aty_cache:
        entry = self._aty_cache[tid]
        self._aty_histograms = entry[1]
        self._aty_btn_save.setEnabled(True)
        self._aty_lbl_status.setText("Aus Cache.")
        _aty_update_metrics(self, entry[0])
        _aty_redraw_histogram(self)
        _aty_draw_garnspiegel(self)
        _aty_draw_fabric(self)
        _aty_draw_knitted(self)
        return

    self._aty_btn_analyze.setEnabled(False)
    self._aty_btn_save.setEnabled(False)
    self._aty_lbl_status.setText("Lese TDMS…")
    QApplication.processEvents()

    try:
        y     = read_first_numeric_channel(str(tdms))
        mm_pp = float(read_step_mm_from_tdms(str(tdms)) or 0.25)
        if y is None or len(y) == 0:
            self._aty_lbl_status.setText("Fehler: Kein Signal.")
            return
        arr = np.asarray(y, dtype=float)
        if float(np.median(arr)) >= 10.0:
            arr = arr / 1000.0

        self._aty_lbl_status.setText("Analysiere Dickstellen…")
        QApplication.processEvents()

        spots    = detect_thick_spots(arr, mm_pp)
        total_mm = float(len(arr) * mm_pp)
        db_vals  = compute_db_values(spots, total_mm)
        hists    = compute_histograms(spots, total_mm)

        # Fabric/Knitted-Spans einmalig berechnen und cachen
        self._aty_lbl_status.setText("Berechne Fabric-Spans…")
        QApplication.processEvents()
        try:
            fab_result = _aty_compute_fabric_spans(arr, mm_pp, 250, bin_colors={1: getattr(self, '_aty_bin1_color', '#ffcc88'), 2: getattr(self, '_aty_bin2_color', '#88dddd')}, bin_visible={1: getattr(self, '_aty_bin1_visible', True), 2: getattr(self, '_aty_bin2_visible', True)})
            fab_spans  = fab_result[0] if isinstance(fab_result, tuple) else fab_result
            knt_spans  = _aty_compute_knitted_spans(arr, mm_pp, 50, bin_colors={1: getattr(self, '_aty_bin1_color', '#ffcc88'), 2: getattr(self, '_aty_bin2_color', '#88dddd')}, bin_visible={1: getattr(self, '_aty_bin1_visible', True), 2: getattr(self, '_aty_bin2_visible', True)})
        except Exception:
            traceback.print_exc()
            fab_spans = []; knt_spans = []
        # Cache: (db_vals, hists, arr, spots, mm_pp, fab_spans, knt_spans)
        if tid is not None:
            self._aty_cache[tid] = (db_vals, hists, arr, spots, mm_pp, fab_spans, knt_spans)

        self._aty_histograms = hists
        self._aty_btn_save.setEnabled(tid is not None)
        self._aty_lbl_status.setText("Fertig.")
        _aty_update_metrics(self, db_vals)
        _aty_redraw_histogram(self)
        _aty_draw_garnspiegel(self)
        _aty_draw_fabric(self)
        _aty_draw_knitted(self)

    except Exception as e:
        traceback.print_exc()
        self._aty_lbl_status.setText(f"Fehler: {e}")
    finally:
        self._aty_btn_analyze.setEnabled(True)


# ---------------------------------------------------------------------------
# Visuellen Inhalt neu rendern (nach Parameteränderung)
# ---------------------------------------------------------------------------

def _aty_refresh_visuals(self):
    """Garnspiegel + Fabric + Knitted neu zeichnen."""
    _aty_draw_garnspiegel(self)
    _aty_draw_fabric(self)
    _aty_draw_knitted(self)


# ---------------------------------------------------------------------------
# Hilfsfunktion: Fenster aus Gesamt-Array ausschneiden
# ---------------------------------------------------------------------------

def _aty_get_window(self):
    """Gibt (arr_view, spots_view, mm_pp, row_spacing_ref) zurück.

    Schneidet ab Startpunkt ein Fenster von num_turns×200mm aus.
    Passt Spot-Indizes auf das Fenster an.
    row_spacing_ref = globaler Max des Gesamt-Arrays (stabile Bandbreite).
    Gibt (None,...) zurück wenn kein Cache-Eintrag vorhanden.
    """
    tid = getattr(self, "_aty_current_trial_id", None)
    if tid is None or tid not in self._aty_cache:
        return None, [], 0.25, 1.0
    entry  = self._aty_cache[tid]
    arr    = entry[2]; spots = entry[3]; mm_pp = float(entry[4])

    try:   start_m = float(self._aty_spin_start.value())
    except: start_m = 0.0
    try:   num_turns = int(self._aty_spin_turns.value())
    except: num_turns = 10

    start_idx = max(0, min(int(start_m * 1000.0 / mm_pp), len(arr)-1))
    needed    = int(num_turns * 200.0 / mm_pp)
    arr_view  = arr[start_idx : start_idx + needed]
    if len(arr_view) == 0:
        return None, [], mm_pp, float(np.max(arr))

    spots_view = []
    for sp in (spots or []):
        s = int(sp["start_idx"]) - start_idx
        e = s + int(sp["n_pts"])
        if e <= 0 or s >= len(arr_view):
            continue
        sp2 = dict(sp)
        sp2["start_idx"] = max(0, s)
        sp2["n_pts"]     = min(e, len(arr_view)) - sp2["start_idx"]
        if sp2["n_pts"] > 0:
            spots_view.append(sp2)

    row_spacing_ref = float(np.max(arr))
    return arr_view, spots_view, mm_pp, row_spacing_ref


# ---------------------------------------------------------------------------
# Garnspiegel zeichnen (mit Di/Dü-Farbcodierung via plot_garnspiegel)
# ---------------------------------------------------------------------------

def _aty_draw_garnspiegel(self):
    """Zeichnet ATY-Garnspiegel mit Di/Dü-Farbcodierung.

    Verwendet GarnCanvas.plot_garnspiegel – identisch zu YarnScope.
    Liest Farben und Sichtbarkeit direkt aus COLOR_STATE / VISIBILITY_STATE
    (garngraf_canvas.py), die via den Farb-Editor live geändert werden können.
    """
    canvas = getattr(self, "_aty_garn_canvas", None)
    if canvas is None:
        return
    arr_view, _, mm_pp, row_spacing_ref = _aty_get_window(self)
    if arr_view is None or len(arr_view) == 0:
        return
    try:
        try:   gap   = float(self._aty_spin_gap.value())
        except: gap  = 2.0
        try:   turns = int(self._aty_spin_turns.value())
        except: turns = 10

        canvas.plot_garnspiegel(
            arr_view,
            gap_factor=gap,
            show_colors=True,
            row_spacing_ref=row_spacing_ref,
            num_turns=turns,
        )
        canvas.draw()
    except Exception:
        traceback.print_exc()


# ---------------------------------------------------------------------------
# Fabric zeichnen
# ---------------------------------------------------------------------------



def _aty_compute_fabric_spans(arr, mm_pp, n_bands, bin_colors=None, bin_visible=None):
    """Berechnet Di/Dü-Farbspans für n_bands Fabric-Bänder.

    Segment-Länge wird dynamisch berechnet: seg_mm = total_mm / n_bands.
    Damit füllen die n_bands Bänder immer das gesamte Garn ohne Leerraum.
    Klassifikation identisch zu GarnCanvas.plot_garnspiegel:
    CLASS_THRESHOLDS, COLOR_STATE, VISIBILITY_STATE aus garngraf_canvas.py.
    """
    arr      = np.asarray(arr, dtype=float)
    total_mm = float(len(arr)) * mm_pp
    seg_mm   = total_mm / max(1, n_bands)      # dynamisch – füllt ganzen Bildschirm
    pts_seg  = max(1, int(round(seg_mm / mm_pp)))
    actual   = min(n_bands, len(arr) // pts_seg)
    if actual == 0:
        return [[] for _ in range(n_bands)], seg_mm

    mean_all = float(np.mean(arr[:actual * pts_seg]))
    mm_step  = seg_mm / pts_seg

    di_pct  = CLASS_THRESHOLDS["Di"]["pct"]
    due_pct = CLASS_THRESHOLDS["Dü"]["pct"]
    di_len  = CLASS_THRESHOLDS["Di"]["mm"]
    due_len = CLASS_THRESHOLDS["Dü"]["mm"]
    need1_di  = max(1, int((di_len[0]  + 1e-9) / mm_step))
    need2_di  = max(1, int((di_len[1]  + 1e-9) / mm_step))
    need3_di  = max(1, int((di_len[2]  + 1e-9) / mm_step))
    need1_due = max(1, int((due_len[0] + 1e-9) / mm_step))
    need2_due = max(1, int((due_len[1] + 1e-9) / mm_step))
    need3_due = max(1, int((due_len[2] + 1e-9) / mm_step))

    def _runs_np(mask):
        """Vektorisierte Run-Erkennung via np.diff."""
        if not mask.any():
            return np.empty(0, int), np.empty(0, int)
        padded = np.concatenate(([0], mask.view(np.uint8), [0]))
        diff   = np.diff(padded)
        return np.where(diff == 1)[0], (np.where(diff == -1)[0] - 1)

    x_mm = np.linspace(0.0, seg_mm, pts_seg, endpoint=False)
    spans_per_band = []

    for b in range(actual):
        seg    = np.asarray(arr[b*pts_seg:(b+1)*pts_seg], dtype=float)
        spans  = []

        # Dickstellen
        b1 = (seg >= (1.0+di_pct[0]/100.0)*mean_all) & (seg < (1.0+di_pct[1]/100.0)*mean_all)
        b2 = (seg >= (1.0+di_pct[1]/100.0)*mean_all) & (seg < (1.0+di_pct[2]/100.0)*mean_all)
        b3 = (seg >= (1.0+di_pct[2]/100.0)*mean_all)
        for mask, row in ((b1,'1'),(b2,'2'),(b3,'3')):
            ss, ee = _runs_np(mask)
            for s, e in zip(ss, ee):
                L = int(e)-int(s)+1
                if L < need1_di: continue
                col   = '1' if L < need2_di else '2' if L < need3_di else '3'
                key   = f"Di{row}{col}"
                if not VISIBILITY_STATE.is_enabled(key): continue
                color = COLOR_STATE.di_colors.get(key, DI_COLORS.get(key,"#ff0000"))
                spans.append((float(x_mm[s]), float(x_mm[min(int(e),pts_seg-1)]+mm_step), color))

        # Dünnstellen
        t1 = (seg <= (1.0-due_pct[0]/100.0)*mean_all) & (seg > (1.0-due_pct[1]/100.0)*mean_all)
        t2 = (seg <= (1.0-due_pct[1]/100.0)*mean_all) & (seg > (1.0-due_pct[2]/100.0)*mean_all)
        t3 = (seg <= (1.0-due_pct[2]/100.0)*mean_all)
        for mask, row in ((t1,'1'),(t2,'2'),(t3,'3')):
            ss, ee = _runs_np(mask)
            for s, e in zip(ss, ee):
                L = int(e)-int(s)+1
                if L < need1_due: continue
                col   = '1' if L < need2_due else '2' if L < need3_due else '3'
                key   = f"Dü{row}{col}"
                if not VISIBILITY_STATE.is_enabled(key): continue
                color = COLOR_STATE.due_colors.get(key, DUE_COLORS.get(key,"#0000ff"))
                spans.append((float(x_mm[s]), float(x_mm[min(int(e),pts_seg-1)]+mm_step), color))

        spans_per_band.append(spans)

    while len(spans_per_band) < n_bands:
        spans_per_band.append([])
    return spans_per_band, seg_mm


def _aty_compute_knitted_spans(arr, mm_pp, n_rows, row_len_mm=400.0, bin_colors=None, bin_visible=None):
    """Berechnet Di/Dü-Farbspans für n_rows Knitted-Reihen.

    Jede Reihe = row_len_mm (Standard 400mm) des Garns, fortlaufend.
    x-Koordinaten werden auf 0..200mm skaliert (Canvas-Darstellungsfenster).
    Klassifikation identisch zu _aty_compute_fabric_spans.
    """
    arr      = np.asarray(arr, dtype=float)
    pts_row  = max(1, int(round(row_len_mm / mm_pp)))
    actual   = min(n_rows, len(arr) // pts_row)
    if actual == 0:
        return [[] for _ in range(n_rows)]

    mean_all  = float(np.mean(arr[:actual * pts_row]))
    mm_step   = row_len_mm / pts_row
    display_mm = 200.0
    scale     = display_mm / row_len_mm   # Skalierung auf Canvas-X-Achse

    di_pct  = CLASS_THRESHOLDS["Di"]["pct"]
    due_pct = CLASS_THRESHOLDS["Dü"]["pct"]
    di_len  = CLASS_THRESHOLDS["Di"]["mm"]
    due_len = CLASS_THRESHOLDS["Dü"]["mm"]
    need1_di  = max(1, int((di_len[0]  + 1e-9) / mm_step))
    need2_di  = max(1, int((di_len[1]  + 1e-9) / mm_step))
    need3_di  = max(1, int((di_len[2]  + 1e-9) / mm_step))
    need1_due = max(1, int((due_len[0] + 1e-9) / mm_step))
    need2_due = max(1, int((due_len[1] + 1e-9) / mm_step))
    need3_due = max(1, int((due_len[2] + 1e-9) / mm_step))

    def _runs_np(mask):
        if not mask.any():
            return np.empty(0, int), np.empty(0, int)
        padded = np.concatenate(([0], mask.view(np.uint8), [0]))
        diff   = np.diff(padded)
        return np.where(diff == 1)[0], (np.where(diff == -1)[0] - 1)

    x_mm = np.linspace(0.0, row_len_mm, pts_row, endpoint=False)
    spans_per_row = []

    for r in range(actual):
        seg   = np.asarray(arr[r*pts_row:(r+1)*pts_row], dtype=float)
        spans = []

        b1 = (seg >= (1.0+di_pct[0]/100.0)*mean_all) & (seg < (1.0+di_pct[1]/100.0)*mean_all)
        b2 = (seg >= (1.0+di_pct[1]/100.0)*mean_all) & (seg < (1.0+di_pct[2]/100.0)*mean_all)
        b3 = (seg >= (1.0+di_pct[2]/100.0)*mean_all)
        for mask, row in ((b1,'1'),(b2,'2'),(b3,'3')):
            ss, ee = _runs_np(mask)
            for s, e in zip(ss, ee):
                L = int(e)-int(s)+1
                if L < need1_di: continue
                col   = '1' if L < need2_di else '2' if L < need3_di else '3'
                key   = f"Di{row}{col}"
                if not VISIBILITY_STATE.is_enabled(key): continue
                color = COLOR_STATE.di_colors.get(key, DI_COLORS.get(key,"#ff0000"))
                spans.append((float(x_mm[s])*scale, float(x_mm[min(int(e),pts_row-1)]+mm_step)*scale, color))

        t1 = (seg <= (1.0-due_pct[0]/100.0)*mean_all) & (seg > (1.0-due_pct[1]/100.0)*mean_all)
        t2 = (seg <= (1.0-due_pct[1]/100.0)*mean_all) & (seg > (1.0-due_pct[2]/100.0)*mean_all)
        t3 = (seg <= (1.0-due_pct[2]/100.0)*mean_all)
        for mask, row in ((t1,'1'),(t2,'2'),(t3,'3')):
            ss, ee = _runs_np(mask)
            for s, e in zip(ss, ee):
                L = int(e)-int(s)+1
                if L < need1_due: continue
                col   = '1' if L < need2_due else '2' if L < need3_due else '3'
                key   = f"Dü{row}{col}"
                if not VISIBILITY_STATE.is_enabled(key): continue
                color = COLOR_STATE.due_colors.get(key, DUE_COLORS.get(key,"#0000ff"))
                spans.append((float(x_mm[s])*scale, float(x_mm[min(int(e),pts_row-1)]+mm_step)*scale, color))

        spans_per_row.append(spans)

    while len(spans_per_row) < n_rows:
        spans_per_row.append([])
    return spans_per_row


def _aty_draw_fabric(self):
    """Zeichnet Fabric-Canvas mit ATY-Bin-Farbcodierung.

    Segment-Länge = total_mm / n_bands → füllt den ganzen Bildschirm.
    Bin 1 (Kurzhocker) = orange #ffcc88, Bin 2 (Langwelle) = blaugrün #88dddd.
    Spans werden aus Cache geladen (beim Analyze berechnet).
    Bei «Anzeigen» (anderes n_bands): wird neu berechnet.
    """
    canvas = getattr(self, "_aty_fabric_canvas", None)
    if canvas is None:
        return
    tid = getattr(self, "_aty_current_trial_id", None)
    if tid is None or tid not in self._aty_cache:
        return
    entry = self._aty_cache[tid]
    if len(entry) < 5:
        return
    arr = entry[2]; mm_pp = float(entry[4])
    if arr is None or len(arr) == 0:
        return
    try:
        try:   n_bands = int(self._aty_spin_bands.value())
        except: n_bands = 250

        # Gecachte Spans (250 Bänder) – falls n_bands != 250: neu berechnen
        fab_spans_cached = entry[5] if len(entry) > 5 else None
        if fab_spans_cached and len(fab_spans_cached) == n_bands:
            spans  = fab_spans_cached
            seg_mm = float(len(arr)) * mm_pp / n_bands
        else:
            result = _aty_compute_fabric_spans(arr, mm_pp, n_bands, bin_colors={1: getattr(self, '_aty_bin1_color', '#ffcc88'), 2: getattr(self, '_aty_bin2_color', '#88dddd')}, bin_visible={1: getattr(self, '_aty_bin1_visible', True), 2: getattr(self, '_aty_bin2_visible', True)})
            spans  = result[0] if isinstance(result, tuple) else result
            seg_mm = result[1] if isinstance(result, tuple) else float(len(arr)) * mm_pp / n_bands
            # Cache aktualisieren
            new_entry = list(entry)
            while len(new_entry) < 7: new_entry.append(None)
            new_entry[5] = spans
            self._aty_cache[tid] = tuple(new_entry)

        # x_range_mm = 0..seg_mm (jedes Band ist seg_mm lang)
        canvas.set_color_spans(spans, x_range_mm=(0.0, seg_mm))
    except Exception:
        traceback.print_exc()


# ---------------------------------------------------------------------------
# Kennzahlen-Label
# ---------------------------------------------------------------------------

def _aty_update_metrics(self, db_vals: dict):
    def _f(k, dec=1):
        v = db_vals.get(k)
        try:
            vv = float(v)
            return f"{vv:,.{dec}f}".replace(",","'") if math.isfinite(vv) else "-"
        except: return "-"
    l1 = f"Laenge: {_f('TotalLen_m')} m  |  Kurzhocker: {_f('N_B1')} /100m  |  Langwelle: {_f('N_B2')} /100m"
    l2 = f"Ø Len B1: {_f('AvgLen_B1',2)} mm  |  Ø Len B2: {_f('AvgLen_B2',2)} mm  |  Ø Hgt B1: {_f('AvgHeight_B1',1)} um  |  Ø Hgt B2: {_f('AvgHeight_B2',1)} um"
    try: self._aty_lbl_metrics.setText(l1 + "\n" + l2)
    except: pass


# ---------------------------------------------------------------------------
# Histogramm
# ---------------------------------------------------------------------------

def _aty_redraw_histogram(self):
    hists = getattr(self, "_aty_histograms", {})
    if not hists: return
    fk    = self._aty_feature_combo.currentData()
    label = self._aty_feature_combo.currentText()
    if fk not in hists: return
    h      = hists[fk]
    edges  = np.asarray(h["edges"])
    c1     = np.asarray(h["counts_1"])
    c2     = np.asarray(h["counts_2"])
    width  = (edges[1]-edges[0])*0.42
    centers = 0.5*(edges[:-1]+edges[1:])
    ax = self._aty_hist_ax
    ax.clear(); ax.set_facecolor("#1e1e1e"); ax.figure.patch.set_facecolor("#1e1e1e")
    ax.bar(centers-width/2, c1, width=width, color="#e07b00", alpha=0.85, label="Bin 1 – Kurzhocker")
    ax.bar(centers+width/2, c2, width=width, color="#0e8a8a", alpha=0.85, label="Bin 2 – Langwelle")
    ax.set_xlabel(label, color="#aaa", fontsize=7)
    ax.set_ylabel("Anzahl / 100 m", color="#aaa", fontsize=7)
    ax.set_title(f"Verteilung: {label}", color="#ccc", fontsize=8)
    ax.tick_params(colors="#888", labelsize=6)
    for sp in ax.spines.values(): sp.set_color("#444")
    ax.legend(fontsize=6, framealpha=0.5, facecolor="#222", edgecolor="#555", labelcolor="#ddd")
    self._aty_hist_canvas.draw_idle()
    def _fmt(v):
        try:
            vv=float(v)
            if not np.isfinite(vv): return "-"
            if abs(vv)>=10000: return f"{vv:,.0f}".replace(",","'")
            elif abs(vv)>=100: return f"{vv:.1f}"
            elif abs(vv)>=1:   return f"{vv:.2f}"
            else:              return f"{vv:.4f}"
        except: return "-"
    tbl = self._aty_hist_table
    tbl.blockSignals(True)
    try:
        for i in range(20):
            lo,hi = float(edges[i]),float(edges[i+1])
            it0 = QTableWidgetItem(f"{_fmt(lo)} – {_fmt(hi)}"); it0.setTextAlignment(Qt.AlignCenter); tbl.setItem(i,0,it0)
            it1 = QTableWidgetItem(_fmt(c1[i])); it1.setTextAlignment(Qt.AlignCenter); it1.setBackground(QColor("#2a1a00")); tbl.setItem(i,1,it1)
            it2 = QTableWidgetItem(_fmt(c2[i])); it2.setTextAlignment(Qt.AlignCenter); it2.setBackground(QColor("#001a1a")); tbl.setItem(i,2,it2)
    finally:
        tbl.blockSignals(False)


# ---------------------------------------------------------------------------
# Speichern / Batch
# ---------------------------------------------------------------------------

def _aty_on_save(self):
    tid  = getattr(self,"_aty_current_trial_id",None)
    tdms = getattr(self,"_aty_current_tdms",None)
    if tid is None or tid not in self._aty_cache: return
    db_vals = self._aty_cache[tid][0]
    try:
        from ui.screen_aty_batch import _save_aty_to_db  # noqa: lazy import OK here
        ok = _save_aty_to_db(tid, db_vals, tdms)
        if ok:
            self._aty_lbl_status.setText("Gespeichert.")
            self._aty_btn_save.setEnabled(False)
            _aty_populate_trial_list(self)
        else:
            self._aty_lbl_status.setText("Speichern fehlgeschlagen.")
    except Exception as e:
        self._aty_lbl_status.setText(f"Fehler: {e}")

def _aty_open_batch(self):
    try:
        from ui.screen_aty_batch import ATYBatchScreen
        sid=self._series_pk; sname=""
        try: sname=self.lbl_small_title.text() if hasattr(self,"lbl_small_title") else ""
        except: pass
        mw=self.window()
        if not hasattr(mw,"aty_batch") or mw.aty_batch is None:
            mw.aty_batch=ATYBatchScreen(on_back_home=lambda: mw.stack.setCurrentWidget(self),locked_series_id=sid,locked_series_name=sname)
            mw.stack.addWidget(mw.aty_batch)
        else:
            mw.aty_batch._locked_series_id=sid; mw.aty_batch._locked_series_name=sname
            mw.aty_batch._insider_mode=False; mw.aty_batch._on_back_home=lambda: mw.stack.setCurrentWidget(self)
        mw.setWindowTitle("TrippleT – YarnScope ATY Batch")
        mw.stack.setCurrentWidget(mw.aty_batch)
        QTimer.singleShot(50, mw.aty_batch._init_series_state)
    except Exception as e:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "ATY Batch", f"Fehler: {e}")


# ---------------------------------------------------------------------------
# Knitted zeichnen
# ---------------------------------------------------------------------------

def _aty_draw_knitted(self):
    """Zeichnet Knitted-Canvas mit ATY-Bin-Farbcodierung.

    Jede Reihe = 400mm (row_len_mm) des Garns, fortlaufend.
    x_range_mm=0..200 entspricht dem Darstellungsfenster.
    """
    canvas = getattr(self, "_aty_knitted_canvas", None)
    if canvas is None:
        return
    tid = getattr(self, "_aty_current_trial_id", None)
    if tid is None or tid not in self._aty_cache:
        return
    entry = self._aty_cache[tid]
    if len(entry) < 5:
        return
    arr = entry[2]; mm_pp = float(entry[4])
    if arr is None or len(arr) == 0:
        return
    try:
        try:   n_rows = int(self._aty_spin_rows.value())
        except: n_rows = 50

        # Gecachte Knitted-Spans – falls n_rows != 50: neu berechnen
        knt_spans_cached = entry[6] if len(entry) > 6 else None
        if knt_spans_cached and len(knt_spans_cached) == n_rows:
            spans = knt_spans_cached
        else:
            spans = _aty_compute_knitted_spans(arr, mm_pp, n_rows, bin_colors={1: getattr(self, '_aty_bin1_color', '#ffcc88'), 2: getattr(self, '_aty_bin2_color', '#88dddd')}, bin_visible={1: getattr(self, '_aty_bin1_visible', True), 2: getattr(self, '_aty_bin2_visible', True)})
            new_entry = list(entry)
            while len(new_entry) < 8: new_entry.append(None)
            new_entry[6] = spans
            self._aty_cache[tid] = tuple(new_entry)

        canvas.set_row_count(n_rows)
        canvas.set_color_spans(spans, x_range_mm=(0.0, 200.0), row_len_mm=400.0)
    except Exception:
        traceback.print_exc()


# ---------------------------------------------------------------------------
# Registrierung auf ShowExperimentScreen
# ---------------------------------------------------------------------------
# Patching erfolgt direkt in screen_show_experiment.py (Top-Level-Import).
# Diese Datei stellt nur die Funktionen bereit.