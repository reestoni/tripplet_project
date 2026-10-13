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

import json
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, QThread, Signal

MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 2000
# Server-side Fallback bei Ablehnung durch die Sicherheitsfilter (Claude API).
FALLBACK_BETA = "server-side-fallback-2026-07-01"

LANG_NAMES = {"en": "English", "de": "German", "es": "Spanish"}

SYSTEM_RULES = """You are the help assistant inside TrippleT, a desktop application for a textile/yarn \
laboratory (trial series, trials, jets, yarns, lab machines, yarn stock).

Answer the user's question ONLY from the help entries below. Rules:
- Pick the single help entry that best answers the question and return its key in "entry_key".
  If no entry answers it, return "none" and say briefly that the help does not cover this.
- "answer": 1-4 short sentences in the user's language (the language the question is written in).
  Name the screen and the concrete steps. Keep button, menu and column names exactly as written
  in the help (they are English in the app, e.g. [New spool(s)], Add Trial Series).
- Do not invent buttons, screens or features that are not in the help entries.
- No Markdown, no lists with symbols; plain sentences.
- "confident": true if the chosen entry clearly answers the question, otherwise false.

HELP ENTRIES (key, screen, question, steps, note):
"""


def has_ai_access() -> bool:
    """True, wenn der eingeloggte Nutzer einen KI-Schluessel und noch
    Kontingent hat (gleiche Pruefung wie Athena / Lab Assistant)."""
    try:
        from ui.advisor_worker import load_api_key
        return bool(load_api_key())
    except Exception:
        return False


def _plain(html_text: str) -> str:
    from ui.widgets.help_search import normalize_display
    return normalize_display(html_text)


def build_knowledge(lang: str) -> Dict[str, object]:
    """Hilfetexte als Text fuer den System-Prompt + Liste gueltiger Keys."""
    from ui.widgets.help_search import get_index, SCREEN_NAMES
    lines: List[str] = []
    keys: List[str] = []
    for e in get_index():
        if e.lang != lang:
            continue
        keys.append(e.key)
        steps = " ".join(f"{i}. {_plain(s)}" for i, s in enumerate(e.steps, 1))
        note = f" Note: {_plain(e.note)}" if e.note else ""
        lines.append(f"[{e.key}] {SCREEN_NAMES.get(e.screen, e.screen)} | {_plain(e.question)} | {steps}{note}")
    return {"text": "\n".join(lines), "keys": keys}


def response_schema(keys: List[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "entry_key": {"type": "string", "enum": list(keys) + ["none"]},
            "confident": {"type": "boolean"},
        },
        "required": ["answer", "entry_key", "confident"],
        "additionalProperties": False,
    }


def billed_tokens(usage) -> Dict[str, int]:
    """Tokens fuers Kontingent: Cache-Lesungen zu 1/10 (entspricht dem Preis)."""
    inp = int(getattr(usage, "input_tokens", 0) or 0)
    cw = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
    cr = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
    out = int(getattr(usage, "output_tokens", 0) or 0)
    return {"input": inp + cw + (cr + 9) // 10, "output": out}


def ask(question: str, lang: str, api_key: str, client=None) -> dict:
    """Fragt Claude. Rueckgabe: {"answer", "entry_key", "confident", "usage"}
    oder {"error": "..."}. `client` ist fuer Tests injizierbar."""
    import anthropic
    kb = build_knowledge(lang)
    if not kb["keys"]:
        return {"error": "No help texts available."}
    if client is None:
        client = anthropic.Anthropic(api_key=api_key, max_retries=2, timeout=60.0)
    system = [{
        "type": "text",
        "text": SYSTEM_RULES + kb["text"],
        "cache_control": {"type": "ephemeral"},  # Hilfetexte sind pro Sprache stabil
    }]
    try:
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            betas=[FALLBACK_BETA],
            fallbacks="default",
            system=system,
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": response_schema(kb["keys"])},
            },
            messages=[{"role": "user", "content": question.strip()}],
        )
    except anthropic.AuthenticationError:
        return {"error": "The AI key is not valid. Please contact an admin."}
    except anthropic.PermissionDeniedError:
        return {"error": "The AI key has no permission for this model."}
    except anthropic.RateLimitError:
        return {"error": "The AI is busy right now. Please try again in a minute."}
    except anthropic.APIStatusError as e:
        return {"error": f"AI error ({e.status_code}). Please try again later."}
    except anthropic.APIConnectionError:
        return {"error": "No connection to the AI service (api.anthropic.com)."}

    usage = billed_tokens(resp.usage)
    if resp.stop_reason == "refusal":
        return {"error": "The AI could not answer this question.", "usage": usage}
    text = next((b.text for b in resp.content if getattr(b, "type", "") == "text"), "")
    try:
        data = json.loads(text)
    except Exception:
        return {"error": "The AI answer could not be read.", "usage": usage}
    if data.get("entry_key") not in kb["keys"]:
        data["entry_key"] = "none"
    data["usage"] = usage
    return data


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
