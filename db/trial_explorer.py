# db/trial_explorer.py
"""Data layer of the new Smart Chart (Nutzerwunsch 2026-10-30): find trials
by their properties across all series, then chart any field against any other.

- FIELD CATALOG (build_catalog): one list of fields with plain names and
  units, grouped Yarn / Machine / Lab / General. Measurement and machine
  fields come from tblSmartChartAxis (the curated axis list of the series
  report - a new row there = a new field here, no code); yarn and general
  fields are built in. Fields whose table/column is missing are left out.
- DATASET (TrialDataset): one row per trial (reference samples excluded),
  plus its plies with their yarn. Field values are loaded lazily per field
  and cached, so only fields that are filtered/charted cost a query.
- FILTERS: {"key", "min", "max"} for numbers, {"key", "values": [...]} for
  lists. Yarn filters must hold for ONE ply together (PES + 70-80 dtex +
  30-40 filaments = the same yarn), restricted to Core/Effect plies with
  ply_scope "core"/"effect". That ply is the trial's "matched ply" - yarn
  values in chart and list come from it.

- STATISTICS (Nutzerwunsch 2026-10-30, the superuser Statistics page as
  dashboard visuals): experiment fields (product group, order type,
  project, owner, start month), time fields (Year/Month of the series,
  Trial year/month) and "Tested on" (list of lab machines - a list value,
  a trial counts once per machine). Series without trials and experiments
  without series are kept as EMPTY rows (`TrialDataset.empties`, negative
  ids): only `apply(..., include_empty=True)` returns them, which the
  dashboard does for "Count of trial series / experiments" - so these
  counts match the Statistics page.

Pure Python apart from the loaders, so filtering/aggregation is testable
with a hand-built dataset (tests/test_trial_explorer.py).
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field as dc_field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

NONE_LABEL = "(none)"
CALC_GROUP = "Calculated"
GROUPS = (CALC_GROUP, "Yarn", "Jet", "Machine", "Machine (per ply)", "Lab", "Experiment", "Time", "General")
# Tables with one or more rows per trial -> field group names (Smart Chart
# "Fields" pane, Nutzerwunsch 2026-10-30 "wie Power BI": all fields of all tables)
TABLE_GROUPS = {
    "tbltrial": "Machine",
    "tbltrialsettings": "Machine (per ply)",
    "tbllaborstatimatds": "Statimat",
    "tbllaborstatimatm": "Statimat",
    "tbllaboritematlab": "Itemat Lab",
    "tbllaboritematplus": "Itemat Plus",
    "tbllabortiter": "Titer",
    "tbllabordtyomat": "DTYoMat",
    "tbllaboratyomat": "ATYoMat",
    "tbllaborrapid600": "Rapid 600",
    "tbllaborekb": "Crimp (EKB)",
    "tbllaborheissluftschrumpf": "Hot air shrinkage",
    "tbllaborkochschrumpf": "Boiling shrinkage",
    "tbllaboratyshrinkage": "ATY shrinkage",
    "tbllaborwaterbath": "Water bath",
}
_SKIP_COLUMNS = {"id", "trialid", "trialseriesid", "globalid", "user", "userid", "timestamp", "createdby",
                 "versuchsnummer", "isreference", "yarnid", "spoolid", "ply"}
_NUM_TYPES = {"int", "decimal", "double", "float", "smallint", "tinyint", "bigint", "mediumint", "real"}
PLY_SCOPES = ("any", "core", "effect")


@dataclass
class Field:
    key: str
    title: str
    unit: str = ""
    group: str = "General"
    kind: str = "num"          # "num" | "cat"
    level: str = "trial"       # "trial" | "yarn" (per ply)
    source: Dict[str, Any] = dc_field(default_factory=dict)

    @property
    def label(self) -> str:
        return f"{self.title} ({self.unit})" if self.unit else self.title


# ── built-in fields ──────────────────────────────────────────────────────
YARN_FIELDS = [
    Field("yarn_material", "Material", "", "Yarn", "cat", "yarn"),
    Field("yarn_type", "Yarn type", "", "Yarn", "cat", "yarn"),
    Field("yarn_endtiter", "End titer", "dtex", "Yarn", "num", "yarn"),
    Field("yarn_titer", "Titer", "dtex", "Yarn", "num", "yarn"),
    Field("yarn_filaments", "Filaments", "", "Yarn", "num", "yarn"),
    Field("yarn_dpf", "dpf", "dtex", "Yarn", "num", "yarn"),
    Field("yarn_name", "Yarn", "", "Yarn", "cat", "yarn"),
    Field("yarn_use", "Yarn use", "", "Yarn", "cat", "yarn"),
]
GENERAL_FIELDS = [
    Field("machine", "Machine", "", "General", "cat"),
    Field("jet", "Jet", "", "Jet", "cat"),
    Field("series", "Trial series", "", "General", "cat"),
    Field("experiment", "Experiment", "", "General", "cat"),
    Field("owner", "Owner", "", "General", "cat"),
    Field("tested_on", "Tested on (lab machine)", "", "General", "cat", source={"computed": "tested_on"}),
    Field("year", "Year", "", "Time", "cat"),
    Field("month", "Month", "", "Time", "cat"),
    Field("trial_year", "Trial year", "", "Time", "cat"),
    Field("trial_month", "Trial month", "", "Time", "cat"),
    Field("exp_productgroup", "Product group", "", "Experiment", "cat"),
    Field("exp_ordertype", "Order type", "", "Experiment", "cat"),
    Field("exp_project", "Project", "", "Experiment", "cat"),
    Field("exp_owner", "Experiment owner", "", "Experiment", "cat"),
    Field("exp_machine", "Experiment machine", "", "Experiment", "cat"),
    Field("exp_year", "Experiment year", "", "Experiment", "cat"),
    Field("exp_month", "Experiment month", "", "Experiment", "cat"),
]
# Fields stored on the Trial itself (attributes) or in Trial.extra - known
# for every trial AND for the empty series/experiment rows.
ATTR_KEYS = ("machine", "jet", "series", "experiment", "year")
EXTRA_KEYS = ("owner", "month", "trial_year", "trial_month", "exp_productgroup", "exp_ordertype",
              "exp_project", "exp_owner", "exp_machine", "exp_year", "exp_month")
# Time fields: labels sort chronologically ("2026-03"), gaps are filled in charts
TIME_KEYS = {"year": "year", "month": "month", "trial_year": "year", "trial_month": "month",
             "exp_year": "year", "exp_month": "month"}
# Lab machines for "Tested on" - the same list and names as the Statistics
# page (ui/stats_suite_queries.py uses this one): DISTINCT TrialID per table.
LAB_MACHINE_TABLES = [
    ("tbllabortiter", "Titer"),
    ("tbllaborstatimatm", "Statimat M"),
    ("tbllaborstatimatds", "Statimat DS"),
    ("tbllaborekb", "EKB"),
    ("tbllaboritematlab", "Itemat Lab"),
    ("tbllaboritematplus", "Itemat Plus"),
    ("tbllabordtyomat", "DTYoMat"),
    ("tbllaborrapid600", "Rapid 600"),
    ("tbllaborheissluftschrumpf", "Hot Air Shrinkage"),
    ("tbllaborkochschrumpf", "Hot Water Shrinkage"),
    ("tbllaboratyshrinkage", "ATY Shrinkage"),
    ("tbllaboratyomat", "ATYoMat"),
    ("tbllaborwaterbath", "Waterbath"),
]
# Data of the jet used in the trial (tblTrial.JetID -> tbljets), Nutzerwunsch
# 2026-10-30. (column, title, unit, lookup table, lookup label column);
# a lookup turns the id into its name -> list field, otherwise number field
# (text columns marked "text" are list fields as they are).
JET_COLUMNS = [
    ("Hersteller", "Jet manufacturer", "", "tbljethersteller", "Hersteller"),
    ("Serie", "Jet series", "", "tblseries", "Series"),
    ("JetGroupID", "Jet group", "", "tbljetgroup", "GroupName"),
    ("JetTypeID", "Jet type", "", "tbljettype", "Name"),
    ("Prozess", "Jet process", "", "tblprozesse", "Prozess"),
    ("Werkstoff", "Jet material", "", "tblwerkstoff", "Name"),
    ("Rohling", "Jet blank", "", "tbljetrohling", "Nummer"),
    ("Entwicklungsname", "Development name", "", "text", None),
    ("Prototypenname", "Prototype name", "", "text", None),
    ("Luftbohrung", "Air hole diameter", "mm", None, None),
    ("AnzahlLuftbohrungen", "Number of air holes", "", None, None),
    ("WinkelLuftbohrung", "Air hole angle", "°", None, None),
    ("Luftkanalform", "Air channel shape", "", "tblairchannelshape", "AirChannelShape"),
    ("Luftverbrauch", "Jet air factor", "Nm³/h", None, None),
    ("YarnChannelShape", "Yarn channel shape", "", "tblyarnchannelshape", "Shape"),
    ("GarnkanalBreite", "Yarn channel width", "mm", None, None),
    ("GarnkanalTiefe", "Yarn channel depth", "mm", None, None),
    ("GarnkanalRadius", "Yarn channel radius", "mm", None, None),
    ("GarnkanalLängeEingang", "Yarn channel length inlet", "mm", None, None),
    ("GarnkanalLängeAusgang", "Yarn channel length outlet", "mm", None, None),
    ("GebogenerKanal", "Curved channel", "", "yesno", None),
    ("Kreisbogen", "Arc", "mm", None, None),
    ("Wirbelkammer", "Swirl chamber", "", "tblwirbelkammer", "Wirbelkammer"),
    ("WirbelkammerBreite", "Swirl chamber width", "mm", None, None),
    ("WirbelkammerRadius", "Swirl chamber radius", "mm", None, None),
    ("WirbelkammerKreissehne", "Swirl chamber chord", "mm", None, None),
    ("AbstandSchlitzEingang", "Slot distance inlet", "mm", None, None),
    ("AbstandSchlitzAusgang", "Slot distance outlet", "mm", None, None),
    ("SchlitzbreiteEingang", "Slot width inlet", "mm", None, None),
    ("SchlitzbreiteAusgang", "Slot width outlet", "mm", None, None),
    ("SchanzeEingang", "Ramp inlet", "", "text", None),
    ("KonusForm", "Cone shape", "", "tblkonusform", "KonusForm"),
    ("WinkelKonusI", "Cone angle I", "°", None, None),
    ("WinkelKonusII", "Cone angle II", "°", None, None),
    ("RadiusKonus", "Cone radius", "mm", None, None),
    ("AbstandLBKonus", "Distance air hole – cone", "mm", None, None),
    ("AbstandEinlaufKonusZuLB", "Distance inlet cone – air hole", "mm", None, None),
    ("Konuslänge", "Cone length", "mm", None, None),
    ("LängeDK", "Length DK", "mm", None, None),
    ("TiterVon", "Jet titer range from", "dtex", None, None),
    ("TiterBis", "Jet titer range to", "dtex", None, None),
    ("IdealTiter", "Jet ideal titer", "dtex", None, None),
    ("WindingSpeed", "Jet winding speed", "m/min", None, None),
    ("YarnTensionAfterJetFrom", "Jet tension after jet from", "cN", None, None),
    ("YarnTensionAfterJetTo", "Jet tension after jet to", "cN", None, None),
]


def jet_fields() -> List[Field]:
    """Jet fields whose column exists in tbljets."""
    out = []
    for col, title, unit, lookup, _lab in JET_COLUMNS:
        if not _column_exists("tbljets", col):
            continue
        kind = "cat" if lookup else "num"
        out.append(Field("jet_" + _slug(col), title, unit, "Jet", kind,
                         source={"jet_col": col, "lookup": lookup, "label": _lab}))
    return out


def _slug(col: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in col.lower().replace("ä", "ae"))


# axis keys of tblSmartChartAxis that make no sense here (pseudo rows, ids)
_SKIP_AXES = {"trial_nr", "customgroup", "jet_air_consumption", "jetcal_pressure", "air_cons"}
_MACHINE_TABLES = {"tbltrial", "tbltrialsettings", "tbljets"}


LAB_GROUP = "Lab"
LAB_TABLE_GROUPS = {name for table, name in TABLE_GROUPS.items() if table.startswith("tbllabor")}


def parent_group(group: str) -> Optional[str]:
    """Lab tables are shown inside one "Lab" folder (Nutzerwunsch 2026-10-30)."""
    return LAB_GROUP if group in LAB_TABLE_GROUPS else None


def group_tree(fields: Iterable[Field]) -> List[Tuple[str, List[str]]]:
    """[(top group, [sub groups])] in display order. A top group without
    sub groups holds its fields directly; "Lab" may have both."""
    order = group_order(fields)
    tops: List[Tuple[str, List[str]]] = []
    index: Dict[str, int] = {}
    for g in order:
        parent = parent_group(g)
        top = parent or g
        if top not in index:
            index[top] = len(tops)
            tops.append((top, []))
        if parent:
            tops[index[top]][1].append(g)
    return tops


def group_order(fields: Iterable[Field]) -> List[str]:
    """Groups in display order: Yarn, Jet, Machine…, then the lab tables
    alphabetically, General last."""
    present = []
    for f in fields:
        if f.group not in present:
            present.append(f.group)
    late = ("Experiment", "Time", "General")
    first = [g for g in GROUPS if g in present and g not in late and g != LAB_GROUP]
    lab = ([LAB_GROUP] if LAB_GROUP in present else []) + sorted(g for g in present if g in LAB_TABLE_GROUPS)
    rest = sorted(g for g in present if g not in GROUPS and g not in LAB_TABLE_GROUPS)
    return first + lab + rest + [g for g in late if g in present]


def _pretty(col: str) -> str:
    """'ElongationCV' -> 'Elongation CV', '1stHeaterT1' -> '1st Heater T1'."""
    out = ""
    for i, ch in enumerate(col.replace("_", " ")):
        prev = col[i - 1] if i else ""
        if i and ch.isupper() and (prev.islower() or prev.isdigit()) and out[-1:] != " ":
            out += " "
        out += ch
    return " ".join(out.split())


def table_fields(curated: set) -> List[Field]:
    """Every number column of the tables in TABLE_GROUPS that is not already
    a curated axis. Tables with a "Tension" column (Itemat) get one field per
    tension - an average over all tensions would mean nothing."""
    try:
        from db.connection import fetch_all
        names = list(TABLE_GROUPS)
        ph = ",".join(["?"] * len(names))
        cols = fetch_all(
            "SELECT TABLE_NAME AS t, COLUMN_NAME AS c, DATA_TYPE AS d FROM information_schema.columns "
            f"WHERE table_schema = DATABASE() AND LOWER(TABLE_NAME) IN ({ph}) ORDER BY TABLE_NAME, ORDINAL_POSITION",
            names)
    except Exception as e:
        logger.warning("trial_explorer: table fields not loaded: %s", e)
        return []
    by_table: Dict[str, List[Tuple[str, str]]] = {}
    for r in cols:
        by_table.setdefault(str(r["t"]).lower(), []).append((str(r["c"]), str(r["d"]).lower()))
    out: List[Field] = []
    for table, columns in by_table.items():
        lower = {c.lower() for c, _ in columns}
        if table != "tbltrial" and "trialid" not in lower:
            continue
        group = TABLE_GROUPS[table]
        tensions: List[Optional[float]] = [None]
        if "tension" in lower:
            try:
                from db.connection import fetch_all
                tensions = sorted({float(r["v"]) for r in fetch_all(
                    f"SELECT DISTINCT Tension AS v FROM {table} WHERE Tension IS NOT NULL") if r.get("v") is not None})[:8]
            except Exception:
                tensions = []
        for col, dtype in columns:
            cl = col.lower()
            if dtype not in _NUM_TYPES or cl in _SKIP_COLUMNS or cl.endswith("id") or cl == "tension":
                continue
            for ten in tensions:
                cond = None if ten is None else f"Tension = {ten:g}"
                if (table, cl, _norm_cond(cond)) in curated:
                    continue
                title = _pretty(col) + ("" if ten is None else f" @ {ten:g} cN/dtex")
                key = f"t_{_slug(table)}__{_slug(col)}" + ("" if ten is None else f"__t{ten:g}".replace(".", "_"))
                out.append(Field(key, title, "", group, "num",
                                 source={"main_table": table, "alt_table": None, "field": col, "condition": cond}))
    return out


def _norm_cond(cond: Optional[str]) -> str:
    """'Tension = 0.30' and 'Tension = 0.3' are the same condition."""
    if not cond:
        return ""
    parts = str(cond).replace(" ", "").lower().split("=")
    if len(parts) == 2:
        try:
            return f"{parts[0]}={float(parts[1]):g}"
        except ValueError:
            pass
    return str(cond).replace(" ", "").lower()


def build_catalog() -> List[Field]:
    """All fields available in this database, in display order."""
    fields: List[Field] = list(YARN_FIELDS) + list(GENERAL_FIELDS) + jet_fields()
    try:
        from ui.report_queries import _load_axes_from_db
        db_y, db_x, _g = _load_axes_from_db()
    except Exception as e:
        logger.warning("trial_explorer: axes not loaded: %s", e)
        db_y, db_x = None, None
    seen = {f.key for f in fields}
    for a in list(db_x or []) + list(db_y or []):
        key = str(a.get("key") or "")
        if not key or key.lower() in _SKIP_AXES or key in seen:
            continue
        if a.get("join_sql") or a.get("is_group_by"):
            continue
        main = str(a.get("main_table") or "").lower()
        if key == "air_cons_real":
            f = Field(key, a.get("title") or "Air consumption", a.get("unit") or "", "Machine", "num",
                      source={"computed": "air_cons_real"})
        else:
            if not _column_exists(main, a.get("field")) and not (
                    a.get("alt_table") and _column_exists(str(a["alt_table"]).lower(), a.get("field"))):
                continue
            f = Field(key, str(a.get("title") or key), str(a.get("unit") or ""),
                      TABLE_GROUPS.get(main) or ("Machine" if main in _MACHINE_TABLES else "Lab"), "num",
                      source={"main_table": a.get("main_table"), "alt_table": a.get("alt_table"),
                              "field": a.get("field"), "condition": a.get("condition")})
        fields.append(f)
        seen.add(key)
    curated = set()
    for f in fields:
        src = f.source
        for tbl in (src.get("main_table"), src.get("alt_table")):
            if tbl and src.get("field"):
                curated.add((str(tbl).lower(), str(src["field"]).lower(), _norm_cond(src.get("condition"))))
    fields += [f for f in table_fields(curated) if f.key not in seen]
    order = {g: i for i, g in enumerate(group_order(fields))}
    return sorted(fields, key=lambda f: order.get(f.group, 99))


def _column_exists(table: str, column: Any) -> bool:
    if not table or not column:
        return False
    try:
        from db.connection import get_columns_map, table_exists
        return table_exists(table) and str(column).lower() in get_columns_map(table)
    except Exception:
        return False


def catalog_by_key(fields: Iterable[Field]) -> Dict[str, Field]:
    return {f.key: f for f in fields}


# ── dataset ──────────────────────────────────────────────────────────────
@dataclass
class Ply:
    ply: str
    use: str            # "Core" / "Effect" / ... / ""
    values: Dict[str, Any]   # yarn_* field key -> value


@dataclass
class Trial:
    id: int
    nr: int
    series_id: Optional[int]
    exp_pk: Optional[int]
    experiment: str
    series: str          # "2026-41-007.03 PES trials"
    machine: str
    jet: str
    year: str
    plies: List[Ply] = dc_field(default_factory=list)
    extra: Dict[str, Any] = dc_field(default_factory=dict)   # air pressure, jet factor (computed fields)
    empty: bool = False   # placeholder for a series without trials / an experiment without series


@dataclass
class Result:
    ids: List[int]
    matched: Dict[int, Optional[Ply]]

    @property
    def count(self) -> int:
        return len(self.ids)


class TrialDataset:
    """All real trials with plies; field values loaded lazily per field.
    `loader(field) -> {trial_id: value}` can be replaced in tests."""

    def __init__(self, catalog: Sequence[Field], trials: Optional[List[Trial]] = None,
                 loader: Optional[Callable[[Field], Dict[int, Any]]] = None):
        self.fields = catalog_by_key(catalog)
        loaded = trials if trials is not None else _load_trials()
        self.trials: List[Trial] = [t for t in loaded if not t.empty]
        self.empties: List[Trial] = [t for t in loaded if t.empty]
        self.by_id: Dict[int, Trial] = {t.id: t for t in loaded}
        self._loader = loader or self._load_field
        self._cache: Dict[str, Dict[int, Any]] = {}

    # ---- values ----
    def values(self, key: str) -> Dict[int, Any]:
        """{trial id: value} of a trial-level field (cached)."""
        if key not in self._cache:
            f = self.fields[key]
            if f.key in ATTR_KEYS:
                self._cache[key] = {t.id: getattr(t, f.key) or None for t in self.trials + self.empties}
            elif f.key in EXTRA_KEYS:
                self._cache[key] = {t.id: t.extra.get(f.key) or None for t in self.trials + self.empties}
            else:
                try:
                    # calculated fields always come from their formula (also with a test loader)
                    self._cache[key] = self._load_calc(f) if f.source.get("formula") is not None else self._loader(f)
                except Exception as e:
                    logger.warning("trial_explorer: field %s not loaded: %s", key, e)
                    self._cache[key] = {}
        return self._cache[key]

    def value(self, key: str, tid: int, matched: Optional[Ply] = None) -> Any:
        f = self.fields[key]
        if f.level == "yarn":
            ply = matched if matched is not None else default_ply(self.by_id[tid].plies, "any")
            return ply.values.get(key) if ply is not None else None
        return self.values(key).get(tid)

    def _jet_rows(self) -> Dict[int, Dict[str, Any]]:
        """tbljets once per dataset: {jet id: {lower column: value}}."""
        if not hasattr(self, "_jets"):
            try:
                from db.connection import fetch_all
                self._jets = {int(r["ID"]): {str(k).lower(): v for k, v in r.items()}
                              for r in fetch_all("SELECT * FROM tbljets")}
            except Exception as e:
                logger.warning("trial_explorer: jets not loaded: %s", e)
                self._jets = {}
        return self._jets

    def _load_jet_field(self, f: Field) -> Dict[int, Any]:
        col = str(f.source["jet_col"]).lower()
        lookup, label = f.source.get("lookup"), f.source.get("label")
        names: Dict[Any, str] = {}
        if lookup and lookup not in ("text", "yesno"):
            names = _lookup(lookup, "ID", label)
        jets = self._jet_rows()
        out: Dict[int, Any] = {}
        for t in self.trials:
            row = jets.get(t.extra.get("jet_id"))
            if row is None:
                continue
            v = row.get(col)
            if v is None or v == "":
                continue
            if lookup == "yesno":
                out[t.id] = "Yes" if int(v or 0) else "No"
            elif lookup == "text":
                out[t.id] = str(v).strip() or None
            elif lookup:
                try:
                    out[t.id] = names.get(int(v)) or str(v)
                except (TypeError, ValueError):
                    out[t.id] = str(v)
            else:
                fv = _f(v)
                # 0 = "not entered" in tbljets (no 0 mm hole / 0 dtex range); angles may be 0
                if fv is not None and (fv != 0 or f.unit == "°"):
                    out[t.id] = fv
        return out

    def set_calc_fields(self, defs: Sequence[Dict[str, Any]]) -> List[Field]:
        """(Re)register calculated fields {"key", "name", "unit", "formula"}
        (formula with {field key} placeholders). Returns the Field objects."""
        for k in [k for k, f in self.fields.items() if f.group == CALC_GROUP]:
            self.fields.pop(k, None)
            self._cache.pop(k, None)
        out = []
        for d in defs or []:
            key = str(d.get("key") or "")
            if not key.startswith("calc_"):
                continue
            f = Field(key, str(d.get("name") or key), str(d.get("unit") or ""), CALC_GROUP, "num",
                      source={"formula": str(d.get("formula") or "")})
            self.fields[key] = f
            out.append(f)
        return out

    def _load_calc(self, f: Field) -> Dict[int, float]:
        from db.formula import compile_formula, evaluate
        code, keys = compile_formula(f.source["formula"], self.fields, exclude=f.key)
        maps = {k: (self.values(k) if self.fields[k].level != "yarn" else None) for k in keys}
        out: Dict[int, float] = {}
        for t in self.trials:
            vals = {}
            for k in keys:
                vals[k] = _f(maps[k].get(t.id)) if maps[k] is not None else _f(self.value(k, t.id))
            r = evaluate(code, vals)
            if r is not None:
                out[t.id] = r
        return out

    def _load_field(self, f: Field) -> Dict[int, Any]:
        if f.source.get("formula") is not None:
            return self._load_calc(f)
        if f.source.get("jet_col"):
            return self._load_jet_field(f)
        if f.source.get("computed") == "tested_on":
            return _tested_on()
        if f.source.get("computed") == "air_cons_real":
            out = {}
            for t in self.trials:
                jf, ap = t.extra.get("jet_factor"), t.extra.get("air_pressure")
                if jf is not None and ap is not None:
                    out[t.id] = round(jf * (ap + 1), 2)
            return out
        out = _avg_per_trial(f.source.get("main_table"), f.source.get("field"), f.source.get("condition"))
        alt = f.source.get("alt_table")
        if alt:
            for tid, v in _avg_per_trial(alt, f.source.get("field"), f.source.get("condition")).items():
                out.setdefault(tid, v)
        return out

    # ---- filtering ----
    def apply(self, filters: Sequence[Dict[str, Any]], ply_scope: str = "any",
              skip_key: Optional[str] = None, include_empty: bool = False) -> Result:
        """Trials matching all filters (optionally ignoring one key, for the
        histogram/counts of that field). include_empty: also the empty
        series/experiment rows (for counting series/experiments)."""
        id_sets = [set(f["ids"]) for f in filters if f.get("ids") is not None]   # lasso / selection
        flt = [f for f in filters if f.get("key") in self.fields and f.get("key") != skip_key]
        yarn_f = [f for f in flt if self.fields[f["key"]].level == "yarn"]
        trial_f = [f for f in flt if self.fields[f["key"]].level != "yarn"]
        maps = {f["key"]: self.values(f["key"]) for f in trial_f}
        ids: List[int] = []
        matched: Dict[int, Optional[Ply]] = {}
        for t in (self.trials + self.empties if include_empty else self.trials):
            if id_sets and not all(t.id in ids for ids in id_sets):
                continue
            if not all(_passes(self.fields[f["key"]], maps[f["key"]].get(t.id), f) for f in trial_f):
                continue
            plies = scoped_plies(t.plies, ply_scope)
            if yarn_f:
                hit = next((p for p in plies
                            if all(_passes(self.fields[f["key"]], p.values.get(f["key"]), f) for f in yarn_f)),
                           None)
                if hit is None:
                    continue
                matched[t.id] = hit
            else:
                matched[t.id] = default_ply(t.plies, ply_scope)
            ids.append(t.id)
        return Result(ids, matched)

    def summary(self, res: Result) -> Dict[str, int]:
        ts = [self.by_id[i] for i in res.ids]
        return {"trials": len(ts), "series": len({t.series_id for t in ts}),
                "machines": len({t.machine for t in ts if t.machine}),
                "jets": len({t.jet for t in ts if t.jet})}

    def field_values(self, key: str, filters, ply_scope: str = "any") -> List[Any]:
        """Values of one field over the trials matching all OTHER filters -
        for the histogram / category counts in "Add filter". Yarn fields:
        one value per scoped ply."""
        res = self.apply(filters, ply_scope, skip_key=key)
        f = self.fields[key]
        if f.level == "yarn":
            return [p.values.get(key) for i in res.ids for p in scoped_plies(self.by_id[i].plies, ply_scope)]
        m = self.values(key)
        return [m.get(i) for i in res.ids]


def scoped_plies(plies: Sequence[Ply], scope: str) -> List[Ply]:
    if scope == "core":
        return [p for p in plies if p.use.lower() == "core"]
    if scope == "effect":
        return [p for p in plies if p.use.lower() == "effect"]
    return list(plies)


def default_ply(plies: Sequence[Ply], scope: str = "any") -> Optional[Ply]:
    """The ply whose yarn represents the trial without yarn filters: within
    the scope, Core first, else the lowest ply number."""
    cand = scoped_plies(plies, scope) or (list(plies) if scope == "any" else [])
    if not cand:
        return None
    core = [p for p in cand if p.use.lower() == "core"]
    return (core or sorted(cand, key=lambda p: _ply_no(p.ply)))[0]


def _ply_no(ply: str) -> int:
    digits = "".join(ch for ch in str(ply or "") if ch.isdigit())
    return int(digits) if digits else 999


def _passes(f: Field, v: Any, flt: Dict[str, Any]) -> bool:
    if f.kind == "cat":
        wanted = flt.get("values") or []
        return not wanted or any(lab in wanted for lab in cat_labels(v))
    if v is None:
        return False
    try:
        x = float(v)
    except (TypeError, ValueError):
        return False
    lo, hi = flt.get("min"), flt.get("max")
    if not ((lo is None or x >= float(lo)) and (hi is None or x <= float(hi))):
        return False
    only = flt.get("only")
    if only:
        return any(abs(x - float(o)) <= 1e-6 * max(1.0, abs(x)) for o in only)
    step = flt.get("step")
    if step:
        q = x / float(step)
        return abs(q - round(q)) <= 1e-6 * max(1.0, abs(q))
    return True


def cat_label(v: Any) -> str:
    if isinstance(v, (list, tuple)):
        return ", ".join(cat_labels(v))
    s = "" if v is None else str(v).strip()
    return s or NONE_LABEL


def cat_labels(v: Any) -> List[str]:
    """All labels of a value - a list value ("Tested on") has one per entry."""
    if isinstance(v, (list, tuple)):
        labs = [cat_label(x) for x in v if x not in (None, "")]
        return labs or [NONE_LABEL]
    return [cat_label(v)]


# ── statistics for "Add filter" ──────────────────────────────────────────
def histogram(values: Iterable[Any], bins: int = 40) -> Dict[str, Any]:
    """{"lo","hi","counts":[...],"edges":[...]} over the numeric values;
    a nice rounded range, empty counts when there are no values."""
    xs = sorted(float(v) for v in values if _is_num(v))
    if not xs:
        return {"lo": None, "hi": None, "counts": [], "edges": [], "n": 0, "min": None, "max": None}
    # range from the 2nd to the 98th percentile so a few outliers (550 dtex
    # among 70-dtex yarns) don't squeeze everything into one bar; values
    # outside fall into the first/last bar
    if len(xs) >= 50:
        lo, hi = xs[int(len(xs) * 0.02)], xs[min(len(xs) - 1, int(len(xs) * 0.98))]
    else:
        lo, hi = xs[0], xs[-1]
    if hi == lo:
        hi = lo + 1
    step = _nice_step((hi - lo) / bins)
    lo = math.floor(lo / step) * step
    n = max(1, int(math.ceil((hi - lo) / step + 1e-9)))
    if hi >= lo + n * step:
        n += 1
    counts = [0] * n
    for x in xs:
        counts[max(0, min(n - 1, int((x - lo) // step)))] += 1
    edges = [round(lo + i * step, 6) for i in range(n + 1)]
    return {"lo": edges[0], "hi": edges[-1], "counts": counts, "edges": edges, "n": len(xs),
            "min": xs[0], "max": xs[-1]}


def _nice_step(raw: float) -> float:
    if raw <= 0:
        return 1.0
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def category_counts(values: Iterable[Any]) -> List[Tuple[str, int]]:
    counts: Dict[str, int] = {}
    for v in values:
        for lab in cat_labels(v):
            counts[lab] = counts.get(lab, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower()))


def _is_num(v: Any) -> bool:
    if v is None or isinstance(v, bool):
        return False
    try:
        x = float(v)
    except (TypeError, ValueError):
        return False
    return not math.isnan(x)


def describe_selection(flt: Dict[str, Any]) -> str:
    n = len(flt.get("ids") or [])
    return f"Selected {n} trial{'s' if n != 1 else ''}"


def describe_filter(f: Field, flt: Dict[str, Any]) -> str:
    """Chip text, e.g. "End titer 70 – 80 dtex", "Material: PES, PA"."""
    if f.kind == "cat":
        vals = flt.get("values") or []
        shown = ", ".join(vals[:3]) + (f" +{len(vals) - 3}" if len(vals) > 3 else "")
        return f"{f.title}: {shown}" if vals else f"{f.title}: any"
    lo, hi = flt.get("min"), flt.get("max")
    unit = f" {f.unit}" if f.unit else ""
    fmt = lambda x: f"{float(x):g}"
    only = flt.get("only") or []
    if only:
        vals = sorted(float(o) for o in only)
        shown = ", ".join(fmt(v) for v in vals[:6]) + (f" +{len(vals) - 6}" if len(vals) > 6 else "")
        return f"{f.title}: {shown}{unit}"
    if lo is not None and hi is not None:
        txt = f"{f.title} {fmt(lo)} – {fmt(hi)}{unit}"
    elif lo is not None:
        txt = f"{f.title} ≥ {fmt(lo)}{unit}"
    elif hi is not None:
        txt = f"{f.title} ≤ {fmt(hi)}{unit}"
    else:
        txt = f"{f.title}: has a value"
    step = flt.get("step")
    if step:
        txt += " · whole numbers" if float(step) == 1 else f" · every {fmt(step)}"
    return txt


def distinct_values(values: Iterable[Any], lo: Optional[float] = None, hi: Optional[float] = None,
                    limit: int = 80) -> Optional[List[Tuple[float, int]]]:
    """[(value, count)] of the numbers between lo and hi, sorted; None when
    there are more than `limit` different values (picking makes no sense)."""
    counts: Dict[float, int] = {}
    for v in values:
        if not _is_num(v):
            continue
        x = round(float(v), 6)
        if (lo is not None and x < lo) or (hi is not None and x > hi):
            continue
        counts[x] = counts.get(x, 0) + 1
        if len(counts) > limit:
            return None
    return sorted(counts.items())


# ── loaders (DB) ─────────────────────────────────────────────────────────
def _avg_per_trial(table: Optional[str], field: Optional[str], condition: Optional[str]) -> Dict[int, float]:
    """AVG per trial like the series report (0 and NULL = no value)."""
    if not table or not field or not _column_exists(str(table).lower(), field):
        return {}
    from db.connection import fetch_all, get_columns_map
    cols = get_columns_map(table)
    real = cols.get(str(field).lower(), field)
    id_col = "ID" if str(table).lower() == "tbltrial" else "TrialID"
    cond = f" AND {condition}" if condition else ""
    rows = fetch_all(
        f"SELECT {id_col} AS tid, AVG(`{real}`) AS val FROM {table} "
        f"WHERE `{real}` IS NOT NULL AND `{real}` <> 0{cond} GROUP BY {id_col}")
    out: Dict[int, float] = {}
    for r in rows:
        try:
            if r.get("tid") is not None and r.get("val") is not None:
                out[int(r["tid"])] = float(r["val"])
        except (TypeError, ValueError):
            pass
    return out


def _lookup(table: str, id_col: str, label_sql: str) -> Dict[int, str]:
    try:
        from db.connection import fetch_all, table_exists
        if not table_exists(table):
            return {}
        return {int(r["i"]): str(r["l"] or "").strip()
                for r in fetch_all(f"SELECT {id_col} AS i, {label_sql} AS l FROM {table}")}
    except Exception as e:
        logger.warning("trial_explorer: lookup %s: %s", table, e)
        return {}


def _ym(d: Any) -> Tuple[str, str]:
    """(year, "YYYY-MM") of a date/datetime, ("", "") without one."""
    if hasattr(d, "year") and hasattr(d, "month"):
        return str(d.year), f"{d.year:04d}-{d.month:02d}"
    return "", ""


def _load_experiments() -> Dict[int, Dict[str, Any]]:
    """{experiment pk: {name, exp_* fields, jahr}} incl. start month/owner =
    its earliest series (the same rule as the Statistics page)."""
    from db.connection import fetch_all
    try:
        rows = fetch_all("SELECT ID, ExperimentID, Jahr, Produktgruppe, Bestellungstyp, Projekt, Maschine "
                         "FROM tblExperimente")
    except Exception as e:      # older databases: names only
        logger.warning("trial_explorer: experiment details not loaded: %s", e)
        rows = fetch_all("SELECT ID, ExperimentID FROM tblExperimente")
    groups = _lookup("tblproduktgruppe", "ID", "Produktgruppe")
    types = _lookup("tblbestellungstyp", "ID", "Bestellungstyp")
    projects = _lookup("tblproject", "ID", "CONCAT(COALESCE(ProjectNumber,''), ' - ', COALESCE(ProjectName,''))")
    machines = _lookup("tblMaschine", "ID", "Maschine")
    name_of = lambda m, v: m.get(int(v)) if _is_num(v) else None
    out: Dict[int, Dict[str, Any]] = {}
    for r in rows:
        jahr = r.get("Jahr")
        out[int(r["ID"])] = {
            "name": str(r.get("ExperimentID") or "").strip(),
            "jahr": str(int(jahr)) if _is_num(jahr) and int(jahr) > 0 else "",
            "exp_productgroup": name_of(groups, r.get("Produktgruppe")),
            "exp_ordertype": name_of(types, r.get("Bestellungstyp")),
            "exp_project": (name_of(projects, r.get("Projekt")) or "").strip(" -") or None,
            "exp_machine": name_of(machines, r.get("Maschine")),
        }
    return out


def _tested_on() -> Dict[int, Tuple[str, ...]]:
    """{trial id: (lab machine, ...)} - every lab table with a row for the trial."""
    from db.connection import fetch_all, table_exists
    found: Dict[int, List[str]] = {}
    for table, name in LAB_MACHINE_TABLES:
        try:
            if not table_exists(table):
                continue
            for r in fetch_all(f"SELECT DISTINCT TrialID AS tid FROM {table} WHERE TrialID IS NOT NULL"):
                found.setdefault(int(r["tid"]), []).append(name)
        except Exception as e:
            logger.warning("trial_explorer: tested on %s: %s", table, e)
    return {tid: tuple(names) for tid, names in found.items()}


def _load_trials() -> List[Trial]:
    """Real trials (reference samples excluded) plus EMPTY rows for series
    without trials and experiments without series (see module doc)."""
    from db.connection import fetch_all
    from db.trial_reference import exclude_references_sql
    exps = _load_experiments()
    users = _lookup("tblUser", "ID", "TRIM(CONCAT(COALESCE(FirstName,''), ' ', COALESCE(LastName,'')))")
    machines = _lookup("tblMaschine", "ID", "Maschine")
    try:
        s_rows = fetch_all("SELECT ID, ExperimentID, SeriesName, CreationDate, MachineID, BacklogOwner "
                           "FROM tblTrialSeries")
    except Exception as e:
        logger.warning("trial_explorer: series owner not loaded: %s", e)
        s_rows = fetch_all("SELECT ID, ExperimentID, SeriesName, CreationDate, MachineID FROM tblTrialSeries")
    series: Dict[int, Dict[str, Any]] = {}
    first_of_exp: Dict[int, Tuple[Any, int]] = {}
    for r in s_rows:
        sid = int(r["ID"])
        exp_pk = int(r["ExperimentID"]) if _is_num(r.get("ExperimentID")) else None
        exp = exps.get(exp_pk, {}) if exp_pk is not None else {}
        sname = str(r.get("SeriesName") or "").strip()
        created = r.get("CreationDate")
        year, month = _ym(created)
        owner = users.get(int(r["BacklogOwner"])) if _is_num(r.get("BacklogOwner")) else None
        series[sid] = {"exp_pk": exp_pk, "experiment": exp.get("name", ""),
                       "series": f"{exp['name']}.{sname}" if exp.get("name") else sname,
                       "machine": machines.get(int(r["MachineID"]), "") if _is_num(r.get("MachineID")) else "",
                       "year": year or exp.get("jahr", ""), "month": month, "created": created,
                       "owner": owner or None}
        if exp_pk is not None and hasattr(created, "year"):
            best = first_of_exp.get(exp_pk)
            if best is None or (created, sid) < best:
                first_of_exp[exp_pk] = (created, sid)
    # experiment start and owner = earliest series; without a dated series: Jahr
    for pk, exp in exps.items():
        first = first_of_exp.get(pk)
        if first is not None:
            exp["exp_year"], exp["exp_month"] = _ym(first[0])
            exp["exp_owner"] = series[first[1]]["owner"]
        else:
            exp["exp_year"], exp["exp_month"], exp["exp_owner"] = exp.get("jahr", ""), "", None
    exp_keys = ("exp_productgroup", "exp_ordertype", "exp_project", "exp_owner", "exp_machine",
                "exp_year", "exp_month")

    def extras(s: Dict[str, Any]) -> Dict[str, Any]:
        exp = exps.get(s["exp_pk"], {}) if s.get("exp_pk") is not None else {}
        out = {"owner": s.get("owner"), "month": s.get("month") or None}
        out.update({k: exp.get(k) or None for k in exp_keys})
        return out

    rows = fetch_all(
        "SELECT T.ID AS id, T.Versuchsnummer AS nr, T.TrialSeriesID AS sid, T.AirPressure AS ap, T.JetID AS jet_id, "
        "T.Timestamp AS ts, J.Jet AS jet, J.Luftverbrauch AS jf "
        "FROM tblTrial T "
        "LEFT JOIN tbljets J ON J.ID = T.JetID "
        f"WHERE T.TrialSeriesID IS NOT NULL AND {exclude_references_sql('T')}")
    trials: Dict[int, Trial] = {}
    for r in rows:
        s = series.get(int(r["sid"])) or {"exp_pk": None, "experiment": "", "series": "", "machine": "",
                                          "year": "", "month": "", "created": None, "owner": None}
        t = Trial(
            id=int(r["id"]), nr=int(r.get("nr") or 0), series_id=int(r["sid"]), exp_pk=s["exp_pk"],
            experiment=s["experiment"], series=s["series"], machine=s["machine"],
            jet=str(r.get("jet") or "").strip(), year=s["year"],
        )
        t_year, t_month = _ym(r.get("ts") or s["created"])
        t.extra = {"air_pressure": _f(r.get("ap")), "jet_factor": _f(r.get("jf")),
                   "jet_id": int(r["jet_id"]) if r.get("jet_id") is not None else None,
                   **extras(s), "trial_year": t_year or s["year"] or None, "trial_month": t_month or None}
        trials[t.id] = t
    # empty rows: series without (real) trials, experiments without series
    with_trials = {t.series_id for t in trials.values()}
    empties: List[Trial] = []
    for sid, s in series.items():
        if sid in with_trials or s["exp_pk"] is None:
            continue
        e = Trial(id=-sid, nr=0, series_id=sid, exp_pk=s["exp_pk"], experiment=s["experiment"],
                  series=s["series"], machine=s["machine"], jet="", year=s["year"], empty=True)
        e.extra = extras(s)
        empties.append(e)
    exps_with_series = {s["exp_pk"] for s in series.values()}
    for pk, exp in exps.items():
        if pk in exps_with_series:
            continue
        e = Trial(id=-(10_000_000 + pk), nr=0, series_id=None, exp_pk=pk, experiment=exp["name"], series="",
                  machine=exp.get("exp_machine") or "", jet="", year=exp.get("jahr", ""), empty=True)
        e.extra = extras({"exp_pk": pk})
        empties.append(e)

    materials = _lookup("tblMaterial", "ID", "Material")
    yarn_types = _lookup("tblGarntyp", "ID", "Garntyp")
    uses = _lookup("tblYarnUse", "ID", "Name")
    ply_rows = fetch_all(
        "SELECT S.TrialID AS tid, S.Ply AS ply, S.YarnUseID AS use_id, Y.Name AS name, Y.Endtiter AS endtiter, "
        "Y.Titer AS titer, Y.NumberOfFilaments AS fil, Y.dpf AS dpf, Y.Material AS mat, Y.Garntyp AS gtyp "
        "FROM tblTrialSettings S JOIN tblYarn Y ON Y.ID = S.YarnID")
    seen = set()
    for r in ply_rows:
        t = trials.get(int(r["tid"])) if r.get("tid") is not None else None
        if t is None:
            continue
        use = uses.get(int(r["use_id"]), "") if r.get("use_id") is not None else ""
        key = (t.id, str(r.get("ply") or ""), str(r.get("name") or ""), use)
        if key in seen:
            continue
        seen.add(key)
        mat = materials.get(int(r["mat"]), "") if _is_num(r.get("mat")) else str(r.get("mat") or "")
        gtyp = yarn_types.get(int(r["gtyp"]), "") if _is_num(r.get("gtyp")) else str(r.get("gtyp") or "")
        t.plies.append(Ply(str(r.get("ply") or ""), use, {
            "yarn_material": mat or None, "yarn_type": gtyp or None,
            "yarn_endtiter": _f(r.get("endtiter")), "yarn_titer": _f(r.get("titer")),
            "yarn_filaments": _f(r.get("fil")), "yarn_dpf": _f(r.get("dpf")),
            "yarn_name": str(r.get("name") or "").strip() or None, "yarn_use": use or None,
        }))
    return sorted(trials.values(), key=lambda t: (t.series, t.nr)) + empties


def _f(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x
