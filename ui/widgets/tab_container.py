from __future__ import annotations
# ui/widgets/tab_container.py
"""Browser-artige Tabs für MainWindow's zentralen Inhaltsbereich (2026-08-27,
Nutzerwunsch: "wenn ich aus dem sidepanel etwas anklicke mit gehaltener ctrl
taste, wird eine neue registerkarte mit dem screen geöffnet").

Architektur-Kniff, der die App-weite Sidebar-Navigation (main.py, ~100
Aufrufstellen von `self.stack.addWidget(...)`/`self.stack.setCurrentWidget(...)`)
komplett UNVERÄNDERT lässt: JEDER Screen in dieser App ist ein langlebiges
Singleton (genau eine Instanz pro Screen-Klasse, wiederverwendet über die
gesamte Session - siehe CLAUDE.md). Ein Widget kann in Qt aber immer nur EIN
Elternteil haben - zwei Tabs können also nie *gleichzeitig* dieselbe
Bildschirm-Instanz zeigen. Statt jede Screen-Klasse "mehrfach instanzierbar"
zu machen (riesiger, riskanter Umbau über ~30 Screens), bekommt jeder Tab
stattdessen seinen EIGENEN QStackedWidget-Container (identisch zum früheren
einzelnen globalen `self.stack`) - "innerhalb" eines Tabs navigieren
(normaler Klick) funktioniert exakt wie bisher. `MainWindow.stack` wird zu
einer Property, die auf den STACK DES AKTIVEN TABS zeigt (siehe main.py) -
das macht die Umstellung für die ~100 bestehenden Aufrufstellen unsichtbar.

Ist ein Screen schon in einem ANDEREN Tab offen (z.B. weil er dort per
Ctrl+Klick geöffnet wurde, und man klickt ihn jetzt nochmal an, mit oder
ohne Ctrl), wird er NICHT dorthin verschoben (das würde den alten Tab in
einem kaputten Zustand zurücklassen) - stattdessen wird einfach zu diesem
bereits existierenden Tab gewechselt. Gleiches Verhalten wie viele andere
Single-Instance-pro-Dokument-Apps (ein bereits offenes Dokument wird beim
erneuten Öffnen fokussiert statt dupliziert).
"""

import re
from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QStackedWidget, QTabWidget, QWidget


def _pretty_tab_label(text: str) -> str:
    """Leitet ein kurzes Tab-Label aus einem bestehenden Fenstertitel
    ("TrippleT – Manage Jets") ab, statt Klassennamen zu parsen - die
    Titeltexte sind an jeder _go_X()-Aufrufstelle in main.py bereits von
    Hand sauber formuliert, das hier ist reine Wiederverwendung."""
    t = (text or "").strip()
    for prefix in ("TrippleT – ", "TrippleT - ", "TrippleT–", "TrippleT-"):
        if t.startswith(prefix):
            t = t[len(prefix):].strip()
            break
    return t or "Tab"


