"""db/series_attachments: listing is shared with the web app; downloads only from the attachment folders."""
import os

from db import series_attachments as sa


def _rows(path):
    return [{"ID": 7, "RelativePath": os.path.dirname(path), "StoredFilename": os.path.basename(path),
             "OriginalFilename": "x", "FullPath": path, "CreatedBy": 1}]


def test_download_only_inside_roots(tmp_path, monkeypatch):
    root = tmp_path / "imgs"
    (root / "5").mkdir(parents=True)
    good = root / "5" / "a.jpg"
    good.write_bytes(b"x")
    outside = tmp_path / "secret.txt"
    outside.write_text("no")
    monkeypatch.setitem(sa.DOWNLOAD_ROOTS, "image", (str(root),))
    monkeypatch.setattr(sa, "list_images", lambda sid: _rows(str(good)))
    assert sa.file_for_download("image", 5, 7) == os.path.normcase(os.path.realpath(str(good)))
    assert sa.file_for_download("image", 5, 8) is None
    monkeypatch.setattr(sa, "list_images", lambda sid: _rows(str(root / ".." / "secret.txt")))
    assert sa.file_for_download("image", 5, 7) is None
    monkeypatch.setattr(sa, "list_images", lambda sid: _rows(str(outside)))
    assert sa.file_for_download("image", 5, 7) is None
    assert sa.file_for_download("exe", 5, 7) is None


def test_roots_are_plain_paths():
    for roots in sa.DOWNLOAD_ROOTS.values():
        for r in roots:
            assert "\t" not in r and r[1] == ":"
