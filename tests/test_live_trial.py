"""Bookmarks of YarnScope Live (sensor_live.LiveSession.bookmark) and a new trial from one (ui/yarnscope/live_trial.py).

Fake streaming box (test_sensor_live.StreamDaq), tmp folders; the database calls of the copy are replaced, so nothing is
written to a database. Checks: "Merken" copies the last N m (length changeable, limits), knots/m of that stretch, the
trial copy gets the typed values (validated like the copy dialog), the TDMS only when asked, with the trial's name in
the trial folder (an older file to _replaced), "only as file" to _manual."""
import datetime as dt

import pytest

from test_sensor_live import StreamDaq, _wait
from test_sensor_measure import env  # noqa: F401
from db import trial_actions as ta
from db import trial_copy as tc
from ui.yarnscope import dty_service, live_trial
from ui.yarnscope import sensor_live as sl
from ui.yarnscope import sensor_measure as sm
from ui.yarnscope.dty_tdms_reader import read_axis_channels, read_step_mm_from_tdms

FIELDS = [tc.CopyField("trial:JetID", "Jet", "trial", "JetID", choices=[(5, "LB-04"), (9, "P212")], default=True),
          tc.CopyField("trial:AirPressure", "Air Pressure (bar)", "trial", "AirPressure", rule="air", default=True),
          tc.CopyField("trial:SpeedShaft2", "Speed", "trial", "SpeedShaft2", rule="onlyDoubles", default=True),
          tc.CopyField("trial:Shaft2x_OF", "OF", "trial", "Shaft2x_OF", rule="onlyDoubles", default=True),
          tc.CopyField("trial:Comment", "Comment", "trial", "Comment")]


@pytest.fixture
def fake_db(monkeypatch):
    made = []

    def setup(series_id):
        return {"trials": [{"id": 101, "vno": 1}, {"id": 102, "vno": 2}], "fields": FIELDS, "next_no": 3,
                "source": {101: {"trial:JetID": 5, "trial:AirPressure": 3.0}, 102: {"trial:JetID": 9, "trial:AirPressure": 3.2}},
                "labs": []}

    def copy(series_id, plan, fields, user=None, lab_tables=None):
        made.append((series_id, plan))
        return [555], None
    monkeypatch.setattr(ta, "copy_trials_setup", setup)
    monkeypatch.setattr(ta, "copy_trials", copy)
    import db.connection
    monkeypatch.setattr(db.connection, "fetch_all", lambda sql, params=(): [{"Versuchsnummer": 3}])
    return made


def _session(n_rows=2):
    sm.set_daq(StreamDaq())
    s = sl.start(box="Dev2", head_name="PXL_3_121_W", connector="C1", speed_m_min=764, window_m=10, save=False)
    _wait(lambda: s.meters() >= 130)
    return s


def test_bookmark_takes_the_last_metres(env):  # noqa: F811
    s = _session()
    b = s.bookmark()                                   # default 100 m
    b2 = s.bookmark(length_m=20, label="3.4 bar")
    sl.stop()
    assert b["length_m"] == pytest.approx(100, abs=0.5) and b2["length_m"] == pytest.approx(20, abs=0.5)
    assert 100 < b["sensors"][0]["fpm"] < 300 and b["speed"] == 764
    v = s.view()
    assert [x["id"] for x in v["bookmarks"]] == [1, 2] and "_axes" not in v["bookmarks"][0]
    assert v["bookmarks"][1]["label"] == "3.4 bar" and v["bookmark_m"] == sl.BOOKMARK_M
    for bad in (2, 301, "x"):
        with pytest.raises(sm.MeasureError) as e:
            s.bookmark(length_m=bad)
        assert e.value.code == "bad_length"
    s.label_bookmark(2, "neu")
    s.delete_bookmark(1)
    assert [x["label"] for x in s.view()["bookmarks"]] == ["neu"]
    with pytest.raises(sm.MeasureError) as e:
        s.find_bookmark(1)
    assert e.value.code == "no_bookmark"


