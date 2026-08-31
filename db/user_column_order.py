# db/user_column_order.py
"""Per-user, per-screen persisted column display order.

Backs drag&drop column reordering in reorderable tables (e.g. ManageJetsScreen,
see ui/screen_manage_jets.py) so a user's chosen column order survives an app
restart. Generic across `screen_key` so future screens can reuse the same
`tblUserColumnOrder` table without a new migration.

Both functions are best-effort and never raise: a missing table (not yet
migrated to this environment) or no logged-in user simply disables persistence
for the session, it never blocks the UI.
"""

import json
from typing import List, Optional

import app_meta
from db.connection import execute, fetch_all, table_exists

_TABLE = "tblUserColumnOrder"


def load_column_order(screen_key: str) -> Optional[List[str]]:
    """Returns the saved column-name order for the current user/screen, or None."""
    user_id = app_meta.current_user.get("id")
    if not user_id or not table_exists(_TABLE):
        return None
    try:
        rows = fetch_all(
            f"SELECT ColumnOrderJSON FROM {_TABLE} WHERE UserID = ? AND ScreenKey = ?",
            [user_id, screen_key],
        )
        if not rows:
            return None
        names = json.loads(rows[0]["ColumnOrderJSON"])
        return [n for n in names if isinstance(n, str)] or None
    except Exception:
        return None


def save_column_order(screen_key: str, column_names: List[str]) -> None:
    """Best-effort upsert of the current column order for the logged-in user."""
    user_id = app_meta.current_user.get("id")
    if not user_id or not table_exists(_TABLE):
        return
    try:
        execute(f"DELETE FROM {_TABLE} WHERE UserID = ? AND ScreenKey = ?",
                [user_id, screen_key])
        execute(
            f"INSERT INTO {_TABLE} (UserID, ScreenKey, ColumnOrderJSON, Timestamp) "
            f"VALUES (?, ?, ?, NOW())",
            [user_id, screen_key, json.dumps(column_names)],
        )
    except Exception:
        pass
