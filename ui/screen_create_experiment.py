from __future__ import annotations
# ui/screen_create_experiment.py
"""Screen zum Erstellen, Bearbeiten und Kopieren von Experimenten (CreateExperimentScreen).

Zentraler Eingabe-Screen für neue Versuche. Wird in drei Modi geöffnet:
  - "create": Neues Experiment anlegen
  - "edit":   Bestehendes Experiment bearbeiten (existing_experiment_id gesetzt)
  - "copy":   Bestehendes Experiment als Vorlage kopieren

Struktur (Tabs):
  - Tab "Experiment": Metadaten (Bezeichnung, Maschine, Garn, Projektgruppe usw.)
  - Tab "Trials":     Trial-Einträge (Versuchspunkte) als editierbare Tabelle
  - Tab "Waterbath":  Wasserbad-Parameter (falls Tabelle vorhanden)
  - Tab "Bilder":     Bilder und PDFs zur TrialSeries

Besonderheiten:
  - Alle Felder werden dynamisch aus den DB-Spalten generiert
  - FK-Felder als PrettyComboBox mit lesbaren Namen
  - Trial-Tabelle mit gelöschten Zeilen (Tastatur-Delete)
  - Waterbath-Zeilen automatisch aus Trial-Anzahl generiert
  - Experiment-Request-Verknüpfung mit Vorausfüllen von Feldern
  - Speichern triggert Backlog-Update

Datenbankbezug:
  tblExperimente, tblTrialSeries, tblTrial, tblTrialSettings,
  tblWaterbath (optional), tblBacklog, tblExperimentRequests
"""

# ui/screen_create_experiment.py
from ui.theme import accent_tint, accent_gridline, get_accent

import os

from typing import Any, List, Optional, Dict, Tuple
from decimal import Decimal, ROUND_HALF_UP


from PySide6.QtCore import Qt, QRegularExpression, QRect, QDate, QPoint, QSize, QMimeData
from PySide6.QtGui import (
    QIcon, QPainter, QPixmap, QIntValidator, QRegularExpressionValidator, QKeyEvent, QPen, QColor
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTabWidget, QFormLayout, QComboBox, QLineEdit, QSpinBox,
    QGridLayout, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSpacerItem, QSizePolicy, QAbstractItemView, QCompleter,
    QCheckBox,
    QListWidget,
    QTreeWidget, QTreeWidgetItem, QDialog
)

from db.connection import (
    get_connection,
    new_global_id,
    table_exists as _db_table_exists,
    get_columns_map as _db_get_columns_map,
)
from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from ui.widgets.spool_picker import SpoolPickerDialog, spool_label
from ui.widgets.yarn_colour import colour_icon, colour_tooltip, load_yarn_colours
from ui.widgets.tree_search import TreeSearch
import ui.widgets.yarn_locations as _yarn_locations
from ui.pathutil import resource_path
from ui.text_normalize import norm as _norm, resolve_field
from db.trial_reference import exclude_references_sql, format_trial_number, next_trial_number
from db.dy_ratio import append_ratio_column

import app_meta
import re


# insert_waterbath_rows: db/trial_actions.py (Qt-free, shared with the web app)
from db.trial_actions import insert_waterbath_rows  # noqa: E402,F401
import db.trial_actions as _trial_actions  # noqa: E402
# Form data, rules and saving of create / add series / add lab machines:
# db/experiment_create.py (Qt-free, shared with the web app)
import db.experiment_create as _ec  # noqa: E402


# -->-->-->-->-->-->-->-->-->- DB Helpers -->-->-->-->-->-->-->-->-->-

def fetch_all(sql: str, params: list | tuple = ()):
    """Führt ein SELECT aus und gibt eine Liste von Dicts zurück (Wrapper für db.connection)."""
    """Return rows as list[dict]."""
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description] if cur.description else []
        rows = []
        for r in cur.fetchall():
            d = {cols[i]: r[i] for i in range(len(cols))}
            rows.append(d)
        return rows


def table_exists(name: str) -> bool:
    """Gibt True zurück wenn die Tabelle in der DB existiert."""
    return _db_table_exists(name.lower())


def get_columns_map(table: str) -> Dict[str, str]:
    """Gibt {normierter_Name: echter_Name} für alle Spalten einer Tabelle zurück."""
    """{lower_name: real_name}"""
    return _db_get_columns_map(table.lower())


def get_columns_info(table: str) -> List[Dict[str, Any]]:
    """Gibt Spalten-Metadaten (Name, Typ, Nullable) einer Tabelle zurück."""
    """Spalteninfos (MySQL)."""
    cmap = _db_get_columns_map(table.lower())
    out: List[Dict[str, Any]] = []
    for lc, real in cmap.items():
        out.append({"lower": lc, "real": real, "data_type": None, "type_name": None})
    return out


# get_or_create_shadow_yarn: db/experiment_create.py (Qt-free, shared with the web app)
from db.experiment_create import get_or_create_shadow_yarn  # noqa: E402,F401


# -->-->-->-->-->-->-->-->-->- UI Helpers -->-->-->-->-->-->-->-->-->-

def _make_icon(checked: bool) -> QIcon:
    """Erstellt ein Checkmark/Minus-Icon für Bool-Felder in der Trial-Tabelle."""
    pix = QPixmap(16, 16)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    if checked:
        p.setPen(Qt.NoPen)
        p.setBrush(Qt.green)
        p.drawEllipse(0, 0, 16, 16)
        p.setBrush(Qt.white)
        p.drawEllipse(4, 4, 8, 8)
    else:
        p.setPen(Qt.gray)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(1, 1, 14, 14)
    p.end()
    return QIcon(pix)


class PrettyComboBox(QComboBox):
    """Erweiterter QComboBox mit Suche und leerem ersten Eintrag für FK-Felder.

    Filtert die Optionen bei Texteingabe und unterstützt Mausrad-Scroll.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet("""
            QComboBox {
                background-color: #ffffff;
                color: #000000;
                padding-right: 28px;
                border: 1px solid #8fbf8f;
                selection-background-color: #e0e0e0;
            }
            QComboBox:editable { background-color: #ffffff; color: #000000; }
            QComboBox::drop-down { width: 24px; border: none; }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #000000;
                selection-background-color: #d7e3f4;
                selection-color: #000000;
                outline: none;
            }
            QComboBox QAbstractItemView::item:hover {
                background: #ededed;
                color: #000000;
            }
        """)
        self.setEditable(False)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.setMinimumHeight(26)

        def paintEvent(self, e):
            super().paintEvent(e)
            r = self.rect()
            arrow_rect = QRect(r.right() - 20, r.top(), 20, r.height())
            p = QPainter(self)
            try:
                p.setRenderHint(QPainter.Antialiasing)
                p.setPen(Qt.NoPen)
                p.setBrush(QColor("#333333"))
                w = arrow_rect.width()
                h = arrow_rect.height()
                cx = arrow_rect.left() + w // 2
                cy = arrow_rect.top() + h // 2 + 1
                points = [(cx - 5, cy - 2), (cx + 5, cy - 2), (cx, cy + 4)]
                p.drawPolygon(*[QPoint(*pt) for pt in points])
                pen = QPen(QColor("#cddccd"))
                p.setPen(pen)
                p.drawLine(
                    arrow_rect.left(), r.top() + 3,
                    arrow_rect.left(), r.bottom() - 3
                )
            finally:
                p.end()


class ReadOnlyTable(QTableWidget):
    """Tabelle für Trial-Einträge mit Delete-Taste-Support.

    Zeilen können mit Delete-Taste markiert und beim Speichern entfernt werden.

    `on_row_moved(src_row, dst_row)` (optional, 2026-08-28 ergänzt auf
    Nutzerwunsch: "kann ich die einzelnen düsen/druck listeneinträge mittels
    buttons hoch resp. runter machen. kannst du das auch zusätzlich via
    drag&drop realisieren") aktiviert Drag&Drop-Umsortierung per Maus,
    zusätzlich zu (nicht statt) bestehenden Up/Down-Buttons - siehe
    CreateExperimentScreen.tblJets. Bewegt dabei bewusst nur EINE Zeile pro
    Drag (die beim Drag-Start aktuelle Zeile, siehe startDrag()), analog zu
    den Up/Down-Buttons, die ebenfalls nur `currentRow()` bewegen und nicht
    die ganze Mehrfachauswahl (tblJets erlaubt ExtendedSelection nur fürs
    "Markierte kopieren"-Feature, nicht fürs Verschieben)."""
    def __init__(self, rows: int, cols: int, on_delete_row=None, on_row_moved=None,
                 parent: Optional[QWidget] = None):
        super().__init__(rows, cols, parent)
        self.on_delete_row = on_delete_row
        self._on_row_moved = on_row_moved
        self._drag_src_row = -1
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        if callable(on_row_moved):
            self.setDragEnabled(True)
            self.setAcceptDrops(True)
            self.setDropIndicatorShown(True)
            self.setDragDropMode(QAbstractItemView.InternalMove)
            # Ohne das liefert dropIndicatorPosition() teils OnItem (Zell-
            # Overwrite-Semantik) statt Above-/BelowItem - für eine reine
            # Zeilen-Umsortierung wollen wir ausschliesslich "vor"/"nach"
            # dieser Zeile, nie "auf" ihr.
            self.setDragDropOverwriteMode(False)

    def keyPressEvent(self, event: QKeyEvent):
        """Delete-Taste markiert die selektierte Zeile zum Löschen."""
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            row = self.currentRow()
            if row >= 0:
                allow = True
                if callable(self.on_delete_row):
                    res = self.on_delete_row(row)
                    if res is False:
                        allow = False
                if allow:
                    self.removeRow(row)
                event.accept()
                return
        super().keyPressEvent(event)

    def startDrag(self, supported_actions):
        """Merkt sich die Zeile, auf der der Drag tatsächlich begonnen hat -
        `currentRow()` allein wäre nach dem Drop nicht mehr zuverlässig
        rekonstruierbar (siehe dropEvent())."""
        self._drag_src_row = self.currentRow()
        super().startDrag(supported_actions)

    def dropEvent(self, event):
        """Eigene Zeilen-Umsortierung statt Qt's Default-Itemverschiebung
        (die würde nur die QTableWidgetItems bewegen, nicht die externe
        Python-Datenliste eines Aufrufers wie CreateExperimentScreen._jets_data
        - daher hier bewusst KEIN super().dropEvent(), sondern volle
        Delegation an on_row_moved(), das Tabelle UND Datenliste synchron
        hält, siehe CreateExperimentScreen._move_jet_row())."""
        if not callable(self._on_row_moved) or event.source() is not self:
            super().dropEvent(event)
            return
        src = self._drag_src_row
        self._drag_src_row = -1
        if src < 0:
            event.ignore()
            return
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        target_row = self.rowAt(pos.y())
        if target_row < 0:
            insert_before = self.rowCount()
        elif self.dropIndicatorPosition() == QAbstractItemView.BelowItem:
            insert_before = target_row + 1
        else:
            insert_before = target_row
        # Standard-Umsortierungs-Arithmetik: `insert_before` bezieht sich auf
        # die Reihenfolge VOR dem Entfernen von `src` - liegt das Ziel dahinter,
        # rutscht der Index durchs Entfernen selbst um 1 nach vorne.
        dst = insert_before - 1 if insert_before > src else insert_before
        dst = max(0, min(self.rowCount() - 1, dst))
        # Bugreport 2026-08-31: "die bewegte Zeile verschwindet nach dem
        # Loslassen". Ursache: bei InternalMove ruft Qt's eigenes
        # QAbstractItemView::startDrag() nach Abschluss des Drags
        # zusätzlich intern clearOrRemove() auf, das die urspruenglich
        # gezogene(n) Zeile(n) NOCHMAL aus der Quelle entfernt - sobald die
        # resultierende Drop-Action Qt.MoveAction ist (der Default bei
        # acceptProposedAction()). Wir haben Quelle UND Ziel oben bereits
        # vollstaendig selbst per Item-Verschiebung + _on_row_moved()
        # synchronisiert - die zusaetzliche Qt-eigene Entfernung loescht
        # dadurch die falsche (inzwischen verschobene) Zeile nochmal.
        # Fix: Drop-Action auf IgnoreAction setzen, bevor akzeptiert wird -
        # damit bleibt clearOrRemove() aus, ohne den Drop selbst abzulehnen.
        event.setDropAction(Qt.IgnoreAction)
        if dst == src:
            event.ignore()
            return
        event.accept()
        self._on_row_moved(src, dst)


from PySide6.QtWidgets import QStyledItemDelegate
from ui.widgets.friendly_error import show_error

class _JetColProtectDelegate(QStyledItemDelegate):
    """Delegate das die Jet-Spalte in der Trial-Tabelle schreibschützt (nur Anzeige)."""
    """Verhindert direkte Bearbeitung in Spalten 0, 1, 4 der Jet-Tabelle."""
    EDITABLE_COLS = {2, 3}

    def createEditor(self, parent, option, index):
        if index.column() not in self.EDITABLE_COLS:
            return None
        editor = QLineEdit(parent)
        editor.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #4a90d9;
                padding: 2px 4px;
                selection-background-color: #b7d6ff;
            }
        """)
        return editor

    def setEditorData(self, editor, index):
        editor.setText(index.data() or "")
        editor.selectAll()

    def setModelData(self, editor, model, index):
        model.setData(index, editor.text(), Qt.EditRole)


