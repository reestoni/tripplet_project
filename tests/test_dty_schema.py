"""DTY process + schema (db/dty_process.py, ui/dty_stations.py,
ui/dty_schema_panel.py, FrozenFirstColumnTable.set_highlight)."""
import os

import pytest

from db import dty_process as dp
from ui import dty_stations as ds


def test_station_mapping_points_to_known_stations():
    known = {k for k, _l, _p in ds.STATIONS}
    assert set(ds.FIELD_STATION.values()) <= known
    assert all(k == k.lower() for k in ds.FIELD_STATION)
    assert ds.PREJET_KEYS <= set(ds.FIELD_STATION)
    assert ds.JET3_KEYS <= set(ds.FIELD_STATION)


def test_summary_keys_belong_to_their_station():
    from ui.dty_schema_panel import _SUMMARY
    for station, items in _SUMMARY.items():
        for key, _fmt in items:
            assert ds.station_of(key) == station, (station, key)


def test_rows_of_station():
    keys = ["housing", "jet", "position", "1stheatert1", None, "w3_jet", "customgroup"]
    assert ds.rows_of_station(keys, "mainjet") == [0, 1]
    assert ds.rows_of_station(keys, "heater1") == [3]
    assert ds.rows_of_station(keys, "jet3") == [5]
    assert ds.station_of("customgroup") is None


def _hidden(keys, matrix, flags=None):
    flags = flags if flags is not None else dp.flags_by_id(
        [{"ID": r[0], "UsesPreJet": r[5], "UsesJet3": r[6]} for r in dp.SEED])
    return ds.process_hidden_rows(keys, len(matrix[0]), lambda r, c: matrix[r][c],
                                  keys.index("dtyprocessid"), flags)


def test_prejet_and_jet3_rows_hidden_unless_needed():
    keys = ["dtyprocessid", "w0_w1_of", "preinterminglingjets", "w3_jet", "shaft3"]
    std = [["1", "1"], ["", ""], ["", ""], ["", ""], ["5", "5"]]
    assert _hidden(keys, std) == {1, 2, 3}
    before_heater = [["1", "5"], ["", ""], ["", ""], ["", ""], ["5", "5"]]
    assert _hidden(keys, before_heater) == {3}          # CL-D uses the pre-jet
    after_set = [["6", "1"], ["", ""], ["", ""], ["", ""], ["5", "5"]]
    assert _hidden(keys, after_set) == {1, 2}           # CL-E uses jet 3
    # a value is never hidden away, whatever the process says
    with_value = [["1", "1"], ["", "4.5"], ["", ""], ["", ""], ["5", "5"]]
    assert _hidden(keys, with_value) == {3}


def test_ply_path_and_merge():
    assert ds.ply_path(3, 1) == "elastane"
    assert ds.ply_path(4, 2, 6) == "elastane"           # elastane stored as FDY, material EL
    assert ds.ply_path(2, 2, 11) == "bypass"            # FDY effect yarn
    assert ds.ply_path(1, 1, 11) == "full"              # POY
    assert ds.ply_path(None, None) == "full"
    assert ds.merge_station(ds.BEFORE_HEATER_PROCESS_ID) == "lw1"
    assert ds.merge_station("1") == "lw2"
    assert ds.merge_station(None) == "lw2"


def test_seed_is_consistent():
    ids = [r[0] for r in dp.SEED]
    assert len(ids) == len(set(ids)) == 8
    by_code = {r[1]: r for r in dp.SEED}
    assert by_code["STD"][0] == dp.STANDARD_ID
    assert by_code["EL"][0] == dp.ELASTANE_ID
    assert by_code["CL-D"][0] == ds.BEFORE_HEATER_PROCESS_ID and by_code["CL-D"][5] == 1
    assert by_code["CL-E"][6] == 1
    assert ds.ELASTANE_MATERIAL_ID == dp.ELASTANE_MATERIAL_ID
    assert ds.ELASTANE_YARN_USE_ID == dp.ELASTANE_YARN_USE_ID


