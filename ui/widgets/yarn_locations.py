# ui/widgets/yarn_locations.py
"""Where are the spools of a yarn? (Nutzerwunsch 2026-10-30)

Show Experiment puts a small spool symbol behind every ply in the Material box:
full spool = spools of this yarn are in stock, empty tube = none in stock.
Clicking the full spool opens YarnLocationsDialog with every spool in stock,
sorted by location (with tube colour, batch, weight and whether the spool is
assigned to the current series via tblTrialSettings.SpoolID).

"In stock" = tblYarnSpool.Status = 'in stock' - same rule as Yarn Stock.

    summary = load_stock_summary([12, 15])       # {yarn_id: StockSummary}
    html = stock_symbol_html(12, summary.get(12))
"""
from __future__ import annotations

import html
import os
import re
import tempfile
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Set

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from db.connection import fetch_all, table_exists
from ui.widgets.yarn_colour import colour_icon, colour_qcolor, colour_tooltip

SYMBOL_SIZE = 16          # displayed size in the Material box (px)
_SYMBOL_SCALE = 2         # drawn at 2x so it stays sharp on HiDPI screens
_symbol_paths: Dict[bool, str] = {}


@dataclass
class StockSummary:
    spools: int
    kg: float
    locations: int


def location_sort_key(loc: Optional[str]) -> List[object]:
    """Natural sort: E2 before E12, empty locations last."""
    s = (loc or "").strip().upper()
    if not s:
        return [1]
    return [0] + [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s) if t]


def load_stock_summary(yarn_ids: Iterable[int]) -> Dict[int, StockSummary]:
    """{yarn_id: StockSummary} for yarns with at least one spool in stock.
    Yarns without stock are missing from the dict. Best effort: {} on error."""
    ids = sorted({int(y) for y in yarn_ids if y is not None})
    if not ids or not table_exists("tblYarnSpool"):
        return {}
    ph = ",".join(["?"] * len(ids))
    try:
        rows = fetch_all(
            f"SELECT YarnID, COUNT(*) AS n, SUM(WeightKg) AS kg, "
            f"COUNT(DISTINCT Location) AS locs FROM tblYarnSpool "
            f"WHERE YarnID IN ({ph}) AND Status = 'in stock' GROUP BY YarnID",
            ids,
        )
    except Exception:
        return {}
    out: Dict[int, StockSummary] = {}
    for r in rows:
        n = int(r.get("n") or 0)
        if n <= 0 or r.get("YarnID") is None:
            continue
        out[int(r["YarnID"])] = StockSummary(
            spools=n, kg=float(r.get("kg") or 0.0), locations=int(r.get("locs") or 0))
    return out


