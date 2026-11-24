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
STATE_TEXT = {"running": "Measuring", "stopping": "Stopping…", "done": "Finished", "error": "Error", "new": "Starting…",
              "loaded": "Loaded"}

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
        # load a saved live run again and see exactly its curves (Nutzerwunsch 2026-11-24, sensor_live.load_saved)
        self._loaded: Optional[Dict[str, Any]] = None
        self.btn_load = QPushButton("Load a measurement…")
        self.btn_load.clicked.connect(self._on_load)
        left.addWidget(self.btn_load)
        self.btn_back_live = QPushButton("Back to the live view")
        self.btn_back_live.clicked.connect(self._back_to_live)
        self.btn_back_live.setVisible(False)
        left.addWidget(self.btn_back_live)
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
        for key, title in (("fpm", "Knots/m"), ("cv", "CV"), ("thick", "Thickness"), ("speed", "Speed")):
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
        # a trial without a bookmark - never a TDMS (Nutzerwunsch 2026-11-24); works without a live measurement too
        self.btn_new_trial = QPushButton("Create trials…")
        self.btn_new_trial.setToolTip("New trials from a template with jet, plate, pressure, OF and speed - optionally "
                                      "each with a bookmark as TDMS")
        self.btn_new_trial.clicked.connect(lambda: self._on_trial(free=True))
        for w in (self.btn_mark, QLabel("last"), self.sp_mark):
            bm.addWidget(w)
        bm.addStretch(1)
        for w in (self.btn_trial, self.btn_file, self.btn_unmark, self.btn_new_trial):
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
        if hasattr(self, "btn_load"):
            self.btn_load.setEnabled(not run)
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
        self.btn_new_trial.setEnabled(ta.can_edit_trials(self.user))
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

    def _on_load(self) -> None:
        dlg = LoadRunDialog("aty" if self.rb_aty.isChecked() else "dty", self)
        if dlg.exec() == QDialog.Accepted and dlg.view:
            self._loaded = dlg.view
            self._shown = 0
            self.btn_back_live.setVisible(True)
            self._set_focus(None) if self._focus else None
            self._poll()

    def _back_to_live(self) -> None:
        self._loaded = None
        self._shown = 0
        self.btn_back_live.setVisible(False)
        self.table.setRowCount(0)
        if self._fig is not None:
            self._fig.clear()
            self._canvas.draw_idle()
        self.lbl_status.setText("No live measurement running.")
        self._poll()

    def _on_start(self) -> None:
        self._loaded = None
        self.btn_back_live.setVisible(False)
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

    def _on_trial(self, free: bool = False) -> None:
        s = sl.current()
        b = None if free else self._selected_bookmark()
        if not free and not (b and s):
            return
        dlg = LiveTrialDialog(s, b, self.user, self)
        if dlg.exec() == QDialog.Accepted and dlg.result_infos:
            parts = []
            for r in dlg.result_infos:
                t = f"{r['series_id']} V{r['vno']:03d}"
                if r.get("file"):
                    t += f" ({r['file']}" + (f", old file moved to {sm.REPLACED_DIR}" if r.get("replaced") else "") + ")"
                if r.get("tdms_error"):
                    t += f" <span style='color:#c0392b'>file not saved: {r['tdms_error']}</span>"
                parts.append(t)
            self.lbl_msg.setText("Created: " + ", ".join(parts))
            self._fill_bookmarks(force=True)

    def _on_stop(self) -> None:
        self.btn_stop.setEnabled(False)
        self.lbl_status.setText("Stopping…")
        QTimer.singleShot(10, lambda: (sl.stop(), self._poll()))

    # ---------------------------------------------------------------------------------------- dashboard
    def _view(self) -> Optional[Dict[str, Any]]:
        """What the dashboard shows: a loaded saved run, or the current live session."""
        if self._loaded is not None:
            return self._loaded
        s = sl.current()
        return s.view(0) if s is not None else None

    def _poll(self) -> None:
        self._sync()
        v = self._view()
        if v is None:
            return
        if v["state"] == "loaded":
            txt = (f"<b>Loaded</b> · {v.get('loaded')} · measured {str(v.get('loaded_at') or '').replace('T', ' ')[:16]} · "
                   f"{(v.get('meters') or 0):.0f} m")
            if not v.get("exact"):
                txt += ("<br><span style='color:#666'>analysed again from the signal; with 'measure the speed' only its "
                        "mean is known</span>")
            self.lbl_status.setText(txt)
            rows = v["rows"]
            self._tiles(v, rows[-1] if rows else None)
            if len(rows) != self._shown or self._shown == 0:
                self._fill_table(v, rows)
                self._draw(v, rows)
                self._shown = len(rows)
            return
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
        n = 3 * len(sens) + (1 if len(sens) > 1 else 0)
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
                lab = self._tile_labels[3 * i + k]
                lab.setStyleSheet(f"QLabel{{border-left:5px solid {COLORS[i % 2]};padding:6px;}}")
                lab.setText(f"{head} · {what}</span><br><span style='font-size:24px;font-weight:bold'>{f(val)}</span> {unit}")
            # thickness minus the empty value (2026-11-24): whole window, bulk (open parts), knots
            lab = self._tile_labels[3 * i + 2]
            lab.setStyleSheet(f"QLabel{{border-left:5px solid {COLORS[i % 2]};padding:6px;}}")
            lab.setToolTip("Signal minus empty value, mean of the window; bulk = open parts, knots = the detected knots. "
                           "Not yet validated against a known diameter.")
            if r.get("d_um") is not None:
                lab.setText(f"{head} · Thickness</span><br><span style='font-size:24px;font-weight:bold'>{f(r['d_um'], 0)}</span> µm"
                            f"<br>Bulk {f(r.get('d_bulk'), 0)} · Knots {f(r.get('d_knot'), 0)} µm")
            else:
                lab.setText(f"{head} · Thickness</span><br><span style='color:#777'>"
                            f"{'Check the empty value before the start.' if last else '–'}</span>")
        if len(sens) > 1:
            lab = self._tile_labels[3 * len(sens)]
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
        self._zoom_btns["thick"].setVisible(self._focus is None and bool(last) and any(
            x.get("d_bulk") is not None for x in (last or {}).get("sensors", [])))

    def _fill_table(self, v: Dict[str, Any], rows: List[Dict[str, Any]]) -> None:
        sens = v.get("sensors") or []
        heads = ["m"]
        for s in sens:
            heads += [f"{_head_label(s['head'])} {s['connector']} knots/m", "CV %", "Thickness µm", "Bulk", "Knots"]
        if len(sens) > 1:
            heads += ["Speed m/min", "Match"]
        self.table.setColumnCount(len(heads))
        self.table.setHorizontalHeaderLabels(heads)
        self.table.setRowCount(len(rows))
        f = lambda x, d=1: "–" if x is None else f"{x:.{d}f}"  # noqa: E731
        for k, r in enumerate(reversed(rows)):
            vals = [f"{r['from_m']:.0f}–{r['to_m']:.0f}"]
            for s in r["sensors"]:
                vals += [f(s.get("fpm")), f(s.get("cv")), f(s.get("d_um"), 0), f(s.get("d_bulk"), 0), f(s.get("d_knot"), 0)]
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
        has_d = any(x.get("d_bulk") is not None for r in rows for x in r["sensors"])
        keys = ["fpm", "cv"] + (["thick"] if has_d else []) + (["speed"] if two else [])
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
        if "thick" in pos:                       # bulk solid, knots dotted, per sensor
            ax = self._fig.add_subplot(1, n, pos["thick"])
            self._ax_keys.append((ax, "thick"))
            allv = []
            for i, s in enumerate(sens):
                for key, style, what in (("d_bulk", "-", "bulk"), ("d_knot", ":", "knots")):
                    ys = [r["sensors"][i].get(key) if i < len(r["sensors"]) else None for r in rows]
                    allv += ys
                    ax.plot(x, ys, style, marker="o", ms=3, color=COLORS[i % 2],
                            label=f"{_head_label(s['head'])} {s['connector']} {what}")
            yr = y_range(allv, 0.05)
            if yr:
                ax.set_ylim(*yr)
            ax.set_title("Thickness µm", fontsize=12 if big else 9)
            ax.tick_params(labelsize=10 if big else 8)
            ax.legend(fontsize=9 if big else 6)
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
        v = self._view()
        if v is not None:
            self._zoom_btns["speed"].setVisible(not big and len(v.get("sensors") or []) > 1)
            self._zoom_btns["thick"].setVisible(not big and any(x.get("d_bulk") is not None
                                                                for r in v["rows"] for x in r["sensors"]))
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
    """"Create trials...": series (recent ones or a typed number), template trial and ONE COLUMN PER NEW TRIAL
    (Nutzerwunsch 2026-11-24: e.g. jet plate 1 and plate 2 at once) with the copy fields shown by default (jet, plate,
    pressure, OF, speed ...) filled from the template; "+ Trial" copies the last column. Per column optionally a
    bookmark as that trial's TDMS (each bookmark once). live_trial.create_many checks everything before the first copy."""

    def __init__(self, session, bookmark: Optional[Dict[str, Any]], user: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Create trials (from bookmark {bookmark['id']})" if bookmark else "Create trials")
        self.setMinimumWidth(620)
        self.session, self.bm, self.user = session, bookmark, user
        self.result_info: Optional[Dict[str, Any]] = None
        self.result_infos: List[Dict[str, Any]] = []
        self._setup: Optional[Dict[str, Any]] = None
        self._cols: List[Dict[str, Any]] = []          # per column: {"edits": {key: (field, widget)}, "bm": QComboBox}
        self._orig: Dict[str, Any] = {}
        root = QVBoxLayout(self)
        if bookmark:
            sens = (bookmark.get("sensors") or [{}])[0]
            info = QLabel(f"Bookmark {bookmark['id']} at {bookmark['at'][11:16]}: {bookmark['length_m']:.0f} m, "
                          f"{sens.get('fpm') or '–'} knots/m, CV {sens.get('cv') or '–'} %, measured speed "
                          f"{bookmark.get('speed') or '–'} m/min.")
        else:
            info = QLabel("Copies of a trial with your values - one column per trial. Optionally one bookmark per trial "
                          "is saved as its TDMS.")
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
        from PySide6.QtWidgets import QScrollArea
        self._grid_host = QWidget()
        self.grid = QGridLayout(self._grid_host)
        self.grid.setHorizontalSpacing(8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._grid_host)
        scroll.setMinimumHeight(240)
        root.addWidget(scroll, 1)
        arow = QHBoxLayout()
        self.btn_add = QPushButton("+ Trial")
        self.btn_add.setToolTip("Another trial: copies the values of the last column")
        self.btn_add.clicked.connect(self._add_col)
        self.lbl_names = QLabel("")
        self.lbl_names.setStyleSheet("color:#555;")
        arow.addWidget(self.btn_add)
        arow.addWidget(self.lbl_names, 1)
        root.addLayout(arow)
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

    # first column, for code that knows only one trial
    @property
    def _edits(self) -> Dict[str, Any]:
        return self._cols[0]["edits"] if self._cols else {}

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
            self._clear_grid()
            return
        self.lbl_series.setText(f"{info['eid']} · {info['name']}")
        self._sid = info["id"]
        self._setup = live_trial.setup(info["id"])
        for t in sorted(self._setup["trials"], key=lambda t: t["vno"]):
            self.cb_template.addItem(f"V{t['vno']:03d}", t["id"])
        if self._setup["default"] is not None:
            self.cb_template.setCurrentIndex(self.cb_template.findData(self._setup["default"]))
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(bool(self._setup["trials"]))
        if not self._setup["trials"]:
            self.lbl_series.setText(self.lbl_series.text() + " – no trial to copy.")

    # ------------------------------------------------------------------------------------------- columns
    def _clear_grid(self) -> None:
        while self.grid.count():
            it = self.grid.takeAt(0)
            if it.widget() is not None:
                it.widget().deleteLater()

    def _bookmarks(self) -> List[Dict[str, Any]]:
        return [sl.LiveSession.bookmark_meta(b) for b in (self.session.bookmarks if self.session else [])]

    def _new_widget(self, f, value: Any):
        if f.choices:
            w = QComboBox()
            w.addItem("", None)
            for k, name in f.choices:
                w.addItem(name, k)
            try:
                i = w.findData(int(value)) if value not in (None, "") else 0
            except (TypeError, ValueError):
                i = 0
            w.setCurrentIndex(max(0, i))
        else:
            w = QLineEdit("" if value is None else str(value))
        return w

    def _widget_value(self, w) -> Any:
        return w.currentData() if isinstance(w, QComboBox) else w.text().strip()

    def _fill_values(self) -> None:
        """Template changed (or loaded): one column with the template's values."""
        from db import trial_copy as tc
        for col in self._cols:
            self._drop_col(col)
        self._cols = []
        self._orig = {}
        if self._setup and self.cb_template.currentData() is not None:
            src = self._setup["source"].get(int(self.cb_template.currentData()), {})
            for f in self._setup["fields"]:
                v = src.get(f.key)
                if v is tc.NOT_AVAILABLE:
                    continue
                self._orig[f.key] = (f, v if f.choices else tc.display_value(f, v))
        self._add_col(from_orig=True)

    def _add_col(self, from_orig: bool = False) -> None:
        if not self._orig:
            self._rebuild()
            return
        if len(self._cols) >= live_trial.MAX_TRIALS:
            return
        last = None if from_orig or not self._cols else self._cols[-1]
        edits = {}
        for key, (f, v) in self._orig.items():
            val = self._widget_value(last["edits"][key][1]) if last else v
            edits[key] = (f, self._new_widget(f, val))
        bm = QComboBox()
        bm.addItem("–", None)
        for b in self._bookmarks():
            sens = (b.get("sensors") or [{}])[0]
            bm.addItem(f"📌{b['id']}{' ' + b['label'] if b.get('label') else ''} · {b['length_m']:.0f} m · "
                       f"{sens.get('fpm') or '–'} knots/m", b["id"])
        bm.setEnabled(bm.count() > 1)
        self._cols.append({"edits": edits, "bm": bm})
        self._rebuild()

    @staticmethod
    def _drop_col(col: Dict[str, Any]) -> None:
        for _f, w in col["edits"].values():
            w.setParent(None)
            w.deleteLater()
        col["bm"].setParent(None)
        col["bm"].deleteLater()

    def _remove_col(self, ci: int) -> None:
        if len(self._cols) > 1:
            self._drop_col(self._cols.pop(ci))
            self._rebuild()

    def _rebuild(self) -> None:
        """Lays the columns out again (widgets keep their values)."""
        while self.grid.count():                      # take the widgets out without deleting the column widgets
            it = self.grid.takeAt(0)
            w = it.widget()
            if w is not None and w.property("hdr"):
                w.deleteLater()
        if not self._cols:
            self.lbl_names.setText("")
            return
        nxt = int((self._setup or {}).get("next_no") or 1)
        names = [f"V{nxt + i:03d}" for i in range(len(self._cols))]
        for ci, name in enumerate(names):
            box = QWidget()
            box.setProperty("hdr", True)
            hl = QHBoxLayout(box)
            hl.setContentsMargins(0, 0, 0, 0)
            lab = QLabel(f"<b>{name}</b>")
            hl.addWidget(lab)
            if len(self._cols) > 1:
                x = QPushButton("✕")
                x.setFixedWidth(26)
                x.setToolTip("Remove this trial")
                x.clicked.connect(lambda _c=False, k=ci: self._remove_col(k))
                hl.addWidget(x)
            hl.addStretch(1)
            self.grid.addWidget(box, 0, ci + 1)
        row = 1
        for key, (f, _v) in self._orig.items():
            lab = QLabel(f.label + ":")
            lab.setProperty("hdr", True)
            self.grid.addWidget(lab, row, 0)
            for ci, col in enumerate(self._cols):
                self.grid.addWidget(col["edits"][key][1], row, ci + 1)
            row += 1
        lab = QLabel("TDMS from bookmark:")
        lab.setProperty("hdr", True)
        self.grid.addWidget(lab, row, 0)
        for ci, col in enumerate(self._cols):
            self.grid.addWidget(col["bm"], row, ci + 1)
        self.lbl_names.setText("New trials: " + ", ".join(names))
        self.buttons.button(QDialogButtonBox.Ok).setText(
            f"Create {len(self._cols)} trials" if len(self._cols) > 1 else "Create trial")

    def _values(self, ci: int = 0) -> Dict[str, Any]:
        """Only what the user changed in column ci (the rest is copied from the template as it is)."""
        out = {}
        for key, (f, w) in self._cols[ci]["edits"].items():
            orig = self._orig[key][1]
            if isinstance(w, QComboBox):
                try:
                    o = int(orig) if orig not in (None, "") else None
                except (TypeError, ValueError):
                    o = orig
                if w.currentData() != o:
                    out[key] = "" if w.currentData() is None else str(w.currentData())
            elif w.text().strip() != str(orig or ""):
                out[key] = w.text().strip()
        return out

    def _create(self) -> None:
        if not self._setup or not self._cols:
            return
        items = []
        for ci, col in enumerate(self._cols):
            bid = col["bm"].currentData()
            items.append({"values": self._values(ci), "bookmark_id": bid, "save_tdms": bid is not None})
        try:
            self.result_infos = live_trial.create_many(self._sid, int(self.cb_template.currentData()), items,
                                                       user=self.user, session=self.session)
        except Exception as e:  # noqa: BLE001
            self.lbl_err.setText(error_text(e))
            return
        self.result_info = self.result_infos[0] if self.result_infos else None
        self.accept()


class LoadRunDialog(QDialog):
    """Saved live runs of the DTY / ATY _manual folder (sensor_live.saved_runs): with a side file loaded at once (exactly
    the curves of that day), otherwise analysed again with a progress bar (sensor_live.load_saved)."""

    def __init__(self, kind: str = "dty", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Load a saved live measurement")
        self.setMinimumSize(760, 420)
        self.view: Optional[Dict[str, Any]] = None
        self._job = None
        root = QVBoxLayout(self)
        krow = QHBoxLayout()
        self.rb_dty, self.rb_aty = QRadioButton("DTY"), QRadioButton("ATY")
        (self.rb_aty if kind == "aty" else self.rb_dty).setChecked(True)
        self.rb_dty.toggled.connect(lambda _c: self._fill())
        krow.addWidget(self.rb_dty)
        krow.addWidget(self.rb_aty)
        krow.addStretch(1)
        root.addLayout(krow)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Measured", "File", "m", "Sensors", ""])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.itemDoubleClicked.connect(lambda _it: self._load())
        root.addWidget(self.table, 1)
        from PySide6.QtWidgets import QProgressBar
        self.bar = QProgressBar()
        self.bar.setVisible(False)
        root.addWidget(self.bar)
        self.lbl = QLabel("")
        self.lbl.setWordWrap(True)
        root.addWidget(self.lbl)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText("Load")
        self.buttons.accepted.connect(self._load)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)
        self._runs: List[Dict[str, Any]] = []
        self._fill()

    def _kind(self) -> str:
        return "aty" if self.rb_aty.isChecked() else "dty"

    def _fill(self) -> None:
        try:
            self._runs = sl.saved_runs(self._kind())
        except Exception as e:  # noqa: BLE001
            self._runs = []
            self.lbl.setText(f"<span style='color:#c0392b'>{error_text(e)}</span>")
        self.table.setRowCount(len(self._runs))
        for k, r in enumerate(self._runs):
            sens = ", ".join(f"{_head_label(x.get('head') or '')} {x.get('connector') or ''}" for x in (r.get("sensors") or []))
            vals = [str(r.get("at") or "").replace("T", " ")[:16], r["file"],
                    "–" if r.get("meters") is None else f"{r['meters']:.0f}", sens,
                    "exact (instant)" if r.get("exact") else "analysed again (takes a while)"]
            for c, val in enumerate(vals):
                self.table.setItem(k, c, QTableWidgetItem(val))
        self.table.resizeColumnsToContents()
        if self._runs:
            self.table.selectRow(0)
        else:
            self.lbl.setText("No saved live measurements in this folder.")

    def _load(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows or self._job is not None:
            return
        r = self._runs[rows[0].row()]
        if r.get("exact"):
            try:
                self.view = sl.load_saved(r["file"], self._kind())
            except Exception as e:  # noqa: BLE001
                self.lbl.setText(f"<span style='color:#c0392b'>{error_text(e)}</span>")
                return
            self.accept()
            return
        from ui.widgets.sensor_measure_dialog import _Job
        self.bar.setVisible(True)
        self.bar.setMaximum(0)
        self.lbl.setText("Analysing the signal again…")
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)
        self._job = _Job(sl.load_saved, {"file": r["file"], "kind": self._kind()}, True)
        self._job.progress.connect(lambda a, b: (self.bar.setMaximum(max(1, b)), self.bar.setValue(a)))
        self._job.finished_ok.connect(self._done)
        self._job.failed.connect(lambda e: self.lbl.setText(f"<span style='color:#c0392b'>{error_text(e)}</span>"))
        self._job.finished.connect(self._job_end)
        self._job.start()

    def _done(self, view: Dict[str, Any]) -> None:
        self.view = view
        self.accept()

    def _job_end(self) -> None:
        self._job = None
        self.bar.setVisible(False)
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(True)

    def reject(self) -> None:
        if self._job is not None:
            self._job.cancel()
        super().reject()

