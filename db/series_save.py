# db/series_save.py
"""Saving edited Show Experiment cells - Qt-free, shared by the desktop
(ui/screen_show_experiment.py) and the web app.

Moved out of ui/screen_show_experiment.py (2026-11-13) without behaviour
change:

- normalize_value() / normalize_input(): input validation of one cell
  (PivotEditModel._validate_and_normalize + the extra rules in
  PivotEditModel.setData / MachinePivotModel.setData).
- save_cells(): the UPDATEs of PivotEditModel.save_dirty (GroupCellBinding,
  lab tables with User/Timestamp, unit conversion l/min, change history,
  DY ratio).
- stamp_trial_ids() / stamp_trial_timestamp(): Timestamp+User of tblTrial
  when a tension field of Machine Data changed (ShowExperimentScreen._save_all).
- recompute_itemat_intermingling() / recompute_itemat_plus(): IP(t) and CV@0
  after an Itemat save.
- multi_ply_differs() / log_multi_ply(): the stealth multi-ply feature
  tracking after a save.
- fill_*(): which cells the "Fill row" dialogs (_FillRowRange*Dialog) change.
- save_series_edits(): the whole _save_all sequence for callers without Qt
  models (web): edits per model -> same steps in the same order.

Edits are always [(binding, text)] with binding = db.series_tables.CellBinding
or GroupCellBinding (from the LabPivot / MachineData cells) and text = the
normalized display text (normalize_input), "" = clear (NULL).
"""
from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from db.connection import get_connection
from db.connection import get_columns_map as _db_get_columns_map
from db.series_tables import CellBinding, GroupCellBinding  # noqa: F401  (re-exported)
from ui.text_normalize import canon_rule

logger = logging.getLogger(__name__)

Edit = Tuple[Any, Any]   # (CellBinding | GroupCellBinding, new text)


# ---------------------------- DB helpers ----------------------------

def execute_non_query(sql: str, params: list | tuple = ()) -> int:
    """INSERT/UPDATE/DELETE-Wrapper: gibt rowcount zurück.
    Gibt mindestens 1 zurück wenn kein Exception, da MySQL rowcount bei
    UPDATE ohne Wertänderung 0 zurückgibt (CLIENT_FOUND_ROWS nicht gesetzt).
    """
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(sql, params)
        rc = getattr(cur, "rowcount", -1)
        # rowcount = -1: Treiber kann es nicht bestimmen → als Erfolg werten
        # rowcount =  0: kein Treffer (falsche ID) oder Wert unverändert
        # rowcount >  0: Zeilen betroffen
        if rc == -1:
            return 1
        return rc or 0


def fetch_all(sql: str, params: list | tuple = ()):
    """Return rows as list[dict] (same as ui.screen_show_experiment.fetch_all)."""
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description] if cur.description else []
        rows = []
        for r in cur.fetchall():
            d = {}
            for i, c in enumerate(cols):
                d[c] = r[i]
            rows.append(d)
        return rows


def get_columns_map(table: str) -> Dict[str, str]:
    """{lower_name: real_name}"""
    return _db_get_columns_map(table.lower())


def user_id_of(user: Any) -> Any:
    """User ID from a user dict (app_meta.current_user: key 'ID' / 'Id' / 'id')
    or the ID itself. None if unknown."""
    if isinstance(user, dict):
        for k in ("ID", "Id", "id"):
            if k in user:
                return user[k]
        return None
    return user


def to_float(s: Any) -> Optional[float]:
    if s is None:
        return None
    try:
        return float(str(s).replace(",", "."))
    except Exception:
        return None


# ---------------------------- input validation ----------------------------

RE_INT = re.compile(r"^[+-]?\d+$")
# akzeptiert: 123 | 123. | 123, | .5 | ,5 | 123.45 | 123,45 | +.7 | -0,8
RE_FLOAT_LIKE = re.compile(r"^[+-]?((\d+([.,]\d*)?)|([.,]\d+))$")
RE_FLOAT_2DP = re.compile(r"^[+-]?(\d+([.,]\d{0,2})?|[.,]\d{1,2})$")

AIR_PRESSURE_TITLE = "Air Pressure (bar)"


def normalize_value(rule: Optional[str], text_in: Any) -> Optional[str]:
    """Normalized string, "" if empty (-> NULL), None if invalid
    (PivotEditModel._validate_and_normalize; rule = the row validator).
    - onlySZ: nur S, Z, SZ (case-insensitiv), Ausgabe uppercase
    - onlyInteger: Ganzzahl (Vorzeichen ok), Ausgabe ohne führende Nullen
    - onlyDoubles: Ganzzahl oder Dezimal (Punkt/Komma), Ausgabe mit Punkt, Ganzzahl ohne .0
    - anything else (dropdown:tbl, hidden, None): the stripped text
    """
    if text_in is None:
        return ""
    s = str(text_in).strip()
    if s == "":
        return ""  # leeren Wert erlauben

    rule = canon_rule(rule)
    if not rule:
        return s  # keine Regel

    if rule == "onlySZ":
        up = s.upper().replace(" ", "")
        return up if up in ("S", "Z", "SZ") else None

    if rule == "onlyInteger":
        if RE_INT.fullmatch(s):
            try:
                return str(int(s))
            except Exception:
                return None
        return None

    if rule == "onlyDoubles":
        if not RE_FLOAT_LIKE.fullmatch(s):
            return None
        try:
            v = float(s.replace(",", "."))
            return str(int(v)) if v.is_integer() else f"{v}"
        except Exception:
            return None

    return s


