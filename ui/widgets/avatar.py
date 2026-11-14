"""avatar.py - round profile picture for Qt (data: db/user_avatar.py, shared with the web app)."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPainterPath, QPixmap

from db import user_avatar

_cache: dict = {}   # (user_id, size, version) -> QPixmap


def round_pixmap_from_bytes(data: bytes, size: int) -> Optional[QPixmap]:
    src = QPixmap()
    if not data or not src.loadFromData(data):
        return None
    ratio = 2  # sharp on high-dpi screens
    src = src.scaled(size * ratio, size * ratio, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    out = QPixmap(size * ratio, size * ratio)
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, size * ratio, size * ratio)
    p.setClipPath(path)
    p.drawPixmap(0, 0, src)
    p.end()
    out.setDevicePixelRatio(ratio)
    return out


def round_pixmap(user_id, size: int) -> Optional[QPixmap]:
    """The user's picture as a round pixmap, or None if there is none."""
    ver = user_avatar.version(user_id)
    if not ver:
        return None
    key = (user_id, size, ver)
    if key not in _cache:
        pm = round_pixmap_from_bytes(user_avatar.load_bytes(user_id) or b"", size)
        if pm is None:
            return None
        _cache[key] = pm
    return _cache[key]
