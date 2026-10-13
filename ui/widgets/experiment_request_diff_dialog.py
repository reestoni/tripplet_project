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

import datetime
import re
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QScrollArea,
    QWidget, QFrame, QPushButton, QDialogButtonBox, QMessageBox,
)

from db.connection import get_connection, fetch_all, table_exists, get_columns_map
from db import experiment_request_changes as request_changes
from ui.text_normalize import resolve_field

# Pure row metadata - never a real content difference worth showing (mirrors
# ui/screen_create_experiment_request.py::EXCLUDE_FIELDS).
_META_FIELDS = {
    "ID", "Timestamp", "CreatedBy", "RequestStatus", "ChangeOfRequestID",
    "PriorVersionOfID", "DenialReason",
}
_DATE_FIELDS = {"Wunschtermin"}

_HIGHLIGHT_STYLE = (
    "background: #fff3b0; border: 1px solid #e0b400; "
    "border-radius: 4px; padding: 4px 6px;"
)
_UNCHANGED_STYLE = "color: #888; padding: 4px 6px;"


def _fetch_row(request_id: Any) -> Optional[Dict[str, Any]]:
    if request_id in (None, ""):
        return None
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute("SELECT * FROM [tblExperimentRequests] WHERE [ID]=?", [request_id])
        row = cur.fetchone()
        if not row:
            return None
        names = [d[0] for d in (cur.description or [])]
    return {names[i]: row[i] for i in range(len(names))}


def _lookup_project_label(project_id: Any) -> str:
    """Same lookup as _ExperimentRequestReadOnlyDialog._lookup_project_label()
    in ui/screen_show_experiment.py - small enough to duplicate here rather
    than depend on that dialog's instance state."""
    if project_id in (None, ""):
        return ""
    for t in ("tblProject", "tblProjects"):
        if not table_exists(t):
            continue
        try:
            cols = get_columns_map(t)
            f_num = resolve_field(
                ["Project Number", "ProjectNumber", "Projekt Nummer", "ProjektNummer", "Number", "Nr"], cols)
            f_name = resolve_field(
                ["Project Name", "ProjectName", "Projekt Name", "ProjektName", "Name", "Titel", "Title"], cols)
            if not (f_num and f_name):
                continue
            rows = fetch_all(f"SELECT [{f_num}] AS PN, [{f_name}] AS PName FROM [{t}] WHERE [ID]=?", [project_id])
            if rows:
                pn = str(rows[0].get("PN") or "")
                pnm = str(rows[0].get("PName") or "")
                return (pn + " - " + pnm).strip(" -")
        except Exception:
            continue
    return str(project_id)


def _format_value(field_name: str, val: Any) -> str:
    if val is None:
        return ""
    if field_name in _DATE_FIELDS:
        if isinstance(val, (datetime.datetime, datetime.date)):
            return val.strftime("%d.%m.%Y")
        s = re.sub(r"(Z|[+-]\d{2}:\d{2})$", "", str(val).strip().replace("T", " ")).strip()
        s_date = s.split(" ")[0]
        if re.match(r"^\d{4}-\d{2}-\d{2}$", s_date):
            try:
                return datetime.datetime.strptime(s_date, "%Y-%m-%d").strftime("%d.%m.%Y")
            except Exception:
                return s
        return s
    if field_name.lower() == "projekt":
        return _lookup_project_label(val)
    return str(val).strip()


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

        original = _fetch_row(original_id) or {}
        proposed = _fetch_row(copy_id) or {}
        title = str(proposed.get("Titel") or original.get("Titel") or "").strip() or f"Request #{original_id}"

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

        field_names = [n for n in original.keys() if n not in _META_FIELDS]
        for n in proposed.keys():
            if n not in _META_FIELDS and n not in field_names:
                field_names.append(n)

        any_changes = False
        row_i = 1
        for fn in field_names:
            old_val = _format_value(fn, original.get(fn))
            new_val = _format_value(fn, proposed.get(fn))
            changed = old_val != new_val

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
        try:
            original_id, archived_version_id = request_changes.accept_pending_change(self._copy_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not accept the change:\n\n{e}")
            return
        # Best-effort heads-up (2026-09-02, user request) to whoever already
        # created an Experiment from this request before it changed - they're
        # otherwise not part of this review loop at all and would only find
        # out by explicitly checking back. Never blocks/fails the actual
        # accept if it errors.
        try:
            import app_meta
            from ui.notifications import notify_experiment_owners_of_request_change
            actor_id = (app_meta.current_user or {}).get("id")
            notify_experiment_owners_of_request_change(original_id, archived_version_id, actor_id)
        except Exception:
            pass
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
            request_changes.reject_pending_change(self._copy_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not reject the change:\n\n{e}")
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
