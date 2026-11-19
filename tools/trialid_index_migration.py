"""Index on TrialID for the lab tables and the change log (found 2026-11-19 with the slow Quick Scan).

    python tools/trialid_index_migration.py status   [--target dev|prod]
    python tools/trialid_index_migration.py apply    [--target dev|prod]
    python tools/trialid_index_migration.py rollback [--target dev|prod]

Almost every table that hangs on a trial by TrialID had no index on that column, so each "rows of this trial /
these trials" read the whole table (tbllaboritematlab: 57'000 rows). Every lab tab in Show Experiment, the
report, Smart Chart, exports and Quick Scan read that way.

apply:    ALTER TABLE ... ADD INDEX idx_<table>_trialid (TrialID), online (ALGORITHM=INPLACE, LOCK=NONE),
          only on tables of TABLES that exist, have a TrialID column and no index starting with TrialID yet.
          No data is changed; older TrippleT versions do not notice anything (an index is invisible to SQL).
rollback: drops exactly the indexes named idx_<table>_trialid again (never anything else).

Without --target only dev_local (TRIPPLET_MODE=dev_local, database tripplet_dev_local). dev / prod only on
explicit request of the user.
"""
from __future__ import annotations

import os
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TARGETS = {"dev_local": "tripplet_dev_local", "dev": "tripplet_dev", "prod": "tripplet"}

# tables read "by TrialID" in the apps (lower case, as on the server)
TABLES = [
    "tbllaboritematlab", "tbllaboritematplus", "tbllabortiter", "tbllaborstatimatm", "tbllaborstatimatds",
    "tbllabordtyomat", "tbllaboratyomat", "tbllaborwaterbath", "tbllaborekb", "tbllaborrapid600",
    "tbllaborheissluftschrumpf", "tbllaborkochschrumpf", "tbllaboratyshrinkage", "tblchangelog",
]


def index_name(table: str) -> str:
    return f"idx_{table.lower()}_trialid"


def _guard(target: str):
    if target not in TARGETS:
        raise SystemExit(f"Refused: unknown target {target!r}.")
    if os.environ.get("TRIPPLET_MODE") != target:
        raise SystemExit(f"Refused: set TRIPPLET_MODE={target} for target {target}.")
    from db import connection as c
    if c.is_offline_mode() or c.current_db_name() != TARGETS[target]:
        raise SystemExit(f"Refused: database is {c.current_db_name()!r}, expected {TARGETS[target]!r}.")
    return c


def survey(c) -> list[dict]:
    """One entry per table of TABLES: real name, exists, has TrialID, existing TrialID index, ours, rows."""
    names = {r["t"].lower(): r["t"] for r in c.fetch_all(
        "SELECT TABLE_NAME AS t FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()", [])}
    out = []
    for tb in TABLES:
        real = names.get(tb)
        e = {"table": tb, "name": real, "exists": bool(real), "has_col": False, "indexed_by": None, "ours": False, "rows": None}
        if real:
            e["has_col"] = bool(c.fetch_all(
                "SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = ? "
                "AND LOWER(COLUMN_NAME) = 'trialid'", [real]))
            first = c.fetch_all(
                "SELECT INDEX_NAME AS i FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() "
                "AND TABLE_NAME = ? AND SEQ_IN_INDEX = 1 AND LOWER(COLUMN_NAME) = 'trialid'", [real])
            idx = [r["i"] for r in first]
            e["ours"] = index_name(tb) in [i.lower() for i in idx]
            e["indexed_by"] = idx[0] if idx else None
            e["rows"] = c.fetch_all(f"SELECT COUNT(*) AS n FROM `{real}`", [])[0]["n"]
        out.append(e)
    return out


def _print(rows: list[dict]) -> None:
    for e in rows:
        if not e["exists"]:
            state = "table missing"
        elif not e["has_col"]:
            state = "no TrialID column"
        elif e["indexed_by"]:
            state = f"indexed ({e['indexed_by']})"
        else:
            state = "NO INDEX"
        print(f"  {e['table']:28s} {state:40s} {'' if e['rows'] is None else e['rows']:>8}")


def main(argv) -> None:
    args = list(argv)
    target = "dev_local"
    if "--target" in args:
        i = args.index("--target")
        target = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
    cmd = args[0] if args else "status"
    c = _guard(target)
    rows = survey(c)
    print(f"{c.current_db_name()}: TrialID indexes")
    _print(rows)
    if cmd == "apply":
        todo = [e for e in rows if e["exists"] and e["has_col"] and not e["indexed_by"]]
        if not todo:
            print("nothing to do")
            return
        for e in todo:
            t0 = time.time()
            c.execute(f"ALTER TABLE `{e['name']}` ADD INDEX `{index_name(e['table'])}` (`TrialID`), "
                      f"ALGORITHM=INPLACE, LOCK=NONE")
            print(f"  + {index_name(e['table'])} ({time.time() - t0:.1f} s)")
        missing = [e["table"] for e in survey(c) if e["exists"] and e["has_col"] and not e["indexed_by"]]
        print("done" if not missing else f"FAILED for: {', '.join(missing)}")
    elif cmd == "rollback":
        ours = [e for e in rows if e["ours"]]
        if not ours:
            print("no index of this script there - nothing to do")
            return
        for e in ours:
            c.execute(f"ALTER TABLE `{e['name']}` DROP INDEX `{index_name(e['table'])}`")
            print(f"  - {index_name(e['table'])}")
        print("done")
    elif cmd != "status":
        raise SystemExit(f"unknown command {cmd!r}")


if __name__ == "__main__":
    main(sys.argv[1:])
