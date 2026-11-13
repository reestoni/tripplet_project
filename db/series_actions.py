# db/series_actions.py
"""Actions on a whole trial series - Qt-free, shared by the desktop (Backlog,
All Experiments, Show Experiment, Create Experiment) and the web app.

Moved out of the screens on 2026-11-13 without behaviour change (same SQL,
same rules, same order); the screens keep only their dialogs and messages:

- rename: split_prefix() / compose_name() / rename_series()
  (BacklogDnDTable._ctx_rename_trialseries, AllExperimentsScreen.
  _rename_trialseries_at_row - both had identical copies of the prefix split)
- machine: current_machine() / list_machines() / change_machine()
  (BacklogDnDTable._ctx_reassign_machine, AllExperimentsScreen._reassign_machine_at_row)
- priority: set_backlog_prio() (BacklogScreen._update_backlog_prio)
- notes: save_notes() (ShowExperimentScreen._save_notes)
- copy series: series_jet_groups() - the Jet rows "Copy TrialSeries" prefills
  (CreateExperimentScreen._prefill_jets_from_trialseries). Saving the copy
  is the normal Create Experiment "addseries" save (still in the form).

Permission rules (same as the desktop context menus):
    can_rename(user)          access level >= 2
    can_change_machine(user)  access level >= 4 (superuser)
    can_change_prio(user)     everybody (the Backlog menu never restricted it)
    can_save_notes(user)      everybody (Show Experiment never restricted it)

`user` is a dict like app_meta.current_user ({"id", "username",
"access_level", ...}); the rule functions also accept a plain access level.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from db.connection import execute, fetch_all, update_trialseries_name

FEATURE_CHANGE_MACHINE = 7   # tblFeatureUsage.FeatureID (stealth tracking)


# ---------------------------------------------------------------- rules

def access_level(user: Any) -> int:
    """Access level of a user dict (key access_level) or of a plain number."""
    if isinstance(user, dict):
        user = user.get("access_level")
    try:
        return int(user or 0)
    except (TypeError, ValueError):
        return 0


def can_rename(user: Any) -> bool:
    return access_level(user) >= 2


def can_change_machine(user: Any) -> bool:
    return access_level(user) >= 4


def can_change_prio(user: Any) -> bool:
    return True


def can_save_notes(user: Any) -> bool:
    return True


def legacy_feature_user_id(user: Any) -> Any:
    """UserID the desktop writes into tblFeatureUsage for machine / yarn changes.

    Kept 1:1: the screens used getattr(app_meta.current_user, "id") on a DICT,
    which is always None - so these two features have always been tracked
    without a user. Changing that is a separate decision."""
    return getattr(user, "id", None) or getattr(user, "ID", None)


# ---------------------------------------------------------------- rename

def split_prefix(full_name: str) -> Tuple[str, str]:
    """Split a TrialSeries name into (prefix_to_keep, editable_part).

    Rules:
    - If it starts with something like "f(03 ) " (letter + (...) + spaces), keep that.
    - Else if it starts with digits followed by whitespace, keep that.
    - Otherwise prefix is empty.
    """
    s = full_name or ""

    # Pattern like: f(03 ) <name>  or A(12)  <name>
    m = re.match(r"^(\s*[A-Za-z]\([^\)]*\)\s+)(.*)$", s)
    if m:
        return m.group(1), m.group(2)

    # Pattern like: 03 <name>
    m = re.match(r"^(\s*\d+\s+)(.*)$", s)
    if m:
        return m.group(1), m.group(2)

    return "", s


def compose_name(prefix: str, new_text: str) -> Optional[str]:
    """Full new name from the kept prefix and the entered text; None = empty
    input (the desktop then keeps the old name)."""
    new_text = (new_text or "").strip()
    if not new_text:
        return None
    return f"{prefix}{new_text}" if prefix else new_text


def rename_series(series_id: int, new_full: str) -> int:
    """UPDATE tblTrialSeries.SeriesName (db.connection.update_trialseries_name)."""
    return update_trialseries_name(int(series_id), new_full)


def current_series_name(series_id: int) -> str:
    rows = fetch_all("SELECT SeriesName FROM tblTrialSeries WHERE ID = ?", [int(series_id)])
    return str(rows[0].get("SeriesName") or "") if rows else ""


def rename(series_id: int, new_text: str) -> Optional[str]:
    """Web: rename keeping the prefix of the CURRENT name in the DB (the desktop
    takes the name it shows). Returns the new full name, None = nothing done."""
    prefix, _editable = split_prefix(current_series_name(series_id).strip("\n"))
    new_full = compose_name(prefix, new_text)
    if not new_full:
        return None
    rename_series(series_id, new_full)
    return new_full


# ---------------------------------------------------------------- machine

def current_machine(series_id: int) -> Tuple[Optional[int], str]:
    """(MachineID, machine name) of the series; raises on DB errors."""
    row = fetch_all(
        "SELECT s.MachineID, m.Maschine AS MachineName "
        "FROM tblTrialSeries s "
        "LEFT JOIN tblMaschine m ON m.ID = s.MachineID "
        "WHERE s.ID = ?",
        [series_id],
    )
    cur_machine_id = int(row[0]["MachineID"]) if row and row[0]["MachineID"] else None
    cur_machine_name = str(row[0]["MachineName"] or "") if row else ""
    return cur_machine_id, cur_machine_name


def list_machines() -> List[Dict[str, Any]]:
    """[{"ID", "Maschine"}] sorted by name (jokers included); [] on DB errors."""
    try:
        machines = fetch_all(
            "SELECT ID, Maschine FROM tblMaschine ORDER BY Maschine", [])
    except Exception:
        machines = []
    return [{"ID": int(r["ID"]), "Maschine": str(r["Maschine"] or "")} for r in machines]


def change_machine(series_id: int, new_machine_id: int, user: Any = None) -> None:
    """UPDATE tblTrialSeries.MachineID (raises on error), then the stealth
    feature tracking (never raises)."""
    execute(
        "UPDATE tblTrialSeries SET MachineID = ? WHERE ID = ?",
        [new_machine_id, series_id],
    )
    # Feature-Tracking
    try:
        execute(
            "INSERT INTO tblFeatureUsage (FeatureID, UserID, ExtraInfo) VALUES (?, ?, ?)",
            [FEATURE_CHANGE_MACHINE, legacy_feature_user_id(user), str(series_id)],
        )
    except Exception:
        pass


# ---------------------------------------------------------------- priority / notes

def set_backlog_prio(series_id: Any, new_prio: Any) -> None:
    sql = """
            UPDATE tblTrialSeries
            SET [BacklogPrio] = ?
            WHERE [ID] = ?;
        """
    execute(sql, [new_prio, series_id])


def save_notes(series_id: Any, text: Optional[str]) -> None:
    """tblTrialSeries.Notes; "" is stored as NULL."""
    execute(
        "UPDATE tblTrialSeries SET Notes = ? WHERE ID = ?",
        [text or None, series_id],
    )


# ---------------------------------------------------------------- copy series (jet rows)

def series_jet_groups(series_id: int, housing_names: Optional[Dict[Any, str]] = None) -> List[Dict[str, Any]]:
    """Jet rows of a series for "Copy TrialSeries" / the Jet tab: tblTrial
    JetID, Jet Plate, Air Pressure and HousingID grouped by (JetID, pressure):
    [{"JetID", "JetName", "Plates", "Pressure", "PlateList", "HousingID",
    "HousingName"}]. housing_names = {HousingID: name} (None: tblHousing)."""
    from db.series_tables import get_columns_map, table_exists
    from ui.text_normalize import resolve_field
    # Resolve columns from tblTrial
    if not table_exists("tblTrial"):
        return []
    cmap_t = get_columns_map("tblTrial")
    col_sid = resolve_field(
        ["TrialSeriesID", "SeriesID", "SerieID"], cmap_t) or "TrialSeriesID"
    col_jet = resolve_field(["JetID", "Jet"], cmap_t) or "JetID"
    col_plate = resolve_field(
        ["Jet Plate", "JetPlate", "JetPlates", "Plate"], cmap_t) or "Jet Plate"
    col_press = resolve_field(["Air Pressure (bar)", "Air Pressure",
                              "Pressure (bar)", "Pressure"], cmap_t) or "Air Pressure (bar)"
    col_housing = resolve_field(["HousingID", "Housing"], cmap_t)

    if col_housing:
        select_housing = f", [{col_housing}] AS JHOUSING"
    else:
        select_housing = ""

    rows = fetch_all(
        f"SELECT [{col_jet}] AS JID, [{col_plate}] AS JPLATE, [{col_press}] AS JPRESS"
        f"{select_housing} "
        f"FROM [tblTrial] WHERE [{col_sid}] = ?",
        [series_id]
    )
    if not rows:
        return []

    if housing_names is None:
        from db.machine_data import load_housing_lookup
        housing_name_by_id = dict(load_housing_lookup().map)
    else:
        housing_name_by_id = housing_names

    # Build JetID -> JetName mapping
    jet_name_by_id = {}
    try:
        if table_exists("tblDTYJets"):
            cmap_j = get_columns_map("tblDTYJets")
            col_j_id = resolve_field(["ID"], cmap_j) or "ID"
            col_j_name = resolve_field(
                ["Jet", "Name", "Bezeichnung"], cmap_j) or "Jet"
            for r in fetch_all(f"SELECT [{col_j_id}] AS JID, [{col_j_name}] AS JName FROM [tblDTYJets]"):
                try:
                    jet_name_by_id[int(r['JID'])] = str(r['JName'])
                except Exception:
                    pass
    except Exception:
        pass

    # Group by (JetID, Pressure)
    from collections import defaultdict
    groups = defaultdict(lambda: set())
    pressure_by_key = {}
    housing_by_key: dict = {}
    for r in rows:
        try:
            jid = int(r.get("JID") or r.get("JetID"))
        except Exception:
            jid = r.get("JID") or r.get("JetID")
        plate = r.get("JPLATE") or r.get("JetPlate")
        # parse plate to int if possible
        try:
            plate = int(str(plate).strip())
        except Exception:
            try:
                plate = int(float(str(plate).strip()))
            except Exception:
                plate = str(plate).strip()
        pres_raw = str(r.get("JPRESS", "") or r.get("Pressure", "")).replace(",", ".").strip()
        try:
            pres_val = float(pres_raw)
        except Exception:
            pres_val = pres_raw  # keep as string
        key = (jid, pres_val)
        if plate not in (None, ""):
            groups[key].add(plate)
        pressure_by_key[key] = pres_val
        # Housing: erstes gefundenes Housing pro Gruppe übernehmen
        if key not in housing_by_key and col_housing:
            raw_hid = r.get("JHOUSING")
            if raw_hid is not None:
                try:
                    housing_by_key[key] = int(raw_hid)
                except Exception:
                    housing_by_key[key] = raw_hid

    out: List[Dict[str, Any]] = []
    for (jid, pres_val), plates in groups.items():
        plates_list = sorted([int(x) for x in plates if isinstance(x, (int, float))] + [int(float(x))
                             for x in plates if isinstance(x, str) and x.replace('.', '', 1).isdigit()]) if plates else []
        # normalize pressure display
        if isinstance(pres_val, (int, float)):
            p_disp = f"{float(pres_val):.2f}".rstrip("0").rstrip(".")
        else:
            p_disp = str(pres_val)
        # jet name
        jname = jet_name_by_id.get(jid, "")
        # housing
        housing_id = housing_by_key.get((jid, pres_val))
        housing_name = ""
        if housing_id is not None:
            try:
                housing_name = housing_name_by_id.get(int(housing_id), "")
            except Exception:
                housing_name = housing_name_by_id.get(housing_id, "")
        out.append({
            "JetID": jid, "JetName": jname, "Plates": len(plates_list),
            "Pressure": p_disp, "PlateList": ",".join(str(x) for x in plates_list),
            "HousingID": housing_id, "HousingName": housing_name,
        })
    return out
