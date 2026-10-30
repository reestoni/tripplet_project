"""New Smart Chart (Nutzerwunsch 2026-10-30): db/trial_explorer.py filtering
and ui/smart_chart_figure.py, with a hand-built dataset (no DB).
End-to-end on dev_local verified: PES + 70-80 dtex + 30-40 filaments ->
2'460 trials in 60 series (any ply) / 173 (core only), chart, split by
machine, saved view round trip, PDF."""
import pytest

from db import trial_explorer as te
from ui.smart_chart_figure import MAX_COLOURS, OTHER, build_figure


def _ply(no, use, mat, endtiter, fil, name="y"):
    return te.Ply(no, use, {"yarn_material": mat, "yarn_type": "DTY", "yarn_endtiter": endtiter, "yarn_titer": None,
                            "yarn_filaments": fil, "yarn_dpf": None, "yarn_name": name, "yarn_use": use})


def _trial(tid, series_id, plies, machine="AFK", jet="S315"):
    return te.Trial(id=tid, nr=tid, series_id=series_id, exp_pk=1, experiment="2026-01-001",
                    series=f"2026-01-001.{series_id:02d}", machine=machine, jet=jet, year="2026", plies=plies)


@pytest.fixture
def ds():
    trials = [
        _trial(1, 1, [_ply("Ply 1", "Core", "PES", 76, 36, "PES 76f36")]),
        # PES ply has the wrong titer, the 75 dtex ply is PA -> no single ply fits PES + 70-80
        _trial(2, 1, [_ply("Ply 1", "Core", "PES", 167, 48), _ply("Ply 2", "Effect", "PA 6.6", 75, 34)]),
        # fits only through the effect ply
        _trial(3, 2, [_ply("Ply 1", "Core", "PA 6.6", 44, 12), _ply("Ply 2", "Effect", "PES", 78, 34, "PES 78f34")],
               machine="SSM DP2T", jet="P212"),
        _trial(4, 2, [_ply("Ply 1", "Core", "PES", 72, 24)], machine="SSM DP2T", jet="P212"),
        _trial(5, 3, [], machine="eAFK", jet=""),
    ]
    lab = {"tenacity": {1: 4.1, 2: 3.9, 3: 3.5, 4: 4.0}, "air_pressure": {1: 3.0, 2: 3.5, 3: 3.0, 4: 4.0, 5: 2.0}}
    catalog = te.YARN_FIELDS + te.GENERAL_FIELDS + [
        te.Field("air_pressure", "Air Pressure", "bar", "Machine", "num"),
        te.Field("tenacity", "Tenacity", "cN/dtex", "Lab", "num"),
    ]
    return te.TrialDataset(catalog, trials=trials, loader=lambda f: lab.get(f.key, {}))


PES_70_80 = [{"key": "yarn_material", "values": ["PES"]}, {"key": "yarn_endtiter", "min": 70, "max": 80}]


def test_yarn_filters_must_fit_the_same_ply(ds):
    res = ds.apply(PES_70_80)
    assert res.ids == [1, 3, 4]
    assert res.matched[3].values["yarn_name"] == "PES 78f34"  # the matching (effect) ply
    assert ds.apply(PES_70_80 + [{"key": "yarn_filaments", "min": 30, "max": 40}]).ids == [1, 3]


def test_ply_scope(ds):
    assert ds.apply(PES_70_80, "core").ids == [1, 4]
    assert ds.apply(PES_70_80, "effect").ids == [3]
    # without yarn filters the scope does not drop trials
    assert ds.apply([], "core").ids == [1, 2, 3, 4, 5]


def test_trial_level_and_category_filters(ds):
    assert ds.apply([{"key": "machine", "values": ["SSM DP2T"]}]).ids == [3, 4]
    assert ds.apply([{"key": "jet", "values": [te.NONE_LABEL]}]).ids == [5]
    assert ds.apply([{"key": "tenacity", "min": 4.0}]).ids == [1, 4]
    assert ds.apply([{"key": "tenacity", "max": 3.6}]).ids == [3]  # trials without a value never pass


def test_summary_and_field_values_ignore_own_filter(ds):
    res = ds.apply(PES_70_80)
    assert ds.summary(res) == {"trials": 3, "series": 2, "machines": 2, "jets": 2}
    # values of End titer under the OTHER filters (material PES): one value per ply
    vals = ds.field_values("yarn_endtiter", PES_70_80)
    assert sorted(vals) == [44, 72, 75, 76, 78, 167]
    assert te.category_counts(ds.field_values("machine", [])) == [("AFK", 2), ("SSM DP2T", 2), ("eAFK", 1)]


