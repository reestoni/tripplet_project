from __future__ import annotations
# ui/screen_report.py
"""Report-Screen für TrippleT – Visualisierung einer TrialSeries.

Alles, was die DB liest/schreibt oder rechnet (Seite füllen, Bridge-Slots,
PDF), steht Qt-frei in db/report_service.py (gemeinsam mit der Web-App
tripplet_web) - hier bleiben nur Qt-Dinge: WebView, Dialoge, Zwischenablage.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QSizePolicy, QMessageBox, QFrame,
)
from PySide6.QtCore import QSize

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineScript
    from PySide6.QtWebChannel import QWebChannel
    from PySide6.QtCore import QObject, Slot
    _WEB_ENGINE_AVAILABLE = True
except ImportError:
    _WEB_ENGINE_AVAILABLE = False
    QObject = object
    def Slot(*a, **kw):
        def dec(f): return f
        return dec

from ui.pathutil import resource_path, web_base_url
from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from db import report_service
# re-exported - imported from here by tests/older code
from db.report_service import (  # noqa: F401
    MACHINE_JOIN, advanced_filter_sql, value_notes_text, _adv_allowed_fields,
)
import app_meta

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bridge: Python <-> JavaScript (DB/compute in db/report_service.py)
# ---------------------------------------------------------------------------

class _ReportBridge(QObject):

    def __init__(self, screen):
        super().__init__(screen)
        self._screen = screen

    def _run_js(self, js: str) -> None:
        if self._screen._web:
            self._screen._web.page().runJavaScript(js)

    def _slot(self, name: str, *args) -> None:
        """Shared slot (report_service.handle) -> receiveXxx(...) in the page."""
        res = report_service.handle(name, list(args), user=app_meta.current_user,
                                    series_pk=self._screen._series_pk)
        if res is not None:
            self._run_js(report_service.js_call(*res))

    @Slot(str)
    def copyImageToClipboard(self, b64_png: str) -> None:
        try:
            import base64
            from PySide6.QtGui import QImage, QClipboard
            from PySide6.QtWidgets import QApplication
            img_bytes = base64.b64decode(b64_png)
            img = QImage()
            img.loadFromData(img_bytes, "PNG")
            if not img.isNull():
                QApplication.clipboard().setImage(img, QClipboard.Clipboard)
        except Exception as e:
            logger.error("copyImageToClipboard: %s", e)

    @Slot()
    def getSeriesList(self):
        self._slot("getSeriesList")

    @Slot(str, str)
    def loadSeriesData(self, series_pk_str, color):
        self._slot("loadSeriesData", series_pk_str, color)

    @Slot(str, str, str, str)
    def runVisualQuery(self, series_pks_json, group_by, filters_json, adv_filters_json='[]'):
        self._slot("runVisualQuery", series_pks_json, group_by, filters_json, adv_filters_json)

    @Slot(str)
    def saveReport(self, report_json: str) -> None:
        """Save or update a report (only the author overwrites, others get a copy)."""
        self._slot("saveReport", report_json)

    @Slot()
    def loadReportList(self) -> None:
        self._slot("loadReportList")

    @Slot(str)
    def loadReport(self, report_id_str: str) -> None:
        self._slot("loadReport", report_id_str)

    @Slot(str)
    def deleteReport(self, report_id_str: str) -> None:
        self._slot("deleteReport", report_id_str)

    @Slot(str, str)
    def addImage(self, insert_after_str: str, width: str) -> None:
        """Open file dialog and send image as base64 to JS."""
        try:
            import base64, os
            from PySide6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getOpenFileName(
                self._screen, "Select image", "",
                "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
            )
            if not path:
                return
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            ext = os.path.splitext(path)[1].lower().lstrip(".")
            mime = {"jpg":"jpeg","jpeg":"jpeg","png":"png","bmp":"bmp","gif":"gif","webp":"webp"}.get(ext,"png")
            data_url = f"data:image/{mime};base64,{b64}"
            title = os.path.splitext(os.path.basename(path))[0]
            self._run_js(f"receiveImage({insert_after_str}, {json.dumps(data_url)}, {json.dumps(title)}, {json.dumps(width)});")
        except Exception as e:
            logger.error("addImage: %s", e)

    @Slot(str)
    def exportPdf(self, payload_json: str) -> None:
        """Heberlein-branded PDF (report_service.build_report_pdf) - here only
        the save dialog and writing the file."""
        from db.usage_log import log_usage_event
        log_usage_event("feature", "pdf_export")
        try:
            import datetime
            import pathlib as _pl
            from PySide6.QtWidgets import QFileDialog

            payload = json.loads(payload_json)
            now     = datetime.datetime.now()
            _docs   = str(_pl.Path.home() / "Documents")
            dflt    = report_service.pdf_default_filename(payload, now)
            out_path, _ = QFileDialog.getSaveFileName(
                self._screen, "Save PDF report",
                str(_pl.Path(_docs) / dflt), "PDF Files (*.pdf)"
            )
            if not out_path:
                self._run_js("receivePdfResult(false, 'cancelled');")
                return
            pdf = report_service.build_report_pdf(payload, now)
            with open(out_path, "wb") as f:
                f.write(pdf)
            self._run_js("receivePdfResult(true, " + json.dumps(out_path) + ");")
        except Exception as e:
            logger.error("exportPdf: %s", e)
            self._run_js("receivePdfResult(false, " + json.dumps(str(e)) + ");")

    @Slot(str, str, str, str, str)
    def loadFreeField(self, table, field, condition, chart_idx, y_key):
        self._slot("loadFreeField", table, field, condition, chart_idx, y_key)

    @Slot(str)
    def jsError(self, message: str) -> None:
        logger.error("JS ERROR: %s", message)
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self._screen, "JS error", message)

    @Slot()
    def getLayoutTemplates(self) -> None:
        self._slot("getLayoutTemplates")

    @Slot(str)
    def saveLayoutTemplate(self, payload_json: str) -> None:
        self._slot("saveLayoutTemplate", payload_json)

    @Slot(str)
    def deleteLayoutTemplate(self, template_id_str: str) -> None:
        self._slot("deleteLayoutTemplate", template_id_str)

    @Slot(str)
    def overwriteLayoutTemplate(self, payload_json: str) -> None:
        self._slot("overwriteLayoutTemplate", payload_json)

    @Slot()
    def getPdfTemplates(self) -> None:
        self._slot("getPdfTemplates")


# ---------------------------------------------------------------------------
# Screen
# ---------------------------------------------------------------------------

class ReportScreen(QWidget):

    def __init__(self, on_back=None, mode="series", parent=None, sidebar_callbacks: Optional[dict] = None):
        super().__init__(parent)
        self.on_back = on_back
        self.mode = mode  # immer "series" (aus Show Experiment); der Visual-SQL-Modus ist entfernt
        self._series_pk: Optional[int] = None
        self._experiment_request_id: Optional[Any] = None
        self._expreq_popup = None
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring). Der frühere
        # Header-Back-Button lebt als kontextueller Back-Chip weiter (gleiches
        # Muster wie ShowExperimentScreen) - zurück zu Show Experiment.
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        tools = QFrame()
        tl = QHBoxLayout(tools)
        tl.setContentsMargins(24, 12, 24, 0)
        tl.setSpacing(8)

        self.btn_back_chip = QPushButton("← Show Experiment")
        self.btn_back_chip.setCursor(Qt.PointingHandCursor)
        self.btn_back_chip.setStyleSheet(
            "QPushButton{background:transparent;color:#39a650;border:1px solid #39a650;"
            "border-radius:4px;padding:5px 10px;font-weight:600;}"
            "QPushButton:hover{background:#e8f5e9;}"
        )
        self.btn_back_chip.clicked.connect(self._go_back)
        self.btn_back_chip.setVisible(callable(self.on_back))
        tl.addWidget(self.btn_back_chip)
        tl.addStretch(1)

        # Experiment Request Button (analog zu screen_show_experiment)
        self.btn_experiment_request = QPushButton()
        self.btn_experiment_request.setObjectName("IconBtn")
        self.btn_experiment_request.setToolTip("Show linked Experiment Request")
        self.btn_experiment_request.setFlat(True)
        self.btn_experiment_request.setFixedSize(34, 34)
        self.btn_experiment_request.setStyleSheet(
            "QPushButton{border:none;background:transparent;padding:0px;}"
            "QPushButton:hover{background:rgba(0,0,0,0.06);border-radius:6px;}"
        )
        import os as _os2
        _icon_candidates = [
            resource_path("assets/images/experiment_request.png"),
            resource_path("assets/experiment_request.png"),
            resource_path("ui/icons/experiment_request.png"),
        ]
        _icon_set = False
        for _p in _icon_candidates:
            try:
                if _p and _os2.path.exists(_p):
                    self.btn_experiment_request.setIcon(QIcon(_p))
                    self.btn_experiment_request.setIconSize(QSize(22, 22))
                    _icon_set = True
                    break
            except Exception:
                continue
        if not _icon_set:
            self.btn_experiment_request.setText("ER")
        self.btn_experiment_request.setVisible(False)
        self.btn_experiment_request.clicked.connect(self._open_experiment_request_popup)
        tl.addWidget(self.btn_experiment_request)
        # Kontext-Hilfe EN/DE/ES (Nutzerwunsch 2026-10-13, ui/widgets/multilang_help.py);
        # im Smart-Chart-Modus direkt auf dem Smart-Chart-Tab
        from ui.widgets.multilang_help import make_help_button
        tl.addWidget(make_help_button("How does the Report work?", self._open_help))
        content_layout.addWidget(tools)

        self.lbl_series = QLabel()  # kept for internal use, not shown
        self.lbl_status = QLabel()  # kept for internal use, not shown

        if _WEB_ENGINE_AVAILABLE:
            self._web = QWebEngineView()
            self._web.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._bridge = _ReportBridge(self)
            self._channel = QWebChannel()
            self._channel.registerObject("bridge", self._bridge)
            self._web.page().setWebChannel(self._channel)
            content_layout.addWidget(self._web)
        else:
            fallback = QLabel("⚠️  PySide6-WebEngine is not installed.\npip install PySide6-WebEngine")
            fallback.setAlignment(Qt.AlignCenter)
            fallback.setStyleSheet("font-size:14px; color:#c0392b; padding:40px;")
            content_layout.addWidget(fallback)
            self._web = None

        root.addWidget(FooterBar())

    def _refresh_sidebar(self):
        """Baut die Sidebar-Navigation neu auf, falls sich der Access-Level
        seit dem letzten Aufbau geändert hat, sonst nur die Badges (siehe
        ui/widgets/sidebar_nav.py::refresh_lazy_sidebar())."""
        import app_meta
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
        # Bugreport 2026-09-02: with a SECOND ReportScreen (own QWebEngineView)
        # opened in its own new tab while a FIRST one already exists elsewhere
        # (see main.py::_open_report_in_new_tab(), 2026-09-01), the new tab's
        # QWebEngineView sometimes never actually paints - the tab title/stack
        # switch to it correctly, but the previously visible screen (e.g. Show
        # Experiment) stays on screen underneath, because this view's native
        # render surface got set up at 0x0 geometry (new tab, layout not yet
        # settled) before it was ever shown. A no-op resize-to-current-size
        # AFTER the event loop has settled the real geometry nudges Chromium's
        # compositor into actually painting - same class of QtWebEngine/
        # QStackedWidget gotcha as the well-known "webview stays blank until
        # resized" issue.
        if self._web is not None:
            QTimer.singleShot(0, lambda w=self._web: w.resize(w.size()))

    def load_series(self, series_pk: int, initial_report_id: Optional[int] = None) -> None:
        self._series_pk = series_pk
        self.lbl_series.setText(f"TrialSeries: {series_pk}")
        self.lbl_status.setText("Loading data...")
        self._refresh_experiment_request_link()
        self._sync_experiment_request_icon()

        # Page with every placeholder filled (shared with the web app)
        page = report_service.series_report_page(
            series_pk, initial_report_id, app_meta.current_user)
        n_refs = page["n_refs"]
        self.lbl_status.setText(
            f"{page['n_trials']} trial(s) loaded"
            + (f" + {n_refs} reference sample(s)" if n_refs else ""))

        if self._web is not None:
            html = page["html"]
            try:
                import tempfile as _tmp, os as _os
                _p = _os.path.join(_tmp.gettempdir(), "tripplet_debug.html")
                open(_p, "w", encoding="utf-8").write(html)
                logger.info("DEBUG HTML: %s", _p)
            except Exception as _e:
                logger.error("DEBUG: %s", _e)
            self._web.setHtml(html, web_base_url())


    def _refresh_experiment_request_link(self) -> None:
        """Laedt die verknuepfte ExperimentRequest-ID ueber series_pk -> ExperimentID."""
        self._experiment_request_id = None
        if not self._series_pk:
            return
        try:
            from db.connection import fetch_all
            # series_pk -> tblTrialSeries.ExperimentID -> tblExperimente.ExperimentRequest
            rows = fetch_all(
                """
                SELECT er.ID AS req_id
                FROM tblTrialSeries ts
                JOIN tblExperimente e ON e.ID = ts.ExperimentID
                JOIN tblExperimentRequests er ON er.ID = e.ExperimentRequestID
                WHERE ts.ID = ?
                LIMIT 1
                """,
                [self._series_pk],
            )
            if rows:
                self._experiment_request_id = rows[0].get("req_id")
        except Exception:
            self._experiment_request_id = None

    def _sync_experiment_request_icon(self) -> None:
        """Zeigt/versteckt den ER-Button je nach verlinktem Request."""
        try:
            rid = self._experiment_request_id
            visible = rid not in (None, "", 0, "0")
            if hasattr(self, "btn_experiment_request") and self.btn_experiment_request:
                self.btn_experiment_request.setVisible(bool(visible))
        except Exception:
            pass

    def _open_experiment_request_popup(self) -> None:
        """Oeffnet den ExperimentRequest als nicht-modalen Read-Only-Dialog."""
        rid = self._experiment_request_id
        if rid in (None, "", 0, "0"):
            return
        try:
            # Bereits offen -> nach vorne holen
            if self._expreq_popup is not None and self._expreq_popup.isVisible():
                self._expreq_popup.raise_()
                self._expreq_popup.activateWindow()
                return
            from ui.screen_show_experiment import _ExperimentRequestReadOnlyDialog
            dlg = _ExperimentRequestReadOnlyDialog(self, request_id=rid)
            dlg.setWindowModality(Qt.NonModal)
            dlg.setModal(False)
            dlg.setAttribute(Qt.WA_DeleteOnClose, True)
            dlg.finished.connect(lambda: setattr(self, "_expreq_popup", None))
            self._expreq_popup = dlg
            dlg.show()
        except Exception as e:
            QMessageBox.critical(self, "Experiment Request", str(e))

    def _open_help(self) -> None:
        from ui.widgets.multilang_help import show_help
        from ui.widgets.help_texts_report import TEXTS
        show_help(TEXTS, self)

    def _go_back(self) -> None:
        if callable(self.on_back):
            self.on_back()