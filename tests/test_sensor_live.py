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
        self.base = _yarn(3_000_000 + LAG, seed=11)
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


def test_desktop_live_window(env):  # noqa: F811
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication
    from ui.widgets import sensor_live_window as slw
    app = QApplication.instance() or QApplication([])
    QSettings("TrippleT", "SensorLive").clear()
    sm.set_daq(StreamDaq())
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
    assert w.table.rowCount() >= 2 and "knots/m" in w._tile_labels[0].text() and "m/min" in w._tile_labels[2].text()
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
