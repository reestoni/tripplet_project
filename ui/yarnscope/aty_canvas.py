"""
aty_canvas.py – Standalone-Canvas-Klassen für ATY-Garnvisualisierung in TrippleT.

Extrahiert und bereinigt aus ui/widgets/garn/garngraf.py (YarnScope).
Alle drei Klassen sind unabhängig von garngraf.py und können direkt in
TrippleT verwendet werden – kein Cross-Import nach YarnScope nötig.

Klassen:
    ATYGarnCanvas   – Matplotlib-basierter Garnspiegel (10 × 200 mm Bänder,
                      schwarzer Hintergrund, weisse Garnbänder, farbige Bin-Overlays).
    ATYFabricCanvas – QPainter-basierter Fabric-View (horizontale Bänder,
                      Bin-Farbeinfärbung entlang X).
    ATYKnittedCanvas – QPainter-basierter Knitted-View (Zickzack-Reihen,
                       Bin-Farbeinfärbung entlang X).

Farbkonvention ATY-Bins:
    Bin 1 «Kurzhocker» (Steigung > BIN_THRESHOLD µm/mm): #ffcc88 / #e07b00
    Bin 2 «Langwelle»  (Steigung <= BIN_THRESHOLD µm/mm): #88dddd / #0e8a8a

Verwendung:
    from ui.yarnscope.aty_canvas import ATYGarnCanvas, ATYFabricCanvas, ATYKnittedCanvas

    # Garnspiegel
    canvas = ATYGarnCanvas(parent=self)
    canvas.plot_aty(arr_mm, mm_per_point=0.25, spots=spots)

    # Fabric
    fabric = ATYFabricCanvas(parent=self)
    fabric.set_color_spans(spans_per_band, x_range_mm=(0.0, 200.0))

    # Knitted
    knitted = ATYKnittedCanvas(parent=self, rows=50)
    knitted.set_color_spans(spans_per_row, x_range_mm=(0.0, 200.0))
"""

from __future__ import annotations

import numpy as np
from typing import List, Tuple, Any

from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtCore import Signal
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ---------------------------------------------------------------------------
# ATY-Farbkonstanten
# ---------------------------------------------------------------------------

# Bin 1 – Kurzhocker (hohe Steigung: steil und kurz)
BIN1_FILL  = "#ffcc88"   # Füllfarbe für fill_between
BIN1_EDGE  = "#e07b00"   # Randfarbe / Linie

# Bin 2 – Langwelle (flache Steigung: breit und flach)
BIN2_FILL  = "#88dddd"
BIN2_EDGE  = "#0e8a8a"

# Segmentlänge pro Garnspiegel-Zeile (mm)
_SEGMENT_LEN_MM = 200.0
# Standardanzahl Zeilen im Garnspiegel
_NUM_TURNS = 10
# Standard-Messabstand (mm/Punkt)
_MM_PER_POINT = 0.25


# ===========================================================================
# ATYGarnCanvas – Garnspiegel mit ATY-Bin-Einfärbung
# ===========================================================================

