# db/experiment_create.py
"""Create Experiment / Add Trial Series / Add Lab Machines - Qt-free, shared by
the desktop (ui/screen_create_experiment.py) and the web app.

Moved out of the screen on 2026-11-13 without behaviour change (same SQL, same
order, same rules); the screen keeps only its widgets and messages.

Form data (lists for the dropdowns / trees):
    experiments_table()                 -> (table, {year, pg, ot, num, machine, gid, expreq, project}) or None
    product_groups() / order_types()    -> [{"id", "label"}]   ("7 – Name")
    projects()                          -> [{"id", "label"}]   (without the "— none —" entry)
    open_requests()                     -> [{"id", "label"}]   approved (3), not linked, no prior versions
    request_project(request_id)         -> project id of a request or None
    backlog_statuses()                  -> [{"id", "name"}]    only Backlog / In Progress
    next_experiment_number(y, pg, ot)   -> "007"
    existing_experiments()              -> [{"id", "label", "machine_id", ...}]
    series_of_experiment(exp_id)        -> [{"id", "name"}]
    trials_of_series(series_id)         -> [{"id", "number", "label"}]
    machines()                          -> [{"id", "name", "joker"}]
    machine_fields(machine_id)          -> field layout of the Machine tab (tblMachineFields, RDSetting 0)
    yarn_tree() / jet_tree()            -> groups with their yarns / jets
    housings() / yarn_uses()            -> [{"id", "name"}]

Form rules:
    ply_label_for(materials, yarn_id, ply_offset, series_id) -> (label, conflict text or None)
    plan_lab_entries(...)               -> new entries of the Lab Machines list ("+" button)
    can_delete_lab_entry(entries, i, lab_machines) -> False for the Itemat 0.0 baseline while
                                           other variants of that machine are in the list

Writing:
    create(...)              new Experiment + Trial Series + trials (mode "create"), or a new
                             Trial Series + trials in an existing experiment (mode "addseries")
    add_lab_machines(...)    lab rows for chosen trials of an existing series (+ Jet Air rows)
"""
from __future__ import annotations

import datetime
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from db.connection import fetch_all, get_connection, new_global_id
from db.series_tables import get_columns_map, table_exists
from db.trial_reference import format_trial_number
from ui.text_normalize import resolve_field

MAX_PLIES = 5           # rows in the Material list (one row per end)
MAX_PLATES = 20
REQUEST_APPROVED = 3
REQUEST_LINKED = 4      # status of a request once an experiment is created from it
BACKLOG_ID = 1          # joker machines always start in "Backlog"
ITEMAT_TENSIONS = (0.3, 0.6, 1.0, 1.3)

PRESSURE_RE = re.compile(r"^\s*\d+(?:[.,]\d{1,2})?\s*$")
ADD_VALUE_RE = re.compile(r"^\s*[+-]?\d+(?:[.,]\d{1,2})?\s*$")
ADD_CSV_RE = re.compile(r"^\s*[+-]?\d+(?:[.,]\d{1,2})?\s*(,\s*[+-]?\d+(?:[.,]\d{1,2})?\s*)*,?\s*$")
DOUBLE_RE = re.compile(r"^\s*[+-]?\d+(?:[.,]\d{1,3})?\s*$")
SZ_RE = re.compile(r"^\s*(S|Z|SZ)\s*$", re.IGNORECASE)


class Message(str):
    """A user message: the English text (what the desktop shows) plus a code
    and values for translated clients (the web app: "ce.err.<code>")."""
    code: str = ""
    vars: Dict[str, Any] = {}

    def __new__(cls, code: str, text: str, **vars: Any) -> "Message":
        m = super().__new__(cls, text)
        m.code = code
        m.vars = vars
        return m


def _int(s: Any) -> Optional[int]:
    if s is None:
        return None
    st = str(s).strip()
    if st == "":
        return None
    try:
        return int(st)
    except Exception:
        return None


def _float(s: Any) -> Optional[float]:
    if s is None:
        return None
    st = str(s).strip().replace(",", ".")
    if st == "":
        return None
    try:
        return float(st)
    except Exception:
        return None


def _project_table() -> Optional[str]:
    if table_exists("tblProjects"):
        return "tblProjects"
    if table_exists("tblProject"):
        return "tblProject"
    return None


def _group_label(gno: Optional[int], gname: str) -> str:
    if gno is not None and gname:
        return f"{gno} | {gname}"
    if gno is not None:
        return f"{gno} |"
    if gname:
        return f"| {gname}"
    return "Group"


def _load_groups(gtable: str, no_names: Sequence[str], name_names: Sequence[str]) -> List[Dict[str, Any]]:
    """Group rows (tblyarngroup / tbljetgroup) sorted by number (None last)."""
    cmap = get_columns_map(gtable)
    g_id = resolve_field(["ID"], cmap) or "ID"
    g_no = resolve_field(list(no_names), cmap)
    g_name = resolve_field(list(name_names), cmap)
    sel = [f"[{g_id}] AS GID", f"[{g_no}] AS GNo" if g_no else "NULL AS GNo",
           f"[{g_name}] AS GName" if g_name else "NULL AS GName"]
    order = f"ORDER BY [{g_no}] ASC" if g_no else f"ORDER BY [{g_id}] ASC"
    groups = []
    for r in fetch_all(f"SELECT {', '.join(sel)} FROM {gtable} {order}"):
        gid = r.get("GID")
        if gid is None:
            continue
        gno_raw = r.get("GNo")
        gname = str(r.get("GName") or "").strip()
        try:
            gno = int(str(gno_raw).strip()) if gno_raw not in (None, "") else None
        except Exception:
            gno = None
        groups.append({"GID": gid, "GNo": gno, "GName": gname, "Label": _group_label(gno, gname)})
    groups.sort(key=lambda d: (d["GNo"] is None, d["GNo"] if d["GNo"] is not None else 0, str(d["GName"]).lower()))
    return groups


def _children(by_gid: Dict[Any, list], g: Dict[str, Any]) -> list:
    """Members of a group - the group column may hold the group id or (old data) its number."""
    gid = g.get("GID")
    children = by_gid.get(gid, [])
    if not children and gid is not None and g.get("GNo") is not None:
        children = by_gid.get(g["GNo"], [])
    return children


# ====================================================================== form data

def experiments_table() -> Optional[Tuple[str, Dict[str, Optional[str]]]]:
    table = next((t for t in ("tblExperimente", "tblExperiments") if table_exists(t)), None)
    if not table:
        return None
    cmap = get_columns_map(table)
    col_year = resolve_field(["Jahr", "Year"], cmap)
    col_pg = resolve_field(["Produktgruppe", "ProductGroup"], cmap)
    col_ot = resolve_field(["Bestellungstyp", "OrderType"], cmap)
    col_num = resolve_field(["Experimentnummer", "ExperimentNumber"], cmap)
    col_mac = resolve_field(["Maschine", "MachineID", "Machine"], cmap)
    col_gid = resolve_field(["GlobalID"], cmap)
    col_expreq = resolve_field(["ExperimentRequest", "Experiment Request", "RequestID", "ExperimentRequestID"], cmap)
    col_project = resolve_field(["Projekt", "Project", "ProjectID"], cmap)
    if not all([col_year, col_pg, col_ot, col_num]) or not col_mac:
        return None
    return table, {"year": col_year, "pg": col_pg, "ot": col_ot, "num": col_num, "machine": col_mac,
                   "gid": col_gid, "expreq": col_expreq, "project": col_project}


def product_groups() -> List[Dict[str, Any]]:
    return [{"id": r["ID"], "label": f"{r['ID']} – {r['Produktgruppe']}"}
            for r in fetch_all("SELECT ID, Produktgruppe FROM tblProduktgruppe ORDER BY ID")]


def order_types() -> List[Dict[str, Any]]:
    return [{"id": r["ID"], "label": f"{r['ID']} – {r['Bestellungstyp']}"}
            for r in fetch_all("SELECT ID, Bestellungstyp FROM tblBestellungstyp ORDER BY ID")]


def projects() -> List[Dict[str, Any]]:
    table = _project_table()
    if not table:
        return []
    cmap = get_columns_map(table)
    col_id = resolve_field(["ID"], cmap) or "ID"
    col_no = resolve_field(["Project Number", "ProjectNumber", "Projekt Nummer", "ProjektNummer"], cmap)
    col_name = resolve_field(["Project Name", "ProjectName", "Projekt Name", "ProjektName"], cmap)
    if not (col_no and col_name):
        return []
    try:
        rows = fetch_all(f"SELECT [{col_id}] AS PID, [{col_no}] AS PNo, [{col_name}] AS PName "
                         f"FROM [{table}] ORDER BY [{col_no}]")
    except Exception:
        rows = []
    out = []
    for r in rows:
        pid = r.get("PID")
        if pid is None:
            continue
        txt = f"{r.get('PNo')} – {r.get('PName')}".strip(' –') or f"Project {pid}"
        out.append({"id": int(pid), "label": txt})
    return out


