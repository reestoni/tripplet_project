from __future__ import annotations

# ui/screen_show_experiment.py
"""Haupt-Anzeige- und Bearbeitungs-Screen für ein einzelnes Experiment (ShowExperimentScreen).

Der zentralste Screen von TrippleT. Zeigt ein Experiment mit allen Trials und
Messwerten in einer Pivot-Tabelle an. Ermöglicht direktes Bearbeiten der Werte
in der Tabelle.

Aufbau (Tabs):
  - Tab "Trials":          Pivot-Tabelle mit allen Trial-Spalten (editierbar)
  - Tab "Messresultate":   TDMS/Statimat/Itemat Auswertungen
  - Tab "YarnScope DTY":   Garndicken-Diagramm (GarnCanvas)
  - Tab "Bilder":          Bilder zur TrialSeries
  - Tab "Notizen":         Freitext-Notizen

Kernklassen:
  - PivotEditModel:     QAbstractTableModel für die Pivot-Tabelle
    (Zeilen = Felder, Spalten = Trials/Plies)
  - ShowExperimentScreen: Hauptwidget

Besonderheiten:
  - Pivot-Ansicht: Felder als Zeilen, Trials als Spalten (transponiert zur DB-Struktur)
  - CellBinding: verbindet eine Tabellenzelle mit DB-Tabelle/Spalte/PK für direktes Speichern
  - Zellen-Validierung: Typ-Prüfung (int/float/text), Pflichtfelder
  - Füllen-Funktionen: Zellen-Bereich mit Wert füllen (_FillRowRange-Dialoge)
  - Ply-Spalten: mehrere Plies pro Trial (horizontal expandiert)
  - Statimat/Itemat PDF-Import: Werte aus Prüfberichten direkt in Tabelle importieren
  - Bild-Upload (tblTrialSeriesImage), Notizen (tblTrialSeriesNotes)

Datenbankbezug:
  tblExperimente, tblTrialSeries, tblTrial, tblTrialSettings,
  tblTrialSeriesImage, tblExperimentRequests, tblStatimat (optional)
"""

# ui/screen_show_experiment.py
from ui.theme import accent_tint, accent_gridline, get_accent
from PySide6.QtGui import QPixmap, QColor, QIcon
from ui.pathutil import resource_path
from ui.text_normalize import norm, resolve_field, canon_rule  # canon_rule moved there (2026-11-13)
from ui.widgets.statimat_pdf_parser import parse_statimat_pdf
from ui.widgets.itemat_pdf_parser import parse_itemat_pdf, DB_TENSIONS as ITEMAT_DB_TENSIONS
from ui.widgets import sidebar_nav
from ui.yarnscope.garngraf_canvas import GarnCanvas
from ui.widgets.footer import FooterBar
from ui.widgets.frozen_first_column_table import FrozenFirstColumnTable
from ui.widgets.label_printing import (
    MM, fit_text, load_label_template, PrintLabelsDialog, generate_label_sheet_pdf,
)
import ui.aty_yarnscope_tab as _aty_mod
import ui.dty_yarnscope_tab as _dty_mod
import ui.advisor_tab as _advisor_mod
import ui.machine_tab as _machine_tab_mod
import ui.widgets.yarn_locations as _yarn_locations
import ui.cell_notes_ui as _cell_notes_ui
import db.series_tables as _series_tables
import db.machine_data as _machine_data
from db.machine_data import get_columns_info  # noqa: F401  (moved there, still imported from here)
from ui.advisor_worker import AdvisorWorker, load_api_key
from ui.screen_create_experiment_request import (
    EXCLUDE_FIELDS as ER_EXCLUDE_FIELDS,
    MULTILINE_FIELDS as ER_MULTILINE_FIELDS,
    DATE_FIELDS as ER_DATE_FIELDS,
    ColumnInfo as ER_ColumnInfo,
    _get_table_columns as er_get_table_columns,
    _table_exists as er_table_exists,
    _try_tables_for_fk as er_try_tables_for_fk,
    _pick_display_column as er_pick_display_column,
)
from db.connection import (
    get_connection,
    new_global_id,
    execute as _db_execute,
    table_exists as _db_table_exists,
    get_columns_map as _db_get_columns_map,
    is_dev_mode,
)
from db.trial_reference import (
    IS_REFERENCE_COL,
    REFERENCE_NAME_COL,
    has_reference_columns,
    is_reference_value,
    next_reference_number,
    next_trial_number,
    format_number_list,
    format_trial_number,
    reference_label,
    reference_tooltip,
)

import html
import re
import os
import sys
import logging
import tempfile
import uuid
import datetime
import app_meta
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal, QObject, QEvent, QSize, QRect, QRegularExpression, QTimer, QItemSelectionModel
from PySide6.QtGui import QShortcut, QKeySequence, QPainter, QPen, QBrush, QFont, QRegularExpressionValidator, QCursor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QFrame,
    QTabWidget,
    QTableView,
    QMessageBox,
    QComboBox,
    QStyledItemDelegate,
    QInputDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QSpinBox,
    QLineEdit,
    QApplication,
    QAbstractItemView,
    QScrollArea,
    QTextEdit,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QDoubleSpinBox,
    QHeaderView,
    QProgressDialog,
    QCheckBox,
    QToolTip,
    QMenu,
    QTableWidget,
    QTableWidgetItem,
    QSizePolicy,
)
from ui.widgets.friendly_error import show_error

# Basisordner fuer TrialSeries-Bilder/-PDFs: db/series_attachments.py (shared with the web app)
from db.series_attachments import TRIALSERIES_IMAGES_BASE_DIR, TRIALSERIES_PDFS_BASE_DIR  # noqa: E402,F401


# Trial label cell renderer: db/trial_labels.py (Qt-free, shared with the web app)
from db.trial_labels import draw_trial_label_cell as _draw_trial_label_cell  # noqa: E402,F401


class _FillRowRangeDialog(QDialog):
    """Dialog zum Füllen eines Zeilenbereichs mit einem Textwert.

    Lässt Benutzer Start/End-Zeile und den Wert eingeben.
    """
    """Popup to bulk-set a machine-tab row value over a trial range.

    When *ply_labels* is provided (tblTrialSettings fields), the dialog shows
    Ply checkboxes so the user can restrict the change to specific Plies.
    For tblTrial fields (trial-wide) *ply_labels* is None/empty and the
    Ply section is hidden entirely.

    get_values() returns (from_trial_1based, to_trial_1based, value, selected_plies)
    where selected_plies is a set of ply label strings (or None = all).
    """

    def __init__(
            self,
            parent: QWidget,
            title: str,
            n_trials: int,
            default_value: str,
            ply_labels: Optional[List[str]] = None,  # None/[] → tblTrial field, hide Ply section
    ):
        super().__init__(parent)
        self.setWindowTitle("Fill row")
        self._n_trials = max(1, int(n_trials))
        self._ply_labels = ply_labels or []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        lbl = QLabel(f"Set value for: <b>{title}</b>")
        lbl.setTextFormat(Qt.RichText)
        layout.addWidget(lbl)

        # ── Ply checkboxes (only for tblTrialSettings fields) ──────────────
        self._ply_checks: List[QCheckBox] = []
        if self._ply_labels:
            ply_frame = QFrame()
            ply_frame.setFrameShape(QFrame.StyledPanel)
            ply_layout = QVBoxLayout(ply_frame)
            ply_layout.setContentsMargins(8, 6, 8, 6)
            ply_layout.setSpacing(4)
            ply_layout.addWidget(QLabel("<b>Materials to update:</b>"))
            cb_row = QHBoxLayout()
            cb_row.setSpacing(12)
            for pl in self._ply_labels:
                cb = QCheckBox(str(pl))
                cb.setChecked(True)
                self._ply_checks.append(cb)
                cb_row.addWidget(cb)
            cb_row.addStretch(1)
            ply_layout.addLayout(cb_row)
            layout.addWidget(ply_frame)

        # ── Trial range ────────────────────────────────────────────────────
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignLeft)

        self.sp_from = QSpinBox()
        self.sp_from.setRange(1, self._n_trials)
        self.sp_from.setValue(1)

        self.sp_to = QSpinBox()
        self.sp_to.setRange(1, self._n_trials)
        self.sp_to.setValue(self._n_trials)

        self.ed_value = QLineEdit()
        self.ed_value.setText(default_value or "")

        form.addRow("From trial #", self.sp_from)
        form.addRow("To trial #", self.sp_to)
        form.addRow("Value", self.ed_value)
        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.ed_value.setFocus()
        self.ed_value.selectAll()

    def get_values(self) -> Tuple[int, int, str, Optional[set]]:
        """Gibt (start_row, end_row, wert, spalten_filter) zurück."""
        a = int(self.sp_from.value())
        b = int(self.sp_to.value())
        if b < a:
            a, b = b, a
        value = str(self.ed_value.text())
        if self._ply_checks:
            selected = {cb.text() for cb in self._ply_checks if cb.isChecked()}
        else:
            selected = None  # None = all columns (trial-wide field)
        return a, b, value, selected


class _FillRowRangeJetDialog(QDialog):
    """Dialog zum Füllen eines Zeilenbereichs mit einem Jet-Wert (Combobox)."""
    """Single popup to set the *Jet* row for a trial range.

    Uses a dropdown with all jets (Jet name shown, JetID stored).
    """

    def __init__(
            self,
            parent: QWidget,
            title: str,
            n_trials: int,
            jets_list: List[Tuple[Any, str]],
            default_jet_id: Any = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Fill row")
        self._n_trials = max(1, int(n_trials))
        self._jets_list = jets_list or []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        lbl = QLabel(f"Set value for: <b>{title}</b>")
        lbl.setTextFormat(Qt.RichText)
        layout.addWidget(lbl)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignLeft)

        self.sp_from = QSpinBox()
        self.sp_from.setRange(1, self._n_trials)
        self.sp_from.setValue(1)

        self.sp_to = QSpinBox()
        self.sp_to.setRange(1, self._n_trials)
        self.sp_to.setValue(self._n_trials)

        self.cb_jet = QComboBox()
        self.cb_jet.setEditable(False)
        self.cb_jet.setInsertPolicy(QComboBox.NoInsert)
        self.cb_jet.setMinimumWidth(240)
        self.cb_jet.addItem("", None)  # allow clearing
        for jet_id, jet_name in self._jets_list:
            self.cb_jet.addItem(str(jet_name), jet_id)

        # default selection
        if default_jet_id not in (None, "", " "):
            try:
                i = self.cb_jet.findData(int(default_jet_id))
            except Exception:
                i = self.cb_jet.findData(default_jet_id)
            if i >= 0:
                self.cb_jet.setCurrentIndex(i)

        form.addRow("From trial #", self.sp_from)
        form.addRow("To trial #", self.sp_to)
        form.addRow("Jet", self.cb_jet)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        # Focus on dropdown
        self.cb_jet.setFocus()

        self.sp_from.valueChanged.connect(self._sync_ranges)
        self.sp_to.valueChanged.connect(self._sync_ranges)

    def _sync_ranges(self):
        """Synchronisiert Start/End-Spinner so dass Start <= End gilt."""
        pass

    def get_values(self) -> Tuple[int, int, Any]:
        a = int(self.sp_from.value())
        b = int(self.sp_to.value())
        if b < a:
            a, b = b, a
        return a, b, self.cb_jet.currentData()


class _FillRowRangeDropdownDialog(QDialog):
    """Dialog zum Füllen eines Zeilenbereichs mit einem FK-Wert aus einer Combobox."""
    """Generischer Bulk-Edit-Dialog für Lookup-Zeilen (z.B. DiscType).

    lookup_map: {id → name}  – wird als Dropdown angezeigt; ID wird gespeichert.
    """

    def __init__(
            self,
            parent: QWidget,
            title: str,
            n_trials: int,
            lookup_map: Dict[Any, str],
            default_id: Any = None,
            ply_labels: Optional[List[str]] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Fill row")
        self._n_trials = max(1, int(n_trials))
        self._ply_labels = ply_labels or []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        lbl = QLabel(f"Set value for: <b>{title}</b>")
        lbl.setTextFormat(Qt.RichText)
        layout.addWidget(lbl)

        # ── Ply checkboxes (only for tblTrialSettings fields) ─────────────
        self._ply_checks: List[QCheckBox] = []
        if self._ply_labels:
            ply_frame = QFrame()
            ply_frame.setFrameShape(QFrame.StyledPanel)
            ply_layout = QVBoxLayout(ply_frame)
            ply_layout.setContentsMargins(8, 6, 8, 6)
            ply_layout.setSpacing(4)
            ply_layout.addWidget(QLabel("<b>Materials to update:</b>"))
            cb_row = QHBoxLayout()
            cb_row.setSpacing(12)
            for pl in self._ply_labels:
                cb = QCheckBox(str(pl))
                cb.setChecked(True)
                self._ply_checks.append(cb)
                cb_row.addWidget(cb)
            cb_row.addStretch(1)
            ply_layout.addLayout(cb_row)
            layout.addWidget(ply_frame)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignLeft)

        self.sp_from = QSpinBox()
        self.sp_from.setRange(1, self._n_trials)
        self.sp_from.setValue(1)

        self.sp_to = QSpinBox()
        self.sp_to.setRange(1, self._n_trials)
        self.sp_to.setValue(self._n_trials)

        self.cb_value = QComboBox()
        self.cb_value.setEditable(False)
        self.cb_value.setInsertPolicy(QComboBox.NoInsert)
        self.cb_value.setMinimumWidth(240)
        self.cb_value.addItem("", None)  # allow clearing

        # Dedupliziert, nach Name sortiert, nur int-Keys
        seen: set = set()
        for item_id, item_name in sorted(lookup_map.items(), key=lambda x: str(x[1]).lower()):
            try:
                int_id = int(item_id)
            except Exception:
                int_id = None
            key = int_id if int_id is not None else item_id
            if key in seen:
                continue
            seen.add(key)
            self.cb_value.addItem(str(item_name), key)

        if default_id not in (None, "", " "):
            try:
                i = self.cb_value.findData(int(default_id))
            except Exception:
                i = self.cb_value.findData(default_id)
            if i >= 0:
                self.cb_value.setCurrentIndex(i)

        form.addRow("From trial #", self.sp_from)
        form.addRow("To trial #", self.sp_to)
        form.addRow(title, self.cb_value)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.cb_value.setFocus()

    def get_values(self) -> Tuple[int, int, Any, Optional[set]]:
        a = int(self.sp_from.value())
        b = int(self.sp_to.value())
        if b < a:
            a, b = b, a
        if self._ply_checks:
            selected = {cb.text() for cb in self._ply_checks if cb.isChecked()}
        else:
            selected = None
        return a, b, self.cb_value.currentData(), selected


class _FillRowRangeHousingDialog(QDialog):
    """Dialog zum Füllen eines Zeilenbereichs mit einem Housing-Wert."""
    """Single popup to set the *Housing* row for a trial range.

    Uses a dropdown with all housings (HousingName shown, HousingID stored).
    """

    def __init__(
            self,
            parent: QWidget,
            title: str,
            n_trials: int,
            housing_list: List[Tuple[Any, str]],
            default_housing_id: Any = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Fill row")
        self._n_trials = max(1, int(n_trials))
        self._housing_list = housing_list or []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        lbl = QLabel(f"Set value for: <b>{title}</b>")
        lbl.setTextFormat(Qt.RichText)
        layout.addWidget(lbl)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignLeft)

        self.sp_from = QSpinBox()
        self.sp_from.setRange(1, self._n_trials)
        self.sp_from.setValue(1)

        self.sp_to = QSpinBox()
        self.sp_to.setRange(1, self._n_trials)
        self.sp_to.setValue(self._n_trials)

        self.cb_housing = QComboBox()
        self.cb_housing.setEditable(False)
        self.cb_housing.setInsertPolicy(QComboBox.NoInsert)
        self.cb_housing.setMinimumWidth(240)
        self.cb_housing.addItem("", None)  # allow clearing
        for housing_id, housing_name in self._housing_list:
            self.cb_housing.addItem(str(housing_name), housing_id)

        # default selection
        if default_housing_id not in (None, "", " "):
            try:
                i = self.cb_housing.findData(int(default_housing_id))
            except Exception:
                i = self.cb_housing.findData(default_housing_id)
            if i >= 0:
                self.cb_housing.setCurrentIndex(i)

        form.addRow("From trial #", self.sp_from)
        form.addRow("To trial #", self.sp_to)
        form.addRow("Housing", self.cb_housing)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.cb_housing.setFocus()

        self.sp_from.valueChanged.connect(self._sync_ranges)
        self.sp_to.valueChanged.connect(self._sync_ranges)

    def _sync_ranges(self):
        pass

    def get_values(self) -> Tuple[int, int, Any]:
        a = int(self.sp_from.value())
        b = int(self.sp_to.value())
        if b < a:
            a, b = b, a
        return a, b, self.cb_housing.currentData()


class _ExperimentRequestReadOnlyDialog(QDialog):
    """Read-Only-Popup-Dialog für einen Experiment-Request.

    Zeigt alle Felder von tblExperimentRequests als Labels an.
    Unterstützt Bild-Vorschau (via _open_images_dialog).
    """
    """Read-only popup to show a linked Experiment Request.

    The UI is analogous to screen_create_experiment_request, but without editing/saving.
    """

    def __init__(
            self,
            parent: QWidget | None = None,
            request_id: Any = None,
            experiment_request_id: Any = None,
            title_prefix: str = "",
    ):
        # Support both kwarg spellings for backwards compatibility.
        if request_id in (None, "") and experiment_request_id not in (None, ""):
            request_id = experiment_request_id

        super().__init__(parent)
        self._request_id = request_id
        self._table = "tblExperimentRequests"
        # title_prefix: optional prefix for the window/header title (e.g.
        # "Version 2 — ") - used by the version history dialog (see
        # ui/widgets/experiment_request_version_history.py) so viewing an
        # archived prior version makes it immediately clear this is NOT the
        # current state. Empty ("") leaves behaviour unchanged for every
        # other caller.
        self._title_prefix = title_prefix or ""
        # Window title and header label will be set from tblExperimentRequests.Titel
        # once the record is loaded.
        self.setWindowTitle("Experiment Request")
        self.resize(860, 720)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(10)

        # Title row with image indicator (top-right)
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        title_row.addStretch(1)

        self._title_label = QLabel("Experiment Request")
        self._title_label.setTextFormat(Qt.RichText)
        self._title_label.setStyleSheet("font-size: 20px; font-weight: 700; color: #39A650;")
        self._title_label.setAlignment(Qt.AlignHCenter)
        title_row.addWidget(self._title_label, 0, Qt.AlignVCenter)

        title_row.addStretch(1)

        self._btn_show_images = QPushButton()
        self._btn_show_images.setObjectName("IconBtn")
        self._btn_show_images.setCursor(Qt.PointingHandCursor)
        self._btn_show_images.setFlat(True)
        self._btn_show_images.setToolTip("Show attached images")
        ico = QIcon(resource_path("assets/images/picture.png"))
        if not ico.isNull():
            self._btn_show_images.setIcon(ico)
            self._btn_show_images.setIconSize(QSize(22, 22))
        else:
            self._btn_show_images.setText("Images")
        self._btn_show_images.clicked.connect(self._open_images_dialog)
        self._btn_show_images.setVisible(False)
        title_row.addWidget(self._btn_show_images, 0, Qt.AlignVCenter)

        # Version history (2026-09-01, user request: reachable from the
        # read-only request viewer too - "sehe ich das auch im request
        # viewer? falls nein, da muss ich die einzelnen versionen auch
        # anzeigen lassen können (ist ja sowieso aller read-only)"). Only
        # visible when at least one accepted change was ever archived for
        # this request, see _sync_version_history_button().
        self._history_target_id: Any = None
        self._btn_version_history = QPushButton()
        self._btn_version_history.setObjectName("IconBtn")
        self._btn_version_history.setCursor(Qt.PointingHandCursor)
        self._btn_version_history.setFlat(True)
        self._btn_version_history.setToolTip("View version history")
        ico_hist = QIcon(resource_path("assets/images/history.png"))
        if not ico_hist.isNull():
            self._btn_version_history.setIcon(ico_hist)
            self._btn_version_history.setIconSize(QSize(22, 22))
        else:
            self._btn_version_history.setText("History")
        self._btn_version_history.clicked.connect(self._open_version_history_dialog)
        self._btn_version_history.setVisible(False)
        title_row.addWidget(self._btn_version_history, 0, Qt.AlignVCenter)

        root.addLayout(title_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        host = QWidget()
        self._form = QFormLayout(host)
        self._form.setContentsMargins(0, 0, 0, 0)
        self._form.setLabelAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._form.setFormAlignment(Qt.AlignTop)
        self._form.setHorizontalSpacing(14)
        self._form.setVerticalSpacing(0)

        scroll.setWidget(host)
        root.addWidget(scroll, 1)

        # Results of the series linked to this request (db/series_conclusion.for_request, same in the web popup)
        self._concl_label = QLabel()
        self._concl_label.setWordWrap(True)
        self._concl_label.setTextFormat(Qt.RichText)
        self._concl_label.setStyleSheet("QLabel{background:#f4f8f4; border:1px solid #d6e6d6; border-radius:6px; padding:8px;}")
        self._concl_label.setVisible(False)
        root.addWidget(self._concl_label, 0)
        if not self._title_prefix:          # archived versions show the request only
            self._load_conclusions()

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        btns.accepted.connect(self.accept)
        try:
            btns.button(QDialogButtonBox.Close).clicked.connect(self.close)
        except Exception:
            pass
        root.addWidget(btns, 0)

        self._build_and_load()

        # Initial state for the images indicator
        self._update_images_icon()

    def _load_conclusions(self) -> None:
        from html import escape as _esc
        from db import series_conclusion as _sc
        try:
            items = _sc.for_request(int(self._request_id)) if self._request_id not in (None, "") else []
        except Exception:
            items = []
        if not items:
            return
        parts = ["<b>Results of the linked series</b>"]
        for c in items:
            col = _sc.OUTCOME_COLOURS.get(c.get("outcome") or "open", "#8a94a0")
            line = (f"<br><span style='color:{col}'>●</span> <b>{_esc(c['experiment_id'])} – {_esc(c['series_name'])}</b>"
                    + (f" · {_sc.OUTCOME_LABELS.get(c['outcome'], '')}" if c.get("outcome") else ""))
            if c.get("summary"):
                line += f"<br>&nbsp;&nbsp;&nbsp;{_esc(c['summary'])}"
            rec = " – ".join(x for x in (_sc.RECOMMENDATION_LABELS.get(c.get("recommendation") or "", ""),
                                         c.get("recommendation_text") or "") if x)
            if rec:
                line += f"<br>&nbsp;&nbsp;&nbsp;<i>Recommendation: {_esc(rec)}</i>"
            parts.append(line)
        self._concl_label.setText("".join(parts))
        self._concl_label.setVisible(True)

    def _request_has_images(self, request_id: Any) -> bool:
        """True if at least one image row exists for this request."""
        from db import experiment_request_images as er_images
        return er_images.has_images(request_id)

    def _fetch_request_images(self, request_id: Any) -> List[Dict[str, str]]:
        """Returns dicts with FullPath + display name fields (db/experiment_request_images)."""
        from db import experiment_request_images as er_images
        # Provide both keys (StoredFilename + StoredFile) to be compatible with any viewer implementation
        return er_images.list_images(request_id, with_stored_file_key=True)

    def _update_images_icon(self) -> None:
        """Aktualisiert das Bild-Icon (sichtbar wenn Bilder vorhanden)."""
        btn = getattr(self, "_btn_show_images", None)
        if not btn:
            return
        btn.setVisible(self._request_has_images(self._request_id))

    def _sync_version_history_button(self, prior_version_of_id: Any) -> None:
        """Shows the version-history button when the currently displayed
        row has at least one archived version to show.

        `prior_version_of_id` is this row's OWN PriorVersionOfID (see
        db/experiment_request_changes.py) - if set, this row IS itself an
        archived snapshot, and its version history lives under the LIVE row
        it points to, not under its own ID. Falls back to self._request_id
        for the normal case (viewing the live/current request)."""
        btn = getattr(self, "_btn_version_history", None)
        if not btn:
            return
        try:
            from db import experiment_request_changes as request_changes
            self._history_target_id = prior_version_of_id or self._request_id
            btn.setVisible(request_changes.has_versions(self._history_target_id))
        except Exception:
            btn.setVisible(False)

    def _open_version_history_dialog(self) -> None:
        """Opens the version history dialog for this request (see
        ui/widgets/experiment_request_version_history.py)."""
        target_id = self._history_target_id or self._request_id
        try:
            from ui.widgets.experiment_request_version_history import show_version_history
            show_version_history(self, target_id)
        except Exception as e:
            QMessageBox.critical(self, "Version History", str(e))

    def _open_images_dialog(self) -> None:
        """Öffnet einen Dialog zur Anzeige der Bild-Anhänge des Requests."""
        try:
            images = self._fetch_request_images(self._request_id)
            if not images:
                QMessageBox.information(self, "Images", "No images attached to this request.")
                return

            # Local import to avoid any import-time coupling
            from ui.screen_create_experiment_request import ExperimentRequestImagesDialog

            title = self.windowTitle() or "Experiment Request"
            dlg = ExperimentRequestImagesDialog(
                self,
                f"Images – {title}",
                images,
                table_name="tblExperimentRequestImage",
                fk_field="ExperimentRequestID",
                fk_value=self._request_id,
            )
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Images", str(e))

    def _build_and_load(self) -> None:
        """Baut das Formular auf und lädt alle Request-Daten aus der DB."""
        if not er_table_exists(self._table):
            QMessageBox.critical(self, "DB Error", f"Table not found: {self._table}")
            return

        cols = er_get_table_columns(self._table)

        from db import experiment_requests as er
        try:
            data = er.fetch_request(self._request_id)
            if data is None:
                QMessageBox.warning(self, "Not found", "The linked request was not found.")
                return
        except Exception as e:
            QMessageBox.critical(self, "DB Error", str(e))
            return

        # Use tblExperimentRequests.Titel as the popup title (window title + header).
        win_title, header = er.popup_title(data, self._request_id, self._title_prefix)
        self.setWindowTitle(win_title)
        self._title_label.setText(header)

        # Update images indicator after we know the request is valid.
        self._update_images_icon()
        self._sync_version_history_button(data.get("PriorVersionOfID"))

        # Fields/labels/texts: db/experiment_requests.display_fields() (Titel is
        # the header; CreatedBy is shown here as "Created By", unlike the form).
        for f in er.display_fields(cols, data):
            lbl = QLabel(f["label"])
            lbl.setStyleSheet("padding: 8px 6px; color:#303030; font-weight:600;")

            w = self._make_display_widget(f["name"], f["text"])
            self._form.addRow(lbl, w)

            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet("color:#e6e6e6;")
            self._form.addRow(sep)

    def _lookup_project_label(self, project_id: Any) -> str:
        """Gibt den lesbaren Projektnamen für eine Projekt-ID zurück."""
        from db import experiment_requests as er
        return er.project_label(project_id)

    def _lookup_fk_label(self, field_name: str, fk_id: Any) -> str:
        """Gibt den lesbaren FK-Namen für eine FK-ID zurück (heuristisches Lookup)."""
        from db import experiment_requests as er
        return er.fk_label(field_name, fk_id)

    def _make_widget_for_field(self, field_name: str, val: Any) -> QWidget:
        """Erstellt einen passenden Display-Widget für ein Request-Feld."""
        from db import experiment_requests as er
        return self._make_display_widget(field_name, er.display_text(field_name, val))

    def _make_display_widget(self, field_name: str, txt: str) -> QWidget:
        """Read-only widget for an already formatted field text."""
        if field_name in ER_MULTILINE_FIELDS:
            te = QTextEdit()
            te.setReadOnly(True)
            te.setMinimumHeight(72)
            te.setText(txt)
            te.setStyleSheet("padding: 6px 8px; background:#f7f7f7; border:1px solid #d7d7d7;")
            return te

        le = QLineEdit()
        le.setReadOnly(True)
        le.setText(txt)
        le.setStyleSheet("padding: 6px 8px; background:#f7f7f7; border:1px solid #d7d7d7;")
        return le


# ---------------------------- DB Helpers ----------------------------


def fetch_all(sql: str, params: list | tuple = ()):
    """SELECT-Wrapper: gibt Liste von Dicts zurück."""
    """Return rows as list[dict]."""
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description] if cur.description else []
        rows = []
        for r in cur.fetchall():
            d = {}
            for i, c in enumerate(cols):
                d[c] = r[i]
            rows.append(d)
        return rows


# Saving edited cells (validation, UPDATEs, change history, Itemat recompute,
# fill row): db/series_save.py (Qt-free, shared with the web app).
import db.series_save as _series_save  # noqa: E402
from db.series_save import execute_non_query  # noqa: E402,F401  (moved there, still imported from here)


def table_exists(name: str) -> bool:
    """Gibt True zurück wenn die Tabelle in der DB existiert."""
    return _db_table_exists(name.lower())


def get_columns_map(table: str) -> Dict[str, str]:
    """Gibt {normierter_Name: echter_Name} für alle Spalten zurück."""
    """{lower_name: real_name}"""
    return _db_get_columns_map(table.lower())


# ------------------------ Pivot Table Model ------------------------

_RETEST_FLAG_DOT_ICON: Optional[QIcon] = None


def _retest_flag_dot_icon() -> QIcon:
    """Small red dot as a QIcon (cached) - column-header marker for open retest flags."""
    global _RETEST_FLAG_DOT_ICON
    if _RETEST_FLAG_DOT_ICON is not None:
        return _RETEST_FLAG_DOT_ICON
    pm = QPixmap(12, 12)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#D6432E"))
    p.drawEllipse(1, 1, 10, 10)
    p.end()
    _RETEST_FLAG_DOT_ICON = QIcon(pm)
    return _RETEST_FLAG_DOT_ICON


# Columns a trial copy starts with empty (measured tensions, comments):
# db/trial_actions.py (Qt-free, shared with the web app), re-exported here.
from db.trial_actions import (  # noqa: E402,F401
    COMMENT_COL_RE as _COMMENT_COL_RE,
    TENSION_COLS_NOT_COPIED as _TENSION_COLS_NOT_COPIED,
    col_not_copied as _col_not_copied,
)
import db.trial_actions as _trial_actions  # noqa: E402


# CellBinding / GroupCellBinding: db/series_tables.py (shared with the web app), re-exported here
from db.series_tables import CellBinding, GroupCellBinding  # noqa: E402,F401


_ALERT_ICONS: Dict[Tuple[str, bool], Any] = {}


def _alert_icon(kind: str, cb: bool):
    """Warning symbol for highlighted cells (Settings -> "Mark warnings with a
    symbol"): red = filled circle with "!", orange = triangle with "!" - the
    shape differs, so it also works without telling the colours apart."""
    key = (kind, cb)
    if key in _ALERT_ICONS:
        return _ALERT_ICONS[key]
    from PySide6.QtGui import QPainter, QPixmap, QPolygonF, QIcon
    from PySide6.QtCore import QPointF, QRectF
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    if kind == "red":
        fill = QColor("#000000") if cb else QColor("#C62828")
        p.setBrush(fill)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(4, 4, 56, 56))
        text_col = QColor("#FFFFFF")
    else:
        fill = QColor("#000000") if cb else QColor("#E65100")
        p.setBrush(fill)
        p.setPen(Qt.NoPen)
        p.drawPolygon(QPolygonF([QPointF(32, 3), QPointF(62, 60), QPointF(2, 60)]))
        text_col = QColor("#FFFFFF")
    f = QFont()
    f.setPixelSize(40)
    f.setBold(True)
    p.setFont(f)
    p.setPen(text_col)
    p.drawText(QRectF(0, 10 if kind != "red" else 2, 64, 56), Qt.AlignCenter, "!")
    p.end()
    icon = QIcon(pm)
    _ALERT_ICONS[key] = icon
    return icon


# Recycle bin preview (ui/recycle_preview.py): number of Show Experiment
# screens currently showing a series taken out of the recycle bin. Only then
# do the models look up their table's screen - no cost otherwise.
RECYCLE_PREVIEWS_OPEN = [0]


def _model_in_recycle_preview(model) -> bool:
    """True if the table showing `model` (FrozenFirstColumnTable sets
    _ffct_owner) sits in a Show Experiment screen in recycle bin preview."""
    ref = getattr(model, "_ffct_owner", None)
    w = ref() if ref is not None else None
    while w is not None:
        if getattr(w, "_recycle_preview", None) is not None:
            return True
        w = w.parentWidget()
    return False


