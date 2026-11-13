# db/yarn_admin.py
"""Manage Yarn / New Yarn - Qt-free, shared by the desktop (ui/screen_manage_yarn.py,
ui/screen_new_yarn.py, main.py yarn form callbacks) and the web app.

Moved out of the screens / main.py on 2026-11-13 without behaviour change (same SQL, same rules);
the screens keep their widgets and dialogs.

Rights (no all-or-nothing read-only like Jets):
    everyone with the screen may edit / create; MinStock only superusers (can_edit_minstock),
    delete only with the Admin card right (can_delete = AccessLevel >= 3 or AdminBox).

    load_yarns()                 catalogue yarns (no shadow yarns) + UsedInTrial + StockKg (computed)
    visible_columns(cols, user)  SourceTrialID never, CreatedBy/CreationDate only for superusers
    garntyp_map() / material_map() / colour_map() / yarngroup_map()   (id2name, name2id)
    compute_dpf(endtiter, filaments)
    find_duplicate_yarn(fields, exclude_id)     identical / very similar catalogue yarn
    duplicate_text(match)        the desktop warning text for such a match
    colour lookup: colour_exact(name), colour_similar(name), insert_colour(name)
    save_changes(rows, can_edit_minstock) / insert_yarn(data, user_id, ...) / update_yarn(id, data, ...)
    delete_yarns(ids)
    yarn_usage(yarn_id)          series (+ trials with jet / overfeed / speed) using the yarn
"""
from __future__ import annotations

import datetime
import difflib
from typing import Any, Dict, List, Optional, Tuple

from db.connection import execute, fetch_all, get_columns_map, new_global_id
from ui.text_normalize import canon_simple as _canon, norm as _norm

TABLE = "tblYarn"
ID_COL = "ID"
COMPUTED = {"usedintrial", "stockkg"}          # not tblYarn fields
AUDIT = {"createdby", "creationdate"}          # set on insert, superuser-only, never edited
HIDDEN = {"sourcetrialid"}                     # shadow-yarn link: never shown ("verwirrt nur")
HIDDEN_IN_FORM = {"globalid", "sourcetrialid", "usedintrial", "stockkg"}
DISPLAY_LABELS = {"colourid": "Colour"}        # DB column stays ColourID
COLOUR_SIMILARITY_CUTOFF = 0.75                # calibrated on "blak"/"black", "grey"/"gray"

DUP_CORE_FIELDS = ["Garntyp", "Material", "Titer", "Endtiter", "NumberOfFilaments"]
DUP_COLOUR_FIELD = "ColourID"
DUP_FIELD_LABELS = {"Garntyp": "Garntyp", "Material": "Material", "Titer": "Titer", "Endtiter": "Endtiter",
                    "NumberOfFilaments": "Number of Filaments", "ColourID": "Colour"}


# ---------------------------------------------------------------- rights
def _level(user: Optional[dict]) -> int:
    try:
        return int((user or {}).get("access_level") or 0)
    except Exception:
        return 0


def can_edit_minstock(user: Optional[dict] = None) -> bool:
    """MinStock only for superusers (app_meta.can_edit_min_stock)."""
    if user is None:
        import app_meta
        return bool(app_meta.can_edit_min_stock())
    return _level(user) >= 4


def can_delete(user: Optional[dict] = None) -> bool:
    """Delete = Admin card right (app_meta.can_use_admin_box)."""
    if user is None:
        import app_meta
        return bool(app_meta.can_use_admin_box())
    return _level(user) >= 3 or bool((user or {}).get("admin_box"))


# ---------------------------------------------------------------- columns
def resolve_field(cands: List[str], cols_map: Dict[str, str]) -> Optional[str]:
    """Real column name for one of ``cands`` (exact lowercase, then normalised)."""
    for cand in cands:
        lc = (cand or "").lower()
        if lc in cols_map:
            return cols_map[lc]
    inv = {_norm(k): v for k, v in cols_map.items()}
    for cand in cands:
        nk = _norm(cand)
        if nk in inv:
            return inv[nk]
    return None


def _canon_noparen(s: str) -> str:
    return _canon(s).replace("(", "").replace(")", "")


