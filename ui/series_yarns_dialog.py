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

MAX_ENDS = 20
CHANGED_BG = QColor("#FFF3B0")   # same yellow as unsaved cells in Show Experiment
OFF_FG = QColor("#9a9a9a")


# ── data ──────────────────────────────────────────────────────────────────
# A row of the table = one (Ply, YarnID, YarnUseID) combination. Series rule
# (decided by the lab, kept on purpose): a yarn always has the SAME ply number
# in a series - the same yarn used once as "Core" and once as "Effect" is two
# rows "Ply 1" with different uses, not "Ply 1" and "Ply 3".
@dataclass
class PlyRow:
    ply: str
    yarn_id: Optional[int]
    yarn_name: str
    use_id: Any = None                     # YarnUseID or None
    ends: Dict[int, int] = field(default_factory=dict)  # trial id -> number of rows
    orig_yarn_id: Optional[int] = None     # as loaded (key in the DB)
    orig_use_id: Any = None

    def key(self) -> Tuple[str, Optional[int], Any]:
        return (self.ply, self.yarn_id, self.use_id)


@dataclass
class State:
    trials: List[Tuple[int, Any, str]]     # (trial id, Versuchsnummer, column label)
    rows: List[PlyRow]
    refs: set = field(default_factory=set)  # trial ids of reference samples (may have no ply)


def ply_number(label: str) -> int:
    m = re.search(r"\d+", label or "")
    return int(m.group()) if m else 9999


def next_ply_label(rows: List[PlyRow]) -> str:
    used = {ply_number(r.ply) for r in rows}
    n = 1
    while n in used:
        n += 1
    return f"Ply {n}"


def ply_of_yarn(rows: List[PlyRow], yarn_id: Optional[int]) -> Optional[str]:
    """The ply number a yarn already has in the series (series rule), None if new."""
    for r in rows:
        if r.yarn_id == yarn_id:
            return r.ply
    return None


def load_state(series_pk: int) -> State:
    from db.connection import fetch_all
    from db.trial_reference import IS_REFERENCE_COL, format_trial_number, has_reference_columns, is_reference_value
    ref_sel = f", {IS_REFERENCE_COL} AS IsRef" if has_reference_columns() else ""
    trows = fetch_all(f"SELECT ID, Versuchsnummer{ref_sel} FROM tblTrial WHERE TrialSeriesID = ? "
                      f"ORDER BY Versuchsnummer", [series_pk])
    trials = [(int(r["ID"]), r["Versuchsnummer"], format_trial_number(r["Versuchsnummer"])) for r in trows]
    refs = {int(r["ID"]) for r in trows if is_reference_value(r.get("IsRef"))}
    if not trials:
        return State([], [], refs)
    ph = ",".join("?" for _ in trials)
    srows = fetch_all(
        f"SELECT ts.TrialID, ts.Ply, ts.YarnID, ts.YarnUseID, y.Name AS YarnName "
        f"FROM tblTrialSettings ts LEFT JOIN tblYarn y ON y.ID = ts.YarnID WHERE ts.TrialID IN ({ph})",
        [t[0] for t in trials])
    by_key: Dict[Tuple[str, Optional[int], Any], PlyRow] = {}
    for r in srows:
        yid = int(r["YarnID"]) if r.get("YarnID") is not None else None
        uid = int(r["YarnUseID"]) if r.get("YarnUseID") is not None else None
        key = ((r.get("Ply") or "").strip(), yid, uid)
        row = by_key.get(key)
        if row is None:
            row = by_key[key] = PlyRow(key[0], yid, str(r.get("YarnName") or "(no yarn)"), uid,
                                       orig_yarn_id=yid, orig_use_id=uid)
        tid = int(r["TrialID"])
        row.ends[tid] = row.ends.get(tid, 0) + 1
    rows = sorted(by_key.values(), key=lambda r: (ply_number(r.ply), r.ply, r.yarn_name,
                                                   -1 if r.use_id is None else r.use_id))
    return State(trials, rows, refs)


def mixed_plies(rows: List[PlyRow]) -> set:
    """Ply labels with more than one yarn (old data, against the series rule)."""
    yarns: Dict[str, set] = {}
    for r in rows:
        yarns.setdefault(r.ply, set()).add(r.yarn_id)
    return {p for p, y in yarns.items() if len(y) > 1}


def trials_without_ply(state: State) -> List[str]:
    """Trials (not reference samples) that would be left without a ply."""
    return [label for tid, _v, label in state.trials
            if tid not in state.refs and not any(r.ends.get(tid, 0) > 0 for r in state.rows)]


