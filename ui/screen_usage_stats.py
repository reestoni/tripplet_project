# ui/screen_usage_stats.py
"""Admin-Screen: Nutzungsstatistiken (wer nutzt was, wie oft, zuletzt wann).

Liest aus tblUsageLog (siehe db/usage_log.py), das best-effort bei Login,
jedem Screen-Wechsel und einer kuratierten Liste "grosser" Features
(PDF-Export, Advisor/Athena, Fill-Range-Bulk-Edit, YarnScope-DTY)
mitgeschrieben wird.

Nur fuer Superuser sichtbar (AccessLevel >= 4) - zeigt Aktivitaet pro
Nutzer, keine anonymisierten Daten.

Tab "Dashboard": zwei matplotlib-Charts (Nutzungs-Ranking, Login-Verlauf).
Weitere Tabs: rohe Tabellen zum Nachschlagen im Detail.
"""
from typing import List, Dict

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QTabWidget, QSizePolicy, QAbstractItemView, QMessageBox,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from ui.theme import accent_tint, accent_gridline, get_accent
from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from db.connection import fetch_all, table_exists


class ReadOnlyTableModel(QAbstractTableModel):
    """Einfaches read-only Tabellenmodell fuer Stats-Anzeige."""

    def __init__(self, rows: List[Dict], headers: List[str]):
        super().__init__()
        self._rows = rows
        self._headers = headers

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._headers)

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        r, c = index.row(), index.column()
        val = self._rows[r].get(self._headers[c])
        if role == Qt.BackgroundRole:
            return QBrush(QColor(accent_tint())) if (r % 2 == 0) else QBrush(QColor('#F5FFF5'))
        if role == Qt.DisplayRole:
            return '' if val is None else str(val)
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        return None

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled


def _make_table(headers: List[str]) -> QTableView:
    table = QTableView()
    table.setAlternatingRowColors(False)
    table.setSortingEnabled(True)
    table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
    table.verticalHeader().setVisible(False)
    table.setShowGrid(True)
    table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    table.setSelectionBehavior(QTableView.SelectRows)
    table.setSelectionMode(QAbstractItemView.ExtendedSelection)
    table.setStyleSheet("""
        QTableView { gridline-color: %s; }
        QHeaderView::section {
            background: %s; color: #2b2b2b; font-weight: 600;
            border: 1px solid %s; padding: 4px 6px;
        }
        QTableView::item { color: black; }
        QTableView::item:selected { background: #b7d6ff; color: black; }
    """ % (accent_gridline(), accent_tint(), accent_gridline()))
    return table


class UsageRankingChart(FigureCanvas):
    """Horizontaler Balkenchart: Screens + Features gemeinsam nach Nutzung sortiert."""

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(6, 4), tight_layout=True)
        super().__init__(self.fig)
        if parent is not None:
            self.setParent(parent)
        self.ax = self.fig.add_subplot(111)

    def update_data(self, rows: List[Dict]):
        self.ax.clear()
        if not rows:
            self.ax.text(0.5, 0.5, "Noch keine Daten", ha="center", va="center", transform=self.ax.transAxes)
            self.draw()
            return

        rows = list(reversed(rows))  # groesster Balken oben
        labels = [r["Name"] if r["EventType"] == "screen_open" else f"★ {r['Name']}" for r in rows]
        counts = [r["Cnt"] for r in rows]
        colors = [get_accent() if r["EventType"] == "screen_open" else "#E0A030" for r in rows]

        self.ax.barh(labels, counts, color=colors)
        self.ax.set_xlabel("Aufrufe")
        self.ax.set_title("Meistgenutzte Screens & Features (★ = kuratiertes Feature)")
        self.ax.tick_params(axis="y", labelsize=8)
        self.draw()


class LoginTimelineChart(FigureCanvas):
    """Balkenchart: Logins pro Tag (letzte 30 Tage)."""

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(6, 3), tight_layout=True)
        super().__init__(self.fig)
        if parent is not None:
            self.setParent(parent)
        self.ax = self.fig.add_subplot(111)

    def update_data(self, rows: List[Dict]):
        self.ax.clear()
        if not rows:
            self.ax.text(0.5, 0.5, "Noch keine Daten", ha="center", va="center", transform=self.ax.transAxes)
            self.draw()
            return

        days = [str(r["Day"]) for r in rows]
        counts = [r["Cnt"] for r in rows]
        self.ax.bar(days, counts, color=get_accent())
        self.ax.set_ylabel("Logins")
        self.ax.set_title("Logins pro Tag (letzte 30 Tage)")
        self.ax.tick_params(axis="x", labelrotation=60, labelsize=7)
        self.draw()


