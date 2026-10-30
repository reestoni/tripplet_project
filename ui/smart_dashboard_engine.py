# ui/smart_dashboard_engine.py
"""Smart Chart dashboard ("wie Power BI", Nutzerwunsch 2026-10-30) - the
computing part without any UI, so it is testable.

A report (spec) has pages; a page has visuals and its own filters; each
visual has a type, "wells" (field keys, like the Power BI Visualizations
pane), its own filters and a place on a 12-column grid (x, y, w, h; one
row = GRID_ROW px):
    {"pages": [{"id": "p1", "title": "Page 1", "filters": [...], "visuals": [
        {"id": "v3", "type": "box", "x": 0, "y": 6, "w": 6, "h": 16, "title": "",
         "wells": {"x": "machine", "y": "fpm"}, "agg": "avg", "filters": []}]}],
     "active": "p1"}
Filters for a visual = "Find trials" (all pages) + page filters + visual
filters + clicks/slicers of the OTHER visuals of the same page.

compute_visual() turns one visual into a result for the web page:
    {"kind": "plotly", "figure": {...}, "fair": {...}, "n": 123}
    {"kind": "kpi", "value": "124", "unit": "FP/m", "sub": "n = 312 · ± 18 SD"}
    {"kind": "table", "head": [...], "rows": [[tid, cells…]], "more": 0}
    {"kind": "empty", "message": "Drag a field into Y axis"}
click_filters() turns a click into cross-filters for the other visuals.

Statistics (the superuser Statistics page as visuals, Etappe 5): the
aggregations "Count of trial series / experiments" count distinct series /
experiments and include the EMPTY rows of the dataset (series without
trials, experiments without series), so the numbers match the Statistics
page. Visual type "column" = counts or totals per category, stacked /
side by side / 100 %; time fields (Month, Year …) run in order with empty
months filled in.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from db import fairness as fz
from db.trial_explorer import NONE_LABEL, TIME_KEYS, Result, TrialDataset, cat_label, cat_labels
from ui.smart_chart_figure import CHART_TYPES, PALETTES, build_figure, _fmt, _sort_key

_kfmt = fz._fmt   # readable rounding for cards: 114 · 3.84 · 84.6

WELLS: Dict[str, Tuple[str, str]] = {      # key -> (label, accepted kinds)
    "x": ("X axis", "any"), "y": ("Y axis", "num"), "legend": ("Legend (colour)", "any"),
    "split": ("Small multiples", "any"), "rows": ("Rows", "any"), "cols": ("Columns", "any"),
    "value": ("Value", "num"), "columns": ("Columns", "any"), "field": ("Field", "any"),
    "drill": ("Drill down to (double-click a bar)", "any"),
}
MULTI_WELLS = ("columns", "drill")
DRILL_TYPES = ("bar", "box", "violin", "line")
# Slicer ("Datenschnitt", Nutzerwunsch 2026-10-30): how it looks
SLICER_STYLES = {"list": "List", "dropdown": "Dropdown", "tiles": "Tiles", "between": "Between (range)"}
SLICER_MAX_OPTIONS = 300
CHART_WELLS = ["x", "y", "legend", "split"]
VISUAL_TYPES: Dict[str, Dict[str, Any]] = {
    **{k: {"label": lab, "tip": tip, "wells": (["y", "legend", "split"] if k == "hist" else
                                               ["x", "y", "split"] if k == "density" else
                                               CHART_WELLS + ["drill"] if k in DRILL_TYPES else CHART_WELLS),
           "target": k not in ("density",)}
       for k, (lab, tip) in CHART_TYPES.items()},
    "column": {"label": "Columns", "tip": "Count or total per category - stacked, side by side or 100 %. "
                                          "Months and years run in order",
               "wells": ["x", "legend", "value"], "agg": True, "target": True, "defagg": "count"},
    "matrix": {"label": "Matrix", "tip": "Table of a value per row and column, coloured - gaps show missing trials",
               "wells": ["rows", "cols", "value"], "agg": True, "target": True},
    "kpi": {"label": "Card", "tip": "One number: count, average, best …", "wells": ["value"], "agg": True,
            "target": True},
    "table": {"label": "Table", "tip": "The trials with the fields you choose", "wells": ["columns"]},
    "slicer": {"label": "Slicer", "tip": "Pick values to filter all other visuals: list, dropdown, tiles or a range",
               "wells": ["field"]},
}
AGGS = {"avg": "Average", "median": "Median", "min": "Min", "max": "Max", "sd": "Std. deviation",
        "sum": "Sum", "count": "Count of trials", "count_series": "Count of trial series",
        "count_experiments": "Count of experiments"}
# counting aggregations need no Value; series/experiments include the empty rows
COUNT_AGGS = ("count", "count_series", "count_experiments")
ENTITY = {"count": ("Trials", "trials"), "count_series": ("Trial series", "trial series"),
          "count_experiments": ("Experiments", "experiments")}
STACK_MODES = {"stacked": "Stacked", "grouped": "Side by side", "percent": "100 % stacked"}
MAX_LEGEND = 8
MAX_TIME_POINTS = 240
MAX_ROWS, MAX_COLS = 20, 15
MAX_CATEGORIES = 25          # bars / boxes per chart; rarer values are left out (with a note)
TABLE_LIMIT = 500


GRID_COLS, GRID_ROW = 12, 20
DEFAULT_H = {"kpi": 6, "slicer": 9, "table": 16, "matrix": 16, "column": 16}


def default_h(v: Dict[str, Any]) -> int:
    if v.get("type") == "slicer" and v.get("style") == "between":
        return 6
    return DEFAULT_H.get(v.get("type"), 16)


def auto_layout(visuals: List[Dict[str, Any]]) -> None:
    """Give visuals without a place one: left to right, row by row (old
    pages only had a width). Visuals that have a place keep it."""
    placed = [v for v in visuals if all(isinstance(v.get(k), (int, float)) for k in ("x", "y", "w", "h"))]
    y0 = max((int(v["y"]) + int(v["h"]) for v in placed), default=0)
    x, y, row_h = 0, y0, 0
    for v in visuals:
        if v in placed:
            continue
        w = int(v.get("w") or 6)
        w = max(1, min(GRID_COLS, w))
        h = int(v.get("h") or default_h(v))
        if x + w > GRID_COLS:
            x, y, row_h = 0, y + row_h, 0
        v.update(x=x, y=y, w=w, h=h)
        x += w
        row_h = max(row_h, h)


def normalize_spec(spec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Any saved spec (Etappe 1: {"title", "visuals"}) -> pages format."""
    if not spec:
        spec = default_page()
    if "pages" not in spec:
        spec = {"pages": [{"id": "p1", "title": spec.get("title") or "Page 1",
                           "visuals": spec.get("visuals") or [], "filters": []}], "active": "p1"}
    pages = [p for p in spec.get("pages") or [] if isinstance(p, dict)] or [
        {"id": "p1", "title": "Page 1", "visuals": [], "filters": []}]
    for i, pg in enumerate(pages):
        pg.setdefault("id", f"p{i + 1}")
        pg.setdefault("title", f"Page {i + 1}")
        pg.setdefault("filters", [])
        pg.setdefault("visuals", [])
        for v in pg["visuals"]:
            v.setdefault("filters", [])
        auto_layout(pg["visuals"])
    active = spec.get("active") if any(p["id"] == spec.get("active") for p in pages) else pages[0]["id"]
    calc = [c for c in spec.get("calc") or [] if isinstance(c, dict) and str(c.get("key", "")).startswith("calc_")]
    return {"pages": pages, "active": active, "calc": calc}


