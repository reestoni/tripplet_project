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
from ui.smart_chart_figure import CHART_TYPES, DEFAULT_PALETTE, PALETTES, build_figure, _fmt, _sort_key

_kfmt = fz._fmt   # readable rounding for cards: 114 · 3.84 · 84.6

WELLS: Dict[str, Tuple[str, str]] = {      # key -> (label, accepted kinds)
    "x": ("X axis", "any"), "y": ("Y axis", "num"), "legend": ("Legend (colour)", "any"),
    "split": ("Small multiples", "any"), "rows": ("Rows", "any"), "cols": ("Columns", "any"),
    "value": ("Value", "num"), "columns": ("Columns", "any"), "field": ("Field", "any"),
    "drill": ("Drill down to (double-click a bar)", "any"),
    "values": ("Values (several number fields)", "num"),
    "lines": ("Line (right axis)", "num"),
}
MULTI_WELLS = ("columns", "drill", "values", "lines")
LINE_COLOURS = ("#C62828", "#6A1B9A", "#00838F", "#2E7D32")
DRILL_TYPES = ("bar", "box", "violin", "line")
# Slicer ("Datenschnitt", Nutzerwunsch 2026-10-30): how it looks
SLICER_STYLES = {"list": "List", "dropdown": "Dropdown", "tiles": "Tiles", "between": "Between (range)",
                 "hierarchy": "Year › Month"}
# "Year › Month" (Nutzerwunsch 2026-10-30): years fold open, below them the months 1-12. Works on a year
# or a month field and always filters the MONTH field of the same family.
MONTH_OF = {"year": "month", "month": "month", "trial_year": "trial_month", "trial_month": "trial_month",
            "exp_year": "exp_month", "exp_month": "exp_month"}
MONTH_NAMES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
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
    "stack": {"label": "Stacked fields", "tip": "Several number fields in one column, each a colour - e.g. A, B "
                                                "and C knots per trial, as share (100 %) or as values",
              "wells": ["x", "values", "lines"], "agg": True, "defagg": "avg", "nocount": True},
    "pie": {"label": "Pie / donut", "tip": "Share of each value - count or total, as a pie or a donut",
            "wells": ["legend", "value"], "agg": True, "defagg": "count"},
    "control": {"label": "Control chart", "tip": "Values in order (time, trial …) with the mean and ±3σ limits - "
                                                 "points outside are red, long runs on one side amber",
                "wells": ["x", "y"]},
    "radar": {"label": "Radar", "tip": "Compare jets, yarns, machines … over several number fields at once",
              "wells": ["legend", "values"], "agg": True, "defagg": "avg", "nocount": True},
    "matrix": {"label": "Matrix", "tip": "Table of a value per row and column, coloured - gaps show missing trials",
               "wells": ["rows", "cols", "value"], "agg": True, "target": True},
    "kpi": {"label": "Card", "tip": "One number: count, average, best …", "wells": ["value"], "agg": True,
            "target": True},
    "table": {"label": "Table", "tip": "The trials with the fields you choose", "wells": ["columns"]},
    "slicer": {"label": "Slicer", "tip": "Pick values to filter all other visuals: list, dropdown, tiles or a range",
               "wells": ["field"]},
    "text": {"label": "Text", "tip": "A heading or a comment on the page - also in the PDF", "wells": []},
}
PIE_SHAPES = {"pie": "Pie", "donut": "Donut"}
MAX_CONTROL_POINTS = 2000
RUN_LENGTH = 7            # control chart: this many points in a row on one side of the mean = amber
AGGS = {"avg": "Average", "median": "Median", "min": "Min", "max": "Max", "sd": "Std. deviation",
        "sum": "Sum", "count": "Count of trials", "count_series": "Count of trial series",
        "count_experiments": "Count of experiments"}
# counting aggregations need no Value; series/experiments include the empty rows
COUNT_AGGS = ("count", "count_series", "count_experiments")
ENTITY = {"count": ("Trials", "trials"), "count_series": ("Trial series", "trial series"),
          "count_experiments": ("Experiments", "experiments")}
STACK_MODES = {"stacked": "Stacked", "grouped": "Side by side", "percent": "100 % stacked"}
MAX_LEGEND = 8
MAX_TRIAL_COLUMNS = 150     # "Stacked fields" with X = Trial (a whole series)
MAX_TIME_POINTS = 240
MAX_ROWS, MAX_COLS = 20, 15
MAX_CATEGORIES = 25          # bars / boxes per chart; rarer values are left out (with a note)
TABLE_LIMIT = 500


GRID_COLS, GRID_ROW = 12, 20

# Format tab (Etappe 1+2, Nutzerwunsch 2026-11-02): v["fmt"] holds only what differs from the default:
#   sort (SORTS), top (int), decimals (0-4), labels (True/False; missing = automatic),
#   xtitle / ytitle ("" = hidden), ymin / ymax, legend (LEGEND_POS),
#   palette (PALETTES), colours {value: "#hex"}, colour ("#hex", no legend), scale (MATRIX_SCALES),
#   font (FONT_SIZES), grid (False = no grid lines),
#   vsize (CARD_SIZES), unit / sub (False = hidden) for cards,
#   tsort {"key", "dir"} and rules [{"key", "op", "a", "b", "colour"}] for tables,
#   shapes (True = a shape per colour), psize (POINT_SIZES), xlog / ylog (True = logarithmic axis)
SORTS = {"auto": "Automatic", "value_desc": "Value: high to low", "value_asc": "Value: low to high",
         "name_asc": "Name: A to Z", "name_desc": "Name: Z to A"}
LEGEND_POS = {"auto": "Automatic", "right": "Right", "top": "Top", "bottom": "Bottom", "off": "Off"}
FONT_SIZES = {"small": ("Small", 9), "large": ("Large", 13), "xlarge": ("Extra large", 15)}   # normal = 11
POINT_SIZES = {"small": ("Small", 5), "large": ("Large", 11), "xlarge": ("Extra large", 14)}  # normal = 8
CARD_SIZES = {"s": ("Small", 20), "l": ("Large", 40), "xl": ("Extra large", 52)}             # medium = 30
MATRIX_SCALES = {"RdYlGn": "Red - yellow - green", "Greens": "Greens", "Blues": "Blues", "Viridis": "Viridis",
                 "Greys": "Greys"}
RULE_OPS = {">": "greater than", "<": "less than", "between": "between", "=": "is"}
RULE_COLOURS = {"green": "#D7F0DC", "red": "#F8D7D5", "amber": "#FCEBC5", "blue": "#DCE8F7"}
_SORTABLE = ("bar", "box", "violin", "line", "column", "stack", "pie")
_LABELLED = ("bar", "line", "column", "stack", "matrix", "pie")
_CHARTS = tuple(CHART_TYPES) + ("column", "stack", "matrix", "pie", "control", "radar")
_NO_AXES = ("pie", "radar")
FORMAT_SECTIONS: Dict[str, List[str]] = {
    t: [sec for sec, types in (
        ("sort", _SORTABLE),
        ("numbers", ("bar", "box", "violin", "line", "points", "trend", "column", "stack", "matrix", "kpi", "table",
                     "pie", "control", "radar")),
        ("labels", _LABELLED),
        ("errbars", ("bar", "line")),
        ("colours", _CHARTS),
        ("markers", ("points", "trend", "line")),
        ("text", _CHARTS + ("table", "text")),
        ("axes", tuple(k for k in _CHARTS if k not in _NO_AXES)),
        ("yrange", tuple(k for k in _CHARTS if k not in ("matrix", "density") + _NO_AXES)),
        ("logx", ("points", "trend", "line", "density")),
        ("logy", tuple(k for k in CHART_TYPES if k != "hist") + ("control",)),
        ("legend", tuple(k for k in CHART_TYPES if k != "density") + ("column", "stack", "pie", "radar")),
        ("card", ("kpi",)),
        ("table", ("table",)),
    ) if t in types]
    for t in VISUAL_TYPES}
_LEGEND_LAYOUT = {
    "right": {"orientation": "v", "x": 1.01, "y": 1, "xanchor": "left", "yanchor": "auto"},
    "top": {"orientation": "h", "x": 0, "y": 1.02, "xanchor": "left", "yanchor": "bottom"},
    "bottom": {"orientation": "h", "x": 0, "y": -0.22, "xanchor": "left", "yanchor": "top"},
}


# Dashboard theme (Etappe 3): spec["theme"] sets these for every visual where they fit; a visual's own
# Format wins. key -> the Format section a visual type must have for it.
THEME_KEYS = {"palette": "colours", "font": "text", "grid": "text", "decimals": "numbers", "labels": "labels",
              "legend": "legend"}


def themed(spec: Optional[Dict[str, Any]], v: Dict[str, Any]) -> Dict[str, Any]:
    """The visual with the dashboard theme under its own Format (a copy if anything changes)."""
    theme = (spec or {}).get("theme") or {}
    if not theme:
        return v
    t = v.get("type") or "points"
    secs = FORMAT_SECTIONS.get(t, [])
    base = {k: val for k, val in theme.items()
            if THEME_KEYS.get(k) in secs and not (k == "palette" and t == "matrix")
            and not (k == "grid" and t in ("table", "matrix"))}
    if not base:
        return v
    return {**v, "fmt": {**base, **fmt_of(v)}}


def fmt_of(v: Dict[str, Any]) -> Dict[str, Any]:
    f = v.get("fmt")
    return f if isinstance(f, dict) else {}


def number_format(fmt: Dict[str, Any]):
    """x -> text: fixed decimals if set, else the readable rounding of the cards."""
    d = fmt.get("decimals")
    if isinstance(d, (int, float)) and not isinstance(d, bool) and 0 <= d <= 6:
        return lambda x: f"{x:.{int(d)}f}"
    return _kfmt


