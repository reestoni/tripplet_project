"""Automatic TDMS measurement when the jet tension is saved (ui/yarnscope/auto_measure.py, Nutzerwunsch 2026-11-24).

No database: DTYoMat check and trial list are replaced; the box is the fake of test_sensor_measure. Checks: which
edits count (tension before / after the jet only), the decision (one trial, DTYoMat, ask only if a TDMS exists), the
switch in the measure window, the window measuring the given trial, Show Experiment's step after the save."""
from types import SimpleNamespace

import pytest

from test_sensor_measure import _run_job, env  # noqa: F401
from db.series_save import jet_tension_trial_ids
from ui.yarnscope import auto_measure
from ui.yarnscope import sensor_measure as sm


def _b(field, tid, table="tblTrial"):
    return SimpleNamespace(table=table, field=field, id_value=tid)


def test_tension_trial_ids():
    edits = [(_b("YarnTensionBeforeJet", 11), "12"), (_b("YarnTensionAfterJet", 11), "30"),
             (_b("AirPressure", 12), "3"), (_b("W3Tension", 13), "9"), (_b("YarnTensionAfterJet", 14, "tblLaborX"), "1"),
             (None, "x"), (SimpleNamespace(table="tblTrial", field="Yarn_Tension_After_Jet", id_values=[15, 16]), "2")]
    assert jet_tension_trial_ids(edits) == [11, 15, 16]
    assert auto_measure.tension_trial_ids is jet_tension_trial_ids


TRIALS = [{"trial_id": 11, "vno": 1, "speed": 764.0, "dty": "466_1_241126_0900.tdms", "aty": None},
          {"trial_id": 12, "vno": 2, "speed": 764.0, "dty": None, "aty": None}]


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setattr(auto_measure, "has_dtyomat", lambda tid: tid != 99)
    monkeypatch.setattr(sm, "trials_for", lambda sid: [dict(t) for t in TRIALS])


def test_decide(fake):
    assert auto_measure.decide(466, [])["action"] == "none"
    assert auto_measure.decide(466, [11, 12]) == {"action": "skip", "reason": "several", "n": 2}
    assert auto_measure.decide(466, [99])["reason"] == "no_dtyomat"
    assert auto_measure.decide(466, [55])["reason"] == "no_trial"
    d = auto_measure.decide(466, [12])
    assert d["action"] == "measure" and d["vno"] == 2 and d["speed"] == 764.0
    d = auto_measure.decide(466, ["11", 11])
    assert d["action"] == "ask" and d["file"] == TRIALS[0]["dty"]
    assert auto_measure.decide(466, [11], "aty")["action"] == "measure"


def test_window_switch_and_auto_measure(env, qapp, fake, monkeypatch):  # noqa: F811
    from PySide6.QtCore import QSettings
    from ui.widgets import sensor_measure_dialog as smd
    QSettings("TrippleT", "SensorMeasure").clear()
    seen, done, analysed = [], [], []
    monkeypatch.setattr(auto_measure, "analyse_and_save", lambda path, trial_id, kind="dty", user=None:
                        analysed.append((trial_id, kind)) or {"saved": True, "fpm": 151.0, "error": None})
    dlg = smd.SensorMeasureDialog(466, {"username": "test", "access_level": 2}, on_auto=seen.append, on_auto_done=done.append)
    dlg.show()
    assert not smd.auto_enabled() and not dlg.ck_auto.isChecked()
    dlg.ck_auto.setChecked(True)
    assert smd.auto_enabled() and seen == [True]
    dlg.sp_length.setValue(3)
    dlg._zero = {"axes": []}                       # empty value checked
    assert dlg.auto_measure(12)
    _run_job(dlg, qapp)                            # the measurement
    _run_job(dlg, qapp)                            # then analysed + saved (2026-11-24)
    qapp.processEvents()
    assert [p.name.split("_")[1] for p in env.dty.glob("466_*.tdms")] == ["2"]
    assert analysed == [(12, "dty")] and done[0]["saved"] and done[0]["vno"] == 2 and done[0]["file"].startswith("466_2_")
    assert not dlg.isVisible()                     # the window closed itself for the next tension
    dlg.show()
    assert not dlg.auto_measure(555)               # not a trial of the list
    dlg.ck_auto.setChecked(False)
    assert not smd.auto_enabled() and seen == [True, False]
    dlg.close()
    free = smd.SensorMeasureDialog(None, {"username": "test", "access_level": 2}, free=True)
    assert not free.ck_auto.isVisibleTo(free)
    free.close()


def test_show_experiment_step_after_save(qapp, fake, monkeypatch):
    """ShowExperimentScreen._auto_measure_after_save on a stand-in: switch off = nothing; no TDMS = measure at once;
    TDMS = only after "Yes" and then with replace."""
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QMessageBox
    from ui.screen_show_experiment import ShowExperimentScreen
    QSettings("TrippleT", "SensorMeasure").clear()
    calls = []
    dlg = SimpleNamespace(auto_measure=lambda tid, replace=False: calls.append((tid, replace)))
    stub = SimpleNamespace(_series_pk=466, _open_sensor_measure=lambda: dlg)
    run = lambda ids: ShowExperimentScreen._auto_measure_after_save(stub, ids)  # noqa: E731
    run([12])
    assert calls == []                              # switch off
    QSettings("TrippleT", "SensorMeasure").setValue("auto_tension", True)
    run([12])
    assert calls == [(12, False)]
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.No)
    run([11])
    assert calls == [(12, False)]                   # TDMS exists, "No"
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    run([11])
    assert calls[-1] == (11, True)
    run([99])                                       # no DTYoMat: silently nothing
    assert len(calls) == 2
    QSettings("TrippleT", "SensorMeasure").clear()
