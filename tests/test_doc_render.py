"""ui/doc_render.py (files as images, Qt-free since 2026-11-13) and db/image_compare.py."""
import os
import struct
import subprocess
import sys

import pytest

from ui import doc_render as dr


def test_qt_free():
    code = "import sys, ui.doc_render, db.image_compare; sys.exit(any(m.startswith('PySide6') for m in sys.modules))"
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0


def test_image_pdf_excel(tmp_path):
    from PIL import Image
    png = tmp_path / "a.png"
    Image.new("RGB", (30, 20), (255, 0, 0)).save(png)
    img, err = dr.render(str(png))
    assert err is None and img.size == (30, 20) and dr.info(str(png)) == {"kind": "image"}
    from reportlab.pdfgen import canvas
    pdf = tmp_path / "a.pdf"
    c = canvas.Canvas(str(pdf))
    c.drawString(100, 700, "x")
    c.showPage()
    c.drawString(100, 700, "y")
    c.save()
    assert dr.info(str(pdf)) == {"kind": "pdf", "pages": 2}
    img, err = dr.render(str(pdf), pdf_page=1)
    assert err is None and img.size[0] > 1000
    assert dr.render(str(pdf), pdf_page=5)[0] is None
    from openpyxl import Workbook
    xl = tmp_path / "a.xlsx"
    wb = Workbook()
    wb.active.append(["h1", "h2"])
    wb.active.append([1, 2.5])
    wb.save(xl)
    assert dr.info(str(xl))["sheets"] == ["Sheet"]
    rows, name = dr.xlsx_read_rows(str(xl))
    assert rows[1] == ["1", "2.5"] and name == "Sheet"      # (inline strings stay empty, as before)
    img, err = dr.render(str(xl), title="shown.xlsx")
    assert err is None and img.size[1] > 40
    assert dr.to_png(img)[:4] == b"\x89PNG"


def test_vk4_light_channel(tmp_path):
    # minimal VK4: header, offsets (index 3 = light intensity), an 8-bit 2x2 block
    import numpy as np  # noqa: F401
    data = bytearray(b"VK4_" + b"\0" * 8)
    offsets = [0] * 12
    offsets[3] = 60
    data += struct.pack("<12I", *offsets)
    data += struct.pack("<5I", 2, 2, 8, 0, 0) + bytes([0, 85, 170, 255])
    f = tmp_path / "a.vk4"
    f.write_bytes(bytes(data))
    assert dr.vk4_channels(str(f)) == [dr.VK4_CH_LIGHT_INT]
    img = dr.vk4_image(str(f))
    assert img.size == (2, 2) and img.getpixel((1, 1)) == (255, 255, 255)
    assert dr.info(str(f))["channels"][0]["key"] == dr.VK4_CH_LIGHT_INT


def test_db_helpers():
    from db import image_compare as ic
    assert ic.build_full_path({"RelativePath": "a", "StoredFilename": "b.png"}) == os.path.join("a", "b.png")
    assert ic.build_full_path({"_local": True, "FullPath": "c:/x.png"}) == "c:/x.png"
    assert ic.fetch_aty_radar_for_image({"_local": True}) is None
