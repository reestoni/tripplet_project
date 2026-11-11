"""aty_stations.py - stations of the ATY (air-texturing) machine path and
which Machine Data rows belong to them, for the schema above Machine Data in
Show Experiment (ui/aty_schema.py, drawn by ui/dty_schema_panel.py).
Pure logic, no Qt - tested in tests/test_aty_schema.py.

Path as in the Knowledge Base page aty_air_texturing (scene "Machine"):
creel -> (draw zone godet 0 -> 1) -> feed roll with overfeed, core and
effect separately -> wetting (core only, the effect joins dry just before
the jet) -> texturing jet -> LW 2 (take-off) ->
stabilising zone (optional heater) -> LW 3 -> winder. All plies meet in the
jet, so there is no merge logic as in DTY.

Row keys: see ui/dty_stations.py (fixed rows by short name, machine fields
by DB column in lower case).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

ATY_MACHINE_TYPE = 3   # tblmaschine.Maschinentyp (SSM DP2T, ATY dummy)

# (key, label, per_ply) in machine order
STATIONS: List[tuple] = [
    ("creel", "Creel / Position", True),
    ("draw", "Draw zone (godet 0 -> 1)", True),
    ("feed", "Feed roll (overfeed)", True),
    ("wetting", "Wetting", False),
    ("jet", "Texturing jet", False),
    ("lw2", "LW 2 (take-off)", False),
    ("stabilise", "Stabilising zone", False),
    ("lw3", "LW 3", False),
    ("winder", "Winder", False),
]
STATION_LABEL = {k: lbl for k, lbl, _ in STATIONS}
PER_PLY = {k for k, _, pp in STATIONS if pp}
SHORT = {"draw": "Draw", "feed": "Feed roll", "wetting": "Wetting", "jet": "Jet",
         "lw2": "LW 2", "stabilise": "Stabilising", "lw3": "LW 3", "winder": "Winder"}

FIELD_STATION: Dict[str, str] = {
    # creel / position
    "position": "creel", "yarnuse": "creel", "spool": "creel", "plies": "creel",
    "pretension": "creel",
    # draw zone between godet 0 and godet 1 (both heated)
    "dr": "draw", "temp0": "draw", "temp1": "draw",
    # feed roll = godet 1, overfeed into the jet
    "of": "feed",
    # wetting before the jet - core only
    "wettingheadid": "wetting", "waterpressure": "wetting",
    # texturing jet (in the splash box)
    "housing": "jet", "housingid": "jet", "jet": "jet", "jetid": "jet",
    "jetplate": "jet", "airpressure": "jet", "topplateid": "jet",
    "yarntensionbeforejet": "jet", "tensionafterjetinside": "jet",
    "tensionafterjetoutside": "jet", "position1e": "jet",
    "atyhaloentrycore": "jet", "atyhaloentryeffect": "jet", "atyhaloexit": "jet",
    "anglejetentry": "jet", "anglejetexit": "jet",
    "yarnguidebeforejet": "jet", "yarnguideafterjet": "jet",
    # LW 2 = take-off after the jet, its speed is the reference
    "shaft2speed": "lw2", "speedshaft2": "lw2", "positionw2": "lw2",
    # stabilising zone LW 2 -> LW 3 (stretch, optional heater)
    "w2": "stabilise", "w2tension": "stabilise",
    "setheatertemperature": "stabilise", "lengthsetheater": "stabilise",
    # LW 3
    "w3": "lw3", "w3tension": "lw3", "w3temperature": "lw3",
    # winder
    "winder": "winder", "winding": "winder", "crossingangle": "winder",
    "traverse": "winder", "amplitude": "winder", "counterwobble": "winder",
}

# (row key, format) for the short text under a station: first line, second line
SUMMARY: Dict[str, List[tuple]] = {
    "draw": [("dr", "DR {}")],
    "wetting": [("waterpressure", "{} bar"), ("wettingheadid", "{}")],
    "jet": [("jet", "{}"), ("airpressure", "{} bar")],
    "stabilise": [("w2", "{} %"), ("setheatertemperature", "{} °C")],
    "lw3": [("w3", "{} %"), ("w3temperature", "{} °C")],
    "winder": [("winding", "{}")],
}

# tblYarnUse
CORE, EFFECT, ELASTANE = 1, 2, 3
ROLE = {CORE: "core", EFFECT: "effect", ELASTANE: "elastane"}
ROLE_LABEL = {"core": "Core", "effect": "Effect", "elastane": "Elastane"}


def station_of(row_key: Optional[str]) -> Optional[str]:
    return FIELD_STATION.get(str(row_key or "").lower())


def rows_of_station(row_keys: List[Optional[str]], station: str) -> List[int]:
    return [i for i, k in enumerate(row_keys) if station_of(k) == station]


def filled(v: Any) -> bool:
    """A value worth showing - 0 counts as empty (unused heaters are stored as 0)."""
    if v is None:
        return False
    s = str(v).strip()
    if s in ("", "—", "None"):
        return False
    try:
        return float(s.replace(",", ".")) != 0
    except ValueError:
        return True


def role_of(yarn_use_id: Any) -> Optional[str]:
    try:
        return ROLE.get(int(yarn_use_id))
    except (TypeError, ValueError):
        return None


def lane_order(roles: List[Optional[str]]) -> List[int]:
    """Core first, then effect, elastane, plies without yarn use - stable
    within a role (the ply numbers are not consistent: 423 trials on dev_local
    have the effect as ply 1)."""
    rank = {"core": 0, "effect": 1, "elastane": 2}
    return sorted(range(len(roles)), key=lambda i: (rank.get(roles[i], 3), i))


def feed_speed(lw2: Optional[float], of: Optional[float]) -> Optional[float]:
    """Feed roll = LW 2 x (1 + OF / 100): overfeed = (feed - take-off) / take-off
    (Knowledge Base aty_air_texturing, scene Overfeed)."""
    if not lw2 or of is None:
        return None
    return lw2 * (1 + of / 100.0)


def draw_in_speed(feed: Optional[float], dr: Optional[float]) -> Optional[float]:
    """Godet 0 = feed roll / draw ratio."""
    if not feed or not dr:
        return None
    return feed / dr
