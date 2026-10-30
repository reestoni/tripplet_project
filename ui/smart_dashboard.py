# ui/smart_dashboard.py
"""Smart Chart "Dashboard" mode (Nutzerwunsch 2026-10-30, "wie Power BI"):
pages with freely placed visuals, a Visualizations pane and a Fields pane
with all tables. Lives inside SmartChartScreen (toggle Chart | Dashboard)
and shares its "Find trials" filters (= filters on all pages) and dataset.

Web page: ui/smart_dashboard_html.py (owns the layout = spec), computing:
ui/smart_dashboard_engine.py. Filters per page and per visual are added with
the same Qt dialog as "Find trials" (ui/smart_chart_filter_dialog.py).
Cross-filtering: a click on a bar/box/matrix cell (or a slicer) filters all
OTHER visuals of the same page.
"""
from __future__ import annotations

import copy
import json
import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QWidget

from db import trial_explorer as te
from ui import smart_dashboard_engine as en

try:
    from PySide6.QtWebChannel import QWebChannel
    from PySide6.QtWebEngineWidgets import QWebEngineView
    _WEB = True
except Exception:  # pragma: no cover
    _WEB = False

logger = logging.getLogger(__name__)
PANES = ("filters", "viz", "fields")


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


class SmartDashboard(QWidget):
    def __init__(self, screen, parent=None, read_only: bool = False):
        super().__init__(parent)
        self.screen = screen                      # SmartChartScreen: ds, catalog, filters, ply_scope, on_open_series
        # read_only (Dashboards page, Etappe 6): only slicers, clicks, drill-down, page tabs and
        # tooltips work - nothing is saved, no filters/fields/layout can be changed
        self.read_only = read_only
        self.spec: Dict[str, Any] = en.normalize_spec(None)
        self.cross: Dict[str, List[Dict[str, Any]]] = {}   # visual id -> filters from a click on it
        self._ready = False
        self._sent_catalog = None
        self._calc_fields: List[te.Field] = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        if not _WEB:
            lay.addWidget(QLabel("The dashboard needs PySide6-WebEngine."))
            self.web = None
            return
        self.web = QWebEngineView()
        self.bridge = _Bridge()
        self.bridge.readySignal.connect(self._on_ready)
        self.bridge.specSignal.connect(self._on_spec)
        self.bridge.clickSignal.connect(self._on_click)
        self.bridge.clearSignal.connect(self._on_clear)
        self.bridge.openSignal.connect(self._on_open)
        self.bridge.paneSignal.connect(self._on_pane)
        self.bridge.filterSignal.connect(self._on_filter)
        self.bridge.removeSignal.connect(self._on_remove_filter)
        self.bridge.scopeSignal.connect(self._on_ply_scope)
        self.bridge.calcSignal.connect(self._on_calc)
        self.bridge.selectSignal.connect(self._on_select)
        self.bridge.excelSignal.connect(self._on_export_visual)
        self.bridge.imagesSignal.connect(self._on_images)
        self._pdf_job: Optional[Dict[str, Any]] = None
        self.channel = QWebChannel()
        self.channel.registerObject("bridge", self.bridge)
        self.web.page().setWebChannel(self.channel)
        from ui.smart_dashboard_html import DASHBOARD_HTML
        self.web.setHtml(DASHBOARD_HTML, QUrl("about:blank"))
        lay.addWidget(self.web)

    # ── page <-> python ─────────────────────────────────────────────────
    def _js(self, code: str) -> None:
        if self.web is not None and self._ready:
            self.web.page().runJavaScript(code)

    def _on_ready(self) -> None:
        self._ready = True
        self.send_init()

    def send_init(self) -> None:
        """Catalog + spec to the page, then all results."""
        ds = self.screen.ds
        if ds is None or not self._ready:
            return
        self._apply_calc()
        full = self.catalog()
        cat = [{"key": f.key, "label": f.label, "group": f.group, "kind": f.kind} for f in full]
        data = {"catalog": cat, "groups": te.group_order(full), "tree": te.group_tree(full),
                "types": {k: {"label": t["label"], "tip": t["tip"], "wells": t["wells"], "agg": bool(t.get("agg")),
                              "target": bool(t.get("target")), "defagg": t.get("defagg") or ""}
                          for k, t in en.VISUAL_TYPES.items()},
                "wells": {k: list(v) for k, v in en.WELLS.items()}, "aggs": en.AGGS,
                "slicer_styles": en.SLICER_STYLES, "stacks": en.STACK_MODES, "month_of": en.MONTH_OF, "grid": {"cols": en.GRID_COLS, "row": en.GRID_ROW},
                "spec": self.spec, "panes": {} if self.read_only else self._panes(),
                "readonly": self.read_only}
        self._sent_catalog = (id(self.screen.catalog), json.dumps(self.spec.get("calc") or [], sort_keys=True))
        self._js(f"init({json.dumps(data)});")
        self.refresh()

    def catalog(self) -> List[te.Field]:
        return list(self._calc_fields) + list(self.screen.catalog)

    def _apply_calc(self) -> None:
        """Register this dashboard's calculated fields in the dataset."""
        ds = self.screen.ds
        if ds is not None:
            self._calc_fields = ds.set_calc_fields(self.spec.get("calc") or [])

    def set_spec(self, spec: Optional[Dict[str, Any]]) -> None:
        """From a saved view (or None = default page)."""
        self.spec = en.normalize_spec(copy.deepcopy(spec) if spec else None)
        self.cross = {}
        self.send_init()

    def _on_spec(self, spec_json: str) -> None:
        try:
            spec = json.loads(spec_json)
        except ValueError:
            return
        if not isinstance(spec, dict):
            return
        self.spec = en.normalize_spec(spec)
        ids = {v.get("id") for pg in self.spec["pages"] for v in pg["visuals"]}
        self.cross = {k: v for k, v in self.cross.items() if k in ids}
        self.refresh()

    def _push_spec(self) -> None:
        """Python changed the spec (filters) -> tell the page, then recompute."""
        self._js(f"setSpec({json.dumps(self.spec)});")
        self.refresh()

    # ── computing ───────────────────────────────────────────────────────
    def refresh(self) -> None:
        ds = self.screen.ds
        if ds is None or not self._ready:
            return
        if self._sent_catalog != (id(self.screen.catalog), json.dumps(self.spec.get("calc") or [], sort_keys=True)):
            self.send_init()           # data reloaded or calculated fields changed -> new catalog
            return
        if any(f.key not in ds.fields for f in self._calc_fields):
            self._apply_calc()         # dataset was rebuilt (Reload)
        base = list(self.screen.filters)
        page = en.active_page(self.spec)
        en.reset_notes(ds)
        results = {}
        for v in page["visuals"]:
            flt = en.visual_filters(ds, page, v, base, self.cross)
            try:
                r = en.compute_visual(ds, v, flt, self.screen.ply_scope)
            except Exception as e:
                logger.warning("dashboard visual %s: %s", v.get("id"), e)
                r = {"kind": "empty", "message": "This visual could not be calculated.", "title": v.get("title") or ""}
            r["vfilters"] = en.describe_filters(ds, v.get("filters") or [])
            results[v["id"]] = r
        cross = []
        for v in page["visuals"]:
            if v.get("id") in self.cross:
                cross.append({"source": v["id"], "from": v.get("title") or en.auto_title(ds, v),
                              "text": en.describe_cross(ds, self.cross[v["id"]])})
        slicers = []
        for v in page["visuals"]:
            sf = en.slicer_filter(ds, v)
            if sf is not None:
                n = len(v.get("targets") or []) if v.get("targets") is not None else None
                slicers.append({"source": v["id"], "text": en.describe_filters(ds, [sf])[0],
                                "to": "all visuals" if n is None else f"{n} visual{'s' if n != 1 else ''}"})
        payload = {"results": results, "cross": cross, "slicers": slicers, "page": page["id"],
                   "pageFilters": en.describe_filters(ds, page.get("filters") or []),
                   "allFilters": en.describe_filters(ds, list(self.screen.filters)),
                   "plyScope": self.screen.ply_scope}
        self._js(f"renderResults({json.dumps(payload, default=str)});")

    def _visual(self, vid: str) -> Optional[Dict[str, Any]]:
        return next((v for pg in self.spec["pages"] for v in pg["visuals"] if v.get("id") == vid), None)

    def _on_click(self, vid: str, click_json: str) -> None:
        v = self._visual(vid)
        if v is None or self.screen.ds is None:
            return
        try:
            click = json.loads(click_json)
        except ValueError:
            return
        flts = en.click_filters(self.screen.ds, v, click)
        if not flts:
            return
        if self.cross.get(vid) == flts:      # same click again = undo
            del self.cross[vid]
        else:
            self.cross[vid] = flts
            _log("smart_dashboard_crossfilter", v.get("type", ""))
        self.refresh()

    def _on_clear(self, source: str) -> None:
        self.cross.pop(source, None)
        self.refresh()

    def _on_open(self, tid: int) -> None:
        ds = self.screen.ds
        t = ds.by_id.get(tid) if ds else None
        if t is not None and t.exp_pk is not None and callable(self.screen.on_open_series):
            self.screen.on_open_series(t.exp_pk, t.series_id, t.experiment)

    # ── filters on a page / a visual ────────────────────────────────────
    def _filter_list(self, scope: str, vid: str) -> Optional[List[Dict[str, Any]]]:
        if scope == "all":
            return self.screen.filters
        page = en.active_page(self.spec)
        target = page if scope == "page" else self._visual(vid)
        return None if target is None else target.setdefault("filters", [])

    def _after_filter_change(self, scope: str) -> None:
        if scope == "all":                 # "Find trials" = filters on all pages
            self.screen._render_chips()
            self.screen.refresh()          # count + dashboard
        else:
            self._push_spec()

    def _on_remove_filter(self, scope: str, vid: str, index: int) -> None:
        if self.read_only:
            return
        flts = self._filter_list(scope, vid)
        if flts is not None and 0 <= index < len(flts):
            del flts[index]
            self._after_filter_change(scope)

    def _on_ply_scope(self, scope: str) -> None:
        if self.read_only:
            return
        if scope in te.PLY_SCOPES and scope != self.screen.ply_scope:
            self.screen.grp_scope.button(te.PLY_SCOPES.index(scope)).setChecked(True)
            self.screen._on_scope(te.PLY_SCOPES.index(scope))

    def _on_filter(self, scope: str, vid: str, index: int) -> None:
        if self.read_only:
            return
        ds = self.screen.ds
        if ds is None:
            return
        page = en.active_page(self.spec)
        flts = self._filter_list(scope, vid)
        if flts is None:
            return
        edit = flts[index] if 0 <= index < len(flts) else None
        # the dialog counts with everything that applies here, minus the filter being edited
        context = [] if scope == "all" else \
            list(self.screen.filters) + (list(page.get("filters") or []) if scope == "visual" else [])
        others = context + [f for f in flts if f is not edit]
        from ui.smart_chart_filter_dialog import AddFilterDialog
        dlg = AddFilterDialog(ds, self.catalog(), others + ([edit] if edit else []), self.screen.ply_scope,
                              edit=edit, parent=self)
        dlg.setWindowTitle(("Edit" if edit else "Add") + {"all": " filter on all pages", "page": " filter on this page",
                                                          "visual": " filter on this visual"}.get(scope, " filter"))
        if dlg.exec() != QDialog.Accepted or dlg.result_filter is None:
            return
        new = dlg.result_filter
        if edit is not None:
            flts[index] = new
        else:
            same = next((i for i, f in enumerate(flts) if f.get("key") == new["key"]), None)
            if same is not None:
                flts[same] = new
            else:
                flts.append(new)
        _log("smart_dashboard_filter", scope)
        self._after_filter_change(scope)

    # ── templates ───────────────────────────────────────────────────────
    def start_from(self, template: Optional[str]) -> None:
        """"" = empty page, None = default page, else a template of en.TEMPLATES."""
        if template == "":
            spec = en.normalize_spec({"pages": [{"id": "p1", "title": "Page 1", "visuals": []}], "active": "p1"})
        elif template:
            spec = en.template_spec(template)
            _log("smart_dashboard_template", template)
        else:
            spec = None
        self.set_spec(spec)

    # ── Excel ───────────────────────────────────────────────────────────
    def _filters_for(self, page: Dict[str, Any], v: Dict[str, Any]) -> List[Dict[str, Any]]:
        cross = self.cross if page is en.active_page(self.spec) else {}
        return en.visual_filters(self.screen.ds, page, v, list(self.screen.filters), cross)

    def write_excel(self, path: str, visuals: List[Dict[str, Any]]) -> None:
        from openpyxl import Workbook
        from openpyxl.styles import Font
        ds, page = self.screen.ds, en.active_page(self.spec)
        wb = Workbook()
        wb.remove(wb.active)
        used = set()
        for v in visuals:
            title, head, rows = en.visual_table(ds, v, self._filters_for(page, v), self.screen.ply_scope)
            name = "".join(ch for ch in (title or v["id"]) if ch not in '[]:*?/\\')[:28] or v["id"]
            base, k = name, 2
            while name.lower() in used:
                name = f"{base[:25]} {k}"
                k += 1
            used.add(name.lower())
            ws = wb.create_sheet(name)
            ws.append([title])
            ws["A1"].font = Font(bold=True, size=12)
            ws.append(head)
            for cell in ws[2]:
                cell.font = Font(bold=True)
            for row in rows:
                ws.append([x if not isinstance(x, (list, dict)) else str(x) for x in row])
        info = wb.create_sheet("Filters")
        info.append(["Smart Chart dashboard", page.get("title")])
        for t in en.describe_filters(ds, list(self.screen.filters)):
            info.append(["On all pages", t])
        for t in en.describe_filters(ds, page.get("filters") or []):
            info.append(["On this page", t])
        wb.save(path)

    def _on_export_visual(self, vid: str) -> None:
        if self.read_only:
            return
        v = self._visual(vid)
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

    # ── PDF: the page renders the chart images, python lays out the pages ─
    def export_pdf(self, path: str, all_pages: bool, report_title: str) -> None:
        ds = self.screen.ds
        pages_out, jobs = [], []
        pages = self.spec["pages"] if all_pages else [en.active_page(self.spec)]
        for pg in pages:
            vis = []
            for v in pg["visuals"]:
                try:
                    r = en.compute_visual(ds, v, self._filters_for(pg, v), self.screen.ply_scope)
                except Exception as e:
                    logger.warning("pdf visual %s: %s", v.get("id"), e)
                    r = {"kind": "empty", "message": "could not be calculated", "title": v.get("title") or ""}
                if r.get("kind") == "table" and v.get("type") == "table":
                    pass
                vis.append({**v, "result": r})
                if r.get("kind") == "plotly":
                    from ui.smart_dashboard_pdf import image_size
                    w, h = image_size(v)
                    jobs.append({"key": f"{pg['id']}:{v['id']}", "figure": r["figure"], "w": w, "h": h})
            pages_out.append({"id": pg["id"], "title": pg.get("title") or "", "visuals": vis,
                              "filters": en.describe_filters(ds, pg.get("filters") or [])})
        self._pdf_job = {"path": path, "pages": pages_out, "title": report_title,
                         "all": en.describe_filters(ds, list(self.screen.filters))}
        self._js(f"exportImages({json.dumps(jobs, default=str)});")

    def _on_images(self, images_json: str) -> None:
        job, self._pdf_job = self._pdf_job, None
        if job is None:
            return
        try:
            images = json.loads(images_json) or {}
            from ui.smart_dashboard_pdf import write_pdf
            write_pdf(job["path"], job["title"], job["pages"], job["all"], images)
            _log("smart_dashboard_pdf", str(len(job["pages"])))
        except Exception as e:
            from ui.widgets.friendly_error import show_error
            show_error(self, "PDF", "The PDF could not be written.", e)
            return
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "PDF", f"PDF saved:\n{job['path']}")

    # ── calculated fields / selection ───────────────────────────────────
    def _on_calc(self, key: str) -> None:
        if self.read_only:
            return
        ds = self.screen.ds
        if ds is None:
            return
        self._apply_calc()
        calc = self.spec.setdefault("calc", [])
        existing = next((c for c in calc if c.get("key") == key), None) if key else None
        if not key:
            n = max([int(str(c["key"]).split("_")[-1]) for c in calc if str(c["key"]).split("_")[-1].isdigit()] + [0])
            key = f"calc_{n + 1}"
        from ui.smart_calc_dialog import CalcFieldDialog
        dlg = CalcFieldDialog(ds, existing, key, self)
        if dlg.exec() != QDialog.Accepted:
            return
        if dlg.deleted:
            self.spec["calc"] = [c for c in calc if c.get("key") != key]
        elif dlg.result_def:
            if existing:
                existing.update(dlg.result_def)
            else:
                calc.append(dlg.result_def)
            _log("smart_dashboard_calc", "edit" if existing else "new")
        self.send_init()

    def _on_select(self, vid: str, ids_json: str) -> None:
        try:
            ids = [int(i) for i in json.loads(ids_json)]
        except (ValueError, TypeError):
            return
        if ids:
            self.cross[vid] = [{"ids": sorted(set(ids))}]
            _log("smart_dashboard_select")
        else:
            self.cross.pop(vid, None)
        self.refresh()

    # ── collapsed panes, per Windows user (QSettings) ───────────────────
    @staticmethod
    def _settings():
        from PySide6.QtCore import QSettings
        return QSettings("TrippleT", "SmartChart")

    def _panes(self) -> Dict[str, bool]:
        s = self._settings()
        return {p: str(s.value(f"dashboard/pane_{p}", "0")) in ("1", "true", "True") for p in PANES}

    def _on_pane(self, pane: str, collapsed: bool) -> None:
        if self.read_only:
            return
        if pane in PANES:
            self._settings().setValue(f"dashboard/pane_{pane}", "1" if collapsed else "0")


def _log(name: str, detail: str = "") -> None:
    try:
        from db.usage_log import log_usage_event
        log_usage_event("feature", name, detail)
    except Exception:
        pass