class ATYGarnCanvas(FigureCanvas):
    """Matplotlib-Canvas für ATY-Garnspiegeldiagramme.

    Zeigt das Garnprofil als 10 × 200 mm Bänder (weiss auf schwarz).
    Dickstellen werden nach Bin 1 (orange) und Bin 2 (blaugrün) eingefärbt.

    Signale:
        limitsChanged: Emittiert (xlim, ylim) bei Zoom/Pan-Änderung.

    Verwendung:
        canvas = ATYGarnCanvas(parent=self)
        canvas.plot_aty(arr_mm, mm_per_point=0.25, spots=spots)
    """

    # Signal: wird bei Zoom/Pan emittiert
    limitsChanged = Signal(tuple, tuple)

    def __init__(self, parent=None):
        # Matplotlib Figure mit schwarzem Hintergrund
        fig = Figure(figsize=(10, 3.6), dpi=100)
        self.ax = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)
        fig.patch.set_facecolor("black")
        self.ax.set_facecolor("black")

        # Gespeicherte Vollbild-Limits für Reset-Zoom
        self.full_xlim = (0.0, 1.0)
        self.full_ylim = (0.0, 1.0)

        # Interne Flags für Limit-Emit
        self._suppress_emit = False
        self._last_xlim = None
        self._last_ylim = None

        # Mausrad-Zoom deaktivierbar (z.B. wenn eingebettet in Tab)
        self._no_scroll = False

        # Matplotlib-Events verbinden
        self.mpl_connect('draw_event',   self._on_draw)
        self.mpl_connect('scroll_event', self._on_scroll)
        self.ax.callbacks.connect('xlim_changed', self._on_limits_changed)
        self.ax.callbacks.connect('ylim_changed', self._on_limits_changed)

    # ── Interne Limit-Verwaltung ──────────────────────────────────────────

    def _maybe_emit_if_changed(self):
        """Emittiert limitsChanged wenn sich die Limits seit dem letzten Emit geändert haben."""
        if self._suppress_emit:
            return
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        if (xlim != self._last_xlim) or (ylim != self._last_ylim):
            self._last_xlim, self._last_ylim = xlim, ylim
            self.limitsChanged.emit(xlim, ylim)

    def _on_draw(self, _):
        self._maybe_emit_if_changed()

    def _on_limits_changed(self, _):
        self._maybe_emit_if_changed()

    def _on_scroll(self, event):
        """Zoom per Mausrad (deaktivierbar via self._no_scroll)."""
        if self._no_scroll or event.inaxes != self.ax:
            return
        scale = 1.15 if event.button == 'up' else (1 / 1.15 if event.button == 'down' else 1.0)
        if scale == 1.0:
            return
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        cx, cy = event.xdata, event.ydata
        if cx is None or cy is None:
            return

        def zoom(l0, l1, c, s):
            """Berechnet neues Intervall nach Zoom um Punkt c mit Faktor s."""
            span   = l1 - l0
            new_sp = span / s
            lf     = (c - l0) / span if span else 0.5
            nl0    = c - new_sp * lf
            return nl0, nl0 + new_sp

        nx0, nx1 = zoom(x0, x1, cx, scale)
        ny0, ny1 = zoom(y0, y1, cy, scale)
        self._suppress_emit = True
        self.ax.set_xlim(nx0, nx1)
        self.ax.set_ylim(ny0, ny1)
        self.figure.canvas.draw_idle()
        self._suppress_emit = False
        self._last_xlim, self._last_ylim = (nx0, nx1), (ny0, ny1)
        self.limitsChanged.emit((nx0, nx1), (ny0, ny1))

    def set_full_limits(self, xlim, ylim):
        """Speichert Vollbild-Limits für späteren Reset via full_view()."""
        self.full_xlim = tuple(xlim)
        self.full_ylim = tuple(ylim)
        self._last_xlim = tuple(xlim)
        self._last_ylim = tuple(ylim)

    def full_view(self):
        """Setzt Zoom auf gespeicherte Vollbild-Limits zurück."""
        self._suppress_emit = True
        self.ax.set_xlim(*self.full_xlim)
        self.ax.set_ylim(*self.full_ylim)
        self.figure.canvas.draw_idle()
        self._suppress_emit = False
        self._last_xlim, self._last_ylim = self.full_xlim, self.full_ylim

    # ── Hauptzeichenmethode ───────────────────────────────────────────────

    def plot_aty(
        self,
        arr_mm:       np.ndarray,
        mm_per_point: float = _MM_PER_POINT,
        spots:        List[dict] | None = None,
        num_turns:    int = _NUM_TURNS,
        gap_factor:   float = 2.0,
    ):
        """Zeichnet ATY-Garnspiegel mit Dickstellen-Bin-Einfärbung.

        Args:
            arr_mm:       Garndicke-Array in mm (gesamte Serie).
            mm_per_point: Messabstand in mm pro Datenpunkt (Standard: 0.25 mm).
            spots:        Liste von Dickstellen-Dicts aus detect_thick_spots().
                          Jeder Eintrag hat mindestens: start_idx, n_pts, F04_bin.
                          Wenn None: nur weisses Garnband, keine Einfärbung.
            num_turns:    Anzahl Zeilen im Garnspiegel (Standard: 10).
            gap_factor:   Vertikaler Abstand zwischen Zeilen als Vielfaches
                          des maximalen Garndurchmessers (Standard: 2.0).
        """
        self.ax.clear()
        self.figure.patch.set_facecolor("black")
        self.ax.set_facecolor("black")

        arr = np.asarray(arr_mm, dtype=float)
        turns = max(1, min(num_turns, _NUM_TURNS))

        # Zu wenig Daten: leere Ansicht
        if arr.size < turns:
            self.draw_idle()
            return

        # Array in Segmente à 200mm aufteilen
        pts_per_seg = max(1, len(arr) // turns)
        segments    = np.split(arr[:pts_per_seg * turns], turns)
        mm_step     = _SEGMENT_LEN_MM / float(pts_per_seg)
        global_max  = float(np.max(arr))
        row_spacing = global_max * gap_factor
        x_mm        = np.linspace(0.0, _SEGMENT_LEN_MM, pts_per_seg, endpoint=False)

        # ── Weisse Basisbänder ────────────────────────────────────────────
        for i, seg in enumerate(segments):
            seg   = np.asarray(seg, dtype=float)
            base  = -i * row_spacing
            self.ax.fill_between(
                x_mm,
                base - seg / 2.0,
                base + seg / 2.0,
                color="white", linewidth=0,
            )

        # ── Dickstellen einfärben ─────────────────────────────────────────
        if spots:
            for sp in spots:
                s_idx = int(sp.get("start_idx", 0))
                n_pts = int(sp.get("n_pts", 0))
                bin_id = int(sp.get("F04_bin", 2))

                # Segment-Zeile ermitteln (welche der 10 Zeilen ist betroffen)
                seg_row = s_idx // pts_per_seg
                if seg_row >= turns:
                    continue  # ausserhalb der Anzahl Zeilen

                # Lokaler Index innerhalb des Segments
                local_s = s_idx - seg_row * pts_per_seg
                local_e = min(local_s + n_pts, pts_per_seg)
                if local_e <= local_s:
                    continue

                seg  = np.asarray(segments[seg_row], dtype=float)
                base = -seg_row * row_spacing
                xs   = x_mm[local_s:local_e]
                yt   = base + seg[local_s:local_e] / 2.0
                yb   = base - seg[local_s:local_e] / 2.0

                c_fill = BIN1_FILL if bin_id == 1 else BIN2_FILL
                c_edge = BIN1_EDGE if bin_id == 1 else BIN2_EDGE
                self.ax.fill_between(xs, yb, yt, color=c_fill, alpha=0.85, linewidth=0, zorder=3)
                self.ax.plot(xs, yt, color=c_edge, linewidth=0.7, zorder=4)
                self.ax.plot(xs, yb, color=c_edge, linewidth=0.7, zorder=4)

        # ── Achsen und Limits ─────────────────────────────────────────────
        self.ax.axis("off")
        self.ax.set_aspect("auto")
        self.ax.set_xmargin(0)
        self.ax.set_ymargin(0)
        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0)

        y_top_first   = float(np.max(segments[0]))  / 2.0
        y_bottom_last = -(turns - 1) * row_spacing - float(np.max(segments[-1])) / 2.0
        y_margin      = 0.05 * global_max
        xlim = (0.0, _SEGMENT_LEN_MM)
        ylim = (y_bottom_last - y_margin, y_top_first + y_margin)

        self.ax.set_xlim(*xlim)
        self.ax.set_ylim(*ylim)
        self.set_full_limits(xlim, ylim)
        self.draw_idle()


