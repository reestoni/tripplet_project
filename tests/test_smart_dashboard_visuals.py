"""New dashboard visuals (Nutzerwunsch 2026-11-02): pie / donut, control chart, radar, text."""
import pytest

from test_smart_dashboard_format import ds, _v  # noqa: F401  (same small dataset: RPR 130, AFK 105, SSM 85)
from ui import smart_dashboard_engine as en


def test_pie_counts_shares_and_click(ds):
    v = _v("pie", legend="machine")
    v["agg"] = "count"
    r = en.compute_visual(ds, v, [])
    tr = r["figure"]["data"][0]
    assert tr["type"] == "pie" and tr["labels"] == ["AFK", "SSM", "RPR"] and tr["values"] == [2.0, 2.0, 1.0]
    assert tr["hole"] == 0 and r["title"] == "Trials by Machine" and r["clickable"]
    assert [g[0] for g in r["colours"]["groups"]] == ["AFK", "SSM", "RPR"]
    assert en.click_filters(ds, v, {"x": "SSM"}) == [{"key": "machine", "values": ["SSM"]}]
    assert en.click_filters(ds, v, {"x": "Other"}) == []
    _, head, rows = en.visual_table(ds, v, [])
    assert rows == [["AFK", 2.0], ["SSM", 2.0], ["RPR", 1.0]]


def test_donut_format_and_value(ds):
    v = _v("pie", {"sort": "value_asc", "labels": False, "colours": {"RPR": "#123456"}, "decimals": 1},
           legend="machine", value="fpm")
    v.update(agg="sum", shape="donut")
    r = en.compute_visual(ds, v, [])
    tr = r["figure"]["data"][0]
    assert tr["hole"] > 0 and tr["labels"] == ["RPR", "SSM", "AFK"] and tr["texttemplate"] == ""
    assert tr["marker"]["colors"][0] == "#123456"
    assert "510.0" in r["figure"]["layout"]["annotations"][0]["text"]          # total in the hole
    assert en.compute_visual(ds, _v("pie"), [])["kind"] == "empty"


def test_control_limits_and_signals():
    mean, sigma, lcl, ucl = en.control_limits([10, 12, 11, 13])
    assert mean == 11.5 and sigma == pytest.approx(5 / 3 / 1.128) and ucl == pytest.approx(mean + 3 * sigma)
    assert en.run_points([1, 1, 1, 1, 1, 1, 1, 0, -5], 0) == [True] * 7 + [False, False]
    assert not any(en.run_points([1, -1] * 5, 0))


def test_control_chart(ds):
    r = en.compute_visual(ds, _v("control", y="fpm"), [])
    tr = r["figure"]["data"][0]
    assert tr["y"] == [100.0, 110.0, 80.0, 90.0, 130.0]            # in trial order
    names = [a["text"].split()[0] for a in r["figure"]["layout"]["annotations"]]
    assert names == ["UCL", "Mean", "LCL"] and r["selectable"] and "outside" in r["note"]
    r = en.compute_visual(ds, _v("control", x="air_pressure", y="fpm"), [])
    assert r["figure"]["layout"]["xaxis"]["ticktext"][0] == "3"
    _, head, rows = en.visual_table(ds, _v("control", y="fpm"), [])
    assert head[:2] == ["Trial", "Series"] and len(rows) == 5
    assert en.compute_visual(ds, _v("control", x="machine"), [])["kind"] == "empty"


def test_radar(ds):
    v = _v("radar", legend="machine", values=["fpm", "air_pressure", "yarn_endtiter"])
    r = en.compute_visual(ds, v, [])
    assert r["kind"] == "plotly" and len(r["figure"]["data"]) == 3
    rpr = next(t for t in r["figure"]["data"] if t["name"] == "RPR")
    assert rpr["r"][0] == 100.0 and rpr["theta"][0] == "FP/m"               # highest FP/m = outside
    assert en.click_filters(ds, v, {"n": "AFK"}) == [{"key": "machine", "values": ["AFK"]}]
    assert en.compute_visual(ds, _v("radar", legend="machine", values=["fpm"]), [])["kind"] == "empty"


