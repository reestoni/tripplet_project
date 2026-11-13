# ui/screen_manage_user.py
"""Verwaltungsscreen für Benutzerkonten (tblUser).

Zeigt alle Benutzer in einer editierbaren Tabelle. Unterstützt:
  - Inline-Bearbeitung (Name, E-Mail, Akzentfarbe, Access-Level usw.)
  - Neuanlage mit Passwort-Dialog
  - Passwort zurücksetzen (Admin-Funktion)
  - Löschen (mit Bestätigung)
  - Filtersuche nach Name/Username

Besonderheiten:
  - AccentColour-Spalte: Farbwähler-Dialog (QColorDialog), Vorschau als farbiges Rechteck
  - Active-Spalte: Checkbox (Bool)
  - AccessRight-Spalte: Combobox mit Rollennamen (FK → tblAccessRight)
  - Passwort-Reset: neues Passwort wird als Argon2-Hash gespeichert
  - Nur Benutzer mit AdminLevel können Benutzer anlegen/löschen
"""

from ui.theme import accent_tint, accent_gridline
# ui/screen_manage_user.py
from typing import List, Dict, Optional, Set, Tuple
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, QRegularExpression, QTimer
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QSizePolicy, QTableView, QMessageBox, QLineEdit, QAbstractItemView,
    QStyledItemDelegate, QComboBox, QColorDialog, QInputDialog,
    QDialog, QFormLayout, QDialogButtonBox, QSpinBox,
)

from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from ui.text_normalize import canon_simple as _canon
from db.connection import fetch_all, execute, execute_insert, is_offline_mode


def _load_master_key() -> Optional[bytes]:
    """Lädt den Fernet MASTER_KEY aus secrets.enc (eingebettet via PyInstaller oder lokal)."""
    import sys
    from pathlib import Path

    # Suchpfade: PyInstaller _MEIPASS → daneben exe → Projektordner
    candidates = [Path('secrets.enc')]
    if getattr(sys, 'frozen', False):
        candidates.insert(0, Path(sys._MEIPASS) / 'secrets.enc')
    else:
        candidates.append(Path(__file__).parent.parent / 'secrets.enc')

    for p in candidates:
        if p.exists():
            try:
                key = p.read_bytes().strip()
                # Validierung: Fernet Key ist immer 44 Bytes base64
                if len(key) == 44:
                    return key
            except Exception:
                pass
    return None


def _to_bool(val) -> bool:
    """Konvertiert diverse Werte (0/1, True/False, "yes"/"no") robust zu bool."""
    if isinstance(val, bool):
        return val
    if val in (0, None):
        return False
    try:
        s = str(val).strip().lower()
        if s in ('true', 't', 'yes', 'y', '1', '-1'):
            return True
        if s in ('false', 'f', 'no', 'n', '0', ''):
            return False
    except Exception:
        pass
    try:
        return float(val) != 0.0
    except Exception:
        return False


def _parse_color(val) -> Optional[QColor]:
    """Parst einen Farbwert (Hex-String, QColor, None) zu QColor. Gibt None bei ungültigem Wert zurück."""
    """Best-effort parse for a user colour.

    Supports:
      - '#RRGGBB'
      - 'R,G,B'
      - int 0xRRGGBB
    """
    if val in (None, ''):
        return None
    try:
        if isinstance(val, QColor):
            return val
        if isinstance(val, str):
            s = val.strip()
            if not s:
                return None
            if s.startswith('#'):
                c = QColor(s)
                return c if c.isValid() else None
            if ',' in s:
                parts = [p.strip() for p in s.split(',')]
                if len(parts) >= 3:
                    r, g, b = (int(parts[0]), int(parts[1]), int(parts[2]))
                    c = QColor(r, g, b)
                    return c if c.isValid() else None
        n = int(val)
        if 0 <= n <= 0xFFFFFF:
            r = (n >> 16) & 0xFF
            g = (n >> 8) & 0xFF
            b = n & 0xFF
            c = QColor(r, g, b)
            return c if c.isValid() else None
    except Exception:
        pass
    return None


