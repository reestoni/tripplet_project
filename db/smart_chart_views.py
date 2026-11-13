# db/smart_chart_views.py
"""Saved views of the new Smart Chart (ui/screen_smart_chart.py): filters +
chart settings under a name. The FILTER is saved, not the trial list, so a
view always shows today's data. Private by default, "Shared" (IsShared)
makes it visible to everybody.

Sharing (Etappe 6, Nutzerentscheid 2026-10-30): the creator - and only the
creator - shares a view with single people and/or user groups (the access
rights of tblAccessRight: read, write, admin, superuser - a group share
holds for exactly that group), each "view" or "edit" (tblSmartChartViewShare,
one row per person OR group). Edit = may save changes to it (not share it,
not delete it). Deleting: creator or superuser. Without the share table only
the old "Shared with everybody" works.

Best effort like the other small tables: without tblSmartChartView the
Save/Open buttons are disabled.
"""
from __future__ import annotations

import datetime
import json
from typing import Any, Dict, List, Optional

TABLE = "tblSmartChartView"

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS tblSmartChartView (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(200) NOT NULL,
    UserID INT NULL,
    IsShared TINYINT(1) NOT NULL DEFAULT 0,
    ConfigJSON MEDIUMTEXT NOT NULL,
    CreatedAt DATETIME NOT NULL,
    UpdatedAt DATETIME NULL,
    INDEX ix_scview_user (UserID)
)
"""


SHARE_TABLE = "tblSmartChartViewShare"

CREATE_SHARE_SQL = """
CREATE TABLE IF NOT EXISTS tblSmartChartViewShare (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    ViewID INT NOT NULL,
    UserID INT NULL,
    AccessRightID INT NULL,
    CanEdit TINYINT(1) NOT NULL DEFAULT 0,
    CreatedAt DATETIME NOT NULL,
    INDEX ix_scshare_view (ViewID),
    INDEX ix_scshare_user (UserID),
    INDEX ix_scshare_group (AccessRightID)
)
"""

RIGHT_OWNER, RIGHT_EDIT, RIGHT_VIEW = "owner", "edit", "view"


def create_table() -> None:
    """Only call deliberately - dev/prod only with explicit permission."""
    from db import connection
    connection.execute(CREATE_SQL)
    connection._COLUMNS_MAP_CACHE.clear()


def create_share_table() -> None:
    """Only call deliberately - dev/prod only with explicit permission."""
    from db import connection
    connection.execute(CREATE_SHARE_SQL)
    connection._COLUMNS_MAP_CACHE.clear()


def shares_available() -> bool:
    try:
        from db.connection import get_columns_map
        return available() and "canedit" in get_columns_map(SHARE_TABLE)
    except Exception:
        return False


def available() -> bool:
    try:
        from db.connection import get_columns_map, is_offline_mode
        if is_offline_mode():
            return False
        return "configjson" in get_columns_map(TABLE)
    except Exception:
        return False


def _user():
    try:
        import app_meta
        return (app_meta.current_user or {}).get("id"), int(app_meta.access_level() or 0)
    except Exception:
        return None, 0


def _group(uid) -> Optional[int]:
    """The user's group = tblUser.AccessRights (an ID of tblAccessRight)."""
    if uid is None:
        return None
    try:
        from db.connection import fetch_all
        rows = fetch_all("SELECT AccessRights FROM tblUser WHERE ID = ?", [int(uid)])
        v = rows[0].get("AccessRights") if rows else None
        return int(v) if v is not None else None
    except Exception:
        return None


def is_owner(view: Dict[str, Any]) -> bool:
    uid, _lvl = _user()
    return uid is not None and view.get("UserID") is not None and int(view["UserID"]) == int(uid)


def can_change(view: Dict[str, Any]) -> bool:
    """Save changes to the view: creator, people/groups with an edit share, superuser."""
    _uid, lvl = _user()
    return lvl >= 4 or is_owner(view) or view.get("MyRight") == RIGHT_EDIT


def can_delete(view: Dict[str, Any]) -> bool:
    _uid, lvl = _user()
    return lvl >= 4 or is_owner(view)


