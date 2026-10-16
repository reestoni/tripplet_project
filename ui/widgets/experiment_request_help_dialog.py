from __future__ import annotations
# ui/widgets/experiment_request_help_dialog.py
"""Kontext-Hilfe fuer den Experiment-Request-Workflow (Create Experiment
Request / My Requests) - Nutzerwunsch 2026-08-31: die Anleitung/Grafik, die
in dieser Session als Artifact gebaut wurde, direkt im Tool verfuegbar
machen, aber nicht dauerhaft sichtbar ("irgendwo als Hilfe").

ExperimentRequestHelpDialog zeigt das Lebenszyklus-Diagramm
(assets/images/experiment_request_flow.svg, Farben 1:1 aus ui/theme.py
uebernommen) plus eine kurze Zusammenfassung der Punkte, die im Alltag am
haeufigsten zu Rueckfragen fuehren (Kopie-Mechanismus beim Bearbeiten einer
bereits genehmigten/verknuepften Anfrage). show_experiment_request_help()
ist der von den Screens genutzte Einstiegspunkt (baut den Dialog lazy,
kein Caching noetig - reines Info-Fenster ohne State).
"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDialogButtonBox, QWidget,
)
from PySide6.QtSvgWidgets import QSvgWidget

from ui.pathutil import resource_path

# Natives SVG-Seitenverhaeltnis (viewBox="-230 0 1170 500" in
# assets/images/experiment_request_flow.svg) - Breite/Hoehe der Anzeige
# unten leiten sich davon ab, damit nichts gestaucht/verzerrt wird.
_SVG_W, _SVG_H = 1080, 461


class ExperimentRequestHelpDialog(QDialog):
    """Zeigt den Experiment-Request-Lebenszyklus (Diagramm + Kurztext)."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Wie funktionieren Experiment Requests?")
        # Muss das SVG (siehe _SVG_W/_SVG_H) plus Rand vollstaendig ohne
        # Scrollen fassen - Bugreport 2026-08-31: "das Fenster das aufgeht
        # ist zu schmal" (vorherige Version: SVG-Mindestbreite 1000px in
        # einem nur 900px breiten Dialog, erzwang horizontales Scrollen).
        self.setMinimumSize(_SVG_W + 80, _SVG_H + 260)
        self.resize(_SVG_W + 100, _SVG_H + 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(14)

        intro = QLabel(
            "From request to experiment: green arrows are steps you take yourself, purple ones a superuser "
            "takes when reviewing."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("font-size: 13px; color: #565656;")
        layout.addWidget(intro)

        self._svg = QSvgWidget(resource_path("assets/images/experiment_request_flow.svg"))
        self._svg.setFixedSize(_SVG_W, _SVG_H)
        layout.addWidget(self._svg, 0, Qt.AlignHCenter)

        note = QLabel(
            "<b>Important when editing:</b> if you change a request that is already approved or linked "
            'to an experiment, a separate <b>copy</b> in status "Open" is created (dashed in the diagram) '
            "– only when a superuser accepts it does the content go into the original, without changing "
            "its status or experiment link."
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            "font-size: 13px; color: #2b2b2b; background: #fff3cd; "
            "border: 1px solid #E6C802; border-radius: 8px; padding: 10px 12px;"
        )
        layout.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(buttons)
        layout.addLayout(btn_row)


def show_experiment_request_help(parent: Optional[QWidget] = None) -> None:
    """Oeffnet die Experiment-Request-Hilfe (siehe ExperimentRequestHelpDialog)."""
    dlg = ExperimentRequestHelpDialog(parent)
    dlg.exec()
