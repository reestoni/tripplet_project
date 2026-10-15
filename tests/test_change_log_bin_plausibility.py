"""Change history, recycle bin (JSON round trip) and plausibility check -
pure logic, no DB needed. (Delete/restore of real series was verified on
dev_local: rows identical after restore.)"""
import datetime
import decimal

import pytest
from PySide6.QtCore import Qt

from db import change_log, plausibility, recycle_bin


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("a, b, same", [
    ("3.50", "3.5", True), (decimal.Decimal("3.50"), "3.5", True), (None, "", True),
    (None, "0", False), ("abc", "abc", True), ("abc", "abd", False), ("4", "4.25", False),
])
def test_same_value(a, b, same):
    assert change_log.same_value(a, b) is same


def test_upsert_entries():
    e = change_log.upsert_entries("tblX", 7, {"A": 1}, {"A": 2, "B": 3}, 99)
    assert e == [{"table": "tblX", "row_id": 7, "field": "A", "old": 1, "new": 2, "trial_id": 99},
                 {"table": "tblX", "row_id": 7, "field": "B", "old": None, "new": 3, "trial_id": 99}]
    assert change_log.upsert_entries("tblX", None, {}, {"A": 1}, 1) == []


def test_recycle_bin_json_round_trip():
    import json
    row = {"ID": 1, "B": b"\x00\x01", "D": decimal.Decimal("1.25"), "T": datetime.datetime(2026, 10, 15, 12, 0)}
    back = {k: recycle_bin._dec(v) for k, v in json.loads(json.dumps({k: recycle_bin._enc(v) for k, v in row.items()})).items()}
    assert back == {"ID": 1, "B": b"\x00\x01", "D": "1.25", "T": "2026-10-15 12:00:00"}


def test_range_of_and_unusual():
    vals = [3.0, 3.5, 4.0, 4.5, 5.0, 6.0] * 10
    rg = plausibility.range_of(vals)
    assert rg["p01"] == 3.0 and rg["p99"] == 6.0
    assert not plausibility.is_unusual(rg, "4.2")
    assert plausibility.is_unusual(rg, "35")       # factor 10 too big
    assert plausibility.is_unusual(rg, "0.35")     # factor 10 too small
    assert not plausibility.is_unusual(rg, "")
    assert plausibility.range_of(vals[:10]) is None          # too few values
    assert plausibility.range_of([0.0] * 50) is None         # always the same


def test_find_unusual_in_model(qapp, monkeypatch):
    from ui.screen_show_experiment import PivotEditModel, CellBinding
    m = PivotEditModel(["Air Pressure (bar)", "Speed"], ["V1", "V2"],
                       header_rows=[{"values": ["", "V1", "V2"], "bg": None, "fg": None}])
    monkeypatch.setattr(m, "_ctx_is_readonly", lambda: False)
    for c in range(2):
        m.set_cell(0, c, "4", CellBinding("tblTrial", "ID", c + 1, "AirPressure"))
        m.set_cell(1, c, "600", CellBinding("tblTrial", "ID", c + 1, "SpeedShaft2"))
    monkeypatch.setattr(plausibility, "ranges_for_machine", lambda mid: {
        ("tbltrial", "airpressure"): plausibility.range_of([3.0, 4.0, 5.0] * 20),
        ("tbltrial", "speedshaft2"): plausibility.range_of([550.0, 650.0, 750.0] * 20)})
    m.setData(m.index(1, 2), "35")
    m.setData(m.index(2, 1), "620")
    found = plausibility.find_unusual(m, 1)
    assert [(e["row"], e["col"]) for e in found] == [(0, 1)]
    assert found[0]["text"].startswith("V2 · Air Pressure (bar): 35")


@pytest.mark.parametrize("lvl, status, owner, user, ok", [
    (4, 5, None, 1, True),      # superuser: always
    (2, 1, 9, 1, True),         # Backlog: every write user
    (1, 1, None, 1, False),     # read-only: never
    (2, 2, 1, 1, True),         # In Progress: owner
    (2, 3, 9, 1, False),        # Done: not the owner
    (2, 4, 9, 1, True),         # To Be Cleaned -> Archived: every write user
    (3, 5, 1, 1, False),        # Archived: superusers only
    (2, None, None, 1, False),  # no status, no owner
])
def test_can_move_series(lvl, status, owner, user, ok):
    from db.series_permissions import can_move_series
    assert can_move_series(lvl, status, owner, user) is ok


@pytest.mark.parametrize("lvl, status, owner, user, ok", [
    (2, 4, 9, 1, False),        # To Be Cleaned: write users may move it, but not delete it
    (2, 4, 1, 1, False),        # ... not even the owner
    (4, 4, None, 1, True),      # superuser may
    (2, 1, 9, 1, True),         # Backlog: like moving
    (2, 2, 1, 1, True),         # In Progress: owner, like moving
])
def test_can_delete_series(lvl, status, owner, user, ok):
    from db.series_permissions import can_delete_series
    assert can_delete_series(lvl, status, owner, user) is ok
