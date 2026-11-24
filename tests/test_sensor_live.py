"""ui/yarnscope/sensor_live.py - YarnScope Live with a fake streaming NI box (two sensors on the same yarn).

Rows every window (knots/m + CV per sensor, delay + measured speed), start / stop, the TDMS written piece by piece
(readable like a normal file, 2 files with a second sensor), one live session at a time, errors shown."""
import time

import numpy as np
import pytest

from test_sensor_measure import env  # noqa: F401  (fixture: tmp folders, calibration, Sensoft config, fake box)
from test_sensor_pair import _yarn
from ui.yarnscope import dty_service
from ui.yarnscope import sensor_live as sl
from ui.yarnscope import sensor_measure as sm
from ui.yarnscope.dty_tdms_reader import read_axis_channels, read_step_mm_from_tdms

LAG = 400


class StreamDaq(sm.Daq):
    """Same yarn for ai1/ai9 (sensor 1) and ai4 (sensor 2, LAG samples later); chunks as fast as possible."""

    def __init__(self, max_chunks=10_000):
        self.max_chunks = max_chunks
        self.base = _yarn(1_200_000 + LAG, seed=11)
        self.calls = []

    def boxes(self):
        return [{"name": "Dev2", "product": "USB-6211", "serial": "1A6A875", "simulated": True}]

    def actual_rate(self, box, channels, rate):
        return 20e6 / (20e6 // rate)

    def stream(self, box, channels, rate, on_chunk, should_stop, chunk_s=0.25):
        actual = self.actual_rate(box, channels, rate)
        k = int(actual * chunk_s)
        cal = {"ai1": (10267.73, -1458.12), "ai9": (10424.72, -1480.20), "ai4": (2493.35, -353.89)}
        rng = np.random.default_rng(2)
        self.calls.append(list(channels))
        pos = 0
        for _ in range(self.max_chunks):
            if should_stop() or pos + k > len(self.base) - LAG:
                break
            um = {"ai1": self.base[pos + LAG:pos + LAG + k], "ai9": self.base[pos + LAG:pos + LAG + k] + 150,
                  "ai4": self.base[pos:pos + k]}
            volts = np.array([(um[c] + rng.normal(0, 8, k) - cal[c][0]) / cal[c][1] for c in channels])
            on_chunk(volts, actual)
            pos += k
            time.sleep(0.002)
        return actual


def _wait(cond, timeout=60):
    t0 = time.time()
    while not cond() and time.time() - t0 < timeout:
        time.sleep(0.05)
    assert cond()


def test_live_two_sensors_rows_speed_and_files(env):  # noqa: F811
    sm.set_daq(StreamDaq())
    rate = 20e6 / (20e6 // (764 / 60 / 0.00025))
    dist = 764 / 60 * (LAG / rate) * 1000
    s = sl.start(box="Dev2", head_name="PXL_3_121_W", connector="C1", second={"head_name": "OBD_5_192_M", "connector": "C2"},
                 speed_m_min=764, distance_mm=dist, window_m=10, save=True, name="99999_70")
    with pytest.raises(sm.MeasureError) as e:                  # one live session at a time
        sl.start(box="Dev2", head_name="PXL_3_121_W", connector="C1", speed_m_min=764, save=False)
    assert e.value.code == "busy"
    _wait(lambda: len(s.rows) >= 3)
    sl.stop()
    v = s.view()
    assert v["state"] == "done" and v["error"] is None
    r = v["rows"][1]
    assert r["from_m"] == 10 and len(r["sensors"]) == 2
    assert 100 < r["sensors"][0]["fpm"] < 300 and r["sensors"][0]["cv"] > 0
    assert r["corr"] > 0.8 and r["speed"] == pytest.approx(764, rel=0.005)
    assert r["distance_from_speed_mm"] == pytest.approx(dist, abs=0.5)
    # files: written piece by piece, readable like any TDMS, both sensors, nothing left as .part
    manual = env.dty / sm.MANUAL_DIR
    assert sorted(f.name.split("_")[2] for f in manual.glob("*.tdms")) == ["C1", "C2"] and not list(manual.glob("*.part"))
    f1 = next(manual.glob("99999_70_C1_*.tdms"))
    x, y = read_axis_channels(f1)
    assert y is not None and len(x) == s.samples and read_step_mm_from_tdms(f1) == pytest.approx(0.25)
    assert dty_service.find_tdms(99999, 70) is None             # never a trial's file
    from nptdms import TdmsFile
    t = TdmsFile.read(f1)
    assert t.properties["TrippleT.Live"] == 1 and t.properties["TrippleT.PairFile"].startswith("99999_70_C2_")
    assert v["files"] == [f1.name, t.properties["TrippleT.PairFile"]]


def test_live_one_sensor_without_saving(env):  # noqa: F811
    sm.set_daq(StreamDaq())
    s = sl.start(box="Dev2", head_name="PXL_3_121_W", connector="C1", speed_m_min=764, window_m=10, save=False)
    _wait(lambda: len(s.rows) >= 2)
    sl.stop()
    r = s.view()["rows"][0]
    assert len(r["sensors"]) == 1 and "speed" not in r and r["sensors"][0]["fpm"] > 100
    assert not list((env.dty / sm.MANUAL_DIR).glob("*.tdms")) if (env.dty / sm.MANUAL_DIR).exists() else True


def test_live_errors(env):  # noqa: F811
    sm.set_daq(StreamDaq())
    with pytest.raises(sm.MeasureError) as e:
        sl.start(box="Dev9", head_name="PXL_3_121_W", connector="C1", speed_m_min=764, save=False)
    assert e.value.code == "box_missing"
    with pytest.raises(sm.MeasureError) as e:
        sl.start(box="Dev2", head_name="PXL_3_121_W", connector="C1", speed_m_min=764, save=True, name="a/b")
    assert e.value.code == "bad_name"

    class Broken(StreamDaq):
        def stream(self, *a, **k):
            raise sm.MeasureError("daq_error", "cable")
    sm.set_daq(Broken())
    s = sl.start(box="Dev2", head_name="PXL_3_121_W", connector="C1", speed_m_min=764, save=False)
    _wait(lambda: s.state in ("done", "error"))
    assert s.view()["state"] == "error" and s.view()["error"]["code"] == "daq_error"


def test_desktop_live_window(env, monkeypatch):  # noqa: F811
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication
    from ui.widgets import sensor_live_window as slw
    app = QApplication.instance() or QApplication([])
    QSettings("TrippleT", "SensorLive").clear()
    sm.set_daq(StreamDaq())
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)   # no empty value checked: start anyway
    w = slw.open_window({"username": "test", "access_level": 2})
    assert slw.open_window() is w                                # one window
    w.cb_second.setCurrentIndex(1)                               # OBD 5-192 on C2
    w.sp_speed.setValue(764)
    w.sp_window.setValue(10)
    w.ck_save.setChecked(False)
    w._on_start()
    assert w._running() and not w.btn_start.isEnabled() and w.btn_stop.isEnabled()
    t0 = time.time()
    while time.time() - t0 < 60 and len(sl.current().rows) < 2:
        app.processEvents()
        time.sleep(0.05)
    w._poll()
    assert w.table.rowCount() >= 2 and "knots/m" in w._tile_labels[0].text() and "CV" in w._tile_labels[1].text() and "m/min" in w._tile_labels[4].text()
    sl.stop()
    w._poll()
    assert "Finished" in w.lbl_status.text() and w.btn_start.isEnabled()
    w.close()
    assert slw._window is None


def test_screens_accept_the_live_callback():
    """The sidebar callbacks dict (main._sidebar_nav_kwargs) is passed as **kwargs to these screens."""
    import inspect
    from ui.screen_all_experiments import AllExperimentsScreen
    from ui.screen_backlog import BacklogScreen
    from ui.screen_home import HomeScreen
    from ui.screen_show_experiment import ShowExperimentScreen
    for cls in (ShowExperimentScreen, AllExperimentsScreen, BacklogScreen, HomeScreen):
        assert "on_yarnscope_live" in inspect.signature(cls.__init__).parameters, cls.__name__


class MovingYarnDaq(StreamDaq):
    """Auto speed: the box samples at a fixed rate; the yarn moves at a speed the software does NOT get (it changes
    from SPEED1 to SPEED2 half way). Sensor 1 (ai1/ai9) sees the yarn DIST_MM before sensor 2 (ai4)."""
    SPEED1, SPEED2, DIST_MM = 700.0, 760.0, 160.0

    def __init__(self):
        super().__init__()
        self.base = _yarn(1_400_000, seed=21)              # 350 m of yarn at 0.25 mm per point (ground truth)

    def stream(self, box, channels, rate, on_chunk, should_stop, chunk_s=0.25):
        k = int(rate * chunk_s)
        cal = {"ai1": (10267.73, -1458.12), "ai9": (10424.72, -1480.20), "ai4": (2493.35, -353.89)}
        rng = np.random.default_rng(3)
        pos_mm = 0.0
        sent = 0
        while not should_stop():
            v = self.SPEED1 if sent < 12 * rate else self.SPEED2            # 12 s, then faster
            p = pos_mm + np.arange(k) * (v / 60.0 / rate * 1000.0)
            pos_mm = p[-1] + v / 60.0 / rate * 1000.0
            idx_b = p / 0.25
            idx_a = (p + self.DIST_MM) / 0.25
            if idx_a[-1] >= len(self.base) - 2:
                break
            ya = np.interp(idx_a, np.arange(len(self.base)), self.base)
            yb = np.interp(idx_b, np.arange(len(self.base)), self.base)
            um = {"ai1": ya, "ai9": ya + 150, "ai4": yb}
            on_chunk(np.array([(um[c] + rng.normal(0, 8, k) - cal[c][0]) / cal[c][1] for c in channels]), rate)
            sent += k
            time.sleep(0.001)
        return rate


def test_live_auto_speed_measures_the_speed_itself(env):  # noqa: F811
    from ui.yarnscope.dty_analysis import analyze_series
    daq = MovingYarnDaq()
    sm.set_daq(daq)
    with pytest.raises(sm.MeasureError) as e:                  # auto speed needs two sensors + the distance
        sl.start(box="Dev2", head_name="PXL_3_121_W", connector="C1", speed_m_min=None, auto_speed=True, save=False)
    assert e.value.code == "auto_needs_two"
    s = sl.start(box="Dev2", head_name="PXL_3_121_W", connector="C1", second={"head_name": "OBD_5_192_M", "connector": "C2"},
                 speed_m_min=None, distance_mm=MovingYarnDaq.DIST_MM, auto_speed=True, window_m=30, save=True, name="99999_auto")
    _wait(lambda: s.meters() > 250, timeout=120)
    sl.stop()
    v = s.view()
    assert v["state"] == "done" and v["auto_speed"] and v["error"] is None
    speeds = [r["speed"] for r in v["rows"]]
    assert speeds[0] == pytest.approx(700, rel=0.01)                     # found by itself, nothing typed
    assert speeds[-1] == pytest.approx(760, rel=0.01)                    # follows the change
    truth = analyze_series(daq.base[:int(30_000 / 0.25)], 0.25, 3)["knots_per_m"]
    fpm = v["rows"][0]["sensors"][0]["fpm"]
    assert fpm == pytest.approx(truth, rel=0.03)                         # resampled to 0.25 mm: same knots/m
    f1 = next((env.dty / sm.MANUAL_DIR).glob("99999_auto_C1_*.tdms"))
    from nptdms import TdmsFile
    t = TdmsFile.read(f1)
    assert t.properties["TrippleT.AutoSpeed"] == 1 and 690 < t.properties["TrippleT.MeasuredSpeedMean"] < 770
    assert read_step_mm_from_tdms(f1) == pytest.approx(0.25, abs=0.003)
    x, _y = read_axis_channels(f1)
    assert len(x) * 0.25 / 1000 == pytest.approx(s.meters(), rel=0.02)  # metres in the file = metres measured


def test_desktop_window_auto_speed(env, monkeypatch):  # noqa: F811
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication
    from ui.widgets import sensor_live_window as slw
    app = QApplication.instance() or QApplication([])
    QSettings("TrippleT", "SensorLive").clear()
    sm.set_daq(MovingYarnDaq())
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)   # no empty value checked: start anyway
    w = slw.open_window({"username": "test", "access_level": 2})
    assert not w.ck_auto.isVisible() or not w.cb_second.currentData()
    w.cb_second.setCurrentIndex(1)
    w.sp_distance.setValue(160)
    w._sync()
    assert w._auto_on() and not w.sp_speed.isEnabled()          # no speed to type
    w.sp_window.setValue(10)
    w.ck_save.setChecked(False)
    w._on_start()
    t0 = time.time()
    while time.time() - t0 < 60 and len(sl.current().rows) < 2:
        app.processEvents()
        time.sleep(0.05)
    sl.stop()
    w._poll()
    assert sl.current().auto_speed and sl.current().rows[0]["speed"] == pytest.approx(700, rel=0.01)
    assert "700" in w._tile_labels[4].text()
    w.close()


