# db/user_admin.py
"""Manage User (superusers) - Qt-free, shared by the desktop (ui/screen_manage_user.py) and the web app.

Moved out of the screen on 2026-11-13 without behaviour change (same SQL, same password rules, same
default username "newuser<n>"); the screen keeps its table, dialogs and colour picker.

    access_rights()                 [(ID, name, level)] of tblAccessRight
    load_users()                    tblUser rows without password columns
    column_roles(headers)           id / username / first / last / access / colour / active columns
    normalize_colour(value)         '#RRGGBB' or '' ('R,G,B', '#rgb', int 0xRRGGBB accepted)
    save_changes(rows)              UPDATE per changed row (only columns given)
    next_username(rows)             unique default "newuser", "newuser2", ... within the column length
    check_new_password(username, pw, repeat)   None or the desktop message
    create_user(username, pw, first, last, access_id)   new ID (Argon2 hash, Active = 1)
    reset_password(username, pw)    True / False (db.connection.update_user_password)
    delete_users(ids)
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from db.connection import execute, execute_insert, fetch_all, is_offline_mode
from ui.text_normalize import canon_simple as _canon

PASSWORD_COLS = {"pw", "pwhash", "pw_hash", "passwordhash", "password_hash", "passworthash"}
_HEX = re.compile(r"^#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")


def access_rights() -> List[Tuple[int, str, int]]:
    rows = fetch_all("SELECT [ID], [AccessRight], [AccessLevel] FROM [tblAccessRight] ORDER BY [AccessLevel]", [])
    return [(int(r["ID"]), str(r.get("AccessRight") or ""), int(r.get("AccessLevel") or 0)) for r in rows]


def load_users() -> List[Dict[str, Any]]:
    """All users, password columns removed (never shown, never sent anywhere)."""
    rows = fetch_all("SELECT * FROM [tblUser]", [])
    for r in rows:
        for k in [k for k in r if _canon(k) in PASSWORD_COLS]:
            r.pop(k, None)
    return rows


def column_roles(headers: List[str]) -> Dict[str, Optional[str]]:
    out: Dict[str, Optional[str]] = {k: None for k in ("id", "username", "first", "last", "access", "colour", "active")}
    for h in headers:
        k = _canon(h)
        if k == "id" and not out["id"]:
            out["id"] = h
        elif k == "username" and not out["username"]:
            out["username"] = h
        elif k in {"firstname", "first_name", "first"} and not out["first"]:
            out["first"] = h
        elif k in {"lastname", "last_name", "surname", "last"} and not out["last"]:
            out["last"] = h
        elif k in {"accessrights", "rights", "role"} and not out["access"]:
            out["access"] = h
        elif k in {"colour", "color"} and not out["colour"]:
            out["colour"] = h
        elif k == "active" and not out["active"]:
            out["active"] = h
    return out


def normalize_colour(value: Any) -> str:
    """'#RRGGBB' (upper case, like the desktop QColor.name) or '' for empty / invalid."""
    if value in (None, ""):
        return ""
    try:
        if isinstance(value, str):
            s = value.strip()
            if not s:
                return ""
            if _HEX.match(s):
                if len(s) == 4:
                    s = "#" + "".join(ch * 2 for ch in s[1:])
                return s.upper()
            if "," in s:
                r, g, b = (int(p.strip()) for p in s.split(",")[:3])
                if all(0 <= x <= 255 for x in (r, g, b)):
                    return f"#{r:02X}{g:02X}{b:02X}"
                return ""
        n = int(value)
        if 0 <= n <= 0xFFFFFF:
            return f"#{n:06X}"
    except Exception:
        pass
    return ""


def save_changes(rows: List[Dict[str, Any]], id_col: str = "ID") -> int:
    """UPDATE tblUser per row ({id_col: .., column: value}); returns the number of updated rows."""
    total = 0
    for r in rows:
        if id_col not in r:
            raise ValueError(f"Row has no '{id_col}' field; cannot save.")
        cols = [c for c in r if c != id_col and _canon(c) not in PASSWORD_COLS]
        if not cols:
            continue
        total += execute(f"UPDATE [tblUser] SET {', '.join(f'[{c}] = ?' for c in cols)} WHERE [{id_col}] = ?",
                         [r[c] for c in cols] + [r[id_col]]) or 0
    return total


def username_max_len() -> int:
    if is_offline_mode():
        return 32
    try:
        r = fetch_all("SELECT CHARACTER_MAXIMUM_LENGTH AS maxlen FROM information_schema.columns "
                      "WHERE table_schema = DATABASE() AND table_name = 'tbluser' AND LOWER(column_name) = 'username' "
                      "LIMIT 1", [])
        raw = (r[0].get("maxlen") if r and r[0].get("maxlen") is not None else (r[0].get("MAXLEN") if r else None))
        return int(raw) if raw is not None else 32
    except Exception:
        return 32


def existing_usernames(rows: Optional[List[Dict[str, Any]]] = None) -> set:
    rows = rows if rows is not None else load_users()
    out = set()
    for r in rows:
        for h, v in r.items():
            if _canon(h) == "username":
                if v:
                    out.add(str(v).strip().lower())
                break
    return out


def next_username(rows: Optional[List[Dict[str, Any]]] = None) -> str:
    """Unique default username ("newuser", "newuser2", ...) within the column length."""
    taken = existing_usernames(rows)
    max_len = username_max_len()
    base = "newuser"[:max_len] if max_len else "newuser"

    def cand(n: int) -> str:
        suffix = "" if n <= 1 else str(n)
        if not max_len:
            return f"{base}{suffix}"
        allowed = max_len - len(suffix)
        return suffix[-max_len:] if allowed <= 0 else f"{base[:allowed]}{suffix}"

    i, c = 1, cand(1)
    while c.lower() in taken and i < 10_000:
        i += 1
        c = cand(i)
    if c.lower() in taken:
        raise ValueError("Could not generate a unique Username within the column length constraint.")
    return c


def check_new_password(username: str, pw: str, repeat: str) -> Optional[str]:
    """The desktop rules for a new / reset password: not empty, not the username, both entries equal."""
    pw = (pw or "").strip()
    if not pw:
        return "Password cannot be empty."
    if pw.lower() == (username or "").strip().lower():
        return "Password must not be the same as the username."
    if pw != (repeat or "").strip():
        return "Passwords do not match."
    return None


def create_user(username: str, pw: str, first: str = "", last: str = "", access_id: Optional[int] = None) -> Optional[int]:
    """New tblUser row: username, Argon2 hash, names, access right (default: smallest ID), Active = 1, empty colour."""
    from db.connection import hash_password
    rows = fetch_all("SELECT * FROM [tblUser] LIMIT 1", [])
    headers = list(rows[0].keys()) if rows else ["ID", "FirstName", "LastName", "UserName", "pw_hash", "AccessRights", "Active", "Colour"]
    pw_hash_col = next((h for h in headers if _canon(h) in PASSWORD_COLS - {"pw"}), None)
    if not pw_hash_col:
        raise ValueError("tblUser has no pw_hash column (required for creating a new user).")
    if access_id is None:
        ids = sorted(i for i, _n, _l in access_rights())
        access_id = ids[0] if ids else 1
    values: Dict[str, Any] = {}
    for c in headers:
        k = _canon(c)
        if k == "id" or k in {"pw", "password", "pass", "passwd"}:
            continue
        if k in {"firstname", "first_name", "first"}:
            values[c] = (first or "").strip()
        elif k in {"lastname", "last_name", "surname", "last"}:
            values[c] = (last or "").strip()
        elif k == "username":
            values[c] = username.strip()
        elif c == pw_hash_col:
            values[c] = hash_password(pw.strip())
        elif k in {"accessrights", "rights", "role"}:
            values[c] = access_id
        elif k == "active":
            values[c] = 1
        elif k in {"colour", "color"}:
            values[c] = ""
    cols = list(values)
    return execute_insert(f"INSERT INTO [tblUser] ({', '.join(f'[{c}]' for c in cols)}) "
                          f"VALUES ({','.join(['?'] * len(cols))})", [values[c] for c in cols])


def reset_password(username: str, pw: str) -> bool:
    from db.connection import update_user_password
    return bool(update_user_password(username, pw.strip()))


def delete_users(ids: List[Any], id_col: str = "ID") -> int:
    if not ids:
        return 0
    execute(f"DELETE FROM [tblUser] WHERE [{id_col}] IN ({','.join(['?'] * len(ids))})", list(ids))
    return len(ids)
