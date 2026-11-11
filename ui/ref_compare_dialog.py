"""ref_compare_dialog.py - "Compare with Ref" window of Show Experiment
(Nutzerwunsch 2026-11-11). All trials of the series against one reference
sample over the metrics of ALL lab tabs; the user decides per metric what
"better" means (higher / lower / close to Ref, with tolerance) and sees which
trials pass every criterion. Logic: ui/ref_compare.py, saved criteria sets:
db/ref_criteria.py. Only reads - nothing in the series is changed.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QHBoxLayout, QHeaderView, QInputDialog, QLabel,
    QMenu, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from ui import ref_compare as rc

C_PASS, C_FAIL, C_MISSING = QColor("#C8E6C9"), QColor("#FFCDD2"), QColor("#ECECEC")
C_REF = QColor("#FFF4D6")
C_ALL = QColor("#2E7D32")
FIXED_COLS = 2   # Trial, Result

UNSAVED = "(not saved)"


def _fmt(v: Optional[float]) -> str:
    if v is None:
        return "–"
    return f"{v:.2f}".rstrip("0").rstrip(".") if abs(v) < 1e6 else f"{v:.0f}"


def gather_sources(screen) -> List[Dict[str, Any]]:
    """Numeric rows of every lab tab of the screen (one column per trial).
    Builds tabs that were not opened yet (they are filled lazily)."""
    pending = getattr(screen, "_pending_tab_populate", None) or {}
    for key in list(pending.keys()):
        fn = pending.pop(key, None)
        if fn is not None:
            try:
                fn()
            except Exception:
                pass
    out = []
    for attr, model in screen._iter_save_models():
        if getattr(model, "_col_titles", None) is not screen._trial_labels:
            continue   # machine tabs: one column per ply
        skip = int(getattr(model, "_n_info_rows", 0) or 0)
        rows = [(model._row_titles[r], list(model._matrix[r]))
                for r in range(skip, len(model._row_titles))]
        out.append({"attr": attr, "tab": _tab_label(screen, model) or attr.replace("model_", ""), "rows": rows})
    return out


def _tab_label(screen, model) -> str:
    owner = getattr(model, "_ffct_owner", None)
    table = owner() if callable(owner) else None
    tabs = getattr(screen, "tabs", None)
    if table is None or tabs is None:
        return ""
    for i in range(tabs.count()):
        w = tabs.widget(i)
        if w is table or (w is not None and w.isAncestorOf(table)):
            return tabs.tabText(i).replace("&", "").lstrip("● ").strip()
    return ""


class RefCompareDialog(QDialog):
    def __init__(self, screen, ref_id: Optional[int] = None):
        super().__init__(screen)
        self._screen = screen
        self.setWindowTitle("Compare with Ref")
        self.resize(1250, 680)
        self._trial_ids = [int(t) for t in screen._trial_ids]
        self._vno = {int(t): v for t, v in zip(screen._trial_ids, screen._trial_vnos)}
        self._refs = dict(screen._reference_names)
        self._sources = gather_sources(screen)
        self._criteria: Dict[str, Dict[str, Any]] = {}
        self._sets: List[Dict[str, Any]] = []
        self._set_id: Optional[int] = None
        self._changed = False

        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("Reference:"))
        self.cmb_ref = QComboBox()
        for tid, name in self._refs.items():
            self.cmb_ref.addItem(name or "Ref", tid)
        if ref_id is not None and int(ref_id) in self._refs:
            self.cmb_ref.setCurrentIndex(list(self._refs).index(int(ref_id)))
        self.cmb_ref.currentIndexChanged.connect(self._rebuild)
        top.addWidget(self.cmb_ref)
        top.addSpacing(16)
        top.addWidget(QLabel("Criteria:"))
        self.cmb_set = QComboBox()
        self.cmb_set.setMinimumWidth(220)
        self.cmb_set.activated.connect(self._on_set_chosen)
        top.addWidget(self.cmb_set)
        self.btn_save = QPushButton("Save")
        self.btn_save.setToolTip("Save the criteria under this name (for all users)")
        self.btn_save.clicked.connect(self._save)
        self.btn_save_as = QPushButton("Save as…")
        self.btn_save_as.clicked.connect(lambda: self._save(as_new=True))
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self._delete_set)
        for b in (self.btn_save, self.btn_save_as, self.btn_delete):
            top.addWidget(b)
        top.addStretch(1)
        lay.addLayout(top)

        opts = QHBoxLayout()
        self.chk_only = QCheckBox("Only trials better in all")
        self.chk_only.toggled.connect(self._fill)
        self.chk_hide = QCheckBox("Hide metrics without a criterion")
        self.chk_hide.toggled.connect(self._rebuild)
        opts.addWidget(self.chk_only)
        opts.addWidget(self.chk_hide)
        opts.addStretch(1)
        self.lbl_sum = QLabel("")
        f = self.lbl_sum.font()
        f.setBold(True)
        self.lbl_sum.setFont(f)
        opts.addWidget(self.lbl_sum)
        lay.addLayout(opts)

        hint = QLabel("Click a column header to set what <b>better</b> means for that metric: higher, lower or "
                      "close to the reference (with a tolerance). A trial counts as better when it meets every "
                      "criterion - a missing value does not. Double-click a trial to show it in Machine Data.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#555;")
        lay.addWidget(hint)

        self.tbl = QTableWidget()
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.verticalHeader().setVisible(False)
        hh = self.tbl.horizontalHeader()
        hh.setSectionsClickable(True)
        hh.sectionClicked.connect(self._on_header)
        hh.setDefaultAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.tbl.cellDoubleClicked.connect(self._on_double)
        lay.addWidget(self.tbl, 1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        bottom.addWidget(btn_close)
        lay.addLayout(bottom)

        self._load_sets()
        self._rebuild()
        try:
            from db.usage_log import log_usage_event
            log_usage_event("feature", "ref_compare_open", str(getattr(screen, "_series_pk", "")))
        except Exception:
            pass

    # ── criteria sets ──────────────────────────────────────────────────────
    def _load_sets(self, select_id: Optional[int] = None) -> None:
        from db import ref_criteria
        self._db = ref_criteria.available()
        self._sets = []
        if self._db:
            try:
                self._sets = ref_criteria.list_sets()
            except Exception:
                self._sets = []
        self.cmb_set.blockSignals(True)
        self.cmb_set.clear()
        self.cmb_set.addItem(UNSAVED, None)
        for s in self._sets:
            self.cmb_set.addItem(str(s["Name"]), int(s["ID"]))
        if select_id is not None:
            i = self.cmb_set.findData(int(select_id))
            self.cmb_set.setCurrentIndex(max(i, 0))
        self.cmb_set.blockSignals(False)
        self._set_id = self.cmb_set.currentData()
        self._update_set_buttons()

    def _current_set(self) -> Optional[Dict[str, Any]]:
        return next((s for s in self._sets if int(s["ID"]) == int(self._set_id)), None) \
            if self._set_id is not None else None

    def _update_set_buttons(self) -> None:
        s = self._current_set()
        tip = "" if self._db else "Saving criteria is not set up in this database yet."
        self.btn_save.setEnabled(self._db and self._changed)
        self.btn_save_as.setEnabled(self._db and bool(self._criteria))
        from db import ref_criteria
        self.btn_delete.setEnabled(self._db and s is not None and ref_criteria.can_delete(s))
        for b in (self.btn_save, self.btn_save_as, self.btn_delete):
            b.setToolTip(tip or b.toolTip())
        i = self.cmb_set.currentIndex()
        base = self.cmb_set.itemText(i).removesuffix(" *")
        self.cmb_set.setItemText(i, base + (" *" if self._changed and s is not None else ""))

    def _on_set_chosen(self, _i: int) -> None:
        if self._changed and not self._confirm_discard():
            self.cmb_set.setCurrentIndex(max(self.cmb_set.findData(self._set_id), 0))
            return
        if self._changed and self._current_set() is not None:
            j = self.cmb_set.findData(self._set_id)
            self.cmb_set.setItemText(j, self.cmb_set.itemText(j).removesuffix(" *"))
        self._set_id = self.cmb_set.currentData()
        s = self._current_set()
        self._criteria = {k: dict(v) for k, v in (s["criteria"] if s else {}).items()}
        self._changed = False
        self._rebuild()

    def _confirm_discard(self) -> bool:
        return QMessageBox.question(self, "Compare with Ref", "Discard the changed criteria?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes

    def _save(self, as_new: bool = False) -> None:
        from db import ref_criteria
        s = self._current_set()
        if s is None or as_new:
            name, ok = QInputDialog.getText(self, "Save criteria", "Name of the criteria set "
                                            "(e.g. customer and article):", text="" if s is None else s["Name"])
            if not ok:
                return
            set_id = None
        else:
            name, set_id = s["Name"], int(s["ID"])
        try:
            new_id = ref_criteria.save(name, self._criteria, set_id)
        except ValueError as e:
            QMessageBox.information(self, "Save criteria", str(e))
            return
        except Exception as e:
            from ui.widgets.friendly_error import show_error
            show_error(self, "Save criteria", "The criteria could not be saved.", e, warning=True)
            return
        self._changed = False
        self._load_sets(select_id=new_id)

    def _delete_set(self) -> None:
        from db import ref_criteria
        s = self._current_set()
        if s is None or QMessageBox.question(
                self, "Delete criteria", f'Delete the criteria set "{s["Name"]}" for all users?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            ref_criteria.delete(int(s["ID"]))
        except Exception as e:
            from ui.widgets.friendly_error import show_error
            show_error(self, "Delete criteria", "The criteria set could not be deleted.", e, warning=True)
            return
        self._changed = bool(self._criteria)
        self._load_sets()

    # ── table ──────────────────────────────────────────────────────────────
    def _ref_id(self) -> Optional[int]:
        return self.cmb_ref.currentData()

    def _rebuild(self) -> None:
        ref = self._ref_id()
        self._metrics = rc.collect_metrics(self._sources, self._trial_ids, ref) if ref is not None else []
        if self.chk_hide.isChecked():
            self._shown = [m for m in self._metrics if (self._criteria.get(m["key"]) or {}).get("dir")]
        else:
            self._shown = list(self._metrics)
        self._update_set_buttons()
        self._fill()

    def _header_text(self, m: Dict[str, Any]) -> str:
        c = self._criteria.get(m["key"]) or {}
        d = c.get("dir")
        if d:
            tol = c.get("tol", rc.DEFAULT_TOL[d])
            crit = rc.DIR_LABEL[d] + (f" ±{_fmt(tol)} %" if d == rc.CLOSE or tol else "")
        else:
            crit = "(ignored)"
        # long Itemat titles: break before "@0.3 cN/dtex"
        title = "\n".join(p.strip() for p in m["title"].replace("@", "\n@", 1).split("\n") if p.strip())
        return f"{m['tab']}\n{title}\n{crit}"

    def _fill(self, *_a) -> None:
        rows = rc.evaluate(self._metrics, self._trial_ids, self._criteria, skip_ids=self._refs.keys())
        n_all = sum(1 for r in rows if r["all_pass"])
        total = rows[0]["total"] if rows else 0
        self.lbl_sum.setText(
            "Set at least one criterion (click a column header)" if not total
            else f"{n_all} of {len(rows)} trials better in all {total} criteria")
        if self.chk_only.isChecked():
            rows = [r for r in rows if r["all_pass"]]
        self._rows = rows
        t = self.tbl
        t.clear()
        t.setColumnCount(FIXED_COLS + len(self._shown))
        t.setRowCount(1 + len(rows))
        t.setHorizontalHeaderLabels(["Trial", "Result"] + [self._header_text(m) for m in self._shown])
        for j, m in enumerate(self._shown):
            hi = t.horizontalHeaderItem(FIXED_COLS + j)
            d = (self._criteria.get(m["key"]) or {}).get("dir")
            if hi is not None:
                hi.setToolTip(f"{m['tab']} - {m['title']}\nReference: {_fmt(m['ref'])}\nClick to set the criterion")
                if d:
                    fh = hi.font()
                    fh.setBold(True)
                    hi.setFont(fh)
        bold = QFont(t.font())
        bold.setBold(True)
        # reference row
        name = self.cmb_ref.currentText()
        for c, txt in enumerate(["Ref", name]):
            it = QTableWidgetItem(txt)
            it.setBackground(C_REF)
            it.setFont(bold)
            t.setItem(0, c, it)
        for j, m in enumerate(self._shown):
            it = QTableWidgetItem(_fmt(m["ref"]))
            it.setBackground(C_REF)
            it.setTextAlignment(Qt.AlignCenter)
            t.setItem(0, FIXED_COLS + j, it)
        # trials
        for i, r in enumerate(rows, start=1):
            tid = r["trial_id"]
            it = QTableWidgetItem(f"V{self._vno.get(tid)}")
            it.setData(Qt.UserRole, tid)
            it.setFont(bold)
            t.setItem(i, 0, it)
            res = QTableWidgetItem(f"{r['passed']} / {r['total']}" if r["total"] else "–")
            res.setTextAlignment(Qt.AlignCenter)
            if r["all_pass"]:
                res.setBackground(C_ALL)
                res.setForeground(QColor("#ffffff"))
                res.setFont(bold)
                res.setToolTip("Better than the reference in all criteria")
            elif r["total"]:
                miss = rc.failing(r, self._metrics)
                res.setToolTip("Misses: " + ", ".join(miss))
            t.setItem(i, 1, res)
            for j, m in enumerate(self._shown):
                cell = r["cells"][m["key"]]
                v = m["values"].get(tid)
                diff = cell["diff"]
                txt = _fmt(v) + (f"  ({diff:+.1f} %)" if diff is not None and v is not None else "")
                it = QTableWidgetItem(txt)
                it.setTextAlignment(Qt.AlignCenter)
                st = cell["status"]
                if st == rc.PASS:
                    it.setBackground(C_PASS)
                elif st == rc.FAIL:
                    it.setBackground(C_FAIL)
                elif st == rc.MISSING:
                    it.setBackground(C_MISSING)
                    it.setToolTip("No value - counts as not better")
                else:
                    it.setForeground(QColor("#777777"))
                t.setItem(i, FIXED_COLS + j, it)
        hh = t.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Interactive)
        t.resizeColumnsToContents()
        for c in range(FIXED_COLS, t.columnCount()):
            t.setColumnWidth(c, max(110, min(t.columnWidth(c), 190)))
        t.setColumnWidth(1, 100)

    # ── interaction ────────────────────────────────────────────────────────
    def _on_header(self, col: int) -> None:
        j = col - FIXED_COLS
        if not (0 <= j < len(self._shown)):
            return
        m = self._shown[j]
        cur = dict(self._criteria.get(m["key"]) or {})
        menu = QMenu(self)
        acts = {}
        for d in rc.DIRECTIONS:
            a = menu.addAction({rc.HIGHER: "Higher is better", rc.LOWER: "Lower is better",
                                rc.CLOSE: "Close to Ref is better"}[d])
            a.setCheckable(True)
            a.setChecked(cur.get("dir") == d)
            acts[a] = d
        a_none = menu.addAction("Ignore")
        a_none.setCheckable(True)
        a_none.setChecked(not cur.get("dir"))
        menu.addSeparator()
        tol_now = cur.get("tol", rc.DEFAULT_TOL.get(cur.get("dir"), 0.0))
        a_tol = menu.addAction(f"Tolerance… ({_fmt(tol_now)} %)")
        a_tol.setEnabled(bool(cur.get("dir")))
        hh = self.tbl.horizontalHeader()
        pos = hh.mapToGlobal(hh.rect().bottomLeft())
        pos.setX(hh.mapToGlobal(hh.rect().topLeft()).x() + hh.sectionViewportPosition(col))
        chosen = menu.exec(pos)
        if chosen is None:
            return
        if chosen is a_none:
            self._criteria.pop(m["key"], None)
        elif chosen is a_tol:
            v, ok = QInputDialog.getDouble(
                self, "Tolerance",
                f"{m['title']}\nTolerance in % of the reference value ({_fmt(m['ref'])}):\n"
                "higher/lower: how much worse still counts; close: allowed deviation either way.",
                float(tol_now or 0), 0.0, 1000.0, 1)
            if not ok:
                return
            cur["tol"] = v
            self._criteria[m["key"]] = cur
        else:
            d = acts[chosen]
            new = {"dir": d}
            if cur.get("dir") == d and "tol" in cur:
                new["tol"] = cur["tol"]
            self._criteria[m["key"]] = new
        self._changed = True
        self._rebuild()

    def _on_double(self, row: int, _col: int) -> None:
        it = self.tbl.item(row, 0)
        tid = it.data(Qt.UserRole) if it is not None else None
        if tid is None:
            return
        jump = getattr(self._screen, "_show_trial_in_machine_data", None)
        if callable(jump):
            jump(int(tid))

    def closeEvent(self, ev):  # noqa: N802
        if self._changed and self._db and self._criteria:
            res = QMessageBox.question(
                self, "Compare with Ref", "Save the changed criteria?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
            if res == QMessageBox.Cancel:
                ev.ignore()
                return
            if res == QMessageBox.Save:
                self._save()
                if self._changed:   # not saved (cancelled name dialog)
                    ev.ignore()
                    return
        super().closeEvent(ev)


def open_ref_compare(screen, ref_id: Optional[int] = None) -> None:
    if not getattr(screen, "_reference_names", None):
        QMessageBox.information(screen, "Compare with Ref",
                                "This series has no reference sample. Add one with + Ref first.")
        return
    dlg = RefCompareDialog(screen, ref_id)
    dlg.setAttribute(Qt.WA_DeleteOnClose)
    dlg.show()   # not modal: look at the series meanwhile