# ===========================================================================
# ATYFabricCanvas – Fabric-Ansicht (horizontale Bänder, QPainter)
# ===========================================================================

class ATYFabricCanvas(QtWidgets.QWidget):
    """QPainter-basierter Fabric-View für ATY-Garnvisualisierung.

    Zeigt das Garn als horizontale Bänder (weiss auf schwarz, 200 mm lang).
    Dickstellen-Bereiche werden farbig überlagert (Bin 1: orange, Bin 2: blaugrün).

    Jedes Band entspricht 200 mm Garmlänge. Farbspans werden als
    (x0_mm, x1_mm, hex_color) pro Band übergeben.

    Verwendung:
        fabric = ATYFabricCanvas(parent=self)
        fabric.set_color_spans(spans_per_band)   # List[List[(x0, x1, color)]]
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(False)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )
        # Interne Band-Anzahl (wird via set_band_count oder set_color_spans gesetzt)
        self._band_count = 250
        # Farbspans je Band: List[List[Tuple[x0_mm, x1_mm, hex_color]]]
        self._spans: List[List[Tuple[float, float, str]]] = [[] for _ in range(250)]
        # X-Bereich in mm (Standard: ein Band = 0 bis 200 mm)
        self._xrange_mm: Tuple[float, float] = (0.0, 200.0)

    def set_band_count(self, n: int):
        """Setzt die Anzahl sichtbarer Bänder (1..500) und löst Redraw aus.

        Args:
            n: Gewünschte Bandanzahl. Wird auf [1, 500] geklemmt.
        """
        try:
            n = int(n)
        except Exception:
            return
        n = max(1, min(500, n))
        self._band_count = n
        # Spans-Liste auf neue Länge anpassen
        cur = list(self._spans)
        if len(cur) < n:
            cur.extend([[] for _ in range(n - len(cur))])
        self._spans = cur[:n]
        self.update()

    def set_color_spans(
        self,
        spans_per_segment: List[List[Tuple[float, float, str]]],
        x_range_mm: Tuple[float, float] = (0.0, 200.0),
    ):
        """Setzt Farbspans für alle Bänder und löst Redraw aus.

        Args:
            spans_per_segment: Liste von Band-Span-Listen.
                               Jeder Eintrag: [(x0_mm, x1_mm, '#hex'), ...].
            x_range_mm:        Darstellungsbereich in mm (Standard: 0..200).
        """
        try:
            inferred = int(len(spans_per_segment)) if spans_per_segment is not None else 0
        except Exception:
            inferred = 0
        n = inferred if 1 <= inferred <= 500 else max(50, min(500, self._band_count))
        self._band_count = n
        self._spans = [
            list(spans_per_segment[i]) if (spans_per_segment is not None and i < len(spans_per_segment))
            else []
            for i in range(n)
        ]
        self._xrange_mm = tuple(x_range_mm)
        self.update()

    def minimumSizeHint(self):
        return QtCore.QSize(200, 200)

    def paintEvent(self, event):
        """Zeichnet alle Bänder mit optionalen Farboverlays."""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)

        # Schwarzer Hintergrund
        painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0))

        w = self.width()
        h = self.height()
        n = max(1, len(self._spans))

        # Gap dynamisch reduzieren damit pro Band mindestens 1px übrigbleibt
        gap = 2
        while gap > 0 and (gap * (n - 1)) > (h - n):
            gap -= 1

        band_h     = (h - gap * (n - 1)) / float(n) if n else 1.0
        total_h    = band_h * n + gap * (n - 1)
        start_y    = (h - total_h) / 2.0   # vertikal zentrieren
        x0_mm, x1_mm = self._xrange_mm
        xspan      = max(1e-9, x1_mm - x0_mm)

        painter.setPen(QtCore.Qt.NoPen)

        for i in range(n):
            y_top = start_y + i * (band_h + gap)
            yi0   = int(round(y_top))
            yi1   = int(round(y_top + band_h))
            bh    = max(1, yi1 - yi0)

            # Weisses Basisband
            painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))
            painter.drawRect(0, yi0, w, bh)

            # Farboverlays (Bin 1 / Bin 2)
            for (sx_mm, ex_mm, hexcol) in (self._spans[i] if i < len(self._spans) else []):
                sx  = max(x0_mm, min(ex_mm, sx_mm))
                ex  = min(x1_mm, max(sx_mm, ex_mm))
                if ex <= sx:
                    continue
                px0 = int(round((sx - x0_mm) / xspan * w))
                px1 = int(round((ex - x0_mm) / xspan * w))
                if px1 <= px0:
                    continue
                painter.setBrush(QtGui.QBrush(QtGui.QColor(hexcol)))
                painter.drawRect(px0, yi0, px1 - px0, bh)


# ===========================================================================
# ATYKnittedCanvas – Knitted-Ansicht (Zickzack-Reihen, QPainter)
# ===========================================================================

class ATYKnittedCanvas(QtWidgets.QWidget):
    """QPainter-basierter Knitted-View für ATY-Garnvisualisierung.

    Zeigt das Garn als Zickzack-Reihen (weiss auf schwarz, simuliertes
    Strickbild). Dickstellen-Bereiche werden farbig überlagert
    (Bin 1: orange, Bin 2: blaugrün).

    Eine Reihe entspricht 400 mm Garnlänge.

    Verwendung:
        knitted = ATYKnittedCanvas(parent=self, rows=50)
        knitted.set_color_spans(spans_per_row)   # List[List[(x0, x1, color)]]
    """

    def __init__(self, parent=None, rows: int = 50):
        super().__init__(parent)
        # Anzahl Reihen (50..250)
        self.rows = max(50, min(250, int(rows)))
        # Farbspans je Reihe
        self._spans: List[List[Tuple[float, float, str]]] = [[] for _ in range(self.rows)]
        # X-Bereich in mm (korrespondiert zum Garnspiegel-Ausschnitt 0..200)
        self._xrange_mm: Tuple[float, float] = (0.0, 200.0)
        # Länge einer Strickrcihe in mm
        self._row_len_mm: float = 400.0
        self.setAutoFillBackground(False)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )

    def set_row_count(self, n: int):
        """Setzt die Anzahl Strickreihen (1..250) und löst Redraw aus.

        Args:
            n: Gewünschte Reihenanzahl. Wird auf [1, 250] geklemmt.
        """
        try:
            n = int(n)
        except Exception:
            return
        n = max(1, min(250, n))
        self.rows = n
        cur = list(self._spans)
        if len(cur) < n:
            cur.extend([[] for _ in range(n - len(cur))])
        self._spans = cur[:n]
        self.update()

    def set_color_spans(
        self,
        spans_per_row: List[List[Tuple[float, float, str]]],
        x_range_mm: Tuple[float, float] = (0.0, 200.0),
        row_len_mm: float = 400.0,
    ):
        """Setzt Farbspans für alle Reihen und löst Redraw aus.

        Args:
            spans_per_row: Liste von Reihen-Span-Listen.
                           Jeder Eintrag: [(x0_mm, x1_mm, '#hex'), ...].
            x_range_mm:    Darstellungsbereich in mm (Garnspiegel-X-Achse).
            row_len_mm:    Länge einer Strickreihe in mm (Standard: 400 mm).
        """
        n = max(1, int(getattr(self, 'rows', 50)))
        self._spans = [
            list(spans_per_row[i]) if (spans_per_row is not None and i < len(spans_per_row))
            else []
            for i in range(n)
        ]
        self._xrange_mm  = tuple(x_range_mm)
        self._row_len_mm = float(row_len_mm)
        self.update()

    def minimumSizeHint(self):
        return QtCore.QSize(200, 200)

    def _row_points(
        self,
        inner: QtCore.QRectF,
        row_index: int,
    ) -> Tuple[List[float], List[float]]:
        """Berechnet Zickzack-Punktkoordinaten für eine einzelne Strickreihe.

        Args:
            inner:     Nutzbares Rechteck (ohne Padding).
            row_index: Index der Reihe (0-basiert).

        Returns:
            (xs, ys): Listen von X- und Y-Koordinaten der Zickzack-Punkte.
        """
        rows        = max(1, self.rows)
        row_spacing = inner.height() / rows
        # Amplitude: 55% des Zeilenabstands (begrenzt auf 60%)
        A           = min(0.6 * row_spacing, 0.55 * row_spacing)
        W           = inner.width()
        total_pts   = max(20, int(self._row_len_mm)) + 1
        dx          = W / (total_pts - 1)
        y_mid       = inner.top() + (row_index + 0.5) * row_spacing
        y_top       = y_mid - A
        y_bot       = y_mid + A
        # Jede zweite Reihe beginnt oben statt unten (Strickmuster)
        start_top   = (row_index % 2 == 0)
        xs = [inner.left() + i * dx for i in range(total_pts)]
        ys = []
        flip = start_top
        for _ in range(total_pts):
            ys.append(y_bot if flip else y_top)
            flip = not flip
        return xs, ys

    def paintEvent(self, event):
        """Zeichnet alle Zickzack-Reihen mit optionalen Farboverlays."""
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)

        rect = self.rect()
        p.fillRect(rect, QtGui.QColor(0, 0, 0))

        W   = max(1, rect.width())
        H   = max(1, rect.height())
        pad = max(8, int(0.02 * min(W, H)))
        inner = QtCore.QRectF(pad, pad, W - 2 * pad, H - 2 * pad)

        # Stift für Grundlinie (weiss, Breite abhängig von Reihenanzahl)
        base_pen = QtGui.QPen(QtGui.QColor(255, 255, 255))
        base_pen.setWidthF(max(1.0, 0.2 * (inner.height() / max(1, self.rows))))
        base_pen.setJoinStyle(QtCore.Qt.MiterJoin)
        base_pen.setCapStyle(QtCore.Qt.RoundCap)

        x0_mm, x1_mm = self._xrange_mm
        src_span      = max(1e-9, x1_mm - x0_mm)
        row_len_mm    = max(1e-9, self._row_len_mm)

        for r in range(self.rows):
            xs, ys = self._row_points(inner, r)

            # Zickzack-Grundlinie zeichnen
            p.setPen(base_pen)
            path = QtGui.QPainterPath()
            path.moveTo(xs[0], ys[0])
            for i in range(1, len(xs)):
                path.lineTo(xs[i], ys[i])
            p.drawPath(path)

            # Farboverlays über die Grundlinie malen
            spans = self._spans[r] if r < len(self._spans) else []
            for (sx_mm, ex_mm, hexcol) in spans:
                # Span auf Darstellungsbereich klemmen
                sx_cl = max(x0_mm, min(ex_mm, sx_mm))
                ex_cl = min(x1_mm, max(sx_mm, ex_mm))
                if ex_cl <= sx_cl:
                    continue
                # Fraktionale Position im Garnspiegel-Fenster → Reihen-Pixel
                f0    = (sx_cl - x0_mm) / src_span
                f1    = (ex_cl - x0_mm) / src_span
                x_px0 = float(inner.left() + f0 * row_len_mm / row_len_mm * inner.width())
                x_px1 = float(inner.left() + f1 * row_len_mm / row_len_mm * inner.width())
                if x_px1 <= x_px0:
                    continue
                pen_col = QtGui.QPen(QtGui.QColor(hexcol))
                pen_col.setWidthF(base_pen.widthF())
                pen_col.setJoinStyle(base_pen.joinStyle())
                pen_col.setCapStyle(base_pen.capStyle())
                p.setPen(pen_col)
                # Nur Segmente übermalen die innerhalb des Farbspans liegen
                for i in range(1, len(xs)):
                    xm = 0.5 * (xs[i - 1] + xs[i])
                    if x_px0 <= xm <= x_px1:
                        p.drawLine(
                            QtCore.QPointF(xs[i - 1], ys[i - 1]),
                            QtCore.QPointF(xs[i],     ys[i]),
                        )