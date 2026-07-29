from __future__ import annotations
# ui/screen_aty_batch.py
"""Batch-Verarbeitungs-Screen für ATY TDMS-Dateien (YarnScope ATY Dickstellen-Analyse).

Ermöglicht es, viele ATY-Trials auf einmal zu analysieren:
  1. Serien aus der DB auswählen (Checkbox-Liste)
  2. TDMS-Dateien im konfigurierten ATY-Ordner scannen
  3. Analyse im Hintergrund ausführen
  4. Ergebnisse (N_B1, N_B2, Avg-Werte, Histogramme) in tblLaborATYoMat schreiben

TDMS-Datei-Namenskonvention: <SeriesID>_<TrialNr>_...tdms
Ordner: H:\\Technik\\TrippleT\\ATYtdms

Getrennt von screen_tdms_batch.py (DTY) – verwendet ATYBatchScreen / mw.aty_batch.
"""

import os
import traceback
from dataclasses import dataclass, field
from datetime import datetime as _dt
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PySide6.QtCore import (
    Qt, Signal, QObject, QRunnable, QThreadPool, QAbstractTableModel,
    QModelIndex, QSortFilterProxyModel, QTimer,
)
from PySide6.QtGui import QColor, QFont, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QHeaderView, QProgressBar,
    QMessageBox, QSplitter, QAbstractItemView,
    QCheckBox, QListWidget, QListWidgetItem, QApplication,
)

from db.connection import fetch_all, execute
from ui.widgets.header import HeaderBar
from ui.widgets.footer import FooterBar

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------
ATY_TDMS_BASE_DIR = r"H:\Technik\TrippleT\ATYtdms"

# Status-Werte
ST_NO_FILE  = "—"
ST_PENDING  = "ausstehend"
ST_RUNNING  = "running…"
ST_SAVED    = "✅ gespeichert"
ST_ERROR    = "❌ Fehler"
ST_ANALYZED = "🔍 analysiert"

# Spalten der Ergebnistabelle
_COL_SERIES   = 0
_COL_TRIAL_NO = 1
_COL_TRIAL_ID = 2
_COL_FILE     = 3
_COL_STATUS   = 4
_COL_TOTAL_LEN = 5
_COL_N_B1     = 6
_COL_N_B2     = 7
_COL_AVG_LEN_B1   = 8
_COL_AVG_LEN_B2   = 9
_COL_AVG_HGT_B1   = 10
_COL_AVG_HGT_B2   = 11
_COL_AVG_AREA_B1  = 12
_COL_AVG_AREA_B2  = 13

_HEADERS = [
    "Serie", "Vers.", "TrialID", "Datei", "Status",
    "Length [m]", "N_B1 /100m", "N_B2 /100m",
    "AvgLen B1 [mm]", "AvgLen B2 [mm]",
    "AvgHgt B1 [µm]", "AvgHgt B2 [µm]",
    "AvgArea B1", "AvgArea B2",
]

# DB-Felder für tblLaborATYoMat (Zusammenfassung)
_DB_SUMMARY_COLS = [
    "TotalLen_m", "BinThreshold",
    "N_B1", "N_B2",
    "AvgLen_B1", "AvgLen_B2",
    "AvgHeight_B1", "AvgHeight_B2",
    "AvgArea_B1", "AvgArea_B2",
]
# Histogramm-Spalten: len_b1_bin_1..20, len_b2_bin_1..20, hgt_..., area_...
_DB_HIST_COLS: List[str] = []
for _prefix in ("len", "hgt", "area"):
    for _bid in (1, 2):
        for _i in range(1, 21):
            _DB_HIST_COLS.append(f"{_prefix}_b{_bid}_bin_{_i}")

_ALL_DB_COLS = _DB_SUMMARY_COLS + _DB_HIST_COLS  # 10 + 120 = 130


# ---------------------------------------------------------------------------
# Datenklasse pro Trial-Zeile
# ---------------------------------------------------------------------------
@dataclass
class ATYTrialRow:
    series_id:   int
    series_name: str
    trial_no:    int
    trial_id:    Optional[int]
    tdms_path:   Optional[Path]
    status:      str = ST_NO_FILE
    db_vals:     Dict[str, Any] = field(default_factory=dict)
    error_msg:   str = ""


