from __future__ import annotations
from pathlib import Path
from ui.widgets.garn.file_browser import FileBrowserDialog
from PySide6.QtCore import Qt, Signal, QSize, QSettings
from PySide6 import QtCore, QtWidgets, QtGui
from core.db.connection import DEF_DIR
from typing import Dict
import re
import numpy as np
from PySide6.QtGui import QColor, QTextOption
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from nptdms import TdmsFile
from PySide6.QtCore import QObject
from PySide6.QtCore import Qt
DEF_DIR = Path.cwd()
DEFAULT_IMPORT_DIR = str(DEF_DIR)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
garngraf.py – TDMS-basiertes Garnspiegel-Panel (für ATY-Screen)

Änderungen:
- Tab-Leiste rechts bleibt fix; nur der Tab-Inhalt scrollt.
- Statistik-Block für Dick- und Dünnstellen mit fester Spaltenbreite (rechtebündig),
  sodass die drei Zeilen je Block immer am gleichen Ort starten.
- NEU: Tab "Graph" zeigt sortierte Differenzen (Messwert - Mittelwert) für die gesamte Serie in µm.

Features:
- Garnspiegel (10 × 200 mm) mit weisser Grundfläche.
- Dickstellen (Di11..Di33) und Dünnstellen (Dü11..Dü33) als farbige Overlays.
- Statistik, Matrix, Machine Data und Graph im **Tab-Layout** (QTabWidget).
- Globaler Farboverlay-Schalter wird vom ATY-Screen gesetzt.
- TDMS-Handling: nimmt ersten numerischen Kanal.

Hinweise:
- Di-Bänder (über Mittel): [1.1,1.2), [1.2,1.3), [>=1.3]
- Dü-Bänder (unter Mittel): (0.8,0.9], (0.7,0.8], [<=0.7]
- Längenbänder: [1,2), [2,3), [>=3] mm
"""


class FabricCanvas(QtWidgets.QWidget):
    """
    Canvas für das Fabric-Tab:
    - Schwarzer Hintergrund
    - 250 gleich dicke, horizontale, weisse Bänder
    - 2 Pixel Abstand zwischen den Bändern
    - NEU: farbige Overlays entlang x (Di/Dü) synchron zum Garnspiegel.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(False)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)
        # Farbbereiche je Segment: [(x0_mm, x1_mm, "#hex"), ...]
        self._spans = [[] for _ in range(250)]
        # X-Bereich in mm (Standard: 0..200)
        self._xrange_mm = (0.0, 200.0)
        # Interpretation: 1 Band entspricht 200 mm (= 0.2 m)
        self._band_len_m = 0.2
        # Anzahl Bänder mit echten Messdaten (Rest wird grau dargestellt)
        self._real_band_count = 0
    def set_band_count(self, n: int):
        """Setzt die Anzahl Bänder im Fabric-Tab (min 50, max 500)."""
        try:
            n = int(n)
        except Exception:
            return
        n = max(1, min(500, n))
        if n == getattr(self, '_band_count', n):
            self.update()
            return
        self._band_count = n
        # Spans auf neue Länge bringen
        cur = list(getattr(self, '_spans', []))
        if len(cur) < n:
            cur.extend([[] for _ in range(n - len(cur))])
        self._spans = cur[:n]
        self.update()


    def set_color_spans(self, spans_per_segment, x_range_mm=(0.0, 200.0), real_count: int | None = None):
        """Übernimmt Farbbalken (x0/x1 in mm, Farbe) je Band vom Garnspiegel.
        Synchronisiert dabei die Bandanzahl mit der übergebenen Liste, damit beim Verkleinern
        wirklich weniger Bänder gezeichnet werden.
        real_count: Anzahl Bänder mit echten Messdaten; der Rest wird grau dargestellt.
        """
        try:
            inferred = int(len(spans_per_segment)) if spans_per_segment is not None else 0
        except Exception:
            inferred = 0
        if 1 <= inferred <= 500:
            n = inferred
        else:
            n = max(50, min(500, int(getattr(self, '_band_count', 250))))
        self._band_count = n
        fixed = [spans_per_segment[i] if (spans_per_segment is not None and i < len(spans_per_segment)) else [] for i in range(n)]
        self._spans = [list(seg) for seg in fixed]
        self._xrange_mm = tuple(x_range_mm)
        self._real_band_count = int(real_count) if real_count is not None else n
        self.update()

    def minimumSizeHint(self):
        # Pro Band mind. 1px + 2px Gap → Canvas muss ScrollArea enthalten können
        n = max(1, getattr(self, '_band_count', 250))
        min_h = n * 1 + (n - 1) * 2  # 1px Band + 2px Gap
        return QtCore.QSize(200, min_h)

        def zigzag_length_cm(self, width_cm: float = 20.0) -> float:
            """
                Berechnet die Länge einer einzigen Zickzack-Linie in cm,
                wenn die gesamte nutzbare Breite (inner) 'width_cm' entspricht.
                """
            rect = self.rect()
            W = max(1, rect.width())
            H = max(1, rect.height())
            pad = max(8, int(0.02 * min(W, H)))
            inner_w = max(1.0, W - 2 * pad)
            inner_h = max(1.0, H - 2 * pad)

            rows = max(1, self.rows)
            row_spacing = inner_h / rows
            A = min(0.6 * row_spacing, 0.55 * row_spacing)

            cycles = max(10, int(inner_w / 18))
            pts_per_cycle = 2
            total_pts = cycles * pts_per_cycle + 1
            dx = inner_w / (total_pts - 1)

            N = (total_pts - 1)
            seg_len = math.hypot(dx, 2 * A)
            total_len_px = N * seg_len

            px_to_cm = width_cm / inner_w
            return total_len_px * px_to_cm

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)

        # Schwarzer Hintergrund
        painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0))

        # Parameter
        w = self.width()
        h = self.height()
        n = max(1, len(self._spans))
        # Gap dynamisch reduzieren, damit pro Band mind. 1 px übrig bleibt
        gap = 2
        while gap > 0 and (gap * (n - 1)) > (h - n):
            gap -= 1
        total_gap = gap * (n - 1)
        band_h = (h - total_gap) / float(n) if n else 1.0
        total_height = (band_h * n) + total_gap
        start_y = (h - total_height) / 2.0  # vertikal zentrieren
        painter.setPen(QtCore.Qt.NoPen)

        x0_mm, x1_mm = self._xrange_mm
        xspan = max(1e-9, (x1_mm - x0_mm))

        y0 = float(start_y)
        real_n = int(getattr(self, '_real_band_count', n))
        for i in range(n):
            # y-Positionen sauber runden, damit die Fläche bestmöglich genutzt wird
            y_top = y0 + i * (band_h + gap)
            y_bot = y_top + band_h
            yi0 = int(round(y_top))
            yi1 = int(round(y_bot))
            bh = max(1, yi1 - yi0)

            # Basisband: weiss bei echten Daten, grau bei fehlenden
            base_color = QtGui.QColor(255, 255, 255) if i < real_n else QtGui.QColor(160, 160, 160)
            painter.setBrush(QtGui.QBrush(base_color))
            painter.drawRect(0, yi0, w, bh)

            # Farboverlays (Di/Dü) nur bei echten Bändern
            if i >= real_n:
                continue
            spans = self._spans[i] if i < len(self._spans) else []
            for (sx_mm, ex_mm, hexcol) in spans:
                sx = max(x0_mm, min(ex_mm, sx_mm))
                ex = min(x1_mm, max(sx_mm, ex_mm))
                if ex <= sx:
                    continue
                px0 = int(round((sx - x0_mm) / xspan * w))
                px1 = int(round((ex - x0_mm) / xspan * w))
                if px1 <= px0:
                    continue
                painter.setBrush(QtGui.QBrush(QtGui.QColor(hexcol)))
                painter.drawRect(px0, yi0, px1 - px0, bh)
class MachineDataTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._trial_series_id = None
        self._trial_id = None
        self._machine_name = None
        self._jet_name = None

        self._lbl_title = QtWidgets.QLabel("Machine Data")
        self._lbl_title.setStyleSheet("font-weight: 600; font-size: 16px;")

        row_trialseries = QtWidgets.QHBoxLayout()
        row_trialseries.addWidget(QtWidgets.QLabel("TrialSeries:"))
        self._lbl_id = QtWidgets.QLabel("–")
        self._lbl_id.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row_trialseries.addWidget(self._lbl_id, 1)

        row_exp = QtWidgets.QHBoxLayout()
        row_exp.addWidget(QtWidgets.QLabel("TrialSeries:"))
        self._lbl_exp = QtWidgets.QLabel("–")
        self._lbl_exp.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row_exp.addWidget(self._lbl_exp, 1)

        row_trial = QtWidgets.QHBoxLayout()
        row_trial.addWidget(QtWidgets.QLabel("Versuchsnummer:"))
        self._lbl_trial = QtWidgets.QLabel("–")
        self._lbl_trial.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row_trial.addWidget(self._lbl_trial, 1)

        row_machine = QtWidgets.QHBoxLayout()
        row_machine.addWidget(QtWidgets.QLabel("Machine:"))
        self._lbl_machine = QtWidgets.QLabel("–")
        self._lbl_machine.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row_machine.addWidget(self._lbl_machine, 1)

        row_jet = QtWidgets.QHBoxLayout()
        row_jet.addWidget(QtWidgets.QLabel("Jet:"))
        self._lbl_jet = QtWidgets.QLabel("–")
        self._lbl_jet.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row_jet.addWidget(self._lbl_jet, 1)

        row_air = QtWidgets.QHBoxLayout()
        row_air.addWidget(QtWidgets.QLabel("Luftdruck:"))
        self._lbl_air = QtWidgets.QLabel("–")
        self._lbl_air.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row_air.addWidget(self._lbl_air, 1)

        row_speed = QtWidgets.QHBoxLayout()
        row_speed.addWidget(QtWidgets.QLabel("Geschwindigkeit:"))
        self._lbl_speed = QtWidgets.QLabel("–")
        self._lbl_speed.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row_speed.addWidget(self._lbl_speed, 1)

        row_mat_title = QtWidgets.QHBoxLayout()
        row_mat_title.addWidget(QtWidgets.QLabel("Material:"))

        self._lbl_materials = QtWidgets.QLabel("–")
        self._lbl_materials.setTextFormat(Qt.PlainText)
        self._lbl_materials.setWordWrap(True)
        self._lbl_materials.setTextInteractionFlags(Qt.TextSelectableByMouse)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)
        lay.addWidget(self._lbl_title)
        # lay.addLayout(row_trialseries)  # removed on request: hide TrialSeries row completely
        lay.addLayout(row_exp)
        lay.addLayout(row_trial)
        lay.addLayout(row_machine)
        lay.addLayout(row_jet)
        lay.addLayout(row_air)
        lay.addLayout(row_speed)
        row_of_core = QtWidgets.QHBoxLayout()
        row_of_core.addWidget(QtWidgets.QLabel("OF% Core:"))
        self._lbl_of_core = QtWidgets.QLabel("–")
        self._lbl_of_core.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row_of_core.addWidget(self._lbl_of_core, 1)
        row_of_effect = QtWidgets.QHBoxLayout()
        row_of_effect.addWidget(QtWidgets.QLabel("OF% Effect:"))
        self._lbl_of_effect = QtWidgets.QLabel("–")
        self._lbl_of_effect.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row_of_effect.addWidget(self._lbl_of_effect, 1)
        lay.addLayout(row_of_core)
        lay.addLayout(row_of_effect)
        lay.addLayout(row_mat_title)
        lay.addWidget(self._lbl_materials)
        lay.addStretch(1)

    def set_trial_series_id(self, ts_id):
        self._trial_series_id = ts_id
        self._lbl_id.setText(ts_id if isinstance(ts_id, str) else (
            f"{ts_id}" if ts_id is not None else "–"))

    def set_trial_id(self, trial_id):
        self._trial_id = trial_id
        self._lbl_trial.setText((f"V{int(trial_id)}" if isinstance(trial_id, (int, float)) or (isinstance(
            trial_id, str) and trial_id.isdigit()) else (trial_id if isinstance(trial_id, str) else '–')))

    def set_machine_name(self, name: str | None):
        self._machine_name = name
        self._lbl_machine.setText(name if name else "–")

    def set_jet_name(self, name: str | None):
        self._jet_name = name
        self._lbl_jet.setText(name if name else "–")

    def set_air_pressure(self, val):
        # Expects float or string; show as '5.0 bar'
        txt = None
        try:
            if val is not None and val != "":
                f = float(val)
                txt = f"{f:.1f} bar"
        except Exception:
            txt = None
        self._lbl_air.setText(txt if txt else "–")

    def set_speed(self, val):
        # Expects float or string; show as '123 m/min'
        txt = None
        try:
            if val is not None and val != "":
                f = float(val)
                txt = f"{f:.0f} m/min"
        except Exception:
            txt = None
        self._lbl_speed.setText(txt if txt else "–")

    def set_of_core(self, val):
        # Format as '12.0%'
        txt = None
        try:
            if val is not None and val != "":
                f = float(val)
                txt = f"{f:.1f}%"
        except Exception:
            txt = None
        self._lbl_of_core.setText(txt if txt else "–")

    def set_of_effect(self, val):
        # Format as '12.0%'
        txt = None
        try:
            if val is not None and val != "":
                f = float(val)
                txt = f"{f:.1f}%"
        except Exception:
            txt = None
        self._lbl_of_effect.setText(txt if txt else "–")

    def set_materials(self, items):
        if items:
            text = "\n".join(f"• {s}" for s in items)
            self._lbl_materials.setText(text)
        else:
            self._lbl_materials.setText("–")

    def set_experiment_id(self, value):
        self._lbl_exp.setText(value if value else "nothing found")


# DB fetch helper (nutzt Projekt-Connection; Fallback: leer)
try:
    from core.db.connection import fetch_all  # yarnscope project path
except Exception:
    try:
        from yarnscope.core.db.connection import fetch_all  # alternative package path
    except Exception:
        def fetch_all(sql, params=None):
            return []


class _SyncHub(QObject):
    # Broadcasts fractional limits from any panel to all others
    broadcast = Signal(object, tuple, tuple)
    # Broadcast common full Y-limits so all panels share the same Y scale
    yfull = Signal(object, tuple)
    # Broadcast reference thickness (global_max) used for row spacing
    yref = Signal(object, float)
    # NEW: broadcast threshold changes (global for all panels)
    thresholds = Signal(object, dict)


SYNC_HUB = _SyncHub()

# ------------------ Konstanten ------------------
MM_PER_POINT = 0.25
SEGMENT_LEN_MM = 200.0
POINTS_PER_SEGMENT = int(SEGMENT_LEN_MM / MM_PER_POINT)  # 800
NUM_TURNS = 10
TOTAL_LEN_MM = NUM_TURNS * SEGMENT_LEN_MM                # 2000 mm
NEEDED_POINTS = NUM_TURNS * POINTS_PER_SEGMENT           # 8000

DEFAULT_GAP_FACTOR = 2.0
SUPPORTED_EXTS = {".tdms"}
TESTDATA_DIR = (Path(__file__).resolve().parent / "testdata").resolve()

# Farben
DI_COLORS = {
    "Di11": "#ffd1e6", "Di12": "#ffb3d1", "Di13": "#ff94bd",
    "Di21": "#ff7aa9", "Di22": "#ff5c94", "Di23": "#ff3d80",
    "Di31": "#ff1f6b", "Di32": "#e60057", "Di33": "#b30045",
}
DUE_COLORS = {
    "Dü11": "#d6ecff", "Dü12": "#b9e0ff", "Dü13": "#9cd4ff",
    "Dü21": "#7fc8ff", "Dü22": "#62bbff", "Dü23": "#45afff",
    "Dü31": "#279fff", "Dü32": "#0f87e6", "Dü33": "#065da8",
}

# Per default: immer mit Standardfarben starten (gespeicherte Farben beim Start ignorieren)
LOAD_SAVED_COLORS_ON_START = False
# --- Laufzeit-fähige Farbstate (persistiert via QSettings) ---


class _ColorState(QObject):
    colorsChanged = Signal()

    def __init__(self):
        super().__init__()
        self._settings = QSettings('YarnScope', 'ATY')
        # Start mit Defaults
        self.di_colors = dict(DI_COLORS)
        self.due_colors = dict(DUE_COLORS)
        # Geladene Werte überschreiben (nur wenn Flag aktiv)
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
        # family: 'Di' oder 'Dü'
        try:
            if family == 'Di':
                self.di_colors[key] = hex_color
                self._settings.setValue(f"colors/Di/{key}", hex_color)
            else:
                self.due_colors[key] = hex_color
                self._settings.setValue(f"colors/Due/{key}", hex_color)
            self.colorsChanged.emit()
        except Exception:
            pass


COLOR_STATE = _ColorState()

# --- Sichtbarkeits-Status (Checkboxen je Klasse) ---


class _VisibilityState(QtCore.QObject):
    visibilityChanged = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self._settings = QSettings('YarnScope', 'ATY')
        # Default: alles sichtbar
        self.enabled = {k: True for k in [
            'Di11', 'Di12', 'Di13', 'Di21', 'Di22', 'Di23', 'Di31', 'Di32', 'Di33',
            'Dü11', 'Dü12', 'Dü13', 'Dü21', 'Dü22', 'Dü23', 'Dü31', 'Dü32', 'Dü33'
        ]}
        # Laden aus Settings
        try:
            for k in list(self.enabled.keys()):
                val = self._settings.value(f"visible/{k}", type=str)
                if val is not None:
                    self.enabled[k] = (str(val).lower() != "false")
        except Exception:
            pass

    def set_enabled(self, key: str, on: bool):
        try:
            self.enabled[key] = bool(on)
            self._settings.setValue(
                f"visible/{key}", "true" if on else "false")
            self.visibilityChanged.emit()
        except Exception:
            pass

    def is_enabled(self, key: str) -> bool:
        return self.enabled.get(key, True)


VISIBILITY_STATE = _VisibilityState()

# --- Laufzeit-Globale Schwellenwerte (in-memory, für alle Panels) ---
CLASS_THRESHOLDS = {
    "Di": {"pct": [10.0, 20.0, 30.0], "mm": [1.0, 2.0, 3.0]},
    "Dü": {"pct": [10.0, 20.0, 30.0], "mm": [1.0, 2.0, 3.0]},
}

# ------------------ TDMS-Helpers ------------------


def _read_first_numeric_tdms_channel(path: Path) -> np.ndarray | None:
    tdms = TdmsFile.read(str(path))
    for grp in tdms.groups():
        for ch in grp.channels():
            try:
                arr = np.asarray(ch[:])
                if arr.size > 0 and np.issubdtype(arr.dtype, np.number):
                    return np.asarray(arr, dtype=float)
            except Exception:
                continue
    return None


def _normalize_key(s: str) -> str:
    # lower, strip accents if any, remove everything except letters/digits
    s = str(s).casefold()
    return re.sub(r"[^a-z0-9]+", "", s)


