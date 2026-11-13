"""db/master_tables.py - Order Type, Product Groups, Material, Top Plates without Qt (shared with the web).
The roundtrip writes a row per table and deletes it again."""
import subprocess
import sys
from pathlib import Path

import pytest

from db import master_tables as mt

ROOT = Path(__file__).resolve().parents[1]


def test_qt_free():
    code = ("import sys; import db.master_tables; "
            "sys.exit(1 if any(m.startswith('PySide6') for m in sys.modules) else 0)")
    assert subprocess.run([sys.executable, "-c", code], cwd=str(ROOT)).returncode == 0


def test_yarn_label():
    assert mt.yarn_label({"id": 1, "name": "PES", "garntyp": "POY", "titer": 167.0, "filaments": 48, "colour": "white"}) \
        == "PES - POY, 167 dtex, 48f, white"
    assert mt.yarn_label({"id": 7, "titer": None, "filaments": 0}) == "Yarn 7"


@pytest.mark.parametrize("key", list(mt.KINDS))
def test_roundtrip(key):
    kind = mt.KINDS[key]
    try:
        before = len(mt.load_rows(kind))
    except Exception as e:  # pragma: no cover
        pytest.skip(f"no database: {e}")
    new_id = mt.create(kind)
    try:
        rows = mt.load_rows(kind)
        assert len(rows) == before + 1
        row = next(r for r in rows if r["ID"] == new_id)
        name_col = next(c for c in row if mt._canon(c) in kind.name_cols)
        if key == "top_plates":
            assert row["Name"] == "New Top Plate" and row["GlobalID"]
        else:
            assert row[name_col] == ""
        # computed columns are dropped on save
        upd = {**row, name_col: "zz test master"}
        assert mt.save_changes(kind, [upd]) == 1
        assert next(r for r in mt.load_rows(kind) if r["ID"] == new_id)[name_col] == "zz test master"
        if key == "top_plates":
            assert not mt.name_available(kind, "zz test master")
            assert mt.name_available(kind, "zz test master", except_id=new_id)
    finally:
        mt.delete(kind, [new_id])
    assert len(mt.load_rows(kind)) == before


def test_material_usage():
    rows = [r for r in mt.load_rows(mt.KINDS["material"]) if r.get("UsedInYarn")]
    if not rows:
        pytest.skip("no material in use")
    use = mt.material_usage(rows[0]["ID"])
    assert use and all(u["label"] for u in use)


def test_top_plate_copy_and_files(tmp_path, monkeypatch):
    kind = mt.KINDS["top_plates"]
    monkeypatch.setattr(mt, "files_root", lambda: str(tmp_path))
    new_id = mt.create(kind, {"ID": 999999, "Name": "zz copy", "GlobalID": "x", "has_files": 1})
    try:
        row = next(r for r in mt.load_rows(kind) if r["ID"] == new_id)
        assert row["Name"] == "zz copy" and row["GlobalID"] != "x"
        mt.add_file(new_id, "a.pdf", b"%PDF-1.4", None)
        files = mt.list_files(new_id)
        assert len(files) == 1 and files[0]["FileType"] == "pdf"
        path = mt.file_path(files[0]["ID"])
        assert path and Path(path).read_bytes() == b"%PDF-1.4"
        assert next(r for r in mt.load_rows(kind) if r["ID"] == new_id)["has_files"] == 1
        mt.remove_file(files[0]["ID"])
        assert mt.list_files(new_id) == []
    finally:
        mt.delete(kind, [new_id])
