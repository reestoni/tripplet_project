"""Yarn Count Converter logic (ui/yarn_count.py)."""
import math

import pytest

from ui import yarn_count as yc


def approx(a, b, rel=1e-3):
    return math.isclose(a, b, rel_tol=rel)


def test_known_values():
    r = yc.convert(167, "dtex")
    assert approx(r["den"], 150.3)
    assert approx(r["tex"], 16.7)
    assert approx(r["Nm"], 1000 / 16.7)
    assert approx(yc.convert(150, "den")["dtex"], 166.67)
    assert approx(yc.convert(1, "Nm")["tex"], 1000)
    assert approx(yc.convert(30, "Ne")["tex"], 19.685, rel=1e-3)   # Ne 30 ~ 19.7 tex
    assert approx(yc.convert(20, "tex")["Ne"], 29.53, rel=1e-3)


def test_round_trip_all_units():
    for unit, *_ in yc.UNITS:
        r = yc.convert(42.0, unit)
        for other, *_ in yc.UNITS:
            assert approx(yc.convert(r[other], other)[unit], 42.0, rel=1e-9), (unit, other)


def test_invalid_values():
    for v in (0, -5):
        with pytest.raises(ValueError):
            yc.convert(v, "dtex")


def test_notation():
    p = yc.parse_notation("167f48")
    assert p["unit"] == "dtex" and p["filaments"] == 48 and p["plies"] == 1
    assert approx(p["dtex_f"], 167 / 48)
    p = yc.parse_notation("150D/48F")
    assert p["unit"] == "den" and p["filaments"] == 48 and approx(p["total_dtex"], 166.67)
    p = yc.parse_notation("2x167f48")
    assert p["plies"] == 2 and approx(p["total_dtex"], 334) and p["total_filaments"] == 96
    p = yc.parse_notation("78f68x2")
    assert p["plies"] == 2 and p["total_filaments"] == 136
    p = yc.parse_notation("dtex 167 f48")
    assert p["unit"] == "dtex" and p["filaments"] == 48
    p = yc.parse_notation("300/96", default_unit="den")
    assert p["unit"] == "den" and p["filaments"] == 96
    p = yc.parse_notation("44,4 dtex")
    assert approx(p["count"], 44.4) and p["filaments"] is None
    p = yc.parse_notation("Nm 40")
    assert p["unit"] == "Nm" and approx(p["total_dtex"], 250)
    for bad in ("", "abc", "0f48", "167f0", "f48"):
        assert yc.parse_notation(bad) is None, bad


def test_filament_diameter():
    # 1 dtex polyester filament ~ 9.6 um
    assert approx(yc.filament_diameter_um(1.0, 1.38), 9.606, rel=1e-3)
    assert yc.filament_diameter_um(4.0, 1.38) == pytest.approx(2 * yc.filament_diameter_um(1.0, 1.38))


def test_fmt():
    assert yc.fmt(150.3) == "150.3"
    assert yc.fmt(166.6666) == "166.7"
    assert yc.fmt(3.479) == "3.48"
    assert yc.fmt(1000.0) == "1'000"
    assert yc.fmt(0.12345) == "0.123"


def test_more_units():
    r = yc.convert(1000, "tex")
    assert approx(r["ktex"], 1.0) and approx(r["mtex"], 1_000_000)
    assert approx(yc.convert(1, "Run")["tex"], 310.03, rel=1e-4)
    assert approx(yc.convert(1, "NeL")["tex"], 1653.5, rel=1e-4)
    assert approx(yc.convert(1, "gryd")["tex"], 70.86, rel=1e-3)   # 1 grain/yd ~ 70.86 tex
    assert approx(yc.UNIT["Ne"][3], 590.54, rel=1e-4) and approx(yc.UNIT["NeK"][3], 885.81, rel=1e-4)


def test_formulas_and_designation():
    assert yc.formula("dtex") == "tex = dtex / 10"
    assert yc.formula("Ne") == "tex = 590.54 / Ne"
    assert yc.formula("ktex") == "tex = ktex × 1'000"
    assert all(yc.formula(u[0]).startswith("tex = ") for u in yc.UNITS)
    assert yc.notation(167, 48, 1) == "dtex 167 f48 · 150.3 den / 48 f"
    assert yc.notation(167, 48, 2).startswith("2 × dtex 167 f48")
    assert yc.notation(167, None, 1) == "dtex 167 · 150.3 den"


def test_filament_values():
    from ui import yarn_count as yc
    v = yc.filament_values(16.7, 48, 2, 1.38)
    assert round(v["total_dtex"], 6) == 334.0 and round(v["total_den"], 6) == 300.6
    assert v["total_fil"] == 96 and round(v["dpf_dtex"], 4) == round(167 / 48, 4)
    assert v["designation"].startswith("2 × dtex 167 f48")
    none = yc.filament_values(None, 48, 1, 1.38)
    assert none["total_dtex"] is None and none["designation"] is None
    nofil = yc.filament_values(16.7, None, 1, 1.38)
    assert nofil["dpf_dtex"] is None and nofil["diameter"] is None and nofil["total_fil"] is None