class PivotEditModel(QAbstractTableModel):
    """Editierbares Pivot-Tabellenmodell für die Trial-Ansicht.

    Transponiert die DB-Struktur: Felder = Zeilen, Trials/Plies = Spalten.
    Jede Zelle hat eine CellBinding für direktes Speichern in die DB.

    Besonderheiten:
    - Ply-Spalten: mehrere Messungen pro Trial nebeneinander
    - Zellen-Validierung: Typ-Prüfung vor dem Speichern
    - Zellen-Alerts: visuelle Warnung bei ungültigem Inhalt
    - Read-Only-Zeilen: z.B. berechnete Felder
    - Zebrastreifen-Färbung (alternierend, Ply-abhängig)
    """
    """
    Zeilen = Parameter (linke Titelspalte),
    Spalten = Trials (V1..Vn).
    Linke Titelspalte ist Teil des Modells (Spalte 0).
    Editierbar sind nur Zellen mit vorhandenem Binding (und nicht in readonly-Zeilen).
    Optional: pro Zeile Validierungs-Regel (onlySZ / onlyInteger / onlyDoubles).

    _header_rows: optionale Liste von Dicts für pseudo-Header-Zeilen ganz oben:
        [{"values": ["", "V1","V1","V2","V2",...], "bg": QColor, "fg": QColor, "span_groups": [(start,span),...]}]
    """
    dataChangedExternally = Signal()

    # Farben als Properties – werden bei jedem Aufruf neu berechnet,
    # damit Akzentfarb-Wechsel nach Login sofort greift.
    _FG_BLACK = QColor("black")
    _HDR_BG_TRIAL = QColor("#3f3f3f")
    _HDR_FG = QColor("#ffffff")
    # Reference sample columns (customer originals, see db/trial_reference.py):
    # amber, deliberately independent of the user's accent colour.
    _REF_HDR_BG = QColor("#E8C15A")
    # even = the darker stripe, like accent_tint() vs accent_gridline() of
    # the regular trial columns (same phase as the neighbouring columns)
    _REF_EVEN = QColor("#FBE8B5")
    _REF_ODD = QColor("#FFF4D6")

    # Display settings (ui/display_prefs.py, passed in by FrozenFirstColumnTable)
    _CONTRAST_EVEN = QColor("#FFFFFF")
    _CONTRAST_ODD = QColor("#D0D0D0")
    _CROSS_LINE = QColor("#FFF3B8")    # row/column of the current cell
    _CROSS_LABEL = QColor("#FFD54F")   # its parameter name / trial number
    # Colour-blind friendly (Okabe-Ito): orange / yellow warnings on neutral
    # stripes, blue crosshair - plus symbols, so colour is never the only cue
    _CB_EVEN = QColor("#FFFFFF")
    _CB_ODD = QColor("#E6E6E6")
    _CB_RED_BG, _CB_RED_FG = QColor("#E69F00"), QColor("#000000")
    _CB_ORANGE_BG, _CB_ORANGE_FG = QColor("#F0E442"), QColor("#000000")
    _CB_CROSS_LINE = QColor("#CDE4F7")
    _CB_CROSS_LABEL = QColor("#7FB8E6")

    @property
    def _ALT_EVEN(self):
        if getattr(self, "_contrast", False):
            return self._CONTRAST_EVEN
        if getattr(self, "_cb", False):
            return self._CB_EVEN
        return QColor(accent_tint())

    @property
    def _ALT_ODD(self):
        if getattr(self, "_contrast", False):
            return self._CONTRAST_ODD
        if getattr(self, "_cb", False):
            return self._CB_ODD
        return QColor(accent_gridline())

    def _cell_font(self) -> QFont:
        f = getattr(self, "_base_font", None)
        return QFont(f) if f is not None else QFont()

    def set_display(self, font: QFont, contrast: bool, cross,
                    alert_marks: bool = False, cb_colours: bool = False) -> None:
        """Called by FrozenFirstColumnTable when the display settings change."""
        self._base_font = QFont(font)
        self._contrast = bool(contrast)
        self._cross = cross
        self._alert_marks = bool(alert_marks or cb_colours)
        self._cb = bool(cb_colours)
        self._emit_all(Qt.BackgroundRole, Qt.FontRole, Qt.ForegroundRole, Qt.DecorationRole)

    def cell_alert(self, r: int, c: int) -> Optional[str]:
        """"red" / "orange" / None for a view cell - same rules as the
        colouring in data() (CV >= 10, cell alerts). Used by the reading bar."""
        if r < self._n_hdr or c <= 0:
            return None
        dr = r - self._n_hdr
        if not (0 <= dr < len(self._row_titles)):
            return None
        title = self._row_titles[dr]
        if "Elongation CV" in title or "Tenacity CV" in title:
            raw = self._matrix[dr][c - 1]
            try:
                if raw not in (None, "") and float(str(raw).replace(",", ".")) >= 10.0:
                    return "red"
            except Exception:
                pass
        kind = self._cell_alerts.get((dr, c - 1))
        return kind if kind in ("red", "orange") else None

    def set_crosshair(self, cross) -> None:
        """cross = (view row, view column) of the current cell, or None."""
        if cross == getattr(self, "_cross", None):
            return
        self._cross = cross
        self._emit_all(Qt.BackgroundRole)

    def _emit_all(self, *roles) -> None:
        if self.rowCount() and self.columnCount():
            self.dataChanged.emit(self.index(0, 0),
                                  self.index(self.rowCount() - 1, self.columnCount() - 1), list(roles))

    def _cross_bg(self, r: int, c: int) -> Optional[QColor]:
        cross = getattr(self, "_cross", None)
        if not cross:
            return None
        cr, cc = cross
        # colour-blind mode: blue crosshair (yellow is used for warnings there)
        label, line = (self._CB_CROSS_LABEL, self._CB_CROSS_LINE) if getattr(self, "_cb", False) \
            else (self._CROSS_LABEL, self._CROSS_LINE)
        if r < self._n_hdr:
            return label if (c == cc and c > 0) else None
        if r == cr:
            return label if c == 0 else line
        if c == cc and c > 0:
            return line
        return None

    @property
    def _HDR_BG_PLY(self):
        return QColor(accent_gridline())

    def __init__(
            self,
            row_titles: List[str],
            col_titles: List[str],
            read_only_rows: Optional[set[int]] = None,
            row_validators: Optional[List[Optional[str]]] = None,
            global_readonly: bool = False,
            header_rows: Optional[List[Dict]] = None,
    ):
        super().__init__()
        self._row_titles = row_titles
        self._col_titles = col_titles
        self._global_readonly = bool(global_readonly)
        self._header_rows: List[Dict] = header_rows or []  # pseudo-header rows at top
        n_hdr = len(self._header_rows)
        self._n_hdr = n_hdr
        total_rows = n_hdr + len(row_titles)
        self._matrix: List[List[Optional[str]]] = [
            [None for _ in col_titles] for _ in row_titles
        ]
        self._binding: List[List[Optional[CellBinding]]] = [
            [None for _ in col_titles] for _ in row_titles
        ]
        self._dirty: List[Tuple[int, int, str]] = []
        self._readonly = read_only_rows or set()
        self._validators: List[Optional[str]] = row_validators or [
            None] * len(row_titles)
        # cell-level alert overrides: (dr, col_idx) -> "red" | "orange"
        self._cell_alerts: Dict[Tuple[int, int], str] = {}
        # cell-level tooltips: (dr, col_idx) -> tooltip string
        self._cell_tooltips: Dict[Tuple[int, int], str] = {}
        # Optionale Einheiten-Umrechnung: Anzeige/Eingabe in einer anderen
        # Einheit als in der DB gespeichert (z.B. l/min anzeigen, Nm3/h
        # speichern). display_value = db_value * unit_scale. Default 1.0 =
        # keine Umrechnung (betrifft alle anderen Tabs nicht).
        self._unit_scale: float = 1.0
        self._unit_scale_field: Optional[str] = None
        # col_idx (0-based, in _col_titles) -> tooltip text; see set_flagged_columns()
        self._flagged_cols: Dict[int, str] = {}
        # col_idx (0-based) -> tooltip; see set_reference_columns()
        self._reference_cols: Dict[int, str] = {}
        # Hidden data rows (see set_hidden_rows): stripes count visible rows only
        self._hidden_rows: set = set()
        self._stripe: Optional[List[int]] = None

    def set_hidden_rows(self, rows) -> None:
        """Data rows (0-based, as in _row_titles) that the view hides - the
        light/dark stripes are then counted over the visible rows only."""
        self._hidden_rows = set(rows or ())
        if not self._hidden_rows:
            self._stripe = None
        else:
            self._stripe, k = [], 0
            for dr in range(len(self._row_titles)):
                self._stripe.append(k % 2)
                if dr not in self._hidden_rows:
                    k += 1
        if self._row_titles:
            self.dataChanged.emit(self.index(self._n_hdr, 0),
                                  self.index(self.rowCount() - 1, self.columnCount() - 1),
                                  [Qt.BackgroundRole])

    def set_flagged_columns(self, mapping: Dict[int, str]) -> None:
        """Marks columns with a red dot in the column header (e.g. an open retest flag).

        mapping: {col_idx (0-based, as in col_titles): tooltip text}.
        """
        self._flagged_cols = dict(mapping or {})
        if self._col_titles:
            self.headerDataChanged.emit(Qt.Horizontal, 1, len(self._col_titles))

    def set_reference_columns(self, mapping: Dict[int, str]) -> None:
        """Highlights reference-sample columns (amber) - mapping: {col_idx
        (0-based, as in col_titles): tooltip text}."""
        self._reference_cols = dict(mapping or {})
        if self._col_titles:
            self.headerDataChanged.emit(Qt.Horizontal, 1, len(self._col_titles))

    def set_unit_scale(self, scale: float, field: Optional[str]) -> None:
        """Aktiviert Anzeige/Eingabe in einer umgerechneten Einheit fuer ein
        bestimmtes CellBinding-Feld (z.B. 'AirConsumption'). Beim Speichern
        (save_dirty) wird der eingegebene Wert durch `scale` geteilt, bevor
        er in die DB geschrieben wird - Anzeige bleibt in der gewaehlten
        Einheit, Speicherung immer im DB-Format."""
        self._unit_scale = scale if scale else 1.0
        self._unit_scale_field = field

    def insert_readonly_rows_at_top(self, rows: list) -> None:
        """Fügt read-only Header-Zeilen am Tabellenanfang ein (z.B. Experiment-ID-Zeile)."""
        """Fügt read-only Zeilen ganz oben ins Model ein (nach dem Befüllen aufrufen).
        rows: list of (label, [val_per_col])
        Verschiebt bestehende Daten nach unten, keine set_cell Anpassungen nötig.
        """
        n_new = len(rows)
        if n_new == 0:
            return
        n_cols = len(self._col_titles)
        # Prepend to matrix, binding, validators, row_titles
        new_matrix = [[str(v) if v is not None else "" for v in vals] for _lbl, vals in rows]
        new_binding = [[None] * n_cols for _ in rows]
        new_titles = [lbl for lbl, _vals in rows]
        new_validators = [None] * n_new
        self._matrix = new_matrix + self._matrix
        self._binding = new_binding + self._binding
        self._row_titles = new_titles + self._row_titles
        self._validators = new_validators + self._validators
        # Shift existing readonly row indices up
        self._readonly = {r + n_new for r in self._readonly} | set(range(n_new))
        # info rows (jet, air pressure ...) - not measurements (ui/ref_compare_dialog.py)
        self._n_info_rows = int(getattr(self, "_n_info_rows", 0) or 0) + n_new
        # Shift dirty indices
        self._dirty = [(r + n_new, c, v) for r, c, v in self._dirty]
        if getattr(self, "_undo_mgr", None) is not None:
            self._undo_mgr.clear()  # row numbers changed - old undo steps would hit the wrong rows
        self.layoutChanged.emit()

    def set_cell_alert(self, row: int, col: int, style: str) -> None:
        """Setzt einen visuellen Alert (Hintergrundfarbe) für eine Zelle."""
        """Setzt einen visuellen Alert für Datenzelle (row, col) (0-basiert, ohne Header-Offset).
        style: 'red' oder 'orange'
        """
        self._cell_alerts[(row, col)] = style

    def clear_cell_alerts(self) -> None:
        """Löscht alle Zellen-Alerts."""
        self._cell_alerts.clear()

    # Unsaved cells (Nutzerwunsch 2026-10-16): light yellow until saved.
    _DIRTY_BG = QColor("#FFF1A8")
    _DIRTY_TIP = "Changed - not saved yet"

    def _set_dirty_value(self, r: int, c: int, new: str) -> None:
        """The one place that changes a cell value as an unsaved edit:
        matrix + _dirty, and an undo step (Ctrl+Z, _UndoManager) if the
        screen attached one."""
        old = self._matrix[r][c]
        self._matrix[r][c] = new
        self._dirty.append((r, c, new))
        mgr = getattr(self, "_undo_mgr", None)
        if mgr is not None:
            mgr.record(self, r, c, old, new)

    def dirty_cells(self) -> set:
        """{(data row, data col)} of cells changed since the last save. _dirty
        is appended to in many places and replaced/cleared on save - cached
        by (list identity, length) so data() stays cheap."""
        d = self._dirty
        key = (id(d), len(d))
        if getattr(self, "_dirty_key", None) != key:
            self._dirty_key = key
            self._dirty_set = {(r, c) for r, c, *_ in d}
        return self._dirty_set

    def _ctx_is_readonly(self) -> bool:
        """Gibt True zurück wenn der Screen im Read-Only-Modus ist."""
        if RECYCLE_PREVIEWS_OPEN[0] and _model_in_recycle_preview(self):
            return True
        try:
            lvl = int(getattr(app_meta, "access_level", lambda: 0)() or 0)
        except Exception:
            try:
                user = getattr(app_meta, "current_user", {}) or {}
                lvl = int(user.get("access_level")
                          or user.get("AccessLevel") or 0)
            except Exception:
                lvl = 0
        return bool(getattr(self, "_global_readonly", False)) or (lvl <= 1)

    def rowCount(self, parent=QModelIndex()) -> int:  # type: ignore[override]
        """Gibt die Anzahl Zeilen (= Felder) zurück."""
        return self._n_hdr + len(self._row_titles)

    def columnCount(self, parent=QModelIndex()) -> int:  # type: ignore[override]
        """Gibt die Anzahl Spalten (= Trials × Plies) zurück."""
        return 1 + len(self._col_titles)

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # type: ignore[override]
        """Gibt Kopfzeile/Kopfspalte zurück (Feldnamen vertikal, Trial-IDs horizontal)."""
        if orientation == Qt.Horizontal and section > 0:
            col_idx = section - 1
            note = self._flagged_cols.get(col_idx)
            if note is not None:
                if role == Qt.DecorationRole:
                    return _retest_flag_dot_icon()
                if role == Qt.ToolTipRole:
                    return note or "Retest pending"
            if role == Qt.ToolTipRole and col_idx in self._reference_cols:
                return self._reference_cols[col_idx]
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return "" if section == 0 else self._col_titles[section - 1]
        return section + 1

    def flags(self, index: QModelIndex):  # type: ignore[override]
        """Read-Only-Zeilen und CellBindings ohne Spalte sind nicht editierbar."""
        if not index.isValid():
            return Qt.NoItemFlags
        # pseudo-header rows: never editable
        if index.row() < self._n_hdr:
            return Qt.ItemIsEnabled
        r = index.row() - self._n_hdr
        if index.column() == 0:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if self._ctx_is_readonly():
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if r in self._readonly:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        has_binding = (
                0 <= r < len(self._binding)
                and 0 <= (index.column() - 1) < len(self._binding[r])
                and self._binding[r][index.column() - 1] is not None
        )
        return (Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable) if has_binding \
            else (Qt.ItemIsEnabled | Qt.ItemIsSelectable)

    # ---- Validation helpers (rules: db/series_save.normalize_value / normalize_input) ----
    _re_int = _series_save.RE_INT
    _re_float_like = _series_save.RE_FLOAT_LIKE
    _re_float_2dp = _series_save.RE_FLOAT_2DP

    def _validate_and_normalize(self, row: int, text_in: Any) -> Optional[str]:
        """Normalisierter String, "" wenn leer (-> NULL), None wenn invalid -
        nach der Regel der Zeile (db/series_save.normalize_value)."""
        rule = self._validators[row] if 0 <= row < len(
            self._validators) else None
        return _series_save.normalize_value(rule, text_in)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):  # type: ignore[override]
        """Liefert Zelldaten: Wert, Hintergrundfarbe (Ply-abhängig + Alerts), Alignment."""
        if not index.isValid():
            return None
        r, c = index.row(), index.column()

        # ── pseudo-header rows ────────────────────────────────────────────
        if r < self._n_hdr:
            hdr = self._header_rows[r]
            _is_ref_col = c > 0 and (c - 1) in self._reference_cols
            if role == Qt.BackgroundRole:
                _xb = self._cross_bg(r, c)
                if _xb is not None:
                    return _xb
                if _is_ref_col:
                    return self._REF_HDR_BG
                bg = hdr.get("bg")
                if bg is None:
                    return self._ALT_EVEN if (r % 2 == 0) else self._ALT_ODD
                return bg
            if role == Qt.ForegroundRole:
                fg = hdr.get("fg")
                return fg if fg is not None else self._FG_BLACK
            if role == Qt.DisplayRole:
                vals = hdr.get("values", [])
                return vals[c] if c < len(vals) else ""
            if role == Qt.DecorationRole:
                # colour square of the yarn in the ply header row (Nutzerwunsch 2026-10-22)
                colours = hdr.get("colours") or []
                colour = colours[c] if c < len(colours) else ""
                if not colour:
                    return None
                from ui.widgets.yarn_colour import colour_icon
                return colour_icon(colour)
            if role == Qt.ToolTipRole:
                tips = hdr.get("tooltips", [])
                tip = tips[c] if c < len(tips) else ""
                if not tip and _is_ref_col:
                    tip = self._reference_cols[c - 1]
                colours = hdr.get("colours") or []
                colour = colours[c] if c < len(colours) else ""
                if colour:
                    tip = f"{tip}\nColour: {colour}" if tip else f"Colour: {colour}"
                return tip if tip else None
            if role == Qt.TextAlignmentRole:
                return Qt.AlignCenter
            if role == Qt.FontRole:
                f = self._cell_font()
                f.setBold(True)
                return f
            return None

        # ── normal data rows ──────────────────────────────────────────────
        dr = r - self._n_hdr  # index into _row_titles / _matrix

        # Alert-Berechnung (Elongation/Tenacity-CV-Grenzwert, Zellen-Alerts) wird
        # nur für die Rollen gebraucht, die sie tatsächlich auswerten
        # (Background/Foreground/Font). Für alle anderen Rollen (v.a.
        # DisplayRole/TextAlignmentRole, die bei resizeColumnsToContents()
        # o.ä. sehr oft aufgerufen werden) lohnt sich das Parsing nicht.
        if role in (Qt.BackgroundRole, Qt.ForegroundRole, Qt.FontRole, Qt.DecorationRole):
            # Elongation CV highlight: Wert >= 10 -> rot + fett + heller Rohhintergrund
            _is_elong_cv_alert = False
            # Tenacity CV highlight: Wert >= 10 -> rot + fett + heller Rohhintergrund (analog Elongation CV)
            _is_ten_cv_alert = False
            if c > 0 and 0 <= dr < len(self._row_titles):
                # rule shared with the web app (db/series_tables.cv_limit_alert)
                _is_elong_cv_alert = _series_tables.cv_limit_alert(self._row_titles[dr], self._matrix[dr][c - 1])

            # cell-level alert (Titer out-of-tolerance, Tenacity orange, etc.)
            _cell_alert = self._cell_alerts.get((dr, c - 1)) if c > 0 else None

            _cb = getattr(self, "_cb", False)
            _red = _is_elong_cv_alert or _is_ten_cv_alert or _cell_alert == "red"
            if role == Qt.DecorationRole:
                if getattr(self, "_alert_marks", False) and (_red or _cell_alert == "orange"):
                    return _alert_icon("red" if _red else "orange", _cb)
                return None
            if role == Qt.BackgroundRole:
                if _red:
                    return self._CB_RED_BG if _cb else QColor("#FFD0D0")  # helles Rot
                if _cell_alert == "orange":
                    return self._CB_ORANGE_BG if _cb else QColor("#FFE5B4")  # helles Orange
                if c > 0 and self._dirty and (dr, c - 1) in self.dirty_cells():
                    return self._DIRTY_BG
                _xb = self._cross_bg(r, c)
                if _xb is not None:
                    return _xb
                _odd = self._stripe[dr] if self._stripe and dr < len(self._stripe) else dr % 2
                if c > 0 and (c - 1) in self._reference_cols:
                    return self._REF_EVEN if _odd == 0 else self._REF_ODD
                return self._ALT_EVEN if _odd == 0 else self._ALT_ODD
            if role == Qt.ForegroundRole:
                if _red:
                    return self._CB_RED_FG if _cb else QColor("#CC0000")  # kräftiges Rot
                if _cell_alert == "orange":
                    return self._CB_ORANGE_FG if _cb else QColor("#B85C00")  # dunkel Orange
                return self._FG_BLACK
            if role == Qt.FontRole:
                if _is_elong_cv_alert or _is_ten_cv_alert or _cell_alert in ("red", "orange"):
                    f = self._cell_font()
                    f.setBold(True)
                    return f
                return None
        if role in (Qt.DisplayRole, Qt.EditRole):
            if c == 0:
                return self._row_titles[dr]
            val = self._matrix[dr][c - 1]
            return "" if val is None else val
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter if c > 0 else (Qt.AlignVCenter | Qt.AlignLeft)
        if role == Qt.ToolTipRole and c > 0:
            tip = self._cell_tooltips.get((dr, c - 1))
            if self._dirty and (dr, c - 1) in self.dirty_cells():
                tip = f"{tip}\n{self._DIRTY_TIP}" if tip else self._DIRTY_TIP
            return tip if tip else None
        return None

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):  # type: ignore[override]
        """Speichert einen Zellwert direkt in die DB via CellBinding."""
        if self._ctx_is_readonly():
            return False
        if not index.isValid() or role != Qt.EditRole or index.column() == 0:
            return False
        if index.row() < self._n_hdr:
            return False
        r = index.row() - self._n_hdr
        if r in self._readonly:
            return False
        if self._binding[r][index.column() - 1] is None:
            return False

        normalized = self._validate_and_normalize(
            r, "" if value is None else str(value))
        if normalized is None:
            return False
        title = self._row_titles[r] if 0 <= r < len(self._row_titles) else None
        normalized = _series_save.apply_row_title_rule(title, normalized)  # "Air Pressure (bar)": 2 decimals
        if normalized is None:
            return False

        r, c = index.row() - self._n_hdr, index.column() - 1
        if self._matrix[r][c] == normalized:
            return True
        self._set_dirty_value(r, c, normalized)
        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
        return True

    def set_cell(self, row: int, col: int, value: Any, binding: Optional[CellBinding]):
        """Setzt Wert und Binding einer Zelle (beim Laden der Daten)."""
        self._matrix[row][col] = "" if value is None else str(value)
        self._binding[row][col] = binding
        # value as loaded - save conflict check (db/series_save.find_conflicts) against changes by others
        if not hasattr(self, "_loaded"):
            self._loaded = {}
        self._loaded[(row, col)] = self._matrix[row][col]

    def get_cell_value(self, row: int, col: int) -> Optional[str]:
        if 0 <= row < len(self._matrix) and 0 <= col < len(self._matrix[row]):
            return self._matrix[row][col]
        return None

    def get_binding(self, row: int, col: int) -> Optional[CellBinding]:
        if 0 <= row < len(self._binding) and 0 <= col < len(self._binding[row]):
            return self._binding[row][col]
        return None

    # Notes on values (db/cell_notes.py, ui/cell_notes_ui.py). Set by the
    # screen: _notes_by_key {(table, row id, field): [notes]} for data cells,
    # _note_trial_cols {col (0-based): [notes]} for whole-trial notes, shown
    # in header row 0 (trial number) of the machine tables.
    _notes_by_key = None
    _note_trial_cols = None

    def notes_at(self, r: int, c: int) -> list:
        """Notes of a view cell (row/column as in the view, column 0 = titles)."""
        by_key = self._notes_by_key
        if by_key is None or c <= 0:
            return []
        if r < self._n_hdr:
            return list((self._note_trial_cols or {}).get(c - 1, [])) if r == 0 else []
        # rule shared with the web app (db/cell_notes.notes_for_binding)
        from db.cell_notes import notes_for_binding
        return notes_for_binding(by_key, self.get_binding(r - self._n_hdr, c - 1))

    def save_dirty(self) -> int:
        """Schreibt alle geänderten Zellen in die DB (db/series_save.save_cells:
        GroupCellBinding, Labortabellen mit [User]/[Timestamp], Einheiten-
        Umrechnung, Änderungsprotokoll, DYRatio)."""
        # einfacher Cache pro Modellinstanz, damit get_columns_map()
        # nicht für jede einzelne Zelle erneut aufgerufen wird
        cache = getattr(self, "_lab_audit_cache", None)
        if cache is None:
            cache = {}
            self._lab_audit_cache = cache

        try:
            user = getattr(app_meta, "current_user", {}) or {}
        except Exception:
            user = {}
        if not isinstance(user, dict):
            user = {}

        n = _series_save.save_cells(
            [(self._binding[r][c], new_text) for r, c, new_text in self._dirty],
            user=user,
            series_id=getattr(self, "_log_series_id", None),
            source=getattr(self, "_log_source", "edit"),
            unit_scale=self._unit_scale,
            unit_field=self._unit_scale_field,
            audit_cache=cache,
        )

        # what was just written is the new "as loaded" (next conflict check compares with it)
        loaded = getattr(self, "_loaded", None)
        if loaded is not None:
            for r, c, new_text in self._dirty:
                loaded[(r, c)] = "" if new_text is None else str(new_text)
        self._dirty.clear()
        self.dataChangedExternally.emit()
        return n

    def conflict_items(self) -> list:
        """Dirty cells for db/series_save.find_conflicts: binding, value as loaded, new text, where."""
        out = []
        loaded = getattr(self, "_loaded", {}) or {}
        seen = set()
        for r, c, new_text in reversed(self._dirty):        # last edit of a cell wins
            if (r, c) in seen or (r, c) not in loaded:
                continue
            seen.add((r, c))
            title = str(self.data(self.index(self._n_hdr + r, 0), Qt.DisplayRole) or "")
            col = " · ".join(x for x in (str(self.data(self.index(h, c + 1), Qt.DisplayRole) or "").strip()
                                         for h in range(self._n_hdr)) if x)
            out.append({"binding": self._binding[r][c], "loaded": loaded[(r, c)], "new": new_text,
                        "where": f"{col} · {title}" if col else title})
        return out


# ---------------------------- Screen ----------------------------


# ------------------------ Machine Pivot Model + Delegate ------------------------

class MachinePivotModel(PivotEditModel):
    """
    Spezialisierte PivotEditModel-Variante für den Machine-Tab.
    Zeile 0 = Housing (Dropdown, speichert HousingID).
    Zeile 1 = Jet     (Dropdown, speichert JetID).
    """

    def __init__(
            self,
            jets_map: Dict[Any, str],
            row_titles: List[str],
            col_titles: List[str],
            read_only_rows: Optional[set[int]] = None,
            row_validators: Optional[List[Optional[str]]] = None,
            jet_row_index: int = 1,
            header_rows: Optional[List[Dict]] = None,
            housing_map: Optional[Dict[Any, str]] = None,
            housing_row_index: int = 0,
            jets_tooltip_map: Optional[Dict[Any, str]] = None,
            housing_image_map: Optional[Dict[Any, str]] = None,
            dropdown_rows: Optional[Dict[int, Dict[Any, str]]] = None,
    ):
        self._jets_map = jets_map or {}
        self._jet_row_index = jet_row_index  # 0-based index in _row_titles
        self._housing_map = housing_map or {}
        self._housing_row_index = housing_row_index  # 0-based index in _row_titles
        self._jets_tooltip_map = jets_tooltip_map or {}
        self._housing_image_map = housing_image_map or {}
        # dropdown_rows: {row_index (0-based in _row_titles) → {id → name}}
        self._dropdown_rows: Dict[int, Dict[Any, str]] = dropdown_rows or {}
        super().__init__(
            row_titles=row_titles,
            col_titles=col_titles,
            read_only_rows=read_only_rows,
            row_validators=row_validators,
            header_rows=header_rows,
        )

    def _id_display(self, lookup_map: Dict[Any, str], internal) -> str:
        """Return display name for an ID stored internally (db/machine_data.id_display)."""
        return _machine_data.id_display(lookup_map, internal)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if index.isValid() and index.row() < self._n_hdr:
            return super().data(index, role)
        if (
                index.isValid()
                and role in (Qt.DisplayRole, Qt.EditRole)
                and index.column() > 0
        ):
            r = index.row() - self._n_hdr
            c = index.column() - 1
            internal = self._matrix[r][c] if 0 <= r < len(
                self._matrix) and 0 <= c < len(self._matrix[r]) else None
            # Housing row
            if index.row() == self._n_hdr + self._housing_row_index:
                return self._id_display(self._housing_map, internal)
            # Jet row
            if index.row() == self._n_hdr + self._jet_row_index:
                return self._id_display(self._jets_map, internal)
            # Generische Dropdown-Zeilen (z.B. DiscID)
            drow_idx = index.row() - self._n_hdr
            if drow_idx in self._dropdown_rows:
                return self._id_display(self._dropdown_rows[drow_idx], internal)
        # Tooltip for jet row
        if (
                index.isValid()
                and role == Qt.ToolTipRole
                and index.column() > 0
        ):
            data_row = index.row() - self._n_hdr
            jet_rows = getattr(self, "_all_jet_rows", {self._jet_row_index})
            if data_row in jet_rows:
                r = data_row
                c = index.column() - 1
                internal = self._matrix[r][c] if 0 <= r < len(
                    self._matrix) and 0 <= c < len(self._matrix[r]) else None
                if internal not in (None, ""):
                    try:
                        jid = int(internal)
                    except Exception:
                        jid = internal
                    tip = (self._jets_tooltip_map.get(jid)
                           or self._jets_tooltip_map.get(str(jid)))
                    if tip:
                        return tip
        # Tooltip for housing rows — Bildpfad für Event-Filter
        # Covers primary housing row + extra housing rows (R&D: W3 Housing, PreIntermingling Housing)
        if (
                index.isValid()
                and role == Qt.ToolTipRole
                and index.column() > 0
        ):
            data_row = index.row() - self._n_hdr
            housing_rows = getattr(self, "_all_housing_rows", {self._housing_row_index})
            if data_row in housing_rows:
                r, c = data_row, index.column() - 1
                internal = self._matrix[r][c] if 0 <= r < len(
                    self._matrix) and 0 <= c < len(self._matrix[r]) else None
                if internal not in (None, ""):
                    try:
                        hid = int(internal)
                    except Exception:
                        hid = internal
                    img_path = (self._housing_image_map.get(hid)
                                or self._housing_image_map.get(str(hid)))
                    if img_path:
                        return img_path
        # Tooltip for OF row — computed speed as plain text
        if (
                index.isValid()
                and role == Qt.ToolTipRole
                and index.column() > 0
        ):
            data_row = index.row() - self._n_hdr
            of_row = getattr(self, "_of_tooltip_row", None)
            if of_row is not None and data_row == of_row:
                of_calc = getattr(self, "_of_tooltip_calc", None)
                if callable(of_calc):
                    tip = of_calc(index.column() - 1)
                    if tip:
                        return tip
        return super().data(index, role)

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        if (
                index.isValid()
                and role == Qt.EditRole
                and index.column() > 0
        ):
            # Housing row
            if index.row() == self._n_hdr + self._housing_row_index:
                new_val = _series_save.normalize_input(None, None, value, kind="housing")
                r = index.row() - self._n_hdr
                c = index.column() - 1
                if 0 <= r < len(self._matrix) and 0 <= c < len(self._matrix[r]):
                    if self._matrix[r][c] == new_val:
                        return True
                    self._set_dirty_value(r, c, new_val)
                    self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
                    return True
                return False
            # Jet row
            if index.row() == self._n_hdr + self._jet_row_index:
                new_val = _series_save.normalize_input(None, None, value, kind="jet")
                if new_val is None:
                    return False
                r = index.row() - self._n_hdr
                c = index.column() - 1
                if 0 <= r < len(self._matrix) and 0 <= c < len(self._matrix[r]):
                    current = self._matrix[r][c]
                    if current == new_val:
                        return True
                    self._set_dirty_value(r, c, new_val)
                    self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
                    return True
                return False

        return super().setData(index, value, role)

    def get_dropdown_map(self, row_index_0based: int) -> Optional[Dict[Any, str]]:
        """Gibt die Lookup-Map für eine generische Dropdown-Zeile zurück."""
        return self._dropdown_rows.get(row_index_0based)


