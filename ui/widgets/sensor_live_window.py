"""sensor_live_window.py - "YarnScope Live" window (Nutzerwunsch 2026-11-23; web /tools/yarnscope-live).

Continuous measurement with a small dashboard: start / stop by hand, every window (default 30 m) knots/m + CV per
sensor and, with a second sensor + the distance, the measured speed; optionally saved to the _manual folder.
Logic: ui/yarnscope/sensor_live.py (shared with the web). Opened from the sidebar (Tools) - one window, not modal.
Bookmarks (Nutzerwunsch 2026-11-24): "Bookmark" keeps the last N m (default 100) in memory, no input; on a bookmark
"Create trial..." copies a template trial with jet / pressure / OF / speed (ui/yarnscope/live_trial.py) and, only if
ticked, saves the bookmark as that trial's TDMS; "Save as file..." writes it to _manual.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QFrame, QGridLayout,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMessageBox, QPushButton, QRadioButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from ui.widgets.sensor_measure_dialog import error_text
from ui.yarnscope import live_trial
from ui.yarnscope import sensor_live as sl
from ui.yarnscope import sensor_measure as sm
from ui.yarnscope.sensor_pair import DEFAULT_DISTANCE_MM as _DEFAULT_DISTANCE

COLORS = ["#1d983a", "#2a78d6"]
STATE_TEXT = {"running": "Measuring", "stopping": "Stopping…", "done": "Finished", "error": "Error", "new": "Starting…"}

_window: Optional["SensorLiveWindow"] = None


def open_window(user: Optional[Dict[str, Any]] = None, parent: Optional[QWidget] = None) -> "SensorLiveWindow":
    """The one live window (created on first use, then raised)."""
    global _window
    if _window is None:
        _window = SensorLiveWindow(user, parent)
    _window.show()
    _window.raise_()
    _window.activateWindow()
    return _window


def y_range(vals, rel: float, floor=None):
    """Y axis with a MINIMUM span (like the web page): knots/m >= +-10 % of the mean, CV >= 0..40 %, speed >= +-3 %,
    so 0.5 knots more does not look like a jump (user 2026-11-23). None = nothing to show."""
    v = [x for x in vals if x is not None]
    if not v:
        return floor
    lo, hi = min(v), max(v)
    if floor:
        lo, hi = min(lo, floor[0]), max(hi, floor[1])
    mid = (lo + hi) / 2
    half = max((hi - lo) / 2 * 1.15, abs(sum(v) / len(v)) * rel, 1e-9)
    return (max(floor[0], mid - half) if floor else mid - half, mid + half)


def _head_label(h: str) -> str:
    p = h.split("_")
    return f"{p[0]} {p[1]}-{p[2]}" if len(p) >= 3 else h


class SensorLiveWindow(QWidget):
    def __init__(self, user: Optional[Dict[str, Any]] = None, parent: Optional[QWidget] = None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("TrippleT – YarnScope Live")
        self.resize(1100, 720)
        self.user = user or {}
        try:
            self.read_only = int(self.user.get("access_level") or 0) < 2
        except (TypeError, ValueError):
            self.read_only = True
        self._settings = QSettings("TrippleT", "SensorLive")
        self._shown = 0
        root = QHBoxLayout(self)

        # ---- left: settings
        left = QVBoxLayout()
        info = QLabel("Continuous measurement: start and stop by hand. Every window shows knots/m and CV per sensor "
                      "and - with a second sensor and the distance - the measured speed.")
        info.setWordWrap(True)
        info.setStyleSheet("color:#555;")
        left.addWidget(info)
        form = QFormLayout()
        row = QHBoxLayout()
        self.cb_box = QComboBox()
        btn = QPushButton("↻")
        btn.setFixedWidth(32)
        btn.clicked.connect(self._load_boxes)
        row.addWidget(self.cb_box, 1)
        row.addWidget(btn)
        form.addRow("Box:", row)
        self.cb_sensor = QComboBox()
        self.cb_sensor.currentIndexChanged.connect(lambda _i: self._fill_second())
        form.addRow("Sensor:", self.cb_sensor)
        self.cb_second = QComboBox()
        self.cb_second.currentIndexChanged.connect(lambda _i: self._sync())
        form.addRow("2nd sensor at once:", self.cb_second)
        self.sp_distance = QDoubleSpinBox()
        self.sp_distance.setRange(0, 100000)
        self.sp_distance.setDecimals(1)
        self.sp_distance.setSuffix(" mm")
        self.sp_distance.setSpecialValueText("– (only the delay)")
        self.sp_distance.setValue(float(self._settings.value("distance", _DEFAULT_DISTANCE) or 0))
        form.addRow("Distance:", self.sp_distance)
        # two sensors + distance: TrippleT measures the speed itself (no speed typed, Nutzerwunsch 2026-11-23)
        self.ck_auto = QCheckBox("Measure the speed (from the two sensors and their distance)")
        self.ck_auto.setChecked(str(self._settings.value("auto", "true")).lower() != "false")
        self.ck_auto.toggled.connect(lambda _c: self._sync())
        self.sp_distance.valueChanged.connect(lambda _v: self._sync())
        form.addRow("", self.ck_auto)
        self.sp_speed = QDoubleSpinBox()
        self.sp_speed.setRange(*sm.SPEED_RANGE)
        self.sp_speed.setDecimals(1)
        self.sp_speed.setSuffix(" m/min")
        self.sp_speed.setValue(float(self._settings.value("speed", 600) or 600))
        form.addRow("Speed:", self.sp_speed)
        self.sp_window = QDoubleSpinBox()
        self.sp_window.setRange(*sl.WINDOW_RANGE)
        self.sp_window.setDecimals(0)
        self.sp_window.setSuffix(" m")
        self.sp_window.setValue(float(self._settings.value("window", sl.WINDOW_M) or sl.WINDOW_M))
        form.addRow("Value every:", self.sp_window)
        srow = QHBoxLayout()
        self.ck_save = QCheckBox("Save")
        self.ck_save.setChecked(str(self._settings.value("save", "true")).lower() != "false")
        self.ed_name = QLineEdit(str(self._settings.value("name", "99999_live")))
        self.ed_name.setMaxLength(60)
        self.rb_dty, self.rb_aty = QRadioButton("DTY"), QRadioButton("ATY")
        (self.rb_aty if self._settings.value("kind") == "aty" else self.rb_dty).setChecked(True)
        for w in (self.ck_save, self.ed_name, self.rb_dty, self.rb_aty):
            srow.addWidget(w)
        form.addRow("", srow)
        left.addLayout(form)
        # empty value (no yarn) before the start - the same remembered value as the measure window (2026-11-24)
        zrow = QHBoxLayout()
        self.btn_zero = QPushButton("Check empty value (no yarn)")
        self.btn_zero.clicked.connect(self._on_zero)
        zrow.addWidget(self.btn_zero)
        left.addLayout(zrow)
        self.lbl_zero = QLabel("–")
        self.lbl_zero.setWordWrap(True)
        left.addWidget(self.lbl_zero)
        self.cb_box.currentIndexChanged.connect(lambda _i: self._show_zero())
        self.cb_sensor.currentIndexChanged.connect(lambda _i: self._show_zero())
        self.cb_second.currentIndexChanged.connect(lambda _i: self._show_zero())
        hint = QLabel(f"Saved piece by piece to the sub-folder '{sm.MANUAL_DIR}' (the automatic analysis ignores it), "
                      f"at most {sl.SAVE_LIMIT_M:.0f} m.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#777;font-size:11px;")
        left.addWidget(hint)
        brow = QHBoxLayout()
        self.btn_start = QPushButton("▶ Start")
        self.btn_start.setMinimumHeight(34)
        self.btn_start.setStyleSheet("QPushButton{background:#39A650;color:white;font-weight:bold;padding:0 18px;}"
                                     "QPushButton:disabled{background:#b9d9c0;}")
        self.btn_start.clicked.connect(self._on_start)
        self.btn_stop = QPushButton("■ Stop")
        self.btn_stop.setMinimumHeight(34)
        self.btn_stop.setStyleSheet("QPushButton{background:#c0392b;color:white;font-weight:bold;padding:0 18px;}"
                                    "QPushButton:disabled{background:#e6b0aa;}")
        self.btn_stop.clicked.connect(self._on_stop)
        brow.addWidget(self.btn_start)
        brow.addWidget(self.btn_stop)
        left.addLayout(brow)
        self.lbl_msg = QLabel("")
        self.lbl_msg.setWordWrap(True)
        left.addWidget(self.lbl_msg)
        left.addStretch(1)
        lw = QWidget()
        lw.setLayout(left)
        lw.setFixedWidth(380)
        root.addWidget(lw)

        # ---- right: dashboard
        right = QVBoxLayout()
        self.lbl_status = QLabel("No live measurement running.")
        right.addWidget(self.lbl_status)
        self.tiles = QGridLayout()
        right.addLayout(self.tiles)
        self._tile_labels: List[QLabel] = []
        # one chart at full size (2026-11-24): buttons above the charts or a double click on a chart; Back / Esc returns
        self._focus: Optional[str] = None
        self._ax_keys: List[tuple] = []
        zrow = QHBoxLayout()
        self._zoom_btns: Dict[str, QPushButton] = {}
        for key, title in (("fpm", "Knots/m"), ("cv", "CV"), ("speed", "Speed")):
            b = QPushButton(f"⤢ {title}")
            b.setToolTip("Show this chart at full size (or double-click the chart)")
            b.clicked.connect(lambda _c=False, k=key: self._set_focus(k))
            zrow.addWidget(b)
            self._zoom_btns[key] = b
        self.btn_unzoom = QPushButton("✕ Back (Esc)")
        self.btn_unzoom.clicked.connect(lambda: self._set_focus(None))
        self.btn_unzoom.setVisible(False)
        zrow.addWidget(self.btn_unzoom)
        zrow.addStretch(1)
        right.addLayout(zrow)
        self._fig = None
        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
            self._fig = Figure(figsize=(7, 2.4), tight_layout=True)
            self._canvas = FigureCanvasQTAgg(self._fig)
            self._canvas.mpl_connect("button_press_event", self._on_chart_click)
            right.addWidget(self._canvas, 1)
        except Exception:  # noqa: BLE001 - the table is enough then
            self._canvas = None
        self.table = QTableWidget(0, 0)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        right.addWidget(self.table, 1)
        # ---- bookmarks: one click while tuning, a trial from it afterwards
        bm = QHBoxLayout()
        self.btn_mark = QPushButton("📌 Bookmark")
        self.btn_mark.setMinimumHeight(30)
        self.btn_mark.setToolTip("Keeps the last metres of the signal in memory (nothing is saved yet)")
        self.btn_mark.clicked.connect(self._on_bookmark)
        self.sp_mark = QDoubleSpinBox()
        self.sp_mark.setRange(*sl.BOOKMARK_RANGE)
        self.sp_mark.setDecimals(0)
        self.sp_mark.setSuffix(" m")
        self.sp_mark.setValue(float(self._settings.value("bookmark_m", sl.BOOKMARK_M) or sl.BOOKMARK_M))
        self.sp_mark.setToolTip("Length of a bookmark: the last … metres")
        self.btn_trial = QPushButton("Create trial…")
        self.btn_trial.clicked.connect(self._on_trial)
        self.btn_file = QPushButton("Save as file…")
        self.btn_file.clicked.connect(self._on_file)
        self.btn_unmark = QPushButton("Delete")
        self.btn_unmark.clicked.connect(self._on_unmark)
        for w in (self.btn_mark, QLabel("last"), self.sp_mark):
            bm.addWidget(w)
        bm.addStretch(1)
        for w in (self.btn_trial, self.btn_file, self.btn_unmark):
            bm.addWidget(w)
        right.addLayout(bm)
        self.bm_table = QTableWidget(0, 8)
        self.bm_table.setHorizontalHeaderLabels(["#", "Time", "At m", "Length", "Knots/m", "CV %", "Speed", "Trial / file"])
        self.bm_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.bm_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.bm_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.bm_table.setMaximumHeight(170)
        self.bm_table.itemSelectionChanged.connect(self._sync)
        right.addWidget(self.bm_table)
        self._marks_row = bm
        self._bm_sig = None
        rw = QWidget()
        rw.setLayout(right)
        root.addWidget(rw, 1)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(1000)
        self._load_sensors()
        self._load_boxes()
        self._show_zero()
        self._poll()

    # --------------------------------------------------------------------------------------------- lists
    def _load_boxes(self) -> None:
        self.cb_box.clear()
        try:
            boxes = sm.list_boxes()
        except Exception as e:  # noqa: BLE001
            self.cb_box.addItem(error_text(e), None)
            self._sync()
            return
        if not boxes:
            self.cb_box.addItem("No NI box connected", None)
        for b in boxes:
            self.cb_box.addItem(f"{b['name']} – {b['product']} (serial {b['serial']})", b["name"])
        i = self.cb_box.findData(self._settings.value("box"))
        if i >= 0:
            self.cb_box.setCurrentIndex(i)
        self._sync()

    def _load_sensors(self) -> None:
        self.cb_sensor.clear()
        presets = sm.sensor_presets()
        if not presets:
            self.cb_sensor.addItem("No sensor found in the Sensoft configurations", None)
        for p in presets:
            self.cb_sensor.addItem(p["label"], p)
        for i in range(self.cb_sensor.count()):
            d = self.cb_sensor.itemData(i)
            if d and d.get("key") == self._settings.value("sensor"):
                self.cb_sensor.setCurrentIndex(i)
        self._fill_second()

    def _fill_second(self) -> None:
        main = self.cb_sensor.currentData() or {}
        want = (self.cb_second.currentData() or {}).get("key") or self._settings.value("second")
        self.cb_second.blockSignals(True)
        self.cb_second.clear()
        self.cb_second.addItem("– none –", None)
        for i in range(self.cb_sensor.count()):
            d = self.cb_sensor.itemData(i)
            if d and main and d.get("connector") != main.get("connector") and d.get("head") != main.get("head"):
                self.cb_second.addItem(d["label"], d)
                if d.get("key") == want:
                    self.cb_second.setCurrentIndex(self.cb_second.count() - 1)
        self.cb_second.blockSignals(False)
        self._sync()

    def _running(self) -> bool:
        s = sl.current()
        return bool(s and s.state in ("running", "stopping"))

    def _sync(self) -> None:
        run = self._running()
        ok = bool(self.cb_box.currentData()) and bool(self.cb_sensor.currentData())
        self.btn_start.setEnabled(ok and not run and not self.read_only)
        self.btn_stop.setEnabled(run)
        for w in (self.cb_box, self.cb_sensor, self.cb_second, self.sp_speed, self.sp_window, self.ck_save, self.ed_name,
                  self.rb_dty, self.rb_aty):
            w.setEnabled(not run)
        if hasattr(self, "btn_zero"):
            self.btn_zero.setEnabled(ok and not run and not self.read_only)
        self.sp_distance.setEnabled(not run and bool(self.cb_second.currentData()))
        self.ck_auto.setVisible(bool(self.cb_second.currentData()))
        self.ck_auto.setEnabled(not run and self.sp_distance.value() > 0)
        self.sp_speed.setEnabled(not run and not self._auto_on())
        s = sl.current()
        has_data = bool(s and s.state in ("running", "stopping", "done") and s._tail_pts)
        self.btn_mark.setEnabled(has_data and not self.read_only)
        sel = self._selected_bookmark() is not None
        from db import trial_actions as ta
        self.btn_trial.setEnabled(sel and ta.can_edit_trials(self.user))
        self.btn_file.setEnabled(sel and not self.read_only)
        self.btn_unmark.setEnabled(sel)
        if self.read_only:
            self.lbl_msg.setText("Write access required (AccessLevel > 1).")

    # ------------------------------------------------------------------------------------------- actions
    def _sel_zero(self):
        p = self.cb_sensor.currentData() or {}
        p2 = self.cb_second.currentData() or {}
        return (self.cb_box.currentData(), p.get("head"), p.get("connector"),
                {"head_name": p2["head"], "connector": p2["connector"]} if p2 else None)

    def _show_zero(self) -> None:
        if not hasattr(self, "lbl_zero"):
            return
        box, head, con, second = self._sel_zero()
        z = sm.remembered_zero(box, head, con, second) if box and head else None
        if not z:
            self.lbl_zero.setText("<span style='color:#777'>Without yarn in the sensor - shows what the sensor sees "
                                  "when empty.</span>")
            self.btn_zero.setText("Check empty value (no yarn)")
            return
        two = len({a.get("connector") for a in z["axes"]}) > 1
        vals = "   ".join(f"{a['connector'] + ' ' if two else ''}{a['axis'].upper()}: {a['mean_um']:.1f} µm "
                          f"(± {a['std_um']:.1f})" for a in z["axes"])
        self.lbl_zero.setText(f"{vals}<br><span style='color:#666'>checked {str(z.get('at', ''))[11:16]} - kept until "
                              f"you check again</span>")
        self.btn_zero.setText("Check empty value again")

    def _on_zero(self) -> None:
        from PySide6.QtWidgets import QApplication
        box, head, con, second = self._sel_zero()
        if not box or not head:
            return
        self.lbl_zero.setText("measuring …")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            sm.zero_check(box, head, con)
            if second:
                sm.zero_check(box, second["head_name"], second["connector"])
        except Exception as e:  # noqa: BLE001
            self.lbl_zero.setText(f"<span style='color:#c0392b'>{error_text(e)}</span>")
            return
        finally:
            QApplication.restoreOverrideCursor()
        self._show_zero()

    def _auto_on(self) -> bool:
        return self.ck_auto.isChecked() and bool(self.cb_second.currentData()) and self.sp_distance.value() > 0

    def _on_start(self) -> None:
        box, head, con, second = self._sel_zero()
        if box and head and sm.remembered_zero(box, head, con, second) is None and QMessageBox.question(
                self, "YarnScope Live", "The empty value (no yarn) was not checked. Start anyway?") != QMessageBox.Yes:
            return
        p = self.cb_sensor.currentData() or {}
        p2 = self.cb_second.currentData() or {}
        kind = "aty" if self.rb_aty.isChecked() else "dty"
        for k, v in (("box", self.cb_box.currentData()), ("sensor", p.get("key")), ("second", p2.get("key") or ""),
                     ("distance", self.sp_distance.value()), ("speed", self.sp_speed.value()),
                     ("window", self.sp_window.value()), ("save", self.ck_save.isChecked()),
                     ("name", self.ed_name.text().strip()), ("kind", kind), ("auto", self.ck_auto.isChecked())):
            self._settings.setValue(k, v)
        try:
            sl.start(box=self.cb_box.currentData(), head_name=p.get("head"), connector=p.get("connector"),
                     second={"head_name": p2["head"], "connector": p2["connector"]} if p2 else None,
                     speed_m_min=None if self._auto_on() else self.sp_speed.value(), auto_speed=self._auto_on(),
                     distance_mm=self.sp_distance.value() or None,
                     window_m=self.sp_window.value(), save=self.ck_save.isChecked(), name=self.ed_name.text().strip(),
                     kind=kind, user=self.user)
        except Exception as e:  # noqa: BLE001
            self.lbl_msg.setText(f"<span style='color:#c0392b'>{error_text(e)}</span>")
            return
        self._shown = 0
        self.lbl_msg.setText("")
        self.table.setRowCount(0)
        self._poll()

    # ---------------------------------------------------------------------------------------- bookmarks
    def _selected_bookmark(self) -> Optional[Dict[str, Any]]:
        s = sl.current()
        rows = self.bm_table.selectionModel().selectedRows() if self.bm_table.selectionModel() else []
        if not s or not rows:
            return None
        it = self.bm_table.item(rows[0].row(), 0)
        bid = it.data(Qt.UserRole) if it else None
        return next((b for b in s.bookmarks if b["id"] == bid), None)

    def _on_bookmark(self) -> None:
        s = sl.current()
        if s is None:
            return
        self._settings.setValue("bookmark_m", self.sp_mark.value())
        try:
            b = s.bookmark(self.sp_mark.value())
        except Exception as e:  # noqa: BLE001
            self.lbl_msg.setText(f"<span style='color:#c0392b'>{error_text(e)}</span>")
            return
        self.lbl_msg.setText(f"Bookmark {b['id']}: last {b['length_m']:.0f} m kept.")
        self._fill_bookmarks(force=True)

    def _fill_bookmarks(self, force: bool = False) -> None:
        s = sl.current()
        bms = [sl.LiveSession.bookmark_meta(b) for b in (s.bookmarks if s else [])]
        sig = repr(bms)
        if sig == self._bm_sig and not force:
            return
        self._bm_sig = sig
        keep = (self._selected_bookmark() or {}).get("id")
        f = lambda x, d=1: "–" if x is None else f"{x:.{d}f}"  # noqa: E731
        self.bm_table.setRowCount(len(bms))
        for k, b in enumerate(bms):
            sens = (b.get("sensors") or [{}])[0]
            tr = b.get("trial")
            where = (f"{tr['series_id']} V{tr['vno']:03d}" if tr else "") + (f" · {b['file']}" if b.get("file") else "")
            vals = [str(b["id"]) + (f" {b['label']}" if b.get("label") else ""), b["at"][11:16], f"{b['at_m']:.0f}",
                    f"{b['length_m']:.0f} m", f(sens.get("fpm")), f(sens.get("cv")), f(b.get("speed")), where]
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c == 0:
                    it.setData(Qt.UserRole, b["id"])
                self.bm_table.setItem(k, c, it)
            if b["id"] == keep:
                self.bm_table.selectRow(k)
        self.bm_table.resizeColumnsToContents()
        self._sync()

    def _on_unmark(self) -> None:
        b, s = self._selected_bookmark(), sl.current()
        if b and s:
            s.delete_bookmark(b["id"])
            self._fill_bookmarks(force=True)

    def _on_file(self) -> None:
        b, s = self._selected_bookmark(), sl.current()
        if not (b and s):
            return
        name, ok = QInputDialog.getText(self, "Save bookmark as file",
                                        f"Name (file goes to the sub-folder '{sm.MANUAL_DIR}', no trial):",
                                        text=str(self._settings.value("bm_name", "99999_1")))
        if not ok:
            return
        try:
            r = live_trial.save_file(s, b["id"], name)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Save bookmark", error_text(e))
            return
        self._settings.setValue("bm_name", sm.next_name(name.strip()))
        self.lbl_msg.setText(f"Saved: {', '.join(r['files'])}")
        self._fill_bookmarks(force=True)

    def _on_trial(self) -> None:
        b, s = self._selected_bookmark(), sl.current()
        if not (b and s):
            return
        dlg = LiveTrialDialog(s, b, self.user, self)
        if dlg.exec() == QDialog.Accepted and dlg.result_info:
            r = dlg.result_info
            msg = f"Trial {r['series_id']} V{r['vno']:03d} created."
            if r.get("file"):
                msg += f" File: {r['file']}" + (f" (old file moved to {sm.REPLACED_DIR})" if r.get("replaced") else "")
            if r.get("tdms_error"):
                msg += f" <span style='color:#c0392b'>The file could not be saved: {r['tdms_error']}</span>"
            self.lbl_msg.setText(msg)
            self._fill_bookmarks(force=True)

    def _on_stop(self) -> None:
        self.btn_stop.setEnabled(False)
        self.lbl_status.setText("Stopping…")
        QTimer.singleShot(10, lambda: (sl.stop(), self._poll()))

    # ---------------------------------------------------------------------------------------- dashboard
    def _poll(self) -> None:
        s = sl.current()
        self._sync()
        if s is None:
            return
        v = s.view(0)
        txt = f"<b>{STATE_TEXT.get(v['state'], v['state'])}</b> · {v['meters']:.0f} m · {v['seconds']:.0f} s · {v['rate']:.1f} Hz"
        if v.get("save_stopped"):
            txt += " · <span style='color:#c0392b'>saving stopped at the limit</span>"
        if v.get("files"):
            txt += "<br>Saved: " + ", ".join(v["files"])
        if v.get("error"):
            err = sm.MeasureError(v["error"].get("code", ""), v["error"].get("detail", ""))
            err.vars = dict(v["error"].get("vars") or {})
            txt += f"<br><span style='color:#c0392b'>{error_text(err)}</span>"
        self.lbl_status.setText(txt)
        self._fill_bookmarks()
        rows = v["rows"]
        self._tiles(v, rows[-1] if rows else None)
        if len(rows) != self._shown:
            self._fill_table(v, rows)
            self._draw(v, rows)
            self._shown = len(rows)

    def _tiles(self, v: Dict[str, Any], last: Optional[Dict[str, Any]]) -> None:
        sens = v.get("sensors") or []
        n = 2 * len(sens) + (1 if len(sens) > 1 else 0)
        while len(self._tile_labels) < n:
            lab = QLabel()
            lab.setFrameShape(QFrame.StyledPanel)
            lab.setMinimumHeight(70)
            self.tiles.addWidget(lab, 0, len(self._tile_labels))
            self._tile_labels.append(lab)
        f = lambda x, d=1: "–" if x is None else f"{x:.{d}f}"  # noqa: E731
        for i, s in enumerate(sens):
            r = (last or {}).get("sensors", [{}] * len(sens))[i] if last else {}
            head = f"<span style='color:#666'>{_head_label(s['head'])} · {s['connector']}"
            # CV is important (Nutzerwunsch 2026-11-24): its own tile, as large as knots/m
            for k, (val, unit, what) in enumerate(((r.get("fpm"), "knots/m", "Knots/m"), (r.get("cv"), "%", "CV"))):
                lab = self._tile_labels[2 * i + k]
                lab.setStyleSheet(f"QLabel{{border-left:5px solid {COLORS[i % 2]};padding:6px;}}")
                lab.setText(f"{head} · {what}</span><br><span style='font-size:24px;font-weight:bold'>{f(val)}</span> {unit}")
        if len(sens) > 1:
            lab = self._tile_labels[2 * len(sens)]
            sp = (last or {}).get("speed")
            extra = (f"delay {f((last or {}).get('delay_ms'), 3)} ms · match {f((last or {}).get('corr'), 2)}"
                     if last and last.get("delay_ms") is not None else "the two signals do not match yet")
            if last and sp is None and last.get("distance_from_speed_mm") is not None:
                extra += f" · {last['distance_from_speed_mm']:.1f} mm apart at the set speed"
            lab.setText(f"<span style='color:#666'>Speed</span><br><span style='font-size:24px;font-weight:bold'>"
                        f"{f(sp)}</span> m/min<br><span style='color:#666'>{extra}</span>")
        for j, lab in enumerate(self._tile_labels):
            lab.setVisible(j < n and self._focus is None)
        self._zoom_btns["speed"].setVisible(len(sens) > 1 and self._focus is None)

    def _fill_table(self, v: Dict[str, Any], rows: List[Dict[str, Any]]) -> None:
        sens = v.get("sensors") or []
        heads = ["m"]
        for s in sens:
            heads += [f"{_head_label(s['head'])} {s['connector']} knots/m", "CV %"]
        if len(sens) > 1:
            heads += ["Speed m/min", "Match"]
        self.table.setColumnCount(len(heads))
        self.table.setHorizontalHeaderLabels(heads)
        self.table.setRowCount(len(rows))
        f = lambda x, d=1: "–" if x is None else f"{x:.{d}f}"  # noqa: E731
        for k, r in enumerate(reversed(rows)):
            vals = [f"{r['from_m']:.0f}–{r['to_m']:.0f}"]
            for s in r["sensors"]:
                vals += [f(s.get("fpm")), f(s.get("cv"))]
            if len(sens) > 1:
                vals += [f(r.get("speed")), f(r.get("corr"), 2)]
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(k, c, it)
        self.table.resizeColumnsToContents()

    def _draw(self, v: Dict[str, Any], rows: List[Dict[str, Any]]) -> None:
        if self._fig is None:
            return
        sens = v.get("sensors") or []
        two = len(sens) > 1
        self._fig.clear()
        self._ax_keys = []
        x = [r["to_m"] for r in rows]
        keys = ["fpm", "cv"] + (["speed"] if two else [])
        if self._focus not in keys:
            self._focus = None
        show = [self._focus] if self._focus else keys
        n = len(show)
        big = self._focus is not None
        pos = {k: show.index(k) + 1 for k in show}
        for key, title, rel, floor in (("fpm", "Knots/m", 0.10, None), ("cv", "CV knot spacing %", 0.0, (0, 40))):
            if key not in pos:
                continue
            ax = self._fig.add_subplot(1, n, pos[key])
            self._ax_keys.append((ax, key))
            allv = []
            for i, s in enumerate(sens):
                ys = [r["sensors"][i].get(key) if i < len(r["sensors"]) else None for r in rows]
                allv += ys
                ax.plot(x, ys, marker="o", ms=3, color=COLORS[i % 2], label=f"{_head_label(s['head'])} {s['connector']}")
            yr = y_range(allv, rel, floor)
            if yr:
                ax.set_ylim(*yr)
            ax.set_title(title, fontsize=12 if big else 9)
            ax.tick_params(labelsize=10 if big else 8)
            if two and (key == "fpm" or big):
                ax.legend(fontsize=9 if big else 7)
            if big:
                ax.grid(True, alpha=0.3)
        if two and "speed" in pos:
            ax = self._fig.add_subplot(1, n, pos["speed"])
            self._ax_keys.append((ax, "speed"))
            sp = [r.get("speed") for r in rows]
            ax.plot(x, sp, marker="o", ms=3, color=COLORS[0])
            yr = y_range(sp, 0.03)
            if yr:
                ax.set_ylim(*yr)
            ax.set_title("Speed m/min", fontsize=12 if big else 9)
            ax.tick_params(labelsize=10 if big else 8)
            if big:
                ax.grid(True, alpha=0.3)
        self._canvas.draw_idle()

    # ------------------------------------------------------------------------------- full-size chart
    def _set_focus(self, key: Optional[str]) -> None:
        """One chart at full size (key) or all side by side (None): the tiles, table and bookmarks make room."""
        self._focus = key
        big = key is not None
        for w in (self.table, self.bm_table):
            w.setVisible(not big)
        for lab in self._tile_labels:
            lab.setVisible(not big and lab.text() != "")
        for i in range(self._marks_row.count()):
            it = self._marks_row.itemAt(i).widget()
            if it is not None:
                it.setVisible(not big)
        self.btn_unzoom.setVisible(big)
        for k, b in self._zoom_btns.items():
            b.setVisible(not big)
        s = sl.current()
        if s is not None:
            v = s.view(0)
            self._zoom_btns["speed"].setVisible(not big and len(v.get("sensors") or []) > 1)
            self._draw(v, v["rows"])
        if not big:
            self._poll()

    def _on_chart_click(self, event) -> None:
        if not getattr(event, "dblclick", False):
            return
        if self._focus is not None:
            self._set_focus(None)
            return
        key = next((k for ax, k in self._ax_keys if ax is event.inaxes), None)
        if key:
            self._set_focus(key)

    def keyPressEvent(self, ev) -> None:  # noqa: N802 - Qt
        if ev.key() == Qt.Key_Escape and self._focus is not None:
            self._set_focus(None)
            return
        super().keyPressEvent(ev)

    def closeEvent(self, ev) -> None:  # noqa: N802 - Qt
        s = sl.current()
        open_bm = [b for b in (s.bookmarks if s else []) if not b.get("trial") and not b.get("file")]
        if open_bm and not self._running() and QMessageBox.question(
                self, "YarnScope Live", f"{len(open_bm)} bookmark(s) without a trial or file. They stay in memory until "
                "the next live start or until TrippleT is closed. Close the window?") != QMessageBox.Yes:
            ev.ignore()
            return
        if self._running():
            if QMessageBox.question(self, "YarnScope Live", "A live measurement is running. Stop it?") != QMessageBox.Yes:
                ev.ignore()
                return
            sl.stop()
        self._timer.stop()
        global _window
        _window = None
        super().closeEvent(ev)


class LiveTrialDialog(QDialog):
    """"Create trial...": series (recent ones or a typed number), template trial, the copy fields shown by default
    (jet, pressure, OF, speed ...) filled from the template, and - not ticked - the bookmark as the trial's TDMS."""

    def __init__(self, session, bookmark: Dict[str, Any], user: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Create trial from bookmark {bookmark['id']}")
        self.setMinimumWidth(520)
        self.session, self.bm, self.user = session, bookmark, user
        self.result_info: Optional[Dict[str, Any]] = None
        self._setup: Optional[Dict[str, Any]] = None
        self._edits: Dict[str, Any] = {}
        root = QVBoxLayout(self)
        sens = (bookmark.get("sensors") or [{}])[0]
        info = QLabel(f"Bookmark {bookmark['id']} at {bookmark['at'][11:16]}: {bookmark['length_m']:.0f} m, "
                      f"{sens.get('fpm') or '–'} knots/m, CV {sens.get('cv') or '–'} %, measured speed "
                      f"{bookmark.get('speed') or '–'} m/min.")
        info.setWordWrap(True)
        info.setStyleSheet("color:#555;")
        root.addWidget(info)
        top = QFormLayout()
        srow = QHBoxLayout()
        self.cb_series = QComboBox()
        self.cb_series.setEditable(True)
        self.cb_series.setInsertPolicy(QComboBox.NoInsert)
        self.cb_series.lineEdit().setPlaceholderText("TrialSeriesID, e.g. 466")
        try:
            from ui import recent_series
            for e in recent_series.entries():
                self.cb_series.addItem(f"{e['series']} · {e.get('eid') or ''} {e.get('name') or ''}".strip(), e["series"])
        except Exception:  # noqa: BLE001
            pass
        self.cb_series.setCurrentIndex(-1)
        btn = QPushButton("Load")
        btn.clicked.connect(self._load)
        self.cb_series.activated.connect(lambda _i: self._load())
        self.cb_series.lineEdit().returnPressed.connect(self._load)
        srow.addWidget(self.cb_series, 1)
        srow.addWidget(btn)
        top.addRow("Trial series:", srow)
        self.lbl_series = QLabel("")
        self.lbl_series.setStyleSheet("color:#555;")
        top.addRow("", self.lbl_series)
        self.cb_template = QComboBox()
        self.cb_template.currentIndexChanged.connect(lambda _i: self._fill_values())
        top.addRow("Copy of:", self.cb_template)
        root.addLayout(top)
        self.form = QFormLayout()
        root.addLayout(self.form)
        self.ck_tdms = QCheckBox(f"Save the bookmark ({bookmark['length_m']:.0f} m) as this trial's TDMS")
        self.ck_tdms.setChecked(False)
        root.addWidget(self.ck_tdms)
        self.lbl_err = QLabel("")
        self.lbl_err.setWordWrap(True)
        self.lbl_err.setStyleSheet("color:#c0392b;")
        root.addWidget(self.lbl_err)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText("Create trial")
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)
        self.buttons.accepted.connect(self._create)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)
        if self.cb_series.count():
            self.cb_series.setCurrentIndex(0)
            self._load()

    def _series_id(self) -> Optional[int]:
        d = self.cb_series.currentData() if self.cb_series.currentIndex() >= 0 and \
            self.cb_series.currentText() == self.cb_series.itemText(self.cb_series.currentIndex()) else None
        if d is not None:
            return int(d)
        txt = self.cb_series.currentText().strip().split(" ")[0]
        return int(txt) if txt.isdigit() else None

    def _load(self) -> None:
        sid = self._series_id()
        self._setup = None
        self.cb_template.clear()
        info = live_trial.series_info(sid) if sid else None
        if not info:
            self.lbl_series.setText("No trial series with this number.")
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)
            return
        self.lbl_series.setText(f"{info['eid']} · {info['name']}")
        self._sid = info["id"]
        self._setup = live_trial.setup(info["id"])
        for t in sorted(self._setup["trials"], key=lambda t: t["vno"]):
            self.cb_template.addItem(f"V{t['vno']:03d}", t["id"])
        if self._setup["default"] is not None:
            self.cb_template.setCurrentIndex(self.cb_template.findData(self._setup["default"]))
        self.ck_tdms.setText(f"Save the bookmark ({self.bm['length_m']:.0f} m) as the TDMS of the new trial "
                             f"V{self._setup['next_no']:03d}")
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(bool(self._setup["trials"]))
        if not self._setup["trials"]:
            self.lbl_series.setText(self.lbl_series.text() + " – no trial to copy.")

    def _fill_values(self) -> None:
        from db import trial_copy as tc
        while self.form.rowCount():
            self.form.removeRow(0)
        self._edits = {}
        if not self._setup or self.cb_template.currentData() is None:
            return
        src = self._setup["source"].get(int(self.cb_template.currentData()), {})
        for f in self._setup["fields"]:
            v = src.get(f.key)
            if v is tc.NOT_AVAILABLE:
                continue
            if f.choices:
                w = QComboBox()
                w.addItem("", None)
                for k, name in f.choices:
                    w.addItem(name, k)
                try:
                    i = w.findData(int(v)) if v is not None else 0
                except (TypeError, ValueError):
                    i = 0
                w.setCurrentIndex(max(0, i))
                w.setProperty("orig", w.currentData())
            else:
                w = QLineEdit(tc.display_value(f, v))
                w.setProperty("orig", w.text())
            self._edits[f.key] = (f, w)
            self.form.addRow(f.label + ":", w)

    def _values(self) -> Dict[str, Any]:
        """Only what the user changed (the rest is copied from the template as it is)."""
        out = {}
        for key, (f, w) in self._edits.items():
            if isinstance(w, QComboBox):
                if w.currentData() != w.property("orig"):
                    out[key] = "" if w.currentData() is None else str(w.currentData())
            elif w.text().strip() != str(w.property("orig") or ""):
                out[key] = w.text().strip()
        return out

    def _create(self) -> None:
        if not self._setup:
            return
        try:
            self.result_info = live_trial.create(self._sid, int(self.cb_template.currentData()), self._values(),
                                                 user=self.user, session=self.session, bookmark_id=self.bm["id"],
                                                 save_tdms=self.ck_tdms.isChecked())
        except Exception as e:  # noqa: BLE001
            self.lbl_err.setText(error_text(e))
            return
        self.accept()