def test_default_process_for_existing_trials():
    assert dp.default_for_plies([(4, 11)]) == dp.STANDARD_ID
    assert dp.default_for_plies([(4, 11), (3, None)]) == dp.ELASTANE_ID
    assert dp.default_for_plies([(4, 11), (4, 6)]) == dp.ELASTANE_ID
    assert dp.default_for_plies([]) == dp.STANDARD_ID


def test_migration_refuses_outside_dev_local(monkeypatch):
    import importlib
    mig = importlib.import_module("tools.dty_process_migration")
    for mode in ("prod", "dev", "offline", ""):
        monkeypatch.setenv("TRIPPLET_MODE", mode)
        with pytest.raises(SystemExit):
            mig._guard()


def test_visible_stations():
    st = ds.visible_stations(show_pre=False, show_jet3=False, has_elastane=False)
    assert "lw0" not in st and "prejet" not in st and "jet3" not in st
    assert st[0] == "creel" and st[-1] == "winder"
    st = ds.visible_stations(True, True, False)
    assert st.index("lw0") < st.index("prejet") < st.index("lw1")
    assert st.index("setheater") < st.index("jet3") < st.index("lw3")


def test_frozen_table_highlight(qtbot=None):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QStandardItemModel
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ui.widgets.frozen_first_column_table import FrozenFirstColumnTable
    t = FrozenFirstColumnTable()
    m = QStandardItemModel(10, 5)
    t.setModel(m)
    t.set_highlight([2, 3], [1, 2])
    assert t.highlighted_rows() == {2, 3}
    assert t.top_left._hl_cols == frozenset({1, 2})
    t.grab()  # paints without error
    t.set_highlight(())
    assert t.highlighted_rows() == set()
    t.set_highlight([4])
    t.setModel(QStandardItemModel(3, 3))  # new model clears it
    assert t.highlighted_rows() == set()
    app.processEvents()


# ── merge topology ──────────────────────────────────────────────────────
def _p(no, path=None, auto="full", into=None, at=None):
    return {"no": no, "path": path, "auto_path": auto, "into": into, "at": at}


def test_topology_derived_like_before():
    t = ds.resolve_topology([_p(1), _p(2, auto="elastane")], process_id=2)
    assert t["main"] == 0 and not t["warnings"]
    assert t["plies"][1]["into"] == 0 and t["plies"][1]["at"] == "lw2" and t["plies"][1]["auto"]
    t = ds.resolve_topology([_p(1), _p(2, auto="bypass")], process_id=3)
    assert t["plies"][1]["at"] == "mainjet"
    t = ds.resolve_topology([_p(1), _p(2)], process_id=ds.BEFORE_HEATER_PROCESS_ID)
    assert t["plies"][1]["at"] == "lw1"


def test_topology_chain_of_four_plies():
    plies = [_p(1), _p(2, path="bypass", into=1, at="mainjet"),
             _p(3, into=1, at="lw2"), _p(4, into=3, at="lw1")]
    t = ds.resolve_topology(plies, process_id=5)
    assert t["main"] == 0 and not t["warnings"]
    assert [o["into"] for o in t["plies"]] == [None, 0, 0, 2]
    assert [o["at"] for o in t["plies"]] == [None, "mainjet", "lw2", "lw1"]
    assert t["plies"][1]["path"] == "bypass" and not t["plies"][3]["auto"]


def test_topology_main_is_the_target_not_simply_the_first_ply():
    t = ds.resolve_topology([_p(1, into=2, at="lw2"), _p(2)])
    assert t["main"] == 1 and t["plies"][0]["into"] == 1


