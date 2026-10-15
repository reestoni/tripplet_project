# db/series_permissions.py
"""Who may move a trial series in the Backlog - and therefore also put it in
the recycle bin (Nutzerentscheid 2026-10-15: "nur Personen, welche ein
gegebenes Item verschieben können, dürfen es auch in den Papierkorb legen").

Same rules as BacklogScreen._handle_dnd_move() (and the Backlog help,
"Rules"): a series may be moved if at least one move is allowed:

    status                      who
    Backlog (1)                 every write user (access level >= 2)
    In Progress (2) / Done (3)  owner of the series or a superuser
    To Be Cleaned (4)           every write user (-> Archived)
    Archived (5)                superusers only
    no status                   owner or superuser

Superusers (access level >= 4) may always.

Deleting (can_delete_series): same as moving, except To Be Cleaned - there
only superusers may delete (Nutzerentscheid 2026-10-15), although every
write user may move it on to Archived.
"""
from __future__ import annotations

from typing import Any, Optional

STATUS_BACKLOG, STATUS_IN_PROGRESS, STATUS_DONE, STATUS_TBC, STATUS_ARCHIVED = 1, 2, 3, 4, 5


def _int(v: Any) -> Optional[int]:
    try:
        return int(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def can_move_series(access_level: Any, status_id: Any, owner_id: Any, user_id: Any) -> bool:
    lvl = _int(access_level) or 0
    if lvl >= 4:
        return True
    if lvl < 2 or _int(user_id) is None:
        return False
    status = _int(status_id)
    if status in (STATUS_BACKLOG, STATUS_TBC):
        return True
    if status == STATUS_ARCHIVED:
        return False
    owner = _int(owner_id)
    return owner is not None and owner == _int(user_id)


def can_delete_series(access_level: Any, status_id: Any, owner_id: Any, user_id: Any) -> bool:
    if _int(status_id) == STATUS_TBC and (_int(access_level) or 0) < 4:
        return False
    return can_move_series(access_level, status_id, owner_id, user_id)


def can_move_series_now(series_id: Any, _rule=None) -> bool:
    """Same check with the current user and the series' state in the DB
    (not what a screen showed some time ago)."""
    import app_meta
    from db.connection import fetch_all
    user = app_meta.current_user or {}
    try:
        rows = fetch_all("SELECT BacklogStatusID, BacklogOwner FROM tblTrialSeries WHERE ID = ?", [int(series_id)])
    except Exception:
        return False
    if not rows:
        return False
    try:
        lvl = int(app_meta.access_level() or 0)
    except Exception:
        lvl = 0
    rule = _rule or can_move_series
    return rule(lvl, rows[0].get("BacklogStatusID"), rows[0].get("BacklogOwner"), user.get("id"))


def can_delete_series_now(series_id: Any) -> bool:
    """Recycle bin available: can_delete_series() with the DB state. Without
    recycle bin (offline / not set up) deleting is permanent -> superusers only."""
    from db import recycle_bin
    if recycle_bin.available():
        return can_move_series_now(series_id, _rule=can_delete_series)
    try:
        import app_meta
        return int(app_meta.access_level() or 0) >= 4
    except Exception:
        return False
