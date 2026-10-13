from __future__ import annotations
# ui/widgets/experiment_request_version_history.py
"""Version history dialog for Experiment Requests (2026-09-01, user
request: accepting a proposed change used to overwrite the approved
original in place with no trace of what it looked like before - the user
wants versioning they can trace themselves).

Shows the current (live) row plus every archived prior version (see
db/experiment_request_changes.py) of a request as a clickable list - a
click/"View…" opens the selected version in the existing read-only viewer
(ui.screen_show_experiment._ExperimentRequestReadOnlyDialog), unchanged,
just with a version prefix in its title (title_prefix parameter there).

Used from ui/screen_my_requests.py (context menu "View version history…")
- available to regular users (their own requests) AND superusers (all
requests) alike; unlike accepting/rejecting a pending change, simply
viewing one's own history is not a superuser-only action.
"""

import datetime
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QDialogButtonBox, QLabel, QPushButton,
)

from db import experiment_request_changes as request_changes


def _fmt_timestamp(ts: Any) -> str:
    if isinstance(ts, datetime.datetime):
        return ts.strftime("%Y-%m-%d %H:%M")
    return str(ts or "")


class _VersionHistoryDialog(QDialog):
    """Lists all versions of a request (current + archived prior versions),
    newest first."""

    def __init__(self, request_id: Any, parent=None):
        super().__init__(parent)
        self._request_id = request_id
        self.setWindowTitle("Version History")
        self.setMinimumSize(480, 380)

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            "All versions of this request. Double-click (or \"View…\") opens "
            "the selected version read-only."
        ))

        self._list = QListWidget()
        lay.addWidget(self._list, 1)

        versions = request_changes.list_versions(request_id)
        total = len(versions)

        # "Current" is always the highest version number (total + 1) - the
        # archived prior versions below it are chronologically 1..total,
        # oldest (the very first original) = version 1.
        current_item = QListWidgetItem(f"●  Current (live)  —  Version {total + 1}")
        current_item.setData(Qt.UserRole, (request_id, "Current"))
        bold_font = current_item.font()
        bold_font.setBold(True)
        current_item.setFont(bold_font)
        self._list.addItem(current_item)

        for i, v in enumerate(versions):
            version_no = total - i
            who = str(v.get("CreatedByUser") or "").strip() or "?"
            ts = _fmt_timestamp(v.get("Timestamp"))
            item = QListWidgetItem(f"Version {version_no}  —  {ts}  —  {who}")
            item.setData(Qt.UserRole, (v.get("ID"), f"Version {version_no}"))
            self._list.addItem(item)

        if self._list.count():
            self._list.setCurrentRow(0)
        self._list.itemDoubleClicked.connect(lambda _it: self._view_selected())

        btn_row = QHBoxLayout()
        self._btn_view = QPushButton("View…")
        self._btn_view.clicked.connect(self._view_selected)
        btn_row.addWidget(self._btn_view)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)

        self._list.currentItemChanged.connect(lambda *_: self._update_view_button_label())
        self._update_view_button_label()

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _update_view_button_label(self) -> None:
        item = self._list.currentItem()
        label = item.data(Qt.UserRole)[1] if item is not None else None
        self._btn_view.setText("View…" if label == "Current" else "Compare with Current…")

    def _view_selected(self) -> None:
        """"Current" opens the plain read-only viewer (nothing to compare it
        against); any archived version instead opens the side-by-side diff
        dialog against the live row (2026-09-02, user request: opening an
        older version used to pop up a SECOND overlapping window that
        covered the one underneath - "die originale version wird vom
        'versionsfenster' verdeckt und ich kann die neueste version und die
        ältere nicht miteinander vergleichen" - reusing
        ExperimentRequestDiffDialog's side-by-side/highlight view fixes both
        the overlap and adds the highlighted-differences view for free)."""
        item = self._list.currentItem()
        if item is None:
            return
        view_id, label = item.data(Qt.UserRole)
        if view_id in (None, ""):
            return
        if label == "Current":
            from ui.screen_show_experiment import _ExperimentRequestReadOnlyDialog
            dlg = _ExperimentRequestReadOnlyDialog(self, request_id=view_id, title_prefix=f"{label} — ")
            dlg.exec()
        else:
            from ui.widgets.experiment_request_diff_dialog import compare_versions
            compare_versions(self, current_id=self._request_id, older_id=view_id, older_label=label)


def show_version_history(parent, request_id: Any) -> None:
    """Opens the version history dialog for request_id (always the ID of
    the current/live row - never that of an archived prior version)."""
    if request_id in (None, ""):
        return
    dlg = _VersionHistoryDialog(request_id, parent=parent)
    dlg.exec()
