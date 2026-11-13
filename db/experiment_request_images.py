from __future__ import annotations

# db/experiment_request_images.py
"""Images attached to Experiment Requests, without Qt - shared by the desktop and
the web app (2026-11-13, moved out of ui/screen_create_experiment_request.py and the
read-only request popup in ui/screen_show_experiment.py; behaviour unchanged).

Storage: the files live in REQUEST_IMAGES_BASE_DIR\\<RequestID>\\ under a random
name (uuid hex + original extension); tblExperimentRequestImage holds
RelativePath (= that folder, with trailing backslash), StoredFilename,
OriginalFilename (the name users see/rename), CreatedAt, CreatedBy.

Rules (unchanged): everybody who can open the request can upload and rename;
delete only the uploader (CreatedBy) or a superuser (AccessLevel >= 4). Uploading
before the first save creates a DRAFT request (RequestStatus NULL), see
ensure_request_for_upload().

The generic row helpers (delete_image_records, persist_original_filename,
new_original_filename) also serve the image viewer for series images
(tblTrialSeriesImage) - they take table/fk names for that reason.
"""

import os
import shutil
import uuid
import datetime
from typing import Any, Dict, List, Optional, Tuple

from db.connection import get_connection, is_dev_mode
from db import experiment_requests as er

# Basisordner fuer Experiment-Request-Bilder
# - PROD: Netzlaufwerk (gemeinsame Ablage)
# - DEV:  lokaler Testordner
REQUEST_IMAGES_BASE_DIR = (
    r"C:\ttt\images\ExperimentRequestImages" if is_dev_mode() else r"H:\Technik\TrippleT\ExperimentRequestImages"
)

IMAGE_TABLE = "tblExperimentRequestImage"
IMAGE_FK = "ExperimentRequestID"

# Extensions offered by the desktop file picker (web uploads are checked against it)
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp", ".heic", ".heif")

DELETE_DENIED_MESSAGE = "You can only delete your own uploads (or need superuser rights)."


# ---------------- paths ----------------

def images_dir(request_id: Any) -> str:
    """Gibt den Zielordner fuer Bilder eines Requests zurueck."""
    return os.path.join(REQUEST_IMAGES_BASE_DIR, str(request_id))


def relative_path_for_db(request_id: Any) -> str:
    """Gibt den Pfad so zurueck, wie er in RelativePath gespeichert werden soll."""
    # In der DB wollen wir den UNC-Pfad mit Backslashes und trailing Slash.
    return REQUEST_IMAGES_BASE_DIR + "\\" + str(request_id) + "\\"


# ---------------- listing ----------------

def has_images(request_id: Any) -> bool:
    """True if at least one image row exists for this request."""
    if request_id in (None, ""):
        return False
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            # Works with the Access-to-MySQL translation layer in db.connection
            cur.execute(
                "SELECT 1 FROM [tblExperimentRequestImage] WHERE [ExperimentRequestID]=? LIMIT 1",
                [request_id],
            )
            return cur.fetchone() is not None
    except Exception:
        return False


def list_images(request_id: Any, *, with_stored_file_key: bool = False) -> List[Dict[str, Any]]:
    """Images of the request, newest first: dicts with ID, RelativePath,
    StoredFilename, OriginalFilename, FullPath, CreatedBy (+ StoredFile = same as
    StoredFilename when with_stored_file_key, as the read-only popup passes it)."""
    if request_id in (None, ""):
        return []
    rows: List[Dict[str, Any]] = []
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            "SELECT [ID], [RelativePath], [StoredFilename], [OriginalFilename], [CreatedBy] "
            "FROM [tblExperimentRequestImage] "
            "WHERE [ExperimentRequestID]=? "
            "ORDER BY [ID] DESC",
            [request_id],
        )
        for img_id, rel_path, stored, orig_name, created_by in cur.fetchall() or []:
            rel_path = str(rel_path or "")
            stored = str(stored or "")
            orig_name = str(orig_name or "")
            full = os.path.join(rel_path, stored) if rel_path else stored
            d: Dict[str, Any] = {"ID": img_id, "RelativePath": rel_path, "StoredFilename": stored}
            if with_stored_file_key:
                d["StoredFile"] = stored
            d.update({"OriginalFilename": orig_name, "FullPath": full, "CreatedBy": created_by})
            rows.append(d)
    return rows


def image_file(request_id: Any, image_id: Any) -> Optional[str]:
    """Real path of one image of the request, only if the file exists and lies
    inside REQUEST_IMAGES_BASE_DIR (for web downloads); else None."""
    root = os.path.normcase(os.path.realpath(REQUEST_IMAGES_BASE_DIR))
    for d in list_images(request_id):
        if str(d.get("ID")) != str(image_id):
            continue
        p = os.path.normcase(os.path.realpath(str(d.get("FullPath") or "")))
        if (p.startswith(root + os.sep)) and os.path.isfile(p):
            return p
    return None


