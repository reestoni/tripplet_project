"""
backfill_garnspiegel_analysis.py
=================================
Rechnet die Garnspiegel-Breiten-CV% (ui/yarnscope/garnspiegel_analysis.py)
fuer alle bestehenden tblTrialSeriesImage-Eintraege nach, die noch keine
Zeile in tblTrialSeriesImageAnalysis haben - deckt Fotos ab, die vor der
automatischen Analyse beim Upload (Hook in screen_show_experiment.py,
_analyze_and_save_garnspiegel) hochgeladen wurden.

Idempotent: ueberspringt Bilder, die (fuer die aktuelle ParamsVersion)
bereits eine Analyse-Zeile haben - sicher mehrfach ausfuehrbar, z.B. nach
einer Algorithmus-Aenderung mit neuer PARAMS_VERSION erneut laufen lassen.

Voraussetzungen:
  - Im TrippleT-Projektordner ausfuehren, damit `db`/`ui` importierbar sind.
  - TRIPPLET_MODE vorher setzen (Umgebungsvariable).
  - Netzwerkzugriff auf H:\Technik\TrippleT\TrialSeriesImages.

Nutzung:
    python backfill_garnspiegel_analysis.py --dry-run
    python backfill_garnspiegel_analysis.py
    python backfill_garnspiegel_analysis.py --user-id 3
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from db.connection import fetch_all, execute, new_global_id, MODE  # noqa: E402
from ui.yarnscope.garnspiegel_analysis import (  # noqa: E402
    analyze_image, to_db_row, PARAMS_VERSION, looks_like_garnspiegel_filename,
)

BASE_DIR = r"H:\Technik\TrippleT\TrialSeriesImages"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                         help="Nur anzeigen, nichts in die DB schreiben")
    parser.add_argument("--user-id", type=int, default=None,
                         help="UserID fuer die Backfill-Eintraege (Default: NULL)")
    args = parser.parse_args()

    print(f"TRIPPLET_MODE = {MODE}", flush=True)
    if args.dry_run:
        print("(--dry-run: es wird NICHTS in die DB geschrieben)", flush=True)
    print(f"ParamsVersion = {PARAMS_VERSION}", flush=True)

    all_rows = fetch_all(
        "SELECT img.ID, img.TrialSeriesID, img.RelativePath, img.StoredFilename, img.OriginalFilename "
        "FROM tblTrialSeriesImage img "
        "WHERE NOT EXISTS ("
        "  SELECT 1 FROM tblTrialSeriesImageAnalysis a "
        "  WHERE a.TrialSeriesImageID = img.ID AND a.ParamsVersion = ?"
        ") ORDER BY img.TrialSeriesID, img.ID",
        [PARAMS_VERSION],
    )
    # Nicht jedes Bild ist ein Garnspiegel (Defekt-/Setup-Fotos laufen ueber
    # denselben Upload-Dialog) - nur Dateien nach der bestehenden Labor-
    # Namenskonvention "V<n>.jpg" werden ueberhaupt versucht, gleiche Regel
    # wie im Upload-Hook (_analyze_and_save_garnspiegel).
    rows = [r for r in all_rows if looks_like_garnspiegel_filename(r["OriginalFilename"] or "")]
    n_skipped_not_garnspiegel = len(all_rows) - len(rows)
    print(f"{len(all_rows)} Bilder ohne Analyse fuer ParamsVersion={PARAMS_VERSION}, "
          f"davon {n_skipped_not_garnspiegel} nicht nach V<n>.jpg-Muster (uebersprungen, "
          f"kein Eintrag), {len(rows)} werden versucht", flush=True)

    def _exists_with_retry(p, attempts=3, delay=2.0):
        """A long unattended run over hundreds of network-share files can hit
        a transient H:\\ disconnect (seen in practice: several hundred
        consecutive false "file_missing" results that were actually fine
        moments later) - a bare os.path.exists() has no way to tell a real
        gap from a hiccup, so retry a few times before giving up."""
        for i in range(attempts):
            if os.path.exists(p):
                return True
            if i < attempts - 1:
                time.sleep(delay)
        return False

    t0 = time.time()
    n_ok, n_fail = 0, 0
    for idx, r in enumerate(rows):
        rel = r["RelativePath"] or ""
        stored = r["StoredFilename"] or ""
        path = os.path.join(rel, stored) if rel else os.path.join(BASE_DIR, str(r["TrialSeriesID"]), stored)
        if not _exists_with_retry(path):
            path = os.path.join(BASE_DIR, str(r["TrialSeriesID"]), stored)

        try:
            stats = analyze_image(path) if _exists_with_retry(path) else {
                "status": "file_missing", "orientation": None, "n_strands": 0,
                "mean_width_px": None, "std_width_px": None, "cv_pct": None,
            }
        except Exception as e:
            stats = {"status": f"error", "orientation": None, "n_strands": 0,
                      "mean_width_px": None, "std_width_px": None, "cv_pct": None}
            print(f"  error on {path}: {e}", flush=True)

        if stats["status"] == "ok":
            n_ok += 1
        else:
            n_fail += 1

        if not args.dry_run:
            db_row = to_db_row(stats)
            cols = ["TrialSeriesImageID", "GlobalID", "UserID", "Timestamp", "ParamsVersion"] + list(db_row.keys())
            vals = [r["ID"], new_global_id(), args.user_id, None, PARAMS_VERSION] + list(db_row.values())
            # Timestamp: use NOW() via the same helper pattern as everywhere else in the app
            placeholders = ",".join(["?" if c != "Timestamp" else "NOW()" for c in cols])
            vals_no_ts = [v for c, v in zip(cols, vals) if c != "Timestamp"]
            execute(
                f"INSERT INTO tblTrialSeriesImageAnalysis ({','.join(cols)}) VALUES ({placeholders})",
                vals_no_ts,
            )

        if (idx + 1) % 50 == 0:
            elapsed = time.time() - t0
            print(f"  {idx+1}/{len(rows)} processed ({n_ok} ok, {n_fail} fail), {elapsed:.0f}s elapsed", flush=True)

    print(f"\nDONE: {n_ok} ok, {n_fail} failed, total {len(rows)}"
          + (" (nicht geschrieben, --dry-run)" if args.dry_run else " und geschrieben"), flush=True)


if __name__ == "__main__":
    main()
