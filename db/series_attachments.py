"""series_attachments.py - images and PDFs attached to a trial series, without Qt.

Moved out of ui/screen_show_experiment.py (2026-11-13; _fetch_series_images /
_fetch_series_pdfs and the base folders) so that the desktop and the web app
(tripplet_web) list the same files. The files live in shared folders; the DB
holds RelativePath (= the folder) + StoredFilename.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from db.connection import get_connection, is_dev_mode

# Basisordner fuer TrialSeries-Bilder
# - PROD: Netzlaufwerk (gemeinsame Ablage)
# - DEV:  lokaler Testordner
TRIALSERIES_IMAGES_BASE_DIR = (
    r"C:\ttt\images\TrialSeriesImages" if is_dev_mode() else r"H:\\Technik\\TrippleT\\TrialSeriesImages"
)

# Basisordner fuer TrialSeries-PDFs
# - DEV + DEV_LOCAL: lokaler Testordner
# - PROD: Netzlaufwerk (gemeinsame Ablage)
TRIALSERIES_PDFS_BASE_DIR = (
    r"C:\ttt\pdfs" if is_dev_mode() else r"H:\\Technik\\TrippleT\\TrialSeriesPDF"
)


def _row(rid: Any, rel_path: Any, stored: Any, orig_name: Any, created_by: Any) -> Dict[str, Any]:
    rel_path = str(rel_path or "")
    stored = str(stored or "")
    orig_name = str(orig_name or "")
    full = os.path.join(rel_path, stored) if rel_path else stored
    return {"ID": rid, "RelativePath": rel_path, "StoredFilename": stored, "OriginalFilename": orig_name,
            "FullPath": full, "CreatedBy": created_by}


def list_images(series_id: Any) -> List[Dict[str, Any]]:
    """Images of the series, newest first: dicts with ID, RelativePath, StoredFilename,
    OriginalFilename, FullPath, CreatedBy."""
    if series_id in (None, ""):
        return []
    rows: List[Dict[str, Any]] = []
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            "SELECT [ID], [RelativePath], [StoredFilename], [OriginalFilename], [CreatedBy] "
            "FROM [tblTrialSeriesImage] "
            "WHERE [TrialSeriesID]=? "
            "ORDER BY [ID] DESC",
            [series_id],
        )
        for img_id, rel_path, stored, orig_name, created_by in cur.fetchall() or []:
            rows.append(_row(img_id, rel_path, stored, orig_name, created_by))
    return rows


def list_pdfs(series_id: Any) -> List[Dict[str, Any]]:
    """PDFs of the series, newest first (same dict keys as list_images)."""
    if series_id in (None, ""):
        return []
    rows: List[Dict[str, Any]] = []
    with get_connection() as cn:
        cur = cn.cursor()
        # Include ID for robust rename/delete, if present.
        try:
            cur.execute(
                "SELECT [ID],[RelativePath],[StoredFilename],[OriginalFilename],[CreatedBy] "
                "FROM [tblTrialSeriesPDF] "
                "WHERE [TrialSeriesID]=? "
                "ORDER BY [ID] DESC",
                [series_id],
            )
            for doc_id, rel_path, stored, orig_name, created_by in cur.fetchall() or []:
                rows.append(_row(doc_id, rel_path, stored, orig_name, created_by))
        except Exception:
            # Fallback if table lacks ID column in the select
            cur.execute(
                "SELECT [RelativePath],[StoredFilename],[OriginalFilename],[CreatedBy] "
                "FROM [tblTrialSeriesPDF] "
                "WHERE [TrialSeriesID]=? "
                "ORDER BY [OriginalFilename] DESC",
                [series_id],
            )
            for rel_path, stored, orig_name, created_by in cur.fetchall() or []:
                r = _row(None, rel_path, stored, orig_name, created_by)
                del r["ID"]   # the old fallback rows had no ID key
                rows.append(r)
    return rows


# folders a download may come from (the DB keeps absolute folders; copies of prod data on
# dev/dev_local still point to the share, so both variants are allowed)
DOWNLOAD_ROOTS = {
    "image": (r"C:\ttt\images\TrialSeriesImages", r"H:\Technik\TrippleT\TrialSeriesImages"),
    "pdf": (r"C:\ttt\pdfs", r"H:\Technik\TrippleT\TrialSeriesPDF"),
}


def _norm(path: str) -> str:
    return os.path.normcase(os.path.realpath(path.replace("\\\\", "\\")))


def file_for_download(kind: str, series_id: Any, attachment_id: Any) -> Optional[str]:
    """Path of one attachment of this series, only if it really lies in one of the
    attachment folders of its kind (web app: never serve arbitrary paths from the DB)."""
    if kind not in DOWNLOAD_ROOTS:
        return None
    rows = list_images(series_id) if kind == "image" else list_pdfs(series_id)
    roots = [_norm(r) for r in DOWNLOAD_ROOTS[kind]]
    for r in rows:
        if r.get("ID") is not None and str(r["ID"]) == str(attachment_id):
            full = _norm(r["FullPath"])
            if any(full.startswith(root + os.sep) for root in roots) and os.path.isfile(full):
                return full
            return None
    return None
