# db/feature_access.py
"""Which tools and screens a user may use (Nutzerwunsch 2026-10-30).

FEATURES is the one list of everything that can be switched on/off, with
the default that applied before (minimum access level). A superuser
changes it in Manage User -> "Access…" (ui/widgets/feature_access_dialog.py):

    1. superuser (AccessLevel 4)        -> always everything (nobody locks himself out)
    2. setting for the PERSON           -> allowed / blocked
    3. setting for the GROUP            -> allowed / blocked (group = tblUser.AccessRights,
                                           an ID of tblAccessRight: read, write, admin, superuser)
    4. otherwise the default            -> AccessLevel >= min_level

Without any setting everything stays as it was. Blocked tools disappear
from the sidebar (ui/widgets/sidebar_nav.py) and main.py refuses every
other way in (Recent, help "Take me there", Ctrl+click, links between
screens) - see MainWindow._install_feature_guards().

Superuser tools (Manage User, Usage Stats, Statistics, Offline Sync, Lab
Assistant, Recycle Bin) are not in the list: they stay superuser-only.
Show Experiment / Report are not either - they are opened from a series.

Table tblFeatureAccess (one row per group OR person and feature). Best
effort: without the table (or offline) the defaults apply.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

TABLE = "tblFeatureAccess"

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS tblFeatureAccess (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    FeatureKey VARCHAR(60) NOT NULL,
    AccessRightID INT NULL,
    UserID INT NULL,
    Allowed TINYINT(1) NOT NULL,
    UpdatedAt DATETIME NULL,
    UpdatedBy INT NULL,
    INDEX ix_fa_user (UserID),
    INDEX ix_fa_group (AccessRightID)
)
"""

SUPERUSER_LEVEL = 4


@dataclass(frozen=True)
class Feature:
    key: str
    label: str
    section: str
    min_level: int      # default: allowed from this access level on (as before)


FEATURES: List[Feature] = [
    Feature("all_experiments", "All Experiments", "Navigation", 0),
    Feature("backlog", "Backlog", "Navigation", 2),
    Feature("new_experiment", "New Experiment", "Navigation", 2),
    Feature("add_series", "Add Trial Series", "Navigation", 2),
    Feature("add_lab_machines", "Add Lab Machines", "Navigation", 2),
    Feature("create_request", "Create Experiment Request", "Experiment Requests", 0),
    Feature("my_requests", "My Requests", "Experiment Requests", 0),
    Feature("image_compare", "Image Compare", "Tools", 0),
    Feature("canvas", "Canvas", "Tools", 0),
    Feature("jet_roi", "Jet ROI Calculator", "Tools", 0),
    Feature("air_supply", "Air Supply Network", "Tools", 0),
    Feature("dashboards", "Dashboards", "Tools", 0),
    Feature("requirement_hub", "Requirement Hub", "Tools", 3),
    Feature("smart_chart", "Smart Chart", "Tools", 3),
    Feature("yarn_stock", "Yarn Stock", "Tools", 0),
    Feature("label_generator", "Label Generator", "Tools", 0),
    Feature("tdms_inspector", "TDMS Inspector", "Tools", 0),
    Feature("manage_jets", "Jets", "Admin", 1),
    Feature("top_plates", "Top Plates", "Admin", 1),
    Feature("manage_yarn", "Yarn", "Admin", 1),
    Feature("order_type", "Order Type", "Admin", 1),
    Feature("product_groups", "Product Groups", "Admin", 1),
    Feature("material", "Material", "Admin", 1),
]
BY_KEY: Dict[str, Feature] = {f.key: f for f in FEATURES}
# landing screen after login when Backlog is blocked: the first allowed of these
LANDING_ORDER = ("backlog", "all_experiments", "dashboards", "yarn_stock", "smart_chart")
# screens a user can choose as his start screen (Settings, display_prefs "start"),
# each needs a target in MainWindow._go_landing()
START_SCREENS = ("backlog", "all_experiments", "dashboards", "smart_chart", "yarn_stock", "my_requests",
                 "requirement_hub", "image_compare", "canvas", "jet_roi", "air_supply", "label_generator",
                 "tdms_inspector", "manage_jets", "manage_yarn")

# main.py: every way into a tool goes through one of these MainWindow methods
# (sidebar, Ctrl+click, Recent, help "Take me there", links between screens) -
# MainWindow._install_feature_guards() wraps them. A new tool: add it to
# FEATURES and here.
GUARDED_METHODS = {
    "_go_all_experiments": "all_experiments", "_open_all_experiments_in_new_tab": "all_experiments",
    "_go_backlog": "backlog", "_open_backlog_in_new_tab": "backlog",
    "_go_create_experiment_request": "create_request", "_go_my_requests": "my_requests",
    "_go_image_compare": "image_compare", "_go_canvas": "canvas", "_go_nozzle_calculator": "jet_roi",
    "_go_air_supply": "air_supply", "_go_dashboards": "dashboards", "_go_requirement_hub": "requirement_hub",
    "_go_smartchart": "smart_chart", "_open_smartchart_visual_in_new_tab": "smart_chart",
    "_edit_dashboard_in_smartchart": "smart_chart",
    "_go_yarn_stock": "yarn_stock", "_go_yarn_stock_from_notification": "yarn_stock",
    "_go_label_generator": "label_generator", "_go_tdms_inspector": "tdms_inspector",
    "_go_add_jet": "manage_jets", "_go_add_top_plate": "top_plates", "_go_add_yarn": "manage_yarn",
    "_go_manage_order_type": "order_type", "_go_manage_product_groups": "product_groups",
    "_go_manage_material": "material",
}
# _go_create_experiment(mode): edit/copy of an existing experiment are not switched
CREATE_MODE_FEATURE = {"create": "new_experiment", "legacy": "new_experiment", "addseries": "add_series",
                       "addlabmachines": "add_lab_machines"}

