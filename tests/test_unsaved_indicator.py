"""Unsaved changes in Show Experiment (Nutzerwunsch 2026-10-16): yellow
cells, "Save (n)", dot in the tab, Save/Discard/Cancel on closing a tab.
End-to-end on dev_local verified with series 311 (nothing saved)."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QStackedWidget, QWidget


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def _model():
    from ui.screen_show_experiment import PivotEditModel
    m = PivotEditModel(["Air Pressure (bar)", "Overfeed (%)"], ["V1", "V2"])
    m._binding = [[object(), object()], [object(), object()]]
    return m


def test_dirty_cells_yellow_with_tooltip(app, monkeypatch):
    import app_meta
    monkeypatch.setattr(app_meta, "access_level", lambda: 4)
    m = _model()
    before = m.data(m.index(1, 2), Qt.BackgroundRole)
    assert m.setData(m.index(0, 1), "4.5")
    assert m.dirty_cells() == {(0, 0)}
    assert m.data(m.index(0, 1), Qt.BackgroundRole) == m._DIRTY_BG
    assert m._DIRTY_TIP in m.data(m.index(0, 1), Qt.ToolTipRole)
    assert m.data(m.index(1, 2), Qt.BackgroundRole) == before  # other cells untouched
    m._dirty.clear()  # what save_dirty() does
    assert m.dirty_cells() == set() and m.data(m.index(0, 1), Qt.BackgroundRole) != m._DIRTY_BG


class _FakeScreen(QWidget):
    def __init__(self, answer=True):
        super().__init__()
        self.asked = 0
        self.answer = answer

    def confirm_close_with_unsaved(self):
        self.asked += 1
        return self.answer


def test_tab_close_asks_and_cancel_keeps_tab(app):
    from ui.widgets.tab_container import TabbedNavigator
    nav = TabbedNavigator()
    stack = QStackedWidget()
    scr = _FakeScreen(answer=False)
    stack.addWidget(scr)
    idx = nav.addTab(stack, "Show Experiment")
    nav._on_tab_close_requested(idx)
    assert scr.asked == 1 and nav.indexOf(stack) == idx  # Cancel -> stays
    scr.answer = True
    nav._on_tab_close_requested(nav.indexOf(stack))
    assert nav.indexOf(stack) == -1
    # logout path closes without asking
    stack2 = QStackedWidget()
    scr2 = _FakeScreen(answer=False)
    stack2.addWidget(scr2)
    nav.addTab(stack2, "x")
    nav.close_all_but_first()
    assert scr2.asked == 0 and nav.count() == 1


def test_delete_clears_selected_editable_cells(app, monkeypatch):
    import app_meta
    from PySide6.QtCore import QItemSelectionModel
    from ui.screen_show_experiment import ShowExperimentScreen
    from ui.widgets.frozen_first_column_table import FrozenFirstColumnTable
    monkeypatch.setattr(app_meta, "access_level", lambda: 4)
    m = _model()
    m.setData(m.index(0, 1), "4.0")
    m.setData(m.index(0, 2), "4.5")
    m._readonly = {1}
    m._matrix[1][0] = "8"
    m._dirty.clear()
    t = FrozenFirstColumnTable()
    t.setModel(m)
    sel = t.selectionModel()
    for r, c in ((0, 1), (0, 2), (1, 1), (0, 0)):  # incl. a read-only cell and the title column
        sel.select(m.index(r, c), QItemSelectionModel.Select)
    n = ShowExperimentScreen._clear_selected_cells(object(), t)
    assert n == 2
    assert [m.data(m.index(0, c)) for c in (1, 2)] == ["", ""] and m.data(m.index(1, 1)) == "8"
    assert m.dirty_cells() == {(0, 0), (0, 1)}
