# db/series_yarns.py
"""Data, plan and apply of the Yarns dialog (ui/series_yarns_dialog.py) -
Qt-free, shared with the web app; moved out of the dialog on 2026-11-13
without behaviour change (the dialog re-exports everything).

Yarns of a whole trial series in one table (Nutzerwunsch 2026-10-16,
replaces the old per-trial "Manage Plies" dialog).

    Ply   | Yarn              | Use | V1 | V2 | V3 ...
    Ply 1 | PES 167f48 DTY  v | -   | 1x | 1x | 2x
    Ply 2 | PA 78f68        v | -   | 1x | -  | 1x

- Click the yarn of a ply -> search a yarn -> the whole ply gets it (all
  trials, values stay; a linked spool is cleared - it was a spool of the
  old yarn). No more add + remove and no "Yarn Conflict".
- Click a trial cell: ply on/off for that trial; digit keys or right-click
  set the number of ends (one tblTrialSettings row per end).
- "+ Add ply" (catalog yarn) / "+ Trial output" (half-finished product of
  another trial, shadow yarn of screen_create_experiment) add a row that is
  on for every trial.
- Nothing is written until "Apply": a summary is shown, then everything is
  written in one transaction and logged (db/change_log.py, source "plies").

Data: tblTrialSettings rows (TrialID, YarnID, Ply, YarnUseID). A row of the
table is one (Ply, YarnID, YarnUseID) combination. Series rule (lab decision,
kept on purpose although it is not "logical"): a yarn always has the SAME
ply number in a series. So the same yarn as "Core" and as "Effect" is two
rows "Ply 1" with different uses; "+ Add ply" with a yarn of the series puts
it into its existing ply; changing the yarn of a ply changes all its rows and
refuses a yarn that already has another ply number. Old series where one ply
has different yarns show one row per yarn (amber mark), so nothing gets
mixed up. Every trial keeps at least one ply -
except reference samples (db/trial_reference.py): they may have no yarn at
all (a new one is created without plies), new plies are not switched on for
them automatically, and their columns are amber like in Show Experiment.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from db.yarn_colours import load_yarn_colours

MAX_ENDS = 20


def can_edit(user) -> bool:
    """Show Experiment opens the dialog editable from access level 2 on
    (read-only below; the recycle-bin preview counts as level 1)."""
    from db.series_actions import access_level
    return access_level(user) >= 2


# ── data ──────────────────────────────────────────────────────────────────
# A row of the table = one (Ply, YarnID, YarnUseID) combination. Series rule
# (decided by the lab, kept on purpose): a yarn always has the SAME ply number
# in a series - the same yarn used once as "Core" and once as "Effect" is two
# rows "Ply 1" with different uses, not "Ply 1" and "Ply 3".
@dataclass
class PlyRow:
    ply: str
    yarn_id: Optional[int]
    yarn_name: str
    use_id: Any = None                     # YarnUseID or None
    ends: Dict[int, int] = field(default_factory=dict)  # trial id -> number of rows
    orig_yarn_id: Optional[int] = None     # as loaded (key in the DB)
    orig_use_id: Any = None

    def key(self) -> Tuple[str, Optional[int], Any]:
        return (self.ply, self.yarn_id, self.use_id)


@dataclass
class State:
    trials: List[Tuple[int, Any, str]]     # (trial id, Versuchsnummer, column label)
    rows: List[PlyRow]
    refs: set = field(default_factory=set)  # trial ids of reference samples (may have no ply)


def ply_number(label: str) -> int:
    m = re.search(r"\d+", label or "")
    return int(m.group()) if m else 9999


def next_ply_label(rows: List[PlyRow]) -> str:
    used = {ply_number(r.ply) for r in rows}
    n = 1
    while n in used:
        n += 1
    return f"Ply {n}"


def ply_of_yarn(rows: List[PlyRow], yarn_id: Optional[int]) -> Optional[str]:
    """The ply number a yarn already has in the series (series rule), None if new."""
    for r in rows:
        if r.yarn_id == yarn_id:
            return r.ply
    return None


def load_state(series_pk: int) -> State:
    from db.connection import fetch_all
    from db.trial_reference import IS_REFERENCE_COL, format_trial_number, has_reference_columns, is_reference_value
    ref_sel = f", {IS_REFERENCE_COL} AS IsRef" if has_reference_columns() else ""
    trows = fetch_all(f"SELECT ID, Versuchsnummer{ref_sel} FROM tblTrial WHERE TrialSeriesID = ? "
                      f"ORDER BY Versuchsnummer", [series_pk])
    trials = [(int(r["ID"]), r["Versuchsnummer"], format_trial_number(r["Versuchsnummer"])) for r in trows]
    refs = {int(r["ID"]) for r in trows if is_reference_value(r.get("IsRef"))}
    if not trials:
        return State([], [], refs)
    ph = ",".join("?" for _ in trials)
    srows = fetch_all(
        f"SELECT ts.TrialID, ts.Ply, ts.YarnID, ts.YarnUseID, y.Name AS YarnName "
        f"FROM tblTrialSettings ts LEFT JOIN tblYarn y ON y.ID = ts.YarnID WHERE ts.TrialID IN ({ph})",
        [t[0] for t in trials])
    by_key: Dict[Tuple[str, Optional[int], Any], PlyRow] = {}
    for r in srows:
        yid = int(r["YarnID"]) if r.get("YarnID") is not None else None
        uid = int(r["YarnUseID"]) if r.get("YarnUseID") is not None else None
        key = ((r.get("Ply") or "").strip(), yid, uid)
        row = by_key.get(key)
        if row is None:
            row = by_key[key] = PlyRow(key[0], yid, str(r.get("YarnName") or "(no yarn)"), uid,
                                       orig_yarn_id=yid, orig_use_id=uid)
        tid = int(r["TrialID"])
        row.ends[tid] = row.ends.get(tid, 0) + 1
    rows = sorted(by_key.values(), key=lambda r: (ply_number(r.ply), r.ply, r.yarn_name,
                                                   -1 if r.use_id is None else r.use_id))
    return State(trials, rows, refs)


def mixed_plies(rows: List[PlyRow]) -> set:
    """Ply labels with more than one yarn (old data, against the series rule)."""
    yarns: Dict[str, set] = {}
    for r in rows:
        yarns.setdefault(r.ply, set()).add(r.yarn_id)
    return {p for p, y in yarns.items() if len(y) > 1}


def trials_without_ply(state: State) -> List[str]:
    """Trials (not reference samples) that would be left without a ply."""
    return [label for tid, _v, label in state.trials
            if tid not in state.refs and not any(r.ends.get(tid, 0) > 0 for r in state.rows)]


def duplicate_rows(state: State) -> List[PlyRow]:
    """Rows with the same ply, yarn AND use as an earlier row - can't be told apart."""
    seen, dup = set(), []
    for r in state.rows:
        if r.key() in seen:
            dup.append(r)
        seen.add(r.key())
    return dup


