# db/trial_actions.py
"""Actions on the trials / plies of a series - Qt-free, shared by the desktop
and the web app.

Moved out of the screens on 2026-11-13 without behaviour change (same SQL,
same order, same rules); the screens keep only their dialogs and messages.

Reassign yarn (Backlog / All Experiments context menu, superusers):
    series_ply_yarns(series_id)       -> [{"Ply", "YarnID"}] (DISTINCT per ply)
    reassign_yarn_choices()           -> [{"ID", "Name"}] catalog yarns (no shadow yarns)
    plan_yarn_reassign(series_id, rows, yarn_names) -> plan (trial ids, new ply labels, conflicts)
    apply_yarn_reassign(series_id, plan, user)       -> number of changes
  rows = the editor lines in their order: {"orig_ply", "orig_yid", "new_yid",
  "deleted", "is_new"} (orig_* None for a new line). At least one line must
  stay. Note: the series check refuses ANY yarn different from what a ply
  label already has in the DB, so in practice only "add ply" / "delete the
  last ply" pass - kept as it was (the Yarns dialog of Show Experiment,
  db/series_yarns.py, is the newer way to change yarns).

Copy trials (Show Experiment "Copy trials"):
    copy_trials_setup(series_id)                  -> trials, fields, source values, next number
    copy_trials(series_id, plan, fields, user)    -> (new trial ids, error or None)
  plan = [(source_trial_id, {field.key: value})] - field keys from
  db/trial_copy.build_copy_fields (via copy_trials_setup).

Reference samples (db/trial_reference.py):
    add_reference_sample(series_id, name, user, template_trial_id=None) -> new trial id
    unmark_number(series_id, vno) / write_reference_flag(...) / set_reference_flag(...)
    rename_reference_sample(trial_id, name)

Add trials (Show Experiment "Add trials" -> Create Experiment "addtrials"):
    add_trials(series_id, jets, materials, lab_data, trial_values, settings_values) -> new trial ids
  with the prefill data series_ply_offset(), load_lab_machines(),
  series_lab_data() and db/series_actions.series_jet_groups().

Permission rules:
    can_reassign_yarn(user)   access level >= 4
    can_edit_trials(user)     access level >= 2 (copy trials, add trials, reference samples)
"""
from __future__ import annotations

import datetime
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from db.connection import execute, fetch_all, get_connection, new_global_id
from db.series_actions import access_level, legacy_feature_user_id
from db.series_tables import get_columns_map, table_exists
from db.trial_reference import (
    IS_REFERENCE_COL,
    REFERENCE_NAME_COL,
    exclude_references_sql,
    has_reference_columns,
    next_reference_number,
    next_trial_number,
)
from ui.text_normalize import resolve_field

FEATURE_REASSIGN_YARN = 6   # tblFeatureUsage.FeatureID (stealth tracking)


def can_reassign_yarn(user: Any) -> bool:
    return access_level(user) >= 4


def can_edit_trials(user: Any) -> bool:
    return access_level(user) >= 2


def user_id_of(user: Any) -> Any:
    cu = user or {}
    return cu.get("id") if isinstance(cu, dict) else None


# ====================================================================== reassign yarn

def series_ply_yarns(series_id: int) -> List[Dict[str, Any]]:
    """Current yarn per ply (via tbltrialsettings, DISTINCT per ply, reference
    samples excluded). Raises on DB errors."""
    return fetch_all(
        "SELECT DISTINCT ts.Ply, ts.YarnID "
        "FROM tbltrialsettings ts "
        "JOIN tbltrial t ON t.ID = ts.TrialID "
        "WHERE t.TrialSeriesID = ? AND " + exclude_references_sql("t") + " "
        "ORDER BY ts.Ply",
        [series_id],
    )


def reassign_yarn_choices() -> List[Dict[str, Any]]:
    """All catalog yarns [{"ID", "Name"}] by name; [] on DB errors."""
    try:
        # Halbfabrikat-"Schatten"-Garne (Multimaschinen-Ply-Verknüpfung)
        # sollen hier nicht als Reassign-Ziel auftauchen.
        src_col = resolve_field(['SourceTrialID'], get_columns_map('tblYarn'))
        where = f" WHERE [{src_col}] IS NULL" if src_col else ""
        return fetch_all(f"SELECT ID, Name FROM tblYarn{where} ORDER BY Name", [])
    except Exception:
        return []


def plan_yarn_reassign(series_id: int, rows: List[Dict[str, Any]],
                       yarn_names: Dict[int, str]) -> Dict[str, Any]:
    """Trial ids of the series, the new ply labels ("Ply 1".. in the order of
    the remaining lines) and the conflicts that block saving:
    {"trial_ids", "rows" (copies with "new_ply" on kept lines), "conflicts"}."""
    if rows and all(r.get("deleted") for r in rows):
        raise ValueError("At least one ply must remain.")
    # ── Trials laden ──────────────────────────────────────────────────
    try:
        trial_rows_c = fetch_all(
            "SELECT ID FROM tblTrial WHERE TrialSeriesID = ? AND "
            + exclude_references_sql("") + " ORDER BY Versuchsnummer",
            [series_id])
        trial_ids = [int(r["ID"]) for r in trial_rows_c]
    except Exception:
        trial_ids = []

    rows = [dict(r) for r in rows]
    # Neue Ply-Labels berechnen (nur nicht-gelöschte, in Reihenfolge)
    active_states = [s for s in rows if not s["deleted"]]
    for i, s in enumerate(active_states):
        s["new_ply"] = f"Ply {i + 1}"

    # ── Konsistenzprüfung vor dem Schreiben ───────────────────────────
    # 1) Dialog-intern: zwei Zeilen mit gleichem Ply-Label aber verschiedener YarnID?
    ply_to_yid: dict = {}
    conflicts = []
    for state in active_states:
        new_ply = state["new_ply"]
        new_yid = state.get("new_yid")
        if new_yid is None:
            continue
        if new_ply in ply_to_yid:
            if ply_to_yid[new_ply] != new_yid:
                name_a = yarn_names.get(ply_to_yid[new_ply], f"ID {ply_to_yid[new_ply]}")
                name_b = yarn_names.get(new_yid, f"ID {new_yid}")
                conflicts.append(f"{new_ply}: «{name_a}» vs «{name_b}» (within dialog)")
        else:
            ply_to_yid[new_ply] = new_yid

    # 2) Gegen DB: gibt es in der Series bereits ein anderes Garn für dieses Ply?
    for new_ply, new_yid in ply_to_yid.items():
        conflict_rows = fetch_all(
            """
            SELECT DISTINCT y.Name AS YarnName
            FROM tblTrialSettings ts
            JOIN tblTrial t ON t.ID = ts.TrialID
            JOIN tblYarn y ON y.ID = ts.YarnID
            WHERE t.TrialSeriesID = ?
              AND ts.Ply = ?
              AND ts.YarnID != ?
              AND """ + exclude_references_sql("t") + """
            """,
            [series_id, new_ply, new_yid],
        )
        if conflict_rows:
            existing = ", ".join(r["YarnName"] for r in conflict_rows)
            new_name = yarn_names.get(new_yid, f"ID {new_yid}")
            conflicts.append(f"{new_ply}: «{new_name}» conflicts with existing «{existing}»")

    return {"trial_ids": trial_ids, "rows": rows, "conflicts": conflicts}


