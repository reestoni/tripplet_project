from __future__ import annotations
# ui/yarnscope/garngraf_canvas.py
"""Matplotlib-Canvas-Widget für YarnScope Garnspiegeldiagramme (GarnCanvas).

Stellt einen in PySide6 eingebetteten Matplotlib-Canvas bereit, der
Garndicken-Signale als Linienplot mit optionaler Knoten-Markierung anzeigt.

Hauptklasse: ``GarnCanvas``
  - Rendert DTY-Signale (plot_garnspiegel_dty) und Rohsignale (plot_garnspiegel)
  - Unterstützt Pan/Zoom via Mausrad
  - Emittiert ``limits_changed``-Signal wenn der Zoom-Bereich sich ändert
  - Farbverwaltung über ``_ColorState`` (eine Farbe pro Trial-Linie)
  - Sichtbarkeit je Linie über ``_VisibilityState``

Eingebunden in: ``garngraf.py`` (GarnGrafWidget) und ``screen_show_experiment.py``
"""

# ui/yarnscope/garngraf_canvas.py
# ---------------------------------------------------------------------------
# Abgespeckter Garnspiegel-Canvas für TrippleT / screen_show_experiment.
# Enthält nur GarnCanvas + die minimalen Hilfsklassen/-konstanten.
# Keine Abhängigkeiten auf YarnScope-spezifische Module (file_browser, core.db).
# ---------------------------------------------------------------------------

from pathlib import Path
from typing import Dict

import re
import numpy as np

from PySide6.QtCore import Qt, Signal, QSettings, QObject
from PySide6 import QtCore, QtWidgets, QtGui

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ------------------ Konstanten ------------------
MM_PER_POINT    = 0.25
SEGMENT_LEN_MM  = 200.0
NUM_TURNS       = 20
DEFAULT_GAP_FACTOR = 2.0

# Farben Dickstellen (rosa/rot)
DI_COLORS = {
    "Di11": "#ffd1e6", "Di12": "#ffb3d1", "Di13": "#ff94bd",
    "Di21": "#ff7aa9", "Di22": "#ff5c94", "Di23": "#ff3d80",
    "Di31": "#ff1f6b", "Di32": "#e60057", "Di33": "#b30045",
}
# Farben Dünnstellen (blau)
DUE_COLORS = {
    "Dü11": "#d6ecff", "Dü12": "#b9e0ff", "Dü13": "#9cd4ff",
    "Dü21": "#7fc8ff", "Dü22": "#62bbff", "Dü23": "#45afff",
    "Dü31": "#279fff", "Dü32": "#0f87e6", "Dü33": "#065da8",
}

LOAD_SAVED_COLORS_ON_START = False

CLASS_THRESHOLDS = {
    "Di": {"pct": [10.0, 20.0, 30.0], "mm": [1.0, 2.0, 3.0]},
    "Dü": {"pct": [10.0, 20.0, 30.0], "mm": [1.0, 2.0, 3.0]},
}


# ------------------ Farbstate ------------------

class _ColorState(QObject):
    """Verwaltet die Linienfarben für alle angezeigten Trial-Kurven.

    Weist jeder Trial-ID automatisch eine Farbe aus einer Farbpalette zu.
    """
    colorsChanged = Signal()

    def __init__(self):
        super().__init__()
        self._settings = QSettings('TrippleT', 'GarnCanvas')
        self.di_colors  = dict(DI_COLORS)
        self.due_colors = dict(DUE_COLORS)
        if LOAD_SAVED_COLORS_ON_START:
            try:
                for k in list(self.di_colors.keys()):
                    v = self._settings.value(f"colors/Di/{k}", type=str)
                    if v:
                        self.di_colors[k] = v
                for k in list(self.due_colors.keys()):
                    v = self._settings.value(f"colors/Due/{k}", type=str)
                    if v:
                        self.due_colors[k] = v
            except Exception:
                pass

    def set_color(self, family: str, key: str, hex_color: str):
        """Setzt eine Di- oder Dü-Farbe und emittiert colorsChanged."""
        if family == 'Di':
            self.di_colors[key] = hex_color
        else:
            self.due_colors[key] = hex_color
        try:
            self.colorsChanged.emit()
        except Exception:
            pass

    def reset_colors(self):
        """Setzt alle Farben auf die Standardwerte zurück."""
        self.di_colors  = dict(DI_COLORS)
        self.due_colors = dict(DUE_COLORS)
        try:
            self.colorsChanged.emit()
        except Exception:
            pass