def plan(before: State, after: State) -> List[Dict[str, Any]]:
    """Differences as operations (rows of `after` are matched to `before` by
    position - the dialog never reorders or deletes rows, removing = all 0).
    Every operation names the row's key AS LOADED ("match"), apply_plan()
    resolves the affected DB rows before it changes anything."""
    ops: List[Dict[str, Any]] = []
    n_old = len(before.rows)
    for i, new in enumerate(after.rows):
        old = before.rows[i] if i < n_old else None
        match = (old.ply, old.yarn_id, old.use_id) if old else None
        if old is not None and (new.yarn_id != old.yarn_id or new.use_id != old.use_id):
            ops.append({"op": "change", "match": match, "trials": [t for t, n in old.ends.items() if n > 0],
                        "new_yarn": new.yarn_id, "new_use": new.use_id,
                        "yarn_changed": new.yarn_id != old.yarn_id, "use_changed": new.use_id != old.use_id,
                        "ply": old.ply, "old_name": old.yarn_name, "new_name": new.yarn_name,
                        "old_use": old.use_id})
        for tid, _v, label in after.trials:
            n_old_ends = old.ends.get(tid, 0) if old else 0
            n_new = new.ends.get(tid, 0)
            if n_new > n_old_ends:
                ops.append({"op": "add", "trial": tid, "label": label, "ply": new.ply, "yarn": new.yarn_id,
                            "use": new.use_id, "n": n_new - n_old_ends, "more_ends": n_old_ends > 0,
                            "yarn_name": new.yarn_name})
            elif n_new < n_old_ends:
                ops.append({"op": "remove", "trial": tid, "label": label, "match": match, "ply": old.ply,
                            "use": old.use_id, "n": n_old_ends - n_new, "all": n_new == 0,
                            "yarn_name": old.yarn_name})
    return ops


