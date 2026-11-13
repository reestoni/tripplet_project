# db/yarn_spools.py
"""Spools of a yarn in stock - Qt-free, shared by the desktop (spool picker,
yarn locations, Create Experiment) and the web app.

Moved on 2026-11-13 without behaviour change from ui/widgets/spool_picker.py
(get_available_spools, spool_label) and ui/widgets/yarn_locations.py
(StockSummary, load_stock_summary); both modules re-export the names.

    load_stock_summary(yarn_ids) -> {yarn_id: StockSummary(spools, kg, locations)}
        only yarns with at least one spool 'in stock' (= the green spool symbol)
    get_available_spools(yarn_id, include_spool_id=None) -> [{"ID", "Charge",
        "WeightKg", "Location", "Status"}] spools of the yarn in stock with
        weight > 0 (plus include_spool_id, even if discarded), by charge
    spool_label(row) -> "#12 — Batch A1 — 4.20 kg — E12" (+ "  (discarded)")
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set

from db.connection import fetch_all, table_exists


@dataclass
class StockSummary:
    spools: int
    kg: float
    locations: int


def load_stock_summary(yarn_ids: Iterable[int]) -> Dict[int, StockSummary]:
    """{yarn_id: StockSummary} for yarns with at least one spool in stock.
    Yarns without stock are missing from the dict. Best effort: {} on error."""
    ids = sorted({int(y) for y in yarn_ids if y is not None})
    if not ids or not table_exists("tblYarnSpool"):
        return {}
    ph = ",".join(["?"] * len(ids))
    try:
        rows = fetch_all(
            f"SELECT YarnID, COUNT(*) AS n, SUM(WeightKg) AS kg, "
            f"COUNT(DISTINCT Location) AS locs FROM tblYarnSpool "
            f"WHERE YarnID IN ({ph}) AND Status = 'in stock' GROUP BY YarnID",
            ids,
        )
    except Exception:
        return {}
    out: Dict[int, StockSummary] = {}
    for r in rows:
        n = int(r.get("n") or 0)
        if n <= 0 or r.get("YarnID") is None:
            continue
        out[int(r["YarnID"])] = StockSummary(
            spools=n, kg=float(r.get("kg") or 0.0), locations=int(r.get("locs") or 0))
    return out


def get_available_spools(yarn_id: int, include_spool_id: Optional[int] = None) -> List[Dict]:
    """Spulen desselben Garns, die am Lager sind (Status='in stock', WeightKg>0).
    `include_spool_id` wird immer mit zurückgegeben, auch falls nicht mehr
    am Lager (z.B. bestehende Zuordnung, die man sich beim Bearbeiten
    weiterhin anschauen koennen soll)."""
    if not table_exists("tblYarnSpool") or not yarn_id:
        return []
    rows = fetch_all(
        "SELECT [ID], [Charge], [WeightKg], [Location], [Status] "
        "FROM tblYarnSpool WHERE [YarnID] = ? AND "
        "(([Status] = 'in stock' AND [WeightKg] > 0)" +
        (" OR [ID] = ?" if include_spool_id else "") + ") "
        "ORDER BY [Charge], [ID]",
        [yarn_id] + ([include_spool_id] if include_spool_id else []),
    )
    return rows


def spool_label(row: Dict) -> str:
    charge = row.get("Charge") or "–"
    weight = row.get("WeightKg")
    loc = row.get("Location") or "–"
    w_txt = f"{float(weight):.2f} kg" if weight is not None else "?"
    suffix = "" if row.get("Status") == "in stock" else "  (discarded)"
    return f"#{row['ID']} — Batch {charge} — {w_txt} — {loc}{suffix}"


# ── stock locations (ui/widgets/yarn_locations.YarnLocationsDialog, web stock dialog) ──
def location_sort_key(loc: Optional[str]) -> List[object]:
    """Natural sort: E2 before E12, empty locations last."""
    s = (loc or "").strip().upper()
    if not s:
        return [1]
    return [0] + [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s) if t]


# tube colours are free text, often two-tone ("Black/Yellow", "white / green")
# and with lab spellings - extras on top of yarn_colour.COLOUR_HEX
_TUBE_ALIASES = {"lila": "purple", "blac": "black", "rosa": "pink", "gelb": "yellow",
                 "schwarz": "black", "weiss": "white", "grün": "green", "gruen": "green",
                 "rot": "red", "blau": "blue", "braun": "brown", "grau": "grey"}


def tube_colour_candidates(text: Optional[str]) -> List[List[str]]:
    """Tube colour text ("Black/Yellow", "white / green with print") -> per
    colour part its words (lab spellings mapped, e.g. "lila" -> "purple"); the
    caller takes the first word it knows as a colour (desktop: Qt colour names,
    web: CSS colour names). At most 3 parts."""
    out: List[List[str]] = []
    for part in re.split(r"[/,+&]|\band\b", (text or "").lower()):
        words = [_TUBE_ALIASES.get(w, w) for w in part.split()]
        if words:
            out.append(words)
    return out[:3]


def load_spools_in_stock(yarn_id: int) -> List[Dict]:
    """All spools of the yarn in stock, sorted by location. 'Colour' (tube
    colour) is optional in older databases."""
    if not table_exists("tblYarnSpool"):
        return []
    base = "SELECT ID, Charge, WeightKg, Location, ReceivedDate{c} FROM tblYarnSpool " \
           "WHERE YarnID = ? AND Status = 'in stock'"
    try:
        rows = fetch_all(base.format(c=", Colour"), [int(yarn_id)])
    except Exception:
        rows = fetch_all(base.format(c=""), [int(yarn_id)])
    rows.sort(key=lambda r: (location_sort_key(r.get("Location")), str(r.get("Charge") or ""),
                             int(r.get("ID") or 0)))
    return rows


def load_series_spool_ids(series_pk) -> Set[int]:
    """Spools assigned to trials of the series (Machine Data -> row 'Spool')."""
    if not series_pk:
        return set()
    try:
        rows = fetch_all(
            "SELECT DISTINCT ts.SpoolID FROM tblTrialSettings ts "
            "JOIN tblTrial t ON t.ID = ts.TrialID "
            "WHERE t.TrialSeriesID = ? AND ts.SpoolID IS NOT NULL",
            [series_pk])
    except Exception:
        return set()
    out: Set[int] = set()
    for r in rows:
        try:
            if int(r["SpoolID"] or 0) > 0:
                out.add(int(r["SpoolID"]))
        except Exception:
            pass
    return out
