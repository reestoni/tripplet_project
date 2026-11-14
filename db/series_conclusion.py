"""Conclusion of a trial series ("Fazit", user request 2026-11-14) - Qt-free, shared by the desktop tab
(ui/widgets/conclusion_tab.py) and the web app (app/conclusion_api.py).

One row per series in ``tblSeriesConclusion`` (created only by tools/series_conclusion_migration.py). It is not
tied to a status change: "Done" means "ready to be analysed", the conclusion is written afterwards, any time.

Fields: own goal (only used when the series has no experiment request - with a request its goal is shown),
outcome (achieved / partly / not achieved / open), short summary (max 300 characters, shown on Backlog cards and
in All Experiments), best trials, findings (free text), recommendation (follow-up / release / discard + text).

Every change goes to the change history (tblChangeLog, source "conclusion"). The first save notifies whoever
created the experiment request (bell, type "series_conclusion"). The table has a TrialSeriesID column, so the
recycle bin takes the conclusion along with its series automatically (db/recycle_bin.collect_series).
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

TABLE = "tblSeriesConclusion"

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS tblSeriesConclusion (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    TrialSeriesID INT NOT NULL,
    Goal TEXT NULL,
    Outcome VARCHAR(20) NULL,
    Summary VARCHAR(300) NULL,
    BestTrials VARCHAR(500) NULL,
    Findings MEDIUMTEXT NULL,
    Recommendation VARCHAR(20) NULL,
    RecommendationText TEXT NULL,
    CreatedBy INT NULL,
    CreatedAt DATETIME NULL,
    UpdatedBy INT NULL,
    UpdatedAt DATETIME NULL,
    UNIQUE KEY ux_seriesconclusion_series (TrialSeriesID),
    INDEX ix_seriesconclusion_outcome (Outcome)
)
"""

OUTCOMES = ("achieved", "partly", "not_achieved", "open")
RECOMMENDATIONS = ("follow_up", "release", "discard")
# desktop labels (the web translates the keys itself)
OUTCOME_LABELS = {"achieved": "Achieved", "partly": "Partly achieved", "not_achieved": "Not achieved", "open": "Open"}
RECOMMENDATION_LABELS = {"follow_up": "Follow-up trial", "release": "Release", "discard": "Discard"}
OUTCOME_COLOURS = {"achieved": "#2e9e4f", "partly": "#e0a800", "not_achieved": "#d64545", "open": "#8a94a0"}

SUMMARY_MAX = 300
GOAL_MAX = 2000
FINDINGS_MAX = 20000
REC_TEXT_MAX = 2000
NOTIFICATION_TYPE = "series_conclusion"

# field in the dict <-> column
_COLS = {"goal": "Goal", "outcome": "Outcome", "summary": "Summary", "best_trials": "BestTrials",
         "findings": "Findings", "recommendation": "Recommendation", "recommendation_text": "RecommendationText"}


class ConclusionError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# ── availability / rights ────────────────────────────────────────────────
def table_ready() -> bool:
    try:
        from db.connection import table_exists
        return bool(table_exists(TABLE))
    except Exception:
        return False


def _user() -> Dict[str, Any]:
    try:
        import app_meta
        return dict(app_meta.current_user or {})
    except Exception:
        return {}


def can_edit(user: Optional[Dict[str, Any]] = None) -> bool:
    """Same rule as editing the values of a series: access level 2 and up."""
    u = user if user is not None else _user()
    try:
        return int(u.get("access_level") or 0) >= 2
    except Exception:
        return False


