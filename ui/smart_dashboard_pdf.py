# ui/smart_dashboard_pdf.py
"""PDF of Smart Chart dashboard pages (Etappe 4, Nutzerwunsch 2026-10-30):
each dashboard page becomes one A4 landscape page with its visuals at their
place on the 12-column grid, company logo top right. Charts and matrices come
as images rendered by Plotly in the web page; cards, tables and slicers are
written as text. Filters (all pages + this page) and fairness warnings are
printed too.

All text is measured (_fit/_wrap with the real font width), so nothing runs
out of its card. Font as in What's new: Segoe UI / Arial, else Helvetica.
"""
from __future__ import annotations

import base64
import datetime
import io
import re
from typing import Any, Dict, List, Optional, Tuple

FAIR_COLOURS = {"amber": "#C98A00", "red": "#C62828", "green": "#1F7A3A"}
IMG_COL_PX, IMG_ROW_PX = 100, 20       # pixel size of one grid cell for the chart images (ratio = screen)
MAX_STRETCH = 1.6                      # a short dashboard may fill the page, but no giant charts
PAGE_W, PAGE_H = 841.89, 595.28        # A4 landscape, points
MARGIN = 28.35                         # 1 cm
HEADER_H = 62                          # title + one line of filters + rule
LOGO_H = 15.0
GAP = 5
SLICER_LH = 11.0


def _row_height(area_h: float, colw: float, rows_total: int) -> float:
    """Height of one grid row: fill the page, keep charts from getting too tall."""
    return min(area_h / max(1, rows_total), colw * IMG_ROW_PX / IMG_COL_PX * MAX_STRETCH)


def image_size(v: Dict[str, Any], rows_total: int = 0) -> tuple:
    """Pixel size of a chart image, same proportions as its box on the PDF page."""
    w = max(2, v.get("w") or 6)
    h = max(3, v.get("h") or 16)
    colw = (PAGE_W - 2 * MARGIN) / 12.0
    rowh = _row_height(PAGE_H - 2 * MARGIN - HEADER_H, colw, rows_total or h)
    return int(w * IMG_COL_PX), int(h * rowh / colw * IMG_COL_PX)


def write_pdf(path: str, report_title: str, pages: List[Dict[str, Any]], all_filters: List[str],
              images: Dict[str, str]) -> None:
    """pages: [{"id", "title", "filters": [texts], "visuals": [visual + {"result": …}]}];
    images: {"<page id>:<visual id>": base64 png}."""
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    from ui.whats_new_pdf import _fonts, _resource

    regular, bold, _ = _fonts()
    pw, ph, m = PAGE_W, PAGE_H, MARGIN
    c = canvas.Canvas(path, pagesize=(pw, ph))
    c.setTitle(report_title or "Smart Chart dashboard")
    green, ink, grey, line = (colors.HexColor("#1F7A3A"), colors.HexColor("#1C2321"),
                              colors.HexColor("#5A6460"), colors.HexColor("#DADFD8"))
    style = (regular, bold, ink, grey, line, colors, ImageReader)
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    logo = _logo(ImageReader, _resource("assets/images/heb_logo.png"))

    for pno, page in enumerate(pages, start=1):
        # header: title left, logo right, filters below, green rule
        y = ph - m
        logo_w = 0.0
        if logo:
            iw, ih = logo.getSize()
            logo_w = LOGO_H * iw / ih
            c.drawImage(logo, pw - m - logo_w, y - LOGO_H - 2, logo_w, LOGO_H, mask="auto")
        title_w = pw - 2 * m - logo_w - 16
        c.setFillColor(green)
        c.setFont(bold, 7.5)
        c.drawString(m, y - 8, "SMART CHART · DASHBOARD")
        c.setFillColor(ink)
        c.setFont(bold, 15)
        c.drawString(m, y - 25, _fit(c, _page_title(report_title, page, len(pages)), bold, 15, title_w))
        c.setFillColor(grey)
        c.setFont(regular, 7.5)
        text_y = y - 37
        for t in _filter_lines(c, all_filters, page.get("filters") or [], regular, 7.5, pw - 2 * m):
            c.drawString(m, text_y, t)
            text_y -= 9.5
        rule_y = text_y + 4
        c.setStrokeColor(green)
        c.setLineWidth(1)
        c.line(m, rule_y, pw - m, rule_y)
        top = rule_y - 7

        # grid
        vis = page["visuals"]
        rows_total = max([int(v["y"]) + int(v["h"]) for v in vis] + [1])
        colw = (pw - 2 * m + GAP) / 12.0
        rowh = _row_height(top - m - 2, colw, rows_total)
        for v in vis:
            _card(c, v, m + v["x"] * colw, top - v["y"] * rowh, v["w"] * colw - GAP, v["h"] * rowh - GAP,
                  images.get(f"{page['id']}:{v['id']}"), style)

        c.setStrokeColor(line)
        c.setLineWidth(0.5)
        c.line(m, m - 5, pw - m, m - 5)
        c.setFont(regular, 7)
        c.setFillColor(grey)
        c.drawString(m, m - 14, f"TrippleT Smart Chart · created {now}")
        c.drawRightString(pw - m, m - 14, f"Page {pno} of {len(pages)}")
        c.showPage()
    c.save()