def test_trial_from_bookmark_without_and_with_tdms(env, fake_db):  # noqa: F811
    s = _session()
    b = s.bookmark()
    sl.stop()
    st = live_trial.setup(466)
    assert st["default"] == 102 and [f.key for f in st["fields"]] == [f.key for f in FIELDS if f.default]
    assert "trial:Comment" not in st["source"][101]
    # without TDMS: only the copy, values validated like the copy dialog
    r = live_trial.create(466, 102, {"trial:JetID": "5", "trial:AirPressure": "3,45", "trial:Shaft2x_OF": "4.5"},
                          session=s, bookmark_id=b["id"])
    assert r["vno"] == 3 and r["file"] is None
    assert fake_db[-1] == (466, [(102, {"trial:JetID": 5, "trial:AirPressure": "3.45", "trial:Shaft2x_OF": "4.5"})])
    assert not list(env.dty.glob("*.tdms"))
    assert s.find_bookmark(b["id"])["trial"] == {"series_id": 466, "vno": 3, "trial_id": 555}
    for vals, code in (({"trial:JetID": "77"}, "invalid"), ({"trial:AirPressure": "abc"}, "invalid"),
                       ({"trial:Comment": "x"}, "bad_field"), ({"nope": 1}, "bad_field")):
        with pytest.raises(sm.MeasureError) as e:
            live_trial.create(466, 102, vals, session=s, bookmark_id=b["id"])
        assert e.value.code == code
    with pytest.raises(sm.MeasureError) as e:
        live_trial.create(466, 999, {}, session=s)
    assert e.value.code == "bad_trial"
    # with TDMS: the trial's file in the trial folder, an older one of that number moved to _replaced
    old = env.dty / "466_3_010126_0800.tdms"
    old.write_bytes(b"old")
    when = dt.datetime(2026, 11, 24, 10, 5)
    r = live_trial.create(466, 102, {"trial:SpeedShaft2": "800"}, session=s, bookmark_id=b["id"], save_tdms=True, now=when)
    assert r["file"] == "466_3_241126_1005.tdms" and r["replaced"] == old.name and r["tdms_error"] is None
    assert (env.dty / sm.REPLACED_DIR / old.name).exists() and dty_service.find_tdms(466, 3).name == r["file"]
    x, y = read_axis_channels(env.dty / r["file"])
    assert len(x) == pytest.approx(100 * s._pts_per_m(), rel=0.01) and y is not None
    assert read_step_mm_from_tdms(env.dty / r["file"]) == pytest.approx(0.25, rel=0.01)
    from nptdms import TdmsFile
    p = TdmsFile.read(env.dty / r["file"]).properties
    assert p["TrippleT.TrialID"] == 555 and p["TrippleT.Live"] == 1 and p["TrippleT.Bookmark"] == b["id"]
    with pytest.raises(sm.MeasureError) as e:          # a file needs a bookmark
        live_trial.create(466, 102, {}, session=s, save_tdms=True)
    assert e.value.code == "no_bookmark"


def test_bookmark_only_as_file(env):  # noqa: F811
    s = _session()
    b = s.bookmark(length_m=50)
    sl.stop()
    r = live_trial.save_file(s, b["id"], "99999_80", now=dt.datetime(2026, 11, 24, 9, 0))
    assert r["file"] == "99999_80_241126_0900.tdms" and (env.dty / sm.MANUAL_DIR / r["file"]).exists()
    assert dty_service.find_tdms(99999, 80) is None
    with pytest.raises(sm.MeasureError) as e:
        live_trial.save_file(s, b["id"], "a/b")
    assert e.value.code == "bad_name"


def test_validate_overrides():
    src = {"trial:AirPressure": 3.0, "trial:SpeedShaft2": tc.NOT_AVAILABLE}
    assert tc.validate_overrides(FIELDS, src, {"trial:JetID": "", "trial:AirPressure": ""}) == \
        {"trial:JetID": None, "trial:AirPressure": None}
    with pytest.raises(tc.OverrideError):
        tc.validate_overrides(FIELDS, src, {"trial:AirPressure": "3.456"})     # air: 2 decimals at most
    assert tc.validate_overrides(FIELDS, src, {"trial:AirPressure": "3.45"}) == {"trial:AirPressure": "3.45"}
    assert "trial:SpeedShaft2" not in tc.validate_overrides(FIELDS, src, {"trial:SpeedShaft2": "9"})


