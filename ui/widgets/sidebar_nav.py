from __future__ import annotations
# ui/widgets/sidebar_nav.py
"""Gemeinsamer Aufbau der Haupt-Navigationsgruppen (Navigation/Tools/Admin/
Superuser) für die Sidebar - von ui/screen_home.py UND ui/screen_backlog.py
genutzt (siehe CLAUDE.md, "Home-Screen: Sidebar-Redesign" / "Offener nächster
Schritt", 2026-08-26 ff.).

Reine freie Funktionen statt Instanzmethoden auf HomeScreen, damit mehrere
Screens dieselbe Button-/Badge-/Offline-Gating-Logik teilen können, ohne
Vererbung oder Cross-Instance-Aufrufe. Aus HomeScreen 1:1 übernommen (reiner
Code-Move + Parametrisierung), keine Verhaltensänderung - insbesondere die
Badge-Wrap-Logik (_wrap_button_with_badge) und die drei Zähl-Queries
referenzierten schon vorher kein `self`, waren also faktisch bereits freie
Funktionen.
"""

from typing import Any, Callable, Optional

from PySide6.QtCore import Qt, QSize, QObject, QEvent
from PySide6.QtGui import QIcon, QColor
from PySide6.QtWidgets import (
    QPushButton, QWidget, QGridLayout, QLabel, QColorDialog, QApplication,
    QHBoxLayout, QVBoxLayout,
)

from ui.pathutil import resource_path
from db.connection import get_connection, is_offline_mode

from ui.widgets.sidebar import SidebarPanel


# --------------------------------------------------------------------------- Ctrl+Click "open in new tab" (2026-08-27)
class _CtrlHoverCursorFilter(QObject):
    """Ein einziger, App-weiter Event-Filter (statt einem pro Button) -
    Grund: das Halten/Loslassen von Strg während des Hoverns muss den
    Cursor des GERADE gehoverten Buttons aktualisieren können, aber
    Tastatur-Events gehen in Qt an das fokussierte Widget, nicht an das
    gehoverte (Sidebar-Buttons haben normalerweise nie den Fokus) - ein
    App-weiter Filter sieht dagegen beides (Enter/Leave UND KeyPress/
    KeyRelease), unabhängig vom Fokus. Zeigt Qt.DragCopyCursor (auf den
    meisten Plattformen ein Cursor mit kleinem "+"-Symbol - passendes
    Signal für "öffnet eine neue [Kopie/Ansicht]") während Strg gehalten
    UND ein 'tabCapable'-Button gehovert wird; sonst der normale
    PointingHandCursor. Nutzerwunsch: "der cursor verändert sich so, dass
    ich erkenne, dass es 'registerfähig' ist"."""

    _instance: "Optional[_CtrlHoverCursorFilter]" = None

    def __init__(self):
        super().__init__()
        self._hovered: Optional[QPushButton] = None

    @classmethod
    def ensure_installed(cls) -> "_CtrlHoverCursorFilter":
        if cls._instance is None:
            cls._instance = cls()
            app = QApplication.instance()
            if app is not None:
                app.installEventFilter(cls._instance)
        return cls._instance

    def eventFilter(self, obj, event):
        et = event.type()
        if et == QEvent.Enter and isinstance(obj, QPushButton) and obj.property("tabCapable"):
            self._hovered = obj
            self._apply_cursor(obj)
        elif et == QEvent.Leave and obj is self._hovered:
            self._hovered.setCursor(Qt.PointingHandCursor)
            self._hovered = None
        elif et in (QEvent.KeyPress, QEvent.KeyRelease) and self._hovered is not None:
            if event.key() == Qt.Key_Control:
                self._apply_cursor(self._hovered)
        return False

    def _apply_cursor(self, btn: QPushButton):
        if QApplication.keyboardModifiers() & Qt.ControlModifier:
            btn.setCursor(Qt.DragCopyCursor)
        else:
            btn.setCursor(Qt.PointingHandCursor)


def _wire_tab_capable_click(btn: QPushButton, on_click: Callable, open_in_new_tab: Optional[Callable]):
    """Verdrahtet einen Sidebar-Nav-Button so, dass ein Klick mit gehaltener
    Strg-Taste `open_in_new_tab(on_click)` statt `on_click()` aufruft
    (Nutzerwunsch, 2026-08-27: "wenn ich aus dem sidepanel etwas anklicke
    mit gehaltener ctrl taste, wird eine neue registerkarte mit dem screen
    geöffnet") - siehe MainWindow._open_in_new_tab_dispatch()/ui/widgets/
    tab_container.py für die Tab-Mechanik. `open_in_new_tab=None` lässt den
    Button ganz normal funktionieren - bewusst OHNE den Cursor-Hinweis (kein
    'tabCapable'-Property, kein Event-Filter), da der Hinweis sonst
    "registerfähig" suggerieren würde, obwohl Strg+Klick dort nichts
    Besonderes tut (aktuell nur relevant, falls ein Aufrufer bewusst keine
    Tab-Unterstützung anbietet - main.py übergibt inzwischen für jeden
    Sidebar-Screen denselben Dispatcher, siehe _sidebar_nav_kwargs())."""
    if open_in_new_tab is None:
        btn.clicked.connect(lambda *_: on_click())
        return
    btn.setProperty("tabCapable", True)
    _CtrlHoverCursorFilter.ensure_installed()

    def _handler(*_):
        # Only an actually held Ctrl opens a new tab now - there used to
        # also be an automatic "pinned tab protects itself" redirect (any
        # normal navigation WITHIN a comparison tab opened via Ctrl+click
        # was treated as if Ctrl were held too), which was removed again on
        # explicit user request (2026-09-01: "manchmal gehen neue tabs auf
        # beim navigieren ohne, dass ich explizit in neuem tab öffnen wähle
        # oder ctrl halte ... ich will, dass nur neue tabs erstellt werden,
        # wenn ich es explizit so will") - see HISTORY.md for the prior
        # rationale (2026-08-27 bug report) that originally introduced this
        # automatism.
        ctrl_held = bool(QApplication.keyboardModifiers() & Qt.ControlModifier)
        if ctrl_held:
            open_in_new_tab(on_click)
        else:
            on_click()

    btn.clicked.connect(_handler)


