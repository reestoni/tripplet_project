"""doc_render.py - files as images, without Qt (2026-11-13, moved out of ui/screen_image_compare.py for the
web version; Image Compare uses it, Canvas has the same helpers).

Keyence VK4 (height / colour / intensity channels, numpy parser), PDF pages (pymupdf), Excel sheets (ZIP/XML
reader + PIL renderer, .xls via pandas/xlrd), Word pages (docx2pdf, else mammoth + pymupdf), ordinary images.
Everything returns PIL images; `render()` picks by file type and `info()` says pages / sheets / channels.
"""
from __future__ import annotations

import io
import os
from typing import Any, Dict, List, Optional, Tuple

VK4_CH_HEIGHT_PEAK = "height_peak"
VK4_CH_HEIGHT_LIGHT = "height_light"
VK4_CH_COLOR_PEAK = "color_peak"
VK4_CH_COLOR_LIGHT = "color_light"
VK4_CH_LIGHT_INT = "light_int"

VK4_CH_LABELS = {
    VK4_CH_HEIGHT_PEAK: "Height (laser)",
    VK4_CH_HEIGHT_LIGHT: "Height (light)",
    VK4_CH_COLOR_PEAK: "Laser (Farbe)",
    VK4_CH_COLOR_LIGHT: "Licht (Farbe)",
    VK4_CH_LIGHT_INT: "Intensity (grey)",
}
VK4_CH_ORDER = [VK4_CH_HEIGHT_PEAK, VK4_CH_HEIGHT_LIGHT, VK4_CH_COLOR_PEAK, VK4_CH_COLOR_LIGHT, VK4_CH_LIGHT_INT]
_VK4_IDX = {VK4_CH_HEIGHT_PEAK: 4, VK4_CH_HEIGHT_LIGHT: 5, VK4_CH_COLOR_PEAK: 1, VK4_CH_COLOR_LIGHT: 2,
            VK4_CH_LIGHT_INT: 3}
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tif", ".tiff")
DOC_MAX = 2400          # documents are limited to this many pixels (images keep their full size)


def is_vk4(path: str) -> bool:
    return path.lower().endswith(".vk4")


def is_pdf(path: str) -> bool:
    return path.lower().endswith(".pdf")


def is_excel(path: str) -> bool:
    return path.lower().endswith((".xlsx", ".xlsm", ".xls"))


def is_word(path: str) -> bool:
    return path.lower().endswith((".docx", ".doc"))


def is_image(path: str) -> bool:
    return path.lower().endswith(IMAGE_EXT)


def supported(path: str) -> bool:
    return is_image(path) or is_vk4(path) or is_pdf(path) or is_excel(path) or is_word(path)


# ── VK4 ─────────────────────────────────────────────────────────────────
def vk4_channels(path: str) -> List[str]:
    import struct
    try:
        with open(path, "rb") as f:
            if f.read(4) != b"VK4_":
                return []
            f.seek(12)
            offsets = struct.unpack("<12I", f.read(48))
        return [ch for ch in VK4_CH_ORDER if offsets[_VK4_IDX[ch]] != 0]
    except Exception:
        return []


