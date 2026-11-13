"""series_uploads.py - upload / rename / delete images and PDFs of a trial series, without Qt.

Moved out of ui/screen_show_experiment.py (2026-11-13; _upload_series_images /
_upload_series_pdfs, _insert_trialseries_image_row / _insert_trialseries_pdf_row,
_analyze_and_save_garnspiegel) so that the desktop and the web app (tripplet_web)
store attachments the same way. Desktop behaviour unchanged.

Storage (unchanged): the file is written under a random name (uuid hex + original
extension; PDFs without extension get ".pdf") into <base>\\<TrialSeriesID>\\, base =
db/series_attachments.TRIALSERIES_IMAGES_BASE_DIR / TRIALSERIES_PDFS_BASE_DIR (dev
modes: local C:\\ttt folders, prod: the H: share). tblTrialSeriesImage /
tblTrialSeriesPDF get TrialSeriesID, RelativePath (= that folder with trailing
backslash), StoredFilename, OriginalFilename, CreatedAt, CreatedBy. Images whose name
follows the lab convention "V<n>.jpg" are analysed right away (Garnspiegel width CV%,
tblTrialSeriesImageAnalysis, best-effort). One tblFeatureUsage row per upload batch
(FeatureID 4 = images, 3 = PDFs).

Rules (desktop): everybody may upload (also AccessLevel 1) and rename; delete only the
uploader (CreatedBy) or a superuser (AccessLevel >= 4) - db/experiment_request_images.can_delete.
"""
from __future__ import annotations

import datetime
import logging
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple

from db.connection import execute as _db_execute, get_connection, new_global_id, table_exists
from db import series_attachments as sa
from db import experiment_request_images as er_images

logger = logging.getLogger(__name__)

KINDS = ("image", "pdf")
TABLE = {"image": "tblTrialSeriesImage", "pdf": "tblTrialSeriesPDF"}
FK = "TrialSeriesID"
FEATURE_ID = {"image": 4, "pdf": 3}          # tblFeatureUsage.FeatureID (stealth tracking)
DEFAULT_EXT = {"image": "", "pdf": ".pdf"}   # extension when the original name has none

# Extensions offered by the desktop file picker (web uploads are additionally checked by content)
IMAGE_EXTENSIONS = er_images.IMAGE_EXTENSIONS
PDF_EXTENSIONS = (".pdf",)


def _base(kind: str) -> str:
    return sa.TRIALSERIES_IMAGES_BASE_DIR if kind == "image" else sa.TRIALSERIES_PDFS_BASE_DIR


# ---------------- paths ----------------

def series_dir(kind: str, series_id: Any) -> str:
    """Target folder for images / PDFs of a trial series."""
    return os.path.join(_base(kind), str(series_id))


def relative_path_for_db(kind: str, series_id: Any) -> str:
    """The folder as stored in RelativePath (trailing backslash)."""
    return _base(kind) + "\\" + str(series_id) + "\\"


def prepare_folder(kind: str, series_id: Any) -> str:
    """Creates the series folder; RuntimeError with an explanation if not possible."""
    target_dir = series_dir(kind, series_id)
    try:
        os.makedirs(target_dir, exist_ok=True)
    except PermissionError as e:
        raise RuntimeError(
            "[WinError 5] Access denied while creating the target folder. "
            "This is a permission problem on the share/NTFS.\n\n"
            f"Path: {target_dir}\n\n"
            "Please ensure that the Windows user (or the account running TrippleT) "
            f"has write permission on {_base(kind)}.\n\n"
            f"Original error: {e}"
        )
    except Exception as e:
        raise RuntimeError(f"Target folder could not be created: {target_dir}\n{e}")
    return target_dir


# ---------------- rows ----------------

def insert_row(kind: str, user_id: Any, *, series_id: Any, relative_path: str, stored_filename: str,
               original_filename: str) -> Optional[int]:
    """Adds the row in tblTrialSeriesImage / tblTrialSeriesPDF; returns the new ID."""
    if user_id in (None, ""):
        raise RuntimeError("CreatedBy/UserID could not be determined.")
    sql = (
        f"INSERT INTO [{TABLE[kind]}] "
        "([TrialSeriesID],[RelativePath],[StoredFilename],[OriginalFilename],[CreatedAt],[CreatedBy]) "
        "VALUES (?,?,?,?,?,?)"
    )
    params = [series_id, relative_path, stored_filename, original_filename, datetime.datetime.now(), user_id]
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(sql, params)
        new_id = cur.lastrowid
        try:
            cn.commit()
        except Exception:
            pass
    return new_id


