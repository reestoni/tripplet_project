"""Desktop Canvas <-> boards (ui/screen_canvas.py + db/canvas_boards.py): geometry round trip, local files stored
with the board, autosave. dev_local; the test board is deleted again."""
import os

os.environ.setdefault("TRIPPLET_MODE", "dev_local")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

from db import canvas_boards as cb  # noqa: E402

pytestmark = pytest.mark.skipif(not cb.table_ready(), reason="tblCanvasBoard missing")


@pytest.fixture
def env(monkeypatch, tmp_path):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    import app_meta
    from db.connection import fetch_all
    uid = fetch_all("SELECT ID FROM tblUser ORDER BY ID LIMIT 1")[0]["ID"]
    monkeypatch.setattr(app_meta, "current_user", {"id": uid, "username": "t", "access_level": 4}, raising=False)
    monkeypatch.setenv("TRIPPLET_DIR_CANVAS_FILES", str(tmp_path / "boards"))
    from db import feature_access
    monkeypatch.setattr(feature_access, "can_use", lambda key: True)
    made = []
    yield tmp_path, made
    for b in made:
        cb.delete_board(b)


def _png(path, w=120, h=80):
    from PySide6.QtGui import QColor, QPixmap
    pm = QPixmap(w, h)
    pm.fill(QColor(200, 30, 30))
    pm.save(str(path), "PNG")
    return pm


def test_board_roundtrip_geometry_and_files(env):
    tmp, made = env
    from ui.screen_canvas import CanvasScreen
    scr = CanvasScreen()
    pm = _png(tmp / "pic.png")
    item = scr._view.add_image(pm, "pic.png", source_path=str(tmp / "pic.png"))
    item.set_scale(0.7)
    item.set_angle(30)
    item.setPos(100, 50)
    doc = scr._view.board_document()
    assert doc["items"][0]["src"]["kind"] == "local"
    g = {k: doc["items"][0][k] for k in ("cx", "cy", "w", "h", "angle")}
    assert abs(g["w"] - 84) < 1e-6 and abs(g["h"] - 56) < 1e-6

    bid = cb.create_board("Desktop test", None)
    made.append(bid)
    saved = cb.save_board(bid, scr._store_local_files(bid, scr._view.board_document()), 1)
    assert saved == 2
    b = cb.get_board(bid)
    src = b["content"]["items"][0]["src"]
    assert src["kind"] == "file" and cb.file_path(bid, src["file"])

    scr2 = CanvasScreen()
    missing = scr2._view.load_board(b["content"], bid)
    assert missing == []
    d2 = scr2._view.board_document()["items"][0]
    for k, v in g.items():
        assert abs(d2[k] - v) < 1e-6, k
    assert d2["src"] == src


def test_autosave_tick(env):
    tmp, made = env
    from ui.screen_canvas import CanvasScreen
    scr = CanvasScreen()
    bid = cb.create_board("Autosave test", None)
    made.append(bid)
    scr._board = {"id": bid, "title": "Autosave test", "series_id": None, "version": 1}
    scr._ed_board_title.setText("Autosave test")
    scr._saved_json = scr._doc_json()
    pm = _png(tmp / "a.png")
    scr._view.add_image(pm, "a.png", source_path=str(tmp / "a.png"))
    assert scr._board_dirty()
    scr._board_tick(force_dirty=True)       # first tick: notes the content
    scr._board_tick(force_dirty=True)       # unchanged for one tick -> autosave
    assert scr._board["version"] == 2 and not scr._board_dirty()
    assert cb.get_board(bid)["content"]["items"][0]["src"]["kind"] == "file"