def _logo(ImageReader, path: Optional[str]):
    try:
        return ImageReader(path) if path else None
    except Exception:
        return None


def _page_title(report_title: str, page: Dict[str, Any], n_pages: int) -> str:
    """A lone page with its default name adds nothing: "Report", not "Report – Page 1"."""
    title = page.get("title") or ""
    if not report_title:
        return title
    if not title or (n_pages == 1 and re.fullmatch(r"Page \d+", title)):
        return report_title
    return f"{report_title} – {title}"


def _filter_lines(c, all_filters: List[str], page_filters: List[str], font: str, size: float, width: float) -> List[str]:
    if not all_filters and not page_filters:
        return ["Filters: none"]
    out: List[str] = []
    if all_filters:
        out += _wrap(c, "Filters on all pages: " + " · ".join(all_filters), font, size, width, 2)
    if page_filters:
        out += _wrap(c, "Filters on this page: " + " · ".join(page_filters), font, size, width, 2)
    return out


def _card(c, v, x0, y_top, w, h, img_b64, style) -> None:
    regular, bold, ink, grey, line, colors, ImageReader = style
    c.setStrokeColor(line)
    c.setLineWidth(0.6)
    c.roundRect(x0, y_top - h, w, h, 4, stroke=1, fill=0)
    r = v.get("result") or {}
    title = (v.get("title") if v.get("title_set") else "") or r.get("title") or ""
    c.setFillColor(ink)
    c.setFont(bold, 8)
    c.drawString(x0 + 6, y_top - 11, _fit(c, title, bold, 8, w - 12))
    inner_top = y_top - 15
    fair = r.get("fair")
    if fair and fair.get("level") in ("amber", "red"):
        c.setFillColor(colors.HexColor(FAIR_COLOURS[fair["level"]]))
        c.circle(x0 + 8.5, inner_top - 3, 2.2, stroke=0, fill=1)
        c.setFont(regular, 6)
        for t in _wrap(c, f"{fair['headline']}: {fair['text']}", regular, 6, w - 20, 2):
            c.drawString(x0 + 14, inner_top - 5, t)
            inner_top -= 7.5
        inner_top -= 2
    box = (x0 + 5, y_top - h + 5, w - 10, inner_top - (y_top - h + 5))
    _content(c, r, v, box, img_b64, style)