# --------------------------------------------------------------------------- Widgets
def icon_btn(text: str, icon_file: str, style: str, on_click: Optional[Callable] = None, *,
             tab_capable: bool = False, open_in_new_tab: Optional[Callable] = None) -> QPushButton:
    """Erstellt einen QPushButton mit Icon (links) + Text (rechts).

    `tab_capable=True` (nur für echte Bildschirm-Navigationsziele, nicht für
    die Account-Gruppe - siehe build_utility_group()) aktiviert Ctrl+Klick
    "in neuem Tab öffnen" + den Cursor-Hinweis dafür, siehe
    _wire_tab_capable_click()."""
    btn = QPushButton(text)
    btn.setObjectName(style)
    icon_path = resource_path(f"assets/images/{icon_file}")
    icon = QIcon(icon_path)
    if not icon.isNull():
        btn.setIcon(icon)
        btn.setIconSize(QSize(18, 18))
    if callable(on_click):
        if tab_capable:
            _wire_tab_capable_click(btn, on_click, open_in_new_tab)
        else:
            btn.clicked.connect(lambda *_: on_click())
    else:
        btn.setEnabled(False)
    return btn


def green_btn(text: str, on_click: Optional[Callable] = None, *,
              tab_capable: bool = False, open_in_new_tab: Optional[Callable] = None) -> QPushButton:
    """Text-only Sidebar-Eintrag (kein Icon-Asset vorhanden, siehe CLAUDE.md).
    `tab_capable`/`open_in_new_tab`: siehe icon_btn()."""
    btn = QPushButton(text)
    btn.setObjectName("SidebarItem")
    if callable(on_click):
        if tab_capable:
            _wire_tab_capable_click(btn, on_click, open_in_new_tab)
        else:
            btn.clicked.connect(lambda *_: on_click())
    else:
        btn.setEnabled(False)
    return btn


def wrap_with_badge(btn: QPushButton, count: int):
    """Umhüllt einen QPushButton mit einem roten WhatsApp-Style-Badge (oben rechts).

    QGridLayout-Overlay statt Stacked-Layout (vermeidet "Unable to set
    geometry"-Warnungen auf manchen Setups, siehe ursprüngliche
    HomeScreen._wrap_button_with_badge).
    """
    container = QWidget()
    container.setContentsMargins(0, 0, 0, 0)

    grid = QGridLayout(container)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSpacing(0)
    grid.addWidget(btn, 0, 0)

    badge = QLabel(container)
    badge.setAlignment(Qt.AlignCenter)
    badge.setVisible(count > 0)
    badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
    badge.setText("9+" if count > 9 else str(count))
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
    badge.adjustSize()
    w = max(18, badge.sizeHint().width())
    badge.setFixedSize(w, 18)
    grid.addWidget(badge, 0, 0, alignment=Qt.AlignTop | Qt.AlignRight)

    return container, badge


def refresh_badge(badge: Optional[QLabel], count: int):
    """Aktualisiert einen per wrap_with_badge() erzeugten Badge (Text/Sichtbarkeit/Größe)."""
    if badge is None:
        return
    badge.setVisible(count > 0)
    badge.setText("9+" if count > 9 else str(count))
    try:
        badge.adjustSize()
        w = max(18, badge.sizeHint().width())
        badge.setFixedSize(w, 18)
    except Exception:
        pass


# --------------------------------------------------------------------------- Counts
def get_backlog_count() -> int:
    """Zählt offene Backlog-Einträge (BacklogStatus = 'Backlog')."""
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
        return int(row[0] or 0) if row else 0
    except Exception:
        return 0


def _live_request_filter_sql() -> str:
    """Extra WHERE clause that filters archived prior versions (see
    db/experiment_request_changes.py::supports_versioning()) out of count
    queries - without it, these badges would keep climbing with every
    accepted change to a matching request. Empty string on environments
    without the PriorVersionOfID column."""
    try:
        from db import experiment_request_changes as request_changes
        if request_changes.supports_versioning():
            return " AND [PriorVersionOfID] IS NULL"
    except Exception:
        pass
    return ""


def get_open_experiment_request_count() -> int:
    """Zählt offene ExperimentRequests (RequestStatus = 1)."""
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM [tblExperimentRequests] WHERE [RequestStatus] = 1"
                + _live_request_filter_sql()
            )
            row = cur.fetchone()
        return int(row[0] or 0) if row else 0
    except Exception:
        return 0


def get_approved_experiment_request_count() -> int:
    """Zählt genehmigte ExperimentRequests (RequestStatus = 3)."""
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM [tblExperimentRequests] WHERE [RequestStatus] = 3"
                + _live_request_filter_sql()
            )
            row = cur.fetchone()
        return int(row[0] or 0) if row else 0
    except Exception:
        return 0


def get_new_open_request_count(owner_id: Optional[Any] = None) -> int:
    """Zählt brandneue Requests mit Status 'Request' (RequestStatus=1), die
    KEINE Änderungs-Kopie sind (ChangeOfRequestID IS NULL) - Gegenstück zu
    request_changes.count_pending_changes(), das nur die Kopien zählt. Beide
    zusammen ergeben "alles, was gerade im Status Request wartet" (siehe
    get_pending_request_changes_count()). `owner_id=None`: alle (Superuser-
    Sicht), sonst nur CreatedBy=owner_id."""
    try:
        from db import experiment_request_changes as request_changes
        change_filter = (
            " AND [ChangeOfRequestID] IS NULL" if request_changes.supports_change_tracking() else ""
        )
        with get_connection() as cn:
            cur = cn.cursor()
            if owner_id in (None, ""):
                cur.execute(
                    "SELECT COUNT(*) FROM [tblExperimentRequests] WHERE [RequestStatus] = 1"
                    + change_filter + _live_request_filter_sql()
                )
            else:
                cur.execute(
                    "SELECT COUNT(*) FROM [tblExperimentRequests] WHERE [RequestStatus] = 1"
                    + change_filter + " AND [CreatedBy] = ?" + _live_request_filter_sql(),
                    [owner_id],
                )
            row = cur.fetchone()
        return int(row[0] or 0) if row else 0
    except Exception:
        return 0


