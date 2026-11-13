"""DTY "what if" analysis (Process Playground, ui/screen_process_playground.py):
what happens to the lab values when air pressure, overfeed or speed change -
for one yarn / jet combination, from our own trials.

Answers in directions (more / less / about the same) with a significance
statement, not with point predictions (Nutzerwunsch 2026-11-12: "ob es mehr,
weniger oder etwa gleich viele bleiben und ob es signifikant ist").

Method per (yarn, jet) combination and target value:
  - replicate trials (same series + same settings, e.g. 3 platelets) are
    averaged first, every setting counts once (not weighted by the number of
    platelets: spool / day scatter hits a setting once, however many
    platelets ran) - otherwise replicates would pretend more information;
  - least squares  y ~ pressure + OF + speed (+ squares) + series, the
    series as a fixed effect (removes spool / lab day / campaign differences,
    so an effect has to show up WITHIN series to count);
  - a parameter is only in the model if it varies within at least one
    series and has >= MIN_LEVELS different values; its square only if it has
    >= 4 levels and the curvature is significant (effects are often not
    linear: points/m level off at high pressure);
  - a change start -> new setting is a contrast of the fitted model (the
    series terms cancel), with t-test and 95 % CI;
  - "about the same" = equivalence: the 90 % CI lies within +/- margin,
    margin = EQUIV_FACTOR x repeatability SD of that target (pooled over the
    replicate groups of all combinations), i.e. smaller than what repeating
    the same trial changes anyway;
  - the residual variance is never taken below the repeatability variance
    of a condition mean (with few degrees of freedom it is often
    underestimated by chance - permutation check 2026-11-12 on dev_local:
    shuffled settings give < 1 % "clear" and ~2 % "probable").

Pure logic, no Qt - reads only (fetch_all), never writes.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy import stats

# parameter key -> (label, step for the per-step summary, unit, spin box step, decimals)
PARAMS: Dict[str, Tuple[str, float, str, float, int]] = {
    "pressure": ("Air pressure", 0.5, "bar", 0.1, 1),
    "of": ("Overfeed", 1.0, "%", 0.5, 1),
    "speed": ("Speed", 100.0, "m/min", 50.0, 0),
}

# target key -> (label, unit, decimals)
TARGETS: Dict[str, Tuple[str, str, int]] = {
    "fpm": ("Intermingling points/m", "1/m", 1),
    "fpm_cv": ("CV points/m", "%", 1),
    "stab03": ("Stability 0.3", "%", 1),
    "stab06": ("Stability 0.6", "%", 1),
    "stab10": ("Stability 1.0", "%", 1),
    "stab13": ("Stability 1.3", "%", 1),
    "t_before": ("Tension before jet", "cN", 2),
    "t_after": ("Tension after jet", "cN", 2),
}

LAB_TARGETS = ("fpm", "fpm_cv", "stab03", "stab06", "stab10", "stab13")   # Itemat

# stability is a percentage - values above this are typing errors (8186.1 seen)
STAB_MAX = 110.0

MIN_DOF = 3             # residual degrees of freedom a fit needs
MIN_LEVELS = 3          # distinct values a parameter needs to be judged
EQUIV_FACTOR = 0.5      # "about the same" margin = factor x repeatability SD
FAR_DISTANCE = 0.25     # new setting further than this (share of the measured
#                         range) from every measured setting = "never run"

# verdict codes, strongest first
CLEAR, PROBABLE, TENDENCY, SAME, NO_CLEAR, UNCLEAR, NOT_VARIED, NO_DATA, OUTSIDE, NO_CHANGE = (
    "clear", "probable", "tendency", "same", "no_clear", "unclear", "not_varied", "no_data",
    "outside", "no_change")
SIGNIFICANT = (CLEAR, PROBABLE, TENDENCY)


_SQL = """
SELECT
    t.ID AS trial_id, t.Versuchsnummer AS trial_no, t.TrialSeriesID AS series_id,
    ts.SeriesName AS series_name, t.JetID AS jet_id, j.Jet AS jet_name,
    t.AirPressure AS pressure, t.Shaft2x_OF AS `of`, t.SpeedShaft2 AS speed,
    t.YarnTensionBeforeJet AS t_before, t.YarnTensionAfterJet AS t_after,
    yk.yarn_key, yk.yarn_name,
    fpm.fpm, fpm.fpm_cv, stab.stab03, stab.stab06, stab.stab10, stab.stab13