def apply_row_title_rule(row_title: Optional[str], normalized: str) -> Optional[str]:
    """Extra rule by row title after normalize_value (PivotEditModel.setData):
    "Air Pressure (bar)" = at most 2 decimals, trailing zeros removed. None = invalid."""
    if row_title == AIR_PRESSURE_TITLE:
        s2 = normalized.strip()
        if s2 != "":
            if not RE_FLOAT_2DP.fullmatch(s2):
                return None
            try:
                v = float(s2.replace(",", "."))
                return f"{v:.2f}".rstrip("0").rstrip(".")
            except Exception:
                return None
    return normalized


def normalize_input(rule: Optional[str], row_title: Optional[str], value: Any,
                    kind: Optional[str] = None) -> Optional[str]:
    """What a cell stores when the user enters `value` - the text that goes
    into the edit list (and the DB), or None = invalid input (rejected, cell
    unchanged). "" = clear the value.

    rule      = the row validator (LabPivot.validators / MachineData.validators)
    row_title = the row title (LabPivot.row_titles / MachineData.row_titles)
    kind      = "housing" / "jet" for the Machine Data rows that store an ID
                (MachinePivotModel: data row 0 = Housing, data row 1 = Jet;
                value = the ID or None/"" to clear), else None.
                Generic dropdown rows (rule "dropdown:tbl...") take the ID as
                value with kind None - they are stored as str(id).
    """
    if kind == "housing":
        try:
            hid = int(value)
        except Exception:
            hid = None if value in (None, "", " ") else value
        return "" if hid is None else str(hid)
    if kind == "jet":
        try:
            jet_id = int(value)
        except Exception:
            if value in (None, "", " "):
                jet_id = None
            else:
                return None
        return "" if jet_id is None else str(jet_id)
    normalized = normalize_value(rule, "" if value is None else str(value))
    if normalized is None:
        return None
    return apply_row_title_rule(row_title, normalized)


# ---------------------------- saving cells ----------------------------

_FROM_APP = object()


