"""Fill Route / Merge into ply / Merge point for existing DTY trials.

--mode elastane (default, Nutzerwunsch 2026-11-07): elastane ply -> Route =
    Separate source, Merge into = the other (POY) ply, Merge point = LW 2.
--mode two_ply (Nutzerwunsch 2026-11-09): trials with exactly two plies and no
    elastane -> both plies Route = Full; the second ply Merge into = Ply 1 (the
    lower ply number), Merge point = LW 2.

    python tools/dty_elastane_merge_backfill.py [--mode two_ply] [--target prod]            # dry run
    python tools/dty_elastane_merge_backfill.py [--mode two_ply] [--target prod] --apply    # write

Same guard as tools/dty_process_migration.py (TRIPPLET_MODE and database must
match the target, default dev_local). Only trials with exactly one elastane ply
(YarnUse "Elastane" or yarn material EL) and exactly one other ply are touched,
and only plies whose three fields are still empty. Before writing, the old
values go to %LOCALAPPDATA%/TrippleT/backups/elastane_merge_before_<db>_<time>.json;
every change is written to the change log (tblChangeLog, source "import").
Undo: restore the values from the backup file (or the migration's rollback,
which drops the columns altogether).
"""
from __future__ import annotations

import datetime
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def plan(c):
    from db import dty_process as dp
    rows = c.fetch_all(f"""
        SELECT ts.ID, ts.TrialID, ts.Ply, t.TrialSeriesID AS sid,
               (COALESCE(ts.YarnUseID, 0) = ? OR COALESCE(y.Material, 0) = ?) AS is_el,
               ts.{dp.ROUTE_COLUMN} AS r, ts.{dp.MERGE_INTO_COLUMN} AS i, ts.{dp.MERGE_POINT_COLUMN} AS p
        FROM tbltrialsettings ts JOIN tbltrial t ON t.ID = ts.TrialID
        JOIN tbltrialseries s ON s.ID = t.TrialSeriesID JOIN tblmaschine m ON m.ID = s.MachineID
        LEFT JOIN tblyarn y ON y.ID = ts.YarnID
        WHERE m.Maschinentyp = ? AND ts.TrialID IN (
            SELECT ts2.TrialID FROM tbltrialsettings ts2 LEFT JOIN tblyarn y2 ON y2.ID = ts2.YarnID
            WHERE ts2.YarnUseID = ? OR y2.Material = ?)
        ORDER BY ts.TrialID, ts.ID""",
        [dp.ELASTANE_YARN_USE_ID, dp.ELASTANE_MATERIAL_ID, dp.DTY_MACHINE_TYPE,
         dp.ELASTANE_YARN_USE_ID, dp.ELASTANE_MATERIAL_ID])
    by_trial = {}
    for r in rows:
        by_trial.setdefault(r["TrialID"], []).append(r)
    todo, skipped = [], []
    for tid, plies in by_trial.items():
        el = [p for p in plies if int(p["is_el"] or 0)]
        other = [p for p in plies if not int(p["is_el"] or 0)]
        m = re.search(r"\d+", str(other[0]["Ply"] or "")) if len(other) == 1 else None
        if len(el) != 1 or not m:
            skipped.append(tid)
            continue
        e = el[0]
        if any(e[k] not in (None, "", 0) for k in ("r", "i", "p")):
            continue   # already set by hand - leave it
        todo.append((e, int(m.group())))
    return by_trial, todo, skipped


def plan_two_ply(c):
    """[(row, {field: new value})] for two-ply trials without elastane; only
    empty fields are filled, plies with values set by hand are left alone."""
    from db import dty_process as dp
    rows = c.fetch_all(f"""
        SELECT ts.ID, ts.TrialID, ts.Ply, t.TrialSeriesID AS sid,
               (COALESCE(ts.YarnUseID, 0) = ? OR COALESCE(y.Material, 0) = ?) AS is_el,
               ts.{dp.ROUTE_COLUMN} AS r, ts.{dp.MERGE_INTO_COLUMN} AS i, ts.{dp.MERGE_POINT_COLUMN} AS p
        FROM tbltrialsettings ts JOIN tbltrial t ON t.ID = ts.TrialID
        JOIN tbltrialseries s ON s.ID = t.TrialSeriesID JOIN tblmaschine m ON m.ID = s.MachineID
        LEFT JOIN tblyarn y ON y.ID = ts.YarnID
        WHERE m.Maschinentyp = ?
        ORDER BY ts.TrialID, ts.ID""",
        [dp.ELASTANE_YARN_USE_ID, dp.ELASTANE_MATERIAL_ID, dp.DTY_MACHINE_TYPE])
    by_trial = {}
    for r in rows:
        by_trial.setdefault(r["TrialID"], []).append(r)
    route_full = next(k for k, v in dp.ROUTE_CODE.items() if v == "full")
    mp_lw2 = next(k for k, v in dp.MERGE_CODE.items() if v == "lw2")
    todo, skipped = [], []
    for tid, plies in by_trial.items():
        if len(plies) != 2 or any(int(p["is_el"] or 0) for p in plies):
            continue
        nos = [re.search(r"\d+", str(p["Ply"] or "")) for p in plies]
        if not all(nos):
            skipped.append(tid)
            continue
        main_p, other = sorted(zip(plies, [int(m.group()) for m in nos]), key=lambda x: x[1])
        empty = lambda v: v in (None, "", 0)
        if empty(main_p[0]["r"]):
            todo.append((main_p[0], {dp.ROUTE_COLUMN: route_full}))
        o = other[0]
        if all(empty(o[k]) for k in ("r", "i", "p")):
            todo.append((o, {dp.ROUTE_COLUMN: route_full, dp.MERGE_INTO_COLUMN: main_p[1],
                             dp.MERGE_POINT_COLUMN: mp_lw2}))
    return todo, skipped


