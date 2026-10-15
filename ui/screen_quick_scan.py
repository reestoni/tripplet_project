# ui/screen_quick_scan.py
from __future__ import annotations
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QLineEdit, QTableWidget,
    QTableWidgetItem, QMessageBox, QAbstractItemView, QSizePolicy,
    QScrollArea, QHeaderView, QTabWidget, QListWidget, QListWidgetItem,
    QTextEdit,
)
from PySide6.QtCore import Qt, QSize, QRectF, QPointF, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QColor, QPainter, QPen, QBrush, QFont, QPainterPath

from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from db.connection import fetch_all, execute, execute_insert
import app_meta


def _is_advisor_enabled() -> bool:
    """Advisor Tab sichtbar wenn tbluser.api_key_enc gesetzt ist.
    Gecacht pro Session — kein DB-Call bei jedem Screen-Aufbau.
    """
    cache = _is_advisor_enabled.__dict__
    username = app_meta.current_user.get("username", "")
    if cache.get("_username") == username:
        return cache.get("_result", False)
    try:
        from db.connection import fetch_all
        result = bool(
            username and
            (rows := fetch_all("SELECT api_key_enc FROM tbluser WHERE Username = %s", [username]))
            and rows[0].get("api_key_enc")
        )
    except Exception:
        result = False
    cache["_username"] = username
    cache["_result"]   = result
    return result


OPERATORS      = ["=", ">=", "<=", "between"]
OP_LABELS      = {"=": "=", ">=": ">=", "<=": "<=", "between": "zwischen"}
EQUAL_DEFAULTS = {"titer", "filamente"}

TARGET_TYPES   = ["must", "weighted", "distance"]
TARGET_LABELS  = {"must": "Must", "weighted": "Weighted", "distance": "Distance"}
OPTIMUM_LABELS = {"min": "Min optimal", "max": "Max optimal", "mid": "Mitte optimal"}


class NumericItem(QTableWidgetItem):
    """QTableWidgetItem mit korrekter numerischer Sortierung."""
    def __init__(self, text: str, numeric_val=None):
        super().__init__(text)
        self._num = numeric_val

    def __lt__(self, other):
        try:
            a = self._num if self._num is not None else float(self.text().replace("%",""))
            b = other._num if hasattr(other, "_num") and other._num is not None else float(other.text().replace("%",""))
            return a < b
        except (ValueError, TypeError):
            return self.text() < other.text()


# ---------------------------------------------------------------------------
# ScoreBarChart – horizontale Balken, Top 20 nach Score
# ---------------------------------------------------------------------------
class ScoreBarChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []   # list of (label, score 0-100)
        self.setMinimumHeight(200)

    def set_data(self, results: list, max_items: int = 25, has_score: bool = True):
        """results: Liste von Dicts mit 'experiment_id', 'trial_nr', '_score'"""
        self._data      = []
        self._has_score = has_score
        for r in results[:max_items]:
            score = r.get("_score")
            if not has_score:
                score = None  # kein Score → neutraler Balken
            label = f"{r.get('experiment_id','?')} T{r.get('trial_nr','?')} {r.get('jet_name') or ''}"
            self._data.append((label, score))
        self.setMinimumHeight(max(200, len(self._data) * 28 + 40))
        self.update()

    def paintEvent(self, event):
        if not self._data:
            p = QPainter(self)
            p.setPen(QColor("#888"))
            p.drawText(self.rect(), Qt.AlignCenter, "Keine Daten")
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        W, H     = self.width(), self.height()
        margin_l = 220  # Platz für Labels
        margin_r = 60
        margin_t = 20
        margin_b = 20
        bar_h    = 20
        spacing  = 8
        chart_w  = W - margin_l - margin_r

        font = QFont()
        font.setPointSize(9)
        p.setFont(font)

        for i, (label, score) in enumerate(self._data):
            y = margin_t + i * (bar_h + spacing)

            # Label – heller und fett für besseren Kontrast
            font_lbl = QFont()
            font_lbl.setPointSize(9)
            font_lbl.setBold(True)
            p.setFont(font_lbl)
            p.setPen(QColor("#000000"))
            p.drawText(0, y, margin_l - 6, bar_h, Qt.AlignRight | Qt.AlignVCenter,
                       label[:35])
            p.setFont(font)  # zurück auf Normal-Font

            # Hintergrund
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#2a2a2a"))
            p.drawRoundedRect(QRectF(margin_l, y, chart_w, bar_h), 3, 3)

            if score is None:
                # Kein Score (nur Filter/Must/Distance) → neutraler voller Balken
                p.setBrush(QColor("#58a6ff"))
                p.drawRoundedRect(QRectF(margin_l, y, chart_w, bar_h), 3, 3)
                p.setPen(QColor("#fff"))
                p.drawText(int(margin_l + 4), y, margin_r - 4, bar_h,
                           Qt.AlignLeft | Qt.AlignVCenter, "–")
            else:
                # Balken mit Score-Farbe
                bw = max(2, chart_w * score / 100)
                if score >= 80:   c = QColor("#3fb950")
                elif score >= 50: c = QColor("#e8a838")
                else:             c = QColor("#f78166")
                p.setBrush(c)
                p.drawRoundedRect(QRectF(margin_l, y, bw, bar_h), 3, 3)
                p.setPen(QColor("#fff"))
                p.drawText(int(margin_l + bw + 4), y, margin_r - 4, bar_h,
                           Qt.AlignLeft | Qt.AlignVCenter, f"{score:.0f}%")