def _content(c, r, v, box, img_b64, style) -> None:
    regular, bold, ink, grey, line, colors, ImageReader = style
    bx, by, bw, bh = box
    if bh <= 6:
        return
    kind = r.get("kind")
    if kind == "plotly" and img_b64:
        img = ImageReader(io.BytesIO(base64.b64decode(img_b64)))
        c.drawImage(img, bx, by, bw, bh, preserveAspectRatio=True, anchor="c", mask="auto")
    elif kind == "kpi":
        value, unit = str(r.get("value") or ""), str(r.get("unit") or "")
        size = max(10, min(26 * (r.get("vsize") or 30) / 30, bh * 0.5))
        unit_w = c.stringWidth(" " + unit, regular, 8) if unit else 0
        while size > 8 and c.stringWidth(value, bold, size) + unit_w > bw:
            size -= 1
        base = by + bh - size
        c.setFillColor(colors.HexColor("#C62828" if r.get("status") == "bad" else "#165C2B"))
        c.setFont(bold, size)
        c.drawString(bx + 1, base, _fit(c, value, bold, size, bw - 2))
        value_w = c.stringWidth(value, bold, size)
        c.setFillColor(grey)
        c.setFont(regular, 8)
        if unit and value_w + 4 < bw:
            c.drawString(bx + 1 + value_w + 3, base, _fit(c, unit, regular, 8, bw - value_w - 4))
        c.setFont(regular, 7)
        c.drawString(bx + 1, base - max(10, size * 0.3), _fit(c, r.get("sub") or "", regular, 7, bw - 2))
    elif kind == "table":
        _table(c, r, box, style)
    elif kind == "slicer":
        _slicer(c, r, v, box, style)
    elif kind == "text":
        _text(c, r, box, style)
    else:
        c.setFillColor(grey)
        c.setFont(regular, 7.5)
        lines = _wrap(c, r.get("message") or "", regular, 7.5, bw - 4, 3)
        for i, t in enumerate(lines):
            c.drawCentredString(bx + bw / 2, by + bh / 2 + (len(lines) / 2 - i - 1) * 10, t)


def _text(c, r, box, style) -> None:
    """Text visual: "# " lines as headings, the rest wrapped; **bold** markers are left out."""
    regular, bold, ink, grey, line, colors, ImageReader = style
    bx, by, bw, bh = box
    scale = (r.get("font") or 13) / 13
    y = by + bh
    for raw_line in str(r.get("text") or "").splitlines() or [""]:
        head = raw_line.lstrip().startswith("# ")
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", raw_line.lstrip()[2:] if head else raw_line)
        font, size = (bold, 13 * scale) if head else (regular, 8.5 * scale)
        c.setFont(font, size)
        c.setFillColor(colors.HexColor("#165C2B") if head else ink)
        for part in _wrap(c, text, font, size, bw - 2, 50) if text else [""]:
            y -= size * 1.35
            if y < by:
                return
            c.drawString(bx + 1, y, part)


def _table(c, r, box, style) -> None:
    regular, bold, ink, grey, line, colors, ImageReader = style
    bx, by, bw, bh = box
    head, rows = r.get("head") or [], r.get("rows") or []
    cw = bw / max(1, len(head))
    fs = 6.5 * (r.get("font") or 11) / 11
    lh = fs + 2.5
    bg = r.get("cellbg") or []
    pad = 2
    y = by + bh - lh
    c.setFillColor(colors.HexColor("#F4F6F3"))
    c.rect(bx, y - 2, bw, lh, stroke=0, fill=1)
    c.setFont(bold, fs)
    c.setFillColor(ink)
    for i, t in enumerate(head):
        c.drawString(bx + i * cw + pad, y, _fit(c, t, bold, fs, cw - 2 * pad))
    fits = max(0, int((bh - lh) / lh))
    if len(rows) + (r.get("more") or 0) > fits:
        fits = max(0, fits - 1)           # room for the "more" line
    c.setStrokeColor(line)
    c.setLineWidth(0.3)
    for j, row in enumerate(rows[:fits]):
        ry = y - lh * (j + 1)
        for i, col in enumerate(bg[j] if j < len(bg) else []):
            if col:
                c.setFillColor(colors.HexColor(col))
                c.rect(bx + i * cw, ry - 2, cw, lh, stroke=0, fill=1)
        c.line(bx, ry + lh - 2, bx + bw, ry + lh - 2)
        c.setFillColor(ink)
        c.setFont(regular, fs)
        for i, t in enumerate(row[1:]):
            c.drawString(bx + i * cw + pad, ry, _fit(c, t, regular, fs, cw - 2 * pad))
    rest = len(rows) - fits + (r.get("more") or 0)
    if rest > 0:
        c.setFillColor(grey)
        c.drawString(bx + pad, by + 1, f"… {rest} more {'values' if r.get('grouped') else 'trials'} (see Excel)")


