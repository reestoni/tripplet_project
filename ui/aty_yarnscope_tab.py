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

from db.connection import fetch_all, table_exists
from ui.yarnscope.garngraf_canvas import (
    GarnCanvas, CLASS_THRESHOLDS, COLOR_STATE, VISIBILITY_STATE,
    DI_COLORS, DUE_COLORS,
)
from ui.yarnscope.aty_canvas import ATYFabricCanvas, ATYKnittedCanvas
from ui.yarnscope.dty_tdms_reader import (
    read_step_mm_from_tdms, read_aty_signal,
)
from ui.yarnscope.thick_spot_analysis import (
    detect_thick_spots, compute_db_values,
    aggregate_per_100m, compute_histograms,
)
from ui.yarnscope.aty_core_analysis import (
    analyze_trial as _aty_analyze_trial_core,
    get_zoom_segment as _aty_get_zoom_segment,
    compute_radar_scores as _aty_compute_radar_scores,
    describe_yarn as _aty_describe_yarn,
    to_db_row as _aty_to_db_row,
    RADAR_AXES as _ATY_RADAR_AXES,
    RADAR_LABELS as _ATY_RADAR_LABELS,
)
from ui.theme import get_accent, CARD_BG, LIGHT_BG, TEXT

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
    timer = getattr(self, "_aty_auto_timer", None)
    if timer is not None:
        timer.stop()
    self._aty_auto_timer = None
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
    # Multi-select (Ctrl/Shift-click) in addition to the existing
    # currentRowChanged handler above, used only by the "Compare" sub-tab --
    # does not change the existing single-trial flow.
    self._aty_trial_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
    self._aty_trial_list.itemSelectionChanged.connect(
        lambda: _aty_on_compare_selection_changed(self))
    lv.addWidget(self._aty_trial_list, 1)
    splitter.addWidget(left)

    # Auto-refresh: analog zum DTY-YarnScope-Tab (siehe dty_yarnscope_tab.py)
    # - re-scannt den TDMS-Ordner nur, waehrend dieser Tab aktiv ist UND
    # mindestens ein Trial noch ohne File dasteht.
    self._aty_auto_timer = QTimer()
    self._aty_auto_timer.setInterval(20000)
    self._aty_auto_timer.timeout.connect(lambda: _aty_populate_trial_list(self))
    if not getattr(self, "_aty_tab_watch_connected", False):
        self.tabs.currentChanged.connect(lambda idx: _aty_update_auto_refresh_state(self))
        self._aty_tab_watch_connected = True

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

    # ── Sub-Tab 4: Compare (multi-select in the trial list) ────────────────
    # Light theme by design (instead of the dark YarnScope look of the other
    # sub-tabs) -- follows the card/KPI design from screen_nozzle_calculator.py
    # (_card/_kpi_widget).
    accent = get_accent()
    # The whole tab content sits inside a vertical QScrollArea: on a smaller
    # window the two tables + signal cards + histograms no longer fit without
    # squashing the charts' aspect ratio -- scrolling keeps everything at a
    # readable size instead.
    cmp_outer_scroll = QScrollArea()
    cmp_outer_scroll.setWidgetResizable(True)
    cmp_outer_scroll.setStyleSheet(f"QScrollArea{{background:{LIGHT_BG};border:none;}}")
    cmp_w = QWidget(); cmp_w.setStyleSheet(f"background:{LIGHT_BG};")
    cmp_v = QVBoxLayout(cmp_w); cmp_v.setContentsMargins(10,10,10,10); cmp_v.setSpacing(8)

    cmp_top = QHBoxLayout(); cmp_top.setSpacing(10)
    self._aty_cmp_btn_run = QPushButton("Run Comparison")
    self._aty_cmp_btn_run.setStyleSheet(
        f"QPushButton{{background:{accent};color:#fff;border-radius:3px;"
        f"font-size:12px;font-weight:600;padding:5px 14px;border:none;}}"
        f"QPushButton:hover{{background:{accent};}}"
        f"QPushButton:disabled{{background:#d0d0d0;color:#888;}}")
    self._aty_cmp_btn_run.setFixedHeight(28); self._aty_cmp_btn_run.setEnabled(False)
    self._aty_cmp_btn_run.clicked.connect(lambda: _aty_on_compare_run(self))
    cmp_top.addWidget(self._aty_cmp_btn_run)

    self._aty_cmp_btn_info = QPushButton("ⓘ How is this calculated?")
    self._aty_cmp_btn_info.setCheckable(True); self._aty_cmp_btn_info.setChecked(False)
    self._aty_cmp_btn_info.setFixedHeight(28)
    self._aty_cmp_btn_info.setStyleSheet(
        f"QPushButton{{background:{CARD_BG};color:#666;border:1px solid #dbe2dc;"
        f"border-radius:3px;font-size:11.5px;padding:5px 10px;}}"
        f"QPushButton:hover{{background:#f0f2f0;}}"
        f"QPushButton:checked{{background:#eef6ef;color:{accent};border-color:{accent};}}")
    cmp_top.addWidget(self._aty_cmp_btn_info)

    self._aty_cmp_lbl_status = QLabel(
        "No trials selected (Ctrl/Shift-click for multi-select in the list on the left).")
    self._aty_cmp_lbl_status.setStyleSheet(f"color:{TEXT}; font-size:11.5px;")
    cmp_top.addWidget(self._aty_cmp_lbl_status, 1)
    cmp_v.addLayout(cmp_top)

    # ── Collapsible methodology panel (hidden by default) ──────────────────
    self._aty_cmp_info_panel = QFrame()
    self._aty_cmp_info_panel.setStyleSheet(
        f"QFrame{{background:#f4f8f5;border:1px solid #dbe2dc;border-radius:3px;}}")
    info_lay = QVBoxLayout(self._aty_cmp_info_panel)
    info_lay.setContentsMargins(12,10,12,10)
    lbl_info = QLabel(
        "<b>Core</b> = rolling 10th-percentile of the shadow-diameter signal (40&nbsp;mm window), "
        "not a global mean &ndash; loops only push the signal up, so the local lower envelope is the "
        "true core. The <b>Signal &amp; core</b> chart below shows this directly: raw signal, the "
        "core baseline, and the old global-mean reference line.<br>"
        "<b>Core CV</b> = variability of that core baseline itself along the yarn length.<br>"
        "<b>Frequency / Spacing</b> = distance between consecutive detected loop peaks "
        "(<code>scipy.signal.find_peaks</code>, prominence &gt; 30&nbsp;&micro;m, min. distance 1&nbsp;mm).<br>"
        "<b>Relative height</b> = loop height as % of the local core diameter at that position &ndash; "
        "200&nbsp;&micro;m means something very different on a 100&nbsp;&micro;m core than on a "
        "1200&nbsp;&micro;m core.<br>"
        "<b>Bulk Index</b> = total loop area (Rohsignal&minus;core, integrated over each loop's extent) as "
        "a % of the area a loop-free yarn of the same Core thickness would take up &ndash; one headline "
        "number combining frequency, height, and width, self-normalizing so it stays in a readable range "
        "instead of a raw &micro;m&middot;mm figure.<br>"
        "<b>Bin1/Bin2 (Kurzhocker/Langwelle)</b> = same 100&nbsp;&micro;m/mm height&#8202;/&#8202;length split as the "
        "Verteilung tab, recomputed on these (more accurate) loops &ndash; so the percentages won't exactly "
        "match that tab's numbers.<br>"
        "<b>Core CV @1m / @20m</b> = core unevenness at two length scales (meter-to-meter vs. tens-of-metres "
        "drift) &ndash; a simplified take on the classic \"CV at different cut lengths\" idea.<br>"
        "<b>Tail metrics (P95/P99/max)</b> = how extreme the worst loops are, since two yarns can share a "
        "similar median but differ a lot in their outliers.<br>"
        "<i>Defaults tuned on TrialSeries 288 (Aug 2026); not yet exposed as UI settings "
        "&ndash; see ui/yarnscope/aty_core_analysis.py.</i>"
    )
    lbl_info.setStyleSheet("color:#555; font-size:11px;")
    lbl_info.setWordWrap(True)
    lbl_info.setTextFormat(Qt.RichText)
    info_lay.addWidget(lbl_info)
    self._aty_cmp_info_panel.setVisible(False)
    self._aty_cmp_btn_info.toggled.connect(self._aty_cmp_info_panel.setVisible)
    cmp_v.addWidget(self._aty_cmp_info_panel)

    # ── Radar chart: 5-axis "yarn fingerprint", the headline overview ──────
    # (detail tables + charts follow below). Fixed calibration -- see
    # RADAR_BOUNDS in aty_core_analysis.py for what the axes mean and how to
    # recalibrate as more trials become available.
    lbl_radar = QLabel("Yarn fingerprint")
    lbl_radar.setStyleSheet(f"color:{TEXT}; font-size:12px; font-weight:600;")
    lbl_radar.setTextFormat(Qt.RichText)
    cmp_v.addWidget(lbl_radar)

    radar_card = QFrame()
    radar_card.setStyleSheet(
        f"QFrame{{background:{CARD_BG};border:1px solid #dbe2dc;border-radius:3px;}}")
    radar_row = QHBoxLayout(radar_card); radar_row.setContentsMargins(6, 6, 6, 6); radar_row.setSpacing(12)
    radar_fig = _Fig(figsize=(4.6, 4.6), facecolor=CARD_BG)
    radar_fig.subplots_adjust(top=0.90, bottom=0.08)
    self._aty_cmp_radar_ax = radar_fig.add_subplot(111, polar=True)
    self._aty_cmp_radar_canvas = _FCA(radar_fig)
    self._aty_cmp_radar_canvas.setStyleSheet(f"background:{CARD_BG};")
    self._aty_cmp_radar_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    self._aty_cmp_radar_canvas.setMinimumHeight(360)
    radar_row.addWidget(self._aty_cmp_radar_canvas, 3)

    # Plain-language axis descriptions, using the space beside the (fairly
    # small, mostly-empty-card) chart rather than relying on people already
    # knowing what "Character" or "Outliers" is supposed to mean here.
    lbl_radar_desc = QLabel(
        "<b>Volume</b> &ndash; how puffy the yarn looks overall. High = a lot of "
        "extra bulk from loops sticking out.<br><br>"
        "<b>Frequency</b> &ndash; how many loops there are per metre. High = "
        "densely packed, low = sparse.<br><br>"
        "<b>Character</b> &ndash; the loop type mix. High = mostly short, spiky "
        "loops (Kurzhocker). Low = mostly long, flat loops (Langwelle).<br><br>"
        "<b>Evenness</b> &ndash; how regularly the loops are spaced out along the "
        "yarn. High = evenly spread like beads on a string. Low = clumped "
        "together with gaps in between.<br><br>"
        "<b>Outliers</b> &ndash; how extreme the worst loops are compared to a "
        "typical one. High = a few loops stick out much taller than the rest, "
        "even if the average looks normal."
    )
    lbl_radar_desc.setStyleSheet(f"color:{TEXT}; font-size:11px;")
    lbl_radar_desc.setWordWrap(True)
    lbl_radar_desc.setTextFormat(Qt.RichText)
    lbl_radar_desc.setAlignment(Qt.AlignTop)

    # Right column: axis legend on top, then the per-trial one-sentence
    # characterization below it -- both live beside the chart, in the space
    # that was otherwise just empty card background.
    radar_desc_col = QVBoxLayout(); radar_desc_col.setSpacing(10)
    radar_desc_col.addWidget(lbl_radar_desc)

    self._aty_cmp_radar_summary = QLabel("")
    self._aty_cmp_radar_summary.setStyleSheet(f"color:{TEXT}; font-size:11.5px;")
    self._aty_cmp_radar_summary.setWordWrap(True)
    self._aty_cmp_radar_summary.setTextFormat(Qt.RichText)
    self._aty_cmp_radar_summary.setAlignment(Qt.AlignTop)
    radar_desc_col.addWidget(self._aty_cmp_radar_summary)
    radar_desc_col.addStretch(1)

    radar_row.addLayout(radar_desc_col, 2)

    cmp_v.addWidget(radar_card)

    self._aty_cmp_table = QTableWidget(0, 9)
    self._aty_cmp_table.setHorizontalHeaderLabels([
        "Trial", "Global Mean [µm]", "Core [µm]", "Δ [%]", "Core CV [%]",
        "Freq [1/m]", "Spacing CV [%]", "Height median [µm]", "Height median rel. [%]",
    ])
    _aty_set_header_tooltips(self._aty_cmp_table, _CMP_TABLE1_TOOLTIPS)
    self._aty_cmp_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    self._aty_cmp_table.setAlternatingRowColors(True)
    self._aty_cmp_table.setStyleSheet(
        f"QTableWidget{{background:{CARD_BG};alternate-background-color:#f4f6f4;"
        f"color:{TEXT};gridline-color:#e6e9e6;border:1px solid #dbe2dc;border-radius:3px;}}"
        f"QHeaderView::section{{background:{CARD_BG};color:#888;border:none;"
        f"border-bottom:1px solid #dbe2dc;padding:4px 4px;font-size:10.5px;font-weight:600;}}"
        f"QTableWidget::item{{padding:2px;}}"
        f"QTableWidget::item:selected{{background:{accent};color:#fff;}}")
    self._aty_cmp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    self._aty_cmp_table.verticalHeader().setDefaultSectionSize(24)
    self._aty_cmp_table.verticalHeader().setVisible(False)
    self._aty_cmp_table.setFixedHeight(150)
    cmp_v.addWidget(self._aty_cmp_table)

    # Second table: loop shape (Bin1/Bin2), bulk, two-scale core unevenness,
    # and tail metrics -- kept separate from the main table above instead of
    # widening it further, since Stretch-resize with 15+ columns would get
    # unreadably cramped.
    lbl_shape = QLabel("Shape &amp; bulk")
    lbl_shape.setStyleSheet(f"color:{TEXT}; font-size:12px; font-weight:600;")
    lbl_shape.setTextFormat(Qt.RichText)
    cmp_v.addWidget(lbl_shape)

    self._aty_cmp_table2 = QTableWidget(0, 11)
    self._aty_cmp_table2.setHorizontalHeaderLabels([
        "Trial", "Bulk Index [%]", "Garnspiegel CV [%]", "Bin1 % (Kurzhocker)", "Bin2 % (Langwelle)",
        "Bin1 [1/m]", "Bin2 [1/m]",
        "Core CV @1m [%]", "Core CV @20m [%]", "Rel. height P99 [%]", "Rel. height max [%]",
    ])
    _aty_set_header_tooltips(self._aty_cmp_table2, _CMP_TABLE2_TOOLTIPS)
    self._aty_cmp_table2.setEditTriggers(QAbstractItemView.NoEditTriggers)
    self._aty_cmp_table2.setAlternatingRowColors(True)
    self._aty_cmp_table2.setStyleSheet(
        f"QTableWidget{{background:{CARD_BG};alternate-background-color:#f4f6f4;"
        f"color:{TEXT};gridline-color:#e6e9e6;border:1px solid #dbe2dc;border-radius:3px;}}"
        f"QHeaderView::section{{background:{CARD_BG};color:#888;border:none;"
        f"border-bottom:1px solid #dbe2dc;padding:4px 4px;font-size:10.5px;font-weight:600;}}"
        f"QTableWidget::item{{padding:2px;}}"
        f"QTableWidget::item:selected{{background:{accent};color:#fff;}}")
    self._aty_cmp_table2.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    self._aty_cmp_table2.verticalHeader().setDefaultSectionSize(24)
    self._aty_cmp_table2.verticalHeader().setVisible(False)
    self._aty_cmp_table2.setFixedHeight(150)
    cmp_v.addWidget(self._aty_cmp_table2)

    # Third table: "quality" (typical size) within each loop type, plus how
    # much of the overall Bulk Index each type is responsible for. Count
    # alone (table above) can't tell "many small loops" apart from "few big
    # ones" -- this can.
    lbl_quality = QLabel("Loop quality by type")
    lbl_quality.setStyleSheet(f"color:{TEXT}; font-size:12px; font-weight:600;")
    lbl_quality.setTextFormat(Qt.RichText)
    cmp_v.addWidget(lbl_quality)

    self._aty_cmp_table3 = QTableWidget(0, 7)
    self._aty_cmp_table3.setHorizontalHeaderLabels([
        "Trial", "Kurzhocker height med. [µm]", "Kurzhocker height rel. [%]", "Kurzhocker bulk contrib. [%]",
        "Langwelle height med. [µm]", "Langwelle height rel. [%]", "Langwelle bulk contrib. [%]",
    ])
    _aty_set_header_tooltips(self._aty_cmp_table3, _CMP_TABLE3_TOOLTIPS)
    self._aty_cmp_table3.setEditTriggers(QAbstractItemView.NoEditTriggers)
    self._aty_cmp_table3.setAlternatingRowColors(True)
    self._aty_cmp_table3.setStyleSheet(
        f"QTableWidget{{background:{CARD_BG};alternate-background-color:#f4f6f4;"
        f"color:{TEXT};gridline-color:#e6e9e6;border:1px solid #dbe2dc;border-radius:3px;}}"
        f"QHeaderView::section{{background:{CARD_BG};color:#888;border:none;"
        f"border-bottom:1px solid #dbe2dc;padding:4px 4px;font-size:10.5px;font-weight:600;}}"
        f"QTableWidget::item{{padding:2px;}}"
        f"QTableWidget::item:selected{{background:{accent};color:#fff;}}")
    self._aty_cmp_table3.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    self._aty_cmp_table3.verticalHeader().setDefaultSectionSize(24)
    self._aty_cmp_table3.verticalHeader().setVisible(False)
    self._aty_cmp_table3.setFixedHeight(150)
    cmp_v.addWidget(self._aty_cmp_table3)

    def _chart_card(fig_w, fig_h):
        """White bordered card (like _card() in screen_nozzle_calculator.py) wrapping a chart."""
        card = QFrame()
        card.setStyleSheet(
            f"QFrame{{background:{CARD_BG};border:1px solid #dbe2dc;border-radius:3px;}}")
        lay = QVBoxLayout(card); lay.setContentsMargins(6,6,6,6)
        fig = _Fig(figsize=(fig_w, fig_h), facecolor=CARD_BG)
        fig.subplots_adjust(left=0.13, right=0.97, top=0.90, bottom=0.18)
        ax = fig.add_subplot(111)
        canvas = _FCA(fig)
        canvas.setStyleSheet(f"background:{CARD_BG};")
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Expanding + a stretch factor inside a resizable QScrollArea can
        # collapse the canvas toward its (tiny) minimumSizeHint instead of a
        # readable size -- pin a floor derived from the figure's own inches
        # so it can grow but never gets squashed flat.
        canvas.setMinimumHeight(int(fig_h * 90))
        lay.addWidget(canvas)
        return card, ax, canvas

    # ── Signal & core (zoom), one card per selected trial ──────────────────
    # Uses the "Start [m]" spinbox from the shared control panel below (also
    # used by Garnspiegel/Fabric/Knitted) as the zoom window's start position,
    # so there's no duplicate control. Window is fixed at 40mm (matches the
    # default core-baseline window) -- re-click "Run Comparison" after
    # changing Start to refresh.
    lbl_sig = QLabel("Signal &amp; core (40mm zoom)")
    lbl_sig.setStyleSheet(f"color:{TEXT}; font-size:12px; font-weight:600;")
    lbl_sig.setTextFormat(Qt.RichText)
    cmp_v.addWidget(lbl_sig)

    self._aty_cmp_signal_scroll = QScrollArea()
    self._aty_cmp_signal_scroll.setWidgetResizable(True)
    self._aty_cmp_signal_scroll.setStyleSheet(
        f"QScrollArea{{background:{LIGHT_BG};border:none;}}")
    # This scroll area only exists for the HORIZONTAL case (more trial cards
    # than fit side by side) -- the outer cmp_outer_scroll already handles
    # vertical scrolling for the whole tab, so a nested vertical scrollbar
    # here would just be a second, redundant scroll gesture. Fixed height is
    # the card's own floor (2.6in canvas -> 234px, see _chart_card's
    # setMinimumHeight, + 12px card margins = 246px) plus room for the
    # horizontal scrollbar track so it never needs to grow into a vertical
    # one; the policy below is the actual guarantee.
    self._aty_cmp_signal_scroll.setFixedHeight(264)
    self._aty_cmp_signal_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    sig_inner = QWidget(); sig_inner.setStyleSheet(f"background:{LIGHT_BG};")
    self._aty_cmp_signal_layout = QHBoxLayout(sig_inner)
    self._aty_cmp_signal_layout.setContentsMargins(0,0,0,0)
    self._aty_cmp_signal_layout.setSpacing(8)
    self._aty_cmp_signal_scroll.setWidget(sig_inner)
    cmp_v.addWidget(self._aty_cmp_signal_scroll)
    self._aty_cmp_chart_card = _chart_card  # reused by _aty_render_compare for signal cards

    cmp_charts = QHBoxLayout(); cmp_charts.setSpacing(8)
    sp_card, self._aty_cmp_spacing_ax, self._aty_cmp_spacing_canvas = _chart_card(4.2, 2.6)
    cmp_charts.addWidget(sp_card, 1)
    rh_card, self._aty_cmp_relheight_ax, self._aty_cmp_relheight_canvas = _chart_card(4.2, 2.6)
    cmp_charts.addWidget(rh_card, 1)
    # No vertical stretch here: inside a resizable QScrollArea (see
    # cmp_outer_scroll above) every section should just take its natural
    # size and let the scrollbar handle overflow, rather than fight over
    # leftover space -- a stretch factor was fine back when this tab had a
    # fixed height, but now it just invites the same squash-to-minimum
    # behaviour the canvas minimumHeight above guards against.
    cmp_v.addLayout(cmp_charts)

    # Histogram canvases are persistent (re-drawn in place on every "Run
    # Comparison" click, not rebuilt) -- attach the hover handler exactly
    # once here; _aty_render_compare only updates the *_hist_data lists the
    # lookup closures read from, it never re-attaches.
    self._aty_cmp_spacing_hist_data = []
    self._aty_cmp_relheight_hist_data = []
    self._aty_cmp_spacing_hover_state = _aty_attach_hover(
        self._aty_cmp_spacing_canvas, self._aty_cmp_spacing_ax,
        _aty_make_hist_lookup(self, "_aty_cmp_spacing_hist_data", "mm"))
    self._aty_cmp_relheight_hover_state = _aty_attach_hover(
        self._aty_cmp_relheight_canvas, self._aty_cmp_relheight_ax,
        _aty_make_hist_lookup(self, "_aty_cmp_relheight_hist_data", "%"))

    cmp_outer_scroll.setWidget(cmp_w)
    self._aty_sub_tabs.addTab(cmp_outer_scroll, "Compare")

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

    # Auf kleinen/niedrig aufgelösten Laptop-Bildschirmen quetschen sich
    # Trial-Liste, Sub-Tabs (Charts) und Bedienelemente sonst ineinander
    # (Nutzerfeedback 2026-08-27) - eine QScrollArea um den ganzen Tab-Inhalt
    # sorgt dafür, dass unterhalb dieser Mindestgrösse gescrollt statt
    # gequetscht wird (gleiches Muster wie beim "Compare"-Sub-Tab weiter
    # oben, nur jetzt für den ganzen Haupt-Tab). Die Mindestgrösse muss auf
    # dem Splitter selbst sitzen (nicht auf der QScrollArea) - sonst hätte
    # die QScrollArea nichts, das ihre Sichtfläche tatsächlich überschreiten
    # könnte, und würde nie Scrollbalken zeigen.
    splitter.setMinimumSize(950, 650)
    outer_scroll = QScrollArea()
    outer_scroll.setWidgetResizable(True)
    outer_scroll.setFrameShape(QFrame.NoFrame)
    outer_scroll.setWidget(splitter)
    root.addWidget(outer_scroll, 1)
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
    # Aktuelle Einzel- und Mehrfachauswahl (Trial-ID statt Zeilenindex)
    # merken, damit ein automatischer Refresh (siehe
    # _aty_update_auto_refresh_state()) weder die laufende Analyse noch eine
    # aktive Compare-Auswahl zuruecksetzt.
    prev_row = self._aty_trial_list.currentRow()
    prev_tid = None
    if prev_row >= 0:
        prev_item = self._aty_trial_list.item(prev_row)
        if prev_item:
            prev_tid = (prev_item.data(Qt.UserRole) or {}).get("trial_id")
    prev_selected_tids = set()
    for it in self._aty_trial_list.selectedItems():
        d = it.data(Qt.UserRole) or {}
        if d.get("trial_id") is not None:
            prev_selected_tids.add(d.get("trial_id"))
    self._aty_trial_list.blockSignals(True)
    self._aty_trial_list.clear()
    sid = self._series_pk
    all_have_tdms = True
    restore_row = -1
    for i, t in enumerate(self._trials):
        tl = {k.lower(): v for k, v in t.items()}
        tid = tl.get("id")
        vno = int(tl.get("versuchsnummer") or 0)
        tdms = _aty_find_tdms(sid, vno) if sid else None
        if not tdms:
            all_have_tdms = False
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
        if tid is not None and tid == prev_tid:
            restore_row = i
        if tid in prev_selected_tids:
            item.setSelected(True)
    if restore_row >= 0:
        self._aty_trial_list.setCurrentRow(restore_row)
    self._aty_trial_list.blockSignals(False)
    # Stoppt den Auto-Refresh-Timer, sobald fuer jeden Trial ein TDMS-File
    # gefunden wurde - siehe _aty_update_auto_refresh_state().
    self._aty_all_tdms_present = all_have_tdms
    _aty_update_auto_refresh_state(self)


