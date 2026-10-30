"""Smart Chart dashboard ("wie Power BI", Nutzerwunsch 2026-10-30), engine
ui/smart_dashboard_engine.py with a hand-built dataset (no DB, no web).
End-to-end on dev_local verified: default page (4 cards, box, matrix,
trend), matrix click "AFK · 3.5 bar" filters the other visuals (163 trials),
table/box built from the page, Y well rejects list fields, double-click
opens Show Experiment, page saved in the view settings."""
import pytest

from db import trial_explorer as te
from ui import smart_dashboard_engine as en


def _ply(mat, endtiter):
    return te.Ply("Ply 1", "Core", {"yarn_material": mat, "yarn_type": "DTY", "yarn_endtiter": endtiter,
                                    "yarn_titer": None, "yarn_filaments": 36, "yarn_dpf": None,
                                    "yarn_name": f"{mat} {endtiter}", "yarn_use": "Core"})


@pytest.fixture
def ds():
    trials = []
    machines = ["AFK", "AFK", "AFK", "SSM", "SSM", "SSM"]
    for i, m in enumerate(machines, start=1):
        trials.append(te.Trial(id=i, nr=i, series_id=1 + i % 2, exp_pk=7, experiment="2026-01-001",
                               series=f"S{1 + i % 2}", machine=m, jet="S315", year="2026",
                               plies=[_ply("PES", 76)]))
    lab = {"fpm": {1: 100.0, 2: 110.0, 3: 120.0, 4: 80.0, 5: 90.0, 6: None},
           "air_pressure": {1: 3.0, 2: 3.0, 3: 3.5, 4: 3.0, 5: 3.5, 6: 3.5}}
    cat = te.YARN_FIELDS + te.GENERAL_FIELDS + [te.Field("fpm", "FP/m", "FP/m", "Lab", "num"),
                                                te.Field("air_pressure", "Air Pressure", "bar", "Machine", "num")]
    return te.TrialDataset(cat, trials=trials, loader=lambda f: {k: v for k, v in lab.get(f.key, {}).items()
                                                                 if v is not None})


def _v(t, **wells):
    return {"id": "v1", "type": t, "w": 6, "title": "", "agg": "avg", "wells": wells}


def test_aggregate():
    assert en.aggregate([1, 2, 3, 4], "avg") == 2.5
    assert en.aggregate([1, 2, 3, 4], "median") == 2.5
    assert en.aggregate([1, 5, 3], "max") == 5 and en.aggregate([1, 5, 3], "min") == 1
    assert en.aggregate([2, 4], "sd") == pytest.approx(1.4142, rel=1e-3)
    assert en.aggregate([], "avg") is None and en.aggregate([None, None], "count") == 2


def test_kpi_cards(ds):
    r = en.compute_visual(ds, {**_v("kpi"), "agg": "count"}, [])
    assert r["kind"] == "kpi" and r["value"] == "6" and r["title"] == "Trials"
    r = en.compute_visual(ds, _v("kpi", value="fpm"), [])
    assert r["value"] == "100" and r["unit"] == "FP/m" and "n = 5" in r["sub"]
    r = en.compute_visual(ds, {**_v("kpi", value="fpm"), "agg": "max"}, [])
    assert r["value"] == "120" and r["sub"].startswith("V3")


def test_table_and_empty(ds):
    r = en.compute_visual(ds, _v("table", columns=["machine", "fpm"]), [{"key": "machine", "values": ["SSM"]}])
    assert r["kind"] == "table" and r["head"] == ["Trial", "Series", "Machine", "FP/m (FP/m)"]
    assert [row[1] for row in r["rows"]] == ["V4", "V5", "V6"] and r["rows"][2][4] == ""
    assert en.compute_visual(ds, _v("box", x="machine"), [])["kind"] == "empty"
    assert en.compute_visual(ds, _v("matrix", rows="machine"), [])["kind"] == "empty"


def test_matrix_values_gaps_and_click(ds):
    v = _v("matrix", rows="machine", cols="air_pressure", value="fpm")
    r = en.compute_visual(ds, v, [])
    tr = r["figure"]["data"][0]
    assert tr["y"] == ["AFK", "SSM"] and tr["x"] == ["3", "3.5"]
    assert tr["z"] == [[105.0, 120.0], [80.0, 90.0]]
    flts = en.click_filters(ds, v, {"x": "3.5", "y": "AFK"})
    assert flts[0] == {"key": "machine", "values": ["AFK"]} and flts[1]["key"] == "air_pressure"
    assert ds.apply(flts).ids == [3]
    assert en.describe_cross(ds, flts) == "Machine: AFK · Air Pressure: 3.5 bar"


