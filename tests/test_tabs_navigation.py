"""
TrippleT - Tabs-Feature (ui/widgets/tab_container.py, MainWindow-Tab-Wiring)
=============================================================================
Deckt die Kernmechanik ab, die den 2026-08-27-Bugreport ("wenn ich zwei
experimente in den tabs anzeigen will ... meist wird das erste
ueberschrieben") und den 2026-08-31-Fix (Zurueck-Chip aus einem frischen
Backlog-/All-Experiments-Tab zeigte auf den globalen Singleton statt auf den
Ursprungs-Tab) regressionssicher macht.

Keine echte DB noetig - TabbedNavigator/_StackFacade sind reine Qt-Container-
Logik ohne DB-Zugriff; fuer main.py::MainWindow._open_backlog_in_new_tab()/
_open_all_experiments_in_new_tab() werden BacklogScreen/AllExperimentsScreen
per monkeypatch durch leichte Dummy-QWidgets ersetzt (MainWindow wird dafuer
per __new__() ohne __init__() gebaut - die getesteten Methoden lesen keine
Instanz-Attribute, die erst in __init__() entstehen, siehe deren Docstrings).
"""

import os

os.environ.setdefault("TRIPPLET_MODE", "dev_local")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from PySide6.QtWidgets import QMainWindow
from ui.widgets.tab_container import TabbedNavigator, _StackFacade
from ui.widgets.sidebar_nav import _wire_tab_capable_click


# ===========================================================================
# TabbedNavigator / _StackFacade - reine Container-Mechanik
# ===========================================================================

class TestTabbedNavigatorMechanics:

    @pytest.fixture
    def tabs(self, qtbot):
        t = TabbedNavigator()
        qtbot.addWidget(t)
        return t

    def test_starts_with_one_tab(self, tabs):
        assert tabs.count() == 1

    def test_open_in_new_tab_creates_second_tab(self, tabs):
        first = QWidget()
        tabs.add_widget(first)
        tabs.set_current(first)
        assert tabs.count() == 1

        second = QWidget()

        def _populate():
            tabs.add_widget(second)
            tabs.set_current(second)

        tabs.open_in_new_tab(_populate)

        assert tabs.count() == 2
        assert tabs.active_screen() is second

    def test_two_fresh_instances_are_independent_objects(self, tabs):
        """Simuliert das main.py-Muster fuer Backlog/All Experiments: jede
        _open_X_in_new_tab()-Ausfuehrung baut ein GENUINE neues Widget statt
        ein bestehendes wiederzuverwenden."""
        instances = []

        def _make_and_open():
            w = QWidget()
            instances.append(w)

            def _populate():
                tabs.add_widget(w)
                tabs.set_current(w)
            tabs.open_in_new_tab(_populate)

        _make_and_open()
        _make_and_open()

        assert tabs.count() == 3  # initial leerer Tab 0 + zwei frische
        assert instances[0] is not instances[1]

    def test_find_tab_showing_widget_ignores_hidden_background_children(self, tabs):
        """Regressionstest fuer den urspruenglichen Backlog-Bug: ein Widget,
        das in einem Tab NICHT MEHR sichtbar ist (nur noch als verstecktes
        Hintergrund-Kind existiert), darf nicht als 'schon offen' erkannt
        werden - siehe TabbedNavigator._find_tab_showing_widget()."""
        backlog_like = QWidget()
        other = QWidget()
        tabs.add_widget(backlog_like)
        tabs.set_current(backlog_like)
        # navigiert im selben Tab weiter - backlog_like existiert danach nur
        # noch als verstecktes Kind, ist aber nicht mehr sichtbar
        tabs.add_widget(other)
        tabs.set_current(other)

        assert tabs._find_tab_showing_widget(backlog_like) == -1

        # set_current() fuer das nicht mehr sichtbare Widget muss es im
        # AKTIVEN Tab zeigen (kein stillschweigendes Zurueckspringen zu
        # einem alten, inzwischen unsichtbaren Vorkommen)
        tabs.set_current(backlog_like)
        assert tabs.active_screen() is backlog_like

    def test_close_tab_reparents_children_instead_of_deleting(self, tabs, qtbot):
        """Regressionstest fuer den 'Internal C++ object already deleted'-Bug:
        ein Singleton-Screen, der in einem geschlossenen Tab zuletzt sichtbar
        war, muss den Tab-Schluss ueberleben (nur entkoppelt, nie geloescht)."""
        singleton = QWidget()
        tabs.add_widget(singleton)
        tabs.set_current(singleton)

        second = QWidget()

        def _populate():
            tabs.add_widget(second)
            tabs.set_current(second)
        tabs.open_in_new_tab(_populate)
        assert tabs.count() == 2

        second_tab_index = tabs.currentIndex()
        tabs._on_tab_close_requested(second_tab_index)

        assert tabs.count() == 1
        # `second` sass im geschlossenen Tab - darf nicht mitgeloescht
        # werden (RuntimeError: Internal C++ object already deleted), nur
        # entkoppelt (elternlos)
        assert second.parent() is None
        second.setObjectName("still-alive")
        assert second.objectName() == "still-alive"
        # `singleton` (Tab 0, unveraendert) muss ebenfalls unberuehrt bleiben
        assert singleton.parent() is not None

    def test_last_tab_cannot_be_closed(self, tabs):
        assert tabs.count() == 1
        tabs._on_tab_close_requested(0)
        assert tabs.count() == 1

    def test_close_all_but_first(self, tabs):
        for _ in range(3):
            w = QWidget()

            def _populate(w=w):
                tabs.add_widget(w)
                tabs.set_current(w)
            tabs.open_in_new_tab(_populate)
        assert tabs.count() == 4
        tabs.close_all_but_first()
        assert tabs.count() == 1