class JetComboDelegate(QStyledItemDelegate):
    """Delegate für die Jet-Zeile: zeigt einen QComboBox mit allen Jets aus tblDTYJets an."""

    def __init__(self, jets_list: List[Tuple[Any, str]], parent=None):
        super().__init__(parent)
        self._jets_list = jets_list or []

    def createEditor(self, parent, option, index):
        # Nur auf der Jet-Datenzeile (nicht Titel-Spalte, nicht pseudo-Header)
        model = index.model()
        n_hdr = getattr(model, "_n_hdr", 0)
        jet_row = getattr(model, "_jet_row_index", 1)
        if index.column() == 0 or index.row() != n_hdr + jet_row:
            return None
        cb = QComboBox(parent)
        cb.setEditable(False)
        cb.setInsertPolicy(QComboBox.NoInsert)
        cb.setMinimumWidth(160)
        for jet_id, jet_name in self._jets_list:
            cb.addItem(str(jet_name), jet_id)
        return cb

    def setEditorData(self, editor, index):
        if not isinstance(editor, QComboBox):
            return
        current_text = str(index.data(Qt.DisplayRole) or "")
        # passenden Eintrag anhand des angezeigten Jet-Namens finden
        i = editor.findText(current_text)
        if i >= 0:
            editor.setCurrentIndex(i)

    def setModelData(self, editor, model, index):
        if not isinstance(editor, QComboBox):
            return
        jet_id = editor.currentData()
        model.setData(index, jet_id, Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class HousingComboDelegate(QStyledItemDelegate):
    """Delegate für die Housing-Zeile: zeigt einen QComboBox mit allen Housings aus tblHousing an."""

    def __init__(self, housing_list: List[Tuple[Any, str]], parent=None):
        super().__init__(parent)
        self._housing_list = housing_list or []

    def createEditor(self, parent, option, index):
        model = index.model()
        n_hdr = getattr(model, "_n_hdr", 0)
        housing_row = getattr(model, "_housing_row_index", 0)
        if index.column() == 0 or index.row() != n_hdr + housing_row:
            return None
        cb = QComboBox(parent)
        cb.setEditable(False)
        cb.setInsertPolicy(QComboBox.NoInsert)
        cb.setMinimumWidth(160)
        cb.addItem("", None)
        for housing_id, housing_name in self._housing_list:
            cb.addItem(str(housing_name), housing_id)
        return cb

    def setEditorData(self, editor, index):
        if not isinstance(editor, QComboBox):
            return
        current_text = str(index.data(Qt.DisplayRole) or "")
        i = editor.findText(current_text)
        if i >= 0:
            editor.setCurrentIndex(i)

    def setModelData(self, editor, model, index):
        if not isinstance(editor, QComboBox):
            return
        housing_id = editor.currentData()
        model.setData(index, housing_id, Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class LookupComboDelegate(QStyledItemDelegate):
    """Generischer Delegate für Dropdown-Zeilen aus einer Lookup-Tabelle (z.B. tblDisc).

    row_index: 0-basierter Index in _row_titles (nicht Model-Zeile).
    lookup_list: [(id, name), ...] — wie bei Housing/Jet.
    """

    def __init__(self, row_index: int, lookup_list: List[Tuple[Any, str]], parent=None):
        super().__init__(parent)
        self._row_index = row_index
        self._lookup_list = lookup_list or []

    def createEditor(self, parent, option, index):
        if index.column() == 0:
            return None
        cb = QComboBox(parent)
        cb.setEditable(False)
        cb.setInsertPolicy(QComboBox.NoInsert)
        cb.setMinimumWidth(160)
        cb.addItem("", None)
        for lid, lname in self._lookup_list:
            cb.addItem(str(lname), lid)
        return cb

    def setEditorData(self, editor, index):
        if not isinstance(editor, QComboBox):
            return
        current_text = str(index.data(Qt.DisplayRole) or "")
        i = editor.findText(current_text)
        if i >= 0:
            editor.setCurrentIndex(i)

    def setModelData(self, editor, model, index):
        if not isinstance(editor, QComboBox):
            return
        model.setData(index, editor.currentData(), Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


def _add_cell_history_action(screen, model, index, menu) -> None:
    """Adds "Change history…" for a value (db/change_log.py) - superusers
    only (Nutzerentscheid 2026-10-15)."""
    if model is None or not hasattr(model, "get_binding"):
        return
    from ui.change_history_dialog import can_view_history
    if not can_view_history():
        return
    act = menu.addAction("Change history…")
    act.triggered.connect(lambda: _open_cell_history(screen, model, index))


def _open_cell_history(screen, model, index) -> None:
    from ui.change_history_dialog import show_cell_history
    show_cell_history(screen, model, index)


def _show_experiment_cell_menu(table, index, menu) -> None:
    """FrozenFirstColumnTable.cell_menu_hook: right-click on a value."""
    w = table.parent()
    while w is not None and not isinstance(w, ShowExperimentScreen):
        w = w.parent()
    if w is None:
        return
    _cell_notes_ui.add_cell_note_actions(w, table.model(), index, menu)
    _add_cell_history_action(w, table.model(), index, menu)
    from ui import kb_links
    if table is getattr(w, "tbl_machine", None) or table is getattr(w, "tbl_rd_machine", None):
        is_rd = table is getattr(w, "tbl_rd_machine", None)
        target = kb_links.machine_cell_target(w, table.model(), index, is_rd)
        kb_links.add_action(menu, w, target, "rd_machine_data" if is_rd else "machine_data")
    else:
        kb_links.add_action(menu, w, kb_links.table_target(w, table), "lab")


def _view_row_hidden(table, row: int) -> bool:
    """True if the (data) row is hidden in the table's main view (e.g. rows
    hidden by the user in Machine Data, see ui/machine_row_visibility.py)."""
    view = getattr(table, "right", table)
    try:
        return bool(view.isRowHidden(row)) and row >= int(getattr(view.model(), "_n_hdr", 0) or 0)
    except Exception:
        return False


class _MachineContextMenuFilter(QObject):
    """Event-Filter, der Rechtsklick auf die Titelspalte der Machine-Tabelle abfängt."""

    def __init__(self, screen, table, is_rd: bool = False):
        super().__init__(table)
        self._screen = screen
        self._table = table
        self._is_rd = is_rd

    def eventFilter(self, obj, event):
        if event.type() != QEvent.ContextMenu:
            return False

        # Pass nur weiter, wenn wir ein gültiges Model haben
        _model_attr = 'model_rd_machine' if self._is_rd else 'model_machine'
        if not getattr(self._screen, _model_attr, None):
            return False

        # obj ist die QTableView (left oder right) selbst.
        # ContextMenu-Event.pos() ist relativ zur View → in Viewport-Koordinaten umrechnen.
        if not isinstance(obj, QTableView):
            return False
        view = obj
        viewport_pos = view.viewport().mapFrom(view, event.pos())
        index = view.indexAt(viewport_pos)
        if not index.isValid():
            return False

        row = index.row()
        col = index.column()

        # ── Rechtsklick auf V-Nummer-Header-Zeile (Zeile 0, Spalte > 0) ──────
        # Pseudo-Header Zeile 0 enthält die Versuchsnummern; der Qt-Column-Header
        # ist ausgeblendet, daher muss die Vervielfältigung hier abgefangen werden.
        if row == 0 and col > 0:
            # col-1 = Index in col_specs (Spalte 0 = Zeilentitel)
            self._screen._on_trial_header_menu(col - 1, event.globalPos(), is_rd=self._is_rd)
            return True

        # ── Rechtsklick auf Ply-Label-Zeile (Zeile 1, Spalte > 0) ────────────
        if row == 1 and col > 0:
            self._screen._manage_plies_for_col_spec_idx(col - 1)
            return True

        # ── Rechtsklick auf Titelspalte (Spalte 0) ────────────────────────────
        if col == 0:
            from PySide6.QtWidgets import QMenu
            menu = QMenu()
            # Zeile befüllen (nur wenn nicht Header-Zeile)
            n_hdr = getattr(getattr(self._screen, _model_attr, None), '_n_hdr', 0)
            if row >= n_hdr:
                act_fill = menu.addAction("Fill row")
            else:
                act_fill = None
            # Hide / show rows (Machine Data only, see ui/machine_row_visibility.py)
            row_actions = {}
            if not self._is_rd:
                from ui import machine_row_visibility as _mrv
                row_actions = _mrv.add_context_actions(self._screen, menu, row)
            # Custom Group Toggle
            menu.addSeparator()
            cg_visible = getattr(self._screen, '_custom_group_visible', False)
            act_cg = menu.addAction(
                "Hide Custom Group" if cg_visible else "Show Custom Group"
            )
            if row >= n_hdr:
                from ui import kb_links
                kb_links.add_action(menu, self._screen,
                                    kb_links.machine_row_target(self._screen, row, self._is_rd),
                                    "rd_machine_data" if self._is_rd else "machine_data")
            chosen = menu.exec(event.globalPos())
            if act_fill and chosen == act_fill:
                self._screen._fill_machine_row_from_title(row, is_rd=self._is_rd)
            elif chosen == act_cg:
                self._screen._toggle_custom_group_row()
            elif chosen in row_actions:
                row_actions[chosen]()
            return True

        _tbl_attr = "tbl_rd_machine" if self._is_rd else "tbl_machine"
        try:
            right_view = getattr(
                getattr(self._screen, _tbl_attr, None), "right", None
            )
            if right_view is not None and view is right_view:
                span = right_view.columnSpan(row, col)
                if span > 1:
                    from PySide6.QtWidgets import QMenu
                    menu = QMenu()
                    act_fill = menu.addAction("Fill row…")
                    _add_cell_history_action(self._screen, getattr(self._screen, _model_attr),
                                             right_view.model().index(row, col), menu)
                    chosen = menu.exec(event.globalPos())
                    if chosen == act_fill:
                        self._screen._fill_machine_row_from_title(row, is_rd=self._is_rd)
                    return True
        except Exception:
            pass

        return False


class _HousingImageTooltipFilter(QObject):
    """Event-Filter: zeigt Bild-Tooltip für Housing-Zeile aus tblHousing.Link,
    UND generische Text-Tooltips (z.B. Spool-Zeile) fuer alle anderen Zeilen
    mit einem Eintrag in model._cell_tooltips.

    Wichtig: Qt's eingebauter Tooltip-Mechanismus (ueber data(Qt.ToolTipRole))
    wird von diesem Filter fuer die GESAMTE Tabelle abgefangen (er ist auf
    dem Viewport installiert), auch fuer Zeilen, die er selbst nicht behandelt
    - dort gibt er zwar False zurueck, aber Qt's Default-Tooltip springt
    danach nicht zuverlaessig wieder ein. Daher muss dieser Filter JEDEN
    Tooltip-Fall, den die Tabelle braucht, selbst abdecken.
    """

    def __init__(self, screen, table, parent=None):
        super().__init__(parent)
        self._screen = screen
        self._table = table

    def eventFilter(self, obj, event):
        if event.type() != QEvent.ToolTip:
            return False
        view = obj.parent() if hasattr(obj, 'parent') else None
        if not isinstance(view, QTableView):
            return False
        model = getattr(self._screen, "model_machine", None)
        if model is None:
            return False
        index = view.indexAt(event.pos())
        if not index.isValid() or index.column() == 0:
            return False
        n_hdr = getattr(model, "_n_hdr", 0)
        housing_row = getattr(model, "_housing_row_index", 0)
        if index.row() == n_hdr + housing_row:
            img_path = model.data(index, Qt.ToolTipRole)
            if not img_path or not isinstance(img_path, str) or not img_path.strip():
                QToolTip.hideText()
                return True
            if not os.path.isfile(img_path):
                QToolTip.hideText()
                return True
            html = f'<img src="{img_path}" style="max-width:320px; max-height:320px;" />'
            QToolTip.showText(event.globalPos(), html, view)
            return True
        # Generischer Text-Tooltip (z.B. Spool-Zeile, Plies-Zeile) ueber
        # model._cell_tooltips - dieselbe Quelle, die data(Qt.ToolTipRole)
        # normalerweise liefern wuerde.
        dr = index.row() - n_hdr
        c = index.column() - 1
        tip = getattr(model, "_cell_tooltips", {}).get((dr, c))
        if tip:
            QToolTip.showText(event.globalPos(), tip, view)
            return True
        return False


class _RDHousingTooltipFilter(QObject):
    """Bild-Tooltip für Housing-Zeilen im R&D Machine Data Tab.
    Identisch zu _HousingImageTooltipFilter aber für model_rd_machine,
    und prüft alle Zeilen in model._all_housing_rows.
    """

    def __init__(self, screen, table, parent=None):
        super().__init__(parent)
        self._screen = screen
        self._table = table

    def eventFilter(self, obj, event):
        if event.type() != QEvent.ToolTip:
            return False
        view = obj.parent() if hasattr(obj, 'parent') else None
        if not isinstance(view, QTableView):
            return False
        model = getattr(self._screen, "model_rd_machine", None)
        if model is None:
            return False
        index = view.indexAt(event.pos())
        if not index.isValid() or index.column() == 0:
            return False
        n_hdr = getattr(model, "_n_hdr", 0)
        data_row = index.row() - n_hdr
        all_housing = getattr(model, "_all_housing_rows", set())
        if data_row not in all_housing:
            return False
        img_path = model.data(index, Qt.ToolTipRole)
        if not img_path or not isinstance(img_path, str) or not img_path.strip():
            QToolTip.hideText()
            return True
        if not os.path.isfile(img_path):
            QToolTip.hideText()
            return True
        html = f'<img src="{img_path}" style="max-width:320px; max-height:320px;" />'
        QToolTip.showText(event.globalPos(), html, view)
        return True


class _UndoManager:
    """Ctrl+Z / Ctrl+Y for unsaved cell edits in Show Experiment
    (Nutzerwunsch 2026-10-16). Every change goes through
    PivotEditModel._set_dirty_value() -> record(). All changes made in one
    go (typing one cell, a paste, Delete on a selection, a fill) form one
    step: a step stays open until the event loop runs again. Undo puts the
    old value back and drops the matching _dirty entry, so a cell that is
    back at its saved value is not yellow any more. Cleared after saving
    and when another series is loaded."""

    def __init__(self, screen):
        import weakref
        self._screen = weakref.ref(screen)
        self._undo: List[List[tuple]] = []
        self._redo: List[List[tuple]] = []
        self._group: Optional[List[tuple]] = None
        self._replaying = False

    def record(self, model, r: int, c: int, old, new) -> None:
        if self._replaying:
            return
        import weakref
        if self._group is None:
            self._group = []
            self._undo.append(self._group)
            QTimer.singleShot(0, self._close_group)
        self._group.append((weakref.ref(model), r, c, old, new))
        self._redo.clear()

    def _close_group(self) -> None:
        self._group = None

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()
        self._group = None

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def _apply(self, entries, to_new: bool) -> int:
        n, first = 0, None
        self._replaying = True
        try:
            for ref, r, c, old, new in entries:
                m = ref()
                if m is None or not (0 <= r < len(m._matrix) and 0 <= c < len(m._matrix[r])):
                    continue
                if to_new:
                    m._matrix[r][c] = new
                    m._dirty.append((r, c, new))
                else:
                    m._matrix[r][c] = old
                    for i in range(len(m._dirty) - 1, -1, -1):  # drop the entry this edit added
                        if m._dirty[i][0] == r and m._dirty[i][1] == c:
                            del m._dirty[i]
                            break
                idx = m.index(r + m._n_hdr, c + 1)
                m.dataChanged.emit(idx, idx)
                n += 1
                if first is None:
                    first = (m, idx)
        finally:
            self._replaying = False
        scr = self._screen()
        if first is not None and scr is not None:
            scr._reveal_cell(*first)
        return n

    def undo(self) -> int:
        self._group = None
        if not self._undo:
            return 0
        step = self._undo.pop()
        self._redo.append(step)
        return self._apply(list(reversed(step)), to_new=False)

    def redo(self) -> int:
        self._group = None
        if not self._redo:
            return 0
        step = self._redo.pop()
        self._undo.append(step)
        return self._apply(step, to_new=True)


class ShowExperimentScreen(QWidget):
    def __init__(self, on_back_home, on_back_all_experiments=None, on_add_trials=None,
                 # Sidebar-Navigation (siehe ui/widgets/sidebar_nav.py, geteilt mit
                 # HomeScreen/BacklogScreen/AllExperimentsScreen) - dieselben
                 # Callbacks, siehe BacklogScreen für die Begründung des Musters
                 # (Access-Level erst zur Laufzeit über app_meta bekannt, Sidebar
                 # daher lazy in showEvent() aufgebaut statt hier).
                 on_all_experiments=None, on_open_backlog=None,
                 on_create_experiment=None, on_create_experiment_legacy=None,
                 on_add_series=None, on_add_lab_machines=None, on_open_experiment_request=None,
                 on_create_experiment_request=None, on_open_my_requests=None,
                 on_preview_requests=None, on_preview_open_requests=None,
                 on_image_compare=None, on_canvas=None, on_nozzle_calculator=None, on_air_supply=None,
                 on_requirement_hub=None, on_smartchart=None, on_yarn_stock=None, on_label_generator=None,
                 on_tdms_inspector=None,
                 on_add_jet=None, on_add_top_plate=None, on_add_yarn=None,
                 on_manage_order_type=None, on_manage_product_groups=None, on_manage_material=None,
                 on_add_user=None, on_usage_stats=None, on_offline_sync=None,
                 on_lab_assistant=None,
                 # Log-Out-Callback für die Sidebar-Account-Gruppe (Ersatz für
                 # den früheren Header-Log-Out-Button, der nur auf Home
                 # existierte - siehe screen_home.py::_build_ui()-Docstring).
                 on_logout=None,
                 # Ctrl+Klick "in neuem Tab öffnen" (siehe ui/widgets/tab_container.py)
                 open_in_new_tab=None):
        super().__init__()
        self.on_back_home = on_back_home
        self.on_back_all_experiments = on_back_all_experiments
        self.on_add_trials = on_add_trials
        self.on_open_report = None  # wird von MainWindow gesetzt (→ _go_report)
        self.on_open_report_in_new_tab = None  # set by MainWindow (→ _open_report_in_new_tab, Ctrl+click)
        # Label für den kontextuellen Back-Chip in der Tools-Leiste (Ersatz
        # für den früheren Header-Back-Button) - siehe set_back_target().
        self._back_label: Optional[str] = None

        self._sidebar_nav_callbacks = dict(
            on_all_experiments=on_all_experiments,
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
            on_offline_sync=on_offline_sync,
            on_lab_assistant=on_lab_assistant,
            on_logout=on_logout,
            open_in_new_tab=open_in_new_tab,
        )
        self._sidebar_built_for_level = None
        self._offline_gated_buttons: list = []
        # Jet-Lookup (für Dropdown im Machine-Tab)
        self._jets_list: List[Tuple[Any, str]] = []
        self._jets_map: Dict[Any, str] = {}
        self._jet_delegate: Optional[JetComboDelegate] = None
        # Housing-Lookup (für Dropdown im Machine-Tab)
        self._housing_list: List[Tuple[Any, str]] = []
        self._housing_map: Dict[Any, str] = {}
        self._housing_delegate: Optional[HousingComboDelegate] = None

        self._exp_pk: Optional[int] = None
        self._series_pk: Optional[int] = None
        self._experiment_id_txt: str = ""
        self._experiment_request_id: Optional[Any] = None
        self._trials: List[Dict[str, Any]] = []
        self._trial_ids: List[int] = []
        self._trial_labels: List[str] = []
        self._trial_vnos: List[int] = []
        # trial_id -> name for reference samples (see db/trial_reference.py)
        self._reference_names: Dict[int, str] = {}

        # Lazy tab population (2026-08-13, perf): profiled that opening an
        # experiment with many trials spends most of its (post-DB-caching)
        # time in Qt work - setStyleSheet() re-parsing + headerData() for
        # wide pivot tables - repeated for every lab tab (Titer, Statimat,
        # EKB, shrinkage tabs, ...) on every load_record(), even ones the
        # user never looks at. The DATA FETCH per tab still runs eagerly
        # (it's what decides whether the tab exists at all - some lab
        # tables have zero rows for a given experiment, so applicability
        # isn't knowable from schema alone), but the expensive tail (build
        # model, setModel, resize columns, apply styling) is deferred to
        # the first time the user actually selects that tab - see
        # _defer_or_populate()/_on_tab_current_changed() below. Machine
        # Data is deliberately NOT routed through this - it stays eager,
        # unconditionally, so the screen always opens showing real data
        # immediately instead of a blank first tab.
        self._pending_tab_populate: Dict[str, Any] = {}
        self._tab_widget_to_key: Dict[Any, str] = {}

        # Modeless PDF viewer (so the user can keep editing this screen)
        self._series_pdfs_viewer = None

        # Machine tab (immer sichtbar)
        self.tab_machine: Optional[QWidget] = None
        self.tbl_machine: Optional[QTableView] = None
        self.model_machine: Optional[PivotEditModel] = None
        self._mat_filter_checks: list = []
        self._machine_col_specs: list = []
        self._custom_group_visible: bool = False  # immer ausgeschaltet beim Start

        # R&D Machine tab (nur sichtbar wenn RDSetting=1-Felder vorhanden)
        self.tab_rd_machine: Optional[QWidget] = None
        self.tbl_rd_machine: Optional[QTableView] = None
        self.model_rd_machine: Optional[PivotEditModel] = None

        # dynamische Tabs (nur bei Daten)
        self.tab_titer: Optional[QWidget] = None
        self.tbl_titer: Optional[QTableView] = None
        self.model_titer: Optional[PivotEditModel] = None

        self.tab_jet_air: Optional[QWidget] = None
        self.tbl_jet_air: Optional[QTableView] = None
        self.model_jet_air: Optional[PivotEditModel] = None
        self.tbl_jet_air_atm: Optional[QTableView] = None
        self.model_jet_air_atm: Optional[PivotEditModel] = None
        self.tbl_jet_air_temp: Optional[QTableView] = None
        self.model_jet_air_temp: Optional[PivotEditModel] = None
        self.cmb_jet_air_unit: Optional[QComboBox] = None
        self._jet_air_unit: str = "Nm3h"  # "Nm3h" oder "lmin"

        self.tab_stat: Optional[QWidget] = None
        self.tbl_stat: Optional[QTableView] = None
        self.model_stat: Optional[PivotEditModel] = None

        self.tab_stat_ds: Optional[QWidget] = None
        self.tbl_stat_ds: Optional[QTableView] = None
        self.model_stat_ds: Optional[PivotEditModel] = None
        self.tab_water: Optional[QWidget] = None
        self.tbl_water: Optional[QTableView] = None
        self.model_water: Optional[PivotEditModel] = None

        self.tab_itemat: Optional[QWidget] = None
        self.tbl_itemat: Optional[QTableView] = None
        self.model_itemat: Optional[PivotEditModel] = None
        self.lbl_itemat_retest_banner: Optional[QLabel] = None
        self._itemat_tensions: List[float] = []

        self.tab_itemat_plus: Optional[QWidget] = None
        self.tbl_itemat_plus: Optional[QTableView] = None
        self.model_itemat_plus: Optional[PivotEditModel] = None
        self._itemat_plus_tensions: List[float] = []

        self.tab_dtyomat: Optional[QWidget] = None
        self.tbl_dtyomat: Optional[QTableView] = None
        self.model_dtyomat: Optional[PivotEditModel] = None

        self.tab_atyomat: Optional[QWidget] = None
        self.tbl_atyomat: Optional[QTableView] = None
        self.model_atyomat: Optional[PivotEditModel] = None

        # YarnScope tab
        self.tab_yarnscope: Optional[QWidget] = None
        self._ys_trial_list = None
        self._ys_current_trial_id: Optional[int] = None
        self._ys_cache: dict = {}  # {trial_id: (res, vals)} – alle Trials der aktuellen Series
        self._ys_current_tdms = None
        self._ys_last_res: dict = {}
        self._ys_last_vals: dict = {}
        self._ys_sigs = None
        self._ys_spin_start = None
        self._ys_spin_window = None

        # YarnScope ATY tab
        self.tab_aty_yarnscope: Optional[QWidget] = None

        # agentT Advisor (nur user soj)
        self.tab_advisor: Optional[QWidget] = None
        self._aty_trial_list = None
        self._aty_current_trial_id: Optional[int] = None
        self._aty_current_tdms = None
        self._aty_cache: dict = {}
        self._aty_core_cache: dict = {}  # Compare tab: trial ID -> aty_core_analysis.analyze_trial() result
        self._aty_raw_cache: dict = {}   # Compare tab: trial ID -> (arr_mm, mm_per_point), avoids re-reading TDMS

        self.tab_rapid600: Optional[QWidget] = None
        self.tbl_rapid600: Optional[QTableView] = None
        self.model_rapid600: Optional[PivotEditModel] = None

        # Notes tab
        self.tab_notes: Optional[QWidget] = None
        self.txt_notes: Optional[QTextEdit] = None
        self._notes_timer = None  # QTimer for auto-save debounce
        self._notes_last_saved: str = ""

        # EKB tab
        self.tab_ekb: Optional[QWidget] = None
        self.tbl_ekb: Optional[QTableView] = None
        self.model_ekb: Optional[PivotEditModel] = None

        # Shrinkage tabs
        self.tab_hot_air_shrinkage: Optional[QWidget] = None
        self.tbl_hot_air_shrinkage: Optional[QTableView] = None
        self.model_hot_air_shrinkage: Optional[PivotEditModel] = None

        self.tab_hot_water_shrinkage: Optional[QWidget] = None
        self.tbl_hot_water_shrinkage: Optional[QTableView] = None
        self.model_hot_water_shrinkage: Optional[PivotEditModel] = None

        self.tab_aty_shrinkage: Optional[QWidget] = None
        self.tbl_aty_shrinkage: Optional[QTableView] = None
        self.model_aty_shrinkage: Optional[PivotEditModel] = None

        self._save_model_names: List[str] = []  # Registry of models to save

        self._build_ui()

    def _enable_copy_for_table(self, table: QTableView):
        """Aktiviert Ctrl+C zum Kopieren der selektierten Zellen als TSV ins Clipboard."""
        if table is None:
            return

        # Excel-like editing UX:
        # - Single click: select/focus only
        # - Double click or F2: edit
        # This prevents accidental edits while selecting blocks.
        try:
            table.setEditTriggers(
                QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed)
        except Exception:
            # Don't break copy if a custom view doesn't support this.
            pass

        shortcut = QShortcut(QKeySequence.Copy, table)

        def do_copy():
            selection = table.selectionModel()
            if not selection or not selection.hasSelection():
                return

            indexes = selection.selectedIndexes()
            if not indexes:
                return

            # nach Zeile/Spalte sortieren
            indexes_sorted = sorted(
                indexes, key=lambda i: (i.row(), i.column()))

            top_row = indexes_sorted[0].row()
            left_col = indexes_sorted[0].column()
            bottom_row = indexes_sorted[-1].row()
            right_col = indexes_sorted[-1].column()

            rows = bottom_row - top_row + 1
            cols = right_col - left_col + 1

            data = [["" for _ in range(cols)] for _ in range(rows)]

            for idx in indexes_sorted:
                r = idx.row() - top_row
                c = idx.column() - left_col
                if 0 <= r < rows and 0 <= c < cols:
                    val = idx.data()
                    data[r][c] = "" if val is None else str(val)

            # rows hidden by the user are left out (like a filtered Excel range)
            data = [row for i, row in enumerate(data) if not _view_row_hidden(table, top_row + i)]
            text_block = "\n".join("\t".join(row) for row in data)
            QApplication.clipboard().setText(text_block)

        shortcut.activated.connect(do_copy)

    def _parse_clipboard_tsv(self, text: str) -> List[List[str]]:
        '''
        Parses Excel/clipboard content (usually TSV) into a 2D list.
        Robust enough for typical Excel copy blocks.
        '''
        if text is None:
            return []
        t = str(text)
        # Normalize line endings and remove a single trailing newline Excel often adds
        t = t.replace("\r\n", "\n").replace("\r", "\n")
        if t.endswith("\n"):
            t = t[:-1]
        if t == "":
            return []
        rows = t.split("\n")
        return [r.split("\t") for r in rows]

    def _enable_paste_for_table(self, table: QWidget):
        '''Aktiviert Ctrl+V zum Einfügen von Excel/TSV-Blöcken in die Pivot-Tabellen.'''
        if table is None:
            return

        shortcut = QShortcut(QKeySequence.Paste, table)

        def do_paste():
            model = getattr(table, "model", lambda: None)()
            if model is None:
                return

            clip = QApplication.clipboard().text() or ""
            grid = self._parse_clipboard_tsv(clip)
            if not grid:
                return

            selection = table.selectionModel()
            start_row = None
            start_col = None

            if selection and selection.hasSelection():
                idxs = selection.selectedIndexes() or []
                if idxs:
                    start_row = min(i.row() for i in idxs)
                    start_col = min(i.column() for i in idxs)

            if start_row is None or start_col is None:
                cur = getattr(table, "currentIndex", lambda: QModelIndex())()
                if cur and cur.isValid():
                    start_row, start_col = cur.row(), cur.column()
                else:
                    start_row, start_col = 0, 1

            # Never paste into title column
            if start_col == 0:
                start_col = 1

            max_r = int(getattr(model, "rowCount", lambda: 0)())
            max_c = int(getattr(model, "columnCount", lambda: 0)())

            inserted = 0
            skipped_readonly = 0
            invalid = 0

            # Machine Jet mapping helper
            name_to_id = getattr(self, "_jets_name_to_id", {}) or {}

            # Temporarily reduce UI churn
            try:
                table.setUpdatesEnabled(False)
            except Exception:
                pass

            # pasted rows go to the visible rows only (hidden rows are skipped)
            target_rows: List[int] = []
            _r = start_row
            while len(target_rows) < len(grid) and 0 <= _r < max_r:
                if not _view_row_hidden(table, _r):
                    target_rows.append(_r)
                _r += 1
            for r_off, row_vals in enumerate(grid):
                if r_off >= len(target_rows):
                    break
                tr = target_rows[r_off]
                if tr < 0 or tr >= max_r:
                    continue
                for c_off, raw in enumerate(row_vals):
                    tc = start_col + c_off
                    if tc <= 0 or tc >= max_c:
                        continue

                    idx2 = model.index(tr, tc)
                    try:
                        flags = model.flags(idx2)
                    except Exception:
                        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
                    if not (flags & Qt.ItemIsEditable):
                        skipped_readonly += 1
                        continue

                    val = "" if raw is None else str(raw).replace("\r", "")

                    # Special case: Machine jet/housing rows use IDs, Excel usually has names
                    if isinstance(model, MachinePivotModel):
                        jet_row = getattr(model, "_jet_row_index", 1)
                        if tr == jet_row and tc > 0:
                            s = val.strip()
                            if s == "":
                                # allow clearing
                                pass
                            else:
                                # try int first
                                try:
                                    int(s)
                                except Exception:
                                    # try lookup by name (case-insensitive)
                                    jid = name_to_id.get(s) or name_to_id.get(s.lower())
                                    if jid is None:
                                        invalid += 1
                                        continue
                                    val = str(jid)

                    ok = False
                    try:
                        ok = bool(model.setData(idx2, val, Qt.EditRole))
                    except Exception:
                        ok = False

                    if ok:
                        inserted += 1
                    else:
                        invalid += 1

            try:
                table.setUpdatesEnabled(True)
            except Exception:
                pass

            if skipped_readonly or invalid:
                QMessageBox.information(
                    self,
                    "Paste",
                    f"Inserted: {inserted}\nSkipped (read-only): {skipped_readonly}\nInvalid: {invalid}",
                )

        shortcut.activated.connect(do_paste)

        # Delete / Backspace on selected cells clears them - without double-
        # clicking into the cell first (Nutzerwunsch 2026-10-16). Only while
        # the table has the focus (WidgetWithChildrenShortcut), and a cell
        # editor that is open keeps its own Delete/Backspace (QLineEdit
        # claims them via ShortcutOverride). Runs through setData like typing,
        # so the cells turn yellow and are saved with Save / Ctrl+S.
        for key in (QKeySequence.Delete, QKeySequence(Qt.Key_Backspace)):
            sc_del = QShortcut(key, table)
            sc_del.setContext(Qt.WidgetWithChildrenShortcut)
            sc_del.activated.connect(lambda t=table: self._clear_selected_cells(t))

    def _clear_selected_cells(self, table: QWidget) -> int:
        """Empties every selected, editable cell of `table` (title column and
        read-only cells are skipped). Returns the number of cleared cells."""
        model = getattr(table, "model", lambda: None)()
        if model is None:
            return 0
        sel = table.selectionModel()
        idxs = list(sel.selectedIndexes()) if sel is not None and sel.hasSelection() else []
        if not idxs:
            cur = getattr(table, "currentIndex", lambda: QModelIndex())()
            idxs = [cur] if cur is not None and cur.isValid() else []
        cleared = 0
        for idx in idxs:
            if idx.column() == 0 or not (model.flags(idx) & Qt.ItemIsEditable):
                continue
            if model.data(idx, Qt.EditRole) in (None, ""):
                continue
            try:
                if model.setData(idx, "", Qt.EditRole):
                    cleared += 1
            except Exception:
                continue
        return cleared

    def _register_save_model(self, attr_name: str):
        """Registers a model attribute name for generic save handling.

        We keep names (not instances) so we can apply special post-save hooks
        (e.g. Itemat recompute) based on the attribute.
        """
        if not hasattr(self, "_save_model_names"):
            self._save_model_names = []
        if attr_name not in self._save_model_names:
            self._save_model_names.append(attr_name)
        _m = getattr(self, attr_name, None)
        if _m is not None:
            _m._undo_mgr = getattr(self, "_undo", None)  # Ctrl+Z (_UndoManager)
        # Every per-trial lab model is built with col_titles=self._trial_labels
        # (one column per trial, same order) - highlight reference columns
        # there centrally instead of in each _build_XXX_tab. The machine tabs
        # (one column per ply) do this themselves via col_specs.
        model = getattr(self, attr_name, None)
        if model is not None and getattr(model, "_col_titles", None) is self._trial_labels:
            self._apply_reference_columns(model, self._trial_ids)
        if model is not None:
            _cell_notes_ui.apply_notes_to_model(self, attr_name)

    def _apply_reference_columns(self, model, trial_id_per_col) -> None:
        """Marks the columns of `model` that belong to a reference sample.
        trial_id_per_col: trial ID for each data column (0-based)."""
        if not hasattr(model, "set_reference_columns"):
            return
        refs = self._reference_names
        mapping = {}
        for c_idx, tid in enumerate(trial_id_per_col):
            try:
                tid = int(tid)
            except (TypeError, ValueError):
                continue
            if tid in refs:
                vno = self._trial_vnos[self._trial_ids.index(tid)] if tid in self._trial_ids else "?"
                mapping[c_idx] = reference_tooltip(refs[tid], vno)
        model.set_reference_columns(mapping)

    def _iter_save_models(self):
        """Yields (attr_name, model) for all registered models that exist."""
        for name in getattr(self, "_save_model_names", []) or []:
            m = getattr(self, name, None)
            if m is not None:
                yield name, m

    def _load_jets_lookup(self):
        """Lädt alle Jets aus tblDTYJets (ID + Jet-Name, A–Z sortiert)
        sowie Geometrie-Daten für den Hover-Tooltip (db/machine_data.load_jets_lookup)."""
        jl = _machine_data.load_jets_lookup()
        self._jets_list = jl.list
        self._jets_map = jl.map
        self._jets_name_to_id = jl.name_to_id
        self._jets_tooltip_map: Dict[Any, str] = jl.tooltip_map

    def _load_housing_lookup(self):
        """Lädt alle Housings aus tblHousing (ID + HousingName + Link, A-Z sortiert)
        (db/machine_data.load_housing_lookup)."""
        hl = _machine_data.load_housing_lookup()
        self._housing_list = hl.list
        self._housing_map = hl.map
        self._housing_image_map: Dict[Any, str] = hl.image_map

    # ---------- Lazy tab population ----------

    def _defer_or_populate(self, key: str, tab_widget, populate_fn):
        """Runs `populate_fn` now if `tab_widget` is the currently selected
        tab, otherwise stores it to run the first time the user actually
        selects that tab (see _on_tab_current_changed()). `populate_fn`
        should be the expensive "build model / setModel / resize columns /
        apply styling" tail of a _build_XXX_tab() method - the row fetch
        that decides whether the tab exists at all must already have
        happened in the caller before this is invoked.
        """
        self._tab_widget_to_key[tab_widget] = key
        if self.tabs.currentWidget() is tab_widget:
            populate_fn()
        else:
            self._pending_tab_populate[key] = populate_fn

    _LAST_TAB_KEY = "show_experiment/last_tab/{}"

    def _remember_tab(self, index: int) -> None:
        """Last tab per series (Nutzerwunsch 2026-10-16) - only what the user
        chose, not the switching while a series loads."""
        if getattr(self, "_loading_record", False) or index < 0:
            return
        sid = getattr(self, "_series_pk", None)
        if sid is None:
            return
        try:
            from PySide6.QtCore import QSettings
            QSettings("TrippleT", "TrippleT").setValue(self._LAST_TAB_KEY.format(sid), self.tabs.tabText(index))
        except Exception:
            pass

    def _restore_last_tab(self) -> None:
        sid = getattr(self, "_series_pk", None)
        if sid is None:
            return
        try:
            from PySide6.QtCore import QSettings
            want = QSettings("TrippleT", "TrippleT").value(self._LAST_TAB_KEY.format(sid), "", type=str)
        except Exception:
            return
        if not want:
            return
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i).replace(" ✓", "") == want.replace(" ✓", "") and self.tabs.isTabVisible(i):
                self.tabs.setCurrentIndex(i)
                return

    def _on_tab_current_changed(self, index: int):
        """Runs a deferred tab's populate_fn (see _defer_or_populate()) the
        first time the user actually switches to it."""
        self._remember_tab(index)
        widget = self.tabs.widget(index)
        key = self._tab_widget_to_key.get(widget)
        if key is None:
            return
        populate_fn = self._pending_tab_populate.pop(key, None)
        if populate_fn is not None:
            populate_fn()

    # ---------- PUBLIC API ----------

    def _show_conclusion_tab(self) -> None:
        from db import series_conclusion as _sc
        tab = getattr(self, "tab_conclusion", None)
        if tab is None:
            return
        idx = self.tabs.indexOf(tab)
        if idx != -1:
            self.tabs.removeTab(idx)
        if not _sc.table_ready() or self._series_pk is None:
            return
        tab.load(self._series_pk, list(self._trial_ids), list(self._trial_labels))
        self.tabs.addTab(tab, "Conclusion")
        self._update_conclusion_tab_title()

    def _update_conclusion_tab_title(self) -> None:
        tab = getattr(self, "tab_conclusion", None)
        idx = self.tabs.indexOf(tab) if tab is not None else -1
        if idx != -1:
            self.tabs.setTabText(idx, "Conclusion ✓" if tab.has_conclusion() else "Conclusion")

    def load_record(self, exp_pk: int, series_pk: int, experiment_id: str):
        if getattr(self, "tab_conclusion", None) is not None:
            self.tab_conclusion.ask_save_if_dirty()
        # Unsaved changes of the series shown before (e.g. left via the
        # sidebar, then another series opened from the Backlog) were lost
        # silently - ask Save / Discard first (Nutzerwunsch 2026-10-16).
        if self._has_unsaved():
            n = self.unsaved_count()
            prev = getattr(self, "_experiment_id_txt", "") or ""
            if QMessageBox.question(
                    self, "Unsaved changes",
                    f"Show Experiment {prev} still has {n} unsaved change{'s' if n != 1 else ''}.\n\n"
                    f"Save {'it' if n == 1 else 'them'} before opening {experiment_id}?",
                    QMessageBox.Save | QMessageBox.Discard, QMessageBox.Save) == QMessageBox.Save:
                self._save_all()
        if getattr(self, "_undo", None) is not None:
            self._undo.clear()  # undo steps belong to the series shown before
        self._loading_record = True
        try:
            self._load_record_inner(exp_pk, series_pk, experiment_id)
        finally:
            self._loading_record = False
        self._restore_last_tab()  # same tab as last time for this series
        if self._recycle_preview is None:  # Sidebar -> "Recent" (not for recycle bin previews)
            from ui import recent_series
            recent_series.remember(exp_pk, series_pk, experiment_id, getattr(self, "_series_name_txt", ""))

    def _load_record_inner(self, exp_pk: int, series_pk: int, experiment_id: str):
        self._ys_cache = {}  # Neue Series -> Cache leeren
        self._machine_cache = {}  # Machine-Cache immer neu aufbauen (verhindert Stale-Fields)
        # Discard any not-yet-run deferred tab populates from a PREVIOUS
        # experiment (see _defer_or_populate()) - they'd describe stale data
        # if triggered late for a tab widget reused by this new experiment.
        self._pending_tab_populate = {}
        # Alle Akzent-abhängigen Styles mit aktuellem Akzent neu anwenden
        try:
            _acc = get_accent()
            _tint = accent_tint()
            _grid = accent_gridline()
            _tab_qss = """
                QTabWidget::pane { border: 0px; }
                QTabBar::tab {
                    background: #ffffff; color: #39a650;
                    border: 1px solid #cfcfcf; padding: 8px 14px; margin-right: 4px;
                    border-bottom: none;
                }
                QTabBar::tab:hover { background: #e9e9e9; }
                QTabBar::tab:selected { background: #000000; color: #39a650; }
            """.replace("#39a650", _acc)
            self.tabs.setStyleSheet(_tab_qss)
            _table_qss = """
                QTableView { gridline-color: #B5D7B5; }
                QHeaderView::section {
                    background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                    border: 1px solid #B5D7B5; padding: 4px 6px;
                }
                QTableView::item:selected { background: #b7d6ff; color: black; }
            """.replace("#B5D7B5", _grid).replace("#E9F6E9", _tint)
            self.tbl_machine.setStyleSheet(_table_qss)
            self.lbl_material_title.setStyleSheet(
                "color:" + _acc + "; font-weight:700; padding:4px 6px;")
            self.lbl_material_value.setStyleSheet(
                "border:1px solid " + _acc + "; border-radius:4px; padding:6px 10px;"
                                             "color:#202020; background:#f8fff9;")
            # Titer-Tab StyleSheet aktualisieren falls bereits existiert
            if self.tbl_titer is not None:
                self.tbl_titer.setStyleSheet(_table_qss)
        except Exception:
            pass
        """Öffnet ein Experiment + TrialSeries und baut die Tabs/Listen auf."""
        # Jets + Housing (für Dropdowns) aktualisieren
        self._load_jets_lookup()
        self._load_housing_lookup()

        self._exp_pk = exp_pk
        self._series_pk = series_pk
        self._experiment_id_txt = experiment_id

        try:
            self._refresh_saved_reports_dropdown()
        except Exception:
            pass

        ts = fetch_all(
            "SELECT SeriesName, Notes FROM tblTrialSeries WHERE ID = ?", [series_pk])
        series_name = ts[0]["SeriesName"] if ts else ""
        self.lbl_small_title.setText(f"{experiment_id} – {series_name}")
        self._series_name_txt = series_name
        self.lbl_series_id.setText(f"TrialSeriesID: {series_pk}")

        # Fenster-/Tab-Titel: "ExperimentID.SS" (erste 2 Zeichen des
        # Series-Namens, z.B. "2026-73-024.09") statt "Show Experiment
        # 2026-73-024" - Nutzerwunsch 2026-08-27 ("das ist für den User
        # klarer"), gleiche Kurzform wie schon beim Print-Labels-Header
        # (siehe _on_print_trial_labels() weiter unten). main.py setzt
        # vor load_record() bereits einen generischen Platzhaltertitel -
        # dieser hier ist der zuletzt gesetzte und damit der tatsächlich
        # sichtbare (auch für den Tab-Label-Sync, siehe
        # ui/widgets/tab_container.py).
        try:
            self.window().setWindowTitle(f"TrippleT – {experiment_id}.{series_name[:2]}")
        except Exception:
            pass

        # Load Notes
        self._load_notes(ts[0] if ts else {})
        # Trials laden (falls bei dir für andere Tabs benötigt)
        self._load_trials()

        # Material-Infobox aktualisieren (neu)
        self._refresh_materials_box()

        # Experiment Request link + icon
        self._refresh_experiment_request_link()
        self._sync_experiment_request_icon()
        self._sync_trialseries_images_icon()
        self._sync_trialseries_pdfs_icon()

        # Tabs neu aufbauen
        self._save_model_names = []  # reset save registry
        self._init_machine_cache()  # statische DB-Daten einmalig cachen
        self._build_machine_tab()
        # Always show Machine Data first when a (new) experiment loads -
        # makes _defer_or_populate()'s "is this tab currently visible"
        # check meaningful/predictable, and matches the actual ask (open
        # fast showing Machine Data, lazy-load the rest on demand) rather
        # than leaving the view on whatever lab tab happened to be selected
        # for the PREVIOUS experiment.
        if self.tab_machine is not None:
            self.tabs.setCurrentWidget(self.tab_machine)
        self._build_lab_tabs()
        self._build_yarnscope_tab()
        self._build_aty_yarnscope_tab()

        # agentT Advisor Tab — einmalig aufbauen, nicht bei jedem load_record() neu
        if self.tab_advisor is None and _is_advisor_enabled():
            self._build_advisor_tab()
            self.tabs.addTab(self.tab_advisor, "🦉 Athena")
        elif self.tab_advisor is not None:
            # Nur State zurücksetzen (Output + History), Tab bleibt erhalten
            self._reset_advisor()

        # Athena: gespeicherten Report (letzte Session) automatisch laden,
        # falls vorhanden - MUSS nach _reset_advisor() laufen, sonst wird
        # der geladene Report sofort wieder von reset ueberschrieben. Kein
        # erneuter (kostenpflichtiger) API-Call noetig, nur um zu sehen,
        # was beim letzten Mal rauskam.
        if self.tab_advisor is not None:
            _advisor_mod._load_latest_advisor_report(self)

        # Notes tab: always append last so it appears as the rightmost tab.
        # Remove first if already present (re-load scenario).
        if self.tab_notes is not None:
            idx = self.tabs.indexOf(self.tab_notes)
            if idx != -1:
                self.tabs.removeTab(idx)
            self.tabs.addTab(self.tab_notes, "Notes")

        # Conclusion tab right of Notes (only when the database has tblSeriesConclusion)
        self._show_conclusion_tab()

        # Notizen an Werten laden (Dreiecke + Liste im Notes-Tab)
        _cell_notes_ui.reload_notes(self)
        # Tab ist jetzt im Widget — Hervorhebung setzen
        self._update_notes_tab_style()

        # Beim Öffnen: "Machine Data" aktiv
        if hasattr(self, "tab_machine") and self.tab_machine is not None:
            self.tabs.setCurrentWidget(self.tab_machine)

    # ---------- UI ----------

    def _build_ui(self):
        # Keine TopBar (HeaderBar) mehr (2026-08-26, siehe screen_home.py::
        # _build_ui()-Docstring) - Glocke/Suche/Accent-Farbe/Log Out sitzen
        # jetzt in der Sidebar-Account-Gruppe. Das frühere Back-Button-
        # Bedürfnis (zurück zu Backlog/All Experiments/Manage Yarn/Manage
        # Jets, je nachdem von wo aus geöffnet wurde) bleibt exklusiv hier
        # (Nutzer-Feedback: "will lieber eine andere Lösung als die TopBar
        # nür für 'once in a while' zu behalten") - siehe der kontextuelle
        # Back-Chip weiter unten in der Tools-Leiste, gesetzt über
        # set_back_target().
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar-Navigation (siehe ui/widgets/sidebar.py + sidebar_nav.py,
        # geteilt mit allen anderen Screens) - Inhalt bleibt hier leer, wird
        # lazy beim ersten showEvent() befüllt (access_level ist zum
        # Zeitpunkt dieses Konstruktoraufrufs noch nicht bekannt). Der
        # restliche, bereits bestehende Inhalt dieser Methode wandert von
        # `root` nach `content_layout` (siehe unten) - FooterBar bleibt
        # bewusst auf `root`, spannt also volle Breite unter Sidebar+Inhalt.
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)
        self._content_layout = content_layout
        self._recycle_preview = None  # ui/recycle_preview.py: read-only look into the recycle bin
        # Unsaved changes indicator (Save (n), tab dot, yellow cells): the
        # models' _dirty lists change in many places, so a light poll while
        # the screen is visible is more robust than signals at every site.
        self._unsaved_shown = -1
        self._unsaved_timer = None  # created on first show (_build_ui imports QTimer locally further down)
        self._init_undo()

        # Titelzeile (dunkler Balken + Save)
        tools = QFrame()
        tl = QHBoxLayout(tools)
        tl.setContentsMargins(24, 12, 24, 0)
        tl.setSpacing(8)

        # Kontextueller Back-Chip entfernt (2026-08-27, Nutzerwunsch: "der
        # button oben der mich zurück führt will ich nicht mehr" - die
        # Sidebar-Einträge "Backlog"/"All Experiments" bleiben unverändert
        # bestehen, siehe sidebar_nav.py; set_back_target() bleibt als
        # No-Op-Bookkeeping bestehen, da main.py an mehreren Stellen weiterhin
        # danach ruft, hat aber kein UI-Gegenstück mehr).

        self.lbl_small_title = QLabel("")
        self.lbl_small_title.setStyleSheet(
            "padding: 6px 10px; background: #3f3f3f; color: white; font-weight: 600;"
        )

        # New: label for TrialSeriesID (shown right of the small title)
        self.lbl_series_id = QLabel("TrialSeriesID: —")
        self.lbl_series_id.setStyleSheet(
            "padding: 6px 10px; background: #e8e8e8; color: #202020; font-weight: 600; border: 1px solid #cfcfcf;"
        )
        # Keep a reference on self. In PySide this avoids edge cases where
        # a locally-scoped widget + shortcut behaves inconsistently.
        self.btn_save = QPushButton("Save")
        self.btn_save.setObjectName("GreenBtn")
        self.btn_save.clicked.connect(self._save_all)

        # Enable/disable is synced when the screen becomes visible.
        # This avoids the edge case where the screen is constructed before
        # app_meta.current_user/access_level is populated (then the button would
        # stay disabled forever even though Ctrl+S can save).
        self._sync_save_button_access()

        # Keyboard shortcut: Ctrl+S -> EXACT same path as clicking Save.
        # (The access-level guard is handled inside _save_all, so we always connect.)
        # Wir setzen BEIDE Methoden: QShortcut (WindowShortcut) + keyPressEvent-Override,
        # da ApplicationShortcut in PySide6 mit QStackedWidget-Containern unzuverlässig ist.
        try:
            self._sc_save = QShortcut(QKeySequence("Ctrl+S"), self)
            self._sc_save.setContext(Qt.WindowShortcut)
            self._sc_save.activated.connect(self._save_all)
        except Exception:
            self._sc_save = None

        tl.addWidget(self.lbl_small_title)
        tl.addWidget(self.lbl_series_id)

        # TrialSeries images (upload + viewer)
        self.btn_upload_series_images = QPushButton("Upload images")
        self.btn_upload_series_images.setMinimumHeight(30)
        self.btn_upload_series_images.clicked.connect(self._upload_series_images)
        tl.addWidget(self.btn_upload_series_images)

        self.btn_show_series_images = QPushButton()
        self.btn_show_series_images.setObjectName("IconBtn")
        self.btn_show_series_images.setCursor(Qt.PointingHandCursor)
        self.btn_show_series_images.setFlat(True)
        self.btn_show_series_images.setToolTip("Show attached TrialSeries images")
        ico = QIcon(resource_path("assets/images/picture.png"))
        if not ico.isNull():
            self.btn_show_series_images.setIcon(ico)
            self.btn_show_series_images.setIconSize(QSize(22, 22))
        else:
            self.btn_show_series_images.setText("Images")
        self.btn_show_series_images.clicked.connect(self._open_series_images_dialog)
        self.btn_show_series_images.setVisible(False)
        tl.addWidget(self.btn_show_series_images)

        # TrialSeries PDFs (upload + viewer)
        self.btn_upload_series_pdfs = QPushButton("Upload PDFs")
        self.btn_upload_series_pdfs.setMinimumHeight(30)
        self.btn_upload_series_pdfs.clicked.connect(self._upload_series_pdfs)
        tl.addWidget(self.btn_upload_series_pdfs)

        self.btn_show_series_pdfs = QPushButton()
        self.btn_show_series_pdfs.setObjectName("IconBtn")
        self.btn_show_series_pdfs.setCursor(Qt.PointingHandCursor)
        self.btn_show_series_pdfs.setFlat(True)
        self.btn_show_series_pdfs.setToolTip("Show attached TrialSeries PDFs")
        ico_pdf = QIcon(resource_path("assets/images/pdf.png"))
        if not ico_pdf.isNull():
            self.btn_show_series_pdfs.setIcon(ico_pdf)
            self.btn_show_series_pdfs.setIconSize(QSize(22, 22))
        else:
            self.btn_show_series_pdfs.setText("PDF")
        self.btn_show_series_pdfs.clicked.connect(self._open_series_pdfs_dialog)
        self.btn_show_series_pdfs.setVisible(False)
        tl.addWidget(self.btn_show_series_pdfs)

        # Statimat PDF import (reads attached STATIMAT PDF(s) and writes to DB)
        self.btn_statimat_import = QPushButton("Statimat import")
        self.btn_statimat_import.setMinimumHeight(30)
        self.btn_statimat_import.clicked.connect(self._statimat_import)
        tl.addWidget(self.btn_statimat_import)

        # Itemat Lab PDF import
        self.btn_itemat_import = QPushButton("Itemat import")
        self.btn_itemat_import.setMinimumHeight(30)
        self.btn_itemat_import.clicked.connect(self._itemat_import)
        tl.addWidget(self.btn_itemat_import)

        # Report-Button (3D-Visualisierung)
        self.btn_report = QPushButton()
        self.btn_report.setObjectName("IconBtn")
        self.btn_report.setCursor(Qt.PointingHandCursor)
        self.btn_report.setFlat(True)
        self.btn_report.setToolTip("Open 3D report for this trial series")
        self.btn_report.setFixedSize(34, 34)
        ico_report = QIcon(resource_path("assets/images/analytics.png"))
        if not ico_report.isNull():
            self.btn_report.setIcon(ico_report)
            self.btn_report.setIconSize(QSize(22, 22))
        else:
            self.btn_report.setText("Report")
        self.btn_report.clicked.connect(self._open_report)
        tl.addWidget(self.btn_report)

        # Canvas boards of this series (db/canvas_boards.py, same boards as the web app)
        self.btn_boards = QPushButton("🖼 Board")
        self.btn_boards.setMinimumHeight(30)
        self.btn_boards.setToolTip("Canvas boards of this series (pictures, PDFs and notes on one surface)")
        self.btn_boards.clicked.connect(self._open_boards)
        tl.addWidget(self.btn_boards)

        # Gespeicherte Reports zu dieser TrialSeries: Dropdown + "Go!"-Button
        # (2026-08-27, Nutzerwunsch) - beide nur sichtbar, wenn tatsächlich
        # mind. ein Report für diese Series existiert (siehe load_record()/
        # _refresh_saved_reports_dropdown()). Auswahl öffnet den Report-
        # Screen direkt mit genau diesem Report geladen, statt der leeren
        # Standardansicht (siehe _open_selected_saved_report()).
        self.cmb_saved_reports = QComboBox()
        self.cmb_saved_reports.setMinimumWidth(220)
        self.cmb_saved_reports.setToolTip("Saved Smart Chart reports for this trial series")
        self.cmb_saved_reports.setVisible(False)
        tl.addWidget(self.cmb_saved_reports)

        self.btn_go_saved_report = QPushButton("Go!")
        self.btn_go_saved_report.setMinimumHeight(30)
        self.btn_go_saved_report.setToolTip("Open the selected saved report")
        self.btn_go_saved_report.clicked.connect(self._open_selected_saved_report)
        self.btn_go_saved_report.setVisible(False)
        tl.addWidget(self.btn_go_saved_report)

        tl.addStretch(1)
        self.btn_refresh = QPushButton("↻")
        self.btn_refresh.setToolTip("Screen aktualisieren (F5)")
        self.btn_refresh.setFixedWidth(36)
        self.btn_refresh.setMinimumHeight(30)
        self.btn_refresh.setStyleSheet(
            "QPushButton{background:transparent;color:#39a650;border-radius:4px;"
            "font-size:18px;font-weight:bold;border:1px solid #39a650;padding:0px;}"
            "QPushButton:hover{background:#e8f5e9;}")
        self.btn_refresh.clicked.connect(self._on_refresh)
        try:
            from PySide6.QtGui import QShortcut, QKeySequence
            self._sc_refresh = QShortcut(QKeySequence("F5"), self)
            self._sc_refresh.setContext(Qt.ApplicationShortcut)
            self._sc_refresh.activated.connect(self._on_refresh)
        except Exception:
            pass
        tl.addWidget(self.btn_refresh)
        tl.addWidget(self.btn_save)
        # Kontext-Hilfe EN/DE/ES (Nutzerwunsch 2026-10-13, ui/widgets/multilang_help.py)
        from ui.widgets.multilang_help import make_help_button
        tl.addWidget(make_help_button("How does Show Experiment work?", self._open_help))
        content_layout.addWidget(tools)

        # NEU: Material-Infobox direkt unter dem Balken
        mat_wrap = QFrame()
        mwl = QHBoxLayout(mat_wrap)
        mwl.setContentsMargins(24, 8, 24, 0)
        mwl.setSpacing(8)

        self.lbl_material_title = QLabel("Material")
        self.lbl_material_title.setStyleSheet(
            "color:" + get_accent() + "; font-weight:700; padding:4px 6px;"
        )

        self.lbl_material_value = QLabel("—")
        self.lbl_material_value.setWordWrap(True)
        self.lbl_material_value.setTextFormat(Qt.RichText)
        self.lbl_material_value.setTextInteractionFlags(Qt.LinksAccessibleByMouse)
        self.lbl_material_value.setStyleSheet(
            "border:1px solid " + get_accent() + "; border-radius:4px; padding:6px 10px;"
                                                 "color:#202020; background:#f8fff9;"
        )
        self.lbl_material_value.setMouseTracking(True)
        self.lbl_material_value.linkHovered.connect(
            self._on_material_label_link_hovered)
        self.lbl_material_value.linkActivated.connect(
            self._on_material_label_link_activated)

        mwl.addWidget(self.lbl_material_title, 0, Qt.AlignVCenter)
        mwl.addWidget(self.lbl_material_value, 1, Qt.AlignVCenter)
        content_layout.addWidget(mat_wrap)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 0px; }
            QTabBar::tab {
                background: #ffffff; color: #39a650;
                border: 1px solid #cfcfcf; padding: 8px 14px; margin-right: 4px;
                border-bottom: none;
            }
            QTabBar::tab:hover { background: #e9e9e9; }
            QTabBar::tab:selected { background: #000000; color: #39a650; }
        """.replace("#39a650", get_accent()))
        self.tabs.currentChanged.connect(self._on_tab_current_changed)

        # Experiment Request icon (visible only when linked)
        self.btn_experiment_request = QPushButton()
        self.btn_experiment_request.setObjectName('IconBtn')
        self.btn_experiment_request.setToolTip('Show linked Experiment Request')
        self.btn_experiment_request.setFlat(True)
        self.btn_experiment_request.setFixedSize(34, 34)
        self.btn_experiment_request.setStyleSheet(
            "QPushButton{border:none;background:transparent;padding:0px;}"
            "QPushButton:hover{background:rgba(0,0,0,0.06);border-radius:6px;}"
        )

        # Robust icon lookup: try app root, then ui/ subfolders, then CWD.
        icon_candidates = [
            resource_path('experiment_request.png'),
            resource_path('ui/experiment_request.png'),
            resource_path('ui/icons/experiment_request.png'),
            resource_path('ui/assets/experiment_request.png'),
            resource_path('assets/experiment_request.png'),
            # Project layout: assets/images/experiment_request.png
            resource_path('assets/images/experiment_request.png'),
        ]
        _icon_set = False
        for _p in icon_candidates:
            try:
                if _p and os.path.exists(_p):
                    self.btn_experiment_request.setIcon(QIcon(_p))
                    self.btn_experiment_request.setIconSize(QSize(22, 22))
                    _icon_set = True
                    break
            except Exception:
                continue
        if not _icon_set:
            # Fallback so the button is still visible even if the png is missing.
            self.btn_experiment_request.setText("ER")
            self.btn_experiment_request.setStyleSheet(
                self.btn_experiment_request.styleSheet()
                + "QPushButton{font-weight:700;color:" + get_accent() + ";}"
            )
        self.btn_experiment_request.setVisible(False)
        self.btn_experiment_request.clicked.connect(self._open_experiment_request_popup)
        # IMPORTANT (Qt quirk): Using tabBar corner widgets often gets clipped when
        # there are many tabs. Therefore we place the icon button in its own header
        # row above the tabs so it is always fully visible.
        tabs_header = QFrame()
        thl = QHBoxLayout(tabs_header)
        thl.setContentsMargins(24, 0, 24, 0)
        thl.setSpacing(8)
        thl.addStretch(1)
        thl.addWidget(self.btn_experiment_request, 0, Qt.AlignRight | Qt.AlignVCenter)
        content_layout.addWidget(tabs_header, 0)

        content_layout.addWidget(self.tabs, 1)

        # Machine Data Tab
        self.tab_machine = QWidget()
        vm = QVBoxLayout(self.tab_machine)
        vm.setContentsMargins(24, 12, 24, 24)

        self.machine_info = QLabel("")
        self.machine_info.setStyleSheet("color: #666;")
        vm.addWidget(self.machine_info)

        # ── Ply filter toolbar ───────────────────────────────────────────
        self._mat_filter_bar = QWidget()
        self._mat_filter_bar.setVisible(False)
        _mfb_lay = QHBoxLayout(self._mat_filter_bar)
        _mfb_lay.setContentsMargins(0, 0, 0, 4)
        _mfb_lay.setSpacing(8)

        from PySide6.QtWidgets import QRadioButton, QButtonGroup
        self._rb_single = QRadioButton("Single Plies")
        self._rb_groups = QRadioButton("Groups")
        self._rb_compact = QRadioButton("Compact")
        self._rb_single.setChecked(True)
        self._mat_mode_group = QButtonGroup(self._mat_filter_bar)
        self._mat_mode_group.addButton(self._rb_single, 0)
        self._mat_mode_group.addButton(self._rb_groups, 1)
        self._mat_mode_group.addButton(self._rb_compact, 2)
        _mfb_lay.addWidget(self._rb_single)
        _mfb_lay.addWidget(self._rb_groups)
        _mfb_lay.addWidget(self._rb_compact)

        # Compat alias so existing code referencing _cb_compact still works
        class _CompactAlias:
            def __init__(self_, rb): self_._rb = rb

            def isChecked(self_): return self_._rb.isChecked()

            def stateChanged(self_): pass  # unused

        self._cb_compact = _CompactAlias(self._rb_compact)

        _sep = QFrame()
        _sep.setFrameShape(QFrame.VLine)
        _sep.setFrameShadow(QFrame.Sunken)
        _mfb_lay.addWidget(_sep)
        self._mat_check_layout = QHBoxLayout()
        self._mat_check_layout.setSpacing(8)
        _mfb_lay.addLayout(self._mat_check_layout)
        # "N rows hidden" - menu with "Show all rows" + single rows
        # (see ui/machine_row_visibility.py)
        self.btn_hidden_rows = QToolButton()
        self.btn_hidden_rows.setPopupMode(QToolButton.InstantPopup)
        self.btn_hidden_rows.setToolTip("Rows hidden in this table - show them again")
        self.btn_hidden_rows.setStyleSheet(
            "QToolButton{border:1px solid #9bbbe0;background:#eaf2fc;color:#1f4e8c;"
            "padding:3px 8px;border-radius:4px;}"
            "QToolButton:hover{background:#d8e7fa;}"
            "QToolButton::menu-indicator{image:none;}")
        self.btn_hidden_rows.setVisible(False)
        _mfb_lay.addWidget(self.btn_hidden_rows)
        _mfb_lay.addStretch(1)

        # ── "Print trial labels" Button (links vom "+") ────────────────
        self.btn_print_trial_labels = QPushButton()
        self.btn_print_trial_labels.setToolTip("Print labels (trial numbers)")
        self.btn_print_trial_labels.setFixedSize(30, 30)
        self.btn_print_trial_labels.setStyleSheet(
            "QPushButton{border:none;background:transparent;padding:2px;border-radius:4px;}"
            "QPushButton:hover{background:#e8f5e9;}")
        _ico_label = QIcon(resource_path("assets/images/print_labels.png"))
        if not _ico_label.isNull():
            self.btn_print_trial_labels.setIcon(_ico_label)
            self.btn_print_trial_labels.setIconSize(self.btn_print_trial_labels.size())
        else:
            self.btn_print_trial_labels.setText("🏷")
        self.btn_print_trial_labels.clicked.connect(self._on_print_trial_labels)
        _mfb_lay.addWidget(self.btn_print_trial_labels)

        # ── "Add empty trial" Button ─────────────────────────────────────
        self.btn_add_empty_trial = QPushButton()
        self.btn_add_empty_trial.setToolTip("Add empty trial")
        self.btn_add_empty_trial.setFixedSize(30, 30)
        self.btn_add_empty_trial.setStyleSheet(
            "QPushButton{border:none;background:transparent;padding:2px;border-radius:4px;}"
            "QPushButton:hover{background:#e8f5e9;}")
        _ico_add = QIcon(resource_path("assets/images/add_trial.png"))
        if not _ico_add.isNull():
            self.btn_add_empty_trial.setIcon(_ico_add)
            self.btn_add_empty_trial.setIconSize(self.btn_add_empty_trial.size())
        else:
            self.btn_add_empty_trial.setText("+T")
        self.btn_add_empty_trial.clicked.connect(self._add_empty_trial)
        _mfb_lay.addWidget(self.btn_add_empty_trial)

        # ── "Add reference sample" Button (customer original / benchmark) ──
        self.btn_add_reference = QPushButton("+ Ref")
        self.btn_add_reference.setToolTip(
            "Add reference sample (e.g. customer original spool) - shown as a\n"
            "highlighted benchmark column, not counted as a trial")
        self.btn_add_reference.setFixedHeight(30)
        self.btn_add_reference.setStyleSheet(
            "QPushButton{border:1px solid #E8C15A;background:#FFF4D6;color:#5a4500;"
            "padding:2px 8px;border-radius:4px;font-weight:bold;}"
            "QPushButton:hover{background:#FBE8B5;}"
            "QPushButton:disabled{border-color:#ddd;background:#f4f4f4;color:#aaa;}")
        self.btn_add_reference.clicked.connect(self._add_reference_sample)
        _mfb_lay.addWidget(self.btn_add_reference)

        # ── "vs Ref / Target": all trials against a reference sample or own
        # target values (ui/ref_compare_dialog.py)
        self.btn_ref_compare = QPushButton("vs Ref / Target")
        self.btn_ref_compare.setToolTip(
            "Which trials meet all your criteria? Compare the lab values of all trials\n"
            "with a reference sample or with your own target values (higher / lower / close)")
        self.btn_ref_compare.setFixedHeight(30)
        self.btn_ref_compare.setStyleSheet(
            "QPushButton{border:1px solid #E8C15A;background:#ffffff;color:#5a4500;"
            "padding:2px 8px;border-radius:4px;font-weight:bold;}"
            "QPushButton:hover{background:#FFF4D6;}")
        self.btn_ref_compare.clicked.connect(lambda: self._open_ref_compare())
        self.btn_ref_compare.setVisible(False)
        _mfb_lay.addWidget(self.btn_ref_compare)

        # ── "Copy trials" Button (selected columns are preselected) ─────────
        self.btn_copy_trials = QPushButton("Copy trials")
        self.btn_copy_trials.setToolTip(
            "Copy trials - choose which trials and how often, and change values\n"
            "for the copies before copying. Trials selected in the table are preselected.")
        self.btn_copy_trials.setFixedHeight(30)
        self.btn_copy_trials.clicked.connect(self._on_copy_trials_button)
        _mfb_lay.addWidget(self.btn_copy_trials)

        # ── "Yarns…" Button: yarns/plies of the whole series ───────────────
        self.btn_series_yarns = QPushButton("Yarns…")
        self.btn_series_yarns.setToolTip(
            "Yarns of this series - change the yarn of a ply, add or remove plies\n"
            "per trial, number of ends (also: right-click the Ply row)")
        self.btn_series_yarns.setFixedHeight(30)
        self.btn_series_yarns.clicked.connect(lambda: self._open_series_yarns())
        _mfb_lay.addWidget(self.btn_series_yarns)

        vm.addWidget(self._mat_filter_bar)
        # DTY process schema (toggle "Schema" + panel, only on DTY machines)
        from ui import dty_schema_panel as _dsp
        _dsp.install(self, vm, _mfb_lay)

        self.tbl_machine = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_machine)
        self._enable_paste_for_table(self.tbl_machine)
        self.tbl_machine.verticalHeader().setVisible(False)
        self.tbl_machine.left.verticalHeader().setVisible(False)
        self.tbl_machine.horizontalHeader().setVisible(False)
        self.tbl_machine.horizontalHeader().setMinimumSectionSize(90)
        self.tbl_machine.setSelectionBehavior(QTableView.SelectItems)

        # Kontextmenü auf Spaltenkopf (Trials duplizieren)
        header = self.tbl_machine.horizontalHeader()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(
            self._on_machine_header_context)

        # Event-Filter für Rechtsklick auf die Titelspalte (Spalte 0)
        # Installiert direkt auf left/right QTableView (nicht viewport),
        # weil QContextMenuEvent bei DefaultContextMenu an die View geht.
        self._machine_ctx_filters = []
        for view in self.tbl_machine.findChildren(QTableView):
            f = _MachineContextMenuFilter(self, self.tbl_machine)
            view.installEventFilter(f)
            self._machine_ctx_filters.append(f)

        self.tbl_machine.setStyleSheet("""
            QTableView { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView::item:selected { background: #b7d6ff; color: black; }
        """
                                       .replace("#B5D7B5", accent_gridline())
                                       .replace("#E9F6E9", accent_tint()))
        vm.addWidget(self.tbl_machine, 1)
        self.tabs.addTab(self.tab_machine, "Machine Data")

        # R&D Machine Data Tab (initially hidden; shown by _build_rd_machine_tab when fields exist)
        self.tab_rd_machine = QWidget()
        vrd = QVBoxLayout(self.tab_rd_machine)
        vrd.setContentsMargins(24, 12, 24, 24)

        self.rd_machine_info = QLabel("")
        self.rd_machine_info.setStyleSheet("color: #666;")
        vrd.addWidget(self.rd_machine_info)

        self.tbl_rd_machine = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_rd_machine)
        self._enable_paste_for_table(self.tbl_rd_machine)
        self.tbl_rd_machine.verticalHeader().setVisible(False)
        self.tbl_rd_machine.left.verticalHeader().setVisible(False)
        self.tbl_rd_machine.horizontalHeader().setVisible(False)
        self.tbl_rd_machine.horizontalHeader().setMinimumSectionSize(90)
        self.tbl_rd_machine.setSelectionBehavior(QTableView.SelectItems)

        self._rd_machine_ctx_filters = []
        for view in self.tbl_rd_machine.findChildren(QTableView):
            f = _MachineContextMenuFilter(self, self.tbl_rd_machine, is_rd=True)
            view.installEventFilter(f)
            self._rd_machine_ctx_filters.append(f)

        self.tbl_rd_machine.setStyleSheet("""
            QTableView { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView::item:selected { background: #b7d6ff; color: black; }
        """
                                          .replace("#B5D7B5", accent_gridline())
                                          .replace("#E9F6E9", accent_tint()))
        vrd.addWidget(self.tbl_rd_machine, 1)
        # Tab wird erst durch _build_rd_machine_tab eingefügt

        # Conclusion tab (db/series_conclusion.py, shared with the web) - added in _load_record_inner
        from ui.widgets.conclusion_tab import ConclusionTab
        self.tab_conclusion = ConclusionTab()
        self.tab_conclusion.saved.connect(self._update_conclusion_tab_title)

        # Notes Tab (always visible)
        self.tab_notes = QWidget()
        vn = QVBoxLayout(self.tab_notes)
        vn.setContentsMargins(24, 16, 24, 24)
        vn.setSpacing(8)

        lbl_notes_hint = QLabel(
            "Notes for this Trial Series — saved automatically on focus loss or after a short pause.")
        lbl_notes_hint.setStyleSheet("color: #666; font-size: 11px;")
        vn.addWidget(lbl_notes_hint)

        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("Enter notes, observations or additional information here…")
        self.txt_notes.setAcceptRichText(False)
        self.txt_notes.setStyleSheet(
            "QTextEdit { border: 1px solid " + accent_gridline() + "; border-radius: 4px; "
                                                                   "padding: 8px; font-size: 12px; background: #ffffff; }"
                                                                   "QTextEdit:focus { border: 1px solid " + get_accent() + "; }"
        )
        vn.addWidget(self.txt_notes, 1)
        _cell_notes_ui.build_notes_list(self, vn)

        # Auto-save: timer (debounce 1.5 s after last keystroke)
        from PySide6.QtCore import QTimer
        self._notes_timer = QTimer(self)
        self._notes_timer.setSingleShot(True)
        self._notes_timer.setInterval(1500)
        self._notes_timer.timeout.connect(self._save_notes)
        self.txt_notes.textChanged.connect(self._on_notes_text_changed)

        # Also save on focus-out
        class _NotesFocusFilter(QObject):
            def __init__(self, parent_screen):
                super().__init__(parent_screen)
                self._screen = parent_screen

            def eventFilter(self, obj, event):
                if event.type() == QEvent.FocusOut:
                    self._screen._save_notes()
                return False

        self._notes_focus_filter = _NotesFocusFilter(self)
        self.txt_notes.installEventFilter(self._notes_focus_filter)

        # Notes tab is NOT added here — it is appended last in load_record
        # so it always appears as the rightmost tab regardless of which
        # dynamic lab tabs are currently visible.

        # Bottom-Bar
        root.addWidget(FooterBar())

    # ---------- Access / Save enablement ----------

    def _get_access_level(self) -> int:
        """Best-effort access level lookup.

        Important: This screen can be constructed before app_meta is fully
        initialised. Therefore we re-check when the screen is shown.
        """
        lvl = 0
        try:
            lvl = int(getattr(app_meta, "access_level", lambda: 0)() or 0)
        except Exception:
            try:
                user = getattr(app_meta, "current_user", {}) or {}
                lvl = int(user.get("access_level") or user.get("AccessLevel") or 0)
            except Exception:
                lvl = 0
        if getattr(self, "_recycle_preview", None) is not None:
            return min(lvl, 1)  # recycle bin preview: read only, like AccessLevel 1
        return lvl

    def set_recycle_preview(self, controller, banner: Optional[QWidget]) -> None:
        """Recycle bin preview on/off (ui/recycle_preview.py): read only plus
        a banner with the decision buttons above the title bar."""
        was = self._recycle_preview is not None
        self._recycle_preview = controller
        RECYCLE_PREVIEWS_OPEN[0] += (controller is not None) - was
        old = getattr(self, "_recycle_banner", None)
        if old is not None:
            old.hide()
            old.setParent(None)
            old.deleteLater()
        self._recycle_banner = banner
        if banner is not None:
            self._content_layout.insertWidget(0, banner)
        try:
            self._sync_save_button_access()
        except Exception:
            pass
        self.update()

    def on_tab_closed(self) -> None:
        """Called by TabbedNavigator when the tab holding this screen closes."""
        if self._recycle_preview is not None:
            self._recycle_preview.tab_closed()

    def _refresh_sidebar(self):
        """Baut die Sidebar-Navigation neu auf, falls sich der Access-Level
        seit dem letzten Aufbau geändert hat (siehe BacklogScreen._refresh_sidebar()
        für die ausführliche Begründung des Musters). Aktualisiert sonst nur
        die Badges. Rumpf in ui/widgets/sidebar_nav.py::refresh_lazy_sidebar()
        ausgelagert (2026-08-27, App-weiter Sidebar-Rollout)."""
        sidebar_nav.refresh_lazy_sidebar(self, self._get_access_level())

    def _sync_save_button_access(self) -> None:
        """Keep Save button state consistent with the behaviour of Ctrl+S."""
        try:
            can_write = self._get_access_level() > 1
            if hasattr(self, "btn_save") and self.btn_save:
                self.btn_save.setEnabled(bool(can_write))
                if not can_write:
                    self.btn_save.setToolTip("Read only (AccessLevel 1)")
                else:
                    self.btn_save.setToolTip("")

            # Upload deliberately stays enabled even for read-only users
            # (AccessLevel 1) - only deleting is reserved for the owner/
            # superuser (see ExperimentRequestImagesDialog._can_delete()).

            if hasattr(self, "btn_statimat_import") and self.btn_statimat_import:
                self.btn_statimat_import.setEnabled(bool(can_write))
                if not can_write:
                    self.btn_statimat_import.setToolTip("Write access required (AccessLevel > 1)")
                else:
                    self.btn_statimat_import.setToolTip("")

            if hasattr(self, "btn_itemat_import") and self.btn_itemat_import:
                self.btn_itemat_import.setEnabled(bool(can_write))
                if not can_write:
                    self.btn_itemat_import.setToolTip("Write access required (AccessLevel > 1)")
                else:
                    self.btn_itemat_import.setToolTip("")

            if hasattr(self, "btn_add_reference") and self.btn_add_reference:
                self.btn_add_reference.setEnabled(bool(can_write) and has_reference_columns())
            if hasattr(self, "btn_copy_trials") and self.btn_copy_trials:
                self.btn_copy_trials.setEnabled(bool(can_write))
        except Exception:
            # If anything goes wrong, keep button enabled and let _save_all guard.
            pass

    UNSAVED_MARK = "● "

    def unsaved_count(self) -> int:
        """Number of changed, not yet saved cells over all tables."""
        n = 0
        for _name, model in self._iter_save_models():
            try:
                n += len({(r, c) for r, c, *_ in getattr(model, "_dirty", [])})
            except Exception:
                continue
        return n

    def _update_unsaved_indicator(self) -> None:
        n = self.unsaved_count()
        if n != self._unsaved_shown:
            was = self._unsaved_shown
            self._unsaved_shown = n
            if n:
                self.btn_save.setText(f"Save ({n})")
                self.btn_save.setToolTip(f"{n} unsaved change{'s' if n != 1 else ''} (yellow cells) - Ctrl+S")
                self.btn_save.setStyleSheet("QPushButton{background:#E8890C; color:white; font-weight:700;}"
                                            "QPushButton:hover{background:#C97508;}")
            else:
                self.btn_save.setText("Save")
                self.btn_save.setToolTip("")
                self.btn_save.setStyleSheet("")
            if was > 0 and n == 0:  # saved/discarded -> repaint the yellow cells away
                for t in self.findChildren(FrozenFirstColumnTable):
                    for v in (t.top_left, t.top_right, t.bottom_left, t.bottom_right):
                        v.viewport().update()
        self._apply_unsaved_tab_mark(n > 0)

    def _apply_unsaved_tab_mark(self, dirty: bool) -> None:
        """'● ' in front of this screen's tab label while something is unsaved
        (re-applied on every tick - the tab label is rewritten on navigation)."""
        try:
            from ui.widgets.tab_container import TabbedNavigator
            stack = self.parentWidget()
            nav = stack
            while nav is not None and not isinstance(nav, TabbedNavigator):
                nav = nav.parentWidget()
            if nav is None or stack is None or getattr(stack, "currentWidget", lambda: None)() is not self:
                return
            idx = nav.indexOf(stack)
            if idx < 0:
                return
            text = nav.tabText(idx)
            base = text[len(self.UNSAVED_MARK):] if text.startswith(self.UNSAVED_MARK) else text
            want = (self.UNSAVED_MARK + base) if dirty else base
            if want != text:
                nav.setTabText(idx, want)
        except RuntimeError:
            pass

    def _init_undo(self) -> None:
        """Ctrl+Z / Ctrl+Y (and Ctrl+Shift+Z) for unsaved cell edits. Own
        method: _build_ui imports QShortcut locally further down, which
        would shadow the module import there."""
        self._undo = _UndoManager(self)
        for key, slot in ((QKeySequence.Undo, self._undo.undo), (QKeySequence.Redo, self._undo.redo),
                          (QKeySequence("Ctrl+Shift+Z"), self._undo.redo)):
            sc = QShortcut(key, self)
            sc.setContext(Qt.WidgetWithChildrenShortcut)  # open cell editors / notes keep their own Ctrl+Z
            sc.activated.connect(slot)

    def _reveal_cell(self, model, idx) -> None:
        """After Ctrl+Z / Ctrl+Y: show and select the (first) changed cell."""
        for t in self.findChildren(FrozenFirstColumnTable):
            if t.model() is model:
                try:
                    t.selectionModel().setCurrentIndex(idx, QItemSelectionModel.ClearAndSelect)
                    t.bottom_right.scrollTo(idx)
                except Exception:
                    pass
                return

    def confirm_close_with_unsaved(self) -> bool:
        """Asks Save / Discard / Cancel if something is unsaved. True = go on."""
        if getattr(self, "tab_conclusion", None) is not None:
            self.tab_conclusion.ask_save_if_dirty()
        if not self._has_unsaved():
            return True
        n = self.unsaved_count()
        res = QMessageBox.question(
            self, "Unsaved changes",
            f"There {'is' if n == 1 else 'are'} {n} unsaved change{'s' if n != 1 else ''} "
            f"(yellow cells) in Show Experiment {getattr(self, '_experiment_id_txt', '') or ''}.\n\n"
            "Save before closing?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if res == QMessageBox.Cancel:
            return False
        if res == QMessageBox.Save:
            self._save_all()
            return not self._has_unsaved()  # saving refused (e.g. typo check "go back")
        return True

    def hideEvent(self, event):
        if self._unsaved_timer is not None:
            self._unsaved_timer.stop()
        return super().hideEvent(event)

    def showEvent(self, event):
        if self._unsaved_timer is None:
            self._unsaved_timer = QTimer(self)
            self._unsaved_timer.setInterval(400)
            self._unsaved_timer.timeout.connect(self._update_unsaved_indicator)
        self._unsaved_timer.start()
        self._update_unsaved_indicator()
        # Ensure button is enabled/disabled with up-to-date user state.
        try:
            self._sync_save_button_access()
        except Exception:
            pass
        try:
            self._refresh_sidebar()
        except Exception:
            pass
        return super().showEvent(event)

    def keyPressEvent(self, event):
        # Fallback für Ctrl+S falls QShortcut in verschachtelten Containern nicht feuert.
        if event.key() == Qt.Key_S and (event.modifiers() & Qt.ControlModifier):
            self._save_all()
            event.accept()
            return
        super().keyPressEvent(event)

    # ---------- Navigation & Save ----------

    def _open_boards(self) -> None:
        if self._series_pk is None or not callable(getattr(app_meta, "open_canvas_board", None)):
            return
        app_meta.open_canvas_board(series_id=self._series_pk)

    def _refresh_boards_button(self) -> None:
        """Board button: visible with the Canvas right and the table; shows the number of boards."""
        try:
            from db import canvas_boards as cb
            from db import feature_access as fa
            ok = bool(self._series_pk) and cb.table_ready() and fa.can_use("canvas")
            self.btn_boards.setVisible(ok)
            if ok:
                n = cb.board_counts([self._series_pk]).get(int(self._series_pk), 0)
                self.btn_boards.setText(f"🖼 Board ({n})" if n else "🖼 Board")
        except Exception:
            self.btn_boards.setVisible(False)

    def _open_report(self) -> None:
        """Opens the report screen for the current trial series.

        Ctrl+click opens a fresh SmartChart instance in a new tab instead
        (user request 2026-09-01: keep multiple SmartCharts open at once) -
        same pattern as Ctrl+click elsewhere in the app (e.g. sidebar/All
        Experiments/Backlog)."""
        if self._series_pk is None:
            return
        ctrl_held = bool(QApplication.keyboardModifiers() & Qt.ControlModifier)
        print(f"[DEBUG _open_report] series_pk={self._series_pk} ctrl_held={ctrl_held} "
              f"on_open_report_in_new_tab={self.on_open_report_in_new_tab} "
              f"self={self!r}")
        if ctrl_held and callable(self.on_open_report_in_new_tab):
            self.on_open_report_in_new_tab(self._series_pk)
        elif callable(self.on_open_report):
            self.on_open_report(self._series_pk)

    def _refresh_saved_reports_dropdown(self) -> None:
        """Füllt das "Saved Reports"-Dropdown mit allen gespeicherten Smart-
        Chart-Reports für die aktuelle TrialSeries (siehe _build_ui()).
        Dropdown + Go-Button bleiben unsichtbar, solange es keinen einzigen
        Report für diese Series gibt."""
        self._refresh_boards_button()
        self.cmb_saved_reports.clear()
        if not self._series_pk or not table_exists("tblSmartChartReport"):
            self.cmb_saved_reports.setVisible(False)
            self.btn_go_saved_report.setVisible(False)
            return
        try:
            rows = fetch_all(
                "SELECT ID, Title, Author FROM tblSmartChartReport "
                "WHERE SeriesPK=? AND IsTemplate=0 ORDER BY UpdatedAt DESC",
                [self._series_pk],
            )
        except Exception:
            rows = []
        has_reports = bool(rows)
        for r in rows:
            title = str(r.get("Title") or "").strip() or "(untitled)"
            author = str(r.get("Author") or "").strip()
            label = f"{title} ({author})" if author else title
            self.cmb_saved_reports.addItem(label, int(r["ID"]))
        self.cmb_saved_reports.setVisible(has_reports)
        self.btn_go_saved_report.setVisible(has_reports)

    def _open_selected_saved_report(self) -> None:
        """"Go!"-Button neben dem Saved-Reports-Dropdown - öffnet den
        Report-Screen direkt mit dem gerade ausgewählten Report geladen.

        Ctrl+click opens a fresh SmartChart instance here too, in a new tab
        instead of the shared singleton (see _open_report())."""
        if self._series_pk is None:
            return
        report_id = self.cmb_saved_reports.currentData()
        if report_id is None:
            return
        ctrl_held = bool(QApplication.keyboardModifiers() & Qt.ControlModifier)
        if ctrl_held and callable(self.on_open_report_in_new_tab):
            self.on_open_report_in_new_tab(self._series_pk, report_id)
        elif callable(self.on_open_report):
            self.on_open_report(self._series_pk, report_id)

    def set_back_target(self, label: Optional[str], callback: Optional[Callable]):
        """Merkt sich Label + Sprungziel für eine Rückwärts-Navigation, ohne
        UI-Gegenstück (der frühere Back-Chip wurde 2026-08-27 auf
        Nutzerwunsch entfernt - siehe _build_ui()). Bleibt als reines
        Bookkeeping bestehen, da main.py an mehreren Stellen weiterhin danach
        ruft (Backlog/All Experiments/Manage Yarn/Manage Jets/...)."""
        self.on_back_all_experiments = callback
        self._back_label = label

    def _back_all_experiments(self):
        if self._has_unsaved():
            res = QMessageBox.question(
                self,
                "Unsaved changes",
                "There are unsaved changes. Save now?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes,
            )
            if res == QMessageBox.Cancel:
                return
            if res == QMessageBox.Yes:
                self._save_all()
        self._close_series_pdfs_viewer()
        self._ys_cache = {}  # Screen verlassen -> Cache leeren
        if callable(getattr(self, "on_back_all_experiments", None)):
            self.on_back_all_experiments()
        else:
            self.on_back_home()

    def closeEvent(self, event):
        # If this screen is closed/destroyed, also close the modeless PDF viewer.
        try:
            self._close_series_pdfs_viewer()
        except Exception:
            pass
        return super().closeEvent(event)

    def _close_series_pdfs_viewer(self) -> None:
        dlg = getattr(self, "_series_pdfs_viewer", None)
        if dlg is None:
            return
        try:
            # Close and release references (prevents zombie windows when navigating away)
            dlg.close()
        except Exception:
            pass
        self._series_pdfs_viewer = None

    def _has_unsaved(self) -> bool:
        # Generic check: any registered model has dirty cells
        for _name, model in self._iter_save_models():
            try:
                if len(getattr(model, "_dirty", [])) > 0:
                    return True
            except Exception:
                continue
        return False

    def _confirm_proceed_despite_unsaved(self) -> bool:
        """Same "Unsaved changes - Save now?" guard used for back-navigation
        (see _back_home/_back_all_experiments), reused before any action
        that reloads/rebuilds tabs (e.g. copying trials) and would otherwise
        silently discard pending edits without ever asking. Returns True if
        the caller should proceed (nothing was unsaved, or the user chose
        Save or Discard), False if the caller should abort (Cancel)."""
        if not self._has_unsaved():
            return True
        res = QMessageBox.question(
            self,
            "Unsaved changes",
            "There are unsaved changes. Save now?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if res == QMessageBox.Cancel:
            return False
        if res == QMessageBox.Yes:
            self._save_all()
        return True

    def _stamp_trial_timestamp(self, trial_id: int) -> int:
        """Setzt NOW() in tblTrial.[Timestamp] **und** den aktuellen User in tblTrial.[User]
        für die angegebene Trial-ID (db/series_save.stamp_trial_timestamp)."""
        try:
            user = getattr(app_meta, "current_user", {}) or {}
        except Exception:
            user = {}
        return _series_save.stamp_trial_timestamp(trial_id, user if isinstance(user, dict) else {})

    def _open_help(self):
        from ui.widgets.multilang_help import show_help
        from ui.widgets.help_texts_show_experiment import TEXTS
        show_help(TEXTS, self)

    def _on_refresh(self):
        """Lädt den aktuellen Screen neu (F5), behält aktiven Tab."""
        try:
            exp_pk = getattr(self, '_exp_pk', None)
            series_pk = getattr(self, '_series_pk', None)
            exp_id = getattr(self, '_experiment_id_txt', '')
            if exp_pk is not None and series_pk is not None:
                # Aktiven Tab-Index merken
                active_idx = self.tabs.currentIndex()
                active_tab = self.tabs.widget(active_idx)
                self.load_record(exp_pk, series_pk, exp_id)
                # Gleichen Tab wieder aktivieren
                try:
                    if active_tab is not None:
                        idx = self.tabs.indexOf(active_tab)
                        if idx >= 0:
                            self.tabs.setCurrentIndex(idx)
                        else:
                            self.tabs.setCurrentIndex(min(active_idx, self.tabs.count() - 1))
                except Exception:
                    pass
        except Exception as e:
            QMessageBox.warning(self, 'Error', str(e))

    def _confirm_plausible_values(self) -> bool:
        """False = the user wants to correct unusual values first."""
        try:
            from db.plausibility import find_unusual
            machine_id = (getattr(self, "_machine_cache", None) or {}).get("machine_id")
            found = []
            for attr, tbl_attr in (("model_machine", "tbl_machine"), ("model_rd_machine", "tbl_rd_machine")):
                for e in find_unusual(getattr(self, attr, None), machine_id):
                    found.append((attr, tbl_attr, e))
        except Exception:
            return True
        if not found:
            return True
        lines = "\n".join("•  " + e["text"] for _a, _t, e in found[:15])
        more = f"\n… and {len(found) - 15} more" if len(found) > 15 else ""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Unusual values")
        box.setText(f"{'This value is' if len(found) == 1 else 'These values are'} unusual for this machine "
                    f"(compared with earlier trials). Typo?\n\n{lines}{more}")
        btn_back = box.addButton("Go back and check", QMessageBox.RejectRole)
        box.addButton("Save anyway", QMessageBox.AcceptRole)
        box.setDefaultButton(btn_back)
        box.exec()
        if box.clickedButton() is not btn_back:
            try:
                from db.usage_log import log_usage_event
                log_usage_event("feature", "plausibility_save_anyway", str(len(found)))
            except Exception:
                pass
            return True
        attr, tbl_attr, e = found[0]
        try:
            model, tbl = getattr(self, attr), getattr(self, tbl_attr)
            if attr == "model_machine":
                self.tabs.setCurrentWidget(self.tab_machine)
            idx = model.index(model._n_hdr + e["row"], e["col"] + 1)
            tbl.setCurrentIndex(idx)
            tbl.scrollTo(idx)
        except Exception:
            pass
        return False

    def _confirm_no_conflicts(self) -> bool:
        """Save conflicts (db/series_save.find_conflicts, same rule as the web app): False = do not save now."""
        found = []
        for name, model in self._iter_save_models():
            if not getattr(model, "_dirty", None) or not hasattr(model, "conflict_items"):
                continue
            try:
                found += [dict(x, model=model) for x in _series_save.find_conflicts(
                    model.conflict_items(), unit_scale=getattr(model, "_unit_scale", 1.0) or 1.0,
                    unit_field=getattr(model, "_unit_scale_field", None))]
            except Exception:
                continue
        if not found:
            return True
        lines = "\n".join(f"• {x['where']}: now {x['current'] or '–'}"
                           + (f" ({x['by']}, {x['at']})" if x.get('by') or x.get('at') else "")
                           + f" - yours {x['new'] or '–'}" for x in found[:12])
        more = f"\n… and {len(found) - 12} more" if len(found) > 12 else ""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Changed in the meantime")
        box.setText("Someone else changed these values after you opened the series:\n\n" + lines + more
                    + "\n\nWhich values should stay?")
        btn_mine = box.addButton("Save mine anyway", QMessageBox.AcceptRole)
        btn_theirs = box.addButton("Keep theirs (drop mine)", QMessageBox.DestructiveRole)
        box.addButton("Cancel", QMessageBox.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        try:
            from db.usage_log import log_usage_event
            log_usage_event("feature", "save_conflict",
                            "mine" if clicked is btn_mine else "theirs" if clicked is btn_theirs else "cancel")
        except Exception:
            pass
        if clicked is btn_mine:
            return True
        if clicked is btn_theirs:
            # drop my edits of the conflicting cells, then reload so the other values show
            for x in found:
                m = x["model"]
                b = x["binding"]
                m._dirty = [d for d in m._dirty if m._binding[d[0]][d[1]] is not b]
            self._on_refresh_after_conflict()
        return False

    def _on_refresh_after_conflict(self) -> None:
        """Reload the series after "keep theirs" - remaining edits of other cells are kept only if none are left."""
        if self._has_unsaved():
            QMessageBox.information(self, "Changed in the meantime",
                                    "Your other changes are still unsaved. Save them, then refresh (F5) to see the "
                                    "other values.")
            return
        try:
            self._on_refresh()
        except Exception:
            pass

    def _save_all(self):
        # Access level 1 (or recycle bin preview): read-only
        if self._get_access_level() <= 1:
            return

        total = 0

        # Offene Editoren in allen Pivot-Tabellen committen, damit der aktuelle
        # Zellwert noch in _dirty landet bevor save_dirty() aufgerufen wird.
        _tbl_attrs = [
            "tbl_machine", "tbl_rd_machine", "tbl_titer", "tbl_stat", "tbl_stat_ds",
            "tbl_ekb", "tbl_hot_air_shrinkage", "tbl_hot_water_shrinkage",
            "tbl_aty_shrinkage", "tbl_water", "tbl_itemat", "tbl_itemat_plus",
            "tbl_dtyomat", "tbl_rapid600",
        ]
        for _attr in _tbl_attrs:
            _tbl = getattr(self, _attr, None)
            if _tbl is None:
                continue
            try:
                _views = _tbl.findChildren(QTableView) or []
                if not _views:
                    _views = [_tbl]
                for _view in _views:
                    try:
                        # Aktiven Editor committen: persistentEditorWidget ist nicht nötig —
                        # setCurrentIndex auf Invalid schliesst den Editor und löst
                        # commitData → setData → _dirty aus.
                        if _view.state() == QAbstractItemView.EditingState:
                            idx = _view.currentIndex()
                            _view.setCurrentIndex(QModelIndex())
                            _view.setCurrentIndex(idx)
                    except Exception:
                        pass
            except Exception:
                pass

        # Someone else (web or another desktop) changed a cell since it was loaded -> ask first
        if not self._confirm_no_conflicts():
            return

        # Plausibility check of machine settings (db/plausibility.py): one
        # warning for all unusual values, the user can save anyway
        if not self._confirm_plausible_values():
            return

        # Vor dem Speichern: betroffene Trial-IDs sammeln, falls Tension-Felder geändert wurden
        # (Tension-Felder: db/series_save.stamp_trial_ids)
        trial_ids_to_stamp = set()
        try:
            if hasattr(self, "model_machine") and self.model_machine:
                _mm = self.model_machine
                trial_ids_to_stamp = _series_save.stamp_trial_ids(
                    [(_mm.get_binding(rr, cc), _newtext)
                     for (rr, cc, _newtext) in list(getattr(_mm, "_dirty", []))])
        except Exception:
            trial_ids_to_stamp = set()

        # --- Generic save handling for all registered models ---
        for name, model in self._iter_save_models():
            try:
                model._log_series_id = self._series_pk  # change history (db/change_log.py)
            except Exception:
                pass
            try:
                if name == "model_itemat":
                    dirty_before = len(getattr(model, "_dirty", []))
                    total += model.save_dirty()
                    if dirty_before > 0:
                        total += self._recompute_itemat_intermingling()
                elif name == "model_itemat_plus":
                    dirty_before = len(getattr(model, "_dirty", []))
                    total += model.save_dirty()
                    if dirty_before > 0:
                        total += self._recompute_itemat_plus()  # IP(t) und CV@0 berechnen
                else:
                    total += model.save_dirty()
            except Exception:
                # Einzelne Model-Fehler sollen den Save nicht komplett verhindern
                continue

        # Nach dem Speichern: Timestamp für betroffene Trials setzen
        stamped = 0
        for _tid in list(trial_ids_to_stamp):
            if _tid is not None:
                try:
                    stamped += self._stamp_trial_timestamp(int(_tid))
                except Exception:
                    pass
        total += stamped

        # Feature-Tracking: multi_ply (stealth, kein Crash)
        try:
            self._track_multi_ply()
        except Exception:
            pass

        # No "Saved" message box any more (Nutzerwunsch 2026-10-16): the
        # yellow cells / "Save (n)" / tab dot disappear - that is the
        # confirmation. Saved values can't be undone with Ctrl+Z.
        # Plus a short green tick (Nutzerwunsch 2026-10-19) - only if
        # something was saved and nothing is left over (failed model).
        if not self._has_unsaved():
            self._undo.clear()
            if total > 0:
                from ui.widgets.save_tick import show_save_tick
                show_save_tick(self)
        self._update_unsaved_indicator()
        """Gibt Debug-Info über den Save-Zustand zurück (für Diagnose)."""
        lines = []
        models = list(self._iter_save_models())
        lines.append(f"Models registered: {len(models)}")
        for name, m in models:
            dirty = getattr(m, "_dirty", [])
            lines.append(f"  {name}: {len(dirty)} dirty entries")
        return "\n".join(lines)

    def _track_multi_ply(self) -> None:
        """Trägt einen Eintrag in tblFeatureUsage ein, wenn in mindestens einem Trial
        ein Ply 2-N einen anderen Wert hat als Ply 1 in derselben Parameterzeile.
        Wird stealth nach _save_all aufgerufen – darf nie einen Fehler werfen.
        """
        col_specs = getattr(self, "_machine_col_specs", None)
        model = getattr(self, "model_machine", None)
        if not col_specs or not model:
            return

        # rule: db/series_save.multi_ply_differs (shared with the web app)
        matrix = model._matrix
        found_diff = _series_save.multi_ply_differs(
            col_specs, len(getattr(model, "_row_titles", [])), model.get_binding,
            lambda r, c: matrix[r][c] if 0 <= c < len(matrix[r]) else None)
        if not found_diff:
            return

        user_id = app_meta.current_user.get("id") if app_meta.current_user else None
        if user_id is None:
            return
        _series_save.log_multi_ply(user_id, getattr(self, "_series_pk", None))

    # ---------- Daten laden ----------

    def _load_trials(self):
        # data: db/series_tables.load_trials (shared with the web app) - reference
        # samples first, so the benchmark is always the leftmost column(s).
        st = _series_tables.load_trials(self._series_pk)
        self._series_trials = st
        self._trials = st.trials
        self._trial_ids = st.trial_ids
        self._trial_vnos = st.trial_vnos
        self._reference_names = st.reference_names
        self._trial_labels = st.labels
        if getattr(self, "btn_ref_compare", None) is not None:
            self.btn_ref_compare.setVisible(bool(self._trial_ids))
        # Invalidate the per-load cache in _get_jet_info_rows() - new trial
        # list means its cached result (if any) is stale.
        self._jet_info_rows_cache = None

    def _series_trials_data(self):
        """The current trial columns as db/series_tables.SeriesTrials (the lists
        may have been changed in place, e.g. after copying a trial)."""
        return _series_tables.SeriesTrials(
            series_id=self._series_pk, trials=self._trials, trial_ids=self._trial_ids,
            trial_vnos=getattr(self, "_trial_vnos", []), reference_names=getattr(self, "_reference_names", {}),
            labels=self._trial_labels)

    def _model_from_pivot(self, p):
        """db/series_tables.LabPivot -> editable PivotEditModel (same cells as the old per-tab code).
        Columns = the trials, unless the pivot brings its own col_titles (Jet Air: pressure steps)."""
        model = PivotEditModel(row_titles=p.row_titles,
                               col_titles=self._trial_labels if p.col_titles is None else p.col_titles,
                               row_validators=p.validators)
        if p.extra.get("unit_scale"):
            # Jet Air in l/min: shown converted, stored in Nm3/h (see build_jet_air)
            model.set_unit_scale(p.extra["unit_scale"], p.extra.get("unit_field"))
        for r_idx, row in enumerate(p.cells):
            for c_idx, (value, binding) in enumerate(row):
                model.set_cell(r_idx, c_idx, value, binding)
        return model

    def _init_machine_cache(self):
        """Lädt alle statischen DB-Daten für _build_machine_tab einmalig in den Cache
        (db/machine_data.load_machine_cache, shared with the web app)."""
        self._machine_cache = _machine_data.load_machine_cache(self._series_pk, self._trial_ids)

    def _refresh_materials_box(self):
        """Lädt die Materialliste für die aktuelle TrialSeries und zeigt sie an."""
        try:
            txt = self._load_materials_summary()
            if not txt:
                txt = "—"
        except Exception as e:
            txt = f"— (error while loading: {e})"
        if hasattr(self, "lbl_material_value"):
            self.lbl_material_value.setText(txt)

    def _refresh_experiment_request_link(self) -> None:
        """Loads linked ExperimentRequest ID from tblExperimente (if any) -
        db/experiment_requests.request_id_for_experiment (shared with the web)."""
        from db import experiment_requests as er
        self._experiment_request_id = er.request_id_for_experiment(self._exp_pk)

    def _sync_experiment_request_icon(self) -> None:
        """Shows/hides the Experiment Request icon depending on whether a request is linked."""
        try:
            rid = self._experiment_request_id
            visible = rid not in (None, '', 0, '0')
            if hasattr(self, 'btn_experiment_request') and self.btn_experiment_request is not None:
                self.btn_experiment_request.setVisible(bool(visible))
        except Exception:
            pass

    # ---------- TrialSeries Images ----------

    @staticmethod
    def _current_user_id() -> Any | None:
        cu = getattr(app_meta, "current_user", {}) or {}
        return cu.get("id")

    def _series_has_images(self, series_id: Any) -> bool:
        """True if at least one image row exists for this TrialSeries."""
        if series_id in (None, ""):
            return False
        try:
            with get_connection() as cn:
                cur = cn.cursor()
                cur.execute(
                    "SELECT 1 FROM [tblTrialSeriesImage] WHERE [TrialSeriesID]=? LIMIT 1",
                    [series_id],
                )
                return cur.fetchone() is not None
        except Exception:
            return False

    def _fetch_series_images(self, series_id: Any) -> List[Dict[str, str]]:
        """Attachments of the series (db/series_attachments.list_images, shared with the web app)."""
        from db.series_attachments import list_images
        return list_images(series_id)

    def _sync_trialseries_images_icon(self) -> None:
        """Show / hide the images icon depending on whether images exist."""
        btn = getattr(self, "btn_show_series_images", None)
        if not btn:
            return
        sid = self._series_pk
        btn.setVisible(self._series_has_images(sid))

    def _open_series_images_dialog(self) -> None:
        sid = self._series_pk
        if sid in (None, ""):
            return
        try:
            imgs = self._fetch_series_images(sid)
            if not imgs:
                QMessageBox.information(self, "Images", "No images attached to this TrialSeries.")
                self._sync_trialseries_images_icon()
                return

            from ui.screen_create_experiment_request import ExperimentRequestImagesDialog

            title = self.lbl_small_title.text() or "TrialSeries"
            dlg = ExperimentRequestImagesDialog(
                self,
                f"TrialSeries images – {title}",
                imgs,
                table_name="tblTrialSeriesImage",
                fk_field="TrialSeriesID",
                fk_value=sid,
            )
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Images", str(e))

    def _upload_series_images(self) -> None:
        """Button-Handler: Bilder waehlen, speichern, DB-Records anlegen
        (db/series_uploads.upload_paths, shared with the web app: copy under a
        random name, tblTrialSeriesImage row, Garnspiegel analysis, tracking).

        Upload is allowed for read-only users too (AccessLevel 1) - only
        deleting is reserved for the owner/superuser (see
        ExperimentRequestImagesDialog._can_delete())."""
        sid = self._series_pk
        if sid in (None, ""):
            QMessageBox.warning(self, "Upload", "No trial series selected.")
            return

        try:
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "Select images",
                "",
                "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp *.heic *.heif);;All files (*.*)",
            )
            if not files:
                return

            from db.series_uploads import upload_paths
            stored_any, errors = upload_paths("image", self._current_user_id(), sid, files)

            msg = f"{stored_any} image(s) uploaded."
            if errors:
                msg += "\n\nErrors:\n" + "\n".join(errors)
                QMessageBox.warning(self, "Upload finished with errors", msg)
            else:
                QMessageBox.information(self, "Upload finished", msg)

            self._sync_trialseries_images_icon()

        except Exception as e:
            QMessageBox.critical(self, "Upload Error", str(e))

    # ---------- TrialSeries PDFs ----------

    def _statimat_import(self) -> None:
        """Import STATIMAT PDF(s) attached to this TrialSeries into lab tables.

        Implementierung ausgelagert nach ui/screen_show_experiment_pdf_import.py
        (reiner Code-Move, keine Verhaltensaenderung; siehe dort fuer Details).
        """
        from ui.screen_show_experiment_pdf_import import statimat_import_impl
        statimat_import_impl(self)

    def _itemat_import(self) -> None:
        """Import Itemat Lab PDF(s) attached to this TrialSeries into tblLaborItematLab.

        Implementierung ausgelagert nach ui/screen_show_experiment_pdf_import.py
        (reiner Code-Move, keine Verhaltensaenderung; siehe dort fuer Details).
        """
        from ui.screen_show_experiment_pdf_import import itemat_import_impl
        itemat_import_impl(self)

    def _series_has_pdfs(self, series_id: Any) -> bool:
        if series_id in (None, ""):
            return False
        try:
            with get_connection() as cn:
                cur = cn.cursor()
                cur.execute(
                    "SELECT 1 FROM [tblTrialSeriesPDF] WHERE [TrialSeriesID]=? LIMIT 1",
                    [series_id],
                )
                return cur.fetchone() is not None
        except Exception:
            return False

    def _fetch_series_pdfs(self, series_id: Any) -> List[Dict[str, str]]:
        """Attachments of the series (db/series_attachments.list_pdfs, shared with the web app)."""
        from db.series_attachments import list_pdfs
        return list_pdfs(series_id)

    def _load_notes(self, ts_row: dict) -> None:
        """Load Notes from tblTrialSeries row into txt_notes widget."""
        if self.txt_notes is None:
            return
        try:
            if self._notes_timer is not None:
                self._notes_timer.stop()
            notes_val = ts_row.get("Notes") or ""
            self._notes_last_saved = notes_val
            # Block signals to avoid triggering auto-save on load
            self.txt_notes.blockSignals(True)
            self.txt_notes.setPlainText(notes_val)
            self.txt_notes.blockSignals(False)
            # read-only users / recycle-bin preview: notes cannot be changed (db/series_actions.can_save_notes)
            self.txt_notes.setReadOnly(self._get_access_level() < 2)
        except Exception:
            pass

    def _update_notes_tab_style(self) -> None:
        """Hebt den Notes-Tab fett hervor wenn Notizen vorhanden sind."""
        try:
            if self.tab_notes is None:
                return
            idx = self.tabs.indexOf(self.tab_notes)
            if idx < 0:
                return
            has_notes = bool(
                self.txt_notes is not None
                and self.txt_notes.toPlainText().strip()
            )
            n_cell = len(getattr(self, "_cell_notes", None) or [])
            title = f"Notes ({n_cell})" if n_cell else "Notes"
            bar = self.tabs.tabBar()
            if has_notes:
                bar.setTabText(idx, "🔴 " + title)
            else:
                bar.setTabText(idx, title)
        except Exception:
            pass

    def _on_notes_text_changed(self) -> None:
        """Restart debounce timer on every keystroke."""
        try:
            if self._notes_timer is not None:
                self._notes_timer.start()
            self._update_notes_tab_style()
        except Exception:
            pass

    def _save_notes(self) -> None:
        """Persist Notes to DB if changed."""
        try:
            if self._notes_timer is not None:
                self._notes_timer.stop()
            if self.txt_notes is None or self._series_pk is None:
                return
            current = self.txt_notes.toPlainText()
            if current == self._notes_last_saved:
                return
            from db.series_actions import can_save_notes, save_notes   # Qt-free, shared with the web app
            if not can_save_notes(self._get_access_level()):
                return
            save_notes(self._series_pk, current)
            self._notes_last_saved = current
        except Exception:
            pass

    def _sync_trialseries_pdfs_icon(self) -> None:
        btn = getattr(self, "btn_show_series_pdfs", None)
        if not btn:
            return
        sid = self._series_pk
        btn.setVisible(self._series_has_pdfs(sid))

    def _open_series_pdfs_dialog(self) -> None:
        sid = self._series_pk
        if sid in (None, ""):
            return
        try:
            # If already open, just bring it to front.
            existing = getattr(self, "_series_pdfs_viewer", None)
            if existing is not None:
                try:
                    existing.raise_()
                    existing.activateWindow()
                    return
                except Exception:
                    # If something went wrong, fall back to re-creating it.
                    try:
                        existing.close()
                    except Exception:
                        pass
                    self._series_pdfs_viewer = None

            pdfs = self._fetch_series_pdfs(sid)
            if not pdfs:
                QMessageBox.information(self, "PDFs", "No PDFs attached to this TrialSeries.")
                self._sync_trialseries_pdfs_icon()
                return

            from ui.screen_create_experiment_request import ExperimentRequestPdfsDialog

            title = self.lbl_small_title.text() or "TrialSeries"
            dlg = ExperimentRequestPdfsDialog(
                self,
                f"TrialSeries PDFs – {title}",
                pdfs,
                table_name="tblTrialSeriesPDF",
                fk_field="TrialSeriesID",
                fk_value=sid,
            )
            # IMPORTANT: Modeless, so the user can keep editing this screen.
            dlg.setModal(False)
            dlg.setWindowModality(Qt.NonModal)
            dlg.setAttribute(Qt.WA_DeleteOnClose, True)
            self._series_pdfs_viewer = dlg
            try:
                dlg.destroyed.connect(lambda *_: setattr(self, "_series_pdfs_viewer", None))
            except Exception:
                pass
            dlg.show()
        except Exception as e:
            QMessageBox.critical(self, "PDFs", str(e))
        finally:
            # In case user deleted everything in the dialog
            try:
                self._sync_trialseries_pdfs_icon()
            except Exception:
                pass

    def _upload_series_pdfs(self) -> None:
        """PDFs waehlen und speichern (db/series_uploads.upload_paths, shared
        with the web app).

        Upload is allowed for read-only users too (AccessLevel 1) - only
        deleting is reserved for the owner/superuser (see
        ExperimentRequestPdfsDialog._can_delete())."""
        sid = self._series_pk
        if sid in (None, ""):
            QMessageBox.warning(self, "Upload", "No trial series selected.")
            return

        try:
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "Select PDFs",
                "",
                "PDF (*.pdf);;All files (*.*)",
            )
            if not files:
                return

            from db.series_uploads import upload_paths
            stored_any, errors = upload_paths("pdf", self._current_user_id(), sid, files)

            msg = f"{stored_any} PDF(s) uploaded."
            if errors:
                msg += "\n\nErrors:\n" + "\n".join(errors)
                QMessageBox.warning(self, "Upload finished with errors", msg)
            else:
                QMessageBox.information(self, "Upload finished", msg)

            self._sync_trialseries_pdfs_icon()

        except Exception as e:
            QMessageBox.critical(self, "Upload Error", str(e))

    def _open_experiment_request_popup(self) -> None:
        rid = self._experiment_request_id
        if rid in (None, '', 0, '0'):
            return
        try:
            dlg = _ExperimentRequestReadOnlyDialog(self, rid)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def _load_materials_summary(self) -> str:
        """
        Liest Yarn-Zusammensetzung aus tblTrialSettings (Trial-Ebene).
        Pro Ply wird das häufigste Garn angezeigt (robust gegen vereinzelte Datenfehler).

        Gibt Rich-Text (HTML) zurück: jedes Ply ist ein Link-Anchor
        ("yarn:<YarnID>") mit Spulen-Symbol dahinter ("stock:"/"nostock:");
        ein Klick auf Garn oder grünes Symbol öffnet die Lagerplätze
        (_on_material_label_link_activated).
        """
        if not getattr(self, "_series_pk", None):
            return ""

        from db.yarn_spools import series_materials   # Qt-free, shared with the web app
        result = [(m["ply"], m["yarn_id"], m["name"]) for m in series_materials(self._series_pk)]
        if not result:
            return ""

        # Spulen-Symbol pro Ply (am Lager / nicht am Lager), Klick -> Lagerplaetze
        stock = _yarn_locations.load_stock_summary(yid for _p, yid, _n in result)
        self._material_stock_summary = stock
        self._material_yarn_names = {int(yid): name for _p, yid, name in result if yid is not None}

        parts = []
        for ply, yid, name in result:
            label = html.escape(f"{ply}: {name}" if ply else name)
            if yid is not None:
                parts.append(
                    f'<a href="yarn:{int(yid)}" style="color:#202020; text-decoration:none;">{label}</a>'
                    f'&nbsp;{_yarn_locations.stock_symbol_html(int(yid), stock.get(int(yid)))}')
            else:
                parts.append(label)
        return " • ".join(parts)

    def _on_material_label_link_hovered(self, href: str) -> None:
        """Garn oder Spulen-Symbol in der Materialzeile: Bestand als Tooltip
        (Klick öffnet die Lagerplätze)."""
        href = href or ""
        if href.startswith(("yarn:", "stock:", "nostock:")):
            try:
                yid = int(href.split(":", 1)[1])
            except Exception:
                return
            summary = getattr(self, "_material_stock_summary", {}).get(yid)
            QToolTip.showText(QCursor.pos(), _yarn_locations.stock_symbol_tooltip(summary),
                              self.lbl_material_value)
        else:
            QToolTip.hideText()

    def _on_material_label_link_activated(self, href: str) -> None:
        """Klick auf ein Garn oder auf dessen grünes Spulen-Symbol in der
        Materialzeile: zeigt, wo die Spulen dieses Garns am Lager liegen
        (inkl. Hülsenfarbe). Garn ohne Bestand: Dialog sagt, dass nichts da ist."""
        if not href.startswith(("yarn:", "stock:")):
            return
        try:
            yarn_id = int(href.split(":", 1)[1])
        except Exception:
            return
        try:
            from ui.widgets.yarn_colour import load_yarn_colours
            colour = load_yarn_colours()[0].get(yarn_id)
        except Exception:
            colour = None
        name = getattr(self, "_material_yarn_names", {}).get(yarn_id) or f"Yarn {yarn_id}"
        win = self.window()
        goto = getattr(win, "_go_yarn_stock_from_notification", None)
        try:
            dlg = _yarn_locations.YarnLocationsDialog(
                yarn_id, name, colour,
                _yarn_locations.load_series_spool_ids(getattr(self, "_series_pk", None)),
                parent=self, on_open_yarn_stock=goto)
        except Exception as e:
            show_error(self, "Stock locations", "The stock locations could not be loaded.", e)
            return
        try:
            from db.usage_log import log_usage_event
            log_usage_event("feature", "yarn_stock_locations",
                            "show_experiment_" + href.split(":", 1)[0])
        except Exception:
            pass
        dlg.exec()

    # ---------- Machine Data ----------

    def _build_machine_tab(self):
        _machine_tab_mod.build_machine_tab_impl(self)

    def _on_view_mode_changed(self):
        """Radio-Button Wechsel → nur bei Groups-Wechsel neu aufbauen, sonst nur filtern."""
        prev = getattr(self, "_last_view_mode", None)
        if self._rb_groups.isChecked():
            cur = "groups"
        elif self._rb_compact.isChecked():
            cur = "compact"
        else:
            cur = "single"

        needs_rebuild = (
                prev != cur and (
                prev == "groups" or cur == "groups"
                or prev == "compact" or cur == "compact"
        )
        )
        self._last_view_mode = cur

        if needs_rebuild:
            self._build_machine_tab()
        else:
            # Header-Zeile 1 (Ply-Labels) neu berechnen für Kompakt ↔ Single
            col_specs = getattr(self, "_machine_col_specs", None)
            model = getattr(self, "model_machine", None)
            if col_specs and model and len(model._header_rows) > 1:
                compact_mode = (cur == "compact")
                trial_cs_for_hdr: Dict[int, List[Dict]] = {}
                for cs in col_specs:
                    trial_cs_for_hdr.setdefault(cs["trial_id"], []).append(cs)

                from ui.machine_tab import ply_header_colour
                new_ply_vals = [""]
                new_tooltips = [""]
                new_colours = [""]
                for cs in col_specs:
                    new_colours.append(ply_header_colour(cs, trial_cs_for_hdr, compact_mode))
                    if compact_mode:
                        all_cs = trial_cs_for_hdr.get(cs["trial_id"], [cs])
                        new_ply_vals.append("Ply 1" if len(all_cs) == 1 else "div.")
                        tooltip_lines = []
                        for other_cs in all_cs:
                            ply_lbl = other_cs.get("ply") or ""
                            yname = other_cs.get("yarn_name") or ""
                            if ply_lbl or yname:
                                tooltip_lines.append(f"{ply_lbl}: {yname}" if yname else ply_lbl)
                        new_tooltips.append("\n".join(tooltip_lines) if tooltip_lines else "")
                    else:
                        new_ply_vals.append(cs["ply"])
                        new_tooltips.append(cs.get("yarn_name") or "")

                model._header_rows[1]["values"] = new_ply_vals
                model._header_rows[1]["tooltips"] = new_tooltips
                model._header_rows[1]["colours"] = new_colours
                model.layoutChanged.emit()

            self._apply_mat_column_filter()

    def _apply_mat_column_filter(self):
        """Blendet Spalten in tbl_machine gemäss Modus und Zeige-Checkboxen aus."""
        col_specs = getattr(self, "_machine_col_specs", None)
        if not col_specs:
            return

        compact = self._rb_compact.isChecked()
        groups = self._rb_groups.isChecked()

        # Welche Labels sollen sichtbar sein?
        checked_labels: Optional[set] = None
        checks = getattr(self, "_mat_filter_checks", [])
        if checks:
            checked_labels = {cb.text() for cb in checks if cb.isChecked()}

        right_view = self.tbl_machine.right
        # rule: db/machine_data.hidden_columns (shared with the web app)
        hidden_cols = _machine_data.hidden_columns(col_specs, compact, groups, checked_labels)
        for c_idx, hidden in enumerate(hidden_cols):
            right_view.setColumnHidden(c_idx + 1, hidden)

        self.tbl_machine.resizeColumnsToContents(fixed_data_column_width=90)

        # Checkboxen im Kompakt-Modus deaktivieren

    def _build_rd_machine_tab(
            self,
            *,
            fields_rd: List[Dict],
            machine_id: Any,
            col_specs: List[Dict],
            settings_cols_map: Dict[str, str],
            trial_rows: List[Dict],
    ) -> None:
        _machine_tab_mod.build_rd_machine_tab_impl(
            self,
            fields_rd=fields_rd,
            machine_id=machine_id,
            col_specs=col_specs,
            settings_cols_map=settings_cols_map,
            trial_rows=trial_rows,
        )

    def _fill_machine_row_from_title(self, row: int, is_rd: bool = False):
        _machine_tab_mod.fill_machine_row_from_title_impl(self, row, is_rd=is_rd)

    # ---------- Titer (nur sichtbar wenn Daten) ----------

    def _on_machine_header_context(self, pos):
        """Right-click on the (hidden) real column header in the Machine tab
        - opens the copy dialog with the clicked trial preselected. The
        active path is the trial-number row, see _on_trial_header_menu()."""
        if not self.model_machine or not self._trial_ids:
            return
        col = self.tbl_machine.horizontalHeader().logicalIndexAt(pos)
        col_specs = getattr(self, "_machine_col_specs", None) or []
        if 1 <= col <= len(col_specs):
            self._open_copy_trials_dialog([col_specs[col - 1]["trial_id"]])

    def _toggle_custom_group_row(self) -> None:
        """Schaltet die Custom-Group-Zeile im Machine-Tab ein/aus und speichert den Zustand."""
        self._custom_group_visible = not self._custom_group_visible
        # Zeile im View ein-/ausblenden (zusammen mit den vom Nutzer
        # ausgeblendeten Zeilen, damit die Streifen stimmen)
        if self.model_machine:
            from ui import machine_row_visibility as _mrv
            _mrv.apply(self)

    def _manage_plies_for_col_spec_idx(self, col_spec_idx: int) -> None:
        """Right-click on the ply row of Machine Data: the yarns dialog of the
        whole series, scrolled to the clicked trial."""
        col_specs = getattr(self, "_machine_col_specs", None)
        trial_id = None
        if col_specs and 0 <= col_spec_idx < len(col_specs):
            trial_id = col_specs[col_spec_idx].get("trial_id")
        self._open_series_yarns(focus_trial_id=trial_id)

    def _open_series_yarns(self, focus_trial_id=None) -> None:
        """Yarns of the whole series (ui/series_yarns_dialog.py): change the
        yarn of a ply, switch plies on/off per trial, ends, add plies."""
        if not getattr(self, "_series_pk", None):
            return
        editable = self._get_access_level() >= 2
        if editable and not self._confirm_proceed_despite_unsaved():
            return
        from ui.series_yarns_dialog import SeriesYarnsDialog
        label = " – ".join(x for x in (str(getattr(self, "_experiment_id_txt", "") or ""),
                                        str(getattr(self, "_series_name_txt", "") or "")) if x)
        try:
            dlg = SeriesYarnsDialog(self, self._series_pk, label, editable=editable,
                                    focus_trial_id=focus_trial_id)
        except Exception as e:
            show_error(self, "Yarns", "The yarns of this series could not be loaded.", e)
            return
        if dlg.exec() == QDialog.Accepted:
            self._after_plies_changed()

    def _after_plies_changed(self) -> None:
        """Rebuild what shows plies/yarns after they were changed in the DB."""
        if hasattr(self, "_machine_cache") and self._machine_cache:
            try:
                ph = ",".join(["%s"] * len(self._trial_ids))
                use_rows = fetch_all(
                    f"SELECT COUNT(*) AS cnt FROM tblTrialSettings "
                    f"WHERE TrialID IN ({ph}) AND YarnUseID IS NOT NULL",
                    self._trial_ids,
                )
                self._machine_cache["has_groups"] = (use_rows[0]["cnt"] > 0) if use_rows else False
            except Exception:
                pass
        self._build_machine_tab()
        if hasattr(self, "_build_rd_machine_tab"):
            try:
                self._build_rd_machine_tab()
            except Exception:
                pass
        txt = self._load_materials_summary()
        if hasattr(self, "lbl_material_value"):
            self.lbl_material_value.setText(txt or "—")

    def _multiply_trial_from_col_spec_idx(self, col_spec_idx: int) -> None:
        """"Copy trials..." from the trial-number row (row 0 of the Machine
        table) - opens the copy dialog with that trial preselected.
        col_spec_idx = index into _machine_col_specs (= model column - 1)."""
        col_specs = getattr(self, "_machine_col_specs", None) or []
        if 0 <= col_spec_idx < len(col_specs):
            self._open_copy_trials_dialog([col_specs[col_spec_idx]["trial_id"]])

    def _on_copy_trials_button(self) -> None:
        """"Copy trials" button: trials whose columns are selected in the
        Machine table are preselected (none selected -> nothing preselected)."""
        preselected = []
        col_specs = getattr(self, "_machine_col_specs", None) or []
        try:
            sel = self.tbl_machine.right.selectionModel()
            cols = sorted({ix.column() for ix in sel.selectedIndexes()}) if sel else []
            for c in cols:
                if 1 <= c <= len(col_specs):
                    tid = col_specs[c - 1]["trial_id"]
                    if tid not in preselected:
                        preselected.append(tid)
        except Exception:
            preselected = []
        self._open_copy_trials_dialog(preselected)

    def _open_copy_trials_dialog(self, preselected_trial_ids) -> None:
        """Opens the copy dialog (ui/copy_trials_dialog.py) and runs the copy.
        Reference samples are never offered (they're not trials)."""
        from ui.copy_trials_dialog import CopyTrialsDialog, build_copy_fields, load_source_values
        if self._series_pk is None or not self._trial_ids:
            return
        if self._get_access_level() <= 1:
            return
        trials = [
            {"id": int(tid), "vno": vno}
            for tid, vno in zip(self._trial_ids, self._trial_vnos)
            if int(tid) not in self._reference_names
        ]
        if not trials:
            QMessageBox.information(self, "Copy trials", "There are no trials to copy in this series.")
            return
        if not getattr(self, "_machine_cache", None):
            self._init_machine_cache()
        cache = self._machine_cache or {}
        fields = build_copy_fields(
            cache.get("machine_fields") or [],
            cache.get("trial_cols_map") or _db_get_columns_map("tblTrial"),
            cache.get("lookup_maps") or {},
            getattr(self, "_jets_list", []),
            getattr(self, "_housing_list", []),
            bool(cache.get("has_groups")),
        )
        source = load_source_values([t["id"] for t in trials], fields)
        next_no = _trial_actions.next_trial_number_of_series(self._series_pk)
        real_ids = {t["id"] for t in trials}
        dlg = CopyTrialsDialog(self, trials, fields, source, next_no,
                               [int(t) for t in (preselected_trial_ids or []) if int(t) in real_ids])
        if dlg.exec() != QDialog.Accepted:
            return
        plan = dlg.get_plan()
        if plan:
            self._copy_trials_with_plan(plan, fields)

    def _insert_trial_copy(self, cur, src_trial_id: int, series_id: Any, new_versuchsnummer: int) -> int:
        """One new tblTrial row as a copy of src_trial_id (machine params 1:1,
        lab rows structurally cloned but nulled, ply settings cloned):
        db/trial_actions.insert_trial_copy. Returns the new trial's ID."""
        return _trial_actions.insert_trial_copy(cur, src_trial_id, series_id, new_versuchsnummer,
                                                self._current_user_id())

    def _reload_after_trial_copy(self) -> None:
        """Reloads/rebuilds every tab that can show newly-inserted trials -
        shared by both trial-copy flows below."""
        self._load_trials()
        self._build_machine_tab()
        self._build_lab_tabs()

    # ── Reference samples (customer originals, see db/trial_reference.py) ──

    def _on_trial_header_menu(self, col_spec_idx: int, global_pos, is_rd: bool = False) -> None:
        """Right-click on a trial number (row 0 of the Machine / R&D Machine
        table): copy trials + reference-sample actions."""
        col_specs = getattr(self, "_rd_machine_col_specs" if is_rd else "_machine_col_specs", None)
        if not col_specs or not (0 <= col_spec_idx < len(col_specs)):
            return
        trial_id = int(col_specs[col_spec_idx]["trial_id"])
        vno = col_specs[col_spec_idx].get("vno", "?")
        is_ref = trial_id in self._reference_names

        menu = QMenu(self)
        act_copy = None if is_ref else menu.addAction("Copy trials…")
        act_note = _cell_notes_ui.add_trial_note_action(self, menu, trial_id)
        act_playground = None
        if not is_ref and self._process_playground_available():
            act_playground = menu.addAction(f"Open V{vno} in Process Playground…")
            act_playground.setToolTip("What happens to the lab values if you change air pressure, overfeed "
                                      "or speed - starting from this trial")
            menu.setToolTipsVisible(True)
        menu.addSeparator()
        act_add = menu.addAction("Add reference sample…")
        act_mark = act_rename = act_unmark = None
        act_compare = None
        if is_ref:
            act_compare = menu.addAction("Compare trials with this reference…")
            act_rename = menu.addAction("Rename reference sample…")
            act_unmark = menu.addAction("Turn into a normal trial")
        else:
            act_mark = menu.addAction(f"Mark V{vno} as reference sample…")
        ref_actions = [a for a in (act_add, act_mark, act_rename, act_unmark) if a is not None]
        if not has_reference_columns() or self._get_access_level() <= 1:
            for a in ref_actions:
                a.setEnabled(False)
        menu.addSeparator()
        del_ids = self._trials_to_delete(trial_id, is_rd)
        act_delete = menu.addAction(
            f"Delete {format_number_list(self._vnos_of(del_ids)) or 'trial'}…" if len(del_ids) == 1
            else f"Delete {len(del_ids)} selected trials ({format_number_list(self._vnos_of(del_ids))})…")
        why = self._trial_delete_blocker()
        if why:
            act_delete.setEnabled(False)
            act_delete.setToolTip(why)
            menu.setToolTipsVisible(True)

        chosen = menu.exec(global_pos)
        if chosen is None:
            return
        if chosen is act_copy:
            self._multiply_trial_from_col_spec_idx(col_spec_idx)
        elif act_note is not None and chosen is act_note:
            _cell_notes_ui.open_trial_notes(self, trial_id)
        elif chosen is act_add:
            self._add_reference_sample()
        elif chosen is act_mark:
            self._set_reference_flag(trial_id, vno, True)
        elif chosen is act_rename:
            self._rename_reference_sample(trial_id, vno)
        elif chosen is act_unmark:
            self._set_reference_flag(trial_id, vno, False)
        elif chosen is act_delete:
            self._delete_trials(del_ids)
        elif act_compare is not None and chosen is act_compare:
            self._open_ref_compare(trial_id)
        elif act_playground is not None and chosen is act_playground:
            app_meta.open_process_playground(trial_id=trial_id)

    def _process_playground_available(self) -> bool:
        """Right-click "Open in Process Playground…": DTY series only, the
        tool allowed for this user, not offline (ui/screen_process_playground.py)."""
        if not callable(getattr(app_meta, "open_process_playground", None)):
            return False
        try:
            from db.connection import is_offline_mode
            from db.feature_access import can_use
            from ui import dty_schema_panel as _dsp
            return _dsp._profile(self) == "dty" and not is_offline_mode() and can_use("process_playground")
        except Exception:
            return False

    def _open_ref_compare(self, ref_id: Optional[int] = None) -> None:
        from ui.ref_compare_dialog import open_ref_compare
        open_ref_compare(self, ref_id)

    def _show_trial_in_machine_data(self, trial_id: int) -> None:
        """Selects the first column of a trial in Machine Data (double-click
        in Compare with Ref)."""
        specs = getattr(self, "_machine_col_specs", None) or []
        col = next((i for i, cs in enumerate(specs) if int(cs["trial_id"]) == int(trial_id)), None)
        if col is None or self.tab_machine is None:
            return
        self.tabs.setCurrentWidget(self.tab_machine)
        view = self.tbl_machine.right
        model = view.model()
        if model is None:
            return
        idx = model.index(int(getattr(model, "_n_hdr", 0) or 0), col + 1)
        view.setCurrentIndex(idx)
        view.scrollTo(idx)
        self.window().raise_()
        self.window().activateWindow()

    # ── Delete trials (recycle bin, numbers stay used - db/recycle_bin.py) ──

    def _trials_to_delete(self, clicked_trial_id: int, is_rd: bool = False) -> List[int]:
        """The clicked trial - or, if it is part of a selection over several
        trials in the same table, all selected trials (in column order)."""
        specs = getattr(self, "_rd_machine_col_specs" if is_rd else "_machine_col_specs", None) or []
        tbl = getattr(self, "tbl_rd_machine" if is_rd else "tbl_machine", None)
        selected: List[int] = []
        try:
            sel = tbl.right.selectionModel() if tbl is not None else None
            for c in sorted({ix.column() for ix in sel.selectedIndexes()}) if sel else []:
                if 1 <= c <= len(specs):
                    tid = int(specs[c - 1]["trial_id"])
                    if tid not in selected:
                        selected.append(tid)
        except Exception:
            selected = []
        if int(clicked_trial_id) in selected and len(selected) > 1:
            return selected
        return [int(clicked_trial_id)]

    def _vnos_of(self, trial_ids) -> List[Any]:
        by_id = {int(t): v for t, v in zip(self._trial_ids, self._trial_vnos)}
        return [by_id.get(int(t)) for t in trial_ids]

    def _trial_delete_blocker(self) -> str:
        """'' if the current user may delete trials here, else the reason."""
        from db import recycle_bin
        if self._series_pk is None or self._get_access_level() <= 1:
            return "Read only"
        if not recycle_bin.available():
            return "Deleting trials needs the recycle bin (not available offline)."
        if not recycle_bin.can_delete_trials_now(self._series_pk):
            return ("Only who may move this series in the Backlog can delete its trials "
                    "(in To Be Cleaned: superusers only).")
        return ""

    # what else a trial delete takes along: db/recycle_bin.table_label()

    def _delete_trials(self, trial_ids: List[int]) -> None:
        """Deletes trials with everything attached into the recycle bin. The
        other trials keep their numbers - nothing moves up, gaps are never
        filled (Nutzerwunsch 2026-11-11)."""
        from db import recycle_bin
        why = self._trial_delete_blocker()
        if why or not trial_ids:
            if why:
                QMessageBox.information(self, "Delete trials", why)
            return
        if not self._confirm_proceed_despite_unsaved():
            return
        names = format_number_list(self._vnos_of(trial_ids))
        try:
            counts = recycle_bin.preview_trials(int(self._series_pk), trial_ids)
        except recycle_bin.RecycleBinError as e:
            QMessageBox.warning(self, "Delete trials", str(e))
            return
        except Exception as e:
            show_error(self, "Delete trials", "The trials could not be checked.", e, warning=True)
            return
        n = len(trial_ids)
        parts = []
        for table, cnt in counts:
            key = table.lower()
            if key == "tbltrial":
                continue
            label = recycle_bin.table_label(table)
            parts.append(f"{label}: {cnt}")
        left = [v for t, v in zip(self._trial_ids, self._trial_vnos) if int(t) not in set(trial_ids)]
        msg = QMessageBox(self)
        msg.setWindowTitle("Delete trials")
        msg.setIcon(QMessageBox.Warning)
        msg.setText(
            f"<b>Delete {names} ({n} trial{'s' if n != 1 else ''})?</b><br><br>"
            "Also deleted: " + (", ".join(parts) if parts else "nothing else") + "<br><br>"
            "The other trials keep their numbers - nothing moves up. "
            "New trials are always added after the highest remaining number.<br>"
            + ("<b>This removes all trials of the series.</b><br>" if not left else "")
            + f"A superuser can restore them from the <b>Recycle Bin</b> for {recycle_bin.RETENTION_DAYS} days.")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        msg.setDefaultButton(QMessageBox.Cancel)
        msg.button(QMessageBox.Yes).setText("Delete")
        if msg.exec() != QMessageBox.Yes:
            return
        label = f"{self._series_display_label()} {names}".strip()
        try:
            recycle_bin.delete_trials(int(self._series_pk), trial_ids, label)
        except recycle_bin.RecycleBinError as e:
            QMessageBox.warning(self, "Delete trials", str(e))
            return
        except Exception as e:
            show_error(self, "Delete trials", "The trials could not be deleted - nothing was changed.", e)
            return
        self._reload_after_trial_copy()

    def _series_display_label(self) -> str:
        """'2026-73-052.01' style label of the open series for the recycle bin."""
        try:
            rows = fetch_all(
                "SELECT e.ExperimentID AS exp, s.SeriesName AS sn FROM tblTrialSeries s "
                "LEFT JOIN tblExperimente e ON e.ID = s.ExperimentID WHERE s.ID = ?", [self._series_pk])
        except Exception:
            rows = []
        if not rows:
            return ""
        exp = str(rows[0].get("exp") or "").strip()
        sn = str(rows[0].get("sn") or "").strip()
        no = sn.split(" ", 1)[0] if sn[:2].isdigit() else ""
        return f"{exp}.{no}" if exp and no else (exp or sn)

    def _ask_reference_name(self, title: str, current: str = "") -> Optional[str]:
        """Returns the entered name ("" allowed) or None on cancel."""
        text, ok = QInputDialog.getText(
            self, title,
            "Name of the reference sample (e.g. customer, article, lot):",
            QLineEdit.Normal, current,
        )
        return text.strip() if ok else None

    def _add_reference_sample(self) -> None:
        """Adds a new reference sample (flagged tblTrial row) to the series.
        Gets the next negative number (-1, -2, ...) instead of a trial
        number, and the same lab row structure as the first real trial
        (values empty) so all lab tabs are directly editable."""
        if self._series_pk is None:
            return
        if not has_reference_columns():
            QMessageBox.information(self, "Reference sample",
                                    "Reference samples are not available in this database yet.")
            return
        if self._get_access_level() <= 1:
            return
        if not self._confirm_proceed_despite_unsaved():
            return
        name = self._ask_reference_name("Add reference sample")
        if name is None:
            return

        # INSERT + lab row structure: db/trial_actions.add_reference_sample (shared with the web app)
        template_id = next(
            (t for t in self._trial_ids if int(t) not in self._reference_names), None)
        try:
            _trial_actions.add_reference_sample(self._series_pk, name, app_meta.current_user,
                                                template_trial_id=template_id)
        except Exception as e:
            show_error(self, "Reference sample", "The reference sample could not be added.", e, warning=True)
            return

        try:
            from db.usage_log import log_usage_event
            log_usage_event("feature", "reference_sample", "add")
        except Exception:
            pass
        self._reload_after_trial_copy()

    def _set_reference_flag(self, trial_id: int, vno: Any, make_reference: bool) -> None:
        """Turns an existing trial into a reference sample or back."""
        if self._get_access_level() <= 1 or not has_reference_columns():
            return
        if not self._confirm_proceed_despite_unsaved():
            return
        # Marking keeps the trial's (positive) number - the physical spool
        # label carries it. Turning a negative-numbered reference back into
        # a trial gives it the next free trial number.
        new_vno = None
        if make_reference:
            name = self._ask_reference_name(f"Mark V{vno} as reference sample")
            if name is None:
                return
        else:
            ans = QMessageBox.question(
                self, "Reference sample",
                "Turn this reference sample into a normal trial?\n\n"
                "It will then count as a trial again (statistics, reports, exports).",
            )
            if ans != QMessageBox.Yes:
                return
            name = None
            new_vno = _trial_actions.unmark_number(self._series_pk, vno)
        try:
            _trial_actions.write_reference_flag(trial_id, make_reference, name, new_vno)
        except Exception as e:
            show_error(self, "Reference sample", "The reference sample could not be saved.", e, warning=True)
            return
        try:
            from db.usage_log import log_usage_event
            log_usage_event("feature", "reference_sample", "mark" if make_reference else "unmark")
        except Exception:
            pass
        self._reload_after_trial_copy()

    def _rename_reference_sample(self, trial_id: int, vno: Any) -> None:
        if self._get_access_level() <= 1 or not has_reference_columns():
            return
        name = self._ask_reference_name(
            "Rename reference sample", self._reference_names.get(int(trial_id), ""))
        if name is None:
            return
        try:
            _trial_actions.rename_reference_sample(trial_id, name)
        except Exception as e:
            show_error(self, "Reference sample", "The reference sample could not be saved.", e, warning=True)
            return
        self._reference_names[int(trial_id)] = name
        # Only tooltips change - re-apply them to all built models.
        for attr, model in self._iter_save_models():
            if attr in ("model_machine", "model_rd_machine"):
                specs = getattr(self, "_rd_machine_col_specs" if attr == "model_rd_machine"
                                else "_machine_col_specs", None) or []
                self._apply_reference_columns(model, [cs["trial_id"] for cs in specs])
            elif getattr(model, "_col_titles", None) is self._trial_labels:
                self._apply_reference_columns(model, self._trial_ids)

    def _build_lab_tabs(self) -> None:
        """(Re)builds every per-trial lab tab, in tab order. Shared by
        load_record() and _reload_after_trial_copy() so both always cover
        the same set - the copy reload used to keep its own shorter list and
        silently skipped Statimat DS, EKB and the three shrinkage tabs, so a
        freshly copied trial didn't show up there until the series was
        reopened."""
        self._build_titer_tab()
        self._build_jet_air_tab()
        self._build_statimat_tab()
        self._build_statimat_ds_tab()
        self._build_waterbath_tab()
        self._build_ekb_tab()
        self._build_hot_air_shrinkage_tab()
        self._build_hot_water_shrinkage_tab()
        self._build_aty_shrinkage_tab()
        self._build_rapid600_tab()
        self._build_itemat_tab()
        self._build_itemat_plus_tab()
        self._build_dtyomat_tab()
        self._build_atyomat_tab()

    def _copy_trials_with_plan(self, plan, fields) -> None:
        """Creates one copy per plan entry [(source_trial_id, {field.key:
        value})], appended after the series' highest trial number, then
        applies the values changed in the copy dialog to the new trial
        (tblTrial columns, or on ATY the OF of all Core/Effect plies).

        Guards against silently discarding unsaved edits: the reload below
        rebuilds every tab from the DB, which would wipe pending cell edits.
        """
        if not plan or self._series_pk is None:
            return
        if not self._confirm_proceed_despite_unsaved():
            return
        # the copies themselves: db/trial_actions.copy_trials (Qt-free, shared with the web app)
        new_ids, err = _trial_actions.copy_trials(self._series_pk, plan, fields, app_meta.current_user)
        if err is not None:
            show_error(self, "Error copying trials", "The trials could not be copied.", err, warning=True)
            if not new_ids:
                return

        try:
            from db.usage_log import log_usage_event
            n_changed = sum(1 for _src, ov in plan if ov)
            log_usage_event("feature", "copy_trials", f"{len(new_ids)} copies, {n_changed} with changed values")
        except Exception:
            pass

        self._reload_after_trial_copy()
        self._show_new_trial_columns(new_ids)

    def _show_new_trial_columns(self, new_ids) -> None:
        """After copying: switch to Machine Data, select the new trials'
        columns and scroll there (instead of a message box to click away)."""
        try:
            if self.tab_machine is not None:
                self.tabs.setCurrentWidget(self.tab_machine)
            col_specs = getattr(self, "_machine_col_specs", None) or []
            new = {int(t) for t in new_ids}
            cols = [i + 1 for i, cs in enumerate(col_specs) if int(cs["trial_id"]) in new]
            if not cols:
                return
            view = self.tbl_machine.right
            model = view.model()
            sel = view.selectionModel()
            from PySide6.QtCore import QItemSelection, QItemSelectionModel
            selection = QItemSelection()
            last_row = model.rowCount() - 1
            for c in cols:
                selection.select(model.index(0, c), model.index(last_row, c))
            sel.select(selection, QItemSelectionModel.ClearAndSelect)
            view.scrollTo(model.index(0, cols[-1]))
            view.scrollTo(model.index(0, cols[0]))
            QToolTip.showText(
                view.mapToGlobal(view.rect().center()),
                f"{len(new_ids)} new trial(s) created - highlighted in the table.",
                view, view.rect(), 4000,
            )
        except Exception:
            pass

    def _on_print_trial_labels(self) -> None:
        """Druckt Labels mit der Versuchsnummer (z.B. 'V23') fuer die Trials
        der aktuellen Series. Eigenes Template ('TrialLabel'), unabhaengig
        vom Spulen-Label-Template im Garnlager (andere Bogengroesse)."""
        series_pk = getattr(self, "_series_pk", None)
        if not series_pk:
            QMessageBox.information(self, "Print Labels", "No series loaded.")
            return
        # range, header, cell renderer: db/trial_labels.py (Qt-free, shared with the web app)
        from db import trial_labels
        if not table_exists("tbltrial"):
            return
        rng = trial_labels.trial_label_range(series_pk)
        if rng is None:
            QMessageBox.information(self, "Print Labels", "No trials in this series.")
            return
        mn, mx = rng

        # "ExperimentID.SS" (erste 2 Zeichen des Series-Namens) fuer die
        # Kopfzeile ueber der Versuchsnummer - gilt fuer die ganze Series.
        header_txt = trial_labels.trial_label_header(series_pk)

        template = load_label_template(trial_labels.TEMPLATE_NAME)

        range_widget = QWidget()
        range_layout = QHBoxLayout(range_widget)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.addWidget(QLabel("From trial:"))
        spn_from = QSpinBox()
        spn_from.setRange(mn, mx)
        spn_from.setValue(mn)
        range_layout.addWidget(spn_from)
        range_layout.addWidget(QLabel("To trial:"))
        spn_to = QSpinBox()
        spn_to.setRange(mn, mx)
        spn_to.setValue(mx)
        range_layout.addWidget(spn_to)
        range_layout.addStretch(1)

        dlg = PrintLabelsDialog(
            "TrialLabel", template, mx - mn + 1, extra_widget=range_widget, parent=self)

        def _update_count():
            f, t = spn_from.value(), spn_to.value()
            if t < f:
                t = f
                spn_to.blockSignals(True)
                spn_to.setValue(f)
                spn_to.blockSignals(False)
            dlg.set_item_count(t - f + 1)

        spn_from.valueChanged.connect(_update_count)
        spn_to.valueChanged.connect(_update_count)

        if dlg.exec() != QDialog.Accepted:
            return
        tpl = dlg.template_values()
        start_index = dlg.start_index()
        f, t = spn_from.value(), spn_to.value()
        items = trial_labels.trial_label_items(header_txt, f, t)

        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save label PDF", "trial_labels.pdf", "PDF Files (*.pdf)")
        if not out_path:
            return
        try:
            generate_label_sheet_pdf(items, tpl, start_index, out_path, draw_cell=_draw_trial_label_cell)
        except Exception as e:
            show_error(self, "Print Labels", "The PDF could not be created.", e)
            return
        QMessageBox.information(self, "Print Labels", f"Saved to:\n{out_path}")

    def _add_empty_trial(self) -> None:
        """Navigiert zu CreateExperimentScreen im addtrials-Modus."""
        if self._series_pk is None or self._exp_pk is None:
            return
        if callable(getattr(self, "on_add_trials", None)):
            self.on_add_trials(self._exp_pk, self._series_pk, getattr(self, "_experiment_id_txt", ""))
        else:
            QMessageBox.information(self, "Info", "Navigation is not configured.")

    def _clone_lab_rows_for_trial(self, cur, src_trial_id: int, new_trial_id: int) -> None:
        """Lab rows of src_trial_id cloned onto new_trial_id (parameters such
        as Tension kept, measured values NULL): db/trial_actions."""
        _trial_actions.clone_lab_rows_for_trial(cur, src_trial_id, new_trial_id, self._current_user_id())

    def _clone_trial_settings_rows(self, cur, src_trial_id: int, new_trial_id: int) -> None:
        """tblTrialSettings rows of src_trial_id cloned 1:1 onto new_trial_id
        (measured tensions + comments empty): db/trial_actions."""
        _trial_actions.clone_trial_settings_rows(cur, src_trial_id, new_trial_id)

    def _get_jet_info_rows(self) -> list:
        """3 Zeilen (label, [wert_pro_trial]) für Jet / Jet Plate / Air Pressure
        (db/series_tables.jet_info_rows). Cached per load_record() call
        (invalidated in _load_trials()) - up to 13 lab tab builders call this
        for the same trial list (profiled: ~21% of a 255-trial open before caching)."""
        cached = getattr(self, "_jet_info_rows_cache", None)
        if cached is not None:
            return cached
        result = _series_tables.jet_info_rows(getattr(self, "_trial_ids", []) or [])
        self._jet_info_rows_cache = result
        return result

    def _ensure_titer_tab(self):
        _titer_qss = """
            QTableView { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView::item:selected { background: #b7d6ff; color: black; }
        """.replace("#B5D7B5", accent_gridline()).replace("#E9F6E9", accent_tint())
        if self.tab_titer is not None:
            # Tab existiert schon – nur StyleSheet aktualisieren
            self.tbl_titer.setStyleSheet(_titer_qss)
            return
        self.tab_titer = QWidget()
        vt = QVBoxLayout(self.tab_titer)
        vt.setContentsMargins(24, 12, 24, 24)
        self.lbl_titer_retest_banner = self._make_retest_banner()
        vt.addWidget(self.lbl_titer_retest_banner)
        self.tbl_titer = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_titer)
        self._enable_paste_for_table(self.tbl_titer)
        self.tbl_titer.verticalHeader().setVisible(False)
        self.tbl_titer.setStyleSheet(_titer_qss)
        self.tbl_titer.horizontalHeader().setMinimumSectionSize(90)
        self.tbl_titer.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl_titer.horizontalHeader().customContextMenuRequested.connect(
            lambda pos, tw=self.tbl_titer, ls="Titer": self._on_lab_header_context_menu(tw, pos, ls))
        vt.addWidget(self.tbl_titer)
        self.tabs.addTab(self.tab_titer, "Titer")

    def _remove_titer_tab_if_exists(self):
        if self.tab_titer is None:
            return
        idx = self.tabs.indexOf(self.tab_titer)
        if idx != -1:
            self.tabs.removeTab(idx)
        self.tab_titer.deleteLater()
        self.tab_titer = None
        self.tbl_titer = None
        self.model_titer = None
        self.lbl_titer_retest_banner = None

    def _build_titer_tab(self):
        # data: db/series_tables.py (shared with the web app)
        p = _series_tables.build_titer(self._series_trials_data())
        if p is None:
            self._remove_titer_tab_if_exists()
            return
        self._ensure_titer_tab()

        def _populate():
            self.model_titer = self._model_from_pivot(p)
            self.tbl_titer.setModel(self.model_titer)
            self.model_titer.insert_readonly_rows_at_top(self._get_jet_info_rows())
            self._register_save_model("model_titer")
            self.tbl_titer.resizeColumnsToContents(fixed_data_column_width=90)
            self._apply_lab_retest_flags(
                self.model_titer, self.tab_titer, "Titer", self.lbl_titer_retest_banner)

            # ── Soll-Titer: Abweichung > 5 % rot, Tenacity in Statimat DS orange ──
            self._titer_out_of_tolerance = set(p.extra.get("out_of_tolerance", set()))
            for (r, c), style in p.alerts.items():
                self.model_titer.set_cell_alert(len(self._get_jet_info_rows()) + r, c, style)
            if p.extra.get("has_target"):
                self._apply_titer_alert_to_stat_ds()

        self._defer_or_populate("titer", self.tab_titer, _populate)

    def _apply_titer_alert_to_stat_ds(self):
        """Markiert die Tenacity-Zeile in Statimat DS orange für Trials mit Titer-Abweichung."""
        try:
            oot = getattr(self, "_titer_out_of_tolerance", set())
            if not oot:
                return
            model = getattr(self, "model_stat_ds", None)
            if model is None:
                return
            # Tenacity ist Zeile 5 (0-basiert, nach 3 Jet-Info-Zeilen:
            # Jet=0, Jet Plate=1, Air Pressure=2, Elong=3, ElongCV=4, Ten=5, TenCV=6)
            n_jet_rows = len(self._get_jet_info_rows())
            ten_row = n_jet_rows + 2  # Ten ist der 3. Datenwert (0-basiert: +2)
            for c_idx in oot:
                model.set_cell_alert(ten_row, c_idx, "orange")
            model.dataChanged.emit(
                model.createIndex(0, 0),
                model.createIndex(model.rowCount() - 1, model.columnCount() - 1),
            )
        except Exception:
            pass

    # ---------- Jet Air Consumption (nur sichtbar wenn Daten) ----------
    # Anders als die uebrigen Reiter: Zeilen sind KEINE Parameter, sondern
    # physische Duesen (JetID + JetPlate); Spalten sind Druckstufen statt
    # Trials. Basiert auf tblLaborJetAirConsumption.TrialSeriesID (nicht
    # TrialID) - komplett unabhaengig von der Trial-Anzahl der Series.

    def _ensure_jet_air_tab(self):
        _qss = """
            QTableView { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView::item:selected { background: #b7d6ff; color: black; }
        """.replace("#B5D7B5", accent_gridline()).replace("#E9F6E9", accent_tint())
        if self.tab_jet_air is not None:
            self.tbl_jet_air.setStyleSheet(_qss)
            self.tbl_jet_air_atm.setStyleSheet(_qss)
            self.tbl_jet_air_temp.setStyleSheet(_qss)
            return

        self.tab_jet_air = QWidget()
        outer = QVBoxLayout(self.tab_jet_air)
        outer.setContentsMargins(24, 12, 24, 24)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        vj = QVBoxLayout(inner)
        vj.setContentsMargins(0, 0, 0, 0)
        vj.setSpacing(18)
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        # ── Air Consumption + Einheiten-Umschalter ─────────────────────
        hdr1 = QHBoxLayout()
        hdr1.addWidget(QLabel("<b>Air Consumption</b>"))
        hdr1.addStretch(1)
        btn_sync_jets = QPushButton("Sync physical jets")
        btn_sync_jets.setToolTip(
            "Matches this table with the jets/plates currently set in the trials (e.g. after the jet "
            "or plate of a trial was changed later).")
        btn_sync_jets.clicked.connect(self._sync_jet_air_physical_jets)
        hdr1.addWidget(btn_sync_jets)
        hdr1.addWidget(QLabel("Einheit:"))
        self.cmb_jet_air_unit = QComboBox()
        self.cmb_jet_air_unit.addItem("Nm³/h", "Nm3h")
        self.cmb_jet_air_unit.addItem("l/min", "lmin")
        self.cmb_jet_air_unit.setCurrentIndex(0 if self._jet_air_unit == "Nm3h" else 1)
        self.cmb_jet_air_unit.currentIndexChanged.connect(self._on_jet_air_unit_changed)
        hdr1.addWidget(self.cmb_jet_air_unit)
        vj.addLayout(hdr1)

        self.tbl_jet_air = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_jet_air)
        self._enable_paste_for_table(self.tbl_jet_air)
        self.tbl_jet_air.verticalHeader().setVisible(False)
        self.tbl_jet_air.setStyleSheet(_qss)
        self.tbl_jet_air.horizontalHeader().setMinimumSectionSize(90)
        self.tbl_jet_air.setSelectionBehavior(QTableView.SelectItems)
        self.tbl_jet_air.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed)
        self.tbl_jet_air.setMinimumHeight(160)
        vj.addWidget(self.tbl_jet_air)

        # ── Atmospheric Pressure ────────────────────────────────────────
        hdr2 = QHBoxLayout()
        hdr2.addWidget(QLabel("<b>Atmospheric Pressure (mbar)</b>"))
        hdr2.addStretch(1)
        self.txt_jet_air_atm_fill = QLineEdit()
        self.txt_jet_air_atm_fill.setPlaceholderText("Value for all cells")
        self.txt_jet_air_atm_fill.setFixedWidth(140)
        self.txt_jet_air_atm_fill.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"^\s*[+-]?\d+(?:[.,]\d+)?\s*$"), self))
        btn_atm_fill = QPushButton("Apply to all")
        btn_atm_fill.clicked.connect(lambda: self._fill_all_jet_air("model_jet_air_atm", self.txt_jet_air_atm_fill))
        hdr2.addWidget(self.txt_jet_air_atm_fill)
        hdr2.addWidget(btn_atm_fill)
        vj.addLayout(hdr2)

        self.tbl_jet_air_atm = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_jet_air_atm)
        self._enable_paste_for_table(self.tbl_jet_air_atm)
        self.tbl_jet_air_atm.verticalHeader().setVisible(False)
        self.tbl_jet_air_atm.setStyleSheet(_qss)
        self.tbl_jet_air_atm.horizontalHeader().setMinimumSectionSize(90)
        self.tbl_jet_air_atm.setSelectionBehavior(QTableView.SelectItems)
        self.tbl_jet_air_atm.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed)
        self.tbl_jet_air_atm.setMinimumHeight(160)
        vj.addWidget(self.tbl_jet_air_atm)

        # ── Air Temperature ─────────────────────────────────────────────
        hdr3 = QHBoxLayout()
        hdr3.addWidget(QLabel("<b>Air Temperature (°C)</b>"))
        hdr3.addStretch(1)
        self.txt_jet_air_temp_fill = QLineEdit()
        self.txt_jet_air_temp_fill.setPlaceholderText("Value for all cells")
        self.txt_jet_air_temp_fill.setFixedWidth(140)
        self.txt_jet_air_temp_fill.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"^\s*[+-]?\d+(?:[.,]\d+)?\s*$"), self))
        btn_temp_fill = QPushButton("Apply to all")
        btn_temp_fill.clicked.connect(lambda: self._fill_all_jet_air("model_jet_air_temp", self.txt_jet_air_temp_fill))
        hdr3.addWidget(self.txt_jet_air_temp_fill)
        hdr3.addWidget(btn_temp_fill)
        vj.addLayout(hdr3)

        self.tbl_jet_air_temp = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_jet_air_temp)
        self._enable_paste_for_table(self.tbl_jet_air_temp)
        self.tbl_jet_air_temp.verticalHeader().setVisible(False)
        self.tbl_jet_air_temp.setStyleSheet(_qss)
        self.tbl_jet_air_temp.horizontalHeader().setMinimumSectionSize(90)
        self.tbl_jet_air_temp.setSelectionBehavior(QTableView.SelectItems)
        self.tbl_jet_air_temp.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed)
        self.tbl_jet_air_temp.setMinimumHeight(160)
        vj.addWidget(self.tbl_jet_air_temp)

        self.tabs.addTab(self.tab_jet_air, "Jet Air Consumption")

    def _on_jet_air_unit_changed(self, _idx: int):
        """Einheit gewechselt -> Reiter mit neu umgerechneten Werten neu aufbauen.
        Ungespeicherte Änderungen gehen dabei verloren (Hinweis an den User)."""
        new_unit = self.cmb_jet_air_unit.currentData()
        if new_unit == self._jet_air_unit:
            return
        if self.model_jet_air is not None and getattr(self.model_jet_air, "_dirty", None):
            resp = QMessageBox.question(
                self, "Einheit wechseln",
                "There are unsaved changes in the air consumption table.\n"
                "They will be lost when switching the unit. Continue?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if resp != QMessageBox.Yes:
                self.cmb_jet_air_unit.blockSignals(True)
                self.cmb_jet_air_unit.setCurrentIndex(0 if self._jet_air_unit == "Nm3h" else 1)
                self.cmb_jet_air_unit.blockSignals(False)
                return
        self._jet_air_unit = new_unit
        self._build_jet_air_tab()

    def _fill_all_jet_air(self, model_attr: str, txt: QLineEdit) -> None:
        """Schreibt den eingegebenen Wert in alle Zellen des angegebenen Grids
        (markiert sie als dirty - gespeichert wird ueber den normalen Save)."""
        model = getattr(self, model_attr, None)
        if model is None:
            return
        raw = txt.text().strip()
        if raw == "":
            return
        n_rows = model.rowCount() - model._n_hdr
        n_cols = model.columnCount() - 1
        for r in range(n_rows):
            for c in range(n_cols):
                if model.get_binding(r, c) is None:
                    continue
                idx = model.index(r + model._n_hdr, c + 1)
                model.setData(idx, raw, Qt.EditRole)

    def _remove_jet_air_tab_if_exists(self):
        if self.tab_jet_air is None:
            return
        idx = self.tabs.indexOf(self.tab_jet_air)
        if idx != -1:
            self.tabs.removeTab(idx)
        self.tab_jet_air.deleteLater()
        self.tab_jet_air = None
        self.tbl_jet_air = None
        self.model_jet_air = None
        self.tbl_jet_air_atm = None
        self.model_jet_air_atm = None
        self.tbl_jet_air_temp = None
        self.model_jet_air_temp = None
        self.cmb_jet_air_unit = None

    def _build_jet_air_tab(self):
        """Reiter 'Jet Air Consumption': Zeilen = physische Duesen
        (JetID + JetPlate), Spalten = Druckstufen. Drei Grids: Air
        Consumption (mit Einheiten-Umschalter Nm3/h <-> l/min - gespeichert
        wird immer in Nm3/h), Atmospheric Pressure und Air Temperature
        (beide mit "Fuer alle uebernehmen"). Data: db/series_tables.build_jet_air
        (shared with the web app)."""
        ja = _series_tables.build_jet_air(getattr(self, "_series_pk", None), self._jet_air_unit)
        if ja is None:
            self._remove_jet_air_tab_if_exists()
            return

        self._ensure_jet_air_tab()

        def _populate():
            # ── Air Consumption ──────────────────────────────────────────────
            self.model_jet_air = self._model_from_pivot(ja.consumption)
            self.tbl_jet_air.setModel(self.model_jet_air)
            self._register_save_model("model_jet_air")
            self.tbl_jet_air.resizeColumnsToContents(fixed_data_column_width=90)

            # ── Atmospheric Pressure ────────────────────────────────────────
            self.model_jet_air_atm = self._model_from_pivot(ja.atm)
            self.tbl_jet_air_atm.setModel(self.model_jet_air_atm)
            self._register_save_model("model_jet_air_atm")
            self.tbl_jet_air_atm.resizeColumnsToContents(fixed_data_column_width=90)

            # ── Air Temperature ─────────────────────────────────────────────
            self.model_jet_air_temp = self._model_from_pivot(ja.temp)
            self.tbl_jet_air_temp.setModel(self.model_jet_air_temp)
            self._register_save_model("model_jet_air_temp")
            self.tbl_jet_air_temp.resizeColumnsToContents(fixed_data_column_width=90)

        self._defer_or_populate("jet_air", self.tab_jet_air, _populate)

    def _get_current_physical_jets_for_series(self, series_id: int) -> List[Tuple[int, Optional[str]]]:
        """Jets/plates currently set in the trials: db/jet_air_sync.current_physical_jets (shared with the web app)."""
        from db import jet_air_sync
        return jet_air_sync.current_physical_jets(series_id)

    def _sync_jet_air_physical_jets(self):
        """"Sync physical jets": plan + write in db/jet_air_sync.py (Qt-free, shared with the
        web app); here only the questions and messages."""
        from db import jet_air_sync
        series_id = getattr(self, "_series_pk", None)
        plan = jet_air_sync.plan_sync(series_id)
        if plan["status"] == "unavailable":
            return
        if plan["status"] == "nothing_found":
            QMessageBox.information(
                self, "Sync physical jets",
                "No jets/pressure levels found - sync not possible.")
            return
        if plan["status"] == "in_sync":
            QMessageBox.information(
                self, "Sync physical jets",
                "Already in sync - no changes needed.")
            return
        resp = QMessageBox.question(
            self, "Sync physical jets",
            "\n".join(plan["lines"]) + "\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if resp != QMessageBox.Yes:
            return
        try:
            jet_air_sync.apply_sync(series_id, plan, self._current_user_id())
        except Exception as e:
            QMessageBox.critical(self, "DB Error", str(e))
            return

        self._build_jet_air_tab()
        QMessageBox.information(self, "Sync physical jets", "Synchronisierung abgeschlossen.")

    # ---------- Statimat M (nur sichtbar wenn Daten) ----------

    def _ensure_stat_tab(self):
        if self.tab_stat is not None:
            return
        self.tab_stat = QWidget()
        vs = QVBoxLayout(self.tab_stat)
        vs.setContentsMargins(24, 12, 24, 24)
        self.lbl_stat_retest_banner = self._make_retest_banner()
        vs.addWidget(self.lbl_stat_retest_banner)
        self.tbl_stat = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_stat)
        self._enable_paste_for_table(self.tbl_stat)
        self.tbl_stat.verticalHeader().setVisible(False)
        self.tbl_stat.horizontalHeader().setMinimumSectionSize(90)
        self.tbl_stat.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl_stat.horizontalHeader().customContextMenuRequested.connect(
            lambda pos, tw=self.tbl_stat, ls="Statimat": self._on_lab_header_context_menu(tw, pos, ls))
        self.tbl_stat.setSelectionBehavior(QTableView.SelectItems)
        self.tbl_stat.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed)
        self.tbl_stat.setStyleSheet("""
            QTableView { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView::item:selected { background: #b7d6ff; color: black; }
        """
                                    .replace("#B5D7B5", accent_gridline())
                                    .replace("#E9F6E9", accent_tint()))
        vs.addWidget(self.tbl_stat)
        self.tabs.addTab(self.tab_stat, "Statimat M")

    def _remove_stat_tab_if_exists(self):
        if self.tab_stat is None:
            return
        idx = self.tabs.indexOf(self.tab_stat)
        if idx != -1:
            self.tabs.removeTab(idx)
        self.tab_stat.deleteLater()
        self.tab_stat = None
        self.tbl_stat = None
        self.model_stat = None
        self.lbl_stat_retest_banner = None

    def _build_statimat_tab(self):
        # data: db/series_tables.py (shared with the web app)
        p = _series_tables.build_stat(self._series_trials_data())
        if p is None:
            self._remove_stat_tab_if_exists()
            return
        self._ensure_stat_tab()

        def _populate():
            self.model_stat = self._model_from_pivot(p)
            self.tbl_stat.setModel(self.model_stat)
            self.model_stat.insert_readonly_rows_at_top(self._get_jet_info_rows())
            self._register_save_model("model_stat")
            self.tbl_stat.resizeColumnsToContents(fixed_data_column_width=90)
            self._apply_lab_retest_flags(
                self.model_stat, self.tab_stat, "Statimat", self.lbl_stat_retest_banner)

        self._defer_or_populate("stat", self.tab_stat, _populate)

    # ---------- Statimat DS (nur sichtbar wenn Daten) ----------

    def _ensure_stat_ds_tab(self):
        if self.tab_stat_ds is not None:
            return
        self.tab_stat_ds = QWidget()
        vs = QVBoxLayout(self.tab_stat_ds)
        vs.setContentsMargins(24, 12, 24, 24)
        self.lbl_stat_ds_retest_banner = self._make_retest_banner()
        vs.addWidget(self.lbl_stat_ds_retest_banner)
        self.tbl_stat_ds = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_stat_ds)
        self._enable_paste_for_table(self.tbl_stat_ds)
        self.tbl_stat_ds.verticalHeader().setVisible(False)
        self.tbl_stat_ds.horizontalHeader().setMinimumSectionSize(90)
        self.tbl_stat_ds.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl_stat_ds.horizontalHeader().customContextMenuRequested.connect(
            lambda pos, tw=self.tbl_stat_ds, ls="StatimatDS": self._on_lab_header_context_menu(tw, pos, ls))
        self.tbl_stat_ds.setSelectionBehavior(QTableView.SelectItems)
        self.tbl_stat_ds.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed)
        self.tbl_stat_ds.setStyleSheet("""
            QTableView { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView::item:selected { background: #b7d6ff; color: black; }
        """
                                       .replace("#B5D7B5", accent_gridline())
                                       .replace("#E9F6E9", accent_tint()))
        vs.addWidget(self.tbl_stat_ds)
        self.tabs.addTab(self.tab_stat_ds, "Statimat DS")

    def _remove_stat_ds_tab_if_exists(self):
        if self.tab_stat_ds is None:
            return
        idx = self.tabs.indexOf(self.tab_stat_ds)
        if idx != -1:
            self.tabs.removeTab(idx)
        self.tab_stat_ds.deleteLater()
        self.tab_stat_ds = None
        self.tbl_stat_ds = None
        self.model_stat_ds = None
        self.lbl_stat_ds_retest_banner = None

    def _build_statimat_ds_tab(self):
        # data: db/series_tables.py (shared with the web app)
        p = _series_tables.build_stat_ds(self._series_trials_data())
        if p is None:
            self._remove_stat_ds_tab_if_exists()
            return
        self._ensure_stat_ds_tab()

        def _populate():
            self.model_stat_ds = self._model_from_pivot(p)
            self.tbl_stat_ds.setModel(self.model_stat_ds)
            self.model_stat_ds.insert_readonly_rows_at_top(self._get_jet_info_rows())
            self._register_save_model("model_stat_ds")
            self.tbl_stat_ds.resizeColumnsToContents(fixed_data_column_width=90)
            self._apply_lab_retest_flags(
                self.model_stat_ds, self.tab_stat_ds, "StatimatDS", self.lbl_stat_ds_retest_banner)

            # Orange-Alerts für Tenacity falls Titer-Abweichungen bereits bekannt
            self._apply_titer_alert_to_stat_ds()

        self._defer_or_populate("stat_ds", self.tab_stat_ds, _populate)

    # ---------- EKB (sichtbar nur bei Daten) ----------

    def _ensure_ekb_tab(self):
        if self.tab_ekb is not None:
            return
        self.tab_ekb = QWidget()
        vl = QVBoxLayout(self.tab_ekb)
        vl.setContentsMargins(24, 12, 24, 24)
        self.lbl_ekb_retest_banner = self._make_retest_banner()
        vl.addWidget(self.lbl_ekb_retest_banner)
        self.tbl_ekb = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_ekb)
        self._enable_paste_for_table(self.tbl_ekb)
        self.tbl_ekb.verticalHeader().setVisible(False)
        self.tbl_ekb.horizontalHeader().setMinimumSectionSize(110)
        self.tbl_ekb.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl_ekb.horizontalHeader().customContextMenuRequested.connect(
            lambda pos, tw=self.tbl_ekb, ls="EKB": self._on_lab_header_context_menu(tw, pos, ls))
        self.tbl_ekb.setSelectionBehavior(QTableView.SelectItems)
        self.tbl_ekb.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed)
        self.tbl_ekb.setStyleSheet("""
            QTableView { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView::item:selected { background: #b7d6ff; color: black; }
        """
                                   .replace("#B5D7B5", accent_gridline())
                                   .replace("#E9F6E9", accent_tint()))
        vl.addWidget(self.tbl_ekb)
        self.tabs.addTab(self.tab_ekb, "EKB")

    def _remove_ekb_tab_if_exists(self):
        if self.tab_ekb is None:
            return
        idx = self.tabs.indexOf(self.tab_ekb)
        if idx != -1:
            self.tabs.removeTab(idx)
        self.tab_ekb.deleteLater()
        self.tab_ekb = None
        self.tbl_ekb = None
        self.model_ekb = None
        self.lbl_ekb_retest_banner = None

    def _build_ekb_tab(self):
        # data: db/series_tables.py (shared with the web app)
        p = _series_tables.build_ekb(self._series_trials_data())
        if p is None:
            self._remove_ekb_tab_if_exists()
            return
        self._ensure_ekb_tab()

        def _populate():
            self.model_ekb = self._model_from_pivot(p)
            if self.tbl_ekb is not None:
                self.tbl_ekb.setModel(self.model_ekb)
                self.model_ekb.insert_readonly_rows_at_top(self._get_jet_info_rows())
                self._register_save_model("model_ekb")
                self.tbl_ekb.resizeColumnsToContents(fixed_data_column_width=110)
                self._apply_lab_retest_flags(
                    self.model_ekb, self.tab_ekb, "EKB", self.lbl_ekb_retest_banner)

        self._defer_or_populate("ekb", self.tab_ekb, _populate)

    # ---------- Hot Air Shrinkage (sichtbar nur bei Daten) ----------

    def _ensure_hot_air_shrinkage_tab(self):
        if self.tab_hot_air_shrinkage is not None:
            return
        self.tab_hot_air_shrinkage = QWidget()
        vl = QVBoxLayout(self.tab_hot_air_shrinkage)
        vl.setContentsMargins(24, 12, 24, 24)
        self.lbl_hot_air_shrinkage_retest_banner = self._make_retest_banner()
        vl.addWidget(self.lbl_hot_air_shrinkage_retest_banner)
        self.tbl_hot_air_shrinkage = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_hot_air_shrinkage)
        self._enable_paste_for_table(self.tbl_hot_air_shrinkage)
        self.tbl_hot_air_shrinkage.verticalHeader().setVisible(False)
        self.tbl_hot_air_shrinkage.horizontalHeader().setMinimumSectionSize(110)
        self.tbl_hot_air_shrinkage.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl_hot_air_shrinkage.horizontalHeader().customContextMenuRequested.connect(
            lambda pos, tw=self.tbl_hot_air_shrinkage, ls="HotAirShrinkage":
            self._on_lab_header_context_menu(tw, pos, ls))
        self.tbl_hot_air_shrinkage.setSelectionBehavior(QTableView.SelectItems)
        self.tbl_hot_air_shrinkage.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed)
        self.tbl_hot_air_shrinkage.setStyleSheet("""
            QTableView { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView::item:selected { background: #b7d6ff; color: black; }
        """
                                                 .replace("#B5D7B5", accent_gridline())
                                                 .replace("#E9F6E9", accent_tint()))
        vl.addWidget(self.tbl_hot_air_shrinkage)
        self.tabs.addTab(self.tab_hot_air_shrinkage, "Hot Air Shrinkage")

    def _remove_hot_air_shrinkage_tab_if_exists(self):
        if self.tab_hot_air_shrinkage is None:
            return
        idx = self.tabs.indexOf(self.tab_hot_air_shrinkage)
        if idx != -1:
            self.tabs.removeTab(idx)
        self.tab_hot_air_shrinkage.deleteLater()
        self.tab_hot_air_shrinkage = None
        self.tbl_hot_air_shrinkage = None
        self.model_hot_air_shrinkage = None
        self.lbl_hot_air_shrinkage_retest_banner = None

    def _build_hot_air_shrinkage_tab(self):
        # data: db/series_tables.py (shared with the web app)
        p = _series_tables.build_hot_air_shrinkage(self._series_trials_data())
        if p is None:
            self._remove_hot_air_shrinkage_tab_if_exists()
            return
        self._ensure_hot_air_shrinkage_tab()

        def _populate():
            self.model_hot_air_shrinkage = self._model_from_pivot(p)
            if self.tbl_hot_air_shrinkage is not None:
                self.tbl_hot_air_shrinkage.setModel(self.model_hot_air_shrinkage)
                self.model_hot_air_shrinkage.insert_readonly_rows_at_top(self._get_jet_info_rows())
                self._register_save_model("model_hot_air_shrinkage")
                self.tbl_hot_air_shrinkage.resizeColumnsToContents(fixed_data_column_width=110)
                self._apply_lab_retest_flags(
                    self.model_hot_air_shrinkage, self.tab_hot_air_shrinkage, "HotAirShrinkage", self.lbl_hot_air_shrinkage_retest_banner)

        self._defer_or_populate("hot_air_shrinkage", self.tab_hot_air_shrinkage, _populate)

    # ---------- Hot Water Shrinkage (sichtbar nur bei Daten) ----------

    def _ensure_hot_water_shrinkage_tab(self):
        if self.tab_hot_water_shrinkage is not None:
            return
        self.tab_hot_water_shrinkage = QWidget()
        vl = QVBoxLayout(self.tab_hot_water_shrinkage)
        vl.setContentsMargins(24, 12, 24, 24)
        self.lbl_hot_water_shrinkage_retest_banner = self._make_retest_banner()
        vl.addWidget(self.lbl_hot_water_shrinkage_retest_banner)
        self.tbl_hot_water_shrinkage = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_hot_water_shrinkage)
        self._enable_paste_for_table(self.tbl_hot_water_shrinkage)
        self.tbl_hot_water_shrinkage.verticalHeader().setVisible(False)
        self.tbl_hot_water_shrinkage.horizontalHeader().setMinimumSectionSize(110)
        self.tbl_hot_water_shrinkage.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl_hot_water_shrinkage.horizontalHeader().customContextMenuRequested.connect(
            lambda pos, tw=self.tbl_hot_water_shrinkage, ls="HotWaterShrinkage":
            self._on_lab_header_context_menu(tw, pos, ls))
        self.tbl_hot_water_shrinkage.setSelectionBehavior(
            QTableView.SelectItems)
        self.tbl_hot_water_shrinkage.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.EditKeyPressed
            | QAbstractItemView.AnyKeyPressed
        )
        self.tbl_hot_water_shrinkage.setStyleSheet("""
            QTableView { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView::item:selected { background: #b7d6ff; color: black; }
        """
                                                   .replace("#B5D7B5", accent_gridline())
                                                   .replace("#E9F6E9", accent_tint()))
        vl.addWidget(self.tbl_hot_water_shrinkage)
        self.tabs.addTab(self.tab_hot_water_shrinkage, "Hot Water Shrinkage")

    def _remove_hot_water_shrinkage_tab_if_exists(self):
        if self.tab_hot_water_shrinkage is None:
            return
        idx = self.tabs.indexOf(self.tab_hot_water_shrinkage)
        if idx != -1:
            self.tabs.removeTab(idx)
        self.tab_hot_water_shrinkage.deleteLater()
        self.tab_hot_water_shrinkage = None
        self.tbl_hot_water_shrinkage = None
        self.model_hot_water_shrinkage = None
        self.lbl_hot_water_shrinkage_retest_banner = None

    def _build_hot_water_shrinkage_tab(self):
        # data: db/series_tables.py (shared with the web app)
        p = _series_tables.build_hot_water_shrinkage(self._series_trials_data())
        if p is None:
            self._remove_hot_water_shrinkage_tab_if_exists()
            return
        self._ensure_hot_water_shrinkage_tab()

        def _populate():
            self.model_hot_water_shrinkage = self._model_from_pivot(p)
            if self.tbl_hot_water_shrinkage is not None:
                self.tbl_hot_water_shrinkage.setModel(self.model_hot_water_shrinkage)
                self.model_hot_water_shrinkage.insert_readonly_rows_at_top(self._get_jet_info_rows())
                self._register_save_model("model_hot_water_shrinkage")
                self.tbl_hot_water_shrinkage.resizeColumnsToContents(fixed_data_column_width=110)
                self._apply_lab_retest_flags(
                    self.model_hot_water_shrinkage, self.tab_hot_water_shrinkage, "HotWaterShrinkage", self.lbl_hot_water_shrinkage_retest_banner)

        self._defer_or_populate("hot_water_shrinkage", self.tab_hot_water_shrinkage, _populate)

    # ---------- ATY Shrinkage (sichtbar nur bei Daten) ----------

    def _ensure_aty_shrinkage_tab(self):
        if self.tab_aty_shrinkage is not None:
            return
        self.tab_aty_shrinkage = QWidget()
        vl = QVBoxLayout(self.tab_aty_shrinkage)
        vl.setContentsMargins(24, 12, 24, 24)
        self.lbl_aty_shrinkage_retest_banner = self._make_retest_banner()
        vl.addWidget(self.lbl_aty_shrinkage_retest_banner)
        self.tbl_aty_shrinkage = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_aty_shrinkage)
        self._enable_paste_for_table(self.tbl_aty_shrinkage)
        self.tbl_aty_shrinkage.verticalHeader().setVisible(False)
        self.tbl_aty_shrinkage.horizontalHeader().setMinimumSectionSize(110)
        self.tbl_aty_shrinkage.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl_aty_shrinkage.horizontalHeader().customContextMenuRequested.connect(
            lambda pos, tw=self.tbl_aty_shrinkage, ls="ATYShrinkage":
            self._on_lab_header_context_menu(tw, pos, ls))
        self.tbl_aty_shrinkage.setSelectionBehavior(QTableView.SelectItems)
        self.tbl_aty_shrinkage.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed)
        self.tbl_aty_shrinkage.setStyleSheet("""
            QTableView { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView::item:selected { background: #b7d6ff; color: black; }
        """
                                             .replace("#B5D7B5", accent_gridline())
                                             .replace("#E9F6E9", accent_tint()))
        vl.addWidget(self.tbl_aty_shrinkage)
        self.tabs.addTab(self.tab_aty_shrinkage, "ATY Shrinkage")

    def _remove_aty_shrinkage_tab_if_exists(self):
        if self.tab_aty_shrinkage is None:
            return
        idx = self.tabs.indexOf(self.tab_aty_shrinkage)
        if idx != -1:
            self.tabs.removeTab(idx)
        self.tab_aty_shrinkage.deleteLater()
        self.tab_aty_shrinkage = None
        self.tbl_aty_shrinkage = None
        self.model_aty_shrinkage = None
        self.lbl_aty_shrinkage_retest_banner = None

    def _build_aty_shrinkage_tab(self):
        # data: db/series_tables.py (shared with the web app)
        p = _series_tables.build_aty_shrinkage(self._series_trials_data())
        if p is None:
            self._remove_aty_shrinkage_tab_if_exists()
            return
        self._ensure_aty_shrinkage_tab()

        def _populate():
            self.model_aty_shrinkage = self._model_from_pivot(p)
            if self.tbl_aty_shrinkage is not None:
                self.tbl_aty_shrinkage.setModel(self.model_aty_shrinkage)
                self.model_aty_shrinkage.insert_readonly_rows_at_top(self._get_jet_info_rows())
                self._register_save_model("model_aty_shrinkage")
                self.tbl_aty_shrinkage.resizeColumnsToContents(fixed_data_column_width=110)
                self._apply_lab_retest_flags(
                    self.model_aty_shrinkage, self.tab_aty_shrinkage, "ATYShrinkage", self.lbl_aty_shrinkage_retest_banner)

        self._defer_or_populate("aty_shrinkage", self.tab_aty_shrinkage, _populate)

    # ---------- Waterbath (fixe Spaltennamen) ----------

    def _ensure_waterbath_tab(self):
        if self.tab_water is not None:
            return
        self.tab_water = QWidget()
        lw = QVBoxLayout(self.tab_water)
        lw.setContentsMargins(24, 12, 24, 24)
        self.lbl_water_retest_banner = self._make_retest_banner()
        lw.addWidget(self.lbl_water_retest_banner)
        self.tbl_water = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_water)
        self._enable_paste_for_table(self.tbl_water)
        self.tbl_water.verticalHeader().setVisible(False)
        self.tbl_water.horizontalHeader().setMinimumSectionSize(90)
        self.tbl_water.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl_water.horizontalHeader().customContextMenuRequested.connect(
            lambda pos, tw=self.tbl_water, ls="Waterbath": self._on_lab_header_context_menu(tw, pos, ls))
        self.tbl_water.setSelectionBehavior(QTableView.SelectItems)
        self.tbl_water.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed)
        self.tbl_water.setStyleSheet("""
            QTableView { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView::item:selected { background: #b7d6ff; color: black; }
        """
                                     .replace("#B5D7B5", accent_gridline())
                                     .replace("#E9F6E9", accent_tint()))
        lw.addWidget(self.tbl_water)
        self.tabs.addTab(self.tab_water, "Waterbath")

    def _remove_waterbath_tab_if_exists(self):
        if self.tab_water is None:
            return
        idx = self.tabs.indexOf(self.tab_water)
        if idx != -1:
            self.tabs.removeTab(idx)
        self.tab_water.deleteLater()
        self.tab_water = None
        self.tbl_water = None
        self.model_water = None
        self.lbl_water_retest_banner = None

    def _build_waterbath_tab(self):
        # data: db/series_tables.py (shared with the web app)
        p = _series_tables.build_water(self._series_trials_data())
        if p is None:
            self._remove_waterbath_tab_if_exists()
            return
        self._ensure_waterbath_tab()

        def _populate():
            self.model_water = self._model_from_pivot(p)
            self.tbl_water.setModel(self.model_water)
            self.model_water.insert_readonly_rows_at_top(self._get_jet_info_rows())
            self._register_save_model("model_water")
            self.tbl_water.resizeColumnsToContents(fixed_data_column_width=90)
            self._apply_lab_retest_flags(
                self.model_water, self.tab_water, "Waterbath", self.lbl_water_retest_banner)

        self._defer_or_populate("water", self.tab_water, _populate)

    # ---------- Itemat Lab (sichtbar nur bei Daten) ----------

    def _make_retest_banner(self) -> QLabel:
        """Creates the (initially hidden) 'retest pending' banner shown above
        a lab pivot table - shared styling factory so every retest-capable
        lab tab looks the same (see _apply_lab_retest_flags)."""
        banner = QLabel()
        banner.setWordWrap(True)
        banner.setStyleSheet(
            "QLabel { background: #FBE4DC; color: #8A2E17; border: 1px solid #D6432E; "
            "border-radius: 6px; padding: 6px 10px; font-weight: 600; }"
        )
        banner.setVisible(False)
        return banner

    def _ensure_itemat_tab(self):
        if self.tab_itemat is not None:
            return
        self.tab_itemat = QWidget()
        vl = QVBoxLayout(self.tab_itemat)
        vl.setContentsMargins(24, 12, 24, 24)
        self.lbl_itemat_retest_banner = self._make_retest_banner()
        vl.addWidget(self.lbl_itemat_retest_banner)
        self.tbl_itemat = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_itemat)
        self._enable_paste_for_table(self.tbl_itemat)
        self.tbl_itemat.verticalHeader().setVisible(False)
        self.tbl_itemat.horizontalHeader().setMinimumSectionSize(110)
        self.tbl_itemat.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl_itemat.horizontalHeader().customContextMenuRequested.connect(
            lambda pos, tw=self.tbl_itemat, ls="ItematLab": self._on_lab_header_context_menu(tw, pos, ls))
        self.tbl_itemat.setSelectionBehavior(QTableView.SelectItems)
        self.tbl_itemat.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed)
        self.tbl_itemat.setStyleSheet("""
            QTableView { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView::item:selected { background: #b7d6ff; color: black; }
        """
                                      .replace("#B5D7B5", accent_gridline())
                                      .replace("#E9F6E9", accent_tint()))
        vl.addWidget(self.tbl_itemat)
        self.tabs.addTab(self.tab_itemat, "Itemat Lab")

    def _remove_itemat_tab_if_exists(self):
        if self.tab_itemat is None:
            return
        idx = self.tabs.indexOf(self.tab_itemat)
        if idx != -1:
            self.tabs.removeTab(idx)
        self.tab_itemat.deleteLater()
        self.tab_itemat = None
        self.tbl_itemat = None
        self.model_itemat = None
        self.lbl_itemat_retest_banner = None
        self._itemat_tensions = []

    # ---------- Retest flag (superuser flags a trial for a repeat measurement) ----------

    def _on_lab_header_context_menu(self, table_widget, pos, lab_source: str):
        """Right-click on a trial column in any lab pivot: flag for retest.

        Generic version - works for every lab tab whose model columns are
        trials 1:1 (col_titles=self._trial_labels), regardless of which
        physical lab device/table it displays."""
        header = table_widget.horizontalHeader()
        section = header.logicalIndexAt(pos)
        if section <= 0:
            return
        col_idx = section - 1
        if col_idx >= len(self._trials):
            return
        trial = self._trials[col_idx]
        trial_label = (self._trial_labels[col_idx]
                        if col_idx < len(self._trial_labels)
                        else f"Trial {trial.get('ID')}")

        is_super = self._get_access_level() >= 4

        menu = QMenu(self)
        act_flag = menu.addAction(f"🏳  Flag {trial_label} for retest…")
        act_flag.setEnabled(is_super)
        if not is_super:
            act_flag.setToolTip("Only superusers may flag a retest.")
        from ui import kb_links
        kb_links.add_action(menu, self, kb_links.table_target(self, table_widget), "lab_header")
        chosen = menu.exec(header.mapToGlobal(pos))
        if chosen == act_flag:
            self._mark_trial_for_retest(trial, trial_label, lab_source)

    def _mark_trial_for_retest(self, trial: Dict[str, Any], trial_label: str, lab_source: str):
        """Creates an open retest flag and pulls the series back into the Backlog (top priority)."""
        if self._get_access_level() < 4:
            QMessageBox.warning(self, "No permission",
                                "Only superusers may flag a retest.")
            return
        if self._series_pk is None:
            return

        note, ok = QInputDialog.getText(
            self, f"Flag {trial_label} for retest",
            f"Note (optional) — {lab_source}:")
        if not ok:
            return

        from db.retest_flags import mark_trial_for_retest, flags_table_ready
        if not flags_table_ready():
            QMessageBox.warning(
                self, "Not available",
                "Retest flags are not set up on this database yet "
                "(table tblTrialRetestFlag is missing).",
            )
            return

        try:
            mark_trial_for_retest(
                trial_id=int(trial["ID"]),
                trial_series_id=int(self._series_pk),
                lab_source=lab_source,
                note=(note or "").strip(),
                user_id=self._current_user_id(),
            )
        except Exception as e:
            show_error(self, "Error", "The retest flag could not be set.", e)
            return

        try:
            from db.usage_log import log_usage_event
            log_usage_event("feature", "retest_flag_set",
                           f"{trial_label}/{lab_source}/series={self._series_pk}")
        except Exception:
            pass

        self._refresh_lab_retest_flags(lab_source)

        QMessageBox.information(
            self, "Retest flagged",
            f"{trial_label} ({lab_source}) has been flagged for a retest.\n"
            f"The trial series was moved back to the Backlog (top priority).",
        )

    def _build_itemat_tab(self):
        # data: db/series_tables.py (shared with the web app)
        p = _series_tables.build_itemat(self._series_trials_data())
        if p is None:
            self._remove_itemat_tab_if_exists()
            return
        self._itemat_tensions = list(p.extra["tensions"])
        self._ensure_itemat_tab()

        def _populate():
            self.model_itemat = self._model_from_pivot(p)
            self.tbl_itemat.setModel(self.model_itemat)
            self.model_itemat.insert_readonly_rows_at_top(self._get_jet_info_rows())
            self._register_save_model("model_itemat")
            self.tbl_itemat.resizeColumnsToContents(fixed_data_column_width=110)
            self._apply_lab_retest_flags(
                self.model_itemat, self.tab_itemat, "ItematLab", self.lbl_itemat_retest_banner)

        self._defer_or_populate("itemat", self.tab_itemat, _populate)

    def _apply_lab_retest_flags(self, model, tab_widget, lab_source: str, banner_label=None):
        """Shows open retest flags for one lab tab: column-header red dot
        (+ tooltip) on the model, a red dot on the tab icon, and - if the
        tab has one - a banner with the flagged trial(s).

        Generic version of the former itemat-only implementation; called
        both right after a flag is set/resolved and at the end of every
        lab tab's _build_XXX_tab (so reloading the series reflects the
        current flag state everywhere, not just on Itemat Lab)."""
        if model is None or tab_widget is None:
            return
        from db.retest_flags import get_open_retest_flags_for_series_and_source

        flags: List[Dict[str, Any]] = []
        if self._series_pk is not None:
            try:
                flags = get_open_retest_flags_for_series_and_source(
                    int(self._series_pk), lab_source)
            except Exception:
                flags = []

        trial_id_to_col = {int(t["ID"]): c for c, t in enumerate(self._trials)}
        col_map: Dict[int, str] = {}
        banner_parts: List[str] = []
        for f in flags:
            try:
                col_idx = trial_id_to_col.get(int(f.get("TrialID")))
            except Exception:
                col_idx = None
            vno = f.get("Versuchsnummer")
            v_label = format_trial_number(vno) if vno not in (None, "") else "?"
            note = (f.get("Note") or "").strip()
            who = f.get("CreatedByUsername") or ""
            tooltip = f"{v_label} — retest pending" + (f": {note}" if note else "")
            if who:
                tooltip += f" (flagged by {who})"
            if col_idx is not None:
                col_map[col_idx] = tooltip
            banner_parts.append(v_label + (f': "{note}"' if note else ""))

        model.set_flagged_columns(col_map)

        if banner_label is not None:
            if banner_parts:
                banner_label.setText(
                    "🏳 Retest pending — " + "; ".join(banner_parts))
                banner_label.setVisible(True)
            else:
                banner_label.setVisible(False)

        idx = self.tabs.indexOf(tab_widget)
        if idx != -1:
            self.tabs.setTabIcon(idx, _retest_flag_dot_icon() if flags else QIcon())

    def _refresh_lab_retest_flags(self, lab_source: str) -> None:
        """Dispatches to the right lab tab's _apply_lab_retest_flags() call
        after a flag was set (see _mark_trial_for_retest). One entry per
        retest-capable lab tab - add a new lab device here + wire its
        _ensure_XXX_tab/_build_XXX_tab like the others to make it flaggable."""
        dispatch = {
            "ItematLab": lambda: self._apply_lab_retest_flags(
                self.model_itemat, self.tab_itemat, "ItematLab", self.lbl_itemat_retest_banner),
            "Titer": lambda: self._apply_lab_retest_flags(
                self.model_titer, self.tab_titer, "Titer", self.lbl_titer_retest_banner),
            "Statimat": lambda: self._apply_lab_retest_flags(
                self.model_stat, self.tab_stat, "Statimat", self.lbl_stat_retest_banner),
            "StatimatDS": lambda: self._apply_lab_retest_flags(
                self.model_stat_ds, self.tab_stat_ds, "StatimatDS", self.lbl_stat_ds_retest_banner),
            "EKB": lambda: self._apply_lab_retest_flags(
                self.model_ekb, self.tab_ekb, "EKB", self.lbl_ekb_retest_banner),
            "HotAirShrinkage": lambda: self._apply_lab_retest_flags(
                self.model_hot_air_shrinkage, self.tab_hot_air_shrinkage, "HotAirShrinkage",
                self.lbl_hot_air_shrinkage_retest_banner),
            "HotWaterShrinkage": lambda: self._apply_lab_retest_flags(
                self.model_hot_water_shrinkage, self.tab_hot_water_shrinkage, "HotWaterShrinkage",
                self.lbl_hot_water_shrinkage_retest_banner),
            "ATYShrinkage": lambda: self._apply_lab_retest_flags(
                self.model_aty_shrinkage, self.tab_aty_shrinkage, "ATYShrinkage",
                self.lbl_aty_shrinkage_retest_banner),
            "Waterbath": lambda: self._apply_lab_retest_flags(
                self.model_water, self.tab_water, "Waterbath", self.lbl_water_retest_banner),
            "ItematPlus": lambda: self._apply_lab_retest_flags(
                self.model_itemat_plus, self.tab_itemat_plus, "ItematPlus",
                self.lbl_itemat_plus_retest_banner),
            "DTYoMat": lambda: self._apply_lab_retest_flags(
                self.model_dtyomat, self.tab_dtyomat, "DTYoMat", self.lbl_dtyomat_retest_banner),
            "ATYoMat": lambda: self._apply_lab_retest_flags(
                self.model_atyomat, self.tab_atyomat, "ATYoMat", self.lbl_atyomat_retest_banner),
            "Rapid600": lambda: self._apply_lab_retest_flags(
                self.model_rapid600, self.tab_rapid600, "Rapid600", self.lbl_rapid600_retest_banner),
        }
        handler = dispatch.get(lab_source)
        if handler:
            handler()

    def _to_float(self, s: Any) -> Optional[float]:
        if s is None:
            return None
        try:
            return float(str(s).replace(",", "."))
        except Exception:
            return None

    def _recompute_itemat_intermingling(self) -> int:
        """
        Für jede Spannung t>0: IP(t) = IP(0) * Stability(t) / 100
        -> Update nur, wenn der neue Wert sich vom aktuellen DB-Wert unterscheidet
        (db/series_save.recompute_itemat_intermingling).
        """
        if not self.model_itemat or not self._itemat_tensions:
            return 0
        # Gleicher Offset wie in _recompute_itemat_plus() (siehe dort) -
        # insert_readonly_rows_at_top(self._get_jet_info_rows()) verschiebt
        # die echten Datenzeilen um die Jet-Info-Kopfzeilen nach unten.
        n_header = len(self._get_jet_info_rows())
        return _series_save.recompute_itemat_intermingling(
            self.model_itemat.get_cell_value, self.model_itemat.get_binding,
            len(self._trial_labels), self._itemat_tensions, row_offset=n_header)

    # ---------- Itemat Plus (sichtbar nur bei Daten) ----------

    def _ensure_itemat_plus_tab(self):
        if self.tab_itemat_plus is not None:
            return
        self.tab_itemat_plus = QWidget()
        vl = QVBoxLayout(self.tab_itemat_plus)
        vl.setContentsMargins(24, 12, 24, 24)
        self.lbl_itemat_plus_retest_banner = self._make_retest_banner()
        vl.addWidget(self.lbl_itemat_plus_retest_banner)
        self.tbl_itemat_plus = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_itemat_plus)
        self._enable_paste_for_table(self.tbl_itemat_plus)
        self.tbl_itemat_plus.verticalHeader().setVisible(False)
        self.tbl_itemat_plus.horizontalHeader().setMinimumSectionSize(120)
        self.tbl_itemat_plus.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl_itemat_plus.horizontalHeader().customContextMenuRequested.connect(
            lambda pos, tw=self.tbl_itemat_plus, ls="ItematPlus":
            self._on_lab_header_context_menu(tw, pos, ls))
        self.tbl_itemat_plus.setSelectionBehavior(QTableView.SelectItems)
        self.tbl_itemat_plus.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed)
        self.tbl_itemat_plus.setStyleSheet("""
            QTableView { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView::item:selected { background: #b7d6ff; color: black; }
        """
                                           .replace("#B5D7B5", accent_gridline())
                                           .replace("#E9F6E9", accent_tint()))
        vl.addWidget(self.tbl_itemat_plus)
        self.tabs.addTab(self.tab_itemat_plus, "Itemat Plus")

    def _remove_itemat_plus_tab_if_exists(self):
        if self.tab_itemat_plus is None:
            return
        idx = self.tabs.indexOf(self.tab_itemat_plus)
        if idx != -1:
            self.tabs.removeTab(idx)
        self.tab_itemat_plus.deleteLater()
        self.tab_itemat_plus = None
        self.tbl_itemat_plus = None
        self.model_itemat_plus = None
        self.lbl_itemat_plus_retest_banner = None
        self._itemat_plus_tensions = []

    def _build_itemat_plus_tab(self):
        # data: db/series_tables.py (shared with the web app)
        p = _series_tables.build_itemat_plus(self._series_trials_data())
        if p is None:
            self._remove_itemat_plus_tab_if_exists()
            return
        self._itemat_plus_tensions = list(p.extra["tensions"])
        self._ensure_itemat_plus_tab()

        def _populate():
            self.model_itemat_plus = self._model_from_pivot(p)
            self.tbl_itemat_plus.setModel(self.model_itemat_plus)
            self.model_itemat_plus.insert_readonly_rows_at_top(self._get_jet_info_rows())
            self._register_save_model("model_itemat_plus")
            self.tbl_itemat_plus.resizeColumnsToContents(fixed_data_column_width=120)
            self._apply_lab_retest_flags(
                self.model_itemat_plus, self.tab_itemat_plus, "ItematPlus",
                self.lbl_itemat_plus_retest_banner)

        self._defer_or_populate("itemat_plus", self.tab_itemat_plus, _populate)

    def _recompute_itemat_plus(self) -> int:
        """
        Zwei Dinge (db/series_save.recompute_itemat_plus):
        1) Für jede Spannung t>0: IP(t) = IP(0) * Stability(t) / 100
           -> schreibe in den Datensatz mit Stability(t) (nur bei echter Änderung).
        2) CV@0: ((KL S)^2 + (OL S)^2)^0.5 / (KL X + OL X)
           -> schreibe in den 0.0-Datensatz in Feld [Intermingling Points CV (%)] (nur bei echter Änderung).
        """
        if not self.model_itemat_plus:
            return 0
        # insert_readonly_rows_at_top(self._get_jet_info_rows()) schiebt beim
        # Populaten des Tabs (siehe _build_itemat_plus_tab) die Jet/Jet Plate/
        # Air Pressure-Kopfzeilen VOR die eigentlichen Datenzeilen - die
        # Row-Konstanten muessen deshalb um diese Kopfzeilen-Anzahl versetzt
        # werden, sonst werden die Jet-Info-Zeilen (Text, kein float) statt
        # OLX/OLS/KLX/KLS gelesen und FPmCV wird nie mehr neu berechnet.
        n_header = len(self._get_jet_info_rows())
        return _series_save.recompute_itemat_plus(
            self.model_itemat_plus.get_cell_value, self.model_itemat_plus.get_binding,
            len(self._trial_labels), self._itemat_plus_tensions, row_offset=n_header)

    # ---------- DTYoMat (sichtbar nur bei vorhandenen Daten) ----------

    def _ensure_dtyomat_tab(self):
        if self.tab_dtyomat is not None:
            return
        self.tab_dtyomat = QWidget()
        vl = QVBoxLayout(self.tab_dtyomat)
        vl.setContentsMargins(24, 12, 24, 24)
        self.lbl_dtyomat_retest_banner = self._make_retest_banner()
        vl.addWidget(self.lbl_dtyomat_retest_banner)

        self.tbl_dtyomat = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_dtyomat)
        self._enable_paste_for_table(self.tbl_dtyomat)
        self.tbl_dtyomat.verticalHeader().setVisible(False)
        self.tbl_dtyomat.horizontalHeader().setMinimumSectionSize(120)
        self.tbl_dtyomat.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl_dtyomat.horizontalHeader().customContextMenuRequested.connect(
            lambda pos, tw=self.tbl_dtyomat, ls="DTYoMat": self._on_lab_header_context_menu(tw, pos, ls))
        self.tbl_dtyomat.setSelectionBehavior(QTableView.SelectItems)
        self.tbl_dtyomat.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed)
        self.tbl_dtyomat.setStyleSheet("""
            QTableView { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView::item:selected { background: #b7d6ff; color: black; }
        """
                                       .replace("#B5D7B5", accent_gridline())
                                       .replace("#E9F6E9", accent_tint()))
        vl.addWidget(self.tbl_dtyomat)

        self.tabs.addTab(self.tab_dtyomat, "DTYoMat")

    def _remove_dtyomat_tab_if_exists(self):
        if self.tab_dtyomat is None:
            return
        idx = self.tabs.indexOf(self.tab_dtyomat)
        if idx != -1:
            self.tabs.removeTab(idx)
        self.tab_dtyomat.deleteLater()
        self.tab_dtyomat = None
        self.tbl_dtyomat = None
        self.model_dtyomat = None
        self.lbl_dtyomat_retest_banner = None

    def _build_dtyomat_tab(self):
        """DTYoMat tab from tblLaborDTYoMat (first record per trial).
        Data: db/series_tables.build_dtyomat (shared with the web app)."""
        p = _series_tables.build_dtyomat(self._series_trials_data())
        if p is None:
            self._remove_dtyomat_tab_if_exists()
            return
        self._ensure_dtyomat_tab()

        def _populate():
            self.model_dtyomat = self._model_from_pivot(p)
            if self.tbl_dtyomat is not None:
                self.tbl_dtyomat.setModel(self.model_dtyomat)
                self.model_dtyomat.insert_readonly_rows_at_top(self._get_jet_info_rows())
                self._register_save_model("model_dtyomat")
                self.tbl_dtyomat.resizeColumnsToContents(fixed_data_column_width=120)
                self._apply_lab_retest_flags(
                    self.model_dtyomat, self.tab_dtyomat, "DTYoMat", self.lbl_dtyomat_retest_banner)

        self._defer_or_populate("dtyomat", self.tab_dtyomat, _populate)

    # ---------- ATYoMat (sichtbar nur bei vorhandenen Daten) ----------

    def _ensure_atyomat_tab(self):
        if self.tab_atyomat is not None:
            return
        self.tab_atyomat = QWidget()
        vl = QVBoxLayout(self.tab_atyomat)
        vl.setContentsMargins(24, 12, 24, 24)
        self.lbl_atyomat_retest_banner = self._make_retest_banner()
        vl.addWidget(self.lbl_atyomat_retest_banner)

        self.tbl_atyomat = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_atyomat)
        self.tbl_atyomat.verticalHeader().setVisible(False)
        self.tbl_atyomat.horizontalHeader().setMinimumSectionSize(120)
        self.tbl_atyomat.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl_atyomat.horizontalHeader().customContextMenuRequested.connect(
            lambda pos, tw=self.tbl_atyomat, ls="ATYoMat": self._on_lab_header_context_menu(tw, pos, ls))
        self.tbl_atyomat.setSelectionBehavior(QTableView.SelectItems)
        self.tbl_atyomat.setEditTriggers(
            QAbstractItemView.DoubleClicked |
            QAbstractItemView.EditKeyPressed |
            QAbstractItemView.AnyKeyPressed
        )
        self.tbl_atyomat.setStyleSheet("""
            QTableView { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView::item:selected { background: #b7d6ff; color: black; }
        """
                                       .replace("#B5D7B5", accent_gridline())
                                       .replace("#E9F6E9", accent_tint()))
        vl.addWidget(self.tbl_atyomat)

        self.tabs.addTab(self.tab_atyomat, "ATYoMat")

    def _remove_atyomat_tab_if_exists(self):
        if self.tab_atyomat is None:
            return
        idx = self.tabs.indexOf(self.tab_atyomat)
        if idx != -1:
            self.tabs.removeTab(idx)
        self.tab_atyomat.deleteLater()
        self.tab_atyomat = None
        self.tbl_atyomat = None
        self.model_atyomat = None
        self.lbl_atyomat_retest_banner = None

    def _build_atyomat_tab(self):
        """ATYoMat tab from tblLaborATYoMat (core/loop figures of the ATY analysis,
        newest record per trial). Data: db/series_tables.build_atyomat (shared with the web app)."""
        p = _series_tables.build_atyomat(self._series_trials_data())
        if p is None:
            self._remove_atyomat_tab_if_exists()
            return
        self._ensure_atyomat_tab()

        def _populate():
            self.model_atyomat = self._model_from_pivot(p)
            if self.tbl_atyomat is not None:
                self.tbl_atyomat.setModel(self.model_atyomat)
                self.model_atyomat.insert_readonly_rows_at_top(self._get_jet_info_rows())
                self._register_save_model("model_atyomat")
                self.tbl_atyomat.resizeColumnsToContents(fixed_data_column_width=120)
                self._apply_lab_retest_flags(
                    self.model_atyomat, self.tab_atyomat, "ATYoMat", self.lbl_atyomat_retest_banner)

        self._defer_or_populate("atyomat", self.tab_atyomat, _populate)

    # ---------- Rapid 600 (sichtbar nur bei vorhandenen Daten) ----------

    def _ensure_rapid600_tab(self):
        if self.tab_rapid600 is not None:
            return
        self.tab_rapid600 = QWidget()
        vl = QVBoxLayout(self.tab_rapid600)
        vl.setContentsMargins(24, 12, 24, 24)
        self.lbl_rapid600_retest_banner = self._make_retest_banner()
        vl.addWidget(self.lbl_rapid600_retest_banner)

        self.tbl_rapid600 = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_rapid600)
        self._enable_paste_for_table(self.tbl_rapid600)
        self.tbl_rapid600.verticalHeader().setVisible(False)
        self.tbl_rapid600.horizontalHeader().setMinimumSectionSize(120)
        self.tbl_rapid600.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl_rapid600.horizontalHeader().customContextMenuRequested.connect(
            lambda pos, tw=self.tbl_rapid600, ls="Rapid600": self._on_lab_header_context_menu(tw, pos, ls))
        self.tbl_rapid600.setSelectionBehavior(QTableView.SelectItems)
        self.tbl_rapid600.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed)
        self.tbl_rapid600.setStyleSheet("""
            QTableView { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView::item:selected { background: #b7d6ff; color: black; }
        """
                                        .replace("#B5D7B5", accent_gridline())
                                        .replace("#E9F6E9", accent_tint()))
        vl.addWidget(self.tbl_rapid600)

        self.tabs.addTab(self.tab_rapid600, "Rapid 600")

    def _remove_rapid600_tab_if_exists(self):
        if self.tab_rapid600 is None:
            return
        idx = self.tabs.indexOf(self.tab_rapid600)
        if idx != -1:
            self.tabs.removeTab(idx)
        self.tab_rapid600.deleteLater()
        self.tab_rapid600 = None
        self.tbl_rapid600 = None
        self.model_rapid600 = None
        self.lbl_rapid600_retest_banner = None

    def _build_rapid600_tab(self):
        # data: db/series_tables.py (shared with the web app)
        p = _series_tables.build_rapid600(self._series_trials_data())
        if p is None:
            self._remove_rapid600_tab_if_exists()
            return
        self._ensure_rapid600_tab()

        def _populate():
            self.model_rapid600 = self._model_from_pivot(p)
            if self.tbl_rapid600 is not None:
                self.tbl_rapid600.setModel(self.model_rapid600)
                self.model_rapid600.insert_readonly_rows_at_top(self._get_jet_info_rows())
                self._register_save_model("model_rapid600")
                self.tbl_rapid600.resizeColumnsToContents(fixed_data_column_width=120)
                self._apply_lab_retest_flags(
                    self.model_rapid600, self.tab_rapid600, "Rapid600", self.lbl_rapid600_retest_banner)

        self._defer_or_populate("rapid600", self.tab_rapid600, _populate)


