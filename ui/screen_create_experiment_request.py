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
from db.connection import get_connection
from db import experiment_request_changes as request_changes
from ui.pathutil import resource_path
from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from ui.widgets.experiment_request_help_dialog import show_experiment_request_help

import datetime
import shutil
from ui.widgets.friendly_error import show_error


# Form constants, schema/FK helpers, load/save and the image storage rules live
# Qt-free in db/experiment_requests.py and db/experiment_request_images.py
# (shared with the web app); re-exported here under their old names.
from db import experiment_requests as er
from db import experiment_request_images as er_images
from db.experiment_requests import (  # noqa: F401  (re-exported)
    EXCLUDE_FIELDS,
    MULTILINE_FIELDS,
    DATE_FIELDS,
    REQUIRED_FIELDS,
    ColumnInfo,
)
from db.experiment_request_images import REQUEST_IMAGES_BASE_DIR  # noqa: F401  (re-exported)


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

        # UserID -> short username (e.g. "soj"), for the owner badge next to
        # each filename in the list. Best-effort - a missing/failed lookup
        # just means no badge, never breaks the viewer.
        try:
            from db.user_directory import load_user_id_to_username
            self._owner_names = load_user_id_to_username()
        except Exception:
            self._owner_names = {}

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

    def _make_owner_row_widget(
        self, display_name: str, img: Dict[str, Any], item: QListWidgetItem
    ) -> QWidget:
        """Row widget for the file list: filename + a small owner badge
        (short username, e.g. "soj") right-aligned, if CreatedBy is known.

        WA_TransparentForMouseEvents is needed because setItemWidget()
        would otherwise intercept clicks on the row before they trigger
        normal item selection (currentItemChanged/itemSelectionChanged) -
        this keeps the row clickable like a normal list item."""
        w = QWidget()
        w.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 2, 6, 2)
        lay.setSpacing(6)

        lbl = QLabel(display_name)
        lbl.setTextFormat(Qt.PlainText)
        lay.addWidget(lbl, 1)

        owner_id = img.get("CreatedBy")
        owner_name = None
        if owner_id not in (None, ""):
            owner_name = self._owner_names.get(owner_id) or self._owner_names.get(str(owner_id))
        if owner_name:
            badge = QLabel(owner_name)
            badge.setStyleSheet(
                "background: #55606e; color: #f0f2f5; border-radius: 8px; "
                "padding: 1px 7px; font-size: 10px; font-weight: 600;"
            )
            lay.addWidget(badge, 0, Qt.AlignVCenter)
            item.setToolTip(f"Uploaded by {owner_name}")

        return w


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
                row_widget = self._make_owner_row_widget(disp, img, item)
                item.setSizeHint(row_widget.sizeHint())
                self.lst.setItemWidget(item, row_widget)

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

    def _current_access_level(self) -> int:
        try:
            return int((app_meta.current_user or {}).get("access_level") or 0)
        except Exception:
            return 0

    def _current_user_id(self) -> Any | None:
        try:
            return (app_meta.current_user or {}).get("id")
        except Exception:
            return None

    def _can_delete(self, img: Dict[str, Any]) -> bool:
        """Only the owner (CreatedBy) or a superuser (AccessLevel >= 4) may delete
        (rule in db/experiment_request_images.can_delete)."""
        return er_images.can_delete(app_meta.current_user or {}, img)

    def _update_delete_button(self) -> None:
        """Enable/disable delete button based on selection and delete permission."""
        try:
            btn = getattr(self, "btn_delete", None)
            if not btn:
                return
            selected = self.lst.selectedItems()
            can_delete_all = bool(selected) and all(
                self._can_delete(it.data(Qt.UserRole) or {}) for it in selected
            )
            btn.setEnabled(can_delete_all)
            if selected and not can_delete_all:
                btn.setToolTip("You can only delete your own uploads (or need superuser rights).")
            else:
                btn.setToolTip("")
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
            QMessageBox.warning(self, "Save As", "File not found:\n" + src)
            return

        orig = str(d.get("OriginalFilename") or os.path.basename(src))
        dst, _ = QFileDialog.getSaveFileName(self, "Save As", orig)
        if not dst:
            return
        try:
            import shutil
            shutil.copy2(src, dst)
        except Exception as e:
            show_error(self, "Save As", "The file could not be saved.", e)

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

        # Only the owner or a superuser (AccessLevel >= 4) may delete - also
        # reachable via the Delete key (keyPressEvent), not just the button,
        # hence checked here instead of only in _update_delete_button.
        denied = [it for it in items if not self._can_delete(it.data(Qt.UserRole) or {})]
        items = [it for it in items if self._can_delete(it.data(Qt.UserRole) or {})]
        if not items:
            QMessageBox.warning(
                self,
                "Delete",
                "You can only delete your own uploads (or need superuser rights).",
            )
            return

        if not self._confirm_delete(len(items)):
            return

        errors: List[str] = []
        if denied:
            errors.append(
                f"{len(denied)} file(s) skipped: you can only delete your own uploads "
                "(or need superuser rights)."
            )

        # Delete in reverse row order. DB row first, file second, folder
        # cleanup when nothing remains - see
        # db/experiment_request_images.delete_image_records().
        ordered = sorted(items, key=lambda it: self.lst.row(it), reverse=True)
        ordered_imgs = [it.data(Qt.UserRole) or {} for it in ordered]
        deleted = er_images.delete_image_records(
            self._table_name, self._fk_field, self._fk_value, ordered_imgs, errors)
        deleted_ids = {id(d) for d in deleted}

        # Remove from in-memory list + UI (nur nach bestätigtem DB-Delete)
        for item, img in zip(ordered, ordered_imgs):
            if id(img) not in deleted_ids:
                continue  # Eintrag bleibt in der Liste sichtbar
            rel_path = str(img.get("RelativePath") or "")
            stored = str(img.get("StoredFilename") or img.get("StoredFile") or "")
            full_path = str(img.get("FullPath") or (os.path.join(rel_path, stored) if rel_path else stored))
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
        ext = er_images.fixed_extension(img)

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

        # Typed extension dropped, fixed one appended, slashes sanitized
        # (db/experiment_request_images.new_original_filename).
        new_name = er_images.new_original_filename(img, new_base)
        if new_name is None:
            return

        # Snapshot selection so we can rebuild/re-sort the list and keep focus.
        selected_full_path = str(img.get("FullPath") or "")

        try:
            # UPDATE + read back (rowcount may be 0 or -1 even when it worked).
            if not er_images.persist_original_filename(
                    self._table_name, self._fk_field, self._fk_value, img, new_name):
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

