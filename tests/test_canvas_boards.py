"""db/canvas_boards.py - boards in tblCanvasBoard (dev_local; every test board is deleted again)."""
import os

os.environ.setdefault("TRIPPLET_MODE", "dev_local")

import pytest  # noqa: E402

from db import canvas_boards as cb  # noqa: E402

pytestmark = pytest.mark.skipif(not cb.table_ready(), reason="tblCanvasBoard missing (tools/canvas_board_migration.py)")


@pytest.fixture
def user(monkeypatch, tmp_path):
    import app_meta
    from db.connection import fetch_all
    uid = fetch_all("SELECT ID FROM tblUser ORDER BY ID LIMIT 1")[0]["ID"]
    monkeypatch.setattr(app_meta, "current_user", {"id": uid, "username": "t", "access_level": 2}, raising=False)
    monkeypatch.setenv("TRIPPLET_DIR_CANVAS_FILES", str(tmp_path / "canvas"))
    created = []
    yield created
    app_meta.current_user["access_level"] = 4
    for b in created:
        cb.delete_board(b)


def _doc():
    return {"bg": "#101010", "items": [
        {"id": "a", "label": "img", "src": {"kind": "series_image", "series": 1, "id": 2}, "cx": 10, "cy": 20, "w": 300, "h": 200, "angle": 450},
        {"id": "b", "src": {"kind": "evil", "path": "C:/x"}},
        {"id": "c", "src": {"kind": "file", "file": "../../secret.txt"}}],
        "annos": [{"tool": "arrow", "color": "red", "size": 4, "points": [[0, 0], [5, "x"], [9, 9]]},
                  {"tool": "nope", "points": [[1, 1]]}]}


def test_normalise_drops_bad_parts():
    d = cb.normalise_content(_doc())
    assert d["format"] == cb.FORMAT and d["bg"] == "#101010"
    assert [i["id"] for i in d["items"]] == ["a"] and d["items"][0]["angle"] == 90.0
    assert len(d["annos"]) == 1 and d["annos"][0]["points"][1] == [5.0, 0.0]
    with pytest.raises(cb.BoardError):
        cb.normalise_content({"items": [{}] * (cb.MAX_ITEMS + 1)})


def test_create_save_conflict_files_delete(user):
    bid = cb.create_board("  Test   board ", None, _doc())
    user.append(bid)
    b = cb.get_board(bid)
    assert b["Title"] == "Test board" and b["Version"] == 1 and len(b["content"]["items"]) == 1
    name = cb.add_file(bid, "photo one.PNG", b"\x89PNG....")
    assert cb.file_path(bid, name) and cb.file_path(bid, "../x") is None
    doc = b["content"]
    doc["items"].append({"id": "f", "src": {"kind": "file", "file": name}, "cx": 0, "cy": 0, "w": 10, "h": 10})
    v2 = cb.save_board(bid, doc, 1, title="Renamed")
    assert v2 == 2 and cb.get_board(bid)["Title"] == "Renamed"
    with pytest.raises(cb.BoardConflict) as e:
        cb.save_board(bid, doc, 1)           # stale version
    assert e.value.current_version == 2
    # a file no longer referenced is removed on the next save
    doc["items"] = [i for i in doc["items"] if i["id"] != "f"]
    cb.save_board(bid, doc, 2)
    assert cb.file_path(bid, name) is None
    assert any(r["ID"] == bid for r in cb.list_boards())
    with pytest.raises(cb.BoardError):
        cb.add_file(bid, "x.exe", b"MZ")


def test_series_boards_and_rights(user):
    from db.connection import fetch_all
    sid = fetch_all("SELECT ID FROM tblTrialSeries ORDER BY ID DESC LIMIT 1")[0]["ID"]
    bid = cb.create_board("Series board", sid)
    user.append(bid)
    assert [r["ID"] for r in cb.list_boards(sid)][0] == bid and cb.board_counts([sid])[sid] >= 1
    import app_meta
    app_meta.current_user["access_level"] = 1
    assert not cb.can_edit()
    with pytest.raises(cb.BoardError):
        cb.save_board(bid, cb.empty_content(), 1)
    other = {"id": -1, "access_level": 2}
    assert not cb.can_delete(cb.get_board(bid), other)
