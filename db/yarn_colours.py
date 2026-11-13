"""yarn_colours.py - yarn colour names without Qt (moved out of
ui/widgets/yarn_colour.py on 2026-11-13 so db/machine_data.py and the web
app can use them; ui/widgets/yarn_colour.py re-exports both and draws the
squares).

tblYarn.ColourID -> tblColour.Colour holds only a NAME ("white", "black"...),
no colour code. The name -> colour table below is fixed on purpose (user
decision: no extra column in tblColour).
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

# fixed table - all colours of tblColour (2026-10-22) plus obvious spellings
COLOUR_HEX: Dict[str, str] = {
    "white": "#FFFFFF",
    "natural": "#F3EAD3",
    "raw white": "#F3EAD3",
    "beige": "#D9C4A0",
    "black": "#1A1A1A",
    "grey": "#9A9A9A",
    "gray": "#9A9A9A",
}


def colour_css(name: Optional[str]) -> Optional[str]:
    """CSS colour for a colour name (web): the fixed hex, else the name without
    spaces (Qt and CSS share the SVG colour names); None without a name. The
    desktop additionally shows a "?" square for names Qt does not know."""
    key = (name or "").strip().lower()
    if not key:
        return None
    return COLOUR_HEX.get(key) or key.replace(" ", "")


def load_yarn_colours() -> Tuple[Dict[int, str], Dict[str, str]]:
    """({yarn_id: colour name}, {yarn name: colour name}). Best effort: empty
    dicts if tblColour/ColourID do not exist (e.g. older offline snapshot)."""
    by_id: Dict[int, str] = {}
    by_name: Dict[str, str] = {}
    try:
        from db.connection import fetch_all
        rows = fetch_all(
            "SELECT y.ID AS YarnID, y.Name AS YarnName, c.Colour AS Colour "
            "FROM tblYarn y JOIN tblColour c ON c.ID = y.ColourID", [])
    except Exception:
        return by_id, by_name
    for r in rows:
        colour = str(r.get("Colour") or "").strip()
        if not colour:
            continue
        if r.get("YarnID") is not None:
            by_id[int(r["YarnID"])] = colour
        if r.get("YarnName"):
            by_name[str(r["YarnName"])] = colour
    return by_id, by_name
