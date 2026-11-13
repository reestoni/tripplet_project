"""machine_data.py - the data behind Show Experiment's "Machine Data" tab, without Qt.

Moved out of ui/machine_tab.py (build_machine_tab_impl) and
ui/screen_show_experiment.py (_init_machine_cache, jet/housing lookups) on
2026-11-13, so that the desktop screen and the web app (tripplet_web) show
the same cells - same style as db/series_tables.py. Queries and rules are
unchanged, only moved. The desktop turns a MachineData into a
MachinePivotModel (ui/machine_tab.py); widgets, delegates, spans on the
view, signals, radio buttons, the column filter bar and the per-user hidden
rows (QSettings) stay in Qt.

    st = series_tables.load_trials(series_id)
    md = build_machine_data(st, "single")        # "single" / "compact" / "groups"
    md.cells[r][c] -> (raw value, CellBinding | GroupCellBinding | None)
    display_text(md, r, c, jets.map, housings.map) -> text the desktop shows

The R&D Machine Data tab (RDSetting = 1) is built on the same columns:

    rd = build_rd_machine_data(md)               # RDMachineData, rd.visible = tab shown
    rd_display_text(rd, r, c, jets.map, housings.map), rd_tooltip(rd, r, c, ...)
"""
from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from db.connection import fetch_all
from db.series_tables import (
    CellBinding,
    GroupCellBinding,
    SeriesTrials,
    get_columns_map,
    table_exists,
)
from db.trial_reference import reference_label
from db.yarn_colours import colour_css, load_yarn_colours
from ui.text_normalize import canon_rule, norm, resolve_field

VIEW_MODES = ("single", "compact", "groups")

# fixed row titles (top of the table)
FIX_HOUSING = "Housing"
FIX_JET = "Jet"
FIX_PLATE = "Jet Plate Number"
FIX_AIR = "Air Pressure (bar)"
FIX_PLIES = "Plies"
FIX_YARN_USE = "Yarn Use"
FIX_SPOOL = "Spool"
CUSTOM_GROUP_TITLE = "Custom Group"
HOUSING_ROW = 0
JET_ROW = 1

# Computed, read-only row below "T2 Tension" on DTY machines (Nutzerwunsch).
# Calculated live from the T1/T2 cells; stored per ply in
# tblTrialSettings.DYRatio on save (see db/dy_ratio.py).
DY_RATIO_TITLE = "D/Y Ratio (T2/T1)"
DY_RATIO_STORAGE = "computed:dyratio"
DY_RATIO_TOOLTIP = "Calculated: T2 Tension / T1 Tension (not editable)"

# Route / Merge into ply / Merge point on a trial with one ply (ui/dty_schema_panel.py)
SINGLE_PLY_TIP = "Single ply - nothing to merge"


def _text(v: Any) -> str:
    # PivotEditModel.set_cell stores str(value), None -> ""
    return "" if v is None else str(v)


def get_columns_info(table: str) -> List[Dict[str, Any]]:
    """Spalteninfos (MySQL) - data_type/type_name are not known (None)."""
    cmap = get_columns_map(table)
    out: List[Dict[str, Any]] = []
    for lc, real in cmap.items():
        out.append({"lower": lc, "real": real, "data_type": None, "type_name": None})
    return out


# --------------------------------------------------------------------------- D/Y ratio
def dy_ratio_text(t1: Any, t2: Any) -> str:
    """T2/T1 rounded to 2 decimals, "" if a value is missing or T1 is 0 -
    same value that is stored in tblTrialSettings.DYRatio on save."""
    from db.dy_ratio import ratio_text
    return ratio_text(t1, t2)


def insert_dy_ratio_field(field_map: List[Dict], field_validators: List) -> None:
    """Adds the computed D/Y ratio row right after T2 Tension if the machine
    has T1 and T2 Tension as ply fields."""
    def _idx(col: str) -> Optional[int]:
        for i, f in enumerate(field_map):
            if f.get("StorageTable") == "tbltrialsettings" and str(f.get("ColName") or "").lower() == col:
                return i
        return None
    i_t1, i_t2 = _idx("yarntensiont1"), _idx("yarntensiont2")
    if i_t1 is None or i_t2 is None:
        return
    field_map.insert(i_t2 + 1, {"Title": DY_RATIO_TITLE, "ColName": None,
                                "StorageTable": DY_RATIO_STORAGE, "LookupTable": None})
    field_validators.insert(i_t2 + 1, None)


# --------------------------------------------------------------------------- header helpers
def trial_hdr_label(cs: Dict, reference_names: Dict[int, str]) -> str:
    """Trial header text for one column spec - "REF V<n>" for reference
    samples (see db/series_tables.load_trials), else "V<n>"."""
    if int(cs["trial_id"]) in reference_names:
        return reference_label(cs["vno"])
    return f"V{cs['vno']}"


def ply_header_colour(cs: Dict, trial_cs: Dict[int, List[Dict]], compact_mode: bool) -> str:
    """Yarn colour for the colour square in the ply header row ("" = none).
    Compact view with several plies ("div."): only if all plies share it."""
    if not compact_mode:
        return cs.get("yarn_colour") or ""
    colours = {c.get("yarn_colour") or "" for c in trial_cs.get(cs["trial_id"], [cs])}
    return colours.pop() if len(colours) == 1 else ""


def id_display(lookup_map: Dict[Any, str], internal) -> str:
    """Display name for an ID stored in a cell (Housing, Jet, dropdown rows)."""
    if internal is None or str(internal).strip() == "":
        return ""
    # Direkt suchen
    v = lookup_map.get(internal)
    if v is not None:
        return v
    # Als String suchen
    v = lookup_map.get(str(internal))
    if v is not None:
        return v
    # Als int suchen
    try:
        v = lookup_map.get(int(internal))
        if v is not None:
            return v
    except Exception:
        pass
    return str(internal)


# --------------------------------------------------------------------------- lookups (jets, housings)
@dataclass
class JetsLookup:
    list: List[Tuple[Any, str]]            # [(JetID, name)] A-Z - dropdown entries
    map: Dict[Any, str]                    # JetID (int and str key) -> name
    name_to_id: Dict[str, Any]             # name and lower-case name -> JetID (paste)
    tooltip_map: Dict[Any, str]            # JetID (int and str key) -> geometry tooltip


def load_jets_lookup() -> JetsLookup:
    """Lädt alle Jets aus tblDTYJets (ID + Jet-Name, A–Z sortiert)
    sowie Geometrie-Daten für den Hover-Tooltip."""
    out = JetsLookup([], {}, {}, {})
    try:
        rows = fetch_all(
            """
            SELECT [ID], [Jet], [Luftbohrung], [WinkelLuftbohrung], [GarnkanalBreite], [Luftverbrauch], [Entwicklungsname]
            FROM [tblDTYJets]
            ORDER BY [Jet] ASC
            """
        )
    except Exception:
        # Fallback ohne Geometrie-Spalten
        try:
            rows = fetch_all(
                """
                SELECT [ID], [Jet]
                FROM [tblDTYJets]
                ORDER BY [Jet] ASC
                """
            )
        except Exception:
            rows = []
    for r in rows:
        jid = r.get("ID")
        name = r.get("Jet")
        if jid is None:
            continue
        nm = name or ""
        out.list.append((jid, nm))
        # sowohl mit int- als auch mit str-Key zugreifbar
        try:
            out.map[int(jid)] = nm
        except Exception:
            pass
        out.map[str(jid)] = nm
        # Reverse lookup for paste (Jet-Name -> JetID)
        key = str(nm).strip()
        if key:
            out.name_to_id[key] = jid
            out.name_to_id[key.lower()] = jid

        # Geometrie-Tooltip aufbauen
        def _fmt(val, unit, superscript=""):
            if val is None or str(val).strip() == "":
                return "—"
            return f"{val}{superscript} {unit}".strip()

        lines = []
        lb = r.get("Luftbohrung")
        wlb = r.get("WinkelLuftbohrung")
        gb = r.get("GarnkanalBreite")
        lv = r.get("Luftverbrauch")
        if lb is not None: lines.append(f"Luftbohrung:          {_fmt(lb, 'mm')}")
        if wlb is not None: lines.append(f"Winkel Luftbohrung:   {_fmt(wlb, '°')}")
        if gb is not None: lines.append(f"Yarn channel width:   {_fmt(gb, 'mm')}")
        if lv is not None: lines.append(f"Luftverbrauch:        {_fmt(lv, 'Nm³/h')}")
        en = r.get("Entwicklungsname")
        if en is not None and str(en).strip(): lines.append(f"Entwicklungsname:     {en}")
        if lines:
            tip = "\n".join(lines)
            try:
                out.tooltip_map[int(jid)] = tip
            except Exception:
                pass
            out.tooltip_map[str(jid)] = tip
    return out


@dataclass
class HousingLookup:
    list: List[Tuple[Any, str]]            # [(HousingID, name)] A-Z - dropdown entries
    map: Dict[Any, str]                    # HousingID (int and str key) -> name
    image_map: Dict[Any, str]              # HousingID (int and str key) -> image link (tblHousing.Link)


def load_housing_lookup() -> HousingLookup:
    """Lädt alle Housings aus tblHousing (ID + HousingName + Link, A-Z sortiert)."""
    out = HousingLookup([], {}, {})
    try:
        if not table_exists("tblHousing"):
            return out
        cmap = get_columns_map("tblHousing")
        col_id = resolve_field(["ID"], cmap) or "ID"
        col_name = resolve_field(["HousingName", "Name", "Bezeichnung"], cmap)
        if not col_name:
            return out
        col_link = resolve_field(["Link", "link", "Image", "ImagePath", "Bild"], cmap)
        if col_link:
            rows = fetch_all(
                f"SELECT [{col_id}] AS HID, [{col_name}] AS HName, [{col_link}] AS HLink "
                f"FROM tblHousing ORDER BY [{col_name}] ASC"
            )
        else:
            rows = fetch_all(
                f"SELECT [{col_id}] AS HID, [{col_name}] AS HName "
                f"FROM tblHousing ORDER BY [{col_name}] ASC"
            )
    except Exception:
        rows = []
    for r in rows:
        hid = r.get("HID")
        name = r.get("HName") or ""
        if hid is None:
            continue
        out.list.append((hid, str(name)))
        try:
            out.map[int(hid)] = str(name)
        except Exception:
            pass
        out.map[str(hid)] = str(name)
        link = r.get("HLink") or ""
        if str(link).strip():
            try:
                out.image_map[int(hid)] = str(link).strip()
            except Exception:
                pass
            out.image_map[str(hid)] = str(link).strip()
    return out


