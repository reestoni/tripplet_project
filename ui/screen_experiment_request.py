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

from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav


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
        sidebar_callbacks=None,
    ):
        super().__init__()
        self.on_back_home = on_back_home
        self.on_create_experiment_request = on_create_experiment_request
        self.on_open_my_requests = on_open_my_requests
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None
        self._my_requests_badge = None
        self._build_ui()

    def _refresh_sidebar(self):
        """Baut die Sidebar-Navigation neu auf, falls sich der Access-Level
        seit dem letzten Aufbau geändert hat, sonst nur die Badges (siehe
        ui/widgets/sidebar_nav.py::refresh_lazy_sidebar())."""
        import app_meta
        try:
            level = int((app_meta.current_user or {}).get("access_level") or 0)
        except Exception:
            level = 0
        sidebar_nav.refresh_lazy_sidebar(self, level)

    def showEvent(self, event):
        try:
            self._refresh_sidebar()
        except Exception:
            pass
        try:
            self._refresh_my_requests_badge()
        except Exception:
            pass
        super().showEvent(event)

    def _refresh_my_requests_badge(self):
        """Aktualisiert den Badge auf 'My Requests' (offene Aenderungs-Kopien
        die auf Freigabe warten - Superuser sehen alle, normale Nutzer nur
        ihre eigenen). Siehe db/experiment_request_changes.py."""
        import app_meta
        from db import experiment_request_changes as request_changes

        cu = getattr(app_meta, "current_user", {}) or {}
        is_superuser = bool(getattr(app_meta, "is_superuser_level", lambda: False)())
        owner_id = None if is_superuser else cu.get("id")
        cnt = request_changes.count_pending_changes(owner_id)
        sidebar_nav.refresh_badge(self._my_requests_badge, cnt)

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

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring).
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)
        content_layout.addSpacing(48)

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
        try:
            wrapped_my, self._my_requests_badge = sidebar_nav.wrap_with_badge(btn_my, 0)
            wrapped_my.setToolTip("Change proposals waiting for approval")
            btn_row.addWidget(wrapped_my, 1)
        except Exception:
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
        content_layout.addWidget(center, 1)
        root.addWidget(FooterBar(), 0)

    def _go_home(self):
        """Navigiert zurück zum Home-Screen."""
        if callable(self.on_back_home):
            self.on_back_home()