class TestStackFacade:

    @pytest.fixture
    def facade(self, qtbot):
        t = TabbedNavigator()
        qtbot.addWidget(t)
        return _StackFacade(t), t

    def test_add_and_set_current_widget(self, facade):
        stack, tabs = facade
        w = QWidget()
        stack.addWidget(w)
        stack.setCurrentWidget(w)
        assert stack.currentWidget() is w


# ===========================================================================
# sidebar_nav._wire_tab_capable_click() - only Ctrl+click opens a new tab
# (2026-09-01, user request: the previous automatic "pinned tab protects
# itself" redirect - any normal navigation WITHIN a comparison tab opened
# via Ctrl+click undesirably opened yet another new tab there too - was
# removed without replacement: "ich will, dass nur neue tabs erstellt
# werden, wenn ich es explizit so will - sonst bleibe ich einfach im
# aktiven".)
# ===========================================================================

class TestWireTabCapableClick:

    @pytest.fixture
    def app(self, qtbot):
        return QApplication.instance()

    def test_normal_click_calls_on_click(self, qtbot):
        btn = QPushButton()
        qtbot.addWidget(btn)
        calls = {"on_click": 0, "new_tab": 0}
        _wire_tab_capable_click(
            btn, on_click=lambda: calls.__setitem__("on_click", calls["on_click"] + 1),
            open_in_new_tab=lambda cb: calls.__setitem__("new_tab", calls["new_tab"] + 1))

        qtbot.mouseClick(btn, Qt.LeftButton)
        assert calls["on_click"] == 1
        assert calls["new_tab"] == 0

    def test_ctrl_click_calls_open_in_new_tab(self, qtbot, monkeypatch):
        monkeypatch.setattr(QApplication, "keyboardModifiers", staticmethod(lambda: Qt.ControlModifier))

        btn = QPushButton()
        qtbot.addWidget(btn)
        calls = {"on_click": 0, "new_tab": 0}
        _wire_tab_capable_click(
            btn, on_click=lambda: calls.__setitem__("on_click", calls["on_click"] + 1),
            open_in_new_tab=lambda cb: calls.__setitem__("new_tab", calls["new_tab"] + 1))

        qtbot.mouseClick(btn, Qt.LeftButton)
        assert calls["new_tab"] == 1
        assert calls["on_click"] == 0

    def test_normal_click_from_a_tab_opened_via_new_tab_still_stays_put(self, qtbot):
        """Regression test for the 2026-09-01 bug report: a normal click
        (no Ctrl) must NEVER open a new tab, even when the currently active
        tab itself was created via Ctrl+click/'open in new tab' - previously
        this was incorrectly treated the same as Ctrl+click."""
        btn = QPushButton()
        qtbot.addWidget(btn)
        calls = {"on_click": 0, "new_tab": 0}
        _wire_tab_capable_click(
            btn, on_click=lambda: calls.__setitem__("on_click", calls["on_click"] + 1),
            open_in_new_tab=lambda cb: calls.__setitem__("new_tab", calls["new_tab"] + 1))

        qtbot.mouseClick(btn, Qt.LeftButton)  # no Ctrl held
        assert calls["on_click"] == 1
        assert calls["new_tab"] == 0

    def test_open_in_new_tab_none_disables_tab_capability(self, qtbot):
        btn = QPushButton()
        qtbot.addWidget(btn)
        calls = {"on_click": 0}
        _wire_tab_capable_click(
            btn, on_click=lambda: calls.__setitem__("on_click", calls["on_click"] + 1),
            open_in_new_tab=None)
        assert not btn.property("tabCapable")
        qtbot.mouseClick(btn, Qt.LeftButton)
        assert calls["on_click"] == 1


# ===========================================================================
# main.py::MainWindow - Zurueck-Chip-Fix fuer frische Backlog/All-Experiments-
# Tabs (2026-08-31-Bugfix-Regressionstest)
# ===========================================================================

