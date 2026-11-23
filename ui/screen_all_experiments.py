# ui/screen_all_experiments.py
"""Screen zur Anzeige aller Experimente (AllExperimentsScreen).

Zeigt alle TrialSeries / Experimente in einer Tabelle mit Filter, Sortierung
und direktem Status-Management.

Funktionen:
  - Alle Experimente laden und tabellarisch anzeigen
  - Filter nach Maschine, Status, Serie, Suchtext
  - Status direkt in der Tabelle ändern (Combobox, nur für berechtigte Benutzer)
  - Experiment öffnen (Doppelklick oder Button)
  - Experiment-Request-Popup öffnen (ER-Icon)
  - Anhänge-Indikator (Büroklammer-Icon)
  - Notizen-Indikator

Zugriffssteuerung:
  - ``can_review``: Benutzer darf Status-Änderungen vornehmen
  - ``_effective_access_level()``: berücksichtigt app_meta.current_user

Datenbankbezug:
  tblExperimente, tblTrialSeries, tblTrial, tblBacklog, tblExperimentRequests
"""

# ui/screen_all_experiments.py
import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QTableWidget, QTableWidgetItem, QSizePolicy, QSpacerItem, QAbstractItemView,
    QLineEdit, QComboBox, QMessageBox, QDialog, QMenu, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap

from db.connection import (
    fetch_experiments_with_series,
    fetch_all,
    execute,
    get_user_access_level,
    update_trialseries_name,
)
from db.trial_reference import exclude_references_sql
import app_meta  # enthält current_user
from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from ui.pathutil import resource_path
from ui.screen_create_experiment import table_exists, get_columns_map, resolve_field
from ui.screen_show_experiment import _ExperimentRequestReadOnlyDialog
from ui.widgets.friendly_error import show_error

_ER_ICON_PIXMAP = None  # cached QPixmap

_ATTACH_ICON_PIXMAP = None  # cached QPixmap

_NOTES_ICON_PIXMAP = None  # cached QPixmap

_REPORT_ICON_PIXMAP = None  # cached QPixmap


def _get_report_icon_pixmap() -> "QPixmap | None":
    """Lädt das Report-Icon (dasselbe wie der Smart-Chart-Button in Show
    Experiment) als QPixmap (lazy, gecacht)."""
    global _REPORT_ICON_PIXMAP
    if _REPORT_ICON_PIXMAP is not None:
        return _REPORT_ICON_PIXMAP
    from pathlib import Path
    candidates = [
        resource_path('assets/images/analytics.png'),
        resource_path('analytics.png'),
    ]
    for p in candidates:
        try:
            if p and Path(p).exists():
                pm = QPixmap(str(p))
                if not pm.isNull():
                    _REPORT_ICON_PIXMAP = pm.scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    return _REPORT_ICON_PIXMAP
        except Exception:
            continue
    _REPORT_ICON_PIXMAP = None
    return None


def _get_notes_icon_pixmap() -> QPixmap | None:
    """Lädt das Notizen-Icon als QPixmap (lazy, gecacht)."""
    """Loads and caches the Notes icon (scaled)."""
    global _NOTES_ICON_PIXMAP
    if _NOTES_ICON_PIXMAP is not None:
        return _NOTES_ICON_PIXMAP
    from pathlib import Path
    candidates = [
        resource_path('notes.png'),
        resource_path('ui/notes.png'),
        resource_path('ui/icons/notes.png'),
        resource_path('assets/images/notes.png'),
        resource_path('assets/notes.png'),
    ]
    for p in candidates:
        try:
            if p and Path(p).exists():
                pm = QPixmap(str(p))
                if not pm.isNull():
                    _NOTES_ICON_PIXMAP = pm.scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    return _NOTES_ICON_PIXMAP
        except Exception:
            continue
    _NOTES_ICON_PIXMAP = None
    return None


def _get_er_icon_pixmap() -> QPixmap | None:
    """Lädt das ExperimentRequest-Icon als QPixmap (lazy, gecacht)."""
    """Loads and caches the Experiment Request icon as QPixmap (scaled)."""
    global _ER_ICON_PIXMAP
    if _ER_ICON_PIXMAP is not None:
        return _ER_ICON_PIXMAP
    candidates = [
        resource_path('experiment_request.png'),
        resource_path('ui/experiment_request.png'),
        resource_path('ui/icons/experiment_request.png'),
        resource_path('ui/assets/experiment_request.png'),
        resource_path('assets/experiment_request.png'),
        resource_path('assets/images/experiment_request.png'),
    ]
    from pathlib import Path
    for p in candidates:
        try:
            if p and Path(p).exists():
                pm = QPixmap(str(p))
                if not pm.isNull():
                    _ER_ICON_PIXMAP = pm.scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    return _ER_ICON_PIXMAP
        except Exception:
            continue
    _ER_ICON_PIXMAP = None
    return None


def _get_attach_icon_pixmap() -> QPixmap | None:
    """Lädt das Anhänge-Icon als QPixmap (lazy, gecacht)."""
    """Loads and caches the attachment icon (scaled)."""
    global _ATTACH_ICON_PIXMAP
    if _ATTACH_ICON_PIXMAP is not None:
        return _ATTACH_ICON_PIXMAP
    candidates = [
        resource_path('attach.png'),
        resource_path('ui/attach.png'),
        resource_path('ui/icons/attach.png'),
        resource_path('ui/assets/attach.png'),
        resource_path('ui/assets/images/attach.png'),
        resource_path('Fassets/images/attach.png'),
        resource_path('assets/attach.png'),
        resource_path('assets/images/attach.png'),
    ]
    from pathlib import Path
    for p in candidates:
        try:
            if p and Path(p).exists():
                pm = QPixmap(str(p))
                if not pm.isNull():
                    _ATTACH_ICON_PIXMAP = pm.scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    return _ATTACH_ICON_PIXMAP
        except Exception:
            continue
    _ATTACH_ICON_PIXMAP = None
    return None


class _ClickableLabel(QLabel):
    """QLabel das Mausklick-Events weitergibt (für Icons in Tabellenzellen).

    `on_ctrl_click` (optional): called instead of `on_click` when Ctrl is
    held during the click - falls back to `on_click` if not given (user
    request 2026-09-01: Ctrl+click on the RE icon opens SmartChart in a new
    tab instead of the shared singleton, see
    _open_report_icon_for_series())."""

    def __init__(self, on_click=None, on_ctrl_click=None, parent=None):
        super().__init__(parent)
        self._on_click = on_click
        self._on_ctrl_click = on_ctrl_click
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        try:
            if event.button() == Qt.LeftButton:
                ctrl_held = bool(event.modifiers() & Qt.ControlModifier)
                if ctrl_held and callable(self._on_ctrl_click):
                    self._on_ctrl_click()
                    return
                if callable(self._on_click):
                    self._on_click()
                    return
        except Exception:
            pass
        return super().mousePressEvent(event)


