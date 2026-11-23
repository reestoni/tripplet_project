"""sensor_live_window.py - "YarnScope Live" window (Nutzerwunsch 2026-11-23; web /tools/yarnscope-live).

Continuous measurement with a small dashboard: start / stop by hand, every window (default 30 m) knots/m + CV per
sensor and, with a second sensor + the distance, the measured speed; optionally saved to the _manual folder.
Logic: ui/yarnscope/sensor_live.py (shared with the web). Opened from the sidebar (Tools) - one window, not modal.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QRadioButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ui.widgets.sensor_measure_dialog import error_text
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
        self._fig = None
        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
            self._fig = Figure(figsize=(7, 2.4), tight_layout=True)
            self._canvas = FigureCanvasQTAgg(self._fig)
            right.addWidget(self._canvas)
        except Exception:  # noqa: BLE001 - the table is enough then
            self._canvas = None
        self.table = QTableWidget(0, 0)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        right.addWidget(self.table, 1)
        rw = QWidget()
        rw.setLayout(right)
        root.addWidget(rw, 1)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(1000)
        self._load_sensors()
        self._load_boxes()
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
            if d and main and d.get("connector") != main.get("connector"):
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
        self.sp_distance.setEnabled(not run and bool(self.cb_second.currentData()))
        self.ck_auto.setVisible(bool(self.cb_second.currentData()))
        self.ck_auto.setEnabled(not run and self.sp_distance.value() > 0)
        self.sp_speed.setEnabled(not run and not self._auto_on())
        if self.read_only:
            self.lbl_msg.setText("Write access required (AccessLevel > 1).")

    # ------------------------------------------------------------------------------------------- actions
    def _auto_on(self) -> bool:
        return self.ck_auto.isChecked() and bool(self.cb_second.currentData()) and self.sp_distance.value() > 0

    def _on_start(self) -> None:
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
        rows = v["rows"]
        self._tiles(v, rows[-1] if rows else None)
        if len(rows) != self._shown:
            self._fill_table(v, rows)
            self._draw(v, rows)
            self._shown = len(rows)

    def _tiles(self, v: Dict[str, Any], last: Optional[Dict[str, Any]]) -> None:
        sens = v.get("sensors") or []
        n = len(sens) + (1 if len(sens) > 1 else 0)
        while len(self._tile_labels) < n:
            lab = QLabel()
            lab.setFrameShape(QFrame.StyledPanel)
            lab.setMinimumHeight(70)
            self.tiles.addWidget(lab, 0, len(self._tile_labels))
            self._tile_labels.append(lab)
        f = lambda x, d=1: "–" if x is None else f"{x:.{d}f}"  # noqa: E731
        for i, s in enumerate(sens):
            r = (last or {}).get("sensors", [{}] * len(sens))[i] if last else {}
            self._tile_labels[i].setStyleSheet(f"QLabel{{border-left:5px solid {COLORS[i % 2]};padding:6px;}}")
            self._tile_labels[i].setText(f"<span style='color:#666'>{_head_label(s['head'])} · {s['connector']}</span><br>"
                                         f"<span style='font-size:24px;font-weight:bold'>{f(r.get('fpm'))}</span> knots/m"
                                         f"<br>CV {f(r.get('cv'))} %")
        if len(sens) > 1:
            lab = self._tile_labels[len(sens)]
            sp = (last or {}).get("speed")
            extra = (f"delay {f((last or {}).get('delay_ms'), 3)} ms · match {f((last or {}).get('corr'), 2)}"
                     if last and last.get("delay_ms") is not None else "the two signals do not match yet")
            if last and sp is None and last.get("distance_from_speed_mm") is not None:
                extra += f" · {last['distance_from_speed_mm']:.1f} mm apart at the set speed"
            lab.setText(f"<span style='color:#666'>Speed</span><br><span style='font-size:24px;font-weight:bold'>"
                        f"{f(sp)}</span> m/min<br><span style='color:#666'>{extra}</span>")
        for j, lab in enumerate(self._tile_labels):
            lab.setVisible(j < n)

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
        x = [r["to_m"] for r in rows]
        n = 3 if two else 2
        for k, (key, title) in enumerate((("fpm", "Knots/m"), ("cv", "CV knot spacing %"))):
            ax = self._fig.add_subplot(1, n, k + 1)
            for i, s in enumerate(sens):
                ax.plot(x, [r["sensors"][i].get(key) if i < len(r["sensors"]) else None for r in rows], marker="o",
                        ms=3, color=COLORS[i % 2], label=f"{_head_label(s['head'])} {s['connector']}")
            ax.set_title(title, fontsize=9)
            ax.tick_params(labelsize=8)
            if two and k == 0:
                ax.legend(fontsize=7)
        if two:
            ax = self._fig.add_subplot(1, n, 3)
            ax.plot(x, [r.get("speed") for r in rows], marker="o", ms=3, color=COLORS[0])
            ax.set_title("Speed m/min", fontsize=9)
            ax.tick_params(labelsize=8)
        self._canvas.draw_idle()

    def closeEvent(self, ev) -> None:  # noqa: N802 - Qt
        if self._running():
            if QMessageBox.question(self, "YarnScope Live", "A live measurement is running. Stop it?") != QMessageBox.Yes:
                ev.ignore()
                return
            sl.stop()
        self._timer.stop()
        global _window
        _window = None
        super().closeEvent(ev)
