# db/fairness.py
"""Smart Chart "fairness check" (Nutzerwunsch 2026-10-30): warns when a chart
compares groups that differ in OTHER conditions that also affect Y - the
chart may then show the effect of those conditions instead of the grouping.

What is compared: the colours (Colour by, list field), else the panels
(Split by), else the X categories (box/bar/violin or a list field on X),
else - for a number X - the X range cut into 5 bands.

Per condition (material, end titer, filaments, yarn type, machine, jet, air
pressure, overfeed, speed):
- imbalance (0..1): how differently it is spread over the groups - largest
  difference in shares between two groups (list fields), or the distance of
  the group means in standard deviations (numbers); small differences
  (NUM_TOLERANCE / CAT_TOLERANCE) count as normal scatter
- influence (0..1): how much Y depends on it WITHIN the groups (eta², so the
  grouping itself does not count), / 0.25
- score = imbalance x influence; the worst condition sets the light
  (red >= RED, amber >= AMBER).
Extra warnings (at least amber): a group with very few trials, a group that
comes almost entirely from one trial series of its own, groups that do not
share an X range (trend/mean lines compare different things).

A warning light, not a proof: only conditions recorded in TrippleT are checked.
Pure Python (tests/test_fairness.py).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

CONDITIONS = ["yarn_material", "yarn_endtiter", "yarn_filaments", "yarn_type", "machine", "jet",
              "air_pressure", "overfeed", "speed"]
RED, AMBER = 0.30, 0.12
MIN_GROUP = 5          # groups smaller than this are only reported, not compared
SMALL_GROUP = 5
DOMINANT_SHARE = 0.8
X_BANDS = 5
# differences smaller than this are normal scatter, not imbalance
NUM_TOLERANCE = 0.25    # standard deviations between group means
CAT_TOLERANCE = 0.10    # difference in shares (10 percentage points)

GREEN, YELLOW, REDL, NONE = "green", "amber", "red", "none"
_ORDER = {NONE: 0, GREEN: 1, YELLOW: 2, REDL: 3}


@dataclass
class Condition:
    key: str
    title: str
    unit: str
    kind: str
    imbalance: float
    influence: float
    score: float
    per_group: Dict[str, str]          # group -> "82 % PES" / "mean 3.4 bar"

    @property
    def level(self) -> str:
        return REDL if self.score >= RED else (YELLOW if self.score >= AMBER else GREEN)


@dataclass
class Assessment:
    level: str                          # none / green / amber / red
    headline: str
    sentence: str
    grouping: str                       # "Colour by Jet series" …
    groups: List[Tuple[str, int]]
    conditions: List[Condition] = field(default_factory=list)
    warnings: List[Tuple[str, str]] = field(default_factory=list)   # (level, text)
    fix: Optional[Dict[str, Any]] = None                            # filter for "Make it fairer"
    fix_text: str = ""


HEADLINES = {GREEN: "Comparison looks fair", YELLOW: "Comparison partly fair", REDL: "Comparison questionable",
             NONE: ""}


# ── small statistics ─────────────────────────────────────────────────────
def _num(v) -> Optional[float]:
    if v is None or isinstance(v, bool):
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def _mean_sd(xs: Sequence[float]) -> Tuple[float, float]:
    m = sum(xs) / len(xs)
    sd = math.sqrt(sum((a - m) ** 2 for a in xs) / (len(xs) - 1)) if len(xs) > 1 else 0.0
    return m, sd


def quantile_bands(xs: Sequence[float], n: int = X_BANDS) -> List[float]:
    """Inner cut points for n bands with about equally many values."""
    s = sorted(xs)
    if not s:
        return []
    cuts = sorted({s[min(len(s) - 1, int(len(s) * i / n))] for i in range(1, n)})
    return [c for c in cuts if c > s[0]]


def band_of(x: float, cuts: Sequence[float]) -> int:
    for i, c in enumerate(cuts):
        if x < c:
            return i
    return len(cuts)


def eta2(pairs: Sequence[Tuple[Any, float]], min_level: int = 3) -> Optional[float]:
    """Share of the variance of y explained by the level (correlation ratio)."""
    by: Dict[Any, List[float]] = {}
    for lev, y in pairs:
        by.setdefault(lev, []).append(y)
    by = {k: v for k, v in by.items() if len(v) >= min_level}
    ys = [y for v in by.values() for y in v]
    if len(by) < 2 or len(ys) < 6:
        return None
    gm = sum(ys) / len(ys)
    ss_tot = sum((y - gm) ** 2 for y in ys)
    if ss_tot <= 0:
        return 0.0
    ss_b = sum(len(v) * ((sum(v) / len(v)) - gm) ** 2 for v in by.values())
    return max(0.0, min(1.0, ss_b / ss_tot))


def _fmt(x: float) -> str:
    """Readable rounding: 3.42 · 47.5 · 121 · 1050."""
    ax = abs(x)
    if ax >= 100:
        return f"{x:.0f}"
    s = f"{x:.1f}" if ax >= 10 else f"{x:.2f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


# ── assessment ───────────────────────────────────────────────────────────
def assess(points: List[Dict[str, Any]], group_of: Callable[[Dict[str, Any]], Optional[str]],
           cond_value: Callable[[str, Dict[str, Any]], Any], fields: Dict[str, Any],
           grouping_label: str, skip: Sequence[str] = (), x_ranges: bool = False,
           y_title: str = "Y") -> Assessment:
    """points: plotted rows (need "y", "series", "series_id", and "x" if
    x_ranges); group_of(point) -> group label or None (left out);
    cond_value(key, point) -> value of a condition for that point."""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for p in points:
        g = group_of(p)
        if g is not None:
            groups.setdefault(g, []).append(p)
    sizes = sorted(((g, len(v)) for g, v in groups.items()), key=lambda gv: -gv[1])
    if len(groups) < 2:
        return Assessment(NONE, "", "", grouping_label, sizes)
    big = {g: v for g, v in groups.items() if len(v) >= MIN_GROUP}

    conds: List[Condition] = []
    for key in CONDITIONS:
        f = fields.get(key)
        if f is None or key in skip:
            continue
        c = _condition(key, f, big, cond_value)
        if c is not None:
            conds.append(c)
    conds.sort(key=lambda c: -c.score)

    warnings: List[Tuple[str, str]] = []
    for g, n in sizes:
        if n < SMALL_GROUP:
            warnings.append((YELLOW, f"“{g}” has only {n} trial{'s' if n != 1 else ''} - too few to compare."))
    warnings += _dominance(big)
    if x_ranges:
        warnings += _x_overlap(big)

    level = max([c.level for c in conds] + [w for w, _ in warnings] + [GREEN], key=lambda l: _ORDER[l])
    bad = [c for c in conds if c.level in (REDL, YELLOW)]
    if bad:
        names = " and ".join(c.title for c in bad[:2]) + (" (and more)" if len(bad) > 2 else "")
        what = "conditions that also affect" if len(bad) > 1 else "a condition that also affects"
        sentence = f"The groups differ in {names} - {what} {y_title}. "
        top = bad[0]
        gs = [g for g, _ in sizes if g in top.per_group][:2]
        sentence += " · ".join(f"{g}: {top.per_group[g]}" for g in gs) + "."
    elif warnings:
        sentence = warnings[0][1]
    else:
        sentence = (f"No large differences found between the groups in the recorded conditions "
                    f"({', '.join(c.title for c in conds[:4])}{'…' if len(conds) > 4 else ''}).")
    # first condition (worst first) for which a common part exists
    fix, fix_text = None, ""
    for c in bad:
        f_, t_ = _fix(c, big, cond_value)
        if f_ is not None:
            fix, fix_text = f_, t_
            break
        fix_text = fix_text or t_
    return Assessment(level, HEADLINES[level], sentence, grouping_label, sizes, conds, warnings, fix, fix_text)


def _condition(key, f, groups, cond_value) -> Optional[Condition]:
    vals = {g: [(cond_value(key, p), p["y"]) for p in pts] for g, pts in groups.items()}
    if f.kind == "num":
        vals = {g: [(_num(v), y) for v, y in lst] for g, lst in vals.items()}
        vals = {g: [(v, y) for v, y in lst if v is not None] for g, lst in vals.items()}
        vals = {g: lst for g, lst in vals.items() if len(lst) >= max(MIN_GROUP, len(groups[g]) * 0.5)}
        if len(vals) < 2:
            return None
        allx = [v for lst in vals.values() for v, _ in lst]
        _m, sd = _mean_sd(allx)
        means = {g: _mean_sd([v for v, _ in lst])[0] for g, lst in vals.items()}
        if sd <= 0:
            return None
        smd = (max(means.values()) - min(means.values())) / sd
        imb = min(1.0, max(0.0, smd - NUM_TOLERANCE) / 1.25)
        cuts = quantile_bands(allx)
        level_of = lambda v: band_of(v, cuts)
        unit = f" {f.unit}" if f.unit else ""
        per = {g: f"mean {_fmt(means[g])}{unit}" for g in vals}
    else:
        vals = {g: [(("" if v is None else str(v).strip()) or "(none)", y) for v, y in lst]
                for g, lst in vals.items()}
        cats: Dict[str, int] = {}
        for lst in vals.values():
            for v, _ in lst:
                cats[v] = cats.get(v, 0) + 1
        if len(cats) < 2:
            return None
        top = [c for c, _ in sorted(cats.items(), key=lambda kv: -kv[1])][:6]
        norm = lambda v: v if v in top else "other"
        shares = {}
        for g, lst in vals.items():
            cnt: Dict[str, int] = {}
            for v, _ in lst:
                cnt[norm(v)] = cnt.get(norm(v), 0) + 1
            shares[g] = {k: c / len(lst) for k, c in cnt.items()}
        keys = set(k for s in shares.values() for k in s)
        gl = list(shares)
        imb = 0.0
        for i in range(len(gl)):
            for j in range(i + 1, len(gl)):
                a, b = shares[gl[i]], shares[gl[j]]
                imb = max(imb, 0.5 * sum(abs(a.get(k, 0) - b.get(k, 0)) for k in keys))
        imb = max(0.0, imb - CAT_TOLERANCE) / (1 - CAT_TOLERANCE)
        level_of = norm
        per = {}
        for g, s in shares.items():
            named = {k: v for k, v in s.items() if k != "other"} or s
            k, share = max(named.items(), key=lambda kv: kv[1])
            per[g] = f"{share * 100:.0f} % {k}"
    # influence of the condition on Y within the groups
    effs, weights = [], []
    for g, lst in vals.items():
        e = eta2([(level_of(v), y) for v, y in lst])
        if e is not None and len(lst) >= 10:
            effs.append(e)
            weights.append(len(lst))
    if effs:
        infl_raw = sum(e * w for e, w in zip(effs, weights)) / sum(weights)
    else:
        e = eta2([(level_of(v), y) for lst in vals.values() for v, y in lst])
        infl_raw = (e or 0.0) * 0.5      # can't separate it from the grouping -> count half
    infl = min(1.0, infl_raw / 0.25)
    return Condition(key, f.title, f.unit, f.kind, round(imb, 3), round(infl, 3), round(imb * infl, 3), per)


def _dominance(groups) -> List[Tuple[str, str]]:
    out = []
    shares = {}
    for g, pts in groups.items():
        cnt: Dict[Any, int] = {}
        for p in pts:
            cnt[p.get("series_id")] = cnt.get(p.get("series_id"), 0) + 1
        sid, n = max(cnt.items(), key=lambda kv: kv[1])
        shares[g] = (sid, n / len(pts), next((p["series"] for p in pts if p.get("series_id") == sid), ""))
    for g, (sid, share, label) in shares.items():
        if share < DOMINANT_SHARE:
            continue
        elsewhere = [h for h, pts in groups.items() if h != g and
                     sum(1 for p in pts if p.get("series_id") == sid) / len(pts) >= 0.2]
        if not elsewhere:
            out.append((YELLOW, f"{share * 100:.0f} % of “{g}” come from one trial series ({label}) - "
                                f"that is one experiment rather than a general result."))
    return out


def _x_overlap(groups) -> List[Tuple[str, str]]:
    rng = {}
    for g, pts in groups.items():
        xs = sorted(x for x in (_num(p.get("x")) for p in pts) if x is not None)
        if len(xs) >= MIN_GROUP:
            rng[g] = (xs[int(len(xs) * 0.1)], xs[min(len(xs) - 1, int(len(xs) * 0.9))])
    if len(rng) < 2:
        return []
    lo, hi = max(a for a, _ in rng.values()), min(b for _, b in rng.values())
    span = max(b for _, b in rng.values()) - min(a for a, _ in rng.values())
    if span <= 0 or (hi - lo) / span >= 0.3:
        return []
    parts = " · ".join(f"{g}: {_fmt(a)}–{_fmt(b)}" for g, (a, b) in list(rng.items())[:3])
    return [(YELLOW, f"The groups cover different X ranges ({parts}) - their lines do not compare the same thing.")]


def _fix(c: Condition, groups, cond_value) -> Tuple[Optional[Dict[str, Any]], str]:
    """Filter that keeps only what all groups have in common for condition c."""
    if c.kind == "num":
        bounds = []
        for pts in groups.values():
            xs = sorted(x for x in (_num(cond_value(c.key, p)) for p in pts) if x is not None)
            if len(xs) >= MIN_GROUP:
                bounds.append((xs[int(len(xs) * 0.1)], xs[min(len(xs) - 1, int(len(xs) * 0.9))]))
        if len(bounds) < 2:
            return None, ""
        lo, hi = max(a for a, _ in bounds), min(b for _, b in bounds)
        if lo > hi:
            return None, f"There is no common {c.title} range - these groups were not tested under the same conditions."
        unit = f" {c.unit}" if c.unit else ""
        rng = _fmt(lo) if _fmt(lo) == _fmt(hi) else f"{_fmt(lo)} – {_fmt(hi)}"
        return {"key": c.key, "min": lo, "max": hi}, f"Keep only {c.title} {rng}{unit} (the range all groups share)"
    common = None
    for pts in groups.values():
        cnt: Dict[str, int] = {}
        for p in pts:
            v = cond_value(c.key, p)
            v = ("" if v is None else str(v).strip()) or "(none)"
            cnt[v] = cnt.get(v, 0) + 1
        ok = {v for v, n in cnt.items() if n >= 3}
        common = ok if common is None else common & ok
    if not common:
        return None, f"No {c.title} value occurs in all groups - these groups were not tested under the same conditions."
    vals = sorted(common)
    return {"key": c.key, "values": vals}, f"Keep only {c.title}: {', '.join(vals[:4])}{'…' if len(vals) > 4 else ''} (found in all groups)"


# ── glue for the Smart Chart (chart mode and dashboard visuals) ──────────
def chart_grouping(fields, s, rows, info):
    """(label, group_of, group key, x_ranges) of what a chart compares, or
    None. s: settings with x, y, colour, split (keys, "" for none)."""
    chart = info.get("chart")
    if s.get("colour") and not info.get("continuous") and chart != "density":
        return (f"Colour by {fields[s['colour']].title}",
                lambda p: None if p["colour"] in ("Other", "") else p["colour"], s["colour"],
                chart in ("points", "trend", "line") and fields[s["x"]].kind == "num")
    if s.get("split"):
        return (f"Split by {fields[s['split']].title}", lambda p: p["split"] or None, s["split"],
                chart in ("points", "trend", "line") and fields[s["x"]].kind == "num")
    if chart != "hist" and info.get("x_is_cat"):
        return (f"X axis {fields[s['x']].title}", lambda p: str(p.get("xlab", p["x"])), s["x"], False)
    if chart not in ("hist", "density") and fields[s["x"]].kind == "num" and rows:
        xs = [p["x"] for p in rows]
        cuts = quantile_bands(xs)
        edges = [min(xs)] + cuts + [max(xs)]
        fx = fields[s["x"]]
        unit = f" {fx.unit}" if fx.unit else ""
        labels = [f"{fx.title} {_fmt(edges[i])}–{_fmt(edges[i + 1])}{unit}" for i in range(len(edges) - 1)]
        return (f"along the X axis ({fx.title} in {len(labels)} bands)",
                lambda p: labels[min(len(labels) - 1, band_of(p["x"], cuts))], s["x"], False)
    return None


def assess_chart(ds, res, rows, info, s, filters) -> Optional[Assessment]:
    """Fairness of one Smart Chart chart; None if nothing is compared or the
    check fails (it must never break a chart)."""
    try:
        g = chart_grouping(ds.fields, s, rows, info) if rows else None
        if g is None:
            return None
        label, group_of, gkey, x_ranges = g
        skip = {s.get("x"), s.get("colour"), s.get("split"), gkey}
        skip |= {flt["key"] for flt in filters if len(flt.get("values") or []) == 1 or flt.get("only")}
        if ds.fields[gkey].group == "Jet":
            skip.add("jet")
        cond_value = lambda key, p: ds.value(key, p["tid"], res.matched.get(p["tid"]))
        return assess(rows, group_of, cond_value, ds.fields, label, skip=[k for k in skip if k],
                      x_ranges=x_ranges, y_title=ds.fields[s["y"]].title)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("fairness: %s", e)
        return None
