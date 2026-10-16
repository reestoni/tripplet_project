"""Smart Chart advanced filters -> SQL (ui.screen_report.advanced_filter_sql)."""
import pytest

pytest.importorskip("PySide6")

from ui.screen_report import MACHINE_JOIN, advanced_filter_sql


def test_trial_jet_machine_use_existing_aliases():
    where, params, joins = advanced_filter_sql([
        {"table": "tbltrial", "field": "AirPressure", "op": ">", "value": "3.5"},
        {"table": "tbljets", "field": "Jet", "op": "IN", "values": ["A", "B"]},
        {"table": "tblmaschine", "field": "Maschine", "op": "=", "value": "RPR"},
    ])
    assert where == ["T.AirPressure > ?", "J.Jet IN (?,?)", "MC.Maschine = ?"]
    assert params == [3.5, "A", "B", "RPR"]
    assert joins == []
    assert "AS MC " in MACHINE_JOIN


def test_lab_table_is_exists_per_trial():
    where, params, _ = advanced_filter_sql([
        {"table": "tbllaboritematlab", "field": "Tension", "op": ">=", "value": "10"},
        {"table": "tbllabortiter", "field": "Titer", "op": "IS NULL"},
    ])
    assert where[0] == ("EXISTS (SELECT 1 FROM tbllaboritematlab AS adv WHERE adv.TrialID = T.ID "
                        "AND adv.Tension >= ?)")
    assert where[1] == ("NOT EXISTS (SELECT 1 FROM tbllabortiter AS adv WHERE adv.TrialID = T.ID "
                        "AND adv.Titer IS NOT NULL)")
    assert params == [10.0]


def test_jet_blank_goes_through_the_jet():
    where, _, joins = advanced_filter_sql([{"table": "tbljetrohling", "field": "Nummer", "op": "IS NOT NULL"}])
    assert where == ["adv_tbljetrohling.Nummer IS NOT NULL"]
    assert joins == ["LEFT JOIN tbljetrohling AS adv_tbljetrohling ON adv_tbljetrohling.ID = J.Rohling"]


def test_like_and_empty_values():
    where, params, _ = advanced_filter_sql([
        {"table": "tbljets", "field": "Jet", "op": "LIKE", "value": "Slide"},
        {"table": "tbltrial", "field": "AirPressure", "op": ">", "value": ""},
        {"table": "tbljets", "field": "Jet", "op": "IN", "values": []},
    ])
    assert where == ["J.Jet LIKE ?"]
    assert params == ["%Slide%"]


@pytest.mark.parametrize("af", [
    {"table": "tbltrial; DROP TABLE tbluser", "field": "ID", "op": "=", "value": "1"},
    {"table": "tbltrial", "field": "ID) OR (1", "op": "=", "value": "1"},
    {"table": "tbltrial", "field": "ID", "op": "= 1 OR 1 =", "value": "1"},
])
def test_nothing_unchecked_reaches_the_sql(af):
    assert advanced_filter_sql([af]) == ([], [], [])


def test_whitelist():
    allowed = {("tbltrial", "airpressure")}
    where, _, _ = advanced_filter_sql([
        {"table": "tbltrial", "field": "AirPressure", "op": ">", "value": "1"},
        {"table": "tbluser", "field": "Password", "op": "IS NOT NULL"},
    ], allowed)
    assert where == ["T.AirPressure > ?"]