def get_pending_request_changes_count() -> int:
    """Zählt ALLES, was für den Badge auf "My Requests" relevant ist: offene
    Änderungs-Kopien (siehe db/experiment_request_changes.py) PLUS brandneue,
    noch nicht geprüfte Requests (RequestStatus=1, keine Kopie) - Nutzerwunsch
    2026-09-08: beide Arten sollen gezählt/gehighlighted werden, nur mit
    unterschiedlichem Symbol unterscheidbar (siehe screen_my_requests.py,
    Markierung neuer Requests neben der bestehenden Kopie-Markierung).
    Superuser sehen alle, normale Nutzer nur ihre eigenen (gleiche
    Sichtbarkeits-Logik wie zuvor in
    ExperimentRequestScreen._refresh_my_requests_badge(), jetzt hierher
    verschoben, damit der direkte Sidebar-Eintrag denselben Badge zeigt)."""
    try:
        import app_meta
        from db import experiment_request_changes as request_changes
        is_superuser = bool(getattr(app_meta, "is_superuser_level", lambda: False)())
        owner_id = None if is_superuser else (app_meta.current_user or {}).get("id")
        return (
            request_changes.count_pending_changes(owner_id)
            + get_new_open_request_count(owner_id)
        )
    except Exception:
        return 0


# --------------------------------------------------------------------------- Groups
def build_navigation_items(
    sidebar: SidebarPanel,
    offline_gated_buttons: list,
    *,
    access_level: int,
    on_all_experiments,
    on_open_backlog,
    on_open_experiment_request,
    on_create_experiment,
    on_create_experiment_legacy,
    on_add_series,
    on_add_lab_machines,
    on_preview_requests=None,
    on_preview_open_requests=None,
    open_in_new_tab=None,
) -> dict[str, Any]:
    """Fügt die Navigation-Items (Show All Experiments/Backlog/Experiment
    Request/Create/Add Series/Add Lab Machines) in die Sidebar ein.

    Baut bewusst KEINEN Sektions-Header - der Aufrufer entscheidet selbst,
    ob er einen einfachen (sidebar.add_section_header()) oder einen mit
    Sonderverhalten (siehe HomeScreen: geheimer Rechtsklick) davor setzt.

    Gibt ein Dict mit den Referenzen zurück, die der Aufrufer für
    Badge-Refresh (showEvent) und den Legacy-Button-Toggle (Ctrl+Shift+J)
    braucht: backlog_badge, exp_req_badge, approved_exp_req_badge,
    legacy_button.
    """
    refs: dict[str, Any] = {
        "backlog_badge": None,
        "exp_req_badge": None,
        "approved_exp_req_badge": None,
        "legacy_button": None,
    }

    btn_show = icon_btn("All Experiments", "show.png", "SidebarItem", on_all_experiments,
                         tab_capable=True, open_in_new_tab=open_in_new_tab)
    sidebar.add_item(btn_show)

    btn_backlog = icon_btn("Backlog", "backlog.png", "SidebarItem", on_open_backlog,
                            tab_capable=True, open_in_new_tab=open_in_new_tab)
    btn_backlog.setVisible(access_level >= 2)
    # Verified offline-safe (tbltrialseriesimage/tbltrialseriespdf/
    # tbltrialretestflag added to EXTRA_REFERENCE_TABLES) - not gated.
    if access_level >= 2:
        try:
            cnt = get_backlog_count()
        except Exception:
            cnt = 0
        try:
            wrapped, badge = wrap_with_badge(btn_backlog, cnt)
            refs["backlog_badge"] = badge
            sidebar.add_item(wrapped)
        except Exception:
            sidebar.add_item(btn_backlog)
    else:
        sidebar.add_item(btn_backlog)

    # Der frühere "Experiment Request"-Eintrag (Hub-Screen) ist entfernt
    # (Nutzerwunsch, 2026-08-27) - "Create Experiment Request"/"My Requests"
    # sind jetzt direkt in der eigenen "Experiment Requests"-Sektion
    # erreichbar (siehe build_experiment_requests_group()), der Hub-Screen
    # selbst ist damit redundant geworden. `on_open_experiment_request`
    # bleibt als Parameter bestehen (unused hier), um alle bestehenden
    # Aufrufer unangetastet zu lassen. `refs["exp_req_badge"]` bleibt `None`
    # (kein Ersatz-Ort für den "offene Requests"-Badge gebaut - falls das
    # wieder gebraucht wird, müsste er explizit z.B. auf "My Requests"
    # verdrahtet werden).

    # Farbunterscheidung Grün/Lila kommt aus den bereits entsprechend
    # eingefärbten PNGs (create.png/series.png/lab.png sind lila), nicht aus
    # einem eigenen Button-Stil.
    btn_create = icon_btn("New Experiment", "create.png", "SidebarItem", on_create_experiment,
                           tab_capable=True, open_in_new_tab=open_in_new_tab)
    btn_legacy_create = icon_btn(
        "Legacy Import (Manual ID)", "legacy.png", "SidebarItem", on_create_experiment_legacy,
        tab_capable=True, open_in_new_tab=open_in_new_tab)
    btn_legacy_create.hide()
    refs["legacy_button"] = btn_legacy_create
    btn_add_series = icon_btn("Add Trial Series", "series.png", "SidebarItem", on_add_series,
                               tab_capable=True, open_in_new_tab=open_in_new_tab)

    can_see_purple = access_level >= 2
    for _b in (btn_create, btn_add_series):
        _b.setVisible(can_see_purple)

    try:
        cnt = get_approved_experiment_request_count()
    except Exception:
        cnt = 0
    try:
        wrapped, badge = wrap_with_badge(btn_create, cnt)
        refs["approved_exp_req_badge"] = badge
        badge.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        badge.setCursor(Qt.PointingHandCursor)
        badge.setToolTip("View pending experiment requests")
        if callable(on_preview_requests):
            badge.mousePressEvent = lambda _e: on_preview_requests()
        sidebar.add_item(wrapped)
        sidebar.add_item(btn_legacy_create)
    except Exception:
        sidebar.add_item(btn_create)
        sidebar.add_item(btn_legacy_create)
    sidebar.add_item(btn_add_series)

    btn_lab_machines = icon_btn("Add Lab Machines", "lab.png", "SidebarItem", on_add_lab_machines,
                                 tab_capable=True, open_in_new_tab=open_in_new_tab)
    btn_lab_machines.setVisible(can_see_purple)
    sidebar.add_item(btn_lab_machines)

    return refs


