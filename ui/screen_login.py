# ui/screen_login.py
"""Login-Screen für TrippleT.

Zeigt ein Formular mit Benutzername und Passwort. Bei erfolgreichem Login
werden alle Benutzerinformationen in ``app_meta.current_user`` geschrieben
und der ``on_success``-Callback aufgerufen.

Sicherheitsregeln:
  - Passwort darf nicht gleich dem Benutzernamen sein (case-insensitive).
  - Inaktive Benutzer werden geblockt (tblUser.Active).
  - Draft-ExperimentRequests des Benutzers werden beim Login automatisch bereinigt.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QLineEdit, QPushButton, QMessageBox, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt

from ui.widgets.footer import FooterBar
from ui.widgets.header import HeaderBar

# --- DB-Abhängigkeiten ---
from db.connection import (
    check_credentials,
    user_exists,
    get_user_access_level,
    get_user_access_right,
    is_user_active,
    verify_user_password,
    get_user_admin_box,
    cleanup_draft_experiment_requests,
    get_user_first_last_name,
    get_user_accent_colour,
)
try:
    from db.connection import get_user_id  # type: ignore
except Exception:
    get_user_id = None  # type: ignore

# --- Globaler Benutzerkontext ---
import app_meta
from ui.widgets.friendly_error import show_error


class LoginScreen(QWidget):
    """Login-Formular mit Benutzername und Passwort.

    Args:
        on_success:   Callable(userinfo: dict) – wird nach erfolgreichem Login
                      aufgerufen. ``userinfo`` enthält: id, username, first_name,
                      last_name, access_level, access_right, admin_box, accent_colour.
        on_change_pw: Callable(username: str) – öffnet den Passwort-Änderungs-Screen
                      mit dem vorgegebenen Benutzernamen.
    """

    def __init__(self, on_success, on_change_pw):
        super().__init__()
        self.on_success = on_success
        self.on_change_pw = on_change_pw
        self._build_ui()

    def _build_ui(self):
        """Erstellt das Login-Formular (Header, Card, Benutzername/PW-Felder, Buttons, Footer)."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header ohne Home-Button (kein Zurück vom Login)
        header = HeaderBar(title="Log In", show_home=False, show_search=False)
        root.addWidget(header)

        # --- Zentrierte Card ---
        center = QFrame()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 24, 0, 0)
        center_layout.setSpacing(0)

        card = QFrame(objectName="Card")
        card.setMaximumWidth(480)
        card.setMinimumWidth(420)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # Card-Header (Titelzeile)
        card_header = QFrame(objectName="CardHeader")
        hdr_layout = QHBoxLayout(card_header)
        hdr_layout.setContentsMargins(12, 4, 12, 4)
        title = QLabel("Your Credentials")
        title.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        hdr_layout.addWidget(title)
        card_layout.addWidget(card_header)

        # Card-Body mit Eingabefeldern
        body = QFrame()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 16, 24, 16)
        body_layout.setSpacing(14)

        # Benutzername-Feld
        row_user = QHBoxLayout()
        lbl_user = QLabel("User Name")
        lbl_user.setFixedWidth(110)
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("User")
        row_user.addWidget(lbl_user)
        row_user.addWidget(self.txt_user)

        # Passwort-Feld (verdeckte Eingabe)
        row_pw = QHBoxLayout()
        lbl_pw = QLabel("Your Password")
        lbl_pw.setFixedWidth(110)
        self.txt_pw = QLineEdit()
        self.txt_pw.setEchoMode(QLineEdit.Password)
        self.txt_pw.setPlaceholderText("Password")
        row_pw.addWidget(lbl_pw)
        row_pw.addWidget(self.txt_pw)

        body_layout.addLayout(row_user)
        body_layout.addLayout(row_pw)

        # Buttons: Log In + Change Password
        btn_row = QHBoxLayout()
        btn_row.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.btn_login = QPushButton("Log In")
        self.btn_login.setEnabled(False)  # aktiviert sobald beide Felder befüllt sind
        self.btn_login.clicked.connect(self._attempt_login)

        self.btn_change = QPushButton("Change Password")
        self.btn_change.clicked.connect(self._open_change_pw_if_valid)

        btn_row.addWidget(self.btn_login, 0, Qt.AlignLeft)
        btn_row.addSpacing(12)
        btn_row.addWidget(self.btn_change, 0, Qt.AlignLeft)
        btn_row.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        body_layout.addLayout(btn_row)
        card_layout.addWidget(body)
        center_layout.addWidget(card, 0, Qt.AlignHCenter | Qt.AlignTop)

        root.addWidget(center, 1)
        root.addWidget(FooterBar())

        # UX: Login-Button erst aktiv wenn beide Felder befüllt; Enter = Login
        self.txt_user.textChanged.connect(self._toggle_login_enabled)
        self.txt_pw.textChanged.connect(self._toggle_login_enabled)
        self.txt_user.returnPressed.connect(self._attempt_login)
        self.txt_pw.returnPressed.connect(self._attempt_login)

    def _toggle_login_enabled(self):
        """Aktiviert den Login-Button nur wenn Benutzername und Passwort befüllt sind."""
        self.btn_login.setEnabled(
            bool(self.txt_user.text().strip() and self.txt_pw.text()))

    def _attempt_login(self):
        """Versucht den Login mit den eingegebenen Credentials.

        Ablauf:
        1. Sicherheitsprüfung: Passwort == Benutzername → PW-Wechsel erzwingen.
        2. ``check_credentials()`` aufrufen (prüft Argon2-Hash + Active-Flag).
        3. Bei Erfolg: alle Benutzerinfos in ``app_meta.current_user`` schreiben.
        4. Draft-ExperimentRequests bereinigen.
        5. ``on_success()``-Callback aufrufen → Navigation zur App.
        6. Bei Fehler: Inaktiv-Prüfung für differenzierte Fehlermeldung.
        """
        if not self.btn_login.isEnabled():
            return
        user = self.txt_user.text().strip()
        pw = self.txt_pw.text()

        # Sicherheitsprüfung: Passwort darf nicht gleich dem Benutzernamen sein
        if user and pw and user.lower() == pw.lower():
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Insecure password")
            msg.setText("The password must not be the same as the username.")
            msg.setInformativeText("Please change your password now.")
            msg.addButton("OK", QMessageBox.AcceptRole)
            msg.exec()
            # Passwort-Änderungs-Screen direkt öffnen
            self.on_change_pw(user)
            return

        try:
            ok = check_credentials(user, pw)
        except Exception as e:
            show_error(self, "Connection error", "TrippleT could not connect to the database.", e)
            return

        if ok:
            # --- Benutzerinfos aus DB laden ---
            try:
                access_level = int(get_user_access_level(user) or 0)
            except Exception:
                access_level = 0

            print(f"Login successful for user: {user}", flush=True)
            print(f"AccessLevel: {access_level}", flush=True)

            try:
                access_right = get_user_access_right(user)   # Rollenname (z.B. "Admin")
            except Exception:
                access_right = None

            try:
                admin_box = bool(get_user_admin_box(user))    # tblUser.AdminBox
            except Exception:
                admin_box = False

            print(f"AccessRight: {access_right}", flush=True)

            uid = None
            if callable(get_user_id):
                try:
                    uid = get_user_id(user)
                except Exception:
                    uid = None

            try:
                first_name, last_name = get_user_first_last_name(user)
            except Exception:
                first_name, last_name = "", ""

            try:
                accent_colour = get_user_accent_colour(user)  # z.B. "#39a650"
            except Exception:
                accent_colour = None

            # --- Globalen Benutzerkontext setzen ---
            try:
                app_meta.current_user["id"] = uid
                app_meta.current_user["username"] = user
                app_meta.current_user["first_name"] = first_name
                app_meta.current_user["last_name"] = last_name
                app_meta.current_user["access_level"] = int(access_level or 0)
                app_meta.current_user["access_right"] = access_right
                app_meta.current_user["admin_box"] = admin_box
                app_meta.current_user["accent_colour"] = accent_colour
            except Exception:
                # Fallback: Dict neu erstellen falls es noch nicht initialisiert war
                app_meta.current_user = {
                    "id": uid,
                    "username": user,
                    "first_name": first_name,
                    "last_name": last_name,
                    "access_level": int(access_level or 0),
                    "access_right": access_right,
                    "admin_box": admin_box,
                    "accent_colour": accent_colour,
                }

            # --- Persoenliche Anzeige-Einstellungen (Settings -> Show Experiment tables) ---
            try:
                from ui import display_prefs
                display_prefs.load_for_current_user()
                from PySide6.QtCore import QTimer
                if display_prefs.app_scale_needs_restart():
                    # e.g. first login on this PC - after the login has finished
                    QTimer.singleShot(500, lambda: display_prefs.offer_restart(None))
                else:
                    # "What's new" once per release and user (ui/whats_new.py)
                    from ui.whats_new import show_if_unseen
                    QTimer.singleShot(800, lambda: show_if_unseen(self.window()))
            except Exception:
                pass

            # --- Nutzungs-Tracking (best-effort, siehe db/usage_log.py) ---
            from db.usage_log import log_usage_event
            log_usage_event("login", "login")

            # --- Draft-ExperimentRequests des Benutzers beim Login bereinigen ---
            # Verhindert, dass angefangene aber nie abgeschlossene Requests in der DB
            # verbleiben (Status = "Draft"). Fehler dürfen den Login nicht blockieren.
            try:
                cleanup_stats = cleanup_draft_experiment_requests(
                    created_by=uid,
                    created_by_username=user,
                )
                if cleanup_stats.get("requests_found"):
                    print(
                        f"Draft ExperimentRequests cleanup on login: {cleanup_stats}",
                        flush=True,
                    )
            except Exception as e:
                print(f"Draft ExperimentRequests cleanup failed: {e}", flush=True)

            # --- Athena Token-Reset on Login (monatlich) ---
            try:
                from db.connection import execute as db_execute, fetch_all as db_fetch
                import datetime
                reset_rows = db_fetch(
                    "SELECT tokens_reset FROM tblUser WHERE Username = %s",
                    [user],
                )
                do_reset = True
                if reset_rows and reset_rows[0].get("tokens_reset"):
                    last = reset_rows[0]["tokens_reset"]
                    if isinstance(last, str):
                        last = datetime.date.fromisoformat(last)
                    if last > datetime.date.today():
                        do_reset = False
                if do_reset:
                    db_execute(
                        "UPDATE tblUser SET tokens_used = 0, "
                        "tokens_reset = CURDATE() + INTERVAL 1 MONTH "
                        "WHERE Username = %s",
                        [user],
                    )
                    print(f"Athena token reset on login for: {user}", flush=True)
                else:
                    print(f"Athena token reset skipped (valid until {reset_rows[0]['tokens_reset']}) for: {user}", flush=True)
            except Exception as e:
                print(f"Athena token reset failed: {e}", flush=True)

            # Navigation zur App (kein Popup, direkt weiter)
            self.on_success(
                {
                    "id": uid,
                    "username": user,
                    "first_name": first_name,
                    "last_name": last_name,
                    "access_level": int(access_level or 0),
                    "access_right": access_right,
                    "admin_box": admin_box,
                    "accent_colour": accent_colour,
                }
            )
        else:
            # Differenzierte Fehlermeldung: Passwort korrekt, aber User inaktiv?
            try:
                if verify_user_password(user, pw) and not is_user_active(user):
                    m = QMessageBox(self)
                    m.setIcon(QMessageBox.Warning)
                    m.setWindowTitle("Login blocked")
                    m.setText("This user is inactive.")
                    m.setInformativeText(
                        "Please contact an administrator to activate your account.")
                    m.exec()
                    return
            except Exception:
                pass

            # Standard-Fehlermeldung
            m = QMessageBox(self)
            m.setIcon(QMessageBox.Warning)
            m.setWindowTitle("Login failed")
            m.setText("Username or password is incorrect.")
            m.setInformativeText("Please check your entries.")
            m.exec()

    def _open_change_pw_if_valid(self):
        """Öffnet den Passwort-Änderungs-Screen, falls ein gültiger Benutzername eingegeben wurde."""
        username = self.txt_user.text().strip()
        if not username or not user_exists(username):
            m = QMessageBox(self)
            m.setIcon(QMessageBox.Warning)
            m.setWindowTitle("No valid user")
            m.setText(
                "Please enter a valid user first in the field \u201cUser Name\u201d.")
            m.addButton("OK", QMessageBox.AcceptRole)
            m.exec()
            return
        self.on_change_pw(username)

    def reset_login_fields(self):
        """Leert Benutzername und Passwort und setzt den Fokus zurück auf das Benutzerfeld.

        Wird nach einem Logout aufgerufen, damit der nächste Benutzer nicht
        die Credentials des Vorgängers sieht.
        """
        try:
            self.txt_user.clear()
            self.txt_pw.clear()
        except Exception:
            pass
        try:
            self.txt_user.setFocus()
        except Exception:
            pass