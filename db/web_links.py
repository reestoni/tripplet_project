"""Links into the web app (TrippleT Web) - one format for both apps.

The web app builds the same links from the address in the browser; the desktop needs to know the address of the
web server: environment variable ``TRIPPLET_WEB_URL`` (e.g. ``https://tripplet.example.local``), otherwise the
default of the current mode below. Without an address the desktop greys out "Copy web link".

Link format (the web pages read these parameters):
    /series/<id>[?tab=<key>][&trial=<trial id>]    Show Experiment, optional tab and trial column
    /series/<id>/report?report=<report id>          saved report of a series
    /tools/canvas?board=<board id>                  Canvas board
Tab keys: ``machine``, ``rd``, ``notes`` and the keys of ``db.series_tables.LAB_TABS``.
"""
from __future__ import annotations

import os
from typing import Optional
from urllib.parse import urlencode

# Web address per TRIPPLET_MODE. dev/prod: fill in once the server in the company network exists.
DEFAULT_BASE = {
    "dev_local": "http://127.0.0.1:8000",
}


def _mode() -> str:
    try:
        from db.connection import MODE
        return str(MODE)
    except Exception:
        return os.environ.get("TRIPPLET_MODE", "")


def base_url() -> Optional[str]:
    """Address of the web app without trailing slash, or None if unknown."""
    url = (os.environ.get("TRIPPLET_WEB_URL") or "").strip() or DEFAULT_BASE.get(_mode(), "")
    return url.rstrip("/") or None


def _join(path: str, params: dict, base: Optional[str]) -> Optional[str]:
    b = base if base is not None else base_url()
    if not b:
        return None
    q = urlencode({k: v for k, v in params.items() if v not in (None, "")})
    return f"{b.rstrip('/')}{path}" + (f"?{q}" if q else "")


def series_url(series_id: int, tab: Optional[str] = None, trial_id: Optional[int] = None,
               base: Optional[str] = None) -> Optional[str]:
    return _join(f"/series/{int(series_id)}", {"tab": tab, "trial": trial_id}, base)


def report_url(series_id: int, report_id: int, base: Optional[str] = None) -> Optional[str]:
    return _join(f"/series/{int(series_id)}/report", {"report": int(report_id)}, base)


def board_url(board_id: int, base: Optional[str] = None) -> Optional[str]:
    return _join("/tools/canvas", {"board": int(board_id)}, base)
