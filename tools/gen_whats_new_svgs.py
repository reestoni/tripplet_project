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
