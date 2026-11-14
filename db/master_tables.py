# db/master_tables.py
"""Small admin master tables - Order Type, Product Groups, Material, Top Plates - without Qt (2026-11-13, for the
web version; the desktop screens ui/screen_manage_order_types.py, ui/screen_manage_product_groups.py,
ui/screen_manage_material.py, ui/screen_new_top_plate.py and main.py's top plate functions use it).

Same SQL and rules as before: rows = SELECT * (+ computed columns: Material "UsedInYarn", Top Plates "has_files"),
UPDATE per row with the real columns only, New = a row with an empty name, Delete = DELETE (no usage check, as
before). Top Plates: GlobalID set on insert, unique Name, files in tblTopPlateFile under files_root().
Write right everywhere: Admin card (jets_admin.can_edit = AccessLevel >= 3 or tblUser.AdminBox)."""
from __future__ import annotations

import datetime
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from db.connection import execute, execute_insert, fetch_all, new_global_id


@dataclass(frozen=True)
class Kind:
    key: str
    table: str
    feature: str
    screen_key: str                       # db/user_column_order key (same as the desktop screen)
    name_cols: Tuple[str, ...]            # canon names of the "name" column (gets '' on New)
    synthetic: Tuple[str, ...] = ()       # computed columns, never written
    hidden: Tuple[str, ...] = ()          # real columns not shown / not editable (GlobalID)
    fallback_headers: Tuple[str, ...] = ("ID", "Name")


KINDS: Dict[str, Kind] = {
    "order_types": Kind("order_types", "tblBestellungstyp", "order_type", "manage_order_types",
                        ("bestellungstyp", "ordertype", "name", "bezeichnung"), fallback_headers=("ID", "Bestellungstyp")),
    "product_groups": Kind("product_groups", "tblProduktgruppe", "product_groups", "manage_product_groups",
                           ("produktgruppe", "productgroup", "name", "bezeichnung"), fallback_headers=("ID", "Produktgruppe")),
    "material": Kind("material", "tblMaterial", "material", "manage_material", ("material", "name", "bezeichnung"),
                     synthetic=("UsedInYarn",), fallback_headers=("ID", "Material")),
    "top_plates": Kind("top_plates", "tblTopPlates", "top_plates", "manage_top_plates", ("name",),
                       synthetic=("has_files", "__has_files__"), hidden=("GlobalID",)),
}
ID_COL = "ID"


def _canon(s: str) -> str:
    return "".join(ch for ch in str(s).lower() if ch.isalnum())


def can_edit(user: Optional[dict] = None) -> bool:
    from db import jets_admin
    return jets_admin.can_edit(user)


# ---------------------------------------------------------------------------------------------------- rows
def load_rows(kind: Kind) -> List[Dict[str, Any]]:
    if kind.key == "material":
        # UsedInYarn: shown only - whether a catalogue yarn (half-product shadow yarns excluded) uses the material
        from db.connection import get_columns_map
        from db.yarn_admin import resolve_field
        src_col = resolve_field(["SourceTrialID"], get_columns_map("tblYarn"))
        exclude_shadow = f" AND y.{src_col} IS NULL" if src_col else ""
        return fetch_all("SELECT m.*, CASE WHEN EXISTS (SELECT 1 FROM tblYarn y WHERE y.Material = m.ID"
                         f"{exclude_shadow}) THEN 1 ELSE 0 END AS UsedInYarn FROM tblMaterial m", [])
    if kind.key == "top_plates":
        try:
            return fetch_all("SELECT p.*, CASE WHEN COUNT(f.ID) > 0 THEN 1 ELSE 0 END AS has_files FROM tblTopPlates p "
                             "LEFT JOIN tblTopPlateFile f ON f.TopPlateID = p.ID GROUP BY p.ID", [])
        except Exception:      # tblTopPlateFile missing
            return fetch_all("SELECT * FROM [tblTopPlates]", [])
    return fetch_all(f"SELECT * FROM [{kind.table}]", [])


def real_columns(kind: Kind) -> List[Tuple[str, str]]:
    """[(column, MySQL data type)] of the table (information_schema; the table name as a literal because
    db.connection rewrites legacy table names in SQL text)."""
    return [(r["c"], str(r.get("d") or "").lower()) for r in fetch_all(
        "SELECT COLUMN_NAME AS c, DATA_TYPE AS d FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
        "AND LOWER(TABLE_NAME) = LOWER('" + kind.table + "') ORDER BY ORDINAL_POSITION", [])]


