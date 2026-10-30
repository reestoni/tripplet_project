# ui/screen_dashboards.py
"""Dashboards page (Etappe 6, Nutzerwunsch 2026-10-30): LOOK at your own
dashboards and the ones shared with you - Smart Chart is where they are
built. Left the list (My dashboards / Shared with me, search), right the
dashboard read-only (ui/smart_dashboard.py with read_only=True): slicers,
clicks on bars/cells (cross-filter), drill-down, page tabs and tooltips
work, nothing is saved; PDF yes, Excel no (Nutzerentscheid). "Edit in Smart
Chart" for the creator and people with an edit share.

Own dataset (not the one of Smart Chart): calculated fields are registered
per dashboard in the dataset, two open dashboards must not overwrite each
other's. Sidebar entry via app_meta.open_dashboards (set by main.py).
"""
from __future__ import annotations

import datetime
import logging
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
                               QSplitter, QStackedWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from db import smart_chart_views as views
from db import trial_explorer as te
from ui.widgets import sidebar_nav
from ui.widgets.friendly_error import show_error

logger = logging.getLogger(__name__)

ACCENT = "#1F7A3A"
_BTN = ("QPushButton{background:#FFFFFF;color:#1C2321;border:1px solid #C9D1C8;border-radius:6px;"
        "padding:6px 12px;font-weight:600;}QPushButton:hover{background:#EEF1ED;}"
        "QPushButton:disabled{color:#A0A7A2;}")
_BTN_PRIMARY = ("QPushButton{background:#1F7A3A;color:#FFFFFF;border:1px solid #1F7A3A;border-radius:6px;"
                "padding:6px 14px;font-weight:600;}QPushButton:hover{background:#18632F;}"
                "QPushButton:disabled{background:#A9C9B2;border-color:#A9C9B2;}")
MINE, SHARED = "My dashboards", "Shared with me"


