# db/formula.py
"""Calculated fields of the Smart Chart dashboard (Nutzerwunsch 2026-10-30):
safe formulas on the fields of a trial, e.g. "FP/m per air consumption".

Stored with field keys:     {fpm} / {air_cons_real}
Shown to the user as:       [Intermingling Points (FP/m)] / [Air Consumption (m3/h)]
to_display() / from_display() convert between the two (fields by their
label, case-insensitive; a unique title works too).

Only numbers, fields, + - * / ** %, brackets and a few functions (abs,
sqrt, log, log10, exp, round, min, max) are allowed - checked on the
Python syntax tree, never eval() of free text. A result is None when a
field has no value or the maths fails (division by zero …).
"""
from __future__ import annotations

import ast
import math
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

FUNCS = {"abs": abs, "sqrt": math.sqrt, "log": math.log, "log10": math.log10, "exp": math.exp,
         "round": round, "min": min, "max": max}
_OPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.USub, ast.UAdd)
_KEY = re.compile(r"\{([A-Za-z0-9_]+)\}")
_LABEL = re.compile(r"\[([^\]]+)\]")


class FormulaError(ValueError):
    pass


def keys_in(formula: str) -> List[str]:
    return list(dict.fromkeys(_KEY.findall(formula or "")))


def compile_formula(formula: str, fields: Dict[str, Any], exclude: Optional[str] = None):
    """(code object, field keys) or FormulaError with a readable message."""
    text = (formula or "").strip()
    if not text:
        raise FormulaError("The formula is empty.")
    keys = keys_in(text)
    for k in keys:
        if k not in fields:
            raise FormulaError(f"Unknown field {k}.")
        if k == exclude:
            raise FormulaError("A calculated field cannot use itself.")
        if fields[k].kind != "num":
            raise FormulaError(f"“{fields[k].title}” is not a number field.")
    names = {k: f"_f{i}" for i, k in enumerate(keys)}
    py = _KEY.sub(lambda m: names[m.group(1)], text).replace("^", "**").replace("×", "*").replace("÷", "/")
    try:
        tree = ast.parse(py, mode="eval")
    except SyntaxError:
        raise FormulaError("The formula is not complete - check brackets and operators.")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Load)) or isinstance(node, _OPS):
            continue
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            continue
        if isinstance(node, ast.Name) and (node.id in names.values() or node.id in FUNCS):
            continue
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCS and not node.keywords:
            continue
        raise FormulaError("Only numbers, fields, + - * / ^ ( ) and abs, sqrt, log, log10, exp, round, min, max "
                           "are allowed.")
    code = compile(tree, "<formula>", "eval")
    return (code, [(k, names[k]) for k in keys]), keys


def evaluate(compiled, values: Dict[str, Optional[float]]) -> Optional[float]:
    code, mapping = compiled
    env: Dict[str, Any] = dict(FUNCS)
    for k, name in mapping:
        v = values.get(k)
        if v is None:
            return None
        env[name] = v
    try:
        r = eval(code, {"__builtins__": {}}, env)   # noqa: S307 - syntax tree checked in compile_formula
    except (ArithmeticError, ValueError, TypeError, OverflowError):
        return None
    try:
        r = float(r)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(r) or math.isinf(r) else r


def display_names(fields: Iterable[Any]) -> Dict[str, str]:
    """{key: name in the formula}: the label, or "label · group" when two
    fields share a label (Titer (dtex) of the yarn and of the lab)."""
    fl = list(fields)
    count: Dict[str, int] = {}
    for f in fl:
        count[f.label.lower()] = count.get(f.label.lower(), 0) + 1
    return {f.key: f.label if count[f.label.lower()] == 1 else f"{f.label} · {f.group}" for f in fl}


def to_display(formula: str, fields: Dict[str, Any]) -> str:
    names = display_names(fields.values())
    return _KEY.sub(lambda m: f"[{names[m.group(1)]}]" if m.group(1) in names else m.group(0), formula or "")


def from_display(text: str, fields: Iterable[Any]) -> str:
    """[Label] -> {key}; FormulaError for unknown or ambiguous names."""
    fl = list(fields)
    unique = {n.lower(): k for k, n in display_names(fl).items()}
    by_label: Dict[str, List[Any]] = {}
    for f in fl:
        for name in {f.label.lower(), f.title.lower()}:
            by_label.setdefault(name, []).append(f)

    def repl(m):
        name = m.group(1).strip().lower()
        if name in unique:
            return "{" + unique[name] + "}"
        hits = by_label.get(name, [])
        exact = [f for f in hits if f.label.lower() == name] or hits
        if not exact:
            raise FormulaError(f"Unknown field [{m.group(1).strip()}].")
        if len({f.key for f in exact}) > 1:
            raise FormulaError(f"[{m.group(1).strip()}] exists more than once - pick it from the list "
                               f"(e.g. [{exact[0].label} · {exact[0].group}]).")
        return "{" + exact[0].key + "}"
    return _LABEL.sub(repl, text or "")
