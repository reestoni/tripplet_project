from __future__ import annotations
# ui/widgets/help_ai.py
"""KI-Antwort fuer die Hilfe-Suche - Etappe 2 (Nutzerwunsch 2026-10-13).

Nur fuer Nutzer mit KI-Zugang: tblUser.api_key_enc gesetzt und Monats-
kontingent nicht erschoepft - geprueft ueber die bestehende
ui.advisor_worker.load_api_key() (dieselbe Logik wie Athena / Lab Assistant).
Verbrauch wird ueber update_token_usage() ins selbe Kontingent gebucht.

Ablauf: Die Hilfetexte aller Screens (in der Sprache des Hilfe-Fensters)
gehen als gecachter System-Prompt mit; Claude antwortet als strukturiertes
JSON mit Kurzantwort + Verweis auf genau einen Hilfe-Eintrag (Enum aus den
vorhandenen Eintrags-Keys - "Take me there" kann also nie ins Leere fuehren)
oder "none", wenn die Hilfe die Frage nicht abdeckt.

Kontingent: gecachte Tokens kosten ~1/10 und werden deshalb zu 1/10
gezaehlt (sonst waere ein Monatslimit wegen der ~20k Tokens Hilfetext pro
Frage sehr schnell aufgebraucht, obwohl es kaum etwas kostet).
"""

from PySide6.QtCore import QObject, QThread, Signal

# prompt, schema, quota accounting and ask() live in the Qt-free ui/help_ai_core.py
# (shared with the web app) - re-exported here
from ui.help_ai_core import (  # noqa: F401
    MODEL, MAX_TOKENS, FALLBACK_BETA, LANG_NAMES, SYSTEM_RULES, _plain, build_knowledge, response_schema,
    billed_tokens, ask,
)


def has_ai_access() -> bool:
    """True, wenn der eingeloggte Nutzer einen KI-Schluessel und noch
    Kontingent hat (gleiche Pruefung wie Athena / Lab Assistant)."""
    try:
        from ui.advisor_worker import load_api_key
        return bool(load_api_key())
    except Exception:
        return False


class HelpAiWorker(QObject):
    """Fuehrt ask() im Hintergrund aus (UI bleibt bedienbar)."""
    finished = Signal(dict)

    def __init__(self, question: str, lang: str, api_key: str):
        super().__init__()
        self._q, self._lang, self._key = question, lang, api_key

    def run(self) -> None:
        try:
            result = ask(self._q, self._lang, self._key)
        except Exception as e:  # nie die UI abstuerzen lassen
            result = {"error": f"AI request failed: {e}"}
        u = result.get("usage")
        if u:
            try:
                from ui.advisor_worker import update_token_usage
                update_token_usage(u["input"], u["output"])
            except Exception:
                pass
        self.finished.emit(result)


def start_worker(parent: QObject, question: str, lang: str, api_key: str, on_done) -> QThread:
    """Startet HelpAiWorker in einem QThread; on_done(result) im UI-Thread."""
    thread = QThread(parent)
    worker = HelpAiWorker(question, lang, api_key)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(on_done)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread._worker = worker  # Referenz halten
    thread.start()
    return thread
