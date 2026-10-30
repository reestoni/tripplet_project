"""Dashboards page + sharing (Etappe 6, Nutzerentscheid 2026-10-30): only the
creator shares, per person or group (tblAccessRight), view or edit.
End-to-end on dev_local verified: creator shares with a person (view) and his
own group (edit) -> person sees it read-only under "Shared with me" (no
Edit button, drag/Delete do nothing, slicer filters 140 -> 26 experiments,
nothing saved), group member gets "edit", deleting removes the shares."""
from db import smart_chart_views as views


def test_right_for_owner_person_group_everybody():
    r = views.right_for
    assert r(1, 0, [], 1, 4) == "owner"
    assert r(1, 0, [], 2, 1) is None                                   # private
    assert r(1, 1, [], 2, 1) == "view"                                 # everybody
    assert r(1, 0, [{"UserID": 2, "CanEdit": 0}], 2, 1) == "view"
    assert r(1, 0, [{"AccessRightID": 1, "CanEdit": 1}], 2, 1) == "edit"
    assert r(1, 0, [{"AccessRightID": 4, "CanEdit": 1}], 2, 1) is None   # other group
    # edit wins over view, also when "everybody" is ticked
    assert r(1, 1, [{"UserID": 2, "CanEdit": 0}, {"AccessRightID": 1, "CanEdit": 1}], 2, 1) == "edit"


def test_permissions(monkeypatch):
    monkeypatch.setattr(views, "_user", lambda: (2, 2))
    mine, edit, view = ({"UserID": 2, "MyRight": "owner"}, {"UserID": 1, "MyRight": "edit"},
                        {"UserID": 1, "MyRight": "view"})
    assert views.can_share(mine) and not views.can_share(edit) and not views.can_share(view)
    assert views.can_change(mine) and views.can_change(edit) and not views.can_change(view)
    assert views.can_delete(mine) and not views.can_delete(edit)
    monkeypatch.setattr(views, "_user", lambda: (9, 4))                 # superuser: change/delete, not share
    assert views.can_delete(view) and views.can_change(view) and not views.can_share(view)


def test_share_dialog():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ui.smart_share_dialog import ShareDialog
    targets = {"people": [{"ID": 2, "Name": "Anna"}, {"ID": 3, "Name": "Ben"}],
               "groups": [{"ID": 1, "Name": "write"}, {"ID": 4, "Name": "superuser"}]}
    dlg = ShareDialog({"ID": 7, "Name": "Stats", "IsShared": 0}, targets=targets,
                      shares=[{"UserID": 2, "AccessRightID": None, "CanEdit": 1, "Name": "Anna"}])
    assert dlg.cmb_who.count() == 3                                    # Anna already in the list
    dlg.cmb_who.setCurrentIndex([dlg.cmb_who.itemData(i)[1] for i in range(3)].index(1))   # group write
    dlg.cmb_right.setCurrentIndex(0)
    dlg._add()
    dlg.chk_all.setChecked(True)
    everybody, entries = dlg.values()
    assert everybody is True
    assert entries == [{"UserID": 2, "AccessRightID": None, "CanEdit": True},
                       {"UserID": None, "AccessRightID": 1, "CanEdit": False}]
    dlg._remove(dlg.entries[0])
    assert [e["AccessRightID"] for e in dlg.entries] == [1] and dlg.cmb_who.count() == 3