def conflict_message(conflicts: Sequence[str]) -> str:
    return ("Cannot save — the following plies would create inconsistencies:\n\n"
            + "\n".join(f"  • {c}" for c in conflicts)
            + "\n\nAll trials in a series must use the same yarn per ply.")


def _get_ply1_settings(trial_id):
    try:
        rows = fetch_all(
            "SELECT * FROM tblTrialSettings WHERE TrialID = ? ORDER BY ID LIMIT 1",
            [trial_id])
        return dict(rows[0]) if rows else None
    except Exception:
        return None


def apply_yarn_reassign(series_id: int, plan: Dict[str, Any], user: Any = None) -> int:
    """Writes a conflict-free plan (delete ply / clone ply 1 as a new ply /
    change yarn + ply label). Returns the number of changes; raises on a
    write error (earlier statements stay written - autocommit, as before).
    Then the stealth feature tracking."""
    if plan.get("conflicts"):
        raise ValueError(conflict_message(plan["conflicts"]))
    trial_ids = list(plan.get("trial_ids") or [])
    changes_made = 0
    for state in plan["rows"]:
        orig_ply = state["orig_ply"]
        orig_yid = state["orig_yid"]
        deleted = state["deleted"]
        is_new = state["is_new"]
        new_yid = state.get("new_yid")
        new_ply = state.get("new_ply")

        if deleted and is_new:
            # Neu hinzugefügt und gleich wieder gelöscht → nichts tun
            pass

        elif deleted and not is_new and orig_ply and trial_ids:
            # Ply löschen: alle tbltrialsettings-Zeilen mit diesem Ply-Label entfernen
            ph = ",".join(["?"] * len(trial_ids))
            execute(
                f"DELETE FROM tblTrialSettings "
                f"WHERE Ply = ? AND TrialID IN ({ph})",
                [orig_ply] + trial_ids,
            )
            changes_made += 1

        elif is_new and new_yid is not None:
            # Neues Ply: tbltrialsettings-Klon von Ply 1 pro Trial
            for tid in trial_ids:
                tmpl = _get_ply1_settings(tid)
                if tmpl:
                    skip = {"id", "trialid", "globalid"}
                    cols = [c for c in tmpl.keys() if c.lower() not in skip]
                    vals = []
                    for c in cols:
                        if c.lower() == "yarnid":
                            vals.append(new_yid)
                        elif c.lower() == "ply":
                            vals.append(new_ply)
                        else:
                            vals.append(tmpl[c])
                    cols_sql = ", ".join(f"`{c}`" for c in ["TrialID"] + cols)
                    ph2 = ", ".join(["?"] * (1 + len(cols)))
                    execute(
                        f"INSERT INTO tblTrialSettings ({cols_sql}) VALUES ({ph2})",
                        [tid] + vals,
                    )
            changes_made += 1

        elif not is_new and new_ply is not None:
            # Bestehendes Ply: YarnID und Ply-Label aktualisieren
            if trial_ids:
                ph = ",".join(["?"] * len(trial_ids))
                if new_yid != orig_yid or new_ply != orig_ply:
                    execute(
                        f"UPDATE tblTrialSettings SET YarnID = ?, Ply = ? "
                        f"WHERE Ply = ? AND TrialID IN ({ph})",
                        [new_yid, new_ply, orig_ply] + trial_ids,
                    )
                    changes_made += 1

    # ── Feature-Tracking ──────────────────────────────────────────────
    try:
        execute(
            "INSERT INTO tblFeatureUsage (FeatureID, UserID, ExtraInfo) VALUES (?, ?, ?)",
            [FEATURE_REASSIGN_YARN, legacy_feature_user_id(user), str(series_id)],
        )
    except Exception:
        pass
    return changes_made


# ====================================================================== copy trials

# Measured yarn tensions before/after the jet (tblTrial and, on the ATY
# machines, tblTrialSettings) - results of the run, not settings, so a trial
# copy starts with them empty (Nutzerwunsch 2026-10-15). Lower-case names.
TENSION_COLS_NOT_COPIED = {
    "yarntensionbeforejet",
    "yarntensionafterjet",
    "tensionbeforejet_core",
    "tensionafterjetinside",
    "tensionafterjetoutside",
}
# Comments (tblTrialSettings.Comment, comment2..4, per ply) belong to the run
# they were written for - a copy starts with them empty (Nutzerwunsch
# 2026-10-16). Any column "comment" / "commentN" in tblTrial or tblTrialSettings.
COMMENT_COL_RE = re.compile(r"^comment\d*$")


def col_not_copied(col: str) -> bool:
    """True for columns a trial copy starts with empty (tensions, comments)."""
    cl = str(col).lower()
    return cl in TENSION_COLS_NOT_COPIED or bool(COMMENT_COL_RE.match(cl))


# lab tables a trial copy / reference sample gets the row structure of
LAB_TABLES = [
    ("tbllabortiter", "TrialID"),
    ("tbllaborstatimatm", "TrialID"),
    ("tbllaborstatimatds", "TrialID"),
    ("tblLaborWaterbath", "TrialID"),
    ("tblLaborItematLab", "TrialID"),
    ("tblLaborItematPlus", "TrialID"),
    ("tblLaborRapid600", "TrialID"),
    ("tblLaborDTYoMat", "TrialID"),
    ("tblLaborATYoMat", "TrialID"),
    ("tblLaborEKB", "TrialID"),
    ("tblLaborHeissLuftSchrumpf", "TrialID"),
    ("tblLaborKochSchrumpf", "TrialID"),
    ("tblLaborATYShrinkage", "TrialID"),
]


def _is_zero_datetime(v: Any) -> bool:
    """Detect common 'zero' datetime placeholders (e.g. 0 or '0')."""
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return v == 0
    if isinstance(v, str):
        return v.strip() in ("", "0", "0000-00-00", "0000-00-00 00:00:00")
    return False