FROM tbltrial t
JOIN tbltrialseries ts    ON ts.ID = t.TrialSeriesID
JOIN tblmaschine m        ON m.ID = ts.MachineID
JOIN tblmaschinentypen mt ON mt.ID = m.Maschinentyp
JOIN tbljets j            ON j.ID = t.JetID
JOIN (
    SELECT s.TrialID,
           GROUP_CONCAT(DISTINCT s.YarnID ORDER BY s.YarnID SEPARATOR '+') AS yarn_key,
           GROUP_CONCAT(DISTINCT COALESCE(NULLIF(y.Kurzname, ''), y.Name)
                        ORDER BY s.YarnID SEPARATOR ' + ') AS yarn_name
    FROM tbltrialsettings s
    LEFT JOIN tblyarn y ON y.ID = s.YarnID
    WHERE s.YarnID IS NOT NULL
    GROUP BY s.TrialID
) yk ON yk.TrialID = t.ID
LEFT JOIN (
    SELECT TrialID, AVG(FPm) AS fpm, AVG(FPmCV) AS fpm_cv
    FROM tbllaboritematlab WHERE Tension = 0.0 GROUP BY TrialID
) fpm ON fpm.TrialID = t.ID
LEFT JOIN (
    SELECT TrialID,
        AVG(CASE WHEN Tension = 0.3 THEN Stability END) AS stab03,
        AVG(CASE WHEN Tension = 0.6 THEN Stability END) AS stab06,
        AVG(CASE WHEN Tension = 1.0 THEN Stability END) AS stab10,
        AVG(CASE WHEN Tension = 1.3 THEN Stability END) AS stab13
    FROM tbllaboritematlab WHERE Tension IN (0.3, 0.6, 1.0, 1.3) GROUP BY TrialID
) stab ON stab.TrialID = t.ID
WHERE mt.Maschinentyp IN ('DTY', 'DT/DW')
  AND t.JetID IS NOT NULL
  AND {ref_filter}
