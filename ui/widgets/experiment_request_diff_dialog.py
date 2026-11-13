from __future__ import annotations
# ui/widgets/experiment_request_diff_dialog.py
"""Side-by-side diff dialog for reviewing a proposed Experiment Request
change (2026-09-01, user request: "dann, wenn ich als superuser ein
geänderten request approven soll, dass muss ich standardmässig den alten
und den neuen nebeneinander sehen, so dass ich die unterschiede sehe ...
die änderungen [sollen] gehighlighted sein, so dass ich sofort sehe, was
geändert wurde"). Every changed field is highlighted so a superuser can
make an informed accept/reject decision without hunting for the difference
by hand - see db/experiment_request_changes.py for the underlying
pending-change/versioning workflow this reviews.

This is now the primary way a superuser reviews a pending change from
ui/screen_my_requests.py (context menu "Review Changes…", and the default
double-click action on a row that has one) - it replaces the previous
blind "accept"/"reject" actions that showed no comparison at all.
"""

from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QScrollArea,
    QWidget, QFrame, QPushButton, QDialogButtonBox, QMessageBox,
)

import app_meta
from db import experiment_requests as er
from ui.widgets.friendly_error import show_error

# Field-by-field comparison (meta fields skipped, Wunschtermin/Projekt as text):
# db/experiment_requests.compare_requests().

_HIGHLIGHT_STYLE = (
    "background: #fff3b0; border: 1px solid #e0b400; "
    "border-radius: 4px; padding: 4px 6px;"
)
_UNCHANGED_STYLE = "color: #888; padding: 4px 6px;"


