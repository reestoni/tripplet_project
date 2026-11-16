# db/display_settings.py
"""Per-user display settings (tblUser.DisplaySettings, JSON) - Qt-free part of
ui/display_prefs.py, shared with the web app (tripplet_web). Keys and meaning:
see the docstring of ui/display_prefs.py. Moved unchanged 2026-11-13 (DEFAULTS,
cleaning, fitting into a short column); load()/save() read/write the settings
of ANY user (the desktop keeps its in-memory copy in display_prefs, the web
reads per request)."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

COLUMN = "DisplaySettings"

DEFAULTS: Dict[str, Any] = {"scale": 100, "contrast": False, "crosshair": False, "readbar": False,
                            "alert_marks": False, "cb_colours": False, "app_scale": 100,
                            "whats_new_seen": "", "recent_series": [], "start": "backlog", "smart_favs": [],
                            "theme": "classic"}   # web look: "classic" | "modern" | "night" | "blueprint" (2026-11-16, desktop ignores it)
SMART_FAVS_MAX = 40  # Smart Chart / Dashboards: favourite saved views (view IDs)
RECENT_MAX = 8  # Sidebar -> "Recent" (ui/recent_series.py)


def _clean_recent(v: Any) -> list:
    out = []
    for e in (v if isinstance(v, list) else [])[:RECENT_MAX]:
        try:
            out.append({"exp": int(e["exp"]), "series": int(e["series"]),
                        "eid": str(e.get("eid") or "")[:40], "name": str(e.get("name") or "")[:80]})
        except (KeyError, TypeError, ValueError):
            continue
    return out
_BOOL_KEYS = ("contrast", "crosshair", "readbar", "alert_marks", "cb_colours")
SCALE_MIN, SCALE_MAX, SCALE_STEP = 80, 300, 10
APP_SCALE_CHOICES = [100, 125, 150, 200]


def _clean(d: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(DEFAULTS)
    try:
        out["scale"] = max(SCALE_MIN, min(SCALE_MAX, int(d.get("scale", 100))))
    except (TypeError, ValueError):
        pass
    for k in _BOOL_KEYS:
        out[k] = bool(d.get(k, False))
    try:
        a = int(d.get("app_scale", 100))
        out["app_scale"] = a if a in APP_SCALE_CHOICES else 100
    except (TypeError, ValueError):
        pass
    out["whats_new_seen"] = str(d.get("whats_new_seen") or "")[:40]
    out["recent_series"] = _clean_recent(d.get("recent_series"))
    out["start"] = str(d.get("start") or "backlog")[:30]
    out["theme"] = d.get("theme") if d.get("theme") in ("modern", "night", "blueprint") else "classic"
    favs = []
    for v in d.get("smart_favs") or []:
        try:
            if int(v) not in favs:
                favs.append(int(v))
        except (TypeError, ValueError):
            continue
    out["smart_favs"] = favs[:SMART_FAVS_MAX]
    return out


_col_len: Dict[str, Any] = {}


def _column_max_len() -> int:
    """Length of tblUser.DisplaySettings (0 = unlimited / unknown)."""
    if "n" not in _col_len:
        try:
            from db.connection import fetch_all
            rows = fetch_all("SELECT CHARACTER_MAXIMUM_LENGTH AS n, DATA_TYPE AS t FROM information_schema.COLUMNS "
                             "WHERE TABLE_SCHEMA = DATABASE() AND LOWER(TABLE_NAME) = 'tbluser' "
                             "AND COLUMN_NAME = 'DisplaySettings'")
            n = rows[0].get("n") if rows else None
            _col_len["n"] = int(n) if n and str(rows[0].get("t") or "").lower() == "varchar" else 0
        except Exception:
            _col_len["n"] = 0
    return _col_len["n"]


def _fit(prefs: Dict[str, Any], max_len: int) -> str:
    """JSON of the settings - only what differs from DEFAULTS (_clean() fills in the rest);
    in a short column the oldest Recent entries are left out so the rest still gets saved."""
    data = {k: v for k, v in prefs.items() if v != DEFAULTS.get(k)}
    raw = json.dumps(data, separators=(",", ":"))
    while max_len and len(raw) > max_len and data.get("recent_series"):
        data["recent_series"] = data["recent_series"][:-1]
        raw = json.dumps(data, separators=(",", ":"))
    return raw


def has_column() -> bool:
    try:
        from db.connection import get_columns_map
        return COLUMN.lower() in get_columns_map("tblUser")
    except Exception:
        return False


def load(user_id: Any) -> Optional[Dict[str, Any]]:
    """Cleaned settings of a user from the DB; None without the column/user (caller falls back)."""
    if not user_id or not has_column():
        return None
    from db.connection import fetch_all
    rows = fetch_all("SELECT DisplaySettings FROM tblUser WHERE ID = ?", [user_id])
    if not rows:
        return None
    raw = rows[0].get("DisplaySettings")
    try:
        data = json.loads(raw) if raw else {}
    except ValueError:
        data = {}
    return _clean(data if isinstance(data, dict) else {})


def save(user_id: Any, prefs: Dict[str, Any]) -> bool:
    """Writes the (cleaned) settings; False without the column."""
    if not user_id or not has_column():
        return False
    from db.connection import execute
    execute("UPDATE tblUser SET DisplaySettings = ? WHERE ID = ?", [_fit(_clean(prefs), _column_max_len()), user_id])
    return True


def update(user_id: Any, **changes) -> Optional[Dict[str, Any]]:
    """Read - change - write for one user (web app). Returns the new settings or None."""
    cur = load(user_id)
    if cur is None:
        return None
    cur.update(changes)
    new = _clean(cur)
    save(user_id, new)
    return new


def smart_favourites(user_id: Any) -> list:
    """Favourite Smart Chart views / dashboards of a user (view IDs)."""
    return list((load(user_id) or {}).get("smart_favs") or [])


def toggle_smart_favourite(user_id: Any, view_id: int) -> Optional[bool]:
    """Star / unstar a view; True = now a favourite, None = could not be saved."""
    cur = load(user_id)
    if cur is None:
        return None
    favs = [int(v) for v in cur.get("smart_favs") or []]
    on = int(view_id) not in favs
    favs = ([int(view_id)] + favs) if on else [v for v in favs if v != int(view_id)]
    update(user_id, smart_favs=favs)
    return on


def push_recent(entries: list, entry: Dict[str, Any]) -> list:
    """Recent series list with `entry` on top (same series only once, max RECENT_MAX)."""
    rest = [x for x in (entries or []) if x.get("series") != entry.get("series")]
    return [entry] + rest[:RECENT_MAX - 1]