"""


def _num(v) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if np.isfinite(f) else None


def clean_rows(rows: Sequence[dict]) -> List[dict]:
    """Numbers as float/None; zero tensions = not measured; impossible
    stabilities (typing errors) dropped."""
    out = []
    for r in rows:
        d = {str(k).lower(): r[k] for k in r}
        for k in list(PARAMS) + list(TARGETS):
            d[k] = _num(d.get(k))
        for k in ("t_before", "t_after"):
            if d[k] == 0:
                d[k] = None
        for k in ("stab03", "stab06", "stab10", "stab13"):
            if d[k] is not None and not 0 <= d[k] <= STAB_MAX:
                d[k] = None
        out.append(d)
    return out


def load_rows() -> List[dict]:
    """One dict per DTY trial: jet, yarn key (all plies), settings, targets."""
    from db.connection import fetch_all
    from db.trial_reference import exclude_references_sql
    return clean_rows(fetch_all(_SQL.replace("{ref_filter}", exclude_references_sql("t")), []))


# ── data set ────────────────────────────────────────────────────────────────

@dataclass
class Combination:
    key: Tuple[str, object]          # (yarn_key, jet_id)
    yarn_name: str
    jet_name: str
    rows: List[dict]
    n_trials: int
    n_series: int
    n_settings: int
    varied: List[str]                # parameters that can be judged at all
    n_lab_settings: int = 0          # settings with Itemat values (list order)


@dataclass
class DataSet:
    rows: List[dict]
    margins: Dict[str, Optional[float]]           # repeatability SD per target
    combos: Dict[Tuple[str, object], Combination] = field(default_factory=dict)


def judgeable_params(rows: Sequence[dict]) -> List[str]:
    """Parameters with >= MIN_LEVELS values that vary within a series."""
    out = []
    for p in PARAMS:
        vals = {r[p] for r in rows if r.get(p) is not None}
        by_series: Dict[object, set] = defaultdict(set)
        for r in rows:
            if r.get(p) is not None:
                by_series[r["series_id"]].add(r[p])
        if len(vals) >= MIN_LEVELS and any(len(v) >= 2 for v in by_series.values()):
            out.append(p)
    return out


def build_dataset(rows: Sequence[dict]) -> DataSet:
    rows = list(rows)
    ds = DataSet(rows, {t: repeatability_sd(rows, t) for t in TARGETS})
    groups: Dict[Tuple[str, object], List[dict]] = defaultdict(list)
    for r in rows:
        # only trials with at least one lab value / tension count
        if r.get("yarn_key") and any(r.get(t) is not None for t in TARGETS):
            groups[(r["yarn_key"], r["jet_id"])].append(r)
    for key, rs in groups.items():
        varied = judgeable_params(rs)
        if not varied:
            continue
        settings = {(r["series_id"], r["pressure"], r["of"], r["speed"]) for r in rs}
        lab = {(r["series_id"], r["pressure"], r["of"], r["speed"]) for r in rs
               if any(r.get(t) is not None for t in LAB_TARGETS)}
        ds.combos[key] = Combination(
            key, str(rs[0].get("yarn_name") or "?"), str(rs[0].get("jet_name") or "?"), rs, len(rs),
            len({r["series_id"] for r in rs}), len(settings), varied, len(lab))
    return ds


def repeatability_sd(rows: Sequence[dict], target: str) -> Optional[float]:
    """Pooled SD of replicate trials (same jet, yarn, series, settings).
    The 2 % replicate groups with the largest spread are left out, so a
    single typing error cannot inflate the "about the same" margin."""
    groups: Dict[tuple, List[float]] = defaultdict(list)
    for r in rows:
        y = r.get(target)
        if y is None:
            continue
        groups[(r["jet_id"], r["yarn_key"], r["series_id"], r["pressure"], r["of"], r["speed"])].append(y)
    parts = []
    for vals in groups.values():
        if len(vals) >= 2:
            a = np.asarray(vals)
            parts.append((float(((a - a.mean()) ** 2).sum()) / (len(a) - 1), len(a) - 1))
    if not parts:
        return None
    cut = np.percentile([v for v, _d in parts], 98)
    ss = sum(v * d for v, d in parts if v <= cut)
    dof = sum(d for v, d in parts if v <= cut)
    return float(np.sqrt(ss / dof)) if dof >= 5 else None


def settings_of(rows: Sequence[dict]) -> List[dict]:
    """Distinct measured settings (series + pressure/OF/speed) for the start
    point list: {series_id, series_name, pressure, of, speed, trials: [nos]}."""
    agg: Dict[tuple, dict] = {}
    for r in rows:
        k = (r["series_id"], r["pressure"], r["of"], r["speed"])
        d = agg.setdefault(k, {"series_id": r["series_id"], "series_name": r.get("series_name") or "",
                               "pressure": r["pressure"], "of": r["of"], "speed": r["speed"], "trials": []})
        d["trials"].append(r.get("trial_no"))
    return sorted(agg.values(), key=lambda d: (str(d["series_name"]), tuple(
        (d[p] is None, d[p] or 0) for p in PARAMS)))


# ── fit ─────────────────────────────────────────────────────────────────────

def _ols(X: np.ndarray, y: np.ndarray, s2_floor: float = 0.0):
    """OLS on condition means; residual variance never below s2_floor."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    dof = len(y) - np.linalg.matrix_rank(X)
    if dof < MIN_DOF:
        return None
    resid = y - X @ beta
    s2 = max(float(resid @ resid) / dof, s2_floor)
    cov = s2 * np.linalg.pinv(X.T @ X)
    return beta, cov, dof


@dataclass
class Fit:
    target: str
    usable: List[str]                    # linear terms
    squared: List[str]                   # quadratic terms
    centre: Dict[str, float]
    beta: np.ndarray
    cov: np.ndarray
    dof: int
    margin: Optional[float]
    conds: list                          # (series, {p: v}, mean, n)
    series_effect: Dict[object, float]   # fitted series level

    def features(self, x: Dict[str, float]) -> np.ndarray:
        lin = [x[p] - self.centre[p] for p in self.usable]
        sq = [(x[p] - self.centre[p]) ** 2 for p in self.squared]
        return np.array(lin + sq, float)

    def predict_rel(self, x: Dict[str, float]) -> float:
        """Model value without the series level (only differences matter)."""
        k = len(self.usable) + len(self.squared)
        return float(self.features(x) @ self.beta[:k])

    def level(self) -> float:
        return float(np.mean(list(self.series_effect.values()))) if self.series_effect else 0.0


def _conditions(rows: Sequence[dict], target: str):
    agg: Dict[tuple, List[float]] = defaultdict(list)
    for r in rows:
        y = r.get(target)
        if y is None or any(r.get(p) is None for p in PARAMS):
            continue
        agg[(r["series_id"],) + tuple(r[p] for p in PARAMS)].append(y)
    return [(k[0], dict(zip(PARAMS, k[1:])), float(np.mean(v)), len(v)) for k, v in agg.items()]


