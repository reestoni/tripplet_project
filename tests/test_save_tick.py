import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLineEdit, QVBoxLayout, QWidget

from ui.widgets import save_tick


def _app():
    return QApplication.instance() or QApplication([])


def test_tick_does_not_block_input_and_hides_after_animation():
    _app()
    host = QWidget()
    lay = QVBoxLayout(host)
    edit = QLineEdit()
    lay.addWidget(edit)
    host.resize(600, 400)
    host.show()
    edit.setFocus()

    save_tick.show_save_tick(host)
    tick = host._save_tick_overlay
    assert tick.isVisible()
    assert tick.geometry() == host.rect()
    assert tick.testAttribute(Qt.WA_TransparentForMouseEvents)
    assert tick.focusPolicy() == Qt.NoFocus
    # The widget under the centre is still reachable for clicks
    assert host.childAt(host.rect().center()) is not tick

    # Replaying reuses the same overlay (rapid Ctrl+S)
    save_tick.show_save_tick(host)
    assert host._save_tick_overlay is tick

    # Rendering at several points of the animation must not fail
    for t in (0.0, 0.1, 0.5, 0.99):
        tick._t = t
        tick.grab()

    tick._anim.setCurrentTime(save_tick.DURATION_MS)
    assert not tick.isVisible()
    host.close()


def test_never_raises():
    save_tick.show_save_tick(None)