def can_share(view: Dict[str, Any]) -> bool:
    """Only the creator shares his view (Nutzerentscheid)."""
    return is_owner(view)


def right_for(view_owner: Any, is_shared: Any, shares: List[Dict[str, Any]], uid: Any, group: Any) -> Optional[str]:
    """"owner" / "edit" / "view" / None for one user - pure, for tests."""
    if uid is not None and view_owner is not None and int(view_owner) == int(uid):
        return RIGHT_OWNER
    mine = [sh for sh in shares
            if (sh.get("UserID") is not None and uid is not None and int(sh["UserID"]) == int(uid))
            or (sh.get("AccessRightID") is not None and group is not None and int(sh["AccessRightID"]) == int(group))]
    if any(int(sh.get("CanEdit") or 0) for sh in mine):
        return RIGHT_EDIT
    if mine or int(is_shared or 0):
        return RIGHT_VIEW
    return None


def list_views(kind: Optional[str] = None) -> List[Dict[str, Any]]:
    """Views this user may open, newest first, with OwnerName and MyRight
    ("owner"/"edit"/"view"). kind="dashboard" = only dashboards."""
    if not available():
        return []
    from db.connection import fetch_all
    uid, _lvl = _user()
    me = uid if uid is not None else -1
    group = None
    shares: Dict[int, List[Dict[str, Any]]] = {}
    if shares_available():
        group = _group(uid)
        for sh in fetch_all("SELECT ViewID, UserID, AccessRightID, CanEdit FROM tblSmartChartViewShare "
                            "WHERE UserID = ? OR AccessRightID = ?", [me, group if group is not None else -1]):
            shares.setdefault(int(sh["ViewID"]), []).append(sh)
    rows = fetch_all(
        "SELECT v.ID, v.Name, v.UserID, v.IsShared, v.ConfigJSON, v.CreatedAt, v.UpdatedAt, "
        "TRIM(CONCAT(COALESCE(u.FirstName,''), ' ', COALESCE(u.LastName,''))) AS OwnerName "
        "FROM tblSmartChartView v LEFT JOIN tblUser u ON u.ID = v.UserID "
        "ORDER BY COALESCE(v.UpdatedAt, v.CreatedAt) DESC, v.ID DESC")
    out = []
    for r in rows:
        right = right_for(r.get("UserID"), r.get("IsShared"), shares.get(int(r["ID"]), []), uid, group)
        if right is None:
            continue
        if kind == "dashboard" and config_of(r).get("mode") != "dashboard":
            continue
        out.append({**r, "MyRight": right})
    return out


def get_view(view_id: int) -> Optional[Dict[str, Any]]:
    """One view with MyRight, if this user may open it."""
    return next((v for v in list_views() if int(v["ID"]) == int(view_id)), None)


def get_shares(view_id: int) -> List[Dict[str, Any]]:
    """[{UserID, AccessRightID, CanEdit, Name}] of a view."""
    if not shares_available():
        return []
    from db.connection import fetch_all
    return fetch_all(
        "SELECT s.UserID, s.AccessRightID, s.CanEdit, "
        "CASE WHEN s.UserID IS NOT NULL THEN TRIM(CONCAT(COALESCE(u.FirstName,''), ' ', COALESCE(u.LastName,''))) "
        "ELSE a.AccessRight END AS Name "
        "FROM tblSmartChartViewShare s LEFT JOIN tblUser u ON u.ID = s.UserID "
        "LEFT JOIN tblAccessRight a ON a.ID = s.AccessRightID WHERE s.ViewID = ? ORDER BY s.ID", [int(view_id)])


def set_shares(view_id: int, everybody: bool, entries: List[Dict[str, Any]]) -> None:
    """Replace the shares of a view: entries [{"UserID"|"AccessRightID", "CanEdit"}]."""
    from db.connection import execute
    now = datetime.datetime.now().replace(microsecond=0)
    execute("UPDATE tblSmartChartView SET IsShared = ? WHERE ID = ?", [1 if everybody else 0, int(view_id)])
    if not shares_available():
        return
    execute("DELETE FROM tblSmartChartViewShare WHERE ViewID = ?", [int(view_id)])
    for e in entries:
        uid, grp = e.get("UserID"), e.get("AccessRightID")
        if (uid is None) == (grp is None):
            continue
        execute("INSERT INTO tblSmartChartViewShare (ViewID, UserID, AccessRightID, CanEdit, CreatedAt) "
                "VALUES (?,?,?,?,?)", [int(view_id), uid, grp, 1 if e.get("CanEdit") else 0, now])