def _color_to_hex(c: QColor) -> str:
    """Konvertiert eine QColor in einen Hex-String (z.B. "#39a650")."""
    return c.name(QColor.HexRgb).upper()  # '#RRGGBB'




# ---- FK: AccessRights mapping ------------------------------------------------
def load_access_rights_map() -> Tuple[Dict[int, str], Dict[str, int]]:
    """Lädt AccessRight-Mapping aus tblAccessRight.

    Returns:
        (id2name, name2id): id2name = {AccessLevel: AccessRight-Name}, name2id = umgekehrt.
    """
    """Load tblAccessRight (ID, AccessRight) without aliases (Access ODBC quirk)."""
    rows = fetch_all(
        "SELECT [ID], [AccessRight] FROM [tblAccessRight] ORDER BY [AccessRight]", [])
    id2name: Dict[int, str] = {}
    name2id: Dict[str, int] = {}
    for r in rows:
        i = r.get('ID')
        n = r.get('AccessRight')
        if i is not None:
            try:
                i_int = int(i)
            except Exception:
                i_int = i
            id2name[i_int] = n
            name2id[str(n)] = i_int
    return id2name, name2id


class AccessRightDelegate(QStyledItemDelegate):
    """Combobox-Delegate für die AccessRight-Spalte.

    Zeigt lesbare Rollennamen (z.B. "Admin") an, speichert aber die ID zurück.
    """
    def __init__(self, id2name: Dict[int, str], parent=None):
        """Args:
            id2name: Dict {AccessLevel-ID: Rollenname} für Combobox-Einträge.
        """
        super().__init__(parent)
        self.id2name = id2name
        # stable order by name
        self._options = sorted([(i, n) for i, n in id2name.items()], key=lambda t: (
            '' if t[1] is None else str(t[1]).lower()))

    def createEditor(self, parent, option, index):
        """Erstellt eine Combobox mit allen Rollennamen."""
        combo = QComboBox(parent)
        for i, n in self._options:
            combo.addItem(str(n), i)
        return combo

    def setEditorData(self, editor, index):
        """Setzt den aktuellen Rollennamen als Selektion in der Combobox."""
        # value in model should be ID
        current_id = index.model().data(index, Qt.EditRole)
        # find index by id
        for i in range(editor.count()):
            if editor.itemData(i) == current_id:
                editor.setCurrentIndex(i)
                return

    def setModelData(self, editor, model, index):
        """Schreibt die gewählte Rollen-ID zurück ins Modell."""
        # write back the selected ID
        model.setData(index, editor.currentData(), Qt.EditRole)


