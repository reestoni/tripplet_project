"""jet_roi.py - Jet ROI Calculator (amortisation of Heberlein jets), the computing part without Qt
(2026-11-13, moved out of ui/screen_nozzle_calculator.py for the web version; the desktop screen uses it).

Formula: Q [Nm³/h] = k * C * P_abs,  P_abs = bar_g + 1
         k = DB value tblJets.Luftverbrauch when the jet comes from the DB and the value is > 0,
             else the approximation k = _CD * D²;  _CD = 0.562 / 1.1² ≈ 0.4645
PSI → bar: bar = psi / 14.5038
Single mode: competitor jet vs. Heberlein jet. Multi mode: several comparisons Jet A vs Jet B.
PDF reports: generate_pdf / generate_multi_pdf (reportlab; path or binary file object).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

PSI_PER_BAR = 14.5038

# Flow factor derived from Heberlein reference measurement:
# D_ref=1.1mm → Q_ref=0.562 Nm³/h at P_abs=1 bar_a (0 bar gauge = ambient)
# Formula: Q = _CD * C * D[mm]² * P_abs[bar_a]
# _CD = Q_ref / (D_ref² * P_abs_ref) = 0.562 / (1.1² * 1.0) = 0.46446...
_CD = 0.562 / (1.1 ** 2 * 1.0)   # ≈ 0.4645

CURRENCIES: List[Tuple[str, str]] = [
    ("CHF", "CHF"),
    ("EUR", "€"),
    ("USD", "$"),
    ("CNY", "¥"),
    ("GBP", "£"),
]
# Default cost/Nm³ per currency (rough equivalents)
DEFAULT_COST: Dict[str, str] = {
    "CHF": "0.04",
    "EUR": "0.04",
    "USD": "0.04",
    "CNY": "0.30",
    "GBP": "0.03",
}
DEFAULT_NOZZLE_PRICE: Dict[str, str] = {
    "CHF": "100",
    "EUR": "95",
    "USD": "105",
    "CNY": "720",
    "GBP": "82",
}

# Process -> jet filter (Hersteller, Prozess, JetTypeID). DTY: Prozess <= 2, ATY / Spinning: exact.
PROCESS_FILTER = {
    "DTY":      {"Hersteller": 1, "Prozess_max": 2, "JetTypeID": 1},
    "ATY":      {"Hersteller": 1, "Prozess": 3,     "JetTypeID": 1},
    "Spinning": {"Hersteller": 1, "Prozess": 4,     "JetTypeID": 1},
}
PROCESSES = ("DTY", "ATY", "Spinning")
INF = float("inf")


def _bar_g_from_input(value: float, unit: str) -> float:
    """Convert gauge pressure input to bar_g."""
    if unit == "PSI":
        return value / PSI_PER_BAR
    return value  # already bar


def _flow_coeff_per_hole(diameter_mm: float, luftverbrauch: Optional[float] = None) -> float:
    """Nm³/h Luftverbrauch pro Bohrung bei P_abs=1 bar_a.

    Nimmt den echten DB-Wert (tblJets.Luftverbrauch), falls vorhanden und > 0
    (deckt gemessene Abweichungen von der reinen D²-Näherung ab, v.a. bei
    grossen Bohrungen). Fehlt der Wert (NULL/0) oder ist die Düse gar nicht
    in der DB (z.B. Wettbewerber-Düse), wird wie bisher über _CD * D² genähert.
    """
    try:
        lv = float(luftverbrauch) if luftverbrauch is not None else 0.0
    except (TypeError, ValueError):
        lv = 0.0
    if lv > 0:
        return lv
    return _CD * (diameter_mm ** 2)


def _air_flow_nm3h(diameter_mm: float, num_holes: int, pressure_bar_g: float,
                    luftverbrauch: Optional[float] = None) -> float:
    p_abs = max(pressure_bar_g, 0.0) + 1.0
    coeff = _flow_coeff_per_hole(diameter_mm, luftverbrauch)
    return coeff * num_holes * p_abs


# public names
bar_g_from_input = _bar_g_from_input
flow_coeff_per_hole = _flow_coeff_per_hole
air_flow_nm3h = _air_flow_nm3h


def jet_matches_process(row: Dict[str, Any], process: str) -> bool:
    f = PROCESS_FILTER.get(process)
    if f is None:
        return True
    try:
        if int(row.get("Hersteller") or 0) != f["Hersteller"]:
            return False
        if int(row.get("JetTypeID") or 0) != f["JetTypeID"]:
            return False
        p = int(row.get("Prozess") or 0)
    except (ValueError, TypeError):
        return False
    return p <= f["Prozess_max"] if "Prozess_max" in f else p == f["Prozess"]


def jet_diameter(row: Dict[str, Any]) -> Optional[float]:
    try:
        return float(str(row.get("Luftbohrung") or "").replace(",", "."))
    except (TypeError, ValueError):
        return None


def jet_options(rows: List[Dict[str, Any]], process: Optional[str] = None) -> List[Dict[str, Any]]:
    """Jets for the dropdowns: [{"id", "name", "diam", "holes", "lv"}] (process None = all)."""
    out = []
    for r in rows:
        if process and not jet_matches_process(r, process):
            continue
        try:
            holes = int(r.get("LuftlochAnzahl") or 1)
        except (TypeError, ValueError):
            holes = 1
        lv = r.get("Luftverbrauch")
        try:
            lv = float(lv) if lv is not None else None
        except (TypeError, ValueError):
            lv = None
        out.append({"id": r.get("ID"), "name": str(r.get("Jet") or f"ID {r.get('ID')}"), "diam": jet_diameter(r),
                    "holes": holes, "lv": lv})
    return out


def _f(v: Any) -> float:
    return float(str(v).replace(",", "."))


def validate_single(inp: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """(code, English message) of the first wrong input, or None. inp: positions, hours, cost_m3, nozzle_px,
    comp_pressure (bar), comp_type, comp_diam, comp_holes, heb_pressure (bar), heb_mode "product"|"manual",
    heb_jet (dict with _diam/Luftverbrauch or None), heb_holes, heb_type, heb_diam."""
    def ok(fn) -> bool:
        try:
            return bool(fn())
        except Exception:
            return False
    if not ok(lambda: int(inp["positions"]) > 0):
        return "positions", "Positions: positive integer required."
    if not ok(lambda: 0 < _f(inp["hours"]) <= 9000):
        return "hours", "Hours/year: must be 1–9000."
    if not ok(lambda: _f(inp["cost_m3"]) is not None):
        return "cost", "Air cost/Nm³: invalid number."
    if not ok(lambda: _f(inp["nozzle_px"]) is not None):
        return "price", "Jet price: invalid number."
    if not ok(lambda: 0 < float(inp["comp_pressure"]) <= 50):
        return "comp_pressure", "Competitor pressure: must be > 0."
    if not str(inp.get("comp_type") or "").strip():
        return "comp_type", "Competitor: jet type required."
    if not ok(lambda: 0 < _f(inp["comp_diam"]) <= 10):
        return "comp_diam", "Competitor: bore diameter must be 0–10 mm."
    if not ok(lambda: int(inp["comp_holes"]) > 0):
        return "comp_holes", "Competitor: number of air holes must be >= 1."
    if not ok(lambda: 0 < float(inp["heb_pressure"]) <= 50):
        return "heb_pressure", "Heberlein pressure: must be > 0."
    if inp.get("heb_mode", "product") == "product":
        if not inp.get("heb_jet"):
            return "heb_jet", "Heberlein: please select a jet from the DB."
    else:
        if not str(inp.get("heb_type") or "").strip():
            return "heb_type", "Heberlein: jet type required."
        if not ok(lambda: 0 < _f(inp["heb_diam"]) <= 10):
            return "heb_diam", "Heberlein: bore diameter must be 0–10 mm."
    if not ok(lambda: int(inp["heb_holes"]) > 0):
        return "heb_holes", "Heberlein: number of air holes must be >= 1."
    return None


def calculate_single(inp: Dict[str, Any]) -> Dict[str, Any]:
    """Competitor vs Heberlein (inputs as validate_single, pressures in bar_g; comp_p_unit / heb_p_unit
    "bar"|"PSI" only for the texts). Returns everything the screen and the PDF show."""
    n_pos = int(inp["positions"])
    h_yr = _f(inp["hours"])
    cost_m3 = _f(inp["cost_m3"])
    nozzle_px = _f(inp["nozzle_px"])
    comp_pressure = float(inp["comp_pressure"])
    heb_pressure = float(inp["heb_pressure"])
    comp_diam = _f(inp["comp_diam"])
    comp_holes = int(inp["comp_holes"])
    if inp.get("heb_mode", "product") == "product":
        jet = inp["heb_jet"]
        heb_diam = float(jet.get("_diam") or 0.0)
        heb_lv = jet.get("Luftverbrauch")
        heb_type = str(inp.get("heb_type") or jet.get("Jet") or "")
    else:
        heb_diam = _f(inp["heb_diam"])
        heb_lv = None          # manual input: no DB jet -> approximation
        heb_type = str(inp.get("heb_type") or "").strip()
    heb_holes = int(inp["heb_holes"])

    comp_qh = _air_flow_nm3h(comp_diam, comp_holes, comp_pressure)
    heb_qh = _air_flow_nm3h(heb_diam, heb_holes, heb_pressure, heb_lv)
    comp_qday, heb_qday = comp_qh * 24, heb_qh * 24
    comp_qyr, heb_qyr = comp_qh * h_yr, heb_qh * h_yr
    comp_cost_day, heb_cost_day = comp_qday * cost_m3, heb_qday * cost_m3
    comp_cost_yr, heb_cost_yr = comp_qyr * cost_m3, heb_qyr * cost_m3
    saving_day = (comp_cost_day - heb_cost_day) * n_pos
    saving_yr = (comp_cost_yr - heb_cost_yr) * n_pos
    total_nozzle = nozzle_px * n_pos
    amort = total_nozzle / saving_yr if saving_yr > 0 else INF
    saving_qyr = (comp_qyr - heb_qyr) * n_pos
    saving_pct = (comp_qyr - heb_qyr) / comp_qyr * 100 if comp_qyr > 0 else 0.0
    # break-even: at what Heberlein pressure is the flow equal to the competitor's?
    heb_cd2 = heb_holes * _flow_coeff_per_hole(heb_diam, heb_lv)
    comp_cd2 = comp_holes * _flow_coeff_per_hole(comp_diam, None)
    be_bar = (comp_cd2 * (comp_pressure + 1.0) / heb_cd2 - 1.0) if heb_cd2 > 0 else INF
    heb_unit = inp.get("heb_p_unit") or "bar"
    be_str = "N/A" if be_bar == INF else (f"{be_bar * PSI_PER_BAR:.1f} PSI" if heb_unit == "PSI" else f"{be_bar:.2f} bar")
    saving_qh_one = comp_qh - heb_qh
    return {
        "process": inp.get("process") or "", "n_pos": n_pos, "h_yr": h_yr, "cost_m3": cost_m3, "nozzle_px": nozzle_px,
        "sym": inp.get("sym") or "CHF", "comp_type": str(inp.get("comp_type") or "").strip(), "comp_diam": comp_diam,
        "comp_holes": comp_holes, "comp_pressure": comp_pressure, "comp_p_unit": inp.get("comp_p_unit") or "bar",
        "heb_type": heb_type, "heb_diam": heb_diam, "heb_holes": heb_holes, "heb_pressure": heb_pressure,
        "heb_p_unit": heb_unit, "heb_mode": inp.get("heb_mode", "product"),
        "saving_day": saving_day, "saving_yr": saving_yr, "total_nozzle": total_nozzle, "amort": amort,
        "comp_qh": comp_qh, "heb_qh": heb_qh, "comp_qday": comp_qday * n_pos, "heb_qday": heb_qday * n_pos,
        "comp_qyr": comp_qyr * n_pos, "heb_qyr": heb_qyr * n_pos, "saving_qyr": saving_qyr, "saving_pct": saving_pct,
        "be_bar": be_bar, "be_str": be_str, "comp_cost_yr": comp_cost_yr, "heb_cost_yr": heb_cost_yr,
        # prose summary
        "saving_qh_one": saving_qh_one, "saving_qh_all": saving_qh_one * n_pos,
        "saving_qday_all": saving_qh_one * n_pos * 24, "saving_qyr_all": saving_qh_one * n_pos * h_yr,
    }


def single_chart(comp_cost_yr: float, heb_cost_yr: float, nozzle_price: float, n_pos: int, years: int = 5) -> Dict[str, Any]:
    """Cumulative air cost (all positions): competitor vs Heberlein incl. the jets, break-even year or None."""
    ys = list(range(0, years + 1))
    total_nozzle = nozzle_price * n_pos
    saving_yr = (comp_cost_yr - heb_cost_yr) * n_pos
    be = total_nozzle / saving_yr if saving_yr > 0 else None
    return {"years": ys, "comp": [comp_cost_yr * y * n_pos for y in ys],
            "heb": [heb_cost_yr * y * n_pos + total_nozzle for y in ys],
            "breakeven": be if be is not None and be <= years else None}


def calculate_multi(rows: List[Dict[str, Any]], cost_m3: float, sym: str) -> Optional[Dict[str, Any]]:
    """Several comparisons Jet A vs Jet B. rows: [{"label", "pos", "hours", "a_jet", "b_jet" (jet rows),
    "a_price", "b_price", "a_pressure", "b_pressure" (bar_g)}]. None = no complete row."""
    def diam(jet):
        return float(str(jet.get("Luftbohrung") or jet.get("_diam") or "0").replace(",", "."))

    def holes(jet):
        return int(jet.get("LuftlochAnzahl") or 1)

    results = []
    for row in rows:
        label = str(row.get("label") or "").strip() or f"#{len(results) + 1}"
        try:
            n_pos = max(1, int(row.get("pos") or "1"))
            h_yr = _f(row.get("hours") or "0")
        except Exception:
            continue
        a_jet, b_jet = row.get("a_jet"), row.get("b_jet")
        if not a_jet or not b_jet:
            continue
        try:
            a_diam, a_holes = diam(a_jet), holes(a_jet)
            b_diam, b_holes = diam(b_jet), holes(b_jet)
            a_price = _f(row.get("a_price") or "0")
            b_price = _f(row.get("b_price") or "0")
        except Exception:
            continue
        a_qh = _air_flow_nm3h(a_diam, a_holes, float(row.get("a_pressure") or 0), a_jet.get("Luftverbrauch"))
        b_qh = _air_flow_nm3h(b_diam, b_holes, float(row.get("b_pressure") or 0), b_jet.get("Luftverbrauch"))
        if a_diam <= 0:
            continue
        a_air_yr = a_qh * h_yr * cost_m3 * n_pos
        b_air_yr = b_qh * h_yr * cost_m3 * n_pos
        net_invest = (b_price - a_price) * n_pos          # switching cost
        results.append({"label": label, "a_name": str(a_jet.get("Jet") or "?"), "b_name": str(b_jet.get("Jet") or "?"),
                        "n_pos": n_pos, "h_yr": h_yr, "saving_yr": a_air_yr - b_air_yr, "net_invest": net_invest,
                        "air_pct": (a_qh - b_qh) / a_qh * 100 if a_qh > 0 else 0.0, "sym": sym,
                        "a_air_yr": a_air_yr, "b_air_yr": b_air_yr, "a_qh": a_qh, "b_qh": b_qh})
    if not results:
        return None
    total_saving = sum(r["saving_yr"] for r in results)
    total_invest = sum(r["net_invest"] for r in results)
    total_amort = total_invest / total_saving if total_saving > 0 and total_invest > 0 else INF
    total_a = sum(r["a_air_yr"] for r in results)
    total_b = sum(r["b_air_yr"] for r in results)
    total_h = sum(r["h_yr"] for r in results)
    for r in results:
        r["amort"] = None if r["net_invest"] <= 0 else (INF if r["saving_yr"] <= 0 else r["net_invest"] / r["saving_yr"])
    return {"results": results,
            "totals": {"sym": sym, "saving": total_saving, "invest": total_invest, "cost_m3": cost_m3,
                       "air_pct": (total_a - total_b) / total_a * 100 if total_a > 0 else 0.0, "amort": total_amort,
                       "a_air_yr": total_a, "b_air_yr": total_b, "hours": total_h,
                       "wa_qh": sum(r["a_qh"] * r["h_yr"] for r in results) / total_h if total_h > 0 else 0.0,
                       "wb_qh": sum(r["b_qh"] * r["h_yr"] for r in results) / total_h if total_h > 0 else 0.0}}


def multi_chart(total_saving: float, total_invest: float, years: int = 5) -> Dict[str, Any]:
    """Jet A: savings foregone t × saving; Jet B: remaining investment max(0, invest − t × saving)."""
    ys = list(range(years + 1))
    be = total_invest / total_saving if total_saving > 0 and total_invest > 0 else None
    return {"years": ys, "a": [total_saving * y for y in ys], "b": [max(0.0, total_invest - total_saving * y) for y in ys],
            "breakeven": be if be is not None and 0 < be < years else None}


# ---------------------------------------------------------------------------
# PDF Report generator
# ---------------------------------------------------------------------------

def generate_pdf(path: str, d: Dict, chart_widget=None):
    """Generate a 2-page A4 PDF report matching the Heberlein calculator style."""
    import datetime
    import tempfile
    import os

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm, mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable, Image as RLImage,
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

    # ── Colours ───────────────────────────────────────────────────────
    HEB_GREEN  = colors.HexColor("#39A650")
    HEB_DARK   = colors.HexColor("#1D3557")
    ROW_LIGHT  = colors.HexColor("#F2F9F3")
    ROW_HEAD   = colors.HexColor("#39A650")
    GREY_TEXT  = colors.HexColor("#555555")
    BLACK      = colors.black
    WHITE      = colors.white

    PW, PH = A4
    margin = 1.8 * cm

    # ── Styles ────────────────────────────────────────────────────────
    def _s(name, **kw):
        return ParagraphStyle(name, **kw)

    s_title   = _s("title",   fontSize=13, fontName="Helvetica-Bold",
                   textColor=HEB_DARK, spaceAfter=2, spaceBefore=6)
    s_h1      = _s("h1",      fontSize=13, fontName="Helvetica-Bold",
                   textColor=HEB_DARK, spaceBefore=10, spaceAfter=4)
    s_normal  = _s("normal",  fontSize=9,  fontName="Helvetica",
                   textColor=GREY_TEXT, leading=14)
    s_small   = _s("small",   fontSize=8,  fontName="Helvetica",
                   textColor=GREY_TEXT)
    s_footer  = _s("footer",  fontSize=7.5, fontName="Helvetica",
                   textColor=GREY_TEXT)
    s_green   = _s("green",   fontSize=11, fontName="Helvetica-Bold",
                   textColor=HEB_GREEN)
    s_prose   = _s("prose",   fontSize=9,  fontName="Helvetica",
                   textColor=GREY_TEXT, leading=14, spaceAfter=4)

    sym  = d["sym"]
    date = datetime.date.today().strftime("%d.%m.%Y")

    def _pstr(bar_val, unit):
        if unit == "PSI":
            return f"{bar_val * PSI_PER_BAR:.1f} PSI"
        return f"{bar_val:.2f} bar"

    comp_p_str = _pstr(d["comp_pressure"], d["comp_p_unit"])
    heb_p_str  = _pstr(d["heb_pressure"],  d["heb_p_unit"])
    amort_str  = "N/A" if d["amort"] == float("inf") else f"{d['amort']:.2f} years"

    # ── Table helper ──────────────────────────────────────────────────
    col_w = [PW - 2 * margin - 5 * cm, 5 * cm]

    def _section_table(section_label, rows, has_subheader=False):
        """Build a styled 2-column table with green section header."""
        data = [[Paragraph(f"<b>{section_label}</b>",
                           _s("th", fontSize=9, fontName="Helvetica-Bold",
                              textColor=WHITE)), ""]]
        for label, value in rows:
            data.append([
                Paragraph(label, s_normal),
                Paragraph(str(value), s_normal),
            ])
        ts = TableStyle([
            # Section header row
            ("BACKGROUND",   (0, 0), (-1, 0), HEB_GREEN),
            ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
            ("SPAN",         (0, 0), (-1, 0)),
            ("TOPPADDING",   (0, 0), (-1, 0), 5),
            ("BOTTOMPADDING",(0, 0), (-1, 0), 5),
            ("LEFTPADDING",  (0, 0), (-1, 0), 8),
            # Data rows
            ("FONTSIZE",     (0, 1), (-1, -1), 9),
            ("TOPPADDING",   (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 1), (-1, -1), 4),
            ("LEFTPADDING",  (0, 1), (-1, -1), 8),
            ("RIGHTPADDING", (0, 1), (-1, -1), 8),
            ("LINEBELOW",    (0, 1), (-1, -2), 0.4, colors.HexColor("#E0E0E0")),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, ROW_LIGHT]),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ])
        t = Table(data, colWidths=col_w)
        t.setStyle(ts)
        return t

    # ── Header logo helper ────────────────────────────────────────────
    def _logo_row():
        """Returns header logo table (left: heb_logo, right: header_logo)."""
        from ui.pathutil import resource_path
        logo_l = resource_path("assets/images/heb_logo.png")
        logo_r = resource_path("assets/images/header_logo_big.png")
        cells = []
        if logo_l and os.path.exists(logo_l):
            cells.append(RLImage(logo_l, width=6.5*cm, height=2.0*cm,
                                 kind="proportional"))
        else:
            cells.append(Paragraph("HEBERLEIN", _s("lg", fontSize=14,
                                   fontName="Helvetica-Bold", textColor=HEB_GREEN)))
        if logo_r and os.path.exists(logo_r):
            cells.append(RLImage(logo_r, width=2.0*cm, height=1.4*cm,
                                 kind="proportional"))
        else:
            cells.append("")
        logo_w = PW - 2 * margin
        t = Table([cells], colWidths=[logo_w * 0.6, logo_w * 0.4])
        t.setStyle(TableStyle([
            ("ALIGN",  (1, 0), (1, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return t

    # ── Chart: draw natively in reportlab (vector, crisp at any size) ─
    def _build_rl_chart(comp_data, heb_data, years, currency_sym, width, height):
        """Returns a reportlab Drawing of the cumulative cost chart."""
        from reportlab.graphics.shapes import (
            Drawing, Line, String, Rect, Polygon, PolyLine, Group,
        )
        from reportlab.graphics import renderPDF
        from reportlab.lib.colors import HexColor, Color

        GREEN   = HexColor("#39A650")
        GREY    = HexColor("#aaaaaa")
        GRID_C  = HexColor("#ebebeb")
        AXIS_C  = HexColor("#bbbbbb")
        TEXT_C  = HexColor("#777777")
        FILL_C  = Color(0.224, 0.647, 0.314, alpha=0.12)

        d = Drawing(width, height)

        # Margins inside drawing
        ml, mr, mt, mb = 58, 14, 12, 36  # extra bottom margin for legend row
        cw = width  - ml - mr
        ch = height - mt - mb

        all_v = comp_data + heb_data
        mx = max(all_v) if all_v and max(all_v) > 0 else 1
        n  = len(years)

        def tx(i):   return ml + i / (n - 1) * cw
        def ty(v):   return mb + v / mx * ch   # RL: y=0 at bottom

        # Grid lines
        for i in range(5):
            yy = mb + i * ch / 4
            d.add(Line(ml, yy, width - mr, yy,
                       strokeColor=GRID_C, strokeWidth=0.5))

        # Savings fill polygon (comp > heb region)
        fill_pts = []
        visible = [i for i in range(n) if comp_data[i] >= heb_data[i]]
        if visible:
            for i in visible:
                fill_pts.append(tx(i)); fill_pts.append(ty(comp_data[i]))
            for i in reversed(visible):
                fill_pts.append(tx(i)); fill_pts.append(ty(heb_data[i]))
            d.add(Polygon(fill_pts,
                          fillColor=FILL_C, strokeColor=None))

        # Axes
        d.add(Line(ml, mb, ml, mb + ch, strokeColor=AXIS_C, strokeWidth=0.8))
        d.add(Line(ml, mb, width - mr, mb, strokeColor=AXIS_C, strokeWidth=0.8))

        # X labels (years)
        for i, yr in enumerate(years):
            x = tx(i)
            d.add(String(x, mb - 10, str(yr),
                         fontSize=7, fillColor=TEXT_C,
                         textAnchor="middle"))
        # X axis label
        d.add(String(ml + cw / 2, mb - 18, "Year",
                     fontSize=7, fillColor=TEXT_C, textAnchor="middle"))

        # Y labels
        for i in range(5):
            yy = mb + i * ch / 4
            val = i * mx / 4
            s = f"{val/1000:.0f}k" if val >= 10000 else f"{val:,.0f}"
            d.add(String(ml - 4, yy - 3, s,
                         fontSize=6.5, fillColor=TEXT_C,
                         textAnchor="end"))

        # Break-even line
        if len(comp_data) == len(heb_data) == n:
            for i in range(n - 1):
                c0, c1 = comp_data[i], comp_data[i + 1]
                h0, h1 = heb_data[i],  heb_data[i + 1]
                if (c0 - h0) * (c1 - h1) <= 0 and (c0 != h0 or c1 != h1):
                    diff0 = c0 - h0
                    diff1 = c1 - h1
                    if diff1 != diff0:
                        t = diff0 / (diff0 - diff1)
                        bx = tx(i) + t * (tx(i + 1) - tx(i))
                        d.add(Line(bx, mb, bx, mb + ch,
                                   strokeColor=HexColor("#e53935"),
                                   strokeWidth=1,
                                   strokeDashArray=[3, 3]))
                        be_yr = years[i] + t
                        label = f"Break-even: {be_yr:.1f} yr"
                        # Label: place to right of line at mid-height, or left if near right edge
                        label_x = bx + 3 if bx < width * 0.7 else bx - 3
                        anchor = "start" if bx < width * 0.7 else "end"
                        label_y = mb + ch * 0.45   # mid-height — clear of both legend corners
                        d.add(String(label_x, label_y, label,
                                     fontSize=6.5,
                                     fillColor=HexColor("#e53935"),
                                     fontName="Helvetica-Bold",
                                     textAnchor=anchor))
                    break

        # Draw polylines
        def _line(data, color, dash=False):
            pts = []
            for i, v in enumerate(data):
                pts.append(tx(i)); pts.append(ty(v))
            kw = dict(strokeColor=color, strokeWidth=1.5, fillColor=None)
            if dash:
                kw["strokeDashArray"] = [4, 2]
            d.add(PolyLine(pts, **kw))
            # Dots
            for i, v in enumerate(data):
                d.add(Line(tx(i) - 2.5, ty(v), tx(i) + 2.5, ty(v),
                           strokeWidth=0))  # invisible anchor
                from reportlab.graphics.shapes import Circle
                d.add(Circle(tx(i), ty(v), 2.5,
                             fillColor=color, strokeColor=None))

        _line(comp_data, GREY)
        _line(heb_data,  GREEN)

        # Legend — outside chart area, below X-axis labels (always collision-free)
        leg_y = 4   # below X-axis label row
        cx = ml + cw / 2   # center of chart
        # Competitor left of center, Heberlein right
        d.add(Line(cx - 75, leg_y, cx - 63, leg_y,
                   strokeColor=GREY, strokeWidth=1.5))
        d.add(String(cx - 60, leg_y - 3, "Competitor",
                     fontSize=6.5, fillColor=TEXT_C))
        d.add(Line(cx + 5, leg_y, cx + 17, leg_y,
                   strokeColor=GREEN, strokeWidth=1.5))
        d.add(String(cx + 20, leg_y - 3, "Heberlein",
                     fontSize=6.5, fillColor=TEXT_C))

        # Currency label top-right, inside chart but above plot area
        d.add(String(width - mr, mb + ch + 2, f"({currency_sym})",
                     fontSize=6, fillColor=TEXT_C,
                     textAnchor="end"))

        return d

    # ── Build story ───────────────────────────────────────────────────
    story = []

    # ── PAGE 1: Logo + inputs ─────────────────────────────────────────
    story.append(_logo_row())
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=HEB_GREEN))
    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph("Calculator", s_title))
    story.append(Spacer(1, 0.15 * cm))

    story.append(_section_table("General", [
        ("Process",                d["process"]),
        ("Number of positions",    str(d["n_pos"])),
        ("Operating hours / year", f"{d['h_yr']:,.0f}"),
        ("Air cost / Nm³",    f"{d['cost_m3']} {sym}"),
        ("Heberlein jet price",    f"{d['nozzle_px']} {sym}"),
    ]))
    story.append(Spacer(1, 0.25 * cm))

    story.append(_section_table("Competitor Jet", [
        ("Jet type",             d["comp_type"] or "—"),
        ("Air hole diameter",    f"{d['comp_diam']} mm"),
        ("No. of air holes (C)", str(d["comp_holes"])),
        ("Air pressure",         comp_p_str),
    ]))
    story.append(Spacer(1, 0.25 * cm))

    mode_label = "DB Selection" if d["heb_mode"] == "product" else "Manual Entry"
    story.append(_section_table(f"Heberlein Jet — {mode_label}", [
        ("Jet type",             d["heb_type"] or "—"),
        ("Air hole diameter",    f"{d['heb_diam']:.4f} mm"),
        ("No. of air holes (C)", str(d["heb_holes"])),
        ("Air pressure",         heb_p_str),
    ]))
    story.append(Spacer(1, 0.25 * cm))

    story.append(_section_table("Result", [
        ("Savings per day",          f"{d['saving_day']:,.2f} {sym}"),
        ("Savings per year",         f"{d['saving_yr']:,.2f} {sym}"),
        ("Total jet cost (all pos.)", f"{d['total_nozzle']:,.2f} {sym}"),
        ("Amortisation",             amort_str),
        ("Air saving",               f"{d['saving_pct']:.1f} %"),
    ]))

    # ── PAGE 2: Chart + Prose ─────────────────────────────────────────
    story.append(PageBreak())
    story.append(_logo_row())
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=HEB_GREEN))
    story.append(Spacer(1, 0.25 * cm))

    story.append(Paragraph("Air Consumption over Time", s_h1))
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#CCCCCC")))
    story.append(Spacer(1, 0.15 * cm))

    chart_w = PW - 2 * margin
    chart_h = chart_w * 0.36
    # Build vector chart from stored data
    try:
        years_list  = list(range(0, 6))
        n_pos       = d["n_pos"]
        nozzle_px   = d["nozzle_px"]
        comp_cost_yr = d["comp_cost_yr"]
        heb_cost_yr  = d["heb_cost_yr"]
        comp_data = [comp_cost_yr * y * n_pos for y in years_list]
        heb_data  = [heb_cost_yr  * y * n_pos + nozzle_px * n_pos
                     for y in years_list]
        rl_chart = _build_rl_chart(
            comp_data, heb_data, years_list,
            d["sym"], chart_w, chart_h
        )
        story.append(rl_chart)
    except Exception:
        story.append(Spacer(1, chart_h))

    story.append(Spacer(1, 0.45 * cm))

    story.append(Paragraph(
        "<b>Air Consumption Reduction with a Heberlein Jet</b>", s_h1
    ))
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#CCCCCC")))
    story.append(Spacer(1, 0.2 * cm))

    saving_qh_one = d["comp_qh"]  - d["heb_qh"]
    saving_qh_all = saving_qh_one * d["n_pos"]
    saving_qday   = saving_qh_all * 24
    saving_qyr    = saving_qh_all * d["h_yr"]

    def _green(val, unit="m³"):
        return Paragraph(f'<font color="#39A650"><b>{val}</b></font> {unit}', s_prose)

    half = (PW - 2 * margin - 1 * cm) / 2
    saving_table = Table([
        [Paragraph("Air saving per jet per hour:",  s_prose),
         Paragraph("Air saving all jets per hour:", s_prose)],
        [_green(f"{saving_qh_one:.2f}"),
         _green(f"{saving_qh_all:.2f}")],
        [Paragraph("Air saving all jets per day:",  s_prose),
         Paragraph("Air saving all jets per year:", s_prose)],
        [_green(f"{saving_qday:.2f}"),
         _green(f"{saving_qyr:,.2f}")],
    ], colWidths=[half, half])
    saving_table.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",   (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
    ]))
    story.append(saving_table)
    story.append(Spacer(1, 0.4 * cm))

    be = d["be_bar"]
    if be != float("inf") and be > 0:
        be_val = (f"{be * PSI_PER_BAR:.1f} PSI"
                  if d["heb_p_unit"] == "PSI" else f"{be:.2f} bar")
        story.append(Paragraph(
            f'At equal air consumption to the competitor jet, the pressure can be raised '
            f'to <font color="#39A650"><b>{be_val}</b></font> when using a Heberlein jet.',
            s_prose
        ))

    # ── Footer on every page ──────────────────────────────────────────
    def _add_footer(canvas_obj, doc_obj):
        canvas_obj.saveState()
        canvas_obj.setFont("Helvetica", 7.5)
        canvas_obj.setFillColor(GREY_TEXT)
        canvas_obj.drawString(margin, 1.2 * cm,
                              f"Calculation date: {date}")
        canvas_obj.drawRightString(PW - margin, 1.2 * cm,
                                   f"Page {doc_obj.page}")
        canvas_obj.setStrokeColor(colors.HexColor("#E0E0E0"))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(margin, 1.5 * cm, PW - margin, 1.5 * cm)
        canvas_obj.restoreState()

    # ── Build PDF ─────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=1.5 * cm, bottomMargin=2 * cm,
        title="Heberlein Jet ROI Calculator",
        author="Heberlein Technology AG",
    )
    doc.build(story, onFirstPage=_add_footer, onLaterPages=_add_footer)


def generate_multi_pdf(path: str, results: list, totals: dict):
    """Generate A4 PDF for Multi-Jet Comparison — same Heberlein style as single-jet."""
    import datetime, os

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm, mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, Image as RLImage, KeepTogether,
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.graphics.shapes import (
        Drawing, Line, String, Rect, PolyLine, Polygon,
    )
    from reportlab.lib.colors import HexColor, Color

    HEB_GREEN = colors.HexColor("#39A650")
    HEB_DARK  = colors.HexColor("#1D3557")
    ROW_LIGHT = colors.HexColor("#F2F9F3")
    GREY_TEXT = colors.HexColor("#555555")
    WHITE     = colors.white

    PW, PH = A4
    margin = 1.8 * cm

    def _s(name, **kw):
        return ParagraphStyle(name, **kw)

    s_title  = _s("t",  fontSize=13, fontName="Helvetica-Bold",
                  textColor=HEB_DARK, spaceAfter=2, spaceBefore=6)
    s_h1     = _s("h1", fontSize=13, fontName="Helvetica-Bold",
                  textColor=HEB_DARK, spaceBefore=10, spaceAfter=4)
    s_normal = _s("n",  fontSize=9,  fontName="Helvetica",
                  textColor=GREY_TEXT, leading=14)
    s_small  = _s("sm", fontSize=8,  fontName="Helvetica",
                  textColor=GREY_TEXT)
    s_footer = _s("ft", fontSize=7.5, fontName="Helvetica",
                  textColor=GREY_TEXT)

    sym  = totals.get("sym", "CHF")
    date = datetime.date.today().strftime("%d.%m.%Y")

    # ── Footer ────────────────────────────────────────────────────────
    def _add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(GREY_TEXT)
        canvas.drawString(margin, 1.3 * cm, f"Calculation date: {date}")
        canvas.drawRightString(PW - margin, 1.3 * cm, f"Page {doc.page}")
        try:
            import pathlib
            lp = pathlib.Path(__file__).resolve().parents[1] / "assets" / "images" / "heb_logo.png"
            if lp.exists():
                canvas.drawImage(str(lp), margin, PH - 2.6*cm,
                                 width=5.0*cm, height=1.4*cm,
                                 preserveAspectRatio=True, mask="auto")
            rp = pathlib.Path(__file__).resolve().parents[1] / "assets" / "images" / "header_logo_big.png"
            if rp.exists():
                canvas.drawImage(str(rp), PW - margin - 2.0*cm, PH - 2.6*cm,
                                 width=2.0*cm, height=1.4*cm,
                                 preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
        canvas.setStrokeColor(HEB_GREEN)
        canvas.setLineWidth(1.2)
        canvas.line(margin, PH - 2.8*cm, PW - margin, PH - 2.8*cm)
        canvas.restoreState()

    # ── Section table helper (identical style to single-jet) ──────────
    col_w = [PW - 2*margin - 5*cm, 5*cm]

    def _section_table(label, rows):
        data = [[Paragraph(f"<b>{label}</b>",
                           _s("th", fontSize=9, fontName="Helvetica-Bold",
                              textColor=WHITE)), ""]]
        for lbl, val in rows:
            data.append([Paragraph(lbl, s_normal),
                         Paragraph(str(val), s_normal)])
        style = TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0), HEB_GREEN),
            ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
            ("SPAN",         (0, 0), (-1, 0)),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [ROW_LIGHT, WHITE]),
            ("FONTNAME",     (0, 1), (-1,-1), "Helvetica"),
            ("FONTSIZE",     (0, 1), (-1,-1), 9),
            ("TEXTCOLOR",    (0, 1), (-1,-1), GREY_TEXT),
            ("BOTTOMPADDING",(0, 0), (-1,-1), 5),
            ("TOPPADDING",   (0, 0), (-1,-1), 5),
            ("LEFTPADDING",  (0, 0), (-1,-1), 8),
            ("RIGHTPADDING", (0, 0), (-1,-1), 8),
            ("GRID",         (0, 0), (-1,-1), 0.4, colors.HexColor("#D0D0D0")),
        ])
        return Table(data, colWidths=col_w, style=style)

    # ── Per-comparison table ──────────────────────────────────────────
    def _comparison_table(results, sym):
        headers = ["Label", "Jet A", "Jet B", "Hours / yr",
                   f"Air Saving / yr ({sym})", f"Investment ({sym})", "Break-even"]
        data = [[Paragraph(f"<b>{h}</b>",
                           _s("ch", fontSize=8, fontName="Helvetica-Bold",
                              textColor=WHITE)) for h in headers]]
        for res in results:
            be = res.get("net_invest", 0)
            sav = res.get("saving_yr", 0)
            if be <= 0:
                be_s = "—"
            elif sav <= 0:
                be_s = "∞"
            else:
                be_s = f"{be/sav:.2f} yr"
            inv_s = f"{res.get('net_invest',0):,.0f}" if res.get("net_invest",0) > 0 else "0"
            data.append([
                Paragraph(res.get("label",""), s_normal),
                Paragraph(res.get("a_name",""), s_normal),
                Paragraph(res.get("b_name",""), s_normal),
                Paragraph(f"{res.get('h_yr',0):,.0f} h", s_normal),
                Paragraph(f"{res.get('saving_yr',0):,.0f}", s_normal),
                Paragraph(inv_s, s_normal),
                Paragraph(be_s, s_normal),
            ])
        # Totals row
        total_sav = totals.get("saving", 0)
        total_inv = totals.get("invest", 0)
        total_be  = (f"{total_inv/total_sav:.2f} yr"
                     if total_sav > 0 and total_inv > 0 else "—")
        data.append([
            Paragraph("<b>Total</b>", _s("tb", fontSize=9, fontName="Helvetica-Bold",
                                         textColor=HEB_DARK)),
            Paragraph("—", s_small), Paragraph("—", s_small),
            Paragraph("—", s_small),
            Paragraph(f"<b>{total_sav:,.0f}</b>",
                      _s("tv", fontSize=9, fontName="Helvetica-Bold", textColor=HEB_GREEN)),
            Paragraph(f"<b>{total_inv:,.0f}</b>",
                      _s("ti", fontSize=9, fontName="Helvetica-Bold", textColor=HEB_DARK)),
            Paragraph(f"<b>{total_be}</b>",
                      _s("tbe", fontSize=9, fontName="Helvetica-Bold", textColor=HEB_DARK)),
        ])
        ncols = len(headers)
        col_w2 = (PW - 2*margin) / ncols
        style = TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), HEB_GREEN),
            ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
            ("ROWBACKGROUNDS",(0, 1), (-1,-2), [ROW_LIGHT, WHITE]),
            ("BACKGROUND",    (0,-1), (-1,-1), colors.HexColor("#E8F5EC")),
            ("LINEABOVE",     (0,-1), (-1,-1), 1, HEB_GREEN),
            ("FONTNAME",      (0, 1), (-1,-1), "Helvetica"),
            ("FONTSIZE",      (0, 0), (-1,-1), 8),
            ("TEXTCOLOR",     (0, 1), (-1,-2), GREY_TEXT),
            ("BOTTOMPADDING", (0, 0), (-1,-1), 5),
            ("TOPPADDING",    (0, 0), (-1,-1), 5),
            ("LEFTPADDING",   (0, 0), (-1,-1), 6),
            ("RIGHTPADDING",  (0, 0), (-1,-1), 6),
            ("GRID",          (0, 0), (-1,-1), 0.4, colors.HexColor("#D0D0D0")),
        ])
        return Table(data, colWidths=[col_w2]*ncols, style=style)

    # ── Break-even chart (same style as single-jet) ───────────────────
    def _build_be_chart(total_saving, total_invest, sym, width, height):
        d = Drawing(width, height)
        if total_saving <= 0:
            return d
        GREEN  = HexColor("#39A650")
        GREY   = HexColor("#999999")
        RED    = HexColor("#e53935")
        TEXT_C = HexColor("#555555")
        GRID_C = HexColor("#ebebeb")
        FILL_C = Color(0.224, 0.647, 0.314, alpha=0.12)

        ml, mr, mt, mb = 68, 16, 16, 36
        cw = width - ml - mr
        ch = height - mt - mb
        years = list(range(6))
        # Jet A: cumulative air cost WITH old jets (grows each year)
        a_cum = [total_saving * y for y in years]
        # Jet B: net cost = investment upfront minus cumulative savings
        #   positive = still in debt, negative = profit (cap at 0 for display)
        b_cum = [max(0.0, total_invest - total_saving * y) for y in years]
        # Y-axis: 0 at bottom, max at top
        # a_cum grows UP (saving opportunity cost), b_cum falls DOWN to 0
        max_val = max(max(a_cum), max(b_cum), 1)

        def tx(i): return ml + i / 5 * cw
        # v=0 → bottom (mb), v=max_val → top (mb+ch)
        def ty(v): return mb + v / max_val * ch

        # Grid (Y=0 at bottom = mb, Y=max at top = mb+ch)
        for i in range(5):
            yy = mb + i * ch / 4
            d.add(Line(ml, yy, width - mr, yy,
                       strokeColor=GRID_C, strokeWidth=0.5))
            val = max_val * i / 4
            s = f"{val/1000:.0f}k" if val >= 1000 else f"{val:.0f}"
            d.add(String(ml - 4, yy - 3, s,
                         fontSize=6.5, fillColor=TEXT_C, textAnchor="end"))

        # Axes
        d.add(Line(ml, mb, ml, mb + ch, strokeColor=HexColor("#bbbbbb"), strokeWidth=0.8))
        d.add(Line(ml, mb, width - mr, mb,
                   strokeColor=HexColor("#bbbbbb"), strokeWidth=0.8))

        # X labels
        for i, yr in enumerate(years):
            d.add(String(tx(i), mb - 12, str(yr),
                         fontSize=7, fillColor=TEXT_C, textAnchor="middle"))
        d.add(String(ml + cw/2, mb - 24, "Year",
                     fontSize=7, fillColor=TEXT_C, textAnchor="middle"))

        # Savings fill (green area between A and B after break-even)
        if total_invest > 0 and total_saving > 0:
            be_yr = total_invest / total_saving
            if 0 < be_yr < 5:
                be_x = ml + be_yr / 5 * cw
                from reportlab.graphics.shapes import Polygon as RLPoly
                # After break-even: A is above B → fill between them
                fill_pts = [be_x, ty(total_invest - total_saving * be_yr)]
                for i in range(int(be_yr) + 1, 6):
                    fill_pts += [tx(i), ty(a_cum[i])]
                for i in range(5, int(be_yr), -1):
                    fill_pts += [tx(i), ty(b_cum[i])]
                fill_pts += [be_x, ty(total_invest - total_saving * be_yr)]
                if len(fill_pts) >= 6:
                    d.add(RLPoly(fill_pts, fillColor=FILL_C, strokeColor=None))

        # Lines
        for i in range(5):
            d.add(Line(tx(i), ty(a_cum[i]), tx(i+1), ty(a_cum[i+1]),
                       strokeColor=GREY, strokeWidth=1.5))
            d.add(Line(tx(i), ty(b_cum[i]), tx(i+1), ty(b_cum[i+1]),
                       strokeColor=GREEN, strokeWidth=1.5))

        # Dots
        for i in range(6):
            from reportlab.graphics.shapes import Circle
            d.add(Circle(tx(i), ty(a_cum[i]), 3, fillColor=GREY, strokeColor=None))
            d.add(Circle(tx(i), ty(b_cum[i]), 3, fillColor=GREEN, strokeColor=None))

        # Break-even line
        if total_invest > 0 and total_saving > 0 and 0 < total_invest/total_saving < 5:
            be_yr = total_invest / total_saving
            be_x  = ml + be_yr / 5 * cw
            d.add(Line(be_x, mb, be_x, mb + ch,
                       strokeColor=RED, strokeWidth=1,
                       strokeDashArray=[3, 3]))
            label = f"Break-even: {be_yr:.2f} yr"
            lx = be_x + 4 if be_yr < 3.5 else be_x - 90
            d.add(String(lx, mb + ch * 0.45, label,
                         fontSize=6.5, fillColor=RED,
                         fontName="Helvetica-Bold"))

        # Legend bottom-centre (below x-axis labels)
        cx = ml + cw / 2
        ly = 6
        d.add(Line(cx - 80, ly, cx - 68, ly, strokeColor=GREY, strokeWidth=1.5))
        d.add(String(cx - 65, ly - 3, "Jet A  (status quo)",
                     fontSize=6.5, fillColor=TEXT_C))
        d.add(Line(cx + 10, ly, cx + 22, ly, strokeColor=GREEN, strokeWidth=1.5))
        d.add(String(cx + 25, ly - 3, "Jet B  (investment)",
                     fontSize=6.5, fillColor=TEXT_C))
        d.add(String(width - mr, mb + ch + 2, f"({sym})",
                     fontSize=6, fillColor=TEXT_C, textAnchor="end"))
        return d

    # ── Build story ───────────────────────────────────────────────────
    story = []

    # Header line + spacing (logos drawn by _add_footer on canvas)
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("Multi-Jet Comparison", s_title))
    story.append(Spacer(1, 0.15*cm))

    # General section
    story.append(_section_table("General", [
        ("Currency",         sym),
        ("Air cost / Nm³",   f"{totals.get('cost_m3', 0):.4f} {sym}"),
    ]))
    story.append(Spacer(1, 0.3*cm))

    # Totals section
    total_sav = totals.get("saving", 0)
    total_inv = totals.get("invest", 0)
    total_be  = (f"{total_inv/total_sav:.2f} years"
                 if total_sav > 0 and total_inv > 0 else "N/A")
    story.append(_section_table("Summary", [
        ("Total Air Saving / yr",  f"{total_sav:,.0f} {sym}"),
        ("Total Investment",       f"{total_inv:,.0f} {sym}"),
        ("Break-even",             total_be),
        ("Avg Air Saving",         f"{totals.get('air_pct', 0):.1f} %"),
    ]))
    story.append(Spacer(1, 0.3*cm))

    # Per-comparison breakdown
    story.append(Paragraph("Per-Comparison Breakdown", s_h1))
    story.append(_comparison_table(results, sym))
    story.append(Spacer(1, 0.4*cm))

    # Page 2: chart
    from reportlab.platypus import PageBreak
    story.append(PageBreak())
    story.append(Paragraph("Cumulative Cost: Jet A vs Jet B", s_h1))
    story.append(HRFlowable(width="100%", thickness=0.8, color=HEB_GREEN))
    story.append(Spacer(1, 0.3*cm))

    chart_w = PW - 2 * margin
    chart_h = chart_w * 0.36
    story.append(_build_be_chart(
        totals.get("saving", 0),
        totals.get("invest", 0),
        sym, chart_w, chart_h
    ))

    # Build
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=3.2*cm, bottomMargin=2*cm,
        title="Heberlein Multi-Jet Comparison",
        author="Heberlein Technology AG",
    )
    doc.build(story, onFirstPage=_add_footer, onLaterPages=_add_footer)