# ── slicer: drawn as on the dashboard, in its style ──────────────────────
def _slicer(c, r, v, box, style) -> None:
    regular, bold, ink, grey, line, colors, ImageReader = style
    bx, by, bw, bh = box
    selected = [str(x) for x in ((v.get("sel") or {}).get("values") or [])]
    kind = r.get("style")
    if kind == "between":
        return _slicer_between(c, r, v, box, style)
    if kind == "dropdown":
        return _slicer_dropdown(c, v, selected, box, style)
    c.setFont(regular, 7)
    c.setFillColor(grey)
    c.drawString(bx + 1, by + bh - 7, f"{len(selected)} selected" if selected else "All")
    top = by + bh - 13
    box2 = (bx, by, bw, top - by)
    if kind == "hierarchy":
        rows = _hierarchy_rows(r, selected, int((top - by) / SLICER_LH))
    elif kind == "tiles":
        return _slicer_tiles(c, r, selected, box2, style)
    else:
        rows = _list_rows(r, selected, int((top - by) / SLICER_LH), r.get("multi", True))
    _slicer_rows(c, rows, bx, top, bw, style)


def _hierarchy_rows(r, selected: List[str], fits: int) -> List[Dict[str, Any]]:
    """Open years as on the screen; collapse what is all on / all off if the card is too short."""
    tree = r.get("tree") or []
    extra = 1 if r.get("none") else 0

    def build(opened) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for t in tree:
            n_on = sum(1 for m in t["months"] if m["label"] in selected)
            out.append({"text": t["year"], "n": t["n"], "bold": True, "fold": "open" if t["year"] in opened else "shut",
                        "state": "on" if n_on == 12 else "part" if n_on else "off"})
            if t["year"] in opened:
                out += [{"text": m["name"], "n": m["n"], "indent": 18, "dim": not m["n"],
                         "state": "on" if m["label"] in selected else "off"} for m in t["months"]]
        return out

    def count_on(t) -> int:
        return sum(1 for m in t["months"] if m["label"] in selected)

    opened = {t["year"] for i, t in enumerate(tree) if count_on(t) or (i == 0 and not selected)}
    rows = build(opened)
    if len(rows) + extra > fits:
        rows = build({t["year"] for t in tree if 0 < count_on(t) < 12})
    if r.get("none"):
        rows.append({"text": "(no date)", "n": r["none"], "state": "on" if "(none)" in selected else "off"})
    return _limit_rows(rows, fits)


def _list_rows(r, selected: List[str], fits: int, multi: bool) -> List[Dict[str, Any]]:
    """In the order of the slicer; if not all fit, the selected ones come first."""
    unit = f" {r['unit']}" if r.get("unit") and r.get("fkind") == "num" else ""
    rows = [{"text": o["label"] + unit, "n": o["n"], "state": "on" if o["label"] in selected else "off",
             "round": not multi} for o in (r.get("options") or [])]
    if len(rows) > fits:
        rows.sort(key=lambda o: o["state"] != "on")
    return _limit_rows(rows, fits, r.get("more") or 0)


def _limit_rows(rows: List[Dict[str, Any]], fits: int, more: int = 0) -> List[Dict[str, Any]]:
    if len(rows) + (1 if more else 0) <= fits:
        hidden = more
    else:
        keep = max(0, fits - 1)
        hidden = len(rows) - keep + more
        rows = rows[:keep]
    return rows + ([{"more": hidden}] if hidden else [])


def _slicer_rows(c, rows, bx, top, bw, style) -> None:
    regular, bold, ink, grey, line, colors, ImageReader = style
    y = top
    for row in rows:
        y -= SLICER_LH
        if "more" in row:
            c.setFont(regular, 7)
            c.setFillColor(grey)
            c.drawString(bx + 1, y + 2, f"+ {row['more']} more")
            continue
        x = bx + 1 + row.get("indent", 0)
        if row.get("fold"):
            c.setFillColor(grey)
            p = c.beginPath()
            if row["fold"] == "open":
                p.moveTo(x, y + 6.5); p.lineTo(x + 6, y + 6.5); p.lineTo(x + 3, y + 2.5)
            else:
                p.moveTo(x + 1, y + 7.5); p.lineTo(x + 1, y + 1.5); p.lineTo(x + 5, y + 4.5)
            p.close()
            c.drawPath(p, stroke=0, fill=1)
            x += 9
        _tickbox(c, x, y + 1, row["state"], row.get("round", False), style)
        x += 11
        font = bold if row.get("bold") else regular
        n = str(row.get("n", ""))
        c.setFont(regular, 6.5)
        c.setFillColor(colors.HexColor("#9AA59C"))
        c.drawRightString(bx + bw - 1, y + 2, n)
        c.setFont(font, 7.5)
        c.setFillColor(colors.HexColor("#B5BCB7") if row.get("dim") else ink)
        c.drawString(x, y + 2, _fit(c, row["text"], font, 7.5, bx + bw - x - c.stringWidth(n, regular, 6.5) - 5))


