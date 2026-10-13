"""Erzeugt die Hilfe-Skizzen (Plain SVG Tiny fuer QSvgWidget):
assets/images/help_backlog.svg, help_show_experiment.svg, help_report.svg

Aufruf: python tools/gen_help_svgs.py  (ueberschreibt die drei Dateien)
Bildschirmbeschriftungen bleiben englisch wie in der App; {{key}}-Platzhalter
werden pro Sprache aus ui/widgets/help_texts_*.py befuellt. Keine Emojis oder
seltenen Symbole verwenden - der Qt-SVG-Renderer zeigt sie als Kaestchen.
"""
import os
from xml.sax.saxutils import escape as esc

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "images")
FONT = 'font-family="Segoe UI, Arial, sans-serif"'
INK, MUTED, GREEN, LINE = "#2b2b2b", "#565656", "#39a650", "#cccccc"


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h = w, h
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
                      f'  <!-- {title} - generated, language-neutral (UI labels are English in the app). -->',
                      f'  <rect x="0" y="0" width="{w}" height="{h}" fill="#ffffff"/>']

    def rect(self, x, y, w, h, fill="#ffffff", stroke=LINE, rx=4, sw=1):
        st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        self.parts.append(f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{st}/>')

    def text(self, x, y, t, size=12, fill=INK, bold=False, anchor="start", italic=False):
        extra = (' font-weight="bold"' if bold else "") + (' font-style="italic"' if italic else "")
        self.parts.append(f'  <text x="{x}" y="{y}" {FONT} font-size="{size}" fill="{fill}" '
                          f'text-anchor="{anchor}"{extra}>{esc(t)}</text>')

    def btn(self, x, y, label, w=None, kind="grey", h=22, size=10):
        w = w or max(26, int(len(label) * 5.6) + 10)
        fill, stroke, tc = {"grey": ("#e6e6e6", "#bbbbbb", INK), "green": (GREEN, None, "#ffffff"),
                            "purple": ("#8e44ad", None, "#ffffff"), "white": ("#ffffff", "#999999", INK)}[kind]
        self.rect(x, y, w, h, fill, stroke, 3)
        self.text(x + w / 2, y + h / 2 + 4, label, size, tc, anchor="middle")
        return x + w

    def marker(self, cx, cy, label, fill=GREEN):
        self.parts.append(f'  <circle cx="{cx}" cy="{cy}" r="11" fill="{fill}"/>')
        self.text(cx, cy + 4, label, 11, "#ffffff", True, "middle")

    def line(self, x1, y1, x2, y2, color=MUTED, sw=1.5, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"{d}/>')

    def arrow_right(self, x1, y, x2, color=MUTED):
        self.line(x1, y, x2 - 7, y, color)
        self.parts.append(f'  <polygon points="{x2},{y} {x2-8},{y-4} {x2-8},{y+4}" fill="{color}"/>')

    def save(self, name):
        self.parts.append("</svg>")
        with open(os.path.join(ROOT, name), "w", encoding="utf-8") as fh:
            fh.write("\n".join(self.parts) + "\n")
        print("wrote", name)


# ═════════════════════════════ Backlog ═════════════════════════════
s = Svg(940, 500, "Backlog help sketch")
s.rect(40, 6, 890, 300, "#f4f4f4", LINE, 8)
cols = [(56, 18, "Backlog", "1"), (493, 18, "In Progress", "2"), (56, 162, "Done", "3"), (493, 162, "To Be Cleaned", "4")]
for x, y, title, m in cols:
    h = 134 if title != "To Be Cleaned" else 62
    s.rect(x, y, 422, h, "#ffffff", LINE, 6)
    s.rect(x, y, 422, 24, "#4a4a4a", None, 6)
    s.text(x + 10, y + 17, title, 12, "#ffffff", True)
    s.rect(x + 398, y + 7, 10, 10, "#4a4a4a", "#ffffff", 1)
    s.marker(x - 10 if x < 100 else x - 10, y + 12, m)
    n = 3 if h > 100 else 1
    for i in range(n):
        cy = y + 32 + i * 33
        s.rect(x + 8, cy, 406, 28, "#ffffff", "#e0e0e0", 6)
        if title in ("In Progress", "Done"):
            s.rect(x + 8, cy, 4, 28, ["#e67e22", "#2980b9", "#8e44ad"][i % 3], None, 2)
        s.text(x + 18, cy + 12, ["X60.112 stability", "PES 167f72 DTY trials", "Jet comparison S+"][i % 3], 10, INK, True)
        s.text(x + 18, cy + 23, "2026-73-035  •  RPR 3SDS  •  Prio 2  •  owner", 8, MUTED)
# Archived
s.rect(493, 232, 422, 66, "#ffffff", LINE, 6)
s.rect(493, 232, 422, 24, "#4a4a4a", None, 6)
s.text(503, 249, "Archived", 12, "#ffffff", True)
s.marker(483, 244, "5")
s.rect(501, 260, 160, 18, "#ffffff", "#999999", 3)
s.text(507, 273, "Search in Archived…", 9, "#999999")
s.text(670, 273, "▶ 2026   ▶ 73  (12)", 9, MUTED)
s.text(503, 292, "{{archived_hint}}", 8, MUTED, italic=True)

# Status flow
s.text(56, 330, "{{flow_title}}", 12, INK, True)
flow = ["Backlog", "In Progress", "Done", "To Be Cleaned", "Archived"]
x = 56
for i, f in enumerate(flow):
    w = 130
    s.rect(x, 340, w, 26, "#e8f5e9" if i < 3 else "#eeeeee", GREEN if i < 3 else "#bbbbbb", 13)
    s.text(x + w / 2, 357, f, 11, INK, anchor="middle")
    if i < len(flow) - 1:
        s.arrow_right(x + w + 2, 353, x + w + 46)
    x += w + 48
s.text(56, 384, "{{flow_hint}}", 10, MUTED, italic=True)

# Card anatomy
s.text(56, 410, "{{card_title}}", 12, INK, True)
s.rect(56, 424, 860, 58, "#ffffff", "#e0e0e0", 10)
s.rect(56, 424, 6, 58, "#e67e22", None, 3)
s.text(76, 446, "X60.112 stability", 13, INK, True)
s.text(76, 468, "2026-73-035  •  RPR 3SDS  •  In Progress  •  Prio 2  •  Owner name", 10, MUTED)
s.rect(650, 441, 54, 18, "#e67e22", None, 4)
s.text(677, 454, "RETEST", 9, "#ffffff", True, "middle")
for i, (sym, lbl) in enumerate([("chart", ""), ("note", ""), ("file", ""), ("ER", "")]):
    cx = 724 + i * 40
    s.rect(cx, 440, 32, 20, "#f2f2f2", "#cccccc", 4)
    s.text(cx + 16, 454, sym, 9, INK, anchor="middle")
s.marker(44, 453, "A", "#2b2b2b")     # stripe
s.marker(250, 441, "B", "#2b2b2b")  # title
s.marker(640, 432 - 6, "C", "#2b2b2b")  # retest
s.marker(740, 426, "D", "#2b2b2b")  # report
s.marker(820, 426, "E", "#2b2b2b")  # attach
s.marker(860, 426, "F", "#2b2b2b")  # ER
s.save("help_backlog.svg")

# ═════════════════════════════ Show Experiment ═════════════════════════════
s = Svg(940, 384, "Show Experiment help sketch")
s.rect(40, 6, 890, 372, "#f4f4f4", LINE, 8)
# Toolbar
s.marker(22, 30, "1")
s.text(56, 34, "2026-73-035 · X60.112", 11, INK, True)
x = 196
for lbl, kind in [("Upload images", "grey"), ("img", "white"), ("Upload PDFs", "grey"), ("pdf", "white"),
                  ("Statimat import", "grey"), ("Itemat import", "grey"), ("chart", "white")]:
    x = s.btn(x, 19, lbl, kind=kind) + 4
s.rect(x, 19, 78, 22, "#ffffff", "#999999", 3); s.text(x + 5, 34, "saved report ▾", 9, MUTED); x += 82
x = s.btn(x, 19, "Go!") + 4
x = s.btn(x, 19, "↻", 26) + 4
s.btn(x, 19, "Save", 42, "green")
# Material line
s.marker(22, 66, "2")
s.text(56, 70, "Material:", 11, MUTED)
s.text(112, 70, "PES POY 280/167f72 dtex", 11, INK, True)
x = s.btn(270, 56, "ER", 30, "white") + 8
s.text(x, 70, "Machine: RPR 3SDS · Jets …", 10, MUTED)
s.btn(792, 56, "label", 38, "white"); s.btn(836, 56, "+", 30, "white")
# Tabs
s.marker(22, 102, "3")
x = 56
for t in ["Machine Data", "R&D Machine Data", "Titer", "Statimat M", "Itemat Lab", "YarnScope", "Athena", "Notes"]:
    w = int(len(t) * 6.6) + 18
    s.rect(x, 92, w, 22, "#ffffff" if t == "Machine Data" else "#e9e9e9", LINE, 3)
    s.text(x + w / 2, 107, t, 10, INK, t == "Machine Data", "middle")
    x += w + 2
s.text(x + 6, 107, "{{lab_hint}}", 9, MUTED, italic=True)
# Pivot table
tx, ty = 56, 122
s.rect(tx, ty, 866, 250, "#ffffff", LINE, 3)
cols_x = [tx + 200 + i * 110 for i in range(6)]
rows = [("Trial", ["V1", "V2", "V3", "V4", "V5", "V6"], "#e9f6e9", True),
        ("Ply", ["1", "1", "1", "1", "1", "1"], "#f2f9f2", False),
        ("Speed [m/min]", ["600", "600", "700", "700", "800", "800"], "#ffffff", False),
        ("Overfeed [%]", ["2.0", "3.0", "2.0", "3.0", "2.0", "3.0"], "#ffffff", False),
        ("Air pressure [bar]", ["6", "6", "6", "6", "6", "6"], "#ffffff", False),
        ("Jet", ["S+ 1.2", "S+ 1.2", "S+ 1.2", "S+ 1.2", "S+ 1.2", "S+ 1.2"], "#ffffff", False),
        ("Tension T1 [cN]", ["12.1", "11.8", "", "", "", ""], "#ffffff", False)]
for i, (title, vals, bg, bold) in enumerate(rows):
    y = ty + 6 + i * 30
    s.rect(tx + 4, y, 858, 26, bg, None, 0)
    s.text(tx + 12, y + 17, title, 11, INK, True)
    for cx, v in zip(cols_x, vals):
        s.text(cx + 30, y + 17, v, 11, INK, bold, "middle")
s.line(tx + 190, ty + 4, tx + 190, ty + 246, LINE, 1)
s.rect(cols_x[2] + 2, ty + 6 + 6 * 30, 56, 26, "#fffbe6", "#e6c802", 0)
s.text(cols_x[2] + 30, ty + 6 + 6 * 30 + 17, "12.4|", 11, INK, False, "middle")
s.marker(tx + 150, ty + 19, "4", "#2b2b2b")
s.marker(tx + 150, ty + 49, "5", "#2b2b2b")
s.marker(tx + 170, ty + 108, "6", "#2b2b2b")
s.marker(cols_x[2] + 66, ty + 6 + 6 * 30 + 12, "7", "#2b2b2b")
s.text(tx + 12, ty + 236, "{{keys_hint}}", 10, MUTED, italic=True)
# Legend line
s.save("help_show_experiment.svg")

# ═════════════════════════════ Report / Smart Chart ═════════════════════════════
s = Svg(940, 424, "Report / Smart Chart help sketch")
s.rect(40, 6, 890, 412, "#f4f4f4", LINE, 8)
s.marker(22, 30, "1")
x = 56
s.text(x, 34, "Charts:", 10, INK); s.rect(x + 42, 21, 30, 20, "#ffffff", "#999999", 3); s.text(x + 57, 35, "9", 10, INK, anchor="middle")
x += 80
for lbl in ["± SD", "↕ Min/Max", "Legend"]:
    x = s.btn(x, 20, lbl) + 4
x += 6
s.rect(x, 20, 70, 22, "#e8f5e9", GREEN, 11); s.text(x + 35, 35, "● series 1", 9, INK, anchor="middle"); x += 74
for lbl in ["Series", "+ Compare", "+ Image"]:
    x = s.btn(x, 20, lbl) + 4
x += 6
for lbl in ["Note", "Templates", "Save", "Open", "PDF"]:
    x = s.btn(x, 20, lbl) + 4
# Builder (Smart Chart only)
s.marker(22, 70, "2")
s.rect(56, 54, 210, 360, "#ffffff", LINE, 4)
s.text(66, 72, "Visual SQL Builder", 11, INK, True)
s.btn(66, 80, "Trial Data", 92, "green"); s.btn(162, 80, "Free Query", 94)
s.text(66, 122, "Group by (Legend)", 10, MUTED)
s.rect(66, 128, 190, 20, "#ffffff", "#999999", 3); s.text(72, 142, "Jet ▾", 10, INK)
s.btn(66, 156, "Simple", 60, "white"); s.btn(128, 156, "Advanced", 70)
s.btn(66, 184, "+ Add Filter", 90)
s.text(66, 222, "Trial Series", 10, MUTED)
s.rect(66, 228, 190, 92, "#ffffff", "#999999", 3)
for i, t in enumerate(["2026-73-035 X60.112", "2026-73-034 DTY trials", "2026-73-033 Jet S+"]):
    s.text(72, 244 + i * 18, t, 9, INK)
s.text(66, 334, "Hold Ctrl to select multiple", 9, MUTED, italic=True)
s.btn(66, 346, "▶ Run Query", 140, "green"); s.btn(210, 346, "Templ.", 46)
s.text(66, 400, "{{smart_only}}", 10, GREEN, True)
# Drill bar
s.marker(282, 64, "5")
s.rect(296, 54, 626, 20, "#eef5ff", "#c7dbf5", 3)
s.text(304, 68, "DRILL   Overfeed: 3.0 %  ›  Jet S+ 1.2", 10, "#2a5d9f")
# Chart cards
s.marker(282, 96, "3")
for i in range(2):
    cx = 296 + i * 316
    s.rect(cx, 84, 306, 220, "#ffffff", LINE, 4)
    s.text(cx + 8, 101, "::", 11, MUTED, True)
    s.rect(cx + 22, 89, 130, 18, "#ffffff", "#999999", 3); s.text(cx + 28, 102, ["Tension T1 [cN] ▾", "Elongation [%] ▾"][i], 9, INK)
    s.text(cx + 158, 102, "+", 11, GREEN, True)
    s.text(cx + 296, 102, "[ ]  ▲ ▼  x", 10, MUTED, anchor="end")
    s.rect(cx + 22, 112, 130, 18, "#ffffff", "#999999", 3); s.text(cx + 28, 125, "X: Overfeed [%] ▾", 9, INK)
    s.text(cx + 158, 125, "to all", 9, MUTED)
    # bars
    for j, hgt in enumerate([60, 82, 70, 95, 50]):
        bx = cx + 30 + j * 52
        s.rect(bx, 280 - hgt, 34, hgt, ["#4e79a7", "#f28e2b"][i], None, 2)
        s.line(bx + 17, 280 - hgt - 10, bx + 17, 280 - hgt + 10, INK, 1)
    s.line(cx + 22, 280, cx + 296, 280, LINE, 1)
    s.text(cx + 22, 296, "note · gridlines e.g. 5, 10, 15", 9, MUTED, italic=True)
s.marker(330, 180, "4", "#2b2b2b")
s.text(296, 330, "{{drill_hint}}", 10, MUTED)
s.save("help_report.svg")
