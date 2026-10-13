from __future__ import annotations
# ui/widgets/multilang_help.py
"""Gemeinsames Geruest fuer die mehrsprachigen Kontext-Hilfen (EN/DE/ES)
- Nutzerwunsch 2026-10-13: nach Yarn Stock auch Show Experiment, Backlog und
Report/Smart Chart, "immer auf drei Sprachen mit der Flagge als Sprachwaehler".

Stellt bereit:
- Sprachwahl per Flaggen (eigene SVGs, ueber QSvgRenderer gerendert - haengt
  nicht am SVG-Iconengine-Plugin des Builds), Sprache gilt fuer ALLE Hilfen
  gemeinsam (QSettings "TrippleT/Help/language"; Altwert der Yarn-Stock-Hilfe
  wird als Fallback gelesen).
- MultilangHelpDialog: rendert eine reine Daten-Beschreibung pro Sprache
  (Tabs aus Bausteinen, siehe BLOCKS unten) - neue Screens brauchen nur ein
  Textmodul, keinen eigenen Dialog-Code.
- make_help_button(): der runde gruene Hilfe-Button (gleiches Styling wie in
  Yarn Stock / Experiment Requests).

Baustein-Typen (Tupel, erstes Element = Typ):
  ("p", html)                       Absatz
  ("h", text)                       Zwischenueberschrift
  ("task", frage, [schritte], hinweis)  Aufgabe mit nummerierten Klickschritten
  ("note", html) / ("warn", html)   gruener Hinweis / gelber Warnhinweis
  ("ul", [items])                   Aufzaehlung
  ("areas", [(label, html), ...])   zweispaltige Bereichstabelle (Screen guide)
  ("table", [kopf], [[zellen]])     Tabelle mit Kopfzeile
  ("svg", pfad, {key: text}, w, h)  Skizze, {{key}}-Platzhalter werden ersetzt
"""

from typing import Any, Callable, Dict, List, Optional, Tuple
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

LANGUAGES = [("en", "English", "flag_gb.svg"),
             ("de", "Deutsch", "flag_de.svg"),
             ("es", "Español", "flag_es.svg")]
DEFAULT_LANGUAGE = "en"
_CODES = {c for c, _, _ in LANGUAGES}

_FLAG_W, _FLAG_H = 30, 18
_SETTINGS = ("TrippleT", "Help", "language")
_LEGACY_SETTINGS = ("TrippleT", "YarnStockHelp", "language")  # erste Hilfe (Yarn Stock)

H_STYLE = "font-size: 15px; font-weight: 700; color: #2b2b2b; margin-top: 8px;"
P_STYLE = "font-size: 13px; color: #2b2b2b;"
NOTE_GREEN = "background: #e8f5e9; border: 1px solid #39a650; border-radius: 8px; padding: 10px 12px;"
NOTE_YELLOW = "background: #fff3cd; border: 1px solid #E6C802; border-radius: 8px; padding: 10px 12px;"
FLAG_QSS = (
    "QToolButton{border:2px solid transparent;border-radius:4px;padding:2px;background:transparent;}"
    "QToolButton:hover{border-color:#b5d7b5;}"
    "QToolButton:checked{border-color:#39a650;background:#e8f5e9;}"
)


# ── Sprache ─────────────────────────────────────────────────────────────
def load_language() -> str:
    try:
        org, app, key = _SETTINGS
        lang = QSettings(org, app).value(key, None)
        if lang not in _CODES:
            org, app, key = _LEGACY_SETTINGS
            lang = QSettings(org, app).value(key, DEFAULT_LANGUAGE)
        return lang if lang in _CODES else DEFAULT_LANGUAGE
    except Exception:
        return DEFAULT_LANGUAGE


def save_language(lang: str) -> None:
    try:
        org, app, key = _SETTINGS
        QSettings(org, app).setValue(key, lang)
    except Exception:
        pass


def flag_icon(file_name: str) -> QIcon:
    """Flaggen-SVG als einheitliches 30x18-Pixmap mit feinem Rand."""
    pm = QPixmap(_FLAG_W, _FLAG_H)
    pm.fill(Qt.transparent)
    renderer = QSvgRenderer(resource_path(f"assets/images/{file_name}"))
    p = QPainter(pm)
    renderer.render(p)
    p.setPen(QColor("#999999"))
    p.drawRect(0, 0, _FLAG_W - 1, _FLAG_H - 1)
    p.end()
    return QIcon(pm)


