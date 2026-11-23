# ui/screen_tdms_inspector.py
"""Standalone TDMS file analyzer - no database required.

Lets a user pick any .tdms file from disk and run it through the DTY
and/or ATY YarnScope analysis, completely detached from any
experiment/trial/series context. Works in TRIPPLET_MODE=offline too,
since it never touches the database.

Reuses the existing tab-builder functions from ui.dty_yarnscope_tab /
ui.aty_yarnscope_tab as-is (same widgets, same analyze/plot code,
zero duplication) instead of reimplementing the charts. Those modules
were written as monkey-patch extensions of ShowExperimentScreen (see
their own docstrings + screen_show_experiment.py's
_patch_show_experiment_yarnscope()/_patch_show_experiment_aty_yarnscope()),
but internally they only ever call each other via plain module-level
function references with `self` passed in as a bare attribute holder -
never via `self.method()` - so no class-level patching is needed here,
just pre-seeding the same instance attributes ShowExperimentScreen.__init__
sets up before its own tab-builder calls.

The underlying analysis functions (read_dty_signal/read_aty_signal,
analyze_series, analyze_trial, full_extract_vals incl. the ML stability
predictions) already work standalone - a TrialID is only used for an
OPTIONAL DB feature-enrichment step (jet geometry/process params) and is
simply skipped when absent (see dty_analysis.full_extract_vals). This
screen never sets one, so that step, and the Save-to-DB/Batch buttons
(which need a trial to attach to), stay inert - hidden here rather than
left dangling.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QFileDialog,
)

from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from ui.dty_yarnscope_tab import _create_yarnscope_tab_if_needed, _ys_clear_plot
from ui.aty_yarnscope_tab import _create_aty_yarnscope_tab_if_needed


class TdmsInspectorScreen(QWidget):
    """Pick any .tdms file and analyze it with DTY and/or ATY YarnScope."""

    def __init__(self, on_back_home=None, sidebar_callbacks=None):
        super().__init__()
        self.on_back_home = on_back_home
        self._current_path: Optional[Path] = None
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None
        self._build_ui()

    def _refresh_sidebar(self):
        """Baut die Sidebar-Navigation neu auf, falls sich der Access-Level
        seit dem letzten Aufbau geändert hat, sonst nur die Badges (siehe
        ui/widgets/sidebar_nav.py::refresh_lazy_sidebar())."""
        import app_meta
        try:
            level = int((app_meta.current_user or {}).get("access_level") or 0)
        except Exception:
            level = 0
        sidebar_nav.refresh_lazy_sidebar(self, level)

    def showEvent(self, event):
        try:
            self._refresh_sidebar()
        except Exception:
            pass
        super().showEvent(event)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring).
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(24, 16, 24, 16)
        bl.setSpacing(10)

        info = QLabel(
            "Open any .tdms file and run the DTY and/or ATY YarnScope analysis "
            "on it directly - no experiment/trial needed, nothing is read from "
            "or written to the database. Stability predictions (DTY) run "
            "without the usual jet/process features, since there's no trial to "
            "look those up from; 'Compare' (ATY) needs a trial list and isn't "
            "available here."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#666;")
        bl.addWidget(info)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        self.btn_open = QPushButton("\U0001F4C2 Open TDMS file…")
        self.btn_open.setObjectName("GreenBtn")
        self.btn_open.clicked.connect(self._on_open_file)
        top_row.addWidget(self.btn_open, 0)
        # Measure with the YarnScope sensor under an own name + speed (Nutzerwunsch 2026-11-23,
        # ui/widgets/sensor_measure_dialog.py free mode); the new file is opened here.
        self.btn_measure = QPushButton("📏 Measure…")
        self.btn_measure.setToolTip("Measure with the YarnScope sensor (NI box) under your own name and speed - "
                                    "the file opens here")
        self.btn_measure.clicked.connect(self._on_measure)
        top_row.addWidget(self.btn_measure, 0)
        self.lbl_current_file = QLabel("No file selected.")
        self.lbl_current_file.setStyleSheet("color:#666;")
        top_row.addWidget(self.lbl_current_file, 1)
        bl.addLayout(top_row)

        # ---- Attributes the reused DTY/ATY tab-builders expect to exist
        # (same list as ShowExperimentScreen.__init__ pre-seeds before its
        # own _create_..._tab_if_needed() calls - kept in sync manually). ----
        self.tabs = QTabWidget()

        self.tab_yarnscope = None
        self._ys_trial_list = None
        self._ys_current_trial_id = None
        self._ys_cache: dict = {}
        self._ys_current_tdms = None
        self._ys_last_res: dict = {}
        self._ys_last_vals: dict = {}
        self._ys_sigs = None
        self._ys_spin_start = None
        self._ys_spin_window = None
        # Pre-set: prevents the tab builder's 20s TDMS-folder auto-refresh
        # timer from ever starting (it exists to re-scan a series' network
        # TDMS folder, which has no meaning here - see
        # _ys_update_auto_refresh_state() in dty_yarnscope_tab.py).
        self._ys_all_tdms_present = True

        self.tab_aty_yarnscope = None
        self._aty_trial_list = None
        self._aty_current_trial_id = None
        self._aty_current_tdms = None
        self._aty_cache: dict = {}
        self._aty_core_cache: dict = {}
        self._aty_raw_cache: dict = {}
        self._aty_histograms: dict = {}
        # Same reasoning as _ys_all_tdms_present above.
        self._aty_all_tdms_present = True

        _create_yarnscope_tab_if_needed(self)
        _create_aty_yarnscope_tab_if_needed(self)

        # Hide the (permanently empty, since we never populate it) trial-list
        # panel and the DB-only Save/Batch buttons on both tabs - this screen
        # never has a trial to attach either to.
        for trial_list, save_btn, batch_btn in (
            (self._ys_trial_list, self._ys_btn_save, self._ys_btn_batch),
            (self._aty_trial_list, self._aty_btn_save, self._aty_btn_batch),
        ):
            if trial_list is not None and trial_list.parentWidget() is not None:
                trial_list.parentWidget().setVisible(False)
            if save_btn is not None:
                save_btn.setVisible(False)
            if batch_btn is not None:
                batch_btn.setVisible(False)

        bl.addWidget(self.tabs, 1)
        content_layout.addWidget(body, 1)
        root.addWidget(FooterBar())

    def _go_home(self):
        if callable(self.on_back_home):
            self.on_back_home()

    # --------------------------------------------------------------- Logic
    def _on_open_file(self):
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Open TDMS file", "", "TDMS files (*.tdms);;All files (*)")
        if not path_str:
            return
        self._open_path(Path(path_str))

    def _on_measure(self):
        import app_meta
        from ui.widgets.sensor_measure_dialog import SensorMeasureDialog
        old = getattr(self, "_sensor_dlg", None)
        try:
            if old is not None and old.isVisible():
                old.raise_()
                return
        except RuntimeError:
            pass
        dlg = SensorMeasureDialog(None, getattr(app_meta, "current_user", {}) or {}, self, free=True,
                                  on_measured=lambda path: self._open_path(Path(path)))
        dlg.setModal(False)                        # stays open beside the inspector (like Show Experiment)
        dlg.setAttribute(Qt.WA_DeleteOnClose, True)
        self._sensor_dlg = dlg
        dlg.show()

    def _open_path(self, path: Path):
        """Shows a TDMS file in both tabs (file dialog or a fresh measurement)."""
        self._current_path = path
        self.lbl_current_file.setText(f"\U0001F4C4 {path}")

        # Mirrors what _ys_on_trial_selected()/_aty_on_trial_selected() do
        # when a list item is clicked, minus the trial-id/cache bookkeeping
        # - there is no trial here, trial_id stays None throughout.
        self._ys_current_trial_id = None
        self._ys_current_tdms = path
        self._ys_lbl_file.setText(f"\U0001F4C4 {path.name}")
        self._ys_btn_analyze.setEnabled(True)
        self._ys_last_res = {}
        self._ys_last_vals = {}
        self._ys_lbl_status.setText("")
        self._ys_lbl_metrics.setText("")
        _ys_clear_plot(self)

        self._aty_current_trial_id = None
        self._aty_current_tdms = path
        self._aty_lbl_file.setText(f"\U0001F4C4 {path.name}")
        self._aty_btn_analyze.setEnabled(True)
        self._aty_lbl_status.setText("")
        self._aty_lbl_metrics.setText("")
        self._aty_histograms = {}
