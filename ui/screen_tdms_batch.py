from __future__ import annotations
# ui/screen_tdms_batch.py
"""Batch-Verarbeitungs-Screen für TDMS-Dateien (YarnScope DTY-Analyse).

Ermöglicht es, viele Trials auf einmal zu analysieren:
  1. Serien aus der DB auswählen (Checkbox-Liste)
  2. TDMS-Dateien im konfigurierten Ordner scannen
  3. Analyse im Hintergrund ausführen (_AnalysisWorker via QThreadPool)
  4. Ergebnisse (Knoten/m, Stabilität, CV%) in die DB schreiben

Datenbankbezug:
  - Liest: tblTrialSeries, tblTrial, tblTrialSettings (für TDMS-Pfad-Konfiguration)
  - Schreibt: tblTrialSettings (KnotenProMeter, Stabilitaet, CV usw.)

TDMS-Datei-Namenskonvention: <ExperimentID>_<TrialNr>.tdms
  Wird von TDMSFolderScanner._parse_ids() geparst.

Parallelisierung: bis zu 4 Worker parallel (QThreadPool),
  Fortschrittsanzeige via QProgressBar.
"""

# ui/screen_tdms_batch.py
"""
TrippleT – YarnScope Batch-Auswertung
======================================
Scannt den TDMS-Netzwerkordner, ordnet Files via Dateiname (TrialSeriesID_Versuch)
den Trials zu und erlaubt Einzel- und Batch-Analyse mit DB-Speicherung.

Architektur:
  - TDMSFolderScanner   : scannt Ordner, parst Filenamen, löst Trial-IDs auf
  - _AnalysisWorker     : QRunnable, führt analyze_series im Hintergrund aus
  - _BatchTableModel    : QAbstractTableModel für die Ergebnistabelle
  - TDMSBatchScreen     : Haupt-Widget (eingehängt in main.py wie CanvasScreen)
"""


import os
import re
import traceback
from dataclasses import dataclass, field
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
    QComboBox, QTableView, QHeaderView, QProgressBar,
    QMessageBox, QSplitter, QFrame, QSizePolicy, QAbstractItemView,
    QCheckBox, QListWidget, QListWidgetItem, QApplication,
)

from db.connection import fetch_all, get_connection
from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from ui.yarnscope.dty_analysis import analyze_series, full_extract_vals, run_stab_models
from ui.yarnscope.dty_tdms_reader import read_dty_signal, read_step_mm_from_tdms
from ui.yarnscope import dty_service as _dty_service

import app_meta

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------
# Ordner der DTY-TDMS-Dateien (Env TRIPPLET_YARNSCOPE_DTY_DIR, siehe dty_service)
TDMS_BASE_DIR = str(_dty_service.tdms_base())

# Minimale Segmentpunkte für analyze_series (analog YarnScope-Default)
DEFAULT_MIN_SEG_PTS = 3

# Spalten der Tabelle
# Feste Spalten
_COL_SERIES   = 0
_COL_TRIAL_NO = 1
_COL_TRIAL_ID = 2
_COL_FILE     = 3
_COL_STATUS   = 4

# DB-Felder (dynamisch)
_COL_FPM = 5
_COL_CV_FP = 6
_COL_AVGFP = 7
_COL_STDDEVFP = 8
_COL_AVGKL = 9
_COL_CV_KL = 10
_COL_STDDEVKL = 11
_COL_MAXKL = 12
_COL_AVGOL = 13
_COL_CV_OL = 14
_COL_STDDEVOL = 15
_COL_MAXOL = 16
_COL_AKNOTS = 17
_COL_BKNOTS = 18
_COL_CKNOTS = 19
_COL_SKEWKL = 20
_COL_SKEWOL = 21
_COL_RAPPORTCV = 22
_COL_RAPPORTCVLOCAL = 23
_COL_KL_AC1 = 24
_COL_KL_AC2 = 25
_COL_KL_AC3 = 26
_COL_KL_TAILRATIO = 27
_COL_OL_TAILRATIO = 28
_COL_KA_OA_RATIO = 29
_COL_KL_ASYMMEAN = 30
_COL_KL_ASYMCV = 31
_COL_KURTKL = 32
_COL_KURTOL = 33
_COL_THICKNESSDRIFT = 34
_COL_SPECTRALENERGYLOW = 35
_COL_SPECTRALENERGYMID = 36
_COL_SPECTRALENERGYHIGH = 37
_COL_CKNOT_CLUSTERMEAN = 38
_COL_CKNOT_CLUSTERMAX = 39
_COL_STAB_03 = 40
_COL_STAB_06 = 41
_COL_STAB_10 = 42
_COL_STAB_13 = 43
_COL_STAB_03_MODEL = 44
_COL_STAB_06_MODEL = 45
_COL_STAB_10_MODEL = 46
_COL_STAB_13_MODEL = 47
_COL_A_KNOTS = 48
_COL_B_KNOTS = 49
_COL_C_KNOTS = 50
_COL_D_KNOTS = 51
_COL_E_KNOTS = 52
_COL_F_KNOTS = 53
_COL_G_KNOTS = 54
_COL_H_KNOTS = 55
_COL_I_KNOTS = 56
_COL_J_KNOTS = 57
_COL_K_KNOTS = 58
_COL_L_KNOTS = 59
_COL_M_KNOTS = 60
_COL_N_KNOTS = 61
_COL_O_KNOTS = 62
_COL_P_KNOTS = 63
_COL_Q_KNOTS = 64
_COL_R_KNOTS = 65
_COL_S_KNOTS = 66
_COL_T_KNOTS = 67
_COL_KL_BIN_1 = 68
_COL_KL_BIN_2 = 69
_COL_KL_BIN_3 = 70
_COL_KL_BIN_4 = 71
_COL_KL_BIN_5 = 72
_COL_KL_BIN_6 = 73
_COL_KL_BIN_7 = 74
_COL_KL_BIN_8 = 75
_COL_KL_BIN_9 = 76
_COL_KL_BIN_10 = 77
_COL_OL_BIN_1 = 78
_COL_OL_BIN_2 = 79
_COL_OL_BIN_3 = 80
_COL_OL_BIN_4 = 81
_COL_OL_BIN_5 = 82
_COL_OL_BIN_6 = 83
_COL_OL_BIN_7 = 84
_COL_OL_BIN_8 = 85
_COL_OL_BIN_9 = 86
_COL_OL_BIN_10 = 87
_COL_FALLHOEHE1 = 88
_COL_FALLHOEHE2 = 89
_COL_FALLHOEHE3 = 90
_COL_FALLHOEHE4 = 91
_COL_FALLHOEHE5 = 92
_COL_FALLHOEHE6 = 93
_COL_FALLHOEHE7 = 94
_COL_FALLHOEHE8 = 95
_COL_FALLHOEHE9 = 96
_COL_FALLHOEHE10 = 97
_COL_WINKELSEGMENT1 = 98
_COL_WINKELSEGMENT2 = 99
_COL_WINKELSEGMENT3 = 100
_COL_WINKELSEGMENT4 = 101
_COL_WINKELSEGMENT5 = 102
_COL_WINKELSEGMENT6 = 103
_COL_WINKELSEGMENT7 = 104
_COL_WINKELSEGMENT8 = 105
_COL_WINKELSEGMENT9 = 106
_COL_WINKELSEGMENT10 = 107
_COL_KA_BIN_1 = 108
_COL_KA_BIN_2 = 109
_COL_KA_BIN_3 = 110
_COL_KA_BIN_4 = 111
_COL_KA_BIN_5 = 112
_COL_KA_BIN_6 = 113
_COL_KA_BIN_7 = 114
_COL_KA_BIN_8 = 115
_COL_KA_BIN_9 = 116
_COL_KA_BIN_10 = 117
_COL_KA_BIN_11 = 118
_COL_KA_BIN_12 = 119
_COL_KA_BIN_13 = 120
_COL_KA_BIN_14 = 121
_COL_KA_BIN_15 = 122
_COL_KA_BIN_16 = 123
_COL_KA_BIN_17 = 124
_COL_KA_BIN_18 = 125
_COL_KA_BIN_19 = 126
_COL_KA_BIN_20 = 127
_COL_OA_BIN_1 = 128
_COL_OA_BIN_2 = 129
_COL_OA_BIN_3 = 130
_COL_OA_BIN_4 = 131
_COL_OA_BIN_5 = 132
_COL_OA_BIN_6 = 133
_COL_OA_BIN_7 = 134
_COL_OA_BIN_8 = 135
_COL_OA_BIN_9 = 136
_COL_OA_BIN_10 = 137
_COL_OA_BIN_11 = 138
_COL_OA_BIN_12 = 139
_COL_OA_BIN_13 = 140
_COL_OA_BIN_14 = 141
_COL_OA_BIN_15 = 142
_COL_OA_BIN_16 = 143
_COL_OA_BIN_17 = 144
_COL_OA_BIN_18 = 145
_COL_OA_BIN_19 = 146
_COL_OA_BIN_20 = 147

