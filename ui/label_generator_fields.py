# ui/label_generator_fields.py
"""DB-Feld-Registry fuer den Label Generator (ui/screen_label_generator.py).

Bindet Label-Textelemente an Experiment/Trial-Daten. Sucheinstieg ist die
TrialSeriesID (z.B. 341, die interne PK von tbltrialseries) - dieselbe ID,
mit der auch der bestehende Trial-Label-Druck in screen_show_experiment.py
arbeitet. Neues STATISCHES Feld hinzufuegen = ein FIELD_REGISTRY-Eintrag +
eine Zeile in build_fields() - kein UI-Umbau noetig.

Zusaetzlich: DYNAMISCHE "Machine Data"-Felder (machine_field_registry() /
machine_field_values()) - dieselben Felder, die auch der "Machine Data"-Tab
in ui/machine_tab.py zeigt (Housing/Jet/Jet Plate Number/Air Pressure + pro
Maschine konfigurierte Custom-Felder aus tblMachineFields), bewusst nur die
TRIAL-WEITEN davon (StorageTable=tbltrial). Die Ply-weiten Felder (Yarn Use,
Spool, Custom-Felder mit StorageTable=tbltrialsettings) sind bewusst
ausgeklammert - ein Trial kann mehrere Plies mit unterschiedlichen Werten
haben, das passt nicht ins "ein Trial -> ein flacher Wertesatz"-Modell des
Label Generators.

canon_rule() gibt es nur in ui/screen_show_experiment.py - wird dort lazy
(innerhalb der Funktion) importiert, analog zum etablierten Muster in
machine_tab.py/screen_show_experiment_pdf_import.py (siehe CLAUDE.md), NICHT
neu implementiert. norm()/resolve_field() kommen aus dem bereits
konsolidierten ui/text_normalize.py.
"""
from typing import Dict, List, Optional

from db.connection import fetch_all, get_columns_map, table_exists
from ui.text_normalize import norm, resolve_field

# field_key -> Anzeigename im Source-Dropdown
FIELD_REGISTRY: Dict[str, str] = {
    "trial_nr":      "Trial Number",
    "experiment_id": "Experiment ID",
    "series_name":   "Series Name",
    "header":        "Experiment.Series (e.g. 1234.IN)",
}

# Die 4 "Machine Data"-Zeilen, die unabhaengig von der Maschine immer
# existieren (siehe titles_fixed in ui/machine_tab.py::build_machine_tab_impl).
_MACHINE_FIXED_FIELDS: Dict[str, str] = {
    "machine_housing":       "Housing",
    "machine_jet":           "Jet",
    "machine_jet_plate":     "Jet Plate Number",
    "machine_air_pressure":  "Air Pressure (bar)",
}

# Feldnamen, die im "Machine Data"-Tab entweder schon als Fixzeile existieren
# oder Ply-weit sind (Yarn Use/Spool) - beim Scannen von tblMachineFields
# uebersprungen (siehe reserved_titles in ui/machine_tab.py).
_RESERVED_MACHINE_FIELD_NAMES = [
    "Housing", "Jet", "Jet Name", "JetPlate", "Jet Plate Number",
    "Air Pressure (bar)", "AirPressure", "Air Pressure",
    "Yarn Use", "YarnUse", "YarnUseID", "Spool",
]

_JET_TABLE_CANDIDATES = ["tblDTYJets", "tblJets", "tblJet", "tblDuesen", "tblDuese", "Jets"]
_JET_NAME_CANDIDATES = [
    "Name", "JetName", "Bezeichnung", "Title", "Jet", "Nozzle",
    "Code", "Typ", "Type", "Modell", "Model", "Series", "Designation", "Description",
]
_GENERIC_NAME_CANDIDATES = [
    "Name", "DiscName", "Bezeichnung", "Caption", "HousingName",
    "MaterialName", "YarnName", "Description", "Label",
]


def build_fields(exp_id: str, series_name: str, trial_nr) -> Dict[str, str]:
    series_name = str(series_name or "")
    return {
        "trial_nr": str(trial_nr or ""),
        "experiment_id": str(exp_id or ""),
        "series_name": series_name,
        "header": f"{exp_id}.{series_name[:2]}" if exp_id else "",
    }


