"""db/quick_scan.py - Quick Scan (Requirement Hub) without Qt (shared by desktop screen and web)."""
import subprocess
import sys
from pathlib import Path

import pytest

from db import quick_scan as qs

ROOT = Path(__file__).resolve().parents[1]


def test_qt_free():
    code = ("import sys; import db.quick_scan; "
            "sys.exit(1 if any(m.startswith('PySide6') for m in sys.modules) else 0)")
    assert subprocess.run([sys.executable, "-c", code], cwd=str(ROOT)).returncode == 0


def test_score_weighted():
    f = {"operator": "between", "value1": 50.0, "value2": 100.0, "direction": "higher", "target_val": 90.0}
    assert qs.score_weighted(95, f) == 1.0 and qs.score_weighted(40, f) == 0.0
    assert qs.score_weighted(70, f) == pytest.approx(0.5)
    f = {**f, "direction": "lower", "target_val": 60.0}
    assert qs.score_weighted(55, f) == 1.0 and qs.score_weighted(80, f) == pytest.approx(0.5)
    f = {**f, "direction": "exact", "target_val": 75.0}
    assert qs.score_weighted(75, f) == 1.0 and qs.score_weighted(100, f) == 0.0


def test_make_rule():
    num = {"field_key": "x", "data_type": "float"}
    assert qs.make_rule(num, "between", 1, None) is None
    assert qs.make_rule(num, ">=", "a") is None
    r = qs.make_rule(num, "between", 1, 2, "weighted", "2", "lower", "1.5")
    assert r["weight"] == 2.0 and r["direction"] == "lower" and r["target_val"] == 1.5
    assert qs.make_rule(num, ">=", 3, section="filter")["target_type"] == "must"
    lk = {"field_key": "j", "data_type": "lookup"}
    assert qs.make_rule(lk, value1=[]) is None and qs.make_rule(lk, value1=[1, 2])["operator"] == "in"


@pytest.fixture(scope="module")
def fields():
    try:
        f = {x["field_key"]: x for x in qs.load_fields()}
    except Exception as e:  # pragma: no cover
        pytest.skip(f"no database: {e}")
    if "titer" not in f or "stabilitaet_10" not in f:
        pytest.skip("standard fields missing")
    return f


def test_resolve_field(fields):
    f = qs.resolve_field({"field_id": fields["stabilitaet_10"]["field_id"], "tension": 0.6})
    assert f["tension_filter"] == 0.6 and f["source_column"] == "Stability"
    with pytest.raises(ValueError):
        qs.resolve_field({"adhoc": {"table": "tbluser", "column": "Password"}})
    with pytest.raises(ValueError):
        qs.resolve_field({"adhoc": {"table": "tbltrial", "column": "Nope`; DROP"}})
    a = qs.resolve_field({"adhoc": {"table": "tbltrial", "column": "AirPressure", "unit": "bar"}})
    assert a["field_key"] == "adhoc__tbltrial__AirPressure" and a["_adhoc"]


def test_run(fields):
    flt = [qs.make_rule(fields["titer"], "between", 50, 500, section="filter")]
    tg = [qs.make_rule(fields["stabilitaet_10"], "between", 50, 100, "weighted", 1, "higher", 90)]
    rows, w, d = qs.QuickScanEvaluator().run(flt, tg)
    assert len(w) == 1 and not d
    assert all(50 <= (r["titer"] or 0) <= 500 or r["titer"] is None for r in rows)
    scores = [r["_score"] for r in rows]
    assert scores == sorted(scores, reverse=True)


def test_ruleset_roundtrip(fields):
    from db.connection import execute
    lookup = next((f for f in fields.values() if f["data_type"] == "lookup"), None)
    flt = [qs.make_rule(fields["titer"], "=", 167, section="filter")]
    if lookup:
        flt.append({"field": lookup, "operator": "in", "value1": [1], "value2": None, "target_type": "must"})
    tg = [qs.make_rule(fields["stabilitaet_10"], "between", 50, 100, "weighted", 2, "lower", 60),
          qs.make_rule(fields["titer"], ">=", 50, None, "distance")]
    set_id, n = qs.save_ruleset("zz test quick scan", "", flt, tg, "pytest")
    try:
        assert n == len(flt) + 2 and any(s["set_id"] == set_id for s in qs.list_rulesets())
        rules = qs.load_ruleset(set_id)
        assert [r["section"] for r in rules] == ["filter"] * len(flt) + ["target", "target"]
        assert rules[-1]["rule_type"] == "distance"          # saved order comes back (weighted before distance)
        t = rules[-2]
        assert t["rule_type"] == "weighted" and t["direction"] == "lower" and t["target_val"] == 60 and t["weight"] == 2
        assert rules[0]["value1"] == 167 and rules[0]["operator"] == "="
        qs.delete_ruleset(set_id)
        assert not any(s["set_id"] == set_id for s in qs.list_rulesets())
    finally:
        execute("DELETE FROM tblrequirementrule WHERE set_id=%s", [set_id])
        execute("DELETE FROM tblrequirementset WHERE set_id=%s", [set_id])
