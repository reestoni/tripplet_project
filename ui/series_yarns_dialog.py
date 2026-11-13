# ui/series_yarns_dialog.py
"""Yarns of a whole trial series in one table (Nutzerwunsch 2026-10-16,
replaces the old per-trial "Manage Plies" dialog).

    Ply   | Yarn              | Use | V1 | V2 | V3 ...
    Ply 1 | PES 167f48 DTY  v | -   | 1x | 1x | 2x
    Ply 2 | PA 78f68        v | -   | 1x | -  | 1x

- Click the yarn of a ply -> search a yarn -> the whole ply gets it (all
  trials, values stay; a linked spool is cleared - it was a spool of the
  old yarn). No more add + remove and no "Yarn Conflict".
- Click a trial cell: ply on/off for that trial; digit keys or right-click
  set the number of ends (one tblTrialSettings row per end).
- "+ Add ply" (catalog yarn) / "+ Trial output" (half-finished product of
  another trial, shadow yarn of screen_create_experiment) add a row that is
  on for every trial.
- Nothing is written until "Apply": a summary is shown, then everything is
  written in one transaction and logged (db/change_log.py, source "plies").

Data: tblTrialSettings rows (TrialID, YarnID, Ply, YarnUseID). A row of the
table is one (Ply, YarnID, YarnUseID) combination. Series rule (lab decision,
kept on purpose although it is not "logical"): a yarn always has the SAME
ply number in a series. So the same yarn as "Core" and as "Effect" is two
rows "Ply 1" with different uses; "+ Add ply" with a yarn of the series puts
it into its existing ply; changing the yarn of a ply changes all its rows and
refuses a yarn that already has another ply number. Old series where one ply
has different yarns show one row per yarn (amber mark), so nothing gets
mixed up. Every trial keeps at least one ply -
except reference samples (db/trial_reference.py): they may have no yarn at
all (a new one is created without plies), new plies are not switched on for
them automatically, and their columns are amber like in Show Experiment.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout,
)

from ui.widgets.friendly_error import show_error
from ui.widgets.yarn_colour import colour_icon, colour_tooltip, load_yarn_colours

# Data, plan() / apply_plan(), yarn search: db/series_yarns.py (Qt-free,
# shared with the web app) - re-exported here unchanged.
from db.series_yarns import (  # noqa: E402,F401
    MAX_ENDS, PlyRow, State, apply_plan, describe, duplicate_rows, filter_yarns, load_state, load_yarns,
    mixed_plies, next_ply_label, plan, ply_number, ply_of_yarn, trials_without_ply,
)

CHANGED_BG = QColor("#FFF3B0")   # same yellow as unsaved cells in Show Experiment
OFF_FG = QColor("#9a9a9a")


class YarnPickerDialog(QDialog):
    """Search field + list; yarns of this series first."""

    def __init__(self, parent, yarns: List[Dict[str, Any]], series_yarn_ids: List[int], title: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(460, 520)
        self._yarns = yarns
        self._series = [i for i in series_yarn_ids if i is not None]
        self.selected: Optional[Dict[str, Any]] = None
        lay = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search yarn - name, titer, material…  e.g. 167 dty")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._fill)
        self.search.returnPressed.connect(self._take_first)
        lay.addWidget(self.search)
        self.lst = QListWidget()
        self.lst.itemDoubleClicked.connect(self._take)
        self.lst.itemActivated.connect(self._take)
        lay.addWidget(self.lst, 1)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(lambda: self._take(self.lst.currentItem()))
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)
        self._fill("")
        self.search.setFocus()

    def _head(self, text: str) -> None:
        it = QListWidgetItem(text)
        it.setFlags(Qt.NoItemFlags)
        f = QFont(it.font())
        f.setBold(True)
        it.setFont(f)
        it.setForeground(QColor("#565656"))
        self.lst.addItem(it)

    def _fill(self, text: str) -> None:
        self.lst.clear()
        hits = filter_yarns(self._yarns, text)
        in_series = [y for y in hits if y["id"] in self._series]
        rest = [y for y in hits if y["id"] not in self._series]
        for head, group in (("In this series", in_series), ("All yarns", rest)):
            if not group:
                continue
            if in_series:
                self._head(head)
            for y in group:
                it = QListWidgetItem(colour_icon(y.get("colour")), y["name"])
                it.setToolTip(colour_tooltip(y.get("colour")))
                it.setData(Qt.UserRole, y)
                self.lst.addItem(it)
        if not hits:
            self._head("No yarn found")
        for i in range(self.lst.count()):
            if self.lst.item(i).flags() & Qt.ItemIsEnabled:
                self.lst.setCurrentRow(i)
                break

    def _take_first(self) -> None:
        self._take(self.lst.currentItem())

    def _take(self, it) -> None:
        if it is None or not (it.flags() & Qt.ItemIsEnabled):
            return
        self.selected = it.data(Qt.UserRole)
        self.accept()


# ── the dialog ────────────────────────────────────────────────────────────
class _GridTable(QTableWidget):
    """Digit keys set the ends of the selected trial cells (0 = off)."""

    def __init__(self, dialog):
        super().__init__()
        self._dlg = dialog

    def keyPressEvent(self, e):
        t = e.text()
        if t.isdigit() and self._dlg.editable:
            self._dlg.set_ends_selected(int(t))
            return
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace) and self._dlg.editable:
            self._dlg.set_ends_selected(0)
            return
        super().keyPressEvent(e)


COL_PLY, COL_YARN, COL_USE, COL_FIRST_TRIAL = 0, 1, 2, 3


class SeriesYarnsDialog(QDialog):
    def __init__(self, parent, series_pk: int, series_label: str = "", editable: bool = True,
                 focus_trial_id: Optional[int] = None):
        super().__init__(parent)
        self.series_pk = int(series_pk)
        self.editable = bool(editable)
        self.setWindowTitle("Yarns" + (f" – {series_label}" if series_label else ""))
        self.resize(1000, 520)
        self.before = load_state(self.series_pk)
        self.state = copy.deepcopy(self.before)
        self._yarns: Optional[List[Dict[str, Any]]] = None
        self._colours, _ = load_yarn_colours()
        self._use_list: List[Tuple[Any, str]] = [(None, "—")]
        try:
            from db.connection import fetch_all
            self._use_list += [(int(r["ID"]), str(r.get("Name") or "")) for r in
                               fetch_all("SELECT ID, Name FROM tblYarnUse ORDER BY ID")]
        except Exception:
            pass

        lay = QVBoxLayout(self)
        hint = QLabel(
            "Click a <b>yarn</b> to change it for the whole ply. Click a <b>trial cell</b> to switch the ply on "
            "or off for that trial; type a number (1–9) for the ends. Nothing is saved until <b>Apply</b>."
            if self.editable else "Read only - you need write access to change yarns.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#444;")
        lay.addWidget(hint)

        self.tbl = _GridTable(self)
        self.tbl.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl.customContextMenuRequested.connect(self._context_menu)
        self.tbl.cellClicked.connect(self._on_cell_clicked)
        lay.addWidget(self.tbl, 1)

        row = QHBoxLayout()
        self.btn_add = QPushButton("+ Add ply")
        self.btn_add.setToolTip("Add a ply with a yarn from the catalog - on for every trial")
        self.btn_add.clicked.connect(self._add_ply)
        self.btn_trial = QPushButton("+ Trial output")
        self.btn_trial.setToolTip("Use the output of an existing trial (e.g. from another machine) as a ply")
        self.btn_trial.clicked.connect(self._add_trial_output)
        for b in (self.btn_add, self.btn_trial):
            b.setEnabled(self.editable)
            row.addWidget(b)
        self.lbl_changes = QLabel()
        self.lbl_changes.setStyleSheet("color:#565656; padding-left:12px;")
        row.addWidget(self.lbl_changes, 1)
        self.btn_cancel = QPushButton("Cancel" if self.editable else "Close")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_apply = QPushButton("Apply")
        self.btn_apply.setDefault(True)
        self.btn_apply.clicked.connect(self._apply)
        self.btn_apply.setVisible(self.editable)
        row.addWidget(self.btn_cancel)
        row.addWidget(self.btn_apply)
        lay.addLayout(row)

        self._render()
        if focus_trial_id is not None:
            for c, (tid, _v, _l) in enumerate(self.state.trials):
                if tid == focus_trial_id:
                    self.tbl.scrollToItem(self.tbl.item(0, COL_FIRST_TRIAL + c) or self.tbl.item(0, 0))
                    self.tbl.setCurrentCell(0, COL_FIRST_TRIAL + c)
                    break

    # ── rendering ─────────────────────────────────────────────────────
    def _render(self) -> None:
        st = self.state
        self.tbl.clear()
        self.tbl.setColumnCount(COL_FIRST_TRIAL + len(st.trials))
        self.tbl.setRowCount(len(st.rows))
        self.tbl.setHorizontalHeaderLabels(["Ply", "Yarn", "Use"] + [lbl for _t, _v, lbl in st.trials])
        for c, (tid, _v, _l) in enumerate(st.trials):
            if tid in st.refs:
                h = self.tbl.horizontalHeaderItem(COL_FIRST_TRIAL + c)
                h.setForeground(QColor("#5a4500"))
                h.setToolTip("Reference sample - may have no yarn at all")
        hh = self.tbl.horizontalHeader()
        hh.setSectionResizeMode(COL_YARN, QHeaderView.Interactive)
        self.tbl.setColumnWidth(COL_PLY, 70)
        self.tbl.setColumnWidth(COL_YARN, 260)
        self.tbl.setColumnWidth(COL_USE, 110)
        for c in range(COL_FIRST_TRIAL, self.tbl.columnCount()):
            self.tbl.setColumnWidth(c, 52)
        mixed = mixed_plies(st.rows)
        n_old = len(self.before.rows)
        # shown sorted by ply (Ply 1 Core right above Ply 1 Effect); st.rows keeps
        # its order because plan() matches rows to `before` by position
        self._order = sorted(range(len(st.rows)), key=lambda i: (
            ply_number(st.rows[i].ply), st.rows[i].ply, st.rows[i].yarn_name, i))
        for vr, r in enumerate(self._order):
            pr = st.rows[r]
            old = self.before.rows[r] if r < n_old else None
            it = QTableWidgetItem(pr.ply)
            it.setFlags(Qt.ItemIsEnabled)
            if pr.ply in mixed:
                it.setBackground(QColor("#FFE6B3"))
                it.setToolTip("Old data: this ply has different yarns in different trials - one row per yarn/use")
            self.tbl.setItem(vr, COL_PLY, it)

            changed_yarn = old is None or old.yarn_id != pr.yarn_id
            b = QPushButton(f"{pr.yarn_name}  ▾" if self.editable else pr.yarn_name)
            b.setFlat(True)
            b.setStyleSheet("QPushButton{text-align:left;padding:2px 6px;"
                            + ("background:#FFF3B0;" if changed_yarn else "") + "}"
                            "QPushButton:hover{background:#e8f0fb;}")
            colour = self._colours.get(pr.yarn_id) if pr.yarn_id is not None else None
            b.setIcon(colour_icon(colour))
            b.setToolTip(("Change the yarn of this ply for all trials" if self.editable else pr.yarn_name)
                         + "\n" + colour_tooltip(colour))
            b.setEnabled(self.editable)
            b.clicked.connect(lambda _=False, rr=r: self._change_yarn(rr))
            self.tbl.setCellWidget(vr, COL_YARN, b)

            cb = QComboBox()
            for uid, name in self._use_list:
                cb.addItem(name, uid)
            idx = cb.findData(pr.use_id)
            cb.setCurrentIndex(max(0, idx))
            cb.setEnabled(self.editable)
            if old is not None and old.use_id != pr.use_id:
                cb.setStyleSheet("QComboBox{background:#FFF3B0;}")
            cb.currentIndexChanged.connect(lambda _i, rr=r, w=cb: self._set_use(rr, w.currentData()))
            self.tbl.setCellWidget(vr, COL_USE, cb)

            for c, (tid, _v, label) in enumerate(st.trials):
                n = pr.ends.get(tid, 0)
                cell = QTableWidgetItem(f"{n}×" if n else "–")
                cell.setTextAlignment(Qt.AlignCenter)
                cell.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                if not n:
                    cell.setForeground(OFF_FG)
                if tid in st.refs:
                    cell.setBackground(QColor("#FFF4D6"))  # reference sample (amber, as in Show Experiment)
                if n != (old.ends.get(tid, 0) if old else 0):
                    cell.setBackground(CHANGED_BG)
                cell.setToolTip(f"{label} · {pr.ply}: " + (f"{n} end" + ("s" if n > 1 else "") if n else "not used"))
                self.tbl.setItem(vr, COL_FIRST_TRIAL + c, cell)
        self._update_changes()

    def _update_changes(self) -> None:
        ops = plan(self.before, self.state)
        self.lbl_changes.setText(f"{len(describe(ops))} change(s) not applied yet" if ops else "")
        self.btn_apply.setEnabled(bool(ops) and self.editable)

    # ── editing ───────────────────────────────────────────────────────
    def _trial_cells(self) -> List[Tuple[int, int]]:
        out = []
        for idx in self.tbl.selectedIndexes():
            if idx.column() >= COL_FIRST_TRIAL:
                out.append((self._order[idx.row()], idx.column() - COL_FIRST_TRIAL))
        return out

    def _set_ends(self, cells, n: int) -> None:
        n = max(0, min(MAX_ENDS, int(n)))
        for r, c in cells:
            tid = self.state.trials[c][0]
            self.state.rows[r].ends[tid] = n
        self._render()
        self._restore_selection(cells)

    def _restore_selection(self, cells) -> None:
        from PySide6.QtCore import QItemSelectionModel
        sm = self.tbl.selectionModel()
        for r, c in cells:
            sm.select(self.tbl.model().index(self._order.index(r), COL_FIRST_TRIAL + c), QItemSelectionModel.Select)

    def set_ends_selected(self, n: int) -> None:
        cells = self._trial_cells()
        if cells:
            self._set_ends(cells, n)

    def _on_cell_clicked(self, vr: int, col: int) -> None:
        if not self.editable or col < COL_FIRST_TRIAL:
            return
        r = self._order[vr]
        from PySide6.QtWidgets import QApplication
        if QApplication.keyboardModifiers() & (Qt.ControlModifier | Qt.ShiftModifier):
            return  # selecting several cells
        tid = self.state.trials[col - COL_FIRST_TRIAL][0]
        cur = self.state.rows[r].ends.get(tid, 0)
        if cur:
            new = 0
        else:
            old = self.before.rows[r] if r < len(self.before.rows) else None
            new = (old.ends.get(tid, 0) if old else 0) or 1
        self._set_ends([(r, col - COL_FIRST_TRIAL)], new)

    def _context_menu(self, pos) -> None:
        if not self.editable:
            return
        idx = self.tbl.indexAt(pos)
        if not idx.isValid():
            return
        menu = QMenu(self)
        r = self._order[idx.row()]
        if idx.column() >= COL_FIRST_TRIAL:
            cells = self._trial_cells() or [(r, idx.column() - COL_FIRST_TRIAL)]
            for n in range(0, 6):
                a = menu.addAction("Not used" if n == 0 else f"{n} end" + ("s" if n > 1 else ""))
                a.triggered.connect(lambda _=False, nn=n, cc=cells: self._set_ends(cc, nn))
            menu.addSeparator()
        all_cells = [(r, c) for c in range(len(self.state.trials))]  # state row index
        refs = self.state.refs
        menu.addAction(f"{self.state.rows[r].ply}: use in all trials (1 end)").triggered.connect(
            lambda: self._set_ends([(rr, c) for rr, c in all_cells
                                    if self.state.trials[c][0] not in refs
                                    and not self.state.rows[rr].ends.get(self.state.trials[c][0], 0)], 1))
        menu.addAction(f"Remove {self.state.rows[r].ply} from all trials").triggered.connect(
            lambda: self._set_ends(all_cells, 0))
        menu.addAction("Change yarn…").triggered.connect(lambda: self._change_yarn(r))
        menu.exec(self.tbl.viewport().mapToGlobal(pos))

    def _pick_yarn(self, title: str) -> Optional[Dict[str, Any]]:
        if self._yarns is None:
            try:
                self._yarns = load_yarns()
            except Exception as e:
                show_error(self, "Yarns", "The list of yarns could not be loaded.", e)
                return None
        dlg = YarnPickerDialog(self, self._yarns, [r.yarn_id for r in self.state.rows], title)
        return dlg.selected if dlg.exec() == QDialog.Accepted else None

    def _use_name(self, use_id) -> str:
        return dict(self._use_list).get(use_id, "—") if use_id is not None else "—"

    def _change_yarn(self, r: int) -> None:
        """New yarn for the ply - for all its rows (all uses), because a yarn
        has one ply number per series."""
        pr = self.state.rows[r]
        y = self._pick_yarn(f"Yarn for {pr.ply}")
        if y is None or y["id"] == pr.yarn_id:
            return
        other_ply = ply_of_yarn([o for o in self.state.rows if o.ply != pr.ply], y["id"])
        if other_ply:
            QMessageBox.information(
                self, "Change yarn",
                f"{y['name']} is already {other_ply} in this series - a yarn always keeps its ply number.\n\n"
                f"To use it with another yarn use, add it with + Add ply (it goes to {other_ply}).")
            return
        ply, old_yarn = pr.ply, pr.yarn_id  # pr itself changes in the loop
        for o in self.state.rows:
            if o.ply == ply and o.yarn_id == old_yarn:
                o.yarn_id, o.yarn_name = y["id"], y["name"]
        self._render()

    def _set_use(self, r: int, use_id) -> None:
        pr = self.state.rows[r]
        if pr.use_id == use_id:
            return
        taken = [o for o in self.state.rows if o is not pr and o.ply == pr.ply and o.yarn_id == pr.yarn_id
                 and o.use_id == use_id]
        if taken:
            QMessageBox.information(
                self, "Yarn use",
                f"{pr.ply} ({pr.yarn_name}) already has a row with use {self._use_name(use_id)}. "
                "Use the number of ends in that row instead.")
            self._render()  # back to the old value in the dropdown
            return
        pr.use_id = use_id
        self._render()

    def _new_row(self, yarn_id: int, name: str) -> None:
        """New row for all trials. A yarn that is already in the series keeps
        its ply number (series rule) - the new row is the same ply with
        another yarn use, e.g. Ply 1 "Core" + Ply 1 "Effect"."""
        same = [r for r in self.state.rows if r.yarn_id == yarn_id]
        label = same[0].ply if same else next_ply_label(self.state.rows)
        if same:
            where = ", ".join(self._use_name(r.use_id) for r in same)
            if QMessageBox.question(
                    self, "Add ply",
                    f"{name} is already {label} in this series (use: {where}).\n\nA yarn always keeps its ply "
                    f"number - add it to {label} again with another yarn use? Then choose the use in the Use "
                    "column.\n\n(For more ends with the same use, type the number in the trial cells instead.)",
                    QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Yes) != QMessageBox.Yes:
                return
        pr = PlyRow(label, yarn_id, name,
                    ends={tid: (0 if tid in self.state.refs else 1) for tid, _v, _l in self.state.trials})
        self.state.rows.append(pr)
        self._render()
        vr = self._order.index(len(self.state.rows) - 1)
        self.tbl.scrollToItem(self.tbl.item(vr, COL_PLY))
        if same:
            cb = self.tbl.cellWidget(vr, COL_USE)
            if cb is not None:
                cb.setFocus()
                cb.showPopup()

    def _add_ply(self) -> None:
        y = self._pick_yarn("Add ply")
        if y is not None:
            self._new_row(y["id"], y["name"])

    def _add_trial_output(self) -> None:
        from ui.widgets.trial_picker import TrialPickerDialog
        dlg = TrialPickerDialog(parent=self)
        if dlg.exec() != QDialog.Accepted or dlg.selected_trial_id() is None:
            return
        try:
            from ui.screen_create_experiment import get_or_create_shadow_yarn
            from db.connection import fetch_all
            yid = get_or_create_shadow_yarn(dlg.selected_trial_id())
            if yid is None:
                QMessageBox.warning(self, "Trial output", "This trial could not be found.")
                return
            rows = fetch_all("SELECT Name FROM tblYarn WHERE ID = ?", [yid])
            name = str(rows[0]["Name"]) if rows else f"Trial output {yid}"
        except Exception as e:
            show_error(self, "Trial output", "The yarn entry for this trial could not be created.", e)
            return
        self._new_row(int(yid), name)

    # ── apply ─────────────────────────────────────────────────────────
    def _apply(self) -> None:
        missing = trials_without_ply(self.state)
        if missing:
            QMessageBox.warning(self, "Apply", "Every trial needs at least one ply. Without a ply: "
                                + ", ".join(missing[:15]) + (" …" if len(missing) > 15 else ""))
            return
        dup = duplicate_rows(self.state)
        if dup:
            d = dup[0]
            QMessageBox.warning(self, "Apply", f"{d.ply} ({d.yarn_name}) appears twice with the same yarn use "
                                               f"({self._use_name(d.use_id)}). Choose another use in the Use column.")
            return
        ops = plan(self.before, self.state)
        if not ops:
            self.reject()
            return
        lines = describe(ops, dict(self._use_list))
        removes = any(o["op"] == "remove" for o in ops)
        text = "\n".join("• " + l for l in lines[:25]) + (f"\n… and {len(lines) - 25} more" if len(lines) > 25 else "")
        if removes:
            text += "\n\nRemoved plies lose their machine values (tensions, settings) in those trials."
        if any(o["op"] == "yarn" for o in ops):
            text += "\nA changed yarn keeps the machine values; a linked spool is cleared."
        if QMessageBox.question(self, "Apply changes", text, QMessageBox.Apply | QMessageBox.Cancel,
                                QMessageBox.Apply) != QMessageBox.Apply:
            return
        try:
            apply_plan(ops, self.series_pk)
        except Exception as e:
            show_error(self, "Apply", "The yarn changes could not be saved - nothing was changed.", e)
            return
        try:
            from db.usage_log import log_usage_event
            log_usage_event("feature", "series_yarns_apply", str(len(ops)))
        except Exception:
            pass
        self.accept()
