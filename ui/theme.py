# ui/theme.py
"""Zentrales Farbschema und QSS-Builder für TrippleT.

Alle UI-Farben sind hier definiert. Das QSS (Qt Stylesheet) wird einmalig
beim Start via ``build_qss()`` erzeugt und dem QApplication gesetzt.
Nach dem Login wird ``set_accent()`` aufgerufen und ``build_qss()`` erneut
ausgeführt, damit die Akzentfarbe aus dem Benutzerprofil greift.

Umgebungs-Farbcodierung des Headers:
  - Produktion (prod):  Anthrazit (#565656)
  - Entwicklung (dev):  Bordeaux (#800020)  → sofort sichtbar, dass NICHT prod
  - Lokal (dev_local):  Senfgelb (#E6C802)  → lokale Datenbank
  - Offline (offline):  Dunkelgrün (#1B4332) → lokale SQLite-Kopie, kein MySQL
    (is_offline_mode() checked BEFORE is_dev_local_mode() below: offline also
    reports is_dev_local_mode()==True, per db/connection.py, so existing
    "local path instead of network drive" branches keep working unchanged -
    without the explicit offline check first, the header would fall through
    to the same mustard yellow as dev_local, making the two indistinguishable)
"""

from db.connection import is_dev_mode, is_dev_local_mode, is_offline_mode
import re as _re

# --- Basis-Palette ---
DARK = "#565656"        # Anthrazit für Header/CardHeader
LIGHT_BG = "#f6f8f6"    # Hintergrundfarbe Hauptfenster (leicht gruen getoent statt reinem Grau)
CARD_BG = "#ffffff"     # Hintergrundfarbe Cards
_DEFAULT_ACCENT = "#39a650"  # Standard-Grün (Heberlein)
TEXT = "#2b2b2b"        # Standard-Textfarbe
PURPLE = "#8a2be2"      # Lila für PurpleBtn
BORDEAUX = "#800020"    # Bordeaux-Rot für DEV-Header
MUSTARD = "#E6C802"     # Senfgelb für DEV_LOCAL-Header
OFFLINE_GREEN = "#1B4332"  # Dunkelgrün für OFFLINE-Header - dark enough to stay distinct from the #39a650 brand accent
BORDER = "#dbe2dc"      # Neutraler, leicht gruen getoenter Rahmen (Ruhezustand von Feldern/Buttons/Cards)

# Rückwärtskompatibilität – alter Code der `from ui.theme import ACCENT` nutzt
ACCENT = _DEFAULT_ACCENT

# Header-Hintergrundfarbe je nach Laufzeitumgebung. is_offline_mode() muss vor
# is_dev_local_mode() geprueft werden, siehe Docstring oben.
HEADER_BG = (
    OFFLINE_GREEN if is_offline_mode()
    else MUSTARD if is_dev_local_mode()
    else BORDEAUX if is_dev_mode()
    else DARK
)
FOOTER_BG = DARK


# ---------------------------------------------------------------------------
# Akzent-Verwaltung (global, wird nach Login gesetzt)
# ---------------------------------------------------------------------------
_current_accent: str = _DEFAULT_ACCENT


def set_accent(hex_color) -> None:
    """Setzt die globale Akzentfarbe für den aktuellen Benutzer.

    Wird nach erfolgreichem Login aus ``app_meta.current_user['accent_color']``
    aufgerufen. Ungültige Werte (None, leerer String, kein gültiger Hex-Code)
    werden auf das Standard-Grün zurückgesetzt.

    Args:
        hex_color: Hex-Farbcode z.B. ``"#39a650"``, oder None/leer für Default.
    """
    global _current_accent
    val = (hex_color or "").strip()
    if val and _re.fullmatch(r"#[0-9A-Fa-f]{6}", val):
        _current_accent = val
    else:
        _current_accent = _DEFAULT_ACCENT


def get_accent() -> str:
    """Gibt die aktuell gesetzte Akzentfarbe als Hex-String zurück."""
    return _current_accent


