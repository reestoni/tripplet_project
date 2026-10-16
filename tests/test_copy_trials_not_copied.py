"""Trial copies start with tensions and comments empty (Nutzerwunsch 2026-10-15/16)."""
import pytest

from ui.screen_show_experiment import _col_not_copied


@pytest.mark.parametrize("col, empty", [
    ("Comment", True), ("comment2", True), ("COMMENT4", True), ("YarnTensionBeforeJet", True),
    ("TensionAfterJetOutside", True), ("AirPressure", False), ("CommentedBy", False), ("OF", False),
])
def test_col_not_copied(col, empty):
    assert _col_not_copied(col) is empty
