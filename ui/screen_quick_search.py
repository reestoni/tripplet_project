from __future__ import annotations
# ui/screen_quick_search.py
"""Globaler Quick-Search-Dialog (Ctrl+F / 🔍-Button im Header).

Sucht in Echtzeit über alle Experimente nach:
  - Jet-Bezeichnungen (tblJet)
  - Maschinennamen (tblMaschine)
  - Seriennamen (tblTrialSeries)
  - Garnbezeichnungen (tblGarn)

Ergebnisse werden nach Übereinstimmungstyp gruppiert (Jet-Match, Maschinen-Match,
Serien-Match, Garn-Match) und als anklickbare Zeilen dargestellt.

Navigation:
  - Pfeil-Tasten: durch Ergebnisse navigieren
  - Enter: ausgewähltes Experiment öffnen
  - Escape: Dialog schliessen

Öffnung: ``app_meta.open_quick_search()`` oder ``HeaderBar``-🔍-Button.
Das Ergebnis liefert eine Experiment-ID an den ``on_open``-Callback, der in
``main.py`` gesetzt wird und zum jeweiligen Experiment-Screen navigiert.
"""

# ui/screen_quick_search.py

from typing import Any, Dict, List, Optional, Set

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog, QFrame, QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from db.connection import get_connection
from ui.pathutil import resource_path
from ui.theme import BORDER, CARD_BG, TEXT, accent_hover_tint, accent_tint, get_accent

# Modernisierung 2026-08-28 (Nutzerwunsch: "das such fenster selbst, kannst
# du das auch etwas modernisieren?", direkt nach dem Sidebar-Pinned-Search-
# Umbau): der Dialog stammte noch aus der Zeit vor dem Theme-/Akzentfarben-
# System und war hart auf ein eigenständiges, sehr dunkles Schema (#161616/
# #1e1e1e, festes Heberlein-Grün #39A650) verdrahtet - unabhängig von
# `ui/theme.py` und der App-weiten Akzentfarben-Wahl (siehe "Accent Colour"
# im Sidebar-Account-Bereich), und deutlich dunkler als der Rest der (hell
# gehaltenen) App inkl. der eigentlichen Sidebar (SIDEBAR_BG ist ein mittleres
# Grau, kein Schwarzton). Umgestellt auf dieselbe helle Karten-Optik wie der
# Rest der App (CARD_BG/BORDER/TEXT + get_accent()), plus ein echter
# Drop-Shadow (QGraphicsDropShadowEffect - frameless Fenster ohne das wirken
# sonst papierflach) und WA_TranslucentBackground (ohne das rendert Qt bei
# einem frameless QDialog trotz `border-radius` in der QSS ein rechteckiges,
# opakes Fenster - die "runden" Ecken waren dadurch zuvor eigentlich eckig
# mit sichtbaren Artefakten in den vier Ecken, nur auf dem sehr dunklen
# Hintergrund kaum auffällig). Reine Optik/Layout-Politur - Suchlogik
# (_terms/_search), Tastatur-Navigation und die drei nach aussen sichtbaren
# main.py-Schnittstellen (Konstruktor, `open_experiment`-Signal, `show()`)
# sind unverändert.


# ---------------------------------------------------------------------------
# DB search
# ---------------------------------------------------------------------------

def _terms(text: str) -> List[str]:
    """Tokenisiert den Suchtext in Einzelterme (lowercase, Leerzeichen-getrennt)."""
    """Split comma-separated input into stripped, non-empty terms."""
    return [t.strip() for t in text.split(",") if t.strip()]


