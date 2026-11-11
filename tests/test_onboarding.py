"""Onboarding modules (ui/onboarding_catalog.py, assets/onboarding/)."""
import os
import re

from ui import onboarding_catalog as cat
from ui.pathutil import resource_path


def _texts(key):
    texts = cat.module_texts(key)
    assert texts, key
    return texts


def _shape(v):
    """Structure without the text: dict keys, list lengths, placeholders."""
    if isinstance(v, dict):
        return {k: _shape(x) for k, x in sorted(v.items()) if k != "s"}  # "s" = optional short name
    if isinstance(v, list):
        return [_shape(x) for x in v]
    return sorted(re.findall(r"\{(\w+)\}", v)) if isinstance(v, str) else type(v).__name__


def test_catalog_complete():
    keys = [m.key for m in cat.MODULES]
    assert len(keys) == len(set(keys))
    for m in cat.MODULES:
        assert m.category in cat.CATEGORIES or (m.key == cat.START_MODULE and m.category == cat.START_CATEGORY)
        assert not m.group or m.group in cat.GROUPS, m.key
        assert os.path.exists(resource_path(m.file)), m.file
        for d in (m.title, m.summary):
            assert set(d) == set(cat.LANGS)
    for d in list(cat.CATEGORIES.values()) + list(cat.GROUPS.values()) + list(cat.UI.values()):
        assert set(d) == set(cat.LANGS)
    for _code, _name, flag in cat.LANGUAGES:
        assert os.path.exists(resource_path(f"assets/images/{flag}"))


def test_module_texts_same_structure_in_all_languages():
    for m in cat.MODULES:
        texts = _texts(m.key)
        assert set(texts) == set(cat.LANGS), m.key
        ref = _shape(texts["en"])
        for lang in cat.LANGS:
            assert _shape(texts[lang]) == ref, (m.key, lang)


def test_pages_have_no_external_resources():
    for m in cat.MODULES:
        html = open(resource_path(m.file), encoding="utf-8").read()
        assert not re.search(r"""(src|href)\s*=\s*["']https?://""", html), m.key
        assert "window.setLang" in html and "window.goScene" in html
        for lang in cat.LANGS:
            assert all(cat.scene_names(m.key, lang))


def test_quiz_consistent_in_all_languages():
    for m in cat.MODULES:
        texts = _texts(m.key)
        ref = texts["en"].get("quiz")
        if not ref:
            continue
        html = open(resource_path(m.file), encoding="utf-8").read()
        assert 'src="quiz.js"' in html, m.key
        for lang in cat.LANGS:
            quiz = texts[lang]["quiz"]
            n_scenes = len(texts[lang]["scenes"])
            assert [(q["c"], q["sc"]) for q in quiz] == [(q["c"], q["sc"]) for q in ref], (m.key, lang)
            for q in quiz:
                assert 0 <= q["c"] < len(q["a"]) and 0 <= q["sc"] < n_scenes, (m.key, lang, q["q"])
                assert len(set(q["a"])) == len(q["a"]) and q["q"] and q["e"], (m.key, lang, q["q"])
            assert cat.scene_names(m.key, lang)[-1] == cat.text(cat.QUIZ_TAB, lang)


def test_quiz_pass_threshold_matches_page():
    js = open(resource_path("assets/onboarding/quiz.js"), encoding="utf-8").read()
    assert f"const PASS={cat.QUIZ_PASS};" in js
    assert cat.quiz_passed(8, 10) and not cat.quiz_passed(7, 10)


def test_quiz_result_keeps_best(tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings
    from ui import screen_onboarding as so
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
    monkeypatch.setattr(so, "QSettings", lambda org, app: QSettings(QSettings.IniFormat, QSettings.UserScope, org, app))
    assert so.load_quiz_result("x") is None
    so.save_quiz_result("x", 9, 10)
    so.save_quiz_result("x", 6, 10)          # worse attempt does not overwrite the pass
    assert so.load_quiz_result("x") == (9, 10)
    so.save_quiz_result("x", 10, 10)
    assert so.load_quiz_result("x") == (10, 10)


def test_every_category_has_an_area():
    assert set(cat.CATEGORY_AREA) == set(cat.CATEGORIES)
    assert set(cat.CATEGORY_AREA.values()) <= set(cat.AREAS)
    for d in cat.AREAS.values():
        assert set(d) == set(cat.LANGS)
    # areas appear in their own order: categories of one area are next to each other
    order = [cat.CATEGORY_AREA[c] for c in cat.CATEGORIES]
    seen = []
    for a in order:
        if not seen or seen[-1] != a:
            assert a not in seen, f"categories of area {a} are split up"
            seen.append(a)
    assert seen == [a for a in cat.AREAS if a in seen]


def test_module_links_point_to_existing_modules():
    keys = {m.key for m in cat.MODULES}
    for m in cat.MODULES:
        html = open(resource_path(m.file), encoding="utf-8").read()
        for k in re.findall(r"LINK_KEYS=\[([^\]]*)\]", html):
            for key in re.findall(r"'([a-z_]+)'", k):
                assert key in keys, (m.key, key)


def test_start_page_links_every_module():
    """The start page (textile chain) is the map of the whole Knowledge Base: every
    other module must appear in its LINK_KEYS - add new modules there too."""
    start = next(m for m in cat.MODULES if m.key == cat.START_MODULE)
    assert start.category not in cat.CATEGORIES      # stand-alone entry above the areas
    html = open(resource_path(start.file), encoding="utf-8").read()
    linked = set()
    for k in re.findall(r"LINK_KEYS=\[([^\]]*)\]", html):
        linked |= set(re.findall(r"'([a-z_]+)'", k))
    missing = {m.key for m in cat.MODULES} - linked - {start.key}
    assert not missing, f"not on the textile chain start page: {sorted(missing)}"
