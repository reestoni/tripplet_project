from __future__ import annotations

# db/experiment_requests.py
"""Experiment Requests without Qt - shared by the desktop screens and the web app.

Moved out of ui/screen_create_experiment_request.py (form, load, save),
ui/screen_my_requests.py (list, status changes, assign experiment, owner
notifications), ui/widgets/experiment_request_diff_dialog.py (side-by-side
comparison) and the read-only request popup in ui/screen_show_experiment.py
(2026-11-13, pure move - the desktop calls these functions, behaviour unchanged).

Everything that used app_meta.current_user takes a `user` dict instead (same keys
as app_meta.current_user: "id", "username", "access_level", ...).

The pending-change/versioning workflow itself lives in
db/experiment_request_changes.py (unchanged); images in
db/experiment_request_images.py.

Status IDs (tblRequestStatus): 1 Request, 2 Denied, 3 Approved, 4 Experiment.
A request without status (RequestStatus NULL) is a draft (created by an image
upload before the first save, see experiment_request_images.ensure_request_for_upload);
drafts are removed at login by db.connection.cleanup_draft_experiment_requests.
"""

import datetime
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from db.connection import (
    current_db_name,
    fetch_all,
    get_columns_map as _db_get_columns_map,
    get_connection,
    is_offline_mode,
    new_global_id,
    table_exists as _db_table_exists,
)
from db import experiment_request_changes as request_changes
from ui.text_normalize import resolve_field

TABLE = "tblExperimentRequests"

STATUS_REQUEST = 1
STATUS_DENIED = 2
STATUS_APPROVED = 3
STATUS_EXPERIMENT = 4

# Felder, die im Formular nicht angezeigt werden sollen
# (werden teils automatisch beim Speichern gesetzt)
# ChangeOfRequestID/PriorVersionOfID sind reine Kopie-/Versions-Metadaten
# (siehe db/experiment_request_changes.py), nie vom Nutzer editierbare Felder.
# DenialReason wird ausschliesslich ueber den Status-Wechsel "Denied"
# (My Requests, set_status()) gesetzt - im Formular nur lesend als Banner
# angezeigt, siehe denial_banner_text().
EXCLUDE_FIELDS = {
    "ID", "Timestamp", "CreatedBy", "RequestStatus", "ChangeOfRequestID",
    "PriorVersionOfID", "DenialReason",
}

# Mehrzeilige Felder (3 Zeilen)
MULTILINE_FIELDS = {
    "Versuchsgrund",
    "Aufgabe",
    "Versuchsumfang",
    "Beurteilungsparameter",
    "Versuchsbedingungen",
    "Versuchsort",
    "Bemerkungen",
}

DATE_FIELDS = {"Wunschtermin"}

# Pflichtfelder (Save nur aktiv, wenn diese gefüllt sind)
# (Im DB-Schema kann der Feldname entweder "Versuchsgrund" oder "FVersuchsgrund" sein.)
REQUIRED_FIELDS = [
    "Titel",
    "FVersuchsgrund",
    "Versuchsgrund",
    "Aufgabe",
    "Beurteilungsparameter",
    "Versuchsbedingungen",
]

# (label used in the "Still missing" message, field names to look for)
REQUIRED_CHECKS: List[Tuple[str, Tuple[str, ...]]] = [
    ("Titel", ("Titel",)),
    ("Versuchsgrund", ("FVersuchsgrund", "Versuchsgrund")),
    ("Aufgabe", ("Aufgabe",)),
    ("Beurteilungsparameter", ("Beurteilungsparameter",)),
    ("Versuchsbedingungen", ("Versuchsbedingungen",)),
]

MISSING_MESSAGE = (
    "Please fill in at least title, reason for experiment, task, evaluation parameters and test conditions."
)

# My Requests: texts shown on rows (also used by the web list)
PENDING_TOOLTIP = "There is a change proposal for this request that is not approved yet (waiting for a superuser)."
NEW_TOOLTIP = "New request, not reviewed yet."

# Columns of the list query that are never shown as their own column (DenialReason
# only as tooltip on the status). CreatedByUser ("Owner") only for superusers.
LIST_HIDDEN_COLUMNS = {"CreatedBy", "Projekt", "ID", "Timestamp", "DenialReason"}
# Long free-text columns, hidden by default in My Requests ("Show details").
LIST_DETAIL_COLUMNS = {
    "Versuchsgrund", "Aufgabe", "Versuchsumfang", "Beurteilungsparameter",
    "Versuchsbedingungen", "Versuchsort", "Bemerkungen",
}

_UNSET = object()


# ======================================================================
# Users / permissions
# ======================================================================

def user_id(user: Optional[dict]) -> Any:
    return (user or {}).get("id")


def is_superuser(user: Optional[dict]) -> bool:
    """AccessLevel >= 4 (same rule as app_meta.is_superuser_level())."""
    try:
        return int((user or {}).get("access_level") or 0) >= 4
    except Exception:
        return False


def can_open(user: Optional[dict], row: Optional[Dict[str, Any]]) -> bool:
    """Who may open/edit a request row: superusers all, everybody else only the
    rows they created (My Requests only lists their own rows to them)."""
    if not row:
        return False
    if is_superuser(user):
        return True
    uid = user_id(user)
    owner = row.get("CreatedBy")
    return uid not in (None, "") and owner not in (None, "") and str(uid) == str(owner)


# ======================================================================
# Schema / FK lookups (moved from ui/screen_create_experiment_request.py)
# ======================================================================

@dataclass
class ColumnInfo:
    """Metadaten einer DB-Spalte (Name, Typ, Nullable, FK-Info) für das dynamische Formular."""
    name: str
    data_type: Optional[int] = None
    type_name: Optional[str] = None


def try_tables_for_fk(field_name: str) -> List[str]:
    """Ermittelt mögliche FK-Lookup-Tabellen für einen Feldnamen (heuristisch)."""
    """Heuristik: <X>ID → tblX, tblXs, tblXes"""
    base = field_name[:-2] if field_name.lower().endswith("id") else field_name
    base = base.strip().strip("_")
    if not base:
        return []
    cands = [f"tbl{base}", f"tbl{base}s", f"tbl{base}es"]
    # häufige Sonderfälle
    if base.lower() == "user":
        cands = ["tblUser", "tblUsers"]
    return cands


def pick_display_column(table: str) -> Optional[str]:
    """Wählt die beste Anzeigespalte einer FK-Lookup-Tabelle (Name, Bezeichnung o.ä.)."""
    """Wählt eine sinnvolle Anzeigespalte für Dropdowns."""
    preferred = ["Name", "Username", "Title", "Bezeichnung", "Beschreibung", "DisplayName"]
    # MySQL: information_schema
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (current_db_name(), table.lower()),
        )
        rows = cur.fetchall()
        cols = [r[0] for r in rows] if rows else []
    for p in preferred:
        if p in cols:
            return p
    # sonst: erste Textspalte (type_name enthält oft VARCHAR/TEXT)
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (current_db_name(), table.lower()),
        )
        for name, data_type in cur.fetchall() or []:
            tn = str(data_type or "").lower()
            if any(x in tn for x in ["char", "text", "varchar"]):
                return str(name)
    return None


def get_table_columns(table: str) -> List[ColumnInfo]:
    """Lädt alle Spalten einer Tabelle als ColumnInfo-Liste aus der DB.

    tblExperimentRequests ist nicht Teil der Offline-SQLite-Kopie (kein
    ROOT_TABLES-Eintrag, siehe db/offline_schema.py) - die Screens sind im
    Offline-Modus ohnehin per Navigation-Guard gesperrt. Der SQLite-Zweig hier
    sorgt nur dafür, dass ein versehentlicher Aufruf (z.B. durch die eager
    Konstruktion in main.py) sauber "keine Spalten gefunden" statt eines
    information_schema-Fehlers (SQLite kennt information_schema nicht)
    zurückgibt, statt die ganze App am Start zu blockieren.
    """
    if is_offline_mode():
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(f'PRAGMA table_info("{table}")')
            cols: List[ColumnInfo] = []
            for _cid, name, col_type, *_rest in cur.fetchall() or []:
                cols.append(ColumnInfo(name=str(name), data_type=None, type_name=str(col_type or "")))
            return cols

    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            """
            SELECT column_name, data_type, column_type
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (current_db_name(), table.lower()),
        )
        cols: List[ColumnInfo] = []
        for name, data_type, column_type in cur.fetchall() or []:
            cols.append(ColumnInfo(name=str(name), data_type=None, type_name=str(column_type)))
        return cols


def table_exists_info(table: str) -> bool:
    """Gibt True zurück wenn die Tabelle in der DB existiert (uncached, information_schema)."""
    if is_offline_mode():
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND lower(name) = ? LIMIT 1",
                (table.lower(),),
            )
            return cur.fetchone() is not None

    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
            LIMIT 1
            """,
            (current_db_name(), table.lower()),
        )
        return cur.fetchone() is not None


