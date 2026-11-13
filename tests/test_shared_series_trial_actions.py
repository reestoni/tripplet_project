"""Qt-free series / trial actions shared by desktop and web (db/series_actions,
db/trial_actions, db/trial_copy, db/series_yarns, db/label_sheets,
db/trial_labels, db/lab_pdf_import): import without PySide6, permission
rules, rename prefix, yarn-reassign plan, import message. No database."""
import os
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULES = ["db.series_actions", "db.trial_actions", "db.trial_copy", "db.series_yarns",
           "db.label_sheets", "db.trial_labels", "db.lab_pdf_import"]


def test_modules_import_without_pyside6():
    code = (
        "import sys, importlib, importlib.abc\n"
        "class B(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, name, path, target=None):\n"
        "        if name == 'PySide6' or name.startswith('PySide6.'):\n"
        "            raise ImportError('blocked ' + name)\n"
        "sys.meta_path.insert(0, B())\n"
        f"for m in {MODULES!r}:\n"
        "    importlib.import_module(m)\n"
        "assert not any(k.startswith('PySide6') for k in sys.modules)\n"
        "print('ok')\n"
    )
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().endswith("ok")


def test_desktop_modules_reexport_the_shared_code():
    from db import label_sheets, series_yarns, trial_actions, trial_copy
    from ui import copy_trials_dialog, series_yarns_dialog
    from ui.widgets import label_printing
    import ui.screen_show_experiment as sse
    assert copy_trials_dialog.build_copy_fields is trial_copy.build_copy_fields
    assert series_yarns_dialog.apply_plan is series_yarns.apply_plan
    assert label_printing.generate_label_sheet_pdf is label_sheets.generate_label_sheet_pdf
    assert sse._col_not_copied is trial_actions.col_not_copied


@pytest.mark.parametrize("lvl, rename, machine, trials", [
    (0, False, False, False), (1, False, False, False), (2, True, False, True),
    (3, True, False, True), (4, True, True, True),
])
def test_rules(lvl, rename, machine, trials):
    from db import series_actions as sa, series_yarns as sy, trial_actions as ta
    user = {"id": 7, "access_level": lvl}
    assert sa.can_rename(user) is rename
    assert sa.can_rename(lvl) is rename            # a plain level works too
    assert sa.can_change_machine(user) is machine
    assert ta.can_reassign_yarn(user) is machine
    assert ta.can_edit_trials(user) is trials
    assert sy.can_edit(user) is trials
    assert sa.can_change_prio(user)
    assert sa.can_save_notes(user) is trials       # since 2026-11-13: write access needed


def test_feature_tracking_gets_the_user():
    # until 2026-11-13 getattr() on the user DICT gave None and the INSERT failed silently
    from db.series_actions import legacy_feature_user_id
    assert legacy_feature_user_id({"id": 5}) == 5


@pytest.mark.parametrize("full, prefix, rest", [
    ("f(03 ) abc", "f(03 ) ", "abc"), ("03 abc", "03 ", "abc"), ("abc", "", "abc"),
    (" A(12)  x y", " A(12)  ", "x y"), ("12abc", "", "12abc"), ("", "", ""),
])
def test_split_prefix(full, prefix, rest):
    from db.series_actions import split_prefix
    assert split_prefix(full) == (prefix, rest)


def test_compose_name():
    from db.series_actions import compose_name
    assert compose_name("03 ", "  New name ") == "03 New name"
    assert compose_name("", "x") == "x"
    assert compose_name("03 ", "   ") is None


def _plan(monkeypatch, rows, db_conflicts=()):
    from db import trial_actions as ta
    calls = []

    def fake_fetch_all(sql, params=()):
        calls.append(sql)
        if "SELECT ID FROM tblTrial" in sql:
            return [{"ID": 11}, {"ID": 12}]
        return [{"YarnName": n} for n in db_conflicts]
    monkeypatch.setattr(ta, "fetch_all", fake_fetch_all)
    return ta.plan_yarn_reassign(1, rows, {1: "A", 2: "B"}), calls


