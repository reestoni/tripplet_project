"""backlog_moves.py - moving a trial series between Backlog statuses, without Qt.

Moved out of ui/screen_backlog.py (_handle_dnd_move / _series_has_joker_machine /
_update_backlog_status) on 2026-11-13 so that the desktop Backlog and the web
app (tripplet_web) apply exactly the same rules and write exactly the same rows.

Statuses: 1 Backlog, 2 In Progress, 3 Done, 4 To Be Cleaned, 5 Archived.
db/series_permissions.py describes the same rules from the "may this series
be moved at all" side - change both together.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from db.connection import execute, fetch_all

# (code, message) - the code lets the web app translate the message
DENY_MESSAGES: Dict[str, str] = {
    "not_logged_in": "You are not logged in. Please log in first.",
    "owner_only": ("Only the owner or a superuser may change the status. "
                   "Exception: Items with status 'Backlog' may be taken in progress by all users."),
    "archived_superuser": "Only superusers may set or remove the 'Archived' status.",
    "tbc_superuser": "Only superusers may move a series to 'To Be Cleaned'.",
    "tbc_back_superuser": "Only superusers may move a series back from 'To Be Cleaned'.",
}


def check_move(old_status_id: int, new_status_id: int, *, user_id: Any, access_level: int,
               owner_id: Any) -> Optional[str]:
    """None = allowed, otherwise the code of the reason (DENY_MESSAGES)."""
    if user_id is None:
        return "not_logged_in"
    is_super = access_level >= 4

    # Ausnahme: "To Be Cleaned" (4) -> "Archived" (5) darf von JEDEM Write-User
    # (AccessLevel >= 2) ausgeführt werden, unabhängig vom Owner.
    is_tbc_to_archived = (old_status_id == 4 and new_status_id == 5 and access_level >= 2)

    # Statuswechsel-Regel:
    # - Ausnahme: Wenn ein Item aktuell im Backlog ist (old_status_id == 1), darf auch ein Nicht-Owner den Status ändern.
    # - Sonst dürfen Statusänderungen nur durch den Owner oder einen Superuser erfolgen.
    if old_status_id != 1 and not is_super and not is_tbc_to_archived:
        try:
            is_owner = (owner_id is not None) and (int(owner_id) == int(user_id))
        except Exception:
            is_owner = False
        if not is_owner:
            return "owner_only"

    # Wechsel nach/von Archived (5) nur für Superuser.
    # Ausnahme: "To Be Cleaned" -> "Archived" ist für alle Write-User erlaubt.
    if (old_status_id == 5 or new_status_id == 5) and not is_tbc_to_archived:
        if not is_super:
            return "archived_superuser"

    # -> To Be Cleaned (4): always superuser-only, regardless of the old status.
    # Important for retest flags (db/retest_flags.py): a flagged series lands
    # in "Backlog" (1); the old rule only checked old==3 here and let a direct
    # jump 1 -> 4 slip through under the "Backlog" exception above - exactly
    # the checkpoint where open flags get resolved must stay superuser-exclusive.
    if new_status_id == 4 and old_status_id != 4 and not is_super:
        return "tbc_superuser"

    # To Be Cleaned (4) → Backlog/In Progress/Done: nur Superuser
    if old_status_id == 4 and new_status_id in (1, 2, 3) and not is_super:
        return "tbc_back_superuser"
    return None


def needs_machine(old_status_id: int, new_status_id: int, series_id: Any) -> bool:
    """Joker-Maschine Regel: von Backlog weg nur mit Nicht-Joker-Maschine."""
    return old_status_id == 1 and new_status_id != 1 and series_has_joker_machine(series_id)


def series_has_joker_machine(series_id) -> bool:
    sql = """
        SELECT
            s.[ID]           AS [SeriesID],
            m.[ID]           AS [MachineID],
            m.[IsJoker]      AS [IsJoker]
        FROM tblTrialSeries AS s
        LEFT JOIN tblMaschine AS m
            ON m.[ID] = s.[MachineID]
        WHERE s.[ID] = ?;
    """
    try:
        rows = fetch_all(sql, [series_id])
    except Exception:
        return False
    if not rows:
        return False
    val = rows[0].get("IsJoker")
    try:
        return bool(int(val))
    except Exception:
        return bool(val)


def non_joker_machines() -> List[Dict[str, Any]]:
    """Machines the user may pick for a joker series (MachineSelectDialog)."""
    return fetch_all("""
        SELECT [ID], [Maschine]
        FROM tblMaschine
        WHERE [IsJoker] = 0 OR [IsJoker] IS NULL
        ORDER BY [Maschine];
    """, [])


def series_state(series_id) -> Optional[Tuple[Optional[int], Optional[int]]]:
    """(BacklogStatusID, BacklogOwner) as stored now, None if the series does not exist."""
    rows = fetch_all("SELECT BacklogStatusID, BacklogOwner FROM tblTrialSeries WHERE ID = ?", [int(series_id)])
    if not rows:
        return None
    st, owner = rows[0].get("BacklogStatusID"), rows[0].get("BacklogOwner")
    return (int(st) if st is not None else None), (int(owner) if owner is not None else None)


def update_backlog_status(series_id, new_status, old_status, user_id, new_machine_id=None):
    # Wenn zurück in Backlog und Joker → OriginalJoker wieder setzen
    if new_status == 1 and old_status != 1:
        try:
            rows = fetch_all(
                "SELECT [IsJoker], [OriginalJoker] FROM tblTrialSeries WHERE [ID] = ?;",
                [series_id],
            )
            if rows:
                row = rows[0]
                val = row.get("IsJoker")
                try:
                    is_joker = bool(int(val))
                except Exception:
                    is_joker = bool(val)
                orig = row.get("OriginalJoker")
                if is_joker and orig is not None:
                    new_machine_id = orig
        except Exception:
            pass

    set_owner = (old_status == 1 and new_status !=
                 1 and user_id is not None)

    if set_owner and new_machine_id is not None:
        sql = """
            UPDATE tblTrialSeries
            SET [BacklogStatusID] = ?, [BacklogOwner] = ?, [MachineID] = ?
            WHERE [ID] = ?;
        """
        params = [new_status, user_id, new_machine_id, series_id]
    elif set_owner:
        sql = """
            UPDATE tblTrialSeries
            SET [BacklogStatusID] = ?, [BacklogOwner] = ?
            WHERE [ID] = ?;
        """
        params = [new_status, user_id, series_id]
    elif new_machine_id is not None:
        sql = """
            UPDATE tblTrialSeries
            SET [BacklogStatusID] = ?, [MachineID] = ?
            WHERE [ID] = ?;
        """
        params = [new_status, new_machine_id, series_id]
    else:
        sql = """
            UPDATE tblTrialSeries
            SET [BacklogStatusID] = ?
            WHERE [ID] = ?;
        """
        params = [new_status, series_id]

    execute(sql, params)

    # Timestamp-Fallback beim Erreichen von "Done": tblTrial.Timestamp wird
    # eigentlich beim Editieren des jeweils letzten Tension-Feldes gestempelt
    # (siehe screen_show_experiment.py::_save_all(), YarnTensionAfterJet/
    # W3Tension) - Trials, bei denen das nie passiert ist, bleiben sonst
    # dauerhaft NULL und fallen aus jeder zeitbasierten Auswertung (Stats
    # Suite etc.) heraus. Nur NULL-Zeilen heilen, ein bereits gesetzter
    # (echter) Tension-Timestamp wird nie überschrieben. (2026-08-20,
    # explizite Nutzeranfrage)
    if new_status == 3 and old_status != 3:
        try:
            execute(
                "UPDATE tblTrial SET [Timestamp] = NOW() "
                "WHERE [TrialSeriesID] = ? AND [Timestamp] IS NULL;",
                [series_id],
            )
        except Exception as e:
            import traceback
            print(f"[Timestamp-Fallback] Fehler fuer series_id={series_id}: {e}")
            traceback.print_exc()

    # Notifications erstellen wenn Status → Done (ID 3)
    if new_status == 3 and old_status != 3:
        try:
            from ui.notifications import create_done_notifications
            n = create_done_notifications(
                series_id=series_id,
                sender_user_id=user_id,
            )
            print(f"[Notification] {n} notification(s) created for series_id={series_id}")
        except Exception as e:
            import traceback
            print(f"[Notification] Fehler: {e}")
            traceback.print_exc()


def after_move(series_id, new_status_id, user_id) -> None:
    """Side effects after a successful move (called by both apps)."""
    if new_status_id == 4:
        # "To Be Cleaned" is already superuser-exclusive (see check_move) -
        # this step counts as sign-off on any open retest flags of this series.
        try:
            from db.retest_flags import resolve_retest_flags_for_series
            resolve_retest_flags_for_series(series_id, user_id)
        except Exception:
            pass
