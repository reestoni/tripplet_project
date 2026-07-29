from ui.theme import accent_tint, accent_gridline
# ui/screen_manage_yarn.py
from typing import List, Dict, Optional, Tuple
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, QRegularExpression
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QSizePolicy, QTableView, QMessageBox, QLineEdit, QAbstractItemView,
    QStyledItemDelegate, QComboBox
)

from ui.widgets.header import HeaderBar
from ui.widgets.footer import FooterBar
from db.connection import fetch_all, execute, new_global_id, get_columns_map


def _canon(s: str) -> str:
    return str(s).strip().strip('`[]').replace(' ', '').lower() if s is not None else ''


def _canon_noparen(s: str) -> str:
    c = _canon(s)
    return c.replace('(', '').replace(')', '')




# ---------- FK loaders (ohne Aliasse wegen Access-ODBC-Quirk) ----------------
def load_garntyp_map() -> Tuple[Dict[int, str], Dict[str, int]]:
    rows = fetch_all(
        'SELECT [ID], [Garntyp] FROM [tblGarntyp] ORDER BY [Garntyp]', [])
    id2name: Dict[int, str] = {}
    name2id: Dict[str, int] = {}
    for r in rows:
        i = r.get('ID')
        n = r.get('Garntyp')
        try:
            i = int(i)
        except Exception:
            pass
        id2name[i] = n
        name2id[str(n)] = i
    return id2name, name2id


def load_material_map() -> Tuple[Dict[int, str], Dict[str, int]]:
    rows = fetch_all(
        'SELECT [ID], [Material] FROM [tblMaterial] ORDER BY [Material]', [])
    id2name: Dict[int, str] = {}
    name2id: Dict[str, int] = {}
    for r in rows:
        i = r.get('ID')
        n = r.get('Material')
        try:
            i = int(i)
        except Exception:
            pass
        id2name[i] = n
        name2id[str(n)] = i
    return id2name, name2id


def _norm(s: str) -> str:
    return (
        (s or "")
        .lower().replace(" ", "").replace("_", "")
        .replace("(", "").replace(")", "").replace("°", "")
        .replace("/", "").replace("-", "").strip()
    )


def _resolve_field(cands: List[str], cols_map: Dict[str, str]) -> Optional[str]:
    # exakter lowercase-match
    for cand in cands:
        lc = (cand or "").lower()
        if lc in cols_map:
            return cols_map[lc]
    # normalisierter match
    inv = {_norm(k): v for k, v in cols_map.items()}
    for cand in cands:
        nk = _norm(cand)
        if nk in inv:
            return inv[nk]
    return None


def _id_key_variants(v) -> List[object]:
    """Generiert Key-Varianten für Mapping-Lookups (int/str/original)."""
    out: List[object] = []
    if v is None:
        return out
    out.append(v)
    try:
        out.append(int(v))
    except Exception:
        pass
    try:
        out.append(str(v))
    except Exception:
        pass
    # dedupe, preserve order
    seen = set()
    uniq = []
    for x in out:
        if x in seen:
            continue
        seen.add(x)
        uniq.append(x)
    return uniq


def load_yarngroup_map() -> Tuple[Dict[object, str], Dict[str, object]]:
    """YarnGroup (tblyarngroup) mapping: ID -> DisplayName.

    Achtung: In deiner DB kann das Feld fuer den Namen auch z.B. GroupName heissen.
    Darum wird es ueber information_schema aufgeloest.
    """
    table = 'tblyarngroup'
    cols_map = get_columns_map(table)
    col_id = _resolve_field(['ID'], cols_map) or 'ID'
    col_name = _resolve_field(['Name', 'GroupName', 'GruppenName', 'Bezeichnung'], cols_map) or 'Name'
    col_no = _resolve_field(['GroupNumber', 'GroupNo', 'GruppenNummer', 'Number', 'Nummer'], cols_map)

    sel = [f'[{col_id}] AS ID', f'[{col_name}] AS Name']
    if col_no:
        sel.append(f'[{col_no}] AS GroupNo')

    order = f'ORDER BY [{col_no}]' if col_no else f'ORDER BY [{col_name}]'
    rows = fetch_all(f'SELECT {", ".join(sel)} FROM [{table}] {order}', [])

    id2name: Dict[object, str] = {}
    name2id: Dict[str, object] = {}

    for r in rows:
        raw_id = r.get('ID')
        raw_name = r.get('Name')
        raw_no = r.get('GroupNo') if 'GroupNo' in r else None

        # Display label: "<no> - <name>" oder nur name
        name = '' if raw_name is None else str(raw_name).strip()
        try:
            gno = int(str(raw_no).strip()) if raw_no not in (None, '') else None
        except Exception:
            gno = None
        label = f'{gno} - {name}' if (gno is not None and name) else (name or (str(gno) if gno is not None else ''))

        # Map: sowohl int als auch str keys ablegen (robust gegen Typenmix)
        for k in _id_key_variants(raw_id):
            id2name[k] = label
        if label:
            # letztes gewinnt (bei Duplikaten egal)
            name2id[label] = raw_id

    return id2name, name2id