def request_project(request_id: Any) -> Optional[int]:
    """Project of an Experiment Request (it always wins over the form's choice)."""
    rid = _int(request_id)
    if rid is None:
        return None
    try:
        req_cols = get_columns_map("tblExperimentRequests")
        col_proj = resolve_field(["Projekt", "Project", "ProjectID"], req_cols)
        if not col_proj:
            return None
        rows = fetch_all(f"SELECT [{col_proj}] AS Projekt FROM [tblExperimentRequests] WHERE [ID]=?", [rid])
        return _int(rows[0].get("Projekt")) if rows else None
    except Exception:
        return None


def open_requests() -> List[Dict[str, Any]]:
    """Approved Experiment Requests (status 3) not linked to an experiment yet,
    label "ProjectNumber - ProjectName - Title". Archived prior versions
    (PriorVersionOfID set) are left out."""
    if not table_exists("tblExperimentRequests"):
        return []
    project_table = _project_table()
    if not project_table:
        return []
    req_cols = get_columns_map("tblExperimentRequests")
    prj_cols = get_columns_map(project_table)
    col_req_id = resolve_field(["ID"], req_cols) or "ID"
    col_req_status = resolve_field(["RequestStatus", "Status"], req_cols) or "RequestStatus"
    col_req_proj = resolve_field(["Projekt", "Project", "ProjectID"], req_cols) or "Projekt"
    col_prj_id = resolve_field(["ID"], prj_cols) or "ID"
    col_prj_no = resolve_field(["Project Number", "ProjectNumber", "Projekt Nummer", "ProjektNummer"], prj_cols)
    col_prj_name = resolve_field(["Project Name", "ProjectName", "Projekt Name", "ProjektName"], prj_cols)
    if not (col_prj_no and col_prj_name):
        return []
    exp_join = exp_where = ""
    resolved = experiments_table()
    if resolved:
        exp_table, exp_cols = resolved
        col_expreq = exp_cols.get("expreq")
        if col_expreq:
            col_exp_id = resolve_field(["ID"], get_columns_map(exp_table)) or "ID"
            exp_join = f"LEFT JOIN [{exp_table}] AS e ON e.[{col_expreq}] = r.[{col_req_id}]\n"
            exp_where = f"AND e.[{col_exp_id}] IS NULL\n"
    col_req_title = resolve_field(["Titel", "Title"], req_cols)
    select_title = f", r.[{col_req_title}] AS ReqTitle" if col_req_title else ""
    version_where = "AND r.[PriorVersionOfID] IS NULL\n" if "priorversionofid" in req_cols else ""
    sql = (
        f"SELECT r.[{col_req_id}] AS RequestID, p.[{col_prj_no}] AS ProjectNo, p.[{col_prj_name}] AS ProjectName"
        f"{select_title}\n"
        f"FROM [tblExperimentRequests] AS r\n"
        f"LEFT JOIN [{project_table}] AS p ON r.[{col_req_proj}] = p.[{col_prj_id}]\n"
        f"{exp_join}"
        f"WHERE 1=1\n"
        f"AND r.[{col_req_status}] = ?\n"
        f"{exp_where}"
        f"{version_where}"
        f"ORDER BY r.[{col_req_id}] DESC"
    )
    try:
        rows = fetch_all(sql, [REQUEST_APPROVED])
    except Exception:
        rows = []
    out = []
    for r in rows:
        rid = r.get("RequestID")
        if rid is None:
            continue
        pno, pname, title = r.get("ProjectNo"), r.get("ProjectName"), r.get("ReqTitle")
        parts = []
        if pno not in (None, '') or pname not in (None, ''):
            base_txt = f"{pno} - {pname}".strip(' -')
            if base_txt:
                parts.append(base_txt)
        if title not in (None, '') and str(title).strip():
            parts.append(str(title).strip())
        out.append({"id": int(rid), "label": ' - '.join(parts).strip(' -') if parts else f"Request {rid}"})
    return out


def backlog_statuses() -> List[Dict[str, Any]]:
    """Statuses a new series may start with: Backlog, In Progress (in that order)."""
    try:
        rows = fetch_all("SELECT ID, BacklogStatus FROM tblBacklogStatus ORDER BY ID")
    except Exception:
        rows = [{"ID": 1, "BacklogStatus": "Backlog"}, {"ID": 2, "BacklogStatus": "In Progress"}]
    wanted = ["Backlog", "In Progress"]
    filtered = [r for r in rows if str(r.get("BacklogStatus", "")).strip() in wanted] or rows
    order = {name: idx for idx, name in enumerate(wanted)}
    filtered.sort(key=lambda r: order.get(str(r.get("BacklogStatus", "")).strip(), 99))
    return [{"id": r.get("ID"), "name": str(r.get("BacklogStatus", "")).strip()} for r in filtered]


def default_backlog_status(statuses: Sequence[Dict[str, Any]]) -> Any:
    for s in statuses:
        if s["name"] == "Backlog":
            return s["id"]
    return statuses[0]["id"] if statuses else None


def next_experiment_number(year: Any, pg: Any, ot: Any) -> str:
    """Next number for Year-PGOT: highest existing + 1, three digits ("" if a part is missing)."""
    if not (str(year or "") and str(pg if pg is not None else "") and str(ot if ot is not None else "")):
        return ""
    resolved = experiments_table()
    if not resolved:
        raise RuntimeError("Experiments table or columns not found.")
    table, cols = resolved
    rows = fetch_all(
        f"SELECT [{cols['num']}] AS Num FROM {table} "
        f"WHERE [{cols['year']}] = ? AND [{cols['pg']}] = ? AND [{cols['ot']}] = ?",
        [str(year), str(pg), str(ot)])
    max_num = 0
    for r in rows:
        try:
            max_num = max(max_num, int(str(r.get("Num")).strip()))
        except Exception:
            continue
    return f"{(max_num + 1):03d}"


def next_free_number(cur, exp_table: str, cols: Dict[str, Any], year: str, pg: Any, ot: Any,
                     preferred_no_txt: str) -> str:
    """Smallest free number >= preferred (inside the save transaction - two
    users creating at the same time)."""
    try:
        cur.execute(
            f"SELECT [{cols['num']}] FROM {exp_table} "
            f"WHERE [{cols['year']}] = ? AND [{cols['pg']}] = ? AND [{cols['ot']}] = ?",
            [year, pg, ot])
        taken = set()
        for row in cur.fetchall():
            try:
                taken.add(int(str(row[0]).strip()))
            except Exception:
                pass
        candidate = int(preferred_no_txt)
        while candidate in taken:
            candidate += 1
        return f"{candidate:03d}"
    except Exception:
        return preferred_no_txt


def parse_legacy_id(text: str) -> Optional[Tuple[str, int, int, str]]:
    """Legacy import 'YYYY-<PGOT>-NNN' (PGOT = product group + order type, the
    last digit is the order type) -> (year, pg, ot, num) or None."""
    m = re.match(r"^(\d{4})-(\d+)-(\d{3})$", (text or "").strip())
    if not m:
        return None
    year, mid, num = m.group(1), m.group(2), m.group(3)
    if len(mid) < 2:
        return None
    try:
        return year, int(mid[:-1]), int(mid[-1]), num
    except Exception:
        return None


def legacy_id_taken(year: Any, pg: Any, ot: Any, num: Any, cur=None) -> bool:
    """True if Year-PG-OT-Number exists already (legacy import must not duplicate it)."""
    resolved = experiments_table()
    if not resolved:
        return False
    table, cols = resolved
    sql = (f"SELECT [{cols['num']}] FROM {table} WHERE [{cols['year']}] = ? AND [{cols['pg']}] = ? "
           f"AND [{cols['ot']}] = ?")
    params = [str(year), pg, ot]
    if cur is not None:
        cur.execute(sql, params)
        nums = [r[0] for r in cur.fetchall()]
    else:
        nums = [list(r.values())[0] for r in fetch_all(sql, params)]
    try:
        want = int(str(num))
    except Exception:
        return str(num) in {str(n) for n in nums}
    for n in nums:
        try:
            if int(str(n).strip()) == want:
                return True
        except Exception:
            pass
    return False


def experiment_label(year: Any, pg: Any, ot: Any, num: Any) -> str:
    """YEAR-PGOT-NNN, e.g. 2025-70-006."""
    try:
        numtxt = f"{int(num):03d}"
    except Exception:
        numtxt = str(num)
    return f"{year}-{str(pg if pg is not None else '').strip()}{str(ot if ot is not None else '').strip()}-{numtxt}"