def special_columns(headers: List[str]) -> Dict[str, Optional[str]]:
    """Column names by role: dpf, endtiter, filaments, minstock, garntyp, material, yarngroup,
    colour, createdby, creationdate, usedintrial, stockkg, name (same detection as the desktop)."""
    out: Dict[str, Optional[str]] = {k: None for k in (
        "dpf", "endtiter", "filaments", "minstock", "garntyp", "material", "yarngroup", "colour",
        "createdby", "creationdate", "usedintrial", "stockkg", "name")}
    for h in headers:
        k = _canon_noparen(h)
        c = _canon(h)
        if out["dpf"] is None and k in {"dpfdtex", "dpf"}:
            out["dpf"] = h
        if out["endtiter"] is None and k in {"endtiterdtex", "endtiter"}:
            out["endtiter"] = h
        if out["filaments"] is None and k in {"numberoffilaments", "filaments", "nofilaments"}:
            out["filaments"] = h
        if out["minstock"] is None and k == "minstock":
            out["minstock"] = h
        if c == "garntyp":
            out["garntyp"] = h
        if c == "material":
            out["material"] = h
        if c in {"yarngroupid", "yarngroup", "groupid"} and (out["yarngroup"] is None or c == "yarngroupid"):
            out["yarngroup"] = h
        if c in {"colourid", "colour", "color", "colorid"}:
            out["colour"] = h
        if c == "createdby":
            out["createdby"] = h
        if out["creationdate"] is None and k == "creationdate":
            out["creationdate"] = h
        if out["usedintrial"] is None and k == "usedintrial":
            out["usedintrial"] = h
        if out["stockkg"] is None and k == "stockkg":
            out["stockkg"] = h
        if out["name"] is None and c == "name":
            out["name"] = h
    return out


def visible_columns(headers: List[str], superuser: bool) -> List[str]:
    headers = [h for h in headers if _canon(h) not in HIDDEN]
    if not superuser:
        headers = [h for h in headers if _canon(h) not in AUDIT]
    return headers


def editable_columns(headers: List[str], minstock: bool) -> List[str]:
    """Columns a user may change (not ID / DPF / computed / audit; MinStock only with the right)."""
    sp = special_columns(headers)
    out = []
    for h in headers:
        c = _canon(h)
        if h.lower() == ID_COL.lower() or h == sp["dpf"] or c in COMPUTED or c in AUDIT or c in HIDDEN:
            continue
        if h == sp["minstock"] and not minstock:
            continue
        out.append(h)
    return out


def compute_dpf(endtiter: Any, filaments: Any) -> Optional[float]:
    """DPF = Endtiter / NumberOfFilaments (None when a value is missing or 0)."""
    try:
        if endtiter in (None, "") or filaments in (None, "", 0, "0"):
            return None
        e = float(str(endtiter).replace(",", "."))
        f = float(str(filaments).replace(",", "."))
        return None if f == 0.0 else e / f
    except Exception:
        return None


# ---------------------------------------------------------------- data
def load_yarns() -> List[Dict]:
    """Catalogue yarns (shadow yarns of the half-product feature excluded) with UsedInTrial
    (used in at least one ply row) and StockKg (sum of spools 'in stock')."""
    src_col = resolve_field(["SourceTrialID"], get_columns_map(TABLE))
    where = f" WHERE y.{src_col} IS NULL" if src_col else ""
    sql = (
        "SELECT y.*, "
        "CASE WHEN EXISTS (SELECT 1 FROM tbltrialsettings ts WHERE ts.YarnID = y.ID) "
        "THEN 1 ELSE 0 END AS UsedInTrial, "
        "COALESCE((SELECT SUM(sp.WeightKg) FROM tblYarnSpool sp "
        "WHERE sp.YarnID = y.ID AND sp.Status = 'in stock'), 0) AS StockKg "
        f"FROM tblYarn y{where}"
    )
    return fetch_all(sql, [])


def all_columns() -> List[str]:
    """Every tblYarn column (also on an empty table), as the desktop form gets them."""
    rows = fetch_all("SELECT * FROM [tblYarn] LIMIT 1", [])
    if rows:
        return list(rows[0].keys())
    return list(get_columns_map(TABLE).values()) or [ID_COL, "Name"]


def _simple_map(table: str, col: str) -> Tuple[Dict, Dict]:
    id2name: Dict = {}
    name2id: Dict = {}
    for r in fetch_all(f"SELECT [ID], [{col}] FROM [{table}] ORDER BY [{col}]", []):
        i, n = r.get("ID"), r.get(col)
        try:
            i = int(i)
        except Exception:
            pass
        id2name[i] = n
        name2id[str(n)] = i
    return id2name, name2id