_HEADERS = ['Series', 'Trial', 'TrialID', 'File', 'Status', 'FPm', 'CV_FP', 'AvgFP', 'StdDevFP', 'AvgKL', 'CV_KL', 'StdDevKL', 'maxKL', 'AvgOL', 'CV_OL', 'StdDevOL', 'maxOL', 'AKnots', 'BKnots', 'CKnots', 'SkewKL', 'SkewOL', 'RapportCV', 'RapportCVLocal', 'KL_AC1', 'KL_AC2', 'KL_AC3', 'KL_TailRatio', 'OL_TailRatio', 'KA_OA_Ratio', 'KL_AsymMean', 'KL_AsymCV', 'KurtKL', 'KurtOL', 'ThicknessDrift', 'SpectralEnergyLow', 'SpectralEnergyMid', 'SpectralEnergyHigh', 'CKnot_ClusterMean', 'CKnot_ClusterMax', 'Stab_03', 'Stab_06', 'Stab_10', 'Stab_13', 'Stab_03_model', 'Stab_06_model', 'Stab_10_model', 'Stab_13_model', 'a_knots', 'b_knots', 'c_knots', 'd_knots', 'e_knots', 'f_knots', 'g_knots', 'h_knots', 'i_knots', 'j_knots', 'k_knots', 'l_knots', 'm_knots', 'n_knots', 'o_knots', 'p_knots', 'q_knots', 'r_knots', 's_knots', 't_knots', 'kl_bin_1', 'kl_bin_2', 'kl_bin_3', 'kl_bin_4', 'kl_bin_5', 'kl_bin_6', 'kl_bin_7', 'kl_bin_8', 'kl_bin_9', 'kl_bin_10', 'ol_bin_1', 'ol_bin_2', 'ol_bin_3', 'ol_bin_4', 'ol_bin_5', 'ol_bin_6', 'ol_bin_7', 'ol_bin_8', 'ol_bin_9', 'ol_bin_10', 'Fallhöhe1', 'Fallhöhe2', 'Fallhöhe3', 'Fallhöhe4', 'Fallhöhe5', 'Fallhöhe6', 'Fallhöhe7', 'Fallhöhe8', 'Fallhöhe9', 'Fallhöhe10', 'Winkelsegment1', 'Winkelsegment2', 'Winkelsegment3', 'Winkelsegment4', 'Winkelsegment5', 'Winkelsegment6', 'Winkelsegment7', 'Winkelsegment8', 'Winkelsegment9', 'Winkelsegment10', 'ka_bin_1', 'ka_bin_2', 'ka_bin_3', 'ka_bin_4', 'ka_bin_5', 'ka_bin_6', 'ka_bin_7', 'ka_bin_8', 'ka_bin_9', 'ka_bin_10', 'ka_bin_11', 'ka_bin_12', 'ka_bin_13', 'ka_bin_14', 'ka_bin_15', 'ka_bin_16', 'ka_bin_17', 'ka_bin_18', 'ka_bin_19', 'ka_bin_20', 'oa_bin_1', 'oa_bin_2', 'oa_bin_3', 'oa_bin_4', 'oa_bin_5', 'oa_bin_6', 'oa_bin_7', 'oa_bin_8', 'oa_bin_9', 'oa_bin_10', 'oa_bin_11', 'oa_bin_12', 'oa_bin_13', 'oa_bin_14', 'oa_bin_15', 'oa_bin_16', 'oa_bin_17', 'oa_bin_18', 'oa_bin_19', 'oa_bin_20']

