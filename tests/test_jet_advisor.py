"""Jet Advisor (ui/jet_advisor.py) on synthetic trials - no DB."""
import json

import numpy as np
import pytest

from ui import dty_whatif as w
from ui import jet_advisor as ja

YARNS = {
    1: {"yarn_id": 1, "name": "PES 167f48", "material_id": 11, "material": "PES", "type_id": 1, "yarn_type": "POY",
        "endtiter": 167.0, "titer": 280.0, "filaments": 48.0},
    2: {"yarn_id": 2, "name": "PES 150f48", "material_id": 11, "material": "PES", "type_id": 1, "yarn_type": "POY",
        "endtiter": 150.0, "titer": 250.0, "filaments": 48.0},
    3: {"yarn_id": 3, "name": "PA 167f48", "material_id": 9, "material": "PA", "type_id": 1, "yarn_type": "POY",
        "endtiter": 167.0, "titer": 200.0, "filaments": 48.0},
}
JETS = {
    10: {"jet_id": 10, "jet_name": "STD-A", "type_id": 1, "type_name": "Standard", "maker_id": 1, "maker_name": "H",
         "group_id": 1, "group_name": "G1", "air": 0.6, "bore": 1.1, "holes": 1, "titer_from": 100.0, "titer_to": 200.0,
         "titer_ideal": 167.0},
    20: {"jet_id": 20, "jet_name": "DEV-B", "type_id": 2, "type_name": "Entwicklung", "maker_id": 1, "maker_name": "H",
         "group_id": 2, "group_name": "G2", "air": 0.4, "bore": 0.9, "holes": 1, "titer_from": 20.0, "titer_to": 80.0,
         "titer_ideal": 50.0},
}


def _rows():
    rng = np.random.default_rng(1)
    out, tid = [], 0
    for jet, slope in ((10, 25.0), (20, 12.0)):
        for yarn in (1, 2, 3):
            for series in (1, 2):
                for p in (2.0, 3.0, 4.0, 5.0):
                    for of in (3.0, 4.0, 5.0):
                        for _rep in range(2):
                            tid += 1
                            out.append({
                                "trial_id": tid, "trial_no": tid, "series_id": jet * 100 + yarn * 10 + series,
                                "series_name": f"S{jet}-{yarn}-{series}", "jet_id": jet, "jet_name": JETS[jet]["jet_name"],
                                "pressure": p, "of": of, "speed": 800.0, "t_before": None, "t_after": None,
                                "yarn_key": str(yarn), "yarn_name": YARNS[yarn]["name"],
                                "fpm": slope * p + 2 * of + series + rng.normal(0, 2),
                                "fpm_cv": 20 - 2 * p + rng.normal(0, 1),
                                "stab03": None, "stab06": None, "stab13": None,
                                "stab10": 60 + 6 * p + rng.normal(0, 2),
                            })
    return w.clean_rows(out)


@pytest.fixture(scope="module")
def adv():
    return ja.Advisor(_rows(), JETS, YARNS)


def _req(**kw):
    d = {"yarn_id": 1, "targets": {"fpm": {"lo": 90}}}
    d.update(kw)
    return ja.request_from_json(d)


def test_errors(adv):
    assert adv.advise(_req(targets={}))["error"] == ja.ERR_NO_TARGET
    assert adv.advise(_req(yarn_id=None))["error"] == ja.ERR_NO_YARN
    assert adv.advise(_req(yarn_id=None, endtiter=167, filaments=0))["error"] == ja.ERR_NO_YARN


def test_best_jet_and_setting(adv):
    res = adv.advise(_req(targets={"fpm": {"lo": 100}, "stab10": {"lo": 80}}))
    top = res["results"][0]
    assert top.jet["jet_id"] == 10
    assert top.best.prob > 0.9 and top.best.settings["pressure"] >= 4.0
    assert top.best.preds["fpm"].met and top.best.preds["stab10"].met
    assert top.titer_ok is True
    # the development jet cannot reach 100 points/m (12 x 5 bar + ...) - ranked behind, with a miss
    other = next(r for r in res["results"] if r.jet["jet_id"] == 20)
    assert other.best.prob < 0.05 and other.best.miss > 0


def test_filters(adv):
    res = adv.advise(_req(jet_types=[2]))
    assert {r.jet["jet_id"] for r in res["results"]} == {20}
    assert adv.advise(_req(makers=[99]))["results"] == []
    res = adv.advise(_req(titer_fit=True))
    assert {r.jet["jet_id"] for r in res["results"]} == {10}       # 167 dtex outside 20-80


def test_limits_no_extrapolation(adv):
    res = adv.advise(_req(targets={"fpm": {"lo": 100}}, limits={"pressure": [None, 3.0]}))
    top = res["results"][0]
    assert top.best.settings["pressure"] <= 3.0 and top.best.miss > 0
    # outside every measured value -> nothing (no extrapolation)
    assert adv.advise(_req(limits={"speed": [900, None]}))["results"] == []


def test_similar_yarns_and_material(adv):
    res = adv.advise(_req(yarn_id=None, endtiter=160, filaments=48, material_id=11))
    keys = {y["key"] for y in res["yarns"]}
    assert keys == {"1", "2"}                                        # PA excluded
    res = adv.advise(_req(yarn_id=None, endtiter=160, filaments=48, material_id=11, same_material=False))
    assert {y["key"] for y in res["yarns"]} == {"1", "2", "3"}
    assert ja.yarn_distance({"endtiter": 167, "filaments": 48}, {"endtiter": 167 * 1.3, "filaments": 48}) == \
        pytest.approx(1.0)


def test_prefer_air_takes_lower_pressure(adv):
    robust = adv.advise(_req(targets={"fpm": {"lo": 60}}))["results"][0]
    air = adv.advise(_req(targets={"fpm": {"lo": 60}}, prefer="air"))["results"][0]
    assert air.best.air is not None and robust.best.air is not None
    assert air.best.settings["pressure"] < robust.best.settings["pressure"]


def test_window_and_json(adv):
    res = adv.advise(_req(targets={"fpm": {"lo": 60, "hi": 200}}))
    top = res["results"][0]
    lo, hi = top.window["pressure"]
    assert lo <= top.best.settings["pressure"] <= hi
    js = ja.result_json(res)
    json.dumps(js)
    r0 = js["results"][0]
    assert r0["jet"] == "STD-A" and set(r0["preds"]) == {"fpm"} and r0["series"]


def test_request_from_json_ignores_junk():
    r = ja.request_from_json({"targets": {"fpm": {"lo": "80"}, "evil": {"lo": 1}}, "limits": {"x": [1, 2]},
                              "max_distance": 99, "prefer": "x"})
    assert set(r.targets) == {"fpm"} and r.targets["fpm"].lo == 80 and r.limits == {}
    assert r.max_distance == 3.0 and r.prefer == "robust"


def test_clean_rows_zero_points_per_metre_is_no_measurement():
    (r,) = w.clean_rows([{"fpm": 0, "fpm_cv": 0, "stab10": 0, "stab06": 50.0}])
    assert r["fpm"] is None and r["fpm_cv"] is None and r["stab10"] is None and r["stab06"] == 50.0
    (r,) = w.clean_rows([{"fpm": 80, "fpm_cv": 0, "stab10": 0}])
    assert r["fpm"] == 80 and r["fpm_cv"] is None and r["stab10"] == 0


def test_options(adv):
    o = adv.options()
    assert {t["id"] for t in o["jet_types"]} == {1, 2}
    assert {y["id"] for y in o["yarns"]} == {1, 2, 3} and o["targets"] == list(ja.TARGETS)
