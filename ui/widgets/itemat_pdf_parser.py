from __future__ import annotations
# itemat_pdf_parser.py  –  v9  (ddddocr + direkter Text-Layer-Pfad, alle OCR-Fixes)
"""
Parser fuer Itemat Lab / Enka tecnica Gesamt-Auswertung PDFs.
Benoetigt: pip install pymupdf ddddocr pillow pdfplumber

Zwei Parsing-Pfade:
  1. DIREKT: PDF hat OCR-Text-Layer -> pdfplumber extrahiert Text direkt (schnell, zuverlaessig)
  2. OCR:    Kein Text-Layer -> ddddocr auf gerendertem Bild (bisheriger Weg)

v9-Fixes (gegenueber v8):
  FIX 1 – Knoten/m: Chart-Zeile "200 Knoten/m" wird ignoriert; Parser sucht
           nur Zeilen die nach "Knoten/m" auch Zahlen enthalten.
  FIX 2 – Stab.-Faktor: OCR liest Dezimalpunkt als Zeichensalat ('KLS)', 'Ni].',
           'KL].', '9033' statt '90.3'). Neues _sanitize_value_part() ersetzt
           bekannte Artefakte und _fix_stab_count() erkennt fehlende Werte durch
           Spaltenanzahl-Pruefung und setzt None anstatt falscher Zahlen.
  FIX 3 – Var.-Koeff: OCR liest '.' als 'J', 'u' oder '&' (z.B. '91J2', '96u4',
           '&353'). _sanitize_value_part() normalisiert diese zu korrekten
           Dezimalzahlen vor dem float-Parse.
  FIX 4 – Stab.-Faktor '[%}' (geschweifte Klammer statt eckig): wird als Trennzeichen
           behandelt.
"""
import io
import os
import re
import numpy as np
from typing import Any, Dict, List, Optional, Tuple

DB_TENSIONS = [0.0, 0.3, 0.6, 1.0, 1.3]

_X_LINES       = [250, 587, 763, 939, 1115, 1292, 1468]
_ROW_SPACING   = 107
_ROW_KNOTEN_M  = 4
_ROW_STAB      = 5
_ROW_VAR_KOEFF = 8

_N_STAB_COLS = len(_X_LINES) - 3

# Mindestanzahl Zeichen pro Seite um Text-Layer als vorhanden zu werten
_MIN_TEXT_LEN = 80


# ---------------------------------------------------------------------------
# Debug-Ausgabe
# ---------------------------------------------------------------------------

def _dbg(page_idx: int, msg: str) -> None:
    """Einheitliche Debug-Ausgabe fuer den Parser."""
    print(f"[ItematParser] Seite {page_idx + 1:>3}: {msg}")


# ---------------------------------------------------------------------------
# Interne Hilfsfunktionen – OCR-Pfad (unveraendert aus v5/v6)
# ---------------------------------------------------------------------------

def _get_ocr():
    """Gibt eine ddddocr-Instanz zurueck (lazy singleton)."""
    if not hasattr(_get_ocr, "_instance"):
        try:
            import ddddocr
        except ImportError as e:
            raise RuntimeError(
                "ddddocr nicht installiert.\n"
                "Bitte ausfuehren: pip install ddddocr"
            ) from e
        _get_ocr._instance = ddddocr.DdddOcr(show_ad=False)
    return _get_ocr._instance


def _detect_first_line(arr) -> int:
    """Findet die erste horizontale Trennlinie der Tabelle (nach dem Header)."""
    scan = arr[600:900, 700:760]
    dark = (scan < 100).mean(axis=1)
    for i, f in enumerate(dark):
        if f > 0.30:
            return i + 600
    return 776


def _crop_cell(img, fl: int, row: int, col: int):
    """Schneidet eine Tabellenzelle aus (dynamisches Grid)."""
    y0 = fl + row * _ROW_SPACING + 5
    y1 = fl + (row + 1) * _ROW_SPACING - 5
    x0 = _X_LINES[col] + 5
    x1 = _X_LINES[col + 1] - 5
    return img.crop((x0, y0, x1, y1))