def is_guid_col(col: ColumnInfo) -> bool:
    """Gibt True zurück wenn eine Spalte als GUID-Feld erkannt wird (ID/GlobalID-Typ)."""
    # MySQL: GUIDs werden bei uns als VARCHAR gespeichert
    tn = str(col.type_name or "").lower()
    return "char(36" in tn or "varchar(36" in tn


def load_columns(table: str = TABLE) -> List[ColumnInfo]:
    """All columns of tblExperimentRequests (RuntimeError "Table not found" if missing)."""
    if not table_exists_info(table):
        raise RuntimeError(f"Table not found: {table}")
    return get_table_columns(table)


def form_field_names(cols: List[ColumnInfo]) -> List[str]:
    """Names of the editable form fields, in column order."""
    return [c.name for c in cols if c.name not in EXCLUDE_FIELDS]


def load_fk_choices(field_name: str) -> List[Tuple[Any, str]]:
    """Versucht für <X>ID eine Lookup-Tabelle zu finden und (id,label) zu laden."""
    table_cands = try_tables_for_fk(field_name)
    target_table = next((t for t in table_cands if table_exists_info(t)), None)
    if not target_table:
        return []

    display_col = pick_display_column(target_table)
    if not display_col:
        return []

    # id spalte bestimmen
    cols = [c.name for c in get_table_columns(target_table)]
    id_col = None
    for cand in ["ID", f"{field_name}"]:
        if cand in cols:
            id_col = cand
            break
    if not id_col:
        # first column ending with ID
        for c in cols:
            if c.lower().endswith("id"):
                id_col = c
                break
    if not id_col:
        return []

    sql = f"SELECT [{id_col}] AS _id, [{display_col}] AS _txt FROM [{target_table}] ORDER BY [{display_col}]"
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
    out: List[Tuple[Any, str]] = []
    for r in rows:
        out.append((r[0], r[1]))
    return out


def load_project_choices() -> List[Tuple[Any, str]]:
    """Lädt Projekte aus tblProject.

    Anzeige im Dropdown: "Project Number" + "Project Name".
    Gespeicherter Wert: tblProject.ID
    """
    table = "tblProject"
    if not table_exists_info(table):
        return []

    cols_map = {c.name.lower(): c.name for c in get_table_columns(table)}
    id_col = cols_map.get("id")
    num_col = cols_map.get("projectnumber") or cols_map.get("project number")
    name_col = cols_map.get("projectname") or cols_map.get("project name")
    if not (id_col and num_col and name_col):
        return []

    sql = (
        f"SELECT [{id_col}] AS _id, [{num_col}] AS _num, [{name_col}] AS _name "
        "FROM tblProject "
        f"ORDER BY [{num_col}], [{name_col}]"
    )
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()

    out: List[Tuple[Any, str]] = []
    for _id, num, name in rows:
        num_s = "" if num is None else str(num).strip()
        name_s = "" if name is None else str(name).strip()
        if num_s and name_s:
            label = f"{num_s} – {name_s}"
        else:
            label = num_s or name_s or str(_id)
        out.append((_id, label))
    return out


def form_fields(cols: List[ColumnInfo]) -> List[Dict[str, Any]]:
    """The create/edit form, in column order.

    Each field: {"name", "label", "type", "choices", "required"}
      type "fk"        -> dropdown, `choices` = [(value, label), ...]; the empty
                          choice (None) is always allowed in addition
                          (Projekt = tblProject with "number – name" labels,
                          other ...ID columns via the tblX/tblXs lookup heuristic)
      type "date"      -> date (Wunschtermin; the desktop defaults it to today)
      type "multiline" -> multi-line text (3 lines)
      type "text"      -> single-line text (also FK/Projekt columns whose lookup
                          table could not be found)
    `required` follows REQUIRED_FIELDS (Versuchsgrund may be called FVersuchsgrund).
    """
    out: List[Dict[str, Any]] = []
    for col in cols:
        name = col.name
        if name in EXCLUDE_FIELDS:
            continue
        kind, choices = "text", None
        if name == "Projekt":
            choices = load_project_choices()
            kind = "fk" if choices else "text"
        elif name in DATE_FIELDS:
            kind = "date"
        elif name in MULTILINE_FIELDS:
            kind = "multiline"
        elif name.lower().endswith("id") and name != "ID":
            choices = load_fk_choices(name)
            kind = "fk" if choices else "text"
        out.append({"name": name, "label": name, "type": kind,
                    "choices": choices if kind == "fk" else None,
                    "required": name in REQUIRED_FIELDS})
    return out


def form_schema() -> List[Dict[str, Any]]:
    """form_fields() for the current table (web)."""
    return form_fields(load_columns())


# ======================================================================
# Values / validation
# ======================================================================

def _norm_name(s: str) -> str:
    s = (s or "").strip().lower()
    # entferne typische SQL/ODBC-Zeichen und Trennzeichen
    s = s.replace("`", "").replace("[", "").replace("]", "")
    s = s.replace(" ", "").replace("_", "")
    return s


def find_key(keys, field_name: str) -> Optional[str]:
    """Sucht einen Feldnamen in `keys` (robust gegen Access→MySQL: Gross/Klein,
    Spaces/Underscores, Backticks, <name> ↔ <name>ID) - same matching the form
    uses for its widgets."""
    keys = list(keys)
    if field_name in keys:
        return field_name
    target_raw = (field_name or "").strip()
    if not target_raw:
        return None
    target = _norm_name(target_raw)
    for k in keys:
        if _norm_name(k) == target:
            return k
    if not target.endswith("id"):
        target_id = target + "id"
        for k in keys:
            if _norm_name(k) == target_id:
                return k
    else:
        target_noid = target[:-2]
        for k in keys:
            if _norm_name(k) == target_noid:
                return k
    return None


def has_value(v: Any) -> bool:
    """A form value counts as filled when it is not None/blank."""
    return v is not None and str(v).strip() != ""


def validate(values: Dict[str, Any]) -> List[str]:
    """Missing required fields (labels as in the desktop message: Titel,
    Versuchsgrund, Aufgabe, Beurteilungsparameter, Versuchsbedingungen).
    Empty list = valid."""
    missing: List[str] = []
    for label, names in REQUIRED_CHECKS:
        key = None
        for n in names:
            key = find_key(values.keys(), n)
            if key is not None:
                break
        if key is None or not has_value(values.get(key)):
            missing.append(label)
    return missing


def missing_message(missing: List[str]) -> str:
    msg = MISSING_MESSAGE
    if missing:
        msg += "\n\nStill missing: " + ", ".join(missing)
    return msg


def coerce_values(values: Dict[str, Any], cols: Optional[List[ColumnInfo]] = None) -> Dict[str, Any]:
    """Web helper: turn submitted form data into the values the desktop form
    produces - every form field present (missing = None), strings stripped and
    "" -> None, date fields as datetime.date (ISO "YYYY-MM-DD" or dd.mm.yyyy),
    dropdown values as given. Unknown keys are dropped."""
    names = form_field_names(cols if cols is not None else load_columns())
    out: Dict[str, Any] = {}
    for n in names:
        v = values.get(n)
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                v = None
        if n in DATE_FIELDS and isinstance(v, str):
            for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
                try:
                    v = datetime.datetime.strptime(v[:10], fmt).date()
                    break
                except Exception:
                    continue
        if n in DATE_FIELDS and isinstance(v, datetime.datetime):
            v = v.date()
        out[n] = v
    return out


def has_changes(values: Dict[str, Any], loaded: Dict[str, Any], field_names) -> bool:
    """True, wenn sich mindestens ein Feld gegenueber dem beim Laden
    vorgefundenen Stand geaendert hat. Ohne Snapshot (z.B. brandneuer
    Request) immer True."""
    if not loaded:
        return True

    def _norm(v: Any) -> Any:
        if v is None:
            return ""
        if isinstance(v, str):
            return v.strip()
        return v

    for key in field_names:
        if _norm(values.get(key)) != _norm(loaded.get(key)):
            return True
    return False


def with_auto_fields(user: dict, cols: List[ColumnInfo], values: Dict[str, Any],
                      request_status: Any) -> Dict[str, Any]:
    """Form values + the fields set automatically on insert (same order as the
    desktop form: fields, Timestamp, CreatedBy, RequestStatus)."""
    out = dict(values)
    # Auto-Felder nur beim Insert
    out["Timestamp"] = datetime.datetime.now()
    out["CreatedBy"] = user_id(user)
    # RequestStatus soll beim Erstellen automatisch gesetzt werden (nicht im Formular sichtbar)
    if any(c.name == "RequestStatus" for c in cols):
        out["RequestStatus"] = request_status
    return out


# ======================================================================
# Load
# ======================================================================

