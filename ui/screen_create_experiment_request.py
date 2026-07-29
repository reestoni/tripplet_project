from __future__ import annotations
# ui/screen_create_experiment_request.py
"""Screen zur Erstellung und Bearbeitung von Experiment-Requests.

Ermöglicht das Anlegen und Bearbeiten von Experiment-Requests in tblExperimentRequests.
Das Formular wird dynamisch aus den DB-Spalten generiert.

Hauptklassen:
  - ExperimentRequestImagesDialog: Bild-Verwaltungs-Dialog (Upload, Rotation, Umbenennen, Löschen)
  - ExperimentRequestPdfsDialog:   PDF-Verwaltungs-Dialog (analog zu Images)
  - CreateExperimentRequestScreen: Hauptformular-Screen

Besonderheiten:
  - Alle Felder werden dynamisch aus tblExperimentRequests-Spalten generiert
  - FK-Felder werden als Combobox mit lesbaren Namen dargestellt
  - Bild-/PDF-Upload mit Vorschau, Rotation und Batch-Umbenennung
  - Draft-Mechanismus: Request wird als Draft gespeichert bis er abgesendet wird
  - Bei erneutem Öffnen (request_id) wird der bestehende Request geladen
"""

# ui/screen_create_experiment_request.py

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import os
import uuid
import re

from PySide6.QtCore import Qt, QDate, QDateTime, QSize, QPoint, QEvent, QTimer
from PySide6.QtGui import QFontMetrics, QPixmap, QIcon, QImage, QTransform
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFrame,
    QLabel,
    QPushButton,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QScrollArea,
    QMessageBox,
    QDateEdit,
    QFileDialog,
    QDialog,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QDialogButtonBox,
    QMenu,
    QInputDialog,
)

import app_meta
from db.connection import get_connection, new_global_id, current_db_name, is_dev_mode
from ui.pathutil import resource_path
from ui.widgets.header import HeaderBar
from ui.widgets.footer import FooterBar

import datetime
import shutil


# Felder, die im Formular nicht angezeigt werden sollen
# (werden teils automatisch beim Speichern gesetzt)
EXCLUDE_FIELDS = {"ID", "Timestamp", "CreatedBy", "RequestStatus"}

# Basisordner fuer Experiment-Request-Bilder
# - PROD: Netzlaufwerk (gemeinsame Ablage)
# - DEV:  lokaler Testordner
REQUEST_IMAGES_BASE_DIR = (
    r"C:\ttt\images\ExperimentRequestImages" if is_dev_mode() else r"H:\Technik\TrippleT\ExperimentRequestImages"
)

# Mehrzeilige Felder (3 Zeilen)
MULTILINE_FIELDS = {
    "Versuchsgrund",
    "Aufgabe",
    "Versuchsumfang",
    "Beurteilungsparameter",
    "Versuchsbedingungen",
    "Versuchsort",
    "Bemerkungen",
}

DATE_FIELDS = {"Wunschtermin"}

# Pflichtfelder (Save nur aktiv, wenn diese gefüllt sind)
# (Im DB-Schema kann der Feldname entweder "Versuchsgrund" oder "FVersuchsgrund" sein.)
REQUIRED_FIELDS = [
    "Titel",
    "FVersuchsgrund",
    "Versuchsgrund",
    "Aufgabe",
    "Beurteilungsparameter",
    "Versuchsbedingungen",
]


@dataclass
class ColumnInfo:
    """Metadaten einer DB-Spalte (Name, Typ, Nullable, FK-Info) für das dynamische Formular."""
    name: str
    data_type: Optional[int] = None
    type_name: Optional[str] = None