def _read_value(cell_img) -> Optional[float]:
    """
    Liest einen numerischen Wert aus einer Zelle via ddddocr.
    Dezimalpunkt wird immer vor der letzten Stelle eingefuegt.
    """
    from PIL import Image
    ocr  = _get_ocr()
    cell = cell_img.resize((cell_img.width * 3, cell_img.height * 3), Image.LANCZOS)
    buf  = io.BytesIO()
    cell.save(buf, format="PNG")
    raw  = ocr.classification(buf.getvalue())

    digits = re.sub(r'[^0-9]', '', raw)
    if not digits:
        return None

    if len(digits) == 1:
        val_str = "0." + digits
    else:
        val_str = digits[:-1] + "." + digits[-1]

    try:
        return float(val_str)
    except Exception:
        return None


def _render_page(pdf_path: str, page_index: int):
    """Rendert eine PDF-Seite als PIL-Graustufenbild bei 300 dpi."""
    try:
        import fitz
    except ImportError as e:
        raise RuntimeError("PyMuPDF nicht installiert. pip install pymupdf") from e
    from PIL import Image
    doc = fitz.open(pdf_path)
    try:
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = doc[page_index].get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
        return Image.open(io.BytesIO(pix.tobytes("png")))
    finally:
        doc.close()


def _read_versuch_nr_ocr(img, ocr) -> Optional[int]:
    """
    Liest die Versuchsnummer aus der Bemerkung-Zeile via OCR (z.B. 'V67' -> 67).
    """
    from PIL import Image, ImageEnhance
    for y0 in [365, 370, 360, 380, 385, 375, 390, 395]:
        crop = img.crop((50, y0, 900, y0 + 65))
        w, h = crop.size
        crop_big = crop.resize((w * 4, h * 4), Image.LANCZOS)
        crop_big = ImageEnhance.Contrast(crop_big).enhance(4.0)
        arr = np.array(crop_big)
        arr = np.where(arr < 128, 0, 255).astype(np.uint8)
        buf = io.BytesIO()
        Image.fromarray(arr).save(buf, format="PNG")
        raw = ocr.classification(buf.getvalue())
        m = re.search(r'[Vv]([0-9OoIlSsBb]+)', raw)
        if m:
            digits = m.group(1).translate(str.maketrans('OoIlSsBb', '00115588'))
            try:
                val = int(digits)
                if val > 0:
                    return val
            except Exception:
                pass
    return None


# ---------------------------------------------------------------------------
# Interne Hilfsfunktionen – Direkter Text-Layer-Pfad
# ---------------------------------------------------------------------------

def _extract_page_text(pdf_path: str, page_index: int) -> Optional[str]:
    """
    Versucht Text direkt aus dem PDF-Text-Layer zu lesen via pdfplumber.
    Gibt None zurueck wenn kein genuegend langer Text gefunden wird.
    """
    try:
        import pdfplumber
    except ImportError:
        return None

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_index >= len(pdf.pages):
                return None
            page = pdf.pages[page_index]
            text = page.extract_text()
        if text and len(text.strip()) >= _MIN_TEXT_LEN:
            return text.strip()
        return None
    except Exception:
        return None


def _normalize_dashes(s: str) -> str:
    """
    Normalisiert alle Bindestrich-Varianten auf ASCII-Minus.
    Em-Dash u2014, En-Dash u2013, Minus u2212, Non-breaking hyphen u2011.
    """
    return re.sub(r'[\u2013\u2014\u2212\u2011\u00AD]', '-', s)


