"""db/series_tables.py - the lab tabs of Show Experiment without Qt (shared with tripplet_web).

The cell-by-cell comparison against the desktop models (all roles, recompute on save,
Jet Air in both units) ran on dev_local. Here: Qt-free import, the builders on fake
rows, the shared rules, and - only if the local dev_local database answers - the shape
of real series for every tab."""
import json
import os
import subprocess
import sys

import pytest

from db import series_tables as stb

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _run(code: str, mode: str = "dev_local") -> subprocess.CompletedProcess:
    env = dict(os.environ, TRIPPLET_MODE=mode)
    env.pop("QT_QPA_PLATFORM", None)
    return subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=180)


def _trials(*ids):
    rows = [{"ID": i, "Versuchsnummer": n} for n, i in enumerate(ids, start=1)]
    return stb.SeriesTrials(series_id=7, trials=rows, trial_ids=list(ids), trial_vnos=[r["Versuchsnummer"] for r in rows],
                            reference_names={}, labels=[f"V{r['Versuchsnummer']}" for r in rows])


@pytest.fixture
def fake_db(monkeypatch):
    """fetch_all answers from a list of (sql fragment, rows); every table exists."""
    answers = []
    monkeypatch.setattr(stb, "table_exists", lambda name: True)

    def _fetch(sql, params=None):
        for frag, rows in answers:
            if frag in sql:
                return rows
        return []
    monkeypatch.setattr(stb, "fetch_all", _fetch)
    return answers


def test_imports_without_pyside6():
    r = _run("import sys; import db.series_tables as s; s.build_jet_air; s.build_itemat; "
             "print('PySide6' in sys.modules)")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "False"


def test_lab_tabs_in_desktop_order_with_retest_sources():
    assert [t.key for t in stb.LAB_TABS] == [
        "titer", "stat", "stat_ds", "water", "ekb", "hot_air_shrinkage", "hot_water_shrinkage",
        "aty_shrinkage", "rapid600", "itemat", "itemat_plus", "dtyomat", "atyomat"]
    by_key = {t.key: t for t in stb.LAB_TABS}
    assert (by_key["itemat"].title, by_key["itemat"].lab_source) == ("Itemat Lab", "ItematLab")
    assert (by_key["itemat_plus"].title, by_key["itemat_plus"].lab_source) == ("Itemat Plus", "ItematPlus")
    assert (by_key["dtyomat"].title, by_key["dtyomat"].lab_source) == ("DTYoMat", "DTYoMat")
    assert (by_key["atyomat"].title, by_key["atyomat"].lab_source) == ("ATYoMat", "ATYoMat")
    assert stb.JET_AIR_TAB_INDEX == 1 and stb.JET_AIR_TITLE == "Jet Air Consumption"
    # every lab source has a dispatch entry in the desktop retest refresh
    src = open(os.path.join(ROOT, "ui", "screen_show_experiment.py"), encoding="utf-8").read()
    for t in stb.LAB_TABS:
        assert f'"{t.lab_source}": lambda' in src, t.lab_source


def test_itemat_rows_by_tension(fake_db):
    fake_db.append(("tblLaborItematLab", [
        {"RecID": 1, "TrialID": 10, "Tension": 0, "IP": 40, "IPCV": 12, "Stability": None},
        {"RecID": 2, "TrialID": 10, "Tension": "0,3", "IP": None, "IPCV": None, "Stability": 80},
        {"RecID": 3, "TrialID": 12, "Tension": 1.0, "IP": None, "IPCV": None, "Stability": 50},
    ]))
    p = stb.build_itemat(_trials(10, 11, 12))
    assert p.key == "itemat" and p.extra["tensions"] == [0.3, 1.0]
    assert p.row_titles[2:] == ["Stability@0.3 cN/dtex", "Stability@1.0 cN/dtex"]
    assert len(p.cells) == len(p.row_titles) == len(p.validators) and {len(r) for r in p.cells} == {3}
    v, b = p.cells[0][0]
    assert v == 40 and (b.table, b.id_value, b.field) == ("tblLaborItematLab", 1, "Intermingling Points (FP/m)")
    assert p.cells[stb.ITEMAT_ROW_STAB_START][0][0] == 80
    assert p.cells[0][1] == (None, None) and p.cells[0][2] == (None, None)   # no record at tension 0
    assert p.cells[3][2][1].field == "Stability (%)"
    assert p.col_titles is None


