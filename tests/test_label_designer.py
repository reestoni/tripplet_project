"""ui/label_designer.py - Label Generator without Qt (2026-11-13, shared with the web). Reads dev_local only."""
import subprocess
import sys

import pytest

from ui import label_designer as ld


def test_qt_free():
    code = "import sys, ui.label_designer; sys.exit(any(m.startswith('PySide6') for m in sys.modules))"
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0


def test_elements_and_text():
    t = ld.new_element("table", 0)
    assert t["rows"] == 2 and len(t["cells"]) == 2 and len(t["cells"][0]) == 2
    t["rows"], t["cols"] = 3, 1
    t["cells"][0][0]["parts"][0]["text"] = "keep"
    ld.resize_table_cells(t)
    assert len(t["cells"]) == 3 and t["cells"][0][0]["parts"][0]["text"] == "keep"
    assert ld.new_element("logo", 2)["x_mm"] == 8.0
    old = ld.normalize_element({"type": "text", "source": "field", "field_key": "trial_nr"})
    assert old["parts"] == [{"source": "field", "field_key": "trial_nr"}]
    parts = [{"source": "static", "text": "V"}, {"source": "field", "field_key": "trial_nr"},
             {"source": "counter", "start": 5, "step": 2, "digits": 3}]
    assert ld.resolve_text(parts, {"trial_nr": "7", "__label_index__": 2}) == "V7009"
    assert ld.caption_text({"type": "text", "parts": parts}) == "V{trial_nr}{#5}"


def test_preview_and_items():
    els = [ld.new_element("text", 0, {"type": "text", "parts": [{"source": "static", "text": "Hello"}]}),
           ld.new_element("table", 1), ld.new_element("logo", 2)]
    png = ld.preview_png(els, 60, 30, ld.preview_item(None, {"trial_nr": "Trial Number"}))
    assert png[:4] == b"\x89PNG"
    assert ld.build_items([], "copies", 1, None, None) == ([], "no_elements")
    assert ld.build_items(els, "range", 1, None, None)[1] == "no_series"
    items, err = ld.build_items(els, "copies", 3, None, None)
    assert err is None and [i["__label_index__"] for i in items] == [0, 1, 2]
    with_field = [ld.new_element("text", 0, {"type": "text", "parts": [{"source": "field", "field_key": "trial_nr"}]})]
    assert ld.build_items(with_field, "copies", 1, None, None)[1] == "need_trial"


def test_series_context_on_dev_local():
    from db.connection import fetch_all
    rows = fetch_all("SELECT TrialSeriesID FROM tbltrial GROUP BY TrialSeriesID HAVING COUNT(*) > 2 LIMIT 1")
    if not rows:
        pytest.skip("no series")
    ctx = ld.series_context(int(rows[0]["TrialSeriesID"]))
    assert ctx["header"] and ctx["trials"] and "trial_nr" in ctx["fields"]
    items, err = ld.build_items([ld.new_element("text", 0)], "range", 1, ctx, None, ctx["trials"][0], ctx["trials"][1])
    assert err is None and len(items) == 2 and items[0]["trial_nr"] == str(ctx["trials"][0])
    assert ld.series_context(999999999)["header"] is None