def test_chart_visual_and_click(ds):
    v = _v("box", x="machine", y="fpm")
    r = en.compute_visual(ds, v, [])
    assert r["kind"] == "plotly" and r["clickable"] and r["title"] == "FP/m by Machine"
    assert ds.apply(en.click_filters(ds, v, {"x": "SSM"})).ids == [4, 5, 6]
    pts = en.compute_visual(ds, _v("points", x="air_pressure", y="fpm"), [])
    assert pts["kind"] == "plotly" and not pts["clickable"]
    assert en.click_filters(ds, _v("points", x="air_pressure", y="fpm"), {"x": 3}) == []


def test_default_page_and_types():
    page = en.default_page()
    assert len(page["visuals"]) == 9 and len({v["id"] for v in page["visuals"]}) == 9
    assert {"matrix", "kpi", "table", "points", "box"} <= set(en.VISUAL_TYPES)
    for t in en.VISUAL_TYPES.values():
        assert all(w in en.WELLS for w in t["wells"])


# ── slicers (Datenschnitt), Nutzerwunsch 2026-10-30 ──────────────────────
def test_slicer_options_and_filters(ds):
    v = {"id": "s1", "type": "slicer", "w": 3, "wells": {"field": "machine"}, "style": "tiles"}
    r = en.compute_visual(ds, v, [])
    assert r["kind"] == "slicer" and r["style"] == "tiles" and r["title"] == "Machine"
    assert [(o["label"], o["n"]) for o in r["options"]] == [("AFK", 3), ("SSM", 3)]
    assert en.slicer_filter(ds, v) is None                      # nothing chosen = everything
    v["sel"] = {"values": ["SSM"]}
    assert en.slicer_filter(ds, v) == {"key": "machine", "values": ["SSM"]}
    assert ds.apply([en.slicer_filter(ds, v)]).ids == [4, 5, 6]


def test_slicer_numeric_between_and_list(ds):
    v = {"id": "s2", "type": "slicer", "wells": {"field": "air_pressure"}}
    r = en.compute_visual(ds, v, [])
    assert r["style"] == "between" and r["range"]["min"] == 3.0 and r["range"]["max"] == 3.5
    v["sel"] = {"min": 3.2, "max": 3.6}
    assert ds.apply([en.slicer_filter(ds, v)]).ids == [3, 5, 6]
    v.update(style="list", sel={"values": ["3"]})
    r = en.compute_visual(ds, v, [])
    assert [o["label"] for o in r["options"]] == ["3", "3.5"]
    assert en.slicer_filter(ds, v) == {"key": "air_pressure", "only": [3.0]}
    # "between" only exists for number fields
    assert en.slicer_style(ds, {"type": "slicer", "wells": {"field": "machine"}, "style": "between"}) == "list"


# ── Etappe 2: pages, free layout, filters per page / visual ─────────────
def test_normalize_old_spec_and_layout():
    old = {"title": "Old", "visuals": [{"id": "v1", "type": "kpi", "w": 3}, {"id": "v2", "type": "box", "w": 6},
                                       {"id": "v3", "type": "matrix", "w": 6}]}
    sp = en.normalize_spec(old)
    assert sp["active"] == "p1" and sp["pages"][0]["title"] == "Old" and sp["pages"][0]["filters"] == []
    lay = [(v["x"], v["y"], v["w"], v["h"]) for v in sp["pages"][0]["visuals"]]
    assert lay == [(0, 0, 3, 6), (3, 0, 6, 16), (0, 16, 6, 16)]       # third does not fit -> next row
    placed = en.normalize_spec({"pages": [{"id": "a", "visuals": [{"id": "v1", "type": "kpi", "x": 5, "y": 2, "w": 2, "h": 4},
                                                                  {"id": "v2", "type": "box"}]}], "active": "zz"})
    pg = placed["pages"][0]
    assert placed["active"] == "a" and (pg["visuals"][0]["x"], pg["visuals"][0]["y"]) == (5, 2)
    assert pg["visuals"][1]["y"] == 6                                 # new one goes below the placed ones
    assert en.normalize_spec(None)["pages"][0]["visuals"]


