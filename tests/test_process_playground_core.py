"""ui/process_playground_core.py - Process Playground without Qt (shared by desktop screen and web)."""
import subprocess
import sys
from pathlib import Path

import pytest

from ui import dty_whatif as w
from ui import process_playground_core as ppc

ROOT = Path(__file__).resolve().parents[1]


def test_qt_free():
    code = ("import sys; import ui.process_playground_core; "
            "sys.exit(1 if any(m.startswith('PySide6') for m in sys.modules) else 0)")
    assert subprocess.run([sys.executable, "-c", code], cwd=str(ROOT)).returncode == 0


@pytest.fixture(scope="module")
def ds():
    try:
        d = w.build_dataset(w.load_rows())
    except Exception as e:  # pragma: no cover - no database
        pytest.skip(f"no database: {e}")
    if not d.combos:
        pytest.skip("no combinations")
    return d


def test_combos_and_start(ds):
    lst = ppc.combos_list(ds)
    assert len(lst) == len(ds.combos)
    c = ppc.find_combo(ds, lst[0]["key"])
    assert c is not None and c.yarn_name == lst[0]["yarn"]
    opts, best = ppc.settings_options(c)
    assert opts and best is not None
    start = opts[best]["start"]
    assert all(start[p] is not None for p in w.PARAMS)
    # no slider moved -> no change, a hint
    new = ppc.new_settings(c, start, {p: start[p] for p in w.PARAMS})
    assert new == start
    ev = ppc.evaluate(ds, c, start, new, {})
    assert ev["changed"] == [] and len(ev["rows"]) == len(w.TARGETS)
    assert all(r["statement"] == "" for r in ev["rows"])


def test_move_and_chart(ds):
    c = ppc.find_combo(ds, ppc.combos_list(ds)[0]["key"])
    opts, best = ppc.settings_options(c)
    start = opts[best]["start"]
    rng = ppc.slider_ranges(c)
    p = c.varied[0]
    target = rng[p]["hi"] if abs(start[p] - rng[p]["hi"]) > 1e-9 else rng[p]["lo"]
    new = ppc.new_settings(c, start, {p: target + 1000})          # clamped to the measured range
    assert new[p] == pytest.approx(rng[p]["hi"]) or new[p] == pytest.approx(rng[p]["lo"])
    fits = {}
    ev = ppc.evaluate(ds, c, start, new, fits)
    assert ev["changed"] == [p] and ppc.WARN_MOVE not in ev["warnings"]
    assert any(r["statement"] for r in ev["rows"])
    # not varied parameters never move
    for q in w.PARAMS:
        if q not in c.varied:
            assert ppc.new_settings(c, start, {q: (start[q] or 0) + 5})[q] == start[q]
    ch = ppc.chart_json(ds, c, fits, next(iter(w.TARGETS)), p, start, new)
    if ch is not None:
        assert len(ch["x"]) == len(ch["y"]) and ch["start"] == start[p]


def test_suggestions_and_trial(ds):
    c = ppc.find_combo(ds, ppc.combos_list(ds)[0]["key"])
    opts, best = ppc.settings_options(c)
    start = opts[best]["start"]
    goals = {"stab10": w.UP}
    sugg, _msg = w.suggest(c.rows, ds.margins, start, goals, "stab10", fit_cache={})
    js = ppc.suggestions_json(sugg, start, goals, "stab10")
    assert js["targets"][0] == "stab10" and len(js["rows"]) == len(sugg)
    row = next(r for r in c.rows if r.get("trial_id") is not None)
    key, st = ppc.trial_start(ds, row["trial_id"])
    assert key == ppc.combo_key(c) and set(st) == set(w.PARAMS)
    assert ppc.trial_start(ds, -12345) is None
