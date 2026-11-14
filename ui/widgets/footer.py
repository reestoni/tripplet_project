# ui/widgets/footer.py
"""Globale Fusszeile (FooterBar), die am unteren Rand jedes Screens erscheint.

Zeigt links den eingeloggten Benutzer (Icon + Name) und rechts die
Anwendungsversion an. Wird bei jedem showEvent automatisch aktualisiert,
sodass nach einem Login/Logout der korrekte Name erscheint.

Geheimer Rechtsklick auf den Benutzernamen (2026-08-27, umgezogen aus
ui/screen_home.py - Nutzerwunsch: "da wir nun quasi home 'abgeschossen'
haben, müssen wir die sonst wo verstecken"): da FooterBar in praktisch
jedem Screen eingebunden ist (~30 Aufrufstellen), macht diese eine Stelle
das Easter Egg automatisch app-weit verfügbar, statt es auf einen einzelnen,
kaum noch besuchten Screen zu beschränken.
"""

from pathlib import Path

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QInputDialog, QLineEdit, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon

import app_meta
from app_meta import footer_text

from ui.pathutil import resource_path

try:
    from ui.easter_snake import SnakeDialog as _SnakeDialog
    _SNAKE_AVAILABLE = True
except ImportError:
    _SNAKE_AVAILABLE = False

try:
    from ui.athena_owl import AthenaOwl as _AthenaOwl
    _ATHENA_AVAILABLE = True
except ImportError:
    _ATHENA_AVAILABLE = False


def _asset_path(filename: str) -> Path:
    project_root = Path(__file__).resolve().parents[2]
    return project_root / "assets" / "images" / filename


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

        # Geheimer Rechtsklick (siehe Moduldocstring) - auf Icon UND Label,
        # damit der ganze "Benutzer"-Bereich reagiert, nicht nur der Text.
        self.user_icon.installEventFilter(self)
        self.user_label.installEventFilter(self)
        self._athena = None

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

        # Icon: the profile picture (db/user_avatar.py) if there is one, else assets/images/user_white.png
        try:
            pm = None
            try:
                from ui.widgets.avatar import round_pixmap
                pm = round_pixmap((app_meta.current_user or {}).get("id"), 18)
            except Exception:
                pm = None
            self.user_icon.setFixedSize(18 if pm is not None else 14, 18 if pm is not None else 14)
            if pm is None:
                pm = QPixmap(resource_path("assets/images/user_white.png"))
                if not pm.isNull():
                    pm = pm.scaled(14, 14, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            if not pm.isNull():
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

    # ------------------------------------------------------------------
    # Easter egg (hidden, siehe Moduldocstring): nur Rechtsklick auf den
    # Benutzerbereich zeigt einen Passwort-Dialog. Kein spezieller Hover-
    # Cursor (bleibt der normale Pfeil), damit nichts verrät, dass hier
    # etwas versteckt ist.
    # ------------------------------------------------------------------
    def eventFilter(self, obj, event):
        if obj is self.user_icon or obj is self.user_label:
            try:
                is_mouse_press = (event.type() == event.Type.MouseButtonPress)
            except Exception:
                is_mouse_press = False

            if is_mouse_press:
                try:
                    btn = event.button()
                except Exception:
                    btn = None

                if btn == Qt.RightButton:
                    self._prompt_secret()
                    return True
                return False

        return super().eventFilter(obj, event)

    def _prompt_secret(self):
        try:
            pwd, ok = QInputDialog.getText(
                self, "Passwort", "Passwort eingeben:",
                QLineEdit.EchoMode.Password
            )
        except Exception:
            # Fallback if Qt enum differs
            pwd, ok = QInputDialog.getText(self, "Passwort", "Passwort eingeben:")

        if not (ok and isinstance(pwd, str)):
            return
        pwd_lower = pwd.strip().lower()
        if pwd_lower == "still game" and _SNAKE_AVAILABLE:
            try:
                _SnakeDialog.open_or_raise(parent=self.window())
            except Exception:
                pass
        elif pwd_lower == "fly athena" and _ATHENA_AVAILABLE:
            try:
                self._toggle_athena()
            except Exception:
                pass
        elif pwd_lower == "ynwa":
            self._apply_lfc_icon()

    def _toggle_athena(self):
        """Startet/stoppt (Toggle) die Athena-Eule auf dem Screen, der diese
        Fusszeile gerade zeigt - `self.parentWidget()` ist dieser Screen
        (FooterBar wird als letztes Widget in dessen Root-Layout eingefügt,
        siehe Klassendocstring), ein deutlich passenderer Rahmen für die
        Flug-/Schlafpositionierung als die 24px hohe Fusszeile selbst."""
        parent = self.parentWidget() or self
        if self._athena is not None:
            if getattr(self._athena, "_working", False):
                self._athena.stop_working()
                return
            self._athena.deleteLater()
            self._athena = None

        self._athena = _AthenaOwl(parent)
        self._athena.place_sleeping()
        self._athena.raise_()
        self._athena.show()
        self._athena.start_demo()

    def _apply_lfc_icon(self):
        """You'll Never Walk Alone - wechselt Fenster-/App-Icon auf LFC."""
        try:
            icon_path = _asset_path("lfc.ico")
            if not icon_path.exists():
                img_dir = icon_path.parent
                try:
                    matches = [p for p in img_dir.glob("*.ico") if p.name.lower() == "lfc.ico"]
                    if matches:
                        icon_path = matches[0]
                except Exception:
                    pass

            if not icon_path.exists():
                return
            lfc_icon = QIcon(str(icon_path))

            # 1) Set the icon on the top-level window (taskbar/titlebar)
            try:
                top = self.window()
                if top is not None:
                    top.setWindowIcon(lfc_icon)
                    try:
                        top.update()
                        top.repaint()
                    except Exception:
                        pass
            except Exception:
                pass

            # 2) Also set the application icon (helps on some platforms)
            try:
                app = QApplication.instance()
                if app is not None:
                    app.setWindowIcon(lfc_icon)
                    try:
                        QApplication.processEvents()
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass
