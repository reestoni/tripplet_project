# ui/screen_label_generator.py
"""Standalone Label Generator (Home -> Tools).

Interactive Label-Designer: Elemente (Text/Logo) werden direkt auf der
Live-Vorschau per Drag & Drop positioniert/skaliert (QGraphicsView/Scene).
Text-Elemente koennen mehrere Teile aneinanderhaengen (z.B. "V" + Feld
"trial_nr") - siehe ui/label_generator_fields.py fuer die DB-Feld-Registry.
Nutzt die bestehende, gemeinsame Bogen-Layout-Infrastruktur aus
ui/widgets/label_printing.py unveraendert (nur Imports - ui/screen_yarn_stock.py,
ui/screen_show_experiment.py und ui/widgets/label_printing.py selbst bleiben
unangetastet).

DB-Tabelle (auto-erstellt): tblLabelDesign (Name, TemplateName, ElementsJson)
- speichert benannte, wiederverwendbare Label-Layouts (Liste von Elementen
  als JSON). Die Bogen-Geometrie (Seitengroesse/Spalten/Zeilen) liegt separat
  in tblLabelTemplate unter dem festen Namen TEMPLATE_NAME.

Element-Schema (JSON, siehe _normalize_element() fuer Altformat-Kompatibilitaet):
    {"type": "text", "x_mm":.., "y_mm":.., "w_mm":.., "h_mm":..,
     "font_size":.., "bold":.., "align":.., "anchor_group": "a1b2c3d4",
     "parts": [{"source": "static", "text": "V"},
               {"source": "field", "field_key": "trial_nr"},
               {"source": "counter", "start": 1, "step": 1, "digits": 3}]}
    {"type": "logo", "x_mm":.., "y_mm":.., "w_mm":.., "h_mm":..}
    {"type": "table", "x_mm":.., "y_mm":.., "w_mm":.., "h_mm":..,
     "rows": 2, "cols": 2, "show_borders": True,
     "font_size":.., "bold":.., "align":.., "anchor_group":..,
     "cells": [[{"parts": [<ein part wie oben>]}, ...], ...]}  # rows x cols

Tabellen-Element: generisches, gleichmaessiges Raster - jede Zelle ist genau
ew/cols mm breit und eh/rows mm hoch (keine individuellen Spalten-/
Zeilenbreiten), Inhalt pro Zelle genau ein "part" (static/field/counter,
selbes Schema wie Text-Element-parts). Rendering in _draw_table().

Zwei Teile-Quellen ausser "static"/"field":
- "counter": fortlaufende Nummer unabhaengig von TrialSeries-Daten, ausgewertet
  ueber den Batch-Index jedes generierten Labels (item["__label_index__"],
  von _on_generate/_preview_item gesetzt) - start + index*step, optional mit
  Nullen auf `digits` Stellen aufgefuellt.
- "anchor_group": kein Part-Feld, sondern ein Element-Attribut. Elemente mit
  derselben (nicht-leeren) anchor_group-ID bewegen sich beim Verschieben
  (Drag oder X/Y-Spinbox) gemeinsam - siehe LabelElementItem._on_move /
  LabelGeneratorScreen._on_element_moved. Reine Translation, kein Resize-Sync.
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Callable, Dict, List, Optional, Tuple

import fitz  # PyMuPDF
from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFrame,
    QGraphicsItem, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene,
    QGraphicsSimpleTextItem, QGraphicsView, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QMessageBox, QPushButton, QScrollArea, QSpinBox,
    QStyle, QStyleOptionGraphicsItem, QVBoxLayout, QWidget,
)

from db.connection import execute, fetch_all, get_connection, table_exists
from ui.label_generator_fields import (
    FIELD_REGISTRY, build_fields, build_machine_fields, list_trials_for_series,
    machine_field_registry, machine_id_for_series, series_header, trial_ids_by_number,
)
from ui.pathutil import resource_path
from ui.theme import CARD_BG, DARK, LIGHT_BG, TEXT
from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from ui.widgets.label_printing import (
    MM, PrintLabelsDialog, fit_text, generate_label_sheet_pdf,
    load_label_template, save_label_template,
)
from ui.widgets.friendly_error import show_error

TEMPLATE_NAME = "CustomLabel"
DESIGN_TABLE = "tblLabelDesign"
COUNTER_SENTINEL = "__counter__"  # Wahl in _field_combo() fuer "part.source == 'counter'"
LOGO_ASSET = "assets/images/heb_logo.png"
PX_PER_MM = 8.0  # feste Canvas-Skala (kein Stretch-to-fit) - komfortabel zum Draggen
PREVIEW_MARGIN = 18  # Rand fuer Raster/Mini-Lineal um das eigentliche Label herum


def _mm_to_scene(x_mm: float, y_mm: float) -> QPointF:
    """mm (label-relativ) -> Scene-Pixel (inkl. Vorschau-Rand fuers Lineal)."""
    return QPointF(x_mm * PX_PER_MM + PREVIEW_MARGIN, y_mm * PX_PER_MM + PREVIEW_MARGIN)


def _scene_to_mm(pos: QPointF) -> Tuple[float, float]:
    return ((pos.x() - PREVIEW_MARGIN) / PX_PER_MM, (pos.y() - PREVIEW_MARGIN) / PX_PER_MM)


from ui import label_designer as _ld  # noqa: E402
from ui.label_designer import (  # noqa: E402,F401 - Qt-free since 2026-11-13 (web version)
    _db_list_designs, _db_load_design, _db_save_design, _draw_table, _draw_text_in_box, _ensure_design_table,
    _normalize_element, _resolve_text, make_draw_cell,
)


def _card(title: str):
    """Gibt (aeusseres QFrame, Body-QVBoxLayout) zurueck - gleicher Card-Look
    wie in ui/screen_nozzle_calculator.py, hier lokal dupliziert um diese
    Datei unabhaengig von anderen Screens zu halten."""
    card = QFrame(objectName="Card")
    card.setStyleSheet(
        f"QFrame#Card {{ background: {CARD_BG}; border: 1px solid #cfcfcf; border-radius: 2px; }}")
    outer = QVBoxLayout(card)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    hdr = QFrame()
    hdr.setFixedHeight(30)
    hdr.setStyleSheet(f"background: {DARK};")
    hdr_lay = QHBoxLayout(hdr)
    hdr_lay.setContentsMargins(12, 0, 12, 0)
    lbl = QLabel(title)
    lbl.setStyleSheet("color: white; font-size: 13px; font-weight: 600;")
    hdr_lay.addWidget(lbl)
    outer.addWidget(hdr)

    body = QVBoxLayout()
    body.setContentsMargins(16, 12, 16, 12)
    body.setSpacing(8)
    outer.addLayout(body)
    return card, body


# ---------------------------------------------------------------------------
# Interaktive Canvas-Elemente (Drag & Drop)
# ---------------------------------------------------------------------------

HANDLE_SIZE = 10
MIN_SIZE_PX = 12


class ResizeHandle(QGraphicsRectItem):
    """Kleines Quadrat unten rechts an einem LabelElementItem - Ziehen
    veraendert Breite/Hoehe des Eltern-Elements statt sich selbst frei zu
    bewegen."""

    def __init__(self, parent_item: "LabelElementItem"):
        super().__init__(-HANDLE_SIZE / 2, -HANDLE_SIZE / 2, HANDLE_SIZE, HANDLE_SIZE, parent_item)
        self._parent_item = parent_item
        self.setBrush(QBrush(QColor("#2b7cff")))
        self.setPen(QPen(QColor("white"), 1))
        self.setCursor(Qt.SizeFDiagCursor)
        self.setZValue(10)
        self.setPos(parent_item.rect().width(), parent_item.rect().height())

    def mousePressEvent(self, event):
        event.accept()

    def mouseMoveEvent(self, event):
        local = self._parent_item.mapFromScene(event.scenePos())
        w = max(MIN_SIZE_PX, local.x())
        h = max(MIN_SIZE_PX, local.y())
        self._parent_item.set_size_px(w, h)
        self.setPos(w, h)
        event.accept()

    def mouseReleaseEvent(self, event):
        event.accept()


class LabelElementItem(QGraphicsRectItem):
    """Ein Label-Element (Text oder Logo) als zieh-/skalierbare Box auf der
    Canvas. Haelt das zugehoerige Element-Dict synchron zur eigenen Geometrie
    - die tatsaechlich gerenderten Pixel kommen aus der fitz-Hintergrund-Ebene
    (LabelGeneratorScreen._refresh_preview), diese Box ist nur die
    interaktive Hit-Flaeche + der Resize-Griff."""

    def __init__(self, element: Dict, on_change: Optional[Callable[[], None]] = None,
                 on_move: Optional[Callable[["LabelElementItem", float, float], None]] = None):
        w_px = float(element.get("w_mm") or 10.0) * PX_PER_MM
        h_px = float(element.get("h_mm") or 6.0) * PX_PER_MM
        super().__init__(0, 0, w_px, h_px)
        self.element = element
        self._on_change = on_change
        self._on_move = on_move
        # Eigener Positions-Tracker statt aus element["x_mm"]/["y_mm"] zu
        # diffen: _on_geometry_spin_changed() schreibt die neuen mm-Werte
        # schon VOR dem setPos() ins element-Dict, ein Diff dagegen wuerde
        # dort immer 0 liefern. _last_*_mm wird ausschliesslich in
        # itemChange() fortgeschrieben, bleibt also unabhaengig davon
        # verlaesslich - fuer sowohl Drag- als auch Spinbox-/Anker-Bewegung.
        # Muss VOR dem setPos() unten gesetzt sein, da dieses bereits
        # synchron itemChange() ausloest.
        self._last_x_mm = float(element.get("x_mm") or 0.0)
        self._last_y_mm = float(element.get("y_mm") or 0.0)
        self.setFlags(
            QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges)
        self.setPos(_mm_to_scene(float(element.get("x_mm") or 0.0), float(element.get("y_mm") or 0.0)))
        self.caption = QGraphicsSimpleTextItem(self._caption_text(), self)
        self.caption.setBrush(QBrush(QColor("#666666")))
        f = self.caption.font()
        f.setPointSize(7)
        self.caption.setFont(f)
        self.caption.setPos(2, 2)
        self.handle = ResizeHandle(self)
        self._geometry_spins: Optional[Tuple] = None  # set by the properties panel while shown
        self._update_selection_look()

    def _update_selection_look(self) -> None:
        """Only the currently selected element gets the blue drag/resize
        look; every other element just sits there with a faint outline so
        the canvas doesn't read as "everything is selected"."""
        if self.isSelected():
            self.setBrush(QBrush(QColor(43, 124, 255, 45)))
            self.setPen(QPen(QColor("#2b7cff"), 1, Qt.DashLine))
            self.caption.setBrush(QBrush(QColor("#1a4fb4")))
            self.handle.setVisible(True)
        else:
            self.setBrush(QBrush(QColor(0, 0, 0, 10)))
            self.setPen(QPen(QColor("#aaaaaa"), 1, Qt.SolidLine))
            self.caption.setBrush(QBrush(QColor("#888888")))
            self.handle.setVisible(False)

    def _caption_text(self) -> str:
        return _ld.caption_text(self.element)

    def refresh_caption(self) -> None:
        self.caption.setText(self._caption_text())

    def set_size_px(self, w: float, h: float) -> None:
        self.setRect(0, 0, w, h)
        self.element["w_mm"] = w / PX_PER_MM
        self.element["h_mm"] = h / PX_PER_MM
        if self._on_change:
            self._on_change()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self._update_selection_look()
        if change == QGraphicsItem.ItemPositionHasChanged:
            x_mm, y_mm = _scene_to_mm(self.pos())
            dx_mm, dy_mm = x_mm - self._last_x_mm, y_mm - self._last_y_mm
            self._last_x_mm, self._last_y_mm = x_mm, y_mm
            self.element["x_mm"] = x_mm
            self.element["y_mm"] = y_mm
            if self._on_move and (abs(dx_mm) > 1e-9 or abs(dy_mm) > 1e-9):
                self._on_move(self, dx_mm, dy_mm)
            if self._on_change:
                self._on_change()
        return super().itemChange(change, value)

    def paint(self, painter, option, widget=None):
        # Qt draws its own dashed selection decoration on top of selected
        # items by default - we already show selection via our own
        # blue pen/brush in _update_selection_look(), so suppress the
        # built-in one to avoid a doubled-up look.
        opt = QStyleOptionGraphicsItem(option)
        opt.state &= ~QStyle.State_Selected
        super().paint(painter, opt, widget)


