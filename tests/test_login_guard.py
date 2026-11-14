"""db/login_guard.py - lock after too many wrong passwords (shared by desktop + web login). Writes test rows to
tblUsageLog on dev_local under a user name that does not exist and removes them again."""
import os

os.environ.setdefault("TRIPPLET_MODE", "dev_local")

import pytest  # noqa: E402

from db import login_guard as lg  # noqa: E402
from db import user_account as ua  # noqa: E402
from db.connection import execute  # noqa: E402

NAME = "zz_guard_test_desk"


@pytest.fixture
def clean():
    execute("DELETE FROM tblUsageLog WHERE Username = ? AND EventType = 'security'", [NAME])
    yield
    execute("DELETE FROM tblUsageLog WHERE Username = ? AND EventType = 'security'", [NAME])


def test_lock_after_max_fails_and_success_resets(clean):
    assert lg.lock_status(NAME) == (False, 0)
    for i in range(lg.MAX_FAILS - 1):
        assert lg.record_failure(NAME.upper(), "test") == lg.MAX_FAILS - 1 - i   # case-insensitive
        assert not lg.lock_status(NAME)[0]
    assert lg.record_failure(NAME, "test") == 0
    locked, minutes = lg.lock_status(NAME)
    assert locked and 1 <= minutes <= lg.WINDOW_MINUTES
    lg.record_success(NAME, "test")
    assert lg.lock_status(NAME) == (False, 0)


def test_old_failures_expire(clean):
    for _ in range(lg.MAX_FAILS):
        execute("INSERT INTO tblUsageLog (Username, EventType, EventName, EventTime) "
                "VALUES (?, 'security', 'login_failed', NOW() - INTERVAL 20 MINUTE)", [NAME])
    assert lg.lock_status(NAME) == (False, 0)


def test_change_password_respects_lock(clean, monkeypatch):
    import db.connection as c
    monkeypatch.setattr(c, "user_exists", lambda u: True)
    monkeypatch.setattr(c, "verify_user_password", lambda u, p: False)
    for _ in range(lg.MAX_FAILS):
        assert ua.check_password_change(NAME, "wrong", "a", "a") == ua.PW_WRONG_OLD
    assert ua.check_password_change(NAME, "wrong", "a", "a") == ua.PW_LOCKED


def test_blank_name_never_locked():
    assert lg.lock_status("") == (False, 0) and lg.record_failure("  ") is None
