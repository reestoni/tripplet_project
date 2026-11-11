"""ref_compare.py - "Compare with Ref / Target" in Show Experiment
(Nutzerwunsch 2026-11-11): which trials of a series meet ALL the criteria the
user cares about - against a reference sample and/or own target values.

Pure logic, no Qt widgets - tested in tests/test_ref_compare.py. The dialog
is ui/ref_compare_dialog.py, saved criteria sets db/ref_criteria.py.

Metrics = the numeric rows of every lab tab, exactly as shown in Show
Experiment (one column per trial). Per metric the user sets (no defaults -
e.g. a lower stability can be the goal):

  dir     higher / lower / close
  target  own target value (optional) - used instead of the reference value
  tol     tolerance in % of the target/reference

  higher  passes if value >= base - tol %   (tol 0 = at least as high)
  lower   passes if value <= base + tol %
  close   passes if |value - base| <= tol % of base

base = target if set, else the reference value. Without both the criterion
can't be judged (NO_BASE) and does not count. A trial passes when it passes
every counted criterion; a missing value fails.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

HIGHER, LOWER, CLOSE = "higher", "lower", "close"
DIRECTIONS = (HIGHER, LOWER, CLOSE)
DIR_LABEL = {HIGHER: "higher ↑", LOWER: "lower ↓", CLOSE: "≈"}
DEFAULT_TOL = {HIGHER: 0.0, LOWER: 0.0, CLOSE: 2.0}

PASS, FAIL, MISSING, INFO, NO_BASE = "pass", "fail", "missing", "info", "no_base"


def to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip().replace(",", ".")
    if not s or s in ("—", "-", "–", "None"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def metric_key(model_attr: str, row_title: str) -> str:
    """Stable across series: lab model attribute + row title."""
    return f"{model_attr}|{row_title}"


def collect_metrics(sources: List[Dict[str, Any]], trial_ids: List[int],
                    ref_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """sources: [{attr, tab, rows: [(title, [cell per trial column])]}] (rows
    without the info rows at the top). With a reference: the metrics where
    it has a number; without (own targets): every row where any trial has a
    number. Returns [{key, tab, title, ref (float|None), values: {trial_id: float|None}}]."""
    ref_col = None
    if ref_id is not None:
        try:
            ref_col = trial_ids.index(int(ref_id))
        except ValueError:
            return []
    out: List[Dict[str, Any]] = []
    for src in sources:
        for title, cells in src.get("rows", []):
            values = {int(t): (to_float(cells[i]) if i < len(cells) else None) for i, t in enumerate(trial_ids)}
            if ref_col is not None:
                ref = to_float(cells[ref_col]) if ref_col < len(cells) else None
                if ref is None:
                    continue
            else:
                ref = None
                if all(v is None for v in values.values()):
                    continue
            out.append({"key": metric_key(src["attr"], title), "tab": src.get("tab") or src["attr"],
                        "title": title, "ref": ref, "values": values})
    return out


def base_of(metric: Dict[str, Any], crit: Optional[Dict[str, Any]]) -> Optional[float]:
    """The value a trial is compared with: own target, else the reference."""
    t = to_float((crit or {}).get("target"))
    return t if t is not None else metric.get("ref")


def judge(value: Optional[float], base: Optional[float], crit: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """{status, diff (% vs base or None)} of one value against one criterion."""
    diff = None
    if value is not None and base:
        diff = (value - base) / abs(base) * 100.0
    elif value is not None and base is not None:
        diff = 0.0 if value == base else None
    d = (crit or {}).get("dir")
    if d not in DIRECTIONS:
        return {"status": INFO, "diff": diff}
    if base is None:
        return {"status": NO_BASE, "diff": None}
    if value is None:
        return {"status": MISSING, "diff": None}
    tol = (crit or {}).get("tol")
    tol = DEFAULT_TOL[d] if tol is None else max(float(tol), 0.0)
    margin = abs(base) * tol / 100.0
    if d == HIGHER:
        ok = value >= base - margin
    elif d == LOWER:
        ok = value <= base + margin
    else:
        ok = abs(value - base) <= margin
    return {"status": PASS if ok else FAIL, "diff": diff}


def counted(metric: Dict[str, Any], crit: Optional[Dict[str, Any]]) -> bool:
    """A criterion counts when it has a direction and something to compare with."""
    return (crit or {}).get("dir") in DIRECTIONS and base_of(metric, crit) is not None


def evaluate(metrics: List[Dict[str, Any]], trial_ids: List[int], criteria: Dict[str, Dict[str, Any]],
             skip_ids=()) -> List[Dict[str, Any]]:
    """One row per trial (references in skip_ids left out), best first:
    [{trial_id, cells: {key: judge()}, passed, total, all_pass}]."""
    active = [m for m in metrics if counted(m, criteria.get(m["key"]))]
    skip = {int(s) for s in skip_ids}
    rows = []
    for order, tid in enumerate(trial_ids):
        tid = int(tid)
        if tid in skip:
            continue
        cells = {m["key"]: judge(m["values"].get(tid), base_of(m, criteria.get(m["key"])), criteria.get(m["key"]))
                 for m in metrics}
        passed = sum(1 for m in active if cells[m["key"]]["status"] == PASS)
        rows.append({"trial_id": tid, "cells": cells, "passed": passed, "total": len(active),
                     "all_pass": bool(active) and passed == len(active), "_order": order})
    rows.sort(key=lambda r: (-r["passed"], r["_order"]))
    return rows


def failing(row: Dict[str, Any], metrics: List[Dict[str, Any]]) -> List[str]:
    """Titles of the counted criteria a trial misses - for the tooltip."""
    return [m["title"] for m in metrics if row["cells"][m["key"]]["status"] in (FAIL, MISSING)]
