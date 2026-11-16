"""Search field in every Backlog column (both apps, 2026-11-16): db/series_overview.card_matches + the desktop column."""
import os

os.environ.setdefault("TRIPPLET_MODE", "dev_local")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

from db.series_overview import card_matches  # noqa: E402


def test_card_matches():
    vals = ("2026-73-053", "02 PES 167f72 ASe243 vs P243-3", "eAFK", "soj")
    assert card_matches("", *vals) and card_matches("   ", *vals)
    assert card_matches("ase243", *vals) and card_matches("eafk 167f72", *vals) and card_matches("2026-73 soj", *vals)
    assert not card_matches("ase243 dp2t", *vals)        # every word must match
    assert not card_matches("xyz", *vals)
    assert card_matches("x", None, "", "x")             # empty values are fine


def test_desktop_column_search():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from ui import screen_backlog as sb
    s = sb.BacklogScreen()
    tbl = s.tbl_done["table"]
    if tbl.rowCount() < 2:
        pytest.skip("not enough Done cards on dev_local")
    edit = tbl._search_edit
    name = str(tbl.item(0, 0).data(sb.ROLE_SERIES_NAME))
    edit.setText(name)
    visible = [r for r in range(tbl.rowCount()) if not tbl.isRowHidden(r)]
    assert 0 in visible and len(visible) < tbl.rowCount()
    s.reload_all()                                       # live reload keeps the filter
    assert any(tbl.isRowHidden(r) for r in range(tbl.rowCount()))
    edit.clear()
    assert not any(tbl.isRowHidden(r) for r in range(tbl.rowCount()))
    s.deleteLater()