def vk4_image(path: str, channel: str = ""):
    """One VK4 channel as RGB image (height = jet colour map 1–99 %); "" = the first channel there is."""
    if not channel:
        for ch in vk4_channels(path):
            img = vk4_image(path, ch)
            if img is not None:
                return img
        return None
    import struct
    import numpy as np
    from PIL import Image

    def _jet(arr):
        r = np.clip(1.5 - np.abs(arr * 4.0 - 3.0), 0, 1)
        g = np.clip(1.5 - np.abs(arr * 4.0 - 2.0), 0, 1)
        b = np.clip(1.5 - np.abs(arr * 4.0 - 1.0), 0, 1)
        return np.stack([(r * 255).astype(np.uint8), (g * 255).astype(np.uint8), (b * 255).astype(np.uint8)], axis=-1)
    try:
        with open(path, "rb") as f:
            if f.read(4) != b"VK4_":
                return None
            f.seek(12)
            offsets = struct.unpack("<12I", f.read(48))
            idx = _VK4_IDX.get(channel)
            if idx is None:
                return None
            off = offsets[idx]
            if off == 0:
                return None
            f.seek(off)
            blk = f.read(20)
            w = struct.unpack_from("<I", blk, 0)[0]
            h = struct.unpack_from("<I", blk, 4)[0]
            bpp = struct.unpack_from("<I", blk, 8)[0]
            if w == 0 or h == 0:
                return None
            if channel in (VK4_CH_HEIGHT_PEAK, VK4_CH_HEIGHT_LIGHT):
                if bpp not in (16, 32):
                    return None
                raw = f.read(w * h * (bpp // 8))
                if len(raw) < w * h * (bpp // 8):
                    return None
                dtype = "<u2" if bpp == 16 else "<u4"
                arr = np.frombuffer(raw, dtype=dtype).reshape((h, w)).astype(np.float32)
                invalid = arr == (0xFFFF if bpp == 16 else 0xFFFFFFFF)
                valid = arr[~invalid]
                if valid.size == 0:
                    return None
                lo = float(np.percentile(valid, 1))
                hi = float(np.percentile(valid, 99))
                if hi <= lo:
                    hi = lo + 1.0
                norm = np.clip((arr - lo) / (hi - lo), 0.0, 1.0)
                norm[invalid] = 0.0
                rgb = _jet(norm)
                rgb[invalid] = 0
                return Image.fromarray(rgb, "RGB")
            if channel in (VK4_CH_COLOR_PEAK, VK4_CH_COLOR_LIGHT):
                if bpp != 24:
                    return None
                raw = f.read(w * h * 3)
                if len(raw) < w * h * 3:
                    return None
                arr = np.frombuffer(raw, dtype=np.uint8).reshape((h, w, 3))
                return Image.fromarray(arr[:, :, ::-1].copy(), "RGB")
            if channel == VK4_CH_LIGHT_INT:
                if bpp not in (8, 16):
                    return None
                dtype = np.uint8 if bpp == 8 else "<u2"
                raw = f.read(w * h * (bpp // 8))
                if len(raw) < w * h * (bpp // 8):
                    return None
                arr = np.frombuffer(raw, dtype=dtype).reshape((h, w)).astype(np.float32)
                norm = (arr - arr.min()) / max(arr.max() - arr.min(), 1)
                g8 = (norm * 255).astype(np.uint8)
                return Image.fromarray(np.stack([g8, g8, g8], axis=-1), "RGB")
            return None
    except Exception:
        return None


# ── PDF ─────────────────────────────────────────────────────────────────
def pdf_page_count(path: str) -> int:
    try:
        import fitz
        doc = fitz.open(path)
        n = len(doc)
        doc.close()
        return n
    except Exception:
        try:
            from pypdf import PdfReader
            return len(PdfReader(path).pages)
        except Exception:
            return 1


def pdf_image(path: str, page: int = 0) -> Tuple[Any, Optional[str]]:
    """(PIL image, None) or (None, error) of one PDF page at 150 dpi."""
    try:
        import fitz
        from PIL import Image
        doc = fitz.open(path)
        if page >= len(doc):
            return None, "Page %d does not exist." % page
        pix = doc[page].get_pixmap(matrix=fitz.Matrix(150 / 72, 150 / 72), alpha=False)
        doc.close()
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples), None
    except ImportError:
        return None, "pymupdf is not installed. Please run: pip install pymupdf"
    except Exception as e:
        return None, str(e)


# ── Excel ───────────────────────────────────────────────────────────────
_XLSX_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_XLSX_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_XLSX_OFF_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def excel_sheet_names(path: str) -> List[str]:
    if path.lower().endswith(".xls"):
        try:
            import pandas as pd
            return pd.ExcelFile(path, engine="xlrd").sheet_names
        except Exception:
            return ["Sheet1"]
    try:
        import zipfile
        import xml.etree.ElementTree as ET
        with zipfile.ZipFile(path) as z:
            with z.open("xl/workbook.xml") as f:
                tree = ET.parse(f)
        sheets = tree.findall(".//{%s}sheet" % _XLSX_NS)
        return [s.get("name", "Sheet%d" % (i + 1)) for i, s in enumerate(sheets)]
    except Exception:
        return []


def xlsx_read_rows(path: str, sheet_idx: int = 0, max_rows: int = 50):
    """(rows as lists of strings, sheet name) of an xlsx file (ZIP/XML, no openpyxl needed)."""
    import zipfile
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(path) as z:
        znames = z.namelist()
        with z.open("xl/workbook.xml") as f:
            wb_tree = ET.parse(f)
        sheet_els = wb_tree.findall(".//{%s}sheet" % _XLSX_NS)
        if not sheet_els:
            return [], "?"
        idx = min(sheet_idx, len(sheet_els) - 1)
        sheet_el = sheet_els[idx]
        sname = sheet_el.get("name", "Sheet%d" % (idx + 1))
        rid = sheet_el.get("{%s}id" % _XLSX_OFF_NS, "")
        sheet_file = None
        rels_path = "xl/_rels/workbook.xml.rels"
        if rels_path in znames:
            with z.open(rels_path) as f:
                rels = ET.parse(f)
            for rel in rels.findall(".//{%s}Relationship" % _XLSX_REL_NS):
                if rel.get("Id") == rid:
                    target = rel.get("Target", "")
                    sheet_file = target.lstrip("/") if target.startswith("/") else "xl/" + target
                    break
        if not sheet_file or sheet_file not in znames:
            sheet_file = next((n for n in znames if n.startswith("xl/worksheets/sheet")), None)
        if sheet_file is None:
            return [], sname
        shared = []
        if "xl/sharedStrings.xml" in znames:
            with z.open("xl/sharedStrings.xml") as f:
                ss = ET.parse(f)
            for si in ss.findall(".//{%s}si" % _XLSX_NS):
                shared.append("".join(e.text or "" for e in si.iter("{%s}t" % _XLSX_NS)))
        with z.open(sheet_file) as f:
            ws_tree = ET.parse(f)
        rows_data = []
        for row_el in ws_tree.findall(".//{%s}row" % _XLSX_NS):
            row = []
            for cell in row_el.findall("{%s}c" % _XLSX_NS):
                ct = cell.get("t", "")
                v_el = cell.find("{%s}v" % _XLSX_NS)
                val = ""
                if v_el is not None and v_el.text:
                    if ct == "s":
                        try:
                            val = shared[int(v_el.text)]
                        except Exception:
                            val = v_el.text
                    elif ct == "b":
                        val = "TRUE" if v_el.text == "1" else "FALSE"
                    else:
                        try:
                            fv = float(v_el.text)
                            val = str(int(fv)) if fv == int(fv) else "%.4g" % fv
                        except Exception:
                            val = v_el.text
                row.append(val)
            if row:
                rows_data.append(row)
            if len(rows_data) >= max_rows:
                break
    return rows_data, sname


def excel_image(path: str, sheet: int = 0, title: Optional[str] = None) -> Tuple[Any, Optional[str]]:
    """(PIL image of the first 50 rows of a sheet, None) or (None, error). title = file name shown on top."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        if path.lower().endswith(".xls"):
            try:
                import pandas as pd
                df = pd.read_excel(path, sheet_name=sheet, nrows=50, header=None, engine="xlrd")
                rows_data = [list(map(str, r)) for r in df.values.tolist()]
                sname = str(sheet)
            except Exception as e:
                return None, ".xls Ladefehler: " + str(e)
        else:
            rows_data, sname = xlsx_read_rows(path, sheet_idx=sheet, max_rows=50)
        if not rows_data:
            rows_data = [["(no content)"]]
        max_cols = max(len(r) for r in rows_data)
        rows_data = [r + [""] * (max_cols - len(r)) for r in rows_data]
        FONT_SIZE, PAD_X, PAD_Y = 13, 8, 5
        ROW_H = FONT_SIZE + PAD_Y * 2
        try:
            font = ImageFont.truetype("arial.ttf", FONT_SIZE)
            font_bold = ImageFont.truetype("arialbd.ttf", FONT_SIZE)
        except Exception:
            font = ImageFont.load_default()
            font_bold = font
        dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        col_widths = []
        for c in range(max_cols):
            max_w = 40
            for r_idx, row in enumerate(rows_data):
                txt = row[c] if c < len(row) else ""
                f = font_bold if r_idx == 0 else font
                try:
                    bb = dummy.textbbox((0, 0), txt, font=f)
                    w = bb[2] - bb[0]
                except Exception:
                    w = len(txt) * (FONT_SIZE // 2)
                max_w = max(max_w, w)
            col_widths.append(min(max_w + PAD_X * 2, 300))
        title_h = ROW_H + 4
        total_w = sum(col_widths) + 1
        total_h = title_h + len(rows_data) * ROW_H + 1
        img = Image.new("RGB", (total_w, total_h), (20, 20, 20))
        draw = ImageDraw.Draw(img)
        draw.text((PAD_X, PAD_Y), (title or os.path.basename(path)) + "  –  " + sname, fill=(160, 160, 160), font=font)
        for r_idx, row in enumerate(rows_data):
            y = title_h + r_idx * ROW_H
            bg = (45, 106, 63) if r_idx == 0 else ((30, 30, 30) if r_idx % 2 == 0 else (40, 40, 40))
            fg = (255, 255, 255) if r_idx == 0 else (220, 220, 220)
            f = font_bold if r_idx == 0 else font
            draw.rectangle([0, y, total_w, y + ROW_H], fill=bg)
            x = 0
            for c_idx, cw in enumerate(col_widths):
                txt = row[c_idx] if c_idx < len(row) else ""
                draw.text((x + PAD_X, y + PAD_Y), txt, fill=fg, font=f)
                draw.line([(x + cw, y), (x + cw, y + ROW_H)], fill=(70, 70, 70), width=1)
                x += cw
            draw.line([(0, y + ROW_H), (total_w, y + ROW_H)], fill=(70, 70, 70), width=1)
        return img, None
    except Exception as e:
        return None, str(e)


# ── Word ────────────────────────────────────────────────────────────────
def word_to_pdf_buf(path: str) -> Tuple[Optional[io.BytesIO], Optional[str]]:
    """Word -> PDF (docx2pdf with MS Word, else mammoth + pymupdf)."""
    import tempfile
    try:
        from docx2pdf import convert as _d2p
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.close()
        try:
            _d2p(path, tmp.name)
            with open(tmp.name, "rb") as f:
                buf = io.BytesIO(f.read())
            buf.seek(0)
            return buf, None
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass
    except Exception:
        pass
    try:
        import mammoth as _mammoth
        import fitz
        css = """
        body{font-family:Arial,sans-serif;font-size:11pt;line-height:1.55;color:#111;}
        h1{font-size:18pt;color:#1f3864;margin:14pt 0 5pt;}
        h2{font-size:14pt;color:#2e5094;margin:12pt 0 4pt;}
        h3{font-size:12pt;color:#2e5094;margin:9pt 0 3pt;}
        p{margin:0 0 6pt;}
        table{border-collapse:collapse;width:100%;font-size:10pt;}
        td,th{border:1px solid #aaa;padding:3pt 6pt;}
        th{background:#dce6f1;font-weight:bold;}
        strong{font-weight:bold;} em{font-style:italic;}
        """
        with open(path, "rb") as f:
            html_body = _mammoth.convert_to_html(f).value
        html = "<html><head><style>" + css + "</style></head><body>" + html_body + "</body></html>"
        W, H = 595, 842
        story = fitz.Story(html=html)
        buf = io.BytesIO()
        writer = fitz.DocumentWriter(buf, "pdf")
        more = 1
        while more:
            dev = writer.begin_page(fitz.Rect(0, 0, W, H))
            more, _ = story.place(fitz.Rect(50, 50, W - 50, H - 50))
            story.draw(dev)
            writer.end_page()
        writer.close()
        buf.seek(0)
        return buf, None
    except Exception as e:
        return None, "The image could not be read: " + str(e)


def word_page_count(path: str) -> int:
    try:
        import fitz
        buf, _err = word_to_pdf_buf(path)
        if buf is None:
            return 1
        pdf = fitz.open("pdf", buf.read())
        n = len(pdf)
        pdf.close()
        return max(1, n)
    except Exception:
        return 1


def word_image(path: str, page: int = 0) -> Tuple[Any, Optional[str]]:
    try:
        import fitz
        from PIL import Image
        buf, err = word_to_pdf_buf(path)
        if buf is None:
            return None, err
        pdf = fitz.open("pdf", buf.read())
        idx = min(page, len(pdf) - 1)
        pix = pdf[idx].get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
        pdf.close()
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples), None
    except Exception as e:
        return None, str(e)


# ── any file ────────────────────────────────────────────────────────────
def render(path: str, vk4_channel: str = "", pdf_page: int = 0, excel_sheet: int = 0, word_page: int = 0,
           title: Optional[str] = None):
    """(PIL image, error) of any supported file; documents limited to DOC_MAX pixels."""
    try:
        if is_vk4(path):
            img, err = vk4_image(path, vk4_channel), None
        elif is_pdf(path):
            img, err = pdf_image(path, pdf_page)
        elif is_excel(path):
            img, err = excel_image(path, excel_sheet, title)
        elif is_word(path):
            img, err = word_image(path, word_page)
        else:
            from PIL import Image
            img = Image.open(path)
            img.load()
            err = None
        if img is None:
            return None, err or "The file could not be read."
        if (is_pdf(path) or is_excel(path) or is_word(path)) and max(img.size) > DOC_MAX:
            img.thumbnail((DOC_MAX, DOC_MAX))
        return img, None
    except Exception as e:
        return None, str(e)


def info(path: str) -> Dict[str, Any]:
    """What can be chosen for a file: {"kind", "pages" | "sheets" | "channels"}."""
    if is_vk4(path):
        chs = vk4_channels(path)
        return {"kind": "vk4", "channels": [{"key": c, "label": VK4_CH_LABELS[c]} for c in chs]}
    if is_pdf(path):
        return {"kind": "pdf", "pages": pdf_page_count(path)}
    if is_excel(path):
        return {"kind": "excel", "sheets": excel_sheet_names(path)}
    if is_word(path):
        return {"kind": "word", "pages": word_page_count(path)}
    return {"kind": "image"}


def to_png(img, max_side: int = 0) -> bytes:
    """PNG bytes of a PIL image (RGB/RGBA), optionally limited to max_side pixels."""
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    if max_side and max(img.size) > max_side:
        img = img.copy()
        img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()
