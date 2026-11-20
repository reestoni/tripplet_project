"""Copy trials dialog (ui/copy_trials_dialog.py): field list, value
validation, copy order and editing of copied values. No DB needed."""
import pytest
from PySide6.QtCore import Qt

from ui import copy_trials_dialog as ctd


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


TRIAL_COLS = {c.lower(): c for c in [
    "ID", "HousingID", "JetID", "JetPlate", "AirPressure", "SpeedShaft2", "Shaft2x_OF",
    "Shaft3", "YarnTensionBeforeJet", "YarnTensionAfterJet", "Shaft2Speed", "TensionAfterJetInside",
]}


def _fields(machine_fields, has_groups=False):
    return ctd.build_copy_fields(machine_fields, TRIAL_COLS, {}, [(1, "S+ 1.2"), (2, "P142")],
                                 [(5, "HN")], has_groups)


@pytest.mark.parametrize("rule, text, expected", [
    ("air", "5,5", "5.5"), ("air", "6", "6"), ("air", "5.555", None), ("air", "abc", None),
    ("onlyDoubles", "2,25", "2.25"), ("onlyInteger", "3", "3"), ("onlyInteger", "3.5", None),
    ("onlySZ", "z", "Z"), (None, " free text ", "free text"), ("onlyDoubles", "", ""),
])
def test_normalize_value(rule, text, expected):
    assert ctd.normalize_value(rule, text) == expected


def test_summary_values_have_units():
    fields = {f.label: f for f in _fields([
        {"OriginalName": "SpeedShaft2", "FieldName": "Speed Shaft 2 (m/min)", "StorageTable": "tbltrial"},
        {"OriginalName": "Shaft2x_OF", "FieldName": "Shaft 2x (OF%)", "StorageTable": "tbltrial"},
        {"OriginalName": "Shaft3", "FieldName": "Shaft 3 (%)", "StorageTable": "tbltrial"},
        {"OriginalName": "OF", "FieldName": "OF%", "StorageTable": "tbltrialsettings"},
    ], has_groups=True)}
    sv = ctd.summary_value
    assert sv(fields["Jet"], 2) == "P142"
    assert sv(fields["Jet Plate Number"], 1) == "Plate Number 1"
    assert sv(fields["Air Pressure (bar)"], 0.8) == "0.8 bar"
    assert sv(fields["Speed Shaft 2 (m/min)"], 550) == "550 m/min"
    assert sv(fields["Shaft 2x (OF%)"], 4) == "4% OF"
    assert sv(fields["Shaft 3 (%)"], 2.5) == "2.5%"
    assert sv(fields["OF Core (%)"], 24) == "24% OF Core"
    assert sv(fields["OF Effect (%)"], 12) == "12% OF Effect"
    assert sv(fields["Air Pressure (bar)"], None) == ""


def test_dty_fields_skip_tensions_and_defaults_first():
    mf = [
        {"OriginalName": "Shaft3", "FieldName": "Shaft 3 (%)", "StorageTable": "tbltrial", "FieldFunction": "onlyDoubles"},
        {"OriginalName": "SpeedShaft2", "FieldName": "Speed Shaft 2 (m/min)", "StorageTable": "tbltrial", "FieldFunction": "onlyDoubles"},
        {"OriginalName": "YarnTensionBeforeJet", "FieldName": "Tension before Jet (cN)", "StorageTable": "tbltrial"},
        {"OriginalName": "Shaft2x_OF", "FieldName": "Shaft 2x (OF%)", "StorageTable": "tbltrial", "FieldFunction": "onlyDoubles"},
    ]
    labels = [(f.label, f.default) for f in _fields(mf)]
    assert ("Tension before Jet (cN)", True) not in labels and ("Tension before Jet (cN)", False) not in labels
    assert labels[:6] == [("Housing", True), ("Jet", True), ("Jet Plate Number", True),
                          ("Air Pressure (bar)", True), ("Speed Shaft 2 (m/min)", True), ("Shaft 2x (OF%)", True)]
    assert labels[-1] == ("Shaft 3 (%)", False)


def test_aty_gets_of_core_and_effect():
    mf = [
        {"OriginalName": "Shaft2Speed", "FieldName": "Speed (m/min)", "StorageTable": "tbltrial"},
        {"OriginalName": "TensionAfterJetInside", "FieldName": "Tension after Jet inside SB (cN)", "StorageTable": "tbltrial"},
        {"OriginalName": "OF", "FieldName": "OF%", "StorageTable": "tbltrialsettings"},
    ]
    fields = _fields(mf, has_groups=True)
    of = [f for f in fields if f.kind == "use_of"]
    assert [(f.label, f.use_id, f.default) for f in of] == [("OF Core (%)", 1, True), ("OF Effect (%)", 2, True)]
    assert not any("Tension" in f.label for f in fields)
    # without Core/Effect plies in the series there is nothing to change
    assert not [f for f in _fields(mf, has_groups=False) if f.kind == "use_of"]


