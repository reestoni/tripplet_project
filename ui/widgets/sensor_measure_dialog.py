"""sensor_measure_dialog.py - "Measure (YarnScope)" in Show Experiment (Nutzerwunsch 2026-11-20, F&E feasibility).

Records a YarnScope TDMS straight from the NI box instead of Sensoft ATY: box + sensor (from the user's Sensoft
configurations), check the empty value (no yarn), pick the trial (speed proposed from its machine data), measure.
After a measurement the next trial is selected (like Sensoft counting up). Logic: ui/yarnscope/sensor_measure.py
(shared with the web app). The automatic analysis of the web server picks the new files up.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QSettings, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QProgressBar, QPushButton, QRadioButton, QVBoxLayout, QWidget,
)

from ui.yarnscope import sensor_measure as sm
from ui.yarnscope.sensor_pair import DEFAULT_DISTANCE_MM as _DEFAULT_DISTANCE

ERRORS = {
    "no_nidaqmx": "The Python package nidaqmx is missing - install it (pip install nidaqmx).",
    "no_driver": "The NI-DAQmx driver is not installed or not running.",
    "box_missing": "Box {box} is not connected.",
    "head_missing": "No calibration file for sensor head {head}.",
    "bad_connector": "Unknown connector {connector}.",
    "bad_speed": "Speed must be between {lo:g} and {hi:g} m/min.",
    "bad_length": "Length must be between {lo:g} and {hi:g} m.",
    "rate_too_high": "Too fast for this sensor on the box - at most {max_speed} m/min.",
    "folder_missing": "The TDMS folder is not reachable: {folder}",
    "exists": "This trial already has a measurement ({file}).",
    "busy": "A measurement is already running.",
    "cancelled": "Measurement cancelled - nothing saved.",
    "daq_error": "The box reported an error: {detail}",
    "bad_kind": "Unknown folder.",
    "bad_name": "Name not allowed: letters, digits, _ . - and spaces, at most 60 characters.",
    "same_connector": "Both sensors are on connector {connector} - choose a sensor on the other connector.",
    "auto_needs_two": "Measuring the speed needs a second sensor and the distance between the sensors.",
}


def pair_text(res: Dict[str, Any]) -> str:
    """HTML lines for a simultaneous measurement (sensor_pair.pair_report), '' with one sensor."""
    sec, pair = res.get("second"), res.get("pair")
    if not sec:
        return ""
    out = [f"2nd sensor: {sec['file']}"]
    if not pair or not pair.get("reliable"):
        out.append(f"<span style='color:#c0392b'>The two signals do not match (match {(pair or {}).get('corr')}) - "
                   f"no speed, no knot comparison. Is the same yarn running through both sensors?</span>")
        return "<br>" + "<br>".join(out)
    out.append(f"<b>Both sensors</b> · delay {pair.get('delay_ms', 0):.3f} ms · match {pair.get('corr')}")
    if pair.get("speed") is not None:
        dev = pair.get("speed_dev_pct")
        out.append(f"<b>Measured speed {pair['speed']:.1f} m/min</b>" + (f" ({dev:+.2f} %)" if dev is not None else ""))
    elif pair.get("distance_from_speed_mm") is not None:
        out.append(f"At the set speed the sensors are {pair['distance_from_speed_mm']:.1f} mm apart")
    prof = [x.get("speed") for x in pair.get("profile") or []]
    if any(v is not None for v in prof):
        out.append("Speed per 10 m: " + " · ".join("–" if v is None else f"{v:.0f}" for v in prof))
    k = pair.get("knots") or {}
    if k.get("pct_a") is not None:
        out.append(f"Same knots: {k['pct_a']} % of sensor 1, {k.get('pct_b')} % of sensor 2 "
                   f"({k.get('only_a', 0)} / {k.get('only_b', 0)} seen by only one)")
        if k.get("len_diff_mm") is not None:
            out.append(f"Knot length sensor 2 − sensor 1: {k['len_diff_mm']:.2f} mm (± {k.get('len_diff_sd_mm') or 0:.2f})")
    return "<br>" + "<br>".join(out)


def _zero_all(box: str, head_name: str, connector: str, second: Optional[Dict[str, Any]] = None,
              distance_mm: Any = None) -> Dict[str, Any]:
    """Empty value of the main sensor and, if chosen, of the second one (axes carry the connector)."""
    z = sm.zero_check(box, head_name, connector)
    if second:
        z["axes"] += sm.zero_check(box, second["head_name"], second["connector"])["axes"]
    return z


def error_text(e: Exception) -> str:
    if isinstance(e, sm.MeasureError):
        try:
            return ERRORS.get(e.code, "{detail}").format(**{"detail": e.detail, **(e.vars or {})})
        except (KeyError, ValueError):
            return e.detail
    return str(e)


class _Job(QThread):
    progress = Signal(int, int)
    finished_ok = Signal(dict)
    failed = Signal(object)

    def __init__(self, fn, kwargs: Dict[str, Any], with_progress: bool = True):
        super().__init__()
        self._fn, self._kwargs, self._cancel, self._with_progress = fn, kwargs, False, with_progress

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            kw = dict(self._kwargs)
            if self._with_progress:
                kw["progress"] = lambda a, b: self.progress.emit(int(a), int(b))
                kw["cancel"] = lambda: self._cancel
            self.finished_ok.emit(self._fn(**kw))
        except Exception as e:  # noqa: BLE001 - shown to the user
            self.failed.emit(e)


class SensorMeasureDialog(QDialog):
    def __init__(self, series_id: Optional[int], user: Optional[Dict[str, Any]] = None, parent: Optional[QWidget] = None,
                 free: bool = False, on_measured=None):
        """free = TDMS Inspector (Nutzerwunsch 2026-11-23): own name + speed instead of a trial, file to _manual,
        on_measured(path) after each measurement (the inspector opens it)."""
        super().__init__(parent)
        self.free, self.on_measured = bool(free), on_measured
        self.setWindowTitle("Measure (free name)" if self.free else "Measure (YarnScope)")
        self.setMinimumWidth(560)
        self.series_id, self.user = (int(series_id) if series_id is not None else None), user or {}
        try:                               # measuring writes a file to the share: AccessLevel 2+ (like other writes)
            self.read_only = int((user or {}).get("access_level") or 0) < 2
        except (TypeError, ValueError):
            self.read_only = True
        self.measured = 0
        self._job: Optional[_Job] = None
        self._zero: Optional[Dict[str, Any]] = None
        self._trials: List[Dict[str, Any]] = []
        self._settings = QSettings("TrippleT", "SensorMeasure")

        root = QVBoxLayout(self)
        hint = QLabel(
            f"Records the yarn signal under your own name and speed - no series, nothing in the database. The file "
            f"goes to the sub-folder '{sm.MANUAL_DIR}' of the YarnScope folder (the automatic analysis ignores it) "
            f"and opens in the inspector." if self.free else
            "Records the yarn signal directly from the NI box (instead of Sensoft). No master "
            "measurement needed. The file goes to the YarnScope folder and is analysed automatically.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#555;")
        root.addWidget(hint)

        form = QFormLayout()
        row = QHBoxLayout()
        self.cb_box = QComboBox()
        btn_rescan = QPushButton("↻")
        btn_rescan.setFixedWidth(32)
        btn_rescan.setToolTip("Look for boxes again")
        btn_rescan.clicked.connect(self._load_boxes)
        row.addWidget(self.cb_box, 1)
        row.addWidget(btn_rescan)
        form.addRow("Box:", row)
        self.cb_sensor = QComboBox()
        self.cb_sensor.currentIndexChanged.connect(lambda _i: (self._fill_second(), self._reset_zero()))
        form.addRow("Sensor:", self.cb_sensor)
        # 2nd sensor on the other connector, read in the same measurement (Nutzerwunsch 2026-11-23)
        self.cb_second = QComboBox()
        self.cb_second.currentIndexChanged.connect(lambda _i: (self._reset_zero(), self._sync()))
        form.addRow("2nd sensor at once:", self.cb_second)
        self.sp_distance = QDoubleSpinBox()
        self.sp_distance.setRange(0, 100000)
        self.sp_distance.setDecimals(1)
        self.sp_distance.setSuffix(" mm")
        self.sp_distance.setSpecialValueText("– (only the delay)")
        self.sp_distance.setToolTip("Distance between the two sensors - gives the measured speed")
        self.sp_distance.setValue(float(self._settings.value("distance", _DEFAULT_DISTANCE) or 0))
        form.addRow("Distance:", self.sp_distance)
        kind_row = QHBoxLayout()
        self.rb_dty, self.rb_aty = QRadioButton("DTY (YarnScopeTDMS)"), QRadioButton("ATY (ATYtdms)")
        grp = QButtonGroup(self)
        grp.addButton(self.rb_dty)
        grp.addButton(self.rb_aty)
        (self.rb_aty if self._settings.value("kind") == "aty" else self.rb_dty).setChecked(True)
        self.rb_dty.toggled.connect(lambda _c: None if self.free else self._fill_trials())
        kind_row.addWidget(self.rb_dty)
        kind_row.addWidget(self.rb_aty)
        kind_row.addStretch(1)
        form.addRow("Folder:", kind_row)
        root.addLayout(form)

        zrow = QHBoxLayout()
        self.btn_zero = QPushButton("1. Check empty value (no yarn)")
        self.btn_zero.clicked.connect(self._on_zero)
        self.lbl_zero = QLabel("–")
        zrow.addWidget(self.btn_zero)
        zrow.addWidget(self.lbl_zero, 1)
        root.addLayout(zrow)

        form2 = QFormLayout()
        self.cb_trial = QComboBox()
        self.cb_trial.currentIndexChanged.connect(self._on_trial)
        self.ed_name = QLineEdit(str(self._settings.value("free_name", "99999_1")))
        self.ed_name.setMaxLength(60)
        self.ed_name.setPlaceholderText("e.g. 99999_34 - counts up after each measurement")
        self.ed_name.textChanged.connect(lambda _t: self._sync())
        if self.free:
            form2.addRow("Name:", self.ed_name)
        else:
            form2.addRow("Trial:", self.cb_trial)
        self.sp_speed = QDoubleSpinBox()
        self.sp_speed.setRange(*sm.SPEED_RANGE)
        self.sp_speed.setDecimals(1)
        self.sp_speed.setSuffix(" m/min")
        self.sp_speed.setValue(float(self._settings.value("free_speed", 600)) if self.free else 600)
        form2.addRow("Speed:", self.sp_speed)
        self.sp_length = QDoubleSpinBox()
        self.sp_length.setRange(*sm.LENGTH_RANGE)
        self.sp_length.setDecimals(0)
        self.sp_length.setSuffix(" m")
        self.sp_length.setValue(float(self._settings.value("length", sm.DEFAULT_LENGTH_M)))
        form2.addRow("Length:", self.sp_length)
        root.addLayout(form2)

        self.bar = QProgressBar()
        self.bar.setVisible(False)
        root.addWidget(self.bar)
        self.lbl_result = QLabel("")
        self.lbl_result.setWordWrap(True)
        self.lbl_result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(self.lbl_result)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.btn_measure = QPushButton("2. Measure")
        self.btn_measure.setDefault(True)
        self.btn_measure.setMinimumHeight(32)
        self.btn_measure.setStyleSheet("QPushButton{background:#39A650;color:white;font-weight:bold;padding:0 18px;}"
                                       "QPushButton:disabled{background:#b9d9c0;}")
        self.btn_measure.clicked.connect(lambda: self._on_measure(False))
        self.btn_cancel = QPushButton("Cancel measurement")
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self._on_cancel)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_measure)
        btns.addWidget(btn_close)
        root.addLayout(btns)

        self._load_sensors()
        self._load_boxes()
        if not self.free:
            self._load_trials()
        self._sync()

    # ---------------------------------------------------------------------------------------------- lists
    def _kind(self) -> str:
        return "aty" if self.rb_aty.isChecked() else "dty"

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
        last = self._settings.value("box")
        i = self.cb_box.findData(last) if last else -1
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
            self.cb_sensor.setItemData(self.cb_sensor.count() - 1, f"{p['title']} – calibrated {p['date']}",
                                       Qt.ToolTipRole)
        last = self._settings.value("sensor")
        for i in range(self.cb_sensor.count()):
            d = self.cb_sensor.itemData(i)
            if d and d.get("key") == last:
                self.cb_sensor.setCurrentIndex(i)
        self._fill_second()

    def _fill_second(self) -> None:
        """2nd sensor list: '– none –' + the sensors on the OTHER connector than the main one."""
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
        has = bool(self.cb_second.currentData())
        self.sp_distance.setEnabled(has)

    def _load_trials(self, select_vno: Optional[int] = None) -> None:
        try:
            self._trials = sm.trials_for(self.series_id)
        except Exception as e:  # noqa: BLE001
            self._trials = []
            self.lbl_result.setText(f"Trials not loaded: {e}")
        self._fill_trials(select_vno)

    def _fill_trials(self, select_vno: Optional[int] = None) -> None:
        cur = select_vno if select_vno is not None else (self.cb_trial.currentData() or {}).get("vno")
        self.cb_trial.blockSignals(True)
        self.cb_trial.clear()
        kind = self._kind()
        first_free = None
        for t in self._trials:
            f = t.get(kind)
            self.cb_trial.addItem(f"V{t['vno']:03d}" + (f"   ✓ measured ({f})" if f else ""), t)
            if not f and first_free is None:
                first_free = self.cb_trial.count() - 1
        self.cb_trial.blockSignals(False)
        idx = next((i for i in range(self.cb_trial.count()) if self.cb_trial.itemData(i)["vno"] == cur), None)
        if idx is None:
            idx = first_free if first_free is not None else 0
        if self.cb_trial.count():
            self.cb_trial.setCurrentIndex(idx)
            self._on_trial(idx)
        self._sync()

    def _on_trial(self, _i: int) -> None:
        t = self.cb_trial.currentData()
        if t and t.get("speed"):
            self.sp_speed.setValue(float(t["speed"]))
        self._sync()

    def _reset_zero(self) -> None:
        self._zero = None
        self.lbl_zero.setText("–")

    def _sync(self) -> None:
        busy = self._job is not None
        target = self.ed_name.text().strip() if self.free else (
            f"V{self.cb_trial.currentData()['vno']:03d}" if self.cb_trial.currentData() else "")
        ok = bool(self.cb_box.currentData()) and bool(self.cb_sensor.currentData()) and bool(target)
        self.btn_measure.setEnabled(ok and not busy and not self.read_only)
        self.btn_measure.setText(f"2. Measure {target}".rstrip())   # like the web: "2. Measure V002" / "99999_35"
        self.btn_zero.setEnabled(bool(self.cb_box.currentData()) and bool(self.cb_sensor.currentData()) and not busy
                                 and not self.read_only)
        if self.read_only and not self.lbl_result.text():
            self.lbl_result.setText("Write access required (AccessLevel > 1).")
        self.btn_cancel.setVisible(busy)
        self.sp_distance.setEnabled(bool(self.cb_second.currentData()) and not busy)

    # ------------------------------------------------------------------------------------------- actions
    def _sel(self) -> Dict[str, Any]:
        p = self.cb_sensor.currentData() or {}
        p2 = self.cb_second.currentData() or {}
        return {"box": self.cb_box.currentData(), "head_name": p.get("head"), "connector": p.get("connector"),
                "second": {"head_name": p2["head"], "connector": p2["connector"]} if p2 else None,
                "distance_mm": self.sp_distance.value() or None}

    def _remember(self) -> None:
        for k, v in (("box", self.cb_box.currentData()), ("sensor", (self.cb_sensor.currentData() or {}).get("key")),
                     ("second", (self.cb_second.currentData() or {}).get("key") or ""),
                     ("distance", self.sp_distance.value()), ("kind", self._kind()), ("length", self.sp_length.value())):
            self._settings.setValue(k, v)

    def _start(self, fn, kwargs, ok, with_progress=True) -> None:
        self._job = _Job(fn, kwargs, with_progress)
        self._job.progress.connect(self._on_progress)
        self._job.finished_ok.connect(ok)
        self._job.failed.connect(self._on_failed)
        self._job.finished.connect(self._on_job_end)
        self._sync()
        self._job.start()

    def _on_job_end(self) -> None:
        self._job = None
        self.bar.setVisible(False)
        self._sync()
        ask, self._ask_replace = getattr(self, "_ask_replace", None), None
        if ask is not None:            # "exists": ask only now - the old job is completely finished
            ans = QMessageBox.question(
                self, "Already measured",
                f"{error_text(ask)}\n\nMeasure again? The old file is moved to the sub-folder "
                f"'{sm.REPLACED_DIR}' (not deleted).")
            if ans == QMessageBox.Yes:
                self._on_measure(True)
            else:
                self.lbl_result.setText(error_text(ask))

    def _on_failed(self, e: Exception) -> None:
        if isinstance(e, sm.MeasureError) and e.code == "exists":
            self._ask_replace = e
            return
        self.lbl_result.setText(f"<span style='color:#c0392b'>{error_text(e)}</span>")

    def _on_progress(self, a: int, b: int) -> None:
        self.bar.setVisible(True)
        self.bar.setMaximum(max(1, b))
        self.bar.setValue(a)

    def _on_zero(self) -> None:
        s = self._sel()
        self.lbl_zero.setText("measuring …")
        self._start(_zero_all, s, self._zero_done, with_progress=False)

    def _zero_done(self, z: Dict[str, Any]) -> None:
        self._zero = z
        two = len({a.get("connector") for a in z["axes"]}) > 1
        self.lbl_zero.setText("   ".join(f"{a['connector'] + ' ' if two else ''}{a['axis'].upper()}: "
                                        f"{a['mean_um']:.1f} µm (± {a['std_um']:.1f})" for a in z["axes"]))

    def _on_measure(self, replace: bool) -> None:
        if self.free:
            self._on_measure_free()
            return
        t = self.cb_trial.currentData()
        if not t:
            return
        if self._zero is None and not replace:
            if QMessageBox.question(self, "Measure", "The empty value (no yarn) was not checked. Measure anyway?") \
                    != QMessageBox.Yes:
                return
        s = self._sel()
        self._remember()
        self.lbl_result.setText(f"Measuring V{t['vno']:03d} …")
        self._last_kwargs = dict(series_id=self.series_id, trial_id=t["trial_id"], vno=t["vno"], **s,
                                 speed_m_min=self.sp_speed.value(), length_m=self.sp_length.value(),
                                 kind=self._kind(), replace=replace, user=self.user, zero=self._zero)
        self._start(sm.measure, self._last_kwargs, self._measure_done)

    def _on_measure_free(self) -> None:
        if self._zero is None and QMessageBox.question(
                self, "Measure", "The empty value (no yarn) was not checked. Measure anyway?") != QMessageBox.Yes:
            return
        s = self._sel()
        self._remember()
        self._settings.setValue("free_speed", self.sp_speed.value())
        name = self.ed_name.text().strip()
        self.lbl_result.setText(f"Measuring {name} …")
        self._last_kwargs = dict(name=name, **s, speed_m_min=self.sp_speed.value(), length_m=self.sp_length.value(),
                                 kind=self._kind(), user=self.user, zero=self._zero)
        self._start(sm.measure_free, self._last_kwargs, self._measure_free_done)

    def _measure_free_done(self, res: Dict[str, Any]) -> None:
        self.measured += 1
        axes = "   ".join(f"{a['axis'].upper()} Ø {a['mean_um']:.0f} µm" for a in res["axes"])
        pts = f"{res['points']:,}".replace(",", "'")
        self.lbl_result.setText(f"<b>Saved:</b> {res['file']} – {pts} points at {res['rate']:.1f} Hz"
                                f"<br>{axes} – opened in the inspector" + pair_text(res))
        self.ed_name.setText(res["next_name"])
        self._settings.setValue("free_name", res["next_name"])
        if callable(self.on_measured):
            self.on_measured(res["path"])

    def _measure_done(self, res: Dict[str, Any]) -> None:
        self.measured += 1
        axes = "   ".join(f"{a['axis'].upper()} Ø {a['mean_um']:.0f} µm" for a in res["axes"])
        extra = f"<br>Old file moved to {sm.REPLACED_DIR}\\{res['replaced']}." if res.get("replaced") else ""
        pts = f"{res['points']:,}".replace(",", "'")
        self.lbl_result.setText(f"<b>Saved:</b> {res['file']} – {pts} points at {res['rate']:.1f} Hz"
                                f"<br>{axes}{extra}" + pair_text(res))
        done_vno = next((t["vno"] for t in self._trials if t["trial_id"] == self._last_kwargs["trial_id"]), None)
        nxt = None
        if done_vno is not None:
            later = [t["vno"] for t in self._trials if t["vno"] > done_vno]
            nxt = later[0] if later else done_vno
        self._load_trials(select_vno=nxt)

    def closeEvent(self, ev) -> None:  # noqa: N802 - Qt
        if self._job is not None:
            if QMessageBox.question(self, "Measure", "A measurement is running. Cancel it?") != QMessageBox.Yes:
                ev.ignore()
                return
            self._job.cancel()
            self._job.wait(15000)
        super().closeEvent(ev)

    def _on_cancel(self) -> None:
        if self._job is not None:
            self._job.cancel()

