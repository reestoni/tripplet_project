from __future__ import annotations
# ui/screen_backlog.py
"""Backlog-Screen mit Drag-and-Drop Kanban-Board (BacklogScreen).

Zeigt alle TrialSeries in einem statusbasierten Kanban-Board an.
Jede Spalte entspricht einem Backlog-Status (z.B. "Geplant", "In Arbeit", "Fertig").

Hauptfeatures:
  - Drag-and-Drop zwischen Status-Spalten (BacklogDnDTable)
  - Kontextmenü pro Karte: Status, Priorität, Maschine, Garn ändern; Serie löschen/umbenennen
  - Visuelle Karten via CardRowDelegate (Custom Paint)
  - Prioritäts-Badge (Farbe/Zahl)
  - Direktes Öffnen eines Experiments per Doppelklick

Datenbankbezug:
  tblBacklog, tblTrialSeries, tblExperimente, tblMaschine, tblGarn,
  tblBacklogStatus, tblUser
"""

import re
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QSpacerItem,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QDialog,
    QPushButton,
    QAbstractItemView,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QStyle,
    QMenu,
    QInputDialog,
    QLineEdit,
    QScrollArea,
    QStackedWidget,
)
from PySide6.QtCore import Qt, QMimeData, QPoint, QSize, QRect, QRect
from PySide6.QtGui import QDrag, QPixmap, QPainter, QFont, QColor, QPen, QIcon

from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from ui.pathutil import resource_path
from ui.screen_create_experiment import table_exists, get_columns_map, resolve_field
from ui.screen_show_experiment import _ExperimentRequestReadOnlyDialog
from db.connection import fetch_all, execute, update_trialseries_name

# 5%-Zufalls-Easter-Egg (schlafende Athena-Eule) - 2026-08-27 aus
# ui/screen_home.py hierher umgezogen (Nutzerwunsch: "da wir nun quasi home
# 'abgeschossen' haben" - Backlog ist seit 2026-08-26 der eigentliche
# Post-Login-Landing-Screen, siehe CLAUDE.md), siehe BacklogScreen.showEvent().
try:
    from ui.athena_owl import AthenaOwl as _AthenaOwl
    _ATHENA_AVAILABLE = True
except ImportError:
    _ATHENA_AVAILABLE = False
from db.retest_flags import get_open_retest_flags_by_series, resolve_retest_flags_for_series
from db.trial_reference import exclude_references_sql, format_trial_number
import app_meta  # enthält current_user


# ----------------------------
# Datenrollen für Karten
# ----------------------------
ROLE_SERIES_ID = Qt.UserRole
ROLE_EXP_ID = Qt.UserRole + 1
ROLE_SERIES_NAME = Qt.UserRole + 2
ROLE_MACHINE = Qt.UserRole + 3
ROLE_STATUS_NAME = Qt.UserRole + 4
ROLE_STATUS_ID = Qt.UserRole + 5
ROLE_PRIO = Qt.UserRole + 6
ROLE_OWNER = Qt.UserRole + 7
ROLE_ER_ID = Qt.UserRole + 8
ROLE_EXP_PK = Qt.UserRole + 9
ROLE_OWNER_COLOUR = Qt.UserRole + 20  # Hex-Farbe, z.B. #3F51B5
ROLE_HAS_IMAGE = Qt.UserRole + 30
ROLE_HAS_PDF = Qt.UserRole + 31
ROLE_HAS_NOTES = Qt.UserRole + 32
ROLE_HAS_RETEST_FLAG = Qt.UserRole + 33
ROLE_HAS_REPORT = Qt.UserRole + 34
ROLE_YEAR = Qt.UserRole + 40  # Jahresgruppe für Archived

_ER_ICON_PIXMAP = None  # cached QPixmap
_ATTACH_ICON_PIXMAP = None  # cached QPixmap
_NOTES_ICON_PIXMAP = None  # cached QPixmap
_REPORT_ICON_PIXMAP = None  # cached QPixmap


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


def _get_notes_icon_pixmap() -> QPixmap | None:
    """Lädt das Notizen-Icon als QPixmap (lazy, gecacht)."""
    """Loads and caches the Notes icon (scaled)."""
    global _NOTES_ICON_PIXMAP
    if _NOTES_ICON_PIXMAP is not None:
        return _NOTES_ICON_PIXMAP
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


def _get_report_icon_pixmap() -> QPixmap | None:
    """Lädt das Report-Icon (dasselbe wie der Smart-Chart-Button in Show
    Experiment) als QPixmap (lazy, gecacht)."""
    global _REPORT_ICON_PIXMAP
    if _REPORT_ICON_PIXMAP is not None:
        return _REPORT_ICON_PIXMAP
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


