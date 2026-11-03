"""Format tab of the Smart Chart dashboard (Etappe 1, Nutzerwunsch 2026-11-02):
sort and Top N, decimals, data labels, axis titles, Y range, legend - with a
hand-built dataset (no DB). Without "fmt" every visual stays exactly as before
(checked on dev_local against all template visuals: 424 of 424 equal)."""
import pytest

from db import trial_explorer as te
from ui import smart_dashboard_engine as en

# mean FP/m per machine: RPR 130, AFK 105, SSM 85
MACHINES = {1: "AFK", 2: "AFK", 3: "SSM", 4: "SSM", 5: "RPR"}
FPM = {1: 100.0, 2: 110.0, 3: 80.0, 4: 90.0, 5: 130.0}


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


def _v(t, fmt=None, **wells):
    v = {"id": "v1", "type": t, "w": 6, "title": "", "agg": "avg", "wells": wells}
    if fmt is not None:
        v["fmt"] = fmt
    return v


def _cats(r):
    return r["figure"]["layout"]["xaxis"]["categoryarray"]


@pytest.mark.parametrize("sort,expected", [
    ("value_desc", ["RPR", "AFK", "SSM"]), ("value_asc", ["SSM", "AFK", "RPR"]),
    ("name_asc", ["AFK", "RPR", "SSM"]), ("name_desc", ["SSM", "RPR", "AFK"]),
])
def test_bar_sort(ds, sort, expected):
    r = en.compute_visual(ds, _v("bar", {"sort": sort}, x="machine", y="fpm"), [])
    assert _cats(r) == expected


def test_top_n_keeps_the_best_and_says_so(ds):
    r = en.compute_visual(ds, _v("box", {"sort": "value_desc", "top": 2}, x="machine", y="fpm"), [])
    assert _cats(r) == ["RPR", "AFK"] and r["plotted"] == 3 and r["note"] == "Top 2 of 3 shown"
    r = en.compute_visual(ds, _v("bar", {"sort": "value_asc", "top": 1}, x="machine", y="fpm"), [])
    assert _cats(r) == ["SSM"]
    r = en.compute_visual(ds, _v("bar", {"sort": "name_asc", "top": 2}, x="machine", y="fpm"), [])
    assert _cats(r) == ["AFK", "RPR"]            # the two highest, shown by name


def test_column_sort_top_and_excel_follow(ds):
    v = _v("column", {"sort": "name_desc", "top": 2}, x="machine")
    v["agg"] = "count"
    r = en.compute_visual(ds, v, [])
    assert r["figure"]["data"][0]["x"] == ["SSM", "AFK"] and r["note"] == "Top 2 of 3 shown"
    _, head, rows = en.visual_table(ds, v, [])
    assert [row[0] for row in rows] == ["SSM", "AFK"]


def test_stack_sort(ds):
    v = _v("stack", {"sort": "value_desc"}, x="machine", values=["fpm", "air_pressure"])
    v["stack"] = "stacked"
    r = en.compute_visual(ds, v, [])
    assert r["figure"]["data"][0]["x"] == ["RPR", "AFK", "SSM"]


def test_decimals(ds):
    assert en.compute_visual(ds, _v("kpi", {"decimals": 2}, value="fpm"), [])["value"] == "102.00"
    r = en.compute_visual(ds, _v("matrix", {"decimals": 1}, rows="machine", cols="air_pressure", value="fpm"), [])
    assert "105.0" not in str(r) and "100.0" in r["figure"]["data"][0]["text"][0]
    r = en.compute_visual(ds, _v("bar", {"decimals": 1}, x="machine", y="fpm"), [])
    assert r["figure"]["layout"]["yaxis"]["tickformat"] == ".1f"