class UsageStatsScreen(QWidget):
    def __init__(self, on_back_home=None, sidebar_callbacks=None):
        super().__init__()
        self.on_back_home = on_back_home
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None

        self.chart_ranking = UsageRankingChart()
        self.chart_logins = LoginTimelineChart()
        self.tbl_logins = _make_table(["Username", "Logins", "LastLogin"])
        self.tbl_screens = _make_table(["Screen", "Opens", "Users", "LastUsed"])
        self.tbl_features = _make_table(["Feature", "Detail", "Uses", "Users", "LastUsed"])

        self._build_ui()
        self.reload_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring).
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(24, 12, 24, 0)
        btn_reload = QPushButton("Reload", objectName="GreyBtn")
        btn_reload.clicked.connect(self.reload_data)
        self.status_label = QLabel("")
        toolbar.addWidget(btn_reload, 0)
        toolbar.addWidget(self.status_label, 1)
        toolbar_frame = QWidget()
        toolbar_frame.setLayout(toolbar)

        dashboard = QWidget()
        dash_layout = QVBoxLayout(dashboard)
        dash_layout.addWidget(self.chart_ranking, 2)
        dash_layout.addWidget(self.chart_logins, 1)

        tabs = QTabWidget()
        tabs.addTab(dashboard, "Dashboard")
        tabs.addTab(self.tbl_logins, "Logins")
        tabs.addTab(self.tbl_screens, "Screens")
        tabs.addTab(self.tbl_features, "Features")

        content_layout.addWidget(toolbar_frame, 0)
        content_layout.addWidget(tabs, 1)
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

    def reload_data(self):
        if not table_exists("tblUsageLog"):
            self.status_label.setText("tblUsageLog nicht gefunden auf diesem DB-Modus.")
            return

        try:
            logins = fetch_all(
                "SELECT Username, COUNT(*) AS Logins, MAX(EventTime) AS LastLogin "
                "FROM tblUsageLog WHERE EventType = 'login' "
                "GROUP BY Username ORDER BY Logins DESC"
            )
            screens = fetch_all(
                "SELECT EventName AS Screen, COUNT(*) AS Opens, "
                "COUNT(DISTINCT Username) AS Users, MAX(EventTime) AS LastUsed "
                "FROM tblUsageLog WHERE EventType = 'screen_open' "
                "GROUP BY EventName ORDER BY Opens DESC"
            )
            features = fetch_all(
                "SELECT EventName AS Feature, Detail, COUNT(*) AS Uses, "
                "COUNT(DISTINCT Username) AS Users, MAX(EventTime) AS LastUsed "
                "FROM tblUsageLog WHERE EventType = 'feature' "
                "GROUP BY EventName, Detail ORDER BY Uses DESC"
            )
            ranking = fetch_all(
                "SELECT EventName AS Name, EventType, COUNT(*) AS Cnt "
                "FROM tblUsageLog WHERE EventType IN ('screen_open', 'feature') "
                "GROUP BY EventName, EventType ORDER BY Cnt DESC LIMIT 15"
            )
            login_timeline = fetch_all(
                "SELECT DATE(EventTime) AS Day, COUNT(*) AS Cnt "
                "FROM tblUsageLog WHERE EventType = 'login' "
                "AND EventTime >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) "
                "GROUP BY DATE(EventTime) ORDER BY Day ASC"
            )
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Konnte Nutzungsstatistiken nicht laden:\n{e}")
            return

        self.chart_ranking.update_data(ranking)
        self.chart_logins.update_data(login_timeline)

        self.tbl_logins.setModel(ReadOnlyTableModel(logins, ["Username", "Logins", "LastLogin"]))
        self.tbl_screens.setModel(ReadOnlyTableModel(screens, ["Screen", "Opens", "Users", "LastUsed"]))
        self.tbl_features.setModel(ReadOnlyTableModel(features, ["Feature", "Detail", "Uses", "Users", "LastUsed"]))
        for t in (self.tbl_logins, self.tbl_screens, self.tbl_features):
            t.resizeColumnsToContents()

        self.status_label.setText(
            f"{len(logins)} Nutzer mit Logins · {len(screens)} Screens · {len(features)} Feature-Events"
        )

    def _go_home(self):
        if callable(self.on_back_home):
            self.on_back_home()