def active_page(spec: Dict[str, Any]) -> Dict[str, Any]:
    return next((p for p in spec["pages"] if p["id"] == spec.get("active")), spec["pages"][0])


def visual_filters(ds: TrialDataset, page: Dict[str, Any], v: Dict[str, Any], base: List[Dict[str, Any]],
                   cross: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """All filters that apply to visual v (see module docstring)."""
    known = ds.fields
    own = [f for f in (page.get("filters") or []) + (v.get("filters") or []) if f.get("key") in known]
    others: List[Dict[str, Any]] = []
    for sv in page.get("visuals") or []:
        if sv.get("id") == v.get("id"):
            continue
        others += cross.get(sv.get("id"), [])
        sf = slicer_filter(ds, sv)
        targets = sv.get("targets")          # None = all visuals of the page (Nutzerwunsch 2026-10-30)
        if sf is not None and (targets is None or v.get("id") in targets):
            others.append(sf)
    return list(base) + own + others


def describe_filters(ds: TrialDataset, flts: List[Dict[str, Any]]) -> List[str]:
    from db.trial_explorer import describe_filter, describe_selection
    return [describe_selection(f) if f.get("ids") is not None else describe_filter(ds.fields[f["key"]], f)
            for f in flts if f.get("ids") is not None or f.get("key") in ds.fields]


def drill_state(ds: TrialDataset, v: Dict[str, Any]):
    """(x key, extra filters, info) of a visual with drill levels."""
    w = v.get("wells") or {}
    levels = [k for k in [w.get("x")] + list(w.get("drill") or []) if k in ds.fields]
    if v.get("type") not in DRILL_TYPES or len(levels) < 2:
        return w.get("x"), [], None
    path = [p for p in v.get("drillpath") or [] if p.get("key") in ds.fields][:len(levels) - 1]
    depth = len(path)
    extra = [f for f in (_filter_for(ds, p["key"], p["value"]) for p in path) if f]
    info = {"levels": [ds.fields[k].title for k in levels], "depth": depth, "cur": levels[depth],
            "path": [f"{ds.fields[p['key']].title}: {p['value']}" for p in path],
            "can_down": depth < len(levels) - 1}
    return levels[depth], extra, info


def _target(v: Dict[str, Any]) -> Optional[Tuple[float, str]]:
    t = v.get("target") or {}
    val = _num(t.get("value"))
    return (val, "lower" if t.get("better") == "lower" else "higher") if val is not None else None


def default_page() -> Dict[str, Any]:
    v = lambda i, t, w, **wells: {"id": f"v{i}", "type": t, "w": w, "title": "", "agg": "avg", "wells": wells}
    return {"title": "Page 1", "visuals": [
        {**v(8, "slicer", 6, field="machine"), "style": "tiles"},
        {**v(9, "slicer", 6, field="air_pressure"), "style": "between"},
        {**v(1, "kpi", 3), "agg": "count"},
        v(2, "kpi", 3, value="fpm"),
        v(3, "kpi", 3, value="stab_06"),
        v(4, "kpi", 3, value="tenacity"),
        v(5, "box", 6, x="machine", y="fpm"),
        v(6, "matrix", 6, rows="machine", cols="air_pressure", value="fpm"),
        v(7, "trend", 12, x="air_pressure", y="tenacity", legend="machine"),
    ]}


# ── helpers ──────────────────────────────────────────────────────────────
def _num(v) -> Optional[float]:
    if v is None or isinstance(v, bool):
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def aggregate(vals: Sequence[float], agg: str) -> Optional[float]:
    xs = [x for x in vals if x is not None]
    if agg == "count":
        return float(len(vals))
    if not xs:
        return None
    if agg == "sum":
        return sum(xs)
    if agg == "min":
        return min(xs)
    if agg == "max":
        return max(xs)
    if agg == "median":
        s = sorted(xs)
        m = len(s) // 2
        return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2
    mean = sum(xs) / len(xs)
    if agg == "sd":
        return math.sqrt(sum((a - mean) ** 2 for a in xs) / (len(xs) - 1)) if len(xs) > 1 else 0.0
    return mean


def count_of(ds: TrialDataset, tids: Sequence[int], agg: str) -> int:
    """Trials (real ones), distinct trial series or distinct experiments."""
    if agg == "count_series":
        return len({ds.by_id[t].series_id for t in tids if ds.by_id[t].series_id is not None})
    if agg == "count_experiments":
        return len({ds.by_id[t].exp_pk for t in tids if ds.by_id[t].exp_pk is not None})
    return sum(1 for t in tids if not ds.by_id[t].empty)


def _apply(ds: TrialDataset, v: Dict[str, Any], filters, ply_scope: str) -> Result:
    """Rows of a visual: counting series/experiments also takes the empty ones."""
    agg = v.get("agg") or VISUAL_TYPES.get(v.get("type") or "", {}).get("defagg") or "avg"
    empty = agg in ("count_series", "count_experiments") and v.get("type") in ("kpi", "matrix", "column")
    return ds.apply(filters, ply_scope, include_empty=empty)


def _counted(ds: TrialDataset, ids: Sequence[int], agg: str) -> List[int]:
    """Rows that count for agg - an experiment without series adds no series, a trial without
    an experiment no experiment, so they create no (empty) categories either."""
    if agg not in COUNT_AGGS:
        return list(ids)
    return [t for t in ids if count_of(ds, [t], agg)]


def _cell(ds: TrialDataset, tids: Sequence[int], res: Result, vk: Optional[str], agg: str) -> Optional[float]:
    if agg in COUNT_AGGS:
        return float(count_of(ds, tids, agg))
    if not vk:
        return None
    return aggregate([_num(ds.value(vk, t, res.matched.get(t))) for t in tids], agg)


def _labels(ds: TrialDataset, key: str, tid: int, m) -> List[str]:
    if ds.fields[key].kind == "num":
        return [_label(ds, key, tid, m)]
    return cat_labels(ds.value(key, tid, m))


def _time_axis(labels: List[str], key: str) -> List[str]:
    """All years / months from the first to the last label (gaps filled), "(none)" last."""
    real = sorted(lab for lab in labels if lab != NONE_LABEL)
    tail = [NONE_LABEL] if NONE_LABEL in labels else []
    if not real:
        return tail
    try:
        if TIME_KEYS.get(key) == "year":
            a, b = int(real[0]), int(real[-1])
            full = [str(y) for y in range(a, b + 1)]
        else:
            (ya, ma), (yb, mb) = (map(int, real[0].split("-")), map(int, real[-1].split("-")))
            full, y, mo = [], ya, ma
            while (y, mo) <= (yb, mb):
                full.append(f"{y:04d}-{mo:02d}")
                y, mo = (y + 1, 1) if mo == 12 else (y, mo + 1)
    except (TypeError, ValueError):
        return real + tail
    return (full if len(full) <= MAX_TIME_POINTS else real) + tail


def _label(ds: TrialDataset, key: str, tid: int, m) -> str:
    v = ds.value(key, tid, m)
    if ds.fields[key].kind == "num":
        x = _num(v)
        return _fmt(x) if x is not None else NONE_LABEL
    return cat_label(v)


def auto_title(ds: TrialDataset, v: Dict[str, Any]) -> str:
    w, f, t = v.get("wells") or {}, ds.fields, v.get("type")
    title = lambda k: f[w[k]].title if w.get(k) in f else ""
    if t == "kpi":
        agg = v.get("agg") or "avg"
        if agg in COUNT_AGGS or not title("value"):
            return ENTITY.get(agg, ENTITY["count"])[0]
        return f"{AGGS[agg]} {title('value')}"
    if t == "column":
        agg = v.get("agg") or "count"
        what = ENTITY[agg][0] if agg in COUNT_AGGS else f"{AGGS.get(agg, '')} {title('value')}".strip()
        return (f"{what} per {title('x')}" if title("x") else what) + (f" by {title('legend')}" if title("legend") else "")
    if t == "matrix":
        return f"{AGGS.get(v.get('agg') or 'avg', '')} {title('value')} · {title('rows')} × {title('cols')}".strip(" ·×")
    if t == "table":
        return "Trials"
    if t == "slicer":
        return title("field") or "Slicer"
    if t == "hist":
        return f"Distribution of {title('y')}" if title("y") else "Histogram"
    if title("y") and title("x"):
        return f"{title('y')} by {title('x')}" + (f" per {title('legend')}" if title("legend") else "")
    return CHART_TYPES.get(t, ("Visual", ""))[0]


def _fair_dict(a) -> Optional[Dict[str, str]]:
    if a is None or a.level == fz.NONE:
        return None
    return {"level": a.level, "headline": a.headline, "text": a.sentence, "grouping": a.grouping}


# ── compute ──────────────────────────────────────────────────────────────
def compute_visual(ds: TrialDataset, v: Dict[str, Any], filters: List[Dict[str, Any]],
                   ply_scope: str = "any", palette: str = "trippleT") -> Dict[str, Any]:
    t = v.get("type") or "points"
    w = {k: val for k, val in (v.get("wells") or {}).items() if val and (k in MULTI_WELLS or val in ds.fields)}
    drill_x, drill_extra, drill = drill_state(ds, v)
    if drill:
        w["x"] = drill_x
        filters = list(filters) + drill_extra
    res = _apply(ds, v, filters, ply_scope)
    out: Dict[str, Any] = {"title": v.get("title") or auto_title(ds, v), "n": count_of(ds, res.ids, "count")}
    if t == "kpi":
        r = _kpi(ds, res, w.get("value"), v.get("agg") or "avg")
        tg = _target(v)
        if tg and r.get("raw") is not None:
            good = r["raw"] >= tg[0] if tg[1] == "higher" else r["raw"] <= tg[0]
            r["status"] = "good" if good else "bad"
            r["sub"] = (r.get("sub") + " · " if r.get("sub") else "") + f"target {_kfmt(tg[0])}"
        return {**out, **r}
    if t == "table":
        return {**out, **_table(ds, res, [k for k in (v.get("wells") or {}).get("columns") or [] if k in ds.fields])}
    if t == "slicer":
        if not w.get("field"):
            return {**out, "kind": "empty", "message": "Drag a field into Field"}
        return {**out, **_slicer(ds, res, w["field"], v)}
    if t == "column":
        agg = v.get("agg") or "count"
        if not w.get("x") or (not w.get("value") and agg not in COUNT_AGGS):
            return {**out, "kind": "empty", "message": "Drag a field into X axis" if not w.get("x") else
                    "Drag a number into Value - or count trials, series or experiments"}
        r = _column(ds, res, w["x"], w.get("legend"), w.get("value"), agg, v.get("stack") or "stacked", palette)
        tg = _target(v)
        if r.get("kind") == "plotly" and tg and (v.get("stack") or "stacked") != "percent":
            lay = r["figure"]["layout"]
            lay.setdefault("shapes", []).append({"type": "line", "xref": "paper", "yref": "y", "x0": 0, "x1": 1,
                                                 "y0": tg[0], "y1": tg[0],
                                                 "line": {"color": "#C62828", "width": 2, "dash": "dash"}})
            lay.setdefault("annotations", []).append({
                "text": f"Target {_kfmt(tg[0])}", "xref": "paper", "yref": "y", "x": 1, "y": tg[0],
                "xanchor": "right", "yanchor": "bottom", "showarrow": False,
                "font": {"size": 10, "color": "#C62828"}})
        return {**out, **r}
    if t == "matrix":
        if not (w.get("rows") and w.get("cols")) or (not w.get("value") and v.get("agg") not in COUNT_AGGS):
            return {**out, "kind": "empty", "message": "Drag fields into Rows, Columns and Value"}
        r = _matrix(ds, res, w["rows"], w["cols"], w.get("value"), v.get("agg") or "avg")
        tg = _target(v)
        if r.get("kind") == "plotly" and tg:
            tr = r["figure"]["data"][0]
            zs = [z for row in tr["z"] for z in row if z is not None]
            if zs:          # colour around the target: green on the good side, red on the bad side
                lo, hi = min(zs + [tg[0]]), max(zs + [tg[0]])
                span = (hi - lo) or 1.0
                mid = (tg[0] - lo) / span
                good, bad = "#2E9E4F", "#D8504A"
                a, b = (bad, good) if tg[1] == "higher" else (good, bad)
                tr["colorscale"] = [[0, a], [max(0.001, min(0.999, mid)), "#F7F0C8"], [1, b]]
                tr["zmin"], tr["zmax"] = lo, hi
        elif r.get("kind") == "plotly" and v.get("target", {}).get("better") == "lower":
            r["figure"]["data"][0]["reversescale"] = True
        return {**out, **r}
    if t not in CHART_TYPES:
        return {**out, "kind": "empty", "message": "Unknown visual type"}
    y = w.get("y")
    x = w.get("x") or (y if t == "hist" else None)
    if not y or not x:
        need = "Y axis" if t == "hist" else "X axis and Y axis"
        return {**out, "kind": "empty", "message": f"Drag fields into {need}"}
    split = w.get("split") or None
    legend = w.get("legend") or None
    note = ""
    if t in ("bar", "box", "violin", "line") and ds.fields[x].kind == "cat":
        counts: Dict[str, int] = {}
        for tid in res.ids:
            lab = cat_label(ds.value(x, tid, res.matched.get(tid)))
            counts[lab] = counts.get(lab, 0) + 1
        if len(counts) > MAX_CATEGORIES:
            keep = [k for k, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:MAX_CATEGORIES]]
            note = (f"{len(counts) - MAX_CATEGORIES} rarer {ds.fields[x].title} values not shown - "
                    f"use a slicer or filter to pick the ones you want")
            res = ds.apply(list(filters) + [{"key": x, "values": keep}], ply_scope)
    fig, rows, info = build_figure(ds, res, x, y, legend, split, chart=t, palette=palette)
    lay = fig["layout"]
    lay.update({"autosize": True, "font": {**lay.get("font", {}), "size": 11},
                "margin": {"l": 52, "r": 16 if not info.get("continuous") else 70,
                           "t": 26 if split else 8, "b": 40},
                "legend": {"orientation": "v", "x": 1.01, "y": 1, "xanchor": "left", "font": {"size": 10},
                           "itemwidth": 30}})
    if not rows:
        return {**out, "kind": "empty", "message": "No trial has values for these fields"}
    s = {"x": x, "y": y, "colour": legend or "", "split": split or ""}
    fair = fz.assess_chart(ds, res, rows, info, s, filters)
    tg = _target(v)
    if tg:          # target line (vertical for the histogram, whose X is the value)
        vert = t == "hist"
        lay.setdefault("shapes", []).append({
            "type": "line", "xref": "x" if vert else "paper", "yref": "paper" if vert else "y",
            "x0": tg[0] if vert else 0, "x1": tg[0] if vert else 1, "y0": 0 if vert else tg[0], "y1": 1 if vert else tg[0],
            "line": {"color": "#C62828", "width": 2, "dash": "dash"}})
        lay.setdefault("annotations", []).append({
            "text": f"Target {_kfmt(tg[0])}", "xref": "x" if vert else "paper", "yref": "paper" if vert else "y",
            "x": tg[0] if vert else 1, "y": 1 if vert else tg[0], "xanchor": "right" if not vert else "left",
            "yanchor": "bottom", "showarrow": False, "font": {"size": 10, "color": "#C62828"}})
    if v.get("notes") and t in ("points", "trend"):
        _mark_notes(ds, fig, y)
    return {**out, "kind": "plotly", "figure": fig, "plotted": len(rows), "fair": _fair_dict(fair),
            "clickable": t in ("bar", "box", "violin", "line") and info.get("x_is_cat"),
            "selectable": t in ("points", "trend"), "drill": drill, "note": note}


