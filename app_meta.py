# app_meta.py
"""Globale Anwendungs-Metadaten und Laufzeit-Benutzerkontext für TrippleT.

Dieses Modul ist die einzige Quelle der Wahrheit für:
  - Versionsinformationen (APP_VERSION)
  - Den aktuell eingeloggten Benutzer (current_user)
  - Berechtigungsprüfungen (access_level, is_admin_level, usw.)
  - Den globalen Quick-Search-Callback (open_quick_search)

Alle Screens und Widgets importieren dieses Modul direkt, da es keinen
komplexen State enthält und keinen Widget-Lifecycle hat.

Zugriffsebenen (tblAccessRight.AccessLevel):
  - 0: Kein Zugang / nicht eingeloggt
  - 1: Lesezugriff
  - 2: Schreibzugriff
  - 3: Admin (inkl. Benutzerverwaltung)
  - 4: Superuser (alle Funktionen, inkl. Löschoperationen)
"""

APP_NAME = "TrippleT"
APP_VERSION = "4.6.0"          # <— hier künftig nur diese Zahl ändern
APP_COPYRIGHT = "© 2026 Heberlein Technology AG"

# Callback zum Aktualisieren des Bell-Badges (wird von main.py gesetzt)
refresh_bell: callable = lambda: None


def footer_text() -> str:
    """Gibt den Versiontext für die Footer-Leiste zurück, z.B. ``"v 4.4.1 © 2026 Heberlein Technology AG"``."""
    return f"v {APP_VERSION} {APP_COPYRIGHT}"


# ---------------------------------------------------------------------------
# Aktuell eingeloggter Benutzer
# ---------------------------------------------------------------------------
# Wird in screen_login.py nach erfolgreichem Login befüllt.
# Alle Felder sind initial None/0/False (nicht eingeloggt).
current_user: dict = {
    "id": None,               # tblUser.ID (int)
    "username": None,         # tblUser.Username (str)
    "first_name": None,       # tblUser.FirstName (str)
    "last_name": None,        # tblUser.LastName (str)
    "access_level": 0,        # tblAccessRight.AccessLevel (int, 0–4)
    "access_right": None,     # tblAccessRight.AccessRight Anzeigename, z.B. "Admin"
    "admin_box": False,       # tblUser.AdminBox – zusätzliches Admin-Flag
    "accent_colour": None,    # tblUser.AccentColour – Hex-Farbe oder None für Default
}


def access_level() -> int:
    """Gibt den AccessLevel des aktuell eingeloggten Benutzers zurück (0 wenn unbekannt)."""
    try:
        return int(current_user.get("access_level") or 0)
    except Exception:
        return 0


def is_admin_level() -> bool:
    """Gibt True zurück wenn der Benutzer Admin-Rechte hat (AccessLevel >= 3)."""
    return access_level() >= 3


def can_use_admin_box() -> bool:
    """Gibt True zurück wenn Admin-Features verfügbar sind.

    Entweder durch AccessLevel >= 3 ODER durch das spezielle AdminBox-Flag
    in tblUser.AdminBox (für Benutzer mit erhöhten Rechten ohne vollen Admin-Level).
    """
    try:
        return is_admin_level() or bool(current_user.get("admin_box"))
    except Exception:
        return is_admin_level()


def is_superuser_level() -> bool:
    """Gibt True zurück wenn der Benutzer Superuser-Rechte hat (AccessLevel >= 4)."""
    return access_level() >= 4


# ---------------------------------------------------------------------------
# Globaler Quick-Search-Callback
# ---------------------------------------------------------------------------
# Wird von MainWindow gesetzt sobald der Quick-Search-Screen initialisiert ist.
# Alle HeaderBars rufen ``open_quick_search()`` auf wenn der 🔍-Button geklickt wird.
# None = Quick Search noch nicht registriert (Button im Header bleibt stumm).
open_quick_search = None   # callable or None

# Wird von MainWindow gesetzt sobald die Tab-Navigation (TabbedNavigator)
# existiert - siehe ui/widgets/sidebar_nav.py::_wire_tab_capable_click().
# None = noch nicht registriert (Sidebar behandelt dann jeden Klick normal,
# kein Schutz gepinnter Vergleichs-Tabs vor App-Start).
is_active_tab_pinned = None   # callable[[], bool] or None