def _usable(conds) -> List[str]:
    out = []
    for p in PARAMS:
        by_series: Dict[object, set] = defaultdict(set)
        for s, x, _y, _n in conds:
            by_series[s].add(x[p])
        if len({c[1][p] for c in conds}) >= MIN_LEVELS and any(len(v) >= 2 for v in by_series.values()):
            out.append(p)
    return out


def fit_target(rows: Sequence[dict], target: str, margin_sd: Optional[float]) -> Tuple[Optional[Fit], list, list]:
    """-> (fit or None, conditions, usable parameters)."""
    conds = _conditions(rows, target)
    usable = _usable(conds)
    if not usable or len(conds) < len(usable) + MIN_DOF:
        return None, conds, usable
    series = sorted({c[0] for c in conds}, key=str)
    s_idx = {s: i for i, s in enumerate(series)}
    y = np.array([c[2] for c in conds])
    centre = {p: float(np.mean([c[1][p] for c in conds])) for p in usable}
    n_med = float(np.median([c[3] for c in conds]))
    s2_floor = (margin_sd ** 2) / n_med if margin_sd else 0.0

    def design(squared: Sequence[str]):
        cols = [[c[1][p] - centre[p] for c in conds] for p in usable]
        cols += [[(c[1][p] - centre[p]) ** 2 for c in conds] for p in squared]
        dummies = np.zeros((len(conds), len(series)))
        for i, c in enumerate(conds):
            dummies[i, s_idx[c[0]]] = 1.0
        return np.column_stack([np.array(cols).T, dummies])

    squared = []
    for p in usable:
        if len({c[1][p] for c in conds}) < 4:
            continue
        fq = _ols(design([p]), y, s2_floor)
        if fq is None:
            continue
        bq, cq, _dq = fq
        k = len(usable)
        if cq[k, k] > 0 and 2 * stats.t.sf(abs(bq[k] / np.sqrt(cq[k, k])), _dq) < 0.05:
            squared.append(p)
    res = _ols(design(squared), y, s2_floor)
    if res is None and squared:
        squared = []
        res = _ols(design(squared), y, s2_floor)
    if res is None:
        return None, conds, usable
    beta, cov, dof = res
    k = len(usable) + len(squared)
    margin = EQUIV_FACTOR * margin_sd if margin_sd else None
    return Fit(target, usable, squared, centre, beta, cov, dof, margin, conds,
               {s: float(beta[k + i]) for s, i in s_idx.items()}), conds, usable


# ── change start -> new ─────────────────────────────────────────────────────

@dataclass
class Change:
    target: str
    verdict: str
    direction: int = 0                   # +1 more, -1 less, 0 none
    delta: Optional[float] = None
    ci: Optional[Tuple[float, float]] = None
    p: Optional[float] = None
    margin: Optional[float] = None
    start_value: Optional[float] = None  # model value at the start (series average level)
    reason: str = ""                     # why there is no statement
    series: Dict[str, Tuple[int, int]] = field(default_factory=dict)   # param -> (agree, with)
    curved: List[str] = field(default_factory=list)
    one_series: bool = False


def _series_slopes(conds, p, lo: Optional[float] = None, hi: Optional[float] = None) -> List[float]:
    """One slope of y on p per series (mean over clean one-factor comparisons
    inside the series: settings where the other parameters are equal).
    With lo/hi only the part of each comparison around that range counts
    (the measured values inside it plus the nearest one on each side) - the
    statement is local too, effects are often not linear."""
    by: Dict[tuple, List[Tuple[float, float]]] = defaultdict(list)
    for s, x, y, _n in conds:
        rest = tuple(x[q] for q in PARAMS if q != p)
        by[(s, rest)].append((x[p], y))
    per_series: Dict[object, List[float]] = defaultdict(list)
    for (s, _rest), pts in by.items():
        if lo is not None and hi is not None:
            xs_all = sorted({a for a, _b in pts})
            below = [v for v in xs_all if v <= lo]
            above = [v for v in xs_all if v >= hi]
            a = below[-1] if below else xs_all[0]
            b = above[0] if above else xs_all[-1]
            pts = [(x_, y_) for x_, y_ in pts if a <= x_ <= b]
        xs = np.array([a_ for a_, _b in pts])
        if len(set(xs)) < 2:
            continue
        ys = np.array([b_ for _a, b_ in pts])
        per_series[s].append(float(np.polyfit(xs, ys, 1)[0]))
    return [float(np.mean(v)) for v in per_series.values()]


