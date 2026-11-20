"""Effective intermingling points per tension in the report and in Smart Chart (Nutzerwunsch 2026-11-20).

FP/m(t) = FP/m at tension 0 * Stability(t) / 100, computed on reading (ui/report_queries.effective_fpm_values),
also where the stored FPm of the tension row is missing. The axes are added in code, not in tblSmartChartAxis.
The DB test runs in a subprocess on dev_local (see test_report_service.py) and is skipped without the local DB.
"""
import json
import os
import subprocess
import sys
import textwrap

import pytest

from ui import report_queries as rq

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_axes_follow_the_stability_axes():
    db_like = [dict(a) for a in rq.Y_AXES if a["field"] != rq.EFFECTIVE_FPM_FIELD]
    keys = [a["key"] for a in rq.with_effective_fpm_axes(db_like)]
    i = keys.index("stab_13")
    assert keys[i + 1:i + 5] == ["fpm_eff_03", "fpm_eff_06", "fpm_eff_10", "fpm_eff_13"]
    # already there (e.g. later as DB rows) -> not twice
    again = rq.with_effective_fpm_axes(rq.with_effective_fpm_axes(db_like))
    assert [a["key"] for a in again].count("fpm_eff_10") == 1
    eff = [a for a in rq.EFFECTIVE_FPM_AXES]
    assert {a["unit"] for a in eff} == {"FP/m"}
    assert [a["condition"] for a in eff] == ["Tension = 0.3", "Tension = 0.6", "Tension = 1", "Tension = 1.3"]


def test_values_on_dev_local():
    script = textwrap.dedent("""
        import os, sys, json
        os.environ["TRIPPLET_MODE"] = "dev_local"
        sys.path.insert(0, {root!r})
        from db import connection
        assert connection.current_db_name() == "tripplet_dev_local"
        try:
            connection.fetch_all("SELECT 1 AS x")
        except Exception as e:
            print(json.dumps({{"__skip__": str(e)}})); sys.exit(0)
        from ui import report_queries as rq
        from db import trial_explorer as te
        rows = connection.fetch_all(
            "SELECT s.TrialID AS tid, s.Stability AS st, z.FPm AS ip0, s.FPm AS fpm_t "
            "FROM tbllaboritematlab s JOIN tbllaboritematlab z ON z.TrialID = s.TrialID AND z.Tension = 0 "
            "WHERE s.Tension = 1 AND s.Stability > 0 AND z.FPm > 0 ORDER BY s.ID DESC LIMIT 200")
        rows = [r for r in rows if sum(1 for x in rows if x["tid"] == r["tid"]) == 1][:50]
        vals = rq._fetch_y_values([int(r["tid"]) for r in rows], "tbllaboritematlab", "tbllaboritematplus",
                                  rq.EFFECTIVE_FPM_FIELD, "Tension = 1")
        diffs = [abs(vals[int(r["tid"])] - float(r["ip0"]) * float(r["st"]) / 100) for r in rows]
        stored = [abs(vals[int(r["tid"])] - float(r["fpm_t"])) for r in rows if r["fpm_t"] is not None]
        cat = {{f.key: f for f in te.build_catalog()}}
        y, _x, _g = rq._load_axes_from_db()
        out = {{"n": len(rows), "max_diff": max(diffs) if diffs else 0, "max_stored": max(stored) if stored else 0,
               "in_catalog": all(k in cat for k in ("fpm_eff_03", "fpm_eff_13")),
               "axes": [a["key"] for a in (y or [])]}}
        print(json.dumps(out))
    """).format(root=_ROOT)
    res = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=180)
    assert res.returncode == 0, res.stderr[-2000:]
    out = json.loads(res.stdout.strip().splitlines()[-1])
    if "__skip__" in out:
        pytest.skip(out["__skip__"])
    assert out["n"] > 0
    assert out["max_diff"] < 1e-6                    # exactly IP(0) * Stability / 100
    assert out["max_stored"] < 0.01                  # same as the stored value (only rounding)
    assert out["in_catalog"]
    assert "fpm_eff_10" in out["axes"]
