"""Jet Advisor - which jets with which machine settings reach a target
(points/m, CV, stability) for a yarn (2026-11-15, desktop + web).

The reverse of the Process Playground (ui/dty_whatif.py): there the user
changes settings and sees what happens, here the user gives targets and
material and gets a ranking of jets with recommended settings.

Method (variant A, transparent, no extrapolation):
  1. similar yarns: same material (optional), final titer and filament count
     close (log distance, ENDTITER_STEP / FIL_STEP = distance 1); multi-ply
     yarns count with summed titer / filaments;
  2. per (yarn, jet) the fits of dty_whatif (pressure / overfeed / speed,
     series as level) - prediction = mean series level + model, its spread
     = model uncertainty + repeatability + spread between series;
  3. candidates: every measured setting (condition mean) and, with a fit for
     every requested target, a grid over the measured range (only points
     close to a measured setting, dty_whatif.FAR_DISTANCE);
  4. per candidate P(all targets met) (normal, targets independent), score
     = P x similarity factor; per jet the best candidate wins, the window =
     range of the grid points with P >= WINDOW_SHARE x best. Ties (often
     several settings / jets at P ~ 1) are broken by the safety margin
     (smallest distance inside the targets, in SD) or - prefer="air" - by the
     air consumption at that pressure (formula of ui/jet_roi.py).

Pure logic, no Qt - reads only, never writes.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy import stats

from ui import dty_whatif as w

PARAMS = list(w.PARAMS)                      # pressure, of, speed
TARGETS = list(w.LAB_TARGETS)                # fpm, fpm_cv, stab03 .. stab13

ENDTITER_STEP = 1.3      # factor of final titer that counts as distance 1
FIL_STEP = 1.5           # factor of filament count that counts as distance 1
MAX_DISTANCE = 1.0       # default: yarns further away are not used
SIM_PENALTY = 0.3        # score x (1 - SIM_PENALTY x min(distance, 1))
GRID_STEPS = 7
WINDOW_SHARE = 0.9
TOP_N = 30

# error codes (screens translate them)
ERR_NO_TARGET = "no_target"
ERR_NO_YARN = "no_yarn"


# ── master data ─────────────────────────────────────────────────────────────

_JET_SQL = """
SELECT j.ID AS jet_id, j.Jet AS jet_name, j.JetTypeID AS type_id, jt.Name AS type_name,
       j.Hersteller AS maker_id, h.Hersteller AS maker_name,
       j.JetGroupID AS group_id, g.GroupName AS group_name,
       j.Luftverbrauch AS air, j.Luftbohrung AS bore, j.AnzahlLuftbohrungen AS holes, j.TiterVon AS titer_from, j.TiterBis AS titer_to, j.IdealTiter AS titer_ideal
FROM tbljets j
LEFT JOIN tbljettype jt ON jt.ID = j.JetTypeID
LEFT JOIN tbljethersteller h ON h.ID = j.Hersteller
LEFT JOIN tbljetgroup g ON g.ID = j.JetGroupID
"""

_YARN_SQL = """
SELECT y.ID AS yarn_id, COALESCE(NULLIF(y.Kurzname, ''), y.Name) AS name, y.Material AS material_id,
       m.Material AS material, y.Garntyp AS type_id, gt.Garntyp AS yarn_type,
       y.Endtiter AS endtiter, y.Titer AS titer, y.NumberOfFilaments AS filaments