def save_cells(edits: Iterable[Edit], *, user: Any = None, series_id: Any = None, source: str = "edit",
               unit_scale: float = 1.0, unit_field: Optional[str] = None,
               audit_cache: Optional[Dict[str, Tuple[Optional[str], Optional[str]]]] = None,
               log_user_id: Any = _FROM_APP) -> int:
    """Writes the edited cells (PivotEditModel.save_dirty). Returns the summed
    "rowcount" of the UPDATEs (execute_non_query: at least 1 per statement
    without error - also when the value did not change).

    edits      : [(binding, text)] in edit order (a cell edited twice = two
                 entries, both written, the last one wins); binding None is skipped.
                 GroupCellBinding = one UPDATE per ID of the group.
    user       : user dict (app_meta.current_user) or user ID - written to the
                 [User] column of lab tables (tblLabor*) together with
                 [Timestamp] = NOW(), if the table has those columns.
    series_id  : stored with the change history (tblChangeLog.SeriesID).
    source     : tblChangeLog.Source ("edit").
    unit_scale / unit_field: display unit conversion - for cells of field
                 `unit_field`, stored = entered / unit_scale (Jet Air in l/min:
                 LabPivot.extra["unit_scale"] / ["unit_field"]).
    audit_cache: optional dict {table: (user col, timestamp col)} kept between calls.
    log_user_id: tblChangeLog.UserID; default = app_meta.current_user["id"]
                 (the desktop); the web passes its user ID.

    Order: old values for the change history are read first (one query per
    table/field), then the UPDATEs, then the change history, then DYRatio of
    the tblTrialSettings rows whose T1/T2 changed. An exception of an UPDATE
    propagates (nothing logged/recomputed then) - like before.
    """
    edits = list(edits)
    n = 0
    cache = audit_cache if audit_cache is not None else {}
    user_id = user_id_of(user)

    dy_ratio_ids: set = set()  # tblTrialSettings rows whose T1/T2 changed

    # Change history (db/change_log.py): old DB values of all changed
    # cells, one query per (table, field), read before writing
    from db import change_log as _chlog
    _log_on = _chlog.table_ready()
    _old_vals: Dict[Tuple[str, str], Dict[int, Dict[str, Any]]] = {}
    _log_new: Dict[Tuple[str, int, str], Any] = {}
    if _log_on:
        _want: Dict[Tuple[str, str], set] = {}
        for _b, _t in edits:
            if not _b:
                continue
            _ids = _b.id_values if isinstance(_b, GroupCellBinding) else [_b.id_value]
            _want.setdefault((str(_b.table), str(_b.field)), set()).update(_ids)
        for (_tb, _fd), _ids in _want.items():
            try:
                _old_vals[(_tb, _fd)] = _chlog.read_current(_tb, _fd, list(_ids))
            except Exception:
                _old_vals[(_tb, _fd)] = {}

    for bind, new_text in edits:
        if not bind:
            continue
        if str(bind.table).lower() == "tbltrialsettings" \
                and str(bind.field).lower() in ("yarntensiont1", "yarntensiont2"):
            if isinstance(bind, GroupCellBinding):
                dy_ratio_ids.update(bind.id_values)
            else:
                dy_ratio_ids.add(bind.id_value)

        # ── GroupCellBinding: alle IDs der Gruppe updaten ─────────────
        if isinstance(bind, GroupCellBinding):
            text_str = "" if new_text is None else str(new_text).strip()
            for gid in bind.id_values:
                _log_new[(str(bind.table), int(gid), str(bind.field))] = text_str
                if text_str == "":
                    sql = (
                        f"UPDATE {bind.table} SET "
                        f"`{bind.field}` = NULL WHERE `{bind.id_field}` = ?"
                    )
                    params: list[Any] = [gid]
                else:
                    sql = (
                        f"UPDATE {bind.table} SET "
                        f"`{bind.field}` = ? WHERE `{bind.id_field}` = ?"
                    )
                    params = [text_str, gid]
                n += execute_non_query(sql, params)
            continue

        table_name = str(bind.table)
        is_lab_table = table_name.lower().startswith("tbllabor")

        user_col = None
        ts_col = None
        if is_lab_table:
            # Spaltennamen für User/Timestamp pro Tabelle cachen
            if table_name in cache:
                user_col, ts_col = cache[table_name]
            else:
                try:
                    cols = get_columns_map(table_name)
                except Exception:
                    cols = {}
                user_col = cols.get("user")
                ts_col = cols.get("timestamp")
                cache[table_name] = (user_col, ts_col)

        text_str = "" if new_text is None else str(new_text).strip()

        # Einheiten-Umrechnung: Anzeige-Einheit -> DB-Einheit (z.B. l/min -> Nm3/h)
        if text_str != "" and unit_scale != 1.0 and bind.field == unit_field:
            try:
                _disp_val = float(text_str.replace(",", "."))
                text_str = repr(_disp_val / unit_scale)
            except Exception:
                pass

        if text_str == "":
            # Wert -> NULL
            if is_lab_table and (user_col or ts_col):
                set_parts = [f"[{bind.field}] = NULL"]
                params = []
                if user_col:
                    set_parts.append(f"[{user_col}] = ?")
                    params.append(user_id)
                if ts_col:
                    set_parts.append(f"[{ts_col}] = NOW()")
                sql = (
                        f"UPDATE {bind.table} SET "
                        + ", ".join(set_parts)
                        + f" WHERE [{bind.id_field}] = ?"
                )
                params.append(bind.id_value)
            else:
                sql = (
                    f"UPDATE {bind.table} SET "
                    f"[{bind.field}] = NULL WHERE [{bind.id_field}] = ?"
                )
                params = [bind.id_value]
        else:
            # normaler UPDATE mit neuem Wert
            if is_lab_table and (user_col or ts_col):
                set_parts = [f"[{bind.field}] = ?"]
                params = [text_str]
                if user_col:
                    set_parts.append(f"[{user_col}] = ?")
                    params.append(user_id)
                if ts_col:
                    set_parts.append(f"[{ts_col}] = NOW()")
                sql = (
                        f"UPDATE {bind.table} SET "
                        + ", ".join(set_parts)
                        + f" WHERE [{bind.id_field}] = ?"
                )
                params.append(bind.id_value)
            else:
                sql = (
                    f"UPDATE {bind.table} SET "
                    f"[{bind.field}] = ? WHERE [{bind.id_field}] = ?"
                )
                params = [text_str, bind.id_value]

        n += execute_non_query(sql, params)
        try:
            _log_new[(str(bind.table), int(bind.id_value), str(bind.field))] = text_str
        except (TypeError, ValueError):
            pass

    if _log_on and _log_new:
        _entries = []
        for (_tb, _rid, _fd), _new in _log_new.items():
            _cur = _old_vals.get((_tb, _fd), {}).get(_rid, {})
            _tid = _rid if _tb.lower() == "tbltrial" else _cur.get("trial_id")
            _entries.append({"table": _tb, "row_id": _rid, "field": _fd,
                             "old": _cur.get("value"), "new": _new, "trial_id": _tid})
        if log_user_id is _FROM_APP:
            _chlog.log_changes(_entries, series_id=series_id, source=source)
        else:
            _chlog.log_changes(_entries, series_id=series_id, source=source, user_id=log_user_id)

    if dy_ratio_ids:
        from db.dy_ratio import recompute
        try:
            recompute(dy_ratio_ids)
        except Exception as e:
            logging.getLogger(__name__).warning("DYRatio recompute failed: %s", e)

    return n