# --------------------------------------------------------------------------- per-series cache
_MF_QUERY = """SELECT FieldNumber, \
                      FieldName, \
                      FieldFunction, \
                      OriginalName,
                      COALESCE(StorageTable, 'tbltrial') AS StorageTable,
                      COALESCE(RDSetting, 0)             AS RDSetting
               FROM tblMachineFields \
               WHERE MachineID = ?
               ORDER BY FieldNumber, FieldName"""


def has_groups(trial_ids: List[Any]) -> bool:
    """YarnUseIDs vorhanden? (offers the "Groups" view)"""
    try:
        if trial_ids:
            ph = ",".join(["%s"] * len(trial_ids))
            use_rows = fetch_all(
                f"SELECT COUNT(*) AS cnt FROM tblTrialSettings "
                f"WHERE TrialID IN ({ph}) AND YarnUseID IS NOT NULL",
                trial_ids,
            )
            return (use_rows[0]["cnt"] > 0) if use_rows else False
        return False
    except Exception:
        return False


def load_machine_cache(series_pk: Any, trial_ids: List[Any]) -> Dict[str, Any]:
    """Static data of a series for the Machine Data tab (desktop: screen._machine_cache).

    Keys: machine_id, original_joker_id, machine_fields (tblMachineFields rows, plus the
    fields only the Joker machine knows), trial_cols_map, settings_cols_map, yarn_map
    {YarnID: name}, yarn_colour_map {YarnID: colour name}, yarn_use_map {ID: name},
    lookup_maps {LookupTable: {id (int and str key): name}}, has_groups (bool).
    Later code adds is_dty / dty_flags / is_aty lazily."""
    cache: Dict[str, Any] = {}

    # MachineID der Series + OriginalJoker (gesetzt wenn Series von Joker-Maschine kam)
    r = fetch_all(
        "SELECT TS.MachineID, TS.OriginalJoker FROM tblTrialSeries AS TS WHERE TS.ID = ?",
        [series_pk],
    )
    cache["machine_id"] = r[0]["MachineID"] if r else None
    cache["original_joker_id"] = r[0].get("OriginalJoker") if r else None

    # tblMachineFields (aktuelle Maschine)
    try:
        cache["machine_fields"] = fetch_all(
            _MF_QUERY, [cache["machine_id"]],
        ) if cache["machine_id"] else []
    except Exception:
        cache["machine_fields"] = []

    # Falls OriginalJoker gesetzt (Series kam von Joker-Maschine): fehlende Felder ergänzen.
    # Die Joker-Maschine hat ein grosses Feldset; die neue Maschine kennt möglicherweise
    # einzelne Felder (z.B. Winder) nicht. Die Werte liegen aber bereits in tblTrial.
    joker_id = cache.get("original_joker_id")
    if joker_id and joker_id != cache["machine_id"]:
        try:
            joker_fields = fetch_all(_MF_QUERY, [joker_id])
            existing_norms = {norm(f.get("FieldName") or "") for f in cache["machine_fields"]}
            for jf in joker_fields:
                jf_norm = norm(jf.get("FieldName") or "")
                if jf_norm and jf_norm not in existing_norms:
                    cache["machine_fields"].append(jf)
                    existing_norms.add(jf_norm)
        except Exception:
            pass

    # Spalten-Maps
    cache["trial_cols_map"] = get_columns_map("tblTrial")
    cache["settings_cols_map"] = get_columns_map("tblTrialSettings") if table_exists("tblTrialSettings") else {}

    # tblYarn Map
    cache["yarn_map"] = {}
    if table_exists("tblYarn"):
        for yr in fetch_all("SELECT ID, Name FROM tblYarn"):
            try:
                cache["yarn_map"][int(yr["ID"])] = str(yr["Name"] or "")
            except Exception:
                pass
    cache["yarn_colour_map"] = load_yarn_colours()[0]

    # tblYarnUse Map
    cache["yarn_use_map"] = {}
    try:
        for r in fetch_all("SELECT ID, Name FROM tblYarnUse ORDER BY ID"):
            cache["yarn_use_map"][int(r["ID"])] = str(r.get("Name") or "")
    except Exception:
        pass

    # Lookup-Maps pro LookupTable (für dropdown_rows)
    cache["lookup_maps"] = {}
    for fdef in cache["machine_fields"]:
        # LookupTable aus FieldFunction extrahieren (dropdown:tblXxx)
        ff = str(fdef.get("FieldFunction") or "").strip()
        lt = None
        if ff.lower().startswith("dropdown:"):
            lt = ff[len("dropdown:"):].strip() or None
        if not lt or lt in cache["lookup_maps"]:
            continue
        lk_map: Dict[Any, str] = {}
        try:
            if table_exists(lt):
                lk_cmap = get_columns_map(lt)
                lk_id = resolve_field(["ID"], lk_cmap) or "ID"
                lk_name = resolve_field(
                    ["DiscName", "Name", "Bezeichnung", "Caption",
                     "HousingName", "Jet", "JetName", "MaterialName",
                     "YarnName", "Description", "Label"],
                    lk_cmap)
                # DTY process (db/dty_process.py): own order, not alphabetical
                lk_order = (resolve_field(["SortOrder"], lk_cmap) or lk_name) \
                    if lt.lower() == "tbldtyprocess" else lk_name
                if lk_name:
                    for lk in fetch_all(
                            f"SELECT `{lk_id}` AS LID, `{lk_name}` AS LName "
                            f"FROM `{lt}` ORDER BY `{lk_order}` ASC"
                    ):
                        lid = lk.get("LID")
                        lname = str(lk.get("LName") or "")
                        if lid is not None:
                            lk_map[lid] = lname
                            lk_map[str(lid)] = lname
                            try:
                                lk_map[int(lid)] = lname
                            except Exception:
                                pass
        except Exception:
            pass
        cache["lookup_maps"][lt] = lk_map

    # has_groups: YarnUseIDs vorhanden?
    cache["has_groups"] = has_groups(trial_ids)
    return cache


# --------------------------------------------------------------------------- DTY process rows
def filled(v: Any) -> bool:
    """A value counts as entered (ui/dty_schema_panel.py)."""
    return v is not None and str(v).strip() not in ("", "—", "None")


def is_dty_active(cache: Dict[str, Any], row_keys: List[Optional[str]]) -> bool:
    """DTY machine with the DTY Process row (sets cache["is_dty"] once)."""
    if "is_dty" not in cache:
        from db import dty_process
        cache["is_dty"] = dty_process.available() and dty_process.is_dty_machine(cache.get("machine_id"))
    return bool(cache.get("is_dty")) and "dtyprocessid" in (row_keys or [])


def plies_per_trial(col_specs: List[Dict]) -> Dict[Any, int]:
    """{trial id: number of plies} from the Machine Data column specs
    (Groups mode: one column can hold several plies)."""
    out: Dict[Any, int] = {}
    for cs in col_specs or []:
        n = len(cs.get("sr_all") or []) if cs.get("is_group") else (1 if cs.get("sr") else 0)
        out[cs["trial_id"]] = out.get(cs["trial_id"], 0) + n
    return out


def single_ply_merge_cells(row_keys: List[Optional[str]], col_specs: List[Dict],
                           plies: Dict[Any, int], value_at: Callable[[int, int], Any]) -> List[Tuple[int, int]]:
    """Route / Merge into ply / Merge point make no sense for a trial with
    one ply: these (row, col) cells get no binding (= not editable, skipped
    by paste and Fill row) and SINGLE_PLY_TIP. Values already stored stay."""
    from ui import dty_stations as ds
    rows = [r for r, k in enumerate(row_keys) if k in ds.MERGE_KEYS]
    out: List[Tuple[int, int]] = []
    if not rows:
        return out
    for c, cs in enumerate(col_specs or []):
        if plies.get(cs["trial_id"], 0) >= 2:
            continue
        for r in rows:
            if filled(value_at(r, c)):
                continue
            out.append((r, c))
    return out


def process_rules(cache: Dict[str, Any], row_keys: List[Optional[str]], col_specs: List[Dict],
                  n_cols: int, value_at: Callable[[int, int], Any]) -> Tuple[Set[int], List[Tuple[int, int]]]:
    """(rows to hide, merge cells to lock) - pre-jet / jet 3 / merge rows no
    trial needs (ui/dty_stations.process_hidden_rows). Nothing outside DTY."""
    keys = list(row_keys or [])
    if "dtyprocessid" not in keys or not is_dty_active(cache, keys):
        return set(), []
    from db import dty_process
    from ui import dty_stations as ds
    if "dty_flags" not in cache:
        cache["dty_flags"] = dty_process.flags_by_id()
    plies = plies_per_trial(col_specs)
    locked = single_ply_merge_cells(keys, col_specs, plies, value_at)
    hidden = ds.process_hidden_rows(
        keys, n_cols, value_at, keys.index("dtyprocessid"),
        cache["dty_flags"], multi_ply=any(n >= 2 for n in plies.values()))
    return hidden, locked


# --------------------------------------------------------------------------- column filter
def column_label(cs: Dict, groups: bool) -> str:
    """Label of a column in the "Show:" filter (ply or yarn use group)."""
    if groups:
        return str(cs.get("yarn_use_name") or cs.get("ply") or "")
    return str(cs.get("ply") or "")


def hidden_columns(col_specs: List[Dict], compact: bool, groups: bool,
                   checked_labels: Optional[set] = None) -> List[bool]:
    """Per data column: hidden? Compact = only the first column of each trial;
    otherwise the columns whose label is not ticked in the "Show:" filter."""
    out: List[bool] = []
    trial_first_seen: set = set()
    for cs in col_specs:
        tid = cs.get("trial_id")
        lbl = column_label(cs, groups)
        if compact:
            if tid not in trial_first_seen:
                trial_first_seen.add(tid)
                hidden = False
            else:
                hidden = True
        else:
            if checked_labels is not None and lbl:
                hidden = lbl not in checked_labels
            else:
                hidden = False
        out.append(hidden)
    return out


