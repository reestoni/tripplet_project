"""screen_process_playground.py - Process Playground (Sidebar Tools, Nutzerwunsch
2026-11-12): pick a DTY yarn + jet, type the start conditions (or take them
from a trial), move air pressure / overfeed / speed - the screen says what
happens to the lab values (points/m, CV, stabilities, tensions before / after
the jet): more, less or about the same, and how sure that is. Reverse: set
goals per lab value (one main goal) -> "Find settings" proposes settings that
reach them. Only from our own trials of exactly that yarn / jet combination,
never outside the measured range.

Logic and statistics: ui/dty_whatif.py (reads only). Wired like the Yarn
Count Converter: app_meta.open_process_playground /
sidebar_nav.trigger_process_playground, feature key "process_playground"
(db/feature_access.py). Show Experiment: right-click a DTY trial number ->
"Open in Process Playground…" -> open_trial(trial_id).
Help: ui/widgets/help_texts_process_playground.py.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QPushButton, QSlider, QSplitter, QTableWidget,
                               QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from ui import dty_whatif as w
from ui.pathutil import resource_path
from ui.widgets import sidebar_nav

ACCENT = "#1F7A3A"
CARD_QSS = "QFrame#Card{background:#FFFFFF;border:1px solid #DADFD8;border-radius:8px;}"
SMALL = "color:#5A6460;font-size:12px;border:none;background:transparent;"
NOTE_OK = "color:#8A938F;font-size:11px;border:none;"
NOTE_BAD = "color:#B0412E;font-size:11px;border:none;"
BTN = ("QPushButton{background:#FFFFFF;border:1px solid #C9D1C8;border-radius:5px;padding:5px 12px;}"
       "QPushButton:hover{background:#EEF5EF;}")
BTN_PRIMARY = ("QPushButton{background:#39A650;color:white;border:none;border-radius:5px;padding:6px 14px;"
               "font-weight:600;} QPushButton:hover{background:#2F8F44;} QPushButton:disabled{background:#B9C4BC;}")
TABLE_QSS = ("QTableWidget{border:1px solid #DADFD8;gridline-color:#E6EBE5;background:#FFFFFF;"
             "selection-background-color:#CFE8D4;selection-color:#1C2321;}"
             "QHeaderView::section{background:#EEF2ED;border:none;border-bottom:1px solid #DADFD8;"
             "padding:4px 6px;font-weight:600;}")

# statement colours: strength of the statement, not good / bad
_BG = {
    w.CLEAR: QColor("#CFE3F5"), w.PROBABLE: QColor("#E1EDF8"), w.TENDENCY: QColor("#EEF4FA"),
    w.SAME: QColor("#E8F3EA"), w.NO_CLEAR: QColor("#F4F6F3"),
}
_GREY = QColor("#8A938F")
_STRENGTH = {w.CLEAR: "strong (p < 0.01)", w.PROBABLE: "good (p < 0.05)", w.TENDENCY: "weak (p < 0.10)",
             w.SAME: "change smaller than the repeat scatter", w.NO_CLEAR: "neither clearly changed nor clearly equal"}
# goal column: (label, code)
GOAL_CHOICES = [("", ""), ("higher", w.UP), ("lower", w.DOWN), ("keep", w.KEEP)]
_STATUS_TXT = {w.MET: "met", w.NEUTRAL: "not proven", w.VIOLATED: "BROKEN", w.UNKNOWN: "can't tell"}
_STATUS_BG = {w.MET: QColor("#DCEFE0"), w.VIOLATED: QColor("#F6D5CF"), w.UNKNOWN: QColor("#F1F1EE")}
# start ranges for typing (wider than any data - the check says what was measured)
_START_RANGE = {"pressure": (0.0, 15.0), "of": (-20.0, 40.0), "speed": (0.0, 3000.0)}

# result table columns
C_LABEL, C_START, C_CHANGE, C_STMT, C_BASED, C_GOAL = range(6)


def _card(title: str, subtitle: str = ""):
    card = QFrame()
    card.setObjectName("Card")
    card.setStyleSheet(CARD_QSS)
    lay = QVBoxLayout(card)
    lay.setContentsMargins(16, 12, 16, 14)
    lay.setSpacing(8)
    t = QLabel(title)
    t.setStyleSheet("font-size:15px;font-weight:700;color:#1C2321;border:none;")
    lay.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setWordWrap(True)
        s.setStyleSheet(SMALL)
        lay.addWidget(s)
    return card, lay


def _fmt(v: Optional[float], dec: int) -> str:
    return "" if v is None else f"{v:.{dec}f}"


def _table(cols: List[str]) -> QTableWidget:
    t = QTableWidget(0, len(cols))
    t.setHorizontalHeaderLabels(cols)
    t.setStyleSheet(TABLE_QSS)
    t.verticalHeader().setVisible(False)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    return t


class _Loader(QObject):
    done = Signal(object, object)       # DataSet or None, error or None

    def run(self):
        try:
            self.done.emit(w.build_dataset(w.load_rows()), None)
        except Exception as e:          # shown with friendly_error in the screen
            self.done.emit(None, e)


class ProcessPlaygroundScreen(QWidget):
    def __init__(self, sidebar_callbacks: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None
        self._ds: Optional[w.DataSet] = None
        self._combo: Optional[w.Combination] = None
        self._settings: List[dict] = []
        self._start: Dict[str, float] = {}
        self._fits: dict = {}
        self._changes: Dict[str, w.Change] = {}
        self._suggestions: List[w.Suggestion] = []
        self._filling = False
        self._logged_key = None
        self._pending_trial = None
        self._thread: Optional[QThread] = None
        self._spins: Dict[str, QDoubleSpinBox] = {}
        self._sliders: Dict[str, QSlider] = {}
        self._start_spins: Dict[str, QDoubleSpinBox] = {}
        self._start_notes: Dict[str, QLabel] = {}
        self._start_lbls: Dict[str, QLabel] = {}
        self._why_lbls: Dict[str, QLabel] = {}
        self._goal_boxes: Dict[str, QComboBox] = {}
        self._canvas = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._sidebar, content = sidebar_nav.wrap_body_with_sidebar(root)
        page = QWidget()
        page.setObjectName("Page")
        page.setStyleSheet("QWidget#Page{background:#F4F6F3;}")
        content.addWidget(page)
        pv = QVBoxLayout(page)
        pv.setContentsMargins(20, 14, 20, 14)
        pv.setSpacing(10)

        # ── header ────────────────────────────────────────────────────
        head = QHBoxLayout()
        icon = QLabel()
        pm = QPixmap(resource_path("assets/images/process_playground_120.png"))
        if not pm.isNull():
            icon.setPixmap(pm.scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        head.addWidget(icon, 0, Qt.AlignVCenter)
        head.addSpacing(6)
        tbox = QVBoxLayout()
        tbox.setSpacing(0)
        k = QLabel("TOOLS · DTY")
        k.setStyleSheet(f"color:{ACCENT};font-size:11px;font-weight:700;letter-spacing:1px;")
        t = QLabel("Process Playground")
        t.setStyleSheet("font-size:22px;font-weight:700;color:#1C2321;")
        s = QLabel("What happens to the lab values if you change air pressure, overfeed or speed - and which "
                   "settings reach your goals? Answered from our own trials of exactly this yarn and jet.")
        s.setStyleSheet("color:#5A6460;font-size:12px;")
        for x in (k, t, s):
            tbox.addWidget(x)
        head.addLayout(tbox, 1)
        self.btn_reload = QPushButton("Reload")
        self.btn_reload.setToolTip("Load the latest trials from the database (F5)")
        self.btn_reload.setShortcut("F5")
        self.btn_reload.setStyleSheet(BTN)
        self.btn_reload.clicked.connect(self.reload)
        head.addWidget(self.btn_reload, 0, Qt.AlignVCenter)
        from ui.widgets.multilang_help import make_help_button
        head.addWidget(make_help_button("How does the Process Playground work?", self._open_help), 0, Qt.AlignVCenter)
        pv.addLayout(head)

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        pv.addWidget(split, 1)

        # ── left: yarn / jet ──────────────────────────────────────────
        left, ll = _card("1  Yarn and jet",
                         "Only combinations where air pressure, overfeed or speed were varied in our trials.")
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText("Search yarn or jet…")
        self.ed_search.setClearButtonEnabled(True)
        self.ed_search.textChanged.connect(self._filter_combos)
        ll.addWidget(self.ed_search)
        self.tbl_combos = _table(["Yarn", "Jet", "Trials", "Series", "Varied"])
        self.tbl_combos.setToolTip("Varied: P = air pressure, OF = overfeed, S = speed")
        hh = self.tbl_combos.horizontalHeader()
        hh.setSortIndicator(-1, Qt.AscendingOrder)   # keep the "most data first" order until a click
        self.tbl_combos.setSortingEnabled(True)
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.Interactive)
        self.tbl_combos.setColumnWidth(1, 110)
        for c in range(2, 5):
            hh.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.tbl_combos.itemSelectionChanged.connect(self._on_combo_selected)
        ll.addWidget(self.tbl_combos, 1)
        self.lbl_status = QLabel("Loading trials…")
        self.lbl_status.setStyleSheet(SMALL)
        ll.addWidget(self.lbl_status)
        left.setMinimumWidth(430)
        split.addWidget(left)

        # ── right ─────────────────────────────────────────────────────
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(10)
        split.addWidget(right)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([460, 940])

        top = QHBoxLayout()
        top.setSpacing(10)
        c2, l2 = _card("2  Start conditions", "Type your settings - or take them from a trial.")
        g2 = QGridLayout()
        g2.setHorizontalSpacing(8)
        g2.setVerticalSpacing(2)
        for i, (p, (label, _step, unit, sstep, dec)) in enumerate(w.PARAMS.items()):
            lab = QLabel(f"{label} [{unit}]")
            lab.setStyleSheet("border:none;font-weight:600;")
            g2.addWidget(lab, i * 2, 0)
            sp = QDoubleSpinBox()
            sp.setDecimals(dec)
            sp.setSingleStep(sstep)
            sp.setRange(*_START_RANGE[p])
            sp.setKeyboardTracking(False)
            sp.setMinimumWidth(90)
            sp.valueChanged.connect(self._on_start_typed)
            self._start_spins[p] = sp
            g2.addWidget(sp, i * 2, 1)
            note = QLabel("")
            note.setStyleSheet(NOTE_OK)
            self._start_notes[p] = note
            g2.addWidget(note, i * 2 + 1, 0, 1, 2)
        l2.addLayout(g2)
        self.cb_trial = QComboBox()
        self.cb_trial.setMaxVisibleItems(25)
        self.cb_trial.setMinimumWidth(240)
        self.cb_trial.setToolTip("Fills the start conditions with the settings of a trial we really ran")
        self.cb_trial.activated.connect(self._on_trial_picked)
        l2.addWidget(self.cb_trial)
        self.lbl_combo = QLabel("")
        self.lbl_combo.setWordWrap(True)
        self.lbl_combo.setStyleSheet(SMALL)
        l2.addWidget(self.lbl_combo)
        l2.addStretch(1)
        top.addWidget(c2, 2)

        c3, l3 = _card("3  Change", "Move the settings - only within the range we measured.")
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(4)
        for i, (p, (label, _step, unit, sstep, dec)) in enumerate(w.PARAMS.items()):
            lab = QLabel(f"{label} [{unit}]")
            lab.setStyleSheet("border:none;font-weight:600;")
            grid.addWidget(lab, i * 2, 0)
            st = QLabel("")
            st.setStyleSheet(SMALL)
            self._start_lbls[p] = st
            grid.addWidget(st, i * 2, 1)
            sl = QSlider(Qt.Horizontal)
            sl.valueChanged.connect(lambda v, p=p: self._on_slider(p, v))
            self._sliders[p] = sl
            grid.addWidget(sl, i * 2, 2)
            sp = QDoubleSpinBox()
            sp.setDecimals(dec)
            sp.setSingleStep(sstep)
            sp.setKeyboardTracking(False)
            sp.setMinimumWidth(90)
            sp.valueChanged.connect(lambda v, p=p: self._on_spin(p, v))
            self._spins[p] = sp
            grid.addWidget(sp, i * 2, 3)
            why = QLabel("")
            why.setStyleSheet(NOTE_OK)
            self._why_lbls[p] = why
            grid.addWidget(why, i * 2 + 1, 2, 1, 2)
        grid.setColumnStretch(2, 1)
        l3.addLayout(grid)
        row = QHBoxLayout()
        self.lbl_warn = QLabel("")
        self.lbl_warn.setWordWrap(True)
        self.lbl_warn.setStyleSheet("color:#8A5A00;font-size:12px;border:none;")
        row.addWidget(self.lbl_warn, 1)
        self.btn_reset = QPushButton("Back to start")
        self.btn_reset.setStyleSheet(BTN)
        self.btn_reset.clicked.connect(self._reset)
        row.addWidget(self.btn_reset)
        l3.addLayout(row)
        top.addWidget(c3, 3)
        rv.addLayout(top)

        c4, l4 = _card("4  What happens")
        frow = QHBoxLayout()
        lb = QLabel("Find settings - main goal:")
        lb.setStyleSheet("border:none;font-weight:600;")
        frow.addWidget(lb)
        self.cb_main = QComboBox()
        for tk, (label, *_r) in w.TARGETS.items():
            self.cb_main.addItem(label, tk)
        self.cb_main.setCurrentIndex(list(w.TARGETS).index("stab10"))
        frow.addWidget(self.cb_main)
        self.cb_main_dir = QComboBox()
        self.cb_main_dir.addItem("higher", w.UP)
        self.cb_main_dir.addItem("lower", w.DOWN)
        frow.addWidget(self.cb_main_dir)
        hint = QLabel("other goals: column Goal")
        hint.setStyleSheet(SMALL)
        frow.addWidget(hint)
        frow.addStretch(1)
        self.btn_find = QPushButton("Find settings")
        self.btn_find.setStyleSheet(BTN_PRIMARY)
        self.btn_find.setToolTip("Search all settings we measured around for the main goal, keeping the other goals")
        self.btn_find.clicked.connect(self._find)
        frow.addWidget(self.btn_find)
        l4.addLayout(frow)
        self.tbl_res = _table(["Lab value", "At start (est.)", "Change (95 % range)", "Statement", "Based on", "Goal"])
        rh = self.tbl_res.horizontalHeader()
        for c in range(6):
            rh.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        rh.setSectionResizeMode(C_BASED, QHeaderView.Stretch)
        self.tbl_res.horizontalHeaderItem(C_START).setToolTip(
            "Estimated from all series of this yarn and jet - the statements do not depend on it")
        self.tbl_res.itemSelectionChanged.connect(self._draw_chart)
        self.tbl_res.setRowCount(len(w.TARGETS))
        for i, tk in enumerate(w.TARGETS):
            cb = QComboBox()
            for label, code in GOAL_CHOICES:
                cb.addItem(label, code)
            cb.setToolTip("Goal for Find settings: higher, lower or keep about the same")
            self._goal_boxes[tk] = cb
            self.tbl_res.setCellWidget(i, C_GOAL, cb)
        self.tbl_res.verticalHeader().setDefaultSectionSize(28)
        self.tbl_res.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # all 8 rows always visible - the tabs below take the rest
        self.tbl_res.setFixedHeight(self.tbl_res.horizontalHeader().sizeHint().height() + 28 * len(w.TARGETS) + 4)
        l4.addWidget(self.tbl_res)
        rv.addWidget(c4)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane{border:1px solid #DADFD8;border-radius:6px;background:#FFFFFF;}"
                                "QTabBar::tab{padding:6px 14px;}")
        chart_page = QWidget()
        cl = QVBoxLayout(chart_page)
        cl.setContentsMargins(12, 8, 12, 8)
        crow = QHBoxLayout()
        lb = QLabel("Show against:")
        crow.addWidget(lb)
        self.cb_chart_param = QComboBox()
        for p, (label, *_r) in w.PARAMS.items():
            self.cb_chart_param.addItem(label, p)
        self.cb_chart_param.currentIndexChanged.connect(self._draw_chart)
        crow.addWidget(self.cb_chart_param)
        self.lbl_chart_hint = QLabel("Click a lab value in the table above.")
        self.lbl_chart_hint.setStyleSheet(SMALL)
        self.lbl_chart_hint.setWordWrap(True)
        crow.addWidget(self.lbl_chart_hint, 1)
        cl.addLayout(crow)
        self._chart_box = QVBoxLayout()
        cl.addLayout(self._chart_box, 1)
        self.tabs.addTab(chart_page, "Where the statement comes from")

        sug_page = QWidget()
        sl_ = QVBoxLayout(sug_page)
        sl_.setContentsMargins(12, 8, 12, 8)
        self.lbl_sug = QLabel("Choose a main goal and click Find settings.")
        self.lbl_sug.setWordWrap(True)
        self.lbl_sug.setStyleSheet(SMALL)
        sl_.addWidget(self.lbl_sug)
        self.tbl_sug = _table([])
        self.tbl_sug.itemSelectionChanged.connect(self._on_suggestion_picked)
        sl_.addWidget(self.tbl_sug, 1)
        self.tabs.addTab(sug_page, "Suggestions")
        rv.addWidget(self.tabs, 1)

        self._set_enabled(False)

    # ── loading ───────────────────────────────────────────────────────
    def reload(self) -> None:
        if self._thread is not None:
            return
        self.lbl_status.setText("Loading trials…")
        self.btn_reload.setEnabled(False)
        self._thread = QThread(self)
        self._loader = _Loader()
        self._loader.moveToThread(self._thread)
        self._thread.started.connect(self._loader.run)
        self._loader.done.connect(self._on_loaded)
        self._thread.start()

    def _on_loaded(self, ds, err) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
        self.btn_reload.setEnabled(True)
        if err is not None or ds is None:
            self.lbl_status.setText("Could not load the trials.")
            from ui.widgets.friendly_error import show_error
            show_error(self, "Process Playground", "The trials could not be loaded.", err)
            return
        keep = self._combo.key if self._combo else None
        keep_start = dict(self._start)
        self._ds = ds
        self._fill_combos(keep)
        if self._pending_trial is not None:
            tid, self._pending_trial = self._pending_trial, None
            self.open_trial(tid)
        elif keep is not None and keep_start and self._combo is not None:
            self._set_start(keep_start)

    def _fill_combos(self, keep=None) -> None:
        tbl = self.tbl_combos
        tbl.setSortingEnabled(False)
        tbl.blockSignals(True)
        tbl.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        combos = sorted(self._ds.combos.values(), key=lambda c: (-c.n_lab_settings, -c.n_settings, c.yarn_name))
        tbl.setRowCount(len(combos))
        short = {"pressure": "P", "of": "OF", "speed": "S"}
        sel_row = None
        for i, c in enumerate(combos):
            vals = [c.yarn_name, c.jet_name, c.n_trials, c.n_series, " ".join(short[p] for p in c.varied)]
            for j, v in enumerate(vals):
                it = QTableWidgetItem()
                if isinstance(v, int):
                    it.setData(Qt.DisplayRole, v)
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                else:
                    it.setText(str(v))
                if j == 0:
                    it.setData(Qt.UserRole, c.key)
                    it.setToolTip(f"{c.yarn_name}\n{c.n_settings} different settings in {c.n_series} series")
                tbl.setItem(i, j, it)
            if keep is not None and c.key == keep:
                sel_row = i
        tbl.blockSignals(False)
        tbl.setSortingEnabled(True)
        self.lbl_status.setText(f"{len(combos)} yarn / jet combinations from {len(self._ds.rows):,} DTY trials"
                                .replace(",", "'"))
        self._filter_combos(self.ed_search.text())
        if sel_row is not None:
            tbl.selectRow(sel_row)
        elif self._combo is not None:
            self._combo = None
            self._set_enabled(False)

    def _filter_combos(self, text: str) -> None:
        words = (text or "").lower().split()
        for r in range(self.tbl_combos.rowCount()):
            hay = " ".join((self.tbl_combos.item(r, c).text() if self.tbl_combos.item(r, c) else "")
                           for c in (0, 1)).lower()
            self.tbl_combos.setRowHidden(r, not all(wd in hay for wd in words))

    # ── opening from Show Experiment ──────────────────────────────────
    def open_trial(self, trial_id) -> bool:
        """Select the yarn / jet of a trial and use its settings as start.
        Before the data is loaded the request is kept and done afterwards.
        Returns False if the trial is not usable here."""
        if self._ds is None:
            self._pending_trial = trial_id
            if self._thread is None:
                self.reload()
            return True
        row = next((r for r in self._ds.rows if r.get("trial_id") == trial_id), None)
        key = (row.get("yarn_key"), row.get("jet_id")) if row else None
        if row is None or key not in self._ds.combos:
            self.lbl_status.setText("This trial has no yarn / jet combination with varied settings and lab values.")
            return False
        self.ed_search.clear()
        for r in range(self.tbl_combos.rowCount()):
            it = self.tbl_combos.item(r, 0)
            if it is not None and it.data(Qt.UserRole) == key:
                self.tbl_combos.selectRow(r)
                self.tbl_combos.scrollToItem(it, QAbstractItemView.PositionAtCenter)
                break
        self._set_start({p: row.get(p) for p in w.PARAMS})
        return True

    # ── selection ─────────────────────────────────────────────────────
    def _on_combo_selected(self) -> None:
        items = self.tbl_combos.selectedItems()
        if not items or self._ds is None:
            return
        it = self.tbl_combos.item(items[0].row(), 0)
        c = self._ds.combos.get(it.data(Qt.UserRole) if it else None)
        if c is None or c is self._combo:
            return
        self._combo = c
        self._fits = {}
        self._suggestions = []
        self._show_suggestions("Choose a main goal and click Find settings.")
        self._settings = w.settings_of(c.rows)
        self.lbl_combo.setText(f"{c.yarn_name}  ·  {c.jet_name}\n{c.n_trials} trials, "
                               f"{c.n_settings} settings, {c.n_series} series")
        self.cb_trial.blockSignals(True)
        self.cb_trial.clear()
        self.cb_trial.addItem("Take from a trial…", None)
        best, best_n = None, -1
        for i, s in enumerate(self._settings):
            parts = [("OF " if p == "of" else "") + f"{_fmt(s[p], w.PARAMS[p][4]) or '-'} {w.PARAMS[p][2]}"
                     for p in w.PARAMS]
            nos = ", ".join(f"V{n}" for n in sorted(x for x in s["trials"] if x is not None))
            n_tr = len(s["trials"])
            self.cb_trial.addItem(" · ".join(parts) + f"  ({n_tr} trial{'s' if n_tr != 1 else ''})  -  "
                                  f"{s['series_name']}", i)
            self.cb_trial.setItemData(i + 1, f"{s['series_name']}" + chr(10) + f"Trials {nos}", Qt.ToolTipRole)
            if n_tr > best_n and all(s[p] is not None for p in w.PARAMS):
                best, best_n = i, n_tr
        self.cb_trial.setCurrentIndex(0)
        self.cb_trial.blockSignals(False)
        self._set_enabled(True)
        self._setup_sliders()
        if best is not None:
            self._set_start({p: self._settings[best][p] for p in w.PARAMS})

    def _setup_sliders(self) -> None:
        rows = self._combo.rows
        self._filling = True
        for p, (label, _step, unit, sstep, dec) in w.PARAMS.items():
            vals = [r[p] for r in rows if r.get(p) is not None]
            lo, hi = (min(vals), max(vals)) if vals else (0.0, 0.0)
            sp, sl = self._spins[p], self._sliders[p]
            sp.setRange(lo, hi)
            sl.setRange(0, max(1, int(round((hi - lo) / sstep))))
            on = p in self._combo.varied
            sp.setEnabled(on)
            sl.setEnabled(on)
            self._why_lbls[p].setText(f"measured {_fmt(lo, dec)} to {_fmt(hi, dec)} {unit}" if on else
                                      "not varied with this yarn and jet - no statement possible")
        self._filling = False

    def _on_trial_picked(self, index: int) -> None:
        i = self.cb_trial.itemData(index)
        if i is None or i >= len(self._settings):
            return
        self._set_start({p: self._settings[i][p] for p in w.PARAMS})

    def _set_start(self, start: Dict[str, Optional[float]]) -> None:
        self._filling = True
        for p, sp in self._start_spins.items():
            v = start.get(p)
            sp.setValue(v if v is not None else sp.minimum())
        self._filling = False
        self._on_start_typed()

    def _on_start_typed(self, *_a) -> None:
        if self._filling or self._combo is None:
            return
        self._start = {p: round(self._start_spins[p].value(), 6) for p in w.PARAMS}
        notes = w.start_notes(self._combo.rows, self._start)
        for p, (ok, txt) in notes.items():
            self._start_notes[p].setText(txt if ok else "not measured here - " + txt)
            self._start_notes[p].setStyleSheet(NOTE_OK if ok else NOTE_BAD)
            self._start_lbls[p].setText(f"start {_fmt(self._start[p], w.PARAMS[p][4])}")
        # a typed start no longer matches the trial in the list
        if self.cb_trial.currentIndex() > 0:
            i = self.cb_trial.currentData()
            s = self._settings[i] if i is not None and i < len(self._settings) else None
            if s is None or any(s[p] is None or abs(s[p] - self._start[p]) > 1e-6 for p in w.PARAMS):
                self.cb_trial.setCurrentIndex(0)
        self._move_sliders(self._start)

    def _move_sliders(self, values: Dict[str, float]) -> None:
        self._filling = True
        for p, sp in self._spins.items():
            v = min(max(values[p], sp.minimum()), sp.maximum())
            sp.setValue(v)
            self._sliders[p].setValue(int(round((v - sp.minimum()) / w.PARAMS[p][3])))
        self._filling = False
        self._recompute()

    def _reset(self) -> None:
        self._move_sliders(self._start)

    def _on_slider(self, p: str, v: int) -> None:
        if self._filling:
            return
        sp = self._spins[p]
        self._filling = True
        sp.setValue(sp.minimum() + v * w.PARAMS[p][3])
        self._filling = False
        self._recompute()

    def _on_spin(self, p: str, v: float) -> None:
        if self._filling:
            return
        sp, sl = self._spins[p], self._sliders[p]
        self._filling = True
        sl.setValue(int(round((v - sp.minimum()) / w.PARAMS[p][3])))
        self._filling = False
        self._recompute()

    def _new(self) -> Dict[str, float]:
        """Slider values; a parameter whose slider never moved away from the
        clamped start keeps the typed start value."""
        new = dict(self._start)
        for p in w.PARAMS:
            sp = self._spins[p]
            if not sp.isEnabled():
                continue
            v = round(sp.value(), 6)
            clamped = min(max(self._start[p], sp.minimum()), sp.maximum())
            if abs(v - clamped) > 1e-9:
                new[p] = v
        return new

    # ── results ───────────────────────────────────────────────────────
    def _recompute(self) -> None:
        if self._combo is None or self._ds is None or not self._start:
            return
        new = self._new()
        changed = [p for p in w.PARAMS if abs(new[p] - self._start[p]) > 1e-9]
        rows = self._combo.rows
        self._changes = {t: w.change(rows, t, self._ds.margins[t], self._start, new, self._fits) for t in w.TARGETS}
        warn = []
        if any(not ok for ok, _t in w.start_notes(rows, self._start).values()):
            warn.append("The start conditions are outside what we ran with this yarn and jet - "
                        "see the red notes under 2.")
        elif w.never_run(rows, self._start):
            warn.append("These start conditions were never run together - the statements combine what we "
                        "saw when the values were changed separately.")
        if changed and w.never_run(rows, new):
            warn.append("The new settings were never run together - the statement combines what we saw "
                        "when the values were changed separately.")
        if not changed and not warn:
            warn.append("Move a setting to see what happens.")
        self.lbl_warn.setText("  ".join(warn))
        if changed and self._logged_key != self._combo.key:
            self._log("change")
        self._fill_results(changed)
        if changed and self.cb_chart_param.currentData() not in changed:
            self.cb_chart_param.setCurrentIndex(list(w.PARAMS).index(changed[0]))
        self._draw_chart()

    def _log(self, what: str) -> None:
        self._logged_key = self._combo.key
        try:
            from db.usage_log import log_usage_event
            log_usage_event("feature", "process_playground",
                            f"{what}: {self._combo.yarn_name} / {self._combo.jet_name}")
        except Exception:
            pass

    @staticmethod
    def _based_on(ch: w.Change) -> str:
        based = []
        if ch.verdict in (w.CLEAR, w.PROBABLE, w.TENDENCY, w.SAME, w.NO_CLEAR):
            for p, (agree, n) in ch.series.items():
                if n:
                    based.append(f"{w.PARAMS[p][0]}: {agree} of {n} series same direction"
                                 if ch.verdict in w.SIGNIFICANT else f"{w.PARAMS[p][0]}: {n} series")
            if ch.one_series:
                based.append("only 1 series - check it")
            if ch.curved:
                based.append("not linear - depends on the start")
        elif ch.reason:
            based.append(ch.reason)
        return ";  ".join(based)

    @staticmethod
    def _statement(ch: w.Change) -> str:
        if ch.verdict == w.NO_CHANGE:
            return ""
        arrow = {1: "↑ ", -1: "↓ "}.get(ch.direction, "≈ " if ch.verdict == w.SAME else "")
        return arrow + w.verdict_text(ch)

    @staticmethod
    def _change_txt(ch: w.Change, dec: int) -> str:
        if ch.delta is None or ch.ci is None or ch.verdict in (w.OUTSIDE, w.NOT_VARIED):
            return ""
        lo, hi = ch.ci
        return f"{ch.delta:+.{dec}f}  ({lo:+.{dec}f} to {hi:+.{dec}f})"

    def _fill_results(self, changed: List[str]) -> None:
        tbl = self.tbl_res
        for i, (t, (label, unit, dec)) in enumerate(w.TARGETS.items()):
            ch = self._changes[t]
            start_txt = f"{_fmt(ch.start_value, dec)} {unit}" if ch.start_value is not None else ""
            vals = [label, start_txt, self._change_txt(ch, dec), self._statement(ch), self._based_on(ch)]
            for j, v in enumerate(vals):
                it = tbl.item(i, j) or QTableWidgetItem()
                it.setText(v)
                bg = _BG.get(ch.verdict)
                it.setBackground(bg if bg is not None else QColor("#FFFFFF"))
                it.setForeground(_GREY if ch.verdict in (w.UNCLEAR, w.NOT_VARIED, w.NO_DATA, w.OUTSIDE)
                                 and j >= C_CHANGE else QColor("#1C2321"))
                f = QFont()
                f.setBold(j == C_STMT and ch.verdict in w.SIGNIFICANT)
                it.setFont(f)
                if j in (C_START, C_CHANGE):
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if j == C_STMT:
                    it.setToolTip(_STRENGTH.get(ch.verdict, ch.reason or ""))
                if j == C_BASED:
                    it.setToolTip(v.replace(";  ", chr(10)))
                tbl.setItem(i, j, it)
        if not tbl.selectedItems():
            tbl.selectRow(0)

    # ── reverse: find settings ────────────────────────────────────────
    def _goals(self) -> Dict[str, str]:
        goals = {t: cb.currentData() for t, cb in self._goal_boxes.items() if cb.currentData()}
        goals[self.cb_main.currentData()] = self.cb_main_dir.currentData()
        return goals

    def _find(self) -> None:
        if self._combo is None or self._ds is None:
            return
        main = self.cb_main.currentData()
        from PySide6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            sugg, msg = w.suggest(self._combo.rows, self._ds.margins, self._start, self._goals(), main,
                                  fit_cache=self._fits)
        finally:
            QApplication.restoreOverrideCursor()
        self._suggestions = sugg
        self._log("find")
        self._show_suggestions(msg)
        self.tabs.setCurrentIndex(1)

    def _show_suggestions(self, msg: str) -> None:
        tbl = self.tbl_sug
        tbl.blockSignals(True)
        sugg = self._suggestions
        goals = self._goals() if sugg else {}
        main = self.cb_main.currentData()
        targets = [main] + [t for t in w.TARGETS if t in goals and t != main]
        cols = ["#"] + [f"{w.PARAMS[p][0]} [{w.PARAMS[p][2]}]" for p in w.PARAMS] + \
               [w.TARGETS[t][0] + (" (main)" if t == main else "") for t in targets]
        tbl.clear()
        tbl.setColumnCount(len(cols))
        tbl.setHorizontalHeaderLabels(cols)
        tbl.setRowCount(len(sugg))
        for i, sg in enumerate(sugg):
            cells = [str(i + 1)]
            for p in w.PARAMS:
                dec = w.PARAMS[p][4]
                d = sg.new[p] - self._start[p]
                cells.append(f"{sg.new[p]:.{dec}f}" + (f"  ({d:+.{dec}f})" if abs(d) > 1e-9 else ""))
            for j, txt in enumerate(cells):
                it = QTableWidgetItem(txt)
                if j > 0 and "(" in txt:
                    f = QFont()
                    f.setBold(True)
                    it.setFont(f)
                tbl.setItem(i, j, it)
            for k, t in enumerate(targets):
                ch = sg.changes[t]
                stat = sg.status.get(t, "")
                txt = self._statement(ch) or "-"
                if ch.delta is not None and ch.verdict in w.SIGNIFICANT + (w.SAME, w.NO_CLEAR):
                    txt += f" ({ch.delta:+.{w.TARGETS[t][2]}f})"
                if t != main and stat:
                    txt += f"  [{_STATUS_TXT[stat]}]"
                it = QTableWidgetItem(txt)
                it.setToolTip((self._change_txt(ch, w.TARGETS[t][2]) + chr(10) + self._based_on(ch)).strip())
                bg = _BG.get(ch.verdict) if t == main else _STATUS_BG.get(stat)
                if bg is not None:
                    it.setBackground(bg)
                tbl.setItem(i, 1 + len(w.PARAMS) + k, it)
        hh = tbl.horizontalHeader()
        for c in range(len(cols)):
            hh.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        tbl.blockSignals(False)
        if sugg:
            txt = ("Click a suggestion to move the sliders there. Bold = changed. Goals: met = shown with a "
                   "statement, not proven = no clear change, can't tell = too few trials, BROKEN = goes the "
                   "wrong way.")
            self.lbl_sug.setText((msg + "  " if msg else "") + txt)
        else:
            self.lbl_sug.setText(msg or "Choose a main goal and click Find settings.")

    def _on_suggestion_picked(self) -> None:
        items = self.tbl_sug.selectedItems()
        if not items:
            return
        r = items[0].row()
        if 0 <= r < len(self._suggestions):
            self._move_sliders(self._suggestions[r].new)

    # ── chart ─────────────────────────────────────────────────────────
    def _ensure_canvas(self):
        if self._canvas is None:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
            self._fig = Figure(figsize=(6, 2.6), dpi=100, facecolor="#FFFFFF")
            self._canvas = FigureCanvasQTAgg(self._fig)
            self._canvas.setMinimumHeight(200)
            self._chart_box.addWidget(self._canvas)
        return self._fig

    def _draw_chart(self, *_a) -> None:
        if self._combo is None or not self._changes:
            return
        rows = self.tbl_res.selectedItems()
        if not rows:
            return
        t = list(w.TARGETS)[rows[0].row()]
        p = self.cb_chart_param.currentData()
        if t not in self._fits:
            w.change(self._combo.rows, t, self._ds.margins[t], self._start, self._start, self._fits)
        fit, conds, _usable = self._fits[t]
        data = w.chart_data(fit, conds, p, self._start)
        fig = self._ensure_canvas()
        fig.clear()
        ax = fig.add_subplot(111)
        label, unit, _dec = w.TARGETS[t]
        plabel, _s, punit, *_r = w.PARAMS[p]
        if not data:
            ax.text(0.5, 0.5, "not measured for this yarn and jet", ha="center", va="center",
                    color="#8A938F", transform=ax.transAxes)
            ax.set_axis_off()
        else:
            series = sorted(set(data["series"]), key=str)
            cmap = ["#1F7A3A", "#2386C8", "#E69F00", "#8E44AD", "#C0392B", "#16A085", "#7F8C8D", "#D35400"]
            colours = [cmap[series.index(s) % len(cmap)] for s in data["series"]]
            ax.scatter(data["x"], data["y"], s=22, c=colours, alpha=0.8, edgecolors="none", zorder=3)
            if data["curve"]:
                gx, gy, lo, hi = data["curve"]
                ax.fill_between(gx, lo, hi, color="#2386C8", alpha=0.12, linewidth=0)
                ax.plot(gx, gy, color="#2386C8", linewidth=1.8)
                self.lbl_chart_hint.setText("Points: our trials, corrected for series and for the other settings "
                                            "(colour = series). Line: what the statement uses, band = 95 % range.")
            else:
                self.lbl_chart_hint.setText(f"{plabel} was not varied for this value - raw points only.")
            s0 = self._start.get(p)
            if s0 is not None:
                ax.axvline(s0, color="#5A6460", linestyle="--", linewidth=1)
            nv = self._new().get(p)
            if nv is not None and s0 is not None and abs(nv - s0) > 1e-9:
                ax.axvline(nv, color="#1F7A3A", linewidth=1.6)
            ax.set_xlabel(f"{plabel} [{punit}]   (dashed = start, green = new)", fontsize=9)
            ax.set_ylabel(f"{label} [{unit}]", fontsize=9)
            ax.tick_params(labelsize=8)
            ax.grid(True, color="#E6EBE5", linewidth=0.8)
            for sp in ("top", "right"):
                ax.spines[sp].set_visible(False)
        fig.tight_layout()
        self._canvas.draw_idle()

    # ── misc ──────────────────────────────────────────────────────────
    def _set_enabled(self, on: bool) -> None:
        for wd in [self.cb_trial, self.btn_reset, self.tbl_res, self.cb_chart_param, self.btn_find,
                   self.cb_main, self.cb_main_dir] + list(self._start_spins.values()) + \
                list(self._spins.values()) + list(self._sliders.values()):
            wd.setEnabled(on)

    def _open_help(self) -> None:
        from ui.widgets.help_texts_process_playground import TEXTS
        from ui.widgets.multilang_help import show_help
        show_help(TEXTS, self)

    def showEvent(self, event):  # noqa: N802
        try:
            import app_meta
            level = int((app_meta.current_user or {}).get("access_level") or 0)
            sidebar_nav.refresh_lazy_sidebar(self, level)
        except Exception:
            pass
        super().showEvent(event)
        if self._ds is None and self._thread is None:
            self.reload()