# ---------------------------------------------------------------------------
# ParallelCoordChart – parallele Koordinaten
# ---------------------------------------------------------------------------
class ParallelCoordChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._results   = []
        self._axes      = []   # list of (key, label)
        self.setMinimumHeight(300)

    def set_data(self, results: list, axes: list):
        """axes: list of (field_key, label)"""
        self._results = results[:50]
        self._axes    = axes
        self.update()

    def paintEvent(self, event):
        if not self._results or not self._axes:
            p = QPainter(self)
            p.setPen(QColor("#888"))
            p.drawText(self.rect(), Qt.AlignCenter,
                       "Keine Daten oder keine Weighted/Distance Targets definiert")
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        W, H      = self.width(), self.height()
        margin_l  = 40
        margin_r  = 40
        margin_t  = 40
        margin_b  = 50
        chart_w   = W - margin_l - margin_r
        chart_h   = H - margin_t - margin_b
        n_axes    = len(self._axes)

        if n_axes < 2:
            p.setPen(QColor("#888"))
            p.drawText(self.rect(), Qt.AlignCenter, "At least 2 fields required")
            return

        # Achsen-X-Positionen
        ax_x = [margin_l + i * chart_w // (n_axes - 1) for i in range(n_axes)]

        # Min/Max pro Achse
        ranges = {}
        for key, _ in self._axes:
            vals = [r.get(key) for r in self._results if r.get(key) is not None]
            if vals:
                mn, mx = min(vals), max(vals)
                ranges[key] = (mn, mx if mx != mn else mn + 1)
            else:
                ranges[key] = (0, 1)

        font = QFont()
        font.setPointSize(8)
        p.setFont(font)

        # Linien zeichnen
        max_score = max((r.get("_score") or 0) for r in self._results) or 100

        for res in self._results:
            score = res.get("_score")
            if score is not None:
                t = score / 100
                r_col = int(247 * (1 - t) + 63 * t)
                g_col = int(129 * (1 - t) + 185 * t)
                b_col = int(102 * (1 - t) + 80 * t)
                color = QColor(r_col, g_col, b_col, 160)
            else:
                color = QColor("#58a6ff", 120)

            pen = QPen(color, 1.5)
            p.setPen(pen)

            points = []
            valid  = True
            for i, (key, _) in enumerate(self._axes):
                val = res.get(key)
                if val is None:
                    valid = False
                    break
                lo, hi = ranges[key]
                norm = (val - lo) / (hi - lo)
                x = ax_x[i]
                y = margin_t + chart_h - int(norm * chart_h)
                points.append(QPointF(x, y))

            if valid and len(points) >= 2:
                path = QPainterPath(points[0])
                for pt in points[1:]:
                    path.lineTo(pt)
                p.drawPath(path)

        # Achsen zeichnen
        for i, (key, label) in enumerate(self._axes):
            x  = ax_x[i]
            lo, hi = ranges[key]

            # Achsenlinie
            p.setPen(QPen(QColor("#555"), 1))
            p.drawLine(x, margin_t, x, margin_t + chart_h)

            # Label oben
            p.setPen(QColor("#ccc"))
            font.setPointSize(8)
            p.setFont(font)
            p.drawText(x - 50, margin_t - 30, 100, 25,
                       Qt.AlignCenter, label[:18])

            # Min/Max Werte
            p.setPen(QColor("#888"))
            font.setPointSize(7)
            p.setFont(font)
            p.drawText(x - 25, margin_t + chart_h + 4, 50, 16,
                       Qt.AlignCenter, f"{lo:.1f}")
            p.drawText(x - 25, margin_t - 16, 50, 16,
                       Qt.AlignCenter, f"{hi:.1f}")


# ---------------------------------------------------------------------------
# FilterRow  – nur für Filter-Sektion (immer Must)
# Unterstützt data_type='lookup' → Multiselect-Liste statt Operator+Zahlen
# ---------------------------------------------------------------------------
class FilterRow(QWidget):
    def __init__(self, field: dict, on_remove=None, parent=None):
        super().__init__(parent)
        self._field     = field
        self._on_remove = on_remove
        self._is_lookup = (field.get("data_type") == "lookup")
        self._build()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(6)

        unit  = self._field.get("unit") or ""
        label = self._field.get("field_label", "")
        lbl   = QLabel(f"{label} [{unit}]" if unit else label)
        lbl.setFixedWidth(160)
        lbl.setStyleSheet("font-size:12px;")
        lay.addWidget(lbl)

        if self._is_lookup:
            self._build_lookup_row(lay)
        else:
            self._build_numeric_row(lay)

        lay.addStretch()
        btn = QPushButton("✕")
        btn.setObjectName("GreenBtn")
        btn.setFixedSize(26, 26)
        btn.clicked.connect(lambda: self._on_remove(self) if callable(self._on_remove) else None)
        lay.addWidget(btn)

    def _build_numeric_row(self, row):
        """Operator + Zahlenfelder für numerische Felder."""
        self._op = QComboBox()
        for op in OPERATORS:
            self._op.addItem(OP_LABELS[op], op)
        self._op.setFixedWidth(85)
        fk = self._field.get("field_key", "")
        self._op.setCurrentIndex(0 if fk in EQUAL_DEFAULTS else 3)
        self._op.currentIndexChanged.connect(self._sync)
        row.addWidget(self._op)

        self._v1 = QLineEdit()
        self._v1.setPlaceholderText("Wert")
        self._v1.setFixedWidth(65)
        row.addWidget(self._v1)

        self._lbl_bis = QLabel("bis")
        self._lbl_bis.setStyleSheet("color:#888;font-size:11px;")
        self._lbl_bis.setFixedWidth(16)
        row.addWidget(self._lbl_bis)

        self._v2 = QLineEdit()
        self._v2.setPlaceholderText("Wert")
        self._v2.setFixedWidth(65)
        row.addWidget(self._v2)

        # Tension
        self._v_t = None
        if self._field.get("tension_filter") is not None:
            row.addWidget(QLabel("@", styleSheet="color:#aaa;font-size:10px;"))
            self._v_t = QLineEdit()
            self._v_t.setFixedWidth(36)
            self._v_t.setText(str(self._field["tension_filter"]))
            row.addWidget(self._v_t)

        self._sync()

    def _build_lookup_row(self, lay):
        """Kompaktes Multiselect für Lookup-Felder: Button öffnet Popup-Liste."""
        self._selected_ids    = []
        self._selected_labels = []

        self._btn_select = QPushButton("Alle / Auswahl ▾")
        self._btn_select.setFixedHeight(24)
        self._btn_select.setMinimumWidth(160)
        self._btn_select.setStyleSheet(
            "QPushButton { background:#1e1e2e; color:#ddd; border:1px solid #444; "
            "border-radius:3px; font-size:11px; padding:0 6px; text-align:left; }"
            "QPushButton:hover { border-color:#39A650; }"
        )
        self._btn_select.clicked.connect(self._open_lookup_popup)
        lay.addWidget(self._btn_select)

        # Dummy-Attribute damit get_filter() nicht crasht
        self._op      = None
        self._v1      = None
        self._v2      = None
        self._lbl_bis = None
        self._v_t     = None

        # Lookup-Optionen vorladen
        self._lookup_options = self._load_lookup_options()

    def _load_lookup_options(self) -> list:
        """Gibt [(id, label), ...] zurück."""
        lookup_table = self._field.get("lookup_table")
        col_value    = self._field.get("lookup_col_value") or "ID"
        col_label    = self._field.get("lookup_col_label") or col_value
        if not lookup_table:
            return []
        try:
            rows = fetch_all(
                f"SELECT `{col_value}` AS val, `{col_label}` AS lbl "
                f"FROM `{lookup_table}` ORDER BY `{col_label}`", []
            )
            return [(r["val"], str(r["lbl"] or "")) for r in rows]
        except Exception:
            return []

    def _open_lookup_popup(self):
        """Zeigt ein kleines Popup-Fenster mit Checkboxen."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox, QCheckBox, QScrollArea

        dlg = QDialog(self)
        dlg.setWindowTitle(f"{self._field.get('field_label', '')} – select")
        dlg.setMinimumWidth(220)
        dlg.setMaximumHeight(350)

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(4, 4, 4, 4)
        inner_lay.setSpacing(2)

        self._checkboxes = []
        for val, lbl in self._lookup_options:
            cb = QCheckBox(lbl)
            cb.setProperty("lookup_val", val)
            cb.setChecked(val in self._selected_ids)
            cb.setStyleSheet("font-size:12px;")
            inner_lay.addWidget(cb)
            self._checkboxes.append(cb)

        inner_lay.addStretch()
        scroll.setWidget(inner)
        lay.addWidget(scroll, 1)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)

        if dlg.exec():
            self._selected_ids    = []
            self._selected_labels = []
            for cb in self._checkboxes:
                if cb.isChecked():
                    self._selected_ids.append(cb.property("lookup_val"))
                    self._selected_labels.append(cb.text())
            self._update_btn_text()

    def _update_btn_text(self):
        if not self._selected_labels:
            self._btn_select.setText("Alle / Auswahl ▾")
        elif len(self._selected_labels) <= 2:
            self._btn_select.setText(", ".join(self._selected_labels) + " ▾")
        else:
            self._btn_select.setText(f"{len(self._selected_labels)} selected ▾")

    def _sync(self):
        if self._is_lookup:
            return
        between = self._op.currentData() == "between"
        self._lbl_bis.setVisible(between)
        self._v2.setVisible(between)

    def get_filter(self) -> Optional[dict]:
        if self._is_lookup:
            if not self._selected_ids:
                return None
            return {
                "field":       dict(self._field),
                "operator":    "in",
                "value1":      list(self._selected_ids),
                "value2":      None,
                "target_type": "must",
            }
        # Numerisch
        v1t = self._v1.text().strip()
        if not v1t:
            return None
        try:
            v1 = float(v1t)
        except ValueError:
            return None
        op = self._op.currentData()
        v2 = None
        if op == "between":
            v2t = self._v2.text().strip()
            if not v2t:
                return None
            try:
                v2 = float(v2t)
            except ValueError:
                return None
        field = dict(self._field)
        if self._v_t is not None:
            try:
                field["tension_filter"] = float(self._v_t.text().strip())
            except ValueError:
                pass
        return {
            "field": field, "operator": op,
            "value1": v1, "value2": v2,
            "target_type": "must",
        }


# ---------------------------------------------------------------------------
# TargetRow  – mit Typ-Auswahl: must / weighted / distance
# ---------------------------------------------------------------------------
class TargetRow(QWidget):
    def __init__(self, field: dict, on_remove=None, parent=None):
        super().__init__(parent)
        self._field     = field
        self._on_remove = on_remove
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 2, 0, 2)
        outer.setSpacing(2)

        # --- Zeile 1: Feldname + Operator/Wert + Typ ---
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        unit  = self._field.get("unit") or ""
        label = self._field.get("field_label", "")
        lbl   = QLabel(f"{label} [{unit}]" if unit else label)
        lbl.setFixedWidth(160)
        lbl.setStyleSheet("font-size:12px;")
        row1.addWidget(lbl)

        self._op = QComboBox()
        for op in OPERATORS:
            self._op.addItem(OP_LABELS[op], op)
        self._op.setFixedWidth(85)
        self._op.setCurrentIndex(3)  # default: zwischen
        self._op.currentIndexChanged.connect(self._sync)
        row1.addWidget(self._op)

        self._v1 = QLineEdit()
        self._v1.setPlaceholderText("Wert")
        self._v1.setFixedWidth(65)
        row1.addWidget(self._v1)

        self._lbl_bis = QLabel("bis")
        self._lbl_bis.setStyleSheet("color:#888;font-size:11px;")
        self._lbl_bis.setFixedWidth(16)
        row1.addWidget(self._lbl_bis)

        self._v2 = QLineEdit()
        self._v2.setPlaceholderText("Wert")
        self._v2.setFixedWidth(65)
        row1.addWidget(self._v2)

        # Tension
        self._v_t = None
        if self._field.get("tension_filter") is not None:
            row1.addWidget(QLabel("@", styleSheet="color:#aaa;font-size:10px;"))
            self._v_t = QLineEdit()
            self._v_t.setFixedWidth(36)
            self._v_t.setText(str(self._field["tension_filter"]))
            row1.addWidget(self._v_t)

        # Typ-Dropdown
        self._type_combo = QComboBox()
        for t in TARGET_TYPES:
            self._type_combo.addItem(TARGET_LABELS[t], t)
        self._type_combo.setFixedWidth(90)
        self._type_combo.currentIndexChanged.connect(self._sync)
        row1.addWidget(self._type_combo)

        row1.addStretch()
        btn = QPushButton("✕")
        btn.setObjectName("GreenBtn")
        btn.setFixedSize(26, 26)
        btn.clicked.connect(lambda: self._on_remove(self) if callable(self._on_remove) else None)
        row1.addWidget(btn)
        outer.addLayout(row1)

        # --- Zeile 2: Weighted-Optionen (Zielwert + Richtung + Gewicht) ---
        self._row2 = QWidget()
        row2_lay = QHBoxLayout(self._row2)
        row2_lay.setContentsMargins(166, 0, 0, 0)
        row2_lay.setSpacing(6)

        row2_lay.addWidget(QLabel("Ziel:", styleSheet="color:#aaa;font-size:11px;"))
        self._target_val = QLineEdit()
        self._target_val.setFixedWidth(55)
        self._target_val.setPlaceholderText("Zielwert")
        row2_lay.addWidget(self._target_val)

        row2_lay.addWidget(QLabel("Richtung:", styleSheet="color:#aaa;font-size:11px;"))
        self._direction = QComboBox()
        self._direction.addItem("higher is better", "higher")
        self._direction.addItem("tiefer ist besser", "lower")
        self._direction.addItem("genau treffen",     "exact")
        self._direction.setFixedWidth(130)
        row2_lay.addWidget(self._direction)

        row2_lay.addWidget(QLabel("Gewicht:", styleSheet="color:#aaa;font-size:11px;"))
        self._weight = QLineEdit()
        self._weight.setFixedWidth(45)
        self._weight.setText("1.0")
        row2_lay.addWidget(self._weight)
        row2_lay.addStretch()
        outer.addWidget(self._row2)

        self._sync()

    def _sync(self):
        between  = self._op.currentData() == "between"
        weighted = self._type_combo.currentData() == "weighted"
        self._lbl_bis.setVisible(between)
        self._v2.setVisible(between)
        self._row2.setVisible(weighted)

    def get_filter(self) -> Optional[dict]:
        v1t = self._v1.text().strip()
        if not v1t:
            return None
        try:
            v1 = float(v1t)
        except ValueError:
            return None
        op  = self._op.currentData()
        v2  = None
        if op == "between":
            v2t = self._v2.text().strip()
            if not v2t:
                return None
            try:
                v2 = float(v2t)
            except ValueError:
                return None

        field = dict(self._field)
        if self._v_t is not None:
            try:
                field["tension_filter"] = float(self._v_t.text().strip())
            except ValueError:
                pass

        target_type = self._type_combo.currentData()
        weight      = 1.0
        direction   = "higher"
        target_val  = None

        if target_type == "weighted":
            try:
                weight = float(self._weight.text().strip())
            except ValueError:
                weight = 1.0
            direction = self._direction.currentData()
            try:
                target_val = float(self._target_val.text().strip())
            except ValueError:
                target_val = None

        return {
            "field":       field,
            "operator":    op,
            "value1":      v1,
            "value2":      v2,
            "target_type": target_type,
            "weight":      weight,
            "direction":   direction,
            "target_val":  target_val,
        }


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------
def _score_weighted(val: float, f: dict) -> float:
    """Score 0.0–1.0 basierend auf Zielwert und Richtung.

    direction='higher': je höher desto besser, Zielwert = 100%
    direction='lower':  je tiefer desto besser, Zielwert = 100%
    direction='exact':  genau Zielwert = 100%, Abweichung = Score fällt

    Normalisierung: der must-Bereich (value1/value2) dient als Skala.
    Werte innerhalb des Must-Bereichs bekommen Score 0–100%,
    Werte ausserhalb können über 100% hinausgehen (werden auf 100% gecapped).
    """
    target_val = f.get("target_val")
    direction  = f.get("direction", "higher")
    op         = f["operator"]
    v1         = f["value1"]
    v2         = f.get("value2")

    # Referenzbereich für Normalisierung
    if op == "between" and v2 is not None:
        lo, hi = v1, v2
    elif op == ">=":
        lo, hi = v1, v1 * 2 if v1 > 0 else 100.0
    elif op == "<=":
        lo, hi = 0.0, v1
    else:
        lo = hi = v1

    span = hi - lo if hi != lo else 1.0

    # Zielwert: falls nicht angegeben, aus Bereich ableiten
    if target_val is None:
        if direction == "higher":   target_val = hi
        elif direction == "lower":  target_val = lo
        else:                       target_val = (lo + hi) / 2

    if direction == "higher":
        # val >= target → 100%, linear abfallend unter target bis lo → 0%
        if val >= target_val:
            return 1.0
        elif val <= lo:
            return 0.0
        else:
            return (val - lo) / (target_val - lo) if target_val != lo else 1.0

    elif direction == "lower":
        # val <= target → 100%, linear abfallend über target bis hi → 0%
        if val <= target_val:
            return 1.0
        elif val >= hi:
            return 0.0
        else:
            return (hi - val) / (hi - target_val) if hi != target_val else 1.0

    else:  # exact
        # Abstand zum Zielwert, normalisiert auf Bereichsbreite
        dist = abs(val - target_val)
        return max(0.0, 1.0 - dist / (span / 2))


# ---------------------------------------------------------------------------
# QuickScanEvaluator
# ---------------------------------------------------------------------------
# JOIN-Resolver: liest tblsmartchartjoinpath und erzeugt EXISTS-Snippets
# ---------------------------------------------------------------------------
class JoinResolver:
    """Cached JOIN-Pfade aus tblsmartchartjoinpath.
    Unterstützt direkte TrialID-Verbindungen und mehrstufige Pfade via
    tbltrialseries / tblexperimente.
    """
    # Tabellen die direkt t.ID = source.TrialID verknüpft sind
    _DIRECT_TRIAL = frozenset()

    # Anchor-Alias im Haupt-SELECT
    _ANCHORS = {
        "tbltrial":       ("t",  "t.ID"),
        "tbltrialseries": ("ts", "ts.ID"),
        "tblexperimente": ("e",  "e.ID"),
        "tblyarn":        None,   # Sonderfall: via tsy
        "tbltrialsettings": None, # Sonderfall: direkt via TrialID
    }

    def __init__(self):
        self._paths: dict[str, str] = {}   # from_table → JoinSQL (FromTable=source → ToTable=tbltrial)
        self._loaded = False

    def ensure_loaded(self):
        if self._loaded:
            return
        try:
            rows = fetch_all(
                "SELECT FromTable, ToTable, JoinSQL FROM tblsmartchartjoinpath WHERE IsActive=1",
                []
            )
            for r in rows:
                frm = r["FromTable"].lower()
                to  = r["ToTable"].lower()
                # Wir interessieren uns für Pfade die zu tbltrial führen
                if to == "tbltrial":
                    self._paths[frm] = r["JoinSQL"]
                # Pfad von tbltrialseries → tblexperimente (für Lookup)
                if frm == "tbltrialseries" and to == "tblexperimente":
                    self._paths["_ts_to_exp"] = r["JoinSQL"]
        except Exception:
            pass
        self._loaded = True

    def get_exists_snippet(self, source_table: str, col: str, alias: str = "ax") -> str | None:
        """Gibt einen EXISTS-SQL-Snippet zurück der source_table.col über t.ID verknüpft.
        alias: Table-Alias im EXISTS-Subquery.
        Gibt None zurück wenn kein Pfad bekannt.
        """
        self.ensure_loaded()
        tbl = source_table.lower()

        # Direkt via TrialID (alle tbllabor* und tbltrialsettings)
        if tbl in self._paths:
            join_sql = self._paths[tbl]
            # JoinSQL ist z.B. "LEFT JOIN tbllabordtyomat ON tbllabordtyomat.TrialID = tbltrial.ID"
            # Wir brauchen daraus: EXISTS (SELECT 1 FROM tbllabordtyomat ax WHERE ax.TrialID = t.ID AND ax.`col` {cond})
            return f"EXISTS (SELECT 1 FROM `{source_table}` {alias} WHERE {alias}.TrialID = t.ID AND {{cond}})"

        # tbltrial direkt
        if tbl == "tbltrial":
            return "{{cond_direct}}"  # wird als direktes WHERE-Fragment behandelt

        # tblyarn via tbltrialsettings
        if tbl == "tblyarn":
            return (f"EXISTS (SELECT 1 FROM tbltrialsettings tset_ax "
                    f"JOIN `{source_table}` {alias} ON {alias}.ID = tset_ax.YarnID "
                    f"WHERE tset_ax.TrialID = t.ID AND {{cond}})")

        # tblexperimente via ts.ExperimentID
        if tbl == "tblexperimente":
            return "{{cond_exp}}"  # Sonderfall: ts.ExperimentID IN (...)

        return None

    def known_tables(self) -> list[str]:
        """Alle Tabellen für die ein JOIN-Pfad zu tbltrial bekannt ist."""
        self.ensure_loaded()
        base = list(self._paths.keys())
        extra = ["tbltrial", "tblyarn", "tblexperimente", "tbltrialsettings"]
        seen = set()
        result = []
        for t in base + extra:
            if t not in seen and not t.startswith("_"):
                seen.add(t)
                result.append(t)
        return sorted(result)


# Globale Instanz – einmalig geladen
_join_resolver = JoinResolver()


# ---------------------------------------------------------------------------
# Ad-hoc Feld Dialog: wählt Tabelle + Spalte aus INFORMATION_SCHEMA
# ---------------------------------------------------------------------------
class AdhocFieldDialog:
    """Öffnet einen Dialog zur Auswahl eines beliebigen DB-Feldes.
    Gibt ein field-Dict zurück (kompatibel mit FilterRow/TargetRow).
    _adhoc=True markiert das Feld als nicht in tblRequirementField gespeichert.
    """

    # Tabellen-Whitelist: nur sinnvolle Tabellen anbieten
    ALLOWED_TABLES = [
        "tbltrial",
        "tbltrialseries",
        "tbltrialsettings",
        "tblexperimente",
        "tblyarn",
        "tbllaboritematlab",
        "tbllaboritematplus",
        "tbllabordtyomat",
        "tbllabortiter",
        "tbllaborstatimatds",
        "tbllaborstatimatm",
        "tbllaborwaterbath",
        "tbllaboratyshrinkage",
        "tbllaboratyomat",
        "tbllaborekb",
        "tbllaborheissluftschrumpf",
        "tbllaborkochschrumpf",
        "tbllaborrapid600",
        "tbljets",
        "tbljetrohling",
    ]

    # Spalten die systemisch sind und nicht als Felder angeboten werden
    _SKIP_COLS = frozenset({
        "ID", "TrialID", "TrialSeriesID", "ExperimentID", "UserID", "User",
        "Timestamp", "GlobalID", "JetID", "HousingID", "WettingHeadID",
        "MachineID", "CreatedBy", "BacklogStatusID", "BacklogOwner",
        "OriginalJoker", "Rohling", "Hersteller", "JetGroupID", "JetTypeID",
        "Serie", "Wirbelkammer", "Luftkanalform", "YarnChannelShape",
        "KonusForm", "Werkstoff", "YarnID", "Garntyp", "Material",
        "YarnGroupID", "Maschine", "Produktgruppe", "Bestellungstyp",
        "ExperimentRequestID",
    })

    @staticmethod
    def open(parent) -> dict | None:
        """Öffnet den Dialog. Gibt field-Dict oder None zurück."""
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLabel,
            QComboBox, QLineEdit, QDialogButtonBox, QCheckBox,
        )

        dlg = QDialog(parent)
        dlg.setWindowTitle("Select ad-hoc field from database")
        dlg.setMinimumWidth(440)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        lay.addWidget(QLabel(
            "Select a table and column. The field will be used directly.\n"
            "und bei Bedarf automatisch in tblRequirementField registriert.",
            styleSheet="color:#aaa; font-size:11px;"
        ))

        # Tabellen-Dropdown
        row_tbl = QHBoxLayout()
        row_tbl.addWidget(QLabel("Tabelle:"))
        combo_tbl = QComboBox()
        combo_tbl.setMinimumWidth(260)
        _join_resolver.ensure_loaded()
        known = _join_resolver.known_tables()
        # Zeige nur Tabellen aus Whitelist, in der Reihenfolge der Whitelist
        for tbl in AdhocFieldDialog.ALLOWED_TABLES:
            if tbl in known or tbl in ("tbltrial", "tblyarn", "tblexperimente"):
                combo_tbl.addItem(tbl, tbl)
        row_tbl.addWidget(combo_tbl)
        row_tbl.addStretch()
        lay.addLayout(row_tbl)

        # Spalten-Dropdown
        row_col = QHBoxLayout()
        row_col.addWidget(QLabel("Spalte:     "))
        combo_col = QComboBox()
        combo_col.setMinimumWidth(260)
        row_col.addWidget(combo_col)
        row_col.addStretch()
        lay.addLayout(row_col)

        # Label (optional)
        row_lbl = QHBoxLayout()
        row_lbl.addWidget(QLabel("Label:      "))
        edit_lbl = QLineEdit()
        edit_lbl.setMinimumWidth(260)
        edit_lbl.setPlaceholderText("Leer lassen = Spaltenname verwenden")
        row_lbl.addWidget(edit_lbl)
        row_lbl.addStretch()
        lay.addLayout(row_lbl)

        # Einheit (optional)
        row_unit = QHBoxLayout()
        row_unit.addWidget(QLabel("Einheit:    "))
        edit_unit = QLineEdit()
        edit_unit.setMinimumWidth(260)
        edit_unit.setPlaceholderText("z.B.  %  /  knoten/m  /  cN/dtex")
        row_unit.addWidget(edit_unit)
        row_unit.addStretch()
        lay.addLayout(row_unit)

        # Tension-Filter (nur für Itemat-Tabellen)
        row_tens = QHBoxLayout()
        chk_tens = QCheckBox("Tension-Filter:")
        edit_tens = QLineEdit()
        edit_tens.setFixedWidth(70)
        edit_tens.setPlaceholderText("z.B. 1.3")
        edit_tens.setEnabled(False)
        chk_tens.toggled.connect(edit_tens.setEnabled)
        row_tens.addWidget(chk_tens)
        row_tens.addWidget(edit_tens)
        row_tens.addStretch()
        lay.addLayout(row_tens)

        # Spalten laden wenn Tabelle wechselt
        def _load_columns(idx):
            tbl = combo_tbl.itemData(idx)
            combo_col.clear()
            if not tbl:
                return
            try:
                cols = fetch_all(
                    "SELECT COLUMN_NAME, DATA_TYPE "
                    "FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s "
                    "ORDER BY ORDINAL_POSITION",
                    [tbl]
                )
                for c in cols:
                    cname = c["COLUMN_NAME"]
                    if cname in AdhocFieldDialog._SKIP_COLS:
                        continue
                    dtype = c["DATA_TYPE"]
                    combo_col.addItem(f"{cname}  [{dtype}]", cname)
            except Exception as ex:
                combo_col.addItem(f"Fehler: {ex}", None)

        combo_tbl.currentIndexChanged.connect(_load_columns)
        _load_columns(0)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)

        if not dlg.exec():
            return None

        tbl = combo_tbl.currentData()
        col = combo_col.currentData()
        if not tbl or not col:
            return None

        label = edit_lbl.text().strip() or col
        unit  = edit_unit.text().strip() or None
        tens  = None
        if chk_tens.isChecked():
            try:
                tens = float(edit_tens.text().strip())
            except ValueError:
                tens = None

        # field_key: eindeutig aus tabelle + spalte + optionalem tension
        key = f"adhoc__{tbl}__{col}"
        if tens is not None:
            key += f"__{str(tens).replace('.', '_')}"

        return {
            "field_id":              None,   # noch nicht in DB
            "field_key":             key,
            "field_label":           label,
            "source_table_primary":  tbl,
            "source_table_fallback": None,
            "source_column":         col,
            "tension_filter":        tens,
            "data_type":             "float",
            "unit":                  unit,
            "lookup_table":          None,
            "lookup_col_value":      None,
            "lookup_col_label":      None,
            "_adhoc":                True,
        }

    @staticmethod
    def ensure_registered(field: dict) -> int:
        """Stellt sicher dass das Ad-hoc-Feld in tblRequirementField existiert.
        Gibt field_id zurück. Führt UPSERT durch (INSERT wenn neu, SELECT wenn vorhanden).
        """
        key = field["field_key"]
        rows = fetch_all(
            "SELECT field_id FROM tblrequirementfield WHERE field_key = %s", [key]
        )
        if rows:
            fid = rows[0]["field_id"]
            field["field_id"] = fid
            return fid

        # execute_insert() statt execute()+separatem fetch_all('SELECT
        # LAST_INSERT_ID()') - Letzteres zieht sich unabhängig eine (nicht
        # notwendigerweise dieselbe) Connection aus dem Pool, siehe CLAUDE.md.
        fid = execute_insert(
            "INSERT INTO tblrequirementfield "
            "(field_key, field_label, source_table_primary, source_table_fallback, "
            " source_column, tension_filter, data_type, unit, is_active, sort_order) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,1,999)",
            [
                key,
                field["field_label"],
                field["source_table_primary"],
                field.get("source_table_fallback"),
                field["source_column"],
                field.get("tension_filter"),
                field.get("data_type", "float"),
                field.get("unit"),
            ]
        )
        field["field_id"] = fid
        return fid


# ---------------------------------------------------------------------------
class QuickScanEvaluator:

    def run(self, filter_list: list, target_list: list):
        """
        filter_list: Felder aus Filter-Sektion (immer must)
        target_list: Felder aus Target-Sektion (must/weighted/distance)
        """
        # Alle Filter sind must → EXISTS-Subqueries
        # Targets vom Typ must → ebenfalls EXISTS
        # Targets weighted/distance → nach Basis-Query per IN-Query auflösen

        must_targets    = [t for t in target_list if t["target_type"] == "must"]
        weighted_targets= [t for t in target_list if t["target_type"] == "weighted"]
        distance_targets= [t for t in target_list if t["target_type"] == "distance"]

        all_must = filter_list + must_targets

        # Lookup-Filter separat (IN-Logik)
        lookup_f = [f for f in all_must if f["field"].get("data_type") == "lookup"]
        non_lookup_must = [f for f in all_must if f["field"].get("data_type") != "lookup"]

        rows = self._base_query(non_lookup_must, lookup_f)
        if not rows:
            return [], weighted_targets, distance_targets

        # Lab-Werte für weighted + distance laden
        score_fields = weighted_targets + distance_targets
        if score_fields:
            trial_ids = [r["trial_id"] for r in rows]
            lab_map   = self._load_lab_values(trial_ids, score_fields)
            for row in rows:
                row.update(lab_map.get(row["trial_id"], {}))

        # Score berechnen – Trials mit NULL oder 0 für Target-Felder ausschliessen
        total_weight = sum(t["weight"] for t in weighted_targets) or 1.0
        scored_rows  = []
        for row in rows:
            skip  = False
            score = 0.0

            # Weighted: NULL oder 0 → ausschliessen
            for t in weighted_targets:
                key = t["field"]["field_key"]
                val = row.get(key)
                if val is None or val == 0:
                    skip = True
                    break
                contrib = _score_weighted(val, t) * t["weight"]
                score  += contrib
                # Teilscore speichern für Tabellen-Anzeige
                row[f"_contrib_{key}"] = contrib
            if skip:
                continue

            # Distance: NULL oder 0 → ausschliessen
            for t in distance_targets:
                key = t["field"]["field_key"]
                val = row.get(key)
                if val is None or val == 0:
                    skip = True
                    break
            if skip:
                continue

            row["_score"] = round((score / total_weight) * 100, 1) if weighted_targets else None
            scored_rows.append(row)

        # Sortieren: erst nach Score desc, dann nach Experiment
        scored_rows.sort(key=lambda r: (
            -(r["_score"] or 0),
            r.get("experiment_id", ""),
        ))

        return scored_rows[:500], weighted_targets, distance_targets

    # ---- SQL helpers -------------------------------------------------------

    def _cond(self, col, f):
        op, v1, v2 = f["operator"], f["value1"], f["value2"]
        if op == "=":       return f"{col} = %s",              [v1]
        if op == ">=":      return f"{col} >= %s",             [v1]
        if op == "<=":      return f"{col} <= %s",             [v1]
        if op == "between": return f"{col} BETWEEN %s AND %s", [v1, v2]
        return "1=1", []

    def _build_filter_clause(self, f, alias_counter: list) -> tuple[str, list]:
        """Generiert WHERE-Klausel für ein beliebiges Feld via JoinResolver.
        alias_counter: [int] – wird inplace hochgezählt für eindeutige Aliasse.
        Gibt (sql_fragment, params) zurück.
        """
        fld          = f["field"]
        col          = fld["source_column"]
        source_table = (fld.get("source_table_primary") or "").lower()
        tension      = fld.get("tension_filter")
        alias_counter[0] += 1
        alias = f"ax{alias_counter[0]}"

        # Lookup-Typ: IN (id1, id2, ...)
        if fld.get("data_type") == "lookup":
            selected_ids = f.get("value1") or []
            if not selected_ids:
                return "1=1", []
            placeholders = ",".join(["%s"] * len(selected_ids))
            if source_table == "tblyarn":
                sql = (f"EXISTS (SELECT 1 FROM tbltrialsettings tset_{alias} "
                       f"JOIN `{fld['source_table_primary']}` {alias} "
                       f"ON {alias}.ID = tset_{alias}.YarnID "
                       f"WHERE tset_{alias}.TrialID = t.ID "
                       f"AND {alias}.`{col}` IN ({placeholders}))")
            elif source_table == "tbltrial":
                sql = f"t.`{col}` IN ({placeholders})"
            elif source_table == "tblexperimente":
                sql = f"ts.ExperimentID IN ({placeholders})"
            else:
                sql = (f"EXISTS (SELECT 1 FROM `{fld['source_table_primary']}` {alias} "
                       f"WHERE {alias}.TrialID = t.ID AND {alias}.`{col}` IN ({placeholders}))")
            return sql, list(selected_ids)

        # Numerischer Filter
        # Only apply Tension filter to tables that actually have a Tension column.
        # t_cond is evaluated PER TABLE so the fallback table is checked independently.
        _TENSION_TABLES = {
            "tbllaboritematlab", "tbllaboritematplus",
            "tbllabordtyomat", "tbllaboratyomat",
        }

        def _t_cond_for(tbl_name: str, tbl_alias: str) -> str:
            if tension is not None and tbl_name.lower() in _TENSION_TABLES:
                return f" AND {tbl_alias}.`Tension` = {tension}"
            return ""

        t_cond = _t_cond_for(source_table, alias)

        if source_table == "tbltrial":
            cond, p = self._cond(f"t.`{col}`", f)
            return cond, p

        if source_table == "tblyarn":
            cond, p = self._cond(f"{alias}.`{col}`", f)
            sql = (f"EXISTS (SELECT 1 FROM tbltrialsettings tset_{alias} "
                   f"JOIN tblyarn {alias} ON {alias}.ID = tset_{alias}.YarnID "
                   f"WHERE tset_{alias}.TrialID = t.ID AND {cond})")
            return sql, p

        if source_table == "tbltrialseries":
            cond, p = self._cond(f"ts.`{col}`", f)
            return cond, p

        if source_table == "tblexperimente":
            cond, p = self._cond(f"e.`{col}`", f)
            return cond, p

        # Alle anderen: direkt via TrialID (tbllabor*, tbltrialsettings, ...)
        cond, p = self._cond(f"{alias}.`{col}`", f)
        sql = (f"EXISTS (SELECT 1 FROM `{fld['source_table_primary']}` {alias} "
               f"WHERE {alias}.TrialID = t.ID{t_cond} AND {cond})")

        # Fallback-Tabelle: tension guard evaluated independently for the fallback table
        fallback = fld.get("source_table_fallback")
        if fallback:
            alias2 = f"{alias}b"
            t_cond2 = _t_cond_for(fallback, alias2)
            cond2, p2 = self._cond(f"{alias2}.`{col}`", f)
            sql2 = (f"EXISTS (SELECT 1 FROM `{fallback}` {alias2} "
                    f"WHERE {alias2}.TrialID = t.ID{t_cond2} AND {cond2})")
            return f"({sql} OR {sql2})", p + p2

        return sql, p

    def _base_query(self, all_must, lookup_f=None):
        """Generische _base_query – nutzt JoinResolver für beliebige Tabellen.
        all_must: alle Filter + must-Targets (kombiniert).
        """
        params = []
        # Reference samples (customer originals) are not trials - never a hit.
        from db.trial_reference import exclude_references_sql
        where  = [exclude_references_sql("t")]
        alias_counter = [0]

        # Alle must-Filter generisch auflösen
        non_lookup = [f for f in all_must if f["field"].get("data_type") != "lookup"]
        for f in non_lookup:
            sql, p = self._build_filter_clause(f, alias_counter)
            where.append(sql)
            params.extend(p)

        # Lookup-Filter
        for f in (lookup_f or []):
            sql, p = self._build_filter_clause(f, alias_counter)
            if sql != "1=1":
                where.append(sql)
                params.extend(p)

        sql = """
            SELECT DISTINCT
                t.ID                AS trial_id,
                t.Versuchsnummer    AS trial_nr,
                ts.SeriesName       AS series_name,
                e.ExperimentID      AS experiment_id,
                e.ID                AS exp_pk,
                ts.ID               AS series_pk,
                j.Jet               AS jet_name,
                y.Name              AS yarn_name,
                y.Endtiter          AS titer,
                y.NumberOfFilaments AS filamente
            FROM tbltrial t
            JOIN tbltrialseries ts       ON ts.ID = t.TrialSeriesID
            JOIN tblexperimente e        ON e.ID  = ts.ExperimentID
            LEFT JOIN tbljets j          ON j.ID  = t.JetID
            LEFT JOIN tbltrialsettings tset ON tset.TrialID = t.ID AND tset.Ply = 'Ply 1'
            LEFT JOIN tblyarn y          ON y.ID  = tset.YarnID
        """
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY e.ExperimentID DESC, t.Versuchsnummer ASC LIMIT 500"

        return fetch_all(sql, params)

    def _load_lab_values(self, trial_ids, fields):
        """Lädt Werte für alle trial_ids. Unterstützt beliebige Tabellen via TrialID,
        tbltrial-direkt, tblyarn via tsy, tbltrialseries, tblexperimente.
        {tid: {key: val}}
        """
        if not trial_ids:
            return {}
        id_list = ",".join(str(i) for i in trial_ids)
        lab_map = {}

        for f in fields:
            fld     = f["field"]
            key     = fld["field_key"]
            col     = fld["source_column"]
            primary = fld["source_table_primary"]
            tbl     = primary.lower()
            fallback= fld.get("source_table_fallback")
            tension = fld.get("tension_filter")
            _TENSION_TABLES = {"tbllaboritematlab", "tbllaboritematplus"}
            t_cond  = (f" AND Tension = {tension}"
                       if tension is not None and tbl in _TENSION_TABLES
                       else "")

            if tbl == "tbltrial":
                rows = fetch_all(
                    f"SELECT ID AS TrialID, `{col}` AS val FROM `{primary}` "
                    f"WHERE ID IN ({id_list})", [])
            elif tbl == "tblyarn":
                rows = fetch_all(
                    f"SELECT t.ID AS TrialID, y.`{col}` AS val "
                    f"FROM tbltrial t "
                    f"JOIN tbltrialsettings tset ON tset.TrialID = t.ID "
                    f"JOIN tblyarn y ON y.ID = tset.YarnID "
                    f"WHERE t.ID IN ({id_list}) AND tset.YarnID IS NOT NULL", [])
            elif tbl in ("tbltrialseries", "tblexperimente"):
                # Join nötig
                if tbl == "tbltrialseries":
                    rows = fetch_all(
                        f"SELECT t.ID AS TrialID, ts.`{col}` AS val "
                        f"FROM tbltrial t "
                        f"JOIN tbltrialseries ts ON ts.ID = t.TrialSeriesID "
                        f"WHERE t.ID IN ({id_list})", [])
                else:
                    rows = fetch_all(
                        f"SELECT t.ID AS TrialID, e.`{col}` AS val "
                        f"FROM tbltrial t "
                        f"JOIN tbltrialseries ts ON ts.ID = t.TrialSeriesID "
                        f"JOIN tblexperimente e ON e.ID = ts.ExperimentID "
                        f"WHERE t.ID IN ({id_list})", [])
            else:
                # Standard: TrialID-Direkt (alle tbllabor*, tbltrialsettings)
                rows = fetch_all(
                    f"SELECT TrialID, `{col}` AS val FROM `{primary}` "
                    f"WHERE TrialID IN ({id_list}){t_cond}", [])

            found = set()
            for r in rows:
                if r["val"] is not None and r["val"] != 0:
                    tid = r["TrialID"]
                    lab_map.setdefault(tid, {})[key] = float(r["val"])
                    found.add(tid)

            # Fallback-Tabelle (nur für Itemat-Felder)
            missing = set(trial_ids) - found
            if missing and fallback:
                miss_list = ",".join(str(i) for i in missing)
                fb_rows = fetch_all(
                    f"SELECT TrialID, `{col}` AS val FROM `{fallback}` "
                    f"WHERE TrialID IN ({miss_list}){t_cond}", [])
                for r in fb_rows:
                    if r["val"] is not None and r["val"] != 0:
                        tid = r["TrialID"]
                        lab_map.setdefault(tid, {})[key] = float(r["val"])

        return lab_map

    def build_debug_info(self, filter_list, target_list) -> str:
        must_t  = [t for t in target_list if t["target_type"] == "must"]
        w_t     = [t for t in target_list if t["target_type"] == "weighted"]
        d_t     = [t for t in target_list if t["target_type"] == "distance"]
        lines   = ["-- Quick Scan Query\n"]
        lines.append(f"Filter (Must):   {len(filter_list)} Felder")
        lines.append(f"Target Must:     {len(must_t)} Felder")
        lines.append(f"Target Weighted: {len(w_t)} Felder")
        lines.append(f"Target Distance: {len(d_t)} Felder\n")
        if w_t:
            lines.append("Weighted Targets:")
            for t in w_t:
                fld = t["field"]
                lines.append(
                    f"  {fld['field_label']}: {t['operator']} {t['value1']}"
                    + (f"–{t['value2']}" if t.get("value2") else "")
                    + f"  direction={t.get('direction', '?')}  optimum={t.get('target_val', '?')}  gewicht={t['weight']}"
                )
        if d_t:
            lines.append("Distance Targets:")
            for t in d_t:
                fld = t["field"]
                lines.append(f"  {fld['field_label']}: Ziel={t['value1']}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# QuickScanScreen
# ---------------------------------------------------------------------------
class QuickScanScreen(QWidget):
    def __init__(self, on_back_hub=None, sidebar_callbacks=None):
        super().__init__()
        self._on_back_hub  = on_back_hub
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None
        self._all_fields   = []
        self._filter_rows  = []
        self._target_rows  = []
        self._evaluator    = QuickScanEvaluator()
        # Letzter Scan-State für Advisor
        self._last_top25        = []
        self._last_filters      = []
        self._last_w_targets    = []
        self._last_d_targets    = []
        self._advisor_worker    = None
        self._build_ui()
        self._load_fields()

    def _asset_path(self, f):
        return Path(__file__).resolve().parents[1] / "assets" / "images" / f

    def _icon_btn(self, text, icon_file, style, cb=None):
        btn = QPushButton(text)
        btn.setObjectName(style)
        p = self._asset_path(icon_file)
        if p.exists():
            btn.setIcon(QIcon(str(p)))
            btn.setIconSize(QSize(18, 18))
        if callable(cb):
            btn.clicked.connect(cb)
        return btn

    def _sep(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "color:#aaa;font-size:10px;font-weight:bold;"
            "padding-top:8px;padding-bottom:2px;"
            "border-bottom:1px solid #555;")
        return lbl

    def _make_combo(self, placeholder):
        c = QComboBox()
        c.setMinimumWidth(200)
        c.addItem(placeholder, None)
        return c

    def _populate_combo(self, combo):
        combo.blockSignals(True)
        while combo.count() > 1:
            combo.removeItem(1)
        for f in self._all_fields:
            combo.addItem(f["field_label"], f)
        combo.insertSeparator(combo.count())
        combo.addItem("\u2699  Custom \u2026", "__adhoc__")
        combo.blockSignals(False)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring).
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        main = QWidget()
        main_lay = QHBoxLayout(main)
        main_lay.setContentsMargins(16, 16, 16, 16)
        main_lay.setSpacing(8)

        # ---- LINKE SEITE + TOGGLE als Stack ----
        self._panel_open  = True
        self._panel_width = 560

        left_wrapper = QWidget()
        left_wrapper_lay = QHBoxLayout(left_wrapper)
        left_wrapper_lay.setContentsMargins(0, 0, 0, 0)
        left_wrapper_lay.setSpacing(0)

        self._left_panel = QFrame(objectName="Card")
        self._left_panel.setMaximumWidth(self._panel_width)
        self._left_panel.setMinimumWidth(self._panel_width)
        ll = QVBoxLayout(self._left_panel)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        lh = QFrame(objectName="CardHeader")
        lh_lay = QHBoxLayout(lh)
        lh_lay.setContentsMargins(12, 4, 12, 4)
        lh_lay.addWidget(QLabel("Filter & Targets",
            styleSheet="color:white;font-weight:bold;font-size:14px;"))
        lh_lay.addStretch()
        btn_clear = QPushButton("Clear all")
        btn_clear.setObjectName("HomeBtn")
        btn_clear.setFixedHeight(24)
        btn_clear.clicked.connect(self._clear_all)
        lh_lay.addWidget(btn_clear)

        btn_load_rs = QPushButton("📂 Laden")
        btn_load_rs.setToolTip("Gespeichertes Ruleset laden")
        btn_load_rs.setFixedHeight(24)
        btn_load_rs.setStyleSheet(
            "QPushButton { background:#2d4a6b; color:#e2e8f0; border:1px solid #4a7fa5;"
            "border-radius:3px; font-size:11px; font-weight:bold; padding:0 8px; }"
            "QPushButton:hover { background:#3a6491; color:#fff; border-color:#60a8d4; }"
        )
        btn_load_rs.clicked.connect(self._load_ruleset_dialog)
        lh_lay.addWidget(btn_load_rs)

        btn_save_rs = QPushButton("💾 Speichern")
        btn_save_rs.setToolTip("Aktuelles Ruleset speichern")
        btn_save_rs.setFixedHeight(24)
        btn_save_rs.setStyleSheet(
            "QPushButton { background:#1e4a2d; color:#e2e8f0; border:1px solid #39A650;"
            "border-radius:3px; font-size:11px; font-weight:bold; padding:0 8px; }"
            "QPushButton:hover { background:#2a6b40; color:#fff; border-color:#4ade80; }"
        )
        btn_save_rs.clicked.connect(self._save_ruleset_dialog)
        lh_lay.addWidget(btn_save_rs)
        ll.addWidget(lh)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget()
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(12, 8, 12, 8)
        inner_lay.setSpacing(2)
        inner_lay.setAlignment(Qt.AlignTop)

        inner_lay.addWidget(self._sep("FILTER  (immer Must)"))
        self._filter_inner = QVBoxLayout()
        self._filter_inner.setSpacing(2)
        self._filter_inner.setAlignment(Qt.AlignTop)
        inner_lay.addLayout(self._filter_inner)
        self._combo_filter = self._make_combo("+ Filter hinzufuegen ...")
        self._combo_filter.currentIndexChanged.connect(
            lambda i: self._add(i, "filter", self._combo_filter))
        inner_lay.addWidget(self._combo_filter)
        btn_adhoc_filter = QPushButton("+ Feld aus DB (Ad-hoc) …")
        btn_adhoc_filter.setObjectName("HomeBtn")
        btn_adhoc_filter.setFixedHeight(24)
        btn_adhoc_filter.setToolTip("Add any DB column as filter")
        btn_adhoc_filter.clicked.connect(lambda: self._add_adhoc("filter"))
        inner_lay.addWidget(btn_adhoc_filter)

        inner_lay.addSpacing(8)
        inner_lay.addWidget(self._sep("TARGETS  (Must / Weighted / Distance)"))
        self._target_inner = QVBoxLayout()
        self._target_inner.setSpacing(2)
        self._target_inner.setAlignment(Qt.AlignTop)
        inner_lay.addLayout(self._target_inner)
        self._combo_target = self._make_combo("+ Target hinzufuegen ...")
        self._combo_target.currentIndexChanged.connect(
            lambda i: self._add(i, "target", self._combo_target))
        inner_lay.addWidget(self._combo_target)
        btn_adhoc_target = QPushButton("+ Feld aus DB (Ad-hoc) …")
        btn_adhoc_target.setObjectName("HomeBtn")
        btn_adhoc_target.setFixedHeight(24)
        btn_adhoc_target.setToolTip("Add any DB column as target")
        btn_adhoc_target.clicked.connect(lambda: self._add_adhoc("target"))
        inner_lay.addWidget(btn_adhoc_target)

        scroll.setWidget(inner)
        ll.addWidget(scroll, 1)

        btn_area = QFrame()
        btn_lay  = QHBoxLayout(btn_area)
        btn_lay.setContentsMargins(12, 6, 12, 10)
        btn_lay.setSpacing(8)
        btn_run = self._icon_btn("Run Quick Scan", "quick_search.png", "GreenBtn", self._run)
        btn_run.setFixedHeight(36)
        btn_sql = QPushButton("Show SQL")
        btn_sql.setObjectName("GreenBtn")
        btn_sql.setFixedHeight(36)
        btn_sql.setFixedWidth(100)
        btn_sql.clicked.connect(self._show_sql)
        btn_lay.addWidget(btn_run, 1)
        btn_lay.addWidget(btn_sql, 0)
        ll.addWidget(btn_area)

        left_wrapper_lay.addWidget(self._left_panel)

        # Arrow-Button – vertikal zentriert, an der rechten Kante des Panels
        self._toggle_btn = QPushButton("◀")
        self._toggle_btn.setFixedSize(20, 52)
        self._toggle_btn.setToolTip("Filter & Targets einklappen")
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1D3557, stop:1 #2c5f8a);
                color: white;
                border: none;
                border-radius: 0 8px 8px 0;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2c4f7a, stop:1 #3a7ab8);
            }
            QPushButton:pressed {
                background: #1a2d47;
            }
        """)
        self._toggle_btn.clicked.connect(self._toggle_panel)
        left_wrapper_lay.addWidget(self._toggle_btn, 0, Qt.AlignVCenter)

        self._left_wrapper = left_wrapper
        main_lay.addWidget(left_wrapper)

        # ---- RECHTE SEITE ----
        right = QFrame(objectName="Card")
        rl    = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        rh = QFrame(objectName="CardHeader")
        rh_lay = QHBoxLayout(rh)
        rh_lay.setContentsMargins(12, 4, 12, 4)
        self._lbl_title = QLabel("Resultate",
            styleSheet="color:white;font-weight:bold;font-size:14px;")
        rh_lay.addWidget(self._lbl_title)
        rl.addWidget(rh)

        # Tab-Widget – nur Tabelle + Score Ranking
        self._tabs = QTabWidget()
        self._tabs.setObjectName("ResultTabs")

        self._table = QTableWidget()
        self._table.setObjectName("DataTable")
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSortingEnabled(True)
        self._tabs.addTab(self._table, "Tabelle")

        score_scroll = QScrollArea()
        score_scroll.setWidgetResizable(True)
        score_scroll.setFrameShape(QFrame.NoFrame)
        self._score_chart = ScoreBarChart()
        score_scroll.setWidget(self._score_chart)
        self._tabs.addTab(score_scroll, "Score Ranking")

        # Advisor Tab – sichtbar wenn tbluser.api_key_enc gesetzt ist
        self._qs_advisor_history: list = []   # Chat-History (in-memory)
        if _is_advisor_enabled():
            advisor_widget = QWidget()
            adv_lay = QVBoxLayout(advisor_widget)
            adv_lay.setContentsMargins(12, 12, 12, 12)
            adv_lay.setSpacing(8)

            # Header
            adv_hdr = QHBoxLayout()
            from ui.athena_owl import AthenaHeaderLabel
            adv_lbl = AthenaHeaderLabel("🦉 Athena – Jet Optimization Advisor", owl=None)
            adv_lbl.setStyleSheet("font-size:13px; font-weight:bold;")
            adv_hdr.addWidget(adv_lbl)
            adv_hdr.addStretch()
            self._btn_qs_advisor = QPushButton("🦉 Athena wecken")
            self._btn_qs_advisor.setObjectName("GreenBtn")
            self._btn_qs_advisor.setFixedHeight(30)
            self._btn_qs_advisor.setMinimumWidth(170)
            self._btn_qs_advisor.setEnabled(False)
            self._btn_qs_advisor.clicked.connect(self._run_qs_advisor)
            adv_hdr.addWidget(self._btn_qs_advisor)
            self._btn_qs_advisor_reset = QPushButton("↺  Neu")
            self._btn_qs_advisor_reset.setToolTip("Clear chat history")
            self._btn_qs_advisor_reset.setFixedHeight(30)
            self._btn_qs_advisor_reset.setFixedWidth(70)
            self._btn_qs_advisor_reset.setStyleSheet(
                "QPushButton { background:#1e293b; color:#cbd5e1; border:1px solid #475569;"
                "border-radius:4px; font-size:12px; font-weight:bold; }"
                "QPushButton:hover { background:#334155; color:#fff; border-color:#39A650; }"
            )
            self._btn_qs_advisor_reset.clicked.connect(self._reset_qs_advisor)
            adv_hdr.addWidget(self._btn_qs_advisor_reset)
            adv_lay.addLayout(adv_hdr)

            hint = QLabel("~ CHF 0.02 pro Analyse  ·  Anthropic API  ·  Kein Training")
            hint.setStyleSheet("color:#666; font-size:10px;")
            adv_lay.addWidget(hint)

            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setStyleSheet("color:#333;")
            adv_lay.addWidget(line)

            # Output-Container — Athena schläft hier unten rechts
            qs_output_container = QWidget()
            qs_output_container.setMinimumHeight(250)
            qs_out_lay = QVBoxLayout(qs_output_container)
            qs_out_lay.setContentsMargins(0, 0, 0, 0)

            self._qs_advisor_output = QTextEdit()
            self._qs_advisor_output.setReadOnly(True)
            self._qs_advisor_output.setStyleSheet(
                "background:#111827; color:#e5e7eb;"
                "font-family:'Consolas','Courier New',monospace;"
                "font-size:12px; border:1px solid #374151;"
                "border-radius:6px; padding:12px;"
            )
            self._qs_advisor_output.setPlaceholderText(
                "Please run a Quick Scan first, then start the analysis.\n\n"
                "Athena analysiert die Top 25 Treffer:\n"
                "  • Welche Jets / Serien am besten abschneiden und warum\n"
                "  • Welche Rules knapp verfehlt werden\n"
                "  • Was die Top-Performer gemeinsam haben\n"
                "  • Concrete recommendations for the next trial\n\n"
                "Nach der Analyse kannst du Folgefragen stellen."
            )
            qs_out_lay.addWidget(self._qs_advisor_output)
            adv_lay.addWidget(qs_output_container, 1)

            # Athena schläft unten rechts im Output-Container
            from ui.athena_owl import AthenaOwl
            self._qs_athena = AthenaOwl(qs_output_container)
            self._qs_athena.place_sleeping()
            adv_lbl._owl = self._qs_athena

            # Chat-Input für Folgefragen
            chat_frame = QFrame()
            chat_frame.setStyleSheet(
                "QFrame { background:#1a1f2e; border:1px solid #2d3748; border-radius:6px; }"
            )
            chat_inner = QVBoxLayout(chat_frame)
            chat_inner.setContentsMargins(10, 8, 10, 8)
            chat_inner.setSpacing(5)
            chat_lbl2 = QLabel("Frage an Athena:")
            chat_lbl2.setStyleSheet("color:#9ca3af; font-size:11px; background:transparent; border:none;")
            chat_inner.addWidget(chat_lbl2)
            chat_row = QHBoxLayout()
            self._qs_chat_input = QTextEdit()
            self._qs_chat_input.setFixedHeight(52)
            self._qs_chat_input.setPlaceholderText(
                "z.B. «Was haben die Top-3 gemeinsam?» oder «Warum scheitert Rule X so oft?»"
            )
            self._qs_chat_input.setStyleSheet(
                "background:#111827; color:#e5e7eb; font-size:12px;"
                "border:1px solid #374151; border-radius:4px; padding:5px;"
            )
            chat_row.addWidget(self._qs_chat_input, 1)
            self._btn_qs_advisor_send = QPushButton("Senden  ↵")
            self._btn_qs_advisor_send.setFixedSize(90, 52)
            self._btn_qs_advisor_send.setStyleSheet(
                "QPushButton { background:#39A650; color:#ffffff; border:none;"
                "border-radius:5px; font-size:13px; font-weight:bold; }"
                "QPushButton:hover { background:#2e8a42; }"
                "QPushButton:disabled { background:#1e293b; color:#4b5563; border:1px solid #374151; }"
            )
            self._btn_qs_advisor_send.setEnabled(False)
            self._btn_qs_advisor_send.clicked.connect(self._send_qs_question)
            chat_row.addWidget(self._btn_qs_advisor_send)
            chat_inner.addLayout(chat_row)
            adv_lay.addWidget(chat_frame)

            self._qs_advisor_status = QLabel("")
            self._qs_advisor_status.setStyleSheet("color:#9ca3af; font-size:10px;")
            adv_lay.addWidget(self._qs_advisor_status)

            self._tabs.addTab(advisor_widget, "🦉 Athena")
        else:
            self._btn_qs_advisor      = None
            self._btn_qs_advisor_send = None
            self._qs_advisor_output   = None
            self._qs_advisor_status   = None

        rl.addWidget(self._tabs, 1)

        self._lbl_status = QLabel("Filter und Targets waehlen, dann Run.",
            styleSheet="color:#888;font-size:11px;padding:4px 12px;")
        rl.addWidget(self._lbl_status)

        main_lay.addWidget(right, 1)
        content_layout.addWidget(main, 1)
        root.addWidget(FooterBar())

    def _refresh_sidebar(self):
        """Baut die Sidebar-Navigation neu auf, falls sich der Access-Level
        seit dem letzten Aufbau geändert hat, sonst nur die Badges (siehe
        ui/widgets/sidebar_nav.py::refresh_lazy_sidebar())."""
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

    # ------------------------------------------------------------------
    # Ruleset Save / Load
    # ------------------------------------------------------------------

    def _save_ruleset_dialog(self):
        """Speichert die aktuelle Filter+Target-Konfiguration als Ruleset in der DB."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QDialogButtonBox, QTextEdit

        filters, targets = self._get_all()
        if not filters and not targets:
            QMessageBox.information(self, "Ruleset speichern",
                "Keine Filter oder Targets gesetzt.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Ruleset speichern")
        dlg.setMinimumWidth(380)
        lay = QVBoxLayout(dlg)
        lay.setSpacing(10)
        lay.setContentsMargins(16, 16, 16, 16)

        lay.addWidget(QLabel("Name:"))
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("z.B. DTY 167f48 Standard")
        lay.addWidget(name_edit)

        lay.addWidget(QLabel("Beschreibung (optional):"))
        desc_edit = QTextEdit()
        desc_edit.setFixedHeight(70)
        desc_edit.setPlaceholderText("Kurze Beschreibung des Rulesets...")
        lay.addWidget(desc_edit)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)

        if not dlg.exec():
            return

        name = name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ruleset speichern", "Bitte einen Namen eingeben.")
            return
        desc = desc_edit.toPlainText().strip()

        try:
            import app_meta
            created_by = app_meta.current_user.get("username", "")

            # tblrequirementset anlegen - execute_insert() statt execute()+
            # separatem fetch_all('SELECT LAST_INSERT_ID()'), siehe CLAUDE.md.
            set_id = execute_insert(
                "INSERT INTO tblrequirementset (set_name, description, is_active, created_by) "
                "VALUES (%s, %s, 1, %s)",
                [name, desc or None, created_by]
            )

            # Alle Filter + Targets als Rules speichern
            all_rows = (
                [(f, "filter") for f in filters] +
                [(t, "target") for t in targets]
            )
            for sort_order, (r, section) in enumerate(all_rows, start=1):
                field      = r["field"]
                # Ad-hoc-Felder automatisch in tblRequirementField registrieren
                if field.get("_adhoc") or field.get("field_id") is None:
                    AdhocFieldDialog.ensure_registered(field)
                field_id   = field["field_id"]
                rule_type  = r.get("target_type", "filter") if section == "target" else "filter"
                operator   = r.get("operator")
                value1     = r.get("value1")
                value2     = r.get("value2")
                weight     = r.get("weight") if rule_type == "weighted" else None
                target_val = r.get("target_val") if rule_type == "weighted" else None
                # direction als Kommentar in min_value/max_value nicht möglich —
                # wir nutzen ein JSON-Feld nicht. Stattdessen: direction in description via sort_order trick.
                # Saubere Lösung: direction in min_value speichern als kodierter Float:
                #   higher=1.0, lower=2.0, exact=3.0 → wird beim Laden dekodiert
                direction  = r.get("direction", "higher") if rule_type == "weighted" else None
                dir_code   = {"higher": 1.0, "lower": 2.0, "exact": 3.0}.get(direction) if direction else None

                execute(
                    "INSERT INTO tblrequirementrule "
                    "(set_id, field_id, rule_type, operator, target_value, "
                    " min_value, max_value, weight, sort_order, is_active) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,1)",
                    [set_id, field_id, rule_type, operator, target_val,
                     value1, value2, weight, sort_order]
                )
                # direction separat in einer zweiten Update (da kein extra Feld vorhanden):
                # Wir nutzen max_value für between-v2, aber direction braucht einen Platz.
                # Lösung: direction als signed sort_order kodieren ist zu hacky.
                # Sauberste Lösung ohne Schema-Änderung:
                # filter-rule: min_value=value1, max_value=value2
                # weighted: min_value=value1(range_lo), max_value=value2(range_hi), target_value=target_val
                # direction: nicht direkt speicherbar ohne Schema-Erweiterung.
                # → direction in tblrequirementrule.sort_order*10 + dir_code kodieren:
                #   sort_order_encoded = sort_order * 10 + dir_code (1/2/3)
                if dir_code is not None:
                    execute(
                        "UPDATE tblrequirementrule SET sort_order=%s "
                        "WHERE set_id=%s AND field_id=%s AND rule_type='weighted' AND sort_order=%s",
                        [sort_order * 10 + int(dir_code), set_id, field_id, sort_order]
                    )

            QMessageBox.information(self, "Ruleset gespeichert",
                f"«{name}» wurde gespeichert ({len(all_rows)} Regeln).")

        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Speichern", str(e))

    def _load_ruleset_dialog(self):
        """Zeigt alle gespeicherten Rulesets und lädt das gewählte in die UI."""
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                                        QListWidget, QListWidgetItem,
                                        QDialogButtonBox, QPushButton, QLabel)

        try:
            sets = fetch_all(
                "SELECT set_id, set_name, description, created_by, created_at "
                "FROM tblrequirementset WHERE is_active=1 "
                "ORDER BY created_at DESC",
                []
            )
        except Exception as e:
            QMessageBox.critical(self, "DB Fehler", str(e))
            return

        if not sets:
            QMessageBox.information(self, "Load ruleset",
                "Keine gespeicherten Rulesets gefunden.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Load ruleset")
        dlg.setMinimumWidth(420)
        dlg.setMinimumHeight(320)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

        lay.addWidget(QLabel("Gespeicherte Rulesets:"))
        lst = QListWidget()
        lst.setStyleSheet("font-size:12px;")
        for s in sets:
            label = s["set_name"]
            if s.get("created_by"):
                label += f"  ({s['created_by']})"
            if s.get("description"):
                label += f"  —  {s['description']}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, s["set_id"])
            lst.addItem(item)
        lst.setCurrentRow(0)
        lay.addWidget(lst, 1)

        btn_row = QHBoxLayout()
        btn_delete = QPushButton("🗑 Delete")
        btn_delete.setStyleSheet(
            "QPushButton { background:#3b1e1e; color:#f87171; border:1px solid #7f1d1d;"
            "border-radius:4px; font-size:12px; padding:4px 10px; }"
            "QPushButton:hover { background:#5b2a2a; }"
        )
        def _delete():
            sel = lst.currentItem()
            if not sel:
                return
            sid = sel.data(Qt.UserRole)
            sname = sel.text().split("\n")[0].strip()
            if QMessageBox.question(dlg, "Delete",
                f"Really delete ruleset «{sname}»?",
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
                return
            try:
                execute("UPDATE tblrequirementset SET is_active=0 WHERE set_id=%s", [sid])
                lst.takeItem(lst.currentRow())
            except Exception as ex:
                QMessageBox.critical(dlg, "Fehler", str(ex))
        btn_delete.clicked.connect(_delete)
        btn_row.addWidget(btn_delete)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)

        if not dlg.exec():
            return

        sel = lst.currentItem()
        if not sel:
            return
        set_id = sel.data(Qt.UserRole)
        self._apply_ruleset(set_id)

    def _apply_ruleset(self, set_id: int):
        """Lädt ein Ruleset aus der DB und befüllt Filter + Targets in der UI."""
        try:
            rules = fetch_all(
                """
                SELECT r.rule_id, r.rule_type, r.operator,
                       r.target_value, r.min_value, r.max_value,
                       r.weight, r.sort_order,
                       f.field_id, f.field_key, f.field_label,
                       f.source_table_primary, f.source_table_fallback,
                       f.source_column, f.tension_filter,
                       f.data_type, f.unit,
                       f.lookup_table, f.lookup_col_value, f.lookup_col_label
                FROM tblrequirementrule r
                JOIN tblrequirementfield f ON f.field_id = r.field_id
                WHERE r.set_id = %s AND r.is_active = 1
                ORDER BY r.sort_order
                """,
                [set_id]
            )
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Laden", str(e))
            return

        if not rules:
            QMessageBox.information(self, "Load ruleset", "Ruleset contains no rules.")
            return

        # UI leeren
        self._clear_all()

        for r in rules:
            field = {
                "field_id":              r["field_id"],
                "field_key":             r["field_key"],
                "field_label":           r["field_label"],
                "source_table_primary":  r["source_table_primary"],
                "source_table_fallback": r["source_table_fallback"],
                "source_column":         r["source_column"],
                "tension_filter":        r["tension_filter"],
                "data_type":             r["data_type"],
                "unit":                  r["unit"],
                "lookup_table":          r["lookup_table"],
                "lookup_col_value":      r["lookup_col_value"],
                "lookup_col_label":      r["lookup_col_label"],
                "_adhoc":                r["field_key"].startswith("adhoc__"),
            }
            rule_type = r["rule_type"]

            if rule_type == "filter":
                row = FilterRow(field, on_remove=lambda rw: self._del(rw, "filter"))
                self._filter_inner.addWidget(row)
                self._filter_rows.append(row)
                self._restore_filter_values(row, r)
            else:
                row = TargetRow(field, on_remove=lambda rw: self._del(rw, "target"))
                self._target_inner.addWidget(row)
                self._target_rows.append(row)
                self._restore_target_values(row, r, rule_type)

    def _restore_filter_values(self, row: "FilterRow", r: dict):
        """Setzt Operator + Werte einer FilterRow aus DB-Daten."""
        try:
            op = r.get("operator") or ">="
            for i in range(row._op.count()):
                if row._op.itemData(i) == op:
                    row._op.setCurrentIndex(i)
                    break
            if r.get("min_value") is not None:
                row._v1.setText(str(r["min_value"]))
            if r.get("max_value") is not None and op == "between":
                row._v2.setText(str(r["max_value"]))
            if row._v_t is not None and r.get("tension_filter") is not None:
                row._v_t.setText(str(r["tension_filter"]))
        except Exception:
            pass

    def _restore_target_values(self, row: "TargetRow", r: dict, rule_type: str):
        """Setzt Operator + Werte + Typ einer TargetRow aus DB-Daten."""
        try:
            # rule_type setzen
            for i in range(row._type_combo.count()):
                if row._type_combo.itemData(i) == rule_type:
                    row._type_combo.setCurrentIndex(i)
                    break

            # Operator
            op = r.get("operator") or ">="
            for i in range(row._op.count()):
                if row._op.itemData(i) == op:
                    row._op.setCurrentIndex(i)
                    break

            # Werte: min_value = value1, max_value = value2 (bei between)
            if r.get("min_value") is not None:
                row._v1.setText(str(r["min_value"]))
            if r.get("max_value") is not None and op == "between":
                row._v2.setText(str(r["max_value"]))

            if row._v_t is not None and r.get("tension_filter") is not None:
                row._v_t.setText(str(r["tension_filter"]))

            if rule_type == "weighted":
                # Zielwert
                if r.get("target_value") is not None:
                    row._target_val.setText(str(r["target_value"]))
                # Gewicht
                if r.get("weight") is not None:
                    row._weight.setText(str(r["weight"]))
                # Direction: dekodiert aus sort_order (sort_order = orig*10 + dir_code)
                so = r.get("sort_order") or 0
                dir_code = so % 10 if so >= 10 else 1
                direction = {1: "higher", 2: "lower", 3: "exact"}.get(dir_code, "higher")
                for i in range(row._direction.count()):
                    if row._direction.itemData(i) == direction:
                        row._direction.setCurrentIndex(i)
                        break

            row._sync()
        except Exception:
            pass

    def _toggle_panel(self):
        """Klappt das linke Filter-Panel mit Animation ein oder aus."""
        btn_w = 20 + 8  # Button-Breite + Spacing

        # Panel-Animation (maximumWidth + minimumWidth)
        self._anim = QPropertyAnimation(self._left_panel, b"maximumWidth")
        self._anim.setDuration(350)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

        self._anim2 = QPropertyAnimation(self._left_panel, b"minimumWidth")
        self._anim2.setDuration(350)
        self._anim2.setEasingCurve(QEasingCurve.InOutCubic)

        # Wrapper-Animation (maximumWidth)
        self._anim3 = QPropertyAnimation(self._left_wrapper, b"maximumWidth")
        self._anim3.setDuration(350)
        self._anim3.setEasingCurve(QEasingCurve.InOutCubic)

        self._anim4 = QPropertyAnimation(self._left_wrapper, b"minimumWidth")
        self._anim4.setDuration(350)
        self._anim4.setEasingCurve(QEasingCurve.InOutCubic)

        if self._panel_open:
            self._anim.setStartValue(self._panel_width);  self._anim.setEndValue(0)
            self._anim2.setStartValue(self._panel_width); self._anim2.setEndValue(0)
            self._anim3.setStartValue(self._panel_width + btn_w); self._anim3.setEndValue(btn_w)
            self._anim4.setStartValue(self._panel_width + btn_w); self._anim4.setEndValue(btn_w)
            self._toggle_btn.setText("▶")
            self._toggle_btn.setToolTip("Filter & Targets ausklappen")
            self._panel_open = False
        else:
            self._anim.setStartValue(0);  self._anim.setEndValue(self._panel_width)
            self._anim2.setStartValue(0); self._anim2.setEndValue(self._panel_width)
            self._anim3.setStartValue(btn_w); self._anim3.setEndValue(self._panel_width + btn_w)
            self._anim4.setStartValue(btn_w); self._anim4.setEndValue(self._panel_width + btn_w)
            self._toggle_btn.setText("◀")
            self._toggle_btn.setToolTip("Filter & Targets einklappen")
            self._panel_open = True

        self._anim.start()
        self._anim2.start()
        self._anim3.start()
        self._anim4.start()

    def _load_fields(self):
        try:
            rows = fetch_all(
                "SELECT * FROM tblRequirementField "
                "WHERE is_active=1 ORDER BY sort_order, field_label", [])
            self._all_fields = rows or []
        except Exception as e:
            QMessageBox.warning(self, "DB Fehler", str(e))
            return
        self._populate_combo(self._combo_filter)
        self._populate_combo(self._combo_target)

    def _add(self, idx, section, combo):
        if idx <= 0:
            return
        field = combo.itemData(idx)
        if not field:
            return
        combo.blockSignals(True)
        combo.setCurrentIndex(0)
        combo.blockSignals(False)

        if field == "__adhoc__":
            self._add_adhoc(section)
            return

        if section == "filter":
            row = FilterRow(field, on_remove=lambda r: self._del(r, "filter"))
            self._filter_inner.addWidget(row)
            self._filter_rows.append(row)
        else:
            row = TargetRow(field, on_remove=lambda r: self._del(r, "target"))
            self._target_inner.addWidget(row)
            self._target_rows.append(row)

    def _add_adhoc(self, section: str):
        """Öffnet den Ad-hoc-Feld-Dialog und fügt das gewählte Feld als Row ein."""
        field = AdhocFieldDialog.open(self)
        if not field:
            return
        if section == "filter":
            row = FilterRow(field, on_remove=lambda r: self._del(r, "filter"))
            self._filter_inner.addWidget(row)
            self._filter_rows.append(row)
        else:
            row = TargetRow(field, on_remove=lambda r: self._del(r, "target"))
            self._target_inner.addWidget(row)
            self._target_rows.append(row)

    def _del(self, row, section):
        lst = self._filter_rows if section == "filter" else self._target_rows
        lay = self._filter_inner if section == "filter" else self._target_inner
        if row in lst:
            lst.remove(row)
        lay.removeWidget(row)
        row.setParent(None)
        row.deleteLater()

    def _clear_all(self):
        for r in list(self._filter_rows):
            self._del(r, "filter")
        for r in list(self._target_rows):
            self._del(r, "target")
        self._table.setRowCount(0)
        self._lbl_title.setText("Resultate")
        self._lbl_status.setText("Filter und Targets waehlen, dann Run.")

    def _get_all(self):
        filters = [r.get_filter() for r in self._filter_rows]
        targets = [r.get_filter() for r in self._target_rows]
        return [f for f in filters if f], [t for t in targets if t]

    def _show_sql(self):
        filters, targets = self._get_all()
        if not filters and not targets:
            QMessageBox.information(self, "Show SQL", "Keine Filter/Targets ausgefuellt.")
            return
        txt = self._evaluator.build_debug_info(filters, targets)
        dlg = QMessageBox(self)
        dlg.setWindowTitle("SQL Debug")
        dlg.setText("Query-Uebersicht:")
        dlg.setDetailedText(txt)
        dlg.exec()

    def _run(self):
        filters, targets = self._get_all()
        if not filters and not targets:
            QMessageBox.information(self, "Quick Scan",
                "Bitte mindestens einen Filter oder Target eingeben.")
            return
        self._lbl_status.setText("Suche laeuft ...")
        self._table.setRowCount(0)
        self._score_chart.set_data([])
        self.repaint()
        try:
            results, w_targets, d_targets = self._evaluator.run(filters, targets)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            self._lbl_status.setText("Fehler.")
            return
        self._show_results(results, filters, targets, w_targets, d_targets)

    def _show_results(self, results, filters, targets, w_targets, d_targets):
        has_score = bool(w_targets)

        base_cols = [
            ("experiment_id", "Experiment"),
            ("trial_nr",      "Trial #"),
            ("series_name",   "Series"),
            ("jet_name",      "Jet"),
            ("yarn_name",     "Garn"),
            ("titer",         "Titer"),
            ("filamente",     "Fil."),
        ]
        score_col  = [("_score", "Score %")] if has_score else []
        # Dynamische Spalten: weighted + distance Felder
        dyn_cols = []
        for t in w_targets + d_targets:
            fld   = t["field"]
            key   = fld["field_key"]
            unit  = fld.get("unit") or ""
            label = fld["field_label"]
            tens  = fld.get("tension_filter")
            if tens is not None:
                label += f" @{tens}"
            if unit:
                label += f" [{unit}]"
            is_weighted = (t in w_targets)
            dyn_cols.append((key, label, is_weighted, t))

        all_cols = score_col + base_cols + [(k, l) for k, l, _, _ in dyn_cols]

        if not results:
            self._lbl_title.setText("Resultate – 0 Treffer")
            self._lbl_status.setText("Keine Treffer gefunden.")
            self._table.setRowCount(0)
            return

        self._table.setSortingEnabled(False)
        self._table.setColumnCount(len(all_cols))
        self._table.setHorizontalHeaderLabels([c[1] for c in all_cols])
        self._table.setRowCount(len(results))

        # Lookup für weighted-Spalten: key → target dict
        weighted_keys = {t["field"]["field_key"]: t for t in w_targets}

        for ri, res in enumerate(results):
            for ci, (key, _) in enumerate(all_cols):
                val = res.get(key)
                if key == "_score":
                    txt  = f"{val:.1f}%" if val is not None else "–"
                    item = NumericItem(txt, val)
                elif key in weighted_keys and val is not None:
                    # Messwert + gewichteter Teilscore
                    contrib = res.get(f"_contrib_{key}")
                    total_w = sum(t["weight"] for t in w_targets) or 1.0
                    if contrib is not None:
                        contrib_pct = (contrib / total_w) * 100
                        txt = f"{val:.1f} (→ {contrib_pct:.1f}%)"
                    else:
                        txt = f"{val:.1f}"
                    item = NumericItem(txt, float(val))
                elif isinstance(val, float):
                    item = NumericItem(f"{val:.1f}", val)
                elif isinstance(val, int):
                    item = NumericItem(str(val), float(val))
                else:
                    item = NumericItem(str(val) if val is not None else "–")
                item.setTextAlignment(Qt.AlignCenter)
                if key == "_score" and val is not None:
                    if val >= 80:
                        item.setForeground(QColor("#3fb950"))
                    elif val >= 50:
                        item.setForeground(QColor("#e8a838"))
                    else:
                        item.setForeground(QColor("#f78166"))
                self._table.setItem(ri, ci, item)

        self._table.setSortingEnabled(True)
        self._table.resizeColumnsToContents()
        self._lbl_title.setText(f"Resultate – {len(results)} Treffer")
        n_w = len(w_targets)
        n_d = len(d_targets)
        self._lbl_status.setText(
            f"{len(results)} Trial(s) · "
            f"{len(filters)} Filter · "
            f"{len(targets)} Target(s)"
            + (f" · {n_w} weighted" if n_w else "")
            + (f" · {n_d} distance" if n_d else "")
        )

        # Score Ranking Chart befüllen
        self._score_chart.set_data(results, max_items=25, has_score=bool(w_targets))

        # Letzten Scan-State speichern für Advisor
        self._last_top25     = results[:25]
        self._last_filters   = filters
        self._last_w_targets = w_targets
        self._last_d_targets = d_targets
        # Chat-History bei neuem Scan zurücksetzen (neuer Kontext)
        self._qs_advisor_history = []
        if hasattr(self, "_btn_qs_advisor_send"):
            self._btn_qs_advisor_send.setEnabled(False)
        if self._btn_qs_advisor is not None:
            self._btn_qs_advisor.setEnabled(bool(results))
    # ------------------------------------------------------------------
    # agentT – Quick Scan Advisor
    # ------------------------------------------------------------------

    def _run_qs_advisor(self):
        """Startet die Athena-Erstanalyse der Top 25 Quick Scan Resultate."""
        from ui.advisor_worker import load_api_key, ADVISOR_SYSTEM_PROMPT
        import json

        if not self._last_top25:
            return

        api_key = load_api_key()
        if not api_key:
            self._qs_advisor_output.setPlainText(
                "⚠️  Kein API Key gefunden.\n\n"
                "C:\\ProgramData\\TrippleT\\ai_secrets.json\n"
                '{"anthropic_api_key": "sk-ant-..."}'
            )
            return

        self._btn_qs_advisor.setEnabled(False)
        self._btn_qs_advisor.setText("🦉 Eule denkt...")
        self._btn_qs_advisor_send.setEnabled(False)
        self._qs_advisor_status.setText("⏳  Analysis running…")
        self._qs_advisor_output.setPlainText("")
        if hasattr(self, "_qs_athena"):
            self._qs_athena.start_working()

        ctx = self._build_qs_advisor_context()

        qs_system = ADVISOR_SYSTEM_PROMPT + """

