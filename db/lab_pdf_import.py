# db/lab_pdf_import.py
"""Statimat / Itemat PDF import - Qt-free, shared by Show Experiment
(ui/screen_show_experiment_pdf_import.py keeps the PDF picker, progress
dialogs and the result message) and the web app.

Moved out of statimat_import_impl / itemat_import_impl on 2026-11-13
without behaviour change (same mapping, same SQL, change history as before).
Only PDFs attached to the series are offered (db/series_attachments.list_pdfs).

Two steps per PDF, so the web can show what would be written first:

    targets = statimat_targets()
    prop = propose_statimat(series_id, pdf_path, targets)   # parse + match trials, no writes
    write_statimat(prop, targets, log, stats)               # upserts, change entries into log

    cols = itemat_columns()
    header, records = parse_itemat(pdf_path)
    prop = propose_itemat(series_id, pdf_path, records)
    write_itemat(prop, cols, user, log, stats)

or everything like the desktop: import_statimat(...) / import_itemat(...)
-> {"imported", "skipped", "errors"}; import_message() builds the text.

Statimat mapping (Gerät decides the table):
    STATIMAT DS -> tbllaborstatimatds, STATIMAT M -> tbllaborstatimatm (+ Titer both)
    Dehnung -X-/-CV- -> Elongation/ElongationCV, Festigkeit -X-/-CV- ->
    Tenacity/TenacityCV, Feinheit -X- -> tbllabortiter.Titer
    PDF spool number -> trial with Versuchsnummer = number (else ID = number) in the series.
Itemat mapping (tblLaborItematLab), PDF page -> trial number:
    Knoten/m + Var.-Koeff. -> FPm + FPmCV @ Tension 0.0 (inserted if missing)
    Stab.-Faktor col 2..5 -> Stability @ 0.3/0.6/1.0/1.3 (only existing rows),
    FPm there = Knoten/m_0 * Stability / 100.
"""
from __future__ import annotations

import datetime
import logging
import os
import sys
import tempfile
from typing import Any, Callable, Dict, List, Optional, Sequence

from db.connection import execute, get_connection, new_global_id
from db.series_tables import get_columns_map, table_exists
from ui.text_normalize import resolve_field

ITEMAT_TABLE = "tblLaborItematLab"
FEATURE_STATIMAT_IMPORT = 1   # tblFeatureUsage.FeatureID
FEATURE_ITEMAT_IMPORT = 5


def can_import(user: Any) -> bool:
    """Write access (access level >= 2): Show Experiment disables the import
    buttons for read-only users (_sync_save_button_access, "Write access
    required"). Uploading attachments stays open to everybody."""
    from db.series_actions import access_level
    return access_level(user) >= 2


def _user_id(user: Any) -> Any:
    return user.get("id") if user else None


def import_message(head: str, count_label: str, imported: int, skipped: Sequence[str],
                   errors: Sequence[str]) -> str:
    msg = f"{head}\n\n{count_label}: {imported}"
    if skipped:
        msg += "\n\nSkipped:\n" + "\n".join(skipped[:50])
        if len(skipped) > 50:
            msg += f"\n... ({len(skipped) - 50} weitere)"
    if errors:
        msg += "\n\nErrors:\n" + "\n".join(errors[:50])
        if len(errors) > 50:
            msg += f"\n... ({len(errors) - 50} weitere)"
    return msg


def _track(feature_id: int, user: Any, series_id: Any) -> None:
    try:
        user_id = _user_id(user)
        if user_id is not None:
            execute(
                "INSERT INTO tblFeatureUsage (FeatureID, UserID, ExtraInfo) VALUES (?, ?, ?)",
                [feature_id, user_id, str(series_id)],
            )
    except Exception:
        pass  # Tracking darf nie den Import-Flow stoeren


# ====================================================================== Statimat

