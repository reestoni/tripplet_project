from __future__ import annotations
# ui/widgets/header.py
"""Globale Kopfzeile (HeaderBar), die am oberen Rand jedes Screens erscheint."""

from typing import Optional, Callable

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame, QStackedWidget,
)
from PySide6.QtCore import Qt, Signal, QSize, QRect
from PySide6.QtGui import QPixmap, QIcon, QPainter, QColor, QFont, QPen
from ui.pathutil import resource_path


class BellButton(QWidget):
    """Glöckchen-Button mit rotem Badge-Zähler oben rechts."""

    clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Notifications")
        self._count = 0
        self._total = 0
        self._hovered = False
        self._icon = QPixmap(resource_path("assets/images/bell.png"))

    def set_count(self, count: int, total: int = 0) -> None:
        """Aktualisiert Badge-Zahl und Sichtbarkeit.

        Bell ist sichtbar wenn count > 0 (roter Badge) ODER total > 0 (kein Badge, nur Icon).
        """
        self._count = max(0, count)
        self._total = max(0, total)
        self.setVisible(self._count > 0 or self._total > 0)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Hover-Hintergrund
        if self._hovered:
            p.setBrush(QColor(255, 255, 255, 40))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(self.rect(), 8, 8)

        # Bell-Icon zentriert
        if not self._icon.isNull():
            icon_size = 22
            x = (self.width() - icon_size) // 2
            y = (self.height() - icon_size) // 2
            p.drawPixmap(x, y, self._icon.scaled(
                icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # Badge
        if self._count > 0:
            badge_text = str(self._count) if self._count < 100 else "99+"
            badge_w = max(18, len(badge_text) * 7 + 6)
            badge_h = 18
            bx = self.width() - badge_w + 2
            by = 1

            # Roter Kreis
            p.setBrush(QColor("#E74C3C"))
            p.setPen(QColor("#ffffff") if False else Qt.NoPen)
            p.drawRoundedRect(QRect(bx, by, badge_w, badge_h), badge_h // 2, badge_h // 2)

            # Weisser Text
            font = QFont()
            font.setPixelSize(10)
            font.setBold(True)
            p.setFont(font)
            p.setPen(QColor("#ffffff"))
            p.drawText(QRect(bx, by, badge_w, badge_h), Qt.AlignCenter, badge_text)

        p.end()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


class HeaderBar(QFrame):
    """Kopfleiste mit Navigation, Titel, Logos und optionalem Log-Out-Button.

    Signale:
        homeClicked:   Wird ausgelöst, wenn der Home-Button geklickt wird.
        backClicked:   Wird ausgelöst, wenn der Back-Button geklickt wird.
        searchClicked: Wird ausgelöst, wenn der Such-Button geklickt wird
                       und kein globaler ``app_meta.open_quick_search`` registriert ist.

    Args:
        title:       Titeltext der Seite.
        show_home:   Home-Button anzeigen (Standard: True).
        show_back:   Back-Button unterhalb des Home-Buttons anzeigen (Standard: False).
        on_logout:   Callable für den Log-Out-Button; wenn None, wird kein Button gezeigt.
        logout_text: Beschriftung des Log-Out-Buttons (Standard: ``"Log Out"``).
    """

    homeClicked = Signal()
    backClicked = Signal()
    searchClicked = Signal()

    def __init__(
        self,
        title: str = "Home",
        *,
        show_home: bool = True,
        show_back: bool = False,
        on_logout: Optional[Callable[[], None]] = None,
        logout_text: str = "Log Out",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent, objectName="TopBar")
        self.setFixedHeight(90)

        self._on_logout = on_logout

        # ---- Home-Slot (feste Breite, damit Titel nicht springt) ----
        BTN_WIDTH = 60
        self._btn_home = QPushButton(objectName="HomeBtn")
        self._btn_home.setCursor(Qt.PointingHandCursor)
        self._btn_home.clicked.connect(self.homeClicked.emit)

        icon_path = resource_path("assets/icons/home.png")
        icon = QIcon(icon_path)
        if icon.isNull():
            self._btn_home.setText("Home")
        else:
            self._btn_home.setIcon(icon)
            self._btn_home.setText("")

        self._btn_home.setFixedWidth(BTN_WIDTH)

        # QStackedWidget ermöglicht es, Home-Button durch unsichtbaren Platzhalter
        # zu ersetzen, ohne das Layout zu verschieben.
        self._home_stack = QStackedWidget()
        self._home_stack.setMinimumWidth(BTN_WIDTH)
        self._home_stack.setMaximumWidth(BTN_WIDTH)
        self._home_stack.addWidget(self._btn_home)   # index 0: Button
        self._home_stack.addWidget(QWidget())        # index 1: Platzhalter
        self._home_stack.setCurrentIndex(0 if show_home else 1)

        # Optionaler Back-Button direkt unter dem Home-Button
        self._btn_back = QPushButton("Back", objectName="HomeBtn")
        self._btn_back.setCursor(Qt.PointingHandCursor)
        self._btn_back.clicked.connect(self.backClicked.emit)
        self._btn_back.setVisible(show_back)

        # Gemeinsame Spalte für Home + Back (fixe Breite)
        self._nav_col = QWidget()
        nav_layout = QVBoxLayout(self._nav_col)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(4)
        nav_layout.addWidget(self._home_stack, 0, Qt.AlignTop | Qt.AlignHCenter)
        nav_layout.addWidget(self._btn_back, 0, Qt.AlignTop | Qt.AlignHCenter)
        self._nav_col.setMinimumWidth(BTN_WIDTH)
        self._nav_col.setMaximumWidth(BTN_WIDTH)

        # ---- Titel ----
        self._title_label = QLabel(title, objectName="TopTitle")
        self._title_label.setAlignment(Qt.AlignVCenter)

        # ---- Logos ----
        self._logo_tripplet = QLabel(objectName="LogoCenter")
        self._logo_tripplet.setAlignment(Qt.AlignCenter)
        tri = QPixmap(resource_path("assets/images/tricolour.png"))
        if not tri.isNull():
            self._logo_tripplet.setPixmap(tri.scaledToHeight(60, Qt.SmoothTransformation))

        self._logo_heberlein = QLabel(objectName="LogoRight")
        self._logo_heberlein.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        heb = QPixmap(resource_path("assets/images/logo-heberlein-weiss.png"))
        if not heb.isNull():
            self._logo_heberlein.setPixmap(heb.scaledToHeight(63, Qt.SmoothTransformation))

        # User wird im Header bewusst NICHT angezeigt (siehe FooterBar).

        # ---- Log Out Button (optional) ----
        self._btn_logout: Optional[QPushButton] = None
        if callable(self._on_logout):
            # Gleicher Stil wie Home -> gleicher objectName
            self._btn_logout = QPushButton(logout_text, objectName="HomeBtn")
            self._btn_logout.setCursor(Qt.PointingHandCursor)
            self._btn_logout.setMinimumHeight(self._btn_home.sizeHint().height())
            self._btn_logout.clicked.connect(self._on_logout)

        # ---- Notification Bell Button ----
        self._btn_bell = BellButton()
        self._btn_bell.setVisible(False)
        self._bell_count = 0

        # ---- Search Button ----
        self._btn_search = QPushButton("🔍", objectName="HomeBtn")
        self._btn_search.setCursor(Qt.PointingHandCursor)
        self._btn_search.setToolTip("Quick Search  (Ctrl+F)")
        self._btn_search.setFixedSize(36, 36)
        self._btn_search.clicked.connect(self._on_search_clicked)

        # ---- Layout: [Home+Back] [Titel] [Stretch] [TrippleT] [Stretch] [(LogOut)] [Suche] [Heberlein] ----
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 6, 16, 6)
        lay.setSpacing(12)

        lay.addWidget(self._nav_col, 0, Qt.AlignVCenter)
        lay.addWidget(self._title_label, 0, Qt.AlignVCenter)
        lay.addStretch(1)
        lay.addWidget(self._logo_tripplet, 0, Qt.AlignCenter)
        lay.addStretch(1)

        if self._btn_logout is not None:
            lay.addWidget(self._btn_logout, 0, Qt.AlignRight | Qt.AlignVCenter)
            lay.addSpacing(24)
        lay.addWidget(self._btn_bell, 0, Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(self._btn_search, 0, Qt.AlignRight | Qt.AlignVCenter)
        lay.addSpacing(8)
        lay.addWidget(self._logo_heberlein, 0, Qt.AlignRight)

    # ---- Öffentliche API ----

    def set_title(self, title: str):
        """Setzt den Titeltext zur Laufzeit (z.B. wenn Experiment-ID bekannt ist)."""
        self._title_label.setText(title)

    def set_bell_count(self, count: int, total: int = 0) -> None:
        """Setzt die Anzahl ungelesener Notifications und aktualisiert das Badge.

        Args:
            count: Anzahl ungelesener Notifications.
            total: Gesamtanzahl (gelesen + ungelesen). Bell bleibt sichtbar wenn total > 0.
        """
        self._bell_count = max(0, count)
        self._btn_bell.set_count(self._bell_count, total=max(0, total))

    def connect_bell(self, slot: Callable) -> None:
        """Verbindet den Bell-Button mit einem Slot."""
        self._btn_bell.clicked.connect(slot)

    def set_home_visible(self, visible: bool):
        """Zeigt oder versteckt den Home-Button (ohne das Layout zu verschieben)."""
        self._home_stack.setCurrentIndex(0 if visible else 1)

    def set_back_visible(self, visible: bool):
        """Zeigt oder versteckt den Back-Button."""
        if hasattr(self, "_btn_back"):
            self._btn_back.setVisible(visible)

    def connect_home(self, slot):
        """Verbindet den Home-Button-Klick mit einem Callable."""
        self.homeClicked.connect(slot)

    def connect_back(self, slot):
        """Verbindet den Back-Button-Klick mit einem Callable."""
        self.backClicked.connect(slot)

    def connect_search(self, slot):
        """Verbindet das searchClicked-Signal mit einem Callable (Fallback wenn app_meta nicht gesetzt)."""
        self.searchClicked.connect(slot)

    def _on_search_clicked(self):
        """Öffnet Quick Search via app_meta (global) oder sendet searchClicked-Signal."""
        try:
            import app_meta
            if callable(app_meta.open_quick_search):
                app_meta.open_quick_search()
                return
        except Exception:
            pass
        self.searchClicked.emit()