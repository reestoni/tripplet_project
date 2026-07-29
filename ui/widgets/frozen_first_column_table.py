# ui/widgets/frozen_first_column_table.py
from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt, Slot, QEvent
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QTableView, QAbstractItemView, QHeaderView, QSizePolicy
)
from PySide6.QtCore import QItemSelectionModel


class FrozenFirstColumnTable(QWidget):
    """
    Kombi-Widget aus vier QTableViews ("Freeze Panes", wie in Excel):

        +----------------+---------------------------------------+
        | top_left       | top_right                              |  <- Titel-/Header-Zeilen
        | (Spalte 0,     | (Spalten 1..N,                         |     (fixiert vertikal)
        |  Header-Zeilen)|  Header-Zeilen)                        |
        +----------------+---------------------------------------+
        | bottom_left    | bottom_right                           |  <- Datenzeilen
        | (Spalte 0,     | (Spalten 1..N,                         |     (scrollbar)
        |  Datenzeilen)  |  Datenzeilen)  <- Hauptansicht, scrollt |
        +----------------+---------------------------------------+
             ^ fixiert horizontal              ^ scrollt

    - Spalte 0 (Parameter-Titel) bleibt beim horizontalen Scrollen fixiert.
    - Die Header-Zeilen ganz oben (PivotEditModel._n_hdr, z.B. Trial-/Ply-
      Titelzeilen) bleiben beim vertikalen Scrollen fixiert.
    - Scrollen, Zeilenhöhen, Spaltenbreiten und Selektion sind zwischen allen
      vier Teilansichten synchronisiert.
    - Übliche QTableView-APIs werden an die Hauptansicht (bottom_right)
      weitergereicht, damit sich das Widget wie eine einzelne QTableView
      anfühlt.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialisiert alle vier QTableViews und koppelt Scrollen, Zeilen-/Spaltengrössen und Selektion."""
        super().__init__(parent)
        self._model = None
        self._n_hdr = 0
        self._syncing = False  # Reentrancy-Guard fuer Resize-Sync

        self.top_left = QTableView(self)
        self.top_right = QTableView(self)
        self.bottom_left = QTableView(self)
        self.bottom_right = QTableView(self)

        # Rückwärtskompatible Aliase (ältere Aufrufer/Attribute erwarten .left/.right)
        self.left = self.bottom_left
        self.right = self.bottom_right

        lay = QGridLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.top_left, 0, 0)
        lay.addWidget(self.top_right, 0, 1)
        lay.addWidget(self.bottom_left, 1, 0)
        lay.addWidget(self.bottom_right, 1, 1)

        self.top_left.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.bottom_left.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.top_right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.bottom_right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        for v in (self.top_left, self.top_right, self.bottom_left):
            v.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            v.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        for v in (self.top_left, self.top_right, self.bottom_left, self.bottom_right):
            v.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
            v.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
            v.horizontalHeader().setSectionsMovable(False)
            v.setCornerButtonEnabled(False)

        self.setFocusProxy(self.bottom_right)

        self.bottom_right.verticalScrollBar().valueChanged.connect(
            self.bottom_left.verticalScrollBar().setValue)
        self.bottom_left.verticalScrollBar().valueChanged.connect(
            self.bottom_right.verticalScrollBar().setValue)

        self.bottom_right.horizontalScrollBar().valueChanged.connect(
            self.top_right.horizontalScrollBar().setValue)
        self.top_right.horizontalScrollBar().valueChanged.connect(
            self.bottom_right.horizontalScrollBar().setValue)

        self.top_left.verticalHeader().sectionResized.connect(
            lambda r, o, n: self._sync_row_height(self.top_right, r, n))
        self.top_right.verticalHeader().sectionResized.connect(
            lambda r, o, n: self._sync_row_height(self.top_left, r, n))
        self.bottom_left.verticalHeader().sectionResized.connect(
            lambda r, o, n: self._sync_row_height(self.bottom_right, r, n))
        self.bottom_right.verticalHeader().sectionResized.connect(
            lambda r, o, n: self._sync_row_height(self.bottom_left, r, n))

        self.top_left.horizontalHeader().sectionResized.connect(
            self._on_col0_resized_top)
        self.bottom_left.horizontalHeader().sectionResized.connect(
            self._on_col0_resized_bottom)
        self.top_right.horizontalHeader().sectionResized.connect(
            lambda c, o, n: self._sync_col_width(self.bottom_right, c, n))
        self.bottom_right.horizontalHeader().sectionResized.connect(
            lambda c, o, n: self._sync_col_width(self.top_right, c, n))

        for v in (self.top_left, self.top_right, self.bottom_left):
            v.setFrameShape(self.bottom_right.frameShape())
            v.setFrameShadow(self.bottom_right.frameShadow())

        self.top_left.verticalHeader().setVisible(False)
        self.top_right.verticalHeader().setVisible(False)
        self.bottom_right.verticalHeader().installEventFilter(self)
        self._sync_vheader_visibility()

    # ---------- Öffentliche API ----------

    def setModel(self, model):
        """Alle vier Ansichten auf dasselbe Model setzen, Zeilen/Spalten passend ausblenden."""
        self._model = model
        self._n_hdr = int(getattr(model, "_n_hdr", 0) or 0)

        sel = QItemSelectionModel(model)
        for v in (self.top_left, self.top_right, self.bottom_left, self.bottom_right):
            v.setModel(model)
            v.setSelectionModel(sel)

        self._apply_row_and_column_visibility()

        self.top_left.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.bottom_left.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.top_right.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.bottom_right.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        self.top_left.resizeColumnToContents(0)
        self.bottom_left.resizeColumnToContents(0)
        self._update_left_width()

        self.top_left.horizontalHeader().sectionResized.connect(
            lambda sec, old, new: self._update_left_width() if sec == 0 else None)
        self.bottom_left.horizontalHeader().sectionResized.connect(
            lambda sec, old, new: self._update_left_width() if sec == 0 else None)

        if self._n_hdr > 0:
            # Model hat eigene Pseudo-Header-Zeilen (z.B. Trial-/Ply-Titel).
            # Diese oben fixiert anzeigen; nativer Spaltenkopf waere hier nur
            # eine leere/doppelte Kopfzeile -> ausblenden.
            self.top_left.setVisible(True)
            self.top_right.setVisible(True)
            for v in (self.top_left, self.top_right, self.bottom_left, self.bottom_right):
                v.horizontalHeader().setVisible(False)
            self._update_top_height()
        else:
            # Keine Pseudo-Header-Zeilen -> die Tabelle nutzt den nativen
            # Qt-Spaltenkopf zur Beschriftung. Der ist in Qt bereits von
            # Haus aus beim vertikalen Scrollen fixiert, daher wird hier kein
            # zusaetzliches oberes Panel gebraucht (sonst gaebe es eine leere
            # Dopplung). Verhaelt sich dann wie die reine 2-Spalten-Variante.
            self.top_left.setVisible(False)
            self.top_right.setVisible(False)

        self.top_left.model().rowsInserted.connect(lambda *a: self._update_top_height())
        self.top_left.model().modelReset.connect(lambda: self._update_top_height())

    def verticalHeader(self):  # noqa: N802
        """Gibt den vertikalen Header der Hauptansicht (Datenzeilen, rechts unten) zurück."""
        return self.bottom_right.verticalHeader()

    def horizontalHeader(self):  # noqa: N802
        """Gibt den horizontalen Header der Hauptansicht zurück."""
        return self.bottom_right.horizontalHeader()

    def setSelectionBehavior(self, behavior):  # noqa: N802
        for v in (self.top_left, self.top_right, self.bottom_left, self.bottom_right):
            v.setSelectionBehavior(behavior)

    def setEditTriggers(self, triggers):  # noqa: N802
        for v in (self.top_left, self.top_right, self.bottom_left, self.bottom_right):
            v.setEditTriggers(triggers)

    def setStyleSheet(self, style):  # noqa: N802
        QWidget.setStyleSheet(self, style)
        for v in (self.top_left, self.top_right, self.bottom_left, self.bottom_right):
            v.setStyleSheet(style)

    def resizeColumnsToContents(self, fixed_data_column_width: Optional[int] = None):  # noqa: N802
        """Spaltenbreiten anpassen.

        `fixed_data_column_width`: wenn gesetzt, werden die Datenspalten
        (1..N) auf diese feste Breite gesetzt statt inhaltsbasiert berechnet.
        Qt's `resizeColumnsToContents()` ruft dafür `.data()` für JEDE Zelle
        jeder Spalte auf (O(rows x cols)) - bei Pivot-Tabellen mit
        trial-abhängig vielen Spalten (z.B. ShowExperimentScreen, hunderte
        Trials = hunderte Spalten) dominiert das die Ladezeit. Spalte 0
        (Parameter-Titel) bleibt immer inhaltsbasiert (nur eine Spalte,
        O(rows), unkritisch).
        """
        self.top_left.resizeColumnToContents(0)
        self.bottom_left.resizeColumnToContents(0)
        if fixed_data_column_width is not None:
            model = self.bottom_right.model()
            n_cols = model.columnCount() if model else 0
            for c in range(1, n_cols):
                self.bottom_right.setColumnWidth(c, fixed_data_column_width)
        else:
            self.bottom_right.resizeColumnsToContents()
        self._sync_all_column_widths_from(self.bottom_right)
        self._update_left_width()

    def selectionModel(self):  # noqa: N802
        return self.bottom_right.selectionModel()

    def model(self):  # noqa: N802
        return self._model

    def __getattr__(self, name):
        """Delegiert unbekannte Attribute/Methoden an die Hauptansicht (Kompatibilität mit QTableView-API)."""
        return getattr(self.bottom_right, name)

    # ---------- Private Helfer ----------

    def _apply_row_and_column_visibility(self):
        if self._model is None:
            return
        cols = self._model.columnCount()
        rows = self._model.rowCount()
        n_hdr = self._n_hdr

        for c in range(cols):
            self.top_left.setColumnHidden(c, c != 0)
            self.bottom_left.setColumnHidden(c, c != 0)
            self.top_right.setColumnHidden(c, c == 0)
            self.bottom_right.setColumnHidden(c, c == 0)

        for r in range(rows):
            is_hdr = r < n_hdr
            self.top_left.setRowHidden(r, not is_hdr)
            self.top_right.setRowHidden(r, not is_hdr)
            self.bottom_left.setRowHidden(r, is_hdr)
            self.bottom_right.setRowHidden(r, is_hdr)

    def _update_left_width(self):
        try:
            colw = max(self.top_left.columnWidth(0), self.bottom_left.columnWidth(0))
            self.top_left.setColumnWidth(0, colw)
            self.bottom_left.setColumnWidth(0, colw)
            vhw = self.bottom_left.verticalHeader().width()
            fw = self.bottom_left.frameWidth() * 2
            w = colw + vhw + fw
            self.top_left.setFixedWidth(w)
            self.bottom_left.setFixedWidth(w)
        except Exception:
            pass

    def _update_top_height(self):
        try:
            self.top_left.resizeRowsToContents()
            total = 0
            for r in range(self._n_hdr):
                total += self.top_left.rowHeight(r)
            fw = self.top_left.frameWidth() * 2
            hhw = self.top_left.horizontalHeader().height() if self.top_left.horizontalHeader().isVisible() else 0
            h = total + fw + hhw
            self.top_left.setFixedHeight(h)
            self.top_right.setFixedHeight(h)
        except Exception:
            pass

    def _sync_vheader_visibility(self):
        try:
            vis = self.bottom_right.verticalHeader().isVisible()
            if self.bottom_left.verticalHeader().isVisible() != vis:
                self.bottom_left.verticalHeader().setVisible(vis)
        except Exception:
            pass

    def eventFilter(self, obj, ev):
        try:
            if obj is self.bottom_right.verticalHeader() and ev.type() in (QEvent.Hide, QEvent.Show):
                self._sync_vheader_visibility()
        except Exception:
            pass
        return super().eventFilter(obj, ev)

    def _sync_row_height(self, target_view: QTableView, row: int, new_size: int):
        if self._syncing:
            return
        try:
            self._syncing = True
            if target_view.verticalHeader().sectionSize(row) != new_size:
                target_view.verticalHeader().resizeSection(row, new_size)
        except Exception:
            pass
        finally:
            self._syncing = False

    def _sync_col_width(self, target_view: QTableView, col: int, new_size: int):
        if self._syncing:
            return
        try:
            self._syncing = True
            if target_view.columnWidth(col) != new_size:
                target_view.setColumnWidth(col, new_size)
        except Exception:
            pass
        finally:
            self._syncing = False

    def _sync_all_column_widths_from(self, source_view: QTableView):
        if self._model is None:
            return
        try:
            for c in range(1, self._model.columnCount()):
                self.top_right.setColumnWidth(c, source_view.columnWidth(c))
        except Exception:
            pass

    def _on_col0_resized_top(self, sec: int, _old: int, new: int):
        if sec != 0:
            return
        self._sync_col_width(self.bottom_left, 0, new)

    def _on_col0_resized_bottom(self, sec: int, _old: int, new: int):
        if sec != 0:
            return
        self._sync_col_width(self.top_left, 0, new)