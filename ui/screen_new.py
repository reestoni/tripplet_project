# ui/screen_new.py
"""Leeres Screen-Template für neue Screens.

Diese Datei dient als Vorlage (Boilerplate) wenn ein neuer Screen erstellt wird.
Sie enthält nur Header, Footer und einen leeren Inhaltsbereich.
Klasse umbenennen und _build_ui() mit dem eigentlichen Inhalt füllen.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame
from ui.widgets.header import HeaderBar
from ui.widgets.footer import FooterBar


class ManageYarnScreen(QWidget):
    """Vorlage für einen neuen Screen.

    Muss umbenannt und mit echtem Inhalt befüllt werden.
    """

    def __init__(self, on_back_home=None):
        super().__init__()
        self.on_back_home = on_back_home
        self._build_ui()

    def _build_ui(self):
        """Erstellt das Basis-Layout: Header – Inhalt (Platzhalter) – Footer."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header ganz oben
        header = HeaderBar(title="New Screen", show_home=True)
        header.connect_home(self._go_home)
        root.addWidget(header, 0)

        # Zentrum (Platzhalter, füllt den Raum)
        center = QFrame()
        root.addWidget(center, 1)

        # Footer ganz unten
        footer = FooterBar()
        root.addWidget(footer, 0)

    def _go_home(self):
        """Navigiert zurück zum Home-Screen."""
        if callable(self.on_back_home):
            self.on_back_home()
