"""advisor_tab.py - agentT/Athena Jet-Optimization-Advisor-Tab fuer TrippleT.

Enthaelt alle Funktionen, die am Ende von screen_show_experiment.py via
Monkey-Patching auf ShowExperimentScreen registriert werden (siehe dort
_patch_show_experiment_advisor()). Ausgelagert aus screen_show_experiment.py
(reiner Code-Move, keine Verhaltensaenderung) - analog zu dty_yarnscope_tab.py
und aty_yarnscope_tab.py.

_is_advisor_enabled() bleibt bewusst in screen_show_experiment.py, da sie auch
ausserhalb dieses Tabs (Tab-Sichtbarkeits-Check) aufgerufen wird.

table_exists/fetch_all/execute_non_query werden lazy aus ui.screen_show_experiment
importiert (nicht neu implementiert), damit exakt dieselben DB-Wrapper wie vorher
verwendet werden.
"""
from __future__ import annotations

import datetime

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QTextEdit,
)

import app_meta
from db.connection import new_global_id
from ui.advisor_worker import AdvisorWorker, load_api_key


def _build_advisor_tab(self):
    """Baut den 🦉 Athena Advisor Tab auf. Nur für User 'soj'.

    NEU:
      - Chat-Input (Textarea + Senden-Button) für Folgefragen
      - Chat-History in-memory (max. 6 Turns = 3x user + 3x assistant)
      - "Analyse neu starten"-Button löscht History
    """
    from ui.athena_owl import AthenaOwl, AthenaHeaderLabel
    from PySide6.QtWidgets import QSplitter
    from PySide6.QtCore import Qt as _Qt

    # Chat-History (in-memory, max. 6 Einträge)
    self._advisor_history: list = []

    self.tab_advisor = QWidget()
    lay = QVBoxLayout(self.tab_advisor)
    lay.setContentsMargins(16, 16, 16, 16)
    lay.setSpacing(8)

    # ── Header ──────────────────────────────────────────────────────────
    hdr = QHBoxLayout()
    lbl_title = AthenaHeaderLabel("🦉 Athena – Jet Optimization Advisor", owl=None)
    lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #39A650;")
    hdr.addWidget(lbl_title)
    hdr.addStretch()

    self._btn_advisor_run = QPushButton("🦉 Wake Athena")
    self._btn_advisor_run.setObjectName("GreenBtn")
    self._btn_advisor_run.setFixedHeight(32)
    self._btn_advisor_run.setMinimumWidth(160)
    self._btn_advisor_run.clicked.connect(self._run_advisor)
    hdr.addWidget(self._btn_advisor_run)

    self._btn_advisor_reset = QPushButton("↺  Neu")
    self._btn_advisor_reset.setToolTip("Clear chat history and restart")
    self._btn_advisor_reset.setFixedHeight(32)
    self._btn_advisor_reset.setFixedWidth(70)
    self._btn_advisor_reset.setStyleSheet(
        "QPushButton { background:#1e293b; color:#cbd5e1; border:1px solid #475569;"
        "border-radius:4px; font-size:12px; font-weight:bold; }"
        "QPushButton:hover { background:#334155; color:#fff; border-color:#39A650; }"
    )
    self._btn_advisor_reset.clicked.connect(self._reset_advisor)
    hdr.addWidget(self._btn_advisor_reset)
    lay.addLayout(hdr)

    # Kosten-Hinweis
    hint = QLabel("~ CHF 0.02 pro Analyse  ·  Anthropic API  ·  7 Tage Retention  ·  Kein Training")
    hint.setStyleSheet("color: #555; font-size: 10px;")
    lay.addWidget(hint)

    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet("color: #333;")
    lay.addWidget(line)

    # ── Output-Container — Athena schläft hier unten rechts ──────────────
    output_container = QWidget()
    output_container.setMinimumHeight(250)
    output_lay = QVBoxLayout(output_container)
    output_lay.setContentsMargins(0, 0, 0, 0)

    self._advisor_output = QTextEdit()
    self._advisor_output.setReadOnly(True)
    # Rohen Markdown-Text SEPARAT mitführen (nie aus dem Widget zurücklesen!):
    # QTextEdit.toPlainText() liefert nach setMarkdown() den GERENDERTEN Text
    # (z.B. ohne die **-Sternchen), nicht den Markdown-Quelltext. Wuerde man
    # das fuer die Verlaufs-Akkumulation zurücklesen, ginge die Markdown-
    # Syntax bei jeder Folgefrage weiter verloren.
    self._advisor_output_md = ""
    self._advisor_output.setStyleSheet(
        "background: #111827; color: #e5e7eb;"
        "font-family: 'Consolas', 'Courier New', monospace;"
        "font-size: 12px; border: 1px solid #374151;"
        "border-radius: 6px; padding: 12px;"
    )
    # setMarkdown() rendert intern zu HTML - die QSS-Farbe oben greift dafuer
    # NICHT zuverlaessig (z.B. Links werden von Qt standardmaessig in einem
    # dunkelblauen Ton gerendert, der auf dem dunklen Hintergrund kaum lesbar
    # ist). Eigenes Dokument-Stylesheet mit auf den dunklen Hintergrund
    # abgestimmten Farben fuer alle relevanten Markdown-Elemente.
    self._advisor_output.document().setDefaultStyleSheet(
        "body { color: #e5e7eb; }"
        "a { color: #7dd3fc; }"
        "code { color: #fbbf24; background: #1f2937; padding: 1px 4px; border-radius: 3px; }"
        "pre { color: #fbbf24; background: #1f2937; }"
        "table { color: #e5e7eb; border-collapse: collapse; }"
        "th, td { border: 1px solid #374151; padding: 4px 8px; }"
        "th { background: #1f2937; }"
        "h1, h2, h3, h4 { color: #f3f4f6; }"
        "strong, b { color: #f9fafb; }"
    )
    self._advisor_output.setPlaceholderText(
        "Klicke «Athena wecken» um eine KI-Auswertung dieser TrialSeries zu erhalten.\n\n"
        "Athena analysiert:\n"
        "  • Jet-Geometrien aller Trials (Luftbohrung, GarnkanalBreite, Winkel, ...)\n"
        "  • Itemat Lab / Itemat Plus (FPm, Stability pro Tension)\n"
        "  • YarnScope / DTYoMat (Knotenklassen, ML-Prognosen Stab_03/06/10/13)\n"
        "  • Statimat Reissfestigkeit und Dehnung\n"
        "  • Gespeicherte Ruleset-Evaluationen (falls vorhanden)\n\n"
        "Nach der Analyse kannst du Folgefragen stellen."
    )
    output_lay.addWidget(self._advisor_output)
    lay.addWidget(output_container, 1)

    # Athena schläft unten rechts im Output-Container (nicht im ganzen Tab,
    # damit sie nicht über den Chat-Bereich fliegt)
    self._athena = AthenaOwl(output_container)
    self._athena.place_sleeping()
    lbl_title._owl = self._athena

    # ── Chat-Input (Folgefragen) ─────────────────────────────────────────
    chat_frame = QFrame()
    chat_frame.setStyleSheet(
        "QFrame { background:#1a1f2e; border:1px solid #2d3748;"
        "border-radius:6px; }"
    )
    chat_lay = QVBoxLayout(chat_frame)
    chat_lay.setContentsMargins(10, 8, 10, 8)
    chat_lay.setSpacing(6)

    chat_lbl = QLabel("Frage an Athena:")
    chat_lbl.setStyleSheet("color:#9ca3af; font-size:11px; background:transparent; border:none;")
    chat_lay.addWidget(chat_lbl)

    chat_input_row = QHBoxLayout()
    self._advisor_chat_input = QTextEdit()
    self._advisor_chat_input.setFixedHeight(60)
    self._advisor_chat_input.setPlaceholderText(
        "e.g. «Why is trial 3 better than trial 1?» or «Explain the stability drop at 1.3 cN/dtex»"
    )
    self._advisor_chat_input.setStyleSheet(
        "background:#111827; color:#e5e7eb; font-size:12px;"
        "border:1px solid #374151; border-radius:4px; padding:6px;"
    )
    chat_input_row.addWidget(self._advisor_chat_input, 1)

    self._btn_advisor_send = QPushButton("Senden  ↵")
    self._btn_advisor_send.setFixedSize(90, 60)
    self._btn_advisor_send.setStyleSheet(
        "QPushButton { background:#39A650; color:#ffffff; border:none;"
        "border-radius:5px; font-size:13px; font-weight:bold; }"
        "QPushButton:hover { background:#2e8a42; }"
        "QPushButton:disabled { background:#1e293b; color:#4b5563; border:1px solid #374151; }"
    )
    self._btn_advisor_send.setEnabled(False)
    self._btn_advisor_send.clicked.connect(self._send_advisor_question)
    chat_input_row.addWidget(self._btn_advisor_send)
    chat_lay.addLayout(chat_input_row)

    lay.addWidget(chat_frame)

    # ── Status-Label ────────────────────────────────────────────────────
    self._advisor_status = QLabel("")
    self._advisor_status.setStyleSheet("color: #9ca3af; font-size: 10px;")
    lay.addWidget(self._advisor_status)


