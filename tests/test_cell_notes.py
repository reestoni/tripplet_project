"""Notes on values in Show Experiment (db/cell_notes.py, ui/cell_notes_ui.py),
Nutzerwunsch 2026-10-30. DB simulated; end-to-end on dev_local verified with
series 311 (note on Air Pressure + trial note, triangle, Notes tab list, jump)."""
import datetime

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMenu, QWidget


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def _note(nid, table, row_id, field, text="x", by=7, trial=1):
    return {"ID": nid, "TableName": table, "RowID": row_id, "FieldName": field, "TrialID": trial,
            "NoteText": text, "CreatedBy": by, "UserName": "Ann Lab",
            "CreatedAt": datetime.datetime(2026, 10, 30, 7, 28), "UpdatedAt": None}


def _model():
    from ui.screen_show_experiment import CellBinding, GroupCellBinding, PivotEditModel
    m = PivotEditModel(["Air Pressure (bar)", "Tenacity"], ["V1", "V2"],
                       header_rows=[{"values": ["", "V1", "V2"]}])
    m._binding = [
        [CellBinding("tblTrial", "ID", 10, "AirPressure"), CellBinding("tblTrial", "ID", 11, "AirPressure")],
        [GroupCellBinding("tblLaborStatimatM", "ID", [5, 6], "Tenacity"), None],
    ]
    return m


def test_notes_at_data_cells_group_and_trial_header(app):
    from db import cell_notes
    m = _model()
    assert m.notes_at(1, 1) == []  # nothing set -> no notes, no error
    notes = [_note(1, "tblTrial", 10, "AirPressure"),
             _note(2, "TBLLABORSTATIMATM", 6, "tenacity"),   # case-insensitive, 2nd id of the group
             _note(3, "tblTrial", 11, "")]                     # whole-trial note, not a cell
    m._notes_by_key = cell_notes.by_cell(notes)
    m._note_trial_cols = {1: [notes[2]]}
    assert [n["ID"] for n in m.notes_at(1, 1)] == [1]
    assert m.notes_at(1, 2) == []                 # same field, other trial
    assert [n["ID"] for n in m.notes_at(2, 1)] == [2]
    assert m.notes_at(2, 2) == []                 # no binding
    assert [n["ID"] for n in m.notes_at(0, 2)] == [3]   # trial number row
    assert m.notes_at(1, 0) == []                 # title column


def test_tooltip_escapes_and_truncates(app):
    from ui.cell_notes_ui import notes_tooltip_html
    tip = notes_tooltip_html([_note(1, "t", 1, "f", "a < b\nsecond line")])
    assert "a &lt; b<br>second line" in tip and "Ann Lab, 30.10.2026 07:28" in tip
    many = notes_tooltip_html([_note(i, "t", 1, "f") for i in range(8)])
    assert "8 notes" in many and "3 more" in many


def test_edit_and_delete_rules(monkeypatch):
    import app_meta
    from db import cell_notes
    n = _note(1, "t", 1, "f", by=7)
    monkeypatch.setattr(app_meta, "current_user", {"id": 7})
    monkeypatch.setattr(app_meta, "access_level", lambda: 1)
    assert cell_notes.can_edit(n) and cell_notes.can_delete(n)
    monkeypatch.setattr(app_meta, "current_user", {"id": 8})
    assert not cell_notes.can_edit(n) and not cell_notes.can_delete(n)
    monkeypatch.setattr(app_meta, "access_level", lambda: 4)  # superuser may delete, not edit
    assert not cell_notes.can_edit(n) and cell_notes.can_delete(n)


class _Screen(QWidget):
    _recycle_preview = None
    _series_pk = 311
    _trial_ids = [10, 11]
    _trial_labels = ["V1", "V2"]


def _menu_texts(screen, model, row, col):
    from ui import cell_notes_ui
    menu = QMenu()
    cell_notes_ui.add_cell_note_actions(screen, model, model.index(row, col), menu)
    return [a.text() for a in menu.actions()]


def test_cell_menu_add_or_show(app, monkeypatch):
    from db import cell_notes
    monkeypatch.setattr(cell_notes, "available", lambda: True)
    scr, m = _Screen(), _model()
    m._notes_by_key = cell_notes.by_cell([_note(1, "tblTrial", 10, "AirPressure")])
    assert _menu_texts(scr, m, 1, 1) == ["Notes (1)…"]
    assert _menu_texts(scr, m, 1, 2) == ["Add note…"]
    assert _menu_texts(scr, m, 2, 2) == []             # cell without record
    scr._recycle_preview = object()                     # read-only preview: read, never add
    assert _menu_texts(scr, m, 1, 1) == ["Notes (1)…"]
    assert _menu_texts(scr, m, 1, 2) == []
    monkeypatch.setattr(cell_notes, "available", lambda: False)  # no table / offline
    scr._recycle_preview = None
    assert _menu_texts(scr, m, 1, 1) == []