# --------------------------------------------------------------------------- the tab
@dataclass
class MachineData:
    """Machine Data of one series in one view mode. Rows = fixed rows + machine fields
    + Custom Group; columns = one per ply ("single"/"compact") or per yarn use group
    ("groups") of each trial. Row/column indexes are 0-based data indexes (no header rows)."""
    series_id: Any
    view_mode: str                                   # "single" / "compact" / "groups"
    machine_id: Any = None
    message: Optional[str] = None                    # set = no table (desktop shows the text)
    fields: List[Dict[str, Any]] = field(default_factory=list)       # tblMachineFields rows
    fields_rd: List[Dict[str, Any]] = field(default_factory=list)    # RDSetting = 1 (R&D tab)
    field_map: List[Dict[str, Any]] = field(default_factory=list)    # dynamic rows: Title/ColName/StorageTable/LookupTable
    titles_fixed: List[str] = field(default_factory=list)
    row_titles: List[str] = field(default_factory=list)
    row_keys: List[Optional[str]] = field(default_factory=list)
    validators: List[Optional[str]] = field(default_factory=list)
    read_only_rows: List[int] = field(default_factory=list)
    custom_group_row: int = -1
    trial_wide_rows: List[int] = field(default_factory=list)         # one cell per trial (spanned)
    dropdown_rows: Dict[int, Dict[Any, str]] = field(default_factory=dict)   # row -> {id: name} (mixed keys)
    dropdown_lists: Dict[int, List[Tuple[int, str]]] = field(default_factory=dict)  # row -> [(id, name)] entries
    spool_tooltips: Optional[Dict[int, str]] = None  # SpoolID -> full label (single view only)
    col_specs: List[Dict[str, Any]] = field(default_factory=list)    # desktop column specs (full DB rows)
    columns: List[Dict[str, Any]] = field(default_factory=list)      # slim, JSON-friendly column info
    header_rows: List[Dict[str, Any]] = field(default_factory=list)  # trial row + ply row (index 0 = title column)
    cells: List[List[Tuple[Any, Any]]] = field(default_factory=list)  # [row][col] = (value, binding)
    cell_tooltips: Dict[Tuple[int, int], str] = field(default_factory=dict)
    cell_alerts: Dict[Tuple[int, int], str] = field(default_factory=dict)
    dy_ratio: Optional[Tuple[int, int, int]] = None  # (row T1, row T2, row ratio)
    process_hidden_rows: Set[int] = field(default_factory=set)
    trial_spans: List[Tuple[int, int]] = field(default_factory=list)  # (first data col, number of cols)
    has_multi_ply: bool = False
    filter_labels: List[str] = field(default_factory=list)
    has_groups: bool = False
    trial_rows: List[Dict[str, Any]] = field(default_factory=list)   # tblTrial rows (+ JetName)
    settings_cols_map: Dict[str, str] = field(default_factory=dict)
    reference_names: Dict[int, str] = field(default_factory=dict)    # TrialID -> name of the reference samples


def view_mode_flags(view_mode: str) -> Tuple[bool, bool]:
    """(groups, compact)"""
    return view_mode == "groups", view_mode == "compact"