def analyze_garnspiegel(image_id: Optional[int], file_path: str, original_filename: str, user_id: Any) -> None:
    """Best-effort: Garnspiegel width CV% (ui/yarnscope/garnspiegel_analysis.py, no Qt)
    for a freshly uploaded image -> tblTrialSeriesImageAnalysis. Only files named after
    the lab convention "V<n>.jpg" are tried (no false positive on unrelated photos).
    Never raises - the upload itself must not fail because of this."""
    if image_id is None or not table_exists("tblTrialSeriesImageAnalysis"):
        return
    try:
        from ui.yarnscope.garnspiegel_analysis import (
            analyze_image, to_db_row, PARAMS_VERSION, looks_like_garnspiegel_filename,
        )
        if not looks_like_garnspiegel_filename(original_filename):
            return
        stats = analyze_image(file_path)
        db_row = to_db_row(stats)
        cols = ["TrialSeriesImageID", "GlobalID", "UserID", "Timestamp", "ParamsVersion"] + list(db_row.keys())
        vals = [image_id, new_global_id(), user_id, datetime.datetime.now(), PARAMS_VERSION] + list(db_row.values())
        placeholders = ",".join(["?"] * len(cols))
        _db_execute(
            f"INSERT INTO tblTrialSeriesImageAnalysis ({','.join(cols)}) VALUES ({placeholders})",
            vals,
        )
    except Exception as e:
        logger.warning("analyze_garnspiegel: %s", e)


def store_file(kind: str, user_id: Any, series_id: Any, data: bytes, original_filename: str,
               target_dir: Optional[str] = None) -> Tuple[str, Optional[int]]:
    """Writes one file (bytes) under a random name into the series folder, adds its row
    and (images) runs the Garnspiegel analysis. `original_filename` = the name users see
    (path parts are dropped). Returns (stored file name, new row ID). Call prepare_folder() first."""
    orig_name = os.path.basename(original_filename)
    _, ext = os.path.splitext(orig_name)
    ext = ext or DEFAULT_EXT[kind]

    stored_name = f"{uuid.uuid4().hex}{ext}"
    dst = os.path.join(target_dir or series_dir(kind, series_id), stored_name)
    with open(dst, "wb") as fdst:
        fdst.write(data)

    new_id = insert_row(kind, user_id, series_id=series_id, relative_path=relative_path_for_db(kind, series_id),
                        stored_filename=stored_name, original_filename=orig_name)
    if kind == "image":
        analyze_garnspiegel(new_id, dst, orig_name, user_id)
    return stored_name, new_id


def log_upload(kind: str, user_id: Any, series_id: Any) -> None:
    """tblFeatureUsage row for an upload batch (stealth tracking, never raises)."""
    try:
        if user_id is not None:
            _db_execute(
                "INSERT INTO tblFeatureUsage (FeatureID, UserID, ExtraInfo) VALUES (?, ?, ?)",
                [FEATURE_ID[kind], user_id, str(series_id)],
            )
    except Exception:
        pass


def upload_paths(kind: str, user_id: Any, series_id: Any, paths: List[str]) -> Tuple[int, List[str]]:
    """Desktop upload: files picked on disk -> (stored count, ["name: error"]).
    Folder problems raise RuntimeError (nothing stored)."""
    target_dir = prepare_folder(kind, series_id)
    stored, errors = 0, []
    for src in paths:
        try:
            with open(src, "rb") as fsrc:
                data = fsrc.read()
            store_file(kind, user_id, series_id, data, os.path.basename(src), target_dir)
            stored += 1
        except Exception as e:
            errors.append(f"{os.path.basename(src)}: {e}")
    if stored >= 1:
        log_upload(kind, user_id, series_id)
    return stored, errors


# ---------------- web upload ----------------

def sniff_kind(data: bytes) -> Optional[str]:
    """"image" / "pdf" from the first bytes of the file, None if it is neither."""
    head = bytes(data[:32])
    if head.startswith(b"%PDF-"):
        return "pdf"
    if (head.startswith(b"\x89PNG\r\n\x1a\n") or head.startswith(b"\xff\xd8\xff")
            or head.startswith(b"GIF87a") or head.startswith(b"GIF89a") or head.startswith(b"BM")
            or head.startswith(b"II*\x00") or head.startswith(b"MM\x00*")
            or (head.startswith(b"RIFF") and head[8:12] == b"WEBP")
            or (head[4:8] == b"ftyp" and head[8:12] in (b"heic", b"heix", b"hevc", b"hevx", b"mif1",
                                                        b"msf1", b"heim", b"heis", b"avif"))):
        return "image"
    return None


