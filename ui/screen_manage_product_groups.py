from ui.theme import accent_tint, accent_gridline
# ui/screen_manage_product_groups.py
from typing import List, Dict, Optional, Set
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QSizePolicy, QTableView, QMessageBox, QLineEdit, QAbstractItemView
)

from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from ui.text_normalize import canon_simple as _canon
from db.connection import fetch_all, execute, execute_insert
from db import master_tables as _mt   # Qt-free, shared with the web

# Wiederverwendet statt dupliziert (analog zu screen_manage_yarn.py/
# screen_manage_material.py) - vollstaendig generisch (kein Jets-spezifischer
# State), siehe ui/screen_manage_jets.py fuer die Implementierung.
from ui.screen_manage_jets import FilterableHeaderView, ColumnOrderDialog, MultiColumnFilterProxy


class GenericEditableModel(QAbstractTableModel):
    """Simple editable model with dirty tracking and alternating light background."""

    def __init__(self, rows: List[Dict], headers: List[str], id_column: str = 'ID',
                 read_only: bool = False):
        super().__init__()
        self._rows = rows[:]
        self._headers = headers[:]
        self._id_col = id_column
        self._dirty: Set[tuple] = set()
        self._read_only = read_only

    def set_read_only(self, read_only: bool):
        """Schaltet die Editierbarkeit aller Zellen um (Ansicht muss danach neu gezeichnet werden)."""
        self._read_only = read_only

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._headers)

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        r, c = index.row(), index.column()
        header = self._headers[c]
        val = self._rows[r].get(header, None)

        if role == Qt.BackgroundRole:
            return QBrush(QColor(accent_tint())) if (r % 2 == 0) else QBrush(QColor('#F5FFF5'))
        if role == Qt.EditRole:
            return val
        if role == Qt.DisplayRole:
            return '' if val is None else str(val)
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        return None

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemIsEnabled
        header = self._headers[index.column()]
        if header.lower() == self._id_col.lower() or self._read_only:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole or self._read_only:
            return False
        header = self._headers[index.column()]
        if header.lower() == self._id_col.lower():
            return False
        if isinstance(value, str):
            value = value.strip()
        self._rows[index.row()][header] = value
        self._dirty.add((index.row(), index.column()))
        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
        return True

    def dirty_rows(self) -> List[Dict]:
        if not self._dirty:
            return []
        dirty_row_indices = sorted({r for (r, _) in self._dirty})
        return [self._rows[i] for i in dirty_row_indices]

    def clear_dirty(self):
        self._dirty.clear()

    def id_column(self) -> str:
        return self._id_col

    def headers(self) -> List[str]:
        return self._headers

    def rows(self) -> List[Dict]:
        return self._rows