def _aty_update_auto_refresh_state(self):
    """Startet/stoppt den ATY-YarnScope-Auto-Refresh-Timer.

    Analog zu dty_yarnscope_tab.py::_ys_update_auto_refresh_state(): laeuft
    nur, waehrend der ATY-YarnScope-Tab aktiv ist UND mindestens ein Trial
    noch ohne TDMS-File dasteht.
    """
    timer = getattr(self, "_aty_auto_timer", None)
    if timer is None:
        return
    should_run = (
        self.tab_aty_yarnscope is not None
        and self.tabs.currentWidget() is self.tab_aty_yarnscope
        and not getattr(self, "_aty_all_tdms_present", False)
    )
    if should_run and not timer.isActive():
        timer.start()
    elif not should_run and timer.isActive():
        timer.stop()


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
# Compare multiple trials (core baseline + loop metrics)
# ---------------------------------------------------------------------------
# Independent path, decoupled from the existing single-trial flow above
# (currentRowChanged / _aty_cache / detect_thick_spots). Uses
# ui.yarnscope.aty_core_analysis, NOT thick_spot_analysis -- the latter stays
# unchanged for the existing single-trial flow. Reversible: this block plus
# the "Compare" sub-tab can be removed without touching the rest of the file.

# Validated categorical palette (see dataviz skill, references/palette.md) --
# fixed order, do not rotate/reorder.
_CMP_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
               "#e87ba4", "#008300", "#4a3aa7", "#e34948"]


