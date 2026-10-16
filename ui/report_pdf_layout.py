"""report_pdf_layout.py - ReportLab-PDF-Bausteine fuer ReportScreen.exportPdf.

Ausgelagert aus ui/screen_report.py (reiner Code-Move, keine
Verhaltensaenderung). Enthaelt die PDF-Template-Defaults sowie kleine
ReportLab-Hilfsfunktionen (Meta-Zellen, Section-Header, Infobox-Tabelle,
Notiz-Bloecke), die von _ReportBridge.exportPdf (weiterhin in
screen_report.py) verwendet werden.

reportlab/db.connection werden bewusst lazy in jeder Funktion importiert
(nicht neu implementiert), damit exakt dieselben Wrapper wie vorher
verwendet werden.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PDF-Template laden
# ---------------------------------------------------------------------------

_PDF_TEMPLATE_DEFAULTS = {
    "accentColor":       "#39A650",
    "navyColor":         "#1D3557",
    "fontFamily":        "Segoe UI, Arial, sans-serif",
    "pageMarginTop":     "18mm",
    "pageMarginSide":    "14mm",
    "pageMarginBottom":  "14mm",
    "coverAccentHeight": "5mm",
    "coverTitleSize":    "26pt",
    "coverSubtitleSize": "10pt",
    "coverKicker":       "Heberlein Technology AG",
    "coverFooter":       "Heberlein Technology AG · Wattwil, Switzerland",
    "chartHeightMm":     118,
    "chartsPerPage":     2,
    "headerFontSize":    "8pt",
    "headerLogoHeight":  "20px",
    "sectionTitleSize":  "11pt",
    "pageNumberFormat":  "Page {n} of {total}",
    "showPageNumbers":   True,
    "showHeader":        True,
    "showCoverMeta":     True,
}


# ---------------------------------------------------------------------------
# reportlab PDF helpers (used by _ReportBridge.exportPdf)
# ---------------------------------------------------------------------------

def _meta_cell(label, value, s_label, s_value):
    from reportlab.platypus import Paragraph
    def _x(s): return str(s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    return [Paragraph(_x(label), s_label), Paragraph(_x(value) if value else "—", s_value)]


def _section_hdr(title, accent_color, navy_color, style):
    from reportlab.platypus import HRFlowable, Spacer, Paragraph, KeepTogether
    from reportlab.lib.units import mm
    p  = Paragraph(f'<font color="#1D3557"><b>{title}</b></font>', style)
    hr = HRFlowable(width="100%", thickness=0.8, color=accent_color, spaceAfter=4)
    return KeepTogether([p, hr, Spacer(1, 2*mm)])


def _infobox_table(infobox, accent, navy, s_label, s_value, s_tag, PW, ml, mr):
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib import colors
    from reportlab.lib.units import mm

    def _xe(s): return str(s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

    def _tags(vals, unit=""):
        if not vals:
            return Paragraph("—", s_tag)
        def _xe(s): return str(s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        txt = "  ".join(
            '<font color="#4a6b80">{}{}</font>'.format(_xe(v), (" "+unit) if unit else "")
            for v in vals
        )
        return Paragraph(txt, s_tag)

    def _cell(lbl, val_widget):
        return [Paragraph(lbl, s_label), val_widget]

    col_w = (PW - ml - mr) / 3
    rows = [
        [
            _cell("Series",         Paragraph(_xe(infobox.get("seriesName","") or "—"), s_value)),
            _cell("Machine",        Paragraph(_xe(infobox.get("machine","") or "—"), s_value)),
            _cell("Material",       Paragraph(_xe(infobox.get("material","") or "—"), s_value)),
        ],
        [
            _cell("Air Pressure",   _tags(infobox.get("airPressures",[]), "bar")),
            _cell("Overfeed",       _tags(infobox.get("overfeeds",[]),    "%")),
            _cell("Machine Speed",  _tags(infobox.get("speeds",[]),       "m/min")),
        ],
        [
            _cell("Trials",         Paragraph(_xe(infobox.get("nTrials","") or "—"), s_value)),
            _cell("",               Paragraph("", s_value)),
            _cell("",               Paragraph("", s_value)),
        ],
    ]
    flat_rows = []
    for row in rows:
        flat_rows.append([cell[0] for cell in row])
        flat_rows.append([cell[1] for cell in row])

    tbl = Table(flat_rows, colWidths=[col_w, col_w, col_w])
    tbl.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,0),(-1,-1),
         [colors.HexColor("#EEF6EF"), colors.HexColor("#F8FCF8")] * 10),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING",   (0,0), (-1,-1), 3),
        ("BOTTOMPADDING",(0,0), (-1,-1), 3),
        ("LINEBELOW",    (0,1), (-1,1), 0.5, colors.HexColor("#D0E8D4")),
        ("LINEBELOW",    (0,3), (-1,3), 0.5, colors.HexColor("#D0E8D4")),
        ("LINEBELOW",    (0,5), (-1,5), 0.5, colors.HexColor("#D0E8D4")),
        ("BOX",          (0,0), (-1,-1), 1,  colors.HexColor("#C8DFC8")),
    ]))
    return tbl


def _note_block(title, text, s_h2, s_note, navy):
    from reportlab.platypus import Paragraph, KeepTogether
    def _x(s): return str(s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    def _xbr(s):
        """Escape for ReportLab XML and preserve line breaks as <br/>."""
        escaped = _x(s)
        escaped = escaped.replace("\r\n", "\n").replace("\r", "\n")
        return escaped.replace("\n", "<br/>")
    items = []
    if title and str(title).strip():
        items.append(Paragraph(_x(title), s_h2))
    items.append(Paragraph(_xbr(text), s_note))
    return KeepTogether(items)


def _load_pdf_template(template_id=None) -> dict:
    """Lädt ein PDF-Layout-Template aus tblSmartChartPdfTemplate.
    Gibt immer ein vollständiges Dict zurück (Fallback auf Defaults).
    template_id=None → Default-Template (IsDefault=1).
    """
    try:
        import json as _json
        from db.connection import fetch_all, table_exists
        if not table_exists("tblSmartChartPdfTemplate"):
            return dict(_PDF_TEMPLATE_DEFAULTS)
        if template_id:
            rows = fetch_all(
                "SELECT LayoutJSON FROM tblSmartChartPdfTemplate "
                "WHERE ID = ? AND IsActive = 1", [template_id]
            )
        else:
            rows = fetch_all(
                "SELECT LayoutJSON FROM tblSmartChartPdfTemplate "
                "WHERE IsDefault = 1 AND IsActive = 1 LIMIT 1", []
            )
        if not rows:
            # Fallback: erstes aktives Template
            rows = fetch_all(
                "SELECT LayoutJSON FROM tblSmartChartPdfTemplate "
                "WHERE IsActive = 1 ORDER BY ID LIMIT 1", []
            )
        if rows and rows[0].get("LayoutJSON"):
            loaded = _json.loads(rows[0]["LayoutJSON"])
            # Defaults als Basis, geladene Werte überschreiben
            result = dict(_PDF_TEMPLATE_DEFAULTS)
            result.update(loaded)
            return result
    except Exception as e:
        logger.warning("_load_pdf_template: %s — nutze Defaults", e)
    return dict(_PDF_TEMPLATE_DEFAULTS)