FROM tblyarn y
LEFT JOIN tblmaterial m ON m.ID = y.Material
LEFT JOIN tblgarntyp gt ON gt.ID = y.Garntyp
"""


def _f(v) -> Optional[float]:
    return w._num(v)


def load_jets() -> Dict[int, dict]:
    from db.connection import fetch_all
    out = {}
    for r in fetch_all(_JET_SQL, []):
        d = dict(r)
        d["bore"] = _f(str(d.get("bore") or "").replace(",", ".") or None)
        for k in ("air", "holes", "titer_from", "titer_to", "titer_ideal"):
            d[k] = _f(d.get(k))
        out[int(d["jet_id"])] = d
    return out


def load_yarns() -> Dict[int, dict]:
    from db.connection import fetch_all
    out = {}
    for r in fetch_all(_YARN_SQL, []):
        d = dict(r)
        for k in ("endtiter", "titer", "filaments"):
            d[k] = _f(d.get(k))
        out[int(d["yarn_id"])] = d
    return out


def yarn_key_features(key: str, yarns: Dict[int, dict]) -> Optional[dict]:
    """Features of a yarn key ('12' or '12+31'): summed final titer and
    filaments, set of materials; None if a ply is missing its numbers."""
    try:
        ids = [int(x) for x in str(key).split("+") if x]
    except ValueError:
        return None
    if not ids or any(i not in yarns for i in ids):
        return None
    ys = [yarns[i] for i in ids]
    if any(not y["endtiter"] or not y["filaments"] for y in ys):
        return None
    return {"endtiter": sum(y["endtiter"] for y in ys), "filaments": sum(y["filaments"] for y in ys),
            "materials": sorted({y["material_id"] for y in ys if y["material_id"] is not None}),
            "plies": len(ids)}


def yarn_distance(a: dict, b: dict) -> float:
    """Log distance of final titer and filament count (see ENDTITER_STEP / FIL_STEP)."""
    dt = math.log(a["endtiter"] / b["endtiter"]) / math.log(ENDTITER_STEP)
    df = math.log(a["filaments"] / b["filaments"]) / math.log(FIL_STEP)
    return math.hypot(dt, df)


# ── request / result ────────────────────────────────────────────────────────

@dataclass
class Spec:
    lo: Optional[float] = None
    hi: Optional[float] = None

    def active(self) -> bool:
        return self.lo is not None or self.hi is not None

    def prob(self, mean: float, sd: float) -> float:
        """P(a new run lands inside the spec), value ~ normal(mean, sd)."""
        return float(np.clip(self.prob_array(np.array([mean]), np.array([sd]))[0], 0.0, 1.0))

    def prob_array(self, mean: np.ndarray, sd: np.ndarray) -> np.ndarray:
        sd = np.maximum(sd, 1e-9)
        hi = stats.norm.cdf(self.hi, mean, sd) if self.hi is not None else 1.0
        lo = stats.norm.cdf(self.lo, mean, sd) if self.lo is not None else 0.0
        return np.clip(hi - lo, 0.0, 1.0)

    def miss(self, v: float, sd: float) -> float:
        """How far outside the spec, in standard deviations (0 = inside)."""
        sd = max(sd, 1e-9)
        out = 0.0
        if self.lo is not None and v < self.lo:
            out = (self.lo - v) / sd
        if self.hi is not None and v > self.hi:
            out = (v - self.hi) / sd
        return out

    def inside(self, v: float, sd: float) -> float:
        """Distance inside the spec to the nearest limit, in SD (negative = outside)."""
        sd = max(sd, 1e-9)
        d = [x for x in ((v - self.lo) / sd if self.lo is not None else None,
                         (self.hi - v) / sd if self.hi is not None else None) if x is not None]
        return min(d) if d else 0.0

    def met(self, v: float) -> bool:
        return (self.lo is None or v >= self.lo) and (self.hi is None or v <= self.hi)


@dataclass
class Request:
    targets: Dict[str, Spec]
    yarn_id: Optional[int] = None             # an existing yarn ...
    endtiter: Optional[float] = None          # ... or the numbers
    filaments: Optional[float] = None
    material_id: Optional[int] = None
    same_material: bool = True
    max_distance: float = MAX_DISTANCE
    jet_types: Optional[List[int]] = None     # None = all; 0 in the list = jets without a type
    makers: Optional[List[int]] = None
    groups: Optional[List[int]] = None
    titer_fit: bool = False                   # only jets whose titer range contains the final titer
    prefer: str = "robust"                    # tie-break: "robust" (safety margin) | "air" (less air)
    limits: Dict[str, Tuple[Optional[float], Optional[float]]] = field(default_factory=dict)


@dataclass
class Prediction:
    value: float
    sd: float
    prob: float
    met: bool
    miss: float = 0.0
    inside: float = 0.0


@dataclass
class Candidate:
    settings: Dict[str, float]
    preds: Dict[str, Prediction]
    prob: float
    source: str                               # "measured" | "model"
    n_trials: int = 0                         # measured: trials at this setting
    air: Optional[float] = None               # Nm3/h at this pressure (None = jet data missing)

    @property
    def miss(self) -> float:
        """Sum over the targets of the distance outside the spec (in SD) - ranks
        candidates when none reaches the targets."""
        return float(sum(p.miss for p in self.preds.values()))

    @property
    def safety(self) -> float:
        """Smallest distance inside the targets (SD) - bigger = more robust."""
        return float(min((p.inside for p in self.preds.values()), default=0.0))

    def rank_key(self, prefer: str = "robust"):
        """Bigger = better: P (in steps of 0.02), less miss, then safety or less air."""
        tie = -(self.air if self.air is not None else 1e9) if prefer == "air" else round(self.safety, 1)
        return (round(self.prob * 50), -round(self.miss, 1), tie, self.source == "measured", self.n_trials)


@dataclass
class JetResult:
    jet: dict
    yarn_key: str
    yarn_name: str
    distance: float
    score: float
    best: Candidate
    window: Dict[str, Tuple[float, float]]
    n_trials: int
    n_series: int
    series: List[Tuple[int, str]]
    varied: List[str]
    titer_ok: Optional[bool]
    prefer: str = "robust"
    trial_id: Optional[int] = None            # newest trial of the combination (opens the Process Playground)


# ── advisor ─────────────────────────────────────────────────────────────────

class Advisor:
    """Holds the trials, master data and fits (one instance per process /
    screen; reload() after new data)."""

    def __init__(self, rows: Optional[Sequence[dict]] = None, jets: Optional[Dict[int, dict]] = None,
                 yarns: Optional[Dict[int, dict]] = None):
        self._rows_in, self._jets_in, self._yarns_in = rows, jets, yarns
        self.reload()

    def reload(self) -> None:
        self.rows = list(self._rows_in) if self._rows_in is not None else w.load_rows()
        self.jets = self._jets_in if self._jets_in is not None else load_jets()
        self.yarns = self._yarns_in if self._yarns_in is not None else load_yarns()
        self.margins = {t: w.repeatability_sd(self.rows, t) for t in TARGETS}
        groups: Dict[Tuple[str, int], List[dict]] = defaultdict(list)
        for r in self.rows:
            if r.get("yarn_key") and r.get("jet_id") is not None and any(r.get(t) is not None for t in TARGETS):
                groups[(str(r["yarn_key"]), int(r["jet_id"]))].append(r)
        self.combos = dict(groups)
        self.features = {k: yarn_key_features(k, self.yarns) for k in {k for k, _j in groups}}
        self._fits: Dict[Tuple[str, int, str], tuple] = {}

    # lists for the screens
    def options(self) -> dict:
        used_jets = {j for _k, j in self.combos}
        used_yarns = {int(i) for k in self.features if self.features[k] for i in k.split("+")}

        def uniq(id_key, name_key):
            seen = {}
            for j in used_jets:
                d = self.jets.get(j)
                if d:
                    seen[d.get(id_key) if d.get(id_key) is not None else 0] = d.get(name_key) or ""
            return sorted(({"id": i, "name": n} for i, n in seen.items()), key=lambda x: (x["id"] == 0, x["name"]))

        mats = {}
        for y in self.yarns.values():
            if y["material_id"] is not None and int(y["yarn_id"]) in used_yarns:
                mats[y["material_id"]] = y["material"] or ""
        yarns = sorted((
            {"id": int(y["yarn_id"]), "name": y["name"] or "", "material_id": y["material_id"],
             "material": y["material"] or "", "endtiter": y["endtiter"], "filaments": y["filaments"],
             "yarn_type": y["yarn_type"] or ""}
            for y in self.yarns.values() if int(y["yarn_id"]) in used_yarns), key=lambda d: d["name"].lower())
        return {"jet_types": uniq("type_id", "type_name"), "makers": uniq("maker_id", "maker_name"),
                "groups": uniq("group_id", "group_name"),
                "materials": sorted(({"id": i, "name": n} for i, n in mats.items()), key=lambda x: x["name"]),
                "yarns": yarns, "targets": TARGETS, "params": PARAMS,
                "n_trials": len(self.rows), "n_combos": len(self.combos)}

    def _fit(self, key: str, jet: int, target: str):
        k = (key, jet, target)
        if k not in self._fits:
            self._fits[k] = w.fit_target(self.combos[(key, jet)], target, self.margins.get(target))
        return self._fits[k]

    def _wanted(self, req: Request) -> Optional[dict]:
        if req.yarn_id is not None:
            y = self.yarns.get(int(req.yarn_id))
            if not y or not y["endtiter"] or not y["filaments"]:
                return None
            return {"endtiter": y["endtiter"], "filaments": y["filaments"],
                    "materials": [y["material_id"]] if y["material_id"] is not None else [], "plies": 1,
                    "yarn_key": str(int(req.yarn_id))}
        if not req.endtiter or not req.filaments or req.endtiter <= 0 or req.filaments <= 0:
            return None
        return {"endtiter": float(req.endtiter), "filaments": float(req.filaments),
                "materials": [req.material_id] if req.material_id is not None else [], "plies": 1, "yarn_key": None}

    def _jet_ok(self, jet: dict, req: Request, endtiter: float) -> bool:
        if req.jet_types is not None and (jet.get("type_id") or 0) not in req.jet_types:
            return False
        if req.makers is not None and (jet.get("maker_id") or 0) not in req.makers:
            return False
        if req.groups is not None and (jet.get("group_id") or 0) not in req.groups:
            return False
        if req.titer_fit and _titer_ok(jet, endtiter) is False:
            return False
        return True

    def similar_yarns(self, req: Request) -> List[Tuple[str, float]]:
        want = self._wanted(req)
        if want is None:
            return []
        out = []
        for key, feat in self.features.items():
            if not feat:
                continue
            if req.same_material and want["materials"] and feat["materials"] != want["materials"]:
                continue
            d = 0.0 if want.get("yarn_key") == key else yarn_distance(feat, want)
            if d <= req.max_distance + 1e-9:
                out.append((key, d))
        return sorted(out, key=lambda x: x[1])

    def advise(self, req: Request, top_n: int = TOP_N) -> dict:
        active = {t: s for t, s in req.targets.items() if t in TARGETS and s.active()}
        if not active:
            return {"error": ERR_NO_TARGET}
        want = self._wanted(req)
        if want is None:
            return {"error": ERR_NO_YARN}
        similar = self.similar_yarns(req)
        best_per_jet: Dict[int, JetResult] = {}
        n_combos = 0
        for key, dist in similar:
            for (k, jet_id), rows in self.combos.items():
                if k != key:
                    continue
                jet = self.jets.get(jet_id) or {"jet_id": jet_id, "jet_name": str(rows[0].get("jet_name") or jet_id)}
                if not self._jet_ok(jet, req, want["endtiter"]):
                    continue
                n_combos += 1
                res = self._evaluate(key, jet_id, rows, active, req, dist, jet, want["endtiter"])
                if res is None:
                    continue
                cur = best_per_jet.get(jet_id)
                if cur is None or _jet_key(res) < _jet_key(cur):
                    best_per_jet[jet_id] = res
        ranked = sorted(best_per_jet.values(), key=_jet_key)
        return {"results": ranked[:top_n], "n_jets": len(ranked), "n_combos": n_combos,
                "yarns": [{"key": k, "name": self._key_name(k), "distance": round(d, 2)} for k, d in similar],
                "targets": list(active)}

    def _key_name(self, key: str) -> str:
        for (k, _j), rows in self.combos.items():
            if k == key:
                return str(rows[0].get("yarn_name") or key)
        return key

    def _in_limits(self, req: Request, x: Dict[str, float]) -> bool:
        for p, (lo, hi) in req.limits.items():
            v = x.get(p)
            if v is None:
                continue
            if lo is not None and v < lo - 1e-9 or hi is not None and v > hi + 1e-9:
                return False
        return True

    def _evaluate(self, key, jet_id, rows, active, req, dist, jet, endtiter) -> Optional[JetResult]:
        sims = 1.0 - SIM_PENALTY * min(dist, 1.0)
        cands: List[Candidate] = []
        # measured settings
        agg: Dict[tuple, List[dict]] = defaultdict(list)
        for r in rows:
            if all(r.get(p) is not None for p in PARAMS):
                agg[tuple(r[p] for p in PARAMS)].append(r)
        for xs, rs in agg.items():
            x = dict(zip(PARAMS, xs))
            if not self._in_limits(req, x):
                continue
            preds = {}
            for t, spec in active.items():
                vals = [r[t] for r in rs if r.get(t) is not None]
                if not vals:
                    break
                m = float(np.mean(vals))
                rep = self.margins.get(t) or (float(np.std(vals, ddof=1)) if len(vals) > 1 else abs(m) * 0.1 + 1e-6)
                sd = rep * math.sqrt(1.0 + 1.0 / len(vals))
                preds[t] = Prediction(m, sd, spec.prob(m, sd), spec.met(m), spec.miss(m, sd),
                                      spec.inside(m, sd))
            if len(preds) == len(active):
                cands.append(Candidate(x, preds, float(np.prod([p.prob for p in preds.values()])),
                                       "measured", len(rs), air_nm3h(jet, x["pressure"])))
        # model grid
        fits = {t: self._fit(key, jet_id, t)[0] for t in active}
        grid_cands: List[Candidate] = []
        if all(f is not None for f in fits.values()):
            grid_cands = self._grid(rows, fits, active, req, jet)
            cands += grid_cands
        if not cands:
            return None
        best = max(cands, key=lambda c: c.rank_key(req.prefer))
        window = {}
        pool = [c for c in grid_cands + [c for c in cands if c.source == "measured"]
                if c.prob >= WINDOW_SHARE * best.prob and best.prob > 0]
        for p in PARAMS:
            vals = [c.settings[p] for c in pool] or [best.settings[p]]
            window[p] = (float(min(vals)), float(max(vals)))
        series = sorted({(int(r["series_id"]), str(r.get("series_name") or "")) for r in rows}, key=lambda s: -s[0])
        return JetResult(jet, key, str(rows[0].get("yarn_name") or key), dist, best.prob * sims, best, window,
                         len(rows), len(series), series, w.judgeable_params(rows), _titer_ok(jet, endtiter),
                         req.prefer, max((int(r["trial_id"]) for r in rows if r.get("trial_id") is not None),
                                         default=None))

    def _grid(self, rows, fits: Dict[str, "w.Fit"], active, req, jet: dict) -> List[Candidate]:
        measured = [r for r in rows if all(r.get(p) is not None for p in PARAMS)]
        if not measured:
            return []
        usable = set().union(*(set(f.usable) for f in fits.values()))
        axes = {}
        ranges = {}
        for p in PARAMS:
            vals = sorted({r[p] for r in measured})
            ranges[p] = (vals[-1] - vals[0]) or 1.0
            lo, hi = req.limits.get(p, (None, None))
            if p in usable:
                a, b = vals[0], vals[-1]
                if lo is not None:
                    a = max(a, lo)
                if hi is not None:
                    b = min(b, hi)
                if a > b + 1e-9:
                    return []
                axes[p] = sorted(set(np.round(np.linspace(a, b, GRID_STEPS), 4)))
            else:
                axes[p] = [v for v in vals if (lo is None or v >= lo - 1e-9) and (hi is None or v <= hi + 1e-9)]
                if not axes[p]:
                    return []
        mesh = np.array(np.meshgrid(*[axes[p] for p in PARAMS], indexing="ij")).reshape(len(PARAMS), -1).T
        meas = np.array([[r[p] for p in PARAMS] for r in measured])
        scale = np.array([ranges[p] for p in PARAMS])
        # near a measured setting (all parameters together)
        dmin = np.min(np.max(np.abs(mesh[:, None, :] - meas[None, :, :]) / scale, axis=2), axis=1)
        mesh = mesh[dmin <= w.FAR_DISTANCE + 1e-9]
        if not len(mesh):
            return []
        means, sds, pt, probs = {}, {}, {}, np.ones(len(mesh))
        for t, f in fits.items():
            k = len(f.usable) + len(f.squared)
            S = len(f.series_effect)
            F = np.array([f.features(dict(zip(PARAMS, row))) for row in mesh]).reshape(len(mesh), k)
            A = np.hstack([F, np.full((len(mesh), S), 1.0 / S)])
            mu = A @ f.beta
            var_model = np.einsum("ij,jk,ik->i", A, f.cov, A)
            rep = self.margins.get(t) or 0.0
            between = float(np.var(list(f.series_effect.values()), ddof=1)) if S > 1 else 0.0
            sd = np.sqrt(np.maximum(var_model, 0) + rep ** 2 + between)
            means[t], sds[t] = mu, sd
            pt[t] = active[t].prob_array(mu, sd)
            probs = probs * pt[t]
        out = []
        for i, row in enumerate(mesh):
            preds = {t: Prediction(float(means[t][i]), float(sds[t][i]), float(pt[t][i]),
                                   active[t].met(float(means[t][i])),
                                   active[t].miss(float(means[t][i]), float(sds[t][i])),
                                   active[t].inside(float(means[t][i]), float(sds[t][i]))) for t in fits}
            x = dict(zip(PARAMS, map(float, row)))
            out.append(Candidate(x, preds, float(probs[i]), "model", 0, air_nm3h(jet, x["pressure"])))
        return out


def _jet_key(r: "JetResult"):
    """Ranking (smaller = better): score, how far the best setting misses the
    targets, safety margin or air, yarn similarity, trials behind it."""
    c = r.best
    tie = (c.air if c.air is not None else 1e9) if r.prefer == "air" else -round(c.safety, 1)
    return (-round(r.score * 50), round(c.miss, 1), tie, round(r.distance, 2), -r.n_trials)


def air_nm3h(jet: dict, pressure: Optional[float]) -> Optional[float]:
    """Air consumption of the jet at this pressure (bar g), formula of the Jet ROI
    calculator; None without bore / Luftverbrauch."""
    from ui import jet_roi
    if pressure is None or not (jet.get("bore") or jet.get("air")):
        return None
    holes = int(jet.get("holes") or 1)
    return float(jet_roi.air_flow_nm3h(jet.get("bore") or 0.0, holes, pressure, jet.get("air")))


def _titer_ok(jet: dict, endtiter: float) -> Optional[bool]:
    lo, hi = jet.get("titer_from"), jet.get("titer_to")
    if lo is None and hi is None:
        return None
    return (lo is None or endtiter >= lo) and (hi is None or endtiter <= hi)


# ── JSON for the web / plain dicts for the desktop ──────────────────────────

def _r(v, d=3):
    return None if v is None else round(float(v), d)


def result_json(res: dict) -> dict:
    if "error" in res:
        return res
    out = []
    for r in res["results"]:
        j = r.jet
        out.append({
            "jet_id": j.get("jet_id"), "jet": j.get("jet_name") or "", "type": j.get("type_name") or "",
            "type_id": j.get("type_id"), "maker": j.get("maker_name") or "", "group": j.get("group_name") or "",
            "air": _r(j.get("air")), "titer_from": _r(j.get("titer_from"), 0), "titer_to": _r(j.get("titer_to"), 0),
            "titer_ok": r.titer_ok, "yarn_key": r.yarn_key, "yarn": r.yarn_name, "distance": _r(r.distance, 2),
            "score": _r(r.score), "prob": _r(r.best.prob), "source": r.best.source,
            "settings": {p: _r(v, 2) for p, v in r.best.settings.items()},
            "window": {p: [_r(a, 2), _r(b, 2)] for p, (a, b) in r.window.items()},
            "miss": _r(r.best.miss, 2), "safety": _r(r.best.safety, 2), "air_nm3h": _r(r.best.air, 2),
            "all_met": all(p.met for p in r.best.preds.values()),
            "preds": {t: {"value": _r(p.value, 2), "sd": _r(p.sd, 2), "prob": _r(p.prob), "met": p.met}
                      for t, p in r.best.preds.items()},
            "n_trials": r.n_trials, "n_series": r.n_series, "n_at_setting": r.best.n_trials,
            "series": [{"id": s, "name": n} for s, n in r.series[:12]], "varied": r.varied,
            "trial_id": r.trial_id,
        })
    return {"results": out, "n_jets": res["n_jets"], "n_combos": res["n_combos"], "yarns": res["yarns"],
            "targets": res["targets"]}


def request_from_json(d: dict) -> Request:
    """Request from plain JSON (web body / desktop form): numbers checked, unknown keys ignored."""
    num = _f

    def ids(v):
        if v is None:
            return None
        return [int(x) for x in v]

    targets = {}
    for t, s in (d.get("targets") or {}).items():
        if t in TARGETS and isinstance(s, dict):
            targets[t] = Spec(num(s.get("lo")), num(s.get("hi")))
    limits = {}
    for p, s in (d.get("limits") or {}).items():
        if p in PARAMS and isinstance(s, (list, tuple)) and len(s) == 2:
            limits[p] = (num(s[0]), num(s[1]))
    yid = d.get("yarn_id")
    mid = d.get("material_id")
    return Request(targets=targets, yarn_id=int(yid) if yid not in (None, "") else None,
                   endtiter=num(d.get("endtiter")), filaments=num(d.get("filaments")),
                   material_id=int(mid) if mid not in (None, "") else None,
                   same_material=bool(d.get("same_material", True)),
                   max_distance=max(0.0, min(3.0, num(d.get("max_distance")) or MAX_DISTANCE)),
                   jet_types=ids(d.get("jet_types")), makers=ids(d.get("makers")), groups=ids(d.get("groups")),
                   titer_fit=bool(d.get("titer_fit", False)), limits=limits,
                   prefer="air" if d.get("prefer") == "air" else "robust")
