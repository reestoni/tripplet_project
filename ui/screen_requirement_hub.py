# ui/screen_requirement_hub.py
"""Requirement Hub – Schaltzentrale für das TrippleT Requirement Set Feature.

Einstiegspunkt für alle drei Modi:
  - Quick Scan   : Formular ausfüllen, Top-Trials sofort, kein Speichern
  - Research     : Ruleset ohne Projekt, selektiv speichern (geplant)
  - Project Eval : Ruleset an Projekt gebunden, Snapshot + Report (geplant)

Aufbau analog screen_home.py (Card-Struktur, HeaderBar, FooterBar).
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QSizePolicy, QSpacerItem,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QIcon

from ui.widgets.header import HeaderBar
from ui.widgets.footer import FooterBar
import app_meta


class RequirementHubScreen(QWidget):
    def __init__(self,
                 on_back_home=None,
                 on_quick_scan=None):
        super().__init__()
        self._on_back_home  = on_back_home
        self._on_quick_scan = on_quick_scan

        self._build_ui()

    # ------------------------------------------------------------------
    # Helpers (analog screen_home.py)
    # ------------------------------------------------------------------
    def _asset_path(self, filename: str) -> Path:
        project_root = Path(__file__).resolve().parents[1]
        return project_root / "assets" / "images" / filename

    def _icon_label(self, filename: str, size: int = 18) -> QLabel:
        lbl = QLabel()
        pm = QPixmap(str(self._asset_path(filename)))
        if not pm.isNull():
            pm = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl.setScaledContents(False)
            lbl.setPixmap(pm)
            right_margin = 6
            lbl.setFixedHeight(size)
            lbl.setFixedWidth(size + right_margin)
        lbl.setContentsMargins(0, 0, 6, 0)
        return lbl

    def _icon_btn(self, text: str, icon_file: str, style: str, on_click=None) -> QPushButton:
        """Button mit Icon + Text. on_click=None → disabled."""
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

    # ------------------------------------------------------------------
    # Card builder
    # ------------------------------------------------------------------
    def _build_requirement_card(self) -> QFrame:
        """Erstellt die Requirement-Card mit allen Modus-Buttons."""
        card = QFrame(objectName="Card")
        card.setMaximumWidth(800)
        card.setMinimumWidth(700)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Card Header ---
        header = QFrame(objectName="CardHeader")
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(12, 4, 12, 4)
        hdr_layout.setSpacing(8)
        hdr_layout.addWidget(self._icon_label("requirement_hub_white.png", 24), 0, Qt.AlignVCenter)
        title = QLabel("Requirement Hub")
        title.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        hdr_layout.addWidget(title, 0, Qt.AlignVCenter)
        layout.addWidget(header)

        # --- Card Body ---
        body = QFrame()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 16, 24, 16)
        body_layout.setSpacing(12)

        # Zeile 1: Quick Scan + Platzhalter
        row1 = QHBoxLayout()
        row1.setSpacing(20)

        btn_quick_scan = self._icon_btn(
            "Quick Scan", "quick_search.png", "GreenBtn",
            self._on_quick_scan
        )
        row1.addWidget(btn_quick_scan, 1)
        row1.addWidget(QFrame(), 1)  # Platzhalter für zweiten Button

        body_layout.addLayout(row1)
        body_layout.addSpacerItem(
            QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )
        layout.addWidget(body)

        return card

    # ------------------------------------------------------------------
    # UI aufbauen
    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = HeaderBar(
            title="Requirement Hub",
            show_home=True,
        )
        if callable(self._on_back_home):
            header.connect_home(self._on_back_home)
        root.addWidget(header)

        # Scrollbarer Center-Bereich
        center = QFrame()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 24, 0, 0)
        center_layout.setSpacing(16)

        req_card = self._build_requirement_card()
        center_layout.addWidget(req_card, 0, Qt.AlignHCenter | Qt.AlignTop)
        center_layout.addStretch()

        root.addWidget(center, 1)
        root.addWidget(FooterBar())