# DB-Felder Liste für Scan-Query und Display
_DB_FIELDS = ['FPm', 'CV_FP', 'AvgFP', 'StdDevFP', 'AvgKL', 'CV_KL', 'StdDevKL', 'maxKL', 'AvgOL', 'CV_OL', 'StdDevOL', 'maxOL', 'AKnots', 'BKnots', 'CKnots', 'SkewKL', 'SkewOL', 'RapportCV', 'RapportCVLocal', 'KL_AC1', 'KL_AC2', 'KL_AC3', 'KL_TailRatio', 'OL_TailRatio', 'KA_OA_Ratio', 'KL_AsymMean', 'KL_AsymCV', 'KurtKL', 'KurtOL', 'ThicknessDrift', 'SpectralEnergyLow', 'SpectralEnergyMid', 'SpectralEnergyHigh', 'CKnot_ClusterMean', 'CKnot_ClusterMax', 'Stab_03', 'Stab_06', 'Stab_10', 'Stab_13', 'Stab_03_model', 'Stab_06_model', 'Stab_10_model', 'Stab_13_model', 'a_knots', 'b_knots', 'c_knots', 'd_knots', 'e_knots', 'f_knots', 'g_knots', 'h_knots', 'i_knots', 'j_knots', 'k_knots', 'l_knots', 'm_knots', 'n_knots', 'o_knots', 'p_knots', 'q_knots', 'r_knots', 's_knots', 't_knots', 'kl_bin_1', 'kl_bin_2', 'kl_bin_3', 'kl_bin_4', 'kl_bin_5', 'kl_bin_6', 'kl_bin_7', 'kl_bin_8', 'kl_bin_9', 'kl_bin_10', 'ol_bin_1', 'ol_bin_2', 'ol_bin_3', 'ol_bin_4', 'ol_bin_5', 'ol_bin_6', 'ol_bin_7', 'ol_bin_8', 'ol_bin_9', 'ol_bin_10', 'Fallhöhe1', 'Fallhöhe2', 'Fallhöhe3', 'Fallhöhe4', 'Fallhöhe5', 'Fallhöhe6', 'Fallhöhe7', 'Fallhöhe8', 'Fallhöhe9', 'Fallhöhe10', 'Winkelsegment1', 'Winkelsegment2', 'Winkelsegment3', 'Winkelsegment4', 'Winkelsegment5', 'Winkelsegment6', 'Winkelsegment7', 'Winkelsegment8', 'Winkelsegment9', 'Winkelsegment10', 'ka_bin_1', 'ka_bin_2', 'ka_bin_3', 'ka_bin_4', 'ka_bin_5', 'ka_bin_6', 'ka_bin_7', 'ka_bin_8', 'ka_bin_9', 'ka_bin_10', 'ka_bin_11', 'ka_bin_12', 'ka_bin_13', 'ka_bin_14', 'ka_bin_15', 'ka_bin_16', 'ka_bin_17', 'ka_bin_18', 'ka_bin_19', 'ka_bin_20', 'oa_bin_1', 'oa_bin_2', 'oa_bin_3', 'oa_bin_4', 'oa_bin_5', 'oa_bin_6', 'oa_bin_7', 'oa_bin_8', 'oa_bin_9', 'oa_bin_10', 'oa_bin_11', 'oa_bin_12', 'oa_bin_13', 'oa_bin_14', 'oa_bin_15', 'oa_bin_16', 'oa_bin_17', 'oa_bin_18', 'oa_bin_19', 'oa_bin_20']


# Status-Werte
ST_NO_FILE   = "—"
ST_PENDING   = "pending"
ST_RUNNING   = "running…"
ST_SAVED     = "✅ saved"
ST_ERROR     = "❌ error"
ST_ANALYZED  = "🔍 analysiert"


# ---------------------------------------------------------------------------
# Datenklasse pro Trial-Zeile
# ---------------------------------------------------------------------------
@dataclass
class TrialRow:
    """Dataclass für eine Zeile im Batch-Screen: Trial-Metadaten + Analyse-Ergebnis + Status."""
    series_id:    int
    series_name:  str
    trial_no:     int
    trial_id:     Optional[int]      # None = Trial nicht in DB gefunden
    tdms_path:    Optional[Path]     # None = kein File im Ordner
    status:       str = ST_NO_FILE
    result:       Dict[str, Any] = field(default_factory=dict)
    error_msg:    str = ""

    # Kurzwerte für Tabelle (nach Analyse befüllt)
    db_vals: Dict[str, Any] = field(default_factory=dict)  # alle DB-Felder