# ── reading ──────────────────────────────────────────────────────────────
def request_goal(series_id: int) -> Optional[Dict[str, Any]]:
    """Goal of the linked experiment request (title, reason, task, evaluation criteria) or None."""
    from db.connection import fetch_all
    try:
        rows = fetch_all(
            "SELECT er.ID, er.Titel, er.Versuchsgrund, er.Aufgabe, er.Beurteilungsparameter, er.CreatedBy "
            "FROM tblTrialSeries ts JOIN tblExperimente e ON e.ID = ts.ExperimentID "
            "JOIN tblExperimentRequests er ON er.ID = e.ExperimentRequestID WHERE ts.ID = ?", [int(series_id)])
    except Exception:
        return None
    if not rows:
        return None
    r = rows[0]
    return {"request_id": int(r["ID"]), "title": str(r.get("Titel") or ""), "reason": str(r.get("Versuchsgrund") or ""),
            "task": str(r.get("Aufgabe") or ""), "criteria": str(r.get("Beurteilungsparameter") or ""),
            "created_by": r.get("CreatedBy")}


def _row(series_id: int) -> Optional[Dict[str, Any]]:
    from db.connection import fetch_all
    rows = fetch_all(f"SELECT * FROM {TABLE} WHERE TrialSeriesID = ?", [int(series_id)])
    return rows[0] if rows else None


def _ids(text: Any) -> List[int]:
    out: List[int] = []
    for p in str(text or "").split(","):
        p = p.strip()
        if p.isdigit() and int(p) not in out:
            out.append(int(p))
    return out


def _user_name(uid: Any) -> str:
    if uid in (None, ""):
        return ""
    from db.connection import fetch_all
    try:
        rows = fetch_all("SELECT Username, FirstName, LastName FROM tblUser WHERE ID = ?", [uid])
    except Exception:
        try:
            rows = fetch_all("SELECT Username FROM tblUser WHERE ID = ?", [uid])
        except Exception:
            rows = []
    if not rows:
        return ""
    r = rows[0]
    full = " ".join(x for x in (str(r.get("FirstName") or "").strip(), str(r.get("LastName") or "").strip()) if x)
    return full or str(r.get("Username") or "")


def empty() -> Dict[str, Any]:
    return {"goal": "", "outcome": None, "summary": "", "best_trials": [], "findings": "", "recommendation": None,
            "recommendation_text": ""}


def get(series_id: int) -> Dict[str, Any]:
    """Conclusion of a series for both apps: fields + the request goal + who changed it last."""
    out: Dict[str, Any] = {"series_id": int(series_id), "ready": table_ready(), "exists": False, **empty(),
                           "request": request_goal(series_id), "updated_by": "", "updated_at": None,
                           "created_by": "", "created_at": None}
    if not out["ready"]:
        return out
    r = _row(series_id)
    if not r:
        return out
    out.update(exists=True, goal=str(r.get("Goal") or ""), outcome=r.get("Outcome") or None,
               summary=str(r.get("Summary") or ""), best_trials=_ids(r.get("BestTrials")),
               findings=str(r.get("Findings") or ""), recommendation=r.get("Recommendation") or None,
               recommendation_text=str(r.get("RecommendationText") or ""),
               updated_by=_user_name(r.get("UpdatedBy")), updated_at=r.get("UpdatedAt"),
               created_by=_user_name(r.get("CreatedBy")), created_at=r.get("CreatedAt"))
    return out


def has_content(c: Dict[str, Any]) -> bool:
    return bool(c.get("outcome") or str(c.get("summary") or "").strip() or str(c.get("findings") or "").strip()
                or c.get("recommendation") or str(c.get("recommendation_text") or "").strip() or c.get("best_trials"))


def summary_map(series_ids: Optional[Iterable[int]] = None) -> Dict[int, Dict[str, Any]]:
    """{series id: {outcome, summary}} for Backlog cards and All Experiments (one query)."""
    if not table_ready():
        return {}
    from db.connection import fetch_all
    sql = f"SELECT TrialSeriesID, Outcome, Summary, Findings, Recommendation FROM {TABLE}"
    params: List[Any] = []
    ids = [int(i) for i in series_ids] if series_ids is not None else None
    if ids is not None:
        if not ids:
            return {}
        sql += f" WHERE TrialSeriesID IN ({','.join('?' * len(ids))})"
        params = ids
    out: Dict[int, Dict[str, Any]] = {}
    try:
        for r in fetch_all(sql, params):
            c = {"outcome": r.get("Outcome") or None, "summary": str(r.get("Summary") or ""),
                 "findings": str(r.get("Findings") or ""), "recommendation": r.get("Recommendation")}
            if has_content(c):
                out[int(r["TrialSeriesID"])] = {"outcome": c["outcome"], "summary": c["summary"]}
    except Exception:
        return {}
    return out


