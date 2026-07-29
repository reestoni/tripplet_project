# ui/screen_usage_stats.py
"""Admin-Screen: Nutzungsstatistiken (wer nutzt was, wie oft, zuletzt wann).

Liest aus tblUsageLog (siehe db/usage_log.py), das best-effort bei Login,
jedem Screen-Wechsel und einer kuratierten Liste "grosser" Features
(PDF-Export, Advisor/Athena, Fill-Range-Bulk-Edit, YarnScope-DTY)
mitgeschrieben wird.

Nur fuer Superuser sichtbar (AccessLevel >= 4) - zeigt Aktivitaet pro
Nutzer, keine anonymisierten Daten.
"""
from typing import List, Dict

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QTabWidget, QSizePolicy, QAbstractItemView, QMessageBox,
)

from ui.theme import accent_tint, accent_gridline
from ui.widgets.footer import FooterBar
from ui.widgets.header import HeaderBar
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


class UsageStatsScreen(QWidget):
    def __init__(self, on_back_home=None):
        super().__init__()
        self.on_back_home = on_back_home

        self.tbl_logins = _make_table(["Username", "Logins", "LastLogin"])
        self.tbl_screens = _make_table(["Screen", "Opens", "Users", "LastUsed"])
        self.tbl_features = _make_table(["Feature", "Detail", "Uses", "Users", "LastUsed"])

        self._build_ui()
        self.reload_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = HeaderBar(title="Usage Stats", show_home=True)
        header.connect_home(self._go_home)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(24, 12, 24, 0)
        btn_reload = QPushButton("Reload", objectName="GreyBtn")
        btn_reload.clicked.connect(self.reload_data)
        self.status_label = QLabel("")
        toolbar.addWidget(btn_reload, 0)
        toolbar.addWidget(self.status_label, 1)
        toolbar_frame = QWidget()
        toolbar_frame.setLayout(toolbar)

        tabs = QTabWidget()
        tabs.addTab(self.tbl_logins, "Logins")
        tabs.addTab(self.tbl_screens, "Screens")
        tabs.addTab(self.tbl_features, "Features")

        root.addWidget(header)
        root.addWidget(toolbar_frame, 0)
        root.addWidget(tabs, 1)
        root.addWidget(FooterBar())

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
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Konnte Nutzungsstatistiken nicht laden:\n{e}")
            return

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
