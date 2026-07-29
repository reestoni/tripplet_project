# ui/screen_home.py
"""Home-Screen von TrippleT (Hauptnavigation nach dem Login).

Zeigt je nach Benutzerrolle unterschiedliche Karten an:
  - Alle Benutzer:    Experiment-Karte (Erstellen, Alle anzeigen)
  - AccessLevel >= 1: Experiment-Request-Karte mit Badge-Zähler
  - AdminBox:         Admin-Karte (Benutzer, Jets, Material usw.)
  - Superuser:        Superuser-Karte (erweiterte Funktionen)
  - Tools-Karte:      Canvas, Image Compare (immer sichtbar)

Willkommensnachricht: wird aus der DB geladen (tblSettings o.ä.) und kann
von Admins direkt im Home-Screen bearbeitet werden.

Badge-Zähler: zeigen die Anzahl offener/genehmigter Requests und Backlog-Items.
Akzentfarbe: kann der Benutzer im Home-Screen per Farbwähler setzen (wird in
  tblUser.AccentColour gespeichert und beim nächsten Login geladen).
"""

# ui/screen_home.py
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QSizePolicy, QSpacerItem, QGridLayout,
    QInputDialog, QLineEdit, QApplication, QColorDialog

)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QShortcut, QKeySequence, QIcon

from ui.widgets.header import HeaderBar
from ui.pathutil import resource_path
from ui.widgets.footer import FooterBar

from db.connection import get_connection, execute
import app_meta
from ui.theme import set_accent, build_qss, get_accent
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


