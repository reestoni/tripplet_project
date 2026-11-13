"""db/series_save.py - the Qt-free save logic of Show Experiment (shared with
the web app). No DB: the write helpers are replaced by recorders.
(The desktop path was compared statement by statement before/after the move
on dev_local series; one real round trip on dev_local, restored afterwards.)"""
import os
import subprocess
import sys

import pytest

from db import change_log, plausibility, series_save as ss
from db.series_tables import CellBinding, GroupCellBinding

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_imports_without_pyside6():
    code = (
        "import sys\n"
        "class B:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name.split('.')[0] == 'PySide6':\n"
        "            raise ImportError('blocked')\n"
        "sys.meta_path.insert(0, B())\n"
        "import db.series_save, db.plausibility\n"
        "print('ok')\n")
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "ok"


# ---------------------------- normalize ----------------------------

@pytest.mark.parametrize("rule, text, out", [
    (None, "  abc ", "abc"), (None, None, ""), ("onlyDoubles", "", ""),
    ("onlySZ", "s z", "SZ"), ("onlySZ", "x", None),
    ("onlyInteger", "007", "7"), ("onlyInteger", "-3", "-3"), ("onlyInteger", "1.5", None),
    ("onlyDoubles", "3,50", "3.5"), ("onlyDoubles", "4.0", "4"), ("onlyDoubles", ",5", "0.5"),
    ("onlyDoubles", "1e3", None), ("double", "2,25", "2.25"),
    ("dropdown:tblDTYProcess", 5, "5"), ("hidden", " x ", "x"),
])
def test_normalize_value(rule, text, out):
    assert ss.normalize_value(rule, text) == out


@pytest.mark.parametrize("title, text, out", [
    ("Air Pressure (bar)", "3,456", None),     # max. 2 decimals
    ("Air Pressure (bar)", "3,40", "3.4"),
    ("Air Pressure (bar)", "4", "4"),
    ("Air Pressure (bar)", "", ""),
    ("Speed", "3,456", "3.456"),
])
def test_normalize_input_air_pressure(title, text, out):
    assert ss.normalize_input("onlyDoubles", title, text) == out


@pytest.mark.parametrize("kind, value, out", [
    ("jet", 12, "12"), ("jet", "12", "12"), ("jet", None, ""), ("jet", " ", ""), ("jet", "abc", None),
    ("housing", 3, "3"), ("housing", None, ""), ("housing", "abc", "abc"),   # housing keeps odd text (as before)
])
def test_normalize_input_id_rows(kind, value, out):
    assert ss.normalize_input("onlyInteger", "Jet", value, kind=kind) == out


# ---------------------------- save_cells ----------------------------

@pytest.fixture
def rec(monkeypatch):
    calls = {"sql": [], "log": [], "dy": []}

    def _exec(sql, params=()):
        calls["sql"].append((sql, list(params)))
        return 1

    monkeypatch.setattr(ss, "execute_non_query", _exec)
    monkeypatch.setattr(ss, "get_columns_map", lambda t: {"user": "User", "timestamp": "Timestamp"}
                        if t.lower().startswith("tbllabor") else {})
    monkeypatch.setattr(change_log, "table_ready", lambda: True)
    monkeypatch.setattr(change_log, "read_current", lambda tb, fd, ids: {
        int(i): {"value": "old", "trial_id": 99} for i in ids})
    monkeypatch.setattr(change_log, "log_changes",
                        lambda entries, series_id=None, source="edit", **kw: calls["log"].append(
                            (list(entries), series_id, source, kw)))
    import db.dy_ratio as dy
    monkeypatch.setattr(dy, "recompute", lambda ids: calls["dy"].append(set(ids)))
    return calls