def build_experiment_requests_group(
    sidebar: SidebarPanel,
    *,
    on_create_experiment_request,
    on_open_my_requests,
    open_in_new_tab=None,
) -> dict[str, Any]:
    """Eigene Sektion (nach Navigation, vor Tools) mit direktem Zugriff auf
    "Create Experiment Request"/"My Requests" - Nutzerwunsch 2026-08-27: bisher
    nur über den "Experiment Request"-Hub-Screen (2 Klicks) erreichbar, jetzt
    zusaetzlich 1 Klick direkt aus der Sidebar. Der Hub-Screen selbst bleibt
    unveraendert bestehen (über den bestehenden "Experiment Request"-Eintrag
    in der Navigation-Sektion weiterhin erreichbar), diese Sektion ist rein
    additiv.

    Badge auf "My Requests" = offene Änderungs-Kopien UND brandneue Requests,
    die beide auf Prüfung warten (siehe get_pending_request_changes_count()) -
    identische Zählung wie zuvor auf dem Hub-Screen selbst
    (ExperimentRequestScreen), seit 2026-09-08 um neue Requests erweitert.
    """
    sidebar.add_section_header("experiment_requests_section_white.png", "Experiment Requests")

    btn_create = icon_btn(
        "Create Experiment Request", "create_experiment_request.png", "SidebarItem",
        on_create_experiment_request, tab_capable=True, open_in_new_tab=open_in_new_tab)
    sidebar.add_item(btn_create)

    btn_my_requests = icon_btn(
        "My Requests", "my_experiment_requests.png", "SidebarItem",
        on_open_my_requests, tab_capable=True, open_in_new_tab=open_in_new_tab)
    cnt = get_pending_request_changes_count()
    wrapped, badge = wrap_with_badge(btn_my_requests, cnt)
    wrapped.setToolTip("Requests/change proposals waiting for approval" if cnt else "")
    sidebar.add_item(wrapped)

    return {"my_requests_badge": badge}


def build_tools_group(
    sidebar: SidebarPanel,
    offline_gated_buttons: list,
    *,
    access_level: int,
    on_image_compare,
    on_canvas,
    on_nozzle_calculator,
    on_air_supply,
    on_requirement_hub,
    on_smartchart,
    on_yarn_stock,
    on_label_generator,
    on_tdms_inspector,
    open_in_new_tab=None,
):
    """Fügt die Tools-Sektion (Canvas, Image Compare usw.) in die Sidebar ein."""
    sidebar.add_section_header("tools.png", "Tools")

    btn_image_compare = icon_btn("Image Compare", "image_compare.png", "SidebarItem", on_image_compare,
                                  tab_capable=True, open_in_new_tab=open_in_new_tab)
    offline_gated_buttons.append(btn_image_compare)
    sidebar.add_item(btn_image_compare)

    btn_canvas = icon_btn("Canvas", "canvas.png", "SidebarItem", on_canvas,
                           tab_capable=True, open_in_new_tab=open_in_new_tab)
    offline_gated_buttons.append(btn_canvas)
    sidebar.add_item(btn_canvas)

    btn_nozzle_calc = icon_btn("Jet ROI Calculator", "nozzle_calculator.png", "SidebarItem", on_nozzle_calculator,
                                tab_capable=True, open_in_new_tab=open_in_new_tab)
    offline_gated_buttons.append(btn_nozzle_calc)
    sidebar.add_item(btn_nozzle_calc)

    btn_air_supply = icon_btn("Air Supply Network", "air_supply.png", "SidebarItem", on_air_supply,
                               tab_capable=True, open_in_new_tab=open_in_new_tab)
    offline_gated_buttons.append(btn_air_supply)
    sidebar.add_item(btn_air_supply)

    # Requirement Hub / Smart Chart (access_level >= 3)
    if access_level >= 3:
        btn_req_hub = icon_btn("Requirement Hub", "requirement_hub.png", "SidebarItem", on_requirement_hub,
                                tab_capable=True, open_in_new_tab=open_in_new_tab)
        offline_gated_buttons.append(btn_req_hub)
        sidebar.add_item(btn_req_hub)

        btn_smartchart = icon_btn("Smart Chart", "analytics.png", "SidebarItem", on_smartchart,
                                   tab_capable=True, open_in_new_tab=open_in_new_tab)
        offline_gated_buttons.append(btn_smartchart)
        sidebar.add_item(btn_smartchart)

    btn_yarn_stock = icon_btn("Yarn Stock", "manage_yarn.png", "SidebarItem", on_yarn_stock,
                               tab_capable=True, open_in_new_tab=open_in_new_tab)
    offline_gated_buttons.append(btn_yarn_stock)
    sidebar.add_item(btn_yarn_stock)

    btn_label_gen = icon_btn("Label Generator", "label.png", "SidebarItem", on_label_generator,
                              tab_capable=True, open_in_new_tab=open_in_new_tab)
    offline_gated_buttons.append(btn_label_gen)
    sidebar.add_item(btn_label_gen)

    # TDMS Inspector - never DB-gated (see ui/screen_tdms_inspector.py), works
    # offline too, so it is deliberately NOT appended to offline_gated_buttons.
    btn_tdms_inspector = icon_btn("TDMS Inspector", "tdms_inspector.png", "SidebarItem", on_tdms_inspector,
                                   tab_capable=True, open_in_new_tab=open_in_new_tab)
    sidebar.add_item(btn_tdms_inspector)


