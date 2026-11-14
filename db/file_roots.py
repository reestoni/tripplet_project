"""file_roots.py - folders on the file share that TrippleT reads and writes (desktop and web).

Default: dev databases (dev, dev_local) use local test folders under C:\\ttt, prod uses the H: share
(H: = \\\\heb-fil-003\\heberlein). Every folder can be overridden with an environment variable
TRIPPLET_DIR_<KEY> - the web server sets them in its config (a Windows service sees no per-user
drive mappings; it either maps H: itself or points these variables at the UNC paths).

Note: the database stores absolute folders for attachments (RelativePath = "H:\\Technik\\..."), so
servers that read existing attachments must still resolve H: - see tripplet_web/DEPLOY.md.
"""
from __future__ import annotations

import os
from typing import Dict, Tuple

SHARE = r"H:\Technik\TrippleT"

# key -> (dev folder, prod folder)
FOLDERS: Dict[str, Tuple[str, str]] = {
    "TRIALSERIES_IMAGES": (r"C:\ttt\images\TrialSeriesImages", SHARE + r"\TrialSeriesImages"),
    "TRIALSERIES_PDFS": (r"C:\ttt\pdfs", SHARE + r"\TrialSeriesPDF"),
    "REQUEST_IMAGES": (r"C:\ttt\images\ExperimentRequestImages", SHARE + r"\ExperimentRequestImages"),
    "JET_FILES": (r"C:\ttt\JetFiles", SHARE + r"\JetFiles"),
    "TOPPLATE_FILES": (r"C:\ttt\TopPlateFiles", SHARE + r"\TopPlateFiles"),
    "USER_AVATARS": (r"C:\ttt\UserAvatars", SHARE + r"\UserAvatars"),
}


def env_name(key: str) -> str:
    return f"TRIPPLET_DIR_{key}"


def _dev() -> bool:
    try:
        from db.connection import is_dev_mode
        return bool(is_dev_mode())
    except Exception:
        return False


def folder(key: str) -> str:
    """The folder for ``key``: env override, else the dev or prod default."""
    override = (os.environ.get(env_name(key)) or "").strip()
    if override:
        return override
    dev, prod = FOLDERS[key]
    return dev if _dev() else prod


def known_folders(key: str) -> Tuple[str, ...]:
    """All folders a stored path of this kind may point to (current one + both defaults; copies of
    prod data on dev databases still point to the share)."""
    seen = []
    for p in (folder(key), *FOLDERS[key]):
        if p and p not in seen:
            seen.append(p)
    return tuple(seen)
