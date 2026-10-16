import os
import shutil
import datetime
from typing import List, Dict, Optional, Callable, Set

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QScrollArea, QFormLayout, QLabel,
    QLineEdit, QCheckBox, QComboBox, QHBoxLayout, QPushButton, QMessageBox,
    QSizePolicy, QTabWidget, QListWidget, QListWidgetItem, QFileDialog,
    QAbstractItemView, QSplitter, QTextBrowser
)
from PySide6.QtGui import QPixmap

from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from ui.text_normalize import canon_simple as _canon
from ui.widgets.friendly_error import show_error


# ── File storage ─────────────────────────────────────────────────────────────
def _top_plate_files_root() -> str:
    try:
        from db.connection import is_dev_mode
        if is_dev_mode():
            return "C:\\ttt\\TopPlateFiles"
    except Exception:
        pass
    return "H:\\Technik\\TrippleT\\TopPlateFiles"

_FILE_ICONS = {
    ".pdf":  "📄",
    ".png":  "🖼",
    ".jpg":  "🖼",
    ".jpeg": "🖼",
    ".bmp":  "🖼",
    ".tif":  "🖼",
    ".tiff": "🖼",
    ".docx": "📝",
    ".xlsx": "📊",
}

def _file_icon(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return _FILE_ICONS.get(ext, "📎")


class NewTopPlateScreen(QWidget):
    """
    Dynamisches Formular mit zwei gleich breiten Spalten.
    - ID wird nur informativ angezeigt.
    - GlobalID wird nicht angezeigt und im Backend gesetzt.
    - Kann für "New" (leeres Formular) und "Copy" (vorbefüllt) verwendet werden.
    - Validierung:
        * Feld 'Name' muss ausgefüllt sein.
        * Feld 'Name' darf in tblTopPlates noch nicht existieren.
    """

    def __init__(
        self,
        columns: List[str],
        fk_maps: Dict[str, Dict],
        bool_columns: Optional[Set[str]] = None,
        id_column: str = "ID",
        on_back_home: Optional[Callable[[], None]] = None,
        on_save: Optional[Callable[[Dict], int]] = None,
        on_created: Optional[Callable[[int], None]] = None,
        check_top_plate_name: Optional[Callable[[str], bool]] = None,
        sidebar_callbacks: Optional[dict] = None,
    ):
        super().__init__()
        self.columns = columns or []
        self.fk_maps = fk_maps or {}
        self.bool_columns = set(bool_columns or set())
        self.id_column = id_column or "ID"
        self.on_back_home = on_back_home
        self._on_save = on_save
        self._on_created = on_created
        self._check_top_plate_name = check_top_plate_name
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None

        # Spaltenname -> Editor-Widget
        self._editors: Dict[str, QWidget] = {}
        self._current_top_plate_id: Optional[int] = None
        self._read_only = False

        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring). Die frühere
        # "kein Home-Button"-Begründung betraf nur den TopBar-Home-Button -
        # Cancel/Save bleiben weiterhin der primäre Navigationsweg aus diesem
        # Formular heraus.
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        # ── Tab-Widget ────────────────────────────────────────────────────
        self._tabs = QTabWidget()

        # ── Tab 1: Fields ─────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        center = QWidget()

        main_layout = QHBoxLayout(center)
        main_layout.setContentsMargins(32, 24, 32, 24)
        main_layout.setSpacing(32)

        left_widget = QWidget()
        right_widget = QWidget()
        left_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        right_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        left_form = QFormLayout(left_widget)
        right_form = QFormLayout(right_widget)
        for frm in (left_form, right_form):
            frm.setContentsMargins(0, 0, 0, 0)
            frm.setHorizontalSpacing(24)
            frm.setVerticalSpacing(10)

        main_layout.addWidget(left_widget, 1)
        main_layout.addWidget(right_widget, 1)

        _HIDDEN_COLS = {"globalid", "has_files"}
        visible_cols = [col for col in self.columns if col.lower() not in _HIDDEN_COLS]
        total = len(visible_cols)
        split = (total + 1) // 2

        for i, col in enumerate(visible_cols):
            target_form = left_form if i < split else right_form
            if col.lower() == self.id_column.lower():
                lbl = QLabel("Wird automatisch vergeben")
                lbl.setStyleSheet("color: #666666; font-style: italic;")
                target_form.addRow(QLabel(col + ":"), lbl)
                continue
            widget = self._create_editor_for_column(col)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self._editors[col] = widget
            target_form.addRow(QLabel(col + ":"), widget)

        scroll.setWidget(center)
        fields_widget = QWidget()
        fields_lay = QVBoxLayout(fields_widget)
        fields_lay.setContentsMargins(0, 0, 0, 0)
        fields_lay.addWidget(scroll)
        self._tabs.addTab(fields_widget, "Fields")

        # ── Tab 2: Files ──────────────────────────────────────────────────
        files_widget = QWidget()
        files_outer = QVBoxLayout(files_widget)
        files_outer.setContentsMargins(12, 10, 12, 10)
        files_outer.setSpacing(6)

        files_info = QLabel("Files attached to this top plate (images, PDFs, documents).")
        files_info.setStyleSheet("color:#666; font-size:11px;")
        files_outer.addWidget(files_info)

        # Splitter: Liste links, Vorschau rechts
        splitter = QSplitter(Qt.Horizontal)

        # ── Links: Dateiliste + Buttons ───────────────────────────────
        list_widget = QWidget()
        list_lay = QVBoxLayout(list_widget)
        list_lay.setContentsMargins(0, 0, 0, 0)
        list_lay.setSpacing(6)

        self._file_list = QListWidget()
        self._file_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._file_list.setAlternatingRowColors(True)
        self._file_list.setMinimumHeight(160)
        self._file_list.itemClicked.connect(self._on_file_selected)
        self._file_list.itemDoubleClicked.connect(self._open_file)
        list_lay.addWidget(self._file_list, 1)

        file_btn_row = QHBoxLayout()
        self.btn_upload_file = QPushButton("Upload File…")
        self.btn_upload_file.setObjectName("GreenBtn")
        self.btn_upload_file.clicked.connect(self._upload_file)
        btn_open = QPushButton("Open")
        btn_open.setObjectName("GreyBtn")
        btn_open.clicked.connect(lambda: self._open_file(self._file_list.currentItem()))
        self.btn_delete_file = QPushButton("Delete")
        self.btn_delete_file.setObjectName("GreyBtn")
        self.btn_delete_file.clicked.connect(self._delete_file)
        file_btn_row.addWidget(self.btn_upload_file)
        file_btn_row.addWidget(btn_open)
        file_btn_row.addWidget(self.btn_delete_file)
        file_btn_row.addStretch()
        list_lay.addLayout(file_btn_row)
        splitter.addWidget(list_widget)

        # ── Rechts: Vorschau ──────────────────────────────────────────
        preview_widget = QWidget()
        preview_lay = QVBoxLayout(preview_widget)
        preview_lay.setContentsMargins(8, 0, 0, 0)
        preview_lay.setSpacing(4)

        self._preview_lbl = QLabel()
        self._preview_lbl.setAlignment(Qt.AlignCenter)
        self._preview_lbl.setMinimumSize(240, 240)
        self._preview_lbl.setStyleSheet(
            "background:#f0f0f0; border:1px solid #ddd; border-radius:6px;")
        self._preview_lbl.setText("No file selected")
        self._preview_lbl.setWordWrap(True)
        preview_lay.addWidget(self._preview_lbl, 1)

        self._preview_meta = QLabel()
        self._preview_meta.setStyleSheet("color:#666; font-size:10px;")
        self._preview_meta.setWordWrap(True)
        preview_lay.addWidget(self._preview_meta)
        splitter.addWidget(preview_widget)

        splitter.setSizes([340, 260])
        files_outer.addWidget(splitter, 1)

        self._tabs.addTab(files_widget, "Files")
        self._tabs.tabBar().setTabEnabled(1, False)   # aktiviert erst wenn top_plate_id bekannt

        content_layout.addWidget(self._tabs, 1)

        # ── Buttons ───────────────────────────────────────────────────────
        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(32, 0, 32, 8)
        btn_layout.setSpacing(12)
        btn_layout.addStretch(1)
        self.btn_cancel = QPushButton("Cancel", objectName="GreyBtn")
        self.btn_cancel.clicked.connect(self._go_home)
        btn_layout.addWidget(self.btn_cancel)
        self.btn_save = QPushButton("Save Top Plate", objectName="GreenBtn")
        self.btn_save.clicked.connect(self._on_click_save)
        btn_layout.addWidget(self.btn_save)

        content_layout.addWidget(btn_frame, 0)
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

    def _create_editor_for_column(self, col: str) -> QWidget:
        key = _canon(col)
        fk = self.fk_maps.get(key)
        if fk:
            combo = QComboBox()
            # Leere Auswahl als erste Option erlauben
            combo.addItem("")
            combo.addItems(list(fk.get("name_to_id", {}).keys()))
            combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            return combo

        if col in self.bool_columns or col.lower() in {b.lower() for b in self.bool_columns}:
            chk = QCheckBox()
            chk.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            return chk

        edit = QLineEdit()
        edit.setClearButtonEnabled(True)
        edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return edit

    # --- Public helpers for MainWindow ---
    def reset_form(self):
        """Leert alle Eingabefelder (für 'New Top Plate') und lädt FK-Listen neu."""
        from PySide6.QtWidgets import QComboBox, QCheckBox, QLineEdit

        for col, widget in self._editors.items():
            key = _canon(col)
            fk = self.fk_maps.get(key)

            if isinstance(widget, QComboBox):
                # Liste immer aus aktueller fk_maps neu aufbauen
                try:
                    widget.blockSignals(True)
                    widget.clear()
                    # Immer zuerst leere Auswahl anbieten
                    widget.addItem("")
                    if fk:
                        widget.addItems(list(fk.get("name_to_id", {}).keys()))
                    # Standardmässig auf leeren Eintrag setzen
                    widget.setCurrentIndex(0)
                finally:
                    widget.blockSignals(False)

            elif isinstance(widget, QCheckBox):
                widget.setChecked(False)

            elif isinstance(widget, QLineEdit):
                widget.clear()

    def load_from_row(self, row: Dict[str, object], clear_name: bool = True):
        """
        Befüllt das Formular mit Werten aus row.
        - ID wird ignoriert (Autowert)
        - GlobalID wird ignoriert
        - Wenn clear_name=True, wird das Feld 'Name' leer gemacht.
        """
        from PySide6.QtWidgets import QComboBox, QCheckBox, QLineEdit

        for col, widget in self._editors.items():
            if col.lower() == self.id_column.lower():
                continue

            value = row.get(col)

            if clear_name and _canon(col) == "name":
                value = None

            key = _canon(col)
            fk = self.fk_maps.get(key)

            if isinstance(widget, QComboBox):
                name = None
                if fk:
                    id_to_name = fk.get("id_to_name", {})
                    name = id_to_name.get(value)
                    if name is None and value is not None:
                        try:
                            iv = int(str(value))
                            name = id_to_name.get(
                                iv) or id_to_name.get(str(iv))
                        except Exception:
                            name = id_to_name.get(str(value))
                if name is None:
                    name = ""
                idx = widget.findText(str(name))
                if idx < 0 and name:
                    widget.addItem(str(name))
                    idx = widget.count() - 1
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                else:
                    if widget.count() > 0:
                        widget.setCurrentIndex(0)

            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value) and value not in (
                    0, "0", "", None, False))

            elif isinstance(widget, QLineEdit):
                widget.setText("" if value is None else str(value))

        # Wenn ID in row vorhanden → bestehende Top Plate → Files-Tab aktivieren
        top_plate_id_val = row.get(self.id_column)
        if top_plate_id_val is not None:
            try:
                self._set_top_plate_id(int(top_plate_id_val))
                self._load_files()
            except Exception:
                pass

    # ── Files tab helpers ────────────────────────────────────────────────────
    def _on_file_selected(self, item: Optional[QListWidgetItem]):
        """Aktualisiert das Vorschau-Panel wenn ein File selektiert wird."""
        if not item:
            self._preview_lbl.setText("No file selected")
            self._preview_meta.setText("")
            return
        r = item.data(Qt.UserRole)
        if not r:
            return
        rel  = r.get("RelativePath") or ""
        path = os.path.join(_top_plate_files_root(), rel) if rel else ""
        fname = r.get("FileName") or ""
        ext   = os.path.splitext(fname)[1].lower()
        kb    = r.get("FileSizeKB") or ""
        meta  = f"{fname}   {kb} KB" if kb else fname
        self._preview_meta.setText(meta)

        IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".gif", ".webp"}
        if ext in IMAGE_EXTS and path and os.path.isfile(path):
            px = QPixmap(path)
            if not px.isNull():
                size = self._preview_lbl.size()
                self._preview_lbl.setPixmap(
                    px.scaled(size.width() - 8, size.height() - 8,
                              Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return
        # Non-image or file not found
        icon = _file_icon(fname)
        self._preview_lbl.clear()
        self._preview_lbl.setText(
            "\n\n".join([icon, fname, ""])
            + ("File not found on disk" if not os.path.isfile(path) else "Double-click to open"))

    def _set_top_plate_id(self, top_plate_id: Optional[int]):
        """Setzt die aktuelle Top-Plate-ID und aktiviert den Files-Tab."""
        self._current_top_plate_id = top_plate_id
        self._tabs.tabBar().setTabEnabled(1, top_plate_id is not None)

    def _load_files(self):
        """Lädt Dateien aus tblTopPlateFile für die aktuelle Top Plate."""
        self._file_list.clear()
        self._preview_lbl.setText("No file selected")
        self._preview_meta.setText("")
        if not self._current_top_plate_id:
            return
        try:
            from db.connection import fetch_all
            rows = fetch_all(
                "SELECT ID, FileName, StoredName, RelativePath, FileType, FileSizeKB, Notes "
                "FROM tblTopPlateFile WHERE TopPlateID = %s ORDER BY UploadedAt DESC",
                [self._current_top_plate_id]
            )
        except Exception:
            return
        for r in rows:
            fname = r.get("FileName") or r.get("StoredName") or ""
            icon  = _file_icon(fname)
            kb    = r.get("FileSizeKB")
            size  = f"  ({kb} KB)" if kb else ""
            notes = f"  – {r['Notes']}" if r.get("Notes") else ""
            item  = QListWidgetItem(f"{icon}  {fname}{size}{notes}")
            item.setData(Qt.UserRole, r)
            self._file_list.addItem(item)

    def _upload_file(self):
        """Öffnet Dateiauswahl, kopiert Datei in TopPlateFiles-Ordner, schreibt DB."""
        if self._read_only:
            return
        if not self._current_top_plate_id:
            QMessageBox.information(self, "Upload", "Please save the top plate first.")
            return
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select files to upload", "",
            "All files (*);;Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;PDF (*.pdf)"
        )
        if not paths:
            return
        root = _top_plate_files_root()
        top_plate_folder = os.path.join(root, str(self._current_top_plate_id))
        os.makedirs(top_plate_folder, exist_ok=True)
        try:
            from db.connection import execute
            import app_meta
            uid = (app_meta.current_user or {}).get("id")
        except Exception as e:
            QMessageBox.critical(self, "Upload failed", str(e))
            return
        errors = []
        for path in paths:
            try:
                fname  = os.path.basename(path)
                ts     = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                stored = f"{ts}_{fname}"
                dest   = os.path.join(top_plate_folder, stored)
                shutil.copy2(path, dest)
                rel    = os.path.join(str(self._current_top_plate_id), stored)
                kb     = max(1, os.path.getsize(dest) // 1024)
                ext    = os.path.splitext(fname)[1].lower()
                ftype  = ("image" if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")
                          else "pdf" if ext == ".pdf" else "other")
                execute(
                    "INSERT INTO tblTopPlateFile "
                    "(TopPlateID, FileName, StoredName, RelativePath, FileType, FileSizeKB, UploadedBy) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    [self._current_top_plate_id, fname, stored, rel, ftype, kb, uid]
                )
            except Exception as e:
                errors.append(f"{os.path.basename(path)}: {e}")
        self._load_files()
        if errors:
            QMessageBox.warning(self, "Upload errors", "\n".join(errors))

    def _open_file(self, item: Optional[QListWidgetItem]):
        """Öffnet die ausgewählte Datei mit dem Standard-Programm."""
        if not item:
            return
        r = item.data(Qt.UserRole)
        if not r:
            return
        rel  = r.get("RelativePath") or ""
        path = os.path.join(_top_plate_files_root(), rel) if rel else ""
        if not path or not os.path.isfile(path):
            QMessageBox.warning(self, "File not found",
                                f"File not found:\n{path}")
            return
        try:
            os.startfile(path)
        except AttributeError:
            import subprocess
            subprocess.Popen(["xdg-open", path])

    def _delete_file(self):
        """Löscht den DB-Eintrag (Datei auf Disk bleibt erhalten)."""
        if self._read_only:
            return
        item = self._file_list.currentItem()
        if not item:
            return
        r = item.data(Qt.UserRole)
        if not r:
            return
        fname = r.get("FileName") or "this file"
        reply = QMessageBox.question(
            self, "Delete file",
            f"Remove '{fname}' from this top plate?\n(File on disk is NOT deleted.)",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            from db.connection import execute
            execute("DELETE FROM tblTopPlateFile WHERE ID = %s", [r["ID"]])
        except Exception as e:
            QMessageBox.critical(self, "Delete failed", str(e))
            return
        self._load_files()

    # ---- Aktionen ----
    def set_read_only(self, read_only: bool):
        """Schaltet das komplette Formular auf reine Ansicht um: alle Felder
        sowie Upload/Delete im Files-Tab werden gesperrt (Speichern eingeschlossen).
        "Open" (Datei ansehen) und "Cancel" bleiben bewusst immer nutzbar. Wird
        bei jeder Navigation zu diesem (wiederverwendeten) Screen von main.py neu
        gesetzt, da New/Copy/Edit sich dieselbe Instanz teilen."""
        self._read_only = bool(read_only)
        for widget in self._editors.values():
            widget.setEnabled(not self._read_only)
        self.btn_upload_file.setEnabled(not self._read_only)
        self.btn_delete_file.setEnabled(not self._read_only)
        tooltip = "Read-only access – you don't have permission to edit this record." if self._read_only else ""
        self.btn_save.setEnabled(not self._read_only)
        self.btn_save.setToolTip(tooltip)
        self.btn_upload_file.setToolTip(tooltip)
        self.btn_delete_file.setToolTip(tooltip)

    def _go_home(self):
        if callable(self.on_back_home):
            self.on_back_home()

    def _get_top_plate_name(self) -> str:
        """Liest den Inhalt des 'Name'-Feldes."""
        from PySide6.QtWidgets import QLineEdit, QComboBox, QCheckBox

        for col, widget in self._editors.items():
            if _canon(col) == "name":
                if isinstance(widget, QLineEdit):
                    return widget.text().strip()
                if isinstance(widget, QComboBox):
                    return widget.currentText().strip()
                if isinstance(widget, QCheckBox):
                    return "1" if widget.isChecked() else "0"
        return ""

    def _collect_values(self) -> Dict[str, object]:
        data: Dict[str, object] = {}
        from PySide6.QtWidgets import QComboBox, QCheckBox, QLineEdit

        for col, widget in self._editors.items():
            if col.lower() == self.id_column.lower():
                continue

            key = _canon(col)
            fk = self.fk_maps.get(key)

            if isinstance(widget, QComboBox):
                name = widget.currentText()
                val = fk["name_to_id"].get(name) if fk else name
                data[col] = val

            elif isinstance(widget, QCheckBox):
                data[col] = 1 if widget.isChecked() else 0

            elif isinstance(widget, QLineEdit):
                txt = widget.text().strip()
                data[col] = txt if txt != "" else None

            else:
                data[col] = None

        return data

    def _on_click_save(self):
        if self._read_only:
            return
        if not callable(self._on_save):
            QMessageBox.warning(
                self, "New Top Plate", "No save callback configured.")
            return

        # 1) Name-Feld prüfen (Pflichtfeld)
        top_plate_name = self._get_top_plate_name()
        if not top_plate_name:
            QMessageBox.warning(
                self, "New Top Plate", "Please enter a name in the 'Name' field.")
            return

        # 2) Name-Feld auf Eindeutigkeit prüfen
        if callable(self._check_top_plate_name):
            try:
                available = self._check_top_plate_name(top_plate_name)
            except Exception:
                available = True
            if not available:
                QMessageBox.warning(
                    self,
                    "New Top Plate",
                    f"A Top Plate with the name '{top_plate_name}' exists already.\nPlease choose a unique name.",
                )
                return

        data = self._collect_values()

        try:
            new_id = self._on_save(data)
        except Exception as e:
            show_error(self, "New Top Plate", "The top plate could not be saved.", e)
            return

        if new_id is None:
            QMessageBox.warning(
                self, "New Top Plate", "Save successful, but new ID is unknown.")
        else:
            QMessageBox.information(
                self, "New Top Plate", f"New Top Plate saved (ID {new_id}).")

        if new_id is not None:
            self._set_top_plate_id(new_id)

        if callable(self._on_created) and new_id is not None:
            try:
                self._on_created(new_id)
                return
            except Exception:
                pass

        self._go_home()