def _blend(hex_color: str, factor: float) -> str:
    """Mischt eine Farbe mit Weiss (lineares Blending im RGB-Raum).

    Args:
        hex_color: Hex-Farbcode ohne führendes ``#``, z.B. ``"39a650"``.
        factor:    1.0 → Originalfarbe, 0.0 → reines Weiss, 0.18 → helles Tint.

    Returns:
        Hex-Farbcode mit ``#``-Präfix.
    """
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r2 = int(r * factor + 255 * (1 - factor))
    g2 = int(g * factor + 255 * (1 - factor))
    b2 = int(b * factor + 255 * (1 - factor))
    return f"#{r2:02x}{g2:02x}{b2:02x}"


def _shade(hex_color: str, factor: float) -> str:
    """Mischt eine Farbe mit Schwarz (lineares Blending im RGB-Raum).

    Wird für dunklere Text-Varianten auf hellem Tint-Hintergrund verwendet
    (z.B. Button-Text im :pressed-Zustand), damit der Kontrast unabhängig
    vom konkreten Farbton ausreicht.

    Args:
        hex_color: Hex-Farbcode ohne führendes ``#``, z.B. ``"39a650"``.
        factor:    1.0 → Originalfarbe, 0.0 → reines Schwarz.

    Returns:
        Hex-Farbcode mit ``#``-Präfix.
    """
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r2 = int(r * factor)
    g2 = int(g * factor)
    b2 = int(b * factor)
    return f"#{r2:02x}{g2:02x}{b2:02x}"


# Sidebar-Hintergrund: helleres Grau als DARK (Header/CardHeader) - Nutzerwunsch
# "dunkler grau, muss ja nicht ganz so dunkel sein wie die Topbar" (2026-08-26).
# Ueber _blend() aus DARK abgeleitet statt eines freihaendig gewaehlten Hex-Werts.
SIDEBAR_BG = _blend(DARK, 0.8)


def accent_tint() -> str:
    """Sehr helles Tint der Akzentfarbe für Tabellen-Header-Hintergründe.

    Bei Standard-Grün: ``#E9F6E9`` (factor=0.18).
    """
    return _blend(_current_accent, 0.18)


def accent_gridline() -> str:
    """Noch helleres Tint der Akzentfarbe für Tabellen-Gridlines.

    Bei Standard-Grün: ``#B5D7B5`` (factor=0.10).
    """
    return _blend(_current_accent, 0.10)


def accent_selection() -> str:
    """Selektionshintergrund für die Experiment-Tabelle (ExpTable).

    Bei Standard-Grün: ``#e6f2e6`` (factor=0.20).
    """
    return _blend(_current_accent, 0.20)


def accent_lineedit_sel() -> str:
    """Selektionshintergrund für QLineEdit.

    Bei Standard-Grün: ``#cdeccd`` (factor=0.25).
    """
    return _blend(_current_accent, 0.25)


# ---------------------------------------------------------------------------
# Button-Zustands-Tints (Hover/Pressed)
# ---------------------------------------------------------------------------
# Ersetzen die frühere harte Invertierung (Hover=Grau, Pressed=Schwarz+Weiss)
# durch sanfte Tints in der jeweiligen Button-Farbfamilie. Für den Standard-
# Button (und Back/Filter) folgt das der aktuellen (personalisierbaren)
# Akzentfarbe; GreenBtn/PurpleBtn folgen ihrer eigenen fixen Markenfarbe.

def accent_hover_tint() -> str:
    """Hover-Hintergrund für Standard-/Back-/Filter-Buttons (8% Akzent)."""
    return _blend(_current_accent, 0.08)


def accent_press_tint() -> str:
    """Pressed-Hintergrund für Standard-/Back-/Filter-Buttons (17% Akzent)."""
    return _blend(_current_accent, 0.17)


def accent_press_text() -> str:
    """Pressed-Textfarbe (abgedunkelter Akzent für Kontrast auf hellem Tint)."""
    return _shade(_current_accent, 0.75)