def _sanitize_value_part(s: str) -> str:
    """
    Bereinigt den Werteteil einer extrahierten Tabellenzeile vor dem Float-Parse.

    Behandelt folgende OCR-Artefakte aus gescannten Itemat-PDFs:

    1. Dezimalpunkt als 'J': '91J2' -> '91.2', '88J2' -> '88.2', '86J2' -> '86.2'
       Muster: Ziffer(n) + J + Ziffer(n) -> Ziffer(n) + '.' + Ziffer(n)

    2. Dezimalpunkt als 'u': '96u4' -> '96.4', '73u7' -> '73.7'
       Muster: Ziffer(n) + u + Ziffer(n) -> wie oben

    3. Sonderzeichen als Dezimaltrenner: '&353' -> '88.3' ist nicht zuverlaessig
       rekonstruierbar; solche Tokens werden entfernt (None-safe).
       Stattdessen: Token das kein gueltiges Muster ergibt -> wird ignoriert.

    4. Schraegstrich als Dezimaltrenner: '73/7' -> '73.7'
       Muster: Ziffer(n) + '/' + Ziffer(n) -> wie oben (aber nur wenn beide
       Seiten kurz genug sind fuer einen Dezimalwert, nicht fuer Knoten/m-Label)

    5. Eckige/geschweifte Klammern, %, | werden als Whitespace behandelt.
    """
    # Geschweifte Klammer als eckige behandeln (OCR-Artefakt: '[%}' statt '[%]')
    s = s.replace('{', '[').replace('}', ']')
    # Klammern und % entfernen
    s = re.sub(r'[\[\]%{}]', ' ', s)
    # Trennzeichen normalisieren
    s = re.sub(r'[|!]', ' ', s)
    # OCR: 'J' als Dezimalpunkt zwischen Ziffern: '91J2' -> '91.2'
    s = re.sub(r'(\d+)[Jj](\d+)', r'\1.\2', s)
    # OCR: 'u' als Dezimalpunkt zwischen Ziffern: '96u4' -> '96.4'
    s = re.sub(r'(\d+)u(\d+)', r'\1.\2', s)
    # OCR: 'A' als Dezimalpunkt zwischen Ziffern: '73A9' -> '73.9'
    s = re.sub(r'(\d+)A(\d+)', r'\1.\2', s)
    # OCR: Schraegstrich als Dezimalpunkt zwischen kurzen Ziffernfolgen: '73/7' -> '73.7'
    s = re.sub(r'(\d{1,3})/(\d{1,2})(?!\d)', r'\1.\2', s)
    # OCR: 4-stellige Ganzzahl die eigentlich xx.xx ist: '9033' -> '90.33'
    # Heuristik: Punkt nach Stelle 2 einfuegen wenn Ergebnis im Bereich 0-110
    def _fix_4digit(m):
        v = m.group(0)
        candidate = v[:2] + '.' + v[2:]
        try:
            if 0.0 < float(candidate) <= 110.0:
                return candidate
        except Exception:
            pass
        return v
    s = re.sub(r'\b\d{4}\b', _fix_4digit, s)
    # Sonderzeichen-Tokens die keine Zahl ergeben, bereinigen: '&353', ''NL].' etc.
    # -> Tokens mit fuehrenden Nicht-Ziffer-Zeichen entfernen
    tokens = s.split()
    clean = []
    for t in tokens:
        # Behalte Token wenn er mit Ziffer oder '-' beginnt
        if re.match(r'^-?\d', t):
            clean.append(t)
        # Sonst verwerfen (OCR-Zeichensalat)
    s = ' '.join(clean)
    return s


def _parse_float(s: str) -> Optional[float]:
    """Parst einen float-String, toleriert Komma als Dezimaltrenner."""
    if not s:
        return None
    s = s.replace(',', '.').strip()
    try:
        return float(s)
    except Exception:
        return None


def _parse_versuch_nr_from_text(text: str) -> Optional[int]:
    """
    Extrahiert die Versuchsnummer aus dem Text-Layer.
    Behandelt OCR-Varianten: 'Vll' -> 11, 'Vl2' -> 12, 'V2O' -> 20 etc.
    """
    text_norm = _normalize_dashes(text)

    m = re.search(r'Bemerkung\s*[:\s]+([Vv]{1,2}\w+)', text_norm)
    if m:
        raw = m.group(1)
        raw = re.sub(r'^[Vv]{2}', 'V', raw)
        # OCR-Zeichenersetzungen nach 'V': l->1, I->1, O->0, S->5, B->8
        raw = raw.translate(str.maketrans('lISOoBb', '1150088'))
        digits = re.sub(r'[^0-9]', '', raw[1:])
        if digits:
            try:
                val = int(digits)
                if val > 0:
                    return val
            except Exception:
                pass
    # Fallback
    m = re.search(r'\b[Vv](\d{1,3})\b', text_norm)
    if m:
        return int(m.group(1))
    return None


def _split_stuck_numbers(s: str) -> str:
    """
    Trennt zusammengeklebte Dezimalzahlen auf.
    Beispiel: '100.096.2' -> '100.0 96.2'
    """
    return re.sub(r'(\d+\.\d+)(?=\d)', r'\1 ', s)