def _start_problem(conds, usable: Sequence[str], start: Dict[str, float]) -> str:
    """Why the start conditions are outside what we measured ("" = fine).
    Varied parameters: start within the measured range. Parameters never
    varied: the start has to be one of the measured values - with another
    value nothing is known about this yarn / jet."""
    for p in PARAMS:
        v = start.get(p)
        vals = sorted({c[1][p] for c in conds})
        if v is None or not vals:
            continue
        label, _st, unit, _ss, dec = PARAMS[p]
        if p in usable:
            if not vals[0] - 1e-9 <= v <= vals[-1] + 1e-9:
                return (f"start {label.lower()} {v:.{dec}f} {unit} outside the measured range "
                        f"({vals[0]:.{dec}f}-{vals[-1]:.{dec}f})")
        elif not any(abs(v - x) <= 1e-6 for x in vals):
            only = ", ".join(f"{x:.{dec}f}" for x in vals[:4])
            return f"start {label.lower()} {v:.{dec}f} {unit} never run (only {only})"
    return ""


def start_notes(rows: Sequence[dict], start: Dict[str, float]) -> Dict[str, Tuple[bool, str]]:
    """Per parameter: (ok, short text) for the start fields of the screen,
    from all trials of the combination (the per-value check is in change())."""
    varied = set(judgeable_params(rows))
    out = {}
    for p in PARAMS:
        label, _st, unit, _ss, dec = PARAMS[p]
        vals = sorted({r[p] for r in rows if r.get(p) is not None})
        v = start.get(p)
        if not vals:
            out[p] = (False, "never recorded")
        elif p in varied:
            ok = v is not None and vals[0] - 1e-9 <= v <= vals[-1] + 1e-9
            out[p] = (ok, f"measured {vals[0]:.{dec}f} to {vals[-1]:.{dec}f} {unit}")
        else:
            ok = v is not None and any(abs(v - x) <= 1e-6 for x in vals)
            out[p] = (ok, "only " + ", ".join(f"{x:.{dec}f}" for x in vals[:4]) + f" {unit} run")
    return out


def _fit_cached(rows, target, margin_sd, fit_cache):
    if fit_cache is not None and target in fit_cache:
        return fit_cache[target]
    res = fit_target(rows, target, margin_sd)
    if fit_cache is not None:
        fit_cache[target] = res
    return res


def change(rows: Sequence[dict], target: str, margin_sd: Optional[float],
           start: Dict[str, float], new: Dict[str, float],
           fit_cache: Optional[dict] = None, detail: bool = True) -> Change:
    """Statement for one target when the settings go from start to new.
    detail=False skips the series counts (search over many candidates)."""
    changed = [p for p in PARAMS if start.get(p) is not None and new.get(p) is not None
               and abs(new[p] - start[p]) > 1e-9]
    fit, conds, usable = _fit_cached(rows, target, margin_sd, fit_cache)
    ch = Change(target, NO_CHANGE)
    if not conds:
        ch.verdict, ch.reason = NO_DATA, "not measured for this yarn / jet"
        return ch
    problem = _start_problem(conds, usable, start)
    if problem:
        ch.verdict, ch.reason = OUTSIDE, problem
        return ch
    if fit is not None and all(start.get(p) is not None for p in fit.usable):
        x0 = {p: start.get(p) if start.get(p) is not None else fit.centre.get(p, 0.0) for p in PARAMS}
        ch.start_value = fit.level() + fit.predict_rel(x0)
    if not changed:
        return ch
    blocked = [p for p in changed if p not in usable]
    if blocked:
        ch.verdict = NOT_VARIED
        ch.reason = " and ".join(PARAMS[p][0] for p in blocked) + " not varied for this value"
        return ch
    if fit is None:
        ch.verdict, ch.reason = UNCLEAR, "too few settings measured for this value"
        return ch
    for p in changed:
        lo = min(c[1][p] for c in conds)
        hi = max(c[1][p] for c in conds)
        if not lo - 1e-9 <= new[p] <= hi + 1e-9:
            ch.verdict = OUTSIDE
            ch.reason = f"{PARAMS[p][0]} outside the measured range ({lo:g}-{hi:g} {PARAMS[p][2]})"
            return ch
    x0 = {p: start[p] for p in PARAMS}
    x1 = dict(x0)
    x1.update({p: new[p] for p in changed})
    c = fit.features(x1) - fit.features(x0)
    k = len(c)
    est = float(c @ fit.beta[:k])
    se = float(np.sqrt(max(c @ fit.cov[:k, :k] @ c, 0.0)))
    ch.delta, ch.margin = est, fit.margin
    ch.curved = [p for p in changed if p in fit.squared]
    if detail:
        varying = set()
        for p in changed:
            by_series: Dict[object, set] = defaultdict(set)
            for s_, x, _y, _n in conds:
                by_series[s_].add(x[p])
            varying |= {s_ for s_, v in by_series.items() if len(v) >= 2}
        ch.one_series = len(varying) <= 1
        for p in changed:
            slopes = _series_slopes(conds, p, min(start[p], new[p]), max(start[p], new[p]))
            sign = np.sign(new[p] - start[p]) * np.sign(est)
            ch.series[p] = (sum(1 for s in slopes if s != 0 and np.sign(s) == sign), len(slopes))
    if se == 0 or not np.isfinite(se):
        ch.verdict, ch.reason = UNCLEAR, "no scatter estimate"
        return ch
    t975, t95 = stats.t.ppf(0.975, fit.dof), stats.t.ppf(0.95, fit.dof)
    ch.ci = (est - t975 * se, est + t975 * se)
    ch.p = float(2 * stats.t.sf(abs(est / se), fit.dof))
    m = fit.margin
    if ch.p < 0.10:
        ch.direction = 1 if est > 0 else -1
        ch.verdict = CLEAR if ch.p < 0.01 else PROBABLE if ch.p < 0.05 else TENDENCY
    elif m is not None and est - t95 * se > -m and est + t95 * se < m:
        ch.verdict = SAME
    elif m is not None and t975 * se > 2 * m:
        ch.verdict, ch.reason = UNCLEAR, "too few / too scattered data for a statement"
    else:
        ch.verdict = NO_CLEAR
    return ch