def series_header(series_id: int) -> Optional[Dict[str, str]]:
    """ExperimentID + SeriesName fuer eine TrialSeriesID. None wenn die
    Series nicht existiert. Wirft DB-Fehler durch (kein stilles Verschlucken -
    der Aufrufer soll dem Nutzer den tatsaechlichen Fehler zeigen koennen)."""
    if not table_exists("tbltrialseries"):
        return None
    rows = fetch_all(
        "SELECT e.[ExperimentID] AS ExpId, s.[SeriesName] AS SeriesName "
        "FROM tbltrialseries s "
        "LEFT JOIN tblexperimente e ON e.[ID] = s.[ExperimentID] "
        "WHERE s.[ID] = ?", [series_id])
    if not rows:
        return None
    return {"experiment_id": rows[0].get("ExpId"), "series_name": rows[0].get("SeriesName")}


def list_trials_for_series(series_id: int) -> List[int]:
    """Alle Versuchsnummern einer TrialSeriesID, aufsteigend sortiert.

    Wirft DB-Fehler durch, damit der Aufrufer echte Fehler von "keine Trials
    gefunden" unterscheiden kann."""
    if not table_exists("tbltrial"):
        return []
    rows = fetch_all(
        "SELECT [Versuchsnummer] AS TrialNr FROM tbltrial "
        "WHERE [TrialSeriesID] = ? ORDER BY [Versuchsnummer]", [series_id])
    return [int(r["TrialNr"]) for r in rows]


def trial_ids_by_number(series_id: int) -> Dict[int, int]:
    """Versuchsnummer -> TrialID fuer eine TrialSeriesID (fuer den Zugriff auf
    die dynamischen Machine-Data-Feldwerte, die eine echte TrialID brauchen -
    list_trials_for_series() liefert bewusst nur die Versuchsnummern, damit
    der bestehende Range-Picker im Label Generator unveraendert bleibt)."""
    if not table_exists("tbltrial"):
        return {}
    rows = fetch_all(
        "SELECT [ID] AS TrialID, [Versuchsnummer] AS TrialNr FROM tbltrial "
        "WHERE [TrialSeriesID] = ? ORDER BY [Versuchsnummer]", [series_id])
    return {int(r["TrialNr"]): int(r["TrialID"]) for r in rows}


def machine_id_for_series(series_id: int) -> Optional[int]:
    """MachineID einer TrialSeries, oder None (z.B. wenn nicht gesetzt)."""
    if not table_exists("tbltrialseries"):
        return None
    rows = fetch_all(
        "SELECT [MachineID] FROM tbltrialseries WHERE [ID] = ?", [series_id])
    if rows and rows[0].get("MachineID") is not None:
        try:
            return int(rows[0]["MachineID"])
        except Exception:
            return None
    return None


def _lookup_name(table: str, name_cands: Optional[List[str]], id_value) -> str:
    """Loest eine ID gegen table.[ID] -> table.[<erster passender Namensspalte>] auf."""
    if id_value is None or not table_exists(table):
        return ""
    cmap = get_columns_map(table)
    col_id = resolve_field(["ID"], cmap) or "ID"
    col_name = resolve_field(name_cands or _GENERIC_NAME_CANDIDATES, cmap)
    if not col_name:
        return ""
    try:
        rows = fetch_all(f"SELECT [{col_name}] AS NM FROM {table} WHERE [{col_id}] = ?", [id_value])
    except Exception:
        return ""
    return str(rows[0].get("NM") or "") if rows else ""


def _lookup_jet_name(jet_id) -> str:
    """Wie _find_jet_table_and_text_col() in ui/machine_tab.py - probiert
    dieselben Kandidaten-Tabellen durch, bis eine einen Namen liefert."""
    if jet_id is None:
        return ""
    for table in _JET_TABLE_CANDIDATES:
        name = _lookup_name(table, _JET_NAME_CANDIDATES, jet_id)
        if name:
            return name
    return ""


def _fetch_machine_field_defs(machine_id: int) -> List[Dict]:
    if not table_exists("tblmachinefields"):
        return []
    try:
        return fetch_all(
            """SELECT FieldName, FieldFunction, OriginalName,
                      COALESCE(StorageTable, 'tbltrial') AS StorageTable,
                      COALESCE(RDSetting, 0) AS RDSetting
               FROM tblMachineFields WHERE MachineID = ?
               ORDER BY FieldNumber, FieldName""",
            [machine_id])
    except Exception:
        return []