def build_machine_data(st: SeriesTrials, view_mode: str = "single",
                       cache: Optional[Dict[str, Any]] = None) -> MachineData:
    """Everything the Machine Data table shows for a series. cache = load_machine_cache()
    (the desktop passes its screen._machine_cache; it may be completed here: is_dty, dty_flags)."""
    if cache is None:
        cache = load_machine_cache(st.series_id, st.trial_ids)
    machine_id = cache.get("machine_id")
    use_yarn_use_grouping, compact_mode = view_mode_flags(view_mode)
    md = MachineData(series_id=st.series_id, view_mode=view_mode, machine_id=machine_id,
                     has_groups=bool(cache.get("has_groups", False)), reference_names=st.reference_names)

    if not table_exists("tblMachineFields"):
        md.message = "Mapping table 'tblMachineFields' not found."
        return md

    fields = cache.get("machine_fields", [])
    if not fields and machine_id:
        try:
            fields = fetch_all(
                """SELECT FieldNumber,
                          FieldName,
                          FieldFunction,
                          OriginalName,
                          COALESCE(StorageTable, 'tbltrial') AS StorageTable,
                          COALESCE(RDSetting, 0)             AS RDSetting
                   FROM tblMachineFields
                   WHERE MachineID = ?
                   ORDER BY FieldNumber, FieldName""",
                [machine_id],
            )
        except Exception as e:
            md.message = f"Error loading tblMachineFields: {e}"
            return md
    md.fields = fields

    # Felder aufteilen: RDSetting=0 -> Machine Data, RDSetting=1 -> R&D Machine Data,
    # RDSetting=2 -> Machine Data, aber nur ab dieser Version: aeltere exe zeigen
    # nur 0/1 und uebergehen diese Felder (DTY-Verfahren, Merge, Vor-/3. Duese)
    fields_normal = [f for f in fields if int(f.get("RDSetting") or 0) in (0, 2)]
    md.fields_rd = [f for f in fields if int(f.get("RDSetting") or 0) == 1]

    # Trial-Spalten (für exakte Groß/Kleinschreibung)
    trial_cols = cache.get("trial_cols_map") or get_columns_map("tblTrial")

    reserved_titles = [
        "Versuchsnummer", "Housing",
        "Jet", "Jet Name",
        "JetPlate", "Jet Plate Number",
        "Air Pressure (bar)",
        "Yarn Use", "YarnUse", "YarnUseID",
    ]
    reserved_norm = {norm(x) for x in reserved_titles}

    # Für die fixen Felder: Validator + OriginalName (DB-Spalte in tblTrial)
    reserved_validators: Dict[str, Optional[str]] = {
        FIX_PLATE: None, FIX_AIR: None}
    reserved_originals: Dict[str, Optional[str]] = {
        FIX_PLATE: None, FIX_AIR: None}
    reserved_norm.add(norm(FIX_HOUSING))

    seen_norm_titles: set[str] = set()

    # Mapping für alle restlichen Felder (Anzeige = FieldName, Binding = OriginalName)
    # {"Title": FieldName, "ColName": tblTrial-Column}
    field_map: List[Dict[str, Optional[str]]] = []
    field_validators: List[Optional[str]] = []

    for f in fields_normal:
        disp = str(f.get("FieldName") or "").strip()
        orig = str(f.get("OriginalName") or "").strip()
        ff = canon_rule((f.get("FieldFunction") or "").strip() or None)
        if not disp:
            continue

        # hidden-Felder komplett überspringen
        if ff == "hidden":
            continue

        disp_norm = norm(disp)

        if disp_norm in reserved_norm:
            # den passenden fixen Eintrag mit Validator + OriginalName versorgen
            if disp_norm in {norm(FIX_PLATE), norm("JetPlateNumber"), norm("JetPlate")}:
                reserved_validators[FIX_PLATE] = ff
                reserved_originals[FIX_PLATE] = orig or reserved_originals[FIX_PLATE]
            elif disp_norm in {norm(FIX_AIR), norm("AirPressure")}:
                reserved_validators[FIX_AIR] = ff
                reserved_originals[FIX_AIR] = orig or reserved_originals[FIX_AIR]
            continue

        if disp_norm in seen_norm_titles:
            continue

        # OriginalName -> echte Spalten-Schreibweise in tblTrial nachschlagen
        col = None
        if orig:
            col = trial_cols.get(orig.lower()) or resolve_field(
                [orig], trial_cols)
        # Falls OriginalName leer ist, letzte Rettung: anhand Display probieren
        if not col and disp:
            col = trial_cols.get(disp.lower()) or resolve_field(
                [disp], trial_cols)

        # LookupTable für dropdown:tblXxx extrahieren
        lookup_table = None
        if ff and ff.lower().startswith("dropdown:"):
            lookup_table = ff[len("dropdown:"):].strip() or None

        field_map.append({
            "Title": disp,
            "ColName": col or orig or disp,
            "StorageTable": str(f.get("StorageTable") or "tbltrial").strip().lower(),
            "LookupTable": lookup_table,
        })
        field_validators.append(ff)
        seen_norm_titles.add(disp_norm)

    insert_dy_ratio_field(field_map, field_validators)
    md.field_map = field_map

    # Modell + Validatoren
    if use_yarn_use_grouping:
        titles_fixed = [FIX_HOUSING, FIX_JET, FIX_PLATE, FIX_AIR, FIX_PLIES]
    elif compact_mode:
        titles_fixed = [FIX_HOUSING, FIX_JET, FIX_PLATE, FIX_AIR, FIX_PLIES]
    else:
        titles_fixed = [FIX_HOUSING, FIX_JET, FIX_PLATE, FIX_AIR, FIX_YARN_USE, FIX_SPOOL]
    md.titles_fixed = titles_fixed
    row_titles = titles_fixed + [f["Title"] for f in field_map]
    # CustomGroup immer am Ende anhängen (Sichtbarkeit via hideRow gesteuert)
    row_titles = row_titles + [CUSTOM_GROUP_TITLE]
    md.row_titles = row_titles
    # Row keys for the DTY process schema (ui/dty_stations.py): fixed rows by
    # name, machine fields by DB column, aligned with row_titles.
    _fixed_keys = {FIX_HOUSING: "housing", FIX_JET: "jet", FIX_PLATE: "jetplate",
                   FIX_AIR: "airpressure", FIX_PLIES: "plies", FIX_YARN_USE: "yarnuse",
                   FIX_SPOOL: "spool"}
    md.row_keys = (
        [_fixed_keys.get(t) for t in titles_fixed]
        + ["dyratio" if f.get("StorageTable") == DY_RATIO_STORAGE
           else str(f.get("ColName") or "").lower() for f in field_map]
        + ["customgroup"])
    readonly_rows = set()
    if use_yarn_use_grouping or compact_mode:
        readonly_rows.add(titles_fixed.index(FIX_PLIES))  # Plies-Zeile immer read-only
    for i, fdef in enumerate(field_map):
        if fdef.get("StorageTable") == DY_RATIO_STORAGE:
            readonly_rows.add(len(titles_fixed) + i)
    md.read_only_rows = sorted(readonly_rows)

    row_validators: List[Optional[str]] = [None] * len(row_titles)
    row_validators[0] = None  # Housing
    row_validators[1] = None  # Jet
    row_validators[2] = reserved_validators.get(FIX_PLATE)
    row_validators[3] = reserved_validators.get(FIX_AIR)
    for i, ff in enumerate(field_validators, start=len(titles_fixed)):
        row_validators[i] = ff
    md.validators = row_validators
    # CustomGroup: zuletzt, kein Validator
    md.custom_group_row = len(row_titles) - 1

    # dropdown_rows aufbauen: {row_index_0based → {id → name}}
    dropdown_rows: Dict[int, Dict[Any, str]] = {}

    # YarnUse Dropdown (Single Plies Modus) — aus Cache
    if not use_yarn_use_grouping and not compact_mode:
        yarn_use_row_idx = titles_fixed.index(FIX_YARN_USE)
        yu_map: Dict[Any, str] = {"": "—", None: "—", 0: "—", "0": "—"}
        for uid, uname in cache.get("yarn_use_map", {}).items():
            yu_map[uid] = uname
            yu_map[str(uid)] = uname  # String-Key für _id_display
        dropdown_rows[yarn_use_row_idx] = yu_map

        # Spool Dropdown - alle am Lager befindlichen Spulen der
        # Garne, die in dieser Series tatsaechlich als Material vorkommen.
        # Series-weite Liste statt strikt pro Zelle gefiltert (eine Zeile
        # gilt fuer die ganze Tabelle) - dafuer profitiert man von der
        # bestehenden Fill-Range-Mechanik fuer Dropdown-Zeilen (z.B. um
        # dieselbe Spule auf viele Trials gleichzeitig zu setzen).
        spool_row_idx = titles_fixed.index(FIX_SPOOL)
        sp_map: Dict[Any, str] = {"": "—", None: "—", 0: "—", "0": "—"}
        # Volle Infos (Garn/Batch/Gewicht/Ort) landen NICHT in sp_map (das
        # waere die Zellen-/Dropdown-Anzeige und macht die Spalte zu breit),
        # sondern separat in spool_tooltips fuer den Tooltip.
        spool_tooltips: Dict[int, str] = {}
        md.spool_tooltips = spool_tooltips
        if table_exists("tblYarnSpool"):
            try:
                series_yarn_ids = sorted({
                    int(r["YarnID"]) for r in fetch_all(
                        "SELECT DISTINCT ts.YarnID FROM tblTrialSettings ts "
                        "JOIN tblTrial t ON t.ID = ts.TrialID "
                        "WHERE t.TrialSeriesID = ? AND ts.YarnID IS NOT NULL",
                        [st.series_id])
                })
            except Exception:
                series_yarn_ids = []
            if series_yarn_ids:
                ph = ",".join(["?"] * len(series_yarn_ids))
                yname_map = cache.get("yarn_map") or {}
                if not yname_map and table_exists("tblYarn"):
                    for yr in fetch_all("SELECT ID, Name FROM tblYarn"):
                        try:
                            yname_map[int(yr["ID"])] = str(yr.get("Name") or "")
                        except Exception:
                            pass
                spool_rows = fetch_all(
                    f"SELECT ID, YarnID, Charge, WeightKg, Location FROM tblYarnSpool "
                    f"WHERE YarnID IN ({ph}) AND Status = 'in stock' AND WeightKg > 0 "
                    f"ORDER BY YarnID, Charge",
                    series_yarn_ids,
                )
                for sr2 in spool_rows:
                    yname = yname_map.get(int(sr2["YarnID"]), "") if sr2.get("YarnID") is not None else ""
                    short_label = f"#{sr2['ID']}"
                    full_label = f"#{sr2['ID']} {yname} — {sr2.get('Charge') or '–'} — {sr2.get('WeightKg'):.1f}kg — {sr2.get('Location') or '–'}"
                    sp_map[sr2["ID"]] = short_label
                    sp_map[str(sr2["ID"])] = short_label
                    spool_tooltips[int(sr2["ID"])] = full_label
        dropdown_rows[spool_row_idx] = sp_map

    # Lookup-Maps aus Cache
    lookup_maps_cache = cache.get("lookup_maps", {})
    for i, fdef in enumerate(field_map):
        lt = fdef.get("LookupTable")
        if not lt:
            continue
        row_idx = len(titles_fixed) + i
        lk_map = lookup_maps_cache.get(lt)
        if lk_map:
            dropdown_rows[row_idx] = lk_map
    md.dropdown_rows = dropdown_rows

    # dropdown entries (desktop: LookupComboDelegate) - int keys only, A-Z
    from db.dty_process import LOOKUP_NAME as _DTY_LOOKUP
    _keep_order = {len(titles_fixed) + i for i, f in enumerate(field_map)
                   if str(f.get("LookupTable") or "").lower() == _DTY_LOOKUP.lower()}
    for row_idx, lk_map in dropdown_rows.items():
        lk_list = [(k, v) for k, v in lk_map.items() if isinstance(k, int)]
        if row_idx not in _keep_order:  # DTY process: keep SortOrder from the cache
            lk_list.sort(key=lambda x: x[1])
        md.dropdown_lists[row_idx] = lk_list

    if not st.trial_ids:
        return md

    # Jet-Name finden (tblDTYJets bevorzugt)
    def _find_jet_table_and_text_col() -> tuple[Optional[str], Optional[str]]:
        candidates_tables = ["tblDTYJets", "tblJets",
                             "tblJet", "tblDuesen", "tblDuese", "Jets"]
        preferred_names = ["name", "jetname", "bezeichnung", "title",
                           "jet", "nozzle", "code", "typ", "type", "modell", "model",
                           "series", "designation", "description"]
        for tname in candidates_tables:
            if not table_exists(tname):
                continue
            infos = get_columns_info(tname)
            by_lower = {inf["lower"]: inf for inf in infos}
            for cand in preferred_names:
                if cand in by_lower:
                    return tname, by_lower[cand]["real"]
            for inf in infos:
                dt = inf["data_type"]
                tn = (inf["type_name"] or "").upper()
                is_text = (
                                  dt in (1, 12, -1)) or any(x in tn for x in ["CHAR", "TEXT", "MEMO"])
                if is_text and ("id" not in inf["lower"]):
                    return tname, inf["real"]
            return tname, None
        return None, None

    jet_table, jet_text_col = _find_jet_table_and_text_col()

    if jet_table and jet_text_col:
        trial_rows = fetch_all(
            f"""
            SELECT T.*, J.[{jet_text_col}] AS JetName
            FROM tblTrial AS T
            LEFT JOIN {jet_table} AS J ON T.JetID = J.ID
            WHERE T.ID IN ({",".join(["?"] * len(st.trial_ids))})
            ORDER BY T.Versuchsnummer
            """,
            st.trial_ids,
        )
    else:
        trial_rows = fetch_all(
            f"""
            SELECT *
            FROM tblTrial
            WHERE ID IN ({",".join(["?"] * len(st.trial_ids))})
            ORDER BY Versuchsnummer
            """,
            st.trial_ids,
        )
        trial_cols_map = cache.get("trial_cols_map") or get_columns_map("tblTrial")
        jet_text_field = resolve_field(
            ["Jet", "Jet Name", "Nozzle", "Nozzle"], trial_cols_map)
        for row in trial_rows:
            row["JetName"] = row.get(
                jet_text_field) if jet_text_field else None
    md.trial_rows = trial_rows

    # ── col_specs immer aus tblTrialSettings aufbauen ─────────────────
    # (auch wenn keine Settings-Felder in field_map sind – für Konsistenz)
    col_specs: List[Dict] = []  # {"trial": ..., "sr": ..., "ply": str, "trial_id": int}
    settings_cols_map: Dict[str, str] = cache.get("settings_cols_map") or {}
    _ymap: Dict[int, str] = {}

    if table_exists("tblTrialSettings"):
        if not settings_cols_map:
            settings_cols_map = get_columns_map("tblTrialSettings")

        # Settings-Zeilen laden (muss immer frisch sein)
        s_rows = fetch_all(
            f"""
            SELECT * FROM tblTrialSettings
            WHERE TrialID IN ({",".join(["?"] * len(st.trial_ids))})
            ORDER BY TrialID, ID
            """,
            st.trial_ids,
        )

        def _ply_num(sr) -> int:
            ply = (sr.get("Ply") or "").strip()
            m = re.search(r"\d+", ply)
            return int(m.group()) if m else 9999

        settings_by_trial: Dict[int, List[Dict]] = {}
        for sr in s_rows:
            settings_by_trial.setdefault(int(sr["TrialID"]), []).append(sr)
        # Innerhalb jedes Trials nach Ply-Nummer sortieren
        for _tid in settings_by_trial:
            settings_by_trial[_tid].sort(key=_ply_num)

        # Build YarnID → Name lookup for tooltips — aus Cache
        _ymap = cache.get("yarn_map") or {}
        if not _ymap and table_exists("tblYarn"):
            for _yr in fetch_all("SELECT ID, Name FROM tblYarn"):
                try:
                    _ymap[int(_yr["ID"])] = str(_yr["Name"] or "")
                except Exception:
                    pass
        _ycolours: Dict[int, str] = cache.get("yarn_colour_map")
        if _ycolours is None:
            _ycolours = load_yarn_colours()[0]

        trial_row_by_id = {int(t["ID"]): t for t in trial_rows}
        for trial in st.trials:
            tid = int(trial["ID"])
            srows = settings_by_trial.get(tid, [])
            if not srows:
                col_specs.append({
                    "trial": trial_row_by_id.get(tid, {}),
                    "sr": None,
                    "ply": "",
                    "yarn_name": "",
                    "trial_id": tid,
                    "vno": int(trial["Versuchsnummer"]),
                })
            else:
                for idx_sr, sr in enumerate(srows):
                    ply = sr.get("Ply") or f"Ply {idx_sr + 1}"
                    try:
                        _yid = int(sr.get("YarnID") or 0)
                    except Exception:
                        _yid = 0
                    col_specs.append({
                        "trial": trial_row_by_id.get(tid, {}),
                        "sr": sr,
                        "ply": ply,
                        "yarn_name": _ymap.get(_yid, ""),
                        "yarn_colour": _ycolours.get(_yid, ""),
                        "trial_id": tid,
                        "vno": int(trial["Versuchsnummer"]),
                    })
    else:
        trial_row_by_id = {int(t["ID"]): t for t in trial_rows}
        for trial in st.trials:
            col_specs.append({
                "trial": trial_row_by_id.get(int(trial["ID"]), {}),
                "sr": None,
                "ply": "",
                "trial_id": int(trial["ID"]),
                "vno": int(trial["Versuchsnummer"]),
            })
    md.settings_cols_map = settings_cols_map

    # ── YarnUse-Gruppierung ───────────────────────────────────────────
    # Statt pro Ply eine Spalte → pro Trial eine Spalte pro YarnUse-Gruppe.
    # col_specs wird zu group_col_specs umgebaut.
    if use_yarn_use_grouping and col_specs:
        # tblYarnUse laden
        yarn_use_map: Dict[int, str] = cache.get("yarn_use_map") or {}
        if not yarn_use_map:
            try:
                for r in fetch_all("SELECT ID, Name FROM tblYarnUse ORDER BY ID"):
                    yarn_use_map[int(r["ID"])] = str(r.get("Name") or f"Group {r['ID']}")
            except Exception:
                pass

        # YarnUseID pro Settings-Row ermitteln
        # tblTrialSettings.YarnUseID laden für alle relevanten Settings-IDs
        settings_ids_all = [
            int(cs["sr"]["ID"]) for cs in col_specs if cs.get("sr")
        ]
        use_id_by_settings: Dict[int, Optional[int]] = {}
        if settings_ids_all:
            ph = ",".join(["%s"] * len(settings_ids_all))
            try:
                for r in fetch_all(
                        f"SELECT ID, YarnUseID FROM tblTrialSettings WHERE ID IN ({ph})",
                        settings_ids_all
                ):
                    use_id_by_settings[int(r["ID"])] = (
                        int(r["YarnUseID"]) if r.get("YarnUseID") else None
                    )
            except Exception:
                pass

        # col_specs pro Trial nach YarnUseID gruppieren
        # Reihenfolge der Gruppen: wie sie in den Settings vorkommen
        group_col_specs: List[Dict] = []
        # Trials in Reihenfolge
        seen_tids: List[int] = []
        trial_cs_map: Dict[int, List[Dict]] = {}
        for cs in col_specs:
            tid = cs["trial_id"]
            if tid not in trial_cs_map:
                seen_tids.append(tid)
                trial_cs_map[tid] = []
            trial_cs_map[tid].append(cs)

        for tid in seen_tids:
            tcs = trial_cs_map[tid]
            # Gruppen für diesen Trial aufbauen
            groups: Dict[Optional[int], List[Dict]] = OrderedDict()
            for cs in tcs:
                sr = cs.get("sr")
                uid = use_id_by_settings.get(int(sr["ID"])) if sr else None
                groups.setdefault(uid, []).append(cs)

            for uid, members in groups.items():
                use_name = yarn_use_map.get(uid, "—") if uid else "—"
                # Ply-Nummern extrahieren
                ply_nums = []
                for m in members:
                    ply_str = (m.get("ply") or "").strip()
                    match = re.search(r"\d+", ply_str)
                    if match:
                        ply_nums.append(match.group())
                ply_label_short = ", ".join(ply_nums) if ply_nums else "—"

                group_col_specs.append({
                    "trial": members[0]["trial"],
                    "sr": members[0]["sr"],  # erster Ply als Referenz
                    "sr_all": [m["sr"] for m in members if m.get("sr")],
                    "ply": use_name,  # Spalten-Header = YarnUse-Name
                    "ply_label_short": ply_label_short,  # "1, 2" für Plies-Zeile
                    "yarn_name": members[0].get("yarn_name", ""),
                    "yarn_colour": members[0].get("yarn_colour", ""),
                    "trial_id": tid,
                    "vno": members[0]["vno"],
                    "yarn_use_id": uid,
                    "yarn_use_name": use_name,
                    "is_group": True,
                })

        col_specs = group_col_specs
    md.col_specs = col_specs

    # ── header rows ───────────────────────────────────────────────────
    # Zeile 0: Trial-Gruppen  ("", "V1","V1","V2","V2",...)
    # Zeile 1: Ply-Labels     ("", "Ply 1","Ply 2","Ply 1","Ply 2",...)
    # Spalte 0 in beiden Zeilen = leere Titelspalte
    # Pro Trial: alle col_specs sammeln für Kompakt-Tooltip
    trial_cs_for_hdr: Dict[int, List[Dict]] = {}
    for cs in col_specs:
        trial_cs_for_hdr.setdefault(cs["trial_id"], []).append(cs)

    trial_hdr_vals = [""]
    ply_hdr_vals = [""]
    ply_tooltip_vals = [""]
    ply_colour_vals = [""]
    for cs in col_specs:
        trial_hdr_vals.append(trial_hdr_label(cs, st.reference_names))
        ply_colour_vals.append(ply_header_colour(cs, trial_cs_for_hdr, compact_mode))
        if compact_mode:
            # Kompakt: alle Plies des Trials zusammenfassen
            all_cs = trial_cs_for_hdr.get(cs["trial_id"], [cs])
            if len(all_cs) == 1:
                # Nur 1 Ply → "Ply 1"
                ply_hdr_vals.append(cs["ply"])
            else:
                # Mehrere Plies → "div."
                ply_hdr_vals.append("div.")
            # Tooltip: alle Garnamen der Plies
            tooltip_lines = []
            for other_cs in all_cs:
                ply_lbl = other_cs.get("ply") or ""
                yname = other_cs.get("yarn_name") or ""
                if ply_lbl or yname:
                    tooltip_lines.append(f"{ply_lbl}: {yname}" if yname else ply_lbl)
            ply_tooltip_vals.append("\n".join(tooltip_lines) if tooltip_lines else "")
        else:
            ply_hdr_vals.append(cs["ply"])
            ply_tooltip_vals.append(cs.get("yarn_name") or "")

    # Zeile 0 = V-Nummern (gespannt), Zeile 1 = Ply-Labels (einzeln) – nur fett, kein Sonderfarbe
    md.header_rows = [
        {"values": trial_hdr_vals, "bg": None, "fg": None},
        {"values": ply_hdr_vals, "bg": None, "fg": None, "tooltips": ply_tooltip_vals,
         "colours": ply_colour_vals},
    ]

    md.columns = [_column_info(cs, trial_hdr_vals[c + 1], ply_hdr_vals[c + 1], ply_tooltip_vals[c + 1],
                               ply_colour_vals[c + 1], st.reference_names)
                  for c, cs in enumerate(col_specs)]

    _fill_cells(md, cache, col_specs, field_map, titles_fixed, reserved_originals,
                use_yarn_use_grouping, compact_mode, settings_cols_map, _ymap)

    # pre-jet / jet 3 / merge rows (DTY process) - same rule as ui/dty_schema_panel.update_process_rows
    hidden, locked = process_rules(cache, md.row_keys, col_specs, len(col_specs),
                                   lambda r, c: _text(md.cells[r][c][0]))
    md.process_hidden_rows = hidden
    for r, c in locked:
        md.cells[r][c] = (md.cells[r][c][0], None)
        md.cell_tooltips[(r, c)] = SINGLE_PLY_TIP

    # ── one cell per trial: [(first data col, span)] ──────────────────
    _last_tid2 = None
    _grp_start = 0
    _grp_count = 0
    for ci, cs in enumerate(col_specs):
        tid2 = cs["trial_id"]
        if tid2 != _last_tid2:
            if _grp_count > 0:
                md.trial_spans.append((_grp_start, _grp_count))
            _grp_start = ci
            _grp_count = 1
            _last_tid2 = tid2
        else:
            _grp_count += 1
    if _grp_count > 0:
        md.trial_spans.append((_grp_start, _grp_count))

    # Zeilen die trial-weit gespannt werden: Housing, Jet, Plate, Air Pressure,
    # alle tblTrial-Felder, Custom Group. Plies (Groups/Compact) und
    # Yarn Use / Spool (Single) bewusst NICHT - pro Ply/Gruppe eigener Wert.
    md.trial_wide_rows = [0, 1, 2, 3]
    for offset, fdef in enumerate(field_map):
        if fdef.get("StorageTable", "tbltrial") not in ("tbltrialsettings", DY_RATIO_STORAGE):
            md.trial_wide_rows.append(len(titles_fixed) + offset)
    md.trial_wide_rows.append(md.custom_group_row)

    # ── "Show:" filter ────────────────────────────────────────────────
    unique_trial_ids_flt = []
    for cs in col_specs:
        if cs.get("trial_id") not in unique_trial_ids_flt:
            unique_trial_ids_flt.append(cs.get("trial_id"))
    md.has_multi_ply = len(col_specs) > len(unique_trial_ids_flt)
    if md.has_multi_ply:
        # Zeige-Labels: im Groups-Modus Gruppen, sonst Plies
        seen_set_flt: set = set()
        for cs in col_specs:
            lbl = column_label(cs, bool(cs.get("is_group")))
            if lbl and lbl not in seen_set_flt:
                seen_set_flt.add(lbl)
                md.filter_labels.append(lbl)
    return md


