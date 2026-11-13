from ui.theme import accent_tint, accent_gridline

# ui/screen_manage_material.py
from typing import List, Dict, Optional
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QRegularExpression
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QSizePolicy, QTableView, QMessageBox, QLineEdit, QAbstractItemView
)

from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from ui.text_normalize import canon_simple as _canon
from db.connection import fetch_all, execute, execute_insert, get_columns_map
from db import master_tables as _mt   # Qt-free, shared with the web

# Wiederverwendet statt dupliziert (analog zu screen_manage_yarn.py) - die drei
# Klassen sind vollstaendig generisch (kein Jets-spezifischer State), siehe
# ui/screen_manage_jets.py fuer die Implementierung. ExpandableFilterProxy's
# Detail-Zeilen-Kinds sind dort fest auf ('series', 'trial') verdrahtet - siehe
# MaterialTableModel.row_kind() fuer die daraus folgende Konvention.
from ui.screen_manage_jets import FilterableHeaderView, ColumnOrderDialog, ExpandableFilterProxy
from ui.screen_manage_yarn import _resolve_field, load_garntyp_map, load_colour_map
from ui.widgets.friendly_error import show_error


# Optional rating columns that may exist on tblMaterial.
#
# Earlier versions used a separate lookup table for displaying user-friendly
# rating descriptions. That lookup table has been removed, so these columns are
# now treated as plain editable values.
FK_COLS = [
    'Lightfastness',
    'Weather Durability',
    'Acid Resistance',
    'Alkaline Resistance',
]