def never_run(rows: Sequence[dict], new: Dict[str, float]) -> bool:
    """True if no measured setting is close to `new` (all parameters
    together, each scaled by its measured range) - the statement then
    combines values that were only run separately."""
    ranges = {}
    for p in PARAMS:
        vals = [r[p] for r in rows if r.get(p) is not None]
        if vals:
            ranges[p] = (max(vals) - min(vals)) or 1.0
    best = None
    for r in rows:
        if any(r.get(p) is None or new.get(p) is None for p in ranges):
            continue
        d = max(abs(r[p] - new[p]) / ranges[p] for p in ranges)
        best = d if best is None else min(best, d)
    return best is not None and best > FAR_DISTANCE


def per_step(rows: Sequence[dict], target: str, margin_sd: Optional[float], param: str) -> Change:
    """Effect of one STEP of `param` around the middle of the data (summary
    and report script)."""
    fit, conds, usable = fit_target(rows, target, margin_sd)
    if not conds:
        return Change(target, NO_DATA, reason="not measured")
    if param not in usable:
        return Change(target, NOT_VARIED, reason="not varied")
    if fit is None:
        return Change(target, UNCLEAR, reason="too few settings")
    start = {p: fit.centre.get(p, conds[0][1][p]) for p in PARAMS}
    new = dict(start)
    new[param] = start[param] + PARAMS[param][1]
    return change(rows, target, margin_sd, start, new, fit_cache={target: (fit, conds, usable)})


# ── reverse: find settings for goals ────────────────────────────────────────

UP, DOWN, KEEP = "up", "down", "keep"          # goal per target
# status of one goal in a suggestion
MET, NEUTRAL, VIOLATED, UNKNOWN = "met", "neutral", "violated", "unknown"
MAX_CANDIDATES = 6000
MIN_SPREAD = 0.25        # suggestions differ by at least this share of a range


class _Region:
    """Measured settings, scaled by their range - the search only proposes
    settings close to something we really ran (see never_run)."""

    def __init__(self, rows: Sequence[dict]):
        pts = {tuple(r[p] for p in PARAMS) for r in rows if all(r.get(p) is not None for p in PARAMS)}
        self.pts = np.array(sorted(pts), float) if pts else np.zeros((0, len(PARAMS)))
        rng = self.pts.max(axis=0) - self.pts.min(axis=0) if len(self.pts) else np.ones(len(PARAMS))
        self.scale = np.where(rng > 0, rng, 1.0)

    def distance(self, x: Dict[str, float]) -> float:
        if not len(self.pts):
            return float("inf")
        v = np.array([x[p] for p in PARAMS], float)
        return float(np.min(np.max(np.abs(self.pts - v) / self.scale, axis=1)))