def _aty_on_compare_selection_changed(self):
    """Reacts to multi-select in the trial list (used only by the Compare tab)."""
    if self._aty_trial_list is None:
        return
    items = self._aty_trial_list.selectedItems()
    n = len(items)
    btn = getattr(self, "_aty_cmp_btn_run", None)
    lbl = getattr(self, "_aty_cmp_lbl_status", None)
    if btn is not None:
        btn.setEnabled(n >= 1)
    if lbl is not None:
        if n == 0:
            lbl.setText("No trials selected (Ctrl/Shift-click for multi-select in the list on the left).")
        else:
            names = []
            for it in items:
                d = it.data(Qt.UserRole) or {}
                vno = d.get("vno")
                names.append(f"V{vno:03d}" if isinstance(vno, int) else "?")
            lbl.setText(f"{n} trial(s) selected: " + ", ".join(names))


def _aty_get_arr_mm_pp(self, trial_id, tdms_path):
    """Returns (arr_mm, mm_per_point, ellipticity_pct) for a trial.
    ellipticity_pct is None for a single-axis TDMS (the vast majority) - see
    dty_tdms_reader.read_aty_signal().

    Reuses the existing single-trial cache (self._aty_cache) if the trial was
    already loaded there (via "Analysieren"), then self._aty_raw_cache
    (populated by this function itself on first read for Compare-only
    trials) -- otherwise reads the TDMS fresh, identical to the conversion
    in _aty_on_analyze.
    """
    entry = self._aty_cache.get(trial_id) if trial_id is not None else None
    if entry is not None:
        return entry[2], entry[4], (entry[7] if len(entry) > 7 else None)
    cached = self._aty_raw_cache.get(trial_id) if trial_id is not None else None
    if cached is not None:
        return cached
    if not tdms_path:
        return None, None, None
    arr, ell = read_aty_signal(str(tdms_path))
    mm_pp = float(read_step_mm_from_tdms(str(tdms_path)) or 0.25)
    if arr is None or len(arr) == 0:
        return None, None, None
    if trial_id is not None:
        self._aty_raw_cache[trial_id] = (arr, mm_pp, ell)
    return arr, mm_pp, ell


