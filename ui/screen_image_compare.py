from __future__ import annotations
# ui/screen_image_compare.py
"""Bild-Vergleichs-Screen (ImageCompareScreen) für TrippleT.

Ermöglicht das side-by-side Vergleichen von Bildern, PDFs, Excel- und
Word-Dokumenten sowie Keyence VK4-Profildateien.

Aufbau:
  - Linkes Panel: Bild-/Dateiliste aus DB (tblTrialSeriesImage/PDF) + lokale Dateien
  - Rechtes Panel: Vergleichsraster (1–4 Bilder nebeneinander)
  - Toolbar: Zoom, Rotation, Grid-Auswahl, Speichern, Projekt laden/speichern

Datei-Unterstützung:
  - Bilder: PNG, JPG, BMP, WEBP
  - Keyence VK4: Höhen- und Intensitätskanäle (numpy-basierter Parser)
  - PDF: via pymupdf (Seitenauswahl)
  - Excel: via ZIP/XML-Parser (kein openpyxl nötig)
  - Word: via docx2pdf/mammoth + fitz

Projekt-Persistenz: ``.ttcompare``-Format (JSON), speichert Bildpfade,
Rotation und aktuelle Ansicht.
"""

# ui/screen_image_compare.py

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QMimeData, QPoint, QPointF, QRect, Qt, Signal, QTimer, QObject, QRunnable, QThreadPool
from PySide6.QtGui import QColor, QDrag, QFont, QGuiApplication, QPainter, QPen, QPixmap, QTransform
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QMenu, QPushButton, QSizePolicy, QSpinBox, QSplitter, QVBoxLayout,
    QWidget, QTreeWidget, QTreeWidgetItem,
)

from db.connection import get_connection
from ui.widgets.footer import FooterBar
from ui.widgets.header import HeaderBar


# ---------------------------------------------------------------------------
# VK4 file support (Keyence laser profilometer)
# ---------------------------------------------------------------------------

VK4_CH_HEIGHT_PEAK   = "height_peak"
VK4_CH_HEIGHT_LIGHT  = "height_light"
VK4_CH_COLOR_PEAK    = "color_peak"
VK4_CH_COLOR_LIGHT   = "color_light"
VK4_CH_LIGHT_INT     = "light_int"

VK4_CH_LABELS = {
    VK4_CH_HEIGHT_PEAK:  "Height (laser)",
    VK4_CH_HEIGHT_LIGHT: "Height (light)",
    VK4_CH_COLOR_PEAK:   "Laser (Farbe)",
    VK4_CH_COLOR_LIGHT:  "Licht (Farbe)",
    VK4_CH_LIGHT_INT:    "Intensity (grey)",
}
VK4_CH_ORDER = [VK4_CH_HEIGHT_PEAK, VK4_CH_HEIGHT_LIGHT,
                VK4_CH_COLOR_PEAK, VK4_CH_COLOR_LIGHT, VK4_CH_LIGHT_INT]
_VK4_IDX = {VK4_CH_HEIGHT_PEAK:4, VK4_CH_HEIGHT_LIGHT:5,
            VK4_CH_COLOR_PEAK:1, VK4_CH_COLOR_LIGHT:2, VK4_CH_LIGHT_INT:3}


def _is_vk4(path: str) -> bool:
    """Gibt True zurück wenn der Pfad auf eine VK4-Datei zeigt."""
    return path.lower().endswith(".vk4")


def _vk4_available_channels(path: str) -> list:
    """Gibt eine Liste der verfügbaren Datenkanäle einer VK4-Datei zurück."""
    import struct
    try:
        with open(path, "rb") as f:
            if f.read(4) != b"VK4_": return []
            f.seek(12)
            offsets = struct.unpack("<12I", f.read(48))
        return [ch for ch in VK4_CH_ORDER if offsets[_VK4_IDX[ch]] != 0]
    except Exception:
        return []


