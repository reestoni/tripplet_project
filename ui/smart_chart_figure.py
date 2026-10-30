# ui/smart_chart_figure.py
"""Builds the Plotly figure (plain dicts) and the trial list for the new
Smart Chart (ui/screen_smart_chart.py) from a db.trial_explorer dataset.

Chart types (CHART_TYPES): points, points + trend line (per colour, with
R²), mean line ± SD, bars (mean ± SD), box plot, violin, histogram of Y and
an X/Y density map. Colour by a list field (palette, max MAX_COLOURS + "Other",
own colours per value via `colour_map`) or a number field (colour scale for
points; other chart types get the number field cut into 5 ranges).
Split by a list field -> small multiples with shared axes (max MAX_PANELS).
Style options: palette, different shapes per colour, log axes, point size,
dark background.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from db.trial_explorer import NONE_LABEL, Result, TrialDataset, cat_label

# key -> (label, tooltip)
CHART_TYPES: Dict[str, Tuple[str, str]] = {
    "points": ("Points", "One point per trial"),
    "trend": ("Points + trend line", "One point per trial plus a straight trend line per colour, with R²"),
    "line": ("Mean line", "Mean per X value with standard deviation, joined by a line"),
    "bar": ("Bars", "Mean per X value as bars, with standard deviation"),
    "box": ("Box plot", "Spread per X value: median, quartiles, outliers"),
    "violin": ("Violin", "Spread per X value as a smooth shape"),
    "hist": ("Histogram of Y", "How the Y values are spread (X is not used)"),
    "density": ("Density map", "Where most trials lie in X/Y (colour = number of trials)"),
}
MODE_TO_CHART = {"each": "points", "mean": "line"}

PALETTES: Dict[str, Dict[str, Any]] = {
    "trippleT": {"label": "TrippleT", "colours": ["#2F6DB5", "#D9822B", "#4B5058", "#39A650", "#B5446E",
                                                 "#7FB8E6", "#C9A227", "#8C6BB1"], "scale": "Viridis"},
    "heberlein": {"label": "Heberlein green", "colours": ["#1F7A3A", "#8CC63F", "#0F4D25", "#5FAE6E", "#2E5E3E",
                                                          "#B5D99C", "#6E8B74", "#A3A9A4"], "scale": "Greens"},
    "colourblind": {"label": "Colour-blind safe", "colours": ["#0072B2", "#E69F00", "#009E73", "#D55E00",
                                                              "#CC79A7", "#56B4E9", "#F0E442", "#000000"],
                    "scale": "Cividis"},
    "bold": {"label": "Bold", "colours": ["#E6194B", "#3CB44B", "#4363D8", "#F58231", "#911EB4", "#42D4F4",
                                          "#F032E6", "#9A6324"], "scale": "Plasma"},
    "pastel": {"label": "Pastel", "colours": ["#8DA0CB", "#FC8D62", "#66C2A5", "#E78AC3", "#A6D854", "#FFD92F",
                                              "#E5C494", "#B3B3B3"], "scale": "Blues"},
    "grey": {"label": "Greyscale (print)", "colours": ["#111111", "#6B6B6B", "#A0A0A0", "#3A3A3A", "#858585",
                                                       "#C4C4C4", "#252525", "#5A5A5A"], "scale": "Greys"},
}
PALETTE = PALETTES["trippleT"]["colours"]
SYMBOLS = ["circle", "square", "diamond", "triangle-up", "x", "triangle-down", "star", "cross"]
OTHER_COLOUR = "#B8BEB8"
MAX_COLOURS = len(PALETTE)
MAX_PANELS = 9
OTHER = "Other"
NUM_BINS = 5

_LIGHT = {"bg": "#FFFFFF", "fg": "#1C2321", "grid": "#EEF1ED", "axis": "#9AA59C", "other": OTHER_COLOUR}
_DARK = {"bg": "#161B1A", "fg": "#E4EAE6", "grid": "#2B3331", "axis": "#56605C", "other": "#5E6663"}


def _num(v: Any) -> Optional[float]:
    if v is None or isinstance(v, bool):
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def _sort_key(label: Any):
    try:
        return (0, float(label), "")
    except (TypeError, ValueError):
        return (1 if label != NONE_LABEL else 2, 0.0, str(label).lower())


def _fmt(v: Any) -> str:
    x = _num(v)
    if x is None:
        return "" if v is None else str(v)
    return f"{x:.3f}".rstrip("0").rstrip(".") if abs(x) < 1000 else f"{x:.0f}"


def _bins(values: List[float], n: int = NUM_BINS) -> List[Tuple[float, float]]:
    """n ranges with (roughly) equally many values, rounded edges."""
    xs = sorted(values)
    if not xs:
        return []
    edges = [xs[min(len(xs) - 1, int(len(xs) * i / n))] for i in range(n)] + [xs[-1]]
    edges = sorted(set(round(e, 2) for e in edges))
    if len(edges) == 1:
        return [(edges[0], edges[0])]
    return [(edges[i], edges[i + 1]) for i in range(len(edges) - 1)]


def _bin_label(v: float, ranges: List[Tuple[float, float]], unit: str) -> str:
    for i, (a, b) in enumerate(ranges):
        if v <= b or i == len(ranges) - 1:
            return f"{_fmt(a)} – {_fmt(b)}{(' ' + unit) if unit else ''}"
    return NONE_LABEL


def collect(ds: TrialDataset, res: Result, x: str, y: str,
            colour: Optional[str] = None, split: Optional[str] = None,
            need_x: bool = True) -> List[Dict[str, Any]]:
    """One entry per trial that has a Y value (and an X value if need_x)."""
    fx = ds.fields[x]
    fc = ds.fields.get(colour) if colour else None
    out = []
    for tid in res.ids:
        m = res.matched.get(tid)
        yv = _num(ds.value(y, tid, m))
        xv_raw = ds.value(x, tid, m)
        xv = _num(xv_raw) if fx.kind == "num" else (cat_label(xv_raw) if xv_raw not in (None, "") else None)
        if yv is None or (need_x and xv is None):
            continue
        cv = ds.value(colour, tid, m) if colour else None
        t = ds.by_id[tid]
        out.append({
            "tid": tid, "x": xv, "y": yv,
            "colour": (_num(cv) if fc is not None and fc.kind == "num" else cat_label(cv)) if colour else "",
            "split": cat_label(ds.value(split, tid, m)) if split else "",
            "trial": f"V{t.nr}", "series": t.series, "series_id": t.series_id, "exp_pk": t.exp_pk,
            "experiment": t.experiment, "machine": t.machine, "jet": t.jet,
            "yarn": (m.values.get("yarn_name") if m is not None else None) or "",
        })
    return out


def _top(labels: List[str], n: int) -> List[str]:
    counts: Dict[str, int] = {}
    for lab in labels:
        counts[lab] = counts.get(lab, 0) + 1
    return [k for k, _ in sorted(counts.items(), key=lambda kv: (-kv[1], _sort_key(kv[0])))][:n]


def linear_fit(xs: List[float], ys: List[float]) -> Optional[Tuple[float, float, float]]:
    """(slope, intercept, R²) or None for fewer than 3 points / no spread."""
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((a - mx) ** 2 for a in xs)
    if sxx == 0:
        return None
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    slope = sxy / sxx
    icpt = my - slope * mx
    syy = sum((b - my) ** 2 for b in ys)
    r2 = 1.0 if syy == 0 else max(0.0, 1 - sum((b - (slope * a + icpt)) ** 2 for a, b in zip(xs, ys)) / syy)
    return slope, icpt, r2


def _stats(vals: List[float]) -> Tuple[float, float]:
    m = sum(vals) / len(vals)
    sd = math.sqrt(sum((a - m) ** 2 for a in vals) / (len(vals) - 1)) if len(vals) > 1 else 0.0
    return m, sd


def build_figure(ds: TrialDataset, res: Result, x: str, y: str, colour: Optional[str] = None,
                 split: Optional[str] = None, mode: str = "each", chart: Optional[str] = None,
                 palette: str = "trippleT", colour_map: Optional[Dict[str, str]] = None,
                 shapes: bool = False, logx: bool = False, logy: bool = False, size: int = 8,
                 dark: bool = False) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]:
    """(figure, plotted rows, info). info: plotted, hidden_panels, x_is_cat,
    colour_groups [(label, hex)] for the colour editor, chart."""
    chart = chart if chart in CHART_TYPES else MODE_TO_CHART.get(mode, "points")
    th = _DARK if dark else _LIGHT
    pal = PALETTES.get(palette, PALETTES["trippleT"])
    fx, fy = ds.fields[x], ds.fields[y]
    fc = ds.fields.get(colour) if colour else None
    uses_x = chart != "hist"
    pts = collect(ds, res, x, y, colour, split, need_x=uses_x)

    # colour: continuous scale (points with a number field) or groups
    continuous = bool(fc is not None and fc.kind == "num" and chart in ("points", "trend"))
    if chart == "density":
        colour, fc, continuous = None, None, False
        for p in pts:
            p["colour"] = ""
    if fc is not None and fc.kind == "num" and not continuous:
        ranges = _bins([p["colour"] for p in pts if p["colour"] is not None])
        for p in pts:
            p["colour"] = _bin_label(p["colour"], ranges, fc.unit) if p["colour"] is not None else NONE_LABEL
    if continuous:
        colour_list = [""]
    else:
        groups = _top([p["colour"] for p in pts], MAX_COLOURS) if colour else [""]
        if fc is not None and fc.kind == "num":
            groups = sorted(groups, key=lambda g: _sort_key(str(g).split(" ")[0]))
        has_other = bool(colour) and any(p["colour"] not in groups for p in pts)
        for p in pts:
            if colour and p["colour"] not in groups:
                p["colour"] = OTHER
        colour_list = groups + ([OTHER] if has_other else [])
    colour_map = colour_map or {}
    defaults = {c: (th["other"] if c == OTHER else pal["colours"][i % len(pal["colours"])])
                for i, c in enumerate(colour_list)}
    colour_of = {c: colour_map.get(c) or defaults[c] for c in colour_list}
    symbol_of = {c: (SYMBOLS[i % len(SYMBOLS)] if shapes else "circle") for i, c in enumerate(colour_list)}

    panels = sorted(_top([p["split"] for p in pts], 10 ** 6), key=_sort_key) if split else [""]
    hidden = max(0, len(panels) - MAX_PANELS)
    panels = panels[:MAX_PANELS]
    if split:
        pts = [p for p in pts if p["split"] in panels]

    x_is_cat = fx.kind == "cat" or chart in ("bar", "box", "violin")
    if chart in ("bar", "box", "violin") and fx.kind == "num":
        for p in pts:
            p["xlab"] = _fmt(p["x"])
    else:
        for p in pts:
            p["xlab"] = p["x"]
    x_cats = sorted({p["xlab"] for p in pts}, key=_sort_key) if (x_is_cat and uses_x) else None

    n = len(panels)
    cols = 1 if n == 1 else (2 if n in (2, 4) else 3)
    rows = int(math.ceil(n / cols))
    gap_x, gap_y = 0.06, (0.12 if n > 1 else 0.0)
    w = (1 - gap_x * (cols - 1)) / cols
    h = (1 - gap_y * (rows - 1)) / rows

    traces: List[Dict[str, Any]] = []
    layout: Dict[str, Any] = {
        "margin": {"l": 64, "r": 24 if not continuous else 90, "t": 36 if n > 1 else 16, "b": 56},
        "plot_bgcolor": th["bg"], "paper_bgcolor": th["bg"],
        "font": {"family": "Segoe UI, Inter, sans-serif", "size": 12, "color": th["fg"]},
        "legend": {"orientation": "h", "y": -0.18 if n == 1 else -0.08},
        "hovermode": "closest", "showlegend": bool(colour) or chart == "trend", "annotations": [],
        "barmode": "overlay" if chart == "hist" else "group",
        "boxmode": "group", "violinmode": "group", "bargap": 0.15 if chart == "bar" else 0.04,
    }
    x_title = fy.label if chart == "hist" else fx.label
    y_title = "Trials" if chart == "hist" else fy.label
    seen_legend = set()
    for i, pan in enumerate(panels):
        r, c = divmod(i, cols)
        sx = "" if i == 0 else str(i + 1)
        x0 = c * (w + gap_x)
        y1 = 1 - r * (h + gap_y)
        xa = {"domain": [x0, x0 + w], "anchor": f"y{sx}", "gridcolor": th["grid"], "zeroline": False,
              "linecolor": th["axis"], "title": {"text": x_title} if r == rows - 1 else None}
        if x_cats is not None:
            xa.update({"type": "category", "categoryorder": "array", "categoryarray": x_cats})
        elif logx and chart != "hist":
            xa["type"] = "log"
        ya = {"domain": [y1 - h, y1], "anchor": f"x{sx}", "gridcolor": th["grid"], "zeroline": False,
              "linecolor": th["axis"], "title": {"text": y_title} if c == 0 else None}
        if logy and chart != "hist":
            ya["type"] = "log"
        if i:
            xa["matches"], ya["matches"] = "x", "y"
        layout[f"xaxis{sx}"], layout[f"yaxis{sx}"] = xa, ya
        if split:
            layout["annotations"].append({
                "text": f"<b>{pan}</b>", "xref": "paper", "yref": "paper", "x": x0, "y": y1,
                "xanchor": "left", "yanchor": "bottom", "showarrow": False, "font": {"size": 13}})
        in_panel = [p for p in pts if not split or p["split"] == pan]

        if chart == "density":
            if in_panel:
                traces.append(_density(in_panel, sx, pal["scale"], i == 0, th, fx, fy))
            continue
        if continuous:
            if in_panel:
                traces.append(_points_continuous(in_panel, sx, pal["scale"], i == 0, size, fx, fy, fc, th))
                if chart == "trend":
                    t = _trend(in_panel, sx, "All trials", th["fg"], i == 0, logx)
                    if t:
                        traces.append(t)
            continue
        for col in colour_list:
            sel = [p for p in in_panel if not colour or p["colour"] == col]
            if not sel:
                continue
            show = bool(colour) and col not in seen_legend
            seen_legend.add(col)
            hexc = colour_of.get(col, pal["colours"][0])
            base = {"xaxis": f"x{sx}", "yaxis": f"y{sx}", "name": col or fy.title, "legendgroup": col,
                    "showlegend": show}
            if chart in ("points", "trend"):
                traces.append(_points(sel, base, hexc, symbol_of.get(col, "circle"), size, fx, fy, col, th))
                if chart == "trend":
                    t = _trend(sel, sx, col or "All trials", hexc, show or not colour and i == 0, logx, group=col)
                    if t:
                        traces.append(t)
            elif chart == "line":
                traces.append(_mean_trace(sel, base, hexc, fx.kind == "cat", fx, fy, symbol_of.get(col, "square")))
            elif chart == "bar":
                traces.append(_bar_trace(sel, base, hexc, fx, fy))
            elif chart in ("box", "violin"):
                traces.append(_dist_trace(chart, sel, base, hexc))
            elif chart == "hist":
                traces.append({**base, "type": "histogram", "x": [p["y"] for p in sel],
                               "marker": {"color": hexc, "line": {"color": th["bg"], "width": 0.5}},
                               "opacity": 0.65 if colour else 0.9, "nbinsx": 30,
                               "hovertemplate": f"{fy.title}: %{{x}}<br>Trials: %{{y}}<extra>{col}</extra>"})
    info = {"plotted": len(pts), "hidden_panels": hidden, "x_is_cat": x_is_cat, "chart": chart,
            "colour_groups": [(c, colour_of[c]) for c in colour_list if c] if not continuous else [],
            "colour_defaults": {c: defaults[c] for c in colour_list if c},
            "continuous": continuous}
    return {"data": traces, "layout": layout}, pts, info


def _hover(p, fx, fy, col) -> str:
    return (f"<b>{p['trial']}</b> · {p['series']}<br>{p['yarn']}<br>{fx.title}: {_fmt(p['x'])}"
            f"<br>{fy.title}: {_fmt(p['y'])}" + (f"<br>{col}" if col else ""))


def _points(sel, base, hexc, symbol, size, fx, fy, col, th) -> Dict[str, Any]:
    return {**base, "type": "scatter", "mode": "markers",
            "x": [p["x"] for p in sel], "y": [p["y"] for p in sel], "customdata": [p["tid"] for p in sel],
            "marker": {"color": hexc, "size": size, "opacity": 0.85, "symbol": symbol,
                       "line": {"color": th["bg"], "width": 1}},
            "hovertext": [_hover(p, fx, fy, col) for p in sel], "hoverinfo": "text"}


def _points_continuous(sel, sx, scale, first, size, fx, fy, fc, th) -> Dict[str, Any]:
    sel = sorted(sel, key=lambda p: (p["colour"] is None, p["colour"] or 0))
    vals = [p["colour"] for p in sel]
    return {"xaxis": f"x{sx}", "yaxis": f"y{sx}", "type": "scatter", "mode": "markers", "showlegend": False,
            "name": fc.title, "x": [p["x"] for p in sel], "y": [p["y"] for p in sel],
            "customdata": [p["tid"] for p in sel],
            "marker": {"color": [v if v is not None else float("nan") for v in vals], "colorscale": scale,
                       "size": size, "opacity": 0.9, "line": {"color": th["bg"], "width": 0.5},
                       "showscale": first, "colorbar": {"title": {"text": fc.label}, "thickness": 14},
                       "cmin": min((v for v in vals if v is not None), default=0),
                       "cmax": max((v for v in vals if v is not None), default=1)},
            "hovertext": [_hover(p, fx, fy, f"{fc.title}: {_fmt(p['colour'])}") for p in sel], "hoverinfo": "text"}


def _trend(sel, sx, name, hexc, show, logx, group=None) -> Optional[Dict[str, Any]]:
    xs = [p["x"] for p in sel if isinstance(p["x"], (int, float))]
    ys = [p["y"] for p in sel if isinstance(p["x"], (int, float))]
    if logx:
        pairs = [(math.log10(a), b) for a, b in zip(xs, ys) if a > 0]
        xs, ys = [a for a, _ in pairs], [b for _, b in pairs]
    fit = linear_fit(xs, ys)
    if fit is None:
        return None
    slope, icpt, r2 = fit
    lo, hi = min(xs), max(xs)
    line_x = [lo, hi] if not logx else [10 ** lo, 10 ** hi]
    return {"xaxis": f"x{sx}", "yaxis": f"y{sx}", "type": "scatter", "mode": "lines",
            "x": line_x, "y": [slope * lo + icpt, slope * hi + icpt],
            "line": {"color": hexc, "width": 2.5, "dash": "dash"}, "legendgroup": group,
            "name": f"Trend {name}: R² {r2:.2f}", "showlegend": show,
            "hovertemplate": f"Trend {name}<br>slope {slope:.4g}<br>R² {r2:.3f}<extra></extra>"}


def _density(sel, sx, scale, first, th, fx, fy) -> Dict[str, Any]:
    return {"xaxis": f"x{sx}", "yaxis": f"y{sx}", "type": "histogram2dcontour", "showlegend": False,
            "x": [p["x"] for p in sel], "y": [p["y"] for p in sel], "colorscale": scale,
            "reversescale": scale in ("Greens", "Blues", "Greys"), "ncontours": 14, "showscale": first,
            "contours": {"coloring": "heatmap", "showlines": False},
            "colorbar": {"title": {"text": "Trials"}, "thickness": 14},
            "hovertemplate": f"{fx.title}: %{{x}}<br>{fy.title}: %{{y}}<br>Trials: %{{z}}<extra></extra>"}


def _groups(sel, key="xlab"):
    groups: Dict[Any, List[float]] = {}
    for p in sel:
        groups.setdefault(p[key], []).append(p["y"])
    return groups


def _mean_trace(sel, base, hexc, x_is_cat, fx, fy, symbol) -> Dict[str, Any]:
    groups = _groups(sel, "x")
    xs = sorted(groups, key=_sort_key if x_is_cat else (lambda v: v))
    st = [_stats(groups[xv]) for xv in xs]
    return {
        **base, "type": "scatter", "mode": "markers" if x_is_cat else "lines+markers",
        "x": xs, "y": [m for m, _ in st],
        "error_y": {"type": "data", "array": [sd for _, sd in st], "visible": True, "color": hexc,
                    "thickness": 1.5, "width": 6},
        "marker": {"color": hexc, "size": 10, "symbol": symbol if symbol != "circle" else "square"},
        "line": {"color": hexc, "width": 2},
        "hovertext": [f"{fx.title}: {_fmt(xv)}<br>Mean {fy.title}: {_fmt(m)}<br>SD {_fmt(sd)} · n={len(groups[xv])}"
                      for xv, (m, sd) in zip(xs, st)],
        "hoverinfo": "text",
    }


def _bar_trace(sel, base, hexc, fx, fy) -> Dict[str, Any]:
    groups = _groups(sel)
    xs = sorted(groups, key=_sort_key)
    st = [_stats(groups[xv]) for xv in xs]
    return {**base, "type": "bar", "x": xs, "y": [m for m, _ in st],
            "error_y": {"type": "data", "array": [sd for _, sd in st], "visible": True, "thickness": 1.5,
                        "width": 5, "color": "rgba(0,0,0,0.55)"},
            "marker": {"color": hexc, "line": {"color": "rgba(0,0,0,0.15)", "width": 1}},
            "hovertext": [f"{fx.title}: {xv}<br>Mean {fy.title}: {_fmt(m)}<br>SD {_fmt(sd)} · n={len(groups[xv])}"
                          for xv, (m, sd) in zip(xs, st)],
            "hoverinfo": "text"}


def _dist_trace(kind, sel, base, hexc) -> Dict[str, Any]:
    t = {**base, "type": kind, "x": [p["xlab"] for p in sel], "y": [p["y"] for p in sel],
         "marker": {"color": hexc, "size": 4, "opacity": 0.6}, "line": {"color": hexc},
         "customdata": [p["tid"] for p in sel]}
    if kind == "box":
        t.update({"boxmean": True, "boxpoints": "outliers", "fillcolor": _alpha(hexc, 0.35)})
    else:
        t.update({"box": {"visible": True}, "meanline": {"visible": True}, "points": False,
                  "fillcolor": _alpha(hexc, 0.35), "spanmode": "hard", "scalemode": "width"})
    return t


def _alpha(hexc: str, a: float) -> str:
    h = hexc.lstrip("#")
    if len(h) != 6:
        return hexc
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"