def test_save_cells_sql(rec):
    edits = [
        (CellBinding("tblTrial", "ID", 5, "AirPressure"), "3.5"),
        (CellBinding("tblTrial", "ID", 5, "JetID"), ""),
        (CellBinding("tblLaborTiter", "ID", 7, "Titer"), "167.3"),
        (CellBinding("tblLaborTiter", "ID", 8, "Titer"), ""),
        (GroupCellBinding("tblTrialSettings", "ID", [11, 12], "YarnTensionT1"), " 4 "),
        (CellBinding("tblLaborJetAirConsumption", "ID", 3, "AirConsumption"), "100"),
        (None, "ignored"),
    ]
    n = ss.save_cells(edits, user={"id": 42}, series_id=9, unit_scale=50.0, unit_field="AirConsumption")
    assert n == 7
    assert rec["sql"] == [
        ("UPDATE tblTrial SET [AirPressure] = ? WHERE [ID] = ?", ["3.5", 5]),
        ("UPDATE tblTrial SET [JetID] = NULL WHERE [ID] = ?", [5]),
        ("UPDATE tblLaborTiter SET [Titer] = ?, [User] = ?, [Timestamp] = NOW() WHERE [ID] = ?", ["167.3", 42, 7]),
        ("UPDATE tblLaborTiter SET [Titer] = NULL, [User] = ?, [Timestamp] = NOW() WHERE [ID] = ?", [42, 8]),
        ("UPDATE tblTrialSettings SET `YarnTensionT1` = ? WHERE `ID` = ?", ["4", 11]),
        ("UPDATE tblTrialSettings SET `YarnTensionT1` = ? WHERE `ID` = ?", ["4", 12]),
        ("UPDATE tblLaborJetAirConsumption SET [AirConsumption] = ?, [User] = ?, [Timestamp] = NOW() WHERE [ID] = ?",
         ["2.0", 42, 3]),   # 100 l/min / 50 = 2.0 (stored unit)
    ]
    entries, series_id, source, kw = rec["log"][0]
    assert series_id == 9 and source == "edit" and kw == {}   # desktop: log user from app_meta
    by_cell = {(e["table"], e["row_id"], e["field"]): e for e in entries}
    assert by_cell[("tblTrial", 5, "AirPressure")]["trial_id"] == 5          # tblTrial: the row is the trial
    assert by_cell[("tblLaborTiter", 7, "Titer")]["trial_id"] == 99
    assert by_cell[("tblTrialSettings", 12, "YarnTensionT1")]["new"] == "4"
    assert by_cell[("tblLaborJetAirConsumption", 3, "AirConsumption")]["new"] == "2.0"
    assert rec["dy"] == [{11, 12}]


def test_save_cells_log_user_and_cache(rec):
    cache = {}
    ss.save_cells([(CellBinding("tblLaborX", "ID", 1, "A"), "1")], user=5, audit_cache=cache, log_user_id=5)
    assert cache == {"tblLaborX": ("User", "Timestamp")}
    assert rec["log"][0][3] == {"user_id": 5}
    assert rec["sql"][0][1] == ["1", 5, 1]


def test_save_cells_error_propagates_without_log(rec, monkeypatch):
    def boom(sql, params=()):
        raise RuntimeError("db down")
    monkeypatch.setattr(ss, "execute_non_query", boom)
    with pytest.raises(RuntimeError):
        ss.save_cells([(CellBinding("tblTrial", "ID", 1, "YarnTensionT1"), "1")])
    assert rec["log"] == [] and rec["dy"] == []


def test_stamp_trial_ids():
    edits = [(CellBinding("tblTrial", "ID", 1, "YarnTensionAfterJet"), "3"),
             (CellBinding("tblTrial", "ID", 2, "W3Tension"), "3"),
             (CellBinding("tblTrial", "ID", 3, "AirPressure"), "3"),
             (CellBinding("tblTrialSettings", "ID", 4, "YarnTensionBeforeJet"), "3")]
    assert ss.stamp_trial_ids(edits) == {1, 2}


# ---------------------------- Itemat recompute ----------------------------

def test_recompute_itemat_intermingling(monkeypatch):
    from db import series_tables as st
    # 2 info rows on top, columns: IP0 = 50 / missing
    grid = {(2 + st.ITEMAT_ROW_IP0, 0): "50", (2 + st.ITEMAT_ROW_STAB_START, 0): "90",
            (2 + st.ITEMAT_ROW_STAB_START + 1, 0): "80", (2 + st.ITEMAT_ROW_STAB_START, 1): "70"}
    binds = {(2 + st.ITEMAT_ROW_STAB_START, 0): CellBinding("tblLaborItematLab", "ID", 101, "Stability (%)"),
             (2 + st.ITEMAT_ROW_STAB_START + 1, 0): CellBinding("tblLaborItematLab", "ID", 102, "Stability (%)")}
    writes = []
    monkeypatch.setattr(ss, "fetch_all", lambda sql, p: [{"ID": 101, "V": "45.0"}, {"ID": 102, "V": None}])
    monkeypatch.setattr(ss, "execute_non_query", lambda sql, p: writes.append((sql, p)) or 1)
    n = ss.recompute_itemat_intermingling(lambda r, c: grid.get((r, c)), lambda r, c: binds.get((r, c)),
                                          2, [0.6, 1.0], row_offset=2)
    assert n == 1   # 101 already 45.0 -> unchanged
    assert writes == [("UPDATE tblLaborItematLab SET [Intermingling Points (FP/m)] = ? WHERE ID = ?", [40.0, 102])]