def test_itemat_plus_rows(fake_db):
    fake_db.append(("tblLaborItematPlus", [
        {"RecID": 5, "TrialID": 10, "Tension": 0.0, "InterP": 30, "OLX": 1, "OLS": 2, "KLX": 3, "KLS": 4,
         "Stability": None},
        {"RecID": 6, "TrialID": 10, "Tension": 0.6, "InterP": None, "OLX": None, "OLS": None, "KLX": None,
         "KLS": None, "Stability": 70},
    ]))
    p = stb.build_itemat_plus(_trials(10, 11))
    assert p.key == "itemat_plus" and p.extra["tensions"] == [0.6]
    assert len(p.row_titles) == stb.ITEMAT_PLUS_ROW_STAB_START + 1
    assert [p.cells[r][0][0] for r in range(5)] == [30, 1, 2, 3, 4]
    assert p.cells[stb.ITEMAT_PLUS_ROW_KLS0][0][1].field == "KL S (mm)"
    assert p.cells[5][0][0] == 70 and p.cells[5][1] == (None, None)


def test_itemat_save_rules():
    assert stb.itemat_ip_at_tension(40.0, 80.0) == 40.0 * (80.0 / 100.0)
    assert stb.itemat_plus_cv0(1.0, 2.0, 3.0, 4.0) == pytest.approx((4 ** 2 + 2 ** 2) ** 0.5 / 4.0 * 100)
    assert stb.itemat_plus_cv0(None, 2.0, 3.0, 4.0) is None
    assert stb.itemat_plus_cv0(0.0, 2.0, 0.0, 4.0) is None


def test_dtyomat_first_record_per_trial(fake_db):
    rec = {"RecID": 3, "TrialID": 11, "FPm": 55, "CV_FP": 9, "AvgFP": 1, "StdDevFP": 1, "CV_KL": 1, "AvgKL": 1,
           "StdDevKL": 1, "CV_OL": 1, "AvgOL": 1, "StdDevOL": 1, "AKnots": 1, "BKnots": 1, "CKnots": 7}
    fake_db.append(("tblLaborDTYoMat", [rec, dict(rec, RecID=4, FPm=99)]))
    p = stb.build_dtyomat(_trials(10, 11))
    assert len(p.row_titles) == 13 and {len(r) for r in p.cells} == {2}
    assert p.cells[0][1][0] == 55 and p.cells[0][1][1].field == "FP/m" and p.cells[0][1][1].id_value == 3
    assert p.cells[12][1][0] == 7 and p.cells[0][0] == (None, None)


def test_atyomat_rows_match_db_column_map(fake_db):
    from ui.yarnscope.aty_core_analysis import DB_COLUMN_MAP
    cols = [c for k, c in DB_COLUMN_MAP.items() if k != "params_version"]
    fake_db.append(("tblLaborATYoMat", [dict({c: i for i, c in enumerate(cols)}, RecID=8, TrialID=10)]))
    p = stb.build_atyomat(_trials(10))
    assert len(p.row_titles) == len(cols) and [b.field for _v, b in (r[0] for r in p.cells)] == cols


def test_no_rows_no_tab(fake_db):
    st = _trials(10)
    for t in stb.LAB_TABS[-4:]:
        assert t.build(st) is None
    assert stb.build_itemat(_trials()) is None
    assert stb.build_jet_air(7) is None and stb.build_jet_air(None) is None


