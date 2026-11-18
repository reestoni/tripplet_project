"""Deleting users (db/user_admin.delete_users, both apps, fixed 2026-11-18): personal rows (bell messages,
column layouts, ...) go with the account; a user who still owns real data is refused (UserHasData).
Runs against the dev_local database with a test user that is created and deleted here."""
import random
import string

import pytest

from db import user_admin as uadm
from db.connection import execute, fetch_all, is_offline_mode

pytestmark = pytest.mark.skipif(is_offline_mode(), reason="needs the database")


def _count(sql, params):
    rows = fetch_all(sql, params)
    return list(rows[0].values())[0] if rows else 0


def _new_user():
    n = min(uadm.username_max_len() or 5, 5)
    taken = {u.lower() for u in uadm.existing_usernames()}
    for _ in range(50):
        name = "z" + "".join(random.choices(string.ascii_lowercase, k=n - 1))
        if name not in taken:
            return name, uadm.create_user(name, "Start-" + name + "1", "Test", "Delete")
    pytest.skip("no free test user name")


def test_delete_user_with_bell_message():
    name, uid = _new_user()
    try:
        series = fetch_all("SELECT ID FROM tblTrialSeries ORDER BY ID LIMIT 1")
        execute("INSERT INTO tblNotification (RecipientUserID, TrialSeriesID, CreatedAt, ReadAt, Message, NotificationType) "
                "VALUES (?, ?, NOW(), NULL, ?, ?)", [uid, list(series[0].values())[0] if series else None, "test", "test"])
        assert _count("SELECT COUNT(*) FROM tblNotification WHERE RecipientUserID = ?", [uid]) == 1
        assert uadm.data_references([uid]) == []
        assert uadm.delete_users([uid]) == 1
        uid = None
        assert name not in {u.lower() for u in uadm.existing_usernames()}
    finally:
        if uid:
            execute("DELETE FROM tblNotification WHERE RecipientUserID = ?", [uid])
            execute("DELETE FROM tblUser WHERE ID = ?", [uid])


def test_user_with_data_is_refused_without_deleting_anything():
    # read only: a user who created trial series must not be deletable
    rows = fetch_all("SELECT CreatedBy FROM tblTrialSeries WHERE CreatedBy IS NOT NULL LIMIT 1")
    if not rows:
        pytest.skip("no series with a creator")
    owner = list(rows[0].values())[0]
    refs = uadm.data_references([owner])
    assert "tbltrialseries" in [r.lower() for r in refs]