# ---------------------------- plausibility ----------------------------

def test_plausibility_check(monkeypatch):
    monkeypatch.setattr(plausibility, "ranges_for_machine", lambda mid: {
        ("tbltrial", "airpressure"): plausibility.range_of([3.0, 4.0, 5.0] * 20)})
    items = [
        {"binding": CellBinding("tblTrial", "ID", 1, "AirPressure"), "value": "35", "labels": ["V2"],
         "title": "Air Pressure (bar)", "row": 3, "col": 1},
        {"binding": CellBinding("tblTrial", "ID", 2, "AirPressure"), "value": "4.5", "labels": ["V3"],
         "title": "Air Pressure (bar)"},
        {"binding": CellBinding("tblTrial", "ID", 2, "SpeedShaft2"), "value": "9999", "labels": ["V3"],
         "title": "Speed"},   # no range known -> not checked
    ]
    out = plausibility.check(items, 1)
    assert len(out) == 1
    assert out[0]["row"] == 3 and out[0]["col"] == 1
    assert out[0]["text"] == "V2 · Air Pressure (bar): 35   (usually 3 – 5)"
    assert plausibility.check([], 1) == []


# ---------------------------- fill row ----------------------------

SPECS = [{"trial_id": 10, "ply": "Ply 1"}, {"trial_id": 10, "ply": "Ply 2"},
         {"trial_id": 11, "ply": "Ply 1"}, {"trial_id": 11, "ply": "Ply 2"},
         {"trial_id": 12, "ply": "Ply 1"}]


def test_fill_columns_and_options():
    assert ss.unique_trial_ids(SPECS) == [10, 11, 12]
    assert ss.fill_n_trials(SPECS, 5) == 3
    assert ss.fill_n_trials([], 4) == 4
    assert ss.fill_range_columns(SPECS, 2, 3) == [2, 3, 4]
    assert ss.fill_range_columns(SPECS, 3, 2) == [2, 3, 4]            # reversed range
    assert ss.fill_range_columns(SPECS, 1, 3, {"Ply 2"}) == [1, 3]
    assert ss.fill_range_columns([], 2, 3) == [1, 2]                  # no col_specs: data columns
    assert ss.fill_kind(0, has_housing_list=True, has_jets_list=True) == ss.FILL_HOUSING
    assert ss.fill_kind(1, has_housing_list=True, has_jets_list=False) == ss.FILL_TEXT
    assert ss.fill_kind(7, has_housing_list=True, has_jets_list=True, dropdown_rows={7: {}}) == ss.FILL_DROPDOWN
    ts = CellBinding("tblTrialSettings", "ID", 1, "X")
    assert ss.fill_ply_labels(SPECS, ss.FILL_DROPDOWN) == ["Ply 1", "Ply 2"]
    assert ss.fill_ply_labels(SPECS, ss.FILL_TEXT, data_row=8, titles_fixed_count=5, first_binding=ts) == ["Ply 1", "Ply 2"]
    assert ss.fill_ply_labels(SPECS, ss.FILL_TEXT, data_row=3, titles_fixed_count=5, first_binding=ts) == []
    assert ss.fill_ply_labels(SPECS, ss.FILL_TEXT, data_row=8, titles_fixed_count=5,
                              first_binding=CellBinding("tblTrial", "ID", 1, "X")) == []
    assert ss.fill_ply_labels(SPECS[::2], ss.FILL_TEXT, data_row=8, titles_fixed_count=5, first_binding=ts) == []
    assert ss.fill_ply_labels(SPECS, ss.FILL_JET) == []
    assert ss.fill_default([None, "", " ", "4", "5"]) == "4"