def test_filters_per_page_and_visual(ds):
    page = {"id": "p1", "filters": [{"key": "machine", "values": ["AFK"]}], "visuals": [
        {"id": "a", "type": "kpi", "agg": "count", "filters": []},
        {"id": "b", "type": "kpi", "agg": "count", "filters": [{"key": "air_pressure", "min": 3.2, "max": 4}]},
        {"id": "s", "type": "slicer", "wells": {"field": "air_pressure"}, "sel": {"min": 2.9, "max": 3.1}}]}
    va, vb, vs = page["visuals"]
    fa = en.visual_filters(ds, page, va, [], {})
    assert ds.apply(fa).ids == [1, 2]                     # page AFK + slicer 3.0
    fb = en.visual_filters(ds, page, vb, [], {})
    assert ds.apply(fb).ids == []                         # own 3.2-4 and slicer 2.9-3.1 exclude each other
    fs = en.visual_filters(ds, page, vs, [], {"a": [{"key": "machine", "values": ["SSM"]}]})
    assert ds.apply(fs).ids == []                         # page AFK + click SSM on another visual
    assert en.describe_filters(ds, page["filters"]) == ["Machine: AFK"]


def test_slicer_applies_only_to_its_targets(ds):
    page = {"id": "p1", "filters": [], "visuals": [
        {"id": "a", "type": "kpi", "agg": "count"}, {"id": "b", "type": "kpi", "agg": "count"},
        {"id": "s", "type": "slicer", "wells": {"field": "machine"}, "sel": {"values": ["SSM"]}, "targets": ["b"]}]}
    va, vb, _s = page["visuals"]
    assert ds.apply(en.visual_filters(ds, page, va, [], {})).count == 6      # not a target
    assert ds.apply(en.visual_filters(ds, page, vb, [], {})).count == 3
    page["visuals"][2]["targets"] = None                                     # default: all visuals
    assert ds.apply(en.visual_filters(ds, page, va, [], {})).count == 3


# ── Etappe 3: calculated fields, selection, targets, drill-down ─────────
from db import formula as fm


def test_formula_parse_and_evaluate(ds):
    stored = fm.from_display("[FP/m (FP/m)] / [Air Pressure (bar)]", ds.fields.values())
    assert stored == "{fpm} / {air_pressure}"
    assert fm.to_display(stored, ds.fields) == "[FP/m (FP/m)] / [Air Pressure (bar)]"
    code, keys = fm.compile_formula(stored, ds.fields)
    assert keys == ["fpm", "air_pressure"] and fm.evaluate(code, {"fpm": 90.0, "air_pressure": 3.0}) == 30.0
    assert fm.evaluate(code, {"fpm": 90.0, "air_pressure": 0.0}) is None        # division by zero -> no value
    assert fm.evaluate(code, {"fpm": None, "air_pressure": 3.0}) is None
    for bad, msg in (("__import__('os')", "Only numbers"), ("{fpm} +", "not complete"), ("{machine} * 2", "not a number"),
                     ("{nope} * 2", "Unknown field"), ("(1).__class__", "Only numbers")):
        with pytest.raises(fm.FormulaError, match=msg):
            fm.compile_formula(bad, ds.fields)
    with pytest.raises(fm.FormulaError, match="Unknown field"):
        fm.from_display("[Nothing]", ds.fields.values())


def test_calc_field_in_dataset_and_visuals(ds):
    ds.set_calc_fields([{"key": "calc_1", "name": "FP per bar", "unit": "", "formula": "{fpm} / {air_pressure}"}])
    assert ds.values("calc_1")[1] == pytest.approx(100 / 3)
    assert 6 not in ds.values("calc_1")                                         # trial 6 has no FP/m
    r = en.compute_visual(ds, {"id": "k", "type": "kpi", "agg": "max", "wells": {"value": "calc_1"}}, [])
    assert r["value"] == "36.7" and r["sub"].startswith("V2")                   # 110 / 3 bar on trial 2
    ds.set_calc_fields([])
    assert "calc_1" not in ds.fields


