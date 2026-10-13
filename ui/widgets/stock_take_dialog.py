# ui/widgets/stock_take_dialog.py
"""Inventur (Stock take) fuer Yarn Stock - Nutzerwunsch 2026-10-13.

Geoeffnet aus Yarn Stock -> Rack lookup -> "Start stock take…" (Zugriff ab
Level 2). Ablauf: Regal/Platz waehlen -> TrippleT listet die Spulen, die
laut System dort stehen -> Spulen scannen/tippen -> Abweichungen direkt
korrigieren -> beim Abschluss fehlende Spulen ausbuchen oder behalten.

Was wann gespeichert wird (bewusst so, siehe Hilfe-Tab "Stock take"):
- Umlagern ("woanders registriert") und Wieder-Einlagern (ausgebuchte Spule
  gefunden) werden SOFORT nach Rueckfrage gespeichert.
- Fehlende Spulen werden NUR beim Abschluss und nur auf ausdruecklichen
  Klick ausgebucht. Abbrechen bucht nichts aus.
Jede Korrektur landet im Spulen-Protokoll (db/yarn_spool_log.py).

UI-Texte englisch (Projektkonvention); die ausfuehrliche Anleitung steht
dreisprachig in der Yarn-Stock-Hilfe (Tab "Stock take", Button "?" oben rechts).
"""
from datetime import date
from typing import Dict, List, Optional, Set

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QMessageBox,
    QInputDialog, QHeaderView,
)

from db.connection import execute
from db import yarn_spool_log
from db.usage_log import log_usage_event

_FOUND_BG = QColor("#EAF3DE")
_FEEDBACK_STYLE = {
    "ok": "background:#EAF3DE; color:#2b5d22; border:1px solid #9ccc8a;",
    "warn": "background:#FAEEDA; color:#7a4d00; border:1px solid #e3b866;",
    "error": "background:#FCEBEB; color:#8a1f1f; border:1px solid #e09a9a;",
    "info": "background:#f2f2f2; color:#444; border:1px solid #d0d0d0;",
}


