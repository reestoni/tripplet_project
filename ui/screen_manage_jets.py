# ui/screen_manage_jets.py
"""Verwaltungsscreen für Jet-Geometrien (tblJet).

Zeigt alle Jets in einer editierbaren Tabelle mit eingefrorener erster Spalte.
Unterstützt Filter, Neuanlage, Kopieren, Löschen und Inline-Bearbeiten.
Änderungen werden erst nach «Save Changes» in die DB geschrieben.

Spezialitäten:
  - Bool-Spalten (StandardJet, Rohling) werden als Checkbox-Icons angezeigt
  - FK-Spalten verwenden FKComboDelegate für lesbare Namen in der Tabelle
  - FrozenNColumnsTable friert die ersten N Spalten ein (Standard: 1)
"""

from ui.theme import accent_tint, accent_gridline
from typing import List, Dict, Callable, Optional, Set
from decimal import Decimal

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, QRegularExpression, Slot, QEvent, QPoint
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QSizePolicy, QTableView, QMessageBox, QLineEdit, QComboBox, QStyledItemDelegate,
    QAbstractItemView, QHeaderView, QMenu, QWidgetAction, QDialog
)
from PySide6.QtGui import QPixmap, QColor, QKeySequence, QFont, QAction, QPainter, QPen, QBrush
from PySide6.QtWidgets import QApplication

from ui.widgets.footer import FooterBar
from ui.widgets.header import HeaderBar
from ui.pathutil import resource_path
from ui.text_normalize import canon_with_id_strip as _canon


def _to_int_like(val):
    """Konvertiert int/float/Decimal/str sicher zu int, oder None bei Fehler."""
    try:
        if isinstance(val, int):
            return val
        if isinstance(val, float):
            from math import isclose
            return int(val) if isclose(val, int(val), rel_tol=0, abs_tol=1e-9) else None
        if isinstance(val, Decimal):
            i = int(val)
            return i if val == Decimal(i) else None
        s = str(val).strip()
        if s.endswith(".0"):
            s = s[:-2]
        return int(s)
    except Exception:
        return None


def _to_bool(val) -> bool:
    """Konvertiert diverse Eingaben (0/1, True/False, "yes"/"no" usw.) robust zu bool."""
    if isinstance(val, bool):
        return val
    if val in (1, -1):
        return True
    if val in (0, None):
        return False
    try:
        if isinstance(val, Decimal):
            return val != 0
        s = str(val).strip().lower()
        if s in ("true", "t", "yes", "y", "1", "-1"):
            return True
        if s in ("false", "f", "no", "n", "0", ""):
            return False
    except Exception:
        pass
    try:
        return float(val) != 0.0
    except Exception:
        return False