def existing_experiments() -> List[Dict[str, Any]]:
    resolved = experiments_table()
    if not resolved:
        raise RuntimeError("Experiments table/columns not found.")
    table, cols = resolved
    rows = fetch_all(
        f"SELECT ID AS EID, [{cols['year']}] AS Y, [{cols['pg']}] AS PG, [{cols['ot']}] AS OT, "
        f"[{cols['num']}] AS Num, [{cols['machine']}] AS MID FROM {table} "
        f"ORDER BY [{cols['year']}] DESC, [{cols['pg']}], [{cols['ot']}], [{cols['num']}]")
    return [{"id": int(r["EID"]), "label": experiment_label(r["Y"], r.get("PG"), r.get("OT"), r["Num"]),
             "machine_id": _int(r.get("MID")), "year": r["Y"], "pg": r.get("PG"), "ot": r.get("OT"),
             "num": r["Num"]} for r in rows]


def series_of_experiment(exp_id: int) -> List[Dict[str, Any]]:
    table = "tblTrialSeries"
    if not table_exists(table):
        raise RuntimeError("Table 'tblTrialSeries' not found.")
    cmap = get_columns_map(table)
    col_id = resolve_field(["ID"], cmap) or "ID"
    col_exp = resolve_field(["ExperimentID"], cmap) or "ExperimentID"
    col_name = resolve_field(["SeriesName", "Name"], cmap) or "SeriesName"
    return [{"id": int(r["SID"]), "name": str(r["SName"])} for r in fetch_all(
        f"SELECT [{col_id}] AS SID, [{col_name}] AS SName FROM {table} WHERE [{col_exp}] = ? ORDER BY [{col_id}]",
        [int(exp_id)])]


def series_machine(series_id: int) -> Optional[int]:
    rows = fetch_all("SELECT MachineID AS MID FROM tblTrialSeries WHERE ID = ?", [int(series_id)])
    return _int(rows[0].get("MID")) if rows else None


def trials_of_series(series_id: int) -> List[Dict[str, Any]]:
    if not table_exists("tblTrial"):
        return []
    cmap_t = get_columns_map("tblTrial")
    col_sid = resolve_field(["TrialSeriesID", "SerieID", "SeriesID"], cmap_t) or "TrialSeriesID"
    col_no = resolve_field(["Versuchsnummer", "TrialNumber", "VersuchsNr", "VNr", "Number"], cmap_t) or "Versuchsnummer"
    col_id = resolve_field(["ID"], cmap_t) or "ID"
    out = []
    for r in fetch_all(f"SELECT [{col_id}] AS TID, [{col_no}] AS TNo FROM [tblTrial] "
                       f"WHERE [{col_sid}] = ? ORDER BY [{col_no}]", [int(series_id)]):
        number = str(r.get("TNo") if r.get("TNo") not in (None, '') else r.get("TID"))
        out.append({"id": int(r["TID"]), "number": number, "label": format_trial_number(number)})
    return out


def machines() -> List[Dict[str, Any]]:
    table = "tblMaschine"
    if not table_exists(table):
        raise RuntimeError("Table 'tblMaschine' not found.")
    cmap = get_columns_map(table)
    col_id = resolve_field(["ID"], cmap) or "ID"
    col_name = resolve_field(["Maschine", "Machine", "Name"], cmap)
    if not col_name:
        raise RuntimeError("Column 'Maschine' not found.")
    col_is_joker = resolve_field(["IsJoker", "Is Joker", "Joker"], cmap)
    joker_sel = f", [{col_is_joker}] AS MIsJoker" if col_is_joker else ""
    out = []
    for r in fetch_all(f"SELECT [{col_id}] AS MID, [{col_name}] AS MName{joker_sel} FROM {table} ORDER BY [{col_name}]"):
        is_joker = False
        if "MIsJoker" in r:
            val = r.get("MIsJoker")
            try:
                is_joker = bool(int(val))   # Access style 0/-1
            except Exception:
                is_joker = bool(val)
        out.append({"id": r["MID"], "name": str(r["MName"]), "joker": is_joker})
    return out


def field_kind(fnc: str) -> str:
    """Input kind of a machine field from tblMachineFields.FieldFunction."""
    f = (fnc or "").strip().lower()
    if f == "hidden":
        return "hidden"
    if f.startswith("dropdown:"):
        return "dropdown"
    if f == "onlyinteger":
        return "int"
    if f == "onlydoubles":
        return "double"
    if f.replace(" ", "") in ("onlysz", "onlys,z"):
        return "sz"
    return "text"


def machine_fields(machine_id: Any) -> List[Dict[str, Any]]:
    """Fields of the Machine tab for a machine (tblMachineFields, RDSetting 0,
    hidden fields left out), in the desktop's grid: row = DB row + one gap row
    per earlier group, col = DB column; gap_before = first row of a group
    after the first one. Dropdown fields carry their options [[id, name]]."""
    table = "tblMachineFields"
    if not table_exists(table):
        raise RuntimeError("Table 'tblMachineFields' not found.")
    cmap = get_columns_map(table)
    col_mid = resolve_field(["MachineID", "MaschineID"], cmap) or "MachineID"
    col_fno = resolve_field(["FieldNumber"], cmap) or "FieldNumber"
    col_row = resolve_field(["Row", "Zeile"], cmap) or "Row"
    col_col = resolve_field(["Column", "Spalte"], cmap) or "Column"
    col_group = resolve_field(["Group", "Gruppe"], cmap) or "Group"
    col_name = resolve_field(["FieldName", "Caption"], cmap) or "FieldName"
    col_func = resolve_field(["FieldFunction", "Function"], cmap) or "FieldFunction"
    col_orig = resolve_field(["OriginalName", "Original", "OriginalFieldName"], cmap) or "FieldName"
    col_storage = resolve_field(["StorageTable"], cmap)
    rows = fetch_all(
        f"""
        SELECT [{col_fno}] AS FNo, [{col_row}] AS R, [{col_col}] AS C, [{col_group}] AS G,
               [{col_name}] AS Caption, [{col_func}] AS Fnc, [{col_orig}] AS Orig
               {f', [{col_storage}] AS StorTbl' if col_storage else ', NULL AS StorTbl'}
        FROM {table}
        WHERE [{col_mid}] = ? AND COALESCE(RDSetting, 0) = 0
        ORDER BY [{col_fno}]
        """, [machine_id])
    group_to_minrow: Dict[Any, int] = {}
    for r in rows:
        g = r["G"]
        group_to_minrow[g] = min(group_to_minrow.get(g, int(r["R"] or 0)), int(r["R"] or 0))
    group_start_rows = [gr for gr, _ in sorted(group_to_minrow.items(), key=lambda kv: kv[1])]

    def _offset_for_row(base_row: int) -> int:
        return sum(1 for gr in group_start_rows if group_to_minrow[gr] < base_row)

    out = []
    for r in rows:
        fnc = (r["Fnc"] or "").strip()
        kind = field_kind(fnc)
        if kind == "hidden":
            continue
        r0 = int(r["R"] or 0)
        caption = str(r["Caption"] or "")
        storage = str(r.get("StorTbl") or "tbltrial").strip().lower()
        if storage not in ("tbltrial", "tbltrialsettings"):
            storage = "tbltrial"
        f: Dict[str, Any] = {
            "fno": int(r["FNo"] or 0), "caption": caption, "orig": (r["Orig"] or "").strip() or caption,
            "storage": storage, "kind": kind, "row": r0 + _offset_for_row(r0), "col": max(0, int(r["C"] or 0)),
            "gap_before": r0 == group_to_minrow[r["G"]] and group_start_rows.index(r["G"]) > 0,
        }
        if kind == "dropdown":
            f["options"] = dropdown_options(fnc[len("dropdown:"):].strip())
        out.append(f)
    return out


def dropdown_options(lookup_table: str) -> List[List[Any]]:
    """[[id, name]] of a "dropdown:tblXxx" machine field (name column DiscName / Name / ...)."""
    try:
        lk_cmap = get_columns_map(lookup_table)
        lk_id = resolve_field(["ID"], lk_cmap) or "ID"
        lk_name = resolve_field(["DiscName", "Name", "Bezeichnung", "Caption"], lk_cmap)
        if not lk_name:
            return []
        return [[lk.get("LID"), str(lk.get("LName") or "")] for lk in fetch_all(
            f"SELECT [{lk_id}] AS LID, [{lk_name}] AS LName FROM {lookup_table} ORDER BY [{lk_name}] ASC")]
    except Exception:
        return []


