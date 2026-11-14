"""canvas_boards.py - Canvas boards stored in the database (desktop + web, Nutzerwunsch 2026-11-14).

Before, a Canvas lived in a .ttcanvas file on one PC. A board is now a row in tblCanvasBoard, optionally tied to
a trial series ("board of this series"), visible to every user with the Canvas feature, saved with a version
number so two people cannot silently overwrite each other (save_board raises BoardConflict).

Board content = one JSON document in an app-neutral format (both apps read and write it):

    {"format": "tripplet-board", "version": 1, "bg": "#1e1e1e",
     "items": [{"id": "a1b2", "label": "V3.png",
                "src": {"kind": "series_image", "series": 12, "id": 345}      # tblTrialSeriesImage.ID
                     | {"kind": "series_pdf",   "series": 12, "id": 67}       # tblTrialSeriesPDF.ID
                     | {"kind": "file", "file": "3f2a9c_name.png"},           # stored with the board (see below)
                "page": 0, "sheet": 0, "channel": "",                          # PDF/Word page, Excel sheet, VK4 channel
                "cx": 120.0, "cy": 80.0, "w": 640.0, "h": 480.0,               # centre + shown size in board units
                "angle": 0.0}],                                                # degrees, clockwise, around the centre
     "annos": [{"tool": "arrow", "color": "red", "size": 2, "text": "", "points": [[x, y], ...]}]}

Each app converts its own item geometry to centre/size/angle (desktop: rotation around the top-left corner,
web: around the centre), so a board looks the same in both. Files that do not belong to a series (local files,
clipboard pictures) are copied into the board's folder: file_roots "CANVAS_FILES"/<BoardID>/ (dev:
C:\\ttt\\CanvasFiles, prod: H:\\Technik\\TrippleT\\CanvasFiles, env TRIPPLET_DIR_CANVAS_FILES).

The table is created by tools/canvas_board_migration.py (never by the apps themselves).
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import uuid
from typing import Any, Dict, List, Optional

from db import file_roots

TABLE = "tblCanvasBoard"
FORMAT = "tripplet-board"
FORMAT_VERSION = 1
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_ITEMS = 400
MAX_ANNOS = 4000
MAX_POINTS = 20000
TITLE_MAX = 200
MAX_FILE_BYTES = 200 * 1024 * 1024
SRC_KINDS = ("series_image", "series_pdf", "file")
TOOLS = ("arrow", "ellipse", "rect", "free", "text", "highlight", "marker")
COLOURS = ("red", "yellow", "green", "white", "blue")
FILE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tif", ".tiff", ".vk4", ".pdf",
                   ".xlsx", ".xlsm", ".xls", ".docx", ".doc")

CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    ID INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    TrialSeriesID INT NULL,
    Title VARCHAR({TITLE_MAX}) NOT NULL,
    Content MEDIUMTEXT NOT NULL,
    Version INT NOT NULL DEFAULT 1,
    CreatedBy INT NULL,
    CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UpdatedBy INT NULL,
    UpdatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_canvas_series (TrialSeriesID),
    INDEX idx_canvas_updated (UpdatedAt)
) DEFAULT CHARSET=utf8mb4
"""


