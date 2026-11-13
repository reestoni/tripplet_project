"""dty_yarnscope_tab.py - YarnScope (DTY) Tab fuer TrippleT.

Enthaelt alle Funktionen, die am Ende von screen_show_experiment.py via
Monkey-Patching auf ShowExperimentScreen registriert werden (siehe dort
_patch_show_experiment_yarnscope()). Ausgelagert aus screen_show_experiment.py
(reiner Code-Move, keine Verhaltensaenderung) - analog zu aty_yarnscope_tab.py,
das denselben Aufbau fuer den ATY-Tab bereits verwendet.

Alle Berechnungen (TDMS-Suche, Analyse, Trends, Prozesswelle, Vergleich,
Garnspiegel-Daten, Speichern) liegen Qt-frei in ui/yarnscope/dty_service.py,
das auch die Web-Version benutzt - hier bleiben nur Widgets und Zeichnen.
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
from ui.yarnscope import dty_service as _svc
from ui.pathutil import resource_path
from ui.widgets.friendly_error import show_error


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
    return _svc.tdms_base()


# Reine Berechnungen liegen Qt-frei in ui/yarnscope/dty_service.py (gemeinsam
# mit der Web-Version); die alten Namen bleiben als Aliase erhalten.
_ys_open_knot_midpoints = _svc.open_knot_midpoints
_ys_opening_segment_series = _svc.opening_segment_series
_ys_rolling_mean = _svc.rolling_mean
_ys_rolling_mean_by_distance = _svc.rolling_mean_by_distance
_ys_roll_trend = _svc.roll_trend
_ys_local_extrema = _svc.local_extrema
_ys_trend_metrics = _svc.trend_metrics
_ys_analyze_process_wave = _svc.analyze_process_wave
_ys_process_wave_reality_check = _svc.process_wave_reality_check


def _ys_update_process_wave_card(label, analysis, enabled):
    if label is None:
        return
    label.setVisible(bool(enabled))
    if not enabled:
        return
    if analysis is None:
        label.setText('<b style="color:#ffd166">Process wave</b><br>Not enough data for this window size.')
        return
    label.setText(
        '<b style="color:#ffd166">Prozesswelle</b> &nbsp; '
        f'<span style="color:#aaa">Grid {analysis["bin_width"]:.2f} m · '
        f'Window {analysis["span"]:.1f} m</span><br>'
        f'Dominant wavelength <b>{analysis["wavelength"]:.2f} m</b> &nbsp; '
        f'Sine amplitude <b>{analysis["amplitude"]:.2f} µm</b> &nbsp; '
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
        label.setText(f'<b style="color:{color}">{title}</b><br>No trend values in the visible window.')
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
        f'Δ end <b>{_number(metrics["end_delta"])} µm</b> &nbsp; '
        f'Wavelength <b>{_number(metrics["wavelength"], 2, " m")}</b> &nbsp; '
        f'Wave CV <b>{_number(wave_cv, 0, " %")}</b><br>'
        f'Peak–Tal Median <b>{_number(metrics["peak_to_peak"])} µm</b> &nbsp; '
        f'P95 <b>{_number(metrics["peak_to_peak_p95"])} µm</b>')


_ys_peak_valley_midpoints = _svc.peak_valley_midpoints
_ys_series_has_tdms = _svc.series_has_tdms
_ys_find_tdms = _svc.find_tdms
_ys_extract_vals = _svc.extract_basic_vals


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

    ctrl_row.addWidget(QLabel("Window [m]:"))
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
        "Shows the rolling centre line between the height of an open spot and the height of the following "
        "knot in the segment mean plot.")
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
        "Width of the moving average – in metres or in consecutive open spot–knot pairs.")
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
        "Shows the rolling centre line between a local peak and the following valley in the segment "
        "mean plot.")
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
        "Width of the moving average – in metres or in consecutive peak–valley pairs.")
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

    self._ys_chk_opening_trend = QCheckBox("Open spot trend")
    self._ys_chk_opening_trend.setToolTip(
        "Shows the rolling centre line ONLY over the green open spot segment means in the segment "
        "mean plot, without knots (unlike 'Centre open spot–knot', which mixes open spots AND knots).")
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
        "Width of the moving average – in metres or in consecutive open spots.")
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
    self._ys_chk_process_wave = QCheckBox("Analyse process wave")
    self._ys_chk_process_wave.setToolTip(
        "Determines a spatially binned centre line, its dominant wave and a sine fit. Use a longer "
        "window (e.g. 30–100 m) for a reliable comparison.")
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
        "Spatial bin width for the process mean line. Smaller values show more detail, larger values "
        "smooth more.")
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
        "Centres each trial on its process mean median, so the shape is compared and not the absolute "
        "difference in thickness.")
    self._ys_chk_compare_normalized.setStyleSheet("QCheckBox,QCheckBox:disabled{color:#fff;}")
    compare_left_layout.addWidget(self._ys_chk_compare_normalized)
    self._ys_chk_compare_show_process_mean = QCheckBox("Show process mean")
    self._ys_chk_compare_show_process_mean.setChecked(False)
    self._ys_chk_compare_show_process_mean.setToolTip(
        "Also shows the binned base line. It is hidden by default for a clear comparison of several "
        "trials.")
    self._ys_chk_compare_show_process_mean.setStyleSheet("QCheckBox,QCheckBox:disabled{color:#fff;}")
    compare_left_layout.addWidget(self._ys_chk_compare_show_process_mean)
    self._ys_chk_compare_show_drift = QCheckBox("Show drift lines")
    self._ys_chk_compare_show_drift.setChecked(False)
    self._ys_chk_compare_show_drift.setToolTip(
        "Shows the linear regression over the whole visible window per trial. It corresponds to the "
        "drift value in µm/m.")
    self._ys_chk_compare_show_drift.setStyleSheet("QCheckBox,QCheckBox:disabled{color:#fff;}")
    compare_left_layout.addWidget(self._ys_chk_compare_show_drift)
    self._ys_chk_compare_open_trend = QCheckBox("Open spot trend")
    self._ys_chk_compare_open_trend.setChecked(False)
    self._ys_chk_compare_open_trend.setToolTip(
        "Shows per trial the rolling centre line ONLY over the green open spot segment means (as "
        "in the segment mean tab), without knots. For trials not analysed in the segment mean tab "
        "yet, the classification is calculated once when comparing (may take a moment).")
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
        "Width of the moving average – in metres or in consecutive open spots.")
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
    self._ys_lbl_compare_status = QLabel("Choose two to six trials – always evaluated over the whole measured length.")
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
    # Reference samples (customer originals) never have a TDMS file -
    # listing them would also keep the auto-refresh timer running forever.
    refs = getattr(self, "_reference_names", {}) or {}
    for entry in _svc.trial_files(sid, self._trials, refs, with_analysed=True):
        tid = entry["trial_id"]
        vno = entry["vno"]
        tdms = entry["tdms"]
        if not tdms:
            all_have_tdms = False
        icon = "📄" if tdms else "—"
        db_ok = entry["analysed"]
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
    for entry in _svc.trial_files(sid, getattr(self, "_trials", []), refs):
        trial_id = entry["trial_id"]
        vno = entry["vno"]
        tdms = entry["tdms"]
        item = QListWidgetItem(f"V{int(vno):03d}" + ("" if tdms else "  (no TDMS)"))
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
        self._ys_lbl_compare_status.setText("Please choose at least two trials.")
        return
    if len(selected) > 6:
        self._ys_lbl_compare_status.setText("Please compare at most six trials at once.")
        return

    bin_width = float(self._ys_spin_process_wave_bin.value()
                      if self._ys_spin_process_wave_bin else 0.05)
    self._ys_btn_run_comparison.setEnabled(False)
    self._ys_lbl_compare_status.setText("Loading and analysing the whole measured lengths…")

    class _Sigs(QObject):
        done = _Signal(object, str)

    class _Worker(QRunnable):
        def __init__(self, trials, bin_m, cache, sigs):
            super().__init__()
            self._trials, self._bin_m = trials, bin_m
            self._cache, self._sigs = cache, sigs
            self.setAutoDelete(True)

        def run(self):
            results, errors = _svc.run_process_comparison(
                self._trials, self._bin_m, self._cache)
            self._sigs.done.emit(results, errors)

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
    self._ys_lbl_compare_status.setText(_svc.comparison_status_text(results, errors))


# Linienstil je Kurvenart des Prozessvergleichs (Daten: _svc.comparison_traces)
_YS_COMPARE_LINE_STYLE = {
    "process_mean": dict(linewidth=1.0, alpha=0.45),
    "drift": dict(linewidth=1.25, alpha=0.9),
    "sine_fit": dict(linewidth=2.1, linestyle="--"),
    "open_trend": dict(linewidth=1.6, linestyle=":"),
}


def _ys_draw_process_comparison(self, results):
    """Zeichnet Prozessmittel und Sinus-Fits überlagert sowie die Kennzahlentabelle."""
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
    colors = _svc.COMPARE_COLOURS
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

    for trace in _svc.comparison_traces(results, normalized, show_process_mean, show_drift,
                                        show_open_trend, open_roll_mode, open_roll_amount):
        ax.plot(trace["x"], trace["y"], color=trace["colour"], label=trace["label"],
                **_YS_COMPARE_LINE_STYLE[trace["kind"]])

    for row, result in enumerate(results):
        color = colors[row % len(colors)]
        visible = result.get("visible", True)

        table.insertRow(row)
        visibility_icon = "assets/images/visible_on.png" if visible else "assets/images/visible_off.png"
        visibility_button = QPushButton()
        visibility_button.setFixedWidth(30)
        visibility_button.setIcon(QIcon(resource_path(visibility_icon)))
        visibility_button.setIconSize(QSize(18, 18))
        visibility_button.setToolTip(
            "Hide trial in the chart" if visible else "Show trial in the chart")
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
        values = _svc.comparison_table_values(result)
        for col, value in enumerate(values, start=2):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignCenter)
            if col == 2:
                item.setForeground(QColor(color))
            elif col == 14:
                item.setForeground(QColor(_svc.VERDICT_COLOURS.get(value, "#aaa")))
            table.setItem(row, col, item)

    if results:
        axis = _svc.comparison_axis_labels(normalized, show_process_mean)
        ax.set_title(axis["title"], color="#ddd", fontsize=11)
        ax.set_xlabel(axis["xlabel"], color="#aaa", fontsize=9)
        ax.set_ylabel(axis["ylabel"], color="#aaa", fontsize=9)
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
        ax.text(0.5, 0.5, "Choose at least two trials and compare.",
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
        self._ys_lbl_file.setText(f"V{vno} – no TDMS file in the folder")
        self._ys_btn_analyze.setEnabled(False)
    # Cache-Treffer: sofort anzeigen, kein Klick auf Analysieren noetig
    if tid is not None and tid in self._ys_cache:
        res, vals = self._ys_cache[tid]
        self._ys_last_res = res
        self._ys_last_vals = vals
        self._ys_lbl_status.setText("Analysis from cache.")
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
        self._ys_lbl_status.setText("Analysis from cache.")
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
                res = _svc.analyse_signal_file(self._p)
                self._s.done.emit(res, "")
            except Exception as e:
                self._s.done.emit({}, str(e))

    self._ys_sigs = _Sigs()
    self._ys_sigs.done.connect(lambda res, err: _ys_on_analysis_done(self, res, err))
    QThreadPool.globalInstance().start(_Worker(self._ys_current_tdms, self._ys_sigs))


def _ys_on_analysis_done(self, res: dict, err: str):
    self._ys_btn_analyze.setEnabled(True)
    if err:
        self._ys_lbl_status.setText(f"Error: {err}");
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
            vals = _svc.extract_values(
                self._r, trial_id=self._tid,
                progress_cb=lambda msg: self._s.progress.emit(msg))
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
    self._ys_lbl_status.setText(_svc.analysis_status_text(vals))
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
        import math
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.figure import Figure

        def _trend_setting(chk, combo, spin):
            """None = Linie aus, sonst (Rollungsart, Breite) aus den Widgets."""
            if not bool(getattr(self, chk, None) and getattr(self, chk).isChecked()):
                return None
            combo_w, spin_w = getattr(self, combo), getattr(self, spin)
            return ((combo_w.currentText() if combo_w else "Meter"),
                    float(spin_w.value() if spin_w else 1.0))

        process_wave_bin = None
        if bool(getattr(self, "_ys_chk_process_wave", None)
                and self._ys_chk_process_wave.isChecked()):
            process_wave_bin = float(self._ys_spin_process_wave_bin.value()
                                     if self._ys_spin_process_wave_bin else 0.05)

        # Start/Fenster aus Spinboxes
        view = _svc.segment_view(
            res, vals,
            float(self._ys_spin_start.value() if self._ys_spin_start else 0.0),
            float(self._ys_spin_window.value() if self._ys_spin_window else 3.0),
            open_knot=_trend_setting("_ys_chk_delta_trend", "_ys_combo_delta_roll_mode",
                                     "_ys_spin_delta_roll"),
            peak_valley=_trend_setting("_ys_chk_peak_valley_trend",
                                       "_ys_combo_peak_valley_roll_mode",
                                       "_ys_spin_peak_valley_roll"),
            opening=_trend_setting("_ys_chk_opening_trend", "_ys_combo_opening_roll_mode",
                                   "_ys_spin_opening_roll"),
            process_wave_bin=process_wave_bin)
        if view is None:
            lbl = QLabel("No signal available.")
            lbl.setStyleSheet("color:#ff6060; padding:8px;")
            self._ys_plot_layout.addWidget(lbl)
            return

        total_m = view["total_m"]
        start_m, window_m = view["start_m"], view["window_m"]

        # Spinbox-Max anpassen
        if self._ys_spin_start:
            self._ys_spin_start.blockSignals(True)
            self._ys_spin_start.setMaximum(max(0.0, total_m - 0.1))
            self._ys_spin_start.blockSignals(False)

        x_axis, y_smooth = view["x"], view["y_smooth"]
        T, y_cb, y_ba = view["threshold"], view["y_cb"], view["y_ba"]
        open_segs, knot_segs = view["open_segments"], view["knot_segments"]
        trends = view["trends"]
        open_knot_enabled = trends["open_knot"]["enabled"]
        open_knot_trend_x = trends["open_knot"]["x"]
        open_knot_trend_y = trends["open_knot"]["y"]
        open_knot_roll_label = trends["open_knot"]["roll_label"]
        peak_valley_enabled = trends["peak_valley"]["enabled"]
        peak_valley_trend_x = trends["peak_valley"]["x"]
        peak_valley_trend_y = trends["peak_valley"]["y"]
        peak_valley_roll_label = trends["peak_valley"]["roll_label"]
        opening_enabled = trends["opening"]["enabled"]
        opening_trend_x = trends["opening"]["x"]
        opening_trend_y = trends["opening"]["y"]
        opening_roll_label = trends["opening"]["roll_label"]
        process_wave = view["process_wave"]
        process_wave_enabled = view["process_wave_enabled"]

        _ys_update_trend_metric_card(
            getattr(self, "_ys_lbl_open_knot_metrics", None), "Centre open spot–knot",
            "#56d7d0", open_knot_enabled, open_knot_trend_x, open_knot_trend_y)
        _ys_update_trend_metric_card(
            getattr(self, "_ys_lbl_peak_valley_metrics", None), "Mitte Peak–Tal",
            "#ff6bb5", peak_valley_enabled, peak_valley_trend_x, peak_valley_trend_y)
        _ys_update_trend_metric_card(
            getattr(self, "_ys_lbl_opening_metrics", None), "Open spot trend",
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

        seen = set()
        COLOR = _svc.COLOR_ABC

        for g, mv in open_segs:
            lbl = "Opening: medium" if "Opening: medium" not in seen else None
            ax.plot(x_axis[g], [mv] * len(g), color="#39A650", linewidth=1.8, label=lbl)
            if lbl: seen.add(lbl)

        for (g, mv), cls in zip(knot_segs, view["knot_classes"]):
            col = COLOR[cls]
            lbl_key = f"Knoten {cls}: Mittel"
            lbl = lbl_key if lbl_key not in seen else None
            ax.plot(x_axis[g], [mv] * len(g), color=col, linewidth=2.0, label=lbl)
            if lbl: seen.add(lbl)
        A_cnt, B_cnt, C_cnt = view["counts"]["A"], view["counts"]["B"], view["counts"]["C"]

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
                    label=f"Centre open spot–knot (rolling Ø {open_knot_roll_label})")
            if peak_valley_trend_x:
                ax.plot(
                    peak_valley_trend_x, peak_valley_trend_y, color="#ff6bb5", linewidth=1.8,
                    label=f"Mitte Peak–Tal (roll. Ø {peak_valley_roll_label})")
            if opening_trend_x:
                ax.plot(
                    opening_trend_x, opening_trend_y, color="#8de6a0", linewidth=1.8,
                    label=f"Open spot trend (rolling Ø {opening_roll_label})")

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
        a, b, c = view["pie"]["A"], view["pie"]["B"], view["pie"]["C"]
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
        lbl = QLabel(f"Plot error: {e}")
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
        self._ys_lbl_status.setText(f"Error: {e}");
        return
    if ok:
        self._ys_lbl_status.setText("Gespeichert.")
        self._ys_btn_save.setEnabled(False)
        _ys_populate_trial_list(self)
    else:
        self._ys_lbl_status.setText("Saving failed.")


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
        show_error(self, "Batch", "The batch analysis stopped.", e)


def _ys_draw_garnspiegel(self, res: dict, vals: dict = None):
    """Zeichnet den Garnspiegel mit ABC-Knoten-Einfaerbung ab aktuellem Startpunkt."""
    canvas = getattr(self, "_ys_garn_canvas", None)
    if canvas is None:
        return
    try:
        # ── Startpunkt aus Spinbox (identisch zum Segmentmittel-Plot) ────────
        start_m = float(getattr(self, "_ys_spin_start", None) and self._ys_spin_start.value() or 0.0)
        # Daten (Signal ab Startpunkt, Knotenläufe, Klassen) aus dty_service
        kwargs = _svc.garnspiegel_inputs(res, start_m)
        if kwargs is None:
            return
        canvas.plot_garnspiegel_dty(**kwargs)
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
        import math

        start_m = float(self._ys_spin_start.value() if self._ys_spin_start else 0.0)
        window_m = float(self._ys_spin_window.value() if self._ys_spin_window else 3.0)
        view = _svc.signal_view(res, start_m, window_m)
        if view is None:
            ax.clear();
            canvas.draw_idle();
            return

        yseg, x_abs, step_m = view["y"], view["x"], view["step_m"]
        T, y_ab, y_bc = view["threshold"], view["y_ab"], view["y_bc"]

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
        ylim, xlim = _svc.signal_limits(view)
        ax.set_ylim(*ylim)
        ax.set_xlim(*xlim)

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
        QMessageBox.warning(self, 'Error', str(e))

