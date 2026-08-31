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
from ui.pathutil import resource_path
from ui.text_normalize import norm as _norm, resolve_field

import app_meta
import re


def insert_waterbath_rows(cur, tbl, col_trial, trial_id):
    """Fügt Waterbath-Zeilen für einen neuen Trial in die DB ein."""
    """Fügt drei Waterbath-Datensätze für einen Trial hinzu.

    Falls die Tabelle eine Spalte 'GlobalID' besitzt, wird für jede neue Zeile
    eine frische GUID vergeben.
    Erwartet vorhandene Tabelle und Spaltennamen; führt keine Existenzprüfung aus.
    """
    # MySQL: Information-Schema
    cols_map = _db_get_columns_map(tbl.lower())
    global_col = cols_map.get("globalid")
    has_global = bool(global_col)

    for _ in range(3):
        if has_global and global_col:
            cur.execute(
                f"INSERT INTO {tbl} ([{col_trial}],[{global_col}]) VALUES (?,?)",
                [trial_id, new_global_id()],
            )
        else:
            cur.execute(
                f"INSERT INTO {tbl} ([{col_trial}]) VALUES (?)",
                [trial_id],
            )
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


def get_or_create_shadow_yarn(trial_id: int) -> Optional[int]:
    """Multimaschinen-Halbfabrikat-Verknüpfung: liefert die YarnID einer
    "Schatten"-tblYarn-Zeile für den Output eines bestimmten Trials, damit er
    als Ply-Input für einen Trial auf einer anderen Maschine referenziert
    werden kann - ohne den bestehenden Ply-Mechanismus (tbltrialsettings.
    YarnID -> tblYarn) anzufassen und ohne für JEDEN tbltrial einen
    Katalog-Eintrag anzulegen (nur lazy, beim tatsächlichen Auswählen).

    Dedup: eine zweite Anfrage für denselben trial_id gibt dieselbe YarnID
    zurück (SourceTrialID ist der eindeutige Schlüssel), statt einen neuen
    Eintrag anzulegen. Material/Titer/Filamentzahl werden vom Eingangsgarn
    des Quell-Trials übernommen, der gemessene Titer des Quell-Trials
    (tbllabortiter, falls vorhanden) überschreibt den kopierten Wert - beides
    nur für Anzeige/Reports relevant, die Ply-Speicherlogik selbst braucht
    nur eine gültige YarnID.
    """
    existing = fetch_all("SELECT ID FROM tblYarn WHERE SourceTrialID = ?", [trial_id])
    if existing:
        return int(existing[0]["ID"])

    trial_rows = fetch_all(
        "SELECT t.Versuchsnummer, ts.SeriesName "
        "FROM tbltrial t JOIN tbltrialseries ts ON ts.ID = t.TrialSeriesID "
        "WHERE t.ID = ?",
        [trial_id],
    )
    if not trial_rows:
        return None
    vno = trial_rows[0].get("Versuchsnummer")
    series_name = trial_rows[0].get("SeriesName") or ""
    name = f"Semi-finished V{vno} ({series_name})".strip()
    # tblYarn.Name ist varchar(45) - lange SeriesNames muessen gekuerzt
    # werden, sonst bricht der INSERT ("Data too long for column 'Name'").
    _NAME_MAXLEN = 45
    if len(name) > _NAME_MAXLEN:
        prefix = f"Semi-finished V{vno} ("
        suffix = ")"
        budget = _NAME_MAXLEN - len(prefix) - len(suffix) - 1  # -1 fuer "…"
        name = f"{prefix}{series_name[:max(budget, 0)]}…{suffix}"

    # Eingangsgarn des Quell-Trials (erste/Haupt-Ply) als Vorlage für
    # Material/Garntyp/Filamentzahl/dpf.
    input_yarn_rows = fetch_all(
        "SELECT y.Material, y.Garntyp, y.NumberOfFilaments, y.dpf, y.Titer, y.Endtiter "
        "FROM tbltrialsettings ts2 JOIN tblYarn y ON y.ID = ts2.YarnID "
        "WHERE ts2.TrialID = ? ORDER BY ts2.ID LIMIT 1",
        [trial_id],
    )
    template = input_yarn_rows[0] if input_yarn_rows else {}

    # Gemessener Titer des Quell-Trials (gleiches AVG-über-Plies-Muster wie
    # report_queries._fetch_y_values) überschreibt den kopierten Titer, falls vorhanden.
    titer_rows = fetch_all(
        "SELECT AVG(Titer) AS val FROM tbllabortiter "
        "WHERE TrialID = ? AND Titer IS NOT NULL AND Titer <> 0",
        [trial_id],
    )
    measured_titer = titer_rows[0]["val"] if titer_rows and titer_rows[0]["val"] is not None else None
    titer = int(round(float(measured_titer))) if measured_titer is not None else template.get("Titer")

    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            "INSERT INTO tblYarn "
            "(Name, Material, Garntyp, NumberOfFilaments, dpf, Titer, Endtiter, GlobalID, SourceTrialID) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            [
                name,
                template.get("Material"),
                template.get("Garntyp"),
                template.get("NumberOfFilaments"),
                template.get("dpf"),
                titer,
                template.get("Endtiter"),
                new_global_id(),
                trial_id,
            ],
        )
        new_id = cur.lastrowid
        try:
            cn.commit()
        except Exception:
            pass
    return int(new_id) if new_id else None


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
        event.acceptProposedAction()
        if dst != src:
            self._on_row_moved(src, dst)