# ── notes on values (db/cell_notes.py) ───────────────────────────────────
NOTE_COLOUR = "#5E35B1"


def note_index(ds: TrialDataset) -> Dict[str, Any]:
    """{"cell": {(table lower, field lower): {tid: [text]}}, "trial": {tid: [text]}},
    loaded once per dashboard refresh (reset_notes)."""
    idx = getattr(ds, "_note_index", None)
    if idx is not None:
        return idx
    idx = {"cell": {}, "trial": {}}
    try:
        from db import cell_notes
        if cell_notes.available():
            from db.connection import fetch_all
            for n in fetch_all(
                    "SELECT n.TableName, n.FieldName, n.TrialID, n.NoteText, n.CreatedAt, "
                    "TRIM(CONCAT(COALESCE(u.FirstName,''), ' ', COALESCE(u.LastName,''))) AS UserName "
                    "FROM tblNote n LEFT JOIN tblUser u ON u.ID = n.CreatedBy"):
                when = n["CreatedAt"].strftime("%d.%m.%Y") if hasattr(n.get("CreatedAt"), "strftime") else ""
                text = f"{n.get('NoteText') or ''} ({(n.get('UserName') or '').strip()}, {when})"
                tid = int(n["TrialID"])
                table, field = str(n.get("TableName") or "").lower(), str(n.get("FieldName") or "").lower()
                if table == "tbltrial" and not field:
                    idx["trial"].setdefault(tid, []).append(text)
                else:
                    idx["cell"].setdefault((table, field), {}).setdefault(tid, []).append(text)
    except Exception:
        pass
    ds._note_index = idx
    return idx