def garntyp_map() -> Tuple[Dict, Dict]:
    return _simple_map("tblGarntyp", "Garntyp")


def material_map() -> Tuple[Dict, Dict]:
    return _simple_map("tblMaterial", "Material")


def colour_map() -> Tuple[Dict, Dict]:
    return _simple_map("tblColour", "Colour")


def _id_key_variants(v) -> List[object]:
    out: List[object] = []
    if v is None:
        return out
    out.append(v)
    try:
        out.append(int(v))
    except Exception:
        pass
    out.append(str(v))
    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def yarngroup_map() -> Tuple[Dict, Dict]:
    """tblyarngroup: ID -> "<no> - <name>" (name column resolved, it differs between databases)."""
    table = "tblyarngroup"
    cols_map = get_columns_map(table)
    col_id = resolve_field(["ID"], cols_map) or "ID"
    col_name = resolve_field(["Name", "GroupName", "GruppenName", "Bezeichnung"], cols_map) or "Name"
    col_no = resolve_field(["GroupNumber", "GroupNo", "GruppenNummer", "Number", "Nummer"], cols_map)
    sel = [f"[{col_id}] AS ID", f"[{col_name}] AS Name"]
    if col_no:
        sel.append(f"[{col_no}] AS GroupNo")
    order = f"ORDER BY [{col_no}]" if col_no else f"ORDER BY [{col_name}]"
    id2name: Dict = {}
    name2id: Dict = {}
    for r in fetch_all(f"SELECT {', '.join(sel)} FROM [{table}] {order}", []):
        raw_no = r.get("GroupNo") if "GroupNo" in r else None
        name = "" if r.get("Name") is None else str(r.get("Name")).strip()
        try:
            gno = int(str(raw_no).strip()) if raw_no not in (None, "") else None
        except Exception:
            gno = None
        label = f"{gno} - {name}" if (gno is not None and name) else (name or (str(gno) if gno is not None else ""))
        for k in _id_key_variants(r.get("ID")):
            id2name[k] = label
        if label:
            name2id[label] = r.get("ID")
    return id2name, name2id


def fk_lists(headers: List[str]) -> Dict[str, List[Tuple[Any, str]]]:
    """{column: [(id, label)]} for Garntyp, Material, YarnGroup, Colour (in list order)."""
    sp = special_columns(headers)
    out: Dict[str, List[Tuple[Any, str]]] = {}
    loaders = (("garntyp", garntyp_map), ("material", material_map), ("yarngroup", yarngroup_map),
               ("colour", colour_map))
    for role, loader in loaders:
        col = sp[role]
        if not col:
            continue
        try:
            _id2name, name2id = loader()
        except Exception:      # tblColour / tblyarngroup are missing on some databases
            name2id = {}
        out[col] = [(i, n) for n, i in name2id.items()]
    return out


# ---------------------------------------------------------------- duplicates
def _values_equal(a, b) -> bool:
    if a in (None, "") or b in (None, ""):
        return a in (None, "") and b in (None, "")
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return str(a).strip() == str(b).strip()


def find_duplicate_yarn(fields: Dict[str, object], exclude_id: Optional[int] = None):
    """Most similar catalogue yarn to ``fields`` (5 core fields + optional ColourID; colour only
    compared when both sides have one). Only runs when all core fields are set.
    Returns None or (row, diff_count 0|1, diff_fields, compared_fields)."""
    if any(fields.get(c) in (None, "") for c in DUP_CORE_FIELDS):
        return None
    candidate_colour = fields.get(DUP_COLOUR_FIELD)
    rows = fetch_all(
        "SELECT ID, Name, Garntyp, Material, Titer, Endtiter, NumberOfFilaments, ColourID "
        "FROM tblYarn WHERE SourceTrialID IS NULL", [])
    best = None
    for row in rows:
        if exclude_id is not None and _values_equal(row.get("ID"), exclude_id):
            continue
        compared = list(DUP_CORE_FIELDS)
        diff = [c for c in DUP_CORE_FIELDS if not _values_equal(fields.get(c), row.get(c))]
        if candidate_colour not in (None, "") and row.get(DUP_COLOUR_FIELD) is not None:
            compared.append(DUP_COLOUR_FIELD)
            if not _values_equal(candidate_colour, row.get(DUP_COLOUR_FIELD)):
                diff.append(DUP_COLOUR_FIELD)
        if len(diff) > 1:
            continue
        if best is None or len(diff) < best[1]:
            best = (row, len(diff), diff, compared)
    return best


