"""Hiding rows in Machine Data (ui/machine_row_visibility.py) and stripes
over visible rows (PivotEditModel.set_hidden_rows)."""
import pytest
from PySide6.QtCore import Qt

from ui import machine_row_visibility as mrv


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_markers_on_next_visible_row():
    assert mrv.compute_markers(6, {1, 2, 4}, set()) == {3: ("top", [1, 2]), 5: ("top", [4])}


def test_marker_at_end_goes_below_last_visible_row():
    # row 5 = Custom Group (hidden by its own toggle) is skipped
    assert mrv.compute_markers(6, {3, 4}, {5}) == {2: ("bottom", [3, 4])}


def test_nothing_hidden():
    assert mrv.compute_markers(4, set(), {3}) == {}


def test_stripes_count_visible_rows_only(qapp):
    from ui.screen_show_experiment import PivotEditModel
    m = PivotEditModel(["a", "b", "c", "d", "e"], ["V1"])
    bg = lambda dr: m.data(m.index(dr, 1), Qt.BackgroundRole).name()
    even, odd = bg(0), bg(1)
    assert even != odd
    m.set_hidden_rows({1, 2})
    assert [bg(dr) for dr in (0, 3, 4)] == [even, odd, even]
    m.set_hidden_rows(set())
    assert [bg(dr) for dr in range(5)] == [even, odd, even, odd, even]
