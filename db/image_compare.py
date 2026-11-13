"""image_compare.py - the database part of Image Compare (ui/screen_image_compare.py), without Qt
(2026-11-13, moved out of the screen for the web version).

Series with images (tblTrialSeriesImage), the images of a series, and the ATY radar of a Garnspiegel photo
(file name "V<n>…" -> trial -> its saved tblLaborATYoMat analysis -> radar scores)."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


def fetch_series_groups() -> List[Dict[str, Any]]:
    """All series that have images: TrialSeriesID, SeriesName, ExperimentID."""
    from db.connection import get_connection
    rows: List[Dict[str, Any]] = []
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(
                "SELECT DISTINCT s.ID AS TrialSeriesID, s.SeriesName, e.[Experiment ID] AS ExperimentID "
                "FROM tblTrialSeries s "
                "INNER JOIN tblTrialSeriesImage i ON i.TrialSeriesID = s.ID "
                "LEFT JOIN tblExperimente e ON e.ID = s.ExperimentID "
                "ORDER BY e.[Experiment ID] DESC, s.SeriesName"
            )
            cols = [d[0] for d in (cur.description or [])]
            for row in cur.fetchall() or []:
                rows.append(dict(zip(cols, row)))
    except Exception:
        pass
    return rows


def fetch_images_for_series(series_id: int) -> List[Dict[str, Any]]:
    """The images of one series (tblTrialSeriesImage)."""
    from db.connection import get_connection
    rows: List[Dict[str, Any]] = []
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(
                "SELECT ID, TrialSeriesID, RelativePath, StoredFilename, OriginalFilename "
                "FROM tblTrialSeriesImage WHERE TrialSeriesID = ? ORDER BY ID",
                (series_id,),
            )
            cols = [d[0] for d in (cur.description or [])]
            for row in cur.fetchall() or []:
                rows.append(dict(zip(cols, row)))
    except Exception:
        pass
    return rows


def fetch_aty_radar_for_image(meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """ATY radar scores of the trial a Garnspiegel photo was taken for, or None.

    Chain: OriginalFilename "V<n>..." (ui/yarnscope/garnspiegel_analysis.parse_versuchsnummer) -> Versuchsnummer
    -> tblTrial row of that TrialSeriesID -> its saved tblLaborATYoMat row with real values -> radar scores
    (ui/yarnscope/aty_core_analysis.compute_radar_scores). None at any step that does not resolve."""
    if not isinstance(meta, dict) or meta.get("_local"):
        return None
    series_id = meta.get("TrialSeriesID")
    if not series_id:
        return None
    try:
        from db.connection import get_connection
        from ui.yarnscope.garnspiegel_analysis import parse_versuchsnummer
        vno = parse_versuchsnummer(meta.get("OriginalFilename") or "")
        if vno is None:
            return None
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute("SELECT ID FROM tblTrial WHERE TrialSeriesID = ? AND Versuchsnummer = ?", (series_id, vno))
            row = cur.fetchone()
            if not row:
                return None
            trial_id = row[0]
            cur.execute("SELECT * FROM tblLaborATYoMat WHERE TrialID = ? AND BulkIndexPct IS NOT NULL "
                        "ORDER BY Timestamp DESC", (trial_id,))
            cols = [d[0] for d in (cur.description or [])]
            data_row = cur.fetchone()
            if not data_row:
                return None
            row_dict = dict(zip(cols, data_row))
        from ui.yarnscope.aty_core_analysis import compute_radar_scores, from_db_row
        return {"vno": vno, "trial_id": trial_id, "scores": compute_radar_scores(from_db_row(row_dict))}
    except Exception:
        return None


def build_full_path(row: Dict[str, Any]) -> str:
    """Full path of an image row (RelativePath + StoredFilename; local files: FullPath)."""
    if row.get("_local"):
        return str(row.get("FullPath") or "")
    rel = str(row.get("RelativePath") or "")
    stored = str(row.get("StoredFilename") or "")
    return os.path.join(rel, stored) if rel else stored