def reset_notes(ds: TrialDataset) -> None:
    ds._note_index = None


def notes_for(ds: TrialDataset, key: str) -> Dict[int, List[str]]:
    """{trial id: [note texts]} for the cells a field reads (+ notes on the whole trial)."""
    f = ds.fields.get(key)
    idx = note_index(ds)
    out: Dict[int, List[str]] = {tid: list(v) for tid, v in idx["trial"].items()}
    if f is None:
        return out
    fld = str(f.source.get("field") or "").lower()
    for tbl in (f.source.get("main_table"), f.source.get("alt_table")):
        for tid, texts in idx["cell"].get((str(tbl or "").lower(), fld), {}).items():
            out.setdefault(tid, []).extend(texts)
    return out


def _mark_notes(ds: TrialDataset, fig: Dict[str, Any], y: str) -> None:
    import html as _html
    notes = notes_for(ds, y)
    if not notes:
        return
    for tr in fig.get("data") or []:
        ids = tr.get("customdata")
        if not ids or tr.get("type") != "scatter":
            continue
        m = tr.setdefault("marker", {})
        base_c = (m.get("line") or {}).get("color", "#FFFFFF")
        base_w = (m.get("line") or {}).get("width", 1)
        lc, lw, ht = [], [], list(tr.get("hovertext") or [""] * len(ids))
        for i, tid in enumerate(ids):
            ns = notes.get(tid)
            lc.append(NOTE_COLOUR if ns else base_c)
            lw.append(3 if ns else base_w)
            if ns and i < len(ht):
                ht[i] = (ht[i] or "") + "".join(f"<br><span style='color:{NOTE_COLOUR}'><b>Note:</b></span> "
                                                f"{_html.escape(t)}" for t in ns[:3])
        m["line"] = {"color": lc, "width": lw}
        tr["hovertext"] = ht