# ----------------- Multi-column filter proxy -----------------
class MultiColumnFilterProxy(QSortFilterProxyModel):
    """Proxy that AND-combines per-column filters (case-insensitive).

    Two filter types per column:
      - Text  : set_column_filter(col, text)         stored as str in _filters
      - Range : set_range_filter(col, lo, hi)        stored as (lo, hi) tuple
                lo/hi are float or None (open-ended)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filters: Dict[int, object] = {}   # str  OR  (lo, hi)

    # ---- text filter ----
    def set_column_filter(self, col: int, text: str):
        """Set or clear a text substring filter for a column."""
        text = text.strip()
        if text:
            self._filters[col] = text.lower()
        else:
            self._filters.pop(col, None)
        self.invalidateFilter()

    # ---- range filter ----
    def set_range_filter(self, col: int, lo: Optional[float], hi: Optional[float]):
        """Set or clear a numeric range filter. Pass lo=None, hi=None to clear."""
        if lo is None and hi is None:
            self._filters.pop(col, None)
        else:
            self._filters[col] = (lo, hi)
        self.invalidateFilter()

    def active_filters(self) -> Dict[int, object]:
        """Return a copy of the currently active filters."""
        return dict(self._filters)

    def clear_all_filters(self):
        """Remove all column filters."""
        self._filters.clear()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        src = self.sourceModel()
        if src is None:
            return True
        for col, filt in self._filters.items():
            idx = src.index(source_row, col, source_parent)
            val = src.data(idx, Qt.DisplayRole)
            if isinstance(filt, tuple):
                # numeric range
                lo, hi = filt
                try:
                    num = float(str(val).replace(",", "."))
                except (TypeError, ValueError):
                    return False
                if lo is not None and num < lo:
                    return False
                if hi is not None and num > hi:
                    return False
            else:
                # text substring
                if val is None:
                    return False
                if filt not in str(val).lower():
                    return False
        return True


# ----------------- Filterable header view -----------------
class FilterableHeaderView(QHeaderView):
    """QHeaderView subclass with right-click filter popup per section.

    - Text columns  : "contains" QLineEdit
    - Numeric columns: "von / bis" two QLineEdit fields (both optional)
    Active filters show a green ▼ in the section corner.
    Both left/right headers share the same MultiColumnFilterProxy.
    """

    def __init__(self, orientation, parent=None, proxy: Optional["MultiColumnFilterProxy"] = None):
        super().__init__(orientation, parent)
        self._proxy: Optional[MultiColumnFilterProxy] = proxy
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

    def set_proxy(self, proxy: "MultiColumnFilterProxy"):
        """Assign the shared filter proxy."""
        self._proxy = proxy

    def paintSection(self, painter, rect, logical_index):
        """Draw a green ▼ in active-filter sections."""
        super().paintSection(painter, rect, logical_index)
        if self._proxy and logical_index in self._proxy.active_filters():
            painter.save()
            painter.setPen(QColor("#1a6b1a"))
            f = painter.font()
            f.setBold(True)
            painter.setFont(f)
            painter.drawText(rect.adjusted(0, 0, -4, -2), Qt.AlignRight | Qt.AlignBottom, "▼")
            painter.restore()

    # ------------------------------------------------------------------ #
    @staticmethod
    def _is_numeric_col(src_model, logical: int, sample: int = 20) -> bool:
        """Heuristic: column is numeric if >50% of sampled non-empty values parse as float."""
        if src_model is None:
            return False
        rows = src_model.rowCount()
        checked = numeric = 0
        for r in range(min(rows, sample)):
            val = src_model.data(src_model.index(r, logical), Qt.DisplayRole)
            if val is None or str(val).strip() == "":
                continue
            checked += 1
            try:
                float(str(val).replace(",", "."))
                numeric += 1
            except ValueError:
                pass
        return checked > 0 and (numeric / checked) > 0.5

    # ------------------------------------------------------------------ #
    def _on_context_menu(self, pos: QPoint):
        if self._proxy is None:
            return
        logical = self.logicalIndexAt(pos)
        if logical < 0:
            return

        src_model = self._proxy.sourceModel()
        col_name = (src_model.headerData(logical, Qt.Horizontal, Qt.DisplayRole)
                    if src_model else str(logical))
        current = self._proxy.active_filters().get(logical)
        numeric = self._is_numeric_col(src_model, logical)

        menu = QMenu(self)
        menu.setMinimumWidth(240)

        # Title
        title_label = QLabel(f"  Filter: <b>{col_name}</b>")
        title_label.setContentsMargins(8, 6, 8, 2)
        ta = QWidgetAction(menu)
        ta.setDefaultWidget(title_label)
        menu.addAction(ta)
        menu.addSeparator()

        if numeric:
            # ---- range input (von / bis) --------------------------------
            lo_val = hi_val = ""
            if isinstance(current, tuple):
                lo, hi = current
                lo_val = "" if lo is None else str(lo)
                hi_val = "" if hi is None else str(hi)

            container = QWidget()
            cl = QHBoxLayout(container)
            cl.setContentsMargins(8, 4, 8, 4)
            cl.setSpacing(6)

            lbl_von = QLabel("Von:")
            edit_lo = QLineEdit()
            edit_lo.setPlaceholderText("min")
            edit_lo.setText(lo_val)
            edit_lo.setFixedWidth(72)

            lbl_bis = QLabel("Bis:")
            edit_hi = QLineEdit()
            edit_hi.setPlaceholderText("max")
            edit_hi.setText(hi_val)
            edit_hi.setFixedWidth(72)

            cl.addWidget(lbl_von)
            cl.addWidget(edit_lo)
            cl.addWidget(lbl_bis)
            cl.addWidget(edit_hi)
            cl.addStretch()

            wa = QWidgetAction(menu)
            wa.setDefaultWidget(container)
            menu.addAction(wa)
            menu.addSeparator()

            def _apply_range():
                def _parse(s):
                    s = s.strip().replace(",", ".")
                    try:
                        return float(s) if s else None
                    except ValueError:
                        return None
                lo = _parse(edit_lo.text())
                hi = _parse(edit_hi.text())
                self._apply_range_filter(logical, lo, hi)

            clear_action = QAction("✕  Clear this filter", menu)
            clear_action.setEnabled(current is not None)
            clear_action.triggered.connect(lambda: self._apply_range_filter(logical, None, None))
            menu.addAction(clear_action)

            clear_all_action = QAction("✕  Clear all filters", menu)
            clear_all_action.setEnabled(bool(self._proxy.active_filters()))
            clear_all_action.triggered.connect(self._clear_all)
            menu.addAction(clear_all_action)

            for ed in (edit_lo, edit_hi):
                ed.returnPressed.connect(lambda: (_apply_range(), menu.close()))

            menu.aboutToHide.connect(_apply_range)

        else:
            # ---- text input (contains) ----------------------------------
            current_text = current if isinstance(current, str) else ""

            container = QWidget()
            cl = QHBoxLayout(container)
            cl.setContentsMargins(8, 4, 8, 4)
            edit = QLineEdit()
            edit.setPlaceholderText("contains…")
            edit.setText(current_text)
            edit.setMinimumWidth(160)
            edit.setClearButtonEnabled(True)
            cl.addWidget(edit)

            wa = QWidgetAction(menu)
            wa.setDefaultWidget(container)
            menu.addAction(wa)
            menu.addSeparator()

            clear_action = QAction("✕  Clear this filter", menu)
            clear_action.setEnabled(bool(current_text))
            clear_action.triggered.connect(lambda: self._apply_text_filter(logical, ""))
            menu.addAction(clear_action)

            clear_all_action = QAction("✕  Clear all filters", menu)
            clear_all_action.setEnabled(bool(self._proxy.active_filters()))
            clear_all_action.triggered.connect(self._clear_all)
            menu.addAction(clear_all_action)

            edit.returnPressed.connect(lambda: (self._apply_text_filter(logical, edit.text()), menu.close()))
            menu.aboutToHide.connect(lambda: self._apply_text_filter(logical, edit.text()))

        global_pos = self.mapToGlobal(QPoint(self.sectionViewportPosition(logical), self.height()))
        menu.exec(global_pos)

    def _apply_text_filter(self, col: int, text: str):
        if self._proxy:
            self._proxy.set_column_filter(col, text)
            self.viewport().update()

    def _apply_range_filter(self, col: int, lo: Optional[float], hi: Optional[float]):
        if self._proxy:
            self._proxy.set_range_filter(col, lo, hi)
            self.viewport().update()

    def _clear_all(self):
        if self._proxy:
            self._proxy.clear_all_filters()
            self.viewport().update()


# ----------------- Frozen N Columns Table -----------------
class FrozenNColumnsTable(QWidget):
    """
    Composite widget that freezes the first N columns (N>=1) on the left side.
    """

    def __init__(self, parent: Optional[QWidget] = None, freeze_count: int = 1, objectName: Optional[str] = None):
        super().__init__(parent)
        self._model = None
        self._freeze = max(1, int(freeze_count))
        self._filter_proxy: Optional[MultiColumnFilterProxy] = None

        self.left = QTableView(self)
        self.right = QTableView(self)

        if objectName:
            self.left.setObjectName(objectName)
            self.right.setObjectName(objectName)

        # FilterableHeaderView on both sides; proxy wired later via set_filter_proxy()
        self._left_header = FilterableHeaderView(Qt.Horizontal, self.left)
        self._right_header = FilterableHeaderView(Qt.Horizontal, self.right)
        self.left.setHorizontalHeader(self._left_header)
        self.right.setHorizontalHeader(self._right_header)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.left)
        lay.addWidget(self.right)

        self.left.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        for v in (self.left, self.right):
            v.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
            v.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        self.left.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.left.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._left_header.setSectionsMovable(False)
        self._right_header.setSectionsMovable(False)

        self.setFocusProxy(self.right)

        self.right.verticalScrollBar().valueChanged.connect(
            self.left.verticalScrollBar().setValue
        )

        self.right.verticalHeader().sectionResized.connect(
            self._sync_row_height_right_to_left)
        self.left.verticalHeader().sectionResized.connect(
            self._sync_row_height_left_to_right)

        self.right.verticalHeader().installEventFilter(self)
        self.left.installEventFilter(self)
        self.right.installEventFilter(self)
        self.left.viewport().installEventFilter(self)
        self._sync_vheader_visibility()

        self.left.setFrameShape(self.right.frameShape())
        self.left.setFrameShadow(self.right.frameShadow())
        self.left.setCornerButtonEnabled(False)
        self.right.setCornerButtonEnabled(False)

    def set_filter_proxy(self, proxy: MultiColumnFilterProxy):
        """Wire the shared MultiColumnFilterProxy to both header views."""
        self._filter_proxy = proxy
        self._left_header.set_proxy(proxy)
        self._right_header.set_proxy(proxy)

    def setModel(self, model):
        """Setzt dasselbe Model auf beide Ansichten und verbirgt/zeigt die richtigen Spalten."""
        self._model = model
        from PySide6.QtCore import QItemSelectionModel
        sel = QItemSelectionModel(model)
        self.left.setModel(model)
        self.right.setModel(model)
        self.left.setSelectionModel(sel)
        self.right.setSelectionModel(sel)

        self._apply_column_visibility()

        self.left.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.right.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        self._update_left_width()
        self.left.horizontalHeader().sectionResized.connect(self._maybe_update_left_width)
        self.right.horizontalHeader().sectionResized.connect(self._maybe_update_left_width)

    def model(self):
        """Gibt das aktuell gesetzte Model zurück."""
        return self._model

    def setSortingEnabled(self, enabled: bool):
        """Aktiviert/deaktiviert Sortierung auf der rechten Ansicht."""
        self.left.setSortingEnabled(enabled)
        self.right.setSortingEnabled(enabled)

    def setSelectionBehavior(self, behavior):
        """Setzt SelectionBehavior auf beiden Ansichten."""
        self.left.setSelectionBehavior(behavior)
        self.right.setSelectionBehavior(behavior)

    def setSelectionMode(self, mode):
        """Setzt SelectionMode auf beiden Ansichten."""
        self.left.setSelectionMode(mode)
        self.right.setSelectionMode(mode)

    def setAlternatingRowColors(self, on: bool):
        """Setzt alternating row colors auf beiden Ansichten."""
        self.left.setAlternatingRowColors(on)
        self.right.setAlternatingRowColors(on)

    def setShowGrid(self, on: bool):
        """Zeigt/versteckt das Gitternetz auf beiden Ansichten."""
        self.left.setShowGrid(on)
        self.right.setShowGrid(on)

    def setStyleSheet(self, style: str):
        QWidget.setStyleSheet(self, style)
        self.left.setStyleSheet(style)
        self.right.setStyleSheet(style)

    def resizeColumnsToContents(self):
        """Passt Spaltenbreiten an Inhalt an (beide Ansichten)."""
        self.left.resizeColumnsToContents()
        self.right.resizeColumnsToContents()
        self._update_left_width()

    def horizontalHeader(self):
        """Gibt den horizontalen Header der rechten Ansicht zurück."""
        return self.right.horizontalHeader()

    def verticalHeader(self):
        """Gibt den vertikalen Header der rechten Ansicht zurück."""
        return self.right.verticalHeader()

    def setItemDelegateForColumn(self, column: int, delegate):
        """Setzt einen Delegate für eine Spalte (mit Spalten-Offset für die rechte Ansicht)."""
        try:
            self.left.setItemDelegateForColumn(column, delegate)
        except Exception:
            pass
        try:
            self.right.setItemDelegateForColumn(column, delegate)
        except Exception:
            pass

    def selectionModel(self):
        """Gibt das gemeinsame SelectionModel zurück."""
        return self.right.selectionModel()

    def selectRow(self, row: int):
        """Selektiert eine Zeile auf beiden Ansichten."""
        return self.right.selectRow(row)

    def scrollToBottom(self):
        """Scrollt zur letzten Zeile."""
        return self.right.scrollToBottom()

    def scrollTo(self, index, hint=QAbstractItemView.EnsureVisible):
        """Scrollt zu einem bestimmten Index."""
        return self.right.scrollTo(index, hint)

    def setCurrentIndex(self, index):
        """Setzt den aktuellen Index auf beiden Ansichten."""
        return self.right.setCurrentIndex(index)

    def edit(self, index):
        """Startet die In-Place-Bearbeitung einer Zelle."""
        return self.right.edit(index)

    def copy_selection_to_clipboard(self):
        """Kopiert die selektierten Zellen als TSV in die Zwischenablage (kompatibel mit Excel).
        Wenn ganze Zeilen selektiert sind (alle sichtbaren Spalten), wird die Titelzeile vorangestellt."""
        sel = self.right.selectionModel()
        if not sel or not sel.hasSelection():
            return

        indexes = sorted(sel.selectedIndexes(), key=lambda i: (i.row(), i.column()))
        if not indexes:
            return

        model = self.right.model()
        col_count = model.columnCount() if model else 0

        # Alle sichtbaren Spalten beider Views ermitteln
        visible_left = {c for c in range(self._freeze) if not self.left.isColumnHidden(c)}
        visible_right = {c for c in range(col_count) if not self.right.isColumnHidden(c)}
        visible_cols = sorted(visible_left | visible_right)

        # Selektierte Zellen gruppieren (row -> set of col)
        sel_map: dict = {}
        for idx in indexes:
            sel_map.setdefault(idx.row(), set()).add(idx.column())

        rows_sorted = sorted(sel_map.keys())

        # Prüfen ob alle Zeilen vollständig selektiert sind (= ganze Zeilen)
        all_rows_complete = all(
            set(visible_cols) == (sel_map[row] & set(visible_cols))
            for row in rows_sorted
        )

        lines = []

        # Header voranstellen wenn ganze Zeilen kopiert werden
        if all_rows_complete:
            header_cells = []
            for col in visible_cols:
                title = model.headerData(col, Qt.Horizontal, Qt.DisplayRole)
                header_cells.append("" if title is None else str(title))
            lines.append("\t".join(header_cells))

        for row in rows_sorted:
            sel_cols = sel_map[row]
            row_cols = [c for c in visible_cols if c in sel_cols]
            cells = []
            for col in row_cols:
                idx = model.index(row, col)
                val = model.data(idx, Qt.DisplayRole)
                cells.append("" if val is None else str(val))
            lines.append("\t".join(cells))

        text = "\n".join(lines)
        QApplication.clipboard().setText(text)

    def keyPressEvent(self, event):
        """Ctrl+C kopiert Selektion als TSV in die Zwischenablage."""
        if event.matches(QKeySequence.Copy):
            self.copy_selection_to_clipboard()
            event.accept()
        else:
            super().keyPressEvent(event)

    def __getattr__(self, name):
        """Delegiert unbekannte Attribute/Methoden an die rechte Ansicht."""
        return getattr(self.right, name)

    def _apply_column_visibility(self):
        """Blendet Spalten ein/aus: links erste N, rechts alle anderen."""
        if self._model is None:
            return
        cols = self._model.columnCount()
        for c in range(cols):
            self.left.setColumnHidden(c, c >= self._freeze)
            self.right.setColumnHidden(c, c < self._freeze)

    def _maybe_update_left_width(self, section: int, _old: int, _new: int):
        """Callback für sectionResized: aktualisiert die linke Breite wenn nötig."""
        if section < self._freeze:
            self._update_left_width()

    def _update_left_width(self):
        """Berechnet und setzt die fixe Breite der linken Ansicht."""
        try:
            total = sum(self.left.columnWidth(c) for c in range(self._freeze))
            vhw = self.left.verticalHeader().width()
            fw = self.left.frameWidth() * 2
            self.left.setFixedWidth(total + vhw + fw)
        except Exception:
            pass

    def _sync_vheader_visibility(self):
        """Synchronisiert Row-Header-Sichtbarkeit zwischen linker und rechter Ansicht."""
        try:
            vis = self.right.verticalHeader().isVisible()
            if self.left.verticalHeader().isVisible() != vis:
                self.left.verticalHeader().setVisible(vis)
        except Exception:
            pass

    def eventFilter(self, obj, ev):
        """Lauscht auf Show/Hide-Events des Row-Headers für Sync, und fängt Ctrl+C auf beiden Views ab."""
        from PySide6.QtCore import QEvent as _QEvent
        from PySide6.QtGui import QKeyEvent as _QKeyEvent
        try:
            if ev.type() == _QEvent.KeyPress and isinstance(ev, _QKeyEvent):
                if ev.matches(QKeySequence.Copy):
                    self.copy_selection_to_clipboard()
                    return True
        except Exception:
            pass
        try:
            if obj is self.right.verticalHeader() and ev.type() in (QEvent.Hide, QEvent.Show):
                self._sync_vheader_visibility()
        except Exception:
            pass
        try:
            if obj is self.left.viewport() and ev.type() == _QEvent.Wheel:
                QApplication.sendEvent(self.right.viewport(), ev)
                return True
        except Exception:
            pass
        return super().eventFilter(obj, ev)

    @Slot(int, int, int)
    def _sync_row_height_right_to_left(self, row: int, _old: int, new: int):
        """Überträgt Zeilenhöhenänderung von rechts nach links."""
        try:
            if self.left.verticalHeader().sectionSize(row) != new:
                self.left.verticalHeader().resizeSection(row, new)
        except Exception:
            pass

    @Slot(int, int, int)
    def _sync_row_height_left_to_right(self, row: int, _old: int, new: int):
        """Überträgt Zeilenhöhenänderung von links nach rechts."""
        try:
            if self.right.verticalHeader().sectionSize(row) != new:
                self.right.verticalHeader().resizeSection(row, new)
        except Exception:
            pass


# ----------------- table model -----------------
class JetsTableModel(QAbstractTableModel):
    _FG_BLACK = QColor("black")

    def __init__(self, rows: List[Dict], headers: List[str], id_column: str = "ID",
                 fk_maps: Optional[Dict[str, Dict]] = None,
                 bool_columns: Optional[Set[str]] = None):
        super().__init__()
        self._headers = headers[:]
        self._rows = rows[:]
        self._id_col = id_column
        self._dirty_cells: Set[tuple] = set()
        self._fk_maps = dict(fk_maps or {})
        self._bool_cols = set(bool_columns or set())

    def _is_bool_col(self, header: str) -> bool:
        """Gibt True zurück wenn die Spalte als Bool-Checkbox behandelt werden soll."""
        return _canon(header) in self._bool_cols

    def rowCount(self, parent=QModelIndex()) -> int:
        """Gibt die Anzahl Zeilen zurück."""
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        """Gibt die Anzahl Spalten zurück."""
        return len(self._headers)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        """Liefert Zelldaten: Bool-Spalten als Checkmark-Icon, FK-Spalten als lesbare Namen."""
        if not index.isValid():
            return None
        r, c = index.row(), index.column()
        header = self._headers[c]
        key = _canon(header)
        row = self._rows[r]
        val = row.get(header, None)

        if self._is_bool_col(header):
            if role == Qt.CheckStateRole:
                return Qt.Checked if _to_bool(val) else Qt.Unchecked
            if role == Qt.DisplayRole:
                return ""
            if role == Qt.EditRole:
                return _to_bool(val)

        # 📎-Spalte: hat der Jet mindestens ein File?
        if header == "__has_files__":
            has = row.get("has_files") in (1, "1", True)
            if role == Qt.DisplayRole:
                return ""
            if role == Qt.UserRole:
                return has
            if role == Qt.ToolTipRole:
                return "This jet has attached files." if has else ""
            return None

        if role == Qt.DisplayRole:
            fk = self._fk_maps.get(key)
            if fk:
                id_to_name = fk.get("id_to_name", {})
                name = id_to_name.get(val)
                if name is None:
                    i_like = _to_int_like(val)
                    if i_like is not None:
                        name = id_to_name.get(
                            i_like) or id_to_name.get(str(i_like))
                if name is None:
                    name = id_to_name.get(str(val))
                if name is not None:
                    return str(name)
            return "" if val is None else str(val)

        if role == Qt.EditRole:
            return "" if val is None else val

        if role == Qt.ForegroundRole:
            return self._FG_BLACK

        if role == Qt.BackgroundRole:
            return QColor(accent_tint()) if (r % 2 == 0) else QColor(accent_gridline())

        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

        return None

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        """Setzt einen Zellwert und markiert die Zeile als dirty."""
        if not index.isValid():
            return False
        header = self._headers[index.column()]
        key = _canon(header)
        if header.lower() == self._id_col.lower():
            return False

        if self._is_bool_col(header) and role in (Qt.EditRole, Qt.CheckStateRole):
            new_val = 1 if (value == Qt.Checked or _to_bool(value)) else 0
            self._rows[index.row()][header] = new_val
            self._dirty_cells.add((index.row(), index.column()))
            self.dataChanged.emit(
                index, index, [Qt.DisplayRole, Qt.EditRole, Qt.CheckStateRole])
            return True

        if role != Qt.EditRole:
            return False

        fk = self._fk_maps.get(key)
        if fk:
            if isinstance(value, str):
                value = value.strip()
            name_to_id = fk.get("name_to_id", {})
            if value in name_to_id:
                new_val = name_to_id[value]
            else:
                i_like = _to_int_like(value)
                new_val = i_like if i_like is not None else value
            self._rows[index.row()][header] = new_val
        else:
            if isinstance(value, str):
                value = value.strip()
            self._rows[index.row()][header] = value

        self._dirty_cells.add((index.row(), index.column()))
        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
        return True

    def flags(self, index: QModelIndex):
        """ID-Spalte read-only; has_files read-only; Bool-Spalten checkable; andere editierbar."""
        base = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if not index.isValid():
            return base
        header = self._headers[index.column()]
        if header.lower() == self._id_col.lower() or header == "__has_files__":
            return base
        if self._is_bool_col(header):
            return base | Qt.ItemIsUserCheckable
        return base | Qt.ItemIsEditable

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        """Gibt Spaltenheader zurück."""
        if orientation == Qt.Horizontal:
            h = self._headers[section] if section < len(self._headers) else ""
            if role == Qt.DisplayRole:
                return "📎" if h == "__has_files__" else h
            if role == Qt.ToolTipRole:
                return "Has attached files" if h == "__has_files__" else None
            return None
        if role == Qt.DisplayRole:
            return str(section + 1)
        return None

    def headers(self) -> List[str]:
        """Gibt alle Spaltennamen zurück."""
        return self._headers

    def fk_maps(self) -> Dict[str, Dict]:
        """Gibt das FK-Mapping-Dict zurück."""
        return self._fk_maps

    def dirty_rows(self) -> List[Dict]:
        """Gibt alle geänderten Zeilen zurück."""
        if not self._dirty_cells:
            return []
        dirty_row_idxs = sorted({r for r, _ in self._dirty_cells})
        return [self._rows[i] for i in dirty_row_idxs]

    def clear_dirty(self):
        """Leert das Dirty-Set nach erfolgreichem Speichern."""
        self.beginResetModel()
        self._dirty_cells.clear()
        self.endResetModel()


class HasFilesDelegate(QStyledItemDelegate):
    """Draws a clean green checkmark in the __has_files__ column when the jet has files.
    No text — purely painted, so it looks crisp at any row height."""

    _COLOR_CHECK = QColor("#2e7d32")   # dark green
    _COLOR_STEM  = QColor("#2e7d32")

    def paint(self, painter: QPainter, option, index):
        painter.save()

        # Derive background from row parity — same logic as JetsTableModel.data()
        from PySide6.QtWidgets import QStyle
        from ui.theme import accent_tint, accent_gridline
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            row = index.row()
            bg = QColor(accent_tint()) if (row % 2 == 0) else QColor(accent_gridline())
            painter.fillRect(option.rect, bg)

        painter.restore()

        has = index.data(Qt.UserRole)
        if not has:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        r = option.rect
        cx = r.left() + r.width() // 2
        cy = r.top() + r.height() // 2

        # Scale checkmark to row height — max 14 px tall
        size = min(13, r.height() - 6)
        half = size // 2

        # Checkmark path: short left stroke + long right stroke
        pen = QPen(self._COLOR_CHECK, max(1.8, size * 0.18))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        from PySide6.QtCore import QPointF
        # left foot of tick
        x0 = cx - half * 0.55
        y0 = cy + half * 0.05
        # bottom of tick
        xm = cx - half * 0.05
        ym = cy + half * 0.55
        # top-right of tick
        x1 = cx + half * 0.65
        y1 = cy - half * 0.65

        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.moveTo(QPointF(x0, y0))
        path.lineTo(QPointF(xm, ym))
        path.lineTo(QPointF(x1, y1))
        painter.drawPath(path)
        painter.restore()

    def sizeHint(self, option, index):
        sh = super().sizeHint(option, index)
        return sh


class FKComboDelegate(QStyledItemDelegate):
    def __init__(self, proxy: QSortFilterProxyModel, source_model: JetsTableModel,
                 fk_columns_by_index: Dict[int, str], parent=None):
        super().__init__(parent)
        self._proxy = proxy
        self._source = source_model
        self._fk_cols = dict(fk_columns_by_index)

    def _fk_for_view_col(self, view_col: int):
        """Gibt FK-Map für eine View-Spalte zurück (berücksichtigt Offset durch eingefrorene Spalten)."""
        header = self._fk_cols.get(view_col)
        if not header:
            return None
        return self._source.fk_maps().get(_canon(header))

    def createEditor(self, parent, option, index):
        """Erstellt eine Combobox mit FK-Optionen für die Zelle."""
        fk = self._fk_for_view_col(index.column())
        if fk:
            combo = QComboBox(parent)
            names = list(fk.get('name_to_id', {}).keys())
            combo.addItems(names)
            combo.setEditable(False)
            return combo
        return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        """Setzt den aktuellen Wert als Selektion in der Combobox."""
        fk = self._fk_for_view_col(index.column())
        if fk and isinstance(editor, QComboBox):
            current = index.data(Qt.DisplayRole)
            i = editor.findText(str(current))
            editor.setCurrentIndex(max(0, i))
            return
        return super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        """Schreibt die gewählte FK-ID zurück ins Source-Modell."""
        fk = self._fk_for_view_col(index.column())
        if fk and isinstance(editor, QComboBox):
            src_index = self._proxy.mapToSource(index)
            sel_name = editor.currentText()
            self._source.setData(src_index, sel_name, Qt.EditRole)
            return
        return super().setModelData(editor, model, index)


# ----------------- screen -----------------
class ManageJetsScreen(QWidget):
    def __init__(self, on_back_home: Optional[Callable] = None,
                 loader: Optional[Callable[[], List[Dict]]] = None,
                 saver: Optional[Callable[[List[Dict]], int]] = None,
                 id_column: str = "ID",
                 fk_maps: Optional[Dict[str, Dict]] = None,
                 creator: Optional[Callable[[], int]] = None,
                 deleter: Optional[Callable[[List[int]], int]] = None,
                 on_open_new_jet: Optional[Callable[[], None]] = None,
                 on_copy_jet: Optional[Callable[[Dict], None]] = None,
                on_edit_jet: Optional[Callable[[Dict], None]] = None):
        super().__init__()
        self.on_back_home = on_back_home
        self._loader = loader
        self._saver = saver
        self._id_col = id_column
        self._fk_maps_input = fk_maps or {}
        # JetGroupID key alias: manche Caller liefern unterschiedliche Keys (jetgroup, jetgroupid, JetGroupID)
        try:
            if isinstance(self._fk_maps_input, dict):
                if "jetgroup" not in self._fk_maps_input:
                    for k in ("JetGroupID", "jetgroupid", "JetGroupId", "jetGroupID"):
                        if k in self._fk_maps_input:
                            self._fk_maps_input["jetgroup"] = self._fk_maps_input[k]
                            break
        except Exception:
            pass
        self._creator = creator
        self._deleter = deleter
        self._on_open_new_jet = on_open_new_jet
        self._on_copy_jet = on_copy_jet
        self._on_edit_jet = on_edit_jet

        self.table: Optional[FrozenNColumnsTable] = None
        self.model: Optional[JetsTableModel] = None
        self.proxy: Optional[MultiColumnFilterProxy] = None
        self._jet_filter_col: int = -1
        self.status_label: Optional[QLabel] = None
        self.search_edit: Optional[QLineEdit] = None
        self._fk_delegate: Optional[FKComboDelegate] = None

        self._build_ui()
        self.reload_data()

    def _build_ui(self):
        """Erstellt Header, Filter-Toolbar, Tabelle und Footer."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = HeaderBar(title="Manage Jets", show_home=True)
        header.connect_home(self._go_home)

        toolbar = QFrame()
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(24, 12, 24, 0)
        tl.setSpacing(8)

        self.search_edit = QLineEdit(placeholderText="Search Jet…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._on_search_changed)

        self.btn_reload = QPushButton("Reload", objectName="GreyBtn")
        self.btn_reload.clicked.connect(self.reload_data)

        self.btn_new = QPushButton("New Jet", objectName="GreenBtn")
        self.btn_new.clicked.connect(self._on_new)

        self.btn_copy = QPushButton("Copy", objectName="GreyBtn")
        self.btn_copy.clicked.connect(self._on_copy)

        self.btn_edit_form = QPushButton("Edit in Form", objectName="GreyBtn")
        self.btn_edit_form.clicked.connect(self._on_edit_form)

        self.btn_delete = QPushButton("Delete", objectName="GreyBtn")
        self.btn_delete.clicked.connect(self._on_delete)

        self.btn_save = QPushButton("Save Changes", objectName="PurpleBtn")
        self.btn_save.clicked.connect(self.save_changes)

        self.status_label = QLabel("")

        tl.addWidget(self.search_edit, 1)
        tl.addWidget(self.btn_reload, 0)
        tl.addWidget(self.btn_new, 0)
        tl.addWidget(self.btn_copy, 0)
        tl.addWidget(self.btn_edit_form, 0)
        tl.addWidget(self.btn_delete, 0)
        tl.addWidget(self.btn_save, 0)
        tl.addWidget(self.status_label, 0, Qt.AlignVCenter)

        self.table = FrozenNColumnsTable(
            freeze_count=2, objectName="JetsTable")
        self.table.setAlternatingRowColors(False)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setSelectionBehavior(QTableView.SelectItems)
        self.table.setSelectionMode(QTableView.ExtendedSelection)
        self.table.setStyleSheet("""
            QTableView#JetsTable { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView#JetsTable::item { color: black; }
            QTableView#JetsTable::item:selected { background: #b7d6ff; color: black; }
        """
            .replace("#B5D7B5", accent_gridline())
            .replace("#E9F6E9", accent_tint()))

        self.table.right.doubleClicked.connect(self._on_row_double_clicked)
        self.table.left.doubleClicked.connect(self._on_row_double_clicked)

        root.addWidget(header)
        root.addWidget(toolbar, 0)
        root.addWidget(self.table, 1)
        root.addWidget(FooterBar())

    def reload_data(self, select_id: Optional[int] = None):
        """Lädt alle Jet-Daten neu aus der DB (inkl. FK-Maps) und baut Modell neu auf.

        Args:
            select_id: Optional – ID des Jets der nach dem Laden selektiert werden soll.
        """
        if not callable(self._loader):
            self._set_status("No loader configured.", error=True)
            return
        try:
            rows = self._loader()
        except Exception as e:
            self._set_status(f"Load failed: {e}", error=True)
            return

        headers = list(rows[0].keys()) if rows else [self._id_col]

        # Insert __has_files__ column directly after the "Jet" column
        try:
            jet_idx = next(i for i, h in enumerate(headers) if _canon(h) == "jet")
            if "__has_files__" not in headers:
                headers.insert(jet_idx + 1, "__has_files__")
        except StopIteration:
            if "__has_files__" not in headers:
                headers.insert(1, "__has_files__")

        bool_cols = {_canon("Gebogener Kanal")}
        self.model = JetsTableModel(rows=rows, headers=headers, id_column=self._id_col,
                                    fk_maps=self._fk_maps_input, bool_columns=bool_cols)

        if self.proxy is None:
            self.proxy = MultiColumnFilterProxy(self)
            self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
            self.proxy.setDynamicSortFilter(True)
            self.table.set_filter_proxy(self.proxy)

        self.proxy.setSourceModel(self.model)
        self._configure_filter_column()
        self.table.setModel(self.proxy)

        # __has_files__ column: schmal, painted delegate, nicht editierbar
        try:
            hf_idx = self.model.headers().index("__has_files__")
            self.table.right.setColumnWidth(hf_idx, 30)
            self.table.right.horizontalHeader().setSectionResizeMode(
                hf_idx, QHeaderView.Fixed)
            self._has_files_delegate = HasFilesDelegate(parent=self.table.right)
            self.table.right.setItemDelegateForColumn(hf_idx, self._has_files_delegate)
        except Exception:
            pass

        fk_cols_by_idx = {i: h for i, h in enumerate(
            headers) if _canon(h) in self._fk_maps_input}
        self._fk_delegate = FKComboDelegate(
            self.proxy, self.model, fk_cols_by_idx, parent=self.table.right)
        for col_idx in range(len(headers)):
            if col_idx in fk_cols_by_idx:
                self.table.setItemDelegateForColumn(col_idx, self._fk_delegate)

        self._set_status("")
        self.table.resizeColumnsToContents()
        self._on_search_changed(self.search_edit.text()
                                if self.search_edit else "")

        if select_id is not None:
            try:
                id_col = None
                jet_col = None
                for i, h in enumerate(headers):
                    if h.lower() == self._id_col.lower():
                        id_col = i
                    if _canon(h) == "jet":
                        jet_col = i
                if id_col is not None:
                    src_model = self.model
                    row_index = None
                    for r, row in enumerate(src_model._rows):
                        if str(row.get(self._id_col)) == str(select_id):
                            row_index = r
                            break
                    if row_index is not None:
                        src_row_idx = src_model.index(row_index, 0)
                        view_row_idx = self.proxy.mapFromSource(src_row_idx)
                        self.table.selectRow(view_row_idx.row())
                        self.table.scrollToBottom()
                        self.table.scrollTo(
                            view_row_idx, QAbstractItemView.PositionAtBottom)
                        if jet_col is not None:
                            src_cell_idx = src_model.index(row_index, jet_col)
                            view_cell_idx = self.proxy.mapFromSource(
                                src_cell_idx)
                            self.table.setCurrentIndex(view_cell_idx)
                            self.table.scrollTo(
                                view_cell_idx, QAbstractItemView.PositionAtBottom)
                            self.table.setFocus()
                            self.table.edit(view_cell_idx)
            except Exception:
                pass

    def _configure_filter_column(self):
        """Ermittelt die Jet-Spalte für den Suchproxy (Suchfeld oben filtert diese Spalte)."""
        if not self.model:
            return
        headers = self.model.headers()
        self._jet_filter_col = -1
        for i, h in enumerate(headers):
            if _canon(h) == "jet":
                self._jet_filter_col = i
                break

    def _on_search_changed(self, text: str):
        """Aktualisiert den Proxy-Filter bei Texteingabe im Suchfeld (filtert Jet-Spalte)."""
        if not self.proxy:
            return
        col = getattr(self, "_jet_filter_col", -1)
        if col < 0:
            return
        self.proxy.set_column_filter(col, text)
        # Refresh header markers
        try:
            self.table._left_header.viewport().update()
            self.table._right_header.viewport().update()
        except Exception:
            pass

    def save_changes(self):
        """Schreibt alle dirty Zeilen via UPDATE in die DB."""
        if not self.model:
            return
        dirty_rows = self.model.dirty_rows()
        if not dirty_rows:
            self._set_status("No changes to save.")
            return
        if not callable(self._saver):
            self._set_status("No saver configured.", error=True)
            return

        try:
            # Strip synthetic/computed columns that don't exist in the DB
            _SYNTHETIC = {"__has_files__", "has_files"}
            clean_rows = [{k: v for k, v in row.items() if k not in _SYNTHETIC}
                          for row in dirty_rows]
            affected = self._saver(clean_rows)
            self.model.clear_dirty()
            self._set_status(f"Saved {affected} update(s).")
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))
            self._set_status(f"Save failed: {e}", error=True)

    # -------- actions --------
    def _on_new(self):
        """Legt einen neuen leeren Jet in der DB an."""
        if callable(self._on_open_new_jet):
            self._on_open_new_jet()
            self._set_status("")
        else:
            self._set_status("New Jet screen is not available.", error=True)

    def _on_copy(self):
        """Dupliziert den selektierten Jet (alle Felder werden kopiert, neue ID wird vergeben)."""
        """
        Öffnet den NewJet-Screen mit den Werten der selektierten Zeile,
        wobei das Feld 'Jet' leer ist.
        """
        if not callable(self._on_copy_jet):
            self._set_status("Copy not available.", error=True)
            return

        sel = self.table.selectionModel()
        if not sel or not sel.hasSelection():
            self._set_status("No row selected to copy.")
            return

        try:
            view_row = sorted({i.row() for i in sel.selectedIndexes()})[0]
            src_index = self.proxy.mapToSource(self.proxy.index(view_row, 0))
            src_row = src_index.row()
            row_dict = dict(self.model._rows[src_row])
        except Exception:
            self._set_status("Could not read selected row.", error=True)
            return

        self._on_copy_jet(row_dict)
        self._set_status("")

    def _on_row_double_clicked(self, _index):
        """Doppelklick auf Zeile → Formular-Dialog."""
        self._on_edit_form()

    def _on_edit_form(self):
        """Öffnet den selektierten Jet im bestehenden NewJetScreen-Formular als Dialog."""
        sel = self.table.selectionModel()
        if not sel or not sel.hasSelection():
            self._set_status("No row selected.")
            return
        try:
            view_row = sorted({i.row() for i in sel.selectedIndexes()})[0]
            src_index = self.proxy.mapToSource(self.proxy.index(view_row, 0))
            row_dict = dict(self.model._rows[src_index.row()])
        except Exception:
            self._set_status("Could not read selected row.", error=True)
            return

        if callable(self._on_edit_jet):
            self._on_edit_jet(row_dict)
        else:
            self._set_status("Edit in Form not available.", error=True)

    def _on_delete(self):
        """Löscht die selektierten Jets nach Bestätigung aus der DB."""
        if not callable(self._deleter):
            self._set_status("Delete not available.", error=True)
            return
        sel = self.table.selectionModel()
        if not sel or not sel.hasSelection():
            self._set_status("No rows selected.")
            return
        rows = sorted({self.proxy.mapToSource(i).row()
                      for i in sel.selectedIndexes()})
        ids = []
        for r in rows:
            try:
                rid = self.model._rows[r].get(self._id_col)
                if rid is not None:
                    ids.append(rid)
            except Exception:
                continue
        if not ids:
            self._set_status("No IDs to delete.")
            return
        confirm = QMessageBox.question(
            self, "Delete", f"Delete {len(ids)} selected jet(s)?")
        if confirm != QMessageBox.Yes:
            return
        try:
            count = self._deleter(ids)
            self._set_status(f"Deleted {count} row(s).")
            self.reload_data()
        except Exception as e:
            QMessageBox.critical(self, "Delete failed", str(e))
            self._set_status(f"Delete failed: {e}", error=True)

    def _go_home(self):
        """Navigiert zurück zum Home-Screen – fragt bei ungespeicherten Änderungen."""
        if self.model and self.model.dirty_rows():
            from PySide6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "There are unsaved changes. Save before leaving?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if reply == QMessageBox.Save:
                self.save_changes()
                if self.model.dirty_rows():
                    return   # Save failed – bleiben
            elif reply == QMessageBox.Cancel:
                return
        if callable(self.on_back_home):
            self.on_back_home()

    def _set_status(self, text: str, *, error: bool = False):
        """Setzt den Statustext (rot bei error=True)."""
        if not self.status_label:
            return
        self.status_label.setStyleSheet("color: #c62828;" if error else "")
        self.status_label.setText(text)