def describe(ops: List[Dict[str, Any]], use_names: Optional[Dict[Any, str]] = None) -> List[str]:
    """Readable summary (English, UI text)."""
    names = use_names or {}

    def use(u):
        return names.get(u, "—") if u is not None else "—"

    def tag(ply, name, u):
        return f"{ply} ({name}" + (f", {use(u)}" if u is not None else "") + ")"

    lines: List[str] = []
    for o in ops:
        if o["op"] != "change":
            continue
        n = len(o["trials"])
        if o["yarn_changed"]:
            lines.append(f"{o['ply']}: {o['old_name']} → {o['new_name']}"
                         + (f", use {use(o['old_use'])} → {use(o['new_use'])}" if o["use_changed"] else "")
                         + f" ({n} trials)")
        else:
            lines.append(f"{o['ply']} ({o['old_name']}): use {use(o['old_use'])} → {use(o['new_use'])} ({n} trials)")
    adds: Dict[str, List[str]] = {}
    rems: Dict[str, List[str]] = {}
    for o in ops:
        if o["op"] == "add":
            adds.setdefault(tag(o["ply"], o["yarn_name"], o["use"]), []).append(
                o["label"] + (f" +{o['n']} end" + ("s" if o["n"] > 1 else "") if o.get("more_ends")
                              else (f" ({o['n']} ends)" if o["n"] > 1 else "")))
        elif o["op"] == "remove":
            rems.setdefault(tag(o["ply"], o["yarn_name"], o["use"]), []).append(
                o["label"] + ("" if o["all"] else f" -{o['n']} end" + ("s" if o["n"] > 1 else "")))
    for t, labels in adds.items():
        lines.append(f"{t} added to: " + ", ".join(labels))
    for t, labels in rems.items():
        lines.append(f"{t} removed from: " + ", ".join(labels))
    return lines


