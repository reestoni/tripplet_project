"""Tests fuer ui/widgets/yarn_locations.py (Spulen-Symbol + Lagerplaetze in
Show Experiment): Sortierung der Lagerplaetze und Huelsenfarben-Erkennung."""
import pytest
from PySide6.QtWidgets import QApplication

from ui.widgets.yarn_locations import (
    StockSummary, location_sort_key, stock_symbol_html, stock_symbol_tooltip, tube_colours,
)


@pytest.fixture(scope="module", autouse=True)
def _app():
    return QApplication.instance() or QApplication([])


def test_locations_sort_naturally_empty_last():
    locs = ["E12", "", "e2", "D53", None, "C31"]
    assert sorted(locs, key=location_sort_key) == ["C31", "D53", "e2", "E12", "", None]


@pytest.mark.parametrize("text, expected", [
    ("Black/Yellow", ["#1a1a1a", "#ffff00"]),
    ("white / green", ["#ffffff", "#008000"]),
    ("Pink/Lila", ["#ffc0cb", "#800080"]),
    ("Blac/Yellow", ["#1a1a1a", "#ffff00"]),
    ("Yellow with print", ["#ffff00"]),
    ("brown conical", ["#a52a2a"]),
    ("", []),
    ("xyz", []),
])
def test_tube_colours(text, expected):
    assert [c.name() for c in tube_colours(text)] == expected


def test_symbol_link_only_when_in_stock():
    assert 'href="stock:5"' in stock_symbol_html(5, StockSummary(2, 4.0, 1))
    assert 'href="nostock:5"' in stock_symbol_html(5, None)
    assert stock_symbol_tooltip(None) == "Not in stock"
    assert "2 spools, 4.0 kg in 1 location" in stock_symbol_tooltip(StockSummary(2, 4.0, 1))
