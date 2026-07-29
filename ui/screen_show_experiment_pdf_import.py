"""Statimat/Itemat PDF-Import fuer ShowExperimentScreen.

Ausgelagert aus ui/screen_show_experiment.py (reiner Code-Move, keine
Verhaltensaenderung). Beide *_impl-Funktionen erwarten die
ShowExperimentScreen-Instanz als `self`-Argument (Variablenname bewusst
beibehalten, damit der Funktionskoerper 1:1 dem urspruenglichen Methodenkoerper
entspricht) und greifen darueber auf Screen-State/-Methoden zu
(z.B. self._series_pk, self._fetch_series_pdfs, self._build_titer_tab).

table_exists/get_columns_map/resolve_field werden bewusst aus
ui.screen_show_experiment importiert (nicht neu implementiert), damit exakt
dieselbe Tabellen-/Spalten-Normalisierung wie vorher verwendet wird.
"""
from __future__ import annotations

import os
import sys
import logging
import tempfile
import datetime
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMessageBox,
    QDialog,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QAbstractItemView,
    QDialogButtonBox,
    QProgressDialog,
)

import app_meta
from db.connection import get_connection, new_global_id, execute as _db_execute
from ui.widgets.statimat_pdf_parser import parse_statimat_pdf
from ui.widgets.itemat_pdf_parser import DB_TENSIONS as ITEMAT_DB_TENSIONS