def _aty_on_compare_run(self):
    """Computes core/loop metrics for all selected trials and renders the
    table + histograms in the "Compare" sub-tab."""
    items = self._aty_trial_list.selectedItems() if self._aty_trial_list else []
    if not items:
        return
    self._aty_cmp_btn_run.setEnabled(False)
    self._aty_cmp_lbl_status.setText("Computing…")
    QApplication.processEvents()

    zoom_start_mm = float(self._aty_spin_start.value()) * 1000.0

    results = []
    try:
        for it in items:
            d = it.data(Qt.UserRole) or {}
            tid, vno, tdms = d.get("trial_id"), d.get("vno"), d.get("tdms")
            if not tdms:
                continue
            arr, mm_pp, ell = _aty_get_arr_mm_pp(self, tid, tdms)
            if arr is None:
                continue
            cached = self._aty_core_cache.get(tid) if tid is not None else None
            if cached is None:
                cached = _aty_analyze_trial_core(arr, mm_pp, ellipticity_pct=ell)
                if tid is not None:
                    self._aty_core_cache[tid] = cached
            results.append((vno, cached, arr, mm_pp))
        results.sort(key=lambda r: (r[0] is None, r[0]))
        _aty_render_compare(self, results, zoom_start_mm)
        self._aty_cmp_lbl_status.setText(f"Done – {len(results)} trial(s).")
    except Exception as e:
        traceback.print_exc()
        self._aty_cmp_lbl_status.setText(f"Error: {e}")
    finally:
        self._aty_cmp_btn_run.setEnabled(True)


