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
from ui.widgets.statimat_pdf_parser import parse_statimat_pdf
from ui.widgets.itemat_pdf_parser import parse_itemat_pdf, DB_TENSIONS as ITEMAT_DB_TENSIONS
from ui.widgets.header import HeaderBar
from ui.yarnscope.garngraf_canvas import GarnCanvas
from ui.widgets.footer import FooterBar
from ui.widgets.frozen_first_column_table import FrozenFirstColumnTable
from ui.widgets.label_printing import (
    MM, fit_text, load_label_template, PrintLabelsDialog, generate_label_sheet_pdf,
)
import ui.aty_yarnscope_tab as _aty_mod
import ui.dty_yarnscope_tab as _dty_mod
import ui.advisor_tab as _advisor_mod
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

import math
import re
import os
import sys
import logging
import tempfile
import uuid
import datetime
import app_meta
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal, QObject, QEvent, QSize, QRect, QRegularExpression
from PySide6.QtGui import QShortcut, QKeySequence, QPainter, QPen, QBrush, QFont, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
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

# Basisordner fuer TrialSeries-Bilder
# - PROD: Netzlaufwerk (gemeinsame Ablage)
# - DEV:  lokaler Testordner
TRIALSERIES_IMAGES_BASE_DIR = (
    r"C:\ttt\images\TrialSeriesImages" if is_dev_mode() else r"H:\\Technik\\TrippleT\\TrialSeriesImages"
)

# Basisordner fuer TrialSeries-PDFs
# - DEV + DEV_LOCAL: lokaler Testordner
# - PROD: Netzlaufwerk (gemeinsame Ablage)
TRIALSERIES_PDFS_BASE_DIR = (
    r"C:\ttt\pdfs" if is_dev_mode() else r"H:\\Technik\\TrippleT\\TrialSeriesPDF"
)


def _draw_trial_label_cell(page, x0: float, y0: float, lw: float, lh: float, item: Dict) -> None:
    """Zeichnet ein Trial-Label: kleine Kopfzeile 'ExperimentID.Serie' oben,
    darunter die Versuchsnummer (z.B. 'V23') gross - beides zentriert.
    Cell-Renderer fuer generate_label_sheet_pdf."""
    import fitz
    fontname = "hebo"
    max_w = lw - 4

    header_txt = str(item.get("Header") or "").strip()
    header_fs = 9.0
    if header_txt:
        while header_fs > 6.0 and fitz.get_text_length(header_txt, fontname=fontname, fontsize=header_fs) > max_w * MM:
            header_fs -= 0.5
        header_txt = fit_text(header_txt, header_fs, max_w, fontname=fontname)

    v_text = f"V{item['TrialNr']}"
    v_fs = 20.0
    while v_fs > 8.0 and fitz.get_text_length(v_text, fontname=fontname, fontsize=v_fs) > max_w * MM:
        v_fs -= 1.0
    v_text = fit_text(v_text, v_fs, max_w, fontname=fontname)

    # Block (Kopfzeile + V-Nummer) vertikal in der Zelle zentrieren.
    # Wichtig: Schriftgroesse ist in PUNKT, nicht mm - Umrechnung ueber MM
    # (Punkt pro mm) nicht vergessen, sonst wird die Zeilenhoehe massiv
    # unterschaetzt und die beiden Zeilen ueberlappen sich (siehe Chat).
    # Ascent/Descent grob als 0.75/0.25 der Schriftgroesse angenommen.
    def _ascent_mm(fs):
        return (fs * 0.75) / MM

    def _descent_mm(fs):
        return (fs * 0.25) / MM

    header_ascent = _ascent_mm(header_fs) if header_txt else 0.0
    header_descent = _descent_mm(header_fs) if header_txt else 0.0
    gap_mm = 1.8 if header_txt else 0.0
    v_ascent = _ascent_mm(v_fs)
    v_descent = _descent_mm(v_fs)

    block_h = header_ascent + header_descent + gap_mm + v_ascent + v_descent
    block_top = y0 + (lh - block_h) / 2

    if header_txt:
        tw_mm = fitz.get_text_length(header_txt, fontname=fontname, fontsize=header_fs) / MM
        tx = x0 + (lw - tw_mm) / 2
        ty = block_top + header_ascent
        page.insert_text((tx * MM, ty * MM), header_txt, fontsize=header_fs,
                          fontname=fontname, color=(0.4, 0.4, 0.4))
        v_baseline = block_top + header_ascent + header_descent + gap_mm + v_ascent
    else:
        v_baseline = block_top + v_ascent

    tw_mm2 = fitz.get_text_length(v_text, fontname=fontname, fontsize=v_fs) / MM
    tx2 = x0 + (lw - tw_mm2) / 2
    page.insert_text((tx2 * MM, v_baseline * MM), v_text, fontsize=v_fs, fontname=fontname)


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
    ):
        # Support both kwarg spellings for backwards compatibility.
        if request_id in (None, "") and experiment_request_id not in (None, ""):
            request_id = experiment_request_id

        super().__init__(parent)
        self._request_id = request_id
        self._table = "tblExperimentRequests"
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

    def _request_has_images(self, request_id: Any) -> bool:
        """Gibt True zurück wenn dem Request Bilder zugeordnet sind."""
        """True if at least one image row exists for this request."""
        if request_id in (None, ""):
            return False
        try:
            with get_connection() as cn:
                cur = cn.cursor()
                cur.execute(
                    "SELECT 1 FROM [tblExperimentRequestImage] WHERE [ExperimentRequestID]=? LIMIT 1",
                    [request_id],
                )
                return cur.fetchone() is not None
        except Exception:
            return False

    def _fetch_request_images(self, request_id: Any) -> List[Dict[str, str]]:
        """Lädt alle Bild-Metadaten eines Requests aus der DB."""
        """Returns dicts with FullPath + display name fields."""
        if request_id in (None, ""):
            return []
        rows: List[Dict[str, str]] = []
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(
                "SELECT [RelativePath], [StoredFilename], [OriginalFilename] "
                "FROM [tblExperimentRequestImage] "
                "WHERE [ExperimentRequestID]=? "
                "ORDER BY [ID] DESC",
                [request_id],
            )
            for rel_path, stored, orig_name in cur.fetchall() or []:
                rel_path_s = str(rel_path or "")
                stored_s = str(stored or "")
                orig_s = str(orig_name or "")
                full = os.path.join(rel_path_s, stored_s) if rel_path_s else stored_s
                # Provide both keys to be compatible with any viewer implementation
                rows.append(
                    {
                        "RelativePath": rel_path_s,
                        "StoredFilename": stored_s,
                        "StoredFile": stored_s,
                        "OriginalFilename": orig_s,
                        "FullPath": full,
                    }
                )
        return rows

    def _update_images_icon(self) -> None:
        """Aktualisiert das Bild-Icon (sichtbar wenn Bilder vorhanden)."""
        btn = getattr(self, "_btn_show_images", None)
        if not btn:
            return
        btn.setVisible(self._request_has_images(self._request_id))

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
            QMessageBox.critical(self, "DB Error", f"Tabelle nicht gefunden: {self._table}")
            return

        cols = er_get_table_columns(self._table)

        try:
            with get_connection() as cn:
                cur = cn.cursor()
                cur.execute(f"SELECT * FROM [{self._table}] WHERE [ID]=?", [self._request_id])
                row = cur.fetchone()
                if not row:
                    QMessageBox.warning(self, "Nicht gefunden", "Der verknuepfte Request wurde nicht gefunden.")
                    return
                names = [d[0] for d in (cur.description or [])]
                data = {names[i]: row[i] for i in range(len(names))}
        except Exception as e:
            QMessageBox.critical(self, "DB Error", str(e))
            return

        # Use tblExperimentRequests.Titel as the popup title (window title + header).
        req_title = "" if data.get("Titel") is None else str(data.get("Titel")).strip()
        if req_title:
            safe = req_title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            self.setWindowTitle(req_title)
            self._title_label.setText(f"<b>{safe}</b>")
        else:
            # Fallback: keep prior behaviour if Titel is missing/empty.
            self.setWindowTitle(f"Experiment Request #{self._request_id}")
            self._title_label.setText(f"Experiment Request <b>#{self._request_id}</b>")

        # Update images indicator after we know the request is valid.
        self._update_images_icon()

        for c in cols:
            fn = c.name

            # Titel is shown in the popup header; do not repeat it inside the form.
            if fn.lower() in ("titel", "title"):
                continue

            # In the create-screen we exclude CreatedBy, but in the read-only popup we DO want it.
            if fn in ER_EXCLUDE_FIELDS and fn.lower() != "createdby":
                continue

            label_txt = "Created By" if fn.lower() == "createdby" else fn
            lbl = QLabel(label_txt)
            lbl.setStyleSheet("padding: 8px 6px; color:#303030; font-weight:600;")

            v = data.get(fn)
            w = self._make_widget_for_field(fn, v)
            self._form.addRow(lbl, w)

            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet("color:#e6e6e6;")
            self._form.addRow(sep)

    def _lookup_project_label(self, project_id: Any) -> str:
        """Gibt den lesbaren Projektnamen für eine Projekt-ID zurück."""
        if project_id in (None, ""):
            return ""
        for t in ("tblProject", "tblProjects"):
            if not table_exists(t):
                continue
            try:
                cols = get_columns_map(t)
                f_num = resolve_field(
                    ["Project Number", "ProjectNumber", "Projekt Nummer", "ProjektNummer", "Number", "Nr"], cols)
                f_name = resolve_field(
                    ["Project Name", "ProjectName", "Projekt Name", "ProjektName", "Name", "Titel", "Title"], cols)
                if not (f_num and f_name):
                    continue
                rows = fetch_all(f"SELECT [{f_num}] AS PN, [{f_name}] AS PName FROM [{t}] WHERE [ID]=?", [project_id])
                if rows:
                    pn = rows[0].get("PN")
                    pnm = rows[0].get("PName")
                    pn = "" if pn is None else str(pn)
                    pnm = "" if pnm is None else str(pnm)
                    out = (pn + " - " + pnm).strip(" -")
                    return out
            except Exception:
                continue
        return str(project_id)

    def _lookup_fk_label(self, field_name: str, fk_id: Any) -> str:
        """Gibt den lesbaren FK-Namen für eine FK-ID zurück (heuristisches Lookup)."""
        if fk_id in (None, ""):
            return ""

        # Special case: tblExperimentRequests.CreatedBy -> tblUser.ID
        # In popups we want a friendly label, not the raw ID.
        if field_name.lower() in {"createdby", "createdbyid"}:
            for t in ("tblUser", "tblUsers"):
                if not table_exists(t):
                    continue
                try:
                    cols = get_columns_map(t)
                    f_user = resolve_field(["Username", "UserName", "Login", "Name"], cols)
                    if not f_user:
                        continue
                    f_first = resolve_field(["FirstName", "First Name", "Vorname", "GivenName"], cols)
                    f_last = resolve_field(["LastName", "Last Name", "Nachname", "Surname", "FamilyName"], cols)

                    sel = [f"[{f_user}] AS U"]
                    sel.append(f"[{f_first}] AS FN" if f_first else "NULL AS FN")
                    sel.append(f"[{f_last}] AS LN" if f_last else "NULL AS LN")
                    sql = f"SELECT {', '.join(sel)} FROM [{t}] WHERE [ID]=?"
                    rows = fetch_all(sql, [fk_id])
                    if rows:
                        u = rows[0].get("U")
                        if u is None:
                            return str(fk_id)
                        u_s = str(u).strip()
                        fn = rows[0].get("FN")
                        ln = rows[0].get("LN")
                        fn_s = "" if fn is None else str(fn).strip()
                        ln_s = "" if ln is None else str(ln).strip()

                        full = (fn_s + " " + ln_s).strip()
                        # Desired format: Username (FirstName LastName)
                        return f"{u_s} ({full})" if full else u_s
                except Exception:
                    continue
            return str(fk_id)

        if field_name.lower() in {"projekt", "project", "projectid", "projektid"}:
            return self._lookup_project_label(fk_id)

        for t in er_try_tables_for_fk(field_name):
            if not table_exists(t):
                continue
            disp = er_pick_display_column(t)
            if not disp:
                continue
            try:
                rows = fetch_all(f"SELECT [ID] AS ID, [{disp}] AS D FROM [{t}] WHERE [ID]=?", [fk_id])
                if rows:
                    d = rows[0].get("D")
                    return "" if d is None else str(d)
            except Exception:
                continue
        return str(fk_id)

    def _make_widget_for_field(self, field_name: str, val: Any) -> QWidget:
        """Erstellt einen passenden Display-Widget für ein Request-Feld."""
        # If looks like FK, render label
        try:
            looks_fk = (
                    field_name.lower().endswith('id')
                    or field_name.lower() in {'projekt', 'project', 'createdby', 'createdbyid'}
            )
        except Exception:
            looks_fk = False

        if looks_fk and val not in (None, ""):
            txt = self._lookup_fk_label(field_name, val)
        else:
            txt = "" if val is None else str(val)

        if field_name in ER_DATE_FIELDS and txt:
            # keep raw string; Access via ODBC can be datetime/date
            # Normalize to dd.MM.yyyy (no time)
            try:
                from datetime import datetime, date
                if isinstance(val, (datetime, date)):
                    txt = val.strftime("%d.%m.%Y")
                else:
                    s = str(txt).strip()
                    # common Access/ODBC representations
                    s = s.replace("T", " ")
                    # strip timezone if present
                    s = re.sub(r"(Z|[+-]\d{2}:\d{2})$", "", s).strip()
                    # keep only date part if time is present
                    s_date = s.split(" ")[0]
                    if re.match(r"^\d{4}-\d{2}-\d{2}$", s_date):
                        dt = datetime.strptime(s_date, "%Y-%m-%d")
                        txt = dt.strftime("%d.%m.%Y")
                    elif re.match(r"^\d{2}\.\d{2}\.\d{4}$", s_date):
                        txt = s_date  # already desired
                    else:
                        # try a couple more common formats
                        for fmt in ("%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y"):
                            try:
                                dt = datetime.strptime(s_date, fmt)
                                txt = dt.strftime("%d.%m.%Y")
                                break
                            except Exception:
                                continue
            except Exception:
                pass

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


def execute_non_query(sql: str, params: list | tuple = ()) -> int:
    """INSERT/UPDATE/DELETE-Wrapper: gibt rowcount zurück.
    Gibt mindestens 1 zurück wenn kein Exception, da MySQL rowcount bei
    UPDATE ohne Wertänderung 0 zurückgibt (CLIENT_FOUND_ROWS nicht gesetzt).
    """
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(sql, params)
        rc = getattr(cur, "rowcount", -1)
        # rowcount = -1: Treiber kann es nicht bestimmen → als Erfolg werten
        # rowcount =  0: kein Treffer (falsche ID) oder Wert unverändert
        # rowcount >  0: Zeilen betroffen
        if rc == -1:
            return 1
        return rc or 0


def table_exists(name: str) -> bool:
    """Gibt True zurück wenn die Tabelle in der DB existiert."""
    return _db_table_exists(name.lower())


def get_columns_map(table: str) -> Dict[str, str]:
    """Gibt {normierter_Name: echter_Name} für alle Spalten zurück."""
    """{lower_name: real_name}"""
    return _db_get_columns_map(table.lower())


def get_columns_info(table: str) -> List[Dict[str, Any]]:
    """Gibt Spalten-Metadaten (Name, Typ, Nullable) zurück."""
    """Spalteninfos (MySQL)."""
    cmap = _db_get_columns_map(table.lower())
    out: List[Dict[str, Any]] = []
    for lc, real in cmap.items():
        out.append({"lower": lc, "real": real, "data_type": None, "type_name": None})
    return out


def norm(s: str) -> str:
    """Normalisiert einen Spaltennamen (strip + lowercase, Sonderzeichen entfernen)."""
    return (
        (s or "")
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("(", "")
        .replace(")", "")
        .replace("°", "")
        .replace("/", "")
        .replace("-", "")
        .strip()
    )


def resolve_field(cands: List[str], cols_map: Dict[str, str]) -> Optional[str]:
    """Gibt den ersten Kandidaten zurück der in cols_map vorhanden ist."""
    for cand in cands:
        lc = cand.lower()
        if lc in cols_map:
            return cols_map[lc]
    inv = {norm(k): v for k, v in cols_map.items()}
    for cand in cands:
        nk = norm(cand)
        if nk in inv:
            return inv[nk]
    return None


def canon_rule(ff: Optional[str]) -> Optional[str]:
    """Normalisiert einen Feldnamen für Spalten-Matching-Regeln."""
    """DB-Rule -> onlySZ | onlyInteger | onlyDoubles | dropdown:tblXxx | hidden | None."""
    if not ff:
        return None
    s = norm(ff)
    if s in {"onlysz", "sz"}:
        return "onlySZ"
    if s in {"onlyinteger", "integer", "int", "ganzzahl"}:
        return "onlyInteger"
    if s in {"onlydouble", "onlydoubles", "double", "doubles", "float", "zahlmitkomma", "decimal"}:
        return "onlyDoubles"
    if s == "hidden":
        return "hidden"
    if ff.lower().startswith("dropdown:"):
        return ff.strip()
    return None


# ------------------------ Pivot Table Model ------------------------

@dataclass
class CellBinding:
    """Verbindet eine Pivot-Tabellen-Zelle mit einem konkreten DB-Datensatz.

    Enthält: Tabelle, Spalte, Primärschlüssel – genug um einen einzelnen UPDATE auszuführen.
    """
    table: str
    id_field: str
    id_value: Any
    field: str


@dataclass
class GroupCellBinding:
    """Wie CellBinding, aber für YarnUse-Gruppen: schreibt denselben Wert
    in mehrere tblTrialSettings-Zeilen gleichzeitig.
    """
    table: str
    id_field: str
    id_values: List[int]  # alle Settings-IDs der Gruppe
    field: str


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

    @property
    def _ALT_EVEN(self):
        return QColor(accent_tint())

    @property
    def _ALT_ODD(self):
        return QColor(accent_gridline())

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
        # Shift dirty indices
        self._dirty = [(r + n_new, c, v) for r, c, v in self._dirty]
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

    def _ctx_is_readonly(self) -> bool:
        """Gibt True zurück wenn der Screen im Read-Only-Modus ist."""
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

    # ---- Validation helpers ----
    _re_int = re.compile(r"^[+-]?\d+$")
    # akzeptiert: 123 | 123. | 123, | .5 | ,5 | 123.45 | 123,45 | +.7 | -0,8
    _re_float_like = re.compile(r"^[+-]?((\d+([.,]\d*)?)|([.,]\d+))$")
    _re_float_2dp = re.compile(r"^[+-]?(\d+([.,]\d{0,2})?|[.,]\d{1,2})$")

    def _validate_and_normalize(self, row: int, text_in: Any) -> Optional[str]:
        """Validiert und normalisiert einen Eingabewert je nach Zeilentyp.

        Returns:
            Normalisierter Wert als String, oder None bei ungültigem Wert.
        """
        """
        Gibt normalisierten String zurück, "" wenn leer (-> NULL), oder None wenn invalid.
        - onlySZ: nur S, Z, SZ (case-insensitiv), Ausgabe uppercase
        - onlyInteger: Ganzzahl (Vorzeichen ok), Ausgabe ohne führende Nullen
        - onlyDoubles: Ganzzahl oder Dezimal (Punkt/Komma), Ausgabe mit Punkt, Ganzzahl ohne .0
        """
        if text_in is None:
            return ""
        s = str(text_in).strip()
        if s == "":
            return ""  # leeren Wert erlauben

        rule = self._validators[row] if 0 <= row < len(
            self._validators) else None
        rule = canon_rule(rule)
        if not rule:
            return s  # keine Regel

        if rule == "onlySZ":
            up = s.upper().replace(" ", "")
            return up if up in ("S", "Z", "SZ") else None

        if rule == "onlyInteger":
            if self._re_int.fullmatch(s):
                try:
                    return str(int(s))
                except Exception:
                    return None
            return None

        if rule == "onlyDoubles":
            if not self._re_float_like.fullmatch(s):
                return None
            try:
                v = float(s.replace(",", "."))
                return str(int(v)) if v.is_integer() else f"{v}"
            except Exception:
                return None

        return s

    def data(self, index: QModelIndex, role=Qt.DisplayRole):  # type: ignore[override]
        """Liefert Zelldaten: Wert, Hintergrundfarbe (Ply-abhängig + Alerts), Alignment."""
        if not index.isValid():
            return None
        r, c = index.row(), index.column()

        # ── pseudo-header rows ────────────────────────────────────────────
        if r < self._n_hdr:
            hdr = self._header_rows[r]
            if role == Qt.BackgroundRole:
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
            if role == Qt.ToolTipRole:
                tips = hdr.get("tooltips", [])
                tip = tips[c] if c < len(tips) else ""
                return tip if tip else None
            if role == Qt.TextAlignmentRole:
                return Qt.AlignCenter
            if role == Qt.FontRole:
                f = QFont()
                f.setBold(True)
                return f
            return None

        # ── normal data rows ──────────────────────────────────────────────
        dr = r - self._n_hdr  # index into _row_titles / _matrix

        # Elongation CV highlight: Wert >= 10 -> rot + fett + heller Rohhintergrund
        _is_elong_cv_alert = False
        # Tenacity CV highlight: Wert >= 10 -> rot + fett + heller Rohhintergrund (analog Elongation CV)
        _is_ten_cv_alert = False
        if c > 0 and 0 <= dr < len(self._row_titles):
            _title = self._row_titles[dr]
            if "Elongation CV" in _title:
                _raw = self._matrix[dr][c - 1]
                try:
                    _fval = float(str(_raw).replace(",", ".")) if _raw not in (None, "") else None
                    if _fval is not None and _fval >= 10.0:
                        _is_elong_cv_alert = True
                except Exception:
                    pass
            if "Tenacity CV" in _title:
                _raw = self._matrix[dr][c - 1]
                try:
                    _fval = float(str(_raw).replace(",", ".")) if _raw not in (None, "") else None
                    if _fval is not None and _fval >= 10.0:
                        _is_ten_cv_alert = True
                except Exception:
                    pass

        # cell-level alert (Titer out-of-tolerance, Tenacity orange, etc.)
        _cell_alert = self._cell_alerts.get((dr, c - 1)) if c > 0 else None

        if role == Qt.BackgroundRole:
            if _is_elong_cv_alert or _is_ten_cv_alert or _cell_alert == "red":
                return QColor("#FFD0D0")  # helles Rot
            if _cell_alert == "orange":
                return QColor("#FFE5B4")  # helles Orange
            return self._ALT_EVEN if (dr % 2 == 0) else self._ALT_ODD
        if role == Qt.ForegroundRole:
            if _is_elong_cv_alert or _is_ten_cv_alert or _cell_alert == "red":
                return QColor("#CC0000")  # kräftiges Rot
            if _cell_alert == "orange":
                return QColor("#B85C00")  # dunkel Orange
            return self._FG_BLACK
        if role == Qt.FontRole:
            if _is_elong_cv_alert or _is_ten_cv_alert or _cell_alert in ("red", "orange"):
                f = QFont()
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
        if title == "Air Pressure (bar)":
            s2 = normalized.strip()
            if s2 != "":
                if not self._re_float_2dp.fullmatch(s2):
                    return False
                try:
                    v = float(s2.replace(",", "."))
                    s2n = f"{v:.2f}".rstrip("0").rstrip(".")
                    normalized = s2n
                except Exception:
                    return False

        r, c = index.row() - self._n_hdr, index.column() - 1
        if self._matrix[r][c] == normalized:
            return True
        self._matrix[r][c] = normalized
        self._dirty.append((r, c, normalized))
        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
        return True

    def set_cell(self, row: int, col: int, value: Any, binding: Optional[CellBinding]):
        """Setzt Wert und Binding einer Zelle (beim Laden der Daten)."""
        self._matrix[row][col] = "" if value is None else str(value)
        self._binding[row][col] = binding

    def get_cell_value(self, row: int, col: int) -> Optional[str]:
        if 0 <= row < len(self._matrix) and 0 <= col < len(self._matrix[row]):
            return self._matrix[row][col]
        return None

    def get_binding(self, row: int, col: int) -> Optional[CellBinding]:
        if 0 <= row < len(self._binding) and 0 <= col < len(self._binding[row]):
            return self._binding[row][col]
        return None

    def save_dirty(self) -> int:
        """Schreibt alle geänderten Zellen in die DB.

        Spezialfall für Labortabellen (tblLaborXXX):
        - neben dem geänderten Feld werden, falls vorhanden,
          auch [User] und [Timestamp] aktualisiert:
            * [User]      = aktueller User (app_meta.current_user)
            * [Timestamp] = NOW() (Serverzeit in Access)
        """
        n = 0

        # einfacher Cache pro Modellinstanz, damit get_columns_map()
        # nicht für jede einzelne Zelle erneut aufgerufen wird
        cache = getattr(self, "_lab_audit_cache", None)
        if cache is None:
            cache = {}
            self._lab_audit_cache = cache

        # aktuellen User einmalig ermitteln
        user_id = None
        try:
            user = getattr(app_meta, "current_user", {}) or {}
        except Exception:
            user = {}
        if isinstance(user, dict):
            for k in ("ID", "Id", "id"):
                if k in user:
                    user_id = user[k]
                    break

        for r, c, new_text in self._dirty:
            bind = self._binding[r][c]
            if not bind:
                continue

            # ── GroupCellBinding: alle IDs der Gruppe updaten ─────────────
            if isinstance(bind, GroupCellBinding):
                text_str = "" if new_text is None else str(new_text).strip()
                for gid in bind.id_values:
                    if text_str == "":
                        sql = (
                            f"UPDATE {bind.table} SET "
                            f"`{bind.field}` = NULL WHERE `{bind.id_field}` = ?"
                        )
                        params: list[Any] = [gid]
                    else:
                        sql = (
                            f"UPDATE {bind.table} SET "
                            f"`{bind.field}` = ? WHERE `{bind.id_field}` = ?"
                        )
                        params = [text_str, gid]
                    n += execute_non_query(sql, params)
                continue

            table_name = str(bind.table)
            is_lab_table = table_name.lower().startswith("tbllabor")

            user_col = None
            ts_col = None
            if is_lab_table:
                # Spaltennamen für User/Timestamp pro Tabelle cachen
                if table_name in cache:
                    user_col, ts_col = cache[table_name]
                else:
                    try:
                        cols = get_columns_map(table_name)
                    except Exception:
                        cols = {}
                    user_col = cols.get("user")
                    ts_col = cols.get("timestamp")
                    cache[table_name] = (user_col, ts_col)

            text_str = "" if new_text is None else str(new_text).strip()

            # Einheiten-Umrechnung: Anzeige-Einheit -> DB-Einheit (z.B. l/min -> Nm3/h)
            if text_str != "" and self._unit_scale != 1.0 and bind.field == self._unit_scale_field:
                try:
                    _disp_val = float(text_str.replace(",", "."))
                    text_str = repr(_disp_val / self._unit_scale)
                except Exception:
                    pass

            if text_str == "":
                # Wert -> NULL
                if is_lab_table and (user_col or ts_col):
                    set_parts = [f"[{bind.field}] = NULL"]
                    params: list[Any] = []
                    if user_col:
                        set_parts.append(f"[{user_col}] = ?")
                        params.append(user_id)
                    if ts_col:
                        set_parts.append(f"[{ts_col}] = NOW()")
                    sql = (
                            f"UPDATE {bind.table} SET "
                            + ", ".join(set_parts)
                            + f" WHERE [{bind.id_field}] = ?"
                    )
                    params.append(bind.id_value)
                else:
                    sql = (
                        f"UPDATE {bind.table} SET "
                        f"[{bind.field}] = NULL WHERE [{bind.id_field}] = ?"
                    )
                    params = [bind.id_value]
            else:
                # normaler UPDATE mit neuem Wert
                if is_lab_table and (user_col or ts_col):
                    set_parts = [f"[{bind.field}] = ?"]
                    params = [text_str]
                    if user_col:
                        set_parts.append(f"[{user_col}] = ?")
                        params.append(user_id)
                    if ts_col:
                        set_parts.append(f"[{ts_col}] = NOW()")
                    sql = (
                            f"UPDATE {bind.table} SET "
                            + ", ".join(set_parts)
                            + f" WHERE [{bind.id_field}] = ?"
                    )
                    params.append(bind.id_value)
                else:
                    sql = (
                        f"UPDATE {bind.table} SET "
                        f"[{bind.field}] = ? WHERE [{bind.id_field}] = ?"
                    )
                    params = [text_str, bind.id_value]

            n += execute_non_query(sql, params)

        self._dirty.clear()
        self.dataChangedExternally.emit()
        return n


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
        """Return display name for an ID stored internally."""
        if internal is None or str(internal).strip() == "":
            return ""
        # Direkt suchen
        v = lookup_map.get(internal)
        if v is not None:
            return v
        # Als String suchen
        v = lookup_map.get(str(internal))
        if v is not None:
            return v
        # Als int suchen
        try:
            v = lookup_map.get(int(internal))
            if v is not None:
                return v
        except Exception:
            pass
        return str(internal)

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
                try:
                    hid = int(value)
                except Exception:
                    hid = None if value in (None, "", " ") else value
                r = index.row() - self._n_hdr
                c = index.column() - 1
                if 0 <= r < len(self._matrix) and 0 <= c < len(self._matrix[r]):
                    new_val = "" if hid is None else str(hid)
                    if self._matrix[r][c] == new_val:
                        return True
                    self._matrix[r][c] = new_val
                    self._dirty.append((r, c, new_val))
                    self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
                    return True
                return False
            # Jet row
            if index.row() == self._n_hdr + self._jet_row_index:
                try:
                    jet_id = int(value)
                except Exception:
                    if value in (None, "", " "):
                        jet_id = None
                    else:
                        return False
                r = index.row() - self._n_hdr
                c = index.column() - 1
                if 0 <= r < len(self._matrix) and 0 <= c < len(self._matrix[r]):
                    current = self._matrix[r][c]
                    new_val = "" if jet_id is None else str(jet_id)
                    if current == new_val:
                        return True
                    self._matrix[r][c] = new_val
                    self._dirty.append((r, c, new_val))
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