def goal_status(goal: str, ch: Change) -> str:
    if ch.verdict in (UNCLEAR, NOT_VARIED, NO_DATA, OUTSIDE):
        return UNKNOWN
    if goal == KEEP:
        if ch.verdict == SAME:
            return MET
        return VIOLATED if ch.verdict in SIGNIFICANT else NEUTRAL
    want = 1 if goal == UP else -1
    if ch.verdict in SIGNIFICANT:
        return MET if ch.direction == want else VIOLATED
    return NEUTRAL


@dataclass
class Suggestion:
    new: Dict[str, float]
    changes: Dict[str, Change]        # target -> statement (with series details)
    status: Dict[str, str]            # target -> MET / NEUTRAL / VIOLATED / UNKNOWN
    violations: int
    distance: float                   # to the nearest measured setting (share of range)


_STRENGTH_RANK = {CLEAR: 0, PROBABLE: 1, TENDENCY: 2}


def suggest(rows: Sequence[dict], margins: Dict[str, Optional[float]], start: Dict[str, float],
            goals: Dict[str, str], main: str, n: int = 5,
            fit_cache: Optional[dict] = None) -> Tuple[List[Suggestion], str]:
    """Settings (within what we measured, close to settings we really ran)
    that move `main` in its goal direction - with a significant statement -
    while breaking as few of the other goals as possible.
    -> (suggestions best first, message for the user; "" = fine)."""
    if goals.get(main) not in (UP, DOWN):
        return [], "Choose higher or lower for the main goal."
    fit, conds, usable = _fit_cached(rows, main, margins.get(main), fit_cache)
    if fit is None:
        return [], f"Too few trials for a statement on {TARGETS[main][0]}."
    problem = _start_problem(conds, usable, start)
    if problem:
        return [], problem[0].upper() + problem[1:] + "."
    region = _Region(rows)
    axes = []
    for p in PARAMS:
        if p in fit.usable:
            lo = min(c[1][p] for c in conds)
            hi = max(c[1][p] for c in conds)
            axes.append((p, lo, hi, PARAMS[p][3]))
    # grid: spin-box steps over the measured range (coarser if too many)
    factor = 1.0
    while True:
        grids = []
        for p, lo, hi, step in axes:
            st = step * factor
            vals = list(np.round(np.arange(lo, hi + st / 2, st), 6))
            vals.append(round(start[p], 6))
            grids.append(sorted(set(vals)))
        total = int(np.prod([len(g) for g in grids])) if grids else 0
        if total <= MAX_CANDIDATES:
            break
        factor *= 2
    want = 1 if goals[main] == UP else -1
    others = [t for t, g in goals.items() if t != main and g in (UP, DOWN, KEEP)]
    scored = []
    import itertools
    for combo in itertools.product(*grids):
        new = dict(start)
        new.update({p: float(v) for (p, *_r), v in zip(axes, combo)})
        if all(abs(new[p] - start[p]) < 1e-9 for p in PARAMS):
            continue
        dist = region.distance(new)
        if dist > FAR_DISTANCE:
            continue
        m = change(rows, main, margins.get(main), start, new, fit_cache, detail=False)
        if m.verdict not in SIGNIFICANT or m.direction != want:
            continue
        stat = {}
        for t in others:
            stat[t] = goal_status(goals[t], change(rows, t, margins.get(t), start, new, fit_cache, detail=False))
        viol = sum(1 for v in stat.values() if v == VIOLATED)
        unknown = sum(1 for v in stat.values() if v == UNKNOWN)
        met = sum(1 for v in stat.values() if v == MET)
        size = (m.delta * want) / (m.margin or 1.0)
        n_changed = sum(1 for p in PARAMS if abs(new[p] - start[p]) > 1e-9)
        # no broken goal first, then every goal checkable, then a sure
        # statement, then goals proven met, then the biggest gain (in steps
        # of the repeat scatter), then simple
        key = (viol, unknown, _STRENGTH_RANK[m.verdict], -met, -round(size), n_changed, dist)
        scored.append((key, new))
    if not scored:
        return [], (f"Nothing within what we measured makes {TARGETS[main][0]} "
                    f"{'higher' if want > 0 else 'lower'} with a clear statement.")
    scored.sort(key=lambda kv: kv[0])

    def n_changed_of(x):
        return sum(1 for p in PARAMS if abs(x[p] - start[p]) > 1e-9)

    picked: List[Dict[str, float]] = []
    for _key, new in scored:
        far_enough = all(max(abs(new[p] - q[p]) / region.scale[i] for i, p in enumerate(PARAMS)) >= MIN_SPREAD
                         for q in picked)
        if far_enough:
            picked.append(new)
        if len(picked) >= n:
            break
    # always offer the best "turn only one knob" option if there is one
    if picked and not any(n_changed_of(x) == 1 for x in picked):
        single = next((new for (key, new) in scored if n_changed_of(new) == 1 and key[:2] == scored[0][0][:2]), None)
        if single is not None:
            picked = picked[:n - 1] + [single]
    rank = {tuple(new[p] for p in PARAMS): key for key, new in scored}
    picked.sort(key=lambda x: rank[tuple(x[p] for p in PARAMS)])
    out = []
    for new in picked:
        chs = {t: change(rows, t, margins.get(t), start, new, fit_cache) for t in TARGETS}
        stat = {t: (goal_status(goals[t], chs[t]) if t in goals and goals[t] in (UP, DOWN, KEEP) else "")
                for t in TARGETS}
        out.append(Suggestion(new, chs, stat, sum(1 for t in others if stat[t] == VIOLATED),
                              region.distance(new)))
    msg = "" if out[0].violations == 0 else "No setting meets every goal - the best ones are shown."
    return out, msg