# ---------------------------------------------------------------------------
# TDMS-Ordner scannen
# ---------------------------------------------------------------------------
class ATYFolderScanner:
    """Scannt ATY_TDMS_BASE_DIR und baut TrialRow-Objekte."""

    @staticmethod
    def _parse_ids(stem: str) -> Optional[Tuple[int, int]]:
        """Parst SeriesID und TrialNr aus Dateinamen-Stem (Format: <SID>_<VNO>_...)."""
        try:
            first_us = stem.index("_")
        except ValueError:
            return None
        i = first_us - 1
        while i >= 0 and stem[i].isdigit():
            i -= 1
        num1 = stem[i + 1:first_us]
        if not num1:
            return None
        try:
            second_us = stem.index("_", first_us + 1)
        except ValueError:
            return None
        j = second_us - 1
        while j > first_us and stem[j].isdigit():
            j -= 1
        num2 = stem[j + 1:second_us]
        if not num2:
            return None
        try:
            return int(num1), int(num2)
        except ValueError:
            return None

    @staticmethod
    def _build_tdms_map() -> Dict[Tuple[int, int], Path]:
        base = Path(ATY_TDMS_BASE_DIR)
        tdms_map: Dict[Tuple[int, int], Path] = {}
        if base.exists():
            for f in base.iterdir():
                if f.suffix.lower() == ".tdms":
                    ids = ATYFolderScanner._parse_ids(f.stem)
                    if ids:
                        tdms_map[ids] = f
        return tdms_map

    @staticmethod
    def _fetch_saved(trial_ids: List[int]) -> Tuple[set, dict]:
        saved_ids: set = set()
        saved_vals: dict = {}
        if not trial_ids:
            return saved_ids, saved_vals
        ph = ",".join(["?"] * len(trial_ids))
        try:
            cols_sql = ", ".join(_ALL_DB_COLS)
            rows = fetch_all(
                f"SELECT TrialID, {cols_sql} FROM tblLaborATYoMat "
                f"WHERE TrialID IN ({ph}) AND Timestamp IS NOT NULL",
                trial_ids,
            )
            for r in rows:
                tid = r.get("TrialID") if isinstance(r, dict) else r[0]
                if tid is None:
                    continue
                tid = int(tid)
                saved_ids.add(tid)
                d = {}
                for idx, col in enumerate(_ALL_DB_COLS):
                    d[col] = r.get(col) if isinstance(r, dict) else r[idx + 1]
                saved_vals[tid] = d
        except Exception:
            pass
        return saved_ids, saved_vals

    @staticmethod
    def scan_multi(series_ids: List[int]) -> List[ATYTrialRow]:
        if not series_ids:
            return []
        ph = ",".join(["?"] * len(series_ids))

        tdms_map = ATYFolderScanner._build_tdms_map()

        try:
            series_rows = fetch_all(
                f"SELECT s.ID, s.SeriesName, e.[Experiment ID] AS ExpID "
                f"FROM tblTrialSeries s "
                f"LEFT JOIN tblExperimente e ON e.ID = s.ExperimentID "
                f"WHERE s.ID IN ({ph})",
                series_ids,
            )
        except Exception:
            series_rows = []
        series_map: Dict[int, str] = {}
        for sr in series_rows:
            sid   = sr.get("ID")         if isinstance(sr, dict) else sr[0]
            sname = sr.get("SeriesName") if isinstance(sr, dict) else sr[1]
            exp   = sr.get("ExpID")      if isinstance(sr, dict) else sr[2]
            if sid is not None:
                series_map[int(sid)] = f"{exp} | {sname}" if exp else str(sname)

        try:
            trial_rows = fetch_all(
                f"SELECT ID, TrialSeriesID, Versuchsnummer FROM tblTrial "
                f"WHERE TrialSeriesID IN ({ph}) "
                f"ORDER BY TrialSeriesID, Versuchsnummer",
                series_ids,
            )
        except Exception:
            trial_rows = []

        trial_ids = [
            int(tr.get("ID") if isinstance(tr, dict) else tr[0])
            for tr in trial_rows
        ]
        saved_ids, saved_vals = ATYFolderScanner._fetch_saved(trial_ids)

        rows: List[ATYTrialRow] = []
        known_keys: set = set()
        for tr in trial_rows:
            if isinstance(tr, dict):
                tid = int(tr.get("ID") or 0)
                sid = int(tr.get("TrialSeriesID") or 0)
                vno = int(tr.get("Versuchsnummer") or 0)
            else:
                tid, sid, vno = int(tr[0]), int(tr[1]), int(tr[2])

            sname = series_map.get(sid, str(sid))
            tdms  = tdms_map.get((sid, vno))

            if tdms is None:
                st = ST_NO_FILE
            elif tid in saved_ids:
                st = ST_SAVED
            else:
                st = ST_PENDING

            row = ATYTrialRow(
                series_id=sid, series_name=sname,
                trial_no=vno, trial_id=tid,
                tdms_path=tdms, status=st,
            )
            if tid in saved_vals:
                row.db_vals = saved_vals[tid]
            rows.append(row)
            known_keys.add((sid, vno))

        # TDMS-Files ohne DB-Trial
        series_ids_set = set(series_ids)
        for (sid, vno), fpath in tdms_map.items():
            if sid not in series_ids_set:
                continue
            if (sid, vno) not in known_keys:
                sname = series_map.get(sid, f"Serie {sid}")
                rows.append(ATYTrialRow(
                    series_id=sid, series_name=sname,
                    trial_no=vno, trial_id=None,
                    tdms_path=fpath, status="⚠️ kein Trial",
                ))

        rows.sort(key=lambda r: (r.series_id, r.trial_no))
        return rows