from PySide6.QtWidgets import QStyledItemDelegate

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
        self.txtExperimentNumber = QLineEdit()
        # Default: number is auto-generated
        self.txtExperimentNumber.setReadOnly(True)
        self.txtExperimentNumber.setPlaceholderText(
            "wird automatisch vergeben (000)")

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
        row_mat.addWidget(self.treeMaterial, 1)
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
        self.treeJet.setHeaderLabels(["Jet", "Luftbohrung\n(mm)", "Winkel Luftbohrung\n(°)", "Garnkanal-Breite\n(mm)", "Luftverbrauch\n(Nm³/h)", "Entwicklungsname", "Titer Range", "Ideal Titer"])
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

        row_jet.addWidget(self.treeJet, 1)
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
        self.butJetCopy = QPushButton("Markierte kopieren")
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
        """Lädt alle Produktgruppen aus der DB in die entsprechende Combobox."""
        self.cmbProductGroup.clear()
        rows = fetch_all(
            "SELECT ID, Produktgruppe FROM tblProduktgruppe ORDER BY ID")
        for r in rows:
            self.cmbProductGroup.addItem(
                f"{r['ID']} – {r['Produktgruppe']}", r["ID"])
        self.cmbProductGroup.setCurrentIndex(-1)
        self.strExperimentData[1] = ""

    def _load_order_types(self):
        """Lädt alle Bestellungstypen aus der DB in die entsprechende Combobox."""
        self.cmbOrderType.clear()
        rows = fetch_all(
            "SELECT ID, Bestellungstyp FROM tblBestellungstyp ORDER BY ID")
        for r in rows:
            self.cmbOrderType.addItem(
                f"{r['ID']} – {r['Bestellungstyp']}", r["ID"])
        self.cmbOrderType.setCurrentIndex(-1)
        self.strExperimentData[2] = ""

    def _on_experiment_request_changed(self, *_) -> None:
        """Callback wenn ein Experiment-Request aus der Combobox gewählt wird.

        Füllt Felder aus dem gewählten Request vor (Titel, Garn, Maschine usw.).
        """
        """Update UI bits when Experiment Request selection changes."""
        self._update_expreq_icon_visibility()
        # Remove the "attention" highlight once a request is actually selected.
        self._refresh_expreq_combo_highlight()
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

        if not table_exists("tblExperimentRequests"):
            # Standard: Platzhalter auswählen
            if self.cmbExperimentRequest.count() > 0:
                self.cmbExperimentRequest.setCurrentIndex(0)
            else:
                self.cmbExperimentRequest.setCurrentIndex(-1)
            return

        # tblProjects (plural) oder tblProject (singular) akzeptieren
        project_table = None
        if table_exists("tblProjects"):
            project_table = "tblProjects"
        elif table_exists("tblProject"):
            project_table = "tblProject"
        else:
            self.cmbExperimentRequest.setCurrentIndex(-1)
            return

        req_cols = get_columns_map("tblExperimentRequests")
        prj_cols = get_columns_map(project_table)

        col_req_id = resolve_field(["ID"], req_cols) or "ID"
        col_req_status = resolve_field(["RequestStatus", "Status"], req_cols) or "RequestStatus"
        col_req_proj = resolve_field(["Projekt", "Project", "ProjectID"], req_cols) or "Projekt"

        col_prj_id = resolve_field(["ID"], prj_cols) or "ID"
        col_prj_no = resolve_field(["Project Number", "ProjectNumber", "Projekt Nummer", "ProjektNummer"], prj_cols)
        col_prj_name = resolve_field(["Project Name", "ProjectName", "Projekt Name", "ProjektName"], prj_cols)

        if not (col_prj_no and col_prj_name):
            # Ohne diese beiden Spalten können wir das gewünschte Anzeigeformat nicht sicher erstellen
            self.cmbExperimentRequest.setCurrentIndex(-1)
            return

        # Optional: nur Requests zeigen, die noch *nicht* in einem Experiment verknüpft sind.
        exp_join = ""
        exp_where = ""
        resolved = self._resolve_experiments_table_and_columns()
        if resolved:
            exp_table, exp_cols = resolved
            col_expreq = exp_cols.get("expreq")
            if col_expreq:
                # ID-Spalte der Experimente-Tabelle (kann in manchen DBs abweichen)
                exp_cmap = get_columns_map(exp_table)
                col_exp_id = resolve_field(["ID"], exp_cmap) or "ID"

                # LEFT JOIN, dann nur die ohne Match (nicht verknüpft)
                exp_join = f"LEFT JOIN [{exp_table}] AS e ON e.[{col_expreq}] = r.[{col_req_id}]\n"
                exp_where = f"AND e.[{col_exp_id}] IS NULL\n"

        # Titel als Fallback fürs Label
        col_req_title = resolve_field(["Titel", "Title"], req_cols)

        # JOIN auf Projekt ist nice-to-have, nicht zwingend.
        has_project_cols = bool(col_prj_no and col_prj_name)
        select_project = ""
        join_project = ""
        if has_project_cols:
            select_project = f", p.[{col_prj_no}] AS ProjectNo, p.[{col_prj_name}] AS ProjectName"
            join_project = (
                f"LEFT JOIN [{project_table}] AS p ON r.[{col_req_proj}] = p.[{col_prj_id}]\n"
            )

        select_title = f", r.[{col_req_title}] AS ReqTitle" if col_req_title else ""

        sql = (
            f"SELECT r.[{col_req_id}] AS RequestID"
            f"{select_project}"
            f"{select_title}\n"
            f"FROM [tblExperimentRequests] AS r\n"
            f"{join_project}"
            f"{exp_join}"
            f"WHERE 1=1\n"
            f"AND r.[{col_req_status}] = ?\n"
            f"{exp_where}"
            f"ORDER BY r.[{col_req_id}] DESC"
        )

        try:
            rows = fetch_all(sql, [3])
        except Exception:
            rows = []

        # Remember whether there are approved requests available.
        # We only want to highlight the dropdown as "attention" *until* the user selects one.
        self._expreq_has_approved = bool(rows)
        self._refresh_expreq_combo_highlight()

        for r in rows:
            rid = r.get("RequestID")
            if rid is None:
                continue

            pno = r.get("ProjectNo")
            pname = r.get("ProjectName")
            title = r.get("ReqTitle")

            # Build display text robustly (avoid UnboundLocalError)
            parts = []
            if pno not in (None, '') or pname not in (None, ''):
                base_txt = f"{pno} - {pname}".strip(' -')
                if base_txt:
                    parts.append(base_txt)
            if title not in (None, ''):
                t = str(title).strip()
                if t:
                    parts.append(t)
            txt = ' - '.join(parts).strip(' -') if parts else f"Request {rid}"


            self.cmbExperimentRequest.addItem(txt, int(rid))

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
                QMessageBox.critical(self, "Open Experiment Request", f"{e}")
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


    def _set_experiment_request_status(self, cur, request_id: int, new_status: int):
        """Setzt tblExperimentRequests.RequestStatus auf den gewünschten Wert."""
        if not table_exists("tblExperimentRequests"):
            return
        req_cols = get_columns_map("tblExperimentRequests")
        col_id = resolve_field(["ID"], req_cols) or "ID"
        col_status = resolve_field(["RequestStatus", "Status"], req_cols) or "RequestStatus"
        cur.execute(
            f"UPDATE [tblExperimentRequests] SET [{col_status}] = ? WHERE [{col_id}] = ?",
            [int(new_status), int(request_id)],
        )
    def _load_backlog_status(self):
        """Backlog-Status für neue TrialSeries laden (nur 'Backlog' und 'In Progress')."""
        if not hasattr(self, "cmbBacklogStatus"):
            return
        self.cmbBacklogStatus.clear()
        try:
            rows = fetch_all(
                "SELECT ID, BacklogStatus FROM tblBacklogStatus ORDER BY ID"
            )
        except Exception:
            rows = [
                {"ID": 1, "BacklogStatus": "Backlog"},
                {"ID": 2, "BacklogStatus": "In Progress"},
            ]

        wanted = ["Backlog", "In Progress"]
        filtered = [
            r for r in rows
            if str(r.get("BacklogStatus", "")).strip() in wanted
        ]
        if not filtered:
            filtered = rows

        order = {name: idx for idx, name in enumerate(wanted)}
        filtered.sort(
            key=lambda r: order.get(
                str(r.get("BacklogStatus", "")).strip(), 99)
        )

        for r in filtered:
            name = str(r.get("BacklogStatus", "")).strip()
            _id = r.get("ID")
            self.cmbBacklogStatus.addItem(name, _id)

        if self.cmbBacklogStatus.count() > 0:
            idx = self.cmbBacklogStatus.findText("Backlog")
            self.cmbBacklogStatus.setCurrentIndex(idx if idx >= 0 else 0)
        else:
            self.cmbBacklogStatus.setCurrentIndex(-1)

    def _load_existing_experiments(self):
        """Für addSeries/addTrials: Combo mit bestehenden Experimenten befüllen.
           Anzeigeformat: YEAR-PGOT-NNN (z. B. 2025-70-006 bei PG=7, OT=0)"""
        self.cmbExistingExperiment.clear()
        resolved = self._resolve_experiments_table_and_columns()
        if not resolved:
            QMessageBox.warning(self, "Existing Experiment",
                                "Experimente‑Tabelle/Spalten nicht gefunden.")
            return
        table, cols = resolved
        try:
            rows = fetch_all(
                f"SELECT ID AS EID, [{cols['year']}] AS Y, "
                f"[{cols['pg']}] AS PG, [{cols['ot']}] AS OT, "
                f"[{cols['num']}] AS Num, [{cols['machine']}] AS MID "
                f"FROM {table} "
                f"ORDER BY [{cols['year']}] DESC, [{cols['pg']}], [{cols['ot']}], [{cols['num']}]"
            )
            for r in rows:
                num = r['Num']
                try:
                    numtxt = f"{int(num):03d}"
                except Exception:
                    numtxt = str(num)
                pg = str(r.get('PG', '')).strip()
                ot = str(r.get('OT', '')).strip()
                disp_mid = f"{pg}{ot}"
                disp = f"{r['Y']}-{disp_mid}-{numtxt}"
                self.cmbExistingExperiment.addItem(
                    disp,
                    (r['EID'], r['MID'], r['Y'], r['PG'], r['OT'], r['Num'])
                )
            if self.existing_experiment_id is not None:
                for i in range(self.cmbExistingExperiment.count()):
                    data = self.cmbExistingExperiment.itemData(i)
                    if data and data[0] == self.existing_experiment_id:
                        self.cmbExistingExperiment.setCurrentIndex(i)
                        break
            else:
                self.cmbExistingExperiment.setCurrentIndex(-1)
        except Exception as e:
            QMessageBox.critical(self, "Existing Experiment",
                                 f"Fehler beim Laden:\n{e}")

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
        if not table_exists("tblTrial"):
            return

        cmap_t = get_columns_map("tblTrial")
        col_t_sid = resolve_field(
            ["TrialSeriesID", "SerieID", "SeriesID"], cmap_t) or "TrialSeriesID"
        col_t_no = resolve_field(["Versuchsnummer", "TrialNumber",
                                 "VersuchsNr", "VNr", "Number"], cmap_t) or "Versuchsnummer"
        col_t_id = resolve_field(["ID"], cmap_t) or "ID"

        sql = f"SELECT [{col_t_id}] AS TID, [{col_t_no}] AS TNo FROM [tblTrial] WHERE [{col_t_sid}] = ? ORDER BY [{col_t_no}]"
        rows = fetch_all(sql, [series_id])

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
            cb = QCheckBox(f"V{label}")
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
        table = "tblTrialSeries"
        if not table_exists(table):
            QMessageBox.warning(self, "Trial Series",
                                "Tabelle 'tblTrialSeries' nicht gefunden.")
            return
        cmap = get_columns_map(table)
        col_id = resolve_field(["ID"], cmap) or "ID"
        col_exp = resolve_field(["ExperimentID"], cmap) or "ExperimentID"
        col_name = resolve_field(["SeriesName", "Name"], cmap) or "SeriesName"
        rows = fetch_all(
            f"SELECT [{col_id}] AS SID, [{col_name}] AS SName FROM {table} WHERE [{col_exp}] = ? ORDER BY [{col_id}]",
            [exp_id]
        )
        for r in rows:
            self.cmbExistingSeries.addItem(str(r["SName"]), int(r["SID"]))
        if rows:
            self.cmbExistingSeries.setCurrentIndex(0)
        else:
            self.cmbExistingSeries.setCurrentIndex(-1)

    def _load_yarns(self):
        """Material-Auswahl als einklappbarer Tree nach YarnGroup.

        Gruppen-Header:
            --> <GroupNumber> - <GroupName>
        Child-Einträge sind die bisherigen Dropdown-Zeilen.
        """
        self.treeMaterial.clear()

        # --> Groups laden (tblyarngroup) -->
        gtable = "tblyarngroup"
        groups: list[dict] = []

        if table_exists(gtable):
            gcmap = get_columns_map(gtable)
            g_id = resolve_field(["ID"], gcmap) or "ID"
            g_no = resolve_field(["GroupNumber", "GruppenNummer", "GroupNo", "Nummer", "Number"], gcmap)
            g_name = resolve_field(["GroupName", "GruppenName", "Name", "Bezeichnung"], gcmap)

            sel_cols = [f"[{g_id}] AS GID"]
            sel_cols.append(f"[{g_no}] AS GNo" if g_no else "NULL AS GNo")
            sel_cols.append(f"[{g_name}] AS GName" if g_name else "NULL AS GName")

            order = f"ORDER BY [{g_no}] ASC" if g_no else f"ORDER BY [{g_id}] ASC"
            rows = fetch_all(f"SELECT {', '.join(sel_cols)} FROM {gtable} {order}")

            for r in rows:
                gid = r.get("GID")
                if gid is None:
                    continue
                gno_raw = r.get("GNo")
                gname = str(r.get("GName") or "").strip()
                try:
                    gno = int(str(gno_raw).strip()) if gno_raw not in (None, "") else None
                except Exception:
                    gno = None

                if gno is not None and gname:
                    label = f"{gno} | {gname}"
                elif gno is not None and not gname:
                    label = f"{gno} |"
                elif gno is None and gname:
                    label = f"| {gname}"
                else:
                    label = "Group"

                groups.append({"GID": gid, "GNo": gno, "GName": gname, "Label": label})

            # Natural sort by GroupNumber (None -> last)
            groups.sort(key=lambda d: (d["GNo"] is None, d["GNo"] if d["GNo"] is not None else 0, str(d["GName"]).lower()))
        else:
            groups = [{"GID": None, "GNo": None, "GName": "", "Label": "Material"}]

        # --> Yarns laden (tblYarn) -->
        ytable = "tblYarn"
        if not table_exists(ytable):
            self.butAddMaterial.setEnabled(False)
            self.butAddTrialPly.setEnabled(False)
            return

        ycmap = get_columns_map(ytable)
        y_id = resolve_field(["ID"], ycmap) or "ID"
        y_name = resolve_field(["Name", "Bezeichnung", "YarnName", "Material"], ycmap)
        y_group = resolve_field(["YarnGroupID", "YarnGroup", "GroupID", "Group"], ycmap)
        # Automatisch angelegte Halbfabrikat-"Schatten"-Garne (siehe
        # get_or_create_shadow_yarn()) sollen hier nicht auftauchen - die
        # werden gezielt über den "+ Trial"-Button ausgewählt, nicht über den
        # normalen Katalog-Baum. Spalte optional (resolve_field), falls diese
        # Umgebung die Migration noch nicht hat.
        y_src_trial = resolve_field(["SourceTrialID"], ycmap)
        _where_no_shadow = f" WHERE [{y_src_trial}] IS NULL" if y_src_trial else ""

        if not y_name:
            self.butAddMaterial.setEnabled(False)
            self.butAddTrialPly.setEnabled(False)
            return

        if y_group:
            yrows = fetch_all(
                f"SELECT [{y_id}] AS YarnID, [{y_name}] AS YarnName, [{y_group}] AS GID "
                f"FROM {ytable}{_where_no_shadow} ORDER BY [{y_group}] ASC, [{y_name}] ASC"
            )
        else:
            yrows = fetch_all(
                f"SELECT [{y_id}] AS YarnID, [{y_name}] AS YarnName, NULL AS GID "
                f"FROM {ytable}{_where_no_shadow} ORDER BY [{y_name}] ASC"
            )

        yarns_by_gid: dict[Any, list[dict]] = {}
        for r in yrows:
            yarns_by_gid.setdefault(r.get("GID"), []).append(r)

        # --> Tree bauen -->
        any_children = False
        for g in groups:
            top = QTreeWidgetItem([g["Label"]])
            top.setData(0, Qt.UserRole, {"kind": "group", "gid": g.get("GID")})
            try:
                f = top.font(0)
                f.setBold(True)
                top.setFont(0, f)
                top.setForeground(0, QColor("#39A650"))
            except Exception:
                pass

            self.treeMaterial.addTopLevelItem(top)

            gid = g.get("GID")
            children = yarns_by_gid.get(gid, [])

            # Falls YarnGroupID evtl. GroupNumber statt Group-ID ist
            if not children and gid is not None:
                gno = g.get("GNo")
                if gno is not None:
                    children = yarns_by_gid.get(gno, [])

            for yr in children:
                yid = yr.get("YarnID")
                yname = str(yr.get("YarnName") or "").strip()
                if yid is None or not yname:
                    continue
                child = QTreeWidgetItem([yname])
                child.setData(0, Qt.UserRole, {"kind": "yarn", "yarn_id": yid, "yarn_name": yname})
                top.addChild(child)
                any_children = True

            # expansion is handled after building the tree

        # Default: expand only the group "1 | Standard Yarn" (all others collapsed)
        target_item = None
        for i in range(self.treeMaterial.topLevelItemCount()):
            it = self.treeMaterial.topLevelItem(i)
            try:
                meta = it.data(0, Qt.UserRole) or {}
                gid = (meta.get("gid") if isinstance(meta, dict) else None)
            except Exception:
                gid = None

            # Determine the label in a robust way
            label = (it.text(0) or "").strip()
            if label.lower() == "1 | standard yarn":
                target_item = it
                break

        # Fallback: if not found, expand first group (if any)
        if target_item is None and self.treeMaterial.topLevelItemCount() > 0:
            target_item = self.treeMaterial.topLevelItem(0)

        for i in range(self.treeMaterial.topLevelItemCount()):
            it = self.treeMaterial.topLevelItem(i)
            it.setExpanded(it is target_item)

        # If there are no child entries at all, keep everything expanded so the user sees something
        if not any_children:
            for i in range(self.treeMaterial.topLevelItemCount()):
                self.treeMaterial.topLevelItem(i).setExpanded(True)

        self.treeMaterial.clearSelection()
        self._update_add_material_enabled()

    def _load_jets(self):
        """Jet-Auswahl als einklappbarer Tree nach JetGroup.

        Erwartete Tabellen:
            - tbljetgroup: ID, GroupNumber, GroupName
            - tbljets: ID, Name (oder Jet/Bezeichnung), JetGroupID

        Fallback: wenn nur tblDTYJets existiert, werden alle Jets in einer Gruppe angezeigt.
        """
        if hasattr(self, "treeJet"):
            self.treeJet.clear()
        else:
            return

        # --> Groups laden (tbljetgroup) -->
        gtable = "tbljetgroup"
        groups: list[dict] = []

        if table_exists(gtable):
            cmap = get_columns_map(gtable)
            g_id = resolve_field(["ID"], cmap) or "ID"
            g_no = resolve_field(["GroupNumber", "Number", "Nr", "No"], cmap)
            g_name = resolve_field(["GroupName", "Name", "Bezeichnung"], cmap)

            sel_cols = [f"[{g_id}] AS GID"]
            sel_cols.append(f"[{g_no}] AS GNo" if g_no else "NULL AS GNo")
            sel_cols.append(f"[{g_name}] AS GName" if g_name else "NULL AS GName")

            order = f"ORDER BY [{g_no}] ASC" if g_no else f"ORDER BY [{g_id}] ASC"
            rows = fetch_all(f"SELECT {', '.join(sel_cols)} FROM {gtable} {order}")

            for r in rows:
                gid = r.get("GID")
                if gid is None:
                    continue
                gno_raw = r.get("GNo")
                gname = str(r.get("GName") or "").strip()
                try:
                    gno = int(str(gno_raw).strip()) if gno_raw not in (None, "") else None
                except Exception:
                    gno = None

                if gno is not None and gname:
                    label = f"{gno} | {gname}"
                elif gno is not None and not gname:
                    label = f"{gno} |"
                elif gno is None and gname:
                    label = f"| {gname}"
                else:
                    label = "Group"

                groups.append({"GID": gid, "GNo": gno, "GName": gname, "Label": label})

            groups.sort(key=lambda d: (d["GNo"] is None, d["GNo"] if d["GNo"] is not None else 0, str(d["GName"]).lower()))
        else:
            groups = [{"GID": None, "GNo": None, "GName": "", "Label": "Jets"}]

        # --> Jets laden (inkl. Geometrie-Spalten aus tblDTYJets) -->
        # Geometrie-Map: JetID -> dict mit Luftbohrung etc.
        geo_map: dict[Any, dict] = {}
        try:
            if table_exists("tblDTYJets"):
                geo_cmap = get_columns_map("tblDTYJets")
                geo_id_col = resolve_field(["ID"], geo_cmap) or "ID"
                _geo_cols = {
                    "Luftbohrung":      resolve_field(["Luftbohrung"], geo_cmap),
                    "WinkelLuftbohrung": resolve_field(["WinkelLuftbohrung", "Winkel Luftbohrung"], geo_cmap),
                    "GarnkanalBreite":  resolve_field(["GarnkanalBreite", "Garnkanal Breite", "GarnkanalB"], geo_cmap),
                    "Luftverbrauch":    resolve_field(["Luftverbrauch"], geo_cmap),
                    "Entwicklungsname": resolve_field(["Entwicklungsname"], geo_cmap),
                }
                sel_geo = [f"[{geo_id_col}] AS GeoID"]
                for alias, col in _geo_cols.items():
                    sel_geo.append(f"[{col}] AS {alias}" if col else f"NULL AS {alias}")
                geo_rows = fetch_all(f"SELECT {', '.join(sel_geo)} FROM tblDTYJets")
                for gr in geo_rows:
                    gid_raw = gr.get("GeoID")
                    if gid_raw is None:
                        continue
                    geo_map[gid_raw] = gr
                    try:
                        geo_map[int(gid_raw)] = gr
                    except Exception:
                        pass
                    geo_map[str(gid_raw)] = gr
        except Exception:
            pass

        def _geo_val(jet_id: Any, key: str) -> str:
            """Gibt Geometrie-Wert als String zurück, oder '' wenn nicht vorhanden."""
            entry = geo_map.get(jet_id) or geo_map.get(str(jet_id)) or {}
            val = entry.get(key)
            if val is None or str(val).strip() == "":
                return ""
            try:
                f = float(val)
                # Trailing zeros entfernen, aber mindestens eine Nachkommastelle
                s = f"{f:.3f}".rstrip("0").rstrip(".")
                return s
            except Exception:
                return str(val).strip()

        # Preferred: tbljets
        jtable = "tbljets"
        if table_exists(jtable):
            cmap = get_columns_map(jtable)
            j_id = resolve_field(["ID"], cmap) or "ID"
            j_name = resolve_field(["Name", "Jet", "Bezeichnung"], cmap)
            j_group = resolve_field(["JetGroupID", "GroupID", "Group"], cmap)
            j_tvon = resolve_field(["TiterVon"], cmap)
            j_tbis = resolve_field(["TiterBis"], cmap)
            j_ideal = resolve_field(["IdealTiter"], cmap)

            if not j_name:
                return

            extra_cols = []
            extra_cols.append(f"[{j_tvon}] AS TiterVon" if j_tvon else "NULL AS TiterVon")
            extra_cols.append(f"[{j_tbis}] AS TiterBis" if j_tbis else "NULL AS TiterBis")
            extra_cols.append(f"[{j_ideal}] AS IdealTiter" if j_ideal else "NULL AS IdealTiter")
            extra_sql = ", " + ", ".join(extra_cols)

            if j_group:
                jrows = fetch_all(
                    f"SELECT [{j_id}] AS JetID, [{j_name}] AS JetName, [{j_group}] AS GID"
                    f"{extra_sql} "
                    f"FROM {jtable} ORDER BY [{j_group}] ASC, [{j_name}] ASC"
                )
            else:
                jrows = fetch_all(
                    f"SELECT [{j_id}] AS JetID, [{j_name}] AS JetName, NULL AS GID"
                    f"{extra_sql} "
                    f"FROM {jtable} ORDER BY [{j_name}] ASC"
                )
        else:
            # Fallback: tblDTYJets (alte Struktur)
            table = "tblDTYJets"
            if not table_exists(table):
                return
            cmap = get_columns_map(table)
            col_id = resolve_field(["ID"], cmap) or "ID"
            col_jet = resolve_field(["Jet", "Name", "Bezeichnung"], cmap)
            col_group = resolve_field(["JetGroupID", "GroupID", "Group"], cmap)
            if not col_jet:
                return
            if col_group:
                jrows = fetch_all(
                    f"SELECT [{col_id}] AS JetID, [{col_jet}] AS JetName, [{col_group}] AS GID "
                    f"FROM {table} ORDER BY [{col_group}] ASC, [{col_jet}] ASC"
                )
            else:
                jrows = fetch_all(
                    f"SELECT [{col_id}] AS JetID, [{col_jet}] AS JetName, NULL AS GID "
                    f"FROM {table} ORDER BY [{col_jet}] ASC"
                )

        jets_by_gid: dict[Any, list[dict]] = {}
        self._jet_titer_map: dict[Any, dict] = {}
        for r in jrows:
            jets_by_gid.setdefault(r.get("GID"), []).append(r)
            jid_r = r.get("JetID")
            if jid_r is not None:
                self._jet_titer_map[jid_r] = {
                    "TiterVon": r.get("TiterVon"),
                    "TiterBis": r.get("TiterBis"),
                    "IdealTiter": r.get("IdealTiter"),
                }

        def _titer_range_val(jet_id: Any) -> str:
            tm = self._jet_titer_map.get(jet_id) or {}
            tvon = tm.get("TiterVon")
            tbis = tm.get("TiterBis")
            if tvon is not None and tbis is not None and str(tvon).strip() and str(tbis).strip():
                return f"{tvon} dtex - {tbis} dtex"
            return ""

        def _ideal_titer_val(jet_id: Any) -> str:
            tm = self._jet_titer_map.get(jet_id) or {}
            ideal = tm.get("IdealTiter")
            if ideal is not None and str(ideal).strip():
                return f"{ideal} dtex"
            return ""

        # --> Tree bauen -->
        any_children = False
        for g in groups:
            label = str(g.get("Label") or "Group")
            top = QTreeWidgetItem([label, "", "", "", "", "", "", ""])
            top.setData(0, Qt.UserRole, {"kind": "group", "gid": g.get("GID")})
            try:
                f = top.font(0)
                f.setBold(True)
                top.setFont(0, f)
                top.setForeground(0, QColor("#39A650"))
            except Exception:
                pass

            self.treeJet.addTopLevelItem(top)
            top.setFirstColumnSpanned(True)

            gid = g.get("GID")
            children = jets_by_gid.get(gid, [])

            # Falls JetGroupID evtl. GroupNumber statt Group-ID ist
            if not children and gid is not None:
                gno = g.get("GNo")
                if gno is not None:
                    children = jets_by_gid.get(gno, [])

            for jt in children:
                jid = jt.get("JetID")
                jname = str(jt.get("JetName") or "").strip()
                if jid is None or not jname:
                    continue
                child = QTreeWidgetItem([
                    jname,
                    _geo_val(jid, "Luftbohrung"),
                    _geo_val(jid, "WinkelLuftbohrung"),
                    _geo_val(jid, "GarnkanalBreite"),
                    _geo_val(jid, "Luftverbrauch"),
                    _geo_val(jid, "Entwicklungsname"),
                    _titer_range_val(jid),
                    _ideal_titer_val(jid),
                ])
                child.setData(0, Qt.UserRole, {"kind": "jet", "jet_id": jid, "jet_name": jname})
                # Numerische Spalten rechtsbündig
                for col_idx in (1, 2, 3, 4):
                    child.setTextAlignment(col_idx, Qt.AlignRight | Qt.AlignVCenter)
                top.addChild(child)
                any_children = True

        # Default: expand first group (oder alles, wenn keine Gruppen existieren)
        if self.treeJet.topLevelItemCount() > 0:
            self.treeJet.topLevelItem(0).setExpanded(True)
        if not any_children:
            for i in range(self.treeJet.topLevelItemCount()):
                self.treeJet.topLevelItem(i).setExpanded(True)

        # Spaltenbreiten anpassen
        for col_idx in range(self.treeJet.columnCount()):
            self.treeJet.resizeColumnToContents(col_idx)
        # Spalte 0 etwas Luft geben
        self.treeJet.setColumnWidth(0, max(self.treeJet.columnWidth(0), 120))

        # Sortier-Zustand zurücksetzen
        self._jet_sort_col = -1
        self._jet_sort_asc = True
        self.treeJet.header().setSortIndicator(-1, Qt.AscendingOrder)

        self.treeJet.clearSelection()
        self.butAddJet.setEnabled(False)

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
        if table_exists("tblHousing"):
            cmap = get_columns_map("tblHousing")
            col_id = resolve_field(["ID"], cmap) or "ID"
            col_name = resolve_field(["HousingName", "Name", "Bezeichnung"], cmap)
            if col_name:
                rows = fetch_all(
                    f"SELECT [{col_id}] AS HID, [{col_name}] AS HName "
                    f"FROM tblHousing ORDER BY [{col_name}]"
                )
                for r in rows:
                    self.cmbHousing.addItem(str(r["HName"]), r["HID"])
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
        self.cmbMachine.clear()
        table = "tblMaschine"
        if not table_exists(table):
            QMessageBox.warning(
                self, "Machine", "Tabelle 'tblMaschine' nicht gefunden.")
            return
        cmap = get_columns_map(table)
        col_id = resolve_field(["ID"], cmap) or "ID"
        col_name = resolve_field(["Maschine", "Machine", "Name"], cmap)
        if not col_name:
            QMessageBox.warning(
                self, "Machine", "Spalte 'Maschine' nicht gefunden.")
            return

        # Optionales Joker-Flag erkennen (tblMaschine.IsJoker)
        col_is_joker = resolve_field(["IsJoker", "Is Joker", "Joker"], cmap)

        if col_is_joker:
            sql = (
                f"SELECT [{col_id}] AS MID, "
                f"[{col_name}] AS MName, "
                f"[{col_is_joker}] AS MIsJoker "
                f"FROM {table} ORDER BY [{col_name}]"
            )
        else:
            sql = (
                f"SELECT [{col_id}] AS MID, "
                f"[{col_name}] AS MName "
                f"FROM {table} ORDER BY [{col_name}]"
            )

        rows = fetch_all(sql)
        for r in rows:
            is_joker = False
            if "MIsJoker" in r:
                val = r.get("MIsJoker")
                try:
                    # Access speichert Booleans häufig als 0/‑1
                    is_joker = bool(int(val))
                except Exception:
                    is_joker = bool(val)

            self.cmbMachine.addItem(str(r["MName"]), r["MID"])
            idx = self.cmbMachine.count() - 1
            # Joker-Flag als zusätzliches Item-Data (UserRole+1) ablegen
            self.cmbMachine.setItemData(idx, bool(is_joker), Qt.UserRole + 1)

        self.cmbMachine.setCurrentIndex(-1)

    def _load_lab_machines(self):
        # _lab_machines ist ein dict: LMID -> Meta
        self._lab_machines.clear()
        self.cmbLabMachine.clear()

        table = "tblLabMachines"
        if not table_exists(table):
            QMessageBox.warning(self, "Lab Machines",
                                "Tabelle 'tblLabMachines' nicht gefunden.")
            return

        cmap = get_columns_map(table)
        col_id = resolve_field(["ID"], cmap) or "ID"
        col_name = resolve_field(["LabMachineName", "LabMachine", "Name"], cmap) or "LabMachineName"

        # optionale Spalten (können im MySQL-Schema fehlen)
        col_add = resolve_field(["AdditionalField", "AdditinalField"], cmap)
        col_unit = resolve_field(["AdditionalFieldUnit", "Unit"], cmap)
        col_tbl = resolve_field(["TableName", "LaborTable", "Table"], cmap)
        col_src = resolve_field(["AdditionalFieldSource", "AddFieldSource", "Source"], cmap)
        col_rowmode = resolve_field(["RowMode"], cmap)

        def _sel(col, alias, default_sql="NULL"):
            # Erzeugt " [col] AS alias " oder " NULL AS alias "
            if col:
                return f"[{col}] AS {alias}"
            return f"{default_sql} AS {alias}"

        rowmode_default = "'PerTrial'"
        sql = (
            f"SELECT [{col_id}] AS LMID, "
            f"[{col_name}] AS LMName, "
            f"{_sel(col_add, 'AddField')}, "
            f"{_sel(col_unit, 'AddUnit')}, "
            f"{_sel(col_tbl, 'Tbl')}, "
            f"{_sel(col_src, 'Src')}, "
            f"{_sel(col_rowmode, 'RowMode', rowmode_default)} "
            f"FROM {table} ORDER BY [{col_name}]"
        )

        rows = fetch_all(sql)
        for r in rows:
            lm_id = r.get("LMID")
            if lm_id is None:
                continue

            name = str(r.get("LMName") or "").strip()

            # Robust: Itemat braucht praktisch immer ein Additional Field (Tension).
            # Wenn im Schema/Datensatz nichts gepflegt ist, setzen wir Defaults.
            add_field = (r.get("AddField") or "").strip() if isinstance(r.get("AddField"), str) else (r.get("AddField") or "")
            add_unit = (r.get("AddUnit") or "").strip() if isinstance(r.get("AddUnit"), str) else (r.get("AddUnit") or "")

            if (not add_field) and self._is_itemat(r, name):
                add_field = "Tension"
                # Einheit nur setzen, wenn nichts vorgegeben ist
                if not add_unit:
                    add_unit = "cN/dtex"
                r["AddField"] = add_field
                r["AddUnit"] = add_unit

            self.cmbLabMachine.addItem(name, lm_id)
            r["Unit"] = add_unit
            self._lab_machines[int(lm_id)] = r

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

    def _parse_additional_value(self, val):
        """Extract a float from strings like '0.3 cN/dtex'; return original if no number found."""
        try:
            if isinstance(val, (int, float)):
                return float(val)
            s = str(val).strip()
            import re as _re
            m = _re.search(r'[-+]?\d+(?:[.,]\d+)?', s)
            if m:
                return float(m.group(0).replace(',', '.'))
        except Exception:
            pass
        return val

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
                self, "Save", "Bitte mindestens einen Trial anhaken.")
            return

        try:
            with get_connection() as cn:
                cn.autocommit = False
                cur = cn.cursor()
                inserted = 0
                skipped = 0

                # Einige Labor-Tabellen haben einen NOT NULL FK auf tbluser(ID) (z.B. tbllabordtyomat.UserID).
                # Wenn UserID beim INSERT fehlt, setzt MySQL je nach Default z.B. 0 → FK-Fehler.
                # Primär: aktueller Login-User (app_meta.current_user['id']); Fallback: MIN(ID) aus tbluser.
                default_user_id = None
                try:
                    if app_meta.current_user and app_meta.current_user.get("id") is not None:
                        default_user_id = int(app_meta.current_user.get("id"))
                except Exception:
                    default_user_id = None
                if default_user_id is None and table_exists("tbluser"):
                    try:
                        urows = fetch_all("SELECT MIN([ID]) AS uid FROM tbluser")
                        if urows and urows[0].get("uid") is not None:
                            default_user_id = int(urows[0]["uid"])
                    except Exception:
                        default_user_id = None

                for lm in self._lab_data:
                    if str(lm.get("RowMode") or "").strip().lower() == "seriesfreeform":
                        # Jet Air Consumption & Co: keine Zeile pro Trial -
                        # wird unten einmal pro Series (physische Duese x Druck) angelegt.
                        continue
                    tbl = (lm.get("TableName") or "").strip()
                    if not tbl or not table_exists(tbl):
                        continue
                    lcols = get_columns_map(tbl)
                    col_trial = resolve_field(["TrialID"], lcols) or "TrialID"
                    add_src = (lm.get("AdditionalFieldSource") or "").strip()
                    add_real = resolve_field(
                        [add_src], lcols) if add_src else None
                    add_val = lm.get("AdditionalVal", None)
                    # parse numeric from strings with units
                    add_val = self._parse_additional_value(add_val)
                    if isinstance(add_val, (bytes, bytearray)):
                        try:
                            add_val = add_val.decode('utf-8')
                        except Exception:
                            add_val = float(add_val[0]) if len(
                                add_val) > 0 else None

                    # optionaler UserID (FK auf tbluser) – falls vorhanden, sauber setzen
                    col_user = resolve_field(["UserID", "User", "CreatedBy", "CreatedByID"], lcols)

                    for tid in selected_trial_ids:
                        # Special case: Waterbath → allow 3 rows on first creation (no additional field)
                        if 'waterbath' in tbl.lower():
                            try:
                                cur.execute(
                                    f"SELECT COUNT(*) AS Cnt FROM [{tbl}] WHERE [{col_trial}] = ?", [tid])
                                row = cur.fetchone()
                                cnt = int(row[0] if row is not None else 0)
                            except Exception:
                                cnt = 0
                            if cnt == 0:
                                col_gid = resolve_field(["GlobalID"], lcols)
                                for _ in range(3):
                                    cols_sql_parts = [f"[{col_trial}]"]
                                    params = [tid]
                                    if col_gid:
                                        cols_sql_parts.append(f"[{col_gid}]")
                                        params.append(new_global_id())
                                    if col_user:
                                        if default_user_id is None:
                                            raise Exception("No valid user found (tbluser). Please log in first or check tbluser.")
                                        cols_sql_parts.append(f"[{col_user}]")
                                        params.append(default_user_id)
                                    placeholders = ",".join(
                                        ["?"] * len(params))
                                    cur.execute(
                                        f"INSERT INTO [{tbl}] (" + ",".join(
                                            cols_sql_parts) + ") VALUES (" + placeholders + ")",
                                        params,
                                    )
                                    inserted += 1
                            else:
                                skipped += 1
                            continue

                        # Normal machines (with/without additional)
                        exists = False
                        try:
                            if add_real:
                                cur.execute(f"SELECT 1 FROM [{tbl}] WHERE [{col_trial}] = ? AND [{add_real}] = ?", [
                                            tid, add_val])
                            else:
                                cur.execute(
                                    f"SELECT 1 FROM [{tbl}] WHERE [{col_trial}] = ?", [tid])
                            exists = cur.fetchone() is not None
                        except Exception:
                            exists = False
                        if exists:
                            skipped += 1
                            continue
                        col_gid = resolve_field(["GlobalID"], lcols)
                        cols_sql_parts = [f"[{col_trial}]"]
                        params = [tid]
                        if col_gid:
                            cols_sql_parts.append(f"[{col_gid}]")
                            params.append(new_global_id())
                        if add_real is not None:
                            cols_sql_parts.append(f"[{add_real}]")
                            params.append(add_val)
                        if col_user:
                            if default_user_id is None:
                                raise Exception("No valid user found (tbluser). Please log in first or check tbluser.")
                            cols_sql_parts.append(f"[{col_user}]")
                            params.append(default_user_id)
                        placeholders = ",".join(["?"] * len(params))
                        cur.execute(
                            f"INSERT INTO [{tbl}] (" + ",".join(cols_sql_parts) +
                            ") VALUES (" + placeholders + ")",
                            params,
                        )
                        inserted += 1

                jet_air_stats = self._save_jet_air_consumption_rows(cur, ts_id)
                cn.commit()

            msg_lines = [
                "Lab Machines zugewiesen.",
                f"Experiment ID: {exp_id} • Serie: {ts_id}",
                f"Created: {inserted} • Skipped (already exists): {skipped}",
            ]
            if any(jet_air_stats.values()):
                if jet_air_stats["physical_jets"] == 0:
                    msg_lines.append(
                        "Jet Air Consumption: keine physische Düse (JetID) in dieser Series gefunden — "
                        "es wurden keine Zeilen angelegt.")
                else:
                    msg_lines.append(
                        f"Jet Air Consumption: {jet_air_stats['created']} Zeile(n) erstellt, "
                        f"{jet_air_stats['skipped_exists']} bereits vorhanden, "
                        f"{jet_air_stats['physical_jets']} physische Düse(n) gefunden"
                        + (f", {jet_air_stats['no_user']} übersprungen (kein User)"
                           if jet_air_stats['no_user'] else "") + ".")
            QMessageBox.information(self, "Saved", "\n".join(msg_lines))
        except Exception as e:
            try:
                cn.rollback()
            except Exception:
                pass
            QMessageBox.critical(self, "Save failed", f"{e}")

    def _save_addtrials(self):
        """Erstellt neue Trials in der gewählten TrialSeries.
        Gleiche Logik wie create, aber Experiment + Series bereits vorhanden.
        Anzahl Trials = Jets × Platten (identisch mit normalem Create).
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
            QMessageBox.critical(self, "Save", "Tabelle 'tblTrial' nicht gefunden.")
            return
        tr_cols = get_columns_map(trial_table)
        tr_sid     = resolve_field(["TrialSeriesID", "SerieID", "SeriesID"], tr_cols) or "TrialSeriesID"
        tr_no      = resolve_field(["Versuchsnummer", "TrialNumber", "Nr"], tr_cols) or "Versuchsnummer"
        tr_jetid   = resolve_field(["JetID", "Jet Id", "Jet"], tr_cols) or "JetID"
        tr_plate   = resolve_field(["Jet Plate Number", "JetPlate", "Jet Plate", "JetPlateNumber"], tr_cols) or "Jet Plate Number"
        tr_press   = resolve_field(["Air Pressure (bar)", "AirPressure", "Air Pressure"], tr_cols) or "Air Pressure (bar)"
        tr_housing = resolve_field(["HousingID"], tr_cols)
        tr_gid     = resolve_field(["GlobalID"], tr_cols)

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

        jetplate_is_numeric = self._col_is_numeric(trial_table, tr_plate)

        try:
            with get_connection() as cn:
                cn.autocommit = False
                cur = cn.cursor()

                # Letzter Trial der Serie für Lab-Klon
                cur.execute(
                    f"SELECT MAX([{tr_no}]) AS mx, MAX([ID]) AS lid "
                    f"FROM [{trial_table}] WHERE [{tr_sid}] = ?", [ts_id])
                row = cur.fetchone()
                trial_counter = int(row[0]) + 1 if row and row[0] is not None else 1
                last_trial_id = int(row[1]) if row and row[1] is not None else None

                new_trial_ids: List[int] = []

                for j in self._jets_data:
                    try:
                        plates_list = [p.strip() for p in str(j["PlateList"]).split(",") if p.strip()]
                    except Exception:
                        plates_list = []
                    if not plates_list:
                        try:
                            nn = int(j.get("Plates") or 0)
                        except Exception:
                            nn = 0
                        plates_list = [str(k+1) for k in range(max(0, nn))]

                    for plate in plates_list:
                        press_val   = self._to_float_or_none(j["Pressure"])
                        plate_value = self._to_int_or_none(plate) if jetplate_is_numeric else str(plate)
                        housing_id  = j.get("HousingID")

                        cols = [tr_sid, tr_no, tr_jetid, tr_plate, tr_press]
                        vals: List[Any] = [ts_id, trial_counter, int(j["JetID"]), plate_value, press_val]

                        if tr_housing and housing_id is not None:
                            cols.append(tr_housing)
                            vals.append(int(housing_id))
                        for col, val in machine_dynamic_cols_trial:
                            cols.append(col)
                            vals.append(val)
                        if tr_gid:
                            cols.append(tr_gid)
                            vals.append(new_global_id())

                        ph = ",".join(["?"] * len(cols))
                        sql = f"INSERT INTO {trial_table} ({','.join('['+c+']' for c in cols)}) VALUES ({ph})"
                        tid = self._insert_and_identity(cur, sql, vals)
                        new_trial_ids.append(tid)

                        # tblTrialSettings: pro Garn eine Zeile
                        if table_exists("tblTrialSettings") and self._materials_data:
                            ts_set_cols_map = get_columns_map("tblTrialSettings")
                            has_yuse = "yarnuseid" in ts_set_cols_map
                            has_spool = "spoolid" in ts_set_cols_map
                            for idx_m, m in enumerate(self._materials_data):
                                s_cols = ["TrialID", "YarnID", "Ply"]
                                s_vals: List[Any] = [tid, int(m["YarnID"]), m.get("Ply") or f"Ply {idx_m+1}"]
                                if has_yuse and m.get("YarnUseID") is not None:
                                    real_yuse = ts_set_cols_map.get("yarnuseid") or "YarnUseID"
                                    s_cols.append(real_yuse)
                                    s_vals.append(m["YarnUseID"])
                                if has_spool and m.get("SpoolID") is not None:
                                    real_spool = ts_set_cols_map.get("spoolid") or "SpoolID"
                                    s_cols.append(real_spool)
                                    s_vals.append(m["SpoolID"])
                                for s_col, s_val in machine_dynamic_cols_settings:
                                    real_s = ts_set_cols_map.get(s_col.lower()) or s_col
                                    s_cols.append(real_s)
                                    s_vals.append(s_val)
                                s_gid = resolve_field(["GlobalID"], ts_set_cols_map)
                                if s_gid:
                                    s_cols.append(s_gid)
                                    s_vals.append(new_global_id())
                                s_ph = ",".join(["?"] * len(s_cols))
                                cur.execute(
                                    f"INSERT INTO tblTrialSettings "
                                    f"({','.join('['+c+']' for c in s_cols)}) VALUES ({s_ph})",
                                    s_vals)

                        trial_counter += 1

                # Lab Machines -> FRISCH aus _lab_data schreiben (wie im
                # regulaeren Create-Flow in _on_save), NICHT vom letzten
                # Trial klonen. _clone_lab_rows() legt nur dann eine Zeile
                # an, wenn der LETZTE Trial der Serie bereits einen Eintrag
                # in genau dieser Tabelle hat - fehlt der (z.B. weil fuer
                # Statimat DS/Itemat Lab dort noch nichts gemessen wurde),
                # wird gar keine Zeile erzeugt. _lab_data wird beim Oeffnen
                # dieses Screens ueber _prefill_lab_from_series() anhand der
                # GANZEN Serie ermittelt und ist daher zuverlaessig.
                default_user_id = None
                if table_exists("tbluser"):
                    try:
                        urows = fetch_all("SELECT MIN([ID]) AS uid FROM tbluser")
                        if urows and urows[0].get("uid") is not None:
                            default_user_id = int(urows[0]["uid"])
                    except Exception:
                        default_user_id = None

                for lm in self._lab_data:
                    if str(lm.get("RowMode") or "").strip().lower() == "seriesfreeform":
                        # Jet Air Consumption & Co: keine Zeile pro Trial -
                        # wird unten einmal pro Series (physische Duese x Druck) angelegt.
                        continue
                    tbl = (lm.get("TableName") or "").strip()
                    if not tbl or not table_exists(tbl):
                        continue
                    lcols = get_columns_map(tbl)
                    col_trial = resolve_field(["TrialID"], lcols) or "TrialID"
                    add_src = (lm.get("AdditionalFieldSource") or "").strip()
                    add_real = resolve_field([add_src], lcols) if add_src else None
                    add_val = lm.get("AdditionalVal", None)
                    if isinstance(add_val, str):
                        add_val = self._to_float_or_none(add_val) or add_val
                    for tid in new_trial_ids:
                        if 'waterbath' in (tbl or '').lower():
                            insert_waterbath_rows(cur, tbl, col_trial, tid)
                            continue
                        # optionale GlobalID-Spalte im Labor-Table
                        col_gid = resolve_field(["GlobalID"], lcols)
                        cols_sql_parts = [f"[{col_trial}]"]
                        params: List[Any] = [tid]
                        if col_gid:
                            cols_sql_parts.append(f"[{col_gid}]")
                            params.append(new_global_id())
                        if add_real:
                            cols_sql_parts.append(f"[{add_real}]")
                            params.append(add_val)

                        # optionaler UserID (FK auf tbluser) - falls vorhanden, sauber setzen
                        col_user = resolve_field(["UserID", "User"], lcols)
                        if col_user:
                            if default_user_id is None:
                                # Ohne gueltigen User koennen wir diese Lab-Row nicht anlegen (sonst FK-Fehler)
                                continue
                            cols_sql_parts.append(f"[{col_user}]")
                            params.append(default_user_id)

                        placeholders = ",".join(["?"] * len(params))
                        cur.execute(
                            f"INSERT INTO {tbl} (" + ",".join(cols_sql_parts) +
                            ") VALUES (" + placeholders + ")",
                            params,
                        )

                self._save_jet_air_consumption_rows(cur, ts_id)
                cn.commit()

            if callable(self.on_open_experiment):
                num = exp_data[5]
                exp_label = (f"{exp_data[2]}-{str(exp_data[3])}{str(exp_data[4])}-"
                             f"{str(num).zfill(3) if str(num).isdigit() else num}")
                self.on_open_experiment(exp_id, ts_id, exp_label)
            else:
                QMessageBox.information(
                    self, "Gespeichert",
                    f"{len(new_trial_ids)} Trial(s) erfolgreich angelegt.")

        except Exception as e:
            try:
                cn.rollback()
            except Exception:
                pass
            QMessageBox.critical(self, "Fehler", f"Trials konnten nicht angelegt werden:\n{e}")


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
        table_candidates = ["tblExperimente", "tblExperiments"]
        table = next((t for t in table_candidates if table_exists(t)), None)
        if not table:
            return None
        cmap = get_columns_map(table)
        col_year = resolve_field(["Jahr", "Year"], cmap)
        col_pg = resolve_field(["Produktgruppe", "ProductGroup"], cmap)
        col_ot = resolve_field(["Bestellungstyp", "OrderType"], cmap)
        col_num = resolve_field(["Experimentnummer", "ExperimentNumber"], cmap)
        col_mac = resolve_field(["Maschine", "MachineID", "Machine"], cmap)
        col_gid = resolve_field(["GlobalID"], cmap)
        col_expreq = resolve_field(["ExperimentRequest", "Experiment Request", "RequestID", "ExperimentRequestID"], cmap)
        if not all([col_year, col_pg, col_ot, col_num]) or not col_mac:
            return None
        return table, {"year": col_year, "pg": col_pg, "ot": col_ot, "num": col_num, "machine": col_mac, "gid": col_gid, "expreq": col_expreq}

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
        resolved = self._resolve_experiments_table_and_columns()
        if not resolved:
            self.txtExperimentNumber.clear()
            self.strExperimentData[3] = ""
            QMessageBox.warning(self, "Experiment Number",
                                "Experimente‑Tabelle bzw. Spalten nicht gefunden.")
            return
        table, cols = resolved
        try:
            rows = fetch_all(
                f"""
                SELECT [{cols['num']}] AS Num
                FROM {table}
                WHERE [{cols['year']}] = ? AND [{cols['pg']}] = ? AND [{cols['ot']}] = ?
                """,
                [year, pg, ot],
            )
            max_num = 0
            for r in rows:
                val = r.get("Num")
                if val is None or val == "":
                    continue
                try:
                    n = int(str(val).strip())
                except Exception:
                    continue
                if n > max_num:
                    max_num = n
            next_txt = f"{(max_num + 1):03d}"
            self.txtExperimentNumber.setText(next_txt)
            self.strExperimentData[3] = next_txt
        except Exception as e:
            self.txtExperimentNumber.clear()
            self.strExperimentData[3] = ""
            QMessageBox.warning(self, "Experiment Number",
                                f"Fehler beim Lesen aus {table}:\n{e}")

    def _resolve_next_free_experiment_number(self, cur, exp_table: str, cols: dict,
                                              year: str, pg, ot, preferred_no_txt: str) -> str:
        """Gibt die kleinste freie Experimentnummer >= preferred_no_txt zurück.
        Wird in _on_save verwendet, um Race-Conditions bei gleichzeitigem Anlegen zu vermeiden."""
        try:
            cur.execute(
                f"SELECT [{cols['num']}] FROM {exp_table} "
                f"WHERE [{cols['year']}] = ? AND [{cols['pg']}] = ? AND [{cols['ot']}] = ?",
                [year, pg, ot],
            )
            taken = set()
            for row in cur.fetchall():
                try:
                    taken.add(int(str(row[0]).strip()))
                except Exception:
                    pass
            candidate = int(preferred_no_txt)
            while candidate in taken:
                candidate += 1
            return f"{candidate:03d}"
        except Exception:
            return preferred_no_txt

    # -->-->-->- Material -->-->-->-
    def _on_material_changed(self):
        self._check_material()
        self._check_safe()

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
        # Ply-Labels in _materials_data und Tabelle neu vergeben
        for i in range(len(self._materials_data)):
            self._materials_data[i]["Ply"] = f"Ply {i + 1}"
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
        # Konsistenzprüfung gegen bestehende Series (addtrials / addlabmachines)
        # Hinweis: _series_pk/_edit_series_pk gibt es in dieser Klasse nicht -
        # die aktuell gewaehlte Serie steht in cmbExistingSeries.
        series_pk: Optional[int] = None
        if self.mode in ("addtrials", "addlabmachines") and hasattr(self, "cmbExistingSeries"):
            try:
                data = self.cmbExistingSeries.currentData()
                if data is not None:
                    series_pk = int(data)
            except Exception:
                series_pk = None

        # Falls dieses Garn in der Series bereits einer bestimmten Ply-Nummer
        # zugeordnet ist (z.B. "Ply 1" bei den bestehenden Trials), soll ein
        # neuer Trial mit demselben Garn dieselbe Ply-Nummer bekommen –
        # statt (wie bisher) immer per _ply_offset auf die naechste freie
        # Nummer verschoben zu werden.
        existing_ply_for_yarn: Optional[str] = None
        if series_pk:
            try:
                ply_rows = fetch_all(
                    """
                    SELECT DISTINCT ts.Ply
                    FROM tblTrialSettings ts
                    JOIN tblTrial t ON t.ID = ts.TrialID
                    WHERE t.TrialSeriesID = ? AND ts.YarnID = ?
                    """,
                    [series_pk, yarn_id],
                )
                plys = {r["Ply"] for r in ply_rows if r.get("Ply")}
                if len(plys) == 1:
                    existing_ply_for_yarn = next(iter(plys))
            except Exception:
                existing_ply_for_yarn = None

        # Gleiches Prinzip fuer den gerade in Bearbeitung befindlichen (noch
        # nicht gespeicherten) Trial selbst: wird dasselbe Garn ein zweites
        # Mal ueber einen separaten "Add"-Klick hinzugefuegt (statt ueber
        # n_ends unten in einem Rutsch), soll es dieselbe Ply-Nummer bekommen
        # statt eine neue - sonst haette z.B. TrialSeries 385 Garn A viermal
        # als Ply 1/2/3/4 im selben Trial bekommen (2026-08-20, Nutzer-Bugreport
        # + Feature-Wunsch: "dasselbe Garn im selben Versuch = dieselbe Ply").
        if existing_ply_for_yarn is None:
            for m in self._materials_data:
                if int(m.get("YarnID") or -1) == int(yarn_id):
                    existing_ply_for_yarn = m.get("Ply")
                    break

        ply_offset = getattr(self, "_ply_offset", 0)
        # Gleiche Formel wie beim spaeteren Speichern (Zeile mit ply_offset weiter
        # unten) – Pruefung und gespeicherter Wert muessen konsistent sein.
        ply_label = existing_ply_for_yarn or f"Ply {ply_offset + self.tblYarns.rowCount() + 1}"

        if series_pk:
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
                [series_pk, ply_label, yarn_id],
            )
            if conflict_rows:
                existing = ", ".join(r["YarnName"] for r in conflict_rows)
                QMessageBox.critical(
                    self, "Yarn Conflict",
                    f"Cannot add this yarn to {ply_label}.\n\n"
                    f"This ply already has a different yarn in this series:\n"
                    f"  {existing}\n\n"
                    f"All trials in a series must use the same yarn per ply."
                )
                return

        # Konsistenzprüfung gegen bereits hinzugefügte Plies in _materials_data
        for m in self._materials_data:
            if m.get("Ply") == ply_label and int(m["YarnID"]) != int(yarn_id):
                QMessageBox.critical(
                    self, "Yarn Conflict",
                    f"{ply_label} is already assigned to a different yarn:\n"
                    f"  {m['Name']}\n\n"
                    f"All trials in a series must use the same yarn per ply."
                )
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
            self.tblYarns.setItem(rr, 0, QTableWidgetItem(yarn_name))
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
            QMessageBox.critical(self, "Trial Ply", f"Could not create yarn entry for this trial:\n{e}")
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

        table = "tblMachineFields"
        if not table_exists(table):
            QMessageBox.warning(
                self, "Machine", "Tabelle 'tblMachineFields' nicht gefunden.")
            self._check_machine()
            self._check_safe()
            return

        cmap = get_columns_map(table)
        col_mid = resolve_field(
            ["MachineID", "MaschineID"], cmap) or "MachineID"
        col_fno = resolve_field(["FieldNumber"], cmap) or "FieldNumber"
        col_row = resolve_field(["Row", "Zeile"], cmap) or "Row"
        col_col = resolve_field(["Column", "Spalte"], cmap) or "Column"
        col_group = resolve_field(["Group", "Gruppe"], cmap) or "Group"
        col_name = resolve_field(["FieldName", "Caption"], cmap) or "FieldName"
        col_func = resolve_field(
            ["FieldFunction", "Function"], cmap) or "FieldFunction"
        col_orig = resolve_field(
            ["OriginalName", "Original", "OriginalFieldName"], cmap) or "FieldName"
        col_storage = resolve_field(["StorageTable"], cmap)  # kann NULL sein → default 'tbltrial'

        rows = fetch_all(
            f"""
            SELECT [{col_fno}]   AS FNo,
                   [{col_row}]   AS R,
                   [{col_col}]   AS C,
                   [{col_group}] AS G,
                   [{col_name}]  AS Caption,
                   [{col_func}]  AS Fnc,
                   [{col_orig}]  AS Orig
                   {f', [{col_storage}] AS StorTbl' if col_storage else ', NULL AS StorTbl'}
            FROM {table}
            WHERE [{col_mid}] = ?
              AND COALESCE(RDSetting, 0) = 0
            ORDER BY [{col_fno}]
            """,
            [machine_id],
        )

        if not rows:
            self._check_machine()
            self._check_safe()
            return

        group_to_minrow: Dict[Any, int] = {}
        for r in rows:
            g = r["G"]
            if g not in group_to_minrow:
                group_to_minrow[g] = int(r["R"] or 0)
            else:
                group_to_minrow[g] = min(group_to_minrow[g], int(r["R"] or 0))
        groups_sorted = sorted(group_to_minrow.items(), key=lambda kv: kv[1])
        group_start_rows = [gr for gr, _ in groups_sorted]

        def _offset_for_row(base_row: int) -> int:
            cnt = 0
            for gr in group_start_rows:
                if group_to_minrow[gr] < base_row:
                    cnt += 1
            return cnt

        for r in rows:
            r0 = int(r["R"] or 0)
            c0 = int(r["C"] or 0)
            fno = int(r["FNo"] or 0)
            caption = str(r["Caption"] or "")
            fnc = (r["Fnc"] or "").strip()
            orig = (r["Orig"] or "").strip() or caption
            storage = str(r.get("StorTbl") or "tbltrial").strip().lower()
            if storage not in ("tbltrial", "tbltrialsettings"):
                storage = "tbltrial"

            # hidden-Felder komplett überspringen
            if fnc.lower() == "hidden":
                continue

            if r0 == group_to_minrow[r["G"]]:
                if group_start_rows.index(r["G"]) > 0:
                    spacer = QSpacerItem(
                        0, 16, QSizePolicy.Minimum, QSizePolicy.Fixed)
                    self.machine_grid.addItem(
                        spacer, r0 - 1 + _offset_for_row(r0), 0, 1, 6)

            row_idx = r0 + _offset_for_row(r0)
            col_idx = max(0, c0) * 2

            lab = QLabel(caption)

            # dropdown:tblXxx → QComboBox statt QLineEdit
            if fnc.lower().startswith("dropdown:"):
                lookup_table = fnc[len("dropdown:"):].strip()
                widget = QComboBox()
                widget.setInsertPolicy(QComboBox.NoInsert)
                widget.addItem("", None)   # leerer Eintrag (kein Wert)
                try:
                    lk_cmap = get_columns_map(lookup_table)
                    lk_id = resolve_field(["ID"], lk_cmap) or "ID"
                    # Anzeige-Spalte: DiscName, Name, Bezeichnung o.ä.
                    lk_name = resolve_field(
                        ["DiscName", "Name", "Bezeichnung", "Caption"], lk_cmap)
                    if lk_name:
                        lk_rows = fetch_all(
                            f"SELECT [{lk_id}] AS LID, [{lk_name}] AS LName "
                            f"FROM {lookup_table} ORDER BY [{lk_name}] ASC"
                        )
                        for lk in lk_rows:
                            widget.addItem(str(lk.get("LName") or ""), lk.get("LID"))
                except Exception:
                    pass
                self.machine_grid.addWidget(lab,    row_idx, col_idx)
                self.machine_grid.addWidget(widget, row_idx, col_idx + 1)
                self._machine_field_widgets.append((lab, widget, fno, orig, storage))
                continue

            edit = QLineEdit()

            if fnc.lower() == "onlyinteger":
                edit.setValidator(QIntValidator(-10**9, 10**9, self))
            elif fnc.lower() == "onlydoubles":
                regex = QRegularExpression(r"^\s*[+-]?\d+(?:[.,]\d{1,3})?\s*$")
                edit.setValidator(QRegularExpressionValidator(regex, self))
            elif fnc.lower().replace(" ", "") in ("onlysz", "onlys,z", "onlys z", "only s z"):
                regex = QRegularExpression(
                    r"^\s*(S|Z|SZ)\s*$", QRegularExpression.CaseInsensitiveOption)
                edit.setValidator(QRegularExpressionValidator(regex, self))

                def _up(_=None, e=edit):
                    e.blockSignals(True)
                    e.setText(e.text().upper())
                    e.blockSignals(False)
                edit.textChanged.connect(_up)

            self.machine_grid.addWidget(lab,  row_idx, col_idx)
            self.machine_grid.addWidget(edit, row_idx, col_idx + 1)

            self._machine_field_widgets.append((lab, edit, fno, orig, storage))

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
            if cb.isVisible() and cb.isChecked():
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

    def _norm_add_val(self, v):
        """Normalisiere AdditionalValue für Vergleiche (Float auf 3 Nachkommastellen)."""
        if v is None or v == "":
            return None
        try:
            return round(float(str(v).replace(",", ".")), 3)
        except Exception:
            return str(v).strip()

    def _entry_matches(self, row: dict, lm_id: int, add_val_norm):
        if int(row.get("LMID")) != int(lm_id):
            return False
        # vorhandenen Wert robust ermitteln
        existing = row.get("AdditionalVal", None)
        if existing is None:
            disp = (row.get("AdditionalDisp") or "").split(" ")[0]
            existing = self._norm_add_val(disp)
        else:
            existing = self._norm_add_val(existing)

        # Maschinen ohne AdditionalField -> add_val_norm == None macht sie eindeutig
        return existing == add_val_norm

    def _lab_entry_exists(self, lm_id: int, add_val_norm):
        """True, wenn Kombination (LMID, AdditionalVal_norm) bereits existiert.
        Für Maschinen ohne AdditionalField ist add_val_norm=None."""
        for r in self._lab_data:
            if self._entry_matches(r, lm_id, add_val_norm):
                return True
        return False

    def _addlabmachines_value_needed(self, table: str, add_src: str, value: float) -> bool:
        """In addlabmachines mode: True if at least one currently checked
        trial does not yet have this (table, value) combination in the DB.
        Used to suppress the automatic Itemat 0.0-baseline from the pending
        list when every checked trial already has it - _lab_entry_exists()
        alone can't see that, it only knows about entries added in this UI
        session, not what's already saved for the selected (existing)
        trials. In create/addtrials mode trials don't exist yet, so this
        is always True there (nothing to check against)."""
        if self.mode != "addlabmachines" or not table or not table_exists(table):
            return True
        trial_ids = self._get_checked_trial_ids()
        if not trial_ids:
            return True
        try:
            lcols = get_columns_map(table)
            col_trial = resolve_field(["TrialID"], lcols) or "TrialID"
            add_real = resolve_field([add_src], lcols) if add_src else None
            placeholders = ",".join(["?"] * len(trial_ids))
            if add_real:
                rows = fetch_all(
                    f"SELECT DISTINCT [{col_trial}] AS TrialID FROM [{table}] "
                    f"WHERE [{col_trial}] IN ({placeholders}) AND [{add_real}] = ?",
                    trial_ids + [value],
                )
            else:
                rows = fetch_all(
                    f"SELECT DISTINCT [{col_trial}] AS TrialID FROM [{table}] "
                    f"WHERE [{col_trial}] IN ({placeholders})",
                    trial_ids,
                )
            have = {int(r["TrialID"]) for r in rows}
            return any(tid not in have for tid in trial_ids)
        except Exception:
            return True

    def _is_itemat(self, meta: dict, fallback_name: str = "") -> bool:
        """
        Erkenne Itemat-Maschinen robust (DB-Name kann 'Itemat Lab', 'ITEMATLAB', etc. sein).
        """
        name = str(meta.get("LMName") or fallback_name or "").strip(
        ).lower().replace(" ", "")
        # exakte matches + robuste startswith/endswith
        if name in ("itematlab", "itematplus"):
            return True
        return name.startswith("itemat") and (name.endswith("lab") or name.endswith("plus"))

    def _is_series_freeform(self, meta: dict) -> bool:
        """
        Erkennt Lab Machines mit RowMode='SeriesFreeform' (z.B. Jet Air Consumption):
        diese bekommen KEINE automatische 1-Zeile-pro-Trial-Erzeugung, sondern eine
        eigene Kreuzprodukt-Logik (physische Duese x Druck), einmal pro Series.
        """
        return str(meta.get("RowMode") or "").strip().lower() == "seriesfreeform"

    def _add_lab_machine(self):
        # Button-Guard
        if not self.butAddLabMachine.isEnabled():
            return

        # Ausgewählte Maschine & Metadaten
        lm_name = self.cmbLabMachine.currentText().strip()
        lm_id = int(self.cmbLabMachine.currentData())
        meta = self._lab_machines.get(lm_id) or {}

        # leer => kein Additional Field
        caption = (meta.get("AddField") or "").strip()
        unit = (meta.get("AddUnit") or "").strip()
        table = (meta.get("Tbl") or "").strip()
        src = (meta.get("Src") or "").strip()

        needs_additional = bool(caption)
        is_itemat = self._is_itemat(meta, self.cmbLabMachine.currentText())
        is_series_freeform = self._is_series_freeform(meta)

        # ── SeriesFreeform (z.B. Jet Air Consumption): kommagetrennte Liste
        # von Werten (z.B. Druckstufen) statt einem Einzelwert. Diese Werte
        # werden NICHT pro Trial dupliziert, sondern beim Speichern einmal
        # pro Series mit den physischen Duesen (JetID+JetPlate) gekreuzt.
        if is_series_freeform and needs_additional:
            raw = self.txtAdditional.text().strip()
            if raw == "":
                QMessageBox.information(
                    self, "Lab Machine",
                    f"Bitte eine oder mehrere {caption}-Werte angeben (kommagetrennt, z.B. 4, 5, 6).")
                return
            parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip() != ""]
            vals: List[float] = []
            bad: List[str] = []
            for p in parts:
                try:
                    vals.append(float(p.replace(",", ".")))
                except Exception:
                    bad.append(p)
            if bad:
                QMessageBox.warning(
                    self, "Lab Machine",
                    f"Ungültige Werte: {', '.join(bad)}. Bitte nur Zahlen, kommagetrennt.")
                return
            if not vals:
                return

            added_any = False
            for val in vals:
                norm = self._norm_add_val(val)
                if self._lab_entry_exists(lm_id, norm):
                    continue
                disp = f"{val:g}" + ((" " + unit) if unit else "")
                rr = self.tblLabMachines.rowCount()
                self.tblLabMachines.insertRow(rr)
                self.tblLabMachines.setItem(rr, 0, QTableWidgetItem(lm_name))
                self.tblLabMachines.setItem(rr, 1, QTableWidgetItem(disp))
                self._lab_data.append({
                    "LMID": lm_id, "Name": lm_name,
                    "AdditionalDisp": disp, "AdditionalVal": val,
                    "TableName": table, "AdditionalFieldSource": src,
                    "Unit": unit, "RowMode": "SeriesFreeform",
                })
                added_any = True

            if added_any:
                self.txtAdditional.clear()
                self._update_add_lab_enabled()
                self._check_lab()
                self._check_safe()
                self._update_lab_state_addlabmachines()
            return

        # In addtrials: Itemat-Maschinen immer nur 0.0 einfügen (kein manueller Wert)
        if self.mode == "addtrials" and is_itemat and needs_additional:
            baseline_norm = self._norm_add_val(0.0)
            if self._lab_entry_exists(lm_id, baseline_norm):
                return  # bereits vorhanden
            rr = self.tblLabMachines.rowCount()
            self.tblLabMachines.insertRow(rr)
            disp0 = "0.0" + ((" " + unit) if unit else "")
            self.tblLabMachines.setItem(rr, 0, QTableWidgetItem(lm_name))
            self.tblLabMachines.setItem(rr, 1, QTableWidgetItem(disp0))
            self._lab_data.append({
                "LMID": lm_id, "Name": lm_name,
                "AdditionalDisp": disp0, "AdditionalVal": 0.0,
                "TableName": table, "AdditionalFieldSource": src,
                "Unit": unit,
            })
            self._update_add_lab_enabled()
            self._check_lab()
            self._check_safe()
            return

        # Itemat in allen anderen Modi: Checkboxen + optionales Textfeld
        if is_itemat and needs_additional and any(
                cb.isVisible() for cb in getattr(self, "_tension_checkboxes", [])):
            checked_vals = self._get_checked_tensions()

            # Allfälligen manuellen Wert aus txtAdditional dazunehmen
            manual_val = None
            raw_txt = self.txtAdditional.text().strip() if self.txtAdditional.isVisible() else ""
            if raw_txt and self.txtAdditional.hasAcceptableInput():
                try:
                    manual_val = float(raw_txt.replace(",", "."))
                except Exception:
                    pass

            if not checked_vals and manual_val is None:
                return

            # Alle Werte die eingefügt werden sollen: 0.0 immer + angehakte + manuell
            # (0.0-Baseline nur, falls noch nicht in der Pending-Liste UND
            # noch nicht für mindestens einen der angehakten Trials in der DB)
            vals_to_insert: List[float] = []
            baseline_norm = self._norm_add_val(0.0)
            if not self._lab_entry_exists(lm_id, baseline_norm) and \
                    self._addlabmachines_value_needed(table, src, 0.0):
                vals_to_insert.append(0.0)
            for tv in checked_vals:
                if not self._lab_entry_exists(lm_id, self._norm_add_val(tv)):
                    vals_to_insert.append(tv)
            if manual_val is not None and not self._lab_entry_exists(lm_id, self._norm_add_val(manual_val)):
                vals_to_insert.append(manual_val)

            for val in vals_to_insert:
                disp = f"{val:.1f}" + ((" " + unit) if unit else "")
                rr = self.tblLabMachines.rowCount()
                self.tblLabMachines.insertRow(rr)
                self.tblLabMachines.setItem(rr, 0, QTableWidgetItem(lm_name))
                self.tblLabMachines.setItem(rr, 1, QTableWidgetItem(disp))
                self._lab_data.append({
                    "LMID": lm_id, "Name": lm_name,
                    "AdditionalDisp": disp, "AdditionalVal": val,
                    "TableName": table, "AdditionalFieldSource": src,
                    "Unit": unit,
                })

            # Checkboxen zurücksetzen, Textfeld leeren
            self._set_tension_checkboxes_visible(True, uncheck=True)
            self.txtAdditional.clear()
            self._update_add_lab_enabled()
            self._check_lab()
            self._check_safe()
            self._update_lab_state_addlabmachines()
            return

        # -->- 1) Wert lesen/normalisieren
        add_disp = ""
        add_val = None
        add_norm = None

        if needs_additional:
            raw = self.txtAdditional.text().strip()
            if raw == "":
                # Safety (Button sollte eigentlich disabled sein)
                QMessageBox.information(
                    self, "Lab Machine", "Bitte Additional-Wert angeben.")
                return
            try:
                add_val = float(raw.replace(",", "."))
                add_norm = self._norm_add_val(add_val)
                add_disp = f"{add_val:.2f}".rstrip("0").rstrip(".")
            except Exception:
                add_val = None
                add_norm = self._norm_add_val(raw)
                add_disp = raw
        else:
            # Maschinen ohne Additional Field: nur einmal erlauben
            add_norm = None
            add_disp = ""

        # -->- 2) Duplikate verhindern
        if self._lab_entry_exists(lm_id, add_norm):
            # duplicate suppressed for add stage
            return

        # -->- 3) (NEU) Pflicht-Baseline 0.0 VOR dem eigentlichen Wert einfügen
        # Nur wenn Maschine ein Additional Field hat und Itemat-Variante ist.
        if needs_additional and is_itemat:
            baseline_norm = self._norm_add_val(0.0)
            if not self._lab_entry_exists(lm_id, baseline_norm) and \
                    self._addlabmachines_value_needed(table, src, 0.0):
                # Insert baseline row first
                rr = self.tblLabMachines.rowCount()
                self.tblLabMachines.insertRow(rr)
                disp0 = "0.0" + ((" " + unit) if unit else "")
                self.tblLabMachines.setItem(rr, 0, QTableWidgetItem(lm_name))
                self.tblLabMachines.setItem(rr, 1, QTableWidgetItem(disp0))
                self._lab_data.append({
                    "LMID": lm_id, "Name": lm_name,
                    "AdditionalDisp": disp0, "AdditionalVal": 0.0,
                    "TableName": table, "AdditionalFieldSource": src,
                    "Unit": unit,
                })
            # Wenn der Nutzer selbst 0 / 0.0 eingegeben hat, war das die Baseline —
            # keinen zweiten Eintrag anlegen.
            if add_norm == self._norm_add_val(0.0):
                if needs_additional:
                    self.txtAdditional.clear()
                self._update_add_lab_enabled()
                self._check_lab()
                self._check_safe()
                self._update_lab_state_addlabmachines()
                return

        # -->- 4) Eigentlichen (vom Nutzer gewählten) Eintrag hinzufügen
        r = self.tblLabMachines.rowCount()
        self.tblLabMachines.insertRow(r)
        disp = add_disp + ((" " + unit) if unit and add_disp else "")
        self.tblLabMachines.setItem(r, 0, QTableWidgetItem(lm_name))
        self.tblLabMachines.setItem(r, 1, QTableWidgetItem(disp))

        self._lab_data.append({
            "LMID": lm_id,
            "Name": lm_name,
            "AdditionalDisp": disp,
            "AdditionalVal": add_val,
            "TableName": table,
            "AdditionalFieldSource": src,
            "Unit": unit,
        })

        # Eingabefelder zurücksetzen
        if needs_additional:
            self.txtAdditional.clear()
        else:
            self._set_additional_visible(False, clear=True)

        self._update_add_lab_enabled()
        self._check_lab()
        self._check_safe()
        self._update_lab_state_addlabmachines()

    def _delete_lab_row(self, row: int):
        """Delete a lab-machine row.
        For Itemat machines (Itemat Lab / Itemat Plus),
        the 0.0 cN/dtex variant may only be deleted if no
        other variants of this machine exist for that series.
        """
        if not (0 <= row < len(self._lab_data)):
            # inkonsistenter Zustand -> nichts tun, aber Deletion nicht blockieren
            return True

        entry = self._lab_data[row]
        lm_id = entry.get("LMID")
        name = entry.get("Name", "")

        # Meta holen und prüfen, ob es eine Itemat‑Maschine ist
        meta = self._lab_machines.get(lm_id) or {}
        is_itemat = self._is_itemat(meta, name)

        # Prüfen, ob es sich um die 0.0‑Baseline handelt
        add_val = entry.get("AdditionalVal", None)
        is_baseline_zero = False
        try:
            if add_val is not None:
                is_baseline_zero = (self._norm_add_val(add_val) ==
                                    self._norm_add_val(0.0))
        except Exception:
            is_baseline_zero = False

        # Falls Itemat & 0.0‑Variante: nur löschen, wenn keine weiteren Varianten existieren
        if is_itemat and is_baseline_zero:
            has_other_variants = any(
                (i != row) and (d.get("LMID") == lm_id)
                for i, d in enumerate(self._lab_data)
            )
            if has_other_variants:
                QMessageBox.information(
                    self,
                    "0.0 variant cannot be deleted",
                    (
                        "The 0.0 cN/dtex variant of Itemat machines can only be deleted "
                        "when all other variants of this machine for this "
                        "Serie entfernt wurden.\n\n"
                        "Please delete the other variants first "
                        "(z. B. 0.3, 0.6 usw.)."
                    ),
                )
                # False signalisiert dem ReadOnlyTable, dass die Zeile NICHT entfernt werden soll
                return False

        # Normaler Löschpfad (oder Itemat-Baseline ohne weitere Varianten)
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

    def _insert_and_identity(self, cur, sql: str, params: list | tuple) -> int:
        cur.execute(sql, params)
        cur.execute("SELECT @@IDENTITY")
        rid = cur.fetchone()[0]
        try:
            return int(rid)
        except Exception:
            return int(float(rid))

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

    def _col_is_numeric(self, table: str, real_col: str) -> bool:
        info = get_columns_info(table)
        for i in info:
            if i["real"].lower() == real_col.lower():
                dt = i.get("data_type")
                tn = (i.get("type_name") or "").upper()
                if dt in (2, 3, 4, 5, 6, 7) or any(x in tn for x in
                                                   ["BYTE", "SHORT", "LONG", "INT", "INTEGER", "SINGLE", "DOUBLE", "NUMERIC", "DECIMAL"]):
                    return True
        return False

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

        # --> 1) Tabellen & Spalten auflösen -->
        exp_res = self._resolve_experiments_table_and_columns()
        if not exp_res:
            QMessageBox.critical(
                self, "Save", "Experimente‑Tabelle nicht gefunden/inkomplett.")
            return
        exp_table, exp_cols = exp_res

        ts_table = "tblTrialSeries"
        if not table_exists(ts_table):
            QMessageBox.critical(
                self, "Save", "Tabelle 'tblTrialSeries' nicht gefunden.")
            return
        ts_cols = get_columns_map(ts_table)
        ts_exp = resolve_field(
            ["ExperimentID", "Experiment Id"], ts_cols) or "ExperimentID"
        ts_name = resolve_field(["SeriesName", "Name"],
                                ts_cols) or "SeriesName"

        trial_table = "tblTrial"
        if not table_exists(trial_table):
            QMessageBox.critical(
                self, "Save", "Tabelle 'tblTrial' nicht gefunden.")
            return
        tr_cols = get_columns_map(trial_table)
        tr_sid = resolve_field(
            ["TrialSeriesID", "SerieID", "SeriesID"], tr_cols) or "TrialSeriesID"
        tr_no = resolve_field(
            ["Versuchsnummer", "TrialNumber", "Nr"], tr_cols) or "Versuchsnummer"
        tr_jetid = resolve_field(
            ["JetID", "Jet Id", "Jet"], tr_cols) or "JetID"
        tr_plate = resolve_field(
            ["Jet Plate Number", "JetPlate", "Jet Plate", "JetPlateNumber"], tr_cols) or "Jet Plate Number"
        tr_press = resolve_field(
            ["Air Pressure (bar)", "AirPressure", "Air Pressure"], tr_cols) or "Air Pressure (bar)"
        tr_housing = resolve_field(["HousingID"], tr_cols)

        # dynamische Maschinenfelder – aufgeteilt nach StorageTable
        machine_dynamic_cols_trial: List[Tuple[str, Any]] = []        # → tblTrial
        machine_dynamic_cols_settings: List[Tuple[str, Any]] = []     # → tblTrialSettings
        ts_cols_map: Dict[str, str] = get_columns_map("tblTrialSettings") \
            if table_exists("tblTrialSettings") else {}
        for lab, widget, fno, orig, storage in self._machine_field_widgets:
            # Wert auslesen — QComboBox liefert ID via currentData(), QLineEdit via text()
            if isinstance(widget, QComboBox):
                val = widget.currentData()
                if val is None:
                    continue
            else:
                txt = widget.text().strip()
                if txt == "":
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

        from datetime import datetime
        year_txt = self.strExperimentData[0] or str(datetime.now().year)
        machine_id = self._to_int_or_none(self.cmbMachine.currentData()) or 0
        series_name = self.txtSeriesName.text().strip()
        selected_request_id = None
        try:
            if self.mode == "create" and self.cmbExperimentRequest.currentIndex() >= 0:
                selected_request_id = self._to_int_or_none(self.cmbExperimentRequest.currentData())
        except Exception:
            selected_request_id = None

        # "create-like" modes create a new Experiment + TrialSeries (+ Trials)
        is_create_like = self.mode in ("create", "legacy")

        try:
            with get_connection() as cn:
                cn.autocommit = False
                cur = cn.cursor()

                if self.mode == "addseries":
                    if self.cmbExistingExperiment.currentIndex() < 0:
                        raise Exception("No existing experiment selected.")
                    exp_id = int(self.cmbExistingExperiment.currentData()[0])
                elif self.mode == "addtrials":
                    if self.cmbExistingExperiment.currentIndex() < 0 or self.cmbExistingSeries.currentIndex() < 0:
                        raise Exception("Please select experiment and series.")
                    exp_id = int(self.cmbExistingExperiment.currentData()[0])
                    ts_id = int(self.cmbExistingSeries.currentData())
                else:
                    pg_id = self._to_int_or_none(
                        self.cmbProductGroup.currentData()) or 0
                    ot_id = self._to_int_or_none(
                        self.cmbOrderType.currentData()) or 0
                    exp_gid_col = exp_cols.get('gid')
                    exp_req_col = exp_cols.get('expreq')

                    if self.mode == "legacy":
                        manual = self.txtExperimentNumber.text().strip()
                        parsed = self._parse_legacy_experiment_id(manual)
                        if not parsed:
                            QMessageBox.warning(self, "Experiment Number",
                                                "Invalid experiment ID. Expected: YYYY-<PGOT>-NNN (e.g. 2019-73-002)")
                            raise Exception("Invalid legacy experiment id")
                        year_txt, pg_id, ot_id, exp_no_txt = parsed
                        exp_id_text = f"{year_txt}-{pg_id}{ot_id}-{exp_no_txt}"
                    else:
                        exp_no_txt = self.txtExperimentNumber.text().strip()
                        # Race-Condition-Schutz: nochmal prüfen ob Nummer noch frei ist
                        exp_no_txt = self._resolve_next_free_experiment_number(
                            cur, exp_table, exp_cols, year_txt, pg_id, ot_id, exp_no_txt)
                        # Experiment ID zusammensetzen: Jahr-PGOT-NNN (z. B. 2025-70-006)
                        exp_id_text = f"{year_txt}-{pg_id}{ot_id}-{exp_no_txt}"

                    exp_fields = [exp_cols['year'], exp_cols['pg'], exp_cols['ot'], exp_cols['num'], 'Experiment ID']
                    exp_values = [year_txt, pg_id, ot_id, exp_no_txt, exp_id_text]

                    if exp_req_col and selected_request_id is not None:
                        exp_fields.append(exp_req_col)
                        exp_values.append(int(selected_request_id))

                    if exp_gid_col:
                        exp_fields.append(exp_gid_col)
                        exp_values.append(new_global_id())

                    fields_sql = ",".join(f"[{f}]" if f != 'Experiment ID' else "[Experiment ID]" for f in exp_fields)
                    qmarks = ",".join(["?"] * len(exp_values))
                    exp_sql = f"INSERT INTO {exp_table} ({fields_sql}) VALUES ({qmarks})"
                    exp_params = exp_values

                    exp_id = self._insert_and_identity(cur, exp_sql, exp_params)

                # Falls ein Experiment Request verknuepft wurde: Status auf 4 setzen
                if is_create_like and selected_request_id is not None:
                    self._set_experiment_request_status(cur, int(selected_request_id), 4)

                if self.mode in ("create", "legacy", "addseries"):
                    # CreationDate & CreatedBy automatisch setzen, falls Spalten existieren
                    ts_cdate = resolve_field(
                        ["CreationDate", "Created", "Creation Date",
                            "Creation_Date"], ts_cols
                    )
                    ts_createdby = resolve_field(
                        ["CreatedBy", "Created By", "Created_By", "CreatedByID",
                            "CreatedUserID", "CreatedUser"], ts_cols
                    )
                    # Backlog-Spalten (optional)
                    ts_backlog_status = resolve_field(
                        ["BacklogStatusID", "BacklogStatus"], ts_cols
                    )
                    ts_backlog_prio = resolve_field(
                        ["BacklogPrio", "BacklogPriority", "Priority"], ts_cols
                    )
                    ts_backlog_owner = resolve_field(
                        ["BacklogOwner", "OwnerUserID", "Owner"], ts_cols
                    )

                    # Werte vorbereiten
                    fields = [ts_exp, ts_name]
                    # Serienname automatisch nummerieren: '01 <Name>' basierend auf Anzahl
                    # vorhandener TrialSeries im Experiment (erste Serie => 01).
                    series_name_db = series_name
                    try:
                        base_name = re.sub(
                            r'^\s*\d{2}\s+', '', series_name or '').strip()
                        cur.execute(
                            f"SELECT COUNT(*) FROM {ts_table} WHERE [{ts_exp}] = ?",
                            [exp_id],
                        )
                        row = cur.fetchone()
                        cnt_int = int(
                            row[0]) if row and row[0] is not None else 0
                        series_name_db = (
                            f"{cnt_int+1:02d} {base_name}".strip()
                            if base_name
                            else f"{cnt_int+1:02d}"
                        )
                    except Exception:
                        series_name_db = series_name
                    values = [exp_id, series_name_db]
                    # optionale GlobalID-Spalte
                    ts_gid = resolve_field(["GlobalID"], ts_cols)
                    if ts_gid:
                        fields.append(ts_gid)
                        values.append(new_global_id())

                    if ts_cdate:
                        fields.append(ts_cdate)
                        values.append(datetime.now())

                    # Werte aus Backlog-UI holen
                    backlog_status_id = None
                    try:
                        backlog_status_id = self._to_int_or_none(
                            self.cmbBacklogStatus.currentData()
                        )
                    except Exception:
                        backlog_status_id = None

                    # Joker-Maschine erzwingt BacklogStatusID = 1 ("Backlog"),
                    # unabhängig davon, was im General-Tab ausgewählt ist.
                    try:
                        if getattr(self, "_joker_machine_selected", False):
                            backlog_status_id = 1
                    except Exception:
                        # Fallback: nichts tun, wenn Flag aus irgendeinem Grund fehlt
                        pass

                    backlog_prio_val = None
                    try:
                        prio_txt = self.cmbBacklogPrio.currentText().strip()
                        if prio_txt:
                            backlog_prio_val = self._to_int_or_none(prio_txt)
                    except Exception:
                        backlog_prio_val = None

                    # User-ID aus app_meta.current_user (für CreatedBy / BacklogOwner)
                    try:
                        user_id = app_meta.current_user.get("id")
                    except Exception:
                        user_id = None

                    if ts_backlog_status and backlog_status_id is not None:
                        fields.append(ts_backlog_status)
                        values.append(int(backlog_status_id))

                    if ts_backlog_prio and backlog_prio_val is not None:
                        fields.append(ts_backlog_prio)
                        values.append(backlog_prio_val)

                    if ts_backlog_owner and user_id is not None:
                        fields.append(ts_backlog_owner)
                        values.append(int(user_id))

                    if ts_createdby and user_id is not None:
                        fields.append(ts_createdby)
                        values.append(int(user_id))

                        # MachineID der Serie zuweisen (statt in Experiments)
                        ts_machine = resolve_field(
                            ["MachineID", "Maschine"], ts_cols)
                        if ts_machine is not None:
                            fields.append(ts_machine)
                            values.append(machine_id)

                        # Joker-Maschine: Flag + OriginalJoker in tblTrialSeries setzen
                        is_joker_selected = bool(
                            getattr(self, "_joker_machine_selected", False))

                        ts_is_joker = resolve_field([
                            "IsJoker", "Is Joker", "Joker"
                        ], ts_cols)
                        if ts_is_joker is not None:
                            fields.append(ts_is_joker)
                            values.append(-1 if is_joker_selected else 0)

                        ts_original_joker = resolve_field([
                            "OriginalJoker",
                            "Original Joker",
                            "OriginalJokerID",
                            "Original Joker ID",
                            "OriginalJokerMachineID",
                            "Original Joker Machine ID",
                        ], ts_cols)
                        if is_joker_selected and ts_original_joker is not None:
                            fields.append(ts_original_joker)
                            values.append(machine_id)

                    placeholders = ",".join(["?"] * len(fields))
                    ts_sql = f"INSERT INTO {ts_table} ({','.join('['+c+']' for c in fields)}) VALUES ({placeholders})"
                    ts_id = self._insert_and_identity(cur, ts_sql, values)
                # YarnID wird direkt in tblTrialSettings pro Trial gesetzt (siehe unten)

                new_trial_ids: List[int] = []

                jetplate_is_numeric = self._col_is_numeric(
                    trial_table, tr_plate)
                rows_max = fetch_all(
                    f"SELECT MAX([{tr_no}]) AS mx FROM {trial_table} WHERE [{tr_sid}] = ?", [ts_id])
                trial_counter = (
                    int(rows_max[0]["mx"]) + 1) if rows_max and rows_max[0]["mx"] is not None else 1

                for j in self._jets_data:
                    try:
                        plates_list = [p.strip() for p in str(
                            j["PlateList"]).split(",") if p.strip() != ""]
                    except Exception:
                        plates_list = []
                    if not plates_list:
                        try:
                            nn = int(j.get("Plates") or 0)
                        except Exception:
                            nn = 0
                        plates_list = [str(k+1) for k in range(max(0, nn))]

                    for plate in plates_list:
                        cols = [tr_sid, tr_no, tr_jetid, tr_plate, tr_press]
                        press_val = self._to_float_or_none(j["Pressure"])
                        plate_value: Any = self._to_int_or_none(
                            plate) if jetplate_is_numeric else str(plate)
                        vals: List[Any] = [ts_id, trial_counter,
                                           int(j["JetID"]), plate_value, press_val]
                        # HousingID – aus _jets_data (gespeichert beim Add)
                        housing_id = j.get("HousingID")
                        if tr_housing and housing_id is not None:
                            cols.append(tr_housing)
                            vals.append(int(housing_id))
                        for col, val in machine_dynamic_cols_trial:
                            cols.append(col)
                            vals.append(val)
                        # optionale GlobalID-Spalte im Trial (falls vorhanden)
                        tr_gid = resolve_field(["GlobalID"], tr_cols)
                        if tr_gid:
                            cols.append(tr_gid)
                            vals.append(new_global_id())
                        placeholders = ",".join(["?"] * len(cols))
                        sql = f"INSERT INTO {trial_table} ({','.join('['+c+']' for c in cols)}) VALUES ({placeholders})"
                        tid = self._insert_and_identity(cur, sql, vals)
                        new_trial_ids.append(tid)

                        # tblTrialSettings: pro Garn einen Datensatz anlegen
                        if table_exists("tblTrialSettings") and self._materials_data:
                            ts_set_cols_map = get_columns_map("tblTrialSettings")
                            has_yarn_use_col = "yarnuseid" in ts_set_cols_map
                            has_spool_col = "spoolid" in ts_set_cols_map
                            for idx_m, m in enumerate(self._materials_data):
                                s_cols = ["TrialID", "YarnID", "Ply"]
                                s_vals: List[Any] = [
                                    tid,
                                    int(m["YarnID"]),
                                    m.get("Ply") or f"Ply {idx_m + 1}",
                                ]
                                # YarnUseID optional mitschreiben
                                if has_yarn_use_col and m.get("YarnUseID") is not None:
                                    real_yuse = ts_set_cols_map.get("yarnuseid") or "YarnUseID"
                                    s_cols.append(real_yuse)
                                    s_vals.append(m["YarnUseID"])
                                if has_spool_col and m.get("SpoolID") is not None:
                                    real_spool = ts_set_cols_map.get("spoolid") or "SpoolID"
                                    s_cols.append(real_spool)
                                    s_vals.append(m["SpoolID"])
                                for s_col, s_val in machine_dynamic_cols_settings:
                                    real_s = ts_set_cols_map.get(s_col.lower()) or s_col
                                    s_cols.append(real_s)
                                    s_vals.append(s_val)
                                s_gid = resolve_field(["GlobalID"], ts_set_cols_map)
                                if s_gid:
                                    s_cols.append(s_gid)
                                    s_vals.append(new_global_id())
                                s_ph = ",".join(["?"] * len(s_cols))
                                cur.execute(
                                    f"INSERT INTO tblTrialSettings "
                                    f"({','.join('[' + c + ']' for c in s_cols)}) "
                                    f"VALUES ({s_ph})",
                                    s_vals,
                                )

                        trial_counter += 1

                # Lab Machines -> in AddTrials jetzt FRISCH aus _lab_data schreiben (kein Übernehmen)
                # Einige Labor-Tabellen (z.B. tbllabordytomat) haben einen NOT NULL FK auf tbluser(UserID).
                # Falls im Insert kein UserID angegeben wird, landet in MySQL oft ein Default (z.B. 0) -> FK-Fehler.
                default_user_id = None
                if table_exists("tbluser"):
                    try:
                        urows = fetch_all("SELECT MIN([ID]) AS uid FROM tbluser")
                        if urows and urows[0].get("uid") is not None:
                            default_user_id = int(urows[0]["uid"])
                    except Exception:
                        default_user_id = None

                for lm in self._lab_data:
                    if str(lm.get("RowMode") or "").strip().lower() == "seriesfreeform":
                        # Jet Air Consumption & Co: keine Zeile pro Trial -
                        # wird unten einmal pro Series (physische Duese x Druck) angelegt.
                        continue
                    tbl = (lm.get("TableName") or "").strip()
                    if not tbl or not table_exists(tbl):
                        continue
                    lcols = get_columns_map(tbl)
                    col_trial = resolve_field(["TrialID"], lcols) or "TrialID"
                    add_src = (lm.get("AdditionalFieldSource") or "").strip()
                    add_real = resolve_field(
                        [add_src], lcols) if add_src else None
                    add_val = lm.get("AdditionalVal", None)
                    if isinstance(add_val, str):
                        add_val = self._to_float_or_none(add_val) or add_val
                    for tid in new_trial_ids:
                        if 'waterbath' in (tbl or '').lower():
                            insert_waterbath_rows(cur, tbl, col_trial, tid)
                            continue
                        # optionale GlobalID-Spalte im Labor-Table
                        col_gid = resolve_field(["GlobalID"], lcols)
                        cols_sql_parts = [f"[{col_trial}]"]
                        params = [tid]
                        if col_gid:
                            cols_sql_parts.append(f"[{col_gid}]")
                            params.append(new_global_id())
                        if add_real:
                            cols_sql_parts.append(f"[{add_real}]")
                            params.append(add_val)

                        # optionaler UserID (FK auf tbluser) – falls vorhanden, sauber setzen
                        col_user = resolve_field(["UserID", "User"], lcols)
                        if col_user:
                            if default_user_id is None:
                                # Ohne gültigen User können wir diese Lab-Row nicht anlegen (sonst FK-Fehler)
                                continue
                            cols_sql_parts.append(f"[{col_user}]")
                            params.append(default_user_id)

                        placeholders = ",".join(["?"] * len(params))
                        cur.execute(
                            f"INSERT INTO {tbl} (" + ",".join(cols_sql_parts) +
                            ") VALUES (" + placeholders + ")",
                            params,
                        )
                self._save_jet_air_consumption_rows(cur, ts_id)
                cn.commit()

            if callable(self.on_open_experiment):
                if is_create_like:
                    if self.mode == "legacy":
                        # In legacy mode the textbox contains the full Experiment-ID (e.g. 2019-73-002)
                        exp_label = self.txtExperimentNumber.text().strip()
                    else:
                        exp_label = f"{self.strExperimentData[0]}-{self.txtExperimentNumber.text().strip()}"
                else:
                    data = self.cmbExistingExperiment.currentData()
                    num = data[5]
                    exp_label = f"{data[2]}-{str(data[3])}{str(data[4])}-{str(num).zfill(3) if str(num).isdigit() else num}"
                self.on_open_experiment(exp_id, ts_id, exp_label)
            else:
                QMessageBox.information(
                    self, "Saved",
                    f"{'Trials added' if self.mode == 'addtrials' else ('Trial series added' if self.mode == 'addseries' else 'Experiment saved')}.\n"
                    f"Experiment ID: {exp_id} • Serie: {ts_id}"
                )
        except Exception as e:
            try:
                cn.rollback()
            except Exception:
                pass
            QMessageBox.critical(self, "Save failed", f"{e}")

    # -->-->-->- addSeries/addTrials Helper -->-->-->-
    def _prefill_lab_from_series(self, series_id: int) -> None:
        """Befüllt tblLabMachines mit den Lab Machines der bestehenden Trials der Serie.

        Geht durch alle bekannten Lab Machine-Einträge (_lab_machines) und prüft,
        ob die jeweilige TableName Einträge für diese Serie hat. Wenn ja → hinzufügen.
        Für Itemat zusätzlich die DISTINCT AdditionalVal (Tension) aus der Lab-Tabelle laden.
        """
        if not self._lab_machines:
            return

        # Alle Trial-IDs der Serie
        try:
            trial_rows = fetch_all(
                "SELECT ID FROM tblTrial WHERE TrialSeriesID = ? ORDER BY Versuchsnummer",
                [series_id])
            if not trial_rows:
                return
            trial_ids = [int(r["ID"]) for r in trial_rows]
        except Exception:
            return

        placeholders = ",".join(["?"] * len(trial_ids))

        # _lab_data + tblLabMachines leeren (Prefill von Grund auf)
        self._lab_data.clear()
        while self.tblLabMachines.rowCount():
            self.tblLabMachines.removeRow(0)

        added_keys: set = set()  # (lm_id, add_val_norm)

        for lm_id, meta in self._lab_machines.items():
            tbl = str(meta.get("Tbl") or "").strip()
            src = str(meta.get("Src") or "").strip()
            lm_name = str(meta.get("LMName") or "").strip()
            unit = str(meta.get("Unit") or "").strip()
            if not tbl or not table_exists(tbl):
                continue

            try:
                # Prüfen ob Einträge für diese Serie existieren
                lcols = get_columns_map(tbl)
                col_trial = resolve_field(["TrialID"], lcols)
                if not col_trial:
                    continue

                if src and resolve_field([src], lcols):
                    # Mit AdditionalField (z.B. Itemat Tension): DISTINCT Werte laden
                    src_col = resolve_field([src], lcols)
                    rows = fetch_all(
                        f"SELECT DISTINCT [{src_col}] AS AV "
                        f"FROM [{tbl}] WHERE [{col_trial}] IN ({placeholders})"
                        f" AND [{src_col}] IS NOT NULL",
                        trial_ids)
                    for row in rows:
                        add_val = row.get("AV")
                        try:
                            add_val = float(add_val)
                        except Exception:
                            pass
                        key = (lm_id, str(add_val) if add_val is not None else None)
                        if key in added_keys:
                            continue
                        added_keys.add(key)
                        disp = (f"{add_val} {unit}".strip() if add_val is not None else "")
                        r = self.tblLabMachines.rowCount()
                        self.tblLabMachines.insertRow(r)
                        self.tblLabMachines.setItem(r, 0, QTableWidgetItem(lm_name))
                        self.tblLabMachines.setItem(r, 1, QTableWidgetItem(disp))
                        self._lab_data.append({
                            "LMID": lm_id, "Name": lm_name,
                            "AdditionalDisp": disp, "AdditionalVal": add_val,
                            "TableName": tbl, "AdditionalFieldSource": src,
                            "Unit": unit,
                        })
                else:
                    # Ohne AdditionalField: einmal hinzufügen falls Einträge vorhanden
                    cnt_rows = fetch_all(
                        f"SELECT COUNT(*) AS C FROM [{tbl}] WHERE [{col_trial}] IN ({placeholders})",
                        trial_ids)
                    cnt = int(cnt_rows[0]["C"]) if cnt_rows and cnt_rows[0].get("C") else 0
                    if cnt == 0:
                        continue
                    key = (lm_id, None)
                    if key in added_keys:
                        continue
                    added_keys.add(key)
                    r = self.tblLabMachines.rowCount()
                    self.tblLabMachines.insertRow(r)
                    self.tblLabMachines.setItem(r, 0, QTableWidgetItem(lm_name))
                    self.tblLabMachines.setItem(r, 1, QTableWidgetItem(""))
                    self._lab_data.append({
                        "LMID": lm_id, "Name": lm_name,
                        "AdditionalDisp": "", "AdditionalVal": None,
                        "TableName": tbl, "AdditionalFieldSource": src,
                        "Unit": unit,
                    })
            except Exception:
                continue

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
        self._ply_offset = 0
        try:
            rows = fetch_all(
                "SELECT MAX(CAST(REPLACE(Ply, 'Ply ', '') AS UNSIGNED)) AS MaxPly "
                "FROM tblTrialSettings ts "
                "JOIN tblTrial t ON t.ID = ts.TrialID "
                "WHERE t.TrialSeriesID = ?",
                [trialseries_id])
            if rows and rows[0].get("MaxPly") is not None:
                self._ply_offset = int(rows[0]["MaxPly"])
        except Exception:
            # Fallback: COUNT DISTINCT Ply
            try:
                rows2 = fetch_all(
                    "SELECT COUNT(DISTINCT ts.Ply) AS C "
                    "FROM tblTrialSettings ts "
                    "JOIN tblTrial t ON t.ID = ts.TrialID "
                    "WHERE t.TrialSeriesID = ?",
                    [trialseries_id])
                if rows2 and rows2[0].get("C"):
                    self._ply_offset = int(rows2[0]["C"])
            except Exception:
                pass

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
            self.tblYarns.setItem(rr, 0, QTableWidgetItem(name))
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
        """Ermittelt die distinkten 'physischen Duesen' (JetID + JetPlate) einer Series.

        JetID sitzt normalerweise auf tbltrialsettings (pro Ply/Material);
        manche Series haben aber (noch/nur) ein JetID direkt auf tbltrial
        gepflegt (aeltere Datensaetze / andere Erfassungswege). Um das nicht
        stillschweigend zu verpassen, wird beides abgefragt und kombiniert:
        COALESCE(ts.JetID, t.JetID). JetPlate (Plaettchennummer) sitzt auf
        tbltrial.
        """
        if not table_exists("tbltrialsettings") or not table_exists("tbltrial"):
            return []
        ts_cols = get_columns_map("tbltrialsettings")
        t_cols = get_columns_map("tbltrial")
        col_jet_ts = resolve_field(["JetID"], ts_cols)
        col_jet_t = resolve_field(["JetID"], t_cols)
        col_plate = resolve_field(
            ["Jet Plate Number", "JetPlate", "Jet Plate", "JetPlateNumber"], t_cols) or "Jet Plate Number"

        if not col_jet_ts and not col_jet_t:
            return []

        if col_jet_ts and col_jet_t:
            jet_expr = f"COALESCE(ts.[{col_jet_ts}], t.[{col_jet_t}])"
        elif col_jet_ts:
            jet_expr = f"ts.[{col_jet_ts}]"
        else:
            jet_expr = f"t.[{col_jet_t}]"

        try:
            rows = fetch_all(
                f"SELECT DISTINCT {jet_expr} AS JetID, t.[{col_plate}] AS JetPlate "
                f"FROM tbltrialsettings ts "
                f"JOIN tbltrial t ON t.ID = ts.TrialID "
                f"WHERE t.TrialSeriesID = ? AND {jet_expr} IS NOT NULL",
                [series_id],
            )
        except Exception:
            return []
        out = []
        for r in rows:
            out.append({"JetID": int(r["JetID"]), "JetPlate": r.get("JetPlate")})
        return out

    def _save_jet_air_consumption_rows(self, cur, series_id: int) -> Dict[str, int]:
        """Legt fuer alle SeriesFreeform-Lab-Machine-Eintraege (Jet Air Consumption)
        die Kreuzprodukt-Zeilen (physische Duese x Druckstufe) an.

        Wird EINMAL pro Series aufgerufen (nicht pro Trial). Bereits vorhandene
        Kombinationen (Duese+Druck) werden nicht doppelt angelegt - so kann das
        auch beim addtrials-Speichern erneut aufgerufen werden, ohne Duplikate
        zu erzeugen, falls durch neue Trials neue physische Duesen dazukommen.

        Gibt Statistiken zurueck (fuer die Erfolgsmeldung / Diagnose), da diese
        Zeilen nicht im normalen inserted/skipped-Zaehler der Pro-Trial-Schleife
        auftauchen.
        """
        stats = {"created": 0, "skipped_exists": 0, "physical_jets": 0, "no_user": 0}

        freeform_entries = [
            lm for lm in self._lab_data
            if str(lm.get("RowMode") or "").strip().lower() == "seriesfreeform"
        ]
        if not freeform_entries:
            return stats

        physical_jets = self._get_physical_jets_for_series(series_id)
        stats["physical_jets"] = len(physical_jets)
        if not physical_jets:
            return stats

        for lm in freeform_entries:
            tbl = (lm.get("TableName") or "").strip()
            if not tbl or not table_exists(tbl):
                continue
            pressure = lm.get("AdditionalVal")
            if pressure is None:
                continue
            lcols = get_columns_map(tbl)
            col_series = resolve_field(["TrialSeriesID"], lcols) or "TrialSeriesID"
            col_jet = resolve_field(["JetID"], lcols) or "JetID"
            col_plate = resolve_field(["JetPlate"], lcols) or "JetPlate"
            col_press = resolve_field(["AirPressure"], lcols) or "AirPressure"
            col_gid = resolve_field(["GlobalID"], lcols)
            col_user = resolve_field(["UserID", "User"], lcols)
            default_user_id = None
            if col_user and table_exists("tbluser"):
                try:
                    urows = fetch_all("SELECT MIN([ID]) AS uid FROM tbluser")
                    if urows and urows[0].get("uid") is not None:
                        default_user_id = int(urows[0]["uid"])
                except Exception:
                    default_user_id = None

            for pj in physical_jets:
                # Bereits vorhanden? (Duese+Druck fuer diese Series)
                try:
                    existing = fetch_all(
                        f"SELECT [ID] FROM {tbl} WHERE [{col_series}] = ? AND [{col_jet}] = ? "
                        f"AND ([{col_plate}] = ? OR (? IS NULL AND [{col_plate}] IS NULL)) "
                        f"AND [{col_press}] = ?",
                        [series_id, pj["JetID"], pj["JetPlate"], pj["JetPlate"], pressure],
                    )
                except Exception:
                    existing = []
                if existing:
                    stats["skipped_exists"] += 1
                    continue

                cols = [col_series, col_jet, col_plate, col_press]
                vals: List[Any] = [series_id, pj["JetID"], pj["JetPlate"], pressure]
                if col_gid:
                    cols.append(col_gid)
                    vals.append(new_global_id())
                if col_user:
                    if default_user_id is None:
                        stats["no_user"] += 1
                        continue  # kann ohne gueltigen User nicht anlegen (NOT NULL FK)
                    cols.append(col_user)
                    vals.append(default_user_id)
                ph = ",".join(["?"] * len(cols))
                cur.execute(
                    f"INSERT INTO {tbl} (" + ",".join(f"[{c}]" for c in cols) + f") VALUES ({ph})",
                    vals,
                )
                stats["created"] += 1

        return stats

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
            QMessageBox.warning(self, "Prefill Jets",
                                f"Jets konnten nicht geladen werden:\n{e}")
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
        """Query tblTrial for JetID, Jet Plate, Air Pressure and HousingID for the
        given series and aggregate into Jet rows for the Jet tab."""
        # Resolve columns from tblTrial
        if not table_exists("tblTrial"):
            return
        cmap_t = get_columns_map("tblTrial")
        col_sid = resolve_field(
            ["TrialSeriesID", "SeriesID", "SerieID"], cmap_t) or "TrialSeriesID"
        col_jet = resolve_field(["JetID", "Jet"], cmap_t) or "JetID"
        col_plate = resolve_field(
            ["Jet Plate", "JetPlate", "JetPlates", "Plate"], cmap_t) or "Jet Plate"
        col_press = resolve_field(["Air Pressure (bar)", "Air Pressure",
                                  "Pressure (bar)", "Pressure"], cmap_t) or "Air Pressure (bar)"
        col_housing = resolve_field(["HousingID", "Housing"], cmap_t)

        if col_housing:
            select_housing = f", [{col_housing}] AS JHOUSING"
        else:
            select_housing = ""

        rows = fetch_all(
            f"SELECT [{col_jet}] AS JID, [{col_plate}] AS JPLATE, [{col_press}] AS JPRESS"
            f"{select_housing} "
            f"FROM [tblTrial] WHERE [{col_sid}] = ?",
            [series_id]
        )
        if not rows:
            return

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

        # Build JetID -> JetName mapping
        jet_name_by_id = {}
        try:
            if table_exists("tblDTYJets"):
                cmap_j = get_columns_map("tblDTYJets")
                col_j_id = resolve_field(["ID"], cmap_j) or "ID"
                col_j_name = resolve_field(
                    ["Jet", "Name", "Bezeichnung"], cmap_j) or "Jet"
                for r in fetch_all(f"SELECT [{col_j_id}] AS JID, [{col_j_name}] AS JName FROM [tblDTYJets]"):
                    try:
                        jet_name_by_id[int(r['JID'])] = str(r['JName'])
                    except Exception:
                        pass
        except Exception:
            pass

        # Group by (JetID, Pressure)
        from collections import defaultdict
        groups = defaultdict(lambda: set())
        pressure_by_key = {}
        housing_by_key: dict = {}
        for r in rows:
            try:
                jid = int(r.get("JID") or r.get("JetID"))
            except Exception:
                jid = r.get("JID") or r.get("JetID")
            plate = r.get("JPLATE") or r.get("JetPlate")
            # parse plate to int if possible
            try:
                plate = int(str(plate).strip())
            except Exception:
                try:
                    plate = int(float(str(plate).strip()))
                except Exception:
                    plate = str(plate).strip()
            pres_raw = str(r.get("JPRESS", "") or r.get("Pressure", "")).replace(",", ".").strip()
            try:
                pres_val = float(pres_raw)
            except Exception:
                pres_val = pres_raw  # keep as string
            key = (jid, pres_val)
            if plate not in (None, ""):
                groups[key].add(plate)
            pressure_by_key[key] = pres_val
            # Housing: erstes gefundenes Housing pro Gruppe übernehmen
            if key not in housing_by_key and col_housing:
                raw_hid = r.get("JHOUSING")
                if raw_hid is not None:
                    try:
                        housing_by_key[key] = int(raw_hid)
                    except Exception:
                        housing_by_key[key] = raw_hid

        # Insert aggregated rows
        for (jid, pres_val), plates in groups.items():
            plates_list = sorted([int(x) for x in plates if isinstance(x, (int, float))] + [int(float(x))
                                 for x in plates if isinstance(x, str) and x.replace('.', '', 1).isdigit()]) if plates else []
            # normalize pressure display
            if isinstance(pres_val, (int, float)):
                p_disp = f"{float(pres_val):.2f}".rstrip("0").rstrip(".")
            else:
                p_disp = str(pres_val)
            # jet name
            jname = jet_name_by_id.get(jid, "")
            # housing
            housing_id = housing_by_key.get((jid, pres_val))
            housing_name = ""
            if housing_id is not None:
                try:
                    housing_name = housing_name_by_id.get(int(housing_id), "")
                except Exception:
                    housing_name = housing_name_by_id.get(housing_id, "")
            # Add to UI table
            rix = self.tblJets.rowCount()
            self.tblJets.insertRow(rix)
            self.tblJets.setItem(rix, 0, QTableWidgetItem(housing_name))
            self.tblJets.setItem(rix, 1, QTableWidgetItem(jname))
            self.tblJets.setItem(
                rix, 2, QTableWidgetItem(str(len(plates_list))))
            self.tblJets.setItem(rix, 3, QTableWidgetItem(p_disp))
            self.tblJets.setItem(rix, 4, QTableWidgetItem(
                ",".join(str(x) for x in plates_list)))
            # Track internal structure
            self._jets_data.append({
                "JetID": jid, "JetName": jname, "Plates": len(plates_list),
                "Pressure": p_disp, "PlateList": ",".join(str(x) for x in plates_list),
                "HousingID": housing_id, "HousingName": housing_name
            })