def build_admin_group(
    sidebar: SidebarPanel,
    offline_gated_buttons: list,
    *,
    on_add_jet,
    on_add_top_plate,
    on_add_yarn,
    on_manage_order_type,
    on_manage_product_groups,
    on_manage_material,
    open_in_new_tab=None,
):
    """Fügt die Admin-Sektion (Jets-, Yarn-, Material-Verwaltung usw.) in die Sidebar ein."""
    sidebar.add_section_header("admin_white.png", "Admin")

    # Kein "Manage "-Präfix (Sektions-Überschrift "ADMIN" sagt das bereits).
    btn_manage_jets = green_btn("Jets", on_add_jet, tab_capable=True, open_in_new_tab=open_in_new_tab)
    btn_manage_top_plates = green_btn("Top Plates", on_add_top_plate, tab_capable=True, open_in_new_tab=open_in_new_tab)
    btn_add_yarn = green_btn("Yarn", on_add_yarn, tab_capable=True, open_in_new_tab=open_in_new_tab)
    # Manage Jets/Manage Yarn are verified offline-safe (NewJetScreen/
    # ManageYarnScreen construct fine and use the dialect-aware canonical
    # db.connection helpers) - Top Plates is not, gated below.
    offline_gated_buttons.append(btn_manage_top_plates)
    for b in (btn_manage_jets, btn_manage_top_plates, btn_add_yarn):
        sidebar.add_item(b)

    btn_order_type = green_btn("Order Type", on_manage_order_type, tab_capable=True, open_in_new_tab=open_in_new_tab)
    btn_product_groups = green_btn("Product Groups", on_manage_product_groups, tab_capable=True, open_in_new_tab=open_in_new_tab)
    btn_material = green_btn("Material", on_manage_material, tab_capable=True, open_in_new_tab=open_in_new_tab)
    offline_gated_buttons.extend([btn_order_type, btn_product_groups, btn_material])
    for b in (btn_order_type, btn_product_groups, btn_material):
        sidebar.add_item(b)


def build_superuser_group(
    sidebar: SidebarPanel,
    offline_gated_buttons: list,
    *,
    on_add_user,
    on_usage_stats,
    on_statistics,
    on_offline_sync,
    on_lab_assistant,
    open_in_new_tab=None,
):
    """Fügt die Superuser-Sektion (erweiterte Admin-Funktionen) in die Sidebar ein."""
    sidebar.add_section_header("superuser.png", "Superuser")

    btn_manage_user = green_btn("Manage User", on_add_user, tab_capable=True, open_in_new_tab=open_in_new_tab)
    sidebar.add_item(btn_manage_user)
    offline_gated_buttons.append(btn_manage_user)

    btn_usage_stats = green_btn("Usage Stats", on_usage_stats, tab_capable=True, open_in_new_tab=open_in_new_tab)
    sidebar.add_item(btn_usage_stats)
    offline_gated_buttons.append(btn_usage_stats)

    btn_statistics = green_btn("Statistics", on_statistics, tab_capable=True, open_in_new_tab=open_in_new_tab)
    sidebar.add_item(btn_statistics)
    offline_gated_buttons.append(btn_statistics)

    btn_offline_sync = green_btn("Offline Sync", on_offline_sync, tab_capable=True, open_in_new_tab=open_in_new_tab)
    sidebar.add_item(btn_offline_sync)
    # bewusst NICHT in offline_gated_buttons (Offline Sync funktioniert offline)

    btn_lab_assistant = green_btn("Lab Assistant", on_lab_assistant, tab_capable=True, open_in_new_tab=open_in_new_tab)
    sidebar.add_item(btn_lab_assistant)
    offline_gated_buttons.append(btn_lab_assistant)

    # Deleted trial series, restorable (db/recycle_bin.py) - a dialog, no screen
    def _open_recycle_bin():
        from ui.widgets.recycle_bin_dialog import open_recycle_bin
        open_recycle_bin(sidebar.window())
    btn_recycle = green_btn("Recycle Bin", _open_recycle_bin)
    sidebar.add_item(btn_recycle)
    offline_gated_buttons.append(btn_recycle)


def apply_offline_gate(offline_gated_buttons: list):
    """Deaktiviert alle gesammelten offline-ungeeigneten Buttons, wenn der
    Prozess im Offline-Modus läuft (siehe HomeScreen._apply_offline_gate(),
    von dem das hier 1:1 übernommen ist)."""
    if not is_offline_mode():
        return
    for btn in offline_gated_buttons:
        try:
            btn.setEnabled(False)
            btn.setToolTip("Not available offline (not part of the offline data copy yet).")
        except Exception:
            pass


# --------------------------------------------------------------------------- Account/Utility
def trigger_quick_search():
    """Öffnet Quick Search über die globale app_meta-Registrierung (main.py
    registriert dort app_meta.open_quick_search - siehe HeaderBar._on_search_clicked(),
    von dem das hier 1:1 übernommen ist, ohne den Signal-Fallback, der nur für
    Aufrufer ohne globale Registrierung gedacht war)."""
    try:
        import app_meta
        if callable(app_meta.open_quick_search):
            app_meta.open_quick_search()
    except Exception:
        pass


def trigger_help_search():
    """Oeffnet die Hilfe-Suche ueber die globale app_meta-Registrierung
    (main.py setzt app_meta.open_help_search, gleiches Muster wie Quick Search)."""
    try:
        import app_meta
        if callable(app_meta.open_help_search):
            app_meta.open_help_search()
    except Exception:
        pass


def build_pinned_bell(sidebar: SidebarPanel) -> dict[str, Any]:
    """Fügt die Notifications-Glocke als eigenen, fest sichtbaren Eintrag
    ganz oben ein, noch vor Search (2026-09-02, Nutzerwunsch: "die glocke
    muss weiter hoch im sidepanel, am liebsten gleich zu oberst und nicht
    versteckt in account... mach es direkt über die search hin") - exakt
    dasselbe Muster wie build_pinned_search() direkt darunter, aus demselben
    ursprünglichen Grund (Account-Sektion startet standardmässig
    eingeklappt, war zwei Klicks entfernt und weit weg vom Blick, siehe
    dortiger Kommentar zum ursprünglichen Such-Feld-Umzug).

    `on_click=None` bleibt hier bewusst (wie zuvor in build_utility_group())
    - der eigentliche Klick-Handler wird erst dynamisch von
    main.py::_refresh_bell() verdrahtet, sobald ein User eingeloggt ist
    (dort auch das setEnabled(True), das icon_btn()'s Auto-Disable-bei-
    fehlendem-Callback wieder aufhebt - siehe dortiger Kommentar).

    Gibt {"bell_button": QPushButton, "bell_badge": QLabel} zurück -
    identische Keys wie zuvor aus build_utility_group(), main.py greift
    darauf über denselben, unveränderten refs["bell_button"]/
    refs["bell_badge"]-Zugriff zu (siehe install_full_sidebar())."""
    btn_bell = icon_btn("Notifications", "bell.png", "SidebarItem", None)
    wrapped, badge = wrap_with_badge(btn_bell, 0)
    sidebar.add_item(wrapped)
    return {"bell_button": btn_bell, "bell_badge": badge}


