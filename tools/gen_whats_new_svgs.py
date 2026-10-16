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
s.text(20, 28, "What's new", 10, INK, True)
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
