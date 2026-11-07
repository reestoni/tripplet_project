# tests/test_smart_dashboard_highlight.py
"""Cross-highlight (Nutzerwunsch 2026-11-03): a click greys out the rest instead of filtering."""
import pytest

from db import trial_explorer as te
from ui import smart_dashboard_engine as en

# FP/m per machine: AFK 100/110, SSM 80/90, RPR 130; jets alternate S315 (odd ids) / P212 (even ids)
MACHINES = {1: "AFK", 2: "AFK", 3: "SSM", 4: "SSM", 5: "RPR"}
FPM = {1: 100.0, 2: 110.0, 3: 80.0, 4: 90.0, 5: 130.0}
AFK = [{"key": "machine", "values": ["AFK"]}]


@pytest.fixture
def ds():
    ply = te.Ply("Ply 1", "Core", {"yarn_material": "PES", "yarn_type": "DTY", "yarn_endtiter": 76, "yarn_titer": None,
                                   "yarn_filaments": 36, "yarn_dpf": None, "yarn_name": "PES 76", "yarn_use": "Core"})
    trials = [te.Trial(id=i, nr=i, series_id=1, exp_pk=7, experiment="2026-01-001", series="S1", machine=m,
                       jet="S315" if i % 2 else "P212", year="2026", plies=[ply]) for i, m in MACHINES.items()]
    lab = {"fpm": FPM, "air_pressure": {1: 3.0, 2: 3.5, 3: 3.0, 4: 3.5, 5: 3.0}}
    cat = te.YARN_FIELDS + te.GENERAL_FIELDS + [te.Field("fpm", "FP/m", "FP/m", "Lab", "num"),
                                                te.Field("air_pressure", "Air Pressure", "bar", "Machine", "num")]
    return te.TrialDataset(cat, trials=trials, loader=lambda f: dict(lab.get(f.key, {})))


def _v(t, **wells):
    return {"id": "v1", "type": t, "w": 6, "title": "", "agg": "avg", "wells": wells}


def test_mode_and_types():
    assert en.clicks_mode({}) == "highlight" and en.clicks_mode({"clicks": "filter"}) == "filter"
    assert en.normalize_spec({"pages": [], "clicks": "filter"})["clicks"] == "filter"
    assert "clicks" not in en.normalize_spec({"pages": [], "clicks": "highlight"})
    assert en.highlights({}, {"type": "bar"}, AFK)
    assert not en.highlights({}, {"type": "bar"}, [])
    assert not en.highlights({"clicks": "filter"}, {"type": "bar"}, AFK)
    for t in ("kpi", "matrix", "table", "radar", "box", "violin", "hist", "density", "slicer"):
        assert not en.highlights({}, {"type": t}, AFK)


def test_points_grey_out_the_rest(ds):
    r = en.highlight_visual(ds, _v("points", x="air_pressure", y="fpm"), [], AFK)
    tr = r["figure"]["data"][0]
    on = {tid: c != en.DIM_COLOUR for tid, c in zip(tr["customdata"], tr["marker"]["color"])}
    assert on == {1: True, 2: True, 3: False, 4: False, 5: False}
    assert r["highlight"] == 2 and r["note"].startswith("2 of 5 trials highlighted")


def test_bars_keep_all_and_overlay_the_selection(ds):
    r = en.highlight_visual(ds, _v("bar", x="jet", y="fpm"), [], AFK)
    data = r["figure"]["data"]
    full, sel = data[0], data[-1]
    assert len(full["x"]) == 2 and "rgba(" in full["marker"]["color"] and "error_y" not in full
    assert sel["offsetgroup"] == full["offsetgroup"] and full["showlegend"] is False
    means = dict(zip(sel["x"], sel["y"]))
    assert means == {"S315": 100.0, "P212": 110.0}        # AFK trials only: 1 (S315) and 2 (P212)


def test_clicked_bar_itself(ds):
    r = en.highlight_visual(ds, _v("bar", x="machine", y="fpm"), [], AFK)
    sel = r["figure"]["data"][-1]
    assert sel["x"] == ["AFK"] and sel["y"] == [105.0]


def test_line_overlay(ds):
    r = en.highlight_visual(ds, _v("line", x="jet", y="fpm"), [], AFK)
    full, sel = r["figure"]["data"][0], r["figure"]["data"][-1]
    assert full["marker"]["opacity"] == en.DIM_ALPHA and sel["marker"].get("opacity") != en.DIM_ALPHA
    assert sel["hovertext"][0].startswith("<b>Highlighted</b>")


@pytest.mark.parametrize("stack", ["stacked", "percent", "grouped"])
def test_columns_show_the_share(ds, stack):
    v = {**_v("column", x="machine", legend="jet"), "agg": "count", "stack": stack}
    r = en.highlight_visual(ds, v, [], [{"key": "jet", "values": ["S315"]}])
    fig = r["figure"]
    bars, over = fig["data"][:2], fig["data"][2:]
    assert all(t["showlegend"] is False for t in bars) and all(t["showlegend"] for t in over)
    assert len(bars) == len(over) == 2
    by = {t["name"]: dict(zip(t["x"], t["y"])) for t in over}
    full = {t["name"]: dict(zip(t["x"], t["y"])) for t in bars}
    assert by["P212"] == {x: 0.0 for x in full["P212"]}             # nothing of P212 selected
    assert by["S315"] == pytest.approx(full["S315"])                 # all of S315 selected
    assert fig["layout"]["barmode"] == ("group" if stack == "grouped" else "overlay")
    if stack != "grouped":
        s315, p212 = (next(t for t in over if t["name"] == n) for n in ("S315", "P212"))
        first = next(t for t in bars if t["name"] == fig["data"][0]["name"])
        assert all(b == 0 for b in first["base"])                     # first part starts at 0
        assert (s315 if first["name"] == "P212" else p212)["base"] == first["y"]  # second sits on the first


def test_pie_and_stack_grey_categories(ds):
    v = {**_v("pie", legend="machine"), "agg": "count"}
    tr = en.highlight_visual(ds, v, [], AFK)["figure"]["data"][0]
    faded = {lab: c.startswith("rgba(") for lab, c in zip(tr["labels"], tr["marker"]["colors"])}
    assert faded == {"AFK": False, "SSM": True, "RPR": True}
    v = {**_v("stack", x="machine", values=["fpm", "air_pressure"]), "stack": "grouped"}
    tr = en.highlight_visual(ds, v, [], AFK)["figure"]["data"][0]
    faded = {x: c.startswith("rgba(") for x, c in zip(tr["x"], tr["marker"]["color"])}
    assert faded == {"AFK": False, "SSM": True, "RPR": True}
