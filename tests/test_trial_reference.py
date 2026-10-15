"""Reference samples (customer originals as flagged tblTrial rows, see
db/trial_reference.py): SQL filter, labels and the amber column highlight in
the Show Experiment pivot model. No DB needed."""
from unittest.mock import patch

import pytest

from db import trial_reference as tr


def test_exclude_sql_with_and_without_column():
    with patch.object(tr, "has_reference_columns", return_value=True):
        assert tr.exclude_references_sql("t") == "COALESCE(t.IsReference, 0) = 0"
        assert tr.exclude_references_sql("") == "COALESCE(IsReference, 0) = 0"
    # Older DB / offline snapshot without the column: filter must be a no-op.
    with patch.object(tr, "has_reference_columns", return_value=False):
        assert tr.exclude_references_sql("t") == "1=1"


@pytest.mark.parametrize("value, expected", [
    (1, True), ("1", True), (True, True), (0, False), (None, False), ("", False), ("x", False),
])
def test_is_reference_value(value, expected):
    assert tr.is_reference_value(value) is expected


def test_label_and_tooltip():
    assert tr.reference_label(-1) == "Ref"
    assert "Customer X" in tr.reference_tooltip("Customer X", -1)
    assert tr.reference_tooltip("", -1).startswith("Reference sample\n")


@pytest.mark.parametrize("max_vno, expected", [
    (None, 1), (0, 1), (-2, 1),   # empty series / only reference samples -> V1
    (7, 8), ("7", 8),
])
def test_next_trial_number_ignores_negative_reference_numbers(max_vno, expected):
    assert tr.next_trial_number(max_vno) == expected


@pytest.mark.parametrize("min_vno, expected", [
    (None, -1), (1, -1), (5, -1),  # no reference yet -> -1
    (-1, -2), (-3, -4),
])
def test_next_reference_number(min_vno, expected):
    assert tr.next_reference_number(min_vno) == expected


@pytest.mark.parametrize("vno, expected", [(3, "V3"), ("12", "V12"), (-1, "Ref"), (0, "Ref"), ("?", "V?")])
def test_format_trial_number(vno, expected):
    assert tr.format_trial_number(vno) == expected


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_pivot_model_highlights_reference_columns(qapp):
    from PySide6.QtCore import Qt
    from ui.screen_show_experiment import PivotEditModel

    m = PivotEditModel(row_titles=["Titer (dtex)", "FPm"], col_titles=["Ref", "V1", "V2"],
                       header_rows=[{"values": ["", "Ref", "V1", "V2"], "bg": None, "fg": None}])
    m.set_reference_columns({0: "Reference sample: Customer X"})

    ref_bg = m.data(m.index(1, 1), Qt.BackgroundRole)   # first data row, reference column
    trial_bg = m.data(m.index(1, 2), Qt.BackgroundRole)
    assert ref_bg == PivotEditModel._REF_EVEN
    assert trial_bg != ref_bg
    assert m.data(m.index(0, 1), Qt.BackgroundRole) == PivotEditModel._REF_HDR_BG
    assert m.data(m.index(0, 1), Qt.ToolTipRole) == "Reference sample: Customer X"
    assert m.headerData(1, Qt.Horizontal, Qt.ToolTipRole) == "Reference sample: Customer X"
    assert m.headerData(2, Qt.Horizontal, Qt.ToolTipRole) is None

    # Cell alerts still win over the reference tint.
    m.set_cell_alert(0, 0, "red")
    assert m.data(m.index(1, 1), Qt.BackgroundRole) != PivotEditModel._REF_EVEN