def test_live_auto_speed_either_direction(env):  # noqa: F811
    """The yarn may pass the SECOND sensor first (main sensor downstream): the speed is found all the same."""
    class Reverse(MovingYarnDaq):
        DIST_MM = -160.0                                       # sensor 1 sees the yarn 160 mm AFTER sensor 2
    sm.set_daq(Reverse())
    s = sl.start(box="Dev2", head_name="PXL_3_121_W", connector="C1", second={"head_name": "OBD_5_192_M", "connector": "C2"},
                 speed_m_min=None, distance_mm=160, auto_speed=True, window_m=10, save=False)
    _wait(lambda: len(s.rows) >= 2, timeout=120)
    sl.stop()
    assert s.rows[0]["speed"] == pytest.approx(700, rel=0.01)


def test_desktop_live_full_size_chart_and_cv_tile(env, monkeypatch):  # noqa: F811
    """One chart at full size (button or double click, Esc / Back returns) and CV as its own tile (2026-11-24)."""
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication
    from ui.widgets import sensor_live_window as slw
    app = QApplication.instance() or QApplication([])
    QSettings("TrippleT", "SensorLive").clear()
    sm.set_daq(StreamDaq())
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)   # no empty value checked: start anyway
    w = slw.open_window({"username": "test", "access_level": 2})
    w.sp_speed.setValue(764)
    w.sp_window.setValue(10)
    w.ck_save.setChecked(False)
    w._on_start()
    t0 = time.time()
    while time.time() - t0 < 60 and len(sl.current().rows) < 2:
        app.processEvents()
        time.sleep(0.05)
    w._poll()
    texts = [lab.text() for lab in w._tile_labels if not lab.isHidden()]
    assert any("Knots/m" in t for t in texts) and any("CV" in t and "%" in t for t in texts) and len(texts) == 2
    assert w._zoom_btns["speed"].isHidden()                      # one sensor: no speed chart
    w._set_focus("cv")
    assert [k for _a, k in w._ax_keys] == ["cv"] and not w.btn_unzoom.isHidden() and w.table.isHidden()
    w._set_focus(None)
    assert [k for _a, k in w._ax_keys] == ["fpm", "cv"] and not w.table.isHidden()
    sl.stop()
    w.close()