def test_selection_filter_and_target(ds):
    assert ds.apply([{"ids": [2, 5]}]).ids == [2, 5]
    assert en.describe_filters(ds, [{"ids": [2, 5]}]) == ["Selected 2 trials"]
    v = {"id": "k", "type": "kpi", "agg": "avg", "wells": {"value": "fpm"}, "target": {"value": 105, "better": "higher"}}
    assert en.compute_visual(ds, v, [])["status"] == "bad"                     # average 100 < 105
    v["target"]["better"] = "lower"
    assert en.compute_visual(ds, v, [])["status"] == "good"
    r = en.compute_visual(ds, {"id": "b", "type": "box", "wells": {"x": "machine", "y": "fpm"},
                               "target": {"value": 95}}, [])
    assert any(sh.get("y0") == 95 for sh in r["figure"]["layout"]["shapes"])


def test_drill_down(ds):
    v = {"id": "b", "type": "bar", "wells": {"x": "machine", "y": "fpm", "drill": ["air_pressure"]}}
    r = en.compute_visual(ds, v, [])
    assert r["drill"]["cur"] == "machine" and r["drill"]["can_down"]
    v["drillpath"] = [{"key": "machine", "value": "AFK"}]
    r = en.compute_visual(ds, v, [])
    assert r["drill"]["cur"] == "air_pressure" and not r["drill"]["can_down"] and r["n"] == 3
    assert r["drill"]["path"] == ["Machine: AFK"]
    # a click at the lower level filters the other visuals by path + clicked value
    flts = en.click_filters(ds, v, {"x": "3"})
    assert ds.apply(flts).ids == [1, 2]


# ── Etappe 4: templates, Excel data, notes, top-N categories ────────────
def test_templates_are_complete():
    for name, t in en.TEMPLATES.items():
        sp = en.template_spec(name)
        vis = en.active_page(sp)["visuals"]
        assert t["label"] and vis and len({v["id"] for v in vis}) == len(vis)
        assert all(all(isinstance(v[k], int) for k in ("x", "y", "w", "h")) for v in vis)
        assert all(v["type"] in en.VISUAL_TYPES for v in vis)


def test_visual_table_for_excel(ds):
    t, head, rows = en.visual_table(ds, {"id": "b", "type": "box", "wells": {"x": "machine", "y": "fpm"}}, [])
    assert head == ["Trial", "Series", "Machine", "Jet", "FP/m (FP/m)"] and len(rows) == 5   # trial 6: no FP/m
    t, head, rows = en.visual_table(ds, {"id": "m", "type": "matrix", "agg": "avg",
                                         "wells": {"rows": "machine", "cols": "air_pressure", "value": "fpm"}}, [])
    assert head[1:] == ["3", "3.5"] and rows[0] == ["AFK", 105.0, 120.0]
    t, head, rows = en.visual_table(ds, {"id": "k", "type": "kpi", "agg": "count", "wells": {}}, [])
    assert rows[0][0] == 6.0


def test_notes_marked_on_points(ds):
    ds._note_index = {"cell": {("lab", "fpm"): {}}, "trial": {2: ["checked twice (Ann, 30.10.2026)"]}}
    r = en.compute_visual(ds, {"id": "p", "type": "points", "notes": True,
                               "wells": {"x": "air_pressure", "y": "fpm"}}, [])
    tr = r["figure"]["data"][0]
    marked = [tid for tid, c in zip(tr["customdata"], tr["marker"]["line"]["color"]) if c == en.NOTE_COLOUR]
    assert marked == [2] and "checked twice" in tr["hovertext"][tr["customdata"].index(2)]
    en.reset_notes(ds)


def test_many_categories_are_cut(ds, monkeypatch):
    monkeypatch.setattr(en, "MAX_CATEGORIES", 1)
    r = en.compute_visual(ds, {"id": "b", "type": "box", "wells": {"x": "machine", "y": "fpm"}}, [])
    assert len(r["figure"]["layout"]["xaxis"]["categoryarray"]) == 1 and "1 rarer Machine" in r["note"]


def test_alignment_toolbar_in_page():
    from ui.smart_dashboard_html import DASHBOARD_HTML as H
    for needle in ('id="alignbar"', "function alignSel(", "MSEL", "'dh'", "'dv'"):
        assert needle in H