# ── data behind a visual (Excel) ─────────────────────────────────────────
def visual_table(ds: TrialDataset, v: Dict[str, Any], filters: List[Dict[str, Any]],
                 ply_scope: str = "any") -> Tuple[str, List[str], List[List[Any]]]:
    """(title, header, rows) of the data a visual shows - for Excel."""
    t = v.get("type") or "points"
    w = {k: val for k, val in (v.get("wells") or {}).items() if val and (k in MULTI_WELLS or val in ds.fields)}
    drill_x, drill_extra, drill = drill_state(ds, v)
    if drill:
        w["x"] = drill_x
        filters = list(filters) + drill_extra
    res = _apply(ds, v, filters, ply_scope)
    title = v.get("title") or auto_title(ds, v)
    f = ds.fields
    if t == "column" and w.get("x"):
        r = _column(ds, res, w["x"], w.get("legend"), w.get("value"), v.get("agg") or "count",
                    v.get("stack") or "stacked")
        if r.get("kind") != "plotly":
            return title, [], []
        data = r["figure"]["data"]
        return title, [f[w["x"]].title] + [tr["name"] for tr in data], \
            [[x] + [tr["y"][i] for tr in data] for i, x in enumerate(data[0]["x"])]
    if t == "kpi":
        r = _kpi(ds, res, w.get("value"), v.get("agg") or "avg")
        return title, ["Value", "Unit", "Detail"], [[r.get("raw"), r.get("unit"), r.get("sub")]]
    if t == "slicer" and w.get("field"):
        r = _slicer(ds, res, w["field"], v)
        return title, [f[w["field"]].label, "Trials"], [[o["label"], o["n"]] for o in r.get("options") or []]
    if t == "matrix" and w.get("rows") and w.get("cols"):
        r = _matrix(ds, res, w["rows"], w["cols"], w.get("value"), v.get("agg") or "avg")
        if r.get("kind") != "plotly":
            return title, [], []
        tr = r["figure"]["data"][0]
        return title, [f"{f[w['rows']].title} \\ {f[w['cols']].title}"] + list(tr["x"]), \
            [[row] + list(z) for row, z in zip(tr["y"], tr["z"])]
    if t == "table":
        cols = [k for k in (v.get("wells") or {}).get("columns") or [] if k in f]
        rows = []
        for tid in res.ids:
            tt, m = ds.by_id[tid], res.matched.get(tid)
            rows.append([f"V{tt.nr}", tt.series] + [ds.value(k, tid, m) for k in cols])
        return title, ["Trial", "Series"] + [f[k].label for k in cols], rows
    keys = [k for k in (w.get("x"), w.get("y"), w.get("legend"), w.get("split")) if k]
    keys = [k for k in dict.fromkeys(keys) if k not in ("machine", "jet")]
    rows = []
    for tid in res.ids:
        tt, m = ds.by_id[tid], res.matched.get(tid)
        vals = [ds.value(k, tid, m) for k in keys]
        if w.get("y") and ds.value(w["y"], tid, m) is None:
            continue
        rows.append([f"V{tt.nr}", tt.series, tt.machine, tt.jet] + vals)
    return title, ["Trial", "Series", "Machine", "Jet"] + [f[k].label for k in keys], rows


# ── templates ("New" in dashboard mode) ──────────────────────────────────
def _v(i, t, x, y, w, h, **kw):
    wells = kw.pop("wells", {})
    return {"id": f"v{i}", "type": t, "x": x, "y": y, "w": w, "h": h, "title": "", "agg": kw.pop("agg", "avg"),
            "wells": wells, "filters": [], **kw}