def _try_parse_mm(value, unit_hint: str | None = None):
    # returns value in mm if possible
    if value is None:
        return None
    # numeric straight
    if isinstance(value, (int, float)):
        v = float(value)
        # if unit hint says 'm' (meters), convert
        if unit_hint and unit_hint.strip().lower() in {"m", "meter", "meters"}:
            return v * 1000.0
        return v
    s = str(value).strip()
    s = s.replace(",", ".")
    # pick unit suffix if present
    unit = None
    m = re.search(r"([\-+]?\d+(?:\.\d+)?)\s*([a-zµμ/]*)$",
                  s, flags=re.IGNORECASE)
    if m:
        num = m.group(1)
        unit = (m.group(2) or "").lower()
        try:
            v = float(num)
        except Exception:
            return None
        if unit in {"mm", "millimeter", "millimetre"}:
            return v
        if unit in {"m", "meter", "metre"}:
            return v * 1000.0
        # no/unknown unit
        return v
    # plain float string
    try:
        return float(s)
    except Exception:
        return None


def _read_messabstand_mm_from_tdms(path: Path) -> float | None:
    """
    Liest den Messabstand (mm) aus einer TDMS-Datei.
    1) Prüft File/Group/Channel-Properties
    2) **Neu:** Erkennt Tabellen-Channels 'Parameter' / 'Wert' / 'Einheit' und liest dort die Zeile 'Messabstand' aus.
    3) Fallback: versucht Berechnung aus Geschwindigkeit (m/min) und Messfrequenz (Hz), falls beides vorhanden.
    """
    try:
        tdms = TdmsFile.read(str(path))
    except Exception:
        return None

    # ---------- 1) Properties (wie vorher) ----------
    all_props = []
    try:
        for k, v in (tdms.properties or {}).items():
            all_props.append(("file", str(k), v))
    except Exception:
        pass
    try:
        for grp in tdms.groups():
            for k, v in (getattr(grp, 'properties', {}) or {}).items():
                all_props.append(
                    (f"group:{getattr(grp, 'name', '?')}", str(k), v))
            for ch in grp.channels():
                for k, v in (getattr(ch, 'properties', {}) or {}).items():
                    all_props.append(
                        (f"chan:{getattr(grp, 'name', '?')}/{getattr(ch, 'name', '?')}", str(k), v))
    except Exception:
        pass

    try:
        if all_props:
            preview = ", ".join(
                [f"{scope}:{key}" for scope, key, _ in all_props[:80]])
            print(
                f"[garngraf] TDMS Properties gefunden ({len(all_props)}): {preview}")
        else:
            print(f"[garngraf] TDMS Properties gefunden (0)")
    except Exception:
        pass

    candidates = [
        "messabstand", "messabstandmm", "schrittweite", "abstand",
        "step", "stepmm", "deltax", "dx", "samplespacing", "sampledistance", "spacing", "increment"
    ]

    for scope, key, val in all_props:
        nk = _normalize_key(key)
        for cand in candidates:
            if cand in nk:
                parsed = _try_parse_mm(val)
                if parsed is not None:
                    return float(parsed)

    # ---------- 2) Tabellen-Channels 'Parameter'/'Wert'/'Einheit' ----------
    try:
        for grp in tdms.groups():
            # Kanal finden, Namen können leicht variieren (Gross-/Kleinschreibung)
            ch_param = None
            ch_wert = None
            ch_einh = None
            for ch in grp.channels():
                nkn = _normalize_key(ch.name)
                if nkn == "parameter":
                    ch_param = ch
                elif nkn in {"wert", "value", "values"}:
                    ch_wert = ch
                elif nkn in {"einheit", "einheiten", "unit", "units"}:
                    ch_einh = ch
            if ch_param is None or ch_wert is None:
                continue

            params = [str(x).strip() for x in ch_param[:]]
            werte = list(ch_wert[:])
            einhs = list(ch_einh[:]) if ch_einh is not None else [
                None]*len(werte)
            n = min(len(params), len(werte), len(einhs))

            # Fuzzy-Zeilen-Suche
            for i in range(n):
                key_norm = _normalize_key(params[i])
                if any(cand in key_norm for cand in ["messabstand", "schrittweite", "samplespacing", "deltax", "dx", "abstand"]):
                    val = werte[i]
                    unit_hint = str(einhs[i]).strip().lower() if i < len(
                        einhs) and einhs[i] is not None else None
                    parsed = _try_parse_mm(val, unit_hint=unit_hint)
                    if parsed is not None:
                        print(
                            f"[garngraf] Messabstand aus Tabellen-Channels: {parsed:g} mm (Gruppe='{grp.name}', Zeile={i})")
                        return float(parsed)

            # Falls in den Tabellen auch 'Geschwindigkeit' & 'Messfrequenz' stehen → merken
    except Exception as e:
        try:
            print(
                f"[garngraf] Lesen der Tabellen-Channels fehlgeschlagen: {e}")
        except Exception:
            pass

    # ---------- 3) Fallback aus Geschwindigkeit/Frequenz ----------
    speed_mm_per_s = None
    freq_hz = None

    # a) evtl. über Properties
    for _, key, val in all_props:
        nk = _normalize_key(key)
        # Geschwindigkeit (m/min)
        if any(tok in nk for tok in ("geschwindigkeit", "speed")) and speed_mm_per_s is None:
            s = str(val).replace(",", ".")
            try:
                num = float(_re.findall(r"[-+]?\d+(?:\.\d+)?", s)[0])
                if "m/min" in s.lower() or "mpermin" in s.lower():
                    speed_mm_per_s = (num * 1000.0) / 60.0
                else:
                    # konservativ: annehmen bereits mm/s
                    speed_mm_per_s = num
            except Exception:
                pass
        # Frequenz (Hz)
        if any(tok in nk for tok in ("messfrequenz", "samplingrate", "frequenz", "hz", "freq")) and freq_hz is None:
            try:
                freq_hz = float(str(val).replace(",", "."))
            except Exception:
                pass

    # b) evtl. über Tabellen-Channels
    try:
        for grp in tdms.groups():
            lookup = {}
            # Map von Parameter -> (wert, einheit)
            chp = None
            chw = None
            che = None
            for ch in grp.channels():
                nkn = _normalize_key(ch.name)
                if nkn == "parameter":
                    chp = ch
                elif nkn in {"wert", "value", "values"}:
                    chw = ch
                elif nkn in {"einheit", "einheiten", "unit", "units"}:
                    che = ch
            if chp is None or chw is None:
                continue
            params = [str(x).strip() for x in chp[:]]
            werte = list(chw[:])
            einhs = list(che[:]) if che is not None else [None]*len(werte)
            for i in range(min(len(params), len(werte))):
                lookup[_normalize_key(params[i])] = (werte[i], (str(einhs[i]).strip(
                ).lower() if i < len(einhs) and einhs[i] is not None else None))
            # Geschwindigkeit W2 o.ä.
            for k in list(lookup.keys()):
                if "geschwindigkeit" in k or "speed" in k:
                    v, u = lookup[k]
                    # meistens m/min
                    try:
                        num = float(str(v).replace(",", "."))
                        if (u and "m/min" in u) or "m/min" in str(v).lower():
                            speed_mm_per_s = (num * 1000.0) / 60.0
                        else:
                            # annehmen mm/s
                            speed_mm_per_s = num
                    except Exception:
                        pass
                if "messfrequenz" in k or "samplingrate" in k or "frequenz" in k or k.endswith("hz"):
                    v, u = lookup[k]
                    try:
                        freq_hz = float(str(v).replace(",", "."))
                    except Exception:
                        pass
    except Exception:
        pass

    if speed_mm_per_s is not None and freq_hz:
        mm = speed_mm_per_s / freq_hz
        try:
            print(
                f"[garngraf] Messabstand berechnet (Tabellen/Props): {mm:g} mm")
        except Exception:
            pass
        return float(mm)

    return None

    # Collect properties
    all_props = []  # list of (scope, key, value)
    # file-level
    try:
        for k, v in (tdms.properties or {}).items():
            all_props.append(("file", str(k), v))
    except Exception:
        pass
    # groups + channels
    try:
        for grp in tdms.groups():
            for k, v in (getattr(grp, 'properties', {}) or {}).items():
                all_props.append(
                    (f"group:{getattr(grp, 'name', '?')}", str(k), v))
            for ch in grp.channels():
                for k, v in (getattr(ch, 'properties', {}) or {}).items():
                    all_props.append(
                        (f"chan:{getattr(grp, 'name', '?')}/{getattr(ch, 'name', '?')}", str(k), v))
    except Exception:
        pass

    # Debug print of keys (first 200 keys max)
    try:
        if all_props:
            preview = ", ".join(
                [f"{scope}:{key}" for scope, key, _ in all_props[:200]])
            print(
                f"[garngraf] TDMS Properties gefunden ({len(all_props)}): {preview}")
    except Exception:
        pass

    # Preferred key fragments (normalized)
    candidates = [
        "messabstand", "messabstandmm", "messabstandprojekt", "schrittweite", "abstand",
        "step", "stepmm", "deltax", "dx", "samplespacing", "sampledistance", "spacing", "increment"
    ]

    # Direct search
    for scope, key, val in all_props:
        nk = _normalize_key(key)
        for cand in candidates:
            if cand in nk:
                parsed = _try_parse_mm(val)
                if parsed is not None:
                    return float(parsed)

    # Units sometimes stored separately as "Einheit" alongside a value key
    # Attempt to pair "... Einheit" keys.
    # Map: base_key -> unit
    unit_map = {}
    for scope, key, val in all_props:
        nk = _normalize_key(key)
        if any(tok in nk for tok in ("einheit", "unit", "units")):
            base = nk.replace("einheit", "").replace(
                "unit", "").replace("units", "")
            unit_map[base] = str(val).strip().lower()
    for scope, key, val in all_props:
        nk = _normalize_key(key)
        for cand in candidates:
            if cand in nk:
                unit_hint = unit_map.get(nk, None)
                parsed = _try_parse_mm(val, unit_hint=unit_hint)
                if parsed is not None:
                    return float(parsed)

    # Fallback: compute from speed (m/min) and frequency (Hz)
    speed = None
    freq = None
    for _, key, val in all_props:
        nk = _normalize_key(key)
        if any(tok in nk for tok in ("geschwindigkeit", "speed", "v")) and speed is None:
            speed = _try_parse_mm(val)  # might read in mm already; detect unit
            # If value looks like m/min (common), parse via text:
            s = str(val).lower()
            if "m/min" in s or "m pro min" in s or "mpermin" in s:
                # convert meters/min to mm/s
                try:
                    num = float(re.findall(
                        r"[\-+]?\d+(?:\.\d+)?", s.replace(",", "."))[0])
                    speed = (num * 1000.0) / 60.0  # mm/s
                except Exception:
                    pass
        if any(tok in nk for tok in ("messfrequenz", "frequenz", "samplingrate", "hz", "freq")) and freq is None:
            try:
                freq = float(str(val).replace(",", "."))
            except Exception:
                pass
    # Another try: if speed appeared as plain number and a unit key tells it's m/min
    if speed is not None and speed > 100:  # heuristic: probably mm/s already; if too big, assume m/min and convert
        pass
    if speed is not None and freq:
        # If speed looks like mm/s (typical thousands), assume already mm/s.
        mm_per_sample = (speed / freq)
        try:
            print(
                f"[garngraf] Messabstand berechnet aus Geschwindigkeit/Frequenz: {mm_per_sample:g} mm (speed={speed}, freq={freq})")
        except Exception:
            pass
        return float(mm_per_sample)

    return None

    def _parse_value(v):
        # akzeptiert float/int oder Strings wie '0.5', '0.5 mm'
        if v is None:
            return None
        try:
            if isinstance(v, (int, float)):
                return float(v)
            s = str(v).strip().replace(',', '.')
            # Einheiten entfernen
            s = re.sub(r"\s*(mm|millimeter)\s*$", "", s, flags=re.IGNORECASE)
            return float(s)
        except Exception:
            return None

    key_candidates = {
        "messabstand", "messabstand_mm", "mess_abstand", "abstand",
        "step", "step_mm", "delta_x", "dx", "sample_spacing", "sample_spacing_mm"
    }

    # 1) Datei-Properties
    try:
        for k, v in (tdms.properties or {}).items():
            if str(k).strip().casefold() in key_candidates:
                val = _parse_value(v)
                if val is not None:
                    return float(val)
    except Exception:
        pass

    # 2) Gruppen- und Kanal-Properties
    try:
        for grp in tdms.groups():
            for k, v in (getattr(grp, 'properties', {}) or {}).items():
                if str(k).strip().casefold() in key_candidates:
                    val = _parse_value(v)
                    if val is not None:
                        return float(val)
            for ch in grp.channels():
                for k, v in (getattr(ch, 'properties', {}) or {}).items():
                    if str(k).strip().casefold() in key_candidates:
                        val = _parse_value(v)
                        if val is not None:
                            return float(val)
    except Exception:
        pass

    # 3) Nichts gefunden
    return None

# ------------------ Klassifizierer ------------------


def _classify_dickstellen_3x3(arr_mm: np.ndarray,
                              mm_per_point: float,
                              mean_factor_edges=(1.1, 1.2, 1.3),
                              length_edges_mm=(1.0, 2.0, 3.0)) -> Dict[str, int]:
    n = arr_mm.size
    res = {f"Di{r}{c}": 0 for r in (1, 2, 3) for c in (1, 2, 3)}
    if n == 0:
        return res
    mean_mm = float(np.mean(arr_mm))
    if not np.isfinite(mean_mm) or mean_mm <= 0:
        return res
    f1, f2, f3 = mean_factor_edges
    band1 = (arr_mm >= f1*mean_mm) & (arr_mm < f2*mean_mm)
    band2 = (arr_mm >= f2*mean_mm) & (arr_mm < f3*mean_mm)
    band3 = (arr_mm >= f3*mean_mm)
    need1 = max(1, int(np.ceil(length_edges_mm[0] / mm_per_point)))
    need2 = max(1, int(np.ceil(length_edges_mm[1] / mm_per_point)))
    need3 = max(1, int(np.ceil(length_edges_mm[2] / mm_per_point)))

    def count(mask, row):
        i = 0
        while i < n:
            if mask[i]:
                j = i
                while j < n and mask[j]:
                    j += 1
                L = j-i
                if L >= need1:
                    key = f"Di{row}" + \
                        ("1" if L < need2 else "2" if L < need3 else "3")
                    res[key] += 1
                i = j
            else:
                i += 1
    count(band1, 1)
    count(band2, 2)
    count(band3, 3)
    return res


def _classify_duennstellen_3x3(arr_mm: np.ndarray,
                               mm_per_point: float,
                               mean_factor_edges=(0.9, 0.8, 0.7),
                               length_edges_mm=(1.0, 2.0, 3.0)) -> Dict[str, int]:
    n = arr_mm.size
    res = {f"Dü{r}{c}": 0 for r in (1, 2, 3) for c in (1, 2, 3)}
    if n == 0:
        return res
    mean_mm = float(np.mean(arr_mm))
    if not np.isfinite(mean_mm) or mean_mm <= 0:
        return res
    g1, g2, g3 = mean_factor_edges
    band1 = (arr_mm <= g1*mean_mm) & (arr_mm > g2*mean_mm)   # (0.8,0.9]
    band2 = (arr_mm <= g2*mean_mm) & (arr_mm > g3*mean_mm)   # (0.7,0.8]
    band3 = (arr_mm <= g3*mean_mm)                            # [<=0.7]
    need1 = max(1, int(np.ceil(length_edges_mm[0] / mm_per_point)))
    need2 = max(1, int(np.ceil(length_edges_mm[1] / mm_per_point)))
    need3 = max(1, int(np.ceil(length_edges_mm[2] / mm_per_point)))

    def count(mask, row):
        i = 0
        while i < n:
            if mask[i]:
                j = i
                while j < n and mask[j]:
                    j += 1
                L = j-i
                if L >= need1:
                    key = f"Dü{row}" + \
                        ("1" if L < need2 else "2" if L < need3 else "3")
                    res[key] += 1
                i = j
            else:
                i += 1
    count(band1, 1)
    count(band2, 2)
    count(band3, 3)
    return res


def _normalize_counts_per_100m(counts: Dict[str, int], total_length_mm: float) -> Dict[str, float]:
    if total_length_mm <= 0:
        return {k: float('nan') for k in counts}
    f = 100000.0 / total_length_mm
    return {k: v * f for k, v in counts.items()}


def _fmt_thousands_ch(v: float) -> str:
    import numpy as _np
    if v is None or (isinstance(v, float) and not _np.isfinite(v)):
        return "–"
    try:
        s = f"{v:,.2f}"
        return s.replace(",", "'")
    except Exception:
        return str(v)


def compute_hai(y_um_array, k: float = 1.0, q: float = 1.0) -> float:
    """
    Robuster, dimensionsloser Heberlein ATY Index (HAI).
    - y_um_array: Dicke in µm (volle Serie)
    - k: Schwelle in "σ-Einheiten" relativ zur robusten Skala (MAD-basiert), deckt dein σ-Faktor ab
    - q: Exzess-Potenz; q=1 linear, q>1 bestraft starke Ausreisser stärker
    Definition:
      1) z-Standardisierung mit Median/MAD: z_i = (y_i - Median)/s, s = 1.4826*MAD
      2) Exzess: E_i = max(|z_i| - k, 0)   (oder ((|z_i|/k)^q - 1) für q≠1)
      3) p = Anteil(|z_i|>k)
      4) HAI = 100 * p * mean(E_i)
    """
    import numpy as _np
    y = _np.asarray(y_um_array).astype(float)
    if y.size == 0:
        return 0.0
    med = float(_np.median(y))
    mad = float(_np.median(_np.abs(y - med)))
    if mad > 0:
        s = 1.4826 * mad
    else:
        # Fallback auf Std, sonst 1.0 (verhindert Division durch 0)
        s = float(_np.std(y, ddof=1)) if y.size > 1 else 1.0
        if s == 0.0:
            s = 1.0
    z = (y - med) / s
    mask = _np.abs(z) > float(k)
    if not _np.any(mask):
        return 0.0
    if q == 1.0:
        excess = _np.abs(z[mask]) - float(k)
    else:
        excess = ((_np.abs(z[mask]) / float(k)) ** float(q)) - 1.0
    p_out = float(_np.mean(mask))
    mean_excess = float(_np.mean(excess)) if excess.size else 0.0
    hai = 100.0 * p_out * mean_excess
    return float(max(hai, 0.0))

# ------------------ Canvas ------------------


