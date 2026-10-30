# ui/screen_smart_chart.py
"""Smart Chart, rebuilt 2026-10-30 (Nutzerwunsch): find trials by their
properties across ALL series, then chart any field against any other.

Replaces the old "Visual SQL" Smart Chart (ReportScreen mode="visual", incl.
the Free Query Builder - removed on purpose). The series report opened from
Show Experiment (ReportScreen mode="series") is unchanged.

Layout (concept: claude.ai artifact "Smart Chart Konzept"):
- left  "1 Find trials": filter chips (click = edit, × = remove), "+ Add
  filter" (ui/smart_chart_filter_dialog.py), "Yarn filters apply to" Any
  ply / Core only / Effect only
- right: live counter, "2 Build the chart" (X, Y, Colour by, Split by,
  Each trial / Mean per X), the Plotly chart (QWebEngineView), and the list
  of the trials in the chart (double-click = open in Show Experiment)
- top: Open view / Save view (db/smart_chart_views.py), Excel, PDF, Reload

Data and filtering: db/trial_explorer.py, figure: ui/smart_chart_figure.py.
"""
from __future__ import annotations

import base64
import datetime
import json
import logging
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QObject, QTimer, QUrl, Qt, Signal, Slot
from PySide6.QtGui import QAction, QActionGroup, QColor, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QMenu, QPushButton, QScrollArea, QSizePolicy, QSplitter, QTableWidget, QTableWidgetItem, QToolButton,
    QVBoxLayout, QWidget,
)

try:
    from PySide6.QtWebChannel import QWebChannel
    from PySide6.QtWebEngineWidgets import QWebEngineView
    _WEB = True
except Exception:  # pragma: no cover - WebEngine missing
    _WEB = False

from db import smart_chart_views as views
from db import trial_explorer as te
from ui.smart_chart_figure import CHART_TYPES, MODE_TO_CHART, PALETTES, build_figure
from ui.widgets import sidebar_nav
from ui.widgets.footer import FooterBar
from ui.widgets.friendly_error import show_error

logger = logging.getLogger(__name__)

ACCENT = "#1F7A3A"
DEFAULT_X, DEFAULT_Y = "air_pressure", "tenacity"

_BTN = ("QPushButton{background:#FFFFFF;color:#1C2321;border:1px solid #C9D1C8;border-radius:6px;"
        "padding:6px 14px;font-weight:500;}QPushButton:hover{background:#F0F4EF;}"
        "QPushButton:disabled{color:#9AA59C;}")
_BTN_PRIMARY = ("QPushButton{background:#1F7A3A;color:#FFFFFF;border:1px solid #1F7A3A;border-radius:6px;"
                "padding:6px 14px;font-weight:600;}QPushButton:hover{background:#165C2B;}")
_SEG = ("QPushButton{background:#FFFFFF;color:#1C2321;border:1px solid #C9D1C8;padding:6px 10px;}"
        "QPushButton:checked{background:#1F7A3A;color:#FFFFFF;border-color:#1F7A3A;font-weight:600;}")
_PANEL = "QFrame#Panel{background:#FFFFFF;border:1px solid #DADFD8;border-radius:10px;}"

_CHART_HTML = """<!doctype html><html><head><meta charset="utf-8">
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<style>html,body{margin:0;height:100%;background:#fff;font-family:'Segoe UI',sans-serif}
#c{position:absolute;inset:0}#msg{position:absolute;inset:0;display:flex;align-items:center;
justify-content:center;color:#5A6460;font-size:14px;text-align:center;padding:24px;pointer-events:none}</style>
</head><body><div id="c"></div><div id="msg">Loading…</div><script>
var bridge=null;
new QWebChannel(qt.webChannelTransport,function(ch){bridge=ch.objects.bridge;bridge.ready();});
function render(fig,msg){
  document.getElementById('msg').textContent=msg||'';
  if(typeof Plotly==='undefined'){document.getElementById('msg').textContent='The chart library could not be loaded (internet connection?).';return;}
  var el=document.getElementById('c');
  Plotly.react(el,fig.data,fig.layout,{responsive:true,displaylogo:false,
    modeBarButtonsToRemove:['lasso2d','select2d','autoScale2d','toggleSpikelines']});
  if(!el._sc){el._sc=1;el.on('plotly_click',function(e){
    var p=e&&e.points&&e.points[0];if(bridge&&p&&p.customdata!=null)bridge.pointClicked(String(p.customdata));});}
}
function snapshot(){
  if(typeof Plotly==='undefined'){bridge.snapshotReady('');return;}
  Plotly.toImage('c',{format:'png',width:1500,height:820,scale:2}).then(function(u){bridge.snapshotReady(u.split(',')[1]);})
    .catch(function(){bridge.snapshotReady('');});
}
</script></body></html>"""


