from __future__ import annotations
# ui/widgets/help_search.py
"""Hilfe-Suche ueber alle Kontext-Hilfen (Nutzerwunsch 2026-10-13: "ein User
hat keine Idee und will einfach wissen 'wo kann ich alle Auftraege einer
Maschine einsehen?'").

Etappe 1 (fuer alle, gratis, offline): durchsucht die "How do I…?"-Eintraege
aller Hilfen in EN/DE/ES, ergaenzt um eine kleine Synonymliste (Auftrag ->
Versuchsserie, Duese -> Jet, ...). Ergebnis: passende Anleitung + "Take me
there" (oeffnet den Screen) + "Open full help" (oeffnet die Hilfe des Screens
auf dem richtigen Tab). Erreichbar ueber den Sidebar-Eintrag "Help" und F1
(main.py -> app_meta.open_help_search).

Der Index wird direkt aus den Textmodulen gebaut (SOURCES in ui/help_index.py,
Qt-frei und mit der Web-App geteilt) - neue Hilfen dort eintragen, dann sind
sie automatisch durchsuchbar.
"""

import html
import re
from typing import Callable, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QSplitter, QWidget, QScrollArea, QFrame,
)

from ui.widgets.multilang_help import (
    LANGUAGES, DEFAULT_LANGUAGE, load_language, save_language, build_flag_row, P_STYLE,
)

# Search logic + texts live in the Qt-free ui/help_index.py (shared with the web app);
# re-exported here so existing imports (tests, usage stats, help_ai, whats_new) keep working.
from ui.help_index import (  # noqa: F401
    SOURCES, SCREEN_NAMES, SYNONYMS, STOPWORDS, _MIN_PREFIX, normalize, tokens, _word_match, _SYN_NORM,
    concepts_of, _phrase_concepts, HelpEntry, _strip_task, build_index, get_index, SearchHit, hit_for_key,
    KB_LIMIT, KB_MIN_COVERAGE, search, _rank, UI, NEEDS_SERIES, normalize_display,
)


def open_screen_help(screen: str, tab: str, parent: QWidget) -> None:
    """Oeffnet die Kontext-Hilfe eines Screens direkt auf dem Tab."""
    if screen == "yarn_stock":
        from ui.widgets.yarn_stock_help_dialog import show_yarn_stock_help
        show_yarn_stock_help(parent, tab=tab)
        return
    import importlib
    module = dict((k, m) for k, _n, m, _f in SOURCES)[screen]
    from ui.widgets.multilang_help import show_help
    show_help(importlib.import_module(module).TEXTS, parent, tab=tab)


