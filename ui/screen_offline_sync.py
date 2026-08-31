# ui/screen_offline_sync.py
"""Admin screen: prepare/refresh the local offline SQLite copy and merge
offline-created changes back into MySQL.

Superuser-only (AccessLevel >= 4), same gate as Usage Stats - this touches
schema introspection and, eventually, prod writes.

Prepare/refresh (the READ direction) targets whichever MySQL backend the
current process is actually running against (db.connection.MODE) - explicit
user decision (2026-08-13): a snapshot pulled from dev_local while the app
itself runs against prod would be stale/pointless for real offline work.

Merge (the WRITE direction) writes back to WHICHEVER backend the active
offline copy was actually pulled from - not a separately hardcoded mode.
The snapshot stamps its own source_mode on every successful pull (see
db.offline_snapshot.get_snapshot_source_mode()); merge reads that stamp
instead of guessing, so a prod-sourced snapshot merges into prod and a
dev_local-sourced one merges into dev_local, automatically and unambiguously
- explicit user decision (2026-08-13), superseding the earlier "dev_local
only" restriction. Writing to prod is real and irreversible, so merging into
prod specifically gets an EXTRA confirmation dialog on top of the normal
"here's what would change" one (see _on_merge_clicked).

Both the snapshot pull (~50s against the current dev_local size, prod not
yet measured) and the merge run in a background QThread so the UI stays
responsive; both surface their result as plain text rather than a table for
this first cut.
"""
import os

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QMessageBox, QPlainTextEdit,
)

from db.connection import MODE as _LIVE_MODE
from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav

# Snapshot pull follows the live session (prod when running normally).
_SNAPSHOT_SOURCE_MODE = _LIVE_MODE


class _SnapshotWorker(QThread):
    finished_ok = Signal(dict)
    finished_err = Signal(str)
    finished_unmerged = Signal(dict)

    def __init__(self, force: bool = False):
        super().__init__()
        self._force = force

    def run(self):
        try:
            from db.offline_snapshot import pull_snapshot, UnmergedChangesError
            stats = pull_snapshot(source_mode=_SNAPSHOT_SOURCE_MODE, force=self._force)
            self.finished_ok.emit(stats)
        except UnmergedChangesError as e:
            self.finished_unmerged.emit(e.at_risk)
        except Exception as e:
            self.finished_err.emit(str(e))


class _MergePlanWorker(QThread):
    # (plan, target_mode) - target_mode is read from the snapshot's own
    # stamp (see module docstring), not a hardcoded constant.
    finished_ok = Signal(object, str)
    finished_err = Signal(str)

    def run(self):
        try:
            from db.offline_snapshot import get_snapshot_source_mode
            from db.offline_merge import plan_merge

            target_mode = get_snapshot_source_mode()
            if not target_mode:
                self.finished_err.emit(
                    "No offline copy has been prepared yet (or it predates "
                    "this feature) - run \"Prepare/refresh\" first."
                )
                return
            plan = plan_merge(target_mode, source_mode=target_mode)
            self.finished_ok.emit(plan, target_mode)
        except Exception as e:
            self.finished_err.emit(str(e))


class _MergeExecuteWorker(QThread):
    finished_ok = Signal(dict)
    finished_err = Signal(str)

    def __init__(self, plan, target_mode: str):
        super().__init__()
        self._plan = plan
        self._target_mode = target_mode

    def run(self):
        try:
            from db.offline_merge import execute_merge
            stats = execute_merge(self._target_mode, plan=self._plan, source_mode=self._target_mode)
            self.finished_ok.emit(stats)
        except Exception as e:
            self.finished_err.emit(str(e))


def _card() -> QFrame:
    c = QFrame(objectName="Card")
    return c


