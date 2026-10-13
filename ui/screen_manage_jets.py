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
from typing import List, Dict, Callable, Optional, Set, Tuple
from decimal import Decimal
import re
import html

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, QRegularExpression, Slot, QEvent, QPoint, QRectF
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QSizePolicy, QTableView, QMessageBox, QLineEdit, QComboBox, QStyledItemDelegate,
    QAbstractItemView, QHeaderView, QMenu, QWidgetAction, QDialog, QStyle,
    QStyleOptionViewItem, QListWidget, QListWidgetItem
)
from PySide6.QtGui import (
    QPixmap, QColor, QKeySequence, QFont, QAction, QPainter, QPen, QBrush,
    QTextDocument, QAbstractTextDocumentLayout, QTextOption
)
from PySide6.QtWidgets import QApplication

from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from ui.pathutil import resource_path
from ui.text_normalize import canon_with_id_strip as _canon
import app_meta

_AUDIT_COLS = ("createdby", "creationdate")
# Rein berechnet (kein echtes tblDTYJets-Feld, siehe main.py._load_jets_data) -
# anders als _AUDIT_COLS für ALLE sichtbar, nur nicht editierbar.
_COMPUTED_COLS = ("usedintrial",)


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
        self._search_cols: List[int] = []
        self._search_text: str = ""
        self._search_terms: List[str] = []

    # ---- text filter ----
    def set_column_filter(self, col: int, text: str):
        """Set or clear a text substring filter for a column."""
        text = text.strip()
        if text:
            self._filters[col] = text.lower()
        else:
            self._filters.pop(col, None)
        self.invalidateFilter()

    # ---- multi-column OR search (used by the toolbar search field) ----
    def set_search_filter(self, cols: List[int], text: str):
        """Set/clear a case-insensitive substring search across several columns (OR).

        `text` may hold several search terms separated by ';' (e.g. "APh212;X47.66")
        - a row matches if ANY term is found as a substring in ANY of `cols`.
        Independent from set_column_filter()'s per-column popup filters, which
        stay AND-combined.
        """
        self._search_cols = list(cols)
        self._search_text = text.strip().lower()
        terms: List[str] = []
        seen = set()
        for part in self._search_text.split(";"):
            term = part.strip()
            if term and term not in seen:
                seen.add(term)
                terms.append(term)
        self._search_terms = terms
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

        if self._search_terms and self._search_cols:
            for col in self._search_cols:
                idx = src.index(source_row, col, source_parent)
                val = src.data(idx, Qt.DisplayRole)
                if val is None:
                    continue
                val_lower = str(val).lower()
                if any(term in val_lower for term in self._search_terms):
                    break
            else:
                return False
        return True


