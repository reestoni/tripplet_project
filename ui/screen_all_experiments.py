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
    QLineEdit, QComboBox, QMessageBox, QDialog, QMenu
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from db.connection import (
    fetch_experiments_with_series,
    fetch_all,
    execute,
    get_user_access_level,
    update_trialseries_name,
)
import app_meta  # enthält current_user
from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from ui.pathutil import resource_path
from ui.screen_create_experiment import table_exists, get_columns_map, resolve_field
from ui.screen_show_experiment import _ExperimentRequestReadOnlyDialog

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
    """QLabel das Mausklick-Events weitergibt (für Icons in Tabellenzellen)."""

    def __init__(self, on_click=None, parent=None):
        super().__init__(parent)
        self._on_click = on_click
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        try:
            if event.button() == Qt.LeftButton and callable(self._on_click):
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
                 on_add_jet=None, on_add_top_plate=None, on_add_yarn=None,
                 on_manage_order_type=None, on_manage_product_groups=None, on_manage_material=None,
                 on_add_user=None, on_usage_stats=None, on_statistics=None, on_offline_sync=None,
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
            on_add_jet=on_add_jet,
            on_add_top_plate=on_add_top_plate,
            on_add_yarn=on_add_yarn,
            on_manage_order_type=on_manage_order_type,
            on_manage_product_groups=on_manage_product_groups,
            on_manage_material=on_manage_material,
            on_add_user=on_add_user,
            on_usage_stats=on_usage_stats,
            on_statistics=on_statistics,
            on_offline_sync=on_offline_sync,
            on_lab_assistant=on_lab_assistant,
            on_logout=on_logout,
            open_in_new_tab=open_in_new_tab,
        )
        self._sidebar_built_for_level = None
        self._offline_gated_buttons: list = []

        # Maschinenfilter-Map
        self._filter_map = {
            "All": None,
            "AFK": 2,
            "eAFK": 1,
            "Aalidhra": 6,
            "Zinser": 3,
            "SSM DP2T": 4,
            "SSM Xeno": 5,
        }
        self._filter_buttons = []
        self._active_filter = "All"

        # Textfilter
        self._series_filter = ""  # filtert "Trial Series Name"
        self._expid_filter = ""  # filtert "Experiment ID"

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
        clay.setContentsMargins(0, 48, 0, 0)
        clay.setSpacing(0)

        card = QFrame(objectName="Card")
        card.setMaximumWidth(1680)  # +40%
        card.setMinimumWidth(1400)
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

        # Copy TrialSeries Button
        self.butCopyTS = QPushButton("Copy TrialSeries")
        self.butCopyTS.setEnabled(False)
        self.butCopyTS.clicked.connect(self._on_copy_trialseries)
        flay.addWidget(self.butCopyTS, stretch=0)

        cardlay.addWidget(filter_line_wrap)
        # ---------------------------------------------------------------------------------------

        # Tabelle
        self.table = QTableWidget(0, 10, parent=self)
        self.table.setObjectName("ExpTable")
        self.table.setHorizontalHeaderLabels(
            ["Experiment ID", "Trial Series Name", "Machine", "Creation Date", "Owner", "Status", "AM", "ER", "NT", "RE"]
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(650)  # +25%
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

        cardlay.addWidget(table_wrap)
        clay.addWidget(card, 0, Qt.AlignHCenter | Qt.AlignTop)

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
        # Daten holen (ggf. Maschinenfilter bereits DB-seitig)
        try:
            rows = fetch_experiments_with_series(maschine_id)
        except Exception as e:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("DB error"))
            self.table.setItem(0, 1, QTableWidgetItem(""))
            self.table.setItem(0, 2, QTableWidgetItem(str(e)))
            return

        # Bulk-Lookup: welche TrialSeries haben gespeicherte Smart-Chart-
        # Reports (RE-Icon-Spalte, 2026-08-27) - eine Abfrage statt einer
        # pro Zeile, gleiches Muster wie Backlogs _retest_flags_map.
        try:
            _report_rows = fetch_all(
                "SELECT SeriesPK, COUNT(*) AS n FROM tblSmartChartReport "
                "WHERE IsTemplate=0 AND SeriesPK IS NOT NULL GROUP BY SeriesPK"
            )
            self._series_report_map = {int(r["SeriesPK"]): int(r["n"]) for r in _report_rows}
        except Exception:
            self._series_report_map = {}

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

        # Experiment-Request IDs (einmalig laden)
        er_map = {}
        try:
            fld = getattr(self, '_exp_req_field', None)
            if fld:
                q = f"SELECT [ID] AS exp_id_pk, [{fld}] AS experiment_request_id FROM tblExperimente;"
                er_rows = fetch_all(q, [])
                for rr in er_rows or []:
                    er_map[rr.get('exp_id_pk')] = rr.get('experiment_request_id')
        except Exception:
            er_map = {}

        # in Records einhaengen (fuer Sortierung + Anzeige)
        if er_map:
            for rec in rows:
                try:
                    rec['experiment_request_id'] = er_map.get(rec.get('exp_id_pk'))
                except Exception:
                    pass
        else:
            for rec in rows:
                rec['experiment_request_id'] = None

        # -------------------------------------------------
        # Attachments (Image/PDF) pro TrialSeries ermitteln
        # -------------------------------------------------
        series_ids = []
        try:
            series_ids = [int(r.get('series_id_pk')) for r in rows if r.get('series_id_pk') is not None]
        except Exception:
            series_ids = []

        has_attach_set: set[int] = set()
        if series_ids:
            # Access hat Grenzen bei IN(...). Darum in Chunks.
            def _chunks(lst, n=200):
                for i in range(0, len(lst), n):
                    yield lst[i:i + n]

            def _fetch_series_ids(tbl_name: str) -> set[int]:
                out: set[int] = set()
                try:
                    for ch in _chunks(series_ids, 200):
                        ph = ",".join(["?"] * len(ch))
                        q = f"SELECT [TrialSeriesID] FROM {tbl_name} WHERE [TrialSeriesID] IN ({ph}) GROUP BY [TrialSeriesID];"
                        rr = fetch_all(q, ch)
                        for rrr in rr or []:
                            try:
                                out.add(int(rrr.get('TrialSeriesID')))
                            except Exception:
                                continue
                except Exception:
                    return set()
                return out

            img_ids = _fetch_series_ids("tblTrialSeriesImage")
            pdf_ids = _fetch_series_ids("tblTrialSeriesPDF")
            has_attach_set = set(img_ids) | set(pdf_ids)

        # Notes: fetch series IDs that have non-empty Notes
        has_notes_set: set[int] = set()
        if series_ids:
            try:
                for ch in _chunks(series_ids, 200):
                    ph = ",".join(["?"] * len(ch))
                    q = f"SELECT ID FROM tblTrialSeries WHERE ID IN ({ph}) AND Notes IS NOT NULL AND Notes <> '';"
                    rr = fetch_all(q, ch)
                    for rrr in rr or []:
                        try:
                            has_notes_set.add(int(rrr.get('ID')))
                        except Exception:
                            continue
            except Exception:
                pass

        for rec in rows:
            try:
                sid = rec.get('series_id_pk')
                rec['has_attach'] = bool(sid is not None and int(sid) in has_attach_set)
                rec['has_notes'] = bool(sid is not None and int(sid) in has_notes_set)
            except Exception:
                rec['has_attach'] = False
                rec['has_notes'] = False

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

            # Payload für spätere Navigation
            self._row_payload.append(
                (rec["exp_id_pk"], rec["series_id_pk"], rec["experiment_id"])
            )
            self._original_status_ids.append(status_id)

        # Spaltenbreiten
        self.table.resizeColumnToContents(0)
        self.table.setColumnWidth(1, 600)  # Trial Series Name (breit)
        self.table.setColumnWidth(2, 120)  # Machine (schmal)
        self.table.setColumnWidth(3, 160)  # Creation Date
        self.table.setColumnWidth(4, 110)  # Owner (schmaler)
        self.table.setColumnWidth(5, 110)  # Status
        self.table.setColumnWidth(6, 50)  # AM
        self.table.setColumnWidth(7, 60)  # ER
        self.table.setColumnWidth(8, 50)  # NT
        self.table.setColumnWidth(9, 50)  # RE

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
                QMessageBox.critical(
                    self,
                    "Error opening",
                    f"Experiment could not be opened.\n\n"
                    f"ExperimentID: {experiment_id}\n"
                    f"ExpPK: {exp_pk} / SeriesPK: {series_pk}\n\n"
                    f"{e}",
                )
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
                errors.append((row, PermissionError("Keine Schreibrechte (Read-Only).")))
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
                         f"{len(errors)} Zeile(n) konnten nicht gespeichert werden.\n"
                         f"Erster Fehler (Zeile {first_row + 1}):\n{first_err}")
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
            self._notify("warning", "No permission", "Du hast keine Schreibrechte (Read-Only).")
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
                QMessageBox.critical(
                    self,
                    "Change status",
                    f"An error occurred while checking the machine:\n{e}",
                )
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
        lbl.setToolTip("Attachment vorhanden")
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
        lbl.setToolTip("Notes vorhanden")
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

        lbl = _ClickableLabel(on_click=_open)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setToolTip("Open saved Smart Chart report")
        lbl.setPixmap(pm)
        self.table.setCellWidget(row, col, lbl)

    def _open_report_icon_for_series(self, series_pk) -> None:
        """Klick auf das RE-Icon: bei genau einem gespeicherten Report direkt
        öffnen, bei mehreren einen kleinen Auswahl-Dialog zeigen (siehe
        ui/widgets/report_picker.py)."""
        if not series_pk or not callable(self.on_open_report):
            return
        from ui.widgets.report_picker import choose_report_for_series
        report_id = choose_report_for_series(self, series_pk)
        if report_id is not None:
            self.on_open_report(series_pk, report_id)

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
        """Prüft, ob die gegebene TrialSeries aktuell eine Joker-Maschine zugewiesen hat."""
        sql = """
              SELECT s.[ID] AS [SeriesID],
                m.[ID]           AS [MachineID],
                m.[IsJoker]      AS [IsJoker]
              FROM tblTrialSeries AS s
                  LEFT JOIN tblMaschine AS m
              ON m.[ID] = s.[MachineID]
              WHERE s.[ID] = ?; \
              """
        try:
            rows = fetch_all(sql, [series_id])
        except Exception:
            return False
        if not rows:
            return False
        row = rows[0]
        val = row.get("IsJoker")
        try:
            return bool(int(val))
        except Exception:
            return bool(val)

    def _update_backlog_status(self, series_id, new_status, old_status, user_id, new_machine_id=None):
        """Schreibt einen geänderten Status in tblBacklog."""
        # Wenn ein Auftrag zurück in den Status 'Backlog' (1) gesetzt wird,
        # und es sich um eine Joker-TrialSeries handelt, dann soll wieder die
        # Original-Joker-Maschine zugewiesen werden.
        if new_status == 1 and old_status != 1:
            try:
                rows = fetch_all(
                    "SELECT [IsJoker], [OriginalJoker] FROM tblTrialSeries WHERE [ID] = ?;",
                    [series_id],
                )
                if rows:
                    row = rows[0]
                    val = row.get("IsJoker")
                    try:
                        is_joker = bool(int(val))
                    except Exception:
                        is_joker = bool(val)
                    orig = row.get("OriginalJoker")
                    if is_joker and orig is not None:
                        new_machine_id = orig
            except Exception:
                pass

        # Gleiche Logik wie im Backlog-Screen:
        # Wenn von Backlog (1) auf etwas anderes gewechselt wird und ein User bekannt ist,
        # wird der BacklogOwner gesetzt.
        set_owner = (old_status == 1 and new_status !=
                     1 and user_id is not None)

        if set_owner and new_machine_id is not None:
            sql = """
                  UPDATE tblTrialSeries
                  SET [BacklogStatusID] = ?, [BacklogOwner] = ?, [MachineID] = ?
                  WHERE [ID] = ?; \
                  """
            params = [new_status, user_id, new_machine_id, series_id]
        elif set_owner:
            sql = """
                  UPDATE tblTrialSeries
                  SET [BacklogStatusID] = ?, [BacklogOwner] = ?
                  WHERE [ID] = ?; \
                  """
            params = [new_status, user_id, series_id]
        elif new_machine_id is not None:
            sql = """
                  UPDATE tblTrialSeries
                  SET [BacklogStatusID] = ?, [MachineID] = ?
                  WHERE [ID] = ?; \
                  """
            params = [new_status, new_machine_id, series_id]
        else:
            sql = """
                  UPDATE tblTrialSeries
                  SET [BacklogStatusID] = ?
                  WHERE [ID] = ?; \
                  """
            params = [new_status, series_id]

        execute(sql, params)

        # Notifications erstellen wenn Status → Done (ID 3)
        if new_status == 3 and old_status != 3:
            try:
                from ui.notifications import create_done_notifications
                create_done_notifications(
                    series_id=series_id,
                    sender_user_id=user_id,
                )
            except Exception:
                pass

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
            QMessageBox.critical(self, "Copy TrialSeries",
                                 f"Aktion fehlgeschlagen:\n{e}")

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
        can_delete = lvl >= 4
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

        # Aktuelle MachineID laden
        try:
            row_data = fetch_all(
                "SELECT s.MachineID, m.Maschine AS MachineName "
                "FROM tblTrialSeries s "
                "LEFT JOIN tblMaschine m ON m.ID = s.MachineID "
                "WHERE s.ID = ?",
                [series_id],
            )
            cur_machine_id = int(row_data[0]["MachineID"]) if row_data and row_data[0]["MachineID"] else None
            cur_machine_name = str(row_data[0]["MachineName"] or "") if row_data else ""
        except Exception as e:
            QMessageBox.critical(self, "Error",
                                 f"Could not load machine data:\n{e}")
            return

        # Alle Maschinen laden
        try:
            machines = fetch_all(
                "SELECT ID, Maschine FROM tblMaschine ORDER BY Maschine", [])
        except Exception:
            machines = []

        if not machines:
            QMessageBox.information(self, "No Machines",
                                    "No machines found in database.")
            return

        machine_ids = [int(r["ID"]) for r in machines]
        machine_names = [str(r["Maschine"] or "") for r in machines]

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
            execute(
                "UPDATE tblTrialSeries SET MachineID = ? WHERE ID = ?",
                [new_machine_id, series_id],
            )
        except Exception as e:
            QMessageBox.critical(self, "Save Error",
                                 f"Could not save machine:\n{e}")
            return

        # Feature-Tracking
        try:
            user_id = (getattr(app_meta.current_user, "id", None)
                       or getattr(app_meta.current_user, "ID", None))
            execute(
                "INSERT INTO tblFeatureUsage (FeatureID, UserID, ExtraInfo) VALUES (?, ?, ?)",
                [7, user_id, str(series_id)],
            )
        except Exception:
            pass

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
        try:
            yarn_rows = fetch_all(
                "SELECT DISTINCT ts.Ply, ts.YarnID "
                "FROM tbltrialsettings ts "
                "JOIN tbltrial t ON t.ID = ts.TrialID "
                "WHERE t.TrialSeriesID = ? "
                "ORDER BY ts.Ply",
                [series_id],
            )
        except Exception as e:
            QMessageBox.critical(self, "Error",
                                 f"Could not load yarn data:\n{e}")
            return

        if not yarn_rows:
            QMessageBox.information(self, "No Yarn Data",
                                    "This Trial Series has no yarn entries.")
            return

        # ── Alle verfügbaren Garne laden ──────────────────────────────────
        try:
            # Halbfabrikat-"Schatten"-Garne (Multimaschinen-Ply-Verknüpfung)
            # sollen hier nicht als Reassign-Ziel auftauchen.
            src_col = resolve_field(['SourceTrialID'], get_columns_map('tblYarn'))
            where = f" WHERE [{src_col}] IS NULL" if src_col else ""
            all_yarns = fetch_all(f"SELECT ID, Name FROM tblYarn{where} ORDER BY Name", [])
        except Exception:
            all_yarns = []

        yarn_id_to_name = {int(r["ID"]): str(r["Name"]) for r in all_yarns}
        yarn_name_list = [str(r["Name"]) for r in all_yarns]
        yarn_id_list = [int(r["ID"]) for r in all_yarns]

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
            tbl.setItem(row_idx, 1, cur_item)

            cmb = QComboBox()
            cmb.addItems(yarn_name_list)
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

        # ── Trials laden ──────────────────────────────────────────────────
        try:
            trial_rows_c = fetch_all(
                "SELECT ID FROM tblTrial WHERE TrialSeriesID = ? ORDER BY Versuchsnummer",
                [series_id])
            trial_ids = [int(r["ID"]) for r in trial_rows_c]
        except Exception:
            trial_ids = []

        def _get_ply1_settings(trial_id):
            try:
                rows = fetch_all(
                    "SELECT * FROM tblTrialSettings WHERE TrialID = ? ORDER BY ID LIMIT 1",
                    [trial_id])
                return dict(rows[0]) if rows else None
            except Exception:
                return None

        # ── Speichern ─────────────────────────────────────────────────────
        # Neue Ply-Labels berechnen (nur nicht-gelöschte, in Reihenfolge)
        active_states = [s for s in rows_state if not s["deleted"]]
        for i, s in enumerate(active_states):
            s["new_ply"] = f"Ply {i + 1}"

        # ── Konsistenzprüfung vor dem Schreiben ───────────────────────────
        # 1) Dialog-intern: zwei Zeilen mit gleichem Ply-Label aber verschiedener YarnID?
        ply_to_yid: dict = {}
        conflicts = []
        for state in active_states:
            new_ply = state["new_ply"]
            idx = state["cmb"].currentIndex()
            new_yid = yarn_id_list[idx] if idx >= 0 and yarn_id_list else None
            if new_yid is None:
                continue
            if new_ply in ply_to_yid:
                if ply_to_yid[new_ply] != new_yid:
                    name_a = yarn_id_to_name.get(ply_to_yid[new_ply], f"ID {ply_to_yid[new_ply]}")
                    name_b = yarn_id_to_name.get(new_yid, f"ID {new_yid}")
                    conflicts.append(f"{new_ply}: «{name_a}» vs «{name_b}» (within dialog)")
            else:
                ply_to_yid[new_ply] = new_yid

        # 2) Gegen DB: gibt es in der Series bereits ein anderes Garn für dieses Ply?
        for new_ply, new_yid in ply_to_yid.items():
            conflict_rows = fetch_all(
                """
                SELECT DISTINCT y.Name AS YarnName
                FROM tblTrialSettings ts
                         JOIN tblTrial t ON t.ID = ts.TrialID
                         JOIN tblYarn y ON y.ID = ts.YarnID
                WHERE t.TrialSeriesID = ?
                  AND ts.Ply = ?
                  AND ts.YarnID != ?
                """,
                [series_id, new_ply, new_yid],
            )
            if conflict_rows:
                existing = ", ".join(r["YarnName"] for r in conflict_rows)
                new_name = yarn_id_to_name.get(new_yid, f"ID {new_yid}")
                conflicts.append(f"{new_ply}: «{new_name}» conflicts with existing «{existing}»")

        if conflicts:
            from PySide6.QtWidgets import QMessageBox as _QMB
            _QMB.critical(
                None, "Yarn Conflict",
                "Cannot save — the following plies would create inconsistencies:\n\n"
                + "\n".join(f"  • {c}" for c in conflicts)
                + "\n\nAll trials in a series must use the same yarn per ply."
            )
            return

        changes_made = 0
        try:
            for state in rows_state:
                orig_ply = state["orig_ply"]
                orig_yid = state["orig_yid"]
                deleted = state["deleted"]
                is_new = state["is_new"]
                idx = state["cmb"].currentIndex()
                new_yid = yarn_id_list[idx] if idx >= 0 and yarn_id_list else None
                new_ply = state.get("new_ply")

                if deleted and is_new:
                    # Neu hinzugefügt und gleich wieder gelöscht → nichts tun
                    pass

                elif deleted and not is_new and orig_ply and trial_ids:
                    # Ply löschen: alle tbltrialsettings-Zeilen mit diesem Ply-Label entfernen
                    ph = ",".join(["?"] * len(trial_ids))
                    execute(
                        f"DELETE FROM tblTrialSettings "
                        f"WHERE Ply = ? AND TrialID IN ({ph})",
                        [orig_ply] + trial_ids,
                    )
                    changes_made += 1

                elif is_new and new_yid is not None:
                    # Neues Ply: tbltrialsettings-Klon von Ply 1 pro Trial
                    for tid in trial_ids:
                        tmpl = _get_ply1_settings(tid)
                        if tmpl:
                            skip = {"id", "trialid", "globalid"}
                            cols = [c for c in tmpl.keys() if c.lower() not in skip]
                            vals = []
                            for c in cols:
                                if c.lower() == "yarnid":
                                    vals.append(new_yid)
                                elif c.lower() == "ply":
                                    vals.append(new_ply)
                                else:
                                    vals.append(tmpl[c])
                            cols_sql = ", ".join(f"`{c}`" for c in ["TrialID"] + cols)
                            ph2 = ", ".join(["?"] * (1 + len(cols)))
                            execute(
                                f"INSERT INTO tblTrialSettings ({cols_sql}) VALUES ({ph2})",
                                [tid] + vals,
                            )
                    changes_made += 1

                elif not is_new and new_ply is not None:
                    # Bestehendes Ply: YarnID und Ply-Label aktualisieren
                    if trial_ids:
                        ph = ",".join(["?"] * len(trial_ids))
                        if new_yid != orig_yid or new_ply != orig_ply:
                            execute(
                                f"UPDATE tblTrialSettings SET YarnID = ?, Ply = ? "
                                f"WHERE Ply = ? AND TrialID IN ({ph})",
                                [new_yid, new_ply, orig_ply] + trial_ids,
                            )
                            changes_made += 1

        except Exception as e:
            QMessageBox.critical(self, "Save Error",
                                 f"Could not save yarn data:\n{e}")
            return

        # ── Feature-Tracking ──────────────────────────────────────────────
        try:
            user_id = (getattr(app_meta.current_user, "id", None)
                       or getattr(app_meta.current_user, "ID", None))
            execute(
                "INSERT INTO tblFeatureUsage (FeatureID, UserID, ExtraInfo) VALUES (?, ?, ?)",
                [6, user_id, str(series_id)],
            )
        except Exception:
            pass

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

        # ── Confirmation dialog ────────────────────────────────────────────
        msg = QMessageBox(self)
        msg.setWindowTitle("Delete Trial Series")
        msg.setIcon(QMessageBox.Warning)
        msg.setText(
            f"<b>Permanently delete this Trial Series?</b><br><br>"
            f"<b>{series_name}</b><br><br>"
            f"This will delete all Trials, Lab data, and related records.<br>"
            f"<b>This action cannot be undone.</b>"
        )
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        msg.setDefaultButton(QMessageBox.Cancel)
        if msg.exec() != QMessageBox.Yes:
            return

        # ── Delete in FK-safe order ────────────────────────────────────────
        try:
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
            QMessageBox.critical(
                self,
                "Delete Trial Series",
                f"An error occurred while deleting:\n\n{e}",
            )
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

        new_text = (dlg.new_name() or "").strip()
        if not new_text:
            # Empty -> keep old
            return

        new_full = f"{prefix}{new_text}" if prefix else new_text

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
            update_trialseries_name(series_pk, new_full)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Rename Trial Series",
                f"Could not save the new name.\n\n{e}",
            )
            return

        # Update UI cell
        try:
            self.table.item(row, 1).setText(new_full)
        except Exception:
            pass

    @staticmethod
    def _split_trialseries_prefix(full_name: str) -> tuple[str, str]:
        """Split a TrialSeries name into (prefix_to_keep, editable_part).

        Rules:
        - If it starts with something like "f(03 ) " (letter + (...) + spaces), keep that.
        - Else if it starts with digits followed by whitespace, keep that.
        - Otherwise prefix is empty.
        """
        s = full_name or ""

        # Pattern like: f(03 ) <name>  or A(12)  <name>
        m = re.match(r"^(\s*[A-Za-z]\([^\)]*\)\s+)(.*)$", s)
        if m:
            return m.group(1), m.group(2)

        # Pattern like: 03 <name>
        m = re.match(r"^(\s*\d+\s+)(.*)$", s)
        if m:
            return m.group(1), m.group(2)

        return "", s


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
        self._but_cancel = QPushButton("Abbrechen", self)
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