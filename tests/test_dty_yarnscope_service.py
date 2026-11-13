"""Tests for ui/yarnscope/dty_service.py (Qt-free logic of the DTY YarnScope tab)."""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from ui.yarnscope import dty_service as svc

ROOT = Path(__file__).resolve().parents[1]


def test_imports_without_pyside6():
    code = (
        "import sys\n"
        "import ui.yarnscope.dty_service as s\n"
        "import ui.yarnscope.dty_analysis, ui.yarnscope.dty_tdms_reader\n"
        "assert 'PySide6' not in sys.modules, 'PySide6 imported'\n"
        "print('ok')\n"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT),
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    assert "ok" in out.stdout


# ---------------------------------------------------------------------------
# Decimation
# ---------------------------------------------------------------------------

def test_minmax_decimate_short_trace_unchanged():
    x = np.arange(10.0)
    y = np.sin(x)
    dx, dy = svc.minmax_decimate(x, y, 100)
    assert np.array_equal(dx, x) and np.array_equal(dy, y)


def test_minmax_decimate_keeps_extremes_and_limit():
    rng = np.random.default_rng(1)
    n = 400_000
    x = np.arange(n) * 0.00025
    y = rng.normal(100.0, 5.0, n)
    y[123_457] = 500.0   # isolated spike
    y[300_001] = -50.0   # isolated dip
    dx, dy = svc.minmax_decimate(x, y, 8000)
    assert len(dx) <= 8000
    assert np.all(np.diff(dx) > 0)          # original order kept
    assert dy.max() == 500.0 and dy.min() == -50.0
    assert 123_457 * 0.00025 in dx
    # every bucket keeps its own min and max
    edges = np.linspace(0, n, 4001).astype(int)
    for s, e in zip(edges[:-1:500], edges[1::500]):
        assert y[s:e].max() in dy and y[s:e].min() in dy


def test_minmax_decimate_ignores_nan():
    y = np.array([1.0, np.nan, 3.0, np.nan] * 5000)
    x = np.arange(len(y), dtype=float)
    dx, dy = svc.minmax_decimate(x, y, 100)
    assert not np.isnan(dy).any()
    assert dy.max() == 3.0 and dy.min() == 1.0


def test_trace_json_window_full_resolution():
    x = np.arange(100_000) * 0.001
    y = np.cos(x)
    out = svc.trace_json(x, y, 10.0, 12.0, max_points=8000)
    assert out["decimated"] is False
    assert out["n_source"] == len(out["x"]) == 2001
    assert out["x"][0] == pytest.approx(10.0) and out["x"][-1] == pytest.approx(12.0)
    whole = svc.trace_json(x, y, max_points=1000)
    assert whole["decimated"] is True and len(whole["x"]) <= 1000
    json.dumps(whole)


# ---------------------------------------------------------------------------
# TDMS lookup
# ---------------------------------------------------------------------------

def test_parse_tdms_ids():
    assert svc.parse_tdms_ids("157_1_041125_0855") == (157, 1)
    assert svc.parse_tdms_ids("abc157_12_x") == (157, 12)
    assert svc.parse_tdms_ids("157") is None
    assert svc.parse_tdms_ids("x_1_y") is None


def test_file_lookup_in_temp_folder(tmp_path, monkeypatch):
    for name in ("157_1_041125_0855.tdms", "157_3_041125_0905.TDMS", "abc157_4_x.tdms",
                 "158_1_x.txt", "1570_2_y.tdms"):
        (tmp_path / name).write_bytes(b"")
    monkeypatch.setenv(svc.ENV_TDMS_DIR, str(tmp_path))
    assert svc.tdms_base() == tmp_path
    assert svc.series_has_tdms(157)
    assert not svc.series_has_tdms(158)        # only a .txt
    assert svc.find_tdms(157, 1).name == "157_1_041125_0855.tdms"
    assert svc.find_tdms(157, 3).name == "157_3_041125_0905.TDMS"
    assert svc.find_tdms(157, 4).name == "abc157_4_x.tdms"   # fallback via parse_tdms_ids
    assert svc.find_tdms(157, 2) is None
    trials = [{"ID": 11, "Versuchsnummer": 1}, {"ID": 12, "Versuchsnummer": 2},
              {"ID": 13, "Versuchsnummer": 3}, {"ID": 14, "Versuchsnummer": None}]
    files = svc.trial_files(157, trials, reference_ids={13: "Ref"})
    assert [f["trial_id"] for f in files] == [11, 12, 14]
    assert [f["vno"] for f in files] == [1, 2, 0]
    assert files[0]["tdms"].name.startswith("157_1_") and files[1]["tdms"] is None
    assert svc.find_tdms(157, 1, base=tmp_path / "missing") is None
    monkeypatch.delenv(svc.ENV_TDMS_DIR)
    assert str(svc.tdms_base()) == svc.DEFAULT_TDMS_DIR