TEMPLATES: Dict[str, Dict[str, Any]] = {
    "jets": {"label": "Jet comparison", "tip": "Intermingling, stability and tenacity per jet",
             "spec": {"pages": [{"id": "p1", "title": "Jet comparison", "filters": [], "visuals": [
                 _v(1, "slicer", 0, 0, 4, 9, wells={"field": "jet"}, style="dropdown"),
                 _v(2, "slicer", 4, 0, 4, 9, wells={"field": "machine"}, style="tiles"),
                 _v(3, "slicer", 8, 0, 4, 6, wells={"field": "air_pressure"}, style="between"),
                 _v(4, "kpi", 0, 9, 3, 6, agg="count"),
                 _v(5, "kpi", 3, 9, 3, 6, wells={"value": "fpm"}),
                 _v(6, "kpi", 6, 9, 3, 6, wells={"value": "stab_06"}),
                 _v(7, "kpi", 9, 9, 3, 6, wells={"value": "tenacity"}),
                 _v(8, "box", 0, 15, 6, 16, wells={"x": "jet", "y": "fpm"}),
                 _v(9, "box", 6, 15, 6, 16, wells={"x": "jet", "y": "stab_06"}),
                 _v(10, "matrix", 0, 31, 12, 16, wells={"rows": "jet", "cols": "air_pressure", "value": "fpm"})]}],
                 "active": "p1"}},
    "yarn": {"label": "Yarn overview", "tip": "Which yarns were tested, how much, with which results",
             "spec": {"pages": [{"id": "p1", "title": "Yarn overview", "filters": [], "visuals": [
                 _v(1, "slicer", 0, 0, 4, 9, wells={"field": "yarn_material"}, style="tiles"),
                 _v(2, "slicer", 4, 0, 4, 6, wells={"field": "yarn_endtiter"}, style="between"),
                 _v(3, "slicer", 8, 0, 4, 6, wells={"field": "yarn_filaments"}, style="between"),
                 _v(4, "kpi", 0, 9, 4, 6, agg="count"),
                 _v(5, "kpi", 4, 9, 4, 6, wells={"value": "tenacity"}),
                 _v(6, "kpi", 8, 9, 4, 6, wells={"value": "elongation"}),
                 _v(7, "hist", 0, 15, 6, 16, wells={"y": "yarn_endtiter", "legend": "yarn_material"}),
                 _v(8, "points", 6, 15, 6, 16, wells={"x": "yarn_endtiter", "y": "tenacity",
                                                      "legend": "yarn_material"}),
                 _v(9, "table", 0, 31, 12, 14, wells={"columns": ["yarn_name", "machine", "jet", "tenacity",
                                                                   "elongation"]})]}], "active": "p1"}},
    "machines": {"label": "Machine check", "tip": "How the machines compare - with fairness check",
                 "spec": {"pages": [{"id": "p1", "title": "Machine check", "filters": [], "visuals": [
                     _v(1, "slicer", 0, 0, 6, 9, wells={"field": "machine"}, style="tiles"),
                     _v(2, "kpi", 6, 0, 3, 6, agg="count"),
                     _v(3, "kpi", 9, 0, 3, 6, wells={"value": "fpm"}),
                     _v(4, "violin", 0, 9, 6, 16, wells={"x": "machine", "y": "tenacity"}),
                     _v(5, "trend", 6, 9, 6, 16, wells={"x": "air_pressure", "y": "fpm", "legend": "machine"}),
                     _v(6, "matrix", 0, 25, 12, 14, wells={"rows": "machine", "cols": "year", "value": "fpm"},
                        agg="count")]}], "active": "p1"}},
    "stats": {"label": "Lab statistics", "tip": "How many experiments, series and trials - per month, product "
                                                "group, owner and lab machine (like the Statistics page)",
              "spec": {"pages": [{"id": "p1", "title": "Lab statistics", "filters": [], "visuals": [
                  _v(1, "slicer", 0, 0, 4, 9, wells={"field": "exp_productgroup"}, style="dropdown"),
                  _v(2, "slicer", 4, 0, 4, 9, wells={"field": "exp_ordertype"}, style="dropdown"),
                  _v(3, "slicer", 8, 0, 4, 9, wells={"field": "exp_year"}, style="tiles"),
                  _v(4, "kpi", 0, 9, 4, 6, agg="count_experiments"),
                  _v(5, "kpi", 4, 9, 4, 6, agg="count_series"),
                  _v(6, "kpi", 8, 9, 4, 6, agg="count"),
                  _v(7, "column", 0, 15, 12, 16, wells={"x": "exp_month", "legend": "exp_ordertype"},
                     agg="count_experiments"),
                  _v(8, "column", 0, 31, 6, 16, wells={"x": "exp_productgroup"}, agg="count_experiments"),
                  _v(9, "column", 6, 31, 6, 16, wells={"x": "owner"}, agg="count_series"),
                  _v(10, "column", 0, 47, 6, 16, wells={"x": "tested_on"}, agg="count"),
                  _v(11, "matrix", 6, 47, 6, 16, wells={"rows": "machine", "cols": "year"},
                     agg="count_series")]}], "active": "p1"}},
    "lab": {"label": "Lab overview", "tip": "Distribution of the main lab results",
            "spec": {"pages": [{"id": "p1", "title": "Lab overview", "filters": [], "visuals": [
                _v(1, "slicer", 0, 0, 4, 9, wells={"field": "machine"}, style="dropdown"),
                _v(2, "slicer", 4, 0, 4, 9, wells={"field": "year"}, style="tiles"),
                _v(3, "kpi", 8, 0, 4, 6, agg="count"),
                _v(4, "hist", 0, 9, 4, 14, wells={"y": "tenacity"}),
                _v(5, "hist", 4, 9, 4, 14, wells={"y": "elongation"}),
                _v(6, "hist", 8, 9, 4, 14, wells={"y": "fpm"}),
                _v(7, "density", 0, 23, 6, 16, wells={"x": "tenacity", "y": "elongation"}),
                _v(8, "box", 6, 23, 6, 16, wells={"x": "machine", "y": "titer"})]}], "active": "p1"}},
}


def template_spec(name: str) -> Optional[Dict[str, Any]]:
    import copy as _copy
    t = TEMPLATES.get(name)
    return normalize_spec(_copy.deepcopy(t["spec"])) if t else None


def _kpi(ds, res, key, agg) -> Dict[str, Any]:
    if agg in COUNT_AGGS or not key:
        agg = agg if agg in COUNT_AGGS else "count"
        n = count_of(ds, res.ids, agg)
        return {"kind": "kpi", "value": f"{n:,}".replace(",", "'"), "unit": ENTITY[agg][1], "sub": "",
                "raw": float(n)}
    f = ds.fields[key]
    vals = [_num(ds.value(key, tid, res.matched.get(tid))) for tid in res.ids]
    vals = [x for x in vals if x is not None]
    val = aggregate(vals, agg)
    if val is None:
        return {"kind": "kpi", "value": "–", "unit": f.unit, "sub": "no values"}
    raw = val
    sd = aggregate(vals, "sd")
    sub = f"n = {len(vals):,}".replace(",", "'") + (f" · ± {_kfmt(sd)} SD" if agg == "avg" and sd else "")
    if agg in ("max", "min"):
        best = (max if agg == "max" else min)(
            (tid for tid in res.ids if _num(ds.value(key, tid, res.matched.get(tid))) is not None),
            key=lambda tid: _num(ds.value(key, tid, res.matched.get(tid))))
        t = ds.by_id[best]
        sub = f"V{t.nr} · {t.series}"
    return {"kind": "kpi", "value": _kfmt(val), "unit": f.unit, "sub": sub, "raw": raw}


def _table(ds, res, cols) -> Dict[str, Any]:
    head = ["Trial", "Series"] + [ds.fields[k].label for k in cols]
    rows = []
    for tid in res.ids[:TABLE_LIMIT]:
        t = ds.by_id[tid]
        m = res.matched.get(tid)
        cells = []
        for k in cols:
            val = ds.value(k, tid, m)
            cells.append(_fmt(val) if _num(val) is not None else ("" if val is None else str(val)))
        rows.append([tid, f"V{t.nr}", t.series] + cells)
    return {"kind": "table", "head": head, "rows": rows, "more": max(0, res.count - TABLE_LIMIT)}