def _column_info(cs: Dict, trial_label: str, ply_label: str, ply_tooltip: str, colour: str,
                 reference_names: Dict[int, str]) -> Dict[str, Any]:
    sr = cs.get("sr")
    sr_all = cs.get("sr_all") if cs.get("is_group") else ([sr] if sr else [])
    return {
        "trial_id": cs["trial_id"],
        "vno": cs["vno"],
        "trial_label": trial_label,                        # header row 0 ("V12" / "REF ...")
        "reference": reference_names.get(int(cs["trial_id"])),
        "ply": cs.get("ply") or "",                        # "Ply 1" / yarn use name (groups)
        "ply_label": ply_label,                            # header row 1 as shown ("div." in compact)
        "ply_tooltip": ply_tooltip,
        "yarn_name": cs.get("yarn_name") or "",
        "yarn_colour": colour,                             # colour name of the square ("" = none)
        "yarn_colour_css": colour_css(colour),             # CSS colour or None
        "yarn_use_id": (cs.get("yarn_use_id") if cs.get("is_group")
                        else (sr.get("YarnUseID") if sr else None)),
        "yarn_use_name": cs.get("yarn_use_name"),
        "settings_ids": [int(s["ID"]) for s in sr_all if s],
        "is_group": bool(cs.get("is_group")),
        "ply_label_short": cs.get("ply_label_short"),
    }


def _pick_row_key(row: dict, preferred: Optional[str], extra_cands: List[str]) -> Optional[str]:
    if not row:
        return None
    if preferred and preferred in row:
        return preferred
    if preferred:
        pl = preferred.lower()
        for k in row.keys():
            if str(k).lower() == pl:
                return k
    wanted = []
    if preferred:
        wanted.append(preferred)
    wanted.extend(extra_cands or [])
    wanted_norm = {norm(w) for w in wanted if w}
    for k in row.keys():
        if norm(str(k)) in wanted_norm:
            return k
    return None


