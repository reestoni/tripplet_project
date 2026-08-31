# ui/widgets/report_picker.py
"""Gemeinsamer Helfer: gespeicherten Smart-Chart-Report zu einer TrialSeries
auswählen (2026-08-27, Nutzerwunsch: Report-Symbol in All Experiments/
Backlog - analog zum Saved-Reports-Dropdown in Show Experiment, aber ohne
eigenes Dropdown pro Zeile). Gibt es genau einen Report, wird er direkt
zurückgegeben (keine Rückfrage) - erst bei mehreren erscheint ein kleiner
Auswahl-Dialog.

Von ui/screen_all_experiments.py UND ui/screen_backlog.py genutzt.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QDialogButtonBox, QLabel,
)

from db.connection import fetch_all


def get_reports_for_series(series_pk) -> list:
    """Alle gespeicherten (Nicht-Template-)Reports für eine TrialSeries,
    neueste zuerst. Leere Liste bei fehlender Tabelle/DB-Fehler (z.B.
    Offline-Modus, wo tblSmartChartReport nicht Teil der Kopie ist)."""
    if not series_pk:
        return []
    try:
        return fetch_all(
            "SELECT ID, Title, Author FROM tblSmartChartReport "
            "WHERE SeriesPK=? AND IsTemplate=0 ORDER BY UpdatedAt DESC",
            [series_pk],
        )
    except Exception:
        return []


class _ReportPickerDialog(QDialog):
    """Kleiner Auswahl-Dialog, nur wenn mehr als ein Report existiert."""

    def __init__(self, reports: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Report")
        self.setMinimumWidth(380)

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Multiple saved reports exist for this trial series - pick one:"))

        self._list = QListWidget()
        for r in reports:
            title = str(r.get("Title") or "").strip() or "(untitled)"
            author = str(r.get("Author") or "").strip()
            label = f"{title}  —  {author}" if author else title
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, int(r["ID"]))
            self._list.addItem(item)
        if self._list.count():
            self._list.setCurrentRow(0)
        self._list.itemDoubleClicked.connect(lambda _it: self.accept())
        lay.addWidget(self._list)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def selected_report_id(self) -> Optional[int]:
        item = self._list.currentItem()
        return int(item.data(Qt.UserRole)) if item is not None else None


def choose_report_for_series(parent, series_pk) -> Optional[int]:
    """Ermittelt die zu öffnende Report-ID für `series_pk`:
    - keine Reports -> None
    - genau einer -> dessen ID, ohne Rückfrage
    - mehrere -> zeigt _ReportPickerDialog, gibt die Auswahl zurück
      (None bei Abbruch)."""
    reports = get_reports_for_series(series_pk)
    if not reports:
        return None
    if len(reports) == 1:
        return int(reports[0]["ID"])
    dlg = _ReportPickerDialog(reports, parent=parent)
    if dlg.exec() == QDialog.Accepted:
        return dlg.selected_report_id()
    return None
