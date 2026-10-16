from __future__ import annotations
# ui/widgets/statimat_pdf_parser.py
"""Parser für Statimat-Messberichte im PDF-Format.

Liest PDF-Berichte des Statimat-Garnprüfgeräts aus und extrahiert:
  - Geräte-/Kopfinformationen (Gerät, Material, Kunde usw.)
  - Messwerte je Spule (Feinheit, Dehnung, Festigkeit, Feinheitsbruchkraft)

Hauptfunktion: ``parse_statimat_pdf(pdf_path)``

Rückgabe::
    (header_dict, spools_list)

    header_dict: {"Gerät": ..., "Material": ..., "Artikel": ...}
    spools_list: [{"Nr": 1, "Feinheit": 100.0, "Dehnung_CV": 2.1, ...}, ...]

Abhängigkeiten:
    pdfplumber  (pip install pdfplumber)
    unicodedata (stdlib)

Robustheit:
    Der Parser ist defensiv geschrieben: fehlende Felder werden als None
    zurückgegeben, Ausnahmen werden still ignoriert. Typische Fehlquellen
    sind Unterschiede im PDF-Layout zwischen Statimat-Softwareversionen.
"""


import os
import re
import unicodedata
from typing import Any, Dict, List, Tuple, Optional

_NUM = r"([0-9]+(?:[.,][0-9]+)?)"


def _to_float(s: str) -> Optional[float]:
    """Konvertiert einen String (Komma oder Punkt als Dezimaltrennzeichen) in float."""
    s = (s or "").strip().replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def _strip_diacritics(s: str) -> str:
    """Remove diacritics and normalise whitespace (e.g. 'Gerät' -> 'Gerat')."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("\u00a0", " ")
    return s


def _norm_for_contains(s: str) -> str:
    """Normalisiert einen String für robuste Teilstring-Suche (lowercase, Diakritika entfernt)."""
    """Uppercase, strip diacritics, collapse ALL whitespace to single spaces."""
    s = _strip_diacritics(s)
    return " ".join(s.upper().split())


def _extract_customer_material(full_text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extrahiert Kundenmaterial-Bezeichnung und Artikelnummer aus dem PDF-Volltext."""
    """
    Extract:
      Customer: between 'Customer' and 'Material'
      Material: after 'Material' until end of that line
    """
    for ln in (full_text or "").splitlines():
        if "Customer" in ln and "Material" in ln:
            line = " ".join(ln.strip().split())
            m = re.search(r"\bCustomer\s+(.*?)\s+Material\s+(.+)\s*$", line)
            if m:
                return m.group(1).strip() or None, m.group(2).strip() or None
    return None, None


def _extract_device_exact(full_text: str) -> Optional[str]:
    """Extrahiert die Gerätekennung aus dem PDF-Text (exakte Regex-Suche)."""
    """
    EXACT device detection (but whitespace-normalized):
      - if 'STATIMAT DS' is contained -> STATIMAT DS
      - elif 'STATIMAT M' is contained -> STATIMAT M
      - else None
    """
    nt = _norm_for_contains(full_text or "")
    if "STATIMAT DS" in nt:
        return "STATIMAT DS"
    if "STATIMAT M" in nt:
        return "STATIMAT M"
    return None


def _extract_device_raw_hint(full_text: str) -> Optional[str]:
    """Fallback: extrahiert Gerätehinweis aus rohem Text wenn _extract_device_exact fehlschlägt."""
    """Best-effort raw hint for debugging in UI messages."""
    if not full_text:
        return None
    nt_lines = full_text.splitlines()
    for ln in nt_lines:
        if "STATIMAT" in ln.upper():
            return " ".join(ln.strip().split())[:200] or None
    # fallback: first 200 chars
    s = " ".join(full_text.strip().split())
    return (s[:200] if s else None)