def _set_advisor_markdown(widget, text: str) -> None:
    """setMarkdown() + Fix fuer Qt's hartcodierte Link-Farbe.

    QTextDocument.setMarkdown() schreibt bei erkannten Links ein Inline-
    Style color:#0000ff direkt ins generierte HTML - das laesst sich WEDER
    per QSS/Stylesheet noch per QPalette uebersteuern (Inline-Styles haben
    Vorrang). Einzig zuverlaessiger Weg: HTML nach dem Rendern abgreifen und
    die Farbe direkt ersetzen, dann per setHtml() erneut setzen.
    """
    widget.setMarkdown(text)
    html = widget.toHtml().replace("color:#0000ff", "color:#7dd3fc")
    widget.setHtml(html)


def _run_advisor(self):
    """Startet die agentT-Erstanalyse (non-blocking via QThread)."""
    if self._series_pk is None:
        return

    api_key = load_api_key()
    if not api_key:
        self._advisor_output_md = ""
        self._advisor_output.setPlainText(
            "⚠️  Kein API Key gefunden.\n\n"
            "Bitte ai_secrets.json anlegen:\n\n"
            "    Pfad: C:\\ProgramData\\TrippleT\\ai_secrets.json\n\n"
            "    Inhalt:\n"
            '    {\n'
            '        "anthropic_api_key": "sk-ant-api03-..."\n'
            '    }\n\n'
            "API Key erstellen: https://console.anthropic.com/"
        )
        return

    self._btn_advisor_run.setEnabled(False)
    self._btn_advisor_run.setText("🦉 Athena thinking…")
    self._btn_advisor_send.setEnabled(False)
    self._advisor_status.setText("⏳  Daten werden geladen und analysiert...")
    self._advisor_output_md = ""
    self._advisor_output.setPlainText("")
    if hasattr(self, "_athena"):
        self._athena.start_working()

    self._advisor_worker = AdvisorWorker(
        series_pk=self._series_pk,
        trial_ids=list(self._trial_ids),
        experiment_id_txt=getattr(self, "_experiment_id_txt", ""),
        api_key=api_key,
        history=None,
        user_question=None,  # erster Call → vollständiger Report
    )
    self._advisor_worker.result_ready.connect(self._on_advisor_result)
    self._advisor_worker.error_occurred.connect(self._on_advisor_error)
    self._advisor_worker.finished.connect(self._on_advisor_finished)
    self._advisor_worker.start()