# --- table model (editable) ---
class UsersTableModel(QAbstractTableModel):
    """Editierbares Tabellenmodell für tblUser mit Dirty-Tracking.

    Spezialbehandlung:
    - Active-Spalte: Bool, dargestellt als Checkmark
    - AccentColour-Spalte: QColor, dargestellt als farbiges Rechteck (DecorationRole)
    - AccessRight-Spalte: FK, dargestellt als Rollenname
    - Dirty-Tracking: merkt geänderte Zeilen für SQL-UPDATE
    """
    """Editable table model with dirty-cell tracking, boolean columns, FK-display for AccessRights, and light background."""

    def __init__(self, rows: List[Dict], headers: List[str], id_column: str = 'ID',
                 bool_columns: Optional[Set[str]] = None,
                 access_rights_col: Optional[str] = None,
                 id2name_access: Optional[Dict[int, str]] = None):
        super().__init__()
        self._rows = rows[:]
        self._headers = headers[:]
        self._id_col = id_column
        self._dirty_cells = set()
        self._bool_cols = set(bool_columns or set())

        # columns
        self._pw_col_name = None
        for h in self._headers:
            if _canon(h) in {'pw', 'password', 'pass', 'passwd'}:
                self._pw_col_name = h
                break

        self._color_col_name = None
        for h in self._headers:
            if _canon(h) in {'colour', 'color'}:
                self._color_col_name = h
                break

        self._access_col = access_rights_col  # original header name
        self._access_id2name = id2name_access or {}

    def rowCount(self, parent=QModelIndex()) -> int:
        """Gibt die Anzahl Zeilen zurück."""
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        """Gibt die Anzahl Spalten zurück."""
        return len(self._headers)

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        """Gibt Spaltenheader zurück (nur DisplayRole, Horizontal)."""
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        """Liefert Zelldaten je nach Role.

        AccentColour → DecorationRole als QColor-Rechteck.
        Active → CheckStateRole.
        AccessRight → Rollenname via FK-Map.
        """
        if not index.isValid():
            return None
        r, c = index.row(), index.column()
        header = self._headers[c]
        key = _canon(header)
        val = self._rows[r].get(header, None)

        # Background styling
        if role == Qt.BackgroundRole:
            return QBrush(QColor(accent_tint())) if (r % 2 == 0) else QBrush(QColor('#F5FFF5'))

        # Sort role should use raw values (numbers for ID, ints for AccessRights, etc.)
        if role == Qt.EditRole:
            return val

        # Boolean checkbox display
        if key in self._bool_cols:
            if role == Qt.CheckStateRole:
                return Qt.Checked if _to_bool(val) else Qt.Unchecked
            if role in (Qt.DisplayRole, Qt.EditRole):
                return None

        # Password masking
        if header == self._pw_col_name:
            if role == Qt.DisplayRole:
                s = '' if val in (None, '') else str(val)
                return '*' * len(s)

        # Colour: show a small swatch + normalised hex
        if self._color_col_name and header == self._color_col_name:
            c = _parse_color(val)
            if role == Qt.DecorationRole and c is not None:
                return c
            if role == Qt.DisplayRole:
                return '' if c is None else _color_to_hex(c)

        # AccessRights: show name instead of ID
        if self._access_col and header == self._access_col:
            if role == Qt.DisplayRole:
                try:
                    return self._access_id2name.get(int(val), '') if val is not None else ''
                except Exception:
                    return self._access_id2name.get(val, '')

        if role == Qt.DisplayRole:
            return '' if val is None else str(val)
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        return None

    def flags(self, index: QModelIndex):
        """ID-Spalte read-only; Active checkable; AccentColour editierbar; andere editierbar."""
        if not index.isValid():
            return Qt.ItemIsEnabled
        header = self._headers[index.column()]
        key = _canon(header)
        f = Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable
        if key in self._bool_cols:
            f |= Qt.ItemIsUserCheckable
        return f

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        """Setzt einen Zellwert und markiert die Zeile als dirty.

        Behandelt CheckStateRole (Active), EditRole (alle anderen).
        AccessRight-Namen werden via name2id in IDs aufgelöst.
        """
        if not index.isValid():
            return False
        header = self._headers[index.column()]
        key = _canon(header)

        # Boolean checkbox
        if key in self._bool_cols:
            if role in (Qt.CheckStateRole, Qt.EditRole):
                new_val = 1 if (value == Qt.Checked or _to_bool(value)) else 0
                self._rows[index.row()][header] = new_val
                self._dirty_cells.add((index.row(), index.column()))
                self.dataChanged.emit(
                    index, index, [Qt.DisplayRole, Qt.EditRole, Qt.CheckStateRole])
                return True
            return False

        if role != Qt.EditRole:
            return False

        # Normalise colour values to '#RRGGBB' (stored as text)
        if self._color_col_name and header == self._color_col_name:
            c = None
            if isinstance(value, QColor):
                c = value
            else:
                c = _parse_color(value)
            value = '' if c is None else _color_to_hex(c)

        # normalize strings
        if isinstance(value, str):
            value = value.strip()
        self._rows[index.row()][header] = value
        self._dirty_cells.add((index.row(), index.column()))
        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
        return True

    def dirty_rows(self) -> List[Dict]:
        """Gibt alle geänderten Zeilen zurück (für SQL-UPDATE)."""
        if not self._dirty_cells:
            return []
        dirty_row_indices = sorted({r for (r, _) in self._dirty_cells})
        return [self._rows[i] for i in dirty_row_indices]

    def clear_dirty(self):
        """Leert das Dirty-Set nach erfolgreichem Speichern."""
        self._dirty_cells.clear()

    def id_column(self) -> str:
        """Gibt den Namen der ID-Spalte zurück."""
        return self._id_col

    def headers(self) -> List[str]:
        """Gibt die Spaltennamen zurück."""
        return self._headers

    def rows(self) -> List[Dict]:
        """Gibt alle Datenzeilen zurück (ungefiltert)."""
        return self._rows