class _ChartBridge(QObject):
    readySignal = Signal()
    clicked = Signal(int)
    snapshot = Signal(str)

    @Slot()
    def ready(self):
        self.readySignal.emit()

    @Slot(str)
    def pointClicked(self, tid: str):
        try:
            self.clicked.emit(int(tid))
        except ValueError:
            pass

    @Slot(str)
    def snapshotReady(self, b64: str):
        self.snapshot.emit(b64 or "")


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
        self.filters: List[Dict[str, Any]] = []
        self.ply_scope = "any"
        self.view: Optional[Dict[str, Any]] = None   # loaded saved view
        self._chart_ready = False
        self._pending_fig = None
        self._rows: List[Dict[str, Any]] = []
        self._snapshot_cb: Optional[Callable[[str], None]] = None
        self.colour_map: Dict[str, str] = {}   # own colours per value ("Colours…")
        self.mode = "chart"                    # "chart" | "dashboard" (ui/smart_dashboard.py)
        self._info: Dict[str, Any] = {}

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
        pv.setSpacing(12)

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
        self.lbl_title = QLabel("New chart")
        self.lbl_title.setStyleSheet("font-size:20px; font-weight:700; color:#1C2321;")
        tbox.addWidget(lbl_kicker)
        tbox.addWidget(self.lbl_title)
        head.addLayout(tbox, 1)
        mseg = QHBoxLayout()
        mseg.setSpacing(0)
        self.grp_mode = QButtonGroup(self)
        for i, (lab, tip) in enumerate((("Chart", "One chart with its list of trials"),
                                        ("Dashboard", "A page with several visuals, fields of all tables, "
                                                      "click to filter the others - like Power BI"))):
            b = QPushButton(lab)
            b.setCheckable(True)
            b.setChecked(i == 0)
            b.setToolTip(tip)
            b.setStyleSheet(_SEG + "QPushButton{padding:7px 16px;font-size:13px;}")
            self.grp_mode.addButton(b, i)
            mseg.addWidget(b)
        self.grp_mode.idClicked.connect(lambda i: self.set_mode("dashboard" if i == 1 else "chart"))
        head.addLayout(mseg)
        head.addSpacing(12)
        self.btn_new = QPushButton("New")
        self.btn_new.setToolTip("Start again with no filters")
        self.btn_open = QPushButton("Open view")
        self.btn_save = QPushButton("Save view")
        self.btn_share = QPushButton("Share…")
        self.btn_share.setToolTip("Share this view with people or groups - to view or to edit")
        self.btn_excel = QPushButton("Excel")
        self.btn_excel.setToolTip("Export the list of trials in the chart to Excel")
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

        # ── body ────────────────────────────────────────────────────────
        body = QHBoxLayout()
        body.setSpacing(14)
        pv.addLayout(body, 1)

        # step 1: find trials
        left = QFrame()
        left.setObjectName("Panel")
        left.setFixedWidth(330)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(14, 14, 14, 14)
        lv.setSpacing(10)
        lv.addWidget(self._step_label("1", "Find trials"))
        self.chip_host = QWidget()
        self.chip_lay = QVBoxLayout(self.chip_host)
        self.chip_lay.setContentsMargins(0, 0, 0, 0)
        self.chip_lay.setSpacing(6)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.NoFrame)
        sc.setWidget(self.chip_host)
        lv.addWidget(sc, 1)
        self.btn_add = QPushButton("+  Add filter")
        self.btn_add.setStyleSheet(f"QPushButton{{background:#FFFFFF;color:{ACCENT};border:1px dashed #9FB39F;"
                                   "border-radius:8px;padding:10px;font-weight:600;}"
                                   "QPushButton:hover{background:#F0F7F2;}")
        self.btn_add.clicked.connect(lambda: self._edit_filter(None))
        lv.addWidget(self.btn_add)
        lv.addWidget(self._small("Yarn filters apply to"))
        seg = QHBoxLayout()
        seg.setSpacing(0)
        self.grp_scope = QButtonGroup(self)
        for i, (k, lab) in enumerate((("any", "Any ply"), ("core", "Core only"), ("effect", "Effect only"))):
            b = QPushButton(lab)
            b.setCheckable(True)
            b.setStyleSheet(_SEG)
            b.setChecked(k == "any")
            b.setToolTip("Yarn filters must all fit the same ply" if k == "any"
                         else f"Yarn filters must fit a ply with yarn use {lab.split()[0]}")
            self.grp_scope.addButton(b, i)
            seg.addWidget(b)
        self.grp_scope.idClicked.connect(self._on_scope)
        lv.addLayout(seg)
        hint = QLabel("<b>Yarn</b>: material, end titer, filaments, dpf, yarn type…<br>"
                      "<b>Jet</b>: air hole, yarn channel, swirl chamber, cone, titer range, maker…<br>"
                      "<b>Machine</b>: jet, air pressure, overfeed, speed, temperatures…<br>"
                      "<b>Lab</b>: tenacity, elongation, titer, FP/m, stability…<br>"
                      "<b>General</b>: machine, series, experiment, year")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#3E4744; font-size:12px; border-top:1px solid #E6EAE5; padding-top:8px;")
        lv.addWidget(hint)
        body.addWidget(left)
        self.left_panel = left          # hidden in dashboard mode (its Filters pane has "On all pages")

        # step 2: chart + list
        right = QVBoxLayout()
        right.setSpacing(10)
        body.addLayout(right, 1)
        self.lbl_count = QLabel("Loading trials…")
        self.lbl_count.setStyleSheet("background:#E6F2E9; border:1px solid #BFDCC7; border-radius:10px;"
                                     "padding:10px 14px; color:#165C2B; font-size:14px;")
        right.addWidget(self.lbl_count)

        # fairness check (db/fairness.py): light + sentence + Details / Make it fairer
        self.fair_box = QFrame()
        fb = QHBoxLayout(self.fair_box)
        fb.setContentsMargins(12, 8, 10, 8)
        fb.setSpacing(10)
        self.fair_dot = QLabel()
        self.fair_dot.setFixedSize(16, 16)
        fb.addWidget(self.fair_dot, 0, Qt.AlignTop)
        self.fair_text = QLabel()
        self.fair_text.setWordWrap(True)
        self.fair_text.setTextFormat(Qt.RichText)
        fb.addWidget(self.fair_text, 1)
        self.btn_fair_fix = QPushButton("Make it fairer")
        self.btn_fair_fix.setStyleSheet(_BTN)
        self.btn_fair_fix.clicked.connect(self._make_fairer)
        fb.addWidget(self.btn_fair_fix, 0, Qt.AlignTop)
        self.btn_fair_details = QPushButton("Details")
        self.btn_fair_details.setStyleSheet(_BTN)
        self.btn_fair_details.clicked.connect(self._fair_details)
        fb.addWidget(self.btn_fair_details, 0, Qt.AlignTop)
        self.fair_box.setVisible(False)
        from PySide6.QtWidgets import QStackedWidget
        self.mode_stack = QStackedWidget()
        chart_page = QWidget()
        cpl = QVBoxLayout(chart_page)
        cpl.setContentsMargins(0, 0, 0, 0)
        cpl.setSpacing(10)
        cpl.addWidget(self.fair_box)
        self.mode_stack.addWidget(chart_page)
        right.addWidget(self.mode_stack, 1)
        self._fair = None

        chart_panel = QFrame()
        chart_panel.setObjectName("Panel")
        cv = QVBoxLayout(chart_panel)
        cv.setContentsMargins(14, 12, 14, 12)
        cv.setSpacing(8)
        cv.addWidget(self._step_label("2", "Build the chart"))
        ctr = QHBoxLayout()
        ctr.setSpacing(10)
        from ui.smart_chart_style import FieldPicker
        self.cmb_x, self.cmb_y = FieldPicker(), FieldPicker()
        self.cmb_colour, self.cmb_split = FieldPicker(), FieldPicker()
        for lab, cmb in (("X axis", self.cmb_x), ("Y axis", self.cmb_y),
                         ("Colour by", self.cmb_colour), ("Split by", self.cmb_split)):
            box = QVBoxLayout()
            box.setSpacing(2)
            box.addWidget(self._small(lab))
            cmb.changed.connect(self._schedule)
            box.addWidget(cmb)
            ctr.addLayout(box)
        self.cmb_colour.changed.connect(self.colour_map.clear)
        ctr.addStretch(1)
        cv.addLayout(ctr)

        from ui.smart_chart_style import chart_icon, palette_icon
        look = QHBoxLayout()
        look.setSpacing(10)
        tbox = QVBoxLayout()
        tbox.setSpacing(2)
        tbox.addWidget(self._small("Chart"))
        self.cmb_chart = QComboBox()
        self.cmb_chart.setMinimumWidth(200)
        self.cmb_chart.setIconSize(self.cmb_chart.iconSize() * 1.4)
        for key, (lab, tip) in CHART_TYPES.items():
            self.cmb_chart.addItem(chart_icon(key), lab, key)
            self.cmb_chart.setItemData(self.cmb_chart.count() - 1, tip, Qt.ToolTipRole)
        self.cmb_chart.currentIndexChanged.connect(self._on_chart_type)
        tbox.addWidget(self.cmb_chart)
        look.addLayout(tbox)
        pbox = QVBoxLayout()
        pbox.setSpacing(2)
        pbox.addWidget(self._small("Colours"))
        prow = QHBoxLayout()
        prow.setSpacing(6)
        self.cmb_palette = QComboBox()
        self.cmb_palette.setMinimumWidth(190)
        for key, pal in PALETTES.items():
            self.cmb_palette.addItem(palette_icon(key), pal["label"], key)
        self.cmb_palette.currentIndexChanged.connect(self._schedule)
        prow.addWidget(self.cmb_palette)
        self.btn_colours = QPushButton("Colours…")
        self.btn_colours.setToolTip("Choose your own colour for each value in the chart")
        self.btn_colours.setStyleSheet(_BTN)
        self.btn_colours.clicked.connect(self._edit_colours)
        prow.addWidget(self.btn_colours)
        pbox.addLayout(prow)
        look.addLayout(pbox)
        obox = QVBoxLayout()
        obox.setSpacing(2)
        obox.addWidget(self._small("Options"))
        self.btn_options = QPushButton("Options")
        self.btn_options.setStyleSheet(_BTN)
        menu = QMenu(self.btn_options)
        self.act_shapes = menu.addAction("Different shapes per colour")
        self.act_shapes.setToolTip("Circle, square, diamond… - readable in black and white too")
        self.act_logx = menu.addAction("Logarithmic X axis")
        self.act_logy = menu.addAction("Logarithmic Y axis")
        self.act_dark = menu.addAction("Dark background")
        for a in (self.act_shapes, self.act_logx, self.act_logy, self.act_dark):
            a.setCheckable(True)
            a.toggled.connect(self._schedule)
        sizes = menu.addMenu("Point size")
        self.grp_size = QActionGroup(self)
        self.size_actions = {}
        for lab, px in (("Small", 5), ("Medium", 8), ("Large", 12)):
            a = sizes.addAction(lab)
            a.setCheckable(True)
            a.setChecked(px == 8)
            a.setData(px)
            self.grp_size.addAction(a)
            a.toggled.connect(self._schedule)
            self.size_actions[px] = a
        self.btn_options.setMenu(menu)
        obox.addWidget(self.btn_options)
        look.addLayout(obox)
        look.addStretch(1)
        cv.addLayout(look)

        self.split = QSplitter(Qt.Vertical)
        if _WEB:
            self.web = QWebEngineView()
            self.web.setMinimumHeight(260)
            self.bridge = _ChartBridge()
            self.bridge.readySignal.connect(self._on_chart_ready)
            self.bridge.clicked.connect(self._select_trial)
            self.bridge.snapshot.connect(self._on_snapshot)
            self.channel = QWebChannel()
            self.channel.registerObject("bridge", self.bridge)
            self.web.page().setWebChannel(self.channel)
            self.web.setHtml(_CHART_HTML, QUrl("about:blank"))
            self.split.addWidget(self.web)
        else:
            self.web = None
            msg = QLabel("Charts need PySide6-WebEngine.")
            msg.setAlignment(Qt.AlignCenter)
            self.split.addWidget(msg)

        list_box = QWidget()
        lb = QVBoxLayout(list_box)
        lb.setContentsMargins(0, 6, 0, 0)
        lb.setSpacing(4)
        lh = QHBoxLayout()
        lbl_list = QLabel("<b>Trials in the chart</b>")
        lh.addWidget(lbl_list)
        self.lbl_list_hint = QLabel("double-click a line to open it in Show Experiment · click a point to find it here")
        self.lbl_list_hint.setStyleSheet("color:#5A6460; font-size:12px;")
        lh.addWidget(self.lbl_list_hint)
        lh.addStretch(1)
        lb.addLayout(lh)
        self.tbl = QTableWidget(0, 7)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSortingEnabled(True)
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.itemDoubleClicked.connect(self._open_row)
        lb.addWidget(self.tbl, 1)
        self.split.addWidget(list_box)
        self.split.setStretchFactor(0, 3)
        self.split.setStretchFactor(1, 2)
        cv.addWidget(self.split, 1)
        cpl.addWidget(chart_panel, 1)
        from ui.smart_dashboard import SmartDashboard
        self.dashboard = SmartDashboard(self)
        self.mode_stack.addWidget(self.dashboard)

        root.addWidget(FooterBar())

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self.refresh)
        self._render_chips()
        self._update_view_buttons()
        self._sync_controls()

    # ── small widgets ───────────────────────────────────────────────────
    @staticmethod
    def _step_label(no: str, text: str) -> QLabel:
        lab = QLabel(f"<span style='background:{ACCENT};color:#fff;border-radius:9px;padding:1px 7px;"
                     f"font-weight:700;'>{no}</span>&nbsp;&nbsp;<b style='font-size:15px'>{text}</b>")
        return lab

    @staticmethod
    def _small(text: str) -> QLabel:
        lab = QLabel(text)
        lab.setStyleSheet("color:#5A6460; font-size:12px; font-weight:600;")
        return lab

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
        """Load (or reload) all trials. Keeps filters and chart settings."""
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
        self._fill_combos()
        self._render_chips()
        self.refresh()

    def _fill_combos(self) -> None:
        cur = {c: c.currentData() for c in (self.cmb_x, self.cmb_y, self.cmb_colour, self.cmb_split)}
        for cmb, kinds, none_label in ((self.cmb_x, ("num", "cat"), None), (self.cmb_y, ("num",), None),
                                       (self.cmb_colour, ("cat", "num"), "— none —"),
                                       (self.cmb_split, ("cat",), "— none —")):
            cmb.blockSignals(True)
            cmb.set_fields(self.catalog, kinds, none_label)
        self._set_combo(self.cmb_x, cur[self.cmb_x] or DEFAULT_X)
        self._set_combo(self.cmb_y, cur[self.cmb_y] or DEFAULT_Y)
        self._set_combo(self.cmb_colour, cur[self.cmb_colour] or "")
        self._set_combo(self.cmb_split, cur[self.cmb_split] or "")
        for c in cur:
            c.blockSignals(False)

    @staticmethod
    def _set_combo(cmb, key: Optional[str]) -> None:
        if hasattr(cmb, "set_key"):   # FieldPicker
            cmb.set_key(key, emit=True)
            return
        i = cmb.findData(key)
        if i < 0:
            i = next((j for j in range(cmb.count()) if cmb.itemData(j)), 0)
        cmb.setCurrentIndex(i)

    # ── filters ─────────────────────────────────────────────────────────
    def _render_chips(self) -> None:
        while self.chip_lay.count():
            it = self.chip_lay.takeAt(0)
            if it.widget() is not None:
                it.widget().deleteLater()
        if not self.filters:
            lab = QLabel("No filters yet - all trials are included.\nClick “+ Add filter” to narrow them down.")
            lab.setWordWrap(True)
            lab.setStyleSheet("color:#5A6460; font-size:12px; padding:4px 2px;")
            self.chip_lay.addWidget(lab)
        for i, flt in enumerate(self.filters):
            f = self.ds.fields.get(flt["key"]) if self.ds else None
            if f is None:
                continue
            chip = QFrame()
            chip.setStyleSheet("QFrame{background:#E6F2E9;border:1px solid #1F7A3A;border-radius:8px;}"
                               "QLabel{border:none;background:transparent;}")
            h = QHBoxLayout(chip)
            h.setContentsMargins(10, 6, 6, 6)
            btn = QPushButton()
            btn.setFlat(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip("Click to change this filter")
            btn.setStyleSheet("QPushButton{text-align:left;border:none;color:#165C2B;padding:0;}")
            group = f.group + (" · " + {"any": "any ply", "core": "core", "effect": "effect"}[self.ply_scope]
                               if f.level == "yarn" else "")
            btn.setText(f"{group.upper()}\n{te.describe_filter(f, flt)}")
            btn.clicked.connect(lambda _=False, k=i: self._edit_filter(k))
            h.addWidget(btn, 1)
            x = QToolButton()
            x.setText("×")
            x.setToolTip("Remove this filter")
            x.setStyleSheet("QToolButton{border:none;color:#165C2B;font-size:18px;padding:0 6px;}"
                            "QToolButton:hover{color:#B00020;}")
            x.clicked.connect(lambda _=False, k=i: self._remove_filter(k))
            h.addWidget(x)
            self.chip_lay.addWidget(chip)
        self.chip_lay.addStretch(1)

    def _edit_filter(self, index: Optional[int]) -> None:
        if self.ds is None:
            return
        from ui.smart_chart_filter_dialog import AddFilterDialog
        edit = self.filters[index] if index is not None else None
        dlg = AddFilterDialog(self.ds, self.catalog, self.filters, self.ply_scope, edit=edit, parent=self)
        if dlg.exec() != QDialog.Accepted or dlg.result_filter is None:
            return
        new = dlg.result_filter
        if index is not None:
            self.filters[index] = new
        else:
            same = next((j for j, f in enumerate(self.filters) if f["key"] == new["key"]), None)
            if same is not None:
                self.filters[same] = new
            else:
                self.filters.append(new)
            _log("smart_chart_filter", new["key"])
        self._render_chips()
        self.refresh()

    def _remove_filter(self, index: int) -> None:
        if 0 <= index < len(self.filters):
            del self.filters[index]
            self._render_chips()
            self.refresh()

    def _on_scope(self, i: int) -> None:
        self.ply_scope = te.PLY_SCOPES[i]
        self._render_chips()
        self.refresh()

    # ── refresh ─────────────────────────────────────────────────────────
    def _schedule(self, *_a) -> None:
        self._timer.start()

    def settings(self) -> Dict[str, Any]:
        return {"filters": [dict(f) for f in self.filters], "ply_scope": self.ply_scope,
                "x": self.cmb_x.currentData() or DEFAULT_X, "y": self.cmb_y.currentData() or DEFAULT_Y,
                "colour": self.cmb_colour.currentData() or "", "split": self.cmb_split.currentData() or "",
                "chart": self.cmb_chart.currentData() or "points",
                "palette": self.cmb_palette.currentData() or "trippleT", "colour_map": dict(self.colour_map),
                "shapes": self.act_shapes.isChecked(), "logx": self.act_logx.isChecked(),
                "logy": self.act_logy.isChecked(), "dark": self.act_dark.isChecked(),
                "size": int(self.grp_size.checkedAction().data()) if self.grp_size.checkedAction() else 8,
                "mode": self.mode, "dashboard": getattr(self, "dashboard", None) and self.dashboard.spec}

    def set_mode(self, mode: str) -> None:
        """Chart (one chart + list) or Dashboard (several visuals). Filters stay."""
        self.mode = "dashboard" if mode == "dashboard" else "chart"
        self.grp_mode.button(1 if self.mode == "dashboard" else 0).setChecked(True)
        self.mode_stack.setCurrentIndex(1 if self.mode == "dashboard" else 0)
        self.left_panel.setVisible(self.mode == "chart")
        self.btn_excel.setToolTip("Export the list of trials in the chart to Excel" if self.mode == "chart" else
                                  "Export the data of every visual of this page to Excel (one sheet per visual)")
        self.btn_new.setToolTip("Start again with no filters" if self.mode == "chart" else
                                "New dashboard: empty, example or from a template")
        if self.mode == "dashboard":
            _log("smart_dashboard_open")
        self.refresh()

    def refresh(self) -> None:
        if self.ds is None:
            return
        s = self.settings()
        if self.mode == "dashboard":
            res = self.ds.apply(s["filters"], s["ply_scope"])
            summ = self.ds.summary(res)
            self.res = res
            self.lbl_count.setText(
                f"<span style='font-size:22px;font-weight:700'>{_fmt_n(summ['trials'])}</span>"
                f"&nbsp; <b>trials match</b> &nbsp;in {_fmt_n(summ['series'])} series · {summ['machines']} machines · "
                f"{summ['jets']} jets &nbsp;&nbsp;<span style='color:#2F4A37;font-size:12px'>"
                f"these filters apply to every visual of the page · reference samples excluded</span>")
            self.dashboard.refresh()
            return
        QGuiApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            res = self.ds.apply(s["filters"], s["ply_scope"])
            summ = self.ds.summary(res)
            fig, rows, info = build_figure(
                self.ds, res, s["x"], s["y"], s["colour"] or None, s["split"] or None, chart=s["chart"],
                palette=s["palette"], colour_map=s["colour_map"], shapes=s["shapes"], logx=s["logx"],
                logy=s["logy"], size=s["size"], dark=s["dark"])
        except Exception as e:
            QGuiApplication.restoreOverrideCursor()
            show_error(self, "Smart Chart", "The chart could not be built.", e)
            return
        QGuiApplication.restoreOverrideCursor()
        self.res, self._rows, self._info = res, rows, info
        self.lbl_count.setText(
            f"<span style='font-size:22px;font-weight:700'>{_fmt_n(summ['trials'])}</span>"
            f"&nbsp; <b>trials match</b> &nbsp;in {_fmt_n(summ['series'])} series · {summ['machines']} machines · "
            f"{summ['jets']} jets &nbsp;&nbsp;<span style='color:#2F4A37;font-size:12px'>"
            f"{_fmt_n(info['plotted'])} {'have a Y value' if s['chart'] == 'hist' else 'have both X and Y'} "
            f"and are in the chart · reference samples excluded</span>")
        self.btn_colours.setEnabled(bool(info.get("colour_groups")))
        msg = ""
        if not rows:
            msg = ("No trial matches the filters." if not res.ids else
                   "None of the matching trials has a value for both X and Y.")
        elif info["hidden_panels"]:
            msg = ""
        self._render(fig, msg)
        self._fill_table(rows, s)
        self._update_fairness(s, res, rows, info)

    # ── fairness check ──────────────────────────────────────────────────
    _FAIR_STYLE = {
        "green": ("#E6F2E9", "#BFDCC7", "#1F7A3A"),
        "amber": ("#FFF4D6", "#E8C15A", "#C98A00"),
        "red": ("#FDECEA", "#E3A39C", "#C62828"),
    }

    def _update_fairness(self, s, res, rows, info) -> None:
        from db import fairness as fz
        a = fz.assess_chart(self.ds, res, rows, info, s, self.filters)
        self._fair = a
        if a is None or a.level == fz.NONE:
            self.fair_box.setVisible(False)
            return
        bg, border, dot = self._FAIR_STYLE[a.level]
        self.fair_box.setStyleSheet(f"QFrame{{background:{bg};border:1px solid {border};border-radius:10px;}}"
                                    "QLabel{border:none;background:transparent;}")
        self.fair_dot.setStyleSheet(f"background:{dot};border-radius:8px;")
        import html as _html
        self.fair_text.setText(f"<b>{_html.escape(a.headline)}</b> <span style='color:#5A6460'>"
                               f"({_html.escape(a.grouping)})</span><br>{_html.escape(a.sentence)}")
        self.btn_fair_fix.setVisible(a.fix is not None)
        self.btn_fair_fix.setToolTip(a.fix_text)
        self.fair_box.setVisible(True)

    def _make_fairer(self) -> None:
        a = self._fair
        if a is None or a.fix is None:
            return
        new = dict(a.fix)
        same = next((i for i, flt in enumerate(self.filters) if flt["key"] == new["key"]), None)
        if same is not None:
            self.filters[same] = new
        else:
            self.filters.append(new)
        _log("smart_chart_fairer", new["key"])
        self._render_chips()
        self.refresh()

    def _fair_details(self) -> None:
        if self._fair is None:
            return
        _log("smart_chart_fairness_details", self._fair.level)
        dlg = _FairnessDialog(self._fair, self)
        if dlg.exec() == QDialog.Accepted and dlg.apply_fix:
            self._make_fairer()

    def _on_chart_type(self, *_a) -> None:
        self._sync_controls()
        self._schedule()

    def _sync_controls(self) -> None:
        chart = self.cmb_chart.currentData() or "points"
        self.cmb_x.setEnabled(chart != "hist")
        self.cmb_x.setToolTip("Not used by the histogram" if chart == "hist" else "")
        self.cmb_colour.setEnabled(chart != "density")
        self.cmb_colour.setToolTip("The density map colours by the number of trials" if chart == "density" else
                                   "List fields: one colour per value. Number fields: a colour scale "
                                   "(points) or 5 ranges (other charts).")

    def _edit_colours(self) -> None:
        groups = self._info.get("colour_groups") or []
        if not groups:
            return
        from ui.smart_chart_style import ColoursDialog
        dlg = ColoursDialog(groups, self._info.get("colour_defaults") or {}, self.colour_map, self)
        if dlg.exec() == QDialog.Accepted:
            self.colour_map = dlg.result_map
            _log("smart_chart_colours")
            self.refresh()

    def _render(self, fig, msg: str = "") -> None:
        if self.web is None:
            return
        self._pending_fig = (fig, msg)
        if self._chart_ready:
            self.web.page().runJavaScript(f"render({json.dumps(fig)}, {json.dumps(msg)});")

    def _on_chart_ready(self) -> None:
        self._chart_ready = True
        if self._pending_fig is not None:
            self._render(*self._pending_fig)

    def _fill_table(self, rows: List[Dict[str, Any]], s: Dict[str, Any]) -> None:
        fx, fy = self.ds.fields[s["x"]], self.ds.fields[s["y"]]
        heads = ["Trial", "Series", "Yarn", "Machine", "Jet", fx.label, fy.label]
        rows = [dict(p, x=p["x"] if p["x"] is not None else "") for p in rows]
        self.tbl.setSortingEnabled(False)
        self.tbl.clear()
        self.tbl.setColumnCount(len(heads))
        self.tbl.setHorizontalHeaderLabels(heads)
        self.tbl.setRowCount(len(rows))
        for r, p in enumerate(rows):
            vals = [p["trial"], p["series"], p["yarn"], p["machine"], p["jet"], p["x"], p["y"]]
            for c, v in enumerate(vals):
                it = QTableWidgetItem()
                if isinstance(v, float):
                    it.setData(Qt.DisplayRole, round(v, 3))
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                elif c == 0:
                    it.setData(Qt.DisplayRole, p["trial"])
                else:
                    it.setText(str(v))
                if c == 0:
                    it.setData(Qt.UserRole, p["tid"])
                self.tbl.setItem(r, c, it)
        self.tbl.setSortingEnabled(True)
        self.tbl.resizeColumnsToContents()
        for c in range(self.tbl.columnCount()):
            self.tbl.setColumnWidth(c, min(self.tbl.columnWidth(c), 320))

    def _select_trial(self, tid: int) -> None:
        for r in range(self.tbl.rowCount()):
            it = self.tbl.item(r, 0)
            if it is not None and it.data(Qt.UserRole) == tid:
                self.tbl.selectRow(r)
                self.tbl.scrollToItem(it, QAbstractItemView.PositionAtCenter)
                return

    def _open_row(self, item) -> None:
        tid = self.tbl.item(item.row(), 0).data(Qt.UserRole)
        t = self.ds.by_id.get(tid) if self.ds else None
        if t is None or not callable(self.on_open_series) or t.exp_pk is None:
            return
        self.on_open_series(t.exp_pk, t.series_id, t.experiment)

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
        if self.mode != "dashboard":
            self._new_chart()
            return
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
        """New dashboard (filters on all pages stay - they belong to Find trials)."""
        self.view = None
        self._update_share_button()
        self.lbl_title.setText("New dashboard")
        self.dashboard.start_from(template)
        self.refresh()

    def _new_chart(self) -> None:
        self.dashboard.set_spec(None)
        self.filters = []
        self.view = None
        self._update_share_button()
        self.lbl_title.setText("New chart")
        self.grp_scope.button(0).setChecked(True)
        self.ply_scope = "any"
        self._render_chips()
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
        self.grp_scope.button(te.PLY_SCOPES.index(self.ply_scope)).setChecked(True)
        for cmb, key in ((self.cmb_x, cfg.get("x")), (self.cmb_y, cfg.get("y")),
                         (self.cmb_colour, cfg.get("colour") or ""), (self.cmb_split, cfg.get("split") or "")):
            cmb.blockSignals(True)
            if key and key not in known:
                missing.append(str(key))
            self._set_combo(cmb, key if (key in known or key == "") else None)
            cmb.blockSignals(False)
        chart = cfg.get("chart") or MODE_TO_CHART.get(cfg.get("mode"), "points")
        for cmb, key in ((self.cmb_chart, chart), (self.cmb_palette, cfg.get("palette") or "trippleT")):
            cmb.blockSignals(True)
            self._set_combo(cmb, key)
            cmb.blockSignals(False)
        self.colour_map = dict(cfg.get("colour_map") or {})
        for act, key in ((self.act_shapes, "shapes"), (self.act_logx, "logx"), (self.act_logy, "logy"),
                         (self.act_dark, "dark")):
            act.blockSignals(True)
            act.setChecked(bool(cfg.get(key)))
            act.blockSignals(False)
        self.dashboard.set_spec(cfg.get("dashboard"))
        self.mode = "dashboard" if cfg.get("mode") == "dashboard" else "chart"
        self.grp_mode.button(1 if self.mode == "dashboard" else 0).setChecked(True)
        self.mode_stack.setCurrentIndex(1 if self.mode == "dashboard" else 0)
        self.left_panel.setVisible(self.mode == "chart")
        size_act = self.size_actions.get(int(cfg.get("size") or 8)) or self.size_actions[8]
        size_act.blockSignals(True)
        size_act.setChecked(True)
        size_act.blockSignals(False)
        self._sync_controls()
        self._render_chips()
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
    def filter_lines(self) -> List[str]:
        if self.ds is None:
            return []
        lines = [te.describe_filter(self.ds.fields[f["key"]], f) for f in self.filters if f["key"] in self.ds.fields]
        if any(self.ds.fields[f["key"]].level == "yarn" for f in self.filters if f["key"] in self.ds.fields):
            lines.append({"any": "Yarn filters: any ply", "core": "Yarn filters: core plies",
                          "effect": "Yarn filters: effect plies"}[self.ply_scope])
        return lines or ["No filters (all trials)"]

    def _export_excel(self) -> None:
        if self.mode == "dashboard":
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
            return
        if not self._rows:
            QMessageBox.information(self, "Excel", "There are no trials in the chart.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export to Excel",
                                              f"SmartChart_{datetime.date.today():%Y%m%d}.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font
            s = self.settings()
            fx, fy = self.ds.fields[s["x"]], self.ds.fields[s["y"]]
            wb = Workbook()
            ws = wb.active
            ws.title = "Trials"
            heads = ["Trial", "Series", "Experiment", "Yarn", "Machine", "Jet", fx.label, fy.label]
            ws.append(heads)
            for c in ws[1]:
                c.font = Font(bold=True)
            for p in self._rows:
                ws.append([p["trial"], p["series"], p["experiment"], p["yarn"], p["machine"], p["jet"], p["x"], p["y"]])
            info = wb.create_sheet("Filters")
            info.append(["Smart Chart", self.lbl_title.text()])
            info.append(["Exported", datetime.datetime.now().strftime("%d.%m.%Y %H:%M")])
            for line in self.filter_lines():
                info.append(["Filter", line])
            wb.save(path)
            _log("smart_chart_excel")
        except Exception as e:
            show_error(self, "Excel", "The Excel file could not be written.", e)

    def _export_pdf(self) -> None:
        if self.mode == "dashboard":
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
                self.dashboard.export_pdf(path, all_pages, "" if title in ("New chart", "New dashboard") else title)
            return
        if self.web is None or not self._rows:
            QMessageBox.information(self, "PDF", "There is no chart to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF",
                                              f"SmartChart_{datetime.date.today():%Y%m%d}.pdf", "PDF (*.pdf)")
        if not path:
            return
        self._snapshot_cb = lambda b64: self._write_pdf(path, b64)
        self.web.page().runJavaScript("snapshot();")

    def _on_snapshot(self, b64: str) -> None:
        cb, self._snapshot_cb = self._snapshot_cb, None
        if cb is not None:
            cb(b64)

    def _write_pdf(self, path: str, b64: str) -> None:
        try:
            from ui.smart_chart_pdf import write_pdf
            s = self.settings()
            summary = self.lbl_count.text()
            if self._fair is not None and self._fair.level != "none":
                summary += f"<br>Fairness check: {self._fair.headline} - {self._fair.sentence}"
            write_pdf(path, title=self.lbl_title.text(), filters=self.filter_lines(),
                      summary=summary, chart_png=base64.b64decode(b64) if b64 else None,
                      rows=self._rows, x_label=self.ds.fields[s["x"]].label, y_label=self.ds.fields[s["y"]].label)
            _log("smart_chart_pdf")
        except Exception as e:
            show_error(self, "PDF", "The PDF could not be written.", e)
            return
        QMessageBox.information(self, "PDF", f"PDF saved:\n{path}")

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
    """'Dashboard · 2 pages · 9 visuals' or 'Chart · Box plot'."""
    if cfg.get("mode") == "dashboard" and isinstance(cfg.get("dashboard"), dict):
        pages = cfg["dashboard"].get("pages") or ([{"visuals": cfg["dashboard"].get("visuals") or []}])
        n_v = sum(len(p.get("visuals") or []) for p in pages)
        return f"Dashboard · {len(pages)} page{'s' if len(pages) != 1 else ''} · {n_v} visuals"
    return f"Chart · {CHART_TYPES.get(cfg.get('chart') or 'points', ('Points', ''))[0]}"


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