def default_accent_hover_tint() -> str:
    """Hover-Hintergrund für GreenBtn (8% festes Heberlein-Grün)."""
    return _blend(_DEFAULT_ACCENT, 0.08)


def default_accent_press_tint() -> str:
    """Pressed-Hintergrund für GreenBtn (17% festes Heberlein-Grün)."""
    return _blend(_DEFAULT_ACCENT, 0.17)


def default_accent_press_text() -> str:
    """Pressed-Textfarbe für GreenBtn."""
    return _shade(_DEFAULT_ACCENT, 0.75)


def purple_hover_tint() -> str:
    """Hover-Hintergrund für PurpleBtn (8% Lila)."""
    return _blend(PURPLE, 0.08)


def purple_press_tint() -> str:
    """Pressed-Hintergrund für PurpleBtn (17% Lila)."""
    return _blend(PURPLE, 0.17)


def purple_press_text() -> str:
    """Pressed-Textfarbe für PurpleBtn."""
    return _shade(PURPLE, 0.75)


# ---------------------------------------------------------------------------
# QSS-Template (Qt Stylesheet)
# ---------------------------------------------------------------------------
# Platzhalter werden in build_qss() via .replace() ersetzt.
# WICHTIG: Kein f-string verwenden, da CSS geschweifte Klammern enthält.
# ---------------------------------------------------------------------------
_QSS_TEMPLATE = """
QMainWindow {
    background: LIGHT_BG;
}
QToolTip {
    background-color: DARK;
    color: white;
    border: 1px solid rgba(255,255,255,0.25);
    padding: 4px 8px;
    border-radius: 4px;
}
#TopBar {
    background: HEADER_BG;
    color: white;
}
#BottomBar {
    background: FOOTER_BG;
    color: white;
}
#TopTitle {
    color: white;
    font-size: 22px;
    font-weight: 700;
}
#HomeBtn {
    background: transparent;
    border: 1px solid rgba(255,255,255,0.35);
    border-radius: 6px;
    color: white;
    padding: 6px 10px;
}
#HomeBtn:hover { background: rgba(255,255,255,0.12); }
#HomeBtn:pressed { background: rgba(255,255,255,0.22); }
#Card {
    background: CARD_BG;
    border: 1px solid BORDER;
    border-radius: 10px;
}
#CardHeader {
    background: DARK;
    color: white;
    padding: 4px 10px;
    font-size: 15px;
    font-weight: 600;
    min-height: 32px;
    max-height: 32px;
    border-radius: 10px 10px 0 0;
}
#SidebarPanel {
    background: SIDEBAR_BG;
}
#SidebarSectionLabel {
    color: rgba(255,255,255,0.42);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 2px 10px;
}
#SidebarBrandLabel {
    color: white;
    font-size: 16px;
    font-weight: 700;
}
#SidebarSubLabel {
    color: rgba(255,255,255,0.42);
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 1px;
}
QPushButton#SidebarItem {
    text-align: left;
    padding: 8px 10px;
    border: 1px solid transparent;
    border-radius: 8px;
    background: transparent;
    color: #dfe2df;
    font-size: 13px;
    font-weight: 500;
}
QPushButton#SidebarItem:hover {
    background: rgba(0,0,0,0.20);
    border: 1px solid rgba(0,0,0,0.28);
}
QPushButton#SidebarItem:pressed {
    background: rgba(0,0,0,0.32);
    border: 1px solid rgba(0,0,0,0.38);
}
QPushButton#SidebarItem:disabled { color: rgba(255,255,255,0.25); background: transparent; border-color: transparent; }
#HeroTile {
    background: rgba(255,255,255,0.65);
    border: 1px solid BORDER;
    border-radius: 14px;
}
#HeroTile:hover { background: #ffffff; }
#HeroTileLabel {
    color: TEXT;
    font-size: 14px;
    font-weight: 600;
}
.QLabel {
    color: TEXT;
    font-size: 13px;
}
#StatusLabel {
    color: TEXT;
    font-size: 13px;
}
QLineEdit {
    padding: 6px 8px;
    border: 1px solid BORDER;
    border-radius: 6px;
    background: #ffffff;
    color: TEXT;
    selection-background-color: LINEEDIT_SEL;
}
QLineEdit:focus {
    border: 1px solid ACCENT;
}
QLineEdit:disabled {
    color: #888;
    background: #f2f2f2;
}
QPlainTextEdit, QTextEdit {
    padding: 6px 8px;
    border: 1px solid BORDER;
    border-radius: 6px;
    background: #ffffff;
    color: TEXT;
    selection-background-color: LINEEDIT_SEL;
}
QPlainTextEdit:focus, QTextEdit:focus {
    border: 1px solid ACCENT;
}
QComboBox {
    padding: 5px 8px;
    border: 1px solid BORDER;
    border-radius: 6px;
    background: #ffffff;
    color: TEXT;
}
QComboBox:focus {
    border: 1px solid ACCENT;
}
QComboBox:disabled {
    color: #888;
    background: #f2f2f2;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: TEXT;
    outline: none;
    border: 1px solid ACCENT;
    selection-background-color: LINEEDIT_SEL;
    selection-color: TEXT;
    padding: 2px;
}
QComboBox QAbstractItemView::item {
    min-height: 24px;
    padding: 3px 8px;
    background-color: #ffffff;
    color: TEXT;
    border: none;
}
QComboBox QAbstractItemView::item:hover {
    background-color: #f0f0f0;
    color: TEXT;
}
QComboBox QAbstractItemView::item:selected {
    background-color: LINEEDIT_SEL;
    color: TEXT;
}
QSpinBox, QDoubleSpinBox {
    padding: 5px 6px;
    border: 1px solid BORDER;
    border-radius: 6px;
    background: #ffffff;
    color: TEXT;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid ACCENT;
}
QSpinBox:disabled, QDoubleSpinBox:disabled {
    color: #888;
    background: #f2f2f2;
}
QPushButton {
    padding: 8px 16px;
    border-radius: 6px;
    background: #eeeeee;
    border: 1px solid BORDER;
    color: TEXT;
}
QPushButton:hover { background: ACCENT_HOVER_TINT; }
QPushButton:pressed { background: ACCENT_PRESS_TINT; color: ACCENT_PRESS_TEXT; }
QPushButton:disabled {
    color: #9a9a9a; background: #efefef; border-color: #e0e0e0;
}
QPushButton#GreenBtn {
    border: 1px solid DEFAULT_ACCENT; color: DEFAULT_ACCENT; background: white;
}
QPushButton#GreenBtn:hover { background: DEFAULT_ACCENT_HOVER_TINT; }
QPushButton#GreenBtn:pressed { background: DEFAULT_ACCENT_PRESS_TINT; color: DEFAULT_ACCENT_PRESS_TEXT; }
QPushButton#PurpleBtn {
    border: 1px solid PURPLE; color: PURPLE; background: white;
}
QPushButton#PurpleBtn:hover { background: PURPLE_HOVER_TINT; }
QPushButton#PurpleBtn:pressed { background: PURPLE_PRESS_TINT; color: PURPLE_PRESS_TEXT; }
QPushButton#BackBtn {
    padding: 6px 14px;
    border-radius: 999px;
    background: #f7f7f7;
    border: 1px solid BORDER;
    color: TEXT;
    font-weight: 600;
}
QPushButton#BackBtn:hover { background: ACCENT_HOVER_TINT; }
QPushButton#BackBtn:pressed { background: ACCENT_PRESS_TINT; color: ACCENT_PRESS_TEXT; }
#FiltersBar {
    background: #fbfbfb;
    border-bottom: 1px solid #efefef;
}
QPushButton#FilterBtn {
    padding: 4px 12px;
    border-radius: 999px;
    border: 1px solid BORDER;
    background: white;
    color: ACCENT;
    font-weight: 600;
}
QPushButton#FilterBtn:hover { background: ACCENT_HOVER_TINT; color: ACCENT; border-color: ACCENT_HOVER_TINT; }
QPushButton#FilterBtn:pressed { background: ACCENT_PRESS_TINT; color: ACCENT; border-color: ACCENT_PRESS_TINT; }
QPushButton#FilterBtn:checked {
    background: ACCENT_PRESS_TINT; color: ACCENT; border-color: ACCENT_PRESS_TINT;
}
QTableWidget#ExpTable {
    gridline-color: #dcdcdc;
    background: #ffffff;
    outline: none;
    color: black;
    font-size: 13px;
}
QTableWidget#ExpTable::item:selected {
    background: EXP_SEL; color: #222;
}
QMessageBox {
  background: #ffffff;
  border: 1px solid #2f3b45;
  border-radius: 10px;
}
QMessageBox QLabel,
QMessageBox QLabel#qt_msgbox_label,
QMessageBox QLabel#qt_msgboxex_textlabel {
  color: #111111;
  font-size: 15px;
  line-height: 1.35em;
}
QMessageBox QTextEdit,
QMessageBox QPlainTextEdit {
  background: #fafafa;
  border: 1px solid #e3e3e3;
  color: #222;
}
QMessageBox QPushButton {
  padding: 6px 14px;
  border-radius: 8px;
  border: 1px solid #8a8a8a;
  min-width: 80px;
}
QMessageBox QPushButton:hover { background: #f2f2f2; }
QMessageBox QPushButton:default {
  background: #6e59ff; color: #ffffff; border: none;
}
"""


