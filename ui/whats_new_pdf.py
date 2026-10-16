"""whats_new_pdf.py - one "What's new" version as PDF (button "PDF" in the
What's new window, ui/whats_new.py), Nutzerwunsch 2026-10-16.

A4 portrait; page 1 with the "Fresh off the Spool" logo as masthead
(subtitle, version, date next to it), the other pages with a small header
(name + version); the feature cards as in the window
(text left, sketch right, green bar). A section (heading + its cards) never
breaks across pages: it starts on a new page if it doesn't fit (KeepTogether).
Only a section taller than a whole page is split - and then between cards,
never inside one.

Font: Segoe UI from the Windows font folder (has the "→" of the "Where:" lines
and all ES/DE characters), else Arial, else Helvetica with "→" as "->".
Sketches: the SVGs are rendered by Qt (QSvgRenderer) to PNG at 4x - svglib is
not a dependency. Needs a QGuiApplication (always there inside the app).
"""
from __future__ import annotations

import io
import os
import re
from typing import Dict, Optional, Tuple

from ui.widgets.whats_new_texts import RELEASES, SUBTITLE, VERSION_LABEL, WHERE_LABEL, WINDOW_TITLE
from ui.widgets.friendly_error import show_error

ACCENT = "#39A650"
NAVY = "#1D3557"
SKETCH_SCALE = 4

_FONTS: Optional[Tuple[str, str, bool]] = None


def _fonts() -> Tuple[str, str, bool]:
    """(regular, bold, unicode_ok) - registered once."""
    global _FONTS
    if _FONTS is not None:
        return _FONTS
    from reportlab.lib.fonts import addMapping
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    font_dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    for name, regular, bold, italic in (("SegoeUI", "segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf"),
                                        ("Arial", "arial.ttf", "arialbd.ttf", "ariali.ttf")):
        files = [os.path.join(font_dir, f) for f in (regular, bold, italic)]
        if not all(os.path.isfile(f) for f in files):
            continue
        try:
            pdfmetrics.registerFont(TTFont(f"WN-{name}", files[0]))
            pdfmetrics.registerFont(TTFont(f"WN-{name}-Bold", files[1]))
            pdfmetrics.registerFont(TTFont(f"WN-{name}-Italic", files[2]))
            addMapping(f"WN-{name}", 0, 0, f"WN-{name}")
            addMapping(f"WN-{name}", 1, 0, f"WN-{name}-Bold")
            addMapping(f"WN-{name}", 0, 1, f"WN-{name}-Italic")
            addMapping(f"WN-{name}", 1, 1, f"WN-{name}-Bold")
            _FONTS = (f"WN-{name}", f"WN-{name}-Bold", True)
            return _FONTS
        except Exception:
            continue
    _FONTS = ("Helvetica", "Helvetica-Bold", False)
    return _FONTS


def _markup(text: str, unicode_ok: bool) -> str:
    """Card text -> ReportLab paragraph markup: keeps <b>/<i>, escapes the rest."""
    import html
    parts = re.split(r"(</?[bi]>)", str(text or ""))
    out = []
    for p in parts:
        if re.fullmatch(r"</?[bi]>", p):
            out.append(p)
        else:
            p = html.unescape(p).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if not unicode_ok:
                p = p.replace("→", "->")
            out.append(p)
    return "".join(out)


def _resource(rel: str) -> Optional[str]:
    try:
        from ui.widgets.multilang_help import resource_path
        p = resource_path(rel)
        return p if os.path.isfile(p) else None
    except Exception:
        return None


def _sketch_png(name: str) -> Optional[io.BytesIO]:
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QColor, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    from ui.whats_new import SKETCH_DIR, SKETCH_H, SKETCH_W
    from ui.widgets.multilang_help import resource_path
    if name.lower().endswith(".png"):  # raster sketch (e.g. the logo) - as it is
        try:
            with open(resource_path(f"{SKETCH_DIR}/{name}"), "rb") as fh:
                return io.BytesIO(fh.read())
        except OSError:
            return None
    try:
        with open(resource_path(f"{SKETCH_DIR}/{name}"), encoding="utf-8") as fh:
            src = fh.read()
    except OSError:
        return None
    renderer = QSvgRenderer(QByteArray(re.sub(r"\{\{\w+\}\}", "", src).encode("utf-8")))
    if not renderer.isValid():
        return None
    img = QImage(SKETCH_W * SKETCH_SCALE, SKETCH_H * SKETCH_SCALE, QImage.Format_ARGB32)
    img.fill(QColor("#ffffff"))
    painter = QPainter(img)
    renderer.render(painter)
    painter.end()
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    buf.close()
    return io.BytesIO(bytes(data))