def duplicate_rows(state: State) -> List[PlyRow]:
    """Rows with the same ply, yarn AND use as an earlier row - can't be told apart."""
    seen, dup = set(), []
    for r in state.rows:
        if r.key() in seen:
            dup.append(r)
        seen.add(r.key())
    return dup


def plan(before: State, after: State) -> List[Dict[str, Any]]:
    """Differences as operations (rows of `after` are matched to `before` by
    position - the dialog never reorders or deletes rows, removing = all 0).
    Every operation names the row's key AS LOADED ("match"), apply_plan()
    resolves the affected DB rows before it changes anything."""
    ops: List[Dict[str, Any]] = []
    n_old = len(before.rows)
    for i, new in enumerate(after.rows):
        old = before.rows[i] if i < n_old else None
        match = (old.ply, old.yarn_id, old.use_id) if old else None
        if old is not None and (new.yarn_id != old.yarn_id or new.use_id != old.use_id):
            ops.append({"op": "change", "match": match, "trials": [t for t, n in old.ends.items() if n > 0],
                        "new_yarn": new.yarn_id, "new_use": new.use_id,
                        "yarn_changed": new.yarn_id != old.yarn_id, "use_changed": new.use_id != old.use_id,
                        "ply": old.ply, "old_name": old.yarn_name, "new_name": new.yarn_name,
                        "old_use": old.use_id})
        for tid, _v, label in after.trials:
            n_old_ends = old.ends.get(tid, 0) if old else 0
            n_new = new.ends.get(tid, 0)
            if n_new > n_old_ends:
                ops.append({"op": "add", "trial": tid, "label": label, "ply": new.ply, "yarn": new.yarn_id,
                            "use": new.use_id, "n": n_new - n_old_ends, "more_ends": n_old_ends > 0,
                            "yarn_name": new.yarn_name})
            elif n_new < n_old_ends:
                ops.append({"op": "remove", "trial": tid, "label": label, "match": match, "ply": old.ply,
                            "use": old.use_id, "n": n_old_ends - n_new, "all": n_new == 0,
                            "yarn_name": old.yarn_name})
    return ops


def describe(ops: List[Dict[str, Any]], use_names: Optional[Dict[Any, str]] = None) -> List[str]:
    """Readable summary (English, UI text)."""
    names = use_names or {}

    def use(u):
        return names.get(u, "—") if u is not None else "—"

    def tag(ply, name, u):
        return f"{ply} ({name}" + (f", {use(u)}" if u is not None else "") + ")"

    lines: List[str] = []
    for o in ops:
        if o["op"] != "change":
            continue
        n = len(o["trials"])
        if o["yarn_changed"]:
            lines.append(f"{o['ply']}: {o['old_name']} → {o['new_name']}"
                         + (f", use {use(o['old_use'])} → {use(o['new_use'])}" if o["use_changed"] else "")
                         + f" ({n} trials)")
        else:
            lines.append(f"{o['ply']} ({o['old_name']}): use {use(o['old_use'])} → {use(o['new_use'])} ({n} trials)")
    adds: Dict[str, List[str]] = {}
    rems: Dict[str, List[str]] = {}
    for o in ops:
        if o["op"] == "add":
            adds.setdefault(tag(o["ply"], o["yarn_name"], o["use"]), []).append(
                o["label"] + (f" +{o['n']} end" + ("s" if o["n"] > 1 else "") if o.get("more_ends")
                              else (f" ({o['n']} ends)" if o["n"] > 1 else "")))
        elif o["op"] == "remove":
            rems.setdefault(tag(o["ply"], o["yarn_name"], o["use"]), []).append(
                o["label"] + ("" if o["all"] else f" -{o['n']} end" + ("s" if o["n"] > 1 else "")))
    for t, labels in adds.items():
        lines.append(f"{t} added to: " + ", ".join(labels))
    for t, labels in rems.items():
        lines.append(f"{t} removed from: " + ", ".join(labels))
    return lines


