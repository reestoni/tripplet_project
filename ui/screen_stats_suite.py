from __future__ import annotations
# ui/screen_stats_suite.py
"""Statistics Suite - superuser-only aggregate dashboard (AccessLevel >= 4).

Same delivery mechanism as Smart Chart (QWebEngineView + QWebChannel +
Plotly loaded from CDN, see ui/screen_report.py/_ReportBridge), but a
separate, much smaller template purpose-built for count/group-by/time-split
charts across Experiments/TrialSeries/Trials instead of per-trial X/Y
scatter plots - see ui/stats_suite_html_template.py and
ui/stats_suite_queries.py.

Dashboard layout (which chart cards + the global filter bar state) is saved
per logged-in user (tblStatsDashboardBlock/tblStatsDashboardFilter) rather
than shared - each superuser builds their own view, mirroring how
tblSmartChartBlock is saved per report.
"""
import json
import logging

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QVBoxLayout, QWidget, QSizePolicy, QLabel

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebChannel import QWebChannel
    from PySide6.QtCore import QObject, Slot
    _WEB_ENGINE_AVAILABLE = True
except ImportError:
    _WEB_ENGINE_AVAILABLE = False
    QObject = object

    def Slot(*a, **kw):
        def dec(f):
            return f
        return dec

from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from ui.theme import get_accent, accent_tint, accent_gridline
from ui.stats_suite_html_template import _STATS_HTML_TEMPLATE
from ui.stats_suite_queries import (
    ENTITY_LABELS, GROUP_BY_LABELS, GROUP_BY_ENTITY_RESTRICTIONS, TIME_GRANULARITY_LABELS,
    run_stats_query, fetch_filter_options,
)
import app_meta

logger = logging.getLogger(__name__)


class _StatsSuiteBridge(QObject):
    """Python<->JS bridge. Every method pushes its result back into JS by
    calling a named `receiveXxx(...)` function via runJavaScript (same
    fire-and-forget convention as _ReportBridge in ui/screen_report.py),
    rather than relying on QWebChannel's automatic return-value callback."""

    def __init__(self, screen):
        super().__init__(screen)
        self._screen = screen

    def _run_js(self, js: str) -> None:
        if self._screen._web:
            self._screen._web.page().runJavaScript(js)

    @Slot()
    def loadFilterOptions(self) -> None:
        try:
            options = fetch_filter_options()
        except Exception as e:
            logger.error("loadFilterOptions: %s", e)
            options = {"machines": [], "productGroups": [], "orderTypes": [], "labMachines": []}
        self._run_js("receiveFilterOptions(" + json.dumps(options) + ");")

    @Slot()
    def loadDashboard(self) -> None:
        from db.connection import fetch_all

        user_id = (app_meta.current_user or {}).get("id")
        blocks: list = []
        filters = None
        try:
            if user_id:
                rows = fetch_all(
                    "SELECT Entity, GroupBy, TimeGranularity, GridX, GridY, GridW, GridH "
                    "FROM tblStatsDashboardBlock "
                    "WHERE UserID = ? ORDER BY SortOrder ASC, ID ASC",
                    [user_id],
                )
                blocks = [
                    {
                        "entity": r.get("Entity"),
                        "groupBy": r.get("GroupBy"),
                        "timeGranularity": r.get("TimeGranularity"),
                        "gridX": r.get("GridX"),
                        "gridY": r.get("GridY"),
                        "gridW": r.get("GridW"),
                        "gridH": r.get("GridH"),
                    }
                    for r in rows
                ]
                frows = fetch_all(
                    "SELECT FiltersJSON FROM tblStatsDashboardFilter WHERE UserID = ?",
                    [user_id],
                )
                if frows and frows[0].get("FiltersJSON"):
                    filters = json.loads(frows[0]["FiltersJSON"])
        except Exception as e:
            logger.error("loadDashboard: %s", e)
        self._run_js(
            "receiveDashboard(" + json.dumps(blocks) + ", " + json.dumps(filters) + ");"
        )

    @Slot(str)
    def runChartQuery(self, config_json: str) -> None:
        client_id = None
        try:
            cfg = json.loads(config_json)
            client_id = cfg.get("clientId")
            rows = run_stats_query(
                cfg.get("entity"), cfg.get("groupBy"), cfg.get("timeGranularity"),
                cfg.get("filters") or {},
            )
            self._run_js(
                "receiveChartData(" + json.dumps(client_id) + ", " + json.dumps(rows) + ", null);"
            )
        except Exception as e:
            logger.error("runChartQuery: %s", e)
            self._run_js(
                "receiveChartData(" + json.dumps(client_id) + ", null, " + json.dumps(str(e)) + ");"
            )

    @Slot(str)
    def saveDashboard(self, state_json: str) -> None:
        from db.connection import get_connection

        user_id = (app_meta.current_user or {}).get("id")
        if not user_id:
            self._run_js("receiveSaveResult(false, 'No logged-in user');")
            return
        try:
            data = json.loads(state_json)
            blocks = data.get("blocks", [])
            filters = data.get("filters", {})
            with get_connection() as cn:
                cur = cn.cursor()
                cur.execute("DELETE FROM tblStatsDashboardBlock WHERE UserID = ?", [user_id])
                for i, b in enumerate(blocks):
                    cur.execute(
                        "INSERT INTO tblStatsDashboardBlock "
                        "(UserID, SortOrder, Entity, GroupBy, TimeGranularity, GridX, GridY, GridW, GridH) "
                        "VALUES (?,?,?,?,?,?,?,?,?)",
                        [user_id, i, b.get("entity"), b.get("groupBy"), b.get("timeGranularity"),
                         b.get("gridX"), b.get("gridY"), b.get("gridW"), b.get("gridH")],
                    )
                cur.execute("SELECT ID FROM tblStatsDashboardFilter WHERE UserID = ?", [user_id])
                existing = cur.fetchone()
                filters_json = json.dumps(filters)
                if existing:
                    cur.execute(
                        "UPDATE tblStatsDashboardFilter SET FiltersJSON = ? WHERE UserID = ?",
                        [filters_json, user_id],
                    )
                else:
                    cur.execute(
                        "INSERT INTO tblStatsDashboardFilter (UserID, FiltersJSON) VALUES (?,?)",
                        [user_id, filters_json],
                    )
                cn.commit()
            self._run_js("receiveSaveResult(true, '');")
        except Exception as e:
            logger.error("saveDashboard: %s", e)
            self._run_js("receiveSaveResult(false, " + json.dumps(str(e)) + ");")