def test_live_empty_value(env):  # noqa: F811
    """YarnScope Live can check the empty value (2026-11-24): same remembered value as the measure window, written
    into the live files."""
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication
    from ui.widgets import sensor_live_window as slw
    QApplication.instance() or QApplication([])
    QSettings("TrippleT", "SensorLive").clear()
    sm.forget_zeros()
    w = slw.open_window({"username": "test", "access_level": 2})     # env's fake box can read (zero_check)
    assert "Without yarn" in w.lbl_zero.text() and w.btn_zero.isEnabled()
    w._on_zero()
    assert "µm" in w.lbl_zero.text() and "kept until" in w.lbl_zero.text() and "again" in w.btn_zero.text()
    z = sm.remembered_zero("Dev2", "PXL_3_121_W", "C1")
    sm.set_daq(StreamDaq())
    s = sl.start(box="Dev2", head_name="PXL_3_121_W", connector="C1", speed_m_min=764, window_m=10, save=True,
                 name="99999_zero")
    assert s.zero == z
    _wait(lambda: len(s.rows) >= 1)
    sl.stop()
    from nptdms import TdmsFile
    f = next((env.dty / sm.MANUAL_DIR).glob("99999_zero_*.tdms"))
    assert TdmsFile.read(f).properties["TrippleT.EmptyX_um"] == z["axes"][0]["mean_um"]
    w.close()