def duplicate_info(match) -> Dict[str, Any]:
    """Parts of the warning for a find_duplicate_yarn() match (the desktop dialog text + data
    for a translated message): {name, id, identical, diff_label, same_labels, text}."""
    row, diff_count, diff_fields, compared = match
    name = row.get("Name") or f"yarn ID {row.get('ID')}"
    same = ", ".join(DUP_FIELD_LABELS.get(c, c) for c in compared if c not in diff_fields)
    if diff_count == 0:
        text = f'An identical yarn already exists: "{name}" (ID {row.get("ID")}) - same {same}.\n\nSave anyway?'
        diff_label = ""
    else:
        diff_label = DUP_FIELD_LABELS.get(diff_fields[0], diff_fields[0])
        text = (f'This yarn is very similar to "{name}" (ID {row.get("ID")}) - only {diff_label} differs '
                f'(rest matches: {same}).\n\nSave anyway?')
    return {"name": name, "id": row.get("ID"), "identical": diff_count == 0, "diff_label": diff_label,
            "same_labels": same, "text": text}


# ---------------------------------------------------------------- colours (quick add)
def colour_exact(name: str) -> Optional[Tuple[int, str]]:
    """Existing colour with the same name (case-insensitive)."""
    n = (name or "").strip().lower()
    for row in fetch_all("SELECT ID, Colour FROM tblColour", []):
        if (row.get("Colour") or "").strip().lower() == n:
            return int(row["ID"]), row["Colour"]
    return None


def colour_similar(name: str) -> Optional[Tuple[int, str]]:
    """A similar but not identical colour name (difflib, COLOUR_SIMILARITY_CUTOFF)."""
    rows = fetch_all("SELECT ID, Colour FROM tblColour", [])
    names = [r["Colour"] for r in rows if r.get("Colour")]
    close = difflib.get_close_matches((name or "").strip().lower(), [n.lower() for n in names], n=1,
                                      cutoff=COLOUR_SIMILARITY_CUTOFF)
    if not close:
        return None
    match = next(n for n in names if n.lower() == close[0])
    row = next(r for r in rows if r["Colour"] == match)
    return int(row["ID"]), row["Colour"]


def insert_colour(name: str) -> Optional[int]:
    """New tblColour row; insert + lastrowid on ONE connection (pooled @@IDENTITY is unreliable)."""
    from db.connection import get_connection
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute("INSERT INTO tblColour (Colour, GlobalID) VALUES (?, ?)", [name.strip(), new_global_id()])
        cn.commit()
        new_id = cur.lastrowid
    return int(new_id) if new_id else None


# ---------------------------------------------------------------- writing
def _writable(data: Dict, headers: List[str], minstock: bool) -> Dict:
    sp = special_columns(headers)
    out = {}
    for k, v in data.items():
        c = _canon(k)
        if k.lower() == ID_COL.lower() or k == sp["dpf"] or c in COMPUTED or c in AUDIT or c in HIDDEN:
            continue
        if k == sp["minstock"] and not minstock:
            continue
        out[k] = v
    return out


def save_changes(rows: List[Dict], can_edit_minstock_: bool) -> int:
    """UPDATE of changed table rows ({ID, column: value}); DPF / computed / audit / MinStock without
    the right are never written. Returns the number of updated rows."""
    total = 0
    for r in rows:
        if ID_COL not in r:
            raise ValueError(f"Row has no '{ID_COL}' field; cannot save.")
        data = _writable(r, list(r.keys()), can_edit_minstock_)
        if not data:
            continue
        cols = list(data.keys())
        total += execute(f"UPDATE [tblYarn] SET {', '.join(f'[{c}] = ?' for c in cols)} WHERE [{ID_COL}] = ?",
                         [data[c] for c in cols] + [r[ID_COL]]) or 0
    return total


def insert_yarn(data: Dict, user_id: Any, can_edit_minstock_: bool) -> Optional[int]:
    """New yarn from the form: Name defaults to "New Yarn", GlobalID / CreatedBy / CreationDate set
    fresh; insert + lastrowid on one connection. Returns the new ID."""
    data = _writable(dict(data), list(data.keys()), can_edit_minstock_)
    data = {k: v for k, v in data.items() if _canon(k) not in ("globalid", "sourcetrialid")}
    if not data.get("Name"):
        data["Name"] = "New Yarn"
    data["GlobalID"] = new_global_id()
    data["CreatedBy"] = user_id
    data["CreationDate"] = datetime.datetime.now()
    cols = list(data.keys())
    sql = (f"INSERT INTO [tblYarn] ({', '.join(f'[{c}]' for c in cols)}) "
           f"VALUES ({', '.join(['?'] * len(cols))})")
    from db.connection import get_connection
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(sql, [data[c] for c in cols])
        cn.commit()
        new_id = cur.lastrowid
    return int(new_id) if new_id else None


