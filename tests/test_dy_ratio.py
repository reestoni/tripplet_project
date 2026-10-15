"""Computed D/Y ratio row (T2/T1) in Machine Data (ui/machine_tab.py)."""
import pytest

from ui import machine_tab as mt


@pytest.mark.parametrize("t1, t2, expected", [
    ("22.10", "14.80", "0.67"), ("20", "15", "0.75"), ("20,0", "15", "0.75"),
    ("", "15", ""), ("20", None, ""), ("0", "15", ""), ("abc", "15", ""),
])
def test_dy_ratio_text(t1, t2, expected):
    assert mt.dy_ratio_text(t1, t2) == expected


def _f(col, storage="tbltrialsettings"):
    return {"Title": col, "ColName": col, "StorageTable": storage, "LookupTable": None}


def test_ratio_row_inserted_after_t2():
    fm = [_f("Speed", "tbltrial"), _f("YarnTensionT1"), _f("YarnTensionT2"), _f("Comment2")]
    fv = [None] * 4
    mt._insert_dy_ratio_field(fm, fv)
    assert [f["Title"] for f in fm] == ["Speed", "YarnTensionT1", "YarnTensionT2",
                                        mt.DY_RATIO_TITLE, "Comment2"]
    assert len(fv) == 5


def test_no_ratio_row_without_t1_and_t2():
    fm = [_f("YarnTensionT2"), _f("YarnTensionBeforeJet", "tbltrial")]
    mt._insert_dy_ratio_field(fm, [None] * 2)
    assert mt.DY_RATIO_TITLE not in [f["Title"] for f in fm]


def test_ratio_value_rounds_half_up():
    from decimal import Decimal
    from db.dy_ratio import ratio_value
    assert ratio_value("40", "10.5") == Decimal("0.26")   # 0.2625 -> 0.26
    assert ratio_value("8", "1.0") == Decimal("0.13")     # 0.125 -> 0.13 (not banker's 0.12)
    assert ratio_value(None, "1") is None and ratio_value("0", "1") is None


def test_append_ratio_column():
    from decimal import Decimal
    from db.dy_ratio import append_ratio_column
    cmap = {"dyratio": "DYRatio", "yarntensiont1": "YarnTensionT1", "yarntensiont2": "YarnTensionT2"}
    cols, vals = ["TrialID", "YarnTensionT1", "YarnTensionT2"], [1, "20", "15"]
    append_ratio_column(cols, vals, cmap)
    assert cols[-1] == "DYRatio" and vals[-1] == Decimal("0.75")
    cols, vals = ["TrialID", "YarnTensionT1"], [1, "20"]
    append_ratio_column(cols, vals, cmap)
    assert cols == ["TrialID", "YarnTensionT1"]
    cols, vals = ["YarnTensionT1", "YarnTensionT2"], ["20", "15"]
    append_ratio_column(cols, vals, {})          # column missing (old offline snapshot)
    assert cols == ["YarnTensionT1", "YarnTensionT2"]