def build_pinned_search(sidebar: SidebarPanel) -> QPushButton:
    """Fügt Search als eigenen, fest sichtbaren Eintrag ganz oben ein - vor
    jeder add_section_header()/add_row()-Sektion (siehe install_full_sidebar()),
    dadurch landet er über SidebarPanel.add_item() direkt im obersten Layout
    statt im Container einer einklappbaren Sektion (siehe dortiger
    `self._current_section is not None`-Zweig). Ersetzt die frühere Position
    in der Account-Gruppe ganz unten (Nutzerfeedback 2026-08-28: "im
    sidepanel gefällt mir der search button nicht - resp. wo er ist" - dort
    lag Search hinter der standardmässig eingeklappten "Account"-Sektion,
    zwei Klicks entfernt und weit weg vom Blick). Bleibt unabhängig vom
    Ganze-Sidebar-Collapse sichtbar (Icon-only-Fallback läuft über denselben
    `_items`-Mechanismus wie alle anderen Einträge, siehe
    SidebarPanel.apply_collapse_state())."""
    btn_search = icon_btn("Search", "quick_Search.png", "SidebarItem", trigger_quick_search)
    sidebar.add_item(btn_search)
    return btn_search


def build_pinned_help(sidebar: SidebarPanel) -> QPushButton:
    """Fester Eintrag "Help" direkt unter Search (2026-10-13): Hilfe-Suche
    ueber alle Kontext-Hilfen ("wo finde ich…?"), auch per F1."""
    btn_help = icon_btn("Help (F1)", "help_tour.png", "SidebarItem", trigger_help_search)
    btn_help.setToolTip("Where do I find…? Search all help pages")
    sidebar.add_item(btn_help)
    return btn_help


def pick_accent_colour(parent: QWidget):
    """Öffnet einen QColorDialog zur Auswahl der persönlichen Akzentfarbe,
    speichert sie in tblUser.AccentColour und wendet sie sofort an - 1:1 aus
    HomeScreen._pick_accent_colour() hierher verschoben (2026-08-26, TopBar-
    Entfernung), da die Logik schon vorher komplett self-contained war (kein
    Zugriff auf HomeScreen-Zustand) und jetzt von allen vier Sidebar-Screens
    gebraucht wird, nicht nur von Home."""
    try:
        import app_meta
        from ui.theme import set_accent, build_qss, get_accent

        current = QColor(get_accent())
        colour = QColorDialog.getColor(current, parent, "Choose accent colour")
        if not colour.isValid():
            return
        hex_val = colour.name()  # z.B. '#8a2be2'
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
        app_meta.current_user["accent_colour"] = hex_val
        set_accent(hex_val)
        QApplication.instance().setStyleSheet(build_qss())
    except Exception:
        pass


def build_utility_group(sidebar: SidebarPanel, *, on_logout: Optional[Callable] = None) -> dict[str, Any]:
    """Fügt eine "Account"-Gruppe (Accent-Farbe, Log Out) ganz unten in die
    Sidebar ein - Ersatz für die frühere TopBar (HeaderBar), die auf allen
    vier Sidebar-Screens (Home/Backlog/AllExperiments/ShowExperiment)
    entfernt wurde (2026-08-26, Nutzerwunsch: "dann brauchen wir die top bar
    nicht mehr"). Accent-Farbe braucht keinen externen Callback (komplett
    self-contained, siehe pick_accent_colour() oben) - nur Log Out kommt von
    aussen (screen-spezifisch aus main.py durchgereicht), wird bei fehlendem
    Callback komplett versteckt statt nur deaktiviert (gleiches Verhalten wie
    HeaderBar's Log-Out-Button vorher: der wurde nur gebaut, wenn on_logout
    callable war).

    Notifications-Glocke ist seit 2026-09-02 kein Account-Eintrag mehr,
    sondern (wie Search seit 2026-08-28) ein pinned Item ganz oben in der
    Sidebar - siehe build_pinned_bell()."""
    sidebar.add_section_header("user_white.png", "Account")

    # "Settings" (welcome message, accent colour, display of the Show
    # Experiment tables) replaces the former "Accent Colour" button
    def _open_settings():
        from ui.widgets.user_settings_dialog import open_user_settings
        open_user_settings(sidebar.window())
    btn_settings = green_btn("Settings", _open_settings)
    sidebar.add_item(btn_settings)

    # "What's new" (ui/whats_new.py): new features of all versions, any time
    def _open_whats_new():
        from ui.whats_new import show_whats_new
        try:
            from db.usage_log import log_usage_event
            log_usage_event("feature", "whats_new_open")
        except Exception:
            pass
        show_whats_new(sidebar.window())
    btn_new = green_btn("What's new", _open_whats_new)
    sidebar.add_item(btn_new)

    btn_logout = green_btn("Log Out", on_logout)
    btn_logout.setVisible(callable(on_logout))
    sidebar.add_item(btn_logout)

    return {}