class StatsSuiteScreen(QWidget):
    def __init__(self, on_back_home=None, sidebar_callbacks=None):
        super().__init__()
        self.on_back_home = on_back_home
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring).
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        if _WEB_ENGINE_AVAILABLE:
            self._web = QWebEngineView()
            self._web.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._bridge = _StatsSuiteBridge(self)
            self._channel = QWebChannel()
            self._channel.registerObject("bridge", self._bridge)
            self._web.page().setWebChannel(self._channel)
            content_layout.addWidget(self._web)
        else:
            fallback = QLabel("⚠️  PySide6-WebEngine not installed.\npip install PySide6-WebEngine")
            fallback.setStyleSheet("font-size:14px; color:#c0392b; padding:40px;")
            content_layout.addWidget(fallback)
            self._web = None

        root.addWidget(FooterBar())

        if self._web is not None:
            self._load_html()

    def _refresh_sidebar(self):
        """Baut die Sidebar-Navigation neu auf, falls sich der Access-Level
        seit dem letzten Aufbau geändert hat, sonst nur die Badges (siehe
        ui/widgets/sidebar_nav.py::refresh_lazy_sidebar())."""
        try:
            level = int((app_meta.current_user or {}).get("access_level") or 0)
        except Exception:
            level = 0
        sidebar_nav.refresh_lazy_sidebar(self, level)

    def showEvent(self, event):
        try:
            self._refresh_sidebar()
        except Exception:
            pass
        super().showEvent(event)

    def _load_html(self) -> None:
        html = (
            _STATS_HTML_TEMPLATE
            .replace("{accent_color}", get_accent())
            .replace("{accent_tint}", accent_tint())
            .replace("{accent_gridline}", accent_gridline())
            .replace("{entity_labels_json}", json.dumps(ENTITY_LABELS))
            .replace("{group_by_labels_json}", json.dumps(GROUP_BY_LABELS))
            .replace("{group_by_entity_restrictions_json}", json.dumps(GROUP_BY_ENTITY_RESTRICTIONS))
            .replace("{time_granularity_labels_json}", json.dumps(TIME_GRANULARITY_LABELS))
        )
        self._web.setHtml(html, QUrl("about:blank"))

    def reload_data(self) -> None:
        """Called on navigation into this screen. The dashboard bootstrap
        (load filter options + saved blocks/filters) runs JS-side on page
        load via QWebChannel, so a fresh setHtml() is the simplest way to
        re-trigger it - cheap since there is no server round trip until the
        page's own bridge calls fire."""
        if self._web is not None:
            self._load_html()

    def _go_home(self):
        if callable(self.on_back_home):
            self.on_back_home()
