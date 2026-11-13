"""db/usage_stats.py - Usage Stats without Qt (shared with the web) and the recycle bin preview helpers."""
import datetime
import subprocess
import sys
from pathlib import Path

from db import usage_stats as us

ROOT = Path(__file__).resolve().parents[1]


def test_qt_free():
    code = ("import sys; import db.usage_stats, db.recycle_bin; "
            "sys.exit(1 if any(m.startswith('PySide6') for m in sys.modules) else 0)")
    assert subprocess.run([sys.executable, "-c", code], cwd=str(ROOT)).returncode == 0


def test_summary_kind_key_and_order():
    t = datetime.datetime(2026, 11, 1)
    ev = [{"EventName": "help_search_open", "Detail": "Garn -> x", "Username": "a", "EventTime": t},
          {"EventName": "help_search_noresult", "Detail": "foo | hits=0", "Username": "b", "EventTime": t}]
    rows, summary = us.summarize_help_events(ev)
    assert [r["KindKey"] for r in rows] == ["help_search_noresult", "help_search_open"]
    assert rows[1]["Question"] == "garn" and "No result: 1" in summary


def test_load_stats_keys():
    if not us.available():
        return
    st = us.load_stats()
    assert set(st) == {"logins", "screens", "features", "ranking", "login_timeline", "help_events"}
    assert len(st["ranking"]) <= 15
