# tests/test_smart_dashboard_distinct.py
"""Aggregation "Count (distinct)" (Nutzerwunsch 2026-11-05): how many different jets, yarns … ."""
import pytest

from db import trial_explorer as te
from ui import smart_dashboard_engine as en

# machine / jet per trial; trial 6 has no jet recorded
ROWS = {1: ("AFK", "S315"), 2: ("AFK", "P212"), 3: ("AFK", "S315"), 4: ("SSM", "P212"), 5: ("SSM", "HE12"),
        6: ("SSM", "")}
FPM = {1: 100.0, 2: 110.0, 3: 100.0, 4: 90.0, 5: 130.0}


@pytest.fixture
def ds():
    ply = te.Ply("Ply 1", "Core", {"yarn_material": "PES", "yarn_type": "DTY", "yarn_endtiter": 76, "yarn_titer": None,
                                   "yarn_filaments": 36, "yarn_dpf": None, "yarn_name": "PES 76", "yarn_use": "Core"})
    trials = [te.Trial(id=i, nr=i, series_id=1, exp_pk=7, experiment="2026-01-001", series="S1", machine=m,
                       jet=j, year="2026", plies=[ply]) for i, (m, j) in ROWS.items()]
    cat = te.YARN_FIELDS + te.GENERAL_FIELDS + [te.Field("fpm", "FP/m", "FP/m", "Lab", "num")]
    return te.TrialDataset(cat, trials=trials, loader=lambda f: dict({"fpm": FPM}.get(f.key, {})))


def _v(t, **wells):
    return {"id": "v1", "type": t, "w": 6, "title": "", "agg": en.DISTINCT, "wells": wells}


def test_card_counts_different_jets(ds):
    r = en.compute_visual(ds, _v("kpi", value="jet"), [])
    assert r["kind"] == "kpi" and r["value"] == "3" and r["raw"] == 3.0     # empty jet does not count
    assert r["title"] == "Count of Jet (distinct)" and "6 trials" in r["sub"]


def test_card_follows_filters(ds):
    r = en.compute_visual(ds, _v("kpi", value="jet"), [{"key": "machine", "values": ["AFK"]}])
    assert r["value"] == "2"


def test_card_on_number_field_and_without_value(ds):
    assert en.compute_visual(ds, _v("kpi", value="fpm"), [])["value"] == "4"     # 100, 110, 90, 130
    r = en.compute_visual(ds, _v("kpi"), [])
    assert r["value"] == "–" and "Value" in r["sub"]


def test_target_uses_the_count(ds):
    v = {**_v("kpi", value="jet"), "target": {"value": 5, "better": "higher"}}
    assert en.compute_visual(ds, v, [])["status"] == "bad"


def test_column_per_machine(ds):
    r = en.compute_visual(ds, _v("column", x="machine", value="jet"), [])
    tr = r["figure"]["data"][0]
    assert dict(zip(tr["x"], tr["y"])) == {"AFK": 2.0, "SSM": 2.0}


def test_matrix_and_pie(ds):
    r = en.compute_visual(ds, _v("matrix", rows="machine", cols="series", value="jet"), [])
    assert r["figure"]["data"][0]["z"] == [[2.0], [2.0]]
    r = en.compute_visual(ds, _v("pie", legend="machine", value="jet"), [])
    assert dict(zip(r["figure"]["data"][0]["labels"], r["figure"]["data"][0]["values"])) == {"AFK": 2.0, "SSM": 2.0}


def test_stack_and_radar_ignore_distinct(ds):
    v = _v("stack", values=["fpm"])
    r = en.compute_visual(ds, v, [])
    assert r["kind"] == "plotly"          # falls back to average, no crash
    assert en.DISTINCT in en.AGGS and en.DISTINCT not in en.COUNT_AGGS


# ── Table "One row per value" (Nutzerwunsch 2026-11-05: which are the jets?) ──
def _t(*cols, **kw):
    return {"id": "t1", "type": "table", "w": 6, "title": "", "group": True, "wells": {"columns": list(cols)}, **kw}


def test_grouped_table_lists_the_jets(ds):
    r = en.compute_visual(ds, _t("jet"), [])
    assert r["kind"] == "table" and r["grouped"] and r["title"] == "Jet"
    assert r["head"] == ["Jet", "Trials", "Series"]
    assert [row[1:] for row in r["rows"]] == [["HE12", "1", "1"], ["P212", "2", "1"], ["S315", "2", "1"]]
    assert "1 trials without Jet" in r["note"] and "raw" not in r
    # as many rows as the distinct card counts
    assert len(r["rows"]) == int(en.compute_visual(ds, _v("kpi", value="jet"), [])["value"])


def test_grouped_table_filters_numbers_and_sort(ds):
    r = en.compute_visual(ds, _t("jet", "fpm", fmt={"tsort": {"key": "fpm", "dir": "desc"}}),
                          [{"key": "machine", "values": ["AFK"]}])
    assert r["head"] == ["Jet", "FP/m (average)", "Trials", "Series"]
    assert [row[1:3] for row in r["rows"]] == [["P212", "110"], ["S315", "100"]]
    r = en.compute_visual(ds, _t("jet", fmt={"tsort": {"key": "__trials", "dir": "desc"}}), [])
    assert [row[1] for row in r["rows"]][-1] == "HE12"


def test_grouped_table_two_fields_and_rules(ds):
    rule = {"key": "jet", "op": "=", "a": "S315", "colour": "green"}
    r = en.compute_visual(ds, _t("machine", "jet", fmt={"rules": [rule]}), [])
    assert [row[1:3] for row in r["rows"]] == [["AFK", "P212"], ["AFK", "S315"], ["SSM", "HE12"],
                                               ["SSM", "P212"], ["SSM", "(none)"]]
    assert r["cellbg"][1][1] == en.RULE_COLOURS["green"] and r["cellbg"][0][1] == ""


def test_grouped_table_without_text_field_and_excel(ds):
    r = en.compute_visual(ds, _t("fpm"), [])
    assert not r.get("grouped") and "text field" in r["note"]
    title, head, rows = en.visual_table(ds, _t("jet", "fpm"), [])
    assert head == ["Jet", "FP/m (average)", "Trials", "Series"]
    assert rows[0] == ["HE12", 130.0, 1, 1]
    assert en.compute_visual(ds, {**_t("jet"), "group": False}, [])["head"][:2] == ["Trial", "Series"]
