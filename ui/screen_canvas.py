from __future__ import annotations
# ui/screen_canvas.py
"""Freier Zeichen-/Annotations-Canvas für TrippleT (CanvasScreen).

Ermöglicht das Laden von Bildern, PDFs, Excel- und Word-Dokumenten sowie
Keyence VK4-Dateien auf eine freie Zeichenfläche (QGraphicsScene).

Features:
  - Mehrere Bilder gleichzeitig auf dem Canvas platzieren, verschieben, skalieren, rotieren
  - Annotations-Tools: Pan, Pfeil, Ellipse, Rechteck, Freihand, Text, Highlight, Marker, Radierer, Verschieben
  - Farb- und Strichstärken-Auswahl
  - Undo (bis 10 Schritte) via Snapshot-Stack
  - Gitternetz-Overlay (konfigurierbare Teilungen)
  - Hintergrundfarbe ändern
  - Projekt speichern/laden (.ttcanvas, JSON-Format)
  - VK4-Kanal-Toggle für selektierte VK4-Bilder
  - Pinch-to-Zoom (Touch-Gesten)
  - Clipboard-Paste (Ctrl+V)

Datei-Unterstützung: PNG/JPG/BMP/WEBP, VK4, PDF, Excel, Word
(gleiche Hilfsfunktionen wie screen_image_compare.py)
"""

# ui/screen_canvas.py

import copy
import json
import math
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import (
    QPoint, QPointF, QRectF, Qt, Signal, QTimer, QObject, QRunnable, QThreadPool,
)
from PySide6.QtGui import (
    QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPen, QPixmap,
)
from PySide6.QtWidgets import (
    QColorDialog, QDialog, QFileDialog, QFrame, QGraphicsItem, QGraphicsObject,
    QGraphicsScene, QGraphicsView, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
    QSizePolicy, QSpinBox, QSplitter, QVBoxLayout, QWidget,
    QTreeWidget, QTreeWidgetItem
)

from db.connection import get_connection
from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav

# ---------------------------------------------------------------------------
# Files as images + DB: Qt-free since 2026-11-13 (ui/doc_render.py, db/image_compare.py - shared with
# Image Compare and the web version; the duplicated helpers of this screen are gone)
# ---------------------------------------------------------------------------
from ui.screen_image_compare import (  # noqa: E402,F401
    VK4_CH_COLOR_LIGHT, VK4_CH_COLOR_PEAK, VK4_CH_HEIGHT_LIGHT, VK4_CH_HEIGHT_PEAK, VK4_CH_LABELS, VK4_CH_LIGHT_INT,
    VK4_CH_ORDER, _excel_sheet_names, _is_excel, _is_pdf, _is_vk4, _is_word, _load_excel_as_pixmap,
    _load_pdf_as_pixmap, _load_vk4_as_pixmap, _load_vk4_channel, _load_word_as_pixmap, _pdf_page_count,
    _pil_to_pixmap, _vk4_available_channels, _word_page_count, _word_to_pdf_buf, _xlsx_read_rows,
)
_xlsx_sheet_names = _excel_sheet_names


def _load_pixmap_from_path(path: str, vk4_channel: str = "") -> "Optional[QPixmap]":
    """File as QPixmap (image, VK4, first PDF / Word page, first Excel sheet)."""
    if _is_vk4(path):
        return _load_vk4_channel(path, vk4_channel) if vk4_channel else _load_vk4_as_pixmap(path)
    if _is_pdf(path):
        return _load_pdf_as_pixmap(path, page=0)[0]
    if _is_excel(path):
        return _load_excel_as_pixmap(path, sheet=0)[0]
    if _is_word(path):
        return _load_word_as_pixmap(path, page=0)[0]
    pm = QPixmap(path)
    return pm if not pm.isNull() else None


TOOL_PAN       = "pan"
TOOL_ARROW     = "arrow"
TOOL_ELLIPSE   = "ellipse"
TOOL_RECT      = "rect"
TOOL_FREE      = "free"
TOOL_TEXT      = "text"
TOOL_ERASER    = "eraser"
TOOL_MOVE      = "move"
TOOL_HIGHLIGHT = "highlight"
TOOL_MARKER    = "marker"

_ERASER_RADIUS = 28
_MARKER_CHARS  = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
_UNDO_LIMIT    = 10

ANNO_COLORS = {
    "red":    QColor(220,  50,  50),
    "yellow": QColor(240, 200,   0),
    "green":  QColor( 50, 200,  80),
    "white":  QColor(255, 255, 255),
    "blue":   QColor( 50, 130, 255),
}

_DEFAULT_BG = QColor(30, 30, 30)


# ---------------------------------------------------------------------------
# Undo-State: vollständiger Snapshot des Canvas-Zustands
# ---------------------------------------------------------------------------
@dataclass
class _CanvasSnapshot:
    """Speichert einen vollständigen Canvas-Zustand für Undo (Bilder + Annotationen + Hintergrund)."""
    """Speichert einen vollständigen Zustand für Undo."""
    annotations: list          # Liste von dicts (serialisierbar)
    images: list               # Liste von dicts (serialisierbar)
    bg_color: str              # Hintergrundfarbe als Hex-String


# ---------------------------------------------------------------------------
# Annotation
# ---------------------------------------------------------------------------
@dataclass
class Annotation:
    """Datenklasse für eine einzelne Annotation (Linie, Pfeil, Ellipse, Text usw.)."""
    tool:   str
    color:  str
    points: List[Tuple[float, float]] = field(default_factory=list)
    text:   str = ""
    size:   int = 2


def _get_multiline_text(parent, title: str, label: str) -> Tuple[str, bool]:
    """QInputDialog.getMultiLineText(), but with the input field's colors
    forced explicitly instead of relying purely on the app-wide stylesheet.

    Reported bug: the built-in dialog's QPlainTextEdit rendered as (nearly)
    unreadable dark-on-dark for the user despite theme.py's app-wide
    QPlainTextEdit/QTextEdit QSS rule resolving correctly to white/dark in
    a direct palette check here - some Windows/Qt combination apparently
    doesn't fully propagate that app-wide rule to this specific widget.
    Setting the stylesheet directly on the instance sidesteps that, since a
    widget's own stylesheet always wins over an inherited one. Same helper
    duplicated in screen_image_compare.py (no shared canvas-utils module).
    """
    dlg = QInputDialog(parent)
    dlg.setInputMode(QInputDialog.TextInput)
    dlg.setOption(QInputDialog.UsePlainTextEditForTextInput, True)
    dlg.setWindowTitle(title)
    dlg.setLabelText(label)
    for edit in dlg.findChildren(QPlainTextEdit):
        edit.setStyleSheet("QPlainTextEdit { background-color: #ffffff; color: #2b2b2b; }")
    ok = dlg.exec() == QDialog.Accepted
    return dlg.textValue(), ok


from db.image_compare import (  # noqa: E402,F401
    build_full_path as _build_full_path, fetch_canvas_series_groups as _fetch_series_groups,
    fetch_images_for_series as _fetch_images_for_series, fetch_pdfs_for_series as _fetch_pdfs_for_series,
)


class _PixmapSignals(QObject):
    """Qt-Signale für den asynchronen Pixmap-Loader."""
    done = Signal(object, object)

class _PixmapLoader(QRunnable):
    """Hintergrund-Worker: prüft ob ein Dateipfad existiert (für schnelle Vorschau)."""
    def __init__(self, path, meta, signals):
        super().__init__()
        self._path = path; self._meta = meta; self._signals = signals
        self.setAutoDelete(True)
    def run(self):
        try:
            exists = bool(self._path and os.path.isfile(self._path))
        except Exception:
            exists = False
        self._signals.done.emit(self._path if exists else None, self._meta)

_pool = QThreadPool.globalInstance()
_pool.setMaxThreadCount(4)


class _RenderSignals(QObject):
    """Qt-Signale für den asynchronen Render-Worker."""
    done = Signal(object, object, object)   # (QPixmap|None, err_str|None, meta)


class _RenderWorker(QRunnable):
    """Rendert PDF/Excel/Word-Seiten im Hintergrund-Thread."""
    def __init__(self, path: str, meta: dict, signals: "_RenderSignals"):
        super().__init__()
        self._path    = path
        self._meta    = meta
        self._signals = signals
        self.setAutoDelete(True)

    def run(self):
        pm = err = None
        try:
            if _is_pdf(self._path):
                pm, err = _load_pdf_as_pixmap(self._path,
                              page=int(self._meta.get("_pdf_page") or 0))
            elif _is_excel(self._path):
                pm, err = _load_excel_as_pixmap(self._path,
                              sheet=int(self._meta.get("_excel_sheet") or 0))
            elif _is_word(self._path):
                pm, err = _load_word_as_pixmap(self._path,
                              page=int(self._meta.get("_word_page") or 0))
        except Exception as e:
            err = str(e)
        self._signals.done.emit(pm, err, self._meta)


# ---------------------------------------------------------------------------
# Loading Overlay
# ---------------------------------------------------------------------------
class _LoadingOverlay(QWidget):
    """Halbtransparenter Overlay mit animiertem Fortschrittsbalken."""

    def __init__(self, parent: "QWidget"):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._progress = 0
        self._text = "Loading..."
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.hide()

    def start(self, text: str = "Loading..."):
        self._text = text
        self._progress = 0
        self.resize(self.parent().size())
        self.raise_()
        self.show()
        self._timer.start(30)

    def stop(self):
        self._timer.stop()
        self.hide()

    def finish(self):
        self._timer.stop()
        self._progress = 100
        self.update()
        QTimer.singleShot(300, self.stop)

    def _tick(self):
        if self._progress < 90:
            self._progress = min(90, self._progress + 2)
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(0, 0, 0, 160))
        p.setPen(QColor(220, 220, 220))
        f = QFont(); f.setPointSize(10); p.setFont(f)
        p.drawText(0, h // 2 - 28, w, 24, Qt.AlignCenter, self._text)
        bar_w = min(w - 60, 320)
        bar_h = 10
        bar_x = (w - bar_w) // 2
        bar_y = h // 2 - 5
        p.setBrush(QColor(60, 60, 60)); p.setPen(Qt.NoPen)
        p.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 5, 5)
        fill_w = int(bar_w * self._progress / 100)
        if fill_w > 0:
            p.setBrush(QColor(57, 166, 80))
            p.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 5, 5)
        p.end()


