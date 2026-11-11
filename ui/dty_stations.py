"""dty_stations.py - stations of the DTY machine path and which Machine
Data rows belong to them (for the process schema in Show Experiment,
ui/dty_schema_panel.py). Pure logic, no Qt - tested in
tests/test_dty_schema.py.

Row keys: Machine Data rows are identified by a key - the fixed rows by a
short name ("housing", "jet", ...), the rows from tblMachineFields by their
DB column in lower case (OriginalName), the computed D/Y ratio by "dyratio".
ui/machine_tab.py stores them in screen._machine_row_keys.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Set

# (key, label, per_ply) in machine order. per_ply = the station exists on
# every position (= ply) before the plies are merged.
STATIONS: List[tuple] = [
    ("creel", "Creel / Position", True),
    ("lw0", "LW 0", True),
    ("prejet", "Pre-intermingling jet", True),
    ("lw1", "LW 1", True),
    ("heater1", "Primary heater", True),
    ("cooling", "Cooling plate", True),
    ("friction", "Friction unit", True),
    ("lw2", "LW 2", False),
    ("mainjet", "Main jet", False),
    ("lw2x", "LW 2.x (OF)", False),
    ("setheater", "Set heater", False),
    ("jet3", "Jet 3 (before LW 3)", False),
    ("lw3", "LW 3", False),
    ("winder", "Winder", False),
    ("elastane", "Elastane feed", True),
    ("process", "DTY process", False),
]
STATION_LABEL = {k: lbl for k, lbl, _ in STATIONS}
PER_PLY = {k for k, _, pp in STATIONS if pp}

# row key -> station. Keys not listed belong to no station (comments,
# custom group, ...).
FIELD_STATION: Dict[str, str] = {
    # creel / position
    "position": "creel", "yarnuse": "creel", "spool": "creel", "plies": "creel",
    "pretension": "creel", "acfeederid": "creel",
    "dtyrouteid": "creel", "mergeintoply": "creel", "mergepointid": "creel",
    # LW 0 + pre-intermingling (between LW 0 and LW 1)
    "w0_w1_of": "lw0",
    "preinterminglinghousing": "prejet", "preinterminglingjets": "prejet",
    "preinterminglingairpressure": "prejet",
    # LW 1 (draw ratio LW 1 -> LW 2)
    "shaft1_dr": "lw1", "dr": "lw1",
    # primary heater
    "1stheatert1": "heater1", "1stheatert2": "heater1", "1stheaterlength": "heater1",
    "temp1": "heater1", "temp0": "heater1",
    # friction
    "twistdirection": "friction", "discconfiguration": "friction",
    "discconfigurationid": "friction", "discid": "friction", "disctype": "friction",
    "discdiameter": "friction", "discthickness": "friction", "dyvalue": "friction",
    "yarntensiont1": "friction", "yarntensiont2": "friction", "dyratio": "friction",
    # LW 2
    "speedshaft2": "lw2", "shaft2speed": "lw2", "w2": "lw2", "w2tension": "lw2",
    # main jet (between LW 2 and LW 2.x)
    "housing": "mainjet", "housingid": "mainjet", "jet": "mainjet", "jetid": "mainjet",
    "jetplate": "mainjet", "airpressure": "mainjet", "topplateid": "mainjet",
    "yarntensionbeforejet": "mainjet", "yarntensionafterjet": "mainjet",
    "anglejetentry": "mainjet", "anglejetexit": "mainjet",
    "wettingheadid": "mainjet", "waterpressure": "mainjet",
    "yarnguidebeforejet": "mainjet", "yarnguideafterjet": "mainjet",
    # LW 2.x (overfeed)
    "shaft2x_of": "lw2x", "of": "lw2x",
    # set heater
    "2ndheaterset": "setheater", "2ndheaterlength": "setheater",
    "setheatertemperature": "setheater", "lengthsetheater": "setheater",
    # third jet (after set heater, before LW 3)
    "w3_housing": "jet3", "w3_jet": "jet3", "w3_airpressure": "jet3",
    # LW 3
    "shaft3": "lw3", "w3": "lw3", "w3tension": "lw3",
    # winder
    "winder": "winder", "winding": "winder", "crossingangle": "winder",
    "traverse": "winder", "amplitude": "winder", "counterwobble": "winder",
    # elastane feed
    "draftelastane": "elastane", "overfeedfeeder": "elastane",
    # process
    "dtyprocessid": "process",
}

PREJET_KEYS = {"w0_w1_of", "preinterminglinghousing", "preinterminglingjets",
               "preinterminglingairpressure"}
JET3_KEYS = {"w3_housing", "w3_jet", "w3_airpressure"}
MERGE_KEYS = {"dtyrouteid", "mergeintoply", "mergepointid"}


def station_of(row_key: Optional[str]) -> Optional[str]:
    return FIELD_STATION.get(str(row_key or "").lower())


def rows_of_station(row_keys: List[Optional[str]], station: str) -> List[int]:
    """Data rows (0-based) of Machine Data that belong to `station`."""
    return [i for i, k in enumerate(row_keys) if station_of(k) == station]


def _filled(v: Any) -> bool:
    return v not in (None, "", 0, "0", "0.0") and str(v).strip() not in ("", "—")


def process_hidden_rows(row_keys: List[Optional[str]], n_cols: int,
                        value_at: Callable[[int, int], Any],
                        process_row: Optional[int],
                        flags: Dict[int, Dict[str, bool]],
                        multi_ply: bool = False) -> Set[int]:
    """Rows of the pre-intermingling jet, of jet 3 and the merge rows (Route
    / Merge into ply / Merge point) that no trial of the series needs:
    hidden unless a trial's process uses them (merge rows: a trial has at
    least 2 plies) or a value is entered (values are never hidden away)."""
    used_pre = used_jet3 = False
    if process_row is not None:
        for c in range(n_cols):
            try:
                pid = int(value_at(process_row, c) or 0)
            except Exception:
                pid = 0
            f = flags.get(pid) or {}
            used_pre = used_pre or bool(f.get("pre"))
            used_jet3 = used_jet3 or bool(f.get("jet3"))
    hidden: Set[int] = set()
    for group, used in ((PREJET_KEYS, used_pre), (JET3_KEYS, used_jet3), (MERGE_KEYS, multi_ply)):
        rows = [i for i, k in enumerate(row_keys) if str(k or "").lower() in group]
        if used or any(_filled(value_at(r, c)) for r in rows for c in range(n_cols)):
            continue
        hidden.update(rows)
    return hidden


# ── path of one trial for the drawing ──────────────────────────────────
DRAWN_YARN_TYPES = {2, 3, 8}     # tblgarntyp FDY, HOY, FOY - already drawn
BEFORE_HEATER_PROCESS_ID = 5     # "Cotton-like: before heater" (db.dty_process.SEED)


ELASTANE_YARN_USE_ID = 3         # tblYarnUse "Elastane"
ELASTANE_MATERIAL_ID = 6         # tblmaterial "EL" - elastane yarns are Garntyp FDY


def ply_path(yarn_use_id: Any, yarn_type_id: Any, material_id: Any = None) -> str:
    """"elastane" (separate source, fed at LW 2), "bypass" (drawn yarn on
    its own position, skips heater and friction, fed at the main jet) or
    "full" (POY: LW 1 - heater - friction - LW 2)."""
    for v, want in ((yarn_use_id, ELASTANE_YARN_USE_ID), (material_id, ELASTANE_MATERIAL_ID)):
        try:
            if int(v or 0) == want:
                return "elastane"
        except Exception:
            pass
    try:
        if int(yarn_type_id or 0) in DRAWN_YARN_TYPES:
            return "bypass"
    except Exception:
        pass
    return "full"


def merge_station(process_id: Any) -> str:
    """Where the plies run together onto one position."""
    try:
        if int(process_id or 0) == BEFORE_HEATER_PROCESS_ID:
            return "lw1"
    except Exception:
        pass
    return "lw2"


def visible_stations(show_pre: bool, show_jet3: bool, has_elastane: bool) -> List[str]:
    out = []
    for k, _lbl, _pp in STATIONS:
        if k in ("process",):
            continue
        if k in ("lw0", "prejet") and not show_pre:
            continue
        if k == "jet3" and not show_jet3:
            continue
        if k == "elastane" and not has_elastane:
            continue
        out.append(k)
    return out


# ── topology: which ply runs into which, and where ──────────────────────
MERGE_ORDER = ["lw1", "lw2", "mainjet", "lw2x", "setheater", "jet3", "lw3"]


def _pos(station: str) -> int:
    keys = [k for k, _l, _p in STATIONS]
    return keys.index(station) if station in keys else len(keys)


def resolve_topology(plies: List[Dict[str, Any]], process_id: Any = None) -> Dict[str, Any]:
    """plies: [{"no": ply number, "path": route or None, "auto_path": derived
    route, "into": target ply number or None, "at": merge station or None}]
    in table order.

    Returns {"main": index of the main ply, "plies": [{"path", "into" (index
    or None), "at" (station or None), "auto": bool}], "warnings": [...]}.
    Empty fields are derived like before the fields existed: the first ply
    that is not a separate source is the main line; the others run into it
    (separate source at LW 2, bypass at the main jet, full path at LW 2 or
    LW 1 for "before heater"). Wrong entries (unknown ply, loops, joining a
    ply that has already ended) give a warning and fall back to the main ply.
    """
    n = len(plies)
    out = [{"path": p.get("path") or p.get("auto_path") or "full",
            "into": None, "at": None, "auto": True} for p in plies]
    warnings: List[str] = []
    if not n:
        return {"main": None, "plies": out, "warnings": warnings}
    by_no: Dict[Any, int] = {}
    for i, p in enumerate(plies):
        by_no.setdefault(p.get("no"), i)
    label = [f"Ply {p.get('no')}" if p.get("no") is not None else f"Ply {i + 1}" for i, p in enumerate(plies)]

    explicit = {}
    for i, p in enumerate(plies):
        tgt = p.get("into")
        if tgt in (None, "", 0, "0"):
            continue
        try:
            tgt = int(float(tgt))
        except Exception:
            warnings.append(f"{label[i]}: 'Merge into ply' is not a number.")
            continue
        j = by_no.get(tgt)
        if j is None:
            warnings.append(f"{label[i]}: there is no Ply {tgt} in this trial.")
        elif j == i:
            warnings.append(f"{label[i]}: cannot merge into itself.")
        else:
            explicit[i] = j

    # loops (Ply 2 -> 3 -> 2): all plies of the loop fall back to the default
    for i in list(explicit):
        if i not in explicit:
            continue
        chain, k = [i], explicit.get(i)
        while k is not None and k not in chain:
            chain.append(k)
            k = explicit.get(k)
        if k is not None:
            loop = chain[chain.index(k):]
            warnings.append(" -> ".join(label[x] for x in loop + [k])
                            + ": the merge chain runs in a circle - check 'Merge into ply'.")
            for x in loop:
                explicit.pop(x, None)

    # main line: a ply that merges nowhere - prefer one that others target
    roots = [i for i in range(n) if i not in explicit]
    targeted = {j for j in explicit.values()}
    non_sep = [i for i in roots if out[i]["path"] != "elastane"]
    main = next((i for i in non_sep if i in targeted), None)
    if main is None:
        main = non_sep[0] if non_sep else roots[0] if roots else 0

    default_at = merge_station(process_id)
    for i in range(n):
        o = out[i]
        if i == main:
            continue
        if i in explicit:
            o["into"], o["auto"] = explicit[i], False
        else:
            o["into"] = main
        at = plies[i].get("at")
        if at:
            o["at"], o["auto"] = at, False
        elif o["path"] == "elastane":
            o["at"] = "lw2"
        elif o["path"] == "bypass":
            o["at"] = "mainjet"
        else:
            o["at"] = default_at

    # a ply can only join a ply that is still running at that station
    def end_of(k: int, depth: int = 0) -> int:
        if k == main or depth > n:
            return 10 ** 6
        return _pos(out[k]["at"] or "lw2")

    for i in range(n):
        o = out[i]
        if i == main or o["into"] is None:
            continue
        if o["into"] != main and _pos(o["at"]) >= end_of(o["into"]):
            warnings.append(f"{label[i]} joins {label[o['into']]} at {STATION_LABEL.get(o['at'], o['at'])}, "
                            f"but {label[o['into']]} has already merged before - drawn into the main line.")
            o["into"] = main
    return {"main": main, "plies": out, "warnings": warnings}


# ── speeds (Nutzerangabe 2026-11-07: LW 2 = Speed Shaft 2 is always 100 %) ──
def lw1_speed(lw2: Optional[float], dr: Optional[float]) -> Optional[float]:
    """LW 1 = LW 2 / Shaft 1 DR (draw ratio LW 1 -> LW 2)."""
    if lw2 is None or not dr:
        return None
    return lw2 / dr


def speeds(lw2: Optional[float], of_2x: Optional[float] = None, shaft3: Optional[float] = None,
           winder: Optional[float] = None) -> Dict[str, Optional[float]]:
    """Trial-level speeds in m/min. The percentages are always relative to
    LW 2 and mean "slower than LW 2": 5 % -> 0.95 x LW 2."""
    if not lw2:
        return {}

    def slower(pct):
        return None if pct is None else lw2 * (1 - pct / 100.0)
    return {"lw2": lw2, "lw2x": slower(of_2x), "lw3": slower(shaft3), "winder": slower(winder)}


def lw0_speed(lw1: Optional[float], of_w0_w1: Optional[float]) -> Optional[float]:
    """LW 0 = LW 1 / (1 - W0-W1 OF % / 100) - the overfeed between LW 0 and
    LW 1 refers to LW 1 (Nutzerangabe 2026-11-08)."""
    if lw1 is None or of_w0_w1 is None or of_w0_w1 >= 100:
        return None
    return lw1 / (1 - of_w0_w1 / 100.0)