def test_yarn_plan_relabels_kept_plies(monkeypatch):
    rows = [{"orig_ply": "Ply 1", "orig_yid": 1, "new_yid": 1, "deleted": True, "is_new": False},
            {"orig_ply": "Ply 2", "orig_yid": 2, "new_yid": 2, "deleted": False, "is_new": False},
            {"orig_ply": None, "orig_yid": None, "new_yid": 1, "deleted": False, "is_new": True}]
    plan, _ = _plan(monkeypatch, rows)
    assert plan["trial_ids"] == [11, 12]
    assert [r.get("new_ply") for r in plan["rows"]] == [None, "Ply 1", "Ply 2"]
    assert plan["conflicts"] == []


def test_yarn_plan_changing_a_yarn_is_allowed(monkeypatch):
    # the old DB check compared against the yarn being replaced and blocked every change
    rows = [{"orig_ply": "Ply 1", "orig_yid": 1, "new_yid": 2, "deleted": False, "is_new": False}]
    plan, _ = _plan(monkeypatch, rows, db_conflicts=["A"])
    assert plan["conflicts"] == [] and plan["rows"][0]["new_ply"] == "Ply 1"


def test_yarn_plan_two_yarns_on_one_ply_stay_one_ply(monkeypatch):
    rows = [{"orig_ply": "Ply 1", "orig_yid": 1, "new_yid": 1, "deleted": False, "is_new": False},
            {"orig_ply": "Ply 1", "orig_yid": 2, "new_yid": 2, "deleted": False, "is_new": False},
            {"orig_ply": "Ply 2", "orig_yid": 3, "new_yid": 3, "deleted": False, "is_new": False}]
    plan, _ = _plan(monkeypatch, rows)
    assert [r["new_ply"] for r in plan["rows"]] == ["Ply 1", "Ply 1", "Ply 2"]
    assert plan["conflicts"] and "within dialog" in plan["conflicts"][0]   # series rule: one yarn per ply


def test_yarn_apply_refuses_a_plan_with_conflicts():
    from db import trial_actions as ta
    with pytest.raises(ValueError):
        ta.apply_yarn_reassign(1, {"conflicts": ["x"], "rows": [], "trial_ids": []})


def test_yarn_plan_needs_one_ply(monkeypatch):
    rows = [{"orig_ply": "Ply 1", "orig_yid": 1, "new_yid": 1, "deleted": True, "is_new": False}]
    with pytest.raises(ValueError):
        _plan(monkeypatch, rows)


def test_col_not_copied():
    from db.trial_actions import col_not_copied
    assert col_not_copied("YarnTensionAfterJet") and col_not_copied("Comment3")
    assert not col_not_copied("AirPressure")


def test_import_message_lists_and_truncates():
    from db.lab_pdf_import import import_message
    msg = import_message("Import finished.", "Imported spools", 3, [f"s{i}" for i in range(52)], ["e"])
    assert msg.startswith("Import finished.\n\nImported spools: 3\n\nSkipped:\ns0")
    assert "... (2 weitere)" in msg and msg.endswith("Errors:\ne")


def test_label_sheet_bytes_has_one_page_per_sheet():
    fitz = pytest.importorskip("fitz")
    from db.label_sheets import DEFAULT_TEMPLATE, label_sheet_pdf_bytes
    from db.trial_labels import draw_trial_label_cell, trial_label_items
    tpl = dict(DEFAULT_TEMPLATE)          # 3 x 8 = 24 labels per sheet
    data = label_sheet_pdf_bytes(trial_label_items("2026-71-014.01", 1, 30), tpl, 0, draw_trial_label_cell)
    doc = fitz.open(stream=data, filetype="pdf")
    assert doc.page_count == 2
    text = "".join(p.get_text() for p in doc)
    assert "V1\n" in text and "V30" in text and "2026-71-014.01" in text
