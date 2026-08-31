# ui/widgets/trial_picker.py
"""Kleiner, wiederverwendbarer Dialog zur Auswahl eines bestehenden Trials
als Ply-Input (Multimaschinen-Halbfabrikat, siehe
screen_create_experiment.get_or_create_shadow_yarn()).

Sucht live nach Experiment-ID oder Serienname und listet einzelne Trials
(nicht ganze Serien) auf, da innerhalb einer Serie unterschiedliche
Versuchsnummern unterschiedliche Halbfabrikat-Ausgaben sind.
"""
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QDialogButtonBox,
)

from db.connection import fetch_all

_SEARCH_LIMIT = 200


def search_trials(term: str):
    """Trials whose experiment ID, series name or machine contain every
    word of the search term (case-insensitive, any order, each word may
    match a different field) - newest experiments first."""
    words = term.split()
    if not words:
        return []
    where_parts = []
    params: list = []
    for word in words:
        like = f"%{word}%"
        where_parts.append(
            "(e.[Experiment ID] LIKE ? OR ts.SeriesName LIKE ? OR m.Maschine LIKE ?)"
        )
        params.extend([like, like, like])
    where_sql = " AND ".join(where_parts)
    return fetch_all(
        "SELECT t.ID AS TrialID, t.Versuchsnummer, ts.SeriesName, "
        "e.[Experiment ID] AS ExperimentID, m.Maschine "
        "FROM tbltrial t "
        "JOIN tbltrialseries ts ON ts.ID = t.TrialSeriesID "
        "JOIN tblexperimente e ON e.ID = ts.ExperimentID "
        "LEFT JOIN tblmaschine m ON m.ID = ts.MachineID "
        f"WHERE {where_sql} "
        f"ORDER BY e.[Experiment ID] DESC, t.Versuchsnummer ASC LIMIT {_SEARCH_LIMIT}",
        params,
    )


def trial_label(row) -> str:
    machine = row.get("Maschine") or "?"
    series = row.get("SeriesName") or ""
    vno = row.get("Versuchsnummer")
    exp_id = row.get("ExperimentID") or "?"
    return f"{exp_id} · {series} · V{vno} — {machine}"


class TrialPickerDialog(QDialog):
    """Live-Suche über Experiment-ID/Serienname, Ergebnisliste einzelner
    Trials. `selected_trial_id()` liefert die gewählte tbltrial.ID (oder
    None, falls per Cancel/ohne Auswahl geschlossen)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select trial as ply source")
        self.setMinimumSize(520, 420)

        root = QVBoxLayout(self)

        hint = QLabel(
            "Search by experiment ID, series name or machine, then pick the specific "
            "trial whose output should be used as this ply's input. Enter multiple "
            "words (in any order) to narrow the results further."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#666; font-size:11px;")
        root.addWidget(hint)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("e.g. 2026-79 eAFK …")
        root.addWidget(self.txt_search)

        self.lst_results = QListWidget()
        root.addWidget(self.lst_results, 1)

        self._btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._btns.button(QDialogButtonBox.Ok).setEnabled(False)
        self._btns.accepted.connect(self.accept)
        self._btns.rejected.connect(self.reject)
        root.addWidget(self._btns)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(250)
        self._debounce.timeout.connect(self._run_search)

        self.txt_search.textChanged.connect(lambda _: self._debounce.start())
        self.lst_results.itemSelectionChanged.connect(
            lambda: self._btns.button(QDialogButtonBox.Ok).setEnabled(
                self.lst_results.currentItem() is not None
            )
        )
        self.lst_results.itemDoubleClicked.connect(lambda _: self.accept())

        self.txt_search.setFocus()

    def _run_search(self):
        term = self.txt_search.text().strip()
        self.lst_results.clear()
        if not term:
            return
        try:
            rows = search_trials(term)
        except Exception as e:
            item = QListWidgetItem(f"Search error: {e}")
            item.setFlags(Qt.NoItemFlags)
            self.lst_results.addItem(item)
            return
        if not rows:
            item = QListWidgetItem("No matching trials.")
            item.setFlags(Qt.NoItemFlags)
            self.lst_results.addItem(item)
            return
        for r in rows:
            item = QListWidgetItem(trial_label(r))
            item.setData(Qt.UserRole, int(r["TrialID"]))
            self.lst_results.addItem(item)

    def selected_trial_id(self) -> Optional[int]:
        item = self.lst_results.currentItem()
        return item.data(Qt.UserRole) if item else None
