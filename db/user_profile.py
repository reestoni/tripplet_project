"""user_profile.py - everything the app keeps about the logged-in user, without Qt.

Shared by the desktop login (ui/screen_login.py fills app_meta.current_user
with it) and the web app (tripplet_web, per request). Every field is read on
its own and falls back quietly, exactly like the login did before
(2026-11-13: moved out of LoginScreen._attempt_login).
"""
from __future__ import annotations

from typing import Any, Dict

from db.connection import (
    get_user_access_level,
    get_user_access_right,
    get_user_accent_colour,
    get_user_admin_box,
    get_user_first_last_name,
    get_user_id,
)


def load_profile(username: str) -> Dict[str, Any]:
    """{"id", "username", "first_name", "last_name", "access_level",
    "access_right", "admin_box", "accent_colour"} - same keys as app_meta.current_user."""
    try:
        access_level = int(get_user_access_level(username) or 0)
    except Exception:
        access_level = 0
    try:
        access_right = get_user_access_right(username)   # role name, e.g. "Admin"
    except Exception:
        access_right = None
    try:
        admin_box = bool(get_user_admin_box(username))    # tblUser.AdminBox
    except Exception:
        admin_box = False
    try:
        uid = get_user_id(username)
    except Exception:
        uid = None
    try:
        first_name, last_name = get_user_first_last_name(username)
    except Exception:
        first_name, last_name = "", ""
    try:
        accent_colour = get_user_accent_colour(username)  # e.g. "#39a650"
    except Exception:
        accent_colour = None
    return {
        "id": uid,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "access_level": int(access_level or 0),
        "access_right": access_right,
        "admin_box": admin_box,
        "accent_colour": accent_colour,
    }