class HelpSearchDialog(QDialog):
    """Suchfenster. `navigate(screen_key, tab_key)` oeffnet den Screen
    (main.py); fehlt es, wird "Take me there" ausgeblendet."""

    def __init__(self, parent: Optional[QWidget] = None,
                 navigate: Optional[Callable[[str, str], None]] = None):
        super().__init__(parent)
        self.setMinimumSize(980, 620)
        self._navigate = navigate
        self._lang = load_language()
        self._lang_pinned = False      # True, sobald eine Flagge geklickt wurde
        self._hits: List[SearchHit] = []
        self._opened_key: Optional[str] = None

        root = QVBoxLayout(self)
        flag_row, self._flags = build_flag_row(self._on_flag, self)
        root.addLayout(flag_row)

        self.txt = QLineEdit()
        self.txt.setClearButtonEnabled(True)
        self.txt.setMinimumHeight(36)
        self.txt.setStyleSheet("font-size: 15px; padding: 4px 8px;")
        search_row = QHBoxLayout()
        search_row.addWidget(self.txt, 1)
        # Etappe 2: KI-Antwort nur mit KI-Zugang (tblUser.api_key_enc + Kontingent)
        from ui.widgets.help_ai import has_ai_access
        self._ai_enabled = has_ai_access()
        self._ai_thread = None
        self._ai_result: Optional[dict] = None
        self.btn_ai = QPushButton(objectName="PurpleBtn")
        self.btn_ai.setMinimumHeight(36)
        self.btn_ai.clicked.connect(self._on_ask_ai)
        self.btn_ai.setVisible(self._ai_enabled)
        search_row.addWidget(self.btn_ai)
        root.addLayout(search_row)
        self.lbl_hint = QLabel()
        self.lbl_hint.setStyleSheet("color:#565656;")
        root.addWidget(self.lbl_hint)

        split = QSplitter(Qt.Horizontal)
        self.lst = QListWidget()
        self.lst.setMinimumWidth(340)
        self.lst.setStyleSheet("QListWidget::item{padding:6px;} QListWidget::item:selected{background:#b7d6ff;color:black;}")
        split.addWidget(self.lst)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)
        self.detail = QLabel()
        self.detail.setWordWrap(True)
        self.detail.setTextFormat(Qt.RichText)
        self.detail.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.detail.setStyleSheet(P_STYLE)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(self.detail)
        rl.addWidget(scroll, 1)
        btns = QHBoxLayout()
        # Etappe 3: Rueckmeldung pro angezeigter Antwort (-> Usage Stats, Tab "Help")
        self.lbl_fb = QLabel()
        self.lbl_fb.setStyleSheet("color:#565656;")
        self.btn_fb_up = QPushButton(objectName="GreyBtn")
        self.btn_fb_down = QPushButton(objectName="GreyBtn")
        self.btn_fb_up.clicked.connect(lambda: self._on_feedback(True))
        self.btn_fb_down.clicked.connect(lambda: self._on_feedback(False))
        self._fb_given: set = set()
        btns.addWidget(self.lbl_fb)
        btns.addWidget(self.btn_fb_up)
        btns.addWidget(self.btn_fb_down)
        btns.addStretch(1)
        self.btn_full = QPushButton(objectName="GreyBtn")
        self.btn_full.clicked.connect(self._on_full_help)
        self.btn_go = QPushButton(objectName="GreenBtn")
        self.btn_go.clicked.connect(self._on_go)
        self.btn_go.setVisible(callable(navigate))
        btns.addWidget(self.btn_full)
        btns.addWidget(self.btn_go)
        rl.addLayout(btns)
        split.addWidget(right)
        split.setStretchFactor(1, 1)
        root.addWidget(split, 1)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._run_search)
        self.txt.textChanged.connect(lambda _t: self._timer.start())
        self.lst.currentRowChanged.connect(self._show_detail)
        self.lst.itemDoubleClicked.connect(lambda _i: self._on_go())
        self.txt.returnPressed.connect(self._on_go)

        self._apply_ui_texts()
        self._run_search()
        self.txt.setFocus()

    # ── Sprache ──
    def _on_flag(self, lang: str) -> None:
        self._lang, self._lang_pinned = lang, True
        save_language(lang)
        self._apply_ui_texts()
        self._render_list()

    def _apply_ui_texts(self) -> None:
        u = UI[self._lang]
        self.setWindowTitle(u["title"])
        self.txt.setPlaceholderText(u["placeholder"])
        self.btn_go.setText(u["go"])
        self.btn_full.setText(u["full"])
        self.btn_ai.setText(u["ask"])
        self.btn_ai.setToolTip(u["ask_tip"])
        self.btn_fb_up.setText(u["fb_up"])
        self.btn_fb_down.setText(u["fb_down"])
        self._update_feedback_ui()
        for code, btn in self._flags.items():
            btn.setChecked(code == self._lang)

    # ── Suche ──
    def _run_search(self) -> None:
        q = self.txt.text().strip()
        self._ai_result = None
        self._hits = search(q, with_kb=True) if q else []
        # Anzeige-Sprache automatisch auf die Sprache der Frage, solange keine Flagge gewaehlt wurde
        if self._hits and not self._lang_pinned and self._hits[0].best_lang != self._lang:
            self._lang = self._hits[0].best_lang
            self._apply_ui_texts()
        self._render_list()

    def _render_list(self) -> None:
        u = UI[self._lang]
        self.lst.blockSignals(True)
        self.lst.clear()
        for h in self._hits:
            e = h.by_lang.get(self._lang) or h.by_lang[h.best_lang]
            title = f"{u['ai_label']}: {normalize_display(e.question)}" if h.ai_answer else normalize_display(e.question)
            where = u["kb"] if h.screen == "kb" else SCREEN_NAMES.get(h.screen, h.screen)
            it = QListWidgetItem(f"{title}\n{where}")
            if h.screen == "kb":
                it.setForeground(QColor("#2b7a3d"))
            if h.ai_answer:
                f = it.font(); f.setBold(True); it.setFont(f)
            self.lst.addItem(it)
        self.lst.blockSignals(False)
        q = self.txt.text().strip()
        if not q:
            self.lbl_hint.setText(u["hint"])
        elif not self._hits:
            self.lbl_hint.setText(u["none"] + (" " + u["ask_tip"] if self._ai_enabled else ""))
        else:
            self.lbl_hint.setText("")
        has = bool(self._hits)
        if not has:
            self._update_feedback_ui()
        self.btn_go.setEnabled(has)
        self.btn_full.setEnabled(has)
        if has:
            self.lst.setCurrentRow(0)
            self._show_detail(0)
        else:
            self.detail.setText("")

    def _current_hit(self) -> Optional[SearchHit]:
        r = self.lst.currentRow()
        return self._hits[r] if 0 <= r < len(self._hits) else None

    def _show_detail(self, row: int) -> None:
        if not (0 <= row < len(self._hits)):
            return
        h = self._hits[row]
        u = UI[self._lang]
        e = h.by_lang.get(self._lang) or h.by_lang[h.best_lang]
        is_kb = h.screen == "kb"
        self.btn_go.setText(u["kb_open"] if is_kb else u["go"])
        self.btn_go.setVisible(is_kb or callable(self._navigate))
        self.btn_full.setVisible(not is_kb)
        if is_kb:
            from ui import kb_search
            self.detail.setText(
                f"<p style='color:#2b7a3d;font-weight:600'>{u['kb']}</p><h3>{e.question}</h3>"
                f"<p>{html.escape(kb_search.summary(h.key, e.lang))}</p>"
                f"<p style='color:#565656'>{u['kb_hint']}</p>")
            self._update_feedback_ui()
            return
        steps = "".join(f"<li>{s}</li>" for s in e.steps)
        extra = f"<p style='color:#565656'>{e.note}</p>" if e.note else ""
        warn = (f"<p style='background:#fff3cd;padding:6px'>{u['needs_series']}</p>"
                if h.screen in NEEDS_SERIES else "")
        areas = (f"<p style='color:#8a8a8a;font-size:12px'>{u['areas']}</p>"
                 if re.search(r"\(\d\)|\([A-F]\)", " ".join(e.steps) + e.note) else "")
        ai = ""
        if h.ai_answer:
            ai = (f"<p style='background:#f3eefc;border:1px solid #8e44ad;border-radius:6px;padding:8px'>"
                  f"<b>{u['ai_label']}:</b> {html.escape(h.ai_answer)}</p>")
        self.detail.setText(
            f"{ai}<p style='color:#2b7a3d;font-weight:600'>{u['screen']}: {SCREEN_NAMES.get(h.screen, h.screen)}</p>"
            f"<h3>{e.question}</h3><ol>{steps}</ol>{extra}{warn}{areas}")
        self._update_feedback_ui()

    # ── Aktionen ──
    def _log(self, event: str, detail: str) -> None:
        try:
            from db.usage_log import log_usage_event
            log_usage_event("feature", event, detail[:250])
        except Exception:
            pass

    def _on_ask_ai(self) -> None:
        q = self.txt.text().strip()
        if not q or not self._ai_enabled or self._ai_thread is not None:
            return
        from ui.advisor_worker import load_api_key
        from ui.widgets.help_ai import start_worker
        key = load_api_key()
        if not key:
            self._ai_enabled = False
            self.btn_ai.setVisible(False)
            return
        u = UI[self._lang]
        self.btn_ai.setEnabled(False)
        self.detail.setText(f"<p style='color:#8e44ad'>{u['asking']}</p>")
        self._ai_question = q
        self._ai_thread = start_worker(self, q, self._lang, key, self._on_ai_done)

    def _on_ai_done(self, result: dict) -> None:
        self._ai_thread = None
        self.btn_ai.setEnabled(True)
        u = UI[self._lang]
        if result.get("error"):
            self.detail.setText(f"<p style='color:#a32d2d'>{html.escape(result['error'])}</p>")
            self._log("help_ai_error", f"{self._ai_question} | {result['error']}")
            return
        answer = (result.get("answer") or "").strip()
        key = result.get("entry_key") or "none"
        self._log("help_ai_ask", f"{self._ai_question} -> {key}")
        hit = hit_for_key(key) if key != "none" else None
        if hit is None:
            self.detail.setText(
                f"<p style='background:#f3eefc;border:1px solid #8e44ad;border-radius:6px;padding:8px'>"
                f"<b>{u['ai_label']}:</b> {html.escape(answer or u['ai_none'])}</p>")
            return
        hit.ai_answer = answer
        self._hits = [hit] + [h for h in self._hits if h.key != key]
        self._opened_key = None
        self._render_list()

    def _feedback_id(self) -> Optional[str]:
        h = self._current_hit()
        q = self.txt.text().strip()
        if h is None or not q:
            return None
        return f"{q} -> {h.key}{' (AI)' if h.ai_answer else ''}"

    def _update_feedback_ui(self) -> None:
        u = UI[self._lang]
        fid = self._feedback_id()
        visible = fid is not None
        given = visible and fid in self._fb_given
        self.lbl_fb.setText(u["fb_thanks"] if given else (u["fb_q"] if visible else ""))
        self.btn_fb_up.setVisible(visible and not given)
        self.btn_fb_down.setVisible(visible and not given)

    def _on_feedback(self, helpful: bool) -> None:
        fid = self._feedback_id()
        if fid is None or fid in self._fb_given:
            return
        self._fb_given.add(fid)
        self._log("help_feedback_up" if helpful else "help_feedback_down", fid)
        self._update_feedback_ui()

    def _on_go(self) -> None:
        h = self._current_hit()
        if h is not None and h.screen == "kb":
            # popup over the search window; closing it comes back here
            from ui import kb_search
            from ui.kb_links import open_target
            target = kb_search.parse_key(h.key)
            if target:
                self._opened_key = h.key
                self._log("help_search_open", f"{self.txt.text().strip()} -> {h.key}")
                open_target(self, target, "help_search")
            return
        if h is None or not callable(self._navigate):
            return
        self._opened_key = h.key
        self._log("help_search_open", f"{self.txt.text().strip()} -> {h.key}")
        self._navigate(h.screen, h.tab)
        self.accept()

    def _on_full_help(self) -> None:
        h = self._current_hit()
        if h is None or h.screen == "kb":
            return
        self._opened_key = h.key
        self._log("help_search_open", f"{self.txt.text().strip()} -> {h.key} (full help)")
        open_screen_help(h.screen, h.tab, self)

    def done(self, r: int) -> None:
        q = self.txt.text().strip()
        if q and self._opened_key is None:
            self._log("help_search_noresult" if not self._hits else "help_search_noclick",
                      f"{q} | hits={len(self._hits)}")
        super().done(r)