def _aty_make_hover_artists(ax):
    """Creates the vline+annotation pair used by _aty_attach_hover.

    Must be called again after every ax.clear() -- clear() destroys any
    previously created artists, including these. Re-pins the current x/y
    limits afterwards: axvline(0, ...) would otherwise feed into Matplotlib's
    autoscale and drag the x-axis down to include x=0, distorting the plot
    regardless of where the real data actually sits.
    """
    # Force autoscale to run now (it's otherwise deferred to the next draw()),
    # so the limits captured below reflect the already-plotted real data,
    # not stale pre-clear()/default (0,1) limits.
    ax.relim()
    ax.autoscale_view()
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    vline = ax.axvline(0, color="#999", linewidth=0.8, linestyle=":",
                        visible=False, zorder=10)
    annot = ax.annotate(
        "", xy=(0, 0), xytext=(10, 10), textcoords="offset points",
        bbox=dict(boxstyle="round,pad=0.4", fc="#ffffff", ec="#dbe2dc", lw=0.8),
        fontsize=7, color="#2b2b2b", visible=False, zorder=11, annotation_clip=False,
    )
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    return {"vline": vline, "annot": annot}


def _aty_attach_hover(canvas, ax, lookup_fn, state=None):
    """Attaches a crosshair + tooltip to a matplotlib axes on mouse hover.

    lookup_fn(x_data) -> (header_str, [(label, value_str, color), ...]) or
    None/falsy to hide the tooltip at that x. Returns the artist state dict.

    Call this exactly ONCE per canvas. For axes that get ax.clear()'d and
    redrawn in place on every render (rather than recreated) -- clear()
    destroys the vline/annotation artists along with everything else -- have
    the render function call _aty_make_hover_artists(ax) again after each
    clear() and overwrite this returned dict's entries in place; the
    handlers below always read the current values from `state`, so they
    keep working after a refresh.
    """
    if state is None:
        state = _aty_make_hover_artists(ax)

    def _hide():
        vline, annot = state.get("vline"), state.get("annot")
        if vline is None or annot is None:
            return
        if vline.get_visible() or annot.get_visible():
            vline.set_visible(False)
            annot.set_visible(False)
            canvas.draw_idle()

    def _on_move(event):
        vline, annot = state.get("vline"), state.get("annot")
        if vline is None or annot is None:
            return
        if event.inaxes != ax or event.xdata is None:
            _hide()
            return
        result = lookup_fn(event.xdata)
        if not result:
            _hide()
            return
        header, rows = result
        vline.set_xdata([event.xdata, event.xdata])
        vline.set_visible(True)
        annot.set_text(header + "\n" + "\n".join(f"{lbl}: {val}" for lbl, val, _c in rows))
        annot.xy = (event.xdata, event.ydata if event.ydata is not None else ax.get_ylim()[0])
        # Flip the box to the left once we're past ~70% of the x-range so it
        # doesn't run off the right edge of the canvas.
        xlim = ax.get_xlim()
        frac = (event.xdata - xlim[0]) / (xlim[1] - xlim[0]) if xlim[1] != xlim[0] else 0.0
        annot.set_position((-100, 10) if frac > 0.7 else (10, 10))
        annot.set_visible(True)
        canvas.draw_idle()

    canvas.mpl_connect("motion_notify_event", _on_move)
    canvas.mpl_connect("figure_leave_event", lambda _e: _hide())
    return state


def _aty_make_hist_lookup(self, attr_name, unit):
    """Returns a lookup_fn for _aty_attach_hover reading self.<attr_name>,
    a list of (label, color, bin_edges, pct_values) tuples kept up to date
    by _aty_render_compare on every "Run Comparison" click."""
    def lookup(x):
        data = getattr(self, attr_name, None)
        if not data:
            return None
        edges = data[0][2]
        if x < edges[0] or x > edges[-1]:
            return None
        bin_idx = int(np.clip(np.searchsorted(edges, x, side="right") - 1, 0, len(edges) - 2))
        header = f"{edges[bin_idx]:.1f}–{edges[bin_idx+1]:.1f} {unit}"
        rows = [(label, f"{vals[bin_idx]:.1f}%", color) for label, color, _e, vals in data]
        return header, rows
    return lookup


def _aty_set_header_tooltips(table, tooltips):
    """Sets a hover tooltip on each column header of a QTableWidget.

    tooltips must have exactly as many entries as the table has columns,
    in the same order.
    """
    for col, text in enumerate(tooltips):
        item = table.horizontalHeaderItem(col)
        if item is not None:
            item.setToolTip(text)