# ---------------------------- tension timestamp ----------------------------

def _stamp_norm(x: str) -> str:
    return (x or "").lower().replace(" ", "").replace("_", "").replace("(", "").replace(")", "") \
        .replace("°", "").replace("/", "").replace("-", "").strip()


# Machine Data fields (tblTrial) whose edit stamps tblTrial.Timestamp/User
STAMP_TARGETS = {
    _stamp_norm("Yarn Tension before Jet (cN)"),
    _stamp_norm("Yarn Tension after Jet (cN)"),
    _stamp_norm("YarnTensionBeforeJet"),
    _stamp_norm("YarnTensionAfterJet"),
    # W3Tension ("Tension W3 (cN)"): the SSM/draw-machine equivalent
    # of the jet machines' after-jet tension above - the last tension
    # reading taken on those machines, so its edit time is the closest
    # available proxy for "this trial's machine data is complete"
    # (2026-08-20, explicit user request; see also the Done-status
    # fallback in screen_backlog.py's _update_backlog_status()).
    _stamp_norm("W3Tension"),
}


def stamp_trial_ids(machine_edits: Iterable[Edit]) -> set:
    """Trial IDs to stamp after the save: tblTrial bindings of a tension field
    among the Machine Data edits (only the Machine Data model, not R&D)."""
    out = set()
    for bind, _new in machine_edits or ():
        if bind and getattr(bind, "table", None) == "tblTrial":
            if _stamp_norm(getattr(bind, "field", "")) in STAMP_TARGETS:
                out.add(getattr(bind, "id_value", None))
    return out


def stamp_trial_timestamp(trial_id: Any, user: Any = None) -> int:
    """Setzt NOW() in tblTrial.[Timestamp] **und** den User in tblTrial.[User]
    (user = dict or ID). 0 on error."""
    try:
        return execute_non_query(
            "UPDATE tblTrial SET [Timestamp]=NOW(), [User]=? WHERE [ID]=?",
            [user_id_of(user), trial_id],
        )
    except Exception:
        # Falls Spalte mal nicht existiert o.ä., fehlerfrei weitermachen
        return 0


# ---------------------------- Itemat recompute ----------------------------
# get_value(row, col) / get_binding(row, col) read the CURRENT (saved) cells of
# the Itemat table; row_offset = info rows above the data rows (desktop: the
# jet info rows, web pivot: 0); n_cols = number of trial columns.

_EPS = 1e-9


def round_db(value: float, decimals: int = 2) -> float:
    """Round like a MySQL DECIMAL column stores it (ROUND_HALF_UP, not Python's banker's rounding)."""
    from decimal import Decimal, ROUND_HALF_UP
    return float(Decimal(repr(float(value))).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP))


def _write_if_changed(table: str, field: str, cand_vals: Dict[Any, float], cand_ids: List[Any]) -> int:
    updates = 0
    placeholders = ",".join(["?"] * len(cand_ids))
    rows = fetch_all(
        f"SELECT ID, [{field}] AS V FROM {table} WHERE ID IN ({placeholders})",
        cand_ids,
    )
    cur_vals: Dict[Any, Optional[float]] = {r["ID"]: to_float(r.get("V")) for r in rows}
    for rec_id, new_v in cand_vals.items():
        # The columns hold 2 decimals: round like MySQL does (half away from zero) BEFORE
        # comparing - otherwise 106.6316 never equals the stored 106.63 and every save of
        # Itemat Lab/Plus rewrote all IP(t) values (fixed 2026-11-13). Stored values unchanged.
        if new_v is not None:
            new_v = round_db(new_v, 2)
        old_v = cur_vals.get(rec_id)
        if (old_v is None and new_v is None):
            continue
        if (old_v is not None and abs(old_v - new_v) <= _EPS):
            continue
        updates += execute_non_query(
            f"UPDATE {table} SET [{field}] = ? WHERE ID = ?",
            [new_v, rec_id],
        )
    return updates


def _ip_candidates(get_value, get_binding, n_cols, tensions, row_ip0, row_stab_start):
    from db import series_tables as _st
    cand_ids: List[Any] = []
    cand_vals: Dict[Any, float] = {}
    for c_idx in range(n_cols):
        ip0 = to_float(get_value(row_ip0, c_idx))
        if ip0 is None:
            continue
        for t_idx, _tval in enumerate(tensions):
            row = row_stab_start + t_idx
            stab = to_float(get_value(row, c_idx))
            if stab is None:
                continue
            bind = get_binding(row, c_idx)
            if not bind:
                continue
            rec_id = bind.id_value
            cand_ids.append(rec_id)
            cand_vals[rec_id] = _st.itemat_ip_at_tension(ip0, stab)
    return cand_ids, cand_vals