def apply_changes(c, todo, label):
    """todo = [(row, {field: new})] -> backup JSON, UPDATE, change log."""
    from db import change_log
    from db import dty_process as dp
    cols = {"r": dp.ROUTE_COLUMN, "i": dp.MERGE_INTO_COLUMN, "p": dp.MERGE_POINT_COLUMN}
    old_of = lambda row, field: row[next(k for k, v in cols.items() if v == field)]
    base = pathlib.Path(os.environ.get("LOCALAPPDATA") or pathlib.Path.home()) / "TrippleT" / "backups"
    base.mkdir(parents=True, exist_ok=True)
    bfile = base / f"{label}_before_{c.current_db_name()}_{datetime.datetime.now():%Y%m%d_%H%M%S}.json"
    bfile.write_text(json.dumps([{"ID": row["ID"], **{f: old_of(row, f) for f in new}} for row, new in todo],
                                default=str, indent=0), encoding="utf-8")
    entries = {}
    for row, new in todo:
        sets = ", ".join(f"{f} = ?" for f in new)
        c.execute(f"UPDATE tbltrialsettings SET {sets} WHERE ID = ?", list(new.values()) + [row["ID"]])
        for f, v in new.items():
            entries.setdefault(row["sid"], []).append({"table": "tblTrialSettings", "row_id": row["ID"], "field": f,
                                                       "old": old_of(row, f), "new": v, "trial_id": row["TrialID"]})
    logged = sum(change_log.log_changes(v, series_id=sid, source="import") for sid, v in entries.items())
    print(f"written: {len(todo)} plies, change log entries: {logged}, backup: {bfile}")


def main(argv):
    args = list(argv[1:])
    target = "dev_local"
    if "--target" in args:
        i = args.index("--target")
        target = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
    do_apply = "--apply" in args
    mode = "elastane"
    if "--mode" in args:
        i = args.index("--mode")
        mode = args[i + 1] if i + 1 < len(args) else ""
    if mode not in ("elastane", "two_ply"):
        raise SystemExit(__doc__)
    from tools.dty_process_migration import _guard
    c = _guard(target)
    if mode == "two_ply":
        todo, skipped = plan_two_ply(c)
        trials = len({row["TrialID"] for row, _ in todo})
        print(f"{c.current_db_name()}: two-ply trials to fill {trials}, plies {len(todo)}, skipped {len(skipped)} {skipped[:10]}")
        print("examples:", [(row["TrialID"], row["Ply"], new) for row, new in todo[:4]])
        if not do_apply:
            print("dry run - nothing written (add --apply)")
            return
        apply_changes(c, todo, "two_ply_merge")
        return
    from db import dty_process as dp, change_log
    route_sep = next(k for k, v in dp.ROUTE_CODE.items() if v == "elastane")
    mp_lw2 = next(k for k, v in dp.MERGE_CODE.items() if v == "lw2")
    by_trial, todo, skipped = plan(c)
    print(f"{c.current_db_name()}: elastane trials {len(by_trial)}, to set {len(todo)}, skipped {len(skipped)} {skipped[:10]}")
    print("examples:", [(e['TrialID'], e['Ply'], '->', no) for e, no in todo[:3]])
    if not do_apply:
        print("dry run - nothing written (add --apply)")
        return
    base = pathlib.Path(os.environ.get("LOCALAPPDATA") or pathlib.Path.home()) / "TrippleT" / "backups"
    base.mkdir(parents=True, exist_ok=True)
    bfile = base / f"elastane_merge_before_{c.current_db_name()}_{datetime.datetime.now():%Y%m%d_%H%M%S}.json"
    bfile.write_text(json.dumps([{"ID": e["ID"], dp.ROUTE_COLUMN: e["r"], dp.MERGE_INTO_COLUMN: e["i"],
                                  dp.MERGE_POINT_COLUMN: e["p"]} for e, _ in todo], default=str, indent=0),
                     encoding="utf-8")
    entries = {}
    for e, no in todo:
        c.execute(f"UPDATE tbltrialsettings SET {dp.ROUTE_COLUMN} = ?, {dp.MERGE_INTO_COLUMN} = ?, "
                  f"{dp.MERGE_POINT_COLUMN} = ? WHERE ID = ?", [route_sep, no, mp_lw2, e["ID"]])
        for field, old, new in ((dp.ROUTE_COLUMN, e["r"], route_sep), (dp.MERGE_INTO_COLUMN, e["i"], no),
                                (dp.MERGE_POINT_COLUMN, e["p"], mp_lw2)):
            entries.setdefault(e["sid"], []).append({"table": "tblTrialSettings", "row_id": e["ID"], "field": field,
                                                     "old": old, "new": new, "trial_id": e["TrialID"]})
    logged = sum(change_log.log_changes(v, series_id=sid, source="import") for sid, v in entries.items())
    print(f"written: {len(todo)} plies, change log entries: {logged}, backup: {bfile}")


if __name__ == "__main__":
    main(sys.argv)