def _send_advisor_question(self):
    """Sendet eine Folgefrage an Athena (nutzt Chat-History)."""
    question = self._advisor_chat_input.toPlainText().strip()
    if not question or self._series_pk is None:
        return

    api_key = load_api_key()
    if not api_key:
        return

    self._advisor_chat_input.clear()
    self._btn_advisor_run.setEnabled(False)
    self._btn_advisor_send.setEnabled(False)
    self._advisor_status.setText("⏳  Athena denkt nach...")

    # Aktuelle Antwort in Output anhängen (User-Frage sichtbar machen)
    current_text = self._advisor_output_md
    separator = "\n\n" + "─" * 60 + "\n"
    self._advisor_output_md = current_text + separator + f"❓ {question}\n\n⏳ ..."
    _set_advisor_markdown(self._advisor_output, self._advisor_output_md)
    if hasattr(self, "_athena"):
        self._athena.start_working()

    self._advisor_worker = AdvisorWorker(
        series_pk=self._series_pk,
        trial_ids=list(self._trial_ids),
        experiment_id_txt=getattr(self, "_experiment_id_txt", ""),
        api_key=api_key,
        history=self._advisor_history,
        user_question=question,
    )
    self._advisor_worker.result_ready.connect(self._on_advisor_followup_result)
    self._advisor_worker.error_occurred.connect(self._on_advisor_error)
    self._advisor_worker.finished.connect(self._on_advisor_finished)
    self._advisor_worker.start()


