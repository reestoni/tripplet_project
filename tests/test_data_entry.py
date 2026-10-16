"""Excel-like data entry in Show Experiment (Nutzerwunsch 2026-10-16):
Enter goes down, Ctrl+Z / Ctrl+Y for unsaved edits. Verified end-to-end on
dev_local with series 311 (typing + Enter, Shift+Enter, Delete + undo as
one step, redo, Ctrl+Z inside an open editor stays in the editor)."""
import pytest
from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtWidgets import QApplication, QWidget


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def model(monkeypatch):
    import app_meta
    from ui.screen_show_experiment import PivotEditModel
    monkeypatch.setattr(app_meta, "access_level", lambda: 4)
    m = PivotEditModel(["A", "B", "C"], ["V1", "V2"])
    m._binding = [[object(), object()] for _ in range(3)]
    for r in range(3):
        for c in range(2):
            m._matrix[r][c] = f"{r}{c}"
    return m


class _Screen(QWidget):
    revealed = None

    def _reveal_cell(self, model, idx):
        self.revealed = (idx.row(), idx.column())


def test_undo_redo_steps(app, model):
    from ui.screen_show_experiment import _UndoManager
    scr = _Screen()
    mgr = _UndoManager(scr)
    model._undo_mgr = mgr
    model.setData(model.index(0, 1), "x")
    app.processEvents()  # closes the step
    model.setData(model.index(1, 1), "")  # e.g. Delete on two cells = one step
    model.setData(model.index(1, 2), "")
    app.processEvents()
    assert len(mgr._undo) == 2 and model.dirty_cells() == {(0, 0), (1, 0), (1, 1)}
    assert mgr.undo() == 2
    assert [model._matrix[1][c] for c in (0, 1)] == ["10", "11"] and model.dirty_cells() == {(0, 0)}
    assert scr.revealed == (1, 2)
    assert mgr.undo() == 1 and model._matrix[0][0] == "00" and model._dirty == []
    assert mgr.undo() == 0
    assert mgr.redo() == 1 and model._matrix[0][0] == "x" and model.dirty_cells() == {(0, 0)}
    model.setData(model.index(2, 1), "y")  # a new edit drops the redo steps
    assert not mgr.can_redo()


def test_enter_moves_down_skipping_hidden_rows(app, model):
    from PySide6.QtTest import QTest
    from ui.widgets.frozen_first_column_table import FrozenFirstColumnTable
    t = FrozenFirstColumnTable()
    t.setModel(model)
    v = t.bottom_right
    v.setRowHidden(1, True)
    t.selectionModel().setCurrentIndex(model.index(0, 1), QItemSelectionModel.ClearAndSelect)
    QTest.keyClick(v, Qt.Key_Return)
    assert v.currentIndex().row() == 2
    QTest.keyClick(v, Qt.Key_Return, Qt.ShiftModifier)
    assert v.currentIndex().row() == 0
    QTest.keyClick(v, Qt.Key_Return, Qt.ShiftModifier)  # top row: stays
    assert v.currentIndex().row() == 0


def test_recent_series_list_and_menu(app, monkeypatch):
    from PySide6.QtWidgets import QMenu, QPushButton
    import app_meta
    from ui import display_prefs, recent_series
    from ui.widgets import sidebar_nav
    monkeypatch.setattr(display_prefs, "_save_later", lambda: None)
    monkeypatch.setattr(display_prefs, "_prefs", dict(display_prefs.DEFAULTS))
    for i in range(10):
        recent_series.remember(1, 100 + i, f"2026-01-{i:03d}", f"S{i}")
    recent_series.remember(1, 103, "2026-01-003", "S3")  # opened again -> moves to the top, no duplicate
    ids = [e["series"] for e in recent_series.entries()]
    assert ids[0] == 103 and len(ids) == display_prefs.RECENT_MAX and ids.count(103) == 1
    menu = sidebar_nav.build_recent_menu(QPushButton("Recent"))
    assert [a.text() for a in menu.actions() if a.isEnabled() and not a.isSeparator()][0] == "2026-01-003   S3"
    opened = []
    monkeypatch.setattr(app_meta, "open_recent_series", lambda *a: opened.append(a), raising=False)
    monkeypatch.setattr(recent_series, "series_exists", lambda sid: True)
    sidebar_nav.open_recent_series(recent_series.entries()[0])
    assert opened == [(1, 103, "2026-01-003", False)]
    display_prefs._prefs = dict(display_prefs.DEFAULTS)


def test_recent_button_enabled(app):
    from ui.widgets.sidebar import SidebarPanel
    from ui.widgets.sidebar_nav import build_pinned_recent
    assert build_pinned_recent(SidebarPanel()).isEnabled()
