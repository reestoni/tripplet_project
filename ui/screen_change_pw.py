# ui/screen_change_pw.py
"""Passwort-Änderungs-Screen (ChangePasswordScreen).

Wird nach dem Login angezeigt, wenn der Admin das Flag ``force_pw_change``
gesetzt hat, oder wenn der Benutzer selbst sein Passwort ändern möchte.

Ablauf:
  1. ``set_user(username)`` aufrufen, bevor der Screen angezeigt wird.
  2. Benutzer gibt altes + neues Passwort ein.
  3. ``_on_ok()`` validiert (altes PW korrekt, neue PW identisch, PW != Username)
     und ruft ``db.connection.update_user_password()`` auf.
  4. Bei Erfolg: Callback ``on_dismiss()`` führt zurück zum Login.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QLineEdit, QPushButton, QMessageBox, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt

from db.connection import verify_user_password, update_user_password, user_exists
from ui.widgets.footer import FooterBar
from ui.widgets.header import HeaderBar


class ChangePasswordScreen(QWidget):
    """Formular zum Ändern des eigenen Passworts.

    Validierungsregeln:
    - Altes Passwort muss korrekt sein (Argon2-Vergleich via DB).
    - Neues Passwort und Wiederholung müssen identisch sein.
    - Neues Passwort darf nicht gleich dem alten sein.
    - Neues Passwort darf nicht gleich dem Benutzernamen sein (case-insensitive).

    Args:
        on_dismiss: Callable ohne Argumente; wird aufgerufen wenn der Benutzer
                    auf «Dismiss» klickt oder nach erfolgreichem PW-Wechsel.
    """

    def __init__(self, on_dismiss=None):
        super().__init__()
        self.on_dismiss = on_dismiss  # callable() -> zurück zum Login
        self._username: str | None = None
        self._build_ui()

    def set_user(self, username: str):
        """Setzt den Benutzernamen und leert alle Eingabefelder.

        Muss vor dem Anzeigen des Screens aufgerufen werden.

        Args:
            username: Der Benutzername aus ``app_meta.current_user``.
        """
        self._username = username.strip() if username else None
        self.txt_old.clear()
        self.txt_new.clear()
        self.txt_rep.clear()

    def _build_ui(self):
        """Erstellt das Formular-Layout (Header, Card mit 3 Feldern, Buttons, Footer)."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Standard Header (ohne Home, da vor Login-Kontext) ---
        header = HeaderBar(title="Change Password", show_home=False, show_search=False)
        root.addWidget(header)

        # --- Center Card ---
        center = QFrame()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 24, 0, 0)
        center_layout.setSpacing(0)

        card = QFrame(objectName="Card")
        card.setMaximumWidth(640)
        card.setMinimumWidth(560)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # Card-Header (Titelzeile)
        card_header = QFrame(objectName="CardHeader")
        hdr_layout = QHBoxLayout(card_header)
        hdr_layout.setContentsMargins(12, 4, 12, 4)
        title = QLabel("Set New Password")
        title.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        hdr_layout.addWidget(title)
        card_layout.addWidget(card_header)

        # Card-Body (Eingabefelder)
        body = QFrame()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 16, 24, 16)
        body_layout.setSpacing(14)

        # Altes Passwort
        row_old = QHBoxLayout()
        lbl_old = QLabel("Old Password")
        lbl_old.setFixedWidth(150)
        self.txt_old = QLineEdit()
        self.txt_old.setEchoMode(QLineEdit.Password)
        row_old.addWidget(lbl_old)
        row_old.addWidget(self.txt_old)

        # Neues Passwort
        row_new = QHBoxLayout()
        lbl_new = QLabel("New Password")
        lbl_new.setFixedWidth(150)
        self.txt_new = QLineEdit()
        self.txt_new.setEchoMode(QLineEdit.Password)
        row_new.addWidget(lbl_new)
        row_new.addWidget(self.txt_new)

        # Wiederholung
        row_rep = QHBoxLayout()
        lbl_rep = QLabel("Repeat New Password")
        lbl_rep.setFixedWidth(150)
        self.txt_rep = QLineEdit()
        self.txt_rep.setEchoMode(QLineEdit.Password)
        row_rep.addWidget(lbl_rep)
        row_rep.addWidget(self.txt_rep)

        body_layout.addLayout(row_old)
        body_layout.addLayout(row_new)
        body_layout.addLayout(row_rep)

        # OK / Dismiss Buttons
        btn_row = QHBoxLayout()
        btn_row.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.btn_ok = QPushButton("OK")
        self.btn_ok.clicked.connect(self._on_ok)

        self.btn_dismiss = QPushButton("Dismiss")
        self.btn_dismiss.clicked.connect(self._on_dismiss)

        btn_row.addWidget(self.btn_ok, 0, Qt.AlignLeft)
        btn_row.addSpacing(20)
        btn_row.addWidget(self.btn_dismiss, 0, Qt.AlignLeft)
        btn_row.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        body_layout.addLayout(btn_row)
        card_layout.addWidget(body)
        center_layout.addWidget(card, 0, Qt.AlignHCenter | Qt.AlignTop)

        root.addWidget(center, 1)
        root.addWidget(FooterBar())

    # --- Button-Handler ---

    def _on_ok(self):
        """Validiert alle Eingaben und speichert das neue Passwort in der DB.

        Validierungsreihenfolge:
        1. Benutzername gültig und in DB vorhanden
        2. Alle drei Felder befüllt
        3. Altes Passwort korrekt
        4. Neue Passwörter identisch
        5. Neues PW verschieden vom alten
        6. Neues PW verschieden vom Benutzernamen (case-insensitive)
        """
        u = (self._username or "").strip()
        old = self.txt_old.text()
        new = self.txt_new.text()
        rep = self.txt_rep.text()

        # Existenz prüfen (Safety; normal schon vor dem Öffnen geprüft)
        if not u or not user_exists(u):
            QMessageBox.warning(self, "No valid user",
                                "No valid user is set. Returning to login.")
            self._on_dismiss()
            return

        # Alle Felder befüllt?
        if not (old and new and rep):
            QMessageBox.warning(self, "Incomplete input",
                                "Please fill out all three fields.")
            return

        # Altes Passwort korrekt?
        if not verify_user_password(u, old):
            QMessageBox.warning(self, "Wrong password",
                                "The old password is not correct.")
            self.txt_old.clear()
            self.txt_new.clear()
            self.txt_rep.clear()
            self.txt_old.setFocus()
            return

        # Neue Passwörter identisch? (case-sensitive)
        if new != rep:
            QMessageBox.warning(self, "Passwords do not match",
                                "\u201cNew Password\u201d and \u201cRepeat New Password\u201d must be identical.")
            self.txt_new.clear()
            self.txt_rep.clear()
            self.txt_new.setFocus()
            return

        # Neues Passwort muss sich vom alten unterscheiden
        if new == old:
            QMessageBox.warning(self, "Invalid password",
                                "The new password must be different from the old one.")
            self.txt_new.clear()
            self.txt_rep.clear()
            self.txt_new.setFocus()
            return

        # Neues Passwort darf nicht gleich dem Benutzernamen sein (case-insensitive)
        if new.lower() == u.lower():
            QMessageBox.warning(self, "Insecure password",
                                "The new password must not be the same as the username.")
            self.txt_new.clear()
            self.txt_rep.clear()
            self.txt_new.setFocus()
            return

        # Passwort in DB aktualisieren (Argon2-Hash)
        if update_user_password(u, new):
            QMessageBox.information(self, "Password changed",
                                    "Your password has been changed. Log in with the new password.")
            self._on_dismiss()  # zurück zum Login
        else:
            QMessageBox.critical(self, "Update failed",
                                 "Password could not be updated. Please try again.")

    def _on_dismiss(self):
        """Leert alle Felder und kehrt zum Login zurück."""
        self.txt_old.clear()
        self.txt_new.clear()
        self.txt_rep.clear()
        if callable(self.on_dismiss):
            self.on_dismiss()