def order_categories(cats: Sequence[str], value_of, fmt: Dict[str, Any]) -> Tuple[List[str], int]:
    """(categories in the chosen order, how many Top N left out). value_of(cat) -> number or None.
    Top N keeps the highest values (the lowest when sorted low to high)."""
    sort = fmt.get("sort") or "auto"
    out = list(cats)
    num = value_of
    if sort in ("value_desc", "value_asc"):
        has = [c for c in out if num(c) is not None]
        out = sorted(has, key=num, reverse=sort == "value_desc") + [c for c in out if num(c) is None]
    elif sort in ("name_asc", "name_desc"):
        out = sorted(out, key=_sort_key, reverse=sort == "name_desc")
    top = fmt.get("top")
    if isinstance(top, (int, float)) and not isinstance(top, bool) and 0 < top < len(out):
        ranked = sorted([c for c in out if num(c) is not None], key=num, reverse=sort != "value_asc")
        keep = set(ranked[:int(top)])
        hidden = len(out) - len(keep)
        return [c for c in out if c in keep], hidden
    return out, 0


def _palette(fmt: Dict[str, Any], default: str) -> str:
    if fmt.get("palette") in PALETTES:
        return fmt["palette"]
    return default if default in PALETTES else DEFAULT_PALETTE


def _hex(c: Any) -> Optional[str]:
    c = str(c or "")
    return c if len(c) == 7 and c.startswith("#") else None


def _font_px(fmt: Dict[str, Any]) -> Optional[int]:
    f = FONT_SIZES.get(fmt.get("font") or "")
    return f[1] if f else None


def _top_note(hidden: int, total: int) -> str:
    return f"Top {total - hidden} of {total} shown" if hidden else ""
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
    out = {"pages": pages, "active": active, "calc": calc}
    theme = {k: val for k, val in (spec.get("theme") or {}).items() if k in THEME_KEYS} \
        if isinstance(spec.get("theme"), dict) else {}
    if theme:
        out["theme"] = theme
    return out


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
    empty = agg in ("count_series", "count_experiments") and v.get("type") in ("kpi", "matrix", "column", "pie")
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
    if t == "stack":
        keys = [f[k].title for k in (v.get("wells") or {}).get("values") or [] if k in f]
        what = ", ".join(keys[:4]) + (" …" if len(keys) > 4 else "") or "Stacked fields"
        share = "Share of " if (v.get("stack") or "percent") == "percent" else ""
        lines = [f[k].title for k in (v.get("wells") or {}).get("lines") or [] if k in f]
        return (f"{share}{what}" + (f" per {title('x')}" if title("x") else "")
                + (f" with {', '.join(lines[:2])}" if lines else ""))
    if t == "column":
        agg = v.get("agg") or "count"
        what = ENTITY[agg][0] if agg in COUNT_AGGS else f"{AGGS.get(agg, '')} {title('value')}".strip()
        return (f"{what} per {title('x')}" if title("x") else what) + (f" by {title('legend')}" if title("legend") else "")
    if t == "pie":
        agg = v.get("agg") or "count"
        what = ENTITY[agg][0] if agg in COUNT_AGGS else f"{AGGS.get(agg, '')} {title('value')}".strip()
        return f"{what} by {title('legend')}" if title("legend") else what
    if t == "control":
        return f"Control chart: {title('y')}" if title("y") else "Control chart"
    if t == "radar":
        return f"Comparison per {title('legend')}" if title("legend") else "Radar"
    if t == "text":
        return ""
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
def fairness_of(ds: TrialDataset, v: Dict[str, Any], filters: List[Dict[str, Any]], ply_scope: str = "any"):
    """The full fairness assessment of a chart visual (db/fairness.Assessment) for the details dialog, or None."""
    return _compute(ds, v, filters, ply_scope, keep_fair=True).get("_assessment")


def compute_visual(ds: TrialDataset, v: Dict[str, Any], filters: List[Dict[str, Any]],
                   ply_scope: str = "any", palette: str = DEFAULT_PALETTE) -> Dict[str, Any]:
    r = _compute(ds, v, filters, ply_scope, palette)
    fmt = fmt_of(v)
    if fmt and r.get("kind") == "plotly":
        format_figure(r["figure"], fmt, v.get("type") or "points")
    return r


def _compute(ds: TrialDataset, v: Dict[str, Any], filters: List[Dict[str, Any]],
             ply_scope: str = "any", palette: str = DEFAULT_PALETTE, keep_fair: bool = False) -> Dict[str, Any]:
    t = v.get("type") or "points"
    fmt = fmt_of(v)
    palette = _palette(fmt, palette)
    w = {k: val for k, val in (v.get("wells") or {}).items() if val and (k in MULTI_WELLS or val in ds.fields)}
    drill_x, drill_extra, drill = drill_state(ds, v)
    if drill:
        w["x"] = drill_x
        filters = list(filters) + drill_extra
    res = _apply(ds, v, filters, ply_scope)
    out: Dict[str, Any] = {"title": v.get("title") or auto_title(ds, v), "n": count_of(ds, res.ids, "count")}
    if t == "kpi":
        r = _kpi(ds, res, w.get("value"), v.get("agg") or "avg", fmt)
        tg = _target(v)
        if tg and r.get("raw") is not None:
            good = r["raw"] >= tg[0] if tg[1] == "higher" else r["raw"] <= tg[0]
            r["status"] = "good" if good else "bad"
            r["sub"] = (r.get("sub") + " · " if r.get("sub") else "") + f"target {_kfmt(tg[0])}"
        return {**out, **r}
    if t == "table":
        return {**out, **_table(ds, res, [k for k in (v.get("wells") or {}).get("columns") or [] if k in ds.fields], fmt)}
    if t == "slicer":
        if not w.get("field"):
            return {**out, "kind": "empty", "message": "Drag a field into Field"}
        return {**out, **_slicer(ds, res, w["field"], v)}
    if t == "column":
        agg = v.get("agg") or "count"
        if not w.get("x") or (not w.get("value") and agg not in COUNT_AGGS):
            return {**out, "kind": "empty", "message": "Drag a field into X axis" if not w.get("x") else
                    "Drag a number into Value - or count trials, series or experiments"}
        r = _column(ds, res, w["x"], w.get("legend"), w.get("value"), agg, v.get("stack") or "stacked", palette, fmt)
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
        if r.get("kind") == "plotly" and v.get("analytics"):
            draw_analytics(r["figure"]["layout"], analytics_marks(v["analytics"], _column_values(r["figure"], v)))
        return {**out, **r}
    if t == "stack":
        keys = [k for k in (v.get("wells") or {}).get("values") or [] if k in ds.fields]
        if not keys:
            return {**out, "kind": "empty", "message": "Drag two or more number fields into Values"}
        agg = v.get("agg") if v.get("agg") in AGGS and v.get("agg") not in COUNT_AGGS else "avg"
        lines = [k for k in (v.get("wells") or {}).get("lines") or [] if k in ds.fields]
        return {**out, **_stack(ds, res, w.get("x"), keys, agg, v.get("stack") or "percent", palette, lines, fmt)}
    if t == "matrix":
        if not (w.get("rows") and w.get("cols")) or (not w.get("value") and v.get("agg") not in COUNT_AGGS):
            return {**out, "kind": "empty", "message": "Drag fields into Rows, Columns and Value"}
        r = _matrix(ds, res, w["rows"], w["cols"], w.get("value"), v.get("agg") or "avg", fmt)
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
    if t == "text":
        r = {"kind": "text", "text": str(v.get("text") or ""), "title": v.get("title") if v.get("title_set") else ""}
        if _font_px(fmt):
            r["font"] = _font_px(fmt)
        return {**out, **r}
    if t == "pie":
        agg = v.get("agg") or "count"
        if not w.get("legend") or (not w.get("value") and agg not in COUNT_AGGS):
            return {**out, "kind": "empty", "message": "Drag a field into Legend" if not w.get("legend") else
                    "Drag a number into Value - or count trials, series or experiments"}
        return {**out, **_pie(ds, res, w["legend"], w.get("value"), agg, palette, fmt, v.get("shape") == "donut")}
    if t == "control":
        if not w.get("y"):
            return {**out, "kind": "empty", "message": "Drag a number into Y axis - X axis (time, trial …) is optional"}
        r = _control(ds, res, w.get("x"), w["y"], palette, fmt)
        if r.get("kind") == "plotly" and v.get("analytics"):
            ys = [_num(ds.value(w["y"], tid, res.matched.get(tid))) for tid in res.ids if not ds.by_id[tid].empty]
            draw_analytics(r["figure"]["layout"], analytics_marks(v["analytics"], ys), log=bool(fmt.get("ylog")))
        return {**out, **r}
    if t == "radar":
        keys = [k for k in (v.get("wells") or {}).get("values") or [] if k in ds.fields]
        if len(keys) < 3:
            return {**out, "kind": "empty", "message": "Drag three or more number fields into Values - "
                                                       "and a field into Legend to compare groups"}
        agg = v.get("agg") if v.get("agg") in AGGS and v.get("agg") not in COUNT_AGGS else "avg"
        return {**out, **_radar(ds, res, w.get("legend"), keys, agg, palette, fmt)}
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
    order = None
    if t in ("bar", "box", "violin", "line") and (fmt.get("sort") not in (None, "auto") or fmt.get("top")) \
            and (ds.fields[x].kind == "cat" or t != "line"):
        res, order, note = _sort_chart(ds, res, x, y, t, fmt)
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
    cmap = {k: c for k, c in (fmt.get("colours") or {}).items() if _hex(c)}
    if _hex(fmt.get("colour")) and not legend:
        cmap[""] = fmt["colour"]
    psize = POINT_SIZES.get(fmt.get("psize") or "")
    fig, rows, info = build_figure(ds, res, x, y, legend, split, chart=t, palette=palette, colour_map=cmap,
                                   shapes=bool(fmt.get("shapes")), logx=bool(fmt.get("xlog")), logy=bool(fmt.get("ylog")),
                                   size=psize[1] if psize else 8,
                                   errbars=fmt.get("errbars") if fmt.get("errbars") in ("ci", "minmax") else "sd")
    lay = fig["layout"]
    if order is not None:
        for k, ax in lay.items():
            if k.startswith("xaxis") and isinstance(ax, dict) and ax.get("type") == "category":
                present = set(ax.get("categoryarray") or [])
                ax["categoryarray"] = [c for c in order if c in present]
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
    _chart_analytics(v, lay, rows, t, split, fmt)
    if v.get("notes") and t in ("points", "trend"):
        _mark_notes(ds, fig, y)
    colours = {"groups": [list(g) for g in info.get("colour_groups") or []],
               "single": None if legend or info.get("continuous") or t == "density"
               else cmap.get("") or PALETTES[palette]["colours"][0]}
    if keep_fair:
        out["_assessment"] = fair
    return {**out, "kind": "plotly", "figure": fig, "plotted": len(rows), "fair": _fair_dict(fair), "colours": colours,
            "clickable": t in ("bar", "box", "violin", "line") and info.get("x_is_cat"),
            "selectable": t in ("points", "trend"), "drill": drill, "note": note}


def _sort_chart(ds: TrialDataset, res: Result, x: str, y: str, t: str, fmt: Dict[str, Any]):
    """(rows, category order, note) for bar/box/violin/line: the value of a category is the
    mean (bar, line) or the median (box, violin) of Y; Top N leaves out the trials of the rest."""
    numeric_x = ds.fields[x].kind == "num"
    by_cat: Dict[str, List[float]] = {}
    tids_of: Dict[str, List[int]] = {}
    for tid in res.ids:
        m = res.matched.get(tid)
        raw = ds.value(x, tid, m)
        if raw in (None, ""):
            continue
        lab = _fmt(raw) if numeric_x else cat_label(raw)
        tids_of.setdefault(lab, []).append(tid)
        yv = _num(ds.value(y, tid, m))
        if yv is not None:
            by_cat.setdefault(lab, []).append(yv)
    agg = "median" if t in ("box", "violin") else "avg"
    value = {c: aggregate(vals, agg) for c, vals in by_cat.items()}
    cats = sorted(tids_of, key=_sort_key)
    order, hidden = order_categories(cats, value.get, fmt)
    if hidden:
        keep = set(order)
        ids = [tid for c in cats if c in keep for tid in tids_of[c]]
        ids = [tid for tid in res.ids if tid in set(ids)]
        res = Result(ids=ids, matched={tid: res.matched.get(tid) for tid in ids})
    return res, order, _top_note(hidden, len(cats))


def format_figure(fig: Dict[str, Any], fmt: Dict[str, Any], t: str) -> None:
    """The Format tab on a finished Plotly figure: decimals, data labels, axis titles, Y range, legend."""
    lay = fig.setdefault("layout", {})
    nf = number_format(fmt)
    has_dec = fmt.get("decimals") is not None
    if has_dec and t not in ("hist", "density", "matrix"):
        for k, ax in lay.items():
            if k.startswith("yaxis") and isinstance(ax, dict):
                ax["tickformat"] = f".{int(fmt['decimals'])}f"
    labels = fmt.get("labels")
    if t in ("bar", "line") and labels:
        for tr in fig.get("data") or []:
            if tr.get("type") == "bar" or (tr.get("type") == "scatter" and tr.get("error_y")):
                tr["text"] = ["" if yv is None else nf(yv) for yv in tr.get("y") or []]
                tr["hoverinfo"] = tr.get("hoverinfo") or "text"
                if tr["type"] == "bar":
                    tr.update({"textposition": "outside", "cliponaxis": False})
                else:
                    tr.update({"mode": (tr.get("mode") or "markers") + "+text", "textposition": "top center"})
    if fmt.get("errbars") == "off" and t in ("bar", "line"):     # after the labels: they look for error_y
        for tr in fig.get("data") or []:
            tr.pop("error_y", None)
    for key, axis in (("xtitle", "xaxis"), ("ytitle", "yaxis")):
        if key in fmt and fmt[key] is not None:
            for k, ax in lay.items():
                if k.startswith(axis) and k != "yaxis2" and isinstance(ax, dict) and ax.get("title"):
                    ax["title"] = {**(ax["title"] if isinstance(ax["title"], dict) else {}), "text": str(fmt[key])}
    lo, hi = _num(fmt.get("ymin")), _num(fmt.get("ymax"))
    if (lo is not None or hi is not None) and t not in ("matrix", "density"):
        ya = lay.setdefault("yaxis", {})
        ya.pop("rangemode", None)
        if lo is not None and hi is not None:
            ya.update({"range": [min(lo, hi), max(lo, hi)], "autorange": False})
        else:
            ya.update({"range": [lo, hi], "autorange": "max" if lo is not None else "min"})
    if fmt.get("ylog") and t == "control":        # the chart types from build_figure set it themselves
        lay.setdefault("yaxis", {})["type"] = "log"
    px = _font_px(fmt)
    if px:
        lay["font"] = {**(lay.get("font") or {}), "size": px}
        if isinstance(lay.get("legend"), dict):
            lay["legend"]["font"] = {**(lay["legend"].get("font") or {}), "size": px - 1}
    if fmt.get("grid") is False:
        for k, ax in lay.items():
            if (k.startswith("xaxis") or k.startswith("yaxis")) and isinstance(ax, dict):
                ax["showgrid"] = False
    pos = fmt.get("legend")
    if pos == "off":
        lay["showlegend"] = False
    elif pos in _LEGEND_LAYOUT:
        lay["legend"] = {**(lay.get("legend") or {}), **_LEGEND_LAYOUT[pos]}


# ── Analytics (Nutzerwunsch 2026-11-02, like the Power BI Analytics pane) ─
# v["analytics"] = [{"kind", "n" (sd: 1-3), "p" (percentile), "value" (constant), "lo"/"hi" (band),
#                    "label", "colour" (ANALYTICS_COLOURS key)}]. Not part of v["fmt"], so the format
# painter does not copy limits that belong to one field. The statistics use the single trials of the
# chart (per small multiple) - for "Columns" the plotted columns.
ANALYTICS_KINDS = {"mean": "Average line", "median": "Median line", "sd": "Mean ± standard deviations",
                   "percentile": "Percentile line", "min": "Min line", "max": "Max line",
                   "constant": "Constant line", "band": "Band (e.g. spec limits)"}
ANALYTICS_COLOURS = {"blue": "#1565C0", "purple": "#6A1B9A", "teal": "#00838F", "orange": "#EF6C00",
                     "red": "#C62828", "green": "#2E9E4F", "grey": "#546E7A"}
ANALYTICS_DEFAULT_COLOUR = {"mean": "blue", "median": "purple", "sd": "teal", "percentile": "orange",
                            "min": "grey", "max": "grey", "constant": "red", "band": "green"}
ANALYTICS_TYPES = ("bar", "box", "violin", "line", "points", "trend", "hist", "column", "control")
MAX_ANALYTICS = 8


def _percentile(xs: Sequence[float], p: float) -> float:
    s = sorted(xs)
    k = (len(s) - 1) * max(0.0, min(100.0, p)) / 100
    lo = int(math.floor(k))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def analytics_marks(items: Any, values: Sequence[Optional[float]]) -> List[Tuple[float, float, str, str]]:
    """[(lo, hi, label, hex)] for the analytics of a visual - lo == hi is a line, else a band."""
    xs = [x for x in values if x is not None]
    out: List[Tuple[float, float, str, str]] = []
    for a in (items if isinstance(items, list) else [])[:MAX_ANALYTICS]:
        k = a.get("kind") if isinstance(a, dict) else None
        if k not in ANALYTICS_KINDS:
            continue
        col = ANALYTICS_COLOURS.get(a.get("colour")) or ANALYTICS_COLOURS[ANALYTICS_DEFAULT_COLOUR[k]]
        name = str(a.get("label") or "").strip()
        named = lambda default, val: f"{name or default} {_kfmt(val)}".strip()
        if k == "constant":
            val = _num(a.get("value"))
            if val is not None:
                out.append((val, val, named("", val), col))
            continue
        if k == "band":
            lo, hi = _num(a.get("lo")), _num(a.get("hi"))
            if lo is not None and hi is not None:
                lo, hi = min(lo, hi), max(lo, hi)
                out.append((lo, hi, f"{name + ' ' if name else ''}{_kfmt(lo)} – {_kfmt(hi)}", col))
            elif lo is not None or hi is not None:
                val = lo if lo is not None else hi
                out.append((val, val, named("", val), col))
            continue
        if not xs:
            continue
        if k == "sd":
            if len(xs) < 2:
                continue
            n = _num(a.get("n")) or 1
            n = n if n in (1, 2, 3) else 1
            mean = sum(xs) / len(xs)
            sd = aggregate(xs, "sd") or 0.0
            tag = name or f"{int(n)} SD"
            out.append((mean + n * sd, mean + n * sd, f"+{tag} {_kfmt(mean + n * sd)}", col))
            out.append((mean - n * sd, mean - n * sd, f"−{tag} {_kfmt(mean - n * sd)}", col))
            continue
        if k == "percentile":
            p = _num(a.get("p"))
            p = 90.0 if p is None else max(0.0, min(100.0, p))
            val = _percentile(xs, p)
            out.append((val, val, named(f"P{_kfmt(p)}", val), col))
            continue
        val = aggregate(xs, {"mean": "avg"}.get(k, k))
        if val is not None:
            out.append((val, val, named({"mean": "Average", "median": "Median", "min": "Min", "max": "Max"}[k], val),
                        col))
    return out


