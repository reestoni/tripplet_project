# ui/smart_dashboard_pdf.py
"""PDF of Smart Chart dashboard pages (Etappe 4, Nutzerwunsch 2026-10-30):
each dashboard page becomes one A4 landscape page with its visuals at their
place on the 12-column grid. Charts and matrices come as images rendered by
Plotly in the web page; cards, tables and slicers are written as text.
Filters (all pages + this page) and fairness warnings are printed too.
"""
from __future__ import annotations

import base64
import datetime
import io
from typing import Any, Dict, List, Optional

FAIR_COLOURS = {"amber": "#C98A00", "red": "#C62828", "green": "#1F7A3A"}
IMG_COL_PX, IMG_ROW_PX = 100, 20       # pixel size of one grid cell for the chart images (ratio = screen)


def image_size(v: Dict[str, Any]) -> tuple:
    return int(max(2, v.get("w") or 6) * IMG_COL_PX), int(max(3, v.get("h") or 16) * IMG_ROW_PX)


def write_pdf(path: str, report_title: str, pages: List[Dict[str, Any]], all_filters: List[str],
              images: Dict[str, str]) -> None:
    """pages: [{"id", "title", "filters": [texts], "visuals": [visual + {"result": …}]}];
    images: {"<page id>:<visual id>": base64 png}."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    pw, ph = landscape(A4)
    m = 1.0 * cm
    c = canvas.Canvas(path, pagesize=(pw, ph))
    c.setTitle(report_title or "Smart Chart dashboard")
    green, ink, grey, line = (colors.HexColor("#1F7A3A"), colors.HexColor("#1C2321"),
                              colors.HexColor("#5A6460"), colors.HexColor("#DADFD8"))
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

    for pno, page in enumerate(pages, start=1):
        # header
        y = ph - m
        c.setFillColor(green)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(m, y - 8, "SMART CHART · DASHBOARD")
        c.setFillColor(ink)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(m, y - 24, _clip(f"{report_title} – {page['title']}" if report_title else page["title"], 110))
        c.setFont("Helvetica", 7.5)
        c.setFillColor(grey)
        lines = [f"Filters on all pages: {' · '.join(all_filters) or 'none'}",
                 f"Filters on this page: {' · '.join(page.get('filters') or []) or 'none'}"]
        for i, t in enumerate(lines):
            c.drawString(m, y - 36 - i * 9, _clip(t, 190))
        top = y - 36 - len(lines) * 9 - 6

        # grid
        vis = page["visuals"]
        rows_total = max([int(v["y"]) + int(v["h"]) for v in vis] + [1])
        area_w, area_h = pw - 2 * m, top - m - 12
        colw = area_w / 12.0
        rowh = min(area_h / rows_total, colw * IMG_ROW_PX / IMG_COL_PX)
        gap = 4
        for v in vis:
            x0 = m + v["x"] * colw
            y_top = top - v["y"] * rowh
            w = v["w"] * colw - gap
            h = v["h"] * rowh - gap
            c.setStrokeColor(line)
            c.setLineWidth(0.6)
            c.roundRect(x0, y_top - h, w, h, 4, stroke=1, fill=0)
            r = v.get("result") or {}
            title = (v.get("title") if v.get("title_set") else "") or r.get("title") or ""
            c.setFillColor(ink)
            c.setFont("Helvetica-Bold", 7.5)
            c.drawString(x0 + 5, y_top - 10, _clip(title, int(w / 4)))
            inner_top = y_top - 14
            fair = r.get("fair")
            if fair and fair.get("level") in ("amber", "red"):
                c.setFillColor(colors.HexColor(FAIR_COLOURS[fair["level"]]))
                c.circle(x0 + 8, inner_top - 3, 2.2, stroke=0, fill=1)
                c.setFont("Helvetica", 5.8)
                c.drawString(x0 + 13, inner_top - 5, _clip(f"{fair['headline']}: {fair['text']}", int(w / 3)))
                inner_top -= 10
            box = (x0 + 4, y_top - h + 4, w - 8, inner_top - (y_top - h + 4))
            _content(c, r, v, box, images.get(f"{page['id']}:{v['id']}"), colors, ImageReader, ink, grey)

        c.setFont("Helvetica", 6.5)
        c.setFillColor(grey)
        c.drawString(m, m - 12, f"TrippleT Smart Chart · created {now}")
        c.drawRightString(pw - m, m - 12, f"Page {pno} of {len(pages)}")
        c.showPage()
    c.save()


def _content(c, r, v, box, img_b64, colors, ImageReader, ink, grey) -> None:
    bx, by, bw, bh = box
    if bh <= 6:
        return
    kind = r.get("kind")
    if kind == "plotly" and img_b64:
        img = ImageReader(io.BytesIO(base64.b64decode(img_b64)))
        c.drawImage(img, bx, by, bw, bh, preserveAspectRatio=True, anchor="c", mask="auto")
    elif kind == "kpi":
        size = max(10, min(24, bh * 0.45))
        status = r.get("status")
        c.setFillColor(colors.HexColor("#C62828" if status == "bad" else "#165C2B"))
        c.setFont("Helvetica-Bold", size)
        c.drawString(bx + 2, by + bh - size, str(r.get("value") or ""))
        tw = c.stringWidth(str(r.get("value") or ""), "Helvetica-Bold", size)
        c.setFillColor(grey)
        c.setFont("Helvetica", 7)
        c.drawString(bx + 6 + tw, by + bh - size, _clip(r.get("unit") or "", 30))
        c.drawString(bx + 2, by + bh - size - 10, _clip(r.get("sub") or "", int(bw / 3.5)))
    elif kind == "table":
        head, rows = r.get("head") or [], r.get("rows") or []
        n = max(1, len(head))
        cw = bw / n
        lh = 7.5
        c.setFont("Helvetica-Bold", 6)
        c.setFillColor(ink)
        for i, t in enumerate(head):
            c.drawString(bx + i * cw, by + bh - lh, _clip(t, int(cw / 3)))
        c.setFont("Helvetica", 6)
        max_rows = int((bh - lh) / lh) - 1
        for j, row in enumerate(rows[:max(0, max_rows)]):
            for i, t in enumerate(row[1:]):
                c.drawString(bx + i * cw, by + bh - lh * (j + 2), _clip(str(t), int(cw / 3)))
        rest = len(rows) - max(0, max_rows) + (r.get("more") or 0)
        if rest > 0:
            c.setFillColor(grey)
            c.drawString(bx, by + 1, f"… {rest} more trials (see Excel)")
    elif kind == "slicer":
        sel = (v.get("sel") or {})
        if sel.get("values"):
            txt = ", ".join(map(str, sel["values"]))
        elif sel.get("min") is not None or sel.get("max") is not None:
            txt = f"{sel.get('min')} – {sel.get('max')}"
        else:
            txt = "All"
        c.setFillColor(ink)
        c.setFont("Helvetica", 8)
        c.drawString(bx + 2, by + bh - 10, "Selected: " + _clip(txt, int(bw / 4)))
    else:
        c.setFillColor(grey)
        c.setFont("Helvetica-Oblique", 7)
        c.drawString(bx + 2, by + bh / 2, _clip(r.get("message") or "", int(bw / 3.5)))


def _clip(text: str, n: int) -> str:
    text = str(text or "")
    n = max(4, n)
    return text if len(text) <= n else text[: n - 1] + "…"