def apply_plan(ops: List[Dict[str, Any]], series_pk: int, user: Any = None) -> None:
    """Writes the operations in one transaction, then logs them.
    Order: removes (by the loaded key), then all changes - their DB rows are
    looked up BEFORE the first update, so swapping uses between two rows
    can't mix them up - then the new rows. user: dict of the user for the
    change history (None = the desktop's app_meta.current_user)."""
    from db import change_log
    from db.connection import get_columns_map, get_connection, new_global_id
    cols = {k.lower() for k in get_columns_map("tblTrialSettings")}
    has_gid, has_use, has_spool = "globalid" in cols, "yarnuseid" in cols, "spoolid" in cols
    log: List[Dict[str, Any]] = []

    def where_key(match):
        ply, yarn, use = match
        sql, params = ["Ply = ?"], [ply]
        sql.append("YarnID IS NULL" if yarn is None else "YarnID = ?")
        params += [] if yarn is None else [yarn]
        if has_use:
            sql.append("YarnUseID IS NULL" if use is None else "YarnUseID = ?")
            params += [] if use is None else [use]
        return " AND ".join(sql), params

    with get_connection() as cn:
        cur = cn.cursor()
        try:
            for o in ops:
                if o["op"] != "remove":
                    continue
                w, p = where_key(o["match"])
                cur.execute(f"SELECT ID FROM tblTrialSettings WHERE TrialID = ? AND {w} ORDER BY ID DESC",
                            [o["trial"]] + p)
                ids = [r[0] for r in cur.fetchall()][:o["n"]]
                if ids:
                    cur.execute(f"DELETE FROM tblTrialSettings WHERE ID IN ({','.join('?' for _ in ids)})", ids)
                    log.extend({"table": "tblTrialSettings", "row_id": rid, "field": "Ply", "old": o["ply"],
                                "new": None, "trial_id": o["trial"]} for rid in ids)

            changes = []
            for o in ops:
                if o["op"] != "change" or not o["trials"]:
                    continue
                w, p = where_key(o["match"])
                ph = ",".join("?" for _ in o["trials"])
                cur.execute(f"SELECT ID, TrialID FROM tblTrialSettings WHERE TrialID IN ({ph}) AND {w}",
                            list(o["trials"]) + p)
                changes.append((o, cur.fetchall()))
            for o, hit in changes:
                if not hit:
                    continue
                sets, vals = [], []
                if o["yarn_changed"]:
                    sets.append("YarnID = ?")
                    vals.append(o["new_yarn"])
                    if has_spool:
                        sets.append("SpoolID = NULL")
                if o["use_changed"] and has_use:
                    sets.append("YarnUseID = ?")
                    vals.append(o["new_use"])
                if not sets:
                    continue
                ids = [rid for rid, _t in hit]
                cur.execute(f"UPDATE tblTrialSettings SET {', '.join(sets)} WHERE ID IN ({','.join('?' for _ in ids)})",
                            vals + ids)
                for rid, tid in hit:
                    if o["yarn_changed"]:
                        log.append({"table": "tblTrialSettings", "row_id": rid, "field": "YarnID",
                                    "old": o["match"][1], "new": o["new_yarn"], "trial_id": tid})
                    if o["use_changed"]:
                        log.append({"table": "tblTrialSettings", "row_id": rid, "field": "YarnUseID",
                                    "old": o["match"][2], "new": o["new_use"], "trial_id": tid})

            for o in ops:
                if o["op"] != "add":
                    continue
                for _ in range(o["n"]):
                    c, v = ["TrialID", "YarnID", "Ply"], [o["trial"], o["yarn"], o["ply"]]
                    if has_use and o.get("use") is not None:
                        c.append("YarnUseID")
                        v.append(o["use"])
                    if has_gid:
                        c.append("GlobalID")
                        v.append(new_global_id())
                    cur.execute(f"INSERT INTO tblTrialSettings ({', '.join(c)}) VALUES ({', '.join('?' for _ in v)})", v)
                    rid = getattr(cur, "lastrowid", None)
                    if rid:
                        log.append({"table": "tblTrialSettings", "row_id": rid, "field": "Ply", "old": None,
                                    "new": o["ply"], "trial_id": o["trial"]})
            cn.commit()
        except Exception:
            try:
                cn.rollback()
            except Exception:
                pass
            raise
    if user is None:
        change_log.log_changes(log, series_id=series_pk, source="plies")
    else:
        change_log.log_changes(log, series_id=series_pk, source="plies", user_id=(user or {}).get("id"))


# ── yarn search ───────────────────────────────────────────────────────────
def load_yarns() -> List[Dict[str, Any]]:
    """Catalog yarns (no shadow yarns) with a search text."""
    from db.connection import fetch_all, get_columns_map
    cols = {k.lower(): v for k, v in get_columns_map("tblYarn").items()}
    extra = [cols[c] for c in ("kurzname", "garntyp", "material", "titer") if c in cols]
    where = f" WHERE {cols['sourcetrialid']} IS NULL" if "sourcetrialid" in cols else ""
    sel = ", ".join(["ID", "Name"] + extra)
    colours, _ = load_yarn_colours()
    out = []
    for r in fetch_all(f"SELECT {sel} FROM tblYarn{where} ORDER BY Name"):
        colour = colours.get(int(r["ID"]), "")
        words = " ".join(str(r.get(c) or "") for c in ["Name"] + extra) + " " + colour
        out.append({"id": int(r["ID"]), "name": str(r.get("Name") or ""), "colour": colour,
                    "search": words.lower()})
    return out


def filter_yarns(yarns: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
    """All words must occur (order free): "167 dty" finds "PES 167f48 DTY"."""
    words = (text or "").lower().split()
    return [y for y in yarns if all(w in y["search"] for w in words)]