def test_jet_air_shape_and_units(fake_db):
    fake_db.append(("tblDTYJets", [{"ID": 2, "JName": "B-Jet"}, {"ID": 1, "JName": "A-Jet"}]))
    fake_db.append(("tblLaborJetAirConsumption", [
        {"ID": 1, "JetID": 2, "JetPlate": None, "AirPressure": 3.0, "AirConsumption": 1.5,
         "AtmosphericPressure": 960, "AirTemperature": 21},
        {"ID": 2, "JetID": 1, "JetPlate": "4", "AirPressure": 2.5, "AirConsumption": None,
         "AtmosphericPressure": None, "AirTemperature": None},
        {"ID": 3, "JetID": 1, "JetPlate": "4", "AirPressure": 3.0, "AirConsumption": 2,
         "AtmosphericPressure": None, "AirTemperature": None},
    ]))
    ja = stb.build_jet_air(7)
    assert ja.jets == [(1, "4"), (2, "")] and ja.pressures == [2.5, 3.0] and ja.unit == "Nm3h"
    for p in (ja.consumption, ja.atm, ja.temp):
        assert p.row_titles == ["A-Jet / Plate 4", "B-Jet"] and p.col_titles == ["2.5 bar", "3 bar"]
        assert {len(r) for r in p.cells} == {2} and len(p.cells) == 2
    assert ja.consumption.cells[0][1][0] == "2.00" and ja.consumption.cells[1][0] == (None, None)
    assert ja.consumption.cells[0][0][1].field == "AirConsumption"     # bound even when empty
    assert ja.atm.cells[1][1][0] == 960 and ja.temp.cells[1][1][1].field == "AirTemperature"
    assert "unit_scale" not in ja.consumption.extra
    lm = stb.build_jet_air(7, "lmin")
    assert lm.unit == "lmin" and lm.consumption.cells[1][1][0] == f"{1.5 * stb.LMIN_PER_NM3H:.2f}"
    assert lm.consumption.extra == {"unit_scale": stb.LMIN_PER_NM3H, "unit_field": "AirConsumption"}
    assert lm.atm.cells == ja.atm.cells


_REAL = r"""
import json, sys
from db.connection import fetch_all
from db import series_tables as stb
TABLES = {"itemat": "tblLaborItematLab", "itemat_plus": "tblLaborItematPlus",
          "dtyomat": "tblLaborDTYoMat", "atyomat": "tblLaborATYoMat"}
out = {}
for key, table in TABLES.items():
    sids = [r["S"] for r in fetch_all(f"SELECT DISTINCT T.TrialSeriesID AS S FROM {table} L "
                                      f"JOIN tblTrial T ON T.ID = L.TrialID ORDER BY S DESC LIMIT 2")]
    tab = next(t for t in stb.LAB_TABS if t.key == key)
    res = []
    for sid in sids:
        st = stb.load_trials(sid)
        p = tab.build(st)
        res.append(None if p is None else {
            "rows": len(p.row_titles), "val": len(p.validators), "cells_rows": len(p.cells),
            "cells_cols": sorted({len(r) for r in p.cells}), "trials": len(st.trials),
            "filled": sum(1 for r in p.cells for v, b in r if b is not None),
            "tensions": p.extra.get("tensions")})
    out[key] = res
ja_out = []
for r in fetch_all("SELECT DISTINCT TrialSeriesID AS S FROM tblLaborJetAirConsumption ORDER BY S DESC LIMIT 2"):
    ja = stb.build_jet_air(r["S"], "lmin")
    ja_out.append(None if ja is None else [
        [len(p.row_titles), len(p.col_titles), len(p.cells), sorted({len(x) for x in p.cells})]
        for p in (ja.consumption, ja.atm, ja.temp)] + [[len(ja.jets), len(ja.pressures)]])
out["jet_air"] = ja_out
print("PYSIDE", "PySide6" in sys.modules)
print(json.dumps(out))
"""


def test_real_series_every_tab():
    r = _run(_REAL)
    if r.returncode != 0:
        pytest.skip("dev_local not reachable: " + (r.stderr.strip().splitlines() or ["?"])[-1])
    lines = r.stdout.strip().splitlines()
    assert lines[0] == "PYSIDE False"
    out = json.loads(lines[-1])
    for key in ("itemat", "itemat_plus", "dtyomat", "atyomat"):
        for d in out[key]:
            assert d is not None and d["filled"] > 0
            assert d["rows"] == d["val"] == d["cells_rows"] and d["cells_cols"] == [d["trials"]]
            if key.startswith("itemat"):
                start = stb.ITEMAT_ROW_STAB_START if key == "itemat" else stb.ITEMAT_PLUS_ROW_STAB_START
                assert d["rows"] == start + len(d["tensions"])
    for ja in out["jet_air"]:
        assert ja is not None
        n_jets, n_p = ja[-1]
        for rows, cols, cells_rows, cells_cols in ja[:-1]:
            assert (rows, cols, cells_rows, cells_cols) == (n_jets, n_p, n_jets, [n_p])
