"""My Requests: due date + "to review" (db/experiment_requests.py, both apps, 2026-11-18)."""
import datetime

from db import experiment_requests as er

TODAY = datetime.date(2026, 11, 18)


def test_due_groups():
    assert er.due_info("2026-11-15", er.STATUS_REQUEST, TODAY) == {"group": "overdue", "days": -3}
    assert er.due_info(datetime.date(2026, 11, 18), er.STATUS_APPROVED, TODAY) == {"group": "today", "days": 0}
    assert er.due_info("25.11.2026", er.STATUS_REQUEST, TODAY) == {"group": "week", "days": 7}
    assert er.due_info(datetime.datetime(2026, 12, 1, 8, 0), er.STATUS_REQUEST, TODAY) == {"group": "later", "days": 13}
    assert er.due_info(None, er.STATUS_REQUEST, TODAY) == {"group": "none", "days": None}
    assert er.due_info("kein Datum", er.STATUS_REQUEST, TODAY) == {"group": "none", "days": None}


def test_closed_requests_are_never_due():
    # denied or already an experiment: no "overdue"
    assert er.due_info("2026-01-01", er.STATUS_DENIED, TODAY)["group"] == "none"
    assert er.due_info("2026-01-01", er.STATUS_EXPERIMENT, TODAY)["group"] == "none"


def test_due_text_and_sort():
    assert er.due_text({"group": "overdue", "days": -1}) == "1 day overdue"
    assert er.due_text({"group": "overdue", "days": -4}) == "4 days overdue"
    assert er.due_text({"group": "today", "days": 0}) == "today"
    assert er.due_text({"group": "week", "days": 1}) == "tomorrow"
    assert er.due_text({"group": "later", "days": 20}) == "in 20 days"
    assert er.due_text({"group": "none", "days": None}) == ""
    infos = [{"group": "later", "days": 20}, {"group": "none", "days": None}, {"group": "overdue", "days": -1},
             {"group": "overdue", "days": -9}, {"group": "today", "days": 0}]
    ordered = sorted(infos, key=er.due_sort_key)
    assert [i["days"] for i in ordered] == [-9, -1, 0, 20, None]


def test_needs_review_only_for_superusers():
    assert er.needs_review(True, False, True)
    assert er.needs_review(True, True, False)
    assert not er.needs_review(True, False, False)
    assert not er.needs_review(False, True, True)
