"""Erzeugt die kleinen Skizzen fuer "What's new" (Karten in ui/whats_new.py):
assets/images/whats_new/wn_*.svg, je 300 x 130, sprachneutral (Beschriftungen
englisch wie in der App).

Aufruf: python tools/gen_whats_new_svgs.py  (ueberschreibt die Dateien)
Neue Skizze: Funktion unten ergaenzen und in ui/widgets/whats_new_texts.py
beim Feature als "sketch" eintragen.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svg_sketch import Svg, INK, MUTED, GREEN, LINE, ROOT  # noqa: E402

W, H = 300, 130
OUT = "whats_new"
AMBER, AMBER_BG = "#E8C15A", "#FFF4D6"
BLUE, NAVY = "#3d7fd6", "#1F4E8C"
STRIPE_A, STRIPE_B = "#e9f6e9", "#d5ecd8"
os.makedirs(os.path.join(ROOT, OUT), exist_ok=True)


def new(title):
    s = Svg(W, H, title)
    s.rect(1, 1, W - 2, H - 2, "#fafafa", LINE, 8)
    return s


def grid(s, x, y, rows, cols, cw, rh, first_w=96, header=None, fills=None):
    """Mini pivot table: rows = [(title, [values])]."""
    if header:
        s.rect(x, y, first_w + cw * cols, rh, "#4a4a4a", None, 2)
        for i, h in enumerate(header):
            s.text(x + first_w + cw * i + cw / 2, y + rh - 6, h, 9, "#ffffff", True, "middle")
        y += rh
    for r, (title, vals) in enumerate(rows):
        bg = STRIPE_A if r % 2 == 0 else STRIPE_B
        s.rect(x, y + r * rh, first_w + cw * cols, rh, bg, "#c9dfcb", 0)
        s.text(x + 5, y + r * rh + rh - 6, title, 9, INK)
        for c, v in enumerate(vals):
            f = (fills or {}).get((r, c))
            if f:
                s.rect(x + first_w + cw * c, y + r * rh, cw, rh, f, "#c9dfcb", 0)
            s.text(x + first_w + cw * c + cw / 2, y + r * rh + rh - 6, v, 9, INK, anchor="middle")
    return y + len(rows) * rh


def save(s, name):
    s.save(os.path.join(OUT, name))


# ── Show Experiment ─────────────────────────────────────────────────────
s = new("Yarns of the series")
s.text(12, 22, "Yarns", 11, INK, True)
x0, y0 = 12, 30
s.rect(x0, y0, 276, 18, "#4a4a4a", None, 2)
for x, t in ((x0 + 6, "Ply"), (x0 + 44, "Yarn")):
    s.text(x, y0 + 13, t, 9, "#ffffff", True)
for i, t in enumerate(("V1", "V2", "V3")):
    s.text(x0 + 186 + i * 32, y0 + 13, t, 9, "#ffffff", True, "middle")
rows = (("Ply 1", "PES 167f48 DTY", ("1x", "1x", "2x"), True),
        ("Ply 2", "PA 78f68", ("1x", "-", "1x"), False))
for r, (ply, yarn, cells, changed) in enumerate(rows):
    y = y0 + 18 + r * 24
    s.rect(x0, y, 276, 24, STRIPE_A if r == 0 else STRIPE_B, "#c9dfcb", 0)
    s.text(x0 + 6, y + 16, ply, 9, INK)
    s.rect(x0 + 40, y + 3, 124, 18, AMBER_BG if changed else "#ffffff", BLUE if changed else LINE, 3)
    s.text(x0 + 46, y + 16, yarn, 9, INK, changed)
    s.text(x0 + 156, y + 16, "v", 8, MUTED, False, "middle")
    for i, c in enumerate(cells):
        cx = x0 + 186 + i * 32
        if r == 0 and i == 2:
            s.rect(cx - 15, y + 1, 30, 22, "#FFF3B0", None, 0)
        s.text(cx, y + 16, c, 10, MUTED if c == "-" else INK, c != "-", "middle")
s.btn(12, 98, "+ Add ply", 64, "grey", h=20, size=9)
s.btn(80, 98, "+ Trial output", 86, "grey", h=20, size=9)
s.btn(236, 98, "Apply", 52, "green", h=20, size=9)
save(s, "wn_series_yarns.svg")


def spool(s, x, y, in_stock):
    """Spool symbol as in the Material line (16 x 16)."""
    s.rect(x + 3, y + 1, 10, 2, "#8A8A8A", None, 1)
    s.rect(x + 3, y + 13, 10, 2, "#8A8A8A", None, 1)
    if in_stock:
        s.rect(x + 4, y + 3, 8, 10, GREEN, None, 2)
    else:
        s.rect(x + 7, y + 3, 2, 10, "#8A8A8A", None, 0)
        s.line(x + 2, y + 14, x + 14, y + 2, "#C0392B", 2)


s = new("Where are my spools")
s.rect(12, 10, 276, 22, "#f8fff9", GREEN, 4)
s.text(20, 25, "Ply 1: PES 167f48", 9, INK)
spool(s, 102, 13, True)
s.text(124, 25, "Ply 2: PA 78f68", 9, INK)
spool(s, 198, 13, False)
s.line(110, 31, 110, 44, BLUE, 1.5)
x0, y0 = 12, 46
s.rect(x0, y0, 276, 16, "#4a4a4a", None, 2)
for x, t in ((6, "Location"), (64, "Spool"), (110, "Batch"), (160, "kg"), (196, "Tube")):
    s.text(x0 + x, y0 + 12, t, 9, "#ffffff", True)
rows = (("C31", "#927", "GH11", "10.6", ("#ffc0cb", "#800080"), True),
        ("C31", "#928", "GH11", "10.6", ("#ffc0cb", "#800080"), False),
        ("D52", "#940", "GH12", "9.8", ("#1a1a1a", "#ffff00"), False))
for r, (loc, sp, b, kg, tube, bold) in enumerate(rows):
    y = y0 + 16 + r * 20
    s.rect(x0, y, 276, 20, "#ffffff" if loc == "C31" else STRIPE_A, "#e0e0e0", 0)
    for x, t in ((6, loc), (64, sp), (110, b), (160, kg)):
        s.text(x0 + x, y + 14, t, 9, INK, bold)
    s.rect(x0 + 196, y + 5, 5, 10, tube[0], None, 0)
    s.rect(x0 + 201, y + 5, 5, 10, tube[1], None, 0)
    s.rect(x0 + 196, y + 5, 10, 10, "none", "#7A7A7A", 0)
save(s, "wn_spool_locations.svg")

s = new("Notes on values")
NOTE = "#5E35B1"
grid(s, 12, 14, [("Air Pressure", ["3.5", "4.0", "3.5"]), ("Tenacity", ["38.2", "29.6", "37.9"])],
     3, 34, 22, first_w=72, header=["V1", "V2", "V3"])
# triangle on V2 / Tenacity
tx, ty = 12 + 72 + 34 * 2, 14 + 22 * 2
s.parts.append(f'  <polygon points="{tx - 7},{ty} {tx},{ty} {tx},{ty + 7}" fill="{NOTE}"/>')
# tooltip with the note
s.rect(186, 30, 104, 54, "#ffffff", NOTE, 4)
s.text(193, 46, "Spool had knots,", 9, INK)
s.text(193, 58, "measured again", 9, INK)
s.text(193, 75, "- M. Keller, 28.10.", 8, MUTED)
s.line(tx + 1, ty + 3, 186, 52, NOTE, 1)
s.btn(12, 100, "Add note…", 70, "grey", h=20, size=9)
s.text(90, 114, "right-click a value", 9, MUTED)
save(s, "wn_cell_notes.svg")

s = new("New Smart Chart")
# filter chips
for i, txt in enumerate(("Material: PES", "End titer 70 – 80 dtex", "Filaments 30 – 40")):
    s.rect(12, 12 + i * 26, 108, 22, "#E6F2E9", GREEN, 5)
    s.text(18, 27 + i * 26, txt, 8, INK)
s.rect(12, 92, 108, 20, "#ffffff", "#9FB39F", 5)
s.text(66, 106, "+ Add filter", 8, GREEN, True, "middle")
# counter
s.rect(130, 12, 158, 22, "#E6F2E9", "#BFDCC7", 5)
s.text(138, 27, "312 trials · 41 series", 9, INK, True)
# mini scatter
s.line(140, 118, 284, 118, MUTED, 1)
s.line(140, 42, 140, 118, MUTED, 1)
pts = [(152, 98), (160, 92), (172, 90), (184, 84), (196, 80), (208, 74), (220, 70), (232, 66), (246, 60), (260, 56),
       (166, 104), (190, 92), (214, 84), (238, 78), (262, 70), (274, 64)]
for i, (x, y) in enumerate(pts):
    s.parts.append(f'  <circle cx="{x}" cy="{y}" r="3.2" fill="{["#2F6DB5", "#D9822B"][i // 10]}"/>')
s.text(212, 128, "Air pressure", 8, MUTED, anchor="middle")
save(s, "wn_smart_chart.svg")

s = new("Is this comparison fair")
s.rect(12, 10, 276, 40, "#FFF4D6", "#E8C15A", 6)
s.parts.append('  <circle cx="26" cy="23" r="6" fill="#C98A00"/>')
s.text(38, 27, "Comparison partly fair", 10, INK, True)
s.text(38, 41, "Groups differ in material and air pressure", 8, MUTED)
s.btn(196, 16, "Details", 44, "grey", h=18, size=8)
s.btn(244, 16, "Fairer", 40, "grey", h=18, size=8)
for i, (lab, col, xs) in enumerate((("Jet A", "#2F6DB5", (160, 172, 184, 196, 208)),
                                    ("Jet B", "#D9822B", (40, 52, 64, 76, 88)))):
    for j, x in enumerate(xs):
        s.parts.append(f'  <circle cx="{x + 10}" cy="{100 - j * 6 - i * 14}" r="3.4" fill="{col}"/>')
    s.text(170 - i * 150, 126, f"{lab}: {'PES 3.5 bar' if i == 0 else 'PA 2 bar'}", 8, col, True)
s.line(14, 112, 286, 112, MUTED, 1)
save(s, "wn_fairness.svg")

s = new("Dashboard like Power BI")
# canvas with tiles
for x, y, w, h in ((12, 12, 56, 26), (72, 12, 56, 26), (132, 12, 56, 26)):
    s.rect(x, y, w, h, "#ffffff", LINE, 4)
s.text(40, 30, "2'516", 10, GREEN, True, "middle")
s.text(100, 30, "124", 10, GREEN, True, "middle")
s.text(160, 30, "71 %", 10, GREEN, True, "middle")
s.rect(12, 44, 86, 74, "#ffffff", LINE, 4)
for i, (h, c) in enumerate(((30, "#2F6DB5"), (44, "#2F6DB5"), (22, "#2F6DB5"))):
    s.rect(24 + i * 24, 108 - h, 14, h, c, None, 2)
s.rect(102, 44, 86, 74, "#ffffff", LINE, 4)
cols = ["#D8504A", "#F1A340", "#8CC63F", "#2E9E4F"]
for r in range(3):
    for c in range(4):
        if (r, c) in ((0, 3), (2, 0)):
            s.rect(108 + c * 19, 52 + r * 20, 17, 18, "#ffffff", "#B9C2B8", 2)
        else:
            s.rect(108 + c * 19, 52 + r * 20, 17, 18, cols[(r + c) % 4], None, 2)
# fields pane
s.rect(196, 12, 92, 106, "#ffffff", LINE, 4)
s.text(204, 26, "Fields", 9, GREEN, True)
for i, t in enumerate(("Yarn", "Jet", "Statimat", "Itemat Plus", "DTYoMat", "General")):
    s.text(206, 42 + i * 13, "▸ " + t, 8, INK)
save(s, "wn_dashboard.svg")

s = new("Lab statistics in the dashboard")
for i, (x, num, lab) in enumerate(((12, "140", "experiments"), (82, "392", "trial series"), (152, "13'520", "trials"))):
    s.rect(x, 10, 66, 32, "#ffffff", LINE, 4)
    s.text(x + 33, 26, num, 11, GREEN, True, "middle")
    s.text(x + 33, 37, lab, 7, MUTED, anchor="middle")
s.rect(12, 48, 206, 72, "#ffffff", LINE, 4)
stack = ((10, 6, 3), (16, 4, 2), (12, 8, 0), (6, 3, 2), (18, 7, 4), (14, 5, 3), (9, 6, 1))
for i, parts in enumerate(stack):
    y = 112
    for h, c in zip(parts, ("#2F6DB5", "#D9822B", "#4B5058")):
        s.rect(26 + i * 26, y - h * 2, 16, h * 2, c, None, 0)
        y -= h * 2
s.rect(224, 10, 64, 110, "#ffffff", LINE, 4)
s.text(232, 24, "Order type", 8, GREEN, True)
for i, (t, on) in enumerate((("Development", True), ("Customer", True), ("Internal", False))):
    s.rect(230, 32 + i * 18, 52, 14, "#1F7A3A" if on else "#ffffff", LINE, 3)
    s.text(256, 42 + i * 18, t, 7, "#ffffff" if on else INK, anchor="middle")
save(s, "wn_dashboard_stats.svg")

s = new("Dashboards to look at and share")
s.rect(12, 10, 86, 110, "#ffffff", LINE, 4)
s.text(18, 24, "My dashboards", 8, INK, True)
s.rect(16, 29, 78, 14, "#E3F1E6", None, 2)
s.text(20, 39, "Lab statistics", 8, INK)
s.text(20, 54, "Jet check", 8, INK)
s.text(18, 72, "Shared with me", 8, INK, True)
s.text(20, 87, "Yarn overview", 8, INK)
s.text(20, 101, "Machines 2026", 8, INK)
s.rect(104, 10, 120, 110, "#ffffff", LINE, 4)
s.rect(110, 16, 52, 24, "#ffffff", LINE, 3)
s.text(136, 32, "140", 10, GREEN, True, "middle")
s.rect(166, 16, 52, 24, "#ffffff", LINE, 3)
s.text(192, 32, "392", 10, GREEN, True, "middle")
for i, h in enumerate((30, 46, 22, 38, 52)):
    s.rect(116 + i * 20, 112 - h, 12, h, "#2F6DB5", None, 1)
s.rect(230, 10, 58, 110, "#ffffff", LINE, 4)
s.text(236, 24, "Share", 8, GREEN, True)
for i, (t, r) in enumerate((("Anna", "view"), ("write", "edit"), ("Ben", "view"))):
    y = 32 + i * 26
    s.rect(234, y, 50, 22, "#F4F6F3", LINE, 3)
    s.text(238, y + 10, t, 7, INK, True)
    s.text(238, y + 19, r, 7, MUTED)
save(s, "wn_dashboards.svg")

s = new("Format a visual")
s.rect(12, 10, 176, 110, "#ffffff", LINE, 4)
s.text(20, 24, "FP/m by jet", 8, INK, True)
for i, (h, lab) in enumerate(((66, "128"), (55, "112"), (45, "98"), (35, "85"), (25, "71"))):
    s.rect(28 + i * 31, 110 - h, 22, h, "#2F6DB5", None, 2)
    s.text(39 + i * 31, 106 - h, lab, 7, INK, anchor="middle")
s.rect(196, 10, 92, 110, "#ffffff", LINE, 4)
s.text(214, 24, "Build", 8, MUTED, anchor="middle")
s.text(260, 24, "Format", 8, GREEN, True, anchor="middle")
s.rect(242, 27, 38, 2, GREEN, None, 0)
for i, (t, val) in enumerate((("Order", "high to low"), ("Top", "5"), ("Decimals", "0"), ("Labels", "On"))):
    y = 36 + i * 21
    s.text(202, y + 6, t, 7, MUTED, True)
    s.rect(202, y + 9, 80, 10, "#ffffff", LINE, 2)
    s.text(205, y + 17, val, 7, INK)
save(s, "wn_dashboard_format.svg")

s = new("New dashboard visuals")
s.rect(12, 10, 84, 110, "#ffffff", LINE, 4)
s.circle(54, 52, 28, "#8CC63F")
s.path("M54 52 L54 24 A28 28 0 0 1 78.2 66 Z", "#1F7A3A")
s.path("M54 52 L78.2 66 A28 28 0 0 1 43 77.8 Z", "#232E3A")
s.circle(54, 52, 13, "#ffffff")
s.text(54, 104, "Pie / donut", 8, INK, True, "middle")
s.rect(104, 10, 92, 110, "#ffffff", LINE, 4)
s.line(110, 30, 190, 30, "#C62828", 1, "3 2")
s.line(110, 70, 190, 70, "#C62828", 1, "3 2")
s.line(110, 50, 190, 50, "#232E3A", 1)
pts = [(114, 52), (124, 44), (134, 57), (144, 47), (154, 54), (164, 42), (174, 49), (184, 24)]
s.polyline(pts, "#1F7A3A", 1.6)
for x, y in pts:
    s.circle(x, y, 2.2, "#C62828" if y < 30 else "#1F7A3A")
s.text(150, 104, "Control chart", 8, INK, True, "middle")
s.rect(204, 10, 84, 110, "#ffffff", LINE, 4)
s.polygon([(246, 22), (272, 42), (262, 76), (230, 76), (220, 42)], None, "#C9D1C8", 1)
s.polygon([(246, 28), (266, 44), (256, 70), (233, 72), (226, 44)], "#1F7A3A", "#1F7A3A", 1.4, 0.3)
s.polygon([(246, 36), (262, 45), (260, 72), (238, 68), (230, 46)], None, "#8CC63F", 1.6)
s.text(246, 104, "Radar", 8, INK, True, "middle")
save(s, "wn_dashboard_visuals.svg")

s = new("Model view")
s.rect(12, 10, 276, 110, "#ffffff", LINE, 4)
for i, t in enumerate(("Yarn per ply", "Jet", "Experiment")):
    y = 22 + i * 32
    s.rect(20, y, 64, 20, "#ffffff", "#232E3A", 3)
    s.text(26, y + 13, t, 7, INK, True)
    s.line(84, y + 10, 104, y + 10, "#232E3A", 1)
s.line(104, 32, 104, 96, "#232E3A", 1)
s.line(104, 65, 116, 65, "#232E3A", 1)
s.rect(116, 54, 64, 22, "#F0F7F2", "#1F7A3A", 3)
s.text(124, 68, "Trial", 9, GREEN, True)
s.line(180, 65, 196, 65, "#8CC63F", 1)
s.line(196, 22, 196, 104, "#8CC63F", 1)
for i, t in enumerate(("Statimat", "Itemat Plus", "DTYoMat", "Titer")):
    y = 14 + i * 26
    s.line(196, y + 10, 208, y + 10, "#8CC63F", 1)
    s.rect(208, y, 72, 20, "#ffffff", "#8CC63F", 3)
    s.text(214, y + 13, t, 7, INK, True)
save(s, "wn_model_view.svg")

s = new("Analytics and drill-through")
s.rect(10, 10, 160, 110, "#ffffff", LINE, 4)
s.rect(18, 44, 146, 30, "#E3F3E7", None, 0)
s.text(22, 54, "Spec 80 - 120", 7, GREEN, True)
for i, hgt in enumerate((52, 70, 40, 62, 30)):
    s.rect(26 + i * 27, 110 - hgt, 18, hgt, GREEN, None, 1)
s.line(18, 60, 164, 60, "#1565C0", 1.4, "3,3")
s.text(164, 57, "Average 102", 7, "#1565C0", True, "end")
s.line(18, 30, 164, 30, "#00838F", 1.2, "3,3")
s.text(164, 27, "+2 SD", 7, "#00838F", True, "end")
s.rect(60, 70, 96, 40, "#ffffff", "#C9D1C8", 4)
s.text(66, 82, "DRILL THROUGH", 6, MUTED, True)
s.rect(64, 88, 88, 16, "#F0F7F2", None, 3)
s.text(70, 99, "Machine details", 8, GREEN, True)
s.arrow_right(176, 64, 196)
s.rect(200, 10, 90, 110, "#ffffff", LINE, 4)
s.rect(206, 16, 78, 16, "#FFF6E0", "#F0D58A", 3)
s.text(210, 27, "<- Back  AFK", 7, INK, True)
s.rect(206, 38, 78, 28, "#ffffff", LINE, 3)
s.text(212, 50, "Trials", 7, MUTED)
s.text(212, 62, "14", 11, GREEN, True)
s.rect(206, 72, 78, 42, "#ffffff", LINE, 3)
for i, hgt in enumerate((20, 30, 14)):
    s.rect(216 + i * 22, 110 - hgt, 14, hgt, "#B7D9BF", GREEN, 1)
save(s, "wn_dashboard_analytics.svg")

s = new("Click to highlight")
FADE, DARK, LIGHT = "#C8DCCB", "#1F7A3A", "#8CC63F"
s.rect(10, 10, 132, 110, "#ffffff", LINE, 4)
s.text(18, 24, "FP/m by machine", 8, INK, True)
for i, h in enumerate((44, 70, 36, 56)):
    s.rect(24 + i * 28, 108 - h, 20, h, DARK if i == 1 else FADE, None, 2)
s.path("M60 46 L60 60 L64 56 L67 63 L70 62 L67 55 L72 55 Z", INK)
s.rect(150, 10, 138, 52, "#ffffff", LINE, 4)
for i, (full, part) in enumerate(((30, 6), (40, 22), (24, 0), (34, 12))):
    x = 162 + i * 30
    s.rect(x, 56 - full, 18, full, FADE, None, 1)
    if part:
        s.rect(x, 56 - part, 18, part, DARK, None, 1)
s.rect(150, 68, 138, 52, "#ffffff", LINE, 4)
for i, (x, y) in enumerate(((168, 104), (180, 92), (196, 100), (206, 84), (222, 90), (236, 78), (248, 96), (262, 82),
                             (274, 88), (190, 86), (230, 102), (256, 76))):
    s.circle(x, y, 3, DARK if i in (1, 3, 9) else "#D3D8DD")
save(s, "wn_click_highlight.svg")

s = new("Count different values")
s.rect(12, 14, 104, 102, "#ffffff", LINE, 4)
s.text(20, 30, "Aggregation", 8, MUTED, True)
for i, (lab, on) in enumerate((("Average", False), ("Count of trials", False), ("Count (distinct)", True),
                               ("Sum", False))):
    if on:
        s.rect(16, 38 + i * 18, 96, 16, "#E3F1E6", GREEN, 2)
    s.text(22, 50 + i * 18, lab, 8, INK, on)
s.arrow_right(122, 66, 148)
s.rect(154, 22, 134, 86, "#ffffff", LINE, 6)
s.text(221, 40, "Count of Jet (distinct)", 9, INK, True, "middle")
s.text(221, 80, "12", 30, "#1F7A3A", True, "middle")
s.text(221, 98, "different Jet in 340 trials", 8, MUTED, False, "middle")
save(s, "wn_distinct_count.svg")

s = new("One row per value")
s.rect(12, 12, 276, 106, "#ffffff", LINE, 4)
s.rect(12, 12, 276, 18, "#F4F6F3", None, 4)
for x, lab in ((20, "Jet"), (170, "Trials"), (230, "Series")):
    s.text(x, 25, lab, 9, INK, True)
for i, (jet, n, ser) in enumerate((("APe142", "50", "5"), ("APe143", "29", "4"), ("S315", "18", "3"),
                                   ("P212", "12", "2"))):
    y = 46 + i * 19
    s.line(16, y - 13, 284, y - 13, LINE, 0.6)
    s.text(20, y, jet, 9, INK)
    s.text(170, y, n, 9, INK)
    s.text(230, y, ser, 9, INK)
save(s, "wn_value_table.svg")

# ── Create Experiment ───────────────────────────────────────────────────
s = new("Search material and jets")
s.rect(12, 10, 276, 22, "#ffffff", GREEN, 4)
s.text(20, 25, "pa6 44", 10, INK)
s.line(56, 14, 56, 28, INK, 1)
s.text(278, 25, "x", 9, MUTED, False, "end")
s.rect(12, 36, 276, 84, "#ffffff", LINE, 4)
s.text(20, 52, "v  2 | Non Standard Yarn", 9, GREEN, True)
for i, (yarn, stock) in enumerate((("PA6 POY 52/44f36", True), ("PA6 FDY 44f34", False),
                                   ("PA6 HOY 44f12", True))):
    y = 70 + i * 18
    if i == 0:
        s.rect(14, y - 13, 272, 18, "#b7d6ff", None, 0)
    s.rect(34, y - 9, 10, 10, "#ffffff", MUTED, 1)
    s.text(50, y, yarn, 9, INK)
    spool(s, 262, y - 12, stock)
save(s, "wn_create_search.svg")

# ── Onboarding ──────────────────────────────────────────────────────────
s = new("Onboarding")
s.rect(12, 10, 70, 110, "#ffffff", LINE, 4)
s.text(18, 26, "Topics", 9, INK, True)
s.rect(14, 32, 66, 16, "#E3F1E6", None, 2)
s.text(18, 44, "DTY", 9, INK)
s.rect(88, 10, 200, 110, "#ffffff", LINE, 4)
s.rect(88, 10, 200, 14, "#ffffff", None, 0)
for i, (lab, sel) in enumerate((("Machine", True), ("Yarn", False), ("Jet", False))):
    s.rect(92 + i * 40, 12, 38, 12, "#000000" if sel else "#ffffff", "#cfcfcf", 0)
    s.text(111 + i * 40, 21, lab, 6, GREEN, False, "middle")
for i, f in enumerate(("#3d7fd6", "#000000", "#AA151B", "#DE2910")):
    s.rect(212 + i * 18, 13, 14, 9, f, "#999999", 1)
s.polyline([(100, 100), (130, 70), (170, 70), (190, 88), (216, 88), (240, 88), (262, 104)], "#6E6556", 1.5)
s.circle(190, 88, 6, "#93a3a2")
s.rect(210, 81, 14, 14, "#2386C8", None, 2)
s.circle(250, 88, 6, "#93a3a2")
s.line(184, 112, 252, 112, "#2386C8", 2)
s.text(218, 109, "OF", 8, "#2386C8", True, "middle")
save(s, "wn_onboarding.svg")

s = new("Who may use which tool")
s.rect(12, 10, 276, 110, "#ffffff", LINE, 4)
cols = ("read", "write", "Anna", "Ben")
for i, c in enumerate(cols):
    s.text(128 + i * 40, 26, c, 8, INK, True, "middle")
rows = (("Backlog", ("-", "No", "-", "Yes")), ("Smart Chart", ("-", "Yes", "yes", "No")),
        ("Yarn Stock", ("yes", "yes", "yes", "yes")), ("Canvas", ("yes", "yes", "No", "yes")))
for r, (lab, vals) in enumerate(rows):
    y = 34 + r * 20
    s.rect(16, y, 268, 18, "#F4F6F3" if r % 2 == 0 else "#ffffff", None, 0)
    s.text(22, y + 13, lab, 8, INK)
    for i, val in enumerate(vals):
        col = GREEN if val == "Yes" else "#C62828" if val == "No" else MUTED
        s.text(128 + i * 40, y + 13, val, 8, col, val in ("Yes", "No"), "middle")
save(s, "wn_feature_access.svg")

s = new("Your own start screen")
s.rect(12, 14, 276, 44, "#ffffff", LINE, 4)
s.text(22, 30, "Start screen", 9, GREEN, True)
s.text(22, 48, "After the login open:", 9, INK)
s.rect(140, 36, 140, 18, "#ffffff", BLUE, 3)
s.text(146, 49, "Dashboards", 9, INK)
s.text(270, 49, "v", 8, MUTED, anchor="middle")
for i, t in enumerate(("Backlog", "All Experiments", "Dashboards", "Yarn Stock")):
    y = 64 + i * 14
    s.rect(140, y, 140, 14, "#E3F1E6" if t == "Dashboards" else "#ffffff", LINE, 0)
    s.text(146, y + 10, t, 8, INK)
s.text(22, 88, "Default: Backlog", 8, MUTED)
save(s, "wn_start_screen.svg")

s = new("Stacked fields")
s.rect(12, 10, 276, 110, "#ffffff", LINE, 4)
parts = ((6, 52, 42), (4, 58, 38), (5, 60, 35), (7, 76, 17), (6, 78, 16), (8, 80, 12), (7, 79, 14))
for i, (a, b, c) in enumerate(parts):
    x, y0 = 24 + i * 28, 104
    for share, col in ((a, "#2F6DB5"), (b, "#D9822B"), (c, "#4B5058")):
        h = share * 0.84
        s.rect(x, y0 - h, 18, h, col, None, 0)
        y0 -= h
    s.text(x + 9, 116, f"V{i + 1}", 7, MUTED, anchor="middle")
for i, (t, col) in enumerate((("A knots", "#2F6DB5"), ("B knots", "#D9822B"), ("C knots", "#4B5058"))):
    s.rect(226, 24 + i * 16, 9, 9, col, None, 1)
    s.text(240, 32 + i * 16, t, 8, INK)
save(s, "wn_stacked_fields.svg")

s = new("Yarn colour")
s.rect(12, 10, 200, 20, "#ffffff", BLUE, 3)
s.text(20, 24, "Search yarn  e.g. 167 dty", 9, MUTED)
for i, (name, fill) in enumerate((("PES 167f48 DTY", "#FFFFFF"), ("PES 154f48 dtex black", "#1A1A1A"),
                                  ("CO spun Ne 30 natural", "#F3EAD3"), ("PA 78f68 grey", "#9A9A9A"))):
    y = 36 + i * 21
    s.rect(12, y, 200, 21, "#e8f0fb" if i == 1 else "#ffffff", LINE, 0)
    s.rect(18, y + 5, 11, 11, fill, "#7A7A7A", 0)
    s.text(36, y + 15, name, 9, INK)
s.rect(196, 58, 92, 22, "#FFFFE1", "#888888", 2)
s.text(242, 73, "Colour: black", 9, INK, anchor="middle")
save(s, "wn_yarn_colour.svg")

s = new("Reference sample")
s.btn(206, 10, "+ Ref", 44, "amber")
s.btn(254, 10, "+T", 30, "white")
s.rect(14, 42, 92, 18, "#4a4a4a", None, 2)
s.rect(106, 42, 60, 18, AMBER, None, 0)
s.text(136, 55, "Ref", 9, "#5a4500", True, "middle")
for i, v in enumerate(("V1", "V2")):
    s.rect(166 + 60 * i, 42, 60, 18, "#4a4a4a", None, 0)
    s.text(196 + 60 * i, 55, v, 9, "#ffffff", True, "middle")
for r, (t, vals) in enumerate((("Tenacity", ("38.2", "36.9", "37.4")), ("Elongation", ("24.1", "22.8", "23.5")),
                               ("Shrinkage", ("4.1", "4.6", "4.3")))):
    y = 60 + r * 20
    s.rect(14, y, 272, 20, STRIPE_A if r % 2 == 0 else STRIPE_B, "#c9dfcb", 0)
    s.rect(106, y, 60, 20, "#FFF4D6" if r % 2 == 0 else "#FBE8B5", "#c9dfcb", 0)
    s.text(19, y + 14, t, 9, INK)
    for c, v in enumerate(vals):
        s.text(136 + 60 * c, y + 14, v, 9, INK, anchor="middle")
save(s, "wn_reference.svg")

s = new("Copy trials")
s.rect(12, 10, 276, 110, "#ffffff", LINE, 6)
s.text(22, 28, "Copy trials", 11, INK, True)
for i, (t, on) in enumerate((("V1  SlideJet  1 bar  800 m/min", True), ("V2  SlideJet  2 bar  800 m/min", True),
                             ("V3  TexJet  2 bar  650 m/min", False))):
    y = 38 + i * 18
    s.rect(22, y, 11, 11, GREEN if on else "#ffffff", "#888888", 2)
    s.text(40, y + 9, t, 9, INK if on else MUTED)
s.text(22, 106, "2 copies  -  Repeat the block", 9, MUTED)
s.btn(200, 92, "Copy 4 trials", 78, "green")
save(s, "wn_copy_trials.svg")

s = new("D/Y Ratio")
grid(s, 14, 16, [("T1 Tension (cN)", ("22.10", "21.40")), ("T2 Tension (cN)", ("14.80", "14.90")),
                 ("D/Y Ratio (T2/T1)", ("0.67", "0.70"))], 2, 80, 22, first_w=110, header=["V1", "V2"],
     fills={(2, 0): "#f3f3f3", (2, 1): "#f3f3f3"})
s.text(150, 122, "calculated automatically", 9, MUTED, italic=True, anchor="middle")
save(s, "wn_dy_ratio.svg")

s = new("Hide rows")
s.btn(186, 8, "2 rows hidden", 100, "white")
y0 = 38
vals = {"Housing": "SlideJet", "Jet": "P212", "Speed (m/min)": "800"}
for r, t in enumerate(("Housing", "Jet", "Speed (m/min)")):
    y = y0 + r * 20
    s.rect(14, y, 272, 20, STRIPE_A if r % 2 == 0 else STRIPE_B, "#c9dfcb", 0)
    s.text(19, y + 14, t, 9, INK)
    for c in range(3):
        s.text(150 + 50 * c, y + 14, vals[t], 9, INK, anchor="middle")
s.line(16, y0 + 41, 108, y0 + 41, BLUE, 3)
s.text(14, y0 + 76, "Blue line: rows hidden here - click it to show them again", 8, BLUE, italic=True)
save(s, "wn_hide_rows.svg")

s = new("Unsaved changes")
s.rect(10, 8, 120, 16, "#ffffff", LINE, 3)
s.rect(10, 8, 120, 3, GREEN, None, 0)
s.rect(17, 14, 6, 6, INK, None, 3)
s.text(27, 20, "Show Experiment", 8, INK, True)
s.rect(212, 30, 70, 20, "#E8890C", None, 3)
s.text(247, 44, "Save (3)", 9, "#ffffff", True, "middle")
grid(s, 14, 52, [("Air Pressure (bar)", ["4.00", "4.50", "4.00"]), ("Overfeed (%)", ["8", "8", "10"]),
                 ("Jet Plate", ["1", "1", "2"])], 3, 52, 17, first_w=110, header=["V1", "V2", "V3"],
     fills={(0, 1): "#FFF1A8", (1, 2): "#FFF1A8", (2, 2): "#FFF1A8"})
save(s, "wn_unsaved.svg")

s = new("Unusual values")
s.rect(12, 10, 276, 110, "#ffffff", LINE, 6)
s.parts.append('  <polygon points="30,22 40,40 20,40" fill="#E6A100"/>')
s.text(30, 37, "!", 10, "#ffffff", True, "middle")
s.text(48, 34, "Unusual values", 11, INK, True)
s.text(22, 58, "V1 · Air Pressure (bar): 35", 9, INK, True)
s.text(22, 72, "(usually 1 - 5)   Typo?", 9, MUTED)
s.btn(22, 88, "Go back and check", 108, "green")
s.btn(136, 88, "Save anyway", 76, "white")
save(s, "wn_unusual.svg")

s = new("Change history")
s.rect(12, 10, 276, 110, "#ffffff", LINE, 6)
s.text(22, 28, "Change history", 11, INK, True)
for c, (h, x) in enumerate((("When", 22), ("Who", 110), ("Old", 190), ("New", 240))):
    s.text(x, 46, h, 9, INK, True)
s.line(22, 50, 278, 50, LINE, 1)
for r, row in enumerate((("15.10. 12:42", "J. Miller", "3.50", "4.25"), ("02.10. 09:15", "A. Rossi", "3.00", "3.50"))):
    for (v, x) in zip(row, (22, 110, 190, 240)):
        s.text(x, 66 + r * 18, v, 9, INK)
s.text(22, 112, "Right-click a value  >  Change history...", 8, MUTED, italic=True)
save(s, "wn_history.svg")

# ── Settings ────────────────────────────────────────────────────────────
s = new("Text size")
s.text(16, 28, "Text size (whole program)", 10, INK, True)
for i, (n, p) in enumerate((("Normal", "100 %"), ("Large", "125 %"), ("Extra large", "150 %"), ("Huge", "200 %"))):
    x = 16 + i * 68
    sel = i == 2
    s.rect(x, 38, 62, 40, NAVY if sel else "#eeeeee", None if sel else "#bbbbbb", 5)
    s.text(x + 31, 54, n, 8 if len(n) > 6 else 9, "#ffffff" if sel else INK, sel, "middle")
    s.text(x + 31, 68, p, 9, "#ffffff" if sel else INK, sel, "middle")
s.text(16, 100, "Aa", 12, INK)
s.text(40, 100, "Aa", 15, INK)
s.text(70, 100, "Aa", 19, INK, True)
s.text(104, 100, "Aa", 24, INK)
save(s, "wn_text_size.svg")

s = new("Easier reading")
rows = [("Housing", ("SlideJet", "SlideJet")), ("Air Pressure", ("3.50", "3.50")), ("Speed", ("800", "760"))]
y = grid(s, 14, 8, rows, 2, 64, 22, first_w=92, header=["V1", "V2"],
         fills={(0, 1): "#FFF3B8", (2, 1): "#FFF3B8", (1, 0): "#FFF3B8"})
s.rect(14, 30 + 22, 92, 22, "#FFD54F", "#c9dfcb", 0)
s.text(19, 30 + 22 + 16, "Air Pressure", 9, INK)
s.rect(170, 30 + 22, 64, 22, NAVY, None, 0)
s.text(202, 30 + 22 + 16, "3.50", 10, "#ffffff", True, "middle")
s.rect(14, 104, 272, 20, "#F4F7FB", "#9bbbe0", 2)
s.text(20, 118, "V2 · Air Pressure (bar) = 3.50", 10, INK, True)
save(s, "wn_reading.svg")

# ── Backlog / All Experiments ───────────────────────────────────────────
s = new("Wide Backlog")
for i, t in enumerate(("Backlog", "In Progress", "Done", "To Be Cleaned")):
    x = 12 + i * 70
    s.rect(x, 12, 64, 106, "#ffffff", LINE, 4)
    s.rect(x, 12, 64, 14, "#4a4a4a", None, 4)
    s.text(x + 32, 22, t, 7, "#ffffff", True, "middle")
    for k in range(4 if i < 3 else 2):
        s.rect(x + 4, 30 + k * 20, 56, 16, "#ffffff", "#dddddd", 3)
        s.rect(x + 4, 30 + k * 20, 3, 16, ["#e67e22", "#2980b9", "#8e44ad", GREEN][k % 4], None, 1)
    if i == 3:
        s.rect(x, 78, 64, 40, "#ffffff", LINE, 4)
        s.rect(x, 78, 64, 14, "#4a4a4a", None, 4)
        s.text(x + 32, 88, "Archived", 7, "#ffffff", True, "middle")
save(s, "wn_wide_backlog.svg")

s = new("Move several cards")
s.rect(12, 12, 118, 106, "#ffffff", LINE, 4)
s.rect(12, 12, 118, 16, "#4a4a4a", None, 4)
s.text(71, 24, "To Be Cleaned", 9, "#ffffff", True, "middle")
for k in range(4):
    sel = k != 2
    s.rect(18, 34 + k * 20, 106, 16, "#d8e7fa" if sel else "#ffffff", BLUE if sel else "#dddddd", 3)
    s.rect(24, 40 + k * 20, 60 if k % 2 else 74, 4, "#9aa7b5", None, 2)
s.text(71, 126, "Ctrl+click", 9, NAVY, True, "middle")
s.arrow_right(136, 64, 168, BLUE)
s.rect(172, 12, 116, 106, "#ffffff", LINE, 4)
s.rect(172, 12, 116, 16, "#4a4a4a", None, 4)
s.text(230, 24, "Archived", 9, "#ffffff", True, "middle")
s.rect(182, 48, 96, 32, "#ffffff", BLUE, 6, 1.5)
s.text(230, 69, "3 series", 11, NAVY, True, "middle")
save(s, "wn_backlog_multi_move.svg")

s = new("Recycle Bin")
s.rect(12, 10, 276, 110, "#ffffff", LINE, 6)
s.text(22, 28, "Recycle Bin", 11, INK, True)
s.rect(22, 38, 256, 18, "#d8e7fa", None, 2)
s.text(28, 51, "15.10.2026   01 Jet comparison S+   12 trials", 9, INK)
s.text(28, 69, "02.10.2026   03 PES 167f72 DTY      8 trials", 9, MUTED)
s.btn(22, 90, "Restore", 60, "green")
s.btn(88, 90, "Delete permanently", 112, "white")
s.text(278, 104, "90 days", 8, MUTED, italic=True, anchor="end")
save(s, "wn_recycle_bin.svg")

s = new("Recycle bin preview")
s.rect(10, 10, 280, 110, "#ffffff", LINE, 4)
s.rect(10, 10, 280, 14, "#4a4a4a", None, 4)
s.text(16, 20, "Show Experiment  2026-79-005", 8, "#ffffff", True)
s.rect(14, 28, 272, 30, AMBER_BG, AMBER, 3)
s.text(20, 40, "From the Recycle Bin - read only", 8, "#5a4500", True)
for i, (t, w) in enumerate((("Restore for good", 78), ("Back to Recycle Bin", 90), ("Delete permanently", 80))):
    x = 20 + sum((78, 90, 80)[:i]) + 4 * i
    s.rect(x, 44, w, 11, "#ffffff", "#c9b06a", 2)
    s.text(x + w / 2, 52, t, 7, INK, anchor="middle")
grid(s, 14, 62, [("Tenacity", ["38.2", "36.9"]), ("Elongation", ["24.1", "22.8"]), ("Shrinkage", ["4.1", "4.6"])],
     2, 60, 14, first_w=96, header=["V1", "V2"])
s.text(250, 104, "read only", 8, MUTED, anchor="middle")
save(s, "wn_recycle_preview.svg")

# ── Yarn Stock ──────────────────────────────────────────────────────────
s = new("Stock status per yarn")
heads = (("Yarn", 16), ("Yarn total (kg)", 112), ("Min. stock (kg)", 186), ("Status", 258))
s.rect(12, 14, 276, 18, "#4a4a4a", None, 2)
for h, x in heads:
    s.text(x, 27, h, 8, "#ffffff", True)
for r, (yarn, tot, mn, col) in enumerate((("PES 167f72", "84.2", "40", GREEN), ("PA6 78f68", "31.5", "30", "#E6A100"),
                                          ("PES 55f72", "8.0", "25", "#d9534f"))):
    y = 32 + r * 22
    s.rect(12, y, 276, 22, STRIPE_A if r % 2 == 0 else STRIPE_B, "#c9dfcb", 0)
    s.text(16, y + 15, yarn, 9, INK)
    s.text(140, y + 15, tot, 9, INK, anchor="middle")
    s.text(214, y + 15, mn, 9, INK, anchor="middle")
    s.parts.append(f'  <circle cx="268" cy="{y + 11}" r="6" fill="{col}"/>')
s.text(16, 116, "all batches of a yarn together vs. minimum stock", 8, MUTED, italic=True)
save(s, "wn_stock_status.svg")

s = new("New spools")
s.rect(12, 10, 276, 110, "#ffffff", LINE, 6)
s.text(22, 28, "New spool(s)", 11, INK, True)
s.text(22, 48, "Yarn   PES 167f72      Batch   B-2410", 9, INK)
s.text(22, 64, "Spools  4      Weight  5.0 kg", 9, INK)
s.rect(22, 74, 11, 11, GREEN, "#888888", 2)
s.text(40, 83, "Add new spools to the label queue", 9, INK)
s.btn(212, 94, "OK", 66, "green")
s.text(22, 108, "then jumps to the new spools", 8, MUTED, italic=True)
save(s, "wn_new_spools.svg")

s = new("Stock take")
s.rect(12, 10, 276, 110, "#ffffff", LINE, 6)
s.text(22, 26, "Stock take October 2026", 10, INK, True)
s.rect(22, 31, 256, 5, "#e6e6e6", None, 2)
s.rect(22, 31, 96, 5, "#3d7fd6", None, 2)
s.text(278, 26, "9 of 24 checked", 8, MUTED, anchor="end")
tiles = {"ok": ("#EAF3DE", "#9ccc8a", "#2b5d22"), "dev": ("#FAEEDA", "#e3b866", "#7a4d00"),
         "open": ("#f2f2f2", "#c8c8c8", "#444444"), "out": ("#ffffff", "#d0d0d0", "#a0a0a0")}
layout = [["ok", "ok", "dev", "ok"], ["ok", "dev", "ok", "open"], ["open", "open", "out", "open"]]
for r, row in enumerate(layout):
    for c, kind in enumerate(row):
        bg, border, fg = tiles[kind]
        x, y = 22 + c * 46, 42 + r * 25
        s.rect(x, y, 42, 21, bg, border, 3)
        s.text(x + 21, y + 9, f"C{r + 1}{c + 1}", 7, fg, True, "middle")
        sub = {"ok": "16/16", "dev": "14/16", "open": "16", "out": "-"}[kind]
        s.text(x + 21, y + 18, sub, 6, fg, anchor="middle")
s.rect(212, 42, 66, 71, "#fafafa", LINE, 3)
s.text(218, 54, "Results", 8, INK, True)
for i, (t, col) in enumerate((("#230 missing", "#d9534f"), ("#214 moved here", "#b9770e"), ("#311 seen C23", "#b9770e"))):
    s.text(218, 68 + i * 14, t, 7, col)
save(s, "wn_stock_take.svg")

s = new("Spool history")
s.rect(12, 10, 276, 110, "#ffffff", LINE, 6)
s.text(22, 28, "History  -  spool #213", 11, INK, True)
for r, (when, what) in enumerate((("13.10. 09:12", "created  (5.0 kg, C12)"), ("14.10. 15:40", "location C12 > C14"),
                                  ("15.10. 08:05", "stock take: found"), ("15.10. 10:31", "discarded (used up)"))):
    s.text(22, 48 + r * 17, when, 9, MUTED)
    s.text(100, 48 + r * 17, what, 9, INK)
save(s, "wn_spool_history.svg")

# ── Help ────────────────────────────────────────────────────────────────
s = new("Help in three languages")
s.rect(12, 10, 276, 110, "#ffffff", LINE, 6)
s.parts.append(f'  <circle cx="270" cy="24" r="9" fill="#ffffff" stroke="{GREEN}" stroke-width="1.5"/>')
s.text(270, 28, "?", 11, GREEN, True, "middle")
# Union Jack (simplified), German and Spanish flag - like the help's language flags
s.rect(22, 16, 22, 15, "#012169", None, 0)
s.line(22, 16, 44, 31, "#ffffff", 3)
s.line(44, 16, 22, 31, "#ffffff", 3)
s.line(22, 16, 44, 31, "#C8102E", 1)
s.line(44, 16, 22, 31, "#C8102E", 1)
s.rect(30, 16, 6, 15, "#ffffff", None, 0)
s.rect(22, 21, 22, 5, "#ffffff", None, 0)
s.rect(31.5, 16, 3, 15, "#C8102E", None, 0)
s.rect(22, 22, 22, 3, "#C8102E", None, 0)
for i, (c1, c2, c3) in enumerate((("#000000", "#DD0000", "#FFCE00"), ("#AA151B", "#F1BF00", "#AA151B")), start=1):
    x = 22 + i * 30
    for k, (c, h) in enumerate(zip((c1, c2, c3), (5, 5, 5) if i == 1 else (4, 7, 4))):
        y = 16 + (k * 5 if i == 1 else (0, 4, 11)[k])
        s.rect(x, y, 22, h, c, None, 0)
s.text(22, 52, "How do I…?", 10, INK, True)
s.rect(22, 60, 256, 50, "#f6fbf6", "#d5ecd8", 4)
s.text(30, 75, "Copy existing trials", 9, INK, True)
s.text(30, 89, "1. Click Copy trials …", 9, MUTED)
s.text(30, 102, "2. Tick the trials to copy …", 9, MUTED)
save(s, "wn_help.svg")

s = new("Help search")
s.rect(12, 10, 276, 110, "#ffffff", LINE, 6)
s.text(22, 28, "Help  (F1)", 11, INK, True)
s.rect(22, 36, 256, 20, "#ffffff", "#9bbbe0", 3)
s.text(28, 50, "where are all orders of a machine?", 8, INK)
for r, t in enumerate(("All Experiments: Filter by machine", "Backlog: Find a trial series", "Show Experiment: Open a series")):
    s.rect(22, 62 + r * 18, 256, 16, "#d8e7fa" if r == 0 else "#ffffff", None if r == 0 else "#eeeeee", 2)
    s.text(28, 74 + r * 18, t, 9, INK, r == 0)
save(s, "wn_help_search.svg")

s = new("What's new search")
s.rect(12, 10, 276, 110, "#ffffff", LINE, 6)
s.rect(20, 18, 86, 18, "#ffffff", "#9bbbe0", 3)
s.text(25, 31, "barcode", 9, INK)
for r, (v, hits) in enumerate((("Version 4.7.0", ""), ("Version 4.6.5", "2 hits"), ("Version 4.6.2", ""))):
    y = 42 + r * 24
    s.rect(20, y, 86, 22, "#d8e7fa" if hits else "#ffffff", "#eeeeee", 2)
    s.text(25, y + 10, v, 8, INK if hits else "#b0b0b0", bool(hits))
    if hits:
        s.text(25, y + 19, hits, 7, GREEN, True)
s.text(116, 30, "Version 4.6.5", 9, MUTED, True)
for r, t in enumerate(("Barcode scanner", "Print barcode labels")):
    y = 38 + r * 38
    s.rect(116, y, 164, 32, "#ffffff", LINE, 4)
    s.rect(116, y, 4, 32, GREEN, None, 0)
    s.text(126, y + 13, t, 9, INK, True)
    s.rect(126, y + 19, 120, 4, "#e2e2e2", None, 2)
save(s, "wn_whats_new_search.svg")

s = new("What's new as PDF")
s.rect(12, 10, 120, 110, "#ffffff", LINE, 6)
s.text(20, 28, "Fresh off the Spool", 9, INK, True)
for r in range(3):
    s.rect(20, 34 + r * 19, 104, 15, "#ffffff", LINE, 3)
    s.rect(20, 34 + r * 19, 3, 15, GREEN, None, 0)
    s.rect(28, 40 + r * 19, 70, 4, "#cfcfcf", None, 2)
s.btn(20, 93, "PDF", 40, "white")
s.text(150, 66, "→", 18, MUTED, True, "middle")
for i, (x, n) in enumerate(((168, 2), (232, 3))):
    s.rect(x, 14, 56, 80, "#ffffff", LINE, 2)
    s.rect(x + 5, 20, 34, 4, NAVY, None, 1)
    s.rect(x + 5, 27, 46, 1, GREEN, None, 0)
    for r in range(n):
        s.rect(x + 5, 32 + r * 19, 46, 16, "#ffffff", LINE, 2)
        s.rect(x + 5, 32 + r * 19, 2, 16, GREEN, None, 0)
    s.text(x + 28, 108, f"page {i + 1}", 8, MUTED, anchor="middle")
save(s, "wn_whats_new_pdf.svg")

# ── All Experiments ─────────────────────────────────────────────────────
s = new("All Experiments full width")
s.rect(10, 10, 280, 110, "#ffffff", LINE, 4)
s.rect(10, 10, 280, 16, "#4a4a4a", None, 4)
for x, h in ((16, "Exp. ID"), (64, "Trial Series Name"), (210, "Machine"), (258, "RE")):
    s.text(x, 21, h, 7, "#ffffff", True)
for r in range(5):
    y = 26 + r * 18
    s.rect(10, y, 280, 18, STRIPE_A if r % 2 == 0 else "#ffffff", None, 0)
    s.text(16, y + 12, f"2026-7{r}-0{r + 3}", 8, INK)
    s.text(64, y + 12, ["Jet comparison S+ series", "PES 167f72 DTY trials", "TexJet D11 vs N12",
                        "Overfeed series X48", "ATY core/effect"][r], 8, INK)
    s.text(210, y + 12, ["eAFK", "SSM", "eAFK", "RPR", "ATY"][r], 8, INK)
    s.rect(262, y + 4, 10, 10, GREEN, None, 2)
s.arrow_right(150, 124, 290, GREEN)
s.parts.append(f'  <polygon points="10,124 18,120 18,128" fill="{GREEN}"/>')
s.line(18, 124, 150, 124, GREEN, 1.5)
save(s, "wn_all_experiments.svg")
