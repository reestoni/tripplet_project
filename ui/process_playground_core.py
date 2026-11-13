"""process_playground_core.py - Process Playground (ui/screen_process_playground.py) without Qt: everything the
screen builds on top of ui/dty_whatif.py (2026-11-13, for the web version; the desktop screen uses it).

Combination list, start points ("take from a trial"), slider ranges, the new settings from the sliders, the
statement texts per lab value, the warnings (codes), the suggestions of "Find settings" and the chart data -
as plain values, so the desktop table and the web page show the same."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ui import dty_whatif as w

PARAM_SHORT = {"pressure": "P", "of": "OF", "speed": "S"}
STRENGTH = {w.CLEAR: "strong (p < 0.01)", w.PROBABLE: "good (p < 0.05)", w.TENDENCY: "weak (p < 0.10)",
            w.SAME: "change smaller than the repeat scatter", w.NO_CLEAR: "neither clearly changed nor clearly equal"}
GREY_VERDICTS = (w.UNCLEAR, w.NOT_VARIED, w.NO_DATA, w.OUTSIDE)
# warnings (codes; the screens word them)
WARN_START_OUTSIDE, WARN_START_NEVER, WARN_NEW_NEVER, WARN_MOVE = "start_outside", "start_never", "new_never", "move"


def fmt(v: Optional[float], dec: int) -> str:
    return "" if v is None else f"{v:.{dec}f}"


def combo_key(c: w.Combination) -> str:
    """The combination key as text (yarn key | jet id) - for lists and the web."""
    return f"{c.key[0]}|{c.key[1]}"


def find_combo(ds: w.DataSet, key: str) -> Optional[w.Combination]:
    return next((c for c in ds.combos.values() if combo_key(c) == key), None)


def combos_list(ds: w.DataSet) -> List[Dict[str, Any]]:
    """Yarn / jet combinations, most lab settings first (desktop list order)."""
    combos = sorted(ds.combos.values(), key=lambda c: (-c.n_lab_settings, -c.n_settings, c.yarn_name))
    return [{"key": combo_key(c), "yarn": c.yarn_name, "jet": c.jet_name, "trials": c.n_trials, "series": c.n_series,
             "settings": c.n_settings, "varied": " ".join(PARAM_SHORT[p] for p in c.varied)} for c in combos]


def settings_options(c: w.Combination) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    """"Take from a trial": the measured settings with their label, and the best start (most trials, all set)."""
    out, best, best_n = [], None, -1
    for i, s in enumerate(w.settings_of(c.rows)):
        parts = [("OF " if p == "of" else "") + f"{fmt(s[p], w.PARAMS[p][4]) or '-'} {w.PARAMS[p][2]}" for p in w.PARAMS]
        nos = ", ".join(f"V{n}" for n in sorted(x for x in s["trials"] if x is not None))
        n_tr = len(s["trials"])
        out.append({"label": " · ".join(parts) + f"  ({n_tr} trial{'s' if n_tr != 1 else ''})  -  {s['series_name']}",
                    "tooltip": f"{s['series_name']}\nTrials {nos}", "start": {p: s[p] for p in w.PARAMS}})
        if n_tr > best_n and all(s[p] is not None for p in w.PARAMS):
            best, best_n = i, n_tr
    return out, best


def slider_ranges(c: w.Combination) -> Dict[str, Dict[str, Any]]:
    """Per parameter: measured range, slider step, decimals and whether it can be moved at all."""
    out = {}
    for p, (label, _step, unit, sstep, dec) in w.PARAMS.items():
        vals = [r[p] for r in c.rows if r.get(p) is not None]
        lo, hi = (min(vals), max(vals)) if vals else (0.0, 0.0)
        out[p] = {"label": label, "unit": unit, "step": sstep, "dec": dec, "lo": lo, "hi": hi, "varied": p in c.varied}
    return out


def new_settings(c: w.Combination, start: Dict[str, float], moved: Dict[str, float]) -> Dict[str, float]:
    """Slider values -> new settings: only varied parameters move (inside the measured range); a parameter whose
    slider is still at the (clamped) start keeps the typed start value (desktop _new)."""
    ranges = slider_ranges(c)
    new = dict(start)
    for p, v in (moved or {}).items():
        r = ranges.get(p)
        if r is None or not r["varied"] or v is None:
            continue
        v = round(min(max(float(v), r["lo"]), r["hi"]), 6)
        clamped = min(max(start[p], r["lo"]), r["hi"])
        if abs(v - clamped) > 1e-9:
            new[p] = v
    return new


def based_on(ch: w.Change) -> str:
    based = []
    if ch.verdict in (w.CLEAR, w.PROBABLE, w.TENDENCY, w.SAME, w.NO_CLEAR):
        for p, (agree, n) in ch.series.items():
            if n:
                based.append(f"{w.PARAMS[p][0]}: {agree} of {n} series same direction"
                             if ch.verdict in w.SIGNIFICANT else f"{w.PARAMS[p][0]}: {n} series")
        if ch.one_series:
            based.append("only 1 series - check it")
        if ch.curved:
            based.append("not linear - depends on the start")
    elif ch.reason:
        based.append(ch.reason)
    return ";  ".join(based)


def statement(ch: w.Change) -> str:
    if ch.verdict == w.NO_CHANGE:
        return ""
    arrow = {1: "↑ ", -1: "↓ "}.get(ch.direction, "≈ " if ch.verdict == w.SAME else "")
    return arrow + w.verdict_text(ch)


def change_text(ch: w.Change, dec: int) -> str:
    if ch.delta is None or ch.ci is None or ch.verdict in (w.OUTSIDE, w.NOT_VARIED):
        return ""
    lo, hi = ch.ci
    return f"{ch.delta:+.{dec}f}  ({lo:+.{dec}f} to {hi:+.{dec}f})"


def change_json(target: str, ch: w.Change) -> Dict[str, Any]:
    label, unit, dec = w.TARGETS[target]
    return {"target": target, "label": label, "unit": unit, "verdict": ch.verdict, "direction": ch.direction,
            "start": f"{fmt(ch.start_value, dec)} {unit}" if ch.start_value is not None else "",
            "change": change_text(ch, dec), "statement": statement(ch), "based_on": based_on(ch),
            "strength": STRENGTH.get(ch.verdict, ch.reason or ""), "grey": ch.verdict in GREY_VERDICTS,
            "bold": ch.verdict in w.SIGNIFICANT, "delta": ch.delta}


def start_check(c: w.Combination, start: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
    """Notes under the start fields (ok + text)."""
    return {p: {"ok": ok, "text": txt} for p, (ok, txt) in w.start_notes(c.rows, start).items()}


def evaluate(ds: w.DataSet, c: w.Combination, start: Dict[str, float], new: Dict[str, float],
             fits: Optional[dict] = None) -> Dict[str, Any]:
    """What happens to every lab value from start to new + the warnings (codes)."""
    changed = [p for p in w.PARAMS if abs(new[p] - start[p]) > 1e-9]
    changes = {t: w.change(c.rows, t, ds.margins[t], start, new, fits) for t in w.TARGETS}
    warn = []
    if any(not ok for ok, _t in w.start_notes(c.rows, start).values()):
        warn.append(WARN_START_OUTSIDE)
    elif w.never_run(c.rows, start):
        warn.append(WARN_START_NEVER)
    if changed and w.never_run(c.rows, new):
        warn.append(WARN_NEW_NEVER)
    if not changed and not warn:
        warn.append(WARN_MOVE)
    return {"changed": changed, "warnings": warn, "changes": changes,
            "rows": [change_json(t, changes[t]) for t in w.TARGETS]}


def suggestions_json(sugg: List[w.Suggestion], start: Dict[str, float], goals: Dict[str, str], main: str) -> Dict[str, Any]:
    """The suggestion table: changed settings (bold = changed) and per goal the statement + status."""
    targets = [main] + [t for t in w.TARGETS if t in goals and t != main]
    rows = []
    for sg in sugg:
        params = []
        for p in w.PARAMS:
            dec = w.PARAMS[p][4]
            d = sg.new[p] - start[p]
            params.append({"value": f"{sg.new[p]:.{dec}f}", "delta": f"{d:+.{dec}f}" if abs(d) > 1e-9 else ""})
        cells = []
        for t in targets:
            ch = sg.changes[t]
            txt = statement(ch) or "-"
            if ch.delta is not None and ch.verdict in w.SIGNIFICANT + (w.SAME, w.NO_CLEAR):
                txt += f" ({ch.delta:+.{w.TARGETS[t][2]}f})"
            cells.append({"target": t, "text": txt, "status": "" if t == main else sg.status.get(t, ""),
                          "verdict": ch.verdict, "tooltip": (change_text(ch, w.TARGETS[t][2]) + "\n" + based_on(ch)).strip()})
        rows.append({"new": sg.new, "params": params, "cells": cells})
    return {"targets": targets, "rows": rows}


def chart_json(ds: w.DataSet, c: w.Combination, fits: dict, target: str, param: str,
               start: Dict[str, float], new: Dict[str, float]) -> Optional[Dict[str, Any]]:
    """Points (corrected) + model curve with 95 % band for one lab value against one setting."""
    if target not in fits:
        w.change(c.rows, target, ds.margins[target], start, start, fits)
    fit, conds, _usable = fits[target]
    data = w.chart_data(fit, conds, param, start)
    if not data:
        return None
    out = {"x": data["x"], "y": data["y"], "series": [str(s) for s in data["series"]], "curve": None,
           "start": start.get(param), "new": new.get(param) if abs((new.get(param) or 0) - (start.get(param) or 0)) > 1e-9 else None}
    if data["curve"]:
        gx, gy, lo, hi = data["curve"]
        out["curve"] = {"x": [float(v) for v in gx], "y": [float(v) for v in gy], "lo": [float(v) for v in lo], "hi": [float(v) for v in hi]}
    return out


def trial_start(ds: w.DataSet, trial_id) -> Optional[Tuple[str, Dict[str, Optional[float]]]]:
    """"Open in Process Playground" from Show Experiment: the combination and the settings of a trial."""
    row = next((r for r in ds.rows if r.get("trial_id") == trial_id), None)
    key = (row.get("yarn_key"), row.get("jet_id")) if row else None
    if row is None or key not in ds.combos:
        return None
    return combo_key(ds.combos[key]), {p: row.get(p) for p in w.PARAMS}


DTY_MACHINE_TYPES = ("DTY", "DT/DW")      # same as the trial query in ui/dty_whatif.py


def series_is_dty(series_id: int) -> bool:
    """Whether a series runs on a DTY machine ("Open in Process Playground" only there; the desktop asks the
    Machine Data schema, the web this - same machines)."""
    try:
        from db.connection import fetch_all
        rows = fetch_all("SELECT mt.Maschinentyp FROM tbltrialseries ts JOIN tblmaschine m ON m.ID = ts.MachineID "
                         "JOIN tblmaschinentypen mt ON mt.ID = m.Maschinentyp WHERE ts.ID = ?", [series_id])
    except Exception:
        return False
    return bool(rows) and str(list(rows[0].values())[0] if isinstance(rows[0], dict) else rows[0][0]) in DTY_MACHINE_TYPES
