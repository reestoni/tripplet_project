"""display_prefs.py - per-user display settings for reading Show Experiment's
tables, Nutzerwunsch 2026-10-15 (colleagues with poor eyesight).

    scale      text size of the tables in percent (100 = normal)
    contrast   high contrast: black on white/grey stripes, dark grid lines,
               bold text, strong selection colour
    crosshair  highlights the row and column of the current cell incl.
               parameter name and trial number
    readbar    reading bar below each table: "V2 · Ply 1 · Air Pressure = 3.50"
    alert_marks  warnings (red/orange cells) get a symbol, not only a colour
    cb_colours colour-blind friendly: neutral stripes, orange/yellow warnings
               with symbols, blue crosshair
    app_scale  size of the whole program (Qt scale factor, needs a restart;
               also kept locally because it must be known before login)

Stored per user in tblUser.DisplaySettings (JSON), so the settings follow
the login to every PC. Without that column (not migrated yet, older offline
snapshot) they fall back to QSettings on this PC.

FrozenFirstColumnTable (only used by Show Experiment) registers itself as a
listener and re-applies on every change, so Settings and Ctrl+mouse wheel
act immediately on all open tables.
"""
from __future__ import annotations

import json
import weakref
from typing import Any, Callable, Dict, List

from PySide6.QtCore import QSettings, QTimer

import app_meta

COLUMN = "DisplaySettings"
ADD_COLUMN_SQL = "ALTER TABLE tbluser ADD COLUMN DisplaySettings VARCHAR(255) NULL DEFAULT NULL"

DEFAULTS: Dict[str, Any] = {"scale": 100, "contrast": False, "crosshair": False, "readbar": False,
                            "alert_marks": False, "cb_colours": False, "app_scale": 100}
_BOOL_KEYS = ("contrast", "crosshair", "readbar", "alert_marks", "cb_colours")
SCALE_CHOICES = [100, 125, 150, 200]
SCALE_MIN, SCALE_MAX, SCALE_STEP = 80, 300, 10
APP_SCALE_CHOICES = [100, 125, 150, 175, 200]
_LOCAL_APP_SCALE_KEY = "app_scale_local"

_prefs: Dict[str, Any] = dict(DEFAULTS)
_listeners: List[Any] = []
_save_timer: QTimer | None = None


# ── read / write ─────────────────────────────────────────────────────────
def current() -> Dict[str, Any]:
    return dict(_prefs)


def scale() -> int:
    return int(_prefs.get("scale") or 100)