def _save_advisor_report(self, is_new: bool) -> None:
    """Speichert den aktuellen Athena-Report in tblAdvisorReport.

    is_new=True: neue Session ("Athena wecken") -> neuer Verlaufs-Eintrag.
    is_new=False: Folgefrage innerhalb derselben Session -> bestehenden
    Eintrag aktualisieren, kein neuer Verlaufs-Eintrag.
    """
    if not self._series_pk:
        return
    try:
        # Lazy import (vermeidet Zirkularimport, screen_show_experiment
        # importiert dieses Modul selbst) - dieselben DB-Wrapper wie vorher.
        from ui.screen_show_experiment import table_exists, fetch_all, execute_non_query
        if not table_exists("tblAdvisorReport"):
            return
        now = datetime.datetime.now()
        user_id = None
        try:
            user = getattr(app_meta, "current_user", {}) or {}
            user_id = user.get("ID") if isinstance(user, dict) else None
        except Exception:
            user_id = None

        if is_new or not getattr(self, "_advisor_current_report_id", None):
            execute_non_query(
                "INSERT INTO [tblAdvisorReport] "
                "([TrialSeriesID],[UserID],[CreatedAt],[UpdatedAt],[ReportMarkdown],[GlobalID]) "
                "VALUES (?,?,?,?,?,?)",
                [self._series_pk, user_id, now, now, self._advisor_output_md, new_global_id()],
            )
            rows = fetch_all("SELECT @@IDENTITY AS NewID", [])
            self._advisor_current_report_id = int(rows[0]["NewID"]) if rows else None
        else:
            execute_non_query(
                "UPDATE [tblAdvisorReport] SET [ReportMarkdown] = ?, [UpdatedAt] = ? WHERE [ID] = ?",
                [self._advisor_output_md, now, self._advisor_current_report_id],
            )
    except Exception:
        pass  # Speichern ist ein Zusatznutzen, darf Athena nie blockieren


