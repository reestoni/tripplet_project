# ui/widgets/stock_take_round_dialog.py
"""Stock take rounds - overview window, Nutzerwunsch 2026-10-16.

Yarn Stock -> Rack lookup -> "Stock take…". Shows the open round (or a
closed one, read only):
  * Locations tab: one tile per storage location, grouped by rack and level.
    grey = still open, green = checked and fine, orange = checked with
    differences, dashed = left out of this round. Click a tile to check
    that location (scan dialog in location mode, ui/widgets/stock_take_dialog.py);
    right-click for re-check / leave out / include / show results.
  * Results tab: what was found where - per spool, with a summary line;
    "Only differences" by default. Missing spools seen at another location
    in the same round say so ("seen at C21").
  * Export to Excel: summary, locations, results.
Superusers start a round (choosing which locations take part) and close it.
Checking a location needs write access (level 2), as before. Without a
round (or offline / tables missing) the old single-location check is still
available. Data: db/stock_take.py.
"""
from __future__ import annotations

import datetime
from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu, QMessageBox, QProgressBar, QPushButton, QScrollArea,
    QTableWidget, QTableWidgetItem, QTabWidget, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from db import stock_take as st

TILE_W, TILE_H = 82, 50
_TILE_STYLE = {
    st.ST_OPEN: ("#f2f2f2", "#c8c8c8", "#444444", "solid"),
    st.ST_OK: ("#EAF3DE", "#9ccc8a", "#2b5d22", "solid"),
    st.ST_DEVIATION: ("#FAEEDA", "#e3b866", "#7a4d00", "solid"),
    st.ST_EXCLUDED: ("#ffffff", "#d0d0d0", "#a0a0a0", "dashed"),
}
_RESULT_BG = {st.FOUND: "#EAF3DE", st.MISSING_KEPT: "#FCEBEB", st.MISSING_DISCARDED: "#FCEBEB",
              st.UNKNOWN: "#FCEBEB"}
_DEV_BG = "#FAEEDA"


def _is_superuser() -> bool:
    try:
        import app_meta
        return bool(app_meta.is_superuser_level())
    except Exception:
        return False


def _when(v) -> str:
    return v.strftime("%d.%m.%Y %H:%M") if hasattr(v, "strftime") else str(v or "")


def _tile_qss(state: str) -> str:
    bg, border, fg, line = _TILE_STYLE[state]
    return (f"QToolButton{{background:{bg}; border:1px {line} {border}; border-radius:5px; color:{fg};"
            f"font-size:11px; padding:2px;}} QToolButton:hover{{border:2px {line} {border};}}")


def tile_columns(locs: List[str]) -> List[Tuple[str, int]]:
    """Column per location within one level: by slot number (C21 -> 0,
    C23 -> 2), so the slots of all levels line up even with gaps; locations
    without a plain slot number follow after the numbered ones."""
    out, used = [], set()
    rest_locs = []
    for loc in locs:
        _r, _lv, slot = st.parse_location(loc)
        if slot.isdigit() and 0 < int(slot) <= 40 and int(slot) - 1 not in used:
            out.append((loc, int(slot) - 1))
            used.add(int(slot) - 1)
        else:
            rest_locs.append(loc)
    nxt = max(used) + 1 if used else 0
    for loc in rest_locs:
        out.append((loc, nxt))
        nxt += 1
    return out


