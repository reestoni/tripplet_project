"""ui/yarnscope/sensor_pair.py - two sensors one behind the other, synthetic DTY-like yarn (no hardware, no DB).

The second sensor sees the same yarn L samples later (+ its own noise and another empty level): the delay, the
speed from the distance, the distance from the speed, the speed per window and the knot pairing must come out."""
import numpy as np
import pytest

from ui.yarnscope import sensor_pair as sp
from ui.yarnscope.dty_analysis import knot_runs

RATE = 50933.33          # 764 m/min / 0.25 mm
SPEED = 764.0


def _yarn(n, seed=1):
    """Open parts ~700 µm, knots ~480 µm, lengths like a real DTY (knots 2-6 mm, open 1-4 mm at 0.25 mm)."""
    rng = np.random.default_rng(seed)
    y = np.empty(n)
    i, knot = 0, False
    while i < n:
        k = int(rng.integers(8, 24) if knot else rng.integers(4, 16))
        y[i:i + k] = (480 + rng.normal(0, 25)) if knot else (700 + rng.normal(0, 20))
        i += k
        knot = not knot
    return y


def _pair(n=200_000, lag=400, noise=9.0, offset_b=-120.0, seed=1):
    s = _yarn(n + lag, seed)
    rng = np.random.default_rng(seed + 10)
    a = s[lag:lag + n] + rng.normal(0, noise, n)          # sensor 1 sees the yarn first
    b = s[:n] + rng.normal(0, noise, n) + offset_b         # sensor 2: lag samples later, other empty level
    return a, b


def test_delay_speed_and_distance():
    lag = 400                                              # 400 samples at 50'933 Hz = 7.853 ms
    a, b = _pair(lag=lag)
    distance = SPEED / 60.0 * (lag / RATE) * 1000.0        # the distance that belongs to that delay: 100.0 mm
    r = sp.pair_report([a], [b], RATE, 0.25, distance_mm=distance, nominal_speed=SPEED)
    assert r["reliable"] and r["corr"] > 0.9
    assert abs(r["lag_samples"] - lag) < 0.3
    assert r["speed"] == pytest.approx(SPEED, rel=0.002)
    assert r["distance_from_speed_mm"] == pytest.approx(distance, abs=0.2)
    assert len(r["profile"]) == 5 and all(abs(p["speed"] - SPEED) < 5 for p in r["profile"])   # 50 m / 10 m


def test_same_knots_found():
    a, b = _pair(lag=250)
    r = sp.pair_report([a], [b], RATE, 0.25)
    k = r["knots"]
    na = len(knot_runs(a)[0])
    assert k["knots_a"] > 0.9 * na and k["pct_a"] > 95 and k["pct_b"] > 95
    assert abs(k["len_diff_mm"]) < 0.2 and k["pos_sd_mm"] < 0.5
    # without distance / speed: no speed, but the knot pairing still works
    assert "speed" not in r and r["delay_ms"] == pytest.approx(250 / RATE * 1000, abs=0.01)


def test_two_axis_and_negative_or_unsynced():
    a, b = _pair(lag=300)
    rng = np.random.default_rng(5)
    ax_a = [a, a + 200 + rng.normal(0, 9, len(a))]         # 2-axis head: y another level
    r = sp.pair_report(ax_a, [b], RATE, 0.25, synced=False, nominal_speed=SPEED)
    assert abs(r["lag_samples"] - 300) < 0.5
    assert "speed" not in r and "profile" not in r and "distance_from_speed_mm" not in r   # no common clock
    r2 = sp.pair_report([b], [a], RATE, 0.25)              # the other way round: negative delay
    assert abs(r2["lag_samples"] + 300) < 0.5


def test_unrelated_signals_are_not_reliable():
    a, _ = _pair(seed=1)
    c, _ = _pair(seed=7)
    r = sp.pair_report([a], [c], RATE, 0.25, distance_mm=100, nominal_speed=SPEED)
    assert r["reliable"] is False and "speed" not in r and "knots" not in r