def share_targets() -> Dict[str, List[Dict[str, Any]]]:
    """People (active users) and groups (tblAccessRight) to share with."""
    from db.connection import fetch_all
    uid, _lvl = _user()
    people = [r for r in fetch_all(
        "SELECT ID, TRIM(CONCAT(COALESCE(FirstName,''), ' ', COALESCE(LastName,''))) AS Name FROM tblUser "
        "WHERE COALESCE(Active, 1) <> 0 ORDER BY FirstName, LastName") if uid is None or int(r["ID"]) != int(uid)]
    groups = fetch_all("SELECT ID, AccessRight AS Name FROM tblAccessRight ORDER BY ID")
    return {"people": people, "groups": groups}


def config_of(view: Dict[str, Any]) -> Dict[str, Any]:
    try:
        cfg = json.loads(view.get("ConfigJSON") or "{}")
        return cfg if isinstance(cfg, dict) else {}
    except (TypeError, ValueError):
        return {}


_limit: Dict[str, int] = {}


def config_limit() -> int:
    """Bytes a view may have: ConfigJSON TEXT = 64 KB, MEDIUMTEXT (tools/smart_chart_views_migration.py) = 16 MB."""
    if "n" not in _limit:
        n = 65000
        try:
            from db.connection import fetch_all, is_offline_mode
            if is_offline_mode():
                n = 16_000_000
            else:
                # table name as literal: db.connection rewrites table names inside SQL text, not in parameters
                rows = fetch_all("SELECT DATA_TYPE AS t FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
                                 "AND LOWER(TABLE_NAME) = 'tblsmartchartview' AND COLUMN_NAME = 'ConfigJSON'")
                t = str(rows[0]["t"]).lower() if rows else "text"
                n = {"mediumtext": 16_000_000, "longtext": 16_000_000}.get(t, 65000)
        except Exception:
            pass
        _limit["n"] = n
    return _limit["n"]


def save_view(name: str, config: Dict[str, Any], shared: Optional[bool] = False,
              view_id: Optional[int] = None) -> int:
    name = (name or "").strip()
    if not name:
        raise ValueError("empty name")
    from db.connection import execute, execute_insert
    now = datetime.datetime.now().replace(microsecond=0)
    payload = json.dumps(config, ensure_ascii=False, separators=(",", ":"))
    if len(payload.encode("utf-8")) > config_limit():     # TEXT = 64 KB, MEDIUMTEXT = 16 MB
        raise ValueError("This view is too big to be saved (too many pages or visuals). "
                         "Remove a few visuals or split it into two views.")
    if view_id:
        if shared is None:      # saved by someone with an edit share: sharing stays as the creator set it
            execute("UPDATE tblSmartChartView SET Name = ?, ConfigJSON = ?, UpdatedAt = ? WHERE ID = ?",
                    [name, payload, now, int(view_id)])
        else:
            execute("UPDATE tblSmartChartView SET Name = ?, IsShared = ?, ConfigJSON = ?, UpdatedAt = ? WHERE ID = ?",
                    [name, 1 if shared else 0, payload, now, int(view_id)])
        return int(view_id)
    uid, _lvl = _user()
    return int(execute_insert(
        "INSERT INTO tblSmartChartView (Name, UserID, IsShared, ConfigJSON, CreatedAt) VALUES (?,?,?,?,?)",
        [name, uid, 1 if shared else 0, payload, now]))


def delete_view(view_id: int) -> None:
    from db.connection import execute
    execute("DELETE FROM tblSmartChartView WHERE ID = ?", [int(view_id)])
    if shares_available():
        execute("DELETE FROM tblSmartChartViewShare WHERE ViewID = ?", [int(view_id)])
