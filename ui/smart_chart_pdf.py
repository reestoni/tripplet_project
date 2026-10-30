# ui/smart_chart_pdf.py
"""PDF of the new Smart Chart (ui/screen_smart_chart.py): title, filters,
counts, the chart image and the list of trials in the chart. A4 landscape,
reportlab like the series report."""
from __future__ import annotations

import datetime
import html
import io
import re
from typing import Any, Dict, List, Optional


def _plain(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text or "")
    return html.unescape(re.sub(r"<[^>]+>", "", text)).replace("\xa0", " ").strip()


def _x(s: Any) -> str:
    return str(s if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _num(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:.3f}".rstrip("0").rstrip(".")
    return str(v if v is not None else "")


def write_pdf(path: str, title: str, filters: List[str], summary: str, chart_png: Optional[bytes],
              rows: List[Dict[str, Any]], x_label: str, y_label: str) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    green, navy, grey = colors.HexColor("#1F7A3A"), colors.HexColor("#1C2321"), colors.HexColor("#5A6460")
    st_kicker = ParagraphStyle("k", fontName="Helvetica-Bold", fontSize=8, textColor=green, leading=10)
    st_title = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=16, textColor=navy, leading=20, spaceAfter=4)
    st_text = ParagraphStyle("p", fontName="Helvetica", fontSize=9, textColor=navy, leading=12)
    st_small = ParagraphStyle("s", fontName="Helvetica", fontSize=8, textColor=grey, leading=10)
    st_cell = ParagraphStyle("c", fontName="Helvetica", fontSize=7.5, leading=9)

    page_w, page_h = landscape(A4)
    doc = SimpleDocTemplate(path, pagesize=landscape(A4), leftMargin=1.4 * cm, rightMargin=1.4 * cm,
                            topMargin=1.2 * cm, bottomMargin=1.2 * cm, title=title or "Smart Chart")
    usable_w = page_w - 2.8 * cm
    story: List[Any] = [
        Paragraph("SMART CHART", st_kicker),
        Paragraph(_x(title or "Smart Chart"), st_title),
        Paragraph(_x(_plain(summary)).replace("\n", "<br/>"), st_text),
        Paragraph("Filters: " + _x(" · ".join(filters)), st_text),
        Paragraph(f"X: {_x(x_label)} · Y: {_x(y_label)} · created {datetime.datetime.now():%d.%m.%Y %H:%M}", st_small),
        Spacer(1, 0.3 * cm),
    ]
    if chart_png:
        img_h = page_h - 7.2 * cm
        story.append(Image(io.BytesIO(chart_png), width=usable_w, height=min(img_h, usable_w * 820 / 1500)))
        story.append(Spacer(1, 0.4 * cm))
    head = ["Trial", "Series", "Yarn", "Machine", "Jet", x_label, y_label]
    data = [head] + [[Paragraph(_x(p["trial"]), st_cell), Paragraph(_x(p["series"]), st_cell),
                      Paragraph(_x(p["yarn"]), st_cell), Paragraph(_x(p["machine"]), st_cell),
                      Paragraph(_x(p["jet"]), st_cell), _num(p["x"]), _num(p["y"])] for p in rows]
    widths = [1.4 * cm, 6.2 * cm, 5.4 * cm, 2.8 * cm, 2.8 * cm]
    rest = (usable_w - sum(widths)) / 2
    tbl = Table(data, colWidths=widths + [rest, rest], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 7.5),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 0), (-1, 0), green),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F7F3")]),
        ("ALIGN", (5, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, green),
    ]))
    story.append(tbl)
    doc.build(story)