class BoardError(ValueError):
    """Message for the user + code for the web app."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class BoardConflict(BoardError):
    """Someone else saved the board in the meantime (version differs)."""

    def __init__(self, current_version: int, updated_by: str):
        super().__init__("conflict", f"The board was changed by {updated_by or 'someone else'} in the meantime.")
        self.current_version = current_version
        self.updated_by = updated_by


# ----------------------------------------------------------------------------------------------- rights
def _user() -> Dict[str, Any]:
    import app_meta
    return getattr(app_meta, "current_user", None) or {}


def _level(user: Optional[Dict[str, Any]] = None) -> int:
    try:
        return int((user or _user()).get("access_level") or 0)
    except (TypeError, ValueError):
        return 0


def can_edit(user: Optional[Dict[str, Any]] = None) -> bool:
    """Saving boards: from access level 2 (like editing series)."""
    return _level(user) >= 2


def can_delete(board: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> bool:
    u = user or _user()
    return _level(u) >= 4 or (board.get("CreatedBy") is not None and board.get("CreatedBy") == u.get("id"))


def table_ready() -> bool:
    try:
        from db.connection import table_exists
        return table_exists(TABLE)
    except Exception:
        return False


# ----------------------------------------------------------------------------------------------- content
def empty_content(bg: str = "#1e1e1e") -> Dict[str, Any]:
    return {"format": FORMAT, "version": FORMAT_VERSION, "bg": bg, "items": [], "annos": []}


def _num(v: Any, default: float = 0.0, lo: float = -1e7, hi: float = 1e7) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(f):
        return default
    return max(lo, min(hi, f))


def _int(v: Any, default: int = 0, lo: int = 0, hi: int = 10_000) -> int:
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


_COLOUR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\- ]{0,180}$")


def _src(s: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(s, dict) or s.get("kind") not in SRC_KINDS:
        return None
    if s["kind"] == "file":
        name = str(s.get("file") or "")
        if not _FILE_RE.match(name) or ".." in name:
            return None
        return {"kind": "file", "file": name}
    try:
        return {"kind": s["kind"], "series": int(s["series"]), "id": int(s["id"])}
    except (KeyError, TypeError, ValueError):
        return None


def normalise_content(content: Any) -> Dict[str, Any]:
    """Validated copy of a board document (unknown keys dropped, numbers clamped). Raises BoardError."""
    if not isinstance(content, dict):
        raise BoardError("invalid", "The board content is not valid.")
    out = empty_content(content.get("bg") if _COLOUR_RE.match(str(content.get("bg") or "")) else "#1e1e1e")
    items = content.get("items") or []
    annos = content.get("annos") or []
    if not isinstance(items, list) or not isinstance(annos, list):
        raise BoardError("invalid", "The board content is not valid.")
    if len(items) > MAX_ITEMS or len(annos) > MAX_ANNOS:
        raise BoardError("too_big", "The board has too many elements.")
    for it in items:
        if not isinstance(it, dict):
            continue
        src = _src(it.get("src"))
        if src is None:
            continue
        out["items"].append({
            "id": str(it.get("id") or uuid.uuid4().hex[:8])[:16],
            "label": str(it.get("label") or "")[:200],
            "src": src,
            "page": _int(it.get("page")), "sheet": _int(it.get("sheet")),
            "channel": str(it.get("channel") or "")[:40],
            "cx": _num(it.get("cx")), "cy": _num(it.get("cy")),
            "w": _num(it.get("w"), 200.0, 1.0, 1e6), "h": _num(it.get("h"), 150.0, 1.0, 1e6),
            "angle": _num(it.get("angle")) % 360.0,
        })
    points_total = 0
    for a in annos:
        if not isinstance(a, dict) or a.get("tool") not in TOOLS:
            continue
        pts = []
        for p in a.get("points") or []:
            if isinstance(p, (list, tuple)) and len(p) >= 2:
                pts.append([_num(p[0]), _num(p[1])])
        if not pts:
            continue
        points_total += len(pts)
        if points_total > MAX_POINTS:
            raise BoardError("too_big", "The board has too many drawing points.")
        out["annos"].append({
            "tool": a["tool"],
            "color": a.get("color") if a.get("color") in COLOURS else "red",
            "size": _int(a.get("size"), 2, 1, 72),
            "text": str(a.get("text") or "")[:2000],
            "points": pts,
        })
    return out


def dumps(content: Dict[str, Any]) -> str:
    s = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
    if len(s.encode("utf-8")) > MAX_JSON_BYTES:
        raise BoardError("too_big", "The board is too large to be saved.")
    return s


def referenced_files(content: Dict[str, Any]) -> List[str]:
    return [it["src"]["file"] for it in content.get("items", []) if it.get("src", {}).get("kind") == "file"]


# ----------------------------------------------------------------------------------------------- files of a board
def files_folder(board_id: int) -> str:
    return os.path.join(file_roots.folder("CANVAS_FILES"), str(int(board_id)))


def add_file(board_id: int, original_name: str, data: bytes) -> str:
    """Stores a file with the board; returns the stored name (for {"kind": "file", "file": ...})."""
    base = os.path.basename(original_name or "file").strip() or "file"
    ext = os.path.splitext(base)[1].lower()
    if ext not in FILE_EXTENSIONS:
        raise BoardError("file_type", "This file type cannot be put on a board.")
    if len(data or b"") > MAX_FILE_BYTES:
        raise BoardError("file_too_big", "The file is too large.")
    stem = re.sub(r"[^A-Za-z0-9_.\- ]", "_", os.path.splitext(base)[0])[:80].strip(" .") or "file"
    name = f"{uuid.uuid4().hex[:10]}_{stem}{ext}"
    folder = files_folder(board_id)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, name), "wb") as fh:
        fh.write(data)
    return name


def add_file_from_path(board_id: int, path: str) -> str:
    with open(path, "rb") as fh:
        return add_file(board_id, os.path.basename(path), fh.read())


def file_path(board_id: int, name: str) -> Optional[str]:
    """Full path of a stored board file, only if the name is valid and the file exists."""
    if not _FILE_RE.match(str(name or "")) or ".." in name:
        return None
    folder = os.path.realpath(files_folder(board_id))
    p = os.path.realpath(os.path.join(folder, name))
    if not p.startswith(folder + os.sep) or not os.path.isfile(p):
        return None
    return p


def _prune_files(board_id: int, keep: List[str]) -> None:
    folder = files_folder(board_id)
    try:
        for n in os.listdir(folder):
            if n not in keep:
                try:
                    os.remove(os.path.join(folder, n))
                except OSError:
                    pass
    except OSError:
        pass


# ----------------------------------------------------------------------------------------------- database
_LIST_SQL = (f"SELECT b.ID, b.TrialSeriesID, b.Title, b.Version, b.CreatedBy, b.CreatedAt, b.UpdatedBy, b.UpdatedAt, "
             f"s.SeriesName, e.[Experiment ID] AS ExperimentID, "
             f"TRIM(CONCAT(COALESCE(uc.FirstName,''),' ',COALESCE(uc.LastName,''))) AS CreatedByName, "
             f"TRIM(CONCAT(COALESCE(uu.FirstName,''),' ',COALESCE(uu.LastName,''))) AS UpdatedByName "
             f"FROM {TABLE} b "
             f"LEFT JOIN tblTrialSeries s ON s.ID = b.TrialSeriesID "
             f"LEFT JOIN tblExperimente e ON e.ID = s.ExperimentID "
             f"LEFT JOIN tblUser uc ON uc.ID = b.CreatedBy "
             f"LEFT JOIN tblUser uu ON uu.ID = b.UpdatedBy ")


def list_boards(series_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Boards (newest change first) without content; series_id = only the boards of that series."""
    from db.connection import fetch_all
    if series_id is not None:
        return fetch_all(_LIST_SQL + "WHERE b.TrialSeriesID = ? ORDER BY b.UpdatedAt DESC, b.ID DESC", [int(series_id)])
    return fetch_all(_LIST_SQL + "ORDER BY b.UpdatedAt DESC, b.ID DESC")