def clone_lab_rows_for_trial(cur, src_trial_id: int, new_trial_id: int, current_uid: Any = None) -> None:
    """Klont alle Labor-Datensätze von src_trial_id auf new_trial_id.

    - Struktur / Parameter (z.B. Tension) werden übernommen
    - eigentliche Messwerte werden auf NULL gesetzt
    current_uid = the user's ID (replaces 0/empty user placeholders).
    """
    from db.connection import table_exists as _db_table_exists
    for table_name, trial_col in LAB_TABLES:
        # prüfen, ob Tabelle existiert (MySQL)
        if not _db_table_exists(table_name.lower()):
            continue

        cur.execute(
            f"SELECT * FROM {table_name} WHERE {trial_col} = ?",
            (src_trial_id,),
        )
        rows = cur.fetchall()
        if not rows:
            continue

        col_names = [c[0] for c in cur.description]

        # ID + TrialID nicht direkt übernehmen
        skip_lower = {"id", trial_col.lower()}
        gid_col = None
        for c in col_names:
            if c.lower() == "globalid":
                gid_col = c
                skip_lower.add("globalid")
                break
        insert_cols = [c for c in col_names if c.lower() not in skip_lower]

        for row in rows:
            row_map = dict(zip(col_names, row))
            values = []
            for col in insert_cols:
                cl = col.lower()
                v = row_map.get(col)

                # --- keep/correct meta + FK fields so we don't violate constraints ---
                if cl.endswith("id"):
                    # keep foreign keys (e.g. UserID, InstrumentID, ...) intact
                    # but if it is a UserID placeholder (0), map to current user if available.
                    if "user" in cl and _is_zero_datetime(v):
                        values.append(current_uid if current_uid not in (None, "") else None)
                    elif "user" in cl and v in (0, "0", "", None):
                        values.append(current_uid if current_uid not in (None, "") else None)
                    else:
                        values.append(v)
                    continue

                if "createdby" in cl:
                    values.append(current_uid if current_uid not in (None, "") else v)
                    continue

                if any(k in cl for k in ("createdat", "updatedat", "timestamp")):
                    # give cloned rows a fresh timestamp if the source contains an invalid placeholder
                    values.append(datetime.datetime.now() if _is_zero_datetime(v) else v)
                    continue

                if any(k in cl for k in ("date", "time")):
                    # never insert 0 into date/time-like columns
                    values.append(None if _is_zero_datetime(v) else v)
                    continue

                # --- keep parameter columns, null measurement columns ---
                # Keep obvious setting columns; everything else becomes NULL.
                if "tension" in cl:
                    values.append(v)
                else:
                    values.append(None)

            cols_for_insert = [trial_col] + list(insert_cols)
            vals_for_insert = [new_trial_id] + values
            if gid_col:
                cols_for_insert.append(gid_col)
                vals_for_insert.append(new_global_id())
            cols_sql = ", ".join(
                f"[{c}]" for c in cols_for_insert)
            ph = ", ".join("?" for _ in cols_for_insert)
            cur.execute(
                f"INSERT INTO [{table_name}] ({cols_sql}) VALUES ({ph})",
                vals_for_insert,
            )


def clone_trial_settings_rows(cur, src_trial_id: int, new_trial_id: int) -> None:
    """Klont alle tblTrialSettings-Zeilen von src_trial_id auf new_trial_id.

    Alle Felder (inkl. Ply-Parameter wie 1stHeaterT1/T2, YarnTensionT1/T2 usw.)
    werden 1:1 übernommen. Nur ID und TrialID werden neu gesetzt; die
    gemessenen Fadenspannungen vor/nach Jet und die Kommentare bleiben
    leer (col_not_copied()).
    """
    from db.connection import table_exists as _db_table_exists
    if not _db_table_exists("tbltrialsettings"):
        return

    cur.execute(
        "SELECT * FROM tblTrialSettings WHERE TrialID = ?",
        (src_trial_id,),
    )
    rows = cur.fetchall()
    if not rows:
        return

    col_names = [c[0] for c in cur.description]

    skip_lower = {"id", "trialid"}
    gid_col = None
    for c in col_names:
        if c.lower() == "globalid":
            gid_col = c
            skip_lower.add("globalid")
            break
    insert_cols = [c for c in col_names if c.lower() not in skip_lower]

    for row in rows:
        row_map = dict(zip(col_names, row))
        values = [None if col_not_copied(c) else row_map.get(c) for c in insert_cols]

        cols_for_insert = ["TrialID"] + list(insert_cols)
        vals_for_insert = [new_trial_id] + values
        if gid_col:
            cols_for_insert.append(gid_col)
            vals_for_insert.append(new_global_id())

        cols_sql = ", ".join(f"[{c}]" for c in cols_for_insert)
        ph = ", ".join("?" for _ in cols_for_insert)
        cur.execute(
            f"INSERT INTO [tblTrialSettings] ({cols_sql}) VALUES ({ph})",
            vals_for_insert,
        )


def insert_trial_copy(cur, src_trial_id: int, series_id: Any, new_versuchsnummer: int,
                      current_uid: Any = None) -> int:
    """Inserts one new tblTrial row as a copy of src_trial_id (machine
    params 1:1, lab rows structurally cloned but nulled, ply settings
    cloned) at new_versuchsnummer within series_id. Returns the new
    trial's ID."""
    cur.execute("SELECT * FROM tblTrial WHERE ID = ?", (src_trial_id,))
    src_row = cur.fetchone()
    if not src_row:
        raise RuntimeError("Source trial not found.")

    col_names = [c[0] for c in cur.description]
    src_map = dict(zip(col_names, src_row))

    # ID / TrialSeriesID / Versuchsnummer are set explicitly below.
    # Also skip computed/read-only fields (e.g. "D/Y Ratio (T2/T1)").
    skip_lower = {
        "id",  # never copy the primary key
        # TrialSeriesID and Versuchsnummer are set explicitly, so they
        # are NOT skipped here.
        "d/y ratio (t2/t1)",  # computed field in Access
        # never copy DATETIME/TIMESTAMP columns 1:1 (MySQL rejects '0')
        "timestamp",
        "createdat",
        "updatedat",
    }
    # don't copy an existing GlobalID column directly
    gid_col = None
    for c in col_names:
        if c.lower() == "globalid":
            gid_col = c
            skip_lower.add("globalid")
            break
    insert_cols = [c for c in col_names if c.lower() not in skip_lower]

    values = []
    for col in insert_cols:
        cl = col.lower()
        if cl == "trialseriesid":
            values.append(series_id)
        elif cl == "versuchsnummer":
            values.append(new_versuchsnummer)
        elif col_not_copied(cl):
            values.append(None)  # measured / commented on the new run
        else:
            values.append(src_map.get(col))

    cols_for_insert = list(insert_cols)
    vals_for_insert = list(values)
    if gid_col:
        cols_for_insert.append(gid_col)
        vals_for_insert.append(new_global_id())
    cols_sql = ", ".join(f"[{c}]" for c in cols_for_insert)
    ph = ", ".join("?" for _ in cols_for_insert)
    cur.execute(
        f"INSERT INTO tblTrial ({cols_sql}) VALUES ({ph})",
        vals_for_insert,
    )
    # fetch the new ID (Access-ODBC idiom)
    cur.execute("SELECT @@IDENTITY")
    new_id_row = cur.fetchone()
    new_trial_id = int(new_id_row[0]) if new_id_row else None
    if not new_trial_id:
        raise RuntimeError("Could not determine the new trial ID.")

    # copy the lab records for this trial
    clone_lab_rows_for_trial(cur, src_trial_id, new_trial_id, current_uid)
    # copy the tblTrialSettings rows (ply data)
    clone_trial_settings_rows(cur, src_trial_id, new_trial_id)
    return new_trial_id