def recompute_itemat_intermingling(get_value: Callable[[int, int], Any], get_binding: Callable[[int, int], Any],
                                   n_cols: int, tensions: Sequence[float], row_offset: int = 0) -> int:
    """Itemat Lab: for every tension t > 0  IP(t) = IP(0) * Stability(t) / 100,
    written to tblLaborItematLab only where it differs from the DB value."""
    from db import series_tables as _st
    if not tensions:
        return 0
    cand_ids, cand_vals = _ip_candidates(get_value, get_binding, n_cols, tensions,
                                         row_offset + _st.ITEMAT_ROW_IP0,
                                         row_offset + _st.ITEMAT_ROW_STAB_START)
    if not cand_ids:
        return 0
    return _write_if_changed("tblLaborItematLab", "Intermingling Points (FP/m)", cand_vals, cand_ids)


def recompute_itemat_plus(get_value: Callable[[int, int], Any], get_binding: Callable[[int, int], Any],
                          n_cols: int, tensions: Sequence[float], row_offset: int = 0) -> int:
    """Itemat Plus: 1) IP(t) as above into the Stability(t) records,
    2) CV@0 = ((KL S)^2 + (OL S)^2)^0.5 / (KL X + OL X) into the 0.0 record
    [Intermingling Points CV (%)] - both only where it differs from the DB."""
    from db import series_tables as _st
    updates = 0
    cand_ids_ip, cand_vals_ip = _ip_candidates(get_value, get_binding, n_cols, tensions,
                                               row_offset + _st.ITEMAT_PLUS_ROW_IP0,
                                               row_offset + _st.ITEMAT_PLUS_ROW_STAB_START)
    if cand_ids_ip:
        updates += _write_if_changed("tblLaborItematPlus", "Intermingling Points (FP/m)",
                                     cand_vals_ip, cand_ids_ip)

    row_ip0 = row_offset + _st.ITEMAT_PLUS_ROW_IP0
    cand_ids_cv: List[Any] = []
    cand_vals_cv: Dict[Any, float] = {}
    for c_idx in range(n_cols):
        def _f(row_idx):
            return to_float(get_value(row_idx, c_idx))

        olx, ols = _f(row_offset + _st.ITEMAT_PLUS_ROW_OLX0), _f(row_offset + _st.ITEMAT_PLUS_ROW_OLS0)
        klx, kls = _f(row_offset + _st.ITEMAT_PLUS_ROW_KLX0), _f(row_offset + _st.ITEMAT_PLUS_ROW_KLS0)
        cv0 = _st.itemat_plus_cv0(olx, ols, klx, kls)
        if cv0 is None:
            continue
        bind0 = get_binding(row_ip0, c_idx)
        if not bind0:
            continue
        rec0_id = bind0.id_value
        cand_ids_cv.append(rec0_id)
        cand_vals_cv[rec0_id] = cv0
    if cand_ids_cv:
        updates += _write_if_changed("tblLaborItematPlus", "Intermingling Points CV (%)",
                                     cand_vals_cv, cand_ids_cv)
    return updates


# ---------------------------- multi-ply feature tracking ----------------------------

def multi_ply_differs(col_specs: Sequence[Dict], n_rows: int, get_binding: Callable[[int, int], Any],
                      get_value: Callable[[int, int], Any]) -> bool:
    """True if in at least one trial a ply 2..N has another value than ply 1 in
    the same tblTrialSettings row (Machine Data columns = col_specs)."""
    from collections import defaultdict
    if not col_specs:
        return False
    trial_cols: Dict[Any, List[Tuple[str, int]]] = defaultdict(list)
    for c_idx, cs in enumerate(col_specs):
        trial_cols[cs["trial_id"]].append((cs["ply"], c_idx))

    def _norm_val(v):
        if v is None:
            return ""
        return str(v).strip()

    for tid, ply_cols in trial_cols.items():
        if len(ply_cols) < 2:
            continue  # nur ein Ply -> kein Multi-Ply-Vergleich moeglich
        _, c_ply1 = ply_cols[0]
        for r_idx in range(n_rows):
            try:
                bind1 = get_binding(r_idx, c_ply1)
            except Exception:
                bind1 = None
            if not bind1 or getattr(bind1, "table", None) != "tblTrialSettings":
                continue
            val_ply1 = get_value(r_idx, c_ply1)
            for _, c_plyx in ply_cols[1:]:
                if _norm_val(val_ply1) != _norm_val(get_value(r_idx, c_plyx)):
                    return True
    return False


def log_multi_ply(user_id: Any, series_id: Any) -> None:
    """tblFeatureUsage entry FeatureID 2 (multi-ply)."""
    from db.connection import execute as _db_execute
    _db_execute(
        "INSERT INTO tblFeatureUsage (FeatureID, UserID, ExtraInfo) VALUES (?, ?, ?)",
        [2, user_id, str(series_id)],
    )


