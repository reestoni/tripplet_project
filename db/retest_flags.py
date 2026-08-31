"""retest_flags.py - Retest flags for individual trials (e.g. V1 in Itemat Lab).

A superuser flags a trial in a lab pivot view (currently Itemat Lab) as
needing a retest. That immediately moves the owning TrialSeries back to
Backlog status "Backlog" (ID 1) with top priority, so it surfaces right away
in the Backlog screen.

An open flag is resolved once a superuser moves the series to "To Be
Cleaned" (ID 4) in the Backlog (see ui/screen_backlog.py::_handle_dnd_move) -
that is already a superuser-exclusive step today, so no separate approval
dialog is needed.

Best-effort like db/usage_log.py: if the table is missing (e.g. on a DB mode
it hasn't been rolled out to yet), the functions become no-ops instead of
raising.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from db.connection import execute, fetch_all, table_exists

BACKLOG_STATUS_ID = 1
TOP_PRIO = 0


def flags_table_ready() -> bool:
    """True if tblTrialRetestFlag exists on the current DB mode."""
    try:
        return table_exists("tblTrialRetestFlag")
    except Exception:
        return False


def mark_trial_for_retest(
    trial_id: int,
    trial_series_id: int,
    lab_source: str,
    note: str,
    user_id: Optional[int],
) -> None:
    """Creates an open retest flag and pulls the series back into the Backlog (top priority)."""
    if not flags_table_ready():
        return
    execute(
        "INSERT INTO tblTrialRetestFlag "
        "(TrialID, TrialSeriesID, LabSource, Status, Note, CreatedByUserID, CreatedAt) "
        "VALUES (?, ?, ?, 'open', ?, ?, NOW())",
        [trial_id, trial_series_id, lab_source, note or None, user_id],
    )
    execute(
        "UPDATE tblTrialSeries SET BacklogStatusID = ?, BacklogPrio = ? WHERE ID = ?",
        [BACKLOG_STATUS_ID, TOP_PRIO, trial_series_id],
    )


def resolve_retest_flags_for_series(trial_series_id: int, user_id: Optional[int]) -> int:
    """Closes all open flags of a series. Called when the series is moved to 'To Be Cleaned'."""
    if not flags_table_ready():
        return 0
    return execute(
        "UPDATE tblTrialRetestFlag "
        "SET Status = 'done', ResolvedByUserID = ?, ResolvedAt = NOW() "
        "WHERE TrialSeriesID = ? AND Status = 'open'",
        [user_id, trial_series_id],
    )


def get_open_retest_flags_by_series() -> Dict[int, List[Dict[str, Any]]]:
    """Returns {TrialSeriesID: [{TrialID, LabSource, Note, Versuchsnummer}, ...]} for all open flags."""
    if not flags_table_ready():
        return {}
    try:
        rows = fetch_all(
            "SELECT rf.TrialSeriesID, rf.TrialID, rf.LabSource, rf.Note, t.Versuchsnummer "
            "FROM tblTrialRetestFlag rf "
            "LEFT JOIN tblTrial t ON t.ID = rf.TrialID "
            "WHERE rf.Status = 'open'",
            [],
        )
    except Exception:
        return {}

    out: Dict[int, List[Dict[str, Any]]] = {}
    for r in rows:
        try:
            series_id = int(r["TrialSeriesID"])
        except Exception:
            continue
        out.setdefault(series_id, []).append(r)
    return out


def get_open_retest_flags_for_series_and_source(
    trial_series_id: int, lab_source: str
) -> List[Dict[str, Any]]:
    """Open flags of a series for a single data source (e.g. 'ItematLab').

    Used for the in-screen display in ShowExperimentScreen: column-header
    marker and the visible note banner above the pivot table.
    """
    if not flags_table_ready():
        return []
    try:
        rows = fetch_all(
            "SELECT rf.TrialID, rf.Note, rf.CreatedAt, t.Versuchsnummer, "
            "u.Username AS CreatedByUsername "
            "FROM tblTrialRetestFlag rf "
            "LEFT JOIN tblTrial t ON t.ID = rf.TrialID "
            "LEFT JOIN tblUser u ON u.ID = rf.CreatedByUserID "
            "WHERE rf.Status = 'open' AND rf.TrialSeriesID = ? AND rf.LabSource = ? "
            "ORDER BY t.Versuchsnummer",
            [trial_series_id, lab_source],
        )
    except Exception:
        return []
    return rows