def _draw_symbol(in_stock: bool) -> QPixmap:
    """Side view of a spool: grey tube with flanges, wound yarn when in stock."""
    s = SYMBOL_SIZE * _SYMBOL_SCALE
    pm = QPixmap(s, s)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    tube = QColor("#8A8A8A")
    # flanges top and bottom
    p.setPen(Qt.NoPen)
    p.setBrush(tube)
    p.drawRoundedRect(QRectF(s * 0.18, s * 0.06, s * 0.64, s * 0.12), 2, 2)
    p.drawRoundedRect(QRectF(s * 0.18, s * 0.82, s * 0.64, s * 0.12), 2, 2)
    if in_stock:
        p.setBrush(QColor("#3E8E41"))
        p.drawRoundedRect(QRectF(s * 0.24, s * 0.18, s * 0.52, s * 0.64), 3, 3)
        p.setPen(QPen(QColor("#2C6B2F"), max(1, s // 20)))
        for f in (0.36, 0.50, 0.64):
            p.drawLine(int(s * 0.28), int(s * f), int(s * 0.72), int(s * f))
    else:
        p.setBrush(QBrush(tube))
        p.drawRect(QRectF(s * 0.42, s * 0.18, s * 0.16, s * 0.64))
        p.setPen(QPen(QColor("#C0392B"), max(2, s // 12), Qt.SolidLine, Qt.RoundCap))
        p.drawLine(int(s * 0.12), int(s * 0.88), int(s * 0.88), int(s * 0.12))
    p.end()
    return pm


def symbol_path(in_stock: bool) -> str:
    """PNG file of the symbol (QLabel rich text needs a file for <img>)."""
    path = _symbol_paths.get(in_stock)
    if path and os.path.exists(path):
        return path
    folder = os.path.join(tempfile.gettempdir(), "TrippleT")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"spool_{'in' if in_stock else 'none'}_v1.png")
    _draw_symbol(in_stock).save(path, "PNG")
    _symbol_paths[in_stock] = path
    return path


def stock_symbol_html(yarn_id: int, summary: Optional[StockSummary]) -> str:
    """<img> for the Material box. In stock -> link "stock:<id>" (clickable),
    otherwise a plain image (nothing to show)."""
    try:
        src = symbol_path(summary is not None).replace("\\", "/")
    except Exception:
        return ""
    img = (f'<img src="{src}" width="{SYMBOL_SIZE}" height="{SYMBOL_SIZE}" '
           f'style="vertical-align: middle;">')
    if summary is None:
        return f'<a href="nostock:{int(yarn_id)}" style="text-decoration:none;">{img}</a>'
    return f'<a href="stock:{int(yarn_id)}" style="text-decoration:none;">{img}</a>'


def stock_symbol_tooltip(summary: Optional[StockSummary]) -> str:
    if summary is None:
        return "Not in stock"
    sp = "spool" if summary.spools == 1 else "spools"
    loc = "location" if summary.locations == 1 else "locations"
    return (f"In stock: {summary.spools} {sp}, {summary.kg:.1f} kg "
            f"in {summary.locations} {loc}<br>Click to see where")


# tube colours are free text, often two-tone ("Black/Yellow", "white / green")
# and with lab spellings - extras on top of yarn_colour.COLOUR_HEX
_TUBE_ALIASES = {"lila": "purple", "blac": "black", "rosa": "pink", "gelb": "yellow",
                 "schwarz": "black", "weiss": "white", "grün": "green", "gruen": "green",
                 "rot": "red", "blau": "blue", "braun": "brown", "grau": "grey"}
_tube_icon_cache: Dict[str, QIcon] = {}


def tube_colours(text: Optional[str]) -> List[QColor]:
    """Colours of a tube colour text, e.g. "black / pink" -> [black, pink].
    Extra words ("with print", "conical") are ignored; unknown parts dropped."""
    out: List[QColor] = []
    for part in re.split(r"[/,+&]|\band\b", (text or "").lower()):
        for word in part.split():
            c = colour_qcolor(_TUBE_ALIASES.get(word, word))
            if c is not None:
                out.append(c)
                break
    return out[:3]


def tube_colour_icon(text: Optional[str], size: int = 12) -> QIcon:
    """Square split into vertical stripes, one per tube colour; falls back to
    colour_icon() ("?" square) if no colour is recognised."""
    key = (text or "").strip().lower()
    if not key:
        return QIcon()
    cached = _tube_icon_cache.get(key)
    if cached is not None:
        return cached
    colours = tube_colours(key)
    if not colours:
        icon = colour_icon(key, size)
    else:
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        w = (size - 1) / len(colours)
        p.setPen(Qt.NoPen)
        for i, c in enumerate(colours):
            p.setBrush(c)
            p.drawRect(QRectF(0.5 + i * w, 0.5, w, size - 1))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor("#7A7A7A"), 1))
        p.drawRect(QRectF(0.5, 0.5, size - 1, size - 1))
        p.end()
        icon = QIcon(pm)
    _tube_icon_cache[key] = icon
    return icon


def load_spools_in_stock(yarn_id: int) -> List[Dict]:
    """All spools of the yarn in stock, sorted by location. 'Colour' (tube
    colour) is optional in older databases."""
    if not table_exists("tblYarnSpool"):
        return []
    base = "SELECT ID, Charge, WeightKg, Location, ReceivedDate{c} FROM tblYarnSpool " \
           "WHERE YarnID = ? AND Status = 'in stock'"
    try:
        rows = fetch_all(base.format(c=", Colour"), [int(yarn_id)])
    except Exception:
        rows = fetch_all(base.format(c=""), [int(yarn_id)])
    rows.sort(key=lambda r: (location_sort_key(r.get("Location")), str(r.get("Charge") or ""),
                             int(r.get("ID") or 0)))
    return rows


def load_series_spool_ids(series_pk) -> Set[int]:
    """Spools assigned to trials of the series (Machine Data -> row 'Spool')."""
    if not series_pk:
        return set()
    try:
        rows = fetch_all(
            "SELECT DISTINCT ts.SpoolID FROM tblTrialSettings ts "
            "JOIN tblTrial t ON t.ID = ts.TrialID "
            "WHERE t.TrialSeriesID = ? AND ts.SpoolID IS NOT NULL",
            [series_pk])
    except Exception:
        return set()
    out: Set[int] = set()
    for r in rows:
        try:
            if int(r["SpoolID"] or 0) > 0:
                out.add(int(r["SpoolID"]))
        except Exception:
            pass
    return out


class YarnLocationsDialog(QDialog):
    """Read-only list of all spools of one yarn in stock, grouped by location
    (alternating background per location). Spools assigned to the current
    series are bold and marked in the last column."""

    HEADERS = ["Location", "Spool", "Batch", "Weight (kg)", "Tube Colour", "Received", "This series"]
    _GROUP_TINT = QColor("#EEF4EE")

    def __init__(self, yarn_id: int, yarn_name: str, yarn_colour: Optional[str] = None,
                 assigned_spool_ids: Optional[Set[int]] = None, parent=None,
                 on_open_yarn_stock: Optional[Callable[[int, str], None]] = None):
        super().__init__(parent)
        self.setWindowTitle(f"Stock locations - {yarn_name}")
        self.setMinimumWidth(640)
        self.resize(720, 420)
        self._yarn_id = int(yarn_id)
        assigned = assigned_spool_ids or set()

        rows = load_spools_in_stock(yarn_id)
        self.rows = rows

        root = QVBoxLayout(self)
        head = QHBoxLayout()
        sq = QLabel()
        icon = colour_icon(yarn_colour, 14)
        if not icon.isNull():
            sq.setPixmap(icon.pixmap(14, 14))
            sq.setToolTip(colour_tooltip(yarn_colour))
            head.addWidget(sq)
        title = QLabel(f"<b>{_esc(yarn_name)}</b>")
        head.addWidget(title)
        head.addStretch(1)
        root.addLayout(head)

        locs = sorted({(r.get("Location") or "").strip() for r in rows}, key=location_sort_key)
        kg = sum(float(r.get("WeightKg") or 0) for r in rows)
        loc_names = ", ".join(l or "(no location)" for l in locs)
        info = QLabel(
            f"{len(rows)} spool{'s' if len(rows) != 1 else ''} in stock, {kg:.1f} kg, "
            f"in {len(locs)} location{'s' if len(locs) != 1 else ''}: <b>{_esc(loc_names)}</b>"
            if rows else "No spools of this yarn are in stock at the moment.")
        info.setWordWrap(True)
        root.addWidget(info)

        tbl = QTableWidget(len(rows), len(self.HEADERS))
        tbl.setHorizontalHeaderLabels(self.HEADERS)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.setAlternatingRowColors(False)
        bold = QFont()
        bold.setBold(True)

        group, prev_loc = -1, None
        for i, r in enumerate(rows):
            loc = (r.get("Location") or "").strip()
            if loc != prev_loc:
                group += 1
                prev_loc = loc
            sid = int(r.get("ID") or 0)
            is_assigned = sid in assigned
            wt = r.get("WeightKg")
            tube = (r.get("Colour") or "").strip()
            values = [
                loc or "–",
                f"#{sid}",
                str(r.get("Charge") or "–"),
                f"{float(wt):.2f}" if wt is not None else "?",
                tube or "–",
                str(r.get("ReceivedDate") or "")[:10],
                "assigned" if is_assigned else "",
            ]
            for c, v in enumerate(values):
                it = QTableWidgetItem(v)
                if c == 3:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if c == 4 and tube:
                    it.setIcon(tube_colour_icon(tube))
                if is_assigned:
                    it.setFont(bold)
                if group % 2 == 1:
                    it.setBackground(self._GROUP_TINT)
                tbl.setItem(i, c, it)
        tbl.verticalHeader().setDefaultSectionSize(tbl.fontMetrics().height() + 8)
        tbl.resizeColumnsToContents()
        any_assigned = any(int(r.get("ID") or 0) in assigned for r in rows)
        last = len(self.HEADERS) - 1
        tbl.setColumnHidden(last, not any_assigned)
        tbl.horizontalHeader().setSectionResizeMode(last if any_assigned else last - 1,
                                                    QHeaderView.Stretch)
        self.table = tbl
        root.addWidget(tbl, 1)

        if any_assigned:
            hint = QLabel("Bold = spool assigned to this series (Machine Data, row 'Spool').")
            hint.setStyleSheet("color:#666;")
            root.addWidget(hint)

        btns = QHBoxLayout()
        btns.addStretch(1)
        if on_open_yarn_stock is not None and rows:
            b_stock = QPushButton("Open in Yarn Stock")
            b_stock.setToolTip("Opens Yarn Stock at this yarn (batch of the selected spool).")

            def _open():
                sel = tbl.currentRow()
                charge = str(rows[sel].get("Charge") or "") if 0 <= sel < len(rows) else ""
                self.accept()
                on_open_yarn_stock(self._yarn_id, charge)
            b_stock.clicked.connect(_open)
            btns.addWidget(b_stock)
        b_close = QPushButton("Close")
        b_close.clicked.connect(self.reject)
        b_close.setDefault(True)
        btns.addWidget(b_close)
        root.addLayout(btns)


def _esc(s: str) -> str:
    return html.escape(str(s or ""))