class LabelGeneratorScreen(QWidget):
    """Standalone Label-Designer: ein Datensatz laden, Elemente per Drag &
    Drop auf der Live-Vorschau positionieren, als Design speichern/laden,
    N Kopien als druckfertiges PDF exportieren."""

    def __init__(self, on_back_home: Optional[Callable[[], None]] = None,
                 parent: Optional[QWidget] = None,
                 sidebar_callbacks: Optional[dict] = None):
        super().__init__(parent)
        self._on_back_home = on_back_home
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None
        self._loaded_values: Optional[Dict[str, str]] = None
        self._series_context: Optional[Dict[str, str]] = None
        self._trial_numbers: List[int] = []
        self._trial_ids_by_nr: Dict[int, int] = {}
        self._machine_id: Optional[int] = None
        # Startet mit den statischen Feldern + den 4 immer vorhandenen
        # Machine-Data-Fixfeldern; nach einer erfolgreichen Serien-Suche um
        # die pro Maschine konfigurierten Custom-Felder erweitert (siehe
        # _on_search_series()).
        self._dynamic_field_registry: Dict[str, str] = dict(FIELD_REGISTRY)
        self._dynamic_field_registry.update(machine_field_registry(None))
        self._sheet_template: Dict = dict(load_label_template(TEMPLATE_NAME))
        self._bg_item: Optional[QGraphicsPixmapItem] = None
        self._syncing_anchor = False  # Reentrancy-Guard fuer _on_element_moved
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(150)
        self._preview_timer.timeout.connect(self._refresh_preview)

        self._build_ui()
        self._reload_design_combo()
        self._schedule_preview_refresh()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring).
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background: {LIGHT_BG}; border: none;")
        body = QWidget()
        body.setStyleSheet(f"background: {LIGHT_BG};")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(22, 18, 22, 18)
        body_layout.setSpacing(18)
        body_layout.setAlignment(Qt.AlignTop)

        left_col = QVBoxLayout()
        left_col.setSpacing(12)
        left_col.setAlignment(Qt.AlignTop)
        left_col.addWidget(self._build_load_card())
        left_col.addWidget(self._build_size_card())
        left_col.addWidget(self._build_design_card())
        left_col.addWidget(self._build_generate_card())

        left_w = QWidget()
        left_w.setStyleSheet("background: transparent;")
        left_w.setLayout(left_col)

        right_col = QVBoxLayout()
        right_col.setSpacing(12)
        right_col.setAlignment(Qt.AlignTop)
        right_col.addWidget(self._build_canvas_card())

        right_w = QWidget()
        right_w.setStyleSheet("background: transparent;")
        right_w.setLayout(right_col)

        body_layout.addWidget(left_w, 1)
        body_layout.addWidget(right_w, 2)
        scroll.setWidget(body)

        content_layout.addWidget(scroll, 1)
        root.addWidget(FooterBar(), 0)

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

    def _build_load_card(self) -> QFrame:
        card, body = _card("Load data (Trial Series)")

        row = QHBoxLayout()
        row.addWidget(QLabel("Trial Series ID:"))
        self.spn_series_id = QSpinBox()
        self.spn_series_id.setRange(1, 999999999)
        row.addWidget(self.spn_series_id, 1)
        btn_search = QPushButton("Search", objectName="GreenBtn")
        btn_search.clicked.connect(self._on_search_series)
        row.addWidget(btn_search)
        body.addLayout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Trial:"))
        self.cb_trials = QComboBox()
        self.cb_trials.setEnabled(False)
        self.cb_trials.currentIndexChanged.connect(self._on_trial_picked)
        row2.addWidget(self.cb_trials, 1)
        body.addLayout(row2)

        self.lbl_loaded_summary = QLabel(
            "No data loaded yet - static text elements work fine without it.")
        self.lbl_loaded_summary.setWordWrap(True)
        self.lbl_loaded_summary.setStyleSheet("color: #666; font-size: 11px;")
        body.addWidget(self.lbl_loaded_summary)

        return card

    def _build_size_card(self) -> QFrame:
        card, body = _card("Label size")

        row = QHBoxLayout()
        row.addWidget(QLabel("Width (mm):"))
        self.spn_label_w = self._mm_spin(self._sheet_template.get("LabelWidthMm", 60.0))
        self.spn_label_w.setRange(5.0, 500.0)
        row.addWidget(self.spn_label_w)
        row.addWidget(QLabel("Height (mm):"))
        self.spn_label_h = self._mm_spin(self._sheet_template.get("LabelHeightMm", 30.0))
        self.spn_label_h.setRange(5.0, 500.0)
        row.addWidget(self.spn_label_h)
        row.addStretch(1)
        body.addLayout(row)

        hint = QLabel(
            "This is the size of a single label. Sheet layout (rows/columns/margins "
            "on the printed page) is set in the next step when generating the PDF.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666; font-size: 11px;")
        body.addWidget(hint)

        self.spn_label_w.valueChanged.connect(self._on_label_size_changed)
        self.spn_label_h.valueChanged.connect(self._on_label_size_changed)

        return card

    def _build_design_card(self) -> QFrame:
        card, body = _card("Save / load design")

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Saved designs:"))
        self.cb_designs = QComboBox()
        row1.addWidget(self.cb_designs, 1)
        btn_load_design = QPushButton("Load", objectName="GreyBtn")
        btn_load_design.clicked.connect(self._on_load_design)
        row1.addWidget(btn_load_design)
        body.addLayout(row1)

        row2 = QHBoxLayout()
        btn_save_design = QPushButton("Save design as...", objectName="GreyBtn")
        btn_save_design.clicked.connect(self._on_save_design)
        row2.addWidget(btn_save_design)
        btn_clear = QPushButton("New / Clear", objectName="GreyBtn")
        btn_clear.clicked.connect(self._on_clear_design)
        row2.addWidget(btn_clear)
        row2.addStretch(1)
        body.addLayout(row2)

        return card

    def _build_generate_card(self) -> QFrame:
        card, body = _card("Generate")

        row_mode = QHBoxLayout()
        row_mode.addWidget(QLabel("Mode:"))
        self.cb_gen_mode = QComboBox()
        self.cb_gen_mode.addItems(
            ["Selected trial x N copies", "One label per trial in series"])
        self.cb_gen_mode.currentIndexChanged.connect(self._on_gen_mode_changed)
        row_mode.addWidget(self.cb_gen_mode, 1)
        body.addLayout(row_mode)

        self.row_copies = QHBoxLayout()
        self.row_copies.addWidget(QLabel("Copies:"))
        self.spn_quantity = QSpinBox()
        self.spn_quantity.setRange(1, 500)
        self.spn_quantity.setValue(1)
        self.row_copies.addWidget(self.spn_quantity)
        self.row_copies.addStretch(1)
        body.addLayout(self.row_copies)

        self.row_range = QHBoxLayout()
        self.row_range.addWidget(QLabel("From trial:"))
        self.spn_from = QSpinBox()
        self.spn_from.setRange(0, 999999)
        self.row_range.addWidget(self.spn_from)
        self.row_range.addWidget(QLabel("To trial:"))
        self.spn_to = QSpinBox()
        self.spn_to.setRange(0, 999999)
        self.row_range.addWidget(self.spn_to)
        self.row_range.addStretch(1)
        body.addLayout(self.row_range)
        self._set_row_visible(self.row_range, False)

        btn_generate = QPushButton("Generate PDF", objectName="GreenBtn")
        btn_generate.clicked.connect(self._on_generate)
        body.addWidget(btn_generate)

        return card

    def _set_row_visible(self, layout: QHBoxLayout, visible: bool) -> None:
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if w is not None:
                w.setVisible(visible)

    def _on_gen_mode_changed(self, index: int) -> None:
        is_range = index == 1
        self._set_row_visible(self.row_copies, not is_range)
        self._set_row_visible(self.row_range, is_range)

    def _update_batch_range_bounds(self) -> None:
        if not self._trial_numbers:
            return
        mn, mx = min(self._trial_numbers), max(self._trial_numbers)
        for spn in (self.spn_from, self.spn_to):
            spn.blockSignals(True)
        self.spn_from.setRange(mn, mx)
        self.spn_to.setRange(mn, mx)
        self.spn_from.setValue(mn)
        self.spn_to.setValue(mx)
        for spn in (self.spn_from, self.spn_to):
            spn.blockSignals(False)

    def _build_canvas_card(self) -> QFrame:
        card, body = _card("Label canvas")

        row = QHBoxLayout()
        self.scene = QGraphicsScene(self)
        self.scene.selectionChanged.connect(self._on_selection_changed)
        self.view = QGraphicsView(self.scene)
        self.view.setMinimumSize(360, 280)
        self.view.setStyleSheet("background: #e8e8e8; border: 1px solid #cfcfcf;")
        self.view.setRenderHint(QPainter.Antialiasing)
        row.addWidget(self.view, 2)

        self.properties_panel = self._build_properties_panel()
        row.addWidget(self.properties_panel, 1)
        body.addLayout(row)

        add_row = QHBoxLayout()
        btn_add_text = QPushButton("+ Text element", objectName="GreyBtn")
        btn_add_text.clicked.connect(
            lambda: self._add_element(
                {"type": "text", "parts": [{"source": "static", "text": "Text"}]}))
        add_row.addWidget(btn_add_text)
        btn_add_logo = QPushButton("+ Logo element", objectName="GreyBtn")
        btn_add_logo.clicked.connect(lambda: self._add_element({"type": "logo"}))
        add_row.addWidget(btn_add_logo)
        btn_add_table = QPushButton("+ Table element", objectName="GreyBtn")
        btn_add_table.clicked.connect(lambda: self._add_element({"type": "table"}))
        add_row.addWidget(btn_add_table)
        add_row.addStretch(1)
        body.addLayout(add_row)

        legend = QLabel(
            "Drag an element to move it, drag the blue corner to resize. "
            "Grid every 10 mm, dark border marks the actual label edge.")
        legend.setWordWrap(True)
        legend.setStyleSheet("color: #666; font-size: 11px;")
        body.addWidget(legend)

        return card

    def _build_properties_panel(self) -> QFrame:
        panel = QFrame()
        panel.setMinimumWidth(220)
        panel.setStyleSheet("background: white; border: 1px solid #cfcfcf;")
        self._props_layout = QVBoxLayout(panel)
        self._props_layout.setContentsMargins(10, 10, 10, 10)
        self._props_layout.setSpacing(6)
        self._props_layout.setAlignment(Qt.AlignTop)
        self._rebuild_properties_panel()
        return panel

    # ------------------------------------------------------------------
    # Canvas-Elemente
    # ------------------------------------------------------------------

    def _field_combo(self, selected_key: Optional[str] = None) -> QComboBox:
        cb = QComboBox()
        cb.addItem("Static text", None)
        cb.addItem("Running number (counter)", COUNTER_SENTINEL)
        for key, label in self._dynamic_field_registry.items():
            cb.addItem(label, key)
        if selected_key:
            idx = cb.findData(selected_key)
            if idx >= 0:
                cb.setCurrentIndex(idx)
        return cb

    def _mm_spin(self, value: float) -> QDoubleSpinBox:
        spn = QDoubleSpinBox()
        spn.setRange(0.0, 500.0)
        spn.setDecimals(1)
        spn.setValue(float(value))
        return spn

    def _blank_table_cells(self, rows: int, cols: int) -> List[List[Dict]]:
        return [[{"parts": [{"source": "static", "text": ""}]} for _ in range(cols)]
                for _ in range(rows)]

    def _add_element(self, data: Optional[Dict] = None) -> LabelElementItem:
        n = sum(1 for it in self.scene.items() if isinstance(it, LabelElementItem))
        data = _ld.new_element((data or {}).get("type") or "text", n, data)    # ui/label_designer.py
        item = LabelElementItem(
            data, on_change=self._on_element_changed, on_move=self._on_element_moved)
        self.scene.addItem(item)
        self._schedule_preview_refresh()
        return item

    def _on_selection_changed(self) -> None:
        self._rebuild_properties_panel()

    def _on_element_changed(self) -> None:
        self._sync_selected_geometry_spins()
        self._schedule_preview_refresh()

    def _selected_element_item(self) -> Optional[LabelElementItem]:
        selected = [it for it in self.scene.selectedItems() if isinstance(it, LabelElementItem)]
        return selected[0] if len(selected) == 1 else None

    def _other_elements(self, exclude: LabelElementItem) -> List[LabelElementItem]:
        return [it for it in self.scene.items()
                if isinstance(it, LabelElementItem) and it is not exclude]

    def _on_element_moved(self, item: LabelElementItem, dx_mm: float, dy_mm: float) -> None:
        """Verschiebt alle Elemente mit derselben anchor_group um dasselbe
        Delta mit. Guard verhindert Endlosrekursion, da das Nachziehen der
        Partner-Elemente selbst wieder itemChange/_on_move ausloest."""
        if self._syncing_anchor:
            return
        group = item.element.get("anchor_group")
        if not group:
            return
        self._syncing_anchor = True
        try:
            for other in self._other_elements(item):
                if other.element.get("anchor_group") == group:
                    other.setPos(_mm_to_scene(
                        other.element.get("x_mm", 0.0) + dx_mm,
                        other.element.get("y_mm", 0.0) + dy_mm))
        finally:
            self._syncing_anchor = False

    def _on_anchor_changed(self, item: LabelElementItem, combo: QComboBox,
                            chk_align: Optional[QCheckBox] = None) -> None:
        target = combo.currentData()
        if target is None:
            item.element.pop("anchor_group", None)
        else:
            if chk_align is not None and chk_align.isChecked():
                # Vor dem Gruppieren ausrichten (item.element["anchor_group"] ist
                # hier noch nicht gesetzt) - sonst wuerde _on_element_moved()
                # das Ziel-Element beim Ausrichten gleich mitziehen, statt nur
                # `item` an dessen Hoehe anzugleichen.
                item.setPos(_mm_to_scene(
                    item.element.get("x_mm", 0.0), target.element.get("y_mm", 0.0)))
            group = target.element.get("anchor_group")
            if not group:
                group = uuid.uuid4().hex[:8]
                target.element["anchor_group"] = group
            item.element["anchor_group"] = group
        self._rebuild_properties_panel()
        self._schedule_preview_refresh()

    def _sync_selected_geometry_spins(self) -> None:
        item = self._selected_element_item()
        if item is None or not item._geometry_spins:
            return
        spn_x, spn_y, spn_w, spn_h = item._geometry_spins
        for spn, key in ((spn_x, "x_mm"), (spn_y, "y_mm"), (spn_w, "w_mm"), (spn_h, "h_mm")):
            spn.blockSignals(True)
            spn.setValue(float(item.element.get(key, 0.0)))
            spn.blockSignals(False)

    def _on_geometry_spin_changed(self, item: LabelElementItem, **kwargs) -> None:
        item.element.update(kwargs)
        item.setPos(_mm_to_scene(item.element.get("x_mm", 0.0), item.element.get("y_mm", 0.0)))
        item.setRect(0, 0, item.element.get("w_mm", 10.0) * PX_PER_MM,
                     item.element.get("h_mm", 6.0) * PX_PER_MM)
        item.handle.setPos(item.rect().width(), item.rect().height())
        self._schedule_preview_refresh()

    def _on_prop_changed(self, item: LabelElementItem, key: str, value) -> None:
        item.element[key] = value
        self._schedule_preview_refresh()

    def _on_add_part(self, item: LabelElementItem) -> None:
        parts = item.element.setdefault("parts", [])
        parts.append({"source": "static", "text": ""})
        item.refresh_caption()
        self._rebuild_properties_panel()
        self._schedule_preview_refresh()

    def _on_remove_part(self, item: LabelElementItem, idx: int) -> None:
        parts = item.element.get("parts") or []
        if idx < len(parts):
            parts.pop(idx)
        if not parts:
            parts.append({"source": "static", "text": ""})
        item.refresh_caption()
        self._rebuild_properties_panel()
        self._schedule_preview_refresh()

    def _on_part_source_changed(self, item: LabelElementItem, idx: int, combo: QComboBox) -> None:
        parts = item.element.get("parts") or []
        if idx >= len(parts):
            return
        key = combo.currentData()
        if key == COUNTER_SENTINEL:
            old = parts[idx]
            parts[idx] = {
                "source": "counter",
                "start": old.get("start", 1) if old.get("source") == "counter" else 1,
                "step": old.get("step", 1) if old.get("source") == "counter" else 1,
                "digits": old.get("digits", 0) if old.get("source") == "counter" else 0,
            }
        elif key:
            parts[idx] = {"source": "field", "field_key": key}
        else:
            parts[idx] = {"source": "static", "text": parts[idx].get("text", "")}
        item.refresh_caption()
        self._rebuild_properties_panel()
        self._schedule_preview_refresh()

    def _on_part_text_changed(self, item: LabelElementItem, idx: int, text: str) -> None:
        parts = item.element.get("parts") or []
        if idx >= len(parts):
            return
        parts[idx]["text"] = text
        item.refresh_caption()
        self._schedule_preview_refresh()

    def _on_part_counter_changed(self, item: LabelElementItem, idx: int, key: str, value: int) -> None:
        parts = item.element.get("parts") or []
        if idx >= len(parts):
            return
        parts[idx][key] = int(value)
        item.refresh_caption()
        self._schedule_preview_refresh()

    # ------------------------------------------------------------------
    # Tabellen-Element: generisches Raster (rows x cols, gleichmaessig breite
    # Spalten/Zeilen - siehe _draw_table()). Jede Zelle traegt genau einen
    # "part" (static/field/counter), wiederverwendet dasselbe Schema wie die
    # Text-Element-parts, nur ohne die Mehrfach-Teile/"+ Add text piece" UI.
    # ------------------------------------------------------------------

    def _resize_table_cells(self, item: LabelElementItem) -> None:
        """Passt die cells-Matrix an item.element['rows']/['cols'] an -
        bestehender Zellinhalt bleibt erhalten, neue Zellen sind leer,
        ueberzaehlige werden verworfen."""
        _ld.resize_table_cells(item.element)

    def _on_table_dim_changed(self, item: LabelElementItem, key: str, value: int) -> None:
        item.element[key] = int(value)
        self._resize_table_cells(item)
        item.refresh_caption()
        self._rebuild_properties_panel()
        self._schedule_preview_refresh()

    def _table_cell_part(self, item: LabelElementItem, r: int, c: int) -> Dict:
        cell = item.element["cells"][r][c]
        return cell.setdefault("parts", [{"source": "static", "text": ""}])[0]

    def _on_table_cell_source_changed(self, item: LabelElementItem, r: int, c: int,
                                       combo: QComboBox) -> None:
        parts = item.element["cells"][r][c].setdefault("parts", [{"source": "static", "text": ""}])
        key = combo.currentData()
        if key == COUNTER_SENTINEL:
            old = parts[0]
            parts[0] = {
                "source": "counter",
                "start": old.get("start", 1) if old.get("source") == "counter" else 1,
                "step": old.get("step", 1) if old.get("source") == "counter" else 1,
                "digits": old.get("digits", 0) if old.get("source") == "counter" else 0,
            }
        elif key:
            parts[0] = {"source": "field", "field_key": key}
        else:
            parts[0] = {"source": "static", "text": parts[0].get("text", "")}
        self._rebuild_properties_panel()
        self._schedule_preview_refresh()

    def _on_table_cell_text_changed(self, item: LabelElementItem, r: int, c: int, text: str) -> None:
        self._table_cell_part(item, r, c)["text"] = text
        self._schedule_preview_refresh()

    def _on_table_cell_counter_changed(self, item: LabelElementItem, r: int, c: int,
                                        key: str, value: int) -> None:
        self._table_cell_part(item, r, c)[key] = int(value)
        self._schedule_preview_refresh()

    def _build_table_cells_ui(self, layout: QVBoxLayout, item: LabelElementItem) -> None:
        el = item.element
        rows = int(el.get("rows") or 1)
        cols = int(el.get("cols") or 1)
        for r in range(rows):
            for c in range(cols):
                part = self._table_cell_part(item, r, c)
                source = part.get("source")
                if source == "field":
                    sel_key = part.get("field_key")
                elif source == "counter":
                    sel_key = COUNTER_SENTINEL
                else:
                    sel_key = None

                layout.addWidget(QLabel(f"Row {r + 1}, Col {c + 1}:"))
                row = QHBoxLayout()
                cb = self._field_combo(sel_key)
                row.addWidget(cb, 1)
                ed = None
                if source not in ("field", "counter"):
                    ed = QLineEdit(str(part.get("text") or ""))
                    row.addWidget(ed, 1)
                layout.addLayout(row)

                spn_start = spn_step = spn_digits = None
                if source == "counter":
                    crow = QHBoxLayout()
                    crow.addWidget(QLabel("Start:"))
                    spn_start = QSpinBox()
                    spn_start.setRange(-999999, 999999)
                    spn_start.setValue(int(part.get("start", 1) or 0))
                    crow.addWidget(spn_start)
                    crow.addWidget(QLabel("Step:"))
                    spn_step = QSpinBox()
                    spn_step.setRange(-999999, 999999)
                    spn_step.setValue(int(part.get("step", 1) or 0))
                    crow.addWidget(spn_step)
                    crow.addWidget(QLabel("Digits:"))
                    spn_digits = QSpinBox()
                    spn_digits.setRange(0, 10)
                    spn_digits.setValue(int(part.get("digits", 0) or 0))
                    crow.addWidget(spn_digits)
                    crow.addStretch(1)
                    layout.addLayout(crow)

                cb.currentIndexChanged.connect(
                    lambda _=None, it=item, rr=r, cc=c, combo=cb:
                        self._on_table_cell_source_changed(it, rr, cc, combo))
                if ed is not None:
                    ed.textChanged.connect(
                        lambda v, it=item, rr=r, cc=c: self._on_table_cell_text_changed(it, rr, cc, v))
                if spn_start is not None:
                    spn_start.valueChanged.connect(
                        lambda v, it=item, rr=r, cc=c:
                            self._on_table_cell_counter_changed(it, rr, cc, "start", v))
                    spn_step.valueChanged.connect(
                        lambda v, it=item, rr=r, cc=c:
                            self._on_table_cell_counter_changed(it, rr, cc, "step", v))
                    spn_digits.valueChanged.connect(
                        lambda v, it=item, rr=r, cc=c:
                            self._on_table_cell_counter_changed(it, rr, cc, "digits", v))

    def _on_delete_element(self, item: LabelElementItem) -> None:
        self.scene.removeItem(item)
        self._rebuild_properties_panel()
        self._schedule_preview_refresh()

    def _build_parts_rows(self, layout: QVBoxLayout, item: LabelElementItem) -> None:
        parts = item.element.setdefault("parts", [])
        for i, part in enumerate(parts):
            source = part.get("source")
            if source == "field":
                sel_key = part.get("field_key")
            elif source == "counter":
                sel_key = COUNTER_SENTINEL
            else:
                sel_key = None

            row = QHBoxLayout()
            cb = self._field_combo(sel_key)
            row.addWidget(cb, 1)
            ed = None
            if source not in ("field", "counter"):
                ed = QLineEdit(str(part.get("text") or ""))
                row.addWidget(ed, 1)
            btn_remove = QPushButton("✕")
            btn_remove.setFixedWidth(24)
            row.addWidget(btn_remove)
            layout.addLayout(row)

            spn_start = spn_step = spn_digits = None
            if source == "counter":
                crow = QHBoxLayout()
                crow.addWidget(QLabel("Start:"))
                spn_start = QSpinBox()
                spn_start.setRange(-999999, 999999)
                spn_start.setValue(int(part.get("start", 1) or 0))
                crow.addWidget(spn_start)
                crow.addWidget(QLabel("Step:"))
                spn_step = QSpinBox()
                spn_step.setRange(-999999, 999999)
                spn_step.setValue(int(part.get("step", 1) or 0))
                crow.addWidget(spn_step)
                crow.addWidget(QLabel("Digits:"))
                spn_digits = QSpinBox()
                spn_digits.setRange(0, 10)
                spn_digits.setValue(int(part.get("digits", 0) or 0))
                crow.addWidget(spn_digits)
                crow.addStretch(1)
                layout.addLayout(crow)

            cb.currentIndexChanged.connect(
                lambda _=None, it=item, idx=i, combo=cb: self._on_part_source_changed(it, idx, combo))
            btn_remove.clicked.connect(
                lambda _=None, it=item, idx=i: self._on_remove_part(it, idx))
            if ed is not None:
                ed.textChanged.connect(
                    lambda v, it=item, idx=i: self._on_part_text_changed(it, idx, v))
            if spn_start is not None:
                spn_start.valueChanged.connect(
                    lambda v, it=item, idx=i: self._on_part_counter_changed(it, idx, "start", v))
                spn_step.valueChanged.connect(
                    lambda v, it=item, idx=i: self._on_part_counter_changed(it, idx, "step", v))
                spn_digits.valueChanged.connect(
                    lambda v, it=item, idx=i: self._on_part_counter_changed(it, idx, "digits", v))

    def _rebuild_properties_panel(self) -> None:
        layout = self._props_layout
        self._clear_layout(layout)

        item = self._selected_element_item()
        if item is None:
            lbl = QLabel("Click an element on the canvas to edit it.")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #888; font-size: 12px;")
            layout.addWidget(lbl)
            return

        el = item.element
        el_type = el.get("type")
        is_logo = el_type == "logo"
        is_table = el_type == "table"
        title = QLabel("Logo" if is_logo else ("Table" if is_table else "Text element"))
        title.setStyleSheet("font-weight: 600;")
        layout.addWidget(title)

        if is_table:
            dims_row = QHBoxLayout()
            dims_row.addWidget(QLabel("Rows:"))
            spn_rows = QSpinBox()
            spn_rows.setRange(1, 50)
            spn_rows.setValue(int(el.get("rows") or 1))
            dims_row.addWidget(spn_rows)
            dims_row.addWidget(QLabel("Cols:"))
            spn_cols = QSpinBox()
            spn_cols.setRange(1, 20)
            spn_cols.setValue(int(el.get("cols") or 1))
            dims_row.addWidget(spn_cols)
            dims_row.addStretch(1)
            layout.addLayout(dims_row)
            spn_rows.valueChanged.connect(lambda v, it=item: self._on_table_dim_changed(it, "rows", v))
            spn_cols.valueChanged.connect(lambda v, it=item: self._on_table_dim_changed(it, "cols", v))

            chk_borders = QCheckBox("Show borders")
            chk_borders.setChecked(bool(el.get("show_borders", True)))
            chk_borders.toggled.connect(lambda v, it=item: self._on_prop_changed(it, "show_borders", v))
            layout.addWidget(chk_borders)

            layout.addWidget(QLabel("Cells (uniform grid - one value each):"))
            cells_box = QVBoxLayout()
            cells_box.setSpacing(4)
            self._build_table_cells_ui(cells_box, item)
            layout.addLayout(cells_box)

        if not is_logo:
            if not is_table:
                layout.addWidget(QLabel("Content:"))
                parts_box = QVBoxLayout()
                parts_box.setSpacing(4)
                self._build_parts_rows(parts_box, item)
                layout.addLayout(parts_box)
                btn_add_part = QPushButton("+ Add text piece", objectName="GreyBtn")
                btn_add_part.clicked.connect(lambda: self._on_add_part(item))
                layout.addWidget(btn_add_part)

            row_font = QHBoxLayout()
            row_font.addWidget(QLabel("Font:"))
            spn_font = QDoubleSpinBox()
            spn_font.setRange(4.0, 60.0)
            spn_font.setValue(float(el.get("font_size", 9.0)))
            spn_font.valueChanged.connect(lambda v, it=item: self._on_prop_changed(it, "font_size", v))
            row_font.addWidget(spn_font)
            chk_bold = QCheckBox("Bold")
            chk_bold.setChecked(bool(el.get("bold", False)))
            chk_bold.toggled.connect(lambda v, it=item: self._on_prop_changed(it, "bold", v))
            row_font.addWidget(chk_bold)
            layout.addLayout(row_font)

            row_align = QHBoxLayout()
            row_align.addWidget(QLabel("Align:"))
            cb_align = QComboBox()
            cb_align.addItems(["Left", "Center", "Right"])
            cb_align.setCurrentText(str(el.get("align", "left")).capitalize())
            cb_align.currentTextChanged.connect(
                lambda v, it=item: self._on_prop_changed(it, "align", v.lower()))
            row_align.addWidget(cb_align)
            layout.addLayout(row_align)

        layout.addWidget(QLabel("Position / size (mm):"))
        grid = QHBoxLayout()
        spn_x = self._mm_spin(el.get("x_mm", 0.0))
        spn_y = self._mm_spin(el.get("y_mm", 0.0))
        spn_w = self._mm_spin(el.get("w_mm", 10.0))
        spn_h = self._mm_spin(el.get("h_mm", 6.0))
        for lbl_text, spn in (("X", spn_x), ("Y", spn_y), ("W", spn_w), ("H", spn_h)):
            grid.addWidget(QLabel(lbl_text))
            grid.addWidget(spn)
        layout.addLayout(grid)
        spn_x.valueChanged.connect(lambda v, it=item: self._on_geometry_spin_changed(it, x_mm=v))
        spn_y.valueChanged.connect(lambda v, it=item: self._on_geometry_spin_changed(it, y_mm=v))
        spn_w.valueChanged.connect(lambda v, it=item: self._on_geometry_spin_changed(it, w_mm=v))
        spn_h.valueChanged.connect(lambda v, it=item: self._on_geometry_spin_changed(it, h_mm=v))
        item._geometry_spins = (spn_x, spn_y, spn_w, spn_h)

        layout.addWidget(QLabel("Move together with (anchor):"))
        cb_anchor = QComboBox()
        cb_anchor.addItem("— Not anchored —", None)
        current_group = el.get("anchor_group")
        selected_idx = 0
        for other in self._other_elements(item):
            cb_anchor.addItem(other._caption_text() or "Element", other)
            if current_group and other.element.get("anchor_group") == current_group:
                selected_idx = cb_anchor.count() - 1
        cb_anchor.setCurrentIndex(selected_idx)
        layout.addWidget(cb_anchor)

        chk_anchor_align = QCheckBox("Align to same height (Y) when linking")
        chk_anchor_align.setChecked(True)
        layout.addWidget(chk_anchor_align)

        cb_anchor.currentIndexChanged.connect(
            lambda _=None, it=item, combo=cb_anchor, chk=chk_anchor_align:
                self._on_anchor_changed(it, combo, chk))

        btn_delete = QPushButton("Delete element", objectName="GreyBtn")
        btn_delete.clicked.connect(lambda: self._on_delete_element(item))
        layout.addWidget(btn_delete)

    def _clear_layout(self, layout) -> None:
        while layout.count():
            taken = layout.takeAt(0)
            w = taken.widget()
            if w is not None:
                w.deleteLater()
            else:
                sub = taken.layout()
                if sub is not None:
                    self._clear_layout(sub)

    def _collect_elements(self) -> List[Dict]:
        items = [it for it in self.scene.items() if isinstance(it, LabelElementItem)]
        return [dict(it.element) for it in items]

    # ------------------------------------------------------------------
    # Aktionen
    # ------------------------------------------------------------------

    def _on_search_series(self) -> None:
        series_id = self.spn_series_id.value()
        try:
            ctx = _ld.series_context(series_id)          # ui/label_designer.py
        except Exception as e:
            show_error(self, "Search", f"Trial series {series_id} could not be searched.", e)
            return
        self._ctx = ctx
        header, trial_numbers = ctx["header"], ctx["trials"]
        self._trial_ids_by_nr = ctx["trial_ids"]
        self._machine_id = ctx["machine_id"]
        self._dynamic_field_registry = ctx["fields"]
        self._rebuild_properties_panel()

        self._series_context = header
        self._trial_numbers = trial_numbers
        self.cb_trials.blockSignals(True)
        self.cb_trials.clear()
        if not header:
            self.cb_trials.setEnabled(False)
            self.lbl_loaded_summary.setText(
                f"Trial Series {series_id} not found. Check the ID and try again.")
        elif not trial_numbers:
            self.cb_trials.setEnabled(False)
            self.lbl_loaded_summary.setText(
                f"Trial Series {series_id} found ({header['experiment_id']} / "
                f"{header['series_name']}) but has no trials.")
        else:
            for nr in trial_numbers:
                self.cb_trials.addItem(f"Trial {nr}")
            self.cb_trials.setEnabled(True)
        self.cb_trials.blockSignals(False)

        self._update_batch_range_bounds()
        if header and trial_numbers:
            self.cb_trials.setCurrentIndex(0)
            self._on_trial_picked(0)

    def _on_trial_picked(self, index: int) -> None:
        if not self._series_context or index < 0 or index >= len(self._trial_numbers):
            return
        values = _ld.trial_values(self._ctx, self._trial_numbers[index])
        self._loaded_values = values
        self.lbl_loaded_summary.setText(
            "Loaded: " + ", ".join(
                f"{self._dynamic_field_registry.get(k, k)} = {v}" for k, v in values.items()))
        self._schedule_preview_refresh()

    def _on_label_size_changed(self) -> None:
        self._sheet_template["LabelWidthMm"] = self.spn_label_w.value()
        self._sheet_template["LabelHeightMm"] = self.spn_label_h.value()
        try:
            save_label_template(TEMPLATE_NAME, self._sheet_template)
        except Exception:
            pass
        self._schedule_preview_refresh()

    def _reload_design_combo(self) -> None:
        current = self.cb_designs.currentText()
        self.cb_designs.blockSignals(True)
        self.cb_designs.clear()
        self.cb_designs.addItems(_db_list_designs())
        idx = self.cb_designs.findText(current)
        if idx >= 0:
            self.cb_designs.setCurrentIndex(idx)
        self.cb_designs.blockSignals(False)

    def _on_save_design(self) -> None:
        name, ok = QInputDialog.getText(self, "Save design", "Design name:")
        name = (name or "").strip()
        if not ok or not name:
            return
        try:
            _db_save_design(name, self._collect_elements())
        except Exception as e:
            show_error(self, "Save design", "The label design could not be saved.", e)
            return
        self._reload_design_combo()
        idx = self.cb_designs.findText(name)
        if idx >= 0:
            self.cb_designs.setCurrentIndex(idx)
        QMessageBox.information(self, "Save design", "Design saved.")

    def _on_load_design(self) -> None:
        name = self.cb_designs.currentText()
        if not name:
            return
        elements = _db_load_design(name)
        if elements is None:
            QMessageBox.information(self, "Load design", f"Design {name!r} not found.")
            return
        self.scene.clear()
        self._bg_item = None
        for el in elements:
            self._add_element(el)
        self._rebuild_properties_panel()
        self._schedule_preview_refresh()

    def _on_clear_design(self) -> None:
        self.scene.clear()
        self._bg_item = None
        self._rebuild_properties_panel()
        self._schedule_preview_refresh()

    def _preview_item(self) -> Dict[str, str]:
        return _ld.preview_item(self._loaded_values, self._dynamic_field_registry)

    def _schedule_preview_refresh(self) -> None:
        self._preview_timer.start()

    def _refresh_preview(self) -> None:
        elements = self._collect_elements()
        w_mm = float(self._sheet_template.get("LabelWidthMm") or 60.0)
        h_mm = float(self._sheet_template.get("LabelHeightMm") or 30.0)
        try:
            img = QImage.fromData(_ld.preview_png(elements, w_mm, h_mm, self._preview_item(), PX_PER_MM), "PNG")
        except Exception as e:
            print(f"[LabelGenerator] Preview render error: {e}")
            return

        label_pm = QPixmap.fromImage(img)
        canvas_pm = self._compose_ruled_preview(label_pm, w_mm, h_mm)
        if self._bg_item is None:
            self._bg_item = QGraphicsPixmapItem(canvas_pm)
            self._bg_item.setZValue(-1)
            self.scene.addItem(self._bg_item)
        else:
            self._bg_item.setPixmap(canvas_pm)
        self.scene.setSceneRect(0, 0, canvas_pm.width(), canvas_pm.height())

    def _compose_ruled_preview(self, label_pm: QPixmap, w_mm: float, h_mm: float) -> QPixmap:
        """Zeichnet das gerenderte Label auf eine Vorschau-Canvas mit
        10mm-Raster, Mini-Lineal (Zahlen alle 10mm) und Rand entlang der
        echten Label-Kante - damit die Groesse ohne Nachdenken erkennbar ist."""
        m = PREVIEW_MARGIN
        canvas = QPixmap(label_pm.width() + m, label_pm.height() + m)
        canvas.fill(QColor("#e8e8e8"))
        painter = QPainter(canvas)
        painter.drawPixmap(m, m, label_pm)

        grid_pen = QPen(QColor(0, 0, 0, 40))
        painter.setPen(grid_pen)
        mm = 0.0
        while mm <= w_mm:
            x = m + mm * PX_PER_MM
            painter.drawLine(int(x), m, int(x), m + label_pm.height())
            mm += 10
        mm = 0.0
        while mm <= h_mm:
            y = m + mm * PX_PER_MM
            painter.drawLine(m, int(y), m + label_pm.width(), int(y))
            mm += 10

        tick_pen = QPen(QColor("#555"))
        painter.setPen(tick_pen)
        font = painter.font()
        font.setPointSize(7)
        painter.setFont(font)
        mm = 0.0
        while mm <= w_mm:
            x = m + mm * PX_PER_MM
            painter.drawLine(int(x), m - 4, int(x), m)
            if mm > 0:
                painter.drawText(int(x) - 8, m - 6, str(int(mm)))
            mm += 10
        mm = 0.0
        while mm <= h_mm:
            y = m + mm * PX_PER_MM
            painter.drawLine(m - 4, int(y), m, int(y))
            mm += 10

        border_pen = QPen(QColor("#333"))
        border_pen.setWidth(1)
        painter.setPen(border_pen)
        painter.drawRect(m, m, label_pm.width() - 1, label_pm.height() - 1)
        painter.end()
        return canvas

    def _on_generate(self) -> None:
        elements = self._collect_elements()
        is_range = self.cb_gen_mode.currentIndex() == 1
        items, err = _ld.build_items(elements, "range" if is_range else "copies", self.spn_quantity.value(),
                                     getattr(self, "_ctx", None), self._loaded_values,
                                     self.spn_from.value(), self.spn_to.value())       # ui/label_designer.py
        if err:
            QMessageBox.information(self, "Generate PDF", {
                "no_elements": "Add at least one element first.",
                "no_series": "Search a Trial Series first (see 'Load data' above).",
                "empty_range": "No trials in that range.",
                "need_trial": "This design uses a trial data field - pick a trial first "
                              "(see 'Load data' above), or remove that field if you only "
                              "need static text / a running number."}[err])
            return

        dlg = PrintLabelsDialog(TEMPLATE_NAME, self._sheet_template, len(items), parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        tpl = dlg.template_values()
        start_index = dlg.start_index()

        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save label PDF", "labels.pdf", "PDF Files (*.pdf)")
        if not out_path:
            return

        try:
            generate_label_sheet_pdf(
                items, tpl, start_index, out_path, draw_cell=make_draw_cell(elements))
        except Exception as e:
            show_error(self, "Generate PDF", "The PDF could not be created.", e)
            return
        QMessageBox.information(self, "Generate PDF", f"Saved to:\n{out_path}")

    def _go_home(self) -> None:
        if callable(self._on_back_home):
            self._on_back_home()
