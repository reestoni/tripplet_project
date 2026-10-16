# ui/lab_assistant_worker.py
"""Lab Assistant - Athena für die GESAMTE Datenbank statt nur eine TrialSeries.

QThread, der einen agentischen Anthropic Tool-Use-Loop fährt: Claude bekommt
ein `run_sql_query`-Werkzeug und kann selbst read-only SQL gegen die laufende
DB (dev_local/dev/prod, je nach TRIPPLET_MODE) ausführen, um freie Fragen über
die gesamte Datenbank zu beantworten - im Gegensatz zu ui/advisor_worker.py's
AdvisorWorker, das einen fixen JSON-Kontext EINER TrialSeries in einem Single-
Shot-Call verschickt (kein Tool-Use dort).

WICHTIG (Sicherheit): es gibt in diesem Projekt keinen separaten read-only
DB-User/Credential (db/connection.py's _load_secrets() liefert immer dasselbe
volle Credential-Set für den aktiven Modus, auch für raw_mysql_connect()) -
die Absicherung "nur lesende SELECTs, keine Schreibzugriffe, kein Zugriff auf
tbluser" passiert deshalb komplett hier in validate_readonly_sql(), nicht auf
DB-Ebene. Kein Ersatz für einen echten read-only DB-User, aber die einzige
verfügbare Absicherung in diesem Projekt (nicht angenommen, sondern gezielt
recherchiert, bevor das gebaut wurde).

Wiederverwendet load_api_key()/update_token_usage() sowie den DTY-Fachwissen-
Block aus ADVISOR_SYSTEM_PROMPT direkt aus advisor_worker.py (kein Duplikat) -
nur der Tool-Use-Loop selbst ist neu, weil strukturell grundverschieden vom
Single-Shot-Call dort.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Optional

from PySide6.QtCore import QThread, Signal

from db.connection import fetch_all, get_columns_map
from ui.advisor_worker import ADVISOR_SYSTEM_PROMPT, load_api_key, update_token_usage

__all__ = [
    "load_api_key",
    "validate_readonly_sql",
    "run_sql_tool",
    "build_schema_summary",
    "build_system_prompt",
    "LabAssistantWorker",
    "MAX_TOOL_ITERATIONS",
    "MAX_ROWS_PER_QUERY",
]


# ---------------------------------------------------------------------------
# SQL-Sicherheit - siehe Moduldocstring: die einzige Absicherung, es gibt
# keinen read-only DB-User in diesem Projekt.
# ---------------------------------------------------------------------------

MAX_TOOL_ITERATIONS = 6
MAX_ROWS_PER_QUERY = 200

_WRITE_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|"
    r"REPLACE|RENAME|CALL|EXEC|EXECUTE|MERGE|LOCK|UNLOCK|ATTACH|DETACH|"
    r"PRAGMA|VACUUM|LOAD)\b",
    re.IGNORECASE,
)
_OUTFILE_PATTERN = re.compile(r"INTO\s+(OUTFILE|DUMPFILE)", re.IGNORECASE)
_SELECT_OR_WITH = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)
_LIMIT_KEYWORD = re.compile(r"\bLIMIT\b", re.IGNORECASE)

# tbluser hält pw_hash/api_key_enc - darf nie an eine Drittanbieter-API
# (Anthropic) gehen. Blockt die ganze Tabelle statt einzelner Spalten, weil
# ein reiner Spaltennamen-Blocklist "SELECT * FROM tbluser" nicht erkennen
# würde. Kann bei Bedarf später gelockert werden (z.B. nur bestimmte Spalten
# erlauben) - für v1 bewusst die simple, sichere Variante. \b-Wortgrenzen statt
# einer reinen Substring-Prüfung, damit z.B. ein hypothetisches
# "tbluserdirectory" nicht faelschlich mitgesperrt wird.
_BLOCKED_TABLE_PATTERNS = (re.compile(r"\btbluser\b", re.IGNORECASE),)


def validate_readonly_sql(sql: str) -> str:
    """Gibt die bereinigte, sichere SQL zurück oder wirft ValueError.

    Fügt automatisch ein `LIMIT {MAX_ROWS_PER_QUERY + 1}` an, falls die Query
    noch kein eigenes LIMIT hat (die +1 erlaubt run_sql_tool() zuverlässig zu
    erkennen, ob mehr Zeilen existiert hätten) - Performance-/Kosten-Bremse,
    damit eine unbedachte "SELECT * FROM tbllaboritematlab" (~48'700 Zeilen,
    siehe CLAUDE.md) nicht komplett in Python-Speicher gezogen wird, bevor sie
    ohnehin auf MAX_ROWS_PER_QUERY gekappt würde. Ein von Claude explizit
    gesetztes LIMIT wird nie überschrieben.

    Bekannte Grenze: ein Semikolon INNERHALB eines String-Literals (z.B.
    "WHERE Name = 'a;b'") wird fälschlich als Mehrfach-Statement erkannt und
    abgelehnt - akzeptiert für v1, da harmlos (Claude bekommt den Fehler als
    tool_result zurück und kann die Query anpassen, kein Sicherheitsproblem,
    nur ein seltener False-Positive).
    """
    if not sql or not sql.strip():
        raise ValueError("Empty query.")
    cleaned = sql.strip()
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()
    if ";" in cleaned:
        raise ValueError("Only a single SQL statement is allowed (no ';' inside the query).")
    if not _SELECT_OR_WITH.match(cleaned):
        raise ValueError("Only SELECT (or WITH ... SELECT) statements are allowed.")
    if _WRITE_KEYWORDS.search(cleaned):
        raise ValueError("Write/DDL statements are not allowed - read-only access only.")
    if _OUTFILE_PATTERN.search(cleaned):
        raise ValueError("Exporting query results to a file is not allowed.")
    for pattern in _BLOCKED_TABLE_PATTERNS:
        if pattern.search(cleaned):
            raise ValueError("Access to 'tbluser' is not allowed (contains credentials/secrets).")
    if not _LIMIT_KEYWORD.search(cleaned):
        cleaned = f"{cleaned} LIMIT {MAX_ROWS_PER_QUERY + 1}"
    return cleaned


def run_sql_tool(query: str) -> dict:
    """Führt eine von Claude generierte SQL-Abfrage sicher aus (siehe
    validate_readonly_sql()) und kappt das Ergebnis zusätzlich clientseitig
    auf MAX_ROWS_PER_QUERY (nicht per SQL-Rewrite/Subquery - robuster gegen
    beliebige, von Claude generierte Query-Formen, siehe Plan)."""
    try:
        safe_sql = validate_readonly_sql(query)
        rows = fetch_all(safe_sql, [])
    except Exception as e:
        return {"error": str(e)}
    truncated = len(rows) > MAX_ROWS_PER_QUERY
    return {
        "row_count": len(rows),
        "truncated": truncated,
        "rows": rows[:MAX_ROWS_PER_QUERY],
    }


# ---------------------------------------------------------------------------
# Schema-Zusammenfassung für den System-Prompt
# ---------------------------------------------------------------------------

_EXCLUDED_FROM_SCHEMA = {"tbluser", "tblaccessright"}
_schema_summary_cache: Optional[str] = None


def build_schema_summary() -> str:
    """Kompakte 'Tabelle: Spalten'-Liste für den System-Prompt.

    Nutzt die volle FK-Closure über ROOT_TABLES+EXTRA_REFERENCE_TABLES aus
    db/offline_schema.py (get_offline_table_closure()) statt nur der beiden
    rohen Seed-Listen - die Closure zieht u.a. tblexperimente/tblmaschine/
    tblmaterial/tblgarntyp/tblcolour automatisch mit rein (echte FK-Ziele,
    z.B. tbltrialseries.ExperimentID -> tblexperimente), während die reinen
    Seed-Listen diese für einen Ganze-DB-Chat zentralen Tabellen gar nicht
    enthalten würden. NICHT auf Modulebene berechnet (würde bei jedem Import
    dieses Moduls - z.B. schon beim Start von main.py, das die Screen-Klasse
    importieren muss - eine eigene rohe MySQL-Verbindung öffnen, siehe
    get_offline_table_closure()'s raw_mysql_connect(); genau das Muster, das
    beim Login-Crash 2026-08-24 als Ursache für unnötige Eager-Kosten bei
    JEDEM Login identifiziert wurde) - wird erst beim ersten tatsächlichen
    Chat-Aufruf berechnet (aus LabAssistantWorker.run(), also im Hintergrund-
    Thread), danach für die Prozesslaufzeit gecacht (gleiche Begründung wie
    db.connection._TABLE_EXISTS_CACHE - das Schema ändert sich während einer
    laufenden Session nicht)."""
    global _schema_summary_cache
    if _schema_summary_cache is not None:
        return _schema_summary_cache

    from db.offline_schema import EXTRA_REFERENCE_TABLES, ROOT_TABLES, get_offline_table_closure
    try:
        tables, _fk_map = get_offline_table_closure()
    except Exception:
        # get_offline_table_closure() braucht eine eigene, frische MySQL-
        # Verbindung (raw_mysql_connect) - fällt z.B. gegen einen nicht
        # unterstützten Modus zurück auf die rohen Seed-Listen, die nur das
        # bereits gecachte get_columns_map() brauchen.
        seen = set()
        tables = []
        for t in ROOT_TABLES + EXTRA_REFERENCE_TABLES:
            if t not in seen:
                seen.add(t)
                tables.append(t)

    lines = []
    for t in tables:
        if t in _EXCLUDED_FROM_SCHEMA:
            continue
        try:
            cols_map = get_columns_map(t)
        except Exception:
            continue
        if not cols_map:
            continue
        col_names = sorted(cols_map.values())
        lines.append(f"- {t}: {', '.join(col_names)}")

    _schema_summary_cache = "\n".join(lines)
    return _schema_summary_cache


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

def _extract_dty_domain_knowledge() -> str:
    """Holt den DTY-Fachwissen-Block aus advisor_worker.ADVISOR_SYSTEM_PROMPT
    (Wiederverwendung statt Neuformulierung) - degradiert defensiv auf '',
    falls die Marker-Strings dort mal umformuliert werden."""
    text = ADVISOR_SYSTEM_PROMPT
    start = text.find("DTY-FACHDOMÄNE")
    from ui.advisor_worker import LANGUAGE_RULE_MARKER
    end = text.find(LANGUAGE_RULE_MARKER)
    if start == -1 or end == -1 or end <= start:
        return ""
    return text[start:end].strip()


def build_system_prompt() -> str:
    """Baut den vollständigen System-Prompt (Schema + Fachwissen). Wird pro
    Chat-Nachricht einmal aufgerufen, nicht bei Modul-Import (siehe
    build_schema_summary()'s Docstring)."""
    domain = _extract_dty_domain_knowledge()
    domain_block = f"\n\n{domain}\n" if domain else ""
    return f"""Du bist Athena 🦉, Senior Textile Process Engineer bei Heberlein Technology AG.
Du beantwortest freie Fragen über die GESAMTE TrippleT-Labordatenbank (nicht
nur eine einzelne TrialSeries). Denke Schritt für Schritt, sei
direkt, keine Füllsätze, Zahlen immer konkret nennen.

Du hast ein Werkzeug `run_sql_query` (eine einzelne read-only SQL-SELECT-
Abfrage gegen die Datenbank). Nutze es, um alles nachzuschlagen, was du für
eine präzise Antwort brauchst - rate nichts, das du stattdessen abfragen
kannst.

REGELN FÜR run_sql_query:
  - Nur SELECT (oder WITH ... SELECT), keine Schreibzugriffe - werden ohnehin
    serverseitig abgelehnt.
  - Die Tabelle `tbluser` ist gesperrt (enthält Zugangsdaten) - frag nicht danach.
  - Ergebnisse sind auf {MAX_ROWS_PER_QUERY} Zeilen pro Abfrage begrenzt
    (`truncated: true` im Ergebnis zeigt an, wenn mehr Zeilen existieren -
    dann die Abfrage gezielter eingrenzen, z.B. mit WHERE/GROUP BY/Aggregation).
  - Nutze maximal {MAX_TOOL_ITERATIONS} Abfragen für eine einzelne Antwort -
    plane deine Abfragen daher gezielt (z.B. lieber eine aggregierte Abfrage
    mit GROUP BY/COUNT als viele einzelne).
  - Bei einem Fehler in der Antwort: die Abfrage anpassen und erneut versuchen,
    nicht aufgeben.
  - tbltrial-Zeilen mit IsReference = 1 sind KEINE Versuche, sondern
    Referenzmuster (z.B. Originalspule eines Kunden als Benchmark, Name in
    ReferenceName). Für Statistiken/Auswertungen über Versuche immer mit
    COALESCE(IsReference, 0) = 0 ausschliessen - ausser die Frage zielt
    ausdrücklich auf Referenzmuster/Kundenmuster.

VERFÜGBARES SCHEMA (Tabelle: Spalten):
{build_schema_summary()}
{domain_block}
Language: answer in the language the user writes in (German question -> German answer, Spanish -> Spanish, ...). If there is no question (e.g. an automatic analysis) or it is unclear, answer in English.
Fachbegriffe verwenden. Bei mehrzeiligen
Tabellen-Ergebnissen: fasse die relevanten Zahlen in einer kompakten Markdown-
Tabelle zusammen statt jede Zeile einzeln aufzuzählen."""


# ---------------------------------------------------------------------------
# Worker Thread
# ---------------------------------------------------------------------------

class LabAssistantWorker(QThread):
    """Non-blocking QThread für den agentischen Anthropic Tool-Use-Loop.

    Anders als AdvisorWorker (ein einzelner Call pro Frage) kann diese Klasse
    mehrere Anthropic-Calls pro Nutzerfrage machen, dazwischen jeweils
    run_sql_tool() ausführen und das Ergebnis zurückspielen, bis Claude eine
    finale Text-Antwort liefert (oder MAX_TOOL_ITERATIONS erreicht ist).
    """

    result_ready = Signal(str)
    error_occurred = Signal(str)
    # Emittiert die SQL VOR der Ausführung - fürs UI-Transparenz-/Audit-Log
    # (der Nutzer soll sehen können, was Athena tatsächlich abfragt).
    tool_call_started = Signal(str)

    _API_URL = "https://api.anthropic.com/v1/messages"
    _MODEL = "claude-sonnet-5"
    _MAX_TOKENS = 4096

    _TOOLS = [{
        "name": "run_sql_query",
        "description": (
            "Run a single read-only SQL SELECT statement against the TrippleT "
            "lab database and get the resulting rows back as JSON. Only SELECT "
            "(or WITH ... SELECT) is allowed - no writes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A single read-only SQL SELECT statement.",
                }
            },
            "required": ["query"],
        },
    }]

    def __init__(self, api_key: str, history: Optional[list] = None, user_question: str = ""):
        super().__init__()
        self._api_key = api_key
        self._history = list(history) if history else []
        self._user_question = user_question

    def _post(self, messages: list, system_prompt: str, with_tools: bool) -> dict:
        payload = {
            "model": self._MODEL,
            "max_tokens": self._MAX_TOKENS,
            "system": system_prompt,
            "messages": messages,
        }
        if with_tools:
            payload["tools"] = self._TOOLS

        req = urllib.request.Request(
            self._API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def run(self):
        try:
            system_prompt = build_system_prompt()
            messages = list(self._history) + [{"role": "user", "content": self._user_question}]
            total_in = total_out = 0
            content_blocks: list = []

            for _iteration in range(MAX_TOOL_ITERATIONS):
                result = self._post(messages, system_prompt, with_tools=True)
                usage = result.get("usage", {})
                total_in += usage.get("input_tokens", 0)
                total_out += usage.get("output_tokens", 0)
                content_blocks = result.get("content", [])

                tool_use_blocks = [b for b in content_blocks if b.get("type") == "tool_use"]
                if not tool_use_blocks:
                    break

                messages.append({"role": "assistant", "content": content_blocks})
                tool_result_blocks = []
                for tb in tool_use_blocks:
                    query = (tb.get("input") or {}).get("query", "")
                    self.tool_call_started.emit(query)
                    output = run_sql_tool(query)
                    tool_result_blocks.append({
                        "type": "tool_result",
                        "tool_use_id": tb.get("id"),
                        "content": json.dumps(output, ensure_ascii=False, default=str),
                        "is_error": "error" in output,
                    })
                messages.append({"role": "user", "content": tool_result_blocks})
            else:
                # for-Schleife durchgelaufen OHNE break = Iterationslimit
                # erreicht, ohne dass Claude fertig war. Ein letzter Call
                # OHNE tools erzwingt eine reine Text-Antwort statt eines
                # weiteren tool_use.
                result = self._post(messages, system_prompt, with_tools=False)
                usage = result.get("usage", {})
                total_in += usage.get("input_tokens", 0)
                total_out += usage.get("output_tokens", 0)
                content_blocks = result.get("content", [])

            update_token_usage(total_in, total_out)

            text = "\n".join(
                b.get("text", "") for b in content_blocks if b.get("type") == "text"
            ).strip()

            if not text:
                self.error_occurred.emit("Keine Antwort vom Modell erhalten.")
                return

            self.result_ready.emit(text)

        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8")
            except Exception:
                pass
            self.error_occurred.emit(f"HTTP {e.code}: {e.reason}\n\n{body}")

        except urllib.error.URLError as e:
            self.error_occurred.emit(
                f"Netzwerkfehler: {e.reason}\n\n"
                "Check whether a connection to api.anthropic.com is possible."
            )

        except Exception as e:
            self.error_occurred.emit(f"Something unexpected went wrong:\n{type(e).__name__}: {e}")