# ---------------------------------------------------------------------------
# TDMS Folder Scanner
# ---------------------------------------------------------------------------
class TDMSFolderScanner:
    """Statische Hilfsklasse zum Scannen von TDMS-Dateien und Laden von DB-Metadaten."""
    """Scannt TDMS_BASE_DIR und baut eine Liste von TrialRow-Objekten auf."""

    @staticmethod
    def _parse_ids(stem: str) -> Optional[Tuple[int, int]]:
        """Parst ExperimentID und TrialNr aus einem TDMS-Dateinamen-Stem.

        Erwartet Format: ``<ExperimentID>_<TrialNr>`` (z.B. ``"2024001_03"``).

        Returns:
            (ExperimentID, TrialNr) als int-Tupel, oder None bei ungültigem Format.
        """
        """
        Parst TrialSeriesID und Versuchsnummer aus Dateiname.
        Format: ...<SeriesID>_<VersuchNr>_...
        Gleiche Logik wie DTYKnotsView._parse_ids_from_tdms_name.
        """
        return _dty_service.parse_tdms_ids(stem)

    @staticmethod
    def _build_tdms_map() -> Dict[Tuple[int, int], Path]:
        """Scannt den konfigurierten TDMS-Ordner und erstellt ein {(ExpID, TrialNr): Path}-Dict."""
        """Liest den TDMS-Ordner einmal ein und gibt eine (sid, vno)->Path Map zurück."""
        base = Path(TDMS_BASE_DIR)
        tdms_map: Dict[Tuple[int, int], Path] = {}
        if base.exists():
            for f in base.iterdir():
                if f.suffix.lower() == ".tdms":
                    ids = TDMSFolderScanner._parse_ids(f.stem)
                    if ids:
                        tdms_map[ids] = f
        return tdms_map

    @staticmethod
    def _fetch_saved(trial_ids: List[int], fields_only: bool = False) -> Tuple[set, dict]:
        """Lädt bereits gespeicherte Analyse-Werte aus tblTrialSettings.

        Returns:
            (saved_ids, vals_by_id): saved_ids = Set bereits analysierter Trial-IDs,
            vals_by_id = Dict {TrialID: {Feld: Wert}}.
        """
        """
        Lädt gespeicherte Analyse-Werte aus tbllabordtyomat,
        gefiltert auf die übergebenen TrialIDs.
        fields_only=True: nur TrialID laden (für Insider-Modus, sehr schnell).
        fields_only=False: alle 140+ Felder laden (für normale Ansicht).
        Gibt (saved_ids_set, saved_vals_dict) zurück.
        """
        saved_ids: set = set()
        saved_vals: dict = {}
        if not trial_ids:
            return saved_ids, saved_vals
        id_placeholders = ",".join(["?"] * len(trial_ids))
        try:
            if fields_only:
                # Nur IDs – kein Daten-Transfer, sehr schnell
                saved = fetch_all(
                    f"SELECT TrialID FROM tbllabordtyomat "
                    f"WHERE TrialID IN ({id_placeholders}) "
                    f"AND Timestamp IS NOT NULL",
                    trial_ids
                )
                for r in saved:
                    tid_r = r.get("TrialID") if isinstance(r, dict) else r[0]
                    if tid_r is not None:
                        saved_ids.add(int(tid_r))
                # saved_vals bleibt leer – db_vals werden nicht befüllt
            else:
                db_fields_sql = ", ".join(
                    f"[{f}]" if any(c in f for c in "äöü ") else f
                    for f in _DB_FIELDS
                )
                saved = fetch_all(
                    f"SELECT TrialID, {db_fields_sql} "
                    f"FROM tbllabordtyomat "
                    f"WHERE TrialID IN ({id_placeholders}) "
                    f"AND Timestamp IS NOT NULL",
                    trial_ids
                )
                for r in saved:
                    tid_r = r.get("TrialID") if isinstance(r, dict) else r[0]
                    if tid_r is None:
                        continue
                    tid_r = int(tid_r)
                    saved_ids.add(tid_r)
                    d = {}
                    for _i, _fn in enumerate(_DB_FIELDS):
                        _raw = r.get(_fn) if isinstance(r, dict) else r[_i + 1]
                        d[_fn] = _raw
                    saved_vals[tid_r] = d
        except Exception:
            pass
        return saved_ids, saved_vals

    @staticmethod
    def scan_multi(series_ids: List[int], load_db_vals: bool = True) -> List[TrialRow]:
        """Scannt TDMS-Dateien für mehrere Serien und gibt eine Liste von TrialRows zurück.

        Args:
            series_ids:   Liste der zu scannenden TrialSeries-IDs.
            load_db_vals: Wenn True, werden bereits gespeicherte Werte aus der DB geladen.
        """
        """
        Effizienter Scan für mehrere Series gleichzeitig.
        Liest Ordner und alle DB-Tabellen jeweils genau einmal.
        load_db_vals=False: nur Status/Dateinamen, keine 140-Felder-Query
                            (für Insider-Modus mit vielen Serien).
        load_db_vals=True:  alle DB-Felder laden (für normale Einzelserie-Ansicht).
        """
        if not series_ids:
            return []

        placeholders = ",".join(["?"] * len(series_ids))

        # 1) Ordner einmal einlesen
        tdms_map = TDMSFolderScanner._build_tdms_map()

        # 2) Series-Infos: ein Query
        try:
            series_rows = fetch_all(
                f"SELECT s.ID, s.SeriesName, e.[Experiment ID] AS ExpID "
                f"FROM tblTrialSeries s "
                f"LEFT JOIN tblExperimente e ON e.ID = s.ExperimentID "
                f"WHERE s.ID IN ({placeholders})",
                series_ids
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

        # 3) Trials: ein Query
        try:
            trial_rows = fetch_all(
                f"SELECT ID, TrialSeriesID, Versuchsnummer FROM tblTrial "
                f"WHERE TrialSeriesID IN ({placeholders}) "
                f"ORDER BY TrialSeriesID, Versuchsnummer",
                series_ids
            )
        except Exception:
            trial_rows = []

        # 4) Gespeicherte Resultate: fields_only wenn kein vollständiges Laden nötig
        trial_ids = [
            int(tr.get("ID") if isinstance(tr, dict) else tr[0])
            for tr in trial_rows
        ]
        saved_ids, saved_vals = TDMSFolderScanner._fetch_saved(
            trial_ids, fields_only=not load_db_vals
        )

        # 5) TrialRow-Objekte bauen
        rows: List[TrialRow] = []
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

            tr_row = TrialRow(
                series_id=sid, series_name=sname,
                trial_no=vno, trial_id=tid,
                tdms_path=tdms, status=st,
            )
            if tid in saved_vals:
                tr_row.db_vals = saved_vals[tid]
            rows.append(tr_row)
            known_keys.add((sid, vno))

        # Trials die in DB fehlen aber ein TDMS-File haben
        series_ids_set = set(series_ids)
        for (sid, vno), fpath in tdms_map.items():
            if sid not in series_ids_set:
                continue
            if (sid, vno) not in known_keys:
                sname = series_map.get(sid, f"Serie {sid}")
                rows.append(TrialRow(
                    series_id=sid, series_name=sname,
                    trial_no=vno, trial_id=None,
                    tdms_path=fpath, status="⚠️ no trial",
                ))

        rows.sort(key=lambda r: (r.series_id, r.trial_no))
        return rows

    @staticmethod
    def scan(series_filter: Optional[int] = None) -> List[TrialRow]:
        """Scannt alle TDMS-Dateien im Ordner (optional gefiltert nach einer Serie)."""
        """
        Rückwärtskompatible Einzelserie-Variante.
        Delegiert intern an scan_multi.
        """
        if series_filter is not None:
            return TDMSFolderScanner.scan_multi([series_filter])

        # Ohne Filter: alle Serien laden
        try:
            all_series = fetch_all(
                "SELECT ID FROM tblTrialSeries ORDER BY ID"
            )
            all_ids = [
                int(r.get("ID") if isinstance(r, dict) else r[0])
                for r in all_series
            ]
        except Exception:
            all_ids = []
        return TDMSFolderScanner.scan_multi(all_ids)


# ---------------------------------------------------------------------------
# Analyse-Worker (QRunnable)
# ---------------------------------------------------------------------------
class _WorkerSignals(QObject):
    """Qt-Signale für den Analyse-Worker (progress, result, error)."""
    finished = Signal(int, dict, str)   # row_index, vals, error_msg


class _ScanSignals(QObject):
    """Qt-Signale für den Scan-Worker."""
    status  = Signal(str)              # Fortschritts-Meldung für _lbl_status
    done    = Signal(list)             # fertige List[TrialRow]
    error   = Signal(str)



class _ScanWorker(QRunnable):
    """Führt TDMSFolderScanner.scan_multi im Hintergrund aus.

    Schickt häufige Status-Signale damit der Nutzer Fortschritt sieht,
    auch wenn Netzlaufwerk oder DB-Query langsam sind.
    """

    def __init__(self, series_ids: List[int], load_db_vals: bool,
                 signals: "_ScanSignals"):
        super().__init__()
        self._series_ids   = series_ids
        self._load_db_vals = load_db_vals
        self._signals      = signals
        self.setAutoDelete(True)

    def run(self):
        try:
            sig = self._signals

            sig.status.emit("Scanning TDMS folder…")
            tdms_map = TDMSFolderScanner._build_tdms_map()
            n_files = len(tdms_map)
            sig.status.emit(f"TDMS folder read: {n_files} files found.")

            sig.status.emit("Loading series and trials from DB…")
            ph = ",".join(["?"] * len(self._series_ids))
            series_rows = []
            try:
                series_rows = fetch_all(
                    f"SELECT s.ID, s.SeriesName, e.[Experiment ID] AS ExpID "
                    f"FROM tblTrialSeries s "
                    f"LEFT JOIN tblExperimente e ON e.ID = s.ExperimentID "
                    f"WHERE s.ID IN ({ph})",
                    self._series_ids
                )
            except Exception:
                pass
            series_map: Dict[int, str] = {}
            for sr in series_rows:
                sid   = sr.get("ID")         if isinstance(sr, dict) else sr[0]
                sname = sr.get("SeriesName") if isinstance(sr, dict) else sr[1]
                exp   = sr.get("ExpID")      if isinstance(sr, dict) else sr[2]
                if sid is not None:
                    series_map[int(sid)] = f"{exp} | {sname}" if exp else str(sname)

            trial_rows = []
            try:
                trial_rows = fetch_all(
                    f"SELECT ID, TrialSeriesID, Versuchsnummer FROM tblTrial "
                    f"WHERE TrialSeriesID IN ({ph}) "
                    f"ORDER BY TrialSeriesID, Versuchsnummer",
                    self._series_ids
                )
            except Exception:
                pass
            n_trials = len(trial_rows)
            sig.status.emit(f"DB loaded: {n_trials} Trials.")

            trial_ids = [
                int(tr.get("ID") if isinstance(tr, dict) else tr[0])
                for tr in trial_rows
            ]

            saved_ids: set = set()
            saved_vals: dict = {}
            if trial_ids:
                sig.status.emit(
                    f"Loading saved results ({len(trial_ids)} Trials)…"
                )
                saved_ids, saved_vals = TDMSFolderScanner._fetch_saved(
                    trial_ids, fields_only=not self._load_db_vals
                )
                sig.status.emit(
                    f"Saved results loaded: {len(saved_ids)} already analysed."
                )

            # TrialRow-Objekte bauen
            rows: List[TrialRow] = []
            for tr in trial_rows:
                if isinstance(tr, dict):
                    tid = int(tr.get("ID") or 0)
                    sid = int(tr.get("TrialSeriesID") or 0)
                    vno = int(tr.get("Versuchsnummer") or 0)
                else:
                    tid, sid, vno = int(tr[0]), int(tr[1]), int(tr[2])

                sname = series_map.get(sid, str(sid))
                tdms  = tdms_map.get((sid, vno))

                if tid in saved_ids:
                    status = ST_SAVED
                elif tdms:
                    status = ST_PENDING
                else:
                    status = ST_NO_FILE

                rows.append(TrialRow(
                    series_id=sid,
                    series_name=sname,
                    trial_no=vno,
                    trial_id=tid,
                    tdms_path=tdms,
                    status=status,
                    db_vals=saved_vals.get(tid, {}),
                ))

            n_pend = sum(1 for r in rows if r.status == ST_PENDING)
            sig.status.emit(
                f"Scan finished: {len(rows)} Trials | "
                f"{len([r for r in rows if r.tdms_path])} with TDMS | "
                f"{n_pend} pending"
            )
            sig.done.emit(rows)

        except Exception as e:
            self._signals.error.emit(f"{e}\n{traceback.format_exc()[-400:]}")

class _AnalysisWorker(QRunnable):
    """Hintergrund-Worker für die DTY-Knoten-Analyse einer einzelnen TDMS-Datei.

    Läuft im QThreadPool. Emittiert result_ready wenn die Analyse abgeschlossen ist.
    """
    """Führt analyze_series für einen einzelnen Trial im Hintergrund aus."""

    def __init__(self, row_index: int, tdms_path: Path,
                 min_seg_pts: int, signals: _WorkerSignals, trial_id: "int | None" = None):
        super().__init__()
        self._idx        = row_index
        self._path       = tdms_path
        self._min_seg    = min_seg_pts
        self._signals    = signals
        self._trial_id   = trial_id
        self.setAutoDelete(True)

    def run(self):
        """Führt DTY-Analyse + Feature-Extraktion + ML-Predictions vollständig im Worker aus.

        Kein full_extract_vals im Main-Thread → kein UI-Freeze.
        """
        try:
            y     = read_dty_signal(str(self._path))
            dx_mm = read_step_mm_from_tdms(str(self._path))
            if y is None or len(y) == 0:
                self._signals.finished.emit(self._idx, {}, "No signal in the TDMS file.")
                return
            if dx_mm is None or dx_mm <= 0:
                dx_mm = 0.25  # Fallback

            y_arr = np.asarray(y, dtype=float)
            res   = analyze_series(y=y_arr, dx_mm=float(dx_mm), min_seg_pts=self._min_seg)

            # full_extract_vals hier im Worker – verhindert UI-Freeze im Main-Thread
            vals = full_extract_vals(res, y_arr, float(dx_mm), self._min_seg, trial_id=self._trial_id)
            self._signals.finished.emit(self._idx, vals, "")
        except Exception as e:
            self._signals.finished.emit(self._idx, {}, f"{e} | {traceback.format_exc()[-300:]}")


# ---------------------------------------------------------------------------
# DB-Speicher-Helfer (analog _save_values in DTYKnotsView, aber standalone)
# ---------------------------------------------------------------------------
def _save_analysis_to_db(trial_id: int, vals: Dict[str, Any]) -> bool:
    """Schreibt alle Analyse-Werte in tbllabordtyomat (UPDATE, sonst INSERT).

    Die DB-Logik liegt Qt-frei in ui/yarnscope/dty_service.save_analysis()
    (auch von der Web-Version benutzt); hier nur der angemeldete Benutzer.
    vals: extrahiertes Dict aus full_extract_vals(). True bei Erfolg.
    """
    return _dty_service.save_analysis(trial_id, vals, app_meta.current_user)


# ---------------------------------------------------------------------------
# Table Model
# ---------------------------------------------------------------------------
class _BatchTableModel(QAbstractTableModel):

    def __init__(self, rows: List[TrialRow], parent=None):
        super().__init__(parent)
        self._rows = rows

    def rowCount(self, parent=QModelIndex()):
        """Gibt die Anzahl Zeilen zurück."""
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        """Gibt die Anzahl Spalten zurück."""
        return len(_HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Gibt Spaltenheader zurück."""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return _HEADERS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        """Liefert Zelldaten: Farbkodierung je Status (grün=OK, rot=Fehler, grau=kein File)."""
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            return self._display(row, col)

        if role == Qt.ForegroundRole:
            return self._fg_color(row, col)

        if role == Qt.BackgroundRole:
            if row.status == ST_RUNNING:
                return QColor("#2a3a2a")
            if row.status == ST_ERROR:
                return QColor("#3a2020")

        if role == Qt.TextAlignmentRole:
            if col in (_COL_TRIAL_NO, _COL_TRIAL_ID) or col >= 5:
                return int(Qt.AlignRight | Qt.AlignVCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)

        if role == Qt.FontRole:
            if row.status == ST_SAVED:
                f = QFont(); f.setBold(True); return f

        return None

    def _display(self, row: TrialRow, col: int) -> str:
        """Gibt den anzuzeigenden String für eine Zelle zurück."""
        def _fmt(v, dec=1):
            return f"{v:.{dec}f}" if v is not None else ""

        if col == _COL_SERIES:   return row.series_name
        if col == _COL_TRIAL_NO: return str(row.trial_no)
        if col == _COL_TRIAL_ID: return str(row.trial_id) if row.trial_id else "?"
        if col == _COL_FILE:
            return row.tdms_path.name if row.tdms_path else "—"
        if col == _COL_STATUS:   return row.status
        # DB-Felder dynamisch
        if col >= 5:
            field = _DB_FIELDS[col - 5]
            v = row.db_vals.get(field)
            if v is None:
                return ""
            if isinstance(v, str):
                return v
            try:
                return f"{float(v):.2f}"
            except Exception:
                return str(v)
        return ""

    def _fg_color(self, row: TrialRow, col: int):
        """Gibt die Vordergrundfarbe für eine Zelle zurück (je nach Status)."""
        if row.status == ST_SAVED:    return QColor("#7ddf9a")
        if row.status == ST_ANALYZED: return QColor("#f0c040")
        if row.status == ST_ERROR:    return QColor("#ff6060")
        if row.status == ST_NO_FILE:  return QColor("#555")
        if row.status == "⚠️ no trial": return QColor("#f0a040")
        return QColor("#ddd")

    def update_row(self, idx: int):
        """Informiert die View dass sich Zeile idx geändert hat."""
        self.dataChanged.emit(
            self.index(idx, 0),
            self.index(idx, len(_HEADERS) - 1),
            [Qt.DisplayRole, Qt.ForegroundRole, Qt.BackgroundRole],
        )

    def set_rows(self, rows: List[TrialRow]):
        """Ersetzt alle Zeilen und triggert ein vollständiges Redraw."""
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def get_row(self, idx: int) -> TrialRow:
        """Gibt die TrialRow an Index idx zurück."""
        return self._rows[idx]

    def row_count_with_file(self) -> int:
        """Gibt die Anzahl Zeilen zurück die eine TDMS-Datei haben."""
        return sum(1 for r in self._rows if r.tdms_path is not None)

    def rows(self) -> List[TrialRow]:
        """Gibt alle TrialRows zurück."""
        return self._rows


# ---------------------------------------------------------------------------
# Haupt-Screen
# ---------------------------------------------------------------------------
class TDMSBatchScreen(QWidget):

    def __init__(self, on_back_home=None, parent=None,
                 locked_series_id: int = None,
                 locked_series_name: str = "",
                 sidebar_callbacks=None):
        super().__init__(parent)
        self._on_back_home       = on_back_home
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None
        self._locked_series_id   = locked_series_id
        self._locked_series_name = locked_series_name
        self._insider_mode       = False
        self._all_series: list   = []   # [(sid, label), ...]
        self._rows: List[TrialRow] = []
        self._model         = _BatchTableModel([])
        self._pool          = QThreadPool()
        # CPU-bound Workers: je 1 Thread pro CPU-Kern, max 8
        _n_threads = min(8, max(2, os.cpu_count() or 4))
        self._pool.setMaxThreadCount(_n_threads)
        self._running       = False
        self._pending_idxs: List[int] = []
        self._done_count    = 0
        self._save_after    = False
        self._build_ui()

    # ── UI-Aufbau ────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring).
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        # ── Shortcut Ctrl+Shift+J ─────────────────────────────────────────
        self._shortcut_insider = QShortcut(QKeySequence("Ctrl+Shift+J"), self)
        self._shortcut_insider.activated.connect(self._toggle_insider_mode)

        # ── Haupt-Splitter: Series-Liste links, Tabelle rechts ────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)

        # ── Linke Seite: Series-Liste ─────────────────────────────────────
        self._series_panel = QWidget()
        self._series_panel.setMaximumWidth(260)
        self._series_panel.setMinimumWidth(180)
        sp_layout = QVBoxLayout(self._series_panel)
        sp_layout.setContentsMargins(6, 6, 4, 4); sp_layout.setSpacing(4)

        self._lbl_series_title = QLabel("Serien")
        self._lbl_series_title.setStyleSheet(
            "font-weight:bold; color:#7ddf9a; font-size:13px;")
        sp_layout.addWidget(self._lbl_series_title)

        # Toggle Alle/Keine (nur im Insider-Modus sichtbar)
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

        # ── Rechte Seite: Filter + Tabelle ───────────────────────────────
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(4, 6, 8, 4); rv.setSpacing(4)

        # Filter-Zeile
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
        self._btn_scan.setObjectName("GreenBtn"); self._btn_scan.setFixedHeight(28)
        self._btn_scan.clicked.connect(self._on_scan)
        frow.addWidget(self._btn_scan)
        rv.addLayout(frow)

        # Tabelle
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setSortingEnabled(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setDefaultSectionSize(24)
        # Alle Spalten: ResizeToContents, horizontales Scrollen
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(_COL_FILE, QHeaderView.Interactive)
        hdr.setMinimumSectionSize(45)
        self._table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._table.setColumnWidth(_COL_SERIES, 640)
        self._table.setColumnWidth(_COL_FILE,   220)
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
            QTableView::item:selected { background: #39A650; color: #fff; }
        """)
        rv.addWidget(self._table, 1)
        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)

        # Aktions-Zeile
        brow = QHBoxLayout(); brow.setSpacing(8)
        self._lbl_status = QLabel("Bereit.")
        self._lbl_status.setStyleSheet("color:#aaa; font-size:12px;")
        brow.addWidget(self._lbl_status)
        self._progress = QProgressBar()
        self._progress.setVisible(False); self._progress.setFixedHeight(16)
        self._progress.setStyleSheet(
            "QProgressBar{background:#222;border-radius:4px;}"
            "QProgressBar::chunk{background:#39A650;border-radius:4px;}")
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
            "QPushButton{background:#39A650;color:#fff;border-radius:4px;"
            "font-size:13px;font-weight:bold;border:2px solid #5df472;padding:0 12px;}"
            "QPushButton:hover{background:#4ab862;}"
            "QPushButton:disabled{background:#2a3a2a;color:#555;border-color:#333;}")
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
        self._btn_stop.setFixedHeight(30); self._btn_stop.setVisible(False)
        self._btn_stop.clicked.connect(self._on_stop)
        brow.addWidget(self._btn_stop)
        rv.addLayout(brow)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0); splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 900])

        body = QWidget()
        bl = QVBoxLayout(body); bl.setContentsMargins(0,0,0,0)

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
        """Lädt alle verfügbaren TrialSeries aus der DB für die Auswahlliste."""
        """Lädt alle Serien aus DB in self._all_series."""
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
            sid   = r.get("ID")   or (r[0] if isinstance(r,(list,tuple)) else None)
            sname = r.get("SeriesName") or (r[1] if isinstance(r,(list,tuple)) else "")
            exp   = r.get("ExpID") or (r[2] if isinstance(r,(list,tuple)) else "")
            label = f"{exp} | {sname}" if exp else str(sname)
            if sid is not None:
                self._all_series.append((int(sid), label))

    def _rebuild_series_list_widget(self):
        """Aktualisiert das Serien-Auswahl-Widget nach einer Filteränderung."""
        """Füllt die QListWidget mit den sichtbaren Serien + Checkboxen."""
        self._series_list.clear()

        if self._insider_mode:
            series_to_show = self._all_series
        else:
            # Nur locked series
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
                "QCheckBox::indicator:checked { background:#39A650; border:1px solid #5df; border-radius:2px; }"
                "QCheckBox::indicator:unchecked { background:#333; border:1px solid #666; border-radius:2px; }")
            # Serien-Auswahl: nur lokaler Filter, kein DB-Scan
            chk.stateChanged.connect(self._refresh_series_filter)
            self._series_list.setItemWidget(item, chk)
            item.setSizeHint(chk.sizeHint())

    def _checked_series_ids(self) -> List[int]:
        """Gibt die IDs aller angehakten Serien zurück."""
        """Gibt Liste aller angehakten Series-IDs zurück."""
        result = []
        for i in range(self._series_list.count()):
            item = self._series_list.item(i)
            chk  = self._series_list.itemWidget(item)
            sid  = item.data(Qt.UserRole)
            if sid is None:
                continue
            # itemWidget kann None sein wenn noch nicht gerendert → Fallback: angehakt
            if chk is None or chk.isChecked():
                result.append(int(sid))
        return result

    def _toggle_all_series(self):
        """Hakt alle Serien an oder ab (Toggle)."""
        """Alle/Keine Serien anwählen."""
        # Prüfen ob alle angehakt
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
        """Schaltet den Insider-Modus um (zeigt erweiterte Analyse-Optionen)."""
        self._insider_mode = not self._insider_mode
        self._btn_toggle_all.setVisible(self._insider_mode)
        self._rebuild_series_list_widget()
        if self._insider_mode:
            self._lbl_status.setText("🔓 Insider mode – all series visible (scan to load)")
        else:
            self._lbl_status.setText("Bereit.")
            # Zurück zur locked series: neu scannen mit DB-Vals
            QTimer.singleShot(50, self._on_scan)

    # ── Init ──────────────────────────────────────────────────────────────

    def _init_series_state(self):
        self._load_series_list()
        self._rebuild_series_list_widget()
        QTimer.singleShot(100, self._on_scan)

    # ── Scan ──────────────────────────────────────────────────────────────


    def _selected_source_rows(self) -> list:
        """Gibt die Indizes in self._rows der selektierten Proxy-Zeilen zurück."""
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            return []
        result = []
        for proxy_idx in indexes:
            source_idx = self._proxy.mapToSource(proxy_idx)
            result.append(source_idx.row())
        return sorted(set(result))

    def _on_selection_changed(self):
        """Aktualisiert den Batch-Button-Text je nach Selektion."""
        sel = self._selected_source_rows()
        if sel:
            n = len(sel)
            self._btn_batch.setText(f"⚡ {n} analyse selected")
        else:
            self._btn_batch.setText("⚡ Start batch")

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

        load_db_vals = not self._insider_mode
        sigs = _ScanSignals()
        sigs.status.connect(self._lbl_status.setText)
        sigs.done.connect(self._on_scan_done)
        sigs.error.connect(self._on_scan_error)
        worker = _ScanWorker(checked, load_db_vals, sigs)
        self._pool.start(worker)

    def _on_scan_done(self, rows: list):
        self._rows = rows
        self._model.set_rows(self._rows)
        self._refresh_proxy()
        n_files = sum(1 for r in rows if r.tdms_path)
        n_pend  = sum(1 for r in rows if r.status == ST_PENDING)
        mode_hint = " (status only)" if self._insider_mode else ""
        self._lbl_status.setText(
            f"{len(rows)} Trials | {n_files} with TDMS | {n_pend} pending{mode_hint}")
        self._btn_scan.setEnabled(True)
        self._btn_batch.setEnabled(n_files > 0)
        # Auswahl-Button: aktiviert sobald Daten geladen sind
        self._btn_sel.setEnabled(n_files > 0)
        # Selektion-Änderung überwachen
        try:
            self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        except Exception:
            pass

    def _on_scan_error(self, msg: str):
        self._btn_scan.setEnabled(True)
        self._btn_batch.setEnabled(False)
        QMessageBox.critical(self, "Scan error", msg)

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
        """Filtert self._rows nach angehakten Serien – kein DB-Zugriff, sofort."""
        checked = set(self._checked_series_ids())
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

    # ── Analyse ───────────────────────────────────────────────────────────

    # _on_batch replaced by new version above

    def _on_retry_errors(self):
        """Wiederholt alle fehlgeschlagenen Trials."""
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
        # Wichtig: _model.rows() verwenden (gefilterte Ansicht),
        # damit die Indices aus _selected_source_rows() und pending_override stimmen.
        target_rows = self._model.rows()

        # Selektierte Zeilen haben Vorrang
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
            statuses = {}
            for r in target_rows:
                statuses[r.status] = statuses.get(r.status, 0) + 1
            QMessageBox.information(self, "Batch",
                f"No trials to process found.\n\n"
                f"Tip: switch off 'Only pending' to analyse saved ones again.\n\n"
                f"Status distribution:\n"
                + "\n".join(f"  '{k}': {v}" for k, v in sorted(statuses.items())))
            return

        self._running = True
        self._btn_batch.setEnabled(False)
        self._btn_retry.setVisible(False)
        self._btn_stop.setVisible(True)
        self._progress.setMaximum(len(pending))
        self._progress.setValue(0)
        self._progress.setVisible(True)

        # Modelle vorwärmen (einmalig, lokal – kein Netzwerkzugriff)
        try:
            run_stab_models({})
        except Exception:
            pass

        ok = 0
        errors = 0
        for step, idx in enumerate(pending, 1):
            if not self._running:  # Stop-Button
                break
            row = target_rows[idx]
            row.status = ST_RUNNING

            # Tabelle + Status + Progressbar sofort aktualisieren
            display_rows = self._model.rows()
            for di, dr in enumerate(display_rows):
                if dr is row:
                    self._model.update_row(di)
                    break
            self._progress.setValue(step - 1)
            self._lbl_status.setText(
                f"Analysiere {step}/{len(pending)}: {row.tdms_path.name}"
            )
            QApplication.processEvents()

            # Analyse + Speichern
            try:
                y     = read_dty_signal(str(row.tdms_path))
                dx_mm = read_step_mm_from_tdms(str(row.tdms_path))
                if y is None or len(y) == 0:
                    raise ValueError("No signal in the TDMS file.")
                if dx_mm is None or dx_mm <= 0:
                    dx_mm = 0.25

                y_arr = np.asarray(y, dtype=float)
                res   = analyze_series(y=y_arr, dx_mm=float(dx_mm), min_seg_pts=DEFAULT_MIN_SEG_PTS)
                vals  = full_extract_vals(
                    res, y_arr, float(dx_mm), DEFAULT_MIN_SEG_PTS, trial_id=row.trial_id,
                    progress_cb=lambda msg: (self._lbl_status.setText(msg), QApplication.processEvents()))

                row.result  = vals
                row.db_vals = {f: vals.get(f) for f in _DB_FIELDS}

                if self._save_after and row.trial_id is not None:
                    saved_ok = _save_analysis_to_db(row.trial_id, vals)
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
                print(f"[DTY Batch] Fehler idx={idx} trial={row.trial_id}: {e}")

            # Zeile aktualisieren
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
            + (f" | ❌ {errors} errors" if errors else "")
        )

    def _on_stop(self):
        self._running = False
        self._btn_stop.setVisible(False)
        self._btn_batch.setEnabled(True)
        self._lbl_status.setText("Gestoppt.")
        self._progress.setVisible(False)


    def _on_selection_changed(self):
        n = len(self._table.selectionModel().selectedRows())
        if n > 0:
            self._btn_sel.setText(f"☑ Selection ({n})")
            self._btn_sel.setEnabled(True)
        else:
            self._btn_sel.setText("☑ Selection only")

    def _on_batch(self):
        self._save_after = True
        self._start_batch(pending_override=None)

    def _on_batch_selection(self):
        """Batch nur für markierte Zeilen."""
        sel_rows = self._table.selectionModel().selectedRows()
        if not sel_rows:
            return
        # Proxy-Index → Source-Index → self._rows-Index
        pending = []
        for proxy_idx in sel_rows:
            source_idx = self._proxy.mapToSource(proxy_idx)
            row_obj = self._model.get_row(source_idx.row())
            if row_obj is None or row_obj.tdms_path is None:
                continue
            # find index in self._rows
            for i, r in enumerate(self._rows):
                if r is row_obj:
                    pending.append(i)
                    break
        if not pending:
            QMessageBox.information(self, "Selection", "None of the selected rows has a TDMS file.")
            return
        self._save_after = True
        self._start_batch(pending_override=pending)

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