def test_histogram_and_describe():
    h = te.histogram([70, 72, 75, 78, 80, 150])
    assert h["n"] == 6 and sum(h["counts"]) == 6 and h["edges"][0] <= 70 and h["edges"][-1] >= 150
    assert te.histogram([])["counts"] == []
    f = te.Field("yarn_endtiter", "End titer", "dtex", "Yarn", "num", "yarn")
    assert te.describe_filter(f, {"min": 70, "max": 80}) == "End titer 70 – 80 dtex"
    assert te.describe_filter(f, {"min": 70, "max": None}) == "End titer ≥ 70 dtex"
    m = te.Field("yarn_material", "Material", "", "Yarn", "cat", "yarn")
    assert te.describe_filter(m, {"values": ["PES", "PA", "PP", "CO"]}) == "Material: PES, PA, PP +1"


def test_figure_each_and_mean(ds):
    res = ds.apply([])
    fig, rows, info = build_figure(ds, res, "air_pressure", "tenacity", colour="machine")
    assert info["plotted"] == 4 and len(rows) == 4          # trial 5 has no tenacity
    assert {t["name"] for t in fig["data"]} == {"AFK", "SSM DP2T"}
    assert rows[0]["yarn"] in ("PES 76f36", "y")
    fig, rows, _ = build_figure(ds, res, "air_pressure", "tenacity", mode="mean")
    (tr,) = fig["data"]
    assert tr["x"] == [3.0, 3.5, 4.0] and tr["y"][0] == pytest.approx((4.1 + 3.5) / 2)
    assert tr["error_y"]["array"][1] == 0.0


def test_figure_split_and_category_x(ds):
    res = ds.apply([])
    fig, _rows, info = build_figure(ds, res, "machine", "tenacity", split="jet")
    assert info["x_is_cat"] and fig["layout"]["xaxis"]["type"] == "category"
    assert "xaxis2" in fig["layout"] and fig["layout"]["xaxis2"]["matches"] == "x"
    assert [a["text"] for a in fig["layout"]["annotations"]] == ["<b>P212</b>", "<b>S315</b>"]


def test_figure_limits_colours():
    trials = [_trial(i, 1, [_ply("Ply 1", "Core", "PES", 70, 30)], jet=f"J{i}") for i in range(1, 13)]
    cat = te.YARN_FIELDS + te.GENERAL_FIELDS + [te.Field("tenacity", "Tenacity", "", "Lab", "num"),
                                                te.Field("air_pressure", "Air", "bar", "Machine", "num")]
    d = te.TrialDataset(cat, trials=trials, loader=lambda f: {i: float(i) for i in range(1, 13)})
    fig, _r, _i = build_figure(d, d.apply([]), "air_pressure", "tenacity", colour="jet")
    names = [t["name"] for t in fig["data"]]
    assert len(names) == MAX_COLOURS + 1 and names[-1] == OTHER


# ── chart types and colours (Nutzerwunsch 2026-10-30, "mehr Darstellungen") ──
from ui.smart_chart_figure import CHART_TYPES, PALETTES, linear_fit


def test_every_chart_type_builds(ds):
    res = ds.apply([])
    expected = {"points": "scatter", "trend": "scatter", "line": "scatter", "bar": "bar", "box": "box",
                "violin": "violin", "hist": "histogram", "density": "histogram2dcontour"}
    assert set(expected) == set(CHART_TYPES)
    for chart, ttype in expected.items():
        fig, rows, info = build_figure(ds, res, "air_pressure", "tenacity", colour="machine", chart=chart)
        assert info["chart"] == chart and fig["data"], chart
        assert fig["data"][0]["type"] == ttype, chart
    # histogram ignores X: trial 5 has tenacity? no -> still 4 rows; bar/box use category X labels
    fig, _r, _i = build_figure(ds, res, "air_pressure", "tenacity", chart="bar")
    assert fig["layout"]["xaxis"]["type"] == "category" and fig["data"][0]["x"] == ["3", "3.5", "4"]


def test_trend_line_and_fit():
    slope, icpt, r2 = linear_fit([1, 2, 3, 4], [2, 4, 6, 8])
    assert slope == pytest.approx(2) and icpt == pytest.approx(0) and r2 == pytest.approx(1)
    assert linear_fit([1, 1, 1], [1, 2, 3]) is None and linear_fit([1, 2], [1, 2]) is None