# ---------------------------------------------------------------------------
# Save (DB calls recorded, nothing written)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("exists", [False, True])
def test_save_analysis_sql(monkeypatch, exists):
    import db.connection as dbc
    calls = []
    monkeypatch.setattr(dbc, "fetch_all", lambda sql, params=None: [{"1": 1}] if exists else [])
    monkeypatch.setattr(dbc, "execute", lambda sql, params=None: calls.append((sql, list(params))) or 1)
    vals = {"FPm": 42.5, "Stab_03": 81.0, "Stab_03_model": "rf", "AKnots": np.float64(12.0)}
    assert svc.save_analysis(77, vals, {"id": 5}) is True
    (sql, params), = calls
    ncols = len([c for c in svc.SAVE_COLUMNS.split(",") if c.strip()])
    if exists:
        assert sql.startswith("UPDATE tbllabordtyomat SET FPm=?")
        assert params[-1] == 77 and len(params) == ncols + 1
        values = params[:-1]
    else:
        assert sql.startswith("INSERT INTO tbllabordtyomat (TrialID, FPm")
        assert params[0] == 77 and len(params) == ncols + 1
        values = params[1:]
    assert values[0] == 42.5 and values[-2] == 5          # UserID
    assert values.count("rf") == 1


def test_save_analysis_db_error_returns_false(monkeypatch):
    import db.connection as dbc
    monkeypatch.setattr(dbc, "fetch_all", lambda sql, params=None: [])

    def boom(sql, params=None):
        raise RuntimeError("db down")
    monkeypatch.setattr(dbc, "execute", boom)
    assert svc.save_analysis(1, {}, {"id": 1}) is False


# ---------------------------------------------------------------------------
# Pure computations
# ---------------------------------------------------------------------------

def test_rolling_and_trend_helpers():
    assert svc.rolling_mean([1, 2, 3, 4], 2) == [1.0, 1.5, 2.5, 3.5]
    assert svc.roll_trend([0, 1, 2], [1, 2, 3], "Paare", 2) == ([1.0, 1.5, 2.5], "2 Paare")
    y, label = svc.roll_trend([0.0, 0.5, 1.0, 1.5], [1, 2, 3, 4], "Meter", 0.5)
    assert label == "0.5 m" and y == [1.0, 1.5, 2.5, 3.5]
    x = np.linspace(0, 10, 2001)
    m = svc.trend_metrics(list(x), list(5 * np.sin(2 * np.pi * x / 2.0) + 100))  # takes lists
    assert m["wavelength"] == pytest.approx(2.0, abs=0.02)
    assert m["peak_to_peak"] == pytest.approx(10.0, abs=0.1)


def test_process_wave_finds_synthetic_wave():
    x = np.arange(0, 60, 0.00025)
    y = 100 + 3 * np.sin(2 * np.pi * x / 1.5) + np.random.default_rng(3).normal(0, 1, x.size)
    wave = svc.analyze_process_wave(x, y, 0.05)
    assert wave["wavelength"] == pytest.approx(1.5, rel=0.05)
    assert wave["amplitude"] == pytest.approx(3.0, rel=0.1)
    assert svc.analyze_process_wave(x[:10], y[:10]) is None


def test_thresholds_and_classes():
    res = {"threshold": 100.0, "classes": {"thresholds": (30.0, 10.0)}}
    T, cb, ba = svc.thresholds(res)
    assert (T, cb, ba) == (100.0, 70.0, 90.0)
    assert svc.segment_class(60.0, cb, ba) == "A"
    assert svc.segment_class(80.0, cb, ba) == "B"
    assert svc.segment_class(95.0, cb, ba) == "C"
    assert svc.thresholds({"threshold": 1.0, "classes": {"thresholds": [1.0] * 19}})[1:] == (None, None)