class ManageProductGroupsScreen(QWidget):
    TABLE = 'tblProduktgruppe'
    _SCREEN_KEY = 'manage_product_groups'

    def __init__(self, on_back_home=None, sidebar_callbacks: Optional[dict] = None):
        super().__init__()
        self.on_back_home = on_back_home
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None

        self.table: Optional[QTableView] = None
        self.model: Optional[GenericEditableModel] = None
        self.proxy: Optional[MultiColumnFilterProxy] = None
        self._header: Optional[FilterableHeaderView] = None
        self._column_order_dialog: Optional[ColumnOrderDialog] = None

        self.search_edit: Optional[QLineEdit] = None
        self.btn_reload: Optional[QPushButton] = None
        self.btn_new: Optional[QPushButton] = None
        self.btn_columns: Optional[QPushButton] = None
        self.btn_delete: Optional[QPushButton] = None
        self.btn_save: Optional[QPushButton] = None
        self.status_label: Optional[QLabel] = None
        self._search_cols: List[int] = []

        self._id_col = 'ID'
        self._read_only = False

        self._build_ui()
        self.reload_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring).
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        # toolbar (search + actions)
        toolbar = QFrame()
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(24, 12, 24, 0)
        tl.setSpacing(8)

        self.search_edit = QLineEdit(placeholderText='Filter…')
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._on_search_changed)

        self.btn_reload = QPushButton('Reload', objectName='GreyBtn')
        self.btn_reload.clicked.connect(self.reload_data)

        self.btn_new = QPushButton('New', objectName='GreenBtn')
        self.btn_new.clicked.connect(self._on_new)

        self.btn_columns = QPushButton('Columns…', objectName='GreyBtn')
        self.btn_columns.setToolTip('Reorder columns via a drag & drop list')
        self.btn_columns.clicked.connect(self._on_columns_clicked)

        self.btn_delete = QPushButton('Delete', objectName='GreyBtn')
        self.btn_delete.clicked.connect(self._on_delete)

        self.btn_save = QPushButton('Save Changes', objectName='PurpleBtn')
        self.btn_save.clicked.connect(self.save_changes)

        self.status_label = QLabel('')

        tl.addWidget(self.search_edit, 1)
        tl.addWidget(self.btn_reload, 0)
        tl.addWidget(self.btn_new, 0)
        tl.addWidget(self.btn_columns, 0)
        tl.addWidget(self.btn_delete, 0)
        tl.addWidget(self.btn_save, 0)
        tl.addWidget(self.status_label, 0, Qt.AlignVCenter)

        # table
        self.table = QTableView(objectName='ProductGroupsTable')
        # FilterableHeaderView (aus screen_manage_jets) statt Standard-Header:
        # Rechtsklick auf eine Spalte -> "contains"/"von-bis"-Filter, Sections
        # movable fuer Drag&Drop-Umsortieren (siehe "Columns…"-Button).
        self._header = FilterableHeaderView(Qt.Horizontal, self.table)
        self._header.setSectionsMovable(True)
        self.table.setHorizontalHeader(self._header)
        self.table.setAlternatingRowColors(False)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # Styling (wie User/Jets)
        self.table.setStyleSheet("""
            QTableView#ProductGroupsTable { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView#ProductGroupsTable::item { color: black; }
            QTableView#ProductGroupsTable::item:selected { background: #b7d6ff; color: black; }
        """
            .replace("#B5D7B5", accent_gridline())
            .replace("#E9F6E9", accent_tint()))

        content_layout.addWidget(toolbar, 0)
        content_layout.addWidget(self.table, 1)
        root.addWidget(FooterBar())

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

    def _configure_search_column(self, headers: List[str]):
        """Ermittelt die bevorzugte Suchspalte; faellt auf alle Spalten
        zurueck, falls keine gefunden wird (bisheriges Verhalten der alten
        TextFilterProxy)."""
        pref = None
        for i, h in enumerate(headers):
            if _canon(h) in {'produktgruppe', 'productgroup', 'name', 'bezeichnung'}:
                pref = i
                break
        self._search_cols = [pref] if pref is not None else list(range(len(headers)))

    def _on_search_changed(self, text: str):
        if not self.proxy:
            return
        self.proxy.set_search_filter(self._search_cols, text)

    # ---- data layer ----
    def _load_rows(self) -> List[Dict]:
        return _mt.load_rows(_mt.KINDS['product_groups'])

    def _infer_id_col(self, headers: List[str]) -> str:
        for h in headers:
            if h.lower() == 'id':
                return h
        # fallback: first column
        return headers[0] if headers else 'ID'

    def reload_data(self):
        rows = self._load_rows()
        headers = list(rows[0].keys()) if rows else ['ID', 'Produktgruppe']

        self._id_col = self._infer_id_col(headers)

        self.model = GenericEditableModel(
            rows, headers, id_column=self._id_col, read_only=self._read_only)

        if not self.proxy:
            self.proxy = MultiColumnFilterProxy(self)
            self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
            self.proxy.setDynamicSortFilter(True)
            self._header.set_proxy(self.proxy)
        self.proxy.setSourceModel(self.model)
        self._configure_search_column(headers)
        self.proxy.setSortRole(Qt.EditRole)
        self.table.setModel(self.proxy)

        self.table.resizeColumnsToContents()
        # default sort by ID
        id_idx = 0
        for i, h in enumerate(headers):
            if h == self._id_col:
                id_idx = i
                break
        self.table.sortByColumn(id_idx, Qt.AscendingOrder)
        self._restore_column_order()

        self._set_status(f'{len(rows)} row(s) loaded.')
        self._on_search_changed(self.search_edit.text())
        self._apply_read_only_ui()

    def set_read_only(self, read_only: bool):
        """Schaltet Schreibrechte um: New/Delete/Save + Zell-Editing gesperrt,
        Suche bleibt immer nutzbar. Von main.py bei jeder Navigation zu diesem
        Screen mit dem aktuellen Permission-Stand aufgerufen."""
        self._read_only = bool(read_only)
        self._apply_read_only_ui()

    def _apply_read_only_ui(self):
        ro = self._read_only
        if self.model is not None:
            self.model.set_read_only(ro)
            # dataChanged statt layoutChanged: reiner Repaint (read-only-Styling),
            # keine echte Zeilen-/Spaltenumordnung. layoutChanged invalidiert
            # persistente Model-Indizes/Selection-State - bei jedem erneuten
            # Sichtbarwerden dieses Screens wiederholt aufgerufen, führte das in
            # screen_manage_yarn.py nachweislich (Bisektion, faulthandler) zu
            # einem Absturz (Windows access violation) im nächsten selectRow() -
            # gleiches Muster hier, siehe CLAUDE.md.
            rows = self.model.rowCount()
            cols = self.model.columnCount()
            if rows and cols:
                self.model.dataChanged.emit(
                    self.model.index(0, 0), self.model.index(rows - 1, cols - 1))
        tooltip = "Read-only access – you don't have permission to edit this table." if ro else ""
        for btn in (self.btn_new, self.btn_delete, self.btn_save):
            if btn is not None:
                btn.setEnabled(not ro)
                btn.setToolTip(tooltip)

    def save_changes(self):
        if not self.model or self._read_only:
            return
        dirty_rows = self.model.dirty_rows()
        if not dirty_rows:
            self._set_status('No changes to save.')
            return
        try:
            total = _mt.save_changes(_mt.KINDS['product_groups'], dirty_rows)   # db/master_tables.py
            self._set_status(f'Saved {total} update(s).')
            self.model.clear_dirty()
        except Exception as e:
            QMessageBox.critical(self, 'Save failed', str(e))
            self._set_status(f'Save failed: {e}', error=True)

    def _on_new(self):
        if self._read_only:
            return
        try:
            new_id = _mt.create(_mt.KINDS['product_groups'])          # db/master_tables.py

            self.reload_data()
            if new_id is not None:
                self._select_row_by_id(new_id)
            self._set_status('New row created.')
        except Exception as e:
            QMessageBox.critical(self, 'Create failed', str(e))
            self._set_status(f'Create failed: {e}', error=True)

    def _on_delete(self):
        if not self.model or self._read_only:
            return
        src_rows = self._source_selection_rows()
        if not src_rows:
            self._set_status('No rows selected.')
            return
        id_col = self.model.id_column() or 'ID'
        ids = []
        for r in src_rows:
            try:
                rid = self.model.rows()[r].get(id_col)
                if rid is not None:
                    ids.append(rid)
            except Exception:
                pass
        if not ids:
            self._set_status('No valid IDs to delete.')
            return

        if QMessageBox.question(self, 'Confirm Delete', f'Delete {len(ids)} row(s)?') != QMessageBox.Yes:
            return
        try:
            _mt.delete(_mt.KINDS['product_groups'], ids)
            self.reload_data()
            self._set_status(f'Deleted {len(ids)} row(s).')
        except Exception as e:
            QMessageBox.critical(self, 'Delete failed', str(e))
            self._set_status(f'Delete failed: {e}', error=True)

    # ---- column reordering (wie Manage Yarn/Jets/Material) ----
    def _on_columns_clicked(self):
        """Oeffnet/hebt die Drag&Drop-Spaltenliste zum Umsortieren."""
        if not self.model:
            return
        if self._column_order_dialog is None or not self._column_order_dialog.isVisible():
            self._column_order_dialog = ColumnOrderDialog(
                self._header, self.model, 0, on_save=self._save_column_order_now, parent=self)
            self._column_order_dialog.show()
        else:
            self._column_order_dialog.raise_()
            self._column_order_dialog.activateWindow()

    def _save_column_order_now(self):
        """Persistiert die AKTUELLE Spaltenreihenfolge fuer den eingeloggten
        User. Nur explizit aufgerufen (Save-Button im Columns-Dialog)."""
        if not self.model:
            return
        headers = self.model.headers()
        order = []
        for v in range(self._header.count()):
            logical = self._header.logicalIndex(v)
            if logical < len(headers) and not self._header.isSectionHidden(logical):
                order.append(headers[logical])
        from db.user_column_order import save_column_order
        save_column_order(self._SCREEN_KEY, order)

    def _restore_column_order(self):
        """Wendet die zuletzt fuer diesen User gespeicherte Spaltenreihenfolge an (falls vorhanden)."""
        if not self.model:
            return
        from db.user_column_order import load_column_order
        saved = load_column_order(self._SCREEN_KEY)
        if not saved:
            return
        name_to_logical = {h: i for i, h in enumerate(self.model.headers())}
        pos = 0
        for name in saved:
            logical = name_to_logical.get(name)
            if logical is None:
                continue
            current_visual = self._header.visualIndex(logical)
            if current_visual != pos:
                self._header.moveSection(current_visual, pos)
            pos += 1

    # ---- helpers ----
    def _source_selection_rows(self) -> List[int]:
        if not self.table or not self.proxy:
            return []
        sel = self.table.selectionModel().selectedRows()
        rows = []
        for idx in sel:
            try:
                src_i = self.proxy.mapToSource(idx)
                rows.append(src_i.row())
            except Exception:
                pass
        rows.sort()
        return rows

    def _select_row_by_id(self, select_id: Optional[int]):
        if not self.model or select_id is None:
            return
        id_col = None
        headers = self.model.headers()
        for i, h in enumerate(headers):
            if h.lower() == self._id_col.lower():
                id_col = i
                break
        if id_col is None:
            return
        for r, row in enumerate(self.model.rows()):
            if row.get(self._id_col) == select_id:
                if self.proxy:
                    for pr in range(self.proxy.rowCount()):
                        src = self.proxy.mapToSource(
                            self.proxy.index(pr, id_col))
                        if src.row() == r:
                            self.table.selectRow(pr)
                            self.table.scrollTo(self.proxy.index(pr, 0))
                            return
                else:
                    self.table.selectRow(r)
                    self.table.scrollTo(self.model.index(r, 0))
                return

    def _set_status(self, text: str, *, error: bool = False):
        self.status_label.setStyleSheet('color: #c62828;' if error else '')
        self.status_label.setText(text)

    def _go_home(self):
        if callable(self.on_back_home):
            self.on_back_home()