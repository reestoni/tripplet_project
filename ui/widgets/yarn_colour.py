# ui/widgets/yarn_colour.py
"""Small colour square for a yarn (Nutzerwunsch 2026-10-22).

tblYarn.ColourID -> tblColour.Colour holds only a NAME ("white", "black"...),
no colour code. The name -> colour table below is fixed on purpose (user
decision: no extra column in tblColour). Names that are not in the table are
tried as Qt colour names ("red", "navy"...); anything else gets a neutral
square with "?". Yarns without colour get no square (empty icon).

    icon = colour_icon(colours.get(yarn_id))   # QIcon, 12x12, grey border
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap

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

_BORDER = QColor("#7A7A7A")
_UNKNOWN_FILL = QColor("#E6E6E6")
_icon_cache: Dict[Tuple[str, int], QIcon] = {}


def colour_qcolor(name: Optional[str]) -> Optional[QColor]:
    """QColor for a colour name, None if empty or unknown."""
    key = (name or "").strip().lower()
    if not key:
        return None
    if key in COLOUR_HEX:
        return QColor(COLOUR_HEX[key])
    c = QColor(key.replace(" ", ""))
    return c if c.isValid() else None


def colour_icon(name: Optional[str], size: int = 12) -> QIcon:
    """Filled square with a thin border (so white stays visible); empty icon
    without colour, "?" square for an unknown colour name."""
    key = (name or "").strip().lower()
    if not key:
        return QIcon()
    cached = _icon_cache.get((key, size))
    if cached is not None:
        return cached
    colour = colour_qcolor(key)
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, False)
    p.setPen(QPen(_BORDER, 1))
    p.setBrush(colour if colour is not None else _UNKNOWN_FILL)
    p.drawRect(QRectF(0.5, 0.5, size - 1, size - 1))
    if colour is None:
        f = QFont()
        f.setPixelSize(max(7, size - 3))
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("#555555"))
        p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, "?")
    p.end()
    icon = QIcon(pm)
    _icon_cache[(key, size)] = icon
    return icon


def colour_tooltip(name: Optional[str]) -> str:
    return f"Colour: {name.strip()}" if (name or "").strip() else "Colour: not set"


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
