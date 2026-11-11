"""Compare with Ref (ui/ref_compare.py, Nutzerwunsch 2026-11-11): which
trials beat a reference sample in all criteria the user sets. No DB needed;
checked on prod series 460 (Golden Lady) by hand 2026-11-11: FP/m higher, FP
CV lower, Stability@0.3 lower -> 8 of 22 trials pass."""
import pytest

from ui import ref_compare as rc

TRIALS = [100, 1, 2, 3]   # 100 = reference sample
SOURCES = [{"attr": "model_itemat", "tab": "Itemat", "rows": [
    ("FP/m", ["46", "136.7", "40", ""]),
    ("FP CV (%)", ["103.1", "22.3", "120", "50"]),
    ("Stability@0.3", ["71.9", "94.7", "70", "71.9"]),
    ("Comment", ["ok", "x", "y", "z"]),          # not numeric -> no metric
]}, {"attr": "model_titer", "tab": "Titer", "rows": [("Titer", ["79.7", "80.5", "78.0", "79.7"])]}]


def _metrics():
    return rc.collect_metrics(SOURCES, TRIALS, 100)


def test_collect_only_numeric_rows_with_a_reference_value():
    ms = _metrics()
    assert [m["title"] for m in ms] == ["FP/m", "FP CV (%)", "Stability@0.3", "Titer"]
    assert ms[0]["key"] == "model_itemat|FP/m"
    assert ms[0]["values"][3] is None and ms[0]["ref"] == 46.0


@pytest.mark.parametrize("value, crit, status", [
    (50, {"dir": "higher"}, rc.PASS),
    (46, {"dir": "higher"}, rc.PASS),                 # equal counts
    (45, {"dir": "higher"}, rc.FAIL),
    (45, {"dir": "higher", "tol": 5}, rc.PASS),        # 5 % of 46 = 2.3
    (40, {"dir": "lower"}, rc.PASS),
    (47, {"dir": "lower"}, rc.FAIL),
    (46.8, {"dir": "close"}, rc.PASS),                 # default ±2 %
    (48, {"dir": "close"}, rc.FAIL),
    (None, {"dir": "higher"}, rc.MISSING),
    (10, None, rc.INFO),
])
def test_judge(value, crit, status):
    assert rc.judge(value, 46.0, crit)["status"] == status


def test_evaluate_best_first_and_all_pass():
    ms = _metrics()
    crit = {"model_itemat|FP/m": {"dir": "higher"}, "model_itemat|FP CV (%)": {"dir": "lower"},
            "model_itemat|Stability@0.3": {"dir": "lower"}}
    rows = rc.evaluate(ms, TRIALS, crit, skip_ids=[100])
    assert [r["trial_id"] for r in rows] == [1, 3, 2]   # best first, ties in series order
    by = {r["trial_id"]: r for r in rows}
    assert by[1]["passed"] == 2 and not by[1]["all_pass"]            # stability higher
    assert by[2]["passed"] == 1                                       # FP/m and CV worse
    assert by[3]["passed"] == 2 and rc.failing(by[3], ms) == ["FP/m"]  # FP/m missing
    crit["model_itemat|Stability@0.3"] = {"dir": "higher"}
    rows = rc.evaluate(ms, TRIALS, crit, skip_ids=[100])
    assert rows[0]["trial_id"] == 1 and rows[0]["all_pass"]


def test_no_criteria_nobody_passes():
    rows = rc.evaluate(_metrics(), TRIALS, {}, skip_ids=[100])
    assert all(r["total"] == 0 and not r["all_pass"] for r in rows)


def test_parse_drops_ignored_entries():
    from db import ref_criteria
    assert ref_criteria.parse('{"a": {"dir": "lower"}, "b": {"dir": null}, "c": 3}') == {"a": {"dir": "lower"}}
    assert ref_criteria.parse("not json") == {}
