# ui/screen_experiment_request.py
"""Einstiegs-Screen für das Experiment-Request-System.

Zeigt zwei Schaltflächen an:
  - «Create Experiment Request»: öffnet den Erstellungs-Screen
  - «My Requests»: zeigt eigene Request-Liste

Dieser Screen ist ein reiner Navigations-Hub ohne eigene Datenlogik.
"""

from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
)

from ui.widgets.header import HeaderBar
from ui.widgets.footer import FooterBar


class ExperimentRequestScreen(QWidget):
    """Navigations-Screen für das Experiment-Request-System.

    Args:
        on_back_home:                     Callback → Home-Screen
        on_create_experiment_request:     Callback → Erstellungs-Screen
        on_open_my_requests:              Callback → Meine Anfragen
    """
    def __init__(
        self,
        on_back_home=None,
        on_create_experiment_request=None,
        on_open_my_requests=None,
    ):
        super().__init__()
        self.on_back_home = on_back_home
        self.on_create_experiment_request = on_create_experiment_request
        self.on_open_my_requests = on_open_my_requests
        self._build_ui()

    # ---------- Helpers ----------
    def _asset_path(self, filename: str) -> Path:
        """Gibt den absoluten Pfad zu einer Asset-Datei zurück."""
        project_root = Path(__file__).resolve().parents[1]
        return project_root / "assets" / "images" / filename

    def _icon_label(self, filename: str, size: int = 24) -> QLabel:
        """Erstellt ein QLabel mit einem skalierten Icon aus dem assets/images-Ordner."""
        lbl = QLabel()
        pm = QPixmap(str(self._asset_path(filename)))
        if not pm.isNull():
            pm = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl.setPixmap(pm)
            lbl.setFixedHeight(size)
            lbl.setFixedWidth(size + 6)
        lbl.setContentsMargins(0, 0, 6, 0)
        return lbl

    def _icon_btn(self, text: str, icon_file: str, style: str, on_click=None) -> QPushButton:
        """Erstellt einen Button mit Icon. Wenn on_click=None, wird der Button deaktiviert."""
        btn = QPushButton(text)
        btn.setObjectName(style)
        icon_path = self._asset_path(icon_file)
        if icon_path.exists():
            btn.setIcon(QIcon(str(icon_path)))
            btn.setIconSize(QSize(18, 18))
        if callable(on_click):
            btn.clicked.connect(lambda *_: on_click())
        else:
            btn.setEnabled(False)
        return btn

    # ---------- UI ----------
    def _build_ui(self):
        """Erstellt das Layout: Header, zentrierte Card mit zwei Navigations-Buttons, Footer."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = HeaderBar(title="Experiment Request", show_home=True)
        header.connect_home(self._go_home)
        root.addWidget(header, 0)
        root.addSpacing(48)

        center = QFrame()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 24, 0, 0)
        center_layout.setSpacing(16)

        card = QFrame(objectName="Card")
        card.setMaximumWidth(800)
        card.setMinimumWidth(700)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        card_header = QFrame(objectName="CardHeader")
        hdr_layout = QHBoxLayout(card_header)
        hdr_layout.setContentsMargins(12, 4, 12, 4)
        hdr_layout.setSpacing(8)

        hdr_layout.addWidget(
            self._icon_label("experiment_request_white.png", 24),
            0,
            Qt.AlignVCenter,
        )
        title = QLabel("Experiment Requests")
        title.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        hdr_layout.addWidget(title, 0, Qt.AlignVCenter)
        hdr_layout.addSpacerItem(
            QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )
        card_layout.addWidget(card_header)

        body = QFrame()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(24, 16, 24, 16)
        body_layout.setSpacing(20)

        left_col = QVBoxLayout()
        left_col.setSpacing(20)

        btn_create = self._icon_btn(
            "Create Experiment Request",
            "create_experiment_request.png",
            "GreenBtn",
            self.on_create_experiment_request,
        )

        btn_my = self._icon_btn(
            "My Requests",
            "my_experiment_requests.png",
            "GreenBtn",
            self.on_open_my_requests,
        )

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addWidget(btn_create, 1)
        btn_row.addWidget(btn_my, 1)

        left_col.addLayout(btn_row)
        left_col.addSpacerItem(
            QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        body_layout.addLayout(left_col, 1)
        body_layout.addSpacerItem(
            QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )
        card_layout.addWidget(body)

        center_layout.addWidget(card, 0, Qt.AlignHCenter | Qt.AlignTop)
        root.addWidget(center, 1)
        root.addWidget(FooterBar(), 0)

    def _go_home(self):
        """Navigiert zurück zum Home-Screen."""
        if callable(self.on_back_home):
            self.on_back_home()
