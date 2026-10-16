"""Error messages people can act on (ui/widgets/friendly_error.py, 2026-10-16)."""
from ui.widgets import friendly_error as fe


class _DbError(Exception):
    pass


def test_explain_common_causes():
    assert "could not reach the database" in fe.explain(_DbError("2003 (HY000): Can't connect to MySQL server"))[0]
    assert "open in another program" in fe.explain(PermissionError(13, "Permission denied"))[0]
    assert "could not be found" in fe.explain(FileNotFoundError(2, "No such file"))[0]
    assert "already exists" in fe.explain(_DbError("1062 (23000): Duplicate entry 'x' for key"))[0]
    assert "still used" in fe.explain(_DbError("1451 (23000): Cannot delete ... foreign key constraint fails"))[0]
    assert "too long" in fe.explain(_DbError("1406 (22001): Data too long for column"))[0]
    assert "busy" in fe.explain(_DbError("1205 (HY000): Lock wait timeout exceeded"))[0]
    what, todo = fe.explain(_DbError("something odd"))
    assert what == "Something unexpected went wrong." and "Show Details" in todo
    # a trial ID 1452 in a text must not look like a foreign key error
    assert "still used" not in fe.explain(_DbError("trial 1452 not plausible"))[0]


def test_own_errors_are_shown_as_they_are():
    from db.recycle_bin import RecycleBinError
    assert fe.explain(RecycleBinError("Some of the rows exist again."))[0] == "Some of the rows exist again."


def test_show_error_box(_no_modal_error_boxes):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    try:
        raise _DbError("2013 (HY000): Lost connection to MySQL server during query")
    except _DbError as e:
        fe.show_error(None, "Save Yarn", "The yarn could not be saved.", e, details="YarnID: 5")
    title, text = _no_modal_error_boxes[-1]
    assert title == "Save Yarn" and "<b>The yarn could not be saved.</b>" in text and "VPN" in text