def series_exists(series_id: Any) -> bool:
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute("SELECT 1 FROM [tblTrialSeries] WHERE [ID]=? LIMIT 1", [series_id])
        return cur.fetchone() is not None


def add_files(user: dict, series_id: Any, files: List[Tuple[str, bytes]]) -> Dict[str, Any]:
    """Web upload: [(original filename, bytes)] - images and PDFs mixed. The kind comes
    from the content (sniff_kind) and must match the extension (same extensions as the
    desktop pickers). Returns {"images": n, "pdfs": n, "errors": ["name: error"]}.
    LookupError if the series does not exist."""
    if not series_exists(series_id):
        raise LookupError("The trial series was not found.")
    user_id = (user or {}).get("id")
    counts = {"image": 0, "pdf": 0}
    errors: List[str] = []
    folders: Dict[str, str] = {}
    for name, data in files:
        base = os.path.basename((name or "").replace("\\", "/"))
        try:
            kind = sniff_kind(data)
            ext = os.path.splitext(base)[1].lower()
            if kind is None:
                raise ValueError("not an image or PDF file")
            allowed = IMAGE_EXTENSIONS if kind == "image" else PDF_EXTENSIONS
            if ext not in allowed:
                raise ValueError("the file name does not match its content")
            if kind not in folders:
                folders[kind] = prepare_folder(kind, series_id)
            store_file(kind, user_id, series_id, data, base, folders[kind])
            counts[kind] += 1
        except Exception as e:
            errors.append(f"{base}: {e}")
    for kind, n in counts.items():
        if n:
            log_upload(kind, user_id, series_id)
    return {"images": counts["image"], "pdfs": counts["pdf"], "errors": errors}


# ---------------- rename / delete (web; the desktop viewers use the er_images helpers directly) ----------------

def _find(kind: str, series_id: Any, attachment_id: Any) -> Dict[str, Any]:
    if kind not in KINDS:
        raise LookupError("Unknown attachment kind.")
    rows = sa.list_images(series_id) if kind == "image" else sa.list_pdfs(series_id)
    for r in rows:
        if str(r.get("ID")) == str(attachment_id):
            return r
    raise LookupError("Attachment not found.")


def rename(user: dict, kind: str, series_id: Any, attachment_id: Any, typed: str) -> Optional[str]:
    """New OriginalFilename (extension fixed, slashes -> "_") or None if `typed` is blank.
    Desktop rule: everybody may rename. LookupError / RuntimeError (row not updated)."""
    row = _find(kind, series_id, attachment_id)
    new_name = er_images.new_original_filename(row, typed, fallback_ext=DEFAULT_EXT[kind])
    if new_name is None:
        return None
    if not er_images.persist_original_filename(TABLE[kind], FK, series_id, row, new_name):
        raise RuntimeError("No database row was updated. The file could not be matched.")
    return new_name


def delete(user: dict, kind: str, series_id: Any, attachment_ids: List[Any]) -> Dict[str, Any]:
    """Deletes the chosen attachments the user may delete (uploader or superuser), skips
    the others. DB row first, file second, empty folder removed (er_images.delete_image_records).
    Returns {"deleted": [ids], "errors": [texts], "skipped": n not allowed}."""
    if kind not in KINDS:
        raise LookupError("Unknown attachment kind.")
    rows = sa.list_images(series_id) if kind == "image" else sa.list_pdfs(series_id)
    by_id = {str(d.get("ID")): d for d in rows}
    chosen = [by_id[str(i)] for i in attachment_ids if str(i) in by_id]
    allowed = [d for d in chosen if er_images.can_delete(user, d)]
    errors: List[str] = []
    if len(allowed) < len(chosen):
        errors.append(
            f"{len(chosen) - len(allowed)} file(s) skipped: you can only delete your own uploads "
            "(or need superuser rights)."
        )
    skipped = len(chosen) - len(allowed)
    if not allowed:
        return {"deleted": [], "errors": errors, "skipped": skipped}
    done = er_images.delete_image_records(TABLE[kind], FK, series_id, allowed, errors)
    return {"deleted": [d.get("ID") for d in done], "errors": errors, "skipped": skipped}