def machine_field_values(machine_id: Any, values: Dict[Any, Any]) -> Tuple[List[Tuple[str, Any]], List[Tuple[str, Any]]]:
    """{field number: text or dropdown id} of the Machine tab -> (tblTrial
    values, tblTrialSettings values) via trial_actions.machine_values().
    Unknown field numbers, dropdown ids outside the list and texts that do
    not fit the field's input rule raise ValueError (the desktop's input
    validators let only those through)."""
    from db.trial_actions import machine_values
    by_fno = {f["fno"]: f for f in machine_fields(machine_id)}
    fields: List[Tuple[str, Any, str]] = []
    for fno, val in (values or {}).items():
        f = by_fno.get(_int(fno))
        if f is None:
            raise ValueError(f"Unknown machine field {fno}.")
        if f["kind"] == "dropdown":
            if val in (None, ""):
                continue
            ids = {o[0] for o in f.get("options", [])}
            lid = _int(val)
            if lid is None or (lid not in ids and str(val) not in {str(i) for i in ids}):
                raise ValueError(f"{f['caption']}: unknown choice.")
            fields.append((f["orig"], lid, f["storage"]))
            continue
        txt = str(val if val is not None else "").strip()
        if not txt:
            continue
        if f["kind"] == "int" and _int(txt) is None:
            raise ValueError(f"{f['caption']}: whole number expected.")
        if f["kind"] == "double" and not DOUBLE_RE.match(txt):
            raise ValueError(f"{f['caption']}: number expected (max. 3 decimals).")
        if f["kind"] == "sz":
            if not SZ_RE.match(txt):
                raise ValueError(f"{f['caption']}: S, Z or SZ expected.")
            txt = txt.upper()
        fields.append((f["orig"], txt, f["storage"]))
    return machine_values(fields)


def yarn_tree() -> Dict[str, Any]:
    """Material tree: {"groups": [{"label", "yarns": [{"id", "name", "colour", "in_stock"}]}],
    "open": label of the group open by default ("1 | Standard Yarn", else the first)}.
    Shadow yarns of "+ Trial" plies (SourceTrialID) are left out."""
    from db.yarn_colours import load_yarn_colours
    from db.yarn_spools import load_stock_summary
    groups = (_load_groups("tblyarngroup", ["GroupNumber", "GruppenNummer", "GroupNo", "Nummer", "Number"],
                           ["GroupName", "GruppenName", "Name", "Bezeichnung"])
              if table_exists("tblyarngroup") else [{"GID": None, "GNo": None, "GName": "", "Label": "Material"}])
    if not table_exists("tblYarn"):
        return {"groups": [], "open": None}
    ycmap = get_columns_map("tblYarn")
    y_id = resolve_field(["ID"], ycmap) or "ID"
    y_name = resolve_field(["Name", "Bezeichnung", "YarnName", "Material"], ycmap)
    y_group = resolve_field(["YarnGroupID", "YarnGroup", "GroupID", "Group"], ycmap)
    y_src_trial = resolve_field(["SourceTrialID"], ycmap)
    where = f" WHERE [{y_src_trial}] IS NULL" if y_src_trial else ""
    if not y_name:
        return {"groups": [], "open": None}
    if y_group:
        yrows = fetch_all(f"SELECT [{y_id}] AS YarnID, [{y_name}] AS YarnName, [{y_group}] AS GID "
                          f"FROM tblYarn{where} ORDER BY [{y_group}] ASC, [{y_name}] ASC")
    else:
        yrows = fetch_all(f"SELECT [{y_id}] AS YarnID, [{y_name}] AS YarnName, NULL AS GID "
                          f"FROM tblYarn{where} ORDER BY [{y_name}] ASC")
    colours, _ = load_yarn_colours()
    stock = load_stock_summary(r.get("YarnID") for r in yrows)
    by_gid: Dict[Any, list] = {}
    for r in yrows:
        by_gid.setdefault(r.get("GID"), []).append(r)
    out = []
    for g in groups:
        yarns = []
        for yr in _children(by_gid, g):
            yid, yname = yr.get("YarnID"), str(yr.get("YarnName") or "").strip()
            if yid is None or not yname:
                continue
            yarns.append({"id": int(yid), "name": yname, "colour": colours.get(int(yid)) or "",
                          "in_stock": stock.get(int(yid)) is not None})
        out.append({"label": g["Label"], "yarns": yarns})
    open_label = next((g["label"] for g in out if g["label"].strip().lower() == "1 | standard yarn"),
                      out[0]["label"] if out else None)
    return {"groups": out, "open": open_label}


def _num_text(val: Any) -> str:
    if val is None or str(val).strip() == "":
        return ""
    try:
        return f"{float(val):.3f}".rstrip("0").rstrip(".")
    except Exception:
        return str(val).strip()


JET_GEO_COLUMNS = ("Luftbohrung", "WinkelLuftbohrung", "GarnkanalBreite", "Luftverbrauch", "Entwicklungsname")


def jet_tree() -> List[Dict[str, Any]]:
    """Jet tree: [{"label", "jets": [{"id", "name", "geo": {Luftbohrung, WinkelLuftbohrung,
    GarnkanalBreite, Luftverbrauch, Entwicklungsname}, "titer_range", "ideal_titer"}]}]
    (tbljetgroup + tbljets, geometry from tblDTYJets; old structure: only tblDTYJets)."""
    groups = (_load_groups("tbljetgroup", ["GroupNumber", "Number", "Nr", "No"], ["GroupName", "Name", "Bezeichnung"])
              if table_exists("tbljetgroup") else [{"GID": None, "GNo": None, "GName": "", "Label": "Jets"}])
    geo_map: Dict[Any, dict] = {}
    try:
        if table_exists("tblDTYJets"):
            geo_cmap = get_columns_map("tblDTYJets")
            geo_id_col = resolve_field(["ID"], geo_cmap) or "ID"
            cols = {
                "Luftbohrung": resolve_field(["Luftbohrung"], geo_cmap),
                "WinkelLuftbohrung": resolve_field(["WinkelLuftbohrung", "Winkel Luftbohrung"], geo_cmap),
                "GarnkanalBreite": resolve_field(["GarnkanalBreite", "Garnkanal Breite", "GarnkanalB"], geo_cmap),
                "Luftverbrauch": resolve_field(["Luftverbrauch"], geo_cmap),
                "Entwicklungsname": resolve_field(["Entwicklungsname"], geo_cmap),
            }
            sel = [f"[{geo_id_col}] AS GeoID"] + [f"[{c}] AS {a}" if c else f"NULL AS {a}" for a, c in cols.items()]
            for gr in fetch_all(f"SELECT {', '.join(sel)} FROM tblDTYJets"):
                if gr.get("GeoID") is not None:
                    geo_map[str(gr["GeoID"])] = gr
    except Exception:
        pass

    if table_exists("tbljets"):
        cmap = get_columns_map("tbljets")
        j_id = resolve_field(["ID"], cmap) or "ID"
        j_name = resolve_field(["Name", "Jet", "Bezeichnung"], cmap)
        j_group = resolve_field(["JetGroupID", "GroupID", "Group"], cmap)
        if not j_name:
            return []
        extra = ", ".join(f"[{c}] AS {a}" if c else f"NULL AS {a}" for a, c in (
            ("TiterVon", resolve_field(["TiterVon"], cmap)), ("TiterBis", resolve_field(["TiterBis"], cmap)),
            ("IdealTiter", resolve_field(["IdealTiter"], cmap))))
        gsel = f"[{j_group}] AS GID" if j_group else "NULL AS GID"
        order = f"[{j_group}] ASC, [{j_name}] ASC" if j_group else f"[{j_name}] ASC"
        jrows = fetch_all(f"SELECT [{j_id}] AS JetID, [{j_name}] AS JetName, {gsel}, {extra} FROM tbljets ORDER BY {order}")
    else:
        if not table_exists("tblDTYJets"):
            return []
        cmap = get_columns_map("tblDTYJets")
        col_id = resolve_field(["ID"], cmap) or "ID"
        col_jet = resolve_field(["Jet", "Name", "Bezeichnung"], cmap)
        col_group = resolve_field(["JetGroupID", "GroupID", "Group"], cmap)
        if not col_jet:
            return []
        gsel = f"[{col_group}] AS GID" if col_group else "NULL AS GID"
        order = f"[{col_group}] ASC, [{col_jet}] ASC" if col_group else f"[{col_jet}] ASC"
        jrows = fetch_all(f"SELECT [{col_id}] AS JetID, [{col_jet}] AS JetName, {gsel}, "
                          f"NULL AS TiterVon, NULL AS TiterBis, NULL AS IdealTiter FROM tblDTYJets ORDER BY {order}")
    by_gid: Dict[Any, list] = {}
    for r in jrows:
        by_gid.setdefault(r.get("GID"), []).append(r)
    out = []
    for g in groups:
        jets = []
        for jt in _children(by_gid, g):
            jid, jname = jt.get("JetID"), str(jt.get("JetName") or "").strip()
            if jid is None or not jname:
                continue
            geo = geo_map.get(str(jid)) or {}
            tvon, tbis, ideal = jt.get("TiterVon"), jt.get("TiterBis"), jt.get("IdealTiter")
            jets.append({
                "id": int(jid), "name": jname,
                "geo": {k: _num_text(geo.get(k)) for k in JET_GEO_COLUMNS},
                "titer_range": f"{tvon} dtex - {tbis} dtex" if (tvon is not None and tbis is not None
                                                                and str(tvon).strip() and str(tbis).strip()) else "",
                "ideal_titer": f"{ideal} dtex" if ideal is not None and str(ideal).strip() else "",
            })
        out.append({"label": str(g.get("Label") or "Group"), "jets": jets})
    return out