def _parse_row_values(text: str, row_label: str,
                      require_digits: bool = False) -> List[Optional[float]]:
    """
    Sucht die Zeile mit row_label im Text und extrahiert alle Zahlen dahinter.

    require_digits=True: Zeile wird nur akzeptiert wenn nach dem Label auch
    tatsaechlich Ziffern folgen. Noetig fuer 'Knoten/m' um die Chart-Achsen-
    beschriftung '200 Knoten/m' zu ueberspringen.
    """
    norm_label = _normalize_dashes(row_label)

    lines = text.splitlines()
    for line in lines:
        norm_line = _normalize_dashes(line)
        if not re.search(re.escape(norm_label), norm_line, re.IGNORECASE):
            continue

        # Label entfernen
        value_part = re.sub(re.escape(norm_label), '', norm_line, count=1,
                            flags=re.IGNORECASE)

        # require_digits: ueberspringen wenn kein Zifferninhalt
        if require_digits and not re.search(r'\d', value_part):
            continue

        # Sanitize: OCR-Artefakte bereinigen
        value_part = _sanitize_value_part(value_part)
        value_part = re.sub(r'\s+', ' ', value_part).strip()
        value_part = _split_stuck_numbers(value_part)

        nums = re.findall(r'-?\d+(?:[.,]\d+)?', value_part)
        result = [_parse_float(n) for n in nums]
        if result:
            return result
    return []


def _parse_row_values_regex(text: str, label_pattern: str,
                             require_digits: bool = False) -> List[Optional[float]]:
    """
    Wie _parse_row_values, aber mit Regex als Label-Muster.
    Noetig fuer 'Var.-Koeff' vs 'Ver.-Koeff' (OCR a/e-Verwechslung).
    """
    norm_pattern = _normalize_dashes(label_pattern)

    lines = text.splitlines()
    for line in lines:
        norm_line = _normalize_dashes(line)
        if not re.search(norm_pattern, norm_line, re.IGNORECASE):
            continue

        value_part = re.sub(norm_pattern, '', norm_line, count=1, flags=re.IGNORECASE)

        if require_digits and not re.search(r'\d', value_part):
            continue

        value_part = _sanitize_value_part(value_part)
        value_part = re.sub(r'\s+', ' ', value_part).strip()
        value_part = _split_stuck_numbers(value_part)

        nums = re.findall(r'-?\d+(?:[.,]\d+)?', value_part)
        result = [_parse_float(n) for n in nums]
        if result:
            return result
    return []


def _fix_stab_values(stab_vals: List[Optional[float]],
                     expected_count: int) -> List[Optional[float]]:
    """
    Bereinigt Stab.-Faktor-Werte:
    1. Werte > 110 mit fuehrender '1': 1100.0 -> 100.0
    2. Wenn nach der Bereinigung mehr Werte als erwartet: ueberzaehlige entfernen.
    3. Wenn weniger als erwartet: mit None auffuellen.

    Hintergrund: OCR liest manchmal einen Stab-Wert als Zeichensalat der komplett
    ignoriert wird (z.B. 'KLS)', 'Ni].') -> die Spalte fehlt dann und alle
    nachfolgenden Werte verschieben sich um eine Position. Durch Pruefung der
    Anzahl kann dies nicht korrigiert werden (wir wissen nicht WELCHE Spalte fehlt),
    daher wird bei Anzahl-Abweichung None gesetzt.
    """
    fixed = []
    for v in stab_vals:
        if v is None:
            fixed.append(None)
        elif v > 110:
            s = str(v)
            if s.startswith('1') and len(s) > 4:
                candidate = _parse_float(s[1:])
                if candidate is not None and 0 <= candidate <= 110:
                    fixed.append(candidate)
                    continue
            fixed.append(v)
        else:
            fixed.append(v)

    # Anzahl anpassen
    while len(fixed) < expected_count:
        fixed.append(None)
    return fixed[:expected_count]


def _parse_page_from_text(text: str) -> Dict[str, Any]:
    """
    Parst alle benoetigten Werte aus dem Text-Layer einer Seite.

    Gibt dict zurueck: versuch_nr, knoten_m, var_koeff, stability (Liste)
    """
    versuch_nr = _parse_versuch_nr_from_text(text)

    # Debug: relevante Rohzeilen
    for line in text.splitlines():
        norm = _normalize_dashes(line)
        if any(kw in norm for kw in ['Stab.-Faktor', 'Koeff', 'Knoten/m']):
            print(f"  [ItematParser] RAW LINE: {repr(line)}")

    # FIX 1: require_digits=True -> "200 Knoten/m" (Chart-Achse) wird uebersprungen
    knoten_vals = _parse_row_values(text, "Knoten/m", require_digits=True)
    knoten_m    = knoten_vals[0] if knoten_vals else None

    # FIX 3: Regex matcht Var./Ver., sanitize_value_part behebt J/u-Artefakte
    var_vals  = _parse_row_values_regex(text, r'[Vv][ae]r\.-Koeff', require_digits=True)
    var_koeff = var_vals[0] if var_vals else None

    # FIX 2+4: sanitize_value_part + fix_stab_values mit expected_count
    stab_vals = _parse_row_values(text, "Stab.-Faktor", require_digits=True)
    if len(stab_vals) > 1:
        # stab_vals[0] = 100.0 (Tension 0.0), nicht benoetigt
        stability = stab_vals[1:]
        stability = _fix_stab_values(stability, _N_STAB_COLS)
    else:
        stability = [None] * _N_STAB_COLS

    return {
        "versuch_nr": versuch_nr,
        "knoten_m":   knoten_m,
        "var_koeff":  var_koeff,
        "stability":  stability,
    }