COLOR_STATE = _ColorState()


class _VisibilityState(QtCore.QObject):
    """Verwaltet die Sichtbarkeit jeder Trial-Linie (ein/ausblenden)."""
    visibilityChanged = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self.enabled = {k: True for k in list(DI_COLORS) + list(DUE_COLORS)}

    def is_enabled(self, key: str) -> bool:
        """Gibt True zurück wenn die Linie für key sichtbar ist (Standard: True)."""
        return self.enabled.get(key, True)

    def set_enabled(self, key: str, on: bool):
        """Setzt die Sichtbarkeit für key und emittiert visibilityChanged."""
        self.enabled[key] = bool(on)
        try:
            self.visibilityChanged.emit()
        except Exception:
            pass


VISIBILITY_STATE = _VisibilityState()


# ------------------ GarnCanvas ------------------

class GarnCanvas(FigureCanvas):
    """Matplotlib-Canvas für Garnspiegeldiagramme eingebettet in PySide6.

    Signale:
        limits_changed: Wird emittiert wenn sich Zoom/Pan ändert (xlim, ylim).

    Verwendung:
        canvas = GarnCanvas(parent=self)
        canvas.plot_garnspiegel_dty(trials, step_mm=0.1)
    """
    """Matplotlib-Canvas für den Garnspiegel (10 × 200 mm, weisse Bänder mit Di/Dü-Overlays)."""

    limitsChanged  = Signal(tuple, tuple)
    spansComputed  = Signal(list)

    def __init__(self, parent=None):
        fig = Figure(figsize=(10, 3.6), dpi=120)
        self.ax = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)
        fig.patch.set_facecolor("black")
        self.ax.set_facecolor("black")
        self.full_xlim = (0.0, 1.0)
        self.full_ylim = (0.0, 1.0)
        self._suppress_emit = False
        self._last_xlim = None
        self._last_ylim = None
        self.mpl_connect('draw_event',   self._on_draw)
        self.mpl_connect('scroll_event', self._on_scroll)
        self.ax.callbacks.connect('xlim_changed', self._on_limits_changed)
        self.ax.callbacks.connect('ylim_changed', self._on_limits_changed)

    def _maybe_emit_if_changed(self):
        """Emittiert limits_changed wenn sich xlim oder ylim seit dem letzten Emit geändert hat."""
        if self._suppress_emit:
            return
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        if (xlim != self._last_xlim) or (ylim != self._last_ylim):
            self._last_xlim, self._last_ylim = xlim, ylim
            self.limitsChanged.emit(xlim, ylim)

    def _on_draw(self, _):            self._maybe_emit_if_changed()
    def _on_limits_changed(self, _):  self._maybe_emit_if_changed()

    def _on_scroll(self, event):
        """Zoom per Mausrad: Scroll = vertikaler Zoom, Shift+Scroll = horizontaler Zoom."""
        if getattr(self, "_no_scroll", False):
            return
        if event.inaxes != self.ax:
            return
        scale = 1.15 if event.button == 'up' else (1/1.15 if event.button == 'down' else 1.0)
        if scale == 1.0:
            return
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        cx, cy = event.xdata, event.ydata
        if cx is None or cy is None:
            return

        def zoom(l0, l1, c, s):
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
        """Setzt die gespeicherten Vollbild-Limits (für full_view() Reset)."""
        self.full_xlim = tuple(xlim)
        self.full_ylim = tuple(ylim)
        self._last_xlim = tuple(xlim)
        self._last_ylim = tuple(ylim)

    def full_view(self):
        """Setzt den Zoom auf die gespeicherten Vollbild-Limits zurück."""
        self._suppress_emit = True
        self.ax.set_xlim(*self.full_xlim)
        self.ax.set_ylim(*self.full_ylim)
        self.figure.canvas.draw_idle()
        self._suppress_emit = False
        self._last_xlim, self._last_ylim = self.full_xlim, self.full_ylim

    def plot_garnspiegel(
        # Zeichnet ein Rohsignal-Garnspiegeldiagramm (ohne Knoten-Markierung).
        # Für die vollständige Signatur siehe den Funktionskörper.
        self,
        data_mm_all: np.ndarray,
        gap_factor:      float = DEFAULT_GAP_FACTOR,
        show_colors:     bool  = True,
        row_spacing_ref: float | None = None,
        num_turns:       int   | None = None,
        mm_per_point:    float | None = None,
    ):
        self.ax.clear()
        self.figure.patch.set_facecolor("black")
        self.ax.set_facecolor("black")

        turns = int(num_turns) if num_turns is not None else NUM_TURNS
        turns = max(1, min(NUM_TURNS, turns))
        if data_mm_all is None or len(data_mm_all) < turns:
            self.draw_idle()
            return

        # mm_step aus übergebenem Messabstand ableiten (wie in YarnScope),
        # nicht aus Array-Länge – sonst stimmen need1/need2/need3 nicht.
        if mm_per_point is not None and mm_per_point > 0:
            mm_step = float(mm_per_point)
            points_per_segment = max(1, int(round(SEGMENT_LEN_MM / mm_step)))
        else:
            points_per_segment = max(1, len(data_mm_all) // turns)
            mm_step = SEGMENT_LEN_MM / float(points_per_segment) if points_per_segment > 0 else MM_PER_POINT
        segments  = np.split(data_mm_all[:points_per_segment * turns], turns)
        global_max = float(np.max(data_mm_all))
        row_spacing_base = float(row_spacing_ref) if row_spacing_ref is not None else global_max
        row_spacing = row_spacing_base * float(gap_factor)
        x_mm = np.linspace(0.0, SEGMENT_LEN_MM, points_per_segment, endpoint=False)

        # Weisse Basisbänder
        for i, seg in enumerate(segments):
            seg    = np.asarray(seg, dtype=float)
            base   = -i * row_spacing
            y_top  = base + seg / 2.0
            y_bot  = base - seg / 2.0
            self.ax.fill_between(x_mm, y_bot, y_top, color="white", linewidth=0)

        spans_per_segment = [[] for _ in range(turns)]

        if show_colors:
            mean_all = float(np.mean(data_mm_all))
            di_pct   = CLASS_THRESHOLDS["Di"]["pct"]
            due_pct  = CLASS_THRESHOLDS["Dü"]["pct"]
            di_len   = CLASS_THRESHOLDS["Di"]["mm"]
            due_len  = CLASS_THRESHOLDS["Dü"]["mm"]

            def runs(mask):
                res = []
                s = None
                for idx, flag in enumerate(mask):
                    if flag and s is None:
                        s = idx
                    if (not flag or idx == len(mask) - 1) and s is not None:
                        e = idx if not flag else idx
                        res.append((s, e))
                        s = None
                return res

            need1_di  = max(1, int((di_len[0]  + 1e-9) / mm_step))
            need2_di  = max(1, int((di_len[1]  + 1e-9) / mm_step))
            need3_di  = max(1, int((di_len[2]  + 1e-9) / mm_step))
            need1_due = max(1, int((due_len[0] + 1e-9) / mm_step))
            need2_due = max(1, int((due_len[1] + 1e-9) / mm_step))
            need3_due = max(1, int((due_len[2] + 1e-9) / mm_step))

            for i, seg in enumerate(segments):
                seg  = np.asarray(seg, dtype=float)
                base = -i * row_spacing

                # Dickstellen
                b1 = (seg >= (1.0 + di_pct[0]/100.0)*mean_all) & (seg < (1.0 + di_pct[1]/100.0)*mean_all)
                b2 = (seg >= (1.0 + di_pct[1]/100.0)*mean_all) & (seg < (1.0 + di_pct[2]/100.0)*mean_all)
                b3 = (seg >= (1.0 + di_pct[2]/100.0)*mean_all)
                for mask, row in ((b1, '1'), (b2, '2'), (b3, '3')):
                    for s, e in runs(mask):
                        L   = e - s + 1
                        if L < need1_di: continue
                        col = '1' if L < need2_di else '2' if L < need3_di else '3'
                        key = f"Di{row}{col}"
                        if not VISIBILITY_STATE.is_enabled(key): continue
                        xs    = x_mm[s:e+1]
                        y_top = base + seg[s:e+1] / 2.0
                        y_bot = base - seg[s:e+1] / 2.0
                        color = COLOR_STATE.di_colors.get(key, DI_COLORS.get(key))
                        self.ax.fill_between(xs, y_bot, y_top, color=color, alpha=0.9, linewidth=0)
                        spans_per_segment[i].append((float(x_mm[s]), float(x_mm[e] + mm_step), color))

                # Dünnstellen
                t1 = (seg <= (1.0 - due_pct[0]/100.0)*mean_all) & (seg > (1.0 - due_pct[1]/100.0)*mean_all)
                t2 = (seg <= (1.0 - due_pct[1]/100.0)*mean_all) & (seg > (1.0 - due_pct[2]/100.0)*mean_all)
                t3 = (seg <= (1.0 - due_pct[2]/100.0)*mean_all)
                for mask, row in ((t1, '1'), (t2, '2'), (t3, '3')):
                    for s, e in runs(mask):
                        L   = e - s + 1
                        if L < need1_due: continue
                        col = '1' if L < need2_due else '2' if L < need3_due else '3'
                        key = f"Dü{row}{col}"
                        if not VISIBILITY_STATE.is_enabled(key): continue
                        xs    = x_mm[s:e+1]
                        y_top = base + seg[s:e+1] / 2.0
                        y_bot = base - seg[s:e+1] / 2.0
                        color = COLOR_STATE.due_colors.get(key, DUE_COLORS.get(key))
                        self.ax.fill_between(xs, y_bot, y_top, color=color, alpha=0.9, linewidth=0)
                        spans_per_segment[i].append((float(x_mm[s]), float(x_mm[e] + mm_step), color))

        # Achsen & Limits
        self.ax.axis("off")
        self.ax.set_aspect("auto")
        self.ax.set_xmargin(0)
        self.ax.set_ymargin(0)
        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0)
        y_top_first   =  0               + np.max(segments[0])  / 2.0
        y_bottom_last = -(turns-1) * row_spacing - np.max(segments[-1]) / 2.0
        y_margin = 0.05 * global_max
        xlim = (0.0, SEGMENT_LEN_MM)
        ylim = (y_bottom_last - y_margin, y_top_first + y_margin)
        self.ax.set_xlim(*xlim)
        self.ax.set_ylim(*ylim)
        self.set_full_limits(xlim, ylim)
        self.draw_idle()
        try:
            self.spansComputed.emit(spans_per_segment)
        except Exception:
            pass

    def plot_garnspiegel_dty(
        # Zeichnet ein DTY-Garnspiegeldiagramm mit Knoten-Markierung und Otsu-Threshold.
        # Für die vollständige Signatur siehe den Funktionskörper.
        self,
        y_dev:      "np.ndarray",
        clip_um:    float,
        per_run:    list,
        class_fn,
        color_abc:  dict,
        color_open: str,
        dx_mm:      float = 0.25,
        y_um:       "np.ndarray | None" = None,
        num_turns:  int   = 10,
        gap_factor: float = 2.0,
    ):
        """
        Echter Garnspiegel: durchgehendes weisses Band, Breite = absolute Garndicke
        (normalisiert pro Segment auf Mittelwert). Knoten als farbige Einschnoerung.
        """
        import numpy as np

        self.ax.clear()
        self.figure.patch.set_facecolor("black")
        self.ax.set_facecolor("black")

        # Rohdaten: absolutes Signal in µm
        src = y_um if y_um is not None else (y_dev + np.mean(y_dev))
        n_total = len(src)
        if n_total == 0:
            self.draw_idle()
            return

        pts_per_row = max(1, int(round(SEGMENT_LEN_MM / dx_mm)))
        turns = max(1, min(int(num_turns), n_total // pts_per_row))
        use   = turns * pts_per_row

        seg_len_mm = pts_per_row * dx_mm
        x_mm  = np.linspace(0.0, seg_len_mm, pts_per_row, endpoint=False)

        # Globaler Mittelwert als Referenz fuer Zeilenabstand
        global_mean = float(np.mean(src[:use]))
        row_h = global_mean * gap_factor

        # Knoten-Maske + Klasse
        knot_mask  = np.zeros(use, dtype=bool)
        knot_class = np.full(use, "", dtype=object)
        for run in per_run:
            if not isinstance(run, (list, tuple)) or len(run) < 2:
                continue
            s, e = int(run[0]), int(run[1])
            if e <= s or s >= use:
                continue
            e = min(e, use)
            mv  = float(np.mean(src[s:e])) if e > s else 0.0
            cls = class_fn(mv)
            knot_mask[s:e]  = True
            knot_class[s:e] = cls

        for row in range(turns):
            s    = row * pts_per_row
            e    = s + pts_per_row
            seg  = src[s:e].copy()
            km   = knot_mask[s:e]
            kc   = knot_class[s:e]
            base = -row * row_h
            xr   = x_mm[:len(seg)]

            # Normalisierung: Segment-Mittelwert = 1.0
            seg_mean = float(np.mean(seg)) if len(seg) > 0 else global_mean
            seg_norm = seg / max(seg_mean, 1e-9)  # ~1.0 ueberall, Knoten etwas kleiner

            # Verstärkung der Variation fuer Sichtbarkeit
            # Abweichung vom 1.0 wird stark verstaerkt
            amp = 20.0
            seg_vis = 1.0 + (seg_norm - 1.0) * amp
            seg_vis = np.clip(seg_vis, 0.05, 3.0)

            half = seg_vis * global_mean * 0.12

            # Weisses Band (Oeffnungen)
            om = ~km
            self.ax.fill_between(xr,
                                 base - np.where(om, half, 0),
                                 base + np.where(om, half, 0),
                                 where=om[:len(xr)],
                                 color="white", alpha=0.88, linewidth=0)

            # Knoten: gleiches Band aber ABC-Farbe
            for cls_key, col in color_abc.items():
                cm = km & (kc == cls_key)
                if not np.any(cm):
                    continue
                self.ax.fill_between(xr,
                                     base - np.where(cm, half, 0),
                                     base + np.where(cm, half, 0),
                                     where=cm[:len(xr)],
                                     color=col, alpha=0.92, linewidth=0)

        self.ax.axis("off")
        self.ax.set_aspect("auto")
        self.ax.set_xmargin(0)
        self.ax.set_ymargin(0)
        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0)
        y_top = row_h * 0.5
        y_bot = -(turns - 1) * row_h - row_h * 0.5
        self.ax.set_xlim(0.0, seg_len_mm)
        self.ax.set_ylim(y_bot, y_top)
        self.set_full_limits((0.0, seg_len_mm), (y_bot, y_top))
        self.draw_idle()

    def plot_aty(
        self,
        data_mm_all: np.ndarray,
        spots: list,
        gap_factor: float = 2.0,
        num_turns: int = 10,
        row_spacing_ref: float | None = None,
    ):
        """Zeichnet ATY-Garnspiegel mit Bin-Einfärbung.

        Performance: Downsample auf 1000 Punkte/Segment, Spots als
        vorgefärbtes Array (2 fill_between pro Zeile statt 1 pro Spot).
        Bin 1 = Orange #ffcc88, Bin 2 = Blaugrün #88dddd.

        Args:
            row_spacing_ref: Optionale Referenz fuer row_spacing (globaler Max des
                             Gesamt-Arrays). Wie YarnScope _row_spacing_ref:
                             stellt sicher dass die Bandbreite bei verschiedenen
                             Startpunkten konstant bleibt.
        """
        self.ax.clear()
        self.figure.patch.set_facecolor("black")
        self.ax.set_facecolor("black")

        arr   = np.asarray(data_mm_all, dtype=float)
        turns = max(1, min(num_turns, NUM_TURNS))
        if arr.size < turns:
            self.draw_idle()
            return

        pts_per_seg = max(1, len(arr) // turns)
        global_max  = float(np.max(arr))
        # row_spacing_ref wie YarnScope: stabilisiert Bandbreite ueber alle Startpunkte
        ref         = float(row_spacing_ref) if row_spacing_ref is not None else global_max
        row_spacing = ref * float(gap_factor)

        # ── Downsample auf max. 1000 Punkte pro Segment ───────────────────────
        # Verhindert dass fill_between mit 200k Punkten blockiert.
        MAX_PTS = 1000
        if pts_per_seg > MAX_PTS:
            # Reshape + mean: schnellstes numpy-Downsample
            factor  = pts_per_seg // MAX_PTS
            n_use   = turns * (pts_per_seg // factor) * factor
            ds_pts  = pts_per_seg // factor
            arr_cut = arr[:n_use].reshape(turns, pts_per_seg // factor, factor).mean(axis=2)
            segs    = [arr_cut[i] for i in range(turns)]
            mm_per_orig = SEGMENT_LEN_MM / pts_per_seg          # mm pro Original-Punkt
            mm_per_ds   = SEGMENT_LEN_MM / ds_pts               # mm pro DS-Punkt
        else:
            ds_pts      = pts_per_seg
            segs        = list(np.split(arr[:pts_per_seg * turns], turns))
            mm_per_orig = SEGMENT_LEN_MM / pts_per_seg
            mm_per_ds   = mm_per_orig

        x_mm = np.linspace(0.0, SEGMENT_LEN_MM, ds_pts, endpoint=False)

        # ── Spot-Maske aufbauen: 0=kein Spot, 1=Bin1, 2=Bin2 ─────────────────
        # Je Segment ein Array der DS-Länge mit Bin-ID befüllen.
        # Ein Durchlauf über alle Spots, dann 2 fill_between pro Zeile.
        bin_masks = [np.zeros(ds_pts, dtype=np.int8) for _ in range(turns)]
        for sp in (spots or []):
            s_idx   = int(sp.get("start_idx", 0))
            n_pts   = int(sp.get("n_pts",     0))
            bin_id  = int(sp.get("F04_bin",   2))
            row     = s_idx // pts_per_seg
            if row >= turns:
                continue
            # Originalindex → DS-Index
            loc_s_ds = int((s_idx - row * pts_per_seg) / pts_per_seg * ds_pts)
            loc_e_ds = int(min(loc_s_ds + n_pts / pts_per_seg * ds_pts + 1, ds_pts))
            if loc_e_ds > loc_s_ds:
                bin_masks[row][loc_s_ds:loc_e_ds] = bin_id

        # ── Zeichnen ──────────────────────────────────────────────────────────
        for i, seg in enumerate(segs):
            seg  = np.asarray(seg, dtype=float)
            base = -i * row_spacing
            y_lo = base - seg / 2.0
            y_hi = base + seg / 2.0

            # Weisses Basisband
            self.ax.fill_between(x_mm, y_lo, y_hi, color="white", linewidth=0)

            # Bin-1-Spots (orange) – nur dort wo Maske == 1
            m1 = bin_masks[i] == 1
            if m1.any():
                y_lo1 = np.where(m1, y_lo, np.nan)
                y_hi1 = np.where(m1, y_hi, np.nan)
                self.ax.fill_between(x_mm, y_lo1, y_hi1,
                                     color="#ffcc88", alpha=0.9,
                                     linewidth=0, zorder=3)

            # Bin-2-Spots (blaugrün) – nur dort wo Maske == 2
            m2 = bin_masks[i] == 2
            if m2.any():
                y_lo2 = np.where(m2, y_lo, np.nan)
                y_hi2 = np.where(m2, y_hi, np.nan)
                self.ax.fill_between(x_mm, y_lo2, y_hi2,
                                     color="#88dddd", alpha=0.9,
                                     linewidth=0, zorder=3)

        # ── Achsen & Limits ───────────────────────────────────────────────────
        self.ax.axis("off")
        self.ax.set_aspect("auto")
        self.ax.set_xmargin(0)
        self.ax.set_ymargin(0)
        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0)
        y_top_first   = float(np.max(segs[0]))  / 2.0
        y_bottom_last = -(turns - 1) * row_spacing - float(np.max(segs[-1])) / 2.0
        xlim = (0.0, SEGMENT_LEN_MM)
        ylim = (y_bottom_last - 0.05 * global_max, y_top_first + 0.05 * global_max)
        self.ax.set_xlim(*xlim)
        self.ax.set_ylim(*ylim)
        self.set_full_limits(xlim, ylim)
        self.draw_idle()