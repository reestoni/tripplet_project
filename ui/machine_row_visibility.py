"""machine_row_visibility.py - hide single rows in Show Experiment's Machine
Data table, Nutzerwunsch 2026-10-15 ("etwas crowded").

- Right-click a parameter name -> "Hide row" (or "Hide N rows" when several
  parameter names are selected).
- Where rows are hidden, a blue line is drawn on the parameter name of the
  next visible row (or at the bottom of the last one). Tooltip names the
  hidden rows, a click on the line shows them again. Red line if a hidden
  row has a highlighted (red/orange) cell.
- Toolbar button "N rows hidden" -> "Show all rows" or single rows.
- Light/dark stripes are counted over the visible rows only
  (PivotEditModel.set_hidden_rows).
- Remembered per user and machine (QSettings, by row title) - pure view,
  data, saving, copy and report are not affected.

The Custom Group row keeps its own toggle; apply() handles it together with
the user's hidden rows so the stripes stay right.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QEvent, QObject, QSettings, Qt
from PySide6.QtGui import QColor, QCursor, QPen
from PySide6.QtWidgets import QMenu, QStyledItemDelegate, QToolTip

import app_meta

_LINE_BLUE = QColor("#3d7fd6")
_LINE_RED = QColor("#CC0000")
_CLICK_ZONE = 6  # px around the line that count as a click on it


# ── persistence ──────────────────────────────────────────────────────────
def _settings_key(screen) -> Optional[str]:
    machine_id = (getattr(screen, "_machine_cache", None) or {}).get("machine_id")
    if not machine_id:
        return None
    user = app_meta.current_user or {}
    who = user.get("username") or user.get("id") or "default"
    return f"hidden_rows/{who}/machine_{machine_id}"


def load_hidden_titles(screen) -> List[str]:
    key = _settings_key(screen)
    if not key:
        return []
    try:
        val = QSettings("TrippleT", "ShowExperiment").value(key, [])
    except Exception:
        return []
    if isinstance(val, str):
        val = [val] if val else []
    return [str(v) for v in (val or [])]


def _save_hidden_titles(screen, titles: List[str]) -> None:
    key = _settings_key(screen)
    if not key:
        return
    try:
        QSettings("TrippleT", "ShowExperiment").setValue(key, list(titles))
    except Exception:
        pass


# ── state ────────────────────────────────────────────────────────────────
def _custom_group_row(screen) -> Optional[int]:
    return getattr(screen, "_custom_group_row_idx", None)


def user_hidden_rows(screen) -> List[int]:
    """Data rows (0-based) hidden by the user in the current model."""
    model = getattr(screen, "model_machine", None)
    if model is None:
        return []
    hidden = set(load_hidden_titles(screen))
    cg = _custom_group_row(screen)
    return [dr for dr, t in enumerate(model._row_titles) if t in hidden and dr != cg]


def compute_markers(n_rows: int, user_hidden, other_hidden) -> Dict[int, Tuple[str, List[int]]]:
    """{visible data row: ("top"|"bottom", [hidden rows])} - a hidden block
    is shown on the next visible row, a block at the end on the last one."""
    markers: Dict[int, Tuple[str, List[int]]] = {}
    pending: List[int] = []
    last_visible = None
    for dr in range(n_rows):
        if dr in user_hidden:
            pending.append(dr)
        elif dr in other_hidden:
            continue
        else:
            if pending:
                markers[dr] = ("top", pending)
                pending = []
            last_visible = dr
    if pending and last_visible is not None:
        markers[last_visible] = ("bottom", pending)
    return markers


def apply(screen) -> None:
    """Hides the user's rows + (if switched off) the Custom Group row,
    updates stripes, markers and the toolbar button."""
    model = getattr(screen, "model_machine", None)
    tbl = getattr(screen, "tbl_machine", None)
    if model is None or tbl is None:
        return
    n_hdr = getattr(model, "_n_hdr", 0)
    n_rows = len(model._row_titles)
    user_hidden = set(user_hidden_rows(screen))
    other_hidden = set()
    cg = _custom_group_row(screen)
    if cg is not None and 0 <= cg < n_rows and not getattr(screen, "_custom_group_visible", False):
        other_hidden.add(cg)
    # DTY process: pre-jet / jet 3 rows no trial needs (ui/dty_schema_panel.py)
    other_hidden |= {r for r in getattr(screen, "_process_hidden_rows", set()) if 0 <= r < n_rows}
    all_hidden = user_hidden | other_hidden
    for dr in range(n_rows):
        tbl.left.setRowHidden(n_hdr + dr, dr in all_hidden)
        tbl.right.setRowHidden(n_hdr + dr, dr in all_hidden)
    model.set_hidden_rows(all_hidden)
    screen._machine_row_markers = compute_markers(n_rows, user_hidden, other_hidden)
    _update_button(screen, sorted(user_hidden))
    try:
        tbl.left.viewport().update()
    except Exception:
        pass


def hide_rows(screen, rows) -> None:
    model = screen.model_machine
    cg = _custom_group_row(screen)
    titles = load_hidden_titles(screen)
    for dr in rows:
        if dr == cg or not (0 <= dr < len(model._row_titles)):
            continue
        t = model._row_titles[dr]
        if t not in titles:
            titles.append(t)
    _save_hidden_titles(screen, titles)
    apply(screen)
    try:
        from db.usage_log import log_usage_event
        log_usage_event("feature", "hide_machine_rows", str(len(rows)))
    except Exception:
        pass


def show_rows(screen, rows) -> None:
    model = screen.model_machine
    drop = {model._row_titles[dr] for dr in rows if 0 <= dr < len(model._row_titles)}
    _save_hidden_titles(screen, [t for t in load_hidden_titles(screen) if t not in drop])
    apply(screen)


def show_all(screen) -> None:
    show_rows(screen, user_hidden_rows(screen))


# ── UI pieces ────────────────────────────────────────────────────────────
def _update_button(screen, hidden: List[int]) -> None:
    btn = getattr(screen, "btn_hidden_rows", None)
    if btn is None:
        return
    if not hidden:
        btn.setVisible(False)
        return
    model = screen.model_machine
    btn.setText(f"{len(hidden)} row{'s' if len(hidden) != 1 else ''} hidden")
    menu = QMenu(btn)
    menu.addAction("Show all rows", lambda: show_all(screen))
    menu.addSeparator()
    for dr in hidden:
        menu.addAction(f"Show \"{model._row_titles[dr]}\"", lambda dr=dr: show_rows(screen, [dr]))
    old = btn.menu()
    btn.setMenu(menu)
    if old is not None:
        old.deleteLater()
    btn.setVisible(True)


def _selected_title_rows(screen) -> List[int]:
    model = screen.model_machine
    n_hdr = getattr(model, "_n_hdr", 0)
    try:
        idxs = screen.tbl_machine.selectionModel().selectedIndexes()
    except Exception:
        return []
    return sorted({i.row() - n_hdr for i in idxs if i.column() == 0 and i.row() >= n_hdr})


def add_context_actions(screen, menu: QMenu, view_row: int) -> Dict[object, Callable[[], None]]:
    """Adds hide/show entries to the parameter-name context menu."""
    model = getattr(screen, "model_machine", None)
    if model is None:
        return {}
    n_hdr = getattr(model, "_n_hdr", 0)
    dr = view_row - n_hdr
    actions: Dict[object, Callable[[], None]] = {}
    cg = _custom_group_row(screen)
    if 0 <= dr < len(model._row_titles) and dr != cg:
        sel = [r for r in _selected_title_rows(screen) if r != cg]
        target = sel if dr in sel and len(sel) > 1 else [dr]
        menu.addSeparator()
        a = menu.addAction("Hide row" if len(target) == 1 else f"Hide {len(target)} rows")
        actions[a] = lambda: hide_rows(screen, target)
    marker = (getattr(screen, "_machine_row_markers", None) or {}).get(dr)
    if marker:
        a = menu.addAction(f"Show hidden rows here ({len(marker[1])})")
        actions[a] = lambda: show_rows(screen, marker[1])
    n_hidden = len(user_hidden_rows(screen))
    if n_hidden:
        a = menu.addAction(f"Show all hidden rows ({n_hidden})")
        actions[a] = lambda: show_all(screen)
    return actions


def _marker_for(screen, view_row: int):
    model = getattr(screen, "model_machine", None)
    if model is None:
        return None
    return (getattr(screen, "_machine_row_markers", None) or {}).get(view_row - getattr(model, "_n_hdr", 0))


def _marker_is_alert(screen, rows: List[int]) -> bool:
    alerts = getattr(screen.model_machine, "_cell_alerts", {}) or {}
    rows = set(rows)
    return any(dr in rows and kind in ("red", "orange") for (dr, _c), kind in alerts.items())


class _MarkerDelegate(QStyledItemDelegate):
    """Parameter-name column: draws the "rows hidden here" line."""

    def __init__(self, screen, parent=None):
        super().__init__(parent)
        self._screen = screen

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if index.column() != 0:
            return
        marker = _marker_for(self._screen, index.row())
        if not marker:
            return
        edge, rows = marker
        painter.save()
        pen = QPen(_LINE_RED if _marker_is_alert(self._screen, rows) else _LINE_BLUE)
        pen.setWidth(3)
        painter.setPen(pen)
        r = option.rect
        y = r.top() + 1 if edge == "top" else r.bottom() - 1
        painter.drawLine(r.left() + 2, y, r.right() - 2, y)
        painter.restore()


class _MarkerClickFilter(QObject):
    """Click on the line shows the rows again; tooltip names them."""

    def __init__(self, screen, view):
        super().__init__(view)
        self._screen = screen
        self._view = view

    def _hit(self, pos):
        idx = self._view.indexAt(pos)
        if not idx.isValid() or idx.column() != 0:
            return None, False
        marker = _marker_for(self._screen, idx.row())
        if not marker:
            return None, False
        r = self._view.visualRect(idx)
        on_line = (pos.y() - r.top() <= _CLICK_ZONE) if marker[0] == "top" \
            else (r.bottom() - pos.y() <= _CLICK_ZONE)
        return marker, on_line

    def eventFilter(self, obj, ev):
        t = ev.type()
        if t == QEvent.MouseButtonPress and ev.button() == Qt.LeftButton:
            marker, on_line = self._hit(ev.position().toPoint())
            if marker and on_line:
                show_rows(self._screen, marker[1])
                self._view.viewport().unsetCursor()
                return True
        elif t == QEvent.MouseMove:
            _m, on_line = self._hit(ev.position().toPoint())
            if on_line:
                self._view.viewport().setCursor(QCursor(Qt.PointingHandCursor))
            else:
                self._view.viewport().unsetCursor()
        elif t == QEvent.ToolTip:
            marker, _on = self._hit(ev.pos())
            if marker:
                titles = [self._screen.model_machine._row_titles[dr] for dr in marker[1]]
                where = "above" if marker[0] == "top" else "below"
                QToolTip.showText(ev.globalPos(),
                                  f"Hidden {where}: " + ", ".join(titles)
                                  + "\nClick the line to show them again.", self._view)
                return True
        return False


def install(screen) -> None:
    """Once per screen: marker delegate + click filter on the parameter-name
    column of the Machine Data table."""
    if getattr(screen, "_machine_row_vis_installed", False):
        return
    view = screen.tbl_machine.left
    screen._machine_marker_delegate = _MarkerDelegate(screen, view)
    view.setItemDelegateForColumn(0, screen._machine_marker_delegate)
    view.viewport().setMouseTracking(True)
    screen._machine_marker_filter = _MarkerClickFilter(screen, view)
    view.viewport().installEventFilter(screen._machine_marker_filter)
    screen._machine_row_vis_installed = True
