"""dty_schema_panel.py - DTY process schema above the Machine Data table in
Show Experiment (Nutzerwunsch 2026-11-07).

- Drawn from the data of ONE trial (the column of the current cell): one
  lane per ply with its position, LW 0 + pre-intermingling jet only where
  the process or a value needs it, merge onto one position (LW 2, or LW 1
  for "Cotton-like: before heater"), main jet, LW 2.x, set heater, jet 3,
  LW 3, winder. Drawn yarn (FDY/HOY/FOY) bypasses heater and friction,
  elastane comes from its own source at LW 2.
- Click a station -> its rows are highlighted in the table
  (FrozenFirstColumnTable.set_highlight, pure painting); per-ply stations
  frame only that ply's cells. Click a cell -> the schema shows that trial
  and marks the station of the row. Double-click a station -> first value
  of that station becomes the current cell.
- Read-only view: values are changed in the table only, so dirty marks,
  undo, save and the change log stay in one place.

Only on DTY machines (tblmaschine.Maschinentyp = 1) and only when the
tbldtyprocess table exists (db/dty_process.py).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QToolButton, QToolTip, QVBoxLayout, QWidget,
)

from db.machine_data import SINGLE_PLY_TIP as _SINGLE_PLY_TIP
from db import machine_schema as _ms
from ui import dty_stations as ds

_SETTINGS = ("TrippleT", "ShowExperiment")
_KEY_VISIBLE = "dty_schema/visible"

# colours (TrippleT light theme, Heberlein green)
C_LINE = QColor("#2E7D32")
C_LINE_BYPASS = QColor("#1E88E5")
C_LINE_EL = QColor("#8E24AA")
C_STATION = QColor("#FFFFFF")
C_BORDER = QColor("#5F6B5F")
C_EMPTY = QColor("#C8CEC8")
C_HEATER = QColor("#F4A259")
C_COOL = QColor("#9ED0F0")
C_JET = QColor("#43A047")
C_TEXT = QColor("#2B2B2B")
C_MUTED = QColor("#7A847A")
C_SEL = QColor(255, 193, 7, 150)
C_BG = QColor("#F4F6F3")

# station names and value summaries: db/machine_schema.py (shared with the web app)
SHORT = _ms.SHORT
_SUMMARY = _ms.SUMMARY
_JOINED = _ms.JOINED

# ATY stations drawn with a DTY shape (ui/aty_stations.py)
_SHAPE = {"draw": "heater1", "feed": "lw", "jet": "mainjet", "stabilise": "setheater"}


def _mod(profile: Optional[str]):
    """Station module of a schema profile: ui/dty_stations or ui/aty_stations."""
    return _ms.station_module(profile)


from db.machine_data import filled as _filled  # noqa: E402  (shared rule, db/machine_data.py)


# ══════════════════════════════════════════════════════════════════════
# drawing
# ══════════════════════════════════════════════════════════════════════
class DTYSchemaWidget(QWidget):
    """Paints the path of one trial. Data from build_path()."""

    stationClicked = Signal(str, int)        # station, ply index (-1 = trial level / none)
    stationDoubleClicked = Signal(str, int)

    LANE_H = 58
    TOP = 34
    LEFT = 150
    MIN_COL = 74

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: Dict[str, Any] = {}
        self._hits: List[Tuple[QRectF, str, int]] = []
        self._sel: Optional[Tuple[str, int]] = None
        self._tips: Dict[Tuple[str, int], str] = {}  # collected while painting
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    # ── data ─────────────────────────────────────────────────────────
    def set_path(self, data: Dict[str, Any]) -> None:
        self._data = data or {}
        n_lanes = max(1, len(self._data.get("plies") or []))
        h = self.TOP + n_lanes * self.LANE_H + 30
        n_cols = len(self._data.get("stations") or []) or 1
        self.setMinimumWidth(self.LEFT + n_cols * self.MIN_COL + 20)
        self.setFixedHeight(h)
        self.update()

    def set_selected(self, station: Optional[str], ply: int = -1) -> None:
        self._sel = (station, ply) if station else None
        self.update()

    def selected(self) -> Optional[Tuple[str, int]]:
        return self._sel

    # ── geometry ─────────────────────────────────────────────────────
    def _col_x(self) -> Dict[str, float]:
        st = [s for s in (self._data.get("stations") or []) if s != "creel"]
        if not st:
            return {}
        w = max(self.width() - self.LEFT - 20, len(st) * self.MIN_COL)
        step = w / len(st)
        return {s: self.LEFT + step * (i + 0.5) for i, s in enumerate(st)}

    # ── painting ─────────────────────────────────────────────────────
    def paintEvent(self, _ev):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), C_BG)
        self._hits = []
        self._tips = {}
        d = self._data
        if not d:
            p.setPen(C_MUTED)
            p.drawText(self.rect(), Qt.AlignCenter, "Select a trial in the table to see its machine path.")
            p.end()
            return
        xs = self._col_x()
        f = QFont(self.font())
        f.setPointSizeF(max(7.5, f.pointSizeF() - 0.5))
        fb = QFont(f)
        fb.setBold(True)
        fs = QFont(f)
        fs.setPointSizeF(max(7.0, f.pointSizeF() - 1))
        fm_s = QFontMetrics(fs)
        if d.get("profile") == "aty":
            from ui import aty_schema
            aty_schema.paint(self, p, d, f, fb, fs)
            p.end()
            return

        # title + station names
        p.setFont(fb)
        p.setPen(C_TEXT)
        p.drawText(QRectF(8, 4, self.LEFT - 10, 18), Qt.AlignLeft | Qt.AlignVCenter, d.get("title", ""))
        proc = d.get("process") or "(no process)"
        r_proc = QRectF(8, 18, self.LEFT - 10, 14)
        p.setFont(fs)
        p.setPen(C_LINE if d.get("process") else C_MUTED)
        p.drawText(r_proc, Qt.AlignLeft | Qt.AlignVCenter, fm_s.elidedText(proc, Qt.ElideRight, int(r_proc.width())))
        self._hits.append((r_proc, "process", -1))
        p.setFont(f)
        for s, x in xs.items():
            p.setPen(C_MUTED)
            p.drawText(QRectF(x - 45, 8, 90, 16), Qt.AlignCenter, SHORT.get(s, s))

        plies = d.get("plies") or []
        if not plies:
            plies = [{"label": "", "pos": "", "yarn": "", "path": "full", "values": {}, "tips": {},
                      "idx": -1, "into": None, "at": None}]
        order = d.get("order") or list(range(len(plies)))
        lane_y = {k: self.TOP + n * self.LANE_H + 14 for n, k in enumerate(order)}
        keys = list(xs)
        x_end = xs.get("winder", self.width() - 30)
        per_ply = [s for s in xs if s in ds.PER_PLY and s != "elastane"]
        main = d.get("main", order[0] if order else 0)
        if main not in lane_y:
            main = order[0]

        def join_x(station):
            x = xs.get(station)
            if x is None:  # station not drawn (e.g. jet 3 hidden): next drawn one
                later = [k for k in keys if ds._pos(k) > ds._pos(station)]
                x = xs[later[0]] if later else x_end
            return x

        for k in order:
            pl = plies[k]
            y = lane_y[k]
            kind = pl["path"]
            colour = {"bypass": C_LINE_BYPASS, "elastane": C_LINE_EL}.get(kind, C_LINE)
            pen = QPen(colour, 2.6 if k == main else 2.2)
            pen.setStyle({"bypass": Qt.DashLine, "elastane": Qt.DotLine}.get(kind, Qt.SolidLine))
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            # where the lane starts
            if kind == "elastane":
                xa = join_x(pl.get("at") or "lw2")
                before = [kk for kk in keys if xs[kk] < xa - 1]
                x0 = xs[before[-2]] if len(before) >= 2 else (xs[before[-1]] if before else self.LEFT)
            else:
                x0 = self.LEFT - 8
            path = QPainterPath(QPointF(x0, y))
            if k == main or pl.get("into") is None:
                path.lineTo(QPointF(x_end + 18, y))
                x_stop = x_end + 18
            else:
                xa = join_x(pl.get("at") or "lw2")
                xr = xa - self.MIN_COL * 0.55   # rise left of the station's value text
                yt = lane_y.get(pl["into"], lane_y[main])
                path.lineTo(QPointF(xr - 12, y))
                path.cubicTo(QPointF(xr, y), QPointF(xr, yt), QPointF(xa - 16, yt))
                x_stop = xr - 6
            p.drawPath(path)
            # label (creel / separate source)
            if kind == "elastane":
                left = max(8.0, x0 - 2.4 * self.MIN_COL)
                r_lbl = QRectF(left, y - 15, x0 - left - 4, 30)
                shown = {"label": "Elastane" if pl.get("is_elastane") else (pl["label"] + " · own source"),
                         "pos": "",
                         "yarn": " · ".join(v for v in (pl["values"].get("elastane"), pl.get("yarn")) if v)}
                self._draw_creel(p, r_lbl, shown, fb, fs, colour, selected=self._is_sel("elastane", pl["idx"]))
                self._hits.append((r_lbl, "elastane", pl["idx"]))
                tip = "\n".join(t for t in (pl["tips"].get("creel"), pl["tips"].get("lw1"),
                                             pl["tips"].get("elastane")) if t)
                if tip:
                    self._tips[("elastane", pl["idx"])] = tip
                continue
            r_creel = QRectF(8, y - 15, self.LEFT - 18, 30)
            self._draw_creel(p, r_creel, pl, fb, fs, colour, selected=self._is_sel("creel", pl["idx"]))
            self._hits.append((r_creel, "creel", pl["idx"]))
            # the ply's own stations up to its merge point
            for st in per_ply:
                x = xs[st]
                if x >= x_stop:
                    continue
                if kind == "bypass" and st in ("heater1", "cooling", "friction", "lw0", "prejet"):
                    continue
                self._station(p, st, x, y, pl["idx"], pl["values"].get(st), pl["tips"].get(st), fs, fm_s)

        # trial-level stations on the main line
        y_main = lane_y[main]
        for st in xs:
            if st in ds.PER_PLY:
                continue
            self._station(p, st, xs[st], y_main, -1, d["values"].get(st), d["tips"].get(st), fs, fm_s)
        p.end()

    def _is_sel(self, station: str, ply: int) -> bool:
        if not self._sel or self._sel[0] != station:
            return False
        return self._sel[1] in (-1, ply) or ply == -1

    def _draw_creel(self, p, r, pl, fb, fs, colour, selected=False):
        if selected:
            p.setPen(Qt.NoPen)
            p.setBrush(C_SEL)
            p.drawRoundedRect(r.adjusted(-3, -3, 3, 3), 6, 6)
        p.setPen(QPen(colour, 1.6))
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(r.left(), r.center().y() - 9, 18, 18))
        p.drawEllipse(QRectF(r.left() + 6, r.center().y() - 3, 6, 6))
        p.setPen(C_TEXT)
        p.setFont(fb)
        top = f"{pl['label']}" + (f" · Pos {pl['pos']}" if pl.get("pos") else "")
        p.drawText(QRectF(r.left() + 24, r.top(), r.width() - 24, 15), Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(fb).elidedText(top, Qt.ElideRight, int(r.width() - 24)))
        p.setFont(fs)
        p.setPen(C_MUTED)
        p.drawText(QRectF(r.left() + 24, r.top() + 15, r.width() - 24, 14), Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(fs).elidedText(pl.get("yarn") or "", Qt.ElideRight, int(r.width() - 24)))

    def _station(self, p, s, x, y, ply, value, tip, fs, fm_s):
        empty = not value
        sel = self._is_sel(s, ply)
        r = QRectF(x - 16, y - 11, 32, 22)
        if sel:
            p.setPen(Qt.NoPen)
            p.setBrush(C_SEL)
            p.drawRoundedRect(r.adjusted(-6, -6, 6, 20), 6, 6)
        border = C_EMPTY if empty else C_BORDER
        p.setPen(QPen(border, 1.4))
        shape = _SHAPE.get(s, s) if self._data.get("profile") == "aty" else s
        if shape == "wetting":
            p.setBrush(QColor("#E3F1FB") if empty else QColor("#9ED0F0"))
            p.drawRoundedRect(QRectF(x - 14, y - 9, 28, 18), 4, 4)
            p.setPen(QPen(QColor("#2386C8"), 1.2))
            for k in (-6, 0, 6):
                p.drawLine(QPointF(x + k, y - 15), QPointF(x + k, y - 10))
        elif shape.startswith("lw"):
            p.setBrush(QColor("#FFFFFF") if empty else QColor("#E8F5E9"))
            p.drawEllipse(QRectF(x - 13, y - 13, 12, 12))
            p.drawEllipse(QRectF(x + 1, y + 1, 12, 12))
        elif shape in ("heater1", "setheater"):
            p.setBrush(QColor("#FBE3CC") if empty else C_HEATER)
            p.drawRoundedRect(QRectF(x - 18, y - 6, 36, 12), 3, 3)
        elif shape == "cooling":
            p.setBrush(C_COOL)
            p.drawRoundedRect(QRectF(x - 16, y - 4, 32, 8), 2, 2)
        elif shape == "friction":
            p.setBrush(QColor("#FFFFFF") if empty else QColor("#E0E0E0"))
            for k in (-8, 0, 8):
                p.drawEllipse(QRectF(x + k - 4, y - 10, 8, 20))
        elif shape in ("mainjet", "prejet", "jet3"):
            p.setBrush(QColor("#E8F5E9") if empty else C_JET)
            p.drawRoundedRect(QRectF(x - 11, y - 9, 22, 18), 4, 4)
            p.setPen(QPen(border, 1.2))
            p.drawLine(QPointF(x, y - 9), QPointF(x, y - 15))
            p.drawLine(QPointF(x - 3, y - 13), QPointF(x, y - 9))
            p.drawLine(QPointF(x + 3, y - 13), QPointF(x, y - 9))
        elif shape == "winder":
            p.setBrush(QColor("#FFFFFF"))
            p.drawEllipse(QRectF(x - 11, y - 11, 22, 22))
            p.drawEllipse(QRectF(x - 4, y - 4, 8, 8))
        else:
            p.setBrush(QColor("#FFFFFF"))
            p.drawRect(r)
        if value:
            w = self.MIN_COL + 6
            lines = str(value).split("\n")
            for n, line in enumerate(lines[:2]):
                f_line = QFont(fs)
                f_line.setBold(n == 0 and len(lines) > 1)
                p.setFont(f_line)
                p.setPen(C_TEXT if n == 0 else C_MUTED)
                p.drawText(QRectF(x - w / 2, y + 12 + n * 13, w, 14), Qt.AlignCenter,
                           QFontMetrics(f_line).elidedText(line, Qt.ElideRight, int(w)))
        self._hits.append((QRectF(x - self.MIN_COL / 2 + 2, y - 16, self.MIN_COL - 4, 52), s, ply))
        if tip:
            self._tips[(s, ply)] = tip

    def _hit(self, pos) -> Optional[Tuple[str, int]]:
        for r, s, ply in reversed(self._hits):
            if r.contains(QPointF(pos)):
                return s, ply
        return None

    def mousePressEvent(self, ev):  # noqa: N802
        if ev.button() != Qt.LeftButton:
            return super().mousePressEvent(ev)
        h = self._hit(ev.position().toPoint() if hasattr(ev, "position") else ev.pos())
        if h is None:
            self.stationClicked.emit("", -1)
        else:
            self.stationClicked.emit(h[0], h[1])

    def mouseDoubleClickEvent(self, ev):  # noqa: N802
        h = self._hit(ev.position().toPoint() if hasattr(ev, "position") else ev.pos())
        if h is not None:
            self.stationDoubleClicked.emit(h[0], h[1])

    def contextMenuEvent(self, ev):  # noqa: N802
        """Right-click on a station: the Knowledge Base page at this station (ui/kb_links.py)."""
        h = self._hit(ev.pos())
        profile = self._data.get("profile")
        target = kb_target(h[0], profile) if h else None
        if not target:
            return super().contextMenuEvent(ev)
        from PySide6.QtWidgets import QMenu
        from ui import kb_links
        menu = QMenu(self)
        kb_links.add_action(menu, self, target, f"{profile or 'dty'}_schema")
        menu.exec(ev.globalPos())

    def mouseMoveEvent(self, ev):  # noqa: N802
        pos = ev.position().toPoint() if hasattr(ev, "position") else ev.pos()
        h = self._hit(pos)
        self.setCursor(Qt.PointingHandCursor if h else Qt.ArrowCursor)
        if h:
            profile = self._data.get("profile")
            name = _mod(profile).STATION_LABEL.get(h[0], h[0])
            tip = self._data.get("tips", {}).get(h[0]) if h[1] == -1 else None
            if tip is None:
                tip = self._tips.get(h)
            QToolTip.showText(ev.globalPosition().toPoint() if hasattr(ev, "globalPosition") else ev.globalPos(),
                              f"<b>{name}</b><br>" + (tip or "no values").replace("\n", "<br>")
                              + "<br><i>Click: highlight rows in the table</i>"
                              + ("<br><i>Right-click: learn more in the Knowledge Base</i>"
                                 if kb_target(h[0], profile) else ""),
                              self)
        else:
            QToolTip.hideText()


# ══════════════════════════════════════════════════════════════════════
# data of one trial from the Machine Data model
# ══════════════════════════════════════════════════════════════════════
def _display(model, r: int, c: int) -> str:
    try:
        v = model.index(model._n_hdr + r, c + 1).data(Qt.DisplayRole)
    except Exception:
        v = model.get_cell_value(r, c)
    return "" if v is None else str(v).strip()


class _ModelSource:
    """Cells of the Machine Data model for db/machine_schema.py."""

    def __init__(self, screen):
        self.model = getattr(screen, "model_machine", None)
        self.specs = getattr(screen, "_machine_col_specs", None) or []
        self.keys = list(getattr(screen, "_machine_row_keys", None) or [])
        self.titles = list(getattr(self.model, "_row_titles", None) or [])
        self.hidden = getattr(screen, "_process_hidden_rows", set())

    def display(self, r: int, c: int) -> str:
        return _display(self.model, r, c)

    def value(self, r: int, c: int):
        return self.model.get_cell_value(r, c)


def build_path(screen, col: int) -> Dict[str, Any]:
    """Path data of the trial in model column `col` (0-based data column) -
    rules in db/machine_schema.build_dty_path (shared with the web app)."""
    src = _ModelSource(screen)
    if src.model is None or not src.specs or not (0 <= col < len(src.specs)):
        return {}
    return _ms.build_dty_path(src, col, _yarn_types(screen, src.specs))


_num = _ms.num
_speed_text = _ms.speed_text
_short = _ms.short
_int = _ms.as_int
_lane_order = _ms.lane_order


def _cell(model, keys, key, col):
    return model.get_cell_value(keys.index(key), col) if key in keys else None


def _yarn_types(screen, specs) -> Dict[int, Any]:
    out = _ms.load_yarn_types(specs, getattr(screen, "_dty_yarn_types", None))
    screen._dty_yarn_types = out
    return out


# ══════════════════════════════════════════════════════════════════════
# wiring into ShowExperimentScreen
# ══════════════════════════════════════════════════════════════════════
def _is_active(screen) -> bool:
    from db import machine_data as _md
    return _md.is_dty_active(getattr(screen, "_machine_cache", None) or {},
                             getattr(screen, "_machine_row_keys", None) or [])


def _profile(screen) -> Optional[str]:
    """'dty' / 'aty' / None - which schema the Machine Data of this series gets
    (db/machine_schema.profile)."""
    if _is_active(screen):
        return "dty"
    return _ms.profile(getattr(screen, "_machine_cache", None),
                       getattr(screen, "_machine_row_keys", None) or [])


def install(screen, layout, toolbar_layout) -> None:
    """Creates the (hidden) panel below the Machine Data toolbar and the
    "Schema" toggle in the toolbar. Shown by refresh() on DTY machines."""
    screen.btn_dty_schema = QToolButton()
    screen.btn_dty_schema.setText("Schema")
    screen.btn_dty_schema.setCheckable(True)
    screen.btn_dty_schema.setToolTip("Show the machine path of the selected trial.\n"
                                     "Click a station to highlight its rows in the table.")
    screen.btn_dty_schema.setStyleSheet(
        "QToolButton{border:1px solid #b5d7b5;background:#ffffff;padding:3px 10px;border-radius:4px;}"
        "QToolButton:checked{background:#e3f1e3;border-color:#2E7D32;color:#1b5e20;font-weight:600;}")
    try:
        vis = QSettings(*_SETTINGS).value(_KEY_VISIBLE, True)
        vis = vis if isinstance(vis, bool) else str(vis).lower() in ("1", "true")
    except Exception:
        vis = True
    screen.btn_dty_schema.setChecked(vis)
    screen.btn_dty_schema.setVisible(False)
    screen.btn_dty_schema.toggled.connect(lambda on: _on_toggle(screen, on))
    toolbar_layout.addWidget(screen.btn_dty_schema)

    panel = QWidget()
    lay = QVBoxLayout(panel)
    lay.setContentsMargins(0, 0, 0, 6)
    lay.setSpacing(2)
    screen.dty_schema = DTYSchemaWidget()
    scroll = QScrollArea()
    scroll.setWidget(screen.dty_schema)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.StyledPanel)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    screen._dty_schema_scroll = scroll
    lay.addWidget(scroll)
    hint_row = QHBoxLayout()
    hint_row.setContentsMargins(0, 0, 0, 0)
    screen.dty_schema_hint = QLabel("")
    screen.dty_schema_hint.setStyleSheet("color:#7A847A;font-size:11px;")
    hint_row.addWidget(screen.dty_schema_hint)
    # link to the Knowledge Base page of the selected station (popup, ui/kb_links.py)
    screen.dty_schema_kb = QLabel("")
    screen.dty_schema_kb.setStyleSheet("font-size:11px;")
    screen.dty_schema_kb.setVisible(False)
    screen.dty_schema_kb.linkActivated.connect(lambda _href: _open_kb(screen))
    hint_row.addSpacing(10)
    hint_row.addWidget(screen.dty_schema_kb)
    hint_row.addStretch(1)
    lay.addLayout(hint_row)
    panel.setVisible(False)
    screen.dty_schema_panel = panel
    layout.addWidget(panel)

    screen.dty_schema.stationClicked.connect(lambda s, ply: _on_station(screen, s, ply))
    screen.dty_schema.stationDoubleClicked.connect(lambda s, ply: _on_station_dbl(screen, s, ply))
    screen._dty_refresh_timer = QTimer(panel)
    screen._dty_refresh_timer.setSingleShot(True)
    screen._dty_refresh_timer.setInterval(120)
    screen._dty_refresh_timer.timeout.connect(lambda: _redraw(screen))


def _on_toggle(screen, on: bool) -> None:
    try:
        QSettings(*_SETTINGS).setValue(_KEY_VISIBLE, bool(on))
    except Exception:
        pass
    refresh(screen)
    if on:
        try:
            from db.usage_log import log_usage_event
            log_usage_event("feature", f"{_profile(screen) or 'dty'}_schema_show")
        except Exception:
            pass


def update_process_rows(screen) -> None:
    """screen._process_hidden_rows = pre-jet / jet 3 rows no trial needs
    (applied by machine_row_visibility.apply); merge cells of single-ply
    trials lose their binding. Rules: db/machine_data.process_rules."""
    from db import machine_data as _md
    model = getattr(screen, "model_machine", None)
    keys = list(getattr(screen, "_machine_row_keys", None) or [])
    if model is None:
        screen._process_hidden_rows = set()
        return
    hidden, locked = _md.process_rules(
        getattr(screen, "_machine_cache", None) or {}, keys,
        getattr(screen, "_machine_col_specs", None) or [], len(model._col_titles), model.get_cell_value)
    for r, c in locked:
        model._binding[r][c] = None
        model._cell_tooltips[(r, c)] = SINGLE_PLY_TIP
    screen._process_hidden_rows = hidden


SINGLE_PLY_TIP = _SINGLE_PLY_TIP


def refresh(screen) -> None:
    """After (re)building Machine Data: show/hide the panel, connect the new
    model/selection, draw the current trial."""
    if not hasattr(screen, "dty_schema_panel"):
        return
    active = _profile(screen) is not None
    screen.btn_dty_schema.setVisible(active)
    show = active and screen.btn_dty_schema.isChecked()
    screen.dty_schema_panel.setVisible(show)
    tbl = getattr(screen, "tbl_machine", None)
    model = getattr(screen, "model_machine", None)
    if tbl is not None:
        tbl.set_highlight((), scroll=False)
    screen.dty_schema.set_selected(None)
    if not active or model is None:
        return
    if getattr(screen, "_dty_wired_model", None) is not model:
        screen._dty_wired_model = model
        model.dataChanged.connect(lambda tl, br, *_: _on_data_changed(screen, tl, br))
        sel = tbl.selectionModel()
        if sel is not None:
            sel.currentChanged.connect(lambda cur, _prev: _on_current(screen, cur))
    _redraw(screen)


def _current_col(screen) -> int:
    specs = getattr(screen, "_machine_col_specs", None) or []
    tid = getattr(screen, "_dty_schema_trial", None)
    for i, cs in enumerate(specs):
        if cs["trial_id"] == tid:
            return i
    return 0


def _redraw(screen) -> None:
    if not getattr(screen, "dty_schema_panel", None) or not screen.dty_schema_panel.isVisible():
        return
    col = _current_col(screen)
    if _profile(screen) == "aty":
        from ui import aty_schema
        data = aty_schema.build_path(screen, col)
    else:
        data = build_path(screen, col)
    if data:
        screen._dty_schema_trial = data["trial_id"]
    screen.dty_schema._tips = {}
    screen.dty_schema.set_path(data)
    sb = screen._dty_schema_scroll.horizontalScrollBar().sizeHint().height()
    screen._dty_schema_scroll.setFixedHeight(screen.dty_schema.height() + sb + 4)
    warnings = (data or {}).get("warnings") or []
    if warnings:
        screen.dty_schema_hint.setStyleSheet("color:#B23B00;font-size:11px;")
        prefix = "Note: " if data.get("profile") == "aty" else "Check the merge fields: "
        screen.dty_schema_hint.setText(prefix + " · ".join(warnings))
    else:
        screen.dty_schema_hint.setStyleSheet("color:#7A847A;font-size:11px;")
        ply_hint = "its rows" if (data or {}).get("profile") == "aty" else "its route and merge rows"
        screen.dty_schema_hint.setText(
            f"Click a station to highlight its rows · click a ply name for {ply_hint} · "
            "double-click to jump to the first value · the schema follows the trial of the current cell")
    _update_kb_link(screen)


def _on_data_changed(screen, tl, br) -> None:
    keys = list(getattr(screen, "_machine_row_keys", None) or [])
    model = getattr(screen, "model_machine", None)
    if model is None:
        return
    if "dtyprocessid" in keys:
        pr = model._n_hdr + keys.index("dtyprocessid")
        if tl.row() <= pr <= br.row():
            before = set(getattr(screen, "_process_hidden_rows", set()))
            update_process_rows(screen)
            if before != screen._process_hidden_rows:
                from ui import machine_row_visibility as _mrv
                _mrv.apply(screen)
    if hasattr(screen, "_dty_refresh_timer"):
        screen._dty_refresh_timer.start()


def _on_current(screen, cur) -> None:
    if not cur.isValid() or not getattr(screen, "dty_schema_panel", None) \
            or not screen.dty_schema_panel.isVisible():
        return
    model = screen.model_machine
    c = cur.column() - 1
    r = cur.row() - model._n_hdr
    specs = getattr(screen, "_machine_col_specs", None) or []
    if 0 <= c < len(specs) and specs[c]["trial_id"] != getattr(screen, "_dty_schema_trial", None):
        screen._dty_schema_trial = specs[c]["trial_id"]
        _redraw(screen)
    keys = list(getattr(screen, "_machine_row_keys", None) or [])
    mod = _mod(_profile(screen))
    st = mod.station_of(keys[r]) if 0 <= r < len(keys) else None
    if st:
        screen.dty_schema.set_selected(st, c if st in mod.PER_PLY else -1)
    else:
        screen.dty_schema.set_selected(None)


def _station_target(screen, station: str, ply: int) -> Tuple[List[int], List[int]]:
    """(model rows, model columns) to highlight for a station."""
    model = screen.model_machine
    keys = list(getattr(screen, "_machine_row_keys", None) or [])
    mod = _mod(_profile(screen))
    rows = [model._n_hdr + r for r in _ms.station_rows(keys, station, _profile(screen))]
    specs = getattr(screen, "_machine_col_specs", None) or []
    tid = getattr(screen, "_dty_schema_trial", None)
    if station in mod.PER_PLY and ply >= 0:
        cols = [ply + 1]
    else:
        cols = [i + 1 for i, cs in enumerate(specs) if cs["trial_id"] == tid]
    return rows, cols


def kb_target(station: Optional[str], profile: Optional[str] = None):
    """Knowledge Base target of a schema station, or None (e.g. elastane feed)."""
    return _ms.kb_target(station, profile)


def _update_kb_link(screen) -> None:
    sel = screen.dty_schema.selected()
    target = kb_target(sel[0], _profile(screen)) if sel else None
    screen._dty_kb_target = target
    if target:
        screen.dty_schema_kb.setText('<a href="kb" style="color:#1F7A3A;">Learn more in Knowledge Base…</a>')
    screen.dty_schema_kb.setVisible(bool(target))


def _open_kb(screen) -> None:
    target = getattr(screen, "_dty_kb_target", None)
    if target:
        from ui import kb_links
        kb_links.open_target(screen, target, f"{_profile(screen) or 'dty'}_schema")


def _on_station(screen, station: str, ply: int) -> None:
    tbl = screen.tbl_machine
    if not station or screen.dty_schema.selected() == (station, ply):
        screen.dty_schema.set_selected(None)
        tbl.set_highlight((), scroll=False)
        _update_kb_link(screen)
        return
    screen.dty_schema.set_selected(station, ply)
    _update_kb_link(screen)
    rows, cols = _station_target(screen, station, ply)
    visible = [r for r in rows if not tbl.right.isRowHidden(r)]
    tbl.set_highlight(rows, cols)
    label = _mod(_profile(screen)).STATION_LABEL.get(station, station)
    if not rows:
        screen.dty_schema_hint.setText(f"{label}: this machine has no fields for it.")
    elif not visible:
        screen.dty_schema_hint.setText(f"{label}: its rows are hidden - use 'rows hidden' to show them.")
    else:
        screen.dty_schema_hint.setText(f"{label}: {len(visible)} row(s) highlighted · click again to clear")


def _on_station_dbl(screen, station: str, ply: int) -> None:
    rows, cols = _station_target(screen, station, ply)
    tbl = screen.tbl_machine
    rows = [r for r in rows if not tbl.right.isRowHidden(r)]
    if not rows or not cols:
        return
    idx = screen.model_machine.index(rows[0], cols[0])
    tbl.setCurrentIndex(idx)
    tbl.right.scrollTo(idx)
    tbl.setFocus()