def next_trial_number_of_series(series_id: Any) -> int:
    """Next free trial number (highest + 1, reference samples ignored)."""
    rows = fetch_all("SELECT MAX(Versuchsnummer) AS mx FROM tblTrial WHERE TrialSeriesID = ?",
                     [series_id])
    return next_trial_number(rows[0]["mx"] if rows else None)


def copy_trials(series_id: Any, plan, fields, user: Any = None) -> Tuple[List[int], Optional[Exception]]:
    """Creates one copy per plan entry [(source_trial_id, {field.key:
    value})], appended after the series' highest trial number, then applies
    the changed values to the new trial (tblTrial columns, or on ATY the OF
    of all Core/Effect plies). Returns (new trial ids, error): on an error
    the copies made so far stay (autocommit, as before)."""
    by_key = {f.key: f for f in fields}
    current_uid = user_id_of(user)
    new_ids: List[int] = []
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(
                "SELECT MAX(Versuchsnummer) FROM tblTrial WHERE TrialSeriesID = ?",
                (series_id,),
            )
            row = cur.fetchone()
            # Clamped at 0: negative numbers are reference samples.
            max_v = next_trial_number(row[0] if row else None) - 1
            for src_trial_id, overrides in plan:
                max_v += 1
                new_id = insert_trial_copy(cur, src_trial_id, series_id, max_v, current_uid)
                new_ids.append(new_id)
                for fkey, value in (overrides or {}).items():
                    f = by_key.get(fkey)
                    if f is None:
                        continue
                    if f.kind == "trial":
                        cur.execute(f"UPDATE tblTrial SET [{f.column}] = ? WHERE ID = ?",
                                    (value, new_id))
                    elif f.kind == "use_of":
                        cur.execute(
                            f"UPDATE tblTrialSettings SET [{f.column}] = ? "
                            f"WHERE TrialID = ? AND YarnUseID = ?",
                            (value, new_id, f.use_id))
    except Exception as e:
        return new_ids, e
    return new_ids, None


def copy_trials_setup(series_id: Any) -> Dict[str, Any]:
    """What the copy dialog shows, for callers without the Show Experiment
    state (web): {"trials": [{"id", "vno"}] (no reference samples), "fields":
    [CopyField], "source": {trial_id: {field.key: value}}, "next_no"}."""
    from db import machine_data, series_tables
    from db.trial_copy import build_copy_fields, load_source_values
    st = series_tables.load_trials(series_id)
    trials = [{"id": int(t), "vno": v} for t, v in zip(st.trial_ids, st.trial_vnos)
              if int(t) not in st.reference_names]
    cache = machine_data.load_machine_cache(series_id, st.trial_ids) or {}
    fields = build_copy_fields(
        cache.get("machine_fields") or [],
        cache.get("trial_cols_map") or get_columns_map("tblTrial"),
        cache.get("lookup_maps") or {},
        machine_data.load_jets_lookup().list,
        machine_data.load_housing_lookup().list,
        bool(cache.get("has_groups")),
    )
    source = load_source_values([t["id"] for t in trials], fields)
    return {"trials": trials, "fields": fields, "source": source,
            "next_no": next_trial_number_of_series(series_id)}


# ====================================================================== reference samples

def first_real_trial_id(series_id: Any) -> Optional[int]:
    """Template for a new reference sample's lab rows: the first real trial in
    Show Experiment's column order (db/series_tables.load_trials)."""
    from db import series_tables
    st = series_tables.load_trials(series_id)
    return next((int(t) for t in st.trial_ids if int(t) not in st.reference_names), None)


def add_reference_sample(series_id: Any, name: Optional[str], user: Any = None,
                         template_trial_id: Any = "auto") -> int:
    """New reference sample (flagged tblTrial row): next negative number (-1,
    -2, ...) instead of a trial number, plus the lab row structure of the
    template trial (values empty). Raises on errors. template_trial_id
    "auto" = first_real_trial_id(), None = no lab rows."""
    trial_cols = get_columns_map("tblTrial")
    if template_trial_id == "auto":
        template_trial_id = first_real_trial_id(series_id)
    uid = user_id_of(user)
    with get_connection() as cn:
        cur = cn.cursor()
        # Own negative number range (-1, -2, ...): a reference
        # sample doesn't use up a trial number.
        cur.execute(
            "SELECT MIN(Versuchsnummer) FROM tblTrial WHERE TrialSeriesID = ?",
            (series_id,),
        )
        row = cur.fetchone()
        new_v = next_reference_number(row[0] if row else None)

        cols = ["TrialSeriesID", "Versuchsnummer", IS_REFERENCE_COL, REFERENCE_NAME_COL]
        vals: List[Any] = [series_id, new_v, 1, name or None]
        if "globalid" in trial_cols:
            cols.append(trial_cols["globalid"])
            vals.append(new_global_id())
        if "user" in trial_cols and uid not in (None, ""):
            cols.append(trial_cols["user"])
            vals.append(uid)
        cur.execute(
            f"INSERT INTO tblTrial ({', '.join(f'[{c}]' for c in cols)}) "
            f"VALUES ({', '.join('?' for _ in cols)})",
            vals,
        )
        cur.execute("SELECT @@IDENTITY")
        id_row = cur.fetchone()
        new_id = int(id_row[0]) if id_row and id_row[0] else None
        if not new_id:
            raise RuntimeError("Could not determine the new trial ID.")

        if template_trial_id is not None:
            clone_lab_rows_for_trial(cur, int(template_trial_id), new_id, uid)
    return new_id


def unmark_number(series_id: Any, vno: Any) -> Optional[int]:
    """Turning a reference sample back into a trial: a negative-numbered one
    gets the next free trial number (returned), a positive number is kept
    (None) - the physical spool label carries it."""
    try:
        if int(vno) < 1:
            rows = fetch_all(
                "SELECT MAX(Versuchsnummer) AS mx FROM tblTrial WHERE TrialSeriesID = ?",
                [series_id])
            return next_trial_number(rows[0]["mx"] if rows else None)
    except (TypeError, ValueError):
        pass
    return None


