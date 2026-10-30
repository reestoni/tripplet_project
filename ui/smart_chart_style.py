# ui/smart_chart_style.py
"""Smart Chart look controls (ui/screen_smart_chart.py): small chart-type
icons, palette swatch icons and the "Colours…" dialog (own colour per value).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import (
    QColorDialog, QDialog, QDialogButtonBox, QGridLayout, QLabel, QMenu, QPushButton, QScrollArea, QVBoxLayout,
    QWidget,
)

from db.trial_explorer import group_tree
from ui.smart_chart_figure import PALETTES

_INK = QColor("#2F4A37")
_C1, _C2 = QColor("#2F6DB5"), QColor("#D9822B")


def chart_icon(kind: str, size: int = 22) -> QIcon:
    s = size * 2
    pm = QPixmap(s, s)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(QPen(QColor("#9AA59C"), 2))
    p.drawLine(4, s - 4, s - 2, s - 4)
    p.drawLine(4, 2, 4, s - 4)
    p.setPen(Qt.NoPen)
    if kind in ("points", "trend"):
        for i, (x, y) in enumerate(((12, 30), (18, 26), (24, 24), (30, 17), (36, 12), (16, 34), (28, 28), (38, 20))):
            p.setBrush(_C1 if i < 5 else _C2)
            p.drawEllipse(QPointF(x, y), 3, 3)
        if kind == "trend":
            p.setPen(QPen(_INK, 2.5, Qt.DashLine))
            p.drawLine(8, 36, 42, 10)
    elif kind == "line":
        p.setPen(QPen(_C1, 3))
        pts = [QPointF(10, 32), QPointF(20, 22), QPointF(30, 25), QPointF(40, 12)]
        for a, b in zip(pts, pts[1:]):
            p.drawLine(a, b)
        p.setPen(Qt.NoPen)
        p.setBrush(_C1)
        for q in pts:
            p.drawRect(QRectF(q.x() - 3, q.y() - 3, 6, 6))
    elif kind == "bar":
        for i, hgt in enumerate((18, 28, 22, 34)):
            p.setBrush(_C1 if i % 2 == 0 else _C2)
            p.drawRect(QRectF(9 + i * 9, s - 4 - hgt, 7, hgt))
    elif kind == "box":
        for i, (lo, q1, q3, hi) in enumerate(((30, 24, 16, 8), (36, 30, 22, 14))):
            x = 12 + i * 16
            p.setPen(QPen(_C1 if i == 0 else _C2, 2))
            p.drawLine(x + 5, lo, x + 5, hi)
            p.setBrush(QColor("#FFFFFF"))
            p.drawRect(QRectF(x, q3, 10, q1 - q3))
            p.drawLine(x, (q1 + q3) / 2, x + 10, (q1 + q3) / 2)
    elif kind == "violin":
        for i, cx in enumerate((17, 33)):
            path = QPainterPath(QPointF(cx, 6))
            path.cubicTo(QPointF(cx + 9, 16), QPointF(cx + 2, 30), QPointF(cx, 38))
            path.cubicTo(QPointF(cx - 2, 30), QPointF(cx - 9, 16), QPointF(cx, 6))
            p.setBrush(_C1 if i == 0 else _C2)
            p.drawPath(path)
    elif kind == "hist":
        for i, hgt in enumerate((6, 14, 26, 34, 24, 12, 5)):
            p.setBrush(_C1)
            p.drawRect(QRectF(7 + i * 5.5, s - 4 - hgt, 5, hgt))
    elif kind == "density":
        for r, col in ((16, "#DCEFD9"), (11, "#8CC63F"), (6, "#1F7A3A")):
            p.setBrush(QColor(col))
            p.drawEllipse(QPointF(26, 22), r * 1.3, r)
    p.end()
    return QIcon(pm)


def palette_icon(key: str) -> QIcon:
    cols = PALETTES[key]["colours"][:5]
    pm = QPixmap(60, 14)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    for i, c in enumerate(cols):
        p.fillRect(QRectF(i * 12, 0, 11, 14), QColor(c))
    p.end()
    return QIcon(pm)


def _swatch_style(hexc: str) -> str:
    return (f"QPushButton{{background:{hexc};border:1px solid #7A7A7A;border-radius:4px;min-width:56px;"
            "min-height:24px;}QPushButton:hover{border:2px solid #1C2321;}")


class ColoursDialog(QDialog):
    """One colour button per value currently in the chart. Returns the map of
    changed colours (value -> #hex); "Reset" goes back to the palette."""

    def __init__(self, groups: List[Tuple[str, str]], defaults: Dict[str, str],
                 current: Optional[Dict[str, str]] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Colours")
        self.setMinimumWidth(380)
        self.result_map: Dict[str, str] = dict(current or {})
        self._palette = {lab: defaults.get(lab, hexc) for lab, hexc in groups}
        v = QVBoxLayout(self)
        hint = QLabel("Click a colour to change it. Your colours are kept in a saved view.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#5A6460;")
        v.addWidget(hint)
        host = QWidget()
        grid = QGridLayout(host)
        grid.setColumnStretch(0, 1)
        self._buttons: Dict[str, QPushButton] = {}
        for r, (lab, hexc) in enumerate(groups):
            grid.addWidget(QLabel(lab), r, 0)
            b = QPushButton()
            b.setToolTip(f"Change the colour of {lab}")
            b.setStyleSheet(_swatch_style(self.result_map.get(lab, hexc)))
            b.clicked.connect(lambda _=False, l=lab: self._pick(l))
            grid.addWidget(b, r, 1)
            self._buttons[lab] = b
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(host)
        v.addWidget(sc, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Reset)
        bb.button(QDialogButtonBox.Reset).setText("Reset to palette")
        bb.button(QDialogButtonBox.Reset).clicked.connect(self._reset)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _pick(self, lab: str) -> None:
        start = QColor(self.result_map.get(lab, self._palette.get(lab, "#2F6DB5")))
        c = QColorDialog.getColor(start, self, f"Colour of {lab}")
        if not c.isValid():
            return
        self.result_map[lab] = c.name().upper()
        self._buttons[lab].setStyleSheet(_swatch_style(self.result_map[lab]))

    def _reset(self) -> None:
        for lab in self._buttons:
            self.result_map.pop(lab, None)
            self._buttons[lab].setStyleSheet(_swatch_style(self._palette[lab]))


class FieldPicker(QPushButton):
    """Button + menu to choose a field: one sub-menu per group (Yarn, Jet,
    Machine, Lab, General), so the long list stays folded (Nutzerwunsch
    2026-10-30). API like the combo boxes it replaces: currentData(),
    set_key(), signal `changed`."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._key = ""
        self._labels = {}
        self._none_label = None
        self.setMinimumWidth(170)
        self.setMaximumWidth(280)
        self.setStyleSheet("QPushButton{background:#FFFFFF;color:#1C2321;border:1px solid #C9D1C8;"
                           "border-radius:4px;padding:5px 8px;text-align:left;}"
                           "QPushButton:hover{border-color:#1F7A3A;}QPushButton:disabled{color:#9AA59C;}")
        self._menu = QMenu(self)
        self.setMenu(self._menu)

    def set_fields(self, fields, kinds, none_label=None) -> None:
        self._menu.clear()
        self._labels = {}
        self._none_label = none_label
        grp = QActionGroup(self)
        if none_label:
            a = self._menu.addAction(none_label)
            a.setCheckable(True)
            a.setData("")
            grp.addAction(a)
            self._labels[""] = none_label
            self._menu.addSeparator()
        def add(menu, fs):
            for f in fs:
                a = menu.addAction(f.label)
                a.setCheckable(True)
                a.setData(f.key)
                grp.addAction(a)
                self._labels[f.key] = f.label

        for top, subs in group_tree(fields):
            own = [f for f in fields if f.group == top and f.kind in kinds]
            parts = [(g, [f for f in fields if f.group == g and f.kind in kinds]) for g in subs]
            parts = [(g, fs) for g, fs in parts if fs]
            n = len(own) + sum(len(fs) for _g, fs in parts)
            if not n:
                continue
            sub = self._menu.addMenu(f"{top}  ({n})")
            add(sub, own)
            for g, fs in parts:
                add(sub.addMenu(f"{g}  ({len(fs)})"), fs)
        grp.triggered.connect(lambda act: self.set_key(act.data(), emit=True))
        self._group = grp
        self.set_key(self._key if self._key in self._labels else next(iter(self._labels), ""))

    def keys(self):
        return list(self._labels)

    def currentData(self):  # noqa: N802 - same name as QComboBox
        return self._key

    def set_key(self, key, emit: bool = False) -> None:
        key = key if key in self._labels else ("" if self._none_label else next(iter(self._labels), ""))
        changed = key != self._key
        self._key = key
        self.setText(self._labels.get(key, ""))
        self.setToolTip(self._labels.get(key, ""))
        for a in self._group.actions() if hasattr(self, "_group") else []:
            a.setChecked(a.data() == key)
        if emit and changed and not self.signalsBlocked():
            self.changed.emit()
