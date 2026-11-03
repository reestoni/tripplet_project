# ui/screen_smart_chart.py
"""Smart Chart, rebuilt 2026-10-30 (Nutzerwunsch): find trials by their
properties across ALL series and show them in a dashboard like Power BI
(ui/smart_dashboard.py: pages with visuals, Filters / Visualizations / Fields).

Since 2026-11-02 (Nutzerwunsch "Dashboard ist schöner") there is only the
dashboard - the former chart mode (one chart + list of trials) is gone; its
parts live on in the dashboard: Focus mode (⤢, the trials below a visual),
fairness details (click the dot), log axes / shapes / point size in Format.
No saved chart views existed (prod and dev_local checked), so nothing had to
be converted.

The filters on all pages (= "Find trials") are self.filters / self.ply_scope;
the dashboard edits them in its Filters pane. Top: New, Open view, Save view
(db/smart_chart_views.py), Share…, Excel, Reload, PDF.

Data and filtering: db/trial_explorer.py.
"""
from __future__ import annotations

import datetime
import logging
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from db import smart_chart_views as views
from db import trial_explorer as te
from ui.widgets import sidebar_nav
from ui.widgets.footer import FooterBar
from ui.widgets.friendly_error import show_error

logger = logging.getLogger(__name__)

ACCENT = "#1F7A3A"

_BTN = ("QPushButton{background:#FFFFFF;color:#1C2321;border:1px solid #C9D1C8;border-radius:6px;"
        "padding:6px 14px;font-weight:500;}QPushButton:hover{background:#F0F4EF;}"
        "QPushButton:disabled{color:#9AA59C;}")
_BTN_PRIMARY = ("QPushButton{background:#1F7A3A;color:#FFFFFF;border:1px solid #1F7A3A;border-radius:6px;"
                "padding:6px 14px;font-weight:600;}QPushButton:hover{background:#165C2B;}")
_PANEL = "QFrame#Panel{background:#FFFFFF;border:1px solid #DADFD8;border-radius:10px;}"
_NEW_TITLE = "New dashboard"


def _fmt_n(n: int) -> str:
    return f"{n:,}".replace(",", "'")