# ===========================================================================
# YarnScope (DTY) - via eigenem Modul dty_yarnscope_tab.py
# ===========================================================================
# Alle YarnScope-Funktionen sind in ui/dty_yarnscope_tab.py definiert.
# Hier werden sie auf ShowExperimentScreen registriert (siehe unten).


def _patch_show_experiment_yarnscope():
    try:
        cls = ShowExperimentScreen
        cls._build_yarnscope_tab = _dty_mod._build_yarnscope_tab
        cls._remove_yarnscope_tab_if_exists = _dty_mod._remove_yarnscope_tab_if_exists
        cls._create_yarnscope_tab_if_needed = _dty_mod._create_yarnscope_tab_if_needed
        cls._ys_populate_trial_list = _dty_mod._ys_populate_trial_list
        cls._ys_on_trial_selected = _dty_mod._ys_on_trial_selected
        cls._ys_clear_plot = _dty_mod._ys_clear_plot
        cls._ys_on_analyze = _dty_mod._ys_on_analyze
        cls._ys_on_analysis_done = _dty_mod._ys_on_analysis_done
        cls._ys_on_extract_done = _dty_mod._ys_on_extract_done
        cls._ys_update_metrics = _dty_mod._ys_update_metrics
        cls._ys_replot = _dty_mod._ys_replot
        cls._ys_draw_plots = _dty_mod._ys_draw_plots
        cls._ys_draw_garnspiegel = _dty_mod._ys_draw_garnspiegel
        cls._ys_draw_signal = _dty_mod._ys_draw_signal
        cls._ys_on_save = _dty_mod._ys_on_save
        cls._ys_open_batch = _dty_mod._ys_open_batch
        cls._ys_on_refresh = _dty_mod._ys_on_refresh
    except Exception:
        pass


