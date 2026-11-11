# db/ref_criteria.py
"""Saved criteria sets for "Compare with Ref" (ui/ref_compare_dialog.py,
Nutzerwunsch 2026-11-11): per metric "higher / lower / close to the
reference" plus a tolerance, under a name, shared by all users and usable in
every series.

Criteria = JSON {metric key: {"dir": "higher"|"lower"|"close", "tol": float}}
with metric keys from ui/ref_compare.metric_key().

Everyone may save a new set or change a set; deleting: creator or superuser.
Without the table (offline / not set up) the dialog still works, only the
saving is disabled.
"""
from __future__ import annotations

import datetime
import json
from typing import Any, Dict, List, Optional

TABLE = "tblRefCriteriaSet"

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS tblRefCriteriaSet (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Criteria TEXT NOT NULL,
    CreatedBy INT NULL,
    CreatedAt DATETIME NULL,
    UpdatedBy INT NULL,
    UpdatedAt DATETIME NULL,
    UNIQUE KEY ux_refcriteria_name (Name)
)
"""


def create_table() -> None:
    """Only call deliberately - dev/prod only with explicit permission."""
    from db import connection
    connection.execute(CREATE_SQL)
    connection._COLUMNS_MAP_CACHE.clear()


def available() -> bool:
    try:
        from db.connection import get_columns_map, is_offline_mode
        if is_offline_mode():
            return False
        return "criteria" in get_columns_map(TABLE)
    except Exception:
        return False


def _uid() -> Optional[int]:
    import app_meta
    return (app_meta.current_user or {}).get("id")


def list_sets() -> List[Dict[str, Any]]:
    from db.connection import fetch_all
    rows = fetch_all(f"SELECT ID, Name, Criteria, CreatedBy FROM {TABLE} ORDER BY Name")
    for r in rows:
        r["criteria"] = parse(r.get("Criteria"))
    return rows


def parse(text: Any) -> Dict[str, Dict[str, Any]]:
    try:
        data = json.loads(text or "{}")
    except (TypeError, ValueError):
        return {}
    return {k: v for k, v in data.items() if isinstance(v, dict) and v.get("dir")} if isinstance(data, dict) else {}


def save(name: str, criteria: Dict[str, Dict[str, Any]], set_id: Optional[int] = None) -> int:
    """Insert (set_id None) or update. Returns the ID. Raises ValueError
    for an empty or already used name."""
    from db.connection import execute, execute_insert, fetch_all
    name = (name or "").strip()[:100]
    if not name:
        raise ValueError("Please enter a name.")
    clash = fetch_all(f"SELECT ID FROM {TABLE} WHERE Name = ?", [name])
    if clash and (set_id is None or int(clash[0]["ID"]) != int(set_id)):
        raise ValueError(f'A criteria set "{name}" already exists.')
    text = json.dumps({k: v for k, v in criteria.items() if v.get("dir")}, ensure_ascii=False)
    now = datetime.datetime.now().replace(microsecond=0)
    if set_id is None:
        return int(execute_insert(
            f"INSERT INTO {TABLE} (Name, Criteria, CreatedBy, CreatedAt, UpdatedBy, UpdatedAt) "
            "VALUES (?,?,?,?,?,?)", [name, text, _uid(), now, _uid(), now]))
    execute(f"UPDATE {TABLE} SET Name = ?, Criteria = ?, UpdatedBy = ?, UpdatedAt = ? WHERE ID = ?",
            [name, text, _uid(), now, int(set_id)])
    return int(set_id)


def can_delete(row: Dict[str, Any]) -> bool:
    import app_meta
    if int(app_meta.access_level() or 0) >= 4:
        return True
    uid = _uid()
    return uid is not None and row.get("CreatedBy") is not None and int(row["CreatedBy"]) == int(uid)


def delete(set_id: int) -> None:
    from db.connection import execute
    execute(f"DELETE FROM {TABLE} WHERE ID = ?", [int(set_id)])