class ExperimentRequestDiffDialog(QDialog):
    """Side-by-side comparison of a pending change against the current
    original, with every changed field highlighted. Accept/Reject act
    directly from here - the comparison itself is the confirmation, no
    separate "are you sure" popup for Accept (Reject still confirms, since
    it discards the proposal without a trace, unlike Accept which now
    always archives the prior version first, see
    db/experiment_request_changes.py)."""

    def __init__(self, parent, original_id: Any, copy_id: Any, *,
                 read_only: bool = False, left_label: str = "Current",
                 right_label: str = "Proposed", window_title: str = "Review Changes"):
        """`read_only=True` (2026-09-02, user request: comparing an archived
        version from the Version History dialog opened a second overlapping
        window that covered the one underneath, with no way to actually see
        both at once - "die originale version wird vom 'versionsfenster'
        verdeckt und ich kann die neueste version und die ältere nicht
        miteinander vergleichen") - reuses this SAME side-by-side/highlight
        machinery instead of the plain single-record read-only viewer, just
        without Accept/Reject (there's nothing to decide when comparing
        history, only something to look at) and with caller-supplied column
        labels instead of the hardcoded "Current"/"Proposed" (which only fit
        the original pending-change-review use case)."""
        super().__init__(parent)
        self._original_id = original_id
        self._copy_id = copy_id
        self._read_only = read_only
        self.outcome: Optional[str] = None  # "accepted" / "rejected" / None

        self.setWindowTitle(window_title)
        self.setMinimumSize(860, 580)
        self.resize(900, 640)

        cmp = er.compare_requests(original_id, copy_id)
        title = cmp["title"]

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(10)

        header = QLabel(title)
        header.setStyleSheet("font-size: 16px; font-weight: 700;")
        header.setWordWrap(True)
        root.addWidget(header)

        sub = QLabel(f"Changed fields are highlighted. Left: {left_label}. Right: {right_label}.")
        sub.setStyleSheet("color:#666;")
        root.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        host = QWidget()
        grid = QGridLayout(host)
        grid.setContentsMargins(0, 4, 0, 4)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        for col, text in enumerate(("Field", left_label, right_label)):
            lbl = QLabel(text)
            lbl.setStyleSheet("font-weight: 700; color: #303030;")
            grid.addWidget(lbl, 0, col)

        any_changes = False
        row_i = 1
        for r in cmp["rows"]:
            fn, old_val, new_val, changed = r["field"], r["left"], r["right"], r["changed"]

            lbl = QLabel(fn)
            old_lbl = QLabel(old_val or "—")
            new_lbl = QLabel(new_val or "—")
            for w in (old_lbl, new_lbl):
                w.setWordWrap(True)
                w.setTextInteractionFlags(Qt.TextSelectableByMouse)

            if changed:
                any_changes = True
                lbl.setStyleSheet("font-weight: 700;")
                old_lbl.setStyleSheet(_HIGHLIGHT_STYLE)
                new_lbl.setStyleSheet(_HIGHLIGHT_STYLE)
            else:
                lbl.setStyleSheet("color: #888;")
                old_lbl.setStyleSheet(_UNCHANGED_STYLE)
                new_lbl.setStyleSheet(_UNCHANGED_STYLE)

            grid.addWidget(lbl, row_i, 0, Qt.AlignTop)
            grid.addWidget(old_lbl, row_i, 1, Qt.AlignTop)
            grid.addWidget(new_lbl, row_i, 2, Qt.AlignTop)
            row_i += 1

        grid.setRowStretch(row_i, 1)
        scroll.setWidget(host)
        root.addWidget(scroll, 1)

        if not any_changes:
            note = QLabel(f"No differences found between {left_label} and {right_label}.")
            note.setStyleSheet("color:#b33; font-weight:600;")
            root.addWidget(note)

        if not read_only:
            btn_row = QHBoxLayout()
            self.btn_reject = QPushButton("Reject")
            self.btn_reject.setStyleSheet("QPushButton{color:#b33; font-weight:600;}")
            self.btn_reject.clicked.connect(self._on_reject)
            btn_row.addWidget(self.btn_reject)

            btn_row.addStretch(1)

            self.btn_accept = QPushButton("Accept")
            self.btn_accept.setObjectName("GreenBtn")
            self.btn_accept.clicked.connect(self._on_accept)
            btn_row.addWidget(self.btn_accept)

            root.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _on_accept(self) -> None:
        # Accept + best-effort heads-up to owners of experiments already made
        # from this request (db/experiment_requests.accept_pending_change); the
        # requester is notified by the caller (My Requests).
        try:
            er.accept_pending_change(app_meta.current_user or {}, self._copy_id, notify_requester=False)
        except Exception as e:
            show_error(self, "Error", "The change could not be accepted.", e)
            return
        self.outcome = "accepted"
        self.accept()

    def _on_reject(self) -> None:
        reply = QMessageBox.question(
            self, "Reject change",
            "Discard this proposed change? The original stays unchanged, "
            "and the proposal itself cannot be recovered afterward.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            er.reject_pending_change(app_meta.current_user or {}, self._copy_id, notify_requester=False)
        except Exception as e:
            show_error(self, "Error", "The change could not be rejected.", e)
            return
        self.outcome = "rejected"
        self.accept()


def review_pending_change(parent, original_id: Any, copy_id: Any) -> Optional[str]:
    """Opens the diff dialog for review. Returns "accepted", "rejected", or
    None if closed without a decision."""
    dlg = ExperimentRequestDiffDialog(parent, original_id, copy_id)
    dlg.exec()
    return dlg.outcome


def compare_versions(parent, *, current_id: Any, older_id: Any, older_label: str) -> None:
    """Read-only side-by-side comparison for the Version History dialog
    (ui/widgets/experiment_request_version_history.py) - `older_label` is
    e.g. "Version 2", shown as the left column's header; the live/current
    row is always the right column, labeled "Current (Live)". Nothing to
    accept/reject here, just a highlighted look at what changed since then."""
    dlg = ExperimentRequestDiffDialog(
        parent, older_id, current_id,
        read_only=True,
        left_label=older_label,
        right_label="Current (Live)",
        window_title=f"Compare: {older_label} vs. Current",
    )
    dlg.exec()
