# db/jets_admin.py
"""Manage Jets / New Jet - Qt-free, shared by the desktop (main.py, ui/screen_manage_jets.py,
ui/screen_new_jet.py) and the web app.

Moved out of main.py and the screens on 2026-11-13 without behaviour change (same SQL, same
order, same rules); the screens keep only their widgets and messages.

    can_edit(user)              Admin card write right (AccessLevel >= 3 or tblUser.AdminBox)
    FK_DEF / fk_maps()          dropdown lists of the FK columns {canon key: {id_to_name, name_to_id}}
    load_jets()                 tblDTYJets rows + has_files + UsedInTrial (computed)
    save_changes(rows)          UPDATE per row (only real columns)
    insert_jet(data, user_id)   new jet (copy / New Jet form), GlobalID + CreatedBy/CreationDate set fresh
    delete_jets(ids)            DELETE (as before: no usage check)
    jet_name_available(name)    unique "Jet" name
    quick_add_fk_value(col, name)  new master value from the "+" of a FK dropdown
    jet_usage(jet_id)           series (+ trials with yarns / overfeed / speed) that use the jet
    files: files_root(), list_files(), add_file(), remove_file(), file_path()
"""
from __future__ import annotations

import datetime
import os
from decimal import Decimal
from typing import Any, Dict, List, Optional

from db.connection import execute, execute_insert, fetch_all, new_global_id
from db.trial_reference import exclude_references_sql
from ui.text_normalize import canon_with_id_strip as _canon

TABLE = "tblDTYJets"
ID_COL = "ID"
SYNTHETIC = {"__has_files__", "has_files", "UsedInTrial"}   # computed, never written
AUDIT_COLS = ("createdby", "creationdate")                  # set on insert, superuser-only, never edited
COMPUTED_COLS = ("usedintrial",)
HIDDEN_IN_FORM = {"globalid", "usedintrial"}
BOOL_COLUMNS = {"Gebogener Kanal"}                           # desktop: bool_columns (canon compare)

FK_DEF = [
    # FK key (canon), FK column in tblDTYJets, master table, ID field, display field
    ("hersteller", "Hersteller", "tblJetHersteller", "ID", "Hersteller"),
    ("serie", "Serie", "tblDTYSeries", "ID", "DTY Series"),
    ("luftkanalform", "Luftkanalform", "tblAirChannelShape", "ID", "Air Channel Shape"),
    ("yarnchannelshape", "Yarn Channel Shape", "tblYarnChannelShape", "ID", "Shape"),
    ("wirbelkammer", "Wirbelkammer", "tblWirbelkammer", "ID", "Wirbelkammer"),
    ("werkstoff", "Werkstoff", "tblWerkstoff", "ID", "Name"),
    ("konusform", "Konus Form", "tblKonusForm", "ID", "KonusForm"),
    # tblJetGroup: label "GroupNumber | GroupName" (like Manage Yarn)
    ("jetgroup", "JetGroupID", "tblJetGroup", "ID", "GroupName"),
    ("rohling", "Rohling", "tblJetRohling", "ID", "Name"),
    ("jettype", "JetTypeID", "tblJetType", "ID", "Name"),
]


def can_edit(user: Optional[dict] = None) -> bool:
    """Admin card write right (app_meta.can_use_admin_box) for ``user`` (default: current user)."""
    if user is None:
        import app_meta
        return bool(app_meta.can_use_admin_box())
    try:
        return int(user.get("access_level") or 0) >= 3 or bool(user.get("admin_box"))
    except Exception:
        return False


def is_bool_column(col: str) -> bool:
    return _canon(col) in {_canon(b) for b in BOOL_COLUMNS}


