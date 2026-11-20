# ui/copy_trials_dialog.py
""""Copy trials" dialog for Show Experiment (Nutzerwunsch 2026-10-15).

Replaces the old From/To spin-box dialog. One page, three steps:

1. Which trials? - checklist with each trial's key settings (Shift+click
   checks/unchecks a whole range).
2. How often? - number of copies + order (repeat the block / each trial in
   a row), with a one-line preview.
3. Which lab machines? - one checkbox per lab machine the chosen trials
   have rows in (all ticked = as before); unticked ones get no empty lab
   row in the copies (Nutzerwunsch 2026-11-20).
4. Result - one row per new trial, pre-filled from its source trial; the
   values can be changed before copying (changed cells are highlighted).
   Only trial-wide fields are offered (plus OF Core / OF Effect on ATY,
   which live on the Core/Effect plies); per-ply values stay in the table
   and in Manage plies. Measured tensions before/after the jet are never
   shown - copies start with them empty.

The dialog only collects the plan (get_plan()); writing to the DB stays in
ShowExperimentScreen._copy_trials_with_plan() (db/trial_actions.copy_trials).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog,
    QGridLayout, QHBoxLayout, QHeaderView, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QRadioButton, QSpinBox, QTableWidget, QTableWidgetItem,
    QVBoxLayout,
)

from db.trial_reference import format_trial_number

# Field list, source values, value rules: db/trial_copy.py (Qt-free, shared
# with the web app) - re-exported here unchanged.
from db.trial_copy import (  # noqa: E402,F401
    _DEFAULT_COLS, _RE_FLOAT, _RE_FLOAT_2DP, _RE_INT, _SKIP_COLS, _UNIT_RE, NOT_AVAILABLE, VARIES,
    YARN_USE_CORE, YARN_USE_EFFECT, CopyField, _same, _unique_choices, build_copy_fields,
    display_value, load_source_values, normalize_value, summary_value,
)

_CHANGED_BG = QColor("#FFF4D6")
_CHANGED_BORDER_TIP = "Changed - differs from the source trial"


# ── dialog ───────────────────────────────────────────────────────────────

class CopyTrialsDialog(QDialog):
    """trials: [{"id": int, "vno": int}] in display order (real trials only).
    labs: db/trial_actions.lab_tables_of_trials(trial ids) - the lab machines a copy can get."""

    ORDER_BLOCK, ORDER_ROW = "block", "row"

    def __init__(self, parent, trials: Sequence[Dict], fields: Sequence[CopyField],
                 source_values: Dict[int, Dict[str, Any]], next_number: int,
                 preselected: Sequence[int] = (), labs: Sequence[Dict] = ()):
        super().__init__(parent)
        self.setWindowTitle("Copy trials")
        self.setMinimumSize(760, 620)
        self.resize(1080, 700)
        self._trials = list(trials)
        self._fields = list(fields)
        self._src = source_values
        self._next_number = int(next_number)
        self._labs = list(labs)
        self._lab_checks: Dict[str, QCheckBox] = {}
        # edits survive rebuilds: (src_trial_id, n-th copy of that trial) -> {field.key: value}
        self._edits: Dict[Tuple[int, int], Dict[str, Any]] = {}
        self._plan_keys: List[Tuple[int, int]] = []
        self._last_toggled_row: Optional[int] = None
        self._building = False
        self._build_ui(set(int(t) for t in preselected))
        self._rebuild_result()

    # ── UI ──
    def _section(self, lay, num: str, text: str):
        lbl = QLabel(f"<b>{num}&nbsp;&nbsp;{text}</b>")
        lbl.setStyleSheet("font-size: 13px; margin-top: 6px;")
        lay.addWidget(lbl)

    def _build_ui(self, preselected: set):
        lay = QVBoxLayout(self)

        # 1 Which trials?
        head = QHBoxLayout()
        self._section(head, "1", "Which trials?")
        head.addStretch(1)
        b_all, b_none = QPushButton("All"), QPushButton("None")
        b_all.clicked.connect(lambda: self._check_all(True))
        b_none.clicked.connect(lambda: self._check_all(False))
        head.addWidget(b_all)
        head.addWidget(b_none)
        lay.addLayout(head)
        self.lst_trials = QListWidget()
        self.lst_trials.setSelectionMode(QAbstractItemView.NoSelection)
        self.lst_trials.setMaximumHeight(170)
        summary_fields = [f for f in self._fields if f.default]
        for t in self._trials:
            tid = int(t["id"])
            parts = [summary_value(f, self._src.get(tid, {}).get(f.key)) for f in summary_fields]
            parts = [p for p in parts if p]
            it = QListWidgetItem(f"{format_trial_number(t['vno'])}    " + "  ·  ".join(parts))
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if tid in preselected else Qt.Unchecked)
            it.setData(Qt.UserRole, tid)
            self.lst_trials.addItem(it)
        self.lst_trials.itemChanged.connect(self._on_trial_toggled)
        lay.addWidget(self.lst_trials)
        hint = QLabel("Tip: Shift+click a checkbox to check or uncheck a whole range.")
        hint.setStyleSheet("color: #666;")
        lay.addWidget(hint)

        # 2 How often?
        self._section(lay, "2", "How often?")
        row = QHBoxLayout()
        self.spn_copies = QSpinBox()
        self.spn_copies.setRange(1, 50)
        self.spn_copies.setValue(1)
        self.spn_copies.valueChanged.connect(self._rebuild_result)
        row.addWidget(self.spn_copies)
        row.addWidget(QLabel("×"))
        row.addSpacing(16)
        self.rb_block = QRadioButton("Repeat the block")
        self.rb_row = QRadioButton("Each trial in a row")
        self.rb_block.setChecked(True)
        grp = QButtonGroup(self)
        grp.addButton(self.rb_block)
        grp.addButton(self.rb_row)
        self.rb_block.toggled.connect(self._rebuild_result)
        row.addWidget(self.rb_block)
        row.addWidget(self.rb_row)
        row.addSpacing(12)
        self.lbl_order = QLabel()
        self.lbl_order.setStyleSheet("color: #555;")
        row.addWidget(self.lbl_order)
        row.addStretch(1)
        lay.addLayout(row)

        # 3 Which lab machines?
        self._section(lay, "3", "Which lab machines do the copies get?")
        lab_grid = QGridLayout()
        lab_grid.setHorizontalSpacing(18)
        for i, lab in enumerate(self._labs):
            cb = QCheckBox(lab["title"])
            cb.setChecked(True)
            self._lab_checks[lab["table"]] = cb
            lab_grid.addWidget(cb, i // 5, i % 5)
        lay.addLayout(lab_grid)
        self.lbl_labs = QLabel()
        self.lbl_labs.setStyleSheet("color: #666;")
        self.lbl_labs.setWordWrap(True)
        lay.addWidget(self.lbl_labs)

        # 4 Result
        head3 = QHBoxLayout()
        self._section(head3, "4", "Result - you can change values before copying")
        head3.addStretch(1)
        self.chk_all_fields = QCheckBox("Show all fields")
        self.chk_all_fields.toggled.connect(self._apply_column_visibility)
        head3.addWidget(self.chk_all_fields)
        lay.addLayout(head3)
        self.tbl = QTableWidget(0, 2 + len(self._fields))
        self.tbl.setHorizontalHeaderLabels(["New", "From"] + [f.label for f in self._fields])
        self.tbl.verticalHeader().setVisible(False)
        hh = self.tbl.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Interactive)
        fm = self.tbl.fontMetrics()
        self.tbl.setColumnWidth(0, 56)
        self.tbl.setColumnWidth(1, 56)
        for fi, f in enumerate(self._fields):
            # Fixed widths: ResizeToContents would size dropdowns to the
            # longest jet name and push the other columns out of view.
            w = 160 if f.choices else max(80, fm.horizontalAdvance(f.label) + 20)
            self.tbl.setColumnWidth(2 + fi, min(w, 150) if not f.choices else w)
        self.tbl.itemChanged.connect(self._on_item_changed)
        lay.addWidget(self.tbl, 1)
        self._apply_column_visibility()

        info = QLabel("<b>Copied:</b> machine settings and plies.&nbsp;&nbsp; "
                      "<b>Empty:</b> lab values and yarn tensions before/after the jet.")
        info.setStyleSheet("color: #444;")
        lay.addWidget(info)

        btns = QHBoxLayout()
        btns.addStretch(1)
        b_cancel = QPushButton("Cancel")
        b_cancel.clicked.connect(self.reject)
        self.btn_copy = QPushButton()
        self.btn_copy.setDefault(True)
        self.btn_copy.clicked.connect(self.accept)
        btns.addWidget(b_cancel)
        btns.addWidget(self.btn_copy)
        lay.addLayout(btns)

    # ── step 1 ──
    def _check_all(self, on: bool):
        self.lst_trials.blockSignals(True)
        for i in range(self.lst_trials.count()):
            self.lst_trials.item(i).setCheckState(Qt.Checked if on else Qt.Unchecked)
        self.lst_trials.blockSignals(False)
        self._rebuild_result()

    def _on_trial_toggled(self, item: QListWidgetItem):
        row = self.lst_trials.row(item)
        if (QApplication.keyboardModifiers() & Qt.ShiftModifier) and self._last_toggled_row is not None:
            lo, hi = sorted((row, self._last_toggled_row))
            self.lst_trials.blockSignals(True)
            for i in range(lo, hi + 1):
                self.lst_trials.item(i).setCheckState(item.checkState())
            self.lst_trials.blockSignals(False)
        self._last_toggled_row = row
        self._rebuild_result()

    def _selected_trials(self) -> List[Dict]:
        out = []
        for i in range(self.lst_trials.count()):
            if self.lst_trials.item(i).checkState() == Qt.Checked:
                out.append(self._trials[i])
        return out

    # ── step 2 + 3 ──
    def _plan_sources(self) -> List[Dict]:
        sel = self._selected_trials()
        n = self.spn_copies.value()
        if self.rb_block.isChecked():
            return [t for _ in range(n) for t in sel]
        return [t for t in sel for _ in range(n)]

    def _update_labs(self, sel: List[Dict]) -> None:
        """Only the lab machines of the chosen trials are offered; "n of m" when not all have it."""
        ids = {int(t["id"]) for t in sel}
        shown = 0
        for lab in self._labs:
            cb = self._lab_checks[lab["table"]]
            n = sum(1 for t in lab["trials"] if int(t) in ids)
            cb.setVisible(n > 0)
            shown += n > 0
            cb.setText(lab["title"] if n == len(ids) else f"{lab['title']}  ({n} of {len(ids)})")
        self.lbl_labs.setText(
            "Ticked = the copy gets an empty row of this lab machine (like the source trial). "
            "Untick what you will not measure." if shown else ("The chosen trials have no lab machines." if ids else ""))

    def get_lab_tables(self) -> Optional[List[str]]:
        """Lab tables the copies get; None = all ticked (= as before)."""
        if all(cb.isChecked() for cb in self._lab_checks.values()):
            return None
        return [t for t, cb in self._lab_checks.items() if cb.isChecked()]

    def _rebuild_result(self, *_):
        sel = self._selected_trials()
        if hasattr(self, "lbl_labs"):
            self._update_labs(sel)
        n = self.spn_copies.value()
        if len(sel) >= 2:
            a, b = (format_trial_number(sel[0]["vno"]), format_trial_number(sel[1]["vno"]))
            self.lbl_order.setText(f"{a} {b} | {a} {b} …" if self.rb_block.isChecked() else f"{a} {a} | {b} {b} …")
        else:
            self.lbl_order.setText("")

        sources = self._plan_sources()
        self._building = True
        self.tbl.setRowCount(0)
        self._plan_keys = []
        occurrences: Dict[int, int] = {}
        for r, t in enumerate(sources):
            tid = int(t["id"])
            occ = occurrences.get(tid, 0)
            occurrences[tid] = occ + 1
            key = (tid, occ)
            self._plan_keys.append(key)
            self.tbl.insertRow(r)
            for c, txt in ((0, f"V{self._next_number + r}"), (1, format_trial_number(t["vno"]))):
                it = QTableWidgetItem(txt)
                it.setFlags(Qt.ItemIsEnabled)
                self.tbl.setItem(r, c, it)
            for fi, f in enumerate(self._fields):
                self._fill_cell(r, 2 + fi, f, key)
        self._building = False
        self._apply_column_visibility()
        total = len(sources)
        self.btn_copy.setText(f"Copy {total} trial{'s' if total != 1 else ''}")
        self.btn_copy.setEnabled(total > 0)

    def _value_for(self, key: Tuple[int, int], f: CopyField) -> Any:
        edits = self._edits.get(key, {})
        if f.key in edits:
            return edits[f.key]
        return self._src.get(key[0], {}).get(f.key)

    def _fill_cell(self, r: int, c: int, f: CopyField, key: Tuple[int, int]):
        src_val = self._src.get(key[0], {}).get(f.key)
        val = self._value_for(key, f)
        changed = f.key in self._edits.get(key, {})
        if src_val is NOT_AVAILABLE:
            it = QTableWidgetItem("")
            it.setFlags(Qt.NoItemFlags)
            it.setToolTip("This trial has no plies of this kind.")
            self.tbl.setItem(r, c, it)
            return
        if f.choices:
            cmb = QComboBox()
            cmb.addItem("", None)
            for k, name in f.choices:
                cmb.addItem(name, k)
            idx = 0
            if val not in (None, "", VARIES):
                try:
                    found = cmb.findData(int(val))
                    idx = found if found >= 0 else 0
                except (TypeError, ValueError):
                    idx = 0
            cmb.setCurrentIndex(idx)
            if changed:
                cmb.setStyleSheet(f"QComboBox {{ background: {_CHANGED_BG.name()}; }}")
                cmb.setToolTip(_CHANGED_BORDER_TIP)
            cmb.currentIndexChanged.connect(
                lambda _i, cb=cmb, k=key, fld=f: self._on_combo_changed(cb, k, fld))
            self.tbl.setCellWidget(r, c, cmb)
            return
        it = QTableWidgetItem(display_value(f, val))
        it.setData(Qt.UserRole, (key, f.key))
        if val is VARIES and not changed:
            it.setForeground(QColor("#888"))
            it.setToolTip("The plies of the source trial have different values - "
                          "they are kept unless you enter a value here.")
        if changed:
            it.setBackground(_CHANGED_BG)
            it.setToolTip(_CHANGED_BORDER_TIP)
        self.tbl.setItem(r, c, it)

    def _record_edit(self, key, f: CopyField, value):
        src_val = self._src.get(key[0], {}).get(f.key)
        edits = self._edits.setdefault(key, {})
        if _same(f, value, src_val):
            edits.pop(f.key, None)
        else:
            edits[f.key] = value

    def _on_combo_changed(self, cmb: QComboBox, key, f: CopyField):
        if self._building:
            return
        self._record_edit(key, f, cmb.currentData())
        changed = f.key in self._edits.get(key, {})
        cmb.setStyleSheet(f"QComboBox {{ background: {_CHANGED_BG.name()}; }}" if changed else "")
        cmb.setToolTip(_CHANGED_BORDER_TIP if changed else "")

    def _on_item_changed(self, item: QTableWidgetItem):
        if self._building or item.column() < 2:
            return
        data = item.data(Qt.UserRole)
        if not data:
            return
        key, fkey = data
        f = next(x for x in self._fields if x.key == fkey)
        text = item.text()
        src_val = self._src.get(key[0], {}).get(f.key)
        if src_val is VARIES and text == "div." and f.key not in self._edits.get(key, {}):
            return
        norm = normalize_value(f.rule, text)
        self._building = True
        if norm is None:
            QMessageBox.warning(self, "Copy trials", f"'{text}' is not a valid value for {f.label}.")
            item.setText(display_value(f, self._value_for(key, f)))
            self._building = False
            return
        self._record_edit(key, f, norm if norm != "" else None)
        changed = f.key in self._edits.get(key, {})
        item.setText(display_value(f, self._value_for(key, f)))
        item.setBackground(_CHANGED_BG if changed else QColor(Qt.transparent))
        item.setForeground(QColor("#000"))
        item.setToolTip(_CHANGED_BORDER_TIP if changed else "")
        self._building = False

    def _apply_column_visibility(self, *_):
        show_all = self.chk_all_fields.isChecked()
        for fi, f in enumerate(self._fields):
            self.tbl.setColumnHidden(2 + fi, not (show_all or f.default))

    # ── result ──
    def get_plan(self) -> List[Tuple[int, Dict[str, Any]]]:
        """[(source_trial_id, {field.key: new value (None = empty)}), ...] in
        the order the copies are created. Only changed fields are listed."""
        return [(key[0], dict(self._edits.get(key, {}))) for key in self._plan_keys]
