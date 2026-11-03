# ui/pathutil.py
"""Hilfsfunktionen zur Ermittlung des Anwendungs-Wurzelverzeichnisses.

Wird benötigt, um Asset-Pfade (Icons, Bilder) korrekt aufzulösen – sowohl
im Entwicklungsmodus (direkter Python-Start aus VS Code) als auch in
gepackten Builds (PyInstaller onefile/onedir).
"""

import os
import sys


def app_root() -> str:
    """Gibt das Wurzelverzeichnis der Anwendung zurück.

    Berücksichtigt drei Laufzeitkontexte:
    - PyInstaller onefile: Ressourcen liegen in sys._MEIPASS (temporäres Entpack-Verzeichnis)
    - PyInstaller onedir:  Ressourcen liegen neben der .exe (sys.executable)
    - Entwicklung:         Ressourcen liegen ein Verzeichnis über dieser Datei (ttt/)
    """
    if hasattr(sys, "_MEIPASS"):      # PyInstaller onefile/onedir
        return sys._MEIPASS
    if getattr(sys, "frozen", False):  # onedir
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def resource_path(rel_path: str) -> str:
    """Gibt den absoluten Pfad zu einer Ressource zurück.

    Args:
        rel_path: Relativer Pfad zur Ressource, z.B. ``"assets/icons/home.png"``.
                  Schrägstriche werden automatisch in OS-Trennzeichen umgewandelt.

    Returns:
        Absoluter Pfad als String, direkt nutzbar für QPixmap(), QIcon() usw.
    """
    return os.path.join(app_root(), rel_path.replace("/", os.sep))


def web_base_url():
    """Basis-URL für QWebEngine-Seiten aus setHtml(): relative <script src> zeigen
    auf assets/js (Plotly liegt lokal, damit Charts ohne Internet funktionieren)."""
    from PySide6.QtCore import QUrl
    return QUrl.fromLocalFile(resource_path("assets/js") + "/")
