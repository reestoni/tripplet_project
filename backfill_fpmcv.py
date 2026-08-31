"""
backfill_fpmcv.py
==================
Rechnet FPmCV in tblLaborItematPlus fuer alle bestehenden Tension=0-Datensaetze
nach, denen es fehlt - Formel: sqrt(OLS^2 + KLS^2) / (OLX + KLX) * 100.

Hintergrund: ShowExperimentScreen._recompute_itemat_plus() (screen_show_experiment.py)
berechnete FPmCV beim Speichern im Itemat-Plus-Tab wegen falscher, nicht um die
Jet-Info-Kopfzeilen versetzter Row-Indizes seit geraumer Zeit nicht mehr korrekt
(siehe Fix dort). Dieses Skript holt die dadurch entstandene Luecke fuer bereits
gespeicherte Trials einmalig nach - der App-Fix deckt nur kuenftige Speichervorgaenge ab.

Nur Tension=0-Datensaetze werden angefasst, exakt wie im laufenden App-Code
(OLX/OLS/KLX/KLS werden dort ausschliesslich fuer diesen Datensatz gepflegt).

Voraussetzungen:
  - Im TrippleT-Projektordner ausfuehren, damit `db` importierbar ist.
  - TRIPPLET_MODE vorher setzen (Umgebungsvariable), z.B.:
        set TRIPPLET_MODE=dev_local && python backfill_fpmcv.py --dry-run

Nutzung:
    python backfill_fpmcv.py --dry-run     (nur anzeigen, nichts speichern)
    python backfill_fpmcv.py               (tatsaechlich schreiben)
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from db.connection import fetch_all, execute, MODE  # noqa: E402


def compute_fpmcv(olx, ols, klx, kls) -> float | None:
    if None in (olx, ols, klx, kls):
        return None
    denom = float(olx) + float(klx)
    if denom <= 0:
        return None
    return math.sqrt(float(kls) ** 2 + float(ols) ** 2) / denom * 100


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                         help="Nur anzeigen, nichts in die DB schreiben")
    args = parser.parse_args()

    print(f"TRIPPLET_MODE = {MODE}", flush=True)
    if args.dry_run:
        print("(--dry-run: es wird NICHTS in die DB geschrieben)", flush=True)

    rows = fetch_all(
        "SELECT ID, TrialID, [OL X (mm)] AS OLX, [OL S (mm)] AS OLS, "
        "[KL X (mm)] AS KLX, [KL S (mm)] AS KLS "
        "FROM tblLaborItematPlus "
        "WHERE FPmCV IS NULL AND [Tension (cN/dtex)] = 0",
        [],
    )
    print(f"{len(rows)} Datensaetze mit FPmCV=NULL bei Tension=0 gefunden.", flush=True)

    computed = 0
    skipped_missing_input = 0
    for r in rows:
        val = compute_fpmcv(r["OLX"], r["OLS"], r["KLX"], r["KLS"])
        if val is None:
            skipped_missing_input += 1
            continue
        val = round(val, 2)
        computed += 1
        print(f"  TrialID={r['TrialID']} ID={r['ID']}: "
              f"OLX={r['OLX']} OLS={r['OLS']} KLX={r['KLX']} KLS={r['KLS']} -> FPmCV={val}")
        if not args.dry_run:
            execute("UPDATE tblLaborItematPlus SET FPmCV = ? WHERE ID = ?", [val, r["ID"]])

    print(f"\nFertig: {computed} nachberechnet"
          + (" (nicht geschrieben, --dry-run)" if args.dry_run else " und geschrieben")
          + f", {skipped_missing_input} uebersprungen (OLX/OLS/KLX/KLS unvollstaendig, nicht berechenbar).")


if __name__ == "__main__":
    main()