def test_dialog_adds_note_with_ctrl_enter(app, monkeypatch):
    from PySide6.QtTest import QTest
    from db import cell_notes
    from ui import cell_notes_ui
    monkeypatch.setattr(cell_notes, "available", lambda: True)
    added, reloaded = [], []
    monkeypatch.setattr(cell_notes, "add_note",
                        lambda t, r, f, text, trial_id=None, series_id=None: added.append((t, r, f, text, series_id)))
    monkeypatch.setattr(cell_notes_ui, "reload_notes", lambda screen: reloaded.append(screen))
    scr = _Screen()
    dlg = cell_notes_ui.CellNotesDialog(scr, "V1 · Air Pressure", ("tblTrial", 10, "AirPressure"), lambda: [])
    dlg.show()
    dlg.txt.setPlainText("  Spool had knots  ")
    QTest.keyClick(dlg.txt, Qt.Key_Return, Qt.ControlModifier)
    assert added == [("tblTrial", 10, "AirPressure", "Spool had knots", 311)]
    assert reloaded == [scr] and dlg.txt.toPlainText() == ""
    dlg._add()  # empty box -> nothing
    assert len(added) == 1
    dlg.close()


# ── Smart Chart (ui/report_queries.attach_notes, PDF list) ──────────────
def test_attach_notes_maps_axes_and_trial_notes(monkeypatch):
    import db.connection as conn
    from db import cell_notes
    from ui import report_queries
    monkeypatch.setattr(cell_notes, "available", lambda: True)
    at = datetime.datetime(2026, 10, 30, 7, 28)
    db_notes = [
        {"ID": 1, "TableName": "tblLaborStatimatM", "FieldName": "Tenacity", "TrialID": 10, "NoteText": "knots",
         "CreatedAt": at, "UserName": "Ann Lab"},
        {"ID": 2, "TableName": "tblTrial", "FieldName": "AirPressure", "TrialID": 10, "NoteText": "gauge",
         "CreatedAt": at, "UserName": ""},
        {"ID": 3, "TableName": "tblTrial", "FieldName": "", "TrialID": 11, "NoteText": "cleaned",
         "CreatedAt": at, "UserName": "Bo"},
        {"ID": 4, "TableName": "tblLaborTiter", "FieldName": "Titer", "TrialID": 10, "NoteText": "no axis",
         "CreatedAt": at, "UserName": "Bo"},
    ]
    monkeypatch.setattr(conn, "fetch_all", lambda sql, params=None: db_notes)
    axes = [{"key": "tenacity", "main_table": "tbllaborstatimatds", "alt_table": "tbllaborstatimatm",
             "field": "Tenacity"},
            {"key": "air_pressure", "main_table": "tbltrial", "alt_table": None, "field": "AirPressure"}]
    rows = [{"trial_id": 10}, {"trial_id": 11}, {"trial_id": -5}]
    report_queries.attach_notes(rows, axes)
    assert [n["t"] for n in rows[0]["_notes"]["tenacity"]] == ["knots"]   # alt table matches too
    assert rows[0]["_notes"]["air_pressure"][0] == {"id": 2, "t": "gauge", "by": "", "at": "30.10.2026"}
    assert "_tnotes" not in rows[0] and set(rows[0]["_notes"]) == {"tenacity", "air_pressure"}
    assert [n["t"] for n in rows[1]["_tnotes"]] == ["cleaned"] and "_notes" not in rows[1]
    assert "_notes" not in rows[2] and "_tnotes" not in rows[2]


def test_attach_notes_without_table_does_nothing(monkeypatch):
    from db import cell_notes
    from ui import report_queries
    monkeypatch.setattr(cell_notes, "available", lambda: False)
    rows = [{"trial_id": 10}]
    report_queries.attach_notes(rows, [])
    assert rows == [{"trial_id": 10}]


def test_pdf_value_notes_text():
    from ui.screen_report import value_notes_text
    txt = value_notes_text([
        {"trial": "V7", "what": "Tenacity", "t": " knots ", "by": "Ann Lab", "at": "30.10.2026"},
        {"trial": "V9", "what": "whole trial", "t": "cleaned", "by": "", "at": ""},
    ])
    assert txt.split("\n") == ["V7 · Tenacity: knots (Ann Lab, 30.10.2026)", "V9 · whole trial: cleaned"]
