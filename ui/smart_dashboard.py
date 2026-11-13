# ui/smart_dashboard.py
"""Smart Chart "Dashboard" mode (Nutzerwunsch 2026-10-30, "wie Power BI"):
pages with freely placed visuals, a Visualizations pane and a Fields pane
with all tables. It is Smart Chart (SmartChartScreen; the chart mode was removed 2026-11-02)
and shares its "Find trials" filters (= filters on all pages) and dataset.

Web page: ui/smart_dashboard_html.py (owns the layout = spec), computing:
ui/smart_dashboard_engine.py, the state and what the page asks: ui/smart_dashboard_core.py
(Qt-free since 2026-11-13, the web version uses it too). This widget = QWebEngineView + QWebChannel
and the Qt dialogs (filters = the same dialog as "Find trials", calculated fields, colour, fairness).
Cross-filtering: a click on a bar/box/matrix cell (or a slicer) filters all
OTHER visuals of the same page.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QWidget

from db import trial_explorer as te
from ui import smart_dashboard_engine as en
from ui.smart_dashboard_core import PANES, DashboardSession, _log

try:
    from PySide6.QtWebChannel import QWebChannel
    from PySide6.QtWebEngineWidgets import QWebEngineView
    _WEB = True
except Exception:  # pragma: no cover
    _WEB = False

logger = logging.getLogger(__name__)


class _Bridge(QObject):
    readySignal = Signal()
    specSignal = Signal(str)
    clickSignal = Signal(str, str)
    clearSignal = Signal(str)
    openSignal = Signal(int)
    paneSignal = Signal(str, bool)
    filterSignal = Signal(str, str, int)
    removeSignal = Signal(str, str, int)
    scopeSignal = Signal(str)
    calcSignal = Signal(str)
    selectSignal = Signal(str, str)
    excelSignal = Signal(str)
    imagesSignal = Signal(str)
    pickSignal = Signal(str, str, str)
    widthSignal = Signal(str, int)
    modelSignal = Signal(str)
    focusSignal = Signal(str)
    fairSignal = Signal(str)
    throughSignal = Signal(str, str, str)
    backSignal = Signal(bool)

    @Slot()
    def ready(self):
        self.readySignal.emit()

    @Slot(str)
    def updateSpec(self, spec_json: str):
        self.specSignal.emit(spec_json)

    @Slot(str, str)
    def visualClick(self, vid: str, click_json: str):
        self.clickSignal.emit(vid, click_json)

    @Slot(str)
    def clearCross(self, source: str):
        self.clearSignal.emit(source)

    @Slot(int)
    def openTrial(self, tid: int):
        self.openSignal.emit(int(tid))

    @Slot(str, bool)
    def paneState(self, pane: str, collapsed: bool):
        self.paneSignal.emit(pane, bool(collapsed))

    @Slot(str)
    def focusRows(self, vid: str):
        """Focus mode: the trials of one visual for the list below it."""
        self.focusSignal.emit(vid)

    @Slot(str)
    def fairDetails(self, vid: str):
        """Click on the fairness dot of a visual: the details dialog (with "Make it fairer")."""
        self.fairSignal.emit(vid)

    @Slot(str, str, str)
    def drillThrough(self, vid: str, click_json: str, page_id: str):
        """Right-click on a bar/cell/slice → "Drill through" to a detail page."""
        self.throughSignal.emit(vid, click_json, page_id)

    @Slot(bool)
    def drillBack(self, go_back: bool):
        """Leave the drill-through of the active page: True = back to the page it came from."""
        self.backSignal.emit(bool(go_back))

    @Slot(str)
    def modelFields(self, group: str):
        """Model view: how many trials have a value, for the fields of one group."""
        self.modelSignal.emit(group)

    @Slot(str, int)
    def paneWidth(self, pane: str, width: int):
        """A side pane was dragged wider/narrower; 0 = back to the standard width."""
        self.widthSignal.emit(pane, int(width))

    @Slot(str, str, int)
    def editFilter(self, scope: str, vid: str, index: int):
        """scope "all", "page" or "visual"; index -1 = add a new filter."""
        self.filterSignal.emit(scope, vid, int(index))

    @Slot(str, str, int)
    def removeFilter(self, scope: str, vid: str, index: int):
        self.removeSignal.emit(scope, vid, int(index))

    @Slot(str)
    def setPlyScope(self, scope: str):
        self.scopeSignal.emit(scope)

    @Slot(str)
    def editCalc(self, key: str):
        """"" = new calculated field."""
        self.calcSignal.emit(key)

    @Slot(str, str)
    def visualSelect(self, vid: str, ids_json: str):
        self.selectSignal.emit(vid, ids_json)

    @Slot(str)
    def exportVisual(self, vid: str):
        self.excelSignal.emit(vid)

    @Slot(str)
    def imagesReady(self, images_json: str):
        self.imagesSignal.emit(images_json)

    @Slot(str, str, str)
    def pickColour(self, vid: str, label: str, current: str):
        """Format → Colours: label "" = the one colour of a visual without legend."""
        self.pickSignal.emit(vid, label, current)


class SmartDashboard(QWidget):
    def __init__(self, screen, parent=None, read_only: bool = False):
        super().__init__(parent)
        self.screen = screen                      # SmartChartScreen: ds, catalog, filters, ply_scope, on_open_series
        # read_only (Dashboards page, Etappe 6): only slicers, clicks, drill-down, page tabs and
        # tooltips work - nothing is saved, no filters/fields/layout can be changed
        self.read_only = read_only
        self.session = DashboardSession(screen, read_only)
        self._ready = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        if not _WEB:
            lay.addWidget(QLabel("The dashboard needs PySide6-WebEngine."))
            self.web = None
            return
        self.web = QWebEngineView()
        self.bridge = _Bridge()
        b, s = self.bridge, self.session
        b.readySignal.connect(self._on_ready)
        b.specSignal.connect(lambda j: s.update_spec(j) and self.refresh())
        b.clickSignal.connect(lambda vid, c: s.click(vid, c) and self.refresh())
        b.clearSignal.connect(lambda src: (s.clear(src), self.refresh()))
        b.openSignal.connect(self._on_open)
        b.paneSignal.connect(self._on_pane)
        b.filterSignal.connect(self._on_filter)
        b.removeSignal.connect(self._on_remove_filter)
        b.scopeSignal.connect(self._on_ply_scope)
        b.calcSignal.connect(self._on_calc)
        b.selectSignal.connect(lambda vid, ids: (s.select(vid, ids), self.refresh()))
        b.excelSignal.connect(self._on_export_visual)
        b.imagesSignal.connect(self._on_images)
        b.pickSignal.connect(self._on_pick_colour)
        b.widthSignal.connect(self._on_pane_width)
        b.modelSignal.connect(lambda g: self._run(s.model_fields(g)))
        b.focusSignal.connect(lambda vid: self._run(s.focus_rows(vid)))
        b.fairSignal.connect(self._on_fair_details)
        b.throughSignal.connect(lambda vid, c, p: self._run(s.drill_through(vid, c, p)))
        b.backSignal.connect(lambda back: self._run(s.drill_back(back)))
        self._pdf_job: Optional[Dict[str, Any]] = None
        self.channel = QWebChannel()
        self.channel.registerObject("bridge", self.bridge)
        self.web.page().setWebChannel(self.channel)
        from ui.pathutil import web_base_url
        from ui.smart_dashboard_html import DASHBOARD_HTML
        self.web.setHtml(DASHBOARD_HTML, web_base_url())
        lay.addWidget(self.web)

    # ── the state lives in the session ──────────────────────────────────
    @property
    def spec(self) -> Dict[str, Any]:
        return self.session.spec

    @property
    def cross(self) -> Dict[str, List[Dict[str, Any]]]:
        return self.session.cross

    def catalog(self) -> List[te.Field]:
        return self.session.catalog()

    # ── page <-> python ─────────────────────────────────────────────────
    def _js(self, code: str) -> None:
        if self.web is not None and self._ready:
            self.web.page().runJavaScript(code)

    def _run(self, cmds) -> None:
        """Commands of the session -> JavaScript calls on the page."""
        for name, arg in cmds or []:
            args = arg if name in ("focusRows", "modelFields") else [arg]
            self._js(f"{name}({', '.join(json.dumps(a, default=str) for a in args)});")

    def _on_ready(self) -> None:
        self._ready = True
        self.send_init()

    def send_init(self) -> None:
        """Catalog + spec to the page, then all results."""
        if self._ready:
            self._run(self.session.init_cmds(self._panes(), self._pane_widths()))

    def set_spec(self, spec: Optional[Dict[str, Any]]) -> None:
        """From a saved view (or None = default page)."""
        self.session.set_spec(spec)
        self.send_init()

    def start_from(self, template: Optional[str]) -> None:
        self.session.start_from(template)
        self.send_init()

    def refresh(self) -> None:
        if self._ready:
            self._run(self.session.refresh_cmds(self._panes(), self._pane_widths()))

    def _push_spec(self) -> None:
        """Python changed the spec (filters) -> tell the page, then recompute."""
        if self._ready:
            self._run(self.session.spec_cmds())

    def _on_open(self, tid: int) -> None:
        t = self.session.trial_target(tid)
        if t is not None and callable(self.screen.on_open_series):
            self.screen.on_open_series(t["exp_pk"], t["series_id"], t["experiment"])

    # ── dialogs ─────────────────────────────────────────────────────────
    def _on_pick_colour(self, vid: str, label: str, current: str) -> None:
        if self.session.visual(vid) is None or self.read_only:
            return
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QColorDialog
        c = QColorDialog.getColor(QColor(current or "#2F6DB5"), self, f"Colour of {label}" if label else "Colour")
        if c.isValid() and self.session.set_colour(vid, label, c.name()):
            self._push_spec()

    def _after_filter_change(self, scope: str) -> None:
        if scope == "all":                 # "Find trials" = filters on all pages
            self.screen.refresh()          # count + dashboard
        else:
            self._push_spec()

    def _on_remove_filter(self, scope: str, vid: str, index: int) -> None:
        if self.session.remove_filter(scope, vid, index):
            self._after_filter_change(scope)

    def _on_ply_scope(self, scope: str) -> None:
        if not self.read_only:
            self.screen.set_ply_scope(scope)

    def _on_filter(self, scope: str, vid: str, index: int) -> None:
        ds = self.screen.ds
        if self.read_only or ds is None:
            return
        others, edit = self.session.filter_context(scope, vid, index)
        if others is None:
            return
        from ui.smart_chart_filter_dialog import AddFilterDialog
        dlg = AddFilterDialog(ds, self.catalog(), others + ([edit] if edit else []), self.screen.ply_scope,
                              edit=edit, parent=self)
        dlg.setWindowTitle(("Edit" if edit else "Add") + {"all": " filter on all pages", "page": " filter on this page",
                                                          "visual": " filter on this visual"}.get(scope, " filter"))
        if dlg.exec() != QDialog.Accepted or dlg.result_filter is None:
            return
        if self.session.put_filter(scope, vid, index if edit is not None else -1, dlg.result_filter):
            self._after_filter_change(scope)

    def _on_calc(self, key: str) -> None:
        if self.read_only or self.screen.ds is None:
            return
        self.session.apply_calc()
        existing = self.session.calc_def(key)
        if not key:
            key = self.session.next_calc_key()
        from ui.smart_calc_dialog import CalcFieldDialog
        dlg = CalcFieldDialog(self.screen.ds, existing, key, self)
        if dlg.exec() != QDialog.Accepted:
            return
        if dlg.deleted:
            self.session.save_calc(key, None)
        elif dlg.result_def:
            self.session.save_calc(key, dlg.result_def)
        self.send_init()

    def _on_fair_details(self, vid: str) -> None:
        a = self.session.fairness(vid)
        if a is None:
            return
        from ui.screen_smart_chart import _FairnessDialog
        dlg = _FairnessDialog(a, self)
        if dlg.exec() != QDialog.Accepted or not dlg.apply_fix or a.fix is None or self.read_only:
            return
        if self.session.apply_fair_fix(vid):
            self._push_spec()

    # ── Excel / PDF ─────────────────────────────────────────────────────
    def write_excel(self, path: str, visuals: List[Dict[str, Any]]) -> None:
        self.session.write_excel(path, visuals)

    def _on_export_visual(self, vid: str) -> None:
        if self.read_only:
            return
        v = self.session.visual(vid)
        if v is None:
            return
        from PySide6.QtWidgets import QFileDialog
        import datetime as _dt
        path, _ = QFileDialog.getSaveFileName(self, "Export visual to Excel",
                                              f"SmartChart_visual_{_dt.date.today():%Y%m%d}.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        try:
            self.write_excel(path, [v])
            _log("smart_dashboard_excel", "visual")
        except Exception as e:
            from ui.widgets.friendly_error import show_error
            show_error(self, "Excel", "The Excel file could not be written.", e)

    # PDF: the page renders the chart images, python lays out the pages
    def export_pdf(self, path: str, all_pages: bool, report_title: str) -> None:
        job, jobs = self.session.pdf_job(all_pages, report_title)
        self._pdf_job = {**job, "path": path}
        self._js(f"exportImages({json.dumps(jobs, default=str)});")

    def _on_images(self, images_json: str) -> None:
        job, self._pdf_job = self._pdf_job, None
        if job is None:
            return
        try:
            self.session.write_pdf_job(job["path"], job, images_json)
        except Exception as e:
            from ui.widgets.friendly_error import show_error
            show_error(self, "PDF", "The PDF could not be written.", e)
            return
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "PDF", f"PDF saved:\n{job['path']}")

    # ── collapsed panes, per Windows user (QSettings) ───────────────────
    @staticmethod
    def _settings():
        from PySide6.QtCore import QSettings
        return QSettings("TrippleT", "SmartChart")

    def _panes(self) -> Dict[str, bool]:
        s = self._settings()
        return {p: str(s.value(f"dashboard/pane_{p}", "0")) in ("1", "true", "True") for p in PANES}

    def _pane_widths(self) -> Dict[str, int]:
        s, out = self._settings(), {}
        for p in PANES:
            try:
                w = int(s.value(f"dashboard/pane_{p}_width", 0) or 0)
            except (TypeError, ValueError):
                w = 0
            if w:
                out[p] = w
        return out

    def _on_pane_width(self, pane: str, width: int) -> None:
        if pane in PANES:
            self._settings().setValue(f"dashboard/pane_{pane}_width", max(0, int(width)))

    def _on_pane(self, pane: str, collapsed: bool) -> None:
        if self.read_only:
            return
        if pane in PANES:
            self._settings().setValue(f"dashboard/pane_{pane}", "1" if collapsed else "0")


__all__ = ["SmartDashboard", "en"]