def _search(jets: List[str], machines: List[str], series_names: List[str], yarns: List[str]) -> List[Dict]:
    """Führt die Datenbanksuche aus und gibt Treffer-Dicts zurück.

    Sucht gleichzeitig in Jet-, Maschinen-, Serien- und Garn-Feldern.
    Jede Zeile in tblTrialSeries × tblTrial × tblExperimente wird geprüft.

    Args:
        jets:         Suchbegriffe für Jet-Spalten.
        machines:     Suchbegriffe für Maschinen-Spalten.
        series_names: Suchbegriffe für Serien-Namen.
        yarns:        Suchbegriffe für Garn-Spalten.

    Returns:
        Liste von Dicts mit Keys: exp_pk, exp_id, series_pk, series_name, maschine, reason.
    """
    """
    Returns series that match ALL supplied filters (AND logic).
    Within each filter, multiple terms are also AND (series must contain all).
    """
    hits: Dict[int, Dict] = {}   # series_pk → result dict

    def _add(exp_pk, exp_id, series_pk, series_name, maschine, reason):
        spk = int(series_pk)
        if spk not in hits:
            hits[spk] = {
                "exp_pk":      exp_pk,
                "exp_id":      str(exp_id or ""),
                "series_pk":   spk,
                "series_name": str(series_name or ""),
                "maschine":    str(maschine or ""),
                "reasons":     [],
            }
        if reason and reason not in hits[spk]["reasons"]:
            hits[spk]["reasons"].append(reason)

    try:
        with get_connection() as cn:
            cur = cn.cursor()

            # --- Build candidate series from first available filter ---
            # Strategy: start with all series, then intersect per filter.

            # Step 1: get ALL series (we filter in Python for flexibility)
            cur.execute(
                "SELECT e.ID, e.[Experiment ID], s.ID, s.SeriesName, m.Maschine "
                "FROM (tblExperimente AS e "
                "INNER JOIN tblTrialSeries AS s ON s.ExperimentID = e.ID) "
                "LEFT JOIN tblMaschine AS m ON m.ID = s.MachineID "
                "ORDER BY e.[Experiment ID] DESC, s.ID"
            )
            all_series = {}
            for row in cur.fetchall() or []:
                spk = int(row[2])
                all_series[spk] = {
                    "exp_pk":      row[0],
                    "exp_id":      str(row[1] or ""),
                    "series_pk":   spk,
                    "series_name": str(row[3] or ""),
                    "maschine":    str(row[4] or ""),
                }

            # Step 2: build jet index  series_pk → set of jet names
            cur.execute(
                "SELECT t.TrialSeriesID, j.Jet "
                "FROM tblTrial AS t "
                "INNER JOIN tblDTYJets AS j ON j.ID = t.JetID"
            )
            jet_index: Dict[int, Set[str]] = {}
            for row in cur.fetchall() or []:
                spk = int(row[0])
                jet_index.setdefault(spk, set()).add(str(row[1] or "").lower())

            # Step 3: build yarn index  series_pk → set of yarn names
            cur.execute(
                "SELECT t.TrialSeriesID, y.Name "
                "FROM tbltrialsettings ts "
                "JOIN tbltrial t ON t.ID = ts.TrialID "
                "INNER JOIN tblYarn AS y ON y.ID = ts.YarnID "
                "WHERE ts.YarnID IS NOT NULL"
            )
            yarn_index: Dict[int, Set[str]] = {}
            for row in cur.fetchall() or []:
                spk = int(row[0])
                yarn_index.setdefault(spk, set()).add(str(row[1] or "").lower())

    except Exception:
        return []

    # --- Filter in Python (AND across filters, AND within multi-term) ---
    result = []
    for spk, s in all_series.items():
        reasons = []
        skip = False

        # Filter: Series name (all terms must appear in series name OR experiment ID)
        if series_names:
            combined = (s["series_name"] + " " + s["exp_id"]).lower()
            if not all(t.lower() in combined for t in series_names):
                skip = True
            else:
                reasons.append("Series: " + ", ".join(series_names))

        if skip:
            continue

        # Filter: Machine (all terms must appear in machine name)
        if machines:
            if not all(m.lower() in s["maschine"].lower() for m in machines):
                skip = True
            else:
                reasons.append("Machine: " + ", ".join(machines))

        if skip:
            continue

        # Filter: Jets (ALL jet terms must be found among jets used in this series)
        if jets:
            jets_in_series = jet_index.get(spk, set())
            matched = []
            all_found = True
            for jet_term in jets:
                found = any(jet_term.lower() in j for j in jets_in_series)
                if not found:
                    all_found = False
                    break
                matched.append(jet_term)
            if not all_found:
                continue
            reasons.append("Jet: " + ", ".join(matched))

        # Filter: Yarns (ALL yarn terms must be found among yarns used in this series)
        if yarns:
            yarns_in_series = yarn_index.get(spk, set())
            matched_y = []
            all_found_y = True
            for yarn_term in yarns:
                found = any(yarn_term.lower() in y for y in yarns_in_series)
                if not found:
                    all_found_y = False
                    break
                matched_y.append(yarn_term)
            if not all_found_y:
                continue
            reasons.append("Yarn: " + ", ".join(matched_y))

        result.append({**s, "reasons": reasons})

    return result