class MaterialTableModel(QAbstractTableModel):
    """Editable model for tblMaterial with a computed 'UsedInYarn' column
    (same click-to-expand logic as YarnTableModel's UsedInTrial, see
    ui/screen_manage_yarn.py) that inline-expands to the catalog yarns using
    this material - a single detail level (no further Series/Trial drill-down
    like Yarn's UsedInTrial has, since "which yarns use this material" doesn't
    need a second level)."""

    def __init__(self, rows: List[Dict], headers: List[str], id_column: str = 'ID'):
        super().__init__()
        self._rows = rows[:]
        self._headers = headers[:]
        self._id_col = id_column
        self._dirty_cells = set()
        self._read_only = False

        self._usedinyarn_col = None
        for h in self._headers:
            if _canon(h) == 'usedinyarn':
                self._usedinyarn_col = h
                break

        # Welche Material-Zeilen (per Material-ID) gerade inline aufgeklappt
        # sind - steuert nur das Dreieck-Symbol auf der Material-Zeile selbst.
        # Das eigentliche Ein-/Ausblenden der Yarn-Detailzeilen (echte,
        # eingefuegte Model-Zeilen - siehe insert_detail_rows()) macht
        # ManageMaterialScreen.
        self._expanded_ids: set = set()

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

    # ---- inline aufklappbare Yarn-Detailzeilen -------------------------------
    def row_kind(self, row: int) -> str:
        """'material' (echte tblMaterial-Zeile, Default) | 'trial' (Yarn-
        Detailzeile). 'trial' statt eines eigenen Namens, weil
        ExpandableFilterProxy._DETAIL_KINDS in screen_manage_jets.py fest auf
        ('series', 'trial') verdrahtet ist - ein dritter Name wuerde dort
        weder beim Filtern noch beim Sortieren als Detailzeile erkannt."""
        return self._rows[row].get('_row_kind', 'material')

    def anchor_row(self, row: int) -> int:
        """Zeilenindex der Material-Zeile, zu der diese Zeile gehoert (sich
        selbst, falls sie schon eine Material-Zeile ist). Wird von
        ExpandableFilterProxy gebraucht, um Detailzeilen beim Sortieren am
        richtigen Platz zu halten."""
        rd = self._rows[row]
        if rd.get('_row_kind', 'material') == 'material':
            return row
        anchor_id = rd.get('_anchor_material_id')
        for i, r in enumerate(self._rows):
            if r.get('_row_kind', 'material') == 'material' and r.get(self._id_col) == anchor_id:
                return i
        return row  # sollte nicht vorkommen (Material-Zeile zwischenzeitlich entfernt)

    def local_order(self, row: int) -> float:
        """Feste Position innerhalb eines Material-Blocks (0 = die Material-
        Zeile selbst, dann die Yarn-Zeilen in Anzeigereihenfolge)."""
        return self._rows[row].get('_order', 0.0)

    def insert_detail_rows(self, after_row: int, new_rows: List[Dict]):
        """Fuegt echte Model-Zeilen direkt nach `after_row` ein. Bestehende
        dirty-Markierungen (die auf Positionsindizes zeigen) werden
        mitverschoben, sonst wuerde save_changes() nach dem Aufklappen die
        falsche Zeile treffen."""
        if not new_rows:
            return
        n = len(new_rows)
        insert_at = after_row + 1
        self.beginInsertRows(QModelIndex(), insert_at, insert_at + n - 1)
        self._rows[insert_at:insert_at] = new_rows
        self._dirty_cells = {(r + n if r >= insert_at else r, c) for (r, c) in self._dirty_cells}
        self.endInsertRows()

    def remove_rows_span(self, start_row: int, count: int):
        """Gegenstueck zu insert_detail_rows()."""
        if count <= 0:
            return
        self.beginRemoveRows(QModelIndex(), start_row, start_row + count - 1)
        del self._rows[start_row:start_row + count]
        self._dirty_cells = {
            (r - count if r >= start_row + count else r, c)
            for (r, c) in self._dirty_cells if not (start_row <= r < start_row + count)
        }
        self.endRemoveRows()

    def _detail_row_data(self, row: int, col: int, role):
        """data() fuer eine Yarn-Detailzeile: der Datensatz ist nur ein
        Anzeige-Label in Spalte 0 (ManageMaterialScreen spannt die ganze Zeile
        mit setSpan() ueber diese eine Zelle)."""
        if role == Qt.DisplayRole and col == 0:
            return self._rows[row].get('_label', '')
        if role == Qt.BackgroundRole:
            return QBrush(QColor('#E3EEE3'))
        if role == Qt.ForegroundRole:
            return QBrush(QColor('#2b2b2b'))
        if role == Qt.TextAlignmentRole:
            return Qt.AlignVCenter | Qt.AlignLeft
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        r, c = index.row(), index.column()
        if self._rows[r].get('_row_kind', 'material') != 'material':
            return self._detail_row_data(r, c, role)
        header = self._headers[c]
        val = self._rows[r].get(header, None)

        if role == Qt.BackgroundRole:
            return QBrush(QColor(accent_tint())) if (r % 2 == 0) else QBrush(QColor('#F5FFF5'))
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

        # Computed "used in at least one yarn" field (Yes/No). The trailing
        # triangle (▸/▾) mirrors the expand state that ManageMaterialScreen
        # tracks when it inserts real Yarn detail rows directly below this
        # row (insert_detail_rows()) - same pattern as YarnTableModel's
        # UsedInTrial, see ui/screen_manage_yarn.py.
        if self._usedinyarn_col and header == self._usedinyarn_col:
            if role == Qt.DisplayRole:
                if val != 1:
                    return 'No'
                mid = self._rows[r].get(self._id_col)
                return 'Yes ▾' if mid in self._expanded_ids else 'Yes ▸'
            if role == Qt.ToolTipRole and val == 1:
                mid = self._rows[r].get(self._id_col)
                return ('Click to hide the yarns using this material' if mid in self._expanded_ids
                        else 'Click to show the yarns using this material')
            return None

        if role == Qt.EditRole:
            return val
        if role == Qt.DisplayRole:
            return '' if val is None else str(val)
        return None

    def set_read_only(self, read_only: bool):
        """Schaltet die Editierbarkeit aller Zellen um (Ansicht muss danach neu gezeichnet werden)."""
        self._read_only = read_only

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemIsEnabled
        if self._rows[index.row()].get('_row_kind', 'material') != 'material':
            # Detailzeile: nicht selektierbar/editierbar - rein informativ.
            return Qt.ItemIsEnabled
        header = self._headers[index.column()]
        if header.lower() == self._id_col.lower() or header == self._usedinyarn_col or self._read_only:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole or self._read_only:
            return False
        if self._rows[index.row()].get('_row_kind', 'material') != 'material':
            return False  # Detailzeile - nie editierbar (flags() verhindert das ohnehin schon)
        header = self._headers[index.column()]
        if header.lower() == self._id_col.lower() or header == self._usedinyarn_col:
            return False
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

    def usedinyarn_column_name(self) -> Optional[str]:
        return self._usedinyarn_col

    def set_expanded(self, material_id, expanded: bool):
        """Nur fuers Dreieck-Symbol auf der Material-Zeile - das Einfuegen/
        Entfernen der Yarn-Zeilen selbst macht ManageMaterialScreen
        (insert_detail_rows/remove_rows_span). Emittiert dataChanged nur fuer
        die betroffene Zelle."""
        if expanded:
            self._expanded_ids.add(material_id)
        else:
            self._expanded_ids.discard(material_id)
        if not self._usedinyarn_col:
            return
        try:
            row = next(i for i, rw in enumerate(self._rows) if rw.get(self._id_col) == material_id)
        except StopIteration:
            return
        col = self._headers.index(self._usedinyarn_col)
        idx = self.index(row, col)
        self.dataChanged.emit(idx, idx, [Qt.DisplayRole, Qt.ToolTipRole])


