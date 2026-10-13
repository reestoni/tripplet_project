from __future__ import annotations
# ui/widgets/yarn_stock_help_dialog.py
"""Kontext-Hilfe fuer Yarn Stock (Nutzerwunsch 2026-10-13: die als Artifact
gebaute Lager-Erklaerung direkt im Tool verfuegbar machen, statt dass sie
"auf Papier" liegt und im Bedarfsfall niemand sie findet). Gleiches Muster
wie ui/widgets/experiment_request_help_dialog.py: kleiner Info-Button im
Screen, Dialog wird lazy gebaut, reines Info-Fenster.

Drei Tabs:
- "How do I…?": aufgabenorientierte Klickwege ("ich suche X / will Y tun")
- "Screen guide": Skizze des Screens (assets/images/yarn_stock_screen_map.svg)
  plus Erklaerung der Bereiche A/1-4
- "Background": Konzept (Garn/Batch/Spule, Lebenslauf, Ampel, Grenzen)
- "Stock take": ausfuehrliche Inventur-Anleitung (auch direkt aus dem
  Inventur-Fenster per "?" erreichbar, show_yarn_stock_help(tab="stocktake"))

Sprache EN/DE/ES per Flaggen-Button oben rechts umschaltbar, Wahl wird per
QSettings gemerkt. Alle Texte in ui/widgets/yarn_stock_help_texts.py; die
beiden SVGs enthalten {{key}}-Platzhalter, die beim Laden ersetzt werden.

Alle Aussagen spiegeln die Logik in ui/screen_yarn_stock.py und
ui/widgets/spool_picker.py - bei Aenderungen dort (Buttons, Ablaeufe,
Layout) Texte und SVGs mitziehen.
"""

from typing import Optional, List, Tuple, Dict
from xml.sax.saxutils import escape

from PySide6.QtCore import Qt, QByteArray, QSettings, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QPushButton,
    QScrollArea, QFrame, QTabWidget, QToolButton, QButtonGroup,
)
from PySide6.QtSvgWidgets import QSvgWidget

from ui.pathutil import resource_path
from ui.widgets.yarn_stock_help_texts import TEXTS, LANGUAGES, DEFAULT_LANGUAGE

# Native SVG-Groessen (viewBox in den jeweiligen Dateien).
_FLOW_W, _FLOW_H = 940, 250   # assets/images/yarn_stock_spool_flow.svg
_MAP_W, _MAP_H = 940, 470     # assets/images/yarn_stock_screen_map.svg
_FLAG_W, _FLAG_H = 30, 18

_SETTINGS_ORG, _SETTINGS_APP, _SETTINGS_KEY = "TrippleT", "YarnStockHelp", "language"

_H_STYLE = "font-size: 15px; font-weight: 700; color: #2b2b2b; margin-top: 8px;"
_P_STYLE = "font-size: 13px; color: #2b2b2b;"
_NOTE_GREEN = "background: #e8f5e9; border: 1px solid #39a650; border-radius: 8px; padding: 10px 12px;"
_FLAG_QSS = (
    "QToolButton{border:2px solid transparent;border-radius:4px;padding:2px;background:transparent;}"
    "QToolButton:hover{border-color:#b5d7b5;}"
    "QToolButton:checked{border-color:#39a650;background:#e8f5e9;}"
)


