# tests/test_smart_dashboard_pdf.py
"""Dashboard-PDF: Logo da, kein Text ausserhalb von Seite und Karte."""
import base64
import io

import fitz
import pytest
from PIL import Image

from ui.smart_dashboard_pdf import (MARGIN, PAGE_H, PAGE_W, _compact_values, _hierarchy_rows, _list_rows, _page_title,
                                    image_size, write_pdf)


def _png(size):
    buf = io.BytesIO()
    Image.new("RGB", size, "#2F6DB5").save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


LONG = "A very long text without much sense, repeated many times so it must be cut or wrapped " * 6


def _visual(i, x, y, w, h, **kw):
    return {"id": f"v{i}", "x": x, "y": y, "w": w, "h": h, "wells": {}, **kw}


def _pages():
    months = [f"2026-{m:02d}" for m in range(1, 13)] + ["2025-01", "2025-02", "2025-05"]
    return [{"id": "p1", "title": "Page 1", "filters": [LONG], "visuals": [
        _visual(1, 0, 0, 2, 16, type="slicer", sel={"values": months + ["Other value " * 4] * 30},
                result={"kind": "slicer", "title": "Experiment year " * 5}),
        _visual(2, 2, 0, 5, 16, type="bar", result={"kind": "plotly", "title": LONG,
                "fair": {"level": "red", "headline": "Unfair", "text": LONG}}),
        _visual(3, 7, 0, 2, 6, type="kpi", result={"kind": "kpi", "value": "1234567890.123", "unit": "FP/m ≥ 5",
                                                   "sub": LONG, "title": "Card"}),
        _visual(4, 9, 0, 3, 16, type="x", result={"kind": "empty", "message": LONG, "title": "Empty"}),
        _visual(5, 0, 16, 12, 10, type="table", result={
            "kind": "table", "title": "Trials", "head": [LONG] * 6, "more": 3,
            "rows": [[n] + [LONG] * 6 for n in range(40)]}),
    ]}]


def test_text_stays_inside_page_and_logo_is_there(tmp_path):
    path = str(tmp_path / "d.pdf")
    write_pdf(path, LONG, _pages(), [LONG], {"p1:v2": _png(image_size({"w": 5, "h": 16}, 26))})
    doc = fitz.open(path)
    assert len(doc) == 1
    page = doc[0]
    assert len(page.get_images()) == 2                # logo + chart
    for b in page.get_text("blocks"):
        assert MARGIN - 1 <= b[0] and b[2] <= PAGE_W - MARGIN + 1, b[4][:40]
        assert 0 <= b[1] and b[3] <= PAGE_H, b[4][:40]
    # the cards reach the bottom of the page: no empty quarter
    assert max(d["rect"].y1 for d in page.get_drawings() if d["rect"].height > 20) > PAGE_H - MARGIN - 20


def _slicer_page(result, sel, h=12):
    return [{"id": "p1", "title": "P", "filters": [], "visuals": [
        _visual(1, 0, 0, 2, h, type="slicer", sel=sel, result={"kind": "slicer", "title": "S", "multi": True, **result})]}]


def _tree(*years):
    return [{"year": y, "n": 30, "months": [{"label": f"{y}-{m:02d}", "name": f"M{m}", "n": 3} for m in range(1, 13)]}
            for y in years]


@pytest.mark.parametrize("result,sel", [
    ({"style": "list", "options": [{"label": LONG[:60] + str(i), "n": i} for i in range(200)], "more": 7},
     {"values": [LONG[:60] + "150"]}),
    ({"style": "tiles", "options": [{"label": f"Value {i}", "n": i} for i in range(200)]}, {"values": ["Value 150"]}),
    ({"style": "dropdown", "options": []}, {"values": [LONG[:60] + str(i) for i in range(60)]}),
    ({"style": "between", "range": {"min": 0.5, "max": 123456.789, "step": 1}, "unit": "FP/m"}, {"min": 10, "max": 90}),
    ({"style": "hierarchy", "tree": _tree("2026", "2025", "2024", "2023"), "none": 4},
     {"values": [f"2026-{m:02d}" for m in range(1, 13)] + ["2025-03"]}),
])
@pytest.mark.parametrize("h", [4, 6, 12, 32])
def test_slicer_styles_stay_in_their_card(tmp_path, result, sel, h):
    path = str(tmp_path / "d.pdf")
    write_pdf(path, "T", _slicer_page(result, sel, h), [], {})
    page = fitz.open(path)[0]
    card = next(d["rect"] for d in page.get_drawings() if d["rect"].height > 15 and d["rect"].width < 200)
    words = [w for w in page.get_text("words") if card.y0 < w[1] < card.y1]
    assert words
    for w in words:
        assert w[2] <= card.x1 + 0.5 and w[3] <= card.y1 + 2, w[4]


def test_long_list_shows_selected_first_and_rest_as_more():
    rows = _list_rows({"options": [{"label": str(i), "n": 1} for i in range(50)], "more": 2}, ["40"], 5, True)
    assert rows[0]["text"] == "40" and rows[0]["state"] == "on"
    assert len(rows) == 5 and rows[-1] == {"more": 48}


def test_month_tree_ticks_like_the_dashboard():
    r = {"tree": _tree("2026", "2025"), "none": 0}
    rows = _hierarchy_rows(r, [f"2026-{m:02d}" for m in range(1, 13)] + ["2025-03"], 40)
    assert (rows[0]["text"], rows[0]["state"]) == ("2026", "on")
    assert (rows[13]["text"], rows[13]["state"]) == ("2025", "part")
    # short card: the complete year folds, the partly selected one stays open
    rows = _hierarchy_rows(r, [f"2026-{m:02d}" for m in range(1, 13)] + ["2025-03"], 15)
    assert rows[0]["fold"] == "shut" and rows[1]["fold"] == "open"


def test_page_title_and_month_text():
    assert _page_title("Report", {"title": "Page 1"}, 1) == "Report"
    assert _page_title("Report", {"title": "Page 1"}, 2) == "Report – Page 1"
    assert _compact_values([f"2026-{m:02d}" for m in range(1, 13)]) == "2026"
    assert _compact_values(["2026-01", "2026-02", "2026-03", "2026-06", "Unknown"]) == "2026: Jan–Mar, Jun, Unknown"


def test_text_visual_in_the_pdf(tmp_path):
    path = str(tmp_path / "t.pdf")
    v = {"id": "v1", "x": 0, "y": 0, "w": 3, "h": 6, "wells": {}, "type": "text",
         "result": {"kind": "text", "title": "", "text": "# Jets 2026\n" + LONG}}
    write_pdf(path, "T", [{"id": "p1", "title": "P", "filters": [], "visuals": [v]}], [], {})
    page = fitz.open(path)[0]
    words = page.get_text("words")
    assert any(w[4] == "Jets" for w in words) and not any("#" in w[4] for w in words)
    colw = (PAGE_W - 2 * MARGIN + 5) / 12
    assert all(w[2] <= MARGIN + 3 * colw for w in words if w[1] < PAGE_H - MARGIN - 20 and w[1] > 80)
