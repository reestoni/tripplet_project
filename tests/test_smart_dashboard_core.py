"""ui/smart_dashboard_core.py - the Qt-free controller of the Smart Chart dashboard (desktop widget and web
use it, 2026-11-13). Hand-built dataset like tests/test_smart_dashboard.py, no DB, no Qt."""
import io
import sys

import pytest

from db import trial_explorer as te
from ui import smart_dashboard_core as core


def _ply(mat, endtiter):
    return te.Ply("Ply 1", "Core", {"yarn_material": mat, "yarn_type": "DTY", "yarn_endtiter": endtiter,
                                    "yarn_titer": None, "yarn_filaments": 36, "yarn_dpf": None,
                                    "yarn_name": f"{mat} {endtiter}", "yarn_use": "Core"})


class Host:
    def __init__(self, ds):
        self.ds, self.catalog, self.filters, self.ply_scope = ds, list(ds.fields.values()), [], "any"


@pytest.fixture
def host():
    trials = []
    for i, m in enumerate(["AFK", "AFK", "AFK", "SSM", "SSM", "SSM"], start=1):
        trials.append(te.Trial(id=i, nr=i, series_id=1 + i % 2, exp_pk=7, experiment="2026-01-001",
                               series=f"S{1 + i % 2}", machine=m, jet="S315", year="2026", plies=[_ply("PES", 76)]))
    lab = {"fpm": {1: 100.0, 2: 110.0, 3: 120.0, 4: 80.0, 5: 90.0},
           "air_pressure": {1: 3.0, 2: 3.0, 3: 3.5, 4: 3.0, 5: 3.5, 6: 3.5}}
    cat = te.YARN_FIELDS + te.GENERAL_FIELDS + [te.Field("fpm", "FP/m", "FP/m", "Lab", "num"),
                                                te.Field("air_pressure", "Air Pressure", "bar", "Machine", "num")]
    return Host(te.TrialDataset(cat, trials=trials, loader=lambda f: dict(lab.get(f.key, {}))))


SPEC = {"pages": [{"id": "p1", "title": "Page 1", "visuals": [
    {"id": "v1", "type": "bar", "x": 0, "y": 0, "w": 6, "h": 12, "agg": "avg", "wells": {"x": "machine", "y": "fpm"}},
    {"id": "v2", "type": "kpi", "x": 6, "y": 0, "w": 3, "h": 6, "agg": "count", "wells": {}}]},
    {"id": "p2", "title": "Detail", "drillthrough": ["machine"], "visuals": [
        {"id": "v3", "type": "table", "x": 0, "y": 0, "w": 12, "h": 16, "wells": {"columns": ["machine", "fpm"]}}]}],
    "active": "p1"}


def test_qt_free():
    import subprocess
    code = "import sys, ui.smart_dashboard_core; sys.exit(any(m.startswith('PySide6') for m in sys.modules))"
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0


def test_init_then_results_and_click(host):
    s = core.DashboardSession(host)
    s.set_spec(SPEC)
    cmds = s.init_cmds({"viz": True}, {})
    assert [c for c, _a in cmds] == ["init", "renderResults"]
    assert cmds[0][1]["panes"] == {"viz": True} and cmds[0][1]["trials"] == 6
    res = cmds[1][1]["results"]
    assert res["v2"]["value"] == "6"
    # click on the AFK bar filters the card (cross-filter); the same click again undoes it
    assert s.click("v1", {"x": "AFK", "y": 110, "n": ""})
    assert s.refresh_cmds()[0][1]["results"]["v2"]["value"] == "3"
    assert s.click("v1", '{"x": "AFK", "y": 110, "n": ""}')
    assert s.refresh_cmds()[0][1]["results"]["v2"]["value"] == "6"
    s.select("v1", "[1, 2]")
    assert s.refresh_cmds()[0][1]["results"]["v2"]["value"] == "2"
    s.clear("v1")
    assert not s.cross


def test_update_spec_keeps_clicks_of_existing_visuals(host):
    s = core.DashboardSession(host)
    s.set_spec(SPEC)
    s.click("v1", {"x": "SSM"})
    spec = {**SPEC, "pages": [SPEC["pages"][0]]}
    assert s.update_spec(spec) and "v1" in s.cross
    spec2 = {"pages": [{"id": "p1", "title": "P", "visuals": []}], "active": "p1"}
    assert s.update_spec(spec2) and not s.cross
    assert not s.update_spec("not json")