# ---------------------------------------------------------------------------
# Close button (custom-painted, seit Modernisierung 2026-08-28)
# ---------------------------------------------------------------------------

class _CloseButton(QPushButton):
    """Abgerundetes Quadrat mit selbst gezeichnetem X statt eines reinen
    Text-Glyphen ("✕") in einem harten Kreis - Nutzerfeedback: "den button
    selbst kannst du sicherlich noch etwas schöner machen als einfach nur
    einen kreis". Selbst gemalt statt Font-Glyph, damit der Strich unabhängig
    von Systemschriftart/DPI immer gleich sauber, zentriert und in
    konsistenter Strichstärke aussieht (schliesst nebenbei die Lücke aus der
    Modernisierung oben, wo ✕ auf mind. einem Testsystem als leeres
    Font-Rechteck statt eines echten Glyphen gerendert wurde) - und passt mit
    seiner abgerundeten Ecke (8px, wie die Suchfeld-Chips) besser zur übrigen
    Formsprache der Karte als ein isolierter perfekter Kreis. Roter Hover
    bleibt (etabliertes "Fenster schliessen"-Muster), aber gedeckter/wärmer
    (#e8837a) statt knallig, damit er neben dem sonst durchgehend hellen,
    ruhigen Karten-Look nicht wie ein Alarm wirkt."""

    _BG_IDLE = "#f6f8f6"
    _BG_HOVER = "#e8837a"
    _X_IDLE = "#7a827c"
    _X_HOVER = "#ffffff"

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        self.setCursor(Qt.PointingHandCursor)
        self.setFlat(True)
        self.setStyleSheet("QPushButton { border: none; background: transparent; }")

    def paintEvent(self, ev):
        hovered = self.underMouse() and self.isEnabled()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        p.setPen(QPen(QColor(BORDER) if not hovered else QColor(self._BG_HOVER), 1))
        p.setBrush(QColor(self._BG_HOVER if hovered else self._BG_IDLE))
        p.drawRoundedRect(rect, 8, 8)

        pen = QPen(QColor(self._X_HOVER if hovered else self._X_IDLE))
        pen.setWidthF(1.6)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        m = 10.0
        c = rect.center()
        p.drawLine(c.x() - m / 2, c.y() - m / 2, c.x() + m / 2, c.y() + m / 2)
        p.drawLine(c.x() - m / 2, c.y() + m / 2, c.x() + m / 2, c.y() - m / 2)
        p.end()

    def enterEvent(self, ev):
        self.update()
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        self.update()
        super().leaveEvent(ev)


# ---------------------------------------------------------------------------
# Result row widget
# ---------------------------------------------------------------------------

