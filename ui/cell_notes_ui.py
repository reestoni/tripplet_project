# ui/cell_notes_ui.py
"""Notes on values in Show Experiment - UI part (Nutzerwunsch 2026-10-30).
Data/rules: db/cell_notes.py.

- Right-click on a value -> "Add note…" / "Notes (n)…" (everybody)
- Right-click on a trial number (Machine Data) -> note on the whole trial
- Cells with notes get a small triangle in the top right corner, the notes
  are shown in the tooltip (painted by FrozenFirstColumnTable's _GridView via
  PivotEditModel.notes_at())
- Notes tab: list of all notes of the series, double-click jumps to the cell

Functions take the ShowExperimentScreen as first argument (same pattern as
machine_tab.py / advisor_tab.py). Notes are internal and never part of a report.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QFrame, QHBoxLayout, QHeaderView, QInputDialog, QLabel,
    QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from db import cell_notes
from ui.widgets.friendly_error import show_error

_MAX_TOOLTIP_NOTES = 5


# ── helpers ──────────────────────────────────────────────────────────────
def _esc_multiline(text: str) -> str:
    return html.escape(str(text or "")).replace("\n", "<br>")


def _byline(note: Dict[str, Any]) -> str:
    who = (note.get("UserName") or "").strip() or "unknown"
    s = f"{who}, {cell_notes.format_when(note.get('CreatedAt'))}"
    if note.get("UpdatedAt"):
        s += " (edited)"
    return s


def notes_tooltip_html(notes: List[Dict[str, Any]]) -> str:
    parts = []
    for n in notes[:_MAX_TOOLTIP_NOTES]:
        parts.append(f"{_esc_multiline(n.get('NoteText'))}<br>"
                     f"<span style='color:#777;'>- {html.escape(_byline(n))}</span>")
    if len(notes) > _MAX_TOOLTIP_NOTES:
        parts.append(f"<i>… {len(notes) - _MAX_TOOLTIP_NOTES} more (right-click → Notes)</i>")
    title = "<b>Note</b>" if len(notes) == 1 else f"<b>{len(notes)} notes</b>"
    return title + "<br>" + "<br><br>".join(parts)


def can_write(screen) -> bool:
    """Everybody may write notes - not in the read-only recycle bin preview."""
    return cell_notes.available() and getattr(screen, "_recycle_preview", None) is None


def _trial_label(screen, trial_id: Any) -> str:
    try:
        tid = int(trial_id)
    except (TypeError, ValueError):
        return "?"
    for t, label in zip(getattr(screen, "_trial_ids", []) or [], getattr(screen, "_trial_labels", []) or []):
        if int(t) == tid:
            return str(label)
    return f"Trial #{tid}"


def _models(screen) -> List[Tuple[str, Any]]:
    out = []
    for name in getattr(screen, "_save_model_names", []) or []:
        m = getattr(screen, name, None)
        if m is not None and hasattr(m, "notes_at"):
            out.append((name, m))
    return out


def _binding_key(b) -> Optional[Tuple[str, int, str]]:
    """Key of the (first) record of a binding - where a new note is stored."""
    if b is None:
        return None
    ids = getattr(b, "id_values", None)
    rid = (sorted(int(i) for i in ids if i is not None) or [None])[0] if ids is not None else b.id_value
    if rid is None:
        return None
    return (str(b.table), int(rid), str(b.field))


def _column_header(model, view_col: int) -> List[str]:
    n_hdr = getattr(model, "_n_hdr", 0)
    hdr = [str(model.data(model.index(h, view_col), Qt.DisplayRole) or "").strip() for h in range(n_hdr)]
    return [h for i, h in enumerate(hdr) if h and h not in hdr[:i]]


def _table_of(screen, model):
    from ui.widgets.frozen_first_column_table import FrozenFirstColumnTable
    for t in screen.findChildren(FrozenFirstColumnTable):
        if t.model() is model:
            return t
    return None


def _tab_title_of(screen, widget) -> str:
    tabs = getattr(screen, "tabs", None)
    if tabs is None or widget is None:
        return ""
    for i in range(tabs.count()):
        page = tabs.widget(i)
        if page is widget or page.isAncestorOf(widget):
            return tabs.tabText(i).replace("&&", "&").lstrip("🔴 ").strip()
    return ""


def _locate(screen) -> Dict[Tuple[str, int, str], Tuple[str, Any, int, int]]:
    """{cell key (lower): (model attr, model, data row, column 0-based)} over
    all registered models - used for the "Where" column and to jump."""
    out: Dict[Tuple[str, int, str], Tuple[str, Any, int, int]] = {}
    for name, m in _models(screen):
        for dr, row in enumerate(getattr(m, "_binding", []) or []):
            for c, b in enumerate(row):
                if b is None:
                    continue
                ids = getattr(b, "id_values", None) or [getattr(b, "id_value", None)]
                for i in ids:
                    try:
                        out.setdefault((str(b.table).lower(), int(i), str(b.field).lower()), (name, m, dr, c))
                    except (TypeError, ValueError):
                        pass
    return out


# ── loading / applying ───────────────────────────────────────────────────
def reload_notes(screen) -> None:
    """(Re)load the notes of the current series and show them everywhere."""
    if cell_notes.available():
        notes = cell_notes.notes_for_series(getattr(screen, "_series_pk", None),
                                            getattr(screen, "_trial_ids", []) or [])
    else:
        notes = []
    screen._cell_notes = notes
    screen._notes_by_key = cell_notes.by_cell(notes)
    trial_notes: Dict[int, List[Dict[str, Any]]] = {}
    for n in notes:
        if str(n.get("TableName") or "").lower() == "tbltrial" and not n.get("FieldName"):
            trial_notes.setdefault(int(n["TrialID"]), []).append(n)
    screen._trial_notes = trial_notes
    for name, _m in _models(screen):
        apply_notes_to_model(screen, name)
    _fill_notes_list(screen)
    try:
        screen._update_notes_tab_style()
    except Exception:
        pass


def apply_notes_to_model(screen, attr_name: str) -> None:
    model = getattr(screen, attr_name, None)
    if model is None or not hasattr(model, "notes_at"):
        return
    by_key = getattr(screen, "_notes_by_key", None)
    model._notes_by_key = by_key if by_key is not None else {}
    trial_notes = getattr(screen, "_trial_notes", None) or {}
    specs_attr = {"model_machine": "_machine_col_specs", "model_rd_machine": "_rd_machine_col_specs"}.get(attr_name)
    cols: Dict[int, List[Dict[str, Any]]] = {}
    if specs_attr and trial_notes:
        for i, cs in enumerate(getattr(screen, specs_attr, None) or []):
            try:
                tn = trial_notes.get(int(cs["trial_id"]))
            except (KeyError, TypeError, ValueError):
                tn = None
            if tn:
                cols[i] = tn
    model._note_trial_cols = cols
    try:
        model._emit_all(Qt.DisplayRole)
    except Exception:
        pass


# ── menus ────────────────────────────────────────────────────────────────
def add_cell_note_actions(screen, model, index, menu) -> None:
    """Right-click on a value: "Add note…" or "Notes (n)…"."""
    if model is None or not hasattr(model, "notes_at") or not cell_notes.available():
        return
    n_hdr = getattr(model, "_n_hdr", 0)
    b = model.get_binding(index.row() - n_hdr, index.column() - 1)
    if _binding_key(b) is None:
        return
    notes = model.notes_at(index.row(), index.column())
    if notes:
        act = menu.addAction(f"Notes ({len(notes)})…")
    elif can_write(screen):
        act = menu.addAction("Add note…")
    else:
        return
    act.triggered.connect(lambda: open_cell_notes(screen, model, index))


def add_trial_note_action(screen, menu, trial_id: int):
    """Right-click on a trial number: note on the whole trial. Returns the
    action (or None)."""
    if not cell_notes.available():
        return None
    notes = (getattr(screen, "_trial_notes", None) or {}).get(int(trial_id), [])
    label = _trial_label(screen, trial_id)
    if notes:
        return menu.addAction(f"Notes on {label} ({len(notes)})…")
    if can_write(screen):
        return menu.addAction(f"Add note to {label}…")
    return None


def open_cell_notes(screen, model, index) -> None:
    n_hdr = getattr(model, "_n_hdr", 0)
    dr = index.row() - n_hdr
    key = _binding_key(model.get_binding(dr, index.column() - 1))
    if key is None:
        return
    where = " · ".join(_column_header(model, index.column()) + [model._row_titles[dr]])
    tab = _tab_title_of(screen, _table_of(screen, model))
    if tab:
        where = f"{tab}: {where}"
    _open_dialog(screen, where, key, lambda: model.notes_at(index.row(), index.column()))


def open_trial_notes(screen, trial_id: int) -> None:
    key = ("tblTrial", int(trial_id), cell_notes.TRIAL_FIELD)
    where = f"{_trial_label(screen, trial_id)} (whole trial)"
    _open_dialog(screen, where, key,
                 lambda: (getattr(screen, "_trial_notes", None) or {}).get(int(trial_id), []))


def _open_dialog(screen, where: str, key: Tuple[str, int, str], current_notes) -> None:
    try:
        dlg = CellNotesDialog(screen, where, key, current_notes)
    except Exception as e:
        show_error(screen, "Notes", "The notes could not be loaded.", e)
        return
    dlg.exec()


# ── dialog ───────────────────────────────────────────────────────────────
class CellNotesDialog(QDialog):
    """All notes of one cell (or trial) plus a box to write a new one."""

    def __init__(self, screen, where: str, key: Tuple[str, int, str], current_notes):
        super().__init__(screen)
        self._screen = screen
        self._key = key
        self._current_notes = current_notes
        self.setWindowTitle("Notes")
        self.setMinimumWidth(480)
        self.resize(520, 440)

        root = QVBoxLayout(self)
        head = QLabel(f"<b>{html.escape(where)}</b>")
        head.setWordWrap(True)
        root.addWidget(head)
        hint = QLabel("Notes are internal - the Smart Chart shows them only with \"Notes\" switched on, "
                      "the PDF only with \"Include notes on values\".")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#777;")
        root.addWidget(hint)

        self._list_host = QWidget()
        self._list = QVBoxLayout(self._list_host)
        self._list.setContentsMargins(0, 0, 0, 0)
        self._list.setSpacing(6)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(self._list_host)
        root.addWidget(scroll, 1)

        self.txt = None
        if can_write(screen):
            self.txt = QPlainTextEdit()
            self.txt.setPlaceholderText("Write a note, e.g. \"Spool had knots, measured again\"…")
            self.txt.setFixedHeight(80)
            root.addWidget(self.txt)
        btns = QHBoxLayout()
        btns.addStretch(1)
        if self.txt is not None:
            self.btn_add = QPushButton("Add note")
            self.btn_add.setToolTip("Adds the note (Ctrl+Enter)")
            self.btn_add.clicked.connect(self._add)
            btns.addWidget(self.btn_add)
            self.txt.installEventFilter(self)  # Ctrl+Enter = Add note
        b_close = QPushButton("Close")
        b_close.clicked.connect(self.accept)
        btns.addWidget(b_close)
        root.addLayout(btns)
        self._render()
        if self.txt is not None:
            self.txt.setFocus()

    def eventFilter(self, obj, event):  # noqa: N802
        if (obj is self.txt and event.type() == QEvent.KeyPress
                and event.key() in (Qt.Key_Return, Qt.Key_Enter)
                and event.modifiers() & Qt.ControlModifier):
            self._add()
            return True
        return super().eventFilter(obj, event)

    def _render(self) -> None:
        while self._list.count():
            it = self._list.takeAt(0)
            w = it.widget()
            if w is not None:
                w.deleteLater()
        notes = list(self._current_notes() or [])
        if not notes:
            empty = QLabel("No notes yet.")
            empty.setStyleSheet("color:#777;")
            self._list.addWidget(empty)
        for n in notes:
            self._list.addWidget(self._note_widget(n))
        self._list.addStretch(1)

    def _note_widget(self, n: Dict[str, Any]) -> QWidget:
        box = QFrame()
        box.setStyleSheet("QFrame { background:#F3F0FA; border:1px solid #D6CCEB; border-radius:4px; }"
                          "QLabel { border:none; background:transparent; }")
        v = QVBoxLayout(box)
        v.setContentsMargins(8, 6, 8, 6)
        txt = QLabel(_esc_multiline(n.get("NoteText")))
        txt.setTextFormat(Qt.RichText)
        txt.setWordWrap(True)
        txt.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(txt)
        row = QHBoxLayout()
        by = QLabel(f"- {html.escape(_byline(n))}")
        by.setStyleSheet("color:#666;")
        row.addWidget(by)
        if cell_notes.value_changed_since(n):
            chg = QLabel("value changed since this note")
            chg.setStyleSheet("color:#B26A00;")
            row.addWidget(chg)
        row.addStretch(1)
        writable = can_write(self._screen)
        if writable and cell_notes.can_edit(n):
            b = QPushButton("Edit")
            b.setFlat(True)
            b.clicked.connect(lambda _=False, note=n: self._edit(note))
            row.addWidget(b)
        if writable and cell_notes.can_delete(n):
            b = QPushButton("Delete")
            b.setFlat(True)
            b.clicked.connect(lambda _=False, note=n: self._delete(note))
            row.addWidget(b)
        v.addLayout(row)
        return box

    def _changed(self) -> None:
        reload_notes(self._screen)
        self._render()

    def _add(self) -> None:
        if self.txt is None:
            return
        text = self.txt.toPlainText().strip()
        if not text:
            return
        table, row_id, field = self._key
        try:
            cell_notes.add_note(table, row_id, field, text, series_id=getattr(self._screen, "_series_pk", None))
        except Exception as e:
            show_error(self, "Notes", "The note could not be saved.", e)
            return
        try:
            from db.usage_log import log_usage_event
            log_usage_event("feature", "cell_note_add", "trial" if not field else "cell")
        except Exception:
            pass
        self.txt.clear()
        self._changed()

    def _edit(self, n: Dict[str, Any]) -> None:
        text, ok = QInputDialog.getMultiLineText(self, "Edit note", "Note:", str(n.get("NoteText") or ""))
        if not ok or not text.strip() or text.strip() == str(n.get("NoteText") or "").strip():
            return
        try:
            cell_notes.update_note(int(n["ID"]), text)
        except Exception as e:
            show_error(self, "Notes", "The note could not be changed.", e)
            return
        self._changed()

    def _delete(self, n: Dict[str, Any]) -> None:
        if QMessageBox.question(self, "Delete note", "Delete this note?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            cell_notes.delete_note(int(n["ID"]))
        except Exception as e:
            show_error(self, "Notes", "The note could not be deleted.", e)
            return
        self._changed()


# ── Notes tab: list of all notes of the series ───────────────────────────
_LIST_HEADERS = ["Trial", "Where", "Note", "By", "When"]


def build_notes_list(screen, layout) -> None:
    """Adds "Notes on values" (table) below the free series notes."""
    lbl = QLabel("<b>Notes on values</b> - right-click a value or a trial number to add one; "
                 "double-click a line to jump to the value.")
    lbl.setStyleSheet("color:#444; margin-top:6px;")
    lbl.setWordWrap(True)
    tbl = QTableWidget(0, len(_LIST_HEADERS))
    tbl.setHorizontalHeaderLabels(_LIST_HEADERS)
    tbl.verticalHeader().setVisible(False)
    tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
    tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
    tbl.setWordWrap(True)
    hh = tbl.horizontalHeader()
    hh.setSectionResizeMode(2, QHeaderView.Stretch)
    tbl.itemDoubleClicked.connect(lambda item: _jump_from_list(screen, item.row()))
    layout.addWidget(lbl)
    layout.addWidget(tbl, 1)
    screen._notes_list_label = lbl
    screen._notes_list = tbl
    screen._notes_list_rows = []
    lbl.setVisible(cell_notes.available())
    tbl.setVisible(cell_notes.available())


def _fill_notes_list(screen) -> None:
    tbl = getattr(screen, "_notes_list", None)
    if tbl is None:
        return
    avail = cell_notes.available()
    tbl.setVisible(avail)
    lbl = getattr(screen, "_notes_list_label", None)
    if lbl is not None:
        lbl.setVisible(avail)
    notes = list(getattr(screen, "_cell_notes", None) or [])
    order = {int(t): i for i, t in enumerate(getattr(screen, "_trial_ids", []) or [])}
    notes.sort(key=lambda n: (order.get(int(n.get("TrialID") or 0), 10 ** 6), str(n.get("CreatedAt") or "")))
    loc = _locate(screen) if notes else {}
    tbl.setRowCount(len(notes))
    for r, n in enumerate(notes):
        where = _where_text(screen, n, loc)
        vals = [_trial_label(screen, n.get("TrialID")), where, str(n.get("NoteText") or ""),
                (n.get("UserName") or "").strip(), cell_notes.format_when(n.get("CreatedAt"))]
        for c, v in enumerate(vals):
            it = QTableWidgetItem(v)
            if c == 2:
                it.setToolTip(notes_tooltip_html([n]))
            tbl.setItem(r, c, it)
    screen._notes_list_rows = notes
    for c in (0, 1, 3, 4):
        tbl.resizeColumnToContents(c)
    tbl.resizeRowsToContents()


def _where_text(screen, n: Dict[str, Any], loc) -> str:
    if str(n.get("TableName") or "").lower() == "tbltrial" and not n.get("FieldName"):
        return "(whole trial)"
    hit = loc.get(cell_notes.cell_key(n["TableName"], n["RowID"], n.get("FieldName")))
    if hit is None:
        return f"{n.get('TableName')} · {n.get('FieldName')}"
    _name, m, dr, c = hit
    hdr = _column_header(m, c + 1)
    # trial label is in its own column - keep e.g. the ply
    label = _trial_label(screen, n.get("TrialID"))
    hdr = [h for h in hdr if h != label]
    tab = _tab_title_of(screen, _table_of(screen, m))
    parts = ([tab] if tab else []) + hdr + [m._row_titles[dr]]
    return " · ".join(parts)


def _jump_from_list(screen, row: int) -> None:
    notes = getattr(screen, "_notes_list_rows", []) or []
    if not (0 <= row < len(notes)):
        return
    n = notes[row]
    if str(n.get("TableName") or "").lower() == "tbltrial" and not n.get("FieldName"):
        _jump_to_trial(screen, int(n["TrialID"]))
        return
    hit = _locate(screen).get(cell_notes.cell_key(n["TableName"], n["RowID"], n.get("FieldName")))
    if hit is None:
        QMessageBox.information(screen, "Notes", "This value is not shown in any open tab at the moment.")
        return
    _name, m, dr, c = hit
    _select(screen, m, m._n_hdr + dr, c + 1)


def _jump_to_trial(screen, trial_id: int) -> None:
    m = getattr(screen, "model_machine", None)
    specs = getattr(screen, "_machine_col_specs", None) or []
    for i, cs in enumerate(specs):
        if int(cs.get("trial_id") or 0) == trial_id and m is not None:
            _select(screen, m, getattr(m, "_n_hdr", 0), i + 1)
            return


def _select(screen, model, view_row: int, view_col: int) -> None:
    t = _table_of(screen, model)
    if t is None:
        return
    tabs = getattr(screen, "tabs", None)
    if tabs is not None:
        for i in range(tabs.count()):
            if tabs.widget(i).isAncestorOf(t):
                tabs.setCurrentIndex(i)
                break
    idx = model.index(view_row, view_col)
    view = t.bottom_right
    try:
        view.setCurrentIndex(idx)
        view.scrollTo(idx)
        view.setFocus()
    except Exception:
        pass