def _id_auto_increment(kind: Kind) -> bool:
    try:
        rows = fetch_all("SELECT EXTRA AS e FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
                         "AND LOWER(TABLE_NAME) = LOWER('" + kind.table + "') AND COLUMN_NAME = 'ID'", [])
    except Exception:
        return True
    return not rows or "auto_increment" in str(rows[0].get("e") or "").lower()


def editable_columns(kind: Kind, columns: List[str]) -> List[str]:
    skip = {_canon(c) for c in (ID_COL,) + kind.synthetic + kind.hidden}
    return [c for c in columns if _canon(c) not in skip]


def save_changes(kind: Kind, rows: List[Dict[str, Any]]) -> int:
    """UPDATE per changed row (only real columns; computed and hidden ones are dropped)."""
    total = 0
    skip = {_canon(c) for c in kind.synthetic + kind.hidden}
    for r in rows:
        if ID_COL not in r:
            raise ValueError(f"Row has no '{ID_COL}' field; cannot save.")
        cols = [c for c in r if c != ID_COL and _canon(c) not in skip]
        if not cols:
            continue
        set_sql = ", ".join(f"[{c}] = ?" for c in cols)
        total += execute(f"UPDATE [{kind.table}] SET {set_sql} WHERE [{ID_COL}] = ?", [r[c] for c in cols] + [r[ID_COL]]) or 0
    return total


def create(kind: Kind, data: Optional[Dict[str, Any]] = None) -> int:
    """New row. Without data: every column NULL, the name column '' (desktop "New"; Top Plates: "New Top Plate").
    With data (Top Plate form / copy): those values; GlobalID is always set fresh for Top Plates."""
    if kind.key == "top_plates":
        vals = {k: v for k, v in (data or {"Name": "New Top Plate"}).items()
                if _canon(k) not in {_canon(ID_COL), "globalid", "hasfiles"}}
        vals["GlobalID"] = new_global_id()
        cols = list(vals)
        return execute_insert(f"INSERT INTO [tblTopPlates] ({', '.join(f'[{c}]' for c in cols)}) "
                              f"VALUES ({', '.join('?' for _ in cols)})", [vals[c] for c in cols])
    cols = [c for c, _t in real_columns(kind) if c.lower() != "id"] or [c for c in kind.fallback_headers if c != ID_COL]
    values = [("" if _canon(c) in kind.name_cols else None) for c in cols]
    if data:
        values = [data.get(c, v) for c, v in zip(cols, values)]
    if not _id_auto_increment(kind):
        # some databases have no AUTO_INCREMENT on the ID (dev_local tblBestellungstyp) - "New" failed there with
        # "Field 'ID' doesn't have a default value"; the next free number is used instead
        rows = fetch_all(f"SELECT COALESCE(MAX([{ID_COL}]), 0) + 1 AS n FROM [{kind.table}]", [])
        new_id = int(list(rows[0].values())[0])
        execute(f"INSERT INTO [{kind.table}] ([{ID_COL}], {', '.join(f'[{c}]' for c in cols)}) "
                f"VALUES ({','.join(['?'] * (len(cols) + 1))})", [new_id] + values)
        return new_id
    return execute_insert(f"INSERT INTO [{kind.table}] ({', '.join(f'[{c}]' for c in cols)}) "
                          f"VALUES ({','.join(['?'] * len(cols))})", values)


def delete(kind: Kind, ids: List[Any]) -> int:
    if not ids:
        return 0
    return execute(f"DELETE FROM [{kind.table}] WHERE [{ID_COL}] IN ({','.join(['?'] * len(ids))})", list(ids)) or 0


def name_available(kind: Kind, name: str, except_id: Any = None) -> bool:
    """Top Plates: the Name must be unique (desktop _is_top_plate_name_available)."""
    if not name:
        return False
    sql, params = "SELECT COUNT(*) AS n FROM [tblTopPlates] WHERE [Name] = ?", [name]
    if except_id is not None:
        sql += " AND [ID] <> ?"
        params.append(except_id)
    try:
        rows = fetch_all(sql, params)
    except Exception:
        return True
    try:
        return int(list(rows[0].values())[0] or 0) == 0
    except Exception:
        return True


# ---------------------------------------------------------------------------------------------------- material usage
def _fmt_num(v) -> Optional[str]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f"{f:.0f}" if f == int(f) else f"{f:.1f}"