# ----------------- Expandable filter proxy -----------------
class ExpandableFilterProxy(MultiColumnFilterProxy):
    """MultiColumnFilterProxy + zwei Sonderregeln für inline aufklappbare
    'series'/'trial'-Detailzeilen (echte, eingefügte Model-Zeilen - siehe
    ManageYarnScreen/ManageJetsScreen: _expand_*_row/_collapse_*_row, sowie
    das Model-Gegenstück row_kind()/anchor_row()/local_order()/
    insert_detail_rows()/remove_rows_span() in YarnTableModel bzw.
    JetsTableModel). Vollständig generisch (duck-typed über hasattr) - lebt
    hier statt in screen_manage_yarn.py, weil es von beiden Screens genutzt
    wird, genau wie MultiColumnFilterProxy/FilterableHeaderView.

    1. filterAcceptsRow(): eine Detailzeile wird IMMER angezeigt, unabhängig
       von aktiven Spaltenfiltern - für die echten Datenspalten hat sie
       ohnehin keinen sinnvollen Wert, ein aktiver Filter auf irgendeiner
       anderen Spalte darf eine gerade aufgeklappte Zeile nicht verstecken.
    2. lessThan(): ohne Sonderbehandlung würde eine Detailzeile beim
       (dynamischen) Sortieren zufällig einsortiert statt direkt unter ihrer
       Eltern-Zeile zu bleiben, weil sie für die sortierte Spalte keinen
       eigenen Wert hat. Vergleich stattdessen über die Eltern-Zeile in
       genau dieser Spalte, und innerhalb desselben Blocks über eine feste
       Erfassungsreihenfolge (Model.local_order()).

    `before_change` wird vor jeder Sortier-/Filteränderung aufgerufen und
    klappt alle offenen Zeilen zu - Detailzeilen hängen an einer festen
    Position relativ zu ihrer Eltern-Zeile und würden durch eine
    Neusortierung/-filterung sonst zerstreut."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.before_change: Optional[Callable[[], None]] = None

    def _pre(self):
        if self.before_change:
            self.before_change()

    def set_column_filter(self, col, text):
        self._pre()
        super().set_column_filter(col, text)

    def set_range_filter(self, col, lo, hi):
        self._pre()
        super().set_range_filter(col, lo, hi)

    def set_search_filter(self, cols, text):
        self._pre()
        super().set_search_filter(cols, text)

    def clear_all_filters(self):
        self._pre()
        super().clear_all_filters()

    def sort(self, column, order=Qt.AscendingOrder):
        self._pre()
        super().sort(column, order)

    _DETAIL_KINDS = ('series', 'trial')  # gemeinsames Vokabular für alle Detailzeilen-Modelle

    def filterAcceptsRow(self, source_row, source_parent):
        src = self.sourceModel()
        if src is not None and hasattr(src, 'row_kind') and src.row_kind(source_row) in self._DETAIL_KINDS:
            return True
        return super().filterAcceptsRow(source_row, source_parent)

    def lessThan(self, left, right):
        src = self.sourceModel()
        if src is None or not hasattr(src, 'row_kind'):
            return super().lessThan(left, right)
        l_kind = src.row_kind(left.row())
        r_kind = src.row_kind(right.row())
        if l_kind not in self._DETAIL_KINDS and r_kind not in self._DETAIL_KINDS:
            return super().lessThan(left, right)
        l_anchor = src.anchor_row(left.row())
        r_anchor = src.anchor_row(right.row())
        if l_anchor != r_anchor:
            return super().lessThan(src.index(l_anchor, left.column()), src.index(r_anchor, right.column()))
        # Gleicher Block (z. B. Serie + ihre Versuchszeilen): die relative
        # Innen-Reihenfolge (Eltern vor Kindern) muss FIX bleiben, unabhängig
        # davon, ob der Nutzer die Tabelle gerade auf- oder absteigend sortiert
        # hat. QSortFilterProxyModel dreht das Ergebnis von lessThan() aber
        # automatisch um, sobald sortOrder()==DescendingOrder ist (das ist
        # korrekt für "echte" Spaltenvergleiche, siehe der super().lessThan()-
        # Zweig oben) - für unseren rein künstlichen local_order()-Vergleich
        # (kein echter Spaltenwert) müssen wir das deshalb selbst vorab
        # gegenkompensieren, sonst landen bei absteigender Sortierung die
        # Versuchszeilen über statt unter ihrer Serien-Zeile (genau der Bug,
        # den der Screenshot zeigte - bei aufsteigender Sortierung/unsortiert
        # fällt das nie auf, weil dort keine Umkehr stattfindet).
        lo_l = src.local_order(left.row())
        lo_r = src.local_order(right.row())
        if self.sortOrder() == Qt.DescendingOrder:
            return lo_l > lo_r
        return lo_l < lo_r


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

        # Left (frozen) columns stay fixed as an anchor; the right pane's columns
        # can be dragged into any order the user wants (order is preserved
        # across reload_data() calls, see setModel()).
        self._left_header.setSectionsMovable(False)
        self._right_header.setSectionsMovable(True)

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
        """Setzt dasselbe Model auf beide Ansichten und verbirgt/zeigt die richtigen Spalten.

        Eine vom Nutzer per Drag&Drop gesetzte Spaltenreihenfolge (rechter Header)
        übersteht dadurch ein reload_data() (neues Model-Objekt, gleiche Spalten).
        """
        prev_right_state = self._right_header.saveState() if self._model is not None else None

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

        if prev_right_state is not None:
            self._right_header.restoreState(prev_right_state)

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
                 bool_columns: Optional[Set[str]] = None,
                 read_only: bool = False):
        super().__init__()
        self._headers = headers[:]
        self._rows = rows[:]
        self._id_col = id_column
        self._dirty_cells: Set[tuple] = set()
        self._fk_maps = dict(fk_maps or {})
        self._bool_cols = set(bool_columns or set())
        self._read_only = read_only

        # Welche UsedInTrial-Zeilen (per Jet-ID) gerade inline aufgeklappt sind
        # - steuert nur das Dreieck-Symbol auf der Jet-Zeile selbst (siehe
        # set_expanded()). Das Ein-/Ausblenden der TrialSeries-/Versuchs-
        # Detailzeilen (echte, eingefügte Model-Zeilen) macht ManageJetsScreen
        # - identisches Muster wie YarnTableModel in screen_manage_yarn.py.
        self._expanded_ids: set = set()

    def _is_bool_col(self, header: str) -> bool:
        """Gibt True zurück wenn die Spalte als Bool-Checkbox behandelt werden soll."""
        return _canon(header) in self._bool_cols

    def set_read_only(self, read_only: bool):
        """Schaltet die Editierbarkeit aller Zellen um (Ansicht muss danach neu gezeichnet werden)."""
        self._read_only = read_only

    def rowCount(self, parent=QModelIndex()) -> int:
        """Gibt die Anzahl Zeilen zurück."""
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        """Gibt die Anzahl Spalten zurück."""
        return len(self._headers)

    # ---- inline aufklappbare Detailzeilen (TrialSeries/Versuchsnummer) ------
    # Identisches Muster wie YarnTableModel in screen_manage_yarn.py - siehe
    # dort für die ausführliche Begründung. row_kind()/anchor_row()/
    # local_order() werden von ExpandableFilterProxy (screen_manage_jets.py)
    # geduckt-getypt aufgerufen.
    def row_kind(self, row: int) -> str:
        """'jet' (echte Jet-Zeile, Default) | 'series' | 'trial'."""
        return self._rows[row].get('_row_kind', 'jet')

    def anchor_row(self, row: int) -> int:
        rd = self._rows[row]
        if rd.get('_row_kind', 'jet') == 'jet':
            return row
        anchor_id = rd.get('_anchor_jet_id')
        for i, r in enumerate(self._rows):
            if r.get('_row_kind', 'jet') == 'jet' and r.get(self._id_col) == anchor_id:
                return i
        return row  # sollte nicht vorkommen (Jet-Zeile zwischenzeitlich entfernt)

    def local_order(self, row: int) -> float:
        return self._rows[row].get('_order', 0.0)

    def insert_detail_rows(self, after_row: int, new_rows: List[Dict]):
        if not new_rows:
            return
        n = len(new_rows)
        insert_at = after_row + 1
        self.beginInsertRows(QModelIndex(), insert_at, insert_at + n - 1)
        self._rows[insert_at:insert_at] = new_rows
        self._dirty_cells = {(r + n if r >= insert_at else r, c) for (r, c) in self._dirty_cells}
        self.endInsertRows()

    def remove_rows_span(self, start_row: int, count: int):
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
        """data() für eine Serie-/Versuchs-Zeile: EINE gespannte Zelle in der
        rechten (nicht eingefrorenen) Ansicht, ab '_label_col' - trägt Dreieck
        UND Beschreibungstext zusammen (kein Text mehr in der linken/
        eingefrorenen Ansicht - dort bleibt die Spannzelle bewusst leer).

        Ursprünglich hier auf zwei Zellen (Dreieck links, Text rechts)
        aufgeteilt, um möglichst weit links zu beginnen - das erzeugte aber
        zwangsläufig eine breite, hässliche weisse Lücke zwischen den beiden
        getrennten Tabellen-Widgets (eingefroren/scrollbar können nie nahtlos
        aneinander anschliessen, siehe Screenshot-Feedback). Eine einzige
        durchgehende Zelle ohne Lücke wiegt schwerer als "ganz am linken Rand
        der gesamten Tabelle" - "links" heisst hier jetzt "ganz am Anfang des
        scrollbaren Bereichs", nicht "vor den eingefrorenen Spalten"."""
        rd = self._rows[row]
        if role == Qt.DisplayRole and col == rd.get('_label_col', 0):
            return rd.get('_label', '')
        if role == Qt.BackgroundRole:
            # Versuchs-Zeilen (tiefer verschachtelt, rein informativ) bekommen
            # einen helleren Ton als ihre TrialSeries-Zeile, damit die zwei
            # Ebenen optisch auseinanderfallen statt in einem Block zu wirken -
            # analog zu ManageYarnScreen (screen_manage_yarn.py).
            if rd.get('_row_kind') == 'trial':
                return QColor('#F1F8F1')
            return QColor('#E3EEE3')
        if role == Qt.ForegroundRole:
            return self._FG_BLACK
        if role == Qt.TextAlignmentRole:
            return Qt.AlignVCenter | Qt.AlignLeft
        if role == Qt.ToolTipRole and rd.get('_row_kind') == 'series':
            return 'Click ▸ to show/hide trial numbers · click the trial series name to open it'
        return None

    def set_expanded(self, jet_id, expanded: bool):
        """Nur fürs Dreieck-Symbol auf der Jet-Zeile - das Einfügen/Entfernen
        der TrialSeries-Zeilen selbst macht ManageJetsScreen."""
        if expanded:
            self._expanded_ids.add(jet_id)
        else:
            self._expanded_ids.discard(jet_id)
        try:
            ui_idx = self._headers.index("UsedInTrial")
        except ValueError:
            return
        try:
            row = next(i for i, rw in enumerate(self._rows)
                       if rw.get('_row_kind', 'jet') == 'jet' and rw.get(self._id_col) == jet_id)
        except StopIteration:
            return
        idx = self.index(row, ui_idx)
        self.dataChanged.emit(idx, idx, [Qt.DisplayRole, Qt.ToolTipRole])

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        """Liefert Zelldaten: Bool-Spalten als Checkmark-Icon, FK-Spalten als lesbare Namen."""
        if not index.isValid():
            return None
        r, c = index.row(), index.column()
        if self._rows[r].get('_row_kind', 'jet') != 'jet':
            return self._detail_row_data(r, c, role)
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

        if key == "usedintrial" and role == Qt.ToolTipRole and val == 1:
            return ('Click to hide the trial series using this jet' if row.get(self._id_col) in self._expanded_ids
                    else 'Click to show the trial series using this jet')

        if role == Qt.DisplayRole:
            if key == "usedintrial":
                if val != 1:
                    return "No"
                return 'Yes ▾' if row.get(self._id_col) in self._expanded_ids else 'Yes ▸'
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
        if not index.isValid() or self._read_only:
            return False
        if self._rows[index.row()].get('_row_kind', 'jet') != 'jet':
            return False  # Detailzeile - nie editierbar (flags() verhindert das ohnehin schon)
        header = self._headers[index.column()]
        key = _canon(header)
        if header.lower() == self._id_col.lower() or key in _AUDIT_COLS or key in _COMPUTED_COLS:
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
        """ID-Spalte read-only; has_files read-only; Bool-Spalten checkable; andere editierbar
        (ausser im Read-only-Modus: dann ist gar nichts editierbar)."""
        base = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if not index.isValid():
            return base
        if self._rows[index.row()].get('_row_kind', 'jet') != 'jet':
            # Detailzeile: nicht selektierbar/editierbar - Klick-Handling läuft
            # über ManageJetsScreen._handle_table_click, nicht über Qt-Editing.
            return Qt.ItemIsEnabled
        header = self._headers[index.column()]
        if (header.lower() == self._id_col.lower() or header == "__has_files__"
                or _canon(header) in _AUDIT_COLS or _canon(header) in _COMPUTED_COLS):
            return base
        if self._read_only:
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
        # A real __has_files__ cell always has empty DisplayRole text (see
        # JetsTableModel.data()) - non-empty text here means this column
        # happens to be sitting at the label-span anchor of an inline
        # TrialSeries/Versuchsnummer detail row (ManageJetsScreen.
        # _label_anchor_col(), anchored at UsedInTrial's current column -
        # can coincide with any column depending on Columns…-dialog reorder
        # state). Our custom paint below never draws text at all, which
        # would make that label invisible - fall back to normal text
        # rendering for that case.
        if index.data(Qt.DisplayRole):
            super().paint(painter, option, index)
            return

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