class CreateExperimentScreen(QWidget):
    def __init__(
        self,
        model: Optional[object] = None,
        on_back_home=None,
        on_open_experiment=None,
        on_back_experiment=None,
        parent: Optional[QWidget] = None,
        mode: str = "create",
        existing_experiment_id: Optional[int] = None,
        sidebar_callbacks: Optional[dict] = None,
    ):
        super().__init__(parent)
        self.on_back_home = on_back_home
        self.on_open_experiment = on_open_experiment
        self.on_back_experiment = on_back_experiment
        self.mode = (mode or "create").lower()
        self.existing_experiment_id = existing_experiment_id
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None

        # State
        # [Year, PG, OT, Num, MachineID, MachineName]
        self.strExperimentData = ["" for _ in range(6)]
        # [ExperimentID, SeriesName]
        self.strTrialSeriesData = ["" for _ in range(2)]
        self._materials_data: List[Dict[str, Any]] = []
        self._jets_data: List[Dict[str, Any]] = []
        self._jet_titer_map: Dict[Any, Dict] = {}
        self._lab_data: List[Dict[str, Any]] = []
        self._lab_machines: Dict[Any, Dict[str, Any]] = {}
        self._machine_field_widgets: List[Tuple[QLabel,
                                                Any, int, Optional[str], str]] = []
        # ^ (label, widget, fieldnumber, orig_col_name, storage_table)
        #   widget: QLineEdit (normal) oder QComboBox (dropdown:tblXxx)
        #   storage_table: 'tbltrial' | 'tbltrialsettings'
        self._strict_ro_tbl_yarns = False
        self._strict_ro_tbl_labs = False

        self._build_ui()
        self._wire_signals()
        self._load_backlog_status()
        # central, idempotent mode application
        self._mode_applied = False
        if self.mode == "addseries":
            self._apply_mode_addseries()
        elif self.mode == "addtrials":
            self._apply_mode_addtrials()
        elif self.mode == "addlabmachines":
            self._apply_mode_addlabmachines()
        else:
            self._apply_mode_create()
        self._mode_applied = True

        # Daten laden
        if self.mode in ("addseries", "addtrials", "addlabmachines"):
            self._load_existing_experiments()
            self._load_yarns()
            self._load_jets()
            self._load_housing()
            self._load_machines()
            self._load_lab_machines()
        else:
            self._load_product_groups()
            self._load_order_types()
            self._load_projects()
            self._load_open_experiment_requests()
            self._load_yarns()
            self._load_jets()
            self._load_housing()
            self._load_machines()
            self._load_lab_machines()
        self._check_all()

        # Flag, ob aktuell eine Joker‑Maschine gewählt ist
        self._joker_machine_selected: bool = False

        # Non-modal Experiment Request popup (kept open while creating an experiment)
        self._expreq_popup: Optional[object] = None

    # -->-->-->- UI -->-->-->-
    def _build_ui(self):
        """Erstellt Header, Tab-Widget (Experiment, Trials, Waterbath, Bilder), Footer."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring). Der frühere
        # Header-Back-Button (nur im addtrials-Modus sichtbar, zurück zum
        # ShowExperimentScreen, von dem aus "Add Trials" geöffnet wurde) lebt
        # jetzt als kontextueller Back-Chip in der Tools-Leiste weiter -
        # gleiches Muster wie ShowExperimentScreen.btn_back_chip, siehe
        # _apply_mode_addtrials(). Der separate kurze Header-"Titel" pro Modus
        # (z.B. "Create Experiment") entfällt ersatzlos - lbl_small_title
        # trägt bereits einen ausführlicheren, modusabhängigen Untertitel.
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)
# Tools
        tools = QFrame()
        tl = QHBoxLayout(tools)
        tl.setContentsMargins(24, 12, 24, 0)
        tl.setSpacing(8)

        self.btn_back_chip = QPushButton("← Back to Experiment")
        self.btn_back_chip.setCursor(Qt.PointingHandCursor)
        self.btn_back_chip.setStyleSheet(
            "QPushButton{background:transparent;color:#39a650;border:1px solid #39a650;"
            "border-radius:4px;padding:5px 10px;font-weight:600;}"
            "QPushButton:hover{background:#e8f5e9;}"
        )
        self.btn_back_chip.clicked.connect(self._back_experiment_clicked)
        self.btn_back_chip.setVisible(False)
        tl.addWidget(self.btn_back_chip)

        self.lbl_small_title = QLabel("")
        self.lbl_small_title.setStyleSheet(
            "padding: 6px 10px; background: #3f3f3f; color: white; font-weight: 600;")
        self.butSave = QPushButton("Save")
        self.butSave.setObjectName("GreenBtn")
        self.butSave.setEnabled(False)
        self.butSave.clicked.connect(self._on_save)
        # Experiment Request icon (visible only when a request is selected in General tab)
        self.btn_experiment_request = QPushButton()
        self.btn_experiment_request.setObjectName("IconBtn")
        self.btn_experiment_request.setToolTip("Show selected Experiment Request")
        self.btn_experiment_request.setCursor(Qt.PointingHandCursor)
        self.btn_experiment_request.setFlat(True)
        self.btn_experiment_request.setFixedSize(34, 34)
        self.btn_experiment_request.setStyleSheet(
            "QPushButton{border:none;background:transparent;padding:0px;}"
            "QPushButton:hover{background:rgba(0,0,0,0.06);border-radius:6px;}"
        )
        _icon_set = False
        for _p in [
            resource_path("experiment_request.png"),
            resource_path("ui/experiment_request.png"),
            resource_path("ui/icons/experiment_request.png"),
            resource_path("ui/assets/experiment_request.png"),
            resource_path("assets/experiment_request.png"),
            resource_path("assets/images/experiment_request.png"),
        ]:
            try:
                if _p and os.path.exists(_p):
                    self.btn_experiment_request.setIcon(QIcon(_p))
                    self.btn_experiment_request.setIconSize(QSize(22, 22))
                    _icon_set = True
                    break
            except Exception:
                continue
        if not _icon_set:
            self.btn_experiment_request.setText("ER")
            self.btn_experiment_request.setStyleSheet(
                self.btn_experiment_request.styleSheet()
                + "QPushButton{font-weight:700;color:" + get_accent() + ";}"
            )
        self.btn_experiment_request.setVisible(False)
        self.btn_experiment_request.clicked.connect(self._open_selected_experiment_request_popup)

        tl.addWidget(self.lbl_small_title)
        tl.addStretch(1)
        tl.addWidget(self.btn_experiment_request)
        tl.addWidget(self.butSave)
        # Kontext-Hilfe EN/DE/ES (Nutzerwunsch 2026-10-13, ui/widgets/multilang_help.py)
        from ui.widgets.multilang_help import make_help_button
        tl.addWidget(make_help_button("How does Create Experiment work?", self._open_help))
        content_layout.addWidget(tools)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 0px; }
            QTabBar::tab { background-color: #ffffff; color: #39a650; border: 1px solid #cfcfcf;
                           padding: 8px 14px; margin-right: 4px; border-bottom: none; }
            QTabBar::tab:hover { background: #e9e9e9; }
            QTabBar::tab:selected { background: #000000; color: #39a650; }
        """.replace("#39a650", get_accent()))
        content_layout.addWidget(self.tabs, 1)

        # --> Tab: General -->
        self.tab_general = QFrame()
        self._gen_form = QFormLayout(self.tab_general)
        self._gen_form.setContentsMargins(24, 12, 24, 24)

        # create widgets
        self.cmbProductGroup = PrettyComboBox()
        self.cmbOrderType = PrettyComboBox()
        self.cmbExperimentRequest = PrettyComboBox()
        self._cmb_expreq_base_stylesheet = self.cmbExperimentRequest.styleSheet()
        # Project (tblProject), optional - user request 2026-09-02: writeable
        # freely when creating an experiment, but forced+locked to the linked
        # Experiment Request's own project whenever that request has one
        # (see _sync_project_from_request()).
        self.cmbProject = PrettyComboBox()
        self.txtExperimentNumber = QLineEdit()
        # Default: number is auto-generated
        self.txtExperimentNumber.setReadOnly(True)
        self.txtExperimentNumber.setPlaceholderText(
            "assigned automatically (000)")

        # Legacy import mode: allow manual Experiment ID entry (e.g. 2019-73-002)
        if self.mode == "legacy":
            self.txtExperimentNumber.setReadOnly(False)
            self.txtExperimentNumber.setPlaceholderText("manuell, z.B. 2019-73-002")
            try:
                rx = QRegularExpression(r"^\d{4}-\d+-\d{3}$")
                self.txtExperimentNumber.setValidator(QRegularExpressionValidator(rx, self.txtExperimentNumber))
            except Exception:
                pass
            self.txtExperimentNumber.editingFinished.connect(self._on_legacy_experiment_id_changed)

        # existing
        self.cmbExistingExperiment = PrettyComboBox()
        self.cmbExistingSeries = PrettyComboBox()

        # labels (explizit, damit wir sie mitverstecken können)
        self._lbl_pg = QLabel("Product Group")
        self._lbl_ot = QLabel("Order Type")
        self._lbl_exp_request = QLabel("Experiment Request")
        self._lbl_project = QLabel("Project")
        # Keep the top-bar icon visibility in sync with the selection
        self.cmbExperimentRequest.currentIndexChanged.connect(self._on_experiment_request_changed)
        self._lbl_num = QLabel("Experiment Number")
        self._lbl_series = QLabel("Series Name")
        self._lbl_backlog_status = QLabel("Backlog Status")
        self._lbl_backlog_prio = QLabel("Priority")
        self._lbl_exp = QLabel("Existing Experiment")
        self._lbl_ser = QLabel("Existing Trial Series")

        # Widgets im General‑Tab
        self.txtSeriesName = QLineEdit()
        self.cmbBacklogStatus = PrettyComboBox()
        self.cmbBacklogPrio = PrettyComboBox()
        self.cmbBacklogPrio.addItems(["1", "2", "3"])
        self.cmbBacklogPrio.setCurrentText("2")
        self._gen_form.addRow(self._lbl_pg, self.cmbProductGroup)
        self._gen_form.addRow(self._lbl_ot, self.cmbOrderType)
        self._gen_form.addRow(self._lbl_exp_request, self.cmbExperimentRequest)
        self._gen_form.addRow(self._lbl_project, self.cmbProject)
        self._gen_form.addRow(self._lbl_num, self.txtExperimentNumber)
        self._gen_form.addRow(self._lbl_series, self.txtSeriesName)
        self._gen_form.addRow(self._lbl_backlog_status, self.cmbBacklogStatus)
        self._gen_form.addRow(self._lbl_backlog_prio, self.cmbBacklogPrio)
        self._gen_form.addRow(self._lbl_exp, self.cmbExistingExperiment)
        self._gen_form.addRow(self._lbl_ser, self.cmbExistingSeries)

        # --> Trials (checkboxes) for addlabmachines -->
        self._lbl_trials = QLabel("Trials")
        self._trials_host_general = QFrame()
        # High-contrast background/border for better visibility
        self._trials_host_general.setStyleSheet("""
            QFrame { background-color: #FFFFFF; border: 1px solid #B5D7B5; }
        """
            .replace("#B5D7B5", accent_gridline()))
        # Grid: 5 columns per row
        self._trials_grid_general = QGridLayout(self._trials_host_general)
        self._trials_grid_general.setContentsMargins(8, 8, 8, 8)
        self._trials_grid_general.setHorizontalSpacing(18)
        self._trials_grid_general.setVerticalSpacing(10)
        self._lbl_trials.setVisible(False)
        self._trials_host_general.setVisible(False)
        self._gen_form.addRow(self._lbl_trials, self._trials_host_general)

        self.tabs.addTab(self.tab_general, _make_icon(False), "General")

        # --> Tab: Material -->
        self.tab_material = QFrame()
        ml_outer = QVBoxLayout(self.tab_material)
        ml_outer.setContentsMargins(24, 12, 24, 24)
        form_m = QFormLayout()
        ml_outer.addLayout(form_m)
        # Series Name ist jetzt im Tab "General"
        row_mat = QHBoxLayout()

        self.treeMaterial = QTreeWidget()
        self.treeMaterial.setHeaderHidden(True)
        # Spalte 1 = Spulen-Symbol (am Lager / nicht am Lager) wie in der
        # Materialzeile von Show Experiment; Klick -> Lagerplaetze.
        self.treeMaterial.setColumnCount(2)
        self.treeMaterial.header().setStretchLastSection(False)
        self.treeMaterial.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.treeMaterial.header().setSectionResizeMode(1, QHeaderView.Fixed)
        self.treeMaterial.setColumnWidth(1, 30)
        self.treeMaterial.setIconSize(QSize(16, 16))
        self.treeMaterial.setIndentation(18)
        self.treeMaterial.setExpandsOnDoubleClick(True)
        self.treeMaterial.setSelectionMode(QAbstractItemView.SingleSelection)
        self.treeMaterial.setMinimumHeight(200)
        # Custom expand/collapse indicators (from assets/images)
        _tri_right_24 = resource_path("assets/images/triangle_right_24.png")
        _tri_right_16 = resource_path("assets/images/triangle_right_16.png")
        _tri_down_24 = resource_path("assets/images/triangle_down_24.png")
        _tri_down_16 = resource_path("assets/images/triangle_down_16.png")

        tri_right = _tri_right_24 if os.path.exists(_tri_right_24) else _tri_right_16
        tri_down = _tri_down_24 if os.path.exists(_tri_down_24) else _tri_down_16

        tri_right_qss = tri_right.replace("\\", "/")
        tri_down_qss = tri_down.replace("\\", "/")
        # Qt stylesheets prefer forward slashes in file paths
        tri_right = tri_right.replace("\\", "/")
        tri_down = tri_down.replace("\\", "/")

        self.treeMaterial.setStyleSheet(f"""
            QTreeWidget {{ border: 1px solid {accent_gridline()}; background-color: #FFFFFF; }}
            QTreeWidget::item {{ padding: 6px; }}
            QTreeWidget::item:selected {{ background: #b7d6ff; }}

            /* branch (expand/collapse) */
            QTreeView::branch {{ width: 18px; height: 18px; }}
            QTreeView::branch:closed:has-children {{ image: url("{tri_right_qss}"); }}
            QTreeView::branch:open:has-children {{ image: url("{tri_down_qss}"); }}
        """)
        self.butAddMaterial = QPushButton("+")
        self.butAddMaterial.setEnabled(False)
        # Multimaschinen-Halbfabrikat: statt eines Katalog-Garns den Output
        # eines bestehenden Trials (ggf. auf einer anderen Maschine) als Ply
        # verwenden - siehe get_or_create_shadow_yarn().
        self.butAddTrialPly = QPushButton("+ Trial")
        self.butAddTrialPly.setToolTip(
            "Use the output of an existing trial (e.g. from another machine) as this ply's input, "
            "instead of picking a catalog yarn."
        )
        self.searchMaterial = TreeSearch(self.treeMaterial, columns=(0,),
                                         placeholder="Search material (all groups)…")
        mat_col = QVBoxLayout()
        mat_col.setContentsMargins(0, 0, 0, 0)
        mat_col.setSpacing(4)
        mat_col.addWidget(self.searchMaterial.edit)
        mat_col.addWidget(self.treeMaterial, 1)
        row_mat.addLayout(mat_col, 1)
        row_mat.addWidget(self.butAddMaterial, 0)
        row_mat.addWidget(self.butAddTrialPly, 0)
        form_m.addRow("Material", row_mat)

        # Number of ends + YarnUse nebeneinander
        from PySide6.QtWidgets import QComboBox as _CMB, QSpinBox as _SB, QHBoxLayout as _HBL, QLabel as _LBL
        ends_use_row = _HBL()
        ends_use_row.setSpacing(8)

        ends_use_row.addWidget(_LBL("Number of ends:"))
        self._spn_ends = _SB()
        self._spn_ends.setMinimum(1)
        self._spn_ends.setMaximum(20)
        self._spn_ends.setValue(1)
        self._spn_ends.setFixedWidth(60)
        self._spn_ends.setToolTip("Number of ends (how many times to add this yarn)")
        ends_use_row.addWidget(self._spn_ends)

        ends_use_row.addWidget(_LBL("Yarn Use:"))
        self._cmb_yarn_use_create = _CMB()
        self._cmb_yarn_use_create.setToolTip("Yarn Use / Group (optional)")
        self._cmb_yarn_use_create.addItem("—", None)
        try:
            from db.connection import fetch_all as _fa
            for _r in _fa("SELECT ID, Name FROM tblYarnUse ORDER BY ID"):
                self._cmb_yarn_use_create.addItem(str(_r.get("Name") or ""), int(_r["ID"]))
        except Exception:
            pass
        ends_use_row.addWidget(self._cmb_yarn_use_create, 1)
        form_m.addRow("", ends_use_row)
        # txtMaterialUse entfernt – Ply wird automatisch vergeben (Ply 1, Ply 2, ...)
        self.tblYarns = ReadOnlyTable(0, 4, on_delete_row=self._on_yarn_delete_row)
        self.tblYarns.setHorizontalHeaderLabels(["Material", "Ply", "Yarn Use", "Spool"])
        self.tblYarns.verticalHeader().setVisible(False)
        self.tblYarns.horizontalHeader().setStretchLastSection(False)

        def _resize_yarn_cols(event=None):
            w = self.tblYarns.viewport().width()
            col_w = max(50, w // 4)
            for c in range(4):
                self.tblYarns.setColumnWidth(c, col_w)

        self.tblYarns._resize_yarn_cols = _resize_yarn_cols
        orig_resize = self.tblYarns.resizeEvent
        def _patched_resize(event, _orig=orig_resize):
            _orig(event)
            _resize_yarn_cols()
        self.tblYarns.resizeEvent = _patched_resize
        _resize_yarn_cols()
        self.tblYarns.setStyleSheet("""
            QTableWidget { border: 1px solid #B5D7B5; background-color: #FFFFFF; }
            QHeaderView::section {
                background: #3f3f3f; color: white; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 6px 8px;
            }
            QTableWidget::item { padding: 6px; color: black; }
            QTableWidget::item:selected { background: #b7d6ff; color: black; }
        """
            .replace("#B5D7B5", accent_gridline()))
        ml_outer.addWidget(self.tblYarns, 1)
        self.tabs.addTab(self.tab_material, _make_icon(False), "Material")

        # --> Tab: Jet -->
        self.tab_jet = QFrame()
        jl_outer = QVBoxLayout(self.tab_jet)
        jl_outer.setContentsMargins(24, 12, 24, 24)

        grid_jet = QGridLayout()
        grid_jet.setHorizontalSpacing(12)
        grid_jet.setVerticalSpacing(8)
        jl_outer.addLayout(grid_jet)

        # Jet-Auswahl als Tree (wie Material-Tab)
        row_jet = QHBoxLayout()
        row_jet.setContentsMargins(0, 0, 0, 0)

        self.treeJet = QTreeWidget()
        self.treeJet.setHeaderHidden(False)
        self.treeJet.setColumnCount(8)
        self.treeJet.setHeaderLabels(["Jet", "Luftbohrung\n(mm)", "Winkel Luftbohrung\n(°)", "Yarn channel width\n(mm)", "Luftverbrauch\n(Nm³/h)", "Entwicklungsname", "Titer Range", "Ideal Titer"])
        self.treeJet.setIndentation(18)
        self.treeJet.setExpandsOnDoubleClick(True)
        self.treeJet.setSelectionMode(QAbstractItemView.SingleSelection)
        self.treeJet.setMinimumHeight(200)
        self.treeJet.setSortingEnabled(False)  # Wir sortieren manuell (nur Children, nicht Top-Level)
        self.treeJet.header().setSectionsClickable(True)
        self.treeJet.header().setSortIndicatorShown(True)
        self.treeJet.header().sectionClicked.connect(self._on_jet_header_clicked)
        self._jet_sort_col = -1
        self._jet_sort_asc = True

        # Custom expand/collapse indicators (reuse the same assets as Material)
        _j_tri_right_24 = resource_path("assets/images/triangle_right_24.png")
        _j_tri_right_16 = resource_path("assets/images/triangle_right_16.png")
        _j_tri_down_24 = resource_path("assets/images/triangle_down_24.png")
        _j_tri_down_16 = resource_path("assets/images/triangle_down_16.png")

        def _pick_icon(p24: str, p16: str) -> str:
            try:
                return p24 if os.path.exists(p24) else p16
            except Exception:
                return p16

        j_tri_right = _pick_icon(_j_tri_right_24, _j_tri_right_16)
        j_tri_down = _pick_icon(_j_tri_down_24, _j_tri_down_16)

        j_tri_right_qss = j_tri_right.replace("\\", "/")
        j_tri_down_qss = j_tri_down.replace("\\", "/")
        self.treeJet.setStyleSheet(f"""
            QTreeWidget {{ border: 1px solid {accent_gridline()}; background-color: #FFFFFF; color: #000000; }}
            QTreeWidget::item:selected {{ background: #CFE8CF; color: #000000; }}
            QTreeView::branch:closed:has-children {{ image: url("{j_tri_right_qss}"); }}
            QTreeView::branch:open:has-children {{ image: url("{j_tri_down_qss}"); }}
        """)

        self.butAddJet = QPushButton("+")
        self.butAddJet.setEnabled(False)

        # Suche ueber alle Gruppen: Jet-Name und Entwicklungsname
        self.searchJet = TreeSearch(self.treeJet, columns=(0, 5),
                                    placeholder="Search jet (all groups)…")
        jet_col = QVBoxLayout()
        jet_col.setContentsMargins(0, 0, 0, 0)
        jet_col.setSpacing(4)
        jet_col.addWidget(self.searchJet.edit)
        jet_col.addWidget(self.treeJet, 1)
        row_jet.addLayout(jet_col, 1)
        row_jet.addWidget(self.butAddJet, 0)

        jet_container = QWidget()
        jet_container.setLayout(row_jet)

        self.txtNumPlates = QLineEdit()
        self.txtNumPlates.setValidator(QIntValidator(1, 20, self))

        self.cmbHousing = PrettyComboBox()
        grid_jet.addWidget(QLabel("Housing"), 0, 0)
        grid_jet.addWidget(self.cmbHousing, 0, 1, 1, 2)

        grid_jet.addWidget(QLabel("Jet"), 1, 0)
        grid_jet.addWidget(jet_container, 1, 1, 1, 2)
        grid_jet.addWidget(QLabel("Number of Plates"), 2, 0)
        grid_jet.addWidget(self.txtNumPlates, 2, 1)

        self.plates_row = QHBoxLayout()
        self.plates_row.setSpacing(10)
        grid_jet.addLayout(self.plates_row, 3, 0, 1, 3)

        self.plate_labels: List[QLabel] = []
        self.plate_edits: List[QLineEdit] = []
        ordinals = [f"Plate {i}" for i in range(1, 21)]
        for i in range(20):
            mini = QVBoxLayout()
            mini.setSpacing(2)
            lab = QLabel(ordinals[i])
            lab.setAlignment(Qt.AlignHCenter | Qt.AlignBottom)
            edit = QLineEdit()
            edit.setValidator(QIntValidator(0, 100, self))
            edit.setMaximumWidth(60)
            lab.setVisible(False)
            edit.setVisible(False)
            mini.addWidget(lab)
            mini.addWidget(edit)
            wrap = QHBoxLayout()
            wrap.addLayout(mini)
            wrap.setContentsMargins(0, 0, 0, 0)
            self.plates_row.addLayout(wrap)
            self.plate_labels.append(lab)
            self.plate_edits.append(edit)

        self.txtPressure = QLineEdit()
        re_pressure = QRegularExpression(r"^\s*\d+(?:[.,]\d{1,2})?\s*$")
        self.txtPressure.setValidator(
            QRegularExpressionValidator(re_pressure, self))
        grid_jet.addWidget(QLabel("Air Pressure (bar)"), 4, 0)
        grid_jet.addWidget(self.txtPressure, 4, 1, 1, 2)

        self.tblJets = ReadOnlyTable(0, 5, on_delete_row=self._delete_jet_row,
                                     on_row_moved=self._on_jet_row_dragged)
        self.tblJets.setHorizontalHeaderLabels(
            ["Housing", "Jet", "Number of Plates", "Air Pressure (bar)", "Jet Plate(s)"])
        self.tblJets.verticalHeader().setVisible(False)
        self.tblJets.setStyleSheet("""
            QTableWidget { border: 1px solid #B5D7B5; background-color: #FFFFFF; }
            QHeaderView::section {
                background: #3f3f3f; color: white; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 6px 8px;
            }
            QTableWidget::item { padding: 6px; color: black; }
            QTableWidget::item:selected { background: #b7d6ff; color: black; }
        """
            .replace("#B5D7B5", accent_gridline()))
        header = self.tblJets.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.Interactive)
        self.tblJets.setColumnWidth(0, 150)
        self.tblJets.setColumnWidth(1, 180)
        self.tblJets.setColumnWidth(2, 150)
        self.tblJets.setColumnWidth(3, 170)
        self.tblJets.setColumnWidth(4, 220)
        # Delegate: nur Spalten 2+3 editierbar, Rest geschuetzt
        self.tblJets.setItemDelegate(_JetColProtectDelegate(self.tblJets))
        # Multi-Selektion fuer Kopieren
        self.tblJets.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # Spalten 2 (Plates) und 3 (Pressure) direkt editierbar
        self.tblJets.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        self.tblJets.itemChanged.connect(self._on_jet_item_changed)
        jl_outer.addWidget(self.tblJets, 1)

        # Button-Leiste unter tblJets
        jets_btn_row = QHBoxLayout()
        jets_btn_row.setSpacing(6)
        self.butJetCopy = QPushButton("Copy selected")
        self.butJetMoveUp = QPushButton("Up")
        self.butJetMoveDown = QPushButton("Down")
        for b in (self.butJetCopy, self.butJetMoveUp, self.butJetMoveDown):
            b.setFixedHeight(26)
            b.setMinimumWidth(80)
        jets_btn_row.addWidget(self.butJetCopy)
        jets_btn_row.addWidget(self.butJetMoveUp)
        jets_btn_row.addWidget(self.butJetMoveDown)
        jets_btn_row.addStretch(1)
        jl_outer.addLayout(jets_btn_row)

        self.tabs.addTab(self.tab_jet, _make_icon(False), "Jet")

        # --> Tab: Machine -->
        self.tab_machine = QFrame()
        mac = QVBoxLayout(self.tab_machine)
        mac.setContentsMargins(24, 12, 24, 24)
        mac.setSpacing(12)

        form_top = QFormLayout()
        mac.addLayout(form_top)
        self.cmbMachine = PrettyComboBox()
        form_top.addRow("Machine", self.cmbMachine)

        self.machine_grid = QGridLayout()
        self.machine_grid.setHorizontalSpacing(18)
        self.machine_grid.setVerticalSpacing(10)
        mac.addLayout(self.machine_grid, 1)
        mac.addItem(QSpacerItem(
            0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.tabs.addTab(self.tab_machine, _make_icon(False), "Machine")

        # --> Tab: Lab Machines -->
        self.tab_lab = QFrame()
        ll = QVBoxLayout(self.tab_lab)
        ll.setContentsMargins(24, 12, 24, 24)
        ll.setSpacing(10)

        lab_row = QHBoxLayout()
        self.cmbLabMachine = PrettyComboBox()
        self.butAddLabMachine = QPushButton("+")
        self.butAddLabMachine.setEnabled(False)
        lab_row.addWidget(QLabel("Lab Machine"), 0)
        lab_row.addWidget(self.cmbLabMachine, 1)
        lab_row.addWidget(self.butAddLabMachine, 0)
        ll.addLayout(lab_row)

        add_row = QHBoxLayout()
        self.lblAddCaption = QLabel("Additional Field")
        self.txtAdditional = QLineEdit()
        self.lblAddUnit = QLabel("")
        re_add = QRegularExpression(r"^\s*[+-]?\d+(?:[.,]\d{1,2})?\s*$")
        self._single_value_validator = QRegularExpressionValidator(re_add, self)
        # Permissiver: mehrere kommagetrennte Zahlen, fuer SeriesFreeform-
        # Lab Machines wie "Jet Air Consumption" (z.B. "4, 5, 6").
        re_add_csv = QRegularExpression(r"^\s*[+-]?\d+(?:[.,]\d{1,2})?\s*(,\s*[+-]?\d+(?:[.,]\d{1,2})?\s*)*,?\s*$")
        self._csv_value_validator = QRegularExpressionValidator(re_add_csv, self)
        self.txtAdditional.setValidator(self._single_value_validator)
        self.lblAddCaption.setVisible(False)
        self.txtAdditional.setVisible(False)
        self.lblAddUnit.setVisible(False)
        add_row.addWidget(self.lblAddCaption, 0)
        add_row.addWidget(self.txtAdditional, 0)
        add_row.addWidget(self.lblAddUnit, 0)

        # Itemat tension checkboxes (0.3 / 0.6 / 1.0 / 1.3 cN/dtex)
        self.lblTensionCaption = QLabel("Tension")
        self.lblTensionCaption.setVisible(False)
        add_row.addWidget(self.lblTensionCaption, 0)
        _TENSION_VALUES = ["0.3", "0.6", "1.0", "1.3"]
        self._tension_checkboxes: List[QCheckBox] = []
        for tv in _TENSION_VALUES:
            cb = QCheckBox(f"{tv} cN/dtex")
            cb.setVisible(False)
            cb.stateChanged.connect(self._update_add_lab_enabled)
            add_row.addWidget(cb, 0)
            self._tension_checkboxes.append(cb)

        add_row.addStretch(1)
        ll.addLayout(add_row)

        self.tblLabMachines = ReadOnlyTable(
            0, 2, on_delete_row=self._delete_lab_row)
        self.tblLabMachines.setHorizontalHeaderLabels(
            ["Lab Machine", "Additional Data"])
        self.tblLabMachines.verticalHeader().setVisible(False)
        self.tblLabMachines.horizontalHeader().setStretchLastSection(True)
        self.tblLabMachines.setStyleSheet("""
            QTableWidget { border: 1px solid #B5D7B5; background-color: #FFFFFF; }
            QHeaderView::section {
                background: #3f3f3f; color: white; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 6px 8px;
            }
            QTableWidget::item { padding: 6px; color: black; }
            QTableWidget::item:selected { background: #b7d6ff; color: black; }
        """
            .replace("#B5D7B5", accent_gridline()))
        ll.addWidget(self.tblLabMachines, 1)

        self.tabs.addTab(self.tab_lab, _make_icon(False), "Lab Machines")

        # Bottom bar
        root.addWidget(FooterBar())

    def _refresh_sidebar(self):
        """Baut die Sidebar-Navigation neu auf, falls sich der Access-Level
        seit dem letzten Aufbau geändert hat, sonst nur die Badges (siehe
        ui/widgets/sidebar_nav.py::refresh_lazy_sidebar())."""
        import app_meta
        try:
            level = int((app_meta.current_user or {}).get("access_level") or 0)
        except Exception:
            level = 0
        sidebar_nav.refresh_lazy_sidebar(self, level)

    def showEvent(self, event):
        try:
            self._refresh_sidebar()
        except Exception:
            pass
        super().showEvent(event)

    # -->-->-->- Helpers -->-->-->-
    def _keep_only_tabs(self, titles: set[str]):
        """Entfernt alle Tabs ausser den in titles genannten."""
        for i in range(self.tabs.count() - 1, -1, -1):
            if self.tabs.tabText(i) not in titles:
                self.tabs.removeTab(i)

    def _hide_row(self, label_widget: QLabel, field_widget: QWidget, hide: bool = True):
        """Zeigt/versteckt ein Label+Widget-Paar im Formular."""
        label_widget.setVisible(not hide)
        field_widget.setVisible(not hide)

    def _show_row(self, label_widget: QLabel, field_widget: QWidget, show: bool = True):
        """Zeigt ein Label+Widget-Paar im Formular (Gegenteil von _hide_row)."""
        label_widget.setVisible(show)
        field_widget.setVisible(show)

    # -->-->-->- DB-Lader -->-->-->-
    def _load_product_groups(self):
        """Produktgruppen (db/experiment_create.product_groups)."""
        self.cmbProductGroup.clear()
        for r in _ec.product_groups():
            self.cmbProductGroup.addItem(r["label"], r["id"])
        self.cmbProductGroup.setCurrentIndex(-1)
        self.strExperimentData[1] = ""

    def _load_order_types(self):
        """Bestellungstypen (db/experiment_create.order_types)."""
        self.cmbOrderType.clear()
        for r in _ec.order_types():
            self.cmbOrderType.addItem(r["label"], r["id"])
        self.cmbOrderType.setCurrentIndex(-1)
        self.strExperimentData[2] = ""

    def _load_projects(self):
        """Projekte (db/experiment_create.projects) plus "— none —" (user request
        2026-09-02: a chosen project must be clearable again); siehe
        _sync_project_from_request() für Auto-Fill+Lock bei verknüpftem Request."""
        self.cmbProject.clear()
        self.cmbProject.addItem("— none —", None)
        for r in _ec.projects():
            self.cmbProject.addItem(r["label"], r["id"])
        self.cmbProject.setCurrentIndex(0)

    def _sync_project_from_request(self) -> None:
        """Erzwingt+sperrt das Project-Dropdown auf das Projekt des verknüpften
        Experiment Requests, sofern dieser eines hinterlegt hat (Nutzerwunsch
        2026-09-02: "wenn ich eine Experiment Request hinterlege, dann soll
        aber immer die Projektnummer des requests niedergeschrieben werden -
        sofern das request eine hinterlegt hat"). Kein Request (oder ein
        Request ohne Projekt) ausgewählt → Dropdown bleibt frei editierbar."""
        if not hasattr(self, "cmbProject"):
            return
        rid = None
        try:
            rid = self._to_int_or_none(self.cmbExperimentRequest.currentData())
        except Exception:
            rid = None

        project_id = _ec.request_project(rid)

        if project_id is not None:
            self._select_combo_by_data(self.cmbProject, project_id)
            self.cmbProject.setEnabled(False)
            self.cmbProject.setToolTip(
                "Taken from the linked Experiment Request's project - cannot be changed here."
            )
        else:
            self.cmbProject.setEnabled(True)
            self.cmbProject.setToolTip("")

    def _on_experiment_request_changed(self, *_) -> None:
        """Callback wenn ein Experiment-Request aus der Combobox gewählt wird.

        Füllt Felder aus dem gewählten Request vor (Titel, Garn, Maschine usw.).
        """
        """Update UI bits when Experiment Request selection changes."""
        self._update_expreq_icon_visibility()
        # Remove the "attention" highlight once a request is actually selected.
        self._refresh_expreq_combo_highlight()
        try:
            self._sync_project_from_request()
        except Exception:
            pass
        try:
            self._check_safe()
        except Exception:
            pass

    def _load_open_experiment_requests(self):
        """Lädt alle offenen/genehmigten Experiment-Requests in die Combobox.

        Zeigt nur Requests mit RequestStatus = 3 (genehmigt).
        Anzeigeformat: "ProjectNumber - ProjectName - Titel".
        """
        try:
            self.cmbExperimentRequest.clear()
        except Exception:
            return

        # Platzhalter, damit klar ist, dass es ein Dropdown ist
        try:
            self.cmbExperimentRequest.addItem("— please select experiment request —", None)
        except Exception:
            pass

        self._set_expreq_combo_highlight(False)

        # approved, not linked, no prior versions: db/experiment_create.open_requests
        rows = _ec.open_requests()
        # Remember whether there are approved requests available.
        # We only want to highlight the dropdown as "attention" *until* the user selects one.
        self._expreq_has_approved = bool(rows)
        self._refresh_expreq_combo_highlight()
        for r in rows:
            self.cmbExperimentRequest.addItem(r["label"], r["id"])

        # Standard: Platzhalter selektiert lassen
        self.cmbExperimentRequest.setCurrentIndex(0)

        # Pending preset (z.B. gesetzt bevor die Liste geladen war)
        pending = getattr(self, "_preset_request_id_pending", None)
        if pending is not None:
            self._preset_request_id_pending = None
            self.preset_experiment_request(pending)


    def preset_experiment_request(self, request_id: int) -> None:
        """Selektiert einen Experiment Request in der Combobox (General-Tab).

        Wird aufgerufen wenn der User im Home-Screen «Create Experiment» aus
        dem Request-Preview-Dialog klickt.
        """
        if not hasattr(self, "cmbExperimentRequest"):
            return
        cmb = self.cmbExperimentRequest
        for i in range(cmb.count()):
            if cmb.itemData(i) == request_id:
                cmb.setCurrentIndex(i)
                return
        # Noch nicht in der Liste (z.B. weil _load_open_experiment_requests noch
        # nicht aufgerufen wurde) → nach dem Laden nochmals versuchen
        self._preset_request_id_pending = request_id

    def _refresh_expreq_combo_highlight(self) -> None:
        """Aktualisiert die Farbhervorhebung der Request-Combobox (grün = genehmigt)."""
        """Highlight Experiment Request dropdown only when choices exist but none is selected."""
        try:
            has_approved = bool(getattr(self, "_expreq_has_approved", False))
            rid = None
            if hasattr(self, "cmbExperimentRequest"):
                rid = self._to_int_or_none(self.cmbExperimentRequest.currentData())
            # Highlight only if there are approved requests AND no actual selection yet (placeholder).
            self._set_expreq_combo_highlight(bool(has_approved and not rid))
        except Exception:
            pass

    def _set_expreq_combo_highlight(self, has_approved: bool) -> None:
        """Setzt die Hintergrundfarbe der Request-Combobox."""
        """Set a subtle dark-red border on the Experiment Request dropdown."""
        if not hasattr(self, "cmbExperimentRequest"):
            return
        try:
            if not hasattr(self, "_expreq_combo_base_qss"):
                self._expreq_combo_base_qss = self.cmbExperimentRequest.styleSheet() or ""
            base = self._expreq_combo_base_qss or ""
            if has_approved:
                # Thinner + darker red (requested)
                highlight = (
                    "QComboBox{border:1px solid #8B0000;}"
                    "QComboBox:focus{border:1px solid #8B0000;}"
                )
                self.cmbExperimentRequest.setStyleSheet((base + "\n" + highlight).strip())
            else:
                self.cmbExperimentRequest.setStyleSheet(base)
        except Exception:
            pass

    def _update_expreq_icon_visibility(self) -> None:
        """Zeigt/versteckt das ER-Icon neben der Request-Combobox."""
        """Show the Experiment Request icon in the top bar only when a request is selected in General tab."""
        try:
            if not hasattr(self, "btn_experiment_request"):
                return
            # Only in create mode (General tab shows the dropdown)
            if getattr(self, "mode", "") != "create":
                self.btn_experiment_request.setVisible(False)
                return
            if not hasattr(self, "cmbExperimentRequest"):
                self.btn_experiment_request.setVisible(False)
                return
            rid = self._to_int_or_none(self.cmbExperimentRequest.currentData())
            # index 0 is placeholder; treat None as "not selected"
            self.btn_experiment_request.setVisible(bool(rid))
        except Exception:
            try:
                self.btn_experiment_request.setVisible(False)
            except Exception:
                pass

    def _open_selected_experiment_request_popup(self) -> None:
        """Open a *non-modal* read-only Experiment Request popup for the selected request.

        The popup is only meant to stay open while the user continues working in this
        screen. It is auto-closed when saving or leaving this screen.
        """
        rid = None
        try:
            rid = self._to_int_or_none(self.cmbExperimentRequest.currentData())
        except Exception:
            rid = None
        if not rid:
            return
        try:
            # If already open, just bring it to front.
            if self._expreq_popup is not None and self._expreq_popup.isVisible():
                try:
                    self._expreq_popup.raise_()
                    self._expreq_popup.activateWindow()
                except Exception:
                    pass
                return

            # Create a non-modal dialog with this screen as parent.
            from ui.screen_show_experiment import _ExperimentRequestReadOnlyDialog
            dlg = _ExperimentRequestReadOnlyDialog(self, request_id=rid)
            dlg.setWindowModality(Qt.NonModal)
            dlg.setModal(False)
            dlg.setAttribute(Qt.WA_DeleteOnClose, True)

            def _on_closed(*_args):
                self._expreq_popup = None

            try:
                dlg.finished.connect(_on_closed)  # type: ignore[attr-defined]
            except Exception:
                try:
                    dlg.destroyed.connect(_on_closed)  # type: ignore[attr-defined]
                except Exception:
                    pass

            self._expreq_popup = dlg
            dlg.show()
        except Exception as e:
            try:
                show_error(self, "Open Experiment Request", "The experiment request could not be opened.", e)
            except Exception:
                pass

    def _close_experiment_request_popup(self) -> None:
        """Close the non-modal Experiment Request popup if it is open."""
        try:
            if self._expreq_popup is not None:
                try:
                    self._expreq_popup.close()
                finally:
                    self._expreq_popup = None
        except Exception:
            self._expreq_popup = None


    def _load_backlog_status(self):
        """Backlog-Status für neue TrialSeries laden (nur 'Backlog' und 'In Progress')."""
        if not hasattr(self, "cmbBacklogStatus"):
            return
        self.cmbBacklogStatus.clear()
        for r in _ec.backlog_statuses():   # Backlog, In Progress
            self.cmbBacklogStatus.addItem(r["name"], r["id"])

        if self.cmbBacklogStatus.count() > 0:
            idx = self.cmbBacklogStatus.findText("Backlog")
            self.cmbBacklogStatus.setCurrentIndex(idx if idx >= 0 else 0)
        else:
            self.cmbBacklogStatus.setCurrentIndex(-1)

    def _load_existing_experiments(self):
        """Für addSeries/addTrials: Combo mit bestehenden Experimenten befüllen.
           Anzeigeformat: YEAR-PGOT-NNN (z. B. 2025-70-006 bei PG=7, OT=0)"""
        self.cmbExistingExperiment.clear()
        try:
            rows = _ec.existing_experiments()
        except Exception as e:
            show_error(self, "Existing Experiment", "The experiment could not be loaded.", e)
            return
        for r in rows:
            self.cmbExistingExperiment.addItem(
                r["label"], (r["id"], r["machine_id"], r["year"], r["pg"], r["ot"], r["num"]))
        if self.existing_experiment_id is not None:
            for i in range(self.cmbExistingExperiment.count()):
                data = self.cmbExistingExperiment.itemData(i)
                if data and data[0] == self.existing_experiment_id:
                    self.cmbExistingExperiment.setCurrentIndex(i)
                    break
        else:
            self.cmbExistingExperiment.setCurrentIndex(-1)

    def _load_trials_for_selection(self, exp_id: int, series_id: int):
        # UI leeren
        try:
            if hasattr(self, "_trials_grid_general"):
                while self._trials_grid_general.count():
                    item = self._trials_grid_general.takeAt(0)
                    w = item.widget()
                    if w:
                        w.deleteLater()
        except Exception:
            pass

        # Guard
        if series_id is None or series_id < 0:
            return
        rows = [{"TID": t["id"], "TNo": t["number"]} for t in _ec.trials_of_series(series_id)]

        self._trial_checks = []
        cols = 5
        idx = 0

        # Toggle button (select/unselect all)
        try:
            # Recreate each time to avoid stale widget
            self.butTrialsToggle = QPushButton("Select all")
            self.butTrialsToggle.setObjectName("butTrialsToggle")
            self.butTrialsToggle.clicked.connect(self._trials_toggle_all)
            self._trials_grid_general.addWidget(
                self.butTrialsToggle, 0, 0, 1, 5)
        except Exception:
            pass

        for r in rows:
            try:
                tid = int(r.get("TID"))
            except Exception:
                tid = r.get("TID")
            label = str(r.get("TNo") if r.get("TNo")
                        not in (None, '') else r.get("TID"))
            cb = QCheckBox(format_trial_number(label))
            cb.setChecked(True)
            # High-contrast checkbox styling (dynamic color for addlabmachines)
            _style = """
                QCheckBox { color: #111111; font-weight: 600; font-size: 13px; }
                QCheckBox::indicator { width: 18px; height: 18px; }
                QCheckBox::indicator:checked { background: #1e88e5; border: 1px solid #1e88e5; }
                QCheckBox::indicator:unchecked { background-color: #ffffff; border: 1px solid #3f3f3f; }
                QCheckBox::indicator:disabled { background: #cccccc; border: 1px solid #aaaaaa; }
            """
            if self.mode == "addlabmachines":
                _style = _style.replace("#1e88e5", "#BA29E4")
            cb.setStyleSheet(_style)
            if hasattr(self, "_trials_grid_general"):
                rix = 1 + (idx // cols)
                cix = idx % cols
                self._trials_grid_general.addWidget(cb, rix, cix)
            self._trial_checks.append((tid, cb, label))
            try:
                cb.stateChanged.connect(self._on_trial_checkbox_changed)
            except Exception:
                pass
            idx += 1

        # After building list, refresh states
        try:
            self._on_trial_checkbox_changed()
        except Exception:
            pass

    def _load_series_for_experiment(self, exp_id: int):
        """Für addTrials: Serien des Experiments laden."""
        self.cmbExistingSeries.clear()
        try:
            rows = _ec.series_of_experiment(exp_id)
        except RuntimeError as e:
            QMessageBox.warning(self, "Trial Series", str(e))
            return
        for r in rows:
            self.cmbExistingSeries.addItem(r["name"], r["id"])
        self.cmbExistingSeries.setCurrentIndex(0 if rows else -1)

    def _load_yarns(self):
        """Material-Auswahl als einklappbarer Tree nach YarnGroup
        (Daten: db/experiment_create.yarn_tree, Qt-free, shared with the web app).
        Gruppen-Header "<GroupNumber> | <GroupName>", Spalte 1 = Spulen-Symbol."""
        self.treeMaterial.clear()
        tree = _ec.yarn_tree()
        if not tree["groups"]:
            self.butAddMaterial.setEnabled(False)
            self.butAddTrialPly.setEnabled(False)
            return
        self._yarn_colours, _ = load_yarn_colours()
        # Bestand pro Garn (eine Abfrage fuer alle) -> Spulen-Symbol + Tooltip
        self._material_stock_summary = _yarn_locations.load_stock_summary(
            y["id"] for g in tree["groups"] for y in g["yarns"])
        _sym_in = _sym_none = None
        try:
            _sym_in = QIcon(_yarn_locations.symbol_path(True))
            _sym_none = QIcon(_yarn_locations.symbol_path(False))
        except Exception:
            pass
        any_children = False
        target_item = None
        for g in tree["groups"]:
            top = QTreeWidgetItem([g["label"]])
            top.setData(0, Qt.UserRole, {"kind": "group"})
            try:
                f = top.font(0)
                f.setBold(True)
                top.setFont(0, f)
                top.setForeground(0, QColor("#39A650"))
            except Exception:
                pass
            self.treeMaterial.addTopLevelItem(top)
            top.setFirstColumnSpanned(True)
            if g["label"] == tree["open"] and target_item is None:
                target_item = top
            for y in g["yarns"]:
                yid = y["id"]
                child = QTreeWidgetItem([y["name"]])
                child.setData(0, Qt.UserRole, {"kind": "yarn", "yarn_id": yid, "yarn_name": y["name"]})
                child.setIcon(0, colour_icon(self._yarn_colours.get(yid)))
                child.setToolTip(0, colour_tooltip(self._yarn_colours.get(yid)))
                _stock = self._material_stock_summary.get(yid)
                _sym = _sym_in if _stock is not None else _sym_none
                if _sym is not None:
                    child.setIcon(1, _sym)
                child.setToolTip(1, _yarn_locations.stock_symbol_tooltip(_stock))
                top.addChild(child)
                any_children = True

        # Default: only "1 | Standard Yarn" open (else the first group);
        # without any yarn everything open so the user sees something
        for i in range(self.treeMaterial.topLevelItemCount()):
            it = self.treeMaterial.topLevelItem(i)
            it.setExpanded(it is target_item or not any_children)

        self.treeMaterial.clearSelection()
        if hasattr(self, "searchMaterial"):
            self.searchMaterial.reapply()
        self._update_add_material_enabled()

    def _load_jets(self):
        """Jet-Auswahl als einklappbarer Tree nach JetGroup mit Geometrie und
        Titerbereich (Daten: db/experiment_create.jet_tree, Qt-free, shared with
        the web app)."""
        if hasattr(self, "treeJet"):
            self.treeJet.clear()
        else:
            return
        groups = _ec.jet_tree()
        any_children = False
        for g in groups:
            top = QTreeWidgetItem([g["label"], "", "", "", "", "", "", ""])
            top.setData(0, Qt.UserRole, {"kind": "group"})
            try:
                f = top.font(0)
                f.setBold(True)
                top.setFont(0, f)
                top.setForeground(0, QColor("#39A650"))
            except Exception:
                pass
            self.treeJet.addTopLevelItem(top)
            top.setFirstColumnSpanned(True)
            for jt in g["jets"]:
                child = QTreeWidgetItem([jt["name"]] + [jt["geo"][k] for k in _ec.JET_GEO_COLUMNS]
                                        + [jt["titer_range"], jt["ideal_titer"]])
                child.setData(0, Qt.UserRole, {"kind": "jet", "jet_id": jt["id"], "jet_name": jt["name"]})
                # Numerische Spalten rechtsbündig
                for col_idx in (1, 2, 3, 4):
                    child.setTextAlignment(col_idx, Qt.AlignRight | Qt.AlignVCenter)
                top.addChild(child)
                any_children = True

        # Default: expand first group (oder alles, wenn keine Jets existieren)
        if self.treeJet.topLevelItemCount() > 0:
            self.treeJet.topLevelItem(0).setExpanded(True)
        if not any_children:
            for i in range(self.treeJet.topLevelItemCount()):
                self.treeJet.topLevelItem(i).setExpanded(True)

        # Spaltenbreiten anpassen
        for col_idx in range(self.treeJet.columnCount()):
            self.treeJet.resizeColumnToContents(col_idx)
        self.treeJet.setColumnWidth(0, max(self.treeJet.columnWidth(0), 120))

        # Sortier-Zustand zurücksetzen
        self._jet_sort_col = -1
        self._jet_sort_asc = True
        self.treeJet.header().setSortIndicator(-1, Qt.AscendingOrder)

        self.treeJet.clearSelection()
        self.butAddJet.setEnabled(False)
        if hasattr(self, "searchJet"):
            self.searchJet.reapply()

    def _on_jet_header_clicked(self, logical_col: int):
        """Sortiert Children innerhalb jeder Gruppe nach Spalte logical_col.
        Top-Level-Gruppen bleiben an ihrer Position."""
        if self._jet_sort_col == logical_col:
            self._jet_sort_asc = not self._jet_sort_asc
        else:
            self._jet_sort_col = logical_col
            self._jet_sort_asc = True

        order = Qt.AscendingOrder if self._jet_sort_asc else Qt.DescendingOrder
        self.treeJet.header().setSortIndicator(logical_col, order)

        for i in range(self.treeJet.topLevelItemCount()):
            top = self.treeJet.topLevelItem(i)
            n = top.childCount()
            if n < 2:
                continue

            # Children rausnehmen
            children = [top.takeChild(0) for _ in range(n)]

            # Sortierkey: numerisch wenn möglich, sonst String
            def _sort_key(item: QTreeWidgetItem):
                val = item.text(logical_col)
                try:
                    return (0, float(val.replace(",", ".")))
                except (ValueError, AttributeError):
                    return (1, str(val).lower())

            children.sort(key=_sort_key, reverse=not self._jet_sort_asc)

            for child in children:
                top.addChild(child)

    def _load_housing(self):
        """Befüllt cmbHousing aus tblHousing.HousingName; behält bestehende Auswahl."""
        if not hasattr(self, "cmbHousing"):
            return
        current_id = self.cmbHousing.currentData()
        self.cmbHousing.blockSignals(True)
        self.cmbHousing.clear()
        self.cmbHousing.addItem("", None)          # leerer Platzhalter
        for r in _ec.housings():
            self.cmbHousing.addItem(r["name"], r["id"])
        # Auswahl wiederherstellen (z.B. nach Jet-Add)
        if current_id is not None:
            idx = self.cmbHousing.findData(current_id)
            if idx >= 0:
                self.cmbHousing.setCurrentIndex(idx)
        self.cmbHousing.blockSignals(False)
        # _load_housing() kann mehrfach laufen (z.B. nach Jet-Add) und
        # verbindet cmbHousing dabei jedes Mal neu - ein unbedingtes
        # disconnect() (ohne verbundenen Slot) läuft zwar dank try/except
        # nie auf einen Fehler, aber Qt loggt dabei trotzdem eine
        # RuntimeWarning auf stderr (unabhängig vom except) - daher hier
        # stattdessen ein Flag, das den ersten (verbindungslosen) Aufruf
        # ganz vermeidet statt nur dessen Exception abzufangen.
        if getattr(self, "_housing_signal_connected", False):
            try:
                self.cmbHousing.currentIndexChanged.disconnect(self._on_housing_changed)
            except Exception:
                pass
        self.cmbHousing.currentIndexChanged.connect(self._on_housing_changed)
        self._housing_signal_connected = True

    def _on_housing_changed(self):
        self._on_jet_inputs_changed()
        self._check_jet()
        self._check_safe()

    def _load_machines(self):
        """Maschinen mit Joker-Flag (db/experiment_create.machines)."""
        self.cmbMachine.clear()
        try:
            rows = _ec.machines()
        except RuntimeError as e:
            QMessageBox.warning(self, "Machine", str(e))
            return
        for r in rows:
            self.cmbMachine.addItem(r["name"], r["id"])
            # Joker-Flag als zusätzliches Item-Data (UserRole+1) ablegen
            self.cmbMachine.setItemData(self.cmbMachine.count() - 1, bool(r["joker"]), Qt.UserRole + 1)
        self.cmbMachine.setCurrentIndex(-1)

    def _load_lab_machines(self):
        # _lab_machines ist ein dict: LMID -> Meta (db/trial_actions.load_lab_machines)
        self._lab_machines.clear()
        self.cmbLabMachine.clear()

        rows = _trial_actions.load_lab_machines()
        if rows is None:
            QMessageBox.warning(self, "Lab Machines",
                                "Table 'tblLabMachines' not found.")
            return

        for r in rows:
            self.cmbLabMachine.addItem(str(r.get("LMName") or "").strip(), r.get("LMID"))
            self._lab_machines[int(r.get("LMID"))] = r

        self.cmbLabMachine.setCurrentIndex(-1)


    # ---------- Legacy Import (manual Experiment ID) ----------
    def _parse_legacy_experiment_id(self, text: str):
        """Parse 'YYYY-<PGOT>-NNN' where <PGOT> is ProductGroup+OrderType concatenated.
        Returns (year:str, pg:int, ot:int, num:str) or None.
        """
        t = (text or "").strip()
        m = re.match(r"^(\d{4})-(\d+)-(\d{3})$", t)
        if not m:
            return None
        year, mid, num = m.group(1), m.group(2), m.group(3)
        if len(mid) < 2:
            return None
        try:
            ot = int(mid[-1])
            pg = int(mid[:-1])
        except Exception:
            return None
        return year, pg, ot, num

    def _on_legacy_experiment_id_changed(self):
        if self.mode != "legacy":
            return
        parsed = self._parse_legacy_experiment_id(self.txtExperimentNumber.text())
        if not parsed:
            # Keep user text; validation will block save anyway.
            self._check_general()
            self._check_safe()
            return
        year, pg, ot, num = parsed
        # Persist year for save
        self.strExperimentData[0] = year
        self.strExperimentData[1] = str(pg)
        self.strExperimentData[2] = str(ot)
        self.strExperimentData[3] = num

        # Try to select matching PG/OT in combos (best effort)
        try:
            self._select_combo_by_data(self.cmbProductGroup, pg)
        except Exception:
            pass
        try:
            self._select_combo_by_data(self.cmbOrderType, ot)
        except Exception:
            pass

        # Normalise display (keeps formatting consistent)
        try:
            self.txtExperimentNumber.setText(f"{year}-{pg}{ot}-{num}")
        except Exception:
            pass

        self._check_general()
        self._check_safe()

    def _select_combo_by_data(self, combo, value: int):
        for i in range(combo.count()):
            try:
                if int(combo.itemData(i)) == int(value):
                    combo.setCurrentIndex(i)
                    return True
            except Exception:
                continue
        return False


    # -->-->-->- Signals -->-->-->-
    def _wire_signals(self):
        # General
        self.cmbProductGroup.currentIndexChanged.connect(
            self._on_general_changed)
        self.cmbOrderType.currentIndexChanged.connect(self._on_general_changed)
        self.cmbExperimentRequest.currentIndexChanged.connect(self._check_safe)
        self.cmbExistingExperiment.currentIndexChanged.connect(
            self._on_existing_experiment_changed)
        self.cmbExistingSeries.currentIndexChanged.connect(
            self._on_existing_series_changed)

        # Lab Machines
        self.cmbLabMachine.currentIndexChanged.connect(
            self._on_lab_machine_changed)
        self.txtAdditional.textChanged.connect(self._update_add_lab_enabled)
        self.butAddLabMachine.clicked.connect(self._add_lab_machine)

        # Material
        self.txtSeriesName.textChanged.connect(self._on_series_name_changed)
        self.treeMaterial.itemSelectionChanged.connect(self._update_add_material_enabled)
        self.treeMaterial.itemClicked.connect(self._on_material_tree_clicked)
        self.butAddMaterial.clicked.connect(self._add_material)
        self.butAddTrialPly.clicked.connect(self._add_trial_ply)

        # Jet
        self.treeJet.itemSelectionChanged.connect(self._on_jet_inputs_changed)
        self.txtNumPlates.textChanged.connect(self._on_numplates_changed)
        self.txtPressure.textChanged.connect(self._on_jet_inputs_changed)
        self.butAddJet.clicked.connect(self._add_jet_row)
        self.butJetCopy.clicked.connect(self._copy_selected_jet_rows)
        self.butJetMoveUp.clicked.connect(self._move_jet_row_up)
        self.butJetMoveDown.clicked.connect(self._move_jet_row_down)
        for e in getattr(self, "plate_edits", []):
            e.textChanged.connect(self._on_jet_inputs_changed)

        # Machine
        self.cmbMachine.currentIndexChanged.connect(self._on_machine_changed)

        # Lab Machines
        self.cmbLabMachine.currentIndexChanged.connect(
            self._on_lab_machine_changed)
        self.txtAdditional.textChanged.connect(self._update_add_lab_enabled)
        self.butAddLabMachine.clicked.connect(self._add_lab_machine)

    # -->-->-->- Modus -->-->-->-
    def _apply_mode_create(self):
        for i in range(5):
            self.tabs.setTabIcon(i, _make_icon(False))
        self.tabs.setCurrentIndex(0)

        # Sichtbarkeit + Label‑Hiding
        self._hide_row(self._lbl_pg,  self.cmbProductGroup, False)
        self._hide_row(self._lbl_ot,  self.cmbOrderType, False)
        self._hide_row(self._lbl_exp_request, self.cmbExperimentRequest, False)
        self._hide_row(self._lbl_project, self.cmbProject, False)
        self._hide_row(self._lbl_num, self.txtExperimentNumber, False)
        self._hide_row(self._lbl_exp, self.cmbExistingExperiment, True)
        self._hide_row(self._lbl_ser, self.cmbExistingSeries, True)

        self.cmbMachine.setEnabled(True)
        self.btn_back_chip.setVisible(False)
        self.lbl_small_title.setText("New Experiment – fill all tabs")
        self.tabs.setTabEnabled(1, True)   # Material

    def _apply_mode_addseries(self):
        for i in range(5):
            self.tabs.setTabIcon(i, _make_icon(False))
        self.tabs.setCurrentIndex(0)

        # Nur Existing Experiment anzeigen — Labels der anderen Felder verbergen
        self._hide_row(self._lbl_pg,  self.cmbProductGroup, True)
        self._hide_row(self._lbl_ot,  self.cmbOrderType, True)
        self._hide_row(self._lbl_exp_request, self.cmbExperimentRequest, True)
        self._hide_row(self._lbl_project, self.cmbProject, True)
        self._hide_row(self._lbl_num, self.txtExperimentNumber, True)
        self._hide_row(self._lbl_exp, self.cmbExistingExperiment, False)
        self._hide_row(self._lbl_ser, self.cmbExistingSeries, True)

        self.cmbMachine.setEnabled(True)
        self.btn_back_chip.setVisible(False)
        self.lbl_small_title.setText(
            "Add Trial Series – choose existing experiment")
        self.tabs.setTabEnabled(1, True)   # Material benötigt

    def _apply_mode_addtrials(self):
        try:
            for i in range(self.tabs.count()):
                self.tabs.setTabIcon(i, _make_icon(False))
        except Exception:
            pass
        self.tabs.setCurrentIndex(0)

        # Existing Experiment + Series anzeigen — andere verbergen (inkl. Labels)
        self._hide_row(self._lbl_pg,  self.cmbProductGroup, True)
        self._hide_row(self._lbl_ot,  self.cmbOrderType, True)
        self._hide_row(self._lbl_exp_request, self.cmbExperimentRequest, True)
        self._hide_row(self._lbl_project, self.cmbProject, True)
        self._hide_row(self._lbl_num, self.txtExperimentNumber, True)
        # In "addtrials" sollen SeriesName/Backlog-Infos im General-Tab nicht sichtbar sein
        self._hide_row(self._lbl_series, self.txtSeriesName, True)
        self._hide_row(self._lbl_backlog_status, self.cmbBacklogStatus, True)
        self._hide_row(self._lbl_backlog_prio, self.cmbBacklogPrio, True)
        # General: Experiment + Serie anzeigen aber disabled (werden per prefill gesetzt)
        self._hide_row(self._lbl_exp, self.cmbExistingExperiment, False)
        self._hide_row(self._lbl_ser, self.cmbExistingSeries, False)
        self.cmbExistingExperiment.setEnabled(False)
        self.cmbExistingSeries.setEnabled(False)

        self.cmbMachine.setEnabled(False)

        # Nur General + Material + Jet + Machine + Lab Machines
        self._keep_only_tabs({"General", "Material", "Jet", "Machine", "Lab Machines"})

        # Jet-Tab: voll editierbar (User setzt Jet für neue Trials)
        try:
            self.treeJet.setEnabled(True)
            self.butAddJet.setEnabled(False)  # wird durch _jet_inputs_valid aktiviert
            self.butAddJet.setVisible(True)
            self.butJetCopy.setEnabled(True)
            self.butJetMoveUp.setEnabled(True)
            self.butJetMoveDown.setEnabled(True)
            self.cmbHousing.setEnabled(True)
            self.tblJets.setEditTriggers(
                QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        except Exception:
            pass

        self.lbl_small_title.setText(
            "Select experiment & series, then configure trials")

        # Im addtrials-Modus: Back-Chip zeigt zurück zum Experiment (Ersatz
        # für den früheren Header-Back-Button, siehe _build_ui()-Docstring).
        self.btn_back_chip.setVisible(callable(self.on_back_experiment))

        # Material leer + editierbar; Lab Machines frei
        self._set_material_readonly(False)
        self._set_lab_readonly(False)

        self._check_general()
        self._check_safe()

    # -->-->-->- Validierung -->-->-->-
    def _check_all(self):
        self._check_general()
        self._check_material()
        self._check_jet()
        self._check_machine()
        self._check_lab()
        self._check_safe()

    def _tab_index_by_title(self, title: str):
        """Return tab index by visible title, or None."""
        try:
            for i in range(self.tabs.count()):
                if str(self.tabs.tabText(i)).strip().lower() == str(title).strip().lower():
                    return i
        except Exception:
            pass
        return None

    def _trials_toggle_all(self):
        """Toggle all trial checkboxes (only in addlabmachines)."""
        if self.mode != "addlabmachines":
            return
        # Decide action: if any unchecked -> check all; else uncheck all
        any_unchecked = False
        for _, cb, _ in getattr(self, "_trial_checks", []):
            if not cb.isChecked():
                any_unchecked = True
                break
        new_state = True if any_unchecked else False
        for _, cb, _ in getattr(self, "_trial_checks", []):
            cb.blockSignals(True)
            cb.setChecked(new_state)
            cb.blockSignals(False)
        # Update toggle text
        try:
            self.butTrialsToggle.setText(
                "Deselect all" if new_state else "Select all")
        except Exception:
            pass
        # Update icons/save
        self._on_trial_checkbox_changed()

    def _on_trial_checkbox_changed(self):
        """React to single trial checkbox state changes in addlabmachines."""
        if self.mode != "addlabmachines":
            return
        # Update toggle button text based on whether all are checked
        try:
            boxes = [cb for _, cb, _ in getattr(self, "_trial_checks", [])]
            all_checked = bool(boxes) and all(cb.isChecked() for cb in boxes)
            self.butTrialsToggle.setText(
                "Deselect all" if all_checked else "Select all")
        except Exception:
            pass
        # Recompute general status (green only if at least one trial selected)
        self._check_general(update_icon=True)
        # Update Save enabled via existing addlabmachines updater
        try:
            self._update_lab_state_addlabmachines()
        except Exception:
            # Fallback: still run _check_safe to avoid stale button
            self._check_safe()

    def _update_lab_state_addlabmachines(self):
        """In addlabmachines mode: set Lab Machines tab icon and Save enabled based on presence of _lab_data and general selection."""
        if self.mode != "addlabmachines":
            return
        ok_lab = len(getattr(self, "_lab_data", [])) >= 1
        try:
            idx = self._tab_index_by_title("Lab Machines")
            if idx is None:
                idx = 4  # fallback
            self.tabs.setTabIcon(idx, _make_icon(ok_lab))
        except Exception:
            pass
        # Save enabled only if General ok (exp+series) and at least one lab machine defined
        try:
            gen_ok = self._check_general(False)
        except Exception:
            gen_ok = True
        self.butSave.setEnabled(bool(ok_lab and gen_ok))

    def _save_addlabmachines(self):
        """Assign selected lab machines to the checked trials in addlabmachines mode."""
        # Validate selections
        if self.cmbExistingExperiment.currentIndex() < 0 or self.cmbExistingSeries.currentIndex() < 0:
            QMessageBox.information(
                self, "Save", "Please select experiment and series.")
            return

        exp_id = int(self.cmbExistingExperiment.currentData()[0])
        ts_id = int(self.cmbExistingSeries.currentData())

        if not getattr(self, "_lab_data", None):
            QMessageBox.information(
                self, "Save", "Please add at least one lab machine.")
            return

        # Trial-Checkboxen sind nur fuer normale (PerTrial) Lab Machines noetig.
        # SeriesFreeform-Maschinen (z.B. Jet Air Consumption) haengen direkt an
        # der Series und brauchen keine Trial-Auswahl.
        has_per_trial = any(
            str(lm.get("RowMode") or "").strip().lower() != "seriesfreeform"
            for lm in self._lab_data
        )
        selected_trial_ids = self._get_checked_trial_ids()
        if has_per_trial and not selected_trial_ids:
            QMessageBox.information(
                self, "Save", "Please tick at least one trial.")
            return

        # Writing: db/experiment_create.add_lab_machines (Qt-free, shared with the web app)
        try:
            user_id = app_meta.current_user.get("id") if app_meta.current_user else None
        except Exception:
            user_id = None
        try:
            res = _ec.add_lab_machines(ts_id, selected_trial_ids, self._lab_data, user_id)
        except Exception as e:
            show_error(self, "Save failed", "The experiment could not be saved.", e)
            return
        msg_lines = [
            "Lab Machines zugewiesen.",
            f"Experiment ID: {exp_id} • Series: {ts_id}",
            f"Created: {res['created']} • Skipped (already exists): {res['skipped']}",
        ]
        jet_line = _ec.jet_air_message(res["jet_air"])
        if jet_line:
            msg_lines.append(jet_line)
        QMessageBox.information(self, "Saved", "\n".join(msg_lines))

    def _save_addtrials(self):
        """Erstellt neue Trials in der gewählten TrialSeries.
        Gleiche Logik wie create, aber Experiment + Series bereits vorhanden.
        Anzahl Trials = Jets × Platten (identisch mit normalem Create).
        Schreiben: db/trial_actions.add_trials (Qt-free, shared with the web app).
        """
        if self.cmbExistingExperiment.currentIndex() < 0 or self.cmbExistingSeries.currentIndex() < 0:
            QMessageBox.information(self, "Save", "Please select experiment and series.")
            return
        if not self._materials_data:
            QMessageBox.information(self, "Save", "Please add at least one material.")
            return
        if not self._jets_data:
            QMessageBox.information(self, "Save", "Please add at least one jet.")
            return

        exp_data = self.cmbExistingExperiment.currentData()
        exp_id   = int(exp_data[0])
        ts_id    = int(self.cmbExistingSeries.currentData())

        # Trial-Tabelle + Spalten-Map
        trial_table = "tblTrial"
        if not table_exists(trial_table):
            QMessageBox.critical(self, "Save", "Table 'tblTrial' not found.")
            return
        tr_cols = get_columns_map(trial_table)

        # Dynamische Machine-Felder aus _machine_field_widgets lesen
        ts_cols_map: Dict[str, str] = get_columns_map("tblTrialSettings") \
            if table_exists("tblTrialSettings") else {}
        machine_dynamic_cols_trial: List[Tuple[str, Any]] = []
        machine_dynamic_cols_settings: List[Tuple[str, Any]] = []
        for lab, widget, fno, orig, storage in self._machine_field_widgets:
            if isinstance(widget, QComboBox):
                val = widget.currentData()
                if val is None:
                    continue
            else:
                txt = widget.text().strip()
                if not txt:
                    continue
                val = self._to_float_or_none(txt)
                if val is None:
                    ival = self._to_int_or_none(txt)
                    val = ival if ival is not None else txt
            orig_col = orig or lab.text().strip()
            if storage == "tbltrialsettings":
                real = resolve_field([orig_col], ts_cols_map)
                if real:
                    machine_dynamic_cols_settings.append((real, val))
            else:
                real = resolve_field([orig_col], tr_cols)
                if real:
                    machine_dynamic_cols_trial.append((real, val))

        try:
            new_trial_ids = _trial_actions.add_trials(
                ts_id, self._jets_data, self._materials_data, self._lab_data,
                machine_dynamic_cols_trial, machine_dynamic_cols_settings)

            if callable(self.on_open_experiment):
                num = exp_data[5]
                exp_label = (f"{exp_data[2]}-{str(exp_data[3])}{str(exp_data[4])}-"
                             f"{str(num).zfill(3) if str(num).isdigit() else num}")
                self.on_open_experiment(exp_id, ts_id, exp_label)
            else:
                QMessageBox.information(
                    self, "Gespeichert",
                    f"{len(new_trial_ids)} trial(s) created.")

        except Exception as e:
            show_error(self, "Error", "The trials could not be created.", e)


    def _check_safe(self):
        ok = all([
            self._check_general(False),
            self._check_material(False),
            self._check_jet(False),
            self._check_machine(False),
            self._check_lab(False),
        ])
        self.butSave.setEnabled(ok)

    def _check_general(self, update_icon: bool = True) -> bool:
        if self.mode == "addseries":
            # Existing Experiment muss gewählt sein UND Series Name darf nicht leer sein
            ok = (
                self.cmbExistingExperiment.currentIndex() >= 0
                and bool(self.txtSeriesName.text().strip())
            )
        elif self.mode in ("addtrials", "addlabmachines"):
            ok = (
                self.cmbExistingExperiment.currentIndex() >= 0
                and self.cmbExistingSeries.currentIndex() >= 0
            )
            if self.mode == "addlabmachines":
                try:
                    has_trials = any(
                        cb.isChecked() for _, cb, _ in getattr(self, "_trial_checks", [])
                    )
                except Exception:
                    has_trials = False
                ok = ok and has_trials
        else:
            # Create-Mode: Product Group, Order Type, Experiment Number UND Series Name nötig
            ok = bool(
                self.cmbProductGroup.currentIndex() >= 0
                and self.cmbOrderType.currentIndex() >= 0
                and self.txtExperimentNumber.text().strip()
                and self.txtSeriesName.text().strip()
            )
        if update_icon:
            self.tabs.setTabIcon(0, _make_icon(ok))
        return ok

    def _check_material(self, update_icon: bool = True) -> bool:
        # addtrials: mindestens 1 Yarn nötig (User gibt es selbst ein)
        ok = self.tblYarns.rowCount() > 0
        if update_icon:
            self.tabs.setTabIcon(1, _make_icon(ok))
        return ok

    def _check_jet(self, update_icon: bool = True) -> bool:
        if self.mode == "addtrials":
            has_rows = self.tblJets.rowCount() > 0
            ok = has_rows and all(
                j.get("HousingID") is not None for j in getattr(self, "_jets_data", []))
            if update_icon:
                try:
                    self.tabs.setTabIcon(2, _make_icon(ok))
                except Exception:
                    pass
            return ok
        has_rows = self.tblJets.rowCount() > 0
        # Wenn bereits Jets in der Tabelle sind (z.B. nach Prefill beim Kopieren),
        # reicht es, dass alle eingetragenen Jets ein Housing haben.
        # Das cmbHousing-Dropdown betrifft nur den *nächsten* hinzuzufügenden Jet.
        if has_rows:
            all_have_housing = all(
                j.get("HousingID") is not None
                for j in getattr(self, "_jets_data", [])
            )
            ok = all_have_housing
        else:
            ok = False
        if update_icon:
            try:
                self.tabs.setTabIcon(2, _make_icon(ok))
            except Exception:
                pass
        return ok

    def _check_machine(self, update_icon: bool = True) -> bool:
        if self.mode == "addtrials":
            ok = True  # Machine vorbelegt aus Serie, Felder optional
            if update_icon:
                try:
                    self.tabs.setTabIcon(self._tab_index_by_title("Machine") or 3, _make_icon(ok))
                except Exception:
                    pass
            return ok
        ok = self.cmbMachine.currentIndex() >= 0
        if update_icon:
            try:
                self.tabs.setTabIcon(3, _make_icon(ok))
            except Exception:
                pass
        return ok

    def _check_lab(self, update_icon: bool = True) -> bool:
        ok = True  # Lab Machines immer optional
        if update_icon:
            try:
                idx = self._tab_index_by_title("Lab Machines")
                if idx is not None:
                    self.tabs.setTabIcon(idx, _make_icon(ok))
            except Exception:
                pass
        return ok

    # -->-->-->- General -->-->-->-

    def _on_general_changed(self):
        from datetime import datetime
        if self.mode not in ("create", "legacy"):
            return
        self.strExperimentData[1] = "" if self.cmbProductGroup.currentIndex(
        ) < 0 else str(self.cmbProductGroup.currentData())
        self.strExperimentData[2] = "" if self.cmbOrderType.currentIndex(
        ) < 0 else str(self.cmbOrderType.currentData())
        if self.mode == "create":
            self.strExperimentData[0] = str(datetime.now().year)
            self._recompute_experiment_number()
        else:
            # legacy: keep manually provided year/number; just re-check form state
            pass
        self._check_general()
        self._check_safe()

    def _on_series_name_changed(self):
        """
        Series Name beeinflusst nur den General-Tab (nicht mehr Material).
        Diese Funktion sorgt dafür, dass der General-Status neu berechnet wird,
        sobald sich der Serienname ändert – in allen Modi.
        """
        self._check_general()
        self._check_safe()

    def _apply_mode_addlabmachines(self):
        # Start im Tab General
        try:
            for i in range(self.tabs.count()):
                self.tabs.setTabIcon(i, _make_icon(False))
        except Exception:
            pass
        self.tabs.setCurrentIndex(0)

        # General-Tab: exakt gleich wie im Modus "addtrials"
        self._hide_row(self._lbl_pg,  self.cmbProductGroup, True)
        self._hide_row(self._lbl_ot,  self.cmbOrderType, True)
        self._hide_row(self._lbl_exp_request, self.cmbExperimentRequest, True)
        self._hide_row(self._lbl_project, self.cmbProject, True)
        self._hide_row(self._lbl_num, self.txtExperimentNumber, True)
        # In "addlabmachines" sollen Request/SeriesName/Backlog-Infos im General-Tab nicht sichtbar sein
        self._hide_row(self._lbl_series, self.txtSeriesName, True)
        self._hide_row(self._lbl_backlog_status, self.cmbBacklogStatus, True)
        self._hide_row(self._lbl_backlog_prio, self.cmbBacklogPrio, True)
        self._hide_row(self._lbl_exp, self.cmbExistingExperiment, False)
        self._hide_row(self._lbl_ser, self.cmbExistingSeries, False)

        # Trials host zunächst verbergen; erscheint sobald beide Dropdowns gesetzt sind
        try:
            self._lbl_trials.setVisible(False)
            self._trials_host_general.setVisible(False)
        except Exception:
            pass

        # Wie bei addtrials: Maschine im General-Kontext deaktivieren
        self.cmbMachine.setEnabled(False)

        # Tabs: nur General + Lab Machines sichtbar lassen (spezifisch für addlabmachines)
        self._keep_only_tabs({"General", "Lab Machines"})

        # Untertitel beibehalten (addlabmachines-spezifisch)
        self.btn_back_chip.setVisible(False)
        try:
            self.lbl_small_title.setText(
                "Select experiment & series, then choose trials below")
        except Exception:
            pass

        # Readonly-Einstellungen wie zuvor
        try:
            self._set_material_readonly(True)
        except Exception:
            pass
        try:
            self._set_lab_readonly(False)
        except Exception:
            pass

        self._check_general()
        self._check_safe()
        self._update_lab_state_addlabmachines()

    def _resolve_experiments_table_and_columns(self) -> Optional[tuple[str, Dict[str, str]]]:
        return _ec.experiments_table()

    def _recompute_experiment_number(self):
        if self.mode == "legacy":
            # manual Experiment ID in txtExperimentNumber
            return
        if self.mode != "create":
            self.txtExperimentNumber.clear()
            self.strExperimentData[3] = ""
            return
        year = self.strExperimentData[0]
        pg = self.strExperimentData[1]
        ot = self.strExperimentData[2]
        if not (year and pg and ot):
            self.txtExperimentNumber.clear()
            self.strExperimentData[3] = ""
            return
        if not self._resolve_experiments_table_and_columns():
            self.txtExperimentNumber.clear()
            self.strExperimentData[3] = ""
            QMessageBox.warning(self, "Experiment Number",
                                "Experiments table or columns not found.")
            return
        try:
            next_txt = _ec.next_experiment_number(year, pg, ot)
            self.txtExperimentNumber.setText(next_txt)
            self.strExperimentData[3] = next_txt
        except Exception as e:
            self.txtExperimentNumber.clear()
            self.strExperimentData[3] = ""
            show_error(self, "Experiment Number", "The next experiment number could not be read.", e, warning=True)

    def _resolve_next_free_experiment_number(self, cur, exp_table: str, cols: dict,
                                              year: str, pg, ot, preferred_no_txt: str) -> str:
        """Gibt die kleinste freie Experimentnummer >= preferred_no_txt zurück.
        Wird in _on_save verwendet, um Race-Conditions bei gleichzeitigem Anlegen zu vermeiden."""
        return _ec.next_free_number(cur, exp_table, cols, year, pg, ot, preferred_no_txt)

    # -->-->-->- Material -->-->-->-
    def _on_material_changed(self):
        self._check_material()
        self._check_safe()

    def _yarn_name_item(self, yarn_id: Any, name: str) -> QTableWidgetItem:
        """Yarn name cell of tblYarns with the colour square of the yarn."""
        if getattr(self, "_yarn_colours", None) is None:
            self._yarn_colours, _ = load_yarn_colours()
        it = QTableWidgetItem(name)
        try:
            colour = self._yarn_colours.get(int(yarn_id))
        except (TypeError, ValueError):
            colour = None
        it.setIcon(colour_icon(colour))
        if colour:
            it.setToolTip(colour_tooltip(colour))
        return it

    def _on_material_tree_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Klick auf das gruene Spulen-Symbol (Spalte 1): wo liegen die Spulen
        dieses Garns am Lager - derselbe Dialog wie in Show Experiment."""
        if column != 1 or item is None:
            return
        data = item.data(0, Qt.UserRole)
        if not (isinstance(data, dict) and data.get("kind") == "yarn"):
            return
        try:
            yarn_id = int(data.get("yarn_id"))
        except Exception:
            return
        if getattr(self, "_material_stock_summary", {}).get(yarn_id) is None:
            return  # nicht am Lager - nichts zu zeigen (wie Show Experiment)
        # Spulen, die hier schon gewaehlt sind, erscheinen fett
        chosen = {int(m["SpoolID"]) for m in self._materials_data if m.get("SpoolID") is not None}
        win = self.window()
        goto = getattr(win, "_go_yarn_stock_from_notification", None)
        try:
            dlg = _yarn_locations.YarnLocationsDialog(
                yarn_id, str(data.get("yarn_name") or f"Yarn {yarn_id}"),
                getattr(self, "_yarn_colours", {}).get(yarn_id), chosen,
                parent=self, on_open_yarn_stock=goto)
        except Exception as e:
            show_error(self, "Stock locations", "The stock locations could not be loaded.", e)
            return
        try:
            from db.usage_log import log_usage_event
            log_usage_event("feature", "yarn_stock_locations", "create_experiment")
        except Exception:
            pass
        dlg.exec()

    def _get_selected_yarn_from_tree(self) -> Optional[tuple[Any, str]]:
        items = self.treeMaterial.selectedItems() if hasattr(self, "treeMaterial") else []
        if not items:
            return None
        item = items[0]
        data = item.data(0, Qt.UserRole)
        if isinstance(data, dict) and data.get("kind") == "yarn":
            return data.get("yarn_id"), str(data.get("yarn_name") or "")
        return None

    MAX_PLIES = 5

    def _update_add_material_enabled(self):
        y = self._get_selected_yarn_from_tree()
        at_max = self.tblYarns.rowCount() >= self.MAX_PLIES
        self.butAddMaterial.setEnabled(y is not None and not at_max)
        if hasattr(self, "butAddTrialPly"):
            self.butAddTrialPly.setEnabled(not at_max)

    def _on_yarn_delete_row(self, row: int) -> bool:
        """Callback von ReadOnlyTable wenn eine Zeile gelöscht wird.
        Gibt True zurück (Löschen erlaubt) und nummeriert die Ply-Labels danach neu."""
        if self._strict_ro_tbl_yarns:
            return False
        if 0 <= row < len(self._materials_data):
            del self._materials_data[row]
        # Ply-Labels neu vergeben - gleiche Regel wie beim Hinzufügen
        # (db/experiment_create.renumber_plies: gleiches Garn = gleiche Ply;
        # vorher stur "Ply 1..n", womit die Enden eines Garns verschiedene Plies bekamen)
        series_pk = None
        if self.mode in ("addtrials", "addlabmachines"):
            try:
                series_pk = int(self.cmbExistingSeries.currentData())
            except Exception:
                series_pk = None
        for m, label in zip(self._materials_data, _ec.renumber_plies(
                self._materials_data, getattr(self, "_ply_offset", 0), series_pk)):
            m["Ply"] = label
        # UI nach dem Löschen aktualisieren (Tabelle hat Zeile noch nicht entfernt)
        # → Renummerierung wird nach removeRow() sichtbar, daher per QTimer
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._renumber_ply_labels_in_table)
        self._check_material()
        self._check_safe()
        return True

    def _renumber_ply_labels_in_table(self):
        """Schreibt die Ply-Labels aus _materials_data zurück in tblYarns."""
        for i, m in enumerate(self._materials_data):
            item = self.tblYarns.item(i, 1)
            if item:
                item.setText(m["Ply"])
            else:
                self.tblYarns.setItem(i, 1, QTableWidgetItem(m["Ply"]))
        self._update_add_material_enabled()

    def _add_material(self, override_sel: Optional[tuple[Any, str]] = None, skip_spool: bool = False):
        """override_sel: (yarn_id, yarn_name) statt der Tree-Auswahl - genutzt
        von _add_trial_ply(), damit die komplette restliche Logik hier
        (Konflikt-Checks, Ply-Nummerierung, Spool-Picker, MAX_PLIES) für
        Halbfabrikat-Plies unverändert mitgilt, statt sie zu duplizieren.
        skip_spool: Halbfabrikat-"Schatten"-Garne (siehe _add_trial_ply())
        haben keine physische Spule - der Spool-Picker macht fuer sie keinen
        Sinn und wird deshalb uebersprungen."""
        sel = override_sel or self._get_selected_yarn_from_tree()
        if not sel:
            return
        yarn_id, yarn_name = sel
        if self.tblYarns.rowCount() >= self.MAX_PLIES:
            QMessageBox.information(
                self, "Material",
                f"Maximum of {self.MAX_PLIES} yarns per trial series allowed.")
            return
        # Ply label + series/list conflict: db/experiment_create.ply_label_for
        # (Qt-free, shared with the web app) - same yarn = same ply, a ply
        # keeps one yarn in the whole series.
        series_pk: Optional[int] = None
        if self.mode in ("addtrials", "addlabmachines") and hasattr(self, "cmbExistingSeries"):
            try:
                data = self.cmbExistingSeries.currentData()
                if data is not None:
                    series_pk = int(data)
            except Exception:
                series_pk = None
        ply_label, conflict = _ec.ply_label_for(
            self._materials_data, yarn_id, getattr(self, "_ply_offset", 0), series_pk)
        if conflict:
            QMessageBox.critical(self, "Yarn Conflict", conflict)
            return
        r = self.tblYarns.rowCount()
        yarn_use_id = None
        yarn_use_name = "—"
        if hasattr(self, "_cmb_yarn_use_create"):
            yarn_use_id = self._cmb_yarn_use_create.currentData()
            yarn_use_name = self._cmb_yarn_use_create.currentText() if yarn_use_id else "—"
        n_ends = 1
        if hasattr(self, "_spn_ends"):
            n_ends = max(1, int(self._spn_ends.value()))

        # Physische Spule zuordnen (optional) - nur Spulen desselben Garns,
        # die am Lager sind, sind waehlbar. Kein Verbrauch/keine Abbuchung
        # hier, rein informative Verknuepfung fuer Rueckverfolgbarkeit.
        # Halbfabrikat-Schatten-Garne haben keine physische Spule -> skip_spool.
        spool_id = None
        if not skip_spool:
            try:
                dlg = SpoolPickerDialog(yarn_id, yarn_name, current_spool_id=None, parent=self)
                if dlg.exec() == QDialog.Accepted:
                    spool_id = dlg.selected_spool_id()
            except Exception:
                spool_id = None

        spool_display = "—"
        if spool_id is not None:
            try:
                _srows = fetch_all(
                    "SELECT ID, Charge, WeightKg, Location, Status FROM tblYarnSpool WHERE ID = ?",
                    [spool_id])
                if _srows:
                    spool_display = spool_label(_srows[0])
            except Exception:
                spool_display = f"#{spool_id}"

        for end_idx in range(n_ends):
            # Alle Enden desselben Garns (mehrfaedig) teilen sich dieselbe
            # Ply-Nummer - vorher bekam nur die erste Zeile den geprüften/
            # konsistenten ply_label, jedes weitere Ende wurde separat
            # durchnummeriert (Ply 2, Ply 3, ...), obwohl es dasselbe Garn
            # ist. Das kollidierte mit der Serien-weiten "gleiches Garn =
            # gleiche Ply"-Regel, sobald ein anderer Trial dieselbe Nummer
            # schon fuer ein anderes Garn belegt hatte (siehe Yarn-Conflict-
            # Fehler, TrialSeries 385).
            this_ply_label = ply_label
            rr = self.tblYarns.rowCount()
            self.tblYarns.insertRow(rr)
            self.tblYarns.setItem(rr, 0, self._yarn_name_item(yarn_id, yarn_name))
            self.tblYarns.setItem(rr, 1, QTableWidgetItem(this_ply_label))
            self.tblYarns.setItem(rr, 2, QTableWidgetItem(yarn_use_name))
            self.tblYarns.setItem(rr, 3, QTableWidgetItem(spool_display))
            self._materials_data.append(
                {"YarnID": yarn_id, "Name": yarn_name, "Ply": this_ply_label,
                 "YarnUseID": yarn_use_id, "SpoolID": spool_id})

        try:
            self.treeMaterial.clearSelection()
        except Exception:
            pass
        self._update_add_material_enabled()
        self._check_material()
        self._check_safe()

    def _add_trial_ply(self):
        """Handler für butAddTrialPly: Halbfabrikat-Output eines bestehenden
        Trials (ggf. andere Maschine) als Ply verwenden, statt eines
        Katalog-Garns - siehe get_or_create_shadow_yarn()."""
        from ui.widgets.trial_picker import TrialPickerDialog
        dlg = TrialPickerDialog(parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        trial_id = dlg.selected_trial_id()
        if trial_id is None:
            return
        try:
            yarn_id = get_or_create_shadow_yarn(trial_id)
        except Exception as e:
            show_error(self, "Trial Ply", "The yarn entry for this trial could not be created.", e)
            return
        if yarn_id is None:
            QMessageBox.warning(self, "Trial Ply", "Could not find this trial.")
            return
        rows = fetch_all("SELECT Name FROM tblYarn WHERE ID = ?", [yarn_id])
        yarn_name = rows[0]["Name"] if rows else f"Yarn #{yarn_id}"
        self._add_material(override_sel=(yarn_id, yarn_name), skip_spool=True)

    def _get_selected_jet_from_tree(self) -> Optional[tuple[Any, str]]:
        items = self.treeJet.selectedItems() if hasattr(self, "treeJet") else []
        if not items:
            return None
        item = items[0]
        data = item.data(0, Qt.UserRole)
        if isinstance(data, dict) and data.get("kind") == "jet":
            return data.get("jet_id"), str(data.get("jet_name") or "")
        return None

    # -->-->-->- Jet -->-->-->-
    def _on_numplates_changed(self):
        try:
            n = int(self.txtNumPlates.text())
        except Exception:
            n = 0
        for i in range(len(self.plate_edits)):
            show = (i < n)
            self.plate_labels[i].setVisible(show)
            self.plate_edits[i].setVisible(show)
            if show and not self.plate_edits[i].text().strip():
                self.plate_edits[i].setText(str(i + 1))
        self._on_jet_inputs_changed()

    def _on_jet_inputs_changed(self):
        self.butAddJet.setEnabled(self._jet_inputs_valid())

    def _jet_inputs_valid(self) -> bool:
        if not hasattr(self, "cmbHousing") or self.cmbHousing.currentData() is None:
            return False
        sel = self._get_selected_jet_from_tree()
        if not sel:
            return False
        t = self.txtNumPlates.text().strip()
        if not t.isdigit():
            return False
        n = int(t)
        if not (1 <= n <= 20):
            return False
        for i in range(n):
            s = self.plate_edits[i].text().strip()
            if not s.isdigit():
                return False
            v = int(s)
            if not (0 <= v <= 100):
                return False
        p = self.txtPressure.text().strip()
        if p == "":
            return False
        if QRegularExpression(r"^\s*\d+(?:[.,]\d{1,2})?\s*$").match(p).hasMatch() is False:
            return False
        return True

    def _add_jet_row(self):
        if not self._jet_inputs_valid():
            return
        n = int(self.txtNumPlates.text().strip())
        plates = [self.plate_edits[i].text().strip() for i in range(n)]
        plates_csv = ",".join(plates)
        sel = self._get_selected_jet_from_tree()
        if not sel:
            return
        jet_id, jet_name = sel
        p_raw = self.txtPressure.text().strip().replace(",", ".")
        try:
            p_val = float(p_raw)
            p_disp = f"{p_val:.2f}".rstrip("0").rstrip(".")
        except Exception:
            p_disp = self.txtPressure.text().strip()

        housing_id = self.cmbHousing.currentData() if hasattr(self, "cmbHousing") else None
        housing_name = self.cmbHousing.currentText() if hasattr(self, "cmbHousing") else ""

        r = self.tblJets.rowCount()
        self.tblJets.insertRow(r)
        self.tblJets.setItem(r, 0, QTableWidgetItem(housing_name))
        self.tblJets.setItem(r, 1, QTableWidgetItem(jet_name))
        self.tblJets.setItem(r, 2, QTableWidgetItem(str(n)))
        self.tblJets.setItem(r, 3, QTableWidgetItem(p_disp))
        self.tblJets.setItem(r, 4, QTableWidgetItem(plates_csv))

        self._jets_data.append({
            "JetID": jet_id, "JetName": jet_name, "Plates": n, "Pressure": p_disp,
            "PlateList": plates_csv, "HousingID": housing_id, "HousingName": housing_name
        })

        self.txtPressure.clear()
        self._check_jet()
        self._check_safe()

    def _delete_jet_row(self, row: int):
        if 0 <= row < len(self._jets_data):
            del self._jets_data[row]
        self._check_jet()
        self._check_safe()

    # ---> Jets list helpers: Copy, Move, Edit, DnD <---

    def _on_jet_item_changed(self, item):
        """Sync _jets_data wenn Spalten 2 (Plates) oder 3 (Pressure) direkt editiert werden."""
        row = item.row()
        col = item.column()
        if col not in (2, 3) or row < 0 or row >= len(self._jets_data):
            return
        val = item.text().strip()
        if col == 2:
            # Number of Plates: Integer-Validierung
            try:
                n = int(val)
                if n < 1:
                    raise ValueError
            except ValueError:
                # Ungueltige Eingabe: alten Wert wiederherstellen
                self.tblJets.blockSignals(True)
                self.tblJets.item(row, 2).setText(str(self._jets_data[row].get("Plates", "")))
                self.tblJets.blockSignals(False)
                return
            self._jets_data[row]["Plates"] = n
            # PlateList automatisch anpassen (sequenziell 1..n)
            new_plates = ",".join(str(i) for i in range(1, n + 1))
            self._jets_data[row]["PlateList"] = new_plates
            self.tblJets.blockSignals(True)
            self.tblJets.item(row, 4).setText(new_plates)
            self.tblJets.blockSignals(False)
        elif col == 3:
            # Air Pressure: Float-Validierung
            try:
                p_val = float(val.replace(",", "."))
                p_disp = f"{p_val:.2f}".rstrip("0").rstrip(".")
            except ValueError:
                self.tblJets.blockSignals(True)
                self.tblJets.item(row, 3).setText(str(self._jets_data[row].get("Pressure", "")))
                self.tblJets.blockSignals(False)
                return
            self._jets_data[row]["Pressure"] = p_disp
            self.tblJets.blockSignals(True)
            self.tblJets.item(row, 3).setText(p_disp)
            self.tblJets.blockSignals(False)
        self._check_jet()
        self._check_safe()

    def _copy_selected_jet_rows(self):
        """Kopiert markierte Zeilen und fuegt sie ans Ende der Liste an."""
        sel_rows = sorted(set(idx.row() for idx in self.tblJets.selectedIndexes()))
        if not sel_rows:
            return
        self.tblJets.blockSignals(True)
        for src_row in sel_rows:
            if src_row < 0 or src_row >= len(self._jets_data):
                continue
            src_data = dict(self._jets_data[src_row])
            r = self.tblJets.rowCount()
            self.tblJets.insertRow(r)
            for col in range(self.tblJets.columnCount()):
                src_item = self.tblJets.item(src_row, col)
                self.tblJets.setItem(r, col, QTableWidgetItem(src_item.text() if src_item else ""))
            self._jets_data.append(src_data)
        self.tblJets.blockSignals(False)
        self._check_jet()
        self._check_safe()

    def _move_jet_row_up(self):
        """Verschiebt die aktuelle Zeile eine Position nach oben."""
        row = self.tblJets.currentRow()
        if row <= 0 or row >= self.tblJets.rowCount():
            return
        self._move_jet_row(row, row - 1)
        self.tblJets.setCurrentCell(row - 1, self.tblJets.currentColumn())

    def _move_jet_row_down(self):
        """Verschiebt die aktuelle Zeile eine Position nach unten."""
        row = self.tblJets.currentRow()
        if row < 0 or row >= self.tblJets.rowCount() - 1:
            return
        self._move_jet_row(row, row + 1)
        self.tblJets.setCurrentCell(row + 1, self.tblJets.currentColumn())

    def _on_jet_row_dragged(self, src: int, dst: int):
        """Drag&Drop-Gegenstück zu den Up/Down-Buttons (siehe
        ReadOnlyTable.on_row_moved) - dieselbe _move_jet_row()-Logik,
        nur mit beliebiger statt fester Distanz von 1."""
        self._move_jet_row(src, dst)
        self.tblJets.setCurrentCell(dst, self.tblJets.currentColumn())

    def _move_jet_row(self, src: int, dst: int):
        """Verschiebt Zeile `src` an Position `dst` in tblJets UND
        _jets_data synchron (Generalisierung des früheren _swap_jet_rows(),
        das nur benachbarte Zeilen tauschen konnte - gemeinsam genutzt von
        den Up/Down-Buttons [Distanz 1] und der Drag&Drop-Umsortierung
        [beliebige Distanz], 2026-08-28)."""
        n = self.tblJets.rowCount()
        if src == dst or not (0 <= src < n) or not (0 <= dst < n):
            return
        self.tblJets.blockSignals(True)
        ncols = self.tblJets.columnCount()
        # Zeile src zwischenspeichern, dann alle dazwischenliegenden Zeilen
        # um eine Position in Richtung src verschieben (wie beim Verschieben
        # einer Karte in einem Stapel) - danach src-Inhalt bei dst einsetzen.
        texts = [self.tblJets.item(src, c).text() if self.tblJets.item(src, c) else ""
                 for c in range(ncols)]
        data = self._jets_data.pop(src)
        self._jets_data.insert(dst, data)
        step = 1 if dst > src else -1
        for r in range(src, dst, step):
            for c in range(ncols):
                self.tblJets.setItem(r, c, self.tblJets.takeItem(r + step, c))
        for c in range(ncols):
            self.tblJets.setItem(dst, c, QTableWidgetItem(texts[c]))
        self.tblJets.blockSignals(False)

    # ---> Ende Jets list helpers <---

    # -->-->-->- Machine -->-->-->-
    def _clear_machine_grid(self):
        for lab, edit, _, _, _ in self._machine_field_widgets:
            lab.deleteLater()
            edit.deleteLater()
        self._machine_field_widgets.clear()
        while self.machine_grid.count():
            item = self.machine_grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _on_machine_changed(self):
        self._clear_machine_grid()

        idx = self.cmbMachine.currentIndex()
        if idx < 0:
            # Keine Maschine → kein Joker
            self._joker_machine_selected = False
            # Backlog-Status Dropdown wieder freigeben, wenn keine Joker-Maschine ausgewählt ist
            if hasattr(self, "cmbBacklogStatus"):
                try:
                    self.cmbBacklogStatus.setEnabled(True)
                except Exception:
                    pass
            self._check_machine()
            self._check_safe()
            return

        machine_id = self.cmbMachine.currentData()
        self.strExperimentData[4] = str(machine_id)
        self.strExperimentData[5] = self.cmbMachine.currentText() or ""

        # Joker-Flag der gewählten Maschine aus dem ComboBox-Item lesen
        try:
            is_joker = bool(self.cmbMachine.itemData(idx, Qt.UserRole + 1))
        except Exception:
            is_joker = False
        self._joker_machine_selected = is_joker

        # Backlog-Status im General-Tab sperren, wenn eine Joker-Maschine gewählt ist
        if hasattr(self, "cmbBacklogStatus"):
            try:
                self.cmbBacklogStatus.setEnabled(not is_joker)
            except Exception:
                pass

        # Wenn eine Joker-Maschine gewählt ist, den Backlog-Status im General-Tab
        # zwingend auf "Backlog" setzen (ID=1)
        if is_joker and hasattr(self, "cmbBacklogStatus"):
            try:
                bj_idx = self.cmbBacklogStatus.findText("Backlog")
                if bj_idx >= 0:
                    self.cmbBacklogStatus.setCurrentIndex(bj_idx)
            except Exception:
                # Falls irgendetwas schiefgeht, den User nicht blockieren –
                # die DB-Logik erzwingt den Wert zusätzlich noch einmal.
                pass

        # Field layout: db/experiment_create.machine_fields (Qt-free, shared with the web app)
        try:
            fields = _ec.machine_fields(machine_id)
        except RuntimeError as e:
            QMessageBox.warning(self, "Machine", str(e))
            self._check_machine()
            self._check_safe()
            return

        for f in fields:
            row_idx = f["row"]
            col_idx = f["col"] * 2
            if f["gap_before"]:
                spacer = QSpacerItem(0, 16, QSizePolicy.Minimum, QSizePolicy.Fixed)
                self.machine_grid.addItem(spacer, row_idx - 1, 0, 1, 6)
            lab = QLabel(f["caption"])

            # dropdown:tblXxx → QComboBox statt QLineEdit
            if f["kind"] == "dropdown":
                widget = QComboBox()
                widget.setInsertPolicy(QComboBox.NoInsert)
                widget.addItem("", None)   # leerer Eintrag (kein Wert)
                for lid, lname in f.get("options", []):
                    widget.addItem(str(lname or ""), lid)
                self.machine_grid.addWidget(lab, row_idx, col_idx)
                self.machine_grid.addWidget(widget, row_idx, col_idx + 1)
                self._machine_field_widgets.append((lab, widget, f["fno"], f["orig"], f["storage"]))
                continue

            edit = QLineEdit()
            if f["kind"] == "int":
                edit.setValidator(QIntValidator(-10**9, 10**9, self))
            elif f["kind"] == "double":
                regex = QRegularExpression(r"^\s*[+-]?\d+(?:[.,]\d{1,3})?\s*$")
                edit.setValidator(QRegularExpressionValidator(regex, self))
            elif f["kind"] == "sz":
                regex = QRegularExpression(
                    r"^\s*(S|Z|SZ)\s*$", QRegularExpression.CaseInsensitiveOption)
                edit.setValidator(QRegularExpressionValidator(regex, self))

                def _up(_=None, e=edit):
                    e.blockSignals(True)
                    e.setText(e.text().upper())
                    e.blockSignals(False)
                edit.textChanged.connect(_up)

            self.machine_grid.addWidget(lab, row_idx, col_idx)
            self.machine_grid.addWidget(edit, row_idx, col_idx + 1)
            self._machine_field_widgets.append((lab, edit, f["fno"], f["orig"], f["storage"]))

        self._check_machine()
        self._check_safe()

    # -->-->-->- Lab Machines -->-->-->-
    def _on_lab_machine_changed(self):
        # Nur Additional-Textbox löschen/zeigen; Auswahl bleibt erhalten
        self._set_additional_visible(False, clear=True)
        self._set_tension_checkboxes_visible(False, uncheck=True)
        self.txtAdditional.setPlaceholderText("")  # Standard

        idx = self.cmbLabMachine.currentIndex()
        if idx < 0:
            self._update_add_lab_enabled()
            return

        # Meta zur ausgewählten Lab-Maschine
        lm_id = self.cmbLabMachine.currentData()
        meta = self._lab_machines.get(lm_id) or {}
        caption = (meta.get("AddField") or "").strip()
        unit = (meta.get("AddUnit") or "").strip()
        name = str(meta.get("LMName")
                   or self.cmbLabMachine.currentText()).strip()

        # In addtrials: bei Itemat-Maschinen kein manuelles Eingabefeld —
        # es wird immer nur 0.0 eingefügt (Button direkt aktiv)
        if self.mode == "addtrials" and caption and self._is_itemat(meta, name):
            self._set_additional_visible(False, clear=True)
            self.butAddLabMachine.setEnabled(True)
            return

        if caption:
            if self._is_itemat(meta, name):
                # Itemat: Checkboxen + Textfeld für individuelle Werte anzeigen
                self.txtAdditional.setValidator(self._single_value_validator)
                self._set_tension_checkboxes_visible(True, uncheck=True)
                self.lblAddCaption.setText(caption)
                self.lblAddUnit.setText(unit)
                self._set_additional_visible(True, clear=True)
                self.txtAdditional.setPlaceholderText("Andere Tension…")
            elif self._is_series_freeform(meta):
                # SeriesFreeform (z.B. Jet Air Consumption): kommagetrennte
                # Werteliste erlauben statt nur einer einzelnen Zahl.
                self.txtAdditional.setValidator(self._csv_value_validator)
                self.lblAddCaption.setText(caption)
                self.lblAddUnit.setText(unit)
                self._set_additional_visible(True, clear=True)
                self.txtAdditional.setPlaceholderText("z.B. 4, 5, 6")
            else:
                # Andere Maschinen: normales Textfeld
                self.txtAdditional.setValidator(self._single_value_validator)
                self.lblAddCaption.setText(caption)
                self.lblAddUnit.setText(unit)
                self._set_additional_visible(True, clear=True)

        self._update_add_lab_enabled()

    def _set_additional_visible(self, vis: bool, clear: bool = False):
        if clear:
            self.txtAdditional.clear()
        self.lblAddCaption.setVisible(vis)
        self.txtAdditional.setVisible(vis)
        self.lblAddUnit.setVisible(vis)

    def _set_tension_checkboxes_visible(self, vis: bool, uncheck: bool = False):
        """Zeigt/versteckt die Itemat-Tension-Checkboxen und deaktiviert sie optional."""
        self.lblTensionCaption.setVisible(vis)
        for cb in getattr(self, "_tension_checkboxes", []):
            if uncheck:
                cb.blockSignals(True)
                cb.setChecked(False)
                cb.blockSignals(False)
            cb.setVisible(vis)

    def _get_checked_tensions(self) -> List[float]:
        """Gibt die ausgewählten Tension-Werte als float-Liste zurück."""
        result = []
        for cb in getattr(self, "_tension_checkboxes", []):
            if not cb.isHidden() and cb.isChecked():
                try:
                    result.append(float(cb.text().split()[0].replace(",", ".")))
                except Exception:
                    pass
        return result

    def _update_add_lab_enabled(self):
        ok = self.cmbLabMachine.currentIndex() >= 0
        tension_visible = any(cb.isVisible() for cb in getattr(self, "_tension_checkboxes", []))
        if tension_visible:
            # Itemat-Modus: Checkbox-Auswahl ODER ein gültiger Wert im Textfeld reicht
            checkbox_ok = any(cb.isChecked() for cb in self._tension_checkboxes)
            txt = self.txtAdditional.text().strip() if self.txtAdditional.isVisible() else ""
            textfield_ok = bool(txt) and self.txtAdditional.hasAcceptableInput()
            ok = ok and (checkbox_ok or textfield_ok)
        elif self.txtAdditional.isVisible():
            txt = self.txtAdditional.text().strip()
            ok = ok and bool(txt) and self.txtAdditional.hasAcceptableInput()
        self.butAddLabMachine.setEnabled(ok)

    def _is_itemat(self, meta: dict, fallback_name: str = "") -> bool:
        """Erkenne Itemat-Maschinen robust: db/trial_actions.is_itemat."""
        return _trial_actions.is_itemat(meta, fallback_name)

    def _is_series_freeform(self, meta: dict) -> bool:
        """RowMode='SeriesFreeform' (z.B. Jet Air Consumption): db/experiment_create.is_series_freeform."""
        return _ec.is_series_freeform(meta)

    def _add_lab_machine(self):
        # Button-Guard
        if not self.butAddLabMachine.isEnabled():
            return
        lm_id = int(self.cmbLabMachine.currentData())
        meta = self._lab_machines.get(lm_id) or {}
        # Which entries the "+" adds: db/experiment_create.plan_lab_entries
        # (Qt-free, shared with the web app)
        text = self.txtAdditional.text() if not self.txtAdditional.isHidden() else ""
        trial_ids = self._get_checked_trial_ids() if self.mode == "addlabmachines" else []
        entries, msg = _ec.plan_lab_entries(meta, self.mode, self._lab_data, text,
                                            self._get_checked_tensions(), trial_ids)
        if msg:
            QMessageBox.information(self, "Lab Machine", msg)
            return
        for e in entries:
            rr = self.tblLabMachines.rowCount()
            self.tblLabMachines.insertRow(rr)
            self.tblLabMachines.setItem(rr, 0, QTableWidgetItem(e["Name"]))
            self.tblLabMachines.setItem(rr, 1, QTableWidgetItem(e["AdditionalDisp"]))
            self._lab_data.append(e)
        # Eingabefelder zurücksetzen
        if any(not cb.isHidden() for cb in getattr(self, "_tension_checkboxes", [])):
            self._set_tension_checkboxes_visible(True, uncheck=True)
        if (meta.get("AddField") or "").strip():
            if entries:
                self.txtAdditional.clear()
        else:
            self._set_additional_visible(False, clear=True)
        self._update_add_lab_enabled()
        self._check_lab()
        self._check_safe()
        self._update_lab_state_addlabmachines()

    def _delete_lab_row(self, row: int):
        """Delete a lab-machine row. The Itemat 0.0 cN/dtex baseline may only
        go when no other variant of that machine is in the list
        (db/experiment_create.can_delete_lab_entry)."""
        if not (0 <= row < len(self._lab_data)):
            # inkonsistenter Zustand -> nichts tun, aber Deletion nicht blockieren
            return True
        if not _ec.can_delete_lab_entry(self._lab_data, row, self._lab_machines):
            QMessageBox.information(
                self,
                "0.0 variant cannot be deleted",
                (
                    "The 0.0 cN/dtex variant of Itemat machines can only be deleted "
                    "when all other variants of this machine for this "
                    "Serie entfernt wurden.\n\n"
                    "Please delete the other variants first "
                    "(z. B. 0.3, 0.6 usw.)."
                ),
            )
            # False signalisiert dem ReadOnlyTable, dass die Zeile NICHT entfernt werden soll
            return False
        del self._lab_data[row]
        self._check_lab()
        self._check_safe()
        self._update_lab_state_addlabmachines()
        return True

    # -->-->-->- Save / Navigation -->-->-->-
    def _clone_lab_rows(self, cur, src_tid: int, new_tid: int) -> None:
        """Klont die Labor-Datensätze von src_tid auf new_tid.

        - Struktur/Parameter (z.B. Tension, FKs wie UserID) werden übernommen
        - eigentliche Messwerte werden auf NULL gesetzt

        Tabellenliste und Nulling-Strategie sind bewusst identisch zu
        _clone_lab_rows_for_trial() in screen_show_experiment.py (Feature
        "Trial kopieren"), damit beide Wege konsistent funktionieren. Die
        vorherige Variante prüfte Messwert-Spalten anhand einer Keyword-Liste
        (u.a. "stability", "kg", "knoten") - das passt aber auf keinen der
        ~150 DTYoMat/ATYoMat-Feldnamen (FPm, AvgKL, Stab_03, kl_bin_1, ...),
        weshalb dort Altwerte unveraendert uebernommen wurden. Ausserdem
        enthielt die alte Tabellenliste falsche/veraltete Namen
        ("tbllaborstatimat" statt der zwei echten Tabellen statimatds/m,
        "tblaborrapid600" mit Tippfehler, "tbllaboritemat" statt itematlab/
        itematplus, sowie ein nirgends existierendes "tbllaboratemomat"),
        weshalb für Statimat DS und Itemat Lab gar keine Zeile angelegt
        wurde.
        """
        lab_tables = [
            "tbllabortiter",
            "tbllaborstatimatm",
            "tbllaborstatimatds",
            "tbllaborwaterbath",
            "tbllaboritematlab",
            "tbllaboritematplus",
            "tbllaborrapid600",
            "tbllabordtyomat",
            "tbllaboratyomat",
            "tbllaborekb",
            "tbllaborheissluftschrumpf",
            "tbllaborkochschrumpf",
            "tbllaboratyshrinkage",
        ]

        for tbl in lab_tables:
            try:
                if not _db_table_exists(tbl):
                    continue
                cur.execute(f"SELECT * FROM [{tbl}] WHERE [TrialID] = ?", (src_tid,))
                rows = cur.fetchall()
                if not rows:
                    continue
                col_names = [c[0] for c in cur.description]

                skip = {"id", "trialid"}
                gid_col = None
                for c in col_names:
                    if c.lower() == "globalid":
                        gid_col = c
                        skip.add("globalid")
                        break
                insert_cols = [c for c in col_names if c.lower() not in skip]

                for row in rows:
                    row_map = dict(zip(col_names, row))
                    values = []
                    for c in insert_cols:
                        cl = c.lower()
                        v = row_map.get(c)
                        if cl.endswith("id"):
                            # FKs (z.B. UserID, InstrumentID) uebernehmen -
                            # manche Labor-Tabellen haben NOT NULL FKs.
                            values.append(v)
                        elif "tension" in cl:
                            # Einstellung/Parameter, keine Messgroesse -> uebernehmen
                            values.append(v)
                        else:
                            # Messwert -> nullen
                            values.append(None)

                    cols_for_insert = ["TrialID"] + insert_cols
                    vals_for_insert = [new_tid] + values
                    if gid_col:
                        cols_for_insert.append(gid_col)
                        vals_for_insert.append(new_global_id())

                    cs = ", ".join(f"[{c}]" for c in cols_for_insert)
                    ph = ", ".join("?" for _ in cols_for_insert)
                    cur.execute(f"INSERT INTO [{tbl}] ({cs}) VALUES ({ph})", vals_for_insert)
            except Exception:
                pass

    def _to_int_or_none(self, s: Any) -> Optional[int]:
        if s is None:
            return None
        st = str(s).strip()
        if st == "":
            return None
        try:
            return int(st)
        except Exception:
            return None

    def _to_float_or_none(self, s: Any) -> Optional[float]:
        if s is None:
            return None
        st = str(s).strip().replace(",", ".")
        if st == "":
            return None
        try:
            return float(st)
        except Exception:
            return None

    def _open_help(self):
        from ui.widgets.multilang_help import show_help
        from ui.widgets.help_texts_create_experiment import TEXTS
        show_help(TEXTS, self)

    def _on_save(self):
        # Ensure the non-modal Experiment Request popup doesn't outlive this screen.
        self._close_experiment_request_popup()

        if self.mode == "addlabmachines":
            self._save_addlabmachines()
            return
        if self.mode == "addtrials":
            self._save_addtrials()
            return
        if not self.butSave.isEnabled():
            QMessageBox.information(
                self, "Create/Attach", "Please fill in all tabs correctly.")
            return

        # Machine tab -> (tblTrial values, tblTrialSettings values); combo = id, line edit = text
        fields = []
        for lab, widget, fno, orig, storage in self._machine_field_widgets:
            val = widget.currentData() if isinstance(widget, QComboBox) else widget.text()
            fields.append((orig or lab.text().strip(), val, storage))
        trial_vals, settings_vals = _trial_actions.machine_values(fields)

        if self.mode == "legacy" and not _ec.parse_legacy_id(self.txtExperimentNumber.text()):
            QMessageBox.warning(self, "Experiment Number",
                                "Invalid experiment ID. Expected: YYYY-<PGOT>-NNN (e.g. 2019-73-002)")
            return
        experiment_id = None
        if self.mode == "addseries":
            if self.cmbExistingExperiment.currentIndex() < 0:
                QMessageBox.information(self, "Save", "No existing experiment selected.")
                return
            experiment_id = int(self.cmbExistingExperiment.currentData()[0])
        selected_request_id = None
        try:
            if self.mode == "create" and self.cmbExperimentRequest.currentIndex() >= 0:
                selected_request_id = self._to_int_or_none(self.cmbExperimentRequest.currentData())
        except Exception:
            selected_request_id = None
        try:
            user_id = app_meta.current_user.get("id")
        except Exception:
            user_id = None
        try:
            prio = self._to_int_or_none(self.cmbBacklogPrio.currentText().strip())
        except Exception:
            prio = None

        # Writing (experiment, series, trials, lab rows in one transaction):
        # db/experiment_create.create (Qt-free, shared with the web app)
        try:
            res = _ec.create(
                self.mode,
                series_name=self.txtSeriesName.text().strip(),
                machine_id=self._to_int_or_none(self.cmbMachine.currentData()) or 0,
                jets=self._jets_data, materials=self._materials_data, lab_data=self._lab_data,
                trial_values=trial_vals, settings_values=settings_vals,
                product_group=self.cmbProductGroup.currentData(),
                order_type=self.cmbOrderType.currentData(),
                request_id=selected_request_id,
                project_id=self.cmbProject.currentData() if hasattr(self, "cmbProject") else None,
                experiment_id=experiment_id,
                backlog_status=self.cmbBacklogStatus.currentData(),
                backlog_prio=prio,
                user_id=user_id,
                year=(self.strExperimentData[0] or None) if self.mode == "create" else None,
                legacy_id=self.txtExperimentNumber.text().strip() if self.mode == "legacy" else None,
            )
        except Exception as e:
            show_error(self, "Save failed", "The experiment could not be saved.", e)
            return

        if callable(self.on_open_experiment):
            self.on_open_experiment(res["experiment_id"], res["series_id"], res["label"])
        else:
            QMessageBox.information(
                self, "Saved",
                f"{'Trial series added' if self.mode == 'addseries' else 'Experiment saved'}.\n"
                f"Experiment ID: {res['experiment_id']} • Series: {res['series_id']}"
            )

    # -->-->-->- addSeries/addTrials Helper -->-->-->-
    def _prefill_lab_from_series(self, series_id: int) -> None:
        """Befüllt tblLabMachines mit den Lab Machines der bestehenden Trials der Serie
        (Daten: db/trial_actions.series_lab_data, Qt-free, shared with the web app).
        """
        if not self._lab_machines:
            return

        lab_data = _trial_actions.series_lab_data(series_id, self._lab_machines)
        if lab_data is None:
            return

        # _lab_data + tblLabMachines leeren (Prefill von Grund auf)
        self._lab_data.clear()
        while self.tblLabMachines.rowCount():
            self.tblLabMachines.removeRow(0)

        for entry in lab_data:
            r = self.tblLabMachines.rowCount()
            self.tblLabMachines.insertRow(r)
            self.tblLabMachines.setItem(r, 0, QTableWidgetItem(entry["Name"]))
            self.tblLabMachines.setItem(r, 1, QTableWidgetItem(entry["AdditionalDisp"]))
            self._lab_data.append(entry)

        self._check_lab()
        self._check_safe()

    def _on_existing_experiment_changed(self):
        if self.cmbExistingExperiment.currentIndex() < 0:
            self._clear_machine_grid()
            self.cmbMachine.setCurrentIndex(-1)
            self.cmbExistingSeries.clear()
            self.cmbExistingSeries.setCurrentIndex(-1)
            # Hide trials list in addlabmachines
            try:
                if self.mode == "addlabmachines":
                    self._lbl_trials.setVisible(False)
                    try:
                        self._trials_host_general.setVisible(False)
                        # remove any previous checkboxes
                        if hasattr(self, "_trials_grid_general"):
                            while self._trials_grid_general.count():
                                item = self._trials_grid_general.takeAt(0)
                                w = item.widget()
                                if w:
                                    w.deleteLater()
                    except Exception:
                        pass
                    except Exception:
                        pass
            except Exception:
                pass
            self._check_general()
            self._check_machine()
            self._check_safe()
            return

        eid, mid, year, pg, ot, num = self.cmbExistingExperiment.currentData() or (
            None, None, None, None, None, None)
        self.strTrialSeriesData[0] = str(eid) if eid is not None else ""
        self.strExperimentData[0] = str(year) if year is not None else ""
        self.strExperimentData[1] = str(pg) if pg is not None else ""
        self.strExperimentData[2] = str(ot) if ot is not None else ""
        self.strExperimentData[3] = str(num) if num is not None else ""
        self.strExperimentData[4] = str(mid) if mid is not None else ""

        self._set_machine_by_id(mid)

        if self.mode in ("addtrials", "addlabmachines") and eid is not None:
            self._load_series_for_experiment(int(eid))

        # NEW: if in addlabmachines and both dropdowns selected, show list and load trials
        if self.mode == "addlabmachines":
            has_exp = self.cmbExistingExperiment.currentIndex() >= 0
            has_ser = self.cmbExistingSeries.currentIndex() >= 0
            try:
                self._lbl_trials.setVisible(has_exp and has_ser)
                self._trials_host_general.setVisible(has_exp and has_ser)
                if has_exp and has_ser:
                    data = self.cmbExistingExperiment.currentData()
                    exp_id = int(data[0]) if data else None
                    sid = int(self.cmbExistingSeries.currentData())
                    self._load_trials_for_selection(exp_id, sid)
            except Exception:
                pass

        self._check_general()
        self._check_machine()
        self._check_safe()

    def _on_existing_series_changed(self):
        if self.mode == "addtrials":
            if self.cmbExistingSeries.currentIndex() >= 0:
                sid = int(self.cmbExistingSeries.currentData())
                try:
                    self._populate_jets_for_series(sid)
                except Exception:
                    pass
                try:
                    table = "tblTrialSeries"
                    if table_exists(table):
                        cmap = get_columns_map(table)
                        col_id = resolve_field(["ID"], cmap) or "ID"
                        col_mid = resolve_field(
                            ["MachineID", "MaschineID"], cmap) or "MachineID"
                        rows = fetch_all(
                            f"SELECT [{col_mid}] AS MID FROM {table} WHERE [{col_id}] = ?", [sid])
                        if rows:
                            mid = rows[0].get("MID")
                            try:
                                mid = int(mid)
                            except Exception:
                                pass
                            self._set_machine_by_id(mid)
                except Exception:
                    pass
                try:
                    self._prefill_lab_from_series(sid)
                except Exception:
                    pass

        if self.mode == "addlabmachines" and getattr(self, "_mode_applied", False):
            # Nur anzeigen, wenn beide Dropdowns gesetzt sind
            has_exp = self.cmbExistingExperiment.currentIndex() >= 0
            has_ser = self.cmbExistingSeries.currentIndex() >= 0
            try:
                self._lbl_trials.setVisible(has_exp and has_ser)
                self._trials_host_general.setVisible(has_exp and has_ser)
            except Exception:
                pass
            if has_exp and has_ser:
                data = self.cmbExistingExperiment.currentData()
                exp_id = int(data[0]) if data else None
                sid = int(self.cmbExistingSeries.currentData())
                self._load_trials_for_selection(exp_id, sid)
            else:
                try:
                    self._trials_host_general.clear()
                except Exception:
                    pass
        self._check_general()
        self._check_safe()
        self._update_lab_state_addlabmachines()

    def _set_machine_by_id(self, machine_id: Optional[int]):
        if machine_id is None:
            self.cmbMachine.setCurrentIndex(-1)
            self._clear_machine_grid()
            return
        target = -1
        for i in range(self.cmbMachine.count()):
            if self.cmbMachine.itemData(i) == machine_id:
                target = i
                break
        if target >= 0:
            self.cmbMachine.blockSignals(True)
            self.cmbMachine.setCurrentIndex(target)
            self.cmbMachine.blockSignals(False)
            self._on_machine_changed()
        else:
            self.cmbMachine.setCurrentIndex(-1)
            self._clear_machine_grid()

    def _back_home_clicked(self):
        self._close_experiment_request_popup()
        if callable(self.on_back_home):
            self.on_back_home()

    def _back_experiment_clicked(self):
        """Zurück zum Show-Experiment (nur im addtrials-Modus)."""
        self._close_experiment_request_popup()
        if callable(self.on_back_experiment):
            self.on_back_experiment()
        elif callable(self.on_back_home):
            self.on_back_home()

    def open_addtrials_prefill(self, experiment_id: int, trialseries_id: int):
        """Wechselt in addtrials-Modus und wählt Experiment + Serie vor (locked)."""
        self.mode = "addtrials"
        try:
            self._apply_mode_addtrials()
        except Exception:
            pass

        # Kurz enablen damit setCurrentIndex + Signals durchgehen
        self.cmbExistingExperiment.setEnabled(True)
        self.cmbExistingSeries.setEnabled(True)

        # Experiment vorwählen
        for i in range(self.cmbExistingExperiment.count()):
            data = self.cmbExistingExperiment.itemData(i)
            try:
                eid = int(data[0]) if data else None
            except Exception:
                eid = None
            if eid == experiment_id:
                self.cmbExistingExperiment.setCurrentIndex(i)
                break

        # Serie vorwählen — löst _on_existing_series_changed aus (Jets + Machine)
        for i in range(self.cmbExistingSeries.count()):
            if self.cmbExistingSeries.itemData(i) == trialseries_id:
                self.cmbExistingSeries.setCurrentIndex(i)
                break

        # Jetzt wieder sperren
        self.cmbExistingExperiment.setEnabled(False)
        self.cmbExistingSeries.setEnabled(False)

        # Höchste existierende Ply-Nummer der Serie ermitteln → Offset für neue Plies
        self._ply_offset = _trial_actions.series_ply_offset(trialseries_id)

    def closeEvent(self, event):
        """Qt close hook: make sure auxiliary popups are closed."""
        try:
            self._close_experiment_request_popup()
        finally:
            super().closeEvent(event)

    # -->-->-->- Readonly/Populate Helpers -->-->-->-
    def _set_material_readonly(self, ro: bool):
        self.txtSeriesName.setReadOnly(ro)
        self.treeMaterial.setEnabled(not ro)
        self.searchMaterial.setEnabled(not ro)
        self.butAddMaterial.setVisible(not ro)
        self.butAddTrialPly.setVisible(not ro)
        self._strict_ro_tbl_yarns = ro
        if ro:
            self.tblYarns.keyPressEvent = lambda e: None  # block Delete/Backspace

    def _set_lab_readonly(self, ro: bool):
        # AddTrials: ro=False -> alles sichtbar & editierbar
        self.cmbLabMachine.setEnabled(not ro)
        self.cmbLabMachine.setVisible(True if not ro else False)
        self.butAddLabMachine.setEnabled(not ro)
        self.butAddLabMachine.setVisible(True if not ro else False)
        self.txtAdditional.setReadOnly(ro)
        self._strict_ro_tbl_labs = ro
        if ro:
            self.tblLabMachines.keyPressEvent = lambda e: None  # block Delete/Backspace

    def _populate_material_for_series(self, series_id: int):
        while self.tblYarns.rowCount():
            self.tblYarns.removeRow(0)
        self._materials_data.clear()

        # Yarn-Daten direkt aus tbltrialsettings (DISTINCT pro Ply, erster Trial der Series)
        ytable = "tblYarn"
        ymap = {}
        if table_exists(ytable):
            yc = get_columns_map(ytable)
            y_id = resolve_field(["ID"], yc) or "ID"
            y_name = resolve_field(
                ["Name", "Bezeichnung", "YarnName", "Material"], yc) or "Name"
            for r in fetch_all(f"SELECT [{y_id}] AS ID, [{y_name}] AS N FROM [{ytable}]"):
                ymap[int(r["ID"])] = str(r["N"])

        # YarnUse-Map laden
        yarn_use_map: Dict[int, str] = {}
        try:
            for r in fetch_all("SELECT ID, Name FROM tblYarnUse ORDER BY ID"):
                yarn_use_map[int(r["ID"])] = str(r.get("Name") or "")
        except Exception:
            pass

        rows = fetch_all(
            "SELECT DISTINCT ts.Ply, ts.YarnID, ts.YarnUseID, ts.SpoolID "
            "FROM tbltrialsettings ts "
            "JOIN tbltrial t ON t.ID = ts.TrialID "
            "WHERE t.TrialSeriesID = ? AND ts.YarnID IS NOT NULL "
            "ORDER BY ts.Ply",
            [series_id])
        spool_cache: Dict[int, str] = {}
        for r in rows:
            yarn_id = int(r["YarnID"])
            ply = str(r["Ply"] or "")
            name = ymap.get(yarn_id, f"Yarn {yarn_id}")
            yuse_id = int(r["YarnUseID"]) if r.get("YarnUseID") else None
            yuse_name = yarn_use_map.get(yuse_id, "—") if yuse_id else "—"
            spool_id = int(r["SpoolID"]) if r.get("SpoolID") else None
            if spool_id is None:
                spool_display = "—"
            elif spool_id in spool_cache:
                spool_display = spool_cache[spool_id]
            else:
                try:
                    _srows = fetch_all(
                        "SELECT ID, Charge, WeightKg, Location, Status FROM tblYarnSpool WHERE ID = ?",
                        [spool_id])
                    spool_display = spool_label(_srows[0]) if _srows else f"#{spool_id}"
                except Exception:
                    spool_display = f"#{spool_id}"
                spool_cache[spool_id] = spool_display
            rr = self.tblYarns.rowCount()
            self.tblYarns.insertRow(rr)
            self.tblYarns.setItem(rr, 0, self._yarn_name_item(yarn_id, name))
            self.tblYarns.setItem(rr, 1, QTableWidgetItem(str(ply)))
            self.tblYarns.setItem(rr, 2, QTableWidgetItem(yuse_name))
            self.tblYarns.setItem(rr, 3, QTableWidgetItem(spool_display))
            self._materials_data.append(
                {"YarnID": yarn_id, "Name": name, "Ply": ply, "YarnUseID": yuse_id, "SpoolID": spool_id})

        self._set_material_readonly(True)

    def _populate_jets_for_series(self, series_id: int):
        """Füllt tblJets read-only mit den Jets der gewählten TrialSeries (addtrials-Modus)."""
        while self.tblJets.rowCount():
            self.tblJets.removeRow(0)
        self._jets_data.clear()

        # Jets aus tbltrialsettings holen (DISTINCT JetID + Position, aggregiert)
        rows = fetch_all(
            "SELECT DISTINCT ts.JetID, ts.Position, ts.AirPressure "
            "FROM tbltrialsettings ts "
            "JOIN tbltrial t ON t.ID = ts.TrialID "
            "WHERE t.TrialSeriesID = ? AND ts.JetID IS NOT NULL "
            "ORDER BY ts.Position, ts.JetID",
            [series_id])

        if not rows:
            return

        # Jet-Namen aus tbljet laden
        jet_name_map: Dict[int, str] = {}
        housing_map: Dict[int, str] = {}
        try:
            jtable = "tbljet"
            if table_exists(jtable):
                jcmap = get_columns_map(jtable)
                j_id = resolve_field(["ID"], jcmap) or "ID"
                j_name = resolve_field(["Name", "Bezeichnung", "Jet"], jcmap) or "Name"
                j_housing = resolve_field(["HousingID", "Housing"], jcmap)
                sel = [f"[{j_id}] AS ID", f"[{j_name}] AS JName"]
                if j_housing:
                    sel.append(f"[{j_housing}] AS HID")
                for jr in fetch_all(f"SELECT {', '.join(sel)} FROM [{jtable}]"):
                    jid = int(jr["ID"])
                    jet_name_map[jid] = str(jr.get("JName") or f"Jet {jid}")
                    if j_housing:
                        housing_map[jid] = str(jr.get("HID") or "")
        except Exception:
            pass

        for r in rows:
            jet_id = int(r["JetID"])
            position = str(r.get("Position") or "")
            pressure = str(r.get("AirPressure") or "")
            jet_name = jet_name_map.get(jet_id, f"Jet {jet_id}")
            housing = housing_map.get(jet_id, "")
            rr = self.tblJets.rowCount()
            self.tblJets.insertRow(rr)
            self.tblJets.setItem(rr, 0, QTableWidgetItem(jet_name))
            self.tblJets.setItem(rr, 1, QTableWidgetItem(housing))
            self.tblJets.setItem(rr, 2, QTableWidgetItem(position))
            self.tblJets.setItem(rr, 3, QTableWidgetItem(pressure))
            self.tblJets.setItem(rr, 4, QTableWidgetItem(""))
            self._jets_data.append({
                "JetID": jet_id, "Name": jet_name,
                "Position": position, "AirPressure": pressure,
                "HousingID": None,
            })

    def _get_physical_jets_for_series(self, series_id: int) -> List[Dict[str, Any]]:
        """Distinkte 'physische Duesen' (JetID + JetPlate) einer Series:
        db/trial_actions.physical_jets_for_series."""
        return _trial_actions.physical_jets_for_series(series_id)

    def _save_jet_air_consumption_rows(self, cur, series_id: int) -> Dict[str, int]:
        """Jet Air Consumption rows (physische Duese x Druckstufe) der
        SeriesFreeform-Lab-Machines in _lab_data, einmal pro Series:
        db/trial_actions.save_jet_air_consumption_rows."""
        return _trial_actions.save_jet_air_consumption_rows(cur, series_id, self._lab_data)

    def _get_checked_trial_ids(self) -> list[int]:
        """Collect TrialIDs from checkboxes (General tab)."""
        tids: list[int] = []
        try:
            for tid, cb, _ in getattr(self, "_trial_checks", []):
                if cb.isChecked():
                    try:
                        tids.append(int(tid))
                    except Exception:
                        pass
        except Exception:
            pass
        return tids

    # -->-->-->- Public API: Open AddSeries Prefilled -->-->-->-

    def open_addseries_prefill(self, experiment_id: int, trialseries_id: int):
        """Switch to addseries mode, preselect the given experiment, and preload Jet rows
        from the given TrialSeries (aggregated by JetID+Pressure)."""
        # Switch mode and UI
        self.mode = "addseries"
        try:
            self._apply_mode_addseries()
        except Exception:
            pass
        # Clear current Jet table/data
        try:
            self.tblJets.setRowCount(0)
        except Exception:
            pass
        self._jets_data = []
        # Preselect experiment
        self.existing_experiment_id = int(experiment_id)
        try:
            self._load_existing_experiments()
        except Exception:
            pass
        # Prefill jets from selected trial series
        try:
            self._prefill_jets_from_trialseries(int(trialseries_id))
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            show_error(self, "Prefill Jets", "The jets could not be loaded.", e, warning=True)
        # Focus tabs & recompute icons
        try:
            self.tabs.setCurrentIndex(2)  # Jet tab
        except Exception:
            pass
        try:
            self._check_jet()
            self._check_safe()
        except Exception:
            pass

    def _prefill_jets_from_trialseries(self, series_id: int):
        """Jet rows of the given series into the Jet tab (JetID, Jet Plate,
        Air Pressure, HousingID aggregated per jet + pressure). Data:
        db/series_actions.series_jet_groups (Qt-free, shared with the web app)."""
        from db.series_actions import series_jet_groups
        # Build HousingID -> HousingName mapping from already-loaded cmbHousing
        housing_name_by_id: dict = {}
        try:
            if hasattr(self, "cmbHousing"):
                for i in range(self.cmbHousing.count()):
                    hid = self.cmbHousing.itemData(i)
                    hname = self.cmbHousing.itemText(i)
                    if hid is not None:
                        try:
                            housing_name_by_id[int(hid)] = str(hname)
                        except Exception:
                            housing_name_by_id[hid] = str(hname)
        except Exception:
            pass

        for row in series_jet_groups(series_id, housing_name_by_id):
            # Add to UI table
            rix = self.tblJets.rowCount()
            self.tblJets.insertRow(rix)
            self.tblJets.setItem(rix, 0, QTableWidgetItem(row["HousingName"]))
            self.tblJets.setItem(rix, 1, QTableWidgetItem(row["JetName"]))
            self.tblJets.setItem(
                rix, 2, QTableWidgetItem(str(row["Plates"])))
            self.tblJets.setItem(rix, 3, QTableWidgetItem(row["Pressure"]))
            self.tblJets.setItem(rix, 4, QTableWidgetItem(row["PlateList"]))
            # Track internal structure
            self._jets_data.append(row)