from __future__ import annotations
# ui/yarnscope/dty_tdms_reader.py
"""TDMS-Datei-Reader für DTY-Dickenmessungen (YarnScope / Statimat).

Liest NI-TDMS-Dateien (National Instruments) aus, die vom Statimat-Messgerät
erzeugt werden. Liefert das numerische Datensignal (Garndicken-Array) sowie
den Messabstand (Schrittweite) in Millimetern.

Hauptfunktionen:
    read_first_numeric_channel(path)   → numpy-Array der ersten numerischen Spur
    read_step_mm_from_tdms(path)       → Schrittweite in mm (aus Properties oder berechnet)
    points_per_meter(step_mm)          → Datenpunkte pro Meter

Abhängigkeiten:
    nptdms  (pip install nptdms)
    numpy

Schrittweiten-Ermittlung (Priorität):
    1. Direkte Properties (File/Group/Channel): Messabstand, Step, DeltaX, …
    2. Parameter/Wert/Einheit-Kanal-Struktur (Statimat-spezifisches Format)
    3. Berechnung: Geschwindigkeit [mm/s] / Messfrequenz [Hz]
    4. None wenn keine der Strategien erfolgreich ist.
"""

from pathlib import Path
import re
import numpy as np
from nptdms import TdmsFile


def _normalize_key(s: str) -> str:
    """Normalisiert einen Property-/Kanal-Namen für tolerante Vergleiche.

    Wandelt in Kleinbuchstaben um und entfernt alle Nicht-Alphanumzeichen,
    sodass z.B. ``"Mess Abstand [mm]"`` und ``"messabstandmm"`` gleich sind.
    """
    s = str(s).casefold()
    return re.sub(r"[^a-z0-9]+", "", s)


