# tools/migrate_stats_dashboards.py
"""One-off: turns the layouts of the old superuser Statistics page
(tblStatsDashboardBlock / tblStatsDashboardFilter, one per user) into Smart
Chart dashboards (tblSmartChartView), before the page is removed
(Nutzerentscheid 2026-10-30).

Per user with saved cards: a dashboard "Statistics (from the old page)",
owned by that user and shared with the group superuser (view). Every card
becomes a visual - no grouping and no time = Card, otherwise Columns (time
on X, grouping as Legend) - counting experiments / trial series / trials
like before. The filter bar becomes filters on each visual, mapped to the
fields of the card's level (the old page did the same per card):
machines, product groups, order types, lab machines (trials only) and
date from/to as a month range.

Without any saved layout: one "Lab statistics" dashboard from the template,
owned by --owner (default: the first superuser), shared with the group
superuser.

    python tools/migrate_stats_dashboards.py --mode dev_local            (dry run: shows what it would do)
    python tools/migrate_stats_dashboards.py --mode prod --apply

Runs twice without harm: a dashboard with the same name and owner is skipped.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "Statistics (from the old page)"
TEMPLATE_NAME = "Lab statistics"

AGG = {"experiment": "count_experiments", "trialseries": "count_series", "trial": "count"}
GROUP_FIELD = {
    "ordertype": {"experiment": "exp_ordertype", "trialseries": "exp_ordertype", "trial": "exp_ordertype"},
    "productgroup": {"experiment": "exp_productgroup", "trialseries": "exp_productgroup", "trial": "exp_productgroup"},
    "project": {"experiment": "exp_project", "trialseries": "exp_project", "trial": "exp_project"},
    "machine": {"experiment": "exp_machine", "trialseries": "machine", "trial": "machine"},
    "owner": {"experiment": "exp_owner", "trialseries": "owner", "trial": "owner"},
    "labmachine": {"trial": "tested_on"},
}
TIME_FIELD = {"year": {"experiment": "exp_year", "trialseries": "year", "trial": "trial_year"},
              "month": {"experiment": "exp_month", "trialseries": "month", "trial": "trial_month"}}
ROW_FACTOR = 78 / 20      # old grid: 70 px cells + 8 px margin; dashboard rows are 20 px


def visual_for(i: int, block: Dict[str, Any], flt: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    entity = block.get("Entity")
    if entity not in AGG:
        return None
    group = GROUP_FIELD.get(block.get("GroupBy") or "", {}).get(entity)
    time = TIME_FIELD.get(block.get("TimeGranularity") or "", {}).get(entity)
    w = max(2, min(12, int(block.get("GridW") or 4)))
    h = max(3, round(int(block.get("GridH") or 4) * ROW_FACTOR))
    v: Dict[str, Any] = {"id": f"v{i}", "title": "", "agg": AGG[entity], "filters": flt, "w": w, "h": h}
    if block.get("GridX") is not None and block.get("GridY") is not None:
        v["x"], v["y"] = int(block["GridX"]), round(int(block["GridY"]) * ROW_FACTOR)
    if not group and not time:
        v.update({"type": "kpi", "wells": {}})
    elif time:
        v.update({"type": "column", "wells": {"x": time, **({"legend": group} if group else {})}})
    else:
        v.update({"type": "column", "wells": {"x": group}})
    return v


def filters_for(entity: str, old: Dict[str, Any], names: Dict[str, Dict[int, str]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    def ids_to_names(ids, table):
        return [names[table][int(i)] for i in ids or [] if str(i).lstrip("-").isdigit() and int(i) in names[table]]
    machines = ids_to_names(old.get("machines"), "machine")
    if machines:
        out.append({"key": "exp_machine" if entity == "experiment" else "machine", "values": machines})
    pg = ids_to_names(old.get("productGroups"), "productgroup")
    if pg:
        out.append({"key": "exp_productgroup", "values": pg})
    ot = ids_to_names(old.get("orderTypes"), "ordertype")
    if ot:
        out.append({"key": "exp_ordertype", "values": ot})
    if entity == "trial" and old.get("labMachines"):
        out.append({"key": "tested_on", "values": [str(x) for x in old["labMachines"]]})
    lo, hi = str(old.get("dateFrom") or "")[:7], str(old.get("dateTo") or "")[:7]
    if lo or hi:
        out.append({"key": TIME_FIELD["month"][entity], "period": "range", "from": lo or None, "to": hi or None})
    return out


def compact(visuals: List[Dict[str, Any]]) -> None:
    """Move every visual up as far as it goes, like the old page did (GridStack float: false)."""
    done: List[Dict[str, Any]] = []
    for v in sorted(visuals, key=lambda v: (v["y"], v["x"])):
        v["x"] = max(0, min(12 - v["w"], v["x"]))
        y = 0
        while any(o["x"] < v["x"] + v["w"] and v["x"] < o["x"] + o["w"] and o["y"] < y + v["h"] and y < o["y"] + o["h"]
                  for o in done):
            y += 1
        v["y"] = y
        done.append(v)


def build_spec(blocks: List[Dict[str, Any]], old_filters: Dict[str, Any], names) -> Dict[str, Any]:
    from ui import smart_dashboard_engine as en
    visuals = [v for i, b in enumerate(blocks, start=1)
               if (v := visual_for(i, b, filters_for(b.get("Entity"), old_filters, names))) is not None]
    loose = [v for v in visuals if "x" not in v]
    x = 0
    for v in loose:                       # cards without a saved position came first on the old page
        if x + v["w"] > 12:
            x = 0
        v["x"], v["y"] = x, -1
        x += v["w"]
    compact(visuals)
    return en.normalize_spec({"pages": [{"id": "p1", "title": "Statistics", "filters": [], "visuals": visuals}],
                              "active": "p1"})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["prod", "dev", "dev_local"])
    ap.add_argument("--apply", action="store_true", help="write (without: dry run)")
    ap.add_argument("--owner", type=int, default=None, help="owner of the template dashboard if no layouts exist")
    args = ap.parse_args()
    os.environ["TRIPPLET_MODE"] = args.mode
    sys.path.insert(0, ROOT)
    from db.connection import execute, execute_insert, fetch_all, table_exists
    from db import smart_chart_views as views

    if not views.shares_available():
        print("tblSmartChartView / tblSmartChartViewShare missing - nothing done.")
        return 1
    su = fetch_all("SELECT ID FROM tblAccessRight WHERE AccessLevel >= 4 ORDER BY AccessLevel DESC")
    su_group = int(su[0]["ID"]) if su else None
    lookup = lambda sql: {int(r["i"]): str(r["n"] or "").strip() for r in fetch_all(sql)}
    names = {"machine": lookup("SELECT ID AS i, Maschine AS n FROM tblMaschine"),
             "productgroup": lookup("SELECT ID AS i, Produktgruppe AS n FROM tblproduktgruppe"),
             "ordertype": lookup("SELECT ID AS i, Bestellungstyp AS n FROM tblbestellungstyp")}
    plans = []
    if table_exists("tblStatsDashboardBlock"):
        blocks = fetch_all("SELECT UserID, Entity, GroupBy, TimeGranularity, GridX, GridY, GridW, GridH "
                           "FROM tblStatsDashboardBlock ORDER BY UserID, SortOrder, ID")
        filt = {}
        if table_exists("tblStatsDashboardFilter"):
            for r in fetch_all("SELECT UserID, FiltersJSON FROM tblStatsDashboardFilter"):
                try:
                    filt[int(r["UserID"])] = json.loads(r.get("FiltersJSON") or "{}") or {}
                except ValueError:
                    filt[int(r["UserID"])] = {}
        for uid in sorted({int(b["UserID"]) for b in blocks if b.get("UserID") is not None}):
            mine = [b for b in blocks if b.get("UserID") is not None and int(b["UserID"]) == uid]
            plans.append((uid, NAME, build_spec(mine, filt.get(uid, {}), names), len(mine), filt.get(uid, {})))
    if not plans:
        from ui import smart_dashboard_engine as en
        owner = args.owner
        if owner is None:
            rows = fetch_all("SELECT u.ID FROM tblUser u JOIN tblAccessRight a ON a.ID = u.AccessRights "
                             "WHERE a.AccessLevel >= 4 AND COALESCE(u.Active, 1) <> 0 ORDER BY u.ID")
            owner = int(rows[0]["ID"]) if rows else None
        if owner is None:
            print("No saved layouts and no superuser found - nothing done.")
            return 1
        plans.append((owner, TEMPLATE_NAME, en.template_spec("stats"), 0, {}))

    users = {int(r["ID"]): f"{r.get('FirstName') or ''} {r.get('LastName') or ''}".strip()
             for r in fetch_all("SELECT ID, FirstName, LastName FROM tblUser")}
    now = datetime.datetime.now().replace(microsecond=0)
    for uid, name, spec, n_blocks, old in plans:
        exists = fetch_all("SELECT ID FROM tblSmartChartView WHERE UserID = ? AND Name = ?", [uid, name])
        vis = spec["pages"][0]["visuals"]
        print(f"{users.get(uid, uid)}: {name!r} - {n_blocks} old cards -> {len(vis)} visuals "
              f"({', '.join(v['type'] for v in vis)}); old filters {old or 'none'}"
              + ("  [already there, skipped]" if exists else ""))
        for v in vis:
            print(f"     {v['type']:6s} {v['agg']:18s} {v['wells']}  filters={v['filters']}  at {v['x']},{v['y']} "
                  f"{v['w']}x{v['h']}")
        if exists or not args.apply:
            continue
        cfg = {"mode": "dashboard", "filters": [], "ply_scope": "any", "dashboard": spec}
        vid = execute_insert("INSERT INTO tblSmartChartView (Name, UserID, IsShared, ConfigJSON, CreatedAt) "
                             "VALUES (?,?,?,?,?)", [name, uid, 0, json.dumps(cfg, separators=(",", ":")), now])
        if su_group is not None:
            execute("INSERT INTO tblSmartChartViewShare (ViewID, UserID, AccessRightID, CanEdit, CreatedAt) "
                    "VALUES (?,?,?,?,?)", [int(vid), None, su_group, 0, now])
        print(f"     -> created view {vid}, shared with group superuser (view)")
    if not args.apply:
        print("\nDry run - nothing written. Add --apply to create the dashboards.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