def housings() -> List[Dict[str, Any]]:
    if not table_exists("tblHousing"):
        return []
    cmap = get_columns_map("tblHousing")
    col_id = resolve_field(["ID"], cmap) or "ID"
    col_name = resolve_field(["HousingName", "Name", "Bezeichnung"], cmap)
    if not col_name:
        return []
    return [{"id": r["HID"], "name": str(r["HName"])} for r in fetch_all(
        f"SELECT [{col_id}] AS HID, [{col_name}] AS HName FROM tblHousing ORDER BY [{col_name}]")]


def yarn_uses() -> List[Dict[str, Any]]:
    try:
        return [{"id": int(r["ID"]), "name": str(r.get("Name") or "")}
                for r in fetch_all("SELECT ID, Name FROM tblYarnUse ORDER BY ID")]
    except Exception:
        return []


# ====================================================================== form rules

def ply_label_for(materials: Sequence[Dict[str, Any]], yarn_id: Any, ply_offset: int = 0,
                  series_id: Optional[int] = None) -> Tuple[str, Optional[str]]:
    """Ply label for the next added yarn and a conflict text (None = ok).

    Same yarn = same ply (in the series of add trials, and within the list);
    otherwise "Ply <offset + rows + 1>". A ply already used by another yarn
    (series or list) is a conflict - "all trials in a series must use the
    same yarn per ply"."""
    existing: Optional[str] = None
    if series_id:
        try:
            plys = {r["Ply"] for r in fetch_all(
                "SELECT DISTINCT ts.Ply FROM tblTrialSettings ts JOIN tblTrial t ON t.ID = ts.TrialID "
                "WHERE t.TrialSeriesID = ? AND ts.YarnID = ?", [series_id, yarn_id]) if r.get("Ply")}
            if len(plys) == 1:
                existing = next(iter(plys))
        except Exception:
            existing = None
    if existing is None:
        for m in materials:
            if int(m.get("YarnID") or -1) == int(yarn_id):
                existing = m.get("Ply")
                break
    label = existing or f"Ply {ply_offset + len(materials) + 1}"
    if series_id:
        conflict_rows = fetch_all(
            "SELECT DISTINCT y.Name AS YarnName FROM tblTrialSettings ts JOIN tblTrial t ON t.ID = ts.TrialID "
            "JOIN tblYarn y ON y.ID = ts.YarnID WHERE t.TrialSeriesID = ? AND ts.Ply = ? AND ts.YarnID != ?",
            [series_id, label, yarn_id])
        if conflict_rows:
            names = ", ".join(r["YarnName"] for r in conflict_rows)
            return label, Message(
                "ply_conflict_series",
                f"Cannot add this yarn to {label}.\n\nThis ply already has a different yarn in "
                f"this series:\n  {names}\n\nAll trials in a series must use the same yarn per ply.",
                ply=label, yarns=names)
    for m in materials:
        if m.get("Ply") == label and int(m["YarnID"]) != int(yarn_id):
            return label, Message(
                "ply_conflict", f"{label} is already assigned to a different yarn:\n  {m.get('Name', '')}\n\n"
                                f"All trials in a series must use the same yarn per ply.",
                ply=label, yarn=str(m.get('Name', '')))
    return label, None


def renumber_plies(materials: Sequence[Dict[str, Any]], ply_offset: int = 0,
                   series_id: Optional[int] = None) -> List[str]:
    """Ply labels of the list after a row was removed - the rule of
    ply_label_for() applied row by row (same yarn = same ply, otherwise the
    next number), so the ends of one yarn keep one ply."""
    done: List[Dict[str, Any]] = []
    labels: List[str] = []
    for m in materials:
        label, _conflict = ply_label_for(done, m["YarnID"], ply_offset, series_id)
        labels.append(label)
        done.append({**m, "Ply": label})
    return labels


def norm_add_val(v: Any) -> Any:
    """Additional value for comparisons (float rounded to 3 decimals)."""
    if v is None or v == "":
        return None
    try:
        return round(float(str(v).replace(",", ".")), 3)
    except Exception:
        return str(v).strip()


def entry_exists(entries: Sequence[Dict[str, Any]], lm_id: Any, add_norm: Any) -> bool:
    """(lab machine, additional value) already in the list (no value = once per machine)."""
    for r in entries:
        if int(r.get("LMID")) != int(lm_id):
            continue
        existing = r.get("AdditionalVal", None)
        if existing is None:
            existing = norm_add_val((r.get("AdditionalDisp") or "").split(" ")[0])
        else:
            existing = norm_add_val(existing)
        if existing == add_norm:
            return True
    return False


def is_series_freeform(meta: Dict[str, Any]) -> bool:
    """RowMode 'SeriesFreeform' (Jet Air Consumption): no row per trial but jet x pressure per series."""
    return str(meta.get("RowMode") or "").strip().lower() == "seriesfreeform"


def value_needed(table: str, add_src: str, value: float, trial_ids: Sequence[int]) -> bool:
    """Add Lab Machines: True if at least one chosen trial does not have this
    (table, value) row yet - the automatic Itemat 0.0 baseline is left out
    when all chosen trials already have it. Without trials (create / add
    series) always True."""
    if not table or not table_exists(table) or not trial_ids:
        return True
    try:
        lcols = get_columns_map(table)
        col_trial = resolve_field(["TrialID"], lcols) or "TrialID"
        add_real = resolve_field([add_src], lcols) if add_src else None
        ph = ",".join(["?"] * len(trial_ids))
        if add_real:
            rows = fetch_all(f"SELECT DISTINCT [{col_trial}] AS TrialID FROM [{table}] "
                             f"WHERE [{col_trial}] IN ({ph}) AND [{add_real}] = ?", list(trial_ids) + [value])
        else:
            rows = fetch_all(f"SELECT DISTINCT [{col_trial}] AS TrialID FROM [{table}] "
                             f"WHERE [{col_trial}] IN ({ph})", list(trial_ids))
        have = {int(r["TrialID"]) for r in rows}
        return any(int(tid) not in have for tid in trial_ids)
    except Exception:
        return True


def _entry(lm_id: int, name: str, disp: str, val: Any, meta: Dict[str, Any], freeform: bool = False) -> Dict[str, Any]:
    e = {"LMID": lm_id, "Name": name, "AdditionalDisp": disp, "AdditionalVal": val,
         "TableName": (meta.get("Tbl") or "").strip(), "AdditionalFieldSource": (meta.get("Src") or "").strip(),
         "Unit": (meta.get("AddUnit") or "").strip()}
    if freeform:
        e["RowMode"] = "SeriesFreeform"
    return e


def lab_input(meta: Dict[str, Any], mode: str) -> str:
    """Which input the "+" of a lab machine needs: "none" (no additional field,
    or Itemat in add trials = always 0.0), "itemat" (tension boxes + own
    value), "csv" (SeriesFreeform list "4, 5, 6") or "value"."""
    from db.trial_actions import is_itemat
    if not (meta.get("AddField") or "").strip():
        return "none"
    if is_itemat(meta):
        return "none" if mode == "addtrials" else "itemat"
    return "csv" if is_series_freeform(meta) else "value"


