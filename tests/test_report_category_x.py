"""Series report (Show Experiment): Yarn (tblYarn.Kurzname) and Jet as X fields and a second
X level per chart (Nutzerwunsch 2026-11-02). Checked on dev_local with series 277: X = Yarn,
second level = Jet gives exactly the 11 yarn/jet combinations of the series, bars and box
plots as two-level axis, double-click drills to the trials of that yarn and jet."""
from ui.report_html_template import _HTML_TEMPLATE
from ui.report_queries import CATEGORY_X_AXES, with_category_axes


def test_yarn_and_jet_are_added_once():
    base = [{"key": "air_pressure", "title": "Air Pressure"}, {"key": "jet_name", "title": "Jet (DB)"}]
    keys = [x["key"] for x in with_category_axes(base)]
    assert keys == ["air_pressure", "jet_name", "yarn_short"]          # the DB's own jet_name wins
    assert all(c["cat"] for c in CATEGORY_X_AXES) and base[1]["title"] == "Jet (DB)"


def test_page_has_the_second_level():
    for part in ("x2Field", "_toMulticategory", "_comboField", "sel-x2", "MC_LABELS", "multicategory"):
        assert part in _HTML_TEMPLATE
    # both places that draw a chart know the second level: updateChart and the first render of the grid
    # (opening a saved report, "→ All") - the second one was missing at first
    assert _HTML_TEMPLATE.count("_toMulticategory(") == 3            # definition + 2 callers
    # saved reports keep the second level
    assert "x2Field:     s.x2Field    || ''" in _HTML_TEMPLATE and "x2Field:     b.x2Field   || ''" in _HTML_TEMPLATE