class GarnCanvas(FigureCanvas):
    limitsChanged = Signal(tuple, tuple)
    # Spans (x0_mm, x1_mm, '#hex') je Segment für Fabric
    spansComputed = Signal(list)

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
        self.mpl_connect('draw_event', self._on_draw)
        self.mpl_connect('scroll_event', self._on_scroll)
        self.ax.callbacks.connect('xlim_changed', self._on_limits_changed)
        self.ax.callbacks.connect('ylim_changed', self._on_limits_changed)

    def _maybe_emit_if_changed(self):
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
        if event.inaxes != self.ax:
            return
        scale = 1.15 if event.button == 'up' else (
            1/1.15 if event.button == 'down' else 1.0)
        if scale == 1.0:
            return
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        cx, cy = event.xdata, event.ydata
        if cx is None or cy is None:
            return

        def zoom(l0, l1, c, s):
            span = (l1-l0)
            new_span = span/s
            lf = (c-l0)/span if span else 0.5
            nl0 = c-new_span*lf
            nl1 = nl0+new_span
            return nl0, nl1
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
        self.full_xlim = tuple(xlim)
        self.full_ylim = tuple(ylim)
        self._last_xlim = tuple(xlim)
        self._last_ylim = tuple(ylim)

    def apply_fractional_limits(self, frac_xlim, frac_ylim):
        fx0, fx1 = self.full_xlim
        fy0, fy1 = self.full_ylim
        w = fx1-fx0
        h = fy1-fy0
        rx0, rx1 = frac_xlim
        ry0, ry1 = frac_ylim
        nx0 = fx0+rx0*w
        nx1 = fx0+rx1*w
        ny0 = fy0+ry0*h
        ny1 = fy0+ry1*h
        self._suppress_emit = True
        self.ax.set_xlim(nx0, nx1)
        self.ax.set_ylim(ny0, ny1)
        self.figure.canvas.draw_idle()
        self._suppress_emit = False
        self._last_xlim, self._last_ylim = (nx0, nx1), (ny0, ny1)

    def full_view(self):
        self._suppress_emit = True
        self.ax.set_xlim(*self.full_xlim)
        self.ax.set_ylim(*self.full_ylim)
        self.figure.canvas.draw_idle()
        self._suppress_emit = False
        self._last_xlim, self._last_ylim = self.full_xlim, self.full_ylim

    def plot_garnspiegel(self, data_mm_all: np.ndarray, gap_factor: float = DEFAULT_GAP_FACTOR, show_colors: bool = True, row_spacing_ref: float | None = None, num_turns: int | None = None):
        self.ax.clear()
        self.figure.patch.set_facecolor("black")
        self.ax.set_facecolor("black")
        # Dynamische Anzahl Linien (bei kurzen Dateien weniger als 10)
        turns = int(num_turns) if num_turns is not None else NUM_TURNS
        turns = max(1, min(NUM_TURNS, turns))
        if data_mm_all is None or len(data_mm_all) < turns:
            self.draw_idle()
            return
        points_per_segment = max(1, len(data_mm_all) // turns)
        segments = np.split(
            data_mm_all[:points_per_segment*turns], turns)
        mm_step = SEGMENT_LEN_MM / \
            float(points_per_segment) if points_per_segment > 0 else MM_PER_POINT
        global_max = float(np.max(data_mm_all))
        row_spacing_base = float(row_spacing_ref) if (
            row_spacing_ref is not None) else global_max
        row_spacing = row_spacing_base*float(gap_factor)
        x_mm = np.linspace(0.0, SEGMENT_LEN_MM,
                           points_per_segment, endpoint=False)

        # Weiss
        for i, seg in enumerate(segments):
            seg = np.asarray(seg, dtype=float)
            base = -i*row_spacing
            y_top = base+seg/2.0
            y_bottom = base-seg/2.0
            self.ax.fill_between(x_mm, y_bottom, y_top,
                                 color="white", linewidth=0)

        spans_per_segment = [[] for _ in range(turns)]
        if show_colors:
            mean_all = float(np.mean(data_mm_all))
            di_pct = CLASS_THRESHOLDS["Di"]["pct"]
            due_pct = CLASS_THRESHOLDS["Dü"]["pct"]
            di_len = CLASS_THRESHOLDS["Di"]["mm"]
            due_len = CLASS_THRESHOLDS["Dü"]["mm"]

            def runs(mask):
                res = []
                s = None
                for idx, flag in enumerate(mask):
                    if flag and s is None:
                        s = idx
                    if (not flag or idx == len(mask)-1) and s is not None:
                        e = idx if not flag else idx
                        res.append((s, e))
                        s = None
                return res

            need1_di = max(1, int((di_len[0] + 1e-9)/mm_step))
            need2_di = max(1, int((di_len[1] + 1e-9)/mm_step))
            need3_di = max(1, int((di_len[2] + 1e-9)/mm_step))
            need1_due = max(1, int((due_len[0] + 1e-9)/mm_step))
            need2_due = max(1, int((due_len[1] + 1e-9)/mm_step))
            need3_due = max(1, int((due_len[2] + 1e-9)/mm_step))

            for i, seg in enumerate(segments):
                seg = np.asarray(seg, dtype=float)
                base = -i*row_spacing
                # Dickstellen
                b1 = (seg >= (
                    1.0 + di_pct[0]/100.0)*mean_all) & (seg < (1.0 + di_pct[1]/100.0)*mean_all)
                b2 = (seg >= (
                    1.0 + di_pct[1]/100.0)*mean_all) & (seg < (1.0 + di_pct[2]/100.0)*mean_all)
                b3 = (seg >= (1.0 + di_pct[2]/100.0)*mean_all)
                for mask, row in ((b1, '1'), (b2, '2'), (b3, '3')):
                    for s, e in runs(mask):
                        L = e-s+1
                        if L < need1_di:
                            continue
                        col = '1' if L < need2_di else '2' if L < need3_di else '3'
                        key = f"Di{row}{col}"
                        if not VISIBILITY_STATE.is_enabled(key):
                            continue
                        xs = x_mm[s:e+1]
                        y_top = base+seg[s:e+1]/2.0
                        y_bottom = base-seg[s:e+1]/2.0
                        color = COLOR_STATE.di_colors.get(
                            key, DI_COLORS.get(key))
                        self.ax.fill_between(
                            xs, y_bottom, y_top, color=color, alpha=0.9, linewidth=0)
                        x0 = float(x_mm[s])
                        x1 = float(x_mm[e] + mm_step)
                        spans_per_segment[i].append((x0, x1, color))
                # Dünnstellen
                t1 = (seg <= (
                    1.0 - due_pct[0]/100.0)*mean_all) & (seg > (1.0 - due_pct[1]/100.0)*mean_all)
                t2 = (seg <= (
                    1.0 - due_pct[1]/100.0)*mean_all) & (seg > (1.0 - due_pct[2]/100.0)*mean_all)
                t3 = (seg <= (1.0 - due_pct[2]/100.0)*mean_all)
                for mask, row in ((t1, '1'), (t2, '2'), (t3, '3')):
                    for s, e in runs(mask):
                        L = e-s+1
                        if L < need1_due:
                            continue
                        col = '1' if L < need2_due else '2' if L < need3_due else '3'
                        key = f"Dü{row}{col}"
                        if not VISIBILITY_STATE.is_enabled(key):
                            continue
                        xs = x_mm[s:e+1]
                        y_top = base+seg[s:e+1]/2.0
                        y_bottom = base-seg[s:e+1]/2.0
                        color = COLOR_STATE.due_colors.get(
                            key, DUE_COLORS.get(key))
                        self.ax.fill_between(
                            xs, y_bottom, y_top, color=color, alpha=0.9, linewidth=0)
                        x0 = float(x_mm[s])
                        x1 = float(x_mm[e] + mm_step)
                        spans_per_segment[i].append((x0, x1, color))

        # Achsen und Limits
        self.ax.axis("off")
        self.ax.set_aspect("auto")
        self.ax.set_xmargin(0)
        self.ax.set_ymargin(0)
        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0)
        y_top_first = 0 + np.max(segments[0]) / 2.0
        y_bottom_last = -(turns-1)*row_spacing - np.max(segments[-1])/2.0
        y_margin = 0.05*global_max
        xlim = (0.0, SEGMENT_LEN_MM)
        ylim = (y_bottom_last-y_margin, y_top_first+y_margin)
        self.ax.set_xlim(*xlim)
        self.ax.set_ylim(*ylim)
        self.set_full_limits(xlim, ylim)
        self.draw_idle()

        # Spans an Fabric senden
        try:
            self.spansComputed.emit(spans_per_segment)
        except Exception:
            pass


