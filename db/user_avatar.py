"""user_avatar.py - optional profile picture per user (desktop + web, Nutzerwunsch 2026-11-14).

Stored as a file, not in the database (no schema change): <USER_AVATARS>/<UserID>.png, folder from
db/file_roots.py (dev: C:\\ttt\\UserAvatars, prod: H:\\Technik\\TrippleT\\UserAvatars, env
TRIPPLET_DIR_USER_AVATARS). Every upload is normalised here: EXIF rotation applied, cut to a centred
square, scaled to SIZE px, saved as PNG - so both apps only ever read one small, known file.
"""
from __future__ import annotations

import io
import os
from typing import Optional

from db import file_roots

SIZE = 256                       # stored edge length in px
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MIN_EDGE = 32                    # smaller pictures are refused (would only be a blur)
EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff")


class AvatarError(ValueError):
    """Message for the user + a code for the web app (too_big / not_image / too_small)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def folder() -> str:
    return file_roots.folder("USER_AVATARS")


def path_for(user_id) -> str:
    return os.path.join(folder(), f"{int(user_id)}.png")


def has_avatar(user_id) -> bool:
    try:
        return user_id is not None and os.path.isfile(path_for(user_id))
    except (TypeError, ValueError, OSError):
        return False


def version(user_id) -> int:
    """Changes whenever the picture changes (cache key for the web app); 0 = no picture."""
    try:
        return int(os.path.getmtime(path_for(user_id))) if has_avatar(user_id) else 0
    except OSError:
        return 0


def load_bytes(user_id) -> Optional[bytes]:
    if not has_avatar(user_id):
        return None
    try:
        with open(path_for(user_id), "rb") as fh:
            return fh.read()
    except OSError:
        return None


def normalise(data: bytes) -> bytes:
    """Any common image -> square PNG of SIZE px (raises AvatarError)."""
    if not data:
        raise AvatarError("not_image", "The file is not a picture.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise AvatarError("too_big", f"The picture is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    from PIL import Image, ImageOps, UnidentifiedImageError
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except (UnidentifiedImageError, OSError, ValueError) as e:
        raise AvatarError("not_image", "The file is not a picture.") from e
    im = ImageOps.exif_transpose(im)
    if min(im.size) < MIN_EDGE:
        raise AvatarError("too_small", f"The picture is too small (at least {MIN_EDGE} x {MIN_EDGE} px).")
    im = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
    im = ImageOps.fit(im, (SIZE, SIZE), method=Image.LANCZOS, centering=(0.5, 0.4))  # faces sit a bit high
    out = io.BytesIO()
    im.save(out, format="PNG", optimize=True)
    return out.getvalue()


def save(user_id, data: bytes) -> str:
    """Normalise and store the picture of this user; returns the file path."""
    png = normalise(data)
    os.makedirs(folder(), exist_ok=True)
    target = path_for(user_id)
    tmp = target + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(png)
    os.replace(tmp, target)          # never a half-written picture for the other app
    return target


def delete(user_id) -> bool:
    try:
        os.remove(path_for(user_id))
        return True
    except FileNotFoundError:
        return False
