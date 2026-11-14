"""db/file_roots.py: share folders with env overrides (used by desktop and web server)."""
import os

os.environ.setdefault("TRIPPLET_MODE", "dev_local")

from db import file_roots  # noqa: E402


def test_defaults_dev_local():
    for key, (dev, _prod) in file_roots.FOLDERS.items():
        os.environ.pop(file_roots.env_name(key), None)
        assert file_roots.folder(key) == dev


def test_env_override_and_known(monkeypatch):
    monkeypatch.setenv("TRIPPLET_DIR_JET_FILES", r"\\server\share\JetFiles")
    assert file_roots.folder("JET_FILES") == r"\\server\share\JetFiles"
    known = file_roots.known_folders("JET_FILES")
    assert known[0] == r"\\server\share\JetFiles" and r"H:\Technik\TrippleT\JetFiles" in known
    from db import jets_admin
    assert jets_admin.files_root() == r"\\server\share\JetFiles"