class SmartChartScreen(QWidget):
    def __init__(self, on_back: Optional[Callable] = None, on_open_series: Optional[Callable] = None,
                 sidebar_callbacks: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self.on_back = on_back
        self.on_open_series = on_open_series  # (exp_pk, series_pk, experiment_id)
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None
        self.ds: Optional[te.TrialDataset] = None
        self.catalog: List[te.Field] = []
        self.filters: List[Dict[str, Any]] = []      # filters on all pages = "Find trials"
        self.ply_scope = "any"
        self.view: Optional[Dict[str, Any]] = None   # loaded saved view

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._sidebar, content = sidebar_nav.wrap_body_with_sidebar(root)
        page = QWidget()
        page.setStyleSheet("QWidget#Page{background:#F4F6F3;}" + _PANEL)
        page.setObjectName("Page")
        content.addWidget(page)
        pv = QVBoxLayout(page)
        pv.setContentsMargins(20, 14, 20, 12)
        pv.setSpacing(10)

        # ── header ──────────────────────────────────────────────────────
        head = QHBoxLayout()
        self.btn_back = QPushButton("← Home")
        self.btn_back.setStyleSheet("QPushButton{background:transparent;color:#39a650;border:1px solid #39a650;"
                                    "border-radius:4px;padding:5px 10px;font-weight:600;}"
                                    "QPushButton:hover{background:#e8f5e9;}")
        self.btn_back.clicked.connect(lambda: self.on_back() if callable(self.on_back) else None)
        self.btn_back.setVisible(callable(on_back))
        head.addWidget(self.btn_back)
        tbox = QVBoxLayout()
        tbox.setSpacing(0)
        lbl_kicker = QLabel("SMART CHART")
        lbl_kicker.setStyleSheet(f"color:{ACCENT}; font-size:11px; font-weight:700; letter-spacing:1px;")
        self.lbl_title = QLabel(_NEW_TITLE)
        self.lbl_title.setStyleSheet("font-size:20px; font-weight:700; color:#1C2321;")
        tbox.addWidget(lbl_kicker)
        tbox.addWidget(self.lbl_title)
        head.addLayout(tbox, 1)
        self.btn_new = QPushButton("New")
        self.btn_new.setToolTip("New dashboard: empty, example or from a template")
        self.btn_open = QPushButton("Open view")
        self.btn_save = QPushButton("Save view")
        self.btn_share = QPushButton("Share…")
        self.btn_share.setToolTip("Share this view with people or groups - to view or to edit")
        self.btn_excel = QPushButton("Excel")
        self.btn_excel.setToolTip("Export the data of every visual of this page to Excel (one sheet per visual)")
        self.btn_reload = QPushButton("Reload")
        self.btn_reload.setToolTip("Load the latest data from the database (F5)")
        self.btn_pdf = QPushButton("PDF")
        for b in (self.btn_new, self.btn_open, self.btn_save, self.btn_share, self.btn_excel, self.btn_reload):
            b.setStyleSheet(_BTN)
            head.addWidget(b)
        self.btn_pdf.setStyleSheet(_BTN_PRIMARY)
        head.addWidget(self.btn_pdf)
        from ui.widgets.multilang_help import make_help_button
        head.addWidget(make_help_button("How does Smart Chart work?", self._open_help))
        pv.addLayout(head)
        self.btn_new.clicked.connect(self._on_new)
        self.btn_open.clicked.connect(self._open_view)
        self.btn_save.clicked.connect(self._save_view)
        self.btn_share.clicked.connect(self._share_view)
        self.btn_excel.clicked.connect(self._export_excel)
        self.btn_reload.clicked.connect(lambda: self.load_data(force=True))
        self.btn_pdf.clicked.connect(self._export_pdf)
        QShortcut(QKeySequence("F5"), self, activated=lambda: self.load_data(force=True))

        # ── body: the count of matching trials, then the dashboard ──────
        self.lbl_count = QLabel("Loading trials…")
        self.lbl_count.setStyleSheet("background:#E6F2E9; border:1px solid #BFDCC7; border-radius:10px;"
                                     "padding:8px 14px; color:#165C2B; font-size:14px;")
        pv.addWidget(self.lbl_count)
        from ui.smart_dashboard import SmartDashboard
        self.dashboard = SmartDashboard(self)
        pv.addWidget(self.dashboard, 1)
        root.addWidget(FooterBar())
        self._update_view_buttons()

    # ── lifecycle ───────────────────────────────────────────────────────
    def showEvent(self, event):  # noqa: N802
        try:
            import app_meta
            level = int((app_meta.current_user or {}).get("access_level") or 0)
            sidebar_nav.refresh_lazy_sidebar(self, level)
        except Exception:
            pass
        super().showEvent(event)
        if self.ds is None:
            QTimer.singleShot(0, self.load_data)

    def load_data(self, force: bool = False) -> None:
        """Load (or reload) all trials. Keeps the filters and the dashboard."""
        if self.ds is not None and not force:
            return
        QGuiApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.catalog = te.build_catalog()
            self.ds = te.TrialDataset(self.catalog)
        except Exception as e:
            QGuiApplication.restoreOverrideCursor()
            self.lbl_count.setText("The trials could not be loaded.")
            show_error(self, "Smart Chart", "The trials could not be loaded.", e)
            return
        finally:
            if QGuiApplication.overrideCursor() is not None:
                QGuiApplication.restoreOverrideCursor()
        known = set(self.ds.fields)
        self.filters = [f for f in self.filters if f.get("key") in known]
        if not force:
            _log("smart_dashboard_open")
        self.refresh()

    # ── filters on all pages (edited in the dashboard's Filters pane) ──────
    def set_ply_scope(self, scope: str) -> None:
        if scope in te.PLY_SCOPES and scope != self.ply_scope:
            self.ply_scope = scope
            self.refresh()

    def settings(self) -> Dict[str, Any]:
        return {"filters": [dict(f) for f in self.filters], "ply_scope": self.ply_scope,
                "mode": "dashboard", "dashboard": self.dashboard.spec}

    def refresh(self) -> None:
        if self.ds is None:
            return
        res = self.ds.apply(self.filters, self.ply_scope)
        summ = self.ds.summary(res)
        self.res = res
        self.lbl_count.setText(
            f"<span style='font-size:20px;font-weight:700'>{_fmt_n(summ['trials'])}</span>"
            f"&nbsp; <b>trials match</b> &nbsp;in {_fmt_n(summ['series'])} series · {summ['machines']} machines · "
            f"{summ['jets']} jets &nbsp;&nbsp;<span style='color:#2F4A37;font-size:12px'>"
            f"filters on all pages apply to every visual · reference samples excluded</span>")
        self.dashboard.refresh()

    # ── views ───────────────────────────────────────────────────────────
    def _update_view_buttons(self) -> None:
        ok = views.available()
        for b in (self.btn_open, self.btn_save):
            b.setEnabled(ok)
            if not ok:
                b.setToolTip("Saved views are not available in this database yet.")
        self._update_share_button()

    def _update_share_button(self) -> None:
        mine = bool(self.view) and views.can_share(self.view)
        self.btn_share.setVisible(views.available())
        self.btn_share.setEnabled(mine)
        self.btn_share.setToolTip("Share this view with people or groups - to view or to edit" if mine else
                                  "Save the view first - only its creator can share it")

    def _share_view(self) -> None:
        if not self.view:
            return
        from ui.smart_share_dialog import share_view
        share_view(self.view, self)

    def open_view_by_id(self, view_id: int) -> bool:
        """Open a saved view (from the Dashboards page: "Edit in Smart Chart")."""
        self.load_data()
        if self.ds is None:
            return False
        v = views.get_view(int(view_id))
        if v is None:
            QMessageBox.information(self, "Smart Chart", "This view no longer exists or is no longer shared with you.")
            return False
        missing = self.apply_settings(views.config_of(v))
        self.view = v
        self.lbl_title.setText(str(v.get("Name") or "View"))
        self._update_share_button()
        if missing:
            QMessageBox.information(self, "Open view",
                                    "Some fields of this view no longer exist and were left out:\n" + ", ".join(missing))
        return True

    def _on_new(self) -> None:
        from ui import smart_dashboard_engine as en
        menu = QMenu(self)
        menu.addAction("Empty page", lambda: self._new_dashboard(""))
        menu.addAction("Example page", lambda: self._new_dashboard(None))
        menu.addSeparator()
        sec = menu.addAction("Start from a template:")
        sec.setEnabled(False)
        for key, t in en.TEMPLATES.items():
            a = menu.addAction("   " + t["label"], lambda k=key: self._new_dashboard(k))
            a.setToolTip(t["tip"])
        menu.setToolTipsVisible(True)
        menu.exec(self.btn_new.mapToGlobal(self.btn_new.rect().bottomLeft()))

    def _new_dashboard(self, template) -> None:
        """New dashboard (the filters on all pages stay - they belong to Find trials)."""
        self.view = None
        self._update_share_button()
        self.lbl_title.setText(_NEW_TITLE)
        self.dashboard.start_from(template)
        self.refresh()

    def apply_settings(self, cfg: Dict[str, Any]) -> List[str]:
        """Apply a saved configuration; returns the names of unknown fields."""
        missing = []
        known = set(self.ds.fields) if self.ds else set()
        self.filters = []
        for f in cfg.get("filters") or []:
            if f.get("key") in known:
                self.filters.append(f)
            else:
                missing.append(str(f.get("key")))
        self.ply_scope = cfg.get("ply_scope") if cfg.get("ply_scope") in te.PLY_SCOPES else "any"
        self.dashboard.set_spec(cfg.get("dashboard"))
        self.refresh()
        return missing

    def _open_view(self) -> None:
        if self.ds is None:
            return
        dlg = _OpenViewDialog(self)
        if dlg.exec() != QDialog.Accepted or dlg.chosen is None:
            return
        v = dlg.chosen
        missing = self.apply_settings(views.config_of(v))
        self.view = v
        self.lbl_title.setText(str(v.get("Name") or "View"))
        self._update_share_button()
        _log("smart_chart_view_open")
        if missing:
            QMessageBox.information(self, "Open view",
                                    "Some fields of this view no longer exist and were left out:\n" + ", ".join(missing))

    def _save_view(self) -> None:
        dlg = _SaveViewDialog(self, self.view)
        if dlg.exec() != QDialog.Accepted:
            return
        name, shared, overwrite = dlg.values()
        owner = overwrite and self.view and views.is_owner(self.view)
        if overwrite and self.view and not owner:
            shared = None              # edit share: the creator's sharing stays
        try:
            vid = views.save_view(name, self.settings(), shared,
                                  view_id=int(self.view["ID"]) if (overwrite and self.view) else None)
        except Exception as e:
            show_error(self, "Save view", "The view could not be saved.", e)
            return
        if overwrite and self.view:
            self.view = {**self.view, "Name": name, **({} if shared is None else {"IsShared": int(shared)})}
        else:
            self.view = {"ID": vid, "Name": name, "IsShared": int(bool(shared)), "UserID": _uid(),
                         "MyRight": views.RIGHT_OWNER}
        self.lbl_title.setText(name)
        self._update_share_button()
        _log("smart_chart_view_save", "shared" if shared else "private" if shared is not None else "edit share")

    # ── export ──────────────────────────────────────────────────────────
    def _export_excel(self) -> None:
        from ui import smart_dashboard_engine as en
        visuals = en.active_page(self.dashboard.spec)["visuals"]
        if not visuals:
            QMessageBox.information(self, "Excel", "This page has no visuals.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export page to Excel",
                                              f"SmartChart_dashboard_{datetime.date.today():%Y%m%d}.xlsx",
                                              "Excel (*.xlsx)")
        if path:
            try:
                self.dashboard.write_excel(path, visuals)
                _log("smart_dashboard_excel", "page")
            except Exception as e:
                show_error(self, "Excel", "The Excel file could not be written.", e)

    def _export_pdf(self) -> None:
        pages = self.dashboard.spec["pages"]
        all_pages = False
        if len(pages) > 1:
            box = QMessageBox(self)
            box.setWindowTitle("PDF")
            box.setText("Which pages should go into the PDF?")
            b_this = box.addButton("This page", QMessageBox.AcceptRole)
            b_all = box.addButton(f"All {len(pages)} pages", QMessageBox.AcceptRole)
            box.addButton(QMessageBox.Cancel)
            box.exec()
            if box.clickedButton() not in (b_this, b_all):
                return
            all_pages = box.clickedButton() is b_all
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF",
                                              f"SmartChart_dashboard_{datetime.date.today():%Y%m%d}.pdf",
                                              "PDF (*.pdf)")
        if path:
            title = self.lbl_title.text()
            self.dashboard.export_pdf(path, all_pages, "" if title == _NEW_TITLE else title)

    def _open_help(self) -> None:
        from ui.widgets.help_texts_smart_chart import TEXTS
        from ui.widgets.multilang_help import show_help
        show_help(TEXTS, self)