def statimat_targets() -> Dict[str, Any]:
    """Target tables and columns (same logic as the tabs), resolved once."""
    stat_m_table = None
    for _cand in ("tbllaborstatimatm", "tblLaborStatimat", "tbllaborstatimat"):
        if table_exists(_cand):
            stat_m_table = _cand
            break

    stat_ds_table = None
    for _cand in ("tbllaborstatimatds", "tblLaborStatimatDS"):
        if table_exists(_cand):
            stat_ds_table = _cand
            break

    titer_table = None
    for _cand in ("tbllabortiter", "tbltiter", "tblLaborTiter"):
        if table_exists(_cand):
            titer_table = _cand
            break

    # Resolve columns once
    def _resolve_stat_cols(table_name: str):
        cols = get_columns_map(table_name)
        col_elong = resolve_field(["Elongation (%)", "Elongation%", "Elongation"], cols)
        col_elong_cv = resolve_field(["Elongation CV (%)", "ElongationCV%", "ElongationCV"], cols)
        col_ten = resolve_field(["Tenacity (cN/dtex)", "Tenacity", "Tenacity(cN/dtex)"], cols)
        col_ten_cv = resolve_field(["Tenacity CV (%)", "TenacityCV%", "TenacityCV"], cols)
        return col_elong, col_elong_cv, col_ten, col_ten_cv

    stat_m_cols = _resolve_stat_cols(stat_m_table) if stat_m_table else (None, None, None, None)
    stat_ds_cols = _resolve_stat_cols(stat_ds_table) if stat_ds_table else (None, None, None, None)

    titer_col = None
    if titer_table:
        tcols = get_columns_map(titer_table)
        titer_col = resolve_field(["Titer (dtex)", "Titer"], tcols)
    return {"stat_m_table": stat_m_table, "stat_ds_table": stat_ds_table, "titer_table": titer_table,
            "stat_m_cols": stat_m_cols, "stat_ds_cols": stat_ds_cols, "titer_col": titer_col}


def _trial_id_for_spool(cur, sid: Any, spool_no: int) -> Optional[int]:
    """TrialID for a spool number within this TrialSeries."""
    # 1) try Versuchsnummer = spool_no (common in TrippleT)
    try:
        cur.execute(
            "SELECT ID FROM tblTrial WHERE TrialSeriesID = ? AND Versuchsnummer = ? LIMIT 1",
            (sid, spool_no),
        )
        row = cur.fetchone()
        if row and row[0] is not None:
            return int(row[0])
    except Exception:
        pass

    # 2) try ID = spool_no but ensure it belongs to this TrialSeries
    try:
        cur.execute(
            "SELECT ID FROM tblTrial WHERE TrialSeriesID = ? AND ID = ? LIMIT 1",
            (sid, spool_no),
        )
        row = cur.fetchone()
        if row and row[0] is not None:
            return int(row[0])
    except Exception:
        pass

    return None


def _log_device(pdf_path: str, geraet: str, device_raw: str) -> None:
    # Debug: print to terminal (if one exists) and always log to %TEMP%
    try:
        msg = f"[STATIMAT IMPORT] {os.path.basename(pdf_path)} | device={geraet!r} raw={device_raw!r}"
        sys.stdout.flush()
    except Exception:
        msg = ""
    try:
        log_path = os.path.join(tempfile.gettempdir(), 'tripplet_statimat_import.log')
        logger = logging.getLogger('tripplet.statimat_import')
        if not any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', '').endswith(
                'tripplet_statimat_import.log') for h in logger.handlers):
            fh = logging.FileHandler(log_path, encoding='utf-8')
            fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
            logger.addHandler(fh)
            logger.setLevel(logging.INFO)
        logger.info('%s', msg)
    except Exception:
        pass