# ---------------- permissions ----------------

def can_delete(user: Optional[dict], img: Dict[str, Any]) -> bool:
    """Only the owner (CreatedBy) or a superuser (AccessLevel >= 4) may delete."""
    try:
        level = int((user or {}).get("access_level") or 0)
    except Exception:
        level = 0
    if level >= 4:
        return True
    owner_id = img.get("CreatedBy")
    try:
        uid = (user or {}).get("id")
    except Exception:
        uid = None
    return owner_id not in (None, "") and uid not in (None, "") and str(owner_id) == str(uid)


# ---------------- upload ----------------

def ensure_request_for_upload(user: dict, request_id: Any, values: Dict[str, Any],
                              cols: Optional[List[er.ColumnInfo]] = None) -> Any:
    """Stellt sicher, dass es eine ExperimentRequestID gibt.

    Falls der Request noch nicht gespeichert ist (request_id None), wird mit den
    aktuellen Formwerten ein Datensatz erzeugt, aber explizit als "Draft"
    markiert (RequestStatus = NULL) - ohne Pflichtfeld-Validierung."""
    if request_id not in (None, ""):
        return request_id
    return er.create_draft(user, values, cols)


def prepare_folder(request_id: Any) -> str:
    """Creates the request's image folder; RuntimeError with an explanation if not possible."""
    target_dir = images_dir(request_id)
    try:
        os.makedirs(target_dir, exist_ok=True)
    except PermissionError as e:
        raise RuntimeError(
            "[WinError 5] Access denied while creating the target folder. "
            "This is a permission problem on the share/NTFS.\n\n"
            f"Path: {target_dir}\n\n"
            "Please ensure that the Windows user (or the account running TrippleT) "
            f"has write permission on {REQUEST_IMAGES_BASE_DIR}.\n\n"
            f"Original error: {e}"
        )
    except Exception as e:
        raise RuntimeError(f"Target folder could not be created: {target_dir}\n{e}")
    return target_dir


def insert_image_row(user: dict, *, request_id: Any, relative_path: str, stored_filename: str,
                     original_filename: str) -> None:
    """Erzeugt einen Datensatz in tblExperimentRequestImage."""
    created_by = (user or {}).get("id")
    if created_by in (None, ""):
        raise RuntimeError("CreatedBy/UserID could not be determined.")

    sql = (
        "INSERT INTO [tblExperimentRequestImage] "
        "([ExperimentRequestID],[RelativePath],[StoredFilename],[OriginalFilename],[CreatedAt],[CreatedBy]) "
        "VALUES (?,?,?,?,?,?)"
    )
    params = [
        request_id,
        relative_path,
        stored_filename,
        original_filename,
        datetime.datetime.now(),
        created_by,
    ]
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(sql, params)
        try:
            cn.commit()
        except Exception:
            pass


def store_image(user: dict, request_id: Any, data: bytes, original_filename: str,
                target_dir: Optional[str] = None) -> str:
    """Writes one image (bytes) under a random name into the request folder and
    adds its row. `original_filename` = the name the user sees (path parts are
    dropped). Returns the stored file name. Call prepare_folder() first."""
    orig_name = os.path.basename(original_filename)
    _, ext = os.path.splitext(orig_name)
    ext = ext or ""

    stored_name = f"{uuid.uuid4().hex}{ext}"
    dst = os.path.join(target_dir or images_dir(request_id), stored_name)

    with open(dst, "wb") as fdst:
        fdst.write(data)

    # DB-Eintrag
    insert_image_row(
        user,
        request_id=request_id,
        relative_path=relative_path_for_db(request_id),
        stored_filename=stored_name,
        original_filename=orig_name,
    )
    return stored_name


def add_images(user: dict, request_id: Any, files: List[Tuple[str, bytes]]) -> Tuple[int, List[str]]:
    """Web upload: [(original filename, bytes)] -> (stored count, ["name: error"]).
    The request must exist (use ensure_request_for_upload() for a new one) and be
    openable by `user` (PermissionError)."""
    row = er.fetch_request(request_id)
    if row is None:
        raise LookupError("The selected request was not found.")
    if not er.can_open(user, row):
        raise PermissionError("You can only add images to your own requests.")
    target_dir = prepare_folder(request_id)
    stored, errors = 0, []
    for name, data in files:
        try:
            if os.path.splitext(name or "")[1].lower() not in IMAGE_EXTENSIONS:
                raise ValueError("not an image file")
            store_image(user, request_id, data, name, target_dir)
            stored += 1
        except Exception as e:
            errors.append(f"{os.path.basename(name or '')}: {e}")
    return stored, errors