ZUSATZINFO FÜR QUICK SCAN ANALYSE:
Du analysierst die Top 25 Treffer eines Quick Scans mit definierten Regeln.
Du kennst das genaue Ziel (Filters + Weighted Targets).
Deine Analyse soll besonders präzise sein:
- Erkläre warum die Top-Treffer gut abschneiden (welche Rules erfüllt)
- Zeige welche Rules am häufigsten knapp verfehlt werden
- Identifiziere Muster bei Jet-Geometrien der Top-Performer
- Gib konkrete Empfehlung für den nächsten Versuch

Replace "Trial overview" with "Top-5 matches" (only the best 5 in detail)."""

        self._qs_advisor_worker = _QsAdvisorWorker(
            ctx, qs_system, api_key,
            history=None, user_question=None
        )
        self._qs_advisor_worker.result_ready.connect(self._on_qs_advisor_result)
        self._qs_advisor_worker.error_occurred.connect(self._on_qs_advisor_error)
        self._qs_advisor_worker.finished.connect(self._on_qs_advisor_finished)
        self._qs_advisor_worker.start()

    def _send_qs_question(self):
        """Sendet eine Folgefrage an Athena (QS-Kontext + History)."""
        from ui.advisor_worker import load_api_key, ADVISOR_SYSTEM_PROMPT

        question = self._qs_chat_input.toPlainText().strip()
        if not question or not self._last_top25:
            return

        api_key = load_api_key()
        if not api_key:
            return

        self._qs_chat_input.clear()
        self._btn_qs_advisor.setEnabled(False)
        self._btn_qs_advisor_send.setEnabled(False)
        self._qs_advisor_status.setText("⏳  Athena denkt nach...")

        current_text = self._qs_advisor_output.toPlainText()
        separator = "\n\n" + "─" * 60 + "\n"
        self._qs_advisor_output.setPlainText(
            current_text + separator + f"❓ {question}\n\n⏳ ..."
        )
        if hasattr(self, "_qs_athena"):
            self._qs_athena.start_working()

        qs_system = ADVISOR_SYSTEM_PROMPT + """