def board_counts(series_ids: List[int]) -> Dict[int, int]:
    """{series id: number of boards} (for an icon in lists)."""
    ids = [int(i) for i in series_ids if i is not None]
    if not ids or not table_ready():
        return {}
    from db.connection import fetch_all
    rows = fetch_all(f"SELECT TrialSeriesID, COUNT(*) AS n FROM {TABLE} WHERE TrialSeriesID IN "
                     f"({','.join('?' * len(ids))}) GROUP BY TrialSeriesID", ids)
    return {int(r["TrialSeriesID"]): int(r["n"]) for r in rows}


def get_board(board_id: int) -> Optional[Dict[str, Any]]:
    """Board row with parsed "content"; None if it does not exist."""
    from db.connection import fetch_all
    rows = fetch_all(_LIST_SQL.replace("SELECT b.ID,", "SELECT b.Content, b.ID,") + "WHERE b.ID = ?", [int(board_id)])
    if not rows:
        return None
    row = rows[0]
    try:
        row["content"] = normalise_content(json.loads(row.pop("Content") or "{}"))
    except (ValueError, BoardError):
        row["content"] = empty_content()
    return row


def _clean_title(title: str) -> str:
    t = " ".join(str(title or "").split())[:TITLE_MAX]
    if not t:
        raise BoardError("no_title", "Please give the board a title.")
    return t