def missing_for_archive(series_id: int) -> bool:
    """True when moving to "Archived" should ask "No conclusion yet - archive anyway?"."""
    if not table_ready():
        return False
    return int(series_id) not in summary_map([int(series_id)])


def search(terms: List[str]) -> Dict[int, str]:
    """Quick search: {series id: matching snippet} where ALL terms appear in goal/summary/findings/recommendation."""
    if not terms or not table_ready():
        return {}
    from db.connection import fetch_all
    try:
        rows = fetch_all(f"SELECT TrialSeriesID, Goal, Summary, Findings, RecommendationText FROM {TABLE}", [])
    except Exception:
        return {}
    out: Dict[int, str] = {}
    low = [t.lower() for t in terms if t]
    for r in rows:
        text = " ".join(str(r.get(k) or "") for k in ("Summary", "Goal", "Findings", "RecommendationText"))
        if low and all(t in text.lower() for t in low):
            out[int(r["TrialSeriesID"])] = str(r.get("Summary") or "").strip() or text.strip()[:120]
    return out


# ── saving ───────────────────────────────────────────────────────────────
def _clean(data: Dict[str, Any], series_id: int) -> Dict[str, Any]:
    def txt(key: str, limit: int) -> str:
        v = str(data.get(key) or "").replace("\r\n", "\n").strip()
        if len(v) > limit:
            raise ConclusionError("too_long", f"{key} is longer than {limit} characters.")
        return v

    outcome = data.get("outcome") or None
    if outcome is not None and outcome not in OUTCOMES:
        raise ConclusionError("invalid", "Unknown outcome.")
    rec = data.get("recommendation") or None
    if rec is not None and rec not in RECOMMENDATIONS:
        raise ConclusionError("invalid", "Unknown recommendation.")
    best = []
    for v in data.get("best_trials") or []:
        try:
            i = int(v)
        except (TypeError, ValueError):
            raise ConclusionError("invalid", "Invalid trial.")
        if i not in best:
            best.append(i)
    if best:
        from db.connection import fetch_all
        ph = ",".join("?" * len(best))
        ok = {int(r["ID"]) for r in fetch_all(f"SELECT ID FROM tblTrial WHERE TrialSeriesID = ? AND ID IN ({ph})",
                                              [int(series_id), *best])}
        if set(best) - ok:
            raise ConclusionError("invalid", "A selected trial does not belong to this series.")
    summary = txt("summary", SUMMARY_MAX).replace("\n", " ")
    return {"goal": txt("goal", GOAL_MAX), "outcome": outcome, "summary": summary,
            "best_trials": ",".join(str(i) for i in best), "findings": txt("findings", FINDINGS_MAX),
            "recommendation": rec, "recommendation_text": txt("recommendation_text", REC_TEXT_MAX)}