# Plain-language explanations for the Compare tab's two tables' column
# headers -- deliberately non-technical (an analogy alongside the definition,
# not just a formula), per explicit user request.
_CMP_TABLE1_TOOLTIPS = [
    "Which measurement (trial) this row is.",
    "The old, simple way of measuring yarn thickness: just average every single "
    "measurement point. Problem: the fluffy loops sticking out of the yarn pull "
    "this average upward, so it doesn't really tell you how thick the smooth "
    "'core' strand actually is.",
    "The new, more honest estimate of how thick the actual yarn strand is, with "
    "the loops ignored. Think of it as: 'if you only looked at the smooth parts "
    "between the loops, how thick would the yarn be?'",
    "How much lower the new Core number is compared to the old Global Mean. A "
    "negative value means the old method was overestimating the yarn's "
    "thickness because it got fooled by the loops.",
    "How much that Core thickness itself wobbles up and down along the length "
    "of the yarn. Low = very consistent thickness everywhere. High = the yarn "
    "gets noticeably thicker and thinner in different spots.",
    "How many loops there are per metre of yarn. Higher number = more loops "
    "packed into the same length -- a denser, fluffier yarn.",
    "How evenly the loops are spread out. Low = loops appear at fairly regular "
    "intervals, like beads on a string. High = sometimes several loops bunch up "
    "together, then a long empty stretch follows.",
    "Line up every single loop from smallest to tallest and pick the one "
    "exactly in the middle -- how tall is it, in micrometres (thousandths of a "
    "millimetre)? This is the 'typical' loop size, not skewed by a few extreme "
    "ones.",
    "The same typical loop height, but shown as a percentage of the yarn's own "
    "Core thickness instead of an absolute number. This makes thin and thick "
    "yarns comparable: 50% means a typical loop sticks out half as tall as the "
    "yarn strand itself.",
]

_CMP_TABLE2_TOOLTIPS = [
    "Which measurement (trial) this row is.",
    "One single number for 'how puffy is this yarn overall'. It adds up the "
    "size (both height and width) of every loop, then compares that total to "
    "how much material a perfectly smooth, loop-free yarn of the same Core "
    "thickness would take up. 20% means the loops add roughly a fifth more "
    "bulk on top of the bare core -- usually the number that best matches "
    "what you actually see and feel.",
    "Width-CV% measured directly from the Garnspiegel wrap-test photo for this "
    "trial (image processing, not the TDMS signal) -- '-' if no matching photo "
    "(filename 'V<n>.jpg') has been analyzed yet. Correlates well with Bulk "
    "Index within one photo session (r=0.94 on the TrialSeries 288 validation "
    "batch), but treat it as a rough proxy across different photo sessions -- "
    "not yet corrected for session-to-session lighting/distance differences. "
    "See ui/yarnscope/garnspiegel_analysis.py.",
    "What percentage of loops are short and steep ('Kurzhocker') rather than "
    "long and flat ('Langwelle', the next column). Two yarns can have the "
    "exact same number of loops but look completely different if one is "
    "mostly short spikes and the other mostly long flat bumps.",
    "What percentage of loops are long and flat ('Langwelle') instead of "
    "short and steep ('Kurzhocker', the column before). This and the Bin1 "
    "column always add up to 100% -- a yarn with a low Kurzhocker share is "
    "dominated by these long, flat bumps instead.",
    "How many short, steep 'Kurzhocker' loops there are in every metre of "
    "yarn -- the count version of the Bin1 % column.",
    "How many long, flat 'Langwelle' loops there are in every metre of yarn "
    "-- the count version of the Bin2 % column.",
    "Does the yarn's thickness drift up and down from one metre to the next? A "
    "high value means some 1-metre stretches are noticeably thicker than "
    "others right next to them.",
    "Same question, but zoomed out to 20-metre stretches -- does the average "
    "thickness slowly drift over longer sections, e.g. one part of the bobbin "
    "coming out thicker than another?",
    "Ignore the typical loop for a moment and look only at the tallest 1% of "
    "all loops -- the extreme ones. How tall are those, relative to the yarn's "
    "Core thickness? Good for spotting occasional trouble spots that a median "
    "would hide.",
    "The single biggest loop found anywhere in this trial, as a percentage of "
    "the Core thickness. The absolute worst-case outlier -- a value over 100% "
    "means that one loop actually stuck out taller than the yarn's own "
    "thickness.",
]

_CMP_TABLE3_TOOLTIPS = [
    "Which measurement (trial) this row is.",
    "How tall a typical short, steep 'Kurzhocker' loop is, in micrometres. "
    "Two yarns can have the same NUMBER of Kurzhocker loops (see the Shape & "
    "bulk table above) yet look totally different if one yarn's are small "
    "bumps and the other's are big spikes -- this tells them apart.",
    "The same typical Kurzhocker height, but as a percentage of the yarn's "
    "own Core thickness, so thin and thick yarns stay comparable.",
    "How much of the overall Bulk Index (see the Shape & bulk table) comes "
    "specifically from Kurzhocker loops -- combines 'how many there are' and "
    "'how big they are' into one number. If this is high but the Kurzhocker % "
    "count wasn't, it means there are relatively few Kurzhocker loops but "
    "they're substantial ones.",
    "How tall a typical long, flat 'Langwelle' loop is, in micrometres -- "
    "same idea as the Kurzhocker height column, for the other loop type.",
    "The same typical Langwelle height, but as a percentage of the yarn's own "
    "Core thickness.",
    "How much of the overall Bulk Index comes specifically from Langwelle "
    "loops. Together with the Kurzhocker bulk contribution column, these two "
    "always add up to the Bulk Index in the Shape & bulk table.",
]


def _aty_clear_layout(layout):
    """Removes and deletes all widgets from a QLayout (used to rebuild the
    per-trial signal-card row on every "Run Comparison" click).

    setParent(None) removes the widget from display immediately; deleteLater()
    alone would leave it visible until the event loop next goes idle.
    """
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()


