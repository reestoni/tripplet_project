"""ui/yarnscope/sensor_measure.py - YarnScope measuring from TrippleT with a fake NI box (no hardware, no DB).

Checks: calibration and Sensoft configuration parsing, rate / point count like Sensoft, the TDMS is read by the
YarnScope readers exactly like a Sensoft file (channels, step 0.25 mm, file name -> series / trial), an existing
file is never overwritten (moved to _replaced only with replace=True), errors as codes.
"""
import datetime as dt

import numpy as np
import pytest

from ui.yarnscope import dty_service, aty_service
from ui.yarnscope import sensor_measure as sm
from ui.yarnscope.dty_tdms_reader import read_axis_channels, read_step_mm_from_tdms

CAL_2AX = """* PROFILE SENSOR PXL Wire CALIB. DATA FILE. PXL 3.121
16.12.2022
DCX_COEFF\t10267.73\t-1458.12\t[µm, µm/V]
ACX_SENSITIVITY\t-0.00084\t[V/µm]
DCX_OFFSET\t7.048\t[V]
DCY_COEFF\t10424.72\t-1480.20\t[µm, µm/V]
DCY_OFFSET\t7.048\t[V]
"""
CAL_1AX = """* PROFILE SENSOR LARGE CALIB. DATA FILE. 5.192
31.08.2021
DCX_COEFF\t2493.35\t-353.89\t[µm, µm/V]
"""
CONFIG = """[Sensoft ATY.vi]
Boxes 0.Device name = "Dev2"
Boxes 0.Heads 0.Name = "PXL_3_121_W"
Boxes 0.Heads 0.Active = "TRUE"
Boxes 0.Heads 0.Channel inputs 0 = "Dev2/ai1"
Boxes 0.Heads 0.Channel inputs 1 = "Dev2/ai9"
Boxes 0.Heads 1.Name = "OBD_5_192_M"
Boxes 0.Heads 1.Active = "FALSE"
Boxes 0.Heads 1.Channel inputs 0 = "Dev2/ai4"
Boxes 0.Heads 2.Name = "GONE_1_1_W"
Boxes 0.Heads 2.Channel inputs 0 = "Dev2/ai1"
"""


class FakeDaq(sm.Daq):
    """USB-6211-like: rate = 20 MHz / floor(20 MHz / asked) (50'800 -> 50'890.6 Hz as on the real box), returns a constant voltage per channel + small noise."""

    def __init__(self, volts=None):
        self.volts = volts or {"ai1": 7.078, "ai9": 6.690, "ai4": 7.0}
        self.calls = []

    def boxes(self):
        return [{"name": "Dev2", "product": "USB-6211", "serial": "1A6A875", "simulated": True}]

    def actual_rate(self, box, channels, rate):
        return 20e6 // 1 / (20e6 // rate)

    def read(self, box, channels, rate, n, progress=None, cancel=None):
        self.calls.append((box, list(channels), rate, n))
        rng = np.random.default_rng(1)
        data = np.array([self.volts[c] + rng.normal(0, 0.0014, n) for c in channels])
        if progress:
            progress(n, n)
        return self.actual_rate(box, channels, rate), data


@pytest.fixture
def env(tmp_path, monkeypatch):
    cal = tmp_path / "cal"
    cal.mkdir()
    (cal / "PXL_3_121_W.dat").write_text(CAL_2AX, encoding="latin-1")
    (cal / "OBD_5_192_M.dat").write_text(CAL_1AX, encoding="latin-1")
    sensoft = tmp_path / "Sensoft"
    (sensoft / "Config Data" / "Configurations ATY").mkdir(parents=True)
    (sensoft / "Config Data" / "Configurations ATY" / "Default config_Dev2_2A.ini").write_text(CONFIG, encoding="latin-1")
    dty, aty = tmp_path / "dty", tmp_path / "aty"
    dty.mkdir(); aty.mkdir()
    monkeypatch.setenv(sm.ENV_CAL_DIR, str(cal))
    monkeypatch.setenv(sm.ENV_SENSOFT_DIR, str(sensoft))
    monkeypatch.setenv(dty_service.ENV_TDMS_DIR, str(dty))
    monkeypatch.setenv(aty_service.ENV_TDMS_DIR, str(aty))
    fake = FakeDaq()
    sm.set_daq(fake)
    yield type("E", (), {"dty": dty, "aty": aty, "daq": fake})
    sm.set_daq(None)