def create_board(title: str, series_id: Optional[int] = None, content: Optional[Dict[str, Any]] = None) -> int:
    """New board; returns its ID. Files of the content must be added afterwards (add_file needs the ID)."""
    if not can_edit():
        raise BoardError("no_right", "You may not save boards.")
    from db.connection import execute_insert
    doc = normalise_content(content or empty_content())
    uid = _user().get("id")
    new_id = execute_insert(
        f"INSERT INTO {TABLE} (TrialSeriesID, Title, Content, Version, CreatedBy, UpdatedBy) VALUES (?, ?, ?, 1, ?, ?)",
        [int(series_id) if series_id else None, _clean_title(title), dumps(doc), uid, uid])
    if not new_id:
        raise BoardError("save_failed", "The board could not be created.")
    _log("canvas_board_create", str(new_id))
    return int(new_id)


def save_board(board_id: int, content: Dict[str, Any], version: int, title: Optional[str] = None,
               series_id: Any = "keep") -> int:
    """Stores the content if nobody saved in between (else BoardConflict); returns the new version."""
    if not can_edit():
        raise BoardError("no_right", "You may not save boards.")
    from db.connection import execute, fetch_all
    doc = normalise_content(content)
    sets, params = ["Content = ?", "Version = Version + 1", "UpdatedBy = ?", "UpdatedAt = NOW()"], \
        [dumps(doc), _user().get("id")]
    if title is not None:
        sets.append("Title = ?")
        params.append(_clean_title(title))
    if series_id != "keep":
        sets.append("TrialSeriesID = ?")
        params.append(int(series_id) if series_id else None)
    n = execute(f"UPDATE {TABLE} SET {', '.join(sets)} WHERE ID = ? AND Version = ?", params + [int(board_id), int(version)])
    if not n:
        cur = fetch_all(f"SELECT b.Version, TRIM(CONCAT(COALESCE(u.FirstName,''),' ',COALESCE(u.LastName,''))) AS Name "
                        f"FROM {TABLE} b LEFT JOIN tblUser u ON u.ID = b.UpdatedBy WHERE b.ID = ?", [int(board_id)])
        if not cur:
            raise BoardError("not_found", "The board does not exist any more.")
        raise BoardConflict(int(cur[0]["Version"]), str(cur[0]["Name"] or ""))
    _prune_files(board_id, referenced_files(doc))
    _log("canvas_board_save", str(board_id))
    return int(version) + 1


def delete_board(board_id: int) -> None:
    from db.connection import execute
    board = get_board(board_id)
    if board is None:
        return
    if not can_delete(board):
        raise BoardError("no_right", "Only the creator or a superuser may delete this board.")
    execute(f"DELETE FROM {TABLE} WHERE ID = ?", [int(board_id)])
    shutil.rmtree(files_folder(board_id), ignore_errors=True)
    _log("canvas_board_delete", str(board_id))


def _log(name: str, detail: str) -> None:
    try:
        from db.usage_log import log_usage_event
        log_usage_event("feature", name, detail)
    except Exception:
        pass
