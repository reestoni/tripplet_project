"""Regressionstests fuer die Hilfe-Suche (ui/widgets/help_search.py):
typische Laienfragen in DE/EN/ES muessen die richtige Anleitung ganz oben
liefern. Faellt ein Test nach einer Textaenderung, Synonyme oder die
Formulierung der betroffenen Anleitung pruefen."""
import pytest

from ui.widgets.help_search import search, get_index, normalize, SOURCES


@pytest.mark.parametrize("query, screen, lang", [
    ("wo kann ich alle aufträge einer maschine einsehen?", "all_experiments", "de"),
    ("where are all orders of a machine", "all_experiments", "en"),
    ("dónde veo todos los pedidos de una máquina", "all_experiments", "es"),
    ("neue lieferung garn erfassen", "yarn_stock", "de"),
    ("wie lösche ich eine düse", "manage_jets", "de"),
    ("where do I see which trials used a yarn", "manage_yarn", "en"),
    ("wer hat die spule ausgebucht", "yarn_stock", "de"),
    ("cómo cambio el estado de una serie", "all_experiments", "es"),
    ("wie viel garn haben wir noch", "yarn_stock", "de"),
    ("mindestbestand ändern", "yarn_stock", "de"),
    ("nachmessung markieren", "show_experiment", "de"),
    ("inventur machen", "yarn_stock", "de"),
    ("report als pdf", "report", "de"),
])
def test_top_hit(query, screen, lang):
    hits = search(query, 3)
    assert hits, query
    assert hits[0].screen == screen, (query, [(h.screen, h.key) for h in hits])
    assert hits[0].best_lang == lang, (query, hits[0].best_lang)


def test_index_covers_all_sources_and_languages():
    idx = get_index()
    screens = {e.screen for e in idx}
    assert screens == {s for s, _n, _m, _f in SOURCES}
    assert {e.lang for e in idx} == {"en", "de", "es"}


def test_empty_and_stopword_queries():
    assert search("") == []
    assert search("wo ist das") == []


def test_normalize_folds_umlauts_and_accents():
    assert normalize("Düse Größe máquina") == "duse grosse maquina"


def test_usage_stats_help_summary_orders_by_need():
    from datetime import datetime
    from ui.screen_usage_stats import summarize_help_events
    t = datetime(2026, 10, 13, 12, 0)
    ev = [
        {"EventName": "help_search_open", "Detail": "Etiketten drucken -> yarn_stock:tasks_change:1", "Username": "a", "EventTime": t},
        {"EventName": "help_search_noresult", "Detail": "Wo ist der Kaffee | hits=0", "Username": "a", "EventTime": t},
        {"EventName": "help_search_noresult", "Detail": "wo ist der kaffee | hits=0", "Username": "b", "EventTime": t},
        {"EventName": "help_feedback_down", "Detail": "spule suchen -> yarn_stock:tasks_find:2 (AI)", "Username": "a", "EventTime": t},
        {"EventName": "screen_open", "Detail": "", "Username": "a", "EventTime": t},
    ]
    rows, summary = summarize_help_events(ev)
    assert [r["Kind"] for r in rows] == ["No result", "Not helpful", "Opened"]
    assert rows[0]["Count"] == 2 and rows[0]["Users"] == 2 and rows[0]["Question"] == "wo ist der kaffee"
    assert "No result: 2" in summary