def _report_icon_rect(item, card_rect: "QRect") -> "QRect | None":
    """Berechnet die tatsächliche Position des Report-Icons auf einer
    Backlog-Karte (siehe CardRowDelegate.paint(), wo es als letztes Icon in
    der Kette Retest-Badge -> ER -> Attach -> Notes -> Report gezeichnet
    wird). Läuft dieselbe Reihenfolge/Verschiebung nach, damit Hit-Test
    (BacklogDnDTable.mousePressEvent()/mouseMoveEvent()) und tatsächliche
    Zeichenposition immer übereinstimmen, unabhängig davon, welche der
    anderen Icons für diese Karte aktiv sind. None, wenn kein Report-Icon
    gezeichnet wird (keine gespeicherten Reports für diese Series)."""
    if not bool(item.data(ROLE_HAS_REPORT)):
        return None
    right_x = card_rect.right() - 10
    center_y = card_rect.top() + (card_rect.height() // 2)

    if bool(item.data(ROLE_HAS_RETEST_FLAG)):
        right_x -= 44 + 6

    er_id = item.data(ROLE_ER_ID)
    if er_id not in (None, "", 0, "0"):
        pm_er = _get_er_icon_pixmap()
        if pm_er is not None and not pm_er.isNull():
            right_x -= pm_er.width() + 6

    has_img = item.data(ROLE_HAS_IMAGE)
    has_pdf = item.data(ROLE_HAS_PDF)
    try:
        has_attach = bool(int(has_img or 0)) or bool(int(has_pdf or 0))
    except Exception:
        has_attach = bool(has_img) or bool(has_pdf)
    if has_attach:
        pm_attach = _get_attach_icon_pixmap()
        if pm_attach is not None and not pm_attach.isNull():
            right_x -= pm_attach.width() + 6

    if bool(item.data(ROLE_HAS_NOTES)):
        pm_notes = _get_notes_icon_pixmap()
        if pm_notes is not None and not pm_notes.isNull():
            right_x -= pm_notes.width() + 6

    pm = _get_report_icon_pixmap()
    if pm is None or pm.isNull():
        return None
    iw, ih = pm.width(), pm.height()
    ix = right_x - iw
    iy = center_y - (ih // 2)
    return QRect(ix, iy, iw, ih)


class _ExpandIconButton(QPushButton):
    """"Show fullscreen" icon button - loads assets/images/expand.png (24x24,
    white on transparent, same convention as bell.png/notes.png/backlog.png)
    and draws it centered, with a soft hover highlight behind it. Custom
    paintEvent (mirrors BellButton in ui/widgets/header.py) instead of
    setIcon()/setIconSize() so the hover background can be layered under it."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFlat(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Show fullscreen")
        self.setFixedSize(26, 26)
        self.setStyleSheet("QPushButton { background: transparent; border: none; }")
        self._hovered = False
        self._icon_pm = QPixmap(resource_path("assets/images/expand.png"))

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        if self._hovered:
            p.setBrush(QColor(255, 255, 255, 40))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(self.rect(), 4, 4)

        if not self._icon_pm.isNull():
            icon_size = 18
            x = (self.width() - icon_size) // 2
            y = (self.height() - icon_size) // 2
            p.drawPixmap(x, y, self._icon_pm.scaled(
                icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        p.end()


class CardRowDelegate(QStyledItemDelegate):
    """Custom-Delegate der jede Backlog-Zeile als visuell gestaltete Karte rendert.

    Zeichnet: Prioritäts-Badge, Experimentname, Serienname, Maschine, Garn,
    Status-Farbe und optionale Icons (Anhang, ER, Notizen).
    """
    """Rendert jede Tabellenzeile als identische Karte.

    - Zeichnet die Card-Hintergründe über die ganze Zeile (wir nutzen nur Spalte 0)
    - Optional: links ein 4px Owner-Farbstreifen (ausser im Backlog)
    """

    # type: ignore[override]
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        """Zeichnet eine Backlog-Karte mit allen Metadaten und Icons."""
        if index.column() != 0:
            return  # nur Spalte 0 wird gezeichnet

        w = getattr(option, "widget", None)

        # Daten
        series_name = (index.data(ROLE_SERIES_NAME) or "").strip()
        exp_id = (index.data(ROLE_EXP_ID) or "").strip()
        machine = (index.data(ROLE_MACHINE) or "").strip()
        status_name = (index.data(ROLE_STATUS_NAME) or "").strip()
        prio = index.data(ROLE_PRIO)
        owner = (index.data(ROLE_OWNER) or "").strip()
        owner_colour = index.data(ROLE_OWNER_COLOUR)
        has_img = index.data(ROLE_HAS_IMAGE)
        has_pdf = index.data(ROLE_HAS_PDF)
        has_notes = index.data(ROLE_HAS_NOTES)
        has_retest = bool(index.data(ROLE_HAS_RETEST_FLAG))
        has_report = bool(index.data(ROLE_HAS_REPORT))
        has_attach = False
        try:
            has_attach = bool(int(has_img or 0)) or bool(int(has_pdf or 0))
        except Exception:
            has_attach = bool(has_img) or bool(has_pdf)

        # Zweite Zeile: alles kompakt nebeneinander, damit wir Höhe sparen
        subtitle_parts = []
        if exp_id:
            subtitle_parts.append(exp_id)
        if machine:
            subtitle_parts.append(machine)
        if status_name:
            subtitle_parts.append(status_name)
        if prio not in (None, "", "None"):
            subtitle_parts.append(f"Prio {prio}")
        if owner:
            subtitle_parts.append(owner)
        subtitle = "  •  ".join(subtitle_parts)

        # State
        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Card rect (mit etwas Padding)
        r = option.rect.adjusted(6, 4, -6, -4)

        # Shadow (pseudo, via 2. Rect)
        shadow = r.adjusted(2, 2, 2, 2)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 20))
        painter.drawRoundedRect(shadow, 10, 10)

        # Card background
        bg = QColor(255, 255, 255)
        if hovered:
            bg = QColor("#FAFAFA")
        if selected:
            bg = QColor("#FFF8E1")
        painter.setBrush(bg)
        painter.setPen(QPen(QColor("#E0E0E0"), 1))
        painter.drawRoundedRect(r, 10, 10)

        # Owner stripe (ausser in Backlog und Archived)
        try:
            status_id = int(index.data(ROLE_STATUS_ID) or 0)
        except Exception:
            status_id = 0

        # In "Archived" sollen die Karten nicht farblich abgehoben sein.
        if status_id not in (1, 4, 5) and owner_colour:
            qcol = QColor(str(owner_colour))
            if qcol.isValid():
                painter.setPen(Qt.NoPen)
                painter.setBrush(qcol)
                painter.drawRoundedRect(r.adjusted(0, 0, 0, 0), 10, 10)
                # Stripe "abschneiden": wir malen die Card nochmals darüber, aber mit kleinerer x-Start
                inner = r.adjusted(4, 0, 0, 0)
                painter.setBrush(bg)
                painter.setPen(QPen(QColor("#E0E0E0"), 1))
                painter.drawRoundedRect(inner, 10, 10)
                r = inner  # Textbereich

        # Text
        title_font = QFont(option.font)
        title_font.setPointSize(max(9, title_font.pointSize()))
        title_font.setBold(True)

        subtitle_font = QFont(option.font)
        subtitle_font.setPointSize(max(8, subtitle_font.pointSize() - 2))

        x = r.left() + 10
        y = r.top() + 7

        painter.setPen(QColor("#212121"))
        painter.setFont(title_font)
        painter.drawText(
            x, y + 15, series_name[:70] if series_name else "TrialSeries")

        painter.setPen(QColor("#616161"))
        painter.setFont(subtitle_font)
        painter.drawText(x, y + 32, subtitle[:110])

        # Icons (right side)
        # - Experiment Request icon
        # - Attachment icon (image and/or pdf) – not clickable, purely visual
        # - Report icon (clickable, ganz links in dieser Kette gezeichnet -
        #   siehe BacklogDnDTable._report_icon_rect(), das dieselbe
        #   Reihenfolge/Verschiebung nachrechnet, damit Hit-Test und
        #   tatsächliche Position immer übereinstimmen)
        right_x = r.right() - 10
        center_y = r.top() + (r.height() // 2)

        if has_retest:
            badge_w, badge_h = 44, 16
            ix = right_x - badge_w
            iy = center_y - (badge_h // 2)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#C1621A"))
            painter.drawRoundedRect(ix, iy, badge_w, badge_h, 4, 4)
            badge_font = QFont(option.font)
            badge_font.setPointSize(max(7, badge_font.pointSize() - 3))
            badge_font.setBold(True)
            painter.setFont(badge_font)
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(QRect(ix, iy, badge_w, badge_h), Qt.AlignCenter, "RETEST")
            right_x = ix - 6

        er_id = index.data(ROLE_ER_ID)
        if er_id not in (None, "", 0, "0"):
            pm = _get_er_icon_pixmap()
            if pm is not None and not pm.isNull():
                iw = pm.width()
                ih = pm.height()
                ix = right_x - iw
                iy = center_y - (ih // 2)
                painter.drawPixmap(ix, iy, pm)
                right_x = ix - 6

        if has_attach:
            pm = _get_attach_icon_pixmap()
            if pm is not None and not pm.isNull():
                iw = pm.width()
                ih = pm.height()
                ix = right_x - iw
                iy = center_y - (ih // 2)
                painter.drawPixmap(ix, iy, pm)
                right_x = ix - 6

        try:
            _has_notes = bool(has_notes)
        except Exception:
            _has_notes = False
        if _has_notes:
            pm = _get_notes_icon_pixmap()
            if pm is not None and not pm.isNull():
                iw = pm.width()
                ih = pm.height()
                ix = right_x - iw
                iy = center_y - (ih // 2)
                painter.drawPixmap(ix, iy, pm)
                right_x = ix - 6

        if has_report:
            pm = _get_report_icon_pixmap()
            if pm is not None and not pm.isNull():
                iw = pm.width()
                ih = pm.height()
                ix = right_x - iw
                iy = center_y - (ih // 2)
                painter.drawPixmap(ix, iy, pm)
                right_x = ix - 6

        painter.restore()

    # type: ignore[override]
    def sizeHint(self, option, index):
        """Gibt die Zeilenhöhe für eine Karte zurück."""
        # Kartenhöhe (kompakter: 2 Zeilen)
        return super().sizeHint(option, index).expandedTo(QSize(0, 46))


class BacklogDnDTable(QTableWidget):
    """Drag-and-Drop-fähige Tabelle für eine Backlog-Status-Spalte.

    Ermöglicht das Verschieben von Karten zwischen Status-Spalten via
    Mouse-Drag. Zeigt visuelles Feedback während des Drags.
    Stellt ein Kontextmenü für Kartenaktionen bereit.
    """
    """Kartenliste mit Drag&Drop zwischen Backlog-Spalten.

    Wir verschieben keine GUI-Items "physisch" per Drag&Drop, sondern
    setzen via DB den neuen Status und laden danach alle Tabellen neu.
    """

    MIME_TYPE = "application/x-ttt-trialseries"

    def __init__(self, screen, status_id: int):
        super().__init__()
        self._screen = screen
        self._status_id = int(status_id)

        # Styles/State für bessere Drag-Feedbacks
        self._base_style = self.styleSheet() or ""
        self._drag_row_original_brush = None  # type: ignore

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)

        # Karten-Look: keine Gridlines, keine Header
        self.setShowGrid(False)
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)

        self.setAlternatingRowColors(False)
        # Karten-Reihenfolge ist bereits sortiert aus SQL
        self.setSortingEnabled(False)
        self.setMouseTracking(True)

        # Kontextmenü
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_context_menu)

    # type: ignore[override]
    def mousePressEvent(self, event):
        """Intercept clicks on the Experiment Request icon on cards.

        If the user clicks the small ER icon on the right side of a card, we open the
        same read-only popup as in screen_show_experiment.
        """
        try:
            if event.button() == Qt.LeftButton:
                pos = event.pos()
                item = self.itemAt(pos)
                if item is not None:
                    rect = self.visualItemRect(item)
                    r = rect.adjusted(6, 4, -6, -4)

                    report_rect = _report_icon_rect(item, r)
                    if report_rect is not None and report_rect.contains(pos):
                        series_id = item.data(ROLE_SERIES_ID)
                        ctrl_held = bool(event.modifiers() & Qt.ControlModifier)
                        try:
                            self._screen._open_report_icon_for_series(series_id, in_new_tab=ctrl_held)
                        except Exception:
                            pass
                        return

                    er_id = item.data(ROLE_ER_ID)
                    if er_id not in (None, '', 0, '0'):
                        pm = _get_er_icon_pixmap()
                        if pm is not None and not pm.isNull():
                            iw = pm.width()
                            ih = pm.height()
                            ix = r.right() - iw - 10
                            iy = r.top() + (r.height() - ih) // 2
                            icon_rect = QRect(ix, iy, iw, ih)
                            if icon_rect.contains(pos):
                                # Open popup and swallow the click (avoid drag start)
                                try:
                                    self._screen.open_experiment_request_popup(er_id)
                                except Exception:
                                    pass
                                return
        except Exception:
            pass
        super().mousePressEvent(event)

    # type: ignore[override]
    def mouseMoveEvent(self, event):
        """Führt den Drag aus wenn die Maus weit genug bewegt wurde."""
        """Wechsel Cursor zu einer Hand, wenn die Maus ueber dem ER-Icon ist."""
        try:
            pos = event.pos()
            item = self.itemAt(pos)
            if item is not None:
                rect_full = self.visualItemRect(item)
                report_rect = _report_icon_rect(item, rect_full.adjusted(6, 4, -6, -4))
                if report_rect is not None and report_rect.contains(pos):
                    if self.cursor().shape() != Qt.PointingHandCursor:
                        self.setCursor(Qt.PointingHandCursor)
                    return super().mouseMoveEvent(event)

                er_id = item.data(ROLE_ER_ID)
                if er_id not in (None, '', 0, '0'):
                    pm = _get_er_icon_pixmap()
                    if pm is not None and not pm.isNull():
                        rect = self.visualItemRect(item)
                        r = rect.adjusted(6, 4, -6, -4)
                        iw = pm.width()
                        ih = pm.height()
                        ix = r.right() - iw - 10
                        iy = r.top() + (r.height() - ih) // 2
                        icon_rect = QRect(ix, iy, iw, ih)
                        if icon_rect.contains(pos):
                            if self.cursor().shape() != Qt.PointingHandCursor:
                                self.setCursor(Qt.PointingHandCursor)
                            return super().mouseMoveEvent(event)
        except Exception:
            pass

        # Default cursor
        if self.cursor().shape() == Qt.PointingHandCursor:
            self.unsetCursor()
        return super().mouseMoveEvent(event)

    def _set_drop_highlight(self, on: bool):
        """Hebt die Tabelle als Drop-Ziel visuell hervor."""
        """Visuelles Feedback: Ziel-Spalte hervorheben, wenn etwas darüber schwebt."""
        if on:
            self.setStyleSheet(self._base_style +
                               "QTableWidget { border: 2px dashed #2E7D32; }")
        else:
            self.setStyleSheet(self._base_style)

    def _set_drag_row_feedback(self, on: bool):
        """Dimmt die gezogene Zeile während des Drags."""
        """Visuelles Feedback: aktuell 'gehaltene' Zeile im Ursprungstisch markieren."""
        row = self.currentRow()
        if row < 0:
            return
        it = self.item(row, 0)
        if it is None:
            return

        if on:
            if self._drag_row_original_brush is not None:
                return
            self._drag_row_original_brush = it.background()
            it.setBackground(QColor("#FFF8E1"))
        else:
            if self._drag_row_original_brush is None:
                return
            it.setBackground(self._drag_row_original_brush)
            self._drag_row_original_brush = None

    def _build_drag_pixmap(self) -> QPixmap:
        """Erstellt ein Vorschau-Pixmap für die gezogene Karte."""
        """Erzeugt eine gut sichtbare 'Ghost'-Karte für den Drag (identisch zur Karte)."""
        row = self.currentRow()
        it = self.item(row, 0)
        if it is None:
            title = "TrialSeries"
            subtitle = ""
            meta = ""
        else:
            title = (it.data(ROLE_SERIES_NAME) or "TrialSeries").strip()
            exp = (it.data(ROLE_EXP_ID) or "").strip()
            mach = (it.data(ROLE_MACHINE) or "").strip()
            status_name = (it.data(ROLE_STATUS_NAME) or "").strip()
            prio = it.data(ROLE_PRIO)
            owner = (it.data(ROLE_OWNER) or "").strip()

            subtitle_parts = []
            if exp:
                subtitle_parts.append(exp)
            if mach:
                subtitle_parts.append(mach)
            if status_name:
                subtitle_parts.append(status_name)
            if prio not in (None, "", "None"):
                subtitle_parts.append(f"Prio {prio}")
            if owner:
                subtitle_parts.append(owner)
            subtitle = "  •  ".join(subtitle_parts)
            meta = ""

        w = 520
        h = 58
        pm = QPixmap(w, h)
        pm.fill(Qt.transparent)

        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)

        # Shadow
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 30))
        p.drawRoundedRect(3, 3, w - 6, h - 6, 10, 10)

        # Card
        p.setPen(QPen(QColor("#E0E0E0"), 1))
        p.setBrush(QColor(255, 255, 255, 245))
        p.drawRoundedRect(1, 1, w - 3, h - 3, 10, 10)

        title_font = QFont()
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)

        subtitle_font = QFont()
        subtitle_font.setPointSize(max(8, subtitle_font.pointSize() - 2))

        x = 16
        p.setFont(title_font)
        p.setPen(QColor("#212121"))
        p.drawText(x, 26, title[:70])

        p.setFont(subtitle_font)
        p.setPen(QColor("#616161"))
        p.drawText(x, 46, subtitle[:110])

        p.end()
        return pm

    def _selected_series_id(self):
        """Gibt die TrialSeriesID der aktuell selektierten Zeile zurück."""
        row = self.currentRow()
        if row < 0:
            return None
        item = self.item(row, 0)
        if item is None:
            return None
        return item.data(ROLE_SERIES_ID)

    def startDrag(self, supportedActions):
        """Startet den Qt-Drag mit Serien-ID als Mime-Daten."""
        series_id = self._selected_series_id()
        if series_id is None:
            return

        mime = QMimeData()
        mime.setData(self.MIME_TYPE,
                     f"{int(series_id)}|{self._status_id}".encode("utf-8"))

        drag = QDrag(self)
        drag.setMimeData(mime)

        try:
            self._set_drag_row_feedback(True)
            pm = self._build_drag_pixmap()
            drag.setPixmap(pm)
            drag.setHotSpot(pm.rect().center())
        except Exception:
            pass

        try:
            drag.exec(Qt.MoveAction)
        finally:
            try:
                self._set_drag_row_feedback(False)
            except Exception:
                pass

    def dragEnterEvent(self, event):
        """Akzeptiert Drops von anderen BacklogDnDTables."""
        if event.mimeData().hasFormat(self.MIME_TYPE):
            self._set_drop_highlight(True)
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragLeaveEvent(self, event):
        """Entfernt Drop-Highlight wenn Drag die Tabelle verlässt."""
        self._set_drop_highlight(False)
        return super().dragLeaveEvent(event)

    def dragMoveEvent(self, event):
        """Akzeptiert Drop-Moves (kontinuierliches Feedback)."""
        if event.mimeData().hasFormat(self.MIME_TYPE):
            self._set_drop_highlight(True)
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        """Verarbeitet den Drop: aktualisiert Status in DB und verschiebt die Karte."""
        self._set_drop_highlight(False)
        md = event.mimeData()
        if not md.hasFormat(self.MIME_TYPE):
            return super().dropEvent(event)

        try:
            raw = bytes(md.data(self.MIME_TYPE)).decode("utf-8")
            series_id_txt, old_status_txt = raw.split("|", 1)
            series_id = int(series_id_txt)
            old_status_id = int(old_status_txt)
        except Exception:
            event.ignore()
            return

        if old_status_id == self._status_id:
            event.ignore()
            return

        try:
            self._screen._handle_dnd_move(
                series_id, old_status_id, self._status_id)
            event.acceptProposedAction()
        except Exception:
            event.ignore()

    # ----------------------------
    # Kontextmenü (Prio/Status)
    # ----------------------------
    def _open_context_menu(self, pos: QPoint):
        """Öffnet das Kontextmenü für eine Backlog-Karte (Rechtsklick)."""
        row = self.rowAt(pos.y())
        if row < 0:
            return
        self.selectRow(row)

        it = self.item(row, 0)
        if it is None:
            return

        series_id = it.data(ROLE_SERIES_ID)
        if series_id is None:
            return

        lvl = getattr(self._screen, "_effective_access_level", lambda: 0)()
        can_rename   = bool(lvl >= 2)
        can_delete   = bool(lvl >= 4)
        can_reassign = bool(lvl >= 4)

        menu = QMenu(self)
        act_open_new = menu.addAction("↗  Open in New Tab")
        act_open_new.setEnabled(
            callable(getattr(getattr(self, "_screen", None), "on_open_in_new_window", None))
        )
        act_open_new_window = menu.addAction("🗗  Open in New Window")
        act_open_new_window.setEnabled(
            callable(getattr(getattr(self, "_screen", None), "on_open_in_new_os_window", None))
        )
        menu.addSeparator()
        act_prio = menu.addAction("Change priority…")
        act_status = menu.addAction("Change status…")
        act_rename = menu.addAction("Rename trial series…")
        act_rename.setEnabled(can_rename)
        menu.addSeparator()
        act_yarn = menu.addAction("🧵  Garn neu zuweisen…")
        act_yarn.setEnabled(can_reassign)
        act_machine = menu.addAction("⚙️  Change machine…")
        act_machine.setEnabled(can_reassign)
        act_delete = menu.addAction("🗑  Delete trial series…")
        act_delete.setEnabled(can_delete)

        chosen = menu.exec(self.viewport().mapToGlobal(pos))
        if chosen == act_open_new:
            exp_pk    = it.data(ROLE_EXP_PK)
            exp_id    = (it.data(ROLE_EXP_ID) or "").strip()
            scr       = getattr(self, "_screen", None)
            cb        = getattr(scr, "on_open_in_new_window", None)
            if callable(cb) and series_id and exp_id:
                try:
                    cb(int(exp_pk), int(series_id), exp_id)
                except Exception:
                    pass
        elif chosen == act_open_new_window:
            exp_pk    = it.data(ROLE_EXP_PK)
            exp_id    = (it.data(ROLE_EXP_ID) or "").strip()
            scr       = getattr(self, "_screen", None)
            cb        = getattr(scr, "on_open_in_new_os_window", None)
            if callable(cb) and series_id and exp_id:
                try:
                    cb(int(exp_pk), int(series_id), exp_id)
                except Exception:
                    pass
        elif chosen == act_prio:
            self._ctx_change_prio(int(series_id), it)
        elif chosen == act_status:
            self._ctx_change_status(int(series_id), it)
        elif chosen == act_rename:
            if not can_rename:
                QMessageBox.warning(self, "Keine Berechtigung",
                                    "You do not have permission to rename this trial series.")
                return
            self._ctx_rename_trialseries(int(series_id), it)
        elif chosen == act_yarn:
            if not can_reassign:
                QMessageBox.warning(self, "Keine Berechtigung",
                                    "Only superusers may change the yarn of a trial series.")
                return
            self._ctx_reassign_yarn(int(series_id), it)
        elif chosen == act_machine:
            if not can_reassign:
                QMessageBox.warning(self, "Keine Berechtigung",
                                    "Only superusers may change the machine of a trial series.")
                return
            self._ctx_reassign_machine(int(series_id), it)
        elif chosen == act_delete:
            if not can_delete:
                QMessageBox.warning(self, "Keine Berechtigung",
                                    "Only superusers may delete a trial series.")
                return
            exp_pk = it.data(ROLE_EXP_PK)
            self._ctx_delete_trialseries(int(series_id), exp_pk, it)

    def _ctx_change_prio(self, series_id: int, item: QTableWidgetItem):
        """Kontextmenü-Aktion: Priorität einer Serie ändern."""
        cur = item.data(ROLE_PRIO)
        try:
            cur_int = int(cur)
        except Exception:
            cur_int = 0

        new_val, ok = QInputDialog.getInt(
            self, "Change priority", "New priority:", cur_int, 0, 999, 1)
        if not ok:
            return

        self._screen._update_backlog_prio(series_id, int(new_val))
        self._screen.reload_all()

    def _ctx_change_status(self, series_id: int, item: QTableWidgetItem):
        """Kontextmenü-Aktion: Status einer Serie in eine andere Spalte verschieben."""
        old_id = item.data(ROLE_STATUS_ID)
        try:
            old_id_int = int(old_id)
        except Exception:
            old_id_int = self._status_id

        names = self._screen.status_names
        ids = [self._screen.status_name_to_id[n] for n in names]

        access_level = self._screen._effective_access_level()
        is_super = access_level >= 4
        is_write_user = access_level >= 2

        # Nicht-Superuser: Archived (5) und To Be Cleaned (4) grundsätzlich nicht setzbar.
        # Ausnahme: Write-User (AccessLevel >= 2) dürfen aus "To Be Cleaned" (4) heraus
        # gezielt nach "Archived" (5) wechseln.
        if not is_super:
            if old_id_int == 4 and is_write_user:
                names = [n for n in names if self._screen.status_name_to_id[n] in (4, 5)]
            else:
                names = [n for n in names if self._screen.status_name_to_id[n] not in (4, 5)]
            ids = [self._screen.status_name_to_id[n] for n in names]

        # Bereits archiviert (5) und kein Superuser: gesperrt.
        # "To Be Cleaned" (4) bleibt für Write-User offen (Wechsel nach Archived).
        if not is_super and old_id_int == 5:
            QMessageBox.warning(self, "No permission",
                                "Only superusers may change the status of 'Archived' series.")
            return
        if not is_super and old_id_int == 4 and not is_write_user:
            QMessageBox.warning(self, "No permission",
                                "Only superusers may change the status of 'To Be Cleaned' series.")
            return

        current_name = self._screen.status_id_to_name.get(old_id_int, "")
        new_name, ok = QInputDialog.getItem(self, "Change status", "New status:", names, max(
            0, names.index(current_name) if current_name in names else 0), False)
        if not ok:
            return
        new_id = self._screen.status_name_to_id.get(new_name, old_id_int)

        if int(new_id) == int(old_id_int):
            return

        # gleiche Validierung wie DnD/Dropdown
        self._screen._handle_dnd_move(
            int(series_id), int(old_id_int), int(new_id))

    def _ctx_delete_trialseries(self, series_id: int, exp_pk, item: QTableWidgetItem):
        """Kontextmenü-Aktion: Serie löschen (mit Bestätigung, nur für Admins)."""
        """Superuser: TrialSeries mitsamt allen Kindern löschen.

        Löschreihenfolge (FK-sicher):
          tblLaborXXX            (via TrialID)
          tblFeatureUsage        (via TrialID + ExtraInfo)
          tblTrialSettings       (via TrialID, CASCADE via tblTrial)
          tblTrial               (via TrialSeriesID)
          tblTrialSeriesImage    (via TrialSeriesID, falls vorhanden)
          tblTrialSeriesPDF      (via TrialSeriesID, falls vorhanden)
          tblTrialSeries         (die Series selbst)
          tblExperimente         (nur wenn keine weiteren Series für dieses Experiment)
        """
        series_name = (item.data(ROLE_SERIES_NAME) or str(series_id)).strip()

        # ── Bestätigungsdialog ─────────────────────────────────────────────
        msg = QMessageBox(self)
        msg.setWindowTitle("Delete trial series")
        msg.setIcon(QMessageBox.Warning)
        msg.setText(
            f"<b>Permanently delete this trial series?</b><br><br>"
            f"<b>{series_name}</b><br><br>"
            f"All trials, lab data and related entries will be deleted.<br>"
            f"<b>This action cannot be undone.</b>"
        )
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        msg.setDefaultButton(QMessageBox.Cancel)
        if msg.exec() != QMessageBox.Yes:
            return

        # ── Löschen in FK-sicherer Reihenfolge ────────────────────────────
        try:
            trial_rows = fetch_all(
                "SELECT [ID] FROM [tblTrial] WHERE [TrialSeriesID] = ?",
                [series_id],
            )
            trial_ids = [int(r["ID"]) for r in trial_rows]

            if trial_ids:
                placeholders = ",".join(["?"] * len(trial_ids))

                labor_tables = [
                    "tbllabortiter",
                    "tbllaborstatimatm",
                    "tbllaborstatimatds",
                    "tblLaborWaterbath",
                    "tblLaborItematLab",
                    "tblLaborItematPlus",
                    "tblLaborRapid600",
                    "tblLaborDTYoMat",
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
                        pass

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
                        [str(series_id)],
                    )
                except Exception:
                    pass

                try:
                    execute(
                        f"DELETE FROM [tblTrialSettings] WHERE [TrialID] IN ({placeholders})",
                        trial_ids,
                    )
                except Exception:
                    pass

                execute(
                    "DELETE FROM [tblTrial] WHERE [TrialSeriesID] = ?",
                    [series_id],
                )

            for opt_tbl in ("tblTrialSeriesImage", "tblTrialSeriesPDF"):
                try:
                    execute(
                        f"DELETE FROM [{opt_tbl}] WHERE [TrialSeriesID] = ?",
                        [series_id],
                    )
                except Exception:
                    pass

            execute(
                "DELETE FROM [tblTrialSeries] WHERE [ID] = ?",
                [series_id],
            )

            # tblExperimente: löschen wenn keine Series mehr vorhanden
            if exp_pk is not None:
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
                "Delete trial series",
                f"Error deleting:\n\n{e}",
            )
            return

        # ── Feature tracking ──────────────────────────────────────────────
        try:
            from db.connection import execute as _db_execute
            _db_execute(
                "INSERT INTO tblFeatureUsage (FeatureID, UserID, ExtraInfo) VALUES (?, ?, ?)",
                [6, getattr(app_meta, "current_user", {}).get("id") or getattr(app_meta, "current_user", {}).get("ID"), str(series_id)],
            )
        except Exception:
            pass

        # ── Karte aus UI entfernen und neu laden ──────────────────────────
        try:
            self._screen.reload_all()
        except Exception:
            pass

    def _ctx_reassign_yarn(self, series_id: int, item: QTableWidgetItem):
        """Kontextmenü-Aktion: Garn einer Serie neu zuweisen."""
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

        series_name = (item.data(ROLE_SERIES_NAME) or str(series_id)).strip()

        # ── Aktuelle Garnzuordnung laden (via tbltrialsettings, DISTINCT pro Ply) ──
        try:
            yarn_rows = fetch_all(
                "SELECT DISTINCT ts.Ply, ts.YarnID "
                "FROM tbltrialsettings ts "
                "JOIN tbltrial t ON t.ID = ts.TrialID "
                "WHERE t.TrialSeriesID = ? AND " + exclude_references_sql("t") + " "
                "ORDER BY ts.Ply",
                [series_id],
            )
        except Exception as e:
            QMessageBox.critical(self, "Fehler",
                                 f"Garndaten konnten nicht geladen werden:\n{e}")
            return

        if not yarn_rows:
            QMessageBox.information(self, "Keine Garndaten",
                                    "This trial series has no yarn entries.")
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
        yarn_name_list  = [str(r["Name"]) for r in all_yarns]
        yarn_id_list    = [int(r["ID"])   for r in all_yarns]

        # ── Dialog aufbauen ───────────────────────────────────────────────
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Garn neu zuweisen — {series_name}")
        dlg.setMinimumWidth(600)
        dlg.setMinimumHeight(300)
        lay = QVBoxLayout(dlg)

        lbl = QLabel(
            f"<b>{series_name}</b><br>"
            "Select the correct yarn for each ply. "
            "Use ✕ to delete a ply, '+ Add ply' to add a new one."
        )
        lbl.setWordWrap(True)
        lay.addWidget(lbl)

        # Spalten: Ply-Label | Aktuelles Garn | Neues Garn | Löschen
        tbl = QTableWidget(0, 4, dlg)
        tbl.setHorizontalHeaderLabels(["Ply", "Aktuelles Garn", "Neues Garn", ""])
        hdr = tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.Fixed)
        tbl.setColumnWidth(3, 36)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setSelectionMode(QTableWidget.NoSelection)

        rows_state = []  # list of dicts pro Ply

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
                                        "Es muss mindestens ein Ply vorhanden bleiben.")
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

        btn_add = QPushButton("+ Add ply")
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
                "SELECT ID FROM tblTrial WHERE TrialSeriesID = ? AND "
                + exclude_references_sql("") + " ORDER BY Versuchsnummer",
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
            idx     = state["cmb"].currentIndex()
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
                  AND """ + exclude_references_sql("t") + """
                """,
                [series_id, new_ply, new_yid],
            )
            if conflict_rows:
                existing = ", ".join(r["YarnName"] for r in conflict_rows)
                new_name = yarn_id_to_name.get(new_yid, f"ID {new_yid}")
                conflicts.append(f"{new_ply}: «{new_name}» conflicts with existing «{existing}»")

        if conflicts:
            QMessageBox.critical(
                self, "Yarn Conflict",
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
                deleted  = state["deleted"]
                is_new   = state["is_new"]
                idx      = state["cmb"].currentIndex()
                new_yid  = yarn_id_list[idx] if idx >= 0 and yarn_id_list else None
                new_ply  = state.get("new_ply")

                if deleted and is_new:
                    pass  # neu und sofort gelöscht → nichts tun

                elif deleted and not is_new and orig_ply and trial_ids:
                    ph = ",".join(["?"] * len(trial_ids))
                    execute(
                        f"DELETE FROM tblTrialSettings "
                        f"WHERE Ply = ? AND TrialID IN ({ph})",
                        [orig_ply] + trial_ids,
                    )
                    changes_made += 1

                elif is_new and new_yid is not None:
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
            QMessageBox.critical(self, "Fehler beim Speichern",
                                 f"Garndaten konnten nicht gespeichert werden:\n{e}")
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
                self, "Garn aktualisiert",
                f"{changes_made} change(s) saved successfully."
            )
        else:
            QMessageBox.information(self, "No changes",
                                    "No changes were made.")

    def _ctx_reassign_machine(self, series_id: int, item: QTableWidgetItem):
        """Kontextmenü-Aktion: Maschine einer Serie neu zuweisen."""
        """Superuser: Maschine einer TrialSeries nachträglich ändern."""
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QLabel,
            QDialogButtonBox,
        )

        series_name = (item.data(ROLE_SERIES_NAME) or str(series_id)).strip()

        # Aktuelle MachineID laden
        try:
            row = fetch_all(
                "SELECT s.MachineID, m.Maschine AS MachineName "
                "FROM tblTrialSeries s "
                "LEFT JOIN tblMaschine m ON m.ID = s.MachineID "
                "WHERE s.ID = ?",
                [series_id],
            )
            cur_machine_id   = int(row[0]["MachineID"]) if row and row[0]["MachineID"] else None
            cur_machine_name = str(row[0]["MachineName"] or "") if row else ""
        except Exception as e:
            QMessageBox.critical(self, "Fehler",
                                 f"Maschinendaten konnten nicht geladen werden:\n{e}")
            return

        # Alle Maschinen laden
        try:
            machines = fetch_all(
                "SELECT ID, Maschine FROM tblMaschine ORDER BY Maschine", [])
        except Exception:
            machines = []

        if not machines:
            QMessageBox.information(self, "Keine Maschinen",
                                    "Keine Maschinen in der Datenbank gefunden.")
            return

        machine_ids   = [int(r["ID"]) for r in machines]
        machine_names = [str(r["Maschine"] or "") for r in machines]

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Change machine — {series_name}")
        dlg.setMinimumWidth(420)
        lay = QVBoxLayout(dlg)

        lbl = QLabel(
            f"<b>{series_name}</b><br>"
            f"Aktuelle Maschine: <i>{cur_machine_name or '—'}</i>"
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
            QMessageBox.information(self, "No changes",
                                    "The machine was not changed.")
            return

        try:
            execute(
                "UPDATE tblTrialSeries SET MachineID = ? WHERE ID = ?",
                [new_machine_id, series_id],
            )
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Speichern",
                                 f"Maschine konnte nicht gespeichert werden:\n{e}")
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
            self, "Maschine aktualisiert",
            f"Machine successfully changed to '{new_name}'."
        )
        try:
            self._screen.reload_all()
        except Exception:
            pass

    def _ctx_rename_trialseries(self, series_id: int, item: QTableWidgetItem):
        """Kontextmenü-Aktion: Serie umbenennen (Präfix-Logik bleibt erhalten)."""
        """Rename TrialSeries name (same rules as screen_all_experiments)."""
        try:
            current_full = (item.data(ROLE_SERIES_NAME) or "").strip("\n")
        except Exception:
            current_full = ""

        prefix, editable = self._split_trialseries_prefix(current_full)

        dlg = RenameTrialSeriesDialog(
            self, prefix=prefix, current_name=editable)
        if dlg.exec() != QDialog.Accepted:
            return

        new_text = (dlg.new_name() or "").strip()
        if not new_text:
            return  # empty -> keep old

        new_full = f"{prefix}{new_text}" if prefix else new_text

        try:
            update_trialseries_name(int(series_id), new_full)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Rename trial series",
                f"Konnte den neuen Namen nicht speichern.\n\n{e}",
            )
            return

        # Update UI
        try:
            item.setData(ROLE_SERIES_NAME, new_full)
            # repaint row
            self.viewport().update()
        except Exception:
            pass

    @staticmethod
    def _split_trialseries_prefix(full_name: str) -> tuple[str, str]:
        """Trennt den Präfix (z.B. "AB") vom eigentlichen Seriennamen.

        Returns:
            (prefix, name) Tupel.
        """
        """Split a TrialSeries name into (prefix_to_keep, editable_part).

        Rules:
        - If it starts with something like "f(03 ) " (letter + (...) + spaces), keep that.
        - Else if it starts with digits followed by whitespace, keep that.
        - Otherwise prefix is empty.
        """
        s = full_name or ""

        m = re.match(r"^(\s*[A-Za-z]\([^\)]*\)\s+)(.*)$", s)
        if m:
            return m.group(1), m.group(2)

        m = re.match(r"^(\s*\d+\s+)(.*)$", s)
        if m:
            return m.group(1), m.group(2)

        return "", s


