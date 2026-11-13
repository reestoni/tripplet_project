"""db/machine_data.py - Machine Data of Show Experiment without Qt (shared with tripplet_web).

The cell-by-cell comparison against the desktop model ran on dev_local (14 series,
all three view modes). Here: Qt-free import, the pure rules, and - only if the local
dev_local database answers - the structure of a real series in all view modes."""
import json
import os
import subprocess
import sys

import pytest

from db import machine_data as md

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _run(code: str, mode: str = "dev_local") -> subprocess.CompletedProcess:
    env = dict(os.environ, TRIPPLET_MODE=mode)
    env.pop("QT_QPA_PLATFORM", None)
    return subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=120)


def test_imports_without_pyside6():
    r = _run("import sys; import db.machine_data, db.yarn_colours; "
             "print('PySide6' in sys.modules)")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "False"


def test_hidden_columns_compact_keeps_first_ply_of_each_trial():
    specs = [{"trial_id": 1, "ply": "Ply 1"}, {"trial_id": 1, "ply": "Ply 2"},
             {"trial_id": 2, "ply": "Ply 1"}]
    assert md.hidden_columns(specs, compact=True, groups=False) == [False, True, False]
    assert md.hidden_columns(specs, compact=False, groups=False) == [False, False, False]
    assert md.hidden_columns(specs, compact=False, groups=False, checked_labels={"Ply 1"}) == [False, True, False]


def test_column_label_groups_uses_yarn_use_name():
    cs = {"ply": "Core", "yarn_use_name": "Core"}
    assert md.column_label(cs, True) == "Core"
    assert md.column_label({"ply": "Ply 2"}, False) == "Ply 2"


def test_plies_per_trial_counts_group_members():
    specs = [{"trial_id": 1, "sr": {"ID": 1}}, {"trial_id": 1, "sr": {"ID": 2}},
             {"trial_id": 2, "sr": None},
             {"trial_id": 3, "is_group": True, "sr": {"ID": 5}, "sr_all": [{"ID": 5}, {"ID": 6}]}]
    assert md.plies_per_trial(specs) == {1: 2, 2: 0, 3: 2}


def test_single_ply_merge_cells_skip_filled_and_multi_ply():
    keys = ["housing", "dtyrouteid", "mergeintoply"]
    specs = [{"trial_id": 1}, {"trial_id": 2}, {"trial_id": 2}]
    values = {(1, 0): "3"}
    cells = md.single_ply_merge_cells(keys, specs, {1: 1, 2: 2}, lambda r, c: values.get((r, c), ""))
    assert cells == [(2, 0)]


def test_id_display_and_colour_css():
    m = {1: "A", "2": "B"}
    assert md.id_display(m, "1") == "A" and md.id_display(m, 2) == "B"
    assert md.id_display(m, "") == "" and md.id_display(m, "9") == "9"
    assert md.colour_css("Raw White") == "#F3EAD3"
    assert md.colour_css("Navy Blue") == "navyblue"
    assert md.colour_css("") is None


def test_dy_ratio_field_after_t2():
    fm = [{"Title": "T1", "ColName": "YarnTensionT1", "StorageTable": "tbltrialsettings"},
          {"Title": "T2", "ColName": "YarnTensionT2", "StorageTable": "tbltrialsettings"}]
    fv = [None, None]
    md.insert_dy_ratio_field(fm, fv)
    assert fm[2]["Title"] == md.DY_RATIO_TITLE and fm[2]["StorageTable"] == md.DY_RATIO_STORAGE


_REAL = r"""
import json, sys
from db.connection import fetch_all
from db import series_tables as stb, machine_data as md
rows = fetch_all("SELECT T.TrialSeriesID AS S FROM tblTrial T JOIN tblTrialSettings TS ON TS.TrialID = T.ID "
                 "GROUP BY T.TrialSeriesID HAVING COUNT(*) > COUNT(DISTINCT T.ID) ORDER BY S DESC LIMIT 1")
st = stb.load_trials(rows[0]["S"])
cache = md.load_machine_cache(st.series_id, st.trial_ids)
out = {}
for mode in md.VIEW_MODES:
    d = md.build_machine_data(st, mode, cache)
    out[mode] = {
        "message": d.message, "rows": len(d.row_titles), "keys": len(d.row_keys), "val": len(d.validators),
        "cells_rows": len(d.cells), "cells_cols": sorted({len(r) for r in d.cells}), "cols": len(d.col_specs),
        "columns": len(d.columns), "hdr": [len(h["values"]) for h in d.header_rows],
        "span_cols": sum(n for _f, n in d.trial_spans), "trials": len(st.trial_ids),
        "spans": len(d.trial_spans), "cg": d.custom_group_row, "fixed": d.titles_fixed,
        "dd_ok": all(0 <= r < len(d.row_titles) for r in d.dropdown_lists),
        "json": len(json.dumps(d.columns, default=str)) > 0,
        "text": md.display_text(d, 1, 0) if d.cells and d.cells[0] else "",
    }
print("PYSIDE", "PySide6" in sys.modules)
print(json.dumps(out))
"""


def test_real_series_all_view_modes():
    r = _run(_REAL)
    if r.returncode != 0:
        pytest.skip("dev_local not reachable: " + (r.stderr.strip().splitlines() or ["?"])[-1])
    lines = r.stdout.strip().splitlines()
    assert lines[0] == "PYSIDE False"
    out = json.loads(lines[-1])
    for mode, d in out.items():
        assert d["message"] is None
        assert d["rows"] == d["keys"] == d["val"] == d["cells_rows"]
        assert d["cells_cols"] == [d["cols"]] and d["columns"] == d["cols"]
        assert d["hdr"] == [d["cols"] + 1, d["cols"] + 1]
        assert d["span_cols"] == d["cols"] and d["spans"] == d["trials"]
        assert d["cg"] == d["rows"] - 1 and d["dd_ok"] and d["json"]
    # a series with several plies: one column per ply, fewer per yarn use group
    assert out["single"]["cols"] > out["single"]["trials"]
    assert out["compact"]["cols"] == out["single"]["cols"]
    assert out["groups"]["cols"] <= out["single"]["cols"]
    assert out["single"]["fixed"][-2:] == ["Yarn Use", "Spool"]
    assert out["compact"]["fixed"][-1] == "Plies" == out["groups"]["fixed"][-1]