# Moved to db/experiment_requests.py (old names kept for importers, e.g. the
# read-only request popup in ui/screen_show_experiment.py).
_try_tables_for_fk = er.try_tables_for_fk
_pick_display_column = er.pick_display_column
_get_table_columns = er.get_table_columns
_table_exists = er.table_exists_info
_is_guid_col = er.is_guid_col


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

    def _make_owner_row_widget(
        self, display_name: str, d: Dict[str, Any], item: QListWidgetItem
    ) -> QWidget:
        """Row widget for the file list: filename + a small owner badge
        (short username, e.g. "soj") right-aligned, if CreatedBy is known.

        WA_TransparentForMouseEvents is needed because setItemWidget()
        would otherwise intercept clicks on the row before they trigger
        normal item selection (currentItemChanged/itemSelectionChanged) -
        this keeps the row clickable like a normal list item."""
        w = QWidget()
        w.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 2, 6, 2)
        lay.setSpacing(6)

        lbl = QLabel(display_name)
        lbl.setTextFormat(Qt.PlainText)
        lay.addWidget(lbl, 1)

        owner_id = d.get("CreatedBy")
        owner_name = None
        if owner_id not in (None, ""):
            owner_name = self._owner_names.get(owner_id) or self._owner_names.get(str(owner_id))
        if owner_name:
            badge = QLabel(owner_name)
            badge.setStyleSheet(
                "background: #55606e; color: #f0f2f5; border-radius: 8px; "
                "padding: 1px 7px; font-size: 10px; font-weight: 600;"
            )
            lay.addWidget(badge, 0, Qt.AlignVCenter)
            item.setToolTip(f"Uploaded by {owner_name}")

        return w

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

        # UserID -> short username (e.g. "soj"), for the owner badge next to
        # each filename in the list. Best-effort - a missing/failed lookup
        # just means no badge, never breaks the viewer.
        try:
            from db.user_directory import load_user_id_to_username
            self._owner_names = load_user_id_to_username()
        except Exception:
            self._owner_names = {}

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
                row_widget = self._make_owner_row_widget(name, d, item)
                item.setSizeHint(row_widget.sizeHint())
                self.lst.setItemWidget(item, row_widget)
                if select_full_path and str(d.get("FullPath") or "") == select_full_path:
                    sel_row = i
        finally:
            self.lst.blockSignals(False)

        if self.lst.count() > 0:
            self.lst.setCurrentRow(min(sel_row, self.lst.count() - 1))

    def _current_access_level(self) -> int:
        try:
            return int((app_meta.current_user or {}).get("access_level") or 0)
        except Exception:
            return 0

    def _current_user_id(self) -> Any | None:
        try:
            return (app_meta.current_user or {}).get("id")
        except Exception:
            return None

    def _can_delete(self, d: Dict[str, Any]) -> bool:
        """Only the owner (CreatedBy) or a superuser (AccessLevel >= 4) may delete."""
        if self._current_access_level() >= 4:
            return True
        owner_id = d.get("CreatedBy")
        uid = self._current_user_id()
        return owner_id not in (None, "") and uid not in (None, "") and str(owner_id) == str(uid)

    def _update_delete_button(self) -> None:
        selected = self.lst.selectedItems()
        can_delete_all = bool(selected) and all(
            self._can_delete(it.data(Qt.UserRole) or {}) for it in selected
        )
        self.btn_delete.setEnabled(can_delete_all)
        if selected and not can_delete_all:
            self.btn_delete.setToolTip("You can only delete your own uploads (or need superuser rights).")
        else:
            self.btn_delete.setToolTip("")

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
            QMessageBox.warning(self, "Save As", "File not found:\n" + src)
            return

        orig = str(d.get("OriginalFilename") or os.path.basename(src))
        dst, _ = QFileDialog.getSaveFileName(self, "Save As", orig, "PDF files (*.pdf);;All files (*)")
        if not dst:
            return
        try:
            import shutil
            shutil.copy2(src, dst)
        except Exception as e:
            show_error(self, "Save As", "The file could not be saved.", e)

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
            lbl = QLabel("The PDF could not be shown.")
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
            lbl = QLabel("The PDF could not be loaded.")
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
            lbl = QLabel("The PDF could not be shown.")
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

        # Only the owner or a superuser (AccessLevel >= 4) may delete - also
        # reachable via the Delete key, not just the button.
        denied = [it for it in items if not self._can_delete(it.data(Qt.UserRole) or {})]
        items = [it for it in items if self._can_delete(it.data(Qt.UserRole) or {})]
        if not items:
            QMessageBox.warning(
                self,
                "Delete",
                "You can only delete your own uploads (or need superuser rights).",
            )
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
        if denied:
            errors.append(
                f"{len(denied)} file(s) skipped: you can only delete your own uploads "
                "(or need superuser rights)."
            )
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
        prefix = (getattr(self, "txt_prefix", None).text() if getattr(self, "txt_prefix", None) else "")
        # Fixed extension, optional prefix, sanitizing:
        # db/experiment_request_images.new_original_filename().
        new_name = er_images.new_original_filename(
            img, self.txt_new.text(), prefix=prefix, fallback_ext=self._ext)
        if new_name is None:
            QMessageBox.warning(self, "Rename", "Name cannot be empty.")
            return

        try:
            if not er_images.persist_original_filename(
                    self._table_name, self._fk_field, self._fk_value, img, new_name):
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

    def __init__(self, on_back_home=None, on_back_experiment_request=None, request_id: Any | None = None,
                 sidebar_callbacks: Optional[dict] = None):
        super().__init__()
        self.on_back_home = on_back_home
        self.on_back_experiment_request = on_back_experiment_request
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None

        # Wenn gesetzt, wird ein bestehender Request geladen und beim Speichern per UPDATE gespeichert.
        self._edit_request_id: Any | None = request_id

        # Snapshot der beim Laden vorgefundenen Feldwerte (fuer den "wurde
        # ueberhaupt etwas geaendert?"-Check beim Speichern), siehe load_request().
        self._loaded_values: Dict[str, Any] = {}
        # Falls die aktuell editierte Zeile selbst schon eine Aenderungs-Kopie
        # ist (ChangeOfRequestID gesetzt): deren Original-ID, sonst None.
        self._change_of_id: Any | None = None

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

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring). Der frühere
        # Header-Titel ("Create"/"Edit Experiment Request") entfällt
        # ersatzlos - das in-page `title`-Label weiter unten zeigt bereits
        # dieselbe Information. Der Header-Back-Button lebt als kontextueller
        # Back-Chip weiter (gleiches Muster wie ShowExperimentScreen).
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

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

        # Sowohl Bearbeiten als auch Neuanlage fuehren zurueck zu "My
        # Requests" - der Experiment-Request-Hub ist seit 2026-09-04 nirgends
        # mehr verlinkt (siehe main.py::_go_edit_experiment_request()/
        # _go_create_experiment_request()).
        self.btn_back_chip = QPushButton("← My Requests")
        self.btn_back_chip.setCursor(Qt.PointingHandCursor)
        self.btn_back_chip.setStyleSheet(
            "QPushButton{background:transparent;color:#39a650;border:1px solid #39a650;"
            "border-radius:4px;padding:5px 10px;font-weight:600;}"
            "QPushButton:hover{background:#e8f5e9;}"
        )
        self.btn_back_chip.clicked.connect(self._go_experiment_request)
        self.btn_back_chip.setVisible(callable(self.on_back_experiment_request))
        title_row.addWidget(self.btn_back_chip, 0, Qt.AlignVCenter)

        title = QLabel(title_text)
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        title_row.addWidget(title, 0, Qt.AlignVCenter)

        # Kontext-Hilfe (Lebenszyklus-Diagramm), Nutzerwunsch 2026-08-31:
        # nicht dauerhaft sichtbar, nur ein kleiner Trigger daneben. Icon
        # statt "?"-Text seit 2026-09-04 (Nutzerwunsch: schlicht, aber gut
        # erkennbar - Fallback auf "?" falls die PNG mal fehlt).
        self.btn_help = QPushButton()
        self.btn_help.setCursor(Qt.PointingHandCursor)
        self.btn_help.setFixedSize(26, 26)
        self.btn_help.setToolTip("Wie funktionieren Experiment Requests?")
        self.btn_help.setStyleSheet(
            "QPushButton{background:transparent;border:1px solid #39a650;"
            "border-radius:13px;padding:0;}"
            "QPushButton:hover{background:#e8f5e9;}"
        )
        help_icon = QIcon(resource_path("assets/images/help_tour.png"))
        if not help_icon.isNull():
            self.btn_help.setIcon(help_icon)
            self.btn_help.setIconSize(QSize(16, 16))
        else:
            self.btn_help.setText("?")
            self.btn_help.setStyleSheet(
                self.btn_help.styleSheet() + "QPushButton{color:#39a650;font-size:14px;font-weight:700;}"
            )
        self.btn_help.clicked.connect(self._open_help)
        title_row.addWidget(self.btn_help, 0, Qt.AlignVCenter)

        # Version-Historie direkt im Formular oeffenbar (Nutzerwunsch
        # 2026-09-04), nicht nur ueber das Kontextmenu in "My Requests" -
        # gleiche Logik/Dialog (ui/widgets/experiment_request_version_history.py).
        # Nur sichtbar wenn tatsaechlich Versionen existieren, siehe load_request().
        self.btn_history = QPushButton("History…")
        self.btn_history.setCursor(Qt.PointingHandCursor)
        self.btn_history.setStyleSheet(
            "QPushButton{background:transparent;color:#39a650;border:1px solid #39a650;"
            "border-radius:4px;padding:5px 10px;font-weight:600;}"
            "QPushButton:hover{background:#e8f5e9;}"
        )
        self.btn_history.clicked.connect(self._open_version_history)
        self.btn_history.setVisible(False)
        title_row.addWidget(self.btn_history, 0, Qt.AlignVCenter)

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

        # Denial-Banner (nur sichtbar bei RequestStatus=Denied + gesetztem
        # DenialReason, siehe load_request()) - reine Anzeige, kein Formularfeld.
        self._lbl_denial_banner = QLabel()
        self._lbl_denial_banner.setWordWrap(True)
        self._lbl_denial_banner.setStyleSheet(
            "background:#fdecea;color:#611a15;border:1px solid #f5c6cb;"
            "border-radius:4px;padding:8px 12px;font-size:12px;"
        )
        self._lbl_denial_banner.setVisible(False)
        center_layout.addWidget(self._lbl_denial_banner)

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

        content_layout.addWidget(center, 1)
        root.addWidget(FooterBar(), 0)

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
        try:
            self._refresh_sidebar()
        except Exception:
            pass
        super().showEvent(event)

        # Initial state for the images indicator
        self._update_images_icon()

    
    def _request_has_images(self, request_id: Any) -> bool:
        """True if at least one image row exists for this request."""
        return er_images.has_images(request_id)

    def _fetch_request_images(self, request_id: Any) -> List[Dict[str, str]]:
        """Returns dicts with FullPath + display name fields."""
        return er_images.list_images(request_id)

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
        return er_images.images_dir(request_id)

    def _request_images_relative_path_for_db(self, request_id: Any) -> str:
        """Gibt den Pfad so zurueck, wie er in RelativePath gespeichert werden soll."""
        return er_images.relative_path_for_db(request_id)

    def _ensure_request_id_for_upload(self) -> Any:
        """Stellt sicher, dass es eine ExperimentRequestID gibt.

        Falls der Request noch nicht gespeichert ist, wird ein Datensatz erzeugt,
        aber explizit als "Draft" markiert (RequestStatus = NULL) - ohne
        Pflichtfeld-Validierung (db/experiment_request_images.ensure_request_for_upload).
        """
        if self._edit_request_id not in (None, ""):
            return self._edit_request_id
        new_id = er_images.ensure_request_for_upload(
            app_meta.current_user or {}, None, self._collect_values(for_insert=False), self._cols)
        self._edit_request_id = new_id
        return new_id

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
            # Ordner erstellen (RuntimeError mit Erklaerung, falls nicht moeglich)
            target_dir = er_images.prepare_folder(request_id)

            stored_any = 0
            errors: List[str] = []

            for src in files:
                try:
                    with open(src, "rb") as fsrc:
                        data = fsrc.read()
                    # Datei unter zufaelligem Namen + DB-Eintrag
                    er_images.store_image(app_meta.current_user or {}, request_id, data,
                                          os.path.basename(src), target_dir)
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
            self._cols = er.load_columns(self._table)
        except Exception as e:
            QMessageBox.critical(self, "DB Error", str(e))
            return

        # Field types + dropdown choices: db/experiment_requests.form_fields()
        for fld in er.form_fields(self._cols):
            self._add_field_row(fld)

        if not self._widgets:
            self._form_layout.addRow(QLabel("(No fields found)"), QLabel(""))

    # ---------------- Load existing request (Edit) ----------------

    def load_request(self, request_id: Any) -> None:
        """Laedt einen bestehenden Experiment Request und fuellt die Felder.

        request_id entspricht tblExperimentRequests.ID.
        """
        self._edit_request_id = request_id
        try:
            values = er.fetch_request(request_id)
            if values is None:
                QMessageBox.warning(self, "Not found", "The selected request was not found.")
                return
        except Exception as e:
            QMessageBox.critical(self, "DB Error", str(e))
            return

        self._change_of_id = values.get("ChangeOfRequestID")
        self._populate_fields(values)
        # Snapshot NACH _populate_fields, damit die Widgets schon befuellt sind -
        # _collect_values() liest aus den Widgets, das muss beim Diff-Vergleich
        # in _save() exakt dieselbe Normalisierung durchlaufen wie der aktuelle
        # Formularinhalt (z.B. Datum ueber QDateEdit statt Roh-DB-Typ).
        self._loaded_values = self._collect_values(for_insert=False)
        self._check_required_fields()
        self._update_images_icon()

        try:
            self.btn_history.setVisible(request_changes.has_versions(request_id))
        except Exception:
            self.btn_history.setVisible(False)

        banner = er.denial_banner_text(values)
        if banner:
            self._lbl_denial_banner.setText(banner)
            self._lbl_denial_banner.setVisible(True)
        else:
            self._lbl_denial_banner.setVisible(False)

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
        """True, wenn mind. Titel, Versuchsgrund/FVersuchsgrund, Aufgabe,
        Beurteilungsparameter und Versuchsbedingungen gefüllt sind
        (db/experiment_requests.validate)."""
        return not er.validate(self._collect_values(for_insert=False))

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

    def _add_field_row(self, fld: Dict[str, Any]):
        """Widget for one field of er.form_fields() (type fk/date/multiline/text)."""
        name = fld["name"]
        label = QLabel(fld["label"])
        label.setMinimumWidth(190)

        if fld["type"] == "fk":
            # Dropdown (Projekt: tblProject, gespeichert wird tblProject.ID;
            # sonst ...ID-Spalten ueber die tblX-Lookup-Heuristik)
            combo = QComboBox()
            combo.setMinimumHeight(28)
            combo.setStyleSheet(
                "QComboBox { background: #ffffff; border: 1px solid #8fbf8f; padding: 2px 6px; }"
                "QComboBox QAbstractItemView { background: #ffffff; }"
            )
            choices = fld["choices"]
            combo.addItem("", None)  # allow empty
            for _id, txt in choices:
                combo.addItem(str(txt), _id)
            self._choices[name] = choices
            self._widgets[name] = combo
            self._form_layout.addRow(label, combo)
            return

        # Date field
        if fld["type"] == "date":
            w = QDateEdit()
            w.setCalendarPopup(True)
            w.setDisplayFormat("dd.MM.yyyy")
            w.setDate(QDate.currentDate())
            w.setMinimumHeight(28)
            self._widgets[name] = w
            self._form_layout.addRow(label, w)
            return

        # Multiline
        if fld["type"] == "multiline":
            w = QTextEdit()
            w.setAcceptRichText(False)
            w.setTabChangesFocus(True)
            w.setStyleSheet("border: 1px solid #8fbf8f; background: #ffffff;")
            fm = QFontMetrics(w.font())
            # 3 Zeilen + etwas Padding
            w.setFixedHeight(int(fm.lineSpacing() * 3.2) + 14)
            self._widgets[name] = w
            self._form_layout.addRow(label, w)
            return

        # Default (auch FK/Projekt ohne Lookup-Tabelle): single-line textbox
        le = QLineEdit()
        le.setMinimumHeight(28)
        le.setStyleSheet("border: 1px solid #8fbf8f; background: #ffffff;")
        self._widgets[name] = le
        self._form_layout.addRow(label, le)

    def _load_fk_choices(self, field_name: str) -> List[Tuple[Any, str]]:
        """Versucht für <X>ID eine Lookup-Tabelle zu finden und (id,label) zu laden."""
        return er.load_fk_choices(field_name)

    def _load_project_choices(self) -> List[Tuple[Any, str]]:
        """Lädt Projekte aus tblProject ("Nummer – Name", Wert tblProject.ID)."""
        return er.load_project_choices()

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
            # Auto-Felder nur beim Insert (Timestamp, CreatedBy, RequestStatus)
            values = er.with_auto_fields(app_meta.current_user or {}, self._cols, values, request_status)

        return values

    def _has_unsaved_changes(self, values: Dict[str, Any]) -> bool:
        """True, wenn sich mindestens ein Feld gegenueber dem beim Laden
        vorgefundenen Stand (self._loaded_values, siehe load_request())
        geaendert hat. Ohne Snapshot (z.B. brandneuer Request) immer True."""
        return er.has_changes(values, self._loaded_values, list(self._widgets))

    def _save(self):
        # Decision tree (insert / unchanged / direct update / change proposal):
        # db/experiment_requests.save_request().
        try:
            res = er.save_request(
                app_meta.current_user or {},
                self._edit_request_id,
                self._collect_values(for_insert=False),
                cols=self._cols,
                field_names=list(self._widgets),
                loaded_values=self._loaded_values,
                change_of_id=self._change_of_id,
            )
            if res.kind == "invalid":
                QMessageBox.warning(self, res.title, res.message)
                return
            if res.kind == "no_user":
                QMessageBox.critical(self, res.title, res.message)
                return
            if res.kind == "nothing":
                QMessageBox.warning(self, res.title, res.message)
                return
            if res.kind != "unchanged":
                QMessageBox.information(self, res.title, res.message)
            self._go_experiment_request()

        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def _go_experiment_request(self):
        if callable(self.on_back_experiment_request):
            self.on_back_experiment_request()
        elif callable(self.on_back_home):
            # Fallback
            self.on_back_home()

    def _open_help(self):
        show_experiment_request_help(self)

    def _open_version_history(self):
        if self._edit_request_id in (None, ""):
            return
        from ui.widgets.experiment_request_version_history import show_version_history
        show_version_history(self, self._edit_request_id)

    def _go_home(self):
        if callable(self.on_back_home):
            self.on_back_home()