def _heading(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(_H_STYLE)
    return lbl


def _para(html: str, extra_style: str = "") -> QLabel:
    lbl = QLabel(html)
    lbl.setWordWrap(True)
    lbl.setTextFormat(Qt.RichText)
    lbl.setStyleSheet(_P_STYLE + extra_style)
    return lbl


def _muted(html: str) -> QLabel:
    return _para(f"<span style='color:#565656'>{html}</span>")


def _scroll_page() -> Tuple[QScrollArea, QVBoxLayout]:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(24, 16, 24, 12)
    layout.setSpacing(10)
    scroll.setWidget(body)
    return scroll, layout


def _task(question: str, steps: List[str], note: str = "") -> QLabel:
    """Eine Aufgabe: Frage + nummerierte Klickschritte (+ optionaler Hinweis)."""
    items = "".join(f"<li>{s}</li>" for s in steps)
    html = f"<b>{question}</b><ol style='margin-top:2px; margin-bottom:2px'>{items}</ol>"
    if note:
        html += f"<span style='color:#565656'>{note}</span>"
    return _para(html, "padding: 6px 0px 8px 0px; border-bottom: 1px solid #e0e0e0;")


def _svg_widget(rel_path: str, values: Dict[str, str], w: int, h: int) -> QSvgWidget:
    """Laedt ein SVG mit {{key}}-Platzhaltern und ersetzt sie durch `values`."""
    with open(resource_path(rel_path), encoding="utf-8") as fh:
        src = fh.read()
    for k, v in values.items():
        src = src.replace("{{" + k + "}}", escape(v))
    svg = QSvgWidget()
    svg.load(QByteArray(src.encode("utf-8")))
    svg.setFixedSize(w, h)
    return svg


def _flag_icon(file_name: str) -> QIcon:
    """Rendert eine Flaggen-SVG in ein einheitliches 30x18-Pixmap (mit
    feinem Rand, damit helle Flaggenteile auf hellem Grund sichtbar bleiben).
    Bewusst ueber QSvgRenderer statt QIcon(svg-Pfad): haengt so nicht am
    SVG-Iconengine-Plugin, das im kompilierten Build fehlen koennte."""
    pm = QPixmap(_FLAG_W, _FLAG_H)
    pm.fill(Qt.transparent)
    renderer = QSvgRenderer(resource_path(f"assets/images/{file_name}"))
    p = QPainter(pm)
    renderer.render(p)
    p.setPen(QColor("#999999"))
    p.drawRect(0, 0, _FLAG_W - 1, _FLAG_H - 1)
    p.end()
    return QIcon(pm)


def _load_language() -> str:
    try:
        lang = QSettings(_SETTINGS_ORG, _SETTINGS_APP).value(_SETTINGS_KEY, DEFAULT_LANGUAGE)
        return lang if lang in TEXTS else DEFAULT_LANGUAGE
    except Exception:
        return DEFAULT_LANGUAGE


def _save_language(lang: str) -> None:
    try:
        QSettings(_SETTINGS_ORG, _SETTINGS_APP).setValue(_SETTINGS_KEY, lang)
    except Exception:
        pass


class YarnStockHelpDialog(QDialog):
    """Bedienungsanleitung + Hintergrund zu Yarn Stock, dreisprachig."""

    # Tab-Schluessel fuer den Direkteinstieg (show_yarn_stock_help(tab=...))
    TAB_KEYS = ["tasks", "screen", "background", "stocktake"]

    def __init__(self, parent: Optional[QWidget] = None, language: Optional[str] = None,
                 tab: Optional[str] = None):
        super().__init__(parent)
        self.setMinimumSize(_MAP_W + 90, 600)
        self.resize(_MAP_W + 110, 820)
        self._lang = language if language in TEXTS else _load_language()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 12)
        outer.setSpacing(6)

        # Sprachwahl oben rechts
        flag_row = QHBoxLayout()
        flag_row.addStretch(1)
        self._flag_group = QButtonGroup(self)
        self._flag_group.setExclusive(True)
        self._flag_buttons: Dict[str, QToolButton] = {}
        for code, name, file_name in LANGUAGES:
            btn = QToolButton()
            btn.setIcon(_flag_icon(file_name))
            btn.setIconSize(QSize(_FLAG_W, _FLAG_H))
            btn.setCheckable(True)
            btn.setToolTip(name)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_FLAG_QSS)
            btn.clicked.connect(lambda _=False, c=code: self.set_language(c))
            self._flag_group.addButton(btn)
            self._flag_buttons[code] = btn
            flag_row.addWidget(btn)
        outer.addLayout(flag_row)

        self.tabs = QTabWidget()
        outer.addWidget(self.tabs, 1)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 12, 0)
        btn_row.addStretch(1)
        self.btn_close = QPushButton()
        self.btn_close.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_close)
        outer.addLayout(btn_row)

        self._apply_language()
        if tab in self.TAB_KEYS:
            self.tabs.setCurrentIndex(self.TAB_KEYS.index(tab))

    # ── Sprache ──────────────────────────────────────────────────────
    def language(self) -> str:
        return self._lang

    def set_language(self, lang: str) -> None:
        if lang not in TEXTS:
            return
        if lang != self._lang:
            self._lang = lang
            _save_language(lang)
            self._apply_language()
        self._flag_buttons[lang].setChecked(True)

    def _apply_language(self) -> None:
        t = TEXTS[self._lang]
        current_tab = max(0, self.tabs.currentIndex())
        while self.tabs.count():
            page = self.tabs.widget(0)
            self.tabs.removeTab(0)
            page.deleteLater()
        self.tabs.addTab(self._build_tasks_tab(t), t["tab_tasks"])
        self.tabs.addTab(self._build_screen_tab(t), t["tab_screen"])
        self.tabs.addTab(self._build_background_tab(t), t["tab_background"])
        self.tabs.addTab(self._build_stocktake_tab(t), t["tab_stocktake"])
        self.tabs.setCurrentIndex(current_tab)
        self.setWindowTitle(t["window_title"])
        self.btn_close.setText(t["close"])
        self._flag_buttons[self._lang].setChecked(True)

    # ── Tab 1: aufgabenorientierte Anleitung ─────────────────────────
    def _build_tasks_tab(self, t: dict) -> QWidget:
        scroll, layout = _scroll_page()
        layout.addWidget(_para(t["tasks_intro"]))
        layout.addWidget(_heading(t["h_find"]))
        for q, steps, note in t["tasks_find"]:
            layout.addWidget(_task(q, steps, note))
        layout.addWidget(_heading(t["h_change"]))
        layout.addWidget(_muted(t["change_note"]))
        for q, steps, note in t["tasks_change"]:
            layout.addWidget(_task(q, steps, note))
        layout.addStretch(1)
        return scroll

    # ── Tab 2: Bildschirmaufbau ──────────────────────────────────────
    def _build_screen_tab(self, t: dict) -> QWidget:
        scroll, layout = _scroll_page()
        layout.addWidget(
            _svg_widget("assets/images/yarn_stock_screen_map.svg", t["svg_map"], _MAP_W, _MAP_H),
            0, Qt.AlignHCenter)
        layout.addWidget(_muted(t["screen_caption"]))
        rows = "".join(
            f"<tr><td valign='top'><b>{label.replace(' ', '&nbsp;')}</b></td><td>{text}</td></tr>"
            for label, text in t["screen_areas"])
        layout.addWidget(_para(f"<table cellspacing='0' cellpadding='6'>{rows}</table>"))
        layout.addWidget(_heading(t["h_elsewhere"]))
        layout.addWidget(_para(t["elsewhere"]))
        layout.addStretch(1)
        return scroll

    # ── Tab 3: Hintergrund / Konzept ─────────────────────────────────
    def _build_background_tab(self, t: dict) -> QWidget:
        scroll, layout = _scroll_page()
        layout.addWidget(_heading(t["h_levels"]))
        layout.addWidget(_para(t["levels"]))
        layout.addWidget(_heading(t["h_life"]))
        layout.addWidget(
            _svg_widget("assets/images/yarn_stock_spool_flow.svg", t["svg_flow"], _FLOW_W, _FLOW_H),
            0, Qt.AlignHCenter)
        layout.addWidget(_para(t["life_note"], _NOTE_GREEN))
        layout.addWidget(_heading(t["h_status"]))
        layout.addWidget(_para(t["status"]))
        layout.addWidget(_heading(t["h_good"]))
        layout.addWidget(_para(t["good"]))
        layout.addStretch(1)
        return scroll


    # ── Tab 4: Inventur ──────────────────────────────────────────────
    def _build_stocktake_tab(self, t: dict) -> QWidget:
        scroll, layout = _scroll_page()
        layout.addWidget(_para(t["st_intro"]))
        for heading, html in t["stocktake"]:
            layout.addWidget(_heading(heading))
            layout.addWidget(_para(html))
        layout.addWidget(_para(t["st_note"], _NOTE_GREEN))
        layout.addStretch(1)
        return scroll


def show_yarn_stock_help(parent: Optional[QWidget] = None, tab: Optional[str] = None) -> None:
    """Oeffnet die Yarn-Stock-Hilfe (siehe YarnStockHelpDialog), optional
    direkt auf einem Tab ("tasks", "screen", "background", "stocktake")."""
    dlg = YarnStockHelpDialog(parent, tab=tab)
    dlg.exec()