def write_reference_flag(trial_id: Any, make_reference: bool, name: Optional[str] = None,
                         new_vno: Optional[int] = None) -> None:
    if new_vno is not None:
        execute(
            f"UPDATE tblTrial SET {IS_REFERENCE_COL} = 0, {REFERENCE_NAME_COL} = NULL, "
            f"Versuchsnummer = ? WHERE ID = ?",
            [new_vno, int(trial_id)],
        )
    else:
        execute(
            f"UPDATE tblTrial SET {IS_REFERENCE_COL} = ?, {REFERENCE_NAME_COL} = ? WHERE ID = ?",
            [1 if make_reference else 0, name or None, int(trial_id)],
        )


def set_reference_flag(trial_id: Any, series_id: Any, vno: Any, make_reference: bool,
                       name: Optional[str] = None) -> Optional[int]:
    """Mark a trial as reference sample (keeps its number) or back (a
    negative number gets the next trial number). Returns the new number or None."""
    new_vno = None if make_reference else unmark_number(series_id, vno)
    write_reference_flag(trial_id, make_reference, None if not make_reference else name, new_vno)
    return new_vno


def rename_reference_sample(trial_id: Any, name: Optional[str]) -> None:
    execute(
        f"UPDATE tblTrial SET {REFERENCE_NAME_COL} = ? WHERE ID = ?",
        [name or None, int(trial_id)],
    )


def reference_samples_available() -> bool:
    return has_reference_columns()


# ====================================================================== add trials

def insert_waterbath_rows(cur, tbl, col_trial, trial_id):
    """Fügt drei Waterbath-Datensätze für einen Trial hinzu.

    Falls die Tabelle eine Spalte 'GlobalID' besitzt, wird für jede neue Zeile
    eine frische GUID vergeben.
    Erwartet vorhandene Tabelle und Spaltennamen; führt keine Existenzprüfung aus.
    """
    from db.connection import get_columns_map as _db_get_columns_map
    # MySQL: Information-Schema
    cols_map = _db_get_columns_map(tbl.lower())
    global_col = cols_map.get("globalid")
    has_global = bool(global_col)

    for _ in range(3):
        if has_global and global_col:
            cur.execute(
                f"INSERT INTO {tbl} ([{col_trial}],[{global_col}]) VALUES (?,?)",
                [trial_id, new_global_id()],
            )
        else:
            cur.execute(
                f"INSERT INTO {tbl} ([{col_trial}]) VALUES (?)",
                [trial_id],
            )


def to_int_or_none(s: Any) -> Optional[int]:
    if s is None:
        return None
    st = str(s).strip()
    if st == "":
        return None
    try:
        return int(st)
    except Exception:
        return None


def to_float_or_none(s: Any) -> Optional[float]:
    if s is None:
        return None
    st = str(s).strip().replace(",", ".")
    if st == "":
        return None
    try:
        return float(st)
    except Exception:
        return None


def col_is_numeric(table: str, real_col: str) -> bool:
    """As CreateExperimentScreen._col_is_numeric: the column info there never
    carries a type (data_type/type_name are always None), so this is always
    False - the jet plate is therefore always written as text. Kept 1:1."""
    info = [{"lower": lc, "real": real, "data_type": None, "type_name": None}
            for lc, real in get_columns_map(table).items()]
    for i in info:
        if i["real"].lower() == real_col.lower():
            dt = i.get("data_type")
            tn = (i.get("type_name") or "").upper()
            if dt in (2, 3, 4, 5, 6, 7) or any(x in tn for x in
                                               ["BYTE", "SHORT", "LONG", "INT", "INTEGER", "SINGLE", "DOUBLE", "NUMERIC", "DECIMAL"]):
                return True
    return False


def _insert_and_identity(cur, sql: str, params) -> int:
    cur.execute(sql, params)
    cur.execute("SELECT @@IDENTITY")
    rid = cur.fetchone()[0]
    try:
        return int(rid)
    except Exception:
        return int(float(rid))


def physical_jets_for_series(series_id: int) -> List[Dict[str, Any]]:
    """Die distinkten 'physischen Duesen' (JetID + JetPlate) einer Series.

    JetID sitzt normalerweise auf tbltrialsettings (pro Ply/Material);
    manche Series haben aber (noch/nur) ein JetID direkt auf tbltrial
    gepflegt (aeltere Datensaetze / andere Erfassungswege). Um das nicht
    stillschweigend zu verpassen, wird beides abgefragt und kombiniert:
    COALESCE(ts.JetID, t.JetID). JetPlate (Plaettchennummer) sitzt auf
    tbltrial.
    """
    if not table_exists("tbltrialsettings") or not table_exists("tbltrial"):
        return []
    ts_cols = get_columns_map("tbltrialsettings")
    t_cols = get_columns_map("tbltrial")
    col_jet_ts = resolve_field(["JetID"], ts_cols)
    col_jet_t = resolve_field(["JetID"], t_cols)
    col_plate = resolve_field(
        ["Jet Plate Number", "JetPlate", "Jet Plate", "JetPlateNumber"], t_cols) or "Jet Plate Number"

    if not col_jet_ts and not col_jet_t:
        return []

    if col_jet_ts and col_jet_t:
        jet_expr = f"COALESCE(ts.[{col_jet_ts}], t.[{col_jet_t}])"
    elif col_jet_ts:
        jet_expr = f"ts.[{col_jet_ts}]"
    else:
        jet_expr = f"t.[{col_jet_t}]"

    try:
        rows = fetch_all(
            f"SELECT DISTINCT {jet_expr} AS JetID, t.[{col_plate}] AS JetPlate "
            f"FROM tbltrialsettings ts "
            f"JOIN tbltrial t ON t.ID = ts.TrialID "
            f"WHERE t.TrialSeriesID = ? AND {jet_expr} IS NOT NULL",
            [series_id],
        )
    except Exception:
        return []
    out = []
    for r in rows:
        out.append({"JetID": int(r["JetID"]), "JetPlate": r.get("JetPlate")})
    return out


