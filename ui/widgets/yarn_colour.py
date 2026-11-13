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

# fixed name -> colour table and the loader live Qt-free in db/yarn_colours.py (web app)
from db.yarn_colours import COLOUR_HEX, load_yarn_colours  # noqa: F401,E402

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
