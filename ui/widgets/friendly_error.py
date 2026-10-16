# ui/widgets/friendly_error.py
"""Error messages people can act on (Nutzerwunsch 2026-10-16).

Instead of "Failed to save: (1452, 'Cannot add or update a child row: a
foreign key constraint fails …')" every error box says
  1. what did not work        - the caller's sentence, e.g. "The yarn could not be saved."
  2. what happened, in plain words, and
  3. what to do next          - both from explain(), by error type
The technical text is only under "Show Details" (to send to the admin) and
in the log. Errors of our own modules (db.*, ui.*) already carry a sentence
for people (e.g. RecycleBinError) - that sentence is shown as it is.

Use:  show_error(self, "Save Yarn", "The yarn could not be saved.", e)
All texts English (project rule).
"""
from __future__ import annotations

import logging
import traceback
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_ADMIN = "If it keeps happening, send the details (Show Details) to the TrippleT admin."

# (substrings in the error text, lower case) -> (what happened, what to do)
_RULES = [
    # "busy" first: "lock wait timeout" must not be taken for "database not reachable" (timeout)
    (("deadlock", "lock wait timeout", "1205 (", "1213 ("),
     ("The database was busy with another change at the same moment.", "Wait a few seconds and try again.")),
    (("can't connect", "cannot connect", "lost connection", "server has gone away", "connection refused",
      "timed out", "timeout", "2003 (", "2013 (", "2055 (", "network is unreachable", "no route to host",
      "connection not available", "pool exhausted"),
     ("TrippleT could not reach the database.",
      "Check that you are connected to the company network (or VPN), wait a moment and try again. " + _ADMIN)),
    (("permission denied", "errno 13", "winerror 32", "being used by another process", "access is denied",
      "zugriff verweigert"),
     ("The file is open in another program, or you are not allowed to write there.",
      "Close the file (e.g. in Excel) or choose another folder, then try again.")),
    (("no such file", "errno 2", "winerror 2", "winerror 3", "cannot find the path", "not found"),
     ("A file or folder could not be found.",
      "Check that the file still exists and that the network drive is connected, then try again.")),
    (("duplicate entry", "1062 (", "unique constraint"),
     ("An entry with the same values already exists.",
      "Look for the existing entry and use or change that one instead.")),
    (("foreign key constraint", "1451 (", "1452 ("),
     ("This entry is still used somewhere else - or it refers to something that was deleted.",
      "Check where it is used (e.g. trials, yarns, jets) and change or remove that first.")),
    (("data too long", "1406 ("),
     ("A text is too long for this field.", "Shorten the text and try again.")),
    (("incorrect", "1366 (", "1292 (", "out of range", "1264 (", "truncated"),
     ("A value has the wrong format - e.g. text in a number field or an impossible date.",
      "Check the numbers and dates you entered (decimal point, no letters) and try again.")),
    (("disk full", "no space left", "errno 28"),
     ("There is not enough free space on the drive.", "Free up space or save to another drive.")),
]


def _rule(needle: str) -> Tuple[str, str]:
    return next(answer for needles, answer in _RULES if needle in needles)


def _is_ours(exc: BaseException) -> bool:
    mod = type(exc).__module__ or ""
    return mod.startswith(("db.", "ui.")) and bool(str(exc).strip())


def explain(exc: Optional[BaseException]) -> Tuple[str, str]:
    """(what happened, what to do) in plain English."""
    if exc is None:
        return "", _ADMIN
    if _is_ours(exc):
        return str(exc).strip(), ""
    text = f"{type(exc).__name__} {exc}".lower()
    if isinstance(exc, PermissionError):
        return _rule("permission denied")
    if isinstance(exc, FileNotFoundError):
        return _rule("no such file")
    for needles, answer in _RULES:
        if any(n in text for n in needles):
            return answer
    if isinstance(exc, (ValueError, TypeError)):
        return ("A value could not be read.", "Check the values you entered and try again. " + _ADMIN)
    return ("Something unexpected went wrong.", "Try again. " + _ADMIN)


def technical_details(exc: Optional[BaseException], extra: str = "") -> str:
    parts = []
    if extra:
        parts.append(extra.strip())
    if exc is not None:
        parts.append(f"{type(exc).__name__}: {exc}")
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip()
        if tb and exc.__traceback__ is not None:
            parts.append(tb)
    return "\n\n".join(parts)


def message_text(action: str, exc: Optional[BaseException]) -> str:
    what, todo = explain(exc)
    return "\n\n".join(p for p in (action.strip(), what, todo) if p)


def show_error(parent, title: str, action: str, exc: Optional[BaseException] = None,
               details: str = "", warning: bool = False) -> None:
    """Error box: action sentence + plain explanation + what to do; the
    technical text under "Show Details"."""
    from PySide6.QtWidgets import QMessageBox
    logger.error("%s: %s", title, action, exc_info=exc if isinstance(exc, BaseException) else None)
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Warning if warning else QMessageBox.Critical)
    box.setWindowTitle(title)
    import html
    from PySide6.QtCore import Qt
    what, todo = explain(exc)
    box.setTextFormat(Qt.RichText)  # the sentence "what did not work" in bold
    box.setText("<br><br>".join(p for p in (f"<b>{html.escape(action.strip())}</b>", html.escape(what),
                                             html.escape(todo)) if p and p != "<b></b>"))
    det = technical_details(exc, details)
    if det:
        box.setDetailedText(det)
    box.setStandardButtons(QMessageBox.Ok)
    _exec_box(box)


def _exec_box(box) -> None:
    """Shows the box modally - replaced by a recorder in the tests
    (tests/conftest.py), so no test can hang on an error box."""
    box.exec()