# ---------------------------- Fill row (bulk edit) ----------------------------
# The "Fill row" dialogs of Machine Data / R&D Machine Data (right click a row
# title). col_specs = MachineData.col_specs (one dict per data column with
# "trial_id", "ply", groups view: "yarn_use_name"). Trials are numbered
# 1..n in column order ("From trial #" / "To trial #").

FILL_HOUSING, FILL_JET, FILL_DROPDOWN, FILL_TEXT = "housing", "jet", "dropdown", "text"


def unique_trial_ids(col_specs: Sequence[Dict]) -> List[Any]:
    out: List[Any] = []
    for cs in col_specs or ():
        if cs.get("trial_id") not in out:
            out.append(cs.get("trial_id"))
    return out


def fill_kind(data_row: int, *, has_housing_list: bool, has_jets_list: bool,
              dropdown_rows: Iterable[int] = ()) -> str:
    """Which dialog: data row 0 = Housing (if housings exist), 1 = Jet (if jets
    exist), a dropdown row (MachineData.dropdown_rows), else text."""
    if data_row == 0 and has_housing_list:
        return FILL_HOUSING
    if data_row == 1 and has_jets_list:
        return FILL_JET
    if data_row in set(dropdown_rows or ()):
        return FILL_DROPDOWN
    return FILL_TEXT


def fill_n_trials(col_specs: Sequence[Dict], n_cols: int) -> int:
    """Upper end of the trial range in the dialog (distinct trials; without
    col_specs the number of data columns)."""
    tids = unique_trial_ids(col_specs)
    return max(1, len(tids)) if col_specs else max(1, n_cols)


def fill_default(values: Iterable[Any]) -> Any:
    """Preselected value: the first value not None/""/" " (stored ID for the
    dropdown kinds; for text the desktop takes the first non-empty DISPLAY text
    of an editable cell)."""
    for v in values:
        if v not in (None, "", " "):
            return v
    return None


def _has_multi_ply(col_specs: Sequence[Dict]) -> bool:
    return len(col_specs) > len(unique_trial_ids(col_specs))


def fill_ply_labels(col_specs: Sequence[Dict], kind: str, *, data_row: int = 0, titles_fixed_count: int = 0,
                    first_binding: Any = None, use_groups: bool = False) -> List[str]:
    """Ply checkboxes of the dialog ([] = none shown, the whole trial is set).
    dropdown: the plies whenever a trial has several columns.
    text: only for a tblTrialSettings row (binding of the first column) below
    the fixed rows, labels = ply (groups view: yarn use name).
    housing/jet: never."""
    col_specs = list(col_specs or [])
    if kind == FILL_DROPDOWN:
        seen: List[str] = []
        for cs in col_specs:
            pl = str(cs.get("ply") or "")
            if pl and pl not in seen:
                seen.append(pl)
        return seen if _has_multi_ply(col_specs) else []
    if kind != FILL_TEXT:
        return []
    seen = []
    for cs in col_specs:
        if use_groups:
            pl = str(cs.get("yarn_use_name") or cs.get("ply") or "")
        else:
            pl = str(cs.get("ply") or "")
        if pl and pl not in seen:
            seen.append(pl)
    is_ply_row = False
    if data_row >= titles_fixed_count and col_specs and _has_multi_ply(col_specs):
        try:
            b = first_binding
            if b is not None and str(getattr(b, "table", "") or "").lower() == "tbltrialsettings":
                is_ply_row = True
        except Exception:
            pass
    return seen if is_ply_row else []


def fill_range_columns(col_specs: Sequence[Dict], start_trial: int, end_trial: int,
                       selected_plies: Optional[Iterable[str]] = None, n_cols: int = 0) -> List[int]:
    """0-based data columns the fill touches: trials start..end (1-based, swapped
    if reversed), restricted to the selected plies (matched against cs["ply"];
    None = all). Without col_specs: columns start-1..end-1 (n_cols ignored -
    the caller drops columns that do not exist / are not editable)."""
    a, b = int(start_trial), int(end_trial)
    if b < a:
        a, b = b, a
    sel = None if selected_plies is None else set(selected_plies)
    if not col_specs:
        return list(range(a - 1, b))
    order = {tid: i + 1 for i, tid in enumerate(unique_trial_ids(col_specs))}
    out = []
    for c_idx, cs in enumerate(col_specs):
        ti = order.get(cs.get("trial_id"), 0)
        if not (a <= ti <= b):
            continue
        if sel is not None and str(cs.get("ply") or "") not in sel:
            continue
        out.append(c_idx)
    return out


def _same_number(a: str, b: str) -> bool:
    try:
        return float(a.replace(",", ".")) == float(b.replace(",", "."))
    except ValueError:
        return False


