"""Conclusion per trial series in the database (db/series_conclusion.py, Nutzerwunsch 2026-11-14).

    python tools/series_conclusion_migration.py status   [--target dev|prod]
    python tools/series_conclusion_migration.py apply    [--target dev|prod]
    python tools/series_conclusion_migration.py rollback [--target dev|prod]

apply:    creates tblSeriesConclusion (CREATE TABLE IF NOT EXISTS - nothing else is touched)
rollback: drops it again - refused while it holds conclusions.

Without --target only dev_local (TRIPPLET_MODE=dev_local, database tripplet_dev_local). dev / prod only on
explicit request of the user (planned together with the other DB changes). Older TrippleT versions are not
affected (they do not know the table); newer versions hide the conclusion while it is missing.
"""
from __future__ import annotations

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TARGETS = {"dev_local": "tripplet_dev_local", "dev": "tripplet_dev", "prod": "tripplet"}


def _guard(target: str):
    if target not in TARGETS:
        raise SystemExit(f"Refused: unknown target {target!r}.")
    if os.environ.get("TRIPPLET_MODE") != target:
        raise SystemExit(f"Refused: set TRIPPLET_MODE={target} for target {target}.")
    from db import connection as c
    if c.is_offline_mode() or c.current_db_name() != TARGETS[target]:
        raise SystemExit(f"Refused: database is {c.current_db_name()!r}, expected {TARGETS[target]!r}.")
    return c


def _exists(c) -> bool:
    return bool(c.fetch_all("SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() "
                            "AND LOWER(TABLE_NAME) = 'tblseriesconclusion'"))


def main(argv) -> None:
    args = list(argv)
    target = "dev_local"
    if "--target" in args:
        i = args.index("--target")
        target = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
    cmd = args[0] if args else "status"
    c = _guard(target)
    from db import series_conclusion as sc
    there = _exists(c)
    n = c.fetch_all("SELECT COUNT(*) AS n FROM tblSeriesConclusion")[0]["n"] if there else 0
    print(f"{c.current_db_name()}: tblSeriesConclusion {'exists, ' + str(n) + ' conclusions' if there else 'missing'}")
    if cmd == "apply":
        if there:
            print("already there - nothing to do")
            return
        c.execute(sc.CREATE_SQL)
        c._TABLE_EXISTS_CACHE.clear() if hasattr(c, "_TABLE_EXISTS_CACHE") else None
        print("done: tblSeriesConclusion created" if _exists(c) else "FAILED")
    elif cmd == "rollback":
        if not there:
            print("not there - nothing to do")
            return
        if n:
            raise SystemExit(f"Refused: the table holds {n} conclusions.")
        c.execute("DROP TABLE tblSeriesConclusion")
        print("done: tblSeriesConclusion dropped")
    elif cmd != "status":
        raise SystemExit(f"unknown command {cmd!r}")


if __name__ == "__main__":
    main(sys.argv[1:])