def _load_vk4_channel(path: str, channel: str) -> Optional[QPixmap]:
    import struct, numpy as np
    def _np_to_pixmap(arr_rgb):
        from PIL import Image
        import tempfile, os as _os
        img = Image.fromarray(arr_rgb, "RGB")
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close(); img.save(tmp.name)
        pm = QPixmap(tmp.name)
        try: _os.unlink(tmp.name)
        except Exception: pass
        return pm if not pm.isNull() else None
    def _jet(arr):
        r = np.clip(1.5 - np.abs(arr*4.0-3.0), 0, 1)
        g = np.clip(1.5 - np.abs(arr*4.0-2.0), 0, 1)
        b = np.clip(1.5 - np.abs(arr*4.0-1.0), 0, 1)
        return np.stack([(r*255).astype(np.uint8),(g*255).astype(np.uint8),(b*255).astype(np.uint8)], axis=-1)
    try:
        with open(path, "rb") as f:
            if f.read(4) != b"VK4_": return None
            f.seek(12); offsets = struct.unpack("<12I", f.read(48))
            idx = _VK4_IDX.get(channel)
            if idx is None: return None
            off = offsets[idx]
            if off == 0: return None
            f.seek(off); blk = f.read(20)
            w = struct.unpack_from("<I", blk, 0)[0]
            h = struct.unpack_from("<I", blk, 4)[0]
            bpp = struct.unpack_from("<I", blk, 8)[0]
            if w == 0 or h == 0: return None
            if channel in (VK4_CH_HEIGHT_PEAK, VK4_CH_HEIGHT_LIGHT):
                if bpp not in (16, 32): return None
                raw = f.read(w * h * (bpp // 8))
                if len(raw) < w * h * (bpp // 8): return None
                dtype = "<u2" if bpp == 16 else "<u4"
                arr = np.frombuffer(raw, dtype=dtype).reshape((h, w)).astype(np.float32)
                invalid = arr == (0xFFFF if bpp == 16 else 0xFFFFFFFF)
                valid = arr[~invalid]
                if valid.size == 0: return None
                lo = float(np.percentile(valid, 1)); hi = float(np.percentile(valid, 99))
                if hi <= lo: hi = lo + 1.0
                norm = np.clip((arr - lo) / (hi - lo), 0.0, 1.0); norm[invalid] = 0.0
                rgb = _jet(norm); rgb[invalid] = 0
                return _np_to_pixmap(rgb)
            if channel in (VK4_CH_COLOR_PEAK, VK4_CH_COLOR_LIGHT):
                if bpp != 24: return None
                raw = f.read(w * h * 3)
                if len(raw) < w * h * 3: return None
                arr = np.frombuffer(raw, dtype=np.uint8).reshape((h, w, 3))
                return _np_to_pixmap(arr[:, :, ::-1].copy())
            if channel == VK4_CH_LIGHT_INT:
                if bpp not in (8, 16): return None
                dtype = np.uint8 if bpp == 8 else "<u2"
                raw = f.read(w * h * (bpp // 8))
                if len(raw) < w * h * (bpp // 8): return None
                arr = np.frombuffer(raw, dtype=dtype).reshape((h, w)).astype(np.float32)
                norm = (arr - arr.min()) / max(arr.max() - arr.min(), 1)
                g8 = (norm * 255).astype(np.uint8)
                return _np_to_pixmap(np.stack([g8, g8, g8], axis=-1))
            return None
    except Exception:
        return None


def _load_vk4_as_pixmap(path: str) -> Optional[QPixmap]:
    """Lädt den ersten verfügbaren VK4-Kanal als QPixmap."""
    for ch in _vk4_available_channels(path):
        pm = _load_vk4_channel(path, ch)
        if pm is not None: return pm
    return None



# ---------------------------------------------------------------------------
# PDF / Excel / Word helpers  (geteilt mit screen_canvas.py)
# ---------------------------------------------------------------------------

def _is_pdf(path: str) -> bool:
    """Gibt True zurück wenn der Pfad auf eine PDF-Datei zeigt."""
    return path.lower().endswith(".pdf")

def _is_excel(path: str) -> bool:
    """Gibt True zurück wenn der Pfad auf eine Excel-Datei zeigt (.xlsx/.xlsm/.xls)."""
    return path.lower().endswith((".xlsx", ".xlsm", ".xls"))

def _is_word(path: str) -> bool:
    """Gibt True zurück wenn der Pfad auf eine Word-Datei zeigt (.docx/.doc)."""
    return path.lower().endswith((".docx", ".doc"))


def _pil_to_pixmap(img) -> "Optional[QPixmap]":
    """Konvertiert ein PIL-Image zu QPixmap via temporärer PNG-Datei."""
    from PIL import Image as _Image
    import tempfile, os as _os
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    img.save(tmp.name)
    pm = QPixmap(tmp.name)
    try: _os.unlink(tmp.name)
    except Exception: pass
    return pm if not pm.isNull() else None


def _pdf_page_count(path: str) -> int:
    """Gibt die Seitenanzahl eines PDFs zurück (pymupdf, Fallback pypdf)."""
    try:
        import fitz
        doc = fitz.open(path); n = len(doc); doc.close(); return n
    except Exception:
        try:
            from pypdf import PdfReader
            return len(PdfReader(path).pages)
        except Exception:
            return 1


def _load_pdf_as_pixmap(path: str, page: int = 0) -> "tuple":
    """Rendert eine PDF-Seite als QPixmap via pymupdf.

    Returns:
        (QPixmap, None) bei Erfolg oder (None, Fehlermeldung) bei Fehler.
    """
    try:
        import fitz
        doc = fitz.open(path)
        if page >= len(doc):
            return None, "Seite %d existiert nicht." % page
        pix = doc[page].get_pixmap(matrix=fitz.Matrix(150/72, 150/72), alpha=False)
        doc.close()
        from PIL import Image as _Image
        img = _Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        pm = _pil_to_pixmap(img)
        return (pm, None) if pm and not pm.isNull() else (None, "Konvertierung fehlgeschlagen.")
    except ImportError:
        return None, "pymupdf nicht installiert. Bitte: pip install pymupdf"
    except Exception as e:
        return None, str(e)


# Zipfile-basierter Excel-Reader
_XLSX_NS     = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_XLSX_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_XLSX_OFF_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _excel_sheet_names(path: str) -> list:
    """Gibt die Sheet-Namen einer Excel-Datei zurück."""
    if path.lower().endswith(".xls"):
        try:
            import pandas as pd
            return pd.ExcelFile(path, engine="xlrd").sheet_names
        except Exception:
            return ["Sheet1"]
    try:
        import zipfile, xml.etree.ElementTree as ET
        with zipfile.ZipFile(path) as z:
            with z.open("xl/workbook.xml") as f:
                tree = ET.parse(f)
        sheets = tree.findall(".//{%s}sheet" % _XLSX_NS)
        return [s.get("name", "Sheet%d" % (i+1)) for i, s in enumerate(sheets)]
    except Exception:
        return []


def _xlsx_read_rows(path: str, sheet_idx: int = 0, max_rows: int = 50):
    """Liest Zeilen aus einer xlsx-Datei (ZIP/XML, kein openpyxl nötig).

    Returns:
        (rows_data, sheet_name): rows_data = List[List[str]].
    """
    import zipfile, xml.etree.ElementTree as ET
    with zipfile.ZipFile(path) as z:
        znames = z.namelist()
        with z.open("xl/workbook.xml") as f:
            wb_tree = ET.parse(f)
        sheet_els = wb_tree.findall(".//{%s}sheet" % _XLSX_NS)
        if not sheet_els: return [], "?"
        idx = min(sheet_idx, len(sheet_els)-1)
        sheet_el = sheet_els[idx]
        sname = sheet_el.get("name", "Sheet%d" % (idx+1))
        rid   = sheet_el.get("{%s}id" % _XLSX_OFF_NS, "")
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
        if sheet_file is None: return [], sname
        shared = []
        if "xl/sharedStrings.xml" in znames:
            with z.open("xl/sharedStrings.xml") as f:
                ss = ET.parse(f)
            for si in ss.findall(".//{%s}si" % _XLSX_NS):
                t = "".join(e.text or "" for e in si.iter("{%s}t" % _XLSX_NS))
                shared.append(t)
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
                        try: val = shared[int(v_el.text)]
                        except: val = v_el.text
                    elif ct == "b":
                        val = "TRUE" if v_el.text == "1" else "FALSE"
                    else:
                        try:
                            fv = float(v_el.text)
                            val = str(int(fv)) if fv == int(fv) else "%.4g" % fv
                        except: val = v_el.text
                row.append(val)
            if row: rows_data.append(row)
            if len(rows_data) >= max_rows: break
    return rows_data, sname


def _load_excel_as_pixmap(path: str, sheet: int = 0) -> "tuple":
    """Rendert ein Excel-Sheet als QPixmap (PIL-Renderer, kein matplotlib).

    Returns:
        (QPixmap, None) bei Erfolg oder (None, Fehlermeldung) bei Fehler.
    """
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from PIL import Image as _Image
        import io, os as _os
        if path.lower().endswith(".xls"):
            try:
                import pandas as pd
                df = pd.read_excel(path, sheet_name=sheet, nrows=50, header=None, engine="xlrd")
                rows_data = [list(map(str, r)) for r in df.values.tolist()]
                sname = str(sheet)
            except Exception as e:
                return None, ".xls Ladefehler: " + str(e)
        else:
            rows_data, sname = _xlsx_read_rows(path, sheet_idx=sheet, max_rows=50)
        if not rows_data: rows_data = [["(kein Inhalt)"]]
        max_cols = max(len(r) for r in rows_data)
        rows_data = [r + [""] * (max_cols - len(r)) for r in rows_data]
        from PIL import ImageDraw as _IDraw, ImageFont as _IFont
        FONT_SIZE = 13; PAD_X = 8; PAD_Y = 5; ROW_H = FONT_SIZE + PAD_Y * 2
        try:
            font = _IFont.truetype("arial.ttf", FONT_SIZE)
            font_bold = _IFont.truetype("arialbd.ttf", FONT_SIZE)
        except Exception:
            font = _IFont.load_default(); font_bold = font
        dummy = _IDraw.Draw(_Image.new("RGB", (1,1)))
        col_widths = []
        for c in range(max_cols):
            max_w = 40
            for r_idx, row in enumerate(rows_data):
                txt = row[c] if c < len(row) else ""
                f = font_bold if r_idx == 0 else font
                try:
                    bb = dummy.textbbox((0,0), txt, font=f); w = bb[2]-bb[0]
                except: w = len(txt) * (FONT_SIZE//2)
                max_w = max(max_w, w)
            col_widths.append(min(max_w + PAD_X*2, 300))
        title_h = ROW_H + 4
        total_w = sum(col_widths) + 1
        total_h = title_h + len(rows_data) * ROW_H + 1
        img = _Image.new("RGB", (total_w, total_h), (20,20,20))
        draw = _IDraw.Draw(img)
        draw.text((PAD_X, PAD_Y), _os.path.basename(path) + "  –  " + sname,
                  fill=(160,160,160), font=font)
        for r_idx, row in enumerate(rows_data):
            y = title_h + r_idx * ROW_H
            bg = (45,106,63) if r_idx==0 else ((30,30,30) if r_idx%2==0 else (40,40,40))
            fg = (255,255,255) if r_idx==0 else (220,220,220)
            f  = font_bold if r_idx==0 else font
            draw.rectangle([0, y, total_w, y+ROW_H], fill=bg)
            x = 0
            for c_idx, cw in enumerate(col_widths):
                txt = row[c_idx] if c_idx < len(row) else ""
                draw.text((x+PAD_X, y+PAD_Y), txt, fill=fg, font=f)
                draw.line([(x+cw, y),(x+cw, y+ROW_H)], fill=(70,70,70), width=1)
                x += cw
            draw.line([(0, y+ROW_H),(total_w, y+ROW_H)], fill=(70,70,70), width=1)
        pm = _pil_to_pixmap(img)
        return (pm, None) if pm and not pm.isNull() else (None, "Konvertierung fehlgeschlagen.")
    except Exception as e:
        return None, str(e)


def _word_to_pdf_buf(path: str) -> "tuple":
    """Konvertiert ein Word-Dokument zu PDF (BytesIO-Buffer).

    Versucht zuerst docx2pdf (MS Word), dann mammoth+fitz als Fallback.

    Returns:
        (BytesIO, None) bei Erfolg oder (None, Fehlermeldung) bei Fehler.
    """
    import io, tempfile, os as _os
    try:
        from docx2pdf import convert as _d2p
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.close()
        try:
            _d2p(path, tmp.name)
            with open(tmp.name, "rb") as f:
                buf = io.BytesIO(f.read())
            buf.seek(0); return buf, None
        finally:
            try: _os.unlink(tmp.name)
            except Exception: pass
    except Exception:
        pass
    try:
        import mammoth as _mammoth, fitz
        _CSS = """
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
        html = "<html><head><style>" + _CSS + "</style></head><body>" + html_body + "</body></html>"
        W, H = 595, 842
        story = fitz.Story(html=html)
        buf = io.BytesIO()
        writer = fitz.DocumentWriter(buf, "pdf")
        more = 1
        while more:
            dev = writer.begin_page(fitz.Rect(0,0,W,H))
            more, _ = story.place(fitz.Rect(50,50,W-50,H-50))
            story.draw(dev); writer.end_page()
        writer.close(); buf.seek(0); return buf, None
    except Exception as e:
        return None, "Fallback fehlgeschlagen: " + str(e)


def _word_page_count(path: str) -> int:
    """Gibt die Seitenanzahl eines Word-Dokuments zurück."""
    try:
        import fitz
        buf, err = _word_to_pdf_buf(path)
        if buf is None: return 1
        pdf = fitz.open("pdf", buf.read()); n = len(pdf); pdf.close(); return max(1, n)
    except Exception:
        return 1


def _load_word_as_pixmap(path: str, page: int = 0) -> "tuple":
    """Rendert eine Word-Seite als QPixmap.

    Returns:
        (QPixmap, None) bei Erfolg oder (None, Fehlermeldung) bei Fehler.
    """
    try:
        import fitz
        from PIL import Image as _Image
        buf, err = _word_to_pdf_buf(path)
        if buf is None: return None, err
        pdf = fitz.open("pdf", buf.read())
        idx = min(page, len(pdf)-1)
        pix = pdf[idx].get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
        pdf.close()
        img = _Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        pm = _pil_to_pixmap(img)
        return (pm, None) if pm and not pm.isNull() else (None, "Konvertierung fehlgeschlagen.")
    except Exception as e:
        return None, str(e)

def _make_pixmap(path: str, size: int = 0, vk4_channel: str = "",
    # Lädt ein Bild/Dokument als QPixmap, optional mit Skalierung und VK4-Kanal.
    # Returns (QPixmap, page_count, sheet_names).
                 pdf_page: int = 0, excel_sheet: int = 0,
                 word_page: int = 0) -> Optional[QPixmap]:
    try:
        if _is_vk4(path):
            pm = _load_vk4_channel(path, vk4_channel) if vk4_channel else _load_vk4_as_pixmap(path)
        elif _is_pdf(path):
            pm, _ = _load_pdf_as_pixmap(path, page=pdf_page)
        elif _is_excel(path):
            pm, _ = _load_excel_as_pixmap(path, sheet=excel_sheet)
        elif _is_word(path):
            pm, _ = _load_word_as_pixmap(path, page=word_page)
        else:
            pm = QPixmap(path)
        if pm is None or pm.isNull():
            return None
        if size > 0:
            pm = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        elif _is_excel(path) or _is_word(path) or _is_pdf(path):
            # Dokumente: weiterhin auf 2400px begrenzen (werden ohnehin gerendert)
            if max(pm.width(), pm.height()) > 2400:
                pm = pm.scaled(2400, 2400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        # Normale Bilder / VK4: kein Downscaling → volles Original behalten für scharfen Zoom
        return pm
    except Exception:
        return None



# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _fetch_series_groups() -> List[Dict]:
    """Lädt alle Serien mit Bildern oder PDFs aus der DB (mit has_images/has_pdfs-Flags)."""
    rows: List[Dict] = []
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(
                "SELECT DISTINCT s.ID AS TrialSeriesID, s.SeriesName, e.[Experiment ID] AS ExperimentID "
                "FROM tblTrialSeries s "
                "INNER JOIN tblTrialSeriesImage i ON i.TrialSeriesID = s.ID "
                "LEFT JOIN tblExperimente e ON e.ID = s.ExperimentID "
                "ORDER BY e.[Experiment ID] DESC, s.SeriesName"
            )
            cols = [d[0] for d in (cur.description or [])]
            for row in cur.fetchall() or []:
                rows.append(dict(zip(cols, row)))
    except Exception:
        pass
    return rows


def _fetch_images_for_series(series_id: int) -> List[Dict]:
    """Lädt alle Bilder einer Serie aus tblTrialSeriesImage."""
    rows: List[Dict] = []
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(
                "SELECT ID, TrialSeriesID, RelativePath, StoredFilename, OriginalFilename "
                "FROM tblTrialSeriesImage WHERE TrialSeriesID = ? ORDER BY ID",
                (series_id,),
            )
            cols = [d[0] for d in (cur.description or [])]
            for row in cur.fetchall() or []:
                rows.append(dict(zip(cols, row)))
    except Exception:
        pass
    return rows


def _build_full_path(row: Dict) -> str:
    """Baut den vollständigen Dateipfad aus einem Bild-Dict (RelativePath + StoredFilename)."""
    if row.get("_local"):
        return str(row.get("FullPath") or "")
    rel    = str(row.get("RelativePath") or "")
    stored = str(row.get("StoredFilename") or "")
    return os.path.join(rel, stored) if rel else stored


# ---------------------------------------------------------------------------
# Pixmap helpers
# ---------------------------------------------------------------------------

def _apply_rotation(pm: QPixmap, degrees: int) -> QPixmap:
    """Rotiert ein QPixmap um degrees Grad (90°-Schritte)."""
    if pm is None or pm.isNull() or degrees % 360 == 0:
        return pm
    return pm.transformed(QTransform().rotate(degrees), Qt.SmoothTransformation)


def _save_rotated_pixmap(pm: Optional[QPixmap], path: str) -> None:
    """Speichert ein QPixmap als Datei (Format aus Dateiendung)."""
    if pm is None or pm.isNull() or not path:
        return
    try:
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        fmt = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG",
               "bmp": "BMP", "tif": "TIFF", "tiff": "TIFF"}.get(ext, "PNG")
        pm.save(path, fmt)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Async pixmap loader
# ---------------------------------------------------------------------------

class _PixmapSignals(QObject):
    """Qt-Signale für den asynchronen Pixmap-Loader."""
    done = Signal(object, object)


class _PixmapLoader(QRunnable):
    """Hintergrund-Worker: prüft ob ein Dateipfad existiert (für schnelle Vorschau)."""
    def __init__(self, path: str, meta: object, signals: _PixmapSignals):
        super().__init__()
        self._path    = path
        self._meta    = meta
        self._signals = signals
        self.setAutoDelete(True)

    def run(self):
        try:
            exists = bool(self._path and os.path.isfile(self._path))
        except Exception:
            exists = False
        self._signals.done.emit(self._path if exists else None, self._meta)


_pool = QThreadPool.globalInstance()
_pool.setMaxThreadCount(4)


class _RenderSignals(QObject):
    """Qt-Signale für den asynchronen Render-Worker (PDF/Excel/Word)."""
    done = Signal(object, object, object)   # (QPixmap|None, err_str|None, request_meta)


class _RenderWorker(QRunnable):
    """Hintergrund-Worker: rendert PDF/Excel/Word-Seiten als QPixmap."""
    """Rendert PDF/Excel/Word-Seiten im Hintergrund-Thread."""
    def __init__(self, path: str, request_meta: dict, signals: "_RenderSignals"):
        super().__init__()
        self._path    = path
        self._rmeta   = request_meta
        self._signals = signals
        self.setAutoDelete(True)

    def run(self):
        path  = self._path
        meta  = self._rmeta.get("meta") or {}
        pm    = None
        err   = None
        try:
            if _is_pdf(path):
                pg = int(meta.get("_pdf_page") or 0)
                pm, err = _load_pdf_as_pixmap(path, page=pg)
            elif _is_excel(path):
                si = int(meta.get("_excel_sheet") or 0)
                pm, err = _load_excel_as_pixmap(path, sheet=si)
            elif _is_word(path):
                wp = int(meta.get("_word_page") or 0)
                pm, err = _load_word_as_pixmap(path, page=wp)
            # VK4 / normale Bilder werden weiterhin in _on_path_verified geladen
        except Exception as e:
            err = str(e)
        self._signals.done.emit(pm, err, self._rmeta)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOOL_PAN       = "pan"
TOOL_ARROW     = "arrow"
TOOL_ELLIPSE   = "ellipse"
TOOL_RECT      = "rect"
TOOL_FREE      = "free"
TOOL_TEXT      = "text"
TOOL_ERASER    = "eraser"
TOOL_MOVE      = "move"
TOOL_HIGHLIGHT = "highlight"
TOOL_MARKER    = "marker"

_ERASER_RADIUS  = 24
_MARKER_CHARS   = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
_UNDO_LIMIT     = 10

ANNO_COLORS = {
    "red":    QColor(220, 50,  50),
    "yellow": QColor(240, 200, 0),
    "green":  QColor(50,  200, 80),
    "white":  QColor(255, 255, 255),
    "blue":   QColor( 50, 130, 255),
}


_MIME_IMG   = "imgid:"
_MIME_FRAME = "frameidx:"



# ---------------------------------------------------------------------------
# Loading Overlay  –  animierter Ladebalken über einer Cell/Widget
# ---------------------------------------------------------------------------
class _LoadingOverlay(QWidget):
    """Halbtransparenter Lade-Overlay mit animiertem Fortschrittsbalken."""
    """Halbtransparenter Overlay mit animiertem Fortschrittsbalken."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._progress = 0          # 0–100 (animiert)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.hide()

    def start(self, text: str = "Lade..."):
        """Zeigt den Overlay mit dem gegebenen Text und startet die Animation."""
        self._text = text
        self._progress = 0
        self.resize(self.parent().size())
        self.raise_()
        self.show()
        self._timer.start(30)

    def stop(self):
        self._timer.stop()
        self.hide()

    def _tick(self):
        # Indeterminate: läuft bis 90%, bleibt dort bis stop()
        if self._progress < 90:
            self._progress = min(90, self._progress + 2)
        self.update()

    def finish(self):
        """Balken kurz auf 100% setzen, dann ausblenden."""
        self._timer.stop()
        self._progress = 100
        self.update()
        QTimer.singleShot(300, self.stop)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Dunkler Hintergrund
        p.fillRect(0, 0, w, h, QColor(0, 0, 0, 160))

        # Beschriftung
        p.setPen(QColor(220, 220, 220))
        f = QFont(); f.setPointSize(10); p.setFont(f)
        text = getattr(self, "_text", "Lade...")
        p.drawText(0, h//2 - 28, w, 24, Qt.AlignCenter, text)

        # Balken-Hintergrund
        bar_w = min(w - 60, 320)
        bar_h = 10
        bar_x = (w - bar_w) // 2
        bar_y = h//2 - 5
        p.setBrush(QColor(60, 60, 60))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 5, 5)

        # Fortschritt
        fill_w = int(bar_w * self._progress / 100)
        if fill_w > 0:
            p.setBrush(QColor(57, 166, 80))
            p.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 5, 5)

        p.end()

# ---------------------------------------------------------------------------
# Image list item
# ---------------------------------------------------------------------------

class _CompareImageTree(QTreeWidget):
    def __init__(self, panel: "_ImageListPanel", parent: QWidget | None = None):
        super().__init__(parent)
        self._panel = panel
        self._drag_start: Optional[QPoint] = None
        self.setHeaderHidden(True)
        self.setIndentation(15)
        self.setStyleSheet("""
            QTreeWidget { background: #1a1a1a; color: #eee; border: none; font-size: 11px; }
            QTreeWidget::item { height: 26px; border-bottom: 1px solid #2a2a2a; }
            QTreeWidget::item:hover { background: #333; }
        """)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag_start = ev.pos()
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if not (ev.buttons() & Qt.LeftButton) or self._drag_start is None:
            super().mouseMoveEvent(ev)
            return
        if (ev.pos() - self._drag_start).manhattanLength() < 8:
            super().mouseMoveEvent(ev)
            return
        item = self.itemAt(self._drag_start)
        if item is None:
            super().mouseMoveEvent(ev)
            return
        meta = item.data(0, Qt.UserRole)
        if not isinstance(meta, dict) or "ID" not in meta:
            super().mouseMoveEvent(ev)
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(f"{_MIME_IMG}{meta.get('ID')}")
        drag.setMimeData(mime)
        drag.exec(Qt.CopyAction)


class _ImageListPanel(QWidget):
    image_selected = Signal(object)
    whiteboard_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._local_counter = 0
        self._db_images_by_id: Dict[str, Dict] = {}
        self._series_groups: List[Dict] = []
        self.local_root: Optional[QTreeWidgetItem] = None
        self._loaded_once = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)

        frow = QHBoxLayout()
        frow.setSpacing(4)
        self._sf = QLineEdit()
        self._sf.setPlaceholderText("Filter (Experiment/Datei)...")
        self._sf.setClearButtonEnabled(True)
        self._sf.textChanged.connect(self._filter_tree)
        frow.addWidget(self._sf)
        lay.addLayout(frow)

        self.tree = _CompareImageTree(self)
        self.tree.itemExpanded.connect(self._on_item_expanded)
        self.tree.itemClicked.connect(self._on_item_clicked)
        lay.addWidget(self.tree, 1)

        brow = QHBoxLayout()
        brow.setSpacing(4)

        btn_r = QPushButton("Reload")
        btn_r.setObjectName("GreenBtn")
        btn_r.setFixedHeight(28)
        btn_r.clicked.connect(self.load_images)
        brow.addWidget(btn_r)

        btn_l = QPushButton("+ Local")
        btn_l.setObjectName("GreenBtn")
        btn_l.setFixedHeight(28)
        btn_l.clicked.connect(self._add_local)
        brow.addWidget(btn_l)

        btn_wb = QPushButton("⬜ Board")
        btn_wb.setObjectName("GreenBtn")
        btn_wb.setFixedHeight(28)
        btn_wb.setToolTip("Insert whiteboard into active frame")
        btn_wb.clicked.connect(self._add_whiteboard)
        brow.addWidget(btn_wb)

        lay.addLayout(brow)

    def load_images(self):
        self.tree.clear()
        self._db_images_by_id.clear()
        self._loaded_once = True

        self.local_root = QTreeWidgetItem(self.tree, ["📁 Lokale Bilder"])
        self.local_root.setExpanded(True)

        self._series_groups = _fetch_series_groups()
        for g in self._series_groups:
            name = f"{g.get('ExperimentID') or ''} | {g.get('SeriesName') or ''}"
            item = QTreeWidgetItem(self.tree, [name])
            item.setData(0, Qt.UserRole, g)
            item.setForeground(0, QColor("#7ddf9a"))
            QTreeWidgetItem(item, ["Lade Bilder..."])

        self._filter_tree()

    def _on_item_expanded(self, item):
        data = item.data(0, Qt.UserRole)
        if not isinstance(data, dict) or "TrialSeriesID" not in data:
            return
        if item.childCount() == 1 and item.child(0).text(0) == "Lade Bilder...":
            item.removeChild(item.child(0))
            images = _fetch_images_for_series(data["TrialSeriesID"])
            for img in images:
                img.setdefault("ExperimentID", data.get("ExperimentID"))
                img.setdefault("SeriesName", data.get("SeriesName"))
                self._db_images_by_id[str(img.get("ID"))] = img
                child = QTreeWidgetItem(item, [img.get("OriginalFilename") or ""] )
                child.setData(0, Qt.UserRole, img)
                child.setForeground(0, QColor("#bbb"))
            self._filter_tree()

    def _on_item_clicked(self, item, _col):
        data = item.data(0, Qt.UserRole)
        if isinstance(data, dict) and "ID" in data:
            self.image_selected.emit(data)

    def _add_local(self):
        if not hasattr(self, "local_root") or self.local_root is None:
            self.local_root = QTreeWidgetItem(self.tree, ["Lokale Bilder"])
            self.tree.insertTopLevelItem(0, self.local_root)
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Bilder / Dokumente", "",
            "Alle unterstuetzten Dateien (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp *.vk4 *.pdf *.xlsx *.xlsm *.xls *.docx *.doc);;"
            "Bilder (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp);;"
            "Keyence VK4 (*.vk4);;"
            "PDF (*.pdf);;"
            "Excel (*.xlsx *.xlsm *.xls);;"
            "Word (*.docx *.doc);;"
            "Alle Dateien (*.*)",
        )
        for p in paths:
            basename = os.path.basename(p)
            if _is_pdf(p):
                n_pages = _pdf_page_count(p)
                pdf_root = QTreeWidgetItem(self.local_root,
                    [basename + ("  (%d Seiten)" % n_pages if n_pages > 1 else "")])
                pdf_root.setForeground(0, QColor("#8cf"))
                for pg in range(n_pages):
                    self._local_counter -= 1
                    meta = {"ID": self._local_counter,
                            "OriginalFilename": basename + " - Seite %d" % (pg+1),
                            "FullPath": p, "_local": True, "_pdf_page": pg}
                    child = QTreeWidgetItem(pdf_root, ["  Seite %d" % (pg+1)])
                    child.setData(0, Qt.UserRole, meta)
                    child.setForeground(0, QColor("#bbb"))
                pdf_root.setExpanded(n_pages <= 6)
            elif _is_excel(p):
                sheets = _excel_sheet_names(p)
                xls_root = QTreeWidgetItem(self.local_root,
                    [basename + "  (%d Sheets)" % len(sheets)])
                xls_root.setForeground(0, QColor("#7ddf9a"))
                for si, sname in enumerate(sheets):
                    self._local_counter -= 1
                    meta = {"ID": self._local_counter,
                            "OriginalFilename": basename + " - " + sname,
                            "FullPath": p, "_local": True, "_excel_sheet": si}
                    child = QTreeWidgetItem(xls_root, ["  " + sname])
                    child.setData(0, Qt.UserRole, meta)
                    child.setForeground(0, QColor("#bbb"))
                xls_root.setExpanded(len(sheets) <= 6)
            elif _is_word(p):
                n_pages = _word_page_count(p)
                word_root = QTreeWidgetItem(self.local_root,
                    [basename + ("  (%d Seiten)" % n_pages if n_pages > 1 else "")])
                word_root.setForeground(0, QColor("#d4a0ff"))
                for pg in range(n_pages):
                    self._local_counter -= 1
                    meta = {"ID": self._local_counter,
                            "OriginalFilename": basename + " - Seite %d" % (pg+1),
                            "FullPath": p, "_local": True,
                            "_word": True, "_word_page": pg}
                    child = QTreeWidgetItem(word_root, ["  Seite %d" % (pg+1)])
                    child.setData(0, Qt.UserRole, meta)
                    child.setForeground(0, QColor("#bbb"))
                word_root.setExpanded(n_pages <= 6)
            else:
                self._local_counter -= 1
                meta = {"ID": self._local_counter, "OriginalFilename": basename,
                        "FullPath": p, "_local": True}
                child = QTreeWidgetItem(self.local_root, [basename])
                child.setData(0, Qt.UserRole, meta)
                child.setForeground(0, QColor("#bbb"))
        self.local_root.setExpanded(True)
        self._filter_tree()

    def _add_whiteboard(self):
        self.whiteboard_requested.emit()

    def _filter_tree(self):
        txt = self._sf.text().strip().lower()
        visible_images = 0
        visible_series = 0
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            data = it.data(0, Qt.UserRole)

            if it is self.local_root:
                local_visible = 0
                for j in range(it.childCount()):
                    ch = it.child(j)
                    meta = ch.data(0, Qt.UserRole) or {}
                    hay = f"{ch.text(0)}".lower()
                    match = (txt == "") or (txt in hay)
                    ch.setHidden(not match)
                    if match:
                        local_visible += 1
                        visible_images += 1
                it.setHidden(txt != "" and local_visible == 0 and "lokale bilder".find(txt) == -1)
                continue

            if isinstance(data, dict) and "TrialSeriesID" in data:
                group_match = (txt == "") or (txt in it.text(0).lower())
                child_visible = 0
                for j in range(it.childCount()):
                    ch = it.child(j)
                    ch_data = ch.data(0, Qt.UserRole)
                    if isinstance(ch_data, dict) and "ID" in ch_data:
                        hay = f"{it.text(0)} {ch.text(0)}".lower()
                        match = (txt == "") or (txt in hay)
                        ch.setHidden(not match)
                        if match:
                            child_visible += 1
                            visible_images += 1
                    else:
                        ch.setHidden(not group_match)
                hide_group = False
                if txt:
                    hide_group = (not group_match) and (child_visible == 0)
                it.setHidden(hide_group)
                if not hide_group:
                    visible_series += 1
            else:
                it.setHidden(False)

        self.tree.viewport().update()

    def get_meta_by_id(self, img_id: Any) -> Optional[Dict]:
        key = str(img_id)
        if key in self._db_images_by_id:
            return self._db_images_by_id[key]
        root = getattr(self, "local_root", None)
        if root is not None:
            for i in range(root.childCount()):
                meta = root.child(i).data(0, Qt.UserRole)
                if isinstance(meta, dict) and str(meta.get("ID")) == key:
                    return meta
        return None


# ---------------------------------------------------------------------------
# Data classes for annotations and undo snapshots
# ---------------------------------------------------------------------------

@dataclass
class Annotation:
    tool:   str
    color:  str
    size:   int
    text:   str = ""
    points: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class _CellSnapshot:
    annotations: List[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Frame cell – with annotation support + per-cell undo stack
# ---------------------------------------------------------------------------

class _FrameCell(QFrame):
    clicked       = Signal(int)
    image_dropped = Signal(int, str)

    _C_INACTIVE = "#555"
    _C_ACTIVE   = "#39A650"
    _C_BG       = "#1e1e1e"

    def __init__(self, row: int, col: int, parent: QWidget | None = None):
        super().__init__(parent)
        self._row   = row
        self._col   = col
        self._index = row * 100 + col

        self._meta:         Optional[Dict]        = None
        self._pixmap:       Optional[QPixmap]     = None
        self._active:       bool                  = False
        self._zoom:         float                 = 1.0
        self._pan_offset    = QPoint(0, 0)
        self._pan_start:    Optional[QPoint]      = None
        self._pan_snap      = QPoint(0, 0)
        self._drag_start:   Optional[QPoint]      = None
        self._loading:      bool                  = False
        self._rotation:     int                   = 0
        self._whiteboard:   bool                  = False
        self._load_token:   int                   = 0
        self._vk4_channel:  str                   = ""

        # Annotations
        self._annotations:  List[Annotation]      = []
        self._current_anno: Optional[Annotation]  = None

        # Move tool state
        self._move_anno:    Optional[Annotation]  = None
        self._move_start:   Optional[QPoint]      = None

        # Per-cell undo stack (max. _UNDO_LIMIT snapshots)
        self._undo_stack:   List[_CellSnapshot]   = []

        # Tool state (set from outside by ImageCompareScreen)
        self.active_tool:  str = TOOL_PAN
        self.active_color: str = "red"
        self.active_size:  int = 2
        self.grid_overlay: bool = False
        self.grid_divisions: int = 3

        self.setAcceptDrops(True)
        self.setMinimumSize(100, 80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.grabGesture(Qt.PinchGesture)
        self._pinch_zoom_start: float = 1.0
        self._overlay = _LoadingOverlay(self)
        self._apply_style()

    # -----------------------------------------------------------------------
    # Undo
    # -----------------------------------------------------------------------
    def _anno_to_dict(self, anno: Annotation) -> dict:
        return {
            "tool":   anno.tool,
            "color":  anno.color,
            "size":   anno.size,
            "text":   anno.text,
            "points": list(anno.points),
        }

    def _anno_from_dict(self, d: dict) -> Annotation:
        return Annotation(
            tool=d["tool"],
            color=d["color"],
            size=d["size"],
            text=d.get("text", ""),
            points=[tuple(p) for p in d["points"]],
        )

    def push_undo(self):
        """Sichert den aktuellen Annotations-Zustand auf den Undo-Stack."""
        snap = _CellSnapshot(
            annotations=[self._anno_to_dict(a) for a in self._annotations]
        )
        self._undo_stack.append(snap)
        if len(self._undo_stack) > _UNDO_LIMIT:
            self._undo_stack.pop(0)

    def undo(self):
        """Stellt den letzten gespeicherten Zustand wieder her."""
        if not self._undo_stack:
            return
        snap = self._undo_stack.pop()
        self._annotations = [self._anno_from_dict(d) for d in snap.annotations]
        self._current_anno = None
        self.update()

    def _undo_stack_to_list(self) -> list:
        """Serialisiert den Undo-Stack für JSON."""
        return [
            {"annotations": snap.annotations}
            for snap in self._undo_stack
        ]

    def _undo_stack_from_list(self, data: list):
        """Stellt den Undo-Stack aus JSON-Daten wieder her."""
        self._undo_stack = []
        for entry in data:
            snap = _CellSnapshot(annotations=entry.get("annotations", []))
            self._undo_stack.append(snap)

    # -----------------------------------------------------------------------
    # Style / state
    # -----------------------------------------------------------------------
    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        try:
            self._overlay.resize(self.size())
        except Exception:
            pass

    def _apply_style(self):
        c  = self._C_ACTIVE if self._active else self._C_INACTIVE
        bw = 3 if self._active else 1
        self.setStyleSheet(
            f"QFrame {{ border: {bw}px solid {c}; background: {self._C_BG}; }}"
        )

    def set_active(self, active: bool):
        if self._active == active:
            return
        self._active = active
        self._apply_style()
        self.update()

    def set_whiteboard(self, enabled: bool):
        self._load_token += 1
        self._whiteboard  = enabled
        self._meta        = None
        self._pixmap      = None
        self._loading     = False
        self._annotations.clear()
        self._current_anno = None
        self._undo_stack.clear()
        self._pan_offset  = QPoint(0, 0)
        self._zoom        = 1.0
        self.update()

    def set_image(self, meta: Optional[Dict]):
        self._load_token += 1
        load_token = self._load_token
        self._meta       = meta
        self._pixmap     = None
        self._zoom       = 1.0
        self._pan_offset = QPoint(0, 0)
        self._loading    = False
        self._rotation   = 0
        self._whiteboard = False
        self._vk4_channel = ""
        self._annotations.clear()
        self._current_anno = None
        self._undo_stack.clear()
        if meta:
            path = _build_full_path(meta)
            self._loading = True
            is_doc = _is_word(path) or _is_pdf(path) or _is_excel(path)
            if is_doc:
                label = ("Word wird geladen..." if _is_word(path)
                         else "PDF wird geladen..." if _is_pdf(path)
                         else "Excel wird geladen...")
                self._overlay.resize(self.size())
                self._overlay.start(label)
            request_meta = {
                "meta": meta,
                "load_token": load_token,
                "rotation": self._rotation,
            }
            if is_doc:
                # Dokumente: direkt Render-Worker starten (kein Umweg über _PixmapLoader)
                rsigs = _RenderSignals()
                self._rsigs = rsigs
                rsigs.done.connect(self._on_render_done)
                _pool.start(_RenderWorker(path, request_meta, rsigs))
            else:
                # Bilder/VK4: bestehender Pfad über _PixmapLoader
                sigs = _PixmapSignals()
                self._sigs = sigs
                sigs.done.connect(self._on_path_verified)
                _pool.start(_PixmapLoader(path, request_meta, sigs))
        self.update()

    def _on_render_done(self, pm, err: Optional[str], request_meta: Optional[dict]):
        """Callback wenn _RenderWorker fertig ist (PDF/Excel/Word)."""
        request_meta = request_meta or {}
        if request_meta.get("load_token") != self._load_token:
            self._overlay.stop()
            return
        meta = request_meta.get("meta")
        if meta is not self._meta:
            self._overlay.stop()
            return
        self._loading = False
        if pm is None:
            self._overlay.stop()
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Ladefehler", err or "Unbekannter Fehler.")
            self.update()
            return
        rotation = int(request_meta.get("rotation") or 0)
        self._pixmap = _apply_rotation(pm, rotation) if rotation else pm
        self._overlay.finish()
        self.update()

    def _on_path_verified(self, path: Optional[str], request_meta: Optional[Dict]):
        request_meta = request_meta or {}
        if request_meta.get("load_token") != self._load_token:
            return

        self._loading = False
        meta = request_meta.get("meta")
        if meta is not self._meta:
            return

        if path and meta is not None:
            vk4_ch      = request_meta.get("vk4_channel", "")
            pdf_page    = int(meta.get("_pdf_page")    or 0)
            excel_sheet = int(meta.get("_excel_sheet") or 0)
            word_page   = int(meta.get("_word_page")   or 0)
            if not vk4_ch and _is_vk4(path):
                chs = _vk4_available_channels(path)
                vk4_ch = chs[0] if chs else ""
            self._vk4_channel = vk4_ch
            pm = _make_pixmap(path, vk4_channel=vk4_ch,
                              pdf_page=pdf_page,
                              excel_sheet=excel_sheet,
                              word_page=word_page)
            rotation = int(request_meta.get("rotation") or 0)
            self._pixmap = _apply_rotation(pm, rotation) if pm else None
        else:
            self._pixmap = None
        self.update()

    def switch_vk4_channel(self, channel: str):
        """Lädt einen anderen VK4-Kanal und zeigt ihn an."""
        if not self._meta:
            return
        path = _build_full_path(self._meta)
        pm = _make_pixmap(path, vk4_channel=channel)
        if pm is None:
            return
        self._vk4_channel = channel
        self._pixmap = _apply_rotation(pm, self._rotation) if self._rotation else pm
        self.update()

    def clear_image(self):
        self.set_image(None)

    def clear_annotations(self):
        self.push_undo()
        self._annotations.clear()
        self._current_anno = None
        self.update()

    # Legacy-Methode (wird von _CompareGrid.undo_last_annotation nicht mehr genutzt,
    # aber der Name könnte noch woanders referenziert werden)
    def undo_last_annotation(self):
        """Macht die letzte Annotation in der aktiven Zelle rückgängig."""
        self.undo()

    def _erase_at(self, pos: QPoint):
        """Remove annotations whose hit-area overlaps pos."""
        import math
        HIT = _ERASER_RADIUS

        def hits(anno: Annotation) -> bool:
            pts = [self._to_screen(rx, ry) for rx, ry in anno.points]
            if not pts:
                return False
            for sp in pts:
                if math.hypot(sp.x() - pos.x(), sp.y() - pos.y()) <= HIT:
                    return True
            if len(pts) >= 2:
                xs = [p.x() for p in pts]
                ys = [p.y() for p in pts]
                cx = sum(xs) / len(xs)
                cy = sum(ys) / len(ys)
                if math.hypot(cx - pos.x(), cy - pos.y()) <= HIT:
                    return True
            return False

        new_list = [a for a in self._annotations if not hits(a)]
        if len(new_list) != len(self._annotations):
            self._annotations = new_list
            self.update()

    def _find_anno_at(self, pos: QPoint) -> Optional[Annotation]:
        """Return the topmost annotation within hit radius of pos, or None."""
        import math
        HIT = _ERASER_RADIUS

        def hits(anno: Annotation) -> bool:
            pts = [self._to_screen(rx, ry) for rx, ry in anno.points]
            if not pts:
                return False
            for sp in pts:
                if math.hypot(sp.x() - pos.x(), sp.y() - pos.y()) <= HIT:
                    return True
            if len(pts) >= 2:
                xs = [p.x() for p in pts]
                ys = [p.y() for p in pts]
                cx = sum(xs) / len(xs)
                cy = sum(ys) / len(ys)
                if math.hypot(cx - pos.x(), cy - pos.y()) <= HIT:
                    return True
            return False

        for anno in reversed(self._annotations):
            if hits(anno):
                return anno
        return None

    def render_to_pixmap(self) -> Optional[QPixmap]:
        """Return a flat QPixmap of the current image (or whiteboard) with annotations baked in."""
        if self._whiteboard:
            result = QPixmap(self.size())
            result.fill(QColor(255, 255, 255))
            p = QPainter(result)
            p.setRenderHint(QPainter.Antialiasing)
            for anno in self._annotations:
                self._draw_annotation(p, anno)
            p.end()
            return result
        if not self._pixmap or self._pixmap.isNull():
            return None
        result = self._pixmap.copy()
        p = QPainter(result)
        p.setRenderHint(QPainter.Antialiasing)
        ir = self._img_rect()
        if ir and ir.width() > 0 and ir.height() > 0:
            sx = result.width()  / ir.width()
            sy = result.height() / ir.height()
            p.scale(sx, sy)
            p.translate(-ir.x(), -ir.y())
        for anno in self._annotations:
            self._draw_annotation(p, anno)
        p.end()
        return result

    @property
    def meta(self) -> Optional[Dict]:
        return self._meta

    @property
    def index(self) -> int:
        return self._index

    # ---- coordinate helpers ----
    def _img_rect(self) -> Optional[QRect]:
        if self._whiteboard:
            return self.rect()
        if not self._pixmap or self._pixmap.isNull():
            return None
        r = self.rect()
        w, h = r.width(), r.height()
        pw, ph = self._pixmap.width(), self._pixmap.height()
        scale = min(w / pw, h / ph) * self._zoom
        dw = int(pw * scale)
        dh = int(ph * scale)
        x  = (w - dw) // 2 + self._pan_offset.x()
        y  = (h - dh) // 2 + self._pan_offset.y()
        return QRect(x, y, dw, dh)

    def _to_rel(self, pt: QPoint) -> Tuple[float, float]:
        ir = self._img_rect()
        if ir and ir.width() > 0 and ir.height() > 0:
            rx = (pt.x() - ir.x()) / ir.width()
            ry = (pt.y() - ir.y()) / ir.height()
        else:
            rx = pt.x() / max(self.width(), 1)
            ry = pt.y() / max(self.height(), 1)
        return rx, ry

    def _to_screen(self, rx: float, ry: float) -> QPoint:
        ir = self._img_rect()
        if ir and ir.width() > 0:
            x = int(ir.x() + rx * ir.width())
            y = int(ir.y() + ry * ir.height())
        else:
            x = int(rx * self.width())
            y = int(ry * self.height())
        return QPoint(x, y)

    # ---- paint ----
    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        w, h = r.width(), r.height()
        p.fillRect(r, QColor(self._C_BG))

        if self._pixmap and not self._pixmap.isNull():
            ir = self._img_rect()
            p.drawPixmap(ir, self._pixmap)

            # top label
            p.fillRect(QRect(0, 0, w, 20), QColor(0, 0, 0, 160))
            p.setPen(QColor(220, 220, 220))
            orig = (self._meta or {}).get("OriginalFilename") or ""
            sid  = (self._meta or {}).get("TrialSeriesID") or ""
            p.drawText(QRect(4, 2, w - 48, 16), Qt.AlignLeft | Qt.AlignVCenter, f"S{sid}  {orig}")
            p.setPen(QColor(255, 80, 80))
            p.drawText(QRect(w - 22, 2, 18, 16), Qt.AlignCenter, "\u2715")

            # Draw annotations
            all_annos = self._annotations + ([self._current_anno] if self._current_anno else [])
            for anno in all_annos:
                self._draw_annotation(p, anno)

        elif self._whiteboard:
            p.fillRect(r, QColor(255, 255, 255))
            p.fillRect(QRect(0, 0, w, 20), QColor(220, 220, 220))
            p.setPen(QColor(80, 80, 80))
            p.drawText(QRect(4, 2, w - 48, 16), Qt.AlignLeft | Qt.AlignVCenter, "Whiteboard")
            p.setPen(QColor(200, 50, 50))
            p.drawText(QRect(w - 22, 2, 18, 16), Qt.AlignCenter, "\u2715")
            # Draw annotations
            all_annos = self._annotations + ([self._current_anno] if self._current_anno else [])
            for anno in all_annos:
                self._draw_annotation(p, anno)

        elif self._loading:
            p.setPen(QColor(120, 120, 120))
            p.drawText(r, Qt.AlignCenter, "Loading\u2026")
        else:
            p.setPen(QColor(90, 90, 90))
            p.drawText(r, Qt.AlignCenter, f"({self._row + 1},{self._col + 1})\nDrop image here")

        if self._active:
            p.setPen(QPen(QColor(self._C_ACTIVE), 3))
            p.drawRect(r.adjusted(1, 1, -2, -2))

        # Grid overlay
        if self.grid_overlay and (self._pixmap or self._whiteboard):
            ir = self._img_rect() or r
            grid_pen = QPen(QColor(255, 255, 255, 90), 1, Qt.DashLine)
            p.setPen(grid_pen)
            n = self.grid_divisions
            for i in range(1, n):
                x = ir.x() + ir.width() * i // n
                p.drawLine(x, ir.y(), x, ir.y() + ir.height())
                y = ir.y() + ir.height() * i // n
                p.drawLine(ir.x(), y, ir.x() + ir.width(), y)

        p.end()

    def _draw_annotation(self, p: QPainter, anno: Annotation):
        if not anno.points:
            return
        if anno.tool in (TOOL_ARROW, TOOL_ELLIPSE, TOOL_RECT, TOOL_HIGHLIGHT) and len(anno.points) < 2:
            return
        p.save()
        color = ANNO_COLORS.get(anno.color, QColor(220, 50, 50))
        pen_w = getattr(anno, "size", 2)
        pen = QPen(color, pen_w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        pts = [self._to_screen(rx, ry) for rx, ry in anno.points]

        if anno.tool == TOOL_ARROW and len(pts) >= 2:
            start, end = pts[0], pts[-1]
            p.drawLine(start, end)
            import math
            dx = end.x() - start.x()
            dy = end.y() - start.y()
            length = math.hypot(dx, dy)
            if length > 0:
                ux, uy = dx / length, dy / length
                size = 8 + pen_w * 3
                lx = end.x() - size * ux + size * 0.4 * uy
                ly = end.y() - size * uy - size * 0.4 * ux
                rx = end.x() - size * ux - size * 0.4 * uy
                ry2 = end.y() - size * uy + size * 0.4 * ux
                p.drawLine(end, QPoint(int(lx), int(ly)))
                p.drawLine(end, QPoint(int(rx), int(ry2)))

        elif anno.tool == TOOL_ELLIPSE and len(pts) >= 2:
            x1, y1 = pts[0].x(), pts[0].y()
            x2, y2 = pts[-1].x(), pts[-1].y()
            p.drawEllipse(QRect(min(x1, x2), min(y1, y2),
                                abs(x2 - x1), abs(y2 - y1)))

        elif anno.tool == TOOL_RECT and len(pts) >= 2:
            x1, y1 = pts[0].x(), pts[0].y()
            x2, y2 = pts[-1].x(), pts[-1].y()
            p.drawRect(QRect(min(x1, x2), min(y1, y2),
                             abs(x2 - x1), abs(y2 - y1)))

        elif anno.tool == TOOL_FREE and len(pts) >= 2:
            for i in range(len(pts) - 1):
                p.drawLine(pts[i], pts[i + 1])

        elif anno.tool == TOOL_HIGHLIGHT and len(pts) >= 2:
            x1, y1 = pts[0].x(), pts[0].y()
            x2, y2 = pts[-1].x(), pts[-1].y()
            hi_color = QColor(color)
            hi_color.setAlpha(60)
            p.save()
            p.setBrush(hi_color)
            p.setPen(Qt.NoPen)
            p.drawRect(QRect(min(x1, x2), min(y1, y2),
                             abs(x2 - x1), abs(y2 - y1)))
            p.restore()

        elif anno.tool == TOOL_TEXT and pts:
            p.setPen(color)
            font = QFont()
            font.setPointSize(8 + pen_w * 2)
            font.setBold(True)
            p.setFont(font)
            p.drawText(pts[0], anno.text)

        elif anno.tool == TOOL_MARKER and pts:
            p.setPen(color)
            font = QFont()
            font.setPointSize(10 + pen_w * 2)
            font.setBold(True)
            p.setFont(font)
            p.drawText(pts[0], anno.text)

        p.restore()

    # ---- context menu ----
    def _show_anno_context_menu(self, anno: Annotation, global_pos):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #2a2a2a; color: #eee; border: 1px solid #555; }"
            "QMenu::item:selected { background: #39A650; }"
            "QMenu::item { padding: 4px 18px; }"
            "QMenu::separator { background: #444; height: 1px; margin: 3px 0; }"
        )
        color_menu = menu.addMenu("🎨 Farbe")
        for cname in ANNO_COLORS:
            act = color_menu.addAction(cname.capitalize())
            act.setCheckable(True)
            act.setChecked(anno.color == cname)
            act.triggered.connect(lambda checked, c=cname: (setattr(anno, "color", c), self.update()))
        size_menu = menu.addMenu("📏 Thickness")
        for sz, label in [(2, "Thin"), (4, "Medium"), (8, "Thick")]:
            act = size_menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(anno.size == sz)
            act.triggered.connect(lambda checked, s=sz: (setattr(anno, "size", s), self.update()))
        menu.addSeparator()
        del_act = menu.addAction("🗑  Delete")
        del_act.triggered.connect(lambda: (self._annotations.remove(anno), self.update()) if anno in self._annotations else None)
        menu.exec(global_pos)

    # ---- mouse ----
    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            # check × button
            if self._pixmap or self._whiteboard:
                r = self.rect()
                if QRect(r.width() - 22, 2, 20, 18).contains(ev.pos()):
                    if self._whiteboard:
                        self.set_whiteboard(False)
                    else:
                        self.clear_image()
                    return

            self.clicked.emit(self._index)

            if self.active_tool == TOOL_PAN:
                self._drag_start = ev.pos()
                self._pan_start  = ev.pos()
                self._pan_snap   = QPoint(self._pan_offset)

            elif self.active_tool == TOOL_TEXT:
                text, ok = QInputDialog.getText(self, "Annotation", "Text:")
                if ok and text.strip():
                    self.push_undo()
                    rx, ry = self._to_rel(ev.pos())
                    anno = Annotation(tool=TOOL_TEXT, color=self.active_color,
                                      points=[(rx, ry)], text=text.strip(),
                                      size=self.active_size)
                    self._annotations.append(anno)
                    self.update()

            elif self.active_tool == TOOL_ERASER:
                self.push_undo()
                self._erase_at(ev.pos())

            elif self.active_tool == TOOL_MOVE:
                hit = self._find_anno_at(ev.pos())
                if hit is not None:
                    self.push_undo()
                    self._move_anno  = hit
                    self._move_start = ev.pos()

            elif self.active_tool == TOOL_MARKER:
                self.push_undo()
                rx, ry = self._to_rel(ev.pos())
                n = sum(1 for a in self._annotations if a.tool == TOOL_MARKER)
                char = _MARKER_CHARS[n % len(_MARKER_CHARS)]
                anno = Annotation(tool=TOOL_MARKER, color=self.active_color,
                                  points=[(rx, ry)], text=char,
                                  size=self.active_size)
                self._annotations.append(anno)
                self.update()

            else:
                # Start drawing — Undo-Snapshot erst bei mouseRelease (nach Abschluss des Strichs)
                rx, ry = self._to_rel(ev.pos())
                self._current_anno = Annotation(
                    tool=self.active_tool,
                    color=self.active_color,
                    points=[(rx, ry)],
                    size=self.active_size,
                )

        if ev.button() == Qt.RightButton and self.active_tool == TOOL_MOVE:
            hit = self._find_anno_at(ev.pos())
            if hit is not None:
                self._show_anno_context_menu(hit, ev.globalPos())
                return

        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if self.active_tool == TOOL_MOVE and not (ev.buttons() & Qt.LeftButton):
            hit = self._find_anno_at(ev.pos())
            self.setCursor(Qt.SizeAllCursor if hit else Qt.ArrowCursor)

        if not (ev.buttons() & Qt.LeftButton):
            return

        if self.active_tool == TOOL_PAN:
            if self._zoom > 1.01 and self._pan_start is not None:
                delta = ev.pos() - self._pan_start
                self._pan_offset = self._pan_snap + delta
                self.update()
                return
            if (self._meta is not None
                    and self._drag_start is not None
                    and (ev.pos() - self._drag_start).manhattanLength() >= 8):
                drag = QDrag(self)
                mime = QMimeData()
                mime.setText(f"{_MIME_FRAME}{self._index}")
                drag.setMimeData(mime)
                if self._pixmap and not self._pixmap.isNull():
                    pm = self._pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    drag.setPixmap(pm)
                    drag.setHotSpot(QPoint(32, 32))
                drag.exec(Qt.MoveAction)
                self._drag_start = None
                self._pan_start  = None
        else:
            if self.active_tool == TOOL_ERASER:
                self._erase_at(ev.pos())
                return
            if self.active_tool == TOOL_MOVE:
                if self._move_anno is not None and self._move_start is not None:
                    delta = ev.pos() - self._move_start
                    ir = self._img_rect()
                    if ir and ir.width() > 0 and ir.height() > 0:
                        drx = delta.x() / ir.width()
                        dry = delta.y() / ir.height()
                    else:
                        drx = delta.x() / max(self.width(), 1)
                        dry = delta.y() / max(self.height(), 1)
                    self._move_anno.points = [
                        (ox + drx, oy + dry) for ox, oy in self._move_anno.points
                    ]
                    self._move_start = ev.pos()
                    self.update()
                return
            if self._current_anno is not None:
                rx, ry = self._to_rel(ev.pos())
                if self.active_tool == TOOL_FREE:
                    self._current_anno.points.append((rx, ry))
                else:
                    if len(self._current_anno.points) > 1:
                        self._current_anno.points[-1] = (rx, ry)
                    else:
                        self._current_anno.points.append((rx, ry))
                self.update()

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            if self.active_tool != TOOL_PAN and self._current_anno is not None:
                if len(self._current_anno.points) >= 2 or self._current_anno.tool == TOOL_FREE:
                    self.push_undo()
                    self._annotations.append(self._current_anno)
                self._current_anno = None
                self.update()
        self._pan_start  = None
        self._drag_start = None
        self._move_anno  = None
        self._move_start = None
        super().mouseReleaseEvent(ev)

    def mouseDoubleClickEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            if self.active_tool == TOOL_MOVE:
                hit = self._find_anno_at(ev.pos())
                if hit is not None and hit.tool == TOOL_TEXT:
                    from PySide6.QtWidgets import QSpinBox, QDialog, QDialogButtonBox, QFormLayout
                    dlg = QDialog(self)
                    dlg.setWindowTitle("Text size")
                    spin = QSpinBox()
                    spin.setRange(6, 72)
                    spin.setValue(hit.size)
                    spin.setSuffix(" pt")
                    form = QFormLayout(dlg)
                    form.addRow("Size:", spin)
                    btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                    btns.accepted.connect(dlg.accept)
                    btns.rejected.connect(dlg.reject)
                    form.addRow(btns)
                    if dlg.exec() == QDialog.Accepted:
                        hit.size = spin.value()
                        self.update()
                    return
            if self.active_tool == TOOL_PAN and self._meta is not None:
                self._rotation = (self._rotation + 90) % 360
                if self._pixmap:
                    self._pixmap = _apply_rotation(self._pixmap, 90)
                    self.update()
                if not (self._meta or {}).get("_local"):
                    _save_rotated_pixmap(self._pixmap, _build_full_path(self._meta))
        super().mouseDoubleClickEvent(ev)

    def leaveEvent(self, ev):
        self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(ev)

    def wheelEvent(self, ev):
        factor = 1.15 if ev.angleDelta().y() > 0 else (1.0 / 1.15)
        self._zoom = max(0.5, min(10.0, self._zoom * factor))
        self.update()

    def event(self, ev):
        if ev.type() == ev.Type.Gesture:
            return self._handle_gesture(ev)
        return super().event(ev)

    def _handle_gesture(self, ev):
        try:
            gesture = ev.gesture(Qt.PinchGesture)
            if gesture:
                state = gesture.state()
                if state == Qt.GestureState.GestureStarted:
                    self._pinch_zoom_start = self._zoom
                elif state in (Qt.GestureState.GestureUpdated, Qt.GestureState.GestureFinished):
                    scale = gesture.totalScaleFactor()
                    self._zoom = max(0.5, min(10.0, self._pinch_zoom_start * scale))
                    self.update()
        except Exception:
            pass
        return True

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_V and (ev.modifiers() & Qt.ControlModifier):
            clipboard = QGuiApplication.clipboard()
            pm = clipboard.pixmap()
            if not pm.isNull():
                self._whiteboard  = False
                self._meta        = {"OriginalFilename": "clipboard", "_local": True}
                self._pixmap      = pm
                self._zoom        = 1.0
                self._pan_offset  = QPoint(0, 0)
                self._annotations.clear()
                self._current_anno = None
                self._undo_stack.clear()
                self.update()
                return
        super().keyPressEvent(ev)

    def dragEnterEvent(self, ev):
        txt = ev.mimeData().text() if ev.mimeData().hasText() else ""
        if txt.startswith(_MIME_IMG) or txt.startswith(_MIME_FRAME):
            ev.acceptProposedAction()
            self.setStyleSheet("QFrame { border: 2px solid #ffa500; background: #252515; }")

    def dragLeaveEvent(self, _ev):
        self._apply_style()

    def dropEvent(self, ev):
        self._apply_style()
        txt = ev.mimeData().text() if ev.mimeData().hasText() else ""
        if txt:
            self.image_dropped.emit(self._index, txt)
            ev.acceptProposedAction()


# ---------------------------------------------------------------------------
# Compare grid
# ---------------------------------------------------------------------------

class _CompareGrid(QWidget):
    """Raster-Widget das mehrere _FrameCell-Widgets in einem konfigurierbaren Grid anzeigt.

    Unterstützt 1x1 bis 2x2 Layouts. Die aktive Zelle wird grün hervorgehoben.
    Verwaltet Annotationen und Drag-and-Drop zwischen Zellen.
    """
    active_frame_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._cols = 2
        self._rows = 2
        self._cells: List[_FrameCell] = []
        self._active_idx: Optional[int] = None
        self._lay: Optional[QGridLayout] = None
        self.on_list_drop = None
        self._build()

    def set_grid(self, cols: int, rows: int):
        """Konfiguriert das Raster auf cols×rows Zellen und baut es neu auf."""
        cols = max(1, min(10, cols))
        rows = max(1, min(10, rows))
        old = {i: c.meta for i, c in enumerate(self._cells)}
        self._cols = cols
        self._rows = rows
        self._build()
        for i, cell in enumerate(self._cells):
            if old.get(i) is not None:
                cell.set_image(old[i])
        self._active_idx = None

    def _build(self):
        """Erstellt die Zellen und verbindet deren Signale."""
        for cell in self._cells:
            if self._lay is not None:
                self._lay.removeWidget(cell)
            cell.hide()
            cell.deleteLater()
        self._cells.clear()

        if self._lay is None:
            lay = QGridLayout(self)
            lay.setContentsMargins(4, 4, 4, 4)
            lay.setSpacing(6)
            self._lay = lay
        else:
            lay = self._lay
            for i in range(10):
                lay.setRowStretch(i, 0)
                lay.setColumnStretch(i, 0)

        for r in range(self._rows):
            lay.setRowStretch(r, 1)
        for c in range(self._cols):
            lay.setColumnStretch(c, 1)

        for r in range(self._rows):
            for c in range(self._cols):
                cell = _FrameCell(r, c)
                cell.clicked.connect(self._on_cell_clicked)
                cell.image_dropped.connect(self._on_drop)
                lay.addWidget(cell, r, c)
                self._cells.append(cell)

    def set_tool(self, tool: str, color: str, size: int = 2):
        """Setzt das aktive Annotations-Tool auf allen Zellen."""
        for cell in self._cells:
            cell.active_tool  = tool
            cell.active_color = color
            cell.active_size  = size

    def clear_all_annotations(self):
        """Löscht alle Annotationen in allen Zellen."""
        for cell in self._cells:
            cell.clear_annotations()

    def undo_last_annotation(self):
        """Undo auf der aktiven Cell."""
        if self._active_idx is not None:
            for cell in self._cells:
                if cell.index == self._active_idx:
                    cell.undo()
                    return

    def _on_cell_clicked(self, idx: int):
        """Setzt die angeklickte Zelle als aktiv."""
        self._set_active(idx)

    def _set_active(self, idx: int):
        """Markiert Zelle idx als aktiv (grüner Rahmen), alle anderen inaktiv."""
        self._active_idx = idx
        for cell in self._cells:
            cell.set_active(cell.index == idx)
        self.active_frame_changed.emit(idx)

    def assign_to_active(self, meta: Dict):
        """Weist ein Bild/Dokument der aktiven Zelle zu und wechselt zur nächsten."""
        if self._active_idx is None and self._cells:
            self._set_active(self._cells[0].index)
        if self._active_idx is None:
            return
        for cell in self._cells:
            if cell.index == self._active_idx:
                cell.set_image(meta)
                self._advance_active()
                return

    def _advance_active(self):
        """Wechselt zur nächsten leeren Zelle (für sequentielles Zuweisen)."""
        if self._active_idx is None:
            return
        pos = next((i for i, c in enumerate(self._cells) if c.index == self._active_idx), None)
        if pos is None:
            return
        n = len(self._cells)
        for off in range(1, n):
            cand = self._cells[(pos + off) % n]
            if cand.meta is None:
                self._set_active(cand.index)
                return

    def _on_drop(self, target_idx: int, mime_text: str):
        """Verarbeitet einen Drag-and-Drop von der Liste in eine Zelle."""
        if mime_text.startswith(_MIME_FRAME):
            try:
                src_idx = int(mime_text[len(_MIME_FRAME):])
            except ValueError:
                return
            src = next((c for c in self._cells if c.index == src_idx), None)
            tgt = next((c for c in self._cells if c.index == target_idx), None)
            if src and tgt:
                sm, tm = src.meta, tgt.meta
                src.set_image(tm)
                tgt.set_image(sm)
            self._set_active(target_idx)
        elif mime_text.startswith(_MIME_IMG):
            if callable(self.on_list_drop):
                self.on_list_drop(target_idx, mime_text)
            self._set_active(target_idx)

    def active_label(self) -> str:
        """Gibt den Label-Text der aktiven Zelle zurück."""
        if self._active_idx is None:
            return "\u2013"
        r = self._active_idx // 100
        c = self._active_idx % 100
        return f"({r + 1},{c + 1})"

    def active_cell(self) -> Optional["_FrameCell"]:
        """Gibt die aktive Zelle zurück, oder None wenn keine aktiv ist."""
        if self._active_idx is None:
            return None
        return next((c for c in self._cells if c.index == self._active_idx), None)

    def save_project(self, path: str):
        """Speichert Grid-Layout, Bilder, Rotationen, Annotationen und Undo-Stack als JSON."""
        frames = []
        for cell in self._cells:
            annos = [cell._anno_to_dict(a) for a in cell._annotations]
            meta = cell._meta or {}
            frames.append({
                "index":      cell.index,
                "row":        cell._row,
                "col":        cell._col,
                "whiteboard": cell._whiteboard,
                "rotation":   cell._rotation,
                "zoom":       cell._zoom,
                "pan_x":      cell._pan_offset.x(),
                "pan_y":      cell._pan_offset.y(),
                "image_path":  _build_full_path(meta) if meta else "",
                "is_local":    bool(meta.get("_local")),
                "label":       str(meta.get("OriginalFilename") or ""),
                "vk4_channel": getattr(cell, "_vk4_channel", ""),
                "annotations": annos,
                "undo_stack":  cell._undo_stack_to_list(),
            })
        project = {
            "version": 2,
            "cols":    self._cols,
            "rows":    self._rows,
            "frames":  frames,
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(project, fh, ensure_ascii=False, indent=2)

    def load_project(self, path: str):
        """Lädt ein .ttcompare-Projekt und stellt Bilder, Annotationen und Layout wieder her."""
        """Laedt ein gespeichertes Projekt und stellt alle Frames wieder her."""
        with open(path, "r", encoding="utf-8") as fh:
            project = json.load(fh)

        cols = project.get("cols", 2)
        rows = project.get("rows", 2)
        self.set_grid(cols, rows)

        missing = []
        for fd in project.get("frames", []):
            cell = next((c for c in self._cells if c.index == fd["index"]), None)
            if cell is None:
                continue

            if fd.get("whiteboard"):
                cell.set_whiteboard(True)
            else:
                img_path = fd.get("image_path", "")
                if img_path and os.path.isfile(img_path):
                    is_local = fd.get("is_local", False)
                    meta = {
                        "OriginalFilename": fd.get("label", os.path.basename(img_path)),
                        "FullPath":         img_path,
                        "_local":           True,
                    } if is_local else {
                        "OriginalFilename": fd.get("label", ""),
                        "RelativePath":     os.path.dirname(img_path),
                        "StoredFilename":   os.path.basename(img_path),
                    }
                    cell.set_image(meta)
                    cell._rotation   = fd.get("rotation", 0)
                    # VK4-Kanal nach set_image wiederherstellen (set_image setzt ihn zurück)
                    saved_ch = fd.get("vk4_channel", "")
                    if saved_ch and _is_vk4(img_path):
                        cell.switch_vk4_channel(saved_ch)
                elif img_path:
                    missing.append(img_path)

            cell._zoom       = float(fd.get("zoom", 1.0))
            cell._pan_offset = QPoint(int(fd.get("pan_x", 0)), int(fd.get("pan_y", 0)))

            # Annotationen wiederherstellen (set_image löscht sie, daher nach set_image)
            cell._annotations.clear()
            for ad in fd.get("annotations", []):
                cell._annotations.append(cell._anno_from_dict(ad))
            cell.update()

            # Undo-Stack wiederherstellen (version 2; Fallback auf leeren Stack)
            cell._undo_stack_from_list(fd.get("undo_stack", []))

        return missing

    def render_all_to_pixmap(self) -> Optional[QPixmap]:
        """Rendert alle Zellen als zusammengesetztes QPixmap (für «Save All»)."""
        """Rendert alle eingeblendeten Frames zu einem einzigen zusammengesetzten Bild."""
        cells_with_content = [c for c in self._cells if c._pixmap or c._whiteboard]
        if not cells_with_content:
            return None

        cols = self._cols
        rows = self._rows
        cell_w = max((c.width() for c in self._cells), default=400)
        cell_h = max((c.height() for c in self._cells), default=300)
        total_w = cols * cell_w
        total_h = rows * cell_h

        result = QPixmap(total_w, total_h)
        result.fill(QColor(30, 30, 30))
        painter = QPainter(result)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)

        for cell in self._cells:
            pm = cell.render_to_pixmap()
            if pm is None or pm.isNull():
                continue
            dest_x = cell._col * cell_w
            dest_y = cell._row * cell_h
            scaled = pm.scaled(cell_w, cell_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            ox = (cell_w - scaled.width())  // 2
            oy = (cell_h - scaled.height()) // 2
            painter.drawPixmap(dest_x + ox, dest_y + oy, scaled)

        painter.end()
        return result


# ---------------------------------------------------------------------------
# Main screen
# ---------------------------------------------------------------------------

class ImageCompareScreen(QWidget):
    """Hauptscreen für den Bildvergleich.

    Enthält Bild-Liste (links), Annotations-Toolbar (oben), Vergleichsraster (rechts)
    und VK4-Kanal-Toggle-Toolbar.
    """
    def __init__(self, on_back_home=None, parent: QWidget | None = None):
        super().__init__(parent)
        self._on_back_home = on_back_home
        self._active_tool  = TOOL_PAN
        self._active_color = "red"
        self._active_size  = 2
        self._build_ui()

    def _build_ui(self):
        """Erstellt Header, Toolbar, Splitter (Liste | Grid) und Footer."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = HeaderBar(title="Image Compare", show_home=True)
        header.connect_home(self._go_home)
        root.addWidget(header)

        root.addWidget(self._build_toolbar())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(5)

        self._panel = _ImageListPanel()
        self._panel.setMinimumWidth(200)
        self._panel.setMaximumWidth(340)
        self._panel.image_selected.connect(self._on_image_selected)
        self._panel.whiteboard_requested.connect(self._on_whiteboard_requested)
        splitter.addWidget(self._panel)

        self._grid = _CompareGrid()
        self._grid.on_list_drop = self._on_list_drop
        self._grid.active_frame_changed.connect(self._on_active_changed)
        splitter.addWidget(self._grid)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 900])

        root.addWidget(splitter, 1)
        root.addWidget(FooterBar())
        self._update_active_label()

    def _build_toolbar(self) -> QFrame:
        """Erstellt die Annotations-Toolbar (Tools, Farben, Grössen, Grid, Save, Projekt)."""
        bar = QFrame()
        bar.setFixedHeight(48)
        bar.setObjectName("ToolBar")
        bar.setStyleSheet("QFrame#ToolBar { background: #2a2a2a; border-bottom: 1px solid #444; }")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 4, 10, 4)
        lay.setSpacing(6)

        # --- Grid controls ---
        lay.addWidget(QLabel("Grid:", styleSheet="color:#ccc; font-size:12px;"))

        self._spin_cols = QSpinBox()
        self._spin_cols.setRange(1, 10)
        self._spin_cols.setValue(2)
        self._spin_cols.setPrefix("Cols: ")
        self._spin_cols.setFixedWidth(82)
        lay.addWidget(self._spin_cols)

        lay.addWidget(QLabel("×", styleSheet="color:#ccc;"))

        self._spin_rows = QSpinBox()
        self._spin_rows.setRange(1, 10)
        self._spin_rows.setValue(2)
        self._spin_rows.setPrefix("Rows: ")
        self._spin_rows.setFixedWidth(86)
        lay.addWidget(self._spin_rows)

        btn_apply = QPushButton("Apply")
        btn_apply.setObjectName("GreenBtn")
        btn_apply.setFixedHeight(28)
        btn_apply.setFixedWidth(60)
        btn_apply.clicked.connect(self._apply_grid)
        lay.addWidget(btn_apply)

        lay.addSpacing(10)
        lay.addWidget(QLabel("Active frame:", styleSheet="color:#ccc; font-size:12px;"))
        self._lbl_active = QLabel("–")
        self._lbl_active.setStyleSheet("color:#39A650; font-size:13px; font-weight:bold; min-width:42px;")
        lay.addWidget(self._lbl_active)

        lay.addSpacing(4)
        self._lbl_tool = QLabel("🖐 Pan")
        self._lbl_tool.setStyleSheet("color:#aaa; font-size:11px; min-width:80px;")
        lay.addWidget(self._lbl_tool)

        # --- Separator ---
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #555;")
        lay.addWidget(sep)

        # --- Tool buttons ---
        self._tool_btns: Dict[str, QPushButton] = {}
        tools = [
            (TOOL_PAN,       "🖐",  "Pan / Zoom (no annotation)"),
            (TOOL_ARROW,     "↗",  "Arrow"),
            (TOOL_ELLIPSE,   "⬭",  "Ellipse"),
            (TOOL_RECT,      "▭",  "Rectangle"),
            (TOOL_FREE,      "✏️", "Freehand"),
            (TOOL_TEXT,      "T",   "Text label"),
            (TOOL_HIGHLIGHT, "🖊",  "Highlight – semi-transparent fill"),
            (TOOL_MARKER,    "①",  "Numbered marker – auto-increments"),
            (TOOL_ERASER,    "⌫",  "Eraser – click/drag to delete annotations"),
            (TOOL_MOVE,      "⤢",  "Move – drag to reposition / right-click to edit"),
        ]
        for tool_id, icon, tip in tools:
            btn = QPushButton(icon)
            btn.setToolTip(tip)
            btn.setFixedSize(34, 34)
            btn.setCheckable(True)
            btn.setChecked(tool_id == TOOL_PAN)
            btn.setObjectName("ToolBtnActive" if tool_id == TOOL_PAN else "ToolBtnInactive")
            btn.setStyleSheet(self._tool_btn_style(tool_id == TOOL_PAN))
            btn.clicked.connect(lambda checked, t=tool_id: self._select_tool(t))
            lay.addWidget(btn)
            self._tool_btns[tool_id] = btn

        # --- Separator ---
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet("color: #555;")
        lay.addWidget(sep2)

        # --- Color buttons ---
        self._color_btns: Dict[str, QPushButton] = {}
        colors = [("red", "#DC3232"), ("yellow", "#F0C800"), ("green", "#32C850"), ("white", "#FFFFFF"), ("blue", "#3282DC")]
        for color_id, hex_c in colors:
            btn = QPushButton()
            btn.setFixedSize(22, 22)
            btn.setCheckable(True)
            btn.setChecked(color_id == "red")
            btn.setStyleSheet(
                f"QPushButton {{ background: {hex_c}; border-radius: 11px; border: 3px solid "
                + ("#fff" if color_id == "red" else "#555") + "; }"
            )
            btn.clicked.connect(lambda checked, c=color_id: self._select_color(c))
            lay.addWidget(btn)
            self._color_btns[color_id] = btn

        # --- Separator ---
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.VLine)
        sep3.setStyleSheet("color: #555;")
        lay.addWidget(sep3)

        # --- Size buttons ---
        self._size_btns: Dict[int, QPushButton] = {}
        sizes = [(2, "—", "Thin"), (4, "━", "Medium"), (8, "▬", "Thick")]
        for sz, icon, tip in sizes:
            btn = QPushButton(icon)
            btn.setToolTip(tip)
            btn.setFixedSize(28, 28)
            btn.setCheckable(True)
            btn.setChecked(sz == 2)
            btn.setStyleSheet(self._size_btn_style(sz == 2))
            btn.clicked.connect(lambda checked, s=sz: self._select_size(s))
            lay.addWidget(btn)
            self._size_btns[sz] = btn

        sep4 = QFrame()
        sep4.setFrameShape(QFrame.VLine)
        sep4.setStyleSheet("color: #555;")
        lay.addWidget(sep4)

        # --- Undo / Clear ---
        btn_undo = QPushButton("↩ Undo")
        btn_undo.setFixedHeight(28)
        btn_undo.setToolTip("Undo last step in the active cell (max. 10)")
        btn_undo.setStyleSheet("QPushButton { background: #444; color: #ccc; border-radius: 3px; font-size: 11px; } QPushButton:hover { background: #555; }")
        btn_undo.clicked.connect(self._undo_annotation)
        lay.addWidget(btn_undo)

        btn_clear = QPushButton("🗑 Clear all")
        btn_clear.setFixedHeight(28)
        btn_clear.setStyleSheet("QPushButton { background: #5a1a1a; color: #f88; border-radius: 3px; font-size: 11px; } QPushButton:hover { background: #7a2a2a; }")
        btn_clear.clicked.connect(self._clear_annotations)
        lay.addWidget(btn_clear)

        sep_save = QFrame()
        sep_save.setFrameShape(QFrame.VLine)
        sep_save.setStyleSheet("color: #555;")
        lay.addWidget(sep_save)

        btn_save = QPushButton("💾 Save frame…")
        btn_save.setFixedHeight(28)
        btn_save.setToolTip("Save active frame (image + annotations) as image file")
        btn_save.setStyleSheet("QPushButton { background: #1a3a5a; color: #8cf; border-radius: 3px; font-size: 11px; } QPushButton:hover { background: #2a5a8a; }")
        btn_save.clicked.connect(self._save_active_frame)
        lay.addWidget(btn_save)

        btn_save_all = QPushButton("🖼 Save all…")
        btn_save_all.setFixedHeight(28)
        btn_save_all.setToolTip("Save all visible frames as one combined image")
        btn_save_all.setStyleSheet("QPushButton { background: #1a3a5a; color: #8cf; border-radius: 3px; font-size: 11px; } QPushButton:hover { background: #2a5a8a; }")
        btn_save_all.clicked.connect(self._save_all_frames)
        lay.addWidget(btn_save_all)

        sep_proj = QFrame()
        sep_proj.setFrameShape(QFrame.VLine)
        sep_proj.setStyleSheet("color: #555;")
        lay.addWidget(sep_proj)

        btn_proj_save = QPushButton("📁 Projekt speichern")
        btn_proj_save.setFixedHeight(28)
        btn_proj_save.setStyleSheet("QPushButton { background: #2a3a5a; color: #adf; border-radius: 3px; font-size: 11px; } QPushButton:hover { background: #3a5a8a; }")
        btn_proj_save.clicked.connect(self._save_project)
        lay.addWidget(btn_proj_save)

        btn_proj_load = QPushButton("📂 Projekt laden")
        btn_proj_load.setFixedHeight(28)
        btn_proj_load.setStyleSheet("QPushButton { background: #2a3a5a; color: #adf; border-radius: 3px; font-size: 11px; } QPushButton:hover { background: #3a5a8a; }")
        btn_proj_load.clicked.connect(self._load_project)
        lay.addWidget(btn_proj_load)

        sep_grid = QFrame()
        sep_grid.setFrameShape(QFrame.VLine)
        sep_grid.setStyleSheet("color: #555;")
        lay.addWidget(sep_grid)

        self._btn_grid = QPushButton("⊞ Grid")
        self._btn_grid.setFixedHeight(28)
        self._btn_grid.setCheckable(True)
        self._btn_grid.setToolTip("Toggle grid overlay")
        self._btn_grid.setStyleSheet(
            "QPushButton { background: #444; color: #ccc; border-radius: 3px; font-size: 11px; border: 2px solid #666; } "
            "QPushButton:checked { background: #39A650; color: white; border: 2px solid #fff; } "
            "QPushButton:hover { background: #555; }"
        )
        self._btn_grid.clicked.connect(self._toggle_grid)
        lay.addWidget(self._btn_grid)

        self._spin_grid = QSpinBox()
        self._spin_grid.setRange(2, 10)
        self._spin_grid.setValue(3)
        self._spin_grid.setPrefix("÷")
        self._spin_grid.setFixedWidth(52)
        self._spin_grid.setToolTip("Grid divisions")
        self._spin_grid.valueChanged.connect(self._set_grid_divisions)
        lay.addWidget(self._spin_grid)

        sep_vk4 = QFrame(); sep_vk4.setFrameShape(QFrame.VLine)
        sep_vk4.setStyleSheet("color:#555;")
        self._vk4_sep = sep_vk4
        lay.addWidget(self._vk4_sep)

        self._vk4_label = QLabel("VK4:")
        self._vk4_label.setStyleSheet("color:#aaa;font-size:11px;")
        lay.addWidget(self._vk4_label)

        self._vk4_btn_container = QWidget()
        self._vk4_btn_layout    = QHBoxLayout(self._vk4_btn_container)
        self._vk4_btn_layout.setContentsMargins(0,0,0,0)
        self._vk4_btn_layout.setSpacing(3)
        lay.addWidget(self._vk4_btn_container)
        self._vk4_btns: Dict[str, QPushButton] = {}

        self._vk4_sep.setVisible(False)
        self._vk4_label.setVisible(False)
        self._vk4_btn_container.setVisible(False)

        lay.addStretch(1)
        return bar

    def _tool_btn_style(self, active: bool) -> str:
        """Gibt den CSS-Stil für einen Tool-Button zurück (aktiv/inaktiv)."""
        if active:
            return ("QPushButton { background-color: #39A650 !important; color: white; "
                    "border-radius: 4px; font-size: 15px; font-weight: bold; "
                    "border: 3px solid #ffffff; padding: 0px; }"
                    "QPushButton:hover { background-color: #4ab862; }")
        return ("QPushButton { background-color: #555555; color: #eeeeee; "
                "border-radius: 4px; font-size: 15px; "
                "border: 2px solid #888888; padding: 0px; }"
                "QPushButton:hover { background-color: #666666; color: #ffffff; "
                "border: 2px solid #aaaaaa; }")

    def _size_btn_style(self, active: bool) -> str:
        """Gibt den CSS-Stil für einen Grössen-Button zurück (aktiv/inaktiv)."""
        if active:
            return ("QPushButton { background-color: #39A650; color: white; "
                    "border-radius: 4px; font-size: 13px; font-weight: bold; "
                    "border: 3px solid #ffffff; padding: 0px; }"
                    "QPushButton:hover { background-color: #4ab862; }")
        return ("QPushButton { background-color: #555555; color: #eeeeee; "
                "border-radius: 4px; font-size: 13px; "
                "border: 2px solid #888888; padding: 0px; }"
                "QPushButton:hover { background-color: #666666; }")

    def _select_tool(self, tool: str):
        """Setzt das aktive Annotations-Tool und aktualisiert die Toolbar-Buttons."""
        self._active_tool = tool
        tool_names = {
            TOOL_PAN: "🖐 Pan", TOOL_ARROW: "↗ Arrow",
            TOOL_ELLIPSE: "⬭ Ellipse", TOOL_RECT: "▭ Rectangle",
            TOOL_FREE: "✏ Freehand", TOOL_TEXT: "T Text",
            TOOL_HIGHLIGHT: "🖊 Highlight", TOOL_MARKER: "① Marker",
            TOOL_ERASER: "⌫ Eraser", TOOL_MOVE: "⤢ Move",
        }
        for tid, btn in self._tool_btns.items():
            active = tid == tool
            btn.setChecked(active)
            btn.setObjectName("ToolBtnActive" if active else "ToolBtnInactive")
            btn.setStyleSheet(self._tool_btn_style(active))
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        try:
            self._lbl_tool.setText(tool_names.get(tool, tool))
        except Exception:
            pass
        self._grid.set_tool(tool, self._active_color, self._active_size)

    def _select_color(self, color: str):
        """Setzt die aktive Annotations-Farbe und aktualisiert die Farbbuttons."""
        self._active_color = color
        hex_map = {"red": "#DC3232", "yellow": "#F0C800", "green": "#32C850", "white": "#FFFFFF", "blue": "#3282DC"}
        for cid, btn in self._color_btns.items():
            active = cid == color
            hex_c  = hex_map[cid]
            btn.setChecked(active)
            btn.setStyleSheet(
                f"QPushButton {{ background: {hex_c}; border-radius: 11px; border: 3px solid "
                + ("#fff" if active else "#555") + "; }"
            )
        self._grid.set_tool(self._active_tool, color, self._active_size)

    def _select_size(self, size: int):
        """Setzt die aktive Annotations-Strichstärke."""
        self._active_size = size
        for sz, btn in self._size_btns.items():
            btn.setChecked(sz == size)
            btn.setStyleSheet(self._size_btn_style(sz == size))
        self._grid.set_tool(self._active_tool, self._active_color, size)

    def _undo_annotation(self):
        """Macht die letzte Annotation in der aktiven Zelle rückgängig."""
        self._grid.undo_last_annotation()

    def _clear_annotations(self):
        """Löscht alle Annotationen in allen Zellen."""
        self._grid.clear_all_annotations()

    def _toggle_grid(self):
        """Schaltet das Overlay-Gitternetz ein/aus."""
        on = self._btn_grid.isChecked()
        for cell in self._grid._cells:
            cell.grid_overlay = on
            cell.update()

    def _set_grid_divisions(self, n: int):
        """Setzt die Anzahl Gitterteilungen."""
        for cell in self._grid._cells:
            cell.grid_divisions = n
            cell.update()

    def _apply_grid(self):
        """Wendet die Gitter-Einstellungen auf alle Zellen an."""
        self._grid.set_grid(self._spin_cols.value(), self._spin_rows.value())
        self._update_active_label()

    def _on_image_selected(self, meta: Dict):
        """Weist ein aus der Liste ausgewähltes Bild der aktiven Zelle zu."""
        self._grid.assign_to_active(meta)
        self._update_active_label()

    def _on_whiteboard_requested(self):
        """Weist der aktiven Zelle ein leeres Whiteboard zu."""
        cell = self._grid.active_cell()
        if cell is not None:
            cell.set_whiteboard(True)

    def _save_active_frame(self):
        """Speichert das Bild der aktiven Zelle als Datei."""
        cell = self._grid.active_cell()
        if cell is None:
            return
        pm = cell.render_to_pixmap()
        if pm is None:
            return
        meta = cell.meta or {}
        orig = str(meta.get("OriginalFilename") or "whiteboard")
        base, _ = os.path.splitext(orig)
        suggested = f"{base}_annotated.png"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save frame as…", suggested,
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp);;TIFF (*.tif *.tiff)",
        )
        if not path:
            return
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        fmt = {"jpg": "JPEG", "jpeg": "JPEG", "bmp": "BMP",
               "tif": "TIFF", "tiff": "TIFF"}.get(ext, "PNG")
        pm.save(path, fmt)

    def _on_list_drop(self, target_idx: int, mime_text: str):
        """Verarbeitet Drag-and-Drop aus der Bildliste."""
        img_id = mime_text[len(_MIME_IMG):]
        meta   = self._panel.get_meta_by_id(img_id)
        if meta is None:
            return
        tgt = next((c for c in self._grid._cells if c.index == target_idx), None)
        if tgt:
            tgt.set_image(meta)

    def _on_active_changed(self, _idx: int):
        """Callback wenn die aktive Zelle wechselt: aktualisiert Label und VK4-Toolbar."""
        self._update_active_label()
        self._update_vk4_toolbar()

    def _update_active_label(self):
        """Aktualisiert die Statusanzeige mit dem Label der aktiven Zelle."""
        try:
            self._lbl_active.setText(self._grid.active_label())
        except Exception:
            pass

    def _save_all_frames(self):
        """Speichert alle Zellen als zusammengesetztes Bild."""
        pm = self._grid.render_all_to_pixmap()
        if pm is None or pm.isNull():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Nichts zu speichern", "Keine Bilder eingeblendet.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Alle Frames speichern als…", "alle_frames.png",
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp);;TIFF (*.tif *.tiff)",
        )
        if not path:
            return
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        fmt = {"jpg": "JPEG", "jpeg": "JPEG", "bmp": "BMP",
               "tif": "TIFF", "tiff": "TIFF"}.get(ext, "PNG")
        pm.save(path, fmt)

    def _save_project(self):
        """Öffnet einen Datei-Dialog und speichert das Projekt als .ttcompare."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Projekt speichern als…", "compare_projekt.ttcompare",
            "TrippleT Compare (*.ttcompare);;Alle Dateien (*.*)",
        )
        if not path:
            return
        try:
            self._grid.save_project(path)
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Fehler beim Speichern", str(e))

    def _load_project(self):
        """Öffnet einen Datei-Dialog und lädt ein .ttcompare-Projekt."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Projekt laden…", "",
            "TrippleT Compare (*.ttcompare);;Alle Dateien (*.*)",
        )
        if not path:
            return
        try:
            missing = self._grid.load_project(path)
            if missing:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self, "Fehlende Bilder",
                    "Folgende Bilddateien wurden nicht gefunden:\n\n" + "\n".join(missing),
                )
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Fehler beim Laden", str(e))

    def _update_vk4_toolbar(self):
        """Zeigt/versteckt die VK4-Kanal-Buttons je nach selektiertem Bild."""
        """Zeigt/versteckt den VK4-Kanal-Toggle abhängig von der aktiven Zelle."""
        cell = self._grid.active_cell()
        if cell is None:
            self._vk4_sep.setVisible(False)
            self._vk4_label.setVisible(False)
            self._vk4_btn_container.setVisible(False)
            return
        meta = cell.meta
        if meta is None:
            self._vk4_sep.setVisible(False)
            self._vk4_label.setVisible(False)
            self._vk4_btn_container.setVisible(False)
            return
        path = _build_full_path(meta)
        if not _is_vk4(path):
            self._vk4_sep.setVisible(False)
            self._vk4_label.setVisible(False)
            self._vk4_btn_container.setVisible(False)
            return
        channels = _vk4_available_channels(path)
        if len(channels) < 2:
            self._vk4_sep.setVisible(False)
            self._vk4_label.setVisible(False)
            self._vk4_btn_container.setVisible(False)
            return
        # Buttons neu aufbauen wenn nötig
        if list(self._vk4_btns.keys()) != channels:
            for btn in self._vk4_btns.values():
                self._vk4_btn_layout.removeWidget(btn)
                btn.deleteLater()
            self._vk4_btns = {}
            for ch in channels:
                btn = QPushButton(VK4_CH_LABELS[ch])
                btn.setFixedHeight(26)
                btn.setCheckable(True)
                btn.setStyleSheet(
                    "QPushButton{background:#444;color:#ccc;border-radius:3px;font-size:10px;"
                    "border:1px solid #666;}QPushButton:checked{background:#39A650;color:#fff;"
                    "border:1px solid #fff;}QPushButton:hover{background:#555;}")
                btn.clicked.connect(lambda c, channel=ch: self._switch_vk4_channel(channel))
                self._vk4_btn_layout.addWidget(btn)
                self._vk4_btns[ch] = btn
        # Aktiven Kanal markieren
        active_ch = getattr(cell, "_vk4_channel", "")
        for ch, btn in self._vk4_btns.items():
            btn.setChecked(ch == active_ch)
        self._vk4_sep.setVisible(True)
        self._vk4_label.setVisible(True)
        self._vk4_btn_container.setVisible(True)

    def _switch_vk4_channel(self, channel: str):
        """Wechselt den angezeigten VK4-Kanal der aktiven Zelle."""
        """Schaltet den VK4-Kanal der aktiven Zelle um."""
        cell = self._grid.active_cell()
        if cell is None:
            return
        cell.switch_vk4_channel(channel)
        self._update_vk4_toolbar()

    def _go_home(self):
        """Navigiert zurück zum Home-Screen."""
        if callable(self._on_back_home):
            self._on_back_home()

    def showEvent(self, ev):
        """Lädt die Bildliste beim ersten Öffnen des Screens."""
        super().showEvent(ev)
        try:
            if not self._panel._series_groups:
                QTimer.singleShot(150, self._panel.load_images)
        except Exception:
            pass