def _fill_cells(md: MachineData, cache: Dict[str, Any], col_specs: List[Dict], field_map: List[Dict],
                titles_fixed: List[str], reserved_originals: Dict[str, Optional[str]],
                use_yarn_use_grouping: bool, compact_mode: bool,
                settings_cols_map: Dict[str, str], _ymap: Dict[int, str]) -> None:
    n_rows, n_cols = len(md.row_titles), len(col_specs)
    cells: List[List[Tuple[Any, Any]]] = [[(None, None) for _ in range(n_cols)] for _ in range(n_rows)]
    md.cells = cells
    tooltips = md.cell_tooltips

    def set_cell(r: int, c: int, value: Any, binding: Any) -> None:
        cells[r][c] = (value, binding)

    trial_cols_map = cache.get("trial_cols_map") or get_columns_map("tblTrial")

    jet_plate_col = None
    jet_plate_col = trial_cols_map.get("jetplate") or trial_cols_map.get("jet_plate")
    if not jet_plate_col and reserved_originals.get(FIX_PLATE):
        jet_plate_col = trial_cols_map.get(reserved_originals[FIX_PLATE].lower()) \
                        or resolve_field([reserved_originals[FIX_PLATE]], trial_cols_map)
    if not jet_plate_col:
        jet_plate_col = resolve_field(
            ["Jet Plate", "JetPlate", "Jet_Plate", "JetPlateNumber", "Jet Plate Number"], trial_cols_map)

    air_press_col = None
    air_press_col = trial_cols_map.get("airpressure") or trial_cols_map.get("air_pressure")
    if not air_press_col and reserved_originals.get(FIX_AIR):
        air_press_col = trial_cols_map.get(reserved_originals[FIX_AIR].lower()) \
                        or resolve_field([reserved_originals[FIX_AIR]], trial_cols_map)
    if not air_press_col:
        air_press_col = resolve_field(
            ["Air Pressure (bar)", "AirPressure(bar)",
             "AirPressure", "Air_Pressure_bar", "Air Pressure"],
            trial_cols_map)

    # Resolve HousingID column
    housing_id_col = resolve_field(["HousingID"], trial_cols_map)

    # ── Zellen befüllen ───────────────────────────────────────────────
    # 0: Housing (tblTrial – trial-weit)
    for c_idx, cs in enumerate(col_specs):
        trow = cs["trial"]
        housing_id = trow.get("HousingID") if housing_id_col else None
        set_cell(
            0, c_idx, housing_id,
            CellBinding("tblTrial", "ID", trow.get("ID"), "HousingID") if (
                        housing_id_col and trow.get("ID")) else None,
        )

    # 1: Jet (tblTrial – trial-weit)
    for c_idx, cs in enumerate(col_specs):
        trow = cs["trial"]
        jet_id = trow.get("JetID")
        set_cell(
            1, c_idx, jet_id,
            CellBinding("tblTrial", "ID", trow.get("ID"), "JetID") if trow.get("ID") else None,
        )

    # 2: Jet Plate Number (tblTrial – trial-weit)
    for c_idx, cs in enumerate(col_specs):
        trow = cs["trial"]
        jp_key = _pick_row_key(trow, jet_plate_col,
                               ["JetPlate", "jetplate", "Jet_Plate", "jet_plate",
                                "Jet Plate", "Jet Plate Number", "JetPlateNumber"])
        jp_field = jet_plate_col or jp_key
        set_cell(
            2, c_idx,
            trow.get(jp_key) if jp_key else None,
            CellBinding("tblTrial", "ID", trow.get("ID"), jp_field) if (jp_field and trow.get("ID")) else None,
        )

    # 3: Air Pressure (tblTrial – trial-weit)
    for c_idx, cs in enumerate(col_specs):
        trow = cs["trial"]
        ap_key = _pick_row_key(trow, air_press_col,
                               ["AirPressure", "airpressure", "Air_Pressure", "air_pressure",
                                "Air Pressure", "Air Pressure (bar)", "AirPressure(bar)", "Air_Pressure_bar"])
        ap_field = air_press_col or ap_key
        set_cell(
            3, c_idx,
            trow.get(ap_key) if ap_key else None,
            CellBinding("tblTrial", "ID", trow.get("ID"), ap_field) if (ap_field and trow.get("ID")) else None,
        )

    # Plies-Zeile (Groups-Modus oder Kompakt-Modus)
    if use_yarn_use_grouping:
        plies_row_idx = titles_fixed.index(FIX_PLIES)
        for c_idx, cs in enumerate(col_specs):
            set_cell(
                plies_row_idx, c_idx,
                cs.get("ply_label_short", ""),
                None,
            )
            # Tooltip: Garnname pro Ply
            sr_all = cs.get("sr_all") or []
            if sr_all:
                tooltip_lines = []
                for sr in sr_all:
                    ply = sr.get("Ply") or ""
                    yid = None
                    try:
                        yid = int(sr.get("YarnID") or 0) or None
                    except Exception:
                        pass
                    yname = _ymap.get(yid, "") if yid else ""
                    if ply or yname:
                        tooltip_lines.append(f"{ply}: {yname}" if yname else ply)
                if tooltip_lines:
                    tooltips[(plies_row_idx, c_idx)] = "\n".join(tooltip_lines)

    elif compact_mode:
        # Kompakt: pro Trial alle Plies zusammenfassen
        plies_row_idx = titles_fixed.index(FIX_PLIES)
        # Alle col_specs pro Trial sammeln
        trial_all_cs: Dict[int, List[Dict]] = {}
        for cs in col_specs:
            trial_all_cs.setdefault(cs["trial_id"], []).append(cs)

        for c_idx, cs in enumerate(col_specs):
            all_cs = trial_all_cs.get(cs["trial_id"], [cs])
            # Ply-Nummern kurz
            ply_nums = []
            for other_cs in all_cs:
                ply_str = (other_cs.get("ply") or "").strip()
                m = re.search(r"\d+", ply_str)
                if m:
                    ply_nums.append(m.group())
            short = ", ".join(ply_nums) if ply_nums else "—"
            set_cell(plies_row_idx, c_idx, short, None)
            # Tooltip: Garnname pro Ply
            tooltip_lines = []
            for other_cs in all_cs:
                ply_lbl = other_cs.get("ply") or ""
                yid = None
                sr = other_cs.get("sr")
                if sr:
                    try:
                        yid = int(sr.get("YarnID") or 0) or None
                    except Exception:
                        pass
                yname = _ymap.get(yid, "") if yid else ""
                if ply_lbl or yname:
                    tooltip_lines.append(f"{ply_lbl}: {yname}" if yname else ply_lbl)
            if tooltip_lines:
                tooltips[(plies_row_idx, c_idx)] = "\n".join(tooltip_lines)

    # YarnUse-Zeile (nur Single Plies Modus)
    if not use_yarn_use_grouping and not compact_mode:
        yarn_use_row_idx = titles_fixed.index(FIX_YARN_USE)
        for c_idx, cs in enumerate(col_specs):
            sr = cs.get("sr")
            yuid = None
            if sr:
                try:
                    yuid = int(sr.get("YarnUseID") or 0) or None
                except Exception:
                    yuid = None
            set_cell(
                yarn_use_row_idx, c_idx, yuid,
                CellBinding("tblTrialSettings", "ID", sr["ID"], "YarnUseID") if sr else None,
            )

        # Spool-Zeile: physische Duese-Zuordnung pro Ply/Trial
        spool_row_idx = titles_fixed.index(FIX_SPOOL)
        spool_tooltips = md.spool_tooltips or {}
        for c_idx, cs in enumerate(col_specs):
            sr = cs.get("sr")
            spool_id = None
            if sr:
                try:
                    spool_id = int(sr.get("SpoolID") or 0) or None
                except Exception:
                    spool_id = None
            set_cell(
                spool_row_idx, c_idx, spool_id,
                CellBinding("tblTrialSettings", "ID", sr["ID"], "SpoolID") if sr else None,
            )
            if spool_id is not None and spool_id in spool_tooltips:
                tooltips[(spool_row_idx, c_idx)] = spool_tooltips[spool_id]

    # weitere Maschinenfelder
    start_row = len(titles_fixed)
    for offset, fdef in enumerate(field_map):
        r_idx = start_row + offset
        storage = fdef.get("StorageTable", "tbltrial")
        colname = fdef["ColName"]

        if storage == DY_RATIO_STORAGE:
            continue  # computed below from T1/T2
        if storage == "tbltrialsettings" and settings_cols_map:
            real_col = settings_cols_map.get(colname.lower()) or colname
            for c_idx, cs in enumerate(col_specs):
                sr = cs["sr"]
                if use_yarn_use_grouping and cs.get("is_group"):
                    # Gruppe: alle Werte prüfen, ersten nehmen, orange wenn inkonsistent
                    sr_all = cs.get("sr_all") or ([sr] if sr else [])
                    vals = [
                        s.get(real_col) for s in sr_all
                        if s and s.get(real_col) is not None
                    ]
                    val = vals[0] if vals else None
                    inconsistent = len(set(str(v) for v in vals)) > 1 if vals else False
                    settings_ids = [int(s["ID"]) for s in sr_all if s]
                    binding = GroupCellBinding(
                        "tblTrialSettings", "ID", settings_ids, real_col
                    ) if settings_ids else None
                    set_cell(r_idx, c_idx, val, binding)
                    if inconsistent:
                        md.cell_alerts[(r_idx, c_idx)] = "orange"
                else:
                    val = sr.get(real_col) if sr else None
                    binding = CellBinding(
                        "tblTrialSettings", "ID", sr["ID"], real_col
                    ) if sr else None
                    set_cell(r_idx, c_idx, val, binding)
        else:
            real_col = trial_cols_map.get(str(colname).lower()) or colname
            for c_idx, cs in enumerate(col_specs):
                trow = cs["trial"]
                val = trow.get(real_col)
                set_cell(
                    r_idx, c_idx, val,
                    CellBinding("tblTrial", "ID", trow.get("ID"), real_col) if trow.get("ID") else None,
                )

    # D/Y ratio: T2/T1 per column (the desktop keeps it current while T1/T2 are edited)
    _ratio_rows = {str(f.get("ColName") or "").lower() if f.get("StorageTable") != DY_RATIO_STORAGE
                   else "ratio": start_row + i for i, f in enumerate(field_map)}
    if "ratio" in _ratio_rows:
        r_t1, r_t2, r_ratio = _ratio_rows["yarntensiont1"], _ratio_rows["yarntensiont2"], _ratio_rows["ratio"]
        md.dy_ratio = (r_t1, r_t2, r_ratio)
        for c in range(n_cols):
            set_cell(r_ratio, c, dy_ratio_text(_text(cells[r_t1][c][0]), _text(cells[r_t2][c][0])), None)
            tooltips[(r_ratio, c)] = DY_RATIO_TOOLTIP

    # CustomGroup-Zeile befüllen (direkt aus tblTrial.CustomGroup)
    _cg_col = trial_cols_map.get('customgroup') or trial_cols_map.get('custom_group') or 'CustomGroup'
    for c_idx, cs in enumerate(col_specs):
        trow = cs['trial']
        val = trow.get(_cg_col)
        set_cell(
            md.custom_group_row, c_idx, val,
            CellBinding('tblTrial', 'ID', trow.get('ID'), _cg_col) if trow.get('ID') else None,
        )


# --------------------------------------------------------------------------- display (web)
def display_text(md: MachineData, r: int, c: int, jets_map: Optional[Dict[Any, str]] = None,
                 housing_map: Optional[Dict[Any, str]] = None) -> str:
    """Cell text as the desktop shows it (MachinePivotModel.data, DisplayRole):
    Housing / Jet / dropdown rows show the name for the stored ID."""
    internal = _text(md.cells[r][c][0])
    if r == HOUSING_ROW:
        return id_display(housing_map or {}, internal)
    if r == JET_ROW:
        return id_display(jets_map or {}, internal)
    if r in md.dropdown_rows:
        return id_display(md.dropdown_rows[r], internal)
    return internal


# --------------------------------------------------------------------------- R&D Machine Data tab
# Moved out of ui/machine_tab.py (build_rd_machine_tab_impl) on 2026-11-13; queries and
# rules unchanged. Rows = the 4 fixed rows + the RDSetting = 1 fields of the machine,
# columns = those of the Machine Data tab (same view mode, same col_specs).
RD_FIXED_KEYS = ["housing", "jet", "jetplate", "airpressure"]

