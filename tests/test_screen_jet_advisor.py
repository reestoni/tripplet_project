"""Desktop Jet Advisor screen (ui/screen_jet_advisor.py) offscreen, on the synthetic trials of test_jet_advisor."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

from test_jet_advisor import JETS, YARNS, _rows  # noqa: E402  (tests/ is on sys.path under pytest)
from ui import jet_advisor as ja  # noqa: E402


@pytest.fixture
def screen():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from ui.screen_jet_advisor import JetAdvisorScreen
    s = JetAdvisorScreen()
    s._on_loaded(ja.Advisor(_rows(), JETS, YARNS), None)       # instead of the loader thread
    yield s
    s.deleteLater()


def test_find_and_detail(screen, monkeypatch):
    s = screen
    assert s.btn_find.isEnabled() and s.lst_types.count() == 2
    s.cb_yarn.setCurrentIndex(s.cb_yarn.findData(1))
    s._target_edits["fpm"][0].setText("100")
    s._target_edits["stab10"][0].setText("80")
    s.find()
    assert s.tbl.rowCount() == 2
    assert s.tbl.item(0, 1).text() == "STD-A"
    headers = [s.tbl.horizontalHeaderItem(c).text() for c in range(s.tbl.columnCount())]
    assert "Points/m" in headers and "Stab. 1.0" in headers
    assert "STD-A" in s.lbl_detail.text() and s.lst_series.count() > 0 and s.btn_playground.isEnabled()

    # filter: only the development type
    for r in range(s.lst_types.count()):
        it = s.lst_types.item(r)
        from PySide6.QtCore import Qt
        it.setCheckState(Qt.Checked if it.data(Qt.UserRole) == 2 else Qt.Unchecked)
    s.find()
    assert s.tbl.rowCount() == 1 and s.tbl.item(0, 1).text() == "DEV-B"

    # playground button hands the trial over
    seen = []
    import app_meta
    monkeypatch.setattr(app_meta, "open_process_playground", lambda trial_id=None: seen.append(trial_id), raising=False)
    s._open_playground()
    assert seen and seen[0] is not None


def test_own_values_and_errors(screen, monkeypatch):
    s = screen
    msgs = []
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: msgs.append(a[2]))
    s.find()                                                   # no target
    assert msgs and "target" in msgs[-1]
    s._target_edits["fpm"][0].setText("60")
    s.rb_own.setChecked(True)
    s.find()                                                   # no titer / filaments
    assert "titer" in msgs[-1]
    s.ed_endtiter.setText("160")
    s.ed_filaments.setText("48")
    s.cb_material.setCurrentIndex(s.cb_material.findData(11))
    s.find()
    assert s.tbl.rowCount() == 2 and "PES 167f48" in s.lbl_summary.text()
    s._reset()
    assert s.tbl.rowCount() == 0 and s._target_edits["fpm"][0].text() == ""
