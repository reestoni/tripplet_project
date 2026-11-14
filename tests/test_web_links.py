"""db/web_links.py: link format shared with the web app (frontend/src/links.ts)."""
from db import web_links as wl


def test_links_with_base():
    b = "https://tt.example.local/"
    assert wl.series_url(12, base=b) == "https://tt.example.local/series/12"
    assert wl.series_url(12, tab="titer", trial_id=345, base=b) == "https://tt.example.local/series/12?tab=titer&trial=345"
    assert wl.report_url(12, 7, base=b) == "https://tt.example.local/series/12/report?report=7"
    assert wl.board_url(3, base=b) == "https://tt.example.local/tools/canvas?board=3"


def test_base_from_env_and_mode(monkeypatch):
    monkeypatch.setenv("TRIPPLET_WEB_URL", "https://web.local/")
    assert wl.base_url() == "https://web.local"
    monkeypatch.delenv("TRIPPLET_WEB_URL")
    monkeypatch.setattr(wl, "_mode", lambda: "prod")
    assert wl.base_url() is None and wl.series_url(1) is None
    monkeypatch.setattr(wl, "_mode", lambda: "dev_local")
    assert wl.series_url(1) == "http://127.0.0.1:8000/series/1"
