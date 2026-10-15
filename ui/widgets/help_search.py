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

Der Index wird direkt aus den Textmodulen gebaut (SOURCES unten) - neue
Hilfen dort eintragen, dann sind sie automatisch durchsuchbar.
"""

import html
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Tuple

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QSplitter, QWidget, QScrollArea, QFrame,
)

from ui.widgets.multilang_help import (
    LANGUAGES, DEFAULT_LANGUAGE, load_language, save_language, build_flag_row, P_STYLE,
)

# ── Quellen ─────────────────────────────────────────────────────────────
# screen_key -> (Anzeigename, Textmodul, Format). "multilang" = Bausteine aus
# multilang_help, "yarn_stock" = eigenes Format der ersten Hilfe.
SOURCES: List[Tuple[str, str, str, str]] = [
    ("all_experiments", "All Experiments", "ui.widgets.help_texts_all_experiments", "multilang"),
    ("backlog", "Backlog", "ui.widgets.help_texts_backlog", "multilang"),
    ("show_experiment", "Show Experiment", "ui.widgets.help_texts_show_experiment", "multilang"),
    ("create_experiment", "Create Experiment", "ui.widgets.help_texts_create_experiment", "multilang"),
    ("report", "Report / Smart Chart", "ui.widgets.help_texts_report", "multilang"),
    ("manage_yarn", "Manage Yarn", "ui.widgets.help_texts_manage_yarn", "multilang"),
    ("manage_jets", "Manage Jets", "ui.widgets.help_texts_manage_jets", "multilang"),
    ("yarn_stock", "Yarn Stock", "ui.widgets.yarn_stock_help_texts", "yarn_stock"),
]
SCREEN_NAMES = {k: name for k, name, _, _ in SOURCES}

# ── Synonyme (normalisiert, d.h. klein, ohne Akzente) ───────────────────
# Jede Gruppe = ein Begriff. Ein Wort der Frage, das zu einer Gruppe passt,
# findet Eintraege, die irgendein Wort derselben Gruppe enthalten.
SYNONYMS: List[List[str]] = [
    ["trial series", "series", "serie", "versuchsserie", "auftrag", "auftrage", "order", "orders", "job",
     "pedido", "encargo", "experiment", "experimento", "projekt", "project"],
    ["trial", "trials", "versuch", "versuche", "ensayo", "ensayos", "probe", "test"],
    ["machine", "maschine", "maquina", "anlage", "texturiermaschine",
     # Maschinennamen (tblMaschine), damit z. B. "alles von der AFK" die Maschinen-Anleitung findet
     "afk", "eafk", "aalidhra", "erdmann", "ssm", "dp2t", "xeno", "zinser"],
    ["yarn", "garn", "garne", "hilo", "hilos", "faden", "material"],
    ["spool", "spule", "spulen", "bobina", "bobinas", "rolle", "cone", "konus"],
    ["jet", "jets", "duse", "dusen", "duese", "duesen", "tobera", "toberas", "nozzle"],
    ["stock", "lager", "lagerbestand", "bestand", "inventario", "almacen", "inventory", "vorrat"],
    ["stock take", "inventur", "inventario fisico", "zahlen", "count"],
    ["label", "labels", "etikett", "etiketten", "etiqueta", "etiquetas", "aufkleber"],
    ["report", "bericht", "informe", "chart", "diagramm", "grafik", "grafico", "auswertung", "smart chart"],
    ["delete", "loschen", "loeschen", "borrar", "entfernen", "remove", "eliminar"],
    ["find", "search", "suchen", "finden", "buscar", "encontrar", "where", "wo", "donde", "show", "anzeigen",
     "einsehen", "sehen", "ver", "mostrar", "list", "liste", "alle", "all", "todos", "filter", "filtern", "filtrar"],
    ["new", "neu", "neue", "anlegen", "create", "erstellen", "erfassen", "crear", "nuevo", "nueva", "add",
     "hinzufugen", "anadir", "registrar", "register"],
    ["status", "zustand", "estado", "done", "fertig", "erledigt"],
    ["retest", "nachmessen", "nachmessung", "repetir", "repeticion", "wiederholen"],
    ["owner", "besitzer", "verantwortlich", "responsable", "zustandig"],
    ["print", "drucken", "imprimir"],
    ["hide", "ausblenden", "verstecken", "ocultar", "esconder", "einblenden", "unhide", "zeile", "zeilen",
     "row", "rows", "fila", "filas", "crowded", "uebersichtlich", "ubersichtlich"],
    ["export", "excel", "exportieren", "exportar"],
    ["minimum stock", "mindestbestand", "minstock", "stock minimo", "nachbestellen", "reorder", "low"],
    ["priority", "prioritat", "prioritaet", "prioridad", "prio"],
    ["copy", "kopieren", "copiar", "duplicate", "duplizieren", "duplicar", "clone", "klonen"],
    ["archive", "archived", "archiv", "archiviert", "archivado", "alt", "old", "viejo"],
    ["history", "verlauf", "historial", "protokoll", "log", "geandert", "changed", "wer", "who", "quien"],
    ["weight", "gewicht", "peso", "kg", "kilo"],
    ["location", "lagerplatz", "platz", "regal", "rack", "ubicacion", "estanteria", "shelf", "fach"],
    ["batch", "charge", "lote", "los"],
    ["ply", "plies", "fadenlage"],
    ["plate", "platte", "plattchen", "plaquita"],
    ["lab", "labor", "laboratorio", "statimat", "itemat", "messung", "measurement", "medicion"],
    ["request", "anfrage", "solicitud", "experiment request"],
    ["rename", "umbenennen", "renombrar", "name", "nombre"],
    ["reference", "referenz", "referenzmuster", "referencia", "benchmark", "golden sample", "kundenmuster",
     "originalspule", "original", "muster", "muestra", "customer sample", "vorlage", "vergleichsmuster"],
]

STOPWORDS: Set[str] = set("""
a an and are as at be by can could do does for from how i in is it me my of on or the this to was what where
which who will with you your into all
der die das den dem des ein eine einer einem einen und oder ist sind wie wo was wer kann ich mich mir zu
im in am an auf fur von mit bei nach aus ein es sich man meine meinen meiner kann konnen soll muss gibt
el la los las un una unos unas y o es son como donde que quien puedo se de del en con por para al mi mis
""".split())

_MIN_PREFIX = 4


def normalize(text: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = text.replace("ß", "ss")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def tokens(text: str) -> List[str]:
    return [t for t in normalize(text).split() if t and t not in STOPWORDS and len(t) > 1]


def _word_match(token: str, word: str) -> bool:
    if token == word:
        return True
    if len(word) >= _MIN_PREFIX and token.startswith(word):
        return True
    return len(token) >= _MIN_PREFIX + 1 and word.startswith(token)


_SYN_NORM: List[Set[str]] = [{normalize(w) for w in group} for group in SYNONYMS]


def concepts_of(token: str) -> Set[int]:
    out: Set[int] = set()
    for i, group in enumerate(_SYN_NORM):
        for w in group:
            if " " in w:
                continue  # Mehrwort-Synonyme werden ueber den Volltext geprueft
            if _word_match(token, w):
                out.add(i)
                break
    return out


def _phrase_concepts(norm_text: str) -> Set[int]:
    out: Set[int] = set()
    for i, group in enumerate(_SYN_NORM):
        for w in group:
            if " " in w and f" {w} " in f" {norm_text} ":
                out.add(i)
    return out


# ── Index ───────────────────────────────────────────────────────────────
@dataclass
class HelpEntry:
    key: str                 # sprachunabhaengig, z.B. "backlog:tasks:3"
    screen: str
    tab: str                 # Tab-Key fuer "Open full help"
    lang: str
    question: str            # HTML
    steps: List[str]         # HTML
    note: str                # HTML
    q_tokens: List[str] = field(default_factory=list)
    b_tokens: List[str] = field(default_factory=list)
    q_concepts: Set[int] = field(default_factory=set)
    b_concepts: Set[int] = field(default_factory=set)

    def prepare(self) -> "HelpEntry":
        q_norm = normalize(self.question)
        b_norm = normalize(" ".join(self.steps) + " " + self.note + " " + SCREEN_NAMES.get(self.screen, ""))
        self.q_tokens = tokens(self.question)
        self.b_tokens = tokens(b_norm)
        self.q_concepts = set().union(*[concepts_of(t) for t in self.q_tokens]) | _phrase_concepts(q_norm)
        self.b_concepts = set().union(*[concepts_of(t) for t in self.b_tokens]) | _phrase_concepts(b_norm)
        return self


def _strip_task(block) -> Tuple[str, List[str], str]:
    return block[1], list(block[2]), (block[3] if len(block) > 3 else "")


def build_index() -> List[HelpEntry]:
    import importlib
    entries: List[HelpEntry] = []
    for screen, _name, module_name, fmt in SOURCES:
        try:
            texts = importlib.import_module(module_name).TEXTS
        except Exception:
            continue
        for lang, t in texts.items():
            if fmt == "multilang":
                for tab in t["tabs"]:
                    n = 0
                    for block in tab["blocks"]:
                        if block[0] == "task":
                            q, steps, note = _strip_task(block)
                            entries.append(HelpEntry(f"{screen}:{tab['key']}:{n}", screen, tab["key"],
                                                     lang, q, steps, note).prepare())
                            n += 1
            elif fmt == "yarn_stock":
                for part in ("tasks_find", "tasks_change"):
                    for n, (q, steps, note) in enumerate(t.get(part, [])):
                        entries.append(HelpEntry(f"{screen}:{part}:{n}", screen, "tasks", lang,
                                                 q, list(steps), note).prepare())
                for n, (heading, body) in enumerate(t.get("stocktake", [])):
                    entries.append(HelpEntry(f"{screen}:stocktake:{n}", screen, "stocktake", lang,
                                             heading, [body], "").prepare())
    return entries


_INDEX: Optional[List[HelpEntry]] = None


def get_index() -> List[HelpEntry]:
    global _INDEX
    if _INDEX is None:
        _INDEX = build_index()
    return _INDEX


@dataclass
class SearchHit:
    key: str
    screen: str
    tab: str
    score: float
    best_lang: str
    by_lang: Dict[str, HelpEntry]
    ai_answer: str = ""          # gesetzt, wenn der Treffer aus der KI-Antwort stammt


def hit_for_key(key: str) -> Optional[SearchHit]:
    """SearchHit fuer einen Eintrags-Key (alle Sprachfassungen)."""
    by_lang = {e.lang: e for e in get_index() if e.key == key}
    if not by_lang:
        return None
    any_e = next(iter(by_lang.values()))
    return SearchHit(key, any_e.screen, any_e.tab, 0.0, any_e.lang, by_lang)


def search(query: str, limit: int = 12) -> List[SearchHit]:
    """Sucht in allen Sprachen; Treffer werden pro Eintrag (sprachunabhaengig)
    zusammengefasst. Ranking: Anteil getroffener Suchbegriffe zuerst, dann
    Treffer in der Frage (x3) vor Treffern im Text (x1)."""
    q_tokens = tokens(query)
    if not q_tokens:
        return []
    q_norm = normalize(query)
    terms = [(t, concepts_of(t)) for t in q_tokens]
    phrase = _phrase_concepts(q_norm)
    best: Dict[str, SearchHit] = {}
    for e in get_index():
        score, matched = 0.0, 0
        for tok, cons in terms:
            lit_q = any(_word_match(tok, w) for w in e.q_tokens)
            lit_b = lit_q or any(_word_match(tok, w) for w in e.b_tokens)
            in_q = lit_q or bool(cons & e.q_concepts)
            in_b = in_q or lit_b or bool(cons & e.b_concepts)
            if in_q:
                score += 3
                matched += 1
            elif in_b:
                score += 1
                matched += 1
            # Woertliche Treffer (statt nur ueber Synonyme) leicht bevorzugen:
            # so gewinnt die Sprachfassung, in der gefragt wurde.
            if lit_q:
                score += 0.6
            elif lit_b:
                score += 0.3
        score += 2 * len(phrase & e.q_concepts) + len(phrase & e.b_concepts)
        if matched == 0:
            continue
        coverage = matched / len(terms)
        if len(terms) >= 3 and coverage < 0.34:
            continue
        total = coverage * 10 + score
        hit = best.get(e.key)
        if hit is None:
            hit = best[e.key] = SearchHit(e.key, e.screen, e.tab, total, e.lang, {})
        elif total > hit.score:
            hit.score, hit.best_lang = total, e.lang
        hit.by_lang[e.lang] = e
    # alle Sprachfassungen nachtragen (auch nicht getroffene), fuer die Anzeige
    if best:
        for e in get_index():
            if e.key in best:
                best[e.key].by_lang.setdefault(e.lang, e)
    return sorted(best.values(), key=lambda h: -h.score)[:limit]


# ── Dialog ──────────────────────────────────────────────────────────────
UI = {
    "en": {"title": "Help – where do I find…?", "placeholder": "What are you looking for? e.g. all orders of a machine",
           "go": "Take me there", "full": "Open full help", "none": "No matching help found. Try other words – "
           "e.g. the name of a screen, a button or what you want to do.",
           "hint": "Describe what you want to do in your own words.", "screen": "Screen",
           "needs_series": "Open a trial series first (e.g. from the Backlog or All Experiments).",
           "areas": "Numbers like (1) refer to the screen sketch in the full help.",
           "ask": "Ask AI", "ask_tip": "Let the AI answer in your own words (uses your AI token quota).",
           "asking": "Asking the AI…", "ai_label": "AI answer", "ai_none": "The help does not cover this question yet.",
           "fb_q": "Did this help?", "fb_up": "Helpful", "fb_down": "Not helpful", "fb_thanks": "Thanks for the feedback!"},
    "de": {"title": "Hilfe – wo finde ich…?", "placeholder": "Was suchst du? z. B. alle Aufträge einer Maschine",
           "go": "Hinführen", "full": "Ganze Hilfe öffnen", "none": "Keine passende Hilfe gefunden. Versuch es mit "
           "anderen Worten – z. B. dem Namen eines Bildschirms, eines Buttons oder was du tun willst.",
           "hint": "Beschreib in eigenen Worten, was du tun willst.", "screen": "Bildschirm",
           "needs_series": "Zuerst eine Versuchsserie öffnen (z. B. aus dem Backlog oder All Experiments).",
           "areas": "Nummern wie (1) verweisen auf die Bildschirm-Skizze in der ganzen Hilfe.",
           "ask": "KI fragen", "ask_tip": "Die KI antwortet in eigenen Worten (verbraucht dein KI-Kontingent).",
           "asking": "Die KI wird gefragt…", "ai_label": "KI-Antwort", "ai_none": "Die Hilfe deckt diese Frage noch nicht ab.",
           "fb_q": "Hat das geholfen?", "fb_up": "Hilfreich", "fb_down": "Nicht hilfreich", "fb_thanks": "Danke für die Rückmeldung!"},
    "es": {"title": "Ayuda – ¿dónde encuentro…?", "placeholder": "¿Qué buscas? p. ej. todos los pedidos de una máquina",
           "go": "Llévame allí", "full": "Abrir la ayuda completa", "none": "No se encontró ayuda. Prueba con "
           "otras palabras – p. ej. el nombre de una pantalla, de un botón o lo que quieres hacer.",
           "hint": "Describe con tus palabras lo que quieres hacer.", "screen": "Pantalla",
           "needs_series": "Primero abre una serie de ensayos (p. ej. desde el Backlog o All Experiments).",
           "areas": "Los números como (1) se refieren al esquema de la pantalla en la ayuda completa.",
           "ask": "Preguntar a la IA", "ask_tip": "La IA responde con sus palabras (usa tu cuota de tokens de IA).",
           "asking": "Preguntando a la IA…", "ai_label": "Respuesta de la IA", "ai_none": "La ayuda aún no cubre esta pregunta.",
           "fb_q": "¿Te ha ayudado?", "fb_up": "Útil", "fb_down": "No útil", "fb_thanks": "¡Gracias por tu opinión!"},
}

# Screens, die eine geoeffnete Serie brauchen - "Take me there" fuehrt dann zu All Experiments.
NEEDS_SERIES = {"show_experiment"}


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
        self._hits = search(q) if q else []
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
            it = QListWidgetItem(f"{title}\n{SCREEN_NAMES.get(h.screen, h.screen)}")
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
        steps = "".join(f"<li>{s}</li>" for s in e.steps)
        extra = f"<p style='color:#565656'>{e.note}</p>" if e.note else ""
        warn = (f"<p style='background:#fff3cd;padding:6px'>{u['needs_series']}</p>"
                if h.screen in NEEDS_SERIES or (h.screen == "report" and h.tab != "smart") else "")
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
        if h is None or not callable(self._navigate):
            return
        self._opened_key = h.key
        self._log("help_search_open", f"{self.txt.text().strip()} -> {h.key}")
        self._navigate(h.screen, h.tab)
        self.accept()

    def _on_full_help(self) -> None:
        h = self._current_hit()
        if h is None:
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


def normalize_display(html_text: str) -> str:
    """Frage als Klartext fuer die Ergebnisliste."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", html_text))).strip()