def material_usage(material_id) -> List[Dict[str, Any]]:
    """Catalogue yarns (shadow yarns excluded) that use the material: id, name, kurzname, garntyp, titer,
    filaments, colour, label (desktop detail rows)."""
    from db.connection import get_columns_map
    from db.yarn_admin import resolve_field
    cols_map = get_columns_map("tblYarn")
    select_cols = ["ID", "Name"]
    for cand, real in (("kurzname", "Kurzname"), ("garntyp", "Garntyp"), ("titer", "Titer"),
                       ("numberoffilaments", "NumberOfFilaments"), ("colourid", "ColourID")):
        if cand in cols_map:
            select_cols.append(real)
    src_col = resolve_field(["SourceTrialID"], cols_map)
    where = f" AND {src_col} IS NULL" if src_col else ""
    order_by = "ORDER BY COALESCE(NULLIF(Kurzname, ''), Name)" if "Kurzname" in select_cols else "ORDER BY Name"
    rows = fetch_all(f"SELECT {', '.join(select_cols)} FROM tblYarn WHERE Material = ?{where} {order_by}", [material_id])
    try:
        from db.yarn_admin import garntyp_map
        garntyp_id2name, _ = garntyp_map()
    except Exception:
        garntyp_id2name = {}
    try:
        from db.yarn_admin import colour_map
        colour_id2name, _ = colour_map()
    except Exception:
        colour_id2name = {}
    out = []
    for r in rows:
        y = {"id": r.get("ID"), "name": r.get("Name"), "kurzname": r.get("Kurzname"),
             "garntyp": garntyp_id2name.get(r.get("Garntyp")) if r.get("Garntyp") is not None else None,
             "titer": r.get("Titer"), "filaments": r.get("NumberOfFilaments"),
             "colour": colour_id2name.get(r.get("ColourID")) if r.get("ColourID") is not None else None}
        y["label"] = yarn_label(y)
        out.append(y)
    return out


def yarn_label(y: Dict[str, Any]) -> str:
    """"Kurzname - Garntyp, 167 dtex, 48f, colour" (desktop detail row text without the bullet)."""
    name = y.get("kurzname") or y.get("name") or f"Yarn {y.get('id')}"
    parts = []
    if y.get("garntyp"):
        parts.append(str(y["garntyp"]))
    titer = _fmt_num(y.get("titer"))
    if titer is not None:
        parts.append(f"{titer} dtex")
    fils = _fmt_num(y.get("filaments"))
    if fils not in (None, "0"):
        parts.append(f"{fils}f")
    if y.get("colour"):
        parts.append(str(y["colour"]))
    return name + (f" - {', '.join(parts)}" if parts else "")


# ---------------------------------------------------------------------------------------------------- top plate files
def files_root() -> str:
    """TopPlateFiles folder (dev databases: C:\\ttt\\TopPlateFiles, else the H: share; env TRIPPLET_DIR_TOPPLATE_FILES)."""
    from db import file_roots
    return file_roots.folder("TOPPLATE_FILES")


def file_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return "image" if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff") else "pdf" if ext == ".pdf" else "other"


def list_files(top_plate_id) -> List[Dict[str, Any]]:
    try:
        return fetch_all("SELECT ID, FileName, StoredName, RelativePath, FileType, FileSizeKB, Notes, UploadedAt "
                         "FROM tblTopPlateFile WHERE TopPlateID = %s ORDER BY UploadedAt DESC", [top_plate_id])
    except Exception:
        return []


def add_file(top_plate_id, filename: str, content: bytes, user_id: Any = None) -> None:
    """Stores the bytes as <root>/<id>/<timestamp>_<name> and adds the tblTopPlateFile row."""
    fname = os.path.basename(filename)
    folder = os.path.join(files_root(), str(top_plate_id))
    os.makedirs(folder, exist_ok=True)
    stored = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{fname}"
    dest = os.path.join(folder, stored)
    with open(dest, "wb") as fh:
        fh.write(content)
    kb = max(1, os.path.getsize(dest) // 1024)
    execute("INSERT INTO tblTopPlateFile (TopPlateID, FileName, StoredName, RelativePath, FileType, FileSizeKB, UploadedBy) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            [top_plate_id, fname, stored, os.path.join(str(top_plate_id), stored), file_type(fname), kb, user_id])


def remove_file(file_id) -> None:
    """Removes the DB row only (the file on disk stays, as on the desktop)."""
    execute("DELETE FROM tblTopPlateFile WHERE ID = %s", [file_id])


def file_path(file_id) -> Optional[str]:
    rows = fetch_all("SELECT RelativePath FROM tblTopPlateFile WHERE ID = %s", [file_id])
    if not rows or not rows[0].get("RelativePath"):
        return None
    return os.path.join(files_root(), rows[0]["RelativePath"])