# ── dialogs ──────────────────────────────────────────────────────────────
class _FairnessDialog(QDialog):
    """Details of the fairness check: one line per condition."""

    _LEVEL_TEXT = {"green": "fine", "amber": "check", "red": "problem"}
    _LEVEL_BG = {"green": "#E6F2E9", "amber": "#FFF4D6", "red": "#FDECEA"}

    def __init__(self, a, parent=None):
        super().__init__(parent)
        import html as _html
        self.apply_fix = False
        self.setWindowTitle("Is this comparison fair?")
        self.resize(900, 560)
        v = QVBoxLayout(self)
        groups = ", ".join(f"{g} ({n})" for g, n in a.groups[:8]) + (" …" if len(a.groups) > 8 else "")
        head = QLabel(f"<b style='font-size:15px'>{_html.escape(a.headline)}</b><br>"
                      f"Compared: {_html.escape(a.grouping)} - {_html.escape(groups)}<br>{_html.escape(a.sentence)}")
        head.setWordWrap(True)
        v.addWidget(head)
        expl = QLabel("For every recorded condition: how differently it is spread over the groups "
                      "(<i>imbalance</i>) and how much it changes the Y value within a group (<i>effect on Y</i>). "
                      "Only when both are high can the chart mislead.")
        expl.setWordWrap(True)
        expl.setStyleSheet("color:#5A6460;")
        v.addWidget(expl)
        heads = ["Condition", "Effect on Y", "Imbalance", "Rating", "In the groups"]
        tbl = QTableWidget(len(a.conditions), len(heads))
        tbl.setHorizontalHeaderLabels(heads)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setWordWrap(True)
        for r, c in enumerate(a.conditions):
            gs = [g for g, _n in a.groups if g in c.per_group][:6]
            vals = [c.title, _bar(c.influence), _bar(c.imbalance), self._LEVEL_TEXT[c.level],
                    " · ".join(f"{g}: {c.per_group[g]}" for g in gs)]
            for k, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if k == 3:
                    it.setBackground(QColor(self._LEVEL_BG[c.level]))
                tbl.setItem(r, k, it)
        tbl.horizontalHeader().setSectionResizeMode(len(heads) - 1, QHeaderView.Stretch)
        for k in range(len(heads) - 1):
            tbl.resizeColumnToContents(k)
        self._tbl = tbl
        v.addWidget(tbl, 1)
        if a.warnings:
            w = QLabel("<b>Also note</b><ul>" + "".join(f"<li>{_html.escape(t)}</li>" for _l, t in a.warnings)
                       + "</ul>")
            w.setWordWrap(True)
            v.addWidget(w)
        note = QLabel("This is a warning light, not a proof: only conditions recorded in TrippleT are checked "
                      "(not e.g. operator, spool condition or room climate). Green means nothing conspicuous was "
                      "found - not that the comparison is guaranteed to be fair.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#5A6460; font-size:12px;")
        v.addWidget(note)
        row = QHBoxLayout()
        if a.fix is not None:
            b = QPushButton("Make it fairer")
            b.setToolTip(a.fix_text)
            b.clicked.connect(self._fix)
            row.addWidget(b)
            lab = QLabel(_html.escape(a.fix_text))
            lab.setStyleSheet("color:#5A6460;")
            row.addWidget(lab, 1)
        elif a.fix_text:
            lab = QLabel(_html.escape(a.fix_text))
            lab.setWordWrap(True)
            row.addWidget(lab, 1)
        else:
            row.addStretch(1)
        bc = QPushButton("Close")
        bc.clicked.connect(self.reject)
        row.addWidget(bc)
        v.addLayout(row)

    def showEvent(self, ev):  # noqa: N802 - rows can only be fitted once the width is known
        super().showEvent(ev)
        QTimer.singleShot(0, self._tbl.resizeRowsToContents)

    def _fix(self) -> None:
        self.apply_fix = True
        self.accept()


