# ui/smart_dashboard_core.py
"""Smart Chart dashboard - the controller WITHOUT Qt (2026-11-13, for the web version): what the page
(ui/smart_dashboard_html.py) asks through its bridge and what goes back to it. Used by the desktop
widget (ui/smart_dashboard.py, QWebChannel) and by the web (tripplet_web backend/app/smart_chart_api.py,
fetch). Computing: ui/smart_dashboard_engine.py.

A session holds the dashboard state of ONE open page: spec, clicks (cross), drill-through, calculated
fields. Its `host` provides ds, catalog, filters ("Find trials" = filters on all pages) and ply_scope
(the desktop: SmartChartScreen / DashboardsScreen).

Results for the page are "commands": [function name, argument] pairs the page runs
(init, setSpec, renderResults, goPage, toast, focusRows, modelFields, exportImages)."""
from __future__ import annotations

import copy
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from db import trial_explorer as te
from ui import smart_dashboard_engine as en

logger = logging.getLogger(__name__)
PANES = ("filters", "viz", "fields")
RESULT_CACHE = 200          # computed visuals kept per open dashboard
FILTER_SCOPES = ("all", "page", "visual")
Cmd = Tuple[str, Any]


class DashboardSession:
    def __init__(self, host: Any, read_only: bool = False):
        self.host = host
        self.read_only = read_only
        self.spec: Dict[str, Any] = en.normalize_spec(None)
        self.cross: Dict[str, List[Dict[str, Any]]] = {}     # visual id -> filters from a click on it
        # drill-through: detail page id -> {"from": page id, "filters": [...]} (never saved, like clicks)
        self.through: Dict[str, Dict[str, Any]] = {}
        self._calc_fields: List[te.Field] = []
        self._sent_catalog = None
        # results per visual (2026-11-13): a visual is only computed again when what it shows changes -
        # moving / resizing a visual, renaming a page or a change on another visual costs nothing
        self._results: Dict[str, Dict[str, Any]] = {}
        self._results_ds = None

    # ── catalog / spec ─────────────────────────────────────────────────
    @property
    def ds(self) -> Optional[te.TrialDataset]:
        return self.host.ds

    def catalog(self) -> List[te.Field]:
        return list(self._calc_fields) + list(self.host.catalog)

    def apply_calc(self) -> None:
        """Register this dashboard's calculated fields in the dataset."""
        if self.ds is not None:
            self._calc_fields = self.ds.set_calc_fields(self.spec.get("calc") or [])

    def _catalog_sig(self):
        return (id(self.host.catalog), json.dumps(self.spec.get("calc") or [], sort_keys=True))

    def init_data(self, panes: Optional[Dict[str, bool]] = None,
                  pane_widths: Optional[Dict[str, int]] = None) -> Optional[Dict[str, Any]]:
        """Catalog + spec for the page's init()."""
        ds = self.ds
        if ds is None:
            return None
        self.apply_calc()
        full = self.catalog()
        cat = [{"key": f.key, "label": f.label, "group": f.group, "kind": f.kind} for f in full]
        data = {"catalog": cat, "groups": te.group_order(full), "tree": te.group_tree(full),
                "types": {k: {"label": t["label"], "tip": t["tip"], "wells": t["wells"], "agg": bool(t.get("agg")),
                              "target": bool(t.get("target")), "defagg": t.get("defagg") or "",
                              "nocount": bool(t.get("nocount"))}
                          for k, t in en.VISUAL_TYPES.items()},
                "wells": {k: list(v) for k, v in en.WELLS.items()}, "aggs": en.AGGS,
                "slicer_styles": en.SLICER_STYLES, "stacks": en.STACK_MODES,
                "formats": en.FORMAT_SECTIONS, "pie_shapes": en.PIE_SHAPES,
                "point_sizes": {k: p[0] for k, p in en.POINT_SIZES.items()}, "sorts": en.SORTS,
                "legend_pos": en.LEGEND_POS,
                "palettes": {k: p["label"] for k, p in en.PALETTES.items()}, "matrix_scales": en.MATRIX_SCALES,
                "font_sizes": {k: f[0] for k, f in en.FONT_SIZES.items()},
                "card_sizes": {k: c[0] for k, c in en.CARD_SIZES.items()},
                "analytics": {"kinds": en.ANALYTICS_KINDS, "colours": en.ANALYTICS_COLOURS,
                              "defaults": en.ANALYTICS_DEFAULT_COLOUR, "types": list(en.ANALYTICS_TYPES)},
                "rule_ops": en.RULE_OPS, "rule_colours": en.RULE_COLOURS, "month_of": en.MONTH_OF,
                "multi_wells": list(en.MULTI_WELLS), "grid": {"cols": en.GRID_COLS, "row": en.GRID_ROW},
                "spec": self.spec, "panes": {} if self.read_only else (panes or {}),
                "pane_widths": pane_widths or {},
                "model": en.model_info(full), "trials": len(ds.trials), "readonly": self.read_only}
        self._sent_catalog = self._catalog_sig()
        return data

    def init_cmds(self, panes=None, pane_widths=None) -> List[Cmd]:
        data = self.init_data(panes, pane_widths)
        if data is None:
            return []
        return [("init", data)] + self.refresh_cmds()

    def set_spec(self, spec: Optional[Dict[str, Any]]) -> None:
        """From a saved view (or None = default page). Clicks and drill-throughs are dropped."""
        self.spec = en.normalize_spec(copy.deepcopy(spec) if spec else None)
        self.cross = {}
        self.through = {}

    def update_spec(self, spec: Any) -> bool:
        """The page changed the layout (spec as dict or JSON). Keeps clicks of visuals that still exist."""
        if isinstance(spec, str):
            try:
                spec = json.loads(spec)
            except ValueError:
                return False
        if not isinstance(spec, dict):
            return False
        self.spec = en.normalize_spec(spec)
        ids = {v.get("id") for pg in self.spec["pages"] for v in pg["visuals"]}
        self.cross = {k: v for k, v in self.cross.items() if k in ids}
        pages = {pg["id"] for pg in self.spec["pages"]}
        self.through = {k: v for k, v in self.through.items() if k in pages}
        return True

    def spec_cmds(self) -> List[Cmd]:
        """Python changed the spec -> tell the page, then the results."""
        return [("setSpec", self.spec)] + self.refresh_cmds()

    def visual(self, vid: str) -> Optional[Dict[str, Any]]:
        return next((v for pg in self.spec["pages"] for v in pg["visuals"] if v.get("id") == vid), None)

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

    # ── computing ───────────────────────────────────────────────────────
    def base(self, page: Dict[str, Any]) -> List[Dict[str, Any]]:
        """"Find trials" + the drill-through filters of the page."""
        return list(self.host.filters) + list((self.through.get(page.get("id")) or {}).get("filters") or [])

    def through_info(self, page: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        dt = self.through.get(page.get("id"))
        if not dt or self.ds is None:
            return None
        src = next((p for p in self.spec["pages"] if p["id"] == dt.get("from")), None)
        return {"from": dt.get("from") if src else "", "fromTitle": (src or {}).get("title") or "",
                "text": en.describe_filters(self.ds, dt.get("filters") or [])}

    def filters_for(self, page: Dict[str, Any], v: Dict[str, Any]) -> List[Dict[str, Any]]:
        """The filters of visual v as shown: with clicks on the page, a highlighting visual keeps all its
        trials (the clicks only grey out), the others are filtered by them."""
        cross = self.cross if page is en.active_page(self.spec) else {}
        if en.highlights(self.spec, v, en.page_cross(page, cross)):
            cross = {}
        return en.visual_filters(self.ds, page, v, self.base(page), cross)

    def result(self, page: Dict[str, Any], v: Dict[str, Any]) -> Dict[str, Any]:
        """Visual v computed as the dashboard shows it (highlighted or filtered by clicks).
        Cached: same visual settings + filters + clicks + data = same result (a fresh copy is returned)."""
        ds = self.ds
        cross = self.cross if page is en.active_page(self.spec) else {}
        clicks = en.page_cross(page, cross)
        flt = self.filters_for(page, v)
        hl = en.highlights(self.spec, v, clicks)     # grey out instead of filtering (Nutzerwunsch 2026-11-03)
        tv = en.themed(self.spec, v)
        if self._results_ds is not ds:
            self._results, self._results_ds = {}, ds
        key = self._result_key(tv, flt, clicks if hl else None)
        hit = self._results.get(key)
        if hit is None:
            hit = en.highlight_visual(ds, tv, flt, flt + clicks, self.host.ply_scope) if hl else \
                en.compute_visual(ds, tv, flt, self.host.ply_scope)
            if len(self._results) >= RESULT_CACHE:
                self._results.pop(next(iter(self._results)))
            self._results[key] = hit
        return copy.deepcopy(hit)

    def _result_key(self, tv: Dict[str, Any], flt, clicks) -> str:
        shown = {k: val for k, val in tv.items() if k not in ("x", "y", "w", "h")}   # the place does not matter
        return json.dumps([shown, flt, clicks, self.host.ply_scope, self.spec.get("calc") or []],
                          sort_keys=True, default=str)

    def clear_results(self) -> None:
        """Forget the computed visuals (Reload: new data, new notes)."""
        self._results = {}

    def needs_init(self) -> bool:
        return self._sent_catalog != self._catalog_sig()

    def refresh_payload(self) -> Optional[Dict[str, Any]]:
        ds = self.ds
        if ds is None:
            return None
        if any(f.key not in ds.fields for f in self._calc_fields):
            self.apply_calc()         # dataset was rebuilt (Reload)
        page = en.active_page(self.spec)
        en.reset_notes(ds)
        results = {}
        for v in page["visuals"]:
            try:
                r = self.result(page, v)
            except Exception as e:
                logger.warning("dashboard visual %s: %s", v.get("id"), e)
                r = {"kind": "empty", "message": "This visual could not be calculated.", "title": v.get("title") or ""}
            r["vfilters"] = en.describe_filters(ds, v.get("filters") or [])
            through = en.drill_through_pages(self.spec, ds, v, page["id"])
            if through:
                r["through"] = through
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
        return {"results": results, "cross": cross, "slicers": slicers, "page": page["id"],
                "pageFilters": en.describe_filters(ds, page.get("filters") or []),
                "allFilters": en.describe_filters(ds, list(self.host.filters)),
                "plyScope": self.host.ply_scope, "refs": bool(getattr(ds, "include_refs", False)),
                "through": self.through_info(page)}

    def refresh_cmds(self, panes=None, pane_widths=None) -> List[Cmd]:
        if self.ds is None:
            return []
        if self.needs_init():         # data reloaded or calculated fields changed -> new catalog
            return self.init_cmds(panes, pane_widths)
        payload = self.refresh_payload()
        return [] if payload is None else [("renderResults", payload)]

    # ── clicks, selection, drill-through ────────────────────────────────
    def click(self, vid: str, click: Any) -> bool:
        """A click on a bar/cell/slice: cross-filter the other visuals (same click again = undo)."""
        v = self.visual(vid)
        if v is None or self.ds is None:
            return False
        if isinstance(click, str):
            try:
                click = json.loads(click)
            except ValueError:
                return False
        flts = en.click_filters(self.ds, v, click)
        if not flts:
            return False
        if self.cross.get(vid) == flts:
            del self.cross[vid]
        else:
            self.cross[vid] = flts
            _log("smart_dashboard_crossfilter", v.get("type", ""))
        return True

    def clear(self, source: str) -> None:
        self.cross.pop(source, None)

    def select(self, vid: str, ids: Any) -> None:
        """Lasso / box selection on a point chart."""
        if isinstance(ids, str):
            try:
                ids = json.loads(ids)
            except ValueError:
                return
        try:
            ids = [int(i) for i in ids or []]
        except (TypeError, ValueError):
            return
        if ids:
            self.cross[vid] = [{"ids": sorted(set(ids))}]
            _log("smart_dashboard_select")
        else:
            self.cross.pop(vid, None)

    def drill_through(self, vid: str, click: Any, page_id: str) -> List[Cmd]:
        ds = self.ds
        src = en.active_page(self.spec)
        v = next((x for x in src["visuals"] if x.get("id") == vid), None)
        target = next((p for p in self.spec["pages"] if p["id"] == page_id), None)
        if ds is None or v is None or target is None or target is src:
            return []
        if isinstance(click, str):
            try:
                click = json.loads(click)
            except ValueError:
                return []
        # the clicked visual's own filters, page filters, clicks and slicers - without "Find trials",
        # which applies on the detail page anyway
        context = en.visual_filters(ds, src, v, self.base(src)[len(self.host.filters):], self.cross)
        flts = en.drill_through_filters(ds, v, click, target, context)
        if not flts:
            return [("toast", "Nothing to drill through here - the detail page needs one of the fields of this visual")]
        self.through[page_id] = {"from": src["id"], "filters": flts}
        _log("smart_dashboard_drillthrough", v.get("type", ""))
        self.spec["active"] = page_id
        return [("goPage", page_id)]

    def drill_back(self, go_back: bool) -> List[Cmd]:
        page = en.active_page(self.spec)
        dt = self.through.pop(page["id"], None)
        back = (dt or {}).get("from")
        if go_back and back and any(p["id"] == back for p in self.spec["pages"]):
            self.spec["active"] = back
            return [("goPage", back)]
        return self.refresh_cmds()

    def trial_target(self, tid: int) -> Optional[Dict[str, Any]]:
        """Double-click on a trial: where Show Experiment opens."""
        t = self.ds.by_id.get(int(tid)) if self.ds else None
        if t is None or t.exp_pk is None:
            return None
        return {"exp_pk": t.exp_pk, "series_id": t.series_id, "experiment": t.experiment}

    # ── filters on all pages / a page / a visual ─────────────────────────
    def filter_list(self, scope: str, vid: str = "") -> Optional[List[Dict[str, Any]]]:
        if scope == "all":
            return self.host.filters
        page = en.active_page(self.spec)
        target = page if scope == "page" else self.visual(vid)
        return None if target is None else target.setdefault("filters", [])

    def filter_context(self, scope: str, vid: str, index: int):
        """(filters the dialog counts with - minus the edited one, the edited filter or None)."""
        flts = self.filter_list(scope, vid)
        if flts is None:
            return None, None
        page = en.active_page(self.spec)
        edit = flts[index] if 0 <= index < len(flts) else None
        context = [] if scope == "all" else \
            list(self.host.filters) + (list(page.get("filters") or []) if scope == "visual" else [])
        return context + [f for f in flts if f is not edit], edit

    def put_filter(self, scope: str, vid: str, index: int, new: Dict[str, Any]) -> bool:
        """Edited (index >= 0) or new filter; a new one replaces a filter on the same field."""
        flts = self.filter_list(scope, vid)
        if flts is None or self.read_only:
            return False
        if 0 <= index < len(flts):
            flts[index] = new
        else:
            same = next((i for i, f in enumerate(flts) if f.get("key") == new.get("key")), None)
            if same is not None:
                flts[same] = new
            else:
                flts.append(new)
        _log("smart_dashboard_filter", scope)
        return True

    def remove_filter(self, scope: str, vid: str, index: int) -> bool:
        flts = self.filter_list(scope, vid)
        if self.read_only or flts is None or not (0 <= index < len(flts)):
            return False
        del flts[index]
        return True

    # ── colours, calculated fields, fairness ─────────────────────────────
    def set_colour(self, vid: str, label: str, colour: str) -> bool:
        """Format → Colours: label "" = the one colour of a visual without legend."""
        v = self.visual(vid)
        if v is None or self.read_only:
            return False
        fmt = v.setdefault("fmt", {})
        if label:
            fmt.setdefault("colours", {})[label] = colour
        else:
            fmt["colour"] = colour
        return True

    def next_calc_key(self) -> str:
        calc = self.spec.get("calc") or []
        n = max([int(str(c["key"]).split("_")[-1]) for c in calc if str(c["key"]).split("_")[-1].isdigit()] + [0])
        return f"calc_{n + 1}"

    def calc_def(self, key: str) -> Optional[Dict[str, Any]]:
        return next((c for c in self.spec.get("calc") or [] if c.get("key") == key), None) if key else None

    def save_calc(self, key: str, definition: Optional[Dict[str, Any]]) -> None:
        """definition None = delete the calculated field."""
        calc = self.spec.setdefault("calc", [])
        existing = self.calc_def(key)
        if definition is None:
            self.spec["calc"] = [c for c in calc if c.get("key") != key]
            return
        if existing:
            existing.update(definition)
        else:
            calc.append(definition)
        _log("smart_dashboard_calc", "edit" if existing else "new")

    def page_filters_of(self, vid: str):
        """(visual, filters) of a visual on the active page, as the dashboard computes it."""
        page = en.active_page(self.spec)
        v = next((x for x in page["visuals"] if x.get("id") == vid), None)
        if self.ds is None or v is None:
            return None, []
        return v, self.filters_for(page, v)

    def focus_rows(self, vid: str) -> List[Cmd]:
        v, flt = self.page_filters_of(vid)
        if v is None:
            return []
        try:
            data = en.focus_rows(self.ds, en.themed(self.spec, v), flt, self.host.ply_scope)
        except Exception as e:
            logger.warning("focus rows %s: %s", vid, e)
            data = {"head": [], "rows": [], "more": 0}
        _log("smart_dashboard_focus", v.get("type", ""))
        return [("focusRows", [vid, data])]

    def fairness(self, vid: str):
        v, flt = self.page_filters_of(vid)
        if v is None:
            return None
        a = en.fairness_of(self.ds, en.themed(self.spec, v), flt, self.host.ply_scope)
        if a is not None:
            _log("smart_dashboard_fairness_details", a.level)
        return a

    def apply_fair_fix(self, vid: str) -> bool:
        """"Make it fairer" -> a filter on this visual (replaces one on the same field)."""
        if self.read_only:
            return False
        v, flt = self.page_filters_of(vid)
        if v is None:
            return False
        a = en.fairness_of(self.ds, en.themed(self.spec, v), flt, self.host.ply_scope)
        if a is None or a.fix is None:
            return False
        new = dict(a.fix)
        v["filters"] = [f for f in v.get("filters") or [] if f.get("key") != new.get("key")] + [new]
        _log("smart_dashboard_fairer", str(new.get("key")))
        return True

    def model_fields(self, group: str) -> List[Cmd]:
        if self.ds is None:
            return []
        keys = [f.key for f in self.catalog() if f.group == group]
        return [("modelFields", [group, en.filled_counts(self.ds, keys), len(self.ds.trials)])]

    # ── Excel / PDF ──────────────────────────────────────────────────────
    def write_excel(self, target: Any, visuals: List[Dict[str, Any]]) -> None:
        """target = path or binary file object."""
        from openpyxl import Workbook
        from openpyxl.styles import Font
        ds, page = self.ds, en.active_page(self.spec)
        wb = Workbook()
        wb.remove(wb.active)
        used = set()
        for v in visuals:
            title, head, rows = en.visual_table(ds, en.themed(self.spec, v), self.filters_for(page, v),
                                                self.host.ply_scope)
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
        for t in en.describe_filters(ds, list(self.host.filters)):
            info.append(["On all pages", t])
        for t in en.describe_filters(ds, page.get("filters") or []):
            info.append(["On this page", t])
        for t in (self.through_info(page) or {}).get("text") or []:
            info.append(["Drill-through", t])
        wb.save(target)

    def pdf_job(self, all_pages: bool, report_title: str):
        """(job for write_pdf_job, image jobs for the page's exportImages())."""
        from ui.smart_dashboard_pdf import image_size
        ds = self.ds
        pages_out, jobs = [], []
        pages = self.spec["pages"] if all_pages else [en.active_page(self.spec)]
        for pg in pages:
            vis = []
            for v in pg["visuals"]:
                try:
                    r = self.result(pg, v)
                except Exception as e:
                    logger.warning("pdf visual %s: %s", v.get("id"), e)
                    r = {"kind": "empty", "message": "could not be calculated", "title": v.get("title") or ""}
                vis.append({**v, "result": r})
                if r.get("kind") == "plotly":
                    w, h = image_size(v, max(int(o["y"]) + int(o["h"]) for o in pg["visuals"]))
                    jobs.append({"key": f"{pg['id']}:{v['id']}", "figure": r["figure"], "w": w, "h": h})
            pages_out.append({"id": pg["id"], "title": pg.get("title") or "", "visuals": vis,
                              "filters": en.describe_filters(ds, pg.get("filters") or [])
                              + [f"Drill-through: {t}" for t in (self.through_info(pg) or {}).get("text") or []]})
        job = {"pages": pages_out, "title": report_title, "all": en.describe_filters(ds, list(self.host.filters))}
        return job, jobs

    @staticmethod
    def write_pdf_job(target: Any, job: Dict[str, Any], images: Any) -> None:
        """target = path or binary file object; images = {key: base64 png} (or its JSON)."""
        from ui.smart_dashboard_pdf import write_pdf
        if isinstance(images, str):
            images = json.loads(images) or {}
        write_pdf(target, job["title"], job["pages"], job["all"], images or {})
        _log("smart_dashboard_pdf", str(len(job["pages"])))


# ── the filter editor ("+ Add filter" / a filter chip; desktop ui/smart_chart_filter_dialog.py) ──
def parse_num(t: Any) -> Optional[float]:
    t = str(t if t is not None else "").strip().replace(",", ".")
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        return None


def snap(v: float) -> float:
    """Round a value dragged on the histogram to a readable number."""
    if v == 0:
        return 0.0
    mag = 10 ** (len(str(int(abs(v)))) - 2) if abs(v) >= 10 else 0.1
    return round(round(v / mag) * mag, 4)


def field_overview(ds: te.TrialDataset, key: str, others: List[Dict[str, Any]], ply_scope: str) -> Dict[str, Any]:
    """What the editor shows for a field, counted over the trials the OTHER filters leave:
    number field -> histogram; list field -> values with counts (+ the labels for From/To of time fields)."""
    f = ds.fields[key]
    vals = ds.field_values(key, others, ply_scope)
    out: Dict[str, Any] = {"key": f.key, "label": f.label, "group": f.group, "unit": f.unit, "kind": f.kind,
                           "level": f.level, "time": f.key in te.TIME_KEYS}
    if f.kind == "num":
        out["hist"] = te.histogram(vals)
    else:
        cats = te.category_counts(vals)
        out["cats"] = [[lab, n] for lab, n in cats]
        if out["time"]:
            out["periods"] = te.PERIODS
            out["time_labels"] = sorted(lab for lab, _n in cats if lab != te.NONE_LABEL)
    return out


def number_values(ds: te.TrialDataset, key: str, others: List[Dict[str, Any]], ply_scope: str,
                  lo: Optional[float], hi: Optional[float]) -> Optional[List[List[float]]]:
    """"Pick values": the numbers between From and To with counts; None = too many to pick from."""
    vals = te.distinct_values(ds.field_values(key, others, ply_scope), lo, hi)
    return None if vals is None else [[x, n] for x, n in vals]


def make_filter(field: te.Field, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The filter the editor stands for, or None (nothing ticked / no range).
    raw: number field {"min", "max", "mode": "all"|"step"|"pick", "step", "only"};
    list field {"period", "from", "to"} or {"values"}."""
    if field.kind == "num":
        lo, hi = parse_num(raw.get("min")), parse_num(raw.get("max"))
        if lo is not None and hi is not None and lo > hi:
            lo, hi = hi, lo
        flt: Dict[str, Any] = {"key": field.key, "min": lo, "max": hi}
        mode = raw.get("mode") or "all"
        if mode == "step":
            step = parse_num(raw.get("step"))
            if step and step > 0:
                flt["step"] = step
        elif mode == "pick":
            picked = [x for x in (parse_num(o) for o in raw.get("only") or []) if x is not None]
            if not picked:
                return None
            flt["only"] = picked
        return flt
    period = raw.get("period") or "" if field.key in te.TIME_KEYS else ""
    if period:
        if period not in te.PERIODS:
            return None
        flt = {"key": field.key, "period": period}
        if period == "range":
            lo, hi = raw.get("from") or None, raw.get("to") or None
            if lo and hi and lo > hi:
                lo, hi = hi, lo
            if not lo and not hi:
                return None
            flt.update({"from": lo, "to": hi})
        return flt
    vals = [str(v) for v in raw.get("values") or []]
    return {"key": field.key, "values": vals} if vals else None


def filter_hits(ds: te.TrialDataset, others: List[Dict[str, Any]], flt: Optional[Dict[str, Any]],
                ply_scope: str) -> Dict[str, Any]:
    """{"base": trials the other filters leave, "n": trials with the new filter too, "text": chip text}."""
    base = ds.apply(others, ply_scope).count
    if flt is None:
        return {"base": base, "n": None, "text": ""}
    return {"base": base, "n": ds.apply(others + [flt], ply_scope).count,
            "text": te.describe_filter(ds.fields[flt["key"]], flt)}


# ── calculated fields (desktop ui/smart_calc_dialog.py) ─────────────────
def calc_fields_for(ds: te.TrialDataset, key: str) -> List[Dict[str, str]]:
    """Number fields a formula can use: [{"name" (as written in [ ]), "label", "group"}]."""
    from db import formula as fm
    names = fm.display_names(ds.fields.values())
    return [{"name": names.get(f.key, f.label), "label": f.label, "group": f.group}
            for f in ds.fields.values() if f.kind == "num" and f.key != key]


def calc_preview(ds: te.TrialDataset, text: str, key: str, filters: Optional[List[Dict[str, Any]]] = None,
                 ply_scope: str = "any") -> Dict[str, Any]:
    """{"error"} or {"stored", "n", "min", "avg", "max"} of a formula in display form - over all trials and,
    with filters (the filters on all pages), also "filtered": {"n", "base", "min", "avg", "max"}."""
    from db import formula as fm
    try:
        stored = fm.from_display(text, ds.fields.values())
        compiled, keys = fm.compile_formula(stored, ds.fields, exclude=key)
    except fm.FormulaError as e:
        return {"error": str(e)}
    vals, by_id = [], {}
    for t in ds.trials:
        vals_t = {}
        for k in keys:
            v = ds.value(k, t.id)
            try:
                vals_t[k] = None if v is None else float(v)
            except (TypeError, ValueError):
                vals_t[k] = None
        r = fm.evaluate(compiled, vals_t)
        if r is not None:
            vals.append(r)
            by_id[t.id] = r
    out: Dict[str, Any] = {"stored": stored, **_stats(vals)}
    if filters:
        ids = ds.apply(filters, ply_scope).ids
        out["filtered"] = {"base": len(ids), **_stats([by_id[i] for i in ids if i in by_id])}
    return out


def _stats(vals: List[float]) -> Dict[str, Any]:
    if not vals:
        return {"n": 0}
    return {"n": len(vals), "min": min(vals), "avg": sum(vals) / len(vals), "max": max(vals)}


def calc_definition(ds: te.TrialDataset, key: str, name: str, unit: str, text: str) -> Dict[str, Any]:
    """The stored definition; raises db.formula.FormulaError (or ValueError for an empty name)."""
    from db import formula as fm
    name = (name or "").strip()
    if not name:
        raise ValueError("name")
    stored = fm.from_display(text, ds.fields.values())
    fm.compile_formula(stored, ds.fields, exclude=key)
    return {"key": key, "name": name, "unit": (unit or "").strip(), "formula": stored}


def calc_library(ds: te.TrialDataset, view_rows: List[Dict[str, Any]], own: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculated fields of the other dashboards this user may open (db/smart_chart_views.list_views rows) to
    copy into this one: [{"name", "unit", "formula" (display form), "view"}]. Left out: formulas with fields that
    do not exist (any more) and ones this dashboard has already (same formula)."""
    from db import formula as fm
    have = {str(c.get("formula") or "") for c in own or []}
    seen, out = set(), []
    for row in view_rows:
        try:
            cfg = json.loads(row.get("ConfigJSON") or "{}")
        except (TypeError, ValueError):
            continue
        for c in ((cfg.get("dashboard") or {}).get("calc") or []) if isinstance(cfg, dict) else []:
            stored = str(c.get("formula") or "")
            sig = (str(c.get("name") or ""), stored)
            if not stored or stored in have or sig in seen:
                continue
            if any(k not in ds.fields or str(k).startswith("calc_") for k in fm.keys_in(stored)):
                continue
            seen.add(sig)
            out.append({"name": str(c.get("name") or ""), "unit": str(c.get("unit") or ""),
                        "formula": fm.to_display(stored, ds.fields), "view": str(row.get("Name") or "")})
    return sorted(out, key=lambda x: (x["name"].lower(), x["view"].lower()))


# ── saved views: folders and favourites (Nutzerwunsch 2026-11-13) ───────
def group_views(rows: List[Dict[str, Any]], favourites: List[int]) -> List[Dict[str, Any]]:
    """The views as the lists show them: favourites first, then per folder (no folder last), each sorted by name.
    rows = list_views rows; returns [{"title": "★ Favourites" | folder | "", "views": [rows]}]."""
    fav = {int(i) for i in favourites or []}
    favs = [r for r in rows if int(r["ID"]) in fav]
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        if int(r["ID"]) in fav:
            continue
        try:
            cfg = json.loads(r.get("ConfigJSON") or "{}")
        except (TypeError, ValueError):
            cfg = {}
        groups.setdefault(view_folder(cfg if isinstance(cfg, dict) else {}), []).append(r)
    name = lambda r: str(r.get("Name") or "").lower()
    out = [{"title": FAVOURITES, "views": sorted(favs, key=name)}] if favs else []
    for folder in sorted((f for f in groups if f), key=str.lower):
        out.append({"title": folder, "views": sorted(groups[folder], key=name)})
    if "" in groups:
        out.append({"title": "", "views": groups[""]})
    return out


FAVOURITES = "★ Favourites"


def folders_of(rows: List[Dict[str, Any]]) -> List[str]:
    """Folder names in use (for the suggestions when saving)."""
    out = set()
    for r in rows:
        try:
            cfg = json.loads(r.get("ConfigJSON") or "{}")
        except (TypeError, ValueError):
            continue
        f = view_folder(cfg) if isinstance(cfg, dict) else ""
        if f:
            out.add(f)
    return sorted(out, key=str.lower)


def fairness_json(a) -> Optional[Dict[str, Any]]:
    """The fairness check of a visual for a page (desktop _FairnessDialog)."""
    if a is None:
        return None
    return {"level": a.level, "headline": a.headline, "sentence": a.sentence, "grouping": a.grouping,
            "groups": [[g, n] for g, n in a.groups],
            "conditions": [{"title": c.title, "influence": c.influence, "imbalance": c.imbalance, "level": c.level,
                            "per_group": [[g, c.per_group[g]] for g, _n in a.groups if g in c.per_group][:6]}
                           for c in a.conditions],
            "warnings": [t for _l, t in a.warnings], "can_fix": a.fix is not None, "fix_text": a.fix_text}


def view_kind(cfg: Dict[str, Any]) -> Dict[str, int]:
    """{"pages": n, "visuals": n} of a saved view."""
    d = cfg.get("dashboard") if isinstance(cfg.get("dashboard"), dict) else {}
    pages = d.get("pages") or ([{"visuals": d.get("visuals") or []}])
    return {"pages": len(pages), "visuals": sum(len(p.get("visuals") or []) for p in pages)}


def view_settings(filters: List[Dict[str, Any]], ply_scope: str, spec: Dict[str, Any], include_refs: bool = False,
                  folder: str = "") -> Dict[str, Any]:
    """What a saved view stores (db/smart_chart_views.save_view). "refs" / "folder" only when set."""
    cfg = {"filters": [dict(f) for f in filters], "ply_scope": ply_scope, "mode": "dashboard", "dashboard": spec}
    if include_refs:
        cfg["refs"] = True
    if (folder or "").strip():
        cfg["folder"] = folder.strip()[:60]
    return cfg


def view_refs(cfg: Dict[str, Any]) -> bool:
    """Does a saved view include reference samples?"""
    return bool(cfg.get("refs"))


def view_folder(cfg: Dict[str, Any]) -> str:
    return str(cfg.get("folder") or "").strip()


def read_view_settings(cfg: Dict[str, Any], known: set) -> Tuple[List[Dict[str, Any]], str, Any, List[str]]:
    """(filters, ply_scope, dashboard spec, names of unknown fields) of a saved view."""
    filters, missing = [], []
    for f in cfg.get("filters") or []:
        if f.get("key") in known:
            filters.append(f)
        else:
            missing.append(str(f.get("key")))
    scope = cfg.get("ply_scope") if cfg.get("ply_scope") in te.PLY_SCOPES else "any"
    return filters, scope, cfg.get("dashboard"), missing


def _log(name: str, detail: str = "") -> None:
    try:
        from db.usage_log import log_usage_event
        log_usage_event("feature", name, detail)
    except Exception:
        pass
