"""machine_schema.py - data of the machine path schema above Machine Data in
Show Experiment (DTY and ATY), without Qt. Shared by the desktop
(ui/dty_schema_panel.py + ui/aty_schema.py paint it) and the web app
(tripplet_web backend/app/schema.py sends it as JSON, the page draws SVG).

Moved out of ui/dty_schema_panel.build_path / ui/aty_schema.build_path on
2026-11-13 - rules unchanged. The cells are read through a small "source"
object so the desktop can pass its Qt model and the web the
db/machine_data.MachineData:

    src.keys    row keys (db/machine_data row_keys, ui/dty_stations.py)
    src.titles  row titles
    src.specs   column specs (MachineData.col_specs)
    src.hidden  rows hidden by the DTY process rules (pre-jet / jet 3 / merge)
    src.display(r, c) -> str   cell text as shown in the table ("" = empty)
    src.value(r, c)            stored value (IDs for dropdown rows)
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from db import dty_process as dp
from db.machine_data import filled as _filled
from ui import aty_stations as ats
from ui import dty_stations as ds

# (row key, format) for the short text under a DTY station - first filled
# wins, jets join jet + pressure
SUMMARY = {
    "creel": [("position", "Pos {}")],
    "lw0": [("w0_w1_of", "OF {} %")],
    "prejet": [("preinterminglingjets", "{}"), ("preinterminglingairpressure", "{} bar")],
    "lw1": [("shaft1_dr", "DR {}")],
    "heater1": [("1stheatert1", "{} °C")],
    "friction": [("dyvalue", "D/Y {}"), ("discconfiguration", "{}")],
    "lw2": [("speedshaft2", "{} m/min")],
    "mainjet": [("jet", "{}"), ("airpressure", "{} bar")],
    "lw2x": [("shaft2x_of", "OF {} %")],
    "setheater": [("2ndheaterset", "{} °C"), ("setheatertemperature", "{} °C")],
    "jet3": [("w3_jet", "{}"), ("w3_airpressure", "{} bar")],
    "lw3": [("shaft3", "{} %")],
    "winder": [("winder", "{} %")],
    "elastane": [("draftelastane", "Draft {}")],
}
JOINED = {"prejet", "mainjet", "jet3"}

# short station names above the drawing (DTY; ATY: ui/aty_stations.SHORT)
SHORT = {"lw0": "LW 0", "prejet": "Pre-jet", "lw1": "LW 1", "heater1": "Heater",
         "cooling": "Cooling", "friction": "Friction", "lw2": "LW 2", "mainjet": "Main jet",
         "lw2x": "LW 2.x", "setheater": "Set heater", "jet3": "Jet 3", "lw3": "LW 3",
         "winder": "Winder", "elastane": "Elastane"}


def station_module(profile: Optional[str]):
    """Station module of a schema profile: ui/dty_stations or ui/aty_stations."""
    return ats if profile == "aty" else ds


# ── small helpers ────────────────────────────────────────────────────────
def num(v) -> Optional[float]:
    try:
        return float(str(v).replace(",", ".").strip())
    except Exception:
        return None


def speed_text(v: Optional[float]) -> str:
    return "" if v is None else (f"{v:.0f}" if abs(v - round(v)) < 0.05 else f"{v:.1f}") + " m/min"


def short(v: Optional[float]) -> str:
    if v is None:
        return ""
    return f"{v:.0f}" if abs(v - round(v)) < 1e-9 else f"{v:.2f}".rstrip("0").rstrip(".")


def as_int(v) -> int:
    try:
        return int(float(v))
    except Exception:
        return 0


def cell(src, key, col):
    keys = src.keys
    return src.value(keys.index(key), col) if key in keys else None


def _summary(src, station: str, c: int) -> Optional[str]:
    keys = src.keys
    parts = []
    for key, fmt in SUMMARY.get(station, []):
        if key not in keys:
            continue
        v = src.display(keys.index(key), c)
        if _filled(v):
            parts.append(fmt.format(v))
            if station not in JOINED:
                break
    return " · ".join(parts) or None


def _tip(src, station: str, c: int, mod=ds) -> Optional[str]:
    lines = []
    for r in mod.rows_of_station(src.keys, station):
        v = src.display(r, c)
        if (ats.filled if mod is ats else _filled)(v):
            lines.append(f"{src.titles[r]}: {v}")
    return "\n".join(lines) or None


def lane_order(plies, main: int) -> List[int]:
    """Main ply on top, every ply directly below the ply it runs into
    (sorted by merge point), separate sources last in their group."""
    children: Dict[int, List[int]] = {}
    for k, pl in enumerate(plies):
        if k != main and pl.get("into") is not None:
            children.setdefault(pl["into"], []).append(k)
    out: List[int] = []

    def visit(k):
        if k in out:
            return
        out.append(k)
        for c in sorted(children.get(k, []),
                        key=lambda c: (plies[c]["path"] == "elastane", ds._pos(plies[c].get("at") or "lw2"))):
            visit(c)
    visit(main)
    for k in range(len(plies)):
        visit(k)
    return out


def load_yarn_types(specs, cache: Optional[Dict[int, Any]] = None) -> Dict[int, Any]:
    """{YarnID: (Garntyp, Material)} for the plies of the columns; `cache` is
    completed and returned (the desktop keeps it on the screen)."""
    ids = sorted({int((cs.get("sr") or {}).get("YarnID") or 0) for cs in specs} - {0})
    if cache is not None and set(ids) <= set(cache):
        return cache
    out: Dict[int, Any] = dict(cache or {})
    if ids:
        try:
            from db.connection import fetch_all
            ph = ",".join(["?"] * len(ids))
            for r in fetch_all(f"SELECT ID, Garntyp, Material FROM tblyarn WHERE ID IN ({ph})", ids):
                out[int(r["ID"])] = (r.get("Garntyp"), r.get("Material"))
        except Exception:
            pass
        for i in ids:
            out.setdefault(i, (None, None))
    return out


# ── DTY ──────────────────────────────────────────────────────────────────
def _add_speeds(src, c0, plies, values, tips) -> None:
    """Speeds of the feed rolls and the winder, calculated from LW 2
    (Speed Shaft 2 = 100 %, Nutzerangabe 2026-11-07):
      LW 1   = LW 2 / Shaft 1 DR (per ply; for elastane = feed speed from its draft)
      LW 2.x = LW 2 x (1 - Shaft 2x OF % / 100)
      LW 3   = LW 2 x (1 - Shaft 3 % / 100)
      Winder = LW 2 x (1 - Winder % / 100)
      LW 0   = LW 1 / (1 - W0-W1 OF % / 100) (per ply)"""
    sp = ds.speeds(num(cell(src, "speedshaft2", c0)),
                   of_2x=num(cell(src, "shaft2x_of", c0)),
                   shaft3=num(cell(src, "shaft3", c0)),
                   winder=num(cell(src, "winder", c0)))
    for st, setting_key, fmt in (("lw2", None, None), ("lw2x", "shaft2x_of", "OF {} %"),
                                 ("lw3", "shaft3", "{} %"), ("winder", "winder", "{} %")):
        if sp.get(st) is None:
            continue
        line2 = "main speed" if st == "lw2" else ""
        if setting_key:
            raw = num(cell(src, setting_key, c0))
            line2 = fmt.format(short(raw)) if raw is not None else ""
        values[st] = speed_text(sp[st]) + (f"\n{line2}" if line2 else "")
        tips[st] = (tips.get(st) or "") + ("\n" if tips.get(st) else "") + \
            f"Speed (calculated from LW 2): {speed_text(sp[st])}"
    for pl in plies:
        dr = num(cell(src, "shaft1_dr", pl["idx"]))
        v1 = ds.lw1_speed(sp.get("lw2"), dr)
        if v1 is None:
            continue
        if pl.get("auto_path") == "elastane" or pl.get("path") == "elastane":
            pl["values"]["elastane"] = f"Draft {short(dr)} · {speed_text(v1)}"
        pl["values"]["lw1"] = speed_text(v1) + f"\nDR {short(dr)}"
        pl["tips"]["lw1"] = (pl["tips"].get("lw1") or "") + \
            f"\nSpeed (LW 2 / DR): {speed_text(v1)}"
        of0 = num(cell(src, "w0_w1_of", pl["idx"]))
        v0 = ds.lw0_speed(v1, of0)
        if v0 is not None:
            pl["values"]["lw0"] = speed_text(v0) + f"\nOF {short(of0)} %"
            pl["tips"]["lw0"] = (pl["tips"].get("lw0") or "") + \
                f"\nSpeed (LW 1 / (1 - OF %)): {speed_text(v0)}"


def build_dty_path(src, col: int, yarn_types: Dict[int, Any]) -> Dict[str, Any]:
    """Path data of the DTY trial in data column `col` (0-based)."""
    specs = src.specs or []
    keys = list(src.keys or [])
    if not specs or not (0 <= col < len(specs)):
        return {}
    tid = specs[col]["trial_id"]
    cols = [i for i, cs in enumerate(specs) if cs["trial_id"] == tid]
    c0 = cols[0]

    plies = []
    for i in cols:
        cs = specs[i]
        sr = cs.get("sr") or {}
        yid = sr.get("YarnID")
        try:
            ytype, material = yarn_types.get(int(yid or 0)) or (None, None)
        except Exception:
            ytype, material = None, None
        use = cs.get("yarn_use_id") if cs.get("is_group") else sr.get("YarnUseID")
        pos = src.display(keys.index("position"), i) if "position" in keys else ""
        values, tips = {}, {}
        for s in ds.PER_PLY:
            values[s] = _summary(src, s, i)
            tips[s] = _tip(src, s, i)
        auto_path = ds.ply_path(use, ytype, material)
        route = dp.ROUTE_CODE.get(as_int(cell(src, "dtyrouteid", i)))
        at = dp.MERGE_CODE.get(as_int(cell(src, "mergepointid", i)))
        m_no = re.search(r"\d+", str(cs.get("ply") or ""))
        plies.append({"idx": i, "label": cs.get("ply") or "", "pos": pos,
                      "yarn": cs.get("yarn_name") or "", "path": route or auto_path,
                      "auto_path": auto_path, "route_set": route,
                      "is_elastane": auto_path == "elastane",
                      "no": int(m_no.group()) if m_no else None,
                      "into_raw": cell(src, "mergeintoply", i), "at_raw": at,
                      "values": values, "tips": tips})
    for pl in plies:
        if pl["path"] == "elastane" and not pl["values"].get("elastane") and pl["values"].get("lw1"):
            # the elastane draft sits in the ply's "Shaft 1 DR" cell
            pl["values"]["elastane"] = pl["values"]["lw1"].replace("DR", "Draft", 1)

    proc_id = src.value(keys.index("dtyprocessid"), c0) if "dtyprocessid" in keys else None
    proc_name = src.display(keys.index("dtyprocessid"), c0) if "dtyprocessid" in keys else ""
    hidden: Set[int] = set(src.hidden or ())
    show_pre = any(k in ds.PREJET_KEYS and r not in hidden for r, k in enumerate(keys))
    show_jet3 = any(k in ds.JET3_KEYS and r not in hidden for r, k in enumerate(keys))
    has_el = any(pl["path"] == "elastane" for pl in plies)
    values = {s: _summary(src, s, c0) for s, _l, pp in ds.STATIONS if not pp}
    tips = {s: _tip(src, s, c0) for s, _l, pp in ds.STATIONS if not pp}
    _add_speeds(src, c0, plies, values, tips)
    topo = ds.resolve_topology(
        [{"no": pl["no"], "path": pl["route_set"], "auto_path": pl["auto_path"],
          "into": pl["into_raw"], "at": pl["at_raw"]} for pl in plies], proc_id)
    for pl, t in zip(plies, topo["plies"]):
        pl.update(path=t["path"], into=t["into"], at=t["at"], auto=t["auto"])
    main = topo["main"] if topo["main"] is not None else 0
    order = lane_order(plies, main)
    hdr = specs[c0]
    vno = hdr.get("vno")
    title = f"V{vno}" if vno is not None and int(vno) > 0 else "Ref"
    return {
        "title": title, "trial_id": tid, "process": proc_name if _filled(proc_name) else "",
        "process_id": proc_id, "plies": plies, "has_elastane": has_el,
        "main": main, "order": order, "warnings": topo["warnings"],
        "stations": ds.visible_stations(show_pre, show_jet3, False),
        "values": values, "tips": tips,
    }


# ── ATY ──────────────────────────────────────────────────────────────────
def _aty_summary(src, station: str, c: int) -> Optional[str]:
    keys = src.keys
    parts = []
    for key, fmt in ats.SUMMARY.get(station, []):
        if key in keys:
            v = src.display(keys.index(key), c)
            if ats.filled(v):
                parts.append(fmt.format(v))
    return "\n".join(parts[:2]) or None


def _add_line(tips: Dict[str, Any], station: str, line: str) -> None:
    tips[station] = (tips.get(station) + "\n" if tips.get(station) else "") + line


def build_aty_path(src, col: int) -> Dict[str, Any]:
    """Path data of the ATY trial in data column `col` (0-based)."""
    specs = src.specs or []
    keys = list(src.keys or [])
    if not specs or not (0 <= col < len(specs)):
        return {}
    tid = specs[col]["trial_id"]
    cols = [i for i, cs in enumerate(specs) if cs["trial_id"] == tid]
    c0 = cols[0]

    lw2 = num(cell(src, "shaft2speed", c0))
    plies: List[Dict[str, Any]] = []
    for i in cols:
        cs = specs[i]
        sr = cs.get("sr") or {}
        use = cs.get("yarn_use_id") if cs.get("is_group") else sr.get("YarnUseID")
        role = ats.role_of(use)
        pos = src.display(keys.index("position"), i) if "position" in keys else ""
        values = {s: _aty_summary(src, s, i) for s in ats.PER_PLY}
        tips = {s: _tip(src, s, i, ats) for s in ats.PER_PLY}
        # feed roll: speed from LW 2 and the overfeed, draw-in speed from DR
        of = num(cell(src, "of", i))
        dr = num(cell(src, "dr", i))
        temps = [src.display(keys.index(k), i) for k in ("temp0", "temp1") if k in keys]
        temps = [t for t in temps if ats.filled(t)]
        if dr is not None and ats.filled(dr):
            values["draw"] = f"DR {short(dr)}" + (f"\n{' / '.join(temps)} °C" if temps else "")
        elif temps:
            values["draw"] = f"{' / '.join(temps)} °C"
        v_feed = ats.feed_speed(lw2, of)
        if v_feed is not None:
            values["feed"] = speed_text(v_feed) + f"\nOF {short(of)} %"
            _add_line(tips, "feed", f"Speed (LW 2 x (1 + OF %)): {speed_text(v_feed)}")
            v0 = ats.draw_in_speed(v_feed, dr)
            if v0 is not None and dr != 1:
                _add_line(tips, "draw", f"Draw-in speed (feed roll / DR): {speed_text(v0)}")
        elif of is not None:
            values["feed"] = f"OF {short(of)} %"
        label = ats.ROLE_LABEL.get(role or "", "")
        plies.append({"idx": i, "label": label or (cs.get("ply") or ""), "ply": cs.get("ply") or "",
                      "pos": pos if ats.filled(pos) else "", "yarn": cs.get("yarn_name") or "",
                      "role": role, "values": values, "tips": tips})

    values = {s: _aty_summary(src, s, c0) for s, _l, pp in ats.STATIONS if not pp}
    tips = {s: _tip(src, s, c0, ats) for s, _l, pp in ats.STATIONS if not pp}
    if lw2:
        values["lw2"] = speed_text(lw2) + "\ntake-off"
    show_draw = any(pl["values"].get("draw") for pl in plies) or \
        any(ats.station_of(k) == "draw" for k in keys)
    stations = [s for s, _l, _pp in ats.STATIONS if s != "draw" or show_draw]
    vno = specs[c0].get("vno")
    unset = [pl["ply"] for pl in plies if pl["role"] is None]
    warnings = []
    if unset and len(plies) > 1:
        warnings.append("no yarn use (core/effect) for " + ", ".join(str(u) for u in unset)
                        + " - set it in the Yarn Use row")
    return {
        "profile": "aty", "title": f"V{vno}" if vno is not None and int(vno) > 0 else "Ref",
        "trial_id": tid, "process": "Air texturing", "plies": plies,
        "order": ats.lane_order([pl["role"] for pl in plies]),
        "stations": stations, "values": values, "tips": tips, "warnings": warnings,
    }


# ── profile ──────────────────────────────────────────────────────────────
def profile(cache: Optional[Dict[str, Any]], row_keys: List[Optional[str]]) -> Optional[str]:
    """'dty' / 'aty' / None - which schema the Machine Data of a series gets.
    cache = db/machine_data.load_machine_cache() (completed here: is_dty, is_aty)."""
    from db import machine_data as _md
    if _md.is_dty_active(cache if cache is not None else {}, row_keys or []):
        return "dty"
    if cache is None:
        return None
    if "is_aty" not in cache:
        cache["is_aty"] = False
        mid = cache.get("machine_id")
        if mid:
            try:
                from db.connection import fetch_all
                rows = fetch_all("SELECT Maschinentyp FROM tblmaschine WHERE ID = ?", [mid])
                cache["is_aty"] = bool(rows) and int(rows[0].get("Maschinentyp") or 0) == ats.ATY_MACHINE_TYPE
            except Exception:
                pass
    return "aty" if cache["is_aty"] and row_keys else None


def kb_target(station: Optional[str], profile_: Optional[str] = None):
    """Knowledge Base target of a schema station, or None (e.g. elastane feed)."""
    from ui.kb_links import ATY_STATION_TARGET, DTY_STATION_TARGET
    return (ATY_STATION_TARGET if profile_ == "aty" else DTY_STATION_TARGET).get(station or "")


def station_rows(row_keys: List[Optional[str]], station: str, profile_: Optional[str]) -> List[int]:
    """Machine Data rows (0-based) highlighted for a station - the elastane
    feed of DTY also marks the creel and LW 1 rows of its ply."""
    mod = station_module(profile_)
    stations = ("creel", "lw1", "elastane") if station == "elastane" and mod is ds else (station,)
    return sorted(r for st in stations for r in mod.rows_of_station(row_keys, st))


# ── web: source over db/machine_data.MachineData ─────────────────────────
class MachineDataSource:
    """Cells of a db/machine_data.MachineData, shown like the desktop table."""

    def __init__(self, md, jets_map=None, housing_map=None, hidden=None):
        from db import machine_data as _md
        self._md = md
        self._jets = jets_map or {}
        self._housing = housing_map or {}
        self._text = _md.display_text
        self.keys = list(md.row_keys or [])
        self.titles = list(md.row_titles or [])
        self.specs = list(md.col_specs or [])
        self.hidden = set(md.process_hidden_rows if hidden is None else hidden)

    def display(self, r: int, c: int) -> str:
        return str(self._text(self._md, r, c, self._jets, self._housing) or "").strip()

    def value(self, r: int, c: int):
        try:
            return self._md.cells[r][c][0]
        except IndexError:
            return None