def _bar(x: float) -> str:
    word = "high" if x >= 0.6 else ("medium" if x >= 0.3 else "low")
    return f"{word} ({x * 100:.0f} %)"


class _OpenViewDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Open view")
        self.resize(640, 480)
        self.chosen: Optional[Dict[str, Any]] = None
        v = QVBoxLayout(self)
        self.txt_q = QLineEdit()
        self.txt_q.setPlaceholderText("Search by name or owner…")
        self.txt_q.textChanged.connect(self._filter)
        v.addWidget(self.txt_q)
        self.lst = QListWidget()
        self.lst.itemDoubleClicked.connect(lambda _it: self._ok())
        v.addWidget(self.lst, 1)
        row = QHBoxLayout()
        self.btn_del = QPushButton("Delete")
        self.btn_del.clicked.connect(self._delete)
        row.addWidget(self.btn_del)
        row.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Open | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        row.addWidget(bb)
        v.addLayout(row)
        self.lst.currentItemChanged.connect(self._sync)
        self._fill()

    def _fill(self) -> None:
        self.lst.clear()
        try:
            rows = views.list_views()
        except Exception as e:
            show_error(self, "Open view", "The saved views could not be loaded.", e)
            rows = []
        if not rows:
            it = QListWidgetItem("No saved views yet.")
            it.setFlags(Qt.NoItemFlags)
            self.lst.addItem(it)
        for r in rows:
            when = r.get("UpdatedAt") or r.get("CreatedAt")
            when_s = when.strftime("%d.%m.%Y") if hasattr(when, "strftime") else ""
            right = r.get("MyRight")
            extra = (" · shared with you, can edit" if right == views.RIGHT_EDIT else
                     " · shared with you" if right == views.RIGHT_VIEW else
                     " · shared" if int(r.get("IsShared") or 0) else " · private")
            it = QListWidgetItem(f"{r.get('Name')}\n    {_view_kind(views.config_of(r))} · "
                                 f"{r.get('OwnerName') or ''}{extra} · {when_s}")
            it.setData(Qt.UserRole, r)
            self.lst.addItem(it)
        self._sync()

    def _filter(self, q: str) -> None:
        q = q.strip().lower()
        for i in range(self.lst.count()):
            it = self.lst.item(i)
            it.setHidden(bool(q) and q not in it.text().lower())

    def _sync(self, *_a) -> None:
        it = self.lst.currentItem()
        v = it.data(Qt.UserRole) if it is not None else None
        self.btn_del.setEnabled(bool(v) and views.can_delete(v))

    def _ok(self) -> None:
        it = self.lst.currentItem()
        if it is None or not it.data(Qt.UserRole):
            return
        self.chosen = it.data(Qt.UserRole)
        self.accept()

    def _delete(self) -> None:
        it = self.lst.currentItem()
        v = it.data(Qt.UserRole) if it is not None else None
        if not v or not views.can_delete(v):
            return
        if QMessageBox.question(self, "Delete view", f"Delete the view “{v.get('Name')}”?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            views.delete_view(int(v["ID"]))
        except Exception as e:
            show_error(self, "Delete view", "The view could not be deleted.", e)
        self._fill()


class _SaveViewDialog(QDialog):
    def __init__(self, parent, current: Optional[Dict[str, Any]]):
        super().__init__(parent)
        self.setWindowTitle("Save view")
        self.setMinimumWidth(420)
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Name"))
        self.txt = QLineEdit(str((current or {}).get("Name") or ""))
        self.txt.setPlaceholderText("e.g. PES 70–80 dtex: tenacity vs. air pressure")
        v.addWidget(self.txt)
        self.chk_shared = QCheckBox("Share with everybody")
        self.chk_shared.setChecked(bool(int((current or {}).get("IsShared") or 0)))
        v.addWidget(self.chk_shared)
        if current and not views.is_owner(current):
            # saving a view shared with me: its sharing belongs to the creator (a new copy starts private)
            self.chk_shared.setChecked(False)
            self.chk_shared.setToolTip("Only the creator can share this view - a new copy is yours to share")
        self.chk_new = QCheckBox("Save as a new view")
        can_overwrite = bool(current) and views.can_change(current)
        self.chk_new.setChecked(not can_overwrite)
        self.chk_new.setEnabled(can_overwrite)
        v.addWidget(self.chk_new)
        hint = QLabel("The filters are saved, not the list of trials - the view always shows today's data.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#5A6460; font-size:12px;")
        v.addWidget(hint)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(lambda: self.accept() if self.txt.text().strip() else self.txt.setFocus())
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def values(self):
        return self.txt.text().strip(), self.chk_shared.isChecked(), not self.chk_new.isChecked()


def _view_kind(cfg: Dict[str, Any]) -> str:
    """'Dashboard · 2 pages · 9 visuals'."""
    d = cfg.get("dashboard") if isinstance(cfg.get("dashboard"), dict) else {}
    pages = d.get("pages") or ([{"visuals": d.get("visuals") or []}])
    n_v = sum(len(p.get("visuals") or []) for p in pages)
    return f"Dashboard · {len(pages)} page{'s' if len(pages) != 1 else ''} · {n_v} visuals"


def _uid():
    try:
        import app_meta
        return (app_meta.current_user or {}).get("id")
    except Exception:
        return None


def _log(name: str, detail: str = "") -> None:
    try:
        from db.usage_log import log_usage_event
        log_usage_event("feature", name, detail)
    except Exception:
        pass
