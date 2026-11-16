"""Admin "Projects" (2026-11-16, both apps): db/master_tables KINDS["projects"] + ui/screen_manage_projects.py."""
import os

os.environ.setdefault("TRIPPLET_MODE", "dev_local")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

from db import master_tables as mt  # noqa: E402

K = mt.KINDS["projects"]


def test_rules():
    rows = mt.load_rows(K)
    if not rows:
        pytest.skip("no projects on dev_local")
    assert "UsedBy" in rows[0]
    used = [r for r in rows if r["UsedBy"]]
    if used:
        with pytest.raises(mt.InUse):
            mt.delete(K, [used[0]["ID"]])
    new_id = mt.create(K)
    try:
        if rows[0].get("ProjectNumber") is not None:
            with pytest.raises(mt.NumberTaken):
                mt.save_changes(K, [{"ID": new_id, "ProjectNumber": rows[0]["ProjectNumber"]}])
        assert mt.save_changes(K, [{"ID": new_id, "ProjectNumber": 999992, "ProjectName": "zz desktop project",
                                    "UsedBy": 5}]) == 1          # UsedBy is computed - dropped, not written
    finally:
        assert mt.delete(K, [new_id]) == 1


def test_screen():
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from ui.screen_manage_projects import ManageProjectsScreen
    s = ManageProjectsScreen()
    m = s.model
    h = m.headers()
    if not m.rowCount():
        pytest.skip("no projects on dev_local")
    assert not m.flags(m.index(0, h.index("UsedBy"))) & Qt.ItemIsEditable
    assert m.flags(m.index(0, h.index("ProjectName"))) & Qt.ItemIsEditable
    s.set_read_only(True)
    assert not s.btn_new.isEnabled() and not (m.flags(m.index(0, h.index("ProjectName"))) & Qt.ItemIsEditable)
    s.deleteLater()