# ----------------- search-hit highlight delegate -----------------
class SearchHighlightDelegate(QStyledItemDelegate):
    """Draws DisplayRole text with the active toolbar-search terms highlighted.

    The search box may hold several ';'-separated terms (e.g. "APh212;X47.66")
    - each term gets its own highlight color (cycling through `_HIGHLIGHT_COLORS`,
    assigned by the term's position in the search box) so it's visible at a glance
    which part of a hit matched which term.

    Only touches columns the search actually scans (`search_cols_getter`); every
    other cell falls straight through to the default QStyledItemDelegate paint.
    """

    _HIGHLIGHT_COLORS = ["#ffe58a", "#8ad9ff", "#b3ffb3", "#ffb3d9", "#d9b3ff", "#ffcc99"]

    def __init__(self, proxy: MultiColumnFilterProxy, search_cols_getter: Callable[[], List[int]], parent=None):
        super().__init__(parent)
        self._proxy = proxy
        self._search_cols_getter = search_cols_getter

    def _search_terms(self) -> List[str]:
        return getattr(self._proxy, "_search_terms", []) if self._proxy else []

    def _highlighted_html(self, text: str, terms: List[str]) -> str:
        """Escapes `text` and wraps every case-insensitive occurrence of any `terms`
        entry in a <span>, colored by that term's index in `terms` (longer terms win
        on overlap, e.g. one term being a substring of another)."""
        order = sorted(range(len(terms)), key=lambda i: -len(terms[i]))
        pattern = "|".join(f"(?P<t{i}>{re.escape(terms[i])})" for i in order)
        regex = re.compile(pattern, re.IGNORECASE)

        out = []
        pos = 0
        for m in regex.finditer(text):
            if m.start() > pos:
                out.append(html.escape(text[pos:m.start()]))
            term_idx = next(i for i in order if m.group(f"t{i}") is not None)
            color = self._HIGHLIGHT_COLORS[term_idx % len(self._HIGHLIGHT_COLORS)]
            out.append(f'<span style="background-color:{color};">{html.escape(m.group(0))}</span>')
            pos = m.end()
        out.append(html.escape(text[pos:]))
        return "".join(out)

    def paint(self, painter: QPainter, option, index):
        terms = self._search_terms()
        cols = self._search_cols_getter() if callable(self._search_cols_getter) else []
        text = index.data(Qt.DisplayRole)
        text = "" if text is None else str(text)
        text_lower = text.lower()

        if not terms or index.column() not in cols or not any(t in text_lower for t in terms):
            super().paint(painter, option, index)
            return

        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        style = opt.widget.style() if opt.widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem, opt, painter, opt.widget)

        doc = QTextDocument()
        doc.setDefaultFont(opt.font)
        text_option = QTextOption()
        text_option.setAlignment(Qt.AlignHCenter)
        doc.setDefaultTextOption(text_option)
        doc.setHtml(self._highlighted_html(text, terms))
        doc.setTextWidth(opt.rect.width())

        painter.save()
        painter.translate(opt.rect.topLeft())
        painter.setClipRect(QRectF(0, 0, opt.rect.width(), opt.rect.height()))
        y_offset = max(0.0, (opt.rect.height() - doc.size().height()) / 2)
        painter.translate(0, y_offset)
        ctx = QAbstractTextDocumentLayout.PaintContext()
        ctx.palette = opt.palette
        doc.documentLayout().draw(painter, ctx)
        painter.restore()