def apply_plan(ops: List[Dict[str, Any]], series_pk: int) -> None:
    """Writes the operations in one transaction, then logs them.
    Order: removes (by the loaded key), then all changes - their DB rows are
    looked up BEFORE the first update, so swapping uses between two rows
    can't mix them up - then the new rows."""
    from db import change_log
    from db.connection import get_columns_map, get_connection, new_global_id
    cols = {k.lower() for k in get_columns_map("tblTrialSettings")}
    has_gid, has_use, has_spool = "globalid" in cols, "yarnuseid" in cols, "spoolid" in cols
    log: List[Dict[str, Any]] = []

    def where_key(match):
        ply, yarn, use = match
        sql, params = ["Ply = ?"], [ply]
        sql.append("YarnID IS NULL" if yarn is None else "YarnID = ?")
        params += [] if yarn is None else [yarn]
        if has_use:
            sql.append("YarnUseID IS NULL" if use is None else "YarnUseID = ?")
            params += [] if use is None else [use]
        return " AND ".join(sql), params

    with get_connection() as cn:
        cur = cn.cursor()
        try:
            for o in ops:
                if o["op"] != "remove":
                    continue
                w, p = where_key(o["match"])
                cur.execute(f"SELECT ID FROM tblTrialSettings WHERE TrialID = ? AND {w} ORDER BY ID DESC",
                            [o["trial"]] + p)
                ids = [r[0] for r in cur.fetchall()][:o["n"]]
                if ids:
                    cur.execute(f"DELETE FROM tblTrialSettings WHERE ID IN ({','.join('?' for _ in ids)})", ids)
                    log.extend({"table": "tblTrialSettings", "row_id": rid, "field": "Ply", "old": o["ply"],
                                "new": None, "trial_id": o["trial"]} for rid in ids)

            changes = []
            for o in ops:
                if o["op"] != "change" or not o["trials"]:
                    continue
                w, p = where_key(o["match"])
                ph = ",".join("?" for _ in o["trials"])
                cur.execute(f"SELECT ID, TrialID FROM tblTrialSettings WHERE TrialID IN ({ph}) AND {w}",
                            list(o["trials"]) + p)
                changes.append((o, cur.fetchall()))
            for o, hit in changes:
                if not hit:
                    continue
                sets, vals = [], []
                if o["yarn_changed"]:
                    sets.append("YarnID = ?")
                    vals.append(o["new_yarn"])
                    if has_spool:
                        sets.append("SpoolID = NULL")
                if o["use_changed"] and has_use:
                    sets.append("YarnUseID = ?")
                    vals.append(o["new_use"])
                if not sets:
                    continue
                ids = [rid for rid, _t in hit]
                cur.execute(f"UPDATE tblTrialSettings SET {', '.join(sets)} WHERE ID IN ({','.join('?' for _ in ids)})",
                            vals + ids)
                for rid, tid in hit:
                    if o["yarn_changed"]:
                        log.append({"table": "tblTrialSettings", "row_id": rid, "field": "YarnID",
                                    "old": o["match"][1], "new": o["new_yarn"], "trial_id": tid})
                    if o["use_changed"]:
                        log.append({"table": "tblTrialSettings", "row_id": rid, "field": "YarnUseID",
                                    "old": o["match"][2], "new": o["new_use"], "trial_id": tid})

            for o in ops:
                if o["op"] != "add":
                    continue
                for _ in range(o["n"]):
                    c, v = ["TrialID", "YarnID", "Ply"], [o["trial"], o["yarn"], o["ply"]]
                    if has_use and o.get("use") is not None:
                        c.append("YarnUseID")
                        v.append(o["use"])
                    if has_gid:
                        c.append("GlobalID")
                        v.append(new_global_id())
                    cur.execute(f"INSERT INTO tblTrialSettings ({', '.join(c)}) VALUES ({', '.join('?' for _ in v)})", v)
                    rid = getattr(cur, "lastrowid", None)
                    if rid:
                        log.append({"table": "tblTrialSettings", "row_id": rid, "field": "Ply", "old": None,
                                    "new": o["ply"], "trial_id": o["trial"]})
            cn.commit()
        except Exception:
            try:
                cn.rollback()
            except Exception:
                pass
            raise
    change_log.log_changes(log, series_id=series_pk, source="plies")


# ── yarn search ───────────────────────────────────────────────────────────
def load_yarns() -> List[Dict[str, Any]]:
    """Catalog yarns (no shadow yarns) with a search text."""
    from db.connection import fetch_all, get_columns_map
    cols = {k.lower(): v for k, v in get_columns_map("tblYarn").items()}
    extra = [cols[c] for c in ("kurzname", "garntyp", "material", "titer") if c in cols]
    where = f" WHERE {cols['sourcetrialid']} IS NULL" if "sourcetrialid" in cols else ""
    sel = ", ".join(["ID", "Name"] + extra)
    colours, _ = load_yarn_colours()
    out = []
    for r in fetch_all(f"SELECT {sel} FROM tblYarn{where} ORDER BY Name"):
        colour = colours.get(int(r["ID"]), "")
        words = " ".join(str(r.get(c) or "") for c in ["Name"] + extra) + " " + colour
        out.append({"id": int(r["ID"]), "name": str(r.get("Name") or ""), "colour": colour,
                    "search": words.lower()})
    return out


def filter_yarns(yarns: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
    """All words must occur (order free): "167 dty" finds "PES 167f48 DTY"."""
    words = (text or "").lower().split()
    return [y for y in yarns if all(w in y["search"] for w in words)]


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