class StockTakeDialog(QDialog):
    """Inventur eines Regals/Platzes: Soll (laut System) gegen Ist (gescannt)."""

    SPOOL_TABLE = "tblYarnSpool"

    def __init__(self, all_spools: List[Dict], yarn_names: Dict[int, str],
                 location_prefix: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Stock take")
        self.setMinimumSize(900, 680)
        self._spools: Dict[int, Dict] = {int(s["ID"]): dict(s) for s in all_spools if s.get("ID") is not None}
        self._yarn_names = yarn_names
        self._prefix = ""
        self._expected: List[int] = []
        self._found: Set[int] = set()
        self._others: List[Dict] = []          # Scans, die nicht erwartet waren
        self._finished = False
        self.changed = False                   # True, sobald etwas in der DB geaendert wurde

        root = QVBoxLayout(self)
        root.setSpacing(10)

        # ── Regal/Platz ──
        top = QHBoxLayout()
        top.addWidget(QLabel("Location (rack or slot):"))
        self.txt_location = QLineEdit(location_prefix.strip())
        self.txt_location.setPlaceholderText("e.g. E or E12")
        self.txt_location.setFixedWidth(120)
        self.txt_location.returnPressed.connect(self._on_load)
        top.addWidget(self.txt_location)
        btn_load = QPushButton("Load", objectName="GreyBtn")
        btn_load.clicked.connect(self._on_load)
        top.addWidget(btn_load)
        top.addStretch(1)
        btn_help = QPushButton("?")
        btn_help.setFixedSize(26, 26)
        btn_help.setCursor(Qt.PointingHandCursor)
        btn_help.setToolTip("How does the stock take work?")
        btn_help.setStyleSheet(
            "QPushButton{background:transparent;color:#39a650;border:1px solid #39a650;"
            "border-radius:13px;padding:0;font-size:14px;font-weight:700;}"
            "QPushButton:hover{background:#e8f5e9;}")
        btn_help.clicked.connect(self._open_help)
        top.addWidget(btn_help)
        root.addLayout(top)

        self.lbl_expected = QLabel("Enter a rack (e.g. E) or a slot (e.g. E12) and click Load.")
        self.lbl_expected.setWordWrap(True)
        root.addWidget(self.lbl_expected)

        # ── Scan-Feld ──
        scan_row = QHBoxLayout()
        lbl_scan = QLabel("Scan or type spool #:")
        lbl_scan.setStyleSheet("font-size:15px; font-weight:600;")
        scan_row.addWidget(lbl_scan)
        self.txt_scan = QLineEdit()
        self.txt_scan.setPlaceholderText("Scan the label or type the number, then press Enter")
        f = QFont(self.txt_scan.font()); f.setPointSize(14)
        self.txt_scan.setFont(f)
        self.txt_scan.setMinimumHeight(38)
        self.txt_scan.returnPressed.connect(self._on_scan)
        scan_row.addWidget(self.txt_scan, 1)
        root.addLayout(scan_row)

        self.lbl_feedback = QLabel(" ")
        self.lbl_feedback.setWordWrap(True)
        self.lbl_feedback.setMinimumHeight(36)
        self._set_feedback("info", "Load a location to start.")
        root.addWidget(self.lbl_feedback)

        self.lbl_progress = QLabel("")
        self.lbl_progress.setStyleSheet("font-size:14px; font-weight:600;")
        root.addWidget(self.lbl_progress)

        # ── Erwartete Spulen ──
        root.addWidget(QLabel("<b>Expected at this location</b> (according to TrippleT)"))
        self.tbl_expected = self._make_table(["Found", "Spool", "Yarn", "Batch", "Location", "Weight (kg)"])
        root.addWidget(self.tbl_expected, 3)

        # ── Andere Scans ──
        root.addWidget(QLabel("<b>Other scans</b> (not expected here)"))
        self.tbl_others = self._make_table(["Spool", "Yarn", "Batch", "Registered at", "Result"])
        root.addWidget(self.tbl_others, 1)

        # ── Buttons ──
        btns = QHBoxLayout()
        btns.addStretch(1)
        self.btn_finish = QPushButton("Finish stock take…", objectName="GreenBtn")
        self.btn_finish.clicked.connect(self._on_finish)
        self.btn_finish.setEnabled(False)
        btns.addWidget(self.btn_finish)
        btn_cancel = QPushButton("Cancel", objectName="GreyBtn")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)
        root.addLayout(btns)

        if self.txt_location.text().strip():
            self._on_load()
        else:
            self.txt_location.setFocus()

    # ── Helfer ───────────────────────────────────────────────────────
    @staticmethod
    def _make_table(headers: List[str]) -> QTableWidget:
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionMode(QAbstractItemView.NoSelection)
        t.setFocusPolicy(Qt.NoFocus)  # Fokus bleibt im Scan-Feld
        t.horizontalHeader().setStretchLastSection(True)
        return t

    def _set_feedback(self, kind: str, text: str) -> None:
        self.lbl_feedback.setText(text)
        self.lbl_feedback.setStyleSheet(
            _FEEDBACK_STYLE[kind] + "font-size:14px; padding:6px 10px; border-radius:6px;")

    def _describe_spool(self, s: Dict) -> str:
        yarn = self._yarn_names.get(int(s.get("YarnID") or -1), "?")
        return f"{yarn} / batch {s.get('Charge') or '–'}"

    def _update_progress(self) -> None:
        n = len(self._expected)
        self.lbl_progress.setText(f"Found {len(self._found)} of {n} expected spool(s)"
                                  + (f" · {len(self._others)} other scan(s)" if self._others else ""))

    def _open_help(self) -> None:
        from ui.widgets.yarn_stock_help_dialog import show_yarn_stock_help
        show_yarn_stock_help(self, tab="stocktake")
        self.txt_scan.setFocus()

    def _has_progress(self) -> bool:
        return bool(self._found or self._others)

    # ── Laden ────────────────────────────────────────────────────────
    def _on_load(self) -> None:
        prefix = self.txt_location.text().strip().upper()
        if not prefix:
            self._set_feedback("warn", "Enter a rack (e.g. E) or a slot (e.g. E12) first.")
            return
        if self._has_progress() and prefix != self._prefix:
            resp = QMessageBox.question(
                self, "Stock take",
                f"Start over with location '{prefix}'? The scans for '{self._prefix}' are discarded "
                "(corrections already saved stay saved).",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if resp != QMessageBox.Yes:
                self.txt_location.setText(self._prefix)
                return
        self._prefix = prefix
        self._expected = sorted(
            sid for sid, s in self._spools.items()
            if s.get("Status") == "in stock" and (s.get("Location") or "").strip().upper().startswith(prefix))
        self._found, self._others = set(), []
        self._render_expected()
        self._render_others()
        self.lbl_expected.setText(
            f"<b>{len(self._expected)}</b> spool(s) are registered at locations starting with "
            f"<b>{prefix}</b>. Scan every spool you find there.")
        self._set_feedback("info", "Ready - scan the first spool.")
        self.btn_finish.setEnabled(True)
        self._update_progress()
        self.txt_scan.setFocus()

    def _render_expected(self) -> None:
        t = self.tbl_expected
        t.setRowCount(len(self._expected))
        for r, sid in enumerate(self._expected):
            s = self._spools[sid]
            found = sid in self._found
            w = s.get("WeightKg")
            vals = ["yes" if found else "", f"#{sid}", self._yarn_names.get(int(s.get("YarnID") or -1), "?"),
                    s.get("Charge") or "–", s.get("Location") or "–",
                    f"{float(w):.2f}" if w is not None else ""]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if found:
                    it.setBackground(_FOUND_BG)
                if c in (0, 5):
                    it.setTextAlignment(Qt.AlignCenter if c == 0 else Qt.AlignRight | Qt.AlignVCenter)
                t.setItem(r, c, it)
        t.resizeColumnsToContents()
        t.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

    def _render_others(self) -> None:
        t = self.tbl_others
        t.setRowCount(len(self._others))
        for r, o in enumerate(self._others):
            for c, v in enumerate([o["Spool"], o["Yarn"], o["Batch"], o["Registered"], o["Result"]]):
                t.setItem(r, c, QTableWidgetItem(v))
        t.resizeColumnsToContents()

    def _add_other(self, sid: int, s: Optional[Dict], registered: str, result: str) -> None:
        self._others.append({
            "ID": sid, "Spool": f"#{sid}",
            "Yarn": self._yarn_names.get(int(s.get("YarnID") or -1), "?") if s else "–",
            "Batch": (s.get("Charge") or "–") if s else "–",
            "Registered": registered, "Result": result,
        })
        self._render_others()

    # ── Scannen ──────────────────────────────────────────────────────
    def _on_scan(self) -> None:
        from ui.screen_yarn_stock import parse_spool_input  # lazy: Zirkelimport vermeiden
        raw = self.txt_scan.text()
        self.txt_scan.clear()
        if not raw.strip():
            return
        if not self._prefix:
            self._set_feedback("warn", "Load a location first.")
            return
        sid = parse_spool_input(raw)
        if sid is None:
            self._set_feedback("error", f"'{raw.strip()[:40]}' is not a spool number or spool label.")
            return
        if sid in self._found or any(o["ID"] == sid for o in self._others):
            self._set_feedback("warn", f"Spool #{sid} was already scanned.")
            return

        s = self._spools.get(sid)
        if sid in self._expected:
            self._found.add(sid)
            self._render_expected()
            self._set_feedback("ok", f"Found #{sid} - {self._describe_spool(s)}, {s.get('Location') or '–'}")
        elif s is None:
            self._add_other(sid, None, "–", "Unknown spool number - nothing changed")
            self._set_feedback("error", f"Spool #{sid} does not exist in TrippleT. Check the label.")
        elif s.get("Status") != "in stock":
            self._handle_discarded_found(sid, s)
        else:
            self._handle_wrong_location(sid, s)
        self._update_progress()
        self.txt_scan.setFocus()

    def _ask_location(self, text: str) -> Optional[str]:
        loc, ok = QInputDialog.getText(self, "Stock take", text, QLineEdit.Normal, self._prefix)
        loc = (loc or "").strip().upper()
        return loc if ok and loc else None

    def _handle_wrong_location(self, sid: int, s: Dict) -> None:
        old = s.get("Location") or "–"
        new = self._ask_location(
            f"Spool #{sid} ({self._describe_spool(s)}) is registered at {old}, but was found here.\n\n"
            "Enter the location where it actually is to move it,\nor click Cancel to leave it unchanged:")
        if new is None or new == (s.get("Location") or "").upper():
            self._add_other(sid, s, old, "Registered elsewhere - not changed")
            self._set_feedback("warn", f"#{sid} is registered at {old} - left unchanged.")
            return
        try:
            execute(f"UPDATE {self.SPOOL_TABLE} SET [Location] = ? WHERE [ID] = ?", [new, sid])
        except Exception as e:
            QMessageBox.critical(self, "Stock take", f"Failed to move spool #{sid}: {e}")
            return
        yarn_spool_log.log_spool_changes([{"SpoolID": sid, "Action": yarn_spool_log.UPDATED,
                                           "Field": "Location", "Old": s.get("Location"),
                                           "New": f"{new} (stock take)"}])
        s["Location"] = new
        self.changed = True
        self._add_other(sid, s, old, f"Moved to {new}")
        self._set_feedback("ok", f"#{sid} moved from {old} to {new}.")

    def _handle_discarded_found(self, sid: int, s: Dict) -> None:
        new = self._ask_location(
            f"Spool #{sid} ({self._describe_spool(s)}) is marked as DISCARDED, but was found here.\n\n"
            "To put it back in stock, enter its location.\nClick Cancel to leave it discarded:")
        if new is None:
            self._add_other(sid, s, "discarded", "Discarded - not changed")
            self._set_feedback("warn", f"#{sid} is discarded - left unchanged.")
            return
        try:
            execute(f"UPDATE {self.SPOOL_TABLE} SET [Status] = 'in stock', [DiscardedDate] = NULL, "
                    f"[Location] = ? WHERE [ID] = ?", [new, sid])
        except Exception as e:
            QMessageBox.critical(self, "Stock take", f"Failed to put spool #{sid} back in stock: {e}")
            return
        yarn_spool_log.log_spool_changes([
            {"SpoolID": sid, "Action": yarn_spool_log.UPDATED, "Field": "Status",
             "Old": "discarded", "New": "in stock (stock take)"},
            {"SpoolID": sid, "Action": yarn_spool_log.UPDATED, "Field": "Location",
             "Old": s.get("Location"), "New": f"{new} (stock take)"},
        ])
        s["Status"], s["Location"] = "in stock", new
        self.changed = True
        self._add_other(sid, s, "discarded", f"Put back in stock at {new}")
        self._set_feedback("ok", f"#{sid} is back in stock at {new}. Check its weight in the spool list.")

    # ── Abschluss ────────────────────────────────────────────────────
    def missing_ids(self) -> List[int]:
        return [sid for sid in self._expected if sid not in self._found]

    def _on_finish(self) -> None:
        missing = self.missing_ids()
        moved = sum(1 for o in self._others if o["Result"].startswith("Moved"))
        back = sum(1 for o in self._others if o["Result"].startswith("Put back"))
        lines = [f"Location {self._prefix}: found {len(self._found)} of {len(self._expected)} expected spool(s)."]
        if moved or back:
            lines.append(f"Corrections already saved: {moved} moved, {back} put back in stock.")
        box = QMessageBox(self)
        box.setWindowTitle("Finish stock take")
        box.setIcon(QMessageBox.Question if missing else QMessageBox.Information)
        if missing:
            shown = ", ".join(f"#{i}" for i in missing[:15]) + (" …" if len(missing) > 15 else "")
            lines.append(f"\nMissing ({len(missing)}): {shown}")
            lines.append("\nWhat should happen with the missing spools?")
            btn_discard = box.addButton("Discard missing spools", QMessageBox.DestructiveRole)
            btn_keep = box.addButton("Keep them (no change)", QMessageBox.AcceptRole)
        else:
            lines.append("\nAll expected spools were found.")
            btn_discard = None
            btn_keep = box.addButton("Close", QMessageBox.AcceptRole)
        btn_back = box.addButton("Back to scanning", QMessageBox.RejectRole)
        box.setText("\n".join(lines))
        box.exec()
        clicked = box.clickedButton()
        if clicked is btn_back or clicked is None:
            self.txt_scan.setFocus()
            return
        discarded = 0
        if btn_discard is not None and clicked is btn_discard:
            discarded = self._discard(missing)
            if discarded is None:
                return
        log_usage_event("feature", "yarn_stock_stock_take",
                        f"{self._prefix}: {len(self._found)}/{len(self._expected)} found, "
                        f"{moved} moved, {back} back, {discarded} discarded")
        self._finished = True
        self.accept()

    def _discard(self, ids: List[int]) -> Optional[int]:
        today = date.today().isoformat()
        n = 0
        try:
            for sid in ids:
                n += execute(f"UPDATE {self.SPOOL_TABLE} SET [Status] = 'discarded', [DiscardedDate] = ? "
                             f"WHERE [ID] = ?", [today, sid]) or 0
        except Exception as e:
            QMessageBox.critical(self, "Stock take", f"Failed to discard: {e}")
            return None
        yarn_spool_log.log_spool_changes(
            {"SpoolID": sid, "Action": yarn_spool_log.DISCARDED, "Field": "Status",
             "Old": "in stock", "New": "discarded (stock take)"} for sid in ids)
        self.changed = True
        return n

    def reject(self) -> None:
        if self._has_progress() and not self._finished:
            resp = QMessageBox.question(
                self, "Leave stock take",
                "Leave the stock take without finishing?\n\nMoves and put-backs you confirmed are "
                "already saved. Missing spools are NOT discarded.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if resp != QMessageBox.Yes:
                self.txt_scan.setFocus()
                return
        super().reject()