def default_file_name(release_idx: int, lang: str) -> str:
    from ui.whats_new import release_version
    v = re.sub(r"[^\w.-]", "_", release_version(RELEASES[release_idx]))
    return f"TrippleT_{WINDOW_TITLE[lang].replace(' ', '_').replace(chr(39), '')}_{v}_{lang}.pdf"


def export_release_pdf(release_idx: int, lang: str, path: str) -> int:
    """Writes the version RELEASES[release_idx] in `lang` to `path`.
    Returns the number of pages."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        BaseDocTemplate, Frame, Image as RLImage, KeepTogether, PageTemplate, Paragraph, Spacer, Table,
        TableStyle,
    )
    from reportlab.lib.utils import ImageReader
    from ui.whats_new import LOGO, SKETCH_H, SKETCH_W, release_version, release_when

    regular, bold, uni = _fonts()
    release = RELEASES[release_idx]
    version = release_version(release)
    title = f"{WINDOW_TITLE[lang]} - {VERSION_LABEL[lang]} {version}"
    when = release_when(release, lang)

    s_h = ParagraphStyle("wn_h", fontName=bold, fontSize=13, leading=16, textColor=colors.HexColor(NAVY),
                         spaceBefore=4, spaceAfter=5)
    s_t = ParagraphStyle("wn_t", fontName=bold, fontSize=10.5, leading=13, textColor=colors.HexColor("#1a1a1a"),
                         spaceAfter=3)
    s_b = ParagraphStyle("wn_b", fontName=regular, fontSize=9, leading=12, textColor=colors.HexColor("#2b2b2b"))
    s_w = ParagraphStyle("wn_w", fontName=regular, fontSize=8.5, leading=11, textColor=colors.HexColor("#2b2b2b"),
                         spaceBefore=4)
    s_p = ParagraphStyle("wn_p", parent=s_b, spaceAfter=4)

    PW, PH = A4
    ml = mr = 16 * mm
    mt, mb = 26 * mm, 16 * mm
    mt1 = 35 * mm  # page 1: masthead with the logo
    frame_w = PW - ml - mr
    sketch_w = 62 * mm
    sketch_h = sketch_w * SKETCH_H / SKETCH_W
    gap = 4 * mm

    def card(block) -> Table:
        _, t, text, where, sketch = block
        col = [Paragraph(_markup(t, uni), s_t), Paragraph(_markup(text, uni), s_b),
               Paragraph(f"<font color='#565656'>{_markup(WHERE_LABEL[lang], uni)}</font> {_markup(where, uni)}",
                         s_w)]
        png = _sketch_png(sketch) if sketch else None
        if png is not None:
            iw, ih = ImageReader(png).getSize()
            png.seek(0)
            scale = min(sketch_w / iw, sketch_h / ih)  # keep the aspect (raster sketches)
            data = [[col, RLImage(png, width=iw * scale, height=ih * scale)]]
            widths = [frame_w - sketch_w - 2 * gap, sketch_w + gap]
        else:
            data = [[col]]
            widths = [frame_w]
        tbl = Table(data, colWidths=widths)
        tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#dcdcdc")),
            ("LINEBEFORE", (0, 0), (0, -1), 3.5, colors.HexColor(ACCENT)),
            ("LEFTPADDING", (0, 0), (0, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        return tbl

    # sections: heading + its cards, kept on one page
    story = []
    section = []

    def flush():
        if section:
            if story:
                story.append(KeepTogether(list(section)))
            else:  # first section starts right under the masthead (no empty page 1) - card by card
                story.append(KeepTogether(section[:2]))  # heading + first card together
                story.extend(section[2:])
            story.append(Spacer(1, 4 * mm))
            section.clear()

    for block in release["texts"][lang]:
        kind = block[0]
        if kind == "h":
            flush()
            section.append(Paragraph(_markup(block[1], uni), s_h))
        elif kind == "feature":
            section.append(card(block))
            section.append(Spacer(1, 2.5 * mm))
        elif len(block) > 1 and isinstance(block[1], str):  # p/note/... - plain paragraph
            section.append(Paragraph(_markup(block[1], uni), s_p))
    flush()

    logo = _resource("assets/images/heb_logo.png")
    mag_logo = _resource(LOGO)

    def company_logo(canvas, y_top):
        if logo:
            try:
                ir = ImageReader(logo)
                iw, ih = ir.getSize()
                h = 5 * mm
                canvas.drawImage(ir, PW - mr - h * iw / ih, y_top - 4 * mm, width=h * iw / ih, height=h,
                                 mask="auto")
            except Exception:
                pass

    def footer(canvas, doc):
        canvas.setFont(regular, 8)
        canvas.setFillColor(colors.HexColor("#888888"))
        canvas.drawRightString(PW - mr, 9 * mm, str(doc.page))

    def on_first_page(canvas, doc):
        if not mag_logo:
            return on_page(canvas, doc)
        canvas.saveState()
        y_top = PH - 10 * mm
        company_logo(canvas, y_top)
        ir = ImageReader(mag_logo)
        iw, ih = ir.getSize()
        h = 19 * mm  # same band as the company logo (top right)
        w = h * iw / ih
        canvas.drawImage(ir, ml - 2 * mm, PH - 8 * mm - h, width=w, height=h, mask="auto")
        x = ml + w + 4 * mm
        y = PH - 15 * mm
        canvas.setFont(bold, 14)
        canvas.setFillColor(colors.HexColor(NAVY))
        canvas.drawString(x, y, SUBTITLE[lang])
        canvas.setFont(regular, 11)
        canvas.setFillColor(colors.HexColor("#2b2b2b"))
        canvas.drawString(x, y - 5.5 * mm, f"{VERSION_LABEL[lang]} {version}")
        canvas.setFont(regular, 9)
        canvas.setFillColor(colors.HexColor("#565656"))
        canvas.drawString(x, y - 10 * mm, when)
        canvas.setStrokeColor(colors.HexColor(ACCENT))
        canvas.setLineWidth(1.5)
        canvas.line(ml, PH - mt1 + 5 * mm, PW - mr, PH - mt1 + 5 * mm)
        footer(canvas, doc)
        canvas.restoreState()

    def on_page(canvas, doc):
        canvas.saveState()
        y_top = PH - 12 * mm
        x = ml
        company_logo(canvas, y_top)
        canvas.setFont(bold, 14)
        canvas.setFillColor(colors.HexColor(NAVY))
        canvas.drawString(x, y_top - 1 * mm, f"TrippleT · {title}" if uni else f"TrippleT - {title}")
        canvas.setFont(regular, 9)
        canvas.setFillColor(colors.HexColor("#565656"))
        canvas.drawString(x, y_top - 5.5 * mm, when)
        canvas.setStrokeColor(colors.HexColor(ACCENT))
        canvas.setLineWidth(1.5)
        canvas.line(ml, PH - 20 * mm, PW - mr, PH - 20 * mm)
        footer(canvas, doc)
        canvas.restoreState()

    doc = BaseDocTemplate(path, pagesize=A4, leftMargin=ml, rightMargin=mr, topMargin=mt, bottomMargin=mb,
                          title=f"TrippleT {title}", author="TrippleT")
    frame = Frame(ml, mb, frame_w, PH - mt - mb, id="body", leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0)
    first_mt = mt1 if mag_logo else mt
    frame1 = Frame(ml, mb, frame_w, PH - first_mt - mb, id="body1", leftPadding=0, rightPadding=0,
                   topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="first", frames=[frame1], onPage=on_first_page, autoNextPageTemplate="page"),
                          PageTemplate(id="page", frames=[frame], onPage=on_page)])
    doc.build(story)
    return doc.page


def save_release_pdf_dialog(parent, release_idx: int, lang: str) -> Optional[str]:
    """Save dialog + export + open the PDF. Returns the path or None."""
    import pathlib
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QFileDialog, QMessageBox
    docs = pathlib.Path.home() / "Documents"
    path, _ = QFileDialog.getSaveFileName(parent, "Save as PDF", str(docs / default_file_name(release_idx, lang)),
                                          "PDF Files (*.pdf)")
    if not path:
        return None
    try:
        export_release_pdf(release_idx, lang, path)
    except Exception as e:
        show_error(parent, "PDF", "The PDF could not be saved.", e)
        return None
    try:
        from db.usage_log import log_usage_event
        from ui.whats_new import release_version
        log_usage_event("feature", "whats_new_pdf", f"{release_version(RELEASES[release_idx])} {lang}")
    except Exception:
        pass
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))
    return path
