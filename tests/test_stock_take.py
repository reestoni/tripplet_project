"""Stock take rounds (db/stock_take.py, ui/widgets/stock_take_round_dialog.py,
location mode of ui/widgets/stock_take_dialog.py) - without DB. End-to-end on
dev_local verified 2026-10-16 (round with 169 locations, 3 checks incl. move,
unknown number, missing seen elsewhere, leave out, Excel export, close)."""
import datetime

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QInputDialog, QMessageBox

from db import stock_take as st


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def test_parse_and_sort_locations():
    assert st.parse_location(" c21 ") == ("C", "2", "1")
    assert st.parse_location("E") == ("E", "", "")
    assert st.parse_location("12X") == ("", "", "12X")
    locs = ["C110", "A12", "C12", "A3", "C2", "B", "", "c11", "9"]
    assert sorted({st.norm_location(l) for l in locs if l}, key=st.location_sort_key) == \
        ["A12", "A3", "B", "C11", "C12", "C110", "C2", "9"]  # C110 = level 1, slot 10
    groups = st.group_locations(["C21", "A11", "C11", "C23", "x1"])
    assert [g[0] for g in groups] == ["A", "C", "X"]
    assert groups[1][1] == [("1", ["C11"]), ("2", ["C21", "C23"])]


def test_tile_columns_line_up_with_gaps():
    from ui.widgets.stock_take_round_dialog import tile_columns
    assert tile_columns(["A31", "A33"]) == [("A31", 0), ("A33", 2)]
    assert tile_columns(["E", "E1X"]) == [("E", 0), ("E1X", 1)]


def _loc(name, checked=True, excluded=False):
    return {"Location": name, "Excluded": excluded,
            "CheckedAt": datetime.datetime(2026, 10, 16) if checked else None, "Expected": 2, "Found": 1}


def test_status_summary_and_seen_elsewhere():
    items = [
        {"Location": "A11", "SpoolID": 1, "Result": st.FOUND},
        {"Location": "A11", "SpoolID": 2, "Result": st.MISSING_KEPT},
        {"Location": "A12", "SpoolID": 3, "Result": st.FOUND},
        {"Location": "A13", "SpoolID": 2, "Result": st.MOVED_HERE, "Detail": "from A11"},
    ]
    locs = [_loc("A11"), _loc("A12"), _loc("A13"), _loc("A21", checked=False), _loc("A22", excluded=True)]
    by = lambda l: [i for i in items if i["Location"] == l]
    assert [st.location_status(l, by(l["Location"])) for l in locs] == \
        [st.ST_DEVIATION, st.ST_OK, st.ST_DEVIATION, st.ST_OPEN, st.ST_EXCLUDED]
    assert st.resolve_missing(items) == {1: "seen at A13"}
    s = st.summarize(locs, items)
    assert (s["to_check"], s["checked"], s[st.ST_OPEN], s[st.ST_EXCLUDED]) == (4, 3, 1, 1)
    assert (s[st.FOUND], s[st.MISSING_KEPT], s[st.MOVED_HERE], s["missing_seen_elsewhere"]) == (2, 1, 1, 1)


def test_scan_dialog_location_mode_records_outcomes(app, monkeypatch):
    from ui.widgets import stock_take_dialog as sd
    monkeypatch.setattr(sd, "execute", lambda *a, **k: 1)
    monkeypatch.setattr(sd.yarn_spool_log, "log_spool_changes", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: None))
    spools = [
        {"ID": 1, "YarnID": 5, "Location": "C21", "Status": "in stock"},
        {"ID": 2, "YarnID": 5, "Location": "c21 ", "Status": "in stock"},
        {"ID": 3, "YarnID": 5, "Location": "C210", "Status": "in stock"},  # prefix only - not expected
        {"ID": 4, "YarnID": 5, "Location": "A11", "Status": "in stock"},
        {"ID": 5, "YarnID": 5, "Location": "A12", "Status": "discarded"},
    ]
    dlg = sd.StockTakeDialog(spools, {5: "PES"}, round_location="c21", round_name="R")
    assert dlg.txt_location.isReadOnly() and dlg.expected_count() == 2
    answers = iter([("C21", True), ("", False)])
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: next(answers)))
    for raw in ("1", "4", "5", "99999"):
        dlg.txt_scan.setText(raw)
        dlg._on_scan()
    got = {(i["SpoolID"], i["Result"]) for i in dlg.outcome_items()}
    assert got == {(1, st.FOUND), (4, st.MOVED_HERE), (5, st.DISCARDED_UNCHANGED), (99999, st.UNKNOWN),
                   (2, st.MISSING_KEPT)}
    dlg._missing_result = st.MISSING_DISCARDED
    assert (2, st.MISSING_DISCARDED) in {(i["SpoolID"], i["Result"]) for i in dlg.outcome_items()}


def test_round_dialog_without_tables_offers_single_check(app, monkeypatch):
    monkeypatch.setattr(st, "available", lambda: False)
    from ui.widgets.stock_take_round_dialog import StockTakeRoundDialog
    dlg = StockTakeRoundDialog(lambda: ([], {}), writable=True)
    assert not dlg.btn_start.isVisibleTo(dlg) and dlg.btn_single.isVisibleTo(dlg)
    assert "not set up" in dlg.lbl_info.text()


def test_enter_in_scan_field_does_not_finish(app, monkeypatch):
    """Bug 2026-10-16: in location mode Enter also clicked 'Finish stock take…'."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from ui.widgets import stock_take_dialog as sd
    finished = []
    monkeypatch.setattr(sd.StockTakeDialog, "_on_finish", lambda self: finished.append(1))
    spools = [{"ID": 1, "YarnID": 5, "Location": "A11", "Status": "in stock"},
              {"ID": 2, "YarnID": 5, "Location": "A11", "Status": "in stock"}]
    dlg = sd.StockTakeDialog(spools, {5: "PES"}, round_location="A11")
    dlg.show()
    dlg.txt_scan.setFocus()
    QTest.keyClicks(dlg.txt_scan, "1")
    QTest.keyClick(dlg.txt_scan, Qt.Key_Return)
    assert dlg._found == {1} and finished == []
    dlg._finished = True  # close without the "leave without finishing?" question
    dlg.close()


def test_double_click_marks_by_hand_and_right_click_undo(app):
    from ui.widgets import stock_take_dialog as sd
    spools = [{"ID": 1, "YarnID": 5, "Location": "A11", "Status": "in stock"},
              {"ID": 2, "YarnID": 5, "Location": "A11", "Status": "in stock"}]
    dlg = sd.StockTakeDialog(spools, {5: "PES"}, round_location="A11")
    dlg.tbl_expected.cellDoubleClicked.emit(1, 2)  # spool #2 by hand
    assert dlg._found == {2} and dlg.tbl_expected.item(1, 0).text() == "by hand"
    items = {i["SpoolID"]: i for i in dlg.outcome_items()}
    assert items[2]["Result"] == st.FOUND and items[2]["Detail"] == st.BY_HAND_NOTE
    assert items[1]["Result"] == st.MISSING_KEPT
    assert st.summarize([], list(items.values()))["found_by_hand"] == 1
    dlg._undo_found(1)
    assert dlg._found == set() and dlg.missing_ids() == [1, 2]
    dlg._mark_found_by_hand(0)
    dlg.txt_scan.setText("1")
    dlg._on_scan()  # scanning confirms it -> no longer "by hand"
    assert dlg._found == {1} and not dlg._manual
    assert {i["SpoolID"]: i["Detail"] for i in dlg.outcome_items()}[1] is None
    dlg._finished = True