class ManageMaterialScreen(QWidget):
    TABLE = 'tblMaterial'
    _SCREEN_KEY = 'manage_material'

    def __init__(self, on_back_home=None, sidebar_callbacks: Optional[dict] = None):
        super().__init__()
        self.on_back_home = on_back_home
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None

        self.table: Optional[QTableView] = None
        self.model: Optional[MaterialTableModel] = None
        self.proxy: Optional[ExpandableFilterProxy] = None
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

        # Inline aufgeklappte UsedInYarn-Zeilen: Set der gerade aufgeklappten
        # Material-IDs. Die eigentlichen Zeilen sind echte, eingefuegte
        # Model-Zeilen (siehe MaterialTableModel.insert_detail_rows).
        self._expanded_ids: set = set()

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
        self.table = QTableView(objectName='MaterialTable')
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
        self.table.setStyleSheet("""
            QTableView#MaterialTable { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView#MaterialTable::item { color: black; }
            QTableView#MaterialTable::item:selected { background: #b7d6ff; color: black; }
        """
            .replace("#B5D7B5", accent_gridline())
            .replace("#E9F6E9", accent_tint()))
        self.table.clicked.connect(self._on_table_clicked)
        # Pointing-hand cursor over "Yes …" cells / Yarn detail rows signals
        # clickability without touching item painting (same reasoning as
        # YarnTableModel, see ui/screen_manage_yarn.py).
        self.table.setMouseTracking(True)
        self.table.entered.connect(self._on_cell_hovered)

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

    # ---- data layer ----
    def _load_rows(self) -> List[Dict]:
        # + UsedInYarn (shown only): db/master_tables.load_rows
        return _mt.load_rows(_mt.KINDS['material'])

    def _fetch_material_usage(self, material_id) -> List[Dict]:
        return _mt.material_usage(material_id)

    @staticmethod
    def _fmt_num(v) -> Optional[str]:   # kept for callers; same as db/master_tables._fmt_num
        """Kompakte Zahlendarstellung fuers Yarn-Detail-Label (800.00 -> '800',
        3.50 -> '3.5') - siehe ManageYarnScreen._fmt_num fuer dasselbe Muster."""
        if v is None:
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        return f'{f:.0f}' if f == int(f) else f'{f:.1f}'

    @classmethod
    def _yarn_label(cls, y: Dict) -> str:
        return "      •  " + _mt.yarn_label(y)

    def _load_fk_maps(self) -> Dict[str, Dict]:
        # The former lookup table for ratings has been removed.
        # Keep the method for backwards compatibility, but do not load any FK maps.
        return {}

    def _infer_id_col(self, headers: List[str]) -> str:
        for h in headers:
            if h.lower() == 'id':
                return h
        return headers[0] if headers else 'ID'

    def reload_data(self):
        # Vor dem Modell-Austausch alle inline aufgeklappten Zeilen sauber
        # zuklappen (die alten Detailzeilen haengen am alten Modell/Proxy).
        self._collapse_all_usage_rows()
        rows = self._load_rows()
        headers = list(rows[0].keys()) if rows else [
            'ID', 'Material'] + FK_COLS + ['UsedInYarn']

        self._id_col = self._infer_id_col(headers)

        self.model = MaterialTableModel(rows, headers, id_column=self._id_col)
        self.model.set_read_only(self._read_only)

        if not self.proxy:
            self.proxy = ExpandableFilterProxy(self)
            self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
            self.proxy.setDynamicSortFilter(True)
            self.proxy.before_change = self._collapse_all_usage_rows
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
        self._apply_read_only_ui()
        self._restore_column_order()

        self._set_status(f'{len(rows)} row(s) loaded.')
        self._on_search_changed(self.search_edit.text())

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
            # UsedInYarn is no real column - db/master_tables.save_changes drops it
            total = _mt.save_changes(_mt.KINDS['material'], dirty_rows)
            self._set_status(f'Saved {total} update(s).')
            self.model.clear_dirty()
        except Exception as e:
            QMessageBox.critical(self, 'Save failed', str(e))
            self._set_status(f'Save failed: {e}', error=True)

    def _on_new(self):
        if self._read_only:
            return
        try:
            new_id = _mt.create(_mt.KINDS['material'])        # db/master_tables.py

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
            _mt.delete(_mt.KINDS['material'], ids)
            self.reload_data()
            self._set_status(f'Deleted {len(ids)} row(s).')
        except Exception as e:
            QMessageBox.critical(self, 'Delete failed', str(e))
            self._set_status(f'Delete failed: {e}', error=True)

    # ---- inline aufklappbare Yarn-Detailzeilen ----
    def _usedinyarn_col_idx(self) -> int:
        """Logischer Spaltenindex von UsedInYarn, oder -1 falls nicht vorhanden."""
        if not self.model:
            return -1
        col = self.model.usedinyarn_column_name()
        if not col:
            return -1
        try:
            return self.model.headers().index(col)
        except ValueError:
            return -1

    def _find_source_row_for_id(self, material_id) -> Optional[int]:
        if not self.model:
            return None
        for i, row in enumerate(self.model.rows()):
            if row.get('_row_kind', 'material') == 'material' and row.get(self._id_col) == material_id:
                return i
        return None

    def _apply_full_row_span(self, src_row: int):
        """Merged die ganze Zeile zu einer Zelle (Spalte 0 traegt das Label,
        siehe MaterialTableModel._detail_row_data) - fuer neu eingefuegte
        Detailzeilen direkt nach dem Insert aufgerufen."""
        if not self.model or not self.proxy:
            return
        proxy_index = self.proxy.mapFromSource(self.model.index(src_row, 0))
        if proxy_index.isValid():
            self.table.setSpan(proxy_index.row(), 0, 1, self.model.columnCount())

    def _clear_full_row_span(self, src_row: int):
        """Gegenstueck zu _apply_full_row_span() - vor dem Entfernen einer
        Detailzeile aufgerufen, damit kein Span auf eine dann falsche Zeile
        zeigt."""
        if not self.model or not self.proxy:
            return
        proxy_index = self.proxy.mapFromSource(self.model.index(src_row, 0))
        if proxy_index.isValid():
            self.table.setSpan(proxy_index.row(), 0, 1, 1)

    def _expand_material_row(self, material_id, clicked_index):
        """Fuegt fuer jedes Katalog-Garn, das dieses Material verwendet, eine
        echte, rein informative Zeile direkt unter der Material-Zeile ein."""
        try:
            usage = self._fetch_material_usage(material_id)
        except Exception as e:
            show_error(self, 'Used in Yarn', "The list of uses could not be loaded.", e)
            return
        if not usage:
            QMessageBox.information(
                self, 'Used in Yarn',
                'No yarns found for this material (data may have changed - try Reload).')
            return

        src_row = self.proxy.mapToSource(clicked_index).row()
        detail_rows = []
        for order, y in enumerate(usage, start=1):
            detail_rows.append({
                '_row_kind': 'trial',  # siehe MaterialTableModel.row_kind()
                '_anchor_material_id': material_id,
                '_order': float(order),
                '_label': self._yarn_label(y),
            })
        self.model.insert_detail_rows(src_row, detail_rows)
        for offset in range(1, len(detail_rows) + 1):
            self._apply_full_row_span(src_row + offset)

        self._expanded_ids.add(material_id)
        self.model.set_expanded(material_id, True)

    def _collapse_material_row(self, material_id):
        if material_id not in self._expanded_ids:
            return
        src_row = self._find_source_row_for_id(material_id)
        self._expanded_ids.discard(material_id)
        self.model.set_expanded(material_id, False)
        if src_row is None:
            return
        rows = self.model.rows()
        i = src_row + 1
        while i < len(rows) and rows[i].get('_row_kind', 'material') != 'material':
            i += 1
        count = i - (src_row + 1)
        if count:
            for j in range(src_row + 1, src_row + 1 + count):
                self._clear_full_row_span(j)
            self.model.remove_rows_span(src_row + 1, count)

    def _collapse_all_usage_rows(self):
        """Klappt alles zu - aufgerufen vor jedem Reload sowie (ueber
        ExpandableFilterProxy.before_change) vor jedem Sortieren/Filtern."""
        for material_id in list(self._expanded_ids):
            self._collapse_material_row(material_id)

    def _on_table_clicked(self, index):
        """Klick auf eine "Yes ▸/▾"-Zelle klappt die Material-Zeile auf/zu.
        Yarn-Detailzeilen sind rein informativ (nicht klickbar) - anders als
        bei Yarn/Jets gibt es hier keine zweite Verschachtelungsebene, darum
        reicht das 'clicked'-Signal (Pixel-Position wird nicht gebraucht)."""
        if not self.model or not self.proxy or not index.isValid():
            return
        src_row = self.proxy.mapToSource(index).row()
        rows = self.model.rows()
        if src_row < 0 or src_row >= len(rows):
            return
        if rows[src_row].get('_row_kind', 'material') != 'material':
            return
        ui_idx = self._usedinyarn_col_idx()
        disp = index.data(Qt.DisplayRole)
        if ui_idx < 0 or index.column() != ui_idx or not disp or not str(disp).startswith('Yes'):
            return
        material_id = rows[src_row].get(self._id_col)
        if material_id in self._expanded_ids:
            self._collapse_material_row(material_id)
        else:
            self._expand_material_row(material_id, index)

    def _on_cell_hovered(self, index):
        """Zeigt einen Hand-Cursor ueber "Yes …"-Zellen (klickbar, siehe
        MaterialTableModel)."""
        clickable = False
        if index.isValid() and self.model and self.proxy:
            src_row = self.proxy.mapToSource(index).row()
            rows = self.model.rows()
            if 0 <= src_row < len(rows) and rows[src_row].get('_row_kind', 'material') == 'material':
                ui_idx = self._usedinyarn_col_idx()
                disp = index.data(Qt.DisplayRole)
                clickable = (ui_idx >= 0 and index.column() == ui_idx
                             and bool(disp) and str(disp).startswith('Yes'))
        self.table.viewport().setCursor(Qt.PointingHandCursor if clickable else Qt.ArrowCursor)

    # ---- column reordering (wie Manage Yarn/Jets) ----
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
    def _configure_search_column(self, headers: List[str]):
        """Ermittelt die bevorzugte Suchspalte (Material-Name); fällt auf alle
        Spalten zurück, falls keine gefunden wird (bisheriges Verhalten der
        alten TextFilterProxy)."""
        pref = None
        for i, h in enumerate(headers):
            if _canon(h) in {'material', 'name', 'bezeichnung'}:
                pref = i
                break
        self._search_cols = [pref] if pref is not None else list(range(len(headers)))

    def _on_search_changed(self, text: str):
        if not self.proxy:
            return
        self._collapse_all_usage_rows()
        self.proxy.set_search_filter(self._search_cols, text)

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
