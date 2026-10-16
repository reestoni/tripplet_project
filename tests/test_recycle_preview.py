"""Recycle bin preview (ui/recycle_preview.py): read-only Show Experiment and
the decisions - DB simulated. End-to-end on dev_local verified by hand
2026-10-16 (series restored, 0 editable cells, back in the bin with the
original DeletedAt, tab close = back to bin)."""
import datetime

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def fake_bin(monkeypatch):
    from db import recycle_bin
    calls = []
    deleted = datetime.datetime(2026, 10, 1, 8, 30)
    monkeypatch.setattr(recycle_bin, "entry_info", lambda bid: {
        "ID": bid, "DeletedAt": deleted, "DeletedBy": 7, "ObjectID": 311, "Label": "S", "RestoredAt": None,
        "ExperimentPK": 130})
    monkeypatch.setattr(recycle_bin, "restore", lambda bid: calls.append(("restore", bid)) or "S")
    monkeypatch.setattr(recycle_bin, "delete_series",
                        lambda sid, label="", **kw: calls.append(("delete_series", sid, kw)) or 99)
    monkeypatch.setattr(recycle_bin, "delete_permanently", lambda bid: calls.append(("delete_permanently", bid)))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: QMessageBox.Yes))
    import ui.recycle_preview as rp
    monkeypatch.setattr(rp.RecyclePreview, "_refresh_lists", staticmethod(lambda: None))
    return calls, deleted


class _FakeScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.preview = None

    def set_recycle_preview(self, controller, banner):
        self.preview = controller


def _start(monkeypatch):
    import app_meta
    import ui.recycle_preview as rp
    screens = []

    def opener(exp_pk, series_pk, eid, setup):
        s = _FakeScreen()
        setup(s)
        screens.append((exp_pk, series_pk, s))
    monkeypatch.setattr(app_meta, "open_show_experiment_preview", opener, raising=False)
    monkeypatch.setattr("db.connection.fetch_all", lambda *a, **k: [{"EID": "2026-79-005"}])
    p = rp.RecyclePreview({"ID": 5, "Label": "S", "UserName": "A. B", "DeletedAt": None})
    assert p.start(None)
    return p, screens


def test_back_to_bin_keeps_original_date(app, fake_bin, monkeypatch):
    calls, deleted = fake_bin
    p, screens = _start(monkeypatch)
    assert calls[0] == ("restore", 5)
    assert screens[0][:2] == (130, 311) and screens[0][2].preview is p
    assert p.back_to_bin(close_tab=False) == 99
    assert calls[1] == ("delete_series", 311, {"deleted_at": deleted, "deleted_by": 7, "replaces_bin_id": 5})
    assert screens[0][2].preview is None and not p.active
    p.tab_closed()  # already decided -> nothing more
    assert len(calls) == 2


def test_tab_close_and_program_exit_put_it_back(app, fake_bin, monkeypatch):
    import ui.recycle_preview as rp
    calls, _ = fake_bin
    p, _ = _start(monkeypatch)
    p.tab_closed()
    assert [c[0] for c in calls] == ["restore", "delete_series"]
    p2, _ = _start(monkeypatch)
    rp.finish_all()
    assert [c[0] for c in calls] == ["restore", "delete_series", "restore", "delete_series"]
    assert not rp._ACTIVE


def test_keep_and_delete_permanently(app, fake_bin, monkeypatch):
    calls, _ = fake_bin
    p, screens = _start(monkeypatch)
    p.keep()
    p.tab_closed()
    assert [c[0] for c in calls] == ["restore"]  # stays restored
    p2, _ = _start(monkeypatch)
    p2.delete_permanently()
    assert calls[-1] == ("delete_permanently", 99)


def test_preview_makes_only_its_own_tables_read_only(app, monkeypatch):
    import app_meta
    from ui import screen_show_experiment as se
    from ui.widgets.frozen_first_column_table import FrozenFirstColumnTable
    monkeypatch.setattr(app_meta, "access_level", lambda: 4)

    def editable(tbl):
        m = tbl.model()
        return any(m.flags(m.index(r, c)) & Qt.ItemIsEditable
                   for r in range(m.rowCount()) for c in range(1, m.columnCount()))

    def table(host):
        m = se.PivotEditModel(["Tenacity"], ["V1"])
        m._binding = [[object()]]
        t = FrozenFirstColumnTable(host)
        t.setModel(m)
        return t
    preview_host, other_host = QWidget(), QWidget()
    t_prev, t_other = table(preview_host), table(other_host)
    assert editable(t_prev) and editable(t_other)
    preview_host._recycle_preview = object()
    se.RECYCLE_PREVIEWS_OPEN[0] += 1
    try:
        assert not editable(t_prev) and editable(t_other)
    finally:
        se.RECYCLE_PREVIEWS_OPEN[0] -= 1