def plan_lab_entries(meta: Dict[str, Any], mode: str, entries: Sequence[Dict[str, Any]], text: str = "",
                     tensions: Sequence[float] = (), trial_ids: Sequence[int] = ()) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """The "+" of the Lab Machines tab: the new entries for the list (in
    order) and a message (None = ok; entries may be [] for an exact
    duplicate, as on the desktop). meta = row of trial_actions.load_lab_machines.

    - SeriesFreeform: one entry per comma-separated value (Jet Air Consumption pressures)
    - Itemat in add trials: only the 0.0 baseline
    - Itemat otherwise: 0.0 baseline (once, and in Add Lab Machines only if a
      chosen trial lacks it) + ticked tensions + own value
    - other machines: the value (or nothing without additional field), once per value
    """
    from db.trial_actions import is_itemat
    lm_id = int(meta.get("LMID"))
    name = str(meta.get("LMName") or "").strip()
    caption = (meta.get("AddField") or "").strip()
    unit = (meta.get("AddUnit") or "").strip()
    table = (meta.get("Tbl") or "").strip()
    src = (meta.get("Src") or "").strip()
    needs_additional = bool(caption)
    itemat = is_itemat(meta, name)
    pending = list(entries)
    out: List[Dict[str, Any]] = []

    def add(e):
        out.append(e)
        pending.append(e)

    def has(v):
        return entry_exists(pending, lm_id, norm_add_val(v))

    if is_series_freeform(meta) and needs_additional:
        raw = (text or "").strip()
        if raw == "":
            return [], Message("lab_csv_missing",
                               f"Please enter one or more {caption} values (comma-separated, e.g. 4, 5, 6).",
                               caption=caption)
        parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip() != ""]
        vals, bad = [], []
        for p in parts:
            try:
                vals.append(float(p.replace(",", ".")))
            except Exception:
                bad.append(p)
        if bad:
            return [], Message("lab_csv_bad", f"Invalid values: {', '.join(bad)}. Numbers only, comma-separated.",
                               values=", ".join(bad))
        for val in vals:
            if not has(val):
                add(_entry(lm_id, name, f"{val:g}" + ((" " + unit) if unit else ""), val, meta, freeform=True))
        return out, None

    if mode == "addtrials" and itemat and needs_additional:
        if not has(0.0):
            add(_entry(lm_id, name, "0.0" + ((" " + unit) if unit else ""), 0.0, meta))
        return out, None

    if itemat and needs_additional:
        manual = None
        raw = (text or "").strip()
        if raw:
            if not ADD_VALUE_RE.match(raw):
                return [], Message("lab_value_bad", "Please enter a number (max. 2 decimals).")
            manual = float(raw.replace(",", "."))
        checked = [float(t) for t in tensions]
        if not checked and manual is None:
            return [], Message("lab_tension_missing", "Please tick a tension or enter a value.")
        vals: List[float] = []
        if not has(0.0) and value_needed(table, src, 0.0, trial_ids):
            vals.append(0.0)
        for tv in checked:
            if not has(tv):
                vals.append(tv)
        if manual is not None and not has(manual):
            vals.append(manual)
        for val in vals:
            add(_entry(lm_id, name, f"{val:.1f}" + ((" " + unit) if unit else ""), val, meta))
        return out, None

    add_val: Any = None
    add_disp = ""
    add_norm = None
    if needs_additional:
        raw = (text or "").strip()
        if raw == "":
            return [], Message("lab_value_missing", "Please enter an additional value.")
        if not ADD_VALUE_RE.match(raw):
            return [], Message("lab_value_bad", "Please enter a number (max. 2 decimals).")
        add_val = float(raw.replace(",", "."))
        add_norm = norm_add_val(add_val)
        add_disp = f"{add_val:.2f}".rstrip("0").rstrip(".")
    if entry_exists(pending, lm_id, add_norm):
        return [], None
    disp = add_disp + ((" " + unit) if unit and add_disp else "")
    add(_entry(lm_id, name, disp, add_val, meta))
    return out, None


def can_delete_lab_entry(entries: Sequence[Dict[str, Any]], index: int,
                         lab_machines: Dict[int, Dict[str, Any]]) -> bool:
    """The Itemat 0.0 baseline may only go when no other variant of that machine is in the list."""
    from db.trial_actions import is_itemat
    if not (0 <= index < len(entries)):
        return True
    entry = entries[index]
    lm_id = entry.get("LMID")
    meta = lab_machines.get(int(lm_id)) if lm_id is not None else None
    if not is_itemat(meta or {}, entry.get("Name", "")):
        return True
    if entry.get("AdditionalVal") is None or norm_add_val(entry["AdditionalVal"]) != norm_add_val(0.0):
        return True
    return not any(i != index and d.get("LMID") == lm_id for i, d in enumerate(entries))