def propose_statimat(series_id: Any, pdf_path: str, targets: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Parse one STATIMAT PDF and match its spools to trials - nothing is
    written. Raises on parser errors. Returns {"pdf", "device", "table",
    "cols" (elong, elong_cv, ten, ten_cv), "rows": [{"spool_no", "trial_id",
    "elongation", "elongation_cv", "tenacity", "tenacity_cv", "titer"}],
    "skipped": [message]}; no "table" = the whole PDF is skipped."""
    from ui.widgets.statimat_pdf_parser import parse_statimat_pdf
    t = targets or statimat_targets()
    base = os.path.basename(pdf_path)
    out: Dict[str, Any] = {"pdf": pdf_path, "device": None, "table": None, "cols": None,
                           "rows": [], "skipped": []}
    header, pages = parse_statimat_pdf(pdf_path)
    geraet = (header.get('device') or '').strip()
    device_raw = (header.get('device_raw') or '').strip()
    _log_device(pdf_path, geraet, device_raw)

    # Enforce EXACT device detection
    if geraet not in ('STATIMAT DS', 'STATIMAT M'):
        out["skipped"].append(f"{base}: Unknown device '{geraet}' (raw='{device_raw}')")
        return out
    geraet = (header.get("device") or "").strip()
    # Gerät ist canonical aus Parser: 'STATIMAT DS' oder 'STATIMAT M'
    if geraet not in ('STATIMAT DS', 'STATIMAT M'):
        out["skipped"].append(f"{base}: Unknown device '{geraet}'")
        return out
    out["device"] = geraet

    is_ds = (geraet == 'STATIMAT DS')
    is_m = (geraet == 'STATIMAT M')
    if is_ds and not t["stat_ds_table"]:
        out["skipped"].append(f"{base}: Statimat DS table not found.")
        return out
    if is_m and not t["stat_m_table"]:
        out["skipped"].append(f"{base}: Statimat M table not found.")
        return out

    target_table = t["stat_ds_table"] if is_ds else t["stat_m_table"]
    cols = (t["stat_ds_cols"] if is_ds else t["stat_m_cols"])

    if not all([target_table, *cols]):
        out["skipped"].append(f"{base}: Could not resolve columns (schema).")
        return out
    out["table"], out["cols"] = target_table, cols

    with get_connection() as cn:
        cur = cn.cursor()
        for pr in pages:
            spool_no = pr.get("spool_no")
            if not spool_no:
                continue
            trial_id = _trial_id_for_spool(cur, series_id, int(spool_no))
            if not trial_id:
                out["skipped"].append(f"{base} / spool {spool_no}: no matching trial found.")
                continue
            out["rows"].append({
                "spool_no": spool_no, "trial_id": trial_id,
                "elongation": pr.get("dehnung_x"), "elongation_cv": pr.get("dehnung_cv"),
                "tenacity": pr.get("festigkeit_x"), "tenacity_cv": pr.get("festigkeit_cv"),
                "titer": pr.get("feinheit_x"),
            })
    return out


def write_statimat(proposal: Dict[str, Any], targets: Dict[str, Any], log: List[Dict[str, Any]],
                   stats: Dict[str, int]) -> None:
    """Upserts the proposed rows (statimat table + titer); change history
    entries go into `log`, stats["imported"] counts written spools (also
    the ones before an error). Raises on DB errors."""
    from db import change_log as _chlog
    target_table = proposal.get("table")
    if not target_table or not proposal.get("rows"):
        return
    col_elong, col_elong_cv, col_ten, col_ten_cv = proposal["cols"]
    titer_table, titer_col = targets.get("titer_table"), targets.get("titer_col")
    with get_connection() as cn:
        cur = cn.cursor()
        for pr in proposal["rows"]:
            trial_id = pr["trial_id"]
            # Upsert statimat row
            cur.execute(
                f"SELECT ID FROM [{target_table}] WHERE TrialID = ? LIMIT 1",
                (trial_id,),
            )
            row = cur.fetchone()
            elong_x = pr.get("elongation")
            elong_cv = pr.get("elongation_cv")
            ten_x = pr.get("tenacity")
            ten_cv = pr.get("tenacity_cv")

            _after = {col_elong: elong_x, col_elong_cv: elong_cv, col_ten: ten_x, col_ten_cv: ten_cv}
            if row and row[0] is not None:
                rec_id = row[0]
                _before = _chlog.row_before(cur, target_table, rec_id, list(_after))
                cur.execute(
                    f"UPDATE [{target_table}] SET "
                    f"[{col_elong}]=?, [{col_elong_cv}]=?, [{col_ten}]=?, [{col_ten_cv}]=? "
                    f"WHERE ID=?",
                    (elong_x, elong_cv, ten_x, ten_cv, rec_id),
                )
                log.extend(_chlog.upsert_entries(target_table, rec_id, _before, _after, trial_id))
            else:
                # try insert with GlobalID if present
                cols_map = get_columns_map(target_table)
                has_gid = any(k.lower() == "globalid" for k in cols_map.keys())
                if has_gid:
                    cur.execute(
                        f"INSERT INTO [{target_table}] ([TrialID],[{col_elong}],[{col_elong_cv}],[{col_ten}],[{col_ten_cv}],[GlobalID]) "
                        f"VALUES (?,?,?,?,?,?)",
                        (trial_id, elong_x, elong_cv, ten_x, ten_cv, new_global_id()),
                    )
                else:
                    cur.execute(
                        f"INSERT INTO [{target_table}] ([TrialID],[{col_elong}],[{col_elong_cv}],[{col_ten}],[{col_ten_cv}]) "
                        f"VALUES (?,?,?,?,?)",
                        (trial_id, elong_x, elong_cv, ten_x, ten_cv),
                    )
                log.extend(_chlog.upsert_entries(target_table, cur.lastrowid, {}, _after, trial_id))

            # DS + M: also write titer
            if titer_table and titer_col:
                titer_x = pr.get("titer")
                if titer_x is not None:
                    cur.execute(
                        f"SELECT ID FROM [{titer_table}] WHERE TrialID=? LIMIT 1",
                        (trial_id,),
                    )
                    tr = cur.fetchone()
                    if tr and tr[0] is not None:
                        _tb = _chlog.row_before(cur, titer_table, tr[0], [titer_col])
                        cur.execute(
                            f"UPDATE [{titer_table}] SET [{titer_col}]=? WHERE ID=?",
                            (titer_x, tr[0]),
                        )
                        log.extend(_chlog.upsert_entries(titer_table, tr[0], _tb,
                                                         {titer_col: titer_x}, trial_id))
                    else:
                        tcols = get_columns_map(titer_table)
                        has_gid2 = any(k.lower() == "globalid" for k in tcols.keys())
                        if has_gid2:
                            cur.execute(
                                f"INSERT INTO [{titer_table}] ([TrialID],[{titer_col}],[GlobalID]) VALUES (?,?,?)",
                                (trial_id, titer_x, new_global_id()),
                            )
                        else:
                            cur.execute(
                                f"INSERT INTO [{titer_table}] ([TrialID],[{titer_col}]) VALUES (?,?)",
                                (trial_id, titer_x),
                            )
                        log.extend(_chlog.upsert_entries(titer_table, cur.lastrowid, {},
                                                         {titer_col: titer_x}, trial_id))

            stats["imported"] = stats.get("imported", 0) + 1


def import_statimat(series_id: Any, pdf_paths: Sequence[str], user: Any = None,
                    on_pdf_start: Optional[Callable[[int, str], bool]] = None,
                    on_pdf_end: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
    """Whole Statimat import of the chosen (attached!) PDFs: per PDF propose +
    write, errors per PDF collected; then change history and feature
    tracking. on_pdf_start(index, path) -> False = cancel (desktop progress
    dialog), on_pdf_end(index) after each PDF."""
    from db import change_log as _chlog
    _log: list = []  # change history entries, written after the import
    targets = statimat_targets()
    stats = {"imported": 0}
    skipped: List[str] = []
    errors: List[str] = []
    for pdf_idx, pdf_path in enumerate(pdf_paths):
        if on_pdf_start is not None and not on_pdf_start(pdf_idx, pdf_path):
            break
        try:
            prop = propose_statimat(series_id, pdf_path, targets)
            skipped.extend(prop["skipped"])
            write_statimat(prop, targets, _log, stats)
        except Exception as e:
            errors.append(f"{os.path.basename(pdf_path)}: {e}")
        finally:
            if on_pdf_end is not None:
                try:
                    on_pdf_end(pdf_idx)
                except Exception:
                    pass

    # change history (db/change_log.py)
    _chlog.log_changes(_log, series_id=series_id, source="pdf import", user_id=_user_id(user))

    # Feature-Tracking: nur wenn mindestens eine Spule aktualisiert wurde
    if stats["imported"] >= 1:
        _track(FEATURE_STATIMAT_IMPORT, user, series_id)
    return {"imported": stats["imported"], "skipped": skipped, "errors": errors}


# ====================================================================== Itemat

def itemat_columns() -> Optional[Dict[str, Any]]:
    """Columns of tblLaborItematLab; None = a required one (Tension, FPm,
    Stability) is missing (the desktop shows `itemat_columns_raw()` then)."""
    c = itemat_columns_raw()
    if not all([c["tension"], c["fpm"], c["stability"]]):
        return None
    return c


def itemat_columns_raw() -> Dict[str, Any]:
    cols = get_columns_map(ITEMAT_TABLE)
    return {"tension": cols.get("tension"), "fpm": cols.get("fpm"), "fpmcv": cols.get("fpmcv"),
            "stability": cols.get("stability"), "user": cols.get("user"), "timestamp": cols.get("timestamp")}


def parse_itemat(pdf_path: str, progress_callback=None):
    """(header, records) of one Itemat Lab PDF (ui/widgets/itemat_pdf_parser,
    OCR fallback). progress_callback(cur, total) may raise InterruptedError."""
    from ui.widgets.itemat_pdf_parser import parse_itemat_pdf
    return parse_itemat_pdf(pdf_path, progress_callback=progress_callback)


def propose_itemat(series_id: Any, pdf_path: str, records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Match the parsed pages to trials (page's trial number -> Versuchsnummer)
    - nothing is written. {"pdf", "rows": [{"page", "versuch_nr", "trial_id",
    "knoten_m", "var_koeff", "stability"}], "skipped": [message]}."""
    base = os.path.basename(pdf_path)
    out: Dict[str, Any] = {"pdf": pdf_path, "rows": [], "skipped": []}
    with get_connection() as cn:
        cur = cn.cursor()
        for rec in records:
            versuch_nr = rec.get("versuch_nr")
            if not versuch_nr:
                out["skipped"].append(
                    f"{base} / page {rec['page']}: "
                    f"trial number could not be determined."
                )
                continue

            # Trial-ID via Versuchsnummer
            cur.execute(
                "SELECT ID FROM tblTrial "
                "WHERE TrialSeriesID = ? AND Versuchsnummer = ? LIMIT 1",
                (series_id, versuch_nr),
            )
            row = cur.fetchone()
            if not row or row[0] is None:
                out["skipped"].append(
                    f"{base} / V{versuch_nr}: "
                    f"no matching trial found."
                )
                continue
            out["rows"].append({
                "page": rec.get("page"), "versuch_nr": versuch_nr, "trial_id": int(row[0]),
                "knoten_m": rec.get("knoten_m"), "var_koeff": rec.get("var_koeff"),
                "stability": rec.get("stability") or [None, None, None, None],
            })
    return out


def write_itemat(proposal: Dict[str, Any], cols: Dict[str, Any], user: Any,
                 log: List[Dict[str, Any]], stats: Dict[str, int]) -> None:
    """Upserts the proposed rows: Tension 0.0 (inserted if missing) and the
    existing rows at 0.3/0.6/1.0/1.3. Raises on DB errors."""
    from db import change_log as _chlog
    from ui.widgets.itemat_pdf_parser import DB_TENSIONS as ITEMAT_DB_TENSIONS
    itemat_table = ITEMAT_TABLE
    col_tension, col_fpm, col_fpmcv = cols["tension"], cols["fpm"], cols["fpmcv"]
    col_stability, col_user, col_ts = cols["stability"], cols["user"], cols["timestamp"]
    current_user = _user_id(user)

    with get_connection() as cn:
        cur = cn.cursor()
        for rec in proposal["rows"]:
            trial_id = rec["trial_id"]
            knoten_m_0 = rec.get("knoten_m")
            var_koeff = rec.get("var_koeff")
            stability = rec.get("stability") or [None, None, None, None]

            # Bestehende Datensätze für diesen Trial laden
            cur.execute(
                f"SELECT ID, [{col_tension}] FROM [{itemat_table}] "
                f"WHERE TrialID = ?",
                (trial_id,),
            )
            existing = {
                round(float(str(r[1]).replace(",", ".")), 2): r[0]
                for r in (cur.fetchall() or [])
                if r[1] is not None
            }

            def _upsert(tension_val, fpm_val, fpmcv_val, stab_val):
                t_key = round(float(tension_val), 2)
                rec_id = existing.get(t_key)

                set_parts = [f"[{col_tension}]=?"]
                vals = [tension_val]

                if fpm_val is not None:
                    set_parts.append(f"[{col_fpm}]=?")
                    vals.append(fpm_val)
                if fpmcv_val is not None and col_fpmcv:
                    set_parts.append(f"[{col_fpmcv}]=?")
                    vals.append(fpmcv_val)
                if stab_val is not None:
                    set_parts.append(f"[{col_stability}]=?")
                    vals.append(stab_val)
                if col_user:
                    set_parts.append(f"[{col_user}]=?")
                    vals.append(current_user)
                if col_ts:
                    set_parts.append(f"[{col_ts}]=NOW()")

                _after = {col_fpm: fpm_val, col_stability: stab_val}
                if fpmcv_val is not None and col_fpmcv:
                    _after[col_fpmcv] = fpmcv_val
                _after = {k: v for k, v in _after.items() if v is not None}
                if rec_id is not None:
                    _before = _chlog.row_before(cur, itemat_table, rec_id, list(_after))
                    cur.execute(
                        f"UPDATE [{itemat_table}] SET "
                        + ", ".join(set_parts)
                        + " WHERE ID=?",
                        vals + [rec_id],
                    )
                    log.extend(_chlog.upsert_entries(itemat_table, rec_id, _before, _after, trial_id))
                else:
                    col_names = [f"[TrialID]", f"[{col_tension}]"]
                    ins_vals = [trial_id, tension_val]
                    if fpm_val is not None:
                        col_names.append(f"[{col_fpm}]")
                        ins_vals.append(fpm_val)
                    if fpmcv_val is not None and col_fpmcv:
                        col_names.append(f"[{col_fpmcv}]")
                        ins_vals.append(fpmcv_val)
                    if stab_val is not None:
                        col_names.append(f"[{col_stability}]")
                        ins_vals.append(stab_val)
                    if col_user:
                        col_names.append(f"[{col_user}]")
                        ins_vals.append(current_user)
                    if col_ts:
                        col_names.append(f"[{col_ts}]")
                        ins_vals.append(datetime.datetime.now())
                    placeholders = ", ".join(["?"] * len(ins_vals))
                    cur.execute(
                        f"INSERT INTO [{itemat_table}] "
                        f"({', '.join(col_names)}) "
                        f"VALUES ({placeholders})",
                        ins_vals,
                    )
                    log.extend(_chlog.upsert_entries(itemat_table, cur.lastrowid, {}, _after, trial_id))

            # Tension 0.0: FPm = knoten_m_0, CV = var_koeff, Stability = NULL
            # 0.0 darf immer inserted werden (Baseline-Row)
            _upsert(0.0, knoten_m_0, var_koeff, None)

            # Tensions > 0.0: NUR updaten wenn die Row bereits existiert in der DB.
            # Kein INSERT – neue Tensions dürfen nicht automatisch angelegt werden.
            for idx, t in enumerate(ITEMAT_DB_TENSIONS[1:]):  # [0.3, 0.6, 1.0, 1.3]
                t_key = round(float(t), 2)
                if t_key not in existing:
                    continue  # Row existiert nicht → überspringen
                stab = stability[idx] if idx < len(stability) else None
                if stab is not None and knoten_m_0 is not None:
                    fpm = round(knoten_m_0 * stab / 100.0, 4)
                else:
                    fpm = None
                _upsert(t, fpm, None, stab)

            stats["imported"] = stats.get("imported", 0) + 1


def import_itemat(series_id: Any, pdf_paths: Sequence[str], user: Any = None,
                  cols: Optional[Dict[str, Any]] = None,
                  progress_for: Optional[Callable[[str], Any]] = None) -> Dict[str, Any]:
    """Whole Itemat import of the chosen (attached!) PDFs. Parser errors /
    cancel per PDF are collected; DB errors propagate (as before - then no
    change history is written). progress_for(path) -> (callback(cur, total),
    done()) for the desktop progress dialog."""
    from db import change_log as _chlog
    _log: list = []  # change history entries, written after the import
    cols = cols or itemat_columns()
    if cols is None:
        raise RuntimeError("Could not resolve the required columns of tblLaborItematLab.")
    stats = {"imported": 0}
    skipped: List[str] = []
    errors: List[str] = []
    for pdf_path in pdf_paths:
        try:
            cb, done = progress_for(pdf_path) if progress_for is not None else (None, None)
            header, records = parse_itemat(pdf_path, progress_callback=cb)
            if done is not None:
                done()
        except InterruptedError:
            skipped.append(f"{os.path.basename(pdf_path)}: cancelled.")
            continue
        except Exception as e:
            errors.append(f"{os.path.basename(pdf_path)}: parser error: {e}")
            continue

        prop = propose_itemat(series_id, pdf_path, records)
        skipped.extend(prop["skipped"])
        write_itemat(prop, cols, user, _log, stats)

    # change history (db/change_log.py)
    _chlog.log_changes(_log, series_id=series_id, source="pdf import", user_id=_user_id(user))

    # Feature-Tracking (stealth)
    if stats["imported"] >= 1:
        _track(FEATURE_ITEMAT_IMPORT, user, series_id)
    return {"imported": stats["imported"], "skipped": skipped, "errors": errors}


# ====================================================================== one import for both (2026-11-16)
# Nutzerwunsch: one "PDF import" button in Show Experiment - the kind of every PDF is recognised by itself,
# Statimat and Itemat PDFs can be imported in one go.

KIND_STATIMAT, KIND_ITEMAT = "statimat", "itemat"


def detect_kind(pdf_path: str, pages: int = 1, name: str = "") -> Optional[str]:
    """"statimat" / "itemat" / None (unknown) from the first page: Statimat reports always carry "STATIMAT" in
    their text layer (the parser checks the same), Itemat Lab reports are scans without a text layer (or, with an
    OCR layer, say Itemat / Enka). Any other text = not a lab report we import.
    PyMuPDF first (~0.1 s per file; pdfplumber needs 4-12 s on the graphics-heavy Statimat reports).
    name = original file name (the stored one is a hash): a scan WITHOUT text whose name says "Statimat" stays
    Statimat (the Statimat import then skips it with "unknown device") instead of going to the Itemat OCR."""
    text: Optional[str] = None
    try:
        import fitz
        doc = fitz.open(pdf_path)
        try:
            text = "".join((doc[i].get_text("text") or "") + "\n" for i in range(min(doc.page_count, pages)))
        finally:
            doc.close()
    except Exception:
        text = None
    if text is None:                        # PyMuPDF missing or failed -> pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                text = "".join((p.extract_text() or "") + "\n" for p in pdf.pages[:pages])
        except Exception:
            return None                      # not readable at all
    up = text.upper()
    if "STATIMAT" in up:
        return KIND_STATIMAT
    if "ITEMAT" in up or "ENKA" in up:
        return KIND_ITEMAT
    if not text.strip():                    # scan without text layer
        hint = (name or os.path.basename(pdf_path)).upper()
        return KIND_STATIMAT if "STATIMAT" in hint else KIND_ITEMAT
    return None


def detect_kinds(pdf_paths: Sequence[str], names: Optional[Dict[str, str]] = None) -> Dict[str, Optional[str]]:
    return {p: detect_kind(p, name=(names or {}).get(p, "")) for p in pdf_paths}


def import_auto(series_id: Any, pdf_paths: Sequence[str], user: Any = None,
                kinds: Optional[Dict[str, Optional[str]]] = None,
                on_pdf_start: Optional[Callable[[int, str], bool]] = None,
                on_pdf_end: Optional[Callable[[int], None]] = None,
                progress_for: Optional[Callable[[str], Any]] = None) -> Dict[str, Any]:
    """Imports the chosen (attached!) PDFs by their kind: Statimat ones with import_statimat, Itemat ones with
    import_itemat, unknown ones are listed. Returns {"statimat": result | None, "itemat": result | None,
    "unknown": [file name], "message": text for the user}. kinds = already detected kinds (else detected here)."""
    kinds = dict(kinds or {})
    for p in pdf_paths:
        if p not in kinds:
            kinds[p] = detect_kind(p)
    stat = [p for p in pdf_paths if kinds.get(p) == KIND_STATIMAT]
    item = [p for p in pdf_paths if kinds.get(p) == KIND_ITEMAT]
    unknown = [os.path.basename(p) for p in pdf_paths if kinds.get(p) not in (KIND_STATIMAT, KIND_ITEMAT)]
    out: Dict[str, Any] = {"statimat": None, "itemat": None, "unknown": unknown}
    parts: List[str] = []
    if stat:
        out["statimat"] = r = import_statimat(series_id, stat, user, on_pdf_start=on_pdf_start, on_pdf_end=on_pdf_end)
        parts.append(import_message(f"Statimat ({len(stat)} PDF)", "Imported spools", r["imported"], r["skipped"],
                                    r["errors"]))
    if item:
        cols = itemat_columns()
        if cols is None:
            parts.append("Itemat: the required columns of tblLaborItematLab could not be resolved - not imported.")
        else:
            try:
                out["itemat"] = r = import_itemat(series_id, item, user, cols=cols, progress_for=progress_for)
                parts.append(import_message(f"Itemat ({len(item)} PDF)", "Imported trials", r["imported"],
                                            r["skipped"], r["errors"]))
            except Exception as e:     # DB errors propagate from import_itemat
                parts.append(f"Itemat: the import failed: {e}")
    if unknown:
        parts.append("Not a Statimat or Itemat report (not imported):\n" + "\n".join(unknown[:50]))
    out["message"] = "\n\n".join(parts) if parts else "Nothing to import."
    return out
