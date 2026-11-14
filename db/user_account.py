# db/user_account.py
"""Personal account settings without Qt - shared by the desktop (Settings dialog,
Backlog welcome line, Change Password screen) and the web app (tripplet_web).
Moved from ui/widgets/user_settings_dialog.py, ui/screen_backlog.py and
ui/screen_change_pw.py on 2026-11-13, rules unchanged.

- Welcome message (tblUser.WelcomeMessage, max. WELCOME_MAX_LEN, shown on the Backlog)
- Accent colour (tblUser.AccentColour)
- Password change: check_password_change() returns an error code (texts per
  caller), change_password() checks and writes (Argon2 via db.connection)."""
from __future__ import annotations

import re
from typing import Any, Optional

WELCOME_MAX_LEN = 45
DEFAULT_ACCENT = "#39a650"
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


# ── welcome message ─────────────────────────────────────────────────────
def load_welcome_message(user_id: Any) -> str:
    if not user_id:
        return ""
    try:
        from db.connection import fetch_all
        rows = fetch_all("SELECT WelcomeMessage FROM tblUser WHERE ID = ?", [user_id])
        return str((rows[0].get("WelcomeMessage") if rows else None) or "")
    except Exception:
        return ""


def save_welcome_message(user_id: Any, text: str) -> None:
    if not user_id:
        return
    from db.connection import execute
    value = (text or "").strip()[:WELCOME_MAX_LEN] or None
    execute("UPDATE tblUser SET WelcomeMessage = ? WHERE ID = ?", [value, user_id])


def format_welcome(welcome_message: Optional[str], first_name: str) -> str:
    """Backlog headline: "<message>, <first name>" or "Welcome, <first name>"."""
    msg = (welcome_message or "").strip()
    fn = (first_name or "").strip()
    if msg:
        return f"{msg}, {fn}".strip().strip(",")
    return f"Welcome, {fn}".strip()


# ── accent colour ───────────────────────────────────────────────────────
def is_valid_colour(hex_val: str) -> bool:
    return bool(_HEX.match(hex_val or ""))


def save_accent(username: str, hex_val: str) -> None:
    if username:
        from db.connection import execute
        execute("UPDATE tblUser SET AccentColour = ? WHERE Username = ?", [hex_val, username])


# ── password ────────────────────────────────────────────────────────────
# codes in the order of the desktop checks
PW_NO_USER = "no_user"            # username empty / unknown
PW_INCOMPLETE = "incomplete"      # not all three fields filled
PW_WRONG_OLD = "wrong_old"        # old password not correct
PW_MISMATCH = "mismatch"          # new != repeat (case-sensitive)
PW_SAME_AS_OLD = "same_as_old"
PW_SAME_AS_USER = "same_as_user"  # case-insensitive
PW_UPDATE_FAILED = "update_failed"
PW_LOCKED = "locked"              # too many wrong passwords (db/login_guard.py)


def check_password_change(username: str, old: str, new: str, repeat: str) -> Optional[str]:
    """None = ok, otherwise one of the PW_* codes (same order as the desktop)."""
    from db.connection import user_exists, verify_user_password
    u = (username or "").strip()
    if not u or not user_exists(u):
        return PW_NO_USER
    if not (old and new and repeat):
        return PW_INCOMPLETE
    from db import login_guard
    if login_guard.lock_status(u)[0]:
        return PW_LOCKED
    if not verify_user_password(u, old):
        login_guard.record_failure(u, "change_password")
        return PW_WRONG_OLD
    if new != repeat:
        return PW_MISMATCH
    if new == old:
        return PW_SAME_AS_OLD
    if new.lower() == u.lower():
        return PW_SAME_AS_USER
    return None


def change_password(username: str, old: str, new: str, repeat: str) -> Optional[str]:
    """Checks and stores the new password (Argon2 hash). None = changed, else a PW_* code."""
    from db.connection import update_user_password
    err = check_password_change(username, old, new, repeat)
    if err:
        return err
    return None if update_user_password((username or "").strip(), new) else PW_UPDATE_FAILED
