# db/trial_reference.py
"""Reference samples (customer original spools, golden samples) inside a
TrialSeries, Nutzerwunsch 2026-10-15.

A reference sample is a normal tblTrial row with IsReference = 1 - all lab
tables hang on TrialID, so lab values, retest flags etc. keep working
unchanged. What makes it "not a trial":

- Own number range: new reference samples get NEGATIVE trial numbers
  (-1, -2, ...), so they don't use up a trial number - V1, V2, ... stay
  gapless (next_trial_number() / next_reference_number()). A trial marked
  as reference later keeps its positive number (physical spool labels carry
  it); turned back into a trial, a negative-numbered one gets the next free
  positive number.
- Show Experiment shows it as highlighted "Ref" column(s) first.
- The series report draws its values as horizontal benchmark lines instead
  of data points.
- Every cross-trial analysis excludes it (exclude_references_sql()):
  DTY jet training export, Stats Suite, Smart Chart, Quick Scan, Athena
  advisor, Manage Jets usage. Lab Assistant gets a prompt rule instead.

PDF imports (Statimat/Itemat) match samples by trial number, so they can't
address a negative-numbered reference - its lab values are typed in.
Machine data stays editable on purpose (the customer may tell us hints).

Columns are added manually (like tblUsageLog/tblYarnSpoolLog) via
add_columns(); everything here degrades gracefully when they are missing
(e.g. an older offline snapshot): no column -> no references.
"""
from typing import Any, Optional

IS_REFERENCE_COL = "IsReference"
REFERENCE_NAME_COL = "ReferenceName"
REFERENCE_LABEL = "Ref"

ADD_COLUMNS_SQL = (
    "ALTER TABLE tbltrial "
    "ADD COLUMN IsReference TINYINT(1) NOT NULL DEFAULT 0, "
    "ADD COLUMN ReferenceName VARCHAR(255) NULL DEFAULT NULL"
)


def add_columns() -> None:
    """Adds IsReference/ReferenceName to tblTrial (no-op if present). Only
    call deliberately - dev/prod only with explicit permission."""
    from db.connection import execute, get_columns_map
    if "isreference" in get_columns_map("tblTrial"):
        return
    execute(ADD_COLUMNS_SQL)


def has_reference_columns() -> bool:
    try:
        from db.connection import get_columns_map
        return "isreference" in get_columns_map("tblTrial")
    except Exception:
        return False


def exclude_references_sql(alias: str = "t") -> str:
    """WHERE fragment that keeps only real trials. `alias` is the tblTrial
    alias ("" for none). Falls back to an always-true condition when the
    column doesn't exist, so callers can append it unconditionally."""
    if not has_reference_columns():
        return "1=1"
    prefix = f"{alias}." if alias else ""
    return f"COALESCE({prefix}{IS_REFERENCE_COL}, 0) = 0"


def is_reference_value(value: Any) -> bool:
    try:
        return bool(int(value or 0))
    except (TypeError, ValueError):
        return False


def next_trial_number(max_vno: Any) -> int:
    """Next trial number from MAX(Versuchsnummer) of a series. Clamped at 0,
    so a series holding only (negative) reference samples starts at V1."""
    try:
        return max(int(max_vno), 0) + 1
    except (TypeError, ValueError):
        return 1


def next_reference_number(min_vno: Any) -> int:
    """Next (negative) reference number from MIN(Versuchsnummer): -1, -2, ..."""
    try:
        return min(int(min_vno), 0) - 1
    except (TypeError, ValueError):
        return -1


def reference_label(vno: Any = None) -> str:
    """Column label for a reference sample in Show Experiment - just "Ref"
    (Nutzerwunsch); the name is in the tooltip."""
    return REFERENCE_LABEL


def format_trial_number(vno: Any) -> str:
    """'V<n>' for trials, 'Ref' for negative-numbered reference samples - for
    lists/dialogs that only know the number (no IsReference at hand)."""
    try:
        if int(vno) < 1:
            return REFERENCE_LABEL
    except (TypeError, ValueError):
        pass
    return f"V{vno}"


def reference_tooltip(name: Optional[str], vno: Any = None) -> str:
    name = (name or "").strip()
    head = f"Reference sample: {name}" if name else "Reference sample"
    return f"{head}\n(not a trial - excluded from statistics)"
