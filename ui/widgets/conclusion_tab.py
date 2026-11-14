"""Show Experiment tab "Conclusion" (user request 2026-11-14) - logic in db/series_conclusion.py (shared with the
web app). Written any time, not tied to a status: goal (from the experiment request, or an own goal when the series
has none), outcome, short summary, best trials, findings, recommendation. Saved with the Save button of the tab;
switching to another series with unsaved changes asks Save / Discard."""
from __future__ import annotations

import datetime
from html import escape
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QRadioButton, QScrollArea, QTextEdit, QVBoxLayout, QWidget)

from db import series_conclusion as sc


def _fmt(ts: Any) -> str:
    if isinstance(ts, datetime.datetime):
        return ts.strftime("%d.%m.%Y %H:%M")
    return str(ts or "")[:16].replace("T", " ")


class ConclusionTab(QWidget):
    saved = Signal()          # Show Experiment refreshes the tab title / Backlog marker

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._series_id: Optional[int] = None
        self._data: Dict[str, Any] = {}
        self._loaded_snapshot: Dict[str, Any] = {}
        self._trial_boxes: List[QCheckBox] = []
        self._loading = False
        self._editable = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        v = QVBoxLayout(body)
        v.setContentsMargins(24, 16, 24, 24)
        v.setSpacing(10)

        self._lbl_info = QLabel()
        self._lbl_info.setWordWrap(True)
        self._lbl_info.setStyleSheet("color:#666; font-size:11px;")
        v.addWidget(self._lbl_info)

        # goal: from the request (read only) or own goal
        self._box_request = QLabel()
        self._box_request.setWordWrap(True)
        self._box_request.setTextFormat(Qt.RichText)
        self._box_request.setStyleSheet("QLabel{background:#f4f6f4; border:1px solid #dde3dd; border-radius:6px; padding:10px;}")
        v.addWidget(self._box_request)
        self._lbl_goal = QLabel("<b>Goal</b> <span style='color:#888'>(no experiment request - what should this series show?)</span>")
        v.addWidget(self._lbl_goal)
        self._ed_goal = QTextEdit()
        self._ed_goal.setAcceptRichText(False)
        self._ed_goal.setFixedHeight(60)
        v.addWidget(self._ed_goal)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        r = 0
        grid.addWidget(QLabel("<b>Outcome</b>"), r, 0)
        row = QHBoxLayout()
        self._grp_outcome = QButtonGroup(self)
        self._grp_outcome.setExclusive(False)       # allows "nothing chosen"
        for key in sc.OUTCOMES:
            rb = QRadioButton(sc.OUTCOME_LABELS[key])
            rb.setProperty("key", key)
            rb.setStyleSheet(f"QRadioButton {{ color:{sc.OUTCOME_COLOURS[key]}; font-weight:600; }}")
            self._grp_outcome.addButton(rb)
            row.addWidget(rb)
        row.addStretch(1)
        self._grp_outcome.buttonToggled.connect(lambda b, on: self._exclusive(self._grp_outcome, b, on))
        grid.addLayout(row, r, 1)
        r += 1
        grid.addWidget(QLabel("<b>Summary</b>"), r, 0, Qt.AlignTop)
        sbox = QVBoxLayout()
        self._ed_summary = QLineEdit()
        self._ed_summary.setMaxLength(sc.SUMMARY_MAX)
        self._ed_summary.setPlaceholderText("One or two sentences - shown on the Backlog card and in All Experiments")
        self._lbl_count = QLabel()
        self._lbl_count.setStyleSheet("color:#888; font-size:10px;")
        self._ed_summary.textChanged.connect(lambda t: self._lbl_count.setText(f"{len(t)} / {sc.SUMMARY_MAX}"))
        sbox.addWidget(self._ed_summary)
        sbox.addWidget(self._lbl_count, 0, Qt.AlignRight)
        grid.addLayout(sbox, r, 1)
        r += 1
        grid.addWidget(QLabel("<b>Best trials</b>"), r, 0, Qt.AlignTop)
        self._trials_wrap = QWidget()
        self._trials_lay = QGridLayout(self._trials_wrap)
        self._trials_lay.setContentsMargins(0, 0, 0, 0)
        self._trials_lay.setHorizontalSpacing(10)
        grid.addWidget(self._trials_wrap, r, 1)
        r += 1
        grid.addWidget(QLabel("<b>Findings</b>"), r, 0, Qt.AlignTop)
        self._ed_findings = QTextEdit()
        self._ed_findings.setAcceptRichText(False)
        self._ed_findings.setMinimumHeight(160)
        self._ed_findings.setPlaceholderText("What did we learn? Observations, numbers, surprises…")
        grid.addWidget(self._ed_findings, r, 1)
        r += 1
        grid.addWidget(QLabel("<b>Recommendation</b>"), r, 0, Qt.AlignTop)
        rbox = QVBoxLayout()
        row2 = QHBoxLayout()
        self._grp_rec = QButtonGroup(self)
        self._grp_rec.setExclusive(False)
        for key in sc.RECOMMENDATIONS:
            rb = QRadioButton(sc.RECOMMENDATION_LABELS[key])
            rb.setProperty("key", key)
            self._grp_rec.addButton(rb)
            row2.addWidget(rb)
        row2.addStretch(1)
        self._grp_rec.buttonToggled.connect(lambda b, on: self._exclusive(self._grp_rec, b, on))
        rbox.addLayout(row2)
        self._ed_rec = QTextEdit()
        self._ed_rec.setAcceptRichText(False)
        self._ed_rec.setFixedHeight(60)
        self._ed_rec.setPlaceholderText("e.g. confirm at 900 m/min")
        rbox.addWidget(self._ed_rec)
        grid.addLayout(rbox, r, 1)
        grid.setColumnStretch(1, 1)
        v.addLayout(grid)

        bar = QHBoxLayout()
        self._lbl_state = QLabel()
        self._lbl_state.setStyleSheet("color:#888; font-size:11px;")
        bar.addWidget(self._lbl_state, 1)
        self._btn_save = QPushButton("Save conclusion")
        self._btn_save.setObjectName("GreenBtn")
        self._btn_save.clicked.connect(self.save)
        bar.addWidget(self._btn_save)
        v.addLayout(bar)
        v.addStretch(1)

        for w in (self._ed_goal, self._ed_findings, self._ed_rec):
            w.textChanged.connect(self._changed)
        self._ed_summary.textChanged.connect(self._changed)
        self._grp_outcome.buttonToggled.connect(lambda *_: self._changed())
        self._grp_rec.buttonToggled.connect(lambda *_: self._changed())

    # ── helpers ──────────────────────────────────────────────────────────
    def _exclusive(self, grp: QButtonGroup, btn, on: bool) -> None:
        if not on:
            return
        for b in grp.buttons():
            if b is not btn and b.isChecked():
                b.blockSignals(True)
                b.setChecked(False)
                b.blockSignals(False)

    @staticmethod
    def _chosen(grp: QButtonGroup) -> Optional[str]:
        for b in grp.buttons():
            if b.isChecked():
                return b.property("key")
        return None

    @staticmethod
    def _choose(grp: QButtonGroup, key: Optional[str]) -> None:
        for b in grp.buttons():
            b.blockSignals(True)
            b.setChecked(b.property("key") == key)
            b.blockSignals(False)

    def current(self) -> Dict[str, Any]:
        return {"goal": self._ed_goal.toPlainText().strip(), "outcome": self._chosen(self._grp_outcome),
                "summary": self._ed_summary.text().strip(),
                "best_trials": [cb.property("trial_id") for cb in self._trial_boxes if cb.isChecked()],
                "findings": self._ed_findings.toPlainText().strip(), "recommendation": self._chosen(self._grp_rec),
                "recommendation_text": self._ed_rec.toPlainText().strip()}

    def is_dirty(self) -> bool:
        return bool(self._series_id) and self.current() != self._loaded_snapshot

    def _changed(self) -> None:
        if self._loading:
            return
        self._update_state()

    def _update_state(self) -> None:
        d = self._data
        if self.is_dirty():
            self._lbl_state.setText("● unsaved changes")
            self._lbl_state.setStyleSheet("color:#B26A00; font-size:11px; font-weight:600;")
        elif d.get("exists"):
            self._lbl_state.setText(f"Last changed by {d.get('updated_by') or '?'} · {_fmt(d.get('updated_at'))}")
            self._lbl_state.setStyleSheet("color:#888; font-size:11px;")
        else:
            self._lbl_state.setText("No conclusion yet")
            self._lbl_state.setStyleSheet("color:#888; font-size:11px;")
        self._btn_save.setEnabled(self._editable and self.is_dirty())

    # ── loading / saving ─────────────────────────────────────────────────
    def ask_save_if_dirty(self) -> None:
        """Before another series is shown: Save / Discard unsaved conclusion changes."""
        if self.is_dirty() and QMessageBox.question(
                self, "Unsaved conclusion", "The conclusion of this series has unsaved changes. Save them?",
                QMessageBox.Save | QMessageBox.Discard, QMessageBox.Save) == QMessageBox.Save:
            self.save()

    def load(self, series_id: int, trials: List[Dict[str, Any]], labels: List[str]) -> None:
        self._loading = True
        try:
            self._series_id = int(series_id)
            self._data = sc.get(series_id)
            self._editable = bool(self._data.get("ready")) and sc.can_edit()
            req = self._data.get("request")
            if req:
                parts = [f"<b>From the experiment request</b> – {escape(req['title'])}"]
                for lab, key in (("Reason", "reason"), ("Task", "task"), ("Evaluation", "criteria")):
                    if req.get(key):
                        parts.append(f"<b>{lab}:</b> {escape(req[key]).replace(chr(10), '<br>')}")
                self._box_request.setText("<br>".join(parts))
            self._box_request.setVisible(bool(req))
            self._lbl_goal.setVisible(not req)
            self._ed_goal.setVisible(not req)
            self._ed_goal.setPlainText(self._data.get("goal") or "")
            self._choose(self._grp_outcome, self._data.get("outcome"))
            self._ed_summary.setText(self._data.get("summary") or "")
            self._ed_findings.setPlainText(self._data.get("findings") or "")
            self._choose(self._grp_rec, self._data.get("recommendation"))
            self._ed_rec.setPlainText(self._data.get("recommendation_text") or "")
            # best trials: one checkbox per trial
            for cb in self._trial_boxes:
                cb.deleteLater()
            self._trial_boxes = []
            best = set(self._data.get("best_trials") or [])
            for i, (t, lab) in enumerate(zip(trials, labels)):
                tid = int(t.get("id") or t.get("ID") or 0) if isinstance(t, dict) else int(t)
                cb = QCheckBox(str(lab))
                cb.setProperty("trial_id", tid)
                cb.setChecked(tid in best)
                cb.toggled.connect(self._changed)
                self._trials_lay.addWidget(cb, i // 12, i % 12)
                self._trial_boxes.append(cb)
            for w in (self._ed_goal, self._ed_summary, self._ed_findings, self._ed_rec, *self._trial_boxes,
                      *self._grp_outcome.buttons(), *self._grp_rec.buttons()):
                w.setEnabled(self._editable)
            if not self._data.get("ready"):
                self._lbl_info.setText("Conclusions cannot be saved on this database yet.")
            elif not self._editable:
                self._lbl_info.setText("You can read the conclusion; access level 2 is needed to change it.")
            else:
                self._lbl_info.setText("The conclusion of this series - write it whenever the analysis is done "
                                       "(\"Done\" only means: ready to be analysed).")
            self._loaded_snapshot = self.current()
        finally:
            self._loading = False
        self._update_state()

    def has_conclusion(self) -> bool:
        return sc.has_content(self._data) if self._data.get("exists") else False

    def save(self) -> bool:
        if not self._series_id or not self.is_dirty():
            return True
        try:
            res = sc.save(self._series_id, self.current())
        except sc.ConclusionError as e:
            QMessageBox.warning(self, "Conclusion", str(e))
            return False
        except Exception as e:
            QMessageBox.warning(self, "Conclusion", f"The conclusion could not be saved.\n\n{e}")
            return False
        self._data = res["conclusion"]
        self._loaded_snapshot = self.current()
        self._update_state()
        if res.get("notified"):
            self._lbl_state.setText(self._lbl_state.text() + " · requester notified")
        self.saved.emit()
        return True
