"""db/experiment_create.py - rules of Create Experiment / Add Trial Series / Add Lab Machines
(shared by ui/screen_create_experiment.py and the web app). Pure rules, no DB writes."""
from __future__ import annotations

import db.experiment_create as ec

ITEMAT = {"LMID": 3, "LMName": "Itemat Lab", "AddField": "Tension", "AddUnit": "cN/dtex",
          "Tbl": "tbllaboritematlab", "Src": "Tension", "RowMode": "PerTrial"}
TITER = {"LMID": 1, "LMName": "Titer", "AddField": "", "AddUnit": "", "Tbl": "tbllabortiter", "Src": "", "RowMode": "PerTrial"}
JETAIR = {"LMID": 14, "LMName": "Jet Air Consumption", "AddField": "AirPressure", "AddUnit": "bar",
          "Tbl": "tbllaborjetairconsumption", "Src": "AirPressure", "RowMode": "SeriesFreeform"}
OTHER = {"LMID": 7, "LMName": "Texturmat EKB", "AddField": "Temp", "AddUnit": "°C", "Tbl": "x", "Src": "Temp", "RowMode": "PerTrial"}


def vals(entries):
    return [e["AdditionalVal"] for e in entries]


def test_plies_same_yarn_same_ply():
    m = []
    for yarn in (5, 5, 6, 5):
        label, conflict = ec.ply_label_for(m, yarn)
        assert conflict is None
        m.append({"YarnID": yarn, "Ply": label, "Name": f"Y{yarn}"})
    assert [x["Ply"] for x in m] == ["Ply 1", "Ply 1", "Ply 3", "Ply 1"]
    # after removing a row: same rule again (desktop numbered 1..n before)
    assert ec.renumber_plies(m[1:]) == ["Ply 1", "Ply 2", "Ply 1"]
    assert ec.ply_label_for([], 9, ply_offset=2)[0] == "Ply 3"


def test_ply_conflict_in_list():
    m = [{"YarnID": 5, "Ply": "Ply 1", "Name": "A"}, {"YarnID": 6, "Ply": "Ply 2", "Name": "B"}]
    label, conflict = ec.ply_label_for(m, 7, ply_offset=-1)   # would land on Ply 2 (yarn B)
    assert label == "Ply 2" and conflict and conflict.code == "ply_conflict" and conflict.vars["yarn"] == "B"


def test_lab_itemat_baseline_and_tensions():
    new, msg = ec.plan_lab_entries(ITEMAT, "create", [], "", [0.3, 0.6])
    assert msg is None and vals(new) == [0.0, 0.3, 0.6]
    again, msg = ec.plan_lab_entries(ITEMAT, "create", new, "0.6", [0.3])
    assert msg is None and again == []
    own, _ = ec.plan_lab_entries(ITEMAT, "create", new, "1,5")
    assert vals(own) == [1.5]
    _, msg = ec.plan_lab_entries(ITEMAT, "create", [], "", [])
    assert msg.code == "lab_tension_missing"
    # add trials: Itemat always just the 0.0 baseline
    assert vals(ec.plan_lab_entries(ITEMAT, "addtrials", [], "", [0.3])[0]) == [0.0]
    assert not ec.can_delete_lab_entry(new, 0, {3: ITEMAT})
    assert ec.can_delete_lab_entry(new, 1, {3: ITEMAT})
    assert ec.can_delete_lab_entry(new[:1], 0, {3: ITEMAT})


def test_lab_other_kinds():
    assert vals(ec.plan_lab_entries(TITER, "create", [], "")[0]) == [None]
    t1 = ec.plan_lab_entries(TITER, "create", [], "")[0]
    assert ec.plan_lab_entries(TITER, "create", t1, "")[0] == []          # once per machine
    fr, msg = ec.plan_lab_entries(JETAIR, "create", [], "4, 5;6")
    assert msg is None and vals(fr) == [4.0, 5.0, 6.0] and all(e["RowMode"] == "SeriesFreeform" for e in fr)
    assert ec.plan_lab_entries(JETAIR, "create", [], "4, x")[1].code == "lab_csv_bad"
    assert ec.plan_lab_entries(JETAIR, "create", [], "")[1].code == "lab_csv_missing"
    o, msg = ec.plan_lab_entries(OTHER, "create", [], "180")
    assert msg is None and o[0]["AdditionalDisp"] == "180 °C"
    assert ec.plan_lab_entries(OTHER, "create", [], "")[1].code == "lab_value_missing"
    assert ec.plan_lab_entries(OTHER, "create", [], "1.234")[1].code == "lab_value_bad"
    assert [ec.lab_input(m, "create") for m in (ITEMAT, TITER, JETAIR, OTHER)] == ["itemat", "none", "csv", "value"]
    assert ec.lab_input(ITEMAT, "addtrials") == "none"


def test_lab_data_from_takes_tables_from_catalog():
    cat = {3: ITEMAT, 14: JETAIR}
    d = ec.lab_data_from([{"LMID": 3, "AdditionalVal": "0,3"}, {"LMID": 14, "AdditionalVal": 5}], cat)
    assert d[0]["TableName"] == "tbllaboritematlab" and d[0]["AdditionalVal"] == 0.3
    assert d[1]["RowMode"] == "SeriesFreeform"
    for bad in ([{"LMID": 99}], [{"LMID": 3, "AdditionalVal": "x"}]):
        try:
            ec.lab_data_from(bad, cat)
            raise AssertionError("expected ValueError")
        except ValueError:
            pass


def test_jet_rows_and_legacy_id():
    ok = {"JetID": 1, "HousingID": 2, "PlateList": "1,2,3", "Pressure": "4,5"}
    assert ec.check_jet(ok) is None
    assert ec.check_jet({**ok, "HousingID": None})
    assert ec.check_jet({**ok, "PlateList": "1,101"})
    assert ec.check_jet({**ok, "Pressure": "4.555"})
    assert ec.check_jet({**ok, "PlateList": ",".join(["1"] * 21)})
    assert ec.parse_legacy_id("2019-73-002") == ("2019", 7, 3, "002")
    assert ec.parse_legacy_id("2019-7-002") is None
    assert ec.experiment_label(2026, 7, 0, 6) == "2026-70-006"
    assert [ec.field_kind(f) for f in ("hidden", "dropdown:tblDisc", "OnlyInteger", "onlydoubles", "Only S Z", "")] == \
        ["hidden", "dropdown", "int", "double", "sz", "text"]


def test_spool_location_helpers():
    from db.yarn_spools import location_sort_key, tube_colour_candidates
    assert sorted(["E12", "", "E2", "A1"], key=location_sort_key) == ["A1", "E2", "E12", ""]
    assert tube_colour_candidates("Lila / white with print") == [["purple"], ["white", "with", "print"]]
    assert tube_colour_candidates("") == []


def test_legacy_id_taken_reads_experiments():
    from db.connection import fetch_all
    rows = fetch_all("SELECT Jahr AS Y, Produktgruppe AS PG, Bestellungstyp AS OT, Experimentnummer AS N "
                     "FROM tblExperimente WHERE Experimentnummer IS NOT NULL LIMIT 1")
    if not rows:
        return
    r = rows[0]
    assert ec.legacy_id_taken(r["Y"], r["PG"], r["OT"], r["N"])
    assert not ec.legacy_id_taken("1901", r["PG"], r["OT"], "999")