def test_data_labels(ds):
    r = en.compute_visual(ds, _v("bar", {"labels": True, "decimals": 0}, x="machine", y="fpm"), [])
    assert r["figure"]["data"][0]["text"] == ["105", "130", "85"]
    r = en.compute_visual(ds, _v("line", {"labels": True}, x="machine", y="fpm"), [])
    assert "text" in r["figure"]["data"][0]["mode"]
    v = _v("column", {"labels": False}, x="machine")
    v["agg"] = "count"
    assert "text" not in en.compute_visual(ds, v, [])["figure"]["data"][0]
    r = en.compute_visual(ds, _v("matrix", {"labels": False}, rows="machine", cols="air_pressure", value="fpm"), [])
    assert r["figure"]["data"][0]["texttemplate"] == ""


def test_error_bars_off(ds):
    for t in ("bar", "line"):
        r = en.compute_visual(ds, _v(t, {}, x="machine", y="fpm"), [])
        assert r["figure"]["data"][0].get("error_y")                 # standard: ± SD
        r = en.compute_visual(ds, _v(t, {"errbars": "off", "labels": True}, x="machine", y="fpm"), [])
        tr = r["figure"]["data"][0]
        assert "error_y" not in tr and tr.get("text")                # labels still found the mean trace
    assert "errbars" not in en.FORMAT_SECTIONS["box"]


def test_error_bars_confidence_and_min_max(ds):
    def bars(kind):
        tr = en.compute_visual(ds, _v("bar", {"errbars": kind}, x="machine", y="fpm"), [])["figure"]["data"][0]
        i = tr["x"].index("AFK")                                       # AFK: 100, 110 -> mean 105, SD 7.07
        e = tr["error_y"]
        return e["array"][i], (e.get("arrayminus") or e["array"])[i], tr["hovertext"][i], tr["x"].index("RPR"), e
    plus, minus, hov, rpr, e = bars("ci")
    assert plus == pytest.approx(12.706 * 7.0711 / 2 ** 0.5, rel=1e-3) and "95 % confidence" in hov
    assert e["array"][rpr] == 0                                        # n=1: no interval
    plus, minus, hov, _, _ = bars("minmax")
    assert plus == minus == pytest.approx(5) and "Min 100" in hov and "Max 110" in hov


def test_error_bars_asymmetric_and_t_values():
    from ui.smart_chart_figure import _err_bars, _error_y, t95
    means, minus, plus, _ = _err_bars({"a": [1.0, 2.0, 6.0]}, ["a"], "minmax")
    assert means == [3.0] and minus == [2.0] and plus == [3.0]
    e = _error_y(minus, plus)
    assert e["symmetric"] is False and e["arrayminus"] == [2.0]
    assert t95(1) == 12.706 and t95(30) == 2.042 and t95(1000) == 1.96 and t95(0) == 0.0


def test_axes_and_legend(ds):
    fmt = {"xtitle": "Machine type", "ytitle": "", "ymin": 0, "ymax": 200, "legend": "top"}
    lay = en.compute_visual(ds, _v("points", fmt, x="air_pressure", y="fpm", legend="machine"), [])["figure"]["layout"]
    assert lay["xaxis"]["title"]["text"] == "Machine type" and lay["yaxis"]["title"]["text"] == ""
    assert lay["yaxis"]["range"] == [0, 200] and lay["yaxis"]["autorange"] is False
    assert lay["legend"]["orientation"] == "h" and lay["legend"]["yanchor"] == "bottom"
    lay = en.compute_visual(ds, _v("bar", {"ymin": 50, "legend": "off"}, x="machine", y="fpm"), [])["figure"]["layout"]
    assert lay["yaxis"]["range"] == [50, None] and lay["yaxis"]["autorange"] == "max"
    assert lay["showlegend"] is False


def test_nothing_set_changes_nothing(ds):
    for t, wells in (("bar", {"x": "machine", "y": "fpm"}), ("matrix", {"rows": "machine", "cols": "air_pressure",
                                                                        "value": "fpm"}), ("kpi", {"value": "fpm"})):
        assert en.compute_visual(ds, _v(t, {}, **wells), []) == en.compute_visual(ds, _v(t, **wells), [])