def _tickbox(c, x, y, state, round_box, style) -> None:
    colors = style[5]
    s = 7.5
    fill = {"on": "#1F7A3A", "part": "#9CC8A9"}.get(state)
    c.setStrokeColor(colors.HexColor("#1F7A3A" if fill else "#8A938C"))
    c.setLineWidth(0.7)
    if fill:
        c.setFillColor(colors.HexColor(fill))
    if round_box:
        c.circle(x + s / 2, y + s / 2, s / 2, stroke=1, fill=1 if fill else 0)
    else:
        c.roundRect(x, y, s, s, 1.3, stroke=1, fill=1 if fill else 0)
    if state == "on":
        c.setStrokeColor(colors.white)
        c.setLineWidth(1)
        p = c.beginPath()
        p.moveTo(x + 1.7, y + 3.8); p.lineTo(x + 3.2, y + 2.2); p.lineTo(x + 5.9, y + 5.4)
        c.drawPath(p, stroke=1, fill=0)


def _slicer_tiles(c, r, selected, box, style) -> None:
    regular, bold, ink, grey, line, colors, ImageReader = style
    bx, by, bw, bh = box
    x, y, h, pad, gap = bx, by + bh - 14, 13, 5, 3
    options = r.get("options") or []
    if len(options) > int(bh / (h + gap)) * 3:      # roughly more than fits: selected ones first
        options = sorted(options, key=lambda o: o["label"] not in selected)
    for i, o in enumerate(options):
        label = _fit(c, o["label"], regular, 7.5, bw - 2 * pad - 14)
        n = str(o["n"])
        w = c.stringWidth(label, regular, 7.5) + c.stringWidth(n, regular, 6) + 2 * pad + 3
        if x + w > bx + bw:
            x, y = bx, y - h - gap
        if y < by + (h if i < len(options) - 1 else 0):
            c.setFont(regular, 7)
            c.setFillColor(grey)
            c.drawString(bx + 1, by + 1, f"+ {len(options) - i} more")
            return
        on = o["label"] in selected
        c.setStrokeColor(colors.HexColor("#1F7A3A" if on else "#C9D1C8"))
        c.setFillColor(colors.HexColor("#1F7A3A" if on else "#FFFFFF"))
        c.setLineWidth(0.6)
        c.roundRect(x, y, w, h, 3, stroke=1, fill=1)
        c.setFillColor(colors.white if on else ink)
        c.setFont(regular, 7.5)
        c.drawString(x + pad, y + 3.8, label)
        c.setFillColor(colors.HexColor("#D7EBDC" if on else "#9AA59C"))
        c.setFont(regular, 6)
        c.drawRightString(x + w - pad, y + 3.8, n)
        x += w + gap


def _slicer_dropdown(c, v, selected, box, style) -> None:
    regular, bold, ink, grey, line, colors, ImageReader = style
    bx, by, bw, bh = box
    text = "All" if not selected else selected[0] if len(selected) == 1 else f"{len(selected)} selected"
    h = min(16, bh)
    y = by + bh - h
    c.setStrokeColor(colors.HexColor("#C9D1C8"))
    c.setLineWidth(0.6)
    c.roundRect(bx, y, bw, h, 3, stroke=1, fill=0)
    c.setFillColor(ink)
    c.setFont(regular, 8)
    c.drawString(bx + 5, y + h / 2 - 2.8, _fit(c, text, regular, 8, bw - 20))
    c.setFillColor(grey)
    p = c.beginPath()
    ax, ay = bx + bw - 12, y + h / 2 + 2
    p.moveTo(ax, ay); p.lineTo(ax + 6, ay); p.lineTo(ax + 3, ay - 4)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    if len(selected) > 1:                 # on paper nobody can open the list
        c.setFont(regular, 7)
        fits = max(0, int((y - by - 3) / 9))
        for i, t in enumerate(_wrap(c, _compact_values(selected), regular, 7, bw - 2, fits) if fits else []):
            c.drawString(bx + 1, y - 9 - i * 9, t)