# ----------------- column order dialog -----------------
class ColumnOrderDialog(QDialog):
    """Non-modal drag&drop list to reorder the scrollable (non-frozen) table columns.

    Dragging a whole cross-column list is far less fiddly than repeated
    scroll/drag/scroll on the header itself, especially for columns far to the
    right. Frozen columns aren't listed since they aren't reorderable anyway.
    """

    def __init__(self, header: QHeaderView, model, freeze_count: int,
                 on_save: Optional[Callable[[], None]] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reorder Columns")
        self.setWindowFlag(Qt.Tool, True)
        self.resize(320, 480)
        self._header = header
        self._model = model
        self._freeze = freeze_count
        self._on_save = on_save

        layout = QVBoxLayout(self)
        hint = QLabel(
            "Drag rows to reorder columns. Frozen columns stay fixed.\n"
            "This only changes what you see right now — click \"Save layout\" "
            "to keep this order for next time.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.list = QListWidget()
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setDefaultDropAction(Qt.MoveAction)
        layout.addWidget(self.list)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        btn_save = QPushButton("Save layout", objectName="PurpleBtn")
        btn_save.setToolTip("Remember this column order for next time you open this screen")
        btn_save.clicked.connect(self._on_save_clicked)
        btn_row.addWidget(btn_save)
        btn_row.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        self._populate()
        self.list.model().rowsMoved.connect(self._apply_order)

    def _on_save_clicked(self):
        if callable(self._on_save):
            self._on_save()
        self.status_label.setText("Layout saved.")
        self.status_label.setStyleSheet("color: #1a6b1a;")

    def _visible_order(self) -> List[int]:
        """Current visual order of the non-frozen, non-hidden columns (as logical indices)."""
        order = []
        for v in range(self._header.count()):
            logical = self._header.logicalIndex(v)
            if logical >= self._freeze and not self._header.isSectionHidden(logical):
                order.append(logical)
        return order

    def _populate(self):
        self.list.blockSignals(True)
        self.list.clear()
        for logical in self._visible_order():
            label = self._model.headerData(logical, Qt.Horizontal, Qt.DisplayRole)
            item = QListWidgetItem("" if label is None else str(label))
            item.setData(Qt.UserRole, logical)
            self.list.addItem(item)
        self.list.blockSignals(False)

    def _apply_order(self, *args):
        for pos in range(self.list.count()):
            logical = self.list.item(pos).data(Qt.UserRole)
            target_visual = self._freeze + pos
            current_visual = self._header.visualIndex(logical)
            if current_visual != target_visual:
                self._header.moveSection(current_visual, target_visual)
        self.status_label.setText("Not saved yet.")
        self.status_label.setStyleSheet("color: #8a6d00;")


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
                on_edit_jet: Optional[Callable[[Dict], None]] = None,
                on_open_experiment: Optional[Callable[[int, int, str], None]] = None,
                sidebar_callbacks: Optional[dict] = None):
        super().__init__()
        self.on_back_home = on_back_home
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None
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
        self._on_open_experiment = on_open_experiment
        # Inline aufgeklappte UsedInTrial-Zeilen: Sets der gerade aufgeklappten
        # Jet-IDs bzw. TrialSeries-IDs. Die eigentlichen Zeilen sind echte,
        # eingefügte Model-Zeilen (siehe JetsTableModel.insert_detail_rows) -
        # kein Popup mehr (identisches Muster wie ManageYarnScreen). Anzahl
        # eingefrorener Spalten links (siehe FrozenNColumnsTable(freeze_count=2)
        # in _build_ui) - Detailzeilen werden ab hier in der rechten Ansicht
        # gespannt/beschriftet, links bleibt eine leere Spannzelle.
        self._expanded_jet_ids: set = set()
        self._expanded_series_ids: set = set()
        self._freeze_count = 2

        self.table: Optional[FrozenNColumnsTable] = None
        self.model: Optional[JetsTableModel] = None
        self.proxy: Optional[ExpandableFilterProxy] = None
        self._jet_search_cols: List[int] = []
        self.status_label: Optional[QLabel] = None
        self.search_edit: Optional[QLineEdit] = None
        self._fk_delegate: Optional[FKComboDelegate] = None
        self._search_highlight_delegate: Optional[SearchHighlightDelegate] = None
        self._column_order_dialog: Optional[ColumnOrderDialog] = None
        self._SCREEN_KEY = "manage_jets"
        self._read_only = False

        self._build_ui()
        self.reload_data()

    def _build_ui(self):
        """Erstellt Header, Filter-Toolbar, Tabelle und Footer."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring).
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        toolbar = QFrame()
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(24, 12, 24, 0)
        tl.setSpacing(8)

        self.search_edit = QLineEdit(placeholderText="Search Jet or Remarks… (separate multiple with ;)")
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

        self.btn_columns = QPushButton("Columns…", objectName="GreyBtn")
        self.btn_columns.setToolTip("Reorder columns via a drag & drop list")
        self.btn_columns.clicked.connect(self._on_columns_clicked)

        self.status_label = QLabel("")

        tl.addWidget(self.search_edit, 1)
        tl.addWidget(self.btn_reload, 0)
        tl.addWidget(self.btn_new, 0)
        tl.addWidget(self.btn_copy, 0)
        tl.addWidget(self.btn_edit_form, 0)
        tl.addWidget(self.btn_delete, 0)
        tl.addWidget(self.btn_columns, 0)
        tl.addWidget(self.btn_save, 0)
        tl.addWidget(self.status_label, 0, Qt.AlignVCenter)
        # Kontext-Hilfe EN/DE/ES (Nutzerwunsch 2026-10-13, ui/widgets/multilang_help.py)
        from ui.widgets.multilang_help import make_help_button
        tl.addWidget(make_help_button("How does Manage Jets work?", self._open_help), 0)

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
        # UsedInTrial ("Yes ▸/▾") und die daraus aufklappbaren TrialSeries-
        # Detailzeilen leben komplett im rechten (nicht eingefrorenen) Bereich
        # - EINE durchgehende Zelle statt über beide Ansichten gesplittet
        # (ein Versuch, das Dreieck in die linke/eingefrorene Spalte zu legen,
        # erzeugte eine hässliche Lücke zwischen den beiden getrennten Tabellen-
        # Widgets, siehe Screenshot-Feedback). 'clicked' (nur QModelIndex,
        # keine Pixel-Position) reicht deshalb wieder nicht aus für die
        # Dreieck-vs-Text-Unterscheidung auf Serien-Zeilen, siehe
        # eventFilter/_handle_table_click (identisches Muster wie ManageYarnScreen).
        self.table.right.viewport().installEventFilter(self)
        self.table.right.setMouseTracking(True)
        self.table.right.entered.connect(self._on_cell_hovered)

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

    def reload_data(self, select_id: Optional[int] = None):
        """Lädt alle Jet-Daten neu aus der DB (inkl. FK-Maps) und baut Modell neu auf.

        Args:
            select_id: Optional – ID des Jets der nach dem Laden selektiert werden soll.
        """
        if not callable(self._loader):
            self._set_status("No loader configured.", error=True)
            return
        # Vor dem Modell-Austausch alle inline aufgeklappten Zeilen sauber
        # zuklappen (das eingebettete Widget/der Span hängt am alten Modell/Proxy).
        self._collapse_all_usage_rows()
        try:
            rows = self._loader()
        except Exception as e:
            self._set_status(f"Load failed: {e}", error=True)
            return

        headers = list(rows[0].keys()) if rows else [self._id_col]

        # Who created this jet & when - hidden entirely for non-superusers,
        # not just read-only, per explicit user request ("versteckt tracken").
        if not app_meta.is_superuser_level():
            headers = [h for h in headers if _canon(h) not in _AUDIT_COLS]

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
                                    fk_maps=self._fk_maps_input, bool_columns=bool_cols,
                                    read_only=self._read_only)

        if self.proxy is None:
            self.proxy = ExpandableFilterProxy(self)
            self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
            self.proxy.setDynamicSortFilter(True)
            self.proxy.before_change = self._collapse_all_usage_rows
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

        # Highlights the matched substring in the columns the toolbar search scans
        # (skips any that are FK combo columns, which use FKComboDelegate instead).
        self._search_highlight_delegate = SearchHighlightDelegate(
            self.proxy, lambda: self._jet_search_cols, parent=self.table.right)
        for col_idx in self._jet_search_cols:
            if col_idx not in fk_cols_by_idx:
                self.table.setItemDelegateForColumn(col_idx, self._search_highlight_delegate)

        self._set_status("")
        self.table.resizeColumnsToContents()
        self._restore_column_order()
        self._apply_read_only_ui()
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
        """Ermittelt Jet- und Bemerkungen-Spalte für den Suchproxy (Suchfeld oben durchsucht beide)."""
        if not self.model:
            return
        headers = self.model.headers()
        self._jet_search_cols = [i for i, h in enumerate(headers)
                                  if _canon(h) in ("jet", "bemerkungen")]

    def _open_help(self):
        from ui.widgets.multilang_help import show_help
        from ui.widgets.help_texts_manage_jets import TEXTS
        show_help(TEXTS, self)

    def _on_search_changed(self, text: str):
        """Aktualisiert den Proxy-Filter bei Texteingabe im Suchfeld (durchsucht Jet + Bemerkungen)."""
        if not self.proxy:
            return
        cols = getattr(self, "_jet_search_cols", [])
        if not cols:
            return
        self.proxy.set_search_filter(cols, text)
        # Refresh header markers + cell highlighting
        try:
            self.table._left_header.viewport().update()
            self.table._right_header.viewport().update()
            self.table.left.viewport().update()
            self.table.right.viewport().update()
        except Exception:
            pass

    def _on_columns_clicked(self):
        """Öffnet/hebt die Drag&Drop-Spaltenliste zum Umsortieren der rechten (nicht eingefrorenen) Spalten."""
        if not self.model:
            return
        if self._column_order_dialog is None or not self._column_order_dialog.isVisible():
            self._column_order_dialog = ColumnOrderDialog(
                self.table._right_header, self.model, self.table._freeze,
                on_save=self._save_column_order_now, parent=self)
            self._column_order_dialog.show()
        else:
            self._column_order_dialog.raise_()
            self._column_order_dialog.activateWindow()

    def _save_column_order_now(self):
        """Persistiert die AKTUELLE Spaltenreihenfolge für den eingeloggten User.

        Nur explizit aufgerufen (Save-Button im Columns-Dialog) – Umsortieren
        allein soll NICHT automatisch speichern, das war explizites User-Feedback:
        eine Umsortierung kann auch nur einmalig/vorübergehend gemeint sein.
        """
        if not self.model:
            return
        freeze = self.table._freeze
        hdr = self.table._right_header
        headers = self.model.headers()
        order = []
        for v in range(hdr.count()):
            logical = hdr.logicalIndex(v)
            if logical >= freeze and logical < len(headers) and not hdr.isSectionHidden(logical):
                order.append(headers[logical])
        from db.user_column_order import save_column_order
        save_column_order(self._SCREEN_KEY, order)

    def _restore_column_order(self):
        """Wendet die zuletzt für diesen User gespeicherte Spaltenreihenfolge an (falls vorhanden)."""
        if not self.model:
            return
        from db.user_column_order import load_column_order
        saved = load_column_order(self._SCREEN_KEY)
        if not saved:
            return
        freeze = self.table._freeze
        hdr = self.table._right_header
        name_to_logical = {h: i for i, h in enumerate(self.model.headers())}

        pos = freeze
        for name in saved:
            logical = name_to_logical.get(name)
            if logical is None or logical < freeze:
                continue
            current_visual = hdr.visualIndex(logical)
            if current_visual != pos:
                hdr.moveSection(current_visual, pos)
            pos += 1

    def set_read_only(self, read_only: bool):
        """Schaltet Schreibrechte um: Add/Copy/Delete/Save + Zell-Editing gesperrt,
        Suche/Filter/Spalten-Reorder bleiben immer nutzbar. Von main.py bei jeder
        Navigation zu diesem Screen mit dem aktuellen Permission-Stand aufgerufen
        (der eingeloggte User kann sich seit dem letzten Öffnen geändert haben)."""
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
        for btn in (self.btn_new, self.btn_copy, self.btn_delete, self.btn_save):
            btn.setEnabled(not ro)
            btn.setToolTip(tooltip)
        # Stays enabled read-only: viewing a single record in the form is often
        # clearer than the pivot table, even with nothing editable in it.
        self.btn_edit_form.setText("View in Form" if ro else "Edit in Form")
        self.btn_edit_form.setToolTip(
            "View this jet's full record (read-only)" if ro else "")

    def save_changes(self):
        """Schreibt alle dirty Zeilen via UPDATE in die DB."""
        if not self.model or self._read_only:
            return
        # model.clear_dirty() (unten, nach erfolgreichem Save) macht einen
        # vollen beginResetModel()/endResetModel() - das würde eine gerade
        # inline aufgeklappte Detailzeile/deren Span in einen unsauberen
        # Zustand bringen. Vorher sauber zuklappen (Detailzeilen sind ohnehin
        # nie dirty, das betrifft also nie ungespeicherte Edits).
        self._collapse_all_usage_rows()
        dirty_rows = self.model.dirty_rows()
        if not dirty_rows:
            self._set_status("No changes to save.")
            return
        if not callable(self._saver):
            self._set_status("No saver configured.", error=True)
            return

        try:
            # Strip synthetic/computed columns that don't exist in the DB
            _SYNTHETIC = {"__has_files__", "has_files", "UsedInTrial"}
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
        if self._read_only:
            return
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
        if self._read_only:
            return
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

    def _on_row_double_clicked(self, index):
        """Doppelklick: auf einer Detailzeile (Serie/Versuch) nichts - die
        Serien-Zeile navigiert bereits per Einfachklick auf den Text (siehe
        _handle_table_click). Sonst wie bisher → Formular-Dialog."""
        kind, _src_row = self._row_kind_at(index)
        if kind in ('series', 'trial'):
            return
        self._on_edit_form()

    def _usedintrial_col_idx(self) -> int:
        """Logischer Spaltenindex von UsedInTrial, oder -1 falls nicht vorhanden."""
        if not self.model:
            return -1
        try:
            return self.model.headers().index("UsedInTrial")
        except ValueError:
            return -1

    def _row_kind_at(self, index) -> Tuple[str, int]:
        """Source-Zeilenart + Source-Row-Index für einen (Proxy-)Index, oder
        ('jet', -1) falls nicht auflösbar."""
        if not index.isValid() or not self.model or not self.proxy:
            return 'jet', -1
        try:
            src_row = self.proxy.mapToSource(index).row()
            rows = self.model._rows
            if src_row < 0 or src_row >= len(rows):
                return 'jet', -1
            return rows[src_row].get('_row_kind', 'jet'), src_row
        except Exception:
            return 'jet', -1

    def _label_anchor_col(self) -> int:
        """Spalte, ab der eine Detailzeile ihr Label trägt/gespannt wird -
        die UsedInTrial-Spalte selbst (Nutzerwunsch: "Infos direkt unter dem
        Yes von UsedInTrial"), NICHT mehr fix die erste nicht eingefrorene
        Spalte. Ursprünglich schon einmal an UsedInTrial selbst verankert,
        dann auf die Freeze-Grenze umgestellt, weil UsedInTrial als späte
        berechnete Spalte (SELECT j.*, has_files, UsedInTrial) den Span
        winzig machte. Per echtem Qt-Test verifiziert (QHeaderView mit
        reordered Sections): QTableView.setSpan() rendert die Span-Zelle an
        der AKTUELLEN VISUELLEN Position der Start-Spalte, nicht an ihrer
        logischen - ein bewusst überhöhter columnSpan-Wert (siehe
        _apply_full_row_span, `col_count` statt `col_count - anchor`) wird
        von Qt auf den tatsächlich verbleibenden sichtbaren Platz gekappt.
        Dadurch rendert der Span jetzt IMMER korrekt ab der aktuellen
        Position von UsedInTrial bis zum rechten Rand, unabhängig davon, ob
        der Nutzer die Spalte per Drag&Drop (Columns…-Dialog) verschoben hat
        - genau das war beim vorherigen Freeze-Anker kaputt: der Span-Start
        blieb an einer festen logischen Spalte hängen, während UsedInTrial
        (von main.py._load_jets_data() als letzte SELECT-Spalte geliefert)
        an eine ganz andere Position verschoben war, wodurch das Label
        sichtbar neben statt unter "Yes" auftauchte."""
        idx = self._usedintrial_col_idx()
        return idx if idx >= 0 else self._freeze_count

    def _series_triangle_zone_width(self) -> int:
        """Breite (px) des Dreieck-Klickbereichs am Zeilenanfang einer
        TrialSeries-Detailzeile - siehe ManageYarnScreen für die identische
        Logik/Begründung."""
        fm = self.table.right.fontMetrics()
        return fm.horizontalAdvance('▸  ') + 8

    def _handle_table_click(self, pos):
        """Zentrale Klick-Logik für die rechte (nicht eingefrorene) Ansicht -
        siehe eventFilter. Klick auf eine "Yes ▸/▾"-Zelle klappt die Jet-Zeile
        auf/zu. Auf einer TrialSeries-Zeile klappt ein Klick auf das Dreieck
        selbst die Versuchsnummern auf/zu, ein Klick auf den Rest der Zeile
        (nicht wie ein Link dargestellt, aber klickbar) navigiert direkt zum
        Experiment. Versuchsnummer-Zeilen sind nur informativ."""
        if not self.model or not self.proxy:
            return
        index = self.table.right.indexAt(pos)
        if not index.isValid():
            return
        kind, src_row = self._row_kind_at(index)
        if src_row < 0:
            return
        if kind == 'jet':
            ui_idx = self._usedintrial_col_idx()
            disp = index.data(Qt.DisplayRole)
            if ui_idx < 0 or index.column() != ui_idx or not disp or not str(disp).startswith('Yes'):
                return
            jet_id = self.model._rows[src_row].get(self._id_col)
            if jet_id in self._expanded_jet_ids:
                self._collapse_jet_row(jet_id)
            else:
                self._expand_jet_row(jet_id, index)
        elif kind == 'series':
            row = self.model._rows[src_row]
            payload = row['_series_payload']
            series_id = payload['series_id']
            rect = self.table.right.visualRect(index)
            on_triangle = (pos.x() - rect.x()) <= self._series_triangle_zone_width()
            if on_triangle:
                if series_id in self._expanded_series_ids:
                    self._collapse_series_row(series_id)
                else:
                    self._expand_series_row(series_id, index)
            elif callable(self._on_open_experiment):
                self._on_open_experiment(payload['exp_pk'], payload['series_id'], payload['experiment_id_text'])
        # 'trial'-Zeilen: nicht klickbar

    def eventFilter(self, obj, event):
        """Fängt Linksklicks auf dem Viewport der rechten (nicht eingefrorenen)
        Ansicht ab, um die Klick-Position (Dreieck vs. Text auf Serien-Zeilen)
        zu bekommen - identisches Muster wie ManageYarnScreen."""
        if (obj is self.table.right.viewport() and event.type() == QEvent.MouseButtonRelease
                and event.button() == Qt.LeftButton):
            self._handle_table_click(event.pos())
        return super().eventFilter(obj, event)

    def _on_cell_hovered(self, index):
        """Zeigt einen Hand-Cursor über "Yes …"-Zellen sowie über kompletten
        TrialSeries-Detailzeilen (klickbar, aber ohne Link-Farbe/Unterstreichung)."""
        clickable = False
        if index.isValid():
            kind, src_row = self._row_kind_at(index)
            if src_row >= 0:
                if kind == 'series':
                    clickable = True
                elif kind == 'jet':
                    ui_idx = self._usedintrial_col_idx()
                    disp = index.data(Qt.DisplayRole)
                    clickable = (ui_idx >= 0 and index.column() == ui_idx
                                 and bool(disp) and str(disp).startswith('Yes'))
        self.table.right.viewport().setCursor(Qt.PointingHandCursor if clickable else Qt.ArrowCursor)

    @staticmethod
    def _fmt_num(v) -> Optional[str]:
        """Kompakte Zahlendarstellung fürs Trial-Detail-Label (800.00 -> '800',
        3.50 -> '3.5') - identisch zu ManageYarnScreen._fmt_num (dort nicht
        wiederverwendet, um keinen Cross-Import zwischen den beiden
        eigenständigen Kopien dieser Aufklapp-Logik einzuführen)."""
        if v is None:
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        return f'{f:.0f}' if f == int(f) else f'{f:.1f}'

    def _fetch_jet_usage(self, jet_id) -> List[Dict]:
        """Alle TrialSeries (+ deren Versuchsnummern), die diesen Jet über
        tbltrial.JetID verwenden (kein Ply/Settings-Umweg wie bei Yarn -
        ein Trial referenziert seinen Jet direkt). Zusatzdaten pro Versuch wie
        bei ManageYarnScreen (Overfeed/Speed, ATY-Sonderfelder), aber statt des
        Jets (hier ja schon durch jet_id feststehend) wird das/die verwendete(n)
        Garn(e) gezeigt - ein Trial kann mehrere Plies haben (tbltrialsettings),
        darum GROUP_CONCAT statt eines einzelnen Werts."""
        sql = (
            "SELECT s.ID AS SeriesID, s.ExperimentID AS ExpPK, "
            "e.ExperimentID AS ExperimentIdText, s.SeriesName, m.Maschine AS MachineName, "
            "mt.Maschinentyp AS MachineType, "
            "t.Versuchsnummer, t.Shaft2x_OF AS OverfeedPct, t.SpeedShaft2 AS SpeedMMin, "
            "t.`Shaft1,1Core_OF` AS CoreOfPct, t.`Shaft1,2Effect_OF` AS EffectOfPct, "
            "t.Shaft2Speed AS AtySpeedMMin, "
            "GROUP_CONCAT(COALESCE(NULLIF(y.Kurzname, ''), y.Name) ORDER BY ts.Ply SEPARATOR ' / ') AS YarnNames "
            "FROM tbltrial t "
            "JOIN tbltrialseries s ON s.ID = t.TrialSeriesID "
            "JOIN tblexperimente e ON e.ID = s.ExperimentID "
            "LEFT JOIN tblmaschine m ON m.ID = s.MachineID "
            "LEFT JOIN tblmaschinentypen mt ON mt.ID = m.Maschinentyp "
            "LEFT JOIN tbltrialsettings ts ON ts.TrialID = t.ID "
            "LEFT JOIN tblyarn y ON y.ID = ts.YarnID "
            "WHERE t.JetID = ? "
            "GROUP BY t.ID, s.ID, s.ExperimentID, e.ExperimentID, s.SeriesName, m.Maschine, "
            "mt.Maschinentyp, t.Versuchsnummer, t.Shaft2x_OF, t.SpeedShaft2, "
            "t.`Shaft1,1Core_OF`, t.`Shaft1,2Effect_OF`, t.Shaft2Speed "
            "ORDER BY e.ExperimentID, s.SeriesName, t.Versuchsnummer"
        )
        from db.connection import fetch_all
        rows = fetch_all(sql, [jet_id])
        series_map: Dict[object, Dict] = {}
        for r in rows:
            sid = r.get("SeriesID")
            if sid not in series_map:
                exp_txt = r.get("ExperimentIdText") or ""
                series_name = r.get("SeriesName") or ""
                label = f"{exp_txt}.{series_name}" if exp_txt else series_name
                series_map[sid] = {
                    "series_id": sid,
                    "exp_pk": r.get("ExpPK"),
                    "experiment_id_text": exp_txt,
                    "label": label,
                    "machine_name": r.get("MachineName"),
                    "trial_numbers": [],
                }
            vno = r.get("Versuchsnummer")
            if vno is None:
                continue
            existing_vnos = {t["vno"] for t in series_map[sid]["trial_numbers"]}
            if vno not in existing_vnos:
                is_aty = r.get("MachineType") == "ATY"
                speed_val = r.get("AtySpeedMMin") if is_aty else r.get("SpeedMMin")
                series_map[sid]["trial_numbers"].append({
                    "vno": vno,
                    "yarn": r.get("YarnNames"),
                    "is_aty": is_aty,
                    "of_pct": self._fmt_num(r.get("OverfeedPct")),
                    "core_of": self._fmt_num(r.get("CoreOfPct")),
                    "effect_of": self._fmt_num(r.get("EffectOfPct")),
                    "speed": self._fmt_num(speed_val),
                })
        return list(series_map.values())

    def _find_source_row_for_id(self, jet_id) -> Optional[int]:
        if not self.model:
            return None
        for i, row in enumerate(self.model._rows):
            if row.get('_row_kind', 'jet') == 'jet' and row.get(self._id_col) == jet_id:
                return i
        return None

    def _find_source_row_for_series(self, series_id) -> Optional[int]:
        if not self.model:
            return None
        for i, row in enumerate(self.model._rows):
            if row.get('_row_kind') == 'series' and row.get('_series_payload', {}).get('series_id') == series_id:
                return i
        return None

    def _apply_full_row_span(self, src_row: int):
        """Merged die ganze Zeile zu je einer Zelle pro Ansicht (links: leere
        Spannzelle über die eingefrorenen Spalten; rechts: die Label-Zelle ab
        _label_anchor_col(), siehe JetsTableModel._detail_row_data) - für neu
        eingefügte Detailzeilen direkt nach dem Insert aufgerufen."""
        if not self.model or not self.proxy:
            return
        proxy_index = self.proxy.mapFromSource(self.model.index(src_row, 0))
        if not proxy_index.isValid():
            return
        view_row = proxy_index.row()
        self.table.left.setSpan(view_row, 0, 1, self._freeze_count)
        anchor = self._label_anchor_col()
        # Bewusst der volle columnCount() statt "col_count - anchor": Qt kappt
        # das ohnehin auf den tatsächlich verbleibenden sichtbaren Platz ab der
        # AKTUELLEN VISUELLEN Position von `anchor` (siehe _label_anchor_col) -
        # "col_count - anchor" ginge dagegen von unverschobener Logical==Visual-
        # Reihenfolge aus und würde nach einem Drag&Drop-Reorder zu kurz greifen.
        self.table.right.setSpan(view_row, anchor, 1, self.model.columnCount())

    def _clear_full_row_span(self, src_row: int):
        """Gegenstück zu _apply_full_row_span() - vor dem Entfernen einer
        Detailzeile aufgerufen, damit kein Span auf eine dann falsche Zeile zeigt."""
        if not self.model or not self.proxy:
            return
        proxy_index = self.proxy.mapFromSource(self.model.index(src_row, 0))
        if not proxy_index.isValid():
            return
        view_row = proxy_index.row()
        self.table.left.setSpan(view_row, 0, 1, 1)
        self.table.right.setSpan(view_row, self._label_anchor_col(), 1, 1)

    @staticmethod
    def _series_label(payload: Dict, expanded: bool) -> str:
        """Dreieck + Beschreibungstext zusammen, OHNE führenden Einzug (im
        Unterschied zu ManageYarnScreen's '      ▸  ...') - startet damit
        direkt am linken Rand der rechten (scrollbaren) Ansicht, wo die ganze
        Detailzeile lebt (siehe JetsTableModel._detail_row_data)."""
        arrow = '▾' if expanded else '▸'
        n = len(payload['trial_numbers'])
        base = f'{arrow}  {payload["label"]}   ({n} trial{"s" if n != 1 else ""})'
        machine_name = payload.get('machine_name')
        return f'{base} - {machine_name}' if machine_name else base

    @staticmethod
    def _trial_label(t: Dict) -> str:
        """'V<n> - <Garn>, <OF>% OF, <Speed>m/min' (ATY: Core/Effect OF getrennt
        statt einer einzelnen OF-Zahl) - analog zu ManageYarnScreen._trial_label,
        aber mit dem verwendeten Garn statt dem Jet (der ist hier ja durch
        jet_id bereits feststehend). Jeder Teil ausser V<n> entfällt einzeln,
        wenn der Wert fehlt."""
        parts = []
        if t.get('yarn'):
            parts.append(str(t['yarn']))
        if t.get('is_aty'):
            if t.get('core_of') is not None:
                parts.append(f"{t['core_of']}% Core OF")
            if t.get('effect_of') is not None:
                parts.append(f"{t['effect_of']}% Effect OF")
        elif t.get('of_pct') is not None:
            parts.append(f"{t['of_pct']}% OF")
        if t.get('speed') is not None:
            parts.append(f"{t['speed']}m/min")
        suffix = f" - {', '.join(parts)}" if parts else ''
        return f"    •  V{t['vno']}{suffix}"

    def _set_series_row_label(self, row_idx: int, payload: Dict, expanded: bool):
        self.model._rows[row_idx]['_label'] = self._series_label(payload, expanded)
        idx = self.model.index(row_idx, self._label_anchor_col())
        self.model.dataChanged.emit(idx, idx, [Qt.DisplayRole])

    def _expand_jet_row(self, jet_id, clicked_index):
        """Fügt für jede TrialSeries, die diesen Jet verwendet, eine echte
        Zeile direkt unter der Jet-Zeile ein (nicht wie ein Link dargestellt,
        aber klickbar - Klick aufs Dreieck klappt die Versuchsnummern auf,
        Klick auf den Rest der Zeile öffnet das Experiment)."""
        try:
            series_list = self._fetch_jet_usage(jet_id)
        except Exception as e:
            QMessageBox.critical(self, 'Used in Trial Series', f'Could not load usage: {e}')
            return
        if not series_list:
            QMessageBox.information(
                self, 'Used in Trial Series',
                'No trial series found for this jet (data may have changed - try Reload).')
            return

        src_row = self.proxy.mapToSource(clicked_index).row()
        detail_rows = []
        for order, s in enumerate(series_list, start=1):
            detail_rows.append({
                '_row_kind': 'series',
                '_anchor_jet_id': jet_id,
                '_order': float(order),
                '_series_payload': s,
                '_label_col': self._label_anchor_col(),
                '_label': self._series_label(s, expanded=False),
            })
        self.model.insert_detail_rows(src_row, detail_rows)
        for offset in range(1, len(detail_rows) + 1):
            self._apply_full_row_span(src_row + offset)

        self._expanded_jet_ids.add(jet_id)
        self.model.set_expanded(jet_id, True)

    def _collapse_jet_row(self, jet_id):
        """Entfernt den kompletten Detail-Block unter der Jet-Zeile wieder
        (Serien-Zeilen UND alle evtl. noch offenen Versuchsnummer-Zeilen
        darunter - beides liegt lückenlos hintereinander)."""
        if jet_id not in self._expanded_jet_ids:
            return
        src_row = self._find_source_row_for_id(jet_id)
        self._expanded_jet_ids.discard(jet_id)
        self.model.set_expanded(jet_id, False)
        if src_row is None:
            return
        rows = self.model._rows
        i = src_row + 1
        removed_series_ids = []
        while i < len(rows) and rows[i].get('_row_kind', 'jet') != 'jet':
            if rows[i].get('_row_kind') == 'series':
                removed_series_ids.append(rows[i]['_series_payload']['series_id'])
            i += 1
        count = i - (src_row + 1)
        if count:
            for j in range(src_row + 1, src_row + 1 + count):
                self._clear_full_row_span(j)
            self.model.remove_rows_span(src_row + 1, count)
        for sid in removed_series_ids:
            self._expanded_series_ids.discard(sid)

    def _expand_series_row(self, series_id, clicked_index):
        """Fügt für jede Versuchsnummer dieser TrialSeries eine (nicht
        klickbare, rein informative) Zeile direkt unter der Serien-Zeile ein."""
        src_row = self.proxy.mapToSource(clicked_index).row()
        row = self.model._rows[src_row]
        payload = row['_series_payload']
        jet_id = row['_anchor_jet_id']
        base_order = row.get('_order', 0.0)
        trial_rows = [{
            '_row_kind': 'trial',
            '_anchor_jet_id': jet_id,
            '_order': base_order + i / 100000.0,
            '_label_col': self._label_anchor_col(),
            '_label': self._trial_label(t),
        } for i, t in enumerate(payload['trial_numbers'], start=1)]
        self.model.insert_detail_rows(src_row, trial_rows)
        for offset in range(1, len(trial_rows) + 1):
            self._apply_full_row_span(src_row + offset)

        self._expanded_series_ids.add(series_id)
        self._set_series_row_label(src_row, payload, expanded=True)

    def _collapse_series_row(self, series_id):
        if series_id not in self._expanded_series_ids:
            return
        src_row = self._find_source_row_for_series(series_id)
        self._expanded_series_ids.discard(series_id)
        if src_row is None:
            return
        rows = self.model._rows
        i = src_row + 1
        while i < len(rows) and rows[i].get('_row_kind') == 'trial':
            i += 1
        count = i - (src_row + 1)
        if count:
            for j in range(src_row + 1, src_row + 1 + count):
                self._clear_full_row_span(j)
            self.model.remove_rows_span(src_row + 1, count)
        payload = self.model._rows[src_row]['_series_payload']
        self._set_series_row_label(src_row, payload, expanded=False)

    def _collapse_all_usage_rows(self):
        """Klappt alles zu - aufgerufen vor jedem Reload/Save sowie (über
        ExpandableFilterProxy.before_change) vor jedem Sortieren/Filtern,
        weil Detailzeilen an einer festen Position relativ zu ihrer Eltern-
        Zeile hängen und sonst verstreut würden."""
        for jet_id in list(self._expanded_jet_ids):
            self._collapse_jet_row(jet_id)
        self._expanded_series_ids.clear()

    def _on_edit_form(self):
        """Öffnet den selektierten Jet im bestehenden NewJetScreen-Formular als Dialog.
        Bleibt auch im Read-only-Modus verfügbar (übersichtlicher pro Datensatz),
        NewJetScreen selbst wird dabei strikt read-only geöffnet, siehe main.py."""
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
        if self._read_only:
            return
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