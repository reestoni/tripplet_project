"""Statimat/Itemat PDF-Import fuer ShowExperimentScreen.

Ausgelagert aus ui/screen_show_experiment.py (reiner Code-Move). Seit
2026-11-13 liegt das eigentliche Parsen + Schreiben Qt-frei in
db/lab_pdf_import.py (gemeinsam mit der Web-App); hier bleiben nur die
PDF-Auswahl, die Fortschrittsdialoge, das Neuaufbauen der Reiter und die
Ergebnismeldung. Beide *_impl-Funktionen erwarten die
ShowExperimentScreen-Instanz als `self`-Argument.
"""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMessageBox,
    QDialog,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QAbstractItemView,
    QDialogButtonBox,
    QProgressDialog,
)

import app_meta
from db import lab_pdf_import
from ui.widgets.statimat_pdf_parser import parse_statimat_pdf  # noqa: F401  (kept importable from here)
from ui.widgets.itemat_pdf_parser import DB_TENSIONS as ITEMAT_DB_TENSIONS  # noqa: F401
from ui.widgets.friendly_error import show_error


def _pick_attached_pdfs(self, attached_rows, title: str, text: str):
    """User picks one/many PDFs from the *attached* list (shows
    OriginalFilename, not StoredFilename). Returns the chosen FullPaths."""
    dlg = QDialog(self)
    dlg.setWindowTitle(title)
    lay = QVBoxLayout(dlg)

    info = QLabel(text)
    info.setWordWrap(True)
    lay.addWidget(info)

    lst = QListWidget()
    lst.setSelectionMode(QAbstractItemView.MultiSelection)

    # Keep stable index -> row mapping
    for r in attached_rows:
        disp = (r.get("OriginalFilename") or "").strip()
        if not disp:
            disp = (r.get("StoredFilename") or "").strip()
        if not disp:
            disp = os.path.basename(r.get("FullPath") or "")
        lst.addItem(disp)

    lay.addWidget(lst)

    bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    bb.accepted.connect(dlg.accept)
    bb.rejected.connect(dlg.reject)
    lay.addWidget(bb)

    if dlg.exec() != QDialog.Accepted:
        return []

    chosen_paths = []
    for ix in lst.selectionModel().selectedIndexes():
        row = ix.row()
        if 0 <= row < len(attached_rows):
            p = attached_rows[row].get("FullPath") or ""
            if p:
                chosen_paths.append(p)
    return chosen_paths


def statimat_import_impl(self) -> None:
    """Import STATIMAT PDF(s) attached to this TrialSeries into lab tables.

    Rules and mapping: db/lab_pdf_import.py (Qt-free, shared with the web app).
    Only PDFs attached to the current TrialSeries may be imported.
    """
    sid = getattr(self, "_series_pk", None)
    if sid in (None, ""):
        QMessageBox.information(self, "Statimat import", "No trial series loaded.")
        return

    # Build allow-list from attached PDFs
    try:
        attached = self._fetch_series_pdfs(sid)
    except Exception as e:
        show_error(self, "Statimat import", "The list of PDFs could not be loaded.", e, warning=True)
        return

    allowed = set()
    for r in attached:
        p = r.get("FullPath") or ""
        if p:
            allowed.add(os.path.normcase(os.path.abspath(p)))

    if not allowed:
        QMessageBox.information(self, "Statimat import", "This trial series has no attached PDFs.")
        return

    chosen = _pick_attached_pdfs(
        self, attached, "Select STATIMAT PDFs",
        "Select the STATIMAT PDFs to import (only PDFs attached to this trial series):")
    if not chosen:
        return

    progs = {}

    def _start(pdf_idx: int, pdf_path: str) -> bool:
        prog = QProgressDialog(
            f"Lese {os.path.basename(pdf_path)}…", "Cancel",
            0, len(chosen), self
        )
        prog.setWindowTitle("Statimat import")
        prog.setWindowModality(Qt.WindowModal)
        prog.setMinimumDuration(0)
        prog.setValue(pdf_idx)
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
        progs[pdf_idx] = prog
        return not prog.wasCanceled()

    def _end(pdf_idx: int) -> None:
        prog = progs.pop(pdf_idx, None)
        if prog is not None:
            prog.setValue(pdf_idx + 1)
            prog.close()

    res = lab_pdf_import.import_statimat(sid, chosen, app_meta.current_user,
                                         on_pdf_start=_start, on_pdf_end=_end)

    # refresh views/tabs
    try:
        self._build_titer_tab()
        self._build_statimat_tab()
        self._build_statimat_ds_tab()
    except Exception:
        pass

    QMessageBox.information(self, "Statimat import", lab_pdf_import.import_message(
        "Import finished.", "Imported spools", res["imported"], res["skipped"], res["errors"]))


def itemat_import_impl(self) -> None:
    """Import Itemat Lab PDF(s) attached to this TrialSeries into tblLaborItematLab.

    Mapping: db/lab_pdf_import.py (Qt-free, shared with the web app).
    """
    from ui.screen_show_experiment import table_exists

    sid = getattr(self, "_series_pk", None)
    if sid in (None, ""):
        QMessageBox.information(self, "Itemat import", "No trial series loaded.")
        return

    # Ziel-Tabelle prüfen
    itemat_table = lab_pdf_import.ITEMAT_TABLE
    if not table_exists(itemat_table):
        QMessageBox.warning(self, "Itemat import",
                            f"Tabelle '{itemat_table}' not found.")
        return

    # Angehängte PDFs laden
    try:
        attached = self._fetch_series_pdfs(sid)
    except Exception as e:
        show_error(self, "Itemat import", "The list of PDFs could not be loaded.", e, warning=True)
        return

    if not attached:
        QMessageBox.information(self, "Itemat import",
                                "This trial series has no attached PDFs.")
        return

    chosen = _pick_attached_pdfs(
        self, attached, "Select Itemat Lab PDFs",
        "Select the Itemat Lab PDFs to import\n"
        "(only PDFs attached to this trial series):")
    if not chosen:
        return

    # Spalten einmal auflösen
    cols = lab_pdf_import.itemat_columns()
    if cols is None:
        raw = lab_pdf_import.itemat_columns_raw()
        QMessageBox.warning(
            self, "Itemat import",
            f"Could not resolve required columns.\n"
            f"Tension={raw['tension']}, FPm={raw['fpm']}, Stability={raw['stability']}"
        )
        return

    def _progress_for(pdf_path):
        # Progress-Dialog
        prog = QProgressDialog(
            f"Lese {os.path.basename(pdf_path)}…", "Cancel", 0, 100, self
        )
        prog.setWindowTitle("Itemat import")
        prog.setWindowModality(Qt.WindowModal)
        prog.setMinimumDuration(0)
        prog.setValue(0)

        def _progress(cur, total, _prog=prog):
            if _prog.wasCanceled():
                raise InterruptedError("Abgebrochen")
            _prog.setValue(int(cur / total * 100))
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()

        def _done(_prog=prog):
            _prog.setValue(100)
            _prog.close()

        return _progress, _done

    res = lab_pdf_import.import_itemat(sid, chosen, app_meta.current_user, cols=cols,
                                       progress_for=_progress_for)

    # Tabs auffrischen
    try:
        self._build_itemat_tab()
        self._build_itemat_plus_tab()
    except Exception:
        pass

    QMessageBox.information(self, "Itemat import", lab_pdf_import.import_message(
        "Itemat import finished.", "Imported trials", res["imported"], res["skipped"], res["errors"]))
