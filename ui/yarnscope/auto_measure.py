"""auto_measure.py - measure a trial automatically when its jet tension is saved (Nutzerwunsch 2026-11-24).

The user's routine in Show Experiment: measure the tension before / after the jet, type it into Machine Data, save,
then the TDMS measurement, take the spool off, set the machine for the next trial. With the switch "measure
automatically" on (measure window, both apps, off by default), saving the tension starts the measurement of THAT
trial straight away:
  - only for a trial that has the lab machine DTYoMat (a tblLaborDTYoMat row),
  - only if exactly one trial's jet tension was saved (one spool on the machine),
  - no TDMS yet -> measure without asking; a TDMS exists -> ask first ("measure again?", the old file goes to
    _replaced like "Measure again").
Saving is never blocked: the measurement is a step after it. The empty value must have been checked before the first
trial (sensor_measure.remembered_zero) - otherwise the measure window asks as usual.

Qt-free: decide() is used by the desktop (ShowExperimentScreen._save_all) and the web (the save answer carries
"tension_trials", the page asks /api/series/{id}/sensor/auto). Tests: tests/test_auto_measure.py.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable

from ui.yarnscope import sensor_measure as sm

from db.series_save import JET_TENSION_FIELDS as TENSION_FIELDS  # noqa: E402,F401
from db.series_save import jet_tension_trial_ids as tension_trial_ids  # noqa: E402,F401


def has_dtyomat(trial_id: int) -> bool:
    from db.connection import fetch_all, table_exists
    if not table_exists("tblLaborDTYoMat"):
        return False
    return bool(fetch_all("SELECT ID FROM tblLaborDTYoMat WHERE TrialID = ? LIMIT 1", [int(trial_id)]))


def decide(series_id: int, trial_ids: Iterable[Any], kind: str = "dty") -> Dict[str, Any]:
    """What to do after a save: {"action": "none" | "skip" | "measure" | "ask", "reason", "trial_id", "vno",
    "speed", "file"}. skip reasons: several (more than one trial), no_dtyomat, no_trial (reference sample / gone)."""
    ids = []
    for i in trial_ids or ():
        try:
            if int(i) not in ids:
                ids.append(int(i))
        except (TypeError, ValueError):
            pass
    if not ids:
        return {"action": "none"}
    if len(ids) > 1:
        return {"action": "skip", "reason": "several", "n": len(ids)}
    tid = ids[0]
    if not has_dtyomat(tid):
        return {"action": "skip", "reason": "no_dtyomat", "trial_id": tid}
    t = next((x for x in sm.trials_for(int(series_id)) if x["trial_id"] == tid), None)
    if t is None:
        return {"action": "skip", "reason": "no_trial", "trial_id": tid}
    k = kind if kind in sm.KINDS else "dty"
    return {"action": "ask" if t.get(k) else "measure", "trial_id": tid, "vno": t["vno"], "speed": t.get("speed"),
            "file": t.get(k), "kind": k}