# ---------------------------------------------------------------------------
# Scan-Worker (Hintergrund)
# ---------------------------------------------------------------------------
class _ScanSignals(QObject):
    status = Signal(str)
    done   = Signal(list)
    error  = Signal(str)


class _ScanWorker(QRunnable):
    def __init__(self, series_ids: List[int], signals: "_ScanSignals"):
        super().__init__()
        self._series_ids = series_ids
        self._signals    = signals
        self.setAutoDelete(True)

    def run(self):
        try:
            self._signals.status.emit("Scanne ATY-TDMS-Ordner…")
            rows = ATYFolderScanner.scan_multi(self._series_ids)
            n_files = sum(1 for r in rows if r.tdms_path)
            n_pend  = sum(1 for r in rows if r.status == ST_PENDING)
            self._signals.status.emit(
                f"Scan fertig: {len(rows)} Trials | {n_files} mit TDMS | {n_pend} ausstehend"
            )
            self._signals.done.emit(rows)
        except Exception as e:
            self._signals.error.emit(f"{e}\n{traceback.format_exc()[-400:]}")


# ---------------------------------------------------------------------------
# DB-Speicher-Helfer
# ---------------------------------------------------------------------------
def _save_aty_to_db(trial_id: int, db_vals: Dict[str, Any],
                    tdms_path: Optional[Path] = None) -> bool:
    """Schreibt ATY-Analyse-Ergebnisse in tblLaborATYoMat (INSERT oder UPDATE)."""

    def _v(key):
        v = db_vals.get(key)
        try:
            return float(v) if v is not None else None
        except Exception:
            return None

    ts = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
    params = [_v(c) for c in _ALL_DB_COLS]

    try:
        exists = bool(fetch_all(
            "SELECT 1 FROM tblLaborATYoMat WHERE TrialID = ?", (trial_id,)
        ))
    except Exception:
        exists = False

    try:
        if exists:
            set_parts = [f"{c}=?" for c in _ALL_DB_COLS]
            sql = (
                f"UPDATE tblLaborATYoMat SET {', '.join(set_parts)}, Timestamp=? "
                f"WHERE TrialID=?"
            )
            execute(sql, params + [ts, trial_id])
        else:
            cols_str = ", ".join(_ALL_DB_COLS)
            ph = ", ".join(["?"] * len(_ALL_DB_COLS))
            sql = (
                f"INSERT INTO tblLaborATYoMat (TrialID, {cols_str}, Timestamp) "
                f"VALUES (?, {ph}, ?)"
            )
            execute(sql, [trial_id] + params + [ts])
        return True
    except Exception as e:
        print(f"[ATY Batch] DB-Fehler TrialID={trial_id}: {e}")
        return False