def _synthetic_res():
    """Signal with knots (thin spots) every 10 mm, as analyze_series would mark them."""
    dx = 0.25
    n = 40_000  # 10 m
    y = np.full(n, 120.0)
    per_run = []
    for s in range(0, n - 20, 40):
        y[s:s + 12] = 80.0
        per_run.append((s, s + 12, 0, "A", 0.0))
    return {"_y_raw": y, "_dx_mm": dx, "threshold": 100.0,
            "classes": {"thresholds": (10.0, 30.0), "per_run": per_run}}


def test_views_on_synthetic_result():
    res = _synthetic_res()
    vals = {"AKnots": 50.0, "BKnots": 30.0, "CKnots": 20.0}
    view = svc.segment_view(res, vals, 1.0, 2.0, open_knot=("Meter", 1.0),
                            peak_valley=("Paare", 5), opening=("Meter", 0.5),
                            process_wave_bin=0.05, with_metrics=True)
    assert view["total_m"] == pytest.approx(10.0)
    assert view["start_idx"] == 4000 and view["end_idx"] == 12000
    assert len(view["knot_segments"]) == len(view["knot_classes"]) == sum(view["counts"].values())
    assert view["pie"] == {"A": 50.0, "B": 30.0, "C": 20.0}
    assert view["trends"]["opening"]["metrics"]["count"] > 0
    js = svc.segment_view_json(view, max_points=1000)
    assert len(js["line"]["x"]) <= 1000
    assert js["knot_segments"][0][3] in ("A", "B", "C")
    json.dumps(js)

    sig = svc.signal_view(res, 0.0, 3.0)
    ylim, xlim = svc.signal_limits(sig)
    assert xlim == (0.0, pytest.approx(3.0))
    assert ylim[0] < 80.0 < 120.0 < ylim[1]
    json.dumps(svc.signal_view_json(sig, 500))
    assert svc.signal_trace(res, 2.0, 2.5)["n_source"] == 2001

    geom = svc.garnspiegel_view(res, 0.5)
    assert geom["turns"] == svc.GARNSPIEGEL_TURNS
    assert geom["pts_per_row"] == 800
    assert any(r["knot_mask"].any() for r in geom["rows"])
    gj = svc.garnspiegel_json(geom)
    assert gj["x_step_mm"] == pytest.approx(0.25)
    assert sum(i1 - i0 for i0, i1, _c in gj["rows"][0]["spans"]) == 800
    json.dumps(gj)
    assert svc.segment_view({}, {}) is None and svc.signal_view({}) is None


def test_comparison_from_cache():
    a, b = _synthetic_res(), _synthetic_res()
    b["_y_raw"] = b["_y_raw"] + 3 * np.sin(2 * np.pi * np.arange(40_000) * 0.00025 / 1.2)
    cache = {1: (a, {}), 2: (b, {})}
    results, errors = svc.run_process_comparison(
        [{"trial_id": 1, "vno": 1}, {"trial_id": 2, "vno": 2}, {"trial_id": 3, "vno": 3, "tdms": "nope.tdms"}],
        0.05, cache)
    assert [r["label"] for r in results] == ["V001", "V002"]
    assert errors.startswith("V003: ")
    traces = svc.comparison_traces(results, show_drift=True, show_open_trend=True)
    assert {t["kind"] for t in traces} >= {"drift", "sine_fit"}
    assert len(svc.comparison_table_values(results[0])) == len(svc.COMPARE_TABLE_HEADERS) - 2
    json.dumps(svc.comparison_json(results, show_process_mean=True))


# ---------------------------------------------------------------------------
# Real TDMS file (skipped when the share is not reachable)
# ---------------------------------------------------------------------------

def _real_file():
    try:
        # 262/V1 is a short measurement (30 m); otherwise any file
        return svc.find_tdms(262, 1) or next(
            (f for f in svc.tdms_base().iterdir() if f.suffix.lower() == ".tdms"), None)
    except Exception:
        return None


def test_analyse_real_file():
    path = _real_file()
    if path is None:
        pytest.skip("TDMS folder not reachable")
    res = svc.analyse_signal_file(path)
    assert res["_dx_mm"] > 0 and len(res["_y_raw"]) > 0
    vals = svc.extract_basic_vals(res)
    assert vals["FPm"] is None or vals["FPm"] > 0
    summary = svc.result_json(res, vals)
    json.dumps(summary)
    assert summary["n_points"] == len(res["_y_raw"])
    json.dumps(svc.segment_view_json(svc.segment_view(res, vals, 0.0, 100.0)))
    json.dumps(svc.signal_trace(res))