class ExperimentRequestImagesDialog(QDialog):
    """Dialog zur Verwaltung von Bildern eines Experiment-Requests.

    Funktionen: Bilder hochladen, Vorschau, Rotation (90°), Umbenennen,
    Batch-Umbenennung, Löschen, «Save as»-Export.
    Speichert Bilder in tblTrialSeriesImage (oder direkt im Dateisystem).
    """
    """Simple viewer for stored images.

    In the viewer popups, you can right-click an item in the list on the left
    (the OriginalFilename) to rename it. The file extension (e.g. .jpg) is
    preserved and cannot be changed.

    If `table_name`/`fk_field`/`fk_value` are provided, the rename is persisted
    directly into the DB.
    """

    @staticmethod
    def _natural_sort_key(s: str) -> List[object]:
        """Key for natural sorting (e.g. V2 before V17)."""
        parts = re.split(r"(\d+)", s or "")
        out: List[object] = []
        for part in parts:
            if part.isdigit():
                out.append(int(part))
            else:
                out.append(part.lower())
        return out

    def __init__(
        self,
        parent: QWidget,
        title: str,
        images: List[Dict[str, str]],
        *,
        table_name: str | None = None,
        fk_field: str | None = None,
        fk_value: Any | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        # Bigger by default (so images are actually useful), but still resizable.
        # Also enable the maximize button for convenience.
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        self.setMinimumSize(920, 620)
        self.resize(1200, 820)

        self._images = list(images or [])
        # Always show images sorted by OriginalFilename (natural sort, e.g. V2 before V17)
        self._images.sort(
            key=lambda d: self._natural_sort_key(
                str(
                    d.get("OriginalFilename")
                    or d.get("StoredFilename")
                    or d.get("StoredFile")
                    or ""
                )
            )
        )
        self._table_name = table_name
        self._fk_field = fk_field
        self._fk_value = fk_value

        # Zoom state (image preview)
        self._zoom: float = 1.0
        self._pm_original: QPixmap | None = None
        self._did_initial_show: bool = False

        # Pan state (drag-to-move inside the scroll area)
        self._panning: bool = False
        self._pan_start_pos: QPoint | None = None  # viewport coords
        self._pan_start_h: int = 0
        self._pan_start_v: int = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal, self)

        # Left: file list + batch rename button (stacked)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.lst = QListWidget()
        self.lst.setMinimumWidth(260)
        self.lst.setSelectionMode(QListWidget.ExtendedSelection)
        left_layout.addWidget(self.lst, 1)

        self.btn_batch_rename = QPushButton("Batch rename…")
        self.btn_batch_rename.setEnabled(bool(self._table_name and self._fk_field and self._fk_value not in (None, "")))
        self.btn_batch_rename.clicked.connect(self._open_batch_rename)
        left_layout.addWidget(self.btn_batch_rename, 0)
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._delete_selected)
        left_layout.addWidget(self.btn_delete, 0)


        splitter.addWidget(left)

        # Right-click to rename OriginalFilename (left list)
        self.lst.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lst.customContextMenuRequested.connect(self._on_list_context_menu)

        # Right: preview
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self.lbl_name = QLabel("")
        self.lbl_name.setTextFormat(Qt.PlainText)
        self.lbl_name.setWordWrap(True)
        self.lbl_name.setStyleSheet("font-weight: 600;")
        right_layout.addWidget(self.lbl_name, 0)

        # Image preview (scrollable + zoomable)
        self.scroll_preview = QScrollArea()
        self.scroll_preview.setWidgetResizable(False)
        self.scroll_preview.setStyleSheet("border: 1px solid #444; border-radius: 6px;")
        self.lbl_preview = QLabel("Select an image…")
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setStyleSheet("background: transparent; padding: 8px;")
        self.scroll_preview.setWidget(self.lbl_preview)
        # Mouse wheel zoom (over preview)
        self.scroll_preview.viewport().installEventFilter(self)
        right_layout.addWidget(self.scroll_preview, 1)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)

        # Bottom buttons: rotate left / right + close
        bottom = QHBoxLayout()

        # Zoom buttons
        self.btn_zoom_out = QPushButton()
        self.btn_zoom_out.setIcon(QIcon(resource_path(r"assets/images/zoom_out.png")))
        self.btn_zoom_out.setToolTip("Zoom out")
        self.btn_zoom_out.clicked.connect(lambda: self._zoom_relative(1/1.25))

        self.btn_zoom_in = QPushButton()
        self.btn_zoom_in.setIcon(QIcon(resource_path(r"assets/images/zoom_in.png")))
        self.btn_zoom_in.setToolTip("Zoom in")
        self.btn_zoom_in.clicked.connect(lambda: self._zoom_relative(1.25))

        self.btn_rotate_left = QPushButton()
        self.btn_rotate_left.setIcon(QIcon(resource_path("assets/images/rotate_left.png")))
        self.btn_rotate_left.setToolTip("Rotate image 90° left")
        self.btn_rotate_left.clicked.connect(lambda: self._rotate_current(-90))

        self.btn_rotate_right = QPushButton()
        self.btn_rotate_right.setIcon(QIcon(resource_path("assets/images/rotate_right.png")))
        self.btn_rotate_right.setToolTip("Rotate image 90° right")
        self.btn_rotate_right.clicked.connect(lambda: self._rotate_current(90))

        # Center the rotate buttons horizontally (in the area left of "Close")
        bottom.addStretch(1)
        bottom.addWidget(self.btn_zoom_out)
        bottom.addWidget(self.btn_zoom_in)
        bottom.addWidget(self.btn_rotate_left)
        bottom.addWidget(self.btn_rotate_right)
        bottom.addStretch(1)

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        bottom.addWidget(btns)

        layout.addLayout(bottom, 0)

        # Fill list (sorted)
        self._fill_list()

        self.lst.currentItemChanged.connect(self._on_select)
        self.lst.itemSelectionChanged.connect(self._update_delete_button)

        if self.lst.count() > 0:
            self.lst.setCurrentRow(0)

    @staticmethod
    def _display_name(filename: str) -> str:
        """Gibt den Anzeigenamen einer Datei zurück (Dateiname ohne Pfad)."""
        """Returns a user-facing filename without extension."""
        filename = str(filename or "")
        if not filename:
            return ""
        return os.path.splitext(filename)[0]


    def _rotate_current(self, angle: int) -> None:
        """Rotiert das aktuell ausgewählte Bild um angle Grad und speichert es."""
        """Rotate the currently selected image by `angle` degrees and overwrite the file."""
        item = self.lst.currentItem()
        if not item:
            return

        img = item.data(Qt.UserRole) or {}
        path = img.get("FullPath")
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Rotate image", "Image file not found.")
            return

        image = QImage(path)
        if image.isNull():
            QMessageBox.warning(self, "Rotate image", "Failed to load image.")
            return

        rotated = image.transformed(QTransform().rotate(angle))

        if not rotated.save(path):
            QMessageBox.warning(self, "Rotate image", "Failed to save rotated image.")
            return

        # Refresh preview and keep selection
        self._on_select(item, None)


    def _fill_list(self, *, select_full_path: str | None = None) -> None:
        """Befüllt die Dateiliste aus der DB und selektiert optional eine bestimmte Datei."""
        """(Re)build the left list, sorted by OriginalFilename (natural sort)."""
        # Keep the model list sorted
        self._images.sort(key=lambda d: self._natural_sort_key(str(d.get("OriginalFilename") or d.get("StoredFilename") or d.get("StoredFile") or "")))

        self.lst.blockSignals(True)
        try:
            self.lst.clear()

            selected_item = None
            for img in self._images:
                raw = img.get("OriginalFilename") or img.get("StoredFilename") or "(unnamed)"
                disp = self._display_name(raw) if raw != "(unnamed)" else raw
                item = QListWidgetItem(disp)
                item.setData(Qt.UserRole, img)
                self.lst.addItem(item)

                if select_full_path and str(img.get("FullPath") or "") == str(select_full_path):
                    selected_item = item
        finally:
            self.lst.blockSignals(False)

        # Restore selection (and trigger preview) if possible
        if selected_item is not None:
            self.lst.setCurrentItem(selected_item)
            self._on_select(selected_item, None)
        elif self.lst.count() > 0 and self.lst.currentItem() is None:
            # Optional: keep behaviour consistent (select first item)
            self.lst.setCurrentRow(0)
            self._on_select(self.lst.currentItem(), None)

    # ---------------- Context menu: rename OriginalFilename ----------------

    def _update_delete_button(self) -> None:
        """Aktiviert/deaktiviert den Löschen-Button je nach Selektion."""
        """Enable/disable delete button based on selection."""
        try:
            btn = getattr(self, "btn_delete", None)
            if not btn:
                return
            btn.setEnabled(len(self.lst.selectedItems()) > 0)
        except Exception:
            # Never crash the viewer due to UI state.
            pass


    def _open_batch_rename(self) -> None:
        """Öffnet den Batch-Umbenennen-Dialog für alle Bilder."""
        can_persist = bool(self._table_name and self._fk_field and self._fk_value not in (None, ""))
        if not can_persist:
            QMessageBox.information(self, "Batch rename", "Batch rename is only available when the viewer is connected to the database.")
            return

        # Requirement: For batch rename jobs, process images ordered by
        # tblExperimentRequestImage.ID (ascending), not by OriginalFilename.
        # The viewer list stays sorted by OriginalFilename for usability.
        images_for_batch = list(self._images)
        if images_for_batch and any("ID" in d and d.get("ID") not in (None, "") for d in images_for_batch):
            def _id_key(d: Dict[str, str]) -> int:
                try:
                    return int(d.get("ID") or 0)
                except Exception:
                    return 0

            images_for_batch.sort(key=_id_key)

        dlg = BatchRenameDialog(
            self,
            images=images_for_batch,
            table_name=self._table_name,
            fk_field=self._fk_field,
            fk_value=self._fk_value,
            natural_key=self._natural_sort_key,
        )
        if dlg.exec() == QDialog.Accepted:
            self._fill_list()

    def _on_list_context_menu(self, pos: QPoint) -> None:
        """Zeigt ein Kontextmenü für die Dateiliste (Umbenennen, Exportieren)."""
        item = self.lst.itemAt(pos)
        if not item:
            return

        # Only enable renaming if we have enough info to persist.
        can_persist = bool(self._table_name and self._fk_field and self._fk_value not in (None, ""))

        menu = QMenu(self)
        act_rename = menu.addAction("Rename OriginalFilename…")
        act_rename.setEnabled(can_persist)
        act_save_as = menu.addAction("Save As…")

        chosen = menu.exec_(self.lst.mapToGlobal(pos))
        if chosen == act_rename:
            self._rename_original_filename(item)
        elif chosen == act_save_as:
            self._save_as_file(item)

    def _save_as_file(self, item: QListWidgetItem) -> None:
        """Exportiert die gewählte Datei an einen benutzerdefinierten Speicherort."""
        """Kopiert die gespeicherte Datei an einen vom Benutzer gewählten Ort."""
        d = item.data(Qt.UserRole) or {}
        src = str(d.get("FullPath") or "")
        if not src or not os.path.isfile(src):
            QMessageBox.warning(self, "Save As", "Datei nicht gefunden:\n" + src)
            return

        orig = str(d.get("OriginalFilename") or os.path.basename(src))
        dst, _ = QFileDialog.getSaveFileName(self, "Save As", orig)
        if not dst:
            return
        try:
            import shutil
            shutil.copy2(src, dst)
        except Exception as e:
            QMessageBox.critical(self, "Save As", f"Fehler beim Speichern:\n{e}")

    def keyPressEvent(self, event):  # noqa: N802
        """Delete-Taste löscht selektierte Dateien."""
        """Keyboard shortcuts.

        - Ctrl+R: rename currently selected image (same as context menu)
        """
        try:
            if event.key() == Qt.Key_R and (event.modifiers() & Qt.ControlModifier):
                item = self.lst.currentItem()
                can_persist = bool(self._table_name and self._fk_field and self._fk_value not in (None, ""))
                if item and can_persist:
                    self._rename_original_filename(item)
                    event.accept()
                    return

            if event.key() == Qt.Key_Delete:
                if self.lst.selectedItems():
                    self._delete_selected()
                    event.accept()
                    return
        except Exception:
            pass
        super().keyPressEvent(event)

    def _confirm_delete(self, n: int) -> bool:
        """Zeigt Bestätigungs-Dialog vor dem Löschen von n Dateien.

        Returns:
            True wenn bestätigt, False wenn abgebrochen.
        """
        title = "Confirm delete"
        if n == 1:
            text = "Delete the selected image?"
        else:
            text = f"Delete the {n} selected images?"

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle(title)
        box.setText(text)
        box.setInformativeText(
            "This will permanently delete the file(s) and remove the corresponding database entries."
        )
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        return box.exec() == QMessageBox.Yes

    def _delete_selected(self) -> None:
        """Löscht alle selektierten Dateien (DB-Eintrag + Datei auf Disk)."""
        items = list(self.lst.selectedItems() or [])
        if not items:
            return

        can_persist = bool(self._table_name and self._fk_field and self._fk_value not in (None, ""))
        if not can_persist:
            QMessageBox.warning(
                self,
                "Delete",
                "Delete is not available here because the database context is missing.",
            )
            return

        if not self._confirm_delete(len(items)):
            return

        deleted_dirs: set[str] = set()
        deleted_ok_full: set[str] = set()
        deleted_ok_full: set[str] = set()
        errors: List[str] = []

        # Delete in reverse row order so indices remain valid
        for item in sorted(items, key=lambda it: self.lst.row(it), reverse=True):
            img = item.data(Qt.UserRole) or {}
            rel_path = str(img.get("RelativePath") or "")
            stored = str(img.get("StoredFilename") or img.get("StoredFile") or "")
            full_path = str(img.get("FullPath") or (os.path.join(rel_path, stored) if rel_path else stored))

            if rel_path:
                deleted_dirs.add(os.path.normpath(rel_path))

            # 1) Delete file from disk
            try:
                if full_path and os.path.exists(full_path):
                    os.remove(full_path)
            except Exception as e:
                errors.append(f"Could not delete file:\n{full_path}\n\n{e}")

            # 2) Delete row from DB
            try:
                with get_connection() as cn:
                    cur = cn.cursor()
                    cur.execute(
                        f"DELETE FROM [{self._table_name}] WHERE [{self._fk_field}]=? AND [RelativePath]=? AND [StoredFilename]=?",
                        [self._fk_value, rel_path, stored],
                    )
                    try:
                        cn.commit()
                    except Exception:
                        pass
            except Exception as e:
                errors.append(f"Could not delete database entry for:\n{stored}\n\n{e}")

            # 3) Remove from in-memory list + UI
            try:
                self._images = [
                    d for d in self._images
                    if str(d.get("FullPath") or "") != str(full_path)
                ]
                self.lst.takeItem(self.lst.row(item))
            except Exception:
                pass

        # Re-sort + refresh list selection/preview
        try:
            self._images.sort(
                key=lambda d: self._natural_sort_key(
                    str(d.get("OriginalFilename") or d.get("StoredFilename") or d.get("StoredFile") or "")
                )
            )
            self._fill_list()
            if self.lst.count() > 0:
                self.lst.setCurrentRow(min(self.lst.currentRow(), self.lst.count() - 1))
            else:
                self.lbl_name.setText("")
                self.lbl_meta.setText("")
                self.lbl_img.setText("No images.")
                self._update_delete_button()
        except Exception:
            pass

        # If no images remain for this FK, delete the folder too
        try:
            remaining = 1
            with get_connection() as cn:
                cur = cn.cursor()
                cur.execute(
                    f"SELECT COUNT(*) FROM [{self._table_name}] WHERE [{self._fk_field}]=?",
                    [self._fk_value],
                )
                row = cur.fetchone()
                remaining = int(row[0]) if row and row[0] is not None else 0

            if remaining == 0:
                for d in list(deleted_dirs):
                    try:
                        if d and os.path.isdir(d):
                            shutil.rmtree(d)
                    except Exception:
                        # Best-effort cleanup; no UI errors for folder deletion.
                        pass
        except Exception:
            # Folder cleanup is best-effort
            pass

        self._update_delete_button()

        if errors:
            QMessageBox.warning(self, "Delete", "\n\n".join(errors))


    def _rename_original_filename(self, item: QListWidgetItem) -> None:
        """Öffnet einen Dialog zum Umbenennen einer einzelnen Datei."""
        img = item.data(Qt.UserRole) or {}

        rel_path = str(img.get("RelativePath") or "")
        stored = str(img.get("StoredFilename") or img.get("StoredFile") or "")
        current = str(img.get("OriginalFilename") or "")

        # Determine the frozen extension.
        ref_name = current or stored
        _base, ext = os.path.splitext(ref_name)
        if not ext:
            ext = ""  # Nothing to preserve

        # Suggest base name without extension
        current_base = os.path.splitext(current)[0] if current else os.path.splitext(stored)[0]

        new_base, ok = QInputDialog.getText(
            self,
            "Rename OriginalFilename",
            f"New name (extension {ext} is fixed):",
            QLineEdit.Normal,
            current_base,
        )
        if not ok:
            return

        new_base = (new_base or "").strip()
        if not new_base:
            return

        # If user typed a full filename, strip any extension they tried to set.
        # Then enforce the original ext.
        candidate_base, candidate_ext = os.path.splitext(new_base)
        if candidate_ext:
            new_base = candidate_base

        # Sanitize (avoid paths)
        new_base = new_base.replace("/", "_").replace("\\", "_")
        new_name = f"{new_base}{ext}"

        # Snapshot selection so we can rebuild/re-sort the list and keep focus.
        selected_full_path = str(img.get("FullPath") or "")

        # Helper: Access via ODBC is notorious for returning rowcount = -1
        # (unknown) even when an UPDATE succeeded. So we verify by selecting.
        def _verify_persisted(cur) -> bool:
            img_id = img.get("ID")
            if img_id not in (None, ""):
                cur.execute(
                    f"SELECT [OriginalFilename] FROM [{self._table_name}] WHERE [ID]=?",
                    [img_id],
                )
                row = cur.fetchone()
                return bool(row and str(row[0] or "").strip().lower() == str(new_name).strip().lower())

            cur.execute(
                f"SELECT [OriginalFilename] FROM [{self._table_name}] "
                f"WHERE [{self._fk_field}]=? AND [StoredFilename]=? AND [RelativePath]=?",
                [self._fk_value, stored, rel_path],
            )
            row = cur.fetchone()
            return bool(row and str(row[0] or "").strip().lower() == str(new_name).strip().lower())

        try:
            with get_connection() as cn:
                cur = cn.cursor()

                # Prefer the row's own primary key if available (most robust)
                img_id = img.get("ID")
                if img_id not in (None, ""):
                    cur.execute(
                        f"UPDATE [{self._table_name}] SET [OriginalFilename]=? WHERE [ID]=?",
                        [new_name, img_id],
                    )
                else:
                    # Fallback: match by FK + StoredFilename + RelativePath
                    cur.execute(
                        f"UPDATE [{self._table_name}] "
                        f"SET [OriginalFilename]=? "
                        f"WHERE [{self._fk_field}]=? AND [StoredFilename]=? AND [RelativePath]=?",
                        [new_name, self._fk_value, stored, rel_path],
                    )

                cn.commit()

                # Only show the warning if we can verify that the DB did NOT update.
                # (rowcount may be 0 or -1 even when the update worked.)
                if not _verify_persisted(cur):
                    QMessageBox.warning(
                        self,
                        "Rename",
                        "No database row was updated. The image could not be matched."
                    )
                    return
        except Exception as e:
            QMessageBox.critical(self, "Rename failed", str(e))
            return

        # Update local model (self._images) so the viewer updates immediately.
        def _matches(d: Dict[str, str]) -> bool:
            if img.get("ID") not in (None, "") and d.get("ID") not in (None, ""):
                return str(d.get("ID")) == str(img.get("ID"))
            return (
                str(d.get("StoredFilename") or d.get("StoredFile") or "") == stored
                and str(d.get("RelativePath") or "") == rel_path
            )

        for d in self._images:
            if _matches(d):
                d["OriginalFilename"] = new_name
                break

        # Rebuild list (resort) and keep selection + preview consistent.
        self._fill_list(select_full_path=selected_full_path)

    def _on_select(self, current: Optional[QListWidgetItem], _prev: Optional[QListWidgetItem]):
        """Aktualisiert die Vorschau wenn eine andere Datei ausgewählt wird."""
        if not current:
            self.lbl_name.setText("")
            self._pm_original = None
            self._zoom = 1.0
            self.lbl_preview.setText("Select an image…")
            self.lbl_preview.setPixmap(QPixmap())
            self.lbl_preview.adjustSize()
            return

        img = current.data(Qt.UserRole) or {}
        name = img.get("OriginalFilename") or ""
        full_path = img.get("FullPath") or ""

        self.lbl_name.setText(self._display_name(name))

        pm = QPixmap(full_path)
        if pm.isNull():
            self._pm_original = None
            self.lbl_preview.setPixmap(QPixmap())
            self.lbl_preview.setText(f"File not found / cannot load:\n{full_path}")
            return
        self._pm_original = pm
        self._set_zoom_fit()

    def showEvent(self, event):
        """Ensure the dialog opens maximized and the preview fits the final frame size."""
        super().showEvent(event)
        if not self._did_initial_show:
            self._did_initial_show = True
            # Maximize on first show (works with exec()).
            self.setWindowState(self.windowState() | Qt.WindowMaximized)
            # After the layout has its final size, fit the image into the frame.
            QTimer.singleShot(0, lambda: self._set_zoom_fit() if self._pm_original is not None else None)

    def resizeEvent(self, event):  # keep preview crisp on resize
        """Rendert die Vorschau neu wenn sich die Dialoggrösse ändert."""
        super().resizeEvent(event)
        if self._pm_original is not None:
            self._render_preview()


    # ---------------- Zoom / render helpers ----------------

    def _zoom_relative(self, factor: float) -> None:
        """Zoomt die Vorschau relativ zum aktuellen Zoom um den Faktor factor."""
        """Multiply current zoom by `factor` and re-render."""
        if self._pm_original is None:
            return
        try:
            f = float(factor)
        except Exception:
            return
        if f <= 0:
            return
        self._zoom = max(0.25, min(6.0, self._zoom * f))
        self._render_preview()

    def _set_zoom_fit(self) -> None:
        """Setzt die Vorschau auf «Fit to Window»."""
        """Fit the image into the preview viewport (no cropping)."""
        if self._pm_original is None:
            return
        vw = max(1, self.scroll_preview.viewport().width())
        vh = max(1, self.scroll_preview.viewport().height())
        pw = max(1, self._pm_original.width())
        ph = max(1, self._pm_original.height())
        z = min(vw / pw, vh / ph)
        # Don't explode tiny images on fit; cap to 1.0
        z = min(1.0, z)
        self._zoom = max(0.25, min(6.0, z))
        self._render_preview()

    def _render_preview(self) -> None:
        """Rendert die Vorschau des aktuell selektierten Bildes."""
        if self._pm_original is None:
            self.lbl_preview.setPixmap(QPixmap())
            self.lbl_preview.setText("Select an image…")
            self.lbl_preview.adjustSize()
            try:
                self.scroll_preview.viewport().unsetCursor()
            except Exception:
                pass
            return
        pm = self._pm_original
        w = max(1, int(pm.width() * self._zoom))
        h = max(1, int(pm.height() * self._zoom))
        scaled = pm.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.lbl_preview.setText("")
        self.lbl_preview.setPixmap(scaled)
        self.lbl_preview.adjustSize()

        # Hint that the preview can be dragged.
        try:
            if not self._panning:
                self.scroll_preview.viewport().setCursor(Qt.OpenHandCursor)
        except Exception:
            pass

    def eventFilter(self, obj, event):
        """Fängt Scroll-Events für Zoom in der Vorschau ab."""
        # Mouse interactions over preview:
        # - Wheel: zoom
        # - Drag (left mouse button): pan
        try:
            if obj is self.scroll_preview.viewport():
                et = event.type()

                # Wheel zoom
                if et == QEvent.Wheel:
                    dy = event.angleDelta().y()
                    if dy == 0:
                        return True
                    self._zoom_relative(1.1 if dy > 0 else 1 / 1.1)
                    return True

                # Start panning
                if et == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                    if self._pm_original is None:
                        return True
                    self._panning = True
                    self._pan_start_pos = event.pos()
                    self._pan_start_h = self.scroll_preview.horizontalScrollBar().value()
                    self._pan_start_v = self.scroll_preview.verticalScrollBar().value()
                    try:
                        self.scroll_preview.viewport().setCursor(Qt.ClosedHandCursor)
                    except Exception:
                        pass
                    return True

                # Pan while dragging
                if et == QEvent.MouseMove and self._panning and self._pan_start_pos is not None:
                    delta = event.pos() - self._pan_start_pos
                    self.scroll_preview.horizontalScrollBar().setValue(self._pan_start_h - delta.x())
                    self.scroll_preview.verticalScrollBar().setValue(self._pan_start_v - delta.y())
                    return True

                # Stop panning
                if et == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton and self._panning:
                    self._panning = False
                    self._pan_start_pos = None
                    try:
                        self.scroll_preview.viewport().setCursor(Qt.OpenHandCursor)
                    except Exception:
                        pass
                    return True

                # If the user drags outside the viewport, ensure we stop cleanly.
                if et == QEvent.Leave and self._panning:
                    self._panning = False
                    self._pan_start_pos = None
                    try:
                        self.scroll_preview.viewport().setCursor(Qt.OpenHandCursor)
                    except Exception:
                        pass
                    return True

        except Exception:
            pass
        return super().eventFilter(obj, event)