def fetch_request(request_id: Any) -> Optional[Dict[str, Any]]:
    """SELECT * of one request row as {column: value}, None if not found."""
    if request_id in (None, ""):
        return None
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(f"SELECT * FROM [{TABLE}] WHERE [ID]=?", [request_id])
        row = cur.fetchone()
        if not row:
            return None
        col_names = [d[0] for d in (cur.description or [])]
    return {str(col_names[i]): row[i] for i in range(len(col_names))}


def denial_banner_text(values: Dict[str, Any]) -> Optional[str]:
    """Banner text of a denied request with a reason (None otherwise)."""
    denial_reason = values.get("DenialReason")
    if values.get("RequestStatus") == STATUS_DENIED and denial_reason:
        return f"⚠ This request was denied.\nReason: {denial_reason}"
    return None


def load_status_choices() -> List[Tuple[Any, str]]:
    """[(StatusID, StatusName)] from tblRequestStatus, ordered by RequestOrder ([] on error)."""
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            sql = (
                "SELECT [ID], [RequestStatus] "
                "FROM [tblRequestStatus] "
                "ORDER BY [RequestOrder] ASC"
            )
            cur.execute(sql)
            rows = cur.fetchall()
        out: List[Tuple[Any, str]] = []
        for r in rows:
            out.append((r[0], r[1]))
        return out
    except Exception:
        return []


def status_label(choices: List[Tuple[Any, str]], status_id: Any) -> str:
    for _id, _label in choices:
        if _id == status_id:
            return "" if _label is None else str(_label)
    return ""


def load_request(request_id: Any, user: Optional[dict] = None) -> Optional[Dict[str, Any]]:
    """Everything the edit form and the read-only popup show for one request
    (web). None if the row does not exist; PermissionError if `user` is given
    and may not open it (see can_open()).

    {
      "id", "values": {column: raw value} (whole row),
      "form": {field: value} (editable fields only),
      "title": Titel (stripped), "status_id", "status_label",
      "denial_reason", "denial_banner": text or None,
      "change_of_id": original ID if this row is itself a pending change copy,
      "prior_version_of_id": live ID if this row is an archived version,
      "pending_change_id": open change copy of this row (or None),
      "history_target_id": row whose version history applies,
      "versions": [{"ID", "Timestamp", "CreatedByUser"}] newest first,
      "display": [{"name", "label", "text", "multiline"}] as the popup shows it,
      "popup_title", "images": experiment_request_images.list_images(),
    }
    """
    from db import experiment_request_images as images

    values = fetch_request(request_id)
    if values is None:
        return None
    if user is not None and not can_open(user, values):
        raise PermissionError("You can only open your own requests.")
    cols = get_table_columns(TABLE)
    choices = load_status_choices()
    history_target = values.get("PriorVersionOfID") or request_id
    return {
        "id": values.get("ID", request_id),
        "values": values,
        "form": {n: values.get(n) for n in form_field_names(cols)},
        "title": "" if values.get("Titel") is None else str(values.get("Titel")).strip(),
        "status_id": values.get("RequestStatus"),
        "status_label": status_label(choices, values.get("RequestStatus")),
        "denial_reason": values.get("DenialReason"),
        "denial_banner": denial_banner_text(values),
        "change_of_id": values.get("ChangeOfRequestID"),
        "prior_version_of_id": values.get("PriorVersionOfID"),
        "pending_change_id": request_changes.get_pending_change_id(request_id),
        "history_target_id": history_target,
        "versions": request_changes.list_versions(history_target),
        "display": display_fields(cols, values),
        "popup_title": popup_title(values, request_id)[0],
        "images": images.list_images(request_id),
    }


# ======================================================================
# Read-only display (moved from _ExperimentRequestReadOnlyDialog)
# ======================================================================

def _table_exists(name: str) -> bool:
    return _db_table_exists(name.lower())


def _columns_map(table: str) -> Dict[str, str]:
    return _db_get_columns_map(table.lower())


def project_label(project_id: Any) -> str:
    """Gibt den lesbaren Projektnamen für eine Projekt-ID zurück ("number - name")."""
    if project_id in (None, ""):
        return ""
    for t in ("tblProject", "tblProjects"):
        if not _table_exists(t):
            continue
        try:
            cols = _columns_map(t)
            f_num = resolve_field(
                ["Project Number", "ProjectNumber", "Projekt Nummer", "ProjektNummer", "Number", "Nr"], cols)
            f_name = resolve_field(
                ["Project Name", "ProjectName", "Projekt Name", "ProjektName", "Name", "Titel", "Title"], cols)
            if not (f_num and f_name):
                continue
            rows = fetch_all(f"SELECT [{f_num}] AS PN, [{f_name}] AS PName FROM [{t}] WHERE [ID]=?", [project_id])
            if rows:
                pn = rows[0].get("PN")
                pnm = rows[0].get("PName")
                pn = "" if pn is None else str(pn)
                pnm = "" if pnm is None else str(pnm)
                out = (pn + " - " + pnm).strip(" -")
                return out
        except Exception:
            continue
    return str(project_id)


def fk_label(field_name: str, fk_id: Any) -> str:
    """Gibt den lesbaren FK-Namen für eine FK-ID zurück (heuristisches Lookup).
    CreatedBy -> "username (First Last)", Projekt -> project_label()."""
    if fk_id in (None, ""):
        return ""

    # Special case: tblExperimentRequests.CreatedBy -> tblUser.ID
    # In popups we want a friendly label, not the raw ID.
    if field_name.lower() in {"createdby", "createdbyid"}:
        for t in ("tblUser", "tblUsers"):
            if not _table_exists(t):
                continue
            try:
                cols = _columns_map(t)
                f_user = resolve_field(["Username", "UserName", "Login", "Name"], cols)
                if not f_user:
                    continue
                f_first = resolve_field(["FirstName", "First Name", "Vorname", "GivenName"], cols)
                f_last = resolve_field(["LastName", "Last Name", "Nachname", "Surname", "FamilyName"], cols)

                sel = [f"[{f_user}] AS U"]
                sel.append(f"[{f_first}] AS FN" if f_first else "NULL AS FN")
                sel.append(f"[{f_last}] AS LN" if f_last else "NULL AS LN")
                sql = f"SELECT {', '.join(sel)} FROM [{t}] WHERE [ID]=?"
                rows = fetch_all(sql, [fk_id])
                if rows:
                    u = rows[0].get("U")
                    if u is None:
                        return str(fk_id)
                    u_s = str(u).strip()
                    fn = rows[0].get("FN")
                    ln = rows[0].get("LN")
                    fn_s = "" if fn is None else str(fn).strip()
                    ln_s = "" if ln is None else str(ln).strip()

                    full = (fn_s + " " + ln_s).strip()
                    # Desired format: Username (FirstName LastName)
                    return f"{u_s} ({full})" if full else u_s
            except Exception:
                continue
        return str(fk_id)

    if field_name.lower() in {"projekt", "project", "projectid", "projektid"}:
        return project_label(fk_id)

    for t in try_tables_for_fk(field_name):
        if not _table_exists(t):
            continue
        disp = pick_display_column(t)
        if not disp:
            continue
        try:
            rows = fetch_all(f"SELECT [ID] AS ID, [{disp}] AS D FROM [{t}] WHERE [ID]=?", [fk_id])
            if rows:
                d = rows[0].get("D")
                return "" if d is None else str(d)
        except Exception:
            continue
    return str(fk_id)


def display_text(field_name: str, val: Any) -> str:
    """Read-only text of one field: FK columns as labels, Wunschtermin as dd.mm.yyyy."""
    # If looks like FK, render label
    try:
        looks_fk = (
                field_name.lower().endswith('id')
                or field_name.lower() in {'projekt', 'project', 'createdby', 'createdbyid'}
        )
    except Exception:
        looks_fk = False

    if looks_fk and val not in (None, ""):
        txt = fk_label(field_name, val)
    else:
        txt = "" if val is None else str(val)

    if field_name in DATE_FIELDS and txt:
        # keep raw string; Access via ODBC can be datetime/date
        # Normalize to dd.MM.yyyy (no time)
        try:
            from datetime import datetime, date
            if isinstance(val, (datetime, date)):
                txt = val.strftime("%d.%m.%Y")
            else:
                s = str(txt).strip()
                # common Access/ODBC representations
                s = s.replace("T", " ")
                # strip timezone if present
                s = re.sub(r"(Z|[+-]\d{2}:\d{2})$", "", s).strip()
                # keep only date part if time is present
                s_date = s.split(" ")[0]
                if re.match(r"^\d{4}-\d{2}-\d{2}$", s_date):
                    dt = datetime.strptime(s_date, "%Y-%m-%d")
                    txt = dt.strftime("%d.%m.%Y")
                elif re.match(r"^\d{2}\.\d{2}\.\d{4}$", s_date):
                    txt = s_date  # already desired
                else:
                    # try a couple more common formats
                    for fmt in ("%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y"):
                        try:
                            dt = datetime.strptime(s_date, fmt)
                            txt = dt.strftime("%d.%m.%Y")
                            break
                        except Exception:
                            continue
        except Exception:
            pass
    return txt


