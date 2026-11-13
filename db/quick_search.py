# db/quick_search.py
"""Quick search (Ctrl+F) over all trial series by series name / experiment ID,
jet, yarn and machine - Qt-free, shared by the desktop dialog
(ui/screen_quick_search.py) and the web app. Moved unchanged 2026-11-13."""
from __future__ import annotations

from typing import Dict, List, Set

from db.connection import get_connection


def _terms(text: str) -> List[str]:
    """Tokenisiert den Suchtext in Einzelterme (lowercase, Leerzeichen-getrennt)."""
    """Split comma-separated input into stripped, non-empty terms."""
    return [t.strip() for t in text.split(",") if t.strip()]


def _search(jets: List[str], machines: List[str], series_names: List[str], yarns: List[str]) -> List[Dict]:
    """Führt die Datenbanksuche aus und gibt Treffer-Dicts zurück.

    Sucht gleichzeitig in Jet-, Maschinen-, Serien- und Garn-Feldern.
    Jede Zeile in tblTrialSeries × tblTrial × tblExperimente wird geprüft.

    Args:
        jets:         Suchbegriffe für Jet-Spalten.
        machines:     Suchbegriffe für Maschinen-Spalten.
        series_names: Suchbegriffe für Serien-Namen.
        yarns:        Suchbegriffe für Garn-Spalten.

    Returns:
        Liste von Dicts mit Keys: exp_pk, exp_id, series_pk, series_name, maschine, reason.
    """
    """
    Returns series that match ALL supplied filters (AND logic).
    Within each filter, multiple terms are also AND (series must contain all).
    """
    hits: Dict[int, Dict] = {}   # series_pk → result dict

    def _add(exp_pk, exp_id, series_pk, series_name, maschine, reason):
        spk = int(series_pk)
        if spk not in hits:
            hits[spk] = {
                "exp_pk":      exp_pk,
                "exp_id":      str(exp_id or ""),
                "series_pk":   spk,
                "series_name": str(series_name or ""),
                "maschine":    str(maschine or ""),
                "reasons":     [],
            }
        if reason and reason not in hits[spk]["reasons"]:
            hits[spk]["reasons"].append(reason)

    try:
        with get_connection() as cn:
            cur = cn.cursor()

            # --- Build candidate series from first available filter ---
            # Strategy: start with all series, then intersect per filter.

            # Step 1: get ALL series (we filter in Python for flexibility)
            cur.execute(
                "SELECT e.ID, e.[Experiment ID], s.ID, s.SeriesName, m.Maschine "
                "FROM (tblExperimente AS e "
                "INNER JOIN tblTrialSeries AS s ON s.ExperimentID = e.ID) "
                "LEFT JOIN tblMaschine AS m ON m.ID = s.MachineID "
                "ORDER BY e.[Experiment ID] DESC, s.ID"
            )
            all_series = {}
            for row in cur.fetchall() or []:
                spk = int(row[2])
                all_series[spk] = {
                    "exp_pk":      row[0],
                    "exp_id":      str(row[1] or ""),
                    "series_pk":   spk,
                    "series_name": str(row[3] or ""),
                    "maschine":    str(row[4] or ""),
                }

            # Step 2: build jet index  series_pk → set of jet names
            cur.execute(
                "SELECT t.TrialSeriesID, j.Jet "
                "FROM tblTrial AS t "
                "INNER JOIN tblDTYJets AS j ON j.ID = t.JetID"
            )
            jet_index: Dict[int, Set[str]] = {}
            for row in cur.fetchall() or []:
                spk = int(row[0])
                jet_index.setdefault(spk, set()).add(str(row[1] or "").lower())

            # Step 3: build yarn index  series_pk → set of yarn names
            cur.execute(
                "SELECT t.TrialSeriesID, y.Name "
                "FROM tbltrialsettings ts "
                "JOIN tbltrial t ON t.ID = ts.TrialID "
                "INNER JOIN tblYarn AS y ON y.ID = ts.YarnID "
                "WHERE ts.YarnID IS NOT NULL"
            )
            yarn_index: Dict[int, Set[str]] = {}
            for row in cur.fetchall() or []:
                spk = int(row[0])
                yarn_index.setdefault(spk, set()).add(str(row[1] or "").lower())

    except Exception:
        return []

    # --- Filter in Python (AND across filters, AND within multi-term) ---
    result = []
    for spk, s in all_series.items():
        reasons = []
        skip = False

        # Filter: Series name (all terms must appear in series name OR experiment ID)
        if series_names:
            combined = (s["series_name"] + " " + s["exp_id"]).lower()
            if not all(t.lower() in combined for t in series_names):
                skip = True
            else:
                reasons.append("Series: " + ", ".join(series_names))

        if skip:
            continue

        # Filter: Machine (all terms must appear in machine name)
        if machines:
            if not all(m.lower() in s["maschine"].lower() for m in machines):
                skip = True
            else:
                reasons.append("Machine: " + ", ".join(machines))

        if skip:
            continue

        # Filter: Jets (ALL jet terms must be found among jets used in this series)
        if jets:
            jets_in_series = jet_index.get(spk, set())
            matched = []
            all_found = True
            for jet_term in jets:
                found = any(jet_term.lower() in j for j in jets_in_series)
                if not found:
                    all_found = False
                    break
                matched.append(jet_term)
            if not all_found:
                continue
            reasons.append("Jet: " + ", ".join(matched))

        # Filter: Yarns (ALL yarn terms must be found among yarns used in this series)
        if yarns:
            yarns_in_series = yarn_index.get(spk, set())
            matched_y = []
            all_found_y = True
            for yarn_term in yarns:
                found = any(yarn_term.lower() in y for y in yarns_in_series)
                if not found:
                    all_found_y = False
                    break
                matched_y.append(yarn_term)
            if not all_found_y:
                continue
            reasons.append("Yarn: " + ", ".join(matched_y))

        result.append({**s, "reasons": reasons})

    return result