# ---- Filter über First/Last Name --------------------------------------------
class NameFilterProxy(QSortFilterProxyModel):
    """Filter-Proxy: sucht in Name- und Username-Spalten (case-insensitive)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.first_idx = -1
        self.last_idx = -1
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setDynamicSortFilter(True)
        # Important for numeric sorting by ID, we will set SortRole=EditRole in screen.

    def set_name_columns(self, headers: List[str]):
        """Ermittelt Spaltenindizes für Username, FirstName, LastName für den Filter."""
        self.first_idx = -1
        self.last_idx = -1
        for i, h in enumerate(headers):
            k = _canon(h)
            if self.first_idx == -1 and k in {'firstname', 'first_name', 'first'}:
                self.first_idx = i
            if self.last_idx == -1 and k in {'lastname', 'last_name', 'surname', 'last'}:
                self.last_idx = i

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        """Gibt True zurück wenn mindestens eine Name-Spalte dem Filter entspricht."""
        rx = self.filterRegularExpression()
        if not rx.pattern():
            return True

        def match_col(col_idx: int) -> bool:
            if col_idx < 0:
                return False
            idx = self.sourceModel().index(source_row, col_idx)
            data = self.sourceModel().data(idx, Qt.DisplayRole)
            return rx.match(str(data)).hasMatch()

        return match_col(self.first_idx) or match_col(self.last_idx)


# ---- Screen -----------------------------------------------------------------
class ManageUserScreen(QWidget):
    def __init__(self, on_back_home=None, sidebar_callbacks: Optional[dict] = None):
        super().__init__()
        self.on_back_home = on_back_home
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None

        self.table: Optional[QTableView] = None
        self.model: Optional[UsersTableModel] = None
        self.proxy: Optional[NameFilterProxy] = None

        self.search_edit: Optional[QLineEdit] = None
        self.btn_reload: Optional[QPushButton] = None
        self.btn_new: Optional[QPushButton] = None
        self.btn_reset_pw: Optional[QPushButton] = None
        self.btn_delete: Optional[QPushButton] = None
        self.btn_save: Optional[QPushButton] = None
        self.status_label: Optional[QLabel] = None

        self._id_col = 'ID'
        self._access_col = None  # actual header name for AccessRights
        self._color_col = None   # actual header name for Colour/Color
        self._access_id2name: Dict[int, str] = {}
        self._access_delegate: Optional[AccessRightDelegate] = None

        self._build_ui()
        self.reload_data()

    def _on_access(self):
        from ui.widgets.feature_access_dialog import open_feature_access
        open_feature_access(self)

    def _build_ui(self):
        """Erstellt Header, Toolbar (Suche + Buttons), Tabelle, Detailpanel und Footer."""
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

        self.search_edit = QLineEdit(
            placeholderText='Filter by First/Last Name…')
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._on_search_changed)

        self.btn_reload = QPushButton('Reload', objectName='GreyBtn')
        self.btn_reload.clicked.connect(self.reload_data)

        self.btn_new = QPushButton('New User', objectName='GreenBtn')
        self.btn_new.clicked.connect(self._on_new)

        self.btn_api_key = QPushButton('🔑 API Key', objectName='GreyBtn')
        self.btn_api_key.clicked.connect(self._on_set_api_key)

        self.btn_reset_pw = QPushButton('Reset Password', objectName='GreyBtn')
        self.btn_reset_pw.clicked.connect(self._on_reset_password)

        self.btn_delete = QPushButton('Delete', objectName='GreyBtn')
        self.btn_delete.clicked.connect(self._on_delete)

        self.btn_save = QPushButton('Save Changes', objectName='PurpleBtn')
        self.btn_save.clicked.connect(self.save_changes)

        # which tools/screens groups and people may use (db/feature_access.py)
        self.btn_access = QPushButton('Access…', objectName='GreyBtn')
        self.btn_access.setToolTip('Switch tools and screens on or off - per group or per person')
        self.btn_access.clicked.connect(self._on_access)

        self.status_label = QLabel('')

        tl.addWidget(self.search_edit, 1)
        tl.addWidget(self.btn_reload, 0)
        tl.addWidget(self.btn_new, 0)
        tl.addWidget(self.btn_api_key, 0)
        tl.addWidget(self.btn_reset_pw, 0)
        tl.addWidget(self.btn_delete, 0)
        tl.addWidget(self.btn_access, 0)
        tl.addWidget(self.btn_save, 0)
        tl.addWidget(self.status_label, 0, Qt.AlignVCenter)

        # table
        self.table = QTableView(objectName='UsersTable')
        self.table.setAlternatingRowColors(False)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.clicked.connect(self._on_table_clicked)
        self.table.doubleClicked.connect(self._on_table_clicked)
        # Styling like jets
        self.table.setStyleSheet("""
            QTableView#UsersTable { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView#UsersTable::item { color: black; }
            QTableView#UsersTable::item:selected { background: #b7d6ff; color: black; }
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

    def _on_search_changed(self, text: str):
        """Aktualisiert den Proxy-Filter bei Texteingabe im Suchfeld."""
        if not self.proxy:
            return
        if not text:
            self.proxy.setFilterRegularExpression(QRegularExpression())
            return
        rx = QRegularExpression('.*' + QRegularExpression.escape(text) + '.*')
        rx.setPatternOptions(QRegularExpression.CaseInsensitiveOption)
        self.proxy.setFilterRegularExpression(rx)

    def _on_table_clicked(self, index: QModelIndex):
        """Öffnet bei Klick auf die AccentColour-Spalte einen QColorDialog."""
        """Open a colour picker when the user clicks the Colour/Color cell."""
        if not (self.table and self.model and self.proxy and self._color_col):
            return
        try:
            color_col_idx = self.model.headers().index(self._color_col)
        except Exception:
            return
        if index.column() != color_col_idx:
            return

        # Get current colour (source model stores the raw value)
        try:
            src_idx = self.proxy.mapToSource(index)
            current_raw = self.model.data(src_idx, Qt.EditRole)
        except Exception:
            current_raw = None

        start = _parse_color(current_raw) or QColor('#FFFFFF')
        chosen = QColorDialog.getColor(start, self, 'Choose colour')
        if not chosen or not chosen.isValid():
            return

        hex_value = _color_to_hex(chosen)
        # Use a 0ms timer so the view finishes processing the click/selection first.
        QTimer.singleShot(0, lambda: self.proxy.setData(
            index, hex_value, Qt.EditRole))

    # ---- data layer ----
    def _load_users(self) -> List[Dict]:
        """All users without password columns: db/user_admin.load_users (shared with the web app)."""
        from db import user_admin
        return user_admin.load_users()

    def reload_data(self):
        """Lädt alle Benutzerdaten neu aus der DB (inkl. AccessRight-Map) und baut Modell neu auf."""
        # Load users
        rows = self._load_users()
        headers = list(rows[0].keys()) if rows else [self._id_col]

        # Remove password columns from UI entirely (pw, pw_hash, password_hash, etc.)
        if rows:
            remove_keys = set()
            for k in rows[0].keys():
                ck = _canon(k)
                if ck in {"pw", "pwhash", "pw_hash", "passwordhash", "password_hash", "passworthash"}:
                    remove_keys.add(k)

            if remove_keys:
                for r in rows:
                    for k in list(remove_keys):
                        r.pop(k, None)

                headers = [h for h in headers if h not in remove_keys]

        
        # Determine ID column name
        for h in headers:
            if h.lower() == 'id':
                self._id_col = h
                break

        # Identify AccessRights header
        self._access_col = None
        for h in headers:
            if _canon(h) in {'accessrights', 'rights', 'role'}:
                self._access_col = h
                break

        # Identify Colour header
        self._color_col = None
        for h in headers:
            if _canon(h) in {'colour', 'color'}:
                self._color_col = h
                break

        # Load FK map for AccessRights
        self._access_id2name, _ = load_access_rights_map()

        # Keine Admin/Superuser-Checkboxen mehr (Rechte laufen über AccessLevel)
        bool_cols: Set[str] = set()
        # Build model
        self.model = UsersTableModel(
            rows, headers,
            id_column=self._id_col,
            bool_columns=bool_cols,
            access_rights_col=self._access_col,
            id2name_access=self._access_id2name
        )

        # Proxy for filtering + numeric sorting
        if not self.proxy:
            self.proxy = NameFilterProxy(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.set_name_columns(headers)
        self.proxy.setSortRole(Qt.EditRole)  # numeric sort by ID
        self.table.setModel(self.proxy)

        # Delegate for AccessRights column
        if self._access_col is not None:
            if not self._access_delegate:
                self._access_delegate = AccessRightDelegate(
                    self._access_id2name, self.table)
            # find column index
            col_idx = headers.index(self._access_col)
            self.table.setItemDelegateForColumn(col_idx, self._access_delegate)

        # Auto-size & default sort by ID ascending
        self.table.resizeColumnsToContents()
        # find id column index
        id_idx = 0
        for i, h in enumerate(headers):
            if h == self._id_col:
                id_idx = i
                break
        self.table.sortByColumn(id_idx, Qt.AscendingOrder)

        self._set_status(f'{len(rows)} user(s) loaded.')
        # keep current search
        self._on_search_changed(self.search_edit.text())

    def save_changes(self):
        """Schreibt alle dirty Zeilen via UPDATE in die DB.

        AccentColour wird als Hex-String gespeichert, Active als 0/1.
        AccessRight wird als ID gespeichert (nicht als Name).
        """
        if not self.model:
            return
        dirty_rows = self.model.dirty_rows()
        if not dirty_rows:
            self._set_status('No changes to save.')
            return
        id_col = self.model.id_column() or 'ID'
        total = 0
        try:
            from db import user_admin
            headers = self.model.headers()
            total = user_admin.save_changes([{c: r[c] for c in headers if c in r} for r in dirty_rows], id_col)
            self._set_status(f'Saved {total} update(s).')
            self.model.clear_dirty()
        except Exception as e:
            QMessageBox.critical(self, 'Save failed', str(e))
            self._set_status(f'Save failed: {e}', error=True)

    def _on_new(self):
        """Öffnet einen Dialog zur Neuanlage eines Benutzers (Username + Passwort).

        Legt den Benutzer in tblUser an, setzt Passwort-Hash (Argon2) und
        weist Standard-AccessRight zu. Lädt danach Tabelle neu.
        """
        """Creates a new user row with sane defaults (data: db/user_admin, shared with the web app)."""
        try:
            from db import user_admin
            candidate = user_admin.next_username()

            # Ask for an initial password (pw_hash is typically NOT NULL)
            pw, ok = QInputDialog.getText(
                self, 'New User – Set Password', f'Enter an initial password for "{candidate}":',
                QLineEdit.Password, '')
            if not ok:
                return
            if not (pw or '').strip():
                QMessageBox.warning(self, 'New User', 'Password cannot be empty.')
                return
            if (pw or '').strip().lower() == candidate.lower():
                QMessageBox.warning(self, 'New User', 'Password must not be the same as the username.')
                return
            rep, ok2 = QInputDialog.getText(self, 'New User – Set Password', 'Repeat the password:',
                                            QLineEdit.Password, '')
            if not ok2:
                return
            problem = user_admin.check_new_password(candidate, pw, rep)
            if problem:
                QMessageBox.warning(self, 'New User', problem)
                return
            new_id = user_admin.create_user(candidate, pw)

            self.reload_data()
            if new_id is not None:
                self._select_row_by_id(new_id)
            self._set_status(f'New user created ({candidate}).')
        except Exception as e:
            QMessageBox.critical(self, 'Create failed', str(e))
            self._set_status(f'Create failed: {e}', error=True)

    def _on_reset_password(self):
        """Öffnet einen Dialog zum Zurücksetzen des Passworts eines selektierten Benutzers.

        Nur für Admins. Speichert neues Passwort als Argon2-Hash in tblUser.
        """
        """Reset password for the selected user (superuser-only screen)."""
        if not (self.model and self.proxy):
            return

        # Identify username column
        username_col = None
        for h in self.model.headers():
            if _canon(h) == 'username':
                username_col = h
                break
        if not username_col:
            QMessageBox.critical(self, 'Reset Password', 'Could not find a "Username" column in tblUser.')
            return

        sel_rows = self._source_selection_rows()
        if not sel_rows:
            self._set_status('Select a user first.')
            return
        if len(sel_rows) != 1:
            QMessageBox.information(self, 'Reset Password', 'Please select exactly one user to reset the password.')
            return

        src_row = sel_rows[0]
        username = str(self.model.rows()[src_row].get(username_col) or '').strip()
        if not username:
            QMessageBox.warning(self, 'Reset Password', 'Selected row has no username.')
            return

        # Ask for new password
        pw, ok = QInputDialog.getText(
            self,
            'Reset Password',
            f'Enter a new password for "{username}":',
            QLineEdit.Password,
            ''
        )
        if not ok:
            return
        if not (pw or '').strip():
            QMessageBox.warning(self, 'Reset Password', 'Password cannot be empty.')
            return
        if (pw or '').strip().lower() == username.lower():
            QMessageBox.warning(self, 'Reset Password', 'Password must not be the same as the username.')
            return
        rep, ok2 = QInputDialog.getText(self, 'Reset Password', 'Repeat the new password:', QLineEdit.Password, '')
        if not ok2:
            return
        from db import user_admin   # rules + Argon2 hash shared with the web app
        problem = user_admin.check_new_password(username, pw, rep)
        if problem:
            QMessageBox.warning(self, 'Reset Password', problem)
            return
        try:
            if user_admin.reset_password(username, pw):
                QMessageBox.information(self, 'Reset Password', f'Password updated for "{username}".')
                self._set_status(f'Password reset for {username}.')
            else:
                QMessageBox.critical(self, 'Reset Password', 'Password could not be updated.')
                self._set_status('Password reset failed.', error=True)
        except Exception as e:
            QMessageBox.critical(self, 'Reset Password', str(e))
            self._set_status(f'Password reset failed: {e}', error=True)

    def _on_set_api_key(self):
        """Setzt den verschlüsselten Anthropic API Key für den selektierten User."""
        try:
            from cryptography.fernet import Fernet
        except ImportError:
            QMessageBox.critical(self, 'API Key', 'cryptography-Paket fehlt.\n\npip install cryptography')
            return

        if not (self.model and self.proxy):
            return

        # Username-Spalte finden
        username_col = None
        id_col       = None
        for h in self.model.headers():
            if _canon(h) == 'username':
                username_col = h
            if _canon(h) == 'id':
                id_col = h

        if not username_col:
            QMessageBox.critical(self, 'API Key', 'Username column not found.')
            return

        sel_rows = self._source_selection_rows()
        if not sel_rows:
            self._set_status('Erst einen User selektieren.')
            return
        if len(sel_rows) != 1:
            QMessageBox.information(self, 'API Key', 'Please select exactly one user.')
            return

        src_row  = sel_rows[0]
        row_data = self.model.rows()[src_row]
        username = str(row_data.get(username_col) or '').strip()
        user_id  = row_data.get(id_col)

        # MASTER_KEY laden
        master_key = _load_master_key()
        if not master_key:
            QMessageBox.critical(
                self, 'API Key',
                'MASTER_KEY not found.\n'
                '\n'
                'secrets.enc missing or invalid.'
            )
            return

        # Dialog: API Key + Token Limit
        dlg = QDialog(self)
        dlg.setWindowTitle(f'API Key setzen – {username}')
        dlg.setMinimumWidth(420)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        lay.addWidget(QLabel(f'<b>User:</b> {username}'))

        form = QFormLayout()
        form.setSpacing(8)

        key_input = QLineEdit()
        key_input.setPlaceholderText('sk-ant-api03-...')
        key_input.setEchoMode(QLineEdit.Password)
        key_input.setMinimumWidth(300)
        form.addRow('Anthropic API Key:', key_input)

        limit_input = QSpinBox()
        limit_input.setRange(0, 10_000_000)
        limit_input.setSingleStep(100_000)
        limit_input.setValue(500_000)
        limit_input.setSuffix(' Tokens')
        form.addRow('Token-Limit (Monat):', limit_input)

        lay.addLayout(form)

        hint = QLabel('The API key is stored encrypted in the DB.\nNever in plain text.')
        hint.setStyleSheet('color:#888; font-size:10px;')
        lay.addWidget(hint)

        # Löschen-Option
        btn_clear = QPushButton('🗑  API Key entfernen')
        btn_clear.setObjectName('GreyBtn')
        lay.addWidget(btn_clear)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)

        # Löschen-Button: sofort ausführen + Dialog schliessen
        def _do_clear():
            try:
                from db.connection import execute as db_execute
                db_execute(
                    'UPDATE tbluser SET api_key_enc=NULL, tokens_used=0, tokens_reset=NULL '
                    'WHERE ID=%s', [user_id]
                )
                dlg.reject()
                self._set_status(f'API key for {username} removed.')
            except Exception as e:
                QMessageBox.critical(dlg, 'Error', str(e))

        btn_clear.clicked.connect(_do_clear)

        if not dlg.exec():
            return

        api_key = key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, 'API Key', 'The API key must not be empty.')
            return
        if not api_key.startswith('sk-ant-'):
            QMessageBox.warning(self, 'API Key', 'Invalid format – must start with "sk-ant-".')
            return

        # Verschlüsseln
        try:
            f          = Fernet(master_key)
            enc_bytes  = f.encrypt(api_key.encode('utf-8'))
            enc_str    = enc_bytes.decode('utf-8')
        except Exception as e:
            QMessageBox.critical(self, 'Encryption failed', str(e))
            return

        # In DB schreiben
        try:
            from db.connection import execute as db_execute
            import datetime
            db_execute(
                'UPDATE tbluser SET api_key_enc=%s, token_limit=%s, tokens_used=0, '
                'tokens_reset=%s WHERE ID=%s',
                [enc_str, limit_input.value(),
                 datetime.date.today().replace(day=1).isoformat(), user_id]
            )
            QMessageBox.information(
                self, 'API Key gesetzt',
                f'API key for «{username}» was encrypted and saved.\n'
                f'Token-Limit: {limit_input.value():,}'
            )
            self._set_status(f'API key for {username} set.')
        except Exception as e:
            QMessageBox.critical(self, 'DB error', str(e))
            self._set_status(f'Error: {e}', error=True)

    def _on_delete(self):
        """Löscht die selektierten Benutzer nach Bestätigung aus der DB."""
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

        if QMessageBox.question(self, 'Confirm Delete', f'Delete {len(ids)} user(s)?') != QMessageBox.Yes:
            return
        try:
            from db import user_admin
            user_admin.delete_users(ids, id_col)
            self.reload_data()
            self._set_status(f'Deleted {len(ids)} user(s).')
        except Exception as e:
            QMessageBox.critical(self, 'Delete failed', str(e))
            self._set_status(f'Delete failed: {e}', error=True)

    # ---- helpers ----
    def _source_selection_rows(self) -> List[int]:
        """Gibt die Zeilen-Indizes der aktuellen Selektion im Source-Modell zurück."""
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
        """Selektiert die Zeile mit der gegebenen ID und scrollt dorthin."""
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
        """Setzt den Statustext (rot bei error=True)."""
        self.status_label.setStyleSheet('color: #c62828;' if error else '')
        self.status_label.setText(text)

    def _go_home(self):
        """Navigiert zurück zum Home-Screen."""
        if callable(self.on_back_home):
            self.on_back_home()