def _dialog(order_row=False, copies=2):
    fields = _fields([{"OriginalName": "SpeedShaft2", "FieldName": "Speed", "StorageTable": "tbltrial",
                       "FieldFunction": "onlyDoubles"}])
    trials = [{"id": 11, "vno": 1}, {"id": 12, "vno": 2}, {"id": 13, "vno": 3}]
    src = {11: {"trial:AirPressure": 6, "trial:JetID": 1, "trial:SpeedShaft2": 600},
           12: {"trial:AirPressure": 6, "trial:JetID": 1, "trial:SpeedShaft2": 700},
           13: {"trial:AirPressure": 4, "trial:JetID": 2, "trial:SpeedShaft2": 800}}
    dlg = ctd.CopyTrialsDialog(None, trials, fields, src, next_number=4, preselected=[11, 12])
    dlg.spn_copies.setValue(copies)
    if order_row:
        dlg.rb_row.setChecked(True)
    return dlg, fields


def _col(dlg, label):
    return 2 + [f.label for f in dlg._fields].index(label)


def test_block_and_row_order(qapp):
    dlg, _ = _dialog()
    assert [s for s, _ in dlg.get_plan()] == [11, 12, 11, 12]
    assert dlg.btn_copy.text() == "Copy 4 trials"
    assert dlg.tbl.item(0, 0).text() == "V4" and dlg.tbl.item(3, 0).text() == "V7"
    dlg.rb_row.setChecked(True)
    assert [s for s, _ in dlg.get_plan()] == [11, 11, 12, 12]


def test_changed_values_end_up_in_plan_and_survive_rebuild(qapp):
    dlg, _ = _dialog()
    c_air = _col(dlg, "Air Pressure (bar)")
    dlg.tbl.item(1, c_air).setText("5,5")                     # 1st copy of V2
    dlg.tbl.cellWidget(2, _col(dlg, "Jet")).setCurrentIndex(2)  # 2nd copy of V1 -> P142
    plan = dlg.get_plan()
    assert plan[1] == (12, {"trial:AirPressure": "5.5"})
    assert plan[2] == (11, {"trial:JetID": 2})
    assert plan[0] == (11, {}) and plan[3] == (12, {})
    # ticking another trial rebuilds the table - the edits stay
    dlg.lst_trials.item(2).setCheckState(Qt.Checked)
    plan = dlg.get_plan()
    assert [s for s, _ in plan] == [11, 12, 13, 11, 12, 13]
    assert plan[1] == (12, {"trial:AirPressure": "5.5"}) and plan[3] == (11, {"trial:JetID": 2})
    # setting a value back to the source value removes the change
    dlg.tbl.item(1, c_air).setText("6")
    assert dlg.get_plan()[1] == (12, {})


def test_invalid_value_is_rejected(qapp, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    dlg, _ = _dialog(copies=1)
    item = dlg.tbl.item(0, _col(dlg, "Air Pressure (bar)"))
    item.setText("abc")
    assert item.text() == "6"
    assert dlg.get_plan()[0] == (11, {})


def test_lab_machine_choice(qapp):
    """Step 3 (Nutzerwunsch 2026-11-20): only lab machines of the chosen trials are offered, all ticked =
    None (= as before); unticked ones are left out of get_lab_tables()."""
    fields = _fields([{"OriginalName": "SpeedShaft2", "FieldName": "Speed", "StorageTable": "tbltrial"}])
    trials = [{"id": 11, "vno": 1}, {"id": 12, "vno": 2}]
    labs = [{"table": "tbllabortiter", "tab": "titer", "title": "Titer", "trials": [11, 12]},
            {"table": "tbllabordtyomat", "tab": "dtyomat", "title": "DTYoMat", "trials": [12]}]
    dlg = ctd.CopyTrialsDialog(None, trials, fields, {11: {}, 12: {}}, next_number=3, preselected=[11], labs=labs)
    titer, dtyomat = dlg._lab_checks["tbllabortiter"], dlg._lab_checks["tbllabordtyomat"]
    assert not titer.isHidden() and dtyomat.isHidden()          # V1 has no DTYoMat row
    assert dlg.get_lab_tables() is None
    dlg.lst_trials.item(1).setCheckState(Qt.Checked)
    assert not dtyomat.isHidden() and dtyomat.text() == "DTYoMat  (1 of 2)"
    dtyomat.setChecked(False)
    assert dlg.get_lab_tables() == ["tbllabortiter"]
