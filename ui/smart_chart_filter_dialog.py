# ui/smart_chart_filter_dialog.py
"""Smart Chart: "+ Add filter" / edit a filter chip (ui/screen_smart_chart.py).

Left: one searchable tree of all fields, groups (Yarn / Jet / Machine / Lab /
General) collapsible, all collapsed until you search. Right, for a number
field: histogram of the values that the OTHER filters leave (drag across it
to pick a range), From/To and which values count: all in the range, only
every <step> (1 = whole numbers, 0.5 = 1, 1.5, 2 …) or picked values (tick
list of the values that occur, with counts). For a list field: tick list
with counts. The line below always says how many trials the new filter
would leave.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional, Sequence

from PySide6.QtCore import QLocale, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QDoubleValidator, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QRadioButton, QStackedWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget,
)

from db import trial_explorer as te

ACCENT = "#1F7A3A"
INSIDE = QColor("#1F7A3A")
OUTSIDE = QColor("#CBD5CB")


def fmt_num(x: Optional[float]) -> str:
    if x is None:
        return ""
    return f"{x:.4f}".rstrip("0").rstrip(".")


class HistogramWidget(QWidget):
    """Bars of a te.histogram(); the chosen range is green. Drag with the
    mouse to choose a range."""
    rangeChanged = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.setMouseTracking(True)
        self.hist: Dict[str, Any] = {"counts": [], "edges": []}
        self.lo: Optional[float] = None
        self.hi: Optional[float] = None
        self._drag_from: Optional[float] = None
        self.setToolTip("Drag across the bars to choose a range")

    def set_hist(self, hist: Dict[str, Any]) -> None:
        self.hist = hist or {"counts": [], "edges": []}
        self.update()

    def set_range(self, lo: Optional[float], hi: Optional[float]) -> None:
        self.lo, self.hi = lo, hi
        self.update()

    def _value_at(self, px: float) -> Optional[float]:
        e = self.hist.get("edges") or []
        if len(e) < 2:
            return None
        frac = min(1.0, max(0.0, px / max(1, self.width())))
        return e[0] + frac * (e[-1] - e[0])

    def mousePressEvent(self, ev):  # noqa: N802
        self._drag_from = self._value_at(ev.position().x())

    def mouseMoveEvent(self, ev):  # noqa: N802
        if self._drag_from is None or not (ev.buttons() & Qt.LeftButton):
            return
        v = self._value_at(ev.position().x())
        if v is None:
            return
        lo, hi = sorted((self._drag_from, v))
        self.set_range(_snap(lo), _snap(hi))
        self.rangeChanged.emit(self.lo, self.hi)

    def mouseReleaseEvent(self, ev):  # noqa: N802
        self._drag_from = None

    def paintEvent(self, ev):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        counts, edges = self.hist.get("counts") or [], self.hist.get("edges") or []
        w, h = self.width(), self.height() - 1
        p.setPen(QPen(QColor("#9AA59C"), 1))
        p.drawLine(0, h, w, h)
        if not counts:
            p.setPen(QColor("#5A6460"))
            p.drawText(self.rect(), Qt.AlignCenter, "No values")
            return
        mx = max(counts) or 1
        bw = w / len(counts)
        p.setPen(Qt.NoPen)
        for i, c in enumerate(counts):
            a, b = edges[i], edges[i + 1]
            inside = (self.lo is None or b > self.lo) and (self.hi is None or a < self.hi) \
                and (self.lo is not None or self.hi is not None)
            p.setBrush(INSIDE if inside else OUTSIDE)
            bh = max(1.0, (c / mx) * (h - 6)) if c else 0.0
            p.drawRoundedRect(QRectF(i * bw + 1, h - bh, max(1.0, bw - 2), bh), 2, 2)
        p.end()


def _snap(v: float) -> float:
    """Round a dragged value to a readable number."""
    if v == 0:
        return 0.0
    mag = 10 ** (len(str(int(abs(v)))) - 2) if abs(v) >= 10 else 0.1
    return round(round(v / mag) * mag, 4)


class AddFilterDialog(QDialog):
    def __init__(self, ds: te.TrialDataset, catalog: Sequence[te.Field], filters: List[Dict[str, Any]],
                 ply_scope: str = "any", edit: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit filter" if edit else "Add filter")
        self.resize(820, 560)
        self.ds, self.catalog, self.ply_scope = ds, list(catalog), ply_scope
        self.others = [f for f in filters if not (edit and f.get("key") == edit.get("key"))]
        self.result_filter: Optional[Dict[str, Any]] = None
        self.field: Optional[te.Field] = None

        root = QHBoxLayout(self)
        # ── field list
        left = QVBoxLayout()
        left.addWidget(QLabel("<b>Field</b>"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search a field…")
        self.txt_search.textChanged.connect(self._fill_fields)
        left.addWidget(self.txt_search)
        self.lst_fields = QTreeWidget()
        self.lst_fields.setHeaderHidden(True)
        self.lst_fields.setMinimumWidth(260)
        self.lst_fields.setIndentation(14)
        self.lst_fields.currentItemChanged.connect(self._on_field)
        self.lst_fields.itemClicked.connect(self._toggle_group)
        left.addWidget(self.lst_fields, 1)
        root.addLayout(left)

        # ── editor
        right = QVBoxLayout()
        self.lbl_field = QLabel("Choose a field on the left.")
        self.lbl_field.setStyleSheet("font-size:16px; font-weight:600;")
        right.addWidget(self.lbl_field)
        self.lbl_scope = QLabel("")
        self.lbl_scope.setStyleSheet("color:#5A6460;")
        right.addWidget(self.lbl_scope)
        self.stack = QStackedWidget()
        self.stack.addWidget(QWidget())
        self.stack.addWidget(self._build_num())
        self.stack.addWidget(self._build_cat())
        right.addWidget(self.stack, 1)
        self.lbl_hits = QLabel("")
        self.lbl_hits.setWordWrap(True)
        self.lbl_hits.setStyleSheet("background:#E6F2E9; border:1px solid #BFDCC7; border-radius:6px;"
                                    "padding:8px 10px; color:#165C2B;")
        right.addWidget(self.lbl_hits)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.btn_ok = bb.button(QDialogButtonBox.Ok)
        self.btn_ok.setText("Apply" if edit else "Add filter")
        self.btn_ok.setEnabled(False)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        right.addWidget(bb)
        root.addLayout(right, 1)

        self._hit_timer = QTimer(self)
        self._hit_timer.setSingleShot(True)
        self._hit_timer.setInterval(150)
        self._hit_timer.timeout.connect(self._update_hits)

        self._fill_fields()
        if edit:
            self._select_field(edit.get("key"))
            self._load_filter(edit)
            self.lst_fields.setEnabled(False)
            self.txt_search.setEnabled(False)
        else:
            self.txt_search.setFocus()

    # ---- editors ----
    def _build_num(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        self.hist = HistogramWidget()
        self.hist.rangeChanged.connect(self._on_hist_drag)
        v.addWidget(self.hist, 1)
        self.lbl_axis = QLabel("")
        self.lbl_axis.setStyleSheet("color:#5A6460;")
        v.addWidget(self.lbl_axis)
        row = QHBoxLayout()
        val = QDoubleValidator(self)
        val.setNotation(QDoubleValidator.StandardNotation)
        val.setLocale(QLocale.c())
        self.txt_lo, self.txt_hi = QLineEdit(), QLineEdit()
        for lab, t in (("From", self.txt_lo), ("To", self.txt_hi)):
            t.setValidator(val)
            t.setPlaceholderText("any")
            t.setFixedWidth(110)
            t.textEdited.connect(self._on_num_typed)
            row.addWidget(QLabel(lab))
            row.addWidget(t)
        row.addStretch(1)
        v.addLayout(row)

        # which values in the range count (Nutzerwunsch: "nur ganze Zahlen / 1, 1.5, 2 …")
        vm = QHBoxLayout()
        self.grp_vals = QButtonGroup(self)
        self.rb_all = QRadioButton("All values in the range")
        self.rb_step = QRadioButton("Only every")
        self.rb_pick = QRadioButton("Pick values")
        self.rb_all.setChecked(True)
        self.cmb_step = QComboBox()
        self.cmb_step.setEditable(True)
        self.cmb_step.addItems(["1", "0.5", "0.25", "0.2", "0.1"])
        self.cmb_step.setCurrentText("1")
        self.cmb_step.setFixedWidth(70)
        self.cmb_step.setToolTip("1 = whole numbers only · 0.5 = 1, 1.5, 2 … · 0.25 = 1, 1.25, 1.5 …")
        self.cmb_step.currentTextChanged.connect(lambda _t: (self.rb_step.setChecked(True), self._hit_timer.start()))
        for i, rb in enumerate((self.rb_all, self.rb_step, self.rb_pick)):
            self.grp_vals.addButton(rb, i)
        self.grp_vals.idClicked.connect(self._on_value_mode)
        vm.addWidget(self.rb_all)
        vm.addSpacing(10)
        vm.addWidget(self.rb_step)
        vm.addWidget(self.cmb_step)
        vm.addSpacing(10)
        vm.addWidget(self.rb_pick)
        vm.addStretch(1)
        v.addLayout(vm)
        self.lst_values = QListWidget()
        self.lst_values.setMaximumHeight(150)
        self.lst_values.setVisible(False)
        self.lst_values.itemChanged.connect(lambda _it: self._hit_timer.start())
        v.addWidget(self.lst_values)
        self.lbl_values = QLabel("")
        self.lbl_values.setStyleSheet("color:#5A6460;")
        self.lbl_values.setVisible(False)
        v.addWidget(self.lbl_values)
        return w

    def _on_value_mode(self, _i=None) -> None:
        pick = self.rb_pick.isChecked()
        if pick:
            self._fill_values()
        self.lst_values.setVisible(pick and self.lst_values.count() > 0)
        self.lbl_values.setVisible(pick and self.lst_values.count() == 0)
        self._hit_timer.start()

    def _fill_values(self, ticked: Optional[set] = None) -> None:
        """Tick list of the values that occur between From and To."""
        if self.field is None or self.field.kind != "num":
            return
        lo, hi = _parse(self.txt_lo.text()), _parse(self.txt_hi.text())
        if ticked is None:
            ticked = {self.lst_values.item(i).data(Qt.UserRole) for i in range(self.lst_values.count())
                      if self.lst_values.item(i).checkState() == Qt.Checked}
            fresh = self.lst_values.count() == 0
        else:
            fresh = False
        vals = te.distinct_values(self.ds.field_values(self.field.key, self.others, self.ply_scope), lo, hi)
        self.lst_values.blockSignals(True)
        self.lst_values.clear()
        if vals is None:
            self.lbl_values.setText("Too many different values to pick from - narrow From/To or use “Only every”.")
        else:
            for x, n in vals:
                it = QListWidgetItem(f"{fmt_num(x)}{(' ' + self.field.unit) if self.field.unit else ''}   "
                                     f"({n:,})".replace(",", "'"))
                it.setData(Qt.UserRole, x)
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                it.setCheckState(Qt.Checked if (fresh or x in ticked) else Qt.Unchecked)
                self.lst_values.addItem(it)
            self.lbl_values.setText("" if vals else "No values in this range.")
        self.lst_values.blockSignals(False)
        self.lst_values.setVisible(self.rb_pick.isChecked() and self.lst_values.count() > 0)
        self.lbl_values.setVisible(self.rb_pick.isChecked() and self.lst_values.count() == 0)

    def _build_cat(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        # time fields (Year, Month …): a period that moves with the calendar, or from – to
        self.period_box = QWidget()
        pr = QHBoxLayout(self.period_box)
        pr.setContentsMargins(0, 0, 0, 0)
        pr.addWidget(QLabel("Period:"))
        self.cmb_period = QComboBox()
        self.cmb_period.addItem("Pick values below", "")
        for k, lab in te.PERIODS.items():
            self.cmb_period.addItem(lab, k)
        self.cmb_period.currentIndexChanged.connect(self._on_period)
        pr.addWidget(self.cmb_period)
        self.cmb_from, self.cmb_to = QComboBox(), QComboBox()
        for c in (self.cmb_from, self.cmb_to):
            c.currentIndexChanged.connect(lambda _i: self._hit_timer.start())
        self.lbl_from, self.lbl_to = QLabel("from"), QLabel("to")
        for wdg in (self.lbl_from, self.cmb_from, self.lbl_to, self.cmb_to):
            pr.addWidget(wdg)
        pr.addStretch(1)
        v.addWidget(self.period_box)
        self.txt_cat_search = QLineEdit()
        self.txt_cat_search.setPlaceholderText("Search a value…")
        self.txt_cat_search.textChanged.connect(self._filter_cats)
        v.addWidget(self.txt_cat_search)
        self.lst_cats = QListWidget()
        self.lst_cats.itemChanged.connect(lambda _it: self._hit_timer.start())
        v.addWidget(self.lst_cats, 1)
        row = QHBoxLayout()
        b_none = QPushButton("Clear ticks")
        b_none.clicked.connect(lambda: self._tick_all(False))
        row.addWidget(b_none)
        row.addStretch(1)
        v.addLayout(row)
        return w

    # ---- field list ----
    def _fill_fields(self) -> None:
        q = self.txt_search.text().strip().lower()
        cur = self.field.key if self.field else None
        self.lst_fields.blockSignals(True)
        self.lst_fields.clear()
        bold = self.lst_fields.font()
        bold.setBold(True)
        def match(f, g):
            return not q or q in f.label.lower() or q in g.lower()

        def add_group(parent_item, g, top_name):
            fs = [f for f in self.catalog if f.group == g and (match(f, g) or (q and q in top_name.lower()))]
            if not fs:
                return 0
            node = parent_item
            if g != top_name:                      # sub folder, e.g. Lab / Statimat
                node = QTreeWidgetItem([f"{g}  ({len(fs)})"])
                node.setForeground(0, QColor("#165C2B"))
                node.setFlags(Qt.ItemIsEnabled)
                parent_item.addChild(node)
            for f in fs:
                it = QTreeWidgetItem([f.label])
                it.setData(0, Qt.UserRole, f.key)
                node.addChild(it)
                if f.key == cur:
                    node.setExpanded(True)
                    parent_item.setExpanded(True)
                    self.lst_fields.setCurrentItem(it)
            node.setExpanded(bool(q) or node.isExpanded())
            return len(fs)

        for top, subs in te.group_tree(self.catalog):
            head = QTreeWidgetItem([top])
            head.setFont(0, bold)
            head.setForeground(0, QColor("#165C2B"))
            head.setFlags(Qt.ItemIsEnabled)
            self.lst_fields.addTopLevelItem(head)
            n = add_group(head, top, top) + sum(add_group(head, g, top) for g in subs)
            if not n:
                self.lst_fields.takeTopLevelItem(self.lst_fields.indexOfTopLevelItem(head))
                continue
            head.setText(0, f"{top}  ({n})")
            # collapsed until you search (Nutzerwunsch: otherwise too long)
            head.setExpanded(bool(q) or head.isExpanded())
        self.lst_fields.blockSignals(False)

    def _toggle_group(self, item, _col=0) -> None:
        if item is not None and item.childCount():
            item.setExpanded(not item.isExpanded())

    def _select_field(self, key: str) -> None:
        def walk(item):
            for j in range(item.childCount()):
                it = item.child(j)
                if it.data(0, Qt.UserRole) == key:
                    p = it.parent()
                    while p is not None:
                        p.setExpanded(True)
                        p = p.parent()
                    self.lst_fields.setCurrentItem(it)
                    return True
                if walk(it):
                    return True
            return False
        for i in range(self.lst_fields.topLevelItemCount()):
            if walk(self.lst_fields.topLevelItem(i)):
                return

    def _on_field(self, it, _prev=None) -> None:
        key = it.data(0, Qt.UserRole) if it is not None else None
        if not key:
            return
        self.field = self.ds.fields[key]
        f = self.field
        self.lbl_field.setText(f.label)
        self.lbl_scope.setText(f"{f.group}" + (f" · applies to {'any ply' if self.ply_scope == 'any' else self.ply_scope + ' plies'}"
                                                  if f.level == "yarn" else ""))
        vals = self.ds.field_values(f.key, self.others, self.ply_scope)
        if f.kind == "num":
            h = te.histogram(vals)
            self.hist.set_hist(h)
            self.hist.set_range(None, None)
            self.txt_lo.clear()
            self.txt_hi.clear()
            self.rb_all.setChecked(True)
            self.lst_values.clear()
            self._on_value_mode()
            self.lbl_axis.setText(
                f"{h['n']:,} values from {fmt_num(h['min'])} to {fmt_num(h['max'])}{' ' + f.unit if f.unit else ''}"
                f"  ·  bars {fmt_num(h['lo'])} – {fmt_num(h['hi'])}".replace(",", "'") if h["n"] else "No values")
            self.stack.setCurrentIndex(1)
        else:
            self.lst_cats.blockSignals(True)
            self.lst_cats.clear()
            for lab, n in te.category_counts(vals):
                it2 = QListWidgetItem(f"{lab}   ({n:,})".replace(",", "'"))
                it2.setData(Qt.UserRole, lab)
                it2.setFlags(it2.flags() | Qt.ItemIsUserCheckable)
                it2.setCheckState(Qt.Unchecked)
                self.lst_cats.addItem(it2)
            self.lst_cats.blockSignals(False)
            self.txt_cat_search.clear()
            is_time = f.key in te.TIME_KEYS
            self.period_box.setVisible(is_time)
            if is_time:
                labels = sorted(lab for lab, _n in te.category_counts(vals) if lab != te.NONE_LABEL)
                for c, empty in ((self.cmb_from, "(open)"), (self.cmb_to, "(open)")):
                    c.blockSignals(True)
                    c.clear()
                    c.addItem(empty, "")
                    for lab in labels:
                        c.addItem(lab, lab)
                    c.blockSignals(False)
            self.cmb_period.blockSignals(True)
            self.cmb_period.setCurrentIndex(0)
            self.cmb_period.blockSignals(False)
            self._on_period()
            self.stack.setCurrentIndex(2)
        self._update_hits()

    def _load_filter(self, flt: Dict[str, Any]) -> None:
        if self.field is None:
            return
        if self.field.kind == "num":
            lo, hi = flt.get("min"), flt.get("max")
            self.txt_lo.setText(fmt_num(lo))
            self.txt_hi.setText(fmt_num(hi))
            self.hist.set_range(lo, hi)
            if flt.get("only"):
                self.rb_pick.setChecked(True)
                self._fill_values({round(float(o), 6) for o in flt["only"]})
            elif flt.get("step"):
                self.cmb_step.blockSignals(True)
                self.cmb_step.setCurrentText(fmt_num(float(flt["step"])))
                self.cmb_step.blockSignals(False)
                self.rb_step.setChecked(True)
            self._on_value_mode()
        elif flt.get("period") and self.field.key in te.TIME_KEYS:
            self.cmb_period.setCurrentIndex(max(0, self.cmb_period.findData(flt["period"])))
            for c, k in ((self.cmb_from, "from"), (self.cmb_to, "to")):
                i = c.findData(str(flt.get(k) or ""))
                c.setCurrentIndex(i if i >= 0 else 0)
            self._on_period()
        else:
            wanted = set(flt.get("values") or [])
            self.lst_cats.blockSignals(True)
            for i in range(self.lst_cats.count()):
                it = self.lst_cats.item(i)
                it.setCheckState(Qt.Checked if it.data(Qt.UserRole) in wanted else Qt.Unchecked)
            self.lst_cats.blockSignals(False)
        self._update_hits()

    # ---- editing ----
    def _on_hist_drag(self, lo, hi) -> None:
        self.txt_lo.setText(fmt_num(lo))
        self.txt_hi.setText(fmt_num(hi))
        if self.rb_pick.isChecked():
            self._fill_values()
        self._hit_timer.start()

    def _on_num_typed(self, _t) -> None:
        self.hist.set_range(_parse(self.txt_lo.text()), _parse(self.txt_hi.text()))
        if self.rb_pick.isChecked():
            self._fill_values()
        self._hit_timer.start()

    def _period(self) -> str:
        if self.field is None or self.field.key not in te.TIME_KEYS:
            return ""
        return self.cmb_period.currentData() or ""

    def _on_period(self, _i=None) -> None:
        p = self._period()
        for wdg in (self.lbl_from, self.cmb_from, self.lbl_to, self.cmb_to):
            wdg.setVisible(p == "range")
        self.lst_cats.setEnabled(not p)
        self.txt_cat_search.setEnabled(not p)
        self._hit_timer.start()

    def _filter_cats(self, q: str) -> None:
        q = q.strip().lower()
        for i in range(self.lst_cats.count()):
            it = self.lst_cats.item(i)
            it.setHidden(bool(q) and q not in str(it.data(Qt.UserRole)).lower())

    def _tick_all(self, on: bool) -> None:
        self.lst_cats.blockSignals(True)
        for i in range(self.lst_cats.count()):
            self.lst_cats.item(i).setCheckState(Qt.Checked if on else Qt.Unchecked)
        self.lst_cats.blockSignals(False)
        self._update_hits()

    def current_filter(self) -> Optional[Dict[str, Any]]:
        f = self.field
        if f is None:
            return None
        if f.kind == "num":
            lo, hi = _parse(self.txt_lo.text()), _parse(self.txt_hi.text())
            if lo is not None and hi is not None and lo > hi:
                lo, hi = hi, lo
            flt: Dict[str, Any] = {"key": f.key, "min": lo, "max": hi}
            if self.rb_step.isChecked():
                step = _parse(self.cmb_step.currentText())
                if step and step > 0:
                    flt["step"] = step
            elif self.rb_pick.isChecked():
                picked = [self.lst_values.item(i).data(Qt.UserRole) for i in range(self.lst_values.count())
                          if self.lst_values.item(i).checkState() == Qt.Checked]
                if not picked:
                    return None
                flt["only"] = picked
            return flt
        p = self._period()
        if p:
            flt = {"key": f.key, "period": p}
            if p == "range":
                lo, hi = self.cmb_from.currentData() or None, self.cmb_to.currentData() or None
                if lo and hi and lo > hi:
                    lo, hi = hi, lo
                if not lo and not hi:
                    return None
                flt.update({"from": lo, "to": hi})
            return flt
        vals = [self.lst_cats.item(i).data(Qt.UserRole) for i in range(self.lst_cats.count())
                if self.lst_cats.item(i).checkState() == Qt.Checked]
        return {"key": f.key, "values": vals} if vals else None

    def _update_hits(self) -> None:
        flt = self.current_filter()
        if self.field is None:
            self.lbl_hits.setText("")
            self.btn_ok.setEnabled(False)
            return
        base = self.ds.apply(self.others, self.ply_scope).count
        if flt is None:
            self.lbl_hits.setText(f"Tick at least one value. Your other filters leave {base:,} trials.".replace(",", "'"))
            self.btn_ok.setEnabled(False)
            return
        n = self.ds.apply(self.others + [flt], self.ply_scope).count
        what = te.describe_filter(self.field, flt)
        nf = lambda v: f"{v:,}".replace(",", "'")
        self.lbl_hits.setText(f"<b>{nf(n)} trials</b> with {html.escape(what)} (of {nf(base)} left by your other filters)")
        self.btn_ok.setEnabled(True)

    def _accept(self) -> None:
        flt = self.current_filter()
        if flt is None:
            return
        self.result_filter = flt
        self.accept()


def _parse(t: str) -> Optional[float]:
    t = (t or "").strip().replace(",", ".")
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        return None
