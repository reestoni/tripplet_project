"""jet_air_sync.py - "Sync physical jets" of the Jet Air Consumption tab (Qt-free, desktop + web).

tblLaborJetAirConsumption is only filled additively when a series / trials are created
(db/trial_actions.save_jet_air_consumption_rows). When the jet or plate of a trial is changed
later, the grid shows jets no trial uses any more and misses the new ones. The sync:
- adds the missing jet x plate x pressure rows (empty, values are entered afterwards),
- offers to delete grid rows whose jet/plate no trial uses any more - but only when they are
  completely empty (AirConsumption / AtmosphericPressure / AirTemperature all NULL); rows with
  measured values are only listed, never deleted automatically.

plan_sync() only reads; apply_sync() writes the plan in one transaction.
(Moved from ShowExperimentScreen._sync_jet_air_physical_jets / _get_current_physical_jets_for_series,
2026-11-13 - behaviour unchanged, plus a real transaction.)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from db.connection import fetch_all, get_connection, new_global_id
from db.series_tables import get_columns_map, table_exists
from ui.text_normalize import resolve_field

TABLE = "tblLaborJetAirConsumption"


def current_physical_jets(series_id: int) -> List[Tuple[int, Optional[str]]]:
    """(JetID, JetPlate) currently set in the trials of the series (ply jet, else trial jet)."""
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
    return [(int(r["JetID"]), r.get("JetPlate")) for r in rows]


def _plate_key(p: Any) -> str:
    return "" if p is None else str(p)


def plan_sync(series_id: int) -> Dict[str, Any]:
    """{"status": "unavailable" | "nothing_found" | "in_sync" | "changes",
        "to_insert": [(JetID, plate, pressure)], "orphans": [{jet_id, jet, plate, has_data, ids}],
        "delete_ids": [...], "lines": [message lines like the desktop question]}"""
    out: Dict[str, Any] = {"status": "unavailable", "to_insert": [], "orphans": [], "delete_ids": [], "lines": []}
    if not table_exists(TABLE) or not series_id:
        return out
    current_jets = current_physical_jets(series_id)
    rows = fetch_all(
        f"SELECT [ID],[JetID],[JetPlate],[AirPressure],[AirConsumption],"
        f"[AtmosphericPressure],[AirTemperature] FROM {TABLE} WHERE [TrialSeriesID] = ?",
        [series_id],
    )
    pressures = sorted({float(r["AirPressure"]) for r in rows if r.get("AirPressure") is not None})
    if not current_jets or not pressures:
        out["status"] = "nothing_found"
        return out

    existing_keys = {
        (int(r["JetID"]), _plate_key(r.get("JetPlate")), round(float(r["AirPressure"]), 6))
        for r in rows if r.get("JetID") is not None and r.get("AirPressure") is not None
    }
    current_key_set = {(jid, _plate_key(plate)) for jid, plate in current_jets}

    to_insert: List[Tuple[int, Optional[str], float]] = []
    for jid, plate in current_jets:
        for p in pressures:
            key = (jid, _plate_key(plate), round(p, 6))
            if key not in existing_keys:
                to_insert.append((jid, plate, p))

    orphan_combo_rows: Dict[Tuple[int, str], List[dict]] = {}
    for r in rows:
        if r.get("JetID") is None:
            continue
        combo = (int(r["JetID"]), _plate_key(r.get("JetPlate")))
        if combo not in current_key_set:
            orphan_combo_rows.setdefault(combo, []).append(r)

    out["to_insert"] = to_insert
    if not to_insert and not orphan_combo_rows:
        out["status"] = "in_sync"
        return out

    jet_ids = sorted({jid for jid, _ in current_jets} | {c[0] for c in orphan_combo_rows})
    jet_name_map: Dict[int, str] = {}
    try:
        if jet_ids and table_exists("tblDTYJets"):
            ph = ",".join(["?"] * len(jet_ids))
            for jr in fetch_all(f"SELECT [ID], [Jet] AS JName FROM tblDTYJets WHERE [ID] IN ({ph})", jet_ids):
                jet_name_map[int(jr["ID"])] = str(jr.get("JName") or "")
    except Exception:
        pass

    lines: List[str] = []
    if to_insert:
        lines.append(f"{len(to_insert)} missing row(s) will be added (empty, enter the values afterwards).")
    delete_ids: List[int] = []
    if orphan_combo_rows:
        lines.append("\nFolgende Duese(n)/Plate(s) im Grid entsprechen keinem aktuellen Trial mehr:")
        for (jid, plate), rr in sorted(orphan_combo_rows.items()):
            jname = jet_name_map.get(jid, f"Jet {jid}")
            has_data = any(
                r.get("AirConsumption") is not None
                or r.get("AtmosphericPressure") is not None
                or r.get("AirTemperature") is not None
                for r in rr
            )
            if has_data:
                lines.append(f"  - {jname} / Plate {plate or '-'} (has measured values - will NOT be deleted)")
            else:
                lines.append(f"  - {jname} / Plate {plate or '-'} (empty - will be deleted)")
                delete_ids.extend(r["ID"] for r in rr)
            out["orphans"].append({"jet_id": jid, "jet": jname, "plate": plate or "", "has_data": has_data,
                                   "ids": [int(r["ID"]) for r in rr]})
    out.update(status="changes", delete_ids=delete_ids, lines=lines)
    return out


def apply_sync(series_id: int, plan: Dict[str, Any], user_id: Any) -> None:
    """Writes a plan of plan_sync() in one transaction (raises on error)."""
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute("START TRANSACTION")   # the pool runs autocommit - a real transaction
        for jid, plate, p in plan.get("to_insert") or []:
            cur.execute(
                f"INSERT INTO {TABLE} (TrialSeriesID, JetID, JetPlate, AirPressure, UserID, GlobalID) "
                f"VALUES (?,?,?,?,?,?)",
                [series_id, jid, plate, p, user_id, new_global_id()],
            )
        delete_ids = plan.get("delete_ids") or []
        if delete_ids:
            ph = ",".join(["?"] * len(delete_ids))
            cur.execute(f"DELETE FROM {TABLE} WHERE [ID] IN ({ph})", list(delete_ids))
        cn.commit()
