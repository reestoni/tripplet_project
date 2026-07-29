# ui/widgets/footer.py
"""Globale Fusszeile (FooterBar), die am unteren Rand jedes Screens erscheint.

Zeigt links den eingeloggten Benutzer (Icon + Name) und rechts die
Anwendungsversion an. Wird bei jedem showEvent automatisch aktualisiert,
sodass nach einem Login/Logout der korrekte Name erscheint.
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

import app_meta
from app_meta import footer_text

from ui.pathutil import resource_path


class FooterBar(QFrame):
    """Fussleiste mit Benutzeranzeige (links) und Versionsnummer (rechts).

    Wird in jedem Screen als letztes Widget im Root-Layout eingefügt.
    Beispiel::

        root.addWidget(FooterBar(), 0)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BottomBar")
        self.setFixedHeight(24)
        bl = QHBoxLayout(self)
        bl.setContentsMargins(12, 0, 18, 0)

        # Links: User icon + name
        self.user_icon = QLabel("", objectName="FooterUserIcon")
        self.user_icon.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.user_icon.setFixedSize(14, 14)

        self.user_label = QLabel("", objectName="FooterUser")
        self.user_label.setStyleSheet("color: white; font-size: 11px;")
        self.user_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Rechts: Version
        self.version_label = QLabel(footer_text(), objectName="FooterVersion")
        self.version_label.setStyleSheet("color: white; font-size: 11px;")
        self.version_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        bl.addWidget(self.user_icon)
        bl.addWidget(self.user_label)
        bl.addStretch(1)
        bl.addWidget(self.version_label)

        # Initial paint
        self.refresh()

    def showEvent(self, event):
        """Aktualisiert Benutzer und Version bei jedem Screen-Wechsel."""
        try:
            self.refresh()
        except Exception:
            pass
        return super().showEvent(event)

    def refresh(self):
        """Liest den aktuell eingeloggten Benutzer aus app_meta und aktualisiert die Anzeige.

        Liest ``app_meta.current_user`` (dict mit ``first_name``/``last_name``)
        und setzt Icon + Label. Fehler werden still ignoriert, damit ein fehlender
        Login die Anzeige nicht abstürzen lässt.
        """
        # Links: icon + FirstName LastName
        try:
            fn = (app_meta.current_user or {}).get("first_name")
            ln = (app_meta.current_user or {}).get("last_name")
            fn = "" if fn is None else str(fn).strip()
            ln = "" if ln is None else str(ln).strip()
            full = (fn + " " + ln).strip()
        except Exception:
            full = ""

        # Icon (assets/images/user_white.png)
        try:
            icon_path = resource_path("assets/images/user_white.png")
            pm = QPixmap(icon_path)
            if not pm.isNull():
                pm = pm.scaled(14, 14, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.user_icon.setPixmap(pm)
                self.user_icon.setVisible(True)
            else:
                self.user_icon.clear()
                self.user_icon.setVisible(False)
        except Exception:
            self.user_icon.clear()
            self.user_icon.setVisible(False)

        self.user_label.setText(full if full else "")

        # Rechts: Version (falls du Version zur Laufzeit änderst)
        from app_meta import footer_text as _ft
        self.version_label.setText(_ft())