# Tooltip of the "W0-W1 OF (%)" row: Speed Shaft 2 / Shaft 1 DR x (100 + OF) / 100
OF_SPEED_KEY = "speedshaft2mmin"      # Machine Data row (title_key)
OF_DR_KEY = "shaft1dr"                # Machine Data row (title_key)
OF_KEYS = ("w0w1of%", "w0w1of")       # R&D row (title_key), first one found wins


@dataclass
class RDMachineData:
    """R&D Machine Data (tblMachineFields.RDSetting = 1) of one series. Built on a MachineData:
    same columns (col_specs of its view mode). Row/column indexes are 0-based data indexes
    (no header rows); rows = Housing, Jet, Jet Plate Number, Air Pressure + the R&D fields.
    No read-only rows, no hidden rows, no Custom Group row."""
    series_id: Any = None
    machine_id: Any = None
    view_mode: str = "single"
    visible: bool = False                            # tab shown (the machine has RDSetting = 1 fields)
    fields_rd: List[Dict[str, Any]] = field(default_factory=list)    # tblMachineFields rows (RDSetting = 1)
    field_map: List[Dict[str, Any]] = field(default_factory=list)    # dynamic rows: Title/ColName/StorageTable/LookupTable
    titles_fixed: List[str] = field(default_factory=list)            # the 4 fixed row titles
    row_titles: List[str] = field(default_factory=list)
    row_keys: List[Optional[str]] = field(default_factory=list)      # DB column lower case (Knowledge Base links)
    validators: List[Optional[str]] = field(default_factory=list)    # canon_rule per row (onlyInteger, dropdown:tbl, ...)
    read_only_rows: List[int] = field(default_factory=list)          # always empty
    dropdown_rows: Dict[int, Dict[Any, str]] = field(default_factory=dict)   # row -> {id: name} (int and str keys)
    dropdown_lists: Dict[int, List[Tuple[int, str]]] = field(default_factory=dict)  # row -> [(id, name)] A-Z
    col_specs: List[Dict[str, Any]] = field(default_factory=list)    # = MachineData.col_specs (full DB rows)
    columns: List[Dict[str, Any]] = field(default_factory=list)      # slim, JSON-friendly column info
    header_rows: List[Dict[str, Any]] = field(default_factory=list)  # trial row + ply row (index 0 = title column)
    cells: List[List[Tuple[Any, Any]]] = field(default_factory=list)  # [row][col] = (raw value, CellBinding | None)
    cell_tooltips: Dict[Tuple[int, int], str] = field(default_factory=dict)  # always empty
    cell_alerts: Dict[Tuple[int, int], str] = field(default_factory=dict)    # always empty
    trial_spans: List[Tuple[int, int]] = field(default_factory=list)  # (first data col, number of cols)
    trial_wide_rows: List[int] = field(default_factory=list)         # one cell per trial (spanned)
    housing_rows: Set[int] = field(default_factory=set)              # rows whose title contains "housing"
    jet_rows: Set[int] = field(default_factory=set)                  # rows whose title contains "jet"
    of_row: Optional[int] = None                                     # "W0-W1 OF" row (speed tooltip)
    of_speed_tooltips: Dict[int, str] = field(default_factory=dict)  # col -> "Speed: N m/min" (stored values)


def title_key(title: str) -> str:
    """Row title lower case without " _()-/" (the OF speed tooltip finds its rows by it)."""
    n = title.lower()
    for ch in " _()-/":
        n = n.replace(ch, "")
    return n


def float_by_title(row_titles: List[str], key: str, matrix: List[List[Any]], col: int) -> Optional[float]:
    """Value of the first row with title_key == key in column col as float (None = missing/no number)."""
    for i, t in enumerate(row_titles or []):
        if title_key(t) == key:
            if 0 <= i < len(matrix) and 0 <= col < len(matrix[i]):
                try:
                    return float(matrix[i][col])
                except Exception:
                    return None
    return None


def of_speed_tooltip(machine_titles: List[str], machine_matrix: List[List[Any]],
                     rd_titles: List[str], rd_matrix: List[List[Any]], col: int) -> Optional[str]:
    """Tooltip of the OF row: "Speed: N m/min" = Speed Shaft 2 / Shaft 1 DR x (100 + OF) / 100,
    None if a value is missing or the DR is 0. The matrices hold the cell texts ([row][col])."""
    speed = float_by_title(machine_titles, OF_SPEED_KEY, machine_matrix, col)
    dr = float_by_title(machine_titles, OF_DR_KEY, machine_matrix, col)
    of_val = float_by_title(rd_titles, OF_KEYS[0], rd_matrix, col)
    if of_val is None:
        of_val = float_by_title(rd_titles, OF_KEYS[1], rd_matrix, col)
    if speed is None or dr is None or of_val is None or dr == 0:
        return None
    result = speed / dr * (100 + of_val) / 100
    return f"Speed: {int(round(result))} m/min"


def trial_spans(col_specs: List[Dict]) -> List[Tuple[int, int]]:
    """[(first data col, number of cols)] - one group per trial (consecutive columns)."""
    out: List[Tuple[int, int]] = []
    _last_tid = None
    _grp_start = 0
    _grp_count = 0
    for ci, cs in enumerate(col_specs):
        tid = cs["trial_id"]
        if tid != _last_tid:
            if _grp_count > 0:
                out.append((_grp_start, _grp_count))
            _grp_start = ci
            _grp_count = 1
            _last_tid = tid
        else:
            _grp_count += 1
    if _grp_count > 0:
        out.append((_grp_start, _grp_count))
    return out


def build_rd_machine_data(md: MachineData, cache: Optional[Dict[str, Any]] = None,
                          reference_names: Optional[Dict[int, str]] = None) -> RDMachineData:
    """Everything the R&D Machine Data tab shows, on the columns of md. Not visible when
    md has no table (message) or no trials - the desktop then removes the tab as well.
    cache = the one passed to build_machine_data (only trial_cols_map is used)."""
    if md.message is not None or not md.col_specs:
        return RDMachineData(series_id=md.series_id, machine_id=md.machine_id, view_mode=md.view_mode,
                             fields_rd=list(md.fields_rd))
    rd = rd_machine_data_from(md.fields_rd, md.col_specs, md.settings_cols_map, cache,
                              md.reference_names if reference_names is None else reference_names,
                              series_id=md.series_id, machine_id=md.machine_id, view_mode=md.view_mode)
    if rd.of_row is not None:
        m_matrix = [[_text(v) for v, _b in row] for row in md.cells]
        rd_matrix = [[_text(v) for v, _b in row] for row in rd.cells]
        for c in range(len(rd.col_specs)):
            tip = of_speed_tooltip(md.row_titles, m_matrix, rd.row_titles, rd_matrix, c)
            if tip:
                rd.of_speed_tooltips[c] = tip
    return rd


def rd_machine_data_from(fields_rd: List[Dict], col_specs: List[Dict], settings_cols_map: Dict[str, str],
                         cache: Optional[Dict[str, Any]] = None,
                         reference_names: Optional[Dict[int, str]] = None, *,
                         series_id: Any = None, machine_id: Any = None,
                         view_mode: str = "single") -> RDMachineData:
    """build_rd_machine_data from the pieces the desktop passes (MachineData.fields_rd /
    col_specs / settings_cols_map). Leaves of_speed_tooltips empty (the desktop computes
    it live from both models)."""
    cache = cache or {}
    reference_names = reference_names or {}
    rd = RDMachineData(series_id=series_id, machine_id=machine_id, view_mode=view_mode,
                       visible=bool(fields_rd), fields_rd=list(fields_rd or []), col_specs=col_specs)
    if not fields_rd:
        # Keine R&D-Felder -> Tab bleibt versteckt
        return rd

    trial_cols = get_columns_map("tblTrial")

    # Fixe Titel (gleiche wie Machine Data)
    titles_fixed = [FIX_HOUSING, FIX_JET, FIX_PLATE, FIX_AIR]
    rd.titles_fixed = titles_fixed

    reserved_titles = [
        "Versuchsnummer", "Housing",
        "Jet", "Jet Name",
        "JetPlate", "Jet Plate Number",
        "Air Pressure (bar)",
        "Yarn Use", "YarnUse", "YarnUseID",
    ]
    reserved_norm = {norm(x) for x in reserved_titles}
    reserved_validators: Dict[str, Optional[str]] = {FIX_PLATE: None, FIX_AIR: None}
    reserved_originals: Dict[str, Optional[str]] = {FIX_PLATE: None, FIX_AIR: None}
    reserved_norm.add(norm(FIX_HOUSING))

    seen_norm_titles: set = set()
    field_map: List[Dict[str, Optional[str]]] = []
    field_validators: List[Optional[str]] = []

    for f in fields_rd:
        disp = str(f.get("FieldName") or "").strip()
        orig = str(f.get("OriginalName") or "").strip()
        ff = canon_rule((f.get("FieldFunction") or "").strip() or None)
        if not disp:
            continue
        if ff == "hidden":
            continue

        disp_norm = norm(disp)
        if disp_norm in reserved_norm:
            if disp_norm in {norm(FIX_PLATE), norm("JetPlateNumber"), norm("JetPlate")}:
                reserved_validators[FIX_PLATE] = ff
                reserved_originals[FIX_PLATE] = orig or reserved_originals[FIX_PLATE]
            elif disp_norm in {norm(FIX_AIR), norm("AirPressure")}:
                reserved_validators[FIX_AIR] = ff
                reserved_originals[FIX_AIR] = orig or reserved_originals[FIX_AIR]
            continue

        if disp_norm in seen_norm_titles:
            continue

        col = None
        if orig:
            col = trial_cols.get(orig.lower()) or resolve_field([orig], trial_cols)
        if not col and disp:
            col = trial_cols.get(disp.lower()) or resolve_field([disp], trial_cols)

        lookup_table = None
        if ff and ff.lower().startswith("dropdown:"):
            lookup_table = ff[len("dropdown:"):].strip() or None

        field_map.append({
            "Title": disp,
            "ColName": col or orig or disp,
            "StorageTable": str(f.get("StorageTable") or "tbltrial").strip().lower(),
            "LookupTable": lookup_table,
        })
        field_validators.append(ff)
        seen_norm_titles.add(disp_norm)
    rd.field_map = field_map

    row_titles = titles_fixed + [f["Title"] for f in field_map]
    rd.row_titles = row_titles
    # row keys (DB column, lower case) for the Knowledge Base links (ui/kb_links.py)
    rd.row_keys = (list(RD_FIXED_KEYS)
                   + [str(f.get("ColName") or "").lower() for f in field_map])
    row_validators: List[Optional[str]] = [None] * len(row_titles)
    row_validators[2] = reserved_validators.get(FIX_PLATE)
    row_validators[3] = reserved_validators.get(FIX_AIR)
    for i, ff in enumerate(field_validators, start=len(titles_fixed)):
        row_validators[i] = ff
    rd.validators = row_validators

    # Dropdown-Maps aufbauen (own query per lookup table, not the Machine Data cache)
    dropdown_rows: Dict[int, Dict[Any, str]] = {}
    for i, fdef in enumerate(field_map):
        lt = fdef.get("LookupTable")
        if not lt:
            continue
        row_idx = len(titles_fixed) + i
        lk_map: Dict[Any, str] = {}
        try:
            if table_exists(lt):
                lk_cmap = get_columns_map(lt)
                lk_id = resolve_field(["ID"], lk_cmap) or "ID"
                lk_name = resolve_field(
                    ["DiscName", "Name", "Bezeichnung", "Caption",
                     "HousingName", "Jet", "JetName", "MaterialName",
                     "YarnName", "Description", "Label"],
                    lk_cmap)
                if lk_name:
                    lk_rows = fetch_all(
                        f"SELECT [{lk_id}] AS LID, [{lk_name}] AS LName "
                        f"FROM {lt} ORDER BY [{lk_name}] ASC"
                    )
                    for lk in lk_rows:
                        lid = lk.get("LID")
                        lname = str(lk.get("LName") or "")
                        if lid is None:
                            continue
                        try:
                            lk_map[int(lid)] = lname
                        except Exception:
                            pass
                        lk_map[str(lid)] = lname
        except Exception:
            pass
        if lk_map:
            dropdown_rows[row_idx] = lk_map
    rd.dropdown_rows = dropdown_rows
    # dropdown entries (desktop: LookupComboDelegate) - int keys only, A-Z
    for row_idx, lk_map in dropdown_rows.items():
        lk_list = [(k, v) for k, v in lk_map.items() if isinstance(k, int)]
        lk_list.sort(key=lambda x: x[1])
        rd.dropdown_lists[row_idx] = lk_list

    # Header-Zeilen (ply row: the raw ply label in every view mode, own yarn colour per column)
    trial_hdr_vals = [""]
    ply_hdr_vals = [""]
    ply_tooltip_vals = [""]
    for cs in col_specs:
        trial_hdr_vals.append(trial_hdr_label(cs, reference_names))
        ply_hdr_vals.append(cs["ply"])
        ply_tooltip_vals.append(cs.get("yarn_name") or "")
    ply_colour_vals = [""] + [cs.get("yarn_colour") or "" for cs in col_specs]

    rd.header_rows = [
        {"values": trial_hdr_vals, "bg": None, "fg": None},
        {"values": ply_hdr_vals, "bg": None, "fg": None, "tooltips": ply_tooltip_vals,
         "colours": ply_colour_vals},
    ]
    rd.columns = [_column_info(cs, trial_hdr_vals[c + 1], ply_hdr_vals[c + 1], ply_tooltip_vals[c + 1],
                               ply_colour_vals[c + 1], reference_names)
                  for c, cs in enumerate(col_specs)]

    _fill_rd_cells(rd, cache, col_specs, field_map, titles_fixed, reserved_originals, settings_cols_map)

    # one cell per trial: Housing, Jet, Plate, Air Pressure + all tblTrial fields
    rd.trial_spans = trial_spans(col_specs)
    rd.trial_wide_rows = [0, 1, 2, 3]
    for offset, fdef in enumerate(field_map):
        if fdef.get("StorageTable", "tbltrial") != "tbltrialsettings":
            rd.trial_wide_rows.append(len(titles_fixed) + offset)

    # Tooltips: Housing-Zeilen (Bild), Jet-Zeilen (Geometrie), OF-Zeile (Geschwindigkeit)
    housing_rows = set()
    of_row_idx = None
    for i, title in enumerate(row_titles):
        tl = title.lower()
        if "housing" in tl:
            housing_rows.add(i)
        if "w0" in tl and "w1" in tl and "of" in tl:
            of_row_idx = i
    rd.housing_rows = housing_rows
    rd.of_row = of_row_idx

    jet_rows = set()
    for i, title in enumerate(row_titles):
        if "jet" in title.lower():
            jet_rows.add(i)
    rd.jet_rows = jet_rows
    return rd