# --------------------------------------------------------------------------- App-wide rollout (2026-08-27)
def wrap_body_with_sidebar(root_layout, *, width: int = 316) -> tuple[SidebarPanel, QVBoxLayout]:
    """Baut den Sidebar+Content-Split (SidebarPanel links, Content-Widget
    rechts) und hängt ihn an `root_layout` an - Ersatz für das frühere
    `root.addWidget(header)` (siehe CLAUDE.md, "TopBar entfernt"). Gibt
    (sidebar, content_layout) zurück; der Aufrufer baut seinen bisherigen
    Bildschirminhalt in `content_layout` statt direkt in `root_layout` (ein
    ggf. vorhandener Footer bleibt bewusst auf `root_layout`, spannt also
    volle Breite unter Sidebar+Inhalt - siehe die vier ursprünglichen
    Sidebar-Screens für das Muster)."""
    body_layout = QHBoxLayout()
    body_layout.setContentsMargins(0, 0, 0, 0)
    body_layout.setSpacing(0)
    sidebar = SidebarPanel(width=width)
    body_layout.addWidget(sidebar)

    content = QWidget()
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(0)
    body_layout.addWidget(content, 1)

    root_layout.addLayout(body_layout, 1)
    return sidebar, content_layout


def install_full_sidebar(sidebar: SidebarPanel, callbacks: Optional[dict], *,
                          access_level: int, hide_self_link: Optional[str] = None) -> dict:
    """Baut die komplette Sidebar (Navigation/Tools/Admin/Superuser/Account)
    aus einem flachen Callback-Dict (siehe main.py::_sidebar_nav_kwargs()) -
    gemeinsamer Rumpf für _refresh_sidebar() auf jedem Sidebar-Screen (seit
    2026-08-27 App-weit ausgerollt, vorher separat dupliziert in Home/
    Backlog/AllExperiments/ShowExperiment - siehe deren _refresh_sidebar()
    für das ursprüngliche, jetzt hierher gezogene Muster). Fehlende Keys im
    Dict werden als `None` behandelt (der jeweilige Sidebar-Eintrag ist dann
    sichtbar, aber deaktiviert - gleiches Verhalten wie zuvor).

    `hide_self_link` ('all_experiments' oder 'backlog') unterdrückt genau
    den einen Sprungziel-auf-sich-selbst-Nav-Eintrag für die beiden Screens,
    die diese Navigationsziele selbst SIND (AllExperimentsScreen/
    BacklogScreen) - dort bewusst nicht aus dem Callback-Dict genommen,
    sondern hart auf None erzwungen, egal was im Dict steht.

    Ruft am Ende `sidebar.apply_collapse_state()`/`apply_offline_gate()`
    selbst auf. Gibt ein Dict mit allen Badge-/Bell-Refs sowie der
    gesammelten `offline_gated_buttons`-Liste zurück - der Aufrufer
    speichert die Referenzen, die er für showEvent()-Badge-Refreshes
    braucht (siehe refresh_sidebar_badges()/refresh_lazy_sidebar())."""
    cb = callbacks or {}
    offline_gated: list = []
    open_in_new_tab = cb.get("open_in_new_tab")

    # Pinned, VOR jeder Sektion (siehe build_pinned_bell()/build_pinned_search())
    # - dadurch immer sichtbar, unabhängig vom Klapp-Zustand von "Navigation"
    # & Co. Bell zuoberst, direkt über Search (2026-09-02, Nutzerwunsch: "die
    # glocke muss weiter hoch im sidepanel, am liebsten gleich zu oberst und
    # nicht versteckt in account... direkt über die search hin").
    bell_refs = build_pinned_bell(sidebar)
    build_pinned_search(sidebar)
    build_pinned_help(sidebar)
    sidebar.add_separator()

    sidebar.add_section_header("experiment_white.png", "Navigation", expanded=True)
    nav_refs = build_navigation_items(
        sidebar, offline_gated,
        access_level=access_level,
        on_all_experiments=None if hide_self_link == "all_experiments" else cb.get("on_all_experiments"),
        on_open_backlog=None if hide_self_link == "backlog" else cb.get("on_open_backlog"),
        on_open_experiment_request=cb.get("on_open_experiment_request"),
        on_create_experiment=cb.get("on_create_experiment"),
        on_create_experiment_legacy=cb.get("on_create_experiment_legacy"),
        on_add_series=cb.get("on_add_series"),
        on_add_lab_machines=cb.get("on_add_lab_machines"),
        on_preview_requests=cb.get("on_preview_requests"),
        on_preview_open_requests=cb.get("on_preview_open_requests"),
        open_in_new_tab=open_in_new_tab,
    )

    sidebar.add_separator()
    exp_req_group_refs = build_experiment_requests_group(
        sidebar,
        on_create_experiment_request=cb.get("on_create_experiment_request"),
        on_open_my_requests=cb.get("on_open_my_requests"),
        open_in_new_tab=open_in_new_tab,
    )

    sidebar.add_separator()
    build_tools_group(
        sidebar, offline_gated,
        access_level=access_level,
        on_image_compare=cb.get("on_image_compare"),
        on_canvas=cb.get("on_canvas"),
        on_nozzle_calculator=cb.get("on_nozzle_calculator"),
        on_air_supply=cb.get("on_air_supply"),
        on_requirement_hub=cb.get("on_requirement_hub"),
        on_smartchart=cb.get("on_smartchart"),
        on_yarn_stock=cb.get("on_yarn_stock"),
        on_label_generator=cb.get("on_label_generator"),
        on_tdms_inspector=cb.get("on_tdms_inspector"),
        open_in_new_tab=open_in_new_tab,
    )
    sidebar.add_separator()

    if access_level >= 1:
        build_admin_group(
            sidebar, offline_gated,
            on_add_jet=cb.get("on_add_jet"),
            on_add_top_plate=cb.get("on_add_top_plate"),
            on_add_yarn=cb.get("on_add_yarn"),
            on_manage_order_type=cb.get("on_manage_order_type"),
            on_manage_product_groups=cb.get("on_manage_product_groups"),
            on_manage_material=cb.get("on_manage_material"),
            open_in_new_tab=open_in_new_tab,
        )
        sidebar.add_separator()

    if access_level >= 4:
        build_superuser_group(
            sidebar, offline_gated,
            on_add_user=cb.get("on_add_user"),
            on_usage_stats=cb.get("on_usage_stats"),
            on_statistics=cb.get("on_statistics"),
            on_offline_sync=cb.get("on_offline_sync"),
            on_lab_assistant=cb.get("on_lab_assistant"),
            open_in_new_tab=open_in_new_tab,
        )
        sidebar.add_separator()

    sidebar.add_stretch()

    utility_refs = build_utility_group(sidebar, on_logout=cb.get("on_logout"))

    sidebar.apply_collapse_state()
    apply_offline_gate(offline_gated)

    return {
        **bell_refs,
        **nav_refs,
        **exp_req_group_refs,
        **utility_refs,
        "offline_gated_buttons": offline_gated,
    }


