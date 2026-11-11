"""DTY process selection - database changes, ONLY for dev_local.

    python tools/dty_process_migration.py status   [--target prod]
    python tools/dty_process_migration.py apply    [--target prod]
    python tools/dty_process_migration.py rollback [--target prod]

Without --target it only runs on dev_local (TRIPPLET_MODE=dev_local). With
--target prod it runs on the production database (TRIPPLET_MODE=prod, database
"tripplet") - only on explicit request of the user (rolled out 2026-11-09).

apply:
  1. creates tbldtyprocess and fills it with db.dty_process.SEED
  2. adds tbltrial.DTYProcessID (INT NULL)
  3. existing trials on DTY machines (tblmaschine.Maschinentyp = 1):
     Elastane if a ply has YarnUse "Elastane" or an elastane yarn
     (tblyarn.Material = EL), otherwise Standard
  4. tblMachineFields: new row "DTY Process" (FieldNumber 0, dropdown) per
     DTY machine
  5. lookup tables tbldtyroute / tbldtymergepoint and per ply
     tbltrialsettings.DTYRouteID / MergeIntoPly / MergePointID, shown in
     Machine Data as "Route" / "Merge into ply" / "Merge point" (FieldNumber 2,
     right after Position) on DTY machines
  6. tblMachineFields: pre-intermingling (W0-W1 OF, PreIntermingling*) and
     the third jet (W3_*) move from R&D Machine Data to Machine Data
     (RDSetting 1 -> 2) on DTY machines.
  RDSetting 2 = "Machine Data, new versions only": older TrippleT exe show only
  RDSetting 0/1 and simply skip these rows (also Create Experiment and the label
  printer ignore them); ui/machine_tab.py shows 0 and 2.
  The old RDSetting values and the new row IDs are written to a backup file
  (%LOCALAPPDATA%/TrippleT/backups/dty_process_migration_<db>.json).

rollback: exactly the other way round (restores RDSetting from the backup,
deletes the new rows, drops the column and the table). Afterwards the
database is as before apply.

Refuses to run unless TRIPPLET_MODE and database match the target
(dev_local -> tripplet_dev_local, prod -> tripplet).
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TARGETS = {"dev_local": "tripplet_dev_local", "prod": "tripplet"}
NEW_ONLY = 2   # RDSetting for rows only new versions show (see docstring)
MOVED_FIELDS = ["W0_W1_OF", "PreInterminglingHousing", "PreInterminglingJets",
                "PreInterminglingAirPressure", "W3_Housing", "W3_Jet", "W3_AirPressure"]


def _guard(target: str = "dev_local"):
    if target not in TARGETS:
        raise SystemExit(f"Refused: unknown target {target!r}.")
    if os.environ.get("TRIPPLET_MODE") != target:
        raise SystemExit(f"Refused: set TRIPPLET_MODE={target} for target {target}.")
    from db import connection as c
    if c.is_offline_mode() or c.current_db_name() != TARGETS[target]:
        raise SystemExit(f"Refused: database is {c.current_db_name()!r}, expected {TARGETS[target]!r}.")
    return c


def _backup_path(db_name: str) -> pathlib.Path:
    base = pathlib.Path(os.environ.get("LOCALAPPDATA") or pathlib.Path.home()) / "TrippleT" / "backups"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"dty_process_migration_{db_name}.json"


def _has_column(c, table: str, col: str) -> bool:
    return any(str(r.get("Field")).lower() == col.lower()
               for r in c.fetch_all(f"SHOW COLUMNS FROM {table}"))


def _dty_machine_ids(c):
    from db.dty_process import DTY_MACHINE_TYPE
    return [int(r["ID"]) for r in c.fetch_all(
        "SELECT ID FROM tblmaschine WHERE Maschinentyp = ? ORDER BY ID", [DTY_MACHINE_TYPE])]


def status(c) -> dict:
    from db.dty_process import TABLE, TRIAL_COLUMN
    st = {
        "table": c.fetch_all(f"SHOW TABLES LIKE '{TABLE}'") != [],
        "column": _has_column(c, "tbltrial", TRIAL_COLUMN),
        "backup": _backup_path(c.current_db_name()).exists(),
    }
    if st["column"]:
        st["trials_by_process"] = c.fetch_all(
            f"SELECT {TRIAL_COLUMN} AS p, COUNT(*) AS n FROM tbltrial GROUP BY {TRIAL_COLUMN}")
    st["field_rows"] = c.fetch_all(
        "SELECT MachineID, OriginalName, RDSetting FROM tblmachinefields "
        "WHERE OriginalName IN ('DTYProcessID','DTYRouteID','MergeIntoPly','MergePointID','W0_W1_OF','W3_Jet') "
        "ORDER BY MachineID, OriginalName")
    st["ply_columns"] = [col for col in ("DTYRouteID", "MergeIntoPly", "MergePointID")
                         if _has_column(c, "tbltrialsettings", col)]
    return st


def apply(c) -> None:
    from db import dty_process as dp
    bpath = _backup_path(c.current_db_name())
    if bpath.exists() or c.fetch_all(f"SHOW TABLES LIKE '{dp.TABLE}'"):
        raise SystemExit("Already applied (backup file or table exists) - run rollback first.")
    machines = _dty_machine_ids(c)
    ph_m = ",".join(["?"] * len(machines))
    ph_f = ",".join(["?"] * len(MOVED_FIELDS))
    old_rd = c.fetch_all(
        f"SELECT ID, RDSetting FROM tblmachinefields WHERE MachineID IN ({ph_m}) "
        f"AND OriginalName IN ({ph_f})", machines + MOVED_FIELDS)
    backup = {"applied_at": _dt.datetime.now().isoformat(timespec="seconds"),
              "db": c.current_db_name(), "machines": machines,
              "old_rdsetting": [{"ID": int(r["ID"]), "RDSetting": r["RDSetting"]} for r in old_rd],
              "inserted_field_ids": []}
    # write the backup first, so a crash half-way can still be rolled back
    bpath.write_text(json.dumps(backup, indent=1), encoding="utf-8")

    c.execute(
        f"CREATE TABLE {dp.TABLE} ("
        "ID INT NOT NULL AUTO_INCREMENT PRIMARY KEY, Code VARCHAR(10) NOT NULL, "
        "Name VARCHAR(80) NOT NULL, Description VARCHAR(255) NULL, SortOrder INT NOT NULL DEFAULT 0, "
        "UsesPreJet TINYINT NOT NULL DEFAULT 0, UsesJet3 TINYINT NOT NULL DEFAULT 0, "
        "GlobalID VARCHAR(38) NULL)")
    for row in dp.SEED:
        c.execute(f"INSERT INTO {dp.TABLE} (ID, Code, Name, Description, SortOrder, UsesPreJet, "
                  f"UsesJet3, GlobalID) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  list(row) + [c.new_global_id()])
    c.execute(f"ALTER TABLE tbltrial ADD COLUMN {dp.TRIAL_COLUMN} INT NULL")
    c.execute(
        f"UPDATE tbltrial t JOIN tbltrialseries s ON s.ID = t.TrialSeriesID "
        f"JOIN tblmaschine m ON m.ID = s.MachineID "
        f"SET t.{dp.TRIAL_COLUMN} = CASE WHEN EXISTS (SELECT 1 FROM tbltrialsettings ts "
        f"LEFT JOIN tblyarn y ON y.ID = ts.YarnID "
        f"WHERE ts.TrialID = t.ID AND (ts.YarnUseID = ? OR y.Material = ?)) THEN ? ELSE ? END "
        f"WHERE m.Maschinentyp = ?",
        [dp.ELASTANE_YARN_USE_ID, dp.ELASTANE_MATERIAL_ID, dp.ELASTANE_ID, dp.STANDARD_ID,
         dp.DTY_MACHINE_TYPE])
    for mid in machines:
        new_id = c.execute_insert(
            "INSERT INTO tblmachinefields (MachineID, FieldNumber, FieldName, FieldFunction, "
            "StorageTable, OriginalName, RDSetting) VALUES (?, 0, ?, ?, 'tbltrial', ?, ?)",
            [mid, dp.FIELD_NAME, f"dropdown:{dp.LOOKUP_NAME}", dp.TRIAL_COLUMN, NEW_ONLY])
        backup["inserted_field_ids"].append(int(new_id))
        bpath.write_text(json.dumps(backup, indent=1), encoding="utf-8")
    # how the plies run together (per ply)
    for table, seed in ((dp.ROUTE_TABLE, dp.ROUTE_SEED), (dp.MERGE_TABLE, dp.MERGE_SEED)):
        c.execute(f"CREATE TABLE {table} (ID INT NOT NULL AUTO_INCREMENT PRIMARY KEY, "
                  "Code VARCHAR(20) NOT NULL, Name VARCHAR(80) NOT NULL, "
                  "SortOrder INT NOT NULL DEFAULT 0, GlobalID VARCHAR(38) NULL)")
        for row in seed:
            c.execute(f"INSERT INTO {table} (ID, Code, Name, SortOrder, GlobalID) VALUES (?, ?, ?, ?, ?)",
                      list(row) + [c.new_global_id()])
    for col in (dp.ROUTE_COLUMN, dp.MERGE_INTO_COLUMN, dp.MERGE_POINT_COLUMN):
        c.execute(f"ALTER TABLE tbltrialsettings ADD COLUMN {col} INT NULL")
    ply_fields = [(dp.ROUTE_FIELD, f"dropdown:{dp.ROUTE_LOOKUP}", dp.ROUTE_COLUMN),
                  (dp.MERGE_INTO_FIELD, "onlyInteger", dp.MERGE_INTO_COLUMN),
                  (dp.MERGE_POINT_FIELD, f"dropdown:{dp.MERGE_LOOKUP}", dp.MERGE_POINT_COLUMN)]
    for mid in machines:
        for name, func, col in ply_fields:
            new_id = c.execute_insert(
                "INSERT INTO tblmachinefields (MachineID, FieldNumber, FieldName, FieldFunction, "
                "StorageTable, OriginalName, RDSetting) VALUES (?, 2, ?, ?, 'tbltrialsettings', ?, ?)",
                [mid, name, func, col, NEW_ONLY])
            backup["inserted_field_ids"].append(int(new_id))
        bpath.write_text(json.dumps(backup, indent=1), encoding="utf-8")
    if old_rd:
        ph = ",".join(["?"] * len(old_rd))
        c.execute(f"UPDATE tblmachinefields SET RDSetting = ? WHERE ID IN ({ph})",
                  [NEW_ONLY] + [int(r["ID"]) for r in old_rd])
    print(f"Applied on {c.current_db_name()}. Backup: {bpath}")


def rollback(c) -> None:
    from db import dty_process as dp
    bpath = _backup_path(c.current_db_name())
    if not bpath.exists():
        raise SystemExit(f"No backup file {bpath} - nothing to roll back.")
    backup = json.loads(bpath.read_text(encoding="utf-8"))
    ids = backup.get("inserted_field_ids") or []
    if ids:
        c.execute(f"DELETE FROM tblmachinefields WHERE ID IN ({','.join(['?'] * len(ids))})", ids)
    # catch rows inserted before a crash that never reached the backup file
    for col, name in ((dp.TRIAL_COLUMN, dp.FIELD_NAME), (dp.ROUTE_COLUMN, dp.ROUTE_FIELD),
                      (dp.MERGE_INTO_COLUMN, dp.MERGE_INTO_FIELD),
                      (dp.MERGE_POINT_COLUMN, dp.MERGE_POINT_FIELD)):
        c.execute("DELETE FROM tblmachinefields WHERE OriginalName = ? AND FieldName = ?", [col, name])
    for r in backup.get("old_rdsetting") or []:
        c.execute("UPDATE tblmachinefields SET RDSetting = ? WHERE ID = ?", [r["RDSetting"], r["ID"]])
    if _has_column(c, "tbltrial", dp.TRIAL_COLUMN):
        c.execute(f"ALTER TABLE tbltrial DROP COLUMN {dp.TRIAL_COLUMN}")
    c.execute(f"DROP TABLE IF EXISTS {dp.TABLE}")
    for col in (dp.ROUTE_COLUMN, dp.MERGE_INTO_COLUMN, dp.MERGE_POINT_COLUMN):
        if _has_column(c, "tbltrialsettings", col):
            c.execute(f"ALTER TABLE tbltrialsettings DROP COLUMN {col}")
    for table in (dp.ROUTE_TABLE, dp.MERGE_TABLE):
        c.execute(f"DROP TABLE IF EXISTS {table}")
    done = bpath.with_name(bpath.stem + "_rolledback_" + _dt.datetime.now().strftime("%Y%m%d_%H%M%S") + ".json")
    bpath.rename(done)
    print(f"Rolled back on {c.current_db_name()}. Backup kept as {done}")


def main(argv) -> None:
    args = list(argv[1:])
    target = "dev_local"
    if "--target" in args:
        i = args.index("--target")
        target = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
    if len(args) != 1 or args[0] not in ("status", "apply", "rollback"):
        raise SystemExit(__doc__)
    argv = [argv[0], args[0]]
    c = _guard(target)
    if argv[1] == "status":
        for k, v in status(c).items():
            print(f"{k}: {v}")
    elif argv[1] == "apply":
        apply(c)
    else:
        rollback(c)


if __name__ == "__main__":
    main(sys.argv)