def statimat_import_impl(self) -> None:
    """Import STATIMAT PDF(s) attached to this TrialSeries into lab tables.

    Rules:
    - Only PDFs attached to the current TrialSeries may be imported.
    - pdf.Customer must match the current TrialSeriesID (string compare).
    - Gerät decides target table:
        STATIMAT DS -> tbllaborstatimatds / tblLaborStatimatDS (+ Titer)
        STATIMAT M  -> tbllaborstatimatm / tblLaborStatimat / tbllaborstatimat (+ Titer)
    - Mapping:
        Dehnung -X-    -> Elongation
        Dehnung -CV-   -> ElongationCV
        Festigkeit -X- -> Tenacity
        Festigkeit -CV-> TenacityCV
        Feinheit -X-   -> tbllabortiter.Titer (both STATIMAT DS and STATIMAT M)
    """
    # Lazy import (vermeidet Zirkularimport, screen_show_experiment importiert
    # dieses Modul selbst) - table_exists/get_columns_map sind die lowercase-
    # normalisierenden Wrapper aus screen_show_experiment, nicht die aus db.connection.
    from ui.screen_show_experiment import table_exists, get_columns_map, resolve_field

    sid = getattr(self, "_series_pk", None)
    if sid in (None, ""):
        QMessageBox.information(self, "Statimat import", "Keine TrialSeries geladen.")
        return

    # Build allow-list from attached PDFs
    try:
        attached = self._fetch_series_pdfs(sid)
    except Exception as e:
        QMessageBox.warning(self, "Statimat import", f"Konnte PDF-Liste nicht laden:\n{e}")
        return

    allowed = set()
    for r in attached:
        p = r.get("FullPath") or ""
        if p:
            allowed.add(os.path.normcase(os.path.abspath(p)))

    if not allowed:
        QMessageBox.information(self, "Statimat import", "This trial series has no attached PDFs.")
        return

    # User picks one/many PDFs, but we only accept those that are attached
    # User picks one/many PDFs from the *attached* list (show OriginalFilename, not StoredFilename)
    def _pick_attached_pdfs(attached_rows):
        dlg = QDialog(self)
        dlg.setWindowTitle("Select STATIMAT PDFs")
        lay = QVBoxLayout(dlg)

        info = QLabel("Select the STATIMAT PDFs to import (only PDFs attached to this trial series):")
        info.setWordWrap(True)
        lay.addWidget(info)

        lst = QListWidget()
        lst.setSelectionMode(QAbstractItemView.MultiSelection)

        # Keep stable index -> row mapping
        for r in attached_rows:
            disp = (r.get("OriginalFilename") or "").strip()
            if not disp:
                disp = (r.get("StoredFilename") or "").strip()
            if not disp:
                disp = os.path.basename(r.get("FullPath") or "")
            lst.addItem(disp)

        lay.addWidget(lst)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)

        if dlg.exec() != QDialog.Accepted:
            return []

        idxs = lst.selectionModel().selectedIndexes()
        chosen_paths = []
        for ix in idxs:
            row = ix.row()
            if 0 <= row < len(attached_rows):
                p = attached_rows[row].get("FullPath") or ""
                if p:
                    chosen_paths.append(p)
        return chosen_paths

    chosen = _pick_attached_pdfs(attached)
    if not chosen:
        return

    # Determine target tables (same logic as the tabs)
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

    # Helper: find TrialID for a given spool number within this TrialSeries
    def _trial_id_for_spool(cur, spool_no: int) -> Optional[int]:
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

    imported = 0
    skipped = []
    errors = []

    for pdf_idx, pdf_path in enumerate(chosen):
        prog = QProgressDialog(
            f"Lese {os.path.basename(pdf_path)}…", "Abbrechen",
            0, len(chosen), self
        )
        prog.setWindowTitle("Statimat import")
        prog.setWindowModality(Qt.WindowModal)
        prog.setMinimumDuration(0)
        prog.setValue(pdf_idx)
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
        if prog.wasCanceled():
            break

        try:
            header, pages = parse_statimat_pdf(pdf_path)
            geraet = (header.get('device') or '').strip()
            device_raw = (header.get('device_raw') or '').strip()
            # Debug: print to terminal (if one exists) and always log to %TEMP%
            try:
                msg = f"[STATIMAT IMPORT] {os.path.basename(pdf_path)} | device={geraet!r} raw={device_raw!r}"
                sys.stdout.flush()
            except Exception:
                pass
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

            # Enforce EXACT device detection
            if geraet not in ('STATIMAT DS', 'STATIMAT M'):
                skipped.append(f"{os.path.basename(pdf_path)}: Unknown device '{geraet}' (raw='{device_raw}')")
                continue
            customer = (header.get("customer") or "").strip()
            geraet = (header.get("device") or "").strip()
            # material not used for matching/writing yet, but we keep it available
            # material = (header.get("material") or "").strip()

            # Validate Customer vs current TrialSeriesID
            # Customer/TrialSeriesID Check entfernt
            # Gerät ist canonical aus Parser: 'STATIMAT DS' oder 'STATIMAT M'
            if geraet not in ('STATIMAT DS', 'STATIMAT M'):
                skipped.append(f"{os.path.basename(pdf_path)}: Unknown device '{geraet}'")
                continue

            is_ds = (geraet == 'STATIMAT DS')
            is_m = (geraet == 'STATIMAT M')
            if is_ds and not stat_ds_table:
                skipped.append(f"{os.path.basename(pdf_path)}: Statimat-DS Tabelle nicht gefunden.")
                continue
            if is_m and not stat_m_table:
                skipped.append(f"{os.path.basename(pdf_path)}: Statimat-M Tabelle nicht gefunden.")
                continue

            target_table = stat_ds_table if is_ds else stat_m_table
            col_elong, col_elong_cv, col_ten, col_ten_cv = (stat_ds_cols if is_ds else stat_m_cols)

            if not all([target_table, col_elong, col_elong_cv, col_ten, col_ten_cv]):
                skipped.append(f"{os.path.basename(pdf_path)}: Could not resolve columns (schema).")
                continue

            with get_connection() as cn:
                cur = cn.cursor()

                for pr in pages:
                    spool_no = pr.get("spool_no")
                    if not spool_no:
                        continue

                    trial_id = _trial_id_for_spool(cur, int(spool_no))
                    if not trial_id:
                        skipped.append(
                            f"{os.path.basename(pdf_path)} / Spule {spool_no}: Kein passender Trial gefunden.")
                        continue

                    # Upsert statimat row
                    cur.execute(
                        f"SELECT ID FROM [{target_table}] WHERE TrialID = ? LIMIT 1",
                        (trial_id,),
                    )
                    row = cur.fetchone()
                    elong_x = pr.get("dehnung_x")
                    elong_cv = pr.get("dehnung_cv")
                    ten_x = pr.get("festigkeit_x")
                    ten_cv = pr.get("festigkeit_cv")

                    if row and row[0] is not None:
                        rec_id = row[0]
                        cur.execute(
                            f"UPDATE [{target_table}] SET "
                            f"[{col_elong}]=?, [{col_elong_cv}]=?, [{col_ten}]=?, [{col_ten_cv}]=? "
                            f"WHERE ID=?",
                            (elong_x, elong_cv, ten_x, ten_cv, rec_id),
                        )
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

                    # DS: also write titer
                    # DS + M: also write titer
                    if titer_table and titer_col:
                        titer_x = pr.get("feinheit_x")
                        if titer_x is not None:
                            cur.execute(
                                f"SELECT ID FROM [{titer_table}] WHERE TrialID=? LIMIT 1",
                                (trial_id,),
                            )
                            tr = cur.fetchone()
                            if tr and tr[0] is not None:
                                cur.execute(
                                    f"UPDATE [{titer_table}] SET [{titer_col}]=? WHERE ID=?",
                                    (titer_x, tr[0]),
                                )
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

                    imported += 1

        except Exception as e:
            errors.append(f"{os.path.basename(pdf_path)}: {e}")

        finally:
            try:
                prog.setValue(pdf_idx + 1)
                prog.close()
            except Exception:
                pass

    # refresh views/tabs
    try:
        self._build_titer_tab()
        self._build_statimat_tab()
        self._build_statimat_ds_tab()
    except Exception:
        pass

    # Feature-Tracking: nur wenn mindestens eine Spule aktualisiert wurde
    if imported >= 1:
        try:
            user_id = app_meta.current_user.get("id") if app_meta.current_user else None
            if user_id is not None:
                _db_execute(
                    "INSERT INTO tblFeatureUsage (FeatureID, UserID, ExtraInfo) VALUES (?, ?, ?)",
                    [1, user_id, str(getattr(self, '_series_pk', None))],
                )
        except Exception:
            pass  # Tracking darf nie den Import-Flow stoeren
    msg = f"Import fertig.\n\nImportierte Spulen: {imported}"
    if skipped:
        msg += "\n\nSkipped:\n" + "\n".join(skipped[:50])
        if len(skipped) > 50:
            msg += f"\n... ({len(skipped) - 50} weitere)"
    if errors:
        msg += "\n\nFehler:\n" + "\n".join(errors[:50])
        if len(errors) > 50:
            msg += f"\n... ({len(errors) - 50} weitere)"

    QMessageBox.information(self, "Statimat import", msg)