# ---------------- rename ----------------

def fixed_extension(img: Dict[str, Any], fallback: str = "") -> str:
    """Extension that stays fixed when renaming (from OriginalFilename, else StoredFilename)."""
    stored = str(img.get("StoredFilename") or img.get("StoredFile") or "")
    current = str(img.get("OriginalFilename") or "")
    _b, ext = os.path.splitext(current or stored)
    return ext or (fallback or "")


def new_original_filename(img: Dict[str, Any], typed: str, *, prefix: str = "",
                          fallback_ext: str = "") -> Optional[str]:
    """New OriginalFilename from what the user typed: blank -> None; a typed
    extension is dropped and the fixed one appended; optional prefix is prepended
    unless already there; slashes become "_"."""
    ext = fixed_extension(img, fallback_ext)
    new_base = (typed or "").strip()
    if not new_base:
        return None
    # If user typed a full filename, strip any extension they tried to set.
    cand_base, cand_ext = os.path.splitext(new_base)
    if cand_ext:
        new_base = cand_base
    prefix = (prefix or "").strip()
    if prefix:
        # If user already typed the prefix, don't add it again.
        if not new_base.lower().startswith(prefix.lower()):
            new_base = f"{prefix}{new_base}"
    # Sanitize (avoid paths)
    new_base = new_base.replace("/", "_").replace("\\", "_")
    return f"{new_base}{ext}"


def persist_original_filename(table_name: str, fk_field: str, fk_value: Any,
                              img: Dict[str, Any], new_name: str) -> bool:
    """UPDATE OriginalFilename of one image row (by ID, else FK + StoredFilename +
    RelativePath) and verify it by reading back - True if persisted. Raises on DB errors."""
    rel_path = str(img.get("RelativePath") or "")
    stored = str(img.get("StoredFilename") or img.get("StoredFile") or "")

    # Helper: Access via ODBC is notorious for returning rowcount = -1
    # (unknown) even when an UPDATE succeeded. So we verify by selecting.
    def _verify_persisted(cur) -> bool:
        img_id = img.get("ID")
        if img_id not in (None, ""):
            cur.execute(
                f"SELECT [OriginalFilename] FROM [{table_name}] WHERE [ID]=?",
                [img_id],
            )
            row = cur.fetchone()
            return bool(row and str(row[0] or "").strip().lower() == str(new_name).strip().lower())

        cur.execute(
            f"SELECT [OriginalFilename] FROM [{table_name}] "
            f"WHERE [{fk_field}]=? AND [StoredFilename]=? AND [RelativePath]=?",
            [fk_value, stored, rel_path],
        )
        row = cur.fetchone()
        return bool(row and str(row[0] or "").strip().lower() == str(new_name).strip().lower())

    with get_connection() as cn:
        cur = cn.cursor()

        # Prefer the row's own primary key if available (most robust)
        img_id = img.get("ID")
        if img_id not in (None, ""):
            cur.execute(
                f"UPDATE [{table_name}] SET [OriginalFilename]=? WHERE [ID]=?",
                [new_name, img_id],
            )
        else:
            # Fallback: match by FK + StoredFilename + RelativePath
            cur.execute(
                f"UPDATE [{table_name}] "
                f"SET [OriginalFilename]=? "
                f"WHERE [{fk_field}]=? AND [StoredFilename]=? AND [RelativePath]=?",
                [new_name, fk_value, stored, rel_path],
            )

        cn.commit()

        # Only report failure if we can verify that the DB did NOT update.
        # (rowcount may be 0 or -1 even when the update worked.)
        return _verify_persisted(cur)


def rename_image(user: dict, request_id: Any, image_id: Any, typed: str) -> Optional[str]:
    """Web rename: new OriginalFilename (extension fixed) or None if `typed` is
    blank. LookupError if the image does not belong to the request,
    PermissionError if the user cannot open the request, RuntimeError if the
    row could not be updated."""
    row = er.fetch_request(request_id)
    if row is None or not er.can_open(user, row):
        raise PermissionError("You can only rename images of your own requests.")
    img = next((d for d in list_images(request_id) if str(d.get("ID")) == str(image_id)), None)
    if img is None:
        raise LookupError("Image not found.")
    new_name = new_original_filename(img, typed)
    if new_name is None:
        return None
    if not persist_original_filename(IMAGE_TABLE, IMAGE_FK, request_id, img, new_name):
        raise RuntimeError("No database row was updated. The image could not be matched.")
    return new_name


# ---------------- delete ----------------

