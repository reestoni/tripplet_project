# db/plausibility.py
"""Plausibility check of machine settings on save, Nutzerwunsch 2026-10-15
(typos like 35 instead of 3.5 bar, 5500 instead of 550 m/min).

For every numeric machine field (tblMachineFields, FieldFunction
onlyDoubles/onlyInteger) the usual range is derived from all earlier trials
of the same machine (reference samples excluded): the 1st and 99th
percentile P01/P99. A value is "unusual" outside

    P01 - span/2 ... P99 + span/2      span = max(P99 - P01, |median|/2)
    and below P01/3 (if P01 > 0)       catches the "factor 10 too small" typo

At least MIN_VALUES earlier values are needed and they must not all be the
same, otherwise no check. Only a
warning on save - the user can save anyway. Lab values are not checked:
they depend on the yarn (titer 20 or 600 dtex), not on the machine.

Computed per machine once per session (two queries), no table needed.
"""
from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional, Tuple

MIN_VALUES = 30

_cache: Dict[Any, Dict[Tuple[str, str], Dict[str, float]]] = {}


def _num(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def _percentile(sorted_vals: List[float], p: float) -> float:
    k = (len(sorted_vals) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def range_of(values: List[float]) -> Optional[Dict[str, float]]:
    vals = sorted(v for v in values if v is not None)
    if len(vals) < MIN_VALUES:
        return None
    p01, p99 = _percentile(vals, 0.01), _percentile(vals, 0.99)
    if p99 == p01:
        return None  # (almost) always the same value - no idea what is usual
    med = statistics.median(vals)
    span = max(p99 - p01, abs(med) / 2.0)
    lo, hi = p01 - span / 2.0, p99 + span / 2.0
    if p01 > 0:
        lo = max(lo, p01 / 3.0)
    return {"lo": lo, "hi": hi, "p01": p01, "p99": p99, "n": len(vals)}


def _numeric_fields(machine_id) -> List[Tuple[str, str]]:
    from db.connection import fetch_all
    rows = fetch_all("SELECT OriginalName, FieldFunction, COALESCE(StorageTable, 'tbltrial') AS StorageTable "
                     "FROM tblMachineFields WHERE MachineID = ?", [machine_id])
    out = []
    for r in rows:
        ff = str(r.get("FieldFunction") or "").lower()
        if "double" in ff or "integer" in ff:
            out.append((str(r.get("StorageTable") or "tbltrial").lower(), str(r.get("OriginalName") or "")))
    # fixed rows of Machine Data, always numeric
    out.append(("tbltrial", "AirPressure"))
    return out


def ranges_for_machine(machine_id) -> Dict[Tuple[str, str], Dict[str, float]]:
    """{(table lower, column lower): range} - cached per session."""
    if machine_id in (None, ""):
        return {}
    if machine_id in _cache:
        return _cache[machine_id]
    out: Dict[Tuple[str, str], Dict[str, float]] = {}
    try:
        from db.connection import fetch_all, get_columns_map
        from db.trial_reference import exclude_references_sql
        fields = _numeric_fields(machine_id)
        for table, alias, join in (
                ("tbltrial", "t", ""),
                ("tbltrialsettings", "ts", "JOIN tblTrial t ON t.ID = ts.TrialID ")):
            cols_map = get_columns_map(table)
            cols = sorted({cols_map[f.lower()] for tb, f in fields if tb == table and f.lower() in cols_map})
            if not cols:
                continue
            sel = ", ".join(f"{alias}.`{c}` AS `{c}`" for c in cols)
            frm = f"FROM {table} {alias} " + (join if join else "")
            rows = fetch_all(
                f"SELECT {sel} {frm}JOIN tblTrialSeries s ON s.ID = t.TrialSeriesID "
                f"WHERE s.MachineID = ? AND {exclude_references_sql('t')}", [machine_id])
            for c in cols:
                rg = range_of([_num(r.get(c)) for r in rows])
                if rg:
                    out[(table, c.lower())] = rg
    except Exception:
        out = {}
    _cache[machine_id] = out
    return out


def is_unusual(rg: Optional[Dict[str, float]], value: Any) -> bool:
    v = _num(value)
    return rg is not None and v is not None and not (rg["lo"] <= v <= rg["hi"])


def fmt(x: float) -> str:
    return f"{x:.3g}" if abs(x) < 1000 else f"{x:.0f}"


def find_unusual(model, machine_id) -> List[Dict[str, Any]]:
    """Unusual values among the model's unsaved changes:
    [{"row": data row, "col": col, "text": "V3 · Air Pressure (bar): 35 (usually 2 - 8)"}]."""
    if model is None or not getattr(model, "_dirty", None):
        return []
    ranges = ranges_for_machine(machine_id)
    if not ranges:
        return []
    from PySide6.QtCore import Qt
    n_hdr = getattr(model, "_n_hdr", 0)
    out, seen = [], set()
    for r, c, _txt in reversed(model._dirty):  # newest edit of a cell counts
        if (r, c) in seen:
            continue
        seen.add((r, c))
        b = model.get_binding(r, c)
        if b is None:
            continue
        rg = ranges.get((str(b.table).lower(), str(b.field).lower()))
        val = model.get_cell_value(r, c)
        if not is_unusual(rg, val):
            continue
        hdr = []
        # trial-wide values (tblTrial): only the trial number, not the ply
        for h in range(1 if str(b.table).lower() == "tbltrial" else n_hdr):
            t = str(model.data(model.index(h, c + 1), Qt.DisplayRole) or "").strip()
            if t and t not in hdr:
                hdr.append(t)
        where = " · ".join(hdr + [model._row_titles[r]])
        out.append({"row": r, "col": c,
                    "text": f"{where}: {val}   (usually {fmt(rg['p01'])} – {fmt(rg['p99'])})"})
    out.sort(key=lambda e: (e["col"], e["row"]))
    return out