def test_trend_traces(ds):
    fig, _r, _i = build_figure(ds, ds.apply([]), "air_pressure", "tenacity", chart="trend")
    trend = [t for t in fig["data"] if t.get("mode") == "lines"]
    assert len(trend) == 1 and trend[0]["name"].startswith("Trend All trials: R²")


def test_number_colour_scale_and_ranges(ds):
    res = ds.apply([])
    fig, _r, info = build_figure(ds, res, "air_pressure", "tenacity", colour="yarn_endtiter", chart="points")
    assert info["continuous"] and "colorscale" in fig["data"][0]["marker"]
    fig, _r, info = build_figure(ds, res, "air_pressure", "tenacity", colour="yarn_endtiter", chart="bar")
    assert not info["continuous"] and all("–" in t["name"] for t in fig["data"])


def test_palette_own_colours_shapes_dark(ds):
    res = ds.apply([])
    fig, _r, info = build_figure(ds, res, "air_pressure", "tenacity", colour="machine", palette="bold",
                                 colour_map={"SSM DP2T": "#123456"}, shapes=True, dark=True, logy=True, size=12)
    by_name = {t["name"]: t for t in fig["data"]}
    assert by_name["AFK"]["marker"]["color"] == PALETTES["bold"]["colours"][0]
    assert by_name["SSM DP2T"]["marker"]["color"] == "#123456"
    assert info["colour_defaults"]["SSM DP2T"] == PALETTES["bold"]["colours"][1]
    assert {by_name["AFK"]["marker"]["symbol"], by_name["SSM DP2T"]["marker"]["symbol"]} == {"circle", "square"}
    assert by_name["AFK"]["marker"]["size"] == 12
    assert fig["layout"]["plot_bgcolor"] != "#FFFFFF" and fig["layout"]["yaxis"]["type"] == "log"


# ── value steps / picked values, jet group, field picker (Nutzerwunsch 2026-10-30) ──
def test_number_filter_step_and_picked_values():
    f = te.Field("overfeed", "Overfeed", "%", "Machine", "num")
    flt = {"min": 1, "max": 5, "step": 1}
    assert [x for x in (1, 1.5, 2, 2.2, 5, 6) if te._passes(f, x, flt)] == [1, 2, 5]
    flt = {"min": 1, "max": 5, "step": 0.5}
    assert [x for x in (1, 1.5, 1.75, 2.0000001, 3.5) if te._passes(f, x, flt)] == [1, 1.5, 2.0000001, 3.5]
    flt = {"min": 1, "max": 5, "only": [1.5, 3]}
    assert [x for x in (1, 1.5, 3, 3.0, 7) if te._passes(f, x, flt)] == [1.5, 3, 3.0]
    assert te.describe_filter(f, {"min": 1, "max": 5, "step": 1}) == "Overfeed 1 – 5 % · whole numbers"
    assert te.describe_filter(f, {"min": 1, "max": 5, "step": 0.5}) == "Overfeed 1 – 5 % · every 0.5"
    assert te.describe_filter(f, {"min": 1, "max": 5, "only": [3, 1.5]}) == "Overfeed: 1.5, 3 %"


def test_distinct_values():
    assert te.distinct_values([1, 1.5, 1.5, 2, 9, None, "x"], 1, 5) == [(1.0, 1), (1.5, 2), (2.0, 1)]
    assert te.distinct_values(range(200)) is None


def test_jet_group_comes_second():
    assert te.GROUPS[:3] == (te.CALC_GROUP, "Yarn", "Jet")   # own calculated fields first
    assert any(c[0] == "Luftbohrung" for c in te.JET_COLUMNS)


def test_field_picker(qapp=None):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from ui.smart_chart_style import FieldPicker
    fields = te.YARN_FIELDS + te.GENERAL_FIELDS
    p = FieldPicker()
    p.set_fields(fields, ("cat",), "— none —")
    assert p.currentData() == "" and p.text() == "— none —"
    seen = []
    p.changed.connect(lambda: seen.append(p.currentData()))
    p.set_key("machine", emit=True)
    assert p.currentData() == "machine" and seen == ["machine"]
    p.set_key("does-not-exist", emit=True)
    assert p.currentData() == ""
    menus = [a.text() for a in p.menu().actions() if a.menu()]
    assert menus[0].startswith("Yarn") and all("(" in m for m in menus)
