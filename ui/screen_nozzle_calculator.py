# ui/screen_nozzle_calculator.py
"""Amortisation Calculator für Heberlein-Düsen.

Layout: Inputs links (General / Competitor / Heberlein), Results rechts.

Änderungen v2:
  - Druck-Feld aus General entfernt; je eigenes Druckfeld in Competitor + Heberlein
  - bar / PSI-Toggle pro Druckfeld (Button schaltet Einheit + konvertiert Wert)
  - Währung wählbar: CHF, EUR, USD, CNY, GBP (beeinflusst alle Geldbeträge + KPI-Labels)
  - QComboBox mit eigenem Stylesheet (kein System-Dropdown-Look)

Formel: Q [Nm³/h] = k * C * P_abs,  P_abs = bar_g + 1
         k = DB-Wert tblJets.Luftverbrauch, falls die Düse aus der DB stammt und
             der Wert gesetzt (> 0) ist; sonst Näherung k = _CD * D²
         _CD = 0.562 / 1.1² ≈ 0.4645  (Referenz: 1.1mm → 0.562 Nm³/h @ 0 bar gauge)
PSI → bar: bar = psi / 14.5038
"""

from typing import Optional, Callable, List, Dict, Tuple

from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QPainterPath
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QSizePolicy, QLineEdit, QComboBox, QScrollArea, QMessageBox,
    QGridLayout, QMenu, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView,
)

from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from ui.theme import get_accent, DARK, LIGHT_BG, CARD_BG, TEXT


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PSI_PER_BAR = 14.5038

# Flow factor derived from Heberlein reference measurement:
# D_ref=1.1mm → Q_ref=0.562 Nm³/h at P_abs=1 bar_a (0 bar gauge = ambient)
# Formula: Q = _CD * C * D[mm]² * P_abs[bar_a]
# _CD = Q_ref / (D_ref² * P_abs_ref) = 0.562 / (1.1² * 1.0) = 0.46446...
_CD = 0.562 / (1.1 ** 2 * 1.0)   # ≈ 0.4645

CURRENCIES: List[Tuple[str, str]] = [
    ("CHF", "CHF"),
    ("EUR", "€"),
    ("USD", "$"),
    ("CNY", "¥"),
    ("GBP", "£"),
]
# Default cost/Nm³ per currency (rough equivalents)
DEFAULT_COST: Dict[str, str] = {
    "CHF": "0.04",
    "EUR": "0.04",
    "USD": "0.04",
    "CNY": "0.30",
    "GBP": "0.03",
}
DEFAULT_NOZZLE_PRICE: Dict[str, str] = {
    "CHF": "100",
    "EUR": "95",
    "USD": "105",
    "CNY": "720",
    "GBP": "82",
}

# ---------------------------------------------------------------------------
# StyledComboBox — custom dropdown, no system-theme interference
# ---------------------------------------------------------------------------

class StyledComboBox(QFrame):
    """Custom combo box built from QFrame + QLineEdit + QPushButton.

    Uses a QMenu for the dropdown — fully styled, no native widget quirks.
    API is intentionally similar to QComboBox so call sites need minimal changes.

    Signals:
        currentIndexChanged(int)
    """

    currentIndexChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[tuple] = []   # [(text, user_data), ...]
        self._current_idx = -1

        self.setObjectName("StyledComboBox")
        self._refresh_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._display = QLineEdit()
        self._display.setReadOnly(True)
        self._display.setPlaceholderText("—")
        self._display.setCursor(Qt.PointingHandCursor)
        self._display.setStyleSheet(
            "QLineEdit { border: none; background: transparent; "
            f"color: {TEXT}; font-size: 13px; padding: 0 6px; }}"
        )
        self._display.mousePressEvent = lambda e: self._open_menu()
        layout.addWidget(self._display, 1)

        self._arrow_btn = QPushButton("▾")
        self._arrow_btn.setFixedWidth(32)
        self._arrow_btn.setCursor(Qt.PointingHandCursor)
        self._arrow_btn.clicked.connect(self._open_menu)
        layout.addWidget(self._arrow_btn)

        self.setFixedHeight(34)
        self._style_arrow()

    def _refresh_style(self):
        accent = get_accent()
        self.setStyleSheet(
            f"QFrame#StyledComboBox {{ border: 1px solid {accent}; "
            f"border-radius: 1px; background: white; }}"
        )

    def _style_arrow(self):
        accent = get_accent()
        self._arrow_btn.setStyleSheet(
            f"QPushButton {{ border: none; border-left: 1px solid #d8d8d8; "
            f"background: #f5f5f5; color: {accent}; font-size: 14px; "
            f"font-weight: 900; padding: 0; margin: 0; border-radius: 0; }}"
            f"QPushButton:hover {{ background: #ececec; }}"
            f"QPushButton:pressed {{ background: {accent}; color: white; }}"
        )

    def _open_menu(self):
        if not self._items:
            return
        accent = get_accent()
        # tint
        h = accent.lstrip("#")
        ar, ag, ab = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        tint = f"#{int(ar*.18+255*.82):02x}{int(ag*.18+255*.82):02x}{int(ab*.18+255*.82):02x}"

        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ border: 1px solid #cfcfcf; background: white; "
            f"color: {TEXT}; font-size: 13px; padding: 3px 0; }}"
            f"QMenu::item {{ padding: 7px 18px; min-width: 160px; }}"
            f"QMenu::item:selected {{ background: {tint}; color: {TEXT}; }}"
            f"QMenu::item:checked {{ background: {accent}; color: white; font-weight: 700; }}"
            f"QMenu::separator {{ height: 1px; background: #efefef; margin: 2px 0; }}"
        )

        for i, (text, _) in enumerate(self._items):
            action = menu.addAction(text)
            action.setCheckable(True)
            action.setChecked(i == self._current_idx)
            idx = i
            action.triggered.connect(lambda checked, ix=idx: self._select(ix))

        # Show directly below the widget
        menu.exec(self.mapToGlobal(self.rect().bottomLeft()))

    def _select(self, idx: int):
        if idx == self._current_idx:
            return
        self._current_idx = idx
        self._display.setText(self._items[idx][0] if self._items else "")
        self.currentIndexChanged.emit(idx)

    # ── QComboBox-compatible API ──────────────────────────────────────

    def addItem(self, text: str, userData=None):
        self._items.append((text, userData))
        if self._current_idx == -1:
            self._current_idx = 0
            self._display.setText(text)

    def clear(self):
        self._items.clear()
        self._current_idx = -1
        self._display.clear()

    def count(self) -> int:
        return len(self._items)

    def currentIndex(self) -> int:
        return self._current_idx

    def setCurrentIndex(self, idx: int):
        if 0 <= idx < len(self._items):
            self._current_idx = idx
            self._display.setText(self._items[idx][0])
        elif idx == 0 and not self._items:
            self._current_idx = -1
            self._display.clear()

    def currentData(self):
        if 0 <= self._current_idx < len(self._items):
            return self._items[self._current_idx][1]
        return None

    def currentText(self) -> str:
        if 0 <= self._current_idx < len(self._items):
            return self._items[self._current_idx][0]
        return ""

    def itemData(self, idx: int):
        if 0 <= idx < len(self._items):
            return self._items[idx][1]
        return None

    def blockSignals(self, block: bool) -> bool:
        return super().blockSignals(block)

    def setSizeAdjustPolicy(self, *a): pass   # no-op, kept for compat
    def setMinimumContentsLength(self, *a): pass   # no-op

    def refresh_accent(self):
        self._refresh_style()
        self._style_arrow()


# ---------------------------------------------------------------------------
# Air consumption formula
# ---------------------------------------------------------------------------

def _bar_g_from_input(value: float, unit: str) -> float:
    """Convert gauge pressure input to bar_g."""
    if unit == "PSI":
        return value / PSI_PER_BAR
    return value  # already bar


def _flow_coeff_per_hole(diameter_mm: float, luftverbrauch: Optional[float] = None) -> float:
    """Nm³/h Luftverbrauch pro Bohrung bei P_abs=1 bar_a.

    Nimmt den echten DB-Wert (tblJets.Luftverbrauch), falls vorhanden und > 0
    (deckt gemessene Abweichungen von der reinen D²-Näherung ab, v.a. bei
    grossen Bohrungen). Fehlt der Wert (NULL/0) oder ist die Düse gar nicht
    in der DB (z.B. Wettbewerber-Düse), wird wie bisher über _CD * D² genähert.
    """
    try:
        lv = float(luftverbrauch) if luftverbrauch is not None else 0.0
    except (TypeError, ValueError):
        lv = 0.0
    if lv > 0:
        return lv
    return _CD * (diameter_mm ** 2)


def _air_flow_nm3h(diameter_mm: float, num_holes: int, pressure_bar_g: float,
                    luftverbrauch: Optional[float] = None) -> float:
    p_abs = max(pressure_bar_g, 0.0) + 1.0
    coeff = _flow_coeff_per_hole(diameter_mm, luftverbrauch)
    return coeff * num_holes * p_abs


# ---------------------------------------------------------------------------
# Shared widget helpers
# ---------------------------------------------------------------------------

def _card(title: str):
    """Returns (outer QFrame card, body QVBoxLayout)."""
    card = QFrame()
    card.setObjectName("Card")
    card.setStyleSheet(
        f"QFrame#Card {{ background: {CARD_BG}; border: 1px solid #cfcfcf; border-radius: 2px; }}"
    )
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
    body.setSpacing(6)
    outer.addLayout(body)
    return card, body