def _fill_rd_cells(rd: RDMachineData, cache: Dict[str, Any], col_specs: List[Dict], field_map: List[Dict],
                   titles_fixed: List[str], reserved_originals: Dict[str, Optional[str]],
                   settings_cols_map: Dict[str, str]) -> None:
    n_rows, n_cols = len(rd.row_titles), len(col_specs)
    cells: List[List[Tuple[Any, Any]]] = [[(None, None) for _ in range(n_cols)] for _ in range(n_rows)]
    rd.cells = cells

    def set_cell(r: int, c: int, value: Any, binding: Any) -> None:
        cells[r][c] = (value, binding)

    # Zellen befüllen (analog zu _build_machine_tab)
    trial_cols_map = cache.get("trial_cols_map") or get_columns_map("tblTrial")

    jet_plate_col = trial_cols_map.get("jetplate") or trial_cols_map.get("jet_plate")
    if not jet_plate_col and reserved_originals.get(FIX_PLATE):
        jet_plate_col = trial_cols_map.get(reserved_originals[FIX_PLATE].lower()) \
                        or resolve_field([reserved_originals[FIX_PLATE]], trial_cols_map)
    if not jet_plate_col:
        jet_plate_col = resolve_field(
            ["Jet Plate", "JetPlate", "Jet_Plate", "JetPlateNumber", "Jet Plate Number"], trial_cols_map)

    air_press_col = trial_cols_map.get("airpressure") or trial_cols_map.get("air_pressure")
    if not air_press_col and reserved_originals.get(FIX_AIR):
        air_press_col = trial_cols_map.get(reserved_originals[FIX_AIR].lower()) \
                        or resolve_field([reserved_originals[FIX_AIR]], trial_cols_map)
    if not air_press_col:
        air_press_col = resolve_field(
            ["Air Pressure (bar)", "AirPressure(bar)", "AirPressure", "Air_Pressure_bar", "Air Pressure"],
            trial_cols_map)

    housing_id_col = resolve_field(["HousingID"], trial_cols_map)

    # 0: Housing
    for c_idx, cs in enumerate(col_specs):
        trow = cs["trial"]
        housing_id = trow.get("HousingID") if housing_id_col else None
        set_cell(
            0, c_idx, housing_id,
            CellBinding("tblTrial", "ID", trow.get("ID"), "HousingID") if (
                        housing_id_col and trow.get("ID")) else None,
        )

    # 1: Jet
    for c_idx, cs in enumerate(col_specs):
        trow = cs["trial"]
        set_cell(
            1, c_idx, trow.get("JetID"),
            CellBinding("tblTrial", "ID", trow.get("ID"), "JetID") if trow.get("ID") else None,
        )

    # 2: Jet Plate Number
    for c_idx, cs in enumerate(col_specs):
        trow = cs["trial"]
        jp_key = _pick_row_key(trow, jet_plate_col,
                               ["JetPlate", "jetplate", "Jet_Plate", "jet_plate", "Jet Plate",
                                "Jet Plate Number", "JetPlateNumber"])
        jp_field = jet_plate_col or jp_key
        set_cell(
            2, c_idx,
            trow.get(jp_key) if jp_key else None,
            CellBinding("tblTrial", "ID", trow.get("ID"), jp_field) if (jp_field and trow.get("ID")) else None,
        )

    # 3: Air Pressure
    for c_idx, cs in enumerate(col_specs):
        trow = cs["trial"]
        ap_key = _pick_row_key(trow, air_press_col,
                               ["AirPressure", "airpressure", "Air_Pressure", "air_pressure",
                                "Air Pressure", "Air Pressure (bar)", "AirPressure(bar)", "Air_Pressure_bar"])
        ap_field = air_press_col or ap_key
        set_cell(
            3, c_idx,
            trow.get(ap_key) if ap_key else None,
            CellBinding("tblTrial", "ID", trow.get("ID"), ap_field) if (ap_field and trow.get("ID")) else None,
        )

    # Dynamische Felder (ply fields: the column's first ply "sr", also in the Groups view)
    start_row = len(titles_fixed)
    for offset, fdef in enumerate(field_map):
        r_idx = start_row + offset
        storage = fdef.get("StorageTable", "tbltrial")
        colname = fdef["ColName"]

        if storage == "tbltrialsettings" and settings_cols_map:
            real_col = settings_cols_map.get(colname.lower()) or colname
            for c_idx, cs in enumerate(col_specs):
                sr = cs["sr"]
                val = sr.get(real_col) if sr else None
                binding = CellBinding("tblTrialSettings", "ID", sr["ID"], real_col) if sr else None
                set_cell(r_idx, c_idx, val, binding)
        else:
            real_col = trial_cols_map.get(str(colname).lower()) or colname
            for c_idx, cs in enumerate(col_specs):
                trow = cs["trial"]
                val = trow.get(real_col)
                set_cell(
                    r_idx, c_idx, val,
                    CellBinding("tblTrial", "ID", trow.get("ID"), real_col) if trow.get("ID") else None,
                )


def rd_display_text(rd: RDMachineData, r: int, c: int, jets_map: Optional[Dict[Any, str]] = None,
                    housing_map: Optional[Dict[Any, str]] = None) -> str:
    """Cell text as the desktop shows it: row 0 = housing name, row 1 = jet name, dropdown
    rows (W3 Jet, W3 Housing, Top Plate ...) = name from rd.dropdown_rows, else the value."""
    internal = _text(rd.cells[r][c][0])
    if r == HOUSING_ROW:
        return id_display(housing_map or {}, internal)
    if r == JET_ROW:
        return id_display(jets_map or {}, internal)
    if r in rd.dropdown_rows:
        return id_display(rd.dropdown_rows[r], internal)
    return internal


def rd_tooltip(rd: RDMachineData, r: int, c: int, jets_tooltip_map: Optional[Dict[Any, str]] = None,
               housing_image_map: Optional[Dict[Any, str]] = None) -> str:
    """Cell tooltip as MachinePivotModel gives it (same order): jet rows -> jet geometry
    (JetsLookup.tooltip_map, looked up by the stored value), housing rows -> housing image
    link (HousingLookup.image_map; the desktop shows the picture), OF row -> "Speed: N m/min"."""
    internal = _text(rd.cells[r][c][0])
    for rows, lookup in ((rd.jet_rows, jets_tooltip_map), (rd.housing_rows, housing_image_map)):
        if r in rows and internal not in (None, ""):
            try:
                key = int(internal)
            except Exception:
                key = internal
            tip = (lookup or {}).get(key) or (lookup or {}).get(str(key))
            if tip:
                return tip
    if rd.of_row is not None and r == rd.of_row and rd.of_speed_tooltips.get(c):
        return rd.of_speed_tooltips[c]
    return rd.cell_tooltips.get((r, c), "")
