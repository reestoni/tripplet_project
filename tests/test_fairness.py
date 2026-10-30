"""Smart Chart fairness check (db/fairness.py), Nutzerwunsch 2026-10-30.
Calibrated on dev_local: jet series 4er vs APe (box, FP/m) -> green;
material box (PES vs PA vs EL) -> red (end titer, filaments, pressure,
machine; no common titer range); air pressure vs tenacity without colour
-> red (high pressures only on SSM DP2T)."""
import random

import pytest

from db import fairness as fz
from db.trial_explorer import Field

FIELDS = {
    "yarn_material": Field("yarn_material", "Material", "", "Yarn", "cat", "yarn"),
    "air_pressure": Field("air_pressure", "Air Pressure", "bar", "Machine", "num"),
    "machine": Field("machine", "Machine", "", "General", "cat"),
}


def _points(confounded: bool, n=60, seed=1):
    """Two jets A/B. Y depends strongly on material (PES +1.0) and pressure.
    confounded: A runs mostly PES at high pressure, B mostly PA at low pressure."""
    rnd = random.Random(seed)
    pts = []
    for i in range(n):
        g = "A" if i % 2 == 0 else "B"
        if confounded:
            mat = "PES" if (g == "A") == (rnd.random() < 0.9) else "PA"
            ap = rnd.uniform(3.5, 4.5) if g == "A" else rnd.uniform(1.5, 2.5)
        else:
            mat = "PES" if rnd.random() < 0.5 else "PA"
            ap = rnd.uniform(1.5, 4.5)
        y = 3.0 + (1.0 if mat == "PES" else 0.0) + 0.3 * ap + rnd.gauss(0, 0.1)
        pts.append({"tid": i, "y": y, "x": ap, "grp": g, "mat": mat, "ap": ap, "machine": "AFK",
                    "series_id": i % 6, "series": f"S{i % 6}"})
    return pts


def _cond(key, p):
    return {"yarn_material": p["mat"], "air_pressure": p["ap"], "machine": p["machine"]}[key]


def test_fair_comparison_is_green():
    a = fz.assess(_points(False), lambda p: p["grp"], _cond, FIELDS, "Colour by Jet", y_title="FP/m")
    assert a.level == fz.GREEN and a.fix is None
    assert a.sentence.startswith("No large differences")


def test_confounded_comparison_is_red_and_names_the_reason():
    a = fz.assess(_points(True), lambda p: p["grp"], _cond, FIELDS, "Colour by Jet", y_title="FP/m")
    assert a.level == fz.REDL
    worst = {c.key for c in a.conditions if c.level == fz.REDL}
    assert {"yarn_material", "air_pressure"} & worst
    assert "differ in" in a.sentence and "FP/m" in a.sentence
    # machine is the same everywhere -> no condition line for it (only one value)
    assert "machine" not in {c.key for c in a.conditions}


def test_fix_keeps_common_part():
    pts = _points(True)
    a = fz.assess(pts, lambda p: p["grp"], _cond, FIELDS, "Colour by Jet", skip=["air_pressure"])
    assert a.fix["key"] == "yarn_material" and "PES" in a.fix["values"]
    a = fz.assess(pts, lambda p: p["grp"], _cond, FIELDS, "Colour by Jet", skip=["yarn_material"])
    assert a.fix is None and "no common Air Pressure range" in a.fix_text   # 3.5-4.5 vs 1.5-2.5


def test_skipped_and_single_group():
    pts = _points(True)
    a = fz.assess(pts, lambda p: p["grp"], _cond, FIELDS, "x", skip=["yarn_material", "air_pressure"])
    assert a.conditions == []
    assert fz.assess(pts, lambda p: "A", _cond, FIELDS, "x").level == fz.NONE


def test_small_group_dominance_and_x_overlap_warnings():
    pts = _points(False)
    for p in pts[:3]:
        p["grp"] = "C"                                   # tiny group
    for p in pts:
        if p["grp"] == "B":
            p["series_id"], p["series"] = 99, "S99"      # B is one experiment of its own
            p["x"] = p["x"] + 10                         # and lies elsewhere on X
    a = fz.assess(pts, lambda p: p["grp"], _cond, FIELDS, "Colour by Jet", x_ranges=True)
    texts = " | ".join(t for _l, t in a.warnings)
    assert "“C” has only 3 trials" in texts
    assert "of “B” come from one trial series (S99)" in texts
    assert "different X ranges" in texts
    assert a.level in (fz.YELLOW, fz.REDL)


def test_eta2_and_bands():
    assert fz.eta2([("a", 1), ("a", 1), ("a", 1), ("b", 3), ("b", 3), ("b", 3)]) == pytest.approx(1.0)
    assert fz.eta2([("a", 1), ("b", 1)]) is None
    cuts = fz.quantile_bands(list(range(100)))
    assert len(cuts) == 4 and fz.band_of(0, cuts) == 0 and fz.band_of(99, cuts) == 4
    assert fz._fmt(120.707) == "121" and fz._fmt(4.044) == "4.04" and fz._fmt(47.25) == "47.2"
