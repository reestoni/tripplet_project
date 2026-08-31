"""
recalc_all_tdms.py
===================
Rechnet ALLE TDMS-Dateien in einem Ordner neu (ausserhalb TrippleT) und
schreibt die Ergebnisse (Knotenwerte, Fallhoehen, Winkelsegmente,
Stab-Vorhersagen usw.) zurueck nach tbllabordtyomat - exakt dieselbe
Logik wie TrippleTs eingebaute Batch-Verarbeitung (screen_tdms_batch.py),
nur ohne GUI.

Voraussetzungen:
  - Im TrippleT-Projektordner ausfuehren (bzw. den Pfad unten anpassen),
    damit `db` und `ui.yarnscope` importierbar sind.
  - Im selben venv wie TrippleT (braucht dieselben Pakete: scikit-learn,
    xgboost, lightgbm, pandas, numpy, joblib, nptdms).
  - Dateinamen-Konvention wie von TrippleT erwartet: die TDMS-Datei muss
    <SeriesID>_<Versuchsnummer>... im Namen tragen (zwei durch "_"
    getrennte Zahlengruppen), z.B. "1234_12_irgendwas.tdms".

Nutzung:
    python recalc_all_tdms.py --folder "H:\\Technik\\TrippleT\\YarnScopeTDMS"
    python recalc_all_tdms.py --folder "..." --dry-run        (nur anzeigen, nichts speichern)
    python recalc_all_tdms.py --folder "..." --user-id 3      (UserID fuer die DB-Eintraege)
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# TrippleT-Projektordner ins sys.path (falls das Skript woanders liegt als
# neben main.py - Pfad ggf. anpassen).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from db.connection import fetch_all, execute  # noqa: E402
from ui.yarnscope.dty_tdms_reader import read_dty_signal, read_step_mm_from_tdms  # noqa: E402
from ui.yarnscope.dty_analysis import analyze_series, full_extract_vals  # noqa: E402

DEFAULT_MIN_SEG_PTS = 3


def parse_ids_from_filename(stem: str):
    """Extrahiert (SeriesID, Versuchsnummer) aus dem Dateinamen.

    Gleiche Logik wie TDMSFolderScanner._parse_ids in TrippleT
    (ui/screen_tdms_batch.py) - MUSS synchron bleiben, falls sich dort
    mal was aendert.
    """
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


def find_trial_id(series_id: int, versuchsnummer: int):
    rows = fetch_all(
        "SELECT ID FROM tblTrial WHERE TrialSeriesID = ? AND Versuchsnummer = ?",
        [series_id, versuchsnummer],
    )
    return int(rows[0]["ID"]) if rows else None


# Gleiche Spaltenliste wie in screen_tdms_batch.py::_save_analysis_to_db -
# MUSS synchron bleiben, falls sich dort mal was aendert.
_DB_COLS = (
    "FPm, CV_FP, AvgFP, StdDevFP, "
    "CV_KL, AvgKL, StdDevKL, "
    "CV_OL, AvgOL, StdDevOL, maxOL, maxKL, "
    "kl_bin_1,kl_bin_2,kl_bin_3,kl_bin_4,kl_bin_5,"
    "kl_bin_6,kl_bin_7,kl_bin_8,kl_bin_9,kl_bin_10,"
    "ol_bin_1,ol_bin_2,ol_bin_3,ol_bin_4,ol_bin_5,"
    "ol_bin_6,ol_bin_7,ol_bin_8,ol_bin_9,ol_bin_10,"
    "AKnots, BKnots, CKnots,"
    "a_knots,b_knots,c_knots,d_knots,e_knots,f_knots,g_knots,h_knots,i_knots,j_knots,"
    "k_knots,l_knots,m_knots,n_knots,o_knots,p_knots,q_knots,r_knots,s_knots,t_knots,"
    "[Fallhöhe1],[Fallhöhe2],[Fallhöhe3],[Fallhöhe4],[Fallhöhe5],"
    "[Fallhöhe6],[Fallhöhe7],[Fallhöhe8],[Fallhöhe9],[Fallhöhe10],"
    "[Winkelsegment1],[Winkelsegment2],[Winkelsegment3],[Winkelsegment4],[Winkelsegment5],"
    "[Winkelsegment6],[Winkelsegment7],[Winkelsegment8],[Winkelsegment9],[Winkelsegment10],"
    "Stab_03, Stab_06, Stab_10, Stab_13,"
    "Stab_03_model, Stab_06_model, Stab_10_model, Stab_13_model,"
    "SkewKL, SkewOL, RapportCV, RapportCVLocal,"
    "ka_bin_1,ka_bin_2,ka_bin_3,ka_bin_4,ka_bin_5,ka_bin_6,ka_bin_7,ka_bin_8,ka_bin_9,ka_bin_10,"
    "ka_bin_11,ka_bin_12,ka_bin_13,ka_bin_14,ka_bin_15,ka_bin_16,ka_bin_17,ka_bin_18,ka_bin_19,ka_bin_20,"
    "oa_bin_1,oa_bin_2,oa_bin_3,oa_bin_4,oa_bin_5,oa_bin_6,oa_bin_7,oa_bin_8,oa_bin_9,oa_bin_10,"
    "oa_bin_11,oa_bin_12,oa_bin_13,oa_bin_14,oa_bin_15,oa_bin_16,oa_bin_17,oa_bin_18,oa_bin_19,oa_bin_20,"
    "KL_AC1, KL_AC2, KL_AC3, KL_TailRatio, OL_TailRatio, KA_OA_Ratio,"
    "KL_AsymMean, KL_AsymCV, KurtKL, KurtOL, ThicknessDrift,"
    "SpectralEnergyLow, SpectralEnergyMid, SpectralEnergyHigh,"
    "CKnot_ClusterMean, CKnot_ClusterMax, UserID, Timestamp"
)


def save_to_db(trial_id: int, vals: dict, user_id: int) -> None:
    def _v(key):
        v = vals.get(key)
        try:
            return float(v) if v is not None else None
        except Exception:
            return None

    def _s(key):
        v = vals.get(key)
        return str(v) if v is not None else None

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    params = [
        _v("FPm"), _v("CV_FP"), _v("AvgFP"), _v("StdDevFP"),
        _v("CV_KL"), _v("AvgKL"), _v("StdDevKL"),
        _v("CV_OL"), _v("AvgOL"), _v("StdDevOL"),
        _v("maxOL"), _v("maxKL"),
        *[_v(f"kl_bin_{i+1}") for i in range(10)],
        *[_v(f"ol_bin_{i+1}") for i in range(10)],
        _v("AKnots"), _v("BKnots"), _v("CKnots"),
        *[_v(f"{c}_knots") for c in "abcdefghijklmnopqrst"],
        *[_v(f"Fallhöhe{i+1}") for i in range(10)],
        *[_v(f"Winkelsegment{i+1}") for i in range(10)],
        _v("Stab_03"), _v("Stab_06"), _v("Stab_10"), _v("Stab_13"),
        _s("Stab_03_model"), _s("Stab_06_model"),
        _s("Stab_10_model"), _s("Stab_13_model"),
        _v("SkewKL"), _v("SkewOL"), _v("RapportCV"), _v("RapportCVLocal"),
        *[_v(f"ka_bin_{i+1}") for i in range(20)],
        *[_v(f"oa_bin_{i+1}") for i in range(20)],
        _v("KL_AC1"), _v("KL_AC2"), _v("KL_AC3"),
        _v("KL_TailRatio"), _v("OL_TailRatio"), _v("KA_OA_Ratio"),
        _v("KL_AsymMean"), _v("KL_AsymCV"),
        _v("KurtKL"), _v("KurtOL"), _v("ThicknessDrift"),
        _v("SpectralEnergyLow"), _v("SpectralEnergyMid"), _v("SpectralEnergyHigh"),
        _v("CKnot_ClusterMean"), _v("CKnot_ClusterMax"),
        int(user_id) if user_id is not None else None,
        ts,
    ]
    col_list = [c.strip() for c in _DB_COLS.split(",") if c.strip()]

    rows = fetch_all("SELECT 1 FROM tbllabordtyomat WHERE TrialID = ?", [trial_id])
    exists = bool(rows)

    if exists:
        set_parts = [f"{c}=?" for c in col_list]
        sql = f"UPDATE tbllabordtyomat SET {', '.join(set_parts)} WHERE TrialID=?"
        execute(sql, params + [trial_id])
    else:
        cols_str = ", ".join(col_list)
        qm = ",".join(["?"] * len(params))
        sql = f"INSERT INTO tbllabordtyomat (TrialID, {cols_str}) VALUES (?, {qm})"
        execute(sql, [trial_id] + params)


def main():
    parser = argparse.ArgumentParser(
        description="Alle TDMS-Dateien in einem Ordner neu berechnen (ausserhalb TrippleT).")
    parser.add_argument("--folder", required=True, help="Ordner mit den TDMS-Dateien")
    parser.add_argument("--user-id", type=int, default=None,
                         help="UserID fuer die DB-Eintraege (siehe tbluser.ID). "
                              "Ohne Angabe wird NULL geschrieben.")
    parser.add_argument("--dry-run", action="store_true",
                         help="Nur berechnen und anzeigen, nichts in die DB schreiben")
    parser.add_argument("--min-seg-pts", type=int, default=DEFAULT_MIN_SEG_PTS)
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists():
        print(f"Ordner nicht gefunden: {folder}", flush=True)
        sys.exit(1)

    import numpy as np

    tdms_files = sorted(folder.glob("*.tdms"))
    print(f"{len(tdms_files)} TDMS-Dateien gefunden in {folder}", flush=True)
    if args.dry_run:
        print("(--dry-run: es wird NICHTS in die DB geschrieben)", flush=True)

    ok, skipped, errors = 0, 0, 0
    for i, f in enumerate(tdms_files, 1):
        prefix = f"[{i}/{len(tdms_files)}] {f.name}:"

        ids = parse_ids_from_filename(f.stem)
        if not ids:
            print(f"{prefix} Dateiname nicht erkannt "
                  f"(erwarte <SeriesID>_<Versuchsnummer>... im Namen) - übersprungen.", flush=True)
            skipped += 1
            continue
        series_id, vno = ids

        trial_id = find_trial_id(series_id, vno)
        if trial_id is None:
            print(f"{prefix} Kein Trial gefunden für Series {series_id} / V{vno} - übersprungen.", flush=True)
            skipped += 1
            continue

        try:
            y = read_dty_signal(str(f))
            dx_mm = read_step_mm_from_tdms(str(f))
            if y is None or len(y) == 0:
                print(f"{prefix} Kein Signal im File - übersprungen.", flush=True)
                skipped += 1
                continue
            if dx_mm is None or dx_mm <= 0:
                dx_mm = 0.25

            y_arr = np.asarray(y, dtype=float)
            res = analyze_series(y=y_arr, dx_mm=float(dx_mm), min_seg_pts=args.min_seg_pts)
            vals = full_extract_vals(res, y_arr, float(dx_mm), args.min_seg_pts, trial_id=trial_id)

            print(f"{prefix} Trial {trial_id} (Series {series_id}, V{vno}) — "
                  f"FPm={vals.get('FPm')}, "
                  f"Stab_03={vals.get('Stab_03')}, Stab_06={vals.get('Stab_06')}, "
                  f"Stab_10={vals.get('Stab_10')}, Stab_13={vals.get('Stab_13')}", flush=True)

            if not args.dry_run:
                save_to_db(trial_id, vals, args.user_id)
            ok += 1
        except Exception as e:
            print(f"{prefix} FEHLER — {e}", flush=True)
            errors += 1

    print(f"\nFertig: {ok} erfolgreich, {skipped} übersprungen, {errors} Fehler.", flush=True)


if __name__ == "__main__":
    main()