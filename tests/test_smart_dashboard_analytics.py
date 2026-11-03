"""Dashboard Analytics lines and drill-through (Nutzerwunsch 2026-11-02, like Power BI).
Checked on dev_local: bar with Average/±2 SD/band, box with small multiples (lines per panel),
right-click on a machine → detail page with exactly the 14 trials of that machine, Back, Keep all filters."""
import pytest

from test_smart_dashboard_format import ds, _v  # noqa: F401  (FP/m 100, 110, 80, 90, 130; RPR 130, AFK 105, SSM 85)
from ui import smart_dashboard_engine as en


def test_marks_from_values():
    m = en.analytics_marks([{"kind": "mean"}, {"kind": "median", "label": "Mid"}, {"kind": "min"}, {"kind": "max"},
                            {"kind": "percentile", "p": 50}, {"kind": "sd", "n": 2},
                            {"kind": "constant", "value": 95, "colour": "orange"},
                            {"kind": "band", "lo": 120, "hi": 80, "label": "Spec"}, {"kind": "nonsense"}],
                           [100, 110, 80, 90, 130, None])
    labels = [x[2] for x in m]
    assert labels[:5] == ["Average 102", "Mid 100", "Min 80", "Max 130", "P50 100"]
    sd = 19.235
    assert m[5][0] == pytest.approx(102 + 2 * sd, abs=0.01) and m[6][0] == pytest.approx(102 - 2 * sd, abs=0.01)
    assert labels[5].startswith("+2 SD") and labels[6].startswith("−2 SD")
    assert m[7] == (95, 95, "95", en.ANALYTICS_COLOURS["orange"])
    assert m[8][:3] == (80, 120, "Spec 80 – 120")                       # band sorted, nonsense ignored
    assert len(m) == 9
    # no values: only the fixed lines
    assert [x[2] for x in en.analytics_marks([{"kind": "mean"}, {"kind": "constant", "value": 1}], [])] == ["1"]
    assert en.analytics_marks([{"kind": "band", "lo": 5}], [1])[0][:2] == (5, 5)    # half a band = a line


def test_lines_on_charts(ds):
    assert not en.compute_visual(ds, _v("bar", x="machine", y="fpm"), [])["figure"]["layout"].get("shapes")
    v = _v("bar", x="machine", y="fpm")
    v["analytics"] = [{"kind": "mean"}, {"kind": "band", "lo": 85, "hi": 115}]
    lay = en.compute_visual(ds, v, [])["figure"]["layout"]
    assert [(s["type"], s["y0"]) for s in lay["shapes"]] == [("line", 102), ("rect", 85)]
    assert lay["shapes"][0]["xref"] == "x domain" and lay["shapes"][0]["yref"] == "y"
    # small multiples: one set per panel, from that panel's trials
    v = _v("box", x="air_pressure", y="fpm", split="machine")
    v["analytics"] = [{"kind": "mean"}]
    lay = en.compute_visual(ds, v, [])["figure"]["layout"]
    means = {s["yref"]: s["y0"] for s in lay["shapes"]}
    assert sorted(means.values()) == [85, 105, 130]
    # histogram: vertical; log axis: log10 position
    v = _v("hist", y="fpm")
    v["analytics"] = [{"kind": "constant", "value": 100}]
    s = en.compute_visual(ds, v, [])["figure"]["layout"]["shapes"][0]
    assert s["xref"] == "x" and s["x0"] == 100 and s["yref"] == "y domain"
    v = _v("points", {"ylog": True}, x="air_pressure", y="fpm")
    v["analytics"] = [{"kind": "constant", "value": 100}]
    assert en.compute_visual(ds, v, [])["figure"]["layout"]["shapes"][0]["y0"] == pytest.approx(2)
    # columns: from the plotted columns; control chart
    v = _v("column", x="machine")
    v.update(agg="count", analytics=[{"kind": "max"}])
    assert en.compute_visual(ds, v, [])["figure"]["layout"]["shapes"][0]["y0"] == 2
    v = _v("control", y="fpm")
    v["analytics"] = [{"kind": "band", "lo": 85, "hi": 115}]
    assert en.compute_visual(ds, v, [])["figure"]["layout"]["shapes"][-1]["type"] == "rect"


def test_analytics_are_not_format(ds):
    assert "analytics" not in en.FORMAT_SECTIONS["bar"]                  # the painter copies fmt only
    assert set(en.ANALYTICS_TYPES) <= set(en.VISUAL_TYPES)
    assert set(en.ANALYTICS_DEFAULT_COLOUR) == set(en.ANALYTICS_KINDS)


def _spec():
    return en.normalize_spec({"pages": [
        {"id": "p1", "title": "Overview", "visuals": [_v("bar", x="machine", y="fpm"), {**_v("kpi"), "id": "k"}]},
        {"id": "p2", "title": "Machine", "drillthrough": ["machine"], "visuals": []},
        {"id": "p3", "title": "Jet", "drillthrough": ["jet"], "visuals": []}], "active": "p1"})


def test_drill_through_pages_and_filters(ds):
    spec = _spec()
    v = spec["pages"][0]["visuals"][0]
    assert en.drill_through_pages(spec, ds, v, "p1") == [{"id": "p2", "title": "Machine"}]
    assert en.drill_through_pages(spec, ds, spec["pages"][0]["visuals"][1], "p1") == []      # card: no click
    assert en.drill_through_pages(spec, ds, v, "p2") == []                # not to its own page
    page_filter = {"key": "air_pressure", "min": 3, "max": 4}
    flts = en.drill_through_filters(ds, v, {"x": "AFK"}, spec["pages"][1], [page_filter])
    assert flts == [page_filter, {"key": "machine", "values": ["AFK"]}]   # Keep all filters (standard)
    spec["pages"][1]["dt_keep"] = False
    assert en.drill_through_filters(ds, v, {"x": "AFK"}, spec["pages"][1], [page_filter]) == \
        [{"key": "machine", "values": ["AFK"]}]
    assert en.drill_through_filters(ds, v, {"x": "AFK"}, spec["pages"][2], []) == []          # other field
    m = _v("matrix", rows="machine", cols="air_pressure", value="fpm")
    assert en.click_keys(ds, m) == ["machine", "air_pressure"]