class AllExperimentsScreen(QWidget):
    def __init__(self, on_back_home, on_open_experiment, on_copy_trialseries=None, can_review: bool = False,
                 on_open_in_new_window=None,
                 # Report-Symbol ("RE"-Spalte, 2026-08-27, Nutzerwunsch) -
                 # öffnet den Smart-Chart-Report-Screen direkt (mit Auswahl-
                 # Dialog bei mehreren Reports zur selben TrialSeries), siehe
                 # _open_report_icon_for_series()/ui/widgets/report_picker.py.
                 on_open_report=None,
                 # Ctrl+click on the RE icon (2026-09-01, user request: be
                 # able to have multiple SmartChart instances) - opens a
                 # fresh SmartChart instance in a new tab instead of the
                 # shared singleton.
                 on_open_report_in_new_tab=None,
                 # Sidebar-Navigation (siehe ui/widgets/sidebar_nav.py, geteilt mit
                 # HomeScreen/BacklogScreen) - dieselben Callbacks wie bei
                 # BacklogScreen, siehe dort für die Begründung des Musters
                 # (Access-Level erst zur Laufzeit über app_meta bekannt, Sidebar
                 # daher lazy in showEvent() aufgebaut statt hier).
                 on_open_backlog=None, on_create_experiment=None, on_create_experiment_legacy=None,
                 on_add_series=None, on_add_lab_machines=None, on_open_experiment_request=None,
                 on_create_experiment_request=None, on_open_my_requests=None,
                 on_preview_requests=None, on_preview_open_requests=None,
                 on_image_compare=None, on_canvas=None, on_nozzle_calculator=None, on_air_supply=None,
                 on_requirement_hub=None, on_smartchart=None, on_yarn_stock=None, on_label_generator=None,
                 on_tdms_inspector=None,
                 on_yarnscope_live=None,
                 on_add_jet=None, on_add_top_plate=None, on_add_yarn=None,
                 on_manage_order_type=None, on_manage_product_groups=None, on_manage_material=None, on_manage_projects=None,
                 on_add_user=None, on_usage_stats=None, on_offline_sync=None,
                 on_lab_assistant=None,
                 # Log-Out-Callback für die Sidebar-Account-Gruppe (Ersatz für
                 # den früheren Header-Log-Out-Button, der nur auf Home
                 # existierte - siehe screen_home.py::_build_ui()-Docstring).
                 on_logout=None,
                 # Ctrl+Klick "in neuem Tab öffnen" (siehe ui/widgets/tab_container.py)
                 open_in_new_tab=None,
                 # Rechtsklick "Open in New Window" (2026-08-27, Nutzerwunsch:
                 # Ctrl-Logik bleibt unangetastet und öffnet weiterhin einen
                 # Tab - dieser separate Menüpunkt öffnet stattdessen ein
                 # echtes, eigenständiges OS-Fenster, siehe
                 # main.py::open_experiment_in_new_window()).
                 on_open_in_new_os_window=None):
        super().__init__()
        self.on_back_home = on_back_home
        self.on_open_experiment = on_open_experiment
        self.on_copy_trialseries = on_copy_trialseries
        self.on_open_in_new_window = on_open_in_new_window
        self.on_open_in_new_os_window = on_open_in_new_os_window
        self.on_open_report = on_open_report
        self.on_open_report_in_new_tab = on_open_report_in_new_tab
        self._series_report_map: dict = {}

        self._sidebar_nav_callbacks = dict(
            on_open_backlog=on_open_backlog,
            on_create_experiment=on_create_experiment,
            on_create_experiment_legacy=on_create_experiment_legacy,
            on_add_series=on_add_series,
            on_add_lab_machines=on_add_lab_machines,
            on_open_experiment_request=on_open_experiment_request,
            on_create_experiment_request=on_create_experiment_request,
            on_open_my_requests=on_open_my_requests,
            on_preview_requests=on_preview_requests,
            on_preview_open_requests=on_preview_open_requests,
            on_image_compare=on_image_compare,
            on_canvas=on_canvas,
            on_nozzle_calculator=on_nozzle_calculator,
            on_air_supply=on_air_supply,
            on_requirement_hub=on_requirement_hub,
            on_smartchart=on_smartchart,
            on_yarn_stock=on_yarn_stock,
            on_label_generator=on_label_generator,
            on_tdms_inspector=on_tdms_inspector,
            on_yarnscope_live=on_yarnscope_live,
            on_add_jet=on_add_jet,
            on_add_top_plate=on_add_top_plate,
            on_add_yarn=on_add_yarn,
            on_manage_order_type=on_manage_order_type,
            on_manage_product_groups=on_manage_product_groups,
            on_manage_material=on_manage_material,
            on_manage_projects=on_manage_projects,
            on_add_user=on_add_user,
            on_usage_stats=on_usage_stats,
            on_offline_sync=on_offline_sync,
            on_lab_assistant=on_lab_assistant,
            on_logout=on_logout,
            open_in_new_tab=open_in_new_tab,
        )
        self._sidebar_built_for_level = None
        self._offline_gated_buttons: list = []

        # Maschinenfilter-Map
        from db.series_overview import MACHINE_FILTERS   # gemeinsam mit der Web-App
        self._filter_map = dict(MACHINE_FILTERS)
        self._filter_buttons = []
        self._active_filter = "All"

        # Textfilter
        self._series_filter = ""  # filtert "Trial Series Name"
        self._expid_filter = ""  # filtert "Experiment ID"
        self._concl_filter = ""  # "", "any", "none" or an outcome key (db/series_conclusion.py)

        # Sortierung
        # 0 = Experiment ID, 1 = Trial Series Name, 2 = Machine,
        # 3 = Creation Date, 4 = Owner, 5 = Status, 6 = AM, 7 = ER, 8 = NT
        self._sort_column = 3
        self._sort_order_ascending = False

        # Rechte / Status-Lookup
        self._can_review = bool(can_review)

        # AccessLevel global aus app_meta.current_user lesen
        self._access_level = 0
        try:
            user = getattr(app_meta, "current_user", {}) or {}
        except Exception:
            user = {}
        try:
            self._access_level = int(user.get("access_level") or 0)
        except Exception:
            self._access_level = 0

        self.status_name_to_id = {}
        self.status_id_to_name = {}
        self.status_names = []
        self._load_status_lookup()
        self._exp_req_field = self._resolve_experiment_request_field()

        self._original_status_ids = []

        self._build_ui()
        self._is_populating = False
        self._load_data()

    def _build_ui(self):
        """Erstellt Sidebar-Navigation, Filter-Toolbar, Tabelle und Footer.

        Keine TopBar (HeaderBar) mehr (2026-08-26, siehe screen_home.py::
        _build_ui()-Docstring) - Glocke/Suche/Accent-Farbe/Log Out sitzen
        jetzt in der Sidebar-Account-Gruppe.
        """
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar-Navigation (siehe ui/widgets/sidebar.py + sidebar_nav.py,
        # geteilt mit allen anderen Screens) - Inhalt bleibt hier leer, wird
        # lazy beim ersten showEvent() befüllt (access_level ist zum
        # Zeitpunkt dieses Konstruktoraufrufs noch nicht bekannt).
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        center = QFrame()
        clay = QVBoxLayout(center)
        clay.setContentsMargins(24, 48, 24, 24)
        clay.setSpacing(0)

        card = QFrame(objectName="Card")
        # Volle Fensterbreite (Nutzerwunsch 2026-10-13: vorher fest 1400-1680 px
        # zentriert - bei ueblichen Fenstern war die letzte Spalte RE nur per
        # horizontalem Scrollen sichtbar). Die Spalte "Trial Series Name"
        # nimmt den restlichen Platz ein (siehe Stretch-Modus unten).
        card.setMinimumWidth(900)
        cardlay = QVBoxLayout(card)
        cardlay.setContentsMargins(0, 0, 0, 0)
        cardlay.setSpacing(0)

        # Card Header
        chead = QFrame(objectName="CardHeader")
        chead_lay = QHBoxLayout(chead)
        chead_lay.setContentsMargins(12, 4, 12, 4)
        chead_title = QLabel("Experiments")
        chead_title.setStyleSheet(
            "color: white; font-weight: bold; font-size: 14px;")
        chead_lay.addWidget(chead_title)
        # Kontext-Hilfe EN/DE/ES (Nutzerwunsch 2026-10-13, ui/widgets/multilang_help.py) -
        # links neben dem Titel (urspruenglich, weil der Kasten frueher breiter
        # als viele Fenster war - seit 2026-10-13 nutzt er die Fensterbreite).
        from ui.widgets.multilang_help import make_help_button
        chead_lay.addWidget(make_help_button("How does All Experiments work?", self._open_help))
        chead_lay.addStretch(1)
        cardlay.addWidget(chead)

        # Filter-Buttons
        filters_wrap = QFrame(objectName="FiltersBar")
        filters_wrap.setMinimumHeight(44)
        filters = QHBoxLayout(filters_wrap)
        filters.setContentsMargins(18, 8, 18, 4)
        filters.setSpacing(8)

        order = ["All", "AFK", "eAFK", "Aalidhra",
                 "Zinser", "SSM DP2T", "SSM Xeno"]
        for text in order:
            btn = QPushButton(text, objectName="FilterBtn")
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.clicked.connect(lambda checked=False,
                                       name=text: self._on_filter(name))
            self._filter_buttons.append(btn)
            filters.addWidget(btn)

        for b in self._filter_buttons:
            if b.text() == "All":
                b.setChecked(True)
                break

        filters.addSpacerItem(QSpacerItem(
            10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        cardlay.addWidget(filters_wrap)

        # ---- Textboxen zum Filtern (Experiment ID 30%, Trial Series Name 70%) ----
        filter_line_wrap = QFrame()
        flay = QHBoxLayout(filter_line_wrap)
        flay.setContentsMargins(18, 0, 18, 6)
        flay.setSpacing(8)

        # Experiment-ID-Filter (30%)
        self.expid_filter_le = QLineEdit()
        self.expid_filter_le.setPlaceholderText("Filter Experiment ID…")
        self.expid_filter_le.textChanged.connect(self._on_expid_filter_change)
        flay.addWidget(self.expid_filter_le, stretch=3)

        # Seriennamen-Filter (70%)
        self.series_filter_le = QLineEdit()
        self.series_filter_le.setPlaceholderText("Filter Trial Series Name…")
        self.series_filter_le.textChanged.connect(
            self._on_series_filter_change)
        flay.addWidget(self.series_filter_le, stretch=7)

        # Conclusion filter (db/series_conclusion.py)
        from PySide6.QtWidgets import QComboBox as _QComboBox
        from db import series_conclusion as _sc
        self.concl_filter_cb = _QComboBox()
        self.concl_filter_cb.addItem("Conclusion: all", "")
        self.concl_filter_cb.addItem("With conclusion", "any")
        self.concl_filter_cb.addItem("Without conclusion", "none")
        for _k in _sc.OUTCOMES:
            self.concl_filter_cb.addItem(_sc.OUTCOME_LABELS[_k], _k)
        self.concl_filter_cb.currentIndexChanged.connect(self._on_concl_filter_change)
        self.concl_filter_cb.setVisible(_sc.table_ready())
        flay.addWidget(self.concl_filter_cb, stretch=0)

        # Copy TrialSeries Button
        self.butCopyTS = QPushButton("Copy TrialSeries")
        self.butCopyTS.setEnabled(False)
        self.butCopyTS.clicked.connect(self._on_copy_trialseries)
        flay.addWidget(self.butCopyTS, stretch=0)

        cardlay.addWidget(filter_line_wrap)
        # ---------------------------------------------------------------------------------------

        # Tabelle
        self.table = QTableWidget(0, 12, parent=self)
        self.table.setObjectName("ExpTable")
        self.table.setHorizontalHeaderLabels(
            ["Experiment ID", "Trial Series Name", "Machine", "Creation Date", "Owner", "Status", "AM", "ER", "NT", "RE",
             "Outcome", "Conclusion"]   # last two: db/series_conclusion.py (2026-11-14)
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(False)
        # Trial Series Name fuellt die verfuegbare Breite (mind. 200 px), alle
        # anderen Spalten behalten ihre festen Breiten - siehe _fit_name_column().
        # Bewusst kein QHeaderView.Stretch: das schrumpft die Spalte bei schmalen
        # Fenstern bis auf wenige Pixel (unlesbar); so kommt dann lieber der
        # horizontale Scrollbalken zurueck.
        self.table.viewport().installEventFilter(self)
        # Basis fuer die groessenabhaengige Skalierung (siehe _update_scale)
        self._scale = 1.0
        self._base_row_h = self.table.verticalHeader().defaultSectionSize()
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        # Hoehe folgt dem Fenster (Nutzerwunsch 2026-10-13); vorher fest min. 650 px.
        self.table.setMinimumHeight(250)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.table.itemSelectionChanged.connect(
            self._on_table_selection_changed
        )

        # Right-click context menu
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(
            self._on_table_context_menu)

        # Header-Klick zum Sortieren (A-Z / Z-A)
        header_view = self.table.horizontalHeader()
        header_view.sectionClicked.connect(self._on_header_clicked)
        header_view.setSortIndicatorShown(True)
        header_view.setSortIndicator(
            self._sort_column, Qt.SortOrder.AscendingOrder)

        table_wrap = QFrame()
        table_wrap_lay = QVBoxLayout(table_wrap)
        table_wrap_lay.setContentsMargins(18, 12, 18, 18)
        table_wrap_lay.addWidget(self.table)

        cardlay.addWidget(table_wrap, 1)
        clay.addWidget(card, 1)

        content_layout.addWidget(center, 1)
        root.addWidget(FooterBar())

    def showEvent(self, event):
        """Baut/aktualisiert die Sidebar-Navigation bei jedem Anzeigen (siehe
        _refresh_sidebar(), gleiches Muster wie BacklogScreen)."""
        try:
            self._refresh_sidebar()
        except Exception:
            pass
        super().showEvent(event)

    def _refresh_sidebar(self):
        """Baut die Sidebar-Navigation neu auf, falls sich der Access-Level
        seit dem letzten Aufbau geändert hat (siehe BacklogScreen._refresh_sidebar()
        für die ausführliche Begründung des Musters). Aktualisiert sonst nur
        die Badges. Rumpf in ui/widgets/sidebar_nav.py::refresh_lazy_sidebar()
        ausgelagert (2026-08-27, App-weiter Sidebar-Rollout);
        `hide_self_link="all_experiments"` unterdrückt den eigenen
        "All Experiments"-Sprungziel-Eintrag."""
        sidebar_nav.refresh_lazy_sidebar(
            self, self._effective_access_level(), hide_self_link="all_experiments")

    def _load_data(self, maschine_id: int | None = None):
        """Lädt alle Experiment-/Seriendaten aus der DB und befüllt die Tabelle.

        Args:
            maschine_id: Optional – filtert nach einer bestimmten Maschine.
        """
        # Daten holen (gemeinsam mit der Web-App: db/series_overview.py)
        from db import series_overview
        try:
            rows = series_overview.all_experiments_rows(maschine_id, getattr(self, '_exp_req_field', None))
        except Exception as e:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("DB error"))
            self.table.setItem(0, 1, QTableWidgetItem(""))
            self.table.setItem(0, 2, QTableWidgetItem(str(e)))
            return

        # Bulk-Lookup: welche TrialSeries haben gespeicherte Smart-Chart-
        # Reports (RE-Icon-Spalte, 2026-08-27)
        self._series_report_map = series_overview.series_report_map()
        from db import series_conclusion
        self._conclusion_map = series_conclusion.summary_map() if series_conclusion.table_ready() else {}
        cf = getattr(self, "_concl_filter", "")
        if cf:
            def _keep_c(rec):
                c = self._conclusion_map.get(rec.get("series_id_pk"))
                if cf == "any":
                    return c is not None
                if cf == "none":
                    return c is None
                return bool(c) and c.get("outcome") == cf
            rows = [r for r in rows if _keep_c(r)]

        # Textfilter anwenden
        sf = (self._series_filter or "").strip().lower()
        ef = (self._expid_filter or "").strip().lower()

        if sf or ef:
            def _keep(rec):
                # Series-Name contains
                name = (rec.get("series_name") or "").lower()
                ok_series = (sf in name) if sf else True
                # Experiment-ID contains
                expid = str(rec.get("experiment_id") or "").lower()
                ok_expid = (ef in expid) if ef else True
                return ok_series and ok_expid

            rows = [r for r in rows if _keep(r)]

        # Sortierung anwenden
        def _sort_key(rec):
            col = self._sort_column
            try:
                if col == 0:  # Experiment ID
                    return rec.get("experiment_id") or ""
                elif col == 1:  # Trial Series Name
                    return (rec.get("series_name") or "").lower()
                elif col == 2:  # Machine
                    machine_name = rec.get("maschine") or rec.get("machine") or ""
                    return machine_name.lower()
                elif col == 3:  # Creation Date
                    creation = rec.get("creation_date")
                    return "" if creation is None else str(creation)
                elif col == 4:  # Owner
                    return "" if rec.get("owner") is None else str(rec.get("owner")).lower()
                elif col == 5:  # Status
                    try:
                        return int(rec.get("backlog_status_id") or 0)
                    except Exception:
                        return 0
                elif col == 6:  # AM
                    return 1 if rec.get('has_attach') else 0
                elif col == 7:  # ER
                    v = rec.get("experiment_request_id")
                    return 0 if v in (None, '', 0, '0') else 1
                elif col == 8:  # NT
                    return 1 if rec.get('has_notes') else 0
                elif col == 9:  # RE
                    return 1 if self._series_report_map.get(rec.get("series_id_pk")) else 0
                elif col in (10, 11):  # Outcome / Conclusion
                    c = self._conclusion_map.get(rec.get("series_id_pk")) or {}
                    if col == 10:
                        from db.series_conclusion import OUTCOMES
                        o = c.get("outcome")
                        return OUTCOMES.index(o) + 1 if o in OUTCOMES else (9 if c else 99)
                    return (c.get("summary") or "").lower()
            except Exception:
                return 0
            return 0

        rows = sorted(

            rows,
            key=_sort_key,
            reverse=not self._sort_order_ascending
        )

        self._is_populating = True
        self.table.setRowCount(0)
        try:
            self.butCopyTS.setEnabled(False)
        except Exception:
            pass
        self._row_payload = []
        # Reviewed wurde aus der Logik entfernt.
        self._original_status_ids = []

        # Tabelle füllen
        for rec in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)

            # Grundspalten
            item_expid = QTableWidgetItem(str(rec["experiment_id"]))
            self.table.setItem(r, 0, item_expid)

            self.table.setItem(r, 1, QTableWidgetItem(rec.get("series_name") or ""))
            machine_name = rec.get("maschine") or rec.get("machine") or ""
            self.table.setItem(r, 2, QTableWidgetItem(machine_name))

            creation = rec.get("creation_date")
            owner = rec.get("owner")
            status_id = rec.get("backlog_status_id")
            self.table.setItem(r, 3, QTableWidgetItem("" if creation is None else str(creation)))
            self.table.setItem(r, 4, QTableWidgetItem("" if owner is None else str(owner)))

            # Status-Dropdown (analog Backlog)
            combo = self._create_status_combobox(status_id)
            combo.currentIndexChanged.connect(
                lambda _idx, row=r, cb=combo: self._on_status_combo_changed(row, cb)
            )
            self.table.setCellWidget(r, 5, combo)

            # Attachment (Image and/or PDF) - not clickable
            self._set_attach_cell(r, 6, bool(rec.get('has_attach')))

            # Experiment Request Icon
            er_id = rec.get('experiment_request_id')
            self._set_er_cell(r, 7, er_id)

            # Notes icon
            self._set_notes_cell(r, 8, bool(rec.get('has_notes')))

            # Report icon (RE) - 2026-08-27
            self._set_report_cell(r, 9, rec.get("series_id_pk"))

            # Conclusion (db/series_conclusion.py): coloured outcome + summary
            c = self._conclusion_map.get(rec.get("series_id_pk"))
            from db.series_conclusion import OUTCOME_COLOURS, OUTCOME_LABELS
            it_o = QTableWidgetItem(("● " + OUTCOME_LABELS.get(c.get("outcome"), "")) if c and c.get("outcome") else ("●" if c else ""))
            if c:
                it_o.setForeground(QColor(OUTCOME_COLOURS.get(c.get("outcome") or "open", "#8a94a0")))
            self.table.setItem(r, 10, it_o)
            it_s = QTableWidgetItem((c or {}).get("summary") or "")
            it_s.setToolTip((c or {}).get("summary") or "")
            self.table.setItem(r, 11, it_s)

            # Payload für spätere Navigation
            self._row_payload.append(
                (rec["exp_id_pk"], rec["series_id_pk"], rec["experiment_id"])
            )
            self._original_status_ids.append(status_id)

        # Spaltenbreiten
        self._apply_column_widths()

        # Sortindikator im Header aktualisieren
        header_view = self.table.horizontalHeader()
        order = Qt.SortOrder.AscendingOrder if self._sort_order_ascending else Qt.SortOrder.DescendingOrder
        header_view.setSortIndicator(self._sort_column, order)

        self._is_populating = False

    def _on_cell_double_clicked(self, row, col):
        """Doppelklick: normal öffnen; Ctrl+Doppelklick: neues Fenster."""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt as _Qt
        modifiers = QApplication.keyboardModifiers()
        if modifiers & _Qt.KeyboardModifier.ControlModifier:
            self._open_in_new_window(row)
        else:
            self._open_selected(row, col)

    def _open_in_new_window(self, row):
        """Öffnet die TrialSeries in Zeile row in einem neuen Fenster."""
        if not callable(getattr(self, "on_open_in_new_window", None)):
            return
        if row is None or row < 0:
            row = self.table.currentRow()
        if row < 0 or row >= len(getattr(self, "_row_payload", []) or []):
            return
        exp_pk, series_pk, experiment_id = self._row_payload[row]
        try:
            exp_pk = int(exp_pk)
        except Exception:
            pass
        try:
            series_pk = int(series_pk)
        except Exception:
            pass
        self.on_open_in_new_window(exp_pk, series_pk, experiment_id)

    def _open_in_new_os_window(self, row):
        """Öffnet die TrialSeries in Zeile row in einem echten, eigenständigen
        OS-Fenster (Rechtsklick-Kontextmenü "Open in New Window", 2026-08-27,
        Nutzerwunsch) - im Gegensatz zu _open_in_new_window() (Ctrl+Doppelklick,
        öffnet einen Tab), die auf ausdrücklichen Wunsch unangetastet bleibt."""
        if not callable(getattr(self, "on_open_in_new_os_window", None)):
            return
        if row is None or row < 0:
            row = self.table.currentRow()
        if row < 0 or row >= len(getattr(self, "_row_payload", []) or []):
            return
        exp_pk, series_pk, experiment_id = self._row_payload[row]
        try:
            exp_pk = int(exp_pk)
        except Exception:
            pass
        try:
            series_pk = int(series_pk)
        except Exception:
            pass
        self.on_open_in_new_os_window(exp_pk, series_pk, experiment_id)

    def _open_selected(self, row, col):
        """Öffnet das in Zeile row ausgewählte Experiment."""
        # QTableWidget kann (je nach Widget/Delegate) komische Row-Werte liefern.
        # Zur Sicherheit auch currentRow() verwenden.
        if row is None or row < 0:
            row = self.table.currentRow()

        if row < 0 or row >= len(getattr(self, "_row_payload", []) or []):
            return

        if not callable(getattr(self, "on_open_experiment", None)):
            return

        exp_pk, series_pk, experiment_id = self._row_payload[row]
        try:
            exp_pk = int(exp_pk)
        except Exception:
            pass
        try:
            series_pk = int(series_pk)
        except Exception:
            pass

        try:
            self.on_open_experiment(exp_pk, series_pk, experiment_id)
        except Exception as e:
            try:
                show_error(self, "Error opening", "The experiment could not be opened.", e, details=f"ExperimentID: {experiment_id} · ExpPK: {exp_pk} / SeriesPK: {series_pk}")
            except Exception:
                pass

    def _on_header_clicked(self, logical_index: int):
        """Sortiert die Tabelle nach der geklickten Spalte (Toggle asc/desc)."""
        """
        Wird aufgerufen, wenn im Tabellen-Header eine Spalte angeklickt wird.
        - Klick auf dieselbe Spalte: Sortierreihenfolge toggeln (ASC <-> DESC)
        - Klick auf andere Spalte: aufsteigend nach neuer Spalte sortieren
        """
        if logical_index == self._sort_column:
            # Gleiche Spalte -> Richtung wechseln
            self._sort_order_ascending = not self._sort_order_ascending
        else:
            # Neue Spalte -> aufsteigend starten
            self._sort_column = logical_index
            self._sort_order_ascending = True

        maschine_id = self._filter_map.get(self._active_filter, None)
        self._load_data(maschine_id)

    def _on_save_status_clicked(self):
        """Speichert alle geänderten Status-Werte in der DB."""
        """Speichert alle geänderten Backlog-Status (Dropdown) in die Datenbank."""
        errors = []
        row_payload = list(getattr(self, "_row_payload", []))
        original = list(getattr(self, "_original_status_ids", []))

        user_id = self._get_effective_user_id()
        is_super = self._effective_access_level() >= 4

        for row, payload in enumerate(row_payload):
            if not payload or len(payload) < 2:
                continue
            _, series_pk, _ = payload
            try:
                w = self.table.cellWidget(row, 5)
            except Exception:
                w = None
            if not isinstance(w, QComboBox):
                continue
            new_id = w.currentData()
            old_id = original[row] if row < len(original) else None
            if old_id is None or new_id == old_id:
                continue

            # Statuswechsel-Regel:
            # - Ausnahme: Wenn ein Item aktuell im Backlog ist (old_id == 1), dürfen alle Write-User (AccessLevel >= 2) den Change status.
            # - Sonst dürfen Statusänderungen nur durch den Owner (Spalte 'Owner') oder einen Superuser erfolgen.
            access_level = self._effective_access_level()
            if access_level < 2:
                # Read-Only -> zurücksetzen und als Fehler zählen
                if old_id is not None:
                    idx2 = w.findData(old_id)
                    if idx2 >= 0:
                        w.blockSignals(True)
                        w.setCurrentIndex(idx2)
                        w.blockSignals(False)
                errors.append((row, PermissionError("No write permission (read-only).")))
                continue

            current_username = self._effective_username()
            try:
                owner_username = (self.table.item(row, 4).text() if self.table.item(row, 4) else "")
            except Exception:
                owner_username = ""
            owner_username = str(owner_username).strip().lower()
            is_owner = bool(current_username) and bool(owner_username) and (current_username == owner_username)

            # Ausnahme: "To Be Cleaned" (4) -> "Archived" (5) darf von JEDEM Write-User
            # (AccessLevel >= 2) ausgeführt werden, unabhängig vom Owner.
            is_tbc_to_archived = (old_id == 4 and new_id == 5 and access_level >= 2)

            if old_id != 1 and not (is_owner or is_super or is_tbc_to_archived):
                if old_id is not None:
                    idx2 = w.findData(old_id)
                    if idx2 >= 0:
                        w.blockSignals(True)
                        w.setCurrentIndex(idx2)
                        w.blockSignals(False)
                errors.append((row, PermissionError(
                    "Only the owner or a superuser may change the status (exception: Backlog for write users)."
                )))
                continue

            # Sicherheitsnetz: Wechsel nach/von Archived (ID 5) und TBC (ID 4) nur für Superuser.
            # Ausnahme: "To Be Cleaned" -> "Archived" ist für alle Write-User erlaubt.
            if (old_id in (4, 5) or new_id in (4, 5)) and not is_super and not is_tbc_to_archived:
                # Änderung nicht erlaubt -> zurücksetzen
                if old_id is not None:
                    idx = w.findData(old_id)
                    if idx >= 0:
                        w.blockSignals(True)
                        w.setCurrentIndex(idx)
                        w.blockSignals(False)
                self._notify("warning", "Change status",
                             "Only superusers may set or remove the 'Archived' or 'To Be Cleaned' status.")
                continue

            # no conclusion yet -> ask before archiving (db/series_conclusion.py)
            if new_id == 5 and not self._confirm_archive_without_conclusion(series_pk):
                if old_id is not None:
                    idx = w.findData(old_id)
                    if idx >= 0:
                        w.blockSignals(True)
                        w.setCurrentIndex(idx)
                        w.blockSignals(False)
                continue

            # Wenn wir von Backlog (1) auf einen anderen Status wechseln und die Serie
            # aktuell eine Joker-Maschine hat, muss zuerst eine Nicht-Joker-Maschine
            # gewählt werden.
            new_machine_id = None
            if old_id == 1 and new_id != 1:
                try:
                    if self._series_has_joker_machine(series_pk):
                        dlg = MachineSelectionDialog(self)
                        if dlg.exec() != QDialog.Accepted:
                            # User hat abgebrochen -> Statuswechsel zurücksetzen
                            if old_id is not None:
                                idx = w.findData(old_id)
                                if idx >= 0:
                                    w.blockSignals(True)
                                    w.setCurrentIndex(idx)
                                    w.blockSignals(False)
                            continue
                        new_machine_id = dlg.get_selected_machine_id()
                        if new_machine_id is None:
                            # Sicherheitshalber ebenfalls abbrechen
                            if old_id is not None:
                                idx = w.findData(old_id)
                                if idx >= 0:
                                    w.blockSignals(True)
                                    w.setCurrentIndex(idx)
                                    w.blockSignals(False)
                            continue
                except Exception as e:
                    # Im Fehlerfall lieber gar nichts ändern
                    if old_id is not None:
                        idx = w.findData(old_id)
                        if idx >= 0:
                            w.blockSignals(True)
                            w.setCurrentIndex(idx)
                            w.blockSignals(False)
                    self._notify("critical", "Change status", f"An error occurred while checking the machine:\n{e}")
                    continue

            try:
                self._update_backlog_status(
                    series_pk, new_id, old_id, user_id, new_machine_id)
                if row < len(original):
                    original[row] = new_id
            except Exception as e:
                errors.append((row, e))

        # Aktualisierten Original-Status zurückspeichern
        self._original_status_ids = original

        if errors:
            first_row, first_err = errors[0]
            self._notify("critical", "Save status",
                         f"{len(errors)} row(s) could not be saved.\n"
                         f"First error (row {first_row + 1}):\n{first_err}")
        else:
            self._notify("info", "Save status", "All changed statuses were saved successfully.")

    def _notify(self, level: str, title: str, message: str):
        """Zeigt eine QMessageBox (info/warning/critical) an."""
        """Zeigt eine MessageBox, die zuverlässig im Vordergrund erscheint.

        level: 'info' | 'warning' | 'critical'
        """
        m = QMessageBox(self)
        m.setWindowTitle(title)
        m.setText(message)
        m.setTextFormat(Qt.PlainText)
        m.setStandardButtons(QMessageBox.Ok)
        m.setWindowModality(Qt.ApplicationModal)

        lvl = (level or "").lower().strip()
        if lvl == "critical":
            m.setIcon(QMessageBox.Critical)
        elif lvl == "warning":
            m.setIcon(QMessageBox.Warning)
        else:
            m.setIcon(QMessageBox.Information)

        try:
            m.raise_()
            m.activateWindow()
        except Exception:
            pass

        m.exec()

    def set_can_review(self, can_review: bool):
        """Aktiviert/deaktiviert Status-Bearbeitungs-Rechte zur Laufzeit."""
        """Legacy-Flag: wird für Status-Änderungen aktuell nicht mehr ausgewertet."""
        self._can_review = bool(can_review)

    # -------------------------------------------------

    def _on_status_combo_changed(self, row: int, combo):
        """Callback wenn eine Status-Combobox geändert wird; merkt die Änderung vor."""
        """Wird aufgerufen, wenn in einer Zeile der Status geändert wird.
        Speichert die Änderung sofort in der Datenbank (anstatt über 'Save Status')."""
        row_payload = list(getattr(self, "_row_payload", []))
        original = list(getattr(self, "_original_status_ids", []))
        if row < 0 or row >= len(row_payload) or row >= len(original):
            return

        payload = row_payload[row]
        if not payload or len(payload) < 2:
            return
        _, series_pk, _ = payload

        try:
            old_id = original[row]
        except Exception:
            old_id = None

        try:
            new_id = combo.currentData()
        except Exception:
            new_id = None

        # Nichts zu tun, wenn sich effektiv nichts geändert hat
        if old_id is None or new_id is None or new_id == old_id:
            return

        user_id = self._get_effective_user_id()
        is_super = self._effective_access_level() >= 4

        # Statuswechsel-Regel:
        # - Ausnahme: Wenn ein Item aktuell im Backlog ist (old_id == 1), dürfen alle Write-User (AccessLevel >= 2) den Change status.
        # - Sonst dürfen Statusänderungen nur durch den Owner (Spalte 'Owner') oder einen Superuser erfolgen.
        access_level = self._effective_access_level()
        if access_level < 2:
            # Read-Only -> zurücksetzen
            if old_id is not None:
                idx = combo.findData(old_id)
                if idx >= 0:
                    combo.blockSignals(True)
                    combo.setCurrentIndex(idx)
                    combo.blockSignals(False)
            self._notify("warning", "No permission", "You have no write permission (read-only).")
            return

        current_username = self._effective_username()
        try:
            owner_username = (self.table.item(row, 4).text() if self.table.item(row, 4) else "")
        except Exception:
            owner_username = ""
        owner_username = str(owner_username).strip().lower()

        is_owner = bool(current_username) and bool(owner_username) and (current_username == owner_username)

        # Ausnahme: "To Be Cleaned" (4) -> "Archived" (5) darf von JEDEM Write-User
        # (AccessLevel >= 2) ausgeführt werden, unabhängig vom Owner.
        is_tbc_to_archived = (old_id == 4 and new_id == 5 and access_level >= 2)

        if old_id != 1 and not (is_owner or is_super or is_tbc_to_archived):
            # Änderung nicht erlaubt -> zurücksetzen
            if old_id is not None:
                idx = combo.findData(old_id)
                if idx >= 0:
                    combo.blockSignals(True)
                    combo.setCurrentIndex(idx)
                    combo.blockSignals(False)
            self._notify("warning", "No permission",
                         "Status change not allowed.\n\nOnly the owner or a superuser may change the status.\n"
                         "Exception: While an item is in the Backlog, all write users may change the status.")
            return

        # Sicherheitsnetz: Wechsel nach/von Archived (ID 5) und TBC (ID 4) nur für Superuser.
        # Ausnahme: "To Be Cleaned" -> "Archived" ist für alle Write-User erlaubt.
        if (old_id in (4, 5) or new_id in (4, 5)) and not is_super and not is_tbc_to_archived:
            # Änderung nicht erlaubt -> zurücksetzen
            if old_id is not None:
                idx = combo.findData(old_id)
                if idx >= 0:
                    combo.blockSignals(True)
                    combo.setCurrentIndex(idx)
                    combo.blockSignals(False)
            self._notify("warning", "Change status",
                         "Only superusers may set or remove the 'Archived' or 'To Be Cleaned' status.")
            return

        # no conclusion yet -> ask before archiving (db/series_conclusion.py)
        if new_id == 5 and not self._confirm_archive_without_conclusion(series_pk):
            if old_id is not None:
                idx = combo.findData(old_id)
                if idx >= 0:
                    combo.blockSignals(True)
                    combo.setCurrentIndex(idx)
                    combo.blockSignals(False)
            return

        # Wenn wir von Backlog (1) auf einen anderen Status wechseln und die Serie
        # aktuell eine Joker-Maschine hat, muss zuerst eine Nicht-Joker-Maschine
        # gewählt werden.
        new_machine_id = None
        if old_id == 1 and new_id != 1:
            try:
                if self._series_has_joker_machine(series_pk):
                    dlg = MachineSelectionDialog(self)
                    if dlg.exec() != QDialog.Accepted:
                        # User hat abgebrochen -> Statuswechsel zurücksetzen
                        if old_id is not None:
                            idx = combo.findData(old_id)
                            if idx >= 0:
                                combo.blockSignals(True)
                                combo.setCurrentIndex(idx)
                                combo.blockSignals(False)
                        return
                    new_machine_id = dlg.get_selected_machine_id()
                    if new_machine_id is None:
                        # Keine Maschine ausgewählt -> ebenfalls zurücksetzen
                        if old_id is not None:
                            idx = combo.findData(old_id)
                            if idx >= 0:
                                combo.blockSignals(True)
                                combo.setCurrentIndex(idx)
                                combo.blockSignals(False)
                        return
            except Exception as e:
                # Im Fehlerfall lieber gar nichts ändern
                if old_id is not None:
                    idx = combo.findData(old_id)
                    if idx >= 0:
                        combo.blockSignals(True)
                        combo.setCurrentIndex(idx)
                        combo.blockSignals(False)
                show_error(self, "Change status", "The machine could not be checked.", e)
                return

        # Änderung in die Datenbank schreiben
        try:
            self._update_backlog_status(
                series_pk, new_id, old_id, user_id, new_machine_id)
        except Exception as e:
            # Fehler -> zurücksetzen
            if old_id is not None:
                idx = combo.findData(old_id)
                if idx >= 0:
                    combo.blockSignals(True)
                    combo.setCurrentIndex(idx)
                    combo.blockSignals(False)
            self._notify("critical", "Save status", f"The status change could not be saved:\n{e}")
            return

        # Erfolgreich -> Original-Statusid aktualisieren
        try:
            original[row] = new_id
            self._original_status_ids = original
        except Exception:
            # Im Zweifel lieber nur schweigend weitermachen
            self._original_status_ids = original

    # STATUS-LOOKUP & HILFSFUNKTIONEN (analog Backlog)
    # -------------------------------------------------

    def _resolve_experiment_request_field(self) -> str | None:
        """Ermittelt den FK-Feldnamen für ExperimentRequest in tblExperimente (versionstolerant)."""
        """Finds the column in tblExperimente that stores a linked Experiment Request ID."""
        try:
            if not table_exists('tblExperimente'):
                return None
            cols = get_columns_map('tblExperimente')
            return resolve_field(
                ['ExperimentRequest', 'Experiment Request', 'ExperimentRequestID', 'ExperimentRequestId'],
                cols,
            )
        except Exception:
            return None

    def open_experiment_request_popup(self, request_id):
        """Öffnet ein Read-Only-Popup mit den Daten eines ExperimentRequests."""
        if request_id in (None, '', 0, '0'):
            return
        try:
            dlg = _ExperimentRequestReadOnlyDialog(self, request_id)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def _set_attach_cell(self, row: int, col: int, has_attach: bool):
        """Setzt das Anhänge-Icon in einer Tabellenzelle (oder leert sie)."""
        """Sets AM (attachment) icon cell widget if image and/or pdf exists.

        Icon is purely visual and not clickable.
        """
        if not has_attach:
            self.table.setItem(row, col, QTableWidgetItem(""))
            return
        pm = _get_attach_icon_pixmap()
        if pm is None or pm.isNull():
            self.table.setItem(row, col, QTableWidgetItem("AM"))
            return
        lbl = QLabel()
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setToolTip("Has attachments")
        lbl.setPixmap(pm)
        self.table.setCellWidget(row, col, lbl)

    def _set_er_cell(self, row: int, col: int, request_id):
        """Setzt das ER-Icon (ExperimentRequest) in einer Tabellenzelle."""
        """Sets ER icon cell widget if request exists."""
        if request_id in (None, '', 0, '0'):
            # empty
            self.table.setItem(row, col, QTableWidgetItem(""))
            return
        pm = _get_er_icon_pixmap()
        if pm is None or pm.isNull():
            self.table.setItem(row, col, QTableWidgetItem("ER"))
            return

        def _open():
            self.open_experiment_request_popup(request_id)

        lbl = _ClickableLabel(on_click=_open)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setToolTip("Open Experiment Request")
        lbl.setPixmap(pm)
        self.table.setCellWidget(row, col, lbl)

    def _set_notes_cell(self, row: int, col: int, has_notes: bool):
        """Setzt das Notizen-Icon in einer Tabellenzelle."""
        """Sets NT (Notes) icon cell widget if Notes field is non-empty."""
        if not has_notes:
            self.table.setItem(row, col, QTableWidgetItem(""))
            return
        pm = _get_notes_icon_pixmap()
        if pm is None or pm.isNull():
            self.table.setItem(row, col, QTableWidgetItem("NT"))
            return
        lbl = QLabel()
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setToolTip("Has notes")
        lbl.setPixmap(pm)
        self.table.setCellWidget(row, col, lbl)

    def _set_report_cell(self, row: int, col: int, series_pk) -> None:
        """Setzt das RE-Icon (Report) in einer Tabellenzelle - nur sichtbar,
        wenn für diese TrialSeries mind. ein gespeicherter Smart-Chart-Report
        existiert (siehe self._series_report_map, gefüllt in _load_data())."""
        try:
            has_report = bool(self._series_report_map.get(int(series_pk))) if series_pk else False
        except Exception:
            has_report = False
        if not has_report:
            self.table.setItem(row, col, QTableWidgetItem(""))
            return
        pm = _get_report_icon_pixmap()
        if pm is None or pm.isNull():
            self.table.setItem(row, col, QTableWidgetItem("RE"))
            return

        def _open():
            self._open_report_icon_for_series(series_pk)

        def _open_ctrl():
            self._open_report_icon_for_series(series_pk, in_new_tab=True)

        lbl = _ClickableLabel(on_click=_open, on_ctrl_click=_open_ctrl)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setToolTip("Open saved Smart Chart report (Ctrl+Click: new tab)")
        lbl.setPixmap(pm)
        self.table.setCellWidget(row, col, lbl)

    def _open_report_icon_for_series(self, series_pk, in_new_tab: bool = False) -> None:
        """Klick auf das RE-Icon: bei genau einem gespeicherten Report direkt
        öffnen, bei mehreren einen kleinen Auswahl-Dialog zeigen (siehe
        ui/widgets/report_picker.py). Ctrl+click (`in_new_tab`) opens a
        fresh SmartChart instance in a new tab instead of the shared
        singleton - falls back to the normal callback if
        on_open_report_in_new_tab isn't wired up."""
        if not series_pk:
            return
        callback = self.on_open_report_in_new_tab if (in_new_tab and callable(self.on_open_report_in_new_tab)) else self.on_open_report
        if not callable(callback):
            return
        from ui.widgets.report_picker import choose_report_for_series
        report_id = choose_report_for_series(self, series_pk)
        if report_id is not None:
            callback(series_pk, report_id)

    def _load_status_lookup(self):
        """Lädt den Status-Lookup aus tblBacklogStatus für die Comboboxen."""
        sql = """
              SELECT [ID], [BacklogStatus]
              FROM tblBacklogStatus
              ORDER BY [ID]; \
              """
        try:
            rows = fetch_all(sql, [])
        except Exception:
            rows = [
                {"ID": 1, "BacklogStatus": "Backlog"},
                {"ID": 2, "BacklogStatus": "In Progress"},
                {"ID": 3, "BacklogStatus": "Done"},
                {"ID": 4, "BacklogStatus": "To Be Cleaned"},
                {"ID": 5, "BacklogStatus": "Archived"},
            ]

        self.status_name_to_id = {r["BacklogStatus"]: r["ID"] for r in rows}
        self.status_id_to_name = {r["ID"]: r["BacklogStatus"] for r in rows}
        self.status_names = [r["BacklogStatus"] for r in rows]

    def _effective_access_level(self) -> int:
        """Gibt den AccessLevel des aktuellen Benutzers zurück (aus app_meta)."""
        """Ermittelt den effektiven AccessLevel.

        Priorität:
        1) globaler Wert aus app_meta.current_user["access_level"]
        2) DB-Fallback über get_user_access_level(username)
        3) lokaler Wert aus __init__
        """
        try:
            user = getattr(app_meta, "current_user", {}) or {}
        except Exception:
            user = {}

        # Globaler Wert hat Priorität
        try:
            if "access_level" in user:
                return int(user.get("access_level") or 0)
        except Exception:
            pass

        # Fallback: Username-basiert prüfen
        username = user.get("username") or user.get(
            "Username") or user.get("user")
        if username:
            try:
                return int(get_user_access_level(username) or 0)
            except Exception:
                pass

        # Letztes Sicherheitsnetz: lokaler Wert
        try:
            return int(getattr(self, "_access_level", 0) or 0)
        except Exception:
            return 0

    def _effective_username(self) -> str:
        """Gibt den Benutzernamen des aktuellen Benutzers zurück."""
        """Ermittelt den effektiven Username (kleingeschrieben, ohne Leerzeichen)."""
        try:
            user = getattr(app_meta, "current_user", {}) or {}
            uname = user.get("username")
            return (str(uname).strip().lower() if uname is not None else "")
        except Exception:
            return ""

    def _get_effective_user_id(self):
        """Gibt die User-ID des aktuellen Benutzers zurück."""
        try:
            return app_meta.current_user.get("id")
        except Exception:
            return None

    def _create_status_combobox(self, current_id):
        """Erstellt eine Status-Combobox mit dem aktuellen Wert vorselektiert."""
        combo = QComboBox(self.table)

        combo.blockSignals(True)
        combo.clear()

        access_level = self._effective_access_level()
        is_super = access_level >= 4
        is_write_user = access_level >= 2

        # Liste der Status je nach Rolle aufbauen
        if is_super:
            # Superuser → komplette Liste
            for name in self.status_names:
                status_id = self.status_name_to_id.get(name)
                combo.addItem(name, status_id)
        elif current_id == 4 and is_write_user:
            # Write-User in "To Be Cleaned": einzige erlaubte Statusänderung ist
            # der Wechsel nach "Archived" -> nur diese beiden Optionen anzeigen.
            for name in self.status_names:
                status_id = self.status_name_to_id.get(name)
                if status_id in (4, 5):
                    combo.addItem(name, status_id)
        else:
            # Nicht-Superuser sehen Archived (5) und To Be Cleaned (4) nicht.
            for name in self.status_names:
                status_id = self.status_name_to_id.get(name)
                if status_id in (4, 5):
                    continue
                combo.addItem(name, status_id)

        if current_id is not None:
            idx = combo.findData(current_id)
            if idx >= 0:
                combo.setCurrentIndex(idx)

        combo.blockSignals(False)

        # Dropdown-Sperrlogik für Nicht-Superuser:
        # - "Archived" (5) ist und bleibt für Nicht-Superuser gesperrt (kein Zurücksetzen).
        # - "To Be Cleaned" (4) darf von Write-Usern (AccessLevel >= 2) nach
        #   "Archived" verschoben werden -> Dropdown bleibt für sie aktiv.
        if is_super:
            combo.setEnabled(True)
        elif current_id == 5:
            combo.setEnabled(False)
        elif current_id == 4:
            combo.setEnabled(is_write_user)
        else:
            combo.setEnabled(True)

        # AccessLevel == 1: Status darf nie geändert werden -> alle Dropdowns deaktivieren
        try:
            if access_level == 1:
                combo.setEnabled(False)
        except Exception:
            pass
        return combo

    def _series_has_joker_machine(self, series_id) -> bool:
        """Gibt True zurück wenn die Serie eine Joker-Maschine (Platzhalter) hat."""
        from db.backlog_moves import series_has_joker_machine   # gemeinsam mit Backlog + Web-App
        return series_has_joker_machine(series_id)

    def _confirm_archive_without_conclusion(self, series_pk) -> bool:
        """Moving to Archived without a conclusion: ask (a hint, not a block). True = go on."""
        from db import series_conclusion
        try:
            missing = series_conclusion.missing_for_archive(int(series_pk))
        except Exception:
            missing = False
        if not missing:
            return True
        return QMessageBox.question(
            self, "No conclusion yet",
            "This series has no conclusion yet (tab \"Conclusion\" in Show Experiment).\n\nArchive it anyway?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes

    def _update_backlog_status(self, series_id, new_status, old_status, user_id, new_machine_id=None):
        """Schreibt einen geänderten Status - dieselbe Funktion wie das Backlog (db/backlog_moves.py,
        seit 2026-11-13; vorher fehlten hier der Timestamp-Fallback bei "Done" und die
        Retest-Freigabe bei "To Be Cleaned")."""
        from db import backlog_moves
        backlog_moves.update_backlog_status(series_id, new_status, old_status, user_id, new_machine_id)
        backlog_moves.after_move(series_id, new_status, user_id)

    def _on_filter(self, name: str):
        """Aktiviert einen vordefinierten Filter (Maschinengruppe o.ä.)."""
        self._active_filter = name
        maschine_id = self._filter_map.get(name, None)
        self._load_data(maschine_id)

    def _on_series_filter_change(self, text: str):
        """Aktualisiert den Freitext-Filter für Serien-/Experiment-Namen."""
        """Filtert 'Trial Series Name' (contains, case-insensitive)."""
        self._series_filter = text or ""
        maschine_id = self._filter_map.get(self._active_filter, None)
        self._load_data(maschine_id)

    def _on_concl_filter_change(self, *_):
        """Conclusion filter: all / with / without / one outcome."""
        self._concl_filter = self.concl_filter_cb.currentData() or ""
        maschine_id = self._filter_map.get(self._active_filter, None)
        self._load_data(maschine_id)

    def _on_expid_filter_change(self, text: str):
        """Filtert 'Experiment ID' (contains, case-insensitive)."""
        self._expid_filter = text or ""
        maschine_id = self._filter_map.get(self._active_filter, None)
        self._load_data(maschine_id)

    def _on_table_selection_changed(self):
        has_sel = False
        try:
            sel = self.table.selectedIndexes()
            has_sel = bool(sel)
        except Exception:
            has_sel = False
        try:
            self.butCopyTS.setEnabled(has_sel)
        except Exception:
            pass

    _NAME_COL_MIN = 200
    # Feste Spaltenbreiten bei Massstab 1.0 (Spalte 0 nach Inhalt, Spalte 1 = Rest)
    _BASE_COL_WIDTHS = {2: 120, 3: 160, 4: 110, 5: 110, 6: 50, 7: 60, 8: 50, 9: 50, 10: 130, 11: 260}
    # Groessenabhaengige Darstellung (Nutzerwunsch 2026-10-13: "wenn wir genug
    # Platz haben, mach das ganze etwas groesser"): Massstab 1.0 bei einer
    # Tabellenbreite wie im 1600-px-Fenster, darueber in 5-%-Schritten bis
    # max. 1.35. Nie kleiner als bisher.
    _BASE_FONT_PX = 13          # wie QTableWidget#ExpTable in ui/theme.py
    _SCALE_REF_WIDTH = 1200
    _SCALE_MAX = 1.35

    def _apply_column_widths(self) -> None:
        t = getattr(self, "table", None)
        if t is None:
            return
        sc = getattr(self, "_scale", 1.0)
        t.resizeColumnToContents(0)
        for col, w in self._BASE_COL_WIDTHS.items():
            if col < t.columnCount():
                t.setColumnWidth(col, int(round(w * sc)))
        self._fit_name_column()

    def _update_scale(self) -> None:
        """Passt Schrift, Zeilenhoehe und Spaltenbreiten an die verfuegbare
        Tabellenbreite an. Die Schrift wird per Widget-Stylesheet gesetzt, weil
        das globale QSS (QTableWidget#ExpTable, font-size: 13px) setFont() sonst
        ueberschreibt."""
        t = getattr(self, "table", None)
        if t is None or not t.width():
            return
        raw = t.width() / self._SCALE_REF_WIDTH
        new = min(self._SCALE_MAX, max(1.0, round(raw / 0.05) * 0.05))
        if abs(new - getattr(self, "_scale", 1.0)) < 1e-6:
            return
        self._scale = new
        px = int(round(self._BASE_FONT_PX * new))
        t.setStyleSheet(
            f"QTableWidget#ExpTable {{ font-size: {px}px; }}"
            f"QHeaderView::section {{ font-size: {px}px; }}"
            f"QComboBox {{ font-size: {px}px; }}")
        t.verticalHeader().setDefaultSectionSize(int(round(self._base_row_h * new)))
        self._apply_column_widths()

    def _fit_name_column(self) -> None:
        """Gibt der Spalte "Trial Series Name" die restliche Breite der Tabelle
        (mindestens _NAME_COL_MIN), damit alle Spalten bis RE ohne horizontales
        Scrollen sichtbar sind."""
        t = getattr(self, "table", None)
        if t is None or t.columnCount() < 2:
            return
        others = sum(t.columnWidth(c) for c in range(t.columnCount()) if c != 1)
        avail = t.viewport().width() - others
        t.setColumnWidth(1, max(self._NAME_COL_MIN, avail))

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        t = getattr(self, "table", None)
        if t is not None and obj is t.viewport() and event.type() == QEvent.Resize:
            self._update_scale()
            self._fit_name_column()
        return super().eventFilter(obj, event)

    def _open_help(self):
        from ui.widgets.multilang_help import show_help
        from ui.widgets.help_texts_all_experiments import TEXTS
        show_help(TEXTS, self)

    def _on_copy_trialseries(self):
        # Guard
        if not callable(getattr(self, "on_copy_trialseries", None)):
            return
        row = self.table.currentRow()
        if row is None or row < 0 or row >= len(getattr(self, "_row_payload", [])):
            return
        exp_pk, series_pk, experiment_id = self._row_payload[row]
        try:
            self.on_copy_trialseries(exp_pk, series_pk, experiment_id)
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            show_error(self, "Copy TrialSeries", "The trial series could not be copied.", e)

    # ------------------------------------------------------------------
    # Context menu: rename Trial Series (AccessLevel >= 2)
    # ------------------------------------------------------------------

    def _on_table_context_menu(self, pos):
        """Right-click context menu for the table."""
        try:
            item = self.table.itemAt(pos)
        except Exception:
            item = None

        if item is None:
            return

        row = item.row()
        if row < 0 or row >= len(getattr(self, "_row_payload", [])):
            return

        # Ensure row becomes selected when right-clicking
        try:
            self.table.selectRow(row)
        except Exception:
            pass

        lvl = self._effective_access_level()
        can_rename = lvl >= 2
        # delete = whoever may move this series in the Backlog (recycle bin),
        # see db/series_permissions.py
        from db.series_permissions import can_delete_series_now
        try:
            can_delete = can_delete_series_now(self._row_payload[row][1])
        except Exception:
            can_delete = False
        can_reassign = lvl >= 4

        menu = QMenu(self)
        act_open_new = menu.addAction("↗  Open in New Tab")
        act_open_new.setEnabled(callable(getattr(self, "on_open_in_new_window", None)))
        act_open_new_window = menu.addAction("🗗  Open in New Window")
        act_open_new_window.setEnabled(callable(getattr(self, "on_open_in_new_os_window", None)))
        menu.addSeparator()
        act_rename = menu.addAction("Rename Trial Series…")
        act_rename.setEnabled(bool(can_rename))
        menu.addSeparator()
        act_yarn = menu.addAction("🧵  Reassign Yarn…")
        act_yarn.setEnabled(bool(can_reassign))
        act_machine = menu.addAction("⚙️  Change Machine…")
        act_machine.setEnabled(bool(can_reassign))
        act_delete = menu.addAction("🗑  Delete Trial Series…")
        act_delete.setEnabled(bool(can_delete))

        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen is None:
            return

        if chosen == act_open_new:
            self._open_in_new_window(row)
        elif chosen == act_open_new_window:
            self._open_in_new_os_window(row)
        elif chosen == act_rename:
            if not can_rename:
                QMessageBox.warning(
                    self,
                    "Permission denied",
                    "You do not have permission to rename a Trial Series.",
                )
                return
            self._rename_trialseries_at_row(row)
        elif chosen == act_yarn:
            if not can_reassign:
                QMessageBox.warning(
                    self,
                    "Permission denied",
                    "Only superusers may reassign yarn for a Trial Series.",
                )
                return
            self._reassign_yarn_at_row(row)
        elif chosen == act_machine:
            if not can_reassign:
                QMessageBox.warning(
                    self,
                    "Permission denied",
                    "Only superusers may change the machine for a Trial Series.",
                )
                return
            self._reassign_machine_at_row(row)
        elif chosen == act_delete:
            if not can_delete:
                QMessageBox.warning(
                    self,
                    "Permission denied",
                    "You do not have permission to delete a Trial Series.",
                )
                return
            self._delete_trialseries_at_row(row)

    def _reassign_machine_at_row(self, row: int):
        """Superuser: Maschine einer TrialSeries nachträglich ändern."""
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QComboBox, QLabel, QDialogButtonBox,
        )

        if row < 0 or row >= len(getattr(self, "_row_payload", [])):
            return

        exp_pk, series_pk, experiment_id = self._row_payload[row]
        series_id = series_pk

        try:
            series_name = (self.table.item(row, 1).text() or "").strip()
        except Exception:
            series_name = str(series_id)

        from db import series_actions   # Qt-free, shared with the Backlog + web

        # Aktuelle MachineID laden
        try:
            cur_machine_id, cur_machine_name = series_actions.current_machine(series_id)
        except Exception as e:
            show_error(self, "Error", "The machine data could not be loaded.", e)
            return

        # Alle Maschinen laden
        machines = series_actions.list_machines()

        if not machines:
            QMessageBox.information(self, "No Machines",
                                    "No machines found in database.")
            return

        machine_ids = [r["ID"] for r in machines]
        machine_names = [r["Maschine"] for r in machines]

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Change Machine — {series_name}")
        dlg.setMinimumWidth(420)
        lay = QVBoxLayout(dlg)

        lbl = QLabel(
            f"<b>{series_name}</b><br>"
            f"Current machine: <i>{cur_machine_name or '—'}</i>"
        )
        lbl.setWordWrap(True)
        lay.addWidget(lbl)

        cmb = QComboBox(dlg)
        cmb.addItems(machine_names)
        if cur_machine_id in machine_ids:
            cmb.setCurrentIndex(machine_ids.index(cur_machine_id))
        lay.addWidget(cmb)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dlg)
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        lay.addWidget(btn_box)

        if dlg.exec() != QDialog.Accepted:
            return

        new_idx = cmb.currentIndex()
        if new_idx < 0:
            return
        new_machine_id = machine_ids[new_idx]

        if new_machine_id == cur_machine_id:
            QMessageBox.information(self, "No Change",
                                    "The machine was not changed.")
            return

        try:
            # UPDATE + feature tracking: db/series_actions.change_machine
            series_actions.change_machine(series_id, new_machine_id, app_meta.current_user)
        except Exception as e:
            show_error(self, "Save Error", "The machine could not be saved.", e)
            return

        new_name = machine_names[new_idx]
        QMessageBox.information(
            self, "Machine Updated",
            f"Machine successfully changed to '{new_name}'."
        )

    def _reassign_yarn_at_row(self, row: int):
        """Superuser: Garn(e) einer TrialSeries nachträglich ändern.

        Unterstützt:
        - YarnID ändern pro Ply (direkt in tbltrialsettings)
        - Neues Ply hinzufügen (INSERT tblTrialSettings-Klon von Ply 1)
        - Ply löschen (DELETE tblTrialSettings-Zeilen mit diesem Ply-Label)
        - Mindestens 1 Ply muss erhalten bleiben
        - Ply-Labels werden nach Reihenfolge neu vergeben
        """
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem as _TWI,
            QComboBox, QDialogButtonBox, QLabel, QPushButton, QHeaderView,
        )
        from PySide6.QtCore import Qt

        if row < 0 or row >= len(getattr(self, "_row_payload", [])):
            return

        exp_pk, series_pk, experiment_id = self._row_payload[row]
        series_id = series_pk

        try:
            series_name = (self.table.item(row, 1).text() or "").strip()
        except Exception:
            series_name = str(series_id)

        # ── Aktuelle Garnzuordnung laden (via tbltrialsettings, DISTINCT pro Ply) ──
        from db import trial_actions   # Qt-free, shared by Backlog + All Experiments + web
        try:
            yarn_rows = trial_actions.series_ply_yarns(series_id)
        except Exception as e:
            show_error(self, "Error", "The yarn data could not be loaded.", e)
            return

        if not yarn_rows:
            QMessageBox.information(self, "No Yarn Data",
                                    "This Trial Series has no yarn entries.")
            return

        # ── Alle verfügbaren Garne laden ──────────────────────────────────
        # (no shadow yarns of the multi-machine ply link)
        all_yarns = trial_actions.reassign_yarn_choices()

        yarn_id_to_name = {int(r["ID"]): str(r["Name"]) for r in all_yarns}
        yarn_name_list = [str(r["Name"]) for r in all_yarns]
        yarn_id_list = [int(r["ID"]) for r in all_yarns]
        from ui.widgets.yarn_colour import colour_icon, colour_tooltip, load_yarn_colours
        yarn_colours, _ = load_yarn_colours()

        # ── Dialog aufbauen ───────────────────────────────────────────────
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Reassign Yarn — {series_name}")
        dlg.setMinimumWidth(600)
        dlg.setMinimumHeight(300)
        lay = QVBoxLayout(dlg)

        lbl = QLabel(
            f"<b>{series_name}</b><br>"
            "Select the correct yarn for each ply. "
            "Use ✕ to delete a ply, or '+ Add Ply' to add a new one."
        )
        lbl.setWordWrap(True)
        lay.addWidget(lbl)

        tbl = QTableWidget(0, 4, dlg)
        tbl.setHorizontalHeaderLabels(["Ply", "Current Yarn", "New Yarn", ""])
        hdr = tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.Fixed)
        tbl.setColumnWidth(3, 36)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setSelectionMode(QTableWidget.NoSelection)

        rows_state = []

        def _rebuild_ply_labels():
            vis_idx = 0
            for i, r in enumerate(rows_state):
                it = tbl.item(i, 0)
                if it is None:
                    continue
                if not r["deleted"]:
                    it.setText(f"Ply {vis_idx + 1}")
                    vis_idx += 1
                else:
                    it.setText("—")

        def _add_row(orig_ply, orig_yid, is_new=False):
            row_idx = tbl.rowCount()
            tbl.insertRow(row_idx)

            lbl_item = _TWI("")
            lbl_item.setFlags(Qt.ItemIsEnabled)
            tbl.setItem(row_idx, 0, lbl_item)

            cur_name = yarn_id_to_name.get(orig_yid, f"ID {orig_yid}") if orig_yid else "—"
            cur_item = _TWI(cur_name)
            cur_item.setFlags(Qt.ItemIsEnabled)
            if orig_yid:
                cur_item.setIcon(colour_icon(yarn_colours.get(orig_yid)))
                cur_item.setToolTip(colour_tooltip(yarn_colours.get(orig_yid)))
            tbl.setItem(row_idx, 1, cur_item)

            cmb = QComboBox()
            cmb.addItems(yarn_name_list)
            for _i, _yid in enumerate(yarn_id_list):
                cmb.setItemIcon(_i, colour_icon(yarn_colours.get(_yid)))
            if orig_yid and orig_yid in yarn_id_list:
                cmb.setCurrentIndex(yarn_id_list.index(orig_yid))
            elif yarn_id_list:
                cmb.setCurrentIndex(0)
            tbl.setCellWidget(row_idx, 2, cmb)

            btn_del = QPushButton("✕")
            btn_del.setFixedWidth(30)
            btn_del.setToolTip("Delete this ply")

            state = {"orig_ply": orig_ply, "orig_yid": orig_yid,
                     "cmb": cmb, "deleted": False, "is_new": is_new}
            rows_state.append(state)

            def _on_delete(checked=False, s=state, ri=row_idx):
                active = [r for r in rows_state if not r["deleted"]]
                if len(active) <= 1:
                    QMessageBox.warning(dlg, "Not possible",
                                        "At least one ply must remain.")
                    return
                s["deleted"] = True
                for col in range(tbl.columnCount()):
                    w = tbl.cellWidget(ri, col)
                    it = tbl.item(ri, col)
                    if w:
                        w.setEnabled(False)
                    if it:
                        it.setForeground(Qt.gray)
                btn_del.setEnabled(False)
                _rebuild_ply_labels()

            btn_del.clicked.connect(_on_delete)
            tbl.setCellWidget(row_idx, 3, btn_del)

        for r in yarn_rows:
            _add_row(str(r["Ply"]), int(r["YarnID"]) if r["YarnID"] else None)
        _rebuild_ply_labels()
        lay.addWidget(tbl)

        btn_add = QPushButton("+ Add Ply")

        def _on_add():
            first_active = next((r for r in rows_state if not r["deleted"]), None)
            default_yid = None
            if first_active:
                idx = first_active["cmb"].currentIndex()
                default_yid = yarn_id_list[idx] if idx >= 0 and yarn_id_list else None
            _add_row(orig_ply=None, orig_yid=default_yid, is_new=True)
            _rebuild_ply_labels()

        btn_add.clicked.connect(_on_add)
        lay.addWidget(btn_add)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dlg)
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        lay.addWidget(btn_box)

        if dlg.exec() != QDialog.Accepted:
            return

        # ── Plan (new ply labels, conflicts) + write: db/trial_actions ──
        rows = []
        for state in rows_state:
            idx = state["cmb"].currentIndex()
            rows.append({"orig_ply": state["orig_ply"], "orig_yid": state["orig_yid"],
                         "deleted": state["deleted"], "is_new": state["is_new"],
                         "new_yid": yarn_id_list[idx] if idx >= 0 and yarn_id_list else None})
        plan = trial_actions.plan_yarn_reassign(series_id, rows, yarn_id_to_name)

        if plan["conflicts"]:
            from PySide6.QtWidgets import QMessageBox as _QMB
            _QMB.critical(
                None, "Yarn Conflict", trial_actions.conflict_message(plan["conflicts"]))
            return

        try:
            changes_made = trial_actions.apply_yarn_reassign(series_id, plan, app_meta.current_user)
        except Exception as e:
            show_error(self, "Save Error", "The yarn data could not be saved.", e)
            return

        if changes_made:
            QMessageBox.information(
                self, "Yarn Updated",
                f"{changes_made} change(s) successfully saved."
            )
        else:
            QMessageBox.information(self, "No Change",
                                    "No changes were made.")

    def _delete_trialseries_at_row(self, row: int):
        """Superuser: delete a TrialSeries and all its children.

        Deletion order (FK-safe):
          tblLaborXXX            (via TrialID)
          tbllabortiter          (via TrialID)
          tblFeatureUsage        (via TrialID stored in ExtraInfo  → skipped if table absent)
          tblTrialSettings       (via TrialID, CASCADE via tblTrial)
          tblTrial               (via TrialSeriesID)
          tblTrialSeriesImage    (via TrialSeriesID, if table exists)
          tblTrialSeriesPDF      (via TrialSeriesID, if table exists)
          tblTrialSeries         (the series itself)
          tblExperimente         (only if no other TrialSeries remains for this experiment)
        """
        if row < 0 or row >= len(getattr(self, "_row_payload", [])):
            return

        exp_pk, series_pk, experiment_id = self._row_payload[row]

        # Series name for confirmation dialog
        try:
            series_name = (self.table.item(row, 1).text() or "").strip()
        except Exception:
            series_name = str(series_pk)

        # Security check against the current DB state (the menu may be old)
        from db.series_permissions import can_delete_series_now
        if not can_delete_series_now(series_pk):
            QMessageBox.warning(self, "Delete Trial Series",
                                "You may only delete a series that you are allowed to move in the Backlog "
                                "(e.g. as its owner). 'To Be Cleaned' and permanent deleting without recycle "
                                "bin: superusers only.")
            return

        # ── Confirmation dialog ────────────────────────────────────────────
        msg = QMessageBox(self)
        msg.setWindowTitle("Delete Trial Series")
        msg.setIcon(QMessageBox.Warning)
        from db import recycle_bin as _rb
        _bin = _rb.available()
        msg.setText(
            f"<b>Delete this Trial Series?</b><br><br>"
            f"<b>{series_name}</b><br><br>"
            f"This will delete all Trials, Lab data, and related records.<br>"
            + (f"A superuser can restore it from the <b>Recycle Bin</b> for {_rb.RETENTION_DAYS} days."
               if _bin else "<b>This action cannot be undone.</b>")
        )
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        msg.setDefaultButton(QMessageBox.Cancel)
        if msg.exec() != QMessageBox.Yes:
            return

        # ── Delete in FK-safe order ────────────────────────────────────────
        try:
            # Recycle bin (db/recycle_bin.py): copy + delete everything in one
            # transaction; the old direct delete below then finds nothing
            # left (only used offline / without the bin table).
            if _bin:
                _rb.delete_series(int(series_pk), series_name)
            # Collect all TrialIDs for this series
            trial_rows = fetch_all(
                "SELECT [ID] FROM [tblTrial] WHERE [TrialSeriesID] = ?",
                [series_pk],
            )
            trial_ids = [int(r["ID"]) for r in trial_rows]

            if trial_ids:
                placeholders = ",".join(["?"] * len(trial_ids))

                # Sicherheitsnetz: ALLE Tabellen mit einem FK auf tblTrial.ID
                # dynamisch aus dem DB-Schema ermitteln (statt sich nur auf
                # die von Hand gepflegte Liste unten zu verlassen) - genau
                # das Fehlen eines Eintrags dort (tblLaborATYoMat) hat den
                # urspruenglichen Fehler verursacht. Neue Labor-Tabellen mit
                # TrialID-FK werden dadurch automatisch erfasst, auch wenn
                # die Liste unten mal wieder nicht aktualisiert wird.
                try:
                    fk_tables = fetch_all(
                        "SELECT DISTINCT TABLE_NAME, COLUMN_NAME "
                        "FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
                        "WHERE REFERENCED_TABLE_SCHEMA = DATABASE() "
                        "AND REFERENCED_TABLE_NAME = 'tblTrial' "
                        "AND REFERENCED_COLUMN_NAME = 'ID'"
                    )
                except Exception:
                    fk_tables = []
                for row in fk_tables:
                    tbl = row.get("TABLE_NAME")
                    col = row.get("COLUMN_NAME")
                    if not tbl or not col or tbl.lower() == "tbltrial":
                        continue
                    try:
                        execute(
                            f"DELETE FROM [{tbl}] WHERE [{col}] IN ({placeholders})",
                            trial_ids,
                        )
                    except Exception:
                        pass  # bereits leer / Constraint-Sonderfall - Haupt-Liste unten faengt das ab

                # Labor tables (all linked via TrialID) - haendisch gepflegte
                # Liste, bleibt als Fallback/Dokumentation bestehen; die
                # dynamische Ermittlung oben ist mittlerweile der eigentliche
                # Schutz gegen "vergessene Tabelle".
                labor_tables = [
                    "tbllabortiter",
                    "tbllaborstatimatm",
                    "tbllaborstatimatds",
                    "tblLaborWaterbath",
                    "tblLaborItematLab",
                    "tblLaborItematPlus",
                    "tblLaborRapid600",
                    "tblLaborDTYoMat",
                    "tblLaborATYoMat",
                    "tblLaborEKB",
                    "tblLaborHeissLuftSchrumpf",
                    "tblLaborKochSchrumpf",
                    "tblLaborATYShrinkage",
                ]
                for tbl in labor_tables:
                    try:
                        execute(
                            f"DELETE FROM [{tbl}] WHERE [TrialID] IN ({placeholders})",
                            trial_ids,
                        )
                    except Exception:
                        pass  # table may not exist — skip silently

                # tblFeatureUsage: ExtraInfo stores series_pk (as string) for
                # series-level features; TrialID column may also be used.
                # Delete both series-level and trial-level entries.
                try:
                    execute(
                        f"DELETE FROM [tblFeatureUsage] WHERE [TrialID] IN ({placeholders})",
                        trial_ids,
                    )
                except Exception:
                    pass
                try:
                    execute(
                        "DELETE FROM [tblFeatureUsage] WHERE [ExtraInfo] = ?",
                        [str(series_pk)],
                    )
                except Exception:
                    pass

                # tblTrialSettings
                try:
                    execute(
                        f"DELETE FROM [tblTrialSettings] WHERE [TrialID] IN ({placeholders})",
                        trial_ids,
                    )
                except Exception:
                    pass

                # tblTrial
                execute(
                    "DELETE FROM [tblTrial] WHERE [TrialSeriesID] = ?",
                    [series_pk],
                )

            # tblTrialSeriesImage / tblTrialSeriesPDF (optional tables)
            for opt_tbl in ("tblTrialSeriesImage", "tblTrialSeriesPDF"):
                try:
                    execute(
                        f"DELETE FROM [{opt_tbl}] WHERE [TrialSeriesID] = ?",
                        [series_pk],
                    )
                except Exception:
                    pass

            # tblTrialSeries itself
            execute(
                "DELETE FROM [tblTrialSeries] WHERE [ID] = ?",
                [series_pk],
            )

            # tblExperimente: delete if this was the last TrialSeries
            try:
                remaining = fetch_all(
                    "SELECT COUNT(*) AS cnt FROM [tblTrialSeries] WHERE [ExperimentID] = ?",
                    [exp_pk],
                )
                if remaining and int((remaining[0].get("cnt") or 0)) == 0:
                    execute(
                        "DELETE FROM [tblExperimente] WHERE [ID] = ?",
                        [exp_pk],
                    )
            except Exception:
                pass

        except Exception as e:
            show_error(self, "Delete Trial Series", "The trial series could not be deleted.", e)
            return

        # ── Feature tracking ──────────────────────────────────────────────
        try:
            from db.connection import execute as _db_execute
            _db_execute(
                "INSERT INTO tblFeatureUsage (FeatureID, UserID, ExtraInfo) VALUES (?, ?, ?)",
                [6, getattr(app_meta, "current_user", {}).get("id") or getattr(app_meta, "current_user", {}).get("ID"),
                 str(series_pk)],
            )
        except Exception:
            pass

        # ── Remove row from UI ─────────────────────────────────────────────
        try:
            self.table.removeRow(row)
            del self._row_payload[row]
        except Exception:
            pass

    def _rename_trialseries_at_row(self, row: int):
        """Open the rename popup and persist the change."""
        if row < 0 or row >= self.table.rowCount():
            return
        if row < 0 or row >= len(getattr(self, "_row_payload", [])):
            return

        # Current full name from table
        try:
            current_full = (self.table.item(row, 1).text() or "").strip("\n")
        except Exception:
            current_full = ""

        prefix, editable = self._split_trialseries_prefix(current_full)

        dlg = RenameTrialSeriesDialog(
            self, prefix=prefix, current_name=editable)
        if dlg.exec() != QDialog.Accepted:
            return

        from db import series_actions   # Qt-free, shared with the Backlog + web
        new_full = series_actions.compose_name(prefix, dlg.new_name())
        if not new_full:
            # Empty -> keep old
            return

        # Persist to DB
        try:
            _exp_pk, series_pk, _experiment_id = self._row_payload[row]
        except Exception:
            series_pk = None

        if not series_pk:
            QMessageBox.critical(self, "Rename Trial Series",
                                 "Missing Trial Series ID.")
            return

        try:
            series_actions.rename_series(series_pk, new_full)
        except Exception as e:
            show_error(self, "Rename Trial Series", "The new name could not be saved.", e)
            return

        # Update UI cell
        try:
            self.table.item(row, 1).setText(new_full)
        except Exception:
            pass

    @staticmethod
    def _split_trialseries_prefix(full_name: str) -> tuple[str, str]:
        """Split a TrialSeries name into (prefix_to_keep, editable_part):
        db/series_actions.split_prefix (shared with the Backlog + web)."""
        from db.series_actions import split_prefix
        return split_prefix(full_name)