def _extract_page_text(pdf_path: str) -> List[str]:
    """Liest alle Seiten des PDFs mit pdfplumber und gibt Zeilen als Liste zurück."""
    """
    Text extraction:
    1) pdfplumber
    2) per-page fallback to PyMuPDF (fitz) if pdfplumber returns empty for a page
    """
    try:
        import pdfplumber
    except ImportError as e:
        raise RuntimeError("pdfplumber is not installed. Please run: pip install pdfplumber") from e

    page_texts: List[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_texts.append(page.extract_text() or "")

    if any((not (t or "").strip()) for t in page_texts):
        try:
            import fitz  # PyMuPDF
        except Exception:
            return page_texts

        doc = fitz.open(pdf_path)
        for i in range(min(doc.page_count, len(page_texts))):
            if not (page_texts[i] or "").strip():
                page_texts[i] = doc[i].get_text("text") or ""
        doc.close()

    return page_texts


def _find_spool_no(text: str, page_index: int = 0) -> Optional[int]:
    """Extrahiert die Spulennummer aus einer Textzeile (z.B. "Spule 3" oder "Spule V3").

    Falls nur "Spule Vx" ohne Nummer steht (STATIMAT M Einzelmessung),
    wird der 1-basierte Seitenindex als Fallback zurückgegeben.
    """
    m = re.search(r"\bSpule\s+V?(\d+)\b", text or "")
    if m:
        return int(m.group(1))
    # Fallback: "Spule Vx" or similar without a number -> use page position
    if re.search(r"\bSpule\b", text or ""):
        return page_index + 1
    return None


def _find_line(lines: List[str], startswith: str) -> Optional[str]:
    """Sucht die erste Zeile die mit startswith beginnt (case-insensitive).

    Exact-word boundary: the match must be followed by whitespace or end-of-string,
    so that e.g. startswith="Feinheit" does NOT match "Feinheitsb.Kraft".
    """
    sw = startswith.strip()
    for ln in lines:
        l = ln.strip()
        if l.startswith(sw) and (len(l) == len(sw) or l[len(sw)] in (" ", "\t")):
            return l
    return None


def _parse_feinheit(line: str) -> Optional[float]:
    """Extrahiert Feinheitswert [dtex] aus einer Messzeile."""
    m = re.search(rf"^Feinheit\s+\d+\s+{_NUM}", line)
    return _to_float(m.group(1)) if m else None


def _parse_dehnung(line: str) -> Tuple[Optional[float], Optional[float]]:
    """Extrahiert Dehnungs-Mittelwert und CV% aus einer Messzeile. Gibt (mean, cv) zurück."""
    m = re.search(rf"^Dehnung.*?\s+\d+\s+{_NUM}\s*%?\s+{_NUM}\s+{_NUM}\b", line)
    if not m:
        return None, None
    x = _to_float(m.group(1))
    cv = _to_float(m.group(3))
    return x, cv


def _parse_festigkeit(line: str) -> Tuple[Optional[float], Optional[float]]:
    """Extrahiert Festigkeits-Mittelwert und CV% aus einer Messzeile. Gibt (mean, cv) zurück."""
    m = re.search(rf"^Festigkeit\s+\d+\s+{_NUM}\s*([^\s]+)?\s+{_NUM}\s+{_NUM}\b", line)
    if not m:
        return None, None
    x = _to_float(m.group(1))
    cv = _to_float(m.group(4))
    return x, cv


def _parse_feinheitsb_kraft(line: str) -> Tuple[Optional[float], Optional[float]]:
    """Extrahiert Feinheitsbruchkraft-Mittelwert und CV% aus einer Messzeile."""
    """Parse 'Feinheitsb.Kraft' line from Statimat M reports.
    Example: 'Feinheitsb.Kraft 20 4,08 cN/dtex 0,09 2,21 0,04 3,83 4,21'
    Columns: N  X  unit  S  CV  Q  MIN  MAX
    """
    m = re.search(rf"^Feinheitsb\.Kraft\s+\d+\s+{_NUM}\s*(?:cN/dtex)?\s+{_NUM}\s+{_NUM}\b", line)
    if not m:
        return None, None
    x = _to_float(m.group(1))
    cv = _to_float(m.group(3))
    return x, cv


def parse_statimat_pdf(pdf_path: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Hauptfunktion: parst einen Statimat-PDF-Bericht vollständig.

    Args:
        pdf_path: Pfad zur PDF-Datei.

    Returns:
        Tupel (header, spools):
        - header: Dict mit Kopfdaten (Gerät, Material, Artikel, usw.)
        - spools: Liste von Dicts, eine pro Spule, mit Messwerten
          (Nr, Feinheit, Dehnung_mean, Dehnung_CV, Festigkeit_mean, usw.)
    """
    """
    Returns:
      header: dict with keys: customer, material, device, device_raw
      records: list per page/spool with:
        page, spool_no, feinheit_x, dehnung_x, dehnung_cv, festigkeit_x, festigkeit_cv
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(pdf_path)

    page_texts = _extract_page_text(pdf_path)
    full_text = "\n\n".join(page_texts)

    customer, material = _extract_customer_material(full_text)
    device = _extract_device_exact(full_text)
    device_raw = _extract_device_raw_hint(full_text)

    header: Dict[str, Any] = {
        "customer": customer,
        "material": material,
        "device": device,
        "device_raw": device_raw,
    }

    is_m = (device == "STATIMAT M")

    records: List[Dict[str, Any]] = []
    for i, text in enumerate(page_texts):
        lines = [ln for ln in (text.splitlines() if text else []) if ln.strip()]

        spool_no = _find_spool_no(text, page_index=i)

        fein_line = _find_line(lines, "Feinheit")
        dehn_line = _find_line(lines, "Dehnung")

        fein_x = _parse_feinheit(fein_line) if fein_line else None
        dehn_x, dehn_cv = _parse_dehnung(dehn_line) if dehn_line else (None, None)

        if is_m:
            # Statimat M: Feinheitsb.Kraft liefert die spezifische Festigkeit (cN/dtex)
            fb_line = _find_line(lines, "Feinheitsb.Kraft")
            fest_x, fest_cv = _parse_feinheitsb_kraft(fb_line) if fb_line else (None, None)
        else:
            # Statimat DS: klassische Festigkeit-Zeile
            fest_line = _find_line(lines, "Festigkeit")
            fest_x, fest_cv = _parse_festigkeit(fest_line) if fest_line else (None, None)

        records.append({
            "page": i + 1,
            "spool_no": spool_no,
            "feinheit_x": fein_x,
            "dehnung_x": dehn_x,
            "dehnung_cv": dehn_cv,
            "festigkeit_x": fest_x,
            "festigkeit_cv": fest_cv,
        })

    return header, records