"""Tiny SVG drawing helper for the help / What's new sketches (plain SVG
Tiny for QSvgWidget). Used by tools/gen_help_svgs.py and
tools/gen_whats_new_svgs.py. No emojis or rare symbols - the Qt SVG renderer
shows them as boxes."""
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
                            "amber": ("#FFF4D6", "#E8C15A", "#5a4500"),
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