def _slicer_between(c, r, v, box, style) -> None:
    regular, bold, ink, grey, line, colors, ImageReader = style
    bx, by, bw, bh = box
    rg = r.get("range")
    if not rg:
        c.setFillColor(grey)
        c.setFont(regular, 7.5)
        c.drawString(bx + 1, by + bh - 9, "No values")
        return
    sel = v.get("sel") or {}
    lo = sel["min"] if sel.get("min") is not None else rg["min"]
    hi = sel["max"] if sel.get("max") is not None else rg["max"]
    h = 14
    y = by + bh - h
    w = (bw - 12) / 2
    c.setStrokeColor(colors.HexColor("#C9D1C8"))
    c.setLineWidth(0.6)
    c.setFont(regular, 8)
    for i, val in enumerate((lo, hi)):
        x = bx + i * (w + 12)
        c.setFillColor(ink)
        c.roundRect(x, y, w, h, 3, stroke=1, fill=0)
        c.drawString(x + 4, y + 4, _fit(c, f"{val:g}", regular, 8, w - 8))
    c.drawCentredString(bx + bw / 2, y + 4, "–")
    if bh < h + 14:
        return
    ty = y - 8
    span = (rg["max"] - rg["min"]) or 1
    xa = bx + 4 + (bw - 8) * (lo - rg["min"]) / span
    xb = bx + 4 + (bw - 8) * (hi - rg["min"]) / span
    c.setLineWidth(2)
    c.setStrokeColor(colors.HexColor("#DADFD8"))
    c.line(bx + 4, ty, bx + bw - 4, ty)
    c.setStrokeColor(colors.HexColor("#1F7A3A"))
    c.line(xa, ty, xb, ty)
    c.setFillColor(colors.HexColor("#1F7A3A"))
    c.setStrokeColor(colors.white)
    c.setLineWidth(1)
    c.circle(xa, ty, 4, stroke=1, fill=1)
    c.circle(xb, ty, 4, stroke=1, fill=1)
    if bh >= h + 26:
        unit = f" {r['unit']}" if r.get("unit") else ""
        c.setFillColor(grey)
        c.setFont(regular, 6.5)
        c.drawString(bx + 1, ty - 13, _fit(c, f"{rg['min']:g} – {rg['max']:g}{unit} available", regular, 6.5, bw - 2))


def _compact_values(values: List[str]) -> str:
    """Months read better per year: all of 2026 -> "2026", some -> "2026: Jan–Mar, Jun"."""
    from ui.smart_dashboard_engine import MONTH_NAMES

    years: Dict[str, List[int]] = {}
    other: List[str] = []
    for s in values:
        hit = re.fullmatch(r"(\d{4})-(\d{2})", s)
        if hit and 1 <= int(hit.group(2)) <= 12:
            years.setdefault(hit.group(1), []).append(int(hit.group(2)))
        else:
            other.append(s)
    parts: List[str] = []
    for year in sorted(years):
        months = sorted(set(years[year]))
        if len(months) == 12:
            parts.append(year)
            continue
        runs: List[Tuple[int, int]] = []
        for mo in months:
            if runs and runs[-1][1] == mo - 1:
                runs[-1] = (runs[-1][0], mo)
            else:
                runs.append((mo, mo))
        names = [MONTH_NAMES[a - 1] if a == b else f"{MONTH_NAMES[a - 1]}–{MONTH_NAMES[b - 1]}" for a, b in runs]
        parts.append(f"{year}: {', '.join(names)}")
    return ", ".join(parts + other)


def _fit(c, text: Any, font: str, size: float, width: float) -> str:
    """Cut text with "…" so that it is at most width points wide."""
    text = str(text if text is not None else "")
    if c.stringWidth(text, font, size) <= width:
        return text
    while text and c.stringWidth(text + "…", font, size) > width:
        text = text[:-1]
    return text.rstrip() + "…"


def _wrap(c, text: Any, font: str, size: float, width: float, max_lines: int) -> List[str]:
    """Break text into at most max_lines lines; the last one ends in "…" if more was left."""
    from reportlab.lib.utils import simpleSplit

    lines = simpleSplit(str(text or ""), font, size, width) or [""]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = _fit(c, lines[-1] + " " + "m" * 40, font, size, width)
    return [_fit(c, t, font, size, width) for t in lines]