class OfflineSyncScreen(QWidget):
    def __init__(self, on_back_home=None, sidebar_callbacks=None):
        super().__init__()
        self.on_back_home = on_back_home
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None
        self._current_plan = None
        self._current_merge_target_mode = None
        self._snapshot_worker = None
        self._plan_worker = None
        self._merge_worker = None
        self._build_ui()
        self._refresh_last_sync_label()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring).
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 20, 24, 20)
        body_layout.setSpacing(16)

        info = QLabel(
            "Prepares a local offline copy (SQLite) for working without a network "
            "connection, and merges rows created offline back afterwards.\n"
            f"Step 1 pulls from whichever database this session is currently "
            f"running against ({_SNAPSHOT_SOURCE_MODE}). Step 2 (merge) writes "
            "back to that SAME database, whatever it was at the time - never a "
            "different one. Each of the two steps below runs as its own, "
            "separate step, and merging always shows what would change before "
            "anything is written."
        )
        info.setWordWrap(True)
        body_layout.addWidget(info)

        # --- Step 1: prepare/refresh ---
        prep_box = _card()
        prep_layout = QVBoxLayout(prep_box)
        prep_layout.setContentsMargins(20, 16, 20, 16)
        prep_layout.setSpacing(8)

        prep_title = QLabel("1. Prepare / refresh offline copy")
        prep_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        prep_layout.addWidget(prep_title)

        self.lbl_last_sync = QLabel("")
        prep_layout.addWidget(self.lbl_last_sync)

        # Quiet status line for the idle-triggered auto-refresh (see
        # ui/offline_autosnapshot.py) - deliberately small/muted, no popup,
        # only visible to whoever opens this screen and looks.
        self.lbl_auto_status = QLabel("")
        self.lbl_auto_status.setStyleSheet("color: #888; font-size: 11px;")
        prep_layout.addWidget(self.lbl_auto_status)

        prep_btn_row = QHBoxLayout()
        self.btn_prepare = QPushButton("Prepare / refresh now", objectName="GreenBtn")
        self.btn_prepare.clicked.connect(self._on_prepare_clicked)
        prep_btn_row.addWidget(self.btn_prepare)
        prep_btn_row.addStretch()
        prep_layout.addLayout(prep_btn_row)

        self.prep_status = QPlainTextEdit()
        self.prep_status.setReadOnly(True)
        self.prep_status.setMaximumHeight(120)
        prep_layout.addWidget(self.prep_status)

        body_layout.addWidget(prep_box)

        # --- Step 2: merge back ---
        merge_box = _card()
        merge_layout = QVBoxLayout(merge_box)
        merge_layout.setContentsMargins(20, 16, 20, 16)
        merge_layout.setSpacing(8)

        merge_title = QLabel("2. Merge offline changes back")
        merge_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        merge_layout.addWidget(merge_title)

        merge_btn_row = QHBoxLayout()
        self.btn_plan = QPushButton("Check for offline changes", objectName="GreyBtn")
        self.btn_plan.clicked.connect(self._on_plan_clicked)
        merge_btn_row.addWidget(self.btn_plan)

        self.btn_merge = QPushButton("Confirm & merge", objectName="GreenBtn")
        self.btn_merge.setEnabled(False)
        self.btn_merge.clicked.connect(self._on_merge_clicked)
        merge_btn_row.addWidget(self.btn_merge)
        merge_btn_row.addStretch()
        merge_layout.addLayout(merge_btn_row)

        self.merge_status = QPlainTextEdit()
        self.merge_status.setReadOnly(True)
        self.merge_status.setMaximumHeight(160)
        merge_layout.addWidget(self.merge_status)

        body_layout.addWidget(merge_box)
        body_layout.addStretch()

        content_layout.addWidget(body, 1)
        root.addWidget(FooterBar())

    def _go_home(self):
        if callable(self.on_back_home):
            self.on_back_home()

    def _refresh_sidebar(self):
        """Baut die Sidebar-Navigation neu auf, falls sich der Access-Level
        seit dem letzten Aufbau geändert hat, sonst nur die Badges (siehe
        ui/widgets/sidebar_nav.py::refresh_lazy_sidebar())."""
        import app_meta
        try:
            level = int((app_meta.current_user or {}).get("access_level") or 0)
        except Exception:
            level = 0
        sidebar_nav.refresh_lazy_sidebar(self, level)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_last_sync_label()
        self._refresh_auto_status_label()
        try:
            self._refresh_sidebar()
        except Exception:
            pass

    def _refresh_last_sync_label(self):
        from db.connection import get_offline_sqlite_path
        import datetime as _dt

        path = get_offline_sqlite_path()
        if os.path.exists(path):
            mtime = _dt.datetime.fromtimestamp(os.path.getmtime(path))
            self.lbl_last_sync.setText(f"Last prepared: {mtime.strftime('%Y-%m-%d %H:%M:%S')} ({path})")
        else:
            self.lbl_last_sync.setText(f"No offline copy yet ({path})")

    def _refresh_auto_status_label(self):
        from ui.offline_autosnapshot import get_last_attempt

        info = get_last_attempt()
        at = info.get("at")
        if at is None:
            self.lbl_auto_status.setText("Auto-refresh (idle, superusers): not triggered yet this session")
            return
        outcome_text = {"done": "completed", "skipped": "skipped", "failed": "failed"}.get(
            info.get("outcome"), str(info.get("outcome"))
        )
        text = f"Auto-refresh (idle, superusers): last attempt {at.strftime('%Y-%m-%d %H:%M:%S')} - {outcome_text}"
        if info.get("detail"):
            text += f" ({info['detail']})"
        self.lbl_auto_status.setText(text)

    # ------------------------------------------------------------- Prepare
    def _on_prepare_clicked(self, force: bool = False):
        self.btn_prepare.setEnabled(False)
        self.prep_status.setPlainText("Preparing offline copy - this can take about a minute...")
        self._snapshot_worker = _SnapshotWorker(force=force)
        self._snapshot_worker.finished_ok.connect(self._on_prepare_done)
        self._snapshot_worker.finished_err.connect(self._on_prepare_error)
        self._snapshot_worker.finished_unmerged.connect(self._on_prepare_unmerged)
        self._snapshot_worker.start()

    def _on_prepare_done(self, stats: dict):
        self.btn_prepare.setEnabled(True)
        lines = [f"{t}: {n}" for t, n in stats.items()]
        self.prep_status.setPlainText("Offline copy ready.\n" + "\n".join(lines))
        self._refresh_last_sync_label()
        try:
            from db.usage_log import log_usage_event
            log_usage_event("feature", "offline_sync_prepare", f"{sum(stats.values())} rows")
        except Exception:
            pass

    def _on_prepare_error(self, msg: str):
        self.btn_prepare.setEnabled(True)
        self.prep_status.setPlainText(f"Failed: {msg}")
        QMessageBox.warning(self, "Prepare offline copy", f"Could not prepare the offline copy:\n{msg}")

    def _on_prepare_unmerged(self, at_risk: dict):
        self.btn_prepare.setEnabled(True)
        lines = "\n".join(f"{t}: {n} row(s)" for t, n in at_risk.items())
        self.prep_status.setPlainText("Refresh blocked - unmerged offline changes present:\n" + lines)
        reply = QMessageBox.warning(
            self,
            "Unmerged offline changes",
            "Refreshing now would permanently discard offline work that hasn't been "
            f"merged yet:\n\n{lines}\n\n"
            "Use \"Check for offline changes\" below to merge first, or discard these "
            "changes and refresh anyway?",
            QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if reply == QMessageBox.Discard:
            self._on_prepare_clicked(force=True)

    # ------------------------------------------------------------ Merge
    def _on_plan_clicked(self):
        self.btn_plan.setEnabled(False)
        self.btn_merge.setEnabled(False)
        self._current_plan = None
        self.merge_status.setPlainText("Checking for offline changes...")
        self._plan_worker = _MergePlanWorker()
        self._plan_worker.finished_ok.connect(self._on_plan_done)
        self._plan_worker.finished_err.connect(self._on_plan_error)
        self._plan_worker.start()

    def _on_plan_done(self, plan, target_mode: str):
        self.btn_plan.setEnabled(True)
        self._current_plan = plan
        self._current_merge_target_mode = target_mode
        self.merge_status.setPlainText(f"Target: {target_mode}\n\n{plan.summary()}")
        self.btn_merge.setEnabled(not plan.is_empty())

    def _on_plan_error(self, msg: str):
        self.btn_plan.setEnabled(True)
        self.merge_status.setPlainText(f"Failed: {msg}")
        QMessageBox.warning(self, "Check for offline changes", f"Could not check for offline changes:\n{msg}")

    def _on_merge_clicked(self):
        if self._current_plan is None or self._current_plan.is_empty():
            return
        target_mode = self._current_merge_target_mode

        # Writing to prod is real and irreversible - extra, separate
        # confirmation on top of the normal "here's what would change" one
        # below (matches the project's established prod-write rules).
        if target_mode == "prod":
            reply = QMessageBox.warning(
                self,
                "Merging into PRODUCTION",
                "This will write directly into the PRODUCTION database.\n\n"
                "This cannot be undone. Are you absolutely sure?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        reply = QMessageBox.question(
            self,
            "Confirm merge",
            "The following rows will be inserted into "
            f"{target_mode}:\n\n{self._current_plan.summary()}\n\nProceed?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.btn_merge.setEnabled(False)
        self.btn_plan.setEnabled(False)
        self.merge_status.setPlainText("Merging...")
        self._merge_worker = _MergeExecuteWorker(self._current_plan, target_mode)
        self._merge_worker.finished_ok.connect(self._on_merge_done)
        self._merge_worker.finished_err.connect(self._on_merge_error)
        self._merge_worker.start()

    def _on_merge_done(self, stats: dict):
        self.btn_plan.setEnabled(True)
        self._current_plan = None
        lines = [f"{t}: {n['inserted']} inserted, {n['updated']} updated" for t, n in stats.items()]
        self.merge_status.setPlainText("Merge complete.\n" + "\n".join(lines))
        try:
            from db.usage_log import log_usage_event
            total = sum(n["inserted"] + n["updated"] for n in stats.values())
            log_usage_event("feature", "offline_sync_merge", f"{total} rows")
        except Exception:
            pass

    def _on_merge_error(self, msg: str):
        self.btn_plan.setEnabled(True)
        self.merge_status.setPlainText(f"Failed (rolled back): {msg}")
        QMessageBox.warning(self, "Merge", f"Merge failed and was rolled back:\n{msg}")
