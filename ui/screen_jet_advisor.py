"""screen_jet_advisor.py - Jet Advisor (Sidebar Tools, Nutzerwunsch 2026-11-15):
give targets (points/m, CV, stability) and the yarn (an existing one or
material / final titer / filaments) - the screen ranks the jets with the
recommended air pressure / overfeed / speed. Filters: jet type (e.g. only
Standard), maker, group, titer range of the jet, limits for the settings.

Logic: ui/jet_advisor.py (Qt-free, the web page /tools/jet-advisor uses it
too; fits from ui/dty_whatif.py, reads only). Wired like the Process
Playground: app_meta.open_jet_advisor / sidebar_nav.trigger_jet_advisor,
feature key "jet_advisor" (db/feature_access.py). Help: ui/widgets/help_texts_jet_advisor.py
(also the web help) + assets/images/help_jet_advisor.svg.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QCompleter, QFrame,
                               QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPushButton, QRadioButton, QScrollArea, QSizePolicy, QSplitter, QStackedWidget,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ui import dty_whatif as w
from ui import jet_advisor as ja
from ui.pathutil import resource_path
from ui.widgets import sidebar_nav

ACCENT = "#1F7A3A"
CARD_QSS = "QFrame#Card{background:#FFFFFF;border:1px solid #DADFD8;border-radius:8px;}"
SMALL = "color:#5A6460;font-size:12px;border:none;background:transparent;"
BTN = ("QPushButton{background:#FFFFFF;border:1px solid #C9D1C8;border-radius:5px;padding:5px 12px;}"
       "QPushButton:hover{background:#EEF5EF;}")
BTN_PRIMARY = ("QPushButton{background:#39A650;color:white;border:none;border-radius:5px;padding:7px 16px;"
               "font-weight:600;} QPushButton:hover{background:#2F8F44;} QPushButton:disabled{background:#B9C4BC;}")
TABLE_QSS = ("QTableWidget{border:1px solid #DADFD8;gridline-color:#E6EBE5;background:#FFFFFF;"
             "selection-background-color:#CFE8D4;selection-color:#1C2321;}"
             "QHeaderView::section{background:#EEF2ED;border:none;border-bottom:1px solid #DADFD8;"
             "padding:4px 6px;font-weight:600;}")

TARGET_SHORT = {"fpm": "Points/m", "fpm_cv": "CV", "stab03": "Stab. 0.3", "stab06": "Stab. 0.6",
                "stab10": "Stab. 1.0", "stab13": "Stab. 1.3"}
PARAM_SHORT = {"pressure": "Pressure", "of": "OF", "speed": "Speed"}
PARAM_DEC = {"pressure": 1, "of": 1, "speed": 0}
REACH = [("very close (±10 %)", 0.3), ("close (±17 %)", 0.6), ("normal (±30 %)", 1.0), ("wide (±50 %)", 1.5)]
_GOOD, _BAD = QColor("#1F7A3A"), QColor("#B03A2E")



def _card(title: str, subtitle: str = ""):
    card = QFrame()
    card.setObjectName("Card")
    card.setStyleSheet(CARD_QSS)
    lay = QVBoxLayout(card)
    lay.setContentsMargins(14, 10, 14, 12)
    lay.setSpacing(6)
    t = QLabel(title)
    t.setStyleSheet("font-size:15px;font-weight:700;color:#1C2321;border:none;")
    lay.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setWordWrap(True)
        s.setStyleSheet(SMALL)
        lay.addWidget(s)
    return card, lay


def _num(text: str) -> Optional[float]:
    try:
        return float(str(text).strip().replace(",", "."))
    except ValueError:
        return None


def _fmt(v: Optional[float], dec: int = 1) -> str:
    return "–" if v is None else f"{v:.{dec}f}"


def _small_edit(width: int = 70) -> QLineEdit:
    e = QLineEdit()
    e.setFixedWidth(width)
    e.setClearButtonEnabled(False)
    return e


def _check_list(items: List[dict]) -> QListWidget:
    lw = QListWidget()
    lw.setStyleSheet("QListWidget{border:1px solid #DADFD8;border-radius:5px;background:#FFFFFF;}")
    for it in items:
        li = QListWidgetItem(it["name"] or "(none)")
        li.setData(Qt.UserRole, it["id"])
        li.setFlags(li.flags() | Qt.ItemIsUserCheckable)
        li.setCheckState(Qt.Unchecked)
        lw.addItem(li)
    lw.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    lw.setTextElideMode(Qt.ElideRight)
    lw.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
    lw.setFixedHeight(min(110, 22 * max(1, len(items)) + 6))
    return lw


def _checked(lw: QListWidget) -> Optional[List[int]]:
    ids = [lw.item(i).data(Qt.UserRole) for i in range(lw.count()) if lw.item(i).checkState() == Qt.Checked]
    return ids or None


class _Loader(QObject):
    done = Signal(object, object)       # Advisor or None, error or None

    def __init__(self, adv: Optional[ja.Advisor]):
        super().__init__()
        self._adv = adv

    def run(self):
        try:
            if self._adv is None:
                self.done.emit(ja.Advisor(), None)
            else:
                self._adv.reload()
                self.done.emit(self._adv, None)
        except Exception as e:          # shown with friendly_error in the screen
            self.done.emit(None, e)


class JetAdvisorScreen(QWidget):
    def __init__(self, sidebar_callbacks: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None
        self._adv: Optional[ja.Advisor] = None
        self._thread: Optional[QThread] = None
        self._results: List[ja.JetResult] = []
        self._targets_shown: List[str] = []
        self._target_edits: Dict[str, tuple] = {}
        self._limit_edits: Dict[str, tuple] = {}
        self._logged = False
        self._build()

    # ── UI ────────────────────────────────────────────────────────────
    def _build(self) -> None:
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

        head = QHBoxLayout()
        icon = QLabel()
        pm = QPixmap(resource_path("assets/images/jet_advisor_120.png"))
        if not pm.isNull():
            icon.setPixmap(pm.scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        head.addWidget(icon, 0, Qt.AlignVCenter)
        head.addSpacing(6)
        tbox = QVBoxLayout()
        tbox.setSpacing(0)
        k = QLabel("TOOLS · DTY")
        k.setStyleSheet(f"color:{ACCENT};font-size:11px;font-weight:700;letter-spacing:1px;")
        t = QLabel("Jet Advisor")
        t.setStyleSheet("font-size:22px;font-weight:700;color:#1C2321;")
        s = QLabel("Give your targets and the yarn - which jets reach them, with which air pressure, overfeed and "
                   "speed? Answered from our own trials of this yarn or similar ones.")
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
        head.addWidget(make_help_button("How does the Jet Advisor work?", self._open_help), 0, Qt.AlignVCenter)
        pv.addLayout(head)

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        pv.addWidget(split, 1)

        # ── left: form ────────────────────────────────────────────────
        form = QWidget()
        fv = QVBoxLayout(form)
        fv.setContentsMargins(0, 0, 6, 0)
        fv.setSpacing(10)

        c1, l1 = _card("1  Yarn")
        rb = QHBoxLayout()
        self.rb_db = QRadioButton("Existing yarn")
        self.rb_own = QRadioButton("Own values")
        self.rb_db.setChecked(True)
        grp = QButtonGroup(self)
        grp.addButton(self.rb_db)
        grp.addButton(self.rb_own)
        rb.addWidget(self.rb_db)
        rb.addWidget(self.rb_own)
        rb.addStretch(1)
        l1.addLayout(rb)
        self.yarn_stack = QStackedWidget()
        p_db = QWidget()
        vdb = QVBoxLayout(p_db)
        vdb.setContentsMargins(0, 0, 0, 0)
        self.cb_yarn = _shrinkable(QComboBox())
        self.cb_yarn.setEditable(True)
        self.cb_yarn.setInsertPolicy(QComboBox.NoInsert)
        self.cb_yarn.lineEdit().setPlaceholderText("Search yarn…")
        self.cb_yarn.setMaxVisibleItems(20)
        self.cb_yarn.currentIndexChanged.connect(self._yarn_info)
        vdb.addWidget(self.cb_yarn)
        self.lbl_yarn = QLabel("")
        self.lbl_yarn.setStyleSheet(SMALL)
        vdb.addWidget(self.lbl_yarn)
        self.yarn_stack.addWidget(p_db)
        p_own = QWidget()
        g_own = QGridLayout(p_own)
        g_own.setContentsMargins(0, 0, 0, 0)
        self.cb_material = _shrinkable(QComboBox())
        self.ed_endtiter = _small_edit(80)
        self.ed_filaments = _small_edit(80)
        for i, (lab, wd, unit) in enumerate((("Material", self.cb_material, ""),
                                             ("Final titer", self.ed_endtiter, "dtex"),
                                             ("Filaments", self.ed_filaments, ""))):
            g_own.addWidget(QLabel(lab), i, 0)
            g_own.addWidget(wd, i, 1)
            if unit:
                g_own.addWidget(QLabel(unit), i, 2)
        g_own.setColumnStretch(3, 1)
        self.yarn_stack.addWidget(p_own)
        self.rb_db.toggled.connect(lambda on: self.yarn_stack.setCurrentIndex(0 if on else 1))
        l1.addWidget(self.yarn_stack)
        hr = QHBoxLayout()
        hr.addWidget(QLabel("Similar yarns"))
        self.cb_reach = _shrinkable(QComboBox())
        for lab, v in REACH:
            self.cb_reach.addItem(lab, v)
        self.cb_reach.setCurrentIndex(2)
        hr.addWidget(self.cb_reach, 1)
        l1.addLayout(hr)
        self.chk_material = QCheckBox("Only the same material")
        self.chk_material.setChecked(True)
        l1.addWidget(self.chk_material)
        fv.addWidget(c1)

        c2, l2 = _card("2  Targets", "Fill only what matters - empty = no target.")
        g2 = QGridLayout()
        g2.setHorizontalSpacing(8)
        g2.setVerticalSpacing(3)
        g2.addWidget(QLabel("min"), 0, 1)
        g2.addWidget(QLabel("max"), 0, 2)
        for i, tk in enumerate(ja.TARGETS, start=1):
            label, unit, _dec = w.TARGETS[tk]
            tl = QLabel(label)
            tl.setWordWrap(True)
            g2.addWidget(tl, i, 0)
            lo, hi = _small_edit(), _small_edit()
            g2.addWidget(lo, i, 1)
            g2.addWidget(hi, i, 2)
            u = QLabel(unit)
            u.setStyleSheet(SMALL)
            g2.addWidget(u, i, 3)
            self._target_edits[tk] = (lo, hi)
        l2.addLayout(g2)
        fv.addWidget(c2)

        c3, l3 = _card("3  Jets", "Nothing ticked = all.")
        self.lay_filters = l3
        self.lst_types = self.lst_makers = self.lst_groups = None
        self.chk_titer = QCheckBox("Only jets whose titer range fits the final titer")
        fv.addWidget(c3)

        c4, l4 = _card("4  Machine settings", "Limit the search, e.g. a fixed speed.")
        g4 = QGridLayout()
        g4.setHorizontalSpacing(8)
        g4.addWidget(QLabel("from"), 0, 1)
        g4.addWidget(QLabel("to"), 0, 2)
        for i, p in enumerate(ja.PARAMS, start=1):
            label, _st, unit, _ss, _dec = w.PARAMS[p]
            g4.addWidget(QLabel(label), i, 0)
            lo, hi = _small_edit(), _small_edit()
            g4.addWidget(lo, i, 1)
            g4.addWidget(hi, i, 2)
            u = QLabel(unit)
            u.setStyleSheet(SMALL)
            g4.addWidget(u, i, 3)
            self._limit_edits[p] = (lo, hi)
        l4.addLayout(g4)
        hp = QHBoxLayout()
        hp.addWidget(QLabel("When equally good, prefer"))
        self.cb_prefer = _shrinkable(QComboBox())
        self.cb_prefer.addItem("Safety margin", "robust")
        self.cb_prefer.addItem("Less air", "air")
        hp.addWidget(self.cb_prefer, 1)
        l4.addLayout(hp)
        fv.addWidget(c4)

        hb = QHBoxLayout()
        self.btn_find = QPushButton("Find jets")
        self.btn_find.setStyleSheet(BTN_PRIMARY)
        self.btn_find.clicked.connect(self.find)
        hb.addWidget(self.btn_find)
        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setStyleSheet(BTN)
        self.btn_reset.clicked.connect(self._reset)
        hb.addWidget(self.btn_reset)
        hb.addStretch(1)
        fv.addLayout(hb)
        fv.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(form)
        scroll.setMinimumWidth(430)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        split.addWidget(scroll)

        # ── right: results ────────────────────────────────────────────
        right, rl = _card("Result")
        self.lbl_summary = QLabel("Loading trials…")
        self.lbl_summary.setWordWrap(True)
        self.lbl_summary.setStyleSheet(SMALL)
        rl.addWidget(self.lbl_summary)
        self.tbl = QTableWidget(0, 0)
        self.tbl.setStyleSheet(TABLE_QSS)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.itemSelectionChanged.connect(self._show_detail)
        rl.addWidget(self.tbl, 3)
        det = QHBoxLayout()
        self.lbl_detail = QLabel("Select a jet to see why and which trials are behind it.")
        self.lbl_detail.setWordWrap(True)
        self.lbl_detail.setTextFormat(Qt.RichText)
        self.lbl_detail.setStyleSheet("color:#3B4541;font-size:12px;border:none;")
        self.lbl_detail.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        det.addWidget(self.lbl_detail, 2)
        sv = QVBoxLayout()
        sl = QLabel("Trial series behind it (double-click opens; Ctrl = new tab)")
        sl.setStyleSheet(SMALL)
        sv.addWidget(sl)
        self.lst_series = QListWidget()
        self.lst_series.setStyleSheet("QListWidget{border:1px solid #DADFD8;border-radius:5px;}")
        self.lst_series.itemDoubleClicked.connect(self._open_series)
        sv.addWidget(self.lst_series, 1)
        self.btn_playground = QPushButton("Open in Process Playground")
        self.btn_playground.setStyleSheet(BTN)
        self.btn_playground.setEnabled(False)
        self.btn_playground.clicked.connect(self._open_playground)
        sv.addWidget(self.btn_playground)
        det.addLayout(sv, 1)
        dw = QWidget()
        dw.setLayout(det)
        dw.setMaximumHeight(190)
        rl.addWidget(dw, 1)
        split.addWidget(right)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([440, 1000])
        self.btn_find.setEnabled(False)

    # ── loading ───────────────────────────────────────────────────────
    def reload(self) -> None:
        if self._thread is not None:
            return
        self.lbl_summary.setText("Loading trials…")
        self.btn_reload.setEnabled(False)
        self.btn_find.setEnabled(False)
        self._thread = QThread(self)
        self._loader = _Loader(self._adv)
        self._loader.moveToThread(self._thread)
        self._thread.started.connect(self._loader.run)
        self._loader.done.connect(self._on_loaded)
        self._thread.start()

    def _on_loaded(self, adv, err) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
        self.btn_reload.setEnabled(True)
        if err is not None or adv is None:
            self.lbl_summary.setText("Could not load the trials.")
            from ui.widgets.friendly_error import show_error
            show_error(self, "Jet Advisor", "The trials could not be loaded.", err)
            return
        self._adv = adv
        self._fill_options()
        self.btn_find.setEnabled(True)
        if self._results:
            self.find()
        else:
            o = adv.options()
            self.lbl_summary.setText(f"Basis: {o['n_trials']:,} DTY trials, {o['n_combos']} yarn / jet combinations. "
                                     "Choose a yarn, give at least one target and press \"Find jets\"."
                                     .replace(",", "'"))

    def _fill_options(self) -> None:
        o = self._adv.options()
        keep_yarn = self.cb_yarn.currentData()
        self.cb_yarn.blockSignals(True)
        self.cb_yarn.clear()
        self.cb_yarn.addItem("", None)
        for y in o["yarns"]:
            self.cb_yarn.addItem(y["name"], y["id"])
        comp = QCompleter([y["name"] for y in o["yarns"]], self.cb_yarn)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setFilterMode(Qt.MatchContains)
        self.cb_yarn.setCompleter(comp)
        i = self.cb_yarn.findData(keep_yarn)
        self.cb_yarn.setCurrentIndex(max(i, 0))
        self.cb_yarn.blockSignals(False)
        self._yarns = {y["id"]: y for y in o["yarns"]}
        self._yarn_info()
        keep_mat = self.cb_material.currentData()
        self.cb_material.clear()
        self.cb_material.addItem("(any)", None)
        for m in o["materials"]:
            self.cb_material.addItem(m["name"], m["id"])
        self.cb_material.setCurrentIndex(max(self.cb_material.findData(keep_mat), 0))
        # filter lists (rebuilt, ticks kept)
        keep = {n: (_checked(lst) or []) for n, lst in (("t", self.lst_types), ("m", self.lst_makers),
                                                          ("g", self.lst_groups)) if lst is not None}
        while self.lay_filters.count() > 2:          # title + subtitle stay
            it = self.lay_filters.takeAt(2)
            if it.widget() is not None and it.widget() is not self.chk_titer:
                it.widget().deleteLater()
        lists = []
        for n, title, items in (("t", "Jet type", o["jet_types"]), ("m", "Maker", o["makers"]),
                                ("g", "Group", o["groups"])):
            lab = QLabel(title)
            lab.setStyleSheet("font-weight:600;border:none;")
            self.lay_filters.addWidget(lab)
            lst = _check_list(items)
            for r in range(lst.count()):
                if lst.item(r).data(Qt.UserRole) in keep.get(n, []):
                    lst.item(r).setCheckState(Qt.Checked)
            self.lay_filters.addWidget(lst)
            lists.append(lst)
        self.lst_types, self.lst_makers, self.lst_groups = lists
        self.lay_filters.addWidget(self.chk_titer)

    def _yarn_info(self) -> None:
        y = getattr(self, "_yarns", {}).get(self.cb_yarn.currentData())
        self.lbl_yarn.setText("" if not y else
                              f"{y['material']} · {_fmt(y['endtiter'], 0)} dtex · f{_fmt(y['filaments'], 0)}"
                              + (f" · {y['yarn_type']}" if y["yarn_type"] else ""))

    # ── search ────────────────────────────────────────────────────────
    def _request(self) -> dict:
        targets = {}
        for tk, (lo, hi) in self._target_edits.items():
            a, b = _num(lo.text()), _num(hi.text())
            if a is not None or b is not None:
                targets[tk] = {"lo": a, "hi": b}
        limits = {}
        for p, (lo, hi) in self._limit_edits.items():
            a, b = _num(lo.text()), _num(hi.text())
            if a is not None or b is not None:
                limits[p] = [a, b]
        d = {"targets": targets, "limits": limits, "prefer": self.cb_prefer.currentData(),
             "same_material": self.chk_material.isChecked(), "max_distance": self.cb_reach.currentData(),
             "titer_fit": self.chk_titer.isChecked(),
             "jet_types": _checked(self.lst_types) if self.lst_types else None,
             "makers": _checked(self.lst_makers) if self.lst_makers else None,
             "groups": _checked(self.lst_groups) if self.lst_groups else None}
        if self.rb_db.isChecked():
            d["yarn_id"] = self.cb_yarn.currentData()
        else:
            d.update(endtiter=_num(self.ed_endtiter.text()), filaments=_num(self.ed_filaments.text()),
                     material_id=self.cb_material.currentData())
        return d

    def find(self) -> None:
        if self._adv is None:
            return
        from PySide6.QtWidgets import QMessageBox
        res = self._adv.advise(ja.request_from_json(self._request()))
        if "error" in res:
            msg = {ja.ERR_NO_TARGET: "Give at least one target (min or max).",
                   ja.ERR_NO_YARN: "Choose a yarn or give final titer and filament count."}.get(res["error"], "")
            QMessageBox.information(self, "Jet Advisor", msg)
            return
        if not self._logged:
            self._logged = True
            try:
                from db.usage_log import log_usage_event
                log_usage_event("feature", "jet_advisor_run", "desktop")
            except Exception:
                pass
        self._results = res["results"]
        self._targets_shown = res["targets"]
        yarns = ", ".join(f"{y['name']} ({y['distance']:.2f})" for y in res["yarns"][:10])
        more = f" +{len(res['yarns']) - 10}" if len(res["yarns"]) > 10 else ""
        if not res["yarns"]:
            self.lbl_summary.setText("No similar yarn with trials - widen \"Similar yarns\" or allow other materials.")
        elif not self._results:
            self.lbl_summary.setText("No jet with trials in this range - loosen the jet filters or the machine "
                                     f"settings.\nYarns used (distance): {yarns}{more}")
        else:
            self.lbl_summary.setText(f"{res['n_jets']} jets from {res['n_combos']} yarn / jet combinations.  "
                                     f"Yarns used (distance, 0 = same yarn): {yarns}{more}")
        self._fill_table()

    def _fill_table(self) -> None:
        cols = (["#", "Jet", "Type", "Chance"] + [PARAM_SHORT[p] for p in ja.PARAMS]
                + [TARGET_SHORT[tk] for tk in self._targets_shown] + ["Air Nm³/h", "Source", "Yarn", "Trials"])
        tbl = self.tbl
        tbl.clearSelection()
        tbl.setColumnCount(len(cols))
        tbl.setHorizontalHeaderLabels(cols)
        tbl.setRowCount(len(self._results))
        for r, res in enumerate(self._results):
            c = res.best
            cells: List[tuple] = [(str(r + 1), None), (res.jet.get("jet_name") or "", None),
                                  (res.jet.get("type_name") or "", None), (f"{round(c.prob * 100)} %", None)]
            for p in ja.PARAMS:
                a, b = res.window.get(p, (c.settings[p], c.settings[p]))
                txt = _fmt(c.settings[p], PARAM_DEC[p])
                if abs(b - a) > 1e-6:
                    txt += f"  ({_fmt(a, PARAM_DEC[p])}–{_fmt(b, PARAM_DEC[p])})"
                cells.append((txt, None))
            for tk in self._targets_shown:
                pr = c.preds.get(tk)
                if pr is None:
                    cells.append(("–", None))
                else:
                    cells.append(((("✓ " if pr.met else "✗ ") + f"{pr.value:.1f} ± {pr.sd:.1f}"),
                                  _GOOD if pr.met else _BAD))
            cells.append((_fmt(c.air, 2), None))
            cells.append(("measured" if c.source == "measured" else "model", None))
            cells.append((res.yarn_name + (f" ({res.distance:.2f})" if res.distance > 0 else ""), None))
            cells.append((f"{res.n_trials} / {res.n_series} series", None))
            for j, (txt, colour) in enumerate(cells):
                it = QTableWidgetItem(txt)
                if colour is not None:
                    it.setForeground(colour)
                if j == 0 or 3 <= j < len(cells) - 3:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if j == 2 and res.titer_ok is False:
                    it.setText(txt + "  ⚠ titer")
                    it.setToolTip(f"Final titer outside the jet's range {_fmt(res.jet.get('titer_from'), 0)}–"
                                  f"{_fmt(res.jet.get('titer_to'), 0)} dtex")
                tbl.setItem(r, j, it)
        hh = tbl.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        hh.setStretchLastSection(True)
        self.lbl_detail.setText("Select a jet to see why and which trials are behind it.")
        self.lst_series.clear()
        self.btn_playground.setEnabled(False)
        if self._results:
            tbl.selectRow(0)

    def _show_detail(self) -> None:
        rows = self.tbl.selectionModel().selectedRows() if self.tbl.selectionModel() else []
        if not rows or rows[0].row() >= len(self._results):
            return
        res = self._results[rows[0].row()]
        c = res.best
        j = res.jet
        why = (f"Run exactly like this ({c.n_trials} trials)." if c.source == "measured"
               else "Between measured settings, estimated by the model.")
        varied = ", ".join(w.PARAMS[p][0].lower() for p in res.varied) or "–"
        margin = (f"Safety margin to the nearest target limit: {c.safety:.1f} × spread."
                  if all(p.met for p in c.preds.values()) else
                  f"Misses the targets by {c.miss:.1f} × spread in total.")
        preds = "<br>".join(f"{w.TARGETS[tk][0]}: <b>{p.value:.1f}</b> ± {p.sd:.1f} {w.TARGETS[tk][1]} "
                            f"(chance {round(p.prob * 100)} %)" for tk, p in c.preds.items())
        self.lbl_detail.setText(
            f"<b>{j.get('jet_name') or ''}</b> · {j.get('maker_name') or ''} · {j.get('group_name') or ''}<br>"
            f"Titer range {_fmt(j.get('titer_from'), 0)}–{_fmt(j.get('titer_to'), 0)} dtex<br><br>"
            f"<b>Why this setting</b><br>{why} Varied in the trials: {varied}.<br>{margin}<br><br>{preds}")
        self.lst_series.clear()
        for sid, name in res.series:
            it = QListWidgetItem(name or f"#{sid}")
            it.setData(Qt.UserRole, sid)
            self.lst_series.addItem(it)
        self.btn_playground.setEnabled(res.trial_id is not None)

    def _selected(self) -> Optional[ja.JetResult]:
        rows = self.tbl.selectionModel().selectedRows() if self.tbl.selectionModel() else []
        return self._results[rows[0].row()] if rows and rows[0].row() < len(self._results) else None

    def _open_series(self, item: QListWidgetItem) -> None:
        from PySide6.QtWidgets import QApplication
        import app_meta
        from db.connection import fetch_all
        sid = item.data(Qt.UserRole)
        rows = fetch_all("SELECT e.ID AS exp_pk, e.[Experiment ID] AS eid FROM tblTrialSeries s "
                         "JOIN tblExperimente e ON e.ID = s.ExperimentID WHERE s.ID = ?", [int(sid)])
        opener = getattr(app_meta, "open_recent_series", None)
        if rows and callable(opener):
            new_tab = bool(QApplication.keyboardModifiers() & Qt.ControlModifier)
            opener(rows[0]["exp_pk"], int(sid), str(rows[0]["eid"] or ""), new_tab)

    def _open_playground(self) -> None:
        res = self._selected()
        import app_meta
        if res is not None and res.trial_id is not None and callable(getattr(app_meta, "open_process_playground", None)):
            app_meta.open_process_playground(trial_id=res.trial_id)

    def _open_help(self) -> None:
        from ui.widgets.help_texts_jet_advisor import TEXTS
        from ui.widgets.multilang_help import show_help
        show_help(TEXTS, self)

    def _reset(self) -> None:
        for lo, hi in list(self._target_edits.values()) + list(self._limit_edits.values()):
            lo.clear()
            hi.clear()
        for lst in (self.lst_types, self.lst_makers, self.lst_groups):
            if lst is not None:
                for r in range(lst.count()):
                    lst.item(r).setCheckState(Qt.Unchecked)
        self.chk_titer.setChecked(False)
        self.chk_material.setChecked(True)
        self.cb_reach.setCurrentIndex(2)
        self.cb_prefer.setCurrentIndex(0)
        self._results = []
        self.tbl.setRowCount(0)
        self.lst_series.clear()
        self.btn_playground.setEnabled(False)

    def showEvent(self, event):  # noqa: N802
        try:
            import app_meta
            level = int((app_meta.current_user or {}).get("access_level") or 0)
            sidebar_nav.refresh_lazy_sidebar(self, level)
        except Exception:
            pass
        super().showEvent(event)
        if self._adv is None and self._thread is None:
            self.reload()


def _shrinkable(cb: QComboBox) -> QComboBox:
    """Combo boxes with long entries must not widen the form (the list itself shows full names)."""
    cb.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    cb.setMinimumContentsLength(12)
    return cb