class RenameTrialSeriesDialog(QDialog):
    """Simple dialog (English) to rename the editable part of a TrialSeries name."""

    def __init__(self, parent=None, prefix: str = "", current_name: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Rename Trial Series")
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        info = QLabel("Enter the new Trial Series name.")
        lay.addWidget(info)

        if prefix:
            pref = QLabel(f"Prefix (kept): <b>{prefix}</b>")
            pref.setTextFormat(Qt.RichText)
            lay.addWidget(pref)

        self._edit = QLineEdit()
        self._edit.setPlaceholderText("New name…")
        self._edit.setText(current_name or "")
        self._edit.selectAll()
        lay.addWidget(self._edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_cancel)

        self._btn_ok = QPushButton("OK")
        self._btn_ok.setDefault(True)
        self._btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(self._btn_ok)

        lay.addLayout(btn_row)

    def new_name(self) -> str:
        return self._edit.text()


class MachineSelectionDialog(QDialog):
    """Dialog zur Auswahl einer Nicht-Joker-Maschine.

    Wird verwendet, wenn eine TrialSeries von Backlog auf einen anderen Status
    gesetzt werden soll, aber aktuell eine Joker-Maschine zugewiesen ist.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select machine")
        self.setModal(True)

        self._combo = QComboBox(self)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Please select a machine (no joker):"))
        layout.addWidget(self._combo)

        btn_row = QHBoxLayout()
        self._but_ok = QPushButton("OK", self)
        self._but_cancel = QPushButton("Cancel", self)
        self._but_ok.clicked.connect(self.accept)
        self._but_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self._but_ok)
        btn_row.addWidget(self._but_cancel)
        layout.addLayout(btn_row)

        self._load_machines()

    def _load_machines(self):
        sql = """
              SELECT [ID], [Maschine]
              FROM tblMaschine
              WHERE [IsJoker] = 0 OR [IsJoker] IS NULL
              ORDER BY [Maschine]; \
              """
        try:
            rows = fetch_all(sql, [])
        except Exception:
            rows = []
        self._combo.clear()
        for r in rows:
            self._combo.addItem(str(r.get("Maschine") or ""), r.get("ID"))

    def get_selected_machine_id(self):
        idx = self._combo.currentIndex()
        if idx < 0:
            return None
        return self._combo.currentData()