def _load_latest_advisor_report(self) -> None:
    """Laedt den letzten gespeicherten Athena-Report dieser Series (falls
    vorhanden) und zeigt ihn sofort an - kein neuer API-Call noetig."""
    from ui.screen_show_experiment import table_exists, fetch_all

    self._advisor_output_md = ""
    self._advisor_history = []
    if not self._series_pk or not table_exists("tblAdvisorReport"):
        return
    try:
        rows = fetch_all(
            "SELECT [ID], [ReportMarkdown], [CreatedAt] FROM [tblAdvisorReport] "
            "WHERE [TrialSeriesID] = ? ORDER BY [CreatedAt] DESC LIMIT 1",
            [self._series_pk],
        )
    except Exception:
        rows = []
    if not rows:
        return
    text = rows[0].get("ReportMarkdown") or ""
    self._advisor_current_report_id = rows[0]["ID"]
    self._advisor_output_md = text
    _set_advisor_markdown(self._advisor_output, text)
    self._advisor_history = [
        {"role": "user", "content": "Analysiere diese TrialSeries."},
        {"role": "assistant", "content": text},
    ]
    created = rows[0].get("CreatedAt")
    self._advisor_status.setText(f"📄  Gespeicherter Report geladen ({created})  ·  You can ask follow-up questions")
    self._btn_advisor_send.setEnabled(True)


def _on_advisor_result(self, text: str):
    """Ergebnis der Erstanalyse: in Output + History speichern."""
    self._advisor_output_md = text
    _set_advisor_markdown(self._advisor_output, text)
    self._advisor_status.setText("✅  Analysis complete  ·  You can now ask questions")
    # Ersten Turn in History speichern
    self._advisor_history = [
        {"role": "user", "content": "Analysiere diese TrialSeries."},
        {"role": "assistant", "content": text},
    ]
    _save_advisor_report(self, is_new=True)


def _on_advisor_followup_result(self, text: str):
    """Ergebnis einer Folgefrage: an Output anhängen + History aktualisieren."""
    current = self._advisor_output_md
    # "⏳ ..." am Ende entfernen und Antwort einfügen
    if current.endswith("⏳ ..."):
        current = current[: -len("⏳ ...")]
    self._advisor_output_md = current + text
    _set_advisor_markdown(self._advisor_output, self._advisor_output_md)
    self._advisor_output.verticalScrollBar().setValue(
        self._advisor_output.verticalScrollBar().maximum()
    )
    self._advisor_status.setText("✅  Response received")

    # History aktualisieren (max. 6 Einträge = 3 Turns)
    last_question = ""
    current_full = self._advisor_output_md
    # Letzten User-Input aus dem Text extrahieren (nach letztem ─────)
    sep = "─" * 60
    if sep in current_full:
        parts = current_full.split(sep)
        last_part = parts[-1].strip()
        if last_part.startswith("❓ "):
            last_question = last_part.split("\n")[0][2:].strip()

    if last_question:
        self._advisor_history.append({"role": "user", "content": last_question})
        self._advisor_history.append({"role": "assistant", "content": text})
        # Auf max. 6 Einträge kürzen (älteste entfernen, ersten Turn behalten)
        if len(self._advisor_history) > 6:
            self._advisor_history = (
                    self._advisor_history[:2]  # erster Turn bleibt
                    + self._advisor_history[-4:]  # letzte 2 Turns
            )
    _save_advisor_report(self, is_new=False)


def _reset_advisor(self):
    """Löscht Chat-History und Output — Neustart."""
    self._advisor_history = []
    self._advisor_output_md = ""
    self._advisor_current_report_id = None
    self._advisor_output.setPlainText("")
    self._advisor_status.setText("")
    self._btn_advisor_send.setEnabled(False)
    self._advisor_chat_input.clear()


def _on_advisor_error(self, error_msg: str):
    current = self._advisor_output_md
    if current.endswith("⏳ ..."):
        current = current[: -len("⏳ ...")]
    self._advisor_output_md = (
        current + f"\n\n❌  Fehler:\n{error_msg}" if current else f"❌  Fehler:\n\n{error_msg}"
    )
    _set_advisor_markdown(self._advisor_output, self._advisor_output_md)
    self._advisor_status.setText("❌  Fehler")


def _on_advisor_finished(self):
    self._btn_advisor_run.setEnabled(True)
    self._btn_advisor_run.setText("🦉 Wake Athena")
    self._btn_advisor_send.setEnabled(bool(self._advisor_history))
    if hasattr(self, "_athena"):
        self._athena.stop_working()