def test_calibration_and_presets(env):
    h = sm.load_head("PXL_3_121_W")
    assert h.n_axes == 2 and h.date == "16.12.2022" and h.axes[0] == (10267.73, -1458.12)
    assert abs(h.to_um(np.array([7.078]), 0)[0] - (10267.73 - 1458.12 * 7.078)) < 1e-9
    assert sm.load_head("OBD_5_192_M").n_axes == 1
    presets = sm.sensor_presets()
    assert [(p["head"], p["connector"], p["axes"]) for p in presets] == [
        ("PXL_3_121_W", "C1", 2), ("OBD_5_192_M", "C2", 1)]       # head without calibration file left out
    assert sm.channels_for(h, "C1") == ["ai1", "ai9"]
    assert sm.channels_for(sm.load_head("OBD_5_192_M"), "C2") == ["ai4"]
    with pytest.raises(sm.MeasureError) as e:
        sm.load_head("..\\evil")
    assert e.value.code == "head_missing"


def test_plan_limits():
    assert sm.check_plan(762, 100, 2)[2] == pytest.approx(50800)
    for bad, code in ((0, "bad_speed"), ("x", "bad_speed"), (5000, "bad_speed")):
        with pytest.raises(sm.MeasureError) as e:
            sm.check_plan(bad, 100, 1)
        assert e.value.code == code
    with pytest.raises(sm.MeasureError) as e:
        sm.check_plan(762, 0, 1)
    assert e.value.code == "bad_length"
    with pytest.raises(sm.MeasureError) as e:
        sm.check_plan(2000, 100, 2)                    # 133 kHz x 2 > 250 kHz
    assert e.value.code == "rate_too_high" and e.value.vars["max_speed"] == 1875
    # like Sensoft: 100 m at 762 m/min with the box's real rate (50'890.6 Hz)
    assert 400_600 < sm.samples_for(100, 762, 20e6 / (20e6 // 50800)) < 400_800


def test_measure_writes_a_file_the_yarnscope_readers_take(env):
    when = dt.datetime(2026, 11, 20, 13, 11)
    res = sm.measure(series_id=466, trial_id=9001, vno=7, box="Dev2", head_name="PXL_3_121_W", connector="C1",
                     speed_m_min=762, length_m=10, kind="dty", user={"username": "soj"},
                     zero={"axes": [{"axis": "x", "mean_um": -53.3}]}, now=when)
    assert res["file"] == "466_7_201126_1311.tdms" and res["rate"] == pytest.approx(50890.6, abs=0.1)
    path = env.dty / res["file"]
    assert path.is_file() and not list(env.dty.glob("*.part"))
    assert env.daq.calls[-1][1] == ["ai1", "ai9"]
    x, y = read_axis_channels(path)
    assert len(x) == len(y) == res["points"]
    assert x.mean() == pytest.approx(10267.73 - 1458.12 * 7.078, abs=1)      # ≈ -53 µm like the probe
    assert y.mean() == pytest.approx(10424.72 - 1480.20 * 6.690, abs=1)      # ≈ 522 µm
    assert read_step_mm_from_tdms(path) == pytest.approx(0.25)
    assert dty_service.find_tdms(466, 7) == path                              # tab / automatic analysis find it
    assert dty_service.parse_tdms_ids(path.stem) == (466, 7)
    from nptdms import TdmsFile
    t = TdmsFile.read(path)
    g = t["Rohdaten"]
    assert [c.name for c in g.channels()] == ["466_7 (x-Achse)", "466_7 (y-Achse)", " " * 10,
                                              "Parameter", "Wert", "Einheit"]
    assert list(g["Wert"][:]) == ["466_7", "762", "0.25", "50800", "10"]
    assert t.properties["TrippleT.BoxSerial"] == "1A6A875" and t.properties["TrippleT.TrialID"] == 9001
    assert t.properties["TrippleT.EmptyX_um"] == -53.3


def test_one_axis_head_and_aty_folder(env):
    res = sm.measure(series_id=441, trial_id=1, vno=3, box="Dev2", head_name="OBD_5_192_M", connector="C2",
                     speed_m_min=512, length_m=5, kind="aty")
    x, y = read_axis_channels(env.aty / res["file"])
    assert y is None and len(x) == res["points"]
    assert aty_service.find_tdms(441, 3) == env.aty / res["file"]


def test_existing_file_is_never_overwritten(env):
    kw = dict(series_id=466, trial_id=1, vno=2, box="Dev2", head_name="PXL_3_121_W", connector="C1",
              speed_m_min=600, length_m=2)
    first = sm.measure(**kw, now=dt.datetime(2026, 11, 20, 9, 0))
    with pytest.raises(sm.MeasureError) as e:
        sm.measure(**kw)
    assert e.value.code == "exists" and e.value.vars["file"] == first["file"]
    second = sm.measure(**kw, replace=True, now=dt.datetime(2026, 11, 20, 10, 0))
    assert second["replaced"] == first["file"]
    assert (env.dty / sm.REPLACED_DIR / first["file"]).is_file()              # moved, not deleted
    assert sorted(p.name for p in env.dty.glob("*.tdms")) == [second["file"]]


def test_errors(env):
    kw = dict(series_id=1, trial_id=1, vno=1, head_name="PXL_3_121_W", connector="C1", speed_m_min=600, length_m=2)
    with pytest.raises(sm.MeasureError) as e:
        sm.measure(box="Dev1", **kw)
    assert e.value.code == "box_missing"
    with pytest.raises(sm.MeasureError) as e:
        sm.measure(box="Dev2", **{**kw, "connector": "C9"})
    assert e.value.code == "bad_connector"
    with sm._measuring():                                 # one measurement at a time
        with pytest.raises(sm.MeasureError) as e:
            sm.zero_check("Dev2", "PXL_3_121_W", "C1")
        assert e.value.code == "busy"
    z = sm.zero_check("Dev2", "PXL_3_121_W", "C1", seconds=0.5)
    assert [a["axis"] for a in z["axes"]] == ["x", "y"] and abs(z["axes"][0]["mean_um"] + 53) < 2


# ------------------------------------------------------------------------------------------ desktop dialog
@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _run_job(dlg, qapp):
    import time
    t0 = time.time()
    while dlg._job is not None and time.time() - t0 < 20:
        qapp.processEvents()
        time.sleep(0.01)
    qapp.processEvents()


def test_dialog_measures_and_moves_on(env, qapp, monkeypatch):
    from PySide6.QtCore import QSettings
    from ui.widgets import sensor_measure_dialog as smd
    QSettings("TrippleT", "SensorMeasure").clear()
    trials = [{"trial_id": 11, "vno": 1, "speed": 700.0, "dty": "466_1_x.tdms", "aty": None},
              {"trial_id": 12, "vno": 2, "speed": 762.0, "dty": None, "aty": None},
              {"trial_id": 13, "vno": 3, "speed": None, "dty": None, "aty": None}]

    def fake_trials(sid):
        names = {p.name for p in env.dty.glob("*.tdms")}
        return [{**t, "dty": t["dty"] or next((n for n in names if n.startswith(f"466_{t['vno']}_")), None)}
                for t in trials]
    monkeypatch.setattr(smd.sm, "trials_for", fake_trials)
    assert not smd.SensorMeasureDialog(466, {"username": "test", "access_level": 1}).btn_measure.isEnabled()
    dlg = smd.SensorMeasureDialog(466, {"username": "test", "access_level": 2})
    assert dlg.cb_box.currentData() == "Dev2"
    assert dlg.cb_sensor.currentData()["head"] == "PXL_3_121_W"
    assert dlg.cb_trial.currentData()["vno"] == 2           # first trial without a file
    assert dlg.sp_speed.value() == 762.0                     # speed from the trial
    assert dlg.btn_measure.text() == "2. Measure V002"
    dlg.sp_length.setValue(5)
    dlg._on_zero()
    _run_job(dlg, qapp)
    assert dlg._zero and "X:" in dlg.lbl_zero.text()
    dlg._on_measure(False)
    _run_job(dlg, qapp)
    assert "Saved" in dlg.lbl_result.text() and dlg.measured == 1
    assert [p.name.split("_")[1] for p in env.dty.glob("*.tdms")] == ["2"]
    assert dlg.cb_trial.currentData()["vno"] == 3             # moved on to the next trial
    assert dlg.btn_measure.text() == "2. Measure V003"
    dlg.close()


def test_dialog_free_mode_for_the_inspector(env, qapp):
    """TDMS Inspector: own name + speed, file to _manual, name counts up, on_measured gets the path."""
    from PySide6.QtCore import QSettings
    from ui.widgets import sensor_measure_dialog as smd
    QSettings("TrippleT", "SensorMeasure").clear()
    opened = []
    dlg = smd.SensorMeasureDialog(None, {"username": "test", "access_level": 2}, free=True, on_measured=opened.append)
    dlg.ed_name.setText("99999_34")
    dlg.sp_speed.setValue(764)
    dlg.sp_length.setValue(3)
    assert dlg.btn_measure.text() == "2. Measure 99999_34" and dlg.btn_measure.isEnabled()
    dlg._on_zero()
    _run_job(dlg, qapp)
    dlg._on_measure(False)
    _run_job(dlg, qapp)
    files = list((env.dty / sm.MANUAL_DIR).glob("99999_34_*.tdms"))
    assert len(files) == 1 and opened == [str(files[0])]
    assert dlg.ed_name.text() == "99999_35" and dlg.btn_measure.text() == "2. Measure 99999_35"
    dlg.close()


def test_speed_is_the_winder_speed():
    # Winder = Speed Shaft 2 x (1 - Winder % / 100) like the process schema; prod 466 V70: 800, 4.5 % -> 764
    assert sm.default_speed({"SpeedShaft2": 800, "Winder": 4.5}) == 764.0
    assert sm.default_speed({"SpeedShaft2": "600", "Winder": None}) == 600.0     # no winder % -> LW 2
    assert sm.default_speed({"SpeedShaft2": None, "Shaft2Speed": 460}) is None   # ATY: no proposal
    assert sm.default_speed({"SpeedShaft2": 0, "Winder": 3}) is None


def test_free_measurement_goes_to_manual_folder(env):
    when = dt.datetime(2026, 11, 23, 9, 5)
    kw = dict(box="Dev2", head_name="PXL_3_121_W", connector="C1", speed_m_min=764, length_m=4, now=when)
    res = sm.measure_free(name="466_5", **kw)
    path = env.dty / sm.MANUAL_DIR / "466_5_231126_0905.tdms"
    assert res["path"] == str(path) and path.is_file() and res["next_name"] == "466_6"
    assert dty_service.find_tdms(466, 5) is None              # never seen by the tab / the automatic analysis
    assert not list(env.dty.glob("*.tdms"))
    from nptdms import TdmsFile
    t = TdmsFile.read(path)
    assert list(t["Rohdaten"]["Wert"][:])[:2] == ["466_5", "764"] and t.properties["TrippleT.Manual"] == 1
    again = sm.measure_free(name="466_5", **kw)                # same name + minute -> seconds added, not overwritten
    assert again["file"] != res["file"] and len(list((env.dty / sm.MANUAL_DIR).glob("*.tdms"))) == 2
    for bad in ("", "a/b", r"..\x"):
        with pytest.raises(sm.MeasureError) as e:
            sm.measure_free(name=bad, **kw)
        assert e.value.code == "bad_name"
    assert sm.next_name("99999_009") == "99999_010" and sm.next_name("Fabel") == "Fabel_2"