def _matrix(ds, res, rk, ck, vk, agg) -> Dict[str, Any]:
    cells: Dict[Tuple[str, str], List[int]] = {}
    rc: Dict[str, int] = {}
    cc: Dict[str, int] = {}
    for tid in _counted(ds, res.ids, agg):
        m = res.matched.get(tid)
        if agg not in COUNT_AGGS and (not vk or _num(ds.value(vk, tid, m)) is None):
            continue
        for r in _labels(ds, rk, tid, m):
            for c in _labels(ds, ck, tid, m):
                cells.setdefault((r, c), []).append(tid)
                rc[r] = rc.get(r, 0) + 1
                cc[c] = cc.get(c, 0) + 1
    if not cells:
        return {"kind": "empty", "message": "No trial has values for these fields"}
    top_r = [k for k, _ in sorted(rc.items(), key=lambda kv: -kv[1])][:MAX_ROWS]
    top_c = [k for k, _ in sorted(cc.items(), key=lambda kv: -kv[1])][:MAX_COLS]
    rows = sorted(top_r, key=_sort_key)
    cols = sorted(top_c, key=_sort_key)
    z, text, hover = [], [], []
    for r in rows:
        zr, tr, hr = [], [], []
        for c in cols:
            tids = cells.get((r, c))
            a = _cell(ds, tids, res, vk, agg) if tids else None
            zr.append(a)
            tr.append(_kfmt(a) if a is not None else "–")
            n = count_of(ds, tids, "count") if tids else 0
            hr.append(f"{r} · {c}<br>{AGGS[agg]}: {_kfmt(a)}" + (f"<br>n = {n} trials" if agg not in COUNT_AGGS else "")
                      if tids else f"{r} · {c}<br>nothing")
        z.append(zr)
        text.append(tr)
        hover.append(hr)
    fr, fc = ds.fields[rk], ds.fields[ck]
    fig = {"data": [{"type": "heatmap", "x": cols, "y": rows, "z": z, "text": text, "texttemplate": "%{text}",
                     "hovertext": hover, "hoverinfo": "text", "colorscale": "RdYlGn", "xgap": 2, "ygap": 2,
                     "showscale": False, "hoverongaps": True}],
           "layout": {"autosize": True, "margin": {"l": 90, "r": 10, "t": 8, "b": 44},
                      "font": {"family": "Segoe UI, Inter, sans-serif", "size": 11, "color": "#1C2321"},
                      "plot_bgcolor": "#EEF1ED", "paper_bgcolor": "#FFFFFF",
                      "xaxis": {"type": "category", "title": {"text": fc.label}, "side": "bottom"},
                      "yaxis": {"type": "category", "title": {"text": fr.label}, "autorange": "reversed"}}}
    hidden = max(0, len(rc) - MAX_ROWS) + max(0, len(cc) - MAX_COLS)
    return {"kind": "plotly", "figure": fig, "clickable": True,
            "note": f"{hidden} rarer values not shown" if hidden else ""}


# ── columns (Statistics) ─────────────────────────────────────────────────
def _column(ds, res, xk, lk, vk, agg, stack="stacked", palette="trippleT") -> Dict[str, Any]:
    """Counts or totals per X category, one coloured part per Legend value."""
    cells: Dict[Tuple[str, str], List[int]] = {}
    xt: Dict[str, List[int]] = {}
    lt: Dict[str, List[int]] = {}
    for tid in _counted(ds, res.ids, agg):
        m = res.matched.get(tid)
        if agg not in COUNT_AGGS and (not vk or _num(ds.value(vk, tid, m)) is None):
            continue
        for x in _labels(ds, xk, tid, m):
            xt.setdefault(x, []).append(tid)
            for lab in (_labels(ds, lk, tid, m) if lk else [""]):
                cells.setdefault((x, lab), []).append(tid)
                lt.setdefault(lab, []).append(tid)
    if not cells:
        return {"kind": "empty", "message": "Nothing to count for these fields" if agg in COUNT_AGGS else
                "No trial has values for these fields"}
    size = lambda tids: count_of(ds, tids, agg if agg in COUNT_AGGS else "count")
    note = ""
    if xk in TIME_KEYS:
        xs = _time_axis(list(xt), xk)
    elif ds.fields[xk].kind == "num":
        xs = sorted(xt, key=_sort_key)
    else:
        xs = sorted(xt, key=lambda k: (k == NONE_LABEL, -size(xt[k]), k.lower()))
        if len(xs) > MAX_CATEGORIES:
            note = f"{len(xs) - MAX_CATEGORIES} smaller {ds.fields[xk].title} values not shown"
            xs = xs[:MAX_CATEGORIES]
    legends = [""]
    if lk:
        if lk in TIME_KEYS:
            legends = _time_axis(list(lt), lk)
            legends = [lab for lab in legends if lab in lt]
        else:
            legends = sorted(lt, key=lambda k: (k == NONE_LABEL, -size(lt[k]), k.lower()))
        if len(legends) > MAX_LEGEND:      # the rest as "Other"
            keep = legends[:MAX_LEGEND - 1]
            for (x, lab), tids in list(cells.items()):
                if lab not in keep:
                    cells.setdefault((x, "Other"), []).extend(tids)
            legends = keep + ["Other"]
    vals = {(x, lab): _cell(ds, list(dict.fromkeys(cells[(x, lab)])), res, vk, agg)
            for x in xs for lab in legends if (x, lab) in cells}
    totals = {x: sum(vals.get((x, lab)) or 0 for lab in legends) for x in xs}
    colours = PALETTES.get(palette, PALETTES["trippleT"])["colours"]
    what = ENTITY[agg][0] if agg in COUNT_AGGS else f"{AGGS.get(agg, '')} {ds.fields[vk].label}".strip()
    fx = ds.fields[xk]
    traces = []
    for i, lab in enumerate(legends):
        ys, hover = [], []
        for x in xs:
            a = vals.get((x, lab))
            if stack == "percent":
                a = (100.0 * a / totals[x]) if a is not None and totals[x] else None
            if a is None and agg in COUNT_AGGS:
                a = 0.0
            ys.append(a)
            shown = f"{_kfmt(a)} %" if stack == "percent" and a is not None else _kfmt(a) if a is not None else "–"
            hover.append(f"{x}" + (f" · {lab}" if lk else "") + f"<br>{what}: {shown}")
        tr = {"type": "bar", "x": xs, "y": ys, "name": lab or what, "hovertext": hover, "hoverinfo": "text",
              "marker": {"color": "#B9BEC4" if lab == "Other" else colours[i % len(colours)]},
              "showlegend": bool(lk)}
        if len(xs) * len(legends) <= 40:
            tr["text"] = [("" if a is None or (agg in COUNT_AGGS and a == 0) else
                           f"{_kfmt(a)} %" if stack == "percent" else _kfmt(a)) for a in ys]
            tr["textposition"] = "inside" if lk and stack != "grouped" else "outside"
            tr["cliponaxis"] = False
        traces.append(tr)
    fig = {"data": traces,
           "layout": {"autosize": True, "barmode": "group" if stack == "grouped" else "stack", "bargap": 0.2,
                      "margin": {"l": 52, "r": 16, "t": 14, "b": 44},
                      "font": {"family": "Segoe UI, Inter, sans-serif", "size": 11, "color": "#1C2321"},
                      "plot_bgcolor": "#FFFFFF", "paper_bgcolor": "#FFFFFF",
                      "xaxis": {"type": "category", "title": {"text": fx.label}, "categoryorder": "array",
                                "categoryarray": xs},
                      "yaxis": {"title": {"text": "Share (%)" if stack == "percent" else what},
                                "gridcolor": "#E3E7E2", "rangemode": "tozero"},
                      "legend": {"orientation": "v", "x": 1.01, "y": 1, "xanchor": "left", "font": {"size": 10},
                                 "traceorder": "normal"}}}
    return {"kind": "plotly", "figure": fig, "clickable": True, "note": note}