def _rgba(hexc: str, a: float) -> str:
    return f"rgba({int(hexc[1:3], 16)},{int(hexc[3:5], 16)},{int(hexc[5:7], 16)},{a})"


def draw_analytics(lay: Dict[str, Any], marks: List[Tuple[float, float, str, str]], sx: str = "",
                   vertical: bool = False, log: bool = False) -> None:
    """Lines / bands on panel sx ("" = the first) of a figure. vertical = the value is on X (histogram)."""
    shapes, notes = lay.setdefault("shapes", []), lay.setdefault("annotations", [])
    vref, dref = (f"x{sx}", f"y{sx} domain") if vertical else (f"y{sx}", f"x{sx} domain")
    pos = (lambda val: math.log10(val) if val > 0 else None) if log else (lambda val: val)
    for lo, hi, label, col in marks:
        a, b = pos(lo), pos(hi)
        if a is None or b is None:
            continue
        if lo == hi:
            sh = {"type": "line", "line": {"color": col, "width": 1.5, "dash": "dot"}, "layer": "above"}
        else:
            sh = {"type": "rect", "fillcolor": _rgba(col, 0.12), "line": {"width": 0}, "layer": "below"}
        if vertical:
            sh.update({"xref": vref, "yref": dref, "x0": a, "x1": b, "y0": 0, "y1": 1})
            notes.append({"text": label, "xref": vref, "yref": dref, "x": b, "y": 1, "xanchor": "left",
                          "yanchor": "top", "showarrow": False, "font": {"size": 10, "color": col}})
        else:
            sh.update({"xref": dref, "yref": vref, "x0": 0, "x1": 1, "y0": a, "y1": b})
            notes.append({"text": label, "xref": dref, "yref": vref, "x": 0 if lo != hi else 1, "y": b,
                          "xanchor": "left" if lo != hi else "right", "yanchor": "bottom" if lo == hi else "top",
                          "showarrow": False, "font": {"size": 10, "color": col}})
        shapes.append(sh)


def _column_values(fig: Dict[str, Any], v: Dict[str, Any]) -> List[Optional[float]]:
    """The plotted columns: one per X when stacked, else every bar."""
    data = [tr for tr in fig.get("data") or [] if tr.get("type") == "bar"]
    if (v.get("stack") or "stacked") == "grouped":
        return [_num(y) for tr in data for y in tr.get("y") or []]
    tot: Dict[Any, float] = {}
    for tr in data:
        for x, y in zip(tr.get("x") or [], tr.get("y") or []):
            if _num(y) is not None:
                tot[x] = tot.get(x, 0.0) + _num(y)
    return list(tot.values())


def _chart_analytics(v: Dict[str, Any], lay: Dict[str, Any], rows: List[Dict[str, Any]], t: str,
                     split: Optional[str], fmt: Dict[str, Any]) -> None:
    """Analytics of a chart from build_figure: per small multiple, from the trials in it."""
    if t not in ANALYTICS_TYPES or not v.get("analytics"):
        return
    panels = sorted({r["split"] for r in rows}, key=_sort_key) if split else [""]
    for i, pan in enumerate(panels):
        ys = [r["y"] for r in rows if not split or r["split"] == pan]
        draw_analytics(lay, analytics_marks(v["analytics"], ys), "" if i == 0 else str(i + 1),
                       vertical=t == "hist", log=bool(fmt.get("ylog")) and t != "hist")


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


# ── focus mode: the trials of one visual ─────────────────────────────────
FOCUS_LIMIT = 3000
_WELL_ORDER = ("x", "y", "legend", "split", "value", "rows", "cols", "field", "values", "lines", "columns", "drill")


def focus_rows(ds: TrialDataset, v: Dict[str, Any], filters: List[Dict[str, Any]],
               ply_scope: str = "any") -> Dict[str, Any]:
    """The trials a visual is made of (all its filters, clicks and slicers) with the fields of its wells -
    the list under a visual in focus mode. rows: [trial id, trial, series, machine, jet, values …]."""
    t = v.get("type") or "points"
    wells = v.get("wells") or {}
    drill_x, drill_extra, drill = drill_state(ds, v)
    if drill:
        filters = list(filters) + drill_extra
    res = _apply(ds, v, filters, ply_scope)
    keys: List[str] = []
    for well in _WELL_ORDER:
        val = wells.get(well)
        for k in (val if isinstance(val, list) else [val]):
            if k and k in ds.fields and k not in keys and k not in ("machine", "jet", "series", "trial"):
                keys.append(k)
    keys = keys[:8]
    need = wells.get("y") if t in CHART_TYPES or t == "control" else None
    need = need if need in ds.fields else None
    nf = number_format(fmt_of(v)) if fmt_of(v).get("decimals") is not None else _fmt
    rows = []
    for tid in res.ids:
        tr = ds.by_id[tid]
        if tr.empty:
            continue
        m = res.matched.get(tid)
        if need and _num(ds.value(need, tid, m)) is None:
            continue
        cells = []
        for k in keys:
            val = ds.value(k, tid, m)
            cells.append(nf(_num(val)) if _num(val) is not None else ("" if val is None else str(val)))
        rows.append([tid, f"V{tr.nr}", tr.series or "", tr.machine or "", tr.jet or ""] + cells)
    more = max(0, len(rows) - FOCUS_LIMIT)
    return {"head": ["Trial", "Series", "Machine", "Jet"] + [ds.fields[k].label for k in keys],
            "rows": rows[:FOCUS_LIMIT], "more": more}


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
    if t == "stack":
        keys = [k for k in (v.get("wells") or {}).get("values") or [] if k in f]
        r = _stack(ds, res, w.get("x"), keys, v.get("agg") if v.get("agg") not in COUNT_AGGS else "avg",
                   v.get("stack") or "percent",
                   lines=[k for k in (v.get("wells") or {}).get("lines") or [] if k in f], fmt=fmt_of(v)) if keys else {}
        if r.get("kind") != "plotly":
            return title, [], []
        data = r["figure"]["data"]
        return title, [f[w["x"]].title if w.get("x") else ""] + [tr["name"] for tr in data], \
            [[x] + [tr["y"][i] for tr in data] for i, x in enumerate(data[0]["x"])]
    if t == "column" and w.get("x"):
        r = _column(ds, res, w["x"], w.get("legend"), w.get("value"), v.get("agg") or "count",
                    v.get("stack") or "stacked", fmt=fmt_of(v))
        if r.get("kind") != "plotly":
            return title, [], []
        data = r["figure"]["data"]
        return title, [f[w["x"]].title] + [tr["name"] for tr in data], \
            [[x] + [tr["y"][i] for tr in data] for i, x in enumerate(data[0]["x"])]
    if t == "kpi":
        r = _kpi(ds, res, w.get("value"), v.get("agg") or "avg")
        return title, ["Value", "Unit", "Detail"], [[r.get("raw"), r.get("unit"), r.get("sub")]]
    if t in ("pie", "control", "radar"):
        r = _compute(ds, v, filters, ply_scope)
        xl = r.get("xl") or {}
        return title, xl.get("head") or [], xl.get("rows") or []
    if t == "text":
        return title or "Text", ["Text"], [[line] for line in str(v.get("text") or "").splitlines()]
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
        for tid in table_order(ds, res, cols, fmt_of(v)):
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


