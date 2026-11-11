"""ATY machine schema (ui/aty_stations.py, ui/aty_schema.py, shared panel
ui/dty_schema_panel.py)."""
import os

from ui import aty_stations as st


def test_station_mapping_points_to_known_stations():
    known = {k for k, _l, _p in st.STATIONS}
    assert set(st.FIELD_STATION.values()) <= known
    assert all(k == k.lower() for k in st.FIELD_STATION)
    assert set(st.SHORT) | {"creel"} == known


def test_summary_keys_belong_to_their_station():
    for station, items in st.SUMMARY.items():
        for key, _fmt in items:
            assert st.station_of(key) == station, (station, key)


def test_every_station_has_a_kb_target():
    from ui.kb_links import ATY_STATION_TARGET
    assert set(ATY_STATION_TARGET) == {k for k, _l, _p in st.STATIONS}


def test_aty_machine_fields_have_a_station():
    # Machine Data + R&D rows of the SSM DP2T on dev_local/prod (tblMachineFields)
    for key in ("shaft2speed", "of", "dr", "wettingheadid", "waterpressure", "temp0", "temp1",
                "setheatertemperature", "w3temperature", "w2tension", "w3tension", "w2", "w3",
                "yarntensionbeforejet", "tensionafterjetinside", "tensionafterjetoutside",
                "position1e", "positionw2", "atyhaloentrycore", "atyhaloentryeffect", "atyhaloexit",
                "housing", "jet", "jetplate", "airpressure", "yarnuse", "spool"):
        assert st.station_of(key), key
    assert st.station_of("comment") is None and st.station_of("customgroup") is None


def test_roles_and_lane_order():
    assert [st.role_of(u) for u in (1, 2, 3, 4, None, "x")] == \
        ["core", "effect", "elastane", None, None, None]
    # effect stored as ply 1 (common on dev_local): core still on top
    assert st.lane_order(["effect", "core"]) == [1, 0]
    assert st.lane_order(["core", "effect", "effect", "elastane"]) == [0, 1, 2, 3]
    assert st.lane_order([None, "elastane", "effect", "core"]) == [3, 2, 1, 0]


def test_speeds():
    assert abs(st.feed_speed(450.0, 12) - 504.0) < 1e-9     # KB: overfeed relative to take-off
    assert st.feed_speed(None, 12) is None and st.feed_speed(450.0, None) is None
    assert abs(st.draw_in_speed(504.0, 1.68) - 300.0) < 1e-9
    assert st.draw_in_speed(504.0, 0) is None


def test_filled_treats_zero_as_empty():
    assert not st.filled(0) and not st.filled("0.00") and not st.filled("") and not st.filled(None)
    assert st.filled("D13 K3") and st.filled(2.5)


def test_widget_paints_aty_path():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ui.dty_schema_panel import DTYSchemaWidget, kb_target
    w = DTYSchemaWidget()
    ply = lambda i, role, label: {"idx": i, "label": label, "ply": f"Ply {i + 1}", "pos": "",
                                  "yarn": "PES", "role": role,
                                  "values": {"feed": "504 m/min\nOF 12 %"}, "tips": {"feed": "OF: 12"}}
    w.set_path({"profile": "aty", "title": "V1", "process": "Air texturing",
                "plies": [ply(0, "effect", "Effect"), ply(1, "core", "Core")], "order": [1, 0],
                "stations": [s for s, _l, _p in st.STATIONS], "values": {"jet": "D13\n8 bar"},
                "tips": {}, "warnings": []})
    w.resize(1400, w.height())
    w.grab()
    hits = {(s, p) for _r, s, p in w._hits}
    assert {("feed", 0), ("feed", 1), ("jet", -1), ("winder", -1), ("creel", 1)} <= hits
    assert kb_target("jet", "aty")[0] == "aty_air_texturing"
    assert kb_target("jet") is None          # DTY has no station "jet"
    app.processEvents()
