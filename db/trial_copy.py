# db/trial_copy.py
"""Field list, source values and value rules of "Copy trials" - Qt-free,
shared by the desktop dialog (ui/copy_trials_dialog.py re-exports all of
it) and the web app. Moved out of ui/copy_trials_dialog.py on 2026-11-13
without behaviour change; writing the copies: db/trial_actions.copy_trials.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Never offered: measured on the run, copies start empty (see
# screen_show_experiment._col_not_copied(), which also empties the comments).
_SKIP_COLS = {
    "yarntensionbeforejet", "yarntensionafterjet", "tensionbeforejet_core",
    "tensionafterjetinside", "tensionafterjetoutside",
}
# Trial-wide fields shown without "Show all fields" (besides Housing, Jet,
# Jet plate, Air pressure and - on ATY - OF Core / OF Effect).
_DEFAULT_COLS = {"speedshaft2", "shaft2x_of", "shaft2speed"}

YARN_USE_CORE, YARN_USE_EFFECT = 1, 2

VARIES = object()        # source plies of one group have different values
NOT_AVAILABLE = object()  # source trial has no plies of that group

@dataclass
class CopyField:
    key: str                      # unique, e.g. "trial:AirPressure", "of:1"
    label: str
    kind: str                     # "trial" (tblTrial column) | "use_of" (ply OF per yarn use)
    column: str                   # tblTrial column, or tblTrialSettings column for use_of
    use_id: Optional[int] = None
    choices: Optional[List[Tuple[Any, str]]] = None   # dropdown (id, name)
    rule: Optional[str] = None    # onlyDoubles | onlyInteger | onlySZ | air
    default: bool = False


# ── field list ───────────────────────────────────────────────────────────

def _unique_choices(pairs) -> List[Tuple[Any, str]]:
    seen, out = set(), []
    for k, v in pairs:
        try:
            k = int(k)
        except (TypeError, ValueError):
            continue
        if k in seen:
            continue
        seen.add(k)
        out.append((k, str(v or "")))
    return sorted(out, key=lambda kv: kv[1].lower())


def build_copy_fields(machine_fields: Sequence[Dict], trial_cols: Dict[str, str],
                      lookup_maps: Dict[str, Dict], jets_list, housing_list,
                      has_use_groups: bool) -> List[CopyField]:
    """Editable fields for the copy dialog, from the machine's field config
    (tblMachineFields, already loaded in ShowExperimentScreen._machine_cache)."""
    def col(*cands):
        for c in cands:
            real = trial_cols.get(c.lower())
            if real:
                return real
        return None

    fields: List[CopyField] = []
    housing_col, jet_col = col("HousingID"), col("JetID")
    plate_col, air_col = col("JetPlate", "Jet_Plate"), col("AirPressure", "Air_Pressure")
    if housing_col:
        fields.append(CopyField(f"trial:{housing_col}", "Housing", "trial", housing_col,
                                choices=list(housing_list or []), default=True))
    if jet_col:
        fields.append(CopyField(f"trial:{jet_col}", "Jet", "trial", jet_col,
                                choices=list(jets_list or []), default=True))
    if plate_col:
        fields.append(CopyField(f"trial:{plate_col}", "Jet Plate Number", "trial", plate_col,
                                rule="onlyDoubles", default=True))
    if air_col:
        fields.append(CopyField(f"trial:{air_col}", "Air Pressure (bar)", "trial", air_col,
                                rule="air", default=True))
    taken = {f.column.lower() for f in fields}

    has_ply_of = False
    for fdef in machine_fields or []:
        storage = str(fdef.get("StorageTable") or "tbltrial").lower()
        orig = str(fdef.get("OriginalName") or "").strip()
        if storage == "tbltrialsettings":
            if orig.lower() == "of":
                has_ply_of = True
            continue
        real = trial_cols.get(orig.lower())
        if not real or real.lower() in taken or real.lower() in _SKIP_COLS:
            continue
        taken.add(real.lower())
        ff = str(fdef.get("FieldFunction") or "").strip()
        choices, rule = None, None
        if ff.lower().startswith("dropdown:"):
            choices = _unique_choices((lookup_maps.get(ff[9:].strip()) or {}).items())
        elif real.lower() == "w3_jet":
            choices = list(jets_list or [])
        elif real.lower() == "w3_housing":
            choices = list(housing_list or [])
        else:
            rule = ff or None
        fields.append(CopyField(f"trial:{real}", str(fdef.get("FieldName") or real), "trial", real,
                                choices=choices, rule=rule, default=real.lower() in _DEFAULT_COLS))

    # ATY: OF lives on the Core / Effect plies (tblTrialSettings.OF + YarnUseID)
    if has_ply_of and has_use_groups:
        fields.append(CopyField("of:core", "OF Core (%)", "use_of", "OF", YARN_USE_CORE,
                                rule="onlyDoubles", default=True))
        fields.append(CopyField("of:effect", "OF Effect (%)", "use_of", "OF", YARN_USE_EFFECT,
                                rule="onlyDoubles", default=True))
    # Visible-by-default fields first (stable), the rest behind "Show all fields"
    return [f for f in fields if f.default] + [f for f in fields if not f.default]


def load_source_values(trial_ids: Sequence[int], fields: Sequence[CopyField]) -> Dict[int, Dict[str, Any]]:
    """{trial_id: {field.key: value | VARIES | NOT_AVAILABLE}}"""
    from db.connection import fetch_all
    out: Dict[int, Dict[str, Any]] = {int(t): {} for t in trial_ids}
    if not trial_ids:
        return out
    ph = ",".join("?" for _ in trial_ids)
    trial_fields = [f for f in fields if f.kind == "trial"]
    if trial_fields:
        for r in fetch_all(f"SELECT * FROM tblTrial WHERE ID IN ({ph})", list(trial_ids)):
            low = {str(k).lower(): v for k, v in r.items()}
            tid = int(low["id"])
            for f in trial_fields:
                out.setdefault(tid, {})[f.key] = low.get(f.column.lower())
    use_fields = [f for f in fields if f.kind == "use_of"]
    if use_fields:
        vals: Dict[Tuple[int, int], set] = {}
        for r in fetch_all(
                f"SELECT TrialID, YarnUseID, [OF] AS v FROM tblTrialSettings "
                f"WHERE TrialID IN ({ph}) AND YarnUseID IS NOT NULL", list(trial_ids)):
            vals.setdefault((int(r["TrialID"]), int(r["YarnUseID"])), set()).add(r["v"])
        for tid in out:
            for f in use_fields:
                s = vals.get((tid, f.use_id))
                if not s:
                    out[tid][f.key] = NOT_AVAILABLE
                elif len(s) > 1:
                    out[tid][f.key] = VARIES
                else:
                    out[tid][f.key] = next(iter(s))
    return out


# ── value helpers ────────────────────────────────────────────────────────

_RE_INT = re.compile(r"^[+-]?\d+$")
_RE_FLOAT = re.compile(r"^[+-]?((\d+([.,]\d*)?)|([.,]\d+))$")
_RE_FLOAT_2DP = re.compile(r"^[+-]?(\d+([.,]\d{0,2})?|[.,]\d{1,2})$")


def normalize_value(rule: Optional[str], text: Any) -> Optional[str]:
    """Same rules as the Machine Data table (PivotEditModel): returns the
    normalized string, "" for empty, or None if invalid."""
    s = "" if text is None else str(text).strip()
    if s == "":
        return ""
    r = (rule or "").strip().lower()
    if r == "onlysz":
        up = s.upper().replace(" ", "")
        return up if up in ("S", "Z", "SZ") else None
    if r == "onlyinteger":
        return str(int(s)) if _RE_INT.fullmatch(s) else None
    if r in ("onlydoubles", "air"):
        if not (_RE_FLOAT_2DP if r == "air" else _RE_FLOAT).fullmatch(s):
            return None
        v = float(s.replace(",", "."))
        return str(int(v)) if v.is_integer() else (f"{v:.2f}".rstrip("0").rstrip(".") if r == "air" else f"{v}")
    return s


def display_value(field: CopyField, value: Any) -> str:
    if value is VARIES:
        return "div."
    if value is NOT_AVAILABLE or value is None:
        return ""
    if field.choices:
        try:
            key = int(value)
        except (TypeError, ValueError):
            key = value
        for k, name in field.choices:
            if k == key:
                return name
        return str(value)
    try:
        f = float(value)
        return str(int(f)) if f.is_integer() else f"{f:g}"
    except (TypeError, ValueError):
        return str(value)


_UNIT_RE = re.compile(r"\(([^)]*)\)\s*$")


def summary_value(field: CopyField, value: Any) -> str:
    """Value with its unit for the trial checklist, e.g. "0.8 bar",
    "550 m/min", "4% OF", "Plate Number 1" (Nutzerwunsch)."""
    txt = display_value(field, value)
    if not txt or field.choices:
        return txt
    col = field.column.lower()
    if field.kind == "use_of":
        return f"{txt}% OF {'Core' if field.use_id == YARN_USE_CORE else 'Effect'}"
    if col in ("jetplate", "jet_plate"):
        return f"Plate Number {txt}"
    if col == "shaft2x_of":
        return f"{txt}% OF"
    m = _UNIT_RE.search(field.label)
    unit = m.group(1).strip() if m else ""
    if unit.startswith("%"):
        return f"{txt}{unit}"
    return f"{txt} {unit}" if unit else txt


def _same(field: CopyField, a: Any, b: Any) -> bool:
    if a is VARIES or b is VARIES or a is NOT_AVAILABLE or b is NOT_AVAILABLE:
        return a is b
    if a in (None, "") and b in (None, ""):
        return True
    if field.choices:
        try:
            return int(a) == int(b)
        except (TypeError, ValueError):
            return str(a) == str(b)
    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return str(a).strip() == str(b).strip()