def machine_field_registry(machine_id: Optional[int]) -> Dict[str, str]:
    """field_key -> Anzeigename fuer alle trial-weiten "Machine Data"-Felder
    dieser Maschine: die 4 immer vorhandenen Fixfelder plus alle pro Maschine
    konfigurierten Custom-Felder mit StorageTable=tbltrial, RDSetting=0 (kein
    R&D-Feld), FieldFunction != hidden - dieselbe Filterung wie der
    "Machine Data"-Tab in ui/machine_tab.py fuer die tblTrial-Zeilen."""
    from ui.screen_show_experiment import canon_rule

    registry: Dict[str, str] = dict(_MACHINE_FIXED_FIELDS)
    if machine_id is None:
        return registry

    reserved_norm = {norm(x) for x in _RESERVED_MACHINE_FIELD_NAMES}
    used_keys = set(registry.keys())
    for f in _fetch_machine_field_defs(machine_id):
        if int(f.get("RDSetting") or 0) != 0:
            continue
        if str(f.get("StorageTable") or "tbltrial").strip().lower() != "tbltrial":
            continue
        ff = canon_rule((f.get("FieldFunction") or "").strip() or None)
        if ff == "hidden":
            continue
        name = str(f.get("FieldName") or "").strip()
        if not name or norm(name) in reserved_norm:
            continue
        base_key = "machine_" + (norm(name) or "field")
        key = base_key
        i = 2
        while key in used_keys:
            key = f"{base_key}_{i}"
            i += 1
        used_keys.add(key)
        registry[key] = name
    return registry


def machine_field_values(trial_id: int, machine_id: Optional[int]) -> Dict[str, str]:
    """Werte fuer machine_field_registry(machine_id)-Keys, fuer genau eine
    TrialID (trial-weite Felder, ein Wert pro Feld)."""
    from ui.screen_show_experiment import canon_rule

    values: Dict[str, str] = {}
    if not table_exists("tbltrial"):
        return values
    trial_cols = get_columns_map("tbltrial")
    rows = fetch_all("SELECT * FROM tbltrial WHERE [ID] = ? LIMIT 1", [trial_id])
    if not rows:
        return values
    trow = rows[0]

    housing_id_col = resolve_field(["HousingID"], trial_cols)
    if housing_id_col and trow.get(housing_id_col) is not None:
        values["machine_housing"] = _lookup_name(
            "tblhousing", ["HousingName", "Name", "Bezeichnung"], trow.get(housing_id_col))

    jet_id_col = resolve_field(["JetID"], trial_cols)
    if jet_id_col and trow.get(jet_id_col) is not None:
        values["machine_jet"] = _lookup_jet_name(trow.get(jet_id_col))

    plate_col = resolve_field(
        ["Jet Plate", "JetPlate", "Jet_Plate", "JetPlateNumber", "Jet Plate Number"], trial_cols)
    if plate_col:
        values["machine_jet_plate"] = str(trow.get(plate_col) or "")

    air_col = resolve_field(
        ["Air Pressure (bar)", "AirPressure(bar)", "AirPressure",
         "Air_Pressure_bar", "Air Pressure"], trial_cols)
    if air_col:
        values["machine_air_pressure"] = str(trow.get(air_col) or "")

    if machine_id is not None:
        registry = machine_field_registry(machine_id)
        key_by_name = {v: k for k, v in registry.items() if k.startswith("machine_")}
        for f in _fetch_machine_field_defs(machine_id):
            if int(f.get("RDSetting") or 0) != 0:
                continue
            if str(f.get("StorageTable") or "tbltrial").strip().lower() != "tbltrial":
                continue
            ff = canon_rule((f.get("FieldFunction") or "").strip() or None)
            if ff == "hidden":
                continue
            name = str(f.get("FieldName") or "").strip()
            key = key_by_name.get(name)
            if not key or key in values:
                continue
            orig = str(f.get("OriginalName") or "").strip()
            col = None
            if orig:
                col = trial_cols.get(orig.lower()) or resolve_field([orig], trial_cols)
            if not col:
                col = trial_cols.get(name.lower()) or resolve_field([name], trial_cols)
            if not col:
                continue
            raw = trow.get(col)
            if raw is None:
                values[key] = ""
            elif ff and ff.lower().startswith("dropdown:"):
                lookup_table = ff[len("dropdown:"):].strip()
                values[key] = _lookup_name(lookup_table, _GENERIC_NAME_CANDIDATES, raw)
            else:
                values[key] = str(raw)
    return values


def build_machine_fields(trial_id: Optional[int], machine_id: Optional[int]) -> Dict[str, str]:
    """Wie build_fields(), aber fuer die dynamischen Machine-Data-Feldwerte -
    getrennt gehalten, damit build_fields() ohne TrialID weiterhin
    funktioniert. Ohne TrialID (z.B. Serie ohne Trials) leeres Dict."""
    if trial_id is None:
        return {}
    return machine_field_values(trial_id, machine_id)