def lab_data_from(entries: Sequence[Dict[str, Any]], lab_machines: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Entries sent by a client [{"LMID", "AdditionalVal"}] -> lab_data with
    table / source / row mode taken from the catalog (never from the client:
    the table name goes into SQL). Unknown machines raise ValueError."""
    out = []
    for e in entries:
        meta = lab_machines.get(_int(e.get("LMID")) or -1)
        if meta is None:
            raise ValueError("Unknown lab machine.")
        val = e.get("AdditionalVal")
        if val is not None and not isinstance(val, (int, float)):
            val = _float(val)
            if val is None:
                raise ValueError("Invalid additional value.")
        if not (meta.get("AddField") or "").strip():
            val = None
        out.append({"LMID": int(meta["LMID"]), "Name": str(meta.get("LMName") or "").strip(),
                    "AdditionalVal": val, "TableName": (meta.get("Tbl") or "").strip(),
                    "AdditionalFieldSource": (meta.get("Src") or "").strip(),
                    "Unit": (meta.get("AddUnit") or "").strip(),
                    "RowMode": "SeriesFreeform" if is_series_freeform(meta) else (meta.get("RowMode") or "PerTrial")})
    return out


def check_jet(j: Dict[str, Any]) -> Optional[str]:
    """Rules of the Jet tab "+": housing, jet, 1-20 plates numbered 0-100, pressure (max. 2 decimals)."""
    if j.get("HousingID") is None:
        return "Every jet needs a housing."
    if j.get("JetID") is None:
        return "Jet missing."
    plates = [p.strip() for p in str(j.get("PlateList") or "").split(",") if p.strip()]
    if not 1 <= len(plates) <= MAX_PLATES:
        return f"1 to {MAX_PLATES} plates."
    for p in plates:
        if not p.isdigit() or not 0 <= int(p) <= 100:
            return "Plate numbers 0-100."
    if not PRESSURE_RE.match(str(j.get("Pressure") or "")):
        return "Air pressure: number with max. 2 decimals."
    return None


# ====================================================================== writing

def _insert(cur, table: str, cols: Sequence[str], vals: Sequence[Any]) -> int:
    from db.trial_actions import _insert_and_identity
    ph = ",".join(["?"] * len(cols))
    return _insert_and_identity(cur, f"INSERT INTO {table} ({','.join('[' + c + ']' for c in cols)}) VALUES ({ph})",
                                list(vals))


def series_db_name(cur, exp_id: int, series_name: str, col_exp: str = "ExperimentID") -> str:
    """'01 <name>': two-digit prefix = number of series in the experiment + 1
    (a typed prefix is replaced)."""
    try:
        base_name = re.sub(r'^\s*\d{2}\s+', '', series_name or '').strip()
        cur.execute(f"SELECT COUNT(*) FROM tblTrialSeries WHERE [{col_exp}] = ?", [exp_id])
        row = cur.fetchone()
        cnt = int(row[0]) if row and row[0] is not None else 0
        return f"{cnt + 1:02d} {base_name}".strip() if base_name else f"{cnt + 1:02d}"
    except Exception:
        return series_name


def create(mode: str, *, series_name: str, machine_id: int, jets: Sequence[Dict[str, Any]],
           materials: Sequence[Dict[str, Any]], lab_data: Sequence[Dict[str, Any]],
           trial_values: Sequence[Tuple[str, Any]] = (), settings_values: Sequence[Tuple[str, Any]] = (),
           product_group: Any = None, order_type: Any = None, request_id: Any = None, project_id: Any = None,
           experiment_id: Any = None, backlog_status: Any = None, backlog_prio: Any = None,
           user_id: Any = None, year: Optional[str] = None, legacy_id: Optional[str] = None) -> Dict[str, Any]:
    """Write a new experiment (mode "create") or a new series of an existing
    experiment (mode "addseries", experiment_id) with its trials, in ONE
    transaction (rolled back and re-raised on error).

    legacy (desktop import): like create, but the full experiment id is
      typed (legacy_id 'YYYY-<PGOT>-NNN', parse_legacy_id) and taken as is.
    create: number = next free one for Year-PGOT (year = this year), linked
      request -> its project wins over project_id, request status -> 4.
    series: name with "NN " prefix, CreationDate, backlog status (joker
      machine = always Backlog), prio, owner + CreatedBy = user, MachineID,
      IsJoker / OriginalJoker.
    trials: trial_actions.insert_trials (jets x plates, plies, lab rows,
      Jet Air Consumption rows).
    Returns {"experiment_id", "series_id", "label", "trial_ids"}."""
    from db.trial_actions import insert_trials
    if mode not in ("create", "legacy", "addseries"):
        raise ValueError(f"Unknown mode {mode!r}")
    exp_res = experiments_table()
    if not exp_res:
        raise RuntimeError("Experiments table not found/incomplete.")
    exp_table, exp_cols = exp_res
    if not table_exists("tblTrialSeries"):
        raise RuntimeError("Table 'tblTrialSeries' not found.")
    if not table_exists("tblTrial"):
        raise RuntimeError("Table 'tblTrial' not found.")
    ts_cols = get_columns_map("tblTrialSeries")
    ts_exp = resolve_field(["ExperimentID", "Experiment Id"], ts_cols) or "ExperimentID"
    ts_name = resolve_field(["SeriesName", "Name"], ts_cols) or "SeriesName"
    year_txt = str(year or datetime.datetime.now().year)
    joker = next((m["joker"] for m in machines() if _int(m["id"]) == _int(machine_id)), False)
    label = ""

    cn = None
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute("START TRANSACTION")   # the pool runs autocommit - a real transaction

            if mode == "addseries":
                exp_id = int(experiment_id)
                cur.execute(f"SELECT [{exp_cols['year']}], [{exp_cols['pg']}], [{exp_cols['ot']}], [{exp_cols['num']}] "
                            f"FROM {exp_table} WHERE ID = ?", [exp_id])
                er = cur.fetchone()
                if not er:
                    raise ValueError("Experiment not found.")
                label = experiment_label(er[0], er[1], er[2], er[3])
            else:
                if mode == "legacy":
                    parsed = parse_legacy_id(legacy_id or "")
                    if not parsed:
                        raise ValueError("Invalid experiment ID. Expected: YYYY-<PGOT>-NNN (e.g. 2019-73-002)")
                    year_txt, pg_id, ot_id, exp_no_txt = parsed
                    if legacy_id_taken(year_txt, pg_id, ot_id, exp_no_txt, cur):
                        raise ValueError(Message("legacy_taken", f"Experiment {legacy_id} exists already.",
                                                 id=str(legacy_id)))
                else:
                    pg_id = _int(product_group) or 0
                    ot_id = _int(order_type) or 0
                    exp_no_txt = next_experiment_number(year_txt, pg_id, ot_id)
                    exp_no_txt = next_free_number(cur, exp_table, exp_cols, year_txt, pg_id, ot_id, exp_no_txt)
                exp_id_text = f"{year_txt}-{pg_id}{ot_id}-{exp_no_txt}"
                label = exp_id_text
                fields = [exp_cols['year'], exp_cols['pg'], exp_cols['ot'], exp_cols['num'], 'Experiment ID']
                values: List[Any] = [year_txt, pg_id, ot_id, exp_no_txt, exp_id_text]
                rid = _int(request_id)
                if exp_cols.get('expreq') and rid is not None:
                    fields.append(exp_cols['expreq'])
                    values.append(rid)
                if exp_cols.get('gid'):
                    fields.append(exp_cols['gid'])
                    values.append(new_global_id())
                if exp_cols.get('project'):
                    pid = request_project(rid) if rid is not None else None
                    if pid is None:
                        pid = _int(project_id)
                    if pid is not None:
                        fields.append(exp_cols['project'])
                        values.append(int(pid))
                exp_id = _insert(cur, exp_table, fields, values)
                if rid is not None and table_exists("tblExperimentRequests"):
                    req_cols = get_columns_map("tblExperimentRequests")
                    col_id = resolve_field(["ID"], req_cols) or "ID"
                    col_status = resolve_field(["RequestStatus", "Status"], req_cols) or "RequestStatus"
                    cur.execute(f"UPDATE [tblExperimentRequests] SET [{col_status}] = ? WHERE [{col_id}] = ?",
                                [REQUEST_LINKED, rid])

            fields = [ts_exp, ts_name]
            values = [exp_id, series_db_name(cur, exp_id, series_name, ts_exp)]
            for names, val in (
                (["GlobalID"], new_global_id()),
                (["CreationDate", "Created", "Creation Date", "Creation_Date"], datetime.datetime.now()),
            ):
                col = resolve_field(names, ts_cols)
                if col:
                    fields.append(col)
                    values.append(val)
            status = BACKLOG_ID if joker else _int(backlog_status)
            prio = _int(backlog_prio)
            uid = _int(user_id)
            for names, val in (
                (["BacklogStatusID", "BacklogStatus"], status),
                (["BacklogPrio", "BacklogPriority", "Priority"], prio),
                (["BacklogOwner", "OwnerUserID", "Owner"], uid),
                (["CreatedBy", "Created By", "Created_By", "CreatedByID", "CreatedUserID", "CreatedUser"], uid),
            ):
                col = resolve_field(names, ts_cols)
                if col and val is not None:
                    fields.append(col)
                    values.append(int(val))
            col = resolve_field(["MachineID", "Maschine"], ts_cols)
            if col:
                fields.append(col)
                values.append(_int(machine_id) or 0)
            col = resolve_field(["IsJoker", "Is Joker", "Joker"], ts_cols)
            if col:
                fields.append(col)
                values.append(-1 if joker else 0)
            col = resolve_field(["OriginalJoker", "Original Joker", "OriginalJokerID", "Original Joker ID",
                                 "OriginalJokerMachineID", "Original Joker Machine ID"], ts_cols)
            if col and joker:
                fields.append(col)
                values.append(_int(machine_id) or 0)
            ts_id = _insert(cur, "tblTrialSeries", fields, values)

            trial_ids = insert_trials(cur, ts_id, jets, materials, lab_data, trial_values, settings_values)
            cn.commit()
    except Exception:
        try:
            if cn is not None:
                cn.rollback()
        except Exception:
            pass
        raise
    return {"experiment_id": exp_id, "series_id": ts_id, "label": label, "trial_ids": trial_ids}


def add_lab_machines(series_id: int, trial_ids: Sequence[int], lab_data: Sequence[Dict[str, Any]],
                     user_id: Any = None) -> Dict[str, Any]:
    """Lab rows for the chosen trials of an existing series (one transaction):
    per machine/value a row unless the trial has it already; Waterbath = 3 rows
    on first creation; SeriesFreeform machines -> Jet Air Consumption rows of
    the series. Returns {"created", "skipped", "jet_air": stats}."""
    from db.trial_actions import save_jet_air_consumption_rows
    default_user_id = _int(user_id)
    if default_user_id is None and table_exists("tbluser"):
        try:
            urows = fetch_all("SELECT MIN([ID]) AS uid FROM tbluser")
            if urows and urows[0].get("uid") is not None:
                default_user_id = int(urows[0]["uid"])
        except Exception:
            default_user_id = None
    inserted = skipped = 0
    cn = None
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute("START TRANSACTION")   # the pool runs autocommit - a real transaction
            for lm in lab_data:
                if is_series_freeform(lm):
                    continue    # once per series below
                tbl = (lm.get("TableName") or "").strip()
                if not tbl or not table_exists(tbl):
                    continue
                lcols = get_columns_map(tbl)
                col_trial = resolve_field(["TrialID"], lcols) or "TrialID"
                add_src = (lm.get("AdditionalFieldSource") or "").strip()
                add_real = resolve_field([add_src], lcols) if add_src else None
                add_val = lm.get("AdditionalVal", None)
                if isinstance(add_val, str):
                    m = re.search(r'[-+]?\d+(?:[.,]\d+)?', add_val)
                    add_val = float(m.group(0).replace(',', '.')) if m else add_val
                col_user = resolve_field(["UserID", "User", "CreatedBy", "CreatedByID"], lcols)
                col_gid = resolve_field(["GlobalID"], lcols)

                def row(tid, extra=()):
                    cols, params = [col_trial], [tid]
                    if col_gid:
                        cols.append(col_gid)
                        params.append(new_global_id())
                    for c, v in extra:
                        cols.append(c)
                        params.append(v)
                    if col_user:
                        if default_user_id is None:
                            raise RuntimeError("No valid user found (tbluser). Please log in first or check tbluser.")
                        cols.append(col_user)
                        params.append(default_user_id)
                    cur.execute(f"INSERT INTO [{tbl}] (" + ",".join(f"[{c}]" for c in cols) + ") VALUES ("
                                + ",".join(["?"] * len(params)) + ")", params)

                for tid in trial_ids:
                    if 'waterbath' in tbl.lower():
                        try:
                            cur.execute(f"SELECT COUNT(*) AS Cnt FROM [{tbl}] WHERE [{col_trial}] = ?", [tid])
                            r = cur.fetchone()
                            cnt = int(r[0] if r is not None else 0)
                        except Exception:
                            cnt = 0
                        if cnt == 0:
                            for _ in range(3):
                                row(tid)
                                inserted += 1
                        else:
                            skipped += 1
                        continue
                    try:
                        if add_real:
                            cur.execute(f"SELECT 1 FROM [{tbl}] WHERE [{col_trial}] = ? AND [{add_real}] = ?", [tid, add_val])
                        else:
                            cur.execute(f"SELECT 1 FROM [{tbl}] WHERE [{col_trial}] = ?", [tid])
                        exists = cur.fetchone() is not None
                    except Exception:
                        exists = False
                    if exists:
                        skipped += 1
                        continue
                    row(tid, [(add_real, add_val)] if add_real is not None else ())
                    inserted += 1
            jet_air = save_jet_air_consumption_rows(cur, int(series_id), lab_data)
            cn.commit()
    except Exception:
        try:
            if cn is not None:
                cn.rollback()
        except Exception:
            pass
        raise
    return {"created": inserted, "skipped": skipped, "jet_air": jet_air}


def jet_air_message(stats: Dict[str, int]) -> Optional[str]:
    """The Jet Air Consumption line of the Add Lab Machines message (None = nothing to say)."""
    if not any(stats.values()):
        return None
    if stats["physical_jets"] == 0:
        return "Jet Air Consumption: no physical jet (JetID) found in this series — no rows were created."
    return (f"Jet Air Consumption: {stats['created']} row(s) created, {stats['skipped_exists']} already there, "
            f"{stats['physical_jets']} physical jet(s) found"
            + (f", {stats['no_user']} skipped (no user)" if stats['no_user'] else "") + ".")


# ====================================================================== semi-finished plies ("+ Trial")

_SEARCH_LIMIT = 200  # trial search of "+ Trial"


def search_trials(term: str):
    """Trials whose experiment ID, series name or machine contain every
    word of the search term (case-insensitive, any order, each word may
    match a different field) - newest experiments first."""
    words = term.split()
    if not words:
        return []
    where_parts = []
    params: list = []
    for word in words:
        like = f"%{word}%"
        where_parts.append(
            "(e.[Experiment ID] LIKE ? OR ts.SeriesName LIKE ? OR m.Maschine LIKE ?)"
        )
        params.extend([like, like, like])
    where_sql = " AND ".join(where_parts)
    return fetch_all(
        "SELECT t.ID AS TrialID, t.Versuchsnummer, ts.SeriesName, "
        "e.[Experiment ID] AS ExperimentID, m.Maschine "
        "FROM tbltrial t "
        "JOIN tbltrialseries ts ON ts.ID = t.TrialSeriesID "
        "JOIN tblexperimente e ON e.ID = ts.ExperimentID "
        "LEFT JOIN tblmaschine m ON m.ID = ts.MachineID "
        f"WHERE {where_sql} "
        f"ORDER BY e.[Experiment ID] DESC, t.Versuchsnummer ASC LIMIT {_SEARCH_LIMIT}",
        params,
    )


def trial_label(row) -> str:
    machine = row.get("Maschine") or "?"
    series = row.get("SeriesName") or ""
    vno = row.get("Versuchsnummer")
    exp_id = row.get("ExperimentID") or "?"
    return f"{exp_id} · {series} · V{vno} — {machine}"




def get_or_create_shadow_yarn(trial_id: int) -> Optional[int]:
    """Multimaschinen-Halbfabrikat-Verknüpfung: liefert die YarnID einer
    "Schatten"-tblYarn-Zeile für den Output eines bestimmten Trials, damit er
    als Ply-Input für einen Trial auf einer anderen Maschine referenziert
    werden kann - ohne den bestehenden Ply-Mechanismus (tbltrialsettings.
    YarnID -> tblYarn) anzufassen und ohne für JEDEN tbltrial einen
    Katalog-Eintrag anzulegen (nur lazy, beim tatsächlichen Auswählen).

    Dedup: eine zweite Anfrage für denselben trial_id gibt dieselbe YarnID
    zurück (SourceTrialID ist der eindeutige Schlüssel), statt einen neuen
    Eintrag anzulegen. Material/Titer/Filamentzahl werden vom Eingangsgarn
    des Quell-Trials übernommen, der gemessene Titer des Quell-Trials
    (tbllabortiter, falls vorhanden) überschreibt den kopierten Wert - beides
    nur für Anzeige/Reports relevant, die Ply-Speicherlogik selbst braucht
    nur eine gültige YarnID.
    """
    existing = fetch_all("SELECT ID FROM tblYarn WHERE SourceTrialID = ?", [trial_id])
    if existing:
        return int(existing[0]["ID"])

    trial_rows = fetch_all(
        "SELECT t.Versuchsnummer, ts.SeriesName "
        "FROM tbltrial t JOIN tbltrialseries ts ON ts.ID = t.TrialSeriesID "
        "WHERE t.ID = ?",
        [trial_id],
    )
    if not trial_rows:
        return None
    vno = trial_rows[0].get("Versuchsnummer")
    series_name = trial_rows[0].get("SeriesName") or ""
    name = f"Semi-finished V{vno} ({series_name})".strip()
    # tblYarn.Name ist varchar(45) - lange SeriesNames muessen gekuerzt
    # werden, sonst bricht der INSERT ("Data too long for column 'Name'").
    _NAME_MAXLEN = 45
    if len(name) > _NAME_MAXLEN:
        prefix = f"Semi-finished V{vno} ("
        suffix = ")"
        budget = _NAME_MAXLEN - len(prefix) - len(suffix) - 1  # -1 fuer "…"
        name = f"{prefix}{series_name[:max(budget, 0)]}…{suffix}"

    # Eingangsgarn des Quell-Trials (erste/Haupt-Ply) als Vorlage für
    # Material/Garntyp/Filamentzahl/dpf.
    input_yarn_rows = fetch_all(
        "SELECT y.Material, y.Garntyp, y.NumberOfFilaments, y.dpf, y.Titer, y.Endtiter "
        "FROM tbltrialsettings ts2 JOIN tblYarn y ON y.ID = ts2.YarnID "
        "WHERE ts2.TrialID = ? ORDER BY ts2.ID LIMIT 1",
        [trial_id],
    )
    template = input_yarn_rows[0] if input_yarn_rows else {}

    # Gemessener Titer des Quell-Trials (gleiches AVG-über-Plies-Muster wie
    # report_queries._fetch_y_values) überschreibt den kopierten Titer, falls vorhanden.
    titer_rows = fetch_all(
        "SELECT AVG(Titer) AS val FROM tbllabortiter "
        "WHERE TrialID = ? AND Titer IS NOT NULL AND Titer <> 0",
        [trial_id],
    )
    measured_titer = titer_rows[0]["val"] if titer_rows and titer_rows[0]["val"] is not None else None
    titer = int(round(float(measured_titer))) if measured_titer is not None else template.get("Titer")

    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            "INSERT INTO tblYarn "
            "(Name, Material, Garntyp, NumberOfFilaments, dpf, Titer, Endtiter, GlobalID, SourceTrialID) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            [
                name,
                template.get("Material"),
                template.get("Garntyp"),
                template.get("NumberOfFilaments"),
                template.get("dpf"),
                titer,
                template.get("Endtiter"),
                new_global_id(),
                trial_id,
            ],
        )
        new_id = cur.lastrowid
        try:
            cn.commit()
        except Exception:
            pass
    return int(new_id) if new_id else None


def is_shadow_yarn(yarn_id: Any) -> bool:
    """A "+ Trial" ply yarn (tblYarn.SourceTrialID set) - valid as ply input but not in the catalog tree."""
    try:
        cols = {k.lower() for k in get_columns_map("tblYarn")}
        if "sourcetrialid" not in cols:
            return False
        return bool(fetch_all("SELECT ID FROM tblYarn WHERE ID = ? AND SourceTrialID IS NOT NULL", [int(yarn_id)]))
    except Exception:
        return False


def yarn_name(yarn_id: Any) -> str:
    rows = fetch_all("SELECT Name FROM tblYarn WHERE ID = ?", [int(yarn_id)])
    return str(rows[0]["Name"]) if rows else f"Yarn #{yarn_id}"


# ====================================================================== add trials (Show Experiment "+T")

def addtrials_setup(series_id: int) -> Optional[Dict[str, Any]]:
    """What the add-trials form starts with (desktop open_addtrials_prefill):
    experiment + series (fixed), the series' machine (fixed, fields optional),
    the highest ply number used (new plies count on), the lab machines the
    series' trials use (editable list). Jets start empty - the new trials get
    the jets the user adds. None = series not found."""
    from db.trial_actions import load_lab_machines, series_lab_data, series_ply_offset
    rows = fetch_all("SELECT ID, ExperimentID, SeriesName, MachineID FROM tblTrialSeries WHERE ID = ?", [int(series_id)])
    if not rows:
        return None
    r = rows[0]
    label = ""
    resolved = experiments_table()
    if resolved and r.get("ExperimentID") is not None:
        table, cols = resolved
        er = fetch_all(f"SELECT [{cols['year']}] AS Y, [{cols['pg']}] AS PG, [{cols['ot']}] AS OT, "
                       f"[{cols['num']}] AS N FROM {table} WHERE ID = ?", [r["ExperimentID"]])
        if er:
            label = experiment_label(er[0]["Y"], er[0]["PG"], er[0]["OT"], er[0]["N"])
    catalog = {int(m["LMID"]): m for m in (load_lab_machines() or [])}
    lab = series_lab_data(int(series_id), catalog) or []
    return {"experiment_id": _int(r.get("ExperimentID")), "experiment_label": label,
            "series_id": int(r["ID"]), "series_name": str(r.get("SeriesName") or ""),
            "machine_id": _int(r.get("MachineID")), "ply_offset": series_ply_offset(int(series_id)),
            "lab": lab}
