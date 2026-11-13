"""Process Playground statistics (ui/dty_whatif.py) on synthetic trials with
a known effect - no database."""
import numpy as np

from ui import dty_whatif as w


def _rows(effect=10.0, noise=1.0, seed=0, speeds=(800.0,), series=3, curved=0.0):
    """3 platelets per setting, pressure 2.0-4.0 in every series, a series
    offset, fpm = 100 + effect x (pressure - 3) + curved x (pressure - 3)^2,
    t_after unaffected by pressure."""
    rng = np.random.default_rng(seed)
    rows, tid = [], 0
    for s in range(series):
        off = 7.0 * s
        for p in (2.0, 2.5, 3.0, 3.5, 4.0):
            for sp in speeds:
                for _k in range(3):
                    tid += 1
                    rows.append({
                        "trial_id": tid, "trial_no": tid, "series_id": s, "series_name": f"S{s}",
                        "jet_id": 1, "jet_name": "J", "yarn_key": "1", "yarn_name": "PES 167f48",
                        "pressure": p, "of": 4.0, "speed": sp,
                        "fpm": 100 + off + effect * (p - 3) + curved * (p - 3) ** 2 + rng.normal(0, noise),
                        "fpm_cv": None, "stab03": None, "stab06": None, "stab10": None, "stab13": None,
                        "t_before": None, "t_after": 3.0 + 0.1 * s + rng.normal(0, 0.05),
                    })
    return w.clean_rows(rows)


def _change(rows, target, start, new):
    margins = {t: w.repeatability_sd(rows, t) for t in w.TARGETS}
    return w.change(rows, target, margins[target], start, new)


START = {"pressure": 3.0, "of": 4.0, "speed": 800.0}


def test_clear_effect_and_no_effect():
    rows = _rows()
    new = dict(START, pressure=3.5)
    fpm = _change(rows, "fpm", START, new)
    assert fpm.verdict == w.CLEAR and fpm.direction == 1
    assert abs(fpm.delta - 5.0) < 1.5            # 10 per bar x 0.5 bar
    assert fpm.series["pressure"] == (3, 3)
    t = _change(rows, "t_after", START, new)
    assert t.verdict in (w.SAME, w.NO_CLEAR)
    assert t.direction == 0


def test_series_offset_is_removed():
    # without an effect, the large series offsets must not create one
    rows = _rows(effect=0.0)
    ch = _change(rows, "fpm", START, dict(START, pressure=4.0))
    assert ch.verdict not in w.SIGNIFICANT


def test_limits():
    rows = _rows()
    # outside the measured range
    assert _change(rows, "fpm", START, dict(START, pressure=4.5)).verdict == w.OUTSIDE
    # speed never varied
    ch = _change(rows, "fpm", START, dict(START, speed=900.0))
    assert ch.verdict == w.NOT_VARIED and "Speed" in ch.reason
    # not measured at all
    assert _change(rows, "stab10", START, dict(START, pressure=3.5)).verdict == w.NO_DATA
    # nothing changed
    assert _change(rows, "fpm", START, START).verdict == w.NO_CHANGE


def test_curvature_makes_the_effect_local():
    rows = _rows(effect=0.0, curved=-20.0, noise=0.5)   # maximum at 3 bar
    up_low = _change(rows, "fpm", dict(START, pressure=2.0), dict(START, pressure=2.5))
    up_high = _change(rows, "fpm", dict(START, pressure=3.5), dict(START, pressure=4.0))
    assert up_low.direction == 1 and up_high.direction == -1
    assert "pressure" in up_low.curved


def test_never_run_and_dataset():
    rows = _rows(speeds=(800.0, 900.0, 1000.0))
    assert not w.never_run(rows, dict(START, speed=900.0))
    ds = w.build_dataset(rows)
    (c,) = ds.combos.values()
    assert set(c.varied) == {"pressure", "speed"} and c.n_series == 3 and c.n_settings == 45
    assert len(w.settings_of(c.rows)) == 45


