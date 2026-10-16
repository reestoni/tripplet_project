from __future__ import annotations
# ui/screen_aty_batch.py
"""Batch-Verarbeitungs-Screen für ATY TDMS-Dateien (YarnScope ATY Dickstellen-Analyse).

Ermöglicht es, viele ATY-Trials auf einmal zu analysieren:
  1. Serien aus der DB auswählen (Checkbox-Liste)
  2. TDMS-Dateien im konfigurierten ATY-Ordner scannen
  3. Analyse im Hintergrund ausführen
  4. Ergebnisse (Kern, Frequenz, Bulk Index, Bin1/Bin2 u.a. -- siehe
     aty_core_analysis.DB_COLUMN_MAP) in tblLaborATYoMat schreiben

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

from db.connection import fetch_all, execute, new_global_id
from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
import app_meta

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------
ATY_TDMS_BASE_DIR = r"H:\Technik\TrippleT\ATYtdms"

# Status-Werte
ST_NO_FILE  = "—"
ST_PENDING  = "pending"
ST_RUNNING  = "running…"
ST_SAVED    = "✅ saved"
ST_ERROR    = "❌ error"
ST_ANALYZED = "🔍 analysiert"

# Spalten der Ergebnistabelle
_COL_SERIES   = 0
_COL_TRIAL_NO = 1
_COL_TRIAL_ID = 2
_COL_FILE     = 3
_COL_STATUS   = 4
_COL_LENGTH_M   = 5
_COL_CORE_UM    = 6
_COL_BULK_PCT   = 7
_COL_DENSITY    = 8
_COL_BIN1_PCT   = 9
_COL_CORE_CV    = 10

_HEADERS = [
    "Series", "Trial", "TrialID", "File", "Status",
    "Length [m]", "Core [µm]", "Bulk Index [%]",
    "Freq [1/m]", "Bin1 % (Kurzhocker)", "Core CV [%]",
]

# DB-Spalten für tblLaborATYoMat -- Single Source of Truth ist
# aty_core_analysis.DB_COLUMN_MAP; hier nur importiert, nicht dupliziert
# (frueher, mit der alten thick_spot_analysis-Methode, war das eine
# eigenstaendige 130-Spalten-Liste -- seit 2026-08-13 komplett auf die neue
# Kern-Analyse umgestellt, siehe CLAUDE.md).
from ui.yarnscope.aty_core_analysis import (
    analyze_trial as _core_analyze_trial,
    to_db_row as _core_to_db_row,
    from_db_row as _core_from_db_row,
    DB_COLUMNS as _ALL_DB_COLS,
)


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
                sname = series_map.get(sid, f"Series {sid}")
                rows.append(ATYTrialRow(
                    series_id=sid, series_name=sname,
                    trial_no=vno, trial_id=None,
                    tdms_path=fpath, status="⚠️ no trial",
                ))

        rows.sort(key=lambda r: (r.series_id, r.trial_no))
        return rows


def build_calibration_dataset(series_ids: List[int]) -> List[Dict[str, Any]]:
    """Recalibration-batch builder for aty_core_analysis.suggest_radar_bounds():
    DB-first, TDMS-fallback per trial, so recalibrating from trials that have
    already been analyzed and saved (the common case as more ATY trials get
    saved through normal use) needs no TDMS file access at all - only trials
    with no tblLaborATYoMat row yet fall back to reading + analyzing their
    TDMS file, exactly like the interactive batch run above.

    Reuses ATYFolderScanner.scan_multi() (same DB-batch-fetch + TDMS-folder-
    scan already used by the interactive batch screen) instead of querying
    either source again.

    A tblLaborATYoMat row only counts as usable if BulkIndexPct is actually
    set, not merely because Timestamp is - found in dev_local while testing
    this: all 15 rows of TrialSeries 270 have Timestamp set but every metric
    column NULL (stale rows, presumably from before the 2026-08-13 schema
    migration to the new 34-column layout, see CLAUDE.md). Trusting a
    non-empty row dict without checking its actual values would have quietly
    fed None into suggest_radar_bounds() for those trials instead of falling
    back to their TDMS file.

    Example (run from a scratch script, not part of the app UI - same
    pattern as suggest_radar_bounds() itself):
        from ui.screen_aty_batch import build_calibration_dataset
        from ui.yarnscope.aty_core_analysis import suggest_radar_bounds
        results = build_calibration_dataset([270, 288])
        print(suggest_radar_bounds(results))
    """
    from ui.yarnscope.dty_tdms_reader import read_aty_signal, read_step_mm_from_tdms

    rows = ATYFolderScanner.scan_multi(series_ids)
    results: List[Dict[str, Any]] = []
    for row in rows:
        if row.db_vals and row.db_vals.get("BulkIndexPct") is not None:
            results.append(_core_from_db_row(row.db_vals))
            continue
        if row.tdms_path is None:
            continue
        try:
            arr, ell = read_aty_signal(str(row.tdms_path))
            mm_pp = read_step_mm_from_tdms(str(row.tdms_path))
            if arr is None or len(arr) == 0:
                continue
            if mm_pp is None or mm_pp <= 0:
                mm_pp = 0.25
            results.append(_core_analyze_trial(arr, float(mm_pp), ellipticity_pct=ell))
        except Exception as e:
            print(f"[ATY Calibration] Fehler bei {row.tdms_path}: {e}")
    return results


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
            self._signals.status.emit("Scanning ATY TDMS folder…")
            rows = ATYFolderScanner.scan_multi(self._series_ids)
            n_files = sum(1 for r in rows if r.tdms_path)
            n_pend  = sum(1 for r in rows if r.status == ST_PENDING)
            self._signals.status.emit(
                f"Scan finished: {len(rows)} Trials | {n_files} with TDMS | {n_pend} pending"
            )
            self._signals.done.emit(rows)
        except Exception as e:
            self._signals.error.emit(f"{e}\n{traceback.format_exc()[-400:]}")


# ---------------------------------------------------------------------------
# DB-Speicher-Helfer
# ---------------------------------------------------------------------------
def _save_aty_to_db(trial_id: int, db_vals: Dict[str, Any],
                    tdms_path: Optional[Path] = None) -> bool:
    """Schreibt ATY-Analyse-Ergebnisse in tblLaborATYoMat (INSERT oder UPDATE).

    GlobalID identifiziert diese eine Zeile stabil ueber Merges hinweg
    (Offline-Arbeit + spaeteres Zusammenfuehren zweier DBs), nicht den Trial
    selbst (der hat sein eigenes GlobalID in tblTrial). Beim INSERT frisch
    vergeben (new_global_id(), UUID); beim UPDATE per COALESCE nur dann
    (neu) gesetzt, wenn die Zeile noch keins hat (z.B. Altzeilen von vor
    2026-08-13) -- ein bestehendes GlobalID wird nie ueberschrieben, sonst
    wuerde ein Merge-Schluessel unter der Zeile wegrutschen. UserID wird bei
    jedem Speichern (INSERT wie UPDATE) auf den aktuell eingeloggten User
    gesetzt.
    """

    def _v(key):
        v = db_vals.get(key)
        if key == "ParamsVersion":  # only non-numeric column -- keep as string
            return str(v) if v is not None else None
        try:
            f = float(v) if v is not None else None
        except Exception:
            return None
        # NaN/Inf reach here whenever a metric legitimately couldn't be
        # computed (e.g. Bin1HeightMedianUm with zero Bin1 loops, or
        # Ellipticity* on a trial with zero detected peaks) - mysql-connector
        # renders a bare Python NaN as the unquoted SQL token `nan`, not a
        # numeric literal, which MySQL then parses as a column reference
        # ("Unknown column 'nan' in 'field list'"). Store NULL instead.
        if f is not None and not np.isfinite(f):
            return None
        return f

    ts = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
    params = [_v(c) for c in _ALL_DB_COLS]
    user_id = (getattr(app_meta, "current_user", {}) or {}).get("id")

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
                f"UPDATE tblLaborATYoMat SET {', '.join(set_parts)}, "
                f"Timestamp=?, UserID=?, GlobalID=COALESCE(GlobalID, ?) WHERE TrialID=?"
            )
            execute(sql, params + [ts, user_id, new_global_id(), trial_id])
        else:
            cols_str = ", ".join(_ALL_DB_COLS)
            ph = ", ".join(["?"] * len(_ALL_DB_COLS))
            sql = (
                f"INSERT INTO tblLaborATYoMat "
                f"(TrialID, GlobalID, {cols_str}, Timestamp, UserID) "
                f"VALUES (?, ?, {ph}, ?, ?)"
            )
            execute(sql, [trial_id, new_global_id()] + params + [ts, user_id])
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
            if col in (_COL_TRIAL_NO, _COL_TRIAL_ID) or col >= _COL_LENGTH_M:
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
        if col == _COL_LENGTH_M: return _f(row.db_vals.get("LengthM"), 1)
        if col == _COL_CORE_UM:  return _f(row.db_vals.get("CoreMeanUm"), 1)
        if col == _COL_BULK_PCT: return _f(row.db_vals.get("BulkIndexPct"), 1)
        if col == _COL_DENSITY:  return _f(row.db_vals.get("DensityPerM"), 1)
        if col == _COL_BIN1_PCT: return _f(row.db_vals.get("Bin1Pct"), 1)
        if col == _COL_CORE_CV:  return _f(row.db_vals.get("CoreCVPct"), 2)
        return ""

    def _fg_color(self, row: ATYTrialRow):
        if row.status == ST_SAVED:    return QColor("#7ddf9a")
        if row.status == ST_ANALYZED: return QColor("#f0c040")
        if row.status == ST_ERROR:    return QColor("#ff6060")
        if row.status == ST_NO_FILE:  return QColor("#555")
        if row.status == "⚠️ no trial": return QColor("#f0a040")
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
                 locked_series_name: str = "",
                 sidebar_callbacks: Optional[dict] = None):
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
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None
        self._build_ui()

    # ── UI-Aufbau ─────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring).
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

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
        self._chk_only_pending = QCheckBox("Only pending")
        self._chk_only_pending.setChecked(True)
        self._chk_only_pending.stateChanged.connect(self._refresh_proxy)
        frow.addWidget(self._chk_only_pending)
        self._chk_only_files = QCheckBox("Only with TDMS file")
        self._chk_only_files.setChecked(True)
        self._chk_only_files.stateChanged.connect(self._refresh_proxy)
        frow.addWidget(self._chk_only_files)
        frow.addStretch()
        self._btn_scan = QPushButton("🔄 Scan folder")
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
        self._btn_sel = QPushButton("☑ Selection only")
        self._btn_sel.setToolTip("Analyse selected rows only (Ctrl+click / Shift+click)")
        self._btn_sel.setFixedHeight(32)
        self._btn_sel.setEnabled(False)
        self._btn_sel.clicked.connect(self._on_batch_selection)
        brow.addWidget(self._btn_sel)
        self._btn_batch = QPushButton("⚡ Start batch")
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
        self._btn_retry = QPushButton("🔁 Retry errors")
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

        # Rückweg zur aufrufenden ShowExperimentScreen-Instanz (2026-08-28,
        # Nutzer-Bugreport: "beim batchauftrag in yarnscope komm ich nicht
        # mehr zurück zu show experiment") - ging bis zur TopBar-Abschaffung
        # (2026-08-27) über den HeaderBar-Home-Button, der hier nie durch
        # ein Sidebar-Äquivalent ersetzt wurde; `_go_home()`/`_on_back_home`
        # existierten unverändert weiter, hatten aber kein UI-Gegenstück mehr.
        # Bewusst ein eigener sichtbarer Button statt eines Sidebar-Eintrags
        # wie bei ShowExperimentScreen selbst (dort 2026-08-27 entfernt) -
        # anders als dort führt "zurück" hier zu einer KONKRETEN, bereits
        # geöffneten ShowExperimentScreen-Instanz mit Zustand (nicht nur
        # generisch zu "All Experiments"), das braucht eine direkte Aktion.
        back_row = QHBoxLayout()
        back_row.setContentsMargins(8, 6, 8, 0)
        self._btn_back = QPushButton("← Back to Show Experiment")
        self._btn_back.setFixedHeight(26)
        self._btn_back.setStyleSheet(
            "QPushButton{background:#2a2a2a;color:#aaa;border-radius:3px;"
            "font-size:11px;border:1px solid #444;padding:2px 10px;}"
            "QPushButton:hover{background:#3a3a3a;color:#eee;}")
        self._btn_back.clicked.connect(self._go_home)
        back_row.addWidget(self._btn_back)
        back_row.addStretch(1)
        bl.addLayout(back_row)

        bl.addWidget(splitter, 1)
        content_layout.addWidget(body, 1)
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
            label = self._locked_series_name or f"Series {sid}"
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
            self._lbl_status.setText("🔓 Insider mode – all series visible")
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
            f"{len(rows)} Trials | {n_files} with TDMS | {n_pend} pending")
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
        QMessageBox.critical(self, "Scan error", msg)

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
            self._btn_batch.setText(f"⚡ {len(sel)} analyse selected")
        else:
            self._btn_batch.setText("⚡ Start batch")

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
                self, "Selection", "None of the selected rows has a TDMS file.")
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
                "No trials to process found.\n"
                "\n"
                "Tip: switch off 'Only pending' to analyse saved ones again.\n"
                "\n"
                "Status distribution:\n"
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
                from ui.yarnscope.dty_tdms_reader import read_aty_signal, read_step_mm_from_tdms

                arr, ell = read_aty_signal(str(row.tdms_path))
                mm_pp = read_step_mm_from_tdms(str(row.tdms_path))
                if arr is None or len(arr) == 0:
                    raise ValueError("No signal in the TDMS file.")
                if mm_pp is None or mm_pp <= 0:
                    mm_pp = 0.25

                metrics = _core_analyze_trial(arr, float(mm_pp), ellipticity_pct=ell)
                db_vals = _core_to_db_row(metrics)

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
            f"✅ Fertig – {ok}/{len(pending)} saved"
            + (f" | ❌ {errors} errors" if errors else ""))

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

    def _refresh_sidebar(self):
        """Baut die Sidebar-Navigation neu auf, falls sich der Access-Level
        seit dem letzten Aufbau geändert hat, sonst nur die Badges (siehe
        ui/widgets/sidebar_nav.py::refresh_lazy_sidebar())."""
        try:
            level = int((app_meta.current_user or {}).get("access_level") or 0)
        except Exception:
            level = 0
        sidebar_nav.refresh_lazy_sidebar(self, level)

    def showEvent(self, ev):
        super().showEvent(ev)
        QTimer.singleShot(100, self._init_series_state)
        try:
            self._refresh_sidebar()
        except Exception:
            pass