class HomeScreen(QWidget):
    def __init__(self,
                 on_all_experiments,
                 on_create_experiment,
                 on_add_series,
                 on_add_trials,
                 on_create_experiment_legacy=None,
                 on_open_backlog=None,
                 on_open_experiment_request=None,
                 on_preview_requests=None, *,
                 access_level: int = 0, admin_box: bool = False, on_add_lab_machines=None,
                 on_add_yarn=None,
                 on_yarn_stock=None,
                 on_add_user=None,
                 on_add_jet=None,
                 on_add_top_plate=None,
                 on_manage_order_type=None,
                 on_manage_product_groups=None,
                 on_manage_material=None,
                 on_image_compare=None,
                 on_canvas=None,
                 on_smartchart=None,
                 on_search=None,
                 on_requirement_hub=None,
                 on_nozzle_calculator=None,
                 on_air_supply=None,
                 # Nur noch Logout-Callback (Button "Log Out" im Header)
                 on_logout=None):
        super().__init__()
        # Callbacks
        self.on_all_experiments = on_all_experiments
        self.on_create_experiment = on_create_experiment
        self.on_create_experiment_legacy = on_create_experiment_legacy
        self.on_add_series = on_add_series
        self.on_add_trials = on_add_trials
        self.on_open_backlog = on_open_backlog
        self.on_open_experiment_request = on_open_experiment_request
        self.on_preview_requests = on_preview_requests
        self.on_image_compare = on_image_compare
        self.on_canvas = on_canvas
        self.on_smartchart = on_smartchart
        self.on_search = on_search
        self.on_requirement_hub = on_requirement_hub
        self.on_nozzle_calculator = on_nozzle_calculator
        self.on_air_supply = on_air_supply

        try:
            self.access_level = int(access_level or 0)
        except Exception:
            self.access_level = 0

        # Zusätzliches Recht aus tblUser.AdminBox (unabhängig vom AccessLevel)
        self.admin_box = bool(admin_box)
        self.on_add_yarn = on_add_yarn
        self.on_yarn_stock = on_yarn_stock
        self.on_add_user = on_add_user
        self.on_add_jet = on_add_jet
        self.on_add_top_plate = on_add_top_plate
        self.on_manage_order_type = on_manage_order_type
        self.on_manage_product_groups = on_manage_product_groups
        self.on_manage_material = on_manage_material
        self.on_add_lab_machines = on_add_lab_machines

        self._on_logout = on_logout

        self._build_ui()
        self._wire_shortcuts()

        # Flag to ensure refresh only runs after UI exists.
        self._did_build = True


    def hideEvent(self, event):
        """Entfernt Athena beim Screen-Wechsel — wird beim nächsten Besuch neu gewürfelt."""
        super().hideEvent(event)
        try:
            if hasattr(self, "_home_athena") and self._home_athena is not None:
                if getattr(self._home_athena, "_working", False):
                    self._home_athena.stop_working()
                self._home_athena.deleteLater()
                self._home_athena = None
        except Exception:
            pass

    def showEvent(self, event):
        """Aktualisiert Badges und Willkommensnachricht bei jedem Öffnen des Screens."""
        """Called whenever Home becomes visible (e.g. returning from another screen).

        Superuser: refresh the Experiment Request badge (open requests with
        RequestStatus=1).
        """
        try:
            super().showEvent(event)
        except Exception:
            pass

        # Always hide Legacy Import button when arriving on Home.
        try:
            if hasattr(self, "_btn_legacy_create"):
                self._btn_legacy_create.hide()
        except Exception:
            pass

        # Only refresh after UI is built.
        if getattr(self, "_did_build", False):
            try:
                self._refresh_experiment_request_badge()
                self._refresh_approved_experiment_request_badge()
                self._refresh_welcome_message()
                self._refresh_backlog_badge()
            except Exception:
                pass

            # 5% Chance: Athena schläft still im rechten unteren Eck
            try:
                import random as _random
                if _ATHENA_AVAILABLE and _random.random() < 0.05:
                    self._spawn_sleeping_athena()
            except Exception:
                pass

    # ---------- Helpers ----------
    def _format_welcome_text(self, welcome_message, first_name: str) -> str:
        """Ersetzt den Platzhalter {name} in der Willkommensnachricht durch den Vornamen."""
        msg = (welcome_message or "").strip()
        fn = (first_name or "").strip()
        if not fn:
            fn = ""
        if msg:
            return f"{msg}, {fn}".strip().strip(",")
        return f"Welcome, {fn}".strip()

    def _fetch_welcome_message_from_db(self):
        """Lädt die Willkommensnachricht aus der DB (tblSettings oder Fallback-Text)."""
        """Return WelcomeMessage for current user (None if missing)."""
        try:
            user_id = app_meta.current_user.get("id")
        except Exception:
            user_id = None
        if not user_id:
            return None
        try:
            with get_connection() as cn:
                cur = cn.cursor()
                cur.execute("SELECT [WelcomeMessage] FROM [tblUser] WHERE [ID] = ?", [user_id])
                row = cur.fetchone()
            return row[0] if row else None
        except Exception:
            return None

    def _refresh_welcome_message(self):
        """Aktualisiert das Willkommens-Label mit dem aktuellen Benutzer und der DB-Nachricht."""
        """Reload welcome message from DB and update label."""
        try:
            first_name = app_meta.current_user.get("first_name") or ""
        except Exception:
            first_name = ""
        welcome_message = self._fetch_welcome_message_from_db()
        self._welcome_message_raw = welcome_message
        try:
            if hasattr(self, "_welcome_label"):
                self._welcome_label.setText(self._format_welcome_text(welcome_message, first_name))
        except Exception:
            pass

    def _edit_welcome_message(self):
        """Öffnet einen Dialog zum Bearbeiten der Willkommensnachricht (nur für Admins).

        Speichert den neuen Text in der DB und aktualisiert die Anzeige.
        """
        """Open small popup to edit WelcomeMessage (max 45 chars)."""
        try:
            current = (self._welcome_message_raw or "").strip()
        except Exception:
            current = ""

        dlg = QInputDialog(self)
        dlg.setWindowTitle("Welcome Message")
        dlg.setLabelText("Neue Welcome Message (max. 45 Zeichen):")
        dlg.setTextValue(current)
        dlg.setTextEchoMode(QLineEdit.EchoMode.Normal)

        # set max length on internal line edit
        le = dlg.findChild(QLineEdit)
        if le is not None:
            le.setMaxLength(45)

        if dlg.exec() != QInputDialog.DialogCode.Accepted:
            return

        value = (dlg.textValue() or "").strip()
        if len(value) > 45:
            value = value[:45]

        # Empty → store NULL (so default 'Welcome, FirstName' applies)
        if value == "":
            value_db = None
        else:
            value_db = value

        try:
            user_id = app_meta.current_user.get("id")
        except Exception:
            user_id = None
        if not user_id:
            return

        try:
            if value_db is None:
                execute("UPDATE [tblUser] SET [WelcomeMessage] = NULL WHERE [ID] = ?", [user_id])
            else:
                execute("UPDATE [tblUser] SET [WelcomeMessage] = ? WHERE [ID] = ?", [value_db, user_id])
        except Exception:
            # keep UI usable even if save fails
            return

        # Refresh label immediately
        self._refresh_welcome_message()




    def _pick_accent_colour(self):
        """Öffnet einen QColorDialog zur Auswahl der persönlichen Akzentfarbe.

        Speichert die Farbe in tblUser.AccentColour und setzt das QSS neu.
        """
        """Öffnet QColorDialog, speichert AccentColour in tblUser und wendet sie sofort an."""
        try:
            from PySide6.QtGui import QColor
            current = QColor(get_accent())
            colour = QColorDialog.getColor(current, self, "Choose accent colour")
            if not colour.isValid():
                return
            hex_val = colour.name()  # z.B. '#8a2be2'
            # In DB speichern
            uid = app_meta.current_user.get("id")
            username = app_meta.current_user.get("username")
            if username:
                try:
                    with get_connection() as cn:
                        cur = cn.cursor()
                        cur.execute(
                            "UPDATE tblUser SET [AccentColour]=? WHERE [Username]=?",
                            (hex_val, username),
                        )
                        cn.commit()
                except Exception:
                    pass
            # In app_meta speichern
            app_meta.current_user["accent_colour"] = hex_val
            # Theme sofort anwenden
            set_accent(hex_val)
            QApplication.instance().setStyleSheet(build_qss())
        except Exception:
            pass


    def eventFilter(self, obj, event):
        """Fängt Doppelklick auf den Willkommenstext ab (→ Bearbeitungs-Dialog für Admins)."""
        """
        Easter egg (hidden):
        - Only on RIGHT-CLICK on title "Experiments" a password prompt appears.
        - No special hover cursor (keep default arrow cursor).
        """
        # --- Welcome label hover + click (edit WelcomeMessage) ---
        if hasattr(self, "_welcome_label") and obj is self._welcome_label:
            try:
                et = event.type()
            except Exception:
                et = None

            # Hover → hand cursor
            if et == event.Type.Enter:
                try:
                    self._welcome_label.setCursor(Qt.PointingHandCursor)
                except Exception:
                    pass
                return False
            if et == event.Type.Leave:
                try:
                    self._welcome_label.setCursor(Qt.ArrowCursor)
                except Exception:
                    pass
                return False

            # Click → edit popup
            if et == event.Type.MouseButtonPress:
                try:
                    btn = event.button()
                except Exception:
                    btn = None
                if btn == Qt.LeftButton:
                    self._edit_welcome_message()
                    return True
            return False

        if hasattr(self, "_exp_title_label") and obj is self._exp_title_label:
            # Only react to right-click
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
                    try:
                        pwd, ok = QInputDialog.getText(
                            self,
                            "Passwort",
                            "Passwort eingeben:",
                            QLineEdit.EchoMode.Password
                        )
                    except Exception:
                        # Fallback if Qt enum differs
                        pwd, ok = QInputDialog.getText(self, "Passwort", "Passwort eingeben:")

                    if ok and isinstance(pwd, str):
                        pwd_lower = pwd.strip().lower()
                        if pwd_lower == "still game" and _SNAKE_AVAILABLE:
                            try:
                                _SnakeDialog.open_or_raise(parent=self)
                            except Exception:
                                pass
                        elif pwd_lower == "fly athena" and _ATHENA_AVAILABLE:
                            try:
                                self._launch_athena()
                            except Exception:
                                pass
                        elif pwd_lower == "ynwa":
                            try:
                                # Resolve icon path robustly (case-insensitive on Linux/macOS FS)
                                icon_path = self._asset_path("lfc.ico")
                                if not icon_path.exists():
                                    img_dir = icon_path.parent
                                    try:
                                        matches = [p for p in img_dir.glob("*.ico") if p.name.lower() == "lfc.ico"]
                                        if matches:
                                            icon_path = matches[0]
                                    except Exception:
                                        pass

                                if icon_path.exists():
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

                    # Consume ONLY the right-click on the label (keeps it secret)
                    return True

                # Any other mouse button: do not consume (no secret action)
                return False

        return super().eventFilter(obj, event)
    def _asset_path(self, filename: str) -> Path:
        """Gibt den absoluten Pfad zu einer Asset-Datei zurück."""
        project_root = Path(__file__).resolve().parents[1]
        return project_root / "assets" / "images" / filename

    def _icon_label(self, filename: str, size: int = 18) -> QLabel:
        """Erstellt ein QLabel mit skaliertem Icon."""
        lbl = QLabel()
        pm = QPixmap(str(self._asset_path(filename)))
        if not pm.isNull():
            pm = pm.scaled(size, size, Qt.KeepAspectRatio,
                           Qt.SmoothTransformation)
            lbl.setScaledContents(False)
            lbl.setPixmap(pm)
            right_margin = 6
            lbl.setFixedHeight(size)
            lbl.setFixedWidth(size + right_margin)
        lbl.setContentsMargins(0, 0, right_margin, 0)
        return lbl

    def _icon_btn(self, text: str, icon_file: str, style: str, on_click=None) -> QPushButton:
        """Erstellt einen QPushButton mit Icon. Wenn on_click=None, wird er deaktiviert."""
        """
        Erzeugt einen Button mit Icon (links) + Text (rechts).
        Falls das Icon nicht gefunden wird, bleibt es einfach ein Text-Button.
        """
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

    def _make_green_btn(self, text: str, on_click=None):
        """Erstellt einen Standard-GreenBtn (Stil aus theme.py)."""
        btn = QPushButton(text)
        btn.setObjectName("GreenBtn")
        if callable(on_click):
            btn.clicked.connect(lambda *_: on_click())
        else:
            btn.setEnabled(False)
        return btn


    def _get_open_experiment_request_count(self) -> int:
        """Zählt offene ExperimentRequests des aktuellen Benutzers für den Badge."""
        """Counts open Experiment Requests (RequestStatus = 1).

        Only used for the Superuser badge on Home.
        Returns 0 on any error to keep Home usable even if DB is down.
        """
        try:
            with get_connection() as cn:
                cur = cn.cursor()
                cur.execute(
                    "SELECT COUNT(*) FROM [tblExperimentRequests] WHERE [RequestStatus] = 1"
                )
                row = cur.fetchone()
            try:
                return int(row[0] or 0) if row else 0
            except Exception:
                return 0
        except Exception:
            return 0
    def _get_approved_experiment_request_count(self) -> int:
        """Zählt genehmigte ExperimentRequests des aktuellen Benutzers für den Badge."""
        """Counts approved Experiment Requests (RequestStatus = 3).

        Used for the badge on "Create New Experiment" on Home.
        Returns 0 on any error to keep Home usable even if DB is down.
        """
        try:
            with get_connection() as cn:
                cur = cn.cursor()
                cur.execute(
                    "SELECT COUNT(*) FROM [tblExperimentRequests] WHERE [RequestStatus] = 3"
                )
                row = cur.fetchone()
            try:
                return int(row[0] or 0) if row else 0
            except Exception:
                return 0
        except Exception:
            return 0

    def _get_backlog_count(self) -> int:
        """Zählt offene Backlog-Einträge für den Badge."""
        """Counts TrialSeries items that are currently in Backlog (BacklogStatus = 'Backlog').

        Used for the badge on the 'Backlog' button on Home.
        Returns 0 on any error to keep Home usable even if DB is down.
        """
        try:
            with get_connection() as cn:
                cur = cn.cursor()
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM (tblTrialSeries AS s
                          INNER JOIN tblBacklogStatus AS bs
                            ON bs.[ID] = s.[BacklogStatusID])
                    WHERE bs.[BacklogStatus] = 'Backlog'
                    """
                )
                row = cur.fetchone()
            try:
                return int(row[0] or 0) if row else 0
            except Exception:
                return 0
        except Exception:
            return 0


    def _refresh_backlog_badge(self):
        """Aktualisiert den Backlog-Badge mit der aktuellen Anzahl offener Einträge."""
        """Refresh the Backlog badge (AccessLevel >= 2)."""
        if self.access_level < 2:
            return
        badge = getattr(self, "_backlog_badge", None)
        if badge is None:
            return

        cnt = self._get_backlog_count()
        badge.setVisible(cnt > 0)
        badge.setText("9+" if cnt > 9 else str(cnt))

        try:
            badge.adjustSize()
            w = max(18, badge.sizeHint().width())
            badge.setFixedSize(w, 18)
        except Exception:
            pass



    def _refresh_approved_experiment_request_badge(self):
        """Aktualisiert den Badge für genehmigte Requests."""
        """Refresh the approved Experiment Request badge on Create Experiment."""
        badge = getattr(self, "_approved_exp_req_badge", None)
        if badge is None:
            return

        cnt = self._get_approved_experiment_request_count()
        badge.setVisible(cnt > 0)
        badge.setText("9+" if cnt > 9 else str(cnt))

        try:
            badge.adjustSize()
            w = max(18, badge.sizeHint().width())
            badge.setFixedSize(w, 18)
        except Exception:
            pass



    def _wrap_button_with_badge(self, btn: QPushButton, count: int):
        """Umhüllt einen Button mit einem roten Badge-Kreis wenn count > 0.

        Returns:
            QWidget-Container mit Button + optionalem Badge.
        """
        """Wraps a QPushButton with a WhatsApp-style badge (top-right).

        Implementation note:
        We use a simple QGridLayout overlay instead of a stacked layout, because
        stacked layouts force all children to the same geometry and can trigger
        "Unable to set geometry" warnings on some setups.
        """
        container = QWidget()
        container.setContentsMargins(0, 0, 0, 0)

        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)

        # Base button
        grid.addWidget(btn, 0, 0)

        # Badge label (parented to container from the start)
        badge = QLabel(container)
        badge.setAlignment(Qt.AlignCenter)
        badge.setVisible(count > 0)
        badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        # For big numbers, show 9+ (common UX)
        badge_text = "9+" if count > 9 else str(count)
        badge.setText(badge_text)

        # WhatsApp-like badge: red dot + white bold number
        badge.setStyleSheet(
            """
            QLabel {
                background: #e53935;
                color: white;
                border-radius: 9px;
                padding-left: 4px;
                padding-right: 4px;
                font-size: 10px;
                font-weight: 700;
            }
            """
        )

        # Keep size stable and avoid tiny/invalid geometries on HiDPI screens
        badge.adjustSize()
        w = max(18, badge.sizeHint().width())
        badge.setFixedSize(w, 18)

        # Overlay badge in the top-right corner
        grid.addWidget(badge, 0, 0, alignment=Qt.AlignTop | Qt.AlignRight)

        return container, badge


    def _refresh_experiment_request_badge(self):
        """Aktualisiert den Badge für offene ExperimentRequests."""
        """Refresh the open Experiment Request badge (Superuser only)."""
        if self.access_level < 4:
            return
        badge = getattr(self, "_exp_req_badge", None)
        if badge is None:
            return

        cnt = self._get_open_experiment_request_count()
        badge.setVisible(cnt > 0)
        badge.setText("9+" if cnt > 9 else str(cnt))

        # Keep geometry stable when the text width changes.
        try:
            badge.adjustSize()
            w = max(18, badge.sizeHint().width())
            badge.setFixedSize(w, 18)
        except Exception:
            pass


    def _build_ui(self):
        """Erstellt das vollständige Home-Layout: Header, Willkommen, Karten je nach Rolle, Footer."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header mit "Log Out"-Button
        self._header = HeaderBar(
            title="Home",
            show_home=False,
            on_logout=(self._on_logout if callable(self._on_logout) else None),
        )
        header = self._header
        if callable(self.on_search):
            header.connect_search(self.on_search)

        # Farbwähler-Button: kleines Farbkreis-Icon im Header-Bereich
        self._btn_accent = QPushButton("", objectName="HomeBtn")
        self._btn_accent.setToolTip("Change my accent colour")
        self._btn_accent.setCursor(Qt.PointingHandCursor)
        self._btn_accent.setFixedSize(36, 36)
        try:
            _accent_icon = QIcon(resource_path("assets/images/user_white.png"))
            if not _accent_icon.isNull():
                self._btn_accent.setIcon(_accent_icon)
                self._btn_accent.setIconSize(QSize(22, 22))
        except Exception:
            self._btn_accent.setText("👤")
        self._btn_accent.clicked.connect(self._pick_accent_colour)
        # Button in den Header-Layout einfügen (vor dem Heberlein-Logo)
        try:
            hlay = header.layout()
            # Vorletztes Widget ist das Heberlein-Logo → davor einfügen
            hlay.insertWidget(hlay.count() - 1, self._btn_accent, 0, Qt.AlignRight | Qt.AlignVCenter)
            hlay.insertSpacing(hlay.count() - 1, 8)
        except Exception:
            pass

        root.addWidget(header)

        # Fixed-height Welcome line (keeps all boxes exactly where they are)
        self._welcome_wrapper = QFrame()
        self._welcome_wrapper.setFixedHeight(48)
        self._welcome_wrapper.setMaximumWidth(800)
        self._welcome_wrapper.setMinimumWidth(700)
        wlay = QVBoxLayout(self._welcome_wrapper)
        wlay.setContentsMargins(12, 0, 12, 0)
        wlay.setSpacing(0)

        self._welcome_label = QLabel("")
        self._welcome_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self._welcome_label.setStyleSheet(
            "color: black; font-size: 30px; font-weight: bold;"
        )
        self._welcome_label.installEventFilter(self)
        wlay.addWidget(self._welcome_label, 1)

        root.addWidget(self._welcome_wrapper, 0, Qt.AlignHCenter)

        # Load and display welcome text
        self._refresh_welcome_message()


        # --- Center Wrapper ---
        center = QFrame()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 24, 0, 0)
        center_layout.setSpacing(16)

        # 1) Experiments-Card
        experiments_card = QFrame(objectName="Card")
        experiments_card.setMaximumWidth(800)
        experiments_card.setMinimumWidth(700)

        exp_layout = QVBoxLayout(experiments_card)
        exp_layout.setContentsMargins(0, 0, 0, 0)
        exp_layout.setSpacing(0)

        exp_header = QFrame(objectName="CardHeader")
        exp_hdr_layout = QHBoxLayout(exp_header)
        exp_hdr_layout.setContentsMargins(12, 4, 12, 4)
        exp_hdr_layout.setSpacing(8)
                # Header icon (default) + Easter-egg icon (LFC)
        self._exp_icon_default = self._icon_label("experiment_white.png", 24)
        self._exp_icon_lfc = self._icon_label("lfc.ico", 24)
        self._exp_icon_lfc.hide()
        exp_hdr_layout.addWidget(self._exp_icon_default, 0, Qt.AlignVCenter)
        exp_hdr_layout.addWidget(self._exp_icon_lfc, 0, Qt.AlignVCenter)
        self._exp_title_label = QLabel("Experiments")
        self._exp_title_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        self._exp_title_label.installEventFilter(self)

        exp_hdr_layout.addWidget(self._exp_title_label, 0, Qt.AlignVCenter)
        exp_layout.addWidget(exp_header)

        exp_body = QFrame()
        exp_body.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        exp_body_layout = QHBoxLayout(exp_body)
        exp_body_layout.setContentsMargins(24, 16, 24, 16)
        exp_body_layout.setSpacing(20)

        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        # >>> ICON+TEXT Buttons (links: Übersicht)
        btn_show = self._icon_btn(
            "Show All Experiments", "show.png", "GreenBtn", self.on_all_experiments)
        left_col.addWidget(btn_show)

        # Neuer Backlog-Button
        btn_backlog = self._icon_btn(
            "Backlog", "backlog.png", "GreenBtn", self.on_open_backlog
        )
        # Backlog erst ab AccessLevel 2 sichtbar
        btn_backlog.setVisible(self.access_level >= 2)

        # Badge auf Backlog (wie WhatsApp): Anzahl Items mit Status "Backlog"
        if self.access_level >= 2:
            try:
                cnt = self._get_backlog_count()
            except Exception:
                cnt = 0
            try:
                wrapped, badge = self._wrap_button_with_badge(btn_backlog, cnt)
                self._backlog_badge = badge
                left_col.addWidget(wrapped)
            except Exception:
                left_col.addWidget(btn_backlog)
        else:
            left_col.addWidget(btn_backlog)

        # Neuer Button: Experiment Request
        # Soll für alle Benutzergruppen sichtbar und benutzbar sein.
        btn_experiment_request = self._icon_btn(
            "Experiment Request", "experiment_request.png", "GreenBtn", self.on_open_experiment_request
        )
        btn_experiment_request.setVisible(True)

        # Superuser: WhatsApp-style Badge (weisse Zahl auf rotem Punkt)
        # Nur sichtbar, wenn es offene Requests (RequestStatus=1) gibt.
        if self.access_level >= 4:
            cnt = self._get_open_experiment_request_count()
            wrapped, badge = self._wrap_button_with_badge(btn_experiment_request, cnt)
            self._exp_req_badge = badge
            left_col.addWidget(wrapped)
        else:
            left_col.addWidget(btn_experiment_request)
        left_col.addStretch()



        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        # >>> ICON+TEXT Buttons (rechts: Aktionen)
        btn_create = self._icon_btn(
            "Create New Experiment", "create.png", "PurpleBtn", self.on_create_experiment)
        # Hidden: Legacy import (manual Experiment ID). Visible only after Ctrl+Shift+J.
        self._btn_legacy_create = self._icon_btn(
            "Legacy Import (Manual ID)", "legacy.png", "PurpleBtn", self._on_legacy_create_clicked)
        self._btn_legacy_create.hide()
        btn_add_series = self._icon_btn(
            "Add Trial Series to Experiment", "series.png", "PurpleBtn", self.on_add_series)

        # Violette Buttons erst ab AccessLevel 2 sichtbar
        can_see_purple = self.access_level >= 2
        for _b in (btn_create, btn_add_series):
            _b.setVisible(can_see_purple)

        # Badge on "Create New Experiment" for approved requests (RequestStatus=3)
        try:
            cnt = self._get_approved_experiment_request_count()
        except Exception:
            cnt = 0
        try:
            wrapped, badge = self._wrap_button_with_badge(btn_create, cnt)
            self._approved_exp_req_badge = badge
            # Only this badge opens the preview dialog
            badge.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            badge.setCursor(Qt.PointingHandCursor)
            badge.setToolTip("View pending experiment requests")
            if callable(self.on_preview_requests):
                badge.mousePressEvent = lambda _e: self.on_preview_requests()
            right_col.addWidget(wrapped)
            right_col.addWidget(self._btn_legacy_create)
        except Exception:
            right_col.addWidget(btn_create)
            right_col.addWidget(self._btn_legacy_create)
        right_col.addWidget(btn_add_series)

        btn_lab_machines = self._icon_btn("Add Lab Machines to Trials", "lab.png", "PurpleBtn",
                                          self.on_add_lab_machines if callable(self.on_add_lab_machines) else None)
        btn_lab_machines.setVisible(can_see_purple)
        right_col.addWidget(btn_lab_machines)
        right_col.addStretch()


        exp_body_layout.addLayout(left_col, 1)
        exp_body_layout.addLayout(right_col, 1)
        exp_layout.addWidget(exp_body)

        # Top row: Experiments (left) + Tools (right) side by side, centered as a unit
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.addStretch()
        _card_h = 230
        experiments_card.setFixedHeight(_card_h)
        tools_card = self._build_tools_card()
        tools_card.setFixedHeight(_card_h)
        top_row.addWidget(experiments_card, 0, Qt.AlignTop)
        top_row.addWidget(tools_card, 0, Qt.AlignTop)
        top_row.addStretch()
        center_layout.addLayout(top_row)

        # 2) Optional: Admin-Card
        can_admin = (self.access_level >= 3) or self.admin_box
        if can_admin:
            center_layout.addSpacing(8)
            admin_card = self._build_admin_card()
            center_layout.addWidget(
                admin_card, 0, Qt.AlignHCenter | Qt.AlignTop)

            center_layout.addSpacing(8)

        # 3) Optional: Superuser-Card
        if self.access_level >= 4:
            center_layout.addSpacing(8)
            superuser_card = self._build_superuser_card()
            center_layout.addWidget(
                superuser_card, 0, Qt.AlignHCenter | Qt.AlignTop)
        root.addWidget(center, 1)
        root.addWidget(FooterBar())



    def _toggle_legacy_button(self):
        """Zeigt/versteckt den Legacy-Experiment-Erstellen-Button (für Admins)."""
        try:
            btn = getattr(self, "_btn_legacy_create", None)
            if btn is None:
                return
            btn.setVisible(not btn.isVisible())
        except Exception:
            pass

    def _on_legacy_create_clicked(self):
        """Öffnet den alten Experiment-Erstellen-Screen (Legacy-Pfad)."""
        # Hide again immediately (keeps it "invisible" for normal users).
        try:
            if hasattr(self, "_btn_legacy_create"):
                self._btn_legacy_create.hide()
        except Exception:
            pass
        cb = getattr(self, "on_create_experiment_legacy", None)
        if callable(cb):
            cb()

    def _spawn_sleeping_athena(self):
        """5%-Easter-Egg: still schlafende Athena unten rechts."""
        if not _ATHENA_AVAILABLE:
            return
        try:
            if hasattr(self, "_home_athena") and self._home_athena is not None:
                return
            self._home_athena = _AthenaOwl(self)
            self._home_athena.place_sleeping()
            self._home_athena.raise_()
            self._home_athena.show()
        except Exception:
            pass

    def _launch_athena(self):
        """Startet die Athena-Eule im Demo-Modus über den Home-Screen."""
        if not _ATHENA_AVAILABLE:
            return
        try:
            if hasattr(self, "_home_athena") and self._home_athena is not None:
                if getattr(self._home_athena, "_working", False):
                    # Läuft bereits → stoppen (Toggle)
                    self._home_athena.stop_working()
                    return
                else:
                    # Schlafende Easter-Egg-Eule → zuerst entfernen
                    self._home_athena.deleteLater()
                    self._home_athena = None

            # Neu erstellen
            self._home_athena = _AthenaOwl(self)
            self._home_athena.place_sleeping()
            self._home_athena.raise_()
            self._home_athena.show()
            self._home_athena.start_demo()
        except Exception:
            pass

    def _wire_shortcuts(self):
        """Registriert Tastatur-Shortcuts (z.B. Ctrl+F für Quick-Search)."""
        # Ctrl+L als Logout im Home-Screen
        if callable(self._on_logout):
            self._sc_logout = QShortcut(QKeySequence("Ctrl+L"), self)
            self._sc_logout.activated.connect(self._on_logout)

        # Ctrl+Shift+J: reveal hidden Legacy Import button (manual Experiment ID)
        self._sc_legacy = QShortcut(QKeySequence("Ctrl+Shift+J"), self)
        self._sc_legacy.activated.connect(self._toggle_legacy_button)

    def _build_superuser_card(self) -> QFrame:
        """Erstellt die Superuser-Karte mit erweiterten Admin-Funktionen."""
        card = QFrame(objectName="Card")
        card.setMaximumWidth(800)
        card.setMinimumWidth(700)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame(objectName="CardHeader")
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(12, 4, 12, 4)
        hdr_layout.setSpacing(8)
        # Falls kein separates Superuser-Icon existiert, verwenden wir das Admin-Icon.
        hdr_layout.addWidget(self._icon_label(
            "superuser.png", 24), 0, Qt.AlignVCenter)
        title = QLabel("Superuser")
        title.setStyleSheet(
            "color: white; font-weight: bold; font-size: 14px;")
        hdr_layout.addWidget(title, 0, Qt.AlignVCenter)
        layout.addWidget(header)

        body = QFrame()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 16, 24, 16)
        body_layout.setSpacing(12)

        row1 = QHBoxLayout()
        row1.setSpacing(20)

        btn_manage_user = self._make_green_btn("Manage User", self.on_add_user)
        btn_manage_user.setFixedWidth(180)
        btn_manage_user.setMinimumHeight(34)
        row1.addWidget(btn_manage_user)

        # Spacer rechts, damit die Box "analog" aussieht, auch wenn nur ein Button drin ist
        row1.addSpacerItem(QSpacerItem(
            20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        body_layout.addLayout(row1)
        layout.addWidget(body)

        return card

    def _build_tools_card(self) -> QFrame:
        """Erstellt die Tools-Karte (Canvas, Image Compare usw.)."""
        card = QFrame(objectName="Card")
        card.setMaximumWidth(800)
        card.setMinimumWidth(700)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame(objectName="CardHeader")
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(12, 4, 12, 4)
        hdr_layout.setSpacing(8)
        hdr_layout.addWidget(self._icon_label("tools.png", 24), 0, Qt.AlignVCenter)
        title = QLabel("Tools")
        title.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        hdr_layout.addWidget(title, 0, Qt.AlignVCenter)
        layout.addWidget(header)

        body = QFrame()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 16, 24, 16)
        body_layout.setSpacing(12)

        # Zeile 1: Image Compare | Canvas
        row1 = QHBoxLayout()
        row1.setSpacing(20)
        row1.addWidget(self._icon_btn(
            "Image Compare", "image_compare.png", "GreenBtn", self.on_image_compare), 1)
        row1.addWidget(self._icon_btn(
            "Canvas", "canvas.png", "GreenBtn", self.on_canvas), 1)
        body_layout.addLayout(row1)

        # Zeile 2: Jet ROI Calculator | Air Supply Network
        row2 = QHBoxLayout()
        row2.setSpacing(20)
        row2.addWidget(self._icon_btn(
            "Jet ROI Calculator", "nozzle_calculator.png", "GreenBtn",
            self.on_nozzle_calculator if callable(getattr(self, "on_nozzle_calculator", None)) else None), 1)
        row2.addWidget(self._icon_btn(
            "Air Supply Network", "air_supply.png", "GreenBtn",
            self.on_air_supply if callable(getattr(self, "on_air_supply", None)) else None), 1)
        body_layout.addLayout(row2)

        # Zeile 3: Requirement Hub | Smart Chart (access_level >= 3)
        _rh_visible = self.access_level >= 3
        _sc_visible = self.access_level >= 3
        if _rh_visible or _sc_visible:
            row3 = QHBoxLayout()
            row3.setSpacing(20)
            if _rh_visible:
                row3.addWidget(self._icon_btn(
                    "Requirement Hub", "requirement_hub.png", "GreenBtn",
                    self.on_requirement_hub), 1)
            else:
                row3.addWidget(QFrame(), 1)
            if _sc_visible:
                row3.addWidget(self._icon_btn(
                    "Smart Chart", "analytics.png", "GreenBtn",
                    self.on_smartchart), 1)
            else:
                row3.addWidget(QFrame(), 1)
            body_layout.addLayout(row3)

        # Zeile 4: Yarn Stock
        row4 = QHBoxLayout()
        row4.setSpacing(20)
        row4.addWidget(self._icon_btn(
            "Yarn Stock", "manage_yarn.png", "GreenBtn",
            self.on_yarn_stock if callable(getattr(self, "on_yarn_stock", None)) else None), 1)
        row4.addWidget(QFrame(), 1)
        body_layout.addLayout(row4)

        body_layout.addStretch()


        layout.addWidget(body)

        return card

    def _build_admin_card(self) -> QFrame:
        """Erstellt die Admin-Karte (Benutzer-, Jets-, Material-Verwaltung usw.)."""
        card = QFrame(objectName="Card")
        card.setMaximumWidth(800)
        card.setMinimumWidth(700)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame(objectName="CardHeader")
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(12, 4, 12, 4)
        hdr_layout.setSpacing(8)
        hdr_layout.addWidget(self._icon_label(
            "admin_white.png", 24), 0, Qt.AlignVCenter)
        title = QLabel("Admin")
        title.setStyleSheet(
            "color: white; font-weight: bold; font-size: 14px;")
        hdr_layout.addWidget(title, 0, Qt.AlignVCenter)
        layout.addWidget(header)

        body = QFrame()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 16, 24, 16)
        body_layout.setSpacing(12)

        row1 = QHBoxLayout()
        row1.setSpacing(20)
        btn_manage_jets = self._make_green_btn("Manage Jets", self.on_add_jet)
        btn_manage_top_plates = self._make_green_btn(
            "Manage Top Plates", self.on_add_top_plate)
        btn_add_yarn = self._make_green_btn("Manage Yarn", self.on_add_yarn)
        for b in (btn_manage_jets, btn_manage_top_plates, btn_add_yarn):
            b.setFixedWidth(180)
            b.setMinimumHeight(34)
            row1.addWidget(b)

        row2 = QHBoxLayout()
        row2.setSpacing(20)
        btn_order_type = self._make_green_btn(
            "Manage Order Type", self.on_manage_order_type)
        btn_product_groups = self._make_green_btn(
            "Manage Product Groups", self.on_manage_product_groups)
        btn_material = self._make_green_btn(
            "Manage Material", self.on_manage_material)
        for b in (btn_order_type, btn_product_groups, btn_material):
            b.setFixedWidth(180)
            b.setMinimumHeight(34)
            row2.addWidget(b)

        body_layout.addLayout(row1)
        body_layout.addLayout(row2)
        layout.addWidget(body)

        return card