class DashboardsScreen(QWidget):
    def __init__(self, on_open_series: Optional[Callable] = None, on_edit: Optional[Callable[[int], None]] = None,
                 sidebar_callbacks: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self.on_open_series = on_open_series      # (exp_pk, series_pk, experiment_id) - double-click in a table
        self.on_edit = on_edit                    # (view id) -> Smart Chart
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None
        # what SmartDashboard needs from its screen
        self.ds: Optional[te.TrialDataset] = None
        self.catalog: List[te.Field] = []
        self.filters: List[Dict[str, Any]] = []
        self.ply_scope = "any"
        self.grp_scope = None
        self.view: Optional[Dict[str, Any]] = None
        self._views: List[Dict[str, Any]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._sidebar, content = sidebar_nav.wrap_body_with_sidebar(root)
        page = QWidget()
        page.setObjectName("Page")
        page.setStyleSheet("QWidget#Page{background:#F4F6F3;}")
        content.addWidget(page)
        pv = QVBoxLayout(page)
        pv.setContentsMargins(20, 14, 20, 12)
        pv.setSpacing(10)

        head = QHBoxLayout()
        tbox = QVBoxLayout()
        tbox.setSpacing(0)
        kicker = QLabel("DASHBOARDS")
        kicker.setStyleSheet(f"color:{ACCENT}; font-size:11px; font-weight:700; letter-spacing:1px;")
        self.lbl_title = QLabel("Dashboards")
        self.lbl_title.setStyleSheet("font-size:20px; font-weight:700; color:#1C2321;")
        self.lbl_meta = QLabel("")
        self.lbl_meta.setStyleSheet("color:#5A6460; font-size:12px;")
        tbox.addWidget(kicker)
        tbox.addWidget(self.lbl_title)
        tbox.addWidget(self.lbl_meta)
        head.addLayout(tbox, 1)
        self.btn_edit = QPushButton("Edit in Smart Chart")
        self.btn_edit.setToolTip("Open this dashboard in Smart Chart to change it")
        self.btn_reload = QPushButton("Reload")
        self.btn_reload.setToolTip("Load the latest data and dashboards from the database (F5)")
        self.btn_pdf = QPushButton("PDF")
        self.btn_pdf.setToolTip("Save this page or all pages as PDF")
        for b in (self.btn_edit, self.btn_reload):
            b.setStyleSheet(_BTN)
            head.addWidget(b)
        self.btn_pdf.setStyleSheet(_BTN_PRIMARY)
        head.addWidget(self.btn_pdf)
        from ui.widgets.multilang_help import make_help_button
        head.addWidget(make_help_button("How do Dashboards work?", self._open_help))
        pv.addLayout(head)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_reload.clicked.connect(self.reload)
        self.btn_pdf.clicked.connect(self._export_pdf)
        from PySide6.QtGui import QKeySequence, QShortcut
        sc = QShortcut(QKeySequence("F5"), self)
        sc.setContext(Qt.WidgetWithChildrenShortcut)
        sc.activated.connect(self.reload)

        split = QSplitter(Qt.Horizontal)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 8, 0)
        self.txt_q = QLineEdit()
        self.txt_q.setPlaceholderText("Search a dashboard or owner…")
        self.txt_q.textChanged.connect(self._filter_list)
        lv.addWidget(self.txt_q)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setStyleSheet("QTreeWidget{background:#FFFFFF;border:1px solid #DADFD8;border-radius:6px;}"
                                "QTreeWidget::item{padding:5px 2px;}"
                                "QTreeWidget::item:selected{background:#E3F1E6;color:#1C2321;}")
        self.tree.itemSelectionChanged.connect(self._on_pick)
        lv.addWidget(self.tree, 1)
        split.addWidget(left)

        self.stack = QStackedWidget()
        self.lbl_empty = QLabel()
        self.lbl_empty.setAlignment(Qt.AlignCenter)
        self.lbl_empty.setWordWrap(True)
        self.lbl_empty.setStyleSheet("color:#5A6460; font-size:14px;")
        self.stack.addWidget(self.lbl_empty)
        from ui.smart_dashboard import SmartDashboard
        self.dashboard = SmartDashboard(self, read_only=True)
        self.stack.addWidget(self.dashboard)
        split.addWidget(self.stack)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([260, 1200])
        pv.addWidget(split, 1)
        self._set_empty("Loading…")
        self._sync_buttons()

    # ── lifecycle ───────────────────────────────────────────────────────
    def showEvent(self, event):  # noqa: N802
        try:
            import app_meta
            level = int((app_meta.current_user or {}).get("access_level") or 0)
            sidebar_nav.refresh_lazy_sidebar(self, level)
        except Exception:
            pass
        super().showEvent(event)
        QTimer.singleShot(0, self._first_show)

    def _first_show(self) -> None:
        self.load_list()
        if self.ds is None and self._views:
            self.load_data()

    def load_data(self, force: bool = False) -> None:
        if self.ds is not None and not force:
            return
        QGuiApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.catalog = te.build_catalog()
            self.ds = te.TrialDataset(self.catalog)
        except Exception as e:
            self._set_empty("The trials could not be loaded.")
            show_error(self, "Dashboards", "The trials could not be loaded.", e)
            return
        finally:
            QGuiApplication.restoreOverrideCursor()
        if self.view is not None:
            self._show(self.view)

    def reload(self) -> None:
        self.load_list()
        if self._views:
            self.load_data(force=True)

    # ── list ────────────────────────────────────────────────────────────
    def load_list(self) -> None:
        if not views.available():
            self._views = []
            self.tree.clear()
            self._set_empty("Dashboards are not available in this database yet.")
            return
        try:
            self._views = views.list_views(kind="dashboard")
        except Exception as e:
            self._views = []
            show_error(self, "Dashboards", "The dashboards could not be loaded.", e)
        keep = int(self.view["ID"]) if self.view else _last_view()
        self.tree.blockSignals(True)
        self.tree.clear()
        groups = {}
        for title in (MINE, SHARED):
            it = QTreeWidgetItem([title])
            it.setFlags(Qt.ItemIsEnabled)
            f = it.font(0)
            f.setBold(True)
            it.setFont(0, f)
            self.tree.addTopLevelItem(it)
            groups[title] = it
        chosen = None
        for v in self._views:
            mine = v.get("MyRight") == views.RIGHT_OWNER
            it = QTreeWidgetItem([str(v.get("Name") or "Dashboard")])
            it.setData(0, Qt.UserRole, v)
            it.setToolTip(0, _describe(v))
            if not mine:
                it.setText(0, f"{v.get('Name')}  ·  {v.get('OwnerName') or ''}")
            groups[MINE if mine else SHARED].addChild(it)
            if keep is not None and int(v["ID"]) == int(keep):
                chosen = it
        for title, it in groups.items():
            it.setExpanded(True)
            if not it.childCount():
                ph = QTreeWidgetItem(["none yet" if title == MINE else "nothing shared with you yet"])
                ph.setFlags(Qt.NoItemFlags)
                it.addChild(ph)
        self.tree.blockSignals(False)
        if chosen is None:
            chosen = next((groups[t].child(0) for t in (MINE, SHARED)
                           if groups[t].childCount() and groups[t].child(0).data(0, Qt.UserRole)), None)
        if chosen is not None:
            self.tree.setCurrentItem(chosen)        # -> _on_pick
        else:
            self.view = None
            self._set_empty("No dashboards yet.\n\nBuild one in Smart Chart → Dashboard and save it with "
                            "“Save view” - or ask a colleague to share one with you.")
        self._filter_list(self.txt_q.text())

    def _filter_list(self, q: str) -> None:
        q = q.strip().lower()
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            for j in range(top.childCount()):
                it = top.child(j)
                v = it.data(0, Qt.UserRole)
                text = (it.text(0) + " " + (_describe(v) if v else "")).lower()
                it.setHidden(bool(q) and bool(v) and q not in text)

    def _on_pick(self) -> None:
        it = self.tree.currentItem()
        v = it.data(0, Qt.UserRole) if it is not None else None
        if not v:
            return
        self.view = v
        _remember_view(int(v["ID"]))
        if self.ds is None:
            self.load_data()
            return
        self._show(v)

    def _show(self, v: Dict[str, Any]) -> None:
        cfg = views.config_of(v)
        known = set(self.ds.fields) if self.ds else set()
        self.filters = [f for f in cfg.get("filters") or [] if f.get("key") in known]
        self.ply_scope = cfg.get("ply_scope") if cfg.get("ply_scope") in te.PLY_SCOPES else "any"
        self.lbl_title.setText(str(v.get("Name") or "Dashboard"))
        self.lbl_meta.setText(_describe(v))
        self.stack.setCurrentWidget(self.dashboard)
        self.dashboard.set_spec(cfg.get("dashboard"))
        self._sync_buttons()
        try:
            from db.usage_log import log_usage_event
            log_usage_event("feature", "dashboards_view", "own" if v.get("MyRight") == views.RIGHT_OWNER else "shared")
        except Exception:
            pass

    def _set_empty(self, text: str) -> None:
        self.lbl_empty.setText(text)
        self.stack.setCurrentWidget(self.lbl_empty)
        self.lbl_title.setText("Dashboards")
        self.lbl_meta.setText("")
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        showing = self.view is not None and self.stack.currentWidget() is self.dashboard
        self.btn_pdf.setEnabled(showing)
        can_edit = showing and views.can_change(self.view) and callable(self.on_edit) and _smart_chart_allowed()
        self.btn_edit.setVisible(can_edit)

    # ── what SmartDashboard calls on its screen ─────────────────────────
    def refresh(self) -> None:
        self.dashboard.refresh()

    def _render_chips(self) -> None:
        pass

    # ── actions ─────────────────────────────────────────────────────────
    def _edit(self) -> None:
        if self.view is not None and callable(self.on_edit):
            self.on_edit(int(self.view["ID"]))

    def _export_pdf(self) -> None:
        if self.view is None or self.ds is None:
            return
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
        name = "".join(ch if ch.isalnum() or ch in "-_ " else "_" for ch in str(self.view.get("Name") or "Dashboard"))
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", f"{name.strip()}_{datetime.date.today():%Y%m%d}.pdf",
                                              "PDF (*.pdf)")
        if path:
            self.dashboard.export_pdf(path, all_pages, str(self.view.get("Name") or ""))

    def _open_help(self) -> None:
        from ui.widgets.help_texts_dashboards import TEXTS
        from ui.widgets.multilang_help import show_help
        show_help(TEXTS, self)


def _smart_chart_allowed() -> bool:
    """Editing happens in Smart Chart - only for who may use it (db/feature_access.py)."""
    try:
        from db.feature_access import can_use
        return can_use("smart_chart")
    except Exception:
        return True


def _describe(v: Dict[str, Any]) -> str:
    when = v.get("UpdatedAt") or v.get("CreatedAt")
    when_s = when.strftime("%d.%m.%Y") if hasattr(when, "strftime") else ""
    right = v.get("MyRight")
    who = "yours" if right == views.RIGHT_OWNER else f"by {v.get('OwnerName') or '?'}"
    can = {views.RIGHT_EDIT: " · you can edit it", views.RIGHT_VIEW: " · view only"}.get(right, "")
    cfg = views.config_of(v)
    pages = (cfg.get("dashboard") or {}).get("pages") or []
    n_p = len(pages)
    return f"{who}{can} · {n_p} page{'s' if n_p != 1 else ''} · changed {when_s}"


def _settings() -> QSettings:
    return QSettings("TrippleT", "Dashboards")


def _last_view() -> Optional[int]:
    try:
        v = _settings().value("last_view")
        return int(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _remember_view(view_id: int) -> None:
    try:
        _settings().setValue("last_view", int(view_id))
    except Exception:
        pass
