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
"""

from db.connection import is_dev_mode, is_dev_local_mode
import re as _re

# --- Basis-Palette ---
DARK = "#565656"        # Anthrazit für Header/CardHeader
LIGHT_BG = "#f4f4f5"    # Hintergrundfarbe Hauptfenster
CARD_BG = "#ffffff"     # Hintergrundfarbe Cards
_DEFAULT_ACCENT = "#39a650"  # Standard-Grün (Heberlein)
TEXT = "#2b2b2b"        # Standard-Textfarbe
PURPLE = "#8a2be2"      # Lila für PurpleBtn
BORDEAUX = "#800020"    # Bordeaux-Rot für DEV-Header
MUSTARD = "#E6C802"     # Senfgelb für DEV_LOCAL-Header

# Rückwärtskompatibilität – alter Code der `from ui.theme import ACCENT` nutzt
ACCENT = _DEFAULT_ACCENT

# Header-Hintergrundfarbe je nach Laufzeitumgebung
HEADER_BG = MUSTARD if is_dev_local_mode() else (BORDEAUX if is_dev_mode() else DARK)
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
# QSS-Template (Qt Stylesheet)
# ---------------------------------------------------------------------------
# Platzhalter werden in build_qss() via .replace() ersetzt.
# WICHTIG: Kein f-string verwenden, da CSS geschweifte Klammern enthält.
# ---------------------------------------------------------------------------
_QSS_TEMPLATE = """
QMainWindow {
    background: LIGHT_BG;
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
    font-size: 20px;
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
    border: 1px solid #cfcfcf;
    border-radius: 2px;
}
#CardHeader {
    background: DARK;
    color: white;
    padding: 4px 10px;
    font-size: 14px;
    font-weight: 600;
    min-height: 32px;
    max-height: 32px;
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
    border: 1px solid ACCENT;
    border-radius: 1px;
    background: #ffffff;
    color: TEXT;
    selection-background-color: LINEEDIT_SEL;
}
QLineEdit:disabled {
    color: #888;
    background: #f2f2f2;
}
QPushButton {
    padding: 8px 16px;
    border-radius: 3px;
    background: #eeeeee;
    border: 1px solid #d0d0d0;
    color: TEXT;
}
QPushButton:hover { background: #e9e9e9; }
QPushButton:pressed { background: #555555; color: white; }
QPushButton:disabled {
    color: #9a9a9a; background: #efefef; border-color: #e0e0e0;
}
QPushButton#GreenBtn {
    border: 1px solid DEFAULT_ACCENT; color: DEFAULT_ACCENT; background: white;
}
QPushButton#GreenBtn:hover { background: #e9e9e9; }
QPushButton#GreenBtn:pressed { background: #555555; color: white; }
QPushButton#PurpleBtn {
    border: 1px solid PURPLE; color: PURPLE; background: white;
}
QPushButton#PurpleBtn:hover { background: #e9e9e9; }
QPushButton#PurpleBtn:pressed { background: #555555; color: white; }
QPushButton#BackBtn {
    padding: 6px 14px;
    border-radius: 16px;
    background: #f7f7f7;
    border: 1px solid #d6d6d6;
    color: TEXT;
    font-weight: 600;
}
QPushButton#BackBtn:hover { background: #ececec; }
QPushButton#BackBtn:pressed { background: #555; color: white; }
#FiltersBar {
    background: #fbfbfb;
    border-bottom: 1px solid #efefef;
}
QPushButton#FilterBtn {
    padding: 4px 12px;
    border-radius: 12px;
    border: 1px solid #c9c9c9;
    background: white;
    color: ACCENT;
    font-weight: 600;
}
QPushButton#FilterBtn:hover { background: #e9e9e9; color: ACCENT; }
QPushButton#FilterBtn:pressed { background: #000000; color: ACCENT; }
QPushButton#FilterBtn:checked {
    background: #000000; color: ACCENT; border-color: #000000;
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
        .replace("DEFAULT_ACCENT", _DEFAULT_ACCENT)
        .replace("LIGHT_BG",   LIGHT_BG)
        .replace("HEADER_BG",  HEADER_BG)
        .replace("FOOTER_BG",  FOOTER_BG)
        .replace("CARD_BG",    CARD_BG)
        .replace("DARK",       DARK)
        .replace("TEXT",       TEXT)
        .replace("PURPLE",     PURPLE)
        .replace("ACCENT",     _current_accent)
        .replace("LINEEDIT_SEL", accent_lineedit_sel())
        .replace("EXP_SEL",    accent_selection())
    )


# Initialer QSS-String beim Programmstart (Default-Grün, noch kein Benutzer eingeloggt)
APP_QSS = build_qss()