def _clean(d: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(DEFAULTS)
    try:
        out["scale"] = max(SCALE_MIN, min(SCALE_MAX, int(d.get("scale", 100))))
    except (TypeError, ValueError):
        pass
    for k in _BOOL_KEYS:
        out[k] = bool(d.get(k, False))
    try:
        a = int(d.get("app_scale", 100))
        out["app_scale"] = a if a in APP_SCALE_CHOICES else 100
    except (TypeError, ValueError):
        pass
    return out


def _has_column() -> bool:
    try:
        from db.connection import get_columns_map
        return COLUMN.lower() in get_columns_map("tblUser")
    except Exception:
        return False


def _qsettings_key() -> str:
    return f"display/{(app_meta.current_user or {}).get('username') or 'default'}"


def load_for_current_user() -> None:
    """Called after login: loads the user's settings and applies them."""
    data: Dict[str, Any] = {}
    uid = (app_meta.current_user or {}).get("id")
    try:
        if uid and _has_column():
            from db.connection import fetch_all
            rows = fetch_all("SELECT DisplaySettings FROM tblUser WHERE ID = ?", [uid])
            raw = rows[0].get("DisplaySettings") if rows else None
            data = json.loads(raw) if raw else {}
        else:
            raw = QSettings("TrippleT", "Display").value(_qsettings_key(), "")
            data = json.loads(raw) if raw else {}
    except Exception:
        data = {}
    _set(_clean(data), persist=False)
    remember_app_scale_locally()


def save_now() -> None:
    remember_app_scale_locally()
    raw = json.dumps(_prefs, separators=(",", ":"))
    uid = (app_meta.current_user or {}).get("id")
    try:
        if uid and _has_column():
            from db.connection import execute
            execute("UPDATE tblUser SET DisplaySettings = ? WHERE ID = ?", [raw, uid])
            return
    except Exception:
        pass
    try:
        QSettings("TrippleT", "Display").setValue(_qsettings_key(), raw)
    except Exception:
        pass


def _save_later() -> None:
    """Debounced save (Ctrl+mouse wheel fires many small changes)."""
    global _save_timer
    if _save_timer is None:
        _save_timer = QTimer()
        _save_timer.setSingleShot(True)
        _save_timer.setInterval(1000)
        _save_timer.timeout.connect(save_now)
    _save_timer.start()


def update(persist: bool = True, **changes) -> None:
    new = dict(_prefs)
    new.update(changes)
    _set(_clean(new), persist=persist)


def _set(new: Dict[str, Any], persist: bool) -> None:
    global _prefs
    changed = new != _prefs
    _prefs = new
    if persist:
        _save_later()
    if changed:
        _notify()


def zoom_step(direction: int) -> None:
    """Ctrl+mouse wheel / Ctrl+Plus/Minus: +-10 %."""
    s = scale() + (SCALE_STEP if direction > 0 else -SCALE_STEP)
    update(scale=max(SCALE_MIN, min(SCALE_MAX, s)))


# ── app size (Qt scale factor) ──────────────────────────────────────────
def remember_app_scale_locally() -> None:
    """The scale factor must be set before the QApplication exists, i.e.
    before login - so the last user's value is also kept on this PC."""
    try:
        QSettings("TrippleT", "Display").setValue(_LOCAL_APP_SCALE_KEY, int(_prefs.get("app_scale") or 100))
    except Exception:
        pass


def apply_startup_scale() -> None:
    """Called at the very top of main.py, before any QApplication."""
    import os
    try:
        a = int(QSettings("TrippleT", "Display").value(_LOCAL_APP_SCALE_KEY, 100))
    except Exception:
        a = 100
    if a in APP_SCALE_CHOICES and a != 100:
        os.environ["QT_SCALE_FACTOR"] = str(a / 100.0)
    else:
        os.environ.pop("QT_SCALE_FACTOR", None)


def running_app_scale() -> int:
    import os
    try:
        return int(round(float(os.environ.get("QT_SCALE_FACTOR") or 1) * 100))
    except ValueError:
        return 100


def app_scale_needs_restart() -> bool:
    return int(_prefs.get("app_scale") or 100) != running_app_scale()


def restart_app() -> bool:
    """Restarts TrippleT with the new app size. Closes the windows first
    (they may ask about unsaved changes); returns False if one stayed open."""
    import os
    import sys
    from PySide6.QtCore import QProcess
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    app.closeAllWindows()
    if any(w.isVisible() for w in app.topLevelWidgets() if w.isWindow()):
        return False
    a = int(_prefs.get("app_scale") or 100)
    if a != 100:
        os.environ["QT_SCALE_FACTOR"] = str(a / 100.0)
    else:
        os.environ.pop("QT_SCALE_FACTOR", None)
    args = sys.argv[1:] if getattr(sys, "frozen", False) else sys.argv
    QProcess.startDetached(sys.executable, args)
    app.quit()
    return True


def offer_restart(parent=None) -> None:
    """After login on a PC where the app size differs, or after changing it."""
    from PySide6.QtWidgets import QMessageBox
    if not app_scale_needs_restart():
        return
    ans = QMessageBox.question(
        parent, "App size",
        f"The app size {int(_prefs.get('app_scale') or 100)} % applies after TrippleT restarts.\n\n"
        "Restart now? (You will have to log in again.)",
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if ans == QMessageBox.Yes:
        restart_app()


def add_column() -> None:
    """Adds tblUser.DisplaySettings (no-op if present). Only call
    deliberately - dev/prod only with explicit permission."""
    from db import connection
    if COLUMN.lower() in connection.get_columns_map("tblUser"):
        return
    connection.execute(ADD_COLUMN_SQL)
    connection._COLUMNS_MAP_CACHE.clear()


# ── listeners ────────────────────────────────────────────────────────────
def add_listener(method: Callable[[], None]) -> None:
    """Registers a bound method weakly (tables come and go with tabs)."""
    try:
        _listeners.append(weakref.WeakMethod(method))
    except TypeError:
        _listeners.append(lambda m=method: m)


def _notify() -> None:
    alive = []
    for ref in _listeners:
        fn = ref()
        if fn is None:
            continue
        try:
            fn()
        except RuntimeError:
            continue  # C++ object already deleted
        except Exception:
            pass
        alive.append(ref)
    _listeners[:] = alive