def _aty_render_signal_cards(self, results, zoom_start_mm, window_mm=40.0):
    """Rebuilds the "Signal & core" card row: one raw-signal + core-baseline
    + global-mean chart per selected trial, all at the same start position."""
    _aty_clear_layout(self._aty_cmp_signal_layout)
    # Minimum width (not fixed) + stretch: cards grow to fill available
    # space with few trials selected, and the surrounding QScrollArea kicks
    # in once N cards no longer fit at their minimum width.
    for i, (vno, r, arr, mm_pp) in enumerate(results):
        color = _CMP_COLORS[i % len(_CMP_COLORS)]
        card, ax, canvas = self._aty_cmp_chart_card(3.6, 2.6)
        card.setMinimumWidth(340)
        self._aty_cmp_signal_layout.addWidget(card, 1)

        pos_mm, raw_mm, base_mm = _aty_get_zoom_segment(arr, mm_pp, zoom_start_mm, window_mm)
        if len(pos_mm) == 0:
            continue
        global_mean_mm = r["global_mean_um"] / 1000.0
        label = f"V{vno:03d}" if isinstance(vno, int) else "?"

        ax.clear(); ax.set_facecolor(CARD_BG); ax.figure.patch.set_facecolor(CARD_BG)
        ax.set_title(f"{label} @ {zoom_start_mm/1000:.2f}m", color=TEXT, fontsize=9, fontweight="bold")
        ax.set_xlabel("mm", color="#888", fontsize=8)
        ax.set_ylabel("mm", color="#888", fontsize=8)
        ax.tick_params(colors="#999", labelsize=7)
        ax.grid(axis="y", color="#e6e9e6", linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#dbe2dc")

        ax.axhline(global_mean_mm, color=_CMP_COLORS[1], linewidth=1.4,
                   linestyle="--", zorder=2, label="global mean (old)")
        ax.fill_between(pos_mm, base_mm, raw_mm, color=color, alpha=0.15, zorder=2)
        ax.plot(pos_mm, raw_mm, color="#52514e", linewidth=1.3, zorder=3, label="raw signal")
        ax.plot(pos_mm, base_mm, color=color, linewidth=2.0, zorder=4, label="core (new)")
        leg = ax.legend(fontsize=6, framealpha=0.9, facecolor=CARD_BG,
                        edgecolor="#dbe2dc", labelcolor=TEXT, loc="upper right")
        leg.set_zorder(5)

        def _lookup(x, _pos=pos_mm, _raw=raw_mm, _base=base_mm):
            idx = int(np.clip(np.searchsorted(_pos, x), 0, len(_pos) - 1))
            if idx > 0 and abs(_pos[idx - 1] - x) < abs(_pos[idx] - x):
                idx -= 1
            return (f"{_pos[idx]:.2f} mm",
                    [("raw", f"{_raw[idx]:.4f} mm", None),
                     ("core", f"{_base[idx]:.4f} mm", None)])

        _aty_attach_hover(canvas, ax, _lookup)
        canvas.draw_idle()


def _aty_render_radar(self, results):
    """Draws the 5-axis "yarn fingerprint" radar, one polygon per selected
    trial, using aty_core_analysis.compute_radar_scores() (fixed 0-100
    calibration -- see RADAR_BOUNDS there)."""
    ax = self._aty_cmp_radar_ax
    ax.clear()
    ax.figure.patch.set_facecolor(CARD_BG)
    ax.set_facecolor(CARD_BG)

    n_axes = len(_ATY_RADAR_AXES)
    angles = [2 * math.pi * i / n_axes for i in range(n_axes)]
    angles += angles[:1]

    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([_ATY_RADAR_LABELS[a] for a in _ATY_RADAR_AXES],
                        color=TEXT, fontsize=9)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], color="#999", fontsize=6)
    ax.grid(color="#e6e9e6", linewidth=0.8)
    ax.spines["polar"].set_color("#dbe2dc")

    summary_lines = []
    for i, (vno, r, _arr, _mm_pp) in enumerate(results):
        color = _CMP_COLORS[i % len(_CMP_COLORS)]
        label = f"V{vno:03d}" if isinstance(vno, int) else "?"
        scores = _aty_compute_radar_scores(r)
        values = [scores[a] if math.isfinite(scores[a]) else 0.0 for a in _ATY_RADAR_AXES]
        values += values[:1]
        ax.plot(angles, values, color=color, linewidth=2, label=label, zorder=3)
        ax.fill(angles, values, color=color, alpha=0.12, zorder=2)
        sentence = _aty_describe_yarn(scores)
        raw_line = " &middot; ".join(
            f"{_ATY_RADAR_LABELS[a]} "
            f"{(f'{scores[a]:.1f}' if math.isfinite(scores[a]) else '–')}"
            for a in _ATY_RADAR_AXES)
        summary_lines.append(
            f'<span style="color:{color}; font-weight:700;">{label}</span> &ndash; {sentence}'
            f'<br><span style="font-size:10px; color:#8a938c;">{raw_line}</span>')

    if results:
        ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=7.5,
                   framealpha=0.9, facecolor=CARD_BG, edgecolor="#dbe2dc", labelcolor=TEXT)

    self._aty_cmp_radar_canvas.draw_idle()
    self._aty_cmp_radar_summary.setText("<br><br>".join(summary_lines))


def _aty_fetch_garnspiegel_cv(self) -> dict:
    """{Versuchsnummer: CVPct} for the current TrialSeries, from photo-based
    Garnspiegel analysis (tblTrialSeriesImageAnalysis, see
    ui/yarnscope/garnspiegel_analysis.py) - independent of and complementary
    to the TDMS-based metrics in the rest of this Compare tab. Table may not
    exist yet on every environment (rolled out gradually), so this quietly
    returns {} rather than erroring. If a trial has more than one analyzed
    photo, the most recently analyzed one wins."""
    sid = getattr(self, "_series_pk", None)
    if sid is None or not table_exists("tblTrialSeriesImageAnalysis"):
        return {}
    try:
        from ui.yarnscope.garnspiegel_analysis import parse_versuchsnummer
        rows = fetch_all(
            "SELECT img.OriginalFilename, a.CVPct, a.Timestamp "
            "FROM tblTrialSeriesImageAnalysis a "
            "JOIN tblTrialSeriesImage img ON img.ID = a.TrialSeriesImageID "
            "WHERE img.TrialSeriesID = ? AND a.Status = 'ok' "
            "ORDER BY a.Timestamp ASC",
            [sid],
        )
        result = {}
        for r in rows:
            vno = parse_versuchsnummer(r.get("OriginalFilename") or "")
            if vno is not None and r.get("CVPct") is not None:
                result[vno] = float(r["CVPct"])  # later (more recent) rows overwrite earlier ones
        return result
    except Exception:
        return {}