_patch_show_experiment_yarnscope()


# ===========================================================================
# YarnScope ATY – via eigenem Modul aty_yarnscope_tab.py
# ===========================================================================
# Alle ATY-Funktionen sind in ui/aty_yarnscope_tab.py definiert.
# Hier werden sie auf ShowExperimentScreen registriert.
# Attribute-Deklarationen bleiben hier damit __init__ sauber bleibt.

def _patch_show_experiment_aty_yarnscope():
    """Registriert alle ATY-YarnScope-Methoden auf ShowExperimentScreen."""
    cls = ShowExperimentScreen
    cls._build_aty_yarnscope_tab = _aty_mod._build_aty_yarnscope_tab
    cls._remove_aty_yarnscope_tab_if_exists = _aty_mod._remove_aty_yarnscope_tab_if_exists
    cls._create_aty_yarnscope_tab_if_needed = _aty_mod._create_aty_yarnscope_tab_if_needed
    cls._aty_populate_trial_list = _aty_mod._aty_populate_trial_list
    cls._aty_on_trial_selected = _aty_mod._aty_on_trial_selected
    cls._aty_on_analyze = _aty_mod._aty_on_analyze
    cls._aty_refresh_visuals = _aty_mod._aty_refresh_visuals
    cls._aty_get_window = _aty_mod._aty_get_window
    cls._aty_draw_garnspiegel = _aty_mod._aty_draw_garnspiegel
    cls._aty_draw_fabric = _aty_mod._aty_draw_fabric
    cls._aty_update_metrics = _aty_mod._aty_update_metrics
    cls._aty_redraw_histogram = _aty_mod._aty_redraw_histogram
    cls._aty_on_save = _aty_mod._aty_on_save
    cls._aty_open_batch = _aty_mod._aty_open_batch
    cls._aty_on_compare_selection_changed = _aty_mod._aty_on_compare_selection_changed
    cls._aty_on_compare_run = _aty_mod._aty_on_compare_run
    cls._aty_render_compare = _aty_mod._aty_render_compare
    cls._aty_render_radar = _aty_mod._aty_render_radar