class _ResultRow(QFrame):
    """Einzelne Ergebniszeile im Quick-Search-Dialog.

    Zeigt Experiment-ID, Serienname, Maschine und Treffergrund an.
    Wird bei Klick oder Enter markiert (aktiv) und löst on_click aus.
    """
    clicked = Signal(object)

    def __init__(self, data: Dict, subtitle: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self._data = data
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(52)
        accent = get_accent()
        self._style_normal = (
            f"QFrame {{ background: {CARD_BG}; border: none; border-left: 3px solid transparent;"
            f" border-bottom: 1px solid {BORDER}; }}"
            f"QFrame:hover {{ background: {accent_hover_tint()}; }}"
        )
        self._style_active = (
            f"QFrame {{ background: {accent_tint()}; border: none; border-left: 3px solid {accent};"
            f" border-bottom: 1px solid {BORDER}; }}"
        )
        self.setStyleSheet(self._style_normal)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(13, 4, 14, 4)
        lay.setSpacing(8)

        col = QVBoxLayout()
        col.setSpacing(1)

        lbl_main = QLabel(data.get("_display", ""))
        lbl_main.setStyleSheet(f"font-size: 12.5px; font-weight: 600; color: {TEXT};")
        col.addWidget(lbl_main)

        if subtitle:
            lbl_sub = QLabel(subtitle)
            lbl_sub.setStyleSheet("font-size: 10.5px; color: #7a827c;")
            col.addWidget(lbl_sub)

        lay.addLayout(col, 1)

        arrow = QLabel("→")
        arrow.setStyleSheet(f"color: {accent}; font-size: 14px;")
        lay.addWidget(arrow)

    def set_active(self, active: bool):
        """Markiert die Zeile als aktiv (Tastatur-Fokus) oder inaktiv."""
        self.setStyleSheet(self._style_active if active else self._style_normal)

    def mousePressEvent(self, ev):
        """Löst den on_click-Callback mit den Zeilendaten aus."""
        if ev.button() == Qt.LeftButton:
            self.clicked.emit(self._data)
        super().mousePressEvent(ev)


# ---------------------------------------------------------------------------
# Section header
# ---------------------------------------------------------------------------

class _SectionHeader(QFrame):
    """Trennzeile zwischen Ergebnisgruppen (z.B. "Jet-Treffer (3)")."""
    def __init__(self, title: str, count: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.setStyleSheet(f"QFrame {{ background: {accent_tint()}; border-bottom: 1px solid {BORDER}; }}")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lbl = QLabel(title)
        lbl.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {get_accent()}; letter-spacing: 1px;")
        lay.addWidget(lbl)
        lay.addStretch(1)
        cnt = QLabel(f"{count} result(s)")
        cnt.setStyleSheet("font-size: 10px; color: #7a827c;")
        lay.addWidget(cnt)


# ---------------------------------------------------------------------------
# Search field with label
# ---------------------------------------------------------------------------

class _SearchField(QFrame):
    """Einzelnes Suchfeld mit Label (z.B. "Jet:", "Maschine:")."""
    def __init__(self, label: str, placeholder: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("QuickSearchField")
        accent = get_accent()
        self._style_normal = (
            f"QFrame#QuickSearchField {{ background: #f6f8f6; border-radius: 8px; border: 1px solid {BORDER}; }}"
        )
        self._style_focus = (
            f"QFrame#QuickSearchField {{ background: #f6f8f6; border-radius: 8px; border: 1.5px solid {accent}; }}"
        )
        self.setStyleSheet(self._style_normal)
        self.setMinimumHeight(56)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 7, 12, 7)
        lay.setSpacing(3)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: 9px; color: {accent}; font-weight: 700; letter-spacing: 1px;")
        lay.addWidget(lbl)

        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setStyleSheet(
            f"QLineEdit {{ background: transparent; border: none; "
            f"font-size: 14px; color: {TEXT}; }}"
        )
        # Fokus-Ring auf dem umschliessenden Frame statt nur auf dem
        # QLineEdit selbst - konsistent mit den runden "Chip"-Feldern.
        self.edit.focusInEvent = self._wrap_focus(self.edit.focusInEvent, True)
        self.edit.focusOutEvent = self._wrap_focus(self.edit.focusOutEvent, False)
        lay.addWidget(self.edit)

    def _wrap_focus(self, original, focused: bool):
        def handler(ev):
            self.setStyleSheet(self._style_focus if focused else self._style_normal)
            original(ev)
        return handler


# ---------------------------------------------------------------------------
# Quick Search Dialog
# ---------------------------------------------------------------------------

class QuickSearchDialog(QDialog):
    """Modaler Such-Dialog mit vier Suchfeldern und scrollbarer Ergebnisliste.

    Wird einmalig beim Start erstellt und via show()/hide() geöffnet/geschlossen.
    Der on_open-Callback (gesetzt in main.py) öffnet das gewählte Experiment.
    """
    open_experiment = Signal(int, int, str)   # exp_pk, series_pk, exp_id

    # Bausteine für die dynamische Fensterhöhe (siehe _show_hint()/_populate()) -
    # als Konstanten statt wiederholter Magic Numbers, seit der Modernisierung
    # 2026-08-28 (Karte + 16px Drop-Shadow-Rand statt Dialog == Karte 1:1).
    _OUTER_MARGIN = 32   # 16px Rand oben+unten für den Drop-Shadow (siehe outer.setContentsMargins)
    _BAR_HEIGHT = 84
    _FOOTER_HEIGHT = 30
    _HEADER_HEIGHT = 30
    _ROW_HEIGHT = 52
    _HINT_HEIGHT = 90

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        # Ohne das rendert Qt bei einem frameless QDialog trotz `border-radius`
        # in der QSS ein rechteckiges, opakes Fenster - die "runden" Ecken
        # unten sind ohne dieses Attribut nur optisch gerundet, tatsächlich
        # aber eckig mit sichtbaren Artefakten (siehe Moduldocstring).
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setFixedWidth(860)

        accent = get_accent()
        # Der eigentliche Karten-Look sitzt auf `_card` statt direkt auf dem
        # (jetzt transparenten) QDialog, da WA_TranslucentBackground +
        # border-radius auf dem Dialog selbst je nach Plattform inkonsequent
        # gerendert wird - ein normales QFrame-Kind rundet zuverlässig.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)  # Platz für den Drop-Shadow
        card = QFrame()
        card.setObjectName("QuickSearchCard")
        card.setStyleSheet(
            f"QFrame#QuickSearchCard {{ background: {CARD_BG}; border: 1px solid {BORDER};"
            f" border-radius: 14px; }}"
        )
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(48)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 90))
        card.setGraphicsEffect(shadow)
        outer.addWidget(card)

        root = QVBoxLayout(card)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- Search fields bar ----
        bar = QFrame()
        bar.setStyleSheet(f"QFrame {{ background: {CARD_BG}; border-bottom: 1px solid {BORDER};"
                           f" border-top-left-radius: 14px; border-top-right-radius: 14px; }}")
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(16, 14, 12, 14)
        bar_lay.setSpacing(10)

        lbl_icon = QLabel()
        icon_pm = QPixmap(resource_path("assets/images/quick_Search.png"))
        if not icon_pm.isNull():
            lbl_icon.setPixmap(icon_pm.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            lbl_icon.setText("🔍")
            lbl_icon.setStyleSheet("font-size: 18px;")
        bar_lay.addWidget(lbl_icon, 0, Qt.AlignVCenter)

        self._f_series  = _SearchField("SERIES NAME", "e.g. Intermingling")
        self._f_jet     = _SearchField("JET(S)", "e.g. P213, APh213")
        self._f_yarn    = _SearchField("YARN(S)", "e.g. PES 78f36")
        self._f_machine = _SearchField("MACHINE(S)", "e.g. eAFK")

        bar_lay.addWidget(self._f_series, 2)
        bar_lay.addWidget(self._f_jet, 2)
        bar_lay.addWidget(self._f_yarn, 2)
        bar_lay.addWidget(self._f_machine, 1)

        btn_close = _CloseButton()
        btn_close.setToolTip("Close (Esc)")
        btn_close.clicked.connect(self.close)
        bar_lay.addWidget(btn_close, 0, Qt.AlignVCenter)

        root.addWidget(bar)

        # ---- Hint ----
        self._lbl_hint = QLabel("Fill in at least one field to search…")
        self._lbl_hint.setAlignment(Qt.AlignCenter)
        self._lbl_hint.setStyleSheet(f"color: #7a827c; font-size: 12px; padding: 28px; background: {CARD_BG};")
        root.addWidget(self._lbl_hint)

        # ---- Results ----
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet(f"QScrollArea {{ background: {CARD_BG}; border: none; }}")
        self._scroll.hide()

        self._results_host = QWidget()
        self._results_host.setStyleSheet(f"QWidget {{ background: {CARD_BG}; }}")
        self._results_lay = QVBoxLayout(self._results_host)
        self._results_lay.setContentsMargins(0, 0, 0, 0)
        self._results_lay.setSpacing(0)
        self._results_lay.addStretch(1)
        self._scroll.setWidget(self._results_host)
        root.addWidget(self._scroll, 1)

        # ---- Footer ----
        footer = QFrame()
        footer.setFixedHeight(30)
        footer.setStyleSheet(
            f"QFrame {{ background: #f6f8f6; border-top: 1px solid {BORDER};"
            f" border-bottom-left-radius: 14px; border-bottom-right-radius: 14px; }}"
        )
        footer_lay = QHBoxLayout(footer)
        footer_lay.setContentsMargins(16, 0, 16, 0)
        lbl_esc = QLabel("ESC to close  ·  ↑↓ to navigate  ·  Enter to open  ·  comma = AND within field")
        lbl_esc.setStyleSheet("color: #9aa39c; font-size: 10px;")
        footer_lay.addWidget(lbl_esc)
        root.addWidget(footer)

        # Debounce
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(350)
        self._timer.timeout.connect(self._do_search)

        for f in (self._f_series, self._f_jet, self._f_yarn, self._f_machine):
            f.edit.textChanged.connect(self._on_text_changed)
            f.edit.installEventFilter(self)

        self._rows: List[_ResultRow] = []
        self._all_widgets: List[QWidget] = []
        self._active_row: int = -1

        self.setFixedHeight(self._OUTER_MARGIN + self._BAR_HEIGHT + self._FOOTER_HEIGHT + self._HINT_HEIGHT)

    def showEvent(self, ev):
        """Setzt den Fokus auf das erste Suchfeld beim Öffnen."""
        super().showEvent(ev)
        self._f_series.edit.setFocus()
        if self.parent():
            pg = self.parent().geometry()
            x = pg.x() + (pg.width() - self.width()) // 2
            y = pg.y() + (pg.height() - self.height()) // 3
            self.move(x, y)

    def keyPressEvent(self, ev: QKeyEvent):
        """Escape → schliessen; Pfeil-Tasten → Selektion bewegen; Enter → aktivieren."""
        if ev.key() == Qt.Key_Escape:
            self.close()
        elif ev.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._activate_current()
        elif ev.key() == Qt.Key_Down:
            self._move_selection(1)
        elif ev.key() == Qt.Key_Up:
            self._move_selection(-1)
        else:
            super().keyPressEvent(ev)

    def eventFilter(self, obj, ev):
        """Fängt Pfeil- und Enter-Tasten in den Suchfeldern ab für Tastaturnavigation."""
        edits = [f.edit for f in (self._f_series, self._f_jet, self._f_yarn, self._f_machine)]
        if obj in edits and ev.type() == ev.Type.KeyPress:
            if ev.key() == Qt.Key_Down:
                self._move_selection(1); return True
            if ev.key() == Qt.Key_Up:
                self._move_selection(-1); return True
            if ev.key() in (Qt.Key_Return, Qt.Key_Enter):
                self._activate_current(); return True
        return super().eventFilter(obj, ev)

    def _on_text_changed(self):
        """Startet die Suche mit 300ms Debounce-Timer nach jeder Texteingabe."""
        jets    = _terms(self._f_jet.edit.text())
        machines = _terms(self._f_machine.edit.text())
        series  = _terms(self._f_series.edit.text())
        yarns   = _terms(self._f_yarn.edit.text())
        if not jets and not machines and not series and not yarns:
            self._show_hint("Fill in at least one field to search…")
            self._timer.stop()
            return
        self._timer.start()

    def _do_search(self):
        """Liest die Suchfelder aus, ruft _search() auf und aktualisiert die Ergebnisliste."""
        jets     = _terms(self._f_jet.edit.text())
        machines = _terms(self._f_machine.edit.text())
        series   = _terms(self._f_series.edit.text())
        yarns    = _terms(self._f_yarn.edit.text())
        if not jets and not machines and not series and not yarns:
            return
        results = _search(jets, machines, series, yarns)
        self._populate(results)

    def _populate(self, results: List[Dict]):
        """Befüllt die Ergebnisliste mit gruppierten _ResultRow-Widgets."""
        for w in self._all_widgets:
            self._results_lay.removeWidget(w)
            w.deleteLater()
        self._all_widgets.clear()
        self._rows.clear()
        self._active_row = -1

        ins = self._results_lay.count() - 1

        if not results:
            self._show_hint("No results found.")
            return

        hdr = _SectionHeader("🔬  SERIES", len(results))
        self._results_lay.insertWidget(ins, hdr)
        self._all_widgets.append(hdr)
        ins += 1

        for r in results:
            display = f"{r['exp_id']}  ·  {r['series_name']}"
            parts = []
            if r["maschine"]:
                parts.append(r["maschine"])
            if r["reasons"]:
                parts.append("  ·  ".join(r["reasons"]))
            sub = "    ".join(parts)
            r["_display"] = display
            row = _ResultRow(r, sub)
            row.clicked.connect(self._on_row_clicked)
            self._results_lay.insertWidget(ins, row)
            self._rows.append(row)
            self._all_widgets.append(row)
            ins += 1

        self._lbl_hint.hide()
        self._scroll.show()
        content_h = self._HEADER_HEIGHT + len(results) * self._ROW_HEIGHT
        self.setFixedHeight(min(760, self._OUTER_MARGIN + self._BAR_HEIGHT + self._FOOTER_HEIGHT + content_h))

    def _show_hint(self, text: str):
        """Zeigt einen Hinweistext (z.B. "Keine Ergebnisse") statt der Ergebnisliste."""
        self._scroll.hide()
        self._lbl_hint.setText(text)
        self._lbl_hint.show()
        self.setFixedHeight(self._OUTER_MARGIN + self._BAR_HEIGHT + self._FOOTER_HEIGHT + self._HINT_HEIGHT)

    def _move_selection(self, delta: int):
        """Bewegt die Tastatur-Selektion um delta Schritte (+1 / -1)."""
        if not self._rows:
            return
        self._set_active(self._active_row, False)
        self._active_row = max(0, min(len(self._rows) - 1, self._active_row + delta))
        self._set_active(self._active_row, True)
        try:
            self._scroll.ensureWidgetVisible(self._rows[self._active_row])
        except Exception:
            pass

    def _set_active(self, idx: int, active: bool):
        """Setzt den Aktiv-Status einer Ergebniszeile per Index."""
        if 0 <= idx < len(self._rows):
            self._rows[idx].set_active(active)

    def _activate_current(self):
        """Öffnet das aktuell markierte Experiment (Enter-Taste oder Doppelklick)."""
        idx = self._active_row
        if 0 <= idx < len(self._rows):
            self._rows[idx].clicked.emit(self._rows[idx]._data)
        elif self._rows:
            self._rows[0].clicked.emit(self._rows[0]._data)

    def _on_row_clicked(self, data: Dict):
        """Callback wenn eine Ergebniszeile angeklickt wird: ruft on_open mit der Experiment-ID auf."""
        self.hide()
        exp_pk     = int(data["exp_pk"])
        series_pk  = int(data["series_pk"])
        exp_id     = data["exp_id"]
        QTimer.singleShot(0, lambda: self.open_experiment.emit(exp_pk, series_pk, exp_id))
        QTimer.singleShot(50, self.close)