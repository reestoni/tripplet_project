"""Strukturtests fuer die mehrsprachigen Kontext-Hilfen (EN/DE/ES):
alle Sprachen gleich aufgebaut, jeder {{key}}-Platzhalter einer Skizze hat
in jeder Sprache einen Text, Skizzen-Dateien existieren."""
import os
import re

import pytest

from ui.widgets.multilang_help import check_texts
from ui.widgets import (
    help_texts_backlog, help_texts_show_experiment, help_texts_report,
    help_texts_all_experiments, help_texts_create_experiment, help_texts_manage_yarn, help_texts_manage_jets,
    help_texts_smart_chart, help_texts_dashboards, help_texts_process_playground,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULES = [help_texts_backlog, help_texts_show_experiment, help_texts_report,
           help_texts_all_experiments, help_texts_create_experiment, help_texts_manage_yarn, help_texts_manage_jets,
           help_texts_smart_chart, help_texts_dashboards, help_texts_process_playground]


@pytest.mark.parametrize("mod", MODULES, ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def test_structure_identical_in_all_languages(mod):
    check_texts(mod.TEXTS)


@pytest.mark.parametrize("mod", MODULES, ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def test_svg_placeholders_filled_in_every_language(mod):
    for lang, t in mod.TEXTS.items():
        for tab in t["tabs"]:
            for block in tab["blocks"]:
                if block[0] != "svg":
                    continue
                path = os.path.join(ROOT, block[1])
                assert os.path.exists(path), path
                with open(path, encoding="utf-8") as fh:
                    keys = set(re.findall(r"\{\{(\w+)\}\}", fh.read()))
                assert keys == set(block[2]), (lang, tab["key"], keys ^ set(block[2]))


def test_whats_new_texts_same_structure():
    import os
    import app_meta
    from ui.whats_new import release_version, SKETCH_DIR
    from ui.widgets.whats_new_texts import RELEASES
    versions = [r["version"] for r in RELEASES]
    assert "current" not in versions[1:]  # the version being worked on always comes first
    resolved = [release_version(r) for r in RELEASES]
    assert len(resolved) == len(set(resolved)), resolved  # each version only once
    assert resolved[0] == app_meta.APP_VERSION or versions[0] != "current"
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for r in RELEASES:
        assert bool(r["date"]) == (r["version"] != "current"), r["version"]
        assert set(r["texts"]) == {"en", "de", "es", "zh"}
        ref = r["texts"]["en"]
        assert ref, "a release without features must not exist"
        for lang, blocks in r["texts"].items():
            assert [b[0] for b in blocks] == [b[0] for b in ref], (r["version"], lang)
            for b, b_en in zip(blocks, ref):
                if b[0] == "feature":
                    assert len(b) == 5 and b[4] == b_en[4], (lang, b[1])  # same sketch in every language
                    if b[4]:
                        assert os.path.isfile(os.path.join(root, SKETCH_DIR, b[4])), b[4]


def test_whats_new_seen_once(monkeypatch):
    from ui import display_prefs, whats_new
    monkeypatch.setattr(display_prefs, "save_now", lambda: None)
    monkeypatch.setattr(display_prefs, "_save_later", lambda: None)
    display_prefs._prefs = dict(display_prefs.DEFAULTS)
    shown = []
    monkeypatch.setattr(whats_new, "show_whats_new", lambda parent=None: (shown.append(1), whats_new.mark_seen()))
    whats_new.show_if_unseen()
    whats_new.show_if_unseen()
    assert shown == [1]
    assert display_prefs.current()["whats_new_seen"] == whats_new.current_release_id()
    display_prefs._prefs = dict(display_prefs.DEFAULTS)


def test_whats_new_current_date(monkeypatch, tmp_path):
    import sys
    from ui import whats_new
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert whats_new._current_when("en") == "in progress"
    exe = tmp_path / "TrippleT.exe"
    exe.write_text("x")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    import datetime
    assert whats_new._current_when("de") == datetime.date.today().strftime("%d.%m.%Y")


def test_whats_new_dialog_lists_versions(monkeypatch):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    import ui.widgets.multilang_help as mh
    monkeypatch.setattr(mh, "save_language", lambda lang: None)  # don't touch the real language setting
    from ui import display_prefs
    from ui.whats_new import WhatsNewDialog
    from ui.widgets import whats_new_texts as W
    old = {"version": "4.6.2", "date": "2026-10-13",
           "texts": {l: [("h", "Help"), ("feature", "x", "y", "z", None)] for l in ("en", "de", "es")}}
    monkeypatch.setattr(W, "RELEASES", W.RELEASES + [old])
    import ui.whats_new as wn
    monkeypatch.setattr(wn, "RELEASES", W.RELEASES)
    display_prefs._prefs = dict(display_prefs.DEFAULTS, whats_new_seen="4.6.2")
    dlg = WhatsNewDialog(language="en")
    last = len(W.RELEASES) - 1           # the appended 4.6.2
    assert dlg.lst.count() == len(W.RELEASES)
    assert dlg.lst.item(0).text().endswith("NEW") and not dlg.lst.item(last).text().endswith("NEW")
    dlg.lst.setCurrentRow(last)
    dlg.set_language("de")
    assert dlg.lst.item(last).text().startswith("Version 4.6.2\n13.10.2026")
    display_prefs._prefs = dict(display_prefs.DEFAULTS)


def test_whats_new_search(monkeypatch):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    import ui.widgets.multilang_help as mh
    monkeypatch.setattr(mh, "save_language", lambda lang: None)
    from ui import display_prefs
    import ui.whats_new as wn
    from ui.widgets import whats_new_texts as W
    old = {"version": "4.6.2", "date": "2026-10-13",
           "texts": {"en": [("h", "Stock"), ("feature", "Barcode scanner", "Scan a spool.", "Yarn Stock", None)],
                     "de": [("h", "Lager"), ("feature", "Strichcode-Leser", "Spule scannen.", "Yarn Stock", None)],
                     "es": [("h", "Stock"), ("feature", "Lector", "Escanear bobina.", "Yarn Stock", None)]}}
    monkeypatch.setattr(wn, "RELEASES", W.RELEASES + [old])
    old_idx = len(W.RELEASES)
    # any language, word start, every word must match
    assert wn.search_features("Strichcode") == [(old_idx, 1)]
    assert wn.search_features("barc") == [(old_idx, 1)]
    assert (old_idx, 1) in wn.search_features("spule scannen")  # synonyms also find related Yarn Stock cards
    assert wn.search_features("barcode reference") == []
    assert wn.search_features("") == []
    ref_idx = next(i for i, r in enumerate(W.RELEASES) if r["version"] == "4.6.3")   # "Reference samples"
    assert any(ri == ref_idx for ri, _ in wn.search_features("Referenz"))
    display_prefs._prefs = dict(display_prefs.DEFAULTS, whats_new_seen="4.6.2")
    dlg = wn.WhatsNewDialog(language="de")
    dlg.search.setText("Strichcode")
    dlg._apply_search()
    assert dlg._hits == [(old_idx, 1)]
    assert not dlg.lst.item(0).flags() & wn.Qt.ItemIsEnabled  # current version: no hit
    assert dlg.lst.item(old_idx).text().endswith("1 Treffer")
    dlg.set_language("en")  # search survives a language switch
    assert dlg.lst.item(old_idx).text().endswith("1 hits")
    dlg.search.setText("")
    dlg._apply_search()
    assert dlg.lst.item(0).flags() & wn.Qt.ItemIsEnabled and dlg.lst.currentRow() >= 0
    display_prefs._prefs = dict(display_prefs.DEFAULTS)


def test_whats_new_pdf_sections_stay_on_one_page(tmp_path):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from ui.whats_new_pdf import export_release_pdf, _markup
    from ui.widgets.whats_new_texts import RELEASES
    assert _markup("a&nbsp;<b>b</b> <x>", True) == "a\xa0<b>b</b> &lt;x&gt;"
    for lang in ("en", "de", "es"):
        path = tmp_path / f"wn_{lang}.pdf"
        assert export_release_pdf(0, lang, str(path)) >= 1
        assert path.stat().st_size > 10_000
    fitz = __import__("pytest").importorskip("fitz")
    doc = fitz.open(str(tmp_path / "wn_en.pdf"))
    pages = [" ".join(p.get_text().split()) for p in doc]
    section = None
    for block in RELEASES[0]["texts"]["en"]:
        if block[0] == "h":
            section = [i for i, t in enumerate(pages) if block[1] in t]
        elif block[0] == "feature" and section:
            title = " ".join(block[1].split())[:25]
            assert any(title in pages[i] for i in section), (block[1], section)  # card on its heading's page


def test_whats_new_tabs_per_section(monkeypatch):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    import ui.widgets.multilang_help as mh
    monkeypatch.setattr(mh, "save_language", lambda lang: None)
    from ui import display_prefs
    import ui.whats_new as wn
    rel = {"version": "current", "date": "", "texts": {l: [
        ("p", "intro"), ("h", "A & B"), ("feature", "x", "y", "z", None), ("feature", "x2", "y", "z", None),
        ("h", "C"), ("feature", "x3", "y", "z", None)] for l in ("en", "de", "es")}}
    secs = wn.release_sections(rel, "en")
    assert [(t, [b[0] for b in bl]) for t, bl in secs] == [("A & B", ["p", "feature", "feature"]), ("C", ["feature"])]
    assert wn.release_sections({"texts": {"en": [("feature", "x", "y", "z", None)]}}, "en") == \
        [("", [("feature", "x", "y", "z", None)])]
    from ui.widgets import whats_new_texts as W
    # a top release with two sections - independent of what the real current entry holds
    monkeypatch.setattr(wn, "RELEASES", [rel] + [r for r in W.RELEASES if r["version"] != "current"])
    display_prefs._prefs = dict(display_prefs.DEFAULTS)
    dlg = wn.WhatsNewDialog(language="en")
    sections = wn.release_sections(wn.RELEASES[0], "en")
    assert dlg.tabs.count() == len(sections)
    assert dlg.tabs.tabText(0).startswith(sections[0][0].replace("&", "&&"))
    dlg.tabs.setCurrentIndex(1)
    dlg.set_language("de")  # same tab position after switching the language
    assert dlg.tabs.currentIndex() == 1
    dlg.search.setText("Ref")
    dlg._apply_search()
    assert dlg.right.currentWidget() is dlg.scroll  # search = one list
    dlg.search.setText("")
    dlg._apply_search()
    assert dlg.right.currentWidget() is dlg._release_view
    display_prefs._prefs = dict(display_prefs.DEFAULTS)
