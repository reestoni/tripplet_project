"""ref_compare.py - "Compare with Ref" in Show Experiment (Nutzerwunsch
2026-11-11): which trials of a series are better than a reference sample in
ALL the metrics the user cares about?

Pure logic, no Qt widgets - tested in tests/test_ref_compare.py. The dialog
is ui/ref_compare_dialog.py, saved criteria sets db/ref_criteria.py.

Metrics = the numeric rows of every lab tab, exactly as shown in Show
Experiment (one column per trial). "Better" is set per metric by the user
(no defaults - e.g. a lower stability can be the goal):

  higher  passes if value >= ref - tol %   (tol 0 = at least as high)
  lower   passes if value <= ref + tol %
  close   passes if |value - ref| <= tol % of ref
  (none)  ignored

A trial passes when it passes every set criterion; a missing value fails.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

HIGHER, LOWER, CLOSE = "higher", "lower", "close"
DIRECTIONS = (HIGHER, LOWER, CLOSE)
DIR_LABEL = {HIGHER: "higher ↑", LOWER: "lower ↓", CLOSE: "≈ Ref"}
DEFAULT_TOL = {HIGHER: 0.0, LOWER: 0.0, CLOSE: 2.0}

PASS, FAIL, MISSING, INFO = "pass", "fail", "missing", "info"


def to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip().replace(",", ".")
    if not s or s in ("—", "-", "None"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def metric_key(model_attr: str, row_title: str) -> str:
    """Stable across series: lab model attribute + row title."""
    return f"{model_attr}|{row_title}"


def collect_metrics(sources: List[Dict[str, Any]], trial_ids: List[int], ref_id: int) -> List[Dict[str, Any]]:
    """sources: [{attr, tab, rows: [(title, [cell per trial column])]}] (rows
    without the info rows at the top). Returns the metrics where the
    reference has a number:
    [{key, tab, title, ref, values: {trial_id: float|None}}]."""
    try:
        ref_col = trial_ids.index(int(ref_id))
    except ValueError:
        return []
    out: List[Dict[str, Any]] = []
    for src in sources:
        for title, cells in src.get("rows", []):
            ref = to_float(cells[ref_col]) if ref_col < len(cells) else None
            if ref is None:
                continue
            values = {int(t): (to_float(cells[i]) if i < len(cells) else None) for i, t in enumerate(trial_ids)}
            out.append({"key": metric_key(src["attr"], title), "tab": src.get("tab") or src["attr"],
                        "title": title, "ref": ref, "values": values})
    return out


def judge(value: Optional[float], ref: float, crit: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """{status, diff (% vs ref or None)} of one value against one criterion."""
    diff = None
    if value is not None and ref:
        diff = (value - ref) / abs(ref) * 100.0
    elif value is not None:
        diff = 0.0 if value == ref else None
    d = (crit or {}).get("dir")
    if d not in DIRECTIONS:
        return {"status": INFO, "diff": diff}
    if value is None:
        return {"status": MISSING, "diff": None}
    tol = (crit or {}).get("tol")
    tol = DEFAULT_TOL[d] if tol is None else max(float(tol), 0.0)
    margin = abs(ref) * tol / 100.0
    if d == HIGHER:
        ok = value >= ref - margin
    elif d == LOWER:
        ok = value <= ref + margin
    else:
        ok = abs(value - ref) <= margin
    return {"status": PASS if ok else FAIL, "diff": diff}


def evaluate(metrics: List[Dict[str, Any]], trial_ids: List[int], criteria: Dict[str, Dict[str, Any]],
             skip_ids=()) -> List[Dict[str, Any]]:
    """One row per trial (references in skip_ids left out), best first:
    [{trial_id, cells: {key: judge()}, passed, total, all_pass}]."""
    active = [m for m in metrics if (criteria.get(m["key"]) or {}).get("dir") in DIRECTIONS]
    skip = {int(s) for s in skip_ids}
    rows = []
    for order, tid in enumerate(trial_ids):
        tid = int(tid)
        if tid in skip:
            continue
        cells = {m["key"]: judge(m["values"].get(tid), m["ref"], criteria.get(m["key"])) for m in metrics}
        passed = sum(1 for m in active if cells[m["key"]]["status"] == PASS)
        rows.append({"trial_id": tid, "cells": cells, "passed": passed, "total": len(active),
                     "all_pass": bool(active) and passed == len(active), "_order": order})
    rows.sort(key=lambda r: (-r["passed"], r["_order"]))
    return rows


def failing(row: Dict[str, Any], metrics: List[Dict[str, Any]]) -> List[str]:
    """Titles of the set criteria a trial misses - for the tooltip."""
    return [m["title"] for m in metrics if row["cells"][m["key"]]["status"] in (FAIL, MISSING)]
