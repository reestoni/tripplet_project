"""live_trial.py - a new trial from a YarnScope Live bookmark (Nutzerwunsch 2026-11-24).

While tuning a jet the user only clicks "Merken" in the live dashboard (sensor_live.LiveSession.bookmark). Afterwards,
on one bookmark, "Versuch anlegen...": a template trial of the chosen series is copied the same way as "Copy trials"
(db/trial_actions.copy_trials, the same fields and value rules: db/trial_copy, only the fields shown by default -
housing, jet, jet plate, air pressure, speed, OF ...), the user's values are put in, and ONLY IF ASKED the bookmark is
written as the new trial's TDMS: <series>_<trial>_<DDMMYY_HHMM>.tdms in the DTY / ATY folder of the live session (an
older file of that trial number goes to _replaced, never deleted), a second sensor's file into _<connector> like
"Messen". The automatic analysis then takes it. "Nur als Datei" writes a bookmark to _manual without a trial.

Qt-free; used by the desktop live window (ui/widgets/sensor_live_window.py) and tripplet_web app/sensor_live_api.py.
Tests: tests/test_live_trial.py.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List, Optional

from ui.yarnscope import sensor_measure as sm


def series_info(series_id: Any) -> Optional[Dict[str, Any]]:
    """{id, name, eid} of a trial series, None if there is none (typed number in the dialog)."""
    from db.connection import fetch_all
    try:
        sid = int(series_id)
    except (TypeError, ValueError):
        return None
    rows = fetch_all("SELECT ts.ID, ts.SeriesName, e.[Experiment ID] AS eid FROM tblTrialSeries ts "
                     "LEFT JOIN tblExperimente e ON e.ID = ts.ExperimentID WHERE ts.ID = ?", [sid])
    if not rows:
        return None
    r = rows[0]
    return {"id": int(r["ID"]), "name": str(r.get("SeriesName") or ""), "eid": str(r.get("eid") or "")}


def setup(series_id: int) -> Dict[str, Any]:
    """What the dialog shows for a series: real trials (no reference samples), the default template (the highest
    trial number), the copy fields shown by default and every trial's values for them."""
    from db import trial_actions as ta
    s = ta.copy_trials_setup(int(series_id))
    fields = [f for f in s["fields"] if f.default]
    trials = s["trials"]
    default = max(trials, key=lambda t: t["vno"])["id"] if trials else None
    keys = {f.key for f in fields}
    source = {int(t): {k: v for k, v in vals.items() if k in keys} for t, vals in s["source"].items()}
    return {"trials": trials, "default": default, "fields": fields, "source": source, "next_no": s["next_no"]}


def _paths(session, label: str, folder, when: _dt.datetime, first) -> List:
    paths = [first]
    if len(session.sensors) > 1:
        sub = folder / f"_{session.sensors[1][1]}"
        sub.mkdir(exist_ok=True)
        paths.append(sm._free_path(sub, label, when))
    return paths


def create(series_id: int, template_id: int, values: Dict[str, Any], *, user: Any = None, session=None,
           bookmark_id: Any = None, save_tdms: bool = False, now: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """Copies the template trial with the typed values (db/trial_copy.validate_overrides) and, with save_tdms, writes
    the bookmark as the new trial's TDMS. Returns {trial_id, vno, file, replaced, tdms_error}.
    Raises sm.MeasureError: bad_trial, bad_field / invalid (vars field, value), no_bookmark, folder_missing,
    copy_failed. A TDMS that fails AFTER the trial was made does not undo the trial: tdms_error says why."""
    from db import trial_actions as ta, trial_copy as tc
    from db.connection import fetch_all
    s = ta.copy_trials_setup(int(series_id))
    fields = s["fields"]
    if int(template_id) not in {int(t["id"]) for t in s["trials"]}:
        raise sm.MeasureError("bad_trial", "the template is not a trial of this series")
    try:
        over = tc.validate_overrides(fields, s["source"].get(int(template_id), {}), values or {},
                                     allowed=[f.key for f in fields if f.default])
    except tc.OverrideError as e:
        raise sm.MeasureError(e.code, str(e), field=e.field.label if e.field else "", value=str(e.value))
    b = None
    if session is not None and bookmark_id not in (None, ""):
        b = session.find_bookmark(bookmark_id)
    if save_tdms:
        if b is None:
            raise sm.MeasureError("no_bookmark", "no bookmark to save", id=str(bookmark_id))
        folder = sm.tdms_folder(session.kind)
        if not folder.is_dir():
            raise sm.MeasureError("folder_missing", f"{folder} not reachable", folder=str(folder))
    new_ids, err = ta.copy_trials(int(series_id), [(int(template_id), over)], fields, user)
    if err is not None or not new_ids:
        raise sm.MeasureError("copy_failed", str(err or "no trial made")[:300], detail=str(err or "")[:300])
    tid = int(new_ids[0])
    rows = fetch_all("SELECT Versuchsnummer FROM tblTrial WHERE ID = ?", [tid])
    vno = int(rows[0]["Versuchsnummer"]) if rows else None
    res: Dict[str, Any] = {"trial_id": tid, "vno": vno, "series_id": int(series_id), "file": None, "replaced": None,
                           "tdms_error": None}
    if b is not None:
        b["trial"] = {"series_id": int(series_id), "vno": vno, "trial_id": tid}
    if save_tdms and vno is not None:
        try:
            folder = sm.tdms_folder(session.kind)
            moved = sm.move_replaced(sm.existing_file(int(series_id), vno, session.kind))
            when = now or _dt.datetime.now()
            label = f"{int(series_id)}_{vno}"
            first = folder / sm.file_name(int(series_id), vno, when)
            paths = _paths(session, label, folder, when, first)
            session.bookmark_tdms(b, paths, label, TrialID=tid, SeriesID=int(series_id))
            res.update(file=first.name, replaced=moved.name if moved else None)
            b["file"] = first.name
        except Exception as e:  # noqa: BLE001 - the trial stays; the user sees why the file is missing
            res["tdms_error"] = str(e)[:300]
    return res


def save_file(session, bookmark_id: Any, name: Any, now: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """"Nur als Datei": the bookmark to <DTY|ATY>/_manual/<name>[_C1|_C2]_<DDMMYY_HHMM>.tdms, no trial (like the free
    measurement of the TDMS Inspector)."""
    b = session.find_bookmark(bookmark_id)
    nm = sm.check_name(name)
    folder = sm.tdms_folder(session.kind)
    if not folder.is_dir():
        raise sm.MeasureError("folder_missing", f"{folder} not reachable", folder=str(folder))
    sub = folder / sm.MANUAL_DIR
    sub.mkdir(exist_ok=True)
    when = now or _dt.datetime.now()
    if len(session.sensors) == 1:
        paths = [sm._free_path(sub, nm, when)]
        labels = [nm]
    else:
        labels = [f"{nm}_{c}" for _h, c in session.sensors]
        paths = [sm._free_path(sub, lb, when) for lb in labels]
    session.bookmark_tdms(b, paths, labels, Manual=1)
    b["file"] = paths[0].name
    return {"file": paths[0].name, "files": [p.name for p in paths], "path": str(paths[0])}