def save(series_id: int, data: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create or update the conclusion. Returns {"created": bool, "notified": n, "conclusion": get()}.
    Raises ConclusionError (codes: no_table, no_right, not_found, invalid, too_long)."""
    from db.connection import execute, fetch_all
    from db import change_log
    u = user if user is not None else _user()
    if not table_ready():
        raise ConclusionError("no_table", "Conclusions are not available on this database yet.")
    if not can_edit(u):
        raise ConclusionError("no_right", "Access level 2 is needed to write a conclusion.")
    if not fetch_all("SELECT ID FROM tblTrialSeries WHERE ID = ?", [int(series_id)]):
        raise ConclusionError("not_found", "The trial series does not exist.")
    new = _clean(data, int(series_id))
    uid = u.get("id")
    old = _row(int(series_id))
    created = False
    if old is None:
        if not has_content({**new, "best_trials": new["best_trials"]}) and not new["goal"]:
            return {"created": False, "notified": 0, "conclusion": get(series_id)}
        execute(
            f"INSERT INTO {TABLE} (TrialSeriesID, Goal, Outcome, Summary, BestTrials, Findings, Recommendation, "
            "RecommendationText, CreatedBy, CreatedAt, UpdatedBy, UpdatedAt) VALUES (?,?,?,?,?,?,?,?,?,NOW(),?,NOW())",
            [int(series_id), new["goal"] or None, new["outcome"], new["summary"] or None, new["best_trials"] or None,
             new["findings"] or None, new["recommendation"], new["recommendation_text"] or None, uid, uid])
        old_vals: Dict[str, Any] = {}
        created = True
    else:
        changed = {k: v for k, v in new.items() if str(old.get(_COLS[k]) or "") != str(v or "")}
        if not changed:
            return {"created": False, "notified": 0, "conclusion": get(series_id)}
        sets = ", ".join(f"{_COLS[k]} = ?" for k in changed)
        execute(f"UPDATE {TABLE} SET {sets}, UpdatedBy = ?, UpdatedAt = NOW() WHERE TrialSeriesID = ?",
                [*(v if v not in ("",) else None for v in changed.values()), uid, int(series_id)])
        old_vals = {k: old.get(_COLS[k]) for k in changed}
        new = changed
    row = _row(int(series_id)) or {}
    change_log.log_changes(
        [{"table": TABLE, "row_id": row.get("ID"), "field": _COLS[k], "old": old_vals.get(k), "new": v or None,
          "trial_id": None} for k, v in new.items() if row.get("ID") is not None],
        series_id=int(series_id), source="conclusion", user_id=uid)
    notified = _notify_requester(int(series_id), uid) if created else 0
    return {"created": created, "notified": notified, "conclusion": get(series_id)}


def _notify_requester(series_id: int, actor_id: Any) -> int:
    """Bell message for whoever created the experiment request (not for oneself)."""
    req = request_goal(series_id)
    if not req or req.get("created_by") in (None, "") or str(req["created_by"]) == str(actor_id):
        return 0
    try:
        from ui.notifications import create_series_message_notification
        return int(bool(create_series_message_notification(
            req["created_by"], series_id, f"Conclusion for your request \"{req['title']}\" is ready",
            NOTIFICATION_TYPE)))
    except Exception:
        return 0


def delete(series_id: int) -> None:
    """Only for tests / tools - the app never deletes a conclusion on its own."""
    from db.connection import execute
    execute(f"DELETE FROM {TABLE} WHERE TrialSeriesID = ?", [int(series_id)])


def for_request(request_id: int) -> List[Dict[str, Any]]:
    """Conclusions of all series linked to an experiment request (request popup in both apps)."""
    if not table_ready():
        return []
    from db.connection import fetch_all
    try:
        rows = fetch_all(
            f"SELECT ts.ID, ts.SeriesName, e.ExperimentID, c.Outcome, c.Summary, c.Findings, c.Recommendation, "
            f"c.RecommendationText FROM tblExperimente e JOIN tblTrialSeries ts ON ts.ExperimentID = e.ID "
            f"JOIN {TABLE} c ON c.TrialSeriesID = ts.ID WHERE e.ExperimentRequestID = ? ORDER BY e.ExperimentID, ts.ID",
            [int(request_id)])
    except Exception:
        return []
    return [{"series_id": int(r["ID"]), "series_name": str(r.get("SeriesName") or ""),
             "experiment_id": str(r.get("ExperimentID") or ""), "outcome": r.get("Outcome") or None,
             "summary": str(r.get("Summary") or ""), "recommendation": r.get("Recommendation") or None,
             "recommendation_text": str(r.get("RecommendationText") or "")}
            for r in rows if has_content({"outcome": r.get("Outcome"), "summary": r.get("Summary"),
                                          "findings": r.get("Findings"), "recommendation": r.get("Recommendation")})]