def fk_maps() -> Dict[str, Dict]:
    """All FK lists from the master tables (every entry, used or not):
    {canon key: {"id_to_name", "name_to_id", "items": [(id, label)]}} - also under
    _canon(FK column) and "createdby" (user names, display only)."""
    maps: Dict[str, Dict] = {}
    for key, jets_fk_col, table, idc, namec in FK_DEF:
        id_to_name: Dict = {}
        name_to_id: Dict = {}
        items: List = []
        t = str(table).strip().lower()
        if t == "tbljetgroup":
            q = (f"SELECT [{idc}] AS [fk_id], [GroupNumber] AS [fk_no], [{namec}] AS [fk_name] "
                 f"FROM [{table}] ORDER BY [GroupNumber], [{namec}]")
        elif t == "tbljetrohling":
            q = (f"SELECT [{idc}] AS [fk_id], [Nummer] AS [fk_no], [{namec}] AS [fk_name] "
                 f"FROM [{table}] ORDER BY [Nummer], [{namec}]")
        else:
            q = f"SELECT [{idc}] AS [fk_id], [{namec}] AS [fk_name] FROM [{table}] ORDER BY [{namec}]"
        try:
            rows = fetch_all(q, [])
        except Exception as e:
            print(f"[FK-LOAD] Fehler für {table}.{namec}: {e}")
            rows = []
        for r in rows or []:
            i, n = r.get("fk_id"), r.get("fk_name")
            if t == "tbljetgroup":
                no = r.get("fk_no")
                n = f"{'' if no is None else str(no).strip()} | {'' if n is None else str(n).strip()}".strip(" |")
            elif t == "tbljetrohling":
                no = r.get("fk_no")
                n = f"{'' if no is None else str(no).strip()} - {'' if n is None else str(n).strip()}".strip(" -")
            if i is None or n is None:
                continue
            id_to_name[i] = n
            id_to_name[str(i)] = n
            try:
                id_to_name[int(i)] = n
            except Exception:
                pass
            name_to_id[str(n)] = i
            items.append((i, str(n)))
        maps[key] = {"id_to_name": id_to_name, "name_to_id": name_to_id, "items": items, "column": jets_fk_col}
        alt_key = _canon(jets_fk_col)
        if alt_key != key:
            maps[alt_key] = maps[key]
    try:
        from db.user_directory import load_user_id_to_name
        maps["createdby"] = {"id_to_name": load_user_id_to_name(), "name_to_id": {}, "items": []}
    except Exception:
        pass
    return maps


def load_jets() -> List[Dict]:
    """tblDTYJets rows with has_files (0/1) and UsedInTrial (computed: used by at least one trial)."""
    sql = """
        SELECT j.*,
               CASE WHEN COUNT(f.ID) > 0 THEN 1 ELSE 0 END AS has_files,
               CASE WHEN EXISTS (SELECT 1 FROM tbltrial t WHERE t.JetID = j.ID)
                    THEN 1 ELSE 0 END AS UsedInTrial
        FROM tblDTYJets j
        LEFT JOIN tblJetFile f ON f.JetID = j.ID
        GROUP BY j.ID
    """
    try:
        return fetch_all(sql, [])
    except Exception:
        # tblJetFile missing
        return fetch_all(
            "SELECT j.*, "
            "CASE WHEN EXISTS (SELECT 1 FROM tbltrial t WHERE t.JetID = j.ID) "
            "THEN 1 ELSE 0 END AS UsedInTrial "
            "FROM tblDTYJets j", [])


def editable_columns(columns) -> List[str]:
    """Columns a user may change: not ID, not computed, not audit."""
    return [c for c in columns if c.lower() != ID_COL.lower() and c not in SYNTHETIC
            and _canon(c) not in AUDIT_COLS and _canon(c) not in COMPUTED_COLS]


def save_changes(rows: List[Dict]) -> int:
    """UPDATE of changed jet rows ({ID, column: value, ...}); returns the number of updated rows."""
    if not rows:
        return 0
    total = 0
    for r in rows:
        if ID_COL not in r:
            raise ValueError(f"Row has no '{ID_COL}' field; cannot save.")
        cols = [c for c in r.keys() if c != ID_COL and c not in SYNTHETIC]
        if not cols:
            continue
        set_sql = ", ".join([f"[{c}] = ?" for c in cols])
        total += execute(f"UPDATE [tblDTYJets] SET {set_sql} WHERE [{ID_COL}] = ?",
                         [r[c] for c in cols] + [r[ID_COL]]) or 0
    return total


