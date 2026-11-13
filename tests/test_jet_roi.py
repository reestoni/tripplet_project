"""ui/jet_roi.py - Jet ROI Calculator computing part (Qt-free since 2026-11-13, shared with the web)."""
import io
import math

import pytest

from ui import jet_roi as j

JET = {"ID": 1, "Jet": "S315", "_diam": 1.1, "Luftbohrung": "1.1", "LuftlochAnzahl": 1, "Luftverbrauch": 0.6,
       "Hersteller": 1, "Prozess": 2, "JetTypeID": 1}


def _inp(**kw):
    d = dict(positions="100", hours="8000", cost_m3="0.04", nozzle_px="100", comp_pressure=4.0, comp_type="X",
             comp_diam="1.3", comp_holes="1", heb_pressure=4.0, heb_mode="product", heb_jet=JET, heb_holes="1",
             sym="CHF", process="DTY")
    d.update(kw)
    return d


def test_flow_formula():
    assert j.air_flow_nm3h(1.1, 1, 0.0) == pytest.approx(0.562)          # reference: 1.1 mm at 0 bar_g
    assert j.air_flow_nm3h(1.0, 2, 4.0, luftverbrauch=0.5) == pytest.approx(0.5 * 2 * 5)
    assert j.bar_g_from_input(14.5038, "PSI") == pytest.approx(1.0)


def test_single():
    assert j.validate_single(_inp()) is None
    assert j.validate_single(_inp(positions="0"))[0] == "positions"
    assert j.validate_single(_inp(heb_jet=None))[0] == "heb_jet"
    assert j.validate_single(_inp(heb_mode="manual", heb_type="P1", heb_diam="12"))[0] == "heb_diam"
    d = j.calculate_single(_inp())
    comp = j.air_flow_nm3h(1.3, 1, 4.0)
    assert d["comp_qh"] == pytest.approx(comp) and d["heb_qh"] == pytest.approx(3.0)
    assert d["saving_yr"] == pytest.approx((comp - 3.0) * 8000 * 0.04 * 100)
    assert d["amort"] == pytest.approx(10000 / d["saving_yr"])
    assert d["be_str"].endswith("bar") and d["heb_type"] == "S315"
    worse = j.calculate_single(_inp(comp_diam="0.5"))
    assert worse["amort"] == math.inf
    c = j.single_chart(d["comp_cost_yr"], d["heb_cost_yr"], 100, 100)
    assert c["years"] == [0, 1, 2, 3, 4, 5] and c["heb"][0] == 10000 and c["breakeven"] == pytest.approx(d["amort"])


def test_multi_and_process_filter():
    a = {"Jet": "A", "Luftbohrung": "1.3", "LuftlochAnzahl": 1}
    rows = [dict(label="", pos="10", hours="8000", a_jet=a, b_jet=JET, a_price="0", b_price="100", a_pressure=4, b_pressure=4),
            dict(label="incomplete", pos="1", hours="1", a_jet=None, b_jet=JET)]
    m = j.calculate_multi(rows, 0.04, "CHF")
    assert len(m["results"]) == 1 and m["results"][0]["label"] == "#1"
    assert m["totals"]["invest"] == 1000 and m["totals"]["amort"] == pytest.approx(1000 / m["totals"]["saving"])
    assert j.calculate_multi(rows[1:], 0.04, "CHF") is None
    ch = j.multi_chart(m["totals"]["saving"], 1000)
    assert ch["b"][0] == 1000 and ch["a"][0] == 0
    assert j.jet_matches_process(JET, "DTY") and not j.jet_matches_process(JET, "ATY")
    assert [o["name"] for o in j.jet_options([JET, {**JET, "Prozess": 3, "Jet": "Q"}], "ATY")] == ["Q"]


def test_pdfs_to_memory():
    b = io.BytesIO()
    j.generate_pdf(b, j.calculate_single(_inp()))
    assert b.getvalue()[:4] == b"%PDF"
    m = j.calculate_multi([dict(label="L", pos="2", hours="100", a_jet={"Jet": "A", "Luftbohrung": "1.3"}, b_jet=JET,
                                a_price="0", b_price="50", a_pressure=4, b_pressure=4)], 0.04, "CHF")
    b2 = io.BytesIO()
    j.generate_multi_pdf(b2, m["results"], m["totals"])
    assert b2.getvalue()[:4] == b"%PDF"