def update_yarn(yarn_id: Any, data: Dict, can_edit_minstock_: bool) -> None:
    """UPDATE of one yarn from the form."""
    data = _writable(dict(data), list(data.keys()), can_edit_minstock_)
    data = {k: v for k, v in data.items() if _canon(k) not in ("globalid", "sourcetrialid")}
    if not data:
        return
    cols = list(data.keys())
    execute(f"UPDATE [tblYarn] SET {', '.join(f'[{c}] = ?' for c in cols)} WHERE [ID] = ?",
            [data[c] for c in cols] + [yarn_id])


def delete_yarns(ids: List[Any]) -> int:
    if not ids:
        return 0
    execute(f"DELETE FROM [tblYarn] WHERE [{ID_COL}] IN ({','.join(['?'] * len(ids))})", list(ids))
    return len(ids)


# ---------------------------------------------------------------- usage
def _fmt_num(v) -> Optional[str]:
    """800.00 -> '800', 3.50 -> '3.5'."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f"{f:.0f}" if f == int(f) else f"{f:.1f}"


def yarn_usage(yarn_id) -> List[Dict]:
    """Trial series (+ trials with jet / overfeed / speed; ATY: core / effect overfeed and
    Shaft2Speed) that use this yarn in a ply row (tbltrialsettings.YarnID)."""
    sql = (
        "SELECT s.ID AS SeriesID, s.ExperimentID AS ExpPK, "
        "e.ExperimentID AS ExperimentIdText, s.SeriesName, m.Maschine AS MachineName, "
        "mt.Maschinentyp AS MachineType, "
        "t.Versuchsnummer, j.Jet AS JetName, t.Shaft2x_OF AS OverfeedPct, "
        "t.SpeedShaft2 AS SpeedMMin, t.`Shaft1,1Core_OF` AS CoreOfPct, "
        "t.`Shaft1,2Effect_OF` AS EffectOfPct, t.Shaft2Speed AS AtySpeedMMin "
        "FROM tbltrialsettings ts "
        "JOIN tbltrial t ON t.ID = ts.TrialID "
        "JOIN tbltrialseries s ON s.ID = t.TrialSeriesID "
        "JOIN tblexperimente e ON e.ID = s.ExperimentID "
        "LEFT JOIN tblmaschine m ON m.ID = s.MachineID "
        "LEFT JOIN tblmaschinentypen mt ON mt.ID = m.Maschinentyp "
        "LEFT JOIN tbljets j ON j.ID = t.JetID "
        "WHERE ts.YarnID = ? "
        "ORDER BY e.ExperimentID, s.SeriesName, t.Versuchsnummer"
    )
    series_map: Dict[object, Dict] = {}
    for r in fetch_all(sql, [yarn_id]):
        sid = r.get("SeriesID")
        if sid not in series_map:
            exp_txt = r.get("ExperimentIdText") or ""
            series_name = r.get("SeriesName") or ""
            series_map[sid] = {
                "series_id": sid, "exp_pk": r.get("ExpPK"), "experiment_id_text": exp_txt,
                "label": f"{exp_txt}.{series_name}" if exp_txt else series_name,
                "machine_name": r.get("MachineName"), "trial_numbers": [],
            }
        vno = r.get("Versuchsnummer")
        if vno is None:
            continue
        if vno not in {t["vno"] for t in series_map[sid]["trial_numbers"]}:
            is_aty = r.get("MachineType") == "ATY"
            series_map[sid]["trial_numbers"].append({
                "vno": vno, "jet": r.get("JetName"), "is_aty": is_aty,
                "of_pct": _fmt_num(r.get("OverfeedPct")), "core_of": _fmt_num(r.get("CoreOfPct")),
                "effect_of": _fmt_num(r.get("EffectOfPct")),
                "speed": _fmt_num(r.get("AtySpeedMMin") if is_aty else r.get("SpeedMMin")),
            })
    return list(series_map.values())