# ---------------------------------------------------------------------------
# Table Model
# ---------------------------------------------------------------------------
class _ATYTableModel(QAbstractTableModel):

    def __init__(self, rows: List[ATYTrialRow], parent=None):
        super().__init__(parent)
        self._rows = rows

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(_HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return _HEADERS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            return self._display(row, col)
        if role == Qt.ForegroundRole:
            return self._fg_color(row)
        if role == Qt.BackgroundRole:
            if row.status == ST_RUNNING:
                return QColor("#2a3a2a")
            if row.status == ST_ERROR:
                return QColor("#3a2020")
        if role == Qt.TextAlignmentRole:
            if col in (_COL_TRIAL_NO, _COL_TRIAL_ID) or col >= _COL_TOTAL_LEN:
                return int(Qt.AlignRight | Qt.AlignVCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)
        if role == Qt.FontRole:
            if row.status == ST_SAVED:
                f = QFont(); f.setBold(True); return f
        return None

    def _display(self, row: ATYTrialRow, col: int) -> str:
        def _f(v, dec=2):
            try:
                fv = float(v)
                return f"{fv:.{dec}f}" if v is not None else ""
            except Exception:
                return ""

        if col == _COL_SERIES:    return row.series_name
        if col == _COL_TRIAL_NO:  return str(row.trial_no)
        if col == _COL_TRIAL_ID:  return str(row.trial_id) if row.trial_id else "?"
        if col == _COL_FILE:      return row.tdms_path.name if row.tdms_path else "—"
        if col == _COL_STATUS:    return row.status
        if col == _COL_TOTAL_LEN: return _f(row.db_vals.get("TotalLen_m"), 1)
        if col == _COL_N_B1:      return _f(row.db_vals.get("N_B1"), 1)
        if col == _COL_N_B2:      return _f(row.db_vals.get("N_B2"), 1)
        if col == _COL_AVG_LEN_B1:  return _f(row.db_vals.get("AvgLen_B1"), 2)
        if col == _COL_AVG_LEN_B2:  return _f(row.db_vals.get("AvgLen_B2"), 2)
        if col == _COL_AVG_HGT_B1:  return _f(row.db_vals.get("AvgHeight_B1"), 1)
        if col == _COL_AVG_HGT_B2:  return _f(row.db_vals.get("AvgHeight_B2"), 1)
        if col == _COL_AVG_AREA_B1: return _f(row.db_vals.get("AvgArea_B1"), 3)
        if col == _COL_AVG_AREA_B2: return _f(row.db_vals.get("AvgArea_B2"), 3)
        return ""

    def _fg_color(self, row: ATYTrialRow):
        if row.status == ST_SAVED:    return QColor("#7ddf9a")
        if row.status == ST_ANALYZED: return QColor("#f0c040")
        if row.status == ST_ERROR:    return QColor("#ff6060")
        if row.status == ST_NO_FILE:  return QColor("#555")
        if row.status == "⚠️ kein Trial": return QColor("#f0a040")
        return QColor("#ddd")

    def update_row(self, idx: int):
        self.dataChanged.emit(
            self.index(idx, 0),
            self.index(idx, len(_HEADERS) - 1),
            [Qt.DisplayRole, Qt.ForegroundRole, Qt.BackgroundRole],
        )

    def set_rows(self, rows: List[ATYTrialRow]):
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def get_row(self, idx: int) -> ATYTrialRow:
        return self._rows[idx]

    def rows(self) -> List[ATYTrialRow]:
        return self._rows


# ---------------------------------------------------------------------------
# Haupt-Screen
# ---------------------------------------------------------------------------
class ATYBatchScreen(QWidget):

    def __init__(self, on_back_home=None, parent=None,
                 locked_series_id: int = None,
                 locked_series_name: str = ""):
        super().__init__(parent)
        self._on_back_home       = on_back_home
        self._locked_series_id   = locked_series_id
        self._locked_series_name = locked_series_name
        self._insider_mode       = False
        self._all_series: list   = []
        self._rows: List[ATYTrialRow] = []
        self._model    = _ATYTableModel([])
        self._pool     = QThreadPool()
        self._pool.setMaxThreadCount(min(8, max(2, os.cpu_count() or 4)))
        self._running  = False
        self._save_after = False
        self._build_ui()

    # ── UI-Aufbau ─────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        hdr = HeaderBar(title="YarnScope ATY – Batch-Auswertung", show_home=True)
        hdr.connect_home(self._go_home)
        root.addWidget(hdr)

        self._shortcut_insider = QShortcut(QKeySequence("Ctrl+Shift+J"), self)
        self._shortcut_insider.activated.connect(self._toggle_insider_mode)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)

        # ── Links: Series-Liste ──────────────────────────────────────────
        self._series_panel = QWidget()
        self._series_panel.setMaximumWidth(260)
        self._series_panel.setMinimumWidth(180)
        sp_layout = QVBoxLayout(self._series_panel)
        sp_layout.setContentsMargins(6, 6, 4, 4)
        sp_layout.setSpacing(4)

        lbl = QLabel("Serien")
        lbl.setStyleSheet("font-weight:bold; color:#88dddd; font-size:13px;")
        sp_layout.addWidget(lbl)

        self._btn_toggle_all = QPushButton("☑ Select all")
        self._btn_toggle_all.setFixedHeight(26)
        self._btn_toggle_all.setStyleSheet(
            "QPushButton{background:#2a2a2a;color:#aaa;border-radius:3px;"
            "font-size:11px;border:1px solid #444;}"
            "QPushButton:hover{background:#3a3a3a;color:#eee;}")
        self._btn_toggle_all.clicked.connect(self._toggle_all_series)
        self._btn_toggle_all.setVisible(False)
        sp_layout.addWidget(self._btn_toggle_all)

        self._series_list = QListWidget()
        self._series_list.setStyleSheet("""
            QListWidget { background:#1a1a1a; color:#ddd;
                          border:1px solid #333; font-size:12px; }
            QListWidget::item { padding:3px 4px; }
            QListWidget::item:hover { background:#2a2a2a; }
        """)
        sp_layout.addWidget(self._series_list, 1)
        splitter.addWidget(self._series_panel)

        # ── Rechts: Filter + Tabelle + Aktionen ─────────────────────────
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(4, 6, 8, 4)
        rv.setSpacing(4)

        frow = QHBoxLayout(); frow.setSpacing(8)
        self._chk_only_pending = QCheckBox("Nur ausstehende")
        self._chk_only_pending.setChecked(True)
        self._chk_only_pending.stateChanged.connect(self._refresh_proxy)
        frow.addWidget(self._chk_only_pending)
        self._chk_only_files = QCheckBox("Nur mit TDMS-File")
        self._chk_only_files.setChecked(True)
        self._chk_only_files.stateChanged.connect(self._refresh_proxy)
        frow.addWidget(self._chk_only_files)
        frow.addStretch()
        self._btn_scan = QPushButton("🔄 Ordner scannen")
        self._btn_scan.setObjectName("GreenBtn")
        self._btn_scan.setFixedHeight(28)
        self._btn_scan.clicked.connect(self._on_scan)
        frow.addWidget(self._btn_scan)
        rv.addLayout(frow)

        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setSortingEnabled(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setDefaultSectionSize(24)
        hdr_view = self._table.horizontalHeader()
        hdr_view.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(_COL_FILE, QHeaderView.Interactive)
        hdr_view.setMinimumSectionSize(45)
        self._table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._table.setColumnWidth(_COL_SERIES, 500)
        self._table.setColumnWidth(_COL_FILE,   200)
        self._table.setStyleSheet("""
            QTableView {
                background: #1a1a1a; color: #ddd;
                gridline-color: #2a2a2a; font-size: 12px;
                alternate-background-color: #1f1f1f;
            }
            QHeaderView::section {
                background: #2a2a2a; color: #aaa;
                border: 1px solid #333; padding: 3px;
            }
            QTableView::item:selected { background: #0e6e6e; color: #fff; }
        """)
        rv.addWidget(self._table, 1)
        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)

        # Aktions-Zeile
        brow = QHBoxLayout(); brow.setSpacing(8)
        self._lbl_status = QLabel("Bereit.")
        self._lbl_status.setStyleSheet("color:#aaa; font-size:12px;")
        brow.addWidget(self._lbl_status)
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setFixedHeight(16)
        self._progress.setStyleSheet(
            "QProgressBar{background:#222;border-radius:4px;}"
            "QProgressBar::chunk{background:#0e8a8a;border-radius:4px;}")
        brow.addWidget(self._progress, 1)
        brow.addStretch()
        self._btn_sel = QPushButton("☑ Nur Auswahl")
        self._btn_sel.setToolTip("Nur markierte Zeilen analysieren (Ctrl+Klick / Shift+Klick)")
        self._btn_sel.setFixedHeight(32)
        self._btn_sel.setEnabled(False)
        self._btn_sel.clicked.connect(self._on_batch_selection)
        brow.addWidget(self._btn_sel)
        self._btn_batch = QPushButton("⚡ Batch starten")
        self._btn_batch.setObjectName("GreenBtn")
        self._btn_batch.setFixedHeight(32)
        self._btn_batch.setStyleSheet(
            "QPushButton{background:#0e6e6e;color:#fff;border-radius:4px;"
            "font-size:13px;font-weight:bold;border:2px solid #0e8a8a;padding:0 12px;}"
            "QPushButton:hover{background:#0a5555;}"
            "QPushButton:disabled{background:#1a2a2a;color:#555;border-color:#333;}")
        self._btn_batch.setEnabled(False)
        self._btn_batch.clicked.connect(self._on_batch)
        brow.addWidget(self._btn_batch)
        self._btn_retry = QPushButton("🔁 Fehler wiederholen")
        self._btn_retry.setFixedHeight(30)
        self._btn_retry.setStyleSheet(
            "QPushButton{background:#5a2a2a;color:#f88;border-radius:4px;"
            "font-size:12px;border:1px solid #a44;padding:0 8px;}"
            "QPushButton:hover{background:#6a3a3a;}")
        self._btn_retry.setVisible(False)
        self._btn_retry.clicked.connect(self._on_retry_errors)
        brow.addWidget(self._btn_retry)
        self._btn_stop = QPushButton("⏹ Stopp")
        self._btn_stop.setFixedHeight(30)
        self._btn_stop.setVisible(False)
        self._btn_stop.clicked.connect(self._on_stop)
        brow.addWidget(self._btn_stop)
        rv.addLayout(brow)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 900])

        body = QWidget()
        bl = QVBoxLayout(body); bl.setContentsMargins(0, 0, 0, 0)
        bl.addWidget(splitter, 1)
        root.addWidget(body, 1)
        root.addWidget(FooterBar())

    # ── Series-Liste ──────────────────────────────────────────────────────

    def _load_series_list(self):
        try:
            rows = fetch_all(
                "SELECT s.ID, s.SeriesName, e.[Experiment ID] AS ExpID "
                "FROM tblTrialSeries s "
                "LEFT JOIN tblExperimente e ON e.ID = s.ExperimentID "
                "ORDER BY e.[Experiment ID] DESC, s.SeriesName"
            )
        except Exception:
            rows = []
        self._all_series = []
        for r in rows:
            sid   = r.get("ID")   or (r[0] if isinstance(r, (list, tuple)) else None)
            sname = r.get("SeriesName") or (r[1] if isinstance(r, (list, tuple)) else "")
            exp   = r.get("ExpID") or (r[2] if isinstance(r, (list, tuple)) else "")
            label = f"{exp} | {sname}" if exp else str(sname)
            if sid is not None:
                self._all_series.append((int(sid), label))

    def _rebuild_series_list_widget(self):
        self._series_list.clear()
        if self._insider_mode:
            series_to_show = self._all_series
        else:
            sid   = self._locked_series_id
            label = self._locked_series_name or f"Serie {sid}"
            series_to_show = [(sid, label)] if sid is not None else []

        for sid, label in series_to_show:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, sid)
            self._series_list.addItem(item)
            chk = QCheckBox(label)
            chk.setChecked(True)
            chk.setStyleSheet(
                "QCheckBox { color:#ddd; font-size:12px; padding:2px 4px; }"
                "QCheckBox::indicator { width:14px; height:14px; }"
                "QCheckBox::indicator:checked { background:#0e6e6e; border:1px solid #0e8a8a; border-radius:2px; }"
                "QCheckBox::indicator:unchecked { background:#333; border:1px solid #666; border-radius:2px; }")
            chk.stateChanged.connect(self._refresh_series_filter)
            self._series_list.setItemWidget(item, chk)
            item.setSizeHint(chk.sizeHint())

    def _checked_series_ids(self) -> List[int]:
        result = []
        for i in range(self._series_list.count()):
            item = self._series_list.item(i)
            chk  = self._series_list.itemWidget(item)
            sid  = item.data(Qt.UserRole)
            if sid is None:
                continue
            if chk is None or chk.isChecked():
                result.append(int(sid))
        return result

    def _toggle_all_series(self):
        all_checked = all(
            self._series_list.itemWidget(self._series_list.item(i)).isChecked()
            for i in range(self._series_list.count())
            if self._series_list.itemWidget(self._series_list.item(i))
        )
        new_state = not all_checked
        for i in range(self._series_list.count()):
            chk = self._series_list.itemWidget(self._series_list.item(i))
            if chk:
                chk.setChecked(new_state)
        self._btn_toggle_all.setText(
            "☐ Deselect all" if new_state else "☑ Select all")

    # ── Insider-Modus ─────────────────────────────────────────────────────

    def _toggle_insider_mode(self):
        self._insider_mode = not self._insider_mode
        self._btn_toggle_all.setVisible(self._insider_mode)
        self._rebuild_series_list_widget()
        if self._insider_mode:
            self._lbl_status.setText("🔓 Insider-Modus – alle Serien sichtbar")
        else:
            self._lbl_status.setText("Bereit.")
            QTimer.singleShot(50, self._on_scan)

    # ── Init ──────────────────────────────────────────────────────────────

    def _init_series_state(self):
        self._load_series_list()
        self._rebuild_series_list_widget()
        QTimer.singleShot(100, self._on_scan)

    # ── Scan ──────────────────────────────────────────────────────────────

    def _on_scan(self):
        checked = self._checked_series_ids()
        if not checked:
            self._lbl_status.setText("No series selected.")
            self._rows = []
            self._model.set_rows([])
            return
        self._btn_scan.setEnabled(False)
        self._btn_batch.setEnabled(False)
        self._lbl_status.setText("⏳ Scan gestartet…")
        sigs = _ScanSignals()
        sigs.status.connect(self._lbl_status.setText)
        sigs.done.connect(self._on_scan_done)
        sigs.error.connect(self._on_scan_error)
        worker = _ScanWorker(checked, sigs)
        self._pool.start(worker)

    def _on_scan_done(self, rows: list):
        self._rows = rows
        self._model.set_rows(self._rows)
        self._refresh_proxy()
        n_files = sum(1 for r in rows if r.tdms_path)
        n_pend  = sum(1 for r in rows if r.status == ST_PENDING)
        self._lbl_status.setText(
            f"{len(rows)} Trials | {n_files} mit TDMS | {n_pend} ausstehend")
        self._btn_scan.setEnabled(True)
        self._btn_batch.setEnabled(n_files > 0)
        self._btn_sel.setEnabled(n_files > 0)
        try:
            self._table.selectionModel().selectionChanged.connect(
                self._on_selection_changed)
        except Exception:
            pass

    def _on_scan_error(self, msg: str):
        self._btn_scan.setEnabled(True)
        self._btn_batch.setEnabled(False)
        QMessageBox.critical(self, "Scan-Fehler", msg)

    # ── Proxy-Filter ──────────────────────────────────────────────────────

    def _refresh_proxy(self):
        only_pend  = self._chk_only_pending.isChecked()
        only_files = self._chk_only_files.isChecked()
        filtered = []
        for r in self._rows:
            if only_files and r.tdms_path is None:
                continue
            if only_pend and r.status not in (ST_PENDING, ST_ANALYZED, ST_RUNNING, ST_ERROR):
                continue
            filtered.append(r)
        self._model.set_rows(filtered)

    def _refresh_series_filter(self):
        checked    = set(self._checked_series_ids())
        only_pend  = self._chk_only_pending.isChecked()
        only_files = self._chk_only_files.isChecked()
        display = []
        for r in self._rows:
            if r.series_id not in checked:
                continue
            if only_files and r.tdms_path is None:
                continue
            if only_pend and r.status not in (ST_PENDING, ST_ANALYZED, ST_RUNNING, ST_ERROR):
                continue
            display.append(r)
        self._model.set_rows(display)

    # ── Selektion ─────────────────────────────────────────────────────────

    def _selected_source_rows(self) -> list:
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            return []
        result = []
        for proxy_idx in indexes:
            source_idx = self._proxy.mapToSource(proxy_idx)
            result.append(source_idx.row())
        return sorted(set(result))

    def _on_selection_changed(self):
        sel = self._selected_source_rows()
        if sel:
            self._btn_batch.setText(f"⚡ {len(sel)} selektierte analysieren")
        else:
            self._btn_batch.setText("⚡ Batch starten")

    # ── Batch-Analyse ─────────────────────────────────────────────────────

    def _on_batch(self):
        self._save_after = True
        self._start_batch(pending_override=None)

    def _on_batch_selection(self):
        sel_rows = self._table.selectionModel().selectedRows()
        if not sel_rows:
            return
        pending = []
        for proxy_idx in sel_rows:
            source_idx = self._proxy.mapToSource(proxy_idx)
            row_obj = self._model.get_row(source_idx.row())
            if row_obj is None or row_obj.tdms_path is None:
                continue
            for i, r in enumerate(self._rows):
                if r is row_obj:
                    pending.append(i)
                    break
        if not pending:
            QMessageBox.information(
                self, "Auswahl", "Keine der markierten Zeilen hat ein TDMS-File.")
            return
        self._save_after = True
        self._start_batch(pending_override=pending)

    def _on_retry_errors(self):
        rows = self._model.rows()
        for r in rows:
            if r.status == ST_ERROR:
                r.status = ST_PENDING
        self._model.set_rows(rows)
        self._btn_retry.setVisible(False)
        self._save_after = True
        self._start_batch()

    def _start_batch(self, pending_override=None):
        if self._running:
            self._lbl_status.setText("⚠ Batch already running.")
            return
        target_rows = self._rows

        sel = self._selected_source_rows()
        if sel:
            pending = [
                i for i in sel
                if i < len(target_rows)
                and target_rows[i].tdms_path is not None
                and target_rows[i].status != ST_RUNNING
            ]
        elif pending_override is not None:
            pending = pending_override
        else:
            only_pending = self._chk_only_pending.isChecked()
            pending = [
                i for i, r in enumerate(target_rows)
                if r.tdms_path is not None and r.status != ST_RUNNING
                and (not only_pending or r.status not in (ST_SAVED,))
            ]

        if not pending:
            statuses: dict = {}
            for r in target_rows:
                statuses[r.status] = statuses.get(r.status, 0) + 1
            QMessageBox.information(
                self, "Batch",
                "Keine Trials zum Verarbeiten gefunden.\n\n"
                "Tipp: Deaktiviere 'Nur ausstehende' um gespeicherte erneut zu analysieren.\n\n"
                "Status-Verteilung:\n"
                + "\n".join(f"  '{k}': {v}" for k, v in sorted(statuses.items())))
            return

        self._running = True
        self._btn_batch.setEnabled(False)
        self._btn_retry.setVisible(False)
        self._btn_stop.setVisible(True)
        self._progress.setMaximum(len(pending))
        self._progress.setValue(0)
        self._progress.setVisible(True)

        ok = 0
        errors = 0

        for step, idx in enumerate(pending, 1):
            if not self._running:
                break
            row = target_rows[idx]
            row.status = ST_RUNNING

            # Zeile sofort aktualisieren
            display_rows = self._model.rows()
            for di, dr in enumerate(display_rows):
                if dr is row:
                    self._model.update_row(di)
                    break
            self._progress.setValue(step - 1)
            self._lbl_status.setText(
                f"Analysiere {step}/{len(pending)}: {row.tdms_path.name}")
            QApplication.processEvents()

            try:
                from ui.yarnscope.dty_tdms_reader import (
                    read_first_numeric_channel, read_step_mm_from_tdms,
                )
                from ui.yarnscope.thick_spot_analysis import (
                    detect_thick_spots, compute_db_values,
                )

                y     = read_first_numeric_channel(str(row.tdms_path))
                mm_pp = read_step_mm_from_tdms(str(row.tdms_path))
                if y is None or len(y) == 0:
                    raise ValueError("Kein Signal im TDMS-File.")
                if mm_pp is None or mm_pp <= 0:
                    mm_pp = 0.25

                arr = np.asarray(y, dtype=float)
                # mm-Normierung (wie in aty_yarnscope_tab)
                if float(np.median(arr)) >= 10.0:
                    arr = arr / 1000.0

                total_mm = float(len(arr) * mm_pp)
                spots    = detect_thick_spots(arr, float(mm_pp))
                db_vals  = compute_db_values(spots, total_mm)

                row.db_vals = db_vals

                if self._save_after and row.trial_id is not None:
                    saved_ok = _save_aty_to_db(row.trial_id, db_vals, row.tdms_path)
                    row.status = ST_SAVED if saved_ok else ST_ERROR
                    if not saved_ok:
                        row.error_msg = "DB-Schreibfehler"
                        errors += 1
                    else:
                        ok += 1
                else:
                    row.status = ST_ANALYZED
                    ok += 1

            except Exception as e:
                row.status    = ST_ERROR
                row.error_msg = str(e)
                errors += 1
                print(f"[ATY Batch] Fehler idx={idx} trial={row.trial_id}: {e}")

            # Zeile nach Analyse aktualisieren
            display_rows = self._model.rows()
            for di, dr in enumerate(display_rows):
                if dr is row:
                    self._model.update_row(di)
                    break
            self._progress.setValue(step)
            QApplication.processEvents()

        # Fertig
        self._running = False
        self._btn_stop.setVisible(False)
        self._btn_batch.setEnabled(True)
        self._progress.setVisible(False)
        self._btn_retry.setVisible(errors > 0)
        self._lbl_status.setText(
            f"✅ Fertig – {ok}/{len(pending)} gespeichert"
            + (f" | ❌ {errors} Fehler" if errors else ""))

    def _on_stop(self):
        self._running = False
        self._btn_stop.setVisible(False)
        self._btn_batch.setEnabled(True)
        self._lbl_status.setText("Gestoppt.")
        self._progress.setVisible(False)

    # ── Navigation ────────────────────────────────────────────────────────

    def _go_home(self):
        if callable(self._on_back_home):
            self._on_back_home()

    def showEvent(self, ev):
        super().showEvent(ev)
        QTimer.singleShot(100, self._init_series_state)