# ---------------------------------------------------------------------------
# Oeffentliche API
# ---------------------------------------------------------------------------

def parse_itemat_pdf(
    pdf_path: str,
    progress_callback=None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Hauptfunktion: parst einen Itemat-PDF-Bericht und gibt Messwerte je Spule zurueck.

    Erkennt automatisch ob ein OCR-Text-Layer vorhanden ist:
      - Text-Layer vorhanden  -> direkter Parse via pdfplumber (schnell)
      - Kein Text-Layer       -> OCR via ddddocr auf gerendertem Bild

    Args:
        pdf_path:          Pfad zur PDF-Datei.
        progress_callback: Optionale Funktion(current, total) fuer Fortschrittsanzeige.

    Returns:
        Tupel (header, records). header = dict mit Kopfdaten,
        records = Liste von Dicts pro Seite mit Knoten/m, Stabilitaet, CV-Werten.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(pdf_path)

    try:
        import fitz
    except ImportError as e:
        raise RuntimeError("PyMuPDF nicht installiert. pip install pymupdf") from e

    doc     = fitz.open(pdf_path)
    n_pages = doc.page_count
    doc.close()

    print(f"[ItematParser] *** Starte Parse: {os.path.basename(pdf_path)} ({n_pages} Seiten) ***")

    n_direct = 0
    n_ocr    = 0

    header: Dict[str, Any]        = {"pdf": os.path.basename(pdf_path)}
    records: List[Dict[str, Any]] = []

    _ocr_instance = None

    for i in range(n_pages):
        if progress_callback:
            try:
                progress_callback(i + 1, n_pages)
            except Exception:
                pass

        text = _extract_page_text(pdf_path, i)

        if text is not None:
            parsed = _parse_page_from_text(text)
            _dbg(i, f"DIREKT (Text-Layer, {len(text)} Zeichen) "
                     f"-> V{parsed['versuch_nr']}  "
                     f"Knoten/m={parsed['knoten_m']}  "
                     f"VarKoeff={parsed['var_koeff']}  "
                     f"Stab={parsed['stability']}")
            n_direct += 1

            records.append({
                "page":       i + 1,
                "versuch_nr": parsed["versuch_nr"],
                "knoten_m":   parsed["knoten_m"],
                "var_koeff":  parsed["var_koeff"],
                "stability":  parsed["stability"],
            })

        else:
            if _ocr_instance is None:
                print("[ItematParser] Lade ddddocr-Modell...")
                _ocr_instance = _get_ocr()

            img = _render_page(pdf_path, i)
            arr = np.array(img)
            fl  = _detect_first_line(arr)

            versuch_nr = _read_versuch_nr_ocr(img, _ocr_instance)
            knoten_m   = _read_value(_crop_cell(img, fl, _ROW_KNOTEN_M, 1))
            var_koeff  = _read_value(_crop_cell(img, fl, _ROW_VAR_KOEFF, 1))
            stability  = [
                _read_value(_crop_cell(img, fl, _ROW_STAB, c + 2))
                for c in range(_N_STAB_COLS)
            ]

            _dbg(i, f"OCR (ddddocr) "
                     f"-> V{versuch_nr}  "
                     f"Knoten/m={knoten_m}  "
                     f"VarKoeff={var_koeff}  "
                     f"Stab={stability}")
            n_ocr += 1

            records.append({
                "page":       i + 1,
                "versuch_nr": versuch_nr,
                "knoten_m":   knoten_m,
                "var_koeff":  var_koeff,
                "stability":  stability,
            })

    print(f"[ItematParser] *** Fertig: {n_direct} Seiten DIREKT, {n_ocr} Seiten via OCR ***")
    return header, records