def test_topology_warnings():
    t = ds.resolve_topology([_p(1), _p(2, into=7)])
    assert t["warnings"] and t["plies"][1]["into"] == 0          # unknown ply -> main
    t = ds.resolve_topology([_p(1), _p(2, into=3), _p(3, into=2)])
    assert any("circle" in w for w in t["warnings"])
    assert t["main"] == 0
    t = ds.resolve_topology([_p(1), _p(2, into=2)])
    assert any("itself" in w for w in t["warnings"])
    # Ply 3 wants to join Ply 2 at LW 3, but Ply 2 has ended at LW 2
    t = ds.resolve_topology([_p(1), _p(2, into=1, at="lw2"), _p(3, into=2, at="lw3")])
    assert any("already merged" in w for w in t["warnings"]) and t["plies"][2]["into"] == 0


def test_merge_rows_need_two_plies():
    keys = ["dtyprocessid", "dtyrouteid", "mergeintoply", "mergepointid", "shaft3"]
    one = [["1"], [""], [""], [""], ["5"]]
    hidden = ds.process_hidden_rows(keys, 1, lambda r, c: one[r][c], 0, {}, multi_ply=False)
    assert hidden == {1, 2, 3}
    assert ds.process_hidden_rows(keys, 1, lambda r, c: one[r][c], 0, {}, multi_ply=True) == set()


def test_lane_order_puts_children_below_their_target():
    from ui.dty_schema_panel import _lane_order
    plies = [{"path": "full", "into": None, "at": None},
             {"path": "elastane", "into": 0, "at": "lw2"},
             {"path": "full", "into": 3, "at": "lw1"},
             {"path": "full", "into": 0, "at": "lw2"}]
    assert _lane_order(plies, 0) == [0, 3, 2, 1]


def test_lookup_codes_are_stations():
    known = {k for k, _l, _p in ds.STATIONS}
    assert set(dp.MERGE_CODE.values()) <= known
    assert set(dp.ROUTE_CODE.values()) == {"full", "bypass", "elastane"}
    assert ds.MERGE_KEYS <= set(ds.FIELD_STATION)


def test_speeds_relative_to_lw2():
    sp = ds.speeds(600.0, of_2x=7, shaft3=5, winder=5.9)
    assert sp["lw2"] == 600
    assert abs(sp["lw2x"] - 558.0) < 1e-9
    assert abs(sp["lw3"] - 570.0) < 1e-9
    assert abs(sp["winder"] - 564.6) < 1e-9
    assert ds.speeds(None) == {} and ds.speeds(0) == {}
    assert ds.speeds(600.0)["lw3"] is None
    assert abs(ds.lw1_speed(600.0, 1.2) - 500.0) < 1e-9
    assert ds.lw1_speed(600.0, 0) is None and ds.lw1_speed(None, 1.2) is None


def test_lw0_speed_refers_to_lw1():
    assert abs(ds.lw0_speed(500.0, 3) - 500.0 / 0.97) < 1e-9
    assert ds.lw0_speed(500.0, None) is None and ds.lw0_speed(None, 3) is None
    assert ds.lw0_speed(500.0, 100) is None


def test_migration_targets_need_matching_mode(monkeypatch):
    import importlib
    mig = importlib.import_module("tools.dty_process_migration")
    monkeypatch.setenv("TRIPPLET_MODE", "dev_local")
    for target in ("prod", "dev", "nonsense"):
        with pytest.raises(SystemExit):
            mig._guard(target)
    assert mig.NEW_ONLY == 2


def test_new_only_fields_hidden_from_old_filters():
    """RDSetting 2 rows: shown by the new Machine Data filter, skipped by the
    filters older versions use (== 0 / == 1)."""
    rows = [{"RDSetting": 0}, {"RDSetting": 1}, {"RDSetting": 2}, {"RDSetting": None}]
    new_normal = [r for r in rows if int(r.get("RDSetting") or 0) in (0, 2)]
    old_normal = [r for r in rows if int(r.get("RDSetting") or 0) == 0]
    old_rd = [r for r in rows if int(r.get("RDSetting") or 0) == 1]
    assert {2} <= {r["RDSetting"] for r in new_normal}
    assert all(r["RDSetting"] != 2 for r in old_normal + old_rd)