# ── slicer ───────────────────────────────────────────────────────────────
def slicer_style(ds: TrialDataset, v: Dict[str, Any]) -> str:
    key = (v.get("wells") or {}).get("field")
    f = ds.fields.get(key) if key else None
    style = v.get("style") or ("between" if f is not None and f.kind == "num" else "list")
    if style == "between" and (f is None or f.kind != "num"):
        style = "list"
    return style if style in SLICER_STYLES else "list"


def _slicer(ds, res, key, v) -> Dict[str, Any]:
    """Options of a slicer: the values the OTHER filters leave, with counts
    (the caller passes filters without this slicer's own selection)."""
    f = ds.fields[key]
    style = slicer_style(ds, v)
    out: Dict[str, Any] = {"kind": "slicer", "style": style, "fkind": f.kind, "unit": f.unit,
                           "multi": v.get("multi", True) is not False, "sel": v.get("sel") or {}}
    vals = [ds.value(key, tid, res.matched.get(tid)) for tid in res.ids]
    if f.kind == "num":
        nums = sorted(x for x in (_num(a) for a in vals) if x is not None)
        if nums:
            lo, hi = nums[0], nums[-1]
            span = hi - lo
            step = 10 ** math.floor(math.log10(span / 100)) if span > 0 else 1
            out["range"] = {"min": lo, "max": hi, "step": step}
        if style != "between":
            counts: Dict[float, int] = {}
            for x in nums:
                counts[round(x, 6)] = counts.get(round(x, 6), 0) + 1
            opts = sorted(counts.items())
            out["options"] = [{"label": _fmt(x), "n": n} for x, n in opts[:SLICER_MAX_OPTIONS]]
            out["more"] = max(0, len(opts) - SLICER_MAX_OPTIONS)
    else:
        from db.trial_explorer import category_counts
        opts = category_counts(vals)
        out["options"] = [{"label": lab, "n": n} for lab, n in opts[:SLICER_MAX_OPTIONS]]
        out["more"] = max(0, len(opts) - SLICER_MAX_OPTIONS)
    return out


def slicer_filter(ds: TrialDataset, v: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The filter a slicer's selection puts on the other visuals (None = nothing chosen)."""
    if v.get("type") != "slicer":
        return None
    key = (v.get("wells") or {}).get("field")
    f = ds.fields.get(key) if key else None
    sel = v.get("sel") or {}
    if f is None or not sel:
        return None
    if sel.get("values"):
        if f.kind == "num":
            nums = [x for x in (_num(a) for a in sel["values"]) if x is not None]
            return {"key": key, "only": nums} if nums else None
        return {"key": key, "values": [str(a) for a in sel["values"]]}
    if f.kind == "num" and (sel.get("min") is not None or sel.get("max") is not None):
        return {"key": key, "min": _num(sel.get("min")), "max": _num(sel.get("max"))}
    return None


# ── cross-filtering ──────────────────────────────────────────────────────
def _filter_for(ds: TrialDataset, key: str, label: Any) -> Optional[Dict[str, Any]]:
    f = ds.fields.get(key)
    if f is None:
        return None
    if f.kind == "cat":
        return {"key": key, "values": [cat_label(label)]}
    x = _num(label)
    if x is None:
        return None
    tol = 0.0005 if abs(x) < 1000 else 0.5     # labels are rounded by _fmt
    return {"key": key, "min": x - tol, "max": x + tol}


def click_filters(ds: TrialDataset, v: Dict[str, Any], click: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Filters for the other visuals after a click on visual v.
    click: {"x": …, "y": …} as reported by Plotly."""
    w = v.get("wells") or {}
    out: List[Dict[str, Any]] = []
    if v.get("type") == "matrix":
        for key, val in ((w.get("rows"), click.get("y")), (w.get("cols"), click.get("x"))):
            f = _filter_for(ds, key, val) if key else None
            if f:
                out.append(f)
    elif v.get("type") == "column" and w.get("x"):
        f = _filter_for(ds, w["x"], click.get("x"))
        if f:
            out.append(f)
        name = click.get("n")
        if w.get("legend") and name and name != "Other":
            f = _filter_for(ds, w["legend"], name)
            if f:
                out.append(f)
    elif v.get("type") in ("bar", "box", "violin", "line") and w.get("x"):
        x_key, extra, _info = drill_state(ds, v)
        out += extra
        f = _filter_for(ds, x_key, click.get("x"))
        if f:
            out.append(f)
    return out


def describe_cross(ds: TrialDataset, flts: List[Dict[str, Any]]) -> str:
    parts = []
    for f in flts:
        if f.get("ids") is not None:
            from db.trial_explorer import describe_selection
            parts.append(describe_selection(f))
            continue
        fld = ds.fields.get(f["key"])
        if fld is None:
            continue
        if f.get("values"):
            parts.append(f"{fld.title}: {', '.join(f['values'])}")
        else:
            parts.append(f"{fld.title}: {_fmt((f['min'] + f['max']) / 2)}{(' ' + fld.unit) if fld.unit else ''}")
    return " · ".join(parts)