def _make_accordion_button(label: str, indent: int = 0) -> QPushButton:
    """Erstellt einen einheitlichen Akkordeon-Header-Button."""
    btn = QPushButton()
    btn.setFlat(True)
    btn.setCursor(Qt.PointingHandCursor)
    pad_left = 10 + indent * 14
    if indent == 0:
        # Jahres-Header: akzentuiert, sichtbar
        btn.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding: 5px 10px 5px {pad_left}px;
                border: none;
                border-radius: 6px;
                background: rgba(30, 120, 80, 0.08);
                font-size: 13px;
                font-weight: 600;
                color: #1a7a50;
            }}
            QPushButton:hover {{ background: rgba(30, 120, 80, 0.14); }}
        """)
    else:
        # XX-Untergruppe: dezenter
        btn.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding: 4px 10px 4px {pad_left}px;
                border: none;
                border-radius: 5px;
                background: transparent;
                font-size: 11px;
                font-weight: 500;
                color: palette(windowText);
            }}
            QPushButton:hover {{ background: rgba(0,0,0,0.04); }}
        """)
    btn.setText(label)
    return btn


class _ArchivedSeriesRow(QFrame):
    """Kompakte Serienzeile im Archived-Panel — unterstützt Drag-and-Drop zurück nach Done."""

    def __init__(self, row: dict, on_open, screen=None, parent=None):
        super().__init__(parent)
        self._series_id = row.get("TrialSeriesID")
        self._exp_pk    = row.get("ExperimentPK")
        self._exp_id    = str(row.get("Experiment ID") or row.get("ExperimentID") or "")
        self._on_open   = on_open
        self._screen    = screen
        self._drag_start_pos = None

        series_name = str(row.get("TrialSeries Name") or "")
        machine     = str(row.get("Maschine") or "")
        display     = (f"{self._exp_id}  —  {series_name}"
                       if self._exp_id and series_name
                       else (self._exp_id or series_name or "—"))

        self.setCursor(Qt.PointingHandCursor)
        self.setAcceptDrops(False)
        self.setStyleSheet("""
            QFrame {
                background: palette(window);
                border: 0.5px solid rgba(0,0,0,0.09);
                border-radius: 4px;
            }
            QFrame:hover { background: rgba(0,0,0,0.025); border-color: rgba(0,0,0,0.16); }
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 3, 8, 3)
        lay.setSpacing(8)

        # Drag handle hint
        drag_icon = QLabel("⠿")
        drag_icon.setStyleSheet("color:#bbb;font-size:14px;border:none;background:transparent;")
        drag_icon.setToolTip("Drag to move back to Done")
        lay.addWidget(drag_icon)

        lbl_name = QLabel(display)
        lbl_name.setStyleSheet(
            "font-size:12px;font-weight:500;border:none;background:transparent;")
        lay.addWidget(lbl_name, 4)

        if machine:
            lbl_machine = QLabel(machine)
            lbl_machine.setStyleSheet(
                "font-size:11px;color:palette(mid);border:none;background:transparent;")
            lbl_machine.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lay.addWidget(lbl_machine, 1)

    def mouseDoubleClickEvent(self, event):
        from PySide6.QtWidgets import QApplication as _QApp
        from PySide6.QtCore import Qt as _Qt
        ctrl_held = bool(
            _QApp.keyboardModifiers() & _Qt.KeyboardModifier.ControlModifier
        )
        if ctrl_held:
            cb = getattr(getattr(self, "_screen", None), "on_open_in_new_window", None)
            if callable(cb) and self._series_id is not None and self._exp_id:
                try:
                    cb(int(self._exp_pk), int(self._series_id), self._exp_id)
                except Exception:
                    pass
        elif callable(self._on_open) and self._series_id is not None:
            self._on_open(self._series_id, self._exp_pk, self._exp_id)

    def contextMenuEvent(self, event):
        """Rechtsklick: 'Open in New Tab'/'Open in New Window' anbieten."""
        from PySide6.QtWidgets import QMenu as _QMenu
        cb = getattr(getattr(self, "_screen", None), "on_open_in_new_window", None)
        cb_os_window = getattr(getattr(self, "_screen", None), "on_open_in_new_os_window", None)
        menu = _QMenu(self)
        act_open_new = menu.addAction("↗  Open in New Tab")
        act_open_new.setEnabled(callable(cb) and bool(self._series_id) and bool(self._exp_id))
        act_open_new_window = menu.addAction("🗗  Open in New Window")
        act_open_new_window.setEnabled(
            callable(cb_os_window) and bool(self._series_id) and bool(self._exp_id))
        menu.addSeparator()
        act_open = menu.addAction("Open")
        chosen = menu.exec(event.globalPos())
        if chosen == act_open_new and callable(cb) and self._series_id and self._exp_id:
            try:
                cb(int(self._exp_pk), int(self._series_id), self._exp_id)
            except Exception:
                pass
        elif chosen == act_open_new_window and callable(cb_os_window) and self._series_id and self._exp_id:
            try:
                cb_os_window(int(self._exp_pk), int(self._series_id), self._exp_id)
            except Exception:
                pass
        elif chosen == act_open:
            if callable(self._on_open) and self._series_id is not None:
                self._on_open(self._series_id, self._exp_pk, self._exp_id)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.LeftButton) and self._drag_start_pos is not None:
            from PySide6.QtCore import QPoint
            dist = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
            if dist < 10:
                return super().mouseMoveEvent(event)
            # Check superuser before allowing drag from Archived
            if self._screen is not None:
                lvl = self._screen._effective_access_level()
                if lvl < 4:
                    return super().mouseMoveEvent(event)
            # Start drag with status_id=5 (Archived)
            mime = QMimeData()
            mime.setData(_MIME_TYPE,
                         f"{int(self._series_id)}|5".encode("utf-8"))
            drag = QDrag(self)
            drag.setMimeData(mime)
            # Simple pixmap
            pm = QPixmap(self.size())
            pm.fill(QColor(57, 166, 80, 80))
            drag.setPixmap(pm)
            drag.setHotSpot(pm.rect().center())
            self._drag_start_pos = None
            drag.exec(Qt.MoveAction)
        else:
            super().mouseMoveEvent(event)


def _make_series_row(row: dict, on_open, screen=None) -> QWidget:
    """Erstellt eine draggable Serienzeile für das Archived-Panel."""
    return _ArchivedSeriesRow(row, on_open, screen=screen)


class _XxGroup(QWidget):
    """Aufklappbare XX-Untergruppe (zweite Ebene) im Archived-Panel."""

    def __init__(self, xx: str, rows: list[dict], on_open, screen=None, parent=None):
        super().__init__(parent)
        self._rows = rows
        self._on_open = on_open
        self._screen = screen
        self._xx = xx
        self._expanded = False
        self._visible_rows: list[dict] = list(rows)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        self._hdr = _make_accordion_button("", indent=1)
        self._hdr.clicked.connect(self._toggle)
        lay.addWidget(self._hdr)

        self._body = QWidget()
        body_lay = QVBoxLayout(self._body)
        body_lay.setContentsMargins(20, 0, 0, 2)
        body_lay.setSpacing(2)
        # Absteigend sortieren nach "ExpID - SeriesName"
        self._rows = sorted(
            self._rows,
            key=lambda r: (
                str(r.get("Experiment ID") or r.get("ExperimentID") or ""),
                str(r.get("TrialSeries Name") or "")
            ),
            reverse=True,
        )
        for r in self._rows:
            body_lay.addWidget(_make_series_row(r, self._on_open))
        lay.addWidget(self._body)

        self._update_header()
        self._body.setVisible(False)

    def _toggle(self):
        self._expanded = not self._expanded
        self._body.setVisible(self._expanded)
        self._update_header()

    def _update_header(self):
        arrow = "▼" if self._expanded else "▶"
        n = len(self._visible_rows)
        self._hdr.setText(f"  {arrow}  {self._xx}   ({n} {'Serie' if n == 1 else 'Serien'})")

    def filter(self, text: str) -> bool:
        text = text.lower().strip()
        self._visible_rows = []
        body_lay = self._body.layout()
        for i in range(body_lay.count()):
            item = body_lay.itemAt(i)
            if not item:
                continue
            w = item.widget()
            if not w:
                continue
            row = self._rows[i] if i < len(self._rows) else {}
            haystack = " ".join([
                str(row.get("TrialSeries Name") or ""),
                str(row.get("Experiment ID") or row.get("ExperimentID") or ""),
                str(row.get("Maschine") or ""),
            ]).lower()
            visible = (not text) or (text in haystack)
            w.setVisible(visible)
            if visible:
                self._visible_rows.append(row)
        any_visible = bool(self._visible_rows)
        if text and any_visible and not self._expanded:
            self._expanded = True
            self._body.setVisible(True)
        self._update_header()
        return any_visible


class _YearGroup(QWidget):
    """Aufklappbare Jahresgruppe (erste Ebene) im Archived-Panel.
    Enthält _XxGroup-Untergruppen (zweite Ebene).
    """

    def __init__(self, year: str, rows: list[dict], on_open, screen=None, parent=None):
        super().__init__(parent)
        self._rows = rows
        self._on_open = on_open
        self._screen = screen
        self._year = year
        self._expanded = False
        self._xx_groups: list[_XxGroup] = []
        self._build()

    def _build(self):
        from collections import defaultdict
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        self._hdr = _make_accordion_button("", indent=0)
        self._hdr.clicked.connect(self._toggle)
        lay.addWidget(self._hdr)

        self._body = QWidget()
        body_lay = QVBoxLayout(self._body)
        body_lay.setContentsMargins(8, 0, 0, 2)
        body_lay.setSpacing(2)

        # Nach XX gruppieren (YYYY-XX-ZZZ → Zeichen 5-6)
        by_xx: dict[str, list] = defaultdict(list)
        for r in self._rows:
            exp_id = str(r.get("Experiment ID") or r.get("ExperimentID") or "")
            parts = exp_id.split("-")
            xx = parts[1] if len(parts) >= 2 else "?"
            by_xx[xx].append(r)

        for xx in sorted(by_xx.keys(), reverse=True):
            grp = _XxGroup(xx, by_xx[xx], self._on_open, screen=self._screen, parent=self)
            self._xx_groups.append(grp)
            body_lay.addWidget(grp)

        lay.addWidget(self._body)
        self._update_header()
        self._body.setVisible(False)

    def _toggle(self):
        self._expanded = not self._expanded
        self._body.setVisible(self._expanded)
        self._update_header()

    def _update_header(self):
        arrow = "▼" if self._expanded else "▶"
        n = sum(len(g._visible_rows) for g in self._xx_groups) if self._xx_groups else len(self._rows)
        self._hdr.setText(f"  {arrow}  {self._year}   ({n} {'Serie' if n == 1 else 'Serien'})")

    def filter(self, text: str) -> bool:
        any_visible = False
        for grp in self._xx_groups:
            visible = grp.filter(text)
            grp.setVisible(visible)
            if visible:
                any_visible = True
        if text and any_visible and not self._expanded:
            self._expanded = True
            self._body.setVisible(True)
        self._update_header()
        return any_visible


_MIME_TYPE = "application/x-ttt-trialseries"  # same as BacklogTable.MIME_TYPE


class ArchivedPanel(QWidget):
    """Archived-Spalte: Suchfeld + Jahrgruppen mit kompakten Zeilen.
    Accepts drag-and-drop from To Be Cleaned (status_id=4) → Archived (status_id=5).
    Only superusers may drop here; enforced in _handle_dnd_move.
    """

    def __init__(self, on_open_experiment, screen=None, parent=None):
        super().__init__(parent)
        self._on_open  = on_open_experiment
        self._screen   = screen          # BacklogScreen reference for DnD
        self._year_groups: list[_YearGroup] = []
        self._drop_highlight = False
        self.setAcceptDrops(True)
        self._build_ui()

    # ── Drag-and-Drop ────────────────────────────────────────────────
    def _has_mime(self, event) -> bool:
        return event.mimeData().hasFormat(_MIME_TYPE)

    def _set_highlight(self, on: bool):
        self._drop_highlight = on
        self.setStyleSheet(
            "background: #e8f5e9; border: 2px dashed #39A650; border-radius: 6px;"
            if on else ""
        )

    def dragEnterEvent(self, event):
        if self._has_mime(event):
            self._set_highlight(True)
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._has_mime(event):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        self._set_highlight(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self._set_highlight(False)
        md = event.mimeData()
        if not md.hasFormat(_MIME_TYPE):
            return super().dropEvent(event)
        try:
            raw = bytes(md.data(_MIME_TYPE)).decode("utf-8")
            series_id_txt, old_status_txt = raw.split("|", 1)
            series_id    = int(series_id_txt)
            old_status_id = int(old_status_txt)
        except Exception:
            event.ignore()
            return
        if old_status_id == 5:      # already archived — no-op
            event.ignore()
            return
        if self._screen is not None:
            try:
                self._screen._handle_dnd_move(series_id, old_status_id, 5)
                event.acceptProposedAction()
            except Exception:
                event.ignore()
        else:
            event.ignore()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 8)
        root.setSpacing(6)

        # Suchfeld
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search in Archived…")
        self._search.setClearButtonEnabled(True)
        self._search.setStyleSheet("font-size:12px;padding:4px 8px;border-radius:6px;")
        self._search.textChanged.connect(self._on_search)
        root.addWidget(self._search)

        # Scroll-Area für Gruppen
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._groups_widget = QWidget()
        self._groups_layout = QVBoxLayout(self._groups_widget)
        self._groups_layout.setContentsMargins(0, 0, 0, 0)
        self._groups_layout.setSpacing(4)
        self._groups_layout.addStretch()
        scroll.setWidget(self._groups_widget)
        root.addWidget(scroll, 1)

    def load(self, rows: list[dict]):
        """Befüllt das Panel mit Archived-Daten, gruppiert nach Jahr."""
        # Alte Gruppen entfernen
        self._year_groups.clear()
        lay = self._groups_layout
        while lay.count() > 1:  # letztes item = stretch
            item = lay.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        # Nach Jahr gruppieren (aus Experiment ID "YYYY-...")
        from collections import defaultdict
        by_year: dict[str, list] = defaultdict(list)
        for r in rows:
            exp_id = str(r.get("Experiment ID") or r.get("ExperimentID") or "")
            year = exp_id[:4] if exp_id and exp_id[:4].isdigit() else "?"
            by_year[year].append(r)

        # Jahre absteigend sortieren
        for year in sorted(by_year.keys(), reverse=True):
            grp = _YearGroup(year, by_year[year], self._on_open, screen=self._screen, parent=self)
            self._year_groups.append(grp)
            lay.insertWidget(lay.count() - 1, grp)  # vor dem stretch

        self._on_search(self._search.text())

    def _on_search(self, text: str):
        for grp in self._year_groups:
            visible = grp.filter(text)
            grp.setVisible(visible)


class BacklogScreen(QWidget):
    """Kanban-Board-Screen für den Backlog.



    Zeigt alle Serien in Status-Spalten an, erlaubt Drag-and-Drop
    und öffnet Experimente per Doppelklick.
    """
    """Backlog-Screen mit fünf Spalten: Backlog, In Progress, Done, To Be Cleaned, Archived."""

    def __init__(self, on_back_home=None, on_open_experiment=None, current_user_id=None, on_open_in_new_window=None,
                 # Sidebar-Navigation (siehe ui/widgets/sidebar_nav.py) - dieselben
                 # Callbacks wie HomeScreen bekommt, da Backlog seit 2026-08-26 der
                 # Post-Login-Landing-Screen ist und daher dieselbe volle
                 # Navigation braucht (Nutzerwunsch, siehe CLAUDE.md). Anders als
                 # HomeScreen (pro Login neu gebaut) existiert BacklogScreen schon
                 # VOR dem Login (main.py::MainWindow.__init__) - access_level ist
                 # zum Konstruktionszeitpunkt daher noch nicht bekannt; die Sidebar
                 # wird deshalb lazy in showEvent() (neu) aufgebaut, siehe dort.
                 admin_box=False,
                 on_all_experiments=None, on_create_experiment=None, on_create_experiment_legacy=None,
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
                 on_open_in_new_os_window=None,
                 # Report-Symbol auf den Kanban-Karten (2026-08-27,
                 # Nutzerwunsch) - öffnet den Smart-Chart-Report-Screen
                 # direkt (mit Auswahl-Dialog bei mehreren Reports zur
                 # selben TrialSeries), siehe
                 # _open_report_icon_for_series()/ui/widgets/report_picker.py.
                 on_open_report=None,
                 # Ctrl+click on the RE icon (2026-09-01, user request: be
                 # able to have multiple SmartChart instances) - opens a
                 # fresh SmartChart instance in a new tab instead of the
                 # shared singleton.
                 on_open_report_in_new_tab=None):
        super().__init__()
        self.on_back_home = on_back_home
        self.on_open_experiment = on_open_experiment
        self.on_open_in_new_window = on_open_in_new_window
        self.on_open_in_new_os_window = on_open_in_new_os_window
        self.on_open_report = on_open_report
        self.on_open_report_in_new_tab = on_open_report_in_new_tab
        self._series_report_map: dict = {}

        self._admin_box = bool(admin_box)
        self._sidebar_nav_callbacks = dict(
            on_all_experiments=on_all_experiments,
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

        # AccessLevel global aus app_meta.current_user lesen
        try:
            user = getattr(app_meta, "current_user", {}) or {}
        except Exception:
            user = {}
        try:
            self._access_level = int(user.get("access_level") or 0)
        except Exception:
            self._access_level = 0

        # Wenn None → User kommt aus app_meta.current_user["id"]
        self.current_user_id = current_user_id

        self.tbl_backlog = None
        self.tbl_inprogress = None
        self.tbl_done = None
        self.tbl_archived = None

        self.status_name_to_id = {}
        self.status_id_to_name = {}
        self.status_names = []

        self._exp_req_field = self._resolve_experiment_request_field()

        self._load_status_lookup()
        self._build_ui()
        self.reload_all()

    def showEvent(self, event):
        """Lädt den Backlog bei jedem Öffnen neu (damit Status-Änderungen sichtbar sind)."""
        """Wird aufgerufen, wenn der Screen angezeigt wird – Backlog immer neu laden."""
        try:
            self._refresh_sidebar()
        except Exception:
            pass
        try:
            self.reload_all()
        except Exception:
            pass
        try:
            self._refresh_welcome_message()
        except Exception:
            pass

        # 5% Chance: Athena schläft still im rechten unteren Eck (siehe
        # Moduldocstring-Kommentar bei _AthenaOwl-Import).
        try:
            import random as _random
            if _ATHENA_AVAILABLE and _random.random() < 0.05:
                self._spawn_sleeping_athena()
        except Exception:
            pass

        super().showEvent(event)

    def _spawn_sleeping_athena(self):
        """5%-Easter-Egg: still schlafende Athena unten rechts."""
        if not _ATHENA_AVAILABLE:
            return
        try:
            if getattr(self, "_backlog_athena", None) is not None:
                return
            self._backlog_athena = _AthenaOwl(self)
            self._backlog_athena.place_sleeping()
            self._backlog_athena.raise_()
            self._backlog_athena.show()
        except Exception:
            pass

    # ---------- Willkommensnachricht (umgezogen aus HomeScreen, siehe
    # ui/screen_home.py::_format_welcome_text()/_fetch_welcome_message_from_db()
    # für das Original, hier auf Backlog-Groesse verkleinert) ----------

    def _format_welcome_text(self, welcome_message, first_name: str) -> str:
        msg = (welcome_message or "").strip()
        fn = (first_name or "").strip()
        if msg:
            return f"{msg}, {fn}".strip().strip(",")
        return f"Welcome, {fn}".strip()

    def _fetch_welcome_message_from_db(self):
        try:
            user_id = app_meta.current_user.get("id")
        except Exception:
            user_id = None
        if not user_id:
            return None
        try:
            rows = fetch_all("SELECT [WelcomeMessage] FROM [tblUser] WHERE [ID] = ?", [user_id])
            return rows[0]["WelcomeMessage"] if rows else None
        except Exception:
            return None

    def _refresh_welcome_message(self):
        try:
            first_name = app_meta.current_user.get("first_name") or ""
        except Exception:
            first_name = ""
        welcome_message = self._fetch_welcome_message_from_db()
        self._welcome_message_raw = welcome_message
        self._welcome_label.setText(self._format_welcome_text(welcome_message, first_name))

    def _edit_welcome_message(self):
        """Popup zum Bearbeiten der eigenen Willkommensnachricht (max. 45 Zeichen)."""
        current = (getattr(self, "_welcome_message_raw", None) or "").strip()

        dlg = QInputDialog(self)
        dlg.setWindowTitle("Welcome Message")
        dlg.setLabelText("Neue Welcome Message (max. 45 Zeichen):")
        dlg.setTextValue(current)
        dlg.setTextEchoMode(QLineEdit.EchoMode.Normal)
        le = dlg.findChild(QLineEdit)
        if le is not None:
            le.setMaxLength(45)

        if dlg.exec() != QInputDialog.DialogCode.Accepted:
            return

        value = (dlg.textValue() or "").strip()[:45]
        value_db = value if value else None

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
            return

        self._refresh_welcome_message()

    def eventFilter(self, obj, event):
        if obj is getattr(self, "_welcome_label", None):
            et = event.type()
            if et == event.Type.Enter:
                self._welcome_label.setCursor(Qt.PointingHandCursor)
                return False
            if et == event.Type.Leave:
                self._welcome_label.setCursor(Qt.ArrowCursor)
                return False
            if et == event.Type.MouseButtonPress and event.button() == Qt.LeftButton:
                self._edit_welcome_message()
                return True
            return False
        return super().eventFilter(obj, event)

    def _refresh_sidebar(self):
        """Baut die Sidebar-Navigation neu auf, falls sich der Access-Level
        seit dem letzten Aufbau geändert hat (z.B. Logout + Login als anderer
        Nutzer - BacklogScreen existiert schon vor dem ersten Login, daher ist
        der Level beim allerersten _build_ui()-Aufruf noch nicht bekannt,
        siehe __init__). Aktualisiert sonst nur die Badges. Rumpf in
        ui/widgets/sidebar_nav.py::refresh_lazy_sidebar() ausgelagert
        (2026-08-27, App-weiter Sidebar-Rollout) - geteilt mit jedem anderen
        Sidebar-Screen; `hide_self_link="backlog"` unterdrückt den eigenen
        "Backlog"-Sprungziel-Eintrag (kein Sprungziel auf sich selbst)."""
        sidebar_nav.refresh_lazy_sidebar(
            self, self._effective_access_level(), hide_self_link="backlog")

    # -------------------------------------------------
    # RECHTE
    # -------------------------------------------------
    def _effective_access_level(self) -> int:
        try:
            user = getattr(app_meta, "current_user", {}) or {}
        except Exception:
            user = {}
        try:
            if "access_level" in user:
                return int(user.get("access_level") or 0)
        except Exception:
            pass
        try:
            return int(getattr(self, "_access_level", 0) or 0)
        except Exception:
            return 0

    # -------------------------------------------------
    # USER
    # -------------------------------------------------
    def _get_effective_user_id(self):
        if self.current_user_id is not None:
            return self.current_user_id
        try:
            return app_meta.current_user.get("id")
        except Exception:
            return None


    def _get_series_backlog_owner_id(self, series_id: int):
        """Return BacklogOwner user id for a TrialSeries (or None)."""
        try:
            rows = fetch_all(
                "SELECT [BacklogOwner] FROM tblTrialSeries WHERE [ID] = ?;",
                [int(series_id)],
            )
        except Exception:
            return None
        if not rows:
            return None
        owner = rows[0].get("BacklogOwner")
        try:
            return int(owner) if owner is not None else None
        except Exception:
            return owner


    # -------------------------------------------------
    # STATUS-LOOKUP
    # -------------------------------------------------
    def _load_status_lookup(self):
        sql = """
            SELECT [ID], [BacklogStatus]
            FROM tblBacklogStatus
            ORDER BY [ID];
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


    def _resolve_experiment_request_field(self) -> str | None:
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
        if request_id in (None, '', 0, '0'):
            return
        try:
            dlg = _ExperimentRequestReadOnlyDialog(self, request_id)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def _open_report_icon_for_series(self, series_pk, in_new_tab: bool = False) -> None:
        """Klick auf das Report-Icon einer Karte: bei genau einem
        gespeicherten Report direkt öffnen, bei mehreren einen kleinen
        Auswahl-Dialog zeigen (siehe ui/widgets/report_picker.py) - gleiche
        Logik wie in screen_all_experiments.py. Ctrl+click (`in_new_tab`)
        opens a fresh SmartChart instance in a new tab instead of the
        shared singleton - falls back to the normal callback if
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

    # -------------------------------------------------
    # UI
    # -------------------------------------------------
    def _build_ui(self):
        # Keine TopBar (HeaderBar) mehr (2026-08-26, siehe screen_home.py::
        # _build_ui()-Docstring für die volle Begründung) - Glocke/Suche/
        # Accent-Farbe/Log Out sitzen jetzt in der Sidebar-Account-Gruppe.
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Sidebar-Navigation (siehe ui/widgets/sidebar.py + sidebar_nav.py,
        # geteilt mit allen anderen Screens) - Inhalt bleibt hier leer, wird
        # lazy beim ersten showEvent() befüllt (access_level ist zum
        # Zeitpunkt dieses Konstruktoraufrufs noch nicht bekannt, siehe
        # __init__-Docstring).
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        center = QFrame()
        c_lay = QVBoxLayout(center)
        c_lay.setContentsMargins(24, 24, 24, 24)
        c_lay.setSpacing(20)

        # ── Row 1: Backlog  |  In Progress ──────────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(24)

        self.tbl_backlog    = self._make_card("Backlog")
        self.tbl_inprogress = self._make_card("In Progress")

        row1.addWidget(self.tbl_backlog["card"], 1)
        row1.addWidget(self.tbl_inprogress["card"], 1)

        # ── Row 2: Done  |  (To Be Cleaned + Archived gestapelt) ─────────
        row2 = QHBoxLayout()
        row2.setSpacing(24)

        self.tbl_done = self._make_card("Done")
        row2.addWidget(self.tbl_done["card"], 1)

        # Rechte untere Spalte: TBC oben, Archived unten
        right_col = QVBoxLayout()
        right_col.setSpacing(16)

        self.tbl_tbc = self._make_card("To Be Cleaned")
        right_col.addWidget(self.tbl_tbc["card"], 1)

        # Archived Card
        archived_card = QFrame(objectName="Card")
        archived_card.setMinimumWidth(650)
        archived_card.setMaximumWidth(900)
        archived_card.setMinimumHeight(160)
        ac_lay = QVBoxLayout(archived_card)
        ac_lay.setContentsMargins(0, 0, 0, 0)
        ac_lay.setSpacing(0)

        archived_head = QFrame(objectName="CardHeader")
        ah_lay = QHBoxLayout(archived_head)
        ah_lay.setContentsMargins(12, 4, 12, 4)
        ah_lbl = QLabel("Archived")
        ah_lbl.setStyleSheet("color:white;font-weight:bold;font-size:14px;")
        ah_lay.addWidget(ah_lbl)
        ah_lay.addStretch()
        btn_archived_expand = self._expand_button()
        ah_lay.addWidget(btn_archived_expand)
        ac_lay.addWidget(archived_head)

        self._archived_panel = ArchivedPanel(
            on_open_experiment=self._open_experiment_from_archived,
            screen=self)
        ac_lay.addWidget(self._archived_panel, 1)
        btn_archived_expand.clicked.connect(
            lambda: self._expand_card("Archived", self._archived_panel, ac_lay))

        right_col.addWidget(archived_card, 1)
        row2.addLayout(right_col, 1)

        # ── Assemble ─────────────────────────────────────────────────────
        c_lay.addLayout(row1, 1)
        c_lay.addLayout(row2, 1)

        # Ganzen Kanban-Bereich in ScrollArea einwickeln → funktioniert auch
        # auf Laptops mit niedriger Auflösung
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(center)

        # ── Expanded-card view ──────────────────────────────────────────
        # Shown instead of the 5-column board when a card's fullscreen icon
        # is clicked (see _expand_card()/_collapse_card()). Deliberately NOT
        # a separate popup window - reuses this same window, so the header
        # (title/Home button) and footer stay visible; only the center
        # content swaps, with just a Close button to go back to the board.
        self._expanded_view = QWidget()
        exp_lay = QVBoxLayout(self._expanded_view)
        exp_lay.setContentsMargins(24, 20, 24, 20)
        exp_lay.setSpacing(12)

        exp_top_row = QHBoxLayout()
        self._expanded_title_lbl = QLabel("")
        self._expanded_title_lbl.setStyleSheet("font-weight:bold;font-size:18px;")
        exp_top_row.addWidget(self._expanded_title_lbl)
        exp_top_row.addStretch()
        btn_close_expanded = QPushButton("Close")
        btn_close_expanded.clicked.connect(self._collapse_card)
        exp_top_row.addWidget(btn_close_expanded)
        exp_lay.addLayout(exp_top_row)

        self._expanded_body_layout = QVBoxLayout()
        self._expanded_body_layout.setContentsMargins(0, 0, 0, 0)
        exp_lay.addLayout(self._expanded_body_layout, 1)

        self._expand_source_widget = None
        self._expand_source_layout = None

        self._card_stack = QStackedWidget()
        self._card_stack.addWidget(scroll)              # index 0: normal board
        self._card_stack.addWidget(self._expanded_view)  # index 1: expanded card
        self._card_stack.setCurrentIndex(0)

        # Kleine Willkommenszeile (2026-09-04, Nutzerwunsch: fehlte seit dem
        # Umzug von Home nach Backlog als Landing-Screen, siehe HomeScreen -
        # dort war das noch ein grosses 30px-Label). Bewusst klein gehalten
        # (kein eigener Platz-Fresser), populiert erst in showEvent()
        # (current_user ist zum Konstruktionszeitpunkt hier noch nicht
        # gesetzt - Backlog wird schon vor dem Login gebaut).
        self._welcome_label = QLabel("")
        self._welcome_label.setAlignment(Qt.AlignCenter)
        self._welcome_label.setToolTip("Click to edit your welcome message")
        self._welcome_label.setStyleSheet("color:#555;font-size:13px;font-weight:700;")
        self._welcome_label.installEventFilter(self)
        welcome_row = QHBoxLayout()
        welcome_row.setContentsMargins(24, 10, 24, 0)
        welcome_row.addStretch(1)
        welcome_row.addWidget(self._welcome_label)
        welcome_row.addStretch(1)
        # Kontext-Hilfe EN/DE/ES (Nutzerwunsch 2026-10-13, ui/widgets/multilang_help.py)
        from ui.widgets.multilang_help import make_help_button
        welcome_row.addWidget(make_help_button("How does the Backlog work?", self._open_help))
        content_layout.addLayout(welcome_row)

        content_layout.addWidget(self._card_stack, 1)
        root.addWidget(FooterBar())

    def _open_help(self):
        from ui.widgets.multilang_help import show_help
        from ui.widgets.help_texts_backlog import TEXTS
        show_help(TEXTS, self)

    def _open_experiment_request_popup_from_id(self, request_id):
        """Open the read-only Experiment Request popup (same as screen_show_experiment)."""
        if request_id in (None, '', 0, '0'):
            return
        try:
            dlg = _ExperimentRequestReadOnlyDialog(self, request_id)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def _go_home(self):
        if callable(self.on_back_home):
            self.on_back_home()

    # -------------------------------------------------
    # CARD + TABLE
    # -------------------------------------------------
    def _make_card(self, title: str):
        card = QFrame(objectName="Card")
        card.setMinimumWidth(650)
        card.setMaximumWidth(900)
        # Füllt mehr Höhe (wird zusätzlich über Stretch in _build_ui verteilt)
        card.setMinimumHeight(200)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)

        head = QFrame(objectName="CardHeader")
        h_l = QHBoxLayout(head)
        h_l.setContentsMargins(12, 4, 12, 4)
        lbl = QLabel(title)
        lbl.setStyleSheet("color:white;font-weight:bold;font-size:14px;")
        h_l.addWidget(lbl)
        h_l.addStretch()
        btn_expand = self._expand_button()
        h_l.addWidget(btn_expand)
        layout.addWidget(head)

        body = QFrame()
        b_l = QVBoxLayout(body)
        b_l.setContentsMargins(8, 6, 8, 8)

        status_id = self.status_name_to_id.get(title, 1)
        table = self._create_table(status_id)

        b_l.addWidget(table)
        layout.addWidget(body)

        btn_expand.clicked.connect(lambda: self._expand_card(title, table, b_l))

        return {"card": card, "table": table}

    def _expand_button(self) -> QPushButton:
        """Small, plain icon button added to every card header - opens that
        card's table/panel fullscreen (see _expand_card()). Useful at lower
        resolutions where e.g. the stacked Archived card gets very cramped."""
        return _ExpandIconButton()

    def _expand_card(self, title: str, body_widget, layout):
        """Swaps the center content to show `body_widget` (a card's table or
        panel) filling the whole window, instead of the 5-column board.

        Moves the actual live widget into the expanded view rather than
        duplicating it, so drag-and-drop, search fields, selections etc.
        keep working unchanged - no separate synced copy to keep in sync.
        Deliberately reuses this same window (see _build_ui) instead of a
        popup dialog, so the header/footer stay visible and there's no
        separate window to size/position.
        """
        self._expand_source_widget = body_widget
        self._expand_source_layout = layout
        self._expanded_title_lbl.setText(title)
        self._expanded_body_layout.addWidget(body_widget, 1)
        self._card_stack.setCurrentIndex(1)

    def _collapse_card(self):
        """Reverses _expand_card(): moves the widget back to its original
        card and shows the normal 5-column board again."""
        if self._expand_source_widget is not None and self._expand_source_layout is not None:
            self._expand_source_layout.addWidget(self._expand_source_widget, 1)
            self._expand_source_widget.setVisible(True)
        self._expand_source_widget = None
        self._expand_source_layout = None
        self._card_stack.setCurrentIndex(0)

    def _create_table(self, status_id: int):
        tbl = BacklogDnDTable(self, status_id)
        tbl.setColumnCount(1)
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        # Delegate: Karten zeichnen
        tbl.setItemDelegateForColumn(0, CardRowDelegate(tbl))

        # Doppelklick: Experiment öffnen
        tbl.cellDoubleClicked.connect(
            lambda r, c, t=tbl: self._on_cell_double_clicked(r, c, t))
        return tbl

    # -------------------------------------------------
    # DATEN LADEN
    # -------------------------------------------------
    def reload_all(self):
        """Lädt alle fünf Status-Boxen neu."""
        try:
            self._retest_flags_map = get_open_retest_flags_by_series()
        except Exception:
            self._retest_flags_map = {}
        # Bulk-Lookup: welche TrialSeries haben gespeicherte Smart-Chart-
        # Reports (Report-Icon auf den Karten, 2026-08-27) - eine Abfrage
        # statt einer pro Karte, gleiches Muster wie _retest_flags_map.
        try:
            _report_rows = fetch_all(
                "SELECT SeriesPK, COUNT(*) AS n FROM tblSmartChartReport "
                "WHERE IsTemplate=0 AND SeriesPK IS NOT NULL GROUP BY SeriesPK"
            )
            self._series_report_map = {int(r["SeriesPK"]): int(r["n"]) for r in _report_rows}
        except Exception:
            self._series_report_map = {}
        self._load_status_into(self.tbl_backlog["table"], 1)
        self._load_status_into(self.tbl_inprogress["table"], 2)
        self._load_status_into(self.tbl_done["table"], 3)
        self._load_status_into(self.tbl_tbc["table"], 4)
        self._load_archived()

    def _load_archived(self):
        """Lädt Archived-Daten (BacklogStatusID=5) und befüllt ArchivedPanel — sortiert nach Experiment ID absteigend."""
        er_select = ''
        if getattr(self, '_exp_req_field', None):
            try:
                er_select = f", e.[{self._exp_req_field}] AS [ExperimentRequestID]"
            except Exception:
                er_select = ''
        if not er_select:
            er_select = ', NULL AS [ExperimentRequestID]'

        sql = f"""
            SELECT
                s.[ID]              AS [TrialSeriesID],
                e.[ID]              AS [ExperimentPK],
                e.[Experiment ID]   AS [Experiment ID],
                s.[SeriesName]      AS [TrialSeries Name],
                m.[Maschine]        AS [Maschine]
                {er_select}
            FROM
                (((tblExperimente AS e
                  INNER JOIN tblTrialSeries AS s
                    ON e.[ID] = s.[ExperimentID])
                  LEFT JOIN tblMaschine AS m
                    ON m.[ID] = s.[MachineID])
                  LEFT JOIN tblBacklogStatus AS bs
                    ON bs.[ID] = s.[BacklogStatusID])
            WHERE
                s.[BacklogStatusID] = 5
            ORDER BY
                e.[Experiment ID] DESC,
                s.[ID] DESC
        """
        try:
            rows = fetch_all(sql, [])
        except Exception:
            rows = []
        self._archived_panel.load(rows)

    def _open_experiment_from_archived(self, series_id, exp_pk, exp_id_txt):
        """Öffnet ein Experiment aus dem Archived-Panel."""
        if not callable(getattr(self, "on_open_experiment", None)):
            return
        if not series_id or not exp_id_txt:
            return
        if exp_pk in (None, "", 0, "0"):
            try:
                rows = fetch_all(
                    "SELECT [ID] AS ExpPK FROM tblExperimente WHERE [Experiment ID] = ?",
                    [exp_id_txt])
                if rows:
                    exp_pk = rows[0]["ExpPK"]
            except Exception:
                return
        try:
            self.on_open_experiment(int(exp_pk), int(series_id), exp_id_txt)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))

    def _load_status_into(self, table: BacklogDnDTable, status_id: int):
        """Lädt alle TrialSeries für einen Status in die gegebene Tabelle."""

        # Sortierung (alle Boxen):
        # - Prio zuerst (1 ganz oben), hohe Zahl unten
        # - NULL-Prio immer ganz unten
        # - Danach nach Experiment-ID (neueste oben) und stabil nach Series-ID
        #
        # Hinweis: Access kennt IIF(...), MySQL (und die meisten anderen SQL-Dialekte) nicht.
        # Da das Backend bei dir MySQL ist, verwenden wir ein portables CASE WHEN.
        order_by = """
            ORDER BY
                CASE WHEN s.[BacklogPrio] IS NULL THEN 1 ELSE 0 END,
                s.[BacklogPrio] ASC,
                e.[Experiment ID] DESC,
                s.[ID] DESC
        """

        er_select = ''
        if getattr(self, '_exp_req_field', None):
            try:
                er_select = f", e.[{self._exp_req_field}] AS [ExperimentRequestID]"
            except Exception:
                er_select = ''
        if not er_select:
            er_select = ', NULL AS [ExperimentRequestID]'

        sql = f"""
            SELECT
                s.[ID]              AS [TrialSeriesID],
                e.[ID]              AS [ExperimentPK],
                e.[Experiment ID]   AS [Experiment ID],
                s.[SeriesName]      AS [TrialSeries Name],
                m.[Maschine]        AS [Maschine],
                bs.[BacklogStatus]  AS [Status],
                s.[BacklogPrio]     AS [Prio],
                u.[Username]        AS [Owner],
                u.[Colour]          AS [OwnerColour]
                , CASE WHEN tsi.[TrialSeriesID] IS NULL THEN 0 ELSE 1 END AS [HasImage]
                , CASE WHEN tsp.[TrialSeriesID] IS NULL THEN 0 ELSE 1 END AS [HasPDF]
                , CASE WHEN (s.[Notes] IS NOT NULL AND s.[Notes] <> '') THEN 1 ELSE 0 END AS [HasNotes]
                {er_select}
            FROM
                (((((tblExperimente AS e
                  INNER JOIN tblTrialSeries AS s
                    ON e.[ID] = s.[ExperimentID])
                  LEFT JOIN tblMaschine AS m
                    ON m.[ID] = s.[MachineID])
                  LEFT JOIN tblBacklogStatus AS bs
                    ON bs.[ID] = s.[BacklogStatusID])
                  LEFT JOIN tblUser AS u
                    ON u.[ID] = s.[BacklogOwner])
                  LEFT JOIN (
                        SELECT [TrialSeriesID]
                        FROM tblTrialSeriesImage
                        GROUP BY [TrialSeriesID]
                  ) AS tsi
                    ON tsi.[TrialSeriesID] = s.[ID])
                  LEFT JOIN (
                        SELECT [TrialSeriesID]
                        FROM tblTrialSeriesPDF
                        GROUP BY [TrialSeriesID]
                  ) AS tsp
                    ON tsp.[TrialSeriesID] = s.[ID]
            WHERE
                s.[BacklogStatusID] = {int(status_id)}
            {order_by}
        """
        try:
            rows = fetch_all(sql, [])
        except Exception:
            rows = []

        self._fill_table(table, rows, status_id)

    def _fill_table(self, tbl: BacklogDnDTable, rows: list[dict], status_id: int):
        tbl.blockSignals(True)
        tbl.clearContents()
        tbl.setRowCount(len(rows))

        for r_i, row in enumerate(rows):
            series_id = row.get("TrialSeriesID")
            exp_id = row.get("ExperimentID") or row.get("Experiment ID") or ""
            series_name = row.get("TrialSeries Name") or ""
            machine = row.get("Maschine") or ""
            status_name = row.get("Status") or ""
            prio = row.get("Prio")
            owner = row.get("Owner") or ""
            owner_colour = row.get("OwnerColour")

            # Text wird komplett durch Delegate gezeichnet
            item = QTableWidgetItem("")
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)

            item.setData(ROLE_SERIES_ID, series_id)
            item.setData(ROLE_EXP_ID, str(exp_id))
            item.setData(ROLE_SERIES_NAME, str(series_name))
            item.setData(ROLE_MACHINE, str(machine))
            item.setData(ROLE_STATUS_NAME, str(status_name))
            item.setData(ROLE_STATUS_ID, int(status_id))
            item.setData(ROLE_PRIO, "" if prio is None else str(prio))
            item.setData(ROLE_OWNER, str(owner))
            item.setData(ROLE_ER_ID, row.get("ExperimentRequestID"))
            item.setData(ROLE_HAS_IMAGE, row.get("HasImage", 0) or 0)
            item.setData(ROLE_HAS_PDF, row.get("HasPDF", 0) or 0)
            item.setData(ROLE_HAS_NOTES, row.get("HasNotes", 0) or 0)
            has_report = bool(getattr(self, "_series_report_map", {}).get(int(series_id))) if series_id else False
            item.setData(ROLE_HAS_REPORT, has_report)

            open_flags = getattr(self, "_retest_flags_map", {}).get(int(series_id), []) if series_id else []
            if open_flags:
                item.setData(ROLE_HAS_RETEST_FLAG, True)
                labels = []
                for f in open_flags:
                    vno = f.get("Versuchsnummer")
                    v_label = format_trial_number(vno) if vno not in (None, "") else "?"
                    labels.append(f"{v_label} · {f.get('LabSource') or ''}"
                                  + (f" — {f.get('Note')}" if f.get("Note") else ""))
                item.setToolTip("Open retest flag:\n" + "\n".join(labels))

            item.setData(ROLE_EXP_PK, row.get("ExperimentPK"))
            # Owner-Farbe: nur ausserhalb Backlog anzeigen
            if int(status_id) != 1 and owner_colour:
                item.setData(ROLE_OWNER_COLOUR, str(owner_colour))

            tbl.setItem(r_i, 0, item)
            # Muss zur Delegate-Höhe passen (kompakte 2-Zeilen-Karte)
            tbl.setRowHeight(r_i, 50)

        tbl.blockSignals(False)

    # -------------------------------------------------
    # DOPPELKLICK: Experiment öffnen
    # -------------------------------------------------
    def _on_cell_double_clicked(self, row, col, table: BacklogDnDTable):
        """Öffnet screen_show_experiment für die geklickte TrialSeries.

        Ctrl+Doppelklick öffnet in einem neuen Fenster.

        Wichtig (MySQL-Migration): Der Access→MySQL Translator mappt [Experiment ID] → ExperimentID.
        Dadurch heisst die Spalte im Resultset oft **ExperimentID** (ohne Leerzeichen).
        Zudem vermeiden wir hier ein zusätzliches Lookup per Text-ID und nehmen den PK direkt vom Item.
        """
        from PySide6.QtWidgets import QApplication as _QApp
        from PySide6.QtCore import Qt as _Qt
        ctrl_held = bool(
            _QApp.keyboardModifiers() & _Qt.KeyboardModifier.ControlModifier
        )
        open_fn = (
            self.on_open_in_new_window
            if ctrl_held and callable(getattr(self, "on_open_in_new_window", None))
            else self.on_open_experiment
        )
        if not callable(open_fn):
            return

        item = table.item(row, 0)
        if item is None:
            return

        series_id = item.data(ROLE_SERIES_ID)
        exp_id_txt = (item.data(ROLE_EXP_ID) or "").strip()
        exp_pk = item.data(ROLE_EXP_PK)

        if not series_id or not exp_id_txt:
            return

        # exp_pk ist im Normalfall bereits gesetzt (aus der Hauptquery)
        if exp_pk in (None, "", 0, "0"):
            # Fallback: wenn aus irgendeinem Grund kein PK am Item hängt
            try:
                rows = fetch_all(
                    "SELECT [ID] AS ExpPK FROM tblExperimente WHERE [Experiment ID] = ?",
                    [exp_id_txt],
                )
                if rows and "ExpPK" in rows[0]:
                    exp_pk = rows[0]["ExpPK"]
            except Exception:
                return

        try:
            exp_pk_int = int(exp_pk)
        except Exception:
            return

        try:
            series_pk_int = int(series_id)
        except Exception:
            series_pk_int = series_id

        try:
            open_fn(exp_pk_int, series_pk_int, exp_id_txt)
        except Exception as e:
            try:
                QMessageBox.critical(
                    self,
                    "Error opening",
                    f"Experiment could not be opened.\n\n"
                    f"ExperimentID: {exp_id_txt}\n"
                    f"ExpPK: {exp_pk_int} / SeriesPK: {series_pk_int}\n\n"
                    f"{e}",
                )
            except Exception:
                pass

    # -------------------------------------------------
    # PRIO ÄNDERN (wird vom Kontextmenü aufgerufen)
    # -------------------------------------------------
    def _update_backlog_prio(self, series_id, new_prio):
        sql = """
            UPDATE tblTrialSeries
            SET [BacklogPrio] = ?
            WHERE [ID] = ?;
        """
        execute(sql, [new_prio, series_id])

    # -------------------------------------------------
    # STATUS ÄNDERN / DRAG&DROP
    # -------------------------------------------------
    def _handle_dnd_move(self, series_id: int, old_status_id: int, new_status_id: int):
        """Wird von Drag&Drop-Tabellen aufgerufen."""
        user_id = self._get_effective_user_id()

        if user_id is None:
            QMessageBox.warning(
                self,
                "Keine Berechtigung",
                "Du bist nicht eingeloggt. Bitte zuerst einloggen.",
            )
            return

        access_level = self._effective_access_level()
        is_super = access_level >= 4

        # Ausnahme: "To Be Cleaned" (4) -> "Archived" (5) darf von JEDEM Write-User
        # (AccessLevel >= 2) ausgeführt werden, unabhängig vom Owner.
        is_tbc_to_archived = (old_status_id == 4 and new_status_id == 5 and access_level >= 2)

        # Statuswechsel-Regel:
        # - Ausnahme: Wenn ein Item aktuell im Backlog ist (old_status_id == 1), darf auch ein Nicht-Owner den Status ändern.
        # - Sonst dürfen Statusänderungen nur durch den Owner oder einen Superuser erfolgen.
        if old_status_id != 1 and not is_super and not is_tbc_to_archived:
            owner_id = self._get_series_backlog_owner_id(series_id)
            try:
                is_owner = (owner_id is not None) and (int(owner_id) == int(user_id))
            except Exception:
                is_owner = False

            if not is_owner:
                QMessageBox.warning(
                    self,
                    "Keine Berechtigung",
                    "Only the owner or a superuser may change the status. "
                    "Exception: Items with status 'Backlog' may be taken in progress by all users.",
                )
                return


        # Wechsel nach/von Archived (5) nur für Superuser.
        # Ausnahme: "To Be Cleaned" -> "Archived" ist für alle Write-User erlaubt.
        if (old_status_id == 5 or new_status_id == 5) and not is_tbc_to_archived:
            if not is_super:
                QMessageBox.warning(
                    self,
                    "No permission",
                    "Only superusers may set or remove the 'Archived' status.",
                )
                return

        # -> To Be Cleaned (4): always superuser-only, regardless of the old status.
        # Important for retest flags (db/retest_flags.py): a flagged series lands
        # in "Backlog" (1); the old rule only checked old==3 here and let a direct
        # jump 1 -> 4 slip through under the "Backlog" exception above - exactly
        # the checkpoint where open flags get resolved must stay superuser-exclusive.
        if new_status_id == 4 and old_status_id != 4 and not is_super:
            QMessageBox.warning(
                self,
                "No permission",
                "Only superusers may move a series to 'To Be Cleaned'.",
            )
            return

        # To Be Cleaned (4) → Backlog/In Progress/Done: nur Superuser
        if old_status_id == 4 and new_status_id in (1, 2, 3) and not is_super:
            QMessageBox.warning(
                self,
                "No permission",
                "Only superusers may move a series back from 'To Be Cleaned'.",
            )
            return

        # Joker-Maschine Regel: von Backlog weg nur mit Nicht-Joker-Maschine
        new_machine_id = None
        if old_status_id == 1 and new_status_id != 1:
            if self._series_has_joker_machine(series_id):
                dlg = MachineSelectDialog(self)
                if dlg.exec() != QDialog.Accepted:
                    return
                new_machine_id = dlg.get_selected_machine_id()
                if new_machine_id is None:
                    return

        self._update_backlog_status(
            series_id, new_status_id, old_status_id, user_id, new_machine_id)

        if new_status_id == 4:
            # "To Be Cleaned" is already superuser-exclusive (see check above) -
            # this step counts as sign-off on any open retest flags of this series.
            try:
                resolve_retest_flags_for_series(series_id, user_id)
            except Exception:
                pass

        self.reload_all()

    def _series_has_joker_machine(self, series_id) -> bool:
        sql = """
            SELECT
                s.[ID]           AS [SeriesID],
                m.[ID]           AS [MachineID],
                m.[IsJoker]      AS [IsJoker]
            FROM tblTrialSeries AS s
            LEFT JOIN tblMaschine AS m
                ON m.[ID] = s.[MachineID]
            WHERE s.[ID] = ?;
        """
        try:
            rows = fetch_all(sql, [series_id])
        except Exception:
            return False
        if not rows:
            return False
        val = rows[0].get("IsJoker")
        try:
            return bool(int(val))
        except Exception:
            return bool(val)

    def _update_backlog_status(self, series_id, new_status, old_status, user_id, new_machine_id=None):
        # Wenn zurück in Backlog und Joker → OriginalJoker wieder setzen
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

        set_owner = (old_status == 1 and new_status !=
                     1 and user_id is not None)

        if set_owner and new_machine_id is not None:
            sql = """
                UPDATE tblTrialSeries
                SET [BacklogStatusID] = ?, [BacklogOwner] = ?, [MachineID] = ?
                WHERE [ID] = ?;
            """
            params = [new_status, user_id, new_machine_id, series_id]
        elif set_owner:
            sql = """
                UPDATE tblTrialSeries
                SET [BacklogStatusID] = ?, [BacklogOwner] = ?
                WHERE [ID] = ?;
            """
            params = [new_status, user_id, series_id]
        elif new_machine_id is not None:
            sql = """
                UPDATE tblTrialSeries
                SET [BacklogStatusID] = ?, [MachineID] = ?
                WHERE [ID] = ?;
            """
            params = [new_status, new_machine_id, series_id]
        else:
            sql = """
                UPDATE tblTrialSeries
                SET [BacklogStatusID] = ?
                WHERE [ID] = ?;
            """
            params = [new_status, series_id]

        execute(sql, params)

        # Timestamp-Fallback beim Erreichen von "Done": tblTrial.Timestamp wird
        # eigentlich beim Editieren des jeweils letzten Tension-Feldes gestempelt
        # (siehe screen_show_experiment.py::_save_all(), YarnTensionAfterJet/
        # W3Tension) - Trials, bei denen das nie passiert ist, bleiben sonst
        # dauerhaft NULL und fallen aus jeder zeitbasierten Auswertung (Stats
        # Suite etc.) heraus. Nur NULL-Zeilen heilen, ein bereits gesetzter
        # (echter) Tension-Timestamp wird nie überschrieben. (2026-08-20,
        # explizite Nutzeranfrage)
        if new_status == 3 and old_status != 3:
            try:
                execute(
                    "UPDATE tblTrial SET [Timestamp] = NOW() "
                    "WHERE [TrialSeriesID] = ? AND [Timestamp] IS NULL;",
                    [series_id],
                )
            except Exception as e:
                import traceback
                print(f"[Timestamp-Fallback] Fehler fuer series_id={series_id}: {e}")
                traceback.print_exc()

        # Notifications erstellen wenn Status → Done (ID 3)
        if new_status == 3 and old_status != 3:
            try:
                from ui.notifications import create_done_notifications
                n = create_done_notifications(
                    series_id=series_id,
                    sender_user_id=user_id,
                )
                print(f"[Notification] {n} notification(s) created for series_id={series_id}")
            except Exception as e:
                import traceback
                print(f"[Notification] Fehler: {e}")
                traceback.print_exc()


class MachineSelectDialog(QDialog):
    """Dialog zur Auswahl einer Nicht-Joker-Maschine."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select machine")
        self.setModal(True)

        # lokal, um Imports oben schlank zu halten
        from PySide6.QtWidgets import QComboBox
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
            ORDER BY [Maschine];
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


