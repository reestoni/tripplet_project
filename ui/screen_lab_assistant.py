# ui/screen_lab_assistant.py
"""Lab Assistant - Chat-Screen für freie Fragen über die GESAMTE Datenbank.

UI nach dem Vorbild des Chat-Blocks in ui/advisor_tab.py aufgebaut (Output-
QTextEdit mit Markdown-Rendering + AthenaOwl + Chat-Input-Zeile + Senden-Button
+ Status-Label) - dort für EINE TrialSeries, hier ohne jeden Series-/Trial-
Kontext (das ist der ganze Witz dieses Screens). Die eigentliche Tool-Use-Logik
lebt in ui/lab_assistant_worker.py (LabAssistantWorker), analog zu
AdvisorWorker in advisor_worker.py.

Persistenz (Nutzerwunsch, 2026-08-25: "die ergebnisse sind weg, wenn ich den
screen verlasse", dann "das will ich" auf die Nachfrage nach einer echten
Mehrfach-Sitzungs-Historie): mehrere gespeicherte Chat-Sitzungen pro User in
tblLabAssistantChat (kein UNIQUE mehr auf UserID, siehe CLAUDE.md - analog zu
tblAdvisorReport's Session-Log-Muster, nur ohne Bezug zu einer TrialSeries).
Beim Öffnen des Screens wird automatisch die zuletzt aktualisierte Sitzung
geladen; "🕘 History" listet alle gespeicherten Sitzungen dieses Users zum
Zurückspringen; "🆕 New Chat" startet lediglich einen frischen Verlauf (setzt
nur den In-Memory-Zustand zurück) - die bisherige Sitzung bleibt unverändert
in der DB stehen und ist über "History" weiterhin erreichbar, wird NICHT
gelöscht (anders als die erste Version dieses Screens).

Nur für Superuser (AccessLevel >= 4) erreichbar und im Offline-Modus gesperrt
(braucht Netzwerk + volles Schema) - siehe main.py::_go_lab_assistant() und
ui/screen_home.py's _offline_gated_buttons.
"""
from __future__ import annotations

import datetime
import json
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QSizePolicy, QTextEdit, QVBoxLayout, QWidget,
)

import app_meta
from db.connection import execute, execute_insert, fetch_all, new_global_id, table_exists
from ui.advisor_tab import _set_advisor_markdown
from ui.athena_owl import AthenaOwl
from ui.lab_assistant_worker import LabAssistantWorker, load_api_key
from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav

# Wie advisor_tab.py: History auf 3 Turns (6 Einträge) kürzen, erster Turn
# bleibt erhalten - hält den Kontext (und damit die Tokenkosten) pro Frage
# begrenzt, ohne die ursprüngliche Frage aus dem Chat zu verlieren.
_MAX_HISTORY_ENTRIES = 6

# Farbige Inline-Labels statt reiner Textpräfixe (Nutzerwunsch: "meine Frage
# von deiner Antwort besser trennen können") - Qt's setMarkdown() rendert
# eingebettetes Inline-HTML wie <span style="color:..."> zuverlässig (geprüft,
# nicht angenommen: reines Markdown-CSS über document().setDefaultStyleSheet()
# reicht hier NICHT, weil Qt's Markdown-Parser ">"-Blockquotes als normale
# eingerückte <p>-Absätze rendert, nicht als <blockquote>-Element - eine
# blockquote{}-CSS-Regel hätte also keinerlei Effekt gehabt).
_USER_LABEL = '<span style="color:#7dd3fc; font-weight:bold;">🧑 Du</span>'
_ATHENA_LABEL = '<span style="color:#34d399; font-weight:bold;">🦉 Athena</span>'
_THINKING = "⏳ ..."


