"""Tools/screens on/off per group and person (db/feature_access.py,
Nutzerwunsch 2026-10-30): superuser > person > group > default (as before)."""
import pytest

from db import feature_access as fa


def test_decide_order():
    d = fa.decide
    assert d("smart_chart", 2, {}, {}) is False and d("smart_chart", 3, {}, {}) is True     # default as before
    assert d("smart_chart", 2, {}, {"smart_chart": True}) is True                          # group
    assert d("smart_chart", 2, {"smart_chart": False}, {"smart_chart": True}) is False     # person wins
    assert d("backlog", 4, {"backlog": False}, {"backlog": False}) is True                 # superuser: everything
    assert d("unknown_tool", 0, {}, {}) is True


def test_every_feature_is_guarded_in_main():
    import os, re
    guarded = set(fa.GUARDED_METHODS.values()) | set(fa.CREATE_MODE_FEATURE.values())
    assert {f.key for f in fa.FEATURES} == guarded
    src = open(os.path.join(os.path.dirname(__file__), "..", "main.py"), encoding="utf-8").read()
    defined = set(re.findall(r"    def (_\w+)\(self", src))
    assert set(fa.GUARDED_METHODS) <= defined, set(fa.GUARDED_METHODS) - defined
    assert len({f.key for f in fa.FEATURES}) == len(fa.FEATURES)


def test_can_use_and_landing(monkeypatch):
    monkeypatch.setattr(fa, "load", lambda force=False: {"level": 2, "user": {"backlog": False},
                                                          "groups": {"smart_chart": True}})
    assert not fa.can_use("backlog") and fa.can_use("smart_chart") and fa.can_use("all_experiments")
    assert fa.landing_key() == "all_experiments"


def _dialog():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from ui.widgets.feature_access_dialog import FeatureAccessDialog
    data = {"groups": [{"ID": 2, "Name": "read", "Level": 1}, {"ID": 1, "Name": "write", "Level": 2},
                       {"ID": 4, "Name": "superuser", "Level": 4}],
            "users": [{"ID": 10, "Name": "Anna Muster", "GroupID": 1}, {"ID": 11, "Name": "Boss", "GroupID": 4}],
            "group_rules": {1: {"backlog": False}}, "user_rules": {}}
    return FeatureAccessDialog(data=data)


def test_dialog_columns_and_cycle():
    dlg = _dialog()
    assert [c["id"] for c in dlg.columns] == [2, 1, 10]          # no superuser group, no superuser person
    row = next(i for i, f in enumerate(dlg.rows) if f is not None and f.key == "backlog")
    anna = 2
    assert dlg.effective(dlg.columns[anna], "backlog") is False   # from her group
    dlg._cycle(row, anna)                                         # -> allowed for Anna
    assert dlg.effective(dlg.columns[anna], "backlog") is True
    dlg._cycle(row, anna)                                         # -> blocked
    dlg._cycle(row, anna)                                         # -> as the group again
    assert dlg.values() == ({1: {"backlog": False}}, {})
    sc = next(i for i, f in enumerate(dlg.rows) if f is not None and f.key == "smart_chart")
    dlg._cycle(sc, 0)                                             # read group gets Smart Chart
    assert dlg.effective(dlg.columns[anna], "smart_chart") is False and dlg.effective(dlg.columns[0], "smart_chart")
    dlg._reset()
    assert dlg.values() == ({}, {})


# ── start screen per user (Settings, display_prefs "start") ──
def test_landing_follows_start_screen(monkeypatch):
    rules = {"level": 2, "user": {}, "groups": {}}
    monkeypatch.setattr(fa, "load", lambda force=False: rules)
    assert fa.landing_key("yarn_stock") == "yarn_stock"
    assert fa.landing_key(None) == "backlog" and fa.landing_key("nonsense") == "backlog"
    rules["user"] = {"yarn_stock": False}
    assert fa.landing_key("yarn_stock") == "backlog"                 # blocked -> Backlog
    rules["user"] = {"yarn_stock": False, "backlog": False}
    assert fa.landing_key("yarn_stock") == "all_experiments"
    assert fa.landing_key("smart_chart") == "all_experiments"        # default level 3, user is write


def test_start_screens_have_a_target_in_main():
    import os
    src = open(os.path.join(os.path.dirname(__file__), "..", "main.py"), encoding="utf-8").read()
    body = src[src.index("    def _go_landing(self)"):src.index("    def _go_home(self)")]
    for key in fa.START_SCREENS:
        assert f'"{key}":' in body, key
        assert key in fa.BY_KEY


def test_settings_fit_into_short_column():
    from ui import display_prefs as dp
    prefs = {**dp.DEFAULTS, "recent_series": [{"exp": i, "series": i, "eid": "2026-71-013", "name": "x" * 40}
                                              for i in range(8)], "start": "dashboards"}
    raw = dp._fit(prefs, 255)
    import json
    data = json.loads(raw)
    assert len(raw) <= 255 and data["start"] == "dashboards" and 0 < len(data["recent_series"]) < 8
    assert len(json.loads(dp._fit(prefs, 0))["recent_series"]) == 8          # TEXT column: everything
    assert dp._clean({"start": "yarn_stock"})["start"] == "yarn_stock" and dp._clean({})["start"] == "backlog"