def toggle_legacy_button(screen):
    """Zeigt/versteckt den Legacy-Experiment-Erstellen-Button auf `screen`
    (Ctrl+Shift+J, siehe ensure_legacy_reveal_shortcut())."""
    try:
        btn = getattr(screen, "_btn_legacy_create", None)
        if btn is not None:
            btn.setVisible(not btn.isVisible())
    except Exception:
        pass


def ensure_legacy_reveal_shortcut(screen):
    """Registriert einmalig (pro Screen-Instanz) den Ctrl+Shift+J-Shortcut,
    der `screen`s eigenen Legacy-Import-Button umschaltet.

    WICHTIG (2026-08-27, Nutzerfrage: "haben wir da nicht ein Problem mit
    anderen, identischen geheimen Tastenkombinationen (z.B. YarnScope)?"):
    bewusst EIN lokaler QShortcut PRO SCREEN (Default-Kontext
    `Qt.WindowShortcut`, wie zuvor nur auf HomeScreen), NICHT ein einziger
    App-weiter `Qt.ApplicationShortcut`-Shortcut in MainWindow - Grund:
    `ui/screen_aty_batch.py`/`ui/screen_tdms_batch.py` haben je ihren
    EIGENEN, unabhängigen "Ctrl+Shift+J"-Shortcut (Insider-Modus, ein
    komplett anderes Feature, das zufällig dieselbe Tastenkombination
    nutzt). Ein `ApplicationShortcut`-Kontext ist IMMER erreichbar,
    unabhängig davon, welcher Screen gerade sichtbar ist - sobald der
    Nutzer auf ATY-/TDMS-Batch ist, wären dann zwei Shortcuts mit
    identischer Tastenkombination gleichzeitig erreichbar ("ambiguous
    shortcut", Qt feuert dann KEINEN von beiden, das Insider-Modus-Ei würde
    stillschweigend kaputtgehen). Mit `Qt.WindowShortcut` (Default) ist ein
    Shortcut nur erreichbar, während sein Trägerwidget tatsächlich sichtbar
    ist (bei ausgeblendeten Stack-/Tab-Seiten nicht) - da zu jedem Zeitpunkt
    nur GENAU EIN Screen sichtbar ist (ob per Stack oder Tab), gibt es so
    nie mehr als einen gleichzeitig erreichbaren "Ctrl+Shift+J"-Shortcut,
    unabhängig davon, wie viele Screens/Tabs insgesamt existieren.

    `hasattr`-Guard verhindert eine zweite, sich selbst überlappende
    Registrierung auf demselben Screen, falls dieser Rumpf (z.B. nach
    Logout+Login mit anderem Access-Level) mehrfach durchläuft."""
    if hasattr(screen, "_sc_legacy_reveal"):
        return
    from PySide6.QtGui import QShortcut, QKeySequence
    screen._sc_legacy_reveal = QShortcut(QKeySequence("Ctrl+Shift+J"), screen)
    screen._sc_legacy_reveal.activated.connect(lambda s=screen: toggle_legacy_button(s))


def refresh_sidebar_badges(screen):
    """Aktualisiert nur die drei Zähl-Badges (Backlog/Open-Requests/
    Approved-Requests) auf einem Screen, dessen Sidebar-Inhalt sich seit dem
    letzten Aufbau nicht geändert hat (Access-Level unverändert) - der
    "else"-Zweig in jedem Screen's _refresh_sidebar()/refresh_lazy_sidebar()."""
    refresh_badge(getattr(screen, "_backlog_badge", None), get_backlog_count())
    refresh_badge(getattr(screen, "_exp_req_badge", None), get_open_experiment_request_count())
    refresh_badge(getattr(screen, "_approved_exp_req_badge", None), get_approved_experiment_request_count())
    refresh_badge(getattr(screen, "_my_requests_badge", None), get_pending_request_changes_count())


def refresh_lazy_sidebar(screen, access_level: int, *, hide_self_link: Optional[str] = None):
    """Vollständiger Sidebar-Refresh-Rumpf für einen einzelnen Screen: baut
    die Sidebar komplett neu, falls sich `access_level` seit dem letzten
    Aufbau geändert hat (gespeichert in `screen._sidebar_built_for_level`),
    sonst nur die drei Zähl-Badges. Erwartet `screen._sidebar` (SidebarPanel)
    und `screen._sidebar_nav_callbacks` (dict, siehe main.py::
    _sidebar_nav_kwargs()) als bereits gesetzte Attribute. Speichert alle
    Refs (Backlog-/Experiment-Request-/Bell-Badges, offline_gated_buttons)
    direkt auf `screen` - Aufrufer aus `showEvent()`, `access_level` dabei
    jeweils selbst frisch aus app_meta.current_user gelesen (Screens werden
    typischerweise VOR dem ersten Login gebaut, der tatsächliche Level ist
    zum Konstruktionszeitpunkt daher noch nicht bekannt)."""
    if access_level != getattr(screen, "_sidebar_built_for_level", None):
        screen._sidebar_built_for_level = access_level
        screen._sidebar.clear_content()
        refs = install_full_sidebar(
            screen._sidebar, screen._sidebar_nav_callbacks,
            access_level=access_level, hide_self_link=hide_self_link)
        screen._backlog_badge = refs["backlog_badge"]
        screen._exp_req_badge = refs["exp_req_badge"]
        screen._approved_exp_req_badge = refs["approved_exp_req_badge"]
        screen._my_requests_badge = refs["my_requests_badge"]
        screen._bell_button = refs["bell_button"]
        screen._bell_badge = refs["bell_badge"]
        screen._offline_gated_buttons = refs["offline_gated_buttons"]
        screen._btn_legacy_create = refs["legacy_button"]
        ensure_legacy_reveal_shortcut(screen)
    else:
        refresh_sidebar_badges(screen)
