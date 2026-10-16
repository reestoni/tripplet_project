# ui/widgets/frozen_first_column_table.py
from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt, Slot, QEvent
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QTableView, QAbstractItemView, QHeaderView, QSizePolicy, QLabel, QApplication,
    QAbstractItemDelegate,
)
from PySide6.QtCore import QItemSelectionModel

from ui import display_prefs

# High contrast (Settings -> Display, see ui/display_prefs.py): appended to
# the table's own stylesheet so it wins over grid/selection colours there.
_CONTRAST_QSS = """
QTableView { gridline-color: #404040; color: #000000; }
QTableView::item:selected { background: #1F4E8C; color: #FFFFFF; }
"""


class _GridView(QTableView):
    """QTableView with Excel-like Enter (Nutzerwunsch 2026-10-16): Enter
    goes to the cell below - after typing a value (the editor closes with
    "submit") and also without editing. Shift+Enter goes up. Hidden rows
    are skipped; the views share one selection model, so moving here moves
    the current cell of the whole table."""

    def _step(self, delta: int) -> bool:
        cur = self.currentIndex()
        model = self.model()
        if model is None or not cur.isValid():
            return False
        r = cur.row() + delta
        while 0 <= r < model.rowCount() and self.isRowHidden(r):
            r += delta
        if not (0 <= r < model.rowCount()):
            return False
        nxt = model.index(r, cur.column())
        sel = self.selectionModel()
        if sel is not None:
            sel.setCurrentIndex(nxt, QItemSelectionModel.ClearAndSelect)
        self.scrollTo(nxt)
        return True

    def keyPressEvent(self, event):  # noqa: N802
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and self.state() != QAbstractItemView.EditingState:
            if self._step(-1 if event.modifiers() & Qt.ShiftModifier else 1):
                event.accept()
                return
        super().keyPressEvent(event)

    def closeEditor(self, editor, hint):  # noqa: N802
        up = bool(QApplication.keyboardModifiers() & Qt.ShiftModifier)
        super().closeEditor(editor, hint)
        if hint == QAbstractItemDelegate.SubmitModelCache:  # editor closed with Enter
            self._step(-1 if up else 1)