def fill_range_edits(col_specs: Sequence[Dict], start_trial: int, end_trial: int, value: Any, *,
                     cells: Sequence[Tuple[Any, Any]], rule: Optional[str], row_title: Optional[str],
                     kind: str = FILL_TEXT, selected_plies: Optional[Iterable[str]] = None,
                     read_only: bool = False) -> List[Tuple[int, Any, str]]:
    """The cell edits of one "Fill row": [(data col, binding, new text)].
    cells = the row's current cells [(stored text/value, binding)] (one per data
    column, e.g. MachineData.cells[row]); read_only = the row is read-only.
    Columns without binding are skipped (not editable), invalid input
    (normalize_input None) changes nothing, unchanged cells are left out.
    value: housing/jet/dropdown = the ID (None = clear), text = the typed text."""
    if read_only:
        return []
    out = []
    norm_kind = kind if kind in (FILL_HOUSING, FILL_JET) else None
    sel = selected_plies if kind in (FILL_TEXT, FILL_DROPDOWN) else None
    for c in fill_range_columns(col_specs, start_trial, end_trial, sel, len(cells)):
        if not (0 <= c < len(cells)):
            continue
        cur, binding = cells[c]
        if binding is None:
            continue
        new = normalize_input(rule, row_title, value, norm_kind)
        if new is None:
            continue
        cur_txt = "" if cur is None else str(cur)
        if cur_txt == new or (cur_txt and new and _same_number(cur_txt, new)):
            continue      # unchanged (3.0 stored, 3 typed) - not an edit
        out.append((c, binding, new))
    return out


# ---------------------------- the whole save (web) ----------------------------

def model_key(name: str) -> str:
    """"model_itemat" / "itemat" -> "itemat" (desktop attribute or LabPivot key)."""
    n = str(name)
    return n[6:] if n.startswith("model_") else n


def save_series_edits(user: Any, series_id: Any, edits_by_model: Dict[str, List[Edit]], *,
                      source: str = "edit",
                      unit_scales: Optional[Dict[str, Tuple[float, Optional[str]]]] = None,
                      machine_view: Optional[Callable[[], Tuple[Sequence[Dict], Sequence[Sequence[Tuple[Any, Any]]]]]] = None,
                      ) -> Dict[str, Any]:
    """ShowExperimentScreen._save_all without Qt (plausibility check is the
    caller's job before: db.plausibility.check). Same steps, same order:

    1. trial IDs to stamp = tension fields among the "machine" edits
    2. per model in the given order: save_cells(); after "itemat" /
       "itemat_plus" edits the IP(t)/CV@0 recompute from the saved values
       (pivot reloaded from the DB). An error in one model skips it, the
       others are still saved.
    3. tblTrial Timestamp/User of the stamped trials
    4. multi-ply feature tracking - only if machine_view is given: a callable
       returning (col_specs, cells) of Machine Data AFTER the save, e.g.
       lambda: (md.col_specs, md.cells) of a fresh build_machine_data().

    edits_by_model: {"machine": [(binding, text)], "rd_machine": [...],
                     "itemat": [...], "jet_air": [...], ...} - keys = LabPivot
                     keys / desktop model names (a "model_" prefix is ignored).
    unit_scales: {"jet_air": (scale, field)} for a table shown in another unit
                 (LabPivot.extra["unit_scale"], ["unit_field"]).
    user: user dict or ID (lab [User], tblTrial [User], change history).

    Returns {"saved": total count (as the desktop's), "stamped": n,
             "per_model": {name: n}, "failed": {name: error text}}.
    """
    from db import series_tables as _st
    unit_scales = unit_scales or {}
    uid = user_id_of(user)
    result: Dict[str, Any] = {"saved": 0, "stamped": 0, "per_model": {}, "failed": {}}
    total = 0

    machine_edits = []
    for name, edits in edits_by_model.items():
        if model_key(name) == "machine":
            machine_edits.extend(edits or [])
    try:
        trial_ids_to_stamp = stamp_trial_ids(machine_edits)
    except Exception:
        trial_ids_to_stamp = set()

    _trials = []

    def _series_trials():
        if not _trials:
            _trials.append(_st.load_trials(series_id))
        return _trials[0]

    def _recompute(builder, fn) -> int:
        p = builder(_series_trials())
        if p is None:
            return 0
        tensions = list(p.extra.get("tensions") or [])

        def _cell(r, c):
            return p.cells[r][c] if 0 <= r < len(p.cells) and 0 <= c < len(p.cells[r]) else (None, None)

        return fn(lambda r, c: _cell(r, c)[0], lambda r, c: _cell(r, c)[1],
                  len(_series_trials().labels), tensions, 0)

    for name, edits in edits_by_model.items():
        key = model_key(name)
        edits = list(edits or [])
        scale, field = unit_scales.get(key) or unit_scales.get(name) or (1.0, None)
        n_model = 0
        try:
            n_model += save_cells(edits, user=user, series_id=series_id, source=source,
                                  unit_scale=scale or 1.0, unit_field=field, log_user_id=uid)
            if key == "itemat" and edits:
                n_model += _recompute(_st.build_itemat, recompute_itemat_intermingling)
            elif key == "itemat_plus" and edits:
                n_model += _recompute(_st.build_itemat_plus, recompute_itemat_plus)
        except Exception as e:
            # one failing model must not stop the others (like the desktop)
            result["failed"][name] = str(e)
        total += n_model
        result["per_model"][name] = n_model

    stamped = 0
    for _tid in list(trial_ids_to_stamp):
        if _tid is not None:
            try:
                stamped += stamp_trial_timestamp(int(_tid), user)
            except Exception:
                pass
    total += stamped

    if machine_view is not None:
        try:
            col_specs, cells = machine_view()

            def _get(r, c):
                return cells[r][c] if 0 <= c < len(cells[r]) else (None, None)

            if col_specs and multi_ply_differs(col_specs, len(cells), lambda r, c: _get(r, c)[1],
                                               lambda r, c: _get(r, c)[0]) and uid is not None:
                log_multi_ply(uid, series_id)
        except Exception:
            pass

    result["saved"] = total
    result["stamped"] = stamped
    return result