def display_fields(cols: List[ColumnInfo], data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Rows of the read-only popup: every column except Titel (it is the title)
    and the meta fields, but WITH CreatedBy (label "Created By").
    Each: {"name", "label", "text", "multiline"}."""
    out: List[Dict[str, Any]] = []
    for c in cols:
        fn = c.name
        # Titel is shown in the popup header; do not repeat it inside the form.
        if fn.lower() in ("titel", "title"):
            continue
        # In the create-screen we exclude CreatedBy, but in the read-only popup we DO want it.
        if fn in EXCLUDE_FIELDS and fn.lower() != "createdby":
            continue
        label_txt = "Created By" if fn.lower() == "createdby" else fn
        out.append({"name": fn, "label": label_txt, "text": display_text(fn, data.get(fn)),
                    "multiline": fn in MULTILINE_FIELDS})
    return out


def popup_title(data: Dict[str, Any], request_id: Any, prefix: str = "") -> Tuple[str, str]:
    """(window title, header rich text) of the read-only popup - Titel, or
    "Experiment Request #<id>" when it is empty."""
    req_title = "" if data.get("Titel") is None else str(data.get("Titel")).strip()
    if req_title:
        safe = req_title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f"{prefix}{req_title}", f"{prefix}<b>{safe}</b>"
    # Fallback: keep prior behaviour if Titel is missing/empty.
    return (f"{prefix}Experiment Request #{request_id}",
            f"{prefix}Experiment Request <b>#{request_id}</b>")


# ======================================================================
# Save (moved from CreateExperimentRequestScreen._save)
# ======================================================================

@dataclass
class SaveResult:
    """kind:
      "inserted"  new request saved (RequestStatus 1), request_id = new ID (if known)
      "updated"   row overwritten directly (superuser, a change copy itself, or an
                  environment without change tracking); a live row was archived first
      "proposal"  normal user edited a saved request: change copy created/updated,
                  request_id = ID of the copy, the original stays unchanged
      "unchanged" nothing changed - nothing written
      "invalid"   required fields missing (`missing`, `message`)
      "no_user"   no user id - nothing written
      "nothing"   no values to write
    `title`/`message` are the texts the desktop shows."""
    kind: str
    request_id: Any = None
    title: str = ""
    message: str = ""
    missing: List[str] = field(default_factory=list)


def save_request(user: dict, request_id: Any, values: Dict[str, Any], *,
                 cols: Optional[List[ColumnInfo]] = None,
                 field_names: Optional[List[str]] = None,
                 loaded_values: Any = _UNSET,
                 change_of_id: Any = _UNSET) -> SaveResult:
    """Save the form `values` ({field: value} of the editable fields) as `user`.

    request_id None/"" -> insert a new request (RequestStatus 1). Otherwise the
    decision tree of the desktop form:
      - nothing changed against the loaded state -> "unchanged" (no write);
      - the row is itself a change copy, or the user is a superuser, or the
        environment has no ChangeOfRequestID column -> direct UPDATE of the form
        fields (a live row is archived as prior version first, best-effort);
        RequestStatus is never touched;
      - otherwise (normal user, saved request) -> change copy for review
        (experiment_request_changes.create_or_update_pending_change).

    Desktop passes `loaded_values` (snapshot taken right after loading, {} = no
    snapshot -> always "changed") and `change_of_id`. When they are not passed
    (web), the current row is read, checked with can_open() (PermissionError)
    and used as the snapshot. Values are completed to all form fields
    (missing = None) - send the whole form.
    """
    if cols is None:
        cols = load_columns()
    if field_names is None:
        field_names = form_field_names(cols)
    values = {k: values.get(k) for k in field_names}

    missing = validate(values)
    if missing:
        return SaveResult("invalid", request_id, "Missing information", missing_message(missing), missing)

    is_insert = request_id in (None, "")

    # A draft (RequestStatus NULL, created only so images could be uploaded before the
    # first save - create_draft()) is finalised like a new request: form values +
    # Timestamp/CreatedBy + RequestStatus 1. Before 2026-11-13 it took the "edit" path:
    # a normal user got a change proposal on the draft, a superuser an archived update -
    # and the draft stayed NULL, so the login cleanup later deleted it with its images.
    if not is_insert:
        draft = fetch_request(request_id)
        if (draft is not None and draft.get("RequestStatus") is None
                and draft.get("ChangeOfRequestID") in (None, "")
                and draft.get("PriorVersionOfID") in (None, "")):
            if not can_open(user, draft):
                raise PermissionError("You can only edit your own requests.")
            vals = with_auto_fields(user, cols, values, STATUS_REQUEST)
            if vals.get("CreatedBy") in (None, ""):
                return SaveResult("no_user", None, "Login missing",
                                  "CreatedBy could not be set because no user ID was found. Please log in again.")
            set_cols = [k for k in vals if k != "ID"]
            sql = f"UPDATE [{TABLE}] SET " + ",".join(f"[{c}]=?" for c in set_cols) + " WHERE [ID]=?"
            with get_connection() as cn:
                cur = cn.cursor()
                cur.execute(sql, [vals[c] for c in set_cols] + [request_id])
                try:
                    cn.commit()
                except Exception:
                    pass
            return SaveResult("inserted", request_id, "Saved", "Experiment request saved.")

    if is_insert:
        values = with_auto_fields(user, cols, values, STATUS_REQUEST)
        # CreatedBy muss beim Insert vorhanden sein
        if values.get("CreatedBy") in (None, ""):
            return SaveResult("no_user", None, "Login missing",
                              "CreatedBy could not be set because no user ID was found. Please log in again.")
        # ID: falls GUID/Text → setzen, ansonsten weglassen (Autonumber)
        id_col = next((c for c in cols if c.name == "ID"), None)
        if id_col and is_guid_col(id_col):
            values["ID"] = new_global_id()

        ins_cols = [k for k, v in values.items() if v is not None]
        if not ins_cols:
            return SaveResult("nothing", None, "Note", "Nothing to save.")

        placeholders = ",".join(["?"] * len(ins_cols))
        col_sql = ",".join([f"[{c}]" for c in ins_cols])
        sql = f"INSERT INTO [{TABLE}] ({col_sql}) VALUES ({placeholders})"
        params = [values[c] for c in ins_cols]

        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(sql, params)
            try:
                cn.commit()
            except Exception:
                pass
            new_id = getattr(cur, "lastrowid", None)
        if new_id in (None, 0, "") and values.get("ID") is not None:
            new_id = values.get("ID")
        return SaveResult("inserted", new_id, "Saved", "Experiment request saved.")

    if loaded_values is _UNSET or change_of_id is _UNSET:
        row = fetch_request(request_id)
        if row is None:
            raise LookupError("The selected request was not found.")
        if not can_open(user, row):
            raise PermissionError("You can only edit your own requests.")
        if change_of_id is _UNSET:
            change_of_id = row.get("ChangeOfRequestID")
        if loaded_values is _UNSET:
            loaded_values = {k: row.get(k) for k in field_names}
            for k in field_names:
                if k in DATE_FIELDS and isinstance(loaded_values.get(k), datetime.datetime):
                    loaded_values[k] = loaded_values[k].date()

    # Nichts geaendert? Dann gar nichts schreiben - kein Status-
    # Wechsel, keine Kopie (haeufigster Fall: Request nur zum
    # Ansehen geoeffnet und wieder gespeichert).
    if not has_changes(values, loaded_values or {}, field_names):
        return SaveResult("unchanged", request_id)

    superuser = is_superuser(user)
    change_tracking_on = request_changes.supports_change_tracking()
    upd_cols = [k for k in values.keys() if k in field_names]

    if change_of_id is not None or superuser or not change_tracking_on:
        # Diese Zeile ist entweder selbst schon eine offene
        # Aenderungs-Kopie (noch nicht freigegeben, direktes
        # Ueberschreiben also unbedenklich), ein Superuser
        # bearbeitet direkt, oder diese Umgebung hat die
        # ChangeOfRequestID-Spalte noch nicht - in allen drei Faellen kein
        # Kopie-Umweg, und RequestStatus bleibt unangetastet.
        if not upd_cols:
            return SaveResult("nothing", request_id, "Note", "Nothing to save.")

        # A superuser directly editing a LIVE row (no copy
        # detour, see above) still overwrites it immediately -
        # archive its prior state first (user request 2026-09-01:
        # version history should be traceable for the user too).
        # If this row is itself already an open pending change
        # (change_of_id set), it's not "live" - no archive
        # needed. Best-effort: a failure here must not block the
        # actual save.
        set_clause = ",".join([f"[{c}]=?" for c in upd_cols])
        sql = f"UPDATE [{TABLE}] SET {set_clause} WHERE [ID]=?"
        params = [values.get(c) for c in upd_cols] + [request_id]

        # Archive + update in ONE transaction (2026-11-13): before, a failed update
        # left an archived "version" of a change that never happened. The archive
        # itself stays best-effort - its failure still must not block the save.
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute("START TRANSACTION")   # pool is autocommit=True
            try:
                if change_of_id is None and request_changes.supports_versioning():
                    try:
                        request_changes._archive_current_version_on(cur, request_id)
                    except Exception:
                        pass
                cur.execute(sql, params)
                cn.commit()
            except Exception:
                try:
                    cn.rollback()
                except Exception:
                    pass
                raise
        return SaveResult("updated", request_id, "Saved", "Experiment request updated.")

    # Normaler Nutzer bearbeitet ein bereits gespeichertes
    # Original: das Original bleibt unangetastet (inkl. Status
    # und einer evtl. schon verknuepften Experiment-Zeile) -
    # die Aenderung geht als Kopie zur Pruefung an die
    # Superuser (siehe db/experiment_request_changes.py).
    copy_id = request_changes.create_or_update_pending_change(
        original_id=request_id,
        values=values,
        created_by=user_id(user),
    )
    return SaveResult(
        "proposal", copy_id, "Submitted for review",
        "Your changes were saved as a proposal and are waiting for approval by a superuser. Until "
        "then the existing request stays unchanged.",
    )


def create_draft(user: dict, values: Dict[str, Any], cols: Optional[List[ColumnInfo]] = None) -> Any:
    """Insert the form as a DRAFT (RequestStatus NULL, no required-field check)
    and return its ID - needed when images are uploaded before the first save.
    RuntimeError without user id or when the new ID cannot be determined."""
    created_by = user_id(user)
    if created_by in (None, ""):
        raise RuntimeError(
            "CreatedBy/UserID could not be determined. Please log in again."
        )
    if cols is None:
        cols = load_columns()

    # Wir sammeln aktuelle Formwerte (falls schon etwas ausgefuellt ist),
    # setzen aber RequestStatus bewusst auf NULL.
    values = with_auto_fields(user, cols, values, None)

    # ID: falls GUID/Text → setzen, ansonsten weglassen (Autonumber)
    id_col = next((c for c in cols if c.name == "ID"), None)
    if id_col and is_guid_col(id_col):
        values["ID"] = new_global_id()

    ins_cols = [k for k, v in values.items() if v is not None]
    if not ins_cols:
        # mindestens diese Felder setzen
        values["Timestamp"] = datetime.datetime.now()
        values["CreatedBy"] = created_by
        ins_cols = ["Timestamp", "CreatedBy"]

    placeholders = ",".join(["?"] * len(ins_cols))
    col_sql = ",".join([f"[{c}]" for c in ins_cols])
    sql = f"INSERT INTO [{TABLE}] ({col_sql}) VALUES ({placeholders})"
    params = [values[c] for c in ins_cols]

    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(sql, params)
        # autocommit=True, aber wir lassen commit trotzdem laufen
        try:
            cn.commit()
        except Exception:
            pass

        # mysql-connector liefert lastrowid; unser CursorWrapper proxied das.
        new_id = getattr(cur, "lastrowid", None)

        # Fallback: über LAST_INSERT_ID() (pro Connection)
        if new_id in (None, 0, ""):
            try:
                cur.execute("SELECT LAST_INSERT_ID()")
                row = cur.fetchone()
                if row and row[0] not in (None, 0, ""):
                    new_id = row[0]
            except Exception:
                pass
        # Falls GUID als PK verwendet wird, haben wir die ID bereits gesetzt
        if new_id in (None, 0, "") and values.get("ID") is not None:
            new_id = values.get("ID")

    if new_id in (None, 0, ""):
        raise RuntimeError("ExperimentRequestID could not be determined after the insert.")
    return new_id


# ======================================================================
# My Requests: list (moved from ui/screen_my_requests.py)
# ======================================================================

def fetch_request_rows(uid: Any, superuser: bool) -> Tuple[List[Any], List[str]]:
    """Raw rows of My Requests: er.* + ProjektText + CreatedByUser, newest first.
    Change copies and archived versions are never own rows; normal users only
    get their own requests."""
    with get_connection() as cn:
        cur = cn.cursor()
        sql = (
            "SELECT er.*, "
            "CONCAT_WS(' - ', p.ProjectNumber, p.ProjectName) AS ProjektText, "
            "u.[Username] AS CreatedByUser "
            "FROM ((tblExperimentRequests AS er "
            "LEFT JOIN tblProject AS p ON er.[Projekt]=p.[ID]) "
            "LEFT JOIN tblUser AS u ON er.[CreatedBy]=u.[ID]) "
        )

        # Aenderungs-Kopien (ChangeOfRequestID gesetzt) sind kein
        # eigenstaendiger Request - sie erscheinen nie als eigene
        # Zeile, sondern nur als Markierung auf ihrem Original.
        # Archived prior versions (PriorVersionOfID set, see
        # db/experiment_request_changes.py) are likewise not a
        # standalone row - pure read-only snapshots, visible only
        # through the version history dialog. Both columns don't
        # exist on every environment yet (dev is still pending as of
        # 2026-09-02) - drop the respective filter entirely on
        # environments without it, instead of "Unknown column".
        params: List[Any] = []
        where_clauses: List[str] = []
        if request_changes.supports_change_tracking():
            where_clauses.append("er.[ChangeOfRequestID] IS NULL")
        if request_changes.supports_versioning():
            where_clauses.append("er.[PriorVersionOfID] IS NULL")
        if not superuser:
            where_clauses.append("er.[CreatedBy]=?")
            params.append(uid)
        if where_clauses:
            sql += "WHERE " + " AND ".join(where_clauses) + " "

        sql += "ORDER BY er.[Timestamp] DESC"
        cur.execute(sql, params)
        rows = cur.fetchall()
        col_names = [d[0] for d in (cur.description or [])]
    return rows, col_names


def resolve_experiment_request_field() -> Optional[str]:
    """Findet das Feld in tblExperimente, das auf einen Experiment Request (ID) verweist."""
    try:
        if not _table_exists("tblExperimente"):
            return None
        cols = _columns_map("tblExperimente")
        return resolve_field(
            ["ExperimentRequest", "Experiment Request", "ExperimentRequestID", "ExperimentRequestId"],
            cols,
        )
    except Exception:
        return None


def experiment_ids_for_requests(request_ids: List[Any]) -> dict:
    """Liefert {RequestID: ExperimentID} für gegebene RequestIDs.

    Robust gegen unterschiedliche Feldnamen (Migration Access/MySQL).
    """
    out: dict = {}
    if not request_ids:
        return out

    er_field = resolve_experiment_request_field()
    if not er_field:
        return out

    try:
        cols = _columns_map("tblExperimente")
        expid_field = resolve_field(["ExperimentID", "Experiment ID", "ExperimentId"], cols) or "ExperimentID"
    except Exception:
        expid_field = "ExperimentID"

    chunk_size = 200
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            for i in range(0, len(request_ids), chunk_size):
                chunk = request_ids[i:i + chunk_size]
                placeholders = ",".join(["?"] * len(chunk))
                sql = (
                    f"SELECT [{expid_field}] AS ExpID, [{er_field}] AS ReqID "
                    f"FROM [tblExperimente] "
                    f"WHERE [{er_field}] IN ({placeholders})"
                )
                cur.execute(sql, list(chunk))
                rows = cur.fetchall()
                for r in rows or []:
                    exp_id = r[0]
                    req_id = r[1]
                    if req_id in (None, ""):
                        continue
                    out[req_id] = "" if exp_id is None else str(exp_id)
    except Exception:
        return out

    return out


def list_columns(col_names: List[str], superuser: bool) -> List[Tuple[int, str]]:
    """[(index in the row, column name)] of the columns My Requests shows."""
    hidden_cols = set(LIST_HIDDEN_COLUMNS)
    if not superuser:
        hidden_cols.add("CreatedByUser")
    return [(i, name) for i, name in enumerate(col_names) if name not in hidden_cols]


def list_header_label(name: str) -> str:
    if name == "ProjektText":
        return "Project"
    if name == "CreatedByUser":
        return "Owner"
    return name


def list_column_indices(col_names: List[str]) -> Dict[str, Optional[int]]:
    """Indices of id/requeststatus/createdby/titel/denialreason (case-insensitive)."""
    idx: Dict[str, Optional[int]] = {"id": None, "requeststatus": None, "createdby": None,
                                     "titel": None, "denialreason": None}
    for i, n in enumerate(col_names):
        ln = str(n).strip().lower()
        if ln in idx:
            idx[ln] = i
    return idx


def format_list_value(col_name: str, val: Any) -> Any:
    """Wunschtermin as dd.mm.yyyy, everything else unchanged."""
    if col_name == "Wunschtermin" and val not in (None, ""):
        try:
            # QDate / QDateTime
            if hasattr(val, "toString"):
                val = val.toString("dd.MM.yyyy")
            elif isinstance(val, (datetime.date, datetime.datetime)):
                val = val.strftime("%d.%m.%Y")
            else:
                s = str(val).strip()
                for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%d.%m.%Y"):
                    try:
                        val = datetime.datetime.strptime(s, fmt).strftime("%d.%m.%Y")
                        break
                    except Exception:
                        pass
        except Exception:
            pass
    return val


def is_new_unreviewed(status_id: Any, has_pending_change: bool) -> bool:
    """Status "Request" and no open change copy = brand-new, never reviewed."""
    return status_id == STATUS_REQUEST and not has_pending_change


def title_marker(has_pending_change: bool, new_unreviewed: bool) -> str:
    """Prefix of the title cell: "⏳ " open change proposal, "🆕 " new request."""
    if has_pending_change:
        return "⏳ "
    if new_unreviewed:
        return "🆕 "
    return ""


def status_tooltip(status_id: Any, has_pending_change: bool, new_unreviewed: bool, denial_reason: Any) -> str:
    parts: List[str] = []
    if has_pending_change:
        parts.append(PENDING_TOOLTIP)
    elif new_unreviewed:
        parts.append(NEW_TOOLTIP)
    if status_id == STATUS_DENIED and denial_reason:
        parts.append(f"Denial reason: {denial_reason}")
    return "\n".join(parts)


def status_options(choices: List[Tuple[Any, str]], current_status_id: Any,
                   superuser: bool) -> List[Tuple[str, Any, bool]]:
    """Entries of the status dropdown: [(label, id, selectable)].
    Normal users: empty entry + all statuses (dropdown read-only anyway).
    Superusers: no empty entry, "Experiment" only shown (not selectable) when it
    is the current status - it is set by assigning an experiment."""
    out: List[Tuple[str, Any, bool]] = []
    if not superuser:
        out.append(("", None, True))
    for _id, label in choices:
        lbl = "" if label is None else str(label)
        if superuser:
            if lbl.strip() == "":
                continue
            if lbl.strip().lower() == "experiment":
                if _id == current_status_id:
                    out.append((lbl, _id, False))
                continue
        out.append((lbl, _id, True))
    return out


def list_requests(user: dict, *, search: str = "", status_id: Any = None,
                  project: Optional[str] = None, owner: Optional[str] = None) -> Dict[str, Any]:
    """My Requests as data (web). Superusers see all requests, everybody else
    their own; change copies and archived versions are never own rows.

    Returns {
      "is_superuser", "info": status line text, "statuses": [(id, label)],
      "columns": [{"key", "label", "detail"}] (visible columns + "ExperimentID"),
      "projects": [...], "owners": [...] (filter options from the loaded rows),
      "total": rows before filtering,
      "rows": [{"id", "status_id", "status_label", "status_options",
                "status_editable", "owner_id", "owner", "title", "project",
                "denial_reason", "pending_change_id", "has_pending_change",
                "is_new_unreviewed", "experiment_id", "tooltip",
                "open_id" (row to open: a normal user's own open change copy,
                           else the request), "review" (superuser + open copy:
                           show the comparison instead of the form),
                "cells": {column key: display text}, "values": {column: raw}}]
    }
    Filters (all optional, like the desktop toolbar): `search` = case-insensitive
    substring over the displayed texts, `status_id`, `project` = project text,
    `owner` = owner username (superusers only).
    """
    uid = user_id(user)
    if uid in (None, ""):
        return {"is_superuser": False, "info": "No user logged in – no requests available.",
                "statuses": [], "columns": [], "projects": [], "owners": [], "total": 0, "rows": []}
    superuser = is_superuser(user)
    choices = load_status_choices()
    rows, col_names = fetch_request_rows(uid, superuser)
    ix = list_column_indices(col_names)
    id_idx, rs_idx, cb_idx, titel_idx, dr_idx = (ix["id"], ix["requeststatus"], ix["createdby"],
                                                ix["titel"], ix["denialreason"])

    exp_map: dict = {}
    if id_idx is not None and rs_idx is not None:
        try:
            exp_map = experiment_ids_for_requests(
                [r[id_idx] for r in rows if r[rs_idx] == STATUS_EXPERIMENT and r[id_idx] not in (None, "")])
        except Exception:
            exp_map = {}
    pending: dict = {}
    if id_idx is not None:
        try:
            pending = request_changes.get_pending_change_ids([r[id_idx] for r in rows if r[id_idx] not in (None, "")])
        except Exception:
            pending = {}

    visible = list_columns(col_names, superuser)
    proj_idx = col_names.index("ProjektText") if "ProjektText" in col_names else None
    owner_idx = col_names.index("CreatedByUser") if "CreatedByUser" in col_names else None

    out_rows: List[Dict[str, Any]] = []
    for row in rows:
        req_id = row[id_idx] if id_idx is not None else None
        sid = row[rs_idx] if rs_idx is not None else None
        has_pending = req_id in pending
        new_unrev = is_new_unreviewed(sid, has_pending)
        cells: Dict[str, str] = {}
        for c_src, name in visible:
            if c_src == rs_idx:
                continue
            val = format_list_value(name, row[c_src])
            txt = "" if val is None else str(val)
            if str(name).strip().lower() == "titel":
                txt = title_marker(has_pending, new_unrev) + txt
            cells[name] = txt
        exp_id = exp_map.get(req_id, "") or "" if sid == STATUS_EXPERIMENT and req_id not in (None, "") else ""
        cells["ExperimentID"] = str(exp_id)
        dr = row[dr_idx] if dr_idx is not None else None
        out_rows.append({
            "id": req_id, "status_id": sid, "status_label": status_label(choices, sid),
            "status_options": status_options(choices, sid, superuser), "status_editable": superuser,
            "owner_id": row[cb_idx] if cb_idx is not None else None,
            "owner": row[owner_idx] if owner_idx is not None else None,
            "title": str(row[titel_idx] or "") if titel_idx is not None else "",
            "project": row[proj_idx] if proj_idx is not None else None,
            "denial_reason": dr, "pending_change_id": pending.get(req_id),
            "has_pending_change": has_pending, "is_new_unreviewed": new_unrev,
            "experiment_id": exp_id, "tooltip": status_tooltip(sid, has_pending, new_unrev, dr),
            "open_id": pending.get(req_id) if (has_pending and not superuser) else req_id,
            "review": bool(has_pending and superuser),
            "cells": cells, "values": {str(col_names[i]): row[i] for i in range(len(col_names))},
        })

    projects = sorted({str(r["project"]) for r in out_rows if r["project"] not in (None, "")})
    owners = sorted({str(r["owner"]) for r in out_rows if r["owner"] not in (None, "")}) if superuser else []

    s = (search or "").strip().lower()
    shown = []
    for r in out_rows:
        if s and s not in " ".join(t for t in r["cells"].values() if t).lower():
            continue
        if status_id is not None and r["status_id"] != status_id:
            continue
        if project is not None and str(r["project"] or "") != project:
            continue
        if superuser and owner is not None and str(r["owner"] or "") != owner:
            continue
        shown.append(r)

    if superuser:
        info = f"{len(rows)} request(s) (superuser view: all)"
    else:
        info = f"{len(rows)} Request(s) fuer {(user or {}).get('username') or ''}"
    columns = [{"key": n, "label": list_header_label(n), "detail": n in LIST_DETAIL_COLUMNS}
               for _i, n in visible]
    columns.append({"key": "ExperimentID", "label": "Experiment ID", "detail": False})
    return {"is_superuser": superuser, "info": info, "statuses": choices, "columns": columns,
            "projects": projects, "owners": owners, "total": len(rows), "rows": shown}


# ======================================================================
# Notifications to the request owner
# ======================================================================

def notify_owner(user: Optional[dict], owner_id: Any, request_id: Any, message: str) -> None:
    """Benachrichtigt den Request-Besitzer (best-effort, siehe
    ui/notifications.py). Keine Selbst-Benachrichtigung, falls der
    Superuser sein eigenes Request bearbeitet."""
    if owner_id in (None, ""):
        return
    try:
        if str(owner_id) == str(user_id(user)):
            return
        from ui.notifications import create_experiment_request_notification
        create_experiment_request_notification(owner_id, request_id, message)
    except Exception:
        pass


def notify_owner_status_changed(user: Optional[dict], owner_id: Any, request_id: Any,
                                titel: str, new_status_label: str) -> None:
    label = titel.strip() or f"#{request_id}"
    notify_owner(user, owner_id, request_id, f"Request '{label}' status changed to {new_status_label}")


def notify_owner_of_request(user: Optional[dict], request_id: Any, message: str) -> None:
    """Wie notify_owner(), aber holt CreatedBy/Titel selbst per ID nach.
    `message` ist bereits fertig formuliert."""
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute(
                "SELECT [CreatedBy], [Titel] FROM [tblExperimentRequests] WHERE [ID]=?",
                [request_id],
            )
            row = cur.fetchone()
        if not row:
            return
        owner_id, titel = row[0], row[1]
        label = str(titel or "").strip() or f"#{request_id}"
        notify_owner(user, owner_id, request_id, f"Request '{label}': {message}")
    except Exception:
        pass


# ======================================================================
# Status changes (superusers)
# ======================================================================

def check_status_change(choices: List[Tuple[Any, str]], old_id: Any, new_id: Any) -> Tuple[str, str]:
    """Rule for a status change by a superuser -> (verdict, new label):
      "invalid"            empty status or "Experiment" (only set by assigning one)
      "same"               nothing to do
      "needs_reason"       moving to "Denied" needs a reason (shown to the requester)
      "needs_confirmation" moving an Approved/Experiment request back to "Request"
      "ok"
    """
    if new_id in (None, ""):
        return "invalid", ""
    new_label = status_label(choices, new_id).strip()
    if new_label.lower() == "experiment":
        return "invalid", new_label
    if new_id == old_id:
        return "same", new_label
    if new_label.lower() == "denied":
        return "needs_reason", new_label
    if old_id in (STATUS_APPROVED, STATUS_EXPERIMENT) and new_label.lower() == "request":
        return "needs_confirmation", new_label
    return "ok", new_label


def confirm_back_to_request_text(request_id: Any, old_label: str) -> str:
    return (f"Request #{request_id} is currently '{old_label}'. "
            "Really move it back to 'Request' (open)?")


def update_request_status(request_id: Any, new_status_id: Any, denial_reason: Optional[str] = None) -> None:
    """Writes RequestStatus (+ DenialReason where the column exists - a change
    away from "Denied" clears the old reason). Raises on DB errors."""
    with get_connection() as cn:
        cur = cn.cursor()
        has_denial_col = "denialreason" in _db_get_columns_map("tblExperimentRequests")
        if has_denial_col:
            cur.execute(
                "UPDATE [tblExperimentRequests] SET [RequestStatus]=?, [DenialReason]=? WHERE [ID]=?",
                [new_status_id, denial_reason, request_id],
            )
        else:
            cur.execute(
                "UPDATE [tblExperimentRequests] SET [RequestStatus]=? WHERE [ID]=?",
                [new_status_id, request_id],
            )
        try:
            cn.commit()
        except Exception:
            pass


def set_status(user: dict, request_id: Any, new_status_id: Any, reason: Optional[str] = None,
               *, confirmed: bool = False) -> Dict[str, Any]:
    """Status change as My Requests does it (web): superusers only
    (PermissionError otherwise). Returns {"kind", "message", "status_id"}:
      "changed"            written, owner notified
      "unchanged"          already that status
      "invalid"            empty status or "Experiment"
      "needs_reason"       Denied without a (non-blank) reason - nothing written
      "needs_confirmation" Approved/Experiment -> Request without confirmed=True
      "not_found"
    """
    if not is_superuser(user):
        raise PermissionError("Only superusers can change the status of a request.")
    rows = fetch_all("SELECT [RequestStatus], [CreatedBy], [Titel] FROM [tblExperimentRequests] WHERE [ID]=?",
                     [request_id])
    if not rows:
        return {"kind": "not_found", "message": "The selected request was not found.", "status_id": None}
    old_id, owner_id, titel = rows[0]["RequestStatus"], rows[0]["CreatedBy"], rows[0]["Titel"]
    choices = load_status_choices()
    verdict, new_label = check_status_change(choices, old_id, new_status_id)
    if verdict == "invalid":
        return {"kind": "invalid", "message": "This status cannot be set here.", "status_id": old_id}
    if verdict == "same":
        return {"kind": "unchanged", "message": "", "status_id": old_id}
    denial_reason = None
    if verdict == "needs_reason":
        if not (reason or "").strip():
            return {"kind": "needs_reason", "status_id": old_id,
                    "message": f"Reason for denying request #{request_id} (visible to the requester):"}
        denial_reason = reason.strip()
    elif verdict == "needs_confirmation" and not confirmed:
        return {"kind": "needs_confirmation", "status_id": old_id,
                "message": confirm_back_to_request_text(request_id, status_label(choices, old_id).strip())}
    update_request_status(request_id, new_status_id, denial_reason=denial_reason)
    notify_owner_status_changed(user, owner_id, request_id, str(titel or ""), new_label)
    return {"kind": "changed", "message": "", "status_id": new_status_id}


# ======================================================================
# Assign an existing experiment (superusers)
# ======================================================================

def experiment_id_fields() -> Tuple[str, str]:
    """(ExperimentID column, primary key column) of tblExperimente. Raises on DB errors."""
    cols = _columns_map("tblExperimente")
    exp_id_field = resolve_field(["ExperimentID", "Experiment ID", "ExperimentId"], cols) or "ExperimentID"
    pk_field = resolve_field(["ID"], cols) or "ID"
    return exp_id_field, pk_field


def unlinked_experiments(er_field: str, exp_id_field: str, pk_field: str) -> List[Tuple[Any, Any]]:
    """[(pk, ExperimentID)] of experiments without a request, newest ExperimentID first."""
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(
            f"SELECT [{pk_field}] AS PK, [{exp_id_field}] AS ExpID "
            f"FROM [tblExperimente] "
            f"WHERE [{er_field}] IS NULL "
            f"ORDER BY [{exp_id_field}] DESC",
        )
        return list(cur.fetchall())


def experiment_choice_label(pk: Any, exp_id_val: Any) -> str:
    return str(exp_id_val) if exp_id_val is not None else f"ID {pk}"


def link_experiment(request_id: Any, experiment_pk: Any, er_field: str, pk_field: str) -> None:
    """Links the experiment to the request and sets RequestStatus 4. Raises on DB errors."""
    try:
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute("START TRANSACTION")   # pool is autocommit=True - both updates or none (fixed 2026-11-13)
            cur.execute(
                f"UPDATE [tblExperimente] SET [{er_field}]=? WHERE [{pk_field}]=?",
                [request_id, experiment_pk],
            )
            cur.execute(
                "UPDATE [tblExperimentRequests] SET [RequestStatus]=4 WHERE [ID]=?",
                [request_id],
            )
            cn.commit()
    except Exception:
        try:
            cn.rollback()
        except Exception:
            pass
        raise


def assign_experiment(user: dict, request_id: Any, experiment_pk: Any) -> Dict[str, Any]:
    """Assign an experiment without request to `request_id` (web): superusers only
    (PermissionError). Status -> Experiment (4), owner notified.
    Returns {"kind": "linked"|"no_field"|"not_available", "message"}."""
    if not is_superuser(user):
        raise PermissionError("Only superusers can assign experiments.")
    er_field = resolve_experiment_request_field()
    if not er_field:
        return {"kind": "no_field", "message": "The field 'ExperimentRequestID' was not found in tblExperimente."}
    exp_id_field, pk_field = experiment_id_fields()
    available = {str(pk): exp for pk, exp in unlinked_experiments(er_field, exp_id_field, pk_field)}
    if str(experiment_pk) not in available:
        return {"kind": "not_available", "message": "This experiment is already linked to a request."}
    link_experiment(request_id, experiment_pk, er_field, pk_field)
    notify_owner_of_request(user, request_id, "status changed to Experiment")
    label = experiment_choice_label(experiment_pk, available[str(experiment_pk)])
    return {"kind": "linked", "message": f"Experiment {label} was linked to request #{request_id}."}


# ======================================================================
# Pending changes: review (superusers)
# ======================================================================

def accept_pending_change(user: dict, copy_id: Any, *, notify_requester: bool = True) -> Tuple[Any, Any]:
    """Accept a change copy: the original is archived as prior version and
    overwritten, the copy deleted (experiment_request_changes.accept_pending_change).
    Then (best-effort) the owners of experiments already made from the request are
    told, and - unless notify_requester=False - the requester.
    Superusers only (PermissionError). Returns (original_id, archived_version_id)."""
    if not is_superuser(user):
        raise PermissionError("Only superusers can accept change proposals.")
    original_id, archived_version_id = request_changes.accept_pending_change(copy_id)
    # Best-effort heads-up (2026-09-02, user request) to whoever already
    # created an Experiment from this request before it changed - they're
    # otherwise not part of this review loop at all and would only find
    # out by explicitly checking back. Never blocks/fails the actual
    # accept if it errors.
    try:
        from ui.notifications import notify_experiment_owners_of_request_change
        notify_experiment_owners_of_request_change(original_id, archived_version_id, user_id(user))
    except Exception:
        pass
    if notify_requester and original_id not in (None, ""):
        notify_owner_of_request(user, original_id, "your proposed change was accepted")
    return original_id, archived_version_id


def reject_pending_change(user: dict, copy_id: Any, original_id: Any = None, *,
                          notify_requester: bool = True) -> None:
    """Discard a change copy (original untouched). Superusers only. The requester
    of `original_id` is notified unless notify_requester=False."""
    if not is_superuser(user):
        raise PermissionError("Only superusers can reject change proposals.")
    request_changes.reject_pending_change(copy_id)
    if notify_requester and original_id not in (None, ""):
        notify_owner_of_request(user, original_id, "your proposed change was rejected")


# ======================================================================
# Side-by-side comparison (moved from ui/widgets/experiment_request_diff_dialog.py)
# ======================================================================

# Pure row metadata - never a real content difference worth showing.
COMPARE_META_FIELDS = set(EXCLUDE_FIELDS)


def _compare_project_label(project_id: Any) -> str:
    """Project label of the comparison (like project_label(), but empty number/
    name parts via `or ""`)."""
    if project_id in (None, ""):
        return ""
    for t in ("tblProject", "tblProjects"):
        if not _db_table_exists(t):
            continue
        try:
            cols = _db_get_columns_map(t)
            f_num = resolve_field(
                ["Project Number", "ProjectNumber", "Projekt Nummer", "ProjektNummer", "Number", "Nr"], cols)
            f_name = resolve_field(
                ["Project Name", "ProjectName", "Projekt Name", "ProjektName", "Name", "Titel", "Title"], cols)
            if not (f_num and f_name):
                continue
            rows = fetch_all(f"SELECT [{f_num}] AS PN, [{f_name}] AS PName FROM [{t}] WHERE [ID]=?", [project_id])
            if rows:
                pn = str(rows[0].get("PN") or "")
                pnm = str(rows[0].get("PName") or "")
                return (pn + " - " + pnm).strip(" -")
        except Exception:
            continue
    return str(project_id)


def compare_text(field_name: str, val: Any) -> str:
    """Text of one value in the comparison."""
    if val is None:
        return ""
    if field_name in DATE_FIELDS:
        if isinstance(val, (datetime.datetime, datetime.date)):
            return val.strftime("%d.%m.%Y")
        s = re.sub(r"(Z|[+-]\d{2}:\d{2})$", "", str(val).strip().replace("T", " ")).strip()
        s_date = s.split(" ")[0]
        if re.match(r"^\d{4}-\d{2}-\d{2}$", s_date):
            try:
                return datetime.datetime.strptime(s_date, "%Y-%m-%d").strftime("%d.%m.%Y")
            except Exception:
                return s
        return s
    if field_name.lower() == "projekt":
        return _compare_project_label(val)
    return str(val).strip()


def compare_requests(left_id: Any, right_id: Any) -> Dict[str, Any]:
    """Field-by-field comparison of two request rows (pending change review:
    left = original, right = change copy; version history: left = old version,
    right = live row). Returns {"title", "rows": [{"field", "left", "right",
    "changed"}], "any_changes"}; meta fields are skipped."""
    original = fetch_request(left_id) or {}
    proposed = fetch_request(right_id) or {}
    title = str(proposed.get("Titel") or original.get("Titel") or "").strip() or f"Request #{left_id}"
    field_names = [n for n in original.keys() if n not in COMPARE_META_FIELDS]
    for n in proposed.keys():
        if n not in COMPARE_META_FIELDS and n not in field_names:
            field_names.append(n)
    rows = []
    for fn in field_names:
        old_val = compare_text(fn, original.get(fn))
        new_val = compare_text(fn, proposed.get(fn))
        rows.append({"field": fn, "left": old_val, "right": new_val, "changed": old_val != new_val})
    return {"title": title, "rows": rows, "any_changes": any(r["changed"] for r in rows)}


# ======================================================================
# Read-only popup from series lists / Show Experiment / Report + version
# history + Experiment ID -> series (moved from the Qt screens, 2026-11-13,
# shared with the web app)
# ======================================================================

def request_id_for_experiment(experiment_pk: Any) -> Any:
    """Experiment Request linked to an experiment (tblExperimente.ID), None if
    none (from ShowExperimentScreen._refresh_experiment_request_link)."""
    if experiment_pk in (None, ""):
        return None
    f_req = resolve_experiment_request_field()
    if not f_req:
        return None
    try:
        rows = fetch_all(f"SELECT [{f_req}] AS ER FROM [tblExperimente] WHERE [ID]=?", [experiment_pk])
    except Exception:
        return None
    rid = rows[0].get("ER") if rows else None
    return None if rid in (None, "", 0, "0") else rid


def request_id_for_series(series_pk: Any) -> Any:
    """Experiment Request linked to the experiment of a trial series, only if
    the request row exists (Report ER icon, from ReportScreen._refresh_experiment_request_link)."""
    if series_pk in (None, ""):
        return None
    try:
        rows = fetch_all(
            """
            SELECT er.ID AS req_id
            FROM tblTrialSeries ts
            JOIN tblExperimente e ON e.ID = ts.ExperimentID
            JOIN tblExperimentRequests er ON er.ID = e.ExperimentRequestID
            WHERE ts.ID = ?
            LIMIT 1
            """,
            [series_pk],
        )
    except Exception:
        return None
    return rows[0].get("req_id") if rows else None


def is_linked_request(request_id: Any) -> bool:
    """True if an experiment links to this request."""
    f_req = resolve_experiment_request_field()
    if not f_req or request_id in (None, ""):
        return False
    try:
        return bool(fetch_all(f"SELECT 1 AS X FROM [tblExperimente] WHERE [{f_req}]=? LIMIT 1", [request_id]))
    except Exception:
        return False


def can_view(user: Optional[dict], row: Optional[Dict[str, Any]]) -> bool:
    """Who may see a request read-only: whoever may open it (can_open), plus
    everybody for a request linked to an experiment (and its archived versions) -
    the desktop shows those from All Experiments/Backlog/Show Experiment/Report
    to every user who sees the series."""
    if not row:
        return False
    if can_open(user, row):
        return True
    return is_linked_request(row.get("PriorVersionOfID") or row.get("ID"))


def popup_data(request_id: Any, prefix: str = "") -> Optional[Dict[str, Any]]:
    """Content of the read-only popup (_ExperimentRequestReadOnlyDialog): title,
    fields, images and whether a version history exists. None if not found."""
    from db import experiment_request_images as images

    data = fetch_request(request_id)
    if data is None:
        return None
    history_target = data.get("PriorVersionOfID") or request_id
    try:
        has_versions = request_changes.has_versions(history_target)
    except Exception:
        has_versions = False
    return {
        "id": data.get("ID", request_id),
        "title": popup_title(data, request_id, prefix)[0],
        "display": display_fields(get_table_columns(TABLE), data),
        "images": images.list_images(request_id),
        "history_target_id": history_target,
        "has_versions": has_versions,
    }


def version_history(request_id: Any) -> List[Dict[str, Any]]:
    """Entries of the version history dialog, newest first: the live row
    ("Current", version total+1) and every archived prior version (version
    total..1). Each {"id", "version", "current", "timestamp", "user"}."""
    versions = request_changes.list_versions(request_id)
    total = len(versions)
    out: List[Dict[str, Any]] = [{"id": request_id, "version": total + 1, "current": True,
                                  "timestamp": None, "user": ""}]
    for i, v in enumerate(versions):
        ts = v.get("Timestamp")
        out.append({"id": v.get("ID"), "version": total - i, "current": False,
                    "timestamp": ts.strftime("%Y-%m-%d %H:%M") if isinstance(ts, datetime.datetime) else str(ts or ""),
                    "user": str(v.get("CreatedByUser") or "").strip() or "?"})
    return out


def series_for_experiment_id(exp_id_txt: Any) -> Tuple[Optional[int], List[Dict[str, Any]]]:
    """(experiment PK, [{"id", "name", "trials"}]) for an ExperimentID text
    (My Requests: click on Experiment ID -> series picker -> Show Experiment).
    (None, []) if the experiment does not exist."""
    cols = _db_get_columns_map("tblexperimente")
    f_id = None
    for cand in ("experimentid", "experiment id", "experimentid_txt"):
        if cand in cols:
            f_id = cols[cand]
            break
    if not f_id or exp_id_txt in (None, ""):
        return None, []
    exp_rows = fetch_all(f"SELECT ID FROM tblExperimente WHERE `{f_id}` = %s", [str(exp_id_txt)])
    if not exp_rows:
        return None, []
    exp_pk = int(exp_rows[0]["ID"])
    series_rows = fetch_all(
        "SELECT ID, SeriesName, "
        "(SELECT COUNT(*) FROM tblTrial WHERE TrialSeriesID = tblTrialSeries.ID) AS TrialCount "
        "FROM tblTrialSeries WHERE ExperimentID = %s ORDER BY ID",
        [exp_pk],
    )
    return exp_pk, [{"id": int(r["ID"]), "name": str(r.get("SeriesName") or f"Series {r['ID']}"),
                     "trials": int(r.get("TrialCount") or 0)} for r in series_rows]