class RenameTrialSeriesDialog(QDialog):
    """Dialog zum Umbenennen des editierbaren Teils eines TrialSeries-Namens.

    Der Präfix (z.B. 'f(03 ) ' oder '03 ') bleibt bestehen und wird nicht editierbar angezeigt.
    """

    def __init__(self, parent=None, prefix: str = "", current_name: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Rename trial series")
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        info = QLabel("Neuen TrialSeries Namen eingeben.")
        lay.addWidget(info)

        if prefix:
            pref = QLabel(f"Prefix (kept): <b>{prefix}</b>")
            pref.setTextFormat(Qt.RichText)
            lay.addWidget(pref)

        self._edit = QLineEdit(self)
        self._edit.setText(current_name or "")
        self._edit.selectAll()
        lay.addWidget(self._edit)

        btn_row = QHBoxLayout()
        btn_row.addItem(QSpacerItem(
            0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        but_ok = QPushButton("OK", self)
        but_cancel = QPushButton("Abbrechen", self)
        but_ok.clicked.connect(self.accept)
        but_cancel.clicked.connect(self.reject)
        btn_row.addWidget(but_ok)
        btn_row.addWidget(but_cancel)
        lay.addLayout(btn_row)

    def new_name(self) -> str:
        try:
            return self._edit.text()
        except Exception:
            return ""