"""Deleting single trials from Show Experiment (db/recycle_bin.delete_trials,
Nutzerwunsch 2026-11-11): the other trials keep their numbers (nothing moves
up), new trials always come after the highest remaining number (gaps are
never filled; numbers deleted at the end may be used again - Nutzerentscheid).
No DB needed - end-to-end on dev_local verified by hand 2026-11-11 (series
453: V2, V13, V14 deleted and restored -> identical again)."""
import pytest

from db import recycle_bin as rb
from db import trial_reference as tr


@pytest.mark.parametrize("max_vno, expected", [
    (22, 23),    # V23-V42 deleted -> the next trial is V23 again
    (42, 43),    # deleted in the middle -> the gap stays, next after V42
])
def test_next_trial_number_never_fills_gaps(max_vno, expected):
    assert tr.next_trial_number(max_vno) == expected


@pytest.mark.parametrize("vnos, expected", [
    (range(23, 43), "V23–V42"),
    ([3, 7, 8], "V3, V7, V8"),
    ([5, 1, 2, 3, -1], "V1–V3, V5, Ref"),
    ([-1, -2], "2 x Ref"),
    ([], ""),
])
def test_format_number_list(vnos, expected):
    assert tr.format_number_list(vnos) == expected


class _Cur:
    """Answers the two queries of _check_trials_restorable()."""

    def __init__(self, series_exists, taken):
        self.series_exists, self.taken = series_exists, taken

    def execute(self, sql, params=()):
        pass

    def fetchone(self):
        return [1 if self.series_exists else 0]

    def fetchall(self):
        return [[n] for n in self.taken]


_DATA = {"groups": [{"table": "tblTrial", "rows": [{"ID": 1, "Versuchsnummer": 23},
                                                   {"ID": 2, "Versuchsnummer": 24}]}]}


def test_restore_needs_the_series():
    with pytest.raises(rb.RecycleBinError, match="restore the series first"):
        rb._check_trials_restorable(_Cur(False, []), 460, _DATA)


def test_restore_refuses_numbers_used_again():
    # V24 was given out again after the delete -> nothing is restored
    with pytest.raises(rb.RecycleBinError, match="V24"):
        rb._check_trials_restorable(_Cur(True, [24]), 460, _DATA)


def test_restore_ok_when_numbers_free():
    rb._check_trials_restorable(_Cur(True, []), 460, _DATA)


def test_delete_trials_needs_recycle_bin(monkeypatch):
    monkeypatch.setattr(rb, "available", lambda: False)
    assert rb.can_delete_trials_now(460) is False
    with pytest.raises(rb.RecycleBinError):
        rb.delete_trials(460, [1, 2])
