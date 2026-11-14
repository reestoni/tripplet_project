"""db/series_overview.backlog_fingerprint: changes whenever something the Backlog shows changes (both apps poll it)."""
import os

os.environ.setdefault("TRIPPLET_MODE", "dev_local")

from db import series_overview as so  # noqa: E402


def _fake(rows, counts=(3, 4)):
    def fetch_all(sql, params):
        if "COUNT(*)" in sql:
            return [{"C": counts[0] if "Image" in sql else counts[1]}]
        return [dict(r) for r in rows]
    return fetch_all


def test_fingerprint_follows_changes(monkeypatch):
    rows = [{"ID": 1, "BacklogStatusID": 1, "BacklogPrio": 2, "SeriesName": "A", "MachineID": 5, "BacklogOwner": 9, "N": 0}]
    monkeypatch.setattr(so, "retest_flags_map", lambda: {})
    monkeypatch.setattr(so, "fetch_all", _fake(rows))
    a = so.backlog_fingerprint()
    assert a and a == so.backlog_fingerprint()
    for field, value in (("BacklogStatusID", 2), ("BacklogPrio", 1), ("SeriesName", "B"), ("N", 1)):
        changed = [{**rows[0], field: value}]
        monkeypatch.setattr(so, "fetch_all", _fake(changed))
        assert so.backlog_fingerprint() != a, field
    monkeypatch.setattr(so, "fetch_all", _fake(rows, counts=(4, 4)))       # new picture
    assert so.backlog_fingerprint() != a
    monkeypatch.setattr(so, "fetch_all", _fake(rows))
    monkeypatch.setattr(so, "retest_flags_map", lambda: {1: [object()]})  # new retest flag
    assert so.backlog_fingerprint() != a


def test_fingerprint_real_db():
    assert len(so.backlog_fingerprint()) == 16