def _try_tables_for_fk(field_name: str) -> List[str]:
    """Ermittelt mögliche FK-Lookup-Tabellen für einen Feldnamen (heuristisch)."""
    """Heuristik: <X>ID → tblX, tblXs, tblXes"""
    base = field_name[:-2] if field_name.lower().endswith("id") else field_name
    base = base.strip().strip("_")
    if not base:
        return []
    cands = [f"tbl{base}", f"tbl{base}s", f"tbl{base}es"]
    # häufige Sonderfälle
    if base.lower() == "user":
        cands = ["tblUser", "tblUsers"]
    return cands


def _pick_display_column(table: str) -> Optional[str]:
    """Wählt die beste Anzeigespalte einer FK-Lookup-Tabelle (Name, Bezeichnung o.ä.)."""
    """Wählt eine sinnvolle Anzeigespalte für Dropdowns."""
    preferred = ["Name", "Username", "Title", "Bezeichnung", "Beschreibung", "DisplayName"]
    # MySQL: information_schema
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (current_db_name(), table.lower()),
        )
        rows = cur.fetchall()
        cols = [r[0] for r in rows] if rows else []
    for p in preferred:
        if p in cols:
            return p
    # sonst: erste Textspalte (type_name enthält oft VARCHAR/TEXT)
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (current_db_name(), table.lower()),
        )
        for name, data_type in cur.fetchall() or []:
            tn = str(data_type or "").lower()
            if any(x in tn for x in ["char", "text", "varchar"]):
                return str(name)
    return None


def _get_table_columns(table: str) -> List[ColumnInfo]:
    """Lädt alle Spalten einer Tabelle als ColumnInfo-Liste aus der DB."""
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            """
            SELECT column_name, data_type, column_type
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (current_db_name(), table.lower()),
        )
        cols: List[ColumnInfo] = []
        for name, data_type, column_type in cur.fetchall() or []:
            cols.append(ColumnInfo(name=str(name), data_type=None, type_name=str(column_type)))
        return cols


def _table_exists(table: str) -> bool:
    """Gibt True zurück wenn die Tabelle in der DB existiert."""
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
            LIMIT 1
            """,
            (current_db_name(), table.lower()),
        )
        return cur.fetchone() is not None


def _is_guid_col(col: ColumnInfo) -> bool:
    """Gibt True zurück wenn eine Spalte als GUID-Feld erkannt wird (ID/GlobalID-Typ)."""
    # MySQL: GUIDs werden bei uns als VARCHAR gespeichert
    tn = str(col.type_name or "").lower()
    return "char(36" in tn or "varchar(36" in tn