def build_qss() -> str:
    """Baut das vollständige QSS mit der aktuellen Akzentfarbe.

    Alle Platzhalter im Template (ACCENT, HEADER_BG, usw.) werden via
    ``.replace()`` durch die echten Farbwerte ersetzt. Diese Funktion
    wird beim Start und nach jedem Login erneut aufgerufen.

    Returns:
        Vollständiges Qt-Stylesheet als String, direkt an
        ``QApplication.setStyleSheet()`` übergeben werden kann.
    """
    return (
        _QSS_TEMPLATE
        # Wichtig: laengere/spezifischere Platzhalter zuerst ersetzen, da sie
        # kuerzere als Teilstring enthalten (z.B. "ACCENT" in "ACCENT_HOVER_TINT",
        # "TEXT" in "ACCENT_PRESS_TEXT"). Alle *_TEXT-Varianten muessen daher vor
        # dem generischen "TEXT" stehen, alle *_ACCENT*-Varianten vor "ACCENT".
        .replace("DEFAULT_ACCENT_HOVER_TINT", default_accent_hover_tint())
        .replace("DEFAULT_ACCENT_PRESS_TINT", default_accent_press_tint())
        .replace("DEFAULT_ACCENT_PRESS_TEXT", default_accent_press_text())
        .replace("PURPLE_HOVER_TINT", purple_hover_tint())
        .replace("PURPLE_PRESS_TINT", purple_press_tint())
        .replace("PURPLE_PRESS_TEXT", purple_press_text())
        .replace("ACCENT_HOVER_TINT", accent_hover_tint())
        .replace("ACCENT_PRESS_TINT", accent_press_tint())
        .replace("ACCENT_PRESS_TEXT", accent_press_text())
        .replace("LIGHT_BG",   LIGHT_BG)
        .replace("HEADER_BG",  HEADER_BG)
        .replace("FOOTER_BG",  FOOTER_BG)
        .replace("CARD_BG",    CARD_BG)
        .replace("SIDEBAR_BG", SIDEBAR_BG)
        .replace("DARK",       DARK)
        .replace("DEFAULT_ACCENT", _DEFAULT_ACCENT)
        .replace("PURPLE",     PURPLE)
        .replace("ACCENT",     _current_accent)
        .replace("BORDER",     BORDER)
        .replace("TEXT",       TEXT)
        .replace("LINEEDIT_SEL", accent_lineedit_sel())
        .replace("EXP_SEL",    accent_selection())
    )


# Initialer QSS-String beim Programmstart (Default-Grün, noch kein Benutzer eingeloggt)
APP_QSS = build_qss()