# rules for the logged-in user: {"uid", "level", "group", "user": {key: bool}, "groups": {key: bool}}
_state: Dict[str, Any] = {}


def decide(key: str, level: int, user_rules: Dict[str, bool], group_rules: Dict[str, bool]) -> bool:
    """The rule (pure, for tests): superuser > person > group > default."""
    if level >= SUPERUSER_LEVEL:
        return True
    if key in user_rules:
        return bool(user_rules[key])
    if key in group_rules:
        return bool(group_rules[key])
    f = BY_KEY.get(key)
    return True if f is None else level >= f.min_level


def available() -> bool:
    try:
        from db.connection import get_columns_map, is_offline_mode
        if is_offline_mode():
            return False
        return "featurekey" in get_columns_map(TABLE)
    except Exception:
        return False


def create_table() -> None:
    """Only call deliberately - dev/prod only with explicit permission."""
    from db import connection
    connection.execute(CREATE_SQL)
    connection._COLUMNS_MAP_CACHE.clear()


def _current() -> Tuple[Optional[int], int]:
    try:
        import app_meta
        u = app_meta.current_user or {}
        uid = u.get("id")
        return (int(uid) if uid is not None else None), int(u.get("access_level") or 0)
    except Exception:
        return None, 0


def load(force: bool = False) -> Dict[str, Any]:
    """Rules of the logged-in user (cached per user; force after a change)."""
    uid, level = _current()
    if not force and _state.get("uid") == uid and _state.get("level") == level and "user" in _state:
        return _state
    _state.clear()
    _state.update({"uid": uid, "level": level, "group": None, "user": {}, "groups": {}})
    if uid is None or level >= SUPERUSER_LEVEL or not available():
        return _state
    try:
        from db.connection import fetch_all
        rows = fetch_all("SELECT AccessRights FROM tblUser WHERE ID = ?", [uid])
        group = rows[0].get("AccessRights") if rows else None
        _state["group"] = int(group) if group is not None else None
        for r in fetch_all("SELECT FeatureKey, AccessRightID, UserID, Allowed FROM tblFeatureAccess "
                           "WHERE UserID = ? OR AccessRightID = ?", [uid, _state["group"] if group is not None else -1]):
            target = "user" if r.get("UserID") is not None else "groups"
            _state[target][str(r["FeatureKey"])] = bool(int(r.get("Allowed") or 0))
    except Exception as e:
        logger.warning("feature_access: rules not loaded: %s", e)
    return _state


def can_use(key: str) -> bool:
    st = load()
    return decide(key, st["level"], st["user"], st["groups"])


def signature() -> Tuple:
    """Changes when what this user may use changes (sidebar rebuild)."""
    return tuple(can_use(f.key) for f in FEATURES)


def landing_key(preferred: Optional[str] = None) -> Optional[str]:
    """The user's start screen if he may use it, otherwise Backlog or the next allowed one."""
    if preferred in START_SCREENS and can_use(preferred):
        return preferred
    return next((k for k in LANDING_ORDER if can_use(k)), None)


# ── settings for the "Access…" dialog ────────────────────────────────────
def load_all() -> Dict[str, Any]:
    """{"groups": [{ID, Name, Level}], "users": [{ID, Name, Group}],
        "group_rules": {group id: {key: bool}}, "user_rules": {user id: {key: bool}}}"""
    from db.connection import fetch_all
    groups = fetch_all("SELECT ID, AccessRight AS Name, AccessLevel AS Level FROM tblAccessRight ORDER BY AccessLevel")
    users = fetch_all("SELECT ID, TRIM(CONCAT(COALESCE(FirstName,''), ' ', COALESCE(LastName,''))) AS Name, "
                      "AccessRights AS GroupID FROM tblUser WHERE COALESCE(Active, 1) <> 0 ORDER BY FirstName, LastName")
    out = {"groups": groups, "users": users, "group_rules": {}, "user_rules": {}}
    if available():
        for r in fetch_all("SELECT FeatureKey, AccessRightID, UserID, Allowed FROM tblFeatureAccess"):
            if r.get("UserID") is not None:
                out["user_rules"].setdefault(int(r["UserID"]), {})[str(r["FeatureKey"])] = bool(int(r["Allowed"]))
            elif r.get("AccessRightID") is not None:
                out["group_rules"].setdefault(int(r["AccessRightID"]), {})[str(r["FeatureKey"])] = \
                    bool(int(r["Allowed"]))
    return out


def save_all(group_rules: Dict[int, Dict[str, bool]], user_rules: Dict[int, Dict[str, bool]]) -> None:
    """Replace all settings (only keys of FEATURES are kept)."""
    import datetime
    from db.connection import execute
    now = datetime.datetime.now().replace(microsecond=0)
    me, _lvl = _current()
    execute("DELETE FROM tblFeatureAccess")
    for col, rules in (("AccessRightID", group_rules), ("UserID", user_rules)):
        for ident, keys in rules.items():
            for key, allowed in keys.items():
                if key not in BY_KEY or allowed is None:
                    continue
                execute(f"INSERT INTO tblFeatureAccess (FeatureKey, {col}, Allowed, UpdatedAt, UpdatedBy) "
                        "VALUES (?,?,?,?,?)", [key, int(ident), 1 if allowed else 0, now, me])
    load(force=True)
