"""Checks that every help / What's new text module has a language in exactly the same shape as English.

    python tools/check_help_translations.py [lang] [module ...]      (default: zh, all modules)

For every dict that holds language keys ("en" + at least one other), the language must exist and its
value must have the same structure as "en": same types, same list/tuple lengths, same block kinds
(first tuple item), same dict keys, same {placeholders} / {{svg placeholders}}, same file names (.svg/.png)
and the same number of <b>[Button]</b> markers. Exit code 1 on any difference.
"""
from __future__ import annotations

import importlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODULES = [
    "ui.widgets.help_texts_all_experiments", "ui.widgets.help_texts_backlog", "ui.widgets.help_texts_create_experiment",
    "ui.widgets.help_texts_dashboards", "ui.widgets.help_texts_jet_advisor", "ui.widgets.help_texts_manage_jets",
    "ui.widgets.help_texts_manage_yarn", "ui.widgets.help_texts_process_playground", "ui.widgets.help_texts_report",
    "ui.widgets.help_texts_show_experiment", "ui.widgets.help_texts_smart_chart", "ui.widgets.yarn_stock_help_texts",
    "ui.widgets.whats_new_texts", "ui.help_index",
]
LANG_KEYS = {"en", "de", "es", "zh"}
KINDS = {"p", "h", "task", "note", "warn", "ul", "areas", "table", "svg", "feature"}
_PH = re.compile(r"\{\{?[a-z_0-9]*\}?\}")
_FILE = re.compile(r"[\w./-]+\.(?:svg|png)")
_BTN = re.compile(r"<b>\[")


def _sig(s: str):
    return (sorted(_PH.findall(s)), sorted(_FILE.findall(s)), len(_BTN.findall(s)))


def _compare(en, other, path: str, errs: list) -> None:
    if type(en) is not type(other):
        errs.append(f"{path}: type {type(en).__name__} vs {type(other).__name__}")
        return
    if isinstance(en, str):
        if _sig(en) != _sig(other):
            errs.append(f"{path}: placeholders/files/buttons differ\n    en: {_sig(en)}\n    xx: {_sig(other)}")
        if en.strip() and not other.strip():
            errs.append(f"{path}: empty")
    elif isinstance(en, (list, tuple)):
        if len(en) != len(other):
            errs.append(f"{path}: length {len(en)} vs {len(other)}")
            return
        if isinstance(en, tuple) and en and en[0] in KINDS and en[0] != other[0]:
            errs.append(f"{path}: block kind {en[0]!r} vs {other[0]!r}")
        for i, (a, b) in enumerate(zip(en, other)):
            _compare(a, b, f"{path}[{i}]", errs)
    elif isinstance(en, dict):
        if set(en) != set(other):
            errs.append(f"{path}: keys differ: missing {sorted(set(en) - set(other))}, extra {sorted(set(other) - set(en))}")
        for k in en:
            if k in other:
                _compare(en[k], other[k], f"{path}.{k}", errs)


def _walk(obj, path: str, lang: str, errs: list, seen: set) -> None:
    if id(obj) in seen:
        return
    seen.add(id(obj))
    if isinstance(obj, dict):
        keys = set(obj)
        if "en" in keys and len(keys & LANG_KEYS) >= 2 and keys <= LANG_KEYS | {"default"}:
            if lang not in obj:
                errs.append(f"{path}: language {lang!r} missing")
            else:
                _compare(obj["en"], obj[lang], f"{path}.{lang}", errs)
            return
        for k, v in obj.items():
            _walk(v, f"{path}.{k}", lang, errs, seen)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _walk(v, f"{path}[{i}]", lang, errs, seen)


def check(module: str, lang: str) -> list:
    m = importlib.import_module(module)
    errs: list = []
    for name in dir(m):
        if name.isupper():
            _walk(getattr(m, name), f"{module.split('.')[-1]}.{name}", lang, errs, set())
    return errs


def main(argv) -> int:
    lang = argv[0] if argv and len(argv[0]) == 2 else "zh"
    mods = [a for a in argv if len(a) > 2] or MODULES
    bad = 0
    for mod in mods:
        errs = check(mod, lang)
        print(f"{'OK  ' if not errs else 'FAIL'} {mod} ({len(errs)} problems)")
        for e in errs[:25]:
            print("   ", e)
        bad += bool(errs)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
