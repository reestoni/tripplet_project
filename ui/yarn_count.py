"""yarn_count.py - yarn count (linear density) conversions for the Yarn Count
Converter (ui/screen_yarn_count.py, Sidebar Tools, Nutzerwunsch 2026-11-09).

Pure functions, no Qt - tested in tests/test_yarn_count.py.

Base unit is tex (g per 1000 m). Direct systems (mass per length) grow with
the yarn thickness, indirect systems (length per mass) shrink:
    dtex = 10 x tex          (g / 10 000 m)
    den  =  9 x tex          (g /  9 000 m)  ->  den = 0.9 x dtex
    ktex = tex / 1000, mtex = 1000 x tex
    Nm   = 1000 / tex        (m per g)
    English indirect counts (hanks of N yards per lb): count = 453.59237 x 1000 /
    (N x 0.9144) / tex  ->  Ne 840 yd (590.54), NeK 560 yd (885.81),
    NeL 300 yd (1653.5), Run 1600 yd (310.0)
    grain/yd = tex x 0.9144 / 0.06479891 / 1000
Filament diameter from dtex per filament and polymer density rho (g/cm3):
    d [um] = 10 x sqrt(4 x dtex_f / (pi x rho))
"""
from __future__ import annotations

import math
import re
from typing import Dict, List, Optional, Tuple

YD = 0.9144          # m
LB = 453.59237       # g
GRAIN = 0.06479891   # g


def _english(yards_per_hank: float) -> float:
    """tex x count for an indirect English system (hanks of N yards per lb)."""
    return LB * 1000.0 / (yards_per_hank * YD)


# key, label, kind ("direct": unit = k x tex, "indirect": unit = k / tex), k, description
UNITS: List[Tuple[str, str, str, float, str]] = [
    ("dtex", "dtex", "direct", 10.0, "g per 10'000 m"),
    ("den", "den (denier)", "direct", 9.0, "g per 9'000 m"),
    ("tex", "tex", "direct", 1.0, "g per 1'000 m"),
    ("ktex", "ktex", "direct", 0.001, "g per m (slivers, tows)"),
    ("mtex", "mtex", "direct", 1000.0, "mg per 1'000 m"),
    ("Nm", "Nm (metric count)", "indirect", 1000.0, "m per g"),
    ("Ne", "Ne / NeB (cotton count)", "indirect", _english(840), "hanks of 840 yd per lb"),
    ("NeK", "NeK / NeW (worsted count)", "indirect", _english(560), "hanks of 560 yd per lb"),
    ("NeL", "NeL (linen lea)", "indirect", _english(300), "leas of 300 yd per lb"),
    ("Run", "Run (US woollen)", "indirect", _english(1600), "hanks of 1'600 yd per lb"),
    ("gryd", "grain/yd", "direct", YD / GRAIN / 1000.0, "grains per yard (slivers)"),
]
UNIT = {u[0]: u for u in UNITS}

# typical polymer densities in g/cm3 (for the filament diameter)
DENSITIES: List[Tuple[str, float]] = [
    ("PES (polyester)", 1.38),
    ("PA 6", 1.14),
    ("PA 6.6", 1.14),
    ("PP (polypropylene)", 0.91),
    ("PAN (acrylic)", 1.17),
    ("CV (viscose)", 1.52),
    ("CO (cotton)", 1.54),
    ("Aramid", 1.44),
    ("Glass", 2.54),
]


def to_tex(value: float, unit: str) -> float:
    _key, _label, kind, k, _desc = UNIT[unit]
    if value is None or value <= 0:
        raise ValueError("count must be greater than 0")
    return value / k if kind == "direct" else k / value


def from_tex(tex: float, unit: str) -> float:
    _key, _label, kind, k, _desc = UNIT[unit]
    return tex * k if kind == "direct" else k / tex


def convert(value: float, unit: str) -> Dict[str, float]:
    """{unit key: value} for all units."""
    tex = to_tex(value, unit)
    return {u[0]: from_tex(tex, u[0]) for u in UNITS}


def fmt(value: float, unit: str = "") -> str:
    """Readable number: more decimals for small values, no trailing zeros."""
    if value is None or not math.isfinite(value):
        return "–"
    a = abs(value)
    decimals = 0 if a >= 1000 else 1 if a >= 100 else 2 if a >= 1 else 3
    s = f"{value:,.{decimals}f}".replace(",", "'")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def filament_diameter_um(dtex_per_filament: float, density: float) -> float:
    return 10.0 * math.sqrt(4.0 * dtex_per_filament / (math.pi * density))


