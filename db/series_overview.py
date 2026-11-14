"""series_overview.py - the series lists of All Experiments and Backlog, without Qt.

Moved out of ui/screen_all_experiments.py (_load_data) and ui/screen_backlog.py
(_load_status_into / _load_archived / reload_all) on 2026-11-13, so that the
desktop screens and the web app (tripplet_web) show exactly the same rows.
The SQL is unchanged.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from db.connection import fetch_all, fetch_experiments_with_series, get_columns_map, table_exists

# machine filter buttons of All Experiments: label -> tblMaschine.ID (None = all)
MACHINE_FILTERS = {
    "All": None,
    "AFK": 2,
    "eAFK": 1,
    "Aalidhra": 6,
    "Zinser": 3,
    "SSM DP2T": 4,
    "SSM Xeno": 5,
}

# fallback when tblBacklogStatus cannot be read (same as the screens had)
DEFAULT_STATUSES = [
    {"ID": 1, "BacklogStatus": "Backlog"},
    {"ID": 2, "BacklogStatus": "In Progress"},
    {"ID": 3, "BacklogStatus": "Done"},
    {"ID": 4, "BacklogStatus": "To Be Cleaned"},
    {"ID": 5, "BacklogStatus": "Archived"},
]


def experiment_request_field() -> Optional[str]:
    """Column in tblExperimente that stores a linked Experiment Request ID (version tolerant)."""
    try:
        if not table_exists('tblExperimente'):
            return None
        from ui.text_normalize import resolve_field
        cols = get_columns_map('tblExperimente')
        return resolve_field(
            ['ExperimentRequest', 'Experiment Request', 'ExperimentRequestID', 'ExperimentRequestId'],
            cols,
        )
    except Exception:
        return None


def status_lookup() -> List[Dict[str, Any]]:
    """[{ID, BacklogStatus}] ordered by ID."""
    try:
        return fetch_all("""
              SELECT [ID], [BacklogStatus]
              FROM tblBacklogStatus
              ORDER BY [ID]; \
              """, [])
    except Exception:
        return [dict(r) for r in DEFAULT_STATUSES]


def series_report_map() -> Dict[int, int]:
    """{TrialSeriesID: number of saved Smart-Chart reports} (RE icon)."""
    try:
        _report_rows = fetch_all(
            "SELECT SeriesPK, COUNT(*) AS n FROM tblSmartChartReport "
            "WHERE IsTemplate=0 AND SeriesPK IS NOT NULL GROUP BY SeriesPK"
        )
        return {int(r["SeriesPK"]): int(r["n"]) for r in _report_rows}
    except Exception:
        return {}


def reports_for_series(series_pk) -> List[Dict[str, Any]]:
    """Saved (non-template) Smart-Chart reports of a trial series, newest first:
    [{"ID", "Title", "Author"}] - RE icon in All Experiments/Backlog (moved from
    ui/widgets/report_picker.py). [] if the table is missing / on DB errors."""
    if not series_pk:
        return []
    try:
        return fetch_all(
            "SELECT ID, Title, Author FROM tblSmartChartReport "
            "WHERE SeriesPK=? AND IsTemplate=0 ORDER BY UpdatedAt DESC",
            [series_pk],
        )
    except Exception:
        return []


# --------------------------------------------------------------------------- All Experiments
def _chunks(lst, n=200):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def all_experiments_rows(maschine_id: Optional[int] = None, er_field: Optional[str] = None) -> List[Dict[str, Any]]:
    """fetch_experiments_with_series() + experiment_request_id, has_attach, has_notes.
    Raises if the base query fails (the screen shows "DB error")."""
    rows = fetch_experiments_with_series(maschine_id)

    # Experiment-Request IDs (einmalig laden)
    er_map = {}
    try:
        fld = er_field
        if fld:
            q = f"SELECT [ID] AS exp_id_pk, [{fld}] AS experiment_request_id FROM tblExperimente;"
            er_rows = fetch_all(q, [])
            for rr in er_rows or []:
                er_map[rr.get('exp_id_pk')] = rr.get('experiment_request_id')
    except Exception:
        er_map = {}

    # in Records einhaengen (fuer Sortierung + Anzeige)
    if er_map:
        for rec in rows:
            try:
                rec['experiment_request_id'] = er_map.get(rec.get('exp_id_pk'))
            except Exception:
                pass
    else:
        for rec in rows:
            rec['experiment_request_id'] = None

    # -------------------------------------------------
    # Attachments (Image/PDF) pro TrialSeries ermitteln
    # -------------------------------------------------
    series_ids = []
    try:
        series_ids = [int(r.get('series_id_pk')) for r in rows if r.get('series_id_pk') is not None]
    except Exception:
        series_ids = []

    has_attach_set: set[int] = set()
    if series_ids:
        def _fetch_series_ids(tbl_name: str) -> set[int]:
            out: set[int] = set()
            try:
                for ch in _chunks(series_ids, 200):
                    ph = ",".join(["?"] * len(ch))
                    q = f"SELECT [TrialSeriesID] FROM {tbl_name} WHERE [TrialSeriesID] IN ({ph}) GROUP BY [TrialSeriesID];"
                    rr = fetch_all(q, ch)
                    for rrr in rr or []:
                        try:
                            out.add(int(rrr.get('TrialSeriesID')))
                        except Exception:
                            continue
            except Exception:
                return set()
            return out

        img_ids = _fetch_series_ids("tblTrialSeriesImage")
        pdf_ids = _fetch_series_ids("tblTrialSeriesPDF")
        has_attach_set = set(img_ids) | set(pdf_ids)

    # Notes: fetch series IDs that have non-empty Notes
    has_notes_set: set[int] = set()
    if series_ids:
        try:
            for ch in _chunks(series_ids, 200):
                ph = ",".join(["?"] * len(ch))
                q = f"SELECT ID FROM tblTrialSeries WHERE ID IN ({ph}) AND Notes IS NOT NULL AND Notes <> '';"
                rr = fetch_all(q, ch)
                for rrr in rr or []:
                    try:
                        has_notes_set.add(int(rrr.get('ID')))
                    except Exception:
                        continue
        except Exception:
            pass

    for rec in rows:
        try:
            sid = rec.get('series_id_pk')
            rec['has_attach'] = bool(sid is not None and int(sid) in has_attach_set)
            rec['has_notes'] = bool(sid is not None and int(sid) in has_notes_set)
        except Exception:
            rec['has_attach'] = False
            rec['has_notes'] = False
    return rows


# --------------------------------------------------------------------------- Backlog
def _er_select(er_field: Optional[str]) -> str:
    er_select = ''
    if er_field:
        try:
            er_select = f", e.[{er_field}] AS [ExperimentRequestID]"
        except Exception:
            er_select = ''
    if not er_select:
        er_select = ', NULL AS [ExperimentRequestID]'
    return er_select


def backlog_rows(status_id: int, er_field: Optional[str] = None) -> List[Dict[str, Any]]:
    """Cards of one Backlog box (status 1-4): prio first (NULL last), then newest experiment."""
    # Sortierung (alle Boxen):
    # - Prio zuerst (1 ganz oben), hohe Zahl unten
    # - NULL-Prio immer ganz unten
    # - Danach nach Experiment-ID (neueste oben) und stabil nach Series-ID
    order_by = """
        ORDER BY
            CASE WHEN s.[BacklogPrio] IS NULL THEN 1 ELSE 0 END,
            s.[BacklogPrio] ASC,
            e.[Experiment ID] DESC,
            s.[ID] DESC
    """
    er_select = _er_select(er_field)
    sql = f"""
        SELECT
            s.[ID]              AS [TrialSeriesID],
            e.[ID]              AS [ExperimentPK],
            e.[Experiment ID]   AS [Experiment ID],
            s.[SeriesName]      AS [TrialSeries Name],
            m.[Maschine]        AS [Maschine],
            bs.[BacklogStatus]  AS [Status],
            s.[BacklogPrio]     AS [Prio],
            u.[Username]        AS [Owner],
            u.[Colour]          AS [OwnerColour]
            , CASE WHEN tsi.[TrialSeriesID] IS NULL THEN 0 ELSE 1 END AS [HasImage]
            , CASE WHEN tsp.[TrialSeriesID] IS NULL THEN 0 ELSE 1 END AS [HasPDF]
            , CASE WHEN (s.[Notes] IS NOT NULL AND s.[Notes] <> '') THEN 1 ELSE 0 END AS [HasNotes]
            {er_select}
        FROM
            (((((tblExperimente AS e
              INNER JOIN tblTrialSeries AS s
                ON e.[ID] = s.[ExperimentID])
              LEFT JOIN tblMaschine AS m
                ON m.[ID] = s.[MachineID])
              LEFT JOIN tblBacklogStatus AS bs
                ON bs.[ID] = s.[BacklogStatusID])
              LEFT JOIN tblUser AS u
                ON u.[ID] = s.[BacklogOwner])
              LEFT JOIN (
                    SELECT [TrialSeriesID]
                    FROM tblTrialSeriesImage
                    GROUP BY [TrialSeriesID]
              ) AS tsi
                ON tsi.[TrialSeriesID] = s.[ID])
              LEFT JOIN (
                    SELECT [TrialSeriesID]
                    FROM tblTrialSeriesPDF
                    GROUP BY [TrialSeriesID]
              ) AS tsp
                ON tsp.[TrialSeriesID] = s.[ID]
        WHERE
            s.[BacklogStatusID] = {int(status_id)}
        {order_by}
    """
    try:
        return fetch_all(sql, [])
    except Exception:
        return []


def archived_rows(er_field: Optional[str] = None) -> List[Dict[str, Any]]:
    """Archived series (BacklogStatusID = 5), newest experiment first."""
    er_select = _er_select(er_field)
    sql = f"""
        SELECT
            s.[ID]              AS [TrialSeriesID],
            e.[ID]              AS [ExperimentPK],
            e.[Experiment ID]   AS [Experiment ID],
            s.[SeriesName]      AS [TrialSeries Name],
            m.[Maschine]        AS [Maschine]
            {er_select}
        FROM
            (((tblExperimente AS e
              INNER JOIN tblTrialSeries AS s
                ON e.[ID] = s.[ExperimentID])
              LEFT JOIN tblMaschine AS m
                ON m.[ID] = s.[MachineID])
              LEFT JOIN tblBacklogStatus AS bs
                ON bs.[ID] = s.[BacklogStatusID])
        WHERE
            s.[BacklogStatusID] = 5
        ORDER BY
            e.[Experiment ID] DESC,
            s.[ID] DESC
    """
    try:
        return fetch_all(sql, [])
    except Exception:
        return []


def backlog_fingerprint() -> str:
    """Short fingerprint of everything the Backlog shows (status, prio, name, machine, owner, notes, attachment
    and retest-flag counts). Both apps poll it and reload the Backlog only when it changed - cheap enough for
    every 30 s. Empty string if the database cannot be read."""
    import hashlib
    try:
        rows = fetch_all(
            "SELECT [ID], [BacklogStatusID], [BacklogPrio], [SeriesName], [MachineID], [BacklogOwner], "
            "CASE WHEN ([Notes] IS NOT NULL AND [Notes] <> '') THEN 1 ELSE 0 END AS [N] "
            "FROM tblTrialSeries ORDER BY [ID]", [])
        extra = []
        for tbl in ("tblTrialSeriesImage", "tblTrialSeriesPDF"):
            try:
                extra.append(fetch_all(f"SELECT COUNT(*) AS [C] FROM {tbl}", [])[0]["C"])
            except Exception:
                extra.append(None)
        flags = retest_flags_map()
        extra.append(sorted((int(k), len(v)) for k, v in flags.items()))
    except Exception:
        return ""
    h = hashlib.sha1()
    for r in rows:
        h.update(repr((r.get("ID"), r.get("BacklogStatusID"), r.get("BacklogPrio"), r.get("SeriesName"),
                       r.get("MachineID"), r.get("BacklogOwner"), r.get("N"))).encode("utf-8"))
    h.update(repr(extra).encode("utf-8"))
    return h.hexdigest()[:16]


def retest_flags_map() -> Dict[int, list]:
    """{TrialSeriesID: [open retest flags]} (db/retest_flags.py)."""
    try:
        from db.retest_flags import get_open_retest_flags_by_series
        return get_open_retest_flags_by_series()
    except Exception:
        return {}