# ---------- Delegates for FK columns -----------------------------------------
class ComboMapDelegate(QStyledItemDelegate):
    """Generic combobox delegate that shows names but writes IDs."""

    def __init__(self, id2name: Dict[object, str], parent=None):
        super().__init__(parent)
        self.id2name = id2name
        # stable order by display name
        # NOTE: id2name kann mehrere Key-Varianten fuer denselben Datensatz enthalten
        # (z.B. 1 und "1"). Darum dedupen wir ueber den *Label*-Text.
        seen_label = set()
        opts = []
        for i, n in id2name.items():
            label = '' if n is None else str(n)
            if label in seen_label:
                continue
            seen_label.add(label)
            opts.append((i, label))
        self._options = sorted(opts, key=lambda t: (t[1].lower() if isinstance(t[1], str) else str(t[1]).lower()))

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        for i, n in self._options:
            combo.addItem(str(n), i)
        combo.setEditable(False)
        return combo

    def setEditorData(self, editor, index):
        current_id = index.model().data(index, Qt.EditRole)
        for cand in _id_key_variants(current_id):
            for i in range(editor.count()):
                if editor.itemData(i) == cand:
                    editor.setCurrentIndex(i)
                    return

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentData(), Qt.EditRole)


# ---------- Table Model -------------------------------------------------------
class YarnTableModel(QAbstractTableModel):
    """Editable model, with FK-display (Garntyp & Material), computed DPF, and light background."""

    def __init__(self, rows: List[Dict], headers: List[str], id_column: str = 'ID',
                 garntyp_col: Optional[str] = None, garntyp_map: Optional[Dict[int, str]] = None,
                 material_col: Optional[str] = None, material_map: Optional[Dict[int, str]] = None,
                 yarngroup_col: Optional[str] = None, yarngroup_map: Optional[Dict[object, str]] = None):
        super().__init__()
        self._rows = rows[:]
        self._headers = headers[:]
        self._id_col = id_column
        self._dirty_cells = set()
        self._garntyp_col = garntyp_col
        self._garntyp_map = garntyp_map or {}
        self._material_col = material_col
        self._material_map = material_map or {}
        self._yarngroup_col = yarngroup_col
        self._yarngroup_map: Dict[object, str] = yarngroup_map or {}

        # Detect column names for computed DPF and its inputs
        self._dpf_col = None
        self._endtiter_col = None
        self._filaments_col = None
        for h in self._headers:
            k = _canon_noparen(h)
            if self._dpf_col is None and k in {'dpfdtex', 'dpf'}:
                self._dpf_col = h
            if self._endtiter_col is None and k in {'endtiterdtex', 'endtiter'}:
                self._endtiter_col = h
            if self._filaments_col is None and k in {'numberoffilaments', 'filaments', 'nofilaments'}:
                self._filaments_col = h

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

    def _compute_dpf(self, row: int):
        if not self._dpf_col or not self._endtiter_col or not self._filaments_col:
            return None
        endt = self._rows[row].get(self._endtiter_col)
        fils = self._rows[row].get(self._filaments_col)
        try:
            if endt in (None, '') or fils in (None, '', 0, '0'):
                return None
            endt_f = float(str(endt).replace(',', '.'))
            fils_f = float(str(fils).replace(',', '.'))
            if fils_f == 0.0:
                return None
            return endt_f / fils_f
        except Exception:
            return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        r, c = index.row(), index.column()
        header = self._headers[c]
        val = self._rows[r].get(header, None)

        if role == Qt.BackgroundRole:
            return QBrush(QColor(accent_tint())) if (r % 2 == 0) else QBrush(QColor('#F5FFF5'))

        # Computed DPF field
        if self._dpf_col and header == self._dpf_col:
            if role in (Qt.DisplayRole, Qt.EditRole):
                v = self._compute_dpf(r)
                return '' if v is None else v
            if role == Qt.TextAlignmentRole:
                return Qt.AlignCenter
            return None

        if role == Qt.EditRole:
            return val

        # FK display: show names
        if role == Qt.DisplayRole:
            if self._garntyp_col and header == self._garntyp_col:
                try:
                    return self._garntyp_map.get(int(val), '') if val is not None else ''
                except Exception:
                    return self._garntyp_map.get(val, '')
            if self._material_col and header == self._material_col:
                try:
                    return self._material_map.get(int(val), '') if val is not None else ''
                except Exception:
                    return self._material_map.get(val, '')
            if self._yarngroup_col and header == self._yarngroup_col:
                # Wenn das Mapping nicht geladen werden konnte, zeige die rohe ID
                if not self._yarngroup_map:
                    return '' if val is None else str(val)
                for cand in _id_key_variants(val):
                    if cand in self._yarngroup_map:
                        return self._yarngroup_map.get(cand, '')
                # unbekannte ID -> ebenfalls roh anzeigen (hilft beim Debuggen)
                return '' if val is None else str(val)
            return '' if val is None else str(val)

        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        return None

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemIsEnabled
        header = self._headers[index.column()]
        if self._dpf_col and header == self._dpf_col:
            return Qt.ItemIsEnabled  # computed -> not editable
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False
        header = self._headers[index.column()]
        if self._dpf_col and header == self._dpf_col:
            return False  # computed
        if isinstance(value, str):
            value = value.strip()
        self._rows[index.row()][header] = value
        self._dirty_cells.add((index.row(), index.column()))
        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
        return True

    def dirty_rows(self) -> List[Dict]:
        if not self._dirty_cells:
            return []
        dirty_row_indices = sorted({r for (r, _) in self._dirty_cells})
        return [self._rows[i] for i in dirty_row_indices]

    def clear_dirty(self):
        self._dirty_cells.clear()

    def id_column(self) -> str:
        return self._id_col

    def headers(self) -> List[str]:
        return self._headers

    def rows(self) -> List[Dict]:
        return self._rows

    def dpf_column_name(self) -> Optional[str]:
        return self._dpf_col


