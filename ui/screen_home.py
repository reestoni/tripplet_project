# ui/screen_home.py
"""Home-Screen von TrippleT (Hauptnavigation nach dem Login).

Zeigt je nach Benutzerrolle unterschiedliche Karten an:
  - Alle Benutzer:    Experiment-Karte (Erstellen, Alle anzeigen)
  - AccessLevel >= 1: Experiment-Request-Karte mit Badge-Zähler
  - Alle Benutzer:    Admin-Karte (Jets, Yarn, Top Plates, Order Type, Product
                       Groups, Material) – sichtbar für alle, aber nur AccessLevel
                       >= 3 ODER AdminBox=1 haben dort Schreibrechte; alle anderen
                       sehen dieselben Screens read-only (siehe app_meta.can_use_admin_box()
                       und die set_read_only()-Aufrufe in main.py bei jeder Navigation dorthin)
  - Superuser:        Superuser-Karte (erweiterte Funktionen)
  - Tools-Karte:      Canvas, Image Compare (immer sichtbar)

Willkommensnachricht: wird aus der DB geladen (tblSettings o.ä.) und kann
von Admins direkt im Home-Screen bearbeitet werden.

Badge-Zähler: zeigen die Anzahl offener/genehmigter Requests und Backlog-Items.
Akzentfarbe: kann der Benutzer im Home-Screen per Farbwähler setzen (wird in
  tblUser.AccentColour gespeichert und beim nächsten Login geladen).
"""

# ui/screen_home.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSizePolicy, QSpacerItem, QGridLayout,
    QInputDialog, QLineEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence

from ui.widgets.sidebar import SidebarPanel
from ui.widgets import sidebar_nav
from ui.widgets.footer import FooterBar

from db.connection import get_connection, execute
import app_meta
# Die geheimen Rechtsklick-Ostereier (Snake/Athena/LFC) sowie das
# 5%-Zufalls-Athena-Ei sind 2026-08-27 aus Home ausgezogen (Nutzerwunsch:
# "da wir nun quasi home 'abgeschossen' haben, müssen wir die sonst wo
# verstecken") - Snake/Athena/LFC leben jetzt im Rechtsklick auf den
# Benutzernamen in ui/widgets/footer.py (app-weit, da FooterBar überall
# eingebunden ist), das Zufalls-Ei in ui/screen_backlog.py (neuer
# Post-Login-Landing-Screen).