class TabbedNavigator(QTabWidget):
    """Zentrale Inhaltsfläche von MainWindow: eine Reihe schliessbarer,
    browser-artiger Tabs, jeder mit einem eigenen QStackedWidget-Inhalt.

    Öffentliche API, die main.py über die `stack`-Property nutzt (siehe
    _StackFacade unten) - Methodennamen bewusst identisch zu QStackedWidget,
    damit jede bestehende `self.stack.X(...)`-Aufrufstelle unverändert
    funktioniert: add_widget()/set_current()/remove_widget()/active_screen().
    """

    screenChanged = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)
        self._title_provider: Optional[Callable[[], str]] = None
        self._title_setter: Optional[Callable[[str], None]] = None
        # Pro-Widget gemerkter Titel (siehe notify_title_set()/
        # _record_current_title_for()) - ein blosser Tab-Header-Klick (kein
        # _go_X()-Aufruf, kein setWindowTitle()) darf den Titel eines Tabs
        # NICHT vom aktuellen (ggf. zu einem komplett anderen Tab
        # gehoerenden) globalen Fenstertitel ableiten, siehe
        # _on_current_changed().
        self._tab_titles: dict = {}
        # Wird von add_widget()/set_current() gesetzt und bewusst NICHT
        # danach zurückgesetzt (siehe dortige Docstrings) - hält fest,
        # welchem Widget der zuletzt (via MainWindow.setWindowTitle()
        # synchron gemeldete, siehe notify_title_set()) gesetzte Fenstertitel
        # gehört. Da in dieser Single-Thread-App zu jedem Zeitpunkt höchstens
        # EINE _go_X()-artige Navigation "in Arbeit" ist (keine Überlappung
        # möglich), bleibt dieser Wert für die gesamte Dauer einer solchen
        # Methode korrekt - unabhängig davon, ob sie setWindowTitle() vor
        # oder nach dem Stack-/Tab-Wechsel aufruft.
        self._pending_label_widget: Optional[QWidget] = None
        # Reentrancy-Guard fuer notify_title_set(), siehe dort.
        self._restoring_title = False
        self.tabCloseRequested.connect(self._on_tab_close_requested)
        self.currentChanged.connect(self._on_current_changed)
        self._add_tab(label="TrippleT")

    def set_title_provider(self, provider: Callable[[], str], setter: Optional[Callable[[str], None]] = None):
        """MainWindow ruft das mit `self.windowTitle`/`self.setWindowTitle`
        auf (siehe __init__) - Quelle und (optionaler) Rücksetz-Weg für
        Tab-Labels. `setter` erlaubt, beim reinen Tab-Wechsel (kein
        `_go_X()`-Aufruf) den OS-Fenstertitel wieder an das jetzt sichtbare
        Tab anzugleichen (siehe _on_current_changed())."""
        self._title_provider = provider
        self._title_setter = setter

    # ------------------------------------------------------------- Tabs
    def _add_tab(self, *, label: str = "New Tab") -> int:
        stack = QStackedWidget()
        idx = self.addTab(stack, label)
        stack.currentChanged.connect(lambda _i, s=stack: self._on_stack_current_changed(s))
        return idx

    def _on_stack_current_changed(self, stack: QStackedWidget):
        # Nur relevant, wenn genau DIESER Stack gerade der sichtbare (aktive)
        # Tab ist - Änderungen in einem Hintergrund-Tab (z.B. durch den
        # find/redirect-Mechanismus unten) sollen kein sichtbares Ereignis
        # auslösen (Fenstertitel/Badge/Usage-Log beziehen sich sonst auf
        # einen gerade gar nicht sichtbaren Screen).
        if self.widget(self.currentIndex()) is stack:
            self.screenChanged.emit()

    def current_stack(self) -> QStackedWidget:
        w = self.currentWidget()
        if w is None:
            idx = self._add_tab()
            self.setCurrentIndex(idx)
            w = self.currentWidget()
        return w

    def _find_tab_showing_widget(self, widget: QWidget) -> int:
        """Findet den Tab, in dem `widget` gerade SICHTBAR ist (nicht bloss
        irgendwo als verstecktes Hintergrund-Kind existiert) - siehe
        add_widget()/set_current() für die Begründung, wieso das der
        richtige Massstab für "schon offen" ist, nicht Existenz allein.

        Wichtiger Unterschied zu einer reinen indexOf()-Suche: JEDER
        Screen, der in einem Tab jemals sichtbar war, bleibt danach als
        verstecktes Kind von dessen QStackedWidget bestehen (normales
        Stack-Verhalten - nur der jeweils aktuelle wird angezeigt, der Rest
        sammelt sich im Hintergrund an, siehe current_stack()). Eine
        indexOf()-Suche hätte solche "Karteileichen" fälschlich als
        "bereits offen" erkannt - konkret beobachtet mit Backlog (Landing-
        Screen direkt nach dem Login, damit ab dann dauerhaft ein
        unsichtbares Kind von Tab 0): Ctrl+Klick auf "Backlog" aus einem
        ANDEREN, später geöffneten Screen heraus sprang dadurch immer
        wieder nur zu Tab 0 zurück, statt einen neuen Tab zu befüllen -
        obwohl Backlog dort längst gar nicht mehr sichtbar war."""
        for i in range(self.count()):
            stack = self.widget(i)
            if isinstance(stack, QStackedWidget) and stack.currentWidget() is widget:
                return i
        return -1

    # ------------------------------------------------------- Stack-Fassade
    def add_widget(self, widget: QWidget) -> int:
        """Entspricht QStackedWidget.addWidget() - fügt `widget` dem
        AKTIVEN Tab hinzu, ausser es ist GERADE SICHTBAR in einem ANDEREN
        Tab - dann wird nur dorthin gewechselt statt es zu verschieben
        (siehe Moduldocstring/_find_tab_showing_widget())."""
        existing = self._find_tab_showing_widget(widget)
        if existing != -1:
            return self.widget(existing).indexOf(widget)
        self._pending_label_widget = widget
        return self.current_stack().addWidget(widget)

    def set_current(self, widget: QWidget):
        """Entspricht QStackedWidget.setCurrentWidget() - wechselt zu dem
        Tab, in dem `widget` GERADE SICHTBAR ist (siehe
        _find_tab_showing_widget()); ist es nirgends gerade sichtbar (auch
        wenn es als Hintergrund-Kind woanders existiert), wird es im
        aktiven Tab gezeigt - das reparentet es bei Bedarf automatisch weg
        von seinem bisherigen (dort ohnehin unsichtbaren) Tab, Qt räumt die
        Buchführung des alten QStackedWidget dabei selbst auf.

        `self._pending_label_widget` wird gesetzt (und bewusst NICHT danach
        zurückgesetzt, siehe __init__()) - dadurch weiss ein SPÄTER
        innerhalb derselben `_go_X()`-Methode aufgerufenes
        `MainWindow.setWindowTitle()` (auch wenn es erst nach dieser
        Methode zurückkehrt, z.B. aus `ShowExperimentScreen.load_record()`)
        über `notify_title_set()` synchron, welchem Widget der Titel
        gehört - kein Raten anhand eines später (evtl. schon von einer
        ANDEREN, zwischenzeitlich gestarteten Navigation überschriebenen)
        globalen Fenstertitels mehr nötig. Am Ende zusätzlich
        `_record_current_title_for()`, falls der Titel bereits VOR diesem
        Aufruf gesetzt wurde (z.B. `_go_backlog()`: setWindowTitle() zuerst,
        dann setCurrentWidget())."""
        existing = self._find_tab_showing_widget(widget)
        self._pending_label_widget = widget
        if existing == -1:
            self.current_stack().addWidget(widget)
            existing = self.currentIndex()
        if existing != self.currentIndex():
            self.setCurrentIndex(existing)
        self.widget(existing).setCurrentWidget(widget)
        self._record_current_title_for(widget)

    def remove_widget(self, widget: QWidget):
        """Entspricht QStackedWidget.removeWidget() - sucht den Screen in
        JEDEM Tab (nicht nur dem aktiven), da z.B. main.py's
        _dispose_old_create_screen() eine bestimmte Instanz entfernt,
        unabhängig davon, in welchem Tab sie gerade sichtbar ist."""
        for i in range(self.count()):
            stack = self.widget(i)
            if isinstance(stack, QStackedWidget) and stack.indexOf(widget) != -1:
                stack.removeWidget(widget)
                return

    def active_screen(self) -> Optional[QWidget]:
        """Entspricht QStackedWidget.currentWidget() - der Screen, der im
        AKTIVEN Tab gerade sichtbar ist."""
        return self.current_stack().currentWidget()

    # -------------------------------------------------------- Neuer Tab
    def open_in_new_tab(self, nav_callable: Callable[[], None]):
        """Führt `nav_callable` (eine der _go_X()-Methoden von MainWindow)
        gegen einen frisch angelegten, sofort aktivierten Tab aus, statt
        gegen den gerade aktiven - Ctrl+Klick-Verhalten (siehe
        ui/widgets/sidebar_nav.py). Stellt sich der Zielscreen dabei als
        bereits in einem ANDEREN Tab offen heraus (Singleton-Wiederverwendung,
        siehe Moduldocstring), bleibt der frisch angelegte Tab leer und wird
        wieder verworfen - stattdessen bleibt der bereits existierende Tab
        aktiv (add_widget()/set_current() haben bereits dorthin gewechselt).

        `_pending_label_widget = None` HIER (nicht erst in add_widget()/
        set_current()) ist wichtig: main.py's `_populate()`-Funktionen
        setzen typischerweise einen Platzhaltertitel für den NEUEN Screen,
        BEVOR dieser überhaupt gebaut/hinzugefügt wird (z.B.
        `_open_show_experiment_in_new_tab()`). Ohne diesen Reset würde
        `notify_title_set()` diesen Platzhalter fälschlich dem noch
        veralteten `_pending_label_widget` der VORHERIGEN, komplett
        unabhängigen Navigation zuordnen - und war dieses Widget gerade in
        einem ANDEREN Tab sichtbar, dessen Tab-Label sofort sichtbar
        korrumpieren (beobachtet: Öffnen eines zweiten Show-Experiment-Tabs
        überschrieb das Label des ERSTEN, obwohl dessen Inhalt unverändert
        blieb)."""
        new_idx = self._add_tab()
        self.setCurrentIndex(new_idx)
        self._pending_label_widget = None
        try:
            nav_callable()
        finally:
            stack = self.widget(new_idx)
            if stack is not None and stack.count() == 0 and self.indexOf(stack) != -1:
                idx = self.indexOf(stack)
                self.removeTab(idx)
                stack.deleteLater()

    # ------------------------------------------------------------- Close
    def _on_tab_close_requested(self, index: int, confirm: bool = True):
        """Schliesst einen einzelnen Tab (Nutzerwunsch: "diese Register kann
        ich natürlich auch einzeln schliessen"). Der letzte verbleibende Tab
        lässt sich nicht über sein eigenes 'x' schliessen (gleiches Prinzip
        wie in Browsern - dafür ist das Schliessen des ganzen Fensters da,
        siehe MainWindow.closeEvent())."""
        if self.count() <= 1:
            return
        stack = self.widget(index)
        if confirm and stack is not None:
            # unsaved changes (Show Experiment): Save / Discard / Cancel
            for i in range(stack.count()):
                ask = getattr(stack.widget(i), "confirm_close_with_unsaved", None)
                if callable(ask):
                    try:
                        if not ask():
                            return
                    except Exception:
                        pass
        self.removeTab(index)
        if stack is not None:
            # Kind-Screens NICHT löschen - das sind langlebige Singletons,
            # die anderswo weiterleben (siehe Moduldocstring). Nur der
            # Tab-Container selbst wird entsorgt, die Screens werden vorher
            # sauber "entkoppelt" (elternlos, bereit für einen künftigen Tab).
            #
            # WICHTIG: QStackedWidget.removeWidget() entfernt ein Kind nur
            # aus der internen Seiten-/Layout-Liste - der Qt-ELTERN-Bezug
            # (setParent) bleibt dabei bestehen! Ohne das explizite
            # `child.setParent(None)` unten würde `stack.deleteLater()`
            # gleich darunter über genau diesen (noch bestehenden)
            # Eltern-Bezug alle "entfernten" Kinder GLEICH MIT löschen -
            # exakt der Bug, der z.B. ExperimentRequestScreen (nie selbst
            # neu konstruierbar) beim Schliessen eines Tabs unbrauchbar
            # gemacht hat ("Internal C++ object already deleted").
            while stack.count() > 0:
                child = stack.widget(0)
                hook = getattr(child, "on_tab_closed", None)
                if callable(hook):
                    try:
                        hook()  # e.g. Show Experiment in recycle bin preview
                    except Exception:
                        pass
                stack.removeWidget(child)
                child.setParent(None)
            stack.deleteLater()

    def close_all_but_first(self):
        """Räumt alle Tabs bis auf den ersten weg (Nutzerwunsch-Ableitung:
        beim Logout soll die Session nicht mit mehreren stehengebliebenen
        Tabs aus der vorherigen Anmeldung weiterlaufen) - siehe main.py's
        _logout(). Screens werden wie bei _on_tab_close_requested() nur
        entkoppelt, nie gelöscht."""
        while self.count() > 1:
            self._on_tab_close_requested(self.count() - 1, confirm=False)
        self.setCurrentIndex(0)

    # ------------------------------------------------------------- Labels
    #
    # Der komplette Mechanismus ist bewusst rein SYNCHRON (2026-08-27 aus
    # einer deferred QTimer.singleShot(0,...)-Variante heraus umgebaut) -
    # gefundener Bug in dieser Variante: wurden zwei Tabs kurz
    # hintereinander OHNE dazwischenliegenden Event-Loop-Durchlauf geöffnet
    # (z.B. zwei schnelle Klicks), feuerten beide deferred Callbacks
    # gebündelt erst danach - zu diesem Zeitpunkt hatte sich der globale
    # Fenstertitel aber bereits ein zweites Mal geändert (zur zweiten
    # Navigation), sodass BEIDE Tabs am Ende denselben (letzten) Titel
    # übernahmen ("zwei Show-Experiment-Tabs, der zweite überschreibt den
    # ersten" - vom Nutzer nach dem Umzug des Fenstertitel-Formats in
    # ShowExperimentScreen.load_record() gemeldet, wodurch die Titel-Zuweisung
    # neu ausserhalb von add_widget()/set_current() erfolgte und damit
    # öfter in dieses Zeitfenster fiel). Die synchrone Lösung braucht keinen
    # Timer und damit auch kein Zeitfenster, in dem sich zwei Navigationen
    # überholen könnten:
    #   - notify_title_set() ordnet jeden setWindowTitle()-Aufruf SOFORT
    #     dem `_pending_label_widget` zu (deckt "Titel wird NACH dem
    #     Stack-/Tab-Wechsel gesetzt" ab, z.B. load_record()).
    #   - _record_current_title_for() (am Ende von set_current()) liest den
    #     zu diesem Zeitpunkt bereits feststehenden Titel (deckt "Titel wird
    #     VOR dem Wechsel gesetzt" ab, z.B. _go_backlog()).
    #   - _on_current_changed() (reiner Tab-Wechsel, kein add_widget()/
    #     set_current() beteiligt) stellt nur den für das jetzt sichtbare
    #     Widget bereits GEMERKTEN Titel wieder her, leitet nie einen neuen
    #     aus dem (ggf. zu einem anderen Tab gehörenden) globalen Titel ab.
    def notify_title_set(self, title: str):
        """Von MainWindow.setWindowTitle() aufgerufen (siehe main.py).

        `_restoring_title`-Guard (gefunden 2026-08-27, direkt nach dem
        obigen Timer->synchron-Umbau): _on_current_changed() ruft bei einem
        reinen Tab-Wechsel selbst `self._title_setter(title)` auf, um den
        OS-Fenstertitel an das jetzt sichtbare Tab anzugleichen - das läuft
        über GENAU DASSELBE `MainWindow.setWindowTitle()`, das auch hier
        landet. Ohne den Guard würde dieser reine Wiederherstellungs-Aufruf
        fälschlich als "neue Navigation" interpretiert und dem (zu diesem
        Zeitpunkt bereits veralteten, von der letzten ECHTEN Navigation
        stammenden) `_pending_label_widget` zugeordnet - konkret
        beobachtet: Wechsel zu Tab A rief intern setWindowTitle(A) auf,
        wodurch Tab B's gemerkter Titel auf A's Titel überschrieben wurde."""
        if self._restoring_title:
            return
        widget = self._pending_label_widget
        if widget is None:
            return
        # Nur uebernehmen, wenn `widget` GERADE TATSAECHLICH das sichtbare
        # Widget des aktiven Tabs ist (Bugreport 2026-08-27: "die tab titel
        # sind manchmal falsch, wenn es mehr als einen tab gibt"). Viele
        # `_go_X()`-Methoden rufen setWindowTitle() VOR setCurrentWidget()
        # auf (z.B. _go_my_requests()) - in diesem Moment zeigt
        # `_pending_label_widget` noch auf das Ziel des LETZTEN,
        # bereits abgeschlossenen Wechsels (moeglicherweise in einem
        # komplett ANDEREN, gerade inaktiven Tab sichtbar) - ein
        # Uebernehmen wuerde DESSEN Tab-Titel faelschlich ueberschreiben.
        # _record_current_title_for() (am Ende von set_current()/
        # add_widget(), also NACHDEM der eigentliche Wechsel passiert ist)
        # deckt diesen Fall stattdessen zuverlaessig ab - hier nur der
        # "Titel wird NACH dem Wechsel gesetzt"-Fall (z.B.
        # ShowExperimentScreen.load_record()), wo `widget` zu diesem
        # Zeitpunkt bereits unzweideutig das aktive Tab-Widget ist.
        if self.active_screen() is not widget:
            return
        self._tab_titles[widget] = title
        idx = self._find_tab_showing_widget(widget)
        if idx != -1:
            self.setTabText(idx, _pretty_tab_label(title))

    def _record_current_title_for(self, widget: QWidget):
        if self._title_provider is None:
            return
        title = self._title_provider()
        self._tab_titles[widget] = title
        idx = self._find_tab_showing_widget(widget)
        if idx != -1:
            self.setTabText(idx, _pretty_tab_label(title))

    def _on_current_changed(self, _index: int):
        """Reagiert auf JEDEN Tab-Wechsel, egal ob durch set_current() (der
        bereits selbst _record_current_title_for() aufgerufen hat - hier
        dann ein harmloses, redundantes Wiederholen desselben Werts) oder
        durch einen reinen Klick auf den Tab-Reiter selbst (dann die
        einzige Stelle, die das jetzt sichtbare Tab überhaupt beschriftet/
        den OS-Fenstertitel angleicht)."""
        self.screenChanged.emit()
        widget = self.active_screen()
        if widget is None:
            return
        title = self._tab_titles.get(widget)
        if title is None:
            return
        if self._title_setter is not None:
            self._restoring_title = True
            try:
                self._title_setter(title)
            finally:
                self._restoring_title = False
        idx = self._find_tab_showing_widget(widget)
        if idx != -1:
            self.setTabText(idx, _pretty_tab_label(title))


class _StackFacade:
    """QStackedWidget-kompatible Fassade über TabbedNavigator - existiert
    einzig, damit main.py's `self.stack` weiterhin wie der frühere, echte
    QStackedWidget benutzt werden kann (addWidget/setCurrentWidget/
    removeWidget/currentWidget/widget), obwohl "der Stack" jetzt "der Stack
    des gerade aktiven Tabs" bedeutet. Absichtlich ein eigenständiges
    Objekt statt Methoden direkt auf TabbedNavigator (das ist ein
    QTabWidget - `currentWidget()`/`widget()` bedeuten dort schon etwas
    anderes: die Tab-SEITE, nicht den darin sichtbaren Screen)."""

    def __init__(self, tabs: TabbedNavigator):
        self._tabs = tabs

    def addWidget(self, widget: QWidget) -> int:
        return self._tabs.add_widget(widget)

    def setCurrentWidget(self, widget: QWidget):
        self._tabs.set_current(widget)

    def removeWidget(self, widget: QWidget):
        self._tabs.remove_widget(widget)

    def currentWidget(self) -> Optional[QWidget]:
        return self._tabs.active_screen()

    def widget(self, index: int):
        return self._tabs.current_stack().widget(index)