def _kpi(ds, res, key, agg, fmt: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if agg in COUNT_AGGS or not key:
        agg = agg if agg in COUNT_AGGS else "count"
        n = count_of(ds, res.ids, agg)
        return _card_fmt({"kind": "kpi", "value": f"{n:,}".replace(",", "'"), "unit": ENTITY[agg][1], "sub": "",
                          "raw": float(n)}, fmt)
    f = ds.fields[key]
    vals = [_num(ds.value(key, tid, res.matched.get(tid))) for tid in res.ids]
    vals = [x for x in vals if x is not None]
    val = aggregate(vals, agg)
    if val is None:
        return _card_fmt({"kind": "kpi", "value": "–", "unit": f.unit, "sub": "no values"}, fmt)
    raw = val
    sd = aggregate(vals, "sd")
    sub = f"n = {len(vals):,}".replace(",", "'") + (f" · ± {_kfmt(sd)} SD" if agg == "avg" and sd else "")
    if agg in ("max", "min"):
        best = (max if agg == "max" else min)(
            (tid for tid in res.ids if _num(ds.value(key, tid, res.matched.get(tid))) is not None),
            key=lambda tid: _num(ds.value(key, tid, res.matched.get(tid))))
        t = ds.by_id[best]
        sub = f"V{t.nr} · {t.series}"
    return _card_fmt({"kind": "kpi", "value": number_format(fmt or {})(val), "unit": f.unit, "sub": sub, "raw": raw},
                     fmt)


def _card_fmt(r: Dict[str, Any], fmt: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    fmt = fmt or {}
    if fmt.get("unit") is False:
        r["unit"] = ""
    if fmt.get("sub") is False:
        r["sub"] = ""
    size = CARD_SIZES.get(fmt.get("vsize") or "")
    if size:
        r["vsize"] = size[1]
    return r


def table_order(ds, res, cols, fmt: Optional[Dict[str, Any]] = None) -> List[int]:
    """Trial ids of a table in the order of its sorted column (tsort); empty values last."""
    ts = (fmt or {}).get("tsort") or {}
    key, desc = ts.get("key"), ts.get("dir") == "desc"
    if key not in ("trial", "series") and key not in cols:
        return list(res.ids)

    def value(tid):
        t = ds.by_id[tid]
        if key == "trial":
            return float(t.nr)
        if key == "series":
            return str(t.series or "").lower()
        raw = ds.value(key, tid, res.matched.get(tid))
        x = _num(raw)
        return x if x is not None else (None if raw in (None, "") else str(raw).lower())

    vals = {tid: value(tid) for tid in res.ids}
    filled = [tid for tid in res.ids if vals[tid] is not None]
    nums = [tid for tid in filled if isinstance(vals[tid], float)]
    texts = [tid for tid in filled if not isinstance(vals[tid], float)]
    ordered = sorted(nums, key=vals.get, reverse=desc) + sorted(texts, key=vals.get, reverse=desc)
    return ordered + [tid for tid in res.ids if vals[tid] is None]


def rule_hit(rule: Dict[str, Any], raw: Any) -> bool:
    """Does a colour rule of a table column match this value?"""
    op = rule.get("op")
    if op == "=":
        a = rule.get("a")
        xa, xv = _num(a), _num(raw)
        if xa is not None and xv is not None:
            return xa == xv
        return raw not in (None, "") and str(a or "").strip().lower() in [lab.lower() for lab in cat_labels(raw)]
    x, a, b = _num(raw), _num(rule.get("a")), _num(rule.get("b"))
    if x is None or a is None:
        return False
    if op == ">":
        return x > a
    if op == "<":
        return x < a
    if op == "between":
        return b is not None and min(a, b) <= x <= max(a, b)
    return False


def _table(ds, res, cols, fmt: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    fmt = fmt or {}
    nf = number_format(fmt) if fmt.get("decimals") is not None else _fmt
    rules = [r for r in fmt.get("rules") or [] if isinstance(r, dict) and r.get("key") in cols
             and r.get("colour") in RULE_COLOURS]
    head = ["Trial", "Series"] + [ds.fields[k].label for k in cols]
    rows, cellbg = [], []
    for tid in table_order(ds, res, cols, fmt)[:TABLE_LIMIT]:
        t = ds.by_id[tid]
        m = res.matched.get(tid)
        cells, bg = [], ["", ""]
        for k in cols:
            val = ds.value(k, tid, m)
            cells.append(nf(_num(val)) if _num(val) is not None else ("" if val is None else str(val)))
            hit = next((r for r in rules if r["key"] == k and rule_hit(r, val)), None)
            bg.append(RULE_COLOURS[hit["colour"]] if hit else "")
        rows.append([tid, f"V{t.nr}", t.series] + cells)
        cellbg.append(bg)
    out = {"kind": "table", "head": head, "rows": rows, "more": max(0, res.count - TABLE_LIMIT),
           "keys": ["trial", "series"] + list(cols), "tsort": fmt.get("tsort") or None}
    if rules:
        out["cellbg"] = cellbg
    if _font_px(fmt):
        out["font"] = _font_px(fmt)
    return out


def _matrix(ds, res, rk, ck, vk, agg, fmt: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    fmt = fmt or {}
    nf = number_format(fmt)
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
            tr.append(nf(a) if a is not None else "–")
            n = count_of(ds, tids, "count") if tids else 0
            hr.append(f"{r} · {c}<br>{AGGS[agg]}: {_kfmt(a)}" + (f"<br>n = {n} trials" if agg not in COUNT_AGGS else "")
                      if tids else f"{r} · {c}<br>nothing")
        z.append(zr)
        text.append(tr)
        hover.append(hr)
    fr, fc = ds.fields[rk], ds.fields[ck]
    fig = {"data": [{"type": "heatmap", "x": cols, "y": rows, "z": z, "text": text, "texttemplate": "%{text}",
                     "hovertext": hover, "hoverinfo": "text",
                     "colorscale": fmt.get("scale") if fmt.get("scale") in MATRIX_SCALES else "RdYlGn",
                     "xgap": 2, "ygap": 2,
                     "showscale": False, "hoverongaps": True,
                     **({"texttemplate": ""} if fmt.get("labels") is False else {})}],
           "layout": {"autosize": True, "margin": {"l": 90, "r": 10, "t": 8, "b": 44},
                      "font": {"family": "Segoe UI, Inter, sans-serif", "size": 11, "color": "#1C2321"},
                      "plot_bgcolor": "#EEF1ED", "paper_bgcolor": "#FFFFFF",
                      "xaxis": {"type": "category", "title": {"text": fc.label}, "side": "bottom"},
                      "yaxis": {"type": "category", "title": {"text": fr.label}, "autorange": "reversed"}}}
    hidden = max(0, len(rc) - MAX_ROWS) + max(0, len(cc) - MAX_COLS)
    return {"kind": "plotly", "figure": fig, "clickable": True,
            "note": f"{hidden} rarer values not shown" if hidden else ""}


# ── columns (Statistics) ─────────────────────────────────────────────────
def _column(ds, res, xk, lk, vk, agg, stack="stacked", palette=DEFAULT_PALETTE,
            fmt: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Counts or totals per X category, one coloured part per Legend value."""
    fmt = fmt or {}
    nf = number_format(fmt)
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
    cut = xk not in TIME_KEYS and ds.fields[xk].kind != "num"
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
    if fmt.get("sort") not in (None, "auto") or fmt.get("top"):
        whole = {x: _cell(ds, list(dict.fromkeys(xt[x])), res, vk, agg) if x in xt else None for x in xs}
        n_all = len(xs)
        xs, hidden = order_categories(xs, whole.get, fmt)
        note = _top_note(hidden, n_all)
    if cut and len(xs) > MAX_CATEGORIES:
        note = f"{len(xs) - MAX_CATEGORIES} smaller {ds.fields[xk].title} values not shown"
        xs = xs[:MAX_CATEGORIES]
    vals = {(x, lab): _cell(ds, list(dict.fromkeys(cells[(x, lab)])), res, vk, agg)
            for x in xs for lab in legends if (x, lab) in cells}
    totals = {x: sum(vals.get((x, lab)) or 0 for lab in legends) for x in xs}
    colours = PALETTES.get(palette, PALETTES[DEFAULT_PALETTE])["colours"]
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
            shown = f"{nf(a)} %" if stack == "percent" and a is not None else nf(a) if a is not None else "–"
            hover.append(f"{x}" + (f" · {lab}" if lk else "") + f"<br>{what}: {shown}")
        own = (fmt.get("colours") or {}).get(lab) if lk else fmt.get("colour")
        tr = {"type": "bar", "x": xs, "y": ys, "name": lab or what, "hovertext": hover, "hoverinfo": "text",
              "marker": {"color": _hex(own) or ("#B9BEC4" if lab == "Other" else colours[i % len(colours)])},
              "showlegend": bool(lk)}
        if fmt.get("labels") or (fmt.get("labels") is None and len(xs) * len(legends) <= 40):
            tr["text"] = [("" if a is None or (agg in COUNT_AGGS and a == 0) else
                           f"{nf(a)} %" if stack == "percent" else nf(a)) for a in ys]
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
    groups = [[tr["name"], tr["marker"]["color"]] for tr in traces] if lk else []
    return {"kind": "plotly", "figure": fig, "clickable": True, "note": note,
            "colours": {"groups": groups, "single": None if lk else traces[0]["marker"]["color"]}}


# ── pie / donut ──────────────────────────────────────────────────────────
def _pie(ds, res, lk, vk, agg, palette, fmt, donut=False) -> Dict[str, Any]:
    """Share of each Legend value; more than MAX_LEGEND values -> the smallest together as "Other"."""
    fmt = fmt or {}
    nf = number_format(fmt)
    cells: Dict[str, List[int]] = {}
    for tid in _counted(ds, res.ids, agg):
        m = res.matched.get(tid)
        if agg not in COUNT_AGGS and (not vk or _num(ds.value(vk, tid, m)) is None):
            continue
        for lab in _labels(ds, lk, tid, m):
            cells.setdefault(lab, []).append(tid)
    vals = {lab: _cell(ds, list(dict.fromkeys(tids)), res, vk, agg) for lab, tids in cells.items()}
    vals = {lab: x for lab, x in vals.items() if x is not None and x > 0}
    if not vals:
        return {"kind": "empty", "message": "Nothing to show for these fields"}
    labs = sorted(vals, key=lambda k: (k == NONE_LABEL, -vals[k], k.lower()))
    note = ""
    if fmt.get("sort") not in (None, "auto") or fmt.get("top"):
        n_all = len(labs)
        labs, hidden = order_categories(labs, vals.get, fmt)
        note = _top_note(hidden, n_all)
    if len(labs) > MAX_LEGEND:            # the smallest together
        rest = [lab for lab in labs[MAX_LEGEND - 1:]]
        tids = list(dict.fromkeys(t for lab in rest for t in cells[lab]))
        other = _cell(ds, tids, res, vk, agg)
        labs = labs[:MAX_LEGEND - 1]
        if other:
            vals["Other"] = other
            labs.append("Other")
    colours = PALETTES.get(palette, PALETTES[DEFAULT_PALETTE])["colours"]
    own = fmt.get("colours") or {}
    cols = [_hex(own.get(lab)) or ("#B9BEC4" if lab == "Other" else colours[i % len(colours)])
            for i, lab in enumerate(labs)]
    what = ENTITY[agg][0] if agg in COUNT_AGGS else f"{AGGS.get(agg, '')} {ds.fields[vk].label}".strip()
    d = fmt.get("decimals")
    pct = f"%{{percent:.{int(d)}%}}" if isinstance(d, int) and not isinstance(d, bool) else "%{percent:.0%}"
    trace = {"type": "pie", "labels": labs, "values": [vals[lab] for lab in labs], "sort": False,
             "direction": "clockwise", "hole": 0.55 if donut else 0, "marker": {"colors": cols,
                                                                                  "line": {"color": "#FFFFFF", "width": 1.5}},
             "texttemplate": "" if fmt.get("labels") is False else pct, "textposition": "inside",
             "insidetextorientation": "horizontal",
             "hovertext": [f"{lab}<br>{what}: {nf(vals[lab])}" for lab in labs],
             "hovertemplate": "%{hovertext}<br>%{percent:.1%}<extra></extra>"}
    fig = {"data": [trace],
           "layout": {"autosize": True, "margin": {"l": 10, "r": 10, "t": 10, "b": 10},
                      "font": {"family": "Segoe UI, Inter, sans-serif", "size": 11, "color": "#1C2321"},
                      "paper_bgcolor": "#FFFFFF", "showlegend": True,
                      "legend": {"orientation": "v", "x": 1.01, "y": 1, "xanchor": "left", "font": {"size": 10}}}}
    if donut:
        total = sum(vals[lab] for lab in labs)
        fig["layout"]["annotations"] = [{"text": f"<b>{nf(total) if agg not in COUNT_AGGS else int(total)}</b><br>"
                                                 f"<span style='font-size:10px'>{what}</span>",
                                         "x": 0.5, "y": 0.5, "xref": "paper", "yref": "paper", "showarrow": False,
                                         "font": {"size": 15}}] if agg in COUNT_AGGS or agg == "sum" else []
    return {"kind": "plotly", "figure": fig, "clickable": True, "note": note,
            "colours": {"groups": [[lab, c] for lab, c in zip(labs, cols)], "single": None},
            "xl": {"head": [ds.fields[lk].label, what], "rows": [[lab, vals[lab]] for lab in labs]}}


# ── control chart (individuals chart, SPC) ──────────────────────────────
def control_limits(ys: Sequence[float]) -> Tuple[float, float, float, float]:
    """(mean, sigma, LCL, UCL) of an individuals chart: sigma from the mean moving range / 1.128."""
    mean = sum(ys) / len(ys)
    mrs = [abs(b - a) for a, b in zip(ys, ys[1:])]
    sigma = (sum(mrs) / len(mrs) / 1.128) if mrs else 0.0
    return mean, sigma, mean - 3 * sigma, mean + 3 * sigma


def run_points(ys: Sequence[float], mean: float, n: int = RUN_LENGTH) -> List[bool]:
    """True for points in a run of n or more in a row on the same side of the mean."""
    out = [False] * len(ys)
    i = 0
    while i < len(ys):
        side = (ys[i] > mean) - (ys[i] < mean)
        j = i
        while j + 1 < len(ys) and side and ((ys[j + 1] > mean) - (ys[j + 1] < mean)) == side:
            j += 1
        if side and j - i + 1 >= n:
            for k in range(i, j + 1):
                out[k] = True
        i = j + 1
    return out


def _control(ds, res, xk, yk, palette, fmt) -> Dict[str, Any]:
    fmt = fmt or {}
    nf = number_format(fmt)
    fy = ds.fields[yk]
    fx = ds.fields.get(xk) if xk else None
    pts = []
    for tid in res.ids:
        m = res.matched.get(tid)
        y = _num(ds.value(yk, tid, m))
        if y is None:
            continue
        t = ds.by_id[tid]
        if fx is not None:
            raw = ds.value(xk, tid, m)
            if raw in (None, ""):
                continue
            xv = _num(raw) if fx.kind == "num" else None
            key = (0, xv, "") if xv is not None else (1, 0.0, cat_label(raw))
            xlab = _fmt(xv) if xv is not None else cat_label(raw)
        else:
            key = (0, 0.0, (t.series or "", int(t.nr or 0)))
            xlab = f"V{t.nr}"
        pts.append({"tid": tid, "y": y, "key": key, "xlab": xlab, "trial": f"V{t.nr}", "series": t.series or ""})
    if len(pts) < 3:
        return {"kind": "empty", "message": "A control chart needs at least 3 trials with a value"}
    pts.sort(key=lambda p: (p["key"], p["series"], p["trial"]))
    note = ""
    if len(pts) > MAX_CONTROL_POINTS:
        note = f"Only the last {MAX_CONTROL_POINTS} of {len(pts)} trials - filter to see the others"
        pts = pts[-MAX_CONTROL_POINTS:]
    ys = [p["y"] for p in pts]
    mean, sigma, lcl, ucl = control_limits(ys)
    runs = run_points(ys, mean)
    out_of = [y > ucl or y < lcl for y in ys] if sigma > 0 else [False] * len(ys)
    base = _hex(fmt.get("colour")) or PALETTES.get(palette, PALETTES[DEFAULT_PALETTE])["colours"][0]
    marker = ["#C62828" if o else "#C98A00" if r else base for o, r in zip(out_of, runs)]
    xs = list(range(1, len(pts) + 1))
    unit = f" {fy.unit}" if fy.unit else ""
    hover = [f"<b>{p['trial']}</b> · {p['series']}" + (f"<br>{fx.title}: {p['xlab']}" if fx is not None else "")
             + f"<br>{fy.title}: {nf(p['y'])}{unit}"
             + ("<br><b>outside the limits</b>" if o else "<br>run on one side of the mean" if r else "")
             for p, o, r in zip(pts, out_of, runs)]
    every = max(1, math.ceil(len(xs) / 30))
    fig = {"data": [{"type": "scatter", "mode": "lines+markers", "x": xs, "y": ys, "customdata": [p["tid"] for p in pts],
                     "line": {"color": base, "width": 1.4}, "marker": {"color": marker, "size": 6},
                     "hovertext": hover, "hoverinfo": "text", "name": fy.title, "showlegend": False}],
           "layout": {"autosize": True, "margin": {"l": 52, "r": 70, "t": 8, "b": 52},
                      "font": {"family": "Segoe UI, Inter, sans-serif", "size": 11, "color": "#1C2321"},
                      "plot_bgcolor": "#FFFFFF", "paper_bgcolor": "#FFFFFF", "showlegend": False, "hovermode": "closest",
                      "xaxis": {"title": {"text": fx.label if fx is not None else "Trials in order (series, trial)"},
                                "tickmode": "array", "tickvals": xs[::every], "ticktext": [p["xlab"] for p in pts][::every],
                                "gridcolor": "#EEF1ED", "zeroline": False},
                      "yaxis": {"title": {"text": fy.label}, "gridcolor": "#EEF1ED", "zeroline": False},
                      "shapes": [], "annotations": []}}
    lay = fig["layout"]
    for val, name, colour, dash in ((ucl, "UCL", "#C62828", "dash"), (mean, "Mean", "#232E3A", "solid"),
                                    (lcl, "LCL", "#C62828", "dash")):
        if name != "Mean" and sigma <= 0:
            continue
        lay["shapes"].append({"type": "line", "xref": "paper", "yref": "y", "x0": 0, "x1": 1, "y0": val, "y1": val,
                              "line": {"color": colour, "width": 1.3, "dash": dash}})
        lay["annotations"].append({"text": f"{name} {nf(val)}", "xref": "paper", "yref": "y", "x": 1.005, "y": val,
                                   "xanchor": "left", "showarrow": False, "font": {"size": 10, "color": colour}})
    n_out, n_run = sum(out_of), sum(runs)
    summary = f"{n_out} of {len(ys)} outside ±3σ" + (f" · {n_run} in runs of {RUN_LENGTH}+ on one side" if n_run else "")
    return {"kind": "plotly", "figure": fig, "selectable": True, "note": "; ".join(x for x in (summary, note) if x),
            "colours": {"groups": [], "single": base},
            "xl": {"head": ["Trial", "Series"] + ([fx.label] if fx is not None else []) + [fy.label, "Mean", "LCL", "UCL",
                                                                                          "Signal"],
                   "rows": [[p["trial"], p["series"]] + ([p["xlab"]] if fx is not None else [])
                            + [p["y"], mean, lcl, ucl, "outside" if o else "run" if r else ""]
                            for p, o, r in zip(pts, out_of, runs)]}}


# ── radar ────────────────────────────────────────────────────────────────
def _radar(ds, res, lk, keys, agg, palette, fmt) -> Dict[str, Any]:
    """One shape per Legend value. Every axis runs from the lowest to the highest group (0-100),
    because the fields have different units; the real values are in the tooltip."""
    fmt = fmt or {}
    nf = number_format(fmt)
    groups: Dict[str, List[int]] = {}
    for tid in res.ids:
        m = res.matched.get(tid)
        for lab in (_labels(ds, lk, tid, m) if lk else ["All trials"]):
            groups.setdefault(lab, []).append(tid)
    labs = sorted(groups, key=lambda k: (k == NONE_LABEL, -len(groups[k]), k.lower()))
    note = ""
    if len(labs) > MAX_LEGEND:
        note = f"{len(labs) - MAX_LEGEND} smaller groups not shown - use a slicer or filter to pick the ones you want"
        labs = labs[:MAX_LEGEND]
    vals = {(g, k): aggregate([_num(ds.value(k, t, res.matched.get(t))) for t in groups[g]], agg)
            for g in labs for k in keys}
    keys = [k for k in keys if any(vals[(g, k)] is not None for g in labs)]
    if len(keys) < 3:
        return {"kind": "empty", "message": "Fewer than 3 of these fields have values"}
    span = {}
    for k in keys:
        xs = [vals[(g, k)] for g in labs if vals[(g, k)] is not None]
        span[k] = (min(xs), max(xs))
    colours = PALETTES.get(palette, PALETTES[DEFAULT_PALETTE])["colours"]
    own = fmt.get("colours") or {}
    theta = [ds.fields[k].title for k in keys]
    traces, groups_out = [], []
    for i, g in enumerate(labs):
        r, hover = [], []
        for k in keys:
            x = vals[(g, k)]
            lo, hi = span[k]
            r.append(None if x is None else (50.0 if hi == lo else 100.0 * (x - lo) / (hi - lo)))
            f = ds.fields[k]
            hover.append(f"{g}<br>{f.title}: {nf(x) if x is not None else '–'}{(' ' + f.unit) if f.unit else ''}")
        col = _hex(own.get(g)) or colours[i % len(colours)]
        groups_out.append([g, col])
        traces.append({"type": "scatterpolar", "r": r + r[:1], "theta": theta + theta[:1], "name": g,
                       "fill": "toself", "fillcolor": _alpha(col, 0.18), "line": {"color": col, "width": 2},
                       "marker": {"size": 5, "color": col}, "hovertext": hover + hover[:1], "hoverinfo": "text"})
    fig = {"data": traces,
           "layout": {"autosize": True, "margin": {"l": 40, "r": 40, "t": 24, "b": 24},
                      "font": {"family": "Segoe UI, Inter, sans-serif", "size": 11, "color": "#1C2321"},
                      "paper_bgcolor": "#FFFFFF", "showlegend": True,
                      "legend": {"orientation": "v", "x": 1.01, "y": 1, "xanchor": "left", "font": {"size": 10}},
                      "polar": {"bgcolor": "#FFFFFF",
                                "radialaxis": {"range": [0, 100], "showticklabels": False, "gridcolor": "#E3E7E2",
                                               "linecolor": "#E3E7E2"},
                                "angularaxis": {"gridcolor": "#E3E7E2", "linecolor": "#C9D1C8"}}}}
    note = "; ".join(x for x in ("Each axis: lowest group inside, highest outside", note) if x)
    return {"kind": "plotly", "figure": fig, "clickable": bool(lk), "note": note,
            "colours": {"groups": groups_out, "single": None},
            "xl": {"head": [ds.fields[lk].label if lk else ""] + [ds.fields[k].label for k in keys],
                   "rows": [[g] + [vals[(g, k)] for k in keys] for g in labs]}}


def _alpha(hexc: str, a: float) -> str:
    h = hexc.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})" if len(h) == 6 else hexc


# ── stacked fields (several number fields in one column) ──────────────────
def _stack(ds, res, xk, keys, agg="avg", stack="percent", palette=DEFAULT_PALETTE,
           lines: Sequence[str] = (), fmt: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """One column per X value (or one for all trials), one part per field. "percent": the share of
    each field in the sum of the fields (A, B, C knots = 100 %). `lines`: number fields drawn as
    lines on a second axis on the right (combo chart, e.g. FP/m over the knot shares)."""
    fmt = fmt or {}
    nf = number_format(fmt)
    lines = [k for k in lines if k not in keys]
    groups: Dict[str, List[int]] = {}
    order: Dict[str, Any] = {}
    for tid in res.ids:
        m = res.matched.get(tid)
        if all(_num(ds.value(k, tid, m)) is None for k in list(keys) + list(lines)):
            continue
        labs = _labels(ds, xk, tid, m) if xk else ["All trials"]
        for lab in labs:
            groups.setdefault(lab, []).append(tid)
            if xk == "trial":
                t = ds.by_id[tid]
                order[lab] = (t.series, t.nr, (t.series.split(" ")[0] if t.series else ""))
    if not groups:
        return {"kind": "empty", "message": "No trial has values for these fields"}
    note = ""
    if xk == "trial":
        xs = sorted(groups, key=lambda k: order.get(k, ("", 0, ""))[:2])
        limit = MAX_TRIAL_COLUMNS
    elif xk and xk in TIME_KEYS:
        xs = [x for x in _time_axis(list(groups), xk) if x in groups]
        limit = 10 ** 6
    elif xk and ds.fields[xk].kind == "num":
        xs = sorted(groups, key=_sort_key)
        limit = MAX_CATEGORIES
    else:
        xs = sorted(groups, key=lambda k: (k == NONE_LABEL, -len(groups[k]), k.lower()))
        limit = MAX_CATEGORIES
    if fmt.get("sort") not in (None, "auto") or fmt.get("top"):
        def whole(x):
            parts = [aggregate([_num(ds.value(k, t, res.matched.get(t))) for t in groups[x]], agg) for k in keys]
            parts = [p for p in parts if p is not None]
            return sum(parts) if parts else None
        n_all = len(xs)
        xs, hidden = order_categories(xs, whole, fmt)
        note = _top_note(hidden, n_all)
    if len(xs) > limit:
        note = f"{len(xs) - limit} more columns not shown - filter or use a slicer to pick the ones you want"
        xs = xs[:limit]
    vals = {(x, k): aggregate([_num(ds.value(k, t, res.matched.get(t))) for t in groups[x]], agg)
            for x in xs for k in keys}
    totals = {x: sum(vals[(x, k)] or 0 for k in keys) for x in xs}
    colours = PALETTES.get(palette, PALETTES[DEFAULT_PALETTE])["colours"]
    traces = []
    for i, k in enumerate(keys):
        f = ds.fields[k]
        ys, text, hover = [], [], []
        for x in xs:
            a = vals[(x, k)]
            share = (100.0 * a / totals[x]) if a is not None and totals[x] else None
            y = share if stack == "percent" else a
            ys.append(y)
            text.append("" if y is None else (f"{nf(share)} %" if stack == "percent" else nf(a)))
            hover.append(f"{x}<br>{f.label}: {_kfmt(a) if a is not None else '–'}"
                         + (f" ({_kfmt(share)} %)" if share is not None else "")
                         + (f"<br>{AGGS.get(agg, '')} of {len(groups[x])} trials" if len(groups[x]) > 1 else ""))
        tr = {"type": "bar", "x": xs, "y": ys, "name": f.label, "hovertext": hover, "hoverinfo": "text",
              "marker": {"color": _hex((fmt.get("colours") or {}).get(f.label)) or colours[i % len(colours)]}}
        if fmt.get("labels") or (fmt.get("labels") is None and len(xs) <= 30):
            tr.update({"text": text, "textposition": "inside" if stack != "grouped" else "outside",
                       "insidetextanchor": "middle", "cliponaxis": False})
        traces.append(tr)
    ytitle = "Share (%)" if stack == "percent" else (AGGS.get(agg, "") if len(groups) and max(map(len, groups.values())) > 1
                                                    else "Value")
    for j, k in enumerate(lines):
        f = ds.fields[k]
        ys = [aggregate([_num(ds.value(k, t, res.matched.get(t))) for t in groups[x]], agg) for x in xs]
        traces.append({"type": "scatter", "mode": "lines+markers", "x": xs, "y": ys, "name": f.label, "yaxis": "y2",
                       "line": {"color": LINE_COLOURS[j % len(LINE_COLOURS)], "width": 2}, "marker": {"size": 5},
                       "hovertext": [f"{x}<br>{f.label}: {_kfmt(y) if y is not None else '–'}" for x, y in zip(xs, ys)],
                       "hoverinfo": "text", "connectgaps": False})
    ticks = {}
    if xk == "trial":           # short labels: "V12", or "2026-71-005.02 · V12" when several series are shown
        one = len({order[x][0] for x in xs}) == 1
        every = max(1, math.ceil(len(xs) / 40))        # many trials: label only every n-th column
        shown = xs[::every]
        ticks = {"tickmode": "array", "tickvals": shown,
                 "ticktext": [f"V{order[x][1]}" if one else f"{order[x][2]} · V{order[x][1]}" for x in shown]}
    fig = {"data": traces,
           "layout": {"autosize": True, "barmode": "group" if stack == "grouped" else "stack", "bargap": 0.2,
                      "margin": {"l": 52, "r": 16, "t": 14, "b": 60 if xk == "trial" else 44},
                      "font": {"family": "Segoe UI, Inter, sans-serif", "size": 11, "color": "#1C2321"},
                      "plot_bgcolor": "#FFFFFF", "paper_bgcolor": "#FFFFFF",
                      "xaxis": {"type": "category", "title": {"text": ds.fields[xk].label if xk else ""},
                                "categoryorder": "array", "categoryarray": xs, "automargin": True, **ticks},
                      "yaxis": {"title": {"text": ytitle}, "gridcolor": "#E3E7E2", "rangemode": "tozero",
                                **({"range": [0, 100]} if stack == "percent" else {})},
                      "legend": {"orientation": "v", "x": 1.01, "y": 1, "xanchor": "left", "font": {"size": 10},
                                 "traceorder": "normal"}}}
    if lines:
        lay = fig["layout"]
        lay["yaxis2"] = {"overlaying": "y", "side": "right", "showgrid": False, "zeroline": False,
                         "title": {"text": ds.fields[lines[0]].label if len(lines) == 1 else "Line"},
                         "tickfont": {"color": LINE_COLOURS[0]} if len(lines) == 1 else {}}
        lay["margin"].update({"r": 60, "t": 54})
        lay["legend"] = {"orientation": "h", "x": 0, "y": 1.05, "yanchor": "bottom", "font": {"size": 10},
                         "bgcolor": "rgba(0,0,0,0)",
                         "traceorder": "normal"}
    return {"kind": "plotly", "figure": fig, "clickable": bool(xk), "note": note,
            "colours": {"groups": [[tr["name"], tr["marker"]["color"]] for tr in traces[:len(keys)]], "single": None}}


# ── slicer ───────────────────────────────────────────────────────────────
def slicer_style(ds: TrialDataset, v: Dict[str, Any]) -> str:
    key = (v.get("wells") or {}).get("field")
    f = ds.fields.get(key) if key else None
    default = "between" if f is not None and f.kind == "num" else "hierarchy" if key in MONTH_OF else "list"
    style = v.get("style") or default
    if style == "between" and (f is None or f.kind != "num"):
        style = "list"
    if style == "hierarchy" and key not in MONTH_OF:
        style = "list"
    return style if style in SLICER_STYLES else "list"


def _slicer(ds, res, key, v) -> Dict[str, Any]:
    """Options of a slicer: the values the OTHER filters leave, with counts
    (the caller passes filters without this slicer's own selection)."""
    f = ds.fields[key]
    style = slicer_style(ds, v)
    out: Dict[str, Any] = {"kind": "slicer", "style": style, "fkind": f.kind, "unit": f.unit,
                           "multi": v.get("multi", True) is not False, "sel": v.get("sel") or {}}
    if style == "hierarchy":
        return {**out, **_month_tree(ds, res, MONTH_OF[key])}
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


def _month_tree(ds: TrialDataset, res: Result, mk: str) -> Dict[str, Any]:
    """Years (newest first) with their months 1-12 and trial counts; "(none)" = without a date."""
    counts: Dict[str, int] = {}
    for tid in res.ids:
        lab = cat_label(ds.value(mk, tid, res.matched.get(tid)))
        counts[lab] = counts.get(lab, 0) + 1
    years = sorted({lab[:4] for lab in counts if lab != NONE_LABEL and lab[:4].isdigit()}, reverse=True)
    tree = []
    for y in years:
        months = [{"label": f"{y}-{m:02d}", "name": MONTH_NAMES[m - 1], "n": counts.get(f"{y}-{m:02d}", 0)}
                  for m in range(1, 13)]
        tree.append({"year": y, "n": sum(mo["n"] for mo in months), "months": months})
    options = [{"label": mo["label"], "n": mo["n"]} for t in tree for mo in t["months"] if mo["n"]]
    if counts.get(NONE_LABEL):
        options.append({"label": NONE_LABEL, "n": counts[NONE_LABEL]})
    return {"tree": tree, "none": counts.get(NONE_LABEL, 0), "options": options, "more": 0,
            "month_field": ds.fields[mk].title if mk in ds.fields else mk}


def slicer_filter(ds: TrialDataset, v: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The filter a slicer's selection puts on the other visuals (None = nothing chosen)."""
    if v.get("type") != "slicer":
        return None
    key = (v.get("wells") or {}).get("field")
    f = ds.fields.get(key) if key else None
    sel = v.get("sel") or {}
    if f is None or not sel:
        return None
    if sel.get("values") and slicer_style(ds, v) == "hierarchy":
        mk = MONTH_OF[key]
        return {"key": mk, "values": [str(a) for a in sel["values"]]} if mk in ds.fields else None
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
    elif v.get("type") == "stack" and w.get("x"):
        f = _filter_for(ds, w["x"], click.get("x"))
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
    elif v.get("type") == "pie" and w.get("legend") and click.get("x") not in (None, "Other"):
        f = _filter_for(ds, w["legend"], click.get("x"))
        if f:
            out.append(f)
    elif v.get("type") == "radar" and w.get("legend") and click.get("n") not in (None, "", "Other"):
        f = _filter_for(ds, w["legend"], click.get("n"))
        if f:
            out.append(f)
    elif v.get("type") in ("bar", "box", "violin", "line") and w.get("x"):
        x_key, extra, _info = drill_state(ds, v)
        out += extra
        f = _filter_for(ds, x_key, click.get("x"))
        if f:
            out.append(f)
    return out


# ── drill-through (Nutzerwunsch 2026-11-02, like Power BI) ───────────────
# A page with page["drillthrough"] = [field keys] is a detail page: a right-click on a bar, box, cell,
# slice … of another page whose visual uses one of these fields jumps there, filtered to that value.
# page["dt_keep"] False = only the clicked value, else (default) also the filters of the clicked visual.
CLICK_TYPES = ("bar", "box", "violin", "line", "matrix", "column", "stack", "pie", "radar")


def click_keys(ds: TrialDataset, v: Dict[str, Any]) -> List[str]:
    """The fields a click on visual v can filter."""
    w = v.get("wells") or {}
    t = v.get("type")
    if t not in CLICK_TYPES:
        return []
    wells = {"matrix": ("rows", "cols"), "stack": ("x",), "column": ("x", "legend"), "pie": ("legend",),
             "radar": ("legend",)}.get(t, ("x",))
    keys = [w.get(k) for k in wells] + (list(w.get("drill") or []) if t in DRILL_TYPES else [])
    return [k for k in keys if k in ds.fields]


def drill_through_pages(spec: Dict[str, Any], ds: TrialDataset, v: Dict[str, Any],
                        page_id: str) -> List[Dict[str, str]]:
    """Pages a right-click on visual v (on page page_id) can drill through to."""
    keys = set(click_keys(ds, v))
    if not keys:
        return []
    return [{"id": pg["id"], "title": pg.get("title") or pg["id"]} for pg in spec["pages"]
            if pg["id"] != page_id and keys & set(pg.get("drillthrough") or [])]


def drill_through_filters(ds: TrialDataset, v: Dict[str, Any], click: Dict[str, Any], target: Dict[str, Any],
                          context: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filters the detail page gets: the clicked value of its drill-through fields, plus (Keep all filters)
    the filters of the clicked visual (context, without "Find trials"). [] = nothing to drill through."""
    keys = set(target.get("drillthrough") or [])
    clicked = [f for f in click_filters(ds, v, click) if f.get("key") in keys]
    if not clicked:
        return []
    keep = [] if target.get("dt_keep") is False else [f for f in context if f not in clicked]
    return keep + clicked


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

# ── model view (read only, Nutzerwunsch 2026-11-02) ─────────────────────
# How every group of the Fields pane hangs at the trial. Nobody can change anything here: the
# relations are fixed in db/trial_explorer.py. group -> (title, relation, how a value per trial comes about)
MODEL_GROUPS = {
    "General": ("Trial", "", "One row per trial - the centre of the model. Every visual counts and averages "
                             "trials. Machine, series, owner and experiment number come with the trial."),
    "Machine": ("Machine settings", "1 : 1", "Stored on the trial itself (tblTrial): one value per trial."),
    "Machine (per ply)": ("Settings per ply", "1 : n", "One row per ply of the trial (tblTrialSettings) - shown "
                                                       "as the average over the plies."),
    "Time": ("Time", "1 : 1", "Year and month of the trial series. Trial year / month: the trial's own date, "
                              "else the date of its series."),
    "Experiment": ("Experiment", "n : 1", "Several trial series belong to one experiment (tblExperimente). "
                                          "Experiment start and owner come from its earliest series with a date."),
    "Jet": ("Jet", "n : 1", "The jet used in the trial (tblTrial.JetID → tblJets) - many trials share one jet. "
                            "0 in a jet field means: not entered."),
    "Yarn": ("Yarn per ply", "1 : n", "A trial has one or more plies, each with its yarn (tblYarn). Several yarn "
                                      "filters apply to the same ply; 'Yarn filters apply to' picks any, core or "
                                      "effect ply."),
    "Calculated": ("Calculated fields", "formula", "Your own formulas from other fields of the same trial - "
                                                   "saved with this dashboard."),
}
LAB_RELATION = ("1 : n", "Several measurements per trial → the average per trial. 0 and empty count as "
                         "no value.")


def model_info(fields: Sequence[Any]) -> Dict[str, Any]:
    """Nodes of the model view: one per group of the Fields pane, with tables and fields."""
    from db.trial_explorer import TABLE_GROUPS, group_order, parent_group
    groups: Dict[str, List[Any]] = {}
    for f in fields:
        groups.setdefault(f.group, []).append(f)
    nodes = []
    for g in group_order(fields):
        fs = groups.get(g) or []
        if not fs:
            continue
        tables = sorted({str(t) for f in fs for t in (f.source.get("main_table"), f.source.get("alt_table")) if t},
                        key=str.lower)
        tension = any("tension" in str(f.source.get("condition") or "").lower() for f in fs)
        if g in MODEL_GROUPS:
            title, rel, how = MODEL_GROUPS[g]
        else:
            title, (rel, how) = g, LAB_RELATION
            if tension:
                how += " One field per test tension (an average over tensions would mean nothing)."
        if g == "Jet":
            tables = ["tblJets"]
        elif g == "Yarn":
            tables = ["tblYarn", "tblTrialSettings"]
        elif g == "Experiment":
            tables = ["tblExperimente", "tblTrialSeries"]
        elif g == "Time":
            tables = ["tblTrialSeries", "tblTrial"]
        elif g == "General" and not tables:
            tables = ["tblTrial", "tblTrialSeries"]
        nodes.append({"id": g, "title": title, "relation": rel, "how": how, "tables": tables,
                      "kind": "centre" if g == "General" else "lab" if parent_group(g) else
                      "calc" if g == "Calculated" else "dim",
                      "fields": [{"key": f.key, "label": f.label, "kind": f.kind} for f in fs]})
    return {"nodes": nodes, "known_tables": sorted(TABLE_GROUPS)}


def filled_counts(ds: TrialDataset, keys: Sequence[str]) -> Dict[str, int]:
    """Per field: how many (real) trials have a value - yarn fields: in any ply."""
    out: Dict[str, int] = {}
    for k in keys:
        f = ds.fields.get(k)
        if f is None:
            continue
        try:
            if f.level == "yarn":
                out[k] = sum(1 for t in ds.trials if any(p.values.get(k) not in (None, "") for p in t.plies))
            else:
                vals = ds.values(k)
                out[k] = sum(1 for t in ds.trials if vals.get(t.id) not in (None, ""))
        except Exception:
            out[k] = 0
    return out