def _try_parse_mm(value, unit_hint: str | None = None):
    """Versucht, einen Wert als Millimeter zu parsen.

    Unterstützt folgende Eingaben:
    - Zahlen (int/float): direkt übernommen, ausser unit_hint = 'm' → ×1000
    - Strings mit Einheit: ``"0.1 mm"``, ``"0.1 m"``, ``"100 mm"``
    - Strings ohne Einheit: direkt als float geparst

    Args:
        value:     Zu parsender Wert (int, float, str oder None).
        unit_hint: Optionaler Einheiten-Hinweis aus einem separaten Kanal
                   (z.B. ``"m"`` → Ergebnis ×1000).

    Returns:
        Wert in mm als float, oder None bei Fehler.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        if unit_hint and unit_hint.strip().lower() in {"m", "meter", "meters"}:
            return v * 1000.0
        return v
    s = str(value).strip().replace(",", ".")
    m = re.search(r"([\-+]?\d+(?:\.\d+)?)\s*([a-zµμ/]*)$",
                  s, flags=re.IGNORECASE)
    if m:
        num = m.group(1)
        unit = (m.group(2) or "").lower()
        try:
            v = float(num)
        except Exception:
            return None
        if unit in {"mm", "millimeter", "millimetre"}:
            return v
        if unit in {"m", "meter", "metre"}:
            return v * 1000.0
        return v   # unbekannte Einheit → Wert unverändert
    try:
        return float(s)
    except Exception:
        return None


def read_first_numeric_channel(path: Path):
    """Liest den ersten numerischen Kanal aus einer TDMS-Datei.

    Iteriert über alle Groups und Channels und gibt den ersten Kanal zurück,
    dessen Daten als Zahlenarray interpretierbar sind. Dieser Kanal entspricht
    in Statimat-Dateien typischerweise der Garndicken-Messung.

    Args:
        path: Pfad zur .tdms-Datei.

    Returns:
        numpy-Array (float64) mit den Messwerten, oder None wenn kein
        numerischer Kanal gefunden wurde oder die Datei nicht lesbar ist.
    """
    tdms = TdmsFile.read(str(path))
    for grp in tdms.groups():
        for ch in grp.channels():
            try:
                arr = np.asarray(ch[:])
                if arr.size > 0 and np.issubdtype(arr.dtype, np.number):
                    return np.asarray(arr, dtype=float)
            except Exception:
                continue
    return None


def read_step_mm_from_tdms(path: Path) -> float | None:
    """Ermittelt die Messschrittweite in mm aus einer TDMS-Datei.

    Strategie (in dieser Reihenfolge):
    1. Direkte Properties (file-/group-/channel-level): sucht nach Schlüsseln
       wie 'messabstand', 'stepmm', 'deltax', 'samplespacing' usw.
    2. Parameter/Wert/Einheit-Kanal-Struktur (Statimat-Format): sucht nach
       Kanälen namens 'Parameter', 'Wert', 'Einheit' in derselben Group.
    3. Berechnung aus Geschwindigkeit und Messfrequenz:
       step_mm = speed_mm_per_s / freq_hz

    Args:
        path: Pfad zur .tdms-Datei.

    Returns:
        Schrittweite in mm als float, oder None wenn nicht ermittelbar.
    """
    try:
        tdms = TdmsFile.read(str(path))
    except Exception:
        return None

    # --- Alle Properties aus File, Groups und Channels sammeln ---
    all_props = []
    try:
        for k, v in (tdms.properties or {}).items():
            all_props.append(("file", str(k), v))
        for grp in tdms.groups():
            for k, v in (getattr(grp, "properties", {}) or {}).items():
                all_props.append(
                    (f"group:{getattr(grp, 'name', '?')}", str(k), v))
            for ch in grp.channels():
                for k, v in (getattr(ch, "properties", {}) or {}).items():
                    all_props.append(
                        (f"chan:{getattr(grp, 'name', '?')}/{getattr(ch, 'name', '?')}", str(k), v))
    except Exception:
        pass

    # --- Strategie 1: Direkte Property-Schlüssel ---
    candidates = [
        "messabstand", "messabstandmm", "schrittweite", "abstand",
        "step", "stepmm", "deltax", "dx", "samplespacing", "sampledistance", "spacing", "increment"
    ]
    for _, key, val in all_props:
        nk = _normalize_key(key)
        if any(c in nk for c in candidates):
            parsed = _try_parse_mm(val)
            if parsed is not None:
                return float(parsed)

    # --- Strategie 2: Parameter/Wert/Einheit-Kanal-Struktur (Statimat) ---
    try:
        for grp in tdms.groups():
            ch_param = ch_wert = ch_einh = None
            for ch in grp.channels():
                nkn = _normalize_key(ch.name)
                if nkn == "parameter":
                    ch_param = ch
                elif nkn in {"wert", "value", "values"}:
                    ch_wert = ch
                elif nkn in {"einheit", "einheiten", "unit", "units"}:
                    ch_einh = ch
            if ch_param is None or ch_wert is None:
                continue

            params = [str(x).strip() for x in ch_param[:]]
            werte = list(ch_wert[:])
            einhs = list(ch_einh[:]) if ch_einh is not None else [None] * len(werte)
            n = min(len(params), len(werte), len(einhs))
            for i in range(n):
                key_norm = _normalize_key(params[i])
                if any(c in key_norm for c in ["messabstand", "schrittweite", "samplespacing", "deltax", "dx", "abstand"]):
                    val = werte[i]
                    unit_hint = (str(einhs[i]).strip().lower()
                                 if i < len(einhs) and einhs[i] is not None else None)
                    parsed = _try_parse_mm(val, unit_hint=unit_hint)
                    if parsed is not None:
                        return float(parsed)
    except Exception:
        pass

    # --- Strategie 3: Berechnung aus Geschwindigkeit + Frequenz ---
    speed_mm_per_s = None
    freq_hz = None

    # Direkte Properties nach Geschwindigkeit und Frequenz durchsuchen
    for _, key, val in all_props:
        nk = _normalize_key(key)
        if any(tok in nk for tok in ("geschwindigkeit", "speed")) and speed_mm_per_s is None:
            s = str(val).replace(",", ".")
            try:
                num = float(re.findall(r"[-+]?\d+(?:\.\d+)?", s)[0])
                if "m/min" in s.lower() or "mpermin" in s.lower():
                    speed_mm_per_s = (num * 1000.0) / 60.0
                else:
                    speed_mm_per_s = num  # Annahme: bereits mm/s
            except Exception:
                pass
        if any(tok in nk for tok in ("messfrequenz", "samplingrate", "frequenz", "hz", "freq")) and freq_hz is None:
            try:
                freq_hz = float(str(val).replace(",", "."))
            except Exception:
                pass

    # Zusätzlich Parameter/Wert-Kanal nach Geschwindigkeit/Frequenz durchsuchen
    try:
        for grp in tdms.groups():
            lookup = {}
            chp = chw = che = None
            for ch in grp.channels():
                nkn = _normalize_key(ch.name)
                if nkn == "parameter":
                    chp = ch
                elif nkn in {"wert", "value", "values"}:
                    chw = ch
                elif nkn in {"einheit", "einheiten", "unit", "units"}:
                    che = ch
            if chp is None or chw is None:
                continue
            params = [str(x).strip() for x in chp[:]]
            werte = list(chw[:])
            einhs = list(che[:]) if che is not None else [None] * len(werte)
            for i in range(min(len(params), len(werte))):
                lookup[_normalize_key(params[i])] = (
                    werte[i],
                    (str(einhs[i]).strip().lower() if i < len(einhs) and einhs[i] is not None else None)
                )
            for k in list(lookup.keys()):
                v, u = lookup[k]
                if "geschwindigkeit" in k or "speed" in k:
                    try:
                        num = float(str(v).replace(",", "."))
                        speed_mm_per_s = (
                            num * 1000.0) / 60.0 if ((u and "m/min" in u) or "m/min" in str(v).lower()) else num
                    except Exception:
                        pass
                if "messfrequenz" in k or "samplingrate" in k or "frequenz" in k or k.endswith("hz"):
                    try:
                        freq_hz = float(str(v).replace(",", "."))
                    except Exception:
                        pass
    except Exception:
        pass

    # step = Geschwindigkeit [mm/s] / Frequenz [Hz]
    if speed_mm_per_s is not None and freq_hz:
        return float(speed_mm_per_s / freq_hz)

    return None  # Schrittweite konnte nicht ermittelt werden


def points_per_meter(step_mm: float) -> int:
    """Berechnet die Anzahl Datenpunkte pro Meter.

    Args:
        step_mm: Messschrittweite in Millimetern.

    Returns:
        Anzahl Punkte pro Meter (gerundet), oder 0 bei ungültigem Input.

    Beispiel:
        ``step_mm=0.1`` → ``10000`` Punkte/Meter
        ``step_mm=1.0`` → ``1000`` Punkte/Meter
    """
    if not step_mm or step_mm <= 0:
        return 0
    return int(round(1000.0 / float(step_mm)))