def build_flag_row(on_select: Callable[[str], None], parent: QWidget) -> Tuple[QHBoxLayout, Dict[str, QToolButton]]:
    """Flaggen-Leiste (rechtsbuendig). on_select(code) wird beim Klick gerufen."""
    row = QHBoxLayout()
    row.addStretch(1)
    group = QButtonGroup(parent)
    group.setExclusive(True)
    buttons: Dict[str, QToolButton] = {}
    for code, name, file_name in LANGUAGES:
        btn = QToolButton()
        btn.setIcon(flag_icon(file_name))
        btn.setIconSize(QSize(_FLAG_W, _FLAG_H))
        btn.setCheckable(True)
        btn.setToolTip(name)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(FLAG_QSS)
        btn.clicked.connect(lambda _=False, c=code: on_select(c))
        group.addButton(btn)
        buttons[code] = btn
        row.addWidget(btn)
    return row, buttons


# ── Bausteine ───────────────────────────────────────────────────────────
def heading(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(H_STYLE)
    return lbl


def para(html: str, extra_style: str = "") -> QLabel:
    lbl = QLabel(html)
    lbl.setWordWrap(True)
    lbl.setTextFormat(Qt.RichText)
    lbl.setStyleSheet(P_STYLE + extra_style)
    return lbl


def task(question: str, steps: List[str], note: str = "") -> QLabel:
    items = "".join(f"<li>{s}</li>" for s in steps)
    html = f"<b>{question}</b><ol style='margin-top:2px; margin-bottom:2px'>{items}</ol>"
    if note:
        html += f"<span style='color:#565656'>{note}</span>"
    return para(html, "padding: 6px 0px 8px 0px; border-bottom: 1px solid #e0e0e0;")


def ul(items: List[str]) -> str:
    return "<ul style='margin-left:-20px'>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def html_table(head: List[str], rows: List[List[str]]) -> str:
    h = "".join(f"<th align='left' style='background:#e9f6e9'>{x}</th>" for x in head)
    b = "".join("<tr>" + "".join(f"<td valign='top'>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table cellspacing='0' cellpadding='6' border='1' style='border-color:#d0d0d0'><tr>{h}</tr>{b}</table>"


def areas_table(rows: List[Tuple[str, str]]) -> str:
    body = "".join(
        f"<tr><td valign='top'><b>{label.replace(' ', '&nbsp;')}</b></td><td>{text}</td></tr>"
        for label, text in rows)
    return f"<table cellspacing='0' cellpadding='6'>{body}</table>"


def svg_widget(rel_path: str, values: Dict[str, str], w: int, h: int) -> QSvgWidget:
    with open(resource_path(rel_path), encoding="utf-8") as fh:
        src = fh.read()
    for k, v in (values or {}).items():
        src = src.replace("{{" + k + "}}", escape(v))
    svg = QSvgWidget()
    svg.load(QByteArray(src.encode("utf-8")))
    svg.setFixedSize(w, h)
    return svg


def scroll_page() -> Tuple[QScrollArea, QVBoxLayout]:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(24, 16, 24, 12)
    layout.setSpacing(10)
    scroll.setWidget(body)
    return scroll, layout


def render_block(layout: QVBoxLayout, block: tuple) -> None:
    kind = block[0]
    if kind == "p":
        layout.addWidget(para(block[1]))
    elif kind == "h":
        layout.addWidget(heading(block[1]))
    elif kind == "task":
        layout.addWidget(task(block[1], block[2], block[3] if len(block) > 3 else ""))
    elif kind == "note":
        layout.addWidget(para(block[1], NOTE_GREEN))
    elif kind == "warn":
        layout.addWidget(para(block[1], NOTE_YELLOW))
    elif kind == "ul":
        layout.addWidget(para(ul(block[1])))
    elif kind == "areas":
        layout.addWidget(para(areas_table(block[1])))
    elif kind == "table":
        layout.addWidget(para(html_table(block[1], block[2])))
    elif kind == "svg":
        _, path, values, w, h = block
        layout.addWidget(svg_widget(path, values, w, h), 0, Qt.AlignHCenter)
    else:
        raise ValueError(f"Unknown help block type: {kind!r}")


# ── Dialog ──────────────────────────────────────────────────────────────
class MultilangHelpDialog(QDialog):
    """Mehrsprachige Hilfe aus einer Daten-Beschreibung.

    texts[lang] = {"window_title": str, "close": str,
                   "tabs": [{"key": str, "title": str, "blocks": [block, ...]}, ...]}
    Alle Sprachen muessen dieselben Tab-Keys haben (Direkteinstieg per tab=)."""

    def __init__(self, texts: Dict[str, Dict[str, Any]], parent: Optional[QWidget] = None,
                 tab: Optional[str] = None, language: Optional[str] = None,
                 min_width: int = 1000):
        super().__init__(parent)
        self._texts = texts
        self._lang = language if language in texts else load_language()
        if self._lang not in texts:
            self._lang = DEFAULT_LANGUAGE
        self.setMinimumSize(min_width, 600)
        self.resize(min_width + 40, 820)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 12)
        outer.setSpacing(6)
        flag_row, self._flag_buttons = build_flag_row(self.set_language, self)
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
        if tab is not None:
            keys = [t["key"] for t in self._texts[self._lang]["tabs"]]
            if tab in keys:
                self.tabs.setCurrentIndex(keys.index(tab))

    def language(self) -> str:
        return self._lang

    def set_language(self, lang: str) -> None:
        if lang not in self._texts:
            return
        if lang != self._lang:
            self._lang = lang
            save_language(lang)
            self._apply_language()
        self._flag_buttons[lang].setChecked(True)

    def _apply_language(self) -> None:
        t = self._texts[self._lang]
        current = max(0, self.tabs.currentIndex())
        while self.tabs.count():
            page = self.tabs.widget(0)
            self.tabs.removeTab(0)
            page.deleteLater()
        for tab in t["tabs"]:
            scroll, layout = scroll_page()
            for block in tab["blocks"]:
                render_block(layout, block)
            layout.addStretch(1)
            self.tabs.addTab(scroll, tab["title"])
        self.tabs.setCurrentIndex(min(current, self.tabs.count() - 1))
        self.setWindowTitle(t["window_title"])
        self.btn_close.setText(t["close"])
        self._flag_buttons[self._lang].setChecked(True)


def show_help(texts: Dict[str, Dict[str, Any]], parent: Optional[QWidget] = None,
              tab: Optional[str] = None) -> None:
    MultilangHelpDialog(texts, parent, tab=tab).exec()


def make_help_button(tooltip: str, on_click: Callable[[], None]) -> QPushButton:
    """Runder gruener Hilfe-Button (help_tour.png, Fallback "?")."""
    btn = QPushButton()
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFixedSize(26, 26)
    btn.setToolTip(tooltip)
    btn.setStyleSheet(
        "QPushButton{background:transparent;border:1px solid #39a650;"
        "border-radius:13px;padding:0;}"
        "QPushButton:hover{background:#e8f5e9;}")
    icon = QIcon(resource_path("assets/images/help_tour.png"))
    if not icon.isNull():
        btn.setIcon(icon)
        btn.setIconSize(QSize(16, 16))
    else:
        btn.setText("?")
        btn.setStyleSheet(btn.styleSheet() + "QPushButton{color:#39a650;font-size:14px;font-weight:700;}")
    btn.clicked.connect(lambda: on_click())
    return btn


def check_texts(texts: Dict[str, Dict[str, Any]]) -> None:
    """Strukturpruefung fuer Tests: gleiche Sprachen, gleiche Tabs, gleiche
    Anzahl/Typen der Bausteine je Tab in allen Sprachen."""
    assert set(texts) == _CODES, set(texts)
    ref = texts[DEFAULT_LANGUAGE]
    for lang, t in texts.items():
        for k in ("window_title", "close", "tabs"):
            assert k in t, (lang, k)
        assert [x["key"] for x in t["tabs"]] == [x["key"] for x in ref["tabs"]], lang
        for a, b in zip(t["tabs"], ref["tabs"]):
            assert [blk[0] for blk in a["blocks"]] == [blk[0] for blk in b["blocks"]], (lang, a["key"])