def test_clean_rows_drops_typing_errors():
    (r,) = w.clean_rows([{"stab10": 8186.1, "stab06": 95.0, "t_before": 0, "t_after": "2.5", "pressure": "3"}])
    assert r["stab10"] is None and r["stab06"] == 95.0
    assert r["t_before"] is None and r["t_after"] == 2.5 and r["pressure"] == 3.0


def test_chart_data():
    rows = _rows()
    fit, conds, _u = w.fit_target(rows, "fpm", w.repeatability_sd(rows, "fpm"))
    d = w.chart_data(fit, conds, "pressure", START)
    gx, gy, lo, hi = d["curve"]
    assert len(d["x"]) == len(conds) and gy[-1] > gy[0]
    assert all(a <= b for a, b in zip(lo, hi))
    # speed not in the model: raw points, no curve
    assert w.chart_data(fit, conds, "speed", START)["curve"] is None


def test_free_start_conditions():
    rows = _rows(speeds=(800.0, 900.0, 1000.0))
    # start between measured values is fine
    ch = _change(rows, "fpm", dict(START, pressure=2.7), dict(START, pressure=3.2))
    assert ch.verdict == w.CLEAR and ch.start_value is not None
    # start outside the measured range: no statement, with the reason
    ch = _change(rows, "fpm", dict(START, speed=1200.0), dict(START, speed=1200.0, pressure=3.5))
    assert ch.verdict == w.OUTSIDE and "start speed" in ch.reason
    # a parameter never varied: the start has to be the value we ran
    only800 = _rows()
    ch = _change(only800, "fpm", dict(START, speed=900.0), dict(START, speed=900.0, pressure=3.5))
    assert ch.verdict == w.OUTSIDE and "never run" in ch.reason
    notes = w.start_notes(only800, dict(START, speed=900.0))
    assert notes["pressure"][0] and not notes["speed"][0]


def test_suggest_reaches_the_main_goal_and_keeps_the_others():
    rows = _rows(speeds=(800.0, 900.0, 1000.0))
    margins = {t: w.repeatability_sd(rows, t) for t in w.TARGETS}
    goals = {"fpm": w.UP, "t_after": w.KEEP}
    sugg, msg = w.suggest(rows, margins, START, goals, "fpm")
    assert sugg and msg == ""
    best = sugg[0]
    assert best.new["pressure"] > START["pressure"]          # fpm rises with pressure only
    assert best.changes["fpm"].verdict in w.SIGNIFICANT and best.changes["fpm"].direction == 1
    assert best.status["t_after"] in (w.MET, w.NEUTRAL) and best.violations == 0
    # every suggestion stays within what we measured
    assert all(2.0 <= s.new["pressure"] <= 4.0 and s.distance <= w.FAR_DISTANCE for s in sugg)


def test_suggest_says_so_when_impossible():
    rows = _rows(effect=0.0)
    margins = {t: w.repeatability_sd(rows, t) for t in w.TARGETS}
    sugg, msg = w.suggest(rows, margins, START, {"fpm": w.UP}, "fpm")
    assert sugg == [] and "Nothing" in msg
    sugg, msg = w.suggest(rows, margins, START, {"fpm": w.KEEP}, "fpm")
    assert sugg == [] and "main goal" in msg


def test_goal_status():
    up = w.Change("fpm", w.CLEAR, direction=1)
    assert w.goal_status(w.UP, up) == w.MET and w.goal_status(w.DOWN, up) == w.VIOLATED
    assert w.goal_status(w.KEEP, up) == w.VIOLATED
    assert w.goal_status(w.KEEP, w.Change("fpm", w.SAME)) == w.MET
    assert w.goal_status(w.UP, w.Change("fpm", w.NO_CLEAR)) == w.NEUTRAL
    assert w.goal_status(w.UP, w.Change("fpm", w.UNCLEAR)) == w.UNKNOWN
