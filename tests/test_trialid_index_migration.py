"""tools/trialid_index_migration.py - only the parts that need no database (guard, names)."""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("trialid_index_migration", ROOT / "tools" / "trialid_index_migration.py")
mig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mig)


def test_guard_refuses_wrong_or_unknown_target(monkeypatch):
    monkeypatch.setenv("TRIPPLET_MODE", "dev_local")
    for target in ("prod", "dev", "nonsense"):
        with pytest.raises(SystemExit):
            mig._guard(target)


def test_index_names_and_tables():
    assert mig.index_name("tblLaborItematLab") == "idx_tbllaboritematlab_trialid"
    assert len(set(mig.TABLES)) == len(mig.TABLES)
    assert all(t == t.lower() and t.startswith("tbl") for t in mig.TABLES)
    assert "tbllaboritematlab" in mig.TABLES and "tbltrial" not in mig.TABLES