# ── Statistics (Etappe 5): counting series/experiments, columns, time axes ──
@pytest.fixture
def sds():
    """3 trials in 2 series of experiment 7, an empty series (exp 7) and an
    empty experiment 8 - like te._load_trials() builds them."""
    def tr(i, sid, month, tested, empty=False, exp=7):
        t = te.Trial(id=i, nr=max(i, 0), series_id=sid, exp_pk=exp, experiment=f"E{exp}", series=f"S{sid}",
                     machine="AFK", jet="", year=month[:4], empty=empty)
        t.extra = {"owner": "Anna" if sid == 1 else "Ben", "month": month, "exp_ordertype": "Development",
                   "exp_month": "2026-01", "trial_month": month}
        return t, tested
    rows = [tr(1, 1, "2026-01", ("Titer", "Statimat M")), tr(2, 1, "2026-01", ("Titer",)),
            tr(3, 2, "2026-03", ()), tr(-3, 3, "2026-03", None, empty=True),
            tr(-10_000_008, None, "2025-12", None, empty=True, exp=8)]
    trials = [t for t, _ in rows]
    tested = {t.id: x for t, x in rows if x}
    return te.TrialDataset(te.GENERAL_FIELDS, trials=trials,
                           loader=lambda f: tested if f.key == "tested_on" else {})


def test_empty_rows_only_when_counting_series_or_experiments(sds):
    assert len(sds.trials) == 3 and len(sds.empties) == 2
    assert sds.apply([]).count == 3 and sds.apply([], include_empty=True).count == 5
    kpi = lambda agg: en.compute_visual(sds, {**_v("kpi"), "agg": agg}, [])
    assert kpi("count")["value"] == "3" and kpi("count")["unit"] == "trials"
    assert kpi("count_series")["value"] == "3" and kpi("count_experiments")["value"] == "2"
    assert kpi("count_experiments")["title"] == "Experiments" and kpi("count_experiments")["n"] == 3
    # a filter on a trial-only field drops the empty rows again
    r = en.compute_visual(sds, {**_v("kpi"), "agg": "count_series"}, [{"key": "tested_on", "values": ["Titer"]}])
    assert r["value"] == "1"


def test_list_values_count_once_per_entry(sds):
    assert te.cat_label(("Titer", "Statimat M")) == "Titer, Statimat M"
    assert te.category_counts(sds.values("tested_on").values()) == [("Titer", 2), ("Statimat M", 1)]
    assert sds.apply([{"key": "tested_on", "values": ["Statimat M"]}]).ids == [1]
    r = en.compute_visual(sds, {**_v("column", x="tested_on"), "agg": "count"}, [])
    tr = r["figure"]["data"][0]
    assert dict(zip(tr["x"], tr["y"])) == {"Titer": 2, "Statimat M": 1, te.NONE_LABEL: 1}
    assert tr["x"][-1] == te.NONE_LABEL


def test_columns_time_axis_and_stacking(sds):
    assert en._time_axis(["2026-03", "2025-11", te.NONE_LABEL], "month") == \
        ["2025-11", "2025-12", "2026-01", "2026-02", "2026-03", te.NONE_LABEL]
    assert en._time_axis(["2024", "2026"], "year") == ["2024", "2025", "2026"]
    v = {**_v("column", x="month", legend="owner"), "agg": "count_series"}
    r = en.compute_visual(sds, v, [])
    assert r["title"] == "Trial series per Month by Owner"
    data = {t["name"]: dict(zip(t["x"], t["y"])) for t in r["figure"]["data"]}
    assert data["Anna"] == {"2026-01": 1, "2026-02": 0, "2026-03": 0}
    assert data["Ben"]["2026-03"] == 2            # series 2 + the empty series 3
    assert r["figure"]["layout"]["barmode"] == "stack"
    pct = en.compute_visual(sds, {**v, "stack": "percent"}, [])
    assert {t["name"]: t["y"][0] for t in pct["figure"]["data"]} == {"Anna": 100.0, "Ben": 0.0}
    # click on the Ben part of March filters month AND owner
    assert en.click_filters(sds, v, {"x": "2026-03", "n": "Ben"}) == [
        {"key": "month", "values": ["2026-03"]}, {"key": "owner", "values": ["Ben"]}]
    title, head, rows = en.visual_table(sds, v, [])
    assert head == ["Month", "Ben", "Anna"] and rows[-1] == ["2026-03", 2.0, 0.0]   # biggest first
    assert en.compute_visual(sds, _v("column", x="month"), [])["kind"] == "empty"   # avg without a Value


def test_stats_template_is_valid():
    spec = en.template_spec("stats")
    keys = {f.key for f in te.GENERAL_FIELDS}
    for vis in spec["pages"][0]["visuals"]:
        for k in (vis.get("wells") or {}).values():
            assert k in keys
        assert (vis.get("agg") or "avg") in en.AGGS