def delete_image_records(table_name: str, fk_field: str, fk_value: Any,
                         images: List[Dict[str, Any]], errors: List[str]) -> List[Dict[str, Any]]:
    """Deletes image rows + files, in the given order. Returns the image dicts
    that were really deleted; problems are appended to `errors`.

    DB row FIRST, file SECOND: a failed DB delete leaves the file untouched (an
    earlier file-first order orphaned rows when the DELETE then failed on an FK
    of tblTrialSeriesImageAnalysis). A row that is already gone keeps its file.
    If no rows remain for the FK and there were no errors at all, the folders of
    the deleted files are removed too (best-effort). No permission check here -
    callers filter with can_delete()."""
    deleted: List[Dict[str, Any]] = []
    deleted_dirs: set[str] = set()

    for img in images:
        rel_path = str(img.get("RelativePath") or "")
        stored = str(img.get("StoredFilename") or img.get("StoredFile") or "")
        full_path = str(img.get("FullPath") or (os.path.join(rel_path, stored) if rel_path else stored))
        img_id = img.get("ID")

        db_deleted = False
        try:
            with get_connection() as cn:
                cur = cn.cursor()
                # Child row first (FK-Kind von tblTrialSeriesImage) - nur
                # relevant/vorhanden für genau diese Tabelle, best-effort
                # falls die Analyse-Tabelle in einer Umgebung fehlt oder
                # gar keine Analyse für dieses Bild existiert.
                if img_id not in (None, "") and table_name.lower() == "tbltrialseriesimage":
                    try:
                        cur.execute(
                            "DELETE FROM tblTrialSeriesImageAnalysis WHERE TrialSeriesImageID=?",
                            [img_id],
                        )
                    except Exception:
                        pass
                if img_id not in (None, ""):
                    cur.execute(
                        f"DELETE FROM [{table_name}] WHERE [ID]=?", [img_id])
                else:
                    cur.execute(
                        f"DELETE FROM [{table_name}] WHERE [{fk_field}]=? "
                        f"AND [RelativePath]=? AND [StoredFilename]=?",
                        [fk_value, rel_path, stored],
                    )
                db_deleted = (cur.rowcount or 0) > 0
                try:
                    cn.commit()
                except Exception:
                    pass
        except Exception as e:
            errors.append(f"Could not delete database entry for:\n{stored}\n\n{e}")

        if not db_deleted:
            if not errors or "database entry for" not in errors[-1]:
                errors.append(
                    f"Database entry not found (already deleted?), file left untouched:\n{stored}")
            continue  # Datei bewusst NICHT anfassen

        # DB-Zeile ist nachweislich weg - jetzt erst die Datei löschen.
        # deleted_dirs nur für tatsächlich gelöschte Einträge (sonst
        # würde die Ordner-Löschung unten übersprungene Dateien mitreissen).
        if rel_path:
            deleted_dirs.add(os.path.normpath(rel_path))
        try:
            if full_path and os.path.exists(full_path):
                os.remove(full_path)
        except Exception as e:
            errors.append(
                f"Database entry deleted, but the file could not be removed:\n{full_path}\n\n{e}")
        deleted.append(img)

    # If no images remain for this FK, delete the folder too - but only if
    # this batch had zero errors/skips ("0 rows remain in the DB" alone isn't
    # proof the folder is empty: a skipped item keeps its file on purpose).
    try:
        if not errors:
            remaining = 1
            with get_connection() as cn:
                cur = cn.cursor()
                cur.execute(
                    f"SELECT COUNT(*) FROM [{table_name}] WHERE [{fk_field}]=?",
                    [fk_value],
                )
                row = cur.fetchone()
                remaining = int(row[0]) if row and row[0] is not None else 0

            if remaining == 0:
                for d in list(deleted_dirs):
                    try:
                        if d and os.path.isdir(d):
                            shutil.rmtree(d)
                    except Exception:
                        # Best-effort cleanup; no UI errors for folder deletion.
                        pass
    except Exception:
        # Folder cleanup is best-effort
        pass
    return deleted


def delete_images(user: dict, request_id: Any, image_ids: List[Any]) -> Dict[str, Any]:
    """Web delete: images of the request the user may delete (can_delete) are
    removed, others skipped. Returns {"deleted": [ids], "errors": [texts]}."""
    by_id = {str(d.get("ID")): d for d in list_images(request_id)}
    chosen = [by_id[str(i)] for i in image_ids if str(i) in by_id]
    allowed = [d for d in chosen if can_delete(user, d)]
    denied = [d for d in chosen if not can_delete(user, d)]
    errors: List[str] = []
    if denied:
        errors.append(
            f"{len(denied)} file(s) skipped: you can only delete your own uploads "
            "(or need superuser rights)."
        )
    if not allowed:
        return {"deleted": [], "errors": errors or ([DELETE_DENIED_MESSAGE] if chosen else [])}
    done = delete_image_records(IMAGE_TABLE, IMAGE_FK, request_id, allowed, errors)
    return {"deleted": [d.get("ID") for d in done], "errors": errors}
