"""Smart Chart saved views - bigger ConfigJSON (Nutzerwunsch 2026-11-13: big dashboards could not be saved).

    python tools/smart_chart_views_migration.py status   [--target dev|prod]
    python tools/smart_chart_views_migration.py apply    [--target dev|prod]
    python tools/smart_chart_views_migration.py rollback [--target dev|prod]

apply:    tblSmartChartView.ConfigJSON TEXT (64 KB) -> MEDIUMTEXT (16 MB)
rollback: back to TEXT - refused while a view is bigger than 64 KB (it would be cut off).

Without --target only dev_local (TRIPPLET_MODE=dev_local, database tripplet_dev_local). dev / prod only on
explicit request of the user. Older TrippleT versions keep working (they still refuse views over 64 KB when
saving, db/smart_chart_views.config_limit() lets newer versions use the bigger column).
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


def _type(c) -> str:
    rows = c.fetch_all("SELECT DATA_TYPE AS t FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
                       "AND LOWER(TABLE_NAME) = 'tblsmartchartview' AND COLUMN_NAME = 'ConfigJSON'")
    return str(rows[0]["t"]).lower() if rows else ""


def main(argv) -> None:
    args = list(argv)
    target = "dev_local"
    if "--target" in args:
        i = args.index("--target")
        target = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
    cmd = args[0] if args else "status"
    c = _guard(target)
    t = _type(c)
    if not t:
        raise SystemExit("tblSmartChartView does not exist here.")
    biggest = c.fetch_all("SELECT COALESCE(MAX(LENGTH(ConfigJSON)), 0) AS n FROM tblSmartChartView")[0]["n"]
    print(f"{c.current_db_name()}: ConfigJSON is {t}, biggest view {int(biggest):,} bytes")
    if cmd == "apply":
        if t == "mediumtext":
            print("already MEDIUMTEXT - nothing to do")
            return
        c.execute("ALTER TABLE tblSmartChartView MODIFY ConfigJSON MEDIUMTEXT NOT NULL")
        print("done: ConfigJSON is now", _type(c))
    elif cmd == "rollback":
        if t == "text":
            print("already TEXT - nothing to do")
            return
        if int(biggest) > 65000:
            raise SystemExit("Refused: a view is bigger than 64 KB and would be cut off.")
        c.execute("ALTER TABLE tblSmartChartView MODIFY ConfigJSON TEXT NOT NULL")
        print("done: ConfigJSON is now", _type(c))
    elif cmd != "status":
        raise SystemExit(f"unknown command {cmd!r}")


if __name__ == "__main__":
    main(sys.argv[1:])