def test_sections_per_type():
    assert en.FORMAT_SECTIONS["slicer"] == []
    assert en.FORMAT_SECTIONS["table"] == ["numbers", "text", "table"]
    assert en.FORMAT_SECTIONS["kpi"] == ["numbers", "card"]
    assert en.FORMAT_SECTIONS["bar"] == ["sort", "numbers", "labels", "errbars", "colours", "text", "axes", "yrange", "logy",
                                         "legend"]
    assert "sort" not in en.FORMAT_SECTIONS["points"] and "labels" not in en.FORMAT_SECTIONS["box"]


# ── Etappe 2: colours, text, card, table ─────────────────────────────────
def test_palette_and_own_colours(ds):
    r = en.compute_visual(ds, _v("bar", {"palette": "heberlein"}, x="machine", y="fpm"), [])
    assert r["figure"]["data"][0]["marker"]["color"] == en.PALETTES["heberlein"]["colours"][0]
    assert r["colours"] == {"groups": [], "single": en.PALETTES["heberlein"]["colours"][0]}
    r = en.compute_visual(ds, _v("bar", {"colour": "#123456"}, x="machine", y="fpm"), [])
    assert r["figure"]["data"][0]["marker"]["color"] == "#123456" and r["colours"]["single"] == "#123456"
    r = en.compute_visual(ds, _v("points", {"colours": {"SSM": "#ABCDEF"}}, x="air_pressure", y="fpm",
                                 legend="machine"), [])
    by_name = {tr["name"]: tr["marker"]["color"] for tr in r["figure"]["data"]}
    assert by_name["SSM"] == "#ABCDEF" and dict(map(tuple, r["colours"]["groups"]))["SSM"] == "#ABCDEF"
    assert r["colours"]["single"] is None


def test_column_and_stack_colours(ds):
    v = _v("column", {"colours": {"S315": "#111111"}}, x="machine", legend="jet")
    v["agg"] = "count"
    r = en.compute_visual(ds, v, [])
    assert {tr["name"]: tr["marker"]["color"] for tr in r["figure"]["data"]}["S315"] == "#111111"
    assert [g[0] for g in r["colours"]["groups"]] == ["S315", "P212"]
    v = _v("column", {"colour": "#222222"}, x="machine")
    v["agg"] = "count"
    assert en.compute_visual(ds, v, [])["figure"]["data"][0]["marker"]["color"] == "#222222"
    r = en.compute_visual(ds, _v("stack", {"colours": {"FP/m (FP/m)": "#333333"}}, x="machine",
                                 values=["fpm", "air_pressure"]), [])
    assert r["figure"]["data"][0]["marker"]["color"] == "#333333" and len(r["colours"]["groups"]) == 2


def test_matrix_scale_text_size_and_grid(ds):
    r = en.compute_visual(ds, _v("matrix", {"scale": "Blues", "font": "large"}, rows="machine", cols="air_pressure",
                                 value="fpm"), [])
    assert r["figure"]["data"][0]["colorscale"] == "Blues" and r["figure"]["layout"]["font"]["size"] == 13
    lay = en.compute_visual(ds, _v("bar", {"grid": False, "font": "small"}, x="machine", y="fpm"), [])["figure"]["layout"]
    assert lay["xaxis"]["showgrid"] is False and lay["yaxis"]["showgrid"] is False and lay["font"]["size"] == 9


def test_card_format(ds):
    r = en.compute_visual(ds, _v("kpi", {"vsize": "xl", "unit": False, "sub": False}, value="fpm"), [])
    assert r["vsize"] == 52 and r["unit"] == "" and r["sub"] == ""
    v = _v("kpi", {"vsize": "s"})
    v["agg"] = "count"
    assert en.compute_visual(ds, v, [])["vsize"] == 20
    assert "vsize" not in en.compute_visual(ds, _v("kpi", value="fpm"), [])