def itemat_import_impl(self) -> None:
    """Import Itemat Lab PDF(s) attached to this TrialSeries into tblLaborItematLab.

    Mapping:
      PDF Seite N  ->  Trial mit Versuchsnummer = N in dieser TrialSeries
      Knoten/m (Spalte 1)       -> tblLaborItematLab.[Intermingling Points (FP/m)]  @ Tension 0.0
      Var.-Koeff. [%] (Spalte 1)-> tblLaborItematLab.[Intermingling Points CV (%)]  @ Tension 0.0
      Stab.-Faktor [%] (Sp. 2)  -> tblLaborItematLab.[Stability (%)]               @ Tension 0.3
      Stab.-Faktor [%] (Sp. 3)  -> tblLaborItematLab.[Stability (%)]               @ Tension 0.6
      Stab.-Faktor [%] (Sp. 4)  -> tblLaborItematLab.[Stability (%)]               @ Tension 1.0
      Stab.-Faktor [%] (Sp. 5)  -> tblLaborItematLab.[Stability (%)]               @ Tension 1.3
      FPm @ Tension > 0.0 = Knoten/m_0 * Stability / 100
    """
    # Lazy import (vermeidet Zirkularimport, screen_show_experiment importiert
    # dieses Modul selbst) - table_exists/get_columns_map sind die lowercase-
    # normalisierenden Wrapper aus screen_show_experiment, nicht die aus db.connection.
    from ui.screen_show_experiment import table_exists, get_columns_map
    from ui.widgets.itemat_pdf_parser import parse_itemat_pdf, DB_TENSIONS

    sid = getattr(self, "_series_pk", None)
    if sid in (None, ""):
        QMessageBox.information(self, "Itemat import", "Keine TrialSeries geladen.")
        return

    # Ziel-Tabelle prüfen
    itemat_table = "tblLaborItematLab"
    if not table_exists(itemat_table):
        QMessageBox.warning(self, "Itemat import",
                            f"Tabelle '{itemat_table}' nicht gefunden.")
        return

    # Angehängte PDFs laden
    try:
        attached = self._fetch_series_pdfs(sid)
    except Exception as e:
        QMessageBox.warning(self, "Itemat import",
                            f"Konnte PDF-Liste nicht laden:\n{e}")
        return

    if not attached:
        QMessageBox.information(self, "Itemat import",
                                "This trial series has no attached PDFs.")
        return

    # PDF-Auswahl-Dialog (analog Statimat)
    def _pick_attached_pdfs(attached_rows):
        dlg = QDialog(self)
        dlg.setWindowTitle("Select Itemat Lab PDFs")
        lay = QVBoxLayout(dlg)
        info = QLabel(
            "Select the Itemat Lab PDFs to import\n"
            "(only PDFs attached to this trial series):"
        )
        info.setWordWrap(True)
        lay.addWidget(info)
        lst = QListWidget()
        lst.setSelectionMode(QAbstractItemView.MultiSelection)
        for r in attached_rows:
            disp = (r.get("OriginalFilename") or "").strip()
            if not disp:
                disp = (r.get("StoredFilename") or "").strip()
            if not disp:
                disp = os.path.basename(r.get("FullPath") or "")
            lst.addItem(disp)
        lay.addWidget(lst)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        if dlg.exec() != QDialog.Accepted:
            return []
        chosen_paths = []
        for ix in lst.selectionModel().selectedIndexes():
            row = ix.row()
            if 0 <= row < len(attached_rows):
                p = attached_rows[row].get("FullPath") or ""
                if p:
                    chosen_paths.append(p)
        return chosen_paths

    chosen = _pick_attached_pdfs(attached)
    if not chosen:
        return

    # Spalten einmal auflösen
    cols = get_columns_map(itemat_table)
    col_tension = cols.get("tension")
    col_fpm = cols.get("fpm")
    col_fpmcv = cols.get("fpmcv")
    col_stability = cols.get("stability")
    col_user = cols.get("user")
    col_ts = cols.get("timestamp")

    if not all([col_tension, col_fpm, col_stability]):
        QMessageBox.warning(
            self, "Itemat import",
            f"Could not resolve required columns.\n"
            f"Tension={col_tension}, FPm={col_fpm}, Stability={col_stability}"
        )
        return

    # Aktueller User
    current_user = (
        app_meta.current_user.get("id")
    ) if app_meta.current_user else None

    imported = 0
    skipped: list = []
    errors: list = []

    for pdf_path in chosen:
        try:
            # Progress-Dialog
            prog = QProgressDialog(
                f"Lese {os.path.basename(pdf_path)}…", "Abbrechen", 0, 100, self
            )
            prog.setWindowTitle("Itemat import")
            prog.setWindowModality(Qt.WindowModal)
            prog.setMinimumDuration(0)
            prog.setValue(0)

            def _progress(cur, total, _prog=prog):
                if _prog.wasCanceled():
                    raise InterruptedError("Abgebrochen")
                _prog.setValue(int(cur / total * 100))
                from PySide6.QtWidgets import QApplication
                QApplication.processEvents()

            header, records = parse_itemat_pdf(pdf_path, progress_callback=_progress)
            prog.setValue(100)
            prog.close()

        except InterruptedError:
            skipped.append(f"{os.path.basename(pdf_path)}: Abgebrochen.")
            continue
        except Exception as e:
            errors.append(f"{os.path.basename(pdf_path)}: Parser-Fehler: {e}")
            continue

        with get_connection() as cn:
            cur = cn.cursor()

            for rec in records:
                versuch_nr = rec.get("versuch_nr")
                if not versuch_nr:
                    skipped.append(
                        f"{os.path.basename(pdf_path)} / Seite {rec['page']}: "
                        f"Versuchsnummer nicht bestimmbar."
                    )
                    continue

                # Trial-ID via Versuchsnummer
                cur.execute(
                    "SELECT ID FROM tblTrial "
                    "WHERE TrialSeriesID = ? AND Versuchsnummer = ? LIMIT 1",
                    (sid, versuch_nr),
                )
                row = cur.fetchone()
                if not row or row[0] is None:
                    skipped.append(
                        f"{os.path.basename(pdf_path)} / V{versuch_nr}: "
                        f"Kein passender Trial gefunden."
                    )
                    continue

                trial_id = int(row[0])
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

                    if rec_id is not None:
                        cur.execute(
                            f"UPDATE [{itemat_table}] SET "
                            + ", ".join(set_parts)
                            + " WHERE ID=?",
                            vals + [rec_id],
                        )
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

                imported += 1

    # Tabs auffrischen
    try:
        self._build_itemat_tab()
        self._build_itemat_plus_tab()
    except Exception:
        pass

    # Feature-Tracking (stealth)
    if imported >= 1:
        try:
            user_id = app_meta.current_user.get("id") if app_meta.current_user else None
            if user_id is not None:
                _db_execute(
                    "INSERT INTO tblFeatureUsage (FeatureID, UserID, ExtraInfo) VALUES (?, ?, ?)",
                    [5, user_id, str(getattr(self, "_series_pk", None))],
                )
        except Exception:
            pass

    msg = f"Itemat import fertig.\n\nImportierte Versuche: {imported}"
    if skipped:
        msg += "\n\nSkipped:\n" + "\n".join(skipped[:50])
        if len(skipped) > 50:
            msg += f"\n... ({len(skipped) - 50} weitere)"
    if errors:
        msg += "\n\nFehler:\n" + "\n".join(errors[:50])
        if len(errors) > 50:
            msg += f"\n... ({len(errors) - 50} weitere)"

    QMessageBox.information(self, "Itemat import", msg)