class GarnPanel(QtWidgets.QGroupBox):

    def _update_knitted_info_label(self):
        """Aktualisiert die kleine Statusanzeige für das Knitted-Tab.

        Fix: 1 Reihe = 40 cm (0.4 m)

        Neu:
        - Wenn zu wenig Daten vorhanden sind, wird automatisch nur das maximal mögliche angezeigt
          (statt immer z.B. 100 m).
        """
        try:
            if not hasattr(self, 'knitted_info') or self.knitted_info is None:
                return

            requested = int(self.knitted_spin.value()) if hasattr(self, 'knitted_spin') else 50
            requested = max(1, min(250, requested))

            # Verfügbare Reihen aus Datenlänge (ab aktuellem Start)
            src = getattr(self, 'series_mm_full', None)
            start_pts = int(getattr(self, 'current_start_points', 0))
            mm_step = float(self._mm_step())
            points_per_row = max(1, int(round(400.0 / max(1e-9, mm_step))))

            available_rows = None
            if src is not None and len(src) > start_pts:
                available_rows = int((len(src) - start_pts) // points_per_row)
                available_rows = max(0, available_rows)

            effective = requested
            if available_rows is not None:
                effective = max(0, min(requested, available_rows))

                # Range dynamisch anpassen
                try:
                    self.knitted_spin.blockSignals(True)
                    self.knitted_spin.setRange(1, max(1, min(250, max(1, available_rows))))
                    if requested != effective:
                        self.knitted_spin.setValue(max(1, effective) if effective > 0 else 1)
                    self.knitted_spin.blockSignals(False)
                except Exception:
                    try:
                        self.knitted_spin.blockSignals(False)
                    except Exception:
                        pass

            total_m = effective * 0.4
            if abs(total_m - round(total_m)) < 1e-9:
                total_txt = f"{int(round(total_m))} m"
            else:
                total_txt = f"{total_m:.1f} m"

            self.knitted_info.setText(f"Anzeige: {effective} Reihen × 40 cm = {total_txt} yarn")
        except Exception:
            pass

    def _update_knitted_from_series(self):
        """Rechnet Farboverlays für das Knitted-Tab (Reihenzahl wählbar, 50..250).

        Fixe Interpretation:
        - 1 Reihe = 400 mm (40 cm)
        - X-Achse bleibt (0..200 mm) synchron zum Garnspiegel.
        """
        try:
            self._update_knitted_info_label()
            # Canvas evtl. noch nicht vorhanden
            if not hasattr(self, 'knitted_canvas') or self.knitted_canvas is None:
                return

            # Reihen-Anzahl aus UI (oder Default)
            rows_needed = int(self.knitted_spin.value()) if hasattr(self, 'knitted_spin') else 50
            rows_needed = max(1, min(250, rows_needed))

            try:
                self.knitted_canvas.set_row_count(rows_needed)
            except Exception:
                pass

            src = getattr(self, 'series_mm_full', None)
            start_pts = int(getattr(self, 'current_start_points', 0))
            if src is None:
                try:
                    self.knitted_canvas.update()
                except Exception:
                    pass
                return

            # 1 Reihe = 400 mm
            row_len_mm = 400.0
            mm_step = float(self._mm_step())
            points_per_row = max(1, int(round(row_len_mm / max(1e-9, mm_step))))

            total_needed = rows_needed * points_per_row
            end_pts = min(start_pts + total_needed, len(src))
            knitted_slice = src[start_pts:end_pts]

            rows = []
            if knitted_slice.size >= points_per_row:
                usable = knitted_slice[: (knitted_slice.size // points_per_row) * points_per_row]
                rows = list(np.split(usable, len(usable) // points_per_row))

            def _runs(mask):
                res, s = [], None
                for idx, flag in enumerate(mask):
                    if flag and s is None:
                        s = idx
                    if (not flag or idx == len(mask)-1) and s is not None:
                        e = idx if not flag else idx
                        res.append((s, e))
                        s = None
                return res

            spans_per_row = []
            di_pct = CLASS_THRESHOLDS["Di"]["pct"]
            due_pct = CLASS_THRESHOLDS["Dü"]["pct"]
            di_len = CLASS_THRESHOLDS["Di"]["mm"]
            due_len = CLASS_THRESHOLDS["Dü"]["mm"]
            need1_di = max(1, int((di_len[0] + 1e-9)/mm_step))
            need2_di = max(1, int((di_len[1] + 1e-9)/mm_step))
            need3_di = max(1, int((di_len[2] + 1e-9)/mm_step))
            need1_due = max(1, int((due_len[0] + 1e-9)/mm_step))
            need2_due = max(1, int((due_len[1] + 1e-9)/mm_step))
            need3_due = max(1, int((due_len[2] + 1e-9)/mm_step))

            mean_all = float(np.mean(knitted_slice)) if knitted_slice.size else 0.0
            # X-Achse (Garnspiegel) bleibt 0..200 mm
            x_mm = np.linspace(0.0, SEGMENT_LEN_MM, points_per_row, endpoint=False)

            for seg in rows[:rows_needed]:
                seg = np.asarray(seg, dtype=float)
                seg_spans = []

                # Dickstellen
                b1 = (seg >= (1.0 + di_pct[0]/100.0)*mean_all) & (seg < (1.0 + di_pct[1]/100.0)*mean_all)
                b2 = (seg >= (1.0 + di_pct[1]/100.0)*mean_all) & (seg < (1.0 + di_pct[2]/100.0)*mean_all)
                b3 = (seg >= (1.0 + di_pct[2]/100.0)*mean_all)
                for mask, row in ((b1, '1'), (b2, '2'), (b3, '3')):
                    for s, e in _runs(mask):
                        L = e - s + 1
                        if L < need1_di:
                            continue
                        col = '1' if L < need2_di else '2' if L < need3_di else '3'
                        key = f"Di{row}{col}"
                        if not VISIBILITY_STATE.is_enabled(key):
                            continue
                        color = COLOR_STATE.di_colors.get(key, DI_COLORS.get(key))
                        x0 = float(x_mm[s])
                        x1 = float(x_mm[e] + mm_step)
                        seg_spans.append((x0, x1, color))

                # Dünnstellen
                t1 = (seg <= (1.0 - due_pct[0]/100.0)*mean_all) & (seg > (1.0 - due_pct[1]/100.0)*mean_all)
                t2 = (seg <= (1.0 - due_pct[1]/100.0)*mean_all) & (seg > (1.0 - due_pct[2]/100.0)*mean_all)
                t3 = (seg <= (1.0 - due_pct[2]/100.0)*mean_all)
                for mask, row in ((t1, '1'), (t2, '2'), (t3, '3')):
                    for s, e in _runs(mask):
                        L = e - s + 1
                        if L < need1_due:
                            continue
                        col = '1' if L < need2_due else '2' if L < need3_due else '3'
                        key = f"Dü{row}{col}"
                        if not VISIBILITY_STATE.is_enabled(key):
                            continue
                        color = COLOR_STATE.due_colors.get(key, DUE_COLORS.get(key))
                        x0 = float(x_mm[s])
                        x1 = float(x_mm[e] + mm_step)
                        seg_spans.append((x0, x1, color))

                spans_per_row.append(seg_spans)

            while len(spans_per_row) < rows_needed:
                spans_per_row.append([])

            self.knitted_canvas.set_row_count(rows_needed)
            self.knitted_canvas.set_color_spans(spans_per_row[:rows_needed], (0.0, 200.0), row_len_mm)
        except Exception:
            pass


    def _update_fabric_info_label(self):
        """Aktualisiert die kleine Statusanzeige für das Fabric-Tab.

        Fix: 1 Band = 20 cm (0.2 m)

        Neu:
        - Bei zu kurzen Dateien wird nur das maximal mögliche angezeigt.
        """
        try:
            if not hasattr(self, 'fabric_info') or self.fabric_info is None:
                return

            requested = int(self.fabric_spin.value()) if hasattr(self, 'fabric_spin') else 250
            requested = max(1, min(500, requested))

            src = getattr(self, 'series_mm_full', None)
            start_pts = int(getattr(self, 'current_start_points', 0))
            points_per_band = max(1, int(round(SEGMENT_LEN_MM / max(1e-9, float(self._mm_step())))))

            available_bands = None
            if src is not None and len(src) > start_pts:
                available_bands = int((len(src) - start_pts) // points_per_band)
                available_bands = max(0, available_bands)

            effective = requested
            if available_bands is not None:
                effective = max(0, min(requested, available_bands))

                try:
                    self.fabric_spin.blockSignals(True)
                    self.fabric_spin.setRange(1, max(1, min(500, max(1, available_bands))))
                    if requested != effective:
                        self.fabric_spin.setValue(max(1, effective) if effective > 0 else 1)
                    self.fabric_spin.blockSignals(False)
                except Exception:
                    try:
                        self.fabric_spin.blockSignals(False)
                    except Exception:
                        pass

            total_m = effective * 0.2
            if abs(total_m - round(total_m)) < 1e-9:
                total_txt = f"{int(round(total_m))} m"
            else:
                total_txt = f"{total_m:.1f} m"

            self.fabric_info.setText(f"Display: {effective} bands × 20 cm = {total_txt} yarn")
        except Exception:
            pass

    def _update_fabric_from_series(self):
        """Rechnet Farboverlays für das Fabric-Tab (Bandzahl wählbar), ab aktuellem Start."""
        try:
            self._update_fabric_info_label()
            points_per_segment = max(
                1, int(round(SEGMENT_LEN_MM / self._mm_step())))
            segs_needed = int(self.fabric_spin.value()) if hasattr(self, 'fabric_spin') else 250
            segs_needed = max(1, min(500, segs_needed))
            start_pts = int(getattr(self, "current_start_points", 0))
            src = getattr(self, "series_mm_full", None)
            # Band-Anzahl sofort anwenden (auch wenn noch keine Daten geladen sind)
            try:
                self.fabric_canvas.set_band_count(segs_needed)
            except Exception:
                pass
            if src is None:
                # trotzdem redraw (leere Bänder)
                try:
                    self.fabric_canvas.update()
                except Exception:
                    pass
                return
            total_needed = segs_needed * points_per_segment
            end_pts = min(start_pts + total_needed, len(src))
            fabric_slice = src[start_pts:end_pts]

            segs = []
            if fabric_slice.size >= points_per_segment:
                usable = fabric_slice[: (
                    fabric_slice.size // points_per_segment) * points_per_segment]
                segs = list(np.split(usable, len(
                    usable) // points_per_segment))

            def _runs(mask):
                res, s = [], None
                for idx, flag in enumerate(mask):
                    if flag and s is None:
                        s = idx
                    if (not flag or idx == len(mask)-1) and s is not None:
                        e = idx if not flag else idx
                        res.append((s, e))
                        s = None
                return res

            spans30 = []
            mm_step = SEGMENT_LEN_MM / \
                float(points_per_segment) if points_per_segment > 0 else self._mm_step()
            di_pct = CLASS_THRESHOLDS["Di"]["pct"]
            due_pct = CLASS_THRESHOLDS["Dü"]["pct"]
            di_len = CLASS_THRESHOLDS["Di"]["mm"]
            due_len = CLASS_THRESHOLDS["Dü"]["mm"]
            need1_di = max(1, int((di_len[0] + 1e-9)/mm_step))
            need2_di = max(1, int((di_len[1] + 1e-9)/mm_step))
            need3_di = max(1, int((di_len[2] + 1e-9)/mm_step))
            need1_due = max(1, int((due_len[0] + 1e-9)/mm_step))
            need2_due = max(1, int((due_len[1] + 1e-9)/mm_step))
            need3_due = max(1, int((due_len[2] + 1e-9)/mm_step))

            mean_all = float(np.mean(fabric_slice)
                             ) if fabric_slice.size else 0.0
            x_mm = np.linspace(0.0, SEGMENT_LEN_MM,
                               points_per_segment, endpoint=False)

            for seg in segs[:segs_needed]:
                seg = np.asarray(seg, dtype=float)
                seg_spans = []
                # Dickstellen
                b1 = (seg >= (
                    1.0 + di_pct[0]/100.0)*mean_all) & (seg < (1.0 + di_pct[1]/100.0)*mean_all)
                b2 = (seg >= (
                    1.0 + di_pct[1]/100.0)*mean_all) & (seg < (1.0 + di_pct[2]/100.0)*mean_all)
                b3 = (seg >= (1.0 + di_pct[2]/100.0)*mean_all)
                for mask, row in ((b1, '1'), (b2, '2'), (b3, '3')):
                    for s, e in _runs(mask):
                        L = e - s + 1
                        if L < need1_di:
                            continue
                        col = '1' if L < need2_di else '2' if L < need3_di else '3'
                        key = f"Di{row}{col}"
                        if not VISIBILITY_STATE.is_enabled(key):
                            continue
                        color = COLOR_STATE.di_colors.get(
                            key, DI_COLORS.get(key))
                        x0 = float(x_mm[s])
                        x1 = float(x_mm[e] + mm_step)
                        seg_spans.append((x0, x1, color))
                # Dünnstellen
                t1 = (seg <= (
                    1.0 - due_pct[0]/100.0)*mean_all) & (seg > (1.0 - due_pct[1]/100.0)*mean_all)
                t2 = (seg <= (
                    1.0 - due_pct[1]/100.0)*mean_all) & (seg > (1.0 - due_pct[2]/100.0)*mean_all)
                t3 = (seg <= (1.0 - due_pct[2]/100.0)*mean_all)
                for mask, row in ((t1, '1'), (t2, '2'), (t3, '3')):
                    for s, e in _runs(mask):
                        L = e - s + 1
                        if L < need1_due:
                            continue
                        col = '1' if L < need2_due else '2' if L < need3_due else '3'
                        key = f"Dü{row}{col}"
                        if not VISIBILITY_STATE.is_enabled(key):
                            continue
                        color = COLOR_STATE.due_colors.get(
                            key, DUE_COLORS.get(key))
                        x0 = float(x_mm[s])
                        x1 = float(x_mm[e] + mm_step)
                        seg_spans.append((x0, x1, color))
                spans30.append(seg_spans)

            while len(spans30) < segs_needed:
                spans30.append([])

            self.fabric_canvas.set_band_count(segs_needed)
            self.fabric_canvas.set_color_spans(
                spans30[:segs_needed], (0.0, 200.0), real_count=len(segs))
        except Exception:
            pass
    limitsFractionChanged = Signal(object, tuple, tuple)
    _instance_counter = 0

    def __init__(self, title="Garnspiegel", parent=None):
        super().__init__(title, parent)
        # --- Sync-Setup ---
        GarnPanel._instance_counter += 1
        self._sync_id = GarnPanel._instance_counter
        self._applying_sync = False
        # Receive broadcasts from other panels
        SYNC_HUB.broadcast.connect(self._on_sync_broadcast)
        SYNC_HUB.yfull.connect(self._on_yfull_broadcast)
        SYNC_HUB.yref.connect(self._on_yref_broadcast)

        # Daten
        self.series_um: np.ndarray | None = None
        self.series_mm_full: np.ndarray | None = None
        self.total_points = 0
        self.max_start_points = 0
        self.current_start_points = 0
        self.data_mm_current: np.ndarray | None = None
        self.color_overlay_enabled: bool = True
        self._pending_changes: bool = False
        # σ-Faktor für Kernband/Exzess
        self.sigma_factor: float = 1.0
        self.mm_per_point_tdms: float | None = None
        # shared row spacing reference (global thickness max across panels)
        self._row_spacing_ref: float | None = None

        # Zielordner aus Einstellungen oder Default laden
        try:
            _settings = QSettings('YarnScope', 'ATY')
            self.import_dir = _settings.value(
                'import_dir', DEFAULT_IMPORT_DIR, type=str)
        except Exception:
            self.import_dir = DEFAULT_IMPORT_DIR
        outer = QtWidgets.QVBoxLayout(self)
        outer.setSpacing(6)
        outer.setContentsMargins(6, 6, 6, 6)

        # Dateizeile
        file_row = QtWidgets.QHBoxLayout()
        file_row.setSpacing(6)
        self.lbl_file = QtWidgets.QLabel("— no file —")
        self.lbl_file.setMinimumWidth(300)
        self.lbl_file.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.lbl_dataset_info = QtWidgets.QLabel("–")
        self.lbl_dataset_info.setStyleSheet("color: #888;")
        self.lbl_dataset_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.btn_load = QtWidgets.QPushButton("Load data")
        self.btn_load.clicked.connect(self.load_data)
        file_row.addWidget(QtWidgets.QLabel("testdata:"))
        file_row.addWidget(self.lbl_file, 4)
        file_row.addSpacing(12)
        file_row.addWidget(self.lbl_dataset_info, 0)
        file_row.addStretch(1)
        self.btn_load_folder = QtWidgets.QPushButton("Load folder…")
        self.btn_load_folder.setToolTip(
            "Select and load file from target folder")
        self.btn_load_folder.clicked.connect(self.open_file_browser_dialog)
        file_row.addWidget(self.btn_load_folder)
        file_row.addSpacing(6)
        file_row.addWidget(self.btn_load)
        outer.addLayout(file_row)

        # Steuerzeile
        ctl_row = QtWidgets.QHBoxLayout()
        ctl_row.setSpacing(6)
        self.canvas = GarnCanvas(self)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setIconSize(QSize(16, 16))
        try:
            self.toolbar.coordinates.setVisible(False)
        except Exception:
            pass
        self.slider = QtWidgets.QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.setSingleStep(1)
        self.slider.setPageStep(100)
        self.slider.setTracking(False)
        self.slider.sliderReleased.connect(
            lambda: self.on_slider_changed(self.slider.value()))
        self.mm_spin = QtWidgets.QDoubleSpinBox()
        self.mm_spin.setDecimals(2)
        self.mm_spin.setSingleStep(MM_PER_POINT)
        self.mm_spin.setRange(0.0, 0.0)
        self.mm_spin.setKeyboardTracking(False)
        self.mm_spin.editingFinished.connect(self.on_mm_changed)
        self.gap_spin = QtWidgets.QDoubleSpinBox()
        self.gap_spin.setVisible(False)
        self.gap_spin.setDecimals(2)
        self.gap_spin.setRange(0.5, 20.0)
        self.gap_spin.setSingleStep(0.25)
        self.gap_spin.setValue(DEFAULT_GAP_FACTOR)
        self.gap_spin.setKeyboardTracking(False)
        self.gap_spin.editingFinished.connect(self.update_plot_only)
        ctl_row.addWidget(self.toolbar, 0)
        ctl_row.addSpacing(6)
        ctl_row.addWidget(self.slider, 3)
        right_grp = QtWidgets.QHBoxLayout()
        right_grp.setSpacing(6)
        right_grp.addWidget(QtWidgets.QLabel("Start [mm]:"))
        right_grp.addWidget(self.mm_spin)
        right_grp.addSpacing(10)
        self._lbl_gap = QtWidgets.QLabel("GAP-Faktor:")
        self._lbl_gap.setVisible(False)
        right_grp.addWidget(self._lbl_gap)
        right_grp.addWidget(self.gap_spin)
        right_grp.addSpacing(10)
        right_grp.addWidget(QtWidgets.QLabel("σ-Faktor:"))
        self.sigma_spin = QtWidgets.QDoubleSpinBox()
        self.sigma_spin.setDecimals(2)
        self.sigma_spin.setRange(0.05, 3.0)
        self.sigma_spin.setSingleStep(0.05)
        self.sigma_spin.setValue(getattr(self, 'sigma_factor', 1.0))
        right_grp.addWidget(self.sigma_spin)
        # trigger only on focus-out / Enter
        self.sigma_spin.setKeyboardTracking(False)
        self.sigma_spin.editingFinished.connect(
            lambda: (setattr(self, 'sigma_factor', float(self.sigma_spin.value())),
                     self.recompute_and_plot() if hasattr(self, 'recompute_and_plot') else self.update_plot_only())
        )
        self.sigma_go = QtWidgets.QPushButton("Go")
        self.sigma_go.setFixedWidth(40)
        self.sigma_go.clicked.connect(lambda: (setattr(self, 'sigma_factor', float(self.sigma_spin.value(
        ))), self.recompute_and_plot() if hasattr(self, 'recompute_and_plot') else self.update_plot_only()))
        right_grp.addWidget(self.sigma_go)

        # Fabric: Anzahl Bänder (50..500) => 10..100 m bei 200 mm/Band
        right_grp.addSpacing(10)
        right_grp.addWidget(QtWidgets.QLabel('Fabric bands à 0.2m:'))
        self.fabric_spin = QtWidgets.QSpinBox()
        self.fabric_spin.setRange(50, 500)
        self.fabric_spin.setSingleStep(10)
        self.fabric_spin.setValue(250)
        # Wichtig: Update bei Fokusverlust (LineEdit) UND bei Klick auf Pfeile
        self.fabric_spin.setKeyboardTracking(False)
        try:
            self.fabric_spin.lineEdit().editingFinished.connect(self._update_fabric_from_series)
        except Exception:
            pass
        self.fabric_spin.editingFinished.connect(self._update_fabric_from_series)
        self.fabric_spin.valueChanged.connect(lambda _v: self._update_fabric_from_series())
        right_grp.addWidget(self.fabric_spin)

        # kleine Statusanzeige (Fabric)
        self.fabric_info = QtWidgets.QLabel()
        self.fabric_info.setObjectName("fabricInfo")
        self.fabric_info.setStyleSheet("color: #666; font-size: 11px;")
        self.fabric_info.setMinimumWidth(240)
        right_grp.addWidget(self.fabric_info)
        self._update_fabric_info_label()

        # Knitted: Anzahl Reihen (50..250), 1 Reihe = 0.4 m
        right_grp.addSpacing(10)
        right_grp.addWidget(QtWidgets.QLabel('Knitted Reihen à 0.4m:'))
        self.knitted_spin = QtWidgets.QSpinBox()
        self.knitted_spin.setRange(50, 250)
        self.knitted_spin.setSingleStep(10)
        self.knitted_spin.setValue(50)
        self.knitted_spin.setKeyboardTracking(False)
        try:
            self.knitted_spin.lineEdit().editingFinished.connect(self._update_knitted_from_series)
        except Exception:
            pass
        self.knitted_spin.editingFinished.connect(self._update_knitted_from_series)
        self.knitted_spin.valueChanged.connect(lambda _v: self._update_knitted_from_series())
        right_grp.addWidget(self.knitted_spin)

        # kleine Statusanzeige (Knitted)
        self.knitted_info = QtWidgets.QLabel()
        self.knitted_info.setObjectName("knittedInfo")
        self.knitted_info.setStyleSheet("color: #666; font-size: 11px;")
        self.knitted_info.setMinimumWidth(260)
        right_grp.addWidget(self.knitted_info)
        self._update_knitted_info_label()


        right_container = QtWidgets.QWidget()
        right_container.setLayout(right_grp)
        right_container.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        ctl_row.addWidget(right_container, 0, Qt.AlignRight)
        outer.addLayout(ctl_row)

        # Inhalt (links Plot, rechts Tabs)
        content_row = QtWidgets.QHBoxLayout()
        content_row.setSpacing(6)
        left_col = QtWidgets.QVBoxLayout()
        left_col.setSpacing(4)
        # Linke Tabs: Garnspiegel + Fabric

        self.left_tabs = QtWidgets.QTabWidget()

        # Tab: Garnspiegel (enthält die bestehende Canvas)

        self.garnspiegel_tab = QtWidgets.QWidget()

        gs_layout = QtWidgets.QVBoxLayout(self.garnspiegel_tab)

        gs_layout.setContentsMargins(0, 0, 0, 0)

        gs_layout.setSpacing(4)

        gs_layout.addWidget(self.canvas, 1)

        self.left_tabs.addTab(self.garnspiegel_tab, "Garnspiegel")

        # Tab: Fabric (vorerst leer)

        self.fabric_tab_left = QtWidgets.QWidget()

        fabric_layout = QtWidgets.QVBoxLayout(self.fabric_tab_left)

        fabric_layout.setContentsMargins(0, 0, 0, 0)

        fabric_layout.setSpacing(4)

        # Fabric-Canvas mit schwarzem Hintergrund und 10 gleich dicken weissen Bändern (Gap 2 px)

        self.fabric_canvas = FabricCanvas(self.fabric_tab_left)

        fabric_scroll = QtWidgets.QScrollArea()
        fabric_scroll.setWidget(self.fabric_canvas)
        fabric_scroll.setWidgetResizable(True)
        fabric_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        fabric_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        fabric_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        fabric_layout.addWidget(fabric_scroll, 1)

        self.left_tabs.addTab(self.fabric_tab_left, "Fabric")

        # Farbsync: Spans vom Garnspiegel an Fabric weiterreichen
        try:
            self.canvas.spansComputed.connect(
                lambda _spans: (self._update_fabric_from_series(), self._update_knitted_from_series()))
        except Exception:
            pass

        # --- Knitted Tab (schwarzer Hintergrund; 20 weisse Wellen; steile Stäbchen, flache Köpfe; Peaks ausgerichtet) ---
        try:
            self.knitted_tab_left = QtWidgets.QWidget()
            self.knitted_tab_left.setStyleSheet("background-color: black;")
            knitted_layout = QtWidgets.QVBoxLayout(self.knitted_tab_left)
            knitted_layout.setContentsMargins(0, 0, 0, 0)
            knitted_layout.setSpacing(0)

            class KnittedCanvas(QtWidgets.QWidget):
                """
                Weiss auf schwarz; 50 Reihen als Zickzack. 
                Aktive Dick-/Dünnstellen werden farbig übermalt (analog Tab "Fabric").
                1 Reihe = 400 mm.
                """

                def __init__(self, parent=None, rows=50):
                    super().__init__(parent)
                    self.rows = max(50, min(250, int(rows)))
                    self._spans = [[] for _ in range(self.rows)]
                    self._xrange_mm = (0.0, 200.0)
                    self._row_len_mm = 400.0
                    self.setAutoFillBackground(False)
                    self.setSizePolicy(
                        QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

                def set_row_count(self, n: int):
                    """Setzt die Anzahl Reihen (min 50, max 250) und triggert Redraw."""
                    try:
                        n = int(n)
                    except Exception:
                        return
                    n = max(1, min(250, n))
                    if n == getattr(self, 'rows', n):
                        self.update()
                        return
                    self.rows = n
                    cur = list(getattr(self, '_spans', []))
                    if len(cur) < n:
                        cur.extend([[] for _ in range(n - len(cur))])
                    self._spans = cur[:n]
                    self.update()

                def set_color_spans(self, spans_per_row, x_range_mm=(0.0, 200.0), row_len_mm=400.0):
                    n = max(1, int(getattr(self, 'rows', 50)))
                    fixed = [spans_per_row[i] if (spans_per_row is not None and i < len(spans_per_row)) else [] for i in range(n)]
                    self._spans = [list(seg) for seg in fixed]
                    self._xrange_mm = tuple(x_range_mm)
                    self._row_len_mm = float(row_len_mm)
                    self.update()

                def minimumSizeHint(self):
                    return QtCore.QSize(200, 200)

                def _row_points(self, inner_rect, row_index):
                    rows = max(1, self.rows)
                    row_spacing = inner_rect.height() / rows
                    A = min(0.6 * row_spacing, 0.55 * row_spacing)
                    W = inner_rect.width()
                    total_pts = max(20, int(self._row_len_mm)) + 1
                    dx = W / (total_pts - 1)
                    y_mid = inner_rect.top() + (row_index + 0.5) * row_spacing
                    y_top = y_mid - A
                    y_bot = y_mid + A
                    start_top = (row_index % 2 == 0)
                    xs = [inner_rect.left() + i * dx for i in range(total_pts)]
                    ys = []
                    flip = start_top
                    for _ in range(total_pts):
                        ys.append(y_bot if flip else y_top)
                        flip = not flip
                    return xs, ys

                def paintEvent(self, event):
                    p = QtGui.QPainter(self)
                    p.setRenderHint(QtGui.QPainter.Antialiasing, True)
                    rect = self.rect()
                    p.fillRect(rect, QtGui.QColor(0, 0, 0))

                    W = max(1, rect.width())
                    H = max(1, rect.height())
                    pad = max(8, int(0.02 * min(W, H)))
                    inner = QtCore.QRectF(pad, pad, W - 2 * pad, H - 2 * pad)

                    base_pen = QtGui.QPen(QtGui.QColor(255, 255, 255))
                    base_pen.setWidthF(
                        max(1.0, 0.2 * (inner.height() / max(1, self.rows))))
                    base_pen.setJoinStyle(QtCore.Qt.MiterJoin)
                    base_pen.setCapStyle(QtCore.Qt.RoundCap)

                    x0_mm, x1_mm = self._xrange_mm
                    src_span = max(1e-9, (x1_mm - x0_mm))
                    row_len_mm = max(1e-9, self._row_len_mm)

                    for r in range(self.rows):
                        xs, ys = self._row_points(inner, r)
                        # Grundlinie
                        p.setPen(base_pen)
                        path = QtGui.QPainterPath()
                        path.moveTo(xs[0], ys[0])
                        for i in range(1, len(xs)):
                            path.lineTo(xs[i], ys[i])
                        p.drawPath(path)

                        # Farbig übermalen
                        spans = self._spans[r] if r < len(self._spans) else []
                        for (sx_mm, ex_mm, hexcol) in spans:
                            sx_mm_cl = max(x0_mm, min(ex_mm, sx_mm))
                            ex_mm_cl = min(x1_mm, max(sx_mm, ex_mm))
                            if ex_mm_cl <= sx_mm_cl:
                                continue
                            f0 = (sx_mm_cl - x0_mm) / src_span
                            f1 = (ex_mm_cl - x0_mm) / src_span
                            rx0_mm = f0 * row_len_mm
                            rx1_mm = f1 * row_len_mm
                            x_px0 = float(
                                inner.left() + (rx0_mm / row_len_mm) * inner.width())
                            x_px1 = float(
                                inner.left() + (rx1_mm / row_len_mm) * inner.width())
                            if x_px1 <= x_px0:
                                continue
                            pen_row = QtGui.QPen(QtGui.QColor(hexcol))
                            pen_row.setWidthF(base_pen.widthF())
                            pen_row.setJoinStyle(base_pen.joinStyle())
                            pen_row.setCapStyle(base_pen.capStyle())
                            p.setPen(pen_row)
                            for i in range(1, len(xs)):
                                xm = 0.5 * (xs[i-1] + xs[i])
                                if x_px0 <= xm <= x_px1:
                                    p.drawLine(QtCore.QPointF(
                                        xs[i-1], ys[i-1]), QtCore.QPointF(xs[i], ys[i]))
            self.knitted_canvas = KnittedCanvas()
            knitted_layout.addWidget(self.knitted_canvas, 1)
            self.left_tabs.addTab(self.knitted_tab_left, "Knitted")
        except Exception:
            pass

        left_col.addWidget(self.left_tabs, 1)

        self.canvas.limitsChanged.connect(self._emit_fractional_limits)
        content_row.addLayout(left_col, 1)

        # --- rechte Seite mit Tabs (Tabbar fix) ---
        right_col = QtWidgets.QVBoxLayout()
        right_col.setSpacing(8)

        # Tab 1: Statistik (QTextEdit mit Monospace, kein Wrap)
        self.stats_box = QtWidgets.QTextEdit()
        self.stats_box.setReadOnly(True)
        self.stats_box.setMinimumWidth(360)
        self.stats_box.setMaximumWidth(540)
        self.stats_box.setPlaceholderText("Statistik…")
        self.stats_box.setStyleSheet(
            "QTextEdit { font-family: Consolas, 'Courier New', monospace; }")
        self.stats_box.setWordWrapMode(QTextOption.NoWrap)
        stats_wrap = QtWidgets.QWidget()
        stats_layout = QtWidgets.QVBoxLayout(stats_wrap)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.addWidget(self.stats_box)

        # Tab 1b: Unevenness (Run-Length-Histogramm pro Klasse)
        self.uneven_tab = QtWidgets.QWidget()
        unev_layout = QtWidgets.QVBoxLayout(self.uneven_tab)
        unev_layout.setContentsMargins(0, 0, 0, 0)
        unev_layout.setSpacing(6)

        self.uneven_info = QtWidgets.QLabel(
            "Number of adjacent events (runs) per class – based on the percent thresholds of the matrix.")
        self.uneven_info.setWordWrap(True)

        self.uneven_table = QtWidgets.QTableWidget(0, 7)
        self.uneven_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        # Auswahl/Copy: mehrere Zellen markieren + kopieren (Ctrl+C)
        self.uneven_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.uneven_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.uneven_table.setAlternatingRowColors(True)
        # Alternierender Zeilenhintergrund (hellgrün) für bessere Lesbarkeit
        self.uneven_table.setStyleSheet(
            "QTableWidget { background-color: white; alternate-background-color: #e9ffe9; }"
            "QTableWidget::item:selected { background-color: #bfffbf; color: black; }"
        )
        try:
            QtGui.QShortcut(QtGui.QKeySequence.Copy, self.uneven_table, activated=self._copy_unevenness_selection)
        except Exception:
            pass
        self.uneven_table.verticalHeader().setVisible(True)
        self.uneven_table.horizontalHeader().setVisible(True)
        self.uneven_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.uneven_table.verticalHeader().setDefaultSectionSize(26)
        self.uneven_table.setMinimumWidth(360)

        # Header klickbar machen: Klick auf Spalten-/Zeilenüberschrift selektiert ganze Spalte/Zeile
        try:
            hh = self.uneven_table.horizontalHeader()
            vh = self.uneven_table.verticalHeader()
            hh.setSectionsClickable(True)
            vh.setSectionsClickable(True)
            hh.sectionClicked.connect(lambda idx: self.uneven_table.selectColumn(idx))
            vh.sectionClicked.connect(lambda idx: self.uneven_table.selectRow(idx))
        except Exception:
            pass

        unev_layout.addWidget(self.uneven_info)
        unev_layout.addWidget(self.uneven_table, 1)

        # Tab 2: Matrix (Inhalt in ScrollArea, Tabbar bleibt fix)
        matrix_inner = QtWidgets.QWidget()
        mv = QtWidgets.QVBoxLayout(matrix_inner)
        mv.setContentsMargins(0, 0, 0, 0)
        mv.setSpacing(6)
        self.lbl_di = QtWidgets.QLabel("Dickstellen – Matrix (pro 100 m)")
        self.table_di = self._make_matrix_table(
            vertical_labels=["+10–<20 %", "+20–<30 %", "≥ +30 %"])
        self.lbl_due = QtWidgets.QLabel("Thin places – matrix (per 100 m)")
        self.table_due = self._make_matrix_table(
            vertical_labels=["–10–<20 %", "–20–<30 %", "≤ –30 %"])
        mv.addWidget(self.lbl_di)
        mv.addWidget(self.table_di)
        mv.addWidget(self.lbl_due)
        mv.addWidget(self.table_due)
        # Klick auf Matrix-Felder: Colour Picker öffnen
        try:
            self.table_di.cellDoubleClicked.connect(
                lambda r, c: self._matrix_pick_color(True, r, c))
            self.table_due.cellDoubleClicked.connect(
                lambda r, c: self._matrix_pick_color(False, r, c))
        except Exception:
            pass

        # Apply button for deferred updates (moved directly under Dünnstellen – Matrix)
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch(1)
        self._btn_apply = QtWidgets.QPushButton("Apply changes")
        self._btn_apply.setEnabled(False)
        self._btn_apply.clicked.connect(self._apply_pending_changes)
        btn_row.addWidget(self._btn_apply)
        try:
            VISIBILITY_STATE.visibilityChanged.connect(self._mark_dirty)
        except Exception:
            pass
        mv.addLayout(btn_row)
        # --- Schwellenwerte-Editor (global für alle Panels) ---
        self.group_thresh = QtWidgets.QGroupBox(
            "Thresholds (global, at runtime)")
        grid_t = QtWidgets.QGridLayout(self.group_thresh)
        # Di-Thresholds table
        self.table_di_thr = QtWidgets.QTableWidget(2, 3)
        self.table_di_thr.setHorizontalHeaderLabels(
            ["Band 1", "Band 2", "Band 3"])
        self.table_di_thr.setVerticalHeaderLabels(
            ["% above mean", "min. length [mm]"])
        self.table_di_thr.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch)
        self.table_di_thr.verticalHeader().setDefaultSectionSize(28)
        # Dü-Thresholds table
        self.table_due_thr = QtWidgets.QTableWidget(2, 3)
        self.table_due_thr.setHorizontalHeaderLabels(
            ["Band 1", "Band 2", "Band 3"])
        self.table_due_thr.setVerticalHeaderLabels(
            ["% below mean", "min. length [mm]"])
        self.table_due_thr.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch)
        self.table_due_thr.verticalHeader().setDefaultSectionSize(28)
        grid_t.addWidget(QtWidgets.QLabel("Dickstellen (Di)"), 0, 0)
        grid_t.addWidget(self.table_di_thr, 1, 0)
        grid_t.addWidget(QtWidgets.QLabel("Thin places"), 0, 1)
        grid_t.addWidget(self.table_due_thr, 1, 1)
        mv.addWidget(self.group_thresh)
        self._init_color_editor(mv)
        scroll_matrix = QtWidgets.QScrollArea()
        scroll_matrix.setWidgetResizable(True)
        scroll_matrix.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_matrix.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_matrix.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_matrix.setWidget(matrix_inner)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(stats_wrap, "Statistik")
        self.tabs.addTab(self.uneven_tab, "Unevenness")
        self.tabs.addTab(scroll_matrix, "Matrix")
        # Tab: Machine Data (anfangs verborgen)
        self.machine_tab = MachineDataTab(self)
        self._tab_idx_machine = self.tabs.addTab(
            self.machine_tab, "Machine Data")
        if hasattr(self.tabs, "setTabVisible"):
            self.tabs.setTabVisible(self._tab_idx_machine, False)
        else:
            # als Fallback: vorerst entfernen; später bei Bedarf wieder hinzufügen
            self.tabs.removeTab(self._tab_idx_machine)
            self._tab_idx_machine = None

        # NEU: Tab 4 „Graph“ – sortierte Differenzen (gesamte Serie) in µm
        self.graph_tab = QtWidgets.QWidget()
        graph_layout = QtWidgets.QVBoxLayout(self.graph_tab)
        self._graph_layout = graph_layout
        graph_layout.setContentsMargins(0, 0, 0, 0)
        self.graph_fig = Figure(figsize=(8, 1.3), dpi=120)
        self.graph_ax = self.graph_fig.add_subplot(111)
        self.graph_canvas = FigureCanvas(self.graph_fig)
        self.graph_canvas.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.graph_canvas.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.graph_toolbar = NavigationToolbar(self.graph_canvas, self)
        try:
            self.graph_toolbar.coordinates.setVisible(False)
        except Exception:
            pass
        # Wrap in a scroll area so content can scroll
        self._graph_inner = QtWidgets.QWidget()
        inner_layout = QtWidgets.QVBoxLayout(self._graph_inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(6)
        inner_layout.addWidget(self.graph_toolbar)
        inner_layout.addWidget(self.graph_canvas, 1)
        self._graph_scroll = QtWidgets.QScrollArea()
        self._graph_scroll.setWidgetResizable(True)
        self._graph_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self._graph_scroll.setWidget(self._graph_inner)
        graph_layout.addWidget(self._graph_scroll, 1)
        self.tabs.addTab(self.graph_tab, "Graph")

        # NEU: Tab «Dickstellen-Analyse» (Aspektverhältnis-Bins)
        try:
            from ui.yarnscope.thick_spot_analysis import setup_thick_spot_tab
            setup_thick_spot_tab(self)
        except Exception as _e:
            import traceback
            print(f"[garngraf] thick_spot_analysis konnte nicht geladen werden: {_e}")
            traceback.print_exc()

        # Rechte Spalte final einhängen (keine äussere ScrollArea -> Tabbar bleibt fix)
        right_container2 = QtWidgets.QWidget()
        right_container2.setLayout(QtWidgets.QVBoxLayout())
        right_container2.layout().setContentsMargins(0, 0, 0, 0)
        right_container2.layout().addWidget(self.tabs)
        right_container2.setMinimumWidth(380)
        right_container2.setMaximumWidth(560)
        right_container2.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)

        content_row.addWidget(right_container2, 0)
        outer.addLayout(content_row)

        # Start: Dropdowns füllen
        self.populate_combo()

        # Tabellen initial aus globalen Schwellenwerten füllen
        self._load_threshold_tables_from_global()
        # Änderungen überwachen
        self.table_di_thr.itemChanged.connect(self._threshold_table_changed)
        self.table_due_thr.itemChanged.connect(self._threshold_table_changed)
        # Sync: auf Broadcast von anderen Panels reagieren
        try:
            SYNC_HUB.thresholds.connect(self._on_thresholds_broadcast)
        except Exception:
            pass

    def _mm_step(self) -> float:
        # aktueller Messabstand (aus TDMS, sonst Default)
        return float(self.mm_per_point_tdms) if getattr(self, "mm_per_point_tdms", None) is not None else float(MM_PER_POINT)

    def _points_per_segment(self) -> int:
        # Punkte pro 200-mm-Linie abhängig vom Messabstand
        step = self._mm_step()
        return max(1, int(round(SEGMENT_LEN_MM / step)))

    def _needed_points(self) -> int:
        # Gesamtpunkte für den aktuellen Ausschnitt (max. 10 Linien)
        turns = int(getattr(self, "num_turns_current", NUM_TURNS))
        turns = max(1, min(NUM_TURNS, turns))
        return turns * self._points_per_segment()

    def _format_int_ch(self, n):
        try:
            return f"{int(n):,}".replace(",", "'")
        except Exception:
            return str(n)

    def _update_dataset_info_label(self):
        try:
            n = int(getattr(self, 'total_points', 0))
            if n <= 0:
                self.lbl_dataset_info.setText("–")
                return
            step_mm = float(self._mm_step())
            length_m = (n * step_mm) / 1000.0
            self.lbl_dataset_info.setText(
                f"{self._format_int_ch(n)} Messpunkte à {step_mm:g} mm • {length_m:.2f} m"
            )
        except Exception:
            try:
                self.lbl_dataset_info.setText("–")
            except Exception:
                pass
    # --- Hilfs-UI ---

    def _init_visibility_editor(self, layout_parent):
        """Checkboxen je Klasse (Di/Dü) zum Ein-/Ausschalten der Farbcodierung."""
        self.group_visibility = QtWidgets.QGroupBox(
            "Visibility of the classes (matrix & overlays)")
        grid = QtWidgets.QGridLayout(self.group_visibility)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        di_keys = ["Di11", "Di12", "Di13", "Di21",
                   "Di22", "Di23", "Di31", "Di32", "Di33"]
        due_keys = ["Dü11", "Dü12", "Dü13", "Dü21",
                    "Dü22", "Dü23", "Dü31", "Dü32", "Dü33"]

        self._chk_di = {}
        self._chk_due = {}

        grid.addWidget(QtWidgets.QLabel("Dickstellen (Di)"), 0, 0, 1, 3)
        grid.addWidget(QtWidgets.QLabel("Thin places"), 0, 3, 1, 3)

        for idx, key in enumerate(di_keys):
            r = 1 + idx // 3
            c = (idx % 3)
            chk = QtWidgets.QCheckBox(key)
            chk.setChecked(VISIBILITY_STATE.is_enabled(key))
            chk.toggled.connect(lambda on, k=key: (
                VISIBILITY_STATE.set_enabled(k, on)))
            self._chk_di[key] = chk
            grid.addWidget(chk, r, c)

        for idx, key in enumerate(due_keys):
            r = 1 + idx // 3
            c = 3 + (idx % 3)
            chk = QtWidgets.QCheckBox(key)
            chk.setChecked(VISIBILITY_STATE.is_enabled(key))
            chk.toggled.connect(lambda on, k=key: (
                VISIBILITY_STATE.set_enabled(k, on)))
            self._chk_due[key] = chk
            grid.addWidget(chk, r, c)

        layout_parent.addWidget(self.group_visibility)

        try:
            VISIBILITY_STATE.visibilityChanged.connect(self._mark_dirty)
            # deferred redraw handled by Apply button
        except Exception:
            pass

        self._apply_visibility_to_matrix()

    def _apply_visibility_to_matrix(self):
        """Färbt Matrix-Zellen je nach Sichtbarkeit ein (grau = aus)."""

    def _mark_dirty(self, *args, **kwargs):
        """Merkt anstehende Änderungen vor und aktiviert den Apply-Button."""
        try:
            self._pending_changes = True
            if hasattr(self, "_btn_apply"):
                self._btn_apply.setEnabled(True)
        except Exception:
            pass

    def _apply_pending_changes(self):
        """Übernimmt anstehende Änderungen: Matrix aktualisieren + neu rendern."""
        try:
            if hasattr(self, "_refresh_matrix_colors"):
                self._refresh_matrix_colors()
        except Exception:
            pass
        try:
            if hasattr(self, "_apply_visibility_to_matrix"):
                self._apply_visibility_to_matrix()
        except Exception:
            pass
        try:
            if hasattr(self, 'recompute_and_plot'):
                self.recompute_and_plot()
            else:
                self.update_plot_only()
        except Exception:
            pass
        self._pending_changes = False
        if hasattr(self, "_btn_apply"):
            self._btn_apply.setEnabled(False)

        def set_cell_bg(table, row, col, key, default_color):
            item = table.item(row, col)
            if item is None:
                item = QtWidgets.QTableWidgetItem("")
                table.setItem(row, col, item)
            if VISIBILITY_STATE.is_enabled(key):
                try:
                    item.setBackground(QtGui.QColor(default_color))
                    item.setForeground(QtGui.QColor("black"))
                except Exception:
                    pass
            else:
                try:
                    item.setBackground(QtGui.QColor("#eeeeee"))
                    item.setForeground(QtGui.QColor("#666666"))
                except Exception:
                    pass

        for r in range(3):
            for c in range(3):
                key = f"Di{r+1}{c+1}"
                col = COLOR_STATE.di_colors.get(key, DI_COLORS.get(key))
                set_cell_bg(self.table_di, r, c, key, col)

        for r in range(3):
            for c in range(3):
                key = f"Dü{r+1}{c+1}"
                col = COLOR_STATE.due_colors.get(key, DUE_COLORS.get(key))
                set_cell_bg(self.table_due, r, c, key, col)

    def _matrix_pick_color(self, is_dick: bool, row: int, col: int):
        """Öffnet den Colour Picker für die angeklickte Matrix-Box (Di/Dü) und
        übernimmt die Änderung live in COLOR_STATE + Plot."""
        try:
            from PySide6.QtWidgets import QColorDialog
            key = f"{'Di' if is_dick else 'Dü'}{row+1}{col+1}"
            family = 'Di' if is_dick else 'Dü'
            cur_hex = COLOR_STATE.di_colors.get(key, DI_COLORS.get(
                key)) if is_dick else COLOR_STATE.due_colors.get(key, DUE_COLORS.get(key))
            base_col = QtGui.QColor(
                cur_hex) if cur_hex else QtGui.QColor("#ffffff")
            new = QColorDialog.getColor(
                base_col, self, f"Choose colour – {family} {key}")
            if new.isValid():
                hexc = new.name()
                COLOR_STATE.set_color(family, key, hexc)
                try:
                    self._mark_dirty()
                except Exception:
                    pass
        except Exception:
            pass

    def _init_color_editor(self, layout_parent):
        # Farben-Editor (kompakter Grid mit Buttons)
        self.group_colors = QtWidgets.QGroupBox(
            "Colours (thick/thin) – change live")
        self.group_colors.setVisible(False)
        grid = QtWidgets.QGridLayout(self.group_colors)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        def make_btn(hexcol):
            b = QtWidgets.QPushButton()
            b.setFixedWidth(46)
            b.setText("")
            b.setToolTip(hexcol)
            b.setStyleSheet(
                f"QPushButton {{ background: {hexcol}; border: 1px solid #444; }}")
            return b

        # Reihenfolge festlegen
        # Button-Maps für globale Vorschau-Aktualisierung
        self._color_btns_di = {}
        self._color_btns_due = {}
        di_keys = ["Di11", "Di12", "Di13", "Di21",
                           "Di22", "Di23", "Di31", "Di32", "Di33"]
        due_keys = ["Dü11", "Dü12", "Dü13", "Dü21",
                    "Dü22", "Dü23", "Dü31", "Dü32", "Dü33"]

        grid.addWidget(QtWidgets.QLabel("Dickstellen (Di)"), 0, 0, 1, 1)
        for j, k in enumerate(di_keys, start=1):
            btn = make_btn(COLOR_STATE.di_colors.get(k, DI_COLORS.get(k)))
            btn.clicked.connect(lambda _=False, kk=k,
                                b=btn: self._pick_color('Di', kk, b))
            self._color_btns_di[k] = btn
            grid.addWidget(QtWidgets.QLabel(kk if (kk := k) else k),
                           1 + (j-1)//3*2, ((j-1) % 3)*2, 1, 1)
            grid.addWidget(btn, 1 + (j-1)//3*2, ((j-1) % 3)*2 + 1, 1, 1)

        row_off = 1 + ((len(di_keys)-1)//3)*2 + 1
        grid.addWidget(QtWidgets.QLabel("Thin places"), row_off, 0, 1, 1)
        for j, k in enumerate(due_keys, start=1):
            btn = make_btn(COLOR_STATE.due_colors.get(k, DUE_COLORS.get(k)))
            btn.clicked.connect(lambda _=False, kk=k,
                                b=btn: self._pick_color('Dü', kk, b))
            self._color_btns_due[k] = btn
            grid.addWidget(QtWidgets.QLabel(kk if (kk := k) else k),
                           row_off + 1 + (j-1)//3*2, ((j-1) % 3)*2, 1, 1)
            grid.addWidget(btn, row_off + 1 + (j-1) //
                           3*2, ((j-1) % 3)*2 + 1, 1, 1)

        COLOR_STATE.colorsChanged.connect(self._refresh_color_buttons)
        COLOR_STATE.colorsChanged.connect(self._mark_dirty)
        self._refresh_color_buttons()
        layout_parent.addWidget(self.group_colors)
        try:
            COLOR_STATE.colorsChanged.connect(lambda: (self._refresh_matrix_colors(
            ), self.recompute_and_plot() if hasattr(self, 'recompute_and_plot') else self.update_plot_only()))
        except Exception:
            pass

    def _pick_color(self, family: str, key: str, btn: QtWidgets.QPushButton):
        from PySide6.QtWidgets import QColorDialog
        cur_hex = COLOR_STATE.di_colors.get(
            key) if family == 'Di' else COLOR_STATE.due_colors.get(key)
        col = QColor(cur_hex) if cur_hex else QColor("#ffffff")
        new = QColorDialog.getColor(
            col, self, f"Choose colour – {family} {key}")
        if new.isValid():
            hexc = new.name()
            COLOR_STATE.set_color(family, key, hexc)
            try:
                btn.setStyleSheet(
                    f"QPushButton {{ background: {hexc}; border: 1px solid #444; }}")
                btn.setToolTip(hexc)
            except Exception:
                pass

    def _refresh_color_buttons(self):
        """Synchronisiere Matrix-Farbvorschau-Buttons mit globalem COLOR_STATE (panelübergreifend)."""
        try:
            for k, b in getattr(self, '_color_btns_di', {}).items():
                hexc = COLOR_STATE.di_colors.get(k, DI_COLORS.get(k))
                b.setToolTip(hexc)
                b.setStyleSheet(
                    f"QPushButton {{ background: {hexc}; border: 1px solid #444; }}")
            for k, b in getattr(self, '_color_btns_due', {}).items():
                hexc = COLOR_STATE.due_colors.get(k, DUE_COLORS.get(k))
                b.setToolTip(hexc)
                b.setStyleSheet(
                    f"QPushButton {{ background: {hexc}; border: 1px solid #444; }}")
        except Exception:
            pass

    def _make_matrix_table(self, vertical_labels=None) -> QtWidgets.QTableWidget:
        tbl = QtWidgets.QTableWidget(3, 3)
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        tbl.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        tbl.verticalHeader().setVisible(True)
        tbl.horizontalHeader().setVisible(True)
        # kompakte Höhe, flexible Breite
        tbl.setFixedHeight(170)
        tbl.setMinimumWidth(360)
        tbl.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                          QtWidgets.QSizePolicy.Fixed)
        from PySide6.QtWidgets import QHeaderView
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tbl.verticalHeader().setDefaultSectionSize(36)
        tbl.setHorizontalHeaderLabels(["1–<2 mm", "2–<3 mm", "≥3 mm"])
        if vertical_labels is None:
            vertical_labels = ["Band 1", "Band 2", "Band 3"]
        tbl.setVerticalHeaderLabels(vertical_labels)
        try:
            tbl.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            tbl.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        except Exception:
            pass
        return tbl

    # --- Datei-/Daten-Handling ---
    def _list_testdata_files(self):
        TESTDATA_DIR.mkdir(parents=True, exist_ok=True)
        return sorted([p for p in TESTDATA_DIR.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS],
                      key=lambda p: p.name.lower())

    def populate_combo(self):

        # Zielordner-basiert befüllen
        try:
            self.populate_combo_from_dir(self.import_dir)
            return
        except Exception:
            pass

    def populate_combo_from_dir(self, folder_path: str):
        """Füllt die Dateiliste (Combo) aus einem Zielordner."""

        try:

            import os

            self.combo_files.blockSignals(True)

            self.combo_files.clear()

            if folder_path and os.path.isdir(folder_path):

                files = sorted([f for f in os.listdir(
                    folder_path) if f.lower().endswith('.tdms')])

                for fname in files:

                    fpath = os.path.join(folder_path, fname)

                    self.combo_files.addItem(fname, userData=fpath)

        finally:

            self.combo_files.blockSignals(False)
        self.combo_files.blockSignals(True)
        self.combo_files.clear()
        files = self._list_testdata_files()
        if not files:
            self.combo_files.addItem("— no TDMS files —", userData=None)
            self.combo_files.setEnabled(False)
        else:
            self.combo_files.setEnabled(True)
            for p in files:
                self.combo_files.addItem(p.name, userData=str(p))
            self.combo_files.setCurrentIndex(0)
        self.combo_files.blockSignals(False)

    def open_file_browser_dialog(self):
        """Öffnet den File-Browser im zuletzt benutzten Ordner und merkt ihn sich erneut."""
        try:
            settings = QSettings('YarnScope', 'ATY')
            last_dir = settings.value(
                'file_browser/last_dir', DEFAULT_IMPORT_DIR, type=str)
        except Exception:
            last_dir = DEFAULT_IMPORT_DIR

        dlg = FileBrowserDialog(self, folder=(
            last_dir if last_dir else None), title="Load folder…")
        try:
            result = dlg.exec()
            accepted = (result == QtWidgets.QDialog.Accepted)
        except Exception:
            # Fallback, falls QtWidgets nicht im Namensraum ist
            accepted = bool(dlg.exec())

        path = dlg.selected_path if accepted else None
        if path:
            self.current_file_path = str(path)
            try:
                from pathlib import Path as _P
                self.lbl_file.setText(_P(path).name)
            except Exception:
                if hasattr(self, 'lbl_file') and hasattr(self.lbl_file, 'setText'):
                    self.lbl_file.setText(str(path))

            # last_dir speichern
            try:
                from pathlib import Path as _P2
                settings = QSettings('YarnScope', 'ATY')
                settings.setValue('file_browser/last_dir',
                                  str(_P2(path).parent))
                settings.sync()
            except Exception:
                pass

            # Daten laden wie im Original ohne Argumente
            try:
                self.load_data()
            except TypeError:
                # kompatibel: manche Varianten erwarten einen Pfad
                try:
                    self.load_data(self.current_file_path)
                except Exception:
                    pass

    def choose_import_folder(self):
        """Ordnerdialog öffnen, Import-Pfad speichern und Dateiliste neu laden."""

        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select target folder", str(
            self.import_dir) if getattr(self, 'import_dir', None) else "")

        if folder:

            self.import_dir = folder

            try:

                _settings = QSettings('YarnScope', 'ATY')

                _settings.setValue('import_dir', folder)

            except Exception:

                pass

            self.populate_combo_from_dir(folder)

    def load_data(self):
        path = getattr(self, "current_file_path", None)
        if not path:
            QtWidgets.QMessageBox.warning(
                self, "Note", "Please load a TDMS file first.")
            return
        p = Path(path)
        if not p.exists():
            QtWidgets.QMessageBox.critical(
                self, "Error", f"File not found:\n{p}")
            return
        try:
            arr = _read_first_numeric_tdms_channel(p)

            # Messabstand (mm) aus TDMS ermitteln und zu Kontrolle in Konsole ausgeben
            try:
                mm_tdms = _read_messabstand_mm_from_tdms(p)
            except Exception:
                mm_tdms = None
            self.mm_per_point_tdms = float(
                mm_tdms) if mm_tdms is not None else None
            if self.mm_per_point_tdms is not None:
                try:
                    print(
                        f"[garngraf] Messabstand (aus TDMS): {self.mm_per_point_tdms:g} mm")
                except Exception:
                    pass
            else:
                try:
                    print(
                        f"[garngraf] Messabstand (aus TDMS) nicht gefunden – verwende Default {MM_PER_POINT:g} mm")
                except Exception:
                    pass
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Error while reading", f"The TDMS file could not be loaded:\n{e}")
            return
        if arr is None:
            QtWidgets.QMessageBox.critical(
                self, "Error", "No numeric channel found in this TDMS file.")
            return
        self.series_um = np.asarray(arr, dtype=float)
        total_points = self.series_um.size

        # Dynamisch: wie viele volle 200-mm-Linien sind vorhanden?
        pps = int(self._points_per_segment())
        available_turns = int(total_points // max(1, pps))

        if available_turns < 1:
            QtWidgets.QMessageBox.critical(
                self,
                "Not enough data",
                f"Found: {total_points} points, required: at least {pps} points (1 × 200 mm)."
            )
            return

        self.num_turns_available = available_turns
        self.num_turns_current = min(NUM_TURNS, available_turns)

        self.series_mm_full = self.series_um / 1000.0
        self.total_points = total_points

        needed_now = self._needed_points()
        self.max_start_points = max(0, total_points - needed_now)
        self.slider.blockSignals(True)
        self.mm_spin.blockSignals(True)
        self.slider.setRange(0, self.max_start_points)
        self.slider.setValue(0)
        max_start_mm = self.max_start_points * self._mm_step()
        self.mm_spin.setRange(0.0, float(max_start_mm))
        self.mm_spin.setValue(0.0)

        # Schrittweite der mm-Eingabe gemäss Messabstand setzen (falls vorhanden)
        try:
            step = float(self.mm_per_point_tdms) if self.mm_per_point_tdms is not None else float(
                MM_PER_POINT)
            self.mm_spin.setSingleStep(step)
        except Exception:
            pass
        self.slider.blockSignals(False)
        self.mm_spin.blockSignals(False)
        self.current_start_points = 0
        # Graph-Widgets neu aufbauen, dann neu zeichnen
        try:
            self.rebuild_graph_widgets()
        except Exception:
            pass
        # Datensatz-Info (N × Δx = L)
        self._update_dataset_info_label()
        self.recompute_and_plot()

        # --- Machine Data: IDs aus Dateinamen extrahieren ---
        trial_series_id = None
        trial_id = None
        try:
            base = p.stem
            parts = base.split("_")
            if len(parts) >= 1 and parts[0].isdigit():
                trial_series_id = int(parts[0])
            if len(parts) >= 2 and parts[1].isdigit():
                trial_id = int(parts[1])
        except Exception:
            trial_series_id = None
            trial_id = None

        # --- DB: TrialSeries prüfen + Maschine lesen ---
        exists = False
        machine_name = None
        jet_name = None
        materials = []
        exp_code = None
        if trial_series_id is not None:
            try:
                rows = fetch_all(
                    "SELECT ts.ID AS TrialSeriesID, ts.ExperimentID AS ExperimentID, ts.SeriesName AS SeriesName, m.Maschine AS MachineName "
                    "FROM tblTrialSeries AS ts "
                    "LEFT JOIN tblMaschine AS m ON ts.MachineID = m.ID "
                    "WHERE ts.ID = ?",
                    [trial_series_id]
                )
                exists = len(rows) > 0
                if exists:
                    r0 = rows[0]
                    machine_name = r0.get('MachineName') or r0.get('Maschine')
                    exp_id = r0.get('ExperimentID')
                    series_name = r0.get('SeriesName')
                    ts_title = f"{exp_id} - {series_name}" if (exp_id and series_name) else (
                        series_name or str(exp_id) if exp_id else None)
            except Exception:
                exists = False
                machine_name = None

        # --- DB: Trial -> Jet auflösen ---
        if exists and (trial_id is not None):
            try:
                rtrial = fetch_all(
                    "SELECT t.JetID, t.[Air Pressure (bar)] AS AirPressure, t.[Shaft 2 Speed (m/min)] AS Shaft2Speed, t.[Shaft 1,1 Core (OF%)] AS OFCore, t.[Shaft 1,2 Effect (OF%)] AS OFEffect, t.Versuchsnummer AS Versuchsnummer FROM tblTrial AS t WHERE t.TrialSeriesID = ? AND t.Versuchsnummer = ?",
                    [trial_series_id, trial_id]
                )
                if rtrial:
                    jet_id = rtrial[0].get('JetID')
                    air_val = rtrial[0].get('AirPressure') or rtrial[0].get(
                        'Air Pressure (bar)')
                    speed_val = rtrial[0].get('Shaft2Speed') or rtrial[0].get(
                        'Shaft 2 Speed (m/min)')
                    of_core = rtrial[0].get('OFCore') or rtrial[0].get(
                        'Shaft 1,1 Core (OF%)')
                    of_effect = rtrial[0].get('OFEffect') or rtrial[0].get(
                        'Shaft 1,2 Effect (OF%)')
                    versuchs = rtrial[0].get('Versuchsnummer')
                    if jet_id is not None:
                        rjet = fetch_all(
                            "SELECT j.Jet AS JetName FROM tblDTYJets AS j WHERE j.ID = ?",
                            [jet_id]
                        )
                        if rjet:
                            jet_name = rjet[0].get(
                                'JetName') or rjet[0].get('Jet')
            except Exception:
                pass

        # --- DB: ExperimentID (Code) aus tblExperimente lesen ---
        if trial_series_id is not None:
            try:
                rexp = fetch_all(
                    "SELECT e.[Experiment ID] AS ExpCode "
                    "FROM tblTrialSeries AS ts "
                    "LEFT JOIN tblExperimente AS e ON e.ID = ts.ExperimentID "
                    "WHERE ts.ID = ?",
                    [trial_series_id]
                )
                if rexp:
                    exp_code = rexp[0].get(
                        'ExpCode') or rexp[0].get('ExperimentID')
            except Exception:
                exp_code = None

        # --- DB: Materialien für die TrialSeries laden (alle Einträge) ---
        if exists:
            try:
                rmat = fetch_all(
                    "SELECT DISTINCT y.Name AS YarnName, ts.Ply AS UseTxt "
                    "FROM tbltrialsettings ts "
                    "JOIN tbltrial t ON t.ID = ts.TrialID "
                    "LEFT JOIN tblYarn AS y ON y.ID = ts.YarnID "
                    "WHERE t.TrialSeriesID = ? "
                    "AND ts.YarnID IS NOT NULL "
                    "ORDER BY ts.Ply",
                    [trial_series_id]
                )
                for row in rmat:
                    name = row.get('YarnName') or row.get('Name')
                    u = row.get('UseTxt')
                    if name:
                        materials.append(f"{name} ({u})" if u else f"{name}")
            except Exception:
                pass

        # --- UI: Machine Data Tab aktualisieren & Sichtbarkeit setzen ---
        try:
            self.machine_tab.set_trial_series_id(locals().get(
                'ts_title') if locals().get('ts_title') else trial_series_id)
            self.machine_tab.set_trial_id(locals().get(
                'versuchs') if locals().get('versuchs') is not None else trial_id)
            if exists and (not machine_name):
                self.machine_tab.set_machine_name('Machine not found')
            else:
                self.machine_tab.set_machine_name(machine_name)
            if exists and (trial_id is not None) and (not jet_name):
                self.machine_tab.set_jet_name('Jet not found')
            else:
                self.machine_tab.set_jet_name(jet_name)
            self.machine_tab.set_materials(materials)
            # ExperimentID (aus tblExperimente + tblTrialSeries.SeriesName) anzeigen
            exp = locals().get('exp_code')
            sname = locals().get('series_name')
            disp = f"{exp} - {sname}" if exp and sname else (exp or sname)
            self.machine_tab.set_experiment_id(disp)
            # Luftdruck & Geschwindigkeit anzeigen
            try:
                self.machine_tab.set_air_pressure(locals().get('air_val'))
                self.machine_tab.set_speed(locals().get('speed_val'))
                self.machine_tab.set_of_core(locals().get('of_core'))
                self.machine_tab.set_of_effect(locals().get('of_effect'))
            except Exception:
                pass
        except Exception:
            pass
        self._set_machine_tab_visible(bool(exists))

    def _set_machine_tab_visible(self, visible: bool):
        if hasattr(self.tabs, "setTabVisible") and self._tab_idx_machine is not None:
            self.tabs.setTabVisible(self._tab_idx_machine, bool(visible))
        else:
            want = bool(visible)
            has = (getattr(self, "_tab_idx_machine", None) is not None) and (
                self.tabs.indexOf(self.machine_tab) != -1)
            if want and not has:
                self._tab_idx_machine = self.tabs.addTab(
                    self.machine_tab, "Machine Data")
            elif not want and has:
                idx = self.tabs.indexOf(self.machine_tab)
                if idx != -1:
                    self.tabs.removeTab(idx)

    # --- Bedienlogik ---

    def on_slider_changed(self, val: int):
        if self.series_um is None:
            return
        self.current_start_points = int(val)
        self.mm_spin.blockSignals(True)
        self.mm_spin.setValue(
            float(self.current_start_points * self._mm_step()))
        self.mm_spin.blockSignals(False)
        self.recompute_and_plot()

    def on_mm_changed(self, mm_val: float):
        if self.series_um is None:
            return
        step = float(self.mm_per_point_tdms) if self.mm_per_point_tdms is not None else float(
            MM_PER_POINT)
        pts = int(round(mm_val / step))
        pts = max(0, min(pts, self.max_start_points))
        self.current_start_points = pts
        self.slider.blockSignals(True)
        self.slider.setValue(pts)
        self.slider.blockSignals(False)
        self.recompute_and_plot()

    def update_plot_only(self):
        if self.data_mm_current is not None:
            self.canvas.plot_garnspiegel(self.data_mm_current, gap_factor=self.gap_spin.value(),
                                         num_turns=int(getattr(self, "num_turns_current", NUM_TURNS)),
                                         show_colors=self.color_overlay_enabled,
                                         row_spacing_ref=self._row_spacing_ref,
                                         mm_per_point=self._mm_step())

    def set_color_overlay(self, enabled: bool):
        # Toggle DI/DÜ farbige Overlays im Garnspiegel
        self.color_overlay_enabled = bool(enabled)
        try:
            if hasattr(self, 'recompute_and_plot'):
                # Sicher neu berechnen (inkl. Clear + Redraw in plot_garnspiegel)
                self.recompute_and_plot()
            else:
                self.update_plot_only()
        except Exception:
            # Fallback: wenigstens Canvas neu malen
            pass
        try:
            self.canvas.figure.canvas.draw_idle()
        except Exception:
            pass
        try:
            self._update_fabric_from_series()
        except Exception:
            pass

    def _refresh_matrix_headers(self):
        try:
            di_pct = CLASS_THRESHOLDS["Di"]["pct"]
            due_pct = CLASS_THRESHOLDS["Dü"]["pct"]
            di_mm = CLASS_THRESHOLDS["Di"]["mm"]
            due_mm = CLASS_THRESHOLDS["Dü"]["mm"]
            # Zeilen-Köpfe: Prozent-Bänder
            self.table_di.setVerticalHeaderLabels([
                f"+{di_pct[0]:.0f}–<{di_pct[1]:.0f} %",
                f"+{di_pct[1]:.0f}–<{di_pct[2]:.0f} %",
                f"≥ +{di_pct[2]:.0f} %",
            ])
            self.table_due.setVerticalHeaderLabels([
                f"–{due_pct[0]:.0f}–<–{due_pct[1]:.0f} %",
                f"–{due_pct[1]:.0f}–<–{due_pct[2]:.0f} %",
                f"≤ –{due_pct[2]:.0f} %",
            ])
            # Spalten-Köpfe: Längen-Bänder

            def _mm_hdr(mm_list):
                a, b, c = float(mm_list[0]), float(
                    mm_list[1]), float(mm_list[2])
                return [f"{a:.1f}–<{b:.1f} mm", f"{b:.1f}–<{c:.1f} mm", f"≥ {c:.1f} mm"]
            self.table_di.setHorizontalHeaderLabels(_mm_hdr(di_mm))
            self.table_due.setHorizontalHeaderLabels(_mm_hdr(due_mm))
        except Exception:
            pass

    # --- Statistik + Matrix ---

    def _load_threshold_tables_from_global(self):
        # Temporär Signale blockieren, um Schleifen zu vermeiden
        for tbl, key in ((self.table_di_thr, "Di"), (self.table_due_thr, "Dü")):
            tbl.blockSignals(True)
            try:
                pct = CLASS_THRESHOLDS[key]["pct"]
                leng = CLASS_THRESHOLDS[key]["mm"]
                # Row 0: pct, Row 1: length mm
                for col in range(3):
                    it = QtWidgets.QTableWidgetItem(f"{float(pct[col]):.1f}")
                    it.setTextAlignment(Qt.AlignCenter)
                    tbl.setItem(0, col, it)
                    it2 = QtWidgets.QTableWidgetItem(f"{float(leng[col]):.2f}")
                    it2.setTextAlignment(Qt.AlignCenter)
                    tbl.setItem(1, col, it2)
            finally:
                tbl.blockSignals(False)

    def _threshold_table_changed(self, item):
        tbl = item.tableWidget()
        group = "Di" if tbl is self.table_di_thr else "Dü"
        row, col = item.row(), item.column()
        txt = item.text().strip().replace(",", ".")
        try:
            val = float(txt)
        except Exception:
            return  # ignore invalid
        # Update global dict
        if row == 0:  # pct row
            CLASS_THRESHOLDS[group]["pct"][col] = float(val)
        elif row == 1:  # mm row
            CLASS_THRESHOLDS[group]["mm"][col] = float(val)
        # Broadcast to all other panels
        try:
            SYNC_HUB.thresholds.emit(self._sync_id, {
                                     k: {kk: vv[:] for kk, vv in v.items()} for k, v in CLASS_THRESHOLDS.items()})
        except Exception:
            pass
        # Matrix-Köpfe aktualisieren
        try:
            self._refresh_matrix_headers()
        except Exception:
            pass
        # Neu zeichnen
        try:
            self.recompute_and_plot()
        except Exception:
            self.update_plot_only()

    def _on_thresholds_broadcast(self, sender_id, data):
        if sender_id == self._sync_id:
            return
        # Global updaten
        try:
            for k in ("Di", "Dü"):
                for sub in ("pct", "mm"):
                    CLASS_THRESHOLDS[k][sub] = [float(x) for x in data[k][sub]]
        except Exception:
            pass
        # Tabellen auffrischen
        self._load_threshold_tables_from_global()
        # Matrix-Köpfe aktualisieren
        try:
            self._refresh_matrix_headers()
        except Exception:
            pass
        # Neu zeichnen
        try:
            self.recompute_and_plot()
        except Exception:
            self.update_plot_only()

    def _stats_tuple(self, arr_mm: np.ndarray):
        if arr_mm.size == 0:
            return (float("nan"),)*7
        mean_mm = float(np.mean(arr_mm))
        std_mm = float(np.std(arr_mm, ddof=1)) if arr_mm.size > 1 else 0.0
        cv_pct = 100.0 * std_mm / mean_mm if mean_mm != 0 else float("nan")
        min_mm = float(np.min(arr_mm))
        max_mm = float(np.max(arr_mm))
        mean_um = mean_mm * 1000.0
        std_um = std_mm * 1000.0
        return mean_mm, std_mm, cv_pct, min_mm, max_mm, mean_um, std_um


    def _classify_unevenness_points(self, series_mm: np.ndarray) -> np.ndarray:
        """Klassifiziert jeden Messpunkt (der Reihe nach) in:
        0 = Garnkörper
        1..3 = Dickstelle 1..3 (Di)
        4..6 = Dünnstelle 1..3 (Dü)
        Schwellen basieren auf CLASS_THRESHOLDS (Prozent relativ zum Mittelwert).
        """
        series_mm = np.asarray(series_mm, dtype=float)
        if series_mm.size == 0:
            return np.asarray([], dtype=np.int8)

        mu = float(np.mean(series_mm))
        if not np.isfinite(mu) or mu == 0.0:
            return np.zeros(series_mm.shape, dtype=np.int8)

        di_pct = CLASS_THRESHOLDS["Di"]["pct"]
        due_pct = CLASS_THRESHOLDS["Dü"]["pct"]

        # Faktoren relativ zum Mittel
        di1 = 1.0 + float(di_pct[0]) / 100.0
        di2 = 1.0 + float(di_pct[1]) / 100.0
        di3 = 1.0 + float(di_pct[2]) / 100.0

        du1 = 1.0 - float(due_pct[0]) / 100.0
        du2 = 1.0 - float(due_pct[1]) / 100.0
        du3 = 1.0 - float(due_pct[2]) / 100.0

        x = series_mm / mu
        cls = np.zeros(series_mm.shape, dtype=np.int8)

        # Dickstellen: >= di1
        cls[(x >= di1) & (x < di2)] = 1
        cls[(x >= di2) & (x < di3)] = 2
        cls[(x >= di3)] = 3

        # Dünnstellen: <= du1
        cls[(x <= du1) & (x > du2)] = 4
        cls[(x <= du2) & (x > du3)] = 5
        cls[(x <= du3)] = 6

        return cls

    def _compute_runlength_counts(self, cls: np.ndarray):
        """Gibt pro Klasse (0..6) ein Dict {run_len: count} zurück.
        0 = Garnkörper, 1..3 = Dickstellen-Bänder, 4..6 = Dünnstellen-Bänder.
        """
        cls = np.asarray(cls, dtype=np.int16)
        out = {k: {} for k in range(0, 7)}
        if cls.size == 0:
            return out

        cur = int(cls[0])
        run = 1
        for v in cls[1:]:
            v = int(v)
            if v == cur:
                run += 1
                continue
            if 0 <= cur <= 6:
                out[cur][run] = out[cur].get(run, 0) + 1
            cur = v
            run = 1
        if 0 <= cur <= 6:
            out[cur][run] = out[cur].get(run, 0) + 1
        return out
    def _update_unevenness_tab(self):
        """Aktualisiert die Unevenness-Tabelle anhand der vollen Serie.

        Werte werden als Runs pro 100 m ausgegeben (nicht absolute Häufigkeiten pro File).
        """
        try:
            series = self.series_mm_full
            if series is None or len(series) == 0:
                self.uneven_table.setRowCount(0)
                return

            cls = self._classify_unevenness_points(series)
            counts = self._compute_runlength_counts(cls)

            # Länge der vollen Serie in Metern (aus Punktabstand)
            try:
                length_m = (float(len(series)) * float(self._mm_step())) / 1000.0
            except Exception:
                length_m = 0.0
            scale = (100.0 / length_m) if length_m > 0 else 0.0

            # Spaltenüberschriften: Garnkörper + Prozent-Klassen aus der Matrix (3× Di, 3× Dü)
            di_pct = CLASS_THRESHOLDS["Di"]["pct"]
            due_pct = CLASS_THRESHOLDS["Dü"]["pct"]
            headers = [
                "Yarn body",
                f"+{di_pct[0]:.0f}–<{di_pct[1]:.0f} %",
                f"+{di_pct[1]:.0f}–<{di_pct[2]:.0f} %",
                f"≥ +{di_pct[2]:.0f} %",
                f"–{due_pct[0]:.0f}–<–{due_pct[1]:.0f} %",
                f"–{due_pct[1]:.0f}–<–{due_pct[2]:.0f} %",
                f"≤ –{due_pct[2]:.0f} %",
            ]
            self.uneven_table.setHorizontalHeaderLabels(headers)

            # Info-Label aktualisieren
            try:
                if length_m > 0:
                    self.uneven_info.setText(
                        f"Number of consecutive events (runs) per class – per 100 m (series length: {length_m:.1f} m).\n"
                        "Based on the percent thresholds of the matrix.")
                else:
                    self.uneven_info.setText(
                        "Number of adjacent events (runs) per class – per 100 m.\n"
                        "Based on the percent thresholds of the matrix.")
            except Exception:
                pass

            # Max Run-Länge bestimmen (inkl. Garnkörper)
            max_run = 0
            for k in range(0, 7):
                if counts.get(k):
                    max_run = max(max_run, max(counts[k].keys(), default=0))

            if max_run <= 0:
                self.uneven_table.setRowCount(0)
                return

            self.uneven_table.setRowCount(max_run)
            self.uneven_table.setVerticalHeaderLabels([str(i) for i in range(1, max_run + 1)])

            def _fmt(v: float) -> str:
                # Tausendertrennzeichen (Schweiz: ') + 2 Dezimalstellen
                import numpy as _np
                try:
                    vv = float(v)
                except Exception:
                    vv = 0.0
                if not _np.isfinite(vv):
                    return "–"
                s = f"{vv:,.2f}"
                return s.replace(",", "'")


            def _set(r, c, v):
                it = QtWidgets.QTableWidgetItem(_fmt(v))
                it.setTextAlignment(Qt.AlignCenter)
                self.uneven_table.setItem(r, c, it)

            # Reihen: Run-Länge 1..max_run; Spalten: Garnkörper, Di1..3, Dü1..3
            for run_len in range(1, max_run + 1):
                _set(run_len - 1, 0, counts[0].get(run_len, 0) * scale)
                _set(run_len - 1, 1, counts[1].get(run_len, 0) * scale)
                _set(run_len - 1, 2, counts[2].get(run_len, 0) * scale)
                _set(run_len - 1, 3, counts[3].get(run_len, 0) * scale)
                _set(run_len - 1, 4, counts[4].get(run_len, 0) * scale)
                _set(run_len - 1, 5, counts[5].get(run_len, 0) * scale)
                _set(run_len - 1, 6, counts[6].get(run_len, 0) * scale)
        except Exception:
            # Im Zweifel: Tab nicht blockieren
            try:
                self.uneven_table.setRowCount(0)
            except Exception:
                pass
    def _copy_unevenness_selection(self):
        """Kopiert die markierte Auswahl als TSV inkl. Zeilen-/Spaltenüberschriften.

        - Spaltenüberschriften werden in der ersten Zeile mitkopiert
        - Zeilenüberschriften (Run-Länge) werden als erste Spalte mitkopiert
        """
        try:
            table = self.uneven_table
            sel = table.selectedIndexes()
            if not sel:
                return

            rows = [i.row() for i in sel]
            cols = [i.column() for i in sel]
            r0, r1 = min(rows), max(rows)
            c0, c1 = min(cols), max(cols)

            sel_set = {(i.row(), i.column()) for i in sel}

            # Header-Zeile (Spaltenüberschriften)
            header = [""]
            for c in range(c0, c1 + 1):
                hi = table.horizontalHeaderItem(c)
                header.append(hi.text() if hi is not None else "")
            lines = ["	".join(header)]

            # Datenzeilen (mit Zeilenüberschrift)
            for r in range(r0, r1 + 1):
                vi = table.verticalHeaderItem(r)
                row_label = vi.text() if vi is not None else ""
                parts = [row_label]
                for c in range(c0, c1 + 1):
                    if (r, c) in sel_set:
                        item = table.item(r, c)
                        parts.append(item.text() if item is not None else "")
                    else:
                        parts.append("")
                lines.append("	".join(parts))

            QtWidgets.QApplication.clipboard().setText("\n".join(lines))
        except Exception:
            pass


    def _fill_matrix(self, table: QtWidgets.QTableWidget, counts: Dict[str, float], colors: Dict[str, str], is_dick: bool):
        for r in (1, 2, 3):
            for c in (1, 2, 3):
                key = f"{'Di' if is_dick else 'Dü'}{r}{c}"
                val = counts.get(key, float('nan'))
                item = QtWidgets.QTableWidgetItem(_fmt_thousands_ch(val))
                item.setTextAlignment(Qt.AlignCenter)
                qcol = QColor(colors[key])
                item.setBackground(qcol)
                luminance = 0.2126*qcol.redF() + 0.7152*qcol.greenF() + 0.0722*qcol.blueF()
                item.setForeground(Qt.black if luminance > 0.6 else Qt.white)
                item.setToolTip(key)
                table.setItem(r-1, c-1, item)

    def _inject_checkboxes_into_matrix(self, table: QtWidgets.QTableWidget, is_dick: bool):
        """
        Fügt in jedes 3×3-Kästchen der Matrix eine Checkbox ein, ohne die bestehende
        Logik (Counts/Colors) zu entfernen. Die Checkbox spiegelt VISIBILITY_STATE wider.
        """
        # Erwartet 3x3
        rows = 3
        cols = 3
        for r in range(rows):
            for c in range(cols):
                key = f"{'Di' if is_dick else 'Dü'}{r+1}{c+1}"
                # Vorhandenes Item lesen (Text + Farben)
                item = table.item(r, c)
                text = item.text() if item else ""
                bg = item.background().color() if item else QColor("#333")
                fg = item.foreground().color() if item else QColor("#fff")
                # Container-Widget bauen
                w = QtWidgets.QWidget()
                lay = QtWidgets.QVBoxLayout(w)
                lay.setContentsMargins(6, 4, 6, 4)
                lay.setSpacing(2)
                # Count-Label
                lbl = QtWidgets.QLabel(text)
                lbl.setAlignment(Qt.AlignCenter)
                pal = lbl.palette()
                pal.setColor(lbl.foregroundRole(), fg)
                lbl.setPalette(pal)
                lbl.setStyleSheet("font-weight: 600;")
                # Checkbox (ohne Text, zentriert)
                chk = QtWidgets.QCheckBox()
                chk.setToolTip(key)
                chk.setChecked(VISIBILITY_STATE.is_enabled(key))
                # Hintergrund setzen (robust für PyInstaller/Styles)
                w.setObjectName("matrixBox")
                w.setAttribute(QtCore.Qt.WA_StyledBackground, True)
                try:
                    hexcol = bg.name() if hasattr(bg, 'name') else QtGui.QColor(bg).name()
                except Exception:
                    hexcol = QtGui.QColor(bg).name()
                # Stylesheet mit der berechneten Hex-Farbe setzen
                w.setStyleSheet(
                    "#matrixBox { background: " + hexcol + "; border: 1px solid #444; border-radius: 3px; }")
                # Layout zusammensetzen
                lay.addWidget(lbl, 0, Qt.AlignCenter)
                lay.addWidget(chk, 0, Qt.AlignCenter)
                # Toggle-Handler

                def _on_toggled(on, _k=key):
                    VISIBILITY_STATE.set_enabled(_k, bool(on))
                chk.toggled.connect(_on_toggled)
                try:
                    chk.toggled.connect(lambda _=False: self._mark_dirty())
                except Exception:
                    pass

                # Ganze Box klickbar für Colour Picker
                try:
                    def _cell_mouse_press(ev, _r=r, _c=c, _is_dick=is_dick, _w=w):
                        return QtWidgets.QWidget.mousePressEvent(_w, ev)
                    w.mousePressEvent = _cell_mouse_press
                except Exception:
                    pass

                # Widget einsetzen
                table.setCellWidget(r, c, w)

        # Nach dem Ersetzen sind die Items nicht mehr sichtbar – aber die Anzeige (Text/Farbe)
        # ist identisch im eingebetteten Widget repliziert.
        # Markiere Änderungen zur späteren Übernahme per Button.
        try:
            self._mark_dirty()
        except Exception:
            pass

    def _refresh_matrix_colors(self):
        """Recoloriert die Matrix-Zellen gemäss COLOR_STATE, ohne die Zahlen anzutasten."""
        try:
            # Di-Tabelle
            if hasattr(self, 'table_di') and self.table_di is not None:
                for r in range(3):
                    for c in range(3):
                        key = f"Di{r+1}{c+1}"
                        item = self.table_di.item(r, c)
                        if item:
                            hexc = COLOR_STATE.di_colors.get(
                                key, DI_COLORS.get(key))
                            if hexc:
                                qcol = QColor(hexc)
                                item.setBackground(qcol)
                                luminance = 0.2126*qcol.redF() + 0.7152*qcol.greenF() + 0.0722*qcol.blueF()
                                item.setForeground(
                                    Qt.black if luminance > 0.6 else Qt.white)
            # Dü-Tabelle
            if hasattr(self, 'table_due') and self.table_due is not None:
                for r in range(3):
                    for c in range(3):
                        key = f"Dü{r+1}{c+1}"
                        item = self.table_due.item(r, c)
                        if item:
                            hexc = COLOR_STATE.due_colors.get(
                                key, DUE_COLORS.get(key))
                            if hexc:
                                qcol = QColor(hexc)
                                item.setBackground(qcol)
                                luminance = 0.2126*qcol.redF() + 0.7152*qcol.greenF() + 0.0722*qcol.blueF()
                                item.setForeground(
                                    Qt.black if luminance > 0.6 else Qt.white)
        except Exception:
            pass

    def _format_counts_block(self, title: str, prefix: str, counts: Dict[str, float]) -> str:
        """
        Erzeugt GENAU drei Zeilen mit fester Spaltenbreite:
        r = 1 (..11..13), r = 2 (..21..23), r = 3 (..31..33).
        Jede Zelle ist 'KEY=VALUE' mit rechtsbündiger VALUE-Breite.
        """
        COLW = 9  # Breite des Wert-Teils
        SEP = "  "

        def cell(k: str) -> str:
            vtxt = _fmt_thousands_ch(counts.get(k, float('nan')))
            return f"{k}=" + vtxt.rjust(COLW)
        rows = []
        for r in (1, 2, 3):
            line = SEP.join([cell(f"{prefix}{r}1"), cell(
                f"{prefix}{r}2"), cell(f"{prefix}{r}3")])
            rows.append(line)
        return f"{title}\n" + "\n".join(rows)

    def _compute_core_thickness(self):
        """
        Berechnet die Kerndicke (Mittelwert im Kernband) in mm und µm.
        Kernband-Definition: Median ± 1× Standardabweichung (σ) der Dicke.
        Rückgabe: (core_mean_mm, core_mean_um)
        """
        try:
            import numpy as _np
            if self.series_mm_full is None or self.series_mm_full.size == 0:
                return float('nan'), float('nan')
            arr = self.series_mm_full.astype(float)
            med = float(_np.median(arr))
            std_mm = float(_np.std(arr, ddof=1)) if arr.size > 1 else 0.0
            # Grenzen in µm um den Median
            y_left = - std_mm * getattr(self, 'sigma_factor', 1.0) * 1000.0
            y_right = + std_mm * getattr(self, 'sigma_factor', 1.0) * 1000.0

            # Maske der Punkte im Kernband (bezogen auf µm-Delta zum Median)
            deltas_um = (arr - med) * 1000.0
            mask = (deltas_um >= y_left) & (deltas_um <= y_right)
            if not _np.any(mask):
                return float('nan'), float('nan')
            core_mean_mm = float(_np.mean(arr[mask]))
            return core_mean_mm, core_mean_mm * 1000.0
        except Exception:
            return float('nan'), float('nan')

    def _update_graph_tab(self):
        """Update des Graph-Tabs: sortierte Δ (gesamte Serie, µm) + Kernband via Median ± 1σ.
        Grüne Kernfläche, plus Ausreisser: links (hellblau), rechts (hellrot)."""
        if not hasattr(self, "graph_ax") or self.graph_ax is None:
            return
        self.graph_ax.clear()
        try:
            self.graph_ax.set_position([0.08, 0.38, 0.90, 0.46])
        except Exception:
            pass

        import numpy as _np

        if self.series_mm_full is None or self.series_mm_full.size == 0:
            self.graph_ax.set_title("Garnkern")
            self.graph_canvas.draw_idle()
            return
        # --- Achsenbeschriftungen und Zahlen entfernen ---
        self.graph_ax.set_xlabel("")
        self.graph_ax.set_ylabel("")
        self.graph_ax.set_xticklabels([])
        self.graph_ax.set_yticklabels([])
        self.graph_ax.set_xticks([])
        self.graph_ax.set_yticks([])
        self.graph_ax.tick_params(left=False, bottom=False)

        arr = self.series_mm_full.astype(float)
        med = float(_np.median(arr))
        std_mm = float(_np.std(arr, ddof=1)) if arr.size > 1 else 0.0
        # Sortierte Δ in µm
        y_unsorted = (arr - med) * 1000.0
        y = _np.sort(y_unsorted)
        n = y.size
        x = _np.arange(n, dtype=float)
        x1 = x + 1

        # Kernband-Grenzen (µm) nach Median ± 1σ
        y_left = - std_mm * getattr(self, 'sigma_factor', 1.0) * 1000.0
        y_right = + std_mm * getattr(self, 'sigma_factor', 1.0) * 1000.0

        # Indizes relativ zu den sortierten Δ bestimmen
        # idx_left: letzter Index <= y_left
        idx_left = int(_np.searchsorted(y, y_left, side='right')) - 1
        if idx_left < 0:
            idx_left = -1  # -1 => kein linker Bereich
        # idx_right: erster Index >= y_right
        idx_right = int(_np.searchsorted(y, y_right, side='left'))
        if idx_right > n:
            idx_right = n

        # --- Kennzahlen: MET, Frequenz, HKI ---
        try:
            # Flächen links/rechts (Summen der Exzesse)
            A_L = float(
                _np.sum(y_left - y[:idx_left+1])) if idx_left >= 0 else 0.0
            A_R = float(_np.sum(y[idx_right:] - y_right)
                        ) if idx_right < n else 0.0

            # Mean Excess over Threshold (µm) pro Punkt
            MET_L = A_L / n
            MET_R = A_R / n
            MET_tot = MET_L + MET_R

            # Frequenz (Anteil ausserhalb)
            p_L = (idx_left + 1) / n if idx_left >= 0 else 0.0
            p_R = (n - idx_right) / n if idx_right < n else 0.0
            p_tot = p_L + p_R

            # Robust normalisieren für dimensionslose Vergleichszahl
            if n >= 100:
                y1, y99 = _np.percentile(y, [1, 99])
            else:
                y1, y99 = float(y[0]), float(y[-1])
            denom = (y99 - y1) if (y99 - y1) != 0 else 1.0
            HKI = (A_L + A_R) / (n * denom)

            # Für spätere Anzeige im Statistik-Tab speichern
            self._metric_MET_tot = float(MET_tot)
            self._metric_FREQ_tot = float(p_tot)
            self._metric_FREQ_L = float(p_L)
            self._metric_FREQ_R = float(p_R)
            self._metric_HKI = float(HKI)
        except Exception:
            # Falls irgendwas schiefgeht, Nullwerte setzen
            self._metric_MET_tot = 0.0
            self._metric_FREQ_tot = 0.0
            self._metric_FREQ_L = 0.0
            self._metric_FREQ_R = 0.0
            self._metric_HKI = 0.0
        # Kernfläche (grün, unter den Linien)
        self.graph_ax.axhline(0.0, linestyle="--",
                              linewidth=0.8, color="#666666", zorder=1)
        self.graph_ax.axhline(y_left, linestyle="--",
                              linewidth=1.2, color="#2e7d32", zorder=2)
        self.graph_ax.axhline(y_right, linestyle="--",
                              linewidth=1.2, color="#2e7d32", zorder=2)
        self.graph_ax.fill_between(
            x1, y_left, y_right, color="#2e7d32", alpha=0.15, zorder=1)

        # Ausreisserflächen (hellblau links, hellrot rechts)
        if idx_left >= 0:
            self.graph_ax.fill_between(
                x1[:idx_left+1], y[:idx_left+1], y_left, color="#64b5f6", alpha=0.35, zorder=2)
        if idx_right < n:
            self.graph_ax.fill_between(
                x1[idx_right:], y_right, y[idx_right:], color="#ef5350", alpha=0.35, zorder=2)

        # Linie der sortierten Δ zuletzt (darüber zeichnen)
        self.graph_ax.plot(x1, y, linewidth=1.1, zorder=3)

        # Titel
        self.graph_ax.set_title(
            f"Garnkern (Median ± {getattr(self, 'sigma_factor', 1.0):g}σ)")

        # Histogramm unterhalb der Kurve
        try:
            if not hasattr(self, "graph_hist_ax") or self.graph_hist_ax is None:
                self.graph_hist_ax = self.graph_fig.add_axes(
                    [0.08, 0.08, 0.90, 0.26])
            else:
                self.graph_hist_ax.clear()
                try:
                    self.graph_hist_ax.set_position([0.08, 0.08, 0.90, 0.26])
                except Exception:
                    pass

            self.graph_hist_ax.hist(y_unsorted, bins=60, alpha=0.7)

            # Grenzen analog oben
            self.graph_hist_ax.axvline(
                0.0, linestyle="--", linewidth=0.8, color="#666666", zorder=2)
            self.graph_hist_ax.axvline(
                y_left, linestyle="--", linewidth=1.2, color="#2e7d32", zorder=3)
            self.graph_hist_ax.axvline(
                y_right, linestyle="--", linewidth=1.2, color="#2e7d32", zorder=3)

            # Keine Achsentitel/-beschriftungen
            self.graph_hist_ax.set_xlabel("")
            self.graph_hist_ax.set_ylabel("")
            self.graph_hist_ax.set_xticklabels([])
            self.graph_hist_ax.set_yticklabels([])
            self.graph_hist_ax.set_xticks([])
            self.graph_hist_ax.set_yticks([])
            self.graph_hist_ax.grid(False)
        except Exception:
            pass

        self.graph_canvas.draw_idle()

    def recompute_and_plot(self):
        # Thick-Spot-Tab immer aktualisieren (braucht nur series_mm_full, nicht den 2m-Ausschnitt)
        try:
            from ui.yarnscope.thick_spot_analysis import update_thick_spot_tab
            update_thick_spot_tab(self)
        except Exception:
            pass

        # Validate data
        if self.series_um is None or len(self.series_um) < self._needed_points():
            try:
                self.stats_box.setText("")
            except Exception:
                pass
            return

        start = int(self.current_start_points)
        end = start + self._needed_points()
        slice_um = self.series_um[start:end]
        data_mm_all = slice_um / 1000.0
        # Update/broadcast shared row spacing reference (global max)
        try:
            _ref = float(np.max(data_mm_all)) if data_mm_all.size else None
        except Exception:
            _ref = None
        if _ref is not None:
            self._row_spacing_ref = _ref if (
                self._row_spacing_ref is None) else max(self._row_spacing_ref, _ref)
            try:
                SYNC_HUB.yref.emit(self._sync_id, float(self._row_spacing_ref))
            except Exception:
                pass
        # Matrix-Header dynamisch an Pct-Schwellen anpassen
        try:
            self._refresh_matrix_headers()
        except Exception:
            pass
        try:
            self.canvas.plot_garnspiegel(
                data_mm_all,
                gap_factor=self.gap_spin.value(),
                show_colors=self.color_overlay_enabled,
                row_spacing_ref=self._row_spacing_ref,
                num_turns=int(getattr(self, "num_turns_current", NUM_TURNS)),
                mm_per_point=self._mm_step()
            )
        except Exception:
            pass

        mean_mm, std_mm, cv_percent, min_mm, max_mm, mean_um, std_um = self._stats_tuple(
            data_mm_all)
        series_for_full = self.series_mm_full if self.series_mm_full is not None else data_mm_all
        f_mean_mm, f_std_mm, f_cv, f_min_mm, f_max_mm, f_mean_um, f_std_um = self._stats_tuple(
            series_for_full)

        # --- Kernband (Median ± σ·Faktor) vorbereiten ---
        try:
            import numpy as _np
            sigma_factor = getattr(self, 'sigma_factor', 1.0)
            # Ausschnitt (2 m)
            med_slice = float(_np.median(data_mm_all)
                              ) if data_mm_all.size else float('nan')
            band_delta_slice = sigma_factor * \
                std_mm if _np.isfinite(std_mm) else float('nan')
            kb_lo_slice = med_slice - band_delta_slice
            kb_hi_slice = med_slice + band_delta_slice
            # Gesamte Serie
            med_full = float(_np.median(series_for_full)
                             ) if series_for_full.size else float('nan')
            band_delta_full = sigma_factor * \
                f_std_mm if _np.isfinite(f_std_mm) else float('nan')
            kb_lo_full = med_full - band_delta_full
            kb_hi_full = med_full + band_delta_full
        except Exception:
            kb_lo_slice = kb_hi_slice = kb_lo_full = kb_hi_full = float('nan')
            band_delta_slice = band_delta_full = float('nan')
        full_len_mm = (len(self.series_mm_full) * self._mm_step()
                       ) if (self.series_mm_full is not None) else 0.0
        mm_step = float(
            self.mm_per_point_tdms) if self.mm_per_point_tdms is not None else float(MM_PER_POINT)
        di_counts_abs = _classify_dickstellen_3x3(
            self.series_mm_full, mm_step,
            mean_factor_edges=(1.0 + CLASS_THRESHOLDS['Di']['pct'][0]/100.0,
                               1.0 + CLASS_THRESHOLDS['Di']['pct'][1]/100.0,
                               1.0 + CLASS_THRESHOLDS['Di']['pct'][2]/100.0),
            length_edges_mm=(CLASS_THRESHOLDS['Di']['mm'][0], CLASS_THRESHOLDS['Di']['mm'][1], CLASS_THRESHOLDS['Di']['mm'][2])) if self.series_mm_full is not None else {}
        due_counts_abs = _classify_duennstellen_3x3(
            self.series_mm_full, mm_step,
            mean_factor_edges=(1.0 - CLASS_THRESHOLDS['Dü']['pct'][0]/100.0,
                               1.0 - CLASS_THRESHOLDS['Dü']['pct'][1]/100.0,
                               1.0 - CLASS_THRESHOLDS['Dü']['pct'][2]/100.0),
            length_edges_mm=(CLASS_THRESHOLDS['Dü']['mm'][0], CLASS_THRESHOLDS['Dü']['mm'][1], CLASS_THRESHOLDS['Dü']['mm'][2])) if self.series_mm_full is not None else {}
        di_counts_100m = _normalize_counts_per_100m(
            di_counts_abs,  full_len_mm) if full_len_mm else di_counts_abs
        due_counts_100m = _normalize_counts_per_100m(
            due_counts_abs, full_len_mm) if full_len_mm else due_counts_abs

        lines = []
        lines.append(
            f"Samples per line: {self._points_per_segment()} • Length per line: {SEGMENT_LEN_MM:.1f} mm × {int(getattr(self, 'num_turns_current', NUM_TURNS))}")
        lines.append(
            f"Total length (section): {TOTAL_LEN_MM:.1f} mm • Samples in section: {self._needed_points()}")
        lines.append("")
        lines.append("— Ausschnitt (2 m) —")
        lines.append(f"Mittel-Dicke: {mean_mm:.4f} mm ({mean_um:.1f} µm)")
        lines.append(f"Std. deviation: {std_mm:.4f} mm ({std_um:.2f} µm)")
        lines.append(f"CV: {cv_percent:.2f} %")
        lines.append(f"Min. Dicke: {min_mm:.4f} mm ({min_mm*1000:.1f} µm)")
        lines.append(f"Max. Dicke: {max_mm:.4f} mm ({max_mm*1000:.1f} µm)")
        core_mm, core_um = self._compute_core_thickness()
        lines.append(
            f"Kernband: {kb_lo_slice:.4f}–{kb_hi_slice:.4f} mm (±{band_delta_slice*1000.0:.1f} µm)")
        lines.append("")
        lines.append("— Gesamte Serie —")
        lines.append(f"Mittel-Dicke: {f_mean_mm:.4f} mm ({f_mean_um:.1f} µm)")
        lines.append(f"Std. deviation: {f_std_mm:.4f} mm ({f_std_um:.2f} µm)")
        lines.append(f"CV: {f_cv:.2f} %")
        lines.append(f"Min. Dicke: {f_min_mm:.4f} mm ({f_min_mm*1000:.1f} µm)")
        lines.append(f"Max. Dicke: {f_max_mm:.4f} mm ({f_max_mm*1000:.1f} µm)")
        core_mm, core_um = self._compute_core_thickness()
        lines.append(
            f"Kernband: {kb_lo_full:.4f}–{kb_hi_full:.4f} mm (±{band_delta_full*1000.0:.1f} µm)")
        lines.append("")
        lines.append("")
        lines.append("")

        try:
            self._update_graph_tab()
        except Exception:
            pass

        try:
            self._update_unevenness_tab()
        except Exception:
            pass

        lines.append(
            f"— Exzess-Kennzahlen (Basis: Median ± {getattr(self, 'sigma_factor', 1.0):g}σ) —")
        try:
            _met = getattr(self, "_metric_MET_tot", 0.0)
            _freq = getattr(self, "_metric_FREQ_tot", 0.0)
            _eai = getattr(self, "_metric_HKI", 0.0)
        except Exception:
            _met, _freq, _eai = 0.0, 0.0, 0.0
        lines.append(f"MET (µm): {_met:.3f}")
        lines.append(
            f"Frequenz (%): {_freq*100:.2f} "
            f"(thin: {getattr(self, '_metric_FREQ_L', 0.0)*100:.2f} %, "
            f"dick: {getattr(self, '_metric_FREQ_R', 0.0)*100:.2f} %)"
        )
        lines.append(f"HKI: {_eai:.4f}")
        try:
            # HAI auf Basis der vollen Serie in µm, robust z-standardisiert, Schwelle k = sigma_factor
            import numpy as _np
            k = float(getattr(self, 'sigma_factor', 1.0))
            series_um_full = _np.asarray(self.series_mm_full, dtype=float) * \
                1000.0 if self.series_mm_full is not None else _np.asarray(
                    [], dtype=float)
            hai_val = compute_hai(series_um_full, k=k, q=1.0)
        except Exception:
            hai_val = 0.0
        lines.append(
            f"HAI (k={getattr(self, 'sigma_factor', 1.0):g}σ): {hai_val:6.2f}")

        try:
            self.stats_box.setToolTip(
                f"""MET (Mean Excess Thickness): Average thickness of points outside the core band\n    – i.e. how much the yarn deviates from the stable range at the edges (in µm per point).\n    A high MET points to pronounced outliers (thick or thin sections).\n\nFrequency: share of measuring points outside the core band (in %).\n    It describes how often such outliers occur – \n    regardless of their size.\n\nHKI (Heberlein Kennzahl Index): dimensionless comparison value, calculated from the\n    sum of the excess areas relative to a robust range.\n    It combines frequency and size of the deviations into a single, \n    normalised value. A high HKI points to a restless or \n    inhomogeneous yarn profile, a low value to an even \n    and stable yarn.\n\nHAI (Heberlein ATY Index): dimensionless index independent of the titer, via robust z-scaling (median/MAD).\n    1) z = (y - median) / (1.4826*MAD)\n    2) excess only outside the core band: E = max(|z| - k, 0)\n    3) HAI = 100 × (share outside) × mean(E)\n    k is your σ factor, currently k = {getattr(self, 'sigma_factor', 1.0):g}.\n\nDefinition Kernband:\n    Median ± {getattr(self, 'sigma_factor', 1.0):g}× standard deviation (σ) of the thickness in µm.\n\nUse:\n    - MET → size of single deviations\n    - Frequency → how often deviations occur\n    - HKI → overall quality, normalised to a robust range\n    - HAI → comparing ATY yarns (dimensionless, independent of fineness)\n""")
        except Exception:
            pass

        try:
            self.stats_box.setText("\n".join(lines))
        except Exception:
            pass

        try:
            if full_len_mm:
                self._fill_matrix(
                    self.table_di, di_counts_100m, COLOR_STATE.di_colors, True)
                self._fill_matrix(
                    self.table_due, due_counts_100m, COLOR_STATE.due_colors, False)
                # Checkboxes direkt in den Kästchen ergänzen
                try:
                    self._inject_checkboxes_into_matrix(self.table_di, True)
                    self._inject_checkboxes_into_matrix(self.table_due, False)
                except Exception:
                    pass
        except Exception:
            pass

    def _emit_fractional_limits(self, xlim, ylim):
        fx0, fx1 = self.canvas.full_xlim
        fy0, fy1 = self.canvas.full_ylim

        def to_frac(l0, l1, f0, f1):
            span = (f1-f0) if (f1-f0) != 0 else 1.0
            return ((l0-f0)/span, (l1-f0)/span)
        frac_xlim = to_frac(xlim[0], xlim[1], fx0, fx1)
        frac_ylim = to_frac(ylim[0], ylim[1], fy0, fy1)
        def clamp(p): return (
            max(0.0, min(1.0, p[0])), max(0.0, min(1.0, p[1])))
        frac_xlim_c = clamp(frac_xlim)
        frac_ylim_c = clamp(frac_ylim)
        self.limitsFractionChanged.emit(self, frac_xlim_c, frac_ylim_c)
        if not self._applying_sync:
            SYNC_HUB.broadcast.emit(self._sync_id, frac_xlim_c, frac_ylim_c)

    def apply_fractional_limits(self, frac_xlim, frac_ylim):
        self.canvas.apply_fractional_limits(frac_xlim, frac_ylim)

    def reset_zoom(self):
        self.canvas.full_view()

    def _on_yref_broadcast(self, sender_id, ref_val):
        # Ignore own broadcast
        if sender_id == self._sync_id:
            return
        try:
            self._row_spacing_ref = float(
                ref_val) if ref_val is not None else None
        except Exception:
            self._row_spacing_ref = None
        # Redraw with new spacing ref
        self.update_plot_only()

    def _on_yfull_broadcast(self, sender_id, full_ylim):
        # Ignore if from self
        if sender_id == self._sync_id:
            return
        # Preserve current fractional window and x-frac
        fx0, fx1 = self.canvas.full_xlim
        fy0, fy1 = self.canvas.full_ylim
        cx0, cx1 = self.canvas.ax.get_xlim()
        cy0, cy1 = self.canvas.ax.get_ylim()

        def to_frac(l0, l1, f0, f1):
            span = (f1-f0) if (f1-f0) != 0 else 1.0
            return ((l0-f0)/span, (l1-f0)/span)

        frac_xlim = to_frac(cx0, cx1, fx0, fx1)
        frac_ylim = to_frac(cy0, cy1, fy0, fy1)

        # Apply new common full Y-limits, keep X full limits
        self.canvas.set_full_limits(self.canvas.full_xlim, tuple(full_ylim))
        # Re-apply previous fractional limits on new full to preserve current view
        self.apply_fractional_limits(frac_xlim, frac_ylim)

    def _on_sync_broadcast(self, sender_id, frac_xlim, frac_ylim):
        # Ignore if broadcast originates from self
        if sender_id == self._sync_id:
            return
        # Apply without re-broadcasting
        self._applying_sync = True
        try:
            self.apply_fractional_limits(frac_xlim, frac_ylim)
        finally:
            self._applying_sync = False


def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = GarnPanel("Garnspiegel")
    w.resize(1280, 720)
    w.show()    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()