class FrozenFirstColumnTable(QWidget):
    # Optional hook for right-click on a data cell: hook(table, index, menu)
    # adds actions to `menu` (set by ShowExperimentScreen: "Change history…").
    cell_menu_hook = None

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

        self.top_left = _GridView(self)
        self.top_right = _GridView(self)
        self.bottom_left = _GridView(self)
        self.bottom_right = _GridView(self)

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
        # Reading bar (Settings -> "Reading bar"): the current cell in plain
        # words, e.g. "V2 · Ply 1 · Air Pressure (bar) = 3.50"
        self.read_bar = QLabel(self)
        self.read_bar.setTextFormat(Qt.RichText)
        self.read_bar.setWordWrap(True)
        self.read_bar.setVisible(False)
        lay.addWidget(self.read_bar, 2, 0, 1, 2)

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

        # ── Display settings (text size, contrast, crosshair) ────────────
        self._user_qss = ""
        self._fixed_data_w: Optional[int] = None
        self._base_font = QFont(self.bottom_right.font())
        self._base_row_h = self.bottom_right.verticalHeader().defaultSectionSize()
        # extra factor only for the preview in Settings: shows the chosen
        # program-wide "Text size" before the restart (ui/widgets/user_settings_dialog.py)
        self.preview_factor = 1.0
        for v in (self.top_left, self.top_right, self.bottom_left, self.bottom_right):
            v.viewport().installEventFilter(self)  # Ctrl+mouse wheel = zoom
        self.bottom_right.installEventFilter(self)  # right-click on a value
        for keys, step in ((QKeySequence.ZoomIn, 1), (QKeySequence("Ctrl+="), 1),
                           (QKeySequence.ZoomOut, -1)):
            sc = QShortcut(keys, self)
            sc.setContext(Qt.WidgetWithChildrenShortcut)
            sc.activated.connect(lambda s=step: display_prefs.zoom_step(s))
        sc0 = QShortcut(QKeySequence("Ctrl+0"), self)
        sc0.setContext(Qt.WidgetWithChildrenShortcut)
        sc0.activated.connect(lambda: display_prefs.update(scale=100))
        display_prefs.add_listener(self._apply_display)
        self._apply_display()

    # ---------- Öffentliche API ----------

    def setModel(self, model):
        """Alle vier Ansichten auf dasselbe Model setzen, Zeilen/Spalten passend ausblenden."""
        self._model = model
        self._n_hdr = int(getattr(model, "_n_hdr", 0) or 0)
        try:
            import weakref
            model._ffct_owner = weakref.ref(self)  # lets the model find its screen (recycle bin preview)
        except Exception:
            pass

        sel = QItemSelectionModel(model)
        for v in (self.top_left, self.top_right, self.bottom_left, self.bottom_right):
            v.setModel(model)
            v.setSelectionModel(sel)
        sel.currentChanged.connect(self._on_current_changed)
        model.dataChanged.connect(self._update_read_bar)
        self._pass_display_to_model()
        self._update_read_bar()

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
        self._user_qss = style or ""
        self._apply_qss()

    def _apply_qss(self):
        style = self._user_qss
        if display_prefs.current().get("contrast"):
            style = style + _CONTRAST_QSS
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
        self._fixed_data_w = fixed_data_column_width
        if fixed_data_column_width is not None:
            # scaled with the text size (Settings -> Display)
            fixed_data_column_width = int(fixed_data_column_width * self._zoom())
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
            elif obj is self.bottom_right and ev.type() == QEvent.ContextMenu:
                if self._cell_context_menu(ev):
                    return True
            elif ev.type() == QEvent.Wheel and ev.modifiers() & Qt.ControlModifier:
                dy = ev.angleDelta().y()
                if dy:
                    display_prefs.zoom_step(1 if dy > 0 else -1)
                return True
        except Exception:
            pass
        return super().eventFilter(obj, ev)

    def _cell_context_menu(self, ev) -> bool:
        hook = type(self).cell_menu_hook
        if hook is None or self._model is None:
            return False
        view = self.bottom_right
        index = view.indexAt(view.viewport().mapFrom(view, ev.pos()))
        if not index.isValid() or index.row() < self._n_hdr or index.column() < 1:
            return False
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        hook(self, index, menu)
        if not menu.actions():
            return False
        menu.exec(ev.globalPos())
        return True

    # ---------- Display settings ----------

    def _zoom(self) -> float:
        return display_prefs.scale() / 100.0 * float(self.preview_factor or 1.0)

    def _display_font(self) -> QFont:
        p = display_prefs.current()
        f = QFont(self._base_font)
        s = self._zoom()
        if f.pointSizeF() > 0:
            f.setPointSizeF(f.pointSizeF() * s)
        elif f.pixelSize() > 0:
            f.setPixelSize(max(6, int(f.pixelSize() * s)))
        if p["contrast"]:
            f.setBold(True)
        return f

    def _pass_display_to_model(self):
        """Models that know the display settings (PivotEditModel): bold
        fonts in the right size, contrast stripes, crosshair."""
        model = self._model
        if model is None or not hasattr(model, "set_display"):
            return
        p = display_prefs.current()
        cur = self.bottom_right.selectionModel().currentIndex() if self.bottom_right.selectionModel() else None
        cross = (cur.row(), cur.column()) if (p["crosshair"] and cur is not None and cur.isValid()) else None
        model.set_display(self._display_font(), bool(p["contrast"]), cross,
                          alert_marks=bool(p["alert_marks"]), cb_colours=bool(p["cb_colours"]))

    def _apply_display(self):
        f = self._display_font()
        row_h = max(self._base_row_h, int(self._base_row_h * self._zoom()))
        icon_px = max(12, int(row_h * 0.55))
        for v in (self.top_left, self.top_right, self.bottom_left, self.bottom_right):
            v.setFont(f)
            v.verticalHeader().setDefaultSectionSize(row_h)
            v.setIconSize(QSize(icon_px, icon_px))
        self._style_read_bar(f)
        self._apply_qss()
        self._pass_display_to_model()
        if self._model is not None:
            if self._fixed_data_w is not None:
                self.resizeColumnsToContents(fixed_data_column_width=self._fixed_data_w)
            else:
                self.top_left.resizeColumnToContents(0)
                self.bottom_left.resizeColumnToContents(0)
                self._update_left_width()
            self._update_top_height()

    def _style_read_bar(self, table_font: QFont):
        p = display_prefs.current()
        self.read_bar.setVisible(bool(p["readbar"]))
        # font size via stylesheet - the app stylesheet would override setFont()
        if table_font.pointSizeF() > 0:
            size = f"{table_font.pointSizeF() * 1.4:.1f}pt"
        else:
            size = f"{int(max(table_font.pixelSize(), 12) * 1.4)}px"
        if p["contrast"]:
            colours = "background:#000000;color:#FFFFFF;border:2px solid #000;"
        else:
            colours = "background:#F4F7FB;color:#1a1a1a;border:1px solid #9bbbe0;"
        self.read_bar.setStyleSheet(f"QLabel{{{colours}padding:8px 12px;font-size:{size};}}")
        self._update_read_bar()

    def read_bar_text(self, index) -> str:
        """Plain-word description of a cell: header values (trial, ply),
        parameter name, value - and "warning" for highlighted cells."""
        import html as _html
        model = self._model
        if model is None or index is None or not index.isValid():
            return "Click a value in the table."
        r, c = index.row(), index.column()
        parts = []
        if c > 0:
            for h in range(self._n_hdr):
                v = str(model.data(model.index(h, c), Qt.DisplayRole) or "").strip()
                if v and v not in parts:
                    parts.append(v)
        if r < self._n_hdr:
            return _html.escape(" · ".join(parts)) if parts else ""
        title = str(model.data(model.index(r, 0), Qt.DisplayRole) or "").strip()
        if title:
            parts.append(title)
        where = _html.escape(" · ".join(parts))
        if c == 0:
            return f"<b>{where}</b>"
        val = str(model.data(index, Qt.DisplayRole) or "").strip()
        val_html = f"<b>{_html.escape(val)}</b>" if val else "<i>(empty)</i>"
        alert = model.cell_alert(r, c) if hasattr(model, "cell_alert") else None
        warn = "  –  <b>! Warning</b>" if alert == "red" else ("  –  <b>! Check</b>" if alert else "")
        return f"{where} = {val_html}{warn}"

    def _update_read_bar(self, *_args):
        if not display_prefs.current().get("readbar"):
            return
        sel = self.bottom_right.selectionModel()
        cur = sel.currentIndex() if sel is not None else None
        self.read_bar.setText(self.read_bar_text(cur))

    def _on_current_changed(self, current, _previous):
        self._update_read_bar()
        model = self._model
        if model is None or not hasattr(model, "set_crosshair"):
            return
        if display_prefs.current().get("crosshair") and current.isValid():
            model.set_crosshair((current.row(), current.column()))
        else:
            model.set_crosshair(None)

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