class _ManagePliesDialog(QDialog):
    """Manage plies for a single trial (with optional multi-trial apply).

    Shows all tblTrialSettings rows for the trial (Ply label, Yarn).
    - Add ply: yarn dropdown + series-wide consistent ply number
      → optionally apply to multiple trials in the same series
    - Remove ply: delete selected row (with confirmation)

    Ply numbering is series-wide consistent:
    - If the selected yarn already has a ply number anywhere in the series → reuse it
    - Otherwise → next free number not yet used anywhere in the series
    """

    def __init__(self, parent, trial_id: int, vno, series_pk: int,
                 yarn_list: List[Tuple[int, str]],
                 all_trials: List[Tuple[int, str]] | None = None):
        super().__init__(parent)
        self._trial_id = trial_id
        self._series_pk = series_pk
        self._yarn_list = yarn_list  # [(id, name), ...]
        # all_trials: [(trial_id, vno_label), ...] alle Trials der Series
        self._all_trials = all_trials or [(trial_id, str(vno))]
        self.setWindowTitle(f"Manage Plies – V{vno}")
        self.setMinimumWidth(500)
        self._build_ui()
        self._load()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        # YarnUse-Liste laden
        self._yarn_use_list: List[Tuple[Optional[int], str]] = [(None, "—")]
        try:
            for r in fetch_all("SELECT ID, Name FROM tblYarnUse ORDER BY ID"):
                self._yarn_use_list.append((int(r["ID"]), str(r.get("Name") or "")))
        except Exception:
            pass

        # Table: Ply | Yarn | Yarn Use
        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(["Ply", "Yarn", "Yarn Use"])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.verticalHeader().setVisible(False)
        lay.addWidget(self.tbl)

        # Add row
        add_lay = QHBoxLayout()
        add_lay.setSpacing(6)
        self._cmb_yarn = QComboBox()
        self._cmb_yarn.setPlaceholderText("Select yarn…")
        self._cmb_yarn.addItem("", None)
        for yid, yname in self._yarn_list:
            self._cmb_yarn.addItem(yname, yid)
        self._cmb_yarn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._cmb_yarn_use = QComboBox()
        self._cmb_yarn_use.setToolTip("Group (optional)")
        for uid, uname in self._yarn_use_list:
            self._cmb_yarn_use.addItem(uname, uid)
        self._cmb_yarn_use.setFixedWidth(100)

        from PySide6.QtWidgets import QSpinBox, QLabel as _Lbl
        lbl_ends = _Lbl("Ends:")
        self._spn_ends = QSpinBox()
        self._spn_ends.setMinimum(1)
        self._spn_ends.setMaximum(20)
        self._spn_ends.setValue(1)
        self._spn_ends.setFixedWidth(55)
        self._spn_ends.setToolTip("Number of ends")

        btn_add = QPushButton("+ Add Ply")
        btn_add.setFixedWidth(100)
        btn_add.clicked.connect(self._on_add)
        add_lay.addWidget(self._cmb_yarn)
        add_lay.addWidget(self._cmb_yarn_use)
        add_lay.addWidget(lbl_ends)
        add_lay.addWidget(self._spn_ends)
        add_lay.addWidget(btn_add)
        lay.addLayout(add_lay)

        # Remove button
        btn_remove = QPushButton("Remove Selected Ply")
        btn_remove.clicked.connect(self._on_remove)
        lay.addWidget(btn_remove)

        # Multi-trial apply (nur anzeigen wenn Series mehrere Trials hat)
        if len(self._all_trials) > 1:
            from PySide6.QtWidgets import QGroupBox, QScrollArea, QWidget
            grp = QGroupBox("Also apply to:")
            grp_lay = QVBoxLayout(grp)
            grp_lay.setSpacing(2)
            grp_lay.setContentsMargins(6, 4, 6, 4)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setMaximumHeight(120)
            from PySide6.QtWidgets import QFrame
            scroll.setFrameShape(QFrame.NoFrame)
            inner = QWidget()
            inner_lay = QVBoxLayout(inner)
            inner_lay.setSpacing(1)
            inner_lay.setContentsMargins(0, 0, 0, 0)

            self._trial_checkboxes: List = []
            for tid, vlabel in self._all_trials:
                from PySide6.QtWidgets import QCheckBox
                cb = QCheckBox(f"V{vlabel}")
                cb.setChecked(tid == self._trial_id)
                cb.setEnabled(tid != self._trial_id)  # aktueller Trial immer an, nicht abwählbar
                inner_lay.addWidget(cb)
                self._trial_checkboxes.append((tid, cb))

            inner_lay.addStretch()
            scroll.setWidget(inner)
            grp_lay.addWidget(scroll)
            lay.addWidget(grp)
        else:
            self._trial_checkboxes = [(self._trial_id, None)]

        # Close button
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.accept)  # Close = accept so rebuild happens
        lay.addWidget(btns)

    def _load(self):
        self.tbl.setRowCount(0)
        rows = fetch_all(
            """
            SELECT TS.ID, TS.Ply, Y.Name AS YarnName
            FROM tblTrialSettings AS TS
                     LEFT JOIN tblYarn AS Y ON Y.ID = TS.YarnID
            WHERE TS.TrialID = ?
            """,
            [self._trial_id],
        )

        # Sort by numeric part of Ply label (Ply 1, Ply 2, ...)
        def _ply_sort_key(r):
            ply = (r.get("Ply") or "").strip()
            m = re.search(r"\d+", ply)
            return int(m.group()) if m else 9999

        rows = sorted(rows, key=_ply_sort_key)
        for r in rows:
            rr = self.tbl.rowCount()
            self.tbl.insertRow(rr)
            self.tbl.setItem(rr, 0, QTableWidgetItem(str(r.get("Ply") or "")))
            self.tbl.setItem(rr, 1, QTableWidgetItem(str(r.get("YarnName") or "")))
            self.tbl.item(rr, 0).setData(Qt.UserRole, int(r["ID"]))  # settings ID

    def _resolve_ply_label(self) -> str:
        """Return the next free Ply label for this trial (1, 2, 3, ...).

        Collects all numeric parts of existing Ply labels for this trial
        and returns the lowest integer >= 1 not yet in use.
        """
        trial_rows = fetch_all(
            "SELECT Ply FROM tblTrialSettings WHERE TrialID = ?",
            [self._trial_id],
        )
        used_numbers: set = set()
        for r in trial_rows:
            ply = (r.get("Ply") or "").strip()
            if ply:
                m = re.search(r"\d+", ply)
                if m:
                    used_numbers.add(int(m.group()))
        n = 1
        while n in used_numbers:
            n += 1
        return f"Ply {n}"

    def _on_add(self):
        yarn_id = self._cmb_yarn.currentData()
        if yarn_id is None:
            QMessageBox.warning(self, "Add Ply", "Please select a yarn.")
            return

        n_ends = max(1, int(self._spn_ends.value()))
        yarn_use_id = self._cmb_yarn_use.currentData()

        # Welche Trials sind angewählt?
        target_ids = []
        for tid, cb in self._trial_checkboxes:
            if cb is None or cb.isChecked():
                target_ids.append(tid)
        if not target_ids:
            target_ids = [self._trial_id]

        # Nächste n freie Ply-Nummern berechnen
        trial_rows = fetch_all(
            "SELECT Ply FROM tblTrialSettings WHERE TrialID = ?",
            [self._trial_id],
        )
        used_numbers: set = set()
        for r in trial_rows:
            ply = (r.get("Ply") or "").strip()
            if ply:
                m = re.search(r"\d+", ply)
                if m:
                    used_numbers.add(int(m.group()))

        ply_labels = []
        n = 1
        for _ in range(n_ends):
            while n in used_numbers:
                n += 1
            ply_labels.append(f"Ply {n}")
            used_numbers.add(n)
            n += 1

        # Konsistenzprüfung für alle Ply-Labels
        for ply_label in ply_labels:
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
                [self._series_pk, ply_label, yarn_id],
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

        try:
            with get_connection() as cn:
                cur = cn.cursor()
                cols_map = _db_get_columns_map("tblTrialSettings")
                has_gid = any(k == "globalid" for k in cols_map)
                has_yarnuse = any(k == "yarnuseid" for k in cols_map)

                for tid in target_ids:
                    for ply_label in ply_labels:
                        cols = ["TrialID", "YarnID", "Ply"]
                        vals: list = [tid, yarn_id, ply_label]
                        if has_yarnuse and yarn_use_id is not None:
                            cols.append("YarnUseID")
                            vals.append(yarn_use_id)
                        if has_gid:
                            cols.append("GlobalID")
                            vals.append(new_global_id())
                        ph = ", ".join(["?"] * len(vals))
                        cur.execute(
                            f"INSERT INTO tblTrialSettings ({', '.join(cols)}) VALUES ({ph})",
                            vals,
                        )
                cn.commit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not add ply:\n{e}")
            return

        self._load()

    def _on_remove(self):
        row = self.tbl.currentRow()
        if row < 0:
            QMessageBox.information(self, "Remove Ply", "Please select a ply row.")
            return

        ply_label = self.tbl.item(row, 0).text() if self.tbl.item(row, 0) else "?"
        yarn_name = self.tbl.item(row, 1).text() if self.tbl.item(row, 1) else "?"
        settings_id = self.tbl.item(row, 0).data(Qt.UserRole) if self.tbl.item(row, 0) else None

        if settings_id is None:
            return

        if self.tbl.rowCount() <= 1:
            QMessageBox.warning(
                self, "Remove Ply",
                "Cannot remove the last ply.\nA trial must have at least one ply."
            )
            return

        # Which trials are checked?
        target_ids = []
        for tid, cb in self._trial_checkboxes:
            if cb is None or cb.isChecked():
                target_ids.append(tid)
        if not target_ids:
            target_ids = [self._trial_id]

        multi = len(target_ids) > 1
        if multi:
            answer = QMessageBox.question(
                self, "Remove Ply",
                f"Remove ply «{ply_label}» ({yarn_name}) from {len(target_ids)} trials?\n\n"
                f"Trials where «{ply_label}» is the last remaining ply will be skipped.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
        else:
            answer = QMessageBox.question(
                self, "Remove Ply",
                f"Remove ply «{ply_label}» ({yarn_name}) and all its stored values?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
        if answer != QMessageBox.Yes:
            return

        skipped = []
        try:
            with get_connection() as cn:
                cur = cn.cursor()
                for tid in target_ids:
                    # Check how many plies this trial has
                    cur.execute(
                        "SELECT COUNT(*) AS cnt FROM tblTrialSettings WHERE TrialID = ?",
                        (tid,)
                    )
                    cnt_row = cur.fetchone()
                    cnt = cnt_row[0] if cnt_row else 0
                    if cnt <= 1:
                        # Fetch vno label for warning message
                        cur.execute(
                            "SELECT Versuchsnummer FROM tblTrial WHERE ID = ?", (tid,))
                        vno_row = cur.fetchone()
                        vno_lbl = vno_row[0] if vno_row else str(tid)
                        skipped.append(f"V{vno_lbl}")
                        continue
                    if tid == self._trial_id:
                        # Current trial: delete by settings ID (exact row)
                        cur.execute(
                            "DELETE FROM tblTrialSettings WHERE ID = ?", (settings_id,))
                    else:
                        # Other trials: match by Ply label
                        cur.execute(
                            "DELETE FROM tblTrialSettings WHERE TrialID = ? AND Ply = ?",
                            (tid, ply_label))
                cn.commit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not remove ply:\n{e}")
            return

        if skipped:
            QMessageBox.warning(
                self, "Remove Ply — Partial",
                f"Ply «{ply_label}» was removed from the selected trials.\n\n"
                f"The following trials were skipped because «{ply_label}» "
                f"was their last remaining ply:\n"
                + "\n".join(f"  • {v}" for v in skipped)
            )

        self._load()


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
            self._screen._multiply_trial_from_col_spec_idx(col - 1)
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
            # Custom Group Toggle
            menu.addSeparator()
            cg_visible = getattr(self._screen, '_custom_group_visible', False)
            act_cg = menu.addAction(
                "Custom Group ausblenden" if cg_visible else "Custom Group anzeigen"
            )
            chosen = menu.exec(event.globalPos())
            if act_fill and chosen == act_fill:
                self._screen._fill_machine_row_from_title(row, is_rd=self._is_rd)
            elif chosen == act_cg:
                self._screen._toggle_custom_group_row()
            return True

        _tbl_attr = "tbl_rd_machine" if self._is_rd else "tbl_machine"
        try:
            right_view = getattr(
                getattr(self._screen, _tbl_attr, None), "right", None
            )
            if right_view is not None and view is right_view:
                span = right_view.columnSpan(row, col)
                if span > 1:
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


class ShowExperimentScreen(QWidget):
    def __init__(self, on_back_home, on_back_all_experiments=None, on_add_trials=None):
        super().__init__()
        self.on_back_home = on_back_home
        self.on_back_all_experiments = on_back_all_experiments
        self.on_add_trials = on_add_trials
        self.on_open_report = None  # wird von MainWindow gesetzt (→ _go_report)
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

            for r_off, row_vals in enumerate(grid):
                tr = start_row + r_off
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

    def _register_save_model(self, attr_name: str):
        """Registers a model attribute name for generic save handling.

        We keep names (not instances) so we can apply special post-save hooks
        (e.g. Itemat recompute) based on the attribute.
        """
        if not hasattr(self, "_save_model_names"):
            self._save_model_names = []
        if attr_name not in self._save_model_names:
            self._save_model_names.append(attr_name)

    def _iter_save_models(self):
        """Yields (attr_name, model) for all registered models that exist."""
        for name in getattr(self, "_save_model_names", []) or []:
            m = getattr(self, name, None)
            if m is not None:
                yield name, m

    def _load_jets_lookup(self):
        """Lädt alle Jets aus tblDTYJets (ID + Jet-Name, A–Z sortiert)
        sowie Geometrie-Daten für den Hover-Tooltip."""
        self._jets_list = []
        self._jets_map = {}
        self._jets_name_to_id = {}
        self._jets_tooltip_map: Dict[Any, str] = {}
        try:
            rows = fetch_all(
                """
                SELECT [ID], [Jet], [Luftbohrung], [WinkelLuftbohrung], [GarnkanalBreite], [Luftverbrauch], [Entwicklungsname]
                FROM [tblDTYJets]
                ORDER BY [Jet] ASC
                """
            )
        except Exception:
            # Fallback ohne Geometrie-Spalten
            try:
                rows = fetch_all(
                    """
                    SELECT [ID], [Jet]
                    FROM [tblDTYJets]
                    ORDER BY [Jet] ASC
                    """
                )
            except Exception:
                rows = []
        for r in rows:
            jid = r.get("ID")
            name = r.get("Jet")
            if jid is None:
                continue
            nm = name or ""
            self._jets_list.append((jid, nm))
            # sowohl mit int- als auch mit str-Key zugreifbar
            try:
                self._jets_map[int(jid)] = nm
            except Exception:
                pass
            self._jets_map[str(jid)] = nm
            # Reverse lookup for paste (Jet-Name -> JetID)
            key = str(nm).strip()
            if key:
                self._jets_name_to_id[key] = jid
                self._jets_name_to_id[key.lower()] = jid

            # Geometrie-Tooltip aufbauen
            def _fmt(val, unit, superscript=""):
                if val is None or str(val).strip() == "":
                    return "—"
                return f"{val}{superscript} {unit}".strip()

            lines = []
            lb = r.get("Luftbohrung")
            wlb = r.get("WinkelLuftbohrung")
            gb = r.get("GarnkanalBreite")
            lv = r.get("Luftverbrauch")
            if lb is not None: lines.append(f"Luftbohrung:          {_fmt(lb, 'mm')}")
            if wlb is not None: lines.append(f"Winkel Luftbohrung:   {_fmt(wlb, '°')}")
            if gb is not None: lines.append(f"Garnkanal-Breite:     {_fmt(gb, 'mm')}")
            if lv is not None: lines.append(f"Luftverbrauch:        {_fmt(lv, 'Nm³/h')}")
            en = r.get("Entwicklungsname")
            if en is not None and str(en).strip(): lines.append(f"Entwicklungsname:     {en}")
            if lines:
                tip = "\n".join(lines)
                try:
                    self._jets_tooltip_map[int(jid)] = tip
                except Exception:
                    pass
                self._jets_tooltip_map[str(jid)] = tip

    def _load_housing_lookup(self):
        """Lädt alle Housings aus tblHousing (ID + HousingName + Link, A-Z sortiert)."""
        self._housing_list = []
        self._housing_map = {}
        self._housing_image_map: Dict[Any, str] = {}
        try:
            if not table_exists("tblHousing"):
                return
            cmap = get_columns_map("tblHousing")
            col_id = resolve_field(["ID"], cmap) or "ID"
            col_name = resolve_field(["HousingName", "Name", "Bezeichnung"], cmap)
            if not col_name:
                return
            col_link = resolve_field(["Link", "link", "Image", "ImagePath", "Bild"], cmap)
            if col_link:
                rows = fetch_all(
                    f"SELECT [{col_id}] AS HID, [{col_name}] AS HName, [{col_link}] AS HLink "
                    f"FROM tblHousing ORDER BY [{col_name}] ASC"
                )
            else:
                rows = fetch_all(
                    f"SELECT [{col_id}] AS HID, [{col_name}] AS HName "
                    f"FROM tblHousing ORDER BY [{col_name}] ASC"
                )
        except Exception:
            rows = []
        for r in rows:
            hid = r.get("HID")
            name = r.get("HName") or ""
            if hid is None:
                continue
            self._housing_list.append((hid, str(name)))
            try:
                self._housing_map[int(hid)] = str(name)
            except Exception:
                pass
            self._housing_map[str(hid)] = str(name)
            link = r.get("HLink") or ""
            if str(link).strip():
                try:
                    self._housing_image_map[int(hid)] = str(link).strip()
                except Exception:
                    pass
                self._housing_image_map[str(hid)] = str(link).strip()

    # ---------- PUBLIC API ----------

    def load_record(self, exp_pk: int, series_pk: int, experiment_id: str):
        self._ys_cache = {}  # Neue Series -> Cache leeren
        self._machine_cache = {}  # Machine-Cache immer neu aufbauen (verhindert Stale-Fields)
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

        ts = fetch_all(
            "SELECT SeriesName, Notes FROM tblTrialSeries WHERE ID = ?", [series_pk])
        series_name = ts[0]["SeriesName"] if ts else ""
        self.lbl_small_title.setText(f"{experiment_id} – {series_name}")
        self.lbl_series_id.setText(f"TrialSeriesID: {series_pk}")

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

        # Tab ist jetzt im Widget — Hervorhebung setzen
        self._update_notes_tab_style()

        # Beim Öffnen: "Machine Data" aktiv
        if hasattr(self, "tab_machine") and self.tab_machine is not None:
            self.tabs.setCurrentWidget(self.tab_machine)

    # ---------- UI ----------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = HeaderBar(title="Show Experiment",
                           show_home=True, show_back=True)
        header.connect_home(self._back_home)
        header.connect_back(self._back_all_experiments)
        root.addWidget(header)

        # Titelzeile (dunkler Balken + Save)
        tools = QFrame()
        tl = QHBoxLayout(tools)
        tl.setContentsMargins(24, 12, 24, 0)
        tl.setSpacing(8)

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
        root.addWidget(tools)

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
        self.lbl_material_value.setStyleSheet(
            "border:1px solid " + get_accent() + "; border-radius:4px; padding:6px 10px;"
                                                 "color:#202020; background:#f8fff9;"
        )

        mwl.addWidget(self.lbl_material_title, 0, Qt.AlignVCenter)
        mwl.addWidget(self.lbl_material_value, 1, Qt.AlignVCenter)
        root.addWidget(mat_wrap)

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
        root.addWidget(tabs_header, 0)

        root.addWidget(self.tabs, 1)

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
        self._rb_compact = QRadioButton("Kompakt")
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

        vm.addWidget(self._mat_filter_bar)

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
        try:
            lvl = int(getattr(app_meta, "access_level", lambda: 0)() or 0)
            return lvl
        except Exception:
            pass
        try:
            user = getattr(app_meta, "current_user", {}) or {}
            return int(user.get("access_level") or user.get("AccessLevel") or 0)
        except Exception:
            return 0

    def _sync_save_button_access(self) -> None:
        """Keep Save button state consistent with the behaviour of Ctrl+S."""
        try:
            can_write = self._get_access_level() > 1
            if hasattr(self, "btn_save") and self.btn_save:
                self.btn_save.setEnabled(bool(can_write))
                if not can_write:
                    self.btn_save.setToolTip("Nur Lesen (AccessLevel 1)")
                else:
                    self.btn_save.setToolTip("")

            if hasattr(self, "btn_upload_series_images") and self.btn_upload_series_images:
                self.btn_upload_series_images.setEnabled(bool(can_write))
                if not can_write:
                    self.btn_upload_series_images.setToolTip("Nur Lesen (AccessLevel 1)")
                else:
                    self.btn_upload_series_images.setToolTip("")

            if hasattr(self, "btn_upload_series_pdfs") and self.btn_upload_series_pdfs:
                self.btn_upload_series_pdfs.setEnabled(bool(can_write))
                if not can_write:
                    self.btn_upload_series_pdfs.setToolTip("Nur Lesen (AccessLevel 1)")
                else:
                    self.btn_upload_series_pdfs.setToolTip("")

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
        except Exception:
            # If anything goes wrong, keep button enabled and let _save_all guard.
            pass

    def showEvent(self, event):
        # Ensure button is enabled/disabled with up-to-date user state.
        try:
            self._sync_save_button_access()
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

    def _open_report(self) -> None:
        """Öffnet den Report-Screen für die aktuelle TrialSeries."""
        if self._series_pk is None:
            return
        if callable(self.on_open_report):
            self.on_open_report(self._series_pk)

    def _back_home(self):
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
        self.on_back_home()

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

    def _stamp_trial_timestamp(self, trial_id: int) -> int:
        """Setzt NOW() in tblTrial.[Timestamp] **und** den aktuellen User in tblTrial.[User] für die angegebene Trial-ID."""
        try:
            # aktuellen User aus app_meta lesen (Key kann 'ID' / 'Id' / 'id' heissen)
            user = getattr(app_meta, "current_user", {}) or {}
            user_id = None
            if isinstance(user, dict):
                for k in ("ID", "Id", "id"):
                    if k in user:
                        user_id = user[k]
                        break

            # Timestamp und User in EINEM Update schreiben
            return execute_non_query(
                "UPDATE tblTrial SET [Timestamp]=NOW(), [User]=? WHERE [ID]=?",
                [user_id, trial_id],
            )
        except Exception:
            # Falls Spalte mal nicht existiert o.ä., fehlerfrei weitermachen
            return 0

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
            QMessageBox.warning(self, 'Fehler', str(e))

    def _save_all(self):
        # Access level 1: read-only
        try:
            lvl = int(getattr(app_meta, "access_level", lambda: 0)() or 0)
        except Exception:
            try:
                user = getattr(app_meta, "current_user", {}) or {}
                lvl = int(user.get("access_level") or user.get("AccessLevel") or 0)
            except Exception:
                lvl = 0
        if lvl <= 1:
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

        # Vor dem Speichern: betroffene Trial-IDs sammeln, falls Tension-Felder geändert wurden
        trial_ids_to_stamp = set()
        try:
            if hasattr(self, "model_machine") and self.model_machine:
                def _n(x: str) -> str:
                    return (x or "").lower().replace(" ", "").replace("_", "").replace("(", "").replace(")",
                                                                                                        "").replace("°",
                                                                                                                    "").replace(
                        "/", "").replace("-", "").strip()

                targets = {
                    _n("Yarn Tension before Jet (cN)"),
                    _n("Yarn Tension after Jet (cN)"),
                    _n("YarnTensionBeforeJet"),
                    _n("YarnTensionAfterJet"),
                }
                for (rr, cc, _newtext) in list(getattr(self.model_machine, "_dirty", [])):
                    try:
                        bind = self.model_machine.get_binding(rr, cc)
                    except Exception:
                        bind = None
                    if bind and getattr(bind, "table", None) == "tblTrial":
                        f_norm = _n(getattr(bind, "field", ""))
                        if f_norm in targets:
                            trial_ids_to_stamp.add(getattr(bind, "id_value", None))
        except Exception:
            trial_ids_to_stamp = set()

        # --- Generic save handling for all registered models ---
        for name, model in self._iter_save_models():
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

        if total == 0:
            models_info = []
            for name, m in self._iter_save_models():
                dirty_count = len(getattr(m, "_dirty", []))
                models_info.append(f"  {name}: {dirty_count} dirty")
            model_count = len(list(self._iter_save_models()))
            names_list = getattr(self, "_save_model_names", [])
            debug_txt = (
                    f"Registered model names ({len(names_list)}): {names_list}\n"
                    f"Models with instance ({model_count}):\n"
                    + ("\n".join(models_info) if models_info else "  (none)")
            )
            QMessageBox.information(
                self, "Saved – 0 changes",
                f"0 change(s) written.\n\n{debug_txt}")
        else:
            QMessageBox.information(self, "Saved", f"{total} change(s) written to database.")
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

        # Baue pro Trial eine Liste von (ply_label, col_index) auf
        from collections import defaultdict
        trial_cols: Dict[int, List[Tuple[str, int]]] = defaultdict(list)
        for c_idx, cs in enumerate(col_specs):
            trial_cols[cs["trial_id"]].append((cs["ply"], c_idx))

        # Anzahl der Daten-Zeilen im Modell
        n_rows = len(getattr(model, "_row_titles", []))
        n_hdr = getattr(model, "_n_hdr", 0)

        found_diff = False
        for tid, ply_cols in trial_cols.items():
            if len(ply_cols) < 2:
                continue  # nur ein Ply -> kein Multi-Ply-Vergleich moeglich
            # Ply 1 ist der erste Eintrag
            _, c_ply1 = ply_cols[0]
            for r_idx in range(n_rows):
                # Nur tblTrialSettings-Bindings sind Ply-spezifisch
                try:
                    bind1 = model.get_binding(r_idx, c_ply1)
                except Exception:
                    bind1 = None
                if not bind1 or getattr(bind1, "table", None) != "tblTrialSettings":
                    continue
                val_ply1 = model._matrix[r_idx][c_ply1] if 0 <= c_ply1 < len(model._matrix[r_idx]) else None
                for _, c_plyx in ply_cols[1:]:
                    val_plyx = model._matrix[r_idx][c_plyx] if 0 <= c_plyx < len(model._matrix[r_idx]) else None

                    # Leere Werte (None/"") gelten als gleich wie None
                    def _norm_val(v):
                        if v is None:
                            return ""
                        return str(v).strip()

                    if _norm_val(val_ply1) != _norm_val(val_plyx):
                        found_diff = True
                        break
                if found_diff:
                    break
            if found_diff:
                break

        if not found_diff:
            return

        user_id = app_meta.current_user.get("id") if app_meta.current_user else None
        if user_id is None:
            return
        _db_execute(
            "INSERT INTO tblFeatureUsage (FeatureID, UserID, ExtraInfo) VALUES (?, ?, ?)",
            [2, user_id, str(getattr(self, "_series_pk", None))],
        )

    # ---------- Daten laden ----------

    def _load_trials(self):
        rows = fetch_all(
            """
            SELECT ID, Versuchsnummer
            FROM tblTrial
            WHERE TrialSeriesID = ?
            ORDER BY Versuchsnummer
            """,
            [self._series_pk],
        )
        self._trials = rows
        self._trial_ids = [r["ID"] for r in rows]
        self._trial_labels = [f"V{r['Versuchsnummer']}" for r in rows]

    def _init_machine_cache(self):
        """Lädt alle statischen DB-Daten für _build_machine_tab einmalig in den Cache."""
        cache = {}

        # MachineID der Series + OriginalJoker (gesetzt wenn Series von Joker-Maschine kam)
        r = fetch_all(
            "SELECT TS.MachineID, TS.OriginalJoker FROM tblTrialSeries AS TS WHERE TS.ID = ?",
            [self._series_pk],
        )
        cache["machine_id"] = r[0]["MachineID"] if r else None
        cache["original_joker_id"] = r[0].get("OriginalJoker") if r else None

        # tblMachineFields (aktuelle Maschine)
        _mf_query = """SELECT FieldNumber, \
                              FieldName, \
                              FieldFunction, \
                              OriginalName,
                              COALESCE(StorageTable, 'tbltrial') AS StorageTable,
                              COALESCE(RDSetting, 0)             AS RDSetting
                       FROM tblMachineFields \
                       WHERE MachineID = ?
                       ORDER BY FieldNumber, FieldName"""
        try:
            cache["machine_fields"] = fetch_all(
                _mf_query, [cache["machine_id"]],
            ) if cache["machine_id"] else []
        except Exception:
            cache["machine_fields"] = []

        # Falls OriginalJoker gesetzt (Series kam von Joker-Maschine): fehlende Felder ergänzen.
        # Die Joker-Maschine hat ein grosses Feldset; die neue Maschine kennt möglicherweise
        # einzelne Felder (z.B. Winder) nicht. Die Werte liegen aber bereits in tblTrial.
        joker_id = cache.get("original_joker_id")
        if joker_id and joker_id != cache["machine_id"]:
            try:
                joker_fields = fetch_all(_mf_query, [joker_id])
                existing_norms = {norm(f.get("FieldName") or "") for f in cache["machine_fields"]}
                for jf in joker_fields:
                    jf_norm = norm(jf.get("FieldName") or "")
                    if jf_norm and jf_norm not in existing_norms:
                        cache["machine_fields"].append(jf)
                        existing_norms.add(jf_norm)
            except Exception:
                pass

        # Spalten-Maps
        cache["trial_cols_map"] = get_columns_map("tblTrial")
        cache["settings_cols_map"] = get_columns_map("tblTrialSettings") if table_exists("tblTrialSettings") else {}

        # tblYarn Map
        cache["yarn_map"] = {}
        if table_exists("tblYarn"):
            for yr in fetch_all("SELECT ID, Name FROM tblYarn"):
                try:
                    cache["yarn_map"][int(yr["ID"])] = str(yr["Name"] or "")
                except Exception:
                    pass

        # tblYarnUse Map
        cache["yarn_use_map"] = {}
        try:
            for r in fetch_all("SELECT ID, Name FROM tblYarnUse ORDER BY ID"):
                cache["yarn_use_map"][int(r["ID"])] = str(r.get("Name") or "")
        except Exception:
            pass

        # Lookup-Maps pro LookupTable (für dropdown_rows)
        cache["lookup_maps"] = {}
        for fdef in cache["machine_fields"]:
            # LookupTable aus FieldFunction extrahieren (dropdown:tblXxx)
            ff = str(fdef.get("FieldFunction") or "").strip()
            lt = None
            if ff.lower().startswith("dropdown:"):
                lt = ff[len("dropdown:"):].strip() or None
            if not lt or lt in cache["lookup_maps"]:
                continue
            lk_map: Dict[Any, str] = {}
            try:
                if table_exists(lt):
                    lk_cmap = get_columns_map(lt)
                    lk_id = resolve_field(["ID"], lk_cmap) or "ID"
                    lk_name = resolve_field(
                        ["DiscName", "Name", "Bezeichnung", "Caption",
                         "HousingName", "Jet", "JetName", "MaterialName",
                         "YarnName", "Description", "Label"],
                        lk_cmap)
                    if lk_name:
                        for lk in fetch_all(
                                f"SELECT `{lk_id}` AS LID, `{lk_name}` AS LName "
                                f"FROM `{lt}` ORDER BY `{lk_name}` ASC"
                        ):
                            lid = lk.get("LID")
                            lname = str(lk.get("LName") or "")
                            if lid is not None:
                                lk_map[lid] = lname
                                lk_map[str(lid)] = lname
                                try:
                                    lk_map[int(lid)] = lname
                                except Exception:
                                    pass
            except Exception:
                pass
            cache["lookup_maps"][lt] = lk_map

        # has_groups: YarnUseIDs vorhanden?
        try:
            if self._trial_ids:
                ph = ",".join(["%s"] * len(self._trial_ids))
                use_rows = fetch_all(
                    f"SELECT COUNT(*) AS cnt FROM tblTrialSettings "
                    f"WHERE TrialID IN ({ph}) AND YarnUseID IS NOT NULL",
                    self._trial_ids,
                )
                cache["has_groups"] = (use_rows[0]["cnt"] > 0) if use_rows else False
            else:
                cache["has_groups"] = False
        except Exception:
            cache["has_groups"] = False

        self._machine_cache = cache

    def _refresh_materials_box(self):
        """Lädt die Materialliste für die aktuelle TrialSeries und zeigt sie an."""
        try:
            txt = self._load_materials_summary()
            if not txt:
                txt = "—"
        except Exception as e:
            txt = f"— (Fehler beim Laden: {e})"
        if hasattr(self, "lbl_material_value"):
            self.lbl_material_value.setText(txt)

    def _refresh_experiment_request_link(self) -> None:
        """Loads linked ExperimentRequest ID from tblExperimente (if any)."""
        self._experiment_request_id = None
        if self._exp_pk in (None, ""):
            return
        try:
            cols = get_columns_map('tblExperimente')
            f_req = resolve_field(
                ['ExperimentRequest', 'Experiment Request', 'ExperimentRequestID', 'ExperimentRequestId'], cols)
            if not f_req:
                return
            rows = fetch_all(f'SELECT [{f_req}] AS ER FROM [tblExperimente] WHERE [ID]=?', [self._exp_pk])
            if rows:
                self._experiment_request_id = rows[0].get('ER')
        except Exception:
            self._experiment_request_id = None

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

    def _series_images_dir(self, series_id: Any) -> str:
        """Gibt den Zielordner fuer Bilder einer TrialSeries zurueck."""
        return os.path.join(TRIALSERIES_IMAGES_BASE_DIR, str(series_id))

    def _series_images_relative_path_for_db(self, series_id: Any) -> str:
        """Gibt den Pfad so zurueck, wie er in RelativePath gespeichert werden soll."""
        return TRIALSERIES_IMAGES_BASE_DIR + "\\" + str(series_id) + "\\"

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
        """Returns dicts with FullPath + display name fields."""
        if series_id in (None, ""):
            return []
        rows: List[Dict[str, str]] = []
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(
                "SELECT [RelativePath], [StoredFilename], [OriginalFilename] "
                "FROM [tblTrialSeriesImage] "
                "WHERE [TrialSeriesID]=? "
                "ORDER BY [ID] DESC",
                [series_id],
            )
            for rel_path, stored, orig_name in cur.fetchall() or []:
                rel_path = str(rel_path or "")
                stored = str(stored or "")
                orig_name = str(orig_name or "")
                full = os.path.join(rel_path, stored) if rel_path else stored
                rows.append(
                    {
                        "RelativePath": rel_path,
                        "StoredFilename": stored,
                        "OriginalFilename": orig_name,
                        "FullPath": full,
                    }
                )
        return rows

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

    def _insert_trialseries_image_row(
            self,
            *,
            series_id: Any,
            relative_path: str,
            stored_filename: str,
            original_filename: str,
    ) -> None:
        """Erzeugt einen Datensatz in tblTrialSeriesImage."""
        created_by = self._current_user_id()
        if created_by in (None, ""):
            raise RuntimeError("CreatedBy/UserID konnte nicht ermittelt werden.")

        sql = (
            "INSERT INTO [tblTrialSeriesImage] "
            "([TrialSeriesID],[RelativePath],[StoredFilename],[OriginalFilename],[CreatedAt],[CreatedBy]) "
            "VALUES (?,?,?,?,?,?)"
        )
        params = [
            series_id,
            relative_path,
            stored_filename,
            original_filename,
            datetime.datetime.now(),
            created_by,
        ]
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(sql, params)
            try:
                cn.commit()
            except Exception:
                pass

    def _upload_series_images(self) -> None:
        """Button-Handler: Bilder waehlen, speichern, DB-Records anlegen."""
        if self._get_access_level() <= 1:
            QMessageBox.information(self, "Upload", "Nur Lesen (AccessLevel 1).")
            return

        sid = self._series_pk
        if sid in (None, ""):
            QMessageBox.warning(self, "Upload", "Keine TrialSeries ausgewaehlt.")
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

            target_dir = self._series_images_dir(sid)
            db_rel_path = self._series_images_relative_path_for_db(sid)

            try:
                os.makedirs(target_dir, exist_ok=True)
            except PermissionError as e:
                raise RuntimeError(
                    "[WinError 5] Zugriff verweigert beim Erstellen des Zielordners. "
                    "Das ist ein Berechtigungsproblem auf dem Share/NTFS.\n\n"
                    f"Pfad: {target_dir}\n\n"
                    "Bitte sicherstellen, dass der Windows-User (oder der Account, unter dem TrippleT laeuft) "
                    f"Schreibrechte auf {TRIALSERIES_IMAGES_BASE_DIR} hat.\n\n"
                    f"Original-Fehler: {e}"
                )
            except Exception as e:
                raise RuntimeError(f"Zielordner konnte nicht erstellt werden: {target_dir}\n{e}")

            stored_any = 0
            errors: List[str] = []

            for src in files:
                try:
                    orig_name = os.path.basename(src)
                    _, ext = os.path.splitext(orig_name)
                    ext = ext or ""

                    stored_name = f"{uuid.uuid4().hex}{ext}"
                    dst = os.path.join(target_dir, stored_name)

                    with open(src, "rb") as fsrc:
                        data = fsrc.read()
                    with open(dst, "wb") as fdst:
                        fdst.write(data)

                    self._insert_trialseries_image_row(
                        series_id=sid,
                        relative_path=db_rel_path,
                        stored_filename=stored_name,
                        original_filename=orig_name,
                    )

                    stored_any += 1
                except Exception as e:
                    errors.append(f"{os.path.basename(src)}: {e}")

            # Feature-Tracking: upload_image (stealth)
            if stored_any >= 1:
                try:
                    user_id = app_meta.current_user.get("id") if app_meta.current_user else None
                    if user_id is not None:
                        _db_execute(
                            "INSERT INTO tblFeatureUsage (FeatureID, UserID, ExtraInfo) VALUES (?, ?, ?)",
                            [4, user_id, str(getattr(self, "_series_pk", None))],
                        )
                except Exception:
                    pass

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

    def _series_pdfs_dir(self, series_id: Any) -> str:
        """Gibt den Zielordner fuer PDFs einer TrialSeries zurueck."""
        return os.path.join(TRIALSERIES_PDFS_BASE_DIR, str(series_id))

    def _series_pdfs_relative_path_for_db(self, series_id: Any) -> str:
        """Gibt den Pfad so zurueck, wie er in RelativePath gespeichert werden soll."""
        return TRIALSERIES_PDFS_BASE_DIR + "\\" + str(series_id) + "\\"

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
        if series_id in (None, ""):
            return []
        rows: List[Dict[str, str]] = []
        with get_connection() as cn:
            cur = cn.cursor()
            # Include ID for robust rename/delete, if present.
            try:
                cur.execute(
                    "SELECT [ID],[RelativePath],[StoredFilename],[OriginalFilename] "
                    "FROM [tblTrialSeriesPDF] "
                    "WHERE [TrialSeriesID]=? "
                    "ORDER BY [ID] DESC",
                    [series_id],
                )
                fetched = cur.fetchall() or []
                for doc_id, rel_path, stored, orig_name in fetched:
                    rel_path = str(rel_path or "")
                    stored = str(stored or "")
                    orig_name = str(orig_name or "")
                    full = os.path.join(rel_path, stored) if rel_path else stored
                    rows.append(
                        {
                            "ID": doc_id,
                            "RelativePath": rel_path,
                            "StoredFilename": stored,
                            "OriginalFilename": orig_name,
                            "FullPath": full,
                        }
                    )
            except Exception:
                # Fallback if table lacks ID column in the select
                cur.execute(
                    "SELECT [RelativePath],[StoredFilename],[OriginalFilename] "
                    "FROM [tblTrialSeriesPDF] "
                    "WHERE [TrialSeriesID]=? "
                    "ORDER BY [OriginalFilename] DESC",
                    [series_id],
                )
                for rel_path, stored, orig_name in cur.fetchall() or []:
                    rel_path = str(rel_path or "")
                    stored = str(stored or "")
                    orig_name = str(orig_name or "")
                    full = os.path.join(rel_path, stored) if rel_path else stored
                    rows.append(
                        {
                            "RelativePath": rel_path,
                            "StoredFilename": stored,
                            "OriginalFilename": orig_name,
                            "FullPath": full,
                        }
                    )
        return rows

    # ---------- Notes ----------

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
            bar = self.tabs.tabBar()
            if has_notes:
                bar.setTabText(idx, "🔴 Notes")
            else:
                bar.setTabText(idx, "Notes")
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
            _db_execute(
                "UPDATE tblTrialSeries SET Notes = ? WHERE ID = ?",
                [current or None, self._series_pk],
            )
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

    def _insert_trialseries_pdf_row(
            self,
            *,
            series_id: Any,
            relative_path: str,
            stored_filename: str,
            original_filename: str,
    ) -> None:
        created_by = self._current_user_id()
        if created_by in (None, ""):
            raise RuntimeError("CreatedBy/UserID konnte nicht ermittelt werden.")

        sql = (
            "INSERT INTO [tblTrialSeriesPDF] "
            "([TrialSeriesID],[RelativePath],[StoredFilename],[OriginalFilename],[CreatedAt],[CreatedBy]) "
            "VALUES (?,?,?,?,?,?)"
        )
        params = [
            series_id,
            relative_path,
            stored_filename,
            original_filename,
            datetime.datetime.now(),
            created_by,
        ]
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(sql, params)
            try:
                cn.commit()
            except Exception:
                pass

    def _upload_series_pdfs(self) -> None:
        if self._get_access_level() <= 1:
            QMessageBox.information(self, "Upload", "Nur Lesen (AccessLevel 1).")
            return

        sid = self._series_pk
        if sid in (None, ""):
            QMessageBox.warning(self, "Upload", "Keine TrialSeries ausgewaehlt.")
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

            target_dir = self._series_pdfs_dir(sid)
            db_rel_path = self._series_pdfs_relative_path_for_db(sid)

            try:
                os.makedirs(target_dir, exist_ok=True)
            except PermissionError as e:
                raise RuntimeError(
                    "[WinError 5] Zugriff verweigert beim Erstellen des Zielordners. "
                    "Das ist ein Berechtigungsproblem auf dem Share/NTFS.\n\n"
                    f"Pfad: {target_dir}\n\n"
                    "Bitte sicherstellen, dass der Windows-User (oder der Account, unter dem TrippleT laeuft) "
                    f"Schreibrechte auf {TRIALSERIES_PDFS_BASE_DIR} hat.\n\n"
                    f"Original-Fehler: {e}"
                )
            except Exception as e:
                raise RuntimeError(f"Zielordner konnte nicht erstellt werden: {target_dir}\n{e}")

            stored_any = 0
            errors: List[str] = []

            for src in files:
                try:
                    orig_name = os.path.basename(src)
                    _, ext = os.path.splitext(orig_name)
                    ext = ext or ".pdf"

                    stored_name = f"{uuid.uuid4().hex}{ext}"
                    dst = os.path.join(target_dir, stored_name)

                    with open(src, "rb") as fsrc:
                        data = fsrc.read()
                    with open(dst, "wb") as fdst:
                        fdst.write(data)

                    self._insert_trialseries_pdf_row(
                        series_id=sid,
                        relative_path=db_rel_path,
                        stored_filename=stored_name,
                        original_filename=orig_name,
                    )

                    stored_any += 1
                except Exception as e:
                    errors.append(f"{os.path.basename(src)}: {e}")

            # Feature-Tracking: upload_pdf (stealth)
            if stored_any >= 1:
                try:
                    user_id = app_meta.current_user.get("id") if app_meta.current_user else None
                    if user_id is not None:
                        _db_execute(
                            "INSERT INTO tblFeatureUsage (FeatureID, UserID, ExtraInfo) VALUES (?, ?, ?)",
                            [3, user_id, str(getattr(self, "_series_pk", None))],
                        )
                except Exception:
                    pass

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
        """
        if not getattr(self, "_series_pk", None):
            return ""

        rows = fetch_all(
            """
            SELECT ts.Ply, y.Name AS YarnName, COUNT(*) AS cnt
            FROM tblTrialSettings ts
                     JOIN tblYarn y ON y.ID = ts.YarnID
                     JOIN tblTrial t ON t.ID = ts.TrialID
            WHERE t.TrialSeriesID = ?
            GROUP BY ts.Ply, y.Name
            ORDER BY ts.Ply, cnt DESC
            """,
            [self._series_pk],
        )

        if not rows:
            return ""

        # Pro Ply nur die erste Zeile (= häufigste YarnName)
        seen_plies = set()
        result = []
        for r in rows:
            ply = (r.get("Ply") or "").strip()
            if ply in seen_plies:
                continue
            seen_plies.add(ply)
            result.append((ply, (r.get("YarnName") or "").strip() or "(ohne Name)"))

        def _ply_sort_key(pair):
            m = re.search(r"\d+", pair[0])
            return int(m.group()) if m else 9999

        result.sort(key=_ply_sort_key)
        return " • ".join(f"{ply}: {name}" for ply, name in result)

    # ---------- Machine Data ----------

    def _build_machine_tab(self):
        # Aktuellen Modus für _on_view_mode_changed merken
        if self._rb_groups.isChecked():
            self._last_view_mode = "groups"
        elif self._rb_compact.isChecked():
            self._last_view_mode = "compact"
        else:
            self._last_view_mode = "single"

        # Radio-Signals einmalig verbinden
        if not getattr(self, "_rb_signals_connected", False):
            self._rb_single.toggled.connect(self._on_view_mode_changed)
            self._rb_groups.toggled.connect(self._on_view_mode_changed)
            self._rb_compact.toggled.connect(self._on_view_mode_changed)
            self._rb_signals_connected = True
        cache = getattr(self, "_machine_cache", None) or {}
        if not cache:
            self._init_machine_cache()
            cache = getattr(self, "_machine_cache", None) or {}
        machine_id = cache.get("machine_id")
        use_yarn_use_grouping = getattr(self._rb_groups, "isChecked", lambda: False)()

        if not table_exists("tblMachineFields"):
            self.machine_info.setText(
                "Mapping-Tabelle 'tblMachineFields' nicht gefunden.")
            self.tbl_machine.setModel(PivotEditModel([], self._trial_labels))
            return

        fields = cache.get("machine_fields", [])
        if not fields and machine_id:
            try:
                fields = fetch_all(
                    """SELECT FieldNumber,
                              FieldName,
                              FieldFunction,
                              OriginalName,
                              COALESCE(StorageTable, 'tbltrial') AS StorageTable,
                              COALESCE(RDSetting, 0)             AS RDSetting
                       FROM tblMachineFields
                       WHERE MachineID = ?
                       ORDER BY FieldNumber, FieldName""",
                    [machine_id],
                )
            except Exception as e:
                self.machine_info.setText(f"Fehler beim Laden von tblMachineFields: {e}")
                self.tbl_machine.setModel(PivotEditModel([], self._trial_labels))
                return

        # Felder aufteilen: RDSetting=0 -> Machine Data, RDSetting=1 -> R&D Machine Data
        fields_normal = [f for f in fields if int(f.get("RDSetting") or 0) == 0]
        fields_rd = [f for f in fields if int(f.get("RDSetting") or 0) == 1]

        # Trial-Spalten (für exakte Groß/Kleinschreibung)
        trial_cols = cache.get("trial_cols_map") or get_columns_map("tblTrial")

        # Fixe Titel
        FIX_HOUSING = "Housing"
        FIX_JET = "Jet"
        FIX_PLATE = "Jet Plate Number"
        FIX_AIR = "Air Pressure (bar)"
        titles_fixed = [FIX_HOUSING, FIX_JET, FIX_PLATE, FIX_AIR]

        reserved_titles = [
            "Versuchsnummer", "Housing",
            "Jet", "Jet Name",
            "JetPlate", "Jet Plate Number",
            "Air Pressure (bar)",
            "Yarn Use", "YarnUse", "YarnUseID",
        ]
        reserved_norm = {norm(x) for x in reserved_titles}

        # Für die fixen Felder: Validator + OriginalName (DB-Spalte in tblTrial)
        reserved_validators: Dict[str, Optional[str]] = {
            FIX_PLATE: None, FIX_AIR: None}
        reserved_originals: Dict[str, Optional[str]] = {
            FIX_PLATE: None, FIX_AIR: None}
        reserved_norm.add(norm(FIX_HOUSING))

        seen_norm_titles: set[str] = set()

        # Mapping für alle restlichen Felder (Anzeige = FieldName, Binding = OriginalName)
        # {"Title": FieldName, "ColName": tblTrial-Column}
        field_map: List[Dict[str, Optional[str]]] = []
        field_validators: List[Optional[str]] = []

        for f in fields_normal:
            disp = str(f.get("FieldName") or "").strip()
            orig = str(f.get("OriginalName") or "").strip()
            ff = canon_rule((f.get("FieldFunction") or "").strip() or None)
            if not disp:
                continue

            # hidden-Felder komplett überspringen
            if ff == "hidden":
                continue

            disp_norm = norm(disp)

            if disp_norm in reserved_norm:
                # den passenden fixen Eintrag mit Validator + OriginalName versorgen
                if disp_norm in {norm(FIX_PLATE), norm("JetPlateNumber"), norm("JetPlate")}:
                    reserved_validators[FIX_PLATE] = ff
                    reserved_originals[FIX_PLATE] = orig or reserved_originals[FIX_PLATE]
                elif disp_norm in {norm(FIX_AIR), norm("AirPressure")}:
                    reserved_validators[FIX_AIR] = ff
                    reserved_originals[FIX_AIR] = orig or reserved_originals[FIX_AIR]
                continue

            if disp_norm in seen_norm_titles:
                continue

            # OriginalName -> echte Spalten-Schreibweise in tblTrial nachschlagen
            col = None
            if orig:
                col = trial_cols.get(orig.lower()) or resolve_field(
                    [orig], trial_cols)
            # Falls OriginalName leer ist, letzte Rettung: anhand Display probieren
            if not col and disp:
                col = trial_cols.get(disp.lower()) or resolve_field(
                    [disp], trial_cols)

            # LookupTable für dropdown:tblXxx extrahieren
            lookup_table = None
            if ff and ff.lower().startswith("dropdown:"):
                lookup_table = ff[len("dropdown:"):].strip() or None

            field_map.append({
                "Title": disp,
                "ColName": col or orig or disp,
                "StorageTable": str(f.get("StorageTable") or "tbltrial").strip().lower(),
                "LookupTable": lookup_table,
            })
            field_validators.append(ff)
            seen_norm_titles.add(disp_norm)

        # Modell + Validatoren
        FIX_PLIES = "Plies"
        FIX_YARN_USE = "Yarn Use"
        FIX_SPOOL = "Spool"
        compact_mode = self._rb_compact.isChecked()
        if use_yarn_use_grouping:
            titles_fixed = [FIX_HOUSING, FIX_JET, FIX_PLATE, FIX_AIR, FIX_PLIES]
        elif compact_mode:
            titles_fixed = [FIX_HOUSING, FIX_JET, FIX_PLATE, FIX_AIR, FIX_PLIES]
        else:
            titles_fixed = [FIX_HOUSING, FIX_JET, FIX_PLATE, FIX_AIR, FIX_YARN_USE, FIX_SPOOL]
        # Von der Fill-Range-Logik (Kontextmenue) genutzt, um zu erkennen ob ein
        # Feld zu tblTrialSettings (Ply-spezifisch) gehoert. Ersetzt eine frueher
        # hartcodierte Konstante (=5), die durch die neue Spool-Zeile im
        # Single-Plies-Modus (jetzt 6 Fixzeilen) sonst falsch waere.
        self._machine_titles_fixed_count = len(titles_fixed)
        row_titles = titles_fixed + [f["Title"] for f in field_map]
        # CustomGroup immer am Ende anhängen (Sichtbarkeit via hideRow gesteuert)
        row_titles = row_titles + ["Custom Group"]
        readonly_rows = set()
        if use_yarn_use_grouping or compact_mode:
            readonly_rows.add(titles_fixed.index(FIX_PLIES))  # Plies-Zeile immer read-only

        row_validators: List[Optional[str]] = [None] * len(row_titles)
        row_validators[0] = None  # Housing
        row_validators[1] = None  # Jet
        row_validators[2] = reserved_validators.get(FIX_PLATE)
        row_validators[3] = reserved_validators.get(FIX_AIR)
        for i, ff in enumerate(field_validators, start=len(titles_fixed)):
            row_validators[i] = ff
        # CustomGroup: zuletzt, kein Validator
        self._custom_group_row_idx = len(row_titles) - 1  # Modell-Zeilenindex (0-basiert, ohne Header-Zeilen)

        # model_machine wird weiter unten (nach col_specs-Aufbau) instanziert,
        # damit expanded_col_titles (Ply-Unterspalten) bekannt sind.

        # dropdown_rows aufbauen: {row_index_0based → {id → name}}
        # row_index = Position in row_titles (titles_fixed hat 5 Einträge: 0-4)
        dropdown_rows: Dict[int, Dict[Any, str]] = {}

        # YarnUse Dropdown (Single Plies Modus, Zeile 4) — aus Cache
        if not use_yarn_use_grouping and not compact_mode:
            yarn_use_row_idx = titles_fixed.index(FIX_YARN_USE)
            yu_map: Dict[Any, str] = {"": "—", None: "—", 0: "—", "0": "—"}
            for uid, uname in cache.get("yarn_use_map", {}).items():
                yu_map[uid] = uname
                yu_map[str(uid)] = uname  # String-Key für _id_display
            dropdown_rows[yarn_use_row_idx] = yu_map

            # Spool Dropdown (Zeile 5) - alle am Lager befindlichen Spulen der
            # Garne, die in dieser Series tatsaechlich als Material vorkommen.
            # Series-weite Liste statt strikt pro Zelle gefiltert (eine Zeile
            # gilt fuer die ganze Tabelle) - dafuer profitiert man von der
            # bestehenden Fill-Range-Mechanik fuer Dropdown-Zeilen (z.B. um
            # dieselbe Spule auf viele Trials gleichzeitig zu setzen).
            spool_row_idx = titles_fixed.index(FIX_SPOOL)
            sp_map: Dict[Any, str] = {"": "—", None: "—", 0: "—", "0": "—"}
            # Volle Infos (Garn/Batch/Gewicht/Ort) landen NICHT in sp_map (das
            # waere die Zellen-/Dropdown-Anzeige und macht die Spalte zu breit),
            # sondern separat in self._spool_tooltip_map fuer den Tooltip.
            self._spool_tooltip_map: Dict[int, str] = {}
            if table_exists("tblYarnSpool"):
                try:
                    series_yarn_ids = sorted({
                        int(r["YarnID"]) for r in fetch_all(
                            "SELECT DISTINCT ts.YarnID FROM tblTrialSettings ts "
                            "JOIN tblTrial t ON t.ID = ts.TrialID "
                            "WHERE t.TrialSeriesID = ? AND ts.YarnID IS NOT NULL",
                            [self._series_pk])
                    })
                except Exception:
                    series_yarn_ids = []
                if series_yarn_ids:
                    ph = ",".join(["?"] * len(series_yarn_ids))
                    yname_map = cache.get("yarn_map") or {}
                    if not yname_map and table_exists("tblYarn"):
                        for yr in fetch_all("SELECT ID, Name FROM tblYarn"):
                            try:
                                yname_map[int(yr["ID"])] = str(yr.get("Name") or "")
                            except Exception:
                                pass
                    spool_rows = fetch_all(
                        f"SELECT ID, YarnID, Charge, WeightKg, Location FROM tblYarnSpool "
                        f"WHERE YarnID IN ({ph}) AND Status = 'in stock' AND WeightKg > 0 "
                        f"ORDER BY YarnID, Charge",
                        series_yarn_ids,
                    )
                    for sr2 in spool_rows:
                        yname = yname_map.get(int(sr2["YarnID"]), "") if sr2.get("YarnID") is not None else ""
                        short_label = f"#{sr2['ID']}"
                        full_label = f"#{sr2['ID']} {yname} — {sr2.get('Charge') or '–'} — {sr2.get('WeightKg'):.1f}kg — {sr2.get('Location') or '–'}"
                        sp_map[sr2["ID"]] = short_label
                        sp_map[str(sr2["ID"])] = short_label
                        self._spool_tooltip_map[int(sr2["ID"])] = full_label
            dropdown_rows[spool_row_idx] = sp_map

        # Lookup-Maps aus Cache
        lookup_maps_cache = cache.get("lookup_maps", {})
        for i, fdef in enumerate(field_map):
            lt = fdef.get("LookupTable")
            if not lt:
                continue
            row_idx = len(titles_fixed) + i
            lk_map = lookup_maps_cache.get(lt)
            if lk_map:
                dropdown_rows[row_idx] = lk_map

        if not self._trial_ids:
            self.model_machine = MachinePivotModel(
                jets_map=self._jets_map,
                row_titles=row_titles,
                col_titles=self._trial_labels,
                read_only_rows=readonly_rows,
                row_validators=row_validators,
                jet_row_index=1,
                housing_map=self._housing_map,
                housing_row_index=0,
                jets_tooltip_map=self._jets_tooltip_map,
                housing_image_map=getattr(self, "_housing_image_map", {}),
                dropdown_rows=dropdown_rows,
            )
            self._register_save_model("model_machine")
            self.tbl_machine.setModel(self.model_machine)
            # R&D Tab ebenfalls ausblenden
            if self.tab_rd_machine is not None:
                idx = self.tabs.indexOf(self.tab_rd_machine)
                if idx != -1:
                    self.tabs.removeTab(idx)
            return

        # Jet-Name finden (tblDTYJets bevorzugt)
        def _find_jet_table_and_text_col() -> tuple[Optional[str], Optional[str]]:
            candidates_tables = ["tblDTYJets", "tblJets",
                                 "tblJet", "tblDuesen", "tblDuese", "Jets"]
            preferred_names = ["name", "jetname", "bezeichnung", "title",
                               "jet", "nozzle", "code", "typ", "type", "modell", "model",
                               "series", "designation", "description"]
            for tname in candidates_tables:
                if not table_exists(tname):
                    continue
                infos = get_columns_info(tname)
                by_lower = {inf["lower"]: inf for inf in infos}
                for cand in preferred_names:
                    if cand in by_lower:
                        return tname, by_lower[cand]["real"]
                for inf in infos:
                    dt = inf["data_type"]
                    tn = (inf["type_name"] or "").upper()
                    is_text = (
                                      dt in (1, 12, -1)) or any(x in tn for x in ["CHAR", "TEXT", "MEMO"])
                    if is_text and ("id" not in inf["lower"]):
                        return tname, inf["real"]
                return tname, None
            return None, None

        jet_table, jet_text_col = _find_jet_table_and_text_col()

        if jet_table and jet_text_col:
            trial_rows = fetch_all(
                f"""
                SELECT T.*, J.[{jet_text_col}] AS JetName
                FROM tblTrial AS T
                LEFT JOIN {jet_table} AS J ON T.JetID = J.ID
                WHERE T.ID IN ({",".join(["?"] * len(self._trial_ids))})
                ORDER BY T.Versuchsnummer
                """,
                self._trial_ids,
            )
        else:
            trial_rows = fetch_all(
                f"""
                SELECT *
                FROM tblTrial
                WHERE ID IN ({",".join(["?"] * len(self._trial_ids))})
                ORDER BY Versuchsnummer
                """,
                self._trial_ids,
            )
            trial_cols_map = cache.get("trial_cols_map") or get_columns_map("tblTrial")
            jet_text_field = resolve_field(
                ["Jet", "Jet Name", "Nozzle", "Nozzle"], trial_cols_map)
            for row in trial_rows:
                row["JetName"] = row.get(
                    jet_text_field) if jet_text_field else None

        # Fixe Felder – Binding über OriginalName, wenn vorhanden
        trial_cols_map = cache.get("trial_cols_map") or get_columns_map("tblTrial")

        # ── col_specs immer aus tblTrialSettings aufbauen ─────────────────
        # (auch wenn keine Settings-Felder in field_map sind – für Konsistenz)
        col_specs: List[Dict] = []  # {"trial": ..., "sr": ..., "ply": str, "trial_id": int}
        settings_cols_map: Dict[str, str] = cache.get("settings_cols_map") or {}

        if table_exists("tblTrialSettings"):
            if not settings_cols_map:
                settings_cols_map = get_columns_map("tblTrialSettings")

            # Settings-Zeilen laden (muss immer frisch sein)
            s_rows = fetch_all(
                f"""
                SELECT * FROM tblTrialSettings
                WHERE TrialID IN ({",".join(["?"] * len(self._trial_ids))})
                ORDER BY TrialID, ID
                """,
                self._trial_ids,
            )

            def _ply_num(sr) -> int:
                ply = (sr.get("Ply") or "").strip()
                m = re.search(r"\d+", ply)
                return int(m.group()) if m else 9999

            settings_by_trial: Dict[int, List[Dict]] = {}
            for sr in s_rows:
                settings_by_trial.setdefault(int(sr["TrialID"]), []).append(sr)
            # Innerhalb jedes Trials nach Ply-Nummer sortieren
            for _tid in settings_by_trial:
                settings_by_trial[_tid].sort(key=_ply_num)

            # Build YarnID → Name lookup for tooltips — aus Cache
            _ymap: Dict[int, str] = cache.get("yarn_map") or {}
            if not _ymap and table_exists("tblYarn"):
                for _yr in fetch_all("SELECT ID, Name FROM tblYarn"):
                    try:
                        _ymap[int(_yr["ID"])] = str(_yr["Name"] or "")
                    except Exception:
                        pass

            trial_row_by_id = {int(t["ID"]): t for t in trial_rows}
            for trial in self._trials:
                tid = int(trial["ID"])
                srows = settings_by_trial.get(tid, [])
                if not srows:
                    col_specs.append({
                        "trial": trial_row_by_id.get(tid, {}),
                        "sr": None,
                        "ply": "",
                        "yarn_name": "",
                        "trial_id": tid,
                        "vno": int(trial["Versuchsnummer"]),
                    })
                else:
                    for idx_sr, sr in enumerate(srows):
                        ply = sr.get("Ply") or f"Ply {idx_sr + 1}"
                        try:
                            _yid = int(sr.get("YarnID") or 0)
                        except Exception:
                            _yid = 0
                        col_specs.append({
                            "trial": trial_row_by_id.get(tid, {}),
                            "sr": sr,
                            "ply": ply,
                            "yarn_name": _ymap.get(_yid, ""),
                            "trial_id": tid,
                            "vno": int(trial["Versuchsnummer"]),
                        })
        else:
            trial_row_by_id = {int(t["ID"]): t for t in trial_rows}
            for trial in self._trials:
                col_specs.append({
                    "trial": trial_row_by_id.get(int(trial["ID"]), {}),
                    "sr": None,
                    "ply": "",
                    "trial_id": int(trial["ID"]),
                    "vno": int(trial["Versuchsnummer"]),
                })

        # ── YarnUse-Gruppierung für MachineID = 4 ─────────────────────────
        # Statt pro Ply eine Spalte → pro Trial eine Spalte pro YarnUse-Gruppe.
        # col_specs wird zu group_col_specs umgebaut.
        if use_yarn_use_grouping and col_specs:
            # tblYarnUse laden
            yarn_use_map: Dict[int, str] = cache.get("yarn_use_map") or {}
            if not yarn_use_map:
                try:
                    for r in fetch_all("SELECT ID, Name FROM tblYarnUse ORDER BY ID"):
                        yarn_use_map[int(r["ID"])] = str(r.get("Name") or f"Group {r['ID']}")
                except Exception:
                    pass

            # YarnUseID pro Settings-Row ermitteln
            # tblTrialSettings.YarnUseID laden für alle relevanten Settings-IDs
            settings_ids_all = [
                int(cs["sr"]["ID"]) for cs in col_specs if cs.get("sr")
            ]
            use_id_by_settings: Dict[int, Optional[int]] = {}
            if settings_ids_all:
                ph = ",".join(["%s"] * len(settings_ids_all))
                try:
                    for r in fetch_all(
                            f"SELECT ID, YarnUseID FROM tblTrialSettings WHERE ID IN ({ph})",
                            settings_ids_all
                    ):
                        use_id_by_settings[int(r["ID"])] = (
                            int(r["YarnUseID"]) if r.get("YarnUseID") else None
                        )
                except Exception:
                    pass

            # col_specs pro Trial nach YarnUseID gruppieren
            # Reihenfolge der Gruppen: wie sie in yarn_use_map vorkommen + None zuletzt
            from collections import OrderedDict
            group_col_specs: List[Dict] = []
            # Trials in Reihenfolge
            seen_tids: List[int] = []
            trial_cs_map: Dict[int, List[Dict]] = {}
            for cs in col_specs:
                tid = cs["trial_id"]
                if tid not in trial_cs_map:
                    seen_tids.append(tid)
                    trial_cs_map[tid] = []
                trial_cs_map[tid].append(cs)

            for tid in seen_tids:
                tcs = trial_cs_map[tid]
                # Gruppen für diesen Trial aufbauen
                groups: Dict[Optional[int], List[Dict]] = OrderedDict()
                for cs in tcs:
                    sr = cs.get("sr")
                    uid = use_id_by_settings.get(int(sr["ID"])) if sr else None
                    groups.setdefault(uid, []).append(cs)

                for uid, members in groups.items():
                    use_name = yarn_use_map.get(uid, "—") if uid else "—"
                    # Ply-Nummern extrahieren
                    ply_nums = []
                    for m in members:
                        ply_str = (m.get("ply") or "").strip()
                        match = re.search(r"\d+", ply_str)
                        if match:
                            ply_nums.append(match.group())
                    ply_label_short = ", ".join(ply_nums) if ply_nums else "—"

                    group_col_specs.append({
                        "trial": members[0]["trial"],
                        "sr": members[0]["sr"],  # erster Ply als Referenz
                        "sr_all": [m["sr"] for m in members if m.get("sr")],
                        "ply": use_name,  # Spalten-Header = YarnUse-Name
                        "ply_label_short": ply_label_short,  # "1, 2" für Plies-Zeile
                        "yarn_name": members[0].get("yarn_name", ""),
                        "trial_id": tid,
                        "vno": members[0]["vno"],
                        "yarn_use_id": uid,
                        "yarn_use_name": use_name,
                        "is_group": True,
                    })

            col_specs = group_col_specs

        # ── header_rows für Modell aufbauen ───────────────────────────────
        # Zeile 0: Trial-Gruppen  ("", "V1","V1","V2","V2",...)
        # Zeile 1: Ply-Labels     ("", "Ply 1","Ply 2","Ply 1","Ply 2",...)
        # Spalte 0 in beiden Zeilen = leere Titelspalte
        compact_mode = self._rb_compact.isChecked()

        # Pro Trial: alle col_specs sammeln für Kompakt-Tooltip
        trial_cs_for_hdr: Dict[int, List[Dict]] = {}
        for cs in col_specs:
            trial_cs_for_hdr.setdefault(cs["trial_id"], []).append(cs)

        trial_hdr_vals = [""]
        ply_hdr_vals = [""]
        ply_tooltip_vals = [""]
        for cs in col_specs:
            trial_hdr_vals.append(f"V{cs['vno']}")
            if compact_mode:
                # Kompakt: alle Plies des Trials zusammenfassen
                all_cs = trial_cs_for_hdr.get(cs["trial_id"], [cs])
                if len(all_cs) == 1:
                    # Nur 1 Ply → "Ply 1"
                    ply_hdr_vals.append(cs["ply"])
                else:
                    # Mehrere Plies → "div."
                    ply_hdr_vals.append("div.")
                # Tooltip: alle Garnamen der Plies
                tooltip_lines = []
                for other_cs in all_cs:
                    ply_lbl = other_cs.get("ply") or ""
                    yname = other_cs.get("yarn_name") or ""
                    if ply_lbl or yname:
                        tooltip_lines.append(f"{ply_lbl}: {yname}" if yname else ply_lbl)
                ply_tooltip_vals.append("\n".join(tooltip_lines) if tooltip_lines else "")
            else:
                ply_hdr_vals.append(cs["ply"])
                ply_tooltip_vals.append(cs.get("yarn_name") or "")

        hdr_rows = [
            {"values": trial_hdr_vals, "bg": None, "fg": None},
            {"values": ply_hdr_vals, "bg": None, "fg": None, "tooltips": ply_tooltip_vals},
        ]
        # Zeile 0 = V-Nummern (gespannt), Zeile 1 = Ply-Labels (einzeln) – nur fett, kein Sonderfarbe

        # Spalten-Titel leer – Ply-Labels stehen bereits in header_rows[1]
        expanded_col_titles = ["" for _ in col_specs]

        # ── Modell instanzieren ───────────────────────────────────────────
        self.model_machine = MachinePivotModel(
            jets_map=self._jets_map,
            row_titles=row_titles,
            col_titles=expanded_col_titles,
            read_only_rows=readonly_rows,
            row_validators=row_validators,
            jet_row_index=1,
            header_rows=hdr_rows,
            housing_map=self._housing_map,
            housing_row_index=0,
            jets_tooltip_map=self._jets_tooltip_map,
            housing_image_map=getattr(self, "_housing_image_map", {}),
            dropdown_rows=dropdown_rows,
        )
        self._register_save_model("model_machine")
        self._machine_col_specs = col_specs  # for multi-ply feature tracking

        def _pick_row_key(row: dict, preferred: Optional[str], extra_cands: List[str]) -> Optional[str]:
            if not row:
                return None
            if preferred and preferred in row:
                return preferred
            if preferred:
                pl = preferred.lower()
                for k in row.keys():
                    if str(k).lower() == pl:
                        return k
            wanted = []
            if preferred:
                wanted.append(preferred)
            wanted.extend(extra_cands or [])
            wanted_norm = {norm(w) for w in wanted if w}
            for k in row.keys():
                if norm(str(k)) in wanted_norm:
                    return k
            return None

        trial_cols_map = cache.get("trial_cols_map") or get_columns_map("tblTrial")

        jet_plate_col = None
        jet_plate_col = trial_cols_map.get("jetplate") or trial_cols_map.get("jet_plate")
        if not jet_plate_col and reserved_originals.get(FIX_PLATE):
            jet_plate_col = trial_cols_map.get(reserved_originals[FIX_PLATE].lower()) \
                            or resolve_field([reserved_originals[FIX_PLATE]], trial_cols_map)
        if not jet_plate_col:
            jet_plate_col = resolve_field(
                ["Jet Plate", "JetPlate", "Jet_Plate", "JetPlateNumber", "Jet Plate Number"], trial_cols_map)

        air_press_col = None
        air_press_col = trial_cols_map.get("airpressure") or trial_cols_map.get("air_pressure")
        if not air_press_col and reserved_originals.get(FIX_AIR):
            air_press_col = trial_cols_map.get(reserved_originals[FIX_AIR].lower()) \
                            or resolve_field([reserved_originals[FIX_AIR]], trial_cols_map)
        if not air_press_col:
            air_press_col = resolve_field(
                ["Air Pressure (bar)", "AirPressure(bar)",
                 "AirPressure", "Air_Pressure_bar", "Air Pressure"],
                trial_cols_map)

        # Resolve HousingID column
        housing_id_col = resolve_field(["HousingID"], trial_cols_map)

        # ── Zellen befüllen ───────────────────────────────────────────────
        # 0: Housing (tblTrial – trial-weit)
        for c_idx, cs in enumerate(col_specs):
            trow = cs["trial"]
            housing_id = trow.get("HousingID") if housing_id_col else None
            self.model_machine.set_cell(
                0, c_idx, housing_id,
                CellBinding("tblTrial", "ID", trow.get("ID"), "HousingID") if (
                            housing_id_col and trow.get("ID")) else None,
            )

        # 1: Jet (tblTrial – trial-weit)
        for c_idx, cs in enumerate(col_specs):
            trow = cs["trial"]
            jet_id = trow.get("JetID")
            self.model_machine.set_cell(
                1, c_idx, jet_id,
                CellBinding("tblTrial", "ID", trow.get("ID"), "JetID") if trow.get("ID") else None,
            )

        # 2: Jet Plate Number (tblTrial – trial-weit)
        for c_idx, cs in enumerate(col_specs):
            trow = cs["trial"]
            jp_key = _pick_row_key(trow, jet_plate_col,
                                   ["JetPlate", "jetplate", "Jet_Plate", "jet_plate",
                                    "Jet Plate", "Jet Plate Number", "JetPlateNumber"])
            jp_field = jet_plate_col or jp_key
            self.model_machine.set_cell(
                2, c_idx,
                trow.get(jp_key) if jp_key else None,
                CellBinding("tblTrial", "ID", trow.get("ID"), jp_field) if (jp_field and trow.get("ID")) else None,
            )

        # 3: Air Pressure (tblTrial – trial-weit)
        for c_idx, cs in enumerate(col_specs):
            trow = cs["trial"]
            ap_key = _pick_row_key(trow, air_press_col,
                                   ["AirPressure", "airpressure", "Air_Pressure", "air_pressure",
                                    "Air Pressure", "Air Pressure (bar)", "AirPressure(bar)", "Air_Pressure_bar"])
            ap_field = air_press_col or ap_key
            self.model_machine.set_cell(
                3, c_idx,
                trow.get(ap_key) if ap_key else None,
                CellBinding("tblTrial", "ID", trow.get("ID"), ap_field) if (ap_field and trow.get("ID")) else None,
            )

        # Plies-Zeile (Groups-Modus oder Kompakt-Modus)
        if use_yarn_use_grouping:
            plies_row_idx = titles_fixed.index(FIX_PLIES)
            for c_idx, cs in enumerate(col_specs):
                self.model_machine.set_cell(
                    plies_row_idx, c_idx,
                    cs.get("ply_label_short", ""),
                    None,
                )
                # Tooltip: Garnname pro Ply
                sr_all = cs.get("sr_all") or []
                if sr_all:
                    tooltip_lines = []
                    for sr in sr_all:
                        ply = sr.get("Ply") or ""
                        yid = None
                        try:
                            yid = int(sr.get("YarnID") or 0) or None
                        except Exception:
                            pass
                        yname = _ymap.get(yid, "") if yid else ""
                        if ply or yname:
                            tooltip_lines.append(f"{ply}: {yname}" if yname else ply)
                    if tooltip_lines:
                        self.model_machine._cell_tooltips[(plies_row_idx, c_idx)] = "\n".join(tooltip_lines)

        elif compact_mode:
            # Kompakt: pro Trial alle Plies zusammenfassen
            plies_row_idx = titles_fixed.index(FIX_PLIES)
            # Alle col_specs pro Trial sammeln
            trial_all_cs: Dict[int, List[Dict]] = {}
            for cs in col_specs:
                trial_all_cs.setdefault(cs["trial_id"], []).append(cs)

            for c_idx, cs in enumerate(col_specs):
                all_cs = trial_all_cs.get(cs["trial_id"], [cs])
                # Ply-Nummern kurz
                ply_nums = []
                for other_cs in all_cs:
                    sr = other_cs.get("sr")
                    ply_str = (other_cs.get("ply") or "").strip()
                    import re as _re
                    m = _re.search(r"\d+", ply_str)
                    if m:
                        ply_nums.append(m.group())
                short = ", ".join(ply_nums) if ply_nums else "—"
                self.model_machine.set_cell(plies_row_idx, c_idx, short, None)
                # Tooltip: Garnname pro Ply
                tooltip_lines = []
                for other_cs in all_cs:
                    ply_lbl = other_cs.get("ply") or ""
                    yid = None
                    sr = other_cs.get("sr")
                    if sr:
                        try:
                            yid = int(sr.get("YarnID") or 0) or None
                        except Exception:
                            pass
                    yname = _ymap.get(yid, "") if yid else ""
                    if ply_lbl or yname:
                        tooltip_lines.append(f"{ply_lbl}: {yname}" if yname else ply_lbl)
                if tooltip_lines:
                    self.model_machine._cell_tooltips[(plies_row_idx, c_idx)] = "\n".join(tooltip_lines)

        # YarnUse-Zeile (nur Single Plies Modus)
        if not use_yarn_use_grouping and not compact_mode:
            yarn_use_row_idx = titles_fixed.index(FIX_YARN_USE)
            for c_idx, cs in enumerate(col_specs):
                sr = cs.get("sr")
                yuid = None
                if sr:
                    try:
                        yuid = int(sr.get("YarnUseID") or 0) or None
                    except Exception:
                        yuid = None
                self.model_machine.set_cell(
                    yarn_use_row_idx, c_idx, yuid,
                    CellBinding("tblTrialSettings", "ID", sr["ID"], "YarnUseID") if sr else None,
                )

            # Spool-Zeile: physische Duese-Zuordnung pro Ply/Trial
            spool_row_idx = titles_fixed.index(FIX_SPOOL)
            spool_tooltips = getattr(self, "_spool_tooltip_map", {})
            for c_idx, cs in enumerate(col_specs):
                sr = cs.get("sr")
                spool_id = None
                if sr:
                    try:
                        spool_id = int(sr.get("SpoolID") or 0) or None
                    except Exception:
                        spool_id = None
                self.model_machine.set_cell(
                    spool_row_idx, c_idx, spool_id,
                    CellBinding("tblTrialSettings", "ID", sr["ID"], "SpoolID") if sr else None,
                )
                if spool_id is not None and spool_id in spool_tooltips:
                    self.model_machine._cell_tooltips[(spool_row_idx, c_idx)] = spool_tooltips[spool_id]

        # weitere Maschinenfelder
        start_row = len(titles_fixed)
        for offset, fdef in enumerate(field_map):
            r_idx = start_row + offset
            storage = fdef.get("StorageTable", "tbltrial")
            colname = fdef["ColName"]

            if storage == "tbltrialsettings" and settings_cols_map:
                real_col = settings_cols_map.get(colname.lower()) or colname
                for c_idx, cs in enumerate(col_specs):
                    sr = cs["sr"]
                    if use_yarn_use_grouping and cs.get("is_group"):
                        # Gruppe: alle Werte prüfen, ersten nehmen, orange wenn inkonsistent
                        sr_all = cs.get("sr_all") or ([sr] if sr else [])
                        vals = [
                            s.get(real_col) for s in sr_all
                            if s and s.get(real_col) is not None
                        ]
                        val = vals[0] if vals else None
                        inconsistent = len(set(str(v) for v in vals)) > 1 if vals else False
                        settings_ids = [int(s["ID"]) for s in sr_all if s]
                        binding = GroupCellBinding(
                            "tblTrialSettings", "ID", settings_ids, real_col
                        ) if settings_ids else None
                        self.model_machine.set_cell(r_idx, c_idx, val, binding)
                        if inconsistent:
                            self.model_machine._cell_alerts[(r_idx, c_idx)] = "orange"
                    else:
                        val = sr.get(real_col) if sr else None
                        binding = CellBinding(
                            "tblTrialSettings", "ID", sr["ID"], real_col
                        ) if sr else None
                        self.model_machine.set_cell(r_idx, c_idx, val, binding)
            else:
                real_col = trial_cols_map.get(str(colname).lower()) or colname
                for c_idx, cs in enumerate(col_specs):
                    trow = cs["trial"]
                    val = trow.get(real_col)
                    self.model_machine.set_cell(
                        r_idx, c_idx, val,
                        CellBinding("tblTrial", "ID", trow.get("ID"), real_col) if trow.get("ID") else None,
                    )

        # CustomGroup-Zeile befüllen (direkt aus tblTrial.CustomGroup)
        _cg_col = trial_cols_map.get('customgroup') or trial_cols_map.get('custom_group') or 'CustomGroup'
        for c_idx, cs in enumerate(col_specs):
            trow = cs['trial']
            val = trow.get(_cg_col)
            self.model_machine.set_cell(
                self._custom_group_row_idx, c_idx, val,
                CellBinding('tblTrial', 'ID', trow.get('ID'), _cg_col) if trow.get('ID') else None,
            )

        self.tbl_machine.setModel(self.model_machine)
        self.tbl_machine.resizeColumnsToContents()

        # Qt-Column-Header ausblenden – Ply/V-Labels stehen bereits in den Modell-Header-Zeilen
        self.tbl_machine.left.horizontalHeader().setVisible(False)
        self.tbl_machine.right.horizontalHeader().setVisible(False)

        # CustomGroup-Zeile: n_hdr Header-Zeilen + Modell-Zeilenindex
        _cg_view_row = getattr(self.model_machine, '_n_hdr', 2) + self._custom_group_row_idx
        self.tbl_machine.left.setRowHidden(_cg_view_row, not self._custom_group_visible)
        self.tbl_machine.right.setRowHidden(_cg_view_row, not self._custom_group_visible)

        # ── setSpan für trial-weite Spalten ───────────────────────────────
        # col_specs enthält N Einträge pro Trial (eine pro Ply).
        # Für tblTrial-Felder und Header-Zeile 0 (V-Nummer) soll jede
        # Trial-Gruppe über alle ihre Ply-Spalten gespannt werden.
        #
        # Gruppen berechnen: [(model_col_start, span), ...]
        # model_col = 1-basiert (Spalte 0 = Zeilentitel)
        trial_groups: List[Tuple[int, int]] = []  # (first_model_col, span)
        _last_tid2 = None
        _grp_start = 0
        _grp_count = 0
        for ci, cs in enumerate(col_specs):
            tid2 = cs["trial_id"]
            if tid2 != _last_tid2:
                if _grp_count > 0:
                    trial_groups.append((_grp_start, _grp_count))
                _grp_start = ci + 1  # +1 weil Modell-Spalte 0 = Titel
                _grp_count = 1
                _last_tid2 = tid2
            else:
                _grp_count += 1
        if _grp_count > 0:
            trial_groups.append((_grp_start, _grp_count))

        # Zeilen die trial-weit gespannt werden sollen:
        # - Modell-Zeile 0 = Header V-Nummer (trial_hdr_vals)
        # - Modell-Zeile 2+ = alle tblTrial-Felder (StorageTable != tbltrialsettings)
        n_hdr = self.model_machine._n_hdr  # = 2
        trial_wide_model_rows: List[int] = [0]  # Header-Zeile "V1, V2..."
        # Fixed rows: Housing=n_hdr+0, Jet=n_hdr+1, Plate=n_hdr+2, AirPressure=n_hdr+3
        # In Groups-Modus: Plies=n_hdr+4 auch trial-weit
        # In Single Modus: YarnUse=n_hdr+4 ist ply-spezifisch → nicht spanen
        trial_wide_model_rows += [n_hdr + 0, n_hdr + 1, n_hdr + 2, n_hdr + 3]
        # Plies-Zeile (n_hdr+4) bewusst NICHT trial-weit — pro Gruppe eigener Wert
        # Dynamic field rows
        for offset, fdef in enumerate(field_map):
            if fdef.get("StorageTable", "tbltrial") != "tbltrialsettings":
                trial_wide_model_rows.append(n_hdr + len(titles_fixed) + offset)
        # CustomGroup ist tblTrial-Feld → trial-weit spannen
        trial_wide_model_rows.append(n_hdr + self._custom_group_row_idx)

        try:
            right_view = self.tbl_machine.right
            # Alle alten Spans zurücksetzen
            for row in range(right_view.model().rowCount()):
                for col in range(1, right_view.model().columnCount()):
                    if right_view.columnSpan(row, col) > 1 or right_view.rowSpan(row, col) > 1:
                        right_view.setSpan(row, col, 1, 1)
            # Neue Spans setzen
            for first_col, span in trial_groups:
                if span <= 1:
                    continue
                for row_idx in trial_wide_model_rows:
                    right_view.setSpan(row_idx, first_col, 1, span)
            try:
                right_view.viewport().update()
                self.tbl_machine.left.viewport().update()
            except Exception:
                pass
        except Exception:
            pass

        # Alte Row-Delegates komplett zurücksetzen (verhindert Geister-Dropdowns
        # wenn _build_machine_tab mehrfach aufgerufen wird und _n_hdr sich ändert)
        _total_rows = self.model_machine.rowCount()
        for _r in range(_total_rows):
            self.tbl_machine.right.setItemDelegateForRow(_r, None)

        # Dropdown-Delegate für Housing-Zeile (Row n_hdr + 0)
        if self._housing_list:
            self._housing_delegate = HousingComboDelegate(self._housing_list, self.tbl_machine)
            self.tbl_machine.setItemDelegateForRow(n_hdr + 0, self._housing_delegate)

        # Dropdown-Delegate für Jet-Zeile (Row n_hdr + 1)
        if self._jets_list:
            self._jet_delegate = JetComboDelegate(self._jets_list, self.tbl_machine)
            self.tbl_machine.setItemDelegateForRow(n_hdr + 1, self._jet_delegate)

        # LookupComboDelegate für generische dropdown-Zeilen (z.B. DiscID)
        self._lookup_delegates = []
        for row_idx, lk_map in dropdown_rows.items():
            lk_list = [(k, v) for k, v in lk_map.items() if isinstance(k, int)]
            lk_list.sort(key=lambda x: x[1])
            d = LookupComboDelegate(row_idx, lk_list, self.tbl_machine.right)
            self.tbl_machine.right.setItemDelegateForRow(n_hdr + row_idx, d)
            self._lookup_delegates.append(d)

        # Bild-Tooltip für Housing-Zeile
        try:
            self._housing_img_tooltip_filters = []
            for view in self.tbl_machine.findChildren(QTableView):
                f = _HousingImageTooltipFilter(self, self.tbl_machine, self)
                view.viewport().installEventFilter(f)
                self._housing_img_tooltip_filters.append(f)
        except Exception:
            pass

        # ── Ply filter toolbar aufbauen ─────────────────────────────────
        unique_trial_ids_flt = []
        for cs in col_specs:
            if cs.get("trial_id") not in unique_trial_ids_flt:
                unique_trial_ids_flt.append(cs.get("trial_id"))
        has_multi_ply_flt = len(col_specs) > len(unique_trial_ids_flt)

        # Bestehende Checkboxen entfernen
        while self._mat_check_layout.count():
            item = self._mat_check_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._mat_filter_checks: list = []

        if has_multi_ply_flt:
            # Zeige-Labels aufbauen: im Groups-Modus Gruppen, sonst Plies
            seen_labels_flt: list = []
            seen_set_flt: set = set()
            for cs in col_specs:
                if cs.get("is_group"):
                    lbl = str(cs.get("yarn_use_name") or cs.get("ply") or "")
                else:
                    lbl = str(cs.get("ply") or "")
                if lbl and lbl not in seen_set_flt:
                    seen_set_flt.add(lbl)
                    seen_labels_flt.append(lbl)

            lbl_flt = QLabel("Zeige:")
            lbl_flt.setStyleSheet("color: #555; font-size: 11px;")
            self._mat_check_layout.addWidget(lbl_flt)
            for pl in seen_labels_flt:
                cb = QCheckBox(pl)
                cb.setChecked(True)
                cb.stateChanged.connect(self._apply_mat_column_filter)
                self._mat_check_layout.addWidget(cb)
                self._mat_filter_checks.append(cb)

            # Groups-Modus nur anbieten wenn YarnUseIDs in den Settings vorhanden — aus Cache
            has_groups = cache.get("has_groups", False)
            self._rb_groups.setEnabled(has_groups)
            if not has_groups and self._rb_groups.isChecked():
                self._rb_single.setChecked(True)

            self._mat_filter_bar.setVisible(True)
        else:
            # Auch ohne Multi-Ply: Filter-Bar anzeigen damit Modus-Buttons sichtbar bleiben
            # Groups deaktivieren, Single erzwingen
            has_groups = cache.get("has_groups", False)
            self._rb_groups.setEnabled(False)
            if self._rb_groups.isChecked():
                self._rb_single.setChecked(True)
            # Zeige-Checkboxen leeren (keine Plies zum Filtern)
            while self._mat_check_layout.count():
                item = self._mat_check_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self._mat_filter_checks = []
            self._mat_filter_bar.setVisible(True)

        # R&D Machine Tab mit RDSetting=1 Feldern aufbauen
        self._build_rd_machine_tab(
            fields_rd=fields_rd,
            machine_id=machine_id,
            col_specs=col_specs,
            settings_cols_map=settings_cols_map,
            trial_rows=trial_rows,
        )

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

                new_ply_vals = [""]
                new_tooltips = [""]
                for cs in col_specs:
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

        trial_first_seen: set = set()
        right_view = self.tbl_machine.right

        for c_idx, cs in enumerate(col_specs):
            model_col = c_idx + 1
            tid = cs.get("trial_id")
            if groups:
                lbl = str(cs.get("yarn_use_name") or cs.get("ply") or "")
            else:
                lbl = str(cs.get("ply") or "")

            if compact:
                if tid not in trial_first_seen:
                    trial_first_seen.add(tid)
                    hidden = False
                else:
                    hidden = True
            else:
                if checked_labels is not None and lbl:
                    hidden = lbl not in checked_labels
                else:
                    hidden = False

            right_view.setColumnHidden(model_col, hidden)

        self.tbl_machine.resizeColumnsToContents()

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
        """Baut den 'R&D Machine Data'-Tab mit RDSetting=1-Feldern auf.
        Tab wird nur angezeigt, wenn mindestens ein solches Feld existiert.
        """
        cache = getattr(self, "_machine_cache", None) or {}
        # Tab immer zuerst entfernen (falls bereits vorhanden vom letzten Laden)
        if self.tab_rd_machine is not None:
            idx = self.tabs.indexOf(self.tab_rd_machine)
            if idx != -1:
                self.tabs.removeTab(idx)

        if not fields_rd:
            # Keine R&D-Felder -> Tab bleibt versteckt
            self.model_rd_machine = MachinePivotModel(
                jets_map=self._jets_map,
                row_titles=[],
                col_titles=self._trial_labels,
                read_only_rows=set(),
                row_validators=[],
                jet_row_index=-1,
                housing_map=self._housing_map,
                housing_row_index=-1,
                jets_tooltip_map=self._jets_tooltip_map,
                housing_image_map=getattr(self, "_housing_image_map", {}),
                dropdown_rows={},
            )
            self.tbl_rd_machine.setModel(self.model_rd_machine)
            return

        # Tab direkt nach "Machine Data" einfügen
        machine_idx = self.tabs.indexOf(self.tab_machine)
        insert_pos = machine_idx + 1 if machine_idx != -1 else self.tabs.count()
        self.tabs.insertTab(insert_pos, self.tab_rd_machine, "R&&D Machine Data")

        trial_cols = get_columns_map("tblTrial")

        # Fixe Titel (gleiche wie Machine Data)
        FIX_HOUSING = "Housing"
        FIX_JET = "Jet"
        FIX_PLATE = "Jet Plate Number"
        FIX_AIR = "Air Pressure (bar)"
        titles_fixed = [FIX_HOUSING, FIX_JET, FIX_PLATE, FIX_AIR]
        self._rd_machine_titles_fixed_count = len(titles_fixed)

        reserved_titles = [
            "Versuchsnummer", "Housing",
            "Jet", "Jet Name",
            "JetPlate", "Jet Plate Number",
            "Air Pressure (bar)",
            "Yarn Use", "YarnUse", "YarnUseID",
        ]
        reserved_norm = {norm(x) for x in reserved_titles}
        reserved_validators: Dict[str, Optional[str]] = {FIX_PLATE: None, FIX_AIR: None}
        reserved_originals: Dict[str, Optional[str]] = {FIX_PLATE: None, FIX_AIR: None}
        reserved_norm.add(norm(FIX_HOUSING))

        seen_norm_titles: set = set()
        field_map: List[Dict[str, Optional[str]]] = []
        field_validators: List[Optional[str]] = []

        for f in fields_rd:
            disp = str(f.get("FieldName") or "").strip()
            orig = str(f.get("OriginalName") or "").strip()
            ff = canon_rule((f.get("FieldFunction") or "").strip() or None)
            if not disp:
                continue
            if ff == "hidden":
                continue

            disp_norm = norm(disp)
            if disp_norm in reserved_norm:
                if disp_norm in {norm(FIX_PLATE), norm("JetPlateNumber"), norm("JetPlate")}:
                    reserved_validators[FIX_PLATE] = ff
                    reserved_originals[FIX_PLATE] = orig or reserved_originals[FIX_PLATE]
                elif disp_norm in {norm(FIX_AIR), norm("AirPressure")}:
                    reserved_validators[FIX_AIR] = ff
                    reserved_originals[FIX_AIR] = orig or reserved_originals[FIX_AIR]
                continue

            if disp_norm in seen_norm_titles:
                continue

            col = None
            if orig:
                col = trial_cols.get(orig.lower()) or resolve_field([orig], trial_cols)
            if not col and disp:
                col = trial_cols.get(disp.lower()) or resolve_field([disp], trial_cols)

            lookup_table = None
            if ff and ff.lower().startswith("dropdown:"):
                lookup_table = ff[len("dropdown:"):].strip() or None

            field_map.append({
                "Title": disp,
                "ColName": col or orig or disp,
                "StorageTable": str(f.get("StorageTable") or "tbltrial").strip().lower(),
                "LookupTable": lookup_table,
            })
            field_validators.append(ff)
            seen_norm_titles.add(disp_norm)

        row_titles = titles_fixed + [f["Title"] for f in field_map]
        row_validators: List[Optional[str]] = [None] * len(row_titles)
        row_validators[2] = reserved_validators.get(FIX_PLATE)
        row_validators[3] = reserved_validators.get(FIX_AIR)
        for i, ff in enumerate(field_validators, start=len(titles_fixed)):
            row_validators[i] = ff

        # Dropdown-Maps aufbauen
        dropdown_rows: Dict[int, Dict[Any, str]] = {}
        for i, fdef in enumerate(field_map):
            lt = fdef.get("LookupTable")
            if not lt:
                continue
            row_idx = len(titles_fixed) + i
            lk_map: Dict[Any, str] = {}
            try:
                if table_exists(lt):
                    lk_cmap = get_columns_map(lt)
                    lk_id = resolve_field(["ID"], lk_cmap) or "ID"
                    lk_name = resolve_field(
                        ["DiscName", "Name", "Bezeichnung", "Caption",
                         "HousingName", "Jet", "JetName", "MaterialName",
                         "YarnName", "Description", "Label"],
                        lk_cmap)
                    if lk_name:
                        lk_rows = fetch_all(
                            f"SELECT [{lk_id}] AS LID, [{lk_name}] AS LName "
                            f"FROM {lt} ORDER BY [{lk_name}] ASC"
                        )
                        for lk in lk_rows:
                            lid = lk.get("LID")
                            lname = str(lk.get("LName") or "")
                            if lid is None:
                                continue
                            try:
                                lk_map[int(lid)] = lname
                            except Exception:
                                pass
                            lk_map[str(lid)] = lname
            except Exception:
                pass
            if lk_map:
                dropdown_rows[row_idx] = lk_map

        # Header-Zeilen
        trial_hdr_vals = [""]
        ply_hdr_vals = [""]
        ply_tooltip_vals = [""]
        for cs in col_specs:
            trial_hdr_vals.append(f"V{cs['vno']}")
            ply_hdr_vals.append(cs["ply"])
            ply_tooltip_vals.append(cs.get("yarn_name") or "")

        hdr_rows = [
            {"values": trial_hdr_vals, "bg": None, "fg": None},
            {"values": ply_hdr_vals, "bg": None, "fg": None, "tooltips": ply_tooltip_vals},
        ]
        expanded_col_titles = ["" for _ in col_specs]

        self.model_rd_machine = MachinePivotModel(
            jets_map=self._jets_map,
            row_titles=row_titles,
            col_titles=expanded_col_titles,
            read_only_rows=set(),
            row_validators=row_validators,
            jet_row_index=1,
            header_rows=hdr_rows,
            housing_map=self._housing_map,
            housing_row_index=0,
            jets_tooltip_map=self._jets_tooltip_map,
            housing_image_map=getattr(self, "_housing_image_map", {}),
            dropdown_rows=dropdown_rows,
        )
        self._register_save_model("model_rd_machine")

        # Zellen befüllen (analog zu _build_machine_tab)
        trial_cols_map = cache.get("trial_cols_map") or get_columns_map("tblTrial")

        def _pick_row_key_rd(row: dict, preferred: Optional[str], extra_cands: List[str]) -> Optional[str]:
            if not row:
                return None
            if preferred and preferred in row:
                return preferred
            if preferred:
                pl = preferred.lower()
                for k in row.keys():
                    if str(k).lower() == pl:
                        return k
            wanted = []
            if preferred:
                wanted.append(preferred)
            wanted.extend(extra_cands or [])
            wanted_norm = {norm(w) for w in wanted if w}
            for k in row.keys():
                if norm(str(k)) in wanted_norm:
                    return k
            return None

        jet_plate_col = trial_cols_map.get("jetplate") or trial_cols_map.get("jet_plate")
        if not jet_plate_col and reserved_originals.get(FIX_PLATE):
            jet_plate_col = trial_cols_map.get(reserved_originals[FIX_PLATE].lower()) \
                            or resolve_field([reserved_originals[FIX_PLATE]], trial_cols_map)
        if not jet_plate_col:
            jet_plate_col = resolve_field(
                ["Jet Plate", "JetPlate", "Jet_Plate", "JetPlateNumber", "Jet Plate Number"], trial_cols_map)

        air_press_col = trial_cols_map.get("airpressure") or trial_cols_map.get("air_pressure")
        if not air_press_col and reserved_originals.get(FIX_AIR):
            air_press_col = trial_cols_map.get(reserved_originals[FIX_AIR].lower()) \
                            or resolve_field([reserved_originals[FIX_AIR]], trial_cols_map)
        if not air_press_col:
            air_press_col = resolve_field(
                ["Air Pressure (bar)", "AirPressure(bar)", "AirPressure", "Air_Pressure_bar", "Air Pressure"],
                trial_cols_map)

        housing_id_col = resolve_field(["HousingID"], trial_cols_map)

        # 0: Housing
        for c_idx, cs in enumerate(col_specs):
            trow = cs["trial"]
            housing_id = trow.get("HousingID") if housing_id_col else None
            self.model_rd_machine.set_cell(
                0, c_idx, housing_id,
                CellBinding("tblTrial", "ID", trow.get("ID"), "HousingID") if (
                            housing_id_col and trow.get("ID")) else None,
            )

        # 1: Jet
        for c_idx, cs in enumerate(col_specs):
            trow = cs["trial"]
            self.model_rd_machine.set_cell(
                1, c_idx, trow.get("JetID"),
                CellBinding("tblTrial", "ID", trow.get("ID"), "JetID") if trow.get("ID") else None,
            )

        # 2: Jet Plate Number
        for c_idx, cs in enumerate(col_specs):
            trow = cs["trial"]
            jp_key = _pick_row_key_rd(trow, jet_plate_col,
                                      ["JetPlate", "jetplate", "Jet_Plate", "jet_plate", "Jet Plate",
                                       "Jet Plate Number", "JetPlateNumber"])
            jp_field = jet_plate_col or jp_key
            self.model_rd_machine.set_cell(
                2, c_idx,
                trow.get(jp_key) if jp_key else None,
                CellBinding("tblTrial", "ID", trow.get("ID"), jp_field) if (jp_field and trow.get("ID")) else None,
            )

        # 3: Air Pressure
        for c_idx, cs in enumerate(col_specs):
            trow = cs["trial"]
            ap_key = _pick_row_key_rd(trow, air_press_col,
                                      ["AirPressure", "airpressure", "Air_Pressure", "air_pressure",
                                       "Air Pressure", "Air Pressure (bar)", "AirPressure(bar)", "Air_Pressure_bar"])
            ap_field = air_press_col or ap_key
            self.model_rd_machine.set_cell(
                3, c_idx,
                trow.get(ap_key) if ap_key else None,
                CellBinding("tblTrial", "ID", trow.get("ID"), ap_field) if (ap_field and trow.get("ID")) else None,
            )

        # Dynamische Felder
        start_row = len(titles_fixed)
        for offset, fdef in enumerate(field_map):
            r_idx = start_row + offset
            storage = fdef.get("StorageTable", "tbltrial")
            colname = fdef["ColName"]

            if storage == "tbltrialsettings" and settings_cols_map:
                real_col = settings_cols_map.get(colname.lower()) or colname
                for c_idx, cs in enumerate(col_specs):
                    sr = cs["sr"]
                    val = sr.get(real_col) if sr else None
                    binding = CellBinding("tblTrialSettings", "ID", sr["ID"], real_col) if sr else None
                    self.model_rd_machine.set_cell(r_idx, c_idx, val, binding)
            else:
                real_col = trial_cols_map.get(str(colname).lower()) or colname
                for c_idx, cs in enumerate(col_specs):
                    trow = cs["trial"]
                    val = trow.get(real_col)
                    self.model_rd_machine.set_cell(
                        r_idx, c_idx, val,
                        CellBinding("tblTrial", "ID", trow.get("ID"), real_col) if trow.get("ID") else None,
                    )

        self.tbl_rd_machine.setModel(self.model_rd_machine)
        self.tbl_rd_machine.resizeColumnsToContents()
        self.tbl_rd_machine.left.horizontalHeader().setVisible(False)
        self.tbl_rd_machine.right.horizontalHeader().setVisible(False)

        # setSpan für trial-weite Spalten
        n_hdr = self.model_rd_machine._n_hdr
        trial_groups: List[Tuple[int, int]] = []
        _last_tid = None
        _grp_start = 0
        _grp_count = 0
        for ci, cs in enumerate(col_specs):
            tid = cs["trial_id"]
            if tid != _last_tid:
                if _grp_count > 0:
                    trial_groups.append((_grp_start, _grp_count))
                _grp_start = ci + 1
                _grp_count = 1
                _last_tid = tid
            else:
                _grp_count += 1
        if _grp_count > 0:
            trial_groups.append((_grp_start, _grp_count))

        trial_wide_model_rows: List[int] = [0]
        trial_wide_model_rows += [n_hdr + 0, n_hdr + 1, n_hdr + 2, n_hdr + 3]
        for offset, fdef in enumerate(field_map):
            if fdef.get("StorageTable", "tbltrial") != "tbltrialsettings":
                trial_wide_model_rows.append(n_hdr + len(titles_fixed) + offset)

        try:
            right_view = self.tbl_rd_machine.right
            for row in range(right_view.model().rowCount()):
                for col in range(1, right_view.model().columnCount()):
                    if right_view.columnSpan(row, col) > 1 or right_view.rowSpan(row, col) > 1:
                        right_view.setSpan(row, col, 1, 1)
            for first_col, span in trial_groups:
                if span <= 1:
                    continue
                for row_idx in trial_wide_model_rows:
                    right_view.setSpan(row_idx, first_col, 1, span)
        except Exception:
            pass

        # Row-Delegates zurücksetzen
        _total_rows = self.model_rd_machine.rowCount()
        for _r in range(_total_rows):
            self.tbl_rd_machine.right.setItemDelegateForRow(_r, None)

        # Housing-Delegate
        if self._housing_list:
            self._rd_housing_delegate = HousingComboDelegate(self._housing_list, self.tbl_rd_machine)
            self.tbl_rd_machine.setItemDelegateForRow(n_hdr + 0, self._rd_housing_delegate)

        # Jet-Delegate
        if self._jets_list:
            self._rd_jet_delegate = JetComboDelegate(self._jets_list, self.tbl_rd_machine)
            self.tbl_rd_machine.setItemDelegateForRow(n_hdr + 1, self._rd_jet_delegate)

        # LookupComboDelegate
        self._rd_lookup_delegates = []
        for row_idx, lk_map in dropdown_rows.items():
            lk_list = [(k, v) for k, v in lk_map.items() if isinstance(k, int)]
            lk_list.sort(key=lambda x: x[1])
            d = LookupComboDelegate(row_idx, lk_list, self.tbl_rd_machine.right)
            self.tbl_rd_machine.right.setItemDelegateForRow(n_hdr + row_idx, d)
            self._rd_lookup_delegates.append(d)

        # col_specs für _fill_machine_row_from_title
        self._rd_machine_col_specs = col_specs

        # ── Tooltips: Housing-Zeilen und OF-Zeile auf Model markieren ────
        housing_rows = set()
        of_row_idx = None
        for i, title in enumerate(row_titles):
            tl = title.lower()
            if "housing" in tl:
                housing_rows.add(i)
            if "w0" in tl and "w1" in tl and "of" in tl:
                of_row_idx = i

        self.model_rd_machine._all_housing_rows = housing_rows

        jet_rows = set()
        for i, title in enumerate(row_titles):
            if "jet" in title.lower():
                jet_rows.add(i)
        self.model_rd_machine._all_jet_rows = jet_rows

        # Install Housing Bild-Tooltip filter for R&D tab
        try:
            self._rd_housing_tooltip_filters = []
            for view in self.tbl_rd_machine.findChildren(QTableView):
                f = _RDHousingTooltipFilter(self, self.tbl_rd_machine, self)
                view.viewport().installEventFilter(f)
                self._rd_housing_tooltip_filters.append(f)
        except Exception:
            pass

        if of_row_idx is not None:
            _of_row = of_row_idx
            _screen = self

            def _of_calc(col_0based, _of_row=_of_row, _screen=_screen):
                model_rd = _screen.model_rd_machine
                model_m = _screen.model_machine
                if model_rd is None or model_m is None:
                    return None

                def _val(model, title_norm):
                    for i, t in enumerate(getattr(model, "_row_titles", [])):
                        n = t.lower()
                        for ch in " _()-/":
                            n = n.replace(ch, "")
                        if n == title_norm:
                            mx = getattr(model, "_matrix", [])
                            if 0 <= i < len(mx) and 0 <= col_0based < len(mx[i]):
                                try:
                                    return float(mx[i][col_0based])
                                except Exception:
                                    return None
                    return None

                speed = _val(model_m, "speedshaft2mmin")
                dr = _val(model_m, "shaft1dr")
                of_val = _val(model_rd, "w0w1of%")
                if of_val is None:
                    of_val = _val(model_rd, "w0w1of")
                if speed is None or dr is None or of_val is None or dr == 0:
                    return None
                result = speed / dr * (100 + of_val) / 100
                return f"Speed: {int(round(result))} m/min"

            self.model_rd_machine._of_tooltip_row = of_row_idx
            self.model_rd_machine._of_tooltip_calc = _of_calc
        else:
            self.model_rd_machine._of_tooltip_row = None
            self.model_rd_machine._of_tooltip_calc = None

    def _fill_machine_row_from_title(self, row: int, is_rd: bool = False):
        """Dialog anzeigen und eine komplette Zeile im Machine-Tab befüllen."""
        cache = getattr(self, "_machine_cache", None) or {}
        _model = self.model_rd_machine if is_rd else self.model_machine
        _tbl = self.tbl_rd_machine if is_rd else self.tbl_machine
        _col_specs = getattr(self, "_rd_machine_col_specs" if is_rd else "_machine_col_specs", None)
        if not _model:
            return

        # pseudo-header rows ignorieren
        n_hdr = getattr(_model, "_n_hdr", 0)
        if row < n_hdr:
            return

        # Enforce permissions (AccessLevel >= 2 required for bulk row set)
        try:
            lvl = int(getattr(app_meta, "access_level", lambda: 0)() or 0)
        except Exception:
            try:
                user = getattr(app_meta, "current_user", {}) or {}
                lvl = int(user.get("access_level")
                          or user.get("AccessLevel") or 0)
            except Exception:
                lvl = 0
        if lvl < 2:
            QMessageBox.information(
                self,
                "Permission denied",
                "You do not have permission to change values.",
            )
            return

        # Titel der Zeile ermitteln
        title_index = self.model_machine.index(row, 0)
        title = str(self.model_machine.data(title_index, Qt.DisplayRole) or "")

        # Defaultwert: erstes nicht-leeres, editierbares Feld in dieser Zeile
        default_text = ""
        for col in range(1, self.model_machine.columnCount()):
            idx = self.model_machine.index(row, col)
            if not (self.model_machine.flags(idx) & Qt.ItemIsEditable):
                continue
            val = self.model_machine.data(idx, Qt.DisplayRole)
            if val not in (None, ""):
                default_text = str(val)
                break

        # Real trial count (not column count which includes Ply expansions)
        _col_specs_tmp = getattr(self, "_machine_col_specs", None) or []
        if _col_specs_tmp:
            _unique_tids = []
            for _cs in _col_specs_tmp:
                if _cs.get("trial_id") not in _unique_tids:
                    _unique_tids.append(_cs.get("trial_id"))
            n_trials = max(1, len(_unique_tids))
        else:
            n_trials = max(1, self.model_machine.columnCount() - 1)
        if n_trials <= 0:
            return

        housing_model_row = n_hdr + 0  # Housing ist data-row 0
        jet_model_row = n_hdr + 1  # Jet ist data-row 1

        if row == housing_model_row and self._housing_list:
            # Housing-Zeile: Dropdown
            default_housing_id = None
            try:
                for col in range(1, self.model_machine.columnCount()):
                    internal = self.model_machine.get_cell_value(row - n_hdr, col - 1)
                    if internal not in (None, "", " "):
                        default_housing_id = internal
                        break
            except Exception:
                default_housing_id = None

            dlgh = _FillRowRangeHousingDialog(
                self, title=title, n_trials=n_trials,
                housing_list=self._housing_list, default_housing_id=default_housing_id,
            )
            if dlgh.exec() != QDialog.Accepted:
                return
            start_trial, end_trial, housing_id = dlgh.get_values()
            value_to_set = housing_id

        elif row == jet_model_row and self._jets_list:
            # Jet-Zeile: Dropdown
            default_jet_id = None
            try:
                for col in range(1, self.model_machine.columnCount()):
                    internal = self.model_machine.get_cell_value(row - n_hdr, col - 1)
                    if internal not in (None, "", " "):
                        default_jet_id = internal
                        break
            except Exception:
                default_jet_id = None

            dlgj = _FillRowRangeJetDialog(
                self, title=title, n_trials=n_trials,
                jets_list=self._jets_list, default_jet_id=default_jet_id,
            )
            if dlgj.exec() != QDialog.Accepted:
                return
            start_trial, end_trial, jet_id = dlgj.get_values()
            value_to_set = jet_id

        elif (row - n_hdr) in getattr(self.model_machine, "_dropdown_rows", {}):
            # Generische Lookup-Zeile (z.B. DiscType): Dropdown
            data_row = row - n_hdr
            lk_map = self.model_machine._dropdown_rows[data_row]
            default_id = None
            try:
                for col in range(1, self.model_machine.columnCount()):
                    internal = self.model_machine.get_cell_value(data_row, col - 1)
                    if internal not in (None, "", " "):
                        default_id = internal
                        break
            except Exception:
                default_id = None

            # Determine ply_labels for this dropdown row (same logic as text rows)
            col_specs_dd = getattr(self, "_machine_col_specs", None) or []
            _seen_plies_dd: list = []
            _seen_set_dd: set = set()
            for cs in col_specs_dd:
                pl = str(cs.get("ply") or "")
                if pl and pl not in _seen_set_dd:
                    _seen_set_dd.add(pl)
                    _seen_plies_dd.append(pl)
            unique_trial_ids_dd = []
            for cs in col_specs_dd:
                if cs.get("trial_id") not in unique_trial_ids_dd:
                    unique_trial_ids_dd.append(cs.get("trial_id"))
            has_multi_ply_dd = len(col_specs_dd) > len(unique_trial_ids_dd)
            ply_labels_dd = _seen_plies_dd if has_multi_ply_dd else []

            dlgd = _FillRowRangeDropdownDialog(
                self, title=title, n_trials=n_trials,
                lookup_map=lk_map, default_id=default_id,
                ply_labels=ply_labels_dd,
            )
            if dlgd.exec() != QDialog.Accepted:
                return
            start_trial, end_trial, value_to_set, selected_plies_dd = dlgd.get_values()

            # Apply: über col_specs iterieren, mit optionalem Ply-Filter
            col_specs = getattr(self, "_machine_col_specs", None) or []
            unique_trial_ids = []
            for cs in col_specs:
                if cs.get("trial_id") not in unique_trial_ids:
                    unique_trial_ids.append(cs.get("trial_id"))
            trial_order = {tid: i + 1 for i, tid in enumerate(unique_trial_ids)}
            if col_specs:
                for c_idx, cs in enumerate(col_specs):
                    ti = trial_order.get(cs.get("trial_id"), 0)
                    if not (start_trial <= ti <= end_trial):
                        continue
                    if selected_plies_dd is not None:
                        ply = str(cs.get("ply") or "")
                        if ply not in selected_plies_dd:
                            continue
                    model_col = c_idx + 1  # col 0 = title
                    idx = self.model_machine.index(row, model_col)
                    if self.model_machine.flags(idx) & Qt.ItemIsEditable:
                        self.model_machine.setData(idx, value_to_set, Qt.EditRole)
            else:
                for col in range(start_trial, end_trial + 1):
                    idx = self.model_machine.index(row, col)
                    if self.model_machine.flags(idx) & Qt.ItemIsEditable:
                        self.model_machine.setData(idx, value_to_set, Qt.EditRole)
            return

        else:
            # Determine whether this is a tblTrialSettings row (Ply-specific)
            # or a tblTrial row (trial-wide) so we can show/hide Ply checkboxes.
            col_specs = getattr(self, "_machine_col_specs", None) or []
            n_hdr = getattr(self.model_machine, "_n_hdr", 0)
            if is_rd:
                titles_fixed_count = getattr(self, "_rd_machine_titles_fixed_count", 4)
            else:
                titles_fixed_count = getattr(self, "_machine_titles_fixed_count", 5)

            # Im Groups-Modus: Gruppen-Labels statt Ply-Labels für den Dialog
            use_groups = getattr(self._rb_groups, "isChecked", lambda: False)()

            # Collect distinct, ordered labels from col_specs
            _seen_plies: list = []
            _seen_set: set = set()
            for cs in col_specs:
                if use_groups:
                    pl = str(cs.get("yarn_use_name") or cs.get("ply") or "")
                else:
                    pl = str(cs.get("ply") or "")
                if pl and pl not in _seen_set:
                    _seen_set.add(pl)
                    _seen_plies.append(pl)

            # A row is Ply-specific if it maps to tblTrialSettings.
            # Fixed rows (Housing/Jet/Plate/Air) and tblTrial dynamic fields are trial-wide.
            data_row_idx = row - n_hdr  # 0-based into row_titles
            is_ply_row = False
            if data_row_idx >= titles_fixed_count and col_specs:
                # Dynamic field: check field_map (stored in model via row_titles)
                # Easiest: if any two adjacent col_specs for the same trial differ
                # in ply → the row lives in tblTrialSettings.
                # More reliable: check if multiple col_specs share a trial_id
                # (which only happens when tblTrialSettings is used).
                trial_ids_seen: list = []
                for cs in col_specs:
                    tid = cs.get("trial_id")
                    if tid not in trial_ids_seen:
                        trial_ids_seen.append(tid)
                # If we have more col_specs than unique trials → multi-ply → some rows are Ply-specific.
                # We determine whether *this specific row* is Ply-specific by checking whether
                # all col_specs in this row have different sr (settings row) per trial.
                has_multi_ply = len(col_specs) > len(trial_ids_seen)
                if has_multi_ply:
                    # Check the model_machine row_titles for this row
                    row_title_idx = self.model_machine.index(row, 0)
                    rt = str(self.model_machine.data(row_title_idx, Qt.DisplayRole) or "")
                    # Heuristic: if any col_spec has sr != None for this row,
                    # the field is in tblTrialSettings.
                    # We detect this via MachinePivotModel's binding list.
                    # Simplest robust approach: check whether the binding of col 1 (first data col)
                    # references tblTrialSettings.
                    try:
                        b = self.model_machine.get_binding(data_row_idx, 0)
                        if b is not None and str(getattr(b, "table", "") or "").lower() == "tbltrialsettings":
                            is_ply_row = True
                    except Exception:
                        pass

            ply_labels_for_dlg = _seen_plies if is_ply_row else []

            # n_trials = actual number of distinct trials (not column count)
            unique_trial_ids = []
            for cs in col_specs:
                if cs.get("trial_id") not in unique_trial_ids:
                    unique_trial_ids.append(cs.get("trial_id"))
            n_trials_real = len(unique_trial_ids) if unique_trial_ids else n_trials

            dlg = _FillRowRangeDialog(
                self, title=title,
                n_trials=n_trials_real,
                default_value=default_text,
                ply_labels=ply_labels_for_dlg,
            )
            if dlg.exec() != QDialog.Accepted:
                return
            start_trial, end_trial, text, selected_plies = dlg.get_values()
            value_to_set = text

            # Apply: iterate col_specs to find matching (trial_index, ply) combinations
            if col_specs:
                # Map trial_id -> 1-based trial index (by order in unique_trial_ids)
                trial_order = {tid: i + 1 for i, tid in enumerate(unique_trial_ids)}
                for c_idx, cs in enumerate(col_specs):
                    ti = trial_order.get(cs.get("trial_id"), 0)
                    if not (start_trial <= ti <= end_trial):
                        continue
                    if selected_plies is not None:
                        ply = str(cs.get("ply") or "")
                        if ply not in selected_plies:
                            continue
                    model_col = c_idx + 1  # column 0 = title
                    idx = self.model_machine.index(row, model_col)
                    if not (self.model_machine.flags(idx) & Qt.ItemIsEditable):
                        continue
                    self.model_machine.setData(idx, value_to_set, Qt.EditRole)
            else:
                for col in range(start_trial, end_trial + 1):
                    idx = self.model_machine.index(row, col)
                    if not (self.model_machine.flags(idx) & Qt.ItemIsEditable):
                        continue
                    self.model_machine.setData(idx, value_to_set, Qt.EditRole)
            return  # early return — apply already done above

        # Apply for Housing / Jet (trial-wide, no Ply distinction needed)
        # These rows are always spanned across plies → only one col per trial group.
        if col_specs := getattr(self, "_machine_col_specs", None):
            unique_trial_ids2 = []
            for cs in col_specs:
                if cs.get("trial_id") not in unique_trial_ids2:
                    unique_trial_ids2.append(cs.get("trial_id"))
            trial_order2 = {tid: i + 1 for i, tid in enumerate(unique_trial_ids2)}
            n_trials_real2 = len(unique_trial_ids2)
            for c_idx, cs in enumerate(col_specs):
                ti = trial_order2.get(cs.get("trial_id"), 0)
                if not (start_trial <= ti <= end_trial):
                    continue
                model_col = c_idx + 1
                idx = self.model_machine.index(row, model_col)
                if not (self.model_machine.flags(idx) & Qt.ItemIsEditable):
                    continue
                self.model_machine.setData(idx, value_to_set, Qt.EditRole)
        else:
            for col in range(start_trial, end_trial + 1):
                idx = self.model_machine.index(row, col)
                if not (self.model_machine.flags(idx) & Qt.ItemIsEditable):
                    continue
                self.model_machine.setData(idx, value_to_set, Qt.EditRole)

    # ---------- Titer (nur sichtbar wenn Daten) ----------

    def _on_machine_header_context(self, pos):
        """Rechtsklick auf Spaltenkopf im Machine-Tab.

        Ermöglicht das Kopieren eines Trials (inkl. Labor-Struktur) mehrfach.
        """
        if not self.model_machine or not self._trial_ids:
            return

        header = self.tbl_machine.horizontalHeader()
        col = header.logicalIndexAt(pos)
        # Spalte 0 = Zeilentitel (kein Trial)
        if col <= 0:
            return

        trial_index = col - 1
        if trial_index < 0 or trial_index >= len(self._trial_ids):
            return

        trial_label = self._trial_labels[trial_index] if trial_index < len(
            self._trial_labels) else f"V?"

        count, ok = QInputDialog.getInt(
            self,
            "Trials kopieren",
            f"Wie viele Kopien von Trial {trial_label} erstellen?",
            1, 1, 50, 1,
        )
        if not ok or count <= 0:
            return

        self._duplicate_trials_from_machine_col(trial_index, count)

    def _toggle_custom_group_row(self) -> None:
        """Schaltet die Custom-Group-Zeile im Machine-Tab ein/aus und speichert den Zustand."""
        self._custom_group_visible = not self._custom_group_visible
        # Zeile im View ein-/ausblenden
        if self.model_machine:
            n_hdr = getattr(self.model_machine, '_n_hdr', 2)
            cg_view_row = n_hdr + getattr(self, '_custom_group_row_idx', 0)
            self.tbl_machine.left.setRowHidden(cg_view_row, not self._custom_group_visible)
            self.tbl_machine.right.setRowHidden(cg_view_row, not self._custom_group_visible)

    def _manage_plies_for_col_spec_idx(self, col_spec_idx: int) -> None:
        """Öffnet den Manage-Plies-Dialog für den Trial, der col_spec_idx zugeordnet ist."""
        col_specs = getattr(self, "_machine_col_specs", None)
        if not col_specs or col_spec_idx < 0 or col_spec_idx >= len(col_specs):
            return
        cs = col_specs[col_spec_idx]
        trial_id = cs.get("trial_id")
        vno = cs.get("vno", "?")

        # Alle verfügbaren Yarns laden
        yarn_rows = fetch_all("SELECT ID, Name FROM tblYarn ORDER BY Name")
        if not yarn_rows:
            QMessageBox.warning(self, "Manage Plies", "Keine Yarns in tblYarn gefunden.")
            return
        yarn_list = [(int(r["ID"]), str(r["Name"] or "")) for r in yarn_rows]

        # Alle Trials der Series laden für Multi-Trial-Auswahl
        all_trial_rows = fetch_all(
            "SELECT ID, Versuchsnummer FROM tblTrial WHERE TrialSeriesID = ? ORDER BY Versuchsnummer",
            [self._series_pk]
        )
        all_trials = [(int(r["ID"]), str(r["Versuchsnummer"])) for r in all_trial_rows]

        dlg = _ManagePliesDialog(self, trial_id=trial_id, vno=vno,
                                 series_pk=self._series_pk, yarn_list=yarn_list,
                                 all_trials=all_trials)
        if dlg.exec() == QDialog.Accepted:
            # has_groups neu prüfen (könnte sich geändert haben)
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
        """Öffnet den Vervielfältigungs-Dialog für den Versuch, der col_spec_idx zugeordnet ist.

        col_spec_idx = Index in _machine_col_specs (= Modell-Spalte minus 1).
        Da mehrere Ply-Spalten zum selben Trial gehören können, wird via
        _machine_col_specs der korrekte trial_id + trial_index ermittelt.
        """
        if not self.model_machine or not self._trial_ids:
            return

        col_specs = getattr(self, "_machine_col_specs", None)
        if not col_specs or col_spec_idx < 0 or col_spec_idx >= len(col_specs):
            return

        cs = col_specs[col_spec_idx]
        trial_id = cs.get("trial_id")
        vno = cs.get("vno", "?")

        # trial_index = Position in self._trial_ids
        try:
            trial_index = self._trial_ids.index(trial_id)
        except ValueError:
            QMessageBox.warning(self, "Fehler", f"Trial-ID {trial_id} nicht gefunden.")
            return

        trial_label = f"V{vno}"

        count, ok = QInputDialog.getInt(
            self,
            "Versuch kopieren",
            f"Wie viele Kopien von {trial_label} erstellen?",
            1, 1, 50, 1,
        )
        if not ok or count <= 0:
            return

        self._duplicate_trials_from_machine_col(trial_index, count)

    def _duplicate_trials_from_machine_col(self, trial_index: int, copies: int) -> None:
        """Erstellt `copies` neue Trials auf Basis des Trials an `trial_index`.

        - TrialSeriesID bleibt gleich
        - Versuchsnummer wird hochgezählt (MAX+1, MAX+2, ...)
        - Maschinenparameter werden 1:1 übernommen
        - Labor-Datensätze werden strukturell kopiert, Messwerte aber genullt
        """
        if not self._trial_ids or self._series_pk is None:
            return
        if trial_index < 0 or trial_index >= len(self._trial_ids):
            return

        src_trial_id = self._trial_ids[trial_index]
        series_id = self._series_pk

        try:
            from db.connection import get_connection  # sollte bereits importiert sein
        except Exception:
            from db.connection import get_connection  # type: ignore

        try:
            with get_connection() as cn:
                cur = cn.cursor()

                # Aktuelle maximale Versuchsnummer in dieser TrialSeries
                cur.execute(
                    "SELECT MAX(Versuchsnummer) FROM tblTrial WHERE TrialSeriesID = ?",
                    (series_id,),
                )
                row = cur.fetchone()
                max_v = int(row[0]) if row and row[0] is not None else 0

                # Quell-Trial holen
                cur.execute("SELECT * FROM tblTrial WHERE ID = ?",
                            (src_trial_id,))
                src_row = cur.fetchone()
                if not src_row:
                    raise RuntimeError("Quell-Trial nicht gefunden.")

                col_names = [c[0] for c in cur.description]
                src_map = dict(zip(col_names, src_row))

                # ID / TrialSeriesID / Versuchsnummer werden explizit gesetzt
                # Zusätzlich: berechnete / schreibgeschützte Felder (z. B. "D/Y Ratio (T2/T1)") nicht setzen
                skip_lower = {
                    "id",  # Primärschlüssel nie kopieren
                    # TrialSeriesID und Versuchsnummer werden explizit gesetzt,
                    # deshalb NICHT hier überspringen.
                    "d/y ratio (t2/t1)",  # berechnetes Feld in Access
                    # DATETIME/TIMESTAMP-Spalten nie 1:1 kopieren (MySQL akzeptiert kein '0')
                    "timestamp",
                    "createdat",
                    "updatedat",
                }
                # optionale GlobalID-Spalte nicht direkt kopieren
                gid_col = None
                for c in col_names:
                    if c.lower() == "globalid":
                        gid_col = c
                        skip_lower.add("globalid")
                        break
                insert_cols = [c for c in col_names if c.lower()
                               not in skip_lower]

                for _ in range(copies):
                    max_v += 1  # nächste freie Versuchsnummer

                    values = []
                    for col in insert_cols:
                        cl = col.lower()
                        if cl == "trialseriesid":
                            values.append(series_id)
                        elif cl == "versuchsnummer":
                            values.append(max_v)
                        else:
                            values.append(src_map.get(col))

                    cols_for_insert = list(insert_cols)
                    vals_for_insert = list(values)
                    if gid_col:
                        cols_for_insert.append(gid_col)
                        vals_for_insert.append(new_global_id())
                    cols_sql = ", ".join(f"[{c}]" for c in cols_for_insert)
                    ph = ", ".join("?" for _ in cols_for_insert)
                    cur.execute(
                        f"INSERT INTO tblTrial ({cols_sql}) VALUES ({ph})",
                        vals_for_insert,
                    )
                    # neue ID holen (Access-ODBC)
                    cur.execute("SELECT @@IDENTITY")
                    new_id_row = cur.fetchone()
                    new_trial_id = int(new_id_row[0]) if new_id_row else None
                    if not new_trial_id:
                        raise RuntimeError(
                            "Neue Trial-ID konnte nicht ermittelt werden.")

                    # Labor-Datensätze für diesen Trial kopieren
                    self._clone_lab_rows_for_trial(
                        cur, src_trial_id, new_trial_id)

                    # tblTrialSettings-Zeilen (Ply-Daten) kopieren
                    self._clone_trial_settings_rows(
                        cur, src_trial_id, new_trial_id)

        except Exception as e:
            QMessageBox.warning(
                self,
                "Fehler beim Kopieren",
                f"Die Trials konnten nicht kopiert werden:\n{e}",
            )
            return

        # Modelle erneut laden, damit neue Trials in allen Tabs erscheinen
        self._load_trials()
        self._build_machine_tab()
        self._build_titer_tab()
        self._build_jet_air_tab()
        self._build_statimat_tab()
        self._build_waterbath_tab()
        self._build_rapid600_tab()
        self._build_itemat_tab()
        self._build_itemat_plus_tab()
        self._build_dtyomat_tab()
        self._build_atyomat_tab()

        QMessageBox.information(
            self,
            "Trials kopiert",
            f"{copies} Kopie(n) von Trial {self._trial_labels[trial_index]} wurden erstellt.",
        )

    def _on_print_trial_labels(self) -> None:
        """Druckt Labels mit der Versuchsnummer (z.B. 'V23') fuer die Trials
        der aktuellen Series. Eigenes Template ('TrialLabel'), unabhaengig
        vom Spulen-Label-Template im Garnlager (andere Bogengroesse)."""
        series_pk = getattr(self, "_series_pk", None)
        if not series_pk:
            QMessageBox.information(self, "Print Labels", "No series loaded.")
            return
        if not table_exists("tbltrial"):
            return
        try:
            rows = fetch_all(
                "SELECT MIN([Versuchsnummer]) AS mn, MAX([Versuchsnummer]) AS mx "
                "FROM tbltrial WHERE [TrialSeriesID] = ?", [series_pk])
        except Exception:
            rows = []
        if not rows or rows[0].get("mn") is None:
            QMessageBox.information(self, "Print Labels", "No trials in this series.")
            return
        mn, mx = int(rows[0]["mn"]), int(rows[0]["mx"])

        # "ExperimentID.SS" (erste 2 Zeichen des Series-Namens) fuer die
        # Kopfzeile ueber der Versuchsnummer - gilt fuer die ganze Series,
        # also nur einmal abfragen statt pro Trial.
        header_txt = ""
        try:
            hrows = fetch_all(
                "SELECT e.[ExperimentID] AS ExpId, s.[SeriesName] AS SeriesName "
                "FROM tbltrialseries s "
                "LEFT JOIN tblexperimente e ON e.[ID] = s.[ExperimentID] "
                "WHERE s.[ID] = ?", [series_pk])
            if hrows:
                exp_id = hrows[0].get("ExpId")
                series_name = str(hrows[0].get("SeriesName") or "")
                if exp_id is not None:
                    header_txt = f"{exp_id}.{series_name[:2]}"
        except Exception:
            header_txt = ""

        template = load_label_template("TrialLabel")

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
        items = [{"TrialNr": n, "Header": header_txt} for n in range(f, t + 1)]

        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save label PDF", "trial_labels.pdf", "PDF Files (*.pdf)")
        if not out_path:
            return
        try:
            generate_label_sheet_pdf(items, tpl, start_index, out_path, draw_cell=_draw_trial_label_cell)
        except Exception as e:
            QMessageBox.critical(self, "Print Labels", f"Failed to generate PDF: {e}")
            return
        QMessageBox.information(self, "Print Labels", f"Saved to:\n{out_path}")

    def _add_empty_trial(self) -> None:
        """Navigiert zu CreateExperimentScreen im addtrials-Modus."""
        if self._series_pk is None or self._exp_pk is None:
            return
        if callable(getattr(self, "on_add_trials", None)):
            self.on_add_trials(self._exp_pk, self._series_pk, getattr(self, "_experiment_id_txt", ""))
        else:
            QMessageBox.information(self, "Info", "Navigation nicht konfiguriert.")

    def _clone_lab_rows_for_trial(self, cur, src_trial_id: int, new_trial_id: int) -> None:
        """Klont alle Labor-Datensätze von src_trial_id auf new_trial_id.

        - Struktur / Parameter (z.B. Tension) werden übernommen
        - eigentliche Messwerte werden auf NULL gesetzt
        """
        lab_tables = [
            ("tbllabortiter", "TrialID"),
            ("tbllaborstatimatm", "TrialID"),
            ("tbllaborstatimatds", "TrialID"),
            ("tblLaborWaterbath", "TrialID"),
            ("tblLaborItematLab", "TrialID"),
            ("tblLaborItematPlus", "TrialID"),
            ("tblLaborRapid600", "TrialID"),
            ("tblLaborDTYoMat", "TrialID"),
            ("tblLaborATYoMat", "TrialID"),
            ("tblLaborEKB", "TrialID"),
            ("tblLaborHeissLuftSchrumpf", "TrialID"),
            ("tblLaborKochSchrumpf", "TrialID"),
            ("tblLaborATYShrinkage", "TrialID"),
        ]

        for table_name, trial_col in lab_tables:
            # prüfen, ob Tabelle existiert (MySQL)
            if not _db_table_exists(table_name.lower()):
                continue

            cur.execute(
                f"SELECT * FROM {table_name} WHERE {trial_col} = ?",
                (src_trial_id,),
            )
            rows = cur.fetchall()
            if not rows:
                continue

            col_names = [c[0] for c in cur.description]

            # ID + TrialID nicht direkt übernehmen
            skip_lower = {"id", trial_col.lower()}
            gid_col = None
            for c in col_names:
                if c.lower() == "globalid":
                    gid_col = c
                    skip_lower.add("globalid")
                    break
            insert_cols = [c for c in col_names if c.lower() not in skip_lower]

            def _is_zero_datetime(v: Any) -> bool:
                """Detect common 'zero' datetime placeholders (e.g. 0 or '0')."""
                if v is None:
                    return False
                if isinstance(v, (int, float)):
                    return v == 0
                if isinstance(v, str):
                    return v.strip() in ("", "0", "0000-00-00", "0000-00-00 00:00:00")
                return False

            current_uid = None
            try:
                current_uid = self._current_user_id()
            except Exception:
                current_uid = None

            for row in rows:
                row_map = dict(zip(col_names, row))
                values = []
                for col in insert_cols:
                    cl = col.lower()
                    v = row_map.get(col)

                    # --- keep/correct meta + FK fields so we don't violate constraints ---
                    if cl.endswith("id"):
                        # keep foreign keys (e.g. UserID, InstrumentID, ...) intact
                        # but if it is a UserID placeholder (0), map to current user if available.
                        if "user" in cl and _is_zero_datetime(v):
                            values.append(current_uid if current_uid not in (None, "") else None)
                        elif "user" in cl and v in (0, "0", "", None):
                            values.append(current_uid if current_uid not in (None, "") else None)
                        else:
                            values.append(v)
                        continue

                    if "createdby" in cl:
                        values.append(current_uid if current_uid not in (None, "") else v)
                        continue

                    if any(k in cl for k in ("createdat", "updatedat", "timestamp")):
                        # give cloned rows a fresh timestamp if the source contains an invalid placeholder
                        values.append(datetime.datetime.now() if _is_zero_datetime(v) else v)
                        continue

                    if any(k in cl for k in ("date", "time")):
                        # never insert 0 into date/time-like columns
                        values.append(None if _is_zero_datetime(v) else v)
                        continue

                    # --- keep parameter columns, null measurement columns ---
                    # Keep obvious setting columns; everything else becomes NULL.
                    if "tension" in cl:
                        values.append(v)
                    else:
                        values.append(None)

                cols_for_insert = [trial_col] + list(insert_cols)
                vals_for_insert = [new_trial_id] + values
                if gid_col:
                    cols_for_insert.append(gid_col)
                    vals_for_insert.append(new_global_id())
                cols_sql = ", ".join(
                    f"[{c}]" for c in cols_for_insert)
                ph = ", ".join("?" for _ in cols_for_insert)
                cur.execute(
                    f"INSERT INTO [{table_name}] ({cols_sql}) VALUES ({ph})",
                    vals_for_insert,
                )

    def _clone_trial_settings_rows(self, cur, src_trial_id: int, new_trial_id: int) -> None:
        """Klont alle tblTrialSettings-Zeilen von src_trial_id auf new_trial_id.

        Alle Felder (inkl. Ply-Parameter wie 1stHeaterT1/T2, YarnTensionT1/T2 usw.)
        werden 1:1 übernommen. Nur ID und TrialID werden neu gesetzt.
        """
        if not _db_table_exists("tbltrialsettings"):
            return

        cur.execute(
            "SELECT * FROM tblTrialSettings WHERE TrialID = ?",
            (src_trial_id,),
        )
        rows = cur.fetchall()
        if not rows:
            return

        col_names = [c[0] for c in cur.description]

        skip_lower = {"id", "trialid"}
        gid_col = None
        for c in col_names:
            if c.lower() == "globalid":
                gid_col = c
                skip_lower.add("globalid")
                break
        insert_cols = [c for c in col_names if c.lower() not in skip_lower]

        for row in rows:
            row_map = dict(zip(col_names, row))
            values = [row_map.get(c) for c in insert_cols]

            cols_for_insert = ["TrialID"] + list(insert_cols)
            vals_for_insert = [new_trial_id] + values
            if gid_col:
                cols_for_insert.append(gid_col)
                vals_for_insert.append(new_global_id())

            cols_sql = ", ".join(f"[{c}]" for c in cols_for_insert)
            ph = ", ".join("?" for _ in cols_for_insert)
            cur.execute(
                f"INSERT INTO [tblTrialSettings] ({cols_sql}) VALUES ({ph})",
                vals_for_insert,
            )

    def _get_jet_info_rows(self) -> list:
        """3 Zeilen (label, [wert_pro_trial]) für Jet / Jet Plate / Air Pressure.
        Lädt direkt aus DB – unabhängig vom Machine Tab."""
        trial_ids = getattr(self, "_trial_ids", []) or []
        if not trial_ids:
            return [("Jet", []), ("Jet Plate", []), ("Air Pressure", [])]
        try:
            placeholders = ",".join(["?"] * len(trial_ids))
            # Jet name via JOIN auf tblDTYJets
            jet_rows = fetch_all(
                f"SELECT T.ID, T.Versuchsnummer, J.Jet AS JetName, "
                f"T.JetPlate, T.AirPressure "
                f"FROM tblTrial AS T "
                f"LEFT JOIN tblDTYJets AS J ON J.ID = T.JetID "
                f"WHERE T.ID IN ({placeholders}) "
                f"ORDER BY T.Versuchsnummer",
                trial_ids,
            )
            by_id = {int(r["ID"]): r for r in jet_rows}
            # Preserve order of self._trial_ids
            ordered = [by_id.get(int(tid), {}) for tid in trial_ids]
            jets = [str(r.get("JetName") or "") for r in ordered]
            plates = [str(r.get("JetPlate") or "") for r in ordered]
            airs = [str(r.get("AirPressure") or "") for r in ordered]
            return [("Jet", jets), ("Jet Plate", plates), ("Air Pressure", airs)]
        except Exception:
            n = len(trial_ids)
            return [("Jet", [""] * n), ("Jet Plate", [""] * n), ("Air Pressure", [""] * n)]

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
        self.tbl_titer = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_titer)
        self._enable_paste_for_table(self.tbl_titer)
        self.tbl_titer.verticalHeader().setVisible(False)
        self.tbl_titer.setStyleSheet(_titer_qss)
        self.tbl_titer.horizontalHeader().setMinimumSectionSize(90)
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

    def _build_titer_tab(self):
        # Tabelle kann je nach Schema unterschiedlich heissen
        titer_table = None
        for _cand in ("tbltiter", "tblLaborTiter"):
            if table_exists(_cand):
                titer_table = _cand
                break

        if not titer_table or not self._trial_ids:
            self._remove_titer_tab_if_exists()
            return

        titer_cols = get_columns_map(titer_table)
        col_titer = resolve_field(["Titer", "Titer (dtex)", "Titer(dtex)"], titer_cols)
        if not col_titer:
            self._remove_titer_tab_if_exists()
            return

        rows = fetch_all(
            f"""
            SELECT LT.ID, LT.TrialID, LT.[{col_titer}] AS Titer
            FROM {titer_table} AS LT
            WHERE LT.TrialID IN ({",".join(["?"] * len(self._trial_ids))})
            """,
            self._trial_ids,
        )

        if not rows:
            self._remove_titer_tab_if_exists()
            return

        self._ensure_titer_tab()

        self.model_titer = PivotEditModel(
            row_titles=["Titer (dtex)"],
            col_titles=self._trial_labels,
            row_validators=["onlyDoubles"],  # nur Zahlen (mit Komma/Punkt)
        )
        by_trial = defaultdict(dict)
        for r in rows:
            by_trial[int(r["TrialID"])] = r

        for c_idx, trial in enumerate(self._trials):
            rec = by_trial.get(trial["ID"])
            if rec:
                binding = CellBinding(
                    titer_table, "ID", rec["ID"], col_titer)
                self.model_titer.set_cell(
                    0, c_idx, rec.get("Titer"), binding)
            else:
                self.model_titer.set_cell(0, c_idx, None, None)

        self.tbl_titer.setModel(self.model_titer)
        self.model_titer.insert_readonly_rows_at_top(self._get_jet_info_rows())
        self._register_save_model("model_titer")
        self.tbl_titer.resizeColumnsToContents()

        # ── Soll-Titer aus Trial 1 berechnen (einmalig für die ganze Series) ──
        self._titer_out_of_tolerance: set = set()  # c_idx der auffälligen Trials
        try:
            first_trial_id = self._trials[0]["ID"] if self._trials else None
            if first_trial_id is not None:
                yarn_rows = fetch_all(
                    "SELECT YarnID FROM tbltrialsettings WHERE TrialID = ?",
                    [first_trial_id],
                )
                yarn_ids = [r["YarnID"] for r in yarn_rows if r.get("YarnID") is not None]
                soll_titer = None
                if yarn_ids:
                    # Lookup: eindeutige YarnIDs -> Endtiter
                    unique_ids = list(set(yarn_ids))
                    placeholders = ",".join(["?"] * len(unique_ids))
                    titer_rows = fetch_all(
                        f"SELECT ID, Endtiter FROM tblyarn WHERE ID IN ({placeholders})",
                        unique_ids,
                    )
                    endtiter_by_id = {}
                    for tr in titer_rows:
                        try:
                            endtiter_by_id[int(tr["ID"])] = float(tr["Endtiter"] or 0)
                        except Exception:
                            pass
                    # Summiere pro Vorkommen in yarn_ids (Duplikate = mehrere Plies desselben Garns)
                    total = 0.0
                    for yid in yarn_ids:
                        total += endtiter_by_id.get(int(yid), 0.0)
                    soll_titer = total if total > 0 else None

                if soll_titer:
                    lo = soll_titer * 0.95
                    hi = soll_titer * 1.05
                    for c_idx, trial in enumerate(self._trials):
                        rec = by_trial.get(trial["ID"])
                        if not rec:
                            continue
                        raw = rec.get("Titer")
                        if raw in (None, ""):
                            continue
                        try:
                            val = float(str(raw).replace(",", "."))
                        except Exception:
                            continue
                        if val < lo or val > hi:
                            self._titer_out_of_tolerance.add(c_idx)
                            self.model_titer.set_cell_alert(len(self._get_jet_info_rows()), c_idx, "red")
                    # Statimat DS Tenacity orange markieren (falls Modell schon existiert)
                    self._apply_titer_alert_to_stat_ds()
        except Exception:
            pass

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
        self.txt_jet_air_atm_fill.setPlaceholderText("Wert für alle Zellen")
        self.txt_jet_air_atm_fill.setFixedWidth(140)
        self.txt_jet_air_atm_fill.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"^\s*[+-]?\d+(?:[.,]\d+)?\s*$"), self))
        btn_atm_fill = QPushButton("Für alle übernehmen")
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
        self.txt_jet_air_temp_fill.setPlaceholderText("Wert für alle Zellen")
        self.txt_jet_air_temp_fill.setFixedWidth(140)
        self.txt_jet_air_temp_fill.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"^\s*[+-]?\d+(?:[.,]\d+)?\s*$"), self))
        btn_temp_fill = QPushButton("Für alle übernehmen")
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
                "Es gibt ungespeicherte Änderungen im Air-Consumption-Grid.\n"
                "Beim Einheitenwechsel gehen diese verloren. Fortfahren?",
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
        (beide mit "Fuer alle uebernehmen"). Eine Series-gemeinsame
        Druck-Liste wird mit allen physischen Duesen der Series gekreuzt
        (siehe _save_jet_air_consumption_rows in screen_create_experiment.py)."""
        table = "tblLaborJetAirConsumption"
        series_id = getattr(self, "_series_pk", None)
        if not table_exists(table) or not series_id:
            self._remove_jet_air_tab_if_exists()
            return

        rows = fetch_all(
            f"SELECT [ID], [JetID], [JetPlate], [AirPressure], [AirConsumption], "
            f"[AtmosphericPressure], [AirTemperature] "
            f"FROM {table} WHERE [TrialSeriesID] = ?",
            [series_id],
        )
        if not rows:
            self._remove_jet_air_tab_if_exists()
            return

        # Jet-Namen nachladen (gleiche Quelle wie _get_jet_info_rows)
        jet_ids = sorted({int(r["JetID"]) for r in rows if r.get("JetID") is not None})
        jet_name_map: Dict[int, str] = {}
        try:
            if jet_ids and table_exists("tblDTYJets"):
                ph = ",".join(["?"] * len(jet_ids))
                for jr in fetch_all(
                        f"SELECT [ID], [Jet] AS JName FROM tblDTYJets WHERE [ID] IN ({ph})", jet_ids):
                    jet_name_map[int(jr["ID"])] = str(jr.get("JName") or "")
        except Exception:
            pass

        def _plate_key(p):
            return "" if p is None else str(p)

        physical_jets = sorted(
            {(int(r["JetID"]), _plate_key(r.get("JetPlate")))
             for r in rows if r.get("JetID") is not None},
            key=lambda t: (jet_name_map.get(t[0], ""), t[1]),
        )
        pressures = sorted({float(r["AirPressure"]) for r in rows if r.get("AirPressure") is not None})

        if not physical_jets or not pressures:
            self._remove_jet_air_tab_if_exists()
            return

        row_titles = []
        for jid, plate in physical_jets:
            jname = jet_name_map.get(jid, f"Jet {jid}")
            row_titles.append(f"{jname} / Plate {plate}" if plate else jname)

        col_titles = [f"{p:g} bar" for p in pressures]

        self._ensure_jet_air_tab()

        by_key: Dict[Tuple[int, str, float], dict] = {}
        for r in rows:
            if r.get("JetID") is None or r.get("AirPressure") is None:
                continue
            key = (int(r["JetID"]), _plate_key(r.get("JetPlate")), round(float(r["AirPressure"]), 6))
            by_key[key] = r

        # 1 Nm3/h = 1000 l / 60 min = 16.6667 l/min
        LMIN_PER_NM3H = 1000.0 / 60.0
        use_lmin = (self._jet_air_unit == "lmin")

        # ── Air Consumption ──────────────────────────────────────────────
        self.model_jet_air = PivotEditModel(
            row_titles=row_titles, col_titles=col_titles,
            row_validators=["onlyDoubles"] * len(row_titles),
        )
        if use_lmin:
            self.model_jet_air.set_unit_scale(LMIN_PER_NM3H, "AirConsumption")
        for r_idx, (jid, plate) in enumerate(physical_jets):
            for c_idx, p in enumerate(pressures):
                rec = by_key.get((jid, plate, round(p, 6)))
                if rec:
                    binding = CellBinding(table, "ID", rec["ID"], "AirConsumption")
                    val = rec.get("AirConsumption")
                    disp = None
                    if val is not None:
                        v = float(val) * LMIN_PER_NM3H if use_lmin else float(val)
                        disp = f"{v:.2f}"
                    self.model_jet_air.set_cell(r_idx, c_idx, disp, binding)
                else:
                    self.model_jet_air.set_cell(r_idx, c_idx, None, None)
        self.tbl_jet_air.setModel(self.model_jet_air)
        self._register_save_model("model_jet_air")
        self.tbl_jet_air.resizeColumnsToContents()

        # ── Atmospheric Pressure ────────────────────────────────────────
        self.model_jet_air_atm = PivotEditModel(
            row_titles=row_titles, col_titles=col_titles,
            row_validators=["onlyDoubles"] * len(row_titles),
        )
        for r_idx, (jid, plate) in enumerate(physical_jets):
            for c_idx, p in enumerate(pressures):
                rec = by_key.get((jid, plate, round(p, 6)))
                if rec:
                    binding = CellBinding(table, "ID", rec["ID"], "AtmosphericPressure")
                    self.model_jet_air_atm.set_cell(r_idx, c_idx, rec.get("AtmosphericPressure"), binding)
                else:
                    self.model_jet_air_atm.set_cell(r_idx, c_idx, None, None)
        self.tbl_jet_air_atm.setModel(self.model_jet_air_atm)
        self._register_save_model("model_jet_air_atm")
        self.tbl_jet_air_atm.resizeColumnsToContents()

        # ── Air Temperature ─────────────────────────────────────────────
        self.model_jet_air_temp = PivotEditModel(
            row_titles=row_titles, col_titles=col_titles,
            row_validators=["onlyDoubles"] * len(row_titles),
        )
        for r_idx, (jid, plate) in enumerate(physical_jets):
            for c_idx, p in enumerate(pressures):
                rec = by_key.get((jid, plate, round(p, 6)))
                if rec:
                    binding = CellBinding(table, "ID", rec["ID"], "AirTemperature")
                    self.model_jet_air_temp.set_cell(r_idx, c_idx, rec.get("AirTemperature"), binding)
                else:
                    self.model_jet_air_temp.set_cell(r_idx, c_idx, None, None)
        self.tbl_jet_air_temp.setModel(self.model_jet_air_temp)
        self._register_save_model("model_jet_air_temp")
        self.tbl_jet_air_temp.resizeColumnsToContents()

    # ---------- Statimat M (nur sichtbar wenn Daten) ----------

    def _ensure_stat_tab(self):
        if self.tab_stat is not None:
            return
        self.tab_stat = QWidget()
        vs = QVBoxLayout(self.tab_stat)
        vs.setContentsMargins(24, 12, 24, 24)
        self.tbl_stat = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_stat)
        self._enable_paste_for_table(self.tbl_stat)
        self.tbl_stat.verticalHeader().setVisible(False)
        self.tbl_stat.horizontalHeader().setMinimumSectionSize(90)
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

    def _build_statimat_tab(self):
        # Tabelle kann je nach Schema unterschiedlich heissen
        stat_table = None
        for _cand in ("tbllaborstatimatm", "tblLaborStatimat", "tbllaborstatimat"):
            if table_exists(_cand):
                stat_table = _cand
                break

        if not stat_table or not self._trial_ids:
            self._remove_stat_tab_if_exists()
            return

        stat_cols = get_columns_map(stat_table)
        col_elong = resolve_field(
            ["Elongation (%)", "Elongation%", "Elongation"], stat_cols)
        col_elong_cv = resolve_field(
            ["Elongation CV (%)", "ElongationCV%", "ElongationCV"], stat_cols)
        col_ten = resolve_field(
            ["Tenacity (cN/dtex)", "Tenacity", "Tenacity(cN/dtex)"], stat_cols)
        col_ten_cv = resolve_field(
            ["Tenacity CV (%)", "TenacityCV%", "TenacityCV"], stat_cols)

        if not all([col_elong, col_elong_cv, col_ten, col_ten_cv]):
            self._remove_stat_tab_if_exists()
            return

        rows = fetch_all(
            f"""
            SELECT ID, TrialID,
                   [{col_elong}] AS Elong,
                   [{col_elong_cv}] AS ElongCV,
                   [{col_ten}] AS Ten,
                   [{col_ten_cv}] AS TenCV
            FROM {stat_table}
            WHERE TrialID IN ({",".join(["?"] * len(self._trial_ids))})
            """,
            self._trial_ids,
        )

        if not rows:
            self._remove_stat_tab_if_exists()
            return

        self._ensure_stat_tab()

        row_titles = [
            "Elongation (%)",
            "Elongation CV (%)",
            "Tenacity (cN/dtex)",
            "Tenacity CV (%)",
        ]
        self.model_stat = PivotEditModel(
            row_titles=row_titles,
            col_titles=self._trial_labels,
            row_validators=["onlyDoubles"] * len(row_titles),  # nur Zahlen
        )

        by_trial = {r["TrialID"]: r for r in rows}
        for c_idx, trial in enumerate(self._trials):
            rec = by_trial.get(trial["ID"])
            if rec:
                self.model_stat.set_cell(0, c_idx, rec.get("Elong"),
                                         CellBinding(stat_table, "ID", rec["ID"], col_elong))
                self.model_stat.set_cell(1, c_idx, rec.get("ElongCV"),
                                         CellBinding(stat_table, "ID", rec["ID"], col_elong_cv))
                self.model_stat.set_cell(2, c_idx, rec.get("Ten"),
                                         CellBinding(stat_table, "ID", rec["ID"], col_ten))
                self.model_stat.set_cell(3, c_idx, rec.get("TenCV"),
                                         CellBinding(stat_table, "ID", rec["ID"], col_ten_cv))
            else:
                self.model_stat.set_cell(0, c_idx, None, None)
                self.model_stat.set_cell(1, c_idx, None, None)
                self.model_stat.set_cell(2, c_idx, None, None)
                self.model_stat.set_cell(3, c_idx, None, None)

        self.tbl_stat.setModel(self.model_stat)
        self.model_stat.insert_readonly_rows_at_top(self._get_jet_info_rows())
        self._register_save_model("model_stat")
        self.tbl_stat.resizeColumnsToContents()

    # ---------- Statimat DS (nur sichtbar wenn Daten) ----------

    def _ensure_stat_ds_tab(self):
        if self.tab_stat_ds is not None:
            return
        self.tab_stat_ds = QWidget()
        vs = QVBoxLayout(self.tab_stat_ds)
        vs.setContentsMargins(24, 12, 24, 24)
        self.tbl_stat_ds = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_stat_ds)
        self._enable_paste_for_table(self.tbl_stat_ds)
        self.tbl_stat_ds.verticalHeader().setVisible(False)
        self.tbl_stat_ds.horizontalHeader().setMinimumSectionSize(90)
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

    def _build_statimat_ds_tab(self):
        # Tabelle kann je nach Schema unterschiedlich heissen
        stat_ds_table = None
        for _cand in ("tbllaborstatimatds", "tblLaborStatimatDS"):
            if table_exists(_cand):
                stat_ds_table = _cand
                break

        if not stat_ds_table or not self._trial_ids:
            self._remove_stat_ds_tab_if_exists()
            return

        stat_cols = get_columns_map(stat_ds_table)
        col_elong = resolve_field(
            ["Elongation (%)", "Elongation%", "Elongation"], stat_cols)
        col_elong_cv = resolve_field(
            ["Elongation CV (%)", "ElongationCV%", "ElongationCV"], stat_cols)
        col_ten = resolve_field(
            ["Tenacity (cN/dtex)", "Tenacity", "Tenacity(cN/dtex)"], stat_cols)
        col_ten_cv = resolve_field(
            ["Tenacity CV (%)", "TenacityCV%", "TenacityCV"], stat_cols)

        if not all([col_elong, col_elong_cv, col_ten, col_ten_cv]):
            self._remove_stat_ds_tab_if_exists()
            return

        rows = fetch_all(
            f"""
            SELECT ID, TrialID,
                   [{col_elong}] AS Elong,
                   [{col_elong_cv}] AS ElongCV,
                   [{col_ten}] AS Ten,
                   [{col_ten_cv}] AS TenCV
            FROM {stat_ds_table}
            WHERE TrialID IN ({",".join(["?"] * len(self._trial_ids))})
            """,
            self._trial_ids,
        )

        if not rows:
            self._remove_stat_ds_tab_if_exists()
            return

        self._ensure_stat_ds_tab()

        row_titles = [
            "Elongation (%)",
            "Elongation CV (%)",
            "Tenacity (cN/dtex)",
            "Tenacity CV (%)",
        ]
        self.model_stat_ds = PivotEditModel(
            row_titles=row_titles,
            col_titles=self._trial_labels,
            row_validators=["onlyDoubles"] * len(row_titles),  # nur Zahlen
        )

        by_trial = {r["TrialID"]: r for r in rows}
        for c_idx, trial in enumerate(self._trials):
            rec = by_trial.get(trial["ID"])
            if rec:
                self.model_stat_ds.set_cell(0, c_idx, rec.get("Elong"),
                                            CellBinding(stat_ds_table, "ID", rec["ID"], col_elong))
                self.model_stat_ds.set_cell(1, c_idx, rec.get("ElongCV"),
                                            CellBinding(stat_ds_table, "ID", rec["ID"], col_elong_cv))
                self.model_stat_ds.set_cell(2, c_idx, rec.get("Ten"),
                                            CellBinding(stat_ds_table, "ID", rec["ID"], col_ten))
                self.model_stat_ds.set_cell(3, c_idx, rec.get("TenCV"),
                                            CellBinding(stat_ds_table, "ID", rec["ID"], col_ten_cv))
            else:
                self.model_stat_ds.set_cell(0, c_idx, None, None)
                self.model_stat_ds.set_cell(1, c_idx, None, None)
                self.model_stat_ds.set_cell(2, c_idx, None, None)
                self.model_stat_ds.set_cell(3, c_idx, None, None)

        self.tbl_stat_ds.setModel(self.model_stat_ds)
        self.model_stat_ds.insert_readonly_rows_at_top(self._get_jet_info_rows())
        self._register_save_model("model_stat_ds")
        self.tbl_stat_ds.resizeColumnsToContents()

        # Orange-Alerts für Tenacity falls Titer-Abweichungen bereits bekannt
        self._apply_titer_alert_to_stat_ds()

    # ---------- EKB (sichtbar nur bei Daten) ----------

    def _ensure_ekb_tab(self):
        if self.tab_ekb is not None:
            return
        self.tab_ekb = QWidget()
        vl = QVBoxLayout(self.tab_ekb)
        vl.setContentsMargins(24, 12, 24, 24)
        self.tbl_ekb = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_ekb)
        self._enable_paste_for_table(self.tbl_ekb)
        self.tbl_ekb.verticalHeader().setVisible(False)
        self.tbl_ekb.horizontalHeader().setMinimumSectionSize(110)
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

    def _build_ekb_tab(self):
        if not self._trial_ids or not table_exists("tblLaborEKB"):
            self._remove_ekb_tab_if_exists()
            return

        cols_map = get_columns_map("tblLaborEKB")

        col_e_x = resolve_field(
            ["EinkräuselungX", "Einkräuselung X"], cols_map)
        col_e_cv = resolve_field(
            ["EinkräuselungCV", "Einkräuselung CV"], cols_map)
        col_k_x = resolve_field(
            ["KennkräuselungX", "Kennkräuselung X"], cols_map)
        col_k_cv = resolve_field(
            ["KennkräuselungCV", "Kennkräuselung CV"], cols_map)
        col_b_x = resolve_field(
            ["KräuselbeständigkeitX", "Kräuselbeständigkeit X"], cols_map)
        col_b_cv = resolve_field(
            ["KräuselbeständigkeitCV", "Kräuselbeständigkeit CV"], cols_map)

        if not all([col_e_x, col_e_cv, col_k_x, col_k_cv, col_b_x, col_b_cv]):
            self._remove_ekb_tab_if_exists()
            return

        placeholders = ",".join(["?"] * len(self._trial_ids))
        rows = fetch_all(
            f"""
            SELECT
                [ID]       AS RecID,
                [TrialID],
                [{col_e_x}] AS E_X,
                [{col_e_cv}] AS E_CV,
                [{col_k_x}] AS K_X,
                [{col_k_cv}] AS K_CV,
                [{col_b_x}] AS B_X,
                [{col_b_cv}] AS B_CV
            FROM tblLaborEKB
            WHERE [TrialID] IN ({placeholders})
            """,
            self._trial_ids,
        )

        if not rows:
            self._remove_ekb_tab_if_exists()
            return

        by_trial = {int(r["TrialID"]): r for r in rows}

        row_titles = [
            "Einkräuselung X",
            "Einkräuselung CV",
            "Kennkräuselung X",
            "Kennkräuselung CV",
            "Kräuselbeständigkeit X",
            "Kräuselbeständigkeit CV",
        ]

        self._ensure_ekb_tab()

        self.model_ekb = PivotEditModel(
            row_titles=row_titles,
            col_titles=self._trial_labels,
            row_validators=["onlyDoubles"] * len(row_titles),
        )

        for c_idx, trial in enumerate(self._trials):
            tid = trial["ID"]
            rec = by_trial.get(tid)
            if rec:
                rec_id = rec["RecID"]
                self.model_ekb.set_cell(
                    0, c_idx, rec.get("E_X"),
                    CellBinding("tblLaborEKB", "ID", rec_id, col_e_x),
                )
                self.model_ekb.set_cell(
                    1, c_idx, rec.get("E_CV"),
                    CellBinding("tblLaborEKB", "ID", rec_id, col_e_cv),
                )
                self.model_ekb.set_cell(
                    2, c_idx, rec.get("K_X"),
                    CellBinding("tblLaborEKB", "ID", rec_id, col_k_x),
                )
                self.model_ekb.set_cell(
                    3, c_idx, rec.get("K_CV"),
                    CellBinding("tblLaborEKB", "ID", rec_id, col_k_cv),
                )
                self.model_ekb.set_cell(
                    4, c_idx, rec.get("B_X"),
                    CellBinding("tblLaborEKB", "ID", rec_id, col_b_x),
                )
                self.model_ekb.set_cell(
                    5, c_idx, rec.get("B_CV"),
                    CellBinding("tblLaborEKB", "ID", rec_id, col_b_cv),
                )
            else:
                for r_idx in range(len(row_titles)):
                    self.model_ekb.set_cell(r_idx, c_idx, None, None)

        if self.tbl_ekb is not None:
            self.tbl_ekb.setModel(self.model_ekb)
            self.model_ekb.insert_readonly_rows_at_top(self._get_jet_info_rows())
            self._register_save_model("model_ekb")
            self.tbl_ekb.resizeColumnsToContents()

    # ---------- Hot Air Shrinkage (sichtbar nur bei Daten) ----------

    def _ensure_hot_air_shrinkage_tab(self):
        if self.tab_hot_air_shrinkage is not None:
            return
        self.tab_hot_air_shrinkage = QWidget()
        vl = QVBoxLayout(self.tab_hot_air_shrinkage)
        vl.setContentsMargins(24, 12, 24, 24)
        self.tbl_hot_air_shrinkage = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_hot_air_shrinkage)
        self._enable_paste_for_table(self.tbl_hot_air_shrinkage)
        self.tbl_hot_air_shrinkage.verticalHeader().setVisible(False)
        self.tbl_hot_air_shrinkage.horizontalHeader().setMinimumSectionSize(110)
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

    def _build_hot_air_shrinkage_tab(self):
        table_name = "tblLaborHeissLuftSchrumpf"
        if not self._trial_ids or not table_exists(table_name):
            self._remove_hot_air_shrinkage_tab_if_exists()
            return

        cols_map = get_columns_map(table_name)
        col_x = resolve_field(["ShrinkageX", "Shrinkage X"], cols_map)
        col_cv = resolve_field(["ShrinkageCV", "Shrinkage CV"], cols_map)

        if not all([col_x, col_cv]):
            self._remove_hot_air_shrinkage_tab_if_exists()
            return

        placeholders = ",".join(["?"] * len(self._trial_ids))
        rows = fetch_all(
            f"""
            SELECT
                [ID]       AS RecID,
                [TrialID],
                [{col_x}] AS X,
                [{col_cv}] AS CV
            FROM {table_name}
            WHERE [TrialID] IN ({placeholders})
            """,
            self._trial_ids,
        )

        if not rows:
            self._remove_hot_air_shrinkage_tab_if_exists()
            return

        by_trial = {int(r["TrialID"]): r for r in rows}

        row_titles = ["Shrinkage X", "Shrinkage CV"]

        self._ensure_hot_air_shrinkage_tab()

        self.model_hot_air_shrinkage = PivotEditModel(
            row_titles=row_titles,
            col_titles=self._trial_labels,
            row_validators=["onlyDoubles"] * len(row_titles),
        )

        for c_idx, trial in enumerate(self._trials):
            tid = trial["ID"]
            rec = by_trial.get(tid)
            if rec:
                rec_id = rec["RecID"]
                self.model_hot_air_shrinkage.set_cell(
                    0, c_idx, rec.get("X"),
                    CellBinding(table_name, "ID", rec_id, col_x),
                )
                self.model_hot_air_shrinkage.set_cell(
                    1, c_idx, rec.get("CV"),
                    CellBinding(table_name, "ID", rec_id, col_cv),
                )
            else:
                for r_idx in range(len(row_titles)):
                    self.model_hot_air_shrinkage.set_cell(
                        r_idx, c_idx, None, None)

        if self.tbl_hot_air_shrinkage is not None:
            self.tbl_hot_air_shrinkage.setModel(self.model_hot_air_shrinkage)
            self.model_hot_air_shrinkage.insert_readonly_rows_at_top(self._get_jet_info_rows())
            self._register_save_model("model_hot_air_shrinkage")
            self.tbl_hot_air_shrinkage.resizeColumnsToContents()

    # ---------- Hot Water Shrinkage (sichtbar nur bei Daten) ----------

    def _ensure_hot_water_shrinkage_tab(self):
        if self.tab_hot_water_shrinkage is not None:
            return
        self.tab_hot_water_shrinkage = QWidget()
        vl = QVBoxLayout(self.tab_hot_water_shrinkage)
        vl.setContentsMargins(24, 12, 24, 24)
        self.tbl_hot_water_shrinkage = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_hot_water_shrinkage)
        self._enable_paste_for_table(self.tbl_hot_water_shrinkage)
        self.tbl_hot_water_shrinkage.verticalHeader().setVisible(False)
        self.tbl_hot_water_shrinkage.horizontalHeader().setMinimumSectionSize(110)
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

    def _build_hot_water_shrinkage_tab(self):
        table_name = "tblLaborKochSchrumpf"
        if not self._trial_ids or not table_exists(table_name):
            self._remove_hot_water_shrinkage_tab_if_exists()
            return

        cols_map = get_columns_map(table_name)
        col_x = resolve_field(["ShrinkageX", "Shrinkage X"], cols_map)
        col_cv = resolve_field(["ShrinkageCV", "Shrinkage CV"], cols_map)

        if not all([col_x, col_cv]):
            self._remove_hot_water_shrinkage_tab_if_exists()
            return

        placeholders = ",".join(["?"] * len(self._trial_ids))
        rows = fetch_all(
            f"""
            SELECT
                [ID]       AS RecID,
                [TrialID],
                [{col_x}] AS X,
                [{col_cv}] AS CV
            FROM {table_name}
            WHERE [TrialID] IN ({placeholders})
            """,
            self._trial_ids,
        )

        if not rows:
            self._remove_hot_water_shrinkage_tab_if_exists()
            return

        by_trial = {int(r["TrialID"]): r for r in rows}

        row_titles = ["Shrinkage X", "Shrinkage CV"]

        self._ensure_hot_water_shrinkage_tab()

        self.model_hot_water_shrinkage = PivotEditModel(
            row_titles=row_titles,
            col_titles=self._trial_labels,
            row_validators=["onlyDoubles"] * len(row_titles),
        )

        for c_idx, trial in enumerate(self._trials):
            tid = trial["ID"]
            rec = by_trial.get(tid)
            if rec:
                rec_id = rec["RecID"]
                self.model_hot_water_shrinkage.set_cell(
                    0, c_idx, rec.get("X"),
                    CellBinding(table_name, "ID", rec_id, col_x),
                )
                self.model_hot_water_shrinkage.set_cell(
                    1, c_idx, rec.get("CV"),
                    CellBinding(table_name, "ID", rec_id, col_cv),
                )
            else:
                for r_idx in range(len(row_titles)):
                    self.model_hot_water_shrinkage.set_cell(
                        r_idx, c_idx, None, None)

        if self.tbl_hot_water_shrinkage is not None:
            self.tbl_hot_water_shrinkage.setModel(
                self.model_hot_water_shrinkage)
            self.model_hot_water_shrinkage.insert_readonly_rows_at_top(self._get_jet_info_rows())
            self._register_save_model("model_hot_water_shrinkage")
            self.tbl_hot_water_shrinkage.resizeColumnsToContents()

    # ---------- ATY Shrinkage (sichtbar nur bei Daten) ----------

    def _ensure_aty_shrinkage_tab(self):
        if self.tab_aty_shrinkage is not None:
            return
        self.tab_aty_shrinkage = QWidget()
        vl = QVBoxLayout(self.tab_aty_shrinkage)
        vl.setContentsMargins(24, 12, 24, 24)
        self.tbl_aty_shrinkage = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_aty_shrinkage)
        self._enable_paste_for_table(self.tbl_aty_shrinkage)
        self.tbl_aty_shrinkage.verticalHeader().setVisible(False)
        self.tbl_aty_shrinkage.horizontalHeader().setMinimumSectionSize(110)
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

    def _build_aty_shrinkage_tab(self):
        table_name = "tblLaborATYShrinkage"
        if not self._trial_ids or not table_exists(table_name):
            self._remove_aty_shrinkage_tab_if_exists()
            return

        cols_map = get_columns_map(table_name)
        col_x = resolve_field(["ShrinkageX", "Shrinkage X"], cols_map)
        col_cv = resolve_field(["ShrinkageCV", "Shrinkage CV"], cols_map)

        if not all([col_x, col_cv]):
            self._remove_aty_shrinkage_tab_if_exists()
            return

        placeholders = ",".join(["?"] * len(self._trial_ids))
        rows = fetch_all(
            f"""
            SELECT
                [ID]       AS RecID,
                [TrialID],
                [{col_x}] AS X,
                [{col_cv}] AS CV
            FROM {table_name}
            WHERE [TrialID] IN ({placeholders})
            """,
            self._trial_ids,
        )

        if not rows:
            self._remove_aty_shrinkage_tab_if_exists()
            return

        by_trial = {int(r["TrialID"]): r for r in rows}

        row_titles = ["Shrinkage X", "Shrinkage CV"]

        self._ensure_aty_shrinkage_tab()

        self.model_aty_shrinkage = PivotEditModel(
            row_titles=row_titles,
            col_titles=self._trial_labels,
            row_validators=["onlyDoubles"] * len(row_titles),
        )

        for c_idx, trial in enumerate(self._trials):
            tid = trial["ID"]
            rec = by_trial.get(tid)
            if rec:
                rec_id = rec["RecID"]
                self.model_aty_shrinkage.set_cell(
                    0, c_idx, rec.get("X"),
                    CellBinding(table_name, "ID", rec_id, col_x),
                )
                self.model_aty_shrinkage.set_cell(
                    1, c_idx, rec.get("CV"),
                    CellBinding(table_name, "ID", rec_id, col_cv),
                )
            else:
                for r_idx in range(len(row_titles)):
                    self.model_aty_shrinkage.set_cell(r_idx, c_idx, None, None)

        if self.tbl_aty_shrinkage is not None:
            self.tbl_aty_shrinkage.setModel(self.model_aty_shrinkage)
            self.model_aty_shrinkage.insert_readonly_rows_at_top(self._get_jet_info_rows())
            self._register_save_model("model_aty_shrinkage")
            self.tbl_aty_shrinkage.resizeColumnsToContents()

    # ---------- Waterbath (fixe Spaltennamen) ----------

    def _ensure_waterbath_tab(self):
        if self.tab_water is not None:
            return
        self.tab_water = QWidget()
        lw = QVBoxLayout(self.tab_water)
        lw.setContentsMargins(24, 12, 24, 24)
        self.tbl_water = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_water)
        self._enable_paste_for_table(self.tbl_water)
        self.tbl_water.verticalHeader().setVisible(False)
        self.tbl_water.horizontalHeader().setMinimumSectionSize(90)
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

    def _build_waterbath_tab(self):
        if not self._trial_ids:
            self._remove_waterbath_tab_if_exists()
            return
        table_name = "tblLaborWaterbath"
        id_col = "ID"
        trial_col = "TrialID"
        inter_col = "Intermingling Points (FP/m)"
        placeholders = ",".join(["?"] * len(self._trial_ids))
        rows = fetch_all(
            f"""
            SELECT [{id_col}] AS RecID,
                   [{trial_col}] AS WBTrialID,
                   [{inter_col}] AS WBValue
            FROM {table_name}
            WHERE [{trial_col}] IN ({placeholders})
            ORDER BY [{trial_col}], [{id_col}]
            """,
            self._trial_ids,
        )
        if not rows:
            self._remove_waterbath_tab_if_exists()
            return
        self._ensure_waterbath_tab()
        row_titles = ["Intermingling 1", "Intermingling 2", "Intermingling 3"]
        self.model_water = PivotEditModel(
            row_titles=row_titles,
            col_titles=self._trial_labels,
            row_validators=["onlyDoubles"] * len(row_titles),  # nur Zahlen
        )
        per_trial: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for r in rows:
            per_trial[int(r["WBTrialID"])].append(r)
        for c_idx, trial in enumerate(self._trials):
            tid = trial["ID"]
            vals = per_trial.get(tid, [])
            for i in range(3):
                if i < len(vals):
                    rec = vals[i]
                    self.model_water.set_cell(
                        i, c_idx,
                        rec.get("WBValue"),
                        CellBinding(table_name, id_col,
                                    rec["RecID"], inter_col),
                    )
                else:
                    self.model_water.set_cell(i, c_idx, None, None)
        self.tbl_water.setModel(self.model_water)
        self.model_water.insert_readonly_rows_at_top(self._get_jet_info_rows())
        self._register_save_model("model_water")
        self.tbl_water.resizeColumnsToContents()

    # ---------- Itemat Lab (sichtbar nur bei Daten) ----------

    def _ensure_itemat_tab(self):
        if self.tab_itemat is not None:
            return
        self.tab_itemat = QWidget()
        vl = QVBoxLayout(self.tab_itemat)
        vl.setContentsMargins(24, 12, 24, 24)
        self.tbl_itemat = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_itemat)
        self._enable_paste_for_table(self.tbl_itemat)
        self.tbl_itemat.verticalHeader().setVisible(False)
        self.tbl_itemat.horizontalHeader().setMinimumSectionSize(110)
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
        self._itemat_tensions = []

    def _build_itemat_tab(self):
        if not self._trial_ids or not table_exists("tblLaborItematLab"):
            self._remove_itemat_tab_if_exists()
            return

        rows = fetch_all(
            f"""
            SELECT
                IL.ID AS RecID,
                IL.TrialID,
                IL.[Tension (cN/dtex)]     AS Tension,
                IL.[Intermingling Points (FP/m)]     AS IP,
                IL.[Intermingling Points CV (%)]     AS IPCV,
                IL.[Stability (%)]                   AS Stability
            FROM tblLaborItematLab AS IL
            WHERE IL.TrialID IN ({",".join(["?"] * len(self._trial_ids))})
            ORDER BY IL.TrialID, IL.[Tension (cN/dtex)], IL.ID
            """,
            self._trial_ids,
        )

        if not rows:
            self._remove_itemat_tab_if_exists()
            return

        by_trial: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        tensions_set: set[float] = set()
        for r in rows:
            by_trial[int(r["TrialID"])].append(r)
            try:
                t = float(str(r["Tension"]).replace(",", "."))
            except Exception:
                t = 0.0
            if t != 0.0:
                tensions_set.add(round(t, 2))

        tensions_sorted = sorted(tensions_set)
        self._itemat_tensions = tensions_sorted.copy()

        row_titles: List[str] = [
                                    "Intermingling Points (FP/m) @0.0 cN/dtex",
                                    "Intermingling Points CV (%) @0.0 cN/dtex",
                                ] + [f"Stability@{t:.1f} cN/dtex" for t in tensions_sorted]

        self.model_itemat = PivotEditModel(
            row_titles=row_titles,
            col_titles=self._trial_labels,
            row_validators=["onlyDoubles"] * len(row_titles),  # nur Zahlen
        )

        def find_record(trial_list: List[Dict[str, Any]], tension_value: float) -> Optional[Dict[str, Any]]:
            for rr in trial_list:
                try:
                    tt = float(str(rr["Tension"]).replace(",", "."))
                except Exception:
                    tt = 0.0
                if abs(tt - tension_value) < 1e-6:
                    return rr
            return None

        for c_idx, trial in enumerate(self._trials):
            tid = trial["ID"]
            recs = by_trial.get(tid, [])
            r0 = find_record(recs, 0.0)
            if r0:
                self.model_itemat.set_cell(
                    0, c_idx, r0.get("IP"),
                    CellBinding("tblLaborItematLab", "ID",
                                r0["RecID"], "Intermingling Points (FP/m)"),
                )
                self.model_itemat.set_cell(
                    1, c_idx, r0.get("IPCV"),
                    CellBinding("tblLaborItematLab", "ID",
                                r0["RecID"], "Intermingling Points CV (%)"),
                )
            else:
                self.model_itemat.set_cell(0, c_idx, None, None)
                self.model_itemat.set_cell(1, c_idx, None, None)

            for idx, tval in enumerate(tensions_sorted, start=2):
                rr = find_record(recs, tval)
                if rr:
                    self.model_itemat.set_cell(
                        idx, c_idx, rr.get("Stability"),
                        CellBinding("tblLaborItematLab", "ID",
                                    rr["RecID"], "Stability (%)"),
                    )
                else:
                    self.model_itemat.set_cell(idx, c_idx, None, None)

        self._ensure_itemat_tab()
        self.tbl_itemat.setModel(self.model_itemat)
        self.model_itemat.insert_readonly_rows_at_top(self._get_jet_info_rows())
        self._register_save_model("model_itemat")
        self.tbl_itemat.resizeColumnsToContents()

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
        -> Update nur, wenn der neue Wert sich vom aktuellen DB-Wert unterscheidet.
        """
        if not self.model_itemat or not self._itemat_tensions:
            return 0

        updates = 0
        ROW_IP0 = 0
        ROW_STAB_START = 2

        # Kandidaten sammeln
        cand_ids: List[Any] = []
        cand_vals: Dict[Any, float] = {}

        for c_idx in range(len(self._trial_labels)):
            ip0_txt = self.model_itemat.get_cell_value(ROW_IP0, c_idx)
            ip0 = self._to_float(ip0_txt)
            if ip0 is None:
                continue
            for t_idx, _tval in enumerate(self._itemat_tensions):
                row = ROW_STAB_START + t_idx
                stab_txt = self.model_itemat.get_cell_value(row, c_idx)
                stab = self._to_float(stab_txt)
                if stab is None:
                    continue
                bind = self.model_itemat.get_binding(row, c_idx)
                if not bind:
                    continue
                rec_id = bind.id_value
                new_val = ip0 * (stab / 100.0)
                cand_ids.append(rec_id)
                cand_vals[rec_id] = new_val

        if not cand_ids:
            return 0

        # Aktuelle DB-Werte lesen
        placeholders = ",".join(["?"] * len(cand_ids))
        rows = fetch_all(
            f"SELECT ID, [Intermingling Points (FP/m)] AS V FROM tblLaborItematLab WHERE ID IN ({placeholders})",
            cand_ids,
        )
        cur_vals: Dict[Any, Optional[float]] = {
            r["ID"]: self._to_float(r.get("V")) for r in rows}

        # Nur schreiben, wenn Delta
        EPS = 1e-9
        for rec_id, new_v in cand_vals.items():
            old_v = cur_vals.get(rec_id)
            if (old_v is None and new_v is None):
                continue
            if (old_v is not None and abs(old_v - new_v) <= EPS):
                continue
            updates += execute_non_query(
                "UPDATE tblLaborItematLab SET [Intermingling Points (FP/m)] = ? WHERE ID = ?",
                [new_v, rec_id],
            )

        return updates

    # ---------- Itemat Plus (sichtbar nur bei Daten) ----------

    def _ensure_itemat_plus_tab(self):
        if self.tab_itemat_plus is not None:
            return
        self.tab_itemat_plus = QWidget()
        vl = QVBoxLayout(self.tab_itemat_plus)
        vl.setContentsMargins(24, 12, 24, 24)
        self.tbl_itemat_plus = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_itemat_plus)
        self._enable_paste_for_table(self.tbl_itemat_plus)
        self.tbl_itemat_plus.verticalHeader().setVisible(False)
        self.tbl_itemat_plus.horizontalHeader().setMinimumSectionSize(120)
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
        self._itemat_plus_tensions = []

    def _build_itemat_plus_tab(self):
        if not self._trial_ids or not table_exists("tblLaborItematPlus"):
            self._remove_itemat_plus_tab_if_exists()
            return

        rows = fetch_all(
            f"""
            SELECT
                IP.ID AS RecID,
                IP.TrialID,
                IP.[Tension (cN/dtex)]                AS Tension,
                IP.[Intermingling Points (FP/m)]      AS InterP,
                IP.[Intermingling Points CV (%)]      AS InterCV,
                IP.[Stability (%)]                    AS Stability,
                IP.[OL X (mm)]                        AS OLX,
                IP.[OL S (mm)]                        AS OLS,
                IP.[KL X (mm)]                        AS KLX,
                IP.[KL S (mm)]                        AS KLS
            FROM tblLaborItematPlus AS IP
            WHERE IP.TrialID IN ({",".join(["?"] * len(self._trial_ids))})
            ORDER BY IP.TrialID, IP.[Tension (cN/dtex)], IP.ID
            """,
            self._trial_ids,
        )

        if not rows:
            self._remove_itemat_plus_tab_if_exists()
            return

        by_trial: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        tensions_set: set[float] = set()
        for r in rows:
            by_trial[int(r["TrialID"])].append(r)
            try:
                t = float(str(r["Tension"]).replace(",", "."))
            except Exception:
                t = 0.0
            if t != 0.0:
                tensions_set.add(round(t, 2))

        tensions_sorted = sorted(tensions_set)
        self._itemat_plus_tensions = tensions_sorted.copy()

        # Zeilen: IP@0, OLX@0, OLS@0, KLX@0, KLS@0, dann Stability@t für alle t>0
        row_titles: List[str] = [
                                    "Intermingling Points (FP/m) @0.0 cN/dtex",
                                    "OL X (mm) @0.0 cN/dtex",
                                    "OL S (mm) @0.0 cN/dtex",
                                    "KL X (mm) @0.0 cN/dtex",
                                    "KL S (mm) @0.0 cN/dtex",
                                ] + [f"Stability@{t:.1f} cN/dtex" for t in tensions_sorted]

        self.model_itemat_plus = PivotEditModel(
            row_titles=row_titles,
            col_titles=self._trial_labels,
            row_validators=["onlyDoubles"] * len(row_titles),  # nur Zahlen
        )

        def find_record(trial_list: List[Dict[str, Any]], tension_value: float) -> Optional[Dict[str, Any]]:
            for rr in trial_list:
                try:
                    tt = float(str(rr["Tension"]).replace(",", "."))
                except Exception:
                    tt = 0.0
                if abs(tt - tension_value) < 1e-6:
                    return rr
            return None

        for c_idx, trial in enumerate(self._trials):
            tid = trial["ID"]
            recs = by_trial.get(tid, [])

            r0 = find_record(recs, 0.0)
            if r0:
                # Row 0: IP@0
                self.model_itemat_plus.set_cell(
                    0, c_idx, r0.get("InterP"),
                    CellBinding("tblLaborItematPlus", "ID",
                                r0["RecID"], "Intermingling Points (FP/m)"),
                )
                # Row 1..4: OLX, OLS, KLX, KLS @0
                self.model_itemat_plus.set_cell(
                    1, c_idx, r0.get("OLX"),
                    CellBinding("tblLaborItematPlus", "ID",
                                r0["RecID"], "OL X (mm)"),
                )
                self.model_itemat_plus.set_cell(
                    2, c_idx, r0.get("OLS"),
                    CellBinding("tblLaborItematPlus", "ID",
                                r0["RecID"], "OL S (mm)"),
                )
                self.model_itemat_plus.set_cell(
                    3, c_idx, r0.get("KLX"),
                    CellBinding("tblLaborItematPlus", "ID",
                                r0["RecID"], "KL X (mm)"),
                )
                self.model_itemat_plus.set_cell(
                    4, c_idx, r0.get("KLS"),
                    CellBinding("tblLaborItematPlus", "ID",
                                r0["RecID"], "KL S (mm)"),
                )
            else:
                for rr in range(5):
                    self.model_itemat_plus.set_cell(rr, c_idx, None, None)

            # Stability@t für jede Spannung > 0
            for idx, tval in enumerate(tensions_sorted, start=5):
                rr = find_record(recs, tval)
                if rr:
                    self.model_itemat_plus.set_cell(
                        idx, c_idx, rr.get("Stability"),
                        CellBinding("tblLaborItematPlus", "ID",
                                    rr["RecID"], "Stability (%)"),
                    )
                else:
                    self.model_itemat_plus.set_cell(idx, c_idx, None, None)

        self._ensure_itemat_plus_tab()
        self.tbl_itemat_plus.setModel(self.model_itemat_plus)
        self.model_itemat_plus.insert_readonly_rows_at_top(self._get_jet_info_rows())
        self._register_save_model("model_itemat_plus")
        self.tbl_itemat_plus.resizeColumnsToContents()

    def _recompute_itemat_plus(self) -> int:
        """
        Zwei Dinge:
        1) Für jede Spannung t>0: IP(t) = IP(0) * Stability(t) / 100
           -> schreibe in den Datensatz mit Stability(t) (nur bei echter Änderung).
        2) CV@0: ((KL S)^2 + (OL S)^2)^0.5 / (KL X + OL X)
           -> schreibe in den 0.0-Datensatz in Feld [Intermingling Points CV (%)] (nur bei echter Änderung).
        """
        if not self.model_itemat_plus:
            return 0

        updates = 0

        ROW_IP0 = 0
        ROW_OLX0 = 1
        ROW_OLS0 = 2
        ROW_KLX0 = 3
        ROW_KLS0 = 4
        ROW_STAB_START = 5
        EPS = 1e-9

        # -------- Teil 1: IP(t) für t>0 --------
        cand_ids_ip: List[Any] = []
        cand_vals_ip: Dict[Any, float] = {}

        for c_idx in range(len(self._trial_labels)):
            ip0 = self._to_float(
                self.model_itemat_plus.get_cell_value(ROW_IP0, c_idx))
            if ip0 is None:
                continue
            for t_idx, _ in enumerate(self._itemat_plus_tensions):
                row = ROW_STAB_START + t_idx
                stab = self._to_float(
                    self.model_itemat_plus.get_cell_value(row, c_idx))
                if stab is None:
                    continue
                bind = self.model_itemat_plus.get_binding(row, c_idx)
                if not bind:
                    continue
                rec_id = bind.id_value
                new_val = ip0 * (stab / 100.0)
                cand_ids_ip.append(rec_id)
                cand_vals_ip[rec_id] = new_val

        if cand_ids_ip:
            placeholders = ",".join(["?"] * len(cand_ids_ip))
            rows_ip = fetch_all(
                f"SELECT ID, [Intermingling Points (FP/m)] AS V FROM tblLaborItematPlus WHERE ID IN ({placeholders})",
                cand_ids_ip,
            )
            cur_vals_ip: Dict[Any, Optional[float]] = {
                r["ID"]: self._to_float(r.get("V")) for r in rows_ip}

            for rec_id, new_v in cand_vals_ip.items():
                old_v = cur_vals_ip.get(rec_id)
                if (old_v is None and new_v is None):
                    continue
                if (old_v is not None and abs(old_v - new_v) <= EPS):
                    continue
                updates += execute_non_query(
                    "UPDATE tblLaborItematPlus SET [Intermingling Points (FP/m)] = ? WHERE ID = ?",
                    [new_v, rec_id],
                )

        # -------- Teil 2: CV@0 --------
        cand_ids_cv: List[Any] = []
        cand_vals_cv: Dict[Any, float] = {}

        for c_idx in range(len(self._trial_labels)):
            def _f(row_idx):
                return self._to_float(self.model_itemat_plus.get_cell_value(row_idx, c_idx))

            olx, ols, klx, kls = _f(1), _f(2), _f(3), _f(4)
            if None in (olx, ols, klx, kls):
                continue
            denom = (olx or 0.0) + (klx or 0.0)
            if denom <= 0:
                continue
            cv0 = math.sqrt((kls or 0.0) ** 2 +
                            (ols or 0.0) ** 2) / denom * 100

            bind0 = self.model_itemat_plus.get_binding(ROW_IP0, c_idx)
            if not bind0:
                continue
            rec0_id = bind0.id_value
            cand_ids_cv.append(rec0_id)
            cand_vals_cv[rec0_id] = cv0

        if cand_ids_cv:
            placeholders = ",".join(["?"] * len(cand_ids_cv))
            rows_cv = fetch_all(
                f"SELECT ID, [Intermingling Points CV (%)] AS V FROM tblLaborItematPlus WHERE ID IN ({placeholders})",
                cand_ids_cv,
            )
            cur_vals_cv: Dict[Any, Optional[float]] = {
                r["ID"]: self._to_float(r.get("V")) for r in rows_cv}

            for rec_id, new_v in cand_vals_cv.items():
                old_v = cur_vals_cv.get(rec_id)
                if (old_v is None and new_v is None):
                    continue
                if (old_v is not None and abs(old_v - new_v) <= EPS):
                    continue
                updates += execute_non_query(
                    "UPDATE tblLaborItematPlus SET [Intermingling Points CV (%)] = ? WHERE ID = ?",
                    [new_v, rec_id],
                )

        return updates

    # ---------- DTYoMat (sichtbar nur bei vorhandenen Daten) ----------

    def _ensure_dtyomat_tab(self):
        if self.tab_dtyomat is not None:
            return
        self.tab_dtyomat = QWidget()
        vl = QVBoxLayout(self.tab_dtyomat)
        vl.setContentsMargins(24, 12, 24, 24)

        self.tbl_dtyomat = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_dtyomat)
        self._enable_paste_for_table(self.tbl_dtyomat)
        self.tbl_dtyomat.verticalHeader().setVisible(False)
        self.tbl_dtyomat.horizontalHeader().setMinimumSectionSize(120)
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

    def _build_dtyomat_tab(self):
        """
        Baut das DTYoMat-Tab aus tblLaborDTYoMat auf.
        Erwartet pro Trial höchstens einen Datensatz. Falls mehrere vorhanden sind,
        wird aktuell der erste Datensatz pro Trial verwendet.
        """
        if not self._trial_ids or not table_exists("tblLaborDTYoMat"):
            self._remove_dtyomat_tab_if_exists()
            return

        rows = fetch_all(
            f"""
            SELECT
                D.ID         AS RecID,
                D.TrialID    AS TrialID,
                D.[FP/m]     AS FPm,
                D.CV_FP      AS CV_FP,
                D.AvgFP      AS AvgFP,
                D.StdDevFP   AS StdDevFP,
                D.CV_KL      AS CV_KL,
                D.AvgKL      AS AvgKL,
                D.StdDevKL   AS StdDevKL,
                D.CV_OL      AS CV_OL,
                D.AvgOL      AS AvgOL,
                D.StdDevOL   AS StdDevOL,
                D.AKnots     AS AKnots,
                D.BKnots     AS BKnots,
                D.CKnots     AS CKnots
            FROM tblLaborDTYoMat AS D
            WHERE D.TrialID IN ({",".join(["?"] * len(self._trial_ids))})
            ORDER BY D.TrialID, D.ID
            """,
            self._trial_ids,
        )

        if not rows:
            self._remove_dtyomat_tab_if_exists()
            return

        # Pro Trial den ersten Datensatz verwenden
        by_trial: Dict[int, Dict[str, Any]] = {}
        for r in rows:
            tid = int(r["TrialID"])
            if tid not in by_trial:
                by_trial[tid] = r

        row_titles: List[str] = [
            "Intermingling Points per Meter (FP/m)",
            "Intermingling Points CV (%)",
            "Average FP Length (mm)",
            "Standard Deviation FP Length (mm)",
            "Knot Length CV (%)",
            "Average Knot Length (mm)",
            "Standard Deviation Knot Length (mm)",
            "Open Length CV (%)",
            "Average Open Length (mm)",
            "Standard Deviation Open Length (mm)",
            "A-Knots (%)",
            "B-Knots (%)",
            "C-Knots (%)",
        ]

        self._ensure_dtyomat_tab()

        self.model_dtyomat = PivotEditModel(
            row_titles=row_titles,
            col_titles=self._trial_labels,
            row_validators=["onlyDoubles"] * len(row_titles),
        )

        for c_idx, trial in enumerate(self._trials):
            tid = trial["ID"]
            rec = by_trial.get(tid)
            if not rec:
                for r_idx in range(len(row_titles)):
                    self.model_dtyomat.set_cell(r_idx, c_idx, None, None)
                continue

            rec_id = rec["RecID"]

            # 0: FP/m
            self.model_dtyomat.set_cell(
                0,
                c_idx,
                rec.get("FPm"),
                CellBinding("tblLaborDTYoMat", "ID", rec_id, "FP/m"),
            )
            # 1: CV_FP
            self.model_dtyomat.set_cell(
                1,
                c_idx,
                rec.get("CV_FP"),
                CellBinding("tblLaborDTYoMat", "ID", rec_id, "CV_FP"),
            )
            # 2: AvgFP
            self.model_dtyomat.set_cell(
                2,
                c_idx,
                rec.get("AvgFP"),
                CellBinding("tblLaborDTYoMat", "ID", rec_id, "AvgFP"),
            )
            # 3: StdDevFP
            self.model_dtyomat.set_cell(
                3,
                c_idx,
                rec.get("StdDevFP"),
                CellBinding("tblLaborDTYoMat", "ID", rec_id, "StdDevFP"),
            )
            # 4: CV_KL
            self.model_dtyomat.set_cell(
                4,
                c_idx,
                rec.get("CV_KL"),
                CellBinding("tblLaborDTYoMat", "ID", rec_id, "CV_KL"),
            )
            # 5: AvgKL
            self.model_dtyomat.set_cell(
                5,
                c_idx,
                rec.get("AvgKL"),
                CellBinding("tblLaborDTYoMat", "ID", rec_id, "AvgKL"),
            )
            # 6: StdDevKL
            self.model_dtyomat.set_cell(
                6,
                c_idx,
                rec.get("StdDevKL"),
                CellBinding("tblLaborDTYoMat", "ID", rec_id, "StdDevKL"),
            )
            # 7: CV_OL
            self.model_dtyomat.set_cell(
                7,
                c_idx,
                rec.get("CV_OL"),
                CellBinding("tblLaborDTYoMat", "ID", rec_id, "CV_OL"),
            )
            # 8: AvgOL
            self.model_dtyomat.set_cell(
                8,
                c_idx,
                rec.get("AvgOL"),
                CellBinding("tblLaborDTYoMat", "ID", rec_id, "AvgOL"),
            )
            # 9: StdDevOL
            self.model_dtyomat.set_cell(
                9,
                c_idx,
                rec.get("StdDevOL"),
                CellBinding("tblLaborDTYoMat", "ID", rec_id, "StdDevOL"),
            )
            # 10: AKnots
            self.model_dtyomat.set_cell(
                10,
                c_idx,
                rec.get("AKnots"),
                CellBinding("tblLaborDTYoMat", "ID", rec_id, "AKnots"),
            )
            # 11: BKnots
            self.model_dtyomat.set_cell(
                11,
                c_idx,
                rec.get("BKnots"),
                CellBinding("tblLaborDTYoMat", "ID", rec_id, "BKnots"),
            )
            # 12: CKnots
            self.model_dtyomat.set_cell(
                12,
                c_idx,
                rec.get("CKnots"),
                CellBinding("tblLaborDTYoMat", "ID", rec_id, "CKnots"),
            )

        if self.tbl_dtyomat is not None:
            self.tbl_dtyomat.setModel(self.model_dtyomat)
            self.model_dtyomat.insert_readonly_rows_at_top(self._get_jet_info_rows())
            self._register_save_model("model_dtyomat")
            self.tbl_dtyomat.resizeColumnsToContents()

    # ---------- ATYoMat (sichtbar nur bei vorhandenen Daten) ----------

    def _ensure_atyomat_tab(self):
        if self.tab_atyomat is not None:
            return
        self.tab_atyomat = QWidget()
        vl = QVBoxLayout(self.tab_atyomat)
        vl.setContentsMargins(24, 12, 24, 24)

        self.tbl_atyomat = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_atyomat)
        self.tbl_atyomat.verticalHeader().setVisible(False)
        self.tbl_atyomat.horizontalHeader().setMinimumSectionSize(120)
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

    def _build_atyomat_tab(self):
        """
        Baut das ATYoMat-Tab aus tblLaborATYoMat auf.
        Zeigt nur die Zusammenfassungs-Kennzahlen (Averages + Anzahl/100m).
        Pro Trial wird der neueste Datensatz verwendet (MAX(ID)).
        """
        if not self._trial_ids or not table_exists("tblLaborATYoMat"):
            self._remove_atyomat_tab_if_exists()
            return

        rows = fetch_all(
            f"""
            SELECT
                D.ID            AS RecID,
                D.TrialID       AS TrialID,
                D.TotalLen_m    AS TotalLen_m,
                D.BinThreshold  AS BinThreshold,
                D.N_B1          AS N_B1,
                D.N_B2          AS N_B2,
                D.AvgLen_B1     AS AvgLen_B1,
                D.AvgLen_B2     AS AvgLen_B2,
                D.AvgHeight_B1  AS AvgHeight_B1,
                D.AvgHeight_B2  AS AvgHeight_B2,
                D.AvgArea_B1    AS AvgArea_B1,
                D.AvgArea_B2    AS AvgArea_B2
            FROM tblLaborATYoMat AS D
            INNER JOIN (
                SELECT TrialID, MAX(ID) AS MaxID
                FROM tblLaborATYoMat
                WHERE TrialID IN ({",".join(["?"] * len(self._trial_ids))})
                GROUP BY TrialID
            ) AS Latest ON D.ID = Latest.MaxID
            ORDER BY D.TrialID
            """,
            self._trial_ids,
        )

        if not rows:
            self._remove_atyomat_tab_if_exists()
            return

        by_trial: Dict[int, Dict[str, Any]] = {}
        for r in rows:
            tid = int(r["TrialID"])
            if tid not in by_trial:
                by_trial[tid] = r

        row_titles: List[str] = [
            "Gesamtlaenge (m)",
            "Bin-Schwelle (um/mm)",
            "Kurzhocker Anzahl / 100 m",
            "Langwelle Anzahl / 100 m",
            "Kurzhocker Ø Laenge (mm)",
            "Langwelle Ø Laenge (mm)",
            "Kurzhocker Ø Hoehe (um)",
            "Langwelle Ø Hoehe (um)",
            "Kurzhocker Ø Flaeche (um*mm)",
            "Langwelle Ø Flaeche (um*mm)",
        ]

        col_db = [
            "TotalLen_m",
            "BinThreshold",
            "N_B1",
            "N_B2",
            "AvgLen_B1",
            "AvgLen_B2",
            "AvgHeight_B1",
            "AvgHeight_B2",
            "AvgArea_B1",
            "AvgArea_B2",
        ]

        self._ensure_atyomat_tab()

        self.model_atyomat = PivotEditModel(
            row_titles=row_titles,
            col_titles=self._trial_labels,
            row_validators=["onlyDoubles"] * len(row_titles),
        )

        for c_idx, trial in enumerate(self._trials):
            tid = trial["ID"]
            rec = by_trial.get(tid)
            if not rec:
                for r_idx in range(len(row_titles)):
                    self.model_atyomat.set_cell(r_idx, c_idx, None, None)
                continue

            rec_id = rec["RecID"]
            for r_idx, col_name in enumerate(col_db):
                self.model_atyomat.set_cell(
                    r_idx,
                    c_idx,
                    rec.get(col_name),
                    CellBinding("tblLaborATYoMat", "ID", rec_id, col_name),
                )

        if self.tbl_atyomat is not None:
            self.tbl_atyomat.setModel(self.model_atyomat)
            self.model_atyomat.insert_readonly_rows_at_top(self._get_jet_info_rows())
            self._register_save_model("model_atyomat")
            self.tbl_atyomat.resizeColumnsToContents()

    # ---------- Rapid 600 (sichtbar nur bei vorhandenen Daten) ----------

    def _ensure_rapid600_tab(self):
        if self.tab_rapid600 is not None:
            return
        self.tab_rapid600 = QWidget()
        vl = QVBoxLayout(self.tab_rapid600)
        vl.setContentsMargins(24, 12, 24, 24)

        self.tbl_rapid600 = FrozenFirstColumnTable()
        self._enable_copy_for_table(self.tbl_rapid600)
        self._enable_paste_for_table(self.tbl_rapid600)
        self.tbl_rapid600.verticalHeader().setVisible(False)
        self.tbl_rapid600.horizontalHeader().setMinimumSectionSize(120)
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

    def _build_rapid600_tab(self):
        """
        Baut das Rapid 600-Tab aus tblLaborRapid600 auf.
        Erwartet pro Trial höchstens einen Datensatz. Falls mehrere vorhanden sind,
        wird aktuell der erste Datensatz pro Trial verwendet.
        """
        if not self._trial_ids or not table_exists("tblLaborRapid600"):
            self._remove_rapid600_tab_if_exists()
            return

        rows = fetch_all(
            f"""
            SELECT
                R.ID         AS RecID,
                R.TrialID    AS TrialID,
                R.SPD        AS SPD,
                R.[SPD Avg]  AS SPD_Avg,
                R.[SPD Dev]  AS SPD_Dev
            FROM tblLaborRapid600 AS R
            WHERE R.TrialID IN ({",".join(["?"] * len(self._trial_ids))})
            ORDER BY R.TrialID, R.ID
            """,
            self._trial_ids,
        )

        if not rows:
            self._remove_rapid600_tab_if_exists()
            return

        # Pro Trial den ersten Datensatz verwenden
        by_trial: Dict[int, Dict[str, Any]] = {}
        for r in rows:
            tid = int(r["TrialID"])
            if tid not in by_trial:
                by_trial[tid] = r

        row_titles: List[str] = [
            "SPD",
            "SPD Avg",
            "SPD Dev",
        ]

        self._ensure_rapid600_tab()

        self.model_rapid600 = PivotEditModel(
            row_titles=row_titles,
            col_titles=self._trial_labels,
            row_validators=["onlyDoubles"] * len(row_titles),
        )

        for c_idx, trial in enumerate(self._trials):
            tid = trial["ID"]
            rec = by_trial.get(tid)
            if not rec:
                for r_idx in range(len(row_titles)):
                    self.model_rapid600.set_cell(r_idx, c_idx, None, None)
                continue

            rec_id = rec["RecID"]

            # 0: SPD
            self.model_rapid600.set_cell(
                0,
                c_idx,
                rec.get("SPD"),
                CellBinding("tblLaborRapid600", "ID", rec_id, "SPD"),
            )
            # 1: SPD Avg
            self.model_rapid600.set_cell(
                1,
                c_idx,
                rec.get("SPD_Avg"),
                CellBinding("tblLaborRapid600", "ID", rec_id, "SPD Avg"),
            )
            # 2: SPD Dev
            self.model_rapid600.set_cell(
                2,
                c_idx,
                rec.get("SPD_Dev"),
                CellBinding("tblLaborRapid600", "ID", rec_id, "SPD Dev"),
            )

        if self.tbl_rapid600 is not None:
            self.tbl_rapid600.setModel(self.model_rapid600)
            self.model_rapid600.insert_readonly_rows_at_top(self._get_jet_info_rows())
            self._register_save_model("model_rapid600")
            self.tbl_rapid600.resizeColumnsToContents()


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