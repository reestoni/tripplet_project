# ui/offline_autosnapshot.py
"""Idle-triggered background refresh of the offline SQLite snapshot.

Superuser-only for now (see _MIN_ACCESS_LEVEL below - the single place to
touch when this gets extended to other user groups later, per explicit user
request 2026-08-14). Fires pull_snapshot(force=False) after IDLE_THRESHOLD_MS
of no mouse/keyboard activity in an online (non-offline-mode) session, so a
superuser who steps away with prod/dev/dev_local open gets a reasonably
fresh offline copy without remembering to click "Prepare/refresh" manually.

Deliberately NEVER passes force=True: if the existing offline copy has
unmerged local changes (db.offline_snapshot.UnmergedChangesError), the
attempt is silently skipped rather than discarding anyone's offline work -
the whole point of an unattended trigger is that it must be safe to fire
without anyone watching. The result of every attempt (done/skipped/failed)
is kept in-memory for the current process only and shown quietly in
OfflineSyncScreen (a small status line, no popup, no notification) - on
purpose: this is a passive convenience feature, not something that should
interrupt anyone or draw attention to itself.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, Optional

from PySide6.QtCore import QEvent, QObject, QThread, QTimer, Signal

import app_meta
from db.connection import is_offline_mode

# Single knob for who's eligible - extend by lowering this (or swapping in a
# richer group check) when this rolls out beyond superusers. Kept as one
# constant/function instead of scattering "access_level >= 4" checks around.
_MIN_ACCESS_LEVEL = 4

IDLE_THRESHOLD_MS = 15 * 60 * 1000  # 15 minutes
_CHECK_INTERVAL_MS = 30_000  # how often we poll "has it been 15 min yet"

_ACTIVITY_EVENTS = {
    QEvent.MouseMove, QEvent.MouseButtonPress, QEvent.KeyPress,
    QEvent.Wheel, QEvent.TouchBegin,
}


def is_eligible_user() -> bool:
    """Whether the current session's logged-in user qualifies for the idle
    auto-snapshot. Superuser-only today; this is the intended extension
    point for opening it up to other access levels/groups later."""
    return app_meta.access_level() >= _MIN_ACCESS_LEVEL


# --------------------------------------------------------------- last result
# In-memory only (not persisted to disk) - reset on app restart, which is
# fine: this is a "did the last idle stretch refresh anything" indicator for
# the current session, not an audit log. Shown only when OfflineSyncScreen
# is actually opened (see its _refresh_auto_status_label), never proactively.
_last_attempt: Dict[str, Any] = {"at": None, "outcome": None, "detail": ""}


def get_last_attempt() -> Dict[str, Any]:
    return dict(_last_attempt)


def _record(outcome: str, detail: str = "") -> None:
    _last_attempt["at"] = _dt.datetime.now()
    _last_attempt["outcome"] = outcome
    _last_attempt["detail"] = detail


class _AutoSnapshotWorker(QThread):
    finished_ok = Signal(dict)
    finished_err = Signal(str)
    finished_unmerged = Signal(dict)

    def run(self):
        try:
            from db.offline_snapshot import UnmergedChangesError, pull_snapshot
            stats = pull_snapshot(force=False)
            self.finished_ok.emit(stats)
        except UnmergedChangesError as e:
            self.finished_unmerged.emit(e.at_risk)
        except Exception as e:
            self.finished_err.emit(str(e))


class IdleSnapshotManager(QObject):
    """Installs itself as an app-wide event filter to detect idle time and
    fires a background offline-snapshot refresh after IDLE_THRESHOLD_MS of
    no mouse/keyboard activity.

    One instance for the whole process lifetime (created once in
    MainWindow.__init__, started immediately - eligibility is re-checked
    live on every tick via is_eligible_user(), so it naturally does nothing
    before login and adapts if a different user logs in later).
    """

    def __init__(self, app):
        super().__init__(app)
        self._app = app
        self._last_activity = _dt.datetime.now()
        self._triggered_this_idle = False
        self._worker: Optional[_AutoSnapshotWorker] = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check_idle)

    def start(self):
        self._app.installEventFilter(self)
        self._timer.start(_CHECK_INTERVAL_MS)

    def eventFilter(self, obj, event):
        if event.type() in _ACTIVITY_EVENTS:
            self._last_activity = _dt.datetime.now()
            self._triggered_this_idle = False
        return False

    def _check_idle(self):
        if self._triggered_this_idle:
            return
        if self._worker is not None and self._worker.isRunning():
            return
        if is_offline_mode():
            return  # no MySQL source to pull from in an offline session
        if not is_eligible_user():
            return
        idle_ms = (_dt.datetime.now() - self._last_activity).total_seconds() * 1000
        if idle_ms < IDLE_THRESHOLD_MS:
            return
        self._triggered_this_idle = True
        self._run_snapshot()

    def _run_snapshot(self):
        self._worker = _AutoSnapshotWorker()
        self._worker.finished_ok.connect(self._on_done)
        self._worker.finished_err.connect(self._on_error)
        self._worker.finished_unmerged.connect(self._on_unmerged)
        self._worker.start()

    def _on_done(self, stats: dict):
        total = sum(stats.values())
        _record("done", f"{total} rows")

    def _on_error(self, msg: str):
        _record("failed", msg)

    def _on_unmerged(self, at_risk: dict):
        lines = ", ".join(f"{t}: {n}" for t, n in at_risk.items())
        _record("skipped", f"unmerged changes present - {lines}")