class CanvasImageItem(QGraphicsObject):
    """Bewegliches, skalierbares und rotierbares Bild-Item auf dem Canvas.

    Unterstützt:
    - Maus-Drag (im Pan-Modus)
    - Pinch-to-Zoom/Rotate (Touch)
    - Doppelklick: auf 90°-Raster einrasten
    - Ctrl+Scroll: Bild skalieren
    """
    def __init__(self, pixmap, label="", parent=None):
        super().__init__(parent)
        self._pixmap         = pixmap
        self._label          = label
        self._vk4_channel:   str = ""      # aktiver VK4-Kanal (leer = kein VK4)
        self._scale_f        = 1.0
        self._angle          = 0.0
        self._pinch_start_sc = 1.0
        self._pinch_start_an = 0.0
        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges,
        )
        self.setAcceptHoverEvents(True)
        try:
            self.grabGesture(Qt.PinchGesture)
        except Exception:
            pass
        self.setCacheMode(QGraphicsItem.NoCache)

    def _notify_view_bounds(self):
        """Informiert den CanvasView dass sich die Bounds eines Items geändert haben."""
        try:
            sc = self.scene()
            if sc is None:
                return
            for view in sc.views():
                if hasattr(view, "update_canvas_bounds"):
                    view.update_canvas_bounds()
        except Exception:
            pass

    def boundingRect(self):
        """Gibt das Bounding-Rect des Pixmaps zurück."""
        if self._pixmap.isNull():
            return QRectF(0, 0, 100, 100)
        return QRectF(self._pixmap.rect())

    def paint(self, painter, option, widget=None):
        """Zeichnet das Pixmap mit Label-Overlay und Selektions-Rahmen."""
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(0, 0, self._pixmap)
        r = self.boundingRect()
        painter.fillRect(QRectF(0, 0, r.width(), 20), QColor(0, 0, 0, 140))
        painter.setPen(QColor(220, 220, 220))
        f = QFont(); f.setPointSize(9); painter.setFont(f)
        painter.drawText(QRectF(4, 2, r.width()-8, 16),
                         Qt.AlignLeft | Qt.AlignVCenter, self._label)
        if self.isSelected():
            painter.setPen(QPen(QColor(57, 166, 80), 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.boundingRect().adjusted(1, 1, -2, -2))

    def set_scale(self, s):
        """Setzt den Skalierungsfaktor (0.05–20.0)."""
        self._scale_f = max(0.05, min(20.0, s))
        self.setScale(self._scale_f)
        self._notify_view_bounds()

    def set_angle(self, a):
        """Setzt den Rotationswinkel in Grad."""
        self._angle = a % 360
        self.setRotation(self._angle)
        self._notify_view_bounds()

    def swap_pixmap(self, pm: "QPixmap"):
        """Tauscht das Pixmap aus (für VK4-Kanal-Wechsel)."""
        self._pixmap = pm
        self.prepareGeometryChange()
        self.update()
        self._notify_view_bounds()

    def itemChange(self, change, value):
        try:
            if change in (
                QGraphicsItem.ItemPositionHasChanged,
                QGraphicsItem.ItemTransformHasChanged,
                QGraphicsItem.ItemSelectedHasChanged,
            ):
                self._notify_view_bounds()
        except Exception:
            pass
        return super().itemChange(change, value)

    def _pan_tool_active(self) -> bool:
        """Gibt True zurück wenn der Pan-Modus aktiv ist (Items sind dann verschiebbar)."""
        try:
            sc = self.scene()
            if sc is None:
                return False
            for view in sc.views():
                if getattr(view, "_active_tool", None) == TOOL_PAN:
                    return True
        except Exception:
            pass
        return False

    def sceneEvent(self, ev):
        """Verarbeitet Pinch-Gesten für Zoom und Rotation."""
        if ev.type() == ev.Type.Gesture:
            if not self._pan_tool_active():
                return False
            try:
                g = ev.gesture(Qt.PinchGesture)
                if g:
                    st = g.state()
                    if st == Qt.GestureState.GestureStarted:
                        self._pinch_start_sc = self._scale_f
                        self._pinch_start_an = self._angle
                    elif st in (Qt.GestureState.GestureUpdated,
                                Qt.GestureState.GestureFinished):
                        self.set_scale(self._pinch_start_sc * g.totalScaleFactor())
                        self.set_angle(self._pinch_start_an + g.totalRotationAngle())
            except Exception:
                pass
            return True
        return super().sceneEvent(ev)

    def mouseDoubleClickEvent(self, ev):
        """Doppelklick: rastet den Rotationswinkel auf das nächste 90°-Vielfache ein."""
        if not self._pan_tool_active():
            ev.ignore()
            return
        nearest = round(self._angle / 90) * 90
        if abs((self._angle % 360) - (nearest % 360)) < 0.5:
            self.set_angle(self._angle + 90)
        else:
            self.set_angle(float(nearest))
        ev.accept()

    @property
    def pixmap(self):
        return self._pixmap


class AnnotationLayer(QGraphicsItem):
    """Transparenter Graphics-Layer über allen Bildern für Annotations-Zeichnungen.

    Liegt immer im Vordergrund (zValue 1000). Verwaltet die Liste der Annotations
    und zeichnet sie via _draw().
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._annotations  = []
        self._current_anno = None
        self.setZValue(1000)
        self.setFlag(QGraphicsItem.ItemIsMovable,    False)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setAcceptedMouseButtons(Qt.NoButton)

    def boundingRect(self):
        return QRectF(-5000, -5000, 10000, 10000)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        for anno in self._annotations + ([self._current_anno] if self._current_anno else []):
            self._draw(painter, anno)

    def _draw(self, p, anno):
        """Zeichnet eine einzelne Annotation (Pfeil, Ellipse, Freihand, Text usw.)."""
        if not anno.points:
            return
        if anno.tool in (TOOL_ARROW, TOOL_ELLIPSE, TOOL_RECT, TOOL_HIGHLIGHT) \
                and len(anno.points) < 2:
            return
        p.save()
        color = ANNO_COLORS.get(anno.color, QColor(220, 50, 50))
        pw    = anno.size
        p.setPen(QPen(color, pw, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        pts = [QPointF(x, y) for x, y in anno.points]

        if anno.tool == TOOL_ARROW and len(pts) >= 2:
            s, e = pts[0], pts[-1]
            p.drawLine(s, e)
            dx, dy = e.x()-s.x(), e.y()-s.y()
            ln = math.hypot(dx, dy)
            if ln > 0:
                ux, uy = dx/ln, dy/ln
                sz = 8 + pw*3
                p.drawLine(e, QPointF(e.x()-sz*ux+sz*.4*uy, e.y()-sz*uy-sz*.4*ux))
                p.drawLine(e, QPointF(e.x()-sz*ux-sz*.4*uy, e.y()-sz*uy+sz*.4*ux))
        elif anno.tool == TOOL_ELLIPSE and len(pts) >= 2:
            x1,y1=pts[0].x(),pts[0].y(); x2,y2=pts[-1].x(),pts[-1].y()
            p.drawEllipse(QRectF(min(x1,x2),min(y1,y2),abs(x2-x1),abs(y2-y1)))
        elif anno.tool == TOOL_RECT and len(pts) >= 2:
            x1,y1=pts[0].x(),pts[0].y(); x2,y2=pts[-1].x(),pts[-1].y()
            p.drawRect(QRectF(min(x1,x2),min(y1,y2),abs(x2-x1),abs(y2-y1)))
        elif anno.tool == TOOL_FREE and len(pts) >= 2:
            for i in range(len(pts)-1):
                p.drawLine(pts[i], pts[i+1])
        elif anno.tool == TOOL_HIGHLIGHT and len(pts) >= 2:
            x1,y1=pts[0].x(),pts[0].y(); x2,y2=pts[-1].x(),pts[-1].y()
            hi = QColor(color); hi.setAlpha(60)
            p.setBrush(hi); p.setPen(Qt.NoPen)
            p.drawRect(QRectF(min(x1,x2),min(y1,y2),abs(x2-x1),abs(y2-y1)))
        elif anno.tool == TOOL_TEXT and pts:
            p.setPen(color)
            f = QFont(); f.setPointSize(8+pw*2); f.setBold(True); p.setFont(f)
            fm = p.fontMetrics()
            x, y = pts[0].x(), pts[0].y()
            for i, line in enumerate(anno.text.split("\n")):
                p.drawText(QPoint(x, y + i * fm.lineSpacing()), line)
        elif anno.tool == TOOL_MARKER and pts:
            p.setPen(color)
            f = QFont(); f.setPointSize(10+pw*2); f.setBold(True); p.setFont(f)
            p.drawText(pts[0], anno.text)
        p.restore()

    def start_anno(self, anno):
        """Startet eine neue Annotation (wird als laufende Annotation gezeichnet)."""
        self._current_anno = anno; self.update()

    def update_anno(self, pt, tool):
        """Aktualisiert die laufende Annotation mit dem nächsten Punkt."""
        if not self._current_anno: return
        if tool == TOOL_FREE:
            self._current_anno.points.append(pt)
        else:
            if len(self._current_anno.points) > 1:
                self._current_anno.points[-1] = pt
            else:
                self._current_anno.points.append(pt)
        self.update()

    def commit_anno(self):
        """Beendet die laufende Annotation und fügt sie zur Liste hinzu."""
        a = self._current_anno; self._current_anno = None
        if a and (len(a.points) >= 2 or a.tool in (TOOL_FREE, TOOL_TEXT, TOOL_MARKER)):
            self._annotations.append(a)
        self.update()

    def abort_anno(self):
        """Bricht die laufende Annotation ohne Speichern ab."""
        self._current_anno = None; self.update()

    def clear(self):
        self._annotations.clear(); self._current_anno = None; self.update()

    def erase_at(self, pos):
        """Löscht alle Annotations-Punkte innerhalb des Radierer-Radius um pos."""
        HIT = float(_ERASER_RADIUS)
        def hits(a):
            pts = [QPointF(x,y) for x,y in a.points]
            for sp in pts:
                if math.hypot(sp.x()-pos.x(), sp.y()-pos.y()) <= HIT: return True
            if len(pts) >= 2:
                cx = sum(pp.x() for pp in pts)/len(pts)
                cy = sum(pp.y() for pp in pts)/len(pts)
                if math.hypot(cx-pos.x(), cy-pos.y()) <= HIT: return True
            return False
        new = [a for a in self._annotations if not hits(a)]
        if len(new) != len(self._annotations):
            self._annotations = new; self.update()

    def _text_bounding_rect(self, anno):
        """Bounding rect of a (possibly multi-line) TOOL_TEXT annotation,
        mirroring the font/layout used in _draw() so find_anno_at() covers
        every line, not just the anchor point - otherwise only line 1 of a
        multi-line label could be grabbed with the Move tool."""
        if anno.tool != TOOL_TEXT or not anno.points:
            return None
        x0, y0 = anno.points[0]
        pw = anno.size
        f = QFont(); f.setPointSize(8 + pw * 2); f.setBold(True)
        fm = QFontMetrics(f)
        lines = anno.text.split("\n")
        width = max((fm.horizontalAdvance(line) for line in lines), default=0)
        height = (len(lines) - 1) * fm.lineSpacing() + fm.height()
        return QRectF(x0, y0 - fm.ascent(), width, height)

    def find_anno_at(self, pos):
        """Findet die oberste Annotation nahe pos (für Move-Tool)."""
        HIT = float(_ERASER_RADIUS)
        for anno in reversed(self._annotations):
            pts = [QPointF(x,y) for x,y in anno.points]
            for sp in pts:
                if math.hypot(sp.x()-pos.x(), sp.y()-pos.y()) <= HIT: return anno
            if len(pts) >= 2:
                cx = sum(pp.x() for pp in pts)/len(pts)
                cy = sum(pp.y() for pp in pts)/len(pts)
                if math.hypot(cx-pos.x(), cy-pos.y()) <= HIT: return anno
            if anno.tool == TOOL_TEXT:
                rect = self._text_bounding_rect(anno)
                if rect is not None and rect.adjusted(-HIT, -HIT, HIT, HIT).contains(pos):
                    return anno
        return None

    def move_anno(self, anno, dx, dy):
        """Verschiebt alle Punkte einer Annotation um (dx, dy)."""
        anno.points = [(x+dx, y+dy) for x,y in anno.points]; self.update()

    @property
    def annotations(self):
        return self._annotations


# ---------------------------------------------------------------------------
# CanvasView
# ---------------------------------------------------------------------------
class CanvasView(QGraphicsView):
    """QGraphicsView mit Pan/Zoom, Annotations-Drawing und Undo-Stack.

    Verwaltet:
    - Aktives Tool (Pan, Draw, Erase, Move, Text, Marker)
    - Undo-Stack (max. 10 Snapshots)
    - Hintergrundfarbe
    - Gitternetz-Overlay
    - Projekt speichern/laden
    """
    _DEFAULT_SCENE_RECT = QRectF(-1200, -900, 2400, 1800)

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self._bg_color = QColor(_DEFAULT_BG)
        self.setBackgroundBrush(self._bg_color)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.grabGesture(Qt.PinchGesture)
        self.setFocusPolicy(Qt.ClickFocus)

        self._active_tool  = TOOL_PAN
        self._active_color = "red"
        self._active_size  = 2

        self._panning    = False
        self._pan_origin = None
        self._drawing    = False
        self._move_anno  = None
        self._move_last  = None
        self._pinch_start_scale = 1.0
        self._show_grid  = False
        self._grid_divs  = 3

        # Undo-Stack: Liste von _CanvasSnapshot (max. _UNDO_LIMIT)
        self._undo_stack: List[_CanvasSnapshot] = []

        # Merkt sich bei MOVE-Drag den Startpunkt für Undo
        self._move_start_pos: Optional[Tuple[float, float]] = None

        self._anno_layer = AnnotationLayer()
        scene.addItem(self._anno_layer)
        scene.setSceneRect(self._DEFAULT_SCENE_RECT)

    # -----------------------------------------------------------------------
    # Undo-Infrastruktur
    # -----------------------------------------------------------------------
    def _snapshot_images(self) -> list:
        """Serialisiert alle CanvasImageItems als Liste von Dicts für Undo."""
        """Serialisiert alle CanvasImageItems als Liste von dicts."""
        result = []
        for item in self.scene().items():
            if isinstance(item, CanvasImageItem):
                result.append({
                    "label":        item._label,
                    "path":         getattr(item, "_source_path", ""),
                    "vk4_channel":  getattr(item, "_vk4_channel",  ""),
                    "pdf_page":     getattr(item, "_pdf_page",    None),
                    "excel_sheet":  getattr(item, "_excel_sheet", None),
                    "word_page":    getattr(item, "_word_page",   None),
                    "x":            item.pos().x(),
                    "y":            item.pos().y(),
                    "angle":        item._angle,
                    "scale":        item._scale_f,
                })
        return result

    def _snapshot_annotations(self) -> list:
        """Serialisiert alle Annotationen als Liste von Dicts für Undo."""
        """Serialisiert alle Annotations als Liste von dicts."""
        result = []
        for anno in self._anno_layer.annotations:
            result.append({
                "tool":   anno.tool,
                "color":  anno.color,
                "size":   anno.size,
                "text":   anno.text,
                "points": list(anno.points),
            })
        return result

    def push_undo(self):
        """Sichert den aktuellen Zustand auf den Undo-Stack (max. 10)."""
        snap = _CanvasSnapshot(
            annotations=self._snapshot_annotations(),
            images=self._snapshot_images(),
            bg_color=self._bg_color.name(),
        )
        self._undo_stack.append(snap)
        if len(self._undo_stack) > _UNDO_LIMIT:
            self._undo_stack.pop(0)

    def undo(self):
        """Stellt den letzten gespeicherten Zustand wieder her."""
        if not self._undo_stack:
            return
        snap = self._undo_stack.pop()
        self._restore_snapshot(snap)
        self.update_canvas_bounds()

    def _restore_snapshot(self, snap: _CanvasSnapshot):
        """Stellt einen Snapshot vollständig wieder her (Bilder + Annotationen + Hintergrund)."""
        """Stellt einen Snapshot vollständig wieder her."""
        # Hintergrundfarbe
        self._bg_color = QColor(snap.bg_color)
        self.setBackgroundBrush(self._bg_color)

        # Bilder wiederherstellen
        for item in list(self.scene().items()):
            if isinstance(item, CanvasImageItem):
                self.scene().removeItem(item)

        for img_data in snap.images:
            src = img_data.get("path", "")
            if src and os.path.isfile(src):
                vk4_ch      = img_data.get("vk4_channel", "")
                pdf_page    = img_data.get("pdf_page",    None)
                excel_sheet = img_data.get("excel_sheet", None)
                word_page   = img_data.get("word_page",   None)
                if _is_pdf(src) and pdf_page is not None:
                    pm, _ = _load_pdf_as_pixmap(src, page=pdf_page)
                elif _is_excel(src) and excel_sheet is not None:
                    pm, _ = _load_excel_as_pixmap(src, sheet=excel_sheet)
                elif _is_word(src):
                    wp = img_data.get("word_page", 0) or 0
                    pm, _ = _load_word_as_pixmap(src, page=wp)
                else:
                    pm = _load_pixmap_from_path(src, vk4_ch)
                if pm is not None and not pm.isNull():
                    if max(pm.width(), pm.height()) > 2400:
                        pm = pm.scaled(2400, 2400, Qt.KeepAspectRatio,
                                       Qt.SmoothTransformation)
                    item = CanvasImageItem(pm, img_data.get("label", ""))
                    item._source_path  = src
                    item._vk4_channel  = vk4_ch
                    item._pdf_page     = pdf_page
                    item._excel_sheet  = excel_sheet
                    item._word_page    = word_page
                    item.setPos(img_data["x"], img_data["y"])
                    item.set_angle(img_data["angle"])
                    item.set_scale(img_data["scale"])
                    self.scene().addItem(item)
                    self._anno_layer.setZValue(1000)

        # Annotationen wiederherstellen
        self._anno_layer.clear()
        for ad in snap.annotations:
            anno = Annotation(
                tool=ad["tool"],
                color=ad["color"],
                size=ad["size"],
                text=ad.get("text", ""),
                points=[tuple(p) for p in ad["points"]],
            )
            self._anno_layer._annotations.append(anno)
        self._anno_layer.update()

    # -----------------------------------------------------------------------
    # Hintergrundfarbe
    # -----------------------------------------------------------------------
    def set_bg_color(self, color: QColor):
        """Setzt die Canvas-Hintergrundfarbe (mit Undo-Snapshot)."""
        self.push_undo()
        self._bg_color = QColor(color)
        self.setBackgroundBrush(self._bg_color)
        self.scene().update()

    # -----------------------------------------------------------------------
    # Bounds / Tools
    # -----------------------------------------------------------------------
    def _annotation_bounds(self):
        """Berechnet das Bounding-Rect aller Annotationen (für update_canvas_bounds)."""
        rect = None
        annos = list(self._anno_layer.annotations)
        cur = getattr(self._anno_layer, "_current_anno", None)
        if cur is not None:
            annos.append(cur)
        for anno in annos:
            if not anno.points:
                continue
            xs = [p[0] for p in anno.points]
            ys = [p[1] for p in anno.points]
            pad = max(float(_ERASER_RADIUS), float(getattr(anno, "size", 2) * 8))
            r = QRectF(min(xs) - pad, min(ys) - pad,
                       (max(xs) - min(xs)) + 2 * pad,
                       (max(ys) - min(ys)) + 2 * pad)
            rect = r if rect is None else rect.united(r)
        return rect

    def update_canvas_bounds(self):
        """Passt das SceneRect an alle Items und Annotationen an (verhindert Scroll-Abschneiden)."""
        rect = QRectF(self._DEFAULT_SCENE_RECT)
        for item in self.scene().items():
            if isinstance(item, CanvasImageItem):
                rect = rect.united(item.sceneBoundingRect().adjusted(-200, -200, 200, 200))
        anno_rect = self._annotation_bounds()
        if anno_rect is not None and not anno_rect.isEmpty():
            rect = rect.united(anno_rect.adjusted(-120, -120, 120, 120))
        try:
            visible_rect = self.mapToScene(self.viewport().rect()).boundingRect()
            if not visible_rect.isEmpty():
                rect = rect.united(visible_rect.adjusted(-80, -80, 80, 80))
        except Exception:
            pass
        self.scene().setSceneRect(rect.normalized())

    def set_tool(self, tool, color, size):
        """Setzt das aktive Tool, die Farbe und die Strichstärke."""
        self._active_tool  = tool
        self._active_color = color
        self._active_size  = size

    def set_grid(self, show, divs):
        """Schaltet das Gitternetz ein/aus und setzt die Teilungsanzahl."""
        self._show_grid = show
        self._grid_divs = divs
        self.scene().update()

    def add_image(self, pixmap, label="", source_path=""):
        """Fügt ein Bild zum Canvas hinzu (mit Undo-Snapshot)."""
        self.push_undo()
        n = sum(1 for i in self.scene().items() if isinstance(i, CanvasImageItem))
        item = CanvasImageItem(pixmap, label)
        item._source_path = source_path
        item.setPos(60 * (n % 7), 60 * (n % 5))
        self.scene().addItem(item)
        self._anno_layer.setZValue(1000)
        self.update_canvas_bounds()
        return item

    def clear_annotations(self):
        """Löscht alle Annotationen (mit Undo-Snapshot)."""
        self.push_undo()
        self._anno_layer.clear()
        self.update_canvas_bounds()

    @property
    def anno_layer(self):
        return self._anno_layer

    def _image_at(self, pos):
        """Gibt das CanvasImageItem unter dem Viewport-Punkt pos zurück (oder None)."""
        for item in self.items(pos):
            if isinstance(item, CanvasImageItem):
                return item
        return None

    def _erase_image_at(self, pos):
        """Löscht das Bild unter pos (mit Undo-Snapshot). Gibt True zurück wenn etwas gelöscht wurde."""
        img = self._image_at(pos)
        if img is None:
            return False
        try:
            self.push_undo()
            self.scene().removeItem(img)
            self.update_canvas_bounds()
        except Exception:
            return False
        return True

    # -----------------------------------------------------------------------
    # Drawing / background
    # -----------------------------------------------------------------------
    def drawBackground(self, painter, rect):
        """Zeichnet den Hintergrund und optional das Gitternetz."""
        super().drawBackground(painter, rect)
        if not self._show_grid:
            return
        painter.setPen(QPen(QColor(255, 255, 255, 35), 0, Qt.DashLine))
        step = max(40, int(max(rect.width(), rect.height()) / self._grid_divs))
        x = int(rect.left()) - (int(rect.left()) % step)
        while x <= rect.right():
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            x += step
        y = int(rect.top()) - (int(rect.top()) % step)
        while y <= rect.bottom():
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            y += step

    # -----------------------------------------------------------------------
    # Mouse events
    # -----------------------------------------------------------------------
    def mousePressEvent(self, ev):
        """Verarbeitet Mausklick je nach aktivem Tool (Pan, Draw, Erase, Text, Marker usw.)."""
        sp = self.mapToScene(ev.pos())
        if ev.button() == Qt.LeftButton:
            if self._active_tool == TOOL_PAN:
                img = self._image_at(ev.pos())
                if img is not None:
                    try:
                        ctrl = bool(ev.modifiers() & Qt.ControlModifier)
                        if ctrl:
                            # Ctrl: Item zur Selektion hinzufügen / entfernen
                            img.setSelected(not img.isSelected())
                        else:
                            # Kein Ctrl: nur dieses Item selektieren
                            for item in self.scene().selectedItems():
                                if item is not img:
                                    item.setSelected(False)
                            img.setSelected(True)
                    except Exception:
                        pass
                    if img.isSelected():
                        # Snapshot vor dem Verschieben merken
                        self._img_drag_item = img
                        self._img_drag_start = (img.pos().x(), img.pos().y())
                        super().mousePressEvent(ev)
                    return
                # Leerer Klick: alle deselektieren, dann panning
                for item in list(self.scene().selectedItems()):
                    item.setSelected(False)
                self._panning = True
                self._pan_origin = ev.pos()
                self.setCursor(Qt.ClosedHandCursor)
                return
            if self._active_tool == TOOL_ERASER:
                if self._erase_image_at(ev.pos()):
                    return
                self.push_undo()
                self._anno_layer.erase_at(sp)
                self.update_canvas_bounds()
                return
            if self._active_tool == TOOL_MOVE:
                hit = self._anno_layer.find_anno_at(sp)
                if hit:
                    self.push_undo()
                    self._move_anno = hit
                    self._move_last = sp
                return
            if self._active_tool == TOOL_TEXT:
                text, ok = _get_multiline_text(self, "Text", "Text eingeben:")
                if ok and text.strip():
                    self.push_undo()
                    a = Annotation(TOOL_TEXT, self._active_color,
                                   [(sp.x(), sp.y())], text.strip(), self._active_size)
                    self._anno_layer._annotations.append(a)
                    self._anno_layer.update()
                    self.update_canvas_bounds()
                return
            if self._active_tool == TOOL_MARKER:
                self.push_undo()
                n = sum(1 for a in self._anno_layer.annotations if a.tool == TOOL_MARKER)
                char = _MARKER_CHARS[n % len(_MARKER_CHARS)]
                a = Annotation(TOOL_MARKER, self._active_color,
                               [(sp.x(), sp.y())], char, self._active_size)
                self._anno_layer._annotations.append(a)
                self._anno_layer.update()
                self.update_canvas_bounds()
                return
            # Freihand / Formen: Undo erst beim Commit (mouseRelease)
            self._drawing = True
            a = Annotation(self._active_tool, self._active_color,
                           [(sp.x(), sp.y())], "", self._active_size)
            self._anno_layer.start_anno(a)
            self.update_canvas_bounds()
            return

        if ev.button() == Qt.RightButton and self._active_tool == TOOL_MOVE:
            hit = self._anno_layer.find_anno_at(sp)
            if hit:
                self._show_anno_menu(hit, ev.globalPos())
                return

        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        """Verarbeitet Mausbewegung für Pan, Drawing und Eraser."""
        sp = self.mapToScene(ev.pos())
        if self._active_tool == TOOL_MOVE and not (ev.buttons() & Qt.LeftButton):
            hit = self._anno_layer.find_anno_at(sp)
            self.setCursor(Qt.SizeAllCursor if hit else Qt.ArrowCursor)
        if not (ev.buttons() & Qt.LeftButton):
            super().mouseMoveEvent(ev)
            return
        if self._panning and self._pan_origin is not None:
            d = ev.pos() - self._pan_origin
            self._pan_origin = ev.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - d.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - d.y())
            return
        if self._active_tool == TOOL_PAN:
            super().mouseMoveEvent(ev)
            return
        if self._active_tool == TOOL_ERASER:
            erased_img = self._erase_image_at(ev.pos())
            self._anno_layer.erase_at(sp)
            if erased_img:
                self.update_canvas_bounds()
            return
        if self._active_tool == TOOL_MOVE and self._move_anno and self._move_last:
            self._anno_layer.move_anno(self._move_anno,
                                       sp.x() - self._move_last.x(),
                                       sp.y() - self._move_last.y())
            self._move_last = sp
            self.update_canvas_bounds()
            return
        if self._drawing:
            self._anno_layer.update_anno((sp.x(), sp.y()), self._active_tool)
            self.update_canvas_bounds()
            return

    def mouseReleaseEvent(self, ev):
        """Beendet Pan/Drawing und speichert Undo-Snapshot bei Bedarf."""
        if ev.button() == Qt.LeftButton:
            if self._panning:
                self._panning = False
                self.setCursor(Qt.ArrowCursor)
            if self._drawing:
                # Undo-Snapshot erst jetzt (nach abgeschlossenem Strich)
                self.push_undo()
                # ... aber der Snapshot VOR dem Commit soll gespeichert sein,
                # also: Snapshot zurückrollen und neu mit altem Zustand bauen
                # Einfachste Lösung: Snapshot vor dem Strich speichern,
                # d.h. wir entfernen den soeben gepushten und committen erst dann.
                # Wir speichern den Pre-Draw-Zustand: anno_layer ohne current_anno
                if self._undo_stack:
                    last = self._undo_stack.pop()
                    # Entferne die noch nicht committete Annotation aus dem Snapshot
                    self._undo_stack.append(last)
                self._anno_layer.commit_anno()
                self._drawing = False
                self.update_canvas_bounds()

            # Bild-Drag beendet: Undo-Snapshot speichern wenn Position geändert
            img_item = getattr(self, "_img_drag_item", None)
            img_start = getattr(self, "_img_drag_start", None)
            if img_item is not None and img_start is not None:
                new_x, new_y = img_item.pos().x(), img_item.pos().y()
                if abs(new_x - img_start[0]) > 1 or abs(new_y - img_start[1]) > 1:
                    # Snapshot mit alter Position erstellen
                    new_x_cur = img_item.pos().x()
                    new_y_cur = img_item.pos().y()
                    # Temporär zurück für Snapshot
                    img_item.setPos(img_start[0], img_start[1])
                    self.push_undo()
                    img_item.setPos(new_x_cur, new_y_cur)
                self._img_drag_item = None
                self._img_drag_start = None

            self._move_anno = None
            self._move_last = None
        super().mouseReleaseEvent(ev)

    def wheelEvent(self, ev):
        """Mausrad: Ctrl+Scroll = Zoom/Bild-Skalieren, Shift+Scroll = horizontales Scrollen."""
        delta   = ev.angleDelta()
        dy      = delta.y()
        dx      = delta.x()
        vp_pos  = ev.position().toPoint()
        ctrl    = bool(ev.modifiers() & Qt.ControlModifier)
        shift   = bool(ev.modifiers() & Qt.ShiftModifier)

        # Ctrl + Scroll über Bild im Pan-Modus → Bild skalieren
        if ctrl and self._active_tool == TOOL_PAN:
            img = self._image_at(vp_pos)
            if img is not None:
                self.push_undo()
                factor = 1.12 if dy > 0 else (1.0 / 1.12)
                img.set_scale(img._scale_f * factor)
                self.update_canvas_bounds()
                ev.accept()
                return

        # Ctrl + Scroll (leere Fläche) → Canvas zoomen
        if ctrl:
            factor = 1.15 if dy > 0 else (1.0 / 1.15)
            self.scale(factor, factor)
            self.update_canvas_bounds()
            ev.accept()
            return

        # Shift + Scroll → horizontal scrollen
        if shift or dx != 0:
            scroll_dx = -(dx if dx != 0 else dy)
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() + scroll_dx)
            ev.accept()
            return

        # Standard: vertikal scrollen
        self.verticalScrollBar().setValue(
            self.verticalScrollBar().value() - dy)
        ev.accept()

    def event(self, ev):
        """Verarbeitet Pinch-Gesten für Canvas-Zoom."""
        if ev.type() == ev.Type.Gesture:
            try:
                g = ev.gesture(Qt.PinchGesture)
                if g:
                    st = g.state()
                    if st == Qt.GestureState.GestureStarted:
                        self._pinch_start_scale = self.transform().m11()
                    elif st in (Qt.GestureState.GestureUpdated,
                                Qt.GestureState.GestureFinished):
                        cur = self.transform().m11()
                        new = max(0.02, min(50.0,
                                  self._pinch_start_scale * g.totalScaleFactor()))
                        if cur > 0:
                            self.scale(new / cur, new / cur)
                            self.update_canvas_bounds()
            except Exception:
                pass
            return True
        return super().event(ev)

    def keyPressEvent(self, ev):
        """Ctrl+V = Bild aus Clipboard einfügen; Delete = selektierte Bilder löschen."""
        if ev.key() == Qt.Key_V and (ev.modifiers() & Qt.ControlModifier):
            pm = QGuiApplication.clipboard().pixmap()
            if not pm.isNull():
                if max(pm.width(), pm.height()) > 2400:
                    pm = pm.scaled(2400, 2400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.add_image(pm, "clipboard")
                return
        if ev.key() == Qt.Key_Delete:
            removed = False
            for item in list(self.scene().selectedItems()):
                if isinstance(item, CanvasImageItem):
                    self.push_undo()
                    self.scene().removeItem(item)
                    removed = True
            if removed:
                self.update_canvas_bounds()
            return
        super().keyPressEvent(ev)

    def render_to_pixmap(self):
        """Rendert den gesamten Canvas-Inhalt als QPixmap (für «Save as»)."""
        items_rect = QRectF()
        has_items = False
        for item in self.scene().items():
            if isinstance(item, CanvasImageItem):
                r = item.sceneBoundingRect()
                items_rect = r if not has_items else items_rect.united(r)
                has_items = True
        anno_rect = self._annotation_bounds()
        if anno_rect is not None and not anno_rect.isEmpty():
            items_rect = anno_rect if not has_items else items_rect.united(anno_rect)
            has_items = True
        if not has_items:
            items_rect = QRectF(-400, -300, 800, 600)
        items_rect = items_rect.adjusted(-20, -20, 20, 20)
        w = max(1, int(items_rect.width()))
        h = max(1, int(items_rect.height()))
        pm = QPixmap(w, h)
        pm.fill(self._bg_color)
        painter = QPainter(pm)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.scene().render(painter, target=QRectF(0, 0, w, h), source=items_rect)
        painter.end()
        return pm

    # -----------------------------------------------------------------------
    # Projekt speichern / laden  (inkl. Undo-Stack und Hintergrundfarbe)
    # -----------------------------------------------------------------------
    def save_project(self, path: str):
        images = []
        for item in self.scene().items():
            if isinstance(item, CanvasImageItem):
                images.append({
                    "label":        item._label,
                    "path":         getattr(item, "_source_path", ""),
                    "vk4_channel":  getattr(item, "_vk4_channel",  ""),
                    "pdf_page":     getattr(item, "_pdf_page",    None),
                    "excel_sheet":  getattr(item, "_excel_sheet", None),
                    "word_page":    getattr(item, "_word_page",   None),
                    "x":            item.pos().x(),
                    "y":            item.pos().y(),
                    "angle":        item._angle,
                    "scale":        item._scale_f,
                })

        annotations = []
        for anno in self._anno_layer.annotations:
            annotations.append({
                "tool":   anno.tool,
                "color":  anno.color,
                "size":   anno.size,
                "text":   anno.text,
                "points": anno.points,
            })

        # Undo-Stack serialisieren
        undo_data = []
        for snap in self._undo_stack:
            undo_data.append({
                "annotations": snap.annotations,
                "images":      snap.images,
                "bg_color":    snap.bg_color,
            })

        t = self.transform()
        project = {
            "version":     2,
            "bg_color":    self._bg_color.name(),
            "images":      images,
            "annotations": annotations,
            "undo_stack":  undo_data,
            "view": {
                "m11": t.m11(), "m12": t.m12(),
                "m21": t.m21(), "m22": t.m22(),
                "dx":  t.dx(),  "dy":  t.dy(),
            },
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(project, fh, ensure_ascii=False, indent=2)

    def load_project(self, path: str):
        from PySide6.QtGui import QTransform
        with open(path, "r", encoding="utf-8") as fh:
            project = json.load(fh)

        # Hintergrundfarbe (v2; Fallback auf Anthrazit)
        bg_hex = project.get("bg_color", _DEFAULT_BG.name())
        self._bg_color = QColor(bg_hex)
        self.setBackgroundBrush(self._bg_color)

        # Alle bestehenden Bilder entfernen
        for item in list(self.scene().items()):
            if isinstance(item, CanvasImageItem):
                self.scene().removeItem(item)
        self._anno_layer.clear()

        missing = []
        for img_data in project.get("images", []):
            src = img_data.get("path", "")
            if src and os.path.isfile(src):
                vk4_ch      = img_data.get("vk4_channel", "")
                pdf_page    = img_data.get("pdf_page",    None)
                excel_sheet = img_data.get("excel_sheet", None)
                word_page   = img_data.get("word_page",   None)
                if _is_pdf(src) and pdf_page is not None:
                    pm, _ = _load_pdf_as_pixmap(src, page=pdf_page)
                elif _is_excel(src) and excel_sheet is not None:
                    pm, _ = _load_excel_as_pixmap(src, sheet=excel_sheet)
                elif _is_word(src):
                    wp = img_data.get("word_page", 0) or 0
                    pm, _ = _load_word_as_pixmap(src, page=wp)
                else:
                    pm = _load_pixmap_from_path(src, vk4_ch)
                if pm is not None and not pm.isNull():
                    if max(pm.width(), pm.height()) > 2400:
                        pm = pm.scaled(2400, 2400, Qt.KeepAspectRatio,
                                       Qt.SmoothTransformation)
                    item = CanvasImageItem(pm, img_data.get("label", ""))
                    item._source_path  = src
                    item._vk4_channel  = vk4_ch
                    item._pdf_page     = pdf_page
                    item._excel_sheet  = excel_sheet
                    item._word_page    = word_page
                    item.setPos(img_data["x"], img_data["y"])
                    item.set_angle(img_data["angle"])
                    item.set_scale(img_data["scale"])
                    self.scene().addItem(item)
                    self._anno_layer.setZValue(1000)
            else:
                missing.append(src or "(no path)")

        for ad in project.get("annotations", []):
            anno = Annotation(
                tool   = ad["tool"],
                color  = ad["color"],
                size   = ad["size"],
                text   = ad.get("text", ""),
                points = [tuple(p) for p in ad["points"]],
            )
            self._anno_layer._annotations.append(anno)
        self._anno_layer.update()

        # Undo-Stack wiederherstellen
        self._undo_stack = []
        for snap_data in project.get("undo_stack", []):
            snap = _CanvasSnapshot(
                annotations=snap_data.get("annotations", []),
                images=snap_data.get("images", []),
                bg_color=snap_data.get("bg_color", _DEFAULT_BG.name()),
            )
            self._undo_stack.append(snap)

        v = project.get("view", {})
        if v:
            t = QTransform(
                v.get("m11", 1), v.get("m12", 0),
                v.get("m21", 0), v.get("m22", 1),
                v.get("dx",  0), v.get("dy",  0),
            )
            self.setTransform(t)

        self.update_canvas_bounds()

        if missing:
            QMessageBox.warning(
                self, "Missing images",
                "These image files were not found:\n\n" +
                "\n".join(missing)
            )

    def _show_anno_menu(self, anno, global_pos):
        """Zeigt ein Kontextmenü für eine Annotation (Farbe, Stärke, Löschen)."""
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:#2a2a2a;color:#eee;border:1px solid #555;}"
            "QMenu::item:selected{background:#39A650;}"
            "QMenu::item{padding:4px 18px;}"
            "QMenu::separator{background:#444;height:1px;margin:3px 0;}")
        cm = menu.addMenu("Farbe")
        for cname in ANNO_COLORS:
            act = cm.addAction(cname.capitalize())
            act.setCheckable(True)
            act.setChecked(anno.color == cname)
            act.triggered.connect(
                lambda c, n=cname: (setattr(anno, "color", n), self._anno_layer.update()))
        sm = menu.addMenu("Starke")
        for sz, lbl in [(2, "Dunn"), (4, "Medium"), (8, "Thick")]:
            act = sm.addAction(lbl)
            act.setCheckable(True)
            act.setChecked(anno.size == sz)
            act.triggered.connect(
                lambda c, s=sz: (setattr(anno, "size", s), self._anno_layer.update()))
        menu.addSeparator()
        da = menu.addAction("Loschen")
        da.triggered.connect(
            lambda: (self._anno_layer._annotations.remove(anno),
                     self._anno_layer.update(),
                     self.update_canvas_bounds())
            if anno in self._anno_layer._annotations else None)
        menu.exec(global_pos)


# ---------------------------------------------------------------------------
# _ImageListPanel
# ---------------------------------------------------------------------------
class _ImageListPanel(QWidget):
    """Linkes Panel mit Baum-Ansicht der verfügbaren Bilder/PDFs aus DB und lokal.

    Lädt Serien aus der DB (lazy: Bilder erst beim Aufklappen).
    Unterstützt Filter-Buttons (Alle/Bilder/PDFs) und Freitext-Filter.
    """
    image_clicked = Signal(object)

    _FILTER_ALL  = "all"
    _FILTER_IMGS = "images"
    _FILTER_PDFS = "pdfs"
    _IMG_PREFIX  = "🖼"
    _PDF_PREFIX  = "📄"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._local_counter = 0
        self._active_filter = self._FILTER_ALL
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4,4,4,4); lay.setSpacing(4)

        trow = QHBoxLayout(); trow.setSpacing(3)
        self._btn_all  = QPushButton("All")
        self._btn_imgs = QPushButton("🖼 Images")
        self._btn_pdfs = QPushButton("📄 PDFs")
        for btn in (self._btn_all, self._btn_imgs, self._btn_pdfs):
            btn.setCheckable(True); btn.setFixedHeight(24)
            btn.setStyleSheet(self._toggle_style(False))
            trow.addWidget(btn)
        self._btn_all.setChecked(True)
        self._btn_all.setStyleSheet(self._toggle_style(True))
        self._btn_all.clicked.connect(lambda: self._set_filter(self._FILTER_ALL))
        self._btn_imgs.clicked.connect(lambda: self._set_filter(self._FILTER_IMGS))
        self._btn_pdfs.clicked.connect(lambda: self._set_filter(self._FILTER_PDFS))
        lay.addLayout(trow)

        frow = QHBoxLayout(); frow.setSpacing(4)
        self._sf = QLineEdit(); self._sf.setPlaceholderText("Filter (experiment/file)...")
        self._sf.setClearButtonEnabled(True); self._sf.textChanged.connect(self._filter_tree)
        frow.addWidget(self._sf)
        lay.addLayout(frow)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True); self.tree.setIndentation(15)
        self.tree.setStyleSheet("""
            QTreeWidget { background: #1a1a1a; color: #eee; border: none; font-size: 11px; }
            QTreeWidget::item { height: 26px; border-bottom: 1px solid #2a2a2a; }
            QTreeWidget::item:hover { background: #333; }
        """)
        self.tree.itemExpanded.connect(self._on_item_expanded)
        self.tree.itemClicked.connect(self._on_item_clicked)
        lay.addWidget(self.tree)
        brow = QHBoxLayout(); brow.setSpacing(4)
        btn_r = QPushButton("Reload"); btn_r.setObjectName("GreenBtn")
        btn_r.setFixedHeight(28); btn_r.clicked.connect(self.load_images)
        brow.addWidget(btn_r)
        btn_l = QPushButton("+ Local"); btn_l.setObjectName("GreenBtn")
        btn_l.setFixedHeight(28); btn_l.clicked.connect(self._add_local)
        brow.addWidget(btn_l)
        lay.addLayout(brow)

    def load_images(self):
        """Lädt alle Serien aus der DB und befüllt den Baum (lokale Dateien bleiben erhalten)."""
        # DB-Eintraege aktualisieren ohne lokale Dateien zu loeschen
        for i in reversed(range(self.tree.topLevelItemCount())):
            it = self.tree.topLevelItem(i)
            if it is not getattr(self, "local_root", None):
                self.tree.takeTopLevelItem(i)
        if not hasattr(self, "local_root") or self.local_root is None:
            self.local_root = QTreeWidgetItem(self.tree, ["Local images"])
            self.tree.insertTopLevelItem(0, self.local_root)
        groups = _fetch_series_groups()
        for g in groups:
            name = f"{g['ExperimentID']} | {g['SeriesName']}"
            item = QTreeWidgetItem(self.tree, [name])
            item.setData(0, Qt.UserRole, g); item.setForeground(0, QColor("#7ddf9a"))
            QTreeWidgetItem(item, ["Loading images..."])
        self._apply_type_filter()

    def _on_item_expanded(self, item):
        """Lädt Bilder/PDFs einer Serie on-demand wenn der Baum-Knoten aufgeklappt wird."""
        data = item.data(0, Qt.UserRole)
        if not isinstance(data, dict) or "TrialSeriesID" not in data: return
        if item.childCount() == 1 and item.child(0).text(0) == "Loading images...":
            item.removeChild(item.child(0))
            sid    = data["TrialSeriesID"]
            images = _fetch_images_for_series(sid)
            pdfs   = _fetch_pdfs_for_series(sid)

            if images:
                img_root = QTreeWidgetItem(item, [f"🖼  Images ({len(images)})"])
                img_root.setForeground(0, QColor("#7ddf9a"))
                img_root.setFlags(img_root.flags() & ~Qt.ItemIsSelectable)
                for r in images:
                    child = QTreeWidgetItem(img_root, [r["OriginalFilename"]])
                    child.setData(0, Qt.UserRole, r)
                    child.setForeground(0, QColor("#bbb"))
                img_root.setExpanded(True)

            if pdfs:
                pdf_root = QTreeWidgetItem(item, [f"📄  PDFs ({len(pdfs)})"])
                pdf_root.setForeground(0, QColor("#8cf"))
                pdf_root.setFlags(pdf_root.flags() & ~Qt.ItemIsSelectable)
                for r in pdfs:
                    fname   = r["OriginalFilename"]
                    full    = r.get("FullPath", "")
                    n_pages = _pdf_page_count(full) if os.path.isfile(full) else 1
                    if n_pages > 1:
                        pf_root = QTreeWidgetItem(pdf_root,
                            [fname + f"  ({n_pages} Seiten)"])
                        pf_root.setForeground(0, QColor("#8cf"))
                        pf_root.setFlags(pf_root.flags() & ~Qt.ItemIsSelectable)
                        for pg in range(n_pages):
                            meta = dict(r); meta["_pdf_page"] = pg
                            meta["OriginalFilename"] = fname + f" - page {pg + 1}"
                            child = QTreeWidgetItem(pf_root, [f"  page {pg + 1}"])
                            child.setData(0, Qt.UserRole, meta)
                            child.setForeground(0, QColor("#bbb"))
                        pf_root.setExpanded(n_pages <= 6)
                    else:
                        meta = dict(r); meta["_pdf_page"] = 0
                        child = QTreeWidgetItem(pdf_root, [fname])
                        child.setData(0, Qt.UserRole, meta)
                        child.setForeground(0, QColor("#bbb"))
                pdf_root.setExpanded(True)

            if not images and not pdfs:
                QTreeWidgetItem(item, ["(no files)"])

            self._apply_type_filter()

    def _on_item_clicked(self, item, col):
        """Emittiert image_clicked wenn ein Bild/PDF angeklickt wird."""
        data = item.data(0, Qt.UserRole)
        if isinstance(data, dict) and "ID" in data:
            self.image_clicked.emit(data)

    def _add_local(self):
        """Öffnet Datei-Dialog für lokale Bilder/Dokumente und fügt sie dem Baum hinzu."""
        # Sicherstellen dass local_root existiert (falls load_images noch nicht lief)
        if not hasattr(self, "local_root") or self.local_root is None:
            self.local_root = QTreeWidgetItem(self.tree, ["Local images"])
            self.tree.insertTopLevelItem(0, self.local_root)
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Images / documents", "",
            "All supported files (*.png *.jpg *.jpeg *.bmp *.webp *.vk4 *.pdf *.xlsx *.xlsm *.xls *.docx *.doc);;"
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;"
            "Keyence VK4 (*.vk4);;"
            "PDF (*.pdf);;"
            "Excel (*.xlsx *.xlsm *.xls);;"
            "Word (*.docx *.doc);;"
            "All files (*.*)"
        )
        for p in paths:
            basename = os.path.basename(p)
            if _is_pdf(p):
                n_pages = _pdf_page_count(p)
                pdf_root = QTreeWidgetItem(self.local_root,
                    [basename + ("  (%d Seiten)" % n_pages if n_pages > 1 else "")])
                pdf_root.setForeground(0, QColor("#8cf"))
                for pg in range(n_pages):
                    self._local_counter -= 1
                    meta = {"ID": self._local_counter,
                            "OriginalFilename": basename + " - page %d" % (pg + 1),
                            "FullPath": p, "_local": True, "_pdf_page": pg}
                    child = QTreeWidgetItem(pdf_root, ["  page %d" % (pg + 1)])
                    child.setData(0, Qt.UserRole, meta)
                    child.setForeground(0, QColor("#bbb"))
                pdf_root.setExpanded(n_pages <= 6)
            elif _is_excel(p):
                sheets = _excel_sheet_names(p)
                xls_root = QTreeWidgetItem(self.local_root,
                    [basename + "  (%d Sheets)" % len(sheets)])
                xls_root.setForeground(0, QColor("#7ddf9a"))
                for si, sname in enumerate(sheets):
                    self._local_counter -= 1
                    meta = {"ID": self._local_counter,
                            "OriginalFilename": basename + " - " + sname,
                            "FullPath": p, "_local": True, "_excel_sheet": si}
                    child = QTreeWidgetItem(xls_root, ["  " + sname])
                    child.setData(0, Qt.UserRole, meta)
                    child.setForeground(0, QColor("#bbb"))
                xls_root.setExpanded(len(sheets) <= 6)
            elif _is_word(p):
                n_pages = _word_page_count(p)
                word_root = QTreeWidgetItem(self.local_root,
                    [basename + ("  (%d Seiten)" % n_pages if n_pages > 1 else "")])
                word_root.setForeground(0, QColor("#d4a0ff"))
                for pg in range(n_pages):
                    self._local_counter -= 1
                    meta = {"ID": self._local_counter,
                            "OriginalFilename": basename + " - page %d" % (pg + 1),
                            "FullPath": p, "_local": True,
                            "_word": True, "_word_page": pg}
                    child = QTreeWidgetItem(word_root, ["  page %d" % (pg + 1)])
                    child.setData(0, Qt.UserRole, meta)
                    child.setForeground(0, QColor("#bbb"))
                word_root.setExpanded(n_pages <= 6)
            else:
                self._local_counter -= 1
                meta = {"ID": self._local_counter, "OriginalFilename": basename,
                        "FullPath": p, "_local": True}
                child = QTreeWidgetItem(self.local_root, [basename])
                child.setData(0, Qt.UserRole, meta)
        self.local_root.setExpanded(True)

    def _toggle_style(self, active: bool) -> str:
        """Gibt den CSS-Stil für einen Toggle-Button zurück (aktiv/inaktiv)."""
        if active:
            return ("QPushButton{background:#39A650;color:#fff;border-radius:4px;"
                    "font-size:11px;font-weight:bold;border:2px solid #fff;padding:0 4px;}"
                    "QPushButton:hover{background:#4ab862;}")
        return ("QPushButton{background:#333;color:#aaa;border-radius:4px;"
                "font-size:11px;border:2px solid #555;padding:0 4px;}"
                "QPushButton:hover{background:#444;color:#eee;}")

    def _set_filter(self, mode: str):
        """Setzt den Typ-Filter (alle/Bilder/PDFs) und aktualisiert die Anzeige."""
        self._active_filter = mode
        for btn, m in ((self._btn_all,  self._FILTER_ALL),
                       (self._btn_imgs, self._FILTER_IMGS),
                       (self._btn_pdfs, self._FILTER_PDFS)):
            btn.setChecked(m == mode)
            btn.setStyleSheet(self._toggle_style(m == mode))
        self._apply_type_filter()

    def _apply_type_filter(self):
        """Blendet Series ohne passendes Flag aus; blendet Unterordner-Roots."""
        f = self._active_filter
        for i in range(self.tree.topLevelItemCount()):
            series_item = self.tree.topLevelItem(i)
            if series_item is getattr(self, "local_root", None):
                continue
            data = series_item.data(0, Qt.UserRole)
            if isinstance(data, dict) and "TrialSeriesID" in data:
                has_imgs = data.get("has_images", True)
                has_pdfs = data.get("has_pdfs",   True)
                if f == self._FILTER_IMGS:
                    series_item.setHidden(not has_imgs)
                elif f == self._FILTER_PDFS:
                    series_item.setHidden(not has_pdfs)
                else:
                    series_item.setHidden(False)
            for ci in range(series_item.childCount()):
                child = series_item.child(ci)
                txt = child.text(0)
                if txt.startswith(self._IMG_PREFIX):
                    child.setHidden(f == self._FILTER_PDFS)
                elif txt.startswith(self._PDF_PREFIX):
                    child.setHidden(f == self._FILTER_IMGS)

    def _filter_tree(self):
        """Filtert Baum-Knoten nach dem eingegebenen Text im Suchfeld."""
        txt = self._sf.text().lower()
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            it.setHidden(txt not in it.text(0).lower() and txt != "")


# ---------------------------------------------------------------------------
# CanvasScreen (Hauptwidget)
# ---------------------------------------------------------------------------
class CanvasScreen(QWidget):
    """Hauptwidget für den Canvas-Screen.

    Enthält _ImageListPanel (links), Toolbar (oben), CanvasView (rechts).
    """
    def __init__(self, on_back_home=None, parent=None, sidebar_callbacks: Optional[dict] = None):
        super().__init__(parent)
        self._on_back_home = on_back_home
        self._active_tool  = TOOL_PAN
        self._active_color = "red"
        self._active_size  = 2
        self._sigs_list    = []
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None
        self._build_ui()

    def _build_ui(self):
        """Erstellt Sidebar, Toolbar, Splitter (Liste | Canvas) und Footer."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring).
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        splitter = QSplitter(Qt.Horizontal); splitter.setHandleWidth(5)
        self._panel = _ImageListPanel()
        self._panel.setMinimumWidth(200); self._panel.setMaximumWidth(340)
        self._panel.image_clicked.connect(self._on_image_clicked)
        splitter.addWidget(self._panel)
        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(-5000, -5000, 10000, 10000)
        self._view = CanvasView(self._scene, self)
        self._loading_overlay = _LoadingOverlay(self._view)
        self._view._overlay = self._loading_overlay
        splitter.addWidget(self._view)
        splitter.setStretchFactor(0, 0); splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 900])

        content_layout.addWidget(self._build_toolbar())
        # VK4-Toolbar aktualisieren wenn Selektion wechselt
        self._scene.selectionChanged.connect(self._update_vk4_toolbar)
        content_layout.addWidget(splitter, 1)
        root.addWidget(FooterBar())

    def _sep(self):
        """Erstellt eine vertikale Trennlinie für die Toolbar."""
        f = QFrame(); f.setFrameShape(QFrame.VLine); f.setStyleSheet("color:#555;"); return f

    def _tool_style(self, active):
        """Gibt den CSS-Stil für einen Tool-Button zurück."""
        if active:
            return ("QPushButton{background-color:#39A650;color:white;border-radius:4px;"
                    "font-size:15px;font-weight:bold;border:3px solid #fff;padding:0px;}"
                    "QPushButton:hover{background-color:#4ab862;}")
        return ("QPushButton{background-color:#555;color:#eee;border-radius:4px;"
                "font-size:15px;border:2px solid #888;padding:0px;}"
                "QPushButton:hover{background-color:#666;color:#fff;border:2px solid #aaa;}")

    def _size_style(self, active):
        """Gibt den CSS-Stil für einen Grössen-Button zurück."""
        if active:
            return ("QPushButton{background-color:#39A650;color:white;border-radius:4px;"
                    "font-size:13px;font-weight:bold;border:3px solid #fff;padding:0px;}"
                    "QPushButton:hover{background-color:#4ab862;}")
        return ("QPushButton{background-color:#555;color:#eee;border-radius:4px;"
                "font-size:13px;border:2px solid #888;padding:0px;}"
                "QPushButton:hover{background-color:#666;}")

    def _build_toolbar(self):
        """Erstellt die vollständige Canvas-Toolbar mit allen Tools, Farben und Aktionen."""
        bar = QFrame(); bar.setFixedHeight(52); bar.setObjectName("ToolBar")
        bar.setStyleSheet("QFrame#ToolBar{background:#2a2a2a;border-bottom:1px solid #444;}")
        lay = QHBoxLayout(bar); lay.setContentsMargins(10,4,10,4); lay.setSpacing(5)

        self._tool_btns = {}
        tool_defs = [
            (TOOL_PAN,       "🖐",  "Pan / move images"),
            (TOOL_ARROW,     "↗",  "Pfeil"),
            (TOOL_ELLIPSE,   "⬭",  "Ellipse"),
            (TOOL_RECT,      "▭",  "Rechteck"),
            (TOOL_FREE,      "✏️", "Freihand"),
            (TOOL_TEXT,      "T",   "Text"),
            (TOOL_HIGHLIGHT, "🖊",  "Highlight"),
            (TOOL_MARKER,    "①",  "Nummerierter Marker"),
            (TOOL_ERASER,    "⌫",  "Radierer"),
            (TOOL_MOVE,      "⤢",  "Annotation verschieben / Rechtsklick = bearbeiten"),
        ]
        for tid, icon, tip in tool_defs:
            btn = QPushButton(icon); btn.setToolTip(tip)
            btn.setFixedSize(36, 38)
            btn.setCheckable(True); btn.setChecked(tid == TOOL_PAN)
            btn.setStyleSheet(self._tool_style(tid == TOOL_PAN))
            btn.clicked.connect(lambda c, t=tid: self._select_tool(t))
            lay.addWidget(btn); self._tool_btns[tid] = btn

        self._lbl_tool = QLabel("🖐 Pan")
        self._lbl_tool.setStyleSheet("color:#aaa;font-size:11px;min-width:70px;")
        lay.addWidget(self._lbl_tool)
        lay.addWidget(self._sep())

        self._color_btns = {}
        for cid, hx in [("red","#DC3232"),("yellow","#F0C800"),
                         ("green","#32C850"),("white","#FFFFFF"),("blue","#3282DC")]:
            btn = QPushButton(); btn.setFixedSize(24,24)
            btn.setCheckable(True); btn.setChecked(cid=="red")
            btn.setStyleSheet(
                f"QPushButton{{background:{hx};border-radius:12px;"
                f"border:3px solid {'#fff' if cid=='red' else '#555'};}}")
            btn.clicked.connect(lambda c, col=cid: self._select_color(col))
            lay.addWidget(btn); self._color_btns[cid] = btn
        lay.addWidget(self._sep())

        self._size_btns = {}
        for sz, icon, tip in [(2,"—","Thin"),(4,"━","Medium"),(8,"▬","Thick")]:
            btn = QPushButton(icon); btn.setToolTip(tip); btn.setFixedSize(30,30)
            btn.setCheckable(True); btn.setChecked(sz==2)
            btn.setStyleSheet(self._size_style(sz==2))
            btn.clicked.connect(lambda c, s=sz: self._select_size(s))
            lay.addWidget(btn); self._size_btns[sz] = btn
        lay.addWidget(self._sep())

        btn_undo = QPushButton("↩ Undo"); btn_undo.setFixedHeight(28)
        btn_undo.setToolTip("Undo last step (max. 10 steps)")
        btn_undo.setStyleSheet("QPushButton{background:#444;color:#ccc;border-radius:3px;"
                               "font-size:11px;}QPushButton:hover{background:#555;}")
        btn_undo.clicked.connect(self._view.undo); lay.addWidget(btn_undo)

        btn_clr = QPushButton("🗑 Clear"); btn_clr.setFixedHeight(28)
        btn_clr.setStyleSheet("QPushButton{background:#5a1a1a;color:#f88;border-radius:3px;"
                              "font-size:11px;}QPushButton:hover{background:#7a2a2a;}")
        btn_clr.clicked.connect(self._view.clear_annotations); lay.addWidget(btn_clr)
        lay.addWidget(self._sep())

        self._btn_grid = QPushButton("⊞ Grid"); self._btn_grid.setFixedHeight(28)
        self._btn_grid.setCheckable(True)
        self._btn_grid.setStyleSheet(
            "QPushButton{background:#444;color:#ccc;border-radius:3px;font-size:11px;"
            "border:2px solid #666;}QPushButton:checked{background:#39A650;color:white;"
            "border:2px solid #fff;}QPushButton:hover{background:#555;}")
        self._btn_grid.clicked.connect(self._toggle_grid); lay.addWidget(self._btn_grid)

        self._spin_grid = QSpinBox(); self._spin_grid.setRange(2,20)
        self._spin_grid.setValue(3); self._spin_grid.setPrefix("÷")
        self._spin_grid.setFixedWidth(52)
        self._spin_grid.valueChanged.connect(self._set_grid_divs)
        lay.addWidget(self._spin_grid)
        lay.addWidget(self._sep())

        # Hintergrundfarbe-Button
        self._btn_bg = QPushButton("🎨 BG"); self._btn_bg.setFixedHeight(28)
        self._btn_bg.setToolTip("Change canvas background colour")
        self._btn_bg.setStyleSheet(
            "QPushButton{background:#444;color:#ccc;border-radius:3px;"
            "font-size:11px;}QPushButton:hover{background:#555;}")
        self._btn_bg.clicked.connect(self._pick_bg_color)
        lay.addWidget(self._btn_bg)
        lay.addWidget(self._sep())

        btn_save = QPushButton("💾 Save as…"); btn_save.setFixedHeight(28)
        btn_save.setStyleSheet("QPushButton{background:#1a3a5a;color:#8cf;border-radius:3px;"
                               "font-size:11px;}QPushButton:hover{background:#2a5a8a;}")
        btn_save.clicked.connect(self._save_canvas); lay.addWidget(btn_save)

        btn_reset = QPushButton("⌖ Reset"); btn_reset.setFixedHeight(28)
        btn_reset.setStyleSheet("QPushButton{background:#444;color:#ccc;border-radius:3px;"
                                "font-size:11px;}QPushButton:hover{background:#555;}")
        btn_reset.clicked.connect(self._reset_view); lay.addWidget(btn_reset)

        lay.addWidget(self._sep())

        btn_proj_save = QPushButton("📁 Save project"); btn_proj_save.setFixedHeight(28)
        btn_proj_save.setStyleSheet("QPushButton{background:#2a3a5a;color:#adf;border-radius:3px;"
                                    "font-size:11px;}QPushButton:hover{background:#3a5a8a;}")
        btn_proj_save.clicked.connect(self._save_project); lay.addWidget(btn_proj_save)

        btn_proj_load = QPushButton("📂 Load project"); btn_proj_load.setFixedHeight(28)
        btn_proj_load.setStyleSheet("QPushButton{background:#2a3a5a;color:#adf;border-radius:3px;"
                                    "font-size:11px;}QPushButton:hover{background:#3a5a8a;}")
        btn_proj_load.clicked.connect(self._load_project); lay.addWidget(btn_proj_load)

        lay.addWidget(self._sep())

        # VK4-Kanal-Toggle (nur sichtbar wenn ein VK4-Bild selektiert ist)
        self._vk4_sep   = self._sep()
        self._vk4_label = QLabel("VK4:")
        self._vk4_label.setStyleSheet("color:#aaa;font-size:11px;")
        self._vk4_btns: dict = {}
        lay.addWidget(self._vk4_sep)
        lay.addWidget(self._vk4_label)
        self._vk4_btn_container = QWidget()
        self._vk4_btn_layout    = QHBoxLayout(self._vk4_btn_container)
        self._vk4_btn_layout.setContentsMargins(0,0,0,0)
        self._vk4_btn_layout.setSpacing(3)
        lay.addWidget(self._vk4_btn_container)
        self._vk4_sep.setVisible(False)
        self._vk4_label.setVisible(False)
        self._vk4_btn_container.setVisible(False)

        lay.addStretch(1)
        return bar

    def _update_vk4_toolbar(self):
        """Zeigt/versteckt die VK4-Kanal-Buttons je nach selektiertem Item."""
        """Zeigt/versteckt den VK4-Kanal-Toggle je nach selektiertem Item."""
        item = self._selected_vk4_item()
        if item is None:
            self._vk4_sep.setVisible(False)
            self._vk4_label.setVisible(False)
            self._vk4_btn_container.setVisible(False)
            return
        path = getattr(item, "_source_path", "")
        channels = _vk4_available_channels(path)
        if len(channels) < 2:
            self._vk4_sep.setVisible(False)
            self._vk4_label.setVisible(False)
            self._vk4_btn_container.setVisible(False)
            return
        # Buttons neu aufbauen wenn Kanal-Set sich geändert hat
        existing = list(self._vk4_btns.keys())
        if existing != channels:
            for btn in self._vk4_btns.values():
                self._vk4_btn_layout.removeWidget(btn)
                btn.deleteLater()
            self._vk4_btns = {}
            for ch in channels:
                btn = QPushButton(VK4_CH_LABELS[ch])
                btn.setFixedHeight(26)
                btn.setCheckable(True)
                btn.setStyleSheet(
                    "QPushButton{background:#444;color:#ccc;border-radius:3px;font-size:10px;"
                    "border:1px solid #666;}QPushButton:checked{background:#39A650;color:#fff;"
                    "border:1px solid #fff;}QPushButton:hover{background:#555;}")
                btn.clicked.connect(lambda c, channel=ch: self._switch_vk4_channel(channel))
                self._vk4_btn_layout.addWidget(btn)
                self._vk4_btns[ch] = btn
        # Aktiven Kanal markieren
        active_ch = getattr(item, "_vk4_channel", "")
        for ch, btn in self._vk4_btns.items():
            btn.setChecked(ch == active_ch)
        self._vk4_sep.setVisible(True)
        self._vk4_label.setVisible(True)
        self._vk4_btn_container.setVisible(True)

    def _selected_vk4_item(self):
        """Gibt das selektierte CanvasImageItem zurück wenn es eine VK4-Datei ist (sonst None)."""
        """Gibt das selektierte CanvasImageItem zurück, wenn es eine VK4-Datei ist."""
        try:
            for item in self._view.scene().selectedItems():
                if isinstance(item, CanvasImageItem):
                    path = getattr(item, "_source_path", "")
                    if _is_vk4(path):
                        return item
        except Exception:
            pass
        return None

    def _switch_vk4_channel(self, channel: str):
        """Lädt den gewählten VK4-Kanal und tauscht das Pixmap im selektierten Item."""
        item = self._selected_vk4_item()
        if item is None:
            return
        path = getattr(item, "_source_path", "")
        pm = _load_vk4_channel(path, channel)
        if pm is None or pm.isNull():
            return
        # Kein Downscaling → volles Original für scharfen Zoom
        self._view.push_undo()
        item.swap_pixmap(pm)
        item._vk4_channel = channel
        self._update_vk4_toolbar()

    def _select_tool(self, tool):
        """Setzt das aktive Tool und aktualisiert Toolbar-Buttons und Item-Movable-Flag."""
        self._active_tool = tool
        names = {
            TOOL_PAN:"🖐 Pan", TOOL_ARROW:"↗ Arrow", TOOL_ELLIPSE:"⬭ Ellipse",
            TOOL_RECT:"▭ Rect", TOOL_FREE:"✏ Freehand", TOOL_TEXT:"T Text",
            TOOL_HIGHLIGHT:"🖊 Highlight", TOOL_MARKER:"① Marker",
            TOOL_ERASER:"⌫ Eraser", TOOL_MOVE:"⤢ Move",
        }
        for tid, btn in self._tool_btns.items():
            btn.setChecked(tid == tool); btn.setStyleSheet(self._tool_style(tid == tool))
        try: self._lbl_tool.setText(names.get(tool, tool))
        except Exception: pass
        self._view.set_tool(tool, self._active_color, self._active_size)
        movable = (tool == TOOL_PAN)
        for item in self._scene.items():
            if isinstance(item, CanvasImageItem):
                item.setFlag(QGraphicsItem.ItemIsMovable, movable)

    def _select_color(self, color):
        """Setzt die aktive Annotations-Farbe und aktualisiert die Farbbuttons."""
        self._active_color = color
        hx = {"red":"#DC3232","yellow":"#F0C800","green":"#32C850",
               "white":"#FFFFFF","blue":"#3282DC"}
        for cid, btn in self._color_btns.items():
            a = (cid == color); btn.setChecked(a)
            btn.setStyleSheet(
                f"QPushButton{{background:{hx[cid]};border-radius:11px;"
                f"border:3px solid {'#fff' if a else '#555'};}}")
        self._view.set_tool(self._active_tool, color, self._active_size)

    def _select_size(self, size):
        """Setzt die aktive Strichstärke und aktualisiert die Grössen-Buttons."""
        self._active_size = size
        for sz, btn in self._size_btns.items():
            btn.setChecked(sz==size); btn.setStyleSheet(self._size_style(sz==size))
        self._view.set_tool(self._active_tool, self._active_color, size)

    def _toggle_grid(self):
        """Schaltet das Gitternetz ein/aus."""
        self._view.set_grid(self._btn_grid.isChecked(), self._spin_grid.value())

    def _set_grid_divs(self, n):
        """Setzt die Gitterteilungsanzahl."""
        if self._btn_grid.isChecked(): self._view.set_grid(True, n)

    def _pick_bg_color(self):
        """Öffnet einen Farbwähler für die Canvas-Hintergrundfarbe."""
        current = self._view._bg_color
        color = QColorDialog.getColor(current, self, "Choose background colour")
        if color.isValid():
            self._view.set_bg_color(color)
            # Button-Vorschau aktualisieren
            r, g, b = color.red(), color.green(), color.blue()
            text_color = "#000" if (r*0.299 + g*0.587 + b*0.114) > 128 else "#fff"
            self._btn_bg.setStyleSheet(
                f"QPushButton{{background:{color.name()};color:{text_color};"
                f"border-radius:3px;font-size:11px;"
                f"border:1px solid #888;}}QPushButton:hover{{opacity:0.85;}}")

    def _reset_view(self):
        """Setzt Zoom und Position des Canvas zurück (nach Bestätigung)."""
        ans = QMessageBox.question(
            self,
            "Reset Canvas?",
            "Really reset the canvas?\n\n"
            "This will reset zoom and position.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return
        self._view.resetTransform(); self._view.centerOn(0, 0)

    def _save_canvas(self):
        """Rendert den Canvas und speichert ihn als Bild-Datei."""
        pm = self._view.render_to_pixmap()
        if pm.isNull(): return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save canvas as...", "canvas.png",
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp);;TIFF (*.tif *.tiff)")
        if not path: return
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        fmt = {"jpg":"JPEG","jpeg":"JPEG","bmp":"BMP","tif":"TIFF","tiff":"TIFF"}.get(ext,"PNG")
        pm.save(path, fmt)

    def _on_image_clicked(self, meta):
        """Lädt ein aus der Liste ausgewähltes Bild/Dokument auf den Canvas."""
        path = _build_full_path(meta)
        is_doc = _is_word(path) or _is_pdf(path) or _is_excel(path)
        if is_doc:
            label = ("Loading Word..." if _is_word(path)
                     else "Loading PDF..." if _is_pdf(path)
                     else "Loading Excel...")
            ov = getattr(self, "_loading_overlay", None)
            if ov:
                ov.start(label)
            rsigs = _RenderSignals()
            rsigs.done.connect(self._on_render_done)
            self._sigs_list.append(rsigs)
            _pool.start(_RenderWorker(path, meta, rsigs))
        else:
            sigs = _PixmapSignals()
            sigs.done.connect(self._on_pixmap_loaded)
            self._sigs_list.append(sigs)
            _pool.start(_PixmapLoader(path, meta, sigs))

    def _on_render_done(self, pm, err, meta):
        """Callback für _RenderWorker (PDF/Excel/Word): fügt das gerenderte Bild dem Canvas hinzu."""
        """Callback für _RenderWorker (PDF/Excel/Word)."""
        ov = getattr(self, "_loading_overlay", None)
        if pm is None:
            if ov: ov.stop()
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Ladefehler", err or "Unknown error.")
            return
        try:
            if _is_excel(_build_full_path(meta)) or _is_word(_build_full_path(meta)):
                if max(pm.width(), pm.height()) > 2400:
                    pm = pm.scaled(2400, 2400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            # Normale Bilder: kein Downscaling → volles Original für scharfen Zoom
            item = self._view.add_image(pm, str(meta.get("OriginalFilename") or ""),
                                        source_path=_build_full_path(meta))
            if item is not None:
                item._vk4_channel = ""
                item._pdf_page    = meta.get("_pdf_page",    None)
                item._excel_sheet = meta.get("_excel_sheet", None)
                item._word_page   = meta.get("_word_page",   None)
            if ov: ov.finish()
            self._update_vk4_toolbar()
        except Exception as e:
            if ov: ov.stop()
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", str(e))

    def _on_pixmap_loaded(self, path, meta):
        """Callback für normale Bilder und VK4: lädt und fügt das Bild dem Canvas hinzu."""
        """Callback für normale Bilder und VK4 (Dokumente laufen über _on_render_done)."""
        if not path: return
        try:
            vk4_ch = ""
            if _is_vk4(path):
                chs = _vk4_available_channels(path)
                vk4_ch = chs[0] if chs else ""
            pm = _load_pixmap_from_path(path, vk4_ch)
            if pm is None or pm.isNull():
                QMessageBox.warning(self, "Loading failed",
                                    "Could not be loaded:\n" + path)
                return
            # Kein Downscaling → volles Original für scharfen Zoom
            item = self._view.add_image(pm, str(meta.get("OriginalFilename") or ""),
                                        source_path=path)
            if item is not None:
                item._vk4_channel = vk4_ch
                item._pdf_page    = None
                item._excel_sheet = None
                item._word_page   = None
            self._update_vk4_toolbar()
        except Exception as e:
            QMessageBox.critical(self, "Error while loading", str(e))
    def _save_project(self):
        """Öffnet Dialog und speichert das Canvas-Projekt als .ttcanvas."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save project as...", "canvas_projekt.ttcanvas",
            "TrippleT Canvas (*.ttcanvas);;All files (*.*)")
        if not path:
            return
        try:
            self._view.save_project(path)
        except Exception as e:
            QMessageBox.critical(self, "Error while saving", str(e))

    def _load_project(self):
        """Öffnet Dialog und lädt ein .ttcanvas-Projekt."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Load project…", "",
            "TrippleT Canvas (*.ttcanvas);;All files (*.*)")
        if not path:
            return
        try:
            self._view.load_project(path)
            # BG-Button nach dem Laden aktualisieren
            color = self._view._bg_color
            r, g, b = color.red(), color.green(), color.blue()
            text_color = "#000" if (r*0.299 + g*0.587 + b*0.114) > 128 else "#fff"
            self._btn_bg.setStyleSheet(
                f"QPushButton{{background:{color.name()};color:{text_color};"
                f"border-radius:3px;font-size:11px;"
                f"border:1px solid #888;}}QPushButton:hover{{opacity:0.85;}}")
        except Exception as e:
            QMessageBox.critical(self, "Error while loading", str(e))

    def _go_home(self):
        """Navigiert zurück zum Home-Screen."""
        if callable(self._on_back_home): self._on_back_home()

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

    def showEvent(self, ev):
        """Lädt die Bildliste beim ersten Öffnen des Screens."""
        super().showEvent(ev)
        try:
            QTimer.singleShot(150, self._panel.load_images)
        except Exception: pass
        try:
            self._refresh_sidebar()
        except Exception:
            pass