def save_jet_air_consumption_rows(cur, series_id: int, lab_data: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    """Legt fuer alle SeriesFreeform-Lab-Machine-Eintraege (Jet Air Consumption)
    die Kreuzprodukt-Zeilen (physische Duese x Druckstufe) an.

    Wird EINMAL pro Series aufgerufen (nicht pro Trial). Bereits vorhandene
    Kombinationen (Duese+Druck) werden nicht doppelt angelegt - so kann das
    auch beim addtrials-Speichern erneut aufgerufen werden, ohne Duplikate
    zu erzeugen, falls durch neue Trials neue physische Duesen dazukommen.

    Gibt Statistiken zurueck (fuer die Erfolgsmeldung / Diagnose).
    """
    stats = {"created": 0, "skipped_exists": 0, "physical_jets": 0, "no_user": 0}

    freeform_entries = [
        lm for lm in lab_data
        if str(lm.get("RowMode") or "").strip().lower() == "seriesfreeform"
    ]
    if not freeform_entries:
        return stats

    physical_jets = physical_jets_for_series(series_id)
    stats["physical_jets"] = len(physical_jets)
    if not physical_jets:
        return stats

    for lm in freeform_entries:
        tbl = (lm.get("TableName") or "").strip()
        if not tbl or not table_exists(tbl):
            continue
        pressure = lm.get("AdditionalVal")
        if pressure is None:
            continue
        lcols = get_columns_map(tbl)
        col_series = resolve_field(["TrialSeriesID"], lcols) or "TrialSeriesID"
        col_jet = resolve_field(["JetID"], lcols) or "JetID"
        col_plate = resolve_field(["JetPlate"], lcols) or "JetPlate"
        col_press = resolve_field(["AirPressure"], lcols) or "AirPressure"
        col_gid = resolve_field(["GlobalID"], lcols)
        col_user = resolve_field(["UserID", "User"], lcols)
        default_user_id = None
        if col_user and table_exists("tbluser"):
            try:
                urows = fetch_all("SELECT MIN([ID]) AS uid FROM tbluser")
                if urows and urows[0].get("uid") is not None:
                    default_user_id = int(urows[0]["uid"])
            except Exception:
                default_user_id = None

        for pj in physical_jets:
            # Bereits vorhanden? (Duese+Druck fuer diese Series)
            try:
                existing = fetch_all(
                    f"SELECT [ID] FROM {tbl} WHERE [{col_series}] = ? AND [{col_jet}] = ? "
                    f"AND ([{col_plate}] = ? OR (? IS NULL AND [{col_plate}] IS NULL)) "
                    f"AND [{col_press}] = ?",
                    [series_id, pj["JetID"], pj["JetPlate"], pj["JetPlate"], pressure],
                )
            except Exception:
                existing = []
            if existing:
                stats["skipped_exists"] += 1
                continue

            cols = [col_series, col_jet, col_plate, col_press]
            vals: List[Any] = [series_id, pj["JetID"], pj["JetPlate"], pressure]
            if col_gid:
                cols.append(col_gid)
                vals.append(new_global_id())
            if col_user:
                if default_user_id is None:
                    stats["no_user"] += 1
                    continue  # kann ohne gueltigen User nicht anlegen (NOT NULL FK)
                cols.append(col_user)
                vals.append(default_user_id)
            ph = ",".join(["?"] * len(cols))
            cur.execute(
                f"INSERT INTO {tbl} (" + ",".join(f"[{c}]" for c in cols) + f") VALUES ({ph})",
                vals,
            )
            stats["created"] += 1

    return stats


def machine_values(fields: Iterable[Tuple[str, Any, str]]) -> Tuple[List[Tuple[str, Any]], List[Tuple[str, Any]]]:
    """Machine fields of the add-trials form -> (tblTrial values, tblTrialSettings
    values) with the real column names. fields = [(column name, value or
    text, storage "tbltrial" | "tbltrialsettings")]; texts are converted like
    the form does (number if possible, "" = left out)."""
    tr_cols = get_columns_map("tblTrial")
    ts_cols_map: Dict[str, str] = get_columns_map("tblTrialSettings") \
        if table_exists("tblTrialSettings") else {}
    trial_vals: List[Tuple[str, Any]] = []
    settings_vals: List[Tuple[str, Any]] = []
    for orig_col, val, storage in fields:
        if isinstance(val, str):
            txt = val.strip()
            if not txt:
                continue
            val = to_float_or_none(txt)
            if val is None:
                ival = to_int_or_none(txt)
                val = ival if ival is not None else txt
        elif val is None:
            continue
        if storage == "tbltrialsettings":
            real = resolve_field([orig_col], ts_cols_map)
            if real:
                settings_vals.append((real, val))
        else:
            real = resolve_field([orig_col], tr_cols)
            if real:
                trial_vals.append((real, val))
    return trial_vals, settings_vals


def add_trials(series_id: int, jets: Sequence[Dict[str, Any]], materials: Sequence[Dict[str, Any]],
               lab_data: Sequence[Dict[str, Any]],
               trial_values: Sequence[Tuple[str, Any]] = (),
               settings_values: Sequence[Tuple[str, Any]] = ()) -> List[int]:
    """New trials in an existing series, one per jet plate (Jets x plates, as
    in Create Experiment), numbered after the highest trial number, one
    tblTrialSettings row per material, fresh empty lab rows per lab machine
    (lab_data), plus the series' Jet Air Consumption rows. One transaction
    (rolled back and re-raised on error). Returns the new trial ids.

    jets:      [{"JetID", "PlateList" "1,2" or "Plates" n, "Pressure", "HousingID"}]
    materials: [{"YarnID", "Ply" (optional), "YarnUseID", "SpoolID"}]
    lab_data:  [{"TableName", "AdditionalFieldSource", "AdditionalVal", "RowMode"}]
    trial_values / settings_values: [(real column, value)] (machine_values()).
    """
    ts_id = int(series_id)
    # Trial-Tabelle + Spalten-Map
    trial_table = "tblTrial"
    if not table_exists(trial_table):
        raise RuntimeError("Table 'tblTrial' not found.")
    tr_cols = get_columns_map(trial_table)
    tr_sid     = resolve_field(["TrialSeriesID", "SerieID", "SeriesID"], tr_cols) or "TrialSeriesID"
    tr_no      = resolve_field(["Versuchsnummer", "TrialNumber", "Nr"], tr_cols) or "Versuchsnummer"
    tr_jetid   = resolve_field(["JetID", "Jet Id", "Jet"], tr_cols) or "JetID"
    tr_plate   = resolve_field(["Jet Plate Number", "JetPlate", "Jet Plate", "JetPlateNumber"], tr_cols) or "Jet Plate Number"
    tr_press   = resolve_field(["Air Pressure (bar)", "AirPressure", "Air Pressure"], tr_cols) or "Air Pressure (bar)"
    tr_housing = resolve_field(["HousingID"], tr_cols)
    tr_gid     = resolve_field(["GlobalID"], tr_cols)

    jetplate_is_numeric = col_is_numeric(trial_table, tr_plate)

    cn = None
    try:
        with get_connection() as cn:
            cn.autocommit = False
            cur = cn.cursor()

            # Letzter Trial der Serie für Lab-Klon
            cur.execute(
                f"SELECT MAX([{tr_no}]) AS mx, "
                f"MAX(CASE WHEN {exclude_references_sql('')} THEN [ID] END) AS lid "
                f"FROM [{trial_table}] WHERE [{tr_sid}] = ?", [ts_id])
            row = cur.fetchone()
            # next_trial_number(): clamped at 0 - reference samples have
            # negative numbers (db/trial_reference.py)
            trial_counter = next_trial_number(row[0] if row else None)

            new_trial_ids: List[int] = []

            for j in jets:
                try:
                    plates_list = [p.strip() for p in str(j["PlateList"]).split(",") if p.strip()]
                except Exception:
                    plates_list = []
                if not plates_list:
                    try:
                        nn = int(j.get("Plates") or 0)
                    except Exception:
                        nn = 0
                    plates_list = [str(k+1) for k in range(max(0, nn))]

                for plate in plates_list:
                    press_val   = to_float_or_none(j["Pressure"])
                    plate_value = to_int_or_none(plate) if jetplate_is_numeric else str(plate)
                    housing_id  = j.get("HousingID")

                    cols = [tr_sid, tr_no, tr_jetid, tr_plate, tr_press]
                    vals: List[Any] = [ts_id, trial_counter, int(j["JetID"]), plate_value, press_val]

                    if tr_housing and housing_id is not None:
                        cols.append(tr_housing)
                        vals.append(int(housing_id))
                    for col, val in trial_values:
                        cols.append(col)
                        vals.append(val)
                    if tr_gid:
                        cols.append(tr_gid)
                        vals.append(new_global_id())

                    ph = ",".join(["?"] * len(cols))
                    sql = f"INSERT INTO {trial_table} ({','.join('['+c+']' for c in cols)}) VALUES ({ph})"
                    tid = _insert_and_identity(cur, sql, vals)
                    new_trial_ids.append(tid)

                    # tblTrialSettings: pro Garn eine Zeile
                    if table_exists("tblTrialSettings") and materials:
                        from db.dy_ratio import append_ratio_column
                        ts_set_cols_map = get_columns_map("tblTrialSettings")
                        has_yuse = "yarnuseid" in ts_set_cols_map
                        has_spool = "spoolid" in ts_set_cols_map
                        for idx_m, m in enumerate(materials):
                            s_cols = ["TrialID", "YarnID", "Ply"]
                            s_vals: List[Any] = [tid, int(m["YarnID"]), m.get("Ply") or f"Ply {idx_m+1}"]
                            if has_yuse and m.get("YarnUseID") is not None:
                                real_yuse = ts_set_cols_map.get("yarnuseid") or "YarnUseID"
                                s_cols.append(real_yuse)
                                s_vals.append(m["YarnUseID"])
                            if has_spool and m.get("SpoolID") is not None:
                                real_spool = ts_set_cols_map.get("spoolid") or "SpoolID"
                                s_cols.append(real_spool)
                                s_vals.append(m["SpoolID"])
                            for s_col, s_val in settings_values:
                                real_s = ts_set_cols_map.get(s_col.lower()) or s_col
                                s_cols.append(real_s)
                                s_vals.append(s_val)
                            append_ratio_column(s_cols, s_vals, ts_set_cols_map)
                            s_gid = resolve_field(["GlobalID"], ts_set_cols_map)
                            if s_gid:
                                s_cols.append(s_gid)
                                s_vals.append(new_global_id())
                            s_ph = ",".join(["?"] * len(s_cols))
                            cur.execute(
                                f"INSERT INTO tblTrialSettings "
                                f"({','.join('['+c+']' for c in s_cols)}) VALUES ({s_ph})",
                                s_vals)

                    trial_counter += 1

            # Lab Machines -> FRISCH aus lab_data schreiben (wie im
            # regulaeren Create-Flow), NICHT vom letzten Trial klonen - der
            # letzte Trial hat nicht unbedingt in jeder Tabelle schon eine
            # Zeile. lab_data kommt aus series_lab_data() (ganze Serie).
            default_user_id = None
            if table_exists("tbluser"):
                try:
                    urows = fetch_all("SELECT MIN([ID]) AS uid FROM tbluser")
                    if urows and urows[0].get("uid") is not None:
                        default_user_id = int(urows[0]["uid"])
                except Exception:
                    default_user_id = None

            for lm in lab_data:
                if str(lm.get("RowMode") or "").strip().lower() == "seriesfreeform":
                    # Jet Air Consumption & Co: keine Zeile pro Trial -
                    # wird unten einmal pro Series (physische Duese x Druck) angelegt.
                    continue
                tbl = (lm.get("TableName") or "").strip()
                if not tbl or not table_exists(tbl):
                    continue
                lcols = get_columns_map(tbl)
                col_trial = resolve_field(["TrialID"], lcols) or "TrialID"
                add_src = (lm.get("AdditionalFieldSource") or "").strip()
                add_real = resolve_field([add_src], lcols) if add_src else None
                add_val = lm.get("AdditionalVal", None)
                if isinstance(add_val, str):
                    add_val = to_float_or_none(add_val) or add_val
                for tid in new_trial_ids:
                    if 'waterbath' in (tbl or '').lower():
                        insert_waterbath_rows(cur, tbl, col_trial, tid)
                        continue
                    # optionale GlobalID-Spalte im Labor-Table
                    col_gid = resolve_field(["GlobalID"], lcols)
                    cols_sql_parts = [f"[{col_trial}]"]
                    params: List[Any] = [tid]
                    if col_gid:
                        cols_sql_parts.append(f"[{col_gid}]")
                        params.append(new_global_id())
                    if add_real:
                        cols_sql_parts.append(f"[{add_real}]")
                        params.append(add_val)

                    # optionaler UserID (FK auf tbluser) - falls vorhanden, sauber setzen
                    col_user = resolve_field(["UserID", "User"], lcols)
                    if col_user:
                        if default_user_id is None:
                            # Ohne gueltigen User koennen wir diese Lab-Row nicht anlegen (sonst FK-Fehler)
                            continue
                        cols_sql_parts.append(f"[{col_user}]")
                        params.append(default_user_id)

                    placeholders = ",".join(["?"] * len(params))
                    cur.execute(
                        f"INSERT INTO {tbl} (" + ",".join(cols_sql_parts) +
                        ") VALUES (" + placeholders + ")",
                        params,
                    )

            save_jet_air_consumption_rows(cur, ts_id, lab_data)
            cn.commit()
    except Exception:
        try:
            if cn is not None:
                cn.rollback()
        except Exception:
            pass
        raise
    return new_trial_ids


def series_ply_offset(series_id: int) -> int:
    """Highest ply number used in the series (new plies of "add trials" count on from there)."""
    ply_offset = 0
    try:
        rows = fetch_all(
            "SELECT MAX(CAST(REPLACE(Ply, 'Ply ', '') AS UNSIGNED)) AS MaxPly "
            "FROM tblTrialSettings ts "
            "JOIN tblTrial t ON t.ID = ts.TrialID "
            "WHERE t.TrialSeriesID = ?",
            [series_id])
        if rows and rows[0].get("MaxPly") is not None:
            ply_offset = int(rows[0]["MaxPly"])
    except Exception:
        # Fallback: COUNT DISTINCT Ply
        try:
            rows2 = fetch_all(
                "SELECT COUNT(DISTINCT ts.Ply) AS C "
                "FROM tblTrialSettings ts "
                "JOIN tblTrial t ON t.ID = ts.TrialID "
                "WHERE t.TrialSeriesID = ?",
                [series_id])
            if rows2 and rows2[0].get("C"):
                ply_offset = int(rows2[0]["C"])
        except Exception:
            pass
    return ply_offset


def is_itemat(meta: dict, fallback_name: str = "") -> bool:
    """Erkenne Itemat-Maschinen robust (DB-Name kann 'Itemat Lab', 'ITEMATLAB', etc. sein)."""
    name = str(meta.get("LMName") or fallback_name or "").strip(
    ).lower().replace(" ", "")
    # exakte matches + robuste startswith/endswith
    if name in ("itematlab", "itematplus"):
        return True
    return name.startswith("itemat") and (name.endswith("lab") or name.endswith("plus"))


def load_lab_machines() -> Optional[List[Dict[str, Any]]]:
    """Lab machine catalog (tblLabMachines) in name order: rows with LMID,
    LMName, AddField, AddUnit, Tbl, Src, RowMode, Unit. None = table missing."""
    table = "tblLabMachines"
    if not table_exists(table):
        return None

    cmap = get_columns_map(table)
    col_id = resolve_field(["ID"], cmap) or "ID"
    col_name = resolve_field(["LabMachineName", "LabMachine", "Name"], cmap) or "LabMachineName"

    # optionale Spalten (können im MySQL-Schema fehlen)
    col_add = resolve_field(["AdditionalField", "AdditinalField"], cmap)
    col_unit = resolve_field(["AdditionalFieldUnit", "Unit"], cmap)
    col_tbl = resolve_field(["TableName", "LaborTable", "Table"], cmap)
    col_src = resolve_field(["AdditionalFieldSource", "AddFieldSource", "Source"], cmap)
    col_rowmode = resolve_field(["RowMode"], cmap)

    def _sel(col, alias, default_sql="NULL"):
        # Erzeugt " [col] AS alias " oder " NULL AS alias "
        if col:
            return f"[{col}] AS {alias}"
        return f"{default_sql} AS {alias}"

    rowmode_default = "'PerTrial'"
    sql = (
        f"SELECT [{col_id}] AS LMID, "
        f"[{col_name}] AS LMName, "
        f"{_sel(col_add, 'AddField')}, "
        f"{_sel(col_unit, 'AddUnit')}, "
        f"{_sel(col_tbl, 'Tbl')}, "
        f"{_sel(col_src, 'Src')}, "
        f"{_sel(col_rowmode, 'RowMode', rowmode_default)} "
        f"FROM {table} ORDER BY [{col_name}]"
    )

    out = []
    for r in fetch_all(sql):
        lm_id = r.get("LMID")
        if lm_id is None:
            continue

        name = str(r.get("LMName") or "").strip()

        # Robust: Itemat braucht praktisch immer ein Additional Field (Tension).
        # Wenn im Schema/Datensatz nichts gepflegt ist, setzen wir Defaults.
        add_field = (r.get("AddField") or "").strip() if isinstance(r.get("AddField"), str) else (r.get("AddField") or "")
        add_unit = (r.get("AddUnit") or "").strip() if isinstance(r.get("AddUnit"), str) else (r.get("AddUnit") or "")

        if (not add_field) and is_itemat(r, name):
            add_field = "Tension"
            # Einheit nur setzen, wenn nichts vorgegeben ist
            if not add_unit:
                add_unit = "cN/dtex"
            r["AddField"] = add_field
            r["AddUnit"] = add_unit

        r["Unit"] = add_unit
        out.append(r)
    return out


def series_lab_data(series_id: int, lab_machines: Dict[int, Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
    """Lab machines the existing trials of the series use (one entry per
    distinct additional value, e.g. each Itemat tension), as lab_data for
    add_trials(): [{"LMID", "Name", "AdditionalDisp", "AdditionalVal",
    "TableName", "AdditionalFieldSource", "Unit"}]. lab_machines = {LMID:
    row of load_lab_machines()}. None = the series has no trials (or the
    trial query failed) - the form then keeps what it had."""
    # Alle Trial-IDs der Serie
    try:
        trial_rows = fetch_all(
            "SELECT ID FROM tblTrial WHERE TrialSeriesID = ? ORDER BY Versuchsnummer",
            [series_id])
        if not trial_rows:
            return None
        trial_ids = [int(r["ID"]) for r in trial_rows]
    except Exception:
        return None

    placeholders = ",".join(["?"] * len(trial_ids))
    out: List[Dict[str, Any]] = []
    added_keys: set = set()  # (lm_id, add_val_norm)

    for lm_id, meta in lab_machines.items():
        tbl = str(meta.get("Tbl") or "").strip()
        src = str(meta.get("Src") or "").strip()
        lm_name = str(meta.get("LMName") or "").strip()
        unit = str(meta.get("Unit") or "").strip()
        if not tbl or not table_exists(tbl):
            continue

        try:
            # Prüfen ob Einträge für diese Serie existieren
            lcols = get_columns_map(tbl)
            col_trial = resolve_field(["TrialID"], lcols)
            if not col_trial:
                continue

            if src and resolve_field([src], lcols):
                # Mit AdditionalField (z.B. Itemat Tension): DISTINCT Werte laden
                src_col = resolve_field([src], lcols)
                rows = fetch_all(
                    f"SELECT DISTINCT [{src_col}] AS AV "
                    f"FROM [{tbl}] WHERE [{col_trial}] IN ({placeholders})"
                    f" AND [{src_col}] IS NOT NULL",
                    trial_ids)
                for row in rows:
                    add_val = row.get("AV")
                    try:
                        add_val = float(add_val)
                    except Exception:
                        pass
                    key = (lm_id, str(add_val) if add_val is not None else None)
                    if key in added_keys:
                        continue
                    added_keys.add(key)
                    disp = (f"{add_val} {unit}".strip() if add_val is not None else "")
                    out.append({
                        "LMID": lm_id, "Name": lm_name,
                        "AdditionalDisp": disp, "AdditionalVal": add_val,
                        "TableName": tbl, "AdditionalFieldSource": src,
                        "Unit": unit,
                    })
            else:
                # Ohne AdditionalField: einmal hinzufügen falls Einträge vorhanden
                cnt_rows = fetch_all(
                    f"SELECT COUNT(*) AS C FROM [{tbl}] WHERE [{col_trial}] IN ({placeholders})",
                    trial_ids)
                cnt = int(cnt_rows[0]["C"]) if cnt_rows and cnt_rows[0].get("C") else 0
                if cnt == 0:
                    continue
                key = (lm_id, None)
                if key in added_keys:
                    continue
                added_keys.add(key)
                out.append({
                    "LMID": lm_id, "Name": lm_name,
                    "AdditionalDisp": "", "AdditionalVal": None,
                    "TableName": tbl, "AdditionalFieldSource": src,
                    "Unit": unit,
                })
        except Exception:
            continue
    return out