# ── chart data ──────────────────────────────────────────────────────────────

def chart_data(fit: Optional[Fit], conds: list, param: str, start: Dict[str, float]):
    """Measured points of `param` vs target, corrected for series level and
    for the other parameters (moved to the start values), plus the model
    curve with 95 % band. -> dict or None."""
    if not conds:
        return None
    xs = [c[1][param] for c in conds]
    if fit is None or param not in fit.usable:
        return {"x": xs, "y": [c[2] for c in conds], "series": [c[0] for c in conds], "curve": None}
    lvl = fit.level()
    x0 = {p: start.get(p) if start.get(p) is not None else fit.centre.get(p, 0.0) for p in PARAMS}
    for q in PARAMS:      # never extrapolate the other settings (start outside the data)
        vals = [c[1][q] for c in conds]
        x0[q] = min(max(x0[q], min(vals)), max(vals))
    ys = []
    for s, x, y, _n in conds:
        xa = {p: x[p] for p in PARAMS}
        xb = dict(x0)
        xb[param] = x[param]
        ys.append(y - fit.series_effect.get(s, lvl) + lvl - fit.predict_rel(xa) + fit.predict_rel(xb))
    grid = np.linspace(min(xs), max(xs), 40)
    k = len(fit.usable) + len(fit.squared)
    t975 = stats.t.ppf(0.975, fit.dof)
    base = fit.features(x0)
    cy, lo, hi = [], [], []
    for g in grid:
        xg = dict(x0)
        xg[param] = float(g)
        f = fit.features(xg)
        v = lvl + float(f @ fit.beta[:k])
        d = f - base       # uncertainty relative to the start point
        se = float(np.sqrt(max(d @ fit.cov[:k, :k] @ d, 0.0)))
        cy.append(v)
        lo.append(v - t975 * se)
        hi.append(v + t975 * se)
    return {"x": xs, "y": ys, "series": [c[0] for c in conds],
            "curve": (list(grid), cy, lo, hi)}


# ── wording ─────────────────────────────────────────────────────────────────

VERDICT_WORDS = {
    CLEAR: "clearly {dir}",
    PROBABLE: "probably {dir}",
    TENDENCY: "tendency {dir}",
    SAME: "about the same",
    NO_CLEAR: "no clear effect",
    UNCLEAR: "unclear",
    NOT_VARIED: "no statement",
    NO_DATA: "not measured",
    OUTSIDE: "no statement",
    NO_CHANGE: "",
}


def direction_word(target: str, direction: int) -> str:
    if target in ("fpm",):
        return "more" if direction > 0 else "fewer"
    return "higher" if direction > 0 else "lower"


def verdict_text(ch: Change) -> str:
    return VERDICT_WORDS[ch.verdict].format(dir=direction_word(ch.target, ch.direction))


def sentence(ch: Change, step_param: Optional[str] = None) -> str:
    """One line for the report script."""
    txt = verdict_text(ch) or "-"
    if ch.reason and ch.verdict not in SIGNIFICANT:
        txt += f" ({ch.reason})" if ch.verdict != NO_CLEAR else ""
    if ch.delta is not None and ch.ci is not None:
        lo, hi = ch.ci
        txt += f"  ({ch.delta:+.2f}, 95 % CI {lo:+.2f}..{hi:+.2f}"
        for p, (a, n) in ch.series.items():
            if n:
                txt += f"; {a}/{n} series agree"
        txt += ")"
    if ch.curved:
        txt += "  [not linear]"
    return txt