def test_text(ds):
    r = en.compute_visual(ds, {**_v("text", {"font": "large"}), "text": "# Jets 2026\nOnly core yarns"}, [])
    assert r["kind"] == "text" and r["text"].startswith("# Jets") and r["font"] == 13 and r["title"] == ""
    assert en.FORMAT_SECTIONS["text"] == ["text"]
    assert en.FORMAT_SECTIONS["pie"] == ["sort", "numbers", "labels", "colours", "text", "legend"]
    assert "axes" in en.FORMAT_SECTIONS["control"] and "axes" not in en.FORMAT_SECTIONS["radar"]


def test_model_info_and_filled_counts(ds):
    from db import trial_explorer as te
    fields = list(ds.fields.values()) + [te.Field("t_x", "Tenacity @ 0.3", "", "Itemat Plus", "num",
                                                   source={"main_table": "tbllaboritematplus", "field": "Tenacity",
                                                           "condition": "Tension = 0.3"})]
    m = en.model_info(fields)
    by_id = {n["id"]: n for n in m["nodes"]}
    assert by_id["General"]["kind"] == "centre" and by_id["General"]["relation"] == ""
    assert by_id["Yarn"]["relation"] == "1 : n" and by_id["Jet"]["relation"] == "n : 1"
    lab = by_id["Itemat Plus"]
    assert lab["kind"] == "lab" and lab["relation"] == "1 : n" and "tension" in lab["how"]
    assert lab["tables"] == ["tbllaboritematplus"]
    counts = en.filled_counts(ds, ["fpm", "yarn_material", "machine", "nope"])
    assert counts == {"fpm": 5, "yarn_material": 5, "machine": 5}


# ── chart mode merged into the dashboard: focus list, fairness details, markers / log axes ──
def test_focus_rows(ds):
    v = _v("points", {"decimals": 1}, x="air_pressure", y="fpm", legend="machine")
    d = en.focus_rows(ds, v, [{"key": "machine", "values": ["AFK", "SSM"]}])
    assert d["head"] == ["Trial", "Series", "Machine", "Jet", "Air Pressure (bar)", "FP/m (FP/m)"]
    assert [r[1] for r in d["rows"]] == ["V1", "V2", "V3", "V4"] and d["rows"][0][0] == 1
    assert d["rows"][0][5:] == ["3.0", "100.0"] and d["more"] == 0
    pie = {**_v("pie", legend="machine"), "agg": "count"}
    assert len(en.focus_rows(ds, pie, [])["rows"]) == 5            # every trial behind the pie


def test_fairness_object_for_the_details(ds):
    v = _v("box", x="machine", y="fpm")
    a = en.fairness_of(ds, v, [])
    r = en.compute_visual(ds, v, [])
    assert "_assessment" not in r
    if r.get("fair"):                     # the small dataset may be too small to judge - then both are empty
        assert a is not None and a.level == r["fair"]["level"]


def test_markers_and_log_axes(ds):
    r = en.compute_visual(ds, _v("points", {"shapes": True, "psize": "large", "xlog": True, "ylog": True},
                                 x="air_pressure", y="fpm", legend="machine"), [])
    lay, data = r["figure"]["layout"], r["figure"]["data"]
    assert lay["xaxis"]["type"] == "log" and lay["yaxis"]["type"] == "log"
    assert {t["marker"]["symbol"] for t in data} == {"circle", "square", "diamond"} and data[0]["marker"]["size"] == 11
    r = en.compute_visual(ds, _v("control", {"ylog": True}, y="fpm"), [])
    assert r["figure"]["layout"]["yaxis"]["type"] == "log"
    assert "markers" in en.FORMAT_SECTIONS["points"] and "logx" not in en.FORMAT_SECTIONS["box"]