# ---------- Filter auf Name ---------------------------------------------------
class NameFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.name_idx = -1
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setDynamicSortFilter(True)

    def set_name_column(self, headers: List[str]):
        self.name_idx = -1
        for i, h in enumerate(headers):
            if _canon(h) == 'name':
                self.name_idx = i
                break

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        rx = self.filterRegularExpression()
        if not rx.pattern():
            return True
        if self.name_idx < 0:
            return True
        idx = self.sourceModel().index(source_row, self.name_idx)
        data = self.sourceModel().data(idx, Qt.DisplayRole)
        return rx.match(str(data)).hasMatch()


# ---------- Screen ------------------------------------------------------------
class ManageYarnScreen(QWidget):
    def __init__(self, on_back_home=None):
        super().__init__()
        self.on_back_home = on_back_home

        self.table: Optional[QTableView] = None
        self.model: Optional[YarnTableModel] = None
        self.proxy: Optional[NameFilterProxy] = None

        self.search_edit: Optional[QLineEdit] = None
        self.btn_reload: Optional[QPushButton] = None
        self.btn_new: Optional[QPushButton] = None
        self.btn_delete: Optional[QPushButton] = None
        self.btn_save: Optional[QPushButton] = None
        self.status_label: Optional[QLabel] = None

        self._id_col = 'ID'
        self._garntyp_col = None
        self._material_col = None
        self._yarngroup_col = None
        self._garntyp_id2name: Dict[int, str] = {}
        self._material_id2name: Dict[int, str] = {}
        self._yarngroup_id2name: Dict[int, str] = {}
        self._garntyp_delegate: Optional[ComboMapDelegate] = None
        self._material_delegate: Optional[ComboMapDelegate] = None
        self._yarngroup_delegate: Optional[ComboMapDelegate] = None

        self._build_ui()
        self.reload_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header ganz oben
        header = HeaderBar(title='Manage Yarn', show_home=True)
        header.connect_home(self._go_home)
        root.addWidget(header, 0)

        # Toolbar
        toolbar = QFrame()
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(24, 12, 24, 0)
        tl.setSpacing(8)

        self.search_edit = QLineEdit(placeholderText='Filter by Name…')
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._on_search_changed)

        self.btn_reload = QPushButton('Reload', objectName='GreyBtn')
        self.btn_reload.clicked.connect(self.reload_data)

        self.btn_new = QPushButton('New Yarn', objectName='GreenBtn')
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

        # Tabelle
        self.table = QTableView(objectName='YarnTable')
        self.table.setAlternatingRowColors(False)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setStyleSheet("""
            QTableView#YarnTable { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView#YarnTable::item { color: black; }
            QTableView#YarnTable::item:selected { background: #b7d6ff; color: black; }
        """
            .replace("#B5D7B5", accent_gridline())
            .replace("#E9F6E9", accent_tint()))

        root.addWidget(toolbar, 0)
        root.addWidget(self.table, 1)

        # Footer ganz unten
        root.addWidget(FooterBar(), 0)

    # --- Data layer ---
    def _load_yarn(self) -> List[Dict]:
        return fetch_all('SELECT * FROM [tblYarn]', [])

    def reload_data(self):
        rows = self._load_yarn()
        headers = list(rows[0].keys()) if rows else [self._id_col]

        # find ID column
        for h in headers:
            if h.lower() == 'id':
                self._id_col = h
                break

        # identify FK columns in tblYarn
        self._garntyp_col = None
        self._material_col = None
        self._yarngroup_col = None
        for h in headers:
            k = _canon(h)
            if k == 'garntyp':
                self._garntyp_col = h
            if k == 'material':
                self._material_col = h
            if k in {'yarngroupid', 'yarngroup', 'groupid'}:
                # priorisiere das explizite YarnGroupID falls vorhanden
                if self._yarngroup_col is None or k == 'yarngroupid':
                    self._yarngroup_col = h

        # load FK maps
        self._garntyp_id2name, _ = load_garntyp_map()
        self._material_id2name, _ = load_material_map()
        try:
            self._yarngroup_id2name, _ = load_yarngroup_map()
        except Exception:
            # YarnGroup ist optional; Screen funktioniert auch ohne
            self._yarngroup_id2name = {}

        # build model
        self.model = YarnTableModel(
            rows, headers,
            id_column=self._id_col,
            garntyp_col=self._garntyp_col, garntyp_map=self._garntyp_id2name,
            material_col=self._material_col, material_map=self._material_id2name,
            yarngroup_col=self._yarngroup_col, yarngroup_map=self._yarngroup_id2name
        )

        # proxy (filter/sort)
        if not self.proxy:
            self.proxy = NameFilterProxy(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.set_name_column(headers)
        self.proxy.setSortRole(Qt.EditRole)
        self.table.setModel(self.proxy)

        # delegates for FK columns
        if self._garntyp_col is not None:
            if not self._garntyp_delegate:
                self._garntyp_delegate = ComboMapDelegate(
                    self._garntyp_id2name, self.table)
            self.table.setItemDelegateForColumn(headers.index(
                self._garntyp_col), self._garntyp_delegate)

        if self._material_col is not None:
            if not self._material_delegate:
                self._material_delegate = ComboMapDelegate(
                    self._material_id2name, self.table)
            self.table.setItemDelegateForColumn(headers.index(
                self._material_col), self._material_delegate)

        if self._yarngroup_col is not None and self._yarngroup_id2name:
            if not self._yarngroup_delegate:
                self._yarngroup_delegate = ComboMapDelegate(
                    self._yarngroup_id2name, self.table)
            self.table.setItemDelegateForColumn(headers.index(
                self._yarngroup_col), self._yarngroup_delegate)

        self.table.resizeColumnsToContents()
        # sort by ID ascending
        id_idx = 0
        for i, h in enumerate(headers):
            if h == self._id_col:
                id_idx = i
                break
        self.table.sortByColumn(id_idx, Qt.AscendingOrder)

        self._set_status(f"{len(rows)} yarn(s) loaded.")
        self._on_search_changed(self.search_edit.text())

    def save_changes(self):
        if not self.model:
            return
        dirty_rows = self.model.dirty_rows()
        if not dirty_rows:
            self._set_status('No changes to save.')
            return
        id_col = self.model.id_column() or 'ID'
        dpf_col = self.model.dpf_column_name()
        total = 0
        try:
            for r in dirty_rows:
                if id_col not in r:
                    raise ValueError(
                        f"Row has no '{id_col}' field; cannot save.")
                rid = r[id_col]
                cols = [c for c in self.model.headers() if c !=
                        id_col and c in r]
                # exclude computed DPF column from updates
                if dpf_col and dpf_col in cols:
                    cols.remove(dpf_col)
                if not cols:
                    continue
                set_sql = ', '.join([f'[{c}] = ?' for c in cols])
                sql = f'UPDATE [tblYarn] SET {set_sql} WHERE [{id_col}] = ?'
                params = [r[c] for c in cols] + [rid]
                total += execute(sql, params) or 0
            self._set_status(f'Saved {total} update(s).')
            self.model.clear_dirty()
        except Exception as e:
            QMessageBox.critical(self, 'Save failed', str(e))
            self._set_status(f'Save failed: {e}', error=True)

    def _on_new(self):
        try:
            rows = self._load_yarn()
            headers = list(rows[0].keys()) if rows else [
                'ID', 'Name', 'Garntyp', 'Material']
            cols = [h for h in headers if h.lower() != 'id']
            # exclude computed DPF if present
            dpf_col = None
            for h in headers:
                if _canon_noparen(h) in {'dpfdtex', 'dpf'}:
                    dpf_col = h
                    break
            if dpf_col and dpf_col in cols:
                cols.remove(dpf_col)

            values = []
            for c in cols:
                k = _canon(c)
                if k == 'name':
                    values.append('New Yarn')
                elif k == 'garntyp':
                    default_id = sorted(self._garntyp_id2name.keys())[
                        0] if self._garntyp_id2name else None
                    values.append(default_id)
                elif k == 'material':
                    default_id = sorted(self._material_id2name.keys())[
                        0] if self._material_id2name else None
                    values.append(default_id)
                elif k in {'yarngroupid', 'yarngroup', 'groupid'}:
                    if self._yarngroup_id2name:
                        _int_keys = [kk for kk in self._yarngroup_id2name.keys() if isinstance(kk, int)]
                        if _int_keys:
                            default_id = min(_int_keys)
                        else:
                            # fallback: deterministic choice even if keys are mixed types
                            default_id = sorted(self._yarngroup_id2name.keys(), key=lambda x: str(x))[0]
                    else:
                        default_id = None
                    values.append(default_id)
                elif k == 'globalid':
                    # neue GUID für jeden Yarn-Datensatz
                    values.append(new_global_id())
                else:
                    values.append(None)

            placeholders = ','.join(['?'] * len(cols))
            cols_sql = ', '.join([f'[{c}]' for c in cols])
            sql = f'INSERT INTO [tblYarn] ({cols_sql}) VALUES ({placeholders})'
            execute(sql, values)
            row = fetch_all('SELECT @@IDENTITY AS NewID', [])
            new_id = int(row[0]['NewID']
                         ) if row and 'NewID' in row[0] else None
            self.reload_data()
            if new_id is not None:
                self._select_row_by_id(new_id)
            self._set_status('New yarn created.')
        except Exception as e:
            QMessageBox.critical(self, 'Create failed', str(e))
            self._set_status(f'Create failed: {e}', error=True)

    def _on_delete(self):
        if not self.model:
            return
        src = self._source_selection_rows()
        if not src:
            self._set_status('No rows selected.')
            return
        id_col = self.model.id_column() or 'ID'
        ids = []
        for r in src:
            try:
                rid = self.model.rows()[r].get(id_col)
                if rid is not None:
                    ids.append(rid)
            except Exception:
                pass
        if not ids:
            self._set_status('No valid IDs to delete.')
            return

        if QMessageBox.question(self, 'Confirm Delete', f'Delete {len(ids)} yarn(s)?') != QMessageBox.Yes:
            return
        try:
            placeholders = ','.join(['?'] * len(ids))
            sql = f'DELETE FROM [tblYarn] WHERE [{id_col}] IN ({placeholders})'
            execute(sql, ids)
            self.reload_data()
            self._set_status(f'Deleted {len(ids)} yarn(s).')
        except Exception as e:
            QMessageBox.critical(self, 'Delete failed', str(e))
            self._set_status(f'Delete failed: {e}', error=True)

    # --- helpers ---
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

    def _on_search_changed(self, text: str):
        if not self.proxy:
            return
        if not text:
            self.proxy.setFilterRegularExpression(QRegularExpression())
            return
        rx = QRegularExpression('.*' + QRegularExpression.escape(text) + '.*')
        rx.setPatternOptions(QRegularExpression.CaseInsensitiveOption)
        self.proxy.setFilterRegularExpression(rx)

    def _set_status(self, text: str, *, error: bool = False):
        self.status_label.setStyleSheet('color: #c62828;' if error else '')
        self.status_label.setText(text)

    def _go_home(self):
        if callable(self.on_back_home):
            self.on_back_home()