def test_filters_on_all_page_visual(host):
    s = core.DashboardSession(host)
    s.set_spec(SPEC)
    flt = {"key": "machine", "values": ["SSM"]}
    assert s.put_filter("page", "", -1, flt)
    assert s.spec["pages"][0]["filters"] == [flt]
    others, edit = s.filter_context("visual", "v1", -1)
    assert flt in others and edit is None
    assert s.put_filter("all", "", -1, {"key": "machine", "values": ["AFK"]}) and host.filters
    assert s.remove_filter("all", "", 0) and not host.filters
    ro = core.DashboardSession(host, read_only=True)
    ro.set_spec(SPEC)
    assert not ro.put_filter("page", "", -1, flt) and not ro.remove_filter("page", "", 0)


def test_filter_editor(host):
    ds = host.ds
    ov = core.field_overview(ds, "fpm", [], "any")
    assert ov["kind"] == "num" and ov["hist"]["n"] == 5
    ov = core.field_overview(ds, "machine", [], "any")
    assert dict((a, b) for a, b in ov["cats"]) == {"AFK": 3, "SSM": 3}
    f = ds.fields["fpm"]
    assert core.make_filter(f, {"min": "120", "max": "90"}) == {"key": "fpm", "min": 90.0, "max": 120.0}
    assert core.make_filter(f, {"mode": "pick", "only": []}) is None
    assert core.make_filter(f, {"mode": "step", "step": "0,5"})["step"] == 0.5
    assert core.make_filter(ds.fields["machine"], {"values": []}) is None
    h = core.filter_hits(ds, [], {"key": "fpm", "min": 100, "max": None}, "any")
    assert h["base"] == 6 and h["n"] == 3 and "FP/m" in h["text"]
    assert core.number_values(ds, "fpm", [], "any", 90, 110) == [[90.0, 1], [100.0, 1], [110.0, 1]]
    assert core.snap(123.456) == 120.0


def test_calc_fields(host):
    s = core.DashboardSession(host)
    s.set_spec(SPEC)
    key = s.next_calc_key()
    assert key == "calc_1"
    p = core.calc_preview(host.ds, "[FP/m] / [Air Pressure]", key)
    assert p["n"] == 5 and p["max"] == pytest.approx(36.6667, rel=1e-3)
    assert "error" in core.calc_preview(host.ds, "[nope] + 1", key)
    d = core.calc_definition(host.ds, key, "Eff", "", "[FP/m] / [Air Pressure]")
    s.save_calc(key, d)
    assert s.needs_init()                       # new catalog for the page
    assert [c for c, _a in s.refresh_cmds()][0] == "init"
    assert any(c["key"] == key for c in s.init_data()["catalog"])
    s.save_calc(key, None)
    assert not s.spec.get("calc")
    with pytest.raises(ValueError):
        core.calc_definition(host.ds, key, " ", "", "[FP/m]")


def test_drill_through_and_back(host):
    s = core.DashboardSession(host)
    s.set_spec(SPEC)
    cmds = s.drill_through("v1", {"x": "SSM"}, "p2")
    assert cmds == [("goPage", "p2")] and s.spec["active"] == "p2"
    assert s.through_info(s.spec["pages"][1])["text"]
    assert s.drill_back(True) == [("goPage", "p1")] and not s.through


def test_excel_pdf_and_views(host):
    s = core.DashboardSession(host)
    s.set_spec(SPEC)
    buf = io.BytesIO()
    s.write_excel(buf, SPEC["pages"][0]["visuals"])
    assert buf.getvalue()[:2] == b"PK"
    job, jobs = s.pdf_job(True, "T")
    assert len(job["pages"]) == 2 and [j["key"] for j in jobs] == ["p1:v1"]
    cfg = core.view_settings([{"key": "machine", "values": ["AFK"]}], "core", SPEC)
    flt, scope, spec, missing = core.read_view_settings({**cfg, "filters": cfg["filters"] + [{"key": "gone"}]},
                                                        set(host.ds.fields))
    assert scope == "core" and spec == SPEC and missing == ["gone"] and len(flt) == 1
    assert core.view_kind(cfg) == {"pages": 2, "visuals": 3}
    assert s.trial_target(4) == {"exp_pk": 7, "series_id": 1, "experiment": "2026-01-001"}