def test_fill_range_edits():
    b = [CellBinding("tblTrialSettings", "ID", i, "Shaft1_DR") for i in range(5)]
    cells = [("1.5", b[0]), ("1.5", b[1]), ("12.5", b[2]), ("", None), ("1.5", b[4])]
    out = ss.fill_range_edits(SPECS, 1, 3, "12,5", cells=cells, rule="onlyDoubles", row_title="Shaft 1 DR")
    # col 2 already 12.5 (unchanged), col 3 has no binding
    assert [(c, bb.id_value, v) for c, bb, v in out] == [(0, 0, "12.5"), (1, 1, "12.5"), (4, 4, "12.5")]
    assert ss.fill_range_edits(SPECS, 1, 3, "abc", cells=cells, rule="onlyDoubles", row_title="X") == []
    assert ss.fill_range_edits(SPECS, 1, 3, "1", cells=cells, rule=None, row_title="X", read_only=True) == []
    jets = ss.fill_range_edits(SPECS, 2, 2, 17, cells=cells, rule=None, row_title="Jet", kind=ss.FILL_JET,
                               selected_plies={"Ply 2"})   # plies ignored for jet/housing
    assert [(c, v) for c, _b, v in jets] == [(2, "17")]   # col 3 has no binding


# ---------------------------- save_series_edits ----------------------------

def test_save_series_edits_order(monkeypatch):
    seq = []
    monkeypatch.setattr(ss, "save_cells", lambda edits, **kw: seq.append(("save", [v for _b, v in edits],
                                                                          kw.get("unit_scale"))) or len(edits))
    monkeypatch.setattr(ss, "stamp_trial_timestamp", lambda tid, user=None: seq.append(("stamp", tid)) or 1)

    class P:
        extra = {"tensions": [0.6]}
        cells = []

    from db import series_tables as st
    monkeypatch.setattr(st, "load_trials", lambda sid: type("T", (), {"labels": ["V1"]})())
    monkeypatch.setattr(st, "build_itemat", lambda t: P())
    monkeypatch.setattr(ss, "recompute_itemat_intermingling",
                        lambda gv, gb, n, tensions, off: seq.append(("recompute", n, tensions, off)) or 2)

    def failing(edits, **kw):
        raise RuntimeError("x")

    res = ss.save_series_edits({"id": 3}, 77, {
        "model_machine": [(CellBinding("tblTrial", "ID", 8, "YarnTensionAfterJet"), "5")],
        "itemat": [(CellBinding("tblLaborItematLab", "ID", 1, "Stability (%)"), "90")],
        "jet_air": [(CellBinding("tblLaborJetAirConsumption", "ID", 2, "AirConsumption"), "60")],
    }, unit_scales={"jet_air": (16.0, "AirConsumption")})
    assert seq == [("save", ["5"], 1.0), ("save", ["90"], 1.0), ("recompute", 1, [0.6], 0),
                   ("save", ["60"], 16.0), ("stamp", 8)]
    assert res == {"saved": 1 + 3 + 1 + 1, "stamped": 1, "failed": {},
                   "per_model": {"model_machine": 1, "itemat": 3, "jet_air": 1}}

    monkeypatch.setattr(ss, "save_cells", failing)
    res = ss.save_series_edits(None, 1, {"titer": [(None, "1")]})
    assert res["failed"] == {"titer": "x"} and res["saved"] == 0


def test_multi_ply_differs():
    ts = CellBinding("tblTrialSettings", "ID", 1, "X")
    specs = [{"trial_id": 1, "ply": "Ply 1"}, {"trial_id": 1, "ply": "Ply 2"}, {"trial_id": 2, "ply": "Ply 1"}]
    same = [["1", " 1 ", "3"]]
    assert ss.multi_ply_differs(specs, 1, lambda r, c: ts, lambda r, c: same[r][c].strip()) is False
    assert ss.multi_ply_differs(specs, 1, lambda r, c: ts, lambda r, c: ["1", "2", "3"][c]) is True
    assert ss.multi_ply_differs(specs, 1, lambda r, c: CellBinding("tblTrial", "ID", 1, "X"),
                                lambda r, c: ["1", "2", "3"][c]) is False


def test_itemat_recompute_skips_values_equal_after_db_rounding(monkeypatch):
    """2026-11-13: computed 106.6316 vs stored 106.63 rewrote every IP(t) on every save."""
    from db import series_save as ss
    monkeypatch.setattr(ss, "fetch_all", lambda sql, p=None: [{"ID": 1, "V": 106.63}, {"ID": 2, "V": 50.0}])
    writes = []
    monkeypatch.setattr(ss, "execute_non_query", lambda sql, p: writes.append(p) or 1)
    n = ss._write_if_changed("tblLaborItematLab", "Intermingling Points (FP/m)", {1: 106.6316, 2: 50.125}, [1, 2])
    assert n == 1 and writes == [[50.13, 2]]          # 1 unchanged after rounding; 2 rounded half up
    assert ss.round_db(2.675) == 2.68 and ss.round_db(-1.005) == -1.01