# ── start a round ────────────────────────────────────────────────────────
class StartRoundDialog(QDialog):
    """Name + which locations take part (all ticked; untick to leave out)."""

    def __init__(self, locations: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Start stock take round")
        self.resize(460, 620)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Name of the round:"))
        self.txt_name = QLineEdit(f"Stock take {datetime.date.today():%B %Y}")
        lay.addWidget(self.txt_name)
        info = QLabel("All locations take part. Untick the ones you want to leave out of this round "
                      "(e.g. a rack that is cleared out). You can still change this later in the overview "
                      "(right-click a location).")
        info.setWordWrap(True)
        lay.addWidget(info)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self._items: Dict[str, QTreeWidgetItem] = {}
        for rack, levels in st.group_locations(locations):
            parent_item = QTreeWidgetItem(self.tree, [f"Rack {rack}" if rack else "Other locations"])
            parent_item.setFlags(parent_item.flags() | Qt.ItemIsAutoTristate | Qt.ItemIsUserCheckable)
            parent_item.setCheckState(0, Qt.Checked)
            for _level, locs in levels:
                for loc in locs:
                    it = QTreeWidgetItem(parent_item, [loc])
                    it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                    it.setCheckState(0, Qt.Checked)
                    self._items[loc] = it
        self.tree.itemChanged.connect(lambda *_a: self._update_count())
        lay.addWidget(self.tree, 1)
        row = QHBoxLayout()
        for text, state in (("Select all", Qt.Checked), ("Select none", Qt.Unchecked)):
            b = QPushButton(text, objectName="GreyBtn")
            b.clicked.connect(lambda _c=False, s=state: self._set_all(s))
            row.addWidget(b)
        row.addStretch(1)
        self.lbl_count = QLabel()
        row.addWidget(self.lbl_count)
        lay.addLayout(row)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Start round")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self._update_count()

    def _set_all(self, state) -> None:
        for i in range(self.tree.topLevelItemCount()):
            self.tree.topLevelItem(i).setCheckState(0, state)

    def _update_count(self) -> None:
        self.lbl_count.setText(f"{len(self._items) - len(self.excluded())} of {len(self._items)} locations included")

    def name(self) -> str:
        return self.txt_name.text().strip()

    def locations(self) -> List[str]:
        return list(self._items)

    def excluded(self) -> List[str]:
        return [loc for loc, it in self._items.items() if it.checkState(0) != Qt.Checked]


# ── overview ─────────────────────────────────────────────────────────────
class StockTakeRoundDialog(QDialog):
    def __init__(self, get_spools: Callable[[], Tuple[List[Dict], Dict[int, str]]], writable: bool = True,
                 single_location_prefix: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Stock take")
        self.resize(1180, 820)
        self._get_spools = get_spools
        self._writable = writable
        self._single_prefix = single_location_prefix
        self._available = st.available()
        self._round: Optional[Dict] = None
        self._locs: List[Dict] = []
        self._items: List[Dict] = []
        self._spools: Dict[int, Dict] = {}
        self._yarn_names: Dict[int, str] = {}
        self.changed = False  # spools changed (moves, put-backs, discards) -> Yarn Stock reloads

        root = QVBoxLayout(self)
        top = QHBoxLayout()
        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet("font-size:18px; font-weight:700;")
        top.addWidget(self.lbl_title)
        top.addStretch(1)
        top.addWidget(QLabel("Round:"))
        self.cmb_round = QComboBox()
        self.cmb_round.setMinimumWidth(260)
        self.cmb_round.currentIndexChanged.connect(self._on_round_chosen)
        top.addWidget(self.cmb_round)
        btn_help = QPushButton("?")
        btn_help.setFixedSize(26, 26)
        btn_help.setToolTip("How does the stock take work?")
        btn_help.setStyleSheet(
            "QPushButton{background:transparent;color:#39a650;border:1px solid #39a650;"
            "border-radius:13px;padding:0;font-size:14px;font-weight:700;}"
            "QPushButton:hover{background:#e8f5e9;}")
        btn_help.clicked.connect(self._open_help)
        top.addWidget(btn_help)
        root.addLayout(top)

        self.lbl_info = QLabel()
        self.lbl_info.setWordWrap(True)
        root.addWidget(self.lbl_info)
        prog = QHBoxLayout()
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(14)
        prog.addWidget(self.bar, 1)
        self.lbl_progress = QLabel()
        self.lbl_progress.setStyleSheet("font-weight:600;")
        prog.addWidget(self.lbl_progress)
        root.addLayout(prog)

        btns = QHBoxLayout()
        self.btn_start = QPushButton("Start new round…", objectName="GreenBtn")
        self.btn_start.clicked.connect(self._on_start)
        btns.addWidget(self.btn_start)
        self.btn_close_round = QPushButton("Close round…", objectName="GreyBtn")
        self.btn_close_round.clicked.connect(self._on_close_round)
        btns.addWidget(self.btn_close_round)
        self.btn_single = QPushButton("Check a location without a round…", objectName="GreyBtn")
        self.btn_single.clicked.connect(self._on_single)
        btns.addWidget(self.btn_single)
        btns.addStretch(1)
        self.btn_refresh = QPushButton("Refresh", objectName="GreyBtn")
        self.btn_refresh.setToolTip("Reload - e.g. when a colleague checks locations at the same time")
        self.btn_refresh.clicked.connect(lambda: self._load(keep_round=True))
        btns.addWidget(self.btn_refresh)
        self.btn_export = QPushButton("Export to Excel…", objectName="GreyBtn")
        self.btn_export.clicked.connect(self._on_export)
        btns.addWidget(self.btn_export)
        root.addLayout(btns)

        self.tabs = QTabWidget()
        # locations
        loc_page = QWidget()
        lp = QVBoxLayout(loc_page)
        lp.setContentsMargins(4, 6, 4, 4)
        legend = QHBoxLayout()
        for state, text in ((st.ST_OPEN, "open"), (st.ST_OK, "checked, all fine"),
                            (st.ST_DEVIATION, "checked, with differences"), (st.ST_EXCLUDED, "left out")):
            sw = QToolButton()
            sw.setEnabled(False)
            sw.setFixedSize(22, 16)
            sw.setStyleSheet(_tile_qss(state))
            legend.addWidget(sw)
            legend.addWidget(QLabel(text))
            legend.addSpacing(12)
        legend.addStretch(1)
        hint = QLabel("Click a location to check it · right-click for more")
        hint.setStyleSheet("color:#666;")
        legend.addWidget(hint)
        lp.addLayout(legend)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        lp.addWidget(self.scroll, 1)
        self.tabs.addTab(loc_page, "Locations")
        # results
        res_page = QWidget()
        rp = QVBoxLayout(res_page)
        rp.setContentsMargins(4, 6, 4, 4)
        self.lbl_summary = QLabel()
        self.lbl_summary.setWordWrap(True)
        rp.addWidget(self.lbl_summary)
        frow = QHBoxLayout()
        self.chk_dev = QCheckBox("Only differences")
        self.chk_dev.setChecked(True)
        self.chk_dev.toggled.connect(self._render_results)
        frow.addWidget(self.chk_dev)
        frow.addSpacing(16)
        frow.addWidget(QLabel("Location:"))
        self.txt_loc_filter = QLineEdit()
        self.txt_loc_filter.setPlaceholderText("e.g. C or C21")
        self.txt_loc_filter.setFixedWidth(110)
        self.txt_loc_filter.textChanged.connect(self._render_results)
        frow.addWidget(self.txt_loc_filter)
        frow.addStretch(1)
        rp.addLayout(frow)
        self.tbl = QTableWidget(0, 8)
        self.tbl.setHorizontalHeaderLabels(["Location", "Spool", "Yarn", "Batch", "Result", "Detail",
                                            "Checked by", "Checked at"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSortingEnabled(True)
        self.tbl.sortByColumn(0, Qt.AscendingOrder)
        self.tbl.horizontalHeader().setMinimumSectionSize(70)
        rp.addWidget(self.tbl, 1)
        self.tabs.addTab(res_page, "Results")
        root.addWidget(self.tabs, 1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        btn_close = QPushButton("Close", objectName="GreyBtn")
        btn_close.clicked.connect(self.accept)
        bottom.addWidget(btn_close)
        root.addLayout(bottom)

        self._load()

    # ── loading ────────────────────────────────────────────────────────
    def _load(self, keep_round: bool = False, round_id: Optional[int] = None) -> None:
        self._spools_loaded = False
        if not self._available:
            self._round, self._locs, self._items = None, [], []
            self._fill_round_combo([])
            self._render()
            return
        current = round_id if round_id is not None else (
            self._round.get("ID") if keep_round and self._round else None)
        rounds = st.list_rounds()
        if current is None:
            open_r = next((r for r in rounds if r.get("ClosedAt") is None), None)
            current = open_r["ID"] if open_r else (rounds[0]["ID"] if rounds else None)
        self._fill_round_combo(rounds, current)
        self._round = next((r for r in rounds if r["ID"] == current), None)
        if self._round is not None:
            self._locs = st.round_locations(self._round["ID"])
            self._items = st.round_items(self._round["ID"])
        else:
            self._locs, self._items = [], []
        self._render()

    def _fill_round_combo(self, rounds: List[Dict], current: Optional[int] = None) -> None:
        self.cmb_round.blockSignals(True)
        self.cmb_round.clear()
        for r in rounds:
            state = "open" if r.get("ClosedAt") is None else f"closed {_when(r['ClosedAt'])[:10]}"
            self.cmb_round.addItem(f"{r['Name']} ({state})", r["ID"])
            if r["ID"] == current:
                self.cmb_round.setCurrentIndex(self.cmb_round.count() - 1)
        self.cmb_round.setEnabled(self.cmb_round.count() > 1)
        self.cmb_round.blockSignals(False)

    def _on_round_chosen(self, idx: int) -> None:
        rid = self.cmb_round.itemData(idx)
        if rid is not None:
            self._load(round_id=int(rid))

    def _ensure_spools(self) -> None:
        if not getattr(self, "_spools_loaded", False):
            spools, names = self._get_spools()
            self._spools = {int(s["ID"]): s for s in spools if s.get("ID") is not None}
            self._yarn_names = dict(names or {})
            self._spools_loaded = True

    def _is_open(self) -> bool:
        return self._round is not None and self._round.get("ClosedAt") is None

    # ── rendering ──────────────────────────────────────────────────────
    def _items_by_loc(self) -> Dict[str, List[Dict]]:
        out: Dict[str, List[Dict]] = {}
        for it in self._items:
            out.setdefault(it["Location"], []).append(it)
        return out

    def _render(self) -> None:
        su = _is_superuser()
        r = self._round
        if not self._available:
            self.lbl_title.setText("Stock take")
            self.lbl_info.setText("Stock take rounds are not set up in this database (or you are offline). "
                                  "You can still check a single location.")
        elif r is None:
            self.lbl_title.setText("Stock take")
            self.lbl_info.setText("No stock take round has been started yet."
                                  + (" Click <b>Start new round…</b> to begin." if su
                                     else " A superuser starts a round. You can still check a single location."))
        else:
            self.lbl_title.setText(r["Name"])
            started = f"Started {_when(r['StartedAt'])} by {r.get('StartedByName') or 'unknown'}"
            if r.get("ClosedAt") is not None:
                self.lbl_info.setText(f"{started} · <b>closed {_when(r['ClosedAt'])}</b> - read only.")
            else:
                self.lbl_info.setText(f"{started} · open.")
        summary = st.summarize(self._locs, self._items)
        total, done = summary["to_check"], summary["checked"]
        self.bar.setMaximum(max(total, 1))
        self.bar.setValue(done)
        self.lbl_progress.setText(
            f"{done} of {total} locations checked" + (f" · {summary[st.ST_EXCLUDED]} left out"
                                                       if summary[st.ST_EXCLUDED] else "") if r else "")
        is_open = self._is_open()
        self.btn_start.setVisible(self._available and su and not is_open)
        self.btn_close_round.setVisible(self._available and su and is_open)
        self.btn_single.setVisible(not is_open and self._writable)
        self.btn_export.setEnabled(r is not None)
        self.btn_refresh.setEnabled(self._available)
        self._render_tiles()
        self._render_results()

    def _render_tiles(self) -> None:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(10)
        if not self._locs:
            lab = QLabel("No locations to show." if self._round is not None else "")
            lab.setStyleSheet("color:#666;")
            lay.addWidget(lab)
        by_loc = self._items_by_loc()
        rows = {l["Location"]: l for l in self._locs}
        now_count: Dict[str, int] = {}
        if self._is_open() and self._locs:
            self._ensure_spools()
            for s in self._spools.values():
                if s.get("Status") == "in stock":
                    k = st.norm_location(s.get("Location"))
                    now_count[k] = now_count.get(k, 0) + 1
        for rack, levels in st.group_locations(rows):
            box = QFrame()
            box.setObjectName("RackBox")
            box.setStyleSheet("QFrame#RackBox{border:1px solid #e0e0e0; border-radius:6px; background:#fcfcfc;}"
                              "QFrame#RackBox QLabel{border:none; background:transparent;}")
            bl = QVBoxLayout(box)
            bl.setContentsMargins(10, 6, 10, 8)
            done = sum(1 for lv in levels for loc in lv[1]
                       if st.location_status(rows[loc], by_loc.get(loc, [])) in (st.ST_OK, st.ST_DEVIATION))
            todo = sum(1 for lv in levels for loc in lv[1] if not rows[loc]["Excluded"])
            head = QLabel(f"<b>{'Rack ' + rack if rack else 'Other locations'}</b>"
                          f"  <span style='color:#666'>{done}/{todo} checked</span>")
            bl.addWidget(head)
            grid = QGridLayout()
            grid.setHorizontalSpacing(6)
            grid.setVerticalSpacing(6)
            max_col = 0
            for row_i, (_level, locs) in enumerate(levels):
                for loc, col_i in tile_columns(locs):
                    grid.addWidget(self._tile(rows[loc], by_loc.get(loc, []), now_count.get(loc, 0)), row_i, col_i)
                    max_col = max(max_col, col_i)
            grid.setColumnStretch(max_col + 1, 1)
            bl.addLayout(grid)
            lay.addWidget(box)
        lay.addStretch(1)
        self.scroll.setWidget(page)

    def _tile(self, row: Dict, items: List[Dict], now_n: int) -> QToolButton:
        state = st.location_status(row, items)
        loc = row["Location"]
        if state == st.ST_EXCLUDED:
            sub = "left out"
        elif state == st.ST_OPEN:
            sub = f"{now_n} spool{'s' if now_n != 1 else ''}" if self._is_open() else "not checked"
        else:
            sub = f"{int(row.get('Found') or 0)}/{int(row.get('Expected') or 0)}"
            extra = sum(1 for i in items if i.get("Result") not in (st.FOUND, st.MISSING_KEPT, st.MISSING_DISCARDED))
            if extra:
                sub += f" +{extra}"
        b = QToolButton()
        b.setText(f"{loc}\n{sub}")
        b.setFixedSize(TILE_W, TILE_H)
        b.setStyleSheet(_tile_qss(state))
        b.setCursor(Qt.PointingHandCursor)
        tip = [f"<b>{loc}</b>"]
        if state in (st.ST_OK, st.ST_DEVIATION):
            tip.append(f"Checked {_when(row.get('CheckedAt'))} by {row.get('CheckedByName') or 'unknown'}")
            tip.append(f"Found {int(row.get('Found') or 0)} of {int(row.get('Expected') or 0)} expected")
            devs = [i for i in items if st.is_deviation(i.get("Result") or "")]
            for i in devs[:8]:
                sid = f"#{i['SpoolID']}" if i.get("SpoolID") is not None else ""
                tip.append(f"{sid} {st.RESULT_LABELS.get(i['Result'], i['Result'])}"
                           + (f" ({i['Detail']})" if i.get("Detail") else ""))
            if len(devs) > 8:
                tip.append(f"… {len(devs) - 8} more")
        elif state == st.ST_EXCLUDED:
            tip.append("Left out of this round")
        else:
            tip.append("Not checked yet")
        b.setToolTip("<br>".join(tip))
        b.clicked.connect(lambda _c=False, l=loc: self._on_tile_clicked(l))
        b.setContextMenuPolicy(Qt.CustomContextMenu)
        b.customContextMenuRequested.connect(lambda pos, l=loc, w=b: self._tile_menu(l, w.mapToGlobal(pos)))
        return b

    def _render_results(self, *_a) -> None:
        summary = st.summarize(self._locs, self._items)
        parts = [f"<b>{summary['checked']}</b> of {summary['to_check']} locations checked",
                 f"<b>{summary[st.FOUND]}</b> spools found where expected"
                 + (f" ({summary['found_by_hand']} of them marked by hand, not scanned)"
                    if summary["found_by_hand"] else "")]
        for code, text in ((st.MISSING_KEPT, "missing (kept)"), (st.MISSING_DISCARDED, "missing (discarded)"),
                           (st.MOVED_HERE, "moved here"), (st.MOVED_ELSEWHERE, "moved elsewhere"),
                           (st.ELSEWHERE_UNCHANGED, "registered elsewhere"), (st.RESTOCKED, "put back in stock"),
                           (st.DISCARDED_UNCHANGED, "discarded, left discarded"), (st.UNKNOWN, "unknown spool number(s)")):
            if summary[code]:
                parts.append(f"<b>{summary[code]}</b> {text}")
        if summary["missing_seen_elsewhere"]:
            parts.append(f"({summary['missing_seen_elsewhere']} of the missing were seen at another location)")
        self.lbl_summary.setText(" · ".join(parts) if self._round is not None else "")

        if self._items:
            self._ensure_spools()
        resolved = st.resolve_missing(self._items)
        flt = st.norm_location(self.txt_loc_filter.text())
        rows = []
        for n, it in enumerate(self._items):
            if self.chk_dev.isChecked() and not st.is_deviation(it.get("Result") or ""):
                continue
            if flt and not it["Location"].startswith(flt):
                continue
            rows.append((n, it))
        t = self.tbl
        t.setSortingEnabled(False)
        t.setRowCount(len(rows))
        for r, (n, it) in enumerate(rows):
            sid = it.get("SpoolID")
            s = self._spools.get(int(sid)) if sid is not None else None
            detail = it.get("Detail") or ""
            if n in resolved:
                detail = (detail + "; " if detail else "") + resolved[n]
            vals = [it["Location"], f"#{sid}" if sid is not None else "",
                    self._yarn_names.get(int(s.get("YarnID") or -1), "?") if s else "",
                    (s.get("Charge") or "") if s else "",
                    st.RESULT_LABELS.get(it["Result"], it["Result"]), detail,
                    it.get("CheckedByName") or "", _when(it.get("CheckedAt"))]
            bg = QColor(_RESULT_BG.get(it["Result"], _DEV_BG))
            if n in resolved:
                bg = QColor(_DEV_BG)
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                cell.setBackground(bg)
                if c == 1 and sid is not None:
                    cell.setData(Qt.UserRole, int(sid))
                t.setItem(r, c, cell)
        t.setSortingEnabled(True)
        t.resizeColumnsToContents()
        t.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)

    # ── actions ────────────────────────────────────────────────────────
    def _row(self, loc: str) -> Optional[Dict]:
        return next((l for l in self._locs if l["Location"] == loc), None)

    def _on_tile_clicked(self, loc: str) -> None:
        row = self._row(loc)
        if row is None:
            return
        if not self._is_open() or not self._writable:
            self._show_results_for(loc)
            return
        if row["Excluded"]:
            if _is_superuser() and QMessageBox.question(
                    self, "Stock take", f"{loc} is left out of this round. Include it again?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
                self._set_excluded(loc, False)
            elif not _is_superuser():
                QMessageBox.information(self, "Stock take", f"{loc} is left out of this round.")
            return
        self._check(loc)

    def _check(self, loc: str) -> None:
        row = self._row(loc)
        if row is not None and row.get("CheckedAt"):
            if QMessageBox.question(
                    self, "Check again",
                    f"{loc} was already checked {_when(row['CheckedAt'])} by {row.get('CheckedByName') or 'unknown'}."
                    "\n\nCheck it again? The new result replaces the old one.",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
        self._spools_loaded = False
        self._ensure_spools()  # fresh state = expected list
        from ui.widgets.stock_take_dialog import StockTakeDialog
        dlg = StockTakeDialog(list(self._spools.values()), self._yarn_names, parent=self,
                              round_location=loc, round_name=self._round["Name"])
        finished = dlg.exec() == QDialog.Accepted
        self.changed = self.changed or dlg.changed
        if finished:
            try:
                st.save_check(self._round["ID"], loc, dlg.expected_count(), dlg.outcome_items())
            except Exception as e:
                QMessageBox.warning(self, "Stock take", f"The result for {loc} could not be saved:\n\n{e}")
        self._load(keep_round=True)

    def _tile_menu(self, loc: str, pos) -> None:
        row = self._row(loc)
        if row is None:
            return
        m = QMenu(self)
        is_open, su = self._is_open(), _is_superuser()
        if is_open and self._writable and not row["Excluded"]:
            act = m.addAction("Check again…" if row.get("CheckedAt") else "Check this location…")
            act.triggered.connect(lambda: self._check(loc))
        if row.get("CheckedAt"):
            m.addAction("Show results").triggered.connect(lambda: self._show_results_for(loc))
        if is_open and su:
            if row["Excluded"]:
                m.addAction("Include in this round").triggered.connect(lambda: self._set_excluded(loc, False))
            else:
                m.addAction("Leave out of this round").triggered.connect(lambda: self._set_excluded(loc, True))
        if not m.isEmpty():
            m.exec(pos)

    def _set_excluded(self, loc: str, excluded: bool) -> None:
        row = self._row(loc)
        if excluded and row is not None and row.get("CheckedAt"):
            if QMessageBox.question(self, "Leave out", f"{loc} was already checked. Leave it out anyway? "
                                    "Its result stays in the list.",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
        st.set_excluded(self._round["ID"], loc, excluded)
        self._load(keep_round=True)

    def _show_results_for(self, loc: str) -> None:
        self.chk_dev.setChecked(False)
        self.txt_loc_filter.setText(loc)
        self.tabs.setCurrentIndex(1)

    def _on_start(self) -> None:
        if not _is_superuser():
            return
        try:
            locs = st.all_locations()
        except Exception as e:
            QMessageBox.warning(self, "Start stock take round", f"Could not read the locations:\n\n{e}")
            return
        dlg = StartRoundDialog(locs, self)
        if dlg.exec() != QDialog.Accepted:
            return
        try:
            rid = st.start_round(dlg.name(), dlg.locations(), dlg.excluded())
        except Exception as e:
            QMessageBox.warning(self, "Start stock take round", str(e))
            return
        self._load(round_id=rid)

    def _on_close_round(self) -> None:
        if not (_is_superuser() and self._is_open()):
            return
        by_loc = self._items_by_loc()
        open_locs = [l["Location"] for l in self._locs
                     if st.location_status(l, by_loc.get(l["Location"], [])) == st.ST_OPEN]
        text = f"Close \"{self._round['Name']}\"?"
        if open_locs:
            shown = ", ".join(open_locs[:30]) + (" …" if len(open_locs) > 30 else "")
            text += (f"\n\n{len(open_locs)} location(s) have not been checked yet:\n{shown}\n\n"
                     "They stay 'not checked' in the results.")
        text += "\n\nAfter closing, the round can only be viewed (and exported), not changed."
        if QMessageBox.question(self, "Close round", text, QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) != QMessageBox.Yes:
            return
        st.close_round(self._round["ID"])
        self._load(keep_round=True)

    def _on_single(self) -> None:
        """Old flow: check a rack or slot without a round (nothing is recorded)."""
        self._spools_loaded = False
        self._ensure_spools()
        from ui.widgets.stock_take_dialog import StockTakeDialog
        dlg = StockTakeDialog(list(self._spools.values()), self._yarn_names,
                              location_prefix=self._single_prefix, parent=self)
        dlg.exec()
        self.changed = self.changed or dlg.changed

    def _open_help(self) -> None:
        from ui.widgets.yarn_stock_help_dialog import show_yarn_stock_help
        show_yarn_stock_help(self, tab="stocktake")

    def _on_export(self) -> None:
        if self._round is None:
            return
        import re
        safe = re.sub(r"[^\w-]+", "_", self._round["Name"]).strip("_") or "stock_take"
        path, _ = QFileDialog.getSaveFileName(self, "Export stock take", f"{safe}.xlsx", "Excel Files (*.xlsx)")
        if not path:
            return
        try:
            export_excel(path, self._round, self._locs, self._items, *self._spools_for_export())
        except Exception as e:
            QMessageBox.warning(self, "Export to Excel", f"Could not write the file:\n\n{e}")
            return
        st._log("stock_take_export", str(self._round["ID"]))
        QMessageBox.information(self, "Export to Excel", f"Saved:\n{path}")

    def _spools_for_export(self):
        self._ensure_spools()
        return self._spools, self._yarn_names


def export_excel(path: str, rnd: Dict, locs: List[Dict], items: List[Dict],
                 spools: Dict[int, Dict], yarn_names: Dict[int, str]) -> None:
    """Three sheets: Summary, Locations, Results (every spool, not only differences)."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    bold = Font(bold=True)
    summary = st.summarize(locs, items)
    ws = wb.active
    ws.title = "Summary"
    rows = [("Round", rnd["Name"]), ("Started", _when(rnd.get("StartedAt"))),
            ("Started by", rnd.get("StartedByName") or ""), ("Closed", _when(rnd.get("ClosedAt")) or "open"),
            ("", ""), ("Locations in round", summary["to_check"]), ("Locations checked", summary["checked"]),
            ("  all fine", summary[st.ST_OK]), ("  with differences", summary[st.ST_DEVIATION]),
            ("Locations not checked", summary[st.ST_OPEN]), ("Locations left out", summary[st.ST_EXCLUDED]),
            ("", "")]
    rows += [(st.RESULT_LABELS[c], summary[c]) for c in st.RESULT_LABELS]
    rows.append(("Missing, but seen at another location", summary["missing_seen_elsewhere"]))
    rows.append(("Found, marked by hand (not scanned)", summary["found_by_hand"]))
    for r in rows:
        ws.append(list(r))
    for c in ws["A"]:
        c.font = bold
    ws.column_dimensions["A"].width = 44
    ws.column_dimensions["B"].width = 28

    by_loc: Dict[str, List[Dict]] = {}
    for it in items:
        by_loc.setdefault(it["Location"], []).append(it)
    label = {st.ST_OPEN: "not checked", st.ST_OK: "all fine", st.ST_DEVIATION: "differences",
             st.ST_EXCLUDED: "left out"}
    fills = {st.ST_OK: "EAF3DE", st.ST_DEVIATION: "FAEEDA", st.ST_OPEN: "F2F2F2"}
    ws2 = wb.create_sheet("Locations")
    ws2.append(["Location", "Status", "Expected", "Found", "Differences", "Checked by", "Checked at"])
    for l in locs:
        its = by_loc.get(l["Location"], [])
        state = st.location_status(l, its)
        ws2.append([l["Location"], label[state],
                    l.get("Expected") if l.get("CheckedAt") else None, l.get("Found") if l.get("CheckedAt") else None,
                    sum(1 for i in its if st.is_deviation(i.get("Result") or "")) if l.get("CheckedAt") else None,
                    l.get("CheckedByName") or "", _when(l.get("CheckedAt"))])
        if state in fills:
            ws2.cell(ws2.max_row, 2).fill = PatternFill("solid", fgColor=fills[state])

    resolved = st.resolve_missing(items)
    ws3 = wb.create_sheet("Results")
    ws3.append(["Location", "Spool", "Yarn", "Batch", "Weight (kg)", "Result", "Detail", "Checked by", "Checked at"])
    for n, it in enumerate(items):
        sid = it.get("SpoolID")
        s = spools.get(int(sid)) if sid is not None else None
        detail = it.get("Detail") or ""
        if n in resolved:
            detail = (detail + "; " if detail else "") + resolved[n]
        w = s.get("WeightKg") if s else None
        ws3.append([it["Location"], sid, yarn_names.get(int(s.get("YarnID") or -1), "") if s else "",
                    (s.get("Charge") or "") if s else "", float(w) if w is not None else None,
                    st.RESULT_LABELS.get(it["Result"], it["Result"]), detail,
                    it.get("CheckedByName") or "", _when(it.get("CheckedAt"))])
    for sheet in (ws2, ws3):
        for c in sheet[1]:
            c.font = bold
        for col in sheet.columns:
            width = max(len(str(c.value or "")) for c in col)
            sheet.column_dimensions[col[0].column_letter].width = min(max(10, width + 2), 50)
        sheet.freeze_panes = "A2"
    wb.save(path)
