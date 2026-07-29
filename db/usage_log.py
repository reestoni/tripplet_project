"""usage_log.py - Nutzungs-Tracking fuer den Admin-Stats-Screen.

Best-effort: log_usage_event() darf NIE eine Exception nach aussen werfen
oder die UI blockieren - ein fehlgeschlagener Log-Insert (z.B. Tabelle
fehlt noch auf diesem DB-Modus) ist kein Grund, dem User eine Aktion zu
verweigern.

EventType-Konvention:
  "login"       - erfolgreicher Login
  "screen_open" - ein Screen wird im QStackedWidget aktiv (main.py)
  "feature"     - gezielt instrumentierte, "grosse" Aktionen (PDF-Export,
                  Advisor/Athena, Fill-Range-Bulk-Edit, YarnScope-Tab, ...)
"""
from __future__ import annotations


def log_usage_event(event_type: str, event_name: str, detail: str = "") -> None:
    """Schreibt einen Nutzungs-Log-Eintrag. Schlaegt niemals sichtbar fehl."""
    try:
        import app_meta
        from db.connection import execute, table_exists

        if not table_exists("tblUsageLog"):
            return

        user = getattr(app_meta, "current_user", {}) or {}
        user_id = user.get("id")
        username = user.get("username")

        execute(
            "INSERT INTO tblUsageLog (UserID, Username, EventType, EventName, Detail) "
            "VALUES (?, ?, ?, ?, ?)",
            [user_id, username, event_type, event_name, detail],
        )
    except Exception:
        pass