class HomeScreen(QWidget):
    def __init__(self,
                 on_all_experiments,
                 on_create_experiment,
                 on_add_series,
                 on_add_trials,
                 on_create_experiment_legacy=None,
                 on_open_backlog=None,
                 on_open_experiment_request=None,
                 on_create_experiment_request=None,
                 on_open_my_requests=None,
                 on_preview_requests=None,
                 on_preview_open_requests=None, *,
                 access_level: int = 0, admin_box: bool = False, on_add_lab_machines=None,
                 on_add_yarn=None,
                 on_yarn_stock=None,
                 on_add_user=None,
                 on_add_jet=None,
                 on_add_top_plate=None,
                 on_manage_order_type=None,
                 on_manage_product_groups=None,
                 on_manage_material=None,
                 on_manage_projects=None,
                 on_image_compare=None,
                 on_canvas=None,
                 on_smartchart=None,
                 on_requirement_hub=None,
                 on_nozzle_calculator=None,
                 on_air_supply=None,
                 on_usage_stats=None,
                 on_label_generator=None,
                 on_offline_sync=None,
                 on_lab_assistant=None,
                 on_tdms_inspector=None,
                 # Logout-Callback (Button "Log Out" in der Sidebar-Account-Gruppe)
                 on_logout=None,
                 # Ctrl+Klick "in neuem Tab öffnen" (siehe ui/widgets/tab_container.py)
                 open_in_new_tab=None):
        super().__init__()
        # Callbacks
        self.on_all_experiments = on_all_experiments
        self.on_create_experiment = on_create_experiment
        self.on_create_experiment_legacy = on_create_experiment_legacy
        self.on_add_series = on_add_series
        self.on_add_trials = on_add_trials
        self.on_open_backlog = on_open_backlog
        self.on_open_experiment_request = on_open_experiment_request
        self.on_create_experiment_request = on_create_experiment_request
        self.on_open_my_requests = on_open_my_requests
        self.on_preview_requests = on_preview_requests
        self.on_preview_open_requests = on_preview_open_requests
        self.on_image_compare = on_image_compare
        self.on_canvas = on_canvas
        self.on_smartchart = on_smartchart
        self.on_requirement_hub = on_requirement_hub
        self.on_nozzle_calculator = on_nozzle_calculator
        self.on_air_supply = on_air_supply
        self.on_usage_stats = on_usage_stats
        self.on_label_generator = on_label_generator
        self.on_offline_sync = on_offline_sync
        self.on_lab_assistant = on_lab_assistant
        self.on_tdms_inspector = on_tdms_inspector

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
        self.on_manage_projects = on_manage_projects
        self.on_add_lab_machines = on_add_lab_machines

        self._on_logout = on_logout
        self._open_in_new_tab = open_in_new_tab

        # Populated by _build_ui() with every button that leads to a screen
        # not verified to work against the offline SQLite copy - see
        # _apply_offline_gate(). Must exist before _build_ui() runs.
        self._offline_gated_buttons: list = []

        self._build_ui()
        self._apply_offline_gate()
        self._wire_shortcuts()

        # Flag to ensure refresh only runs after UI exists.
        self._did_build = True

    def _apply_offline_gate(self):
        """Disables navigation to screens not verified to work offline.

        Only Home, All Experiments, Create Experiment/Add Series/Add Trials/
        Add Lab Machines (CreateExperimentScreen, all 4 modes), Manage Jets,
        Manage Yarn, and Offline Sync are currently verified against the
        offline SQLite copy (see CLAUDE.md "Offline-Modus (SQLite)" and
        db/offline_schema.py ROOT_TABLES/EXTRA_REFERENCE_TABLES) - everything
        else in self._offline_gated_buttons gets disabled with an explanatory
        tooltip instead of letting a user click through to a screen that will
        likely throw a raw SQL error on a table outside the offline copy.
        """
        from db.connection import is_offline_mode

        if not is_offline_mode():
            return
        for btn in self._offline_gated_buttons:
            try:
                btn.setEnabled(False)
                btn.setToolTip("Not available offline (not part of the offline data copy yet).")
            except Exception:
                pass


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
                self._refresh_my_requests_badge()
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

    # _pick_accent_colour() ist nach ui/widgets/sidebar_nav.py::pick_accent_colour()
    # ausgelagert (2026-08-26, TopBar-Entfernung) - war schon vorher komplett
    # self-contained (kein Zugriff auf HomeScreen-Zustand) und wird jetzt von
    # allen vier Sidebar-Screens gebraucht, nicht nur von Home.


    def _refresh_backlog_badge(self):
        """Aktualisiert den Backlog-Badge mit der aktuellen Anzahl offener Einträge."""
        if self.access_level < 2:
            return
        badge = getattr(self, "_backlog_badge", None)
        if badge is None:
            return
        sidebar_nav.refresh_badge(badge, sidebar_nav.get_backlog_count())

    def _refresh_approved_experiment_request_badge(self):
        """Aktualisiert den Badge für genehmigte Requests (Create New Experiment)."""
        badge = getattr(self, "_approved_exp_req_badge", None)
        if badge is None:
            return
        sidebar_nav.refresh_badge(badge, sidebar_nav.get_approved_experiment_request_count())

    def _refresh_experiment_request_badge(self):
        """Aktualisiert den Badge für offene ExperimentRequests (Superuser only)."""
        if self.access_level < 4:
            return
        badge = getattr(self, "_exp_req_badge", None)
        if badge is None:
            return
        sidebar_nav.refresh_badge(badge, sidebar_nav.get_open_experiment_request_count())

    def _refresh_my_requests_badge(self):
        """Aktualisiert den Badge auf 'My Requests' (offene Änderungs-Kopien,
        siehe db/experiment_request_changes.py) - Superuser sehen alle,
        normale Nutzer nur ihre eigenen."""
        badge = getattr(self, "_my_requests_badge", None)
        if badge is None:
            return
        sidebar_nav.refresh_badge(badge, sidebar_nav.get_pending_request_changes_count())


    def _build_ui(self):
        """Erstellt das vollständige Home-Layout: Sidebar-Navigation, Hauptbereich, Footer.

        Keine TopBar (HeaderBar) mehr (2026-08-26, Nutzerwunsch: "dann
        brauchen wir die top bar nicht mehr") - Glocke/Suche/Accent-Farbe/Log
        Out sind in die "Account"-Gruppe der Sidebar gewandert (ganz unten,
        siehe sidebar_nav.build_utility_group()); Home/Back wurden dabei
        bewusst NICHT in die Sidebar übernommen (Nutzer-Feedback: werden
        nicht mehr gebraucht, da die Sidebar-Navigation bereits alles
        abdeckt) - siehe CLAUDE.md für die volle Diskussion.
        """
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Body: Sidebar-Navigation (links) + Hauptbereich (rechts) ---
        # Ersetzt die frühere Stapel-von-Karten-Ansicht (siehe Git-Historie) durch
        # eine feste, dunkle Sidebar - selbe Buttons/Callbacks/Badges/Offline-Gating
        # wie vorher, nur umgruppiert. Reale Assets (assets/images/*.png,
        # tricolour.png, logo-heberlein-weiss.png), keine neuen Icons erfunden.
        # Das Sidebar-Chrome selbst (feste Breite, dunkler Hintergrund, Marken-
        # Kopf) steckt in ui/widgets/sidebar.py::SidebarPanel - ausgelagert wie
        # HeaderBar, als Grundlage für eine mögliche spätere App-weite Sidebar
        # (siehe CLAUDE.md). Der Inhalt (welche Sektionen/Buttons) bleibt hier.
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        sidebar = SidebarPanel(width=316)

        # Notifications-Glocke, ganz oben angepinnt (2026-09-02, siehe
        # sidebar_nav.build_pinned_bell()) - HomeScreen baut seine Sidebar
        # manuell statt ueber install_full_sidebar() (Legacy, siehe
        # CLAUDE.md: HomeScreen ist nicht mehr der Post-Login-Landing-
        # Screen), daher hier derselbe Aufruf separat statt automatisch
        # ueber dessen zentralen Rumpf.
        bell_refs = sidebar_nav.build_pinned_bell(sidebar)
        self._bell_button = bell_refs["bell_button"]
        self._bell_badge = bell_refs["bell_badge"]

        # --- Navigation-Gruppe (vormals "Experiments"-Karte) ---
        # Der frühere Rechtsklick-Träger für Snake/Athena/LFC (_exp_title_label
        # + eigens dafür gebautes Icon-Paar) ist 2026-08-27 in FooterBar
        # umgezogen (siehe ui/widgets/footer.py) - dadurch reicht hier jetzt
        # der normale Standard-Sektionskopf wie bei jedem anderen Sidebar-
        # Screen.
        sidebar.add_section_header("experiment_white.png", "Navigation", expanded=True)

        # Navigation-Items, Tools/Admin/Superuser-Gruppen: gemeinsam mit
        # BacklogScreen genutzt, siehe ui/widgets/sidebar_nav.py. Gibt Badge-
        # Referenzen zurück, die showEvent() zum Aktualisieren braucht.
        nav_refs = sidebar_nav.build_navigation_items(
            sidebar, self._offline_gated_buttons,
            access_level=self.access_level,
            on_all_experiments=self.on_all_experiments,
            on_open_backlog=self.on_open_backlog,
            on_open_experiment_request=self.on_open_experiment_request,
            on_create_experiment=self.on_create_experiment,
            on_create_experiment_legacy=self._on_legacy_create_clicked,
            on_add_series=self.on_add_series,
            on_add_lab_machines=self.on_add_lab_machines if callable(self.on_add_lab_machines) else None,
            on_preview_requests=self.on_preview_requests,
            on_preview_open_requests=self.on_preview_open_requests,
            open_in_new_tab=self._open_in_new_tab,
        )
        self._backlog_badge = nav_refs["backlog_badge"]
        self._exp_req_badge = nav_refs["exp_req_badge"]
        self._approved_exp_req_badge = nav_refs["approved_exp_req_badge"]
        self._btn_legacy_create = nav_refs["legacy_button"]

        sidebar.add_separator()

        # --- Experiment-Requests-Gruppe (2026-08-27, Nutzerwunsch: direkter
        # Sidebar-Zugriff auf "Create"/"My Requests" statt Umweg über den
        # Experiment-Request-Hub-Screen) ---
        exp_req_group_refs = sidebar_nav.build_experiment_requests_group(
            sidebar,
            on_create_experiment_request=self.on_create_experiment_request,
            on_open_my_requests=self.on_open_my_requests,
            open_in_new_tab=self._open_in_new_tab,
        )
        self._my_requests_badge = exp_req_group_refs["my_requests_badge"]

        sidebar.add_separator()

        # --- Tools-Gruppe ---
        sidebar_nav.build_tools_group(
            sidebar, self._offline_gated_buttons,
            access_level=self.access_level,
            on_image_compare=self.on_image_compare,
            on_canvas=self.on_canvas,
            on_nozzle_calculator=self.on_nozzle_calculator if callable(getattr(self, "on_nozzle_calculator", None)) else None,
            on_air_supply=self.on_air_supply if callable(getattr(self, "on_air_supply", None)) else None,
            on_requirement_hub=self.on_requirement_hub,
            on_smartchart=self.on_smartchart,
            on_yarn_stock=self.on_yarn_stock if callable(getattr(self, "on_yarn_stock", None)) else None,
            on_label_generator=self.on_label_generator if callable(getattr(self, "on_label_generator", None)) else None,
            on_tdms_inspector=self.on_tdms_inspector if callable(getattr(self, "on_tdms_inspector", None)) else None,
            open_in_new_tab=self._open_in_new_tab,
        )
        sidebar.add_separator()

        # --- Admin-Gruppe: jedem eingeloggten Nutzer sichtbar (Schreibrechte
        # weiterhin separat ueber app_meta.can_use_admin_box()/set_read_only()
        # in main.py gesteuert) ---
        can_admin = self.access_level >= 1
        if can_admin:
            sidebar_nav.build_admin_group(
                sidebar, self._offline_gated_buttons,
                on_add_jet=self.on_add_jet,
                on_add_top_plate=self.on_add_top_plate,
                on_add_yarn=self.on_add_yarn,
                on_manage_order_type=self.on_manage_order_type,
                on_manage_product_groups=self.on_manage_product_groups,
                on_manage_material=self.on_manage_material,
                on_manage_projects=self.on_manage_projects,
                open_in_new_tab=self._open_in_new_tab,
            )
            sidebar.add_separator()

        # --- Superuser-Gruppe ---
        if self.access_level >= 4:
            sidebar_nav.build_superuser_group(
                sidebar, self._offline_gated_buttons,
                on_add_user=self.on_add_user,
                on_usage_stats=self.on_usage_stats,
                on_offline_sync=self.on_offline_sync,
                on_lab_assistant=self.on_lab_assistant,
                open_in_new_tab=self._open_in_new_tab,
            )
            sidebar.add_separator()

        sidebar.add_stretch()

        # --- Account-Gruppe (Suche/Notifications/Accent-Farbe/Log Out) ---
        # Ersatz für die entfernte TopBar (siehe _build_ui-Docstring). Steht
        # nach dem add_stretch() oben, damit sie unten in der Sidebar
        # angepinnt bleibt. Bell-Refs werden für main.py's zentrale
        # _refresh_bell()-Logik gebraucht (siehe dort).
        sidebar_nav.build_utility_group(
            sidebar, on_logout=(self._on_logout if callable(self._on_logout) else None))

        # Wendet einen ggf. bereits woanders (z.B. Backlog) eingeklappten,
        # geteilten Collapse-Zustand auf die gerade erst gebauten Items an -
        # siehe ui/widgets/sidebar.py Moduldocstring.
        sidebar.apply_collapse_state()
        self._sidebar = sidebar
        body_layout.addWidget(sidebar)

        # --- Hauptbereich: Willkommensnachricht ---
        main_area = QWidget()
        main_layout = QVBoxLayout(main_area)
        main_layout.setContentsMargins(48, 44, 48, 40)
        main_layout.setSpacing(0)

        self._welcome_wrapper = QFrame()
        self._welcome_wrapper.setMaximumWidth(900)
        wlay = QVBoxLayout(self._welcome_wrapper)
        wlay.setContentsMargins(0, 0, 0, 0)
        wlay.setSpacing(0)

        self._welcome_label = QLabel("")
        self._welcome_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._welcome_label.setStyleSheet(
            "color: black; font-size: 30px; font-weight: bold;"
        )
        wlay.addWidget(self._welcome_label)

        main_layout.addWidget(self._welcome_wrapper, 0, Qt.AlignLeft)
        main_layout.addStretch()

        # Load and display welcome text
        self._refresh_welcome_message()

        body_layout.addWidget(main_area, 1)
        root.addWidget(body, 1)
        root.addWidget(FooterBar())



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

    def _wire_shortcuts(self):
        """Registriert Tastatur-Shortcuts (z.B. Ctrl+L für Logout)."""
        # Ctrl+L als Logout im Home-Screen
        if callable(self._on_logout):
            self._sc_logout = QShortcut(QKeySequence("Ctrl+L"), self)
            self._sc_logout.activated.connect(self._on_logout)

        # Ctrl+Shift+J: reveal des versteckten Legacy-Import-Buttons - seit
        # 2026-08-27 der gemeinsame, App-weit genutzte Helper (siehe
        # ui/widgets/sidebar_nav.py::ensure_legacy_reveal_shortcut()), NICHT
        # ein App-weiter Qt.ApplicationShortcut: würde mit dem unabhängigen,
        # gleichnamigen "Ctrl+Shift+J"-Insider-Modus-Shortcut in
        # ui/screen_aty_batch.py/ui/screen_tdms_batch.py kollidieren
        # ("ambiguous shortcut", Qt feuert dann keinen von beiden), sobald
        # einer dieser beiden Screens sichtbar ist. Ein lokaler, an Home
        # gebundener Shortcut (Default-Kontext Qt.WindowShortcut) ist nur
        # erreichbar, während Home selbst sichtbar ist - genau wie bei
        # jedem anderen Sidebar-Screen (siehe dort für die volle
        # Begründung).
        sidebar_nav.ensure_legacy_reveal_shortcut(self)

    # _build_tools_group()/_build_admin_group()/_build_superuser_group() sind
    # nach ui/widgets/sidebar_nav.py ausgelagert (gemeinsam mit BacklogScreen
    # genutzt) - siehe dort.