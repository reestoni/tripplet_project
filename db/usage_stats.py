# db/usage_stats.py
"""Usage Stats (ui/screen_usage_stats.py) without Qt (2026-11-13, for the web version; the desktop screen uses it).

Reads tblUsageLog (db/usage_log.py): logins per user, screens, features, the ranking of the top 15 screens /
features, logins per day (last 30 days) and the help-search events summarised (what was searched, what is
missing). Superusers only (activity per user, not anonymised)."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from db.connection import fetch_all, table_exists

HELP_COLUMNS = ["Kind", "Question", "Result", "Count", "Users", "LastUsed"]

# order = need for action (on top: what is missing in help / synonyms)
HELP_KINDS = [
    ("help_search_noresult", "No result"),
    ("help_whatsnew_noresult", "Fresh off the Spool: no result"),
    ("help_feedback_down", "Not helpful"),
    ("help_ai_error", "AI error"),
    ("help_search_noclick", "Searched, nothing opened"),
    ("help_ai_ask", "Asked AI"),
    ("help_search_open", "Opened"),
    ("help_whatsnew_search", "Fresh off the Spool: searched"),
    ("help_feedback_up", "Helpful"),
]


def available() -> bool:
    return table_exists("tblUsageLog")


def load_stats() -> Dict[str, List[Dict[str, Any]]]:
    """All lists of the screen: logins, screens, features, ranking, login_timeline, help_events."""
    return {
        "logins": fetch_all(
            "SELECT Username, COUNT(*) AS Logins, MAX(EventTime) AS LastLogin "
            "FROM tblUsageLog WHERE EventType = 'login' GROUP BY Username ORDER BY Logins DESC"),
        "screens": fetch_all(
            "SELECT EventName AS Screen, COUNT(*) AS Opens, COUNT(DISTINCT Username) AS Users, MAX(EventTime) AS LastUsed "
            "FROM tblUsageLog WHERE EventType = 'screen_open' GROUP BY EventName ORDER BY Opens DESC"),
        "features": fetch_all(
            "SELECT EventName AS Feature, Detail, COUNT(*) AS Uses, COUNT(DISTINCT Username) AS Users, "
            "MAX(EventTime) AS LastUsed FROM tblUsageLog WHERE EventType = 'feature' "
            "GROUP BY EventName, Detail ORDER BY Uses DESC"),
        "ranking": fetch_all(
            "SELECT EventName AS Name, EventType, COUNT(*) AS Cnt FROM tblUsageLog "
            "WHERE EventType IN ('screen_open', 'feature') GROUP BY EventName, EventType ORDER BY Cnt DESC LIMIT 15"),
        "login_timeline": fetch_all(
            "SELECT DATE(EventTime) AS Day, COUNT(*) AS Cnt FROM tblUsageLog WHERE EventType = 'login' "
            "AND EventTime >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) GROUP BY DATE(EventTime) ORDER BY Day ASC"),
        "help_events": fetch_all(
            "SELECT EventName, Detail, Username, EventTime FROM tblUsageLog "
            "WHERE EventType = 'feature' AND EventName LIKE 'help\\_%'"),
    }


def readable_help_result(result: str) -> str:
    """'show_experiment:tasks:11 (AI)' -> 'Show Experiment: Print labels ... (AI)'."""
    m = re.match(r"^([a-z_]+:[a-z_]+:\d+)(.*)$", result or "")
    if not m:
        return result
    try:
        from ui.help_index import hit_for_key, SCREEN_NAMES, normalize_display
        h = hit_for_key(m.group(1))
        if h is None:
            return result
        e = h.by_lang.get("en") or next(iter(h.by_lang.values()))
        return f"{SCREEN_NAMES.get(h.screen, h.screen)}: {normalize_display(e.question)}{m.group(2)}"
    except Exception:
        return result


def summarize_help_events(events) -> Tuple[List[Dict[str, Any]], str]:
    """help_* events -> rows (kind, question, result, count, users, last used) + a summary line.
    Detail formats (help_search / help_ai): "question -> key[ (AI)]", "question | hits=n", "question | error"."""
    order = {name: i for i, (name, _l) in enumerate(HELP_KINDS)}
    labels = dict(HELP_KINDS)
    groups: Dict[tuple, Dict[str, Any]] = {}
    totals: Dict[str, int] = {}
    for ev in events:
        name = ev.get("EventName") or ""
        if name not in order:
            continue
        detail = str(ev.get("Detail") or "")
        if " -> " in detail:
            question, result = detail.split(" -> ", 1)
        elif " | " in detail:
            question, result = detail.split(" | ", 1)
        else:
            question, result = detail, ""
        question = question.strip().lower()
        key = (name, question, result.strip())
        g = groups.setdefault(key, {"count": 0, "users": set(), "last": None})
        g["count"] += 1
        g["users"].add(ev.get("Username") or "")
        t = ev.get("EventTime")
        if t is not None and (g["last"] is None or t > g["last"]):
            g["last"] = t
        totals[name] = totals.get(name, 0) + 1
    rows = [{"Kind": labels[n], "KindKey": n, "Question": q, "Result": readable_help_result(r), "Count": g["count"],
             "Users": len(g["users"]), "LastUsed": g["last"]}
            for (n, q, r), g in groups.items()]
    rows.sort(key=lambda r: (order[r["KindKey"]], -r["Count"]))
    summary = " · ".join(f"{labels[n]}: {totals.get(n, 0)}" for n, _l in HELP_KINDS)
    return rows, ("Help search – " + summary) if events else "No help searches recorded yet."
