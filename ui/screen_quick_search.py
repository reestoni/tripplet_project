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
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from db.connection import get_connection


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
        self.setFixedHeight(48)
        self._style_normal = (
            "QFrame { background: #1e1e1e; border: none; border-bottom: 1px solid #2a2a2a; }"
            "QFrame:hover { background: #2d4a35; }"
        )
        self._style_active = (
            "QFrame { background: #2d4a35; border: none; border-bottom: 1px solid #2a2a2a; }"
        )
        self.setStyleSheet(self._style_normal)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 4, 12, 4)
        lay.setSpacing(8)

        col = QVBoxLayout()
        col.setSpacing(1)

        lbl_main = QLabel(data.get("_display", ""))
        lbl_main.setStyleSheet("font-size: 12px; font-weight: bold; color: #f0f0f0;")
        col.addWidget(lbl_main)

        if subtitle:
            lbl_sub = QLabel(subtitle)
            lbl_sub.setStyleSheet("font-size: 10px; color: #888;")
            col.addWidget(lbl_sub)

        lay.addLayout(col, 1)

        arrow = QLabel("→")
        arrow.setStyleSheet("color: #39A650; font-size: 14px;")
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
        self.setFixedHeight(28)
        self.setStyleSheet("QFrame { background: #111; border-bottom: 1px solid #39A650; }")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lbl = QLabel(title)
        lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #39A650; letter-spacing: 1px;")
        lay.addWidget(lbl)
        lay.addStretch(1)
        cnt = QLabel(f"{count} result(s)")
        cnt.setStyleSheet("font-size: 10px; color: #666;")
        lay.addWidget(cnt)


# ---------------------------------------------------------------------------
# Search field with label
# ---------------------------------------------------------------------------

class _SearchField(QFrame):
    """Einzelnes Suchfeld mit Label (z.B. "Jet:", "Maschine:")."""
    def __init__(self, label: str, placeholder: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet("QFrame { background: #222; border-radius: 4px; border: 1px solid #333; }")
        self.setMinimumHeight(58)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(3)

        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 9px; color: #39A650; font-weight: bold; letter-spacing: 1px;")
        lay.addWidget(lbl)

        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setStyleSheet(
            "QLineEdit { background: transparent; border: none; "
            "font-size: 14px; color: #f0f0f0; }"
        )
        lay.addWidget(self.edit)


# ---------------------------------------------------------------------------
# Quick Search Dialog
# ---------------------------------------------------------------------------

class QuickSearchDialog(QDialog):
    """Modaler Such-Dialog mit vier Suchfeldern und scrollbarer Ergebnisliste.

    Wird einmalig beim Start erstellt und via show()/hide() geöffnet/geschlossen.
    Der on_open-Callback (gesetzt in main.py) öffnet das gewählte Experiment.
    """
    open_experiment = Signal(int, int, str)   # exp_pk, series_pk, exp_id

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.setFixedWidth(860)
        self.setStyleSheet("""
            QDialog {
                background: #161616;
                border: 1px solid #39A650;
                border-radius: 8px;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- Search fields bar ----
        bar = QFrame()
        bar.setStyleSheet("QFrame { background: #1a1a1a; border-bottom: 1px solid #333; }")
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(12, 10, 12, 10)
        bar_lay.setSpacing(8)

        lbl_icon = QLabel("🔍")
        lbl_icon.setStyleSheet("font-size: 20px;")
        bar_lay.addWidget(lbl_icon, 0, Qt.AlignVCenter)

        self._f_series  = _SearchField("SERIES NAME", "e.g. Intermingling")
        self._f_jet     = _SearchField("JET(S)", "e.g. P213, APh213")
        self._f_yarn    = _SearchField("YARN(S)", "e.g. PES 78f36")
        self._f_machine = _SearchField("MACHINE(S)", "e.g. eAFK")

        bar_lay.addWidget(self._f_series, 2)
        bar_lay.addWidget(self._f_jet, 2)
        bar_lay.addWidget(self._f_yarn, 2)
        bar_lay.addWidget(self._f_machine, 1)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setStyleSheet(
            "QPushButton { background: #333; border-radius: 14px; color: #aaa; font-size: 13px; border: none; }"
            "QPushButton:hover { background: #c0392b; color: white; }"
        )
        btn_close.clicked.connect(self.close)
        bar_lay.addWidget(btn_close, 0, Qt.AlignVCenter)

        root.addWidget(bar)

        # ---- Hint ----
        self._lbl_hint = QLabel("Fill in at least one field to search…")
        self._lbl_hint.setAlignment(Qt.AlignCenter)
        self._lbl_hint.setStyleSheet("color: #555; font-size: 12px; padding: 24px;")
        root.addWidget(self._lbl_hint)

        # ---- Results ----
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet("QScrollArea { background: #161616; border: none; }")
        self._scroll.hide()

        self._results_host = QWidget()
        self._results_host.setStyleSheet("QWidget { background: #161616; }")
        self._results_lay = QVBoxLayout(self._results_host)
        self._results_lay.setContentsMargins(0, 0, 0, 0)
        self._results_lay.setSpacing(0)
        self._results_lay.addStretch(1)
        self._scroll.setWidget(self._results_host)
        root.addWidget(self._scroll, 1)

        # ---- Footer ----
        footer = QFrame()
        footer.setFixedHeight(28)
        footer.setStyleSheet("QFrame { background: #111; border-top: 1px solid #2a2a2a; }")
        footer_lay = QHBoxLayout(footer)
        footer_lay.setContentsMargins(12, 0, 12, 0)
        lbl_esc = QLabel("ESC to close  ·  ↑↓ to navigate  ·  Enter to open  ·  comma = AND within field")
        lbl_esc.setStyleSheet("color: #444; font-size: 10px;")
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

        self.setFixedHeight(160)

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
        self.setFixedHeight(min(700, 100 + 28 + len(results) * 48 + 28))

    def _show_hint(self, text: str):
        """Zeigt einen Hinweistext (z.B. "Keine Ergebnisse") statt der Ergebnisliste."""
        self._scroll.hide()
        self._lbl_hint.setText(text)
        self._lbl_hint.show()
        self.setFixedHeight(160)

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