def insert_jet(data: Dict, user_id: Any = None) -> int:
    """New jet with full data (New Jet form / copy). ID and computed fields dropped,
    GlobalID if missing, CreatedBy / CreationDate always fresh. Returns the new ID."""
    data = {k: v for k, v in data.items() if k.lower() != ID_COL.lower() and k not in SYNTHETIC}
    if not any(k.lower() == "globalid" for k in data):
        data["GlobalID"] = new_global_id()
    if user_id is None:
        import app_meta
        user_id = (app_meta.current_user or {}).get("id")
    data["CreatedBy"] = user_id
    data["CreationDate"] = datetime.datetime.now()
    cols = list(data.keys())
    sql = (f"INSERT INTO [tblDTYJets] ({', '.join(f'[{c}]' for c in cols)}) "
           f"VALUES ({', '.join('?' for _ in cols)})")
    new_id = execute_insert(sql, [data[c] for c in cols])
    if new_id is None:
        raise RuntimeError("Could not determine the new ID after the insert.")
    return new_id


def delete_jets(ids: List[int]) -> int:
    if not ids:
        return 0
    return execute(f"DELETE FROM [tblDTYJets] WHERE [ID] IN ({','.join(['?'] * len(ids))})", list(ids)) or 0


def jet_name_available(jet_name: str, except_id: Any = None) -> bool:
    """True if no other jet has this "Jet" name (except_id = the jet being edited)."""
    if not jet_name:
        return False
    try:
        if except_id is None:
            rows = fetch_all("SELECT COUNT(*) AS n FROM [tblDTYJets] WHERE [Jet] = ?", [jet_name])
        else:
            rows = fetch_all("SELECT COUNT(*) AS n FROM [tblDTYJets] WHERE [Jet] = ? AND [ID] <> ?",
                             [jet_name, except_id])
    except Exception:
        return True  # do not block in doubt
    if not rows:
        return True
    count = rows[0].get("n")
    if count is None:
        try:
            count = list(rows[0].values())[0]
        except Exception:
            count = 0
    try:
        return int(count) == 0
    except Exception:
        return True


def quick_add_fk_value(col: str, name: str) -> Optional[int]:
    """New entry in the master table of a FK column ("+" next to a dropdown); returns the new ID."""
    name = (name or "").strip()
    if not name:
        return None
    entry = None
    for key, jets_fk_col, table, idc, namec in FK_DEF:
        if jets_fk_col == col or _canon(jets_fk_col) == _canon(col) or key == _canon(col):
            entry = (table, idc, namec)
            break
    if entry is None:
        return None
    table, idc, namec = entry
    execute(f"INSERT INTO [{table}] ([{namec}]) VALUES (?)", [name])
    rows = fetch_all(f"SELECT [{idc}] AS fk_id FROM [{table}] WHERE [{namec}] = ? ORDER BY [{idc}] DESC LIMIT 1", [name])
    return rows[0]["fk_id"] if rows else None


def fmt_num(v) -> Optional[str]:
    """Number for the usage rows: no trailing zeros, None for empty."""
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except Exception:
        return str(v)
    return f"{f:.2f}".rstrip("0").rstrip(".")


