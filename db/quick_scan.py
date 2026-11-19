"""quick_scan.py - Quick Scan of the Requirement Hub (ui/screen_quick_scan.py) without Qt (2026-11-13, moved out of
the screen for the web version; the desktop screen uses it).

Fields (tblRequirementField), lookup options, ad-hoc fields (any column of the allowed tables, registered in
tblRequirementField when a ruleset is saved), the evaluator (filters = must, targets = must / weighted / distance,
score 0-100 %), and rulesets (tblRequirementSet / tblRequirementRule; the weighted direction is coded into
sort_order = n*10 + 1/2/3 as before).

Table and column names of a field end up in SQL text: field dicts are built ONLY here from database rows
(field_id) or checked ad-hoc columns - callers from outside (the web) use resolve_field(), never their own dicts."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from db.connection import execute, execute_insert, fetch_all

OPERATORS = ["=", ">=", "<=", "between"]
EQUAL_DEFAULTS = {"titer", "filamente"}          # numeric filters that start with "=" instead of "between"
TARGET_TYPES = ["must", "weighted", "distance"]
DIRECTIONS = ["higher", "lower", "exact"]
_DIR_CODE = {"higher": 1, "lower": 2, "exact": 3}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def score_weighted(val: float, f: dict) -> float:
    """Score 0.0–1.0 basierend auf Zielwert und Richtung.

    direction='higher': je höher desto besser, Zielwert = 100%
    direction='lower':  je tiefer desto besser, Zielwert = 100%
    direction='exact':  genau Zielwert = 100%, Abweichung = Score fällt

    Normalisierung: der must-Bereich (value1/value2) dient als Skala.
    Werte innerhalb des Must-Bereichs bekommen Score 0–100%,
    Werte ausserhalb können über 100% hinausgehen (werden auf 100% gecapped).
    """
    target_val = f.get("target_val")
    direction  = f.get("direction", "higher")
    op         = f["operator"]
    v1         = f["value1"]
    v2         = f.get("value2")

    # Referenzbereich für Normalisierung
    if op == "between" and v2 is not None:
        lo, hi = v1, v2
    elif op == ">=":
        lo, hi = v1, v1 * 2 if v1 > 0 else 100.0
    elif op == "<=":
        lo, hi = 0.0, v1
    else:
        lo = hi = v1

    span = hi - lo if hi != lo else 1.0

    # Zielwert: falls nicht angegeben, aus Bereich ableiten
    if target_val is None:
        if direction == "higher":   target_val = hi
        elif direction == "lower":  target_val = lo
        else:                       target_val = (lo + hi) / 2

    if direction == "higher":
        # val >= target → 100%, linear abfallend unter target bis lo → 0%
        if val >= target_val:
            return 1.0
        elif val <= lo:
            return 0.0
        else:
            return (val - lo) / (target_val - lo) if target_val != lo else 1.0

    elif direction == "lower":
        # val <= target → 100%, linear abfallend über target bis hi → 0%
        if val <= target_val:
            return 1.0
        elif val >= hi:
            return 0.0
        else:
            return (hi - val) / (hi - target_val) if hi != target_val else 1.0

    else:  # exact
        # Abstand zum Zielwert, normalisiert auf Bereichsbreite
        dist = abs(val - target_val)
        return max(0.0, 1.0 - dist / (span / 2))



# ---------------------------------------------------------------------------
# JOIN resolver: reads tblsmartchartjoinpath
# ---------------------------------------------------------------------------
class JoinResolver:
    """Cached JOIN-Pfade aus tblsmartchartjoinpath.
    Unterstützt direkte TrialID-Verbindungen und mehrstufige Pfade via
    tbltrialseries / tblexperimente.
    """
    # Tabellen die direkt t.ID = source.TrialID verknüpft sind
    _DIRECT_TRIAL = frozenset()

    # Anchor-Alias im Haupt-SELECT
    _ANCHORS = {
        "tbltrial":       ("t",  "t.ID"),
        "tbltrialseries": ("ts", "ts.ID"),
        "tblexperimente": ("e",  "e.ID"),
        "tblyarn":        None,   # Sonderfall: via tsy
        "tbltrialsettings": None, # Sonderfall: direkt via TrialID
    }

    def __init__(self):
        self._paths: dict[str, str] = {}   # from_table → JoinSQL (FromTable=source → ToTable=tbltrial)
        self._loaded = False

    def ensure_loaded(self):
        if self._loaded:
            return
        try:
            rows = fetch_all(
                "SELECT FromTable, ToTable, JoinSQL FROM tblsmartchartjoinpath WHERE IsActive=1",
                []
            )
            for r in rows:
                frm = r["FromTable"].lower()
                to  = r["ToTable"].lower()
                # Wir interessieren uns für Pfade die zu tbltrial führen
                if to == "tbltrial":
                    self._paths[frm] = r["JoinSQL"]
                # Pfad von tbltrialseries → tblexperimente (für Lookup)
                if frm == "tbltrialseries" and to == "tblexperimente":
                    self._paths["_ts_to_exp"] = r["JoinSQL"]
        except Exception:
            pass
        self._loaded = True

    def get_exists_snippet(self, source_table: str, col: str, alias: str = "ax") -> str | None:
        """Gibt einen EXISTS-SQL-Snippet zurück der source_table.col über t.ID verknüpft.
        alias: Table-Alias im EXISTS-Subquery.
        Gibt None zurück wenn kein Pfad bekannt.
        """
        self.ensure_loaded()
        tbl = source_table.lower()

        # Direkt via TrialID (alle tbllabor* und tbltrialsettings)
        if tbl in self._paths:
            join_sql = self._paths[tbl]
            # JoinSQL ist z.B. "LEFT JOIN tbllabordtyomat ON tbllabordtyomat.TrialID = tbltrial.ID"
            # Wir brauchen daraus: EXISTS (SELECT 1 FROM tbllabordtyomat ax WHERE ax.TrialID = t.ID AND ax.`col` {cond})
            return f"EXISTS (SELECT 1 FROM `{source_table}` {alias} WHERE {alias}.TrialID = t.ID AND {{cond}})"

        # tbltrial direkt
        if tbl == "tbltrial":
            return "{{cond_direct}}"  # wird als direktes WHERE-Fragment behandelt

        # tblyarn via tbltrialsettings
        if tbl == "tblyarn":
            return (f"EXISTS (SELECT 1 FROM tbltrialsettings tset_ax "
                    f"JOIN `{source_table}` {alias} ON {alias}.ID = tset_ax.YarnID "
                    f"WHERE tset_ax.TrialID = t.ID AND {{cond}})")

        # tblexperimente via ts.ExperimentID
        if tbl == "tblexperimente":
            return "{{cond_exp}}"  # Sonderfall: ts.ExperimentID IN (...)

        return None

    def known_tables(self) -> list[str]:
        """Alle Tabellen für die ein JOIN-Pfad zu tbltrial bekannt ist."""
        self.ensure_loaded()
        base = list(self._paths.keys())
        extra = ["tbltrial", "tblyarn", "tblexperimente", "tbltrialsettings"]
        seen = set()
        result = []
        for t in base + extra:
            if t not in seen and not t.startswith("_"):
                seen.add(t)
                result.append(t)
        return sorted(result)


# Globale Instanz – einmalig geladen
_join_resolver = JoinResolver()


# ---------------------------------------------------------------------------
# Ad-hoc fields: any column of the allowed tables
# ---------------------------------------------------------------------------
ALLOWED_TABLES = [
    "tbltrial", "tbltrialseries", "tbltrialsettings", "tblexperimente", "tblyarn",
    "tbllaboritematlab", "tbllaboritematplus", "tbllabordtyomat", "tbllabortiter", "tbllaborstatimatds",
    "tbllaborstatimatm", "tbllaborwaterbath", "tbllaboratyshrinkage", "tbllaboratyomat", "tbllaborekb",
    "tbllaborheissluftschrumpf", "tbllaborkochschrumpf", "tbllaborrapid600", "tbljets", "tbljetrohling",
]

# system columns that are never offered as fields
SKIP_COLS = frozenset({
    "ID", "TrialID", "TrialSeriesID", "ExperimentID", "UserID", "User",
    "Timestamp", "GlobalID", "JetID", "HousingID", "WettingHeadID",
    "MachineID", "CreatedBy", "BacklogStatusID", "BacklogOwner",
    "OriginalJoker", "Rohling", "Hersteller", "JetGroupID", "JetTypeID",
    "Serie", "Wirbelkammer", "Luftkanalform", "YarnChannelShape",
    "KonusForm", "Werkstoff", "YarnID", "Garntyp", "Material",
    "YarnGroupID", "Maschine", "Produktgruppe", "Bestellungstyp",
    "ExperimentRequestID",
})


def adhoc_tables() -> List[str]:
    """Tables offered for ad-hoc fields (whitelist order, only those with a known path to the trial)."""
    known = _join_resolver.known_tables()
    return [t for t in ALLOWED_TABLES if t in known or t in ("tbltrial", "tblyarn", "tblexperimente")]


def adhoc_columns(table: str) -> List[Tuple[str, str]]:
    """[(column, data type)] of an allowed table without the system columns."""
    if table not in adhoc_tables():
        return []
    cols = fetch_all("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
                     "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s ORDER BY ORDINAL_POSITION", [table])
    return [(c["COLUMN_NAME"], c["DATA_TYPE"]) for c in cols if c["COLUMN_NAME"] not in SKIP_COLS]


def adhoc_field(table: str, column: str, label: str = "", unit: Optional[str] = None,
                tension: Optional[float] = None, check: bool = True) -> Dict[str, Any]:
    """Field dict of an ad-hoc column (field_id None until registered). check=True: table and column must be
    allowed and exist (ValueError otherwise)."""
    if check and column not in {c for c, _t in adhoc_columns(table)}:
        raise ValueError(f"Unknown column {table}.{column}")
    key = f"adhoc__{table}__{column}"
    if tension is not None:
        key += f"__{str(tension).replace('.', '_')}"
    return {"field_id": None, "field_key": key, "field_label": (label or "").strip() or column,
            "source_table_primary": table, "source_table_fallback": None, "source_column": column,
            "tension_filter": tension, "data_type": "float", "unit": (unit or "").strip() or None,
            "lookup_table": None, "lookup_col_value": None, "lookup_col_label": None, "_adhoc": True}


def ensure_registered(field: Dict[str, Any]) -> int:
    """Makes sure an ad-hoc field exists in tblRequirementField; returns its field_id (INSERT if new)."""
    key = field["field_key"]
    rows = fetch_all("SELECT field_id FROM tblrequirementfield WHERE field_key = %s", [key])
    if rows:
        field["field_id"] = rows[0]["field_id"]
        return field["field_id"]
    # execute_insert() instead of execute() + a separate LAST_INSERT_ID() (other pool connection, see CLAUDE.md)
    fid = execute_insert(
        "INSERT INTO tblrequirementfield "
        "(field_key, field_label, source_table_primary, source_table_fallback, "
        " source_column, tension_filter, data_type, unit, is_active, sort_order) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,1,999)",
        [key, field["field_label"], field["source_table_primary"], field.get("source_table_fallback"),
         field["source_column"], field.get("tension_filter"), field.get("data_type", "float"), field.get("unit")])
    field["field_id"] = fid
    return fid


# ---------------------------------------------------------------------------
# Fields
# ---------------------------------------------------------------------------
_FIELD_COLS = ("field_id", "field_key", "field_label", "source_table_primary", "source_table_fallback",
               "source_column", "tension_filter", "data_type", "unit", "lookup_table", "lookup_col_value",
               "lookup_col_label")


def _field_from_row(r: Dict[str, Any]) -> Dict[str, Any]:
    f = {k: r.get(k) for k in _FIELD_COLS}
    f["_adhoc"] = str(f.get("field_key") or "").startswith("adhoc__")
    return f


def load_fields() -> List[Dict[str, Any]]:
    """Active fields of tblRequirementField (desktop order)."""
    rows = fetch_all("SELECT * FROM tblRequirementField WHERE is_active=1 ORDER BY sort_order, field_label", [])
    return [_field_from_row(r) for r in rows or []]


def field_by_id(field_id: int) -> Optional[Dict[str, Any]]:
    rows = fetch_all("SELECT * FROM tblRequirementField WHERE field_id = %s", [field_id])
    return _field_from_row(rows[0]) if rows else None


def resolve_field(ref: Dict[str, Any]) -> Dict[str, Any]:
    """A field reference from outside -> field dict built here: {"field_id": n[, "tension": x]} or
    {"adhoc": {"table", "column", "label", "unit", "tension"}}. ValueError if unknown."""
    if ref.get("field_id") is not None:
        f = field_by_id(int(ref["field_id"]))
        if f is None:
            raise ValueError("Unknown field")
        if ref.get("tension") not in (None, "") and f.get("tension_filter") is not None:
            f["tension_filter"] = float(ref["tension"])
        return f
    a = ref.get("adhoc") or {}
    tension = a.get("tension")
    return adhoc_field(str(a.get("table") or ""), str(a.get("column") or ""), str(a.get("label") or ""),
                       a.get("unit"), float(tension) if tension not in (None, "") else None)


def lookup_options(field: Dict[str, Any]) -> List[Tuple[Any, str]]:
    """[(value, label)] of a lookup field (from its lookup table)."""
    lookup_table = field.get("lookup_table")
    col_value = field.get("lookup_col_value") or "ID"
    col_label = field.get("lookup_col_label") or col_value
    if not lookup_table:
        return []
    try:
        rows = fetch_all(f"SELECT `{col_value}` AS val, `{col_label}` AS lbl FROM `{lookup_table}` ORDER BY `{col_label}`", [])
        return [(r["val"], str(r["lbl"] or "")) for r in rows]
    except Exception:
        return []


def make_rule(field: Dict[str, Any], operator: str = "between", value1=None, value2=None, target_type: str = "must",
              weight=1.0, direction: str = "higher", target_val=None, section: str = "target") -> Optional[Dict[str, Any]]:
    """A filter / target row as the evaluator takes it, or None while it is incomplete (desktop get_filter of
    FilterRow / TargetRow). Filters are always "must"."""
    if field.get("data_type") == "lookup":
        ids = list(value1 or [])
        if not ids:
            return None
        return {"field": dict(field), "operator": "in", "value1": ids, "value2": None, "target_type": "must"}
    if operator not in OPERATORS:
        return None
    try:
        v1 = float(value1)
    except (TypeError, ValueError):
        return None
    v2 = None
    if operator == "between":
        try:
            v2 = float(value2)
        except (TypeError, ValueError):
            return None
    if section == "filter":
        return {"field": dict(field), "operator": operator, "value1": v1, "value2": v2, "target_type": "must"}
    tt = target_type if target_type in TARGET_TYPES else "must"
    w, d, tv = 1.0, "higher", None
    if tt == "weighted":
        try:
            w = float(weight)
        except (TypeError, ValueError):
            w = 1.0
        d = direction if direction in DIRECTIONS else "higher"
        try:
            tv = float(target_val)
        except (TypeError, ValueError):
            tv = None
    return {"field": dict(field), "operator": operator, "value1": v1, "value2": v2, "target_type": tt,
            "weight": w, "direction": d, "target_val": tv}


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------
class QuickScanEvaluator:

    def run(self, filter_list: list, target_list: list):
        """
        filter_list: Felder aus Filter-Sektion (immer must)
        target_list: Felder aus Target-Sektion (must/weighted/distance)
        """
        # Alle Filter sind must → EXISTS-Subqueries
        # Targets vom Typ must → ebenfalls EXISTS
        # Targets weighted/distance → nach Basis-Query per IN-Query auflösen

        must_targets    = [t for t in target_list if t["target_type"] == "must"]
        weighted_targets= [t for t in target_list if t["target_type"] == "weighted"]
        distance_targets= [t for t in target_list if t["target_type"] == "distance"]

        all_must = filter_list + must_targets

        # Lookup-Filter separat (IN-Logik)
        lookup_f = [f for f in all_must if f["field"].get("data_type") == "lookup"]
        non_lookup_must = [f for f in all_must if f["field"].get("data_type") != "lookup"]

        rows = self._base_query(non_lookup_must, lookup_f)
        if not rows:
            return [], weighted_targets, distance_targets

        # Lab-Werte für weighted + distance laden
        score_fields = weighted_targets + distance_targets
        if score_fields:
            trial_ids = [r["trial_id"] for r in rows]
            lab_map   = self._load_lab_values(trial_ids, score_fields)
            for row in rows:
                row.update(lab_map.get(row["trial_id"], {}))

        # Score berechnen – Trials mit NULL oder 0 für Target-Felder ausschliessen
        total_weight = sum(t["weight"] for t in weighted_targets) or 1.0
        scored_rows  = []
        for row in rows:
            skip  = False
            score = 0.0

            # Weighted: NULL oder 0 → ausschliessen
            for t in weighted_targets:
                key = t["field"]["field_key"]
                val = row.get(key)
                if val is None or val == 0:
                    skip = True
                    break
                contrib = score_weighted(val, t) * t["weight"]
                score  += contrib
                # Teilscore speichern für Tabellen-Anzeige
                row[f"_contrib_{key}"] = contrib
            if skip:
                continue

            # Distance: NULL oder 0 → ausschliessen
            for t in distance_targets:
                key = t["field"]["field_key"]
                val = row.get(key)
                if val is None or val == 0:
                    skip = True
                    break
            if skip:
                continue

            row["_score"] = round((score / total_weight) * 100, 1) if weighted_targets else None
            scored_rows.append(row)

        # Sortieren: erst nach Score desc, dann nach Experiment
        scored_rows.sort(key=lambda r: (
            -(r["_score"] or 0),
            r.get("experiment_id", ""),
        ))

        return scored_rows[:500], weighted_targets, distance_targets

    # ---- SQL helpers -------------------------------------------------------

    def _cond(self, col, f):
        op, v1, v2 = f["operator"], f["value1"], f["value2"]
        if op == "=":       return f"{col} = %s",              [v1]
        if op == ">=":      return f"{col} >= %s",             [v1]
        if op == "<=":      return f"{col} <= %s",             [v1]
        if op == "between": return f"{col} BETWEEN %s AND %s", [v1, v2]
        return "1=1", []

    def _build_filter_clause(self, f, alias_counter: list) -> tuple[str, list]:
        """Generiert WHERE-Klausel für ein beliebiges Feld via JoinResolver.
        alias_counter: [int] – wird inplace hochgezählt für eindeutige Aliasse.
        Gibt (sql_fragment, params) zurück.
        """
        fld          = f["field"]
        col          = fld["source_column"]
        source_table = (fld.get("source_table_primary") or "").lower()
        tension      = fld.get("tension_filter")
        alias_counter[0] += 1
        alias = f"ax{alias_counter[0]}"

        # Lookup-Typ: IN (id1, id2, ...)
        if fld.get("data_type") == "lookup":
            selected_ids = f.get("value1") or []
            if not selected_ids:
                return "1=1", []
            placeholders = ",".join(["%s"] * len(selected_ids))
            if source_table == "tblyarn":
                sql = (f"EXISTS (SELECT 1 FROM tbltrialsettings tset_{alias} "
                       f"JOIN `{fld['source_table_primary']}` {alias} "
                       f"ON {alias}.ID = tset_{alias}.YarnID "
                       f"WHERE tset_{alias}.TrialID = t.ID "
                       f"AND {alias}.`{col}` IN ({placeholders}))")
            elif source_table == "tbltrial":
                sql = f"t.`{col}` IN ({placeholders})"
            elif source_table == "tblexperimente":
                sql = f"ts.ExperimentID IN ({placeholders})"
            else:
                # IN (subquery) instead of a correlated EXISTS - see the note at the numeric case below
                sql = (f"t.ID IN (SELECT {alias}.TrialID FROM `{fld['source_table_primary']}` {alias} "
                       f"WHERE {alias}.`{col}` IN ({placeholders}))")
            return sql, list(selected_ids)

        # Numerischer Filter
        # Only apply Tension filter to tables that actually have a Tension column.
        # t_cond is evaluated PER TABLE so the fallback table is checked independently.
        _TENSION_TABLES = {
            "tbllaboritematlab", "tbllaboritematplus",
            "tbllabordtyomat", "tbllaboratyomat",
        }

        def _t_cond_for(tbl_name: str, tbl_alias: str) -> str:
            if tension is not None and tbl_name.lower() in _TENSION_TABLES:
                return f" AND {tbl_alias}.`Tension` = {tension}"
            return ""

        t_cond = _t_cond_for(source_table, alias)

        if source_table == "tbltrial":
            cond, p = self._cond(f"t.`{col}`", f)
            return cond, p

        if source_table == "tblyarn":
            cond, p = self._cond(f"{alias}.`{col}`", f)
            sql = (f"EXISTS (SELECT 1 FROM tbltrialsettings tset_{alias} "
                   f"JOIN tblyarn {alias} ON {alias}.ID = tset_{alias}.YarnID "
                   f"WHERE tset_{alias}.TrialID = t.ID AND {cond})")
            return sql, p

        if source_table == "tbltrialseries":
            cond, p = self._cond(f"ts.`{col}`", f)
            return cond, p

        if source_table == "tblexperimente":
            cond, p = self._cond(f"e.`{col}`", f)
            return cond, p

        # Alle anderen: direkt via TrialID (tbllabor*, tbltrialsettings, ...)
        # "t.ID IN (SELECT TrialID ... WHERE cond)" = the same trials as "EXISTS (... WHERE TrialID = t.ID AND cond)",
        # but MySQL computes the list once. The correlated EXISTS scanned the whole lab table for every trial:
        # tbllaboritematlab has no index on TrialID (57'000 rows x 14'000 trials, 320 s on dev_local for
        # "Knoten/m >= 80", 2026-11-19).
        cond, p = self._cond(f"{alias}.`{col}`", f)
        sql = (f"t.ID IN (SELECT {alias}.TrialID FROM `{fld['source_table_primary']}` {alias} "
               f"WHERE {cond}{t_cond})")

        # Fallback-Tabelle: tension guard evaluated independently for the fallback table
        fallback = fld.get("source_table_fallback")
        if fallback:
            alias2 = f"{alias}b"
            t_cond2 = _t_cond_for(fallback, alias2)
            cond2, p2 = self._cond(f"{alias2}.`{col}`", f)
            sql2 = (f"t.ID IN (SELECT {alias2}.TrialID FROM `{fallback}` {alias2} "
                    f"WHERE {cond2}{t_cond2})")
            return f"({sql} OR {sql2})", p + p2

        return sql, p

    def _base_query(self, all_must, lookup_f=None):
        """Generische _base_query – nutzt JoinResolver für beliebige Tabellen.
        all_must: alle Filter + must-Targets (kombiniert).
        """
        params = []
        # Reference samples (customer originals) are not trials - never a hit.
        from db.trial_reference import exclude_references_sql
        where  = [exclude_references_sql("t")]
        alias_counter = [0]

        # Alle must-Filter generisch auflösen
        non_lookup = [f for f in all_must if f["field"].get("data_type") != "lookup"]
        for f in non_lookup:
            sql, p = self._build_filter_clause(f, alias_counter)
            where.append(sql)
            params.extend(p)

        # Lookup-Filter
        for f in (lookup_f or []):
            sql, p = self._build_filter_clause(f, alias_counter)
            if sql != "1=1":
                where.append(sql)
                params.extend(p)

        sql = """
            SELECT DISTINCT
                t.ID                AS trial_id,
                t.Versuchsnummer    AS trial_nr,
                ts.SeriesName       AS series_name,
                e.ExperimentID      AS experiment_id,
                e.ID                AS exp_pk,
                ts.ID               AS series_pk,
                j.Jet               AS jet_name,
                y.Name              AS yarn_name,
                y.Endtiter          AS titer,
                y.NumberOfFilaments AS filamente
            FROM tbltrial t
            JOIN tbltrialseries ts       ON ts.ID = t.TrialSeriesID
            JOIN tblexperimente e        ON e.ID  = ts.ExperimentID
            LEFT JOIN tbljets j          ON j.ID  = t.JetID
            LEFT JOIN tbltrialsettings tset ON tset.TrialID = t.ID AND tset.Ply = 'Ply 1'
            LEFT JOIN tblyarn y          ON y.ID  = tset.YarnID
        """
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY e.ExperimentID DESC, t.Versuchsnummer ASC LIMIT 500"

        return fetch_all(sql, params)

    def _load_lab_values(self, trial_ids, fields):
        """Lädt Werte für alle trial_ids. Unterstützt beliebige Tabellen via TrialID,
        tbltrial-direkt, tblyarn via tsy, tbltrialseries, tblexperimente.
        {tid: {key: val}}
        """
        if not trial_ids:
            return {}
        id_list = ",".join(str(i) for i in trial_ids)
        lab_map = {}

        for f in fields:
            fld     = f["field"]
            key     = fld["field_key"]
            col     = fld["source_column"]
            primary = fld["source_table_primary"]
            tbl     = primary.lower()
            fallback= fld.get("source_table_fallback")
            tension = fld.get("tension_filter")
            _TENSION_TABLES = {"tbllaboritematlab", "tbllaboritematplus"}
            t_cond  = (f" AND Tension = {tension}"
                       if tension is not None and tbl in _TENSION_TABLES
                       else "")

            if tbl == "tbltrial":
                rows = fetch_all(
                    f"SELECT ID AS TrialID, `{col}` AS val FROM `{primary}` "
                    f"WHERE ID IN ({id_list})", [])
            elif tbl == "tblyarn":
                rows = fetch_all(
                    f"SELECT t.ID AS TrialID, y.`{col}` AS val "
                    f"FROM tbltrial t "
                    f"JOIN tbltrialsettings tset ON tset.TrialID = t.ID "
                    f"JOIN tblyarn y ON y.ID = tset.YarnID "
                    f"WHERE t.ID IN ({id_list}) AND tset.YarnID IS NOT NULL", [])
            elif tbl in ("tbltrialseries", "tblexperimente"):
                # Join nötig
                if tbl == "tbltrialseries":
                    rows = fetch_all(
                        f"SELECT t.ID AS TrialID, ts.`{col}` AS val "
                        f"FROM tbltrial t "
                        f"JOIN tbltrialseries ts ON ts.ID = t.TrialSeriesID "
                        f"WHERE t.ID IN ({id_list})", [])
                else:
                    rows = fetch_all(
                        f"SELECT t.ID AS TrialID, e.`{col}` AS val "
                        f"FROM tbltrial t "
                        f"JOIN tbltrialseries ts ON ts.ID = t.TrialSeriesID "
                        f"JOIN tblexperimente e ON e.ID = ts.ExperimentID "
                        f"WHERE t.ID IN ({id_list})", [])
            else:
                # Standard: TrialID-Direkt (alle tbllabor*, tbltrialsettings)
                rows = fetch_all(
                    f"SELECT TrialID, `{col}` AS val FROM `{primary}` "
                    f"WHERE TrialID IN ({id_list}){t_cond}", [])

            found = set()
            for r in rows:
                if r["val"] is not None and r["val"] != 0:
                    tid = r["TrialID"]
                    lab_map.setdefault(tid, {})[key] = float(r["val"])
                    found.add(tid)

            # Fallback-Tabelle (nur für Itemat-Felder)
            missing = set(trial_ids) - found
            if missing and fallback:
                miss_list = ",".join(str(i) for i in missing)
                fb_rows = fetch_all(
                    f"SELECT TrialID, `{col}` AS val FROM `{fallback}` "
                    f"WHERE TrialID IN ({miss_list}){t_cond}", [])
                for r in fb_rows:
                    if r["val"] is not None and r["val"] != 0:
                        tid = r["TrialID"]
                        lab_map.setdefault(tid, {})[key] = float(r["val"])

        return lab_map

    def build_debug_info(self, filter_list, target_list) -> str:
        must_t  = [t for t in target_list if t["target_type"] == "must"]
        w_t     = [t for t in target_list if t["target_type"] == "weighted"]
        d_t     = [t for t in target_list if t["target_type"] == "distance"]
        lines   = ["-- Quick Scan Query\n"]
        lines.append(f"Filter (Must):   {len(filter_list)} Felder")
        lines.append(f"Target Must:     {len(must_t)} Felder")
        lines.append(f"Target Weighted: {len(w_t)} Felder")
        lines.append(f"Target Distance: {len(d_t)} Felder\n")
        if w_t:
            lines.append("Weighted Targets:")
            for t in w_t:
                fld = t["field"]
                lines.append(
                    f"  {fld['field_label']}: {t['operator']} {t['value1']}"
                    + (f"–{t['value2']}" if t.get("value2") else "")
                    + f"  direction={t.get('direction', '?')}  optimum={t.get('target_val', '?')}  gewicht={t['weight']}"
                )
        if d_t:
            lines.append("Distance Targets:")
            for t in d_t:
                fld = t["field"]
                lines.append(f"  {fld['field_label']}: Ziel={t['value1']}")
        return "\n".join(lines)



# ---------------------------------------------------------------------------
# Result table (desktop _show_results)
# ---------------------------------------------------------------------------
BASE_COLUMNS = [("experiment_id", "Experiment"), ("trial_nr", "Trial #"), ("series_name", "Series"),
                ("jet_name", "Jet"), ("yarn_name", "Yarn"), ("titer", "Titer"), ("filamente", "Fil.")]


def target_column_label(t: Dict[str, Any]) -> str:
    """Column title of a weighted / distance target: label @tension [unit]."""
    fld = t["field"]
    label = fld["field_label"]
    if fld.get("tension_filter") is not None:
        label += f" @{fld['tension_filter']}"
    if fld.get("unit"):
        label += f" [{fld['unit']}]"
    return label


def contribution_pct(row: Dict[str, Any], key: str, w_targets: List[Dict[str, Any]]) -> Optional[float]:
    """Share of one weighted target in the score (percent points)."""
    contrib = row.get(f"_contrib_{key}")
    if contrib is None:
        return None
    total_w = sum(t["weight"] for t in w_targets) or 1.0
    return contrib / total_w * 100


# ---------------------------------------------------------------------------
# Rulesets (tblRequirementSet / tblRequirementRule)
# ---------------------------------------------------------------------------
def list_rulesets() -> List[Dict[str, Any]]:
    return fetch_all("SELECT set_id, set_name, description, created_by, created_at FROM tblrequirementset "
                     "WHERE is_active=1 ORDER BY created_at DESC", []) or []


def save_ruleset(name: str, description: str, filters: List[Dict[str, Any]], targets: List[Dict[str, Any]],
                 created_by: str) -> Tuple[int, int]:
    """Saves filters + targets as a new ruleset; ad-hoc fields are registered first. -> (set_id, number of rules).
    The weighted direction goes into sort_order = n*10 + 1/2/3 (no column for it). Lookup selections are lists and
    have no column either: their rule is saved without values (the desktop failed to save such a ruleset)."""
    set_id = execute_insert("INSERT INTO tblrequirementset (set_name, description, is_active, created_by) "
                            "VALUES (%s, %s, 1, %s)", [name, description or None, created_by])
    all_rows = [(f, "filter") for f in filters] + [(t, "target") for t in targets]
    for n, (r, section) in enumerate(all_rows, start=1):
        field = r["field"]
        if field.get("_adhoc") or field.get("field_id") is None:
            ensure_registered(field)
        rule_type = r.get("target_type", "filter") if section == "target" else "filter"
        lookup = field.get("data_type") == "lookup"
        weighted = rule_type == "weighted"
        so = n * 10 + _DIR_CODE.get(r.get("direction") or "higher", 1) if weighted else n
        execute("INSERT INTO tblrequirementrule (set_id, field_id, rule_type, operator, target_value, "
                " min_value, max_value, weight, sort_order, is_active) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,1)",
                [set_id, field["field_id"], rule_type, r.get("operator"), r.get("target_val") if weighted else None,
                 None if lookup else r.get("value1"), None if lookup else r.get("value2"),
                 r.get("weight") if weighted else None, so])
    return set_id, len(all_rows)


def delete_ruleset(set_id: int) -> None:
    """Deactivates a ruleset (desktop "Delete")."""
    execute("UPDATE tblrequirementset SET is_active=0 WHERE set_id=%s", [set_id])


def load_ruleset(set_id: int) -> List[Dict[str, Any]]:
    """Rules of a ruleset in their order: [{"section": filter|target, "field", "rule_type", "operator", "value1",
    "value2", "weight", "direction", "target_val"}] (direction decoded from sort_order)."""
    rows = fetch_all(
        "SELECT r.rule_id, r.rule_type, r.operator, r.target_value, r.min_value, r.max_value, r.weight, r.sort_order, "
        "f.field_id, f.field_key, f.field_label, f.source_table_primary, f.source_table_fallback, f.source_column, "
        "f.tension_filter, f.data_type, f.unit, f.lookup_table, f.lookup_col_value, f.lookup_col_label "
        "FROM tblrequirementrule r JOIN tblrequirementfield f ON f.field_id = r.field_id "
        "WHERE r.set_id = %s AND r.is_active = 1 ORDER BY r.sort_order", [set_id]) or []
    # weighted rules carry the direction in sort_order (n*10 + code) - sort by n so the saved order comes back
    # (ordering by the raw column put weighted rules behind the others, also in the desktop)
    rows = sorted(rows, key=lambda r: ((r.get("sort_order") or 0) // 10 if r["rule_type"] == "weighted"
                                       else (r.get("sort_order") or 0)))
    out = []
    for r in rows:
        rule_type = r["rule_type"]
        so = r.get("sort_order") or 0
        direction = {1: "higher", 2: "lower", 3: "exact"}.get(so % 10 if so >= 10 else 1, "higher")
        out.append({"section": "filter" if rule_type == "filter" else "target", "field": _field_from_row(r),
                    "rule_type": rule_type, "operator": r.get("operator") or ">=", "value1": r.get("min_value"),
                    "value2": r.get("max_value"), "weight": r.get("weight"), "direction": direction,
                    "target_val": r.get("target_value")})
    return out