ZUSATZINFO: Du beantwortest Folgefragen zu einem Quick Scan.
Antworte fokussiert und präzise. Format: 🔍 Befund | ⚠️ Ursache | ✅ Empfehlung"""

        self._qs_advisor_worker = _QsAdvisorWorker(
            self._build_qs_advisor_context(),
            qs_system, api_key,
            history=self._qs_advisor_history,
            user_question=question,
        )
        self._qs_advisor_worker.result_ready.connect(self._on_qs_followup_result)
        self._qs_advisor_worker.error_occurred.connect(self._on_qs_advisor_error)
        self._qs_advisor_worker.finished.connect(self._on_qs_advisor_finished)
        self._qs_advisor_worker.start()

    def _reset_qs_advisor(self):
        """Chat-History löschen und neu starten."""
        self._qs_advisor_history = []
        self._qs_advisor_output.setPlainText("")
        self._qs_advisor_status.setText("")
        self._btn_qs_advisor_send.setEnabled(False)
        if hasattr(self, "_qs_chat_input"):
            self._qs_chat_input.clear()

    def _build_qs_advisor_context(self) -> dict:
        """Baut den Kontext für den QS-Advisor zusammen.

        Enthält zusätzlich zu Filtern/Targets/Top25 die vollständigen
        Laborergebnisse (Itemat, Statimat, Titer) aller Top-25-Trials,
        damit Athena primär im Garn-Ergebnis-Raum (FPm, Stability, FPmCV)
        argumentieren kann – Jet-Geometrie nur als Erklärung.
        """
        from ui.advisor_worker import _fetch_lab_results

        filters_fmt = []
        for f in self._last_filters:
            fld = f["field"]
            filters_fmt.append({
                "feld":     fld.get("field_label", fld.get("field_key")),
                "operator": f.get("operator"),
                "wert":     f.get("value1"),
                "typ":      "filter (must)",
            })

        targets_fmt = []
        for t in self._last_w_targets:
            fld = t["field"]
            targets_fmt.append({
                "feld":      fld.get("field_label", fld.get("field_key")),
                "typ":       "weighted",
                "gewicht":   t.get("weight", 1.0),
                "richtung":  t.get("direction", "higher"),
                "zielwert":  t.get("target_val"),
                "operator":  t.get("operator"),
                "wert":      t.get("value1"),
            })
        for t in self._last_d_targets:
            fld = t["field"]
            targets_fmt.append({
                "feld": fld.get("field_label", fld.get("field_key")),
                "typ":  "distance",
                "ziel": t.get("value1"),
            })

        # ── Lab-Daten für alle Top-25-Trials laden ──────────────────────────
        top25_trial_ids = [
            r["trial_id"] for r in self._last_top25
            if r.get("trial_id") is not None
        ]
        lab_data = _fetch_lab_results(top25_trial_ids) if top25_trial_ids else {}

        results_fmt = []
        for r in self._last_top25:
            entry = {
                "experiment": r.get("experiment_id"),
                "trial":      r.get("trial_nr"),
                "trial_id":   r.get("trial_id"),
                "series":     r.get("series_name"),
                "jet":        r.get("jet_name"),
                "garn":       r.get("yarn_name"),
                "titer":      r.get("titer"),
                "score_pct":  r.get("_score"),
            }

            # Target-Felder mit Score-Beitrag (wie bisher)
            for t in self._last_w_targets + self._last_d_targets:
                key     = t["field"]["field_key"]
                lbl     = t["field"].get("field_label", key)
                val     = r.get(key)
                contrib = r.get(f"_contrib_{key}")
                if val is not None:
                    entry[lbl] = f"{val:.1f}"
                    if contrib is not None:
                        total_w = sum(x["weight"] for x in self._last_w_targets) or 1.0
                        entry[f"{lbl}_beitrag_%"] = round((contrib / total_w) * 100, 1)

            # ── Laborergebnisse anfügen ──────────────────────────────────────
            tid = r.get("trial_id")
            lab = lab_data.get(tid, {}) if tid is not None else {}

            itemat_rows = lab.get("itemat") or []
            if itemat_rows:
                entry["lab_itemat"] = [
                    {
                        k: (f"{v:.2f}" if isinstance(v, float) else v)
                        for k, v in row.items()
                        if v is not None
                    }
                    for row in sorted(itemat_rows, key=lambda x: x.get("tension") or 0)
                ]
            else:
                entry["lab_itemat"] = "⚠️ keine Itemat-Daten"

            stat_m = lab.get("statimat_m")
            if stat_m:
                entry["lab_statimat_m"] = {
                    k: (f"{v:.2f}" if isinstance(v, float) else v)
                    for k, v in stat_m.items()
                    if v is not None
                }

            stat_ds = lab.get("statimat_ds")
            if stat_ds:
                entry["lab_statimat_ds"] = {
                    k: (f"{v:.2f}" if isinstance(v, float) else v)
                    for k, v in stat_ds.items()
                    if v is not None
                }

            titer_val = lab.get("titer")
            if titer_val is not None:
                entry["lab_titer_dtex"] = f"{titer_val:.2f}"

            results_fmt.append(entry)

        return {
            "scan_ziel": {
                "filter":  filters_fmt,
                "targets": targets_fmt,
            },
            "top_25_treffer":       results_fmt,
            "anzahl_treffer_total": len(self._last_top25),
            "hinweis": (
                "lab_itemat contains yarn parameters per tension level "
                "(FPm=Knoten/m, Stability, FPmCV). "
                "These are the primary evaluation criteria. "
                "Jet-Geometrie ist Mittel zum Zweck."
            ),
        }

    def _on_qs_advisor_result(self, text: str):
        self._qs_advisor_output.setPlainText(text)
        self._qs_advisor_status.setText(
            "✅  Analyse abgeschlossen  ·  Du kannst jetzt Fragen stellen"
        )
        # Ersten Turn in History speichern
        self._qs_advisor_history = [
            {"role": "user",      "content": "Analysiere diesen Quick Scan."},
            {"role": "assistant", "content": text},
        ]

    def _on_qs_followup_result(self, text: str):
        """Folgefrage-Antwort einfügen."""
        current = self._qs_advisor_output.toPlainText()
        if current.endswith("⏳ ..."):
            current = current[:-len("⏳ ...")]
        self._qs_advisor_output.setPlainText(current + text)
        self._qs_advisor_output.verticalScrollBar().setValue(
            self._qs_advisor_output.verticalScrollBar().maximum()
        )
        self._qs_advisor_status.setText("✅  Antwort erhalten")

        # History aktualisieren (max. 6 Einträge)
        sep = "─" * 60
        current_full = self._qs_advisor_output.toPlainText()
        last_question = ""
        if sep in current_full:
            parts = current_full.split(sep)
            last_part = parts[-1].strip()
            if last_part.startswith("❓ "):
                last_question = last_part.split("\n")[0][2:].strip()
        if last_question:
            self._qs_advisor_history.append({"role": "user",      "content": last_question})
            self._qs_advisor_history.append({"role": "assistant", "content": text})
            if len(self._qs_advisor_history) > 6:
                self._qs_advisor_history = (
                    self._qs_advisor_history[:2] + self._qs_advisor_history[-4:]
                )

    def _on_qs_advisor_error(self, error_msg: str):
        current = self._qs_advisor_output.toPlainText()
        if current.endswith("⏳ ..."):
            current = current[:-len("⏳ ...")]
        self._qs_advisor_output.setPlainText(
            current + f"\n\n❌  Fehler:\n{error_msg}" if current
            else f"❌  Fehler:\n\n{error_msg}"
        )
        self._qs_advisor_status.setText("❌  Fehler")

    def _on_qs_advisor_finished(self):
        self._btn_qs_advisor.setEnabled(bool(self._last_top25))
        self._btn_qs_advisor.setText("🦉 Athena wecken")
        self._btn_qs_advisor_send.setEnabled(bool(self._qs_advisor_history))
        if hasattr(self, "_qs_athena"):
            self._qs_athena.stop_working()


# ---------------------------------------------------------------------------
# QsAdvisorWorker – unterstützt Chat-History und Folgefragen
# ---------------------------------------------------------------------------
from PySide6.QtCore import QThread, Signal as _Signal
import json as _json
import urllib.request as _urllib_req
import urllib.error as _urllib_err


class _QsAdvisorWorker(QThread):
    result_ready   = _Signal(str)
    error_occurred = _Signal(str)

    def __init__(
        self,
        context: dict,
        system_prompt: str,
        api_key: str,
        history=None,
        user_question=None,
    ):
        super().__init__()
        self._context       = context
        self._system_prompt = system_prompt
        self._api_key       = api_key
        self._history       = list(history) if history else []
        self._user_question = user_question

    def run(self):
        try:
            ctx_json = _json.dumps(
                self._context, ensure_ascii=False, indent=2, default=str
            )

            if self._user_question is None:
                # Erster Call: vollständiger Report
                messages = [{
                    "role":    "user",
                    "content": (
                        "Analysiere diesen Quick Scan und erstelle den Report:\n\n"
                        + ctx_json
                    ),
                }]
            else:
                # Folgefrage mit History + kompaktem Kontext-Header
                ctx_header = (
                    f"[QS-Kontext: {self._context.get('anzahl_treffer_total', '?')} Treffer, "
                    f"{len(self._context.get('scan_ziel', {}).get('filter', []))} Filter, "
                    f"{len(self._context.get('scan_ziel', {}).get('targets', []))} Targets]"
                )
                messages = list(self._history) + [{
                    "role":    "user",
                    "content": f"{ctx_header}\n\n{self._user_question}",
                }]

            payload = _json.dumps({
                "model":       "claude-sonnet-5",
                "max_tokens":  128000,
                "system":      self._system_prompt,
                "messages":    messages,
            }).encode("utf-8")

            req = _urllib_req.Request(
                "https://api.anthropic.com/v1/messages",
                data=payload,
                headers={
                    "Content-Type":      "application/json",
                    "x-api-key":         self._api_key,
                    "anthropic-version": "2023-06-01",
                },
                method="POST",
            )
            with _urllib_req.urlopen(req, timeout=300) as resp:
                result = _json.loads(resp.read().decode("utf-8"))

            # Token-Tracking
            try:
                from ui.advisor_worker import update_token_usage
                usage = result.get("usage", {})
                update_token_usage(
                    usage.get("input_tokens", 0),
                    usage.get("output_tokens", 0),
                )
            except Exception:
                pass

            text = "\n".join(
                b.get("text", "") for b in result.get("content", [])
                if b.get("type") == "text"
            ).strip()

            self.result_ready.emit(text or "Keine Antwort erhalten.")

        except _urllib_err.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8")
            except Exception:
                pass
            self.error_occurred.emit(f"HTTP {e.code}: {e.reason}\n\n{body}")
        except Exception as e:
            self.error_occurred.emit(f"{type(e).__name__}: {e}")