# ── yarn notation ──────────────────────────────────────────────────────
_UNIT_WORDS = {"dtex": "dtex", "dt": "dtex", "den": "den", "d": "den", "td": "den", "tex": "tex", "nm": "Nm",
               "ne": "Ne"}
_NOTATION = re.compile(
    r"""^\s*
    (?:(?P<plies_pre>\d+)\s*[x×*]\s*)?                 # 2x ...
    (?:(?P<unit_pre>dtex|den|tex|nm|ne)\s*)?           # dtex 167 ...
    (?P<count>\d+(?:[.,]\d+)?)\s*
    (?P<unit>dtex|dt|den|td|d|tex|nm|ne)?\s*           # ... 150D
    (?:[/\s]*\s*(?:f\s*)?(?P<fil>\d+)\s*(?:f(?:il)?)?)?  # f48 / /48F / /48
    (?:\s*[x×*]\s*(?P<plies_post>\d+))?                # ... x2
    \s*$""", re.IGNORECASE | re.VERBOSE)


def parse_notation(text: str, default_unit: str = "dtex") -> Optional[Dict]:
    """Parses e.g. "167f48", "dtex 167 f48", "150D/48F", "2x167f48",
    "78f68x2", "300/96" (unit from default_unit). Returns None if it is not
    understood, else {count, unit, filaments, plies, total_dtex, dtex_f}."""
    if not text or not text.strip():
        return None
    s = text.strip().replace(",", ".")
    m = _NOTATION.match(s)
    if not m:
        return None
    unit = (m.group("unit") or m.group("unit_pre") or "").lower()
    unit = _UNIT_WORDS.get(unit, default_unit)
    if unit not in UNIT:
        return None
    count = float(m.group("count"))
    if count <= 0:
        return None
    fil = int(m.group("fil")) if m.group("fil") else None
    if fil is not None and fil <= 0:
        return None
    plies = int(m.group("plies_pre") or m.group("plies_post") or 1)
    if plies <= 0:
        return None
    dtex_single = from_tex(to_tex(count, unit), "dtex")
    total = dtex_single * plies
    dtex_f = dtex_single / fil if fil else None
    return {"count": count, "unit": unit, "filaments": fil, "plies": plies,
            "dtex_single": dtex_single, "total_dtex": total,
            "total_filaments": fil * plies if fil else None, "dtex_f": dtex_f}


def formula(unit: str) -> str:
    """Readable conversion rule, e.g. "tex = dtex / 10" or "tex = 590.54 / Ne"."""
    key, label, kind, k, _desc = UNIT[unit]
    name = label.split(" ")[0]
    if key == "tex":
        return "tex = tex"
    def num(x: float) -> str:   # constants with 2 decimals, e.g. 590.54
        return f"{x:,.2f}".rstrip("0").rstrip(".").replace(",", "'")
    if kind == "direct":
        return f"tex = {name} × {num(1 / k)}" if k < 1 else f"tex = {name} / {num(k)}"
    return f"tex = {num(k)} / {name}"


def notation(total_dtex_single: float, filaments: Optional[int], plies: int) -> str:
    """Yarn designation, e.g. "2 × dtex 167 f48 · 2 × 150.3 den / 48 f"."""
    pre = f"{plies} × " if plies > 1 else ""
    den = total_dtex_single * 0.9
    if filaments:
        return f"{pre}dtex {fmt(total_dtex_single)} f{filaments} · {pre}{fmt(den)} den / {filaments} f"
    return f"{pre}dtex {fmt(total_dtex_single)} · {pre}{fmt(den)} den"


def filament_values(tex: Optional[float], filaments: Optional[int], plies: int, density: float) -> Dict[str, Optional[float]]:
    """"Filaments & plies" of the converter: per filament, totals (n x single count, no twist take-up),
    filament diameter and the designation. None values = not computable (no count / no filaments)."""
    keys = ("dpf_dtex", "dpf_den", "diameter", "total_dtex", "total_den", "total_Nm", "total_Ne", "total_fil")
    if not tex:
        return {**{k: None for k in keys}, "designation": None}
    plies = plies if plies and plies > 0 else 1
    dtex = tex * 10
    total = tex * plies
    out: Dict[str, Optional[float]] = {
        "total_dtex": total * 10, "total_den": total * 9, "total_Nm": from_tex(total, "Nm"),
        "total_Ne": from_tex(total, "Ne"), "total_fil": float(filaments * plies) if filaments else None,
        "dpf_dtex": dtex / filaments if filaments else None, "dpf_den": dtex * 0.9 / filaments if filaments else None,
        "diameter": filament_diameter_um(dtex / filaments, density) if filaments else None}
    out["designation"] = notation(dtex, filaments, plies)     # type: ignore[assignment]
    return out