def test_table_sort_rules_and_size(ds):
    fmt = {"tsort": {"key": "fpm", "dir": "desc"}, "decimals": 1, "font": "large",
           "rules": [{"key": "fpm", "op": ">", "a": "100", "colour": "green"},
                     {"key": "machine", "op": "=", "a": "ssm", "colour": "red"},
                     {"key": "fpm", "op": "between", "a": "80", "b": "90", "colour": "amber"}]}
    r = en.compute_visual(ds, _v("table", fmt, columns=["machine", "fpm"]), [])
    assert [row[1] for row in r["rows"]] == ["V5", "V2", "V1", "V4", "V3"]
    assert [row[4] for row in r["rows"]] == ["130.0", "110.0", "100.0", "90.0", "80.0"]
    green, red, amber = (en.RULE_COLOURS[c] for c in ("green", "red", "amber"))
    assert r["cellbg"] == [["", "", "", green], ["", "", "", green], ["", "", "", ""],
                           ["", "", red, amber], ["", "", red, amber]]
    assert r["font"] == 13 and r["keys"] == ["trial", "series", "machine", "fpm"]
    _, _, rows = en.visual_table(ds, _v("table", fmt, columns=["machine", "fpm"]), [])
    assert [row[0] for row in rows] == ["V5", "V2", "V1", "V4", "V3"]           # Excel in the same order
    r = en.compute_visual(ds, _v("table", {"tsort": {"key": "machine", "dir": "asc"}}, columns=["machine"]), [])
    assert [row[3] for row in r["rows"]] == ["AFK", "AFK", "RPR", "SSM", "SSM"] and "cellbg" not in r


def test_rule_hit():
    assert en.rule_hit({"op": "<", "a": "5"}, 4) and not en.rule_hit({"op": "<", "a": "5"}, None)
    assert not en.rule_hit({"op": ">", "a": ""}, 4)                 # unfinished rule does nothing
    assert en.rule_hit({"op": "=", "a": "pes"}, "PES") and en.rule_hit({"op": "=", "a": "3"}, 3.0)


# ── Etappe 3: dashboard theme ────────────────────────────────────────────
def test_theme_applies_where_it_fits_and_own_format_wins(ds):
    spec = en.normalize_spec({"pages": [{"id": "p1", "visuals": []}],
                              "theme": {"palette": "bold", "font": "large", "decimals": 1, "grid": False,
                                        "legend": "top", "labels": True, "junk": 1}})
    assert spec["theme"] == {"palette": "bold", "font": "large", "decimals": 1, "grid": False, "legend": "top",
                             "labels": True}
    bar = en.themed(spec, _v("bar", x="machine", y="fpm"))
    assert bar["fmt"] == spec["theme"]
    r = en.compute_visual(ds, bar, [])
    assert r["figure"]["data"][0]["marker"]["color"] == en.PALETTES["bold"]["colours"][0]
    assert r["figure"]["layout"]["font"]["size"] == 13 and r["figure"]["data"][0]["text"][0] == "105.0"
    own = en.themed(spec, _v("bar", {"palette": "pastel", "grid": True}, x="machine", y="fpm"))
    assert own["fmt"]["palette"] == "pastel" and own["fmt"]["grid"] is True
    lay = en.compute_visual(ds, own, [])["figure"]["layout"]
    assert lay["yaxis"].get("showgrid") is not False                      # the visual switched grid lines back on
    assert en.themed(spec, _v("kpi", value="fpm"))["fmt"] == {"decimals": 1}
    assert set(en.themed(spec, _v("matrix", rows="machine", cols="air_pressure", value="fpm"))["fmt"]) == \
        {"font", "decimals", "labels"}
    assert en.themed(spec, _v("table", columns=["fpm"]))["fmt"] == {"font": "large", "decimals": 1}
    slicer = _v("slicer", field="machine")
    assert en.themed(spec, slicer) is slicer and "fmt" not in slicer         # nothing to format, untouched


def test_no_theme_changes_nothing():
    v = _v("bar", {"sort": "value_desc"}, x="machine", y="fpm")
    assert en.themed({"pages": []}, v) is v and en.themed(None, v) is v
    assert "theme" not in en.normalize_spec({"pages": [{"id": "p1", "visuals": []}], "theme": {}})
