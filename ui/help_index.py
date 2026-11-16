from __future__ import annotations
# ui/help_index.py
"""Qt-free part of the help search (ui/widgets/help_search.py), shared with
the web app (tripplet_web): sources, synonyms, index of all "How do I...?"
entries in EN/DE/ES, ranking (incl. Knowledge Base hits via ui/kb_search.py)
and the texts of the search window. Moved here unchanged 2026-11-13;
ui/widgets/help_search.py re-exports everything, so existing imports keep
working. New help sources: add them to SOURCES here.
"""

import functools
import html
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

# ── Quellen ─────────────────────────────────────────────────────────────
# screen_key -> (Anzeigename, Textmodul, Format). "multilang" = Bausteine aus
# multilang_help, "yarn_stock" = eigenes Format der ersten Hilfe.
SOURCES: List[Tuple[str, str, str, str]] = [
    ("all_experiments", "All Experiments", "ui.widgets.help_texts_all_experiments", "multilang"),
    ("backlog", "Backlog", "ui.widgets.help_texts_backlog", "multilang"),
    ("dashboards", "Dashboards", "ui.widgets.help_texts_dashboards", "multilang"),
    ("show_experiment", "Show Experiment", "ui.widgets.help_texts_show_experiment", "multilang"),
    ("create_experiment", "Create Experiment", "ui.widgets.help_texts_create_experiment", "multilang"),
    ("report", "Report", "ui.widgets.help_texts_report", "multilang"),
    ("smart_chart", "Smart Chart", "ui.widgets.help_texts_smart_chart", "multilang"),
    ("manage_yarn", "Manage Yarn", "ui.widgets.help_texts_manage_yarn", "multilang"),
    ("manage_jets", "Manage Jets", "ui.widgets.help_texts_manage_jets", "multilang"),
    ("process_playground", "Process Playground", "ui.widgets.help_texts_process_playground", "multilang"),
    ("jet_advisor", "Jet Advisor", "ui.widgets.help_texts_jet_advisor", "multilang"),
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
    ["count", "zahlen", "zaehlen", "anzahl", "how many", "wie viele", "contar", "cuantos", "statistics",
     "statistik", "estadistica", "estadisticas", "per month", "pro monat", "por mes"],
    ["machine", "maschine", "maquina", "anlage", "texturiermaschine",
     # Maschinennamen (tblMaschine), damit z. B. "alles von der AFK" die Maschinen-Anleitung findet
     "afk", "eafk", "aalidhra", "erdmann", "ssm", "dp2t", "xeno", "zinser"],
    ["yarn", "garn", "garne", "hilo", "hilos", "faden", "material"],
    ["spool", "spule", "spulen", "bobina", "bobinas", "rolle", "cone", "konus"],
    ["note", "notes", "notiz", "notizen", "nota", "notas", "kommentar", "comment", "bemerkung",
     "anmerkung", "comentario", "vermerk"],
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
    ["history", "verlauf", "historie", "change history", "anderungsverlauf", "aenderungsverlauf",
     "protokoll", "historial", "audit"],
    ["recycle", "papierkorb", "wiederherstellen", "restore", "undo", "ruckgangig", "rueckgaengig", "papelera",
     "recuperar", "geloscht", "geloescht", "deleted"],
    ["unusual", "plausibel", "plausibility", "tippfehler", "typo", "ungewohnlich", "ungewoehnlich", "inusual",
     "error tipografico", "warnung", "warning"],
    ["bigger", "larger", "zoom", "gross", "grosser", "groesser", "vergrossern", "vergroessern", "schrift",
     "schriftgrosse", "schriftgroesse", "text size", "font", "lesen", "lesbar", "sehen", "sehe", "klein",
     "kontrast", "contrast", "grande", "letra", "leer", "ver", "contraste", "settings", "einstellungen",
     "ajustes", "akzentfarbe", "accent", "welcome", "willkommen", "begrussung", "begruessung", "bienvenida",
     "farbenblind", "rot grun", "colour blind", "color blind", "daltonico", "schlecht", "blind",
     "sehschwach", "vorlesen", "lupe", "magnifier"],
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

# Chinese question words etc. (two-character pieces, see tokens())
STOPWORDS |= {"如何", "怎么", "怎样", "什么", "哪里", "在哪", "哪个", "可以", "我想", "我要", "一个", "这个", "那个",
              "我的", "是否", "能否", "需要"}

_MIN_PREFIX = 4
_CJK = "\u3400-\u4dbf\u4e00-\u9fff"
_CJK_RUN = re.compile(f"[{_CJK}]+")


def normalize(text: str) -> str:
    """Lower case, no accents, only letters/digits - and Chinese characters, kept as separate runs."""
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = text.replace("ß", "ss")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(f"[^a-z0-9{_CJK}]+", " ", text.lower())
    text = re.sub(f"([{_CJK}]+)", r" \1 ", text)
    return re.sub(r"\s+", " ", text).strip()


def _cjk_pieces(run: str) -> List[str]:
    """Chinese has no spaces between words: a run counts as its overlapping two-character
    pieces ("复制试验" -> 复制, 制试, 试验), a single character as itself."""
    if len(run) == 1:
        return [run]
    return [run[i:i + 2] for i in range(len(run) - 1)]


def tokens(text: str) -> List[str]:
    out: List[str] = []
    for t in normalize(text).split():
        if _CJK_RUN.fullmatch(t):
            out += [p for p in _cjk_pieces(t) if p not in STOPWORDS and (len(t) > 1 or len(p) == 1)]
        elif t not in STOPWORDS and len(t) > 1:
            out.append(t)
    return out


def _word_match(token: str, word: str) -> bool:
    if token == word:
        return True
    if len(word) >= _MIN_PREFIX and token.startswith(word):
        return True
    return len(token) >= _MIN_PREFIX + 1 and word.startswith(token)


_SYN_NORM: List[Set[str]] = [{normalize(w) for w in group} for group in SYNONYMS]


@functools.lru_cache(maxsize=None)
def concepts_of(token: str) -> FrozenSet[int]:
    """Synonym groups of a word (cached: the KB index has ~40k words)."""
    out: Set[int] = set()
    for i, group in enumerate(_SYN_NORM):
        for w in group:
            if " " in w:
                continue  # Mehrwort-Synonyme werden ueber den Volltext geprueft
            if _word_match(token, w):
                out.add(i)
                break
    return frozenset(out)


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


KB_LIMIT = 5            # Knowledge Base hits shown after the help hits
KB_MIN_COVERAGE = 0.5   # share of the search words a KB hit must contain


def search(query: str, limit: int = 12, with_kb: bool = False) -> List[SearchHit]:
    """Sucht in allen Sprachen; Treffer werden pro Eintrag (sprachunabhaengig)
    zusammengefasst. Ranking: Anteil getroffener Suchbegriffe zuerst, dann
    Treffer in der Frage (x3) vor Treffern im Text (x1).
    with_kb: Knowledge-Base-Treffer (ui/kb_search.py) kommen danach, hoechstens
    KB_LIMIT - sie verdraengen nie eine Hilfe-Antwort."""
    hits = _rank(get_index(), query, limit)
    if with_kb:
        try:
            from ui import kb_search
            hits += _rank(kb_search.get_index(), query, KB_LIMIT, KB_MIN_COVERAGE, title_phrase=True)
        except Exception:
            pass
    return hits


def _rank(index: List[HelpEntry], query: str, limit: int, min_coverage: float = 0.0,
          title_phrase: bool = False) -> List[SearchHit]:
    """title_phrase (KB): two search words in a row in the title count extra,
    so "set heater" ranks the station "Set heater" above texts that only
    mention both words somewhere."""
    q_tokens = tokens(query)
    bigrams = [f" {a} {b} " for a, b in zip(q_tokens, q_tokens[1:])] if title_phrase else []
    if not q_tokens:
        return []
    q_norm = normalize(query)
    terms = [(t, concepts_of(t)) for t in q_tokens]
    phrase = _phrase_concepts(q_norm)
    best: Dict[str, SearchHit] = {}
    for e in index:
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
        if bigrams:
            title = f" {' '.join(e.q_tokens)} "
            score += 4 * sum(1 for bg in bigrams if bg in title)
        if matched == 0:
            continue
        coverage = matched / len(terms)
        if (len(terms) >= 3 and coverage < 0.34) or coverage < min_coverage:
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
        for e in index:
            if e.key in best:
                best[e.key].by_lang.setdefault(e.lang, e)
    return sorted(best.values(), key=lambda h: -h.score)[:limit]


# ── texts of the search window (EN/DE/ES/ZH) ──────────────────────────
UI = {
    "en": {"title": "Help – where do I find…?", "placeholder": "What are you looking for? e.g. all orders of a machine",
           "go": "Take me there", "full": "Open full help", "none": "No matching help found. Try other words – "
           "e.g. the name of a screen, a button or what you want to do.",
           "hint": "Describe what you want to do in your own words.", "screen": "Screen",
           "needs_series": "Open a trial series first (e.g. from the Backlog or All Experiments).",
           "areas": "Numbers like (1) refer to the screen sketch in the full help.",
           "ask": "Ask AI", "ask_tip": "Let the AI answer in your own words (uses your AI token quota).",
           "asking": "Asking the AI…", "ai_label": "AI answer", "ai_none": "The help does not cover this question yet.",
           "fb_q": "Did this help?", "fb_up": "Helpful", "fb_down": "Not helpful", "fb_thanks": "Thanks for the feedback!",
           "kb": "Knowledge Base", "kb_open": "Open in Knowledge Base",
           "kb_hint": "Background knowledge: opens the page in a window – close it and you are back here."},
    "de": {"title": "Hilfe – wo finde ich…?", "placeholder": "Was suchst du? z. B. alle Aufträge einer Maschine",
           "go": "Hinführen", "full": "Ganze Hilfe öffnen", "none": "Keine passende Hilfe gefunden. Versuch es mit "
           "anderen Worten – z. B. dem Namen eines Bildschirms, eines Buttons oder was du tun willst.",
           "hint": "Beschreib in eigenen Worten, was du tun willst.", "screen": "Bildschirm",
           "needs_series": "Zuerst eine Versuchsserie öffnen (z. B. aus dem Backlog oder All Experiments).",
           "areas": "Nummern wie (1) verweisen auf die Bildschirm-Skizze in der ganzen Hilfe.",
           "ask": "KI fragen", "ask_tip": "Die KI antwortet in eigenen Worten (verbraucht dein KI-Kontingent).",
           "asking": "Die KI wird gefragt…", "ai_label": "KI-Antwort", "ai_none": "Die Hilfe deckt diese Frage noch nicht ab.",
           "fb_q": "Hat das geholfen?", "fb_up": "Hilfreich", "fb_down": "Nicht hilfreich", "fb_thanks": "Danke für die Rückmeldung!",
           "kb": "Knowledge Base", "kb_open": "In der Knowledge Base öffnen",
           "kb_hint": "Hintergrundwissen: öffnet die Seite in einem Fenster – schliessen, und du bist wieder hier."},
    "es": {"title": "Ayuda – ¿dónde encuentro…?", "placeholder": "¿Qué buscas? p. ej. todos los pedidos de una máquina",
           "go": "Llévame allí", "full": "Abrir la ayuda completa", "none": "No se encontró ayuda. Prueba con "
           "otras palabras – p. ej. el nombre de una pantalla, de un botón o lo que quieres hacer.",
           "hint": "Describe con tus palabras lo que quieres hacer.", "screen": "Pantalla",
           "needs_series": "Primero abre una serie de ensayos (p. ej. desde el Backlog o All Experiments).",
           "areas": "Los números como (1) se refieren al esquema de la pantalla en la ayuda completa.",
           "ask": "Preguntar a la IA", "ask_tip": "La IA responde con sus palabras (usa tu cuota de tokens de IA).",
           "asking": "Preguntando a la IA…", "ai_label": "Respuesta de la IA", "ai_none": "La ayuda aún no cubre esta pregunta.",
           "fb_q": "¿Te ha ayudado?", "fb_up": "Útil", "fb_down": "No útil", "fb_thanks": "¡Gracias por tu opinión!",
           "kb": "Knowledge Base", "kb_open": "Abrir en la Knowledge Base",
           "kb_hint": "Conocimiento de fondo: abre la página en una ventana; al cerrarla vuelves aquí."},
    "zh": {"title": "帮助 – 在哪里找到…？", "placeholder": "你在找什么？例如：某台机器的所有订单",
           "go": "带我过去", "full": "打开完整帮助", "none": "没有找到合适的帮助。换个说法试试 – "
           "例如屏幕名称、按钮名称或你想做的事。",
           "hint": "用你自己的话描述你想做什么。", "screen": "屏幕",
           "needs_series": "请先打开一个试验系列（例如从 Backlog 或 All Experiments）。",
           "areas": "像 (1) 这样的编号指完整帮助中的屏幕示意图。",
           "ask": "询问 AI", "ask_tip": "让 AI 用自己的话回答（消耗你的 AI 额度）。",
           "asking": "正在询问 AI…", "ai_label": "AI 回答", "ai_none": "帮助中还没有涵盖这个问题。",
           "fb_q": "这对你有帮助吗？", "fb_up": "有帮助", "fb_down": "没有帮助", "fb_thanks": "感谢你的反馈！",
           "kb": "知识库", "kb_open": "在知识库中打开",
           "kb_hint": "背景知识：在窗口中打开页面 – 关闭后即回到这里。"},
}

# Screens, die eine geoeffnete Serie brauchen - "Take me there" fuehrt dann zu All Experiments.
NEEDS_SERIES = {"show_experiment", "report"}


def normalize_display(html_text: str) -> str:
    """Frage als Klartext fuer die Ergebnisliste."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", html_text))).strip()
