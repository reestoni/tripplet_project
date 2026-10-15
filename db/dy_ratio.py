# db/dy_ratio.py
"""D/Y ratio = T2 Tension / T1 Tension of a DTY ply, Nutzerwunsch 2026-10-15.

Stored per ply in tblTrialSettings.DYRatio (T1/T2 are ply values, too). The
old tblTrial.DYRatio column is an Access leftover nothing fills any more and
stays untouched.

Kept current by the application, not by a DB trigger (prod runs with binary
logging and without SUPER, so CREATE TRIGGER is not allowed there):

- PivotEditModel.save_dirty() recomputes the plies whose T1/T2 it wrote,
- Create Experiment / Add Trials put the value into their INSERTs
  (append_ratio_column()),
- copied ply rows carry T1, T2 and DYRatio over unchanged.

Show Experiment calculates the row live from the T1/T2 cells (ratio_text()),
so the display is current before saving, too. Everything here degrades
gracefully when the column is missing (e.g. an older offline snapshot).
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Iterable, List, Optional

COLUMN = "DYRatio"

ADD_COLUMN_SQL = "ALTER TABLE tbltrialsettings ADD COLUMN DYRatio DECIMAL(6,2) NULL DEFAULT NULL"

# Same rounding as ratio_value() (MySQL ROUND on DECIMAL = half up)
_RATIO_SQL = ("CASE WHEN YarnTensionT1 IS NULL OR YarnTensionT2 IS NULL OR YarnTensionT1 = 0 "
              "THEN NULL ELSE ROUND(YarnTensionT2 / YarnTensionT1, 2) END")


def add_column() -> None:
    """Adds tblTrialSettings.DYRatio (no-op if present). Only call
    deliberately - dev/prod only with explicit permission."""
    from db import connection
    if COLUMN.lower() in connection.get_columns_map("tblTrialSettings"):
        return
    connection.execute(ADD_COLUMN_SQL)
    connection._COLUMNS_MAP_CACHE.clear()


def has_column() -> bool:
    try:
        from db.connection import get_columns_map
        cols = get_columns_map("tblTrialSettings")
        return all(c in cols for c in ("dyratio", "yarntensiont1", "yarntensiont2"))
    except Exception:
        return False


def ratio_value(t1: Any, t2: Any) -> Optional[Decimal]:
    """T2/T1 rounded to 2 decimals (half up), None if a value is missing or
    T1 is 0."""
    try:
        a = Decimal(str(t1).strip().replace(",", "."))
        b = Decimal(str(t2).strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None
    if t1 is None or t2 is None or not a.is_finite() or not b.is_finite() or a == 0:
        return None
    return (b / a).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def ratio_text(t1: Any, t2: Any) -> str:
    v = ratio_value(t1, t2)
    return "" if v is None else str(v)


def recompute(settings_ids: Optional[Iterable[Any]] = None) -> int:
    """Recalculates DYRatio from T1/T2 for the given tblTrialSettings IDs, or
    for all rows when settings_ids is None (one-off backfill). Returns the
    number of changed rows; best-effort (0 when the column is missing)."""
    from db.connection import execute
    if not has_column():
        return 0
    if settings_ids is None:
        return execute(
            f"UPDATE tblTrialSettings SET DYRatio = {_RATIO_SQL} "
            f"WHERE NOT (DYRatio <=> {_RATIO_SQL})", [])
    ids: List[int] = sorted({int(i) for i in settings_ids if i is not None})
    n = 0
    for k in range(0, len(ids), 500):
        chunk = ids[k:k + 500]
        ph = ",".join(["?"] * len(chunk))
        n += execute(
            f"UPDATE tblTrialSettings SET DYRatio = {_RATIO_SQL} WHERE ID IN ({ph})", chunk)
    return n


def append_ratio_column(cols: List[str], vals: List[Any], settings_cols_map: dict) -> None:
    """For INSERTs into tblTrialSettings: appends DYRatio computed from the
    T1/T2 values in cols/vals (if both are there and the column exists)."""
    real = settings_cols_map.get("dyratio")
    if not real or any(str(c).lower() == "dyratio" for c in cols):
        return
    by_name = {str(c).lower(): v for c, v in zip(cols, vals)}
    if "yarntensiont1" not in by_name or "yarntensiont2" not in by_name:
        return
    v = ratio_value(by_name["yarntensiont1"], by_name["yarntensiont2"])
    if v is not None:
        cols.append(real)
        vals.append(v)