def test_desktop_bookmark_and_trial_dialog(env, fake_db, monkeypatch):  # noqa: F811
    import time
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit
    from ui.widgets import sensor_live_window as slw
    app = QApplication.instance() or QApplication([])
    QSettings("TrippleT", "SensorLive").clear()
    monkeypatch.setattr(live_trial, "series_info", lambda sid: {"id": 466, "name": "Fabelserie", "eid": "2026-79-1"}
                        if str(sid) == "466" else None)
    import db.trial_actions
    monkeypatch.setattr(db.trial_actions, "can_edit_trials", lambda user: True)
    sm.set_daq(StreamDaq())
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)   # no empty value checked: start anyway
    w = slw.open_window({"username": "test", "access_level": 2})
    w.sp_speed.setValue(764)
    w.sp_window.setValue(10)
    w.ck_save.setChecked(False)
    w._on_start()
    t0 = time.time()
    while time.time() - t0 < 60 and sl.current().meters() < 40:
        app.processEvents()
        time.sleep(0.05)
    w._poll()
    w.sp_mark.setValue(30)
    assert w.btn_mark.isEnabled()
    w._on_bookmark()
    sl.stop()
    w._poll()
    assert w.bm_table.rowCount() == 1 and "30 m" in w.bm_table.item(0, 3).text()
    w.bm_table.selectRow(0)
    assert w.btn_trial.isEnabled() and w.btn_file.isEnabled()
    b = w._selected_bookmark()
    dlg = slw.LiveTrialDialog(sl.current(), b, w.user, w)
    dlg.cb_series.setEditText("466")
    dlg._load()
    assert "Fabelserie" in dlg.lbl_series.text() and dlg.cb_template.currentData() == 102
    f, air = dlg._edits["trial:AirPressure"]
    assert isinstance(air, QLineEdit) and air.text() == "3.2"
    air.setText("3.6")
    jet = dlg._edits["trial:JetID"][1]
    assert isinstance(jet, QComboBox) and jet.currentText() == "P212"
    assert dlg._values() == {"trial:AirPressure": "3.6"}       # only what was changed
    dlg.ck_tdms.setChecked(True)
    dlg._create()
    assert dlg.result_info["vno"] == 3 and dlg.result_info["file"].startswith("466_3_")
    assert fake_db[-1] == (466, [(102, {"trial:AirPressure": "3.6"})])
    dlg.cb_series.setEditText("123")
    dlg._load()
    assert "No trial series" in dlg.lbl_series.text()
    w._fill_bookmarks(force=True)
    assert "466 V003" in w.bm_table.item(0, 7).text()
    w.close()


def test_desktop_trial_without_bookmark(env, fake_db, monkeypatch):  # noqa: F811
    """"Create trial... (without TDMS)" (2026-11-24): no bookmark, no live measurement, never a file."""
    from PySide6.QtWidgets import QApplication
    from ui.widgets import sensor_live_window as slw
    QApplication.instance() or QApplication([])
    monkeypatch.setattr(live_trial, "series_info", lambda sid: {"id": 466, "name": "Fabelserie", "eid": "2026-79-1"})
    dlg = slw.LiveTrialDialog(None, None, {"username": "test", "access_level": 2})
    assert dlg.ck_tdms.isHidden() and "without TDMS" in dlg.windowTitle()
    dlg.cb_series.setEditText("466")
    dlg._load()
    dlg._edits["trial:AirPressure"][1].setText("3.9")
    dlg._create()
    assert dlg.result_info["vno"] == 3 and dlg.result_info["file"] is None
    assert fake_db[-1] == (466, [(102, {"trial:AirPressure": "3.9"})]) and not list(env.dty.glob("*.tdms"))