def jet_usage(jet_id) -> List[Dict]:
    """Trial series (+ trial numbers) that use this jet via tbltrial.JetID, with per trial the
    yarn(s) (GROUP_CONCAT of the plies), overfeed / speed (ATY: core / effect overfeed)."""
    sql = (
        "SELECT s.ID AS SeriesID, s.ExperimentID AS ExpPK, "
        "e.ExperimentID AS ExperimentIdText, s.SeriesName, m.Maschine AS MachineName, "
        "mt.Maschinentyp AS MachineType, "
        "t.Versuchsnummer, t.Shaft2x_OF AS OverfeedPct, t.SpeedShaft2 AS SpeedMMin, "
        "t.`Shaft1,1Core_OF` AS CoreOfPct, t.`Shaft1,2Effect_OF` AS EffectOfPct, "
        "t.Shaft2Speed AS AtySpeedMMin, "
        "GROUP_CONCAT(COALESCE(NULLIF(y.Kurzname, ''), y.Name) ORDER BY ts.Ply SEPARATOR ' / ') AS YarnNames "
        "FROM tbltrial t "
        "JOIN tbltrialseries s ON s.ID = t.TrialSeriesID "
        "JOIN tblexperimente e ON e.ID = s.ExperimentID "
        "LEFT JOIN tblmaschine m ON m.ID = s.MachineID "
        "LEFT JOIN tblmaschinentypen mt ON mt.ID = m.Maschinentyp "
        "LEFT JOIN tbltrialsettings ts ON ts.TrialID = t.ID "
        "LEFT JOIN tblyarn y ON y.ID = ts.YarnID "
        "WHERE t.JetID = ? AND " + exclude_references_sql("t") + " "
        "GROUP BY t.ID, s.ID, s.ExperimentID, e.ExperimentID, s.SeriesName, m.Maschine, "
        "mt.Maschinentyp, t.Versuchsnummer, t.Shaft2x_OF, t.SpeedShaft2, "
        "t.`Shaft1,1Core_OF`, t.`Shaft1,2Effect_OF`, t.Shaft2Speed "
        "ORDER BY e.ExperimentID, s.SeriesName, t.Versuchsnummer"
    )
    rows = fetch_all(sql, [jet_id])
    series_map: Dict[object, Dict] = {}
    for r in rows:
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
                "vno": vno, "yarn": r.get("YarnNames"), "is_aty": is_aty,
                "of_pct": fmt_num(r.get("OverfeedPct")), "core_of": fmt_num(r.get("CoreOfPct")),
                "effect_of": fmt_num(r.get("EffectOfPct")),
                "speed": fmt_num(r.get("AtySpeedMMin") if is_aty else r.get("SpeedMMin")),
            })
    return list(series_map.values())


# ---------------------------------------------------------------- files (tblJetFile + JetFiles share)
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".gif", ".webp"}


def files_root() -> str:
    """JetFiles folder (any dev database: C:\\ttt\\JetFiles, else the H: share)."""
    try:
        from db.connection import is_dev_mode
        if is_dev_mode():
            return "C:\\ttt\\JetFiles"
    except Exception:
        pass
    return "H:\\Technik\\TrippleT\\JetFiles"


def list_files(jet_id) -> List[Dict]:
    try:
        return fetch_all(
            "SELECT ID, FileName, StoredName, RelativePath, FileType, FileSizeKB, Notes "
            "FROM tblJetFile WHERE JetID = ? ORDER BY UploadedAt DESC", [jet_id])
    except Exception:
        return []


def file_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return "image" if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff") else "pdf" if ext == ".pdf" else "other"


def add_file(jet_id, filename: str, content: bytes, user_id: Any = None) -> None:
    """Stores the bytes as <root>/<jet_id>/<timestamp>_<name> and adds the tblJetFile row."""
    fname = os.path.basename(filename)
    folder = os.path.join(files_root(), str(jet_id))
    os.makedirs(folder, exist_ok=True)
    stored = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{fname}"
    dest = os.path.join(folder, stored)
    with open(dest, "wb") as fh:
        fh.write(content)
    kb = max(1, os.path.getsize(dest) // 1024)
    execute("INSERT INTO tblJetFile (JetID, FileName, StoredName, RelativePath, FileType, FileSizeKB, UploadedBy) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [jet_id, fname, stored, os.path.join(str(jet_id), stored), file_type(fname), kb, user_id])


def remove_file(file_id) -> None:
    """Removes the DB row only (the file on disk stays, as on the desktop)."""
    execute("DELETE FROM tblJetFile WHERE ID = ?", [file_id])


def file_path(file_id) -> Optional[str]:
    rows = fetch_all("SELECT JetID, RelativePath FROM tblJetFile WHERE ID = ?", [file_id])
    if not rows or not rows[0].get("RelativePath"):
        return None
    return os.path.join(files_root(), rows[0]["RelativePath"])


def plain(v: Any) -> Any:
    """Decimal -> float for JSON."""
    return float(v) if isinstance(v, Decimal) else v