def _preview_label(row: dict) -> str:
    """Kurze Vorschau fuer einen History-Eintrag: erste Nutzerfrage der
    Sitzung (aus HistoryJSON, nicht aus dem gerenderten Markdown - robuster
    gegen die eingebetteten HTML-Labels/SQL-Audit-Zeilen dort) + Zeitstempel."""
    updated = row.get("UpdatedAt")
    ts = str(updated) if updated else ""
    text = ""
    try:
        history = json.loads(row.get("HistoryJSON") or "[]")
        if history and history[0].get("role") == "user":
            text = history[0].get("content", "")
    except Exception:
        text = ""
    text = (text or "(leerer Chat)").strip().replace("\n", " ")
    if len(text) > 60:
        text = text[:57] + "..."
    return f"{text}\n{ts}" if ts else text


class _ChatHistoryDialog(QDialog):
    """Liste vergangener Lab-Assistant-Chats dieses Users - Klick/Doppelklick
    liefert den gewählten Datensatz zurück (self.selected_row), ändert dabei
    aber nichts an der DB - identisch zum Aufbau von TrialUsageDialog
    (ui/screen_manage_yarn.py, Liste + Klick öffnet)."""

    def __init__(self, rows: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chat-Verlauf")
        self.resize(420, 480)
        self.selected_row: Optional[dict] = None

        layout = QVBoxLayout(self)
        hint = QLabel("Frühere Sitzung auswählen, um sie zu öffnen (der aktuelle Chat bleibt gespeichert).")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.list = QListWidget()
        for row in rows:
            item = QListWidgetItem(_preview_label(row))
            item.setData(Qt.UserRole, row)
            self.list.addItem(item)
        self.list.itemDoubleClicked.connect(lambda _item: self._accept_selected())
        layout.addWidget(self.list, 1)

        btn_row = QHBoxLayout()
        btn_open = QPushButton("Öffnen", objectName="GreenBtn")
        btn_open.clicked.connect(self._accept_selected)
        btn_row.addWidget(btn_open)
        btn_row.addStretch()
        btn_close = QPushButton("Close", objectName="GreyBtn")
        btn_close.clicked.connect(self.reject)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _accept_selected(self):
        item = self.list.currentItem()
        if item is not None:
            self.selected_row = item.data(Qt.UserRole)
            self.accept()


class LabAssistantScreen(QWidget):
    def __init__(self, on_back_home=None, sidebar_callbacks: Optional[dict] = None):
        super().__init__()
        self.on_back_home = on_back_home
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None

        self._history: list = []
        self._output_md: str = ""
        self._chat_row_id: Optional[int] = None
        self._worker: Optional[LabAssistantWorker] = None

        self._build_ui()
        self._load_saved_chat()

    def _refresh_sidebar(self):
        """Baut die Sidebar-Navigation neu auf, falls sich der Access-Level
        seit dem letzten Aufbau geändert hat, sonst nur die Badges (siehe
        ui/widgets/sidebar_nav.py::refresh_lazy_sidebar())."""
        import app_meta
        try:
            level = int((app_meta.current_user or {}).get("access_level") or 0)
        except Exception:
            level = 0
        sidebar_nav.refresh_lazy_sidebar(self, level)

    def showEvent(self, event):
        try:
            self._refresh_sidebar()
        except Exception:
            pass
        super().showEvent(event)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring).
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        body = QFrame()
        body.setStyleSheet("background:#0b0f19;")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        title_row = QHBoxLayout()
        title = QLabel("🦉  Athena · Lab Assistant")
        title.setStyleSheet("color:#f3f4f6; font-size:16px; font-weight:bold; background:transparent;")
        title_row.addWidget(title)
        title_row.addStretch(1)

        btn_history = QPushButton("🕘  History")
        btn_history.setObjectName("GreyBtn")
        btn_history.setToolTip("Frühere Chat-Sitzungen ansehen und wieder öffnen")
        btn_history.clicked.connect(self._open_history)
        title_row.addWidget(btn_history)

        btn_new_chat = QPushButton("🆕  New Chat")
        btn_new_chat.setObjectName("GreyBtn")
        btn_new_chat.setToolTip("Neue Sitzung starten (die bisherige bleibt über 'History' erreichbar)")
        btn_new_chat.clicked.connect(self._new_chat)
        title_row.addWidget(btn_new_chat)
        lay.addLayout(title_row)

        subtitle = QLabel(
            "Stell freie Fragen über die gesamte Labordatenbank - nicht nur eine TrialSeries. "
            "Athena schaut selbst per SQL nach, was sie für die Antwort braucht."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#9ca3af; font-size:11px; background:transparent;")
        lay.addWidget(subtitle)

        # ── Output-Container — Athena schläft hier unten rechts ──────────────
        output_container = QWidget()
        output_container.setMinimumHeight(250)
        output_lay = QVBoxLayout(output_container)
        output_lay.setContentsMargins(0, 0, 0, 0)

        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setStyleSheet(
            "background: #111827; color: #e5e7eb;"
            "font-family: 'Consolas', 'Courier New', monospace;"
            "font-size: 12px; border: 1px solid #374151;"
            "border-radius: 6px; padding: 12px;"
        )
        self._output.document().setDefaultStyleSheet(
            "body { color: #e5e7eb; }"
            "a { color: #7dd3fc; }"
            "code { color: #fbbf24; background: #1f2937; padding: 1px 4px; border-radius: 3px; }"
            "pre { color: #fbbf24; background: #1f2937; }"
            "table { color: #e5e7eb; border-collapse: collapse; }"
            "th, td { border: 1px solid #374151; padding: 4px 8px; }"
            "th { background: #1f2937; }"
            "h1, h2, h3, h4 { color: #f3f4f6; }"
            "strong, b { color: #f9fafb; }"
            "hr { background-color: #374151; }"
        )
        self._output.setPlaceholderText(
            "Stell eine Frage, z.B.:\n\n"
            "  • Welche ATY-Trials hatten in den letzten 3 Monaten einen Bulk Index über 20%?\n"
            "  • Wie viele TrialSeries laufen aktuell im Status 'Backlog'?\n"
            "  • Welche Jets wurden am häufigsten für PES-Garne verwendet?\n\n"
            "Athena fragt die Datenbank selbst per SQL ab, um zu antworten."
        )
        output_lay.addWidget(self._output)
        lay.addWidget(output_container, 1)

        self._athena = AthenaOwl(output_container)
        self._athena.place_sleeping()

        # ── Chat-Input ─────────────────────────────────────────────────────
        chat_frame = QFrame()
        chat_frame.setStyleSheet(
            "QFrame { background:#1a1f2e; border:1px solid #2d3748; border-radius:6px; }"
        )
        chat_lay = QVBoxLayout(chat_frame)
        chat_lay.setContentsMargins(10, 8, 10, 8)
        chat_lay.setSpacing(6)

        chat_lbl = QLabel("Frage an Athena:")
        chat_lbl.setStyleSheet("color:#9ca3af; font-size:11px; background:transparent; border:none;")
        chat_lay.addWidget(chat_lbl)

        chat_input_row = QHBoxLayout()
        self._chat_input = QTextEdit()
        self._chat_input.setFixedHeight(60)
        self._chat_input.setPlaceholderText(
            "z.B. «Welche Maschine hat dieses Jahr am meisten ATY-Trials gefahren?»"
        )
        self._chat_input.setStyleSheet(
            "background:#111827; color:#e5e7eb; font-size:12px;"
            "border:1px solid #374151; border-radius:4px; padding:6px;"
        )
        chat_input_row.addWidget(self._chat_input, 1)

        self._btn_send = QPushButton("Senden  ↵")
        self._btn_send.setFixedSize(90, 60)
        self._btn_send.setStyleSheet(
            "QPushButton { background:#39A650; color:#ffffff; border:none;"
            "border-radius:5px; font-size:13px; font-weight:bold; }"
            "QPushButton:hover { background:#2e8a42; }"
            "QPushButton:disabled { background:#1e293b; color:#4b5563; border:1px solid #374151; }"
        )
        self._btn_send.clicked.connect(self._send_question)
        chat_input_row.addWidget(self._btn_send)
        chat_lay.addLayout(chat_input_row)

        lay.addWidget(chat_frame)

        self._status = QLabel("")
        self._status.setStyleSheet("color: #9ca3af; font-size: 10px; background:transparent;")
        lay.addWidget(self._status)

        content_layout.addWidget(body, 1)
        root.addWidget(FooterBar())

    # ---- chat flow ----
    def _send_question(self):
        question = self._chat_input.toPlainText().strip()
        if not question:
            return

        api_key = load_api_key()
        if not api_key:
            self._status.setText("❌  Kein API Key hinterlegt oder Token-Limit erreicht - siehe Manage User.")
            return

        from db.usage_log import log_usage_event
        log_usage_event("feature", "lab_assistant_query")

        self._chat_input.clear()
        self._btn_send.setEnabled(False)
        self._status.setText("⏳  Athena denkt nach...")
        self._athena.start_working()

        separator = "\n\n---\n\n" if self._output_md else ""
        self._output_md = f"{self._output_md}{separator}> {_USER_LABEL}: {question}\n\n{_THINKING}"
        _set_advisor_markdown(self._output, self._output_md)
        self._output.verticalScrollBar().setValue(self._output.verticalScrollBar().maximum())

        self._worker = LabAssistantWorker(
            api_key=api_key,
            history=self._history,
            user_question=question,
        )
        self._worker.result_ready.connect(lambda text: self._on_result(question, text))
        self._worker.error_occurred.connect(self._on_error)
        self._worker.tool_call_started.connect(self._on_tool_call_started)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _strip_thinking_marker(self):
        if self._output_md.endswith(_THINKING):
            self._output_md = self._output_md[: -len(_THINKING)]

    def _on_tool_call_started(self, sql: str):
        """Zeigt die gerade laufende SQL-Abfrage live im Output an (Transparenz/
        Audit - der Superuser soll sehen können, was Athena tatsächlich abfragt,
        bevor die finale Antwort da ist)."""
        self._strip_thinking_marker()
        self._output_md += f"> 🔍 `{sql}`\n\n{_THINKING}"
        _set_advisor_markdown(self._output, self._output_md)
        self._output.verticalScrollBar().setValue(self._output.verticalScrollBar().maximum())

    def _on_result(self, question: str, text: str):
        self._strip_thinking_marker()
        self._output_md += f"{_ATHENA_LABEL}:\n\n{text}"
        _set_advisor_markdown(self._output, self._output_md)
        self._output.verticalScrollBar().setValue(self._output.verticalScrollBar().maximum())
        self._status.setText("✅  Antwort erhalten")

        self._history.append({"role": "user", "content": question})
        self._history.append({"role": "assistant", "content": text})
        if len(self._history) > _MAX_HISTORY_ENTRIES:
            self._history = self._history[:2] + self._history[-4:]

        self._save_chat()

    def _on_error(self, error_msg: str):
        self._strip_thinking_marker()
        self._output_md += f"\n\n❌  Fehler:\n{error_msg}"
        _set_advisor_markdown(self._output, self._output_md)
        self._status.setText("❌  Fehler")

    def _on_finished(self):
        self._btn_send.setEnabled(True)
        self._athena.stop_working()

    # ---- Persistenz (tblLabAssistantChat, mehrere Sitzungen pro User) ----
    def _load_saved_chat(self):
        """Lädt die zuletzt aktualisierte Sitzung dieses Users, falls
        vorhanden - macht die Persistenz aus Nutzersicht spürbar: Verlassen
        des Screens verliert den Chat nicht mehr. Ältere Sitzungen bleiben
        über "History" erreichbar, siehe _open_history()."""
        user_id = (app_meta.current_user or {}).get("id")
        if not user_id or not table_exists("tblLabAssistantChat"):
            return
        try:
            rows = fetch_all(
                "SELECT ID, TranscriptMarkdown, HistoryJSON, UpdatedAt "
                "FROM tblLabAssistantChat WHERE UserID = ? ORDER BY UpdatedAt DESC, ID DESC LIMIT 1",
                [user_id],
            )
        except Exception:
            rows = []
        if rows:
            self._apply_loaded_row(rows[0], status_prefix="📄  Gespeicherter Chat geladen")

    def _apply_loaded_row(self, row: dict, status_prefix: str = "📄  Chat geöffnet"):
        """Übernimmt einen DB-Datensatz (von _load_saved_chat() oder aus dem
        History-Dialog ausgewählt) als aktive Sitzung."""
        self._chat_row_id = row.get("ID")
        self._output_md = row.get("TranscriptMarkdown") or ""
        try:
            self._history = json.loads(row.get("HistoryJSON") or "[]")
        except Exception:
            self._history = []
        _set_advisor_markdown(self._output, self._output_md)
        if self._output_md:
            self._output.verticalScrollBar().setValue(self._output.verticalScrollBar().maximum())
        updated = row.get("UpdatedAt")
        self._status.setText(f"{status_prefix} ({updated})" if updated else "")

    def _open_history(self):
        """Zeigt alle gespeicherten Sitzungen dieses Users, Auswahl ersetzt
        die aktuell angezeigte Sitzung (die vorher aktive bleibt unverändert
        in der DB - siehe _apply_loaded_row())."""
        user_id = (app_meta.current_user or {}).get("id")
        if not user_id or not table_exists("tblLabAssistantChat"):
            self._status.setText("Keine gespeicherten Chats verfügbar.")
            return
        try:
            rows = fetch_all(
                "SELECT ID, TranscriptMarkdown, HistoryJSON, CreatedAt, UpdatedAt "
                "FROM tblLabAssistantChat WHERE UserID = ? ORDER BY UpdatedAt DESC, ID DESC LIMIT 50",
                [user_id],
            )
        except Exception:
            rows = []
        if not rows:
            self._status.setText("Noch keine gespeicherten Chats vorhanden.")
            return
        dlg = _ChatHistoryDialog(rows, parent=self)
        if dlg.exec() == QDialog.Accepted and dlg.selected_row is not None:
            self._apply_loaded_row(dlg.selected_row)

    def _save_chat(self):
        """Best-effort (analog zu advisor_tab.py's _save_advisor_report) -
        Speichern ist ein Zusatznutzen, darf den Chat nie blockieren."""
        user_id = (app_meta.current_user or {}).get("id")
        if not user_id or not table_exists("tblLabAssistantChat"):
            return
        try:
            now = datetime.datetime.now()
            history_json = json.dumps(self._history, ensure_ascii=False)
            if self._chat_row_id is None:
                self._chat_row_id = execute_insert(
                    "INSERT INTO tblLabAssistantChat "
                    "(UserID, CreatedAt, UpdatedAt, TranscriptMarkdown, HistoryJSON, GlobalID) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    [user_id, now, now, self._output_md, history_json, new_global_id()],
                )
            else:
                execute(
                    "UPDATE tblLabAssistantChat SET UpdatedAt = ?, TranscriptMarkdown = ?, HistoryJSON = ? "
                    "WHERE ID = ?",
                    [now, self._output_md, history_json, self._chat_row_id],
                )
        except Exception:
            pass

    def _new_chat(self):
        """Startet eine frische Sitzung (Verlauf + Anthropic-Kontext geleert,
        _chat_row_id=None -> die nächste Antwort legt einen NEUEN Datensatz
        an, siehe _save_chat()). Die bisherige Sitzung wird NICHT gelöscht -
        sie bleibt unverändert in der DB stehen und ist über "History" wieder
        aufrufbar (Nutzerwunsch: echte Mehrfach-Sitzungs-Historie)."""
        self._history = []
        self._output_md = ""
        self._output.setPlainText("")
        self._status.setText("")
        self._chat_row_id = None

    def _go_home(self):
        if callable(self.on_back_home):
            self.on_back_home()
