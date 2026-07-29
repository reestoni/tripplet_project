from ui.theme import accent_tint, accent_gridline
# ui/screen_manage_order_types.py
from typing import List, Dict, Optional, Set
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, QRegularExpression
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QSizePolicy, QTableView, QMessageBox, QLineEdit, QAbstractItemView
)

from ui.widgets.footer import FooterBar
from ui.widgets.header import HeaderBar
from db.connection import fetch_all, execute




def _canon(s: str) -> str:
    return str(s).strip().strip('`[]').replace(' ', '').lower() if s is not None else ''


class GenericEditableModel(QAbstractTableModel):
    """Simple editable model with dirty tracking and alternating light background."""

    def __init__(self, rows: List[Dict], headers: List[str], id_column: str = 'ID'):
        super().__init__()
        self._rows = rows[:]
        self._headers = headers[:]
        self._id_col = id_column
        self._dirty: Set[tuple] = set()

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
        if header.lower() == self._id_col.lower():
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
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


class TextFilterProxy(QSortFilterProxyModel):
    """Filter by a preferred column if it exists, else across all columns (contains, case-insensitive)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pref_idx = -1
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setDynamicSortFilter(True)

    def set_preferred_column(self, headers: List[str]):
        self.pref_idx = -1
        for i, h in enumerate(headers):
            if _canon(h) in {'bestellungstyp', 'ordertype', 'name', 'bezeichnung'}:
                self.pref_idx = i
                break

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        rx = self.filterRegularExpression()
        if not rx.pattern():
            return True

        def match_col(col_idx: int) -> bool:
            if col_idx < 0:
                return False
            idx = self.sourceModel().index(source_row, col_idx)
            data = self.sourceModel().data(idx, Qt.DisplayRole)
            return rx.match(str(data)).hasMatch()

        # If we have a preferred column, use it; otherwise scan all columns.
        if self.pref_idx >= 0:
            return match_col(self.pref_idx)
        for c in range(self.sourceModel().columnCount()):
            if match_col(c):
                return True
        return False


class ManageOrderTypeScreen(QWidget):
    TABLE = 'tblBestellungstyp'

    def __init__(self, on_back_home=None):
        super().__init__()
        self.on_back_home = on_back_home

        self.table: Optional[QTableView] = None
        self.model: Optional[GenericEditableModel] = None
        self.proxy: Optional[TextFilterProxy] = None

        self.search_edit: Optional[QLineEdit] = None
        self.btn_reload: Optional[QPushButton] = None
        self.btn_new: Optional[QPushButton] = None
        self.btn_delete: Optional[QPushButton] = None
        self.btn_save: Optional[QPushButton] = None
        self.status_label: Optional[QLabel] = None

        self._id_col = 'ID'

        self._build_ui()
        self.reload_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = HeaderBar(title='Manage Order Type', show_home=True)
        header.connect_home(self._go_home)

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

        self.btn_delete = QPushButton('Delete', objectName='GreyBtn')
        self.btn_delete.clicked.connect(self._on_delete)

        self.btn_save = QPushButton('Save Changes', objectName='PurpleBtn')
        self.btn_save.clicked.connect(self.save_changes)

        self.status_label = QLabel('')

        tl.addWidget(self.search_edit, 1)
        tl.addWidget(self.btn_reload, 0)
        tl.addWidget(self.btn_new, 0)
        tl.addWidget(self.btn_delete, 0)
        tl.addWidget(self.btn_save, 0)
        tl.addWidget(self.status_label, 0, Qt.AlignVCenter)

        # table
        self.table = QTableView(objectName='OrderTypeTable')
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
            QTableView#OrderTypeTable { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView#OrderTypeTable::item { color: black; }
            QTableView#OrderTypeTable::item:selected { background: #b7d6ff; color: black; }
        """
            .replace("#B5D7B5", accent_gridline())
            .replace("#E9F6E9", accent_tint()))

        root.addWidget(header)
        root.addWidget(toolbar, 0)
        root.addWidget(self.table, 1)
        root.addWidget(FooterBar())

    def _on_search_changed(self, text: str):
        if not self.proxy:
            return
        if not text:
            self.proxy.setFilterRegularExpression(QRegularExpression())
            return
        rx = QRegularExpression('.*' + QRegularExpression.escape(text) + '.*')
        rx.setPatternOptions(QRegularExpression.CaseInsensitiveOption)
        self.proxy.setFilterRegularExpression(rx)

    # ---- data layer ----
    def _load_rows(self) -> List[Dict]:
        return fetch_all(f'SELECT * FROM [{self.TABLE}]', [])

    def _infer_id_col(self, headers: List[str]) -> str:
        for h in headers:
            if h.lower() == 'id':
                return h
        # fallback: first column
        return headers[0] if headers else 'ID'

    def reload_data(self):
        rows = self._load_rows()
        headers = list(rows[0].keys()) if rows else ['ID', 'Bestellungstyp']

        self._id_col = self._infer_id_col(headers)

        self.model = GenericEditableModel(
            rows, headers, id_column=self._id_col)

        if not self.proxy:
            self.proxy = TextFilterProxy(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setSortRole(Qt.EditRole)
        self.proxy.set_preferred_column(headers)
        self.table.setModel(self.proxy)

        self.table.resizeColumnsToContents()
        # default sort by ID
        id_idx = 0
        for i, h in enumerate(headers):
            if h == self._id_col:
                id_idx = i
                break
        self.table.sortByColumn(id_idx, Qt.AscendingOrder)

        self._set_status(f'{len(rows)} row(s) loaded.')
        self._on_search_changed(self.search_edit.text())

    def save_changes(self):
        if not self.model:
            return
        dirty_rows = self.model.dirty_rows()
        if not dirty_rows:
            self._set_status('No changes to save.')
            return
        id_col = self.model.id_column() or 'ID'
        total = 0
        try:
            for r in dirty_rows:
                if id_col not in r:
                    raise ValueError(
                        f"Row has no '{id_col}' field; cannot save.")
                rid = r[id_col]
                cols = [c for c in self.model.headers() if c !=
                        id_col and c in r]
                if not cols:
                    continue
                set_sql = ', '.join([f'[{c}] = ?' for c in cols])
                sql = f'UPDATE [{self.TABLE}] SET {set_sql} WHERE [{id_col}] = ?'
                params = [r[c] for c in cols] + [rid]
                total += execute(sql, params) or 0
            self._set_status(f'Saved {total} update(s).')
            self.model.clear_dirty()
        except Exception as e:
            QMessageBox.critical(self, 'Save failed', str(e))
            self._set_status(f'Save failed: {e}', error=True)

    def _on_new(self):
        try:
            rows = self._load_rows()
            headers = list(rows[0].keys()) if rows else [
                'ID', 'Bestellungstyp']
            cols = [h for h in headers if h.lower() != 'id']

            # very simple defaults
            values = []
            for c in cols:
                values.append('' if _canon(c) in {
                              'bestellungstyp', 'name', 'bezeichnung'} else None)

            placeholders = ','.join(['?'] * len(cols))
            cols_sql = ', '.join([f'[{c}]' for c in cols])
            sql = f'INSERT INTO [{self.TABLE}] ({cols_sql}) VALUES ({placeholders})'
            execute(sql, values)
            row = fetch_all('SELECT @@IDENTITY AS NewID', [])
            new_id = int(row[0]['NewID']
                         ) if row and 'NewID' in row[0] else None

            self.reload_data()
            if new_id is not None:
                self._select_row_by_id(new_id)
            self._set_status('New row created.')
        except Exception as e:
            QMessageBox.critical(self, 'Create failed', str(e))
            self._set_status(f'Create failed: {e}', error=True)

    def _on_delete(self):
        if not self.model:
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
            placeholders = ','.join(['?'] * len(ids))
            sql = f'DELETE FROM [{self.TABLE}] WHERE [{id_col}] IN ({placeholders})'
            execute(sql, ids)
            self.reload_data()
            self._set_status(f'Deleted {len(ids)} row(s).')
        except Exception as e:
            QMessageBox.critical(self, 'Delete failed', str(e))
            self._set_status(f'Delete failed: {e}', error=True)

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