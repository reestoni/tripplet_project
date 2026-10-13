"""Strukturtests fuer die mehrsprachigen Kontext-Hilfen (EN/DE/ES):
alle Sprachen gleich aufgebaut, jeder {{key}}-Platzhalter einer Skizze hat
in jeder Sprache einen Text, Skizzen-Dateien existieren."""
import os
import re

import pytest

from ui.widgets.multilang_help import check_texts
from ui.widgets import help_texts_backlog, help_texts_show_experiment, help_texts_report

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULES = [help_texts_backlog, help_texts_show_experiment, help_texts_report]


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
