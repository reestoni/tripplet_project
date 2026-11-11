"""dty_process.py - DTY process per trial ("Standard", "Elastane", the
cotton-like variants), Nutzerwunsch 2026-11-07.

Storage:
- lookup table `tbldtyprocess` (ID, Code, Name, Description, SortOrder,
  UsesPreJet, UsesJet3, GlobalID) - entries can be added/renamed without
  touching trial data;
- `tbltrial.DTYProcessID` per trial;
- shown in Machine Data as an ordinary dropdown row from tblMachineFields
  (FieldName "DTY Process", OriginalName "DTYProcessID",
  FieldFunction "dropdown:tblDTYProcess") on DTY machines
  (tblmaschine.Maschinentyp = 1) - so saving, yellow cells, undo and the
  change log work like for every other machine value.

UsesPreJet / UsesJet3 only decide which rows Machine Data shows by default
(pre-intermingling jet between LW 0 and LW 1, third jet after the set
heater before LW 3); rows with values are always shown.

Schema changes live in tools/dty_process_migration.py (apply / rollback,
dev_local only).
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

TABLE = "tbldtyprocess"
LOOKUP_NAME = "tblDTYProcess"          # as written in FieldFunction "dropdown:..."
TRIAL_COLUMN = "DTYProcessID"
FIELD_NAME = "DTY Process"            # row title in Machine Data
DTY_MACHINE_TYPE = 1                  # tblmaschine.Maschinentyp of DTY machines
ELASTANE_YARN_USE_ID = 3              # tblYarnUse "Elastane"
ELASTANE_MATERIAL_ID = 6              # tblmaterial "EL" (elastane yarns are stored as Garntyp FDY)

# (ID, Code, Name, Description, SortOrder, UsesPreJet, UsesJet3)
SEED: List[tuple] = [
    (1, "STD", "Standard",
     "POY plies on their own positions, merged at LW 2 / main jet.", 10, 0, 0),
    (2, "EL", "Elastane",
     "Standard DTY plus elastane from a separate source, fed at LW 2.", 20, 0, 0),
    (3, "CL-A", "Cotton-like: effect at jet",
     "FDY bypasses heater and friction and is fed with overfeed at the main "
     "jet (intermingling or texturing jet).", 30, 0, 0),
    (4, "CL-C", "Cotton-like: two jets",
     "Texturing jet and intermingling jet one after the other.", 40, 1, 1),
    (5, "CL-D", "Cotton-like: before heater",
     "Two POY merged at the inlet, usually with a pre-intermingling jet.", 50, 1, 0),
    (6, "CL-E", "Cotton-like: jet after set heater",
     "Additional intermingling jet after the set heater, before LW 3.", 60, 0, 1),
    (7, "CL-F", "Cotton-like: thick-thin",
     "One POY, draw ratio deliberately below the natural draw ratio.", 70, 0, 0),
    (8, "CL-G", "Cotton-like: filament breaking",
     "One POY, single filaments broken on purpose (hairiness).", 80, 0, 0),
]
STANDARD_ID = 1
ELASTANE_ID = 2

# ── How the plies run together (per ply in tbltrialsettings) ────────────
# Empty = derived as before (ui/dty_stations.py): POY full path, drawn yarn
# bypass, elastane separate source; all plies into the first one at LW 2
# (LW 1 for "before heater", main jet for bypass).
ROUTE_TABLE = "tbldtyroute"
ROUTE_LOOKUP = "tblDTYRoute"
ROUTE_COLUMN = "DTYRouteID"
ROUTE_FIELD = "Route"
# (ID, Code, Name, SortOrder) - Code = path kind used by the schema
ROUTE_SEED: List[tuple] = [
    (1, "full", "Full (LW 1 - heater - friction)", 10),
    (2, "bypass", "Bypass (own feed, no heater/friction)", 20),
    (3, "elastane", "Separate source (no position)", 30),
]
MERGE_TABLE = "tbldtymergepoint"
MERGE_LOOKUP = "tblDTYMergePoint"
MERGE_POINT_COLUMN = "MergePointID"
MERGE_POINT_FIELD = "Merge point"
MERGE_INTO_COLUMN = "MergeIntoPly"
MERGE_INTO_FIELD = "Merge into ply"
# (ID, Code, Name, SortOrder) - Code = station key in ui/dty_stations.py;
# the ply joins the target ply right before this station
MERGE_SEED: List[tuple] = [
    (1, "lw1", "LW 1 (inlet)", 10),
    (2, "lw2", "LW 2", 20),
    (3, "mainjet", "Main jet", 30),
    (4, "lw2x", "LW 2.x", 40),
    (5, "setheater", "Set heater", 50),
    (6, "jet3", "Jet 3", 60),
    (7, "lw3", "LW 3", 70),
]
ROUTE_CODE = {r[0]: r[1] for r in ROUTE_SEED}
MERGE_CODE = {r[0]: r[1] for r in MERGE_SEED}


def available() -> bool:
    try:
        from db.connection import table_exists
        return table_exists(TABLE)
    except Exception:
        return False


def load_processes() -> List[Dict[str, Any]]:
    """All processes ordered by SortOrder ([] if the table is missing)."""
    if not available():
        return []
    try:
        from db.connection import fetch_all
        return fetch_all(
            f"SELECT ID, Code, Name, Description, SortOrder, UsesPreJet, UsesJet3 "
            f"FROM {TABLE} ORDER BY SortOrder, ID")
    except Exception:
        return []


def flags_by_id(processes: Optional[Iterable[Dict[str, Any]]] = None) -> Dict[int, Dict[str, bool]]:
    """{process id: {"pre": UsesPreJet, "jet3": UsesJet3}}."""
    out: Dict[int, Dict[str, bool]] = {}
    for p in (load_processes() if processes is None else processes):
        try:
            out[int(p["ID"])] = {"pre": bool(int(p.get("UsesPreJet") or 0)),
                                 "jet3": bool(int(p.get("UsesJet3") or 0))}
        except Exception:
            continue
    return out


def default_for_plies(plies: Iterable[tuple]) -> int:
    """Process for an existing trial from its plies [(YarnUseID, material
    ID), ...]: Elastane if one ply is elastane (yarn use or material),
    otherwise Standard (all DTY trials so far ran that way, Nutzerangabe)."""
    for use, material in plies:
        try:
            if int(use or 0) == ELASTANE_YARN_USE_ID or int(material or 0) == ELASTANE_MATERIAL_ID:
                return ELASTANE_ID
        except Exception:
            continue
    return STANDARD_ID


def is_dty_machine(machine_id: Any) -> bool:
    if not machine_id:
        return False
    try:
        from db.connection import fetch_all
        rows = fetch_all("SELECT Maschinentyp FROM tblmaschine WHERE ID = ?", [machine_id])
        return bool(rows) and int(rows[0].get("Maschinentyp") or 0) == DTY_MACHINE_TYPE
    except Exception:
        return False
