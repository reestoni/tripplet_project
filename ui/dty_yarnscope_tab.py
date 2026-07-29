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

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
)

from ui.yarnscope.garngraf_canvas import GarnCanvas


# ===========================================================================
# YarnScope – Hilfsfunktionen (Modul-Level)
# ===========================================================================

def _ys_tdms_base():
    from pathlib import Path
    return Path(r"H:\Technik\TrippleT\YarnScopeTDMS")


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
    idx = self.tabs.indexOf(self.tab_yarnscope)
    if idx != -1:
        self.tabs.removeTab(idx)
    self.tab_yarnscope.deleteLater()
    self.tab_yarnscope = None
    self._ys_trial_list = None


def _create_yarnscope_tab_if_needed(self):
    from PySide6.QtWidgets import QSplitter, QListWidget, QListWidgetItem, QDoubleSpinBox
    from PySide6.QtCore import Qt
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
    self._ys_spin_window.setRange(0.1, 3.0);
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
    root.addWidget(splitter, 1)
    self.tabs.addTab(self.tab_yarnscope, "YarnScope")


def _ys_populate_trial_list(self):
    from PySide6.QtWidgets import QListWidgetItem
    from PySide6.QtCore import Qt
    # Lazy import (vermeidet Zirkularimport, screen_show_experiment importiert
    # dieses Modul selbst) - derselbe fetch_all-Wrapper wie vorher.
    from ui.screen_show_experiment import fetch_all
    if self._ys_trial_list is None:
        return
    self._ys_trial_list.blockSignals(True)
    self._ys_trial_list.clear()
    sid = self._series_pk
    for t in self._trials:
        tid = t.get("ID")
        vno = t.get("Versuchsnummer") or t.get("versuchsnummer") or 0
        tdms = _ys_find_tdms(sid, int(vno)) if sid else None
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
    self._ys_trial_list.blockSignals(False)


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
                    read_first_numeric_channel, read_step_mm_from_tdms)
                y = read_first_numeric_channel(str(self._p))
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
    if not self._ys_last_res:
        return
    active = getattr(self, "_ys_sub_tabs", None)
    active_idx = active.currentIndex() if active else 0
    # Segmentmittel immer
    _ys_draw_plots(self, self._ys_last_res, self._ys_last_vals)
    # Garnspiegel + Signal nur wenn Tab sichtbar, sonst lazy beim Tab-Wechsel
    if active_idx == 1:
        _ys_draw_garnspiegel(self, self._ys_last_res, getattr(self, "_ys_last_vals", {}))
    elif active_idx == 2:
        _ys_draw_signal(self, self._ys_last_res)
    # Flag setzen damit Tab-Wechsel weiss was noch gezeichnet werden muss
    self._ys_plots_dirty = True


def _ys_update_metrics(self, vals: dict):
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
        window_m = max(0.1, min(window_m, 3.0, total_m - start_m))

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

        # ── Figure: Segmentmittel (gross) + ABC-Pie (klein rechts) ────────
        fig = Figure(facecolor="#242424")
        # 2 Spalten: Segmentmittel 82%, Pie 18%
        gs = fig.add_gridspec(1, 2, width_ratios=[5, 1],
                              left=0.05, right=0.98, top=0.90, bottom=0.12, wspace=0.05)
        ax = fig.add_subplot(gs[0])
        axp = fig.add_subplot(gs[1])

        ax.set_facecolor("#2e2e2e")
        ax.plot(x_axis, y_smooth, color="#c9d2e3", linewidth=0.7, alpha=0.7)

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
            mw.tdms_batch = TDMSBatchScreen(
                on_back_home=lambda: mw.stack.setCurrentWidget(self),
                locked_series_id=sid,
                locked_series_name=sname,
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

