"""db/backlog_moves.check_move - the Backlog status rules (shared with tripplet_web)."""
import itertools

from db import backlog_moves as bm
from db.series_permissions import can_move_series

ME, OTHER = 7, 9


def _check(old, new, level, owner):
    return bm.check_move(old, new, user_id=ME, access_level=level, owner_id=owner)


def test_not_logged_in():
    assert bm.check_move(1, 2, user_id=None, access_level=4, owner_id=None) == "not_logged_in"


def test_backlog_can_be_taken_by_every_write_user():
    assert _check(1, 2, 2, OTHER) is None
    assert _check(1, 3, 2, None) is None


def test_owner_only_outside_backlog():
    assert _check(2, 3, 2, OTHER) == "owner_only"
    assert _check(2, 3, 2, ME) is None
    assert _check(3, 2, 3, None) == "owner_only"


def test_archived_superuser_only_except_tbc_to_archived():
    assert _check(3, 5, 2, ME) == "archived_superuser"
    assert _check(5, 1, 3, ME) == "archived_superuser"
    assert _check(4, 5, 2, OTHER) is None             # every write user
    assert _check(4, 5, 1, OTHER) == "owner_only"     # read users not


def test_to_be_cleaned_superuser_only():
    assert _check(1, 4, 2, None) == "tbc_superuser"   # the old 1 -> 4 loophole stays closed
    assert _check(3, 4, 3, ME) == "tbc_superuser"
    assert _check(4, 2, 3, ME) == "tbc_back_superuser"


def test_superuser_may_everything():
    for old, new in itertools.product(range(1, 6), repeat=2):
        assert _check(old, new, 4, OTHER) is None


def test_messages_for_every_code():
    for old, new, lvl, owner in itertools.product(range(1, 6), range(1, 6), range(0, 5), (None, ME, OTHER)):
        code = _check(old, new, lvl, owner)
        assert code is None or code in bm.DENY_MESSAGES


def test_some_move_allowed_matches_series_permissions():
    """series_permissions.can_move_series = "at least one move is allowed" (write users)."""
    for old, lvl, owner in itertools.product(range(1, 6), range(2, 5), (None, ME, OTHER)):
        some = any(_check(old, new, lvl, owner) is None for new in range(1, 6) if new != old)
        assert some == can_move_series(lvl, old, owner, ME), (old, lvl, owner)