# ---------------------------- save conflicts (2026-11-16) ----------------------------
# Two people (desktop and web, or two browsers) edit the same series: before writing, every edited cell is
# compared with the database. If its value changed since the editor loaded it - and the other person did not
# enter the same value - the save stops and the user decides (overwrite / keep the other value).

def _conflict_same(a: Any, b: Any) -> bool:
    """Equal for the conflict check: both empty, same text, or the same number (tolerant to unit rounding)."""
    a = None if a is None or str(a).strip() == "" else str(a).strip()
    b = None if b is None or str(b).strip() == "" else str(b).strip()
    if a == b:
        return True
    if a is None or b is None:
        return False
    try:
        fa, fb = float(a.replace(",", ".")), float(b.replace(",", "."))
    except ValueError:
        return False
    return abs(fa - fb) <= 1e-6 * max(1.0, abs(fa), abs(fb))


def find_conflicts(items: Sequence[Dict[str, Any]], *, unit_scale: float = 1.0,
                   unit_field: Optional[str] = None) -> List[Dict[str, Any]]:
    """Cells changed by someone else since loading.

    items: [{"binding": CellBinding | GroupCellBinding, "loaded": value as the editor loaded it (display units),
             "new": the new text, ...any extra keys (kept)}] - items with loaded None are skipped (unknown).
    unit_scale / unit_field: as save_cells (Jet Air in l/min: display = stored x unit_scale).
    Returns copies of the conflicting items with "current" (display units, "" = empty), "by" and "at"
    (last tblChangeLog entry of the cell, "" if unknown). A deleted row is no conflict here (the save
    then simply changes nothing)."""
    from db import change_log as _cl
    items = [it for it in items if it.get("binding") is not None and "loaded" in it and it["loaded"] is not None]
    if not items:
        return []
    want: Dict[Tuple[str, str], set] = {}
    for it in items:
        b = it["binding"]
        ids = b.id_values if isinstance(b, GroupCellBinding) else [b.id_value]
        want.setdefault((str(b.table), str(b.field)), set()).update(i for i in ids if i is not None)
    current: Dict[Tuple[str, str], Dict[int, Dict[str, Any]]] = {}
    for (tb, fd), ids in want.items():
        try:
            current[(tb, fd)] = _cl.read_current(tb, fd, list(ids))
        except Exception:
            current[(tb, fd)] = {}

    def shown(v: Any, field: str) -> Any:
        if v is None or unit_field is None or str(field).lower() != str(unit_field).lower() or unit_scale == 1.0:
            return v
        try:
            return float(v) * unit_scale
        except (TypeError, ValueError):
            return v

    out: List[Dict[str, Any]] = []
    for it in items:
        b = it["binding"]
        ids = b.id_values if isinstance(b, GroupCellBinding) else [b.id_value]
        cur_map = current.get((str(b.table), str(b.field)), {})
        vals = [shown(cur_map[int(i)]["value"], b.field) for i in ids if i is not None and int(i) in cur_map]
        if not vals:
            continue
        differing = [v for v in vals if not _conflict_same(v, it["loaded"])]
        if not differing:
            continue
        cur = differing[0]
        if _conflict_same(cur, it.get("new")):
            continue          # the other person entered the same value
        by = at = ""
        try:
            hist = _cl.history_for_cell(str(b.table), [i for i in ids if i is not None], str(b.field))
            if hist:
                by = str(hist[0].get("UserName") or "").strip()
                at = str(hist[0].get("ChangedAt") or "")[:16]
        except Exception:
            pass
        out.append({**it, "current": "" if cur is None else (f"{cur:g}" if isinstance(cur, float) else str(cur)),
                    "by": by, "at": at})
    return out
