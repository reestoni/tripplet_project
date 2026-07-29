"""text_normalize.py - Gemeinsame Text-/Spaltennamen-Normalisierungs-Helfer.

Konsolidiert mehrfach fast identisch implementierte Helfer (_canon, _norm,
resolve_field), die zuvor in vielen ui/screen_*.py-Dateien einzeln definiert
waren (siehe Code-Review-TODO "Duplizierte Spalten-Normalisierungs-Helfer").

Reiner Code-Move ohne Verhaltensaenderung an den Aufrufstellen: jede
Funktion hier wurde 1:1 aus einer der bisherigen Fundstellen uebernommen.
Abweichende Varianten (z.B. main.py._canon ohne None-Guard,
screen_manage_yarn.py._resolve_field mit None-Guard auf `cand`,
screen_yarn_stock.py._resolve_field mit einfacherer Normalisierung) wurden
bewusst NICHT vereinheitlicht, um bestehendes Verhalten an jeder
Aufrufstelle exakt zu erhalten - sie bleiben unveraendert lokal in ihrer
Datei.
"""
from __future__ import annotations

from typing import Dict, List, Optional


def norm(s: str) -> str:
    """Normalisiert einen Spaltennamen (strip + lowercase, Sonderzeichen entfernen)."""
    return (
        (s or "")
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("(", "")
        .replace(")", "")
        .replace("°", "")
        .replace("/", "")
        .replace("-", "")
        .strip()
    )


def resolve_field(cands: List[str], cols_map: Dict[str, str]) -> Optional[str]:
    """Gibt den ersten Kandidaten zurück der in cols_map vorhanden ist."""
    for cand in cands:
        lc = cand.lower()
        if lc in cols_map:
            return cols_map[lc]
    inv = {norm(k): v for k, v in cols_map.items()}
    for cand in cands:
        nk = norm(cand)
        if nk in inv:
            return inv[nk]
    return None


def canon_simple(s: str) -> str:
    """Canonicalize header/keys: strip brackets/spaces, lowercase."""
    return str(s).strip().strip("`[]").replace(" ", "").lower() if s is not None else ""


def canon_with_id_strip(s: str) -> str:
    """canon_simple() plus Entfernen von führendem 'fk_'/'id' und abschließendem 'id'."""
    if s is None:
        return ""
    x = str(s).strip().strip("`[]").replace(" ", "").lower()
    if x.startswith("fk_"):
        x = x[3:]
    if x.startswith("id"):
        x = x[2:]
    if x.endswith("id"):
        x = x[:-2]
    return x