def _flbl(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color: {TEXT}; font-size: 12px; font-weight: 600;")
    return lbl


def _unit_lbl(text: str, width: int = 50) -> QLabel:
    lbl = QLabel(text)
    lbl.setFixedWidth(width)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet(
        "color: #666; font-size: 11px; background: #f0f0f0; "
        "border: 1px solid #d0d0d0; border-radius: 1px; padding: 5px 2px;"
    )
    return lbl


def _le(value: str = "", placeholder: str = "", readonly: bool = False) -> QLineEdit:
    w = QLineEdit()
    w.setPlaceholderText(placeholder)
    if value:
        w.setText(value)
    if readonly:
        w.setReadOnly(True)
        w.setStyleSheet("background: #f5f5f5; color: #888;")
    return w


def _style_toggle(btn: QPushButton, active: bool):
    accent = get_accent()
    if active:
        btn.setStyleSheet(
            f"QPushButton {{ border: 1px solid {accent}; border-radius: 2px; "
            f"background: {accent}; color: white; font-size: 12px; font-weight: 700; "
            f"padding: 5px 8px; }}"
            f"QPushButton:hover {{ background: {accent}; }}"
        )
    else:
        btn.setStyleSheet(
            "QPushButton { border: 1px solid #d0d0d0; border-radius: 2px; "
            "background: white; color: #444; font-size: 12px; font-weight: 400; "
            "padding: 5px 8px; }"
            "QPushButton:hover { background: #f5f5f5; }"
        )


def _kpi_widget(title: str, unit: str):
    """Returns (outer QFrame, value QLabel, unit QLabel)."""
    frame = QFrame()
    frame.setStyleSheet(
        f"QFrame {{ background: {CARD_BG}; border: 1px solid #e0e0e0; border-radius: 3px; }}"
    )
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(10, 8, 10, 8)
    lay.setSpacing(2)
    t = QLabel(title)
    t.setStyleSheet("color: #888; font-size: 10px; border: none;")
    t.setWordWrap(True)
    v = QLabel("—")
    v.setStyleSheet(f"color: {get_accent()}; font-size: 20px; font-weight: 700; border: none;")
    u = QLabel(unit)
    u.setStyleSheet("color: #aaa; font-size: 10px; border: none;")
    lay.addWidget(t)
    lay.addWidget(v)
    lay.addWidget(u)
    return frame, v, u


# ---------------------------------------------------------------------------
# Pressure field helper — field + bar|PSI toggle button
# ---------------------------------------------------------------------------

class PressureField(QWidget):
    """QLineEdit + bar/PSI toggle button combo.

    Stores value internally always in bar_g.
    The toggle button switches display unit and converts the displayed value.
    """

    def __init__(self, default_bar: float = 4.0, parent=None):
        super().__init__(parent)
        self._unit = "bar"   # current display unit

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._le = QLineEdit(f"{default_bar:.2g}")
        layout.addWidget(self._le, 1)

        self._btn = QPushButton("bar")
        self._btn.setFixedWidth(46)
        self._btn.setFixedHeight(self._le.sizeHint().height())
        self._btn.setToolTip("Switch between bar and PSI")
        self._btn.clicked.connect(self._toggle_unit)
        self._style_btn()
        layout.addWidget(self._btn)

    def _style_btn(self):
        accent = get_accent()
        self._btn.setText(self._unit)
        self._btn.setStyleSheet(
            f"QPushButton {{ border: 1px solid {accent}; border-radius: 1px; "
            f"background: {accent}; color: white; font-size: 11px; font-weight: 700; "
            f"padding: 4px 6px; }}"
            f"QPushButton:hover {{ background: {accent}cc; }}"
        )

    def _toggle_unit(self):
        try:
            current_val = float(self._le.text().replace(",", "."))
        except ValueError:
            current_val = 0.0

        if self._unit == "bar":
            # switch to PSI
            self._unit = "PSI"
            converted = current_val * PSI_PER_BAR
            self._le.setText(f"{converted:.2f}")
        else:
            # switch to bar
            self._unit = "bar"
            converted = current_val / PSI_PER_BAR
            self._le.setText(f"{converted:.3g}")

        self._style_btn()

    def bar_value(self) -> float:
        """Returns current pressure as bar_g (converts from PSI if needed)."""
        try:
            val = float(self._le.text().replace(",", "."))
        except ValueError:
            return 0.0
        return _bar_g_from_input(val, self._unit)

    def unit(self) -> str:
        return self._unit

    def raw_text(self) -> str:
        return self._le.text()

    def reset(self, default_bar: float = 4.0):
        self._unit = "bar"
        self._le.setText(f"{default_bar:.2g}")
        self._style_btn()


# ---------------------------------------------------------------------------
# Chart
# ---------------------------------------------------------------------------

class MultiJetChart(QWidget):
    """Cumulative cost chart: Jet A (status quo) vs Jet B (with investment).
    Shows break-even point where B becomes cheaper than A."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._results = []
        self._total_saving = 0.0
        self._total_invest = 0.0
        self._sym = ""
        self.setMinimumHeight(200)

    def set_data(self, results, total_saving, total_invest, sym):
        self._results = results
        self._total_saving = total_saving
        self._total_invest = total_invest
        self._sym = sym
        self.update()

    def paintEvent(self, event):
        if not self._results:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        GREEN  = QColor("#39A650")
        GREY   = QColor("#999999")
        RED    = QColor("#e53935")
        TEXT_C = QColor("#555555")
        GRID_C = QColor("#ebebeb")
        FILL_C = QColor(57, 166, 80, 30)   # green fill between curves

        W, H = self.width(), self.height()
        ml, mr, mt, mb = 68, 16, 16, 42  # extra bottom for legend
        cw = W - ml - mr
        ch = H - mt - mb

        p.fillRect(0, 0, W, H, QColor(CARD_BG))

        total_saving = self._total_saving
        total_invest = self._total_invest
        if total_saving <= 0 and total_invest <= 0:
            return

        # 5-year cumulative data points (year 0..5)
        years = list(range(6))
        # Jet A cumulative: air costs only (no investment)
        a_cum = [total_saving * y for y in years]
        # Jet B cumulative: investment upfront + 0 ongoing saving (savings reduce cost)
        # Cost of sticking with A vs switching to B:
        # A_total_cost(t) = t * saving_yr  (what we lose by NOT switching)
        # B_total_cost(t) = invest - t * saving_yr  (negative = profit)
        # Break-even when invest = t * saving_yr → t = invest / saving_yr
        b_cum = [max(0.0, total_invest - total_saving * y) for y in years]

        max_val = max(max(a_cum), max(b_cum), 1)

        def tx(i): return ml + i / (len(years) - 1) * cw
        def ty(v): return mt + ch - v / max_val * ch

        # Grid
        for i in range(5):
            yy = mt + i * ch // 4
            p.setPen(QPen(GRID_C, 0.5))
            p.drawLine(ml, yy, W - mr, yy)
            val = max_val * (1 - i / 4)
            s = f"{val/1000:.0f}k" if val >= 1000 else f"{val:.0f}"
            p.setPen(QPen(TEXT_C, 1))
            p.setFont(QFont("Arial", 7))
            p.drawText(0, int(yy) - 6, ml - 4, 14,
                       Qt.AlignRight | Qt.AlignVCenter, s)

        # Axes
        p.setPen(QPen(QColor("#bbbbbb"), 0.8))
        p.drawLine(ml, mt, ml, mt + ch)
        p.drawLine(ml, mt + ch, W - mr, mt + ch)

        # X labels
        p.setPen(QPen(TEXT_C, 1))
        p.setFont(QFont("Arial", 7))
        for i, yr in enumerate(years):
            p.drawText(int(tx(i)) - 15, mt + ch + 4, 30, 16,
                       Qt.AlignCenter, str(yr))
        p.drawText(ml, mt + ch + 20, cw, 14, Qt.AlignCenter, "Year")

        # Savings fill (area where B < A, i.e. B has paid off)
        if total_invest > 0 and total_saving > 0:
            be_yr = total_invest / total_saving
            if be_yr < 5:
                # Fill from break-even to year 5
                from PySide6.QtGui import QPainterPath
                path = QPainterPath()
                be_x = tx(0) + be_yr / 5 * cw
                path.moveTo(be_x, ty(total_invest - total_saving * be_yr))
                for i in range(int(be_yr) + 1, 6):
                    path.lineTo(tx(i), ty(b_cum[i]))
                for i in range(5, int(be_yr), -1):
                    path.lineTo(tx(i), ty(a_cum[i]))
                path.closeSubpath()
                p.fillPath(path, FILL_C)

        # Draw Jet A line (grey — cumulative savings foregone)
        p.setPen(QPen(GREY, 2))
        for i in range(len(years) - 1):
            p.drawLine(int(tx(i)), int(ty(a_cum[i])),
                       int(tx(i+1)), int(ty(a_cum[i+1])))
        # Dots
        p.setBrush(GREY)
        for i in range(len(years)):
            p.drawEllipse(int(tx(i)) - 3, int(ty(a_cum[i])) - 3, 6, 6)

        # Draw Jet B line (green — remaining cost after investment)
        p.setPen(QPen(GREEN, 2))
        p.setBrush(GREEN)
        for i in range(len(years) - 1):
            p.drawLine(int(tx(i)), int(ty(b_cum[i])),
                       int(tx(i+1)), int(ty(b_cum[i+1])))
        for i in range(len(years)):
            p.drawEllipse(int(tx(i)) - 3, int(ty(b_cum[i])) - 3, 6, 6)

        # Break-even vertical line
        if total_saving > 0 and total_invest > 0:
            be_yr = total_invest / total_saving
            if 0 < be_yr < 5:
                be_x = int(tx(0) + be_yr / 5 * cw)
                p.setPen(QPen(RED, 1, Qt.DashLine))
                p.drawLine(be_x, mt, be_x, mt + ch)
                p.setFont(QFont("Arial", 7, QFont.Bold))
                p.setPen(QPen(RED, 1))
                label = f"Break-even: {be_yr:.2f} yr"
                lx = be_x + 4 if be_yr < 3.5 else be_x - 90
                p.drawText(lx, mt + ch // 2, 90, 14, Qt.AlignLeft, label)

        # Legend — top-left inside plot area, clean box
        p.setFont(QFont("Arial", 8))
        lx, ly = ml + 8, mt + 8
        leg_w, leg_h = 130, 34
        # Background box
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 200))
        p.drawRoundedRect(lx, ly, leg_w, leg_h, 4, 4)
        p.setBrush(Qt.NoBrush)
        # Row 1: Jet A
        p.setPen(QPen(GREY, 2))
        p.drawLine(lx + 6, ly + 11, lx + 20, ly + 11)
        p.setPen(QPen(TEXT_C, 1))
        p.drawText(lx + 24, ly + 4, leg_w - 26, 14,
                   Qt.AlignLeft | Qt.AlignVCenter, "Jet A  (status quo)")
        # Row 2: Jet B
        p.setPen(QPen(GREEN, 2))
        p.drawLine(lx + 6, ly + 24, lx + 20, ly + 24)
        p.setPen(QPen(TEXT_C, 1))
        p.drawText(lx + 24, ly + 17, leg_w - 26, 14,
                   Qt.AlignLeft | Qt.AlignVCenter, "Jet B  (investment)")

        p.end()


class AirFlowChart(QWidget):
    _HIT_RADIUS = 18

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(340)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMouseTracking(True)
        self._comp: List[float] = []
        self._heb:  List[float] = []
        self._years: List[int] = []
        self._currency_sym = "CHF"
        self._nozzle_cost: float = 0.0   # total nozzle investment (year 0)
        self._breakeven_yr: Optional[float] = None   # fractional year of intersection
        self._hover: Optional[tuple] = None

    def set_data(self, comp_cost_yr: float, heb_cost_yr: float,
                 nozzle_price: float, n_pos: int,
                 currency_sym: str = "CHF", years: int = 5):
        self._years = list(range(0, years + 1))
        total_nozzle = nozzle_price * n_pos
        self._nozzle_cost = total_nozzle
        self._comp = [comp_cost_yr * y * n_pos for y in self._years]
        self._heb  = [heb_cost_yr  * y * n_pos + total_nozzle for y in self._years]
        self._currency_sym = currency_sym

        # Break-even: comp_cost_yr * t == heb_cost_yr * t + total_nozzle
        # t = total_nozzle / (comp_cost_yr - heb_cost_yr) * n_pos ... already per-position
        saving_yr = (comp_cost_yr - heb_cost_yr) * n_pos
        if saving_yr > 0:
            self._breakeven_yr = total_nozzle / saving_yr
            if self._breakeven_yr > years:
                self._breakeven_yr = None   # outside chart range
        else:
            self._breakeven_yr = None

        self._hover = None
        self.update()

    def _layout(self):
        W, H = self.width(), self.height()
        pl, pr, pt, pb = 66, 18, 14, 34
        cw, ch = W - pl - pr, H - pt - pb
        all_v = self._comp + self._heb
        mx = max(all_v) if all_v and max(all_v) > 0 else 1
        n = len(self._years)
        def tx(i): return pl + i / (n - 1) * cw
        def ty(v): return pt + ch - v / mx * ch
        def tx_yr(yr): return pl + yr / (n - 1) * cw   # fractional year
        return pl, pr, pt, pb, cw, ch, tx, ty, mx, tx_yr

    def mouseMoveEvent(self, event):
        if len(self._years) < 2:
            return
        pl, pr, pt, pb, cw, ch, tx, ty, mx, tx_yr = self._layout()
        try:
            mx_pos = event.position().x()
            my_pos = event.position().y()
        except AttributeError:
            mx_pos = event.x()
            my_pos = event.y()

        best = None
        best_dist = self._HIT_RADIUS
        for si, series in enumerate([self._comp, self._heb]):
            for i, v in enumerate(series):
                dx = tx(i) - mx_pos
                dy = ty(v) - my_pos
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    best = (si, i)

        if best != self._hover:
            self._hover = best
            self.update()

    def leaveEvent(self, event):
        self._hover = None
        self.update()

    def paintEvent(self, event):
        if len(self._years) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        pl, pr, pt, pb, cw, ch, tx, ty, mx, tx_yr = self._layout()
        accent = get_accent()

        # ── Grid ──────────────────────────────────────────────────────
        p.setPen(QPen(QColor("#ebebeb"), 1))
        for i in range(5):
            p.drawLine(pl, int(pt + i * ch / 4), W - pr, int(pt + i * ch / 4))

        # ── Savings fill (area between curves where Heberlein < Competitor) ──
        if self._comp and self._heb:
            # Build polygon: comp forward, heb backward
            fill_path = QPainterPath()
            # Only fill where comp > heb (savings region)
            started = False
            pts_comp = [(tx(i), ty(v)) for i, v in enumerate(self._comp)]
            pts_heb  = [(tx(i), ty(v)) for i, v in enumerate(self._heb)]
            for i in range(len(self._years)):
                cx_, cy_ = pts_comp[i]
                hx_, hy_ = pts_heb[i]
                if cy_ > hy_:   # comp pixel-y > heb pixel-y means comp value < heb value — skip
                    started = False
                    continue
                if not started:
                    fill_path.moveTo(cx_, cy_)
                    started = True
                else:
                    fill_path.lineTo(cx_, cy_)
            # reverse along heb line
            visible = [i for i in range(len(self._years))
                       if pts_comp[i][1] <= pts_heb[i][1]]
            for i in reversed(visible):
                fill_path.lineTo(pts_heb[i][0], pts_heb[i][1])
            fill_path.closeSubpath()

            # parse accent hex to RGBA fill
            ah = accent.lstrip("#")
            ar, ag, ab = int(ah[0:2], 16), int(ah[2:4], 16), int(ah[4:6], 16)
            fill_color = QColor(ar, ag, ab, 35)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(fill_color))
            p.drawPath(fill_path)
            p.setBrush(Qt.NoBrush)

        # ── Axes ──────────────────────────────────────────────────────
        p.setPen(QPen(QColor("#bbb"), 1))
        p.drawLine(pl, pt, pl, pt + ch)
        p.drawLine(pl, pt + ch, W - pr, pt + ch)

        fnt = QFont()
        fnt.setPointSize(8)
        p.setFont(fnt)
        p.setPen(QColor("#777"))

        for i, yr in enumerate(self._years):
            p.drawText(int(tx(i)) - 12, pt + ch + 3, 24, 17, Qt.AlignCenter, str(yr))
        for i in range(5):
            yy = int(pt + i * ch / 4)
            val = mx - i * mx / 4
            s = f"{val/1000:.0f}k" if val >= 10000 else f"{val:,.0f}"
            p.drawText(0, yy - 7, pl - 4, 14, Qt.AlignRight | Qt.AlignVCenter, s)
        p.drawText(pl, pt + ch + 19, cw, 13, Qt.AlignCenter, "Year")

        # ── Break-even vertical line ───────────────────────────────────
        if self._breakeven_yr is not None:
            bx = int(tx_yr(self._breakeven_yr))
            dash_pen = QPen(QColor("#e53935"), 1.5, Qt.DashLine)
            p.setPen(dash_pen)
            p.drawLine(bx, pt, bx, pt + ch)
            # Label
            fnt_be = QFont()
            fnt_be.setPointSize(8)
            fnt_be.setBold(True)
            p.setFont(fnt_be)
            p.setPen(QColor("#e53935"))
            label = f"Break-even: {self._breakeven_yr:.1f} yr"
            lw = p.fontMetrics().horizontalAdvance(label) + 6
            lx_be = bx + 4
            if lx_be + lw > W - pr:
                lx_be = bx - lw - 4
            # small background pill
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(255, 255, 255, 200)))
            p.drawRoundedRect(lx_be - 2, pt + 2, lw + 4, 15, 3, 3)
            p.setPen(QColor("#e53935"))
            p.drawText(lx_be, pt + 2, lw, 15, Qt.AlignLeft | Qt.AlignVCenter, label)
            p.setFont(fnt)   # restore

        # ── Series lines + dots ───────────────────────────────────────
        def _draw(data, color, si):
            pen = QPen(QColor(color), 2)
            p.setPen(pen)
            path = QPainterPath()
            for i, v in enumerate(data):
                x, y = tx(i), ty(v)
                path.moveTo(x, y) if i == 0 else path.lineTo(x, y)
            p.drawPath(path)
            for i, v in enumerate(data):
                is_hov = (self._hover == (si, i))
                r = 6 if is_hov else 3
                p.setBrush(QBrush(QColor(color)))
                p.setPen(QPen(QColor("white"), 1.5) if is_hov else Qt.NoPen)
                p.drawEllipse(QPointF(tx(i), ty(v)), r, r)
            p.setBrush(Qt.NoBrush)

        _draw(self._comp, "#aaaaaa", 0)
        _draw(self._heb,  accent,    1)

        # ── Legend ────────────────────────────────────────────────────
        lx, ly = pl + 8, pt + 5
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#aaaaaa")))
        p.drawRect(lx, ly + 2, 14, 3)
        p.setFont(fnt)
        p.setPen(QColor("#555"))
        p.drawText(lx + 18, ly - 2, 90, 12, Qt.AlignLeft | Qt.AlignVCenter, "Competitor")
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(accent)))
        p.drawRect(lx, ly + 17, 14, 3)
        p.setPen(QColor("#555"))
        p.drawText(lx + 18, ly + 13, 90, 12, Qt.AlignLeft | Qt.AlignVCenter, "Heberlein")

        # currency label top-right
        fnt_sm = QFont()
        fnt_sm.setPointSize(7)
        p.setFont(fnt_sm)
        p.setPen(QColor("#aaa"))
        p.drawText(W - pr - 60, pt, 60, 12, Qt.AlignRight | Qt.AlignVCenter,
                   f"({self._currency_sym})")

        # ── Hover tooltip ─────────────────────────────────────────────
        if self._hover is not None:
            si, pi = self._hover
            series = self._comp if si == 0 else self._heb
            label  = "Competitor" if si == 0 else "Heberlein"
            color  = "#aaaaaa"    if si == 0 else accent
            yr     = self._years[pi]
            val    = series[pi]
            sym    = self._currency_sym

            # Savings at this year (comp - heb, can be negative)
            if pi < len(self._comp) and pi < len(self._heb):
                saving_here = self._comp[pi] - self._heb[pi]
            else:
                saving_here = 0.0

            line1 = f"{label}  —  Year {yr}"
            line2 = f"Cumul. cost:  {val:,.0f} {sym}"
            # For Heberlein year 0: show the nozzle investment
            if si == 1 and pi == 0:
                line3 = f"Jet investment:  {self._nozzle_cost:,.0f} {sym}"
            elif saving_here != 0:
                sign = "+" if saving_here > 0 else ""
                line3 = f"Cumul. saving:  {sign}{saving_here:,.0f} {sym}"
            else:
                line3 = ""

            px_pt, py_pt = tx(pi), ty(val)

            fnt_tt = QFont()
            fnt_tt.setPointSize(9)
            p.setFont(fnt_tt)
            pad = 8
            fm = p.fontMetrics()
            lines = [l for l in [line1, line2, line3] if l]
            bw = max(fm.horizontalAdvance(l) for l in lines) + pad * 2 + 8
            bh = fm.height() * len(lines) + pad * 2 + (len(lines) - 1) * 3

            bx = int(px_pt) - bw // 2
            by = int(py_pt) - bh - 14
            if bx + bw > W - pr:
                bx = W - pr - bw - 4
            if bx < pl:
                bx = pl
            if by < 2:
                by = int(py_pt) + 14

            # Shadow
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(0, 0, 0, 22)))
            p.drawRoundedRect(bx + 2, by + 2, bw, bh, 4, 4)
            # Box
            p.setBrush(QBrush(QColor("#ffffff")))
            p.setPen(QPen(QColor(color), 1.5))
            p.drawRoundedRect(bx, by, bw, bh, 4, 4)
            # Colour bar
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(color)))
            p.drawRoundedRect(bx, by, 4, bh, 2, 2)

            lh = fm.height()
            for row_i, line in enumerate(lines):
                yy = by + pad + row_i * (lh + 3)
                fnt_row = QFont()
                fnt_row.setPointSize(9)
                fnt_row.setBold(row_i == 0)
                p.setFont(fnt_row)
                if row_i == 0:
                    p.setPen(QColor("#333"))
                elif row_i == 2 and saving_here > 0 and not (si == 1 and pi == 0):
                    p.setPen(QColor("#2e7d32"))   # green for positive saving
                else:
                    p.setPen(QColor("#555"))
                p.drawText(bx + pad + 4, yy, bw - pad - 4, lh,
                           Qt.AlignLeft | Qt.AlignVCenter, line)

        p.end()


# ---------------------------------------------------------------------------
# Main Screen
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# PDF Report generator
# ---------------------------------------------------------------------------

def _generate_pdf(path: str, d: Dict, chart_widget=None):
    """Generate a 2-page A4 PDF report matching the Heberlein calculator style."""
    import datetime
    import tempfile
    import os

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm, mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable, Image as RLImage,
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

    # ── Colours ───────────────────────────────────────────────────────
    HEB_GREEN  = colors.HexColor("#39A650")
    HEB_DARK   = colors.HexColor("#1D3557")
    ROW_LIGHT  = colors.HexColor("#F2F9F3")
    ROW_HEAD   = colors.HexColor("#39A650")
    GREY_TEXT  = colors.HexColor("#555555")
    BLACK      = colors.black
    WHITE      = colors.white

    PW, PH = A4
    margin = 1.8 * cm

    # ── Styles ────────────────────────────────────────────────────────
    def _s(name, **kw):
        return ParagraphStyle(name, **kw)

    s_title   = _s("title",   fontSize=13, fontName="Helvetica-Bold",
                   textColor=HEB_DARK, spaceAfter=2, spaceBefore=6)
    s_h1      = _s("h1",      fontSize=13, fontName="Helvetica-Bold",
                   textColor=HEB_DARK, spaceBefore=10, spaceAfter=4)
    s_normal  = _s("normal",  fontSize=9,  fontName="Helvetica",
                   textColor=GREY_TEXT, leading=14)
    s_small   = _s("small",   fontSize=8,  fontName="Helvetica",
                   textColor=GREY_TEXT)
    s_footer  = _s("footer",  fontSize=7.5, fontName="Helvetica",
                   textColor=GREY_TEXT)
    s_green   = _s("green",   fontSize=11, fontName="Helvetica-Bold",
                   textColor=HEB_GREEN)
    s_prose   = _s("prose",   fontSize=9,  fontName="Helvetica",
                   textColor=GREY_TEXT, leading=14, spaceAfter=4)

    sym  = d["sym"]
    date = datetime.date.today().strftime("%d.%m.%Y")

    def _pstr(bar_val, unit):
        if unit == "PSI":
            return f"{bar_val * PSI_PER_BAR:.1f} PSI"
        return f"{bar_val:.2f} bar"

    comp_p_str = _pstr(d["comp_pressure"], d["comp_p_unit"])
    heb_p_str  = _pstr(d["heb_pressure"],  d["heb_p_unit"])
    amort_str  = "N/A" if d["amort"] == float("inf") else f"{d['amort']:.2f} years"

    # ── Table helper ──────────────────────────────────────────────────
    col_w = [PW - 2 * margin - 5 * cm, 5 * cm]

    def _section_table(section_label, rows, has_subheader=False):
        """Build a styled 2-column table with green section header."""
        data = [[Paragraph(f"<b>{section_label}</b>",
                           _s("th", fontSize=9, fontName="Helvetica-Bold",
                              textColor=WHITE)), ""]]
        for label, value in rows:
            data.append([
                Paragraph(label, s_normal),
                Paragraph(str(value), s_normal),
            ])
        ts = TableStyle([
            # Section header row
            ("BACKGROUND",   (0, 0), (-1, 0), HEB_GREEN),
            ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
            ("SPAN",         (0, 0), (-1, 0)),
            ("TOPPADDING",   (0, 0), (-1, 0), 5),
            ("BOTTOMPADDING",(0, 0), (-1, 0), 5),
            ("LEFTPADDING",  (0, 0), (-1, 0), 8),
            # Data rows
            ("FONTSIZE",     (0, 1), (-1, -1), 9),
            ("TOPPADDING",   (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 1), (-1, -1), 4),
            ("LEFTPADDING",  (0, 1), (-1, -1), 8),
            ("RIGHTPADDING", (0, 1), (-1, -1), 8),
            ("LINEBELOW",    (0, 1), (-1, -2), 0.4, colors.HexColor("#E0E0E0")),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, ROW_LIGHT]),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ])
        t = Table(data, colWidths=col_w)
        t.setStyle(ts)
        return t

    # ── Header logo helper ────────────────────────────────────────────
    def _logo_row():
        """Returns header logo table (left: heb_logo, right: header_logo)."""
        from ui.pathutil import resource_path
        logo_l = resource_path("assets/images/heb_logo.png")
        logo_r = resource_path("assets/images/header_logo_big.png")
        cells = []
        if logo_l and os.path.exists(logo_l):
            cells.append(RLImage(logo_l, width=6.5*cm, height=2.0*cm,
                                 kind="proportional"))
        else:
            cells.append(Paragraph("HEBERLEIN", _s("lg", fontSize=14,
                                   fontName="Helvetica-Bold", textColor=HEB_GREEN)))
        if logo_r and os.path.exists(logo_r):
            cells.append(RLImage(logo_r, width=2.0*cm, height=1.4*cm,
                                 kind="proportional"))
        else:
            cells.append("")
        logo_w = PW - 2 * margin
        t = Table([cells], colWidths=[logo_w * 0.6, logo_w * 0.4])
        t.setStyle(TableStyle([
            ("ALIGN",  (1, 0), (1, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return t

    # ── Chart: draw natively in reportlab (vector, crisp at any size) ─
    def _build_rl_chart(comp_data, heb_data, years, currency_sym, width, height):
        """Returns a reportlab Drawing of the cumulative cost chart."""
        from reportlab.graphics.shapes import (
            Drawing, Line, String, Rect, Polygon, PolyLine, Group,
        )
        from reportlab.graphics import renderPDF
        from reportlab.lib.colors import HexColor, Color

        GREEN   = HexColor("#39A650")
        GREY    = HexColor("#aaaaaa")
        GRID_C  = HexColor("#ebebeb")
        AXIS_C  = HexColor("#bbbbbb")
        TEXT_C  = HexColor("#777777")
        FILL_C  = Color(0.224, 0.647, 0.314, alpha=0.12)

        d = Drawing(width, height)

        # Margins inside drawing
        ml, mr, mt, mb = 58, 14, 12, 36  # extra bottom margin for legend row
        cw = width  - ml - mr
        ch = height - mt - mb

        all_v = comp_data + heb_data
        mx = max(all_v) if all_v and max(all_v) > 0 else 1
        n  = len(years)

        def tx(i):   return ml + i / (n - 1) * cw
        def ty(v):   return mb + v / mx * ch   # RL: y=0 at bottom

        # Grid lines
        for i in range(5):
            yy = mb + i * ch / 4
            d.add(Line(ml, yy, width - mr, yy,
                       strokeColor=GRID_C, strokeWidth=0.5))

        # Savings fill polygon (comp > heb region)
        fill_pts = []
        visible = [i for i in range(n) if comp_data[i] >= heb_data[i]]
        if visible:
            for i in visible:
                fill_pts.append(tx(i)); fill_pts.append(ty(comp_data[i]))
            for i in reversed(visible):
                fill_pts.append(tx(i)); fill_pts.append(ty(heb_data[i]))
            d.add(Polygon(fill_pts,
                          fillColor=FILL_C, strokeColor=None))

        # Axes
        d.add(Line(ml, mb, ml, mb + ch, strokeColor=AXIS_C, strokeWidth=0.8))
        d.add(Line(ml, mb, width - mr, mb, strokeColor=AXIS_C, strokeWidth=0.8))

        # X labels (years)
        for i, yr in enumerate(years):
            x = tx(i)
            d.add(String(x, mb - 10, str(yr),
                         fontSize=7, fillColor=TEXT_C,
                         textAnchor="middle"))
        # X axis label
        d.add(String(ml + cw / 2, mb - 18, "Year",
                     fontSize=7, fillColor=TEXT_C, textAnchor="middle"))

        # Y labels
        for i in range(5):
            yy = mb + i * ch / 4
            val = i * mx / 4
            s = f"{val/1000:.0f}k" if val >= 10000 else f"{val:,.0f}"
            d.add(String(ml - 4, yy - 3, s,
                         fontSize=6.5, fillColor=TEXT_C,
                         textAnchor="end"))

        # Break-even line
        if len(comp_data) == len(heb_data) == n:
            for i in range(n - 1):
                c0, c1 = comp_data[i], comp_data[i + 1]
                h0, h1 = heb_data[i],  heb_data[i + 1]
                if (c0 - h0) * (c1 - h1) <= 0 and (c0 != h0 or c1 != h1):
                    diff0 = c0 - h0
                    diff1 = c1 - h1
                    if diff1 != diff0:
                        t = diff0 / (diff0 - diff1)
                        bx = tx(i) + t * (tx(i + 1) - tx(i))
                        d.add(Line(bx, mb, bx, mb + ch,
                                   strokeColor=HexColor("#e53935"),
                                   strokeWidth=1,
                                   strokeDashArray=[3, 3]))
                        be_yr = years[i] + t
                        label = f"Break-even: {be_yr:.1f} yr"
                        # Label: place to right of line at mid-height, or left if near right edge
                        label_x = bx + 3 if bx < width * 0.7 else bx - 3
                        anchor = "start" if bx < width * 0.7 else "end"
                        label_y = mb + ch * 0.45   # mid-height — clear of both legend corners
                        d.add(String(label_x, label_y, label,
                                     fontSize=6.5,
                                     fillColor=HexColor("#e53935"),
                                     fontName="Helvetica-Bold",
                                     textAnchor=anchor))
                    break

        # Draw polylines
        def _line(data, color, dash=False):
            pts = []
            for i, v in enumerate(data):
                pts.append(tx(i)); pts.append(ty(v))
            kw = dict(strokeColor=color, strokeWidth=1.5, fillColor=None)
            if dash:
                kw["strokeDashArray"] = [4, 2]
            d.add(PolyLine(pts, **kw))
            # Dots
            for i, v in enumerate(data):
                d.add(Line(tx(i) - 2.5, ty(v), tx(i) + 2.5, ty(v),
                           strokeWidth=0))  # invisible anchor
                from reportlab.graphics.shapes import Circle
                d.add(Circle(tx(i), ty(v), 2.5,
                             fillColor=color, strokeColor=None))

        _line(comp_data, GREY)
        _line(heb_data,  GREEN)

        # Legend — outside chart area, below X-axis labels (always collision-free)
        leg_y = 4   # below X-axis label row
        cx = ml + cw / 2   # center of chart
        # Competitor left of center, Heberlein right
        d.add(Line(cx - 75, leg_y, cx - 63, leg_y,
                   strokeColor=GREY, strokeWidth=1.5))
        d.add(String(cx - 60, leg_y - 3, "Competitor",
                     fontSize=6.5, fillColor=TEXT_C))
        d.add(Line(cx + 5, leg_y, cx + 17, leg_y,
                   strokeColor=GREEN, strokeWidth=1.5))
        d.add(String(cx + 20, leg_y - 3, "Heberlein",
                     fontSize=6.5, fillColor=TEXT_C))

        # Currency label top-right, inside chart but above plot area
        d.add(String(width - mr, mb + ch + 2, f"({currency_sym})",
                     fontSize=6, fillColor=TEXT_C,
                     textAnchor="end"))

        return d

    # ── Build story ───────────────────────────────────────────────────
    story = []

    # ── PAGE 1: Logo + inputs ─────────────────────────────────────────
    story.append(_logo_row())
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=HEB_GREEN))
    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph("Calculator", s_title))
    story.append(Spacer(1, 0.15 * cm))

    story.append(_section_table("General", [
        ("Process",                d["process"]),
        ("Number of positions",    str(d["n_pos"])),
        ("Operating hours / year", f"{d['h_yr']:,.0f}"),
        ("Air cost / Nm³",    f"{d['cost_m3']} {sym}"),
        ("Heberlein jet price",    f"{d['nozzle_px']} {sym}"),
    ]))
    story.append(Spacer(1, 0.25 * cm))

    story.append(_section_table("Competitor Jet", [
        ("Jet type",             d["comp_type"] or "—"),
        ("Air hole diameter",    f"{d['comp_diam']} mm"),
        ("No. of air holes (C)", str(d["comp_holes"])),
        ("Air pressure",         comp_p_str),
    ]))
    story.append(Spacer(1, 0.25 * cm))

    mode_label = "DB Selection" if d["heb_mode"] == "product" else "Manual Entry"
    story.append(_section_table(f"Heberlein Jet — {mode_label}", [
        ("Jet type",             d["heb_type"] or "—"),
        ("Air hole diameter",    f"{d['heb_diam']:.4f} mm"),
        ("No. of air holes (C)", str(d["heb_holes"])),
        ("Air pressure",         heb_p_str),
    ]))
    story.append(Spacer(1, 0.25 * cm))

    story.append(_section_table("Result", [
        ("Savings per day",          f"{d['saving_day']:,.2f} {sym}"),
        ("Savings per year",         f"{d['saving_yr']:,.2f} {sym}"),
        ("Total jet cost (all pos.)", f"{d['total_nozzle']:,.2f} {sym}"),
        ("Amortisation",             amort_str),
        ("Air saving",               f"{d['saving_pct']:.1f} %"),
    ]))

    # ── PAGE 2: Chart + Prose ─────────────────────────────────────────
    story.append(PageBreak())
    story.append(_logo_row())
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=HEB_GREEN))
    story.append(Spacer(1, 0.25 * cm))

    story.append(Paragraph("Air Consumption over Time", s_h1))
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#CCCCCC")))
    story.append(Spacer(1, 0.15 * cm))

    chart_w = PW - 2 * margin
    chart_h = chart_w * 0.36
    # Build vector chart from stored data
    try:
        years_list  = list(range(0, 6))
        n_pos       = d["n_pos"]
        nozzle_px   = d["nozzle_px"]
        comp_cost_yr = d["comp_cost_yr"]
        heb_cost_yr  = d["heb_cost_yr"]
        comp_data = [comp_cost_yr * y * n_pos for y in years_list]
        heb_data  = [heb_cost_yr  * y * n_pos + nozzle_px * n_pos
                     for y in years_list]
        rl_chart = _build_rl_chart(
            comp_data, heb_data, years_list,
            d["sym"], chart_w, chart_h
        )
        story.append(rl_chart)
    except Exception:
        story.append(Spacer(1, chart_h))

    story.append(Spacer(1, 0.45 * cm))

    story.append(Paragraph(
        "<b>Air Consumption Reduction with a Heberlein Jet</b>", s_h1
    ))
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#CCCCCC")))
    story.append(Spacer(1, 0.2 * cm))

    saving_qh_one = d["comp_qh"]  - d["heb_qh"]
    saving_qh_all = saving_qh_one * d["n_pos"]
    saving_qday   = saving_qh_all * 24
    saving_qyr    = saving_qh_all * d["h_yr"]

    def _green(val, unit="m³"):
        return Paragraph(f'<font color="#39A650"><b>{val}</b></font> {unit}', s_prose)

    half = (PW - 2 * margin - 1 * cm) / 2
    saving_table = Table([
        [Paragraph("Air saving per jet per hour:",  s_prose),
         Paragraph("Air saving all jets per hour:", s_prose)],
        [_green(f"{saving_qh_one:.2f}"),
         _green(f"{saving_qh_all:.2f}")],
        [Paragraph("Air saving all jets per day:",  s_prose),
         Paragraph("Air saving all jets per year:", s_prose)],
        [_green(f"{saving_qday:.2f}"),
         _green(f"{saving_qyr:,.2f}")],
    ], colWidths=[half, half])
    saving_table.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",   (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
    ]))
    story.append(saving_table)
    story.append(Spacer(1, 0.4 * cm))

    be = d["be_bar"]
    if be != float("inf") and be > 0:
        be_val = (f"{be * PSI_PER_BAR:.1f} PSI"
                  if d["heb_p_unit"] == "PSI" else f"{be:.2f} bar")
        story.append(Paragraph(
            f'At equal air consumption to the competitor jet, the pressure can be raised '
            f'to <font color="#39A650"><b>{be_val}</b></font> when using a Heberlein jet.',
            s_prose
        ))

    # ── Footer on every page ──────────────────────────────────────────
    def _add_footer(canvas_obj, doc_obj):
        canvas_obj.saveState()
        canvas_obj.setFont("Helvetica", 7.5)
        canvas_obj.setFillColor(GREY_TEXT)
        canvas_obj.drawString(margin, 1.2 * cm,
                              f"Calculation date: {date}")
        canvas_obj.drawRightString(PW - margin, 1.2 * cm,
                                   f"Page {doc_obj.page}")
        canvas_obj.setStrokeColor(colors.HexColor("#E0E0E0"))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(margin, 1.5 * cm, PW - margin, 1.5 * cm)
        canvas_obj.restoreState()

    # ── Build PDF ─────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=1.5 * cm, bottomMargin=2 * cm,
        title="Heberlein Jet ROI Calculator",
        author="Heberlein Technology AG",
    )
    doc.build(story, onFirstPage=_add_footer, onLaterPages=_add_footer)


def _generate_multi_pdf(path: str, results: list, totals: dict):
    """Generate A4 PDF for Multi-Jet Comparison — same Heberlein style as single-jet."""
    import datetime, os

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm, mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, Image as RLImage, KeepTogether,
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.graphics.shapes import (
        Drawing, Line, String, Rect, PolyLine, Polygon,
    )
    from reportlab.lib.colors import HexColor, Color

    HEB_GREEN = colors.HexColor("#39A650")
    HEB_DARK  = colors.HexColor("#1D3557")
    ROW_LIGHT = colors.HexColor("#F2F9F3")
    GREY_TEXT = colors.HexColor("#555555")
    WHITE     = colors.white

    PW, PH = A4
    margin = 1.8 * cm

    def _s(name, **kw):
        return ParagraphStyle(name, **kw)

    s_title  = _s("t",  fontSize=13, fontName="Helvetica-Bold",
                  textColor=HEB_DARK, spaceAfter=2, spaceBefore=6)
    s_h1     = _s("h1", fontSize=13, fontName="Helvetica-Bold",
                  textColor=HEB_DARK, spaceBefore=10, spaceAfter=4)
    s_normal = _s("n",  fontSize=9,  fontName="Helvetica",
                  textColor=GREY_TEXT, leading=14)
    s_small  = _s("sm", fontSize=8,  fontName="Helvetica",
                  textColor=GREY_TEXT)
    s_footer = _s("ft", fontSize=7.5, fontName="Helvetica",
                  textColor=GREY_TEXT)

    sym  = totals.get("sym", "CHF")
    date = datetime.date.today().strftime("%d.%m.%Y")

    # ── Footer ────────────────────────────────────────────────────────
    def _add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(GREY_TEXT)
        canvas.drawString(margin, 1.3 * cm, f"Calculation date: {date}")
        canvas.drawRightString(PW - margin, 1.3 * cm, f"Page {doc.page}")
        try:
            import pathlib
            lp = pathlib.Path(__file__).resolve().parents[1] / "assets" / "images" / "heb_logo.png"
            if lp.exists():
                canvas.drawImage(str(lp), margin, PH - 2.6*cm,
                                 width=5.0*cm, height=1.4*cm,
                                 preserveAspectRatio=True, mask="auto")
            rp = pathlib.Path(__file__).resolve().parents[1] / "assets" / "images" / "header_logo_big.png"
            if rp.exists():
                canvas.drawImage(str(rp), PW - margin - 2.0*cm, PH - 2.6*cm,
                                 width=2.0*cm, height=1.4*cm,
                                 preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
        canvas.setStrokeColor(HEB_GREEN)
        canvas.setLineWidth(1.2)
        canvas.line(margin, PH - 2.8*cm, PW - margin, PH - 2.8*cm)
        canvas.restoreState()

    # ── Section table helper (identical style to single-jet) ──────────
    col_w = [PW - 2*margin - 5*cm, 5*cm]

    def _section_table(label, rows):
        data = [[Paragraph(f"<b>{label}</b>",
                           _s("th", fontSize=9, fontName="Helvetica-Bold",
                              textColor=WHITE)), ""]]
        for lbl, val in rows:
            data.append([Paragraph(lbl, s_normal),
                         Paragraph(str(val), s_normal)])
        style = TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0), HEB_GREEN),
            ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
            ("SPAN",         (0, 0), (-1, 0)),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [ROW_LIGHT, WHITE]),
            ("FONTNAME",     (0, 1), (-1,-1), "Helvetica"),
            ("FONTSIZE",     (0, 1), (-1,-1), 9),
            ("TEXTCOLOR",    (0, 1), (-1,-1), GREY_TEXT),
            ("BOTTOMPADDING",(0, 0), (-1,-1), 5),
            ("TOPPADDING",   (0, 0), (-1,-1), 5),
            ("LEFTPADDING",  (0, 0), (-1,-1), 8),
            ("RIGHTPADDING", (0, 0), (-1,-1), 8),
            ("GRID",         (0, 0), (-1,-1), 0.4, colors.HexColor("#D0D0D0")),
        ])
        return Table(data, colWidths=col_w, style=style)

    # ── Per-comparison table ──────────────────────────────────────────
    def _comparison_table(results, sym):
        headers = ["Label", "Jet A", "Jet B", "Hours / yr",
                   f"Air Saving / yr ({sym})", f"Investment ({sym})", "Break-even"]
        data = [[Paragraph(f"<b>{h}</b>",
                           _s("ch", fontSize=8, fontName="Helvetica-Bold",
                              textColor=WHITE)) for h in headers]]
        for res in results:
            be = res.get("net_invest", 0)
            sav = res.get("saving_yr", 0)
            if be <= 0:
                be_s = "—"
            elif sav <= 0:
                be_s = "∞"
            else:
                be_s = f"{be/sav:.2f} yr"
            inv_s = f"{res.get('net_invest',0):,.0f}" if res.get("net_invest",0) > 0 else "0"
            data.append([
                Paragraph(res.get("label",""), s_normal),
                Paragraph(res.get("a_name",""), s_normal),
                Paragraph(res.get("b_name",""), s_normal),
                Paragraph(f"{res.get('h_yr',0):,.0f} h", s_normal),
                Paragraph(f"{res.get('saving_yr',0):,.0f}", s_normal),
                Paragraph(inv_s, s_normal),
                Paragraph(be_s, s_normal),
            ])
        # Totals row
        total_sav = totals.get("saving", 0)
        total_inv = totals.get("invest", 0)
        total_be  = (f"{total_inv/total_sav:.2f} yr"
                     if total_sav > 0 and total_inv > 0 else "—")
        data.append([
            Paragraph("<b>Total</b>", _s("tb", fontSize=9, fontName="Helvetica-Bold",
                                         textColor=HEB_DARK)),
            Paragraph("—", s_small), Paragraph("—", s_small),
            Paragraph("—", s_small),
            Paragraph(f"<b>{total_sav:,.0f}</b>",
                      _s("tv", fontSize=9, fontName="Helvetica-Bold", textColor=HEB_GREEN)),
            Paragraph(f"<b>{total_inv:,.0f}</b>",
                      _s("ti", fontSize=9, fontName="Helvetica-Bold", textColor=HEB_DARK)),
            Paragraph(f"<b>{total_be}</b>",
                      _s("tbe", fontSize=9, fontName="Helvetica-Bold", textColor=HEB_DARK)),
        ])
        ncols = len(headers)
        col_w2 = (PW - 2*margin) / ncols
        style = TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), HEB_GREEN),
            ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
            ("ROWBACKGROUNDS",(0, 1), (-1,-2), [ROW_LIGHT, WHITE]),
            ("BACKGROUND",    (0,-1), (-1,-1), colors.HexColor("#E8F5EC")),
            ("LINEABOVE",     (0,-1), (-1,-1), 1, HEB_GREEN),
            ("FONTNAME",      (0, 1), (-1,-1), "Helvetica"),
            ("FONTSIZE",      (0, 0), (-1,-1), 8),
            ("TEXTCOLOR",     (0, 1), (-1,-2), GREY_TEXT),
            ("BOTTOMPADDING", (0, 0), (-1,-1), 5),
            ("TOPPADDING",    (0, 0), (-1,-1), 5),
            ("LEFTPADDING",   (0, 0), (-1,-1), 6),
            ("RIGHTPADDING",  (0, 0), (-1,-1), 6),
            ("GRID",          (0, 0), (-1,-1), 0.4, colors.HexColor("#D0D0D0")),
        ])
        return Table(data, colWidths=[col_w2]*ncols, style=style)

    # ── Break-even chart (same style as single-jet) ───────────────────
    def _build_be_chart(total_saving, total_invest, sym, width, height):
        d = Drawing(width, height)
        if total_saving <= 0:
            return d
        GREEN  = HexColor("#39A650")
        GREY   = HexColor("#999999")
        RED    = HexColor("#e53935")
        TEXT_C = HexColor("#555555")
        GRID_C = HexColor("#ebebeb")
        FILL_C = Color(0.224, 0.647, 0.314, alpha=0.12)

        ml, mr, mt, mb = 68, 16, 16, 36
        cw = width - ml - mr
        ch = height - mt - mb
        years = list(range(6))
        # Jet A: cumulative air cost WITH old jets (grows each year)
        a_cum = [total_saving * y for y in years]
        # Jet B: net cost = investment upfront minus cumulative savings
        #   positive = still in debt, negative = profit (cap at 0 for display)
        b_cum = [max(0.0, total_invest - total_saving * y) for y in years]
        # Y-axis: 0 at bottom, max at top
        # a_cum grows UP (saving opportunity cost), b_cum falls DOWN to 0
        max_val = max(max(a_cum), max(b_cum), 1)

        def tx(i): return ml + i / 5 * cw
        # v=0 → bottom (mb), v=max_val → top (mb+ch)
        def ty(v): return mb + v / max_val * ch

        # Grid (Y=0 at bottom = mb, Y=max at top = mb+ch)
        for i in range(5):
            yy = mb + i * ch / 4
            d.add(Line(ml, yy, width - mr, yy,
                       strokeColor=GRID_C, strokeWidth=0.5))
            val = max_val * i / 4
            s = f"{val/1000:.0f}k" if val >= 1000 else f"{val:.0f}"
            d.add(String(ml - 4, yy - 3, s,
                         fontSize=6.5, fillColor=TEXT_C, textAnchor="end"))

        # Axes
        d.add(Line(ml, mb, ml, mb + ch, strokeColor=HexColor("#bbbbbb"), strokeWidth=0.8))
        d.add(Line(ml, mb, width - mr, mb,
                   strokeColor=HexColor("#bbbbbb"), strokeWidth=0.8))

        # X labels
        for i, yr in enumerate(years):
            d.add(String(tx(i), mb - 12, str(yr),
                         fontSize=7, fillColor=TEXT_C, textAnchor="middle"))
        d.add(String(ml + cw/2, mb - 24, "Year",
                     fontSize=7, fillColor=TEXT_C, textAnchor="middle"))

        # Savings fill (green area between A and B after break-even)
        if total_invest > 0 and total_saving > 0:
            be_yr = total_invest / total_saving
            if 0 < be_yr < 5:
                be_x = ml + be_yr / 5 * cw
                from reportlab.graphics.shapes import Polygon as RLPoly
                # After break-even: A is above B → fill between them
                fill_pts = [be_x, ty(total_invest - total_saving * be_yr)]
                for i in range(int(be_yr) + 1, 6):
                    fill_pts += [tx(i), ty(a_cum[i])]
                for i in range(5, int(be_yr), -1):
                    fill_pts += [tx(i), ty(b_cum[i])]
                fill_pts += [be_x, ty(total_invest - total_saving * be_yr)]
                if len(fill_pts) >= 6:
                    d.add(RLPoly(fill_pts, fillColor=FILL_C, strokeColor=None))

        # Lines
        for i in range(5):
            d.add(Line(tx(i), ty(a_cum[i]), tx(i+1), ty(a_cum[i+1]),
                       strokeColor=GREY, strokeWidth=1.5))
            d.add(Line(tx(i), ty(b_cum[i]), tx(i+1), ty(b_cum[i+1]),
                       strokeColor=GREEN, strokeWidth=1.5))

        # Dots
        for i in range(6):
            from reportlab.graphics.shapes import Circle
            d.add(Circle(tx(i), ty(a_cum[i]), 3, fillColor=GREY, strokeColor=None))
            d.add(Circle(tx(i), ty(b_cum[i]), 3, fillColor=GREEN, strokeColor=None))

        # Break-even line
        if total_invest > 0 and total_saving > 0 and 0 < total_invest/total_saving < 5:
            be_yr = total_invest / total_saving
            be_x  = ml + be_yr / 5 * cw
            d.add(Line(be_x, mb, be_x, mb + ch,
                       strokeColor=RED, strokeWidth=1,
                       strokeDashArray=[3, 3]))
            label = f"Break-even: {be_yr:.2f} yr"
            lx = be_x + 4 if be_yr < 3.5 else be_x - 90
            d.add(String(lx, mb + ch * 0.45, label,
                         fontSize=6.5, fillColor=RED,
                         fontName="Helvetica-Bold"))

        # Legend bottom-centre (below x-axis labels)
        cx = ml + cw / 2
        ly = 6
        d.add(Line(cx - 80, ly, cx - 68, ly, strokeColor=GREY, strokeWidth=1.5))
        d.add(String(cx - 65, ly - 3, "Jet A  (status quo)",
                     fontSize=6.5, fillColor=TEXT_C))
        d.add(Line(cx + 10, ly, cx + 22, ly, strokeColor=GREEN, strokeWidth=1.5))
        d.add(String(cx + 25, ly - 3, "Jet B  (investment)",
                     fontSize=6.5, fillColor=TEXT_C))
        d.add(String(width - mr, mb + ch + 2, f"({sym})",
                     fontSize=6, fillColor=TEXT_C, textAnchor="end"))
        return d

    # ── Build story ───────────────────────────────────────────────────
    story = []

    # Header line + spacing (logos drawn by _add_footer on canvas)
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("Multi-Jet Comparison", s_title))
    story.append(Spacer(1, 0.15*cm))

    # General section
    story.append(_section_table("General", [
        ("Currency",         sym),
        ("Air cost / Nm³",   f"{totals.get('cost_m3', 0):.4f} {sym}"),
    ]))
    story.append(Spacer(1, 0.3*cm))

    # Totals section
    total_sav = totals.get("saving", 0)
    total_inv = totals.get("invest", 0)
    total_be  = (f"{total_inv/total_sav:.2f} years"
                 if total_sav > 0 and total_inv > 0 else "N/A")
    story.append(_section_table("Summary", [
        ("Total Air Saving / yr",  f"{total_sav:,.0f} {sym}"),
        ("Total Investment",       f"{total_inv:,.0f} {sym}"),
        ("Break-even",             total_be),
        ("Avg Air Saving",         f"{totals.get('air_pct', 0):.1f} %"),
    ]))
    story.append(Spacer(1, 0.3*cm))

    # Per-comparison breakdown
    story.append(Paragraph("Per-Comparison Breakdown", s_h1))
    story.append(_comparison_table(results, sym))
    story.append(Spacer(1, 0.4*cm))

    # Page 2: chart
    from reportlab.platypus import PageBreak
    story.append(PageBreak())
    story.append(Paragraph("Cumulative Cost: Jet A vs Jet B", s_h1))
    story.append(HRFlowable(width="100%", thickness=0.8, color=HEB_GREEN))
    story.append(Spacer(1, 0.3*cm))

    chart_w = PW - 2 * margin
    chart_h = chart_w * 0.36
    story.append(_build_be_chart(
        totals.get("saving", 0),
        totals.get("invest", 0),
        sym, chart_w, chart_h
    ))

    # Build
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=3.2*cm, bottomMargin=2*cm,
        title="Heberlein Multi-Jet Comparison",
        author="Heberlein Technology AG",
    )
    doc.build(story, onFirstPage=_add_footer, onLaterPages=_add_footer)


class NozzleCalculatorScreen(QWidget):
    """Single-page jet ROI calculator.

    Left  : inputs — General / Competitor / Heberlein
    Right : results — KPIs / chart / detail table
    """

    def __init__(
        self,
        on_back_home: Optional[Callable[[], None]] = None,
        jets_loader: Optional[Callable[[], List[Dict]]] = None,
        parent: Optional[QWidget] = None,
        sidebar_callbacks: Optional[dict] = None,
    ):
        super().__init__(parent)
        self._on_back_home = on_back_home
        self._jets_loader  = jets_loader
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None
        self._jet_rows: List[Dict] = []
        self._all_jets: List[Dict] = []
        self._calc_mode: str = "single"
        self._heb_mode = "product"
        self._process  = "DTY"
        self._currency_code = "CHF"   # current currency code
        self._currency_sym  = "CHF"   # symbol/code shown in UI

        self._build_ui()
        self._load_jets()

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring).
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        # ── Mode toggle bar ───────────────────────────────────────────
        toggle_bar = QWidget()
        toggle_bar.setFixedHeight(40)
        toggle_bar.setStyleSheet(f"background: {CARD_BG}; border-bottom: 1px solid #cfcfcf;")
        tbl = QHBoxLayout(toggle_bar)
        tbl.setContentsMargins(22, 4, 22, 4)
        tbl.setSpacing(8)
        self._btn_single_mode = QPushButton("Single Jet")
        self._btn_multi_mode  = QPushButton("Multi-Jet Comparison")
        for btn in (self._btn_single_mode, self._btn_multi_mode):
            btn.setFixedHeight(30)
            tbl.addWidget(btn)
        tbl.addStretch()
        self._btn_single_mode.clicked.connect(lambda: self._set_calc_mode("single"))
        self._btn_multi_mode.clicked.connect(lambda: self._set_calc_mode("multi"))
        content_layout.addWidget(toggle_bar, 0)

        # ── Stacked content ───────────────────────────────────────────
        from PySide6.QtWidgets import QStackedWidget
        self._mode_stack = QStackedWidget()
        self._mode_stack.setStyleSheet(f"background: {LIGHT_BG};")

        # ── Single mode ───────────────────────────────────────────────
        single_scroll = QScrollArea()
        single_scroll.setWidgetResizable(True)
        single_scroll.setStyleSheet(f"background: {LIGHT_BG}; border: none;")
        single_body = QWidget()
        single_body.setStyleSheet(f"background: {LIGHT_BG};")
        single_layout = QHBoxLayout(single_body)
        single_layout.setContentsMargins(22, 18, 22, 18)
        single_layout.setSpacing(18)
        single_layout.setAlignment(Qt.AlignTop)

        left_col = QVBoxLayout()
        left_col.setSpacing(12)
        left_col.setAlignment(Qt.AlignTop)
        left_col.addWidget(self._build_general_card())
        left_col.addWidget(self._build_competitor_card())
        left_col.addWidget(self._build_heberlein_card())

        btn_calc = QPushButton("Calculate →")
        btn_calc.setObjectName("GreenBtn")
        btn_calc.setFixedHeight(40)
        btn_calc.clicked.connect(self._calculate)
        left_col.addWidget(btn_calc)

        btn_reset = QPushButton("Reset")
        btn_reset.setFixedHeight(34)
        btn_reset.clicked.connect(self._reset)
        left_col.addWidget(btn_reset)

        self._btn_export = QPushButton("Export PDF")
        self._btn_export.setObjectName("GreenBtn")
        self._btn_export.setFixedHeight(34)
        self._btn_export.clicked.connect(self._export_pdf)
        self._btn_export.setVisible(False)
        left_col.addWidget(self._btn_export)

        left_w = QWidget()
        left_w.setFixedWidth(440)
        left_w.setStyleSheet("background: transparent;")
        left_w.setLayout(left_col)

        right_col = QVBoxLayout()
        right_col.setSpacing(12)
        right_col.setAlignment(Qt.AlignTop)
        right_col.addWidget(self._build_result_card())

        right_w = QWidget()
        right_w.setStyleSheet("background: transparent;")
        right_w.setLayout(right_col)

        single_layout.addWidget(left_w,  0, Qt.AlignTop)
        single_layout.addWidget(right_w, 1)
        single_scroll.setWidget(single_body)

        # ── Multi mode ────────────────────────────────────────────────
        multi_scroll = QScrollArea()
        multi_scroll.setWidgetResizable(True)
        multi_scroll.setStyleSheet(f"background: {LIGHT_BG}; border: none;")
        multi_body = self._build_multi_mode()
        multi_scroll.setWidget(multi_body)

        self._mode_stack.addWidget(single_scroll)   # index 0
        self._mode_stack.addWidget(multi_scroll)    # index 1

        content_layout.addWidget(self._mode_stack, 1)
        root.addWidget(FooterBar(), 0)

        # Init toggle style
        self._calc_mode = "single"
        self._update_mode_btns()

    # ------------------------------------------------------------------
    # General card
    # ------------------------------------------------------------------

    def _build_general_card(self) -> QFrame:
        card, body = _card("General")

        # Process toggle
        proc_row = QHBoxLayout()
        proc_row.setSpacing(4)
        self._btn_aty  = QPushButton("ATY")
        self._btn_dty  = QPushButton("DTY")
        self._btn_spin = QPushButton("Spinning")
        for btn in (self._btn_aty, self._btn_dty, self._btn_spin):
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setFixedHeight(32)
            proc_row.addWidget(btn)
        self._btn_aty.clicked.connect(lambda: self._set_process("ATY"))
        self._btn_dty.clicked.connect(lambda: self._set_process("DTY"))
        self._btn_spin.clicked.connect(lambda: self._set_process("Spinning"))
        body.addLayout(proc_row)
        self._update_process_btns()

        g = QGridLayout()
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(5)
        g.setColumnStretch(1, 1)
        row_i = 0

        # Positions
        self._le_positions = _le("1")
        g.addWidget(_flbl("Positions"), row_i, 0)
        g.addWidget(self._le_positions, row_i, 1)
        row_i += 1

        # Hours / year
        self._le_hours = _le("8000")
        g.addWidget(_flbl("Hours / year"), row_i, 0)
        g.addWidget(self._le_hours, row_i, 1)
        row_i += 1

        # Currency selector
        self._cb_currency = StyledComboBox()
        
        for code, sym in CURRENCIES:
            self._cb_currency.addItem(f"{code}  ({sym})", code)
        self._cb_currency.currentIndexChanged.connect(self._on_currency_changed)
        g.addWidget(_flbl("Currency"), row_i, 0)
        g.addWidget(self._cb_currency, row_i, 1)
        row_i += 1

        # Air cost / Nm³
        self._le_cost_m3 = _le(DEFAULT_COST["CHF"])
        sub_cost = QHBoxLayout()
        sub_cost.setSpacing(4)
        sub_cost.addWidget(self._le_cost_m3, 1)
        self._lbl_cost_unit = _unit_lbl("CHF", 50)
        sub_cost.addWidget(self._lbl_cost_unit)
        g.addWidget(_flbl("Air cost / Nm³"), row_i, 0)
        g.addLayout(sub_cost, row_i, 1)
        row_i += 1

        # Heberlein jet price
        self._le_nozzle_px = _le(DEFAULT_NOZZLE_PRICE["CHF"])
        sub_px = QHBoxLayout()
        sub_px.setSpacing(4)
        sub_px.addWidget(self._le_nozzle_px, 1)
        self._lbl_px_unit = _unit_lbl("CHF", 50)
        sub_px.addWidget(self._lbl_px_unit)
        g.addWidget(_flbl("Heberlein jet price"), row_i, 0)
        g.addLayout(sub_px, row_i, 1)
        row_i += 1

        body.addLayout(g)
        return card

    # ------------------------------------------------------------------
    # Competitor card
    # ------------------------------------------------------------------

    def _build_competitor_card(self) -> QFrame:
        card, body = _card("Competitor Jet")

        g = QGridLayout()
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(5)
        g.setColumnStretch(1, 1)
        row_i = 0

        self._le_comp_type  = _le(placeholder="e.g. CompXX-3")
        self._le_comp_diam  = _le("1.0")
        self._le_comp_holes = _le("1")
        self._pf_comp       = PressureField(default_bar=4.0)

        for lbl_txt, w, unit in [
            ("Jet type",           self._le_comp_type,  None),
            ("Air hole diameter",     self._le_comp_diam,  "mm"),
            ("No. of air holes (C)",  self._le_comp_holes, None),
            ("Air pressure",          self._pf_comp,       None),
        ]:
            g.addWidget(_flbl(lbl_txt), row_i, 0)
            if unit:
                sub = QHBoxLayout()
                sub.setSpacing(4)
                sub.addWidget(w, 1)
                sub.addWidget(_unit_lbl(unit))
                g.addLayout(sub, row_i, 1)
            else:
                g.addWidget(w, row_i, 1)
            row_i += 1

        body.addLayout(g)
        return card

    # ------------------------------------------------------------------
    # Heberlein card
    # ------------------------------------------------------------------

    def _build_heberlein_card(self) -> QFrame:
        card, body = _card("Heberlein Jet")

        # Mode toggle
        mode_row = QHBoxLayout()
        mode_row.setSpacing(4)
        self._btn_mode_prod = QPushButton("DB Selection")
        self._btn_mode_man  = QPushButton("Manual Entry")
        for btn in (self._btn_mode_prod, self._btn_mode_man):
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setFixedHeight(32)
            mode_row.addWidget(btn)
        self._btn_mode_prod.clicked.connect(lambda: self._set_heb_mode("product"))
        self._btn_mode_man.clicked.connect(lambda: self._set_heb_mode("manual"))
        body.addLayout(mode_row)

        g = QGridLayout()
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(5)
        g.setColumnStretch(1, 1)

        # Pressure field (shared between both modes)
        self._pf_heb = PressureField(default_bar=4.0)

        # Product-mode widgets
        self._cb_jet = StyledComboBox()
        
        self._cb_jet.addItem("— select from DB —", None)
        
        self._cb_jet.setMinimumContentsLength(18)
        self._cb_jet.currentIndexChanged.connect(self._on_jet_selected)
        self._le_heb_diam_auto  = _le(readonly=True, placeholder="auto-filled")
        self._le_heb_holes_prod = _le("1")

        # Manual-mode widgets
        self._le_heb_type_man  = _le(placeholder="e.g. P142-2")
        self._le_heb_diam_man  = _le()
        self._le_heb_holes_man = _le("1")

        self._prod_pairs: List[tuple] = []
        self._man_pairs:  List[tuple] = []

        row_idx = 0
        for lbl_txt, w, unit, store in [
            ("Jet type",          self._cb_jet,           None, self._prod_pairs),
            ("Air hole diameter",    self._le_heb_diam_auto, "mm", self._prod_pairs),
            ("No. of air holes (C)", self._le_heb_holes_prod, None, self._prod_pairs),
            ("Jet type",          self._le_heb_type_man,  None, self._man_pairs),
            ("Air hole diameter",    self._le_heb_diam_man,  "mm", self._man_pairs),
            ("No. of air holes (C)", self._le_heb_holes_man, None, self._man_pairs),
        ]:
            lbl = _flbl(lbl_txt)
            if unit:
                container = QWidget()
                sub = QHBoxLayout(container)
                sub.setContentsMargins(0, 0, 0, 0)
                sub.setSpacing(4)
                sub.addWidget(w, 1)
                sub.addWidget(_unit_lbl(unit))
                w_cell = container
            else:
                w_cell = w
            g.addWidget(lbl,    row_idx, 0)
            g.addWidget(w_cell, row_idx, 1)
            store.append((lbl, w_cell))
            row_idx += 1

        # Pressure row (always visible)
        self._lbl_pf_heb = _flbl("Air pressure")
        g.addWidget(self._lbl_pf_heb, row_idx, 0)
        g.addWidget(self._pf_heb,     row_idx, 1)

        body.addLayout(g)
        self._set_heb_mode("product")
        return card

    # ------------------------------------------------------------------
    # Result card
    # ------------------------------------------------------------------

    def _build_result_card(self) -> QFrame:
        card, body = _card("Result")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._result_placeholder = QLabel(
            "Fill in all inputs on the left,\nthen press  Calculate →"
        )
        self._result_placeholder.setAlignment(Qt.AlignCenter)
        self._result_placeholder.setStyleSheet(
            "color: #bbb; font-size: 13px; padding: 50px 20px;"
        )
        body.addWidget(self._result_placeholder)

        # KPI row
        self._kpi_container = QWidget()
        self._kpi_container.setVisible(False)
        kpi_row = QHBoxLayout(self._kpi_container)
        kpi_row.setContentsMargins(0, 0, 0, 0)
        kpi_row.setSpacing(10)

        self._kf_day,  self._kv_day,  self._ku_day  = _kpi_widget("Savings / Day",      "CHF")
        self._kf_yr,   self._kv_yr,   self._ku_yr   = _kpi_widget("Savings / Year",     "CHF")
        self._kf_cost, self._kv_cost, self._ku_cost = _kpi_widget("Total Jet Cost",  "CHF")
        self._kf_amort,self._kv_amort,self._ku_amort= _kpi_widget("Amortisation",       "years")
        self._kf_pct,  self._kv_pct,  self._ku_pct  = _kpi_widget("Air Saving",         "%")
        for f in (self._kf_day, self._kf_yr, self._kf_cost, self._kf_amort, self._kf_pct):
            kpi_row.addWidget(f)
        body.addWidget(self._kpi_container)

        # Chart
        self._chart_title = QLabel()
        self._chart_title.setStyleSheet(
            f"color: {DARK}; font-size: 11px; font-weight: 600; padding-top: 6px;"
        )
        self._chart_title.setVisible(False)
        body.addWidget(self._chart_title)

        self._chart = AirFlowChart()
        self._chart.setVisible(False)
        body.addWidget(self._chart)

        # Detail table
        self._detail_w = QWidget()
        self._detail_w.setVisible(False)
        dl = QGridLayout(self._detail_w)
        dl.setHorizontalSpacing(14)
        dl.setVerticalSpacing(4)
        dl.setColumnStretch(1, 1)
        dl.setColumnStretch(3, 1)

        self._dv: Dict[str, QLabel] = {}
        keys = [
            ("comp_qh",    "Competitor flow / jet"),
            ("heb_qh",     "Heberlein flow / jet"),
            ("comp_qday",  "Competitor total / day"),
            ("heb_qday",   "Heberlein total / day"),
            ("comp_qyr",   "Competitor total / year"),
            ("heb_qyr",    "Heberlein total / year"),
            ("saving_qyr", "Air saving / year"),
            ("saving_pct", "Air saving"),
            ("break_even", "Break-even pressure (Heberlein)"),
        ]
        split = (len(keys) + 1) // 2
        for idx, (key, label) in enumerate(keys):
            col = (idx // split) * 2
            row = idx % split
            lk = QLabel(label + ":")
            lk.setStyleSheet("color: #666; font-size: 11px;")
            lv = QLabel("—")
            lv.setStyleSheet(f"color: {TEXT}; font-size: 11px; font-weight: 600;")
            dl.addWidget(lk, row, col)
            dl.addWidget(lv, row, col + 1)
            self._dv[key] = lv

        body.addWidget(self._detail_w)

        # ── Prose summary (Heberlein-style) ───────────────────────────
        self._summary_w = QWidget()
        self._summary_w.setVisible(False)
        self._summary_w.setStyleSheet(
            f"background: #f8faf8; border-top: 2px solid #e0ede0; padding: 0px;"
        )
        sum_outer = QVBoxLayout(self._summary_w)
        sum_outer.setContentsMargins(0, 12, 0, 4)
        sum_outer.setSpacing(10)

        # Title
        self._sum_title = QLabel("Air Consumption Reduction with a Heberlein Jet")
        self._sum_title.setStyleSheet(
            f"color: {DARK}; font-size: 13px; font-weight: 700; "
            f"background: transparent; border: none;"
        )
        sum_outer.addWidget(self._sum_title)

        # 2×2 grid of key figures
        self._sum_grid_w = QWidget()
        self._sum_grid_w.setStyleSheet("background: transparent;")
        sg = QGridLayout(self._sum_grid_w)
        sg.setContentsMargins(0, 0, 0, 0)
        sg.setHorizontalSpacing(40)
        sg.setVerticalSpacing(8)
        sg.setColumnStretch(0, 1)
        sg.setColumnStretch(1, 1)

        self._sum_labels: Dict[str, QLabel] = {}
        _accent = get_accent()
        sum_fields = [
            ("qh_one",   "Air saving per jet per hour:",  0, 0),
            ("qh_all",   "Air saving all jets per hour:", 0, 1),
            ("qday_all", "Air saving all jets per day:",  1, 0),
            ("qyr_all",  "Air saving all jets per year:", 1, 1),
        ]
        for key, label_txt, row, col in sum_fields:
            lbl = QLabel(label_txt)
            lbl.setStyleSheet(
                f"color: {TEXT}; font-size: 12px; background: transparent; border: none;"
            )
            val = QLabel("—")
            val.setStyleSheet(
                f"color: {_accent}; font-size: 14px; font-weight: 700; "
                f"background: transparent; border: none;"
            )
            sub = QVBoxLayout()
            sub.setSpacing(1)
            sub.addWidget(lbl)
            sub.addWidget(val)
            sg.addLayout(sub, row, col)
            self._sum_labels[key] = val

        sum_outer.addWidget(self._sum_grid_w)

        # Break-even pressure sentence
        self._sum_be_lbl = QLabel()
        self._sum_be_lbl.setWordWrap(True)
        self._sum_be_lbl.setStyleSheet(
            f"color: {TEXT}; font-size: 12px; background: transparent; border: none;"
        )
        sum_outer.addWidget(self._sum_be_lbl)

        body.addWidget(self._summary_w)
        return card

    # ------------------------------------------------------------------
    # Toggle helpers
    # ------------------------------------------------------------------

    def _set_process(self, val: str):
        self._process = val
        self._update_process_btns()
        self._load_jets()   # refilter dropdown for selected process
        if hasattr(self, "_mj_rows"):
            self._mj_refresh_all_cbs()

    def _update_process_btns(self):
        _style_toggle(self._btn_aty,  self._process == "ATY")
        _style_toggle(self._btn_dty,  self._process == "DTY")
        _style_toggle(self._btn_spin, self._process == "Spinning")
        if hasattr(self, "_mj_btn_aty"):
            _style_toggle(self._mj_btn_aty,  self._process == "ATY")
            _style_toggle(self._mj_btn_dty,  self._process == "DTY")
            _style_toggle(self._mj_btn_spin, self._process == "Spinning")

    def _set_heb_mode(self, mode: str):
        self._heb_mode = mode
        _style_toggle(self._btn_mode_prod, mode == "product")
        _style_toggle(self._btn_mode_man,  mode == "manual")
        for lbl, w in self._prod_pairs:
            lbl.setVisible(mode == "product")
            w.setVisible(mode == "product")
        for lbl, w in self._man_pairs:
            lbl.setVisible(mode == "manual")
            w.setVisible(mode == "manual")

    def _on_currency_changed(self, idx: int):
        code = self._cb_currency.itemData(idx) or "CHF"
        sym  = dict(CURRENCIES).get(code, code)
        self._currency_code = code
        self._currency_sym  = sym
        # Update unit labels next to cost fields
        self._lbl_cost_unit.setText(sym)
        self._lbl_px_unit.setText(sym)
        # Suggest default values when currency changes
        self._le_cost_m3.setText(DEFAULT_COST.get(code, "0.04"))
        self._le_nozzle_px.setText(DEFAULT_NOZZLE_PRICE.get(code, "100"))
        # Update KPI unit labels if results already shown
        for ku in (self._ku_day, self._ku_yr, self._ku_cost):
            ku.setText(sym)

    # ------------------------------------------------------------------
    # Jets
    # ------------------------------------------------------------------

    # Process → filter criteria: (Hersteller, Prozess_exact, JetTypeID)
    # DTY: Prozess < 3  (d.h. 1 oder 2), daher tuple mit max=2
    # ATY / Spinning: Prozess exact match
    _PROCESS_FILTER = {
        "DTY":      {"Hersteller": 1, "Prozess_max": 2, "JetTypeID": 1},
        "ATY":      {"Hersteller": 1, "Prozess": 3,     "JetTypeID": 1},
        "Spinning": {"Hersteller": 1, "Prozess": 4,     "JetTypeID": 1},
    }

    def _jet_matches_process(self, row: Dict) -> bool:
        f = self._PROCESS_FILTER.get(self._process)
        if f is None:
            return True
        try:
            if int(row.get("Hersteller") or 0) != f["Hersteller"]:
                return False
        except (ValueError, TypeError):
            return False
        try:
            if int(row.get("JetTypeID") or 0) != f["JetTypeID"]:
                return False
        except (ValueError, TypeError):
            return False
        try:
            p = int(row.get("Prozess") or 0)
            if "Prozess_max" in f:
                if p > f["Prozess_max"]:   # DTY: Prozess < 3 → Prozess <= 2
                    return False
            else:
                if p != f["Prozess"]:      # ATY / Spinning: exact match
                    return False
        except (ValueError, TypeError):
            return False
        return True

    def _load_jets(self):
        if not callable(self._jets_loader):
            return
        try:
            self._jet_rows = self._jets_loader() or []
        except Exception:
            self._jet_rows = []
            return

        # Store all jets for multi-mode dropdowns
        self._all_jets = self._jet_rows

        # Remember currently selected jet so we can try to restore selection
        prev_data = self._cb_jet.currentData()
        prev_id   = (prev_data.get("ID") if isinstance(prev_data, dict) else None)

        self._cb_jet.blockSignals(True)
        self._cb_jet.clear()
        self._cb_jet.addItem("— select from DB —", None)

        restore_idx = 0
        for row in self._jet_rows:
            if not self._jet_matches_process(row):
                continue
            label = str(row.get("Jet") or f"ID {row.get('ID')}")
            try:
                diam = float(str(row.get("Luftbohrung") or "").replace(",", "."))
            except Exception:
                diam = None
            d = dict(row)
            d["_diam"] = diam
            self._cb_jet.addItem(label, d)
            if prev_id is not None and row.get("ID") == prev_id:
                restore_idx = self._cb_jet.count() - 1

        self._cb_jet.setCurrentIndex(restore_idx)
        self._cb_jet.blockSignals(False)

        # If previously selected jet is no longer visible, clear the auto-fill
        if restore_idx == 0:
            self._le_heb_diam_auto.clear()

        # Populate multi-mode jet dropdowns
        for row_data in self._mj_rows:
            for cb in (row_data.get("a_cb"), row_data.get("b_cb")):
                if cb is not None:
                    self._mj_populate_cb(cb)

    def _on_jet_selected(self, idx: int):
        data = self._cb_jet.itemData(idx)
        if data and isinstance(data, dict):
            diam = data.get("_diam")
            self._le_heb_diam_auto.setText(f"{diam:.4f}" if diam is not None else "")
        else:
            self._le_heb_diam_auto.clear()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self) -> Optional[str]:
        try:
            assert int(self._le_positions.text()) > 0
        except Exception:
            return "Positions: positive integer required."
        try:
            h = float(self._le_hours.text().replace(",", "."))
            assert 0 < h <= 9000
        except Exception:
            return "Hours/year: must be 1–9000."
        try:
            float(self._le_cost_m3.text().replace(",", "."))
        except Exception:
            return f"Air cost/Nm³: invalid number."
        try:
            float(self._le_nozzle_px.text().replace(",", "."))
        except Exception:
            return "Jet price: invalid number."
        # Competitor pressure
        try:
            p = self._pf_comp.bar_value()
            assert 0 < p <= 50
        except Exception:
            return "Competitor pressure: must be > 0."
        if not self._le_comp_type.text().strip():
            return "Competitor: jet type required."
        try:
            d = float(self._le_comp_diam.text().replace(",", "."))
            assert 0 < d <= 10
        except Exception:
            return "Competitor: bore diameter must be 0–10 mm."
        try:
            assert int(self._le_comp_holes.text()) > 0
        except Exception:
            return "Competitor: number of air holes must be >= 1."
        # Heberlein pressure
        try:
            p = self._pf_heb.bar_value()
            assert 0 < p <= 50
        except Exception:
            return "Heberlein pressure: must be > 0."
        if self._heb_mode == "product":
            if self._cb_jet.currentData() is None:
                return "Heberlein: please select a jet from the DB."
            try:
                assert int(self._le_heb_holes_prod.text()) > 0
            except Exception:
                return "Heberlein: number of air holes must be >= 1."
        else:
            if not self._le_heb_type_man.text().strip():
                return "Heberlein: jet type required."
            try:
                d = float(self._le_heb_diam_man.text().replace(",", "."))
                assert 0 < d <= 10
            except Exception:
                return "Heberlein: bore diameter must be 0–10 mm."
            try:
                assert int(self._le_heb_holes_man.text()) > 0
            except Exception:
                return "Heberlein: number of air holes must be >= 1."
        return None

    # ------------------------------------------------------------------
    # Calculate
    # ------------------------------------------------------------------

    def _calculate(self):
        err = self._validate()
        if err:
            QMessageBox.warning(self, "Input Error", err)
            return

        n_pos      = int(self._le_positions.text())
        h_yr       = float(self._le_hours.text().replace(",", "."))
        cost_m3    = float(self._le_cost_m3.text().replace(",", "."))
        nozzle_px  = float(self._le_nozzle_px.text().replace(",", "."))
        sym        = self._currency_sym

        comp_pressure = self._pf_comp.bar_value()
        heb_pressure  = self._pf_heb.bar_value()
        comp_diam     = float(self._le_comp_diam.text().replace(",", "."))
        comp_holes    = int(self._le_comp_holes.text())

        if self._heb_mode == "product":
            data      = self._cb_jet.currentData()
            heb_diam  = float(data.get("_diam") or 0.0)
            heb_holes = int(self._le_heb_holes_prod.text())
            heb_lv    = data.get("Luftverbrauch")
        else:
            heb_diam  = float(self._le_heb_diam_man.text().replace(",", "."))
            heb_holes = int(self._le_heb_holes_man.text())
            heb_lv    = None  # manuelle Eingabe: keine DB-Düse -> Näherung

        comp_qh = _air_flow_nm3h(comp_diam, comp_holes, comp_pressure)
        heb_qh  = _air_flow_nm3h(heb_diam,  heb_holes,  heb_pressure, heb_lv)

        comp_qday = comp_qh * 24
        heb_qday  = heb_qh  * 24
        comp_qyr  = comp_qh * h_yr
        heb_qyr   = heb_qh  * h_yr

        comp_cost_day = comp_qday * cost_m3
        heb_cost_day  = heb_qday  * cost_m3
        comp_cost_yr  = comp_qyr  * cost_m3
        heb_cost_yr   = heb_qyr   * cost_m3

        saving_day   = (comp_cost_day - heb_cost_day) * n_pos
        saving_yr    = (comp_cost_yr  - heb_cost_yr)  * n_pos
        total_nozzle = nozzle_px * n_pos
        amort = total_nozzle / saving_yr if saving_yr > 0 else float("inf")

        saving_qyr = (comp_qyr - heb_qyr) * n_pos
        saving_pct = (comp_qyr - heb_qyr) / comp_qyr * 100 if comp_qyr > 0 else 0.0

        # Break-even: at what heb pressure does flow equal comp flow?
        comp_abs   = comp_pressure + 1.0
        heb_coeff  = _flow_coeff_per_hole(heb_diam,  heb_lv)
        comp_coeff = _flow_coeff_per_hole(comp_diam, None)
        heb_CD2  = heb_holes  * heb_coeff
        comp_CD2 = comp_holes * comp_coeff
        be_bar = (comp_CD2 * comp_abs / heb_CD2 - 1.0) if heb_CD2 > 0 else float("inf")
        # Show break-even in same unit as heb pressure field
        if be_bar == float("inf"):
            be_str = "N/A"
        elif self._pf_heb.unit() == "PSI":
            be_str = f"{be_bar * PSI_PER_BAR:.1f} PSI"
        else:
            be_str = f"{be_bar:.2f} bar"

        # Store full state for PDF export
        self._pdf_data = {
            "process":       self._process,
            "n_pos":         n_pos,
            "h_yr":          h_yr,
            "cost_m3":       cost_m3,
            "nozzle_px":     nozzle_px,
            "sym":           sym,
            "comp_type":     self._le_comp_type.text().strip(),
            "comp_diam":     comp_diam,
            "comp_holes":    comp_holes,
            "comp_pressure": comp_pressure,
            "comp_p_unit":   self._pf_comp.unit(),
            "heb_type":      (self._cb_jet.currentText()
                              if self._heb_mode == "product"
                              else self._le_heb_type_man.text().strip()),
            "heb_diam":      heb_diam,
            "heb_holes":     heb_holes,
            "heb_pressure":  heb_pressure,
            "heb_p_unit":    self._pf_heb.unit(),
            "heb_mode":      self._heb_mode,
            "saving_day":    saving_day,
            "saving_yr":     saving_yr,
            "total_nozzle":  total_nozzle,
            "amort":         amort,
            "comp_qh":       comp_qh,
            "heb_qh":        heb_qh,
            "comp_qday":     comp_qday * n_pos,
            "heb_qday":      heb_qday  * n_pos,
            "comp_qyr":      comp_qyr  * n_pos,
            "heb_qyr":       heb_qyr   * n_pos,
            "saving_qyr":    saving_qyr,
            "saving_pct":    saving_pct,
            "be_bar":        be_bar,
            "be_str":        be_str,
            "comp_cost_yr":  comp_cost_yr,
            "heb_cost_yr":   heb_cost_yr,
        }
        self._kv_day.setText(f"{saving_day:,.2f}")
        self._kv_yr.setText(f"{saving_yr:,.0f}")
        self._kv_cost.setText(f"{total_nozzle:,.0f}")
        self._kv_amort.setText("N/A" if amort == float("inf") else f"{amort:.2f}")
        self._kv_pct.setText(f"{saving_pct:.1f}")
        for ku in (self._ku_day, self._ku_yr, self._ku_cost):
            ku.setText(sym)

        # Detail
        comp_p_str = (f"{comp_pressure * PSI_PER_BAR:.1f} PSI"
                      if self._pf_comp.unit() == "PSI" else f"{comp_pressure:.2f} bar")
        heb_p_str  = (f"{heb_pressure  * PSI_PER_BAR:.1f} PSI"
                      if self._pf_heb.unit() == "PSI"  else f"{heb_pressure:.2f} bar")

        self._dv["comp_qh"].setText(f"{comp_qh:.4f} Nm³/h  @ {comp_p_str}")
        self._dv["heb_qh"].setText(f"{heb_qh:.4f} Nm³/h  @ {heb_p_str}")
        self._dv["comp_qday"].setText(f"{comp_qday * n_pos:.2f} Nm³")
        self._dv["heb_qday"].setText(f"{heb_qday  * n_pos:.2f} Nm³")
        self._dv["comp_qyr"].setText(f"{comp_qyr  * n_pos:,.0f} Nm³")
        self._dv["heb_qyr"].setText(f"{heb_qyr   * n_pos:,.0f} Nm³")
        self._dv["saving_qyr"].setText(f"{saving_qyr:,.0f} Nm³")
        self._dv["saving_pct"].setText(f"{saving_pct:.1f} %")
        self._dv["break_even"].setText(be_str)

        # Chart
        self._chart_title.setText(
            f"Cumulative air cost over time ({sym}, all positions)"
        )
        self._chart.set_data(comp_cost_yr, heb_cost_yr, nozzle_px, n_pos,
                             currency_sym=sym, years=5)

        # Show results
        self._result_placeholder.setVisible(False)
        self._kpi_container.setVisible(True)
        self._chart_title.setVisible(True)
        self._chart.setVisible(True)
        self._detail_w.setVisible(True)

        # ── Prose summary ─────────────────────────────────────────────
        saving_qh_one = comp_qh - heb_qh          # per nozzle per hour
        saving_qh_all = saving_qh_one * n_pos      # all nozzles per hour
        saving_qday_all = saving_qh_all * 24       # all nozzles per day
        saving_qyr_all  = saving_qh_all * h_yr     # all nozzles per year

        accent = get_accent()
        val_style = f"color: {accent}; font-size: 14px; font-weight: 700; background: transparent; border: none;"
        for lv in self._sum_labels.values():
            lv.setStyleSheet(val_style)

        def _nm3(v): return f"{v:.2f} Nm³"
        self._sum_labels["qh_one"].setText(_nm3(saving_qh_one))
        self._sum_labels["qh_all"].setText(_nm3(saving_qh_all))
        self._sum_labels["qday_all"].setText(_nm3(saving_qday_all))
        self._sum_labels["qyr_all"].setText(f"{saving_qyr_all:,.2f} Nm³")

        # Break-even pressure sentence
        if be_bar != float("inf") and be_bar > 0:
            if self._pf_heb.unit() == "PSI":
                be_display = f"<b style='color:{accent}'>{be_bar * PSI_PER_BAR:.1f} PSI</b>"
            else:
                be_display = f"<b style='color:{accent}'>{be_bar:.2f} bar</b>"
            self._sum_be_lbl.setText(
                f"At equal air consumption to the competitor jet, the pressure can be "
                f"raised to {be_display} when using a Heberlein jet."
            )
            self._sum_be_lbl.setVisible(True)
        else:
            self._sum_be_lbl.setVisible(False)

        self._summary_w.setVisible(True)
        self._btn_export.setVisible(True)

    # ------------------------------------------------------------------
    # Reset / home / show
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # PDF Export
    # ------------------------------------------------------------------

    def _export_pdf(self):
        """Generate PDF report and open save dialog."""
        if not hasattr(self, "_pdf_data") or not self._pdf_data:
            return

        # Auto-install reportlab if not present
        try:
            import reportlab
        except ImportError:
            from PySide6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, "reportlab required",
                "The 'reportlab' library is required for PDF export but is not installed.\n\n"
                "Install it now? (requires internet connection)",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            import subprocess, sys
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "reportlab"],
                    timeout=60
                )
            except Exception as install_err:
                QMessageBox.critical(
                    self, "Install Failed",
                    f"Could not install reportlab:\n{install_err}\n\n"
                    f"Please run manually:\n  pip install reportlab"
                )
                return

        from PySide6.QtWidgets import QFileDialog
        import datetime
        default_name = f"Heberlein_JetROI_{datetime.date.today().strftime('%Y%m%d')}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF Report", default_name, "PDF Files (*.pdf)"
        )
        if not path:
            return
        try:
            _generate_pdf(path, self._pdf_data, self._chart)
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "PDF Export", f"Report saved:\n{path}")
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "PDF Export Failed", str(e))

    def _reset(self):
        reply = QMessageBox.question(self, "Reset", "Reset all inputs?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        self._le_positions.setText("1")
        self._le_hours.setText("8000")
        self._cb_currency.setCurrentIndex(0)   # triggers _on_currency_changed
        self._le_comp_type.clear()
        self._le_comp_diam.setText("1.0")
        self._le_comp_holes.setText("1")
        self._pf_comp.reset(4.0)
        self._le_heb_type_man.clear()
        self._le_heb_diam_man.clear()
        self._le_heb_holes_man.setText("1")
        self._le_heb_holes_prod.setText("1")
        self._cb_jet.setCurrentIndex(0)
        self._pf_heb.reset(4.0)
        self._set_process("DTY")
        self._set_heb_mode("product")
        self._result_placeholder.setVisible(True)
        self._kpi_container.setVisible(False)
        self._chart_title.setVisible(False)
        self._chart.setVisible(False)
        self._detail_w.setVisible(False)
        self._summary_w.setVisible(False)
        self._btn_export.setVisible(False)

    # ------------------------------------------------------------------
    # Mode switching
    # ------------------------------------------------------------------
    def _set_calc_mode(self, mode: str):
        self._calc_mode = mode
        self._mode_stack.setCurrentIndex(0 if mode == "single" else 1)
        self._update_mode_btns()

    def _update_mode_btns(self):
        accent = get_accent()
        active_ss = (f"background:{accent}; color:#fff; font-weight:700;"
                     f"border-radius:4px; border:none;")
        inactive_ss = ("background:#e8e8e8; color:#555; font-weight:400;"
                       "border-radius:4px; border:none;")
        if self._calc_mode == "single":
            self._btn_single_mode.setStyleSheet(active_ss)
            self._btn_multi_mode.setStyleSheet(inactive_ss)
        else:
            self._btn_single_mode.setStyleSheet(inactive_ss)
            self._btn_multi_mode.setStyleSheet(active_ss)

    # ------------------------------------------------------------------
    # Multi-Jet mode UI
    # ------------------------------------------------------------------
    def _build_multi_mode(self) -> QWidget:
        """Multi-Jet Comparison — same visual style as Single Jet."""

        body = QWidget()
        body.setStyleSheet(f"background: {LIGHT_BG};")
        layout = QHBoxLayout(body)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(18)
        layout.setAlignment(Qt.AlignTop)

        # ── LEFT ─────────────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(12)
        left.setAlignment(Qt.AlignTop)

        # ── General card ──────────────────────────────────────────────
        gen_card, gen_body = _card("General")

        # Process toggle (same as single jet)
        proc_row = QHBoxLayout()
        proc_row.setSpacing(0)
        self._mj_btn_aty  = QPushButton("ATY")
        self._mj_btn_dty  = QPushButton("DTY")
        self._mj_btn_spin = QPushButton("Spinning")
        for _pb in (self._mj_btn_aty, self._mj_btn_dty, self._mj_btn_spin):
            _pb.setFixedHeight(30)
            _pb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            proc_row.addWidget(_pb)
        self._mj_btn_aty.clicked.connect( lambda: self._set_process("ATY"))
        self._mj_btn_dty.clicked.connect( lambda: self._set_process("DTY"))
        self._mj_btn_spin.clicked.connect(lambda: self._set_process("Spinning"))
        gen_body.addLayout(proc_row)

        def _frow(label_text, widget, unit_text=None, lbl_w=160):
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(lbl_w)
            lbl.setStyleSheet(f"color: {TEXT}; font-size: 12px;")
            row.addWidget(lbl)
            row.addWidget(widget, 1)
            if unit_text:
                row.addWidget(_unit_lbl(unit_text))
            return row

        self._mj_currency = StyledComboBox()
        for c in ["CHF", "EUR", "USD", "CNY", "GBP"]:
            self._mj_currency.addItem(c)
        self._mj_currency.currentIndexChanged.connect(
            lambda _: self._update_multi_currency(self._mj_currency.currentText()))
        gen_body.addLayout(_frow("Currency", self._mj_currency))

        self._mj_cost_m3 = _le("0.04")
        gen_body.addLayout(_frow("Air cost / Nm³", self._mj_cost_m3))

        left.addWidget(gen_card)

        # ── Jet rows ──────────────────────────────────────────────────
        self._mj_rows: List[Dict] = []
        self._mj_rows_widget = QWidget()
        self._mj_rows_widget.setStyleSheet("background: transparent;")
        self._mj_rows_layout = QVBoxLayout(self._mj_rows_widget)
        self._mj_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._mj_rows_layout.setSpacing(10)
        left.addWidget(self._mj_rows_widget)

        # Add / Remove buttons
        btn_bar = QHBoxLayout()
        btn_add = QPushButton("+ Add Comparison")
        btn_add.setObjectName("GreenBtn")
        btn_add.setFixedHeight(34)
        btn_add.clicked.connect(self._mj_add_row)
        btn_rem = QPushButton("− Remove Last")
        btn_rem.setFixedHeight(34)
        btn_rem.clicked.connect(self._mj_remove_row)
        btn_bar.addWidget(btn_add)
        btn_bar.addWidget(btn_rem)
        left.addLayout(btn_bar)

        btn_calc = QPushButton("Calculate →")
        btn_calc.setObjectName("GreenBtn")
        btn_calc.setFixedHeight(40)
        btn_calc.clicked.connect(self._calculate_multi)
        left.addWidget(btn_calc)

        btn_rst = QPushButton("Reset")
        btn_rst.setFixedHeight(34)
        btn_rst.clicked.connect(self._reset_multi)
        left.addWidget(btn_rst)

        self._mj_btn_export = QPushButton("Export PDF")
        self._mj_btn_export.setObjectName("GreenBtn")
        self._mj_btn_export.setFixedHeight(34)
        self._mj_btn_export.clicked.connect(self._export_multi_pdf)
        self._mj_btn_export.setVisible(False)
        left.addWidget(self._mj_btn_export)

        left_w = QWidget()
        left_w.setFixedWidth(500)
        left_w.setStyleSheet("background: transparent;")
        left_w.setLayout(left)

        # ── RIGHT ─────────────────────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(12)
        right.setAlignment(Qt.AlignTop)

        self._mj_res_card, mj_res_body = _card("Comparison Result")
        self._mj_res_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._mj_placeholder = QLabel(
            "Fill in the comparisons on the left,\nthen press  Calculate →"
        )
        self._mj_placeholder.setAlignment(Qt.AlignCenter)
        self._mj_placeholder.setStyleSheet(
            "color: #bbb; font-size: 13px; padding: 50px 20px;")
        mj_res_body.addWidget(self._mj_placeholder)

        # KPI row
        self._mj_kpi_container = QWidget()
        self._mj_kpi_container.setVisible(False)
        mj_kpi_row = QHBoxLayout(self._mj_kpi_container)
        mj_kpi_row.setContentsMargins(0, 0, 0, 0)
        mj_kpi_row.setSpacing(10)
        self._mj_kf_saving, self._mj_kv_saving, self._mj_ku_saving = \
            _kpi_widget("Total Saving / yr", "CHF")
        self._mj_kf_invest, self._mj_kv_invest, self._mj_ku_invest = \
            _kpi_widget("Total Investment", "CHF")
        self._mj_kf_amort,  self._mj_kv_amort,  self._mj_ku_amort  = \
            _kpi_widget("Break-even", "years")
        self._mj_kf_airpct, self._mj_kv_airpct, self._mj_ku_airpct = \
            _kpi_widget("Avg Air Saving", "%")
        for f in (self._mj_kf_saving, self._mj_kf_invest,
                  self._mj_kf_amort, self._mj_kf_airpct):
            mj_kpi_row.addWidget(f)
        mj_res_body.addWidget(self._mj_kpi_container)

        # Chart title + chart
        self._mj_chart_title = QLabel()
        self._mj_chart_title.setStyleSheet(
            f"color: {DARK}; font-size: 11px; font-weight: 600; padding-top: 6px;")
        self._mj_chart_title.setVisible(False)
        mj_res_body.addWidget(self._mj_chart_title)

        self._mj_chart = MultiJetChart(self)
        self._mj_chart.setVisible(False)
        mj_res_body.addWidget(self._mj_chart)

        # Detail grid
        self._mj_detail_w = QWidget()
        self._mj_detail_w.setVisible(False)
        mj_dl = QGridLayout(self._mj_detail_w)
        mj_dl.setHorizontalSpacing(14)
        mj_dl.setVerticalSpacing(4)
        mj_dl.setColumnStretch(1, 1)
        mj_dl.setColumnStretch(3, 1)
        self._mj_dv: Dict[str, QLabel] = {}
        mj_keys = [
            ("a_qh",       "Jet A flow / jet"),
            ("b_qh",       "Jet B flow / jet"),
            ("a_air_yr",   "Jet A air cost / yr (total)"),
            ("b_air_yr",   "Jet B air cost / yr (total)"),
            ("saving_yr",  "Air cost saving / yr"),
            ("saving_pct", "Air saving"),
            ("invest",     "Total investment"),
            ("be_yr",      "Break-even"),
        ]
        mj_split = (len(mj_keys) + 1) // 2
        for idx, (key, label) in enumerate(mj_keys):
            col = (idx // mj_split) * 2
            row = idx % mj_split
            lk = QLabel(label + ":")
            lk.setStyleSheet("color: #666; font-size: 11px;")
            lv = QLabel("—")
            lv.setStyleSheet(f"color: {TEXT}; font-size: 11px; font-weight: 600;")
            mj_dl.addWidget(lk, row, col)
            mj_dl.addWidget(lv, row, col + 1)
            self._mj_dv[key] = lv
        mj_res_body.addWidget(self._mj_detail_w)

        # Per-comparison table
        self._mj_table_w = QWidget()
        self._mj_table_w.setVisible(False)
        self._mj_table_w.setStyleSheet(
            f"background: #f8faf8; border-top: 2px solid #e0ede0;")
        mj_tbl_outer = QVBoxLayout(self._mj_table_w)
        mj_tbl_outer.setContentsMargins(0, 12, 0, 4)
        mj_tbl_title = QLabel("Per-Comparison Breakdown")
        mj_tbl_title.setStyleSheet(
            f"color: {DARK}; font-size: 13px; font-weight: 700;"
            f"background: transparent; border: none;")
        mj_tbl_outer.addWidget(mj_tbl_title)
        self._mj_table = QTableWidget(0, 7)
        self._mj_table.setHorizontalHeaderLabels([
            "Label", "Jet A", "Jet B", "Hours / yr",
            "Air Saving / yr", "Investment", "Break-even",
        ])
        self._mj_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._mj_table.verticalHeader().setVisible(False)
        self._mj_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._mj_table.setAlternatingRowColors(True)
        self._mj_table.setStyleSheet(
            "QTableWidget { font-size: 11px; border: none; background: transparent; }"
            f"QHeaderView::section {{ background: {DARK}; color: #fff;"
            f" font-weight: 700; font-size: 11px; padding: 4px; border: none; }}"
            "QTableWidget::item { padding: 3px 5px; }"
        )
        mj_tbl_outer.addWidget(self._mj_table)
        mj_res_body.addWidget(self._mj_table_w)

        right.addWidget(self._mj_res_card)
        right_w = QWidget()
        right_w.setStyleSheet("background: transparent;")
        right_w.setLayout(right)

        layout.addWidget(left_w, 0, Qt.AlignTop)
        layout.addWidget(right_w, 1)

        # Default 3 rows
        for _ in range(3):
            self._mj_add_row()

        return body


    def _mj_add_row(self):
        """Add one Jet A vs Jet B comparison row — single-jet card style."""
        idx = len(self._mj_rows)

        card, body = _card(f"Comparison #{idx + 1}")

        # Label
        name_edit = _le(placeholder=f"Label (e.g. Yarn {chr(65+idx)})")
        name_edit.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {DARK};"
            "background: #f4f8ff; border: 1px solid #c0d0e8; border-radius: 2px; padding: 3px 8px;")

        body_lbl = QHBoxLayout()
        lbl_l = QLabel("Label")
        lbl_l.setFixedWidth(100)
        lbl_l.setStyleSheet(f"color: {TEXT}; font-size: 12px;")
        body_lbl.addWidget(lbl_l)
        body_lbl.addWidget(name_edit, 1)
        body.addLayout(body_lbl)

        def _frow(label_text, widget, unit_text=None):
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(100)
            lbl.setStyleSheet(f"color: {TEXT}; font-size: 12px;")
            row.addWidget(lbl)
            row.addWidget(widget, 1)
            if unit_text:
                row.addWidget(_unit_lbl(unit_text))
            return row

        pos_edit = _le("100")
        h_edit   = _le(placeholder="Hours / yr")
        body.addLayout(_frow("Positions", pos_edit))
        body.addLayout(_frow("Hours / yr", h_edit))

        # Jet A / B columns — use _card style sub-frames
        ab_row = QHBoxLayout()
        ab_row.setSpacing(8)

        def _jet_col(title, is_b=False):
            frame = QFrame()
            frame.setObjectName("Card")
            frame.setStyleSheet(
                f"QFrame#Card {{ background: {CARD_BG}; border: 1px solid #cfcfcf; border-radius: 2px; }}"
            )
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(0, 0, 0, 8)
            fl.setSpacing(6)

            hdr = QFrame()
            hdr.setFixedHeight(28)
            hdr.setStyleSheet(
                f"background: {'#39A650' if is_b else '#565656'};"
            )
            hdr_l = QHBoxLayout(hdr)
            hdr_l.setContentsMargins(10, 0, 10, 0)
            hdr_lbl = QLabel(title)
            hdr_lbl.setStyleSheet("color: white; font-size: 11px; font-weight: 700;")
            hdr_l.addWidget(hdr_lbl)
            fl.addWidget(hdr)

            inner = QVBoxLayout()
            inner.setContentsMargins(10, 4, 10, 0)
            inner.setSpacing(5)

            cb = StyledComboBox()
            inner.addWidget(cb)

            pf = PressureField()
            inner.addWidget(pf)

            price_edit = _le(placeholder="Price / jet  (0 = owned)")
            inner.addWidget(price_edit)

            fl.addLayout(inner)
            return frame, cb, pf, price_edit

        a_frame, a_cb, a_pf, a_price = _jet_col("Jet A  (current)", is_b=False)
        b_frame, b_cb, b_pf, b_price = _jet_col("Jet B  (optimal)", is_b=True)
        ab_row.addWidget(a_frame)
        ab_row.addWidget(b_frame)
        body.addLayout(ab_row)

        self._mj_rows_layout.addWidget(card)

        row_data = {
            "card": card, "name": name_edit,
            "pos": pos_edit, "hours": h_edit,
            "a_cb": a_cb, "a_pf": a_pf, "a_price": a_price,
            "b_cb": b_cb, "b_pf": b_pf, "b_price": b_price,
        }
        self._mj_rows.append(row_data)

        if hasattr(self, "_all_jets"):
            for cb in (a_cb, b_cb):
                self._mj_populate_cb(cb)



    def _mj_remove_row(self):
        if len(self._mj_rows) <= 1:
            return
        row = self._mj_rows.pop()
        row["card"].setParent(None)
        row["card"].deleteLater()

    def _mj_populate_cb(self, cb: "StyledComboBox"):
        """Populate dropdown using same process filter as single mode."""
        prev_data = cb.currentData()
        prev_id   = prev_data.get("ID") if isinstance(prev_data, dict) else None
        cb.blockSignals(True)
        cb.clear()
        cb.addItem("— select jet —", None)
        restore = 0
        for jet in self._all_jets:
            if not self._jet_matches_process(jet):
                continue
            label = str(jet.get("Jet") or f"ID {jet.get('ID')}")
            d = dict(jet)
            try:
                d["_diam"] = float(str(jet.get("Luftbohrung") or "").replace(",","."))
            except Exception:
                d["_diam"] = None
            cb.addItem(label, d)
            if prev_id is not None and jet.get("ID") == prev_id:
                restore = cb.count() - 1
        cb.setCurrentIndex(restore)
        cb.blockSignals(False)

    def _mj_refresh_all_cbs(self):
        """Refresh all multi-mode dropdowns after process change."""
        for row in self._mj_rows:
            for cb in (row.get("a_cb"), row.get("b_cb")):
                if cb is not None:
                    self._mj_populate_cb(cb)

    def _update_multi_currency(self, sym: str):
        SYMS = {"CHF":"CHF","EUR":"€","USD":"$","CNY":"¥","GBP":"£"}
        s = SYMS.get(sym, sym)
        self._mj_u_saving.setText(s)
        self._mj_u_invest.setText(s)
        self._mj_u_amort.setText("years")
        self._mj_u_airpct.setText("%")

    def _calculate_multi(self):
        try:
            cost_m3 = float(self._mj_cost_m3.text().replace(",",".") or "0.04")
            sym     = self._mj_currency.currentText()
            SYMS    = {"CHF":"CHF","EUR":"€","USD":"$","CNY":"¥","GBP":"£"}
            sym_s   = SYMS.get(sym, sym)

            results = []
            for row in self._mj_rows:
                label   = row["name"].text().strip() or f"#{len(results)+1}"
                try:
                    n_pos = max(1, int(row["pos"].text() or "1"))
                    h_yr  = float(row["hours"].text().replace(",",".") or "0")
                except Exception:
                    continue

                # Jet A
                a_jet   = row["a_cb"].currentData()
                b_jet   = row["b_cb"].currentData()
                if not a_jet or not b_jet:
                    continue

                def _diam(jet):
                    return float(str(jet.get("Luftbohrung") or
                                     jet.get("_diam") or "0").replace(",","."))
                def _holes(jet):
                    return int(jet.get("LuftlochAnzahl") or 1)
                def _name(jet):
                    return str(jet.get("Jet") or "?")

                try:
                    a_diam  = _diam(a_jet);  a_holes = _holes(a_jet)
                    b_diam  = _diam(b_jet);  b_holes = _holes(b_jet)
                    a_price = float(row["a_price"].text().replace(",",".") or "0")
                    b_price = float(row["b_price"].text().replace(",",".") or "0")
                except Exception:
                    continue

                a_p   = row["a_pf"].bar_value()
                b_p   = row["b_pf"].bar_value()
                a_qh  = _air_flow_nm3h(a_diam, a_holes, a_p, a_jet.get("Luftverbrauch"))
                b_qh  = _air_flow_nm3h(b_diam, b_holes, b_p, b_jet.get("Luftverbrauch"))

                if a_diam <= 0:
                    continue

                # Annual air cost per comparison
                a_air_yr = a_qh * h_yr * cost_m3 * n_pos
                b_air_yr = b_qh * h_yr * cost_m3 * n_pos
                saving_yr = a_air_yr - b_air_yr

                # Net investment: (B price - A price) × positions
                # If A price = 0 (already owned), investment = B × positions
                # If both have prices, invest = (B - A) × positions (switching cost)
                net_invest = (b_price - a_price) * n_pos

                air_pct = (a_qh - b_qh) / a_qh * 100 if a_qh > 0 else 0.0

                results.append({
                    "label": label,
                    "a_name": _name(a_jet), "b_name": _name(b_jet),
                    "n_pos": n_pos, "h_yr": h_yr,
                    "saving_yr": saving_yr, "net_invest": net_invest,
                    "air_pct": air_pct, "sym": sym_s,
                    "a_air_yr": a_air_yr, "b_air_yr": b_air_yr,
                    "a_qh": a_qh, "b_qh": b_qh,
                })

            if not results:
                QMessageBox.warning(self, "No Data",
                    "Please select Jet A and Jet B for at least one row.")
                return

            total_saving = sum(r["saving_yr"] for r in results)
            total_invest = sum(r["net_invest"] for r in results)
            total_amort  = (total_invest / total_saving
                            if total_saving > 0 and total_invest > 0
                            else float("inf"))

            total_a = sum(r["a_air_yr"] for r in results)
            total_b = sum(r["b_air_yr"] for r in results)
            avg_pct = (total_a - total_b) / total_a * 100 if total_a > 0 else 0.0

            # ── KPI cards (single-jet style) ─────────────────────────
            self._mj_kv_saving.setText(f"{total_saving:,.0f}")
            self._mj_ku_saving.setText(sym_s)
            self._mj_kv_invest.setText(f"{total_invest:,.0f}")
            self._mj_ku_invest.setText(sym_s)
            self._mj_kv_amort.setText(
                "N/A" if total_amort == float("inf") else f"{total_amort:.2f}")
            self._mj_ku_amort.setText("years")
            self._mj_kv_airpct.setText(f"{avg_pct:.1f}")
            self._mj_ku_airpct.setText("%")
            self._mj_kpi_container.setVisible(True)
            self._mj_placeholder.setVisible(False)

            # ── Detail grid (single-jet style) ───────────────────────
            # Aggregate flows (weighted by hours)
            total_h = sum(r["h_yr"] for r in results)
            wa_qh = (sum(r["a_qh"] * r["h_yr"] for r in results) / total_h
                     if total_h > 0 else 0)
            wb_qh = (sum(r["b_qh"] * r["h_yr"] for r in results) / total_h
                     if total_h > 0 else 0)
            total_a_air = sum(r["a_air_yr"] for r in results)
            total_b_air = sum(r["b_air_yr"] for r in results)

            be_s = ("N/A" if total_amort == float("inf")
                    else f"{total_amort:.2f} years")
            self._mj_dv["a_qh"].setText(f"{wa_qh:.4f} Nm³/h  (weighted avg)")
            self._mj_dv["b_qh"].setText(f"{wb_qh:.4f} Nm³/h  (weighted avg)")
            self._mj_dv["a_air_yr"].setText(f"{total_a_air:,.0f} {sym_s}")
            self._mj_dv["b_air_yr"].setText(f"{total_b_air:,.0f} {sym_s}")
            self._mj_dv["saving_yr"].setText(f"{total_saving:,.0f} {sym_s}")
            self._mj_dv["saving_pct"].setText(f"{avg_pct:.1f} %")
            self._mj_dv["invest"].setText(f"{total_invest:,.0f} {sym_s}")
            self._mj_dv["be_yr"].setText(be_s)
            self._mj_detail_w.setVisible(True)

            # ── Per-comparison table ──────────────────────────────────
            self._mj_table.setRowCount(len(results) + 1)  # +1 for totals row
            for ri, res in enumerate(results):
                if res["net_invest"] <= 0:
                    amort_s = "—"
                elif res["saving_yr"] <= 0:
                    amort_s = "∞"
                else:
                    amort_s = f"{res['net_invest']/res['saving_yr']:.2f} yr"
                invest_s = (f"{res['net_invest']:,.0f} {sym_s}"
                            if res["net_invest"] > 0 else "0")
                vals = [
                    res["label"], res["a_name"], res["b_name"],
                    f"{res['h_yr']:,.0f} h",
                    f"{res['saving_yr']:,.0f} {sym_s}",
                    invest_s, amort_s,
                ]
                for ci, v in enumerate(vals):
                    item = QTableWidgetItem(v)
                    item.setTextAlignment(Qt.AlignCenter)
                    self._mj_table.setItem(ri, ci, item)

            # Totals row — highlighted but clean
            total_row = len(results)
            total_be_s = ("N/A" if total_amort == float("inf")
                          else f"{total_amort:.2f} yr")
            total_vals = [
                "Total", "—", "—",
                f"{sum(r['h_yr'] for r in results):,.0f} h",
                f"{total_saving:,.0f} {sym_s}",
                f"{total_invest:,.0f} {sym_s}",
                total_be_s,
            ]
            accent = get_accent()
            for ci, v in enumerate(total_vals):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignCenter)
                item.setBackground(QColor(accent).lighter(175))
                font = item.font(); font.setBold(True); item.setFont(font)
                self._mj_table.setItem(total_row, ci, item)
            self._mj_table_w.setVisible(True)

            # ── Chart ─────────────────────────────────────────────────
            self._mj_chart_title.setText(
                f"Cumulative Cost: Jet A vs Jet B  "
                f"({len(results)} comparisons, {sym_s})")
            self._mj_chart_title.setVisible(True)
            self._mj_chart.set_data(results, total_saving, total_invest, sym_s)
            self._mj_chart.setVisible(True)

            # Store for PDF export
            self._mj_pdf_results = results
            self._mj_pdf_totals  = {
                "sym": sym_s, "saving": total_saving,
                "invest": total_invest, "air_pct": avg_pct,
                "cost_m3": cost_m3,
            }
            self._mj_btn_export.setVisible(True)

        except Exception as e:
            QMessageBox.warning(self, "Calculation Error", str(e))

    def _export_multi_pdf(self):
        from PySide6.QtWidgets import QFileDialog
        import re, pathlib, datetime
        if not hasattr(self, "_mj_pdf_results") or not self._mj_pdf_results:
            return
        docs = str(pathlib.Path.home() / "Documents")
        dflt = f"Heberlein_MultiJet_{datetime.date.today().strftime('%Y%m%d')}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF", str(pathlib.Path(docs) / dflt), "PDF Files (*.pdf)")
        if not path:
            return
        try:
            _generate_multi_pdf(path, self._mj_pdf_results, self._mj_pdf_totals)
            self._mj_btn_export.setText("✓ PDF saved!")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(3000, lambda: self._mj_btn_export.setText("Export PDF"))
        except Exception as e:
            QMessageBox.warning(self, "PDF Error", str(e))

    def _reset_multi(self):
        self._mj_table.setRowCount(0)
        self._mj_placeholder.setVisible(True)
        self._mj_btn_export.setVisible(False)
        self._mj_kpi_container.setVisible(False)
        self._mj_detail_w.setVisible(False)
        self._mj_table_w.setVisible(False)
        self._mj_chart.setVisible(False)
        self._mj_chart_title.setVisible(False)
        self._mj_chart.set_data([], 0, 0, "")
        for row in self._mj_rows:
            row["name"].clear()
            row["hours"].clear()
            row["a_price"].clear()
            row["b_price"].clear()



    def _go_home(self):
        if callable(self._on_back_home):
            self._on_back_home()

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
        super().showEvent(event)
        self._load_jets()
        # Refresh accent colour in case it changed after login
        self._cb_jet.refresh_accent()
        self._cb_currency.refresh_accent()
        try:
            self._refresh_sidebar()
        except Exception:
            pass