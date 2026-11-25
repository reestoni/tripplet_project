"""live_log.py - what was changed during a YarnScope Live run (Nutzerwunsch 2026-11-25: "wie eine kleine Doku").

The user picks the machine; its Machine Data fields (the fixed ones Housing / Jet / Jet plate / Air pressure plus its
tblMachineFields rows, dropdowns with their lookup lists) and freely named fields can be entered at any time of the run:
"Air pressure 3.0 -> 3.4 bar", with a note. Every entry gets the time and the metre position of the run; the dashboard
draws a marker there and lists the entries. Entering a change does NOT pause the recording (user's choice: pause and
resume are their own buttons, sensor_live.LiveSession.pause/resume).

Values are checked like Machine Data / "Copy trials" (dropdown = one of its ids, else db/trial_copy.normalize_value with
the field's rule). The log is plain data (to_json/from_json) - the live session keeps it, writes it into the side file of
a saved run (sensor_live SIDE_SUFFIX) and load_saved shows it again. Qt-free: desktop live window and web API.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List, Optional

from ui.yarnscope import sensor_measure as sm

MAX_ENTRIES = 500
_SKIP_ORIG = {"housingid", "jetid", "jetplate", "jet_plate", "airpressure", "air_pressure", "versuchsnummer"}


def machines() -> List[Dict[str, Any]]:
    """[{id, name}] of all machines (tblMaschine)."""
    from db.series_actions import list_machines
    out = []
    for r in list_machines():
        try:
            out.append({"id": int(r.get("ID")), "name": str(r.get("Maschine") or "")})
        except (TypeError, ValueError):
            continue
    return out


def field_catalog(machine_id: Any) -> List[Dict[str, Any]]:
    """The fields that can be logged for a machine, like its Machine Data: {key, label, rd, rule, choices [[id, name]]}."""
    from db import machine_data as md
    fields: List[Dict[str, Any]] = []

    def _choices(pairs) -> List[List[Any]]:
        seen, out = set(), []
        for k, v in pairs:
            try:
                k = int(k)
            except (TypeError, ValueError):
                continue
            if k not in seen:
                seen.add(k)
                out.append([k, str(v or "")])
        return out
    try:
        fields.append({"key": "housing", "label": "Housing", "rd": False, "rule": None,
                       "choices": _choices(md.load_housing_lookup().list or [])})
        fields.append({"key": "jet", "label": "Jet", "rd": False, "rule": None,
                       "choices": _choices(md.load_jets_lookup().list or [])})
    except Exception:  # noqa: BLE001 - no lookups (no DB): the plain fields still work
        pass
    fields.append({"key": "jet_plate", "label": "Jet Plate Number", "rd": False, "rule": "onlyDoubles", "choices": None})
    fields.append({"key": "air", "label": "Air Pressure (bar)", "rd": False, "rule": "air", "choices": None})
    seen = {f["key"] for f in fields}
    for row in md.machine_fields(machine_id):
        orig = str(row.get("OriginalName") or "").strip()
        name = str(row.get("FieldName") or orig).strip()
        if not name or orig.lower() in _SKIP_ORIG:
            continue
        key = "mf:" + (orig or name)
        if key in seen:
            continue
        seen.add(key)
        ff = str(row.get("FieldFunction") or "").strip()
        choices, rule = None, None
        if ff.lower().startswith("dropdown:"):
            choices = _choices(md.lookup_map(ff[9:].strip()).items())
        else:
            rule = ff or None
        fields.append({"key": key, "label": name, "rd": int(row.get("RDSetting") or 0) == 1, "rule": rule,
                       "choices": choices})
    return fields


class LiveLog:
    """Machine + change entries of one run."""

    def __init__(self) -> None:
        self.machine: Optional[Dict[str, Any]] = None
        self.changes: List[Dict[str, Any]] = []
        self._fields: Dict[str, Dict[str, Any]] = {}
        self._seq = 0

    # ---------------------------------------------------------------------------------------------- machine
    def set_machine(self, machine_id: Any) -> Dict[str, Any]:
        if machine_id in (None, "", 0):
            self.machine, self._fields = None, {}
            return {"machine": None, "fields": []}
        try:
            mid = int(machine_id)
        except (TypeError, ValueError):
            raise sm.MeasureError("bad_machine", f"machine {machine_id!r}", machine=str(machine_id))
        m = next((x for x in machines() if x["id"] == mid), None)
        if m is None:
            raise sm.MeasureError("bad_machine", f"machine {machine_id!r}", machine=str(machine_id))
        cat = field_catalog(mid)
        self.machine, self._fields = m, {f["key"]: f for f in cat}
        return {"machine": m, "fields": cat}

    def fields(self) -> List[Dict[str, Any]]:
        return list(self._fields.values())

    # ---------------------------------------------------------------------------------------------- entries
    def settings(self) -> Dict[str, Dict[str, Any]]:
        """Current value per field after all entries: {key: {label, text}}."""
        cur: Dict[str, Dict[str, Any]] = {}
        for c in self.changes:
            for it in c["items"]:
                cur[it["key"]] = {"label": it["label"], "text": it["new"]}
        return cur

    def _check(self, key: str, value: Any) -> Dict[str, Any]:
        from db import trial_copy as tc
        f = self._fields.get(key)
        if f is None:
            raise sm.MeasureError("bad_field", f"field {key!r}", field=str(key), value=str(value))
        if f.get("choices"):
            if value in (None, ""):
                return {"key": key, "label": f["label"], "new": "", "value": None}
            hit = next((c for c in f["choices"] if str(c[0]) == str(value)), None)
            if hit is None:
                raise sm.MeasureError("invalid", f"{value!r} for {f['label']}", field=f["label"], value=str(value))
            return {"key": key, "label": f["label"], "new": hit[1], "value": hit[0]}
        norm = tc.normalize_value(f.get("rule"), value)
        if norm is None:
            raise sm.MeasureError("invalid", f"{value!r} for {f['label']}", field=f["label"], value=str(value))
        return {"key": key, "label": f["label"], "new": norm, "value": norm}

    def add(self, items: Optional[List[Dict[str, Any]]] = None, free: Optional[List[Dict[str, Any]]] = None,
            note: Any = "", at_m: Optional[float] = None, at: Optional[str] = None) -> Dict[str, Any]:
        """One entry: [{key, value}] of machine fields, [{name, value}] of free fields, a note. Old values come from
        the entries before. Raises MeasureError: empty_change, bad_field, invalid, bad_free, too_many_changes."""
        if len(self.changes) >= MAX_ENTRIES:
            raise sm.MeasureError("too_many_changes", "too many entries", n=MAX_ENTRIES)
        cur = self.settings()
        out: List[Dict[str, Any]] = []
        for it in items or []:
            chk = self._check(str(it.get("key") or ""), it.get("value"))
            if not any(o["key"] == chk["key"] for o in out):
                out.append(chk)
        for it in free or []:
            name = str(it.get("name") or "").strip()
            val = str(it.get("value") or "").strip()
            if not name and not val:
                continue
            if not name or len(name) > 40 or len(val) > 60:
                raise sm.MeasureError("bad_free", f"free field {name!r}", name=name)
            key = "free:" + name
            if not any(o["key"] == key for o in out):
                out.append({"key": key, "label": name, "new": val, "value": val})
        note = str(note or "").strip()[:300]
        if not out and not note:
            raise sm.MeasureError("empty_change", "nothing entered")
        for o in out:
            o["old"] = (cur.get(o["key"]) or {}).get("text")
            o.pop("value", None)
        self._seq = max([self._seq] + [int(c.get("id") or 0) for c in self.changes]) + 1
        entry = {"id": self._seq, "at": at or _dt.datetime.now().isoformat(timespec="seconds"),
                 "at_m": round(float(at_m or 0.0), 1), "items": out, "note": note}
        self.changes.append(entry)
        return entry

    def delete(self, cid: Any) -> None:
        """Removes one entry; the old values of the later ones are recomputed."""
        before = len(self.changes)
        self.changes = [c for c in self.changes if str(c["id"]) != str(cid)]
        if len(self.changes) == before:
            raise sm.MeasureError("no_change", f"entry {cid!r}", id=str(cid))
        cur: Dict[str, str] = {}
        for c in self.changes:
            for it in c["items"]:
                it["old"] = cur.get(it["key"])
                cur[it["key"]] = it["new"]

    # ---------------------------------------------------------------------------------------------- storage
    def to_json(self) -> Dict[str, Any]:
        return {"machine": self.machine, "changes": self.changes}

    @classmethod
    def from_json(cls, d: Optional[Dict[str, Any]]) -> "LiveLog":
        log = cls()
        d = d or {}
        log.machine = d.get("machine")
        log.changes = list(d.get("changes") or [])
        log._seq = max([0] + [int(c.get("id") or 0) for c in log.changes])
        return log


def summary(entry: Dict[str, Any]) -> str:
    """"Air Pressure (bar) 3.0 -> 3.4 · Jet LB-04" (+ note) - for markers and lists."""
    parts = [f"{it['label']} {it['old']} → {it['new']}" if it.get("old") not in (None, "") else f"{it['label']} {it['new']}"
             for it in entry.get("items") or []]
    if entry.get("note"):
        parts.append(str(entry["note"]))
    return " · ".join(parts)
