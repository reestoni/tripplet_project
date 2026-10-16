# ui/recent_series.py
"""Recently opened trial series (Nutzerwunsch 2026-10-16).

Sidebar -> "Recent" (one line under Help, on purpose not a whole section -
the sidebar should not get crowded): a small menu with the last series
opened in Show Experiment; click = open in this tab, Ctrl+click = new tab.
Stored per user in the display settings ("recent_series" in
tblUser.DisplaySettings, ui/display_prefs.py) - follows the login to every
PC. Series opened from the recycle bin preview are not remembered; a series
that no longer exists is dropped from the list when it is clicked.
"""
from __future__ import annotations

from typing import Any, Dict, List


def entries() -> List[Dict[str, Any]]:
    from ui import display_prefs
    return list(display_prefs.current().get("recent_series") or [])


def remember(exp_pk: Any, series_pk: Any, experiment_id: str, series_name: str = "") -> None:
    try:
        from ui import display_prefs
        e = {"exp": int(exp_pk), "series": int(series_pk), "eid": str(experiment_id or ""),
             "name": str(series_name or "")}
        rest = [x for x in entries() if x.get("series") != e["series"]]
        display_prefs.update(quiet=True, recent_series=[e] + rest[:display_prefs.RECENT_MAX - 1])
    except Exception:
        pass  # never let the list get in the way of opening a series


def forget(series_pk: Any) -> None:
    try:
        from ui import display_prefs
        display_prefs.update(quiet=True, recent_series=[x for x in entries() if x.get("series") != int(series_pk)])
    except Exception:
        pass


def label(e: Dict[str, Any], max_name: int = 0) -> str:
    name = (e.get("name") or "").strip()
    if max_name and len(name) > max_name:
        name = name[:max_name - 1].rstrip() + "…"
    return f"{e.get('eid') or e.get('series')}" + (f"   {name}" if name else "")


def series_exists(series_pk: int) -> bool:
    try:
        from db.connection import fetch_all
        return bool(fetch_all("SELECT ID FROM tblTrialSeries WHERE ID = ?", [int(series_pk)]))
    except Exception:
        return True  # can't tell (e.g. connection hiccup) - let the normal open handle it
