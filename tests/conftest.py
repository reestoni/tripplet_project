import sys
import os

# TrippleT_project/ als Root registrieren (ui/, db/ liegen direkt hier)
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pytest


@pytest.fixture(autouse=True)
def _no_modal_error_boxes(monkeypatch):
    """Error boxes (ui/widgets/friendly_error.show_error) are recorded, not
    shown - a modal box would block the test run forever."""
    shown = []
    try:
        import ui.widgets.friendly_error as fe
        monkeypatch.setattr(fe, "_exec_box", lambda box: shown.append((box.windowTitle(), box.text())))
    except Exception:
        pass
    return shown
