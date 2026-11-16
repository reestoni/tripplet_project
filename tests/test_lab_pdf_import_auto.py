"""One PDF import for Statimat and Itemat (db/lab_pdf_import.detect_kind / import_auto), synthetic PDFs, no DB writes."""
import os

import pytest

from db import lab_pdf_import as lpi


def _pdf(path, text=None, image=False):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(path), pagesize=A4)
    if text:
        c.drawString(72, 760, text)
    if image:                                  # a "scan": only graphics, no text layer
        c.rect(72, 400, 300, 200, fill=1)
    c.showPage()
    c.save()
    return str(path)


def test_detect_kind(tmp_path):
    stat = _pdf(tmp_path / "s.pdf", "STATIMAT DS  Heberlein Technology AG  Seite 1")
    scan = _pdf(tmp_path / "i.pdf", image=True)
    enka = _pdf(tmp_path / "e.pdf", "Enka tecnica Gesamt-Auswertung")
    other = _pdf(tmp_path / "o.pdf", "Machine drawing P142-2 rev B")
    assert lpi.detect_kind(stat) == lpi.KIND_STATIMAT
    assert lpi.detect_kind(scan) == lpi.KIND_ITEMAT
    assert lpi.detect_kind(enka) == lpi.KIND_ITEMAT
    assert lpi.detect_kind(other) is None
    assert lpi.detect_kind(str(tmp_path / "missing.pdf")) is None
    # a scanned Statimat report (no text): the original file name decides, not the Itemat OCR
    assert lpi.detect_kind(scan, name="Statimat DS V11 bis V20.pdf") == lpi.KIND_STATIMAT
    assert lpi.detect_kind(scan, name="Itemat Lab V1-V24.pdf") == lpi.KIND_ITEMAT


def test_import_auto_routes_by_kind(tmp_path, monkeypatch):
    calls = {}
    monkeypatch.setattr(lpi, "import_statimat", lambda sid, paths, user, **k: calls.setdefault("s", paths) and
                        {"imported": 3, "skipped": [], "errors": []})
    monkeypatch.setattr(lpi, "import_itemat", lambda sid, paths, user, **k: calls.setdefault("i", paths) and
                        {"imported": 2, "skipped": ["x"], "errors": []})
    monkeypatch.setattr(lpi, "itemat_columns", lambda: {"ok": 1})
    kinds = {"a.pdf": "statimat", "b.pdf": "itemat", "c.pdf": None, "d.pdf": "statimat"}
    res = lpi.import_auto(1, list(kinds), None, kinds=kinds)
    assert calls == {"s": ["a.pdf", "d.pdf"], "i": ["b.pdf"]}
    assert res["statimat"]["imported"] == 3 and res["itemat"]["imported"] == 2 and res["unknown"] == ["c.pdf"]
    assert "Statimat (2 PDF)" in res["message"] and "Itemat (1 PDF)" in res["message"] and "c.pdf" in res["message"]
    # only unknown files -> nothing imported
    res = lpi.import_auto(1, ["z.pdf"], None, kinds={"z.pdf": None})
    assert res["statimat"] is None and res["itemat"] is None and res["unknown"] == ["z.pdf"]