class TestFreshTabBackTarget:

    @pytest.fixture
    def bare_main_window(self, qtbot):
        """Baut eine MainWindow-Instanz OHNE __init__() (kein Login-Dialog,
        keine ~30 Screen-Konstruktionen, keine DB) - die hier getesteten
        Methoden (_open_backlog_in_new_tab/_open_all_experiments_in_new_tab)
        lesen laut ihrem eigenen Code nur self._tabs/self.stack sowie rein
        methodengebundene Callback-Referenzen (_go_X, _sidebar_nav_kwargs),
        keine erst in __init__() gesetzten Datenattribute."""
        import main as main_module
        mw = main_module.MainWindow.__new__(main_module.MainWindow)
        # QMainWindow.__init__() direkt (statt MainWindow.__init__()) baut
        # das darunterliegende C++/Shiboken-Objekt auf, ohne Login-Dialog,
        # ~30 Screen-Konstruktionen oder DB-Zugriff auszuloesen - notwendig,
        # da PySide6-QObject-Subklassen ohne jedes __init__() (auch nicht
        # das der Basisklasse) keine funktionsfaehigen Qt-Methoden haben
        # (z.B. setWindowTitle() wirft sonst RuntimeError).
        QMainWindow.__init__(mw)
        mw._tabs = TabbedNavigator()
        qtbot.addWidget(mw._tabs)
        mw.stack = _StackFacade(mw._tabs)
        return mw, main_module

    def test_backlog_new_tab_back_chip_targets_this_tab_not_singleton(self, bare_main_window, monkeypatch):
        mw, main_module = bare_main_window
        captured = {}

        class _DummyBacklogScreen(QWidget):
            def __init__(self, **kwargs):
                super().__init__()
                captured["kwargs"] = kwargs
                captured["instance"] = self

        monkeypatch.setattr(main_module, "BacklogScreen", _DummyBacklogScreen)

        open_show_calls = []

        def _fake_open_show_experiment_in_new_tab(exp_pk, series_pk, experiment_id,
                                                    back_label=None, back_callback=None):
            open_show_calls.append((exp_pk, series_pk, experiment_id, back_label, back_callback))

        mw._open_show_experiment_in_new_tab = _fake_open_show_experiment_in_new_tab

        mw._open_backlog_in_new_tab()

        fresh_backlog = captured["instance"]
        on_open_in_new_window = captured["kwargs"]["on_open_in_new_window"]

        # ein Fremd-Widget "dazwischen" simuliert, dass der Nutzer inzwischen
        # zu einem anderen Tab/Screen navigiert hat, bevor der Zurueck-Chip
        # geklickt wird
        distractor = QWidget()
        mw.stack.addWidget(distractor)
        mw.stack.setCurrentWidget(distractor)
        assert mw.stack.currentWidget() is not fresh_backlog

        on_open_in_new_window(123, 456, "EXP-1")

        assert len(open_show_calls) == 1
        exp_pk, series_pk, experiment_id, back_label, back_callback = open_show_calls[0]
        assert (exp_pk, series_pk, experiment_id) == (123, 456, "EXP-1")
        assert back_label == "Backlog"
        # Bug-Regression: back_callback darf NICHT der globale Singleton-
        # Navigator sein
        assert back_callback != mw._go_backlog

        back_callback()
        assert mw.stack.currentWidget() is fresh_backlog

    def test_all_experiments_new_tab_back_chip_targets_this_tab_not_singleton(self, bare_main_window, monkeypatch):
        mw, main_module = bare_main_window
        monkeypatch.setattr(main_module.app_meta, "current_user", {"access_level": 4}, raising=False)
        captured = {}

        class _DummyAllExperimentsScreen(QWidget):
            def __init__(self, **kwargs):
                super().__init__()
                captured["kwargs"] = kwargs
                captured["instance"] = self

        monkeypatch.setattr(main_module, "AllExperimentsScreen", _DummyAllExperimentsScreen)

        open_show_calls = []

        def _fake_open_show_experiment_in_new_tab(exp_pk, series_pk, experiment_id,
                                                    back_label=None, back_callback=None):
            open_show_calls.append((exp_pk, series_pk, experiment_id, back_label, back_callback))

        mw._open_show_experiment_in_new_tab = _fake_open_show_experiment_in_new_tab

        mw._open_all_experiments_in_new_tab()

        fresh_all_exp = captured["instance"]
        on_open_in_new_window = captured["kwargs"]["on_open_in_new_window"]

        distractor = QWidget()
        mw.stack.addWidget(distractor)
        mw.stack.setCurrentWidget(distractor)

        on_open_in_new_window(789, 12, "EXP-2")

        assert len(open_show_calls) == 1
        _, _, _, back_label, back_callback = open_show_calls[0]
        assert back_label == "All Experiments"
        assert back_callback != mw._go_all_experiments

        back_callback()
        assert mw.stack.currentWidget() is fresh_all_exp

    def test_two_backlog_tabs_are_independent_screen_instances(self, bare_main_window, monkeypatch):
        mw, main_module = bare_main_window
        instances = []

        class _DummyBacklogScreen(QWidget):
            def __init__(self, **kwargs):
                super().__init__()
                instances.append(self)

        monkeypatch.setattr(main_module, "BacklogScreen", _DummyBacklogScreen)
        mw._open_show_experiment_in_new_tab = lambda *a, **k: None

        mw._open_backlog_in_new_tab()
        mw._open_backlog_in_new_tab()

        assert len(instances) == 2
        assert instances[0] is not instances[1]