def _aty_render_compare(self, results, zoom_start_mm=0.0):
    """Fills the comparison table, the signal/core cards, and the two
    histograms (spacing, relative loop height) for a list of
    (vno, stats_dict, arr_mm, mm_per_point) tuples."""
    _aty_render_radar(self, results)

    tbl = self._aty_cmp_table
    tbl.setRowCount(len(results))

    def _fmt(v, dec=1):
        try:
            vv = float(v)
            return f"{vv:.{dec}f}" if math.isfinite(vv) else "–"
        except Exception:
            return "–"

    for row, (vno, r, _arr, _mm_pp) in enumerate(results):
        vals = [
            f"V{vno:03d}" if isinstance(vno, int) else "?",
            _fmt(r["global_mean_um"]), _fmt(r["core_mean_um"]), _fmt(r["delta_pct"]),
            _fmt(r["core_cv_pct"], 2), _fmt(r["density_per_m"]), _fmt(r["spacing_cv_pct"]),
            _fmt(r["height_median_um"]), _fmt(r["rel_height_median_pct"]),
        ]
        for col, v in enumerate(vals):
            item = QTableWidgetItem(v)
            item.setTextAlignment(Qt.AlignCenter)
            tbl.setItem(row, col, item)

    garnspiegel_cv_by_vno = _aty_fetch_garnspiegel_cv(self)

    tbl2 = self._aty_cmp_table2
    tbl2.setRowCount(len(results))
    for row, (vno, r, _arr, _mm_pp) in enumerate(results):
        cv = garnspiegel_cv_by_vno.get(vno)
        vals2 = [
            f"V{vno:03d}" if isinstance(vno, int) else "?",
            _fmt(r["bulk_index_pct"]), (_fmt(cv) if cv is not None else "–"),
            _fmt(r["bin1_pct"]), _fmt(r["bin2_pct"]),
            _fmt(r["bin1_density_per_m"]), _fmt(r["bin2_density_per_m"]),
            _fmt(r["core_cv_short_pct"]), _fmt(r["core_cv_long_pct"]),
            _fmt(r["rel_height_p99_pct"]), _fmt(r["rel_height_max_pct"]),
        ]
        for col, v in enumerate(vals2):
            item = QTableWidgetItem(v)
            item.setTextAlignment(Qt.AlignCenter)
            tbl2.setItem(row, col, item)

    tbl3 = self._aty_cmp_table3
    tbl3.setRowCount(len(results))
    for row, (vno, r, _arr, _mm_pp) in enumerate(results):
        vals3 = [
            f"V{vno:03d}" if isinstance(vno, int) else "?",
            _fmt(r["bin1_height_median_um"]), _fmt(r["bin1_rel_height_median_pct"]), _fmt(r["bin1_bulk_pct"]),
            _fmt(r["bin2_height_median_um"]), _fmt(r["bin2_rel_height_median_pct"]), _fmt(r["bin2_bulk_pct"]),
        ]
        for col, v in enumerate(vals3):
            item = QTableWidgetItem(v)
            item.setTextAlignment(Qt.AlignCenter)
            tbl3.setItem(row, col, item)

    _aty_render_signal_cards(self, results, zoom_start_mm)

    def _style_ax(ax, title, xlabel):
        ax.clear(); ax.set_facecolor(CARD_BG); ax.figure.patch.set_facecolor(CARD_BG)
        ax.set_title(title, color=TEXT, fontsize=9, fontweight="bold")
        ax.set_xlabel(xlabel, color="#888", fontsize=8)
        ax.set_ylabel("% of loops", color="#888", fontsize=8)
        ax.tick_params(colors="#999", labelsize=7)
        ax.grid(axis="y", color="#e6e9e6", linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#dbe2dc")

    ax_sp = self._aty_cmp_spacing_ax
    _style_ax(ax_sp, "Spacing between peaks", "mm")
    ax_rh = self._aty_cmp_relheight_ax
    _style_ax(ax_rh, "Height relative to core", "%")

    self._aty_cmp_spacing_hist_data = []
    self._aty_cmp_relheight_hist_data = []
    sp_bins = np.arange(0, 16.5, 0.5)
    rh_bins = np.arange(0, 105, 5)

    for i, (vno, r, _arr, _mm_pp) in enumerate(results):
        color = _CMP_COLORS[i % len(_CMP_COLORS)]
        label = f"V{vno:03d}" if isinstance(vno, int) else "?"
        spacing = r.get("spacing_mm")
        if spacing is not None and len(spacing):
            w = np.full(len(spacing), 100.0/len(spacing))
            counts, _e = np.histogram(spacing, bins=sp_bins, weights=w)
            self._aty_cmp_spacing_hist_data.append((label, color, sp_bins, counts))
            ax_sp.hist(spacing, bins=sp_bins, weights=w, histtype="stepfilled",
                       color=color, alpha=0.18, zorder=2)
            ax_sp.hist(spacing, bins=sp_bins, weights=w, histtype="step",
                       color=color, linewidth=1.8, label=label, zorder=3)
        rel = r.get("rel_height_pct")
        if rel is not None and len(rel):
            w = np.full(len(rel), 100.0/len(rel))
            counts, _e = np.histogram(rel, bins=rh_bins, weights=w)
            self._aty_cmp_relheight_hist_data.append((label, color, rh_bins, counts))
            ax_rh.hist(rel, bins=rh_bins, weights=w, histtype="stepfilled",
                       color=color, alpha=0.18, zorder=2)
            ax_rh.hist(rel, bins=rh_bins, weights=w, histtype="step",
                       color=color, linewidth=1.8, label=label, zorder=3)

    if results:
        for ax in (ax_sp, ax_rh):
            leg = ax.legend(fontsize=7.5, framealpha=0.9, facecolor=CARD_BG,
                             edgecolor="#dbe2dc", labelcolor=TEXT)
            leg.set_zorder(4)

    # ax.clear() earlier destroyed the previous hover artists -- recreate them
    # now, AFTER the real hist() data is plotted, so _aty_make_hover_artists's
    # limit re-pin locks in the correct (data-based) range rather than the
    # empty pre-plot default. Refreshes the state dicts the (already-attached,
    # see tab construction) hover handlers read from, in place.
    fresh_sp = _aty_make_hover_artists(ax_sp)
    self._aty_cmp_spacing_hover_state["vline"] = fresh_sp["vline"]
    self._aty_cmp_spacing_hover_state["annot"] = fresh_sp["annot"]
    fresh_rh = _aty_make_hover_artists(ax_rh)
    self._aty_cmp_relheight_hover_state["vline"] = fresh_rh["vline"]
    self._aty_cmp_relheight_hover_state["annot"] = fresh_rh["annot"]

    self._aty_cmp_spacing_canvas.draw_idle()
    self._aty_cmp_relheight_canvas.draw_idle()


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
        arr, ell = read_aty_signal(str(tdms))
        mm_pp = float(read_step_mm_from_tdms(str(tdms)) or 0.25)
        if arr is None or len(arr) == 0:
            self._aty_lbl_status.setText("Fehler: Kein Signal.")
            return

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
        # Cache: (db_vals, hists, arr, spots, mm_pp, fab_spans, knt_spans, ellipticity_pct)
        if tid is not None:
            self._aty_cache[tid] = (db_vals, hists, arr, spots, mm_pp, fab_spans, knt_spans, ell)

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
    """Saves to tblLaborATYoMat using the new core-baseline analysis
    (aty_core_analysis.analyze_trial), NOT the cached thick_spot_analysis
    result the Verteilung/Garnspiegel/Fabric/Knitted visuals still use --
    since 2026-08-13 the DB schema only has columns for the new metrics
    (see CLAUDE.md). Recomputed fresh here rather than cached, since only
    explicit "In DB speichern" clicks need it (cheap, ~1-2s)."""
    tid  = getattr(self,"_aty_current_trial_id",None)
    tdms = getattr(self,"_aty_current_tdms",None)
    if tid is None or tid not in self._aty_cache: return
    entry = self._aty_cache[tid]
    arr, mm_pp = entry[2], entry[4]
    ell = entry[7] if len(entry) > 7 else None
    if arr is None:
        return
    metrics = _aty_analyze_trial_core(arr, float(mm_pp), ellipticity_pct=ell)
    db_vals = _aty_to_db_row(metrics)
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
            _sb_kwargs = mw._sidebar_nav_kwargs() if hasattr(mw, "_sidebar_nav_kwargs") else None
            mw.aty_batch=ATYBatchScreen(on_back_home=lambda: mw.stack.setCurrentWidget(self),locked_series_id=sid,locked_series_name=sname,sidebar_callbacks=_sb_kwargs)
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