class ExperimentRequestPdfsDialog(QDialog):
    """Dialog zur Verwaltung von PDFs eines Experiment-Requests (analog zu Images)."""
    """Viewer for stored PDFs (read-only).

    Features (analog to images):
      - Left list shows OriginalFilename (natural sort).
      - Right-click a list item to rename OriginalFilename (extension is fixed).
      - Delete removes the DB row and the stored file from disk.
      - Preview is embedded:
          * If QtWebEngine is available: show the PDF directly.
          * Otherwise: render pages to images via PyMuPDF (fitz).
    """

    @staticmethod
    def _natural_sort_key(s: str) -> List[object]:
        parts = re.split(r"(\d+)", s or "")
        out: List[object] = []
        for part in parts:
            if part.isdigit():
                out.append(int(part))
            else:
                out.append(part.lower())
        return out

    def __init__(
        self,
        parent: QWidget,
        title: str,
        pdfs: List[Dict[str, str]],
        *,
        table_name: str | None = None,
        fk_field: str | None = None,
        fk_value: Any | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        # PDF viewer dialog should always open maximized.
        self.setWindowState(self.windowState() | Qt.WindowMaximized)
        self.setMinimumSize(920, 620)
        self.resize(1200, 820)

        self._pdfs = list(pdfs or [])
        self._pdfs.sort(
            key=lambda d: self._natural_sort_key(
                str(d.get("OriginalFilename") or d.get("StoredFilename") or "")
            )
        )

        self._table_name = table_name
        self._fk_field = fk_field
        self._fk_value = fk_value

        # Zoom state (image preview)
        self._zoom: float = 1.0
        self._pm_original: QPixmap | None = None
        self._did_initial_show: bool = False

        self._current_full_path: str | None = None
        self._zoom: float = 1.0
        # Page navigation state (PyMuPDF renderer)
        self._page_index: int = 0
        self._page_count: int = 0
        # Keep references so we can release file locks before deleting.
        self._fitz_doc = None
        self._web_view = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal, self)

        # Left
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.lst = QListWidget()
        self.lst.setMinimumWidth(260)
        self.lst.setSelectionMode(QListWidget.ExtendedSelection)
        left_layout.addWidget(self.lst, 1)

        # Batch rename button intentionally removed for the PDF viewer.

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._delete_selected)
        left_layout.addWidget(self.btn_delete, 0)

        splitter.addWidget(left)

        # Right
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self.lbl_name = QLabel("")
        self.lbl_name.setTextFormat(Qt.PlainText)
        self.lbl_name.setWordWrap(True)
        self.lbl_name.setStyleSheet("font-weight: 600;")
        right_layout.addWidget(self.lbl_name, 0)

        # Zoom controls (only used for render fallback, but harmless)
        zoom_bar = QHBoxLayout()
        self.btn_zoom_out = QPushButton()
        self.btn_zoom_in = QPushButton()
        # Icons must be stored in: assets\images\zoom_out.png and assets\images\zoom_in.png
        try:
            self.btn_zoom_out.setIcon(QIcon(resource_path("assets/images/zoom_out.png")))
            self.btn_zoom_in.setIcon(QIcon(resource_path("assets/images/zoom_in.png")))
            self.btn_zoom_out.setIconSize(QSize(20, 20))
            self.btn_zoom_in.setIconSize(QSize(20, 20))
        except Exception:
            # Fallback if icons are missing
            self.btn_zoom_out.setText("–")
            self.btn_zoom_in.setText("+")

        self.btn_zoom_out.setFixedSize(34, 34)
        self.btn_zoom_in.setFixedSize(34, 34)
        self.btn_zoom_out.clicked.connect(lambda: self._set_zoom(self._zoom / 1.25))
        self.btn_zoom_in.clicked.connect(lambda: self._set_zoom(self._zoom * 1.25))
        zoom_bar.addStretch(1)
        zoom_bar.addWidget(self.btn_zoom_out)
        zoom_bar.addWidget(self.btn_zoom_in)
        zoom_bar.addStretch(1)
        right_layout.addLayout(zoom_bar, 0)


        # Page navigation (multi-page PDFs)
        nav_bar = QHBoxLayout()
        self.btn_page_up = QPushButton()
        self.btn_page_down = QPushButton()
        self.btn_page_up.setFixedSize(34, 34)
        self.btn_page_down.setFixedSize(34, 34)
        try:
            self.btn_page_up.setIcon(QIcon(resource_path("assets/images/triangle_up_24.png")))
            self.btn_page_down.setIcon(QIcon(resource_path("assets/images/triangle_down_24.png")))
            self.btn_page_up.setIconSize(QSize(20, 20))
            self.btn_page_down.setIconSize(QSize(20, 20))
        except Exception:
            self.btn_page_up.setText("↑")
            self.btn_page_down.setText("↓")

        self.lbl_page = QLabel("")
        self.lbl_page.setAlignment(Qt.AlignCenter)
        self.lbl_page.setTextFormat(Qt.PlainText)
        self.lbl_page.setMinimumWidth(110)

        # Disabled until a PDF is loaded
        self.btn_page_up.setEnabled(False)
        self.btn_page_down.setEnabled(False)

        self.btn_page_up.clicked.connect(lambda: self._goto_page(self._page_index - 1))
        self.btn_page_down.clicked.connect(lambda: self._goto_page(self._page_index + 1))

        nav_bar.addStretch(1)
        nav_bar.addWidget(self.btn_page_up)
        nav_bar.addWidget(self.lbl_page)
        nav_bar.addWidget(self.btn_page_down)
        nav_bar.addStretch(1)
        right_layout.addLayout(nav_bar, 0)

        self._viewer_container = QWidget()
        self._viewer_layout = QVBoxLayout(self._viewer_container)
        self._viewer_layout.setContentsMargins(0, 0, 0, 0)
        self._viewer_layout.setSpacing(0)
        right_layout.addWidget(self._viewer_container, 1)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns, 0)

        # Context menu: rename
        self.lst.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lst.customContextMenuRequested.connect(self._on_list_context_menu)

        self._fill_list()
        self.lst.currentItemChanged.connect(self._on_select)
        self.lst.itemSelectionChanged.connect(self._update_delete_button)

        # Ensure the first PDF is shown immediately on open (also when only 1 PDF exists).
        if self.lst.count() > 0 and self.lst.currentItem() is None:
            self.lst.setCurrentRow(0)
        if self.lst.currentItem() is not None:
            self._on_select(self.lst.currentItem(), None)

    def _clear_viewer(self) -> None:
        # Release any open file handles (important for Windows delete).
        try:
            if self._fitz_doc is not None:
                self._fitz_doc.close()
        except Exception:
            pass
        self._fitz_doc = None

        try:
            if self._web_view is not None:
                from PySide6.QtCore import QUrl
                self._web_view.setUrl(QUrl("about:blank"))
                self._web_view.deleteLater()
        except Exception:
            pass
        self._web_view = None

        while self._viewer_layout.count():
            it = self._viewer_layout.takeAt(0)
            w = it.widget()
            if w is not None:
                w.deleteLater()

    def _fill_list(self, select_full_path: str | None = None) -> None:
        # Build list while blocking signals, but select AFTER unblocking.
        # Otherwise the initial selection change is swallowed and the viewer stays blank.
        sel_row = 0
        self.lst.blockSignals(True)
        try:
            self.lst.clear()
            for i, d in enumerate(self._pdfs):
                name = str(d.get("OriginalFilename") or d.get("StoredFilename") or "")
                if not name:
                    name = "(unnamed)"
                item = QListWidgetItem(name)
                item.setData(Qt.UserRole, d)
                self.lst.addItem(item)
                if select_full_path and str(d.get("FullPath") or "") == select_full_path:
                    sel_row = i
        finally:
            self.lst.blockSignals(False)

        if self.lst.count() > 0:
            self.lst.setCurrentRow(min(sel_row, self.lst.count() - 1))

    def _update_delete_button(self) -> None:
        self.btn_delete.setEnabled(self.lst.selectedItems() != [])

    def _on_list_context_menu(self, pos: QPoint):
        item = self.lst.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        act_rename = menu.addAction("Rename…")
        act_save_as = menu.addAction("Save As…")
        act = menu.exec(self.lst.mapToGlobal(pos))
        if act == act_rename:
            self._rename_original_filename(item)
        elif act == act_save_as:
            self._save_as_file(item)

    def _save_as_file(self, item: QListWidgetItem) -> None:
        """Kopiert die gespeicherte PDF-Datei an einen vom Benutzer gewählten Ort."""
        d = item.data(Qt.UserRole) or {}
        src = str(d.get("FullPath") or "")
        if not src or not os.path.isfile(src):
            QMessageBox.warning(self, "Save As", "Datei nicht gefunden:\n" + src)
            return

        orig = str(d.get("OriginalFilename") or os.path.basename(src))
        dst, _ = QFileDialog.getSaveFileName(self, "Save As", orig, "PDF-Dateien (*.pdf);;Alle Dateien (*)")
        if not dst:
            return
        try:
            import shutil
            shutil.copy2(src, dst)
        except Exception as e:
            QMessageBox.critical(self, "Save As", f"Fehler beim Speichern:\n{e}")

    def _set_zoom(self, z: float) -> None:
        z = max(0.25, min(4.0, float(z)))
        self._zoom = z
        # Re-render current selection
        if self._current_full_path:
            if self._fitz_doc is not None:
                self._render_current_page()
            else:
                self._show_pdf(self._current_full_path)

    def _on_select(self, current: Optional[QListWidgetItem], _prev: Optional[QListWidgetItem]):
        if not current:
            self.lbl_name.setText("")
            self._clear_viewer()
            self._viewer_layout.addWidget(QLabel("Select a PDF…", self))
            self._current_full_path = None
            return

        d = current.data(Qt.UserRole) or {}
        full = str(d.get("FullPath") or "")
        show_name = str(d.get("OriginalFilename") or d.get("StoredFilename") or full or "")
        self.lbl_name.setText(show_name)
        self._current_full_path = full
        self._page_index = 0
        self._show_pdf(full)

    def _goto_page(self, page_index: int) -> None:
        if self._fitz_doc is None or self._page_count <= 0:
            return
        page_index = int(page_index)
        page_index = max(0, min(self._page_count - 1, page_index))
        if page_index == self._page_index:
            return
        self._page_index = page_index
        self._render_current_page()

    def _clear_viewer_widgets(self) -> None:
        while self._viewer_layout.count():
            it = self._viewer_layout.takeAt(0)
            w = it.widget()
            if w is not None:
                w.deleteLater()

    def _render_current_page(self) -> None:
        """Render the currently selected page using PyMuPDF."""
        if self._fitz_doc is None or self._page_count <= 0:
            self.btn_page_up.setEnabled(False)
            self.btn_page_down.setEnabled(False)
            self.lbl_page.setText("")
            return

        self._clear_viewer_widgets()

        try:
            import fitz  # PyMuPDF

            mat = fitz.Matrix(self._zoom * 1.6, self._zoom * 1.6)
            page = self._fitz_doc.load_page(self._page_index)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            samples = bytes(pix.samples)
            if pix.n >= 3:
                fmt = QImage.Format_RGB888
            else:
                fmt = getattr(QImage, 'Format_Grayscale8', QImage.Format_Indexed8)
            img = QImage(samples, pix.width, pix.height, pix.stride, fmt).copy()

            scroll = QScrollArea(self)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.StyledPanel)

            wrap = QWidget()
            v = QVBoxLayout(wrap)
            v.setContentsMargins(10, 10, 10, 10)
            v.setSpacing(10)

            lbl = QLabel()
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setPixmap(QPixmap.fromImage(img))
            lbl.setStyleSheet("border: 1px solid #444; border-radius: 6px; padding: 6px;")
            v.addWidget(lbl, 0)
            v.addStretch(1)
            scroll.setWidget(wrap)
            self._viewer_layout.addWidget(scroll, 1)

            # Update controls
            self.lbl_page.setText(f"Page {self._page_index + 1}/{self._page_count}")
            self.btn_page_up.setEnabled(self._page_index > 0)
            self.btn_page_down.setEnabled(self._page_index < (self._page_count - 1))

        except Exception:
            self.btn_page_up.setEnabled(False)
            self.btn_page_down.setEnabled(False)
            self.lbl_page.setText("")
            lbl = QLabel("PDF konnte nicht angezeigt werden.")
            lbl.setAlignment(Qt.AlignCenter)
            self._viewer_layout.addWidget(lbl, 1)

    def _show_pdf(self, full_path: str) -> None:
        """Show a PDF in the right pane (read-only).

        Strategy:
          1) Render via PyMuPDF (fitz) – most reliable for multi-page scan PDFs.
          2) If that fails, fall back to QtWebEngine (may be blank if PDF rendering is disabled).

        Note: The UI intentionally shows no technical diagnostics (paths, file existence, backend names).
        """
        self._clear_viewer()
        self.btn_page_up.setEnabled(False)
        self.btn_page_down.setEnabled(False)
        self.lbl_page.setText("")

        # Normalise path (defensive: trims, fixes slashes)
        full_path = (full_path or '').strip()
        try:
            full_path_norm = os.path.normpath(full_path)
        except Exception:
            full_path_norm = full_path

        exists = bool(full_path_norm) and os.path.exists(full_path_norm)

        if not full_path_norm or not exists:
            lbl = QLabel("PDF konnte nicht geladen werden.")
            lbl.setAlignment(Qt.AlignCenter)
            self._viewer_layout.addWidget(lbl, 1)
            return

        # --- Preferred: PyMuPDF renderer (page-wise) ---
        try:
            import fitz  # PyMuPDF

            self._fitz_doc = fitz.open(full_path_norm)
            self._page_count = int(getattr(self._fitz_doc, 'page_count', 0) or 0)
            if self._page_count <= 0:
                self._clear_viewer_widgets()
                empty = QLabel("PDF contains no pages.")
                empty.setAlignment(Qt.AlignCenter)
                self._viewer_layout.addWidget(empty, 1)
                self.btn_page_up.setEnabled(False)
                self.btn_page_down.setEnabled(False)
                self.lbl_page.setText("")
                return

            self._page_index = max(0, min(self._page_count - 1, int(self._page_index)))
            self._render_current_page()
            return

        except Exception as e:
            # Fall back to QtWebEngine below. Don't show technical details to the user.
            try:
                print("[PDF] PyMuPDF render failed:", e)
            except Exception:
                pass

        # --- Fallback: QtWebEngine ---
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView  # type: ignore
            from PySide6.QtCore import QUrl

            view = QWebEngineView(self)
            # Use fromLocalFile to avoid quoting issues
            view.setUrl(QUrl.fromLocalFile(full_path_norm))
            self._web_view = view
            self._viewer_layout.addWidget(view, 1)
            return

        except Exception as e:
            try:
                print("[PDF] QtWebEngine fallback failed:", e)
            except Exception:
                pass
            lbl = QLabel("PDF konnte nicht angezeigt werden.")
            lbl.setAlignment(Qt.AlignCenter)
            self._viewer_layout.addWidget(lbl, 1)
            return

    def _rename_original_filename(self, item: QListWidgetItem) -> None:
        d = item.data(Qt.UserRole) or {}

        rel_path = str(d.get("RelativePath") or "")
        stored = str(d.get("StoredFilename") or "")
        current = str(d.get("OriginalFilename") or "")

        ref_name = current or stored
        _base, ext = os.path.splitext(ref_name)
        if not ext:
            ext = ".pdf"

        current_base = os.path.splitext(current)[0] if current else os.path.splitext(stored)[0]

        new_base, ok = QInputDialog.getText(
            self,
            "Rename OriginalFilename",
            f"New name (extension {ext} is fixed):",
            QLineEdit.Normal,
            current_base,
        )
        if not ok:
            return
        new_base = (new_base or "").strip()
        if not new_base:
            return

        cand_base, cand_ext = os.path.splitext(new_base)
        if cand_ext:
            new_base = cand_base

        new_base = new_base.replace("/", "_").replace("\\", "_")
        new_name = f"{new_base}{ext}"

        selected_full_path = str(d.get("FullPath") or "")

        def _verify(cur) -> bool:
            doc_id = d.get("ID")
            if doc_id not in (None, ""):
                cur.execute(f"SELECT [OriginalFilename] FROM [{self._table_name}] WHERE [ID]=?", [doc_id])
                row = cur.fetchone()
                return bool(row and str(row[0] or "").strip().lower() == str(new_name).strip().lower())

            cur.execute(
                f"SELECT [OriginalFilename] FROM [{self._table_name}] "
                f"WHERE [{self._fk_field}]=? AND [StoredFilename]=? AND [RelativePath]=?",
                [self._fk_value, stored, rel_path],
            )
            row = cur.fetchone()
            return bool(row and str(row[0] or "").strip().lower() == str(new_name).strip().lower())

        try:
            with get_connection() as cn:
                cur = cn.cursor()
                doc_id = d.get("ID")
                if doc_id not in (None, ""):
                    cur.execute(
                        f"UPDATE [{self._table_name}] SET [OriginalFilename]=? WHERE [ID]=?",
                        [new_name, doc_id],
                    )
                else:
                    cur.execute(
                        f"UPDATE [{self._table_name}] SET [OriginalFilename]=? "
                        f"WHERE [{self._fk_field}]=? AND [StoredFilename]=? AND [RelativePath]=?",
                        [new_name, self._fk_value, stored, rel_path],
                    )
                cn.commit()
                if not _verify(cur):
                    QMessageBox.warning(self, "Rename", "No database row was updated. The PDF could not be matched.")
                    return
        except Exception as e:
            QMessageBox.critical(self, "Rename failed", str(e))
            return

        # Update local list + resort
        def _matches(x: Dict[str, str]) -> bool:
            if d.get("ID") not in (None, "") and x.get("ID") not in (None, ""):
                return str(x.get("ID")) == str(d.get("ID"))
            return str(x.get("StoredFilename") or "") == stored and str(x.get("RelativePath") or "") == rel_path

        for x in self._pdfs:
            if _matches(x):
                x["OriginalFilename"] = new_name
                break

        self._pdfs.sort(key=lambda z: self._natural_sort_key(str(z.get("OriginalFilename") or z.get("StoredFilename") or "")))
        self._fill_list(select_full_path=selected_full_path)

    def _open_batch_rename(self) -> None:
        if not (self._table_name and self._fk_field and self._fk_value not in (None, "")):
            return
        prefix, ok = QInputDialog.getText(self, "Batch rename", "Prefix (e.g. V):", QLineEdit.Normal, "V")
        if not ok:
            return
        prefix = (prefix or "").strip()
        if not prefix:
            return
        start_num, ok = QInputDialog.getInt(self, "Batch rename", "Start number:", 1, 1, 999999, 1)
        if not ok:
            return

        # Apply to currently selected, otherwise all
        items = self.lst.selectedItems() or [self.lst.item(i) for i in range(self.lst.count())]
        if not items:
            return

        errors: List[str] = []
        num = int(start_num)

        for it in items:
            d = it.data(Qt.UserRole) or {}
            ref = str(d.get("OriginalFilename") or d.get("StoredFilename") or "")
            _base, ext = os.path.splitext(ref)
            if not ext:
                ext = ".pdf"
            new_name = f"{prefix}{num}{ext}"
            num += 1

            try:
                with get_connection() as cn:
                    cur = cn.cursor()
                    doc_id = d.get("ID")
                    if doc_id not in (None, ""):
                        cur.execute(
                            f"UPDATE [{self._table_name}] SET [OriginalFilename]=? WHERE [ID]=?",
                            [new_name, doc_id],
                        )
                    else:
                        cur.execute(
                            f"UPDATE [{self._table_name}] SET [OriginalFilename]=? "
                            f"WHERE [{self._fk_field}]=? AND [StoredFilename]=? AND [RelativePath]=?",
                            [new_name, self._fk_value, str(d.get('StoredFilename') or ''), str(d.get('RelativePath') or '')],
                        )
                    cn.commit()
            except Exception as e:
                errors.append(f"{ref}: {e}")
                continue

            for x in self._pdfs:
                if str(x.get("FullPath") or "") == str(d.get("FullPath") or ""):
                    x["OriginalFilename"] = new_name
                    break

        self._pdfs.sort(key=lambda z: self._natural_sort_key(str(z.get("OriginalFilename") or z.get("StoredFilename") or "")))
        self._fill_list(select_full_path=self._current_full_path)

        if errors:
            QMessageBox.warning(self, "Batch rename", "Some items failed:\n\n" + "\n".join(errors))

    def _delete_selected(self) -> None:
        items = list(self.lst.selectedItems() or [])
        if not items:
            return

        if QMessageBox.question(
            self,
            "Delete",
            f"Delete {len(items)} PDF(s)?\n\nThis will remove the DB row and delete the stored file.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return

        errors: List[str] = []
        deleted_dirs: set[str] = set()
        deleted_doc_ids: set[str] = set()
        deleted_keys: set[tuple[str, str]] = set()  # (RelativePath, StoredFilename)
        deleted_ok_full: set[str] = set()

        from PySide6.QtCore import QCoreApplication
        import time

        for it in items:
            d = it.data(Qt.UserRole) or {}
            full = str(d.get("FullPath") or "")
            rel = str(d.get("RelativePath") or "")
            stored = str(d.get("StoredFilename") or "")
            doc_id = d.get("ID")

            # Delete file (must happen first; DB row is only removed if the file is gone)
            file_deleted = False
            try:
                # If the file is currently being viewed, release handles first.
                if full and self._current_full_path and os.path.normpath(full) == os.path.normpath(self._current_full_path):
                    self._current_full_path = None
                    self._clear_viewer()
                    QCoreApplication.processEvents()

                if full and os.path.exists(full):
                    # Windows can keep the file locked briefly (WebEngine, AV, etc.). Retry a few times.
                    last_err = None
                    for _ in range(4):
                        try:
                            os.remove(full)
                            file_deleted = True
                            break
                        except Exception as e:
                            last_err = e
                            QCoreApplication.processEvents()
                            time.sleep(0.15)
                    if file_deleted:
                        parent_dir = os.path.dirname(full)
                        if parent_dir:
                            deleted_dirs.add(parent_dir)
                    else:
                        raise last_err if last_err is not None else OSError("delete failed")
                else:
                    # Nothing to delete on disk; treat as ok (we still remove the DB row)
                    file_deleted = True
            except Exception:
                # No path/technical details in the UI.
                errors.append("File could not be deleted (it may still be in use).")

            # Delete DB row (only if file deletion succeeded)
            try:
                if not file_deleted:
                    continue
                db_deleted = False
                if self._table_name and self._fk_field and self._fk_value not in (None, ""):
                    with get_connection() as cn:
                        cur = cn.cursor()
                        if doc_id not in (None, ""):
                            cur.execute(f"DELETE FROM [{self._table_name}] WHERE [ID]=?", [doc_id])
                        else:
                            cur.execute(
                                f"DELETE FROM [{self._table_name}] "
                                f"WHERE [{self._fk_field}]=? AND [StoredFilename]=? AND [RelativePath]=?",
                                [self._fk_value, stored, rel],
                            )
                        cn.commit()
                        db_deleted = True
                else:
                    db_deleted = True
            except Exception as e:
                # Keep this user-facing and without backend details.
                errors.append("Database entry could not be deleted.")
                db_deleted = False

            if file_deleted and db_deleted:
                if doc_id not in (None, ""):
                    deleted_doc_ids.add(str(doc_id))
                if rel or stored:
                    deleted_keys.add((rel, stored))
                if full:
                    deleted_ok_full.add(str(full))

        # Refresh local model + UI (remove deleted items from the left list immediately)
        deleted_full = deleted_ok_full
        keep: List[Dict[str, Any]] = []
        for x in self._pdfs:
            x_full = str(x.get("FullPath") or "")
            x_id = x.get("ID")
            x_rel = str(x.get("RelativePath") or "")
            x_stored = str(x.get("StoredFilename") or "")

            if x_full and x_full in deleted_full:
                continue
            if x_id not in (None, "") and str(x_id) in deleted_doc_ids:
                continue
            if (x_rel, x_stored) in deleted_keys:
                continue
            keep.append(x)
        self._pdfs = keep

        # Rebuild the list and update the viewer so stale titles can't linger.
        self._fill_list()
        if self.lst.count() == 0:
            self._current_full_path = None
            self.lbl_name.setText("")
            self._clear_viewer()
            self._viewer_layout.addWidget(QLabel("Select a PDF…", self))
        else:
            # Force refresh of the right pane (even if Qt decides selection didn't "change")
            self._on_select(self.lst.currentItem(), None)

        # Remove empty folders (best-effort)
        try:
            remaining = 1
            if self._table_name and self._fk_field and self._fk_value not in (None, ""):
                with get_connection() as cn:
                    cur = cn.cursor()
                    cur.execute(f"SELECT COUNT(*) FROM [{self._table_name}] WHERE [{self._fk_field}]=?", [self._fk_value])
                    row = cur.fetchone()
                    remaining = int(row[0]) if row and row[0] is not None else 0

            if remaining == 0:
                for d in list(deleted_dirs):
                    try:
                        if d and os.path.isdir(d):
                            shutil.rmtree(d)
                    except Exception:
                        # Best-effort and silent (no path/technical details in UI).
                        pass
        except Exception:
            pass

        self._update_delete_button()

        if errors:
            QMessageBox.warning(self, "Delete", "\n\n".join(errors))



class BatchRenameDialog(QDialog):
    """Wizard dialog to rename OriginalFilename for a batch of images."""

    def __init__(
        self,
        parent: QWidget,
        *,
        images: List[Dict[str, str]],
        table_name: str,
        fk_field: str,
        fk_value: Any,
        natural_key,
    ):
        super().__init__(parent)
        self.setWindowTitle("Batch rename")
        # Enable maximize button and start maximized
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        self.setWindowState(self.windowState() | Qt.WindowMaximized)
        self.setMinimumSize(900, 650)
        self.resize(1100, 780)

        self._images = list(images or [])
        # IMPORTANT: Keep the ORIGINAL order of the images as passed in from the viewer.
        # Do NOT sort here, otherwise renaming changes the order and can cause images to be skipped.

        self._table_name = table_name
        self._fk_field = fk_field
        self._fk_value = fk_value

        # Zoom state (image preview)
        self._zoom: float = 1.0
        self._pm_original: QPixmap | None = None
        self._did_initial_show: bool = False
        self._idx = 0
        self._ext = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self.lbl_progress = QLabel("")
        self.lbl_progress.setTextFormat(Qt.PlainText)
        root.addWidget(self.lbl_progress)

        mid = QSplitter(Qt.Horizontal)
        root.addWidget(mid, 1)

        # Preview
        preview_wrap = QWidget()
        preview_l = QVBoxLayout(preview_wrap)
        preview_l.setContentsMargins(0, 0, 0, 0)
        preview_l.setSpacing(6)

        self.lbl_name = QLabel("")
        self.lbl_name.setWordWrap(True)
        self.lbl_name.setTextFormat(Qt.PlainText)
        preview_l.addWidget(self.lbl_name)

        self.lbl_preview = QLabel("")
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setMinimumSize(520, 520)
        self.lbl_preview.setStyleSheet("QLabel{background:#111; color:#ddd; border:1px solid #333;}")
        preview_l.addWidget(self.lbl_preview, 1)

        mid.addWidget(preview_wrap)

        # Form
        form_wrap = QWidget()
        form_l = QVBoxLayout(form_wrap)
        form_l.setContentsMargins(0, 0, 0, 0)
        form_l.setSpacing(8)

        grid = QGridLayout()
        grid.setColumnStretch(1, 1)

        grid.addWidget(QLabel("Current (read-only):"), 0, 0)
        self.txt_current = QLineEdit()
        self.txt_current.setReadOnly(True)
        grid.addWidget(self.txt_current, 0, 1)

        grid.addWidget(QLabel("New OriginalFilename:"), 1, 0)
        self.txt_new = QLineEdit()
        grid.addWidget(self.txt_new, 1, 1)

        grid.addWidget(QLabel("Prefix (optional):"), 2, 0)
        self.txt_prefix = QLineEdit()
        self.txt_prefix.setPlaceholderText("e.g. V")
        self.txt_prefix.setMaximumWidth(220)
        grid.addWidget(self.txt_prefix, 2, 1)
        form_l.addLayout(grid)
        self.lbl_hint = QLabel("Extension stays fixed. Optional prefix is prepended if missing. Press Enter to save & go next.")
        self.lbl_hint.setWordWrap(True)
        form_l.addWidget(self.lbl_hint)

        btn_row = QHBoxLayout()
        self.btn_back = QPushButton("← Back")
        self.btn_skip = QPushButton("Skip")
        self.btn_save_next = QPushButton("Save & Next →")
        self.btn_save_next.setDefault(True)
        self.btn_save_next.setAutoDefault(True)
        self.btn_finish = QPushButton("Finish")
        self.btn_cancel = QPushButton("Cancel")
        btn_row.addWidget(self.btn_back)
        btn_row.addWidget(self.btn_skip)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_save_next)
        btn_row.addWidget(self.btn_finish)
        btn_row.addWidget(self.btn_cancel)

        form_l.addStretch(1)
        form_l.addLayout(btn_row)

        mid.addWidget(form_wrap)
        mid.setSizes([700, 400])

        self.btn_back.clicked.connect(self._go_back)
        self.btn_skip.clicked.connect(self._skip)
        self.btn_save_next.clicked.connect(self._save_and_next)
        self.btn_finish.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        # Enter/Return should behave like "Save & Next".
        # Use an eventFilter to avoid Qt's occasional double-trigger quirks
        # (returnPressed + default button) and to ensure we ALWAYS advance.
        self.txt_new.installEventFilter(self)

        self._load_current()
        self.txt_new.setFocus()

    def eventFilter(self, obj, event):  # noqa: N802
        if obj is self.txt_new and event.type() == QEvent.KeyPress:
            key = event.key()
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self._save_and_next()
                return True
        return super().eventFilter(obj, event)

    def _current_img(self) -> Dict[str, str]:
        return self._images[self._idx]

    def _img_full_path(self, img: Dict[str, str]) -> str:
        full_path = str(img.get("FullPath") or "")
        if full_path:
            return full_path
        rel_path = str(img.get("RelativePath") or "")
        stored = str(img.get("StoredFilename") or img.get("StoredFile") or "")
        base = str(img.get("BaseDir") or "")
        if base and stored:
            return os.path.join(base, rel_path, stored)
        return ""

    def _set_preview_pixmap(self, pix: QPixmap) -> None:
        target = self.lbl_preview.size()
        self.lbl_preview.setText("")
        self.lbl_preview.setPixmap(pix.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _load_current(self) -> None:
        if not self._images:
            self.lbl_progress.setText("No images.")
            self.btn_back.setEnabled(False)
            self.btn_skip.setEnabled(False)
            self.btn_save_next.setEnabled(False)
            return

        img = self._current_img()
        name = str(img.get("OriginalFilename") or img.get("StoredFilename") or img.get("StoredFile") or "")
        self.lbl_progress.setText(f"Image {self._idx+1}/{len(self._images)}")
        self.lbl_name.setText(name)
        self.txt_current.setText(name)

        base, ext = os.path.splitext(name)
        self._ext = ext
        self.txt_new.setText(base)
        self.txt_new.selectAll()
        self.txt_new.setFocus()

        full_path = self._img_full_path(img)
        pix = QPixmap(full_path) if full_path else QPixmap()
        if pix and not pix.isNull():
            self._set_preview_pixmap(pix)
        else:
            self.lbl_preview.setPixmap(QPixmap())
            self.lbl_preview.setText("(Preview unavailable)")

        self.btn_back.setEnabled(self._idx > 0)

    def resizeEvent(self, ev):  # noqa: N802
        super().resizeEvent(ev)
        try:
            if not self._images:
                return
            img = self._current_img()
            full_path = self._img_full_path(img)
            pix = QPixmap(full_path) if full_path else QPixmap()
            if pix and not pix.isNull():
                self._set_preview_pixmap(pix)
        except Exception:
            pass

    def _go_back(self) -> None:
        if self._idx <= 0:
            return
        self._idx -= 1
        self._load_current()

    def _skip(self) -> None:
        if self._idx >= len(self._images) - 1:
            self.accept()
            return
        self._idx += 1
        self._load_current()

    def _save_and_next(self) -> None:
        img = self._current_img()
        rel_path = str(img.get("RelativePath") or "")
        stored = str(img.get("StoredFilename") or img.get("StoredFile") or "")
        current = str(img.get("OriginalFilename") or "")
        ref_name = current or stored
        _b, ext = os.path.splitext(ref_name)
        if not ext:
            ext = self._ext or ""

        new_base = (self.txt_new.text() or "").strip()
        if not new_base:
            QMessageBox.warning(self, "Rename", "Name cannot be empty.")
            return

        cand_base, cand_ext = os.path.splitext(new_base)
        if cand_ext:
            new_base = cand_base

        prefix = (getattr(self, "txt_prefix", None).text() if getattr(self, "txt_prefix", None) else "")
        prefix = (prefix or "").strip()
        if prefix:
            # If user already typed the prefix, don't add it again.
            if not new_base.lower().startswith(prefix.lower()):
                new_base = f"{prefix}{new_base}"
        new_base = new_base.replace("/", "_").replace("\\", "_")
        new_name = f"{new_base}{ext}"

        def _verify_persisted(cur) -> bool:
            img_id = img.get("ID")
            if img_id not in (None, ""):
                cur.execute(
                    f"SELECT [OriginalFilename] FROM [{self._table_name}] WHERE [ID]=?",
                    [img_id],
                )
                row = cur.fetchone()
                return bool(row and str(row[0] or "").strip().lower() == str(new_name).strip().lower())

            cur.execute(
                f"SELECT [OriginalFilename] FROM [{self._table_name}] "
                f"WHERE [{self._fk_field}]=? AND [StoredFilename]=? AND [RelativePath]=?",
                [self._fk_value, stored, rel_path],
            )
            row = cur.fetchone()
            return bool(row and str(row[0] or "").strip().lower() == str(new_name).strip().lower())

        try:
            with get_connection() as cn:
                cur = cn.cursor()

                img_id = img.get("ID")
                if img_id not in (None, ""):
                    cur.execute(
                        f"UPDATE [{self._table_name}] SET [OriginalFilename]=? WHERE [ID]=?",
                        [new_name, img_id],
                    )
                else:
                    cur.execute(
                        f"UPDATE [{self._table_name}] SET [OriginalFilename]=? "
                        f"WHERE [{self._fk_field}]=? AND [StoredFilename]=? AND [RelativePath]=?",
                        [new_name, self._fk_value, stored, rel_path],
                    )

                cn.commit()

                if not _verify_persisted(cur):
                    QMessageBox.warning(
                        self,
                        "Rename",
                        "No database row was updated. The image could not be matched."
                    )
                    return

        except Exception as e:
            QMessageBox.critical(self, "Rename failed", str(e))
            return

        img["OriginalFilename"] = new_name

        if self._idx >= len(self._images) - 1:
            self.accept()
            return

        self._idx += 1
        self._load_current()



class CreateExperimentRequestScreen(QWidget):
    """Create form for tblExperimentRequests.

    - Alle Felder anzeigen (ausser ID/Timestamp/CreatedBy)
    - Multiline-Felder als QTextEdit (3 Zeilen)
    - Wunschtermin als Date Picker
    """

    def __init__(self, on_back_home=None, on_back_experiment_request=None, request_id: Any | None = None):
        super().__init__()
        self.on_back_home = on_back_home
        self.on_back_experiment_request = on_back_experiment_request

        # Wenn gesetzt, wird ein bestehender Request geladen und beim Speichern per UPDATE gespeichert.
        self._edit_request_id: Any | None = request_id

        self._table = "tblExperimentRequests"
        self._cols: List[ColumnInfo] = []

        # field_name -> widget
        self._widgets: Dict[str, QWidget] = {}
        # for dropdowns: field_name -> [(id, label), ...]
        self._choices: Dict[str, List[Tuple[Any, str]]] = {}

        self._build_ui()
        self._load_schema_and_build_form()
        # Pflichtfelder visuell markieren (rot/gruen je nach Inhalt)
        self._mark_required_fields()
        # Optional: bestehenden Request laden
        if self._edit_request_id not in (None, ""):
            self.load_request(self._edit_request_id)
        self._wire_required_validation()
        self._check_required_fields()
        # initiale rot/gruen Markierung nach evtl. load_request
        self._update_required_styles()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header_title = (
            "Edit Experiment Request"
            if self._edit_request_id not in (None, "")
            else "Create Experiment Request"
        )
        header = HeaderBar(title=header_title, show_home=True, show_back=True)
        header.connect_home(self._go_home)
        header.connect_back(self._go_experiment_request)
        root.addWidget(header, 0)

        # Scrollbarer Center
        center = QFrame()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(18, 14, 18, 14)
        center_layout.setSpacing(12)

        title_text = (
            "Experiment Request (Edit)"
            if self._edit_request_id not in (None, "")
            else "Experiment Request"
        )

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        title = QLabel(title_text)
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        title_row.addWidget(title, 0, Qt.AlignVCenter)

        title_row.addStretch(1)

        # Image indicator (only visible if at least one image exists for this request)
        self.btn_show_images = QPushButton()
        self.btn_show_images.setObjectName("IconBtn")
        self.btn_show_images.setCursor(Qt.PointingHandCursor)
        self.btn_show_images.setFlat(True)
        self.btn_show_images.setToolTip("Show attached images")
        icon_path = resource_path("assets/images/picture.png")
        ico = QIcon(icon_path)
        if not ico.isNull():
            self.btn_show_images.setIcon(ico)
            self.btn_show_images.setIconSize(QSize(22, 22))
        else:
            # Fallback: small text, in case the icon file is missing in this build
            self.btn_show_images.setText("Images")
        self.btn_show_images.clicked.connect(self._open_images_dialog)
        self.btn_show_images.setVisible(False)
        title_row.addWidget(self.btn_show_images, 0, Qt.AlignVCenter)

        center_layout.addLayout(title_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        form_host = QWidget()
        self._form_layout = QFormLayout(form_host)
        self._form_layout.setContentsMargins(0, 0, 0, 0)
        self._form_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._form_layout.setFormAlignment(Qt.AlignTop)
        self._form_layout.setHorizontalSpacing(14)
        # kein Abstand zwischen den Feldern
        self._form_layout.setVerticalSpacing(0)
        scroll.setWidget(form_host)
        center_layout.addWidget(scroll, 1)

        # Actions
        actions = QHBoxLayout()
        actions.addStretch(1)

        self.btn_upload_images = QPushButton("Upload images")
        self.btn_upload_images.setMinimumHeight(34)
        self.btn_upload_images.clicked.connect(self._upload_images)
        actions.addWidget(self.btn_upload_images)

        self.btn_save = QPushButton("Save")
        # gleicher Style wie in screen_create_experiment.py
        self.btn_save.setObjectName("GreenBtn")
        self.btn_save.setMinimumHeight(34)
        self.btn_save.setEnabled(True)
        self.btn_save.clicked.connect(self._save)
        actions.addWidget(self.btn_save)

        center_layout.addLayout(actions)

        root.addWidget(center, 1)
        root.addWidget(FooterBar(), 0)

        # Initial state for the images indicator
        self._update_images_icon()

    
    def _request_has_images(self, request_id: Any) -> bool:
        """True if at least one image row exists for this request."""
        if request_id in (None, ""):
            return False
        try:
            with get_connection() as cn:
                cur = cn.cursor()
                # Works with the Access-to-MySQL translation layer in db.connection
                cur.execute(
                    "SELECT 1 FROM [tblExperimentRequestImage] WHERE [ExperimentRequestID]=? LIMIT 1",
                    [request_id],
                )
                return cur.fetchone() is not None
        except Exception:
            return False

    def _fetch_request_images(self, request_id: Any) -> List[Dict[str, str]]:
        """Returns dicts with FullPath + display name fields."""
        if request_id in (None, ""):
            return []
        rows: List[Dict[str, str]] = []
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(
                "SELECT [ID], [RelativePath], [StoredFilename], [OriginalFilename] "
                "FROM [tblExperimentRequestImage] "
                "WHERE [ExperimentRequestID]=? "
                "ORDER BY [ID] DESC",
                [request_id],
            )
            for img_id, rel_path, stored, orig_name in cur.fetchall() or []:
                rel_path = str(rel_path or "")
                stored = str(stored or "")
                orig_name = str(orig_name or "")
                full = os.path.join(rel_path, stored) if rel_path else stored
                rows.append(
                    {
                        "ID": img_id,
                        "RelativePath": rel_path,
                        "StoredFilename": stored,
                        "OriginalFilename": orig_name,
                        "FullPath": full,
                    }
                )
        return rows

    def _update_images_icon(self) -> None:
        """Show / hide the images icon depending on whether images exist."""
        btn = getattr(self, "btn_show_images", None)
        if not btn:
            return
        rid = self._edit_request_id
        btn.setVisible(self._request_has_images(rid))

    def _open_images_dialog(self) -> None:
        rid = self._edit_request_id
        if rid in (None, ""):
            return
        try:
            imgs = self._fetch_request_images(rid)
            if not imgs:
                QMessageBox.information(self, "Images", "No images attached to this request.")
                self._update_images_icon()
                return
            dlg = ExperimentRequestImagesDialog(
                self,
                title="Attached images",
                images=imgs,
                table_name="tblExperimentRequestImage",
                fk_field="ExperimentRequestID",
                fk_value=rid,
            )
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Images", str(e))

# ---------------- Images (ExperimentRequestImages + DB rows) ----------------

    @staticmethod
    def _current_user_id() -> Any | None:
        cu = getattr(app_meta, "current_user", {}) or {}
        return cu.get("id")

    def _request_images_dir(self, request_id: Any) -> str:
        """Gibt den Zielordner fuer Bilder eines Requests zurueck."""
        return os.path.join(REQUEST_IMAGES_BASE_DIR, str(request_id))

    def _request_images_relative_path_for_db(self, request_id: Any) -> str:
        """Gibt den Pfad so zurueck, wie er in RelativePath gespeichert werden soll."""
        # In der DB wollen wir den UNC-Pfad mit Backslashes und trailing Slash.
        return REQUEST_IMAGES_BASE_DIR + "\\" + str(request_id) + "\\"

    def _ensure_request_id_for_upload(self) -> Any:
        """Stellt sicher, dass es eine ExperimentRequestID gibt.

        Falls der Request noch nicht gespeichert ist, wird ein Datensatz erzeugt,
        aber explizit als "Draft" markiert (RequestStatus = NULL).

        Wichtig: Wir erzwingen hier *keine* Pflichtfeld-Validierung.
        """
        if self._edit_request_id not in (None, ""):
            return self._edit_request_id

        created_by = self._current_user_id()
        if created_by in (None, ""):
            raise RuntimeError(
                "CreatedBy/UserID konnte nicht ermittelt werden. Bitte neu anmelden."
            )

        # Wir sammeln aktuelle Formwerte (falls schon etwas ausgefuellt ist),
        # setzen aber RequestStatus bewusst auf NULL.
        values = self._collect_values(for_insert=True, request_status=None)

        # ID: falls GUID/Text → setzen, ansonsten weglassen (Autonumber)
        id_col = next((c for c in self._cols if c.name == "ID"), None)
        if id_col and _is_guid_col(id_col):
            values["ID"] = new_global_id()

        cols = [k for k, v in values.items() if v is not None]
        if not cols:
            # mindestens diese Felder setzen
            values["Timestamp"] = datetime.datetime.now()
            values["CreatedBy"] = created_by
            cols = ["Timestamp", "CreatedBy"]

        placeholders = ",".join(["?"] * len(cols))
        col_sql = ",".join([f"[{c}]" for c in cols])
        sql = f"INSERT INTO [{self._table}] ({col_sql}) VALUES ({placeholders})"
        params = [values[c] for c in cols]

        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(sql, params)
            # autocommit=True, aber wir lassen commit trotzdem laufen
            try:
                cn.commit()
            except Exception:
                pass

            # mysql-connector liefert lastrowid; unser CursorWrapper proxied das.
            new_id = getattr(cur, "lastrowid", None)

            # Fallback: über LAST_INSERT_ID() (pro Connection)
            if new_id in (None, 0, ""):
                try:
                    cur.execute("SELECT LAST_INSERT_ID()")
                    row = cur.fetchone()
                    if row and row[0] not in (None, 0, ""):
                        new_id = row[0]
                except Exception:
                    pass
            # Falls GUID als PK verwendet wird, haben wir die ID bereits gesetzt
            if new_id in (None, 0, "") and values.get("ID") is not None:
                new_id = values.get("ID")

        if new_id in (None, 0, ""):
            raise RuntimeError("ExperimentRequestID konnte nach dem Insert nicht ermittelt werden.")

        self._edit_request_id = new_id
        return new_id

    def _insert_experiment_request_image_row(
        self,
        *,
        request_id: Any,
        relative_path: str,
        stored_filename: str,
        original_filename: str,
    ) -> None:
        """Erzeugt einen Datensatz in tblExperimentRequestImage."""
        created_by = self._current_user_id()
        if created_by in (None, ""):
            raise RuntimeError("CreatedBy/UserID konnte nicht ermittelt werden.")

        sql = (
            "INSERT INTO [tblExperimentRequestImage] "
            "([ExperimentRequestID],[RelativePath],[StoredFilename],[OriginalFilename],[CreatedAt],[CreatedBy]) "
            "VALUES (?,?,?,?,?,?)"
        )
        params = [
            request_id,
            relative_path,
            stored_filename,
            original_filename,
            datetime.datetime.now(),
            created_by,
        ]
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(sql, params)
            try:
                cn.commit()
            except Exception:
                pass

    def _upload_images(self) -> None:
        """Button-Handler: Bilder waehlen, speichern, DB-Records anlegen."""
        try:
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "Select images",
                "",
                "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp *.heic *.heif);;All files (*.*)",
            )
            if not files:
                return

            request_id = self._ensure_request_id_for_upload()
            target_dir = self._request_images_dir(request_id)
            db_rel_path = self._request_images_relative_path_for_db(request_id)

            # Ordner erstellen
            try:
                os.makedirs(target_dir, exist_ok=True)
            except PermissionError as e:
                raise RuntimeError(
                    "[WinError 5] Zugriff verweigert beim Erstellen des Zielordners. "
                    "Das ist ein Berechtigungsproblem auf dem Share/NTFS.\n\n"
                    f"Pfad: {target_dir}\n\n"
                    "Please ensure that the Windows user (or the account running TrippleT) "
                    f"Schreibrechte auf {REQUEST_IMAGES_BASE_DIR} hat.\n\n"
                    f"Original-Fehler: {e}"
                )
            except Exception as e:
                raise RuntimeError(f"Zielordner konnte nicht erstellt werden: {target_dir}\n{e}")

            stored_any = 0
            errors: List[str] = []

            for src in files:
                try:
                    orig_name = os.path.basename(src)
                    _, ext = os.path.splitext(orig_name)
                    ext = ext or ""

                    stored_name = f"{uuid.uuid4().hex}{ext}"
                    dst = os.path.join(target_dir, stored_name)

                    # Kopieren (binary)
                    with open(src, "rb") as fsrc:
                        data = fsrc.read()
                    with open(dst, "wb") as fdst:
                        fdst.write(data)

                    # DB-Eintrag
                    self._insert_experiment_request_image_row(
                        request_id=request_id,
                        relative_path=db_rel_path,
                        stored_filename=stored_name,
                        original_filename=orig_name,
                    )

                    stored_any += 1
                except Exception as e:
                    errors.append(f"{os.path.basename(src)}: {e}")

            msg = f"{stored_any} image(s) uploaded."
            if errors:
                msg += "\n\nErrors:\n" + "\n".join(errors)
                QMessageBox.warning(self, "Upload finished with errors", msg)
            else:
                QMessageBox.information(self, "Upload finished", msg)

            # refresh indicator
            self._update_images_icon()

        except Exception as e:
            QMessageBox.critical(self, "Upload Error", str(e))

    def _load_schema_and_build_form(self):
        try:
            if not _table_exists(self._table):
                raise RuntimeError(f"Tabelle nicht gefunden: {self._table}")
            self._cols = _get_table_columns(self._table)
        except Exception as e:
            QMessageBox.critical(self, "DB Error", str(e))
            return

        for col in self._cols:
            if col.name in EXCLUDE_FIELDS:
                continue
            self._add_field_row(col)

        if not self._widgets:
            self._form_layout.addRow(QLabel("(Keine Felder gefunden)"), QLabel(""))

    # ---------------- Load existing request (Edit) ----------------

    def load_request(self, request_id: Any) -> None:
        """Laedt einen bestehenden Experiment Request und fuellt die Felder.

        request_id entspricht tblExperimentRequests.ID.
        """
        self._edit_request_id = request_id
        try:
            with get_connection() as cn:
                cur = cn.cursor()
                cur.execute(f"SELECT * FROM [{self._table}] WHERE [ID]=?", [request_id])
                row = cur.fetchone()
                if not row:
                    QMessageBox.warning(self, "Nicht gefunden", "Der gewaehlte Request wurde nicht gefunden.")
                    return
                col_names = [d[0] for d in (cur.description or [])]
        except Exception as e:
            QMessageBox.critical(self, "DB Error", str(e))
            return

        values = {str(col_names[i]): row[i] for i in range(len(col_names))}
        self._populate_fields(values)
        self._check_required_fields()
        self._update_images_icon()

    def _populate_fields(self, values: Dict[str, Any]) -> None:
        """Schreibt DB-Werte in die Widgets (nur im Formular sichtbare Felder)."""
        for field_name, w in self._widgets.items():
            if field_name not in values:
                continue
            v = values.get(field_name)

            if isinstance(w, QLineEdit):
                w.blockSignals(True)
                w.setText("" if v is None else str(v))
                w.blockSignals(False)
            elif isinstance(w, QTextEdit):
                w.blockSignals(True)
                w.setPlainText("" if v is None else str(v))
                w.blockSignals(False)
            elif isinstance(w, QComboBox):
                self._set_combo_by_data(w, v)
            elif isinstance(w, QDateEdit):
                # Access kann date oder datetime liefern
                try:
                    if v is None:
                        continue
                    if isinstance(v, datetime.datetime):
                        d = v.date()
                    elif isinstance(v, datetime.date):
                        d = v
                    else:
                        # Letzter Versuch: String parse
                        d = datetime.datetime.fromisoformat(str(v)).date()
                    w.blockSignals(True)
                    w.setDate(QDate(d.year, d.month, d.day))
                    w.blockSignals(False)
                except Exception:
                    pass

    def _find_widget(self, field_name: str) -> Optional[QWidget]:
        """Sucht ein Widget zu einem Feldnamen (robust gegen Access→MySQL).

        MySQL/SQLAlchemy/ODBC können Feldnamen anders liefern (Gross/Klein,
        Spaces/Underscores entfernen, Backticks, etc.). Damit Pflichtfeld-Checks
        und Collect/Save stabil bleiben, matchen wir mit einer Normalisierung.
        """
        # 1) direkter Treffer
        w = self._widgets.get(field_name)
        if w is not None:
            return w

        def norm(s: str) -> str:
            s = (s or "").strip().lower()
            # entferne typische SQL/ODBC-Zeichen und Trennzeichen
            s = s.replace("`", "").replace("[", "").replace("]", "")
            s = s.replace(" ", "").replace("_", "")
            return s

        target_raw = (field_name or "").strip()
        if not target_raw:
            return None

        target = norm(target_raw)

        # 2) normalisierte Suche
        for k, v in self._widgets.items():
            if norm(k) == target:
                return v

        # 3) häufige FK-Variante: <name> ↔ <name>ID
        if not target.endswith("id"):
            target_id = target + "id"
            for k, v in self._widgets.items():
                if norm(k) == target_id:
                    return v
        else:
            target_noid = target[:-2]
            for k, v in self._widgets.items():
                if norm(k) == target_noid:
                    return v

        return None

    @staticmethod
    def _set_combo_by_data(combo: QComboBox, data: Any) -> None:
        """Setzt currentIndex anhand itemData()."""
        combo.blockSignals(True)
        try:
            idx = -1
            for i in range(combo.count()):
                if combo.itemData(i) == data:
                    idx = i
                    break
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                # Falls Wert nicht in der Liste ist, auf leer setzen
                combo.setCurrentIndex(0)
        finally:
            combo.blockSignals(False)

    def _mark_required_fields(self) -> None:
        """Kennzeichnet Pflichtfelder visuell.

        Ziel: Rot, solange Feld leer ist; Gruen, sobald Inhalt vorhanden ist.

        Wichtig: Bei QTextEdit wird die sichtbare Eingabeflaeche im viewport()
        gerendert. Deshalb setzen wir den Border am viewport() (und schalten
        den Frame ab), damit wirklich *nur* die Textbox umrahmt ist.
        """

        # Initial einmal setzen
        self._update_required_styles()

    def _apply_required_border(self, w: QWidget, ok: bool) -> None:
        """Setzt den Border fuer ein Pflichtfeld (rot/gruen)."""
        color = "#2E7D32" if ok else "#8B0000"  # gruen / dunkelrot
        border_css = f"border: 1px solid {color};"

        if isinstance(w, QLineEdit):
            w.setStyleSheet(f"QLineEdit {{ {border_css} background: #ffffff; }}")
            return

        if isinstance(w, QTextEdit):
            # Frame weg, Border exakt um die sichtbare Flaeche
            w.setFrameStyle(QFrame.NoFrame)
            w.setStyleSheet("background: #ffffff;")
            w.viewport().setStyleSheet(f"QWidget {{ {border_css} background: #ffffff; }}")
            return

        if isinstance(w, QComboBox):
            w.setStyleSheet(
                f"QComboBox {{ {border_css} background: #ffffff; padding: 2px 6px; }}"
                "QComboBox QAbstractItemView { background: #ffffff; }"
            )
            return

        if isinstance(w, QDateEdit):
            w.setStyleSheet(f"QDateEdit {{ {border_css} background: #ffffff; padding: 2px 6px; }}")
            return

    def _update_required_styles(self) -> None:
        """Aktualisiert die Pflichtfeld-Rahmen (rot/gruen) basierend auf Inhalt."""
        wanted = [
            "Titel",
            # Versuchsgrund kann im Schema entweder Versuchsgrund oder FVersuchsgrund heissen
            "FVersuchsgrund",
            "Versuchsgrund",
            "Aufgabe",
            "Beurteilungsparameter",
            "Versuchsbedingungen",
        ]

        def has_content(w: QWidget | None) -> bool:
            if w is None:
                return False
            if isinstance(w, QLineEdit):
                return bool(w.text().strip())
            if isinstance(w, QTextEdit):
                return bool(w.toPlainText().strip())
            if isinstance(w, QComboBox):
                data = w.currentData()
                if data is not None and str(data).strip() != "":
                    return True
                return bool(w.currentText().strip())
            if isinstance(w, QDateEdit):
                return w.date().isValid()
            return False

        # Versuchsgrund nur einmal behandeln (egal welcher Name existiert)
        handled = set()
        for name in wanted:
            if name in ("FVersuchsgrund", "Versuchsgrund"):
                if "_VG_" in handled:
                    continue
                w = self._find_widget("FVersuchsgrund") or self._find_widget("Versuchsgrund")
                handled.add("_VG_")
            else:
                w = self._find_widget(name)
                handled.add(name)

            if w is None:
                continue
            self._apply_required_border(w, has_content(w))

    def _on_required_changed(self) -> None:
        """Wird bei Aenderungen in Pflichtfeldern aufgerufen."""
        self._check_required_fields()
        self._update_required_styles()

# ---------------- Validation (Save enable/disable) ----------------

    def _wire_required_validation(self) -> None:
        """Verdrahtet Signale so, dass der Save-Button erst aktiv wird,
        wenn die Pflichtfelder befüllt sind."""
        # Wir verbinden nur Widgets, die existieren.
        for fname in REQUIRED_FIELDS:
            w = self._find_widget(fname)
            if isinstance(w, QLineEdit):
                w.textChanged.connect(self._on_required_changed)
            elif isinstance(w, QTextEdit):
                w.textChanged.connect(self._on_required_changed)
            elif isinstance(w, QComboBox):
                w.currentIndexChanged.connect(self._on_required_changed)
            elif isinstance(w, QDateEdit):
                w.dateChanged.connect(self._on_required_changed)

    def _required_ok(self) -> bool:
        """True, wenn mind. Versuchsgrund/FVersuchsgrund, Aufgabe,
        Beurteilungsparameter und Versuchsbedingungen gefüllt sind."""
        # Versuchsgrund kann im Schema entweder Versuchsgrund oder FVersuchsgrund heissen
        vg_widget = self._find_widget("FVersuchsgrund") or self._find_widget("Versuchsgrund")

        def has_text(w: QWidget | None) -> bool:
            if w is None:
                return False
            if isinstance(w, QLineEdit):
                return bool(w.text().strip())
            if isinstance(w, QTextEdit):
                return bool(w.toPlainText().strip())
            if isinstance(w, QComboBox):
                # MySQL-Umstellung: Combos koennen Text anzeigen, ohne itemData/currentData zu setzen.
                data = w.currentData()
                if data is not None and str(data).strip() != "":
                    return True
                return bool(w.currentText().strip())
            if isinstance(w, QDateEdit):
                return w.date().isValid()
            return False

        return all(
            [
                has_text(self._find_widget("Titel")),
                has_text(vg_widget),
                has_text(self._find_widget("Aufgabe")),
                has_text(self._find_widget("Beurteilungsparameter")),
                has_text(self._find_widget("Versuchsbedingungen")),
            ]
        )

    def _check_required_fields(self) -> None:
        """Aktualisiert das Pflichtfeld-Feedback.

        Wichtig: Der Save-Button bleibt bewusst klickbar (MySQL/Lookups koennen sonst
        optisch gefuellt wirken, aber intern als 'leer' gelten). Die finale Validierung
        passiert in _save() mit einer klaren Fehlermeldung.
        """
        try:
            ok = self._required_ok()
        except Exception:
            ok = False

        # Button immer klickbar lassen; optional visuelles Feedback via Property.
        if hasattr(self, "btn_save") and self.btn_save:
            try:
                self.btn_save.setProperty("required_ok", bool(ok))
                self.btn_save.style().unpolish(self.btn_save)
                self.btn_save.style().polish(self.btn_save)
            except Exception:
                pass

        try:
            self._update_required_styles()
        except Exception:
            pass

    def _add_field_row(self, col: ColumnInfo):
        label = QLabel(col.name)
        label.setMinimumWidth(190)

        # Spezialfall: Projekt (Dropdown aus tblProject; gespeichert wird tblProject.ID)
        if col.name == 'Projekt':
            combo = QComboBox()
            combo.setMinimumHeight(28)
            combo.setStyleSheet(
                'QComboBox { background: #ffffff; border: 1px solid #8fbf8f; padding: 2px 6px; }'
                'QComboBox QAbstractItemView { background: #ffffff; }'
            )

            choices = self._load_project_choices()
            if choices:
                combo.addItem('', None)  # allow empty
                for _id, txt in choices:
                    combo.addItem(str(txt), _id)
                self._choices[col.name] = choices
                self._widgets[col.name] = combo
                self._form_layout.addRow(label, combo)
                return

            # Fallback: wenn tblProject/Spalten fehlen → einfache Textbox
            le = QLineEdit()
            le.setMinimumHeight(28)
            le.setStyleSheet('border: 1px solid #8fbf8f; background: #ffffff;')
            self._widgets[col.name] = le
            self._form_layout.addRow(label, le)
            return

        # Date field
        if col.name in DATE_FIELDS:
            w = QDateEdit()
            w.setCalendarPopup(True)
            w.setDisplayFormat("dd.MM.yyyy")
            w.setDate(QDate.currentDate())
            w.setMinimumHeight(28)
            self._widgets[col.name] = w
            self._form_layout.addRow(label, w)
            return

        # Multiline
        if col.name in MULTILINE_FIELDS:
            w = QTextEdit()
            w.setAcceptRichText(False)
            w.setTabChangesFocus(True)
            w.setStyleSheet("border: 1px solid #8fbf8f; background: #ffffff;")
            fm = QFontMetrics(w.font())
            # 3 Zeilen + etwas Padding
            w.setFixedHeight(int(fm.lineSpacing() * 3.2) + 14)
            self._widgets[col.name] = w
            self._form_layout.addRow(label, w)
            return

        # Foreign key heuristic: ...ID (aber nicht die Primär-ID, die wir ausblenden)
        if col.name.lower().endswith("id") and col.name != "ID":
            combo = QComboBox()
            combo.setMinimumHeight(28)
            combo.setStyleSheet(
                "QComboBox { background: #ffffff; border: 1px solid #8fbf8f; padding: 2px 6px; }"
                "QComboBox QAbstractItemView { background: #ffffff; }"
            )

            choices = self._load_fk_choices(col.name)
            if choices:
                combo.addItem("", None)  # allow empty
                for _id, txt in choices:
                    combo.addItem(str(txt), _id)
            else:
                # Fallback: keine Lookups gefunden → einfache Textbox
                le = QLineEdit()
                le.setMinimumHeight(28)
                le.setStyleSheet("border: 1px solid #8fbf8f; background: #ffffff;")
                self._widgets[col.name] = le
                self._form_layout.addRow(label, le)
                return

            self._choices[col.name] = choices
            self._widgets[col.name] = combo
            self._form_layout.addRow(label, combo)
            return

        # Default: single-line textbox
        le = QLineEdit()
        le.setMinimumHeight(28)
        le.setStyleSheet("border: 1px solid #8fbf8f; background: #ffffff;")
        self._widgets[col.name] = le
        self._form_layout.addRow(label, le)

    def _load_fk_choices(self, field_name: str) -> List[Tuple[Any, str]]:
        """Versucht für <X>ID eine Lookup-Tabelle zu finden und (id,label) zu laden."""
        table_cands = _try_tables_for_fk(field_name)
        target_table = next((t for t in table_cands if _table_exists(t)), None)
        if not target_table:
            return []

        display_col = _pick_display_column(target_table)
        if not display_col:
            return []

        # id spalte bestimmen
        cols = [c.name for c in _get_table_columns(target_table)]
        id_col = None
        for cand in ["ID", f"{field_name}"]:
            if cand in cols:
                id_col = cand
                break
        if not id_col:
            # first column ending with ID
            for c in cols:
                if c.lower().endswith("id"):
                    id_col = c
                    break
        if not id_col:
            return []

        sql = f"SELECT [{id_col}] AS _id, [{display_col}] AS _txt FROM [{target_table}] ORDER BY [{display_col}]"
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
        out: List[Tuple[Any, str]] = []
        for r in rows:
            out.append((r[0], r[1]))
        return out


    def _load_project_choices(self) -> List[Tuple[Any, str]]:
        """Lädt Projekte aus tblProject.

        Anzeige im Dropdown: "Project Number" + "Project Name".
        Gespeicherter Wert: tblProject.ID
        """
        table = "tblProject"
        if not _table_exists(table):
            return []

        cols_map = {c.name.lower(): c.name for c in _get_table_columns(table)}
        id_col = cols_map.get("id")
        num_col = cols_map.get("projectnumber") or cols_map.get("project number")
        name_col = cols_map.get("projectname") or cols_map.get("project name")
        if not (id_col and num_col and name_col):
            return []

        sql = (
            f"SELECT [{id_col}] AS _id, [{num_col}] AS _num, [{name_col}] AS _name "
            "FROM tblProject "
            f"ORDER BY [{num_col}], [{name_col}]"
        )
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(sql)
            rows = cur.fetchall()

        out: List[Tuple[Any, str]] = []
        for _id, num, name in rows:
            num_s = "" if num is None else str(num).strip()
            name_s = "" if name is None else str(name).strip()
            if num_s and name_s:
                label = f"{num_s} – {name_s}"
            else:
                label = num_s or name_s or str(_id)
            out.append((_id, label))
        return out

    def _collect_values(self, *, for_insert: bool, request_status: Any = 1) -> Dict[str, Any]:
        values: Dict[str, Any] = {}
        for col in self._cols:
            if col.name in EXCLUDE_FIELDS:
                continue
            w = self._widgets.get(col.name)
            if not w:
                continue

            if isinstance(w, QLineEdit):
                v = w.text().strip()
                values[col.name] = v if v != "" else None
            elif isinstance(w, QTextEdit):
                v = w.toPlainText().strip()
                values[col.name] = v if v != "" else None
            elif isinstance(w, QComboBox):
                data = w.currentData()
                if data is None or str(data).strip() == "":
                    txt = w.currentText().strip()
                    values[col.name] = txt if txt != "" else None
                else:
                    values[col.name] = data
            elif isinstance(w, QDateEdit):
                qd = w.date()
                # Access versteht i.d.R. Python datetime
                values[col.name] = qd.toPython()  # date
            else:
                # unknown widget
                values[col.name] = None

        if for_insert:
            # Auto-Felder nur beim Insert
            values["Timestamp"] = datetime.datetime.now()
            cu = getattr(app_meta, "current_user", {}) or {}
            values["CreatedBy"] = cu.get("id")

            # RequestStatus soll beim Erstellen automatisch gesetzt werden (nicht im Formular sichtbar)
            if any(c.name == "RequestStatus" for c in self._cols):
                values["RequestStatus"] = request_status

        return values

    def _save(self):
        # Generisches INSERT in tblExperimentRequests.
        try:
            # Pflichtfeld-Check (redundant zum disabled Button, aber sicher ist sicher)
            if not self._required_ok():
                missing: List[str] = []
                vg_widget = self._find_widget("FVersuchsgrund") or self._find_widget("Versuchsgrund")

                def has_text(w: QWidget | None) -> bool:
                    if w is None:
                        return False
                    if isinstance(w, QLineEdit):
                        return bool(w.text().strip())
                    if isinstance(w, QTextEdit):
                        return bool(w.toPlainText().strip())
                    if isinstance(w, QComboBox):
                        data = w.currentData()
                        if data is not None and str(data).strip() != "":
                            return True
                        return bool(w.currentText().strip())
                    if isinstance(w, QDateEdit):
                        return w.date().isValid()
                    return False

                checks = [
                    ("Titel", self._find_widget("Titel")),
                    ("Versuchsgrund", vg_widget),
                    ("Aufgabe", self._find_widget("Aufgabe")),
                    ("Beurteilungsparameter", self._find_widget("Beurteilungsparameter")),
                    ("Versuchsbedingungen", self._find_widget("Versuchsbedingungen")),
                ]
                for label, w in checks:
                    if not has_text(w):
                        missing.append(label)

                msg = "Please fill in at least title, reason for experiment, task, evaluation parameters and test conditions ausfüllen."
                if missing:
                    msg += "\n\nFehlt noch: " + ", ".join(missing)

                QMessageBox.warning(self, "Fehlende Angaben", msg)
                return

            is_insert = self._edit_request_id in (None, "")
            values = self._collect_values(for_insert=is_insert, request_status=1)

            # CreatedBy muss beim Insert vorhanden sein
            if is_insert and values.get("CreatedBy") in (None, ""):
                QMessageBox.critical(
                    self,
                    "Login fehlt",
                    "CreatedBy konnte nicht gesetzt werden, weil keine User-ID gefunden wurde. Bitte neu anmelden.",
                )
                return

            if is_insert:
                # ID: falls GUID/Text → setzen, ansonsten weglassen (Autonumber)
                id_col = next((c for c in self._cols if c.name == "ID"), None)
                if id_col and _is_guid_col(id_col):
                    values["ID"] = new_global_id()

                cols = [k for k, v in values.items() if v is not None]
                if not cols:
                    QMessageBox.warning(self, "Hinweis", "Keine Werte zum Speichern.")
                    return

                placeholders = ",".join(["?"] * len(cols))
                col_sql = ",".join([f"[{c}]" for c in cols])
                sql = f"INSERT INTO [{self._table}] ({col_sql}) VALUES ({placeholders})"
                params = [values[c] for c in cols]

                with get_connection() as cn:
                    cur = cn.cursor()
                    cur.execute(sql, params)
                    try:
                        cn.commit()
                    except Exception:
                        pass

                QMessageBox.information(self, "Gespeichert", "Experiment Request wurde gespeichert.")
                self._go_experiment_request()
            else:
                # UPDATE: nur sichtbare Felder schreiben (keine Auto-Felder)
                # Falls Feld leer ist (None), schreiben wir NULL.
                cols = [k for k in values.keys() if k not in ("ID",) and k in self._widgets]

                # Finales Speichern soll den Request "aktiv" machen.
                # Du verwendest RequestStatus=NULL als Draft und RequestStatus=1 als gespeichert.
                if any(c.name == "RequestStatus" for c in self._cols):
                    values["RequestStatus"] = 1
                    cols.append("RequestStatus")
                if not cols:
                    QMessageBox.warning(self, "Hinweis", "Keine Werte zum Speichern.")
                    return

                set_clause = ",".join([f"[{c}]=?" for c in cols])
                sql = f"UPDATE [{self._table}] SET {set_clause} WHERE [ID]=?"
                params = [values.get(c) for c in cols] + [self._edit_request_id]

                with get_connection() as cn:
                    cur = cn.cursor()
                    cur.execute(sql, params)
                    try:
                        cn.commit()
                    except Exception:
                        pass

                QMessageBox.information(self, "Gespeichert", "Experiment Request wurde aktualisiert.")
                self._go_experiment_request()

        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def _go_experiment_request(self):
        if callable(self.on_back_experiment_request):
            self.on_back_experiment_request()
        elif callable(self.on_back_home):
            # Fallback
            self.on_back_home()

    def _go_home(self):
        if callable(self.on_back_home):
            self.on_back_home()