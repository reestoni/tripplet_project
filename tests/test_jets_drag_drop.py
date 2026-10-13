"""
TrippleT – Jets-Tabelle: Zeilen-Umsortierung (Drag&Drop + Up/Down)
====================================================================
Regressionstest fuer den 2026-08-31-Bugfix: "die bewegte Zeile
verschwindet nach dem Loslassen" (Create Experiment, tblJets). Ursache war
NICHT die Umsortierungs-Arithmetik selbst (_move_jet_row(), hier getestet),
sondern dass Qt's eigenes InternalMove-Drag nach dem Drop zusaetzlich
clearOrRemove() aufruft und die Original-Zeile ein zweites Mal entfernt,
sobald acceptProposedAction() (== Qt.MoveAction) verwendet wird - siehe
ReadOnlyTable.dropEvent() in ui/screen_create_experiment.py. Das ist reine
Qt-DnD-Eventschleifen-Mechanik und lässt sich hier nicht sinnvoll
end-to-end simulieren; dieser Test deckt die Umsortierungslogik ab, die
sowohl von den Up/Down-Buttons als auch vom Drag&Drop-Dropziel
(_on_jet_row_dragged()) gemeinsam genutzt wird.

Keine echte DB nötig – CreateExperimentScreen wird per __new__() ohne
__init__() gebaut (_move_jet_row() liest ausschliesslich self.tblJets/
self._jets_data, keine anderen Instanz-Attribute).
"""

import os
import pytest

from PySide6.QtWidgets import QApplication, QTableWidgetItem

from ui.screen_create_experiment import CreateExperimentScreen, ReadOnlyTable


def _make_bare_screen(rows):
    """Baut eine CreateExperimentScreen-Instanz ohne __init__(), mit einer
    tblJets-Tabelle + _jets_data, die _move_jet_row() direkt bedienen kann.
    `rows`: Liste von Labels, eine Zeile pro Label (Spalte 0 = Label,
    _jets_data[i] = {"label": ...})."""
    screen = CreateExperimentScreen.__new__(CreateExperimentScreen)
    screen.tblJets = ReadOnlyTable(len(rows), 1)
    screen._jets_data = []
    for r, label in enumerate(rows):
        screen.tblJets.setItem(r, 0, QTableWidgetItem(label))
        screen._jets_data.append({"label": label})
    return screen


def _table_labels(screen):
    return [screen.tblJets.item(r, 0).text() for r in range(screen.tblJets.rowCount())]


def _data_labels(screen):
    return [d["label"] for d in screen._jets_data]


class TestMoveJetRow:

    @pytest.fixture
    def qapp(self, qtbot):
        return QApplication.instance()

    def test_move_down(self, qapp):
        screen = _make_bare_screen(["A", "B", "C", "D", "E"])
        screen._move_jet_row(1, 4)
        assert _table_labels(screen) == ["A", "C", "D", "E", "B"]
        assert _data_labels(screen) == ["A", "C", "D", "E", "B"]
        assert screen.tblJets.rowCount() == 5

    def test_move_up(self, qapp):
        screen = _make_bare_screen(["A", "B", "C", "D", "E"])
        screen._move_jet_row(4, 1)
        assert _table_labels(screen) == ["A", "E", "B", "C", "D"]
        assert _data_labels(screen) == ["A", "E", "B", "C", "D"]
        assert screen.tblJets.rowCount() == 5

    def test_move_adjacent_down(self, qapp):
        screen = _make_bare_screen(["A", "B", "C"])
        screen._move_jet_row(0, 1)
        assert _table_labels(screen) == ["B", "A", "C"]
        assert _data_labels(screen) == ["B", "A", "C"]

    def test_move_adjacent_up(self, qapp):
        screen = _make_bare_screen(["A", "B", "C"])
        screen._move_jet_row(1, 0)
        assert _table_labels(screen) == ["B", "A", "C"]
        assert _data_labels(screen) == ["B", "A", "C"]

    def test_move_to_same_row_is_noop(self, qapp):
        screen = _make_bare_screen(["A", "B", "C"])
        screen._move_jet_row(1, 1)
        assert _table_labels(screen) == ["A", "B", "C"]
        assert _data_labels(screen) == ["A", "B", "C"]

    def test_no_row_lost_across_all_pairs(self, qapp):
        """Jede moegliche (src, dst)-Kombination auf einer 6-Zeilen-Tabelle
        darf weder eine Zeile verlieren noch duplizieren - Kernaussage des
        Bugreports ("Zeile verschwindet")."""
        labels = ["A", "B", "C", "D", "E", "F"]
        for src in range(len(labels)):
            for dst in range(len(labels)):
                screen = _make_bare_screen(labels)
                screen._move_jet_row(src, dst)
                assert screen.tblJets.rowCount() == len(labels), (src, dst)
                assert sorted(_table_labels(screen)) == sorted(labels), (src, dst)
                assert sorted(_data_labels(screen)) == sorted(labels), (src, dst)
                assert _table_labels(screen) == _data_labels(screen), (src, dst)

    def test_drag_handler_matches_move_jet_row(self, qapp):
        """_on_jet_row_dragged() (Drag&Drop-Einstiegspunkt) muss dieselbe
        Umsortierung liefern wie ein direkter _move_jet_row()-Aufruf."""
        screen = _make_bare_screen(["A", "B", "C", "D"])
        screen._on_jet_row_dragged(0, 2)
        assert _table_labels(screen) == ["B", "C", "A", "D"]
        assert _data_labels(screen) == ["B", "C", "A", "D"]
