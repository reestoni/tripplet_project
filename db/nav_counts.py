"""nav_counts.py - badge counts of the sidebar (Backlog, approved/open
experiment requests, "My Requests"), without Qt.

Moved out of ui/widgets/sidebar_nav.py (2026-11-13) so that the desktop
sidebar and the web app (tripplet_web) count the same way. sidebar_nav
re-exports every function under its old name.
"""
from __future__ import annotations

from typing import Any, Optional

from db.connection import get_connection

def get_backlog_count() -> int:
    """Zählt offene Backlog-Einträge (BacklogStatus = 'Backlog')."""
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(
                """
                SELECT COUNT(*)
                FROM (tblTrialSeries AS s
                      INNER JOIN tblBacklogStatus AS bs
                        ON bs.[ID] = s.[BacklogStatusID])
                WHERE bs.[BacklogStatus] = 'Backlog'
                """
            )
            row = cur.fetchone()
        return int(row[0] or 0) if row else 0
    except Exception:
        return 0


def _live_request_filter_sql() -> str:
    """Extra WHERE clause that filters archived prior versions (see
    db/experiment_request_changes.py::supports_versioning()) out of count
    queries - without it, these badges would keep climbing with every
    accepted change to a matching request. Empty string on environments
    without the PriorVersionOfID column."""
    try:
        from db import experiment_request_changes as request_changes
        if request_changes.supports_versioning():
            return " AND [PriorVersionOfID] IS NULL"
    except Exception:
        pass
    return ""


def get_open_experiment_request_count() -> int:
    """Zählt offene ExperimentRequests (RequestStatus = 1)."""
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM [tblExperimentRequests] WHERE [RequestStatus] = 1"
                + _live_request_filter_sql()
            )
            row = cur.fetchone()
        return int(row[0] or 0) if row else 0
    except Exception:
        return 0


def get_approved_experiment_request_count() -> int:
    """Zählt genehmigte ExperimentRequests (RequestStatus = 3)."""
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM [tblExperimentRequests] WHERE [RequestStatus] = 3"
                + _live_request_filter_sql()
            )
            row = cur.fetchone()
        return int(row[0] or 0) if row else 0
    except Exception:
        return 0


def get_new_open_request_count(owner_id: Optional[Any] = None) -> int:
    """Zählt brandneue Requests mit Status 'Request' (RequestStatus=1), die
    KEINE Änderungs-Kopie sind (ChangeOfRequestID IS NULL) - Gegenstück zu
    request_changes.count_pending_changes(), das nur die Kopien zählt. Beide
    zusammen ergeben "alles, was gerade im Status Request wartet" (siehe
    get_pending_request_changes_count()). `owner_id=None`: alle (Superuser-
    Sicht), sonst nur CreatedBy=owner_id."""
    try:
        from db import experiment_request_changes as request_changes
        change_filter = (
            " AND [ChangeOfRequestID] IS NULL" if request_changes.supports_change_tracking() else ""
        )
        with get_connection() as cn:
            cur = cn.cursor()
            if owner_id in (None, ""):
                cur.execute(
                    "SELECT COUNT(*) FROM [tblExperimentRequests] WHERE [RequestStatus] = 1"
                    + change_filter + _live_request_filter_sql()
                )
            else:
                cur.execute(
                    "SELECT COUNT(*) FROM [tblExperimentRequests] WHERE [RequestStatus] = 1"
                    + change_filter + " AND [CreatedBy] = ?" + _live_request_filter_sql(),
                    [owner_id],
                )
            row = cur.fetchone()
        return int(row[0] or 0) if row else 0
    except Exception:
        return 0


def get_pending_request_changes_count() -> int:
    """Zählt ALLES, was für den Badge auf "My Requests" relevant ist: offene
    Änderungs-Kopien (siehe db/experiment_request_changes.py) PLUS brandneue,
    noch nicht geprüfte Requests (RequestStatus=1, keine Kopie) - Nutzerwunsch
    2026-09-08: beide Arten sollen gezählt/gehighlighted werden, nur mit
    unterschiedlichem Symbol unterscheidbar (siehe screen_my_requests.py,
    Markierung neuer Requests neben der bestehenden Kopie-Markierung).
    Superuser sehen alle, normale Nutzer nur ihre eigenen (gleiche
    Sichtbarkeits-Logik wie zuvor in
    ExperimentRequestScreen._refresh_my_requests_badge(), jetzt hierher
    verschoben, damit der direkte Sidebar-Eintrag denselben Badge zeigt)."""
    try:
        import app_meta
        from db import experiment_request_changes as request_changes
        is_superuser = bool(getattr(app_meta, "is_superuser_level", lambda: False)())
        owner_id = None if is_superuser else (app_meta.current_user or {}).get("id")
        return (
            request_changes.count_pending_changes(owner_id)
            + get_new_open_request_count(owner_id)
        )
    except Exception:
        return 0
