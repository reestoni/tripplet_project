"""Display settings (ui/display_prefs.py) and their effect on the Show
Experiment tables (FrozenFirstColumnTable + PivotEditModel). No DB needed."""
import pytest
from PySide6.QtCore import Qt, QItemSelectionModel

from ui import display_prefs as dp


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _reset():
    dp._prefs = dict(dp.DEFAULTS)
    yield
    dp._prefs = dict(dp.DEFAULTS)


def test_clean_clamps_and_defaults():
    assert dp._clean({"scale": 1000, "contrast": 1}) == dict(dp.DEFAULTS, scale=dp.SCALE_MAX, contrast=True)
    assert dp._clean({"scale": "x"}) == dp.DEFAULTS


def test_zoom_step(monkeypatch):
    monkeypatch.setattr(dp, "_save_later", lambda: None)
    dp.zoom_step(1)
    assert dp.scale() == 110
    for _ in range(10):
        dp.zoom_step(-1)
    assert dp.scale() == dp.SCALE_MIN


def _table():
    from ui.screen_show_experiment import PivotEditModel
    from ui.widgets.frozen_first_column_table import FrozenFirstColumnTable
    m = PivotEditModel(["a", "b", "c"], ["V1", "V2"],
                       header_rows=[{"values": ["", "V1", "V2"], "bg": None, "fg": None}])
    t = FrozenFirstColumnTable()
    t.setModel(m)
    t.resizeColumnsToContents(fixed_data_column_width=90)
    return t, m


def test_scale_contrast_crosshair(qapp):
    t, m = _table()
    size0, h0 = t.right.font().pointSizeF(), t.right.verticalHeader().defaultSectionSize()
    dp.update(persist=False, scale=200, contrast=True, crosshair=True)
    assert t.right.font().pointSizeF() == pytest.approx(size0 * 2)
    assert t.right.verticalHeader().defaultSectionSize() == h0 * 2
    assert t.right.columnWidth(1) == 180
    assert t.right.font().bold()
    bg = lambda r, c: m.data(m.index(r, c), Qt.BackgroundRole).name()
    assert {bg(1, 1), bg(2, 1)} == {"#ffffff", "#d0d0d0"}
    t.selectionModel().setCurrentIndex(m.index(2, 2), QItemSelectionModel.ClearAndSelect)
    assert bg(2, 0) == "#ffd54f"            # parameter name of the row
    assert bg(0, 2) == "#ffd54f"            # trial number of the column
    assert bg(2, 1) == bg(3, 2) == "#fff3b8"
    dp.update(persist=False, scale=100, contrast=False, crosshair=False)
    assert t.right.font().pointSizeF() == pytest.approx(size0)
    assert t.right.columnWidth(1) == 90
    assert bg(2, 1) != "#fff3b8"


def test_reading_bar_and_warning_symbols(qapp):
    t, m = _table()
    m.set_cell(1, 1, "3.5", None)
    m._cell_alerts[(1, 1)] = "red"
    dp.update(persist=False, readbar=True, alert_marks=True)
    t.selectionModel().setCurrentIndex(m.index(2, 2), QItemSelectionModel.ClearAndSelect)
    assert t.read_bar.text() == "V2 · b = <b>3.5</b>  –  <b>! Warning</b>"
    assert m.data(m.index(2, 2), Qt.DecorationRole) is not None
    assert m.data(m.index(2, 1), Qt.DecorationRole) is None
    dp.update(persist=False, cb_colours=True)
    assert m.data(m.index(2, 2), Qt.BackgroundRole).name() == "#e69f00"
    dp.update(persist=False, alert_marks=False, cb_colours=False)
    assert m.data(m.index(2, 2), Qt.DecorationRole) is None


def test_app_scale_choices():
    assert dp._clean({"app_scale": 150})["app_scale"] == 150
    assert dp._clean({"app_scale": 133})["app_scale"] == 100
