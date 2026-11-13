# db/trial_labels.py
"""Trial labels (spool label with the trial number, template 'TrialLabel') as
PDF - Qt-free, shared by Show Experiment ("Print labels") and the web app.

Moved out of ui/screen_show_experiment.py (_draw_trial_label_cell and the
queries of _on_print_trial_labels) on 2026-11-13 without behaviour change.

    rng = trial_label_range(series_id)        # (lowest, highest) trial number >= 1, None = no trials
    pdf = trial_labels_pdf(series_id, 3, 12)  # bytes; template = saved 'TrialLabel' sheet
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from db.connection import fetch_all
from db.label_sheets import MM, fit_text, label_sheet_pdf_bytes, load_label_template
from db.series_tables import table_exists

TEMPLATE_NAME = "TrialLabel"


def draw_trial_label_cell(page, x0: float, y0: float, lw: float, lh: float, item: Dict) -> None:
    """Zeichnet ein Trial-Label: kleine Kopfzeile 'ExperimentID.Serie' oben,
    darunter die Versuchsnummer (z.B. 'V23') gross - beides zentriert.
    Cell-Renderer fuer generate_label_sheet_pdf."""
    import fitz
    fontname = "hebo"
    max_w = lw - 4

    header_txt = str(item.get("Header") or "").strip()
    header_fs = 9.0
    if header_txt:
        while header_fs > 6.0 and fitz.get_text_length(header_txt, fontname=fontname, fontsize=header_fs) > max_w * MM:
            header_fs -= 0.5
        header_txt = fit_text(header_txt, header_fs, max_w, fontname=fontname)

    v_text = f"V{item['TrialNr']}"
    v_fs = 20.0
    while v_fs > 8.0 and fitz.get_text_length(v_text, fontname=fontname, fontsize=v_fs) > max_w * MM:
        v_fs -= 1.0
    v_text = fit_text(v_text, v_fs, max_w, fontname=fontname)

    # Block (Kopfzeile + V-Nummer) vertikal in der Zelle zentrieren.
    # Wichtig: Schriftgroesse ist in PUNKT, nicht mm - Umrechnung ueber MM
    # (Punkt pro mm) nicht vergessen, sonst wird die Zeilenhoehe massiv
    # unterschaetzt und die beiden Zeilen ueberlappen sich (siehe Chat).
    # Ascent/Descent grob als 0.75/0.25 der Schriftgroesse angenommen.
    def _ascent_mm(fs):
        return (fs * 0.75) / MM

    def _descent_mm(fs):
        return (fs * 0.25) / MM

    header_ascent = _ascent_mm(header_fs) if header_txt else 0.0
    header_descent = _descent_mm(header_fs) if header_txt else 0.0
    gap_mm = 1.8 if header_txt else 0.0
    v_ascent = _ascent_mm(v_fs)
    v_descent = _descent_mm(v_fs)

    block_h = header_ascent + header_descent + gap_mm + v_ascent + v_descent
    block_top = y0 + (lh - block_h) / 2

    if header_txt:
        tw_mm = fitz.get_text_length(header_txt, fontname=fontname, fontsize=header_fs) / MM
        tx = x0 + (lw - tw_mm) / 2
        ty = block_top + header_ascent
        page.insert_text((tx * MM, ty * MM), header_txt, fontsize=header_fs,
                          fontname=fontname, color=(0.4, 0.4, 0.4))
        v_baseline = block_top + header_ascent + header_descent + gap_mm + v_ascent
    else:
        v_baseline = block_top + v_ascent

    tw_mm2 = fitz.get_text_length(v_text, fontname=fontname, fontsize=v_fs) / MM
    tx2 = x0 + (lw - tw_mm2) / 2
    page.insert_text((tx2 * MM, v_baseline * MM), v_text, fontsize=v_fs, fontname=fontname)


def trial_label_range(series_id: Any) -> Optional[Tuple[int, int]]:
    """(lowest, highest) trial number >= 1 of the series (reference samples
    with negative numbers are left out); None = no trials / no tblTrial."""
    if not table_exists("tbltrial"):
        return None
    try:
        rows = fetch_all(
            "SELECT MIN([Versuchsnummer]) AS mn, MAX([Versuchsnummer]) AS mx "
            "FROM tbltrial WHERE [TrialSeriesID] = ? AND [Versuchsnummer] >= 1", [series_id])
    except Exception:
        rows = []
    if not rows or rows[0].get("mn") is None:
        return None
    return int(rows[0]["mn"]), int(rows[0]["mx"])


def trial_label_header(series_id: Any) -> str:
    """"ExperimentID.SS" (first 2 characters of the series name) - the small
    line above the trial number, the same for the whole series."""
    header_txt = ""
    try:
        hrows = fetch_all(
            "SELECT e.[ExperimentID] AS ExpId, s.[SeriesName] AS SeriesName "
            "FROM tbltrialseries s "
            "LEFT JOIN tblexperimente e ON e.[ID] = s.[ExperimentID] "
            "WHERE s.[ID] = ?", [series_id])
        if hrows:
            exp_id = hrows[0].get("ExpId")
            series_name = str(hrows[0].get("SeriesName") or "")
            if exp_id is not None:
                header_txt = f"{exp_id}.{series_name[:2]}"
    except Exception:
        header_txt = ""
    return header_txt


def trial_label_items(header_txt: str, from_no: int, to_no: int) -> List[Dict[str, Any]]:
    return [{"TrialNr": n, "Header": header_txt} for n in range(from_no, to_no + 1)]


def trial_labels_pdf(series_id: Any, from_no: Optional[int] = None, to_no: Optional[int] = None,
                     start_index: int = 0, template: Optional[Dict[str, Any]] = None) -> Optional[bytes]:
    """PDF bytes with one label per trial number from_no..to_no (default: all
    trials >= 1 of the series), starting at cell start_index (0-based) of the
    first sheet. template = sheet geometry (default: the saved 'TrialLabel'
    template). None = the series has no trials."""
    rng = trial_label_range(series_id)
    if rng is None:
        return None
    mn, mx = rng
    f = mn if from_no is None else max(mn, min(int(from_no), mx))
    t = mx if to_no is None else max(mn, min(int(to_no), mx))
    if t < f:
        t = f
    header_txt = trial_label_header(series_id)
    tpl = template or load_label_template(TEMPLATE_NAME)
    return label_sheet_pdf_bytes(trial_label_items(header_txt, f, t), tpl, int(start_index or 0),
                                 draw_trial_label_cell)
