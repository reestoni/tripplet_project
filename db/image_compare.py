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
    if row.get("_local") or row.get("_is_db_pdf"):
        return str(row.get("FullPath") or "")
    rel = str(row.get("RelativePath") or "")
    stored = str(row.get("StoredFilename") or "")
    return os.path.join(rel, stored) if rel else stored


# ── Canvas (ui/screen_canvas.py): series with images OR PDFs, and their PDFs ──
def fetch_canvas_series_groups() -> List[Dict[str, Any]]:
    """Series with images or PDFs: TrialSeriesID, SeriesName, ExperimentID, has_images, has_pdfs."""
    from db.connection import get_connection
    rows: List[Dict[str, Any]] = []
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute("SELECT DISTINCT TrialSeriesID FROM tblTrialSeriesImage")
            ids_imgs = {r[0] for r in (cur.fetchall() or [])}
            try:
                cur.execute("SELECT DISTINCT TrialSeriesID FROM tblTrialSeriesPDF")
                ids_pdfs = {r[0] for r in (cur.fetchall() or [])}
            except Exception:
                ids_pdfs = set()
            all_ids = ids_imgs | ids_pdfs
            if not all_ids:
                return rows
            placeholders = ",".join("?" * len(all_ids))
            cur.execute(
                f"SELECT s.ID AS TrialSeriesID, s.SeriesName, e.[Experiment ID] AS ExperimentID "
                f"FROM tblTrialSeries s LEFT JOIN tblExperimente e ON e.ID = s.ExperimentID "
                f"WHERE s.ID IN ({placeholders}) ORDER BY e.[Experiment ID] DESC, s.SeriesName",
                list(all_ids))
            cols = [d[0] for d in (cur.description or [])]
            for row in cur.fetchall() or []:
                d = dict(zip(cols, row))
                d["has_images"] = d["TrialSeriesID"] in ids_imgs
                d["has_pdfs"] = d["TrialSeriesID"] in ids_pdfs
                rows.append(d)
    except Exception:
        pass
    return rows


def fetch_pdfs_for_series(series_id: int) -> List[Dict[str, Any]]:
    """The PDFs of one series (tblTrialSeriesPDF) with FullPath and _is_db_pdf."""
    from db.connection import get_connection
    rows: List[Dict[str, Any]] = []
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute("SELECT ID, TrialSeriesID, RelativePath, StoredFilename, OriginalFilename "
                        "FROM tblTrialSeriesPDF WHERE TrialSeriesID = ? ORDER BY ID", (series_id,))
            cols = [d[0] for d in (cur.description or [])]
            for row in cur.fetchall() or []:
                r = dict(zip(cols, row))
                rel, stor = str(r.get("RelativePath") or ""), str(r.get("StoredFilename") or "")
                r["FullPath"] = os.path.join(rel, stor) if rel else stor
                r["_is_db_pdf"] = True
                rows.append(r)
    except Exception:
        pass
    return rows