_patch_show_experiment_aty_yarnscope()


# ===========================================================================
# agentT – Jet Optimization Advisor (mit Chat-History + Chat-Input)
# ===========================================================================

def _is_advisor_enabled() -> bool:
    """Advisor Tab sichtbar wenn tbluser.api_key_enc gesetzt ist.

    Ergebnis wird pro Session gecacht — kein DB-Call bei jedem load_record().
    """
    cache = _is_advisor_enabled.__dict__
    username = app_meta.current_user.get("username", "")
    if cache.get("_username") == username:
        return cache.get("_result", False)
    try:
        from db.connection import fetch_all
        if not username:
            result = False
        else:
            rows = fetch_all(
                "SELECT api_key_enc FROM tbluser WHERE Username = %s",
                [username]
            )
            result = bool(rows and rows[0].get("api_key_enc"))
    except Exception:
        result = False
    cache["_username"] = username
    cache["_result"] = result
    return result


# _build_advisor_tab, _run_advisor, _send_advisor_question, _save_advisor_report,
# _load_latest_advisor_report, _on_advisor_result/_followup_result/_error/_finished
# und _set_advisor_markdown sind in ui/advisor_tab.py definiert (siehe unten
# _patch_show_experiment_advisor()). _is_advisor_enabled() bleibt hier, da sie
# auch ausserhalb dieses Tabs verwendet wird.


def _patch_show_experiment_advisor():
    cls = ShowExperimentScreen
    cls._build_advisor_tab = _advisor_mod._build_advisor_tab
    cls._run_advisor = _advisor_mod._run_advisor
    cls._send_advisor_question = _advisor_mod._send_advisor_question
    cls._on_advisor_result = _advisor_mod._on_advisor_result
    cls._on_advisor_followup_result = _advisor_mod._on_advisor_followup_result
    cls._reset_advisor = _advisor_mod._reset_advisor
    cls._on_advisor_error = _advisor_mod._on_advisor_error
    cls._on_advisor_finished = _advisor_mod._on_advisor_finished


_patch_show_experiment_advisor()

# Right-click on a value in any Show Experiment table -> "Change history…"
FrozenFirstColumnTable.cell_menu_hook = _show_experiment_cell_menu
