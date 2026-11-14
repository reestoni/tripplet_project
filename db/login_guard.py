"""login_guard.py - protection against password guessing (desktop + web login, Nutzerwunsch 2026-11-14).

After MAX_FAILS wrong passwords for one user name within WINDOW_MINUTES, that user name is locked until
WINDOW_MINUTES after the last of those failures; a successful login clears the count. While locked, the password
is not even checked (and such attempts are not counted, so the lock cannot be stretched forever).

The attempts are kept in tblUsageLog (EventType "security", EventName "login_failed" / "login_ok", Username =
the typed user name in lower case) - no new table, and desktop and web count together because both write there.
Time is the database's NOW(), so clocks of PCs/servers do not matter.

Best effort the other way round: if the log cannot be read or written (table missing, offline mode), nobody is
locked out - the password check itself still applies.
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

MAX_FAILS = 5
WINDOW_MINUTES = 15
EVENT_TYPE = "security"


def _key(username: str) -> str:
    return (username or "").strip().lower()[:100]


def _available() -> bool:
    try:
        from db.connection import is_offline_mode, table_exists
        return not is_offline_mode() and table_exists("tblUsageLog")
    except Exception:
        return False


def _recent_failures(username: str):
    """(failures since the last successful login within the window, newest first; DB 'now')."""
    from db.connection import fetch_all
    rows = fetch_all(
        "SELECT EventName, EventTime, NOW() AS Now FROM tblUsageLog "
        "WHERE Username = ? AND EventType = ? AND EventTime >= NOW() - INTERVAL %d MINUTE "
        "ORDER BY EventTime DESC, ID DESC LIMIT 50" % WINDOW_MINUTES,
        [_key(username), EVENT_TYPE],
    )
    fails = []
    now = None
    for r in rows or []:
        now = r.get("Now") or now
        if r.get("EventName") == "login_ok":
            break
        if r.get("EventName") == "login_failed":
            fails.append(r.get("EventTime"))
    return fails, now


def lock_status(username: str) -> Tuple[bool, int]:
    """(locked, minutes until it is unlocked)."""
    if not _key(username) or not _available():
        return False, 0
    try:
        fails, now = _recent_failures(username)
    except Exception:
        return False, 0
    if len(fails) < MAX_FAILS or now is None:
        return False, 0
    # unlocked WINDOW_MINUTES after the newest failure
    left = (fails[0] - now).total_seconds() + WINDOW_MINUTES * 60
    if left <= 0:
        return False, 0
    return True, max(1, math.ceil(left / 60))


def _write(username: str, name: str, source: str) -> None:
    from db.connection import execute
    execute("INSERT INTO tblUsageLog (UserID, Username, EventType, EventName, Detail) VALUES (NULL, ?, ?, ?, ?)",
            [_key(username), EVENT_TYPE, name, (source or "")[:255]])


def record_failure(username: str, source: str = "") -> Optional[int]:
    """Count one wrong password; returns the attempts left before the lock (None = unknown)."""
    if not _key(username) or not _available():
        return None
    try:
        _write(username, "login_failed", source)
        fails, _now = _recent_failures(username)
        return max(0, MAX_FAILS - len(fails))
    except Exception:
        return None


def record_success(username: str, source: str = "") -> None:
    if not _key(username) or not _available():
        return
    try:
        _write(username, "login_ok", source)
    except Exception:
        pass
