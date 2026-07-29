"""machine_tab.py - Standard-Maschinen-Tab (Machine Data) fuer ShowExperimentScreen.

Enthaelt build_machine_tab_impl(self), ausgelagert aus
ui/screen_show_experiment.py (reiner Code-Move, keine Verhaltensaenderung) -
analog zu screen_show_experiment_pdf_import.py / dty_yarnscope_tab.py /
advisor_tab.py. Baut die generische Pivot-Tabelle "Machine Data" (Housing,
Jet, Jet Plate, Air Pressure, dynamische Maschinenfelder aus tblMachineFields)
fuer die aktuell gewaehlte Machine der TrialSeries auf.

Alle DB-/Normalisierungs-Helfer sowie die Modell-/Delegate-Klassen werden
bewusst lazy aus ui.screen_show_experiment importiert (nicht neu
implementiert), damit exakt dieselben Wrapper/Klassen wie vorher verwendet
werden.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QCheckBox, QTableView, QMessageBox, QDialog

import app_meta


def build_machine_tab_impl(self) -> None:
    from ui.screen_show_experiment import (
        table_exists, fetch_all, get_columns_map, get_columns_info,
        resolve_field, norm, canon_rule,
        PivotEditModel, MachinePivotModel, CellBinding, GroupCellBinding,
        HousingComboDelegate, JetComboDelegate, LookupComboDelegate,
        _HousingImageTooltipFilter,
    )

    # Aktuellen Modus für _on_view_mode_changed merken
    if self._rb_groups.isChecked():
        self._last_view_mode = "groups"
    elif self._rb_compact.isChecked():
        self._last_view_mode = "compact"
    else:
        self._last_view_mode = "single"

    # Radio-Signals einmalig verbinden
    if not getattr(self, "_rb_signals_connected", False):
        self._rb_single.toggled.connect(self._on_view_mode_changed)
        self._rb_groups.toggled.connect(self._on_view_mode_changed)
        self._rb_compact.toggled.connect(self._on_view_mode_changed)
        self._rb_signals_connected = True
    cache = getattr(self, "_machine_cache", None) or {}
    if not cache:
        self._init_machine_cache()
        cache = getattr(self, "_machine_cache", None) or {}
    machine_id = cache.get("machine_id")
    use_yarn_use_grouping = getattr(self._rb_groups, "isChecked", lambda: False)()

    if not table_exists("tblMachineFields"):
        self.machine_info.setText(
            "Mapping-Tabelle 'tblMachineFields' nicht gefunden.")
        self.tbl_machine.setModel(PivotEditModel([], self._trial_labels))
        return

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
            self.machine_info.setText(f"Fehler beim Laden von tblMachineFields: {e}")
            self.tbl_machine.setModel(PivotEditModel([], self._trial_labels))
            return

    # Felder aufteilen: RDSetting=0 -> Machine Data, RDSetting=1 -> R&D Machine Data
    fields_normal = [f for f in fields if int(f.get("RDSetting") or 0) == 0]
    fields_rd = [f for f in fields if int(f.get("RDSetting") or 0) == 1]

    # Trial-Spalten (für exakte Groß/Kleinschreibung)
    trial_cols = cache.get("trial_cols_map") or get_columns_map("tblTrial")

    # Fixe Titel
    FIX_HOUSING = "Housing"
    FIX_JET = "Jet"
    FIX_PLATE = "Jet Plate Number"
    FIX_AIR = "Air Pressure (bar)"
    titles_fixed = [FIX_HOUSING, FIX_JET, FIX_PLATE, FIX_AIR]

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

    # Modell + Validatoren
    FIX_PLIES = "Plies"
    FIX_YARN_USE = "Yarn Use"
    FIX_SPOOL = "Spool"
    compact_mode = self._rb_compact.isChecked()
    if use_yarn_use_grouping:
        titles_fixed = [FIX_HOUSING, FIX_JET, FIX_PLATE, FIX_AIR, FIX_PLIES]
    elif compact_mode:
        titles_fixed = [FIX_HOUSING, FIX_JET, FIX_PLATE, FIX_AIR, FIX_PLIES]
    else:
        titles_fixed = [FIX_HOUSING, FIX_JET, FIX_PLATE, FIX_AIR, FIX_YARN_USE, FIX_SPOOL]
    # Von der Fill-Range-Logik (Kontextmenue) genutzt, um zu erkennen ob ein
    # Feld zu tblTrialSettings (Ply-spezifisch) gehoert. Ersetzt eine frueher
    # hartcodierte Konstante (=5), die durch die neue Spool-Zeile im
    # Single-Plies-Modus (jetzt 6 Fixzeilen) sonst falsch waere.
    self._machine_titles_fixed_count = len(titles_fixed)
    row_titles = titles_fixed + [f["Title"] for f in field_map]
    # CustomGroup immer am Ende anhängen (Sichtbarkeit via hideRow gesteuert)
    row_titles = row_titles + ["Custom Group"]
    readonly_rows = set()
    if use_yarn_use_grouping or compact_mode:
        readonly_rows.add(titles_fixed.index(FIX_PLIES))  # Plies-Zeile immer read-only

    row_validators: List[Optional[str]] = [None] * len(row_titles)
    row_validators[0] = None  # Housing
    row_validators[1] = None  # Jet
    row_validators[2] = reserved_validators.get(FIX_PLATE)
    row_validators[3] = reserved_validators.get(FIX_AIR)
    for i, ff in enumerate(field_validators, start=len(titles_fixed)):
        row_validators[i] = ff
    # CustomGroup: zuletzt, kein Validator
    self._custom_group_row_idx = len(row_titles) - 1  # Modell-Zeilenindex (0-basiert, ohne Header-Zeilen)

    # model_machine wird weiter unten (nach col_specs-Aufbau) instanziert,
    # damit expanded_col_titles (Ply-Unterspalten) bekannt sind.

    # dropdown_rows aufbauen: {row_index_0based → {id → name}}
    # row_index = Position in row_titles (titles_fixed hat 5 Einträge: 0-4)
    dropdown_rows: Dict[int, Dict[Any, str]] = {}

    # YarnUse Dropdown (Single Plies Modus, Zeile 4) — aus Cache
    if not use_yarn_use_grouping and not compact_mode:
        yarn_use_row_idx = titles_fixed.index(FIX_YARN_USE)
        yu_map: Dict[Any, str] = {"": "—", None: "—", 0: "—", "0": "—"}
        for uid, uname in cache.get("yarn_use_map", {}).items():
            yu_map[uid] = uname
            yu_map[str(uid)] = uname  # String-Key für _id_display
        dropdown_rows[yarn_use_row_idx] = yu_map

        # Spool Dropdown (Zeile 5) - alle am Lager befindlichen Spulen der
        # Garne, die in dieser Series tatsaechlich als Material vorkommen.
        # Series-weite Liste statt strikt pro Zelle gefiltert (eine Zeile
        # gilt fuer die ganze Tabelle) - dafuer profitiert man von der
        # bestehenden Fill-Range-Mechanik fuer Dropdown-Zeilen (z.B. um
        # dieselbe Spule auf viele Trials gleichzeitig zu setzen).
        spool_row_idx = titles_fixed.index(FIX_SPOOL)
        sp_map: Dict[Any, str] = {"": "—", None: "—", 0: "—", "0": "—"}
        # Volle Infos (Garn/Batch/Gewicht/Ort) landen NICHT in sp_map (das
        # waere die Zellen-/Dropdown-Anzeige und macht die Spalte zu breit),
        # sondern separat in self._spool_tooltip_map fuer den Tooltip.
        self._spool_tooltip_map: Dict[int, str] = {}
        if table_exists("tblYarnSpool"):
            try:
                series_yarn_ids = sorted({
                    int(r["YarnID"]) for r in fetch_all(
                        "SELECT DISTINCT ts.YarnID FROM tblTrialSettings ts "
                        "JOIN tblTrial t ON t.ID = ts.TrialID "
                        "WHERE t.TrialSeriesID = ? AND ts.YarnID IS NOT NULL",
                        [self._series_pk])
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
                    self._spool_tooltip_map[int(sr2["ID"])] = full_label
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

    if not self._trial_ids:
        self.model_machine = MachinePivotModel(
            jets_map=self._jets_map,
            row_titles=row_titles,
            col_titles=self._trial_labels,
            read_only_rows=readonly_rows,
            row_validators=row_validators,
            jet_row_index=1,
            housing_map=self._housing_map,
            housing_row_index=0,
            jets_tooltip_map=self._jets_tooltip_map,
            housing_image_map=getattr(self, "_housing_image_map", {}),
            dropdown_rows=dropdown_rows,
        )
        self._register_save_model("model_machine")
        self.tbl_machine.setModel(self.model_machine)
        # R&D Tab ebenfalls ausblenden
        if self.tab_rd_machine is not None:
            idx = self.tabs.indexOf(self.tab_rd_machine)
            if idx != -1:
                self.tabs.removeTab(idx)
        return

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
            WHERE T.ID IN ({",".join(["?"] * len(self._trial_ids))})
            ORDER BY T.Versuchsnummer
            """,
            self._trial_ids,
        )
    else:
        trial_rows = fetch_all(
            f"""
            SELECT *
            FROM tblTrial
            WHERE ID IN ({",".join(["?"] * len(self._trial_ids))})
            ORDER BY Versuchsnummer
            """,
            self._trial_ids,
        )
        trial_cols_map = cache.get("trial_cols_map") or get_columns_map("tblTrial")
        jet_text_field = resolve_field(
            ["Jet", "Jet Name", "Nozzle", "Nozzle"], trial_cols_map)
        for row in trial_rows:
            row["JetName"] = row.get(
                jet_text_field) if jet_text_field else None

    # Fixe Felder – Binding über OriginalName, wenn vorhanden
    trial_cols_map = cache.get("trial_cols_map") or get_columns_map("tblTrial")

    # ── col_specs immer aus tblTrialSettings aufbauen ─────────────────
    # (auch wenn keine Settings-Felder in field_map sind – für Konsistenz)
    col_specs: List[Dict] = []  # {"trial": ..., "sr": ..., "ply": str, "trial_id": int}
    settings_cols_map: Dict[str, str] = cache.get("settings_cols_map") or {}

    if table_exists("tblTrialSettings"):
        if not settings_cols_map:
            settings_cols_map = get_columns_map("tblTrialSettings")

        # Settings-Zeilen laden (muss immer frisch sein)
        s_rows = fetch_all(
            f"""
            SELECT * FROM tblTrialSettings
            WHERE TrialID IN ({",".join(["?"] * len(self._trial_ids))})
            ORDER BY TrialID, ID
            """,
            self._trial_ids,
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
        _ymap: Dict[int, str] = cache.get("yarn_map") or {}
        if not _ymap and table_exists("tblYarn"):
            for _yr in fetch_all("SELECT ID, Name FROM tblYarn"):
                try:
                    _ymap[int(_yr["ID"])] = str(_yr["Name"] or "")
                except Exception:
                    pass

        trial_row_by_id = {int(t["ID"]): t for t in trial_rows}
        for trial in self._trials:
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
                        "trial_id": tid,
                        "vno": int(trial["Versuchsnummer"]),
                    })
    else:
        trial_row_by_id = {int(t["ID"]): t for t in trial_rows}
        for trial in self._trials:
            col_specs.append({
                "trial": trial_row_by_id.get(int(trial["ID"]), {}),
                "sr": None,
                "ply": "",
                "trial_id": int(trial["ID"]),
                "vno": int(trial["Versuchsnummer"]),
            })

    # ── YarnUse-Gruppierung für MachineID = 4 ─────────────────────────
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
        # Reihenfolge der Gruppen: wie sie in yarn_use_map vorkommen + None zuletzt
        from collections import OrderedDict
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
                    "trial_id": tid,
                    "vno": members[0]["vno"],
                    "yarn_use_id": uid,
                    "yarn_use_name": use_name,
                    "is_group": True,
                })

        col_specs = group_col_specs

    # ── header_rows für Modell aufbauen ───────────────────────────────
    # Zeile 0: Trial-Gruppen  ("", "V1","V1","V2","V2",...)
    # Zeile 1: Ply-Labels     ("", "Ply 1","Ply 2","Ply 1","Ply 2",...)
    # Spalte 0 in beiden Zeilen = leere Titelspalte
    compact_mode = self._rb_compact.isChecked()

    # Pro Trial: alle col_specs sammeln für Kompakt-Tooltip
    trial_cs_for_hdr: Dict[int, List[Dict]] = {}
    for cs in col_specs:
        trial_cs_for_hdr.setdefault(cs["trial_id"], []).append(cs)

    trial_hdr_vals = [""]
    ply_hdr_vals = [""]
    ply_tooltip_vals = [""]
    for cs in col_specs:
        trial_hdr_vals.append(f"V{cs['vno']}")
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

    hdr_rows = [
        {"values": trial_hdr_vals, "bg": None, "fg": None},
        {"values": ply_hdr_vals, "bg": None, "fg": None, "tooltips": ply_tooltip_vals},
    ]
    # Zeile 0 = V-Nummern (gespannt), Zeile 1 = Ply-Labels (einzeln) – nur fett, kein Sonderfarbe

    # Spalten-Titel leer – Ply-Labels stehen bereits in header_rows[1]
    expanded_col_titles = ["" for _ in col_specs]

    # ── Modell instanzieren ───────────────────────────────────────────
    self.model_machine = MachinePivotModel(
        jets_map=self._jets_map,
        row_titles=row_titles,
        col_titles=expanded_col_titles,
        read_only_rows=readonly_rows,
        row_validators=row_validators,
        jet_row_index=1,
        header_rows=hdr_rows,
        housing_map=self._housing_map,
        housing_row_index=0,
        jets_tooltip_map=self._jets_tooltip_map,
        housing_image_map=getattr(self, "_housing_image_map", {}),
        dropdown_rows=dropdown_rows,
    )
    self._register_save_model("model_machine")
    self._machine_col_specs = col_specs  # for multi-ply feature tracking

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
        self.model_machine.set_cell(
            0, c_idx, housing_id,
            CellBinding("tblTrial", "ID", trow.get("ID"), "HousingID") if (
                        housing_id_col and trow.get("ID")) else None,
        )

    # 1: Jet (tblTrial – trial-weit)
    for c_idx, cs in enumerate(col_specs):
        trow = cs["trial"]
        jet_id = trow.get("JetID")
        self.model_machine.set_cell(
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
        self.model_machine.set_cell(
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
        self.model_machine.set_cell(
            3, c_idx,
            trow.get(ap_key) if ap_key else None,
            CellBinding("tblTrial", "ID", trow.get("ID"), ap_field) if (ap_field and trow.get("ID")) else None,
        )

    # Plies-Zeile (Groups-Modus oder Kompakt-Modus)
    if use_yarn_use_grouping:
        plies_row_idx = titles_fixed.index(FIX_PLIES)
        for c_idx, cs in enumerate(col_specs):
            self.model_machine.set_cell(
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
                    self.model_machine._cell_tooltips[(plies_row_idx, c_idx)] = "\n".join(tooltip_lines)

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
                sr = other_cs.get("sr")
                ply_str = (other_cs.get("ply") or "").strip()
                import re as _re
                m = _re.search(r"\d+", ply_str)
                if m:
                    ply_nums.append(m.group())
            short = ", ".join(ply_nums) if ply_nums else "—"
            self.model_machine.set_cell(plies_row_idx, c_idx, short, None)
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
                self.model_machine._cell_tooltips[(plies_row_idx, c_idx)] = "\n".join(tooltip_lines)

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
            self.model_machine.set_cell(
                yarn_use_row_idx, c_idx, yuid,
                CellBinding("tblTrialSettings", "ID", sr["ID"], "YarnUseID") if sr else None,
            )

        # Spool-Zeile: physische Duese-Zuordnung pro Ply/Trial
        spool_row_idx = titles_fixed.index(FIX_SPOOL)
        spool_tooltips = getattr(self, "_spool_tooltip_map", {})
        for c_idx, cs in enumerate(col_specs):
            sr = cs.get("sr")
            spool_id = None
            if sr:
                try:
                    spool_id = int(sr.get("SpoolID") or 0) or None
                except Exception:
                    spool_id = None
            self.model_machine.set_cell(
                spool_row_idx, c_idx, spool_id,
                CellBinding("tblTrialSettings", "ID", sr["ID"], "SpoolID") if sr else None,
            )
            if spool_id is not None and spool_id in spool_tooltips:
                self.model_machine._cell_tooltips[(spool_row_idx, c_idx)] = spool_tooltips[spool_id]

    # weitere Maschinenfelder
    start_row = len(titles_fixed)
    for offset, fdef in enumerate(field_map):
        r_idx = start_row + offset
        storage = fdef.get("StorageTable", "tbltrial")
        colname = fdef["ColName"]

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
                    self.model_machine.set_cell(r_idx, c_idx, val, binding)
                    if inconsistent:
                        self.model_machine._cell_alerts[(r_idx, c_idx)] = "orange"
                else:
                    val = sr.get(real_col) if sr else None
                    binding = CellBinding(
                        "tblTrialSettings", "ID", sr["ID"], real_col
                    ) if sr else None
                    self.model_machine.set_cell(r_idx, c_idx, val, binding)
        else:
            real_col = trial_cols_map.get(str(colname).lower()) or colname
            for c_idx, cs in enumerate(col_specs):
                trow = cs["trial"]
                val = trow.get(real_col)
                self.model_machine.set_cell(
                    r_idx, c_idx, val,
                    CellBinding("tblTrial", "ID", trow.get("ID"), real_col) if trow.get("ID") else None,
                )

    # CustomGroup-Zeile befüllen (direkt aus tblTrial.CustomGroup)
    _cg_col = trial_cols_map.get('customgroup') or trial_cols_map.get('custom_group') or 'CustomGroup'
    for c_idx, cs in enumerate(col_specs):
        trow = cs['trial']
        val = trow.get(_cg_col)
        self.model_machine.set_cell(
            self._custom_group_row_idx, c_idx, val,
            CellBinding('tblTrial', 'ID', trow.get('ID'), _cg_col) if trow.get('ID') else None,
        )

    self.tbl_machine.setModel(self.model_machine)
    self.tbl_machine.resizeColumnsToContents(fixed_data_column_width=90)

    # Qt-Column-Header ausblenden – Ply/V-Labels stehen bereits in den Modell-Header-Zeilen
    self.tbl_machine.left.horizontalHeader().setVisible(False)
    self.tbl_machine.right.horizontalHeader().setVisible(False)

    # CustomGroup-Zeile: n_hdr Header-Zeilen + Modell-Zeilenindex
    _cg_view_row = getattr(self.model_machine, '_n_hdr', 2) + self._custom_group_row_idx
    self.tbl_machine.left.setRowHidden(_cg_view_row, not self._custom_group_visible)
    self.tbl_machine.right.setRowHidden(_cg_view_row, not self._custom_group_visible)

    # ── setSpan für trial-weite Spalten ───────────────────────────────
    # col_specs enthält N Einträge pro Trial (eine pro Ply).
    # Für tblTrial-Felder und Header-Zeile 0 (V-Nummer) soll jede
    # Trial-Gruppe über alle ihre Ply-Spalten gespannt werden.
    #
    # Gruppen berechnen: [(model_col_start, span), ...]
    # model_col = 1-basiert (Spalte 0 = Zeilentitel)
    trial_groups: List[Tuple[int, int]] = []  # (first_model_col, span)
    _last_tid2 = None
    _grp_start = 0
    _grp_count = 0
    for ci, cs in enumerate(col_specs):
        tid2 = cs["trial_id"]
        if tid2 != _last_tid2:
            if _grp_count > 0:
                trial_groups.append((_grp_start, _grp_count))
            _grp_start = ci + 1  # +1 weil Modell-Spalte 0 = Titel
            _grp_count = 1
            _last_tid2 = tid2
        else:
            _grp_count += 1
    if _grp_count > 0:
        trial_groups.append((_grp_start, _grp_count))

    # Zeilen die trial-weit gespannt werden sollen:
    # - Modell-Zeile 0 = Header V-Nummer (trial_hdr_vals)
    # - Modell-Zeile 2+ = alle tblTrial-Felder (StorageTable != tbltrialsettings)
    n_hdr = self.model_machine._n_hdr  # = 2
    trial_wide_model_rows: List[int] = [0]  # Header-Zeile "V1, V2..."
    # Fixed rows: Housing=n_hdr+0, Jet=n_hdr+1, Plate=n_hdr+2, AirPressure=n_hdr+3
    # In Groups-Modus: Plies=n_hdr+4 auch trial-weit
    # In Single Modus: YarnUse=n_hdr+4 ist ply-spezifisch → nicht spanen
    trial_wide_model_rows += [n_hdr + 0, n_hdr + 1, n_hdr + 2, n_hdr + 3]
    # Plies-Zeile (n_hdr+4) bewusst NICHT trial-weit — pro Gruppe eigener Wert
    # Dynamic field rows
    for offset, fdef in enumerate(field_map):
        if fdef.get("StorageTable", "tbltrial") != "tbltrialsettings":
            trial_wide_model_rows.append(n_hdr + len(titles_fixed) + offset)
    # CustomGroup ist tblTrial-Feld → trial-weit spannen
    trial_wide_model_rows.append(n_hdr + self._custom_group_row_idx)

    try:
        right_view = self.tbl_machine.right
        # Alle alten Spans zurücksetzen
        for row in range(right_view.model().rowCount()):
            for col in range(1, right_view.model().columnCount()):
                if right_view.columnSpan(row, col) > 1 or right_view.rowSpan(row, col) > 1:
                    right_view.setSpan(row, col, 1, 1)
        # Neue Spans setzen
        for first_col, span in trial_groups:
            if span <= 1:
                continue
            for row_idx in trial_wide_model_rows:
                right_view.setSpan(row_idx, first_col, 1, span)
        try:
            right_view.viewport().update()
            self.tbl_machine.left.viewport().update()
        except Exception:
            pass
    except Exception:
        pass

    # Alte Row-Delegates komplett zurücksetzen (verhindert Geister-Dropdowns
    # wenn _build_machine_tab mehrfach aufgerufen wird und _n_hdr sich ändert)
    _total_rows = self.model_machine.rowCount()
    for _r in range(_total_rows):
        self.tbl_machine.right.setItemDelegateForRow(_r, None)

    # Dropdown-Delegate für Housing-Zeile (Row n_hdr + 0)
    if self._housing_list:
        self._housing_delegate = HousingComboDelegate(self._housing_list, self.tbl_machine)
        self.tbl_machine.setItemDelegateForRow(n_hdr + 0, self._housing_delegate)

    # Dropdown-Delegate für Jet-Zeile (Row n_hdr + 1)
    if self._jets_list:
        self._jet_delegate = JetComboDelegate(self._jets_list, self.tbl_machine)
        self.tbl_machine.setItemDelegateForRow(n_hdr + 1, self._jet_delegate)

    # LookupComboDelegate für generische dropdown-Zeilen (z.B. DiscID)
    self._lookup_delegates = []
    for row_idx, lk_map in dropdown_rows.items():
        lk_list = [(k, v) for k, v in lk_map.items() if isinstance(k, int)]
        lk_list.sort(key=lambda x: x[1])
        d = LookupComboDelegate(row_idx, lk_list, self.tbl_machine.right)
        self.tbl_machine.right.setItemDelegateForRow(n_hdr + row_idx, d)
        self._lookup_delegates.append(d)

    # Bild-Tooltip für Housing-Zeile
    try:
        self._housing_img_tooltip_filters = []
        for view in self.tbl_machine.findChildren(QTableView):
            f = _HousingImageTooltipFilter(self, self.tbl_machine, self)
            view.viewport().installEventFilter(f)
            self._housing_img_tooltip_filters.append(f)
    except Exception:
        pass

    # ── Ply filter toolbar aufbauen ─────────────────────────────────
    unique_trial_ids_flt = []
    for cs in col_specs:
        if cs.get("trial_id") not in unique_trial_ids_flt:
            unique_trial_ids_flt.append(cs.get("trial_id"))
    has_multi_ply_flt = len(col_specs) > len(unique_trial_ids_flt)

    # Bestehende Checkboxen entfernen
    while self._mat_check_layout.count():
        item = self._mat_check_layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
    self._mat_filter_checks: list = []

    if has_multi_ply_flt:
        # Zeige-Labels aufbauen: im Groups-Modus Gruppen, sonst Plies
        seen_labels_flt: list = []
        seen_set_flt: set = set()
        for cs in col_specs:
            if cs.get("is_group"):
                lbl = str(cs.get("yarn_use_name") or cs.get("ply") or "")
            else:
                lbl = str(cs.get("ply") or "")
            if lbl and lbl not in seen_set_flt:
                seen_set_flt.add(lbl)
                seen_labels_flt.append(lbl)

        lbl_flt = QLabel("Zeige:")
        lbl_flt.setStyleSheet("color: #555; font-size: 11px;")
        self._mat_check_layout.addWidget(lbl_flt)
        for pl in seen_labels_flt:
            cb = QCheckBox(pl)
            cb.setChecked(True)
            cb.stateChanged.connect(self._apply_mat_column_filter)
            self._mat_check_layout.addWidget(cb)
            self._mat_filter_checks.append(cb)

        # Groups-Modus nur anbieten wenn YarnUseIDs in den Settings vorhanden — aus Cache
        has_groups = cache.get("has_groups", False)
        self._rb_groups.setEnabled(has_groups)
        if not has_groups and self._rb_groups.isChecked():
            self._rb_single.setChecked(True)

        self._mat_filter_bar.setVisible(True)
    else:
        # Auch ohne Multi-Ply: Filter-Bar anzeigen damit Modus-Buttons sichtbar bleiben
        # Groups deaktivieren, Single erzwingen
        has_groups = cache.get("has_groups", False)
        self._rb_groups.setEnabled(False)
        if self._rb_groups.isChecked():
            self._rb_single.setChecked(True)
        # Zeige-Checkboxen leeren (keine Plies zum Filtern)
        while self._mat_check_layout.count():
            item = self._mat_check_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._mat_filter_checks = []
        self._mat_filter_bar.setVisible(True)

    # R&D Machine Tab mit RDSetting=1 Feldern aufbauen
    self._build_rd_machine_tab(
        fields_rd=fields_rd,
        machine_id=machine_id,
        col_specs=col_specs,
        settings_cols_map=settings_cols_map,
        trial_rows=trial_rows,
    )


def build_rd_machine_tab_impl(
        self,
        *,
        fields_rd: List[Dict],
        machine_id: Any,
        col_specs: List[Dict],
        settings_cols_map: Dict[str, str],
        trial_rows: List[Dict],
) -> None:
    """Baut den 'R&D Machine Data'-Tab mit RDSetting=1-Feldern auf.
    Tab wird nur angezeigt, wenn mindestens ein solches Feld existiert.
    """

    from ui.screen_show_experiment import (
        table_exists, fetch_all, get_columns_map, resolve_field, norm, canon_rule,
        MachinePivotModel, CellBinding, HousingComboDelegate, JetComboDelegate,
        LookupComboDelegate, _RDHousingTooltipFilter,
    )
    cache = getattr(self, "_machine_cache", None) or {}
    # Tab immer zuerst entfernen (falls bereits vorhanden vom letzten Laden)
    if self.tab_rd_machine is not None:
        idx = self.tabs.indexOf(self.tab_rd_machine)
        if idx != -1:
            self.tabs.removeTab(idx)

    if not fields_rd:
        # Keine R&D-Felder -> Tab bleibt versteckt
        self.model_rd_machine = MachinePivotModel(
            jets_map=self._jets_map,
            row_titles=[],
            col_titles=self._trial_labels,
            read_only_rows=set(),
            row_validators=[],
            jet_row_index=-1,
            housing_map=self._housing_map,
            housing_row_index=-1,
            jets_tooltip_map=self._jets_tooltip_map,
            housing_image_map=getattr(self, "_housing_image_map", {}),
            dropdown_rows={},
        )
        self.tbl_rd_machine.setModel(self.model_rd_machine)
        return

    # Tab direkt nach "Machine Data" einfügen
    machine_idx = self.tabs.indexOf(self.tab_machine)
    insert_pos = machine_idx + 1 if machine_idx != -1 else self.tabs.count()
    self.tabs.insertTab(insert_pos, self.tab_rd_machine, "R&&D Machine Data")

    trial_cols = get_columns_map("tblTrial")

    # Fixe Titel (gleiche wie Machine Data)
    FIX_HOUSING = "Housing"
    FIX_JET = "Jet"
    FIX_PLATE = "Jet Plate Number"
    FIX_AIR = "Air Pressure (bar)"
    titles_fixed = [FIX_HOUSING, FIX_JET, FIX_PLATE, FIX_AIR]
    self._rd_machine_titles_fixed_count = len(titles_fixed)

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

    row_titles = titles_fixed + [f["Title"] for f in field_map]
    row_validators: List[Optional[str]] = [None] * len(row_titles)
    row_validators[2] = reserved_validators.get(FIX_PLATE)
    row_validators[3] = reserved_validators.get(FIX_AIR)
    for i, ff in enumerate(field_validators, start=len(titles_fixed)):
        row_validators[i] = ff

    # Dropdown-Maps aufbauen
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

    # Header-Zeilen
    trial_hdr_vals = [""]
    ply_hdr_vals = [""]
    ply_tooltip_vals = [""]
    for cs in col_specs:
        trial_hdr_vals.append(f"V{cs['vno']}")
        ply_hdr_vals.append(cs["ply"])
        ply_tooltip_vals.append(cs.get("yarn_name") or "")

    hdr_rows = [
        {"values": trial_hdr_vals, "bg": None, "fg": None},
        {"values": ply_hdr_vals, "bg": None, "fg": None, "tooltips": ply_tooltip_vals},
    ]
    expanded_col_titles = ["" for _ in col_specs]

    self.model_rd_machine = MachinePivotModel(
        jets_map=self._jets_map,
        row_titles=row_titles,
        col_titles=expanded_col_titles,
        read_only_rows=set(),
        row_validators=row_validators,
        jet_row_index=1,
        header_rows=hdr_rows,
        housing_map=self._housing_map,
        housing_row_index=0,
        jets_tooltip_map=self._jets_tooltip_map,
        housing_image_map=getattr(self, "_housing_image_map", {}),
        dropdown_rows=dropdown_rows,
    )
    self._register_save_model("model_rd_machine")

    # Zellen befüllen (analog zu _build_machine_tab)
    trial_cols_map = cache.get("trial_cols_map") or get_columns_map("tblTrial")

    def _pick_row_key_rd(row: dict, preferred: Optional[str], extra_cands: List[str]) -> Optional[str]:
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
        self.model_rd_machine.set_cell(
            0, c_idx, housing_id,
            CellBinding("tblTrial", "ID", trow.get("ID"), "HousingID") if (
                        housing_id_col and trow.get("ID")) else None,
        )

    # 1: Jet
    for c_idx, cs in enumerate(col_specs):
        trow = cs["trial"]
        self.model_rd_machine.set_cell(
            1, c_idx, trow.get("JetID"),
            CellBinding("tblTrial", "ID", trow.get("ID"), "JetID") if trow.get("ID") else None,
        )

    # 2: Jet Plate Number
    for c_idx, cs in enumerate(col_specs):
        trow = cs["trial"]
        jp_key = _pick_row_key_rd(trow, jet_plate_col,
                                  ["JetPlate", "jetplate", "Jet_Plate", "jet_plate", "Jet Plate",
                                   "Jet Plate Number", "JetPlateNumber"])
        jp_field = jet_plate_col or jp_key
        self.model_rd_machine.set_cell(
            2, c_idx,
            trow.get(jp_key) if jp_key else None,
            CellBinding("tblTrial", "ID", trow.get("ID"), jp_field) if (jp_field and trow.get("ID")) else None,
        )

    # 3: Air Pressure
    for c_idx, cs in enumerate(col_specs):
        trow = cs["trial"]
        ap_key = _pick_row_key_rd(trow, air_press_col,
                                  ["AirPressure", "airpressure", "Air_Pressure", "air_pressure",
                                   "Air Pressure", "Air Pressure (bar)", "AirPressure(bar)", "Air_Pressure_bar"])
        ap_field = air_press_col or ap_key
        self.model_rd_machine.set_cell(
            3, c_idx,
            trow.get(ap_key) if ap_key else None,
            CellBinding("tblTrial", "ID", trow.get("ID"), ap_field) if (ap_field and trow.get("ID")) else None,
        )

    # Dynamische Felder
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
                self.model_rd_machine.set_cell(r_idx, c_idx, val, binding)
        else:
            real_col = trial_cols_map.get(str(colname).lower()) or colname
            for c_idx, cs in enumerate(col_specs):
                trow = cs["trial"]
                val = trow.get(real_col)
                self.model_rd_machine.set_cell(
                    r_idx, c_idx, val,
                    CellBinding("tblTrial", "ID", trow.get("ID"), real_col) if trow.get("ID") else None,
                )

    self.tbl_rd_machine.setModel(self.model_rd_machine)
    self.tbl_rd_machine.resizeColumnsToContents(fixed_data_column_width=90)
    self.tbl_rd_machine.left.horizontalHeader().setVisible(False)
    self.tbl_rd_machine.right.horizontalHeader().setVisible(False)

    # setSpan für trial-weite Spalten
    n_hdr = self.model_rd_machine._n_hdr
    trial_groups: List[Tuple[int, int]] = []
    _last_tid = None
    _grp_start = 0
    _grp_count = 0
    for ci, cs in enumerate(col_specs):
        tid = cs["trial_id"]
        if tid != _last_tid:
            if _grp_count > 0:
                trial_groups.append((_grp_start, _grp_count))
            _grp_start = ci + 1
            _grp_count = 1
            _last_tid = tid
        else:
            _grp_count += 1
    if _grp_count > 0:
        trial_groups.append((_grp_start, _grp_count))

    trial_wide_model_rows: List[int] = [0]
    trial_wide_model_rows += [n_hdr + 0, n_hdr + 1, n_hdr + 2, n_hdr + 3]
    for offset, fdef in enumerate(field_map):
        if fdef.get("StorageTable", "tbltrial") != "tbltrialsettings":
            trial_wide_model_rows.append(n_hdr + len(titles_fixed) + offset)

    try:
        right_view = self.tbl_rd_machine.right
        for row in range(right_view.model().rowCount()):
            for col in range(1, right_view.model().columnCount()):
                if right_view.columnSpan(row, col) > 1 or right_view.rowSpan(row, col) > 1:
                    right_view.setSpan(row, col, 1, 1)
        for first_col, span in trial_groups:
            if span <= 1:
                continue
            for row_idx in trial_wide_model_rows:
                right_view.setSpan(row_idx, first_col, 1, span)
    except Exception:
        pass

    # Row-Delegates zurücksetzen
    _total_rows = self.model_rd_machine.rowCount()
    for _r in range(_total_rows):
        self.tbl_rd_machine.right.setItemDelegateForRow(_r, None)

    # Housing-Delegate
    if self._housing_list:
        self._rd_housing_delegate = HousingComboDelegate(self._housing_list, self.tbl_rd_machine)
        self.tbl_rd_machine.setItemDelegateForRow(n_hdr + 0, self._rd_housing_delegate)

    # Jet-Delegate
    if self._jets_list:
        self._rd_jet_delegate = JetComboDelegate(self._jets_list, self.tbl_rd_machine)
        self.tbl_rd_machine.setItemDelegateForRow(n_hdr + 1, self._rd_jet_delegate)

    # LookupComboDelegate
    self._rd_lookup_delegates = []
    for row_idx, lk_map in dropdown_rows.items():
        lk_list = [(k, v) for k, v in lk_map.items() if isinstance(k, int)]
        lk_list.sort(key=lambda x: x[1])
        d = LookupComboDelegate(row_idx, lk_list, self.tbl_rd_machine.right)
        self.tbl_rd_machine.right.setItemDelegateForRow(n_hdr + row_idx, d)
        self._rd_lookup_delegates.append(d)

    # col_specs für _fill_machine_row_from_title
    self._rd_machine_col_specs = col_specs

    # ── Tooltips: Housing-Zeilen und OF-Zeile auf Model markieren ────
    housing_rows = set()
    of_row_idx = None
    for i, title in enumerate(row_titles):
        tl = title.lower()
        if "housing" in tl:
            housing_rows.add(i)
        if "w0" in tl and "w1" in tl and "of" in tl:
            of_row_idx = i

    self.model_rd_machine._all_housing_rows = housing_rows

    jet_rows = set()
    for i, title in enumerate(row_titles):
        if "jet" in title.lower():
            jet_rows.add(i)
    self.model_rd_machine._all_jet_rows = jet_rows

    # Install Housing Bild-Tooltip filter for R&D tab
    try:
        self._rd_housing_tooltip_filters = []
        for view in self.tbl_rd_machine.findChildren(QTableView):
            f = _RDHousingTooltipFilter(self, self.tbl_rd_machine, self)
            view.viewport().installEventFilter(f)
            self._rd_housing_tooltip_filters.append(f)
    except Exception:
        pass

    if of_row_idx is not None:
        _of_row = of_row_idx
        _screen = self

        def _of_calc(col_0based, _of_row=_of_row, _screen=_screen):
            model_rd = _screen.model_rd_machine
            model_m = _screen.model_machine
            if model_rd is None or model_m is None:
                return None

            def _val(model, title_norm):
                for i, t in enumerate(getattr(model, "_row_titles", [])):
                    n = t.lower()
                    for ch in " _()-/":
                        n = n.replace(ch, "")
                    if n == title_norm:
                        mx = getattr(model, "_matrix", [])
                        if 0 <= i < len(mx) and 0 <= col_0based < len(mx[i]):
                            try:
                                return float(mx[i][col_0based])
                            except Exception:
                                return None
                return None

            speed = _val(model_m, "speedshaft2mmin")
            dr = _val(model_m, "shaft1dr")
            of_val = _val(model_rd, "w0w1of%")
            if of_val is None:
                of_val = _val(model_rd, "w0w1of")
            if speed is None or dr is None or of_val is None or dr == 0:
                return None
            result = speed / dr * (100 + of_val) / 100
            return f"Speed: {int(round(result))} m/min"

        self.model_rd_machine._of_tooltip_row = of_row_idx
        self.model_rd_machine._of_tooltip_calc = _of_calc
    else:
        self.model_rd_machine._of_tooltip_row = None
        self.model_rd_machine._of_tooltip_calc = None



def fill_machine_row_from_title_impl(self, row: int, is_rd: bool = False) -> None:
    """Dialog anzeigen und eine komplette Zeile im Machine-Tab befüllen."""
    from ui.screen_show_experiment import (
        _FillRowRangeDialog, _FillRowRangeJetDialog,
        _FillRowRangeDropdownDialog, _FillRowRangeHousingDialog,
    )

    cache = getattr(self, "_machine_cache", None) or {}
    _model = self.model_rd_machine if is_rd else self.model_machine
    _tbl = self.tbl_rd_machine if is_rd else self.tbl_machine
    _col_specs = getattr(self, "_rd_machine_col_specs" if is_rd else "_machine_col_specs", None)
    if not _model:
        return

    # pseudo-header rows ignorieren
    n_hdr = getattr(_model, "_n_hdr", 0)
    if row < n_hdr:
        return

    # Enforce permissions (AccessLevel >= 2 required for bulk row set)
    try:
        lvl = int(getattr(app_meta, "access_level", lambda: 0)() or 0)
    except Exception:
        try:
            user = getattr(app_meta, "current_user", {}) or {}
            lvl = int(user.get("access_level")
                      or user.get("AccessLevel") or 0)
        except Exception:
            lvl = 0
    if lvl < 2:
        QMessageBox.information(
            self,
            "Permission denied",
            "You do not have permission to change values.",
        )
        return

    # Titel der Zeile ermitteln
    title_index = self.model_machine.index(row, 0)
    title = str(self.model_machine.data(title_index, Qt.DisplayRole) or "")

    # Defaultwert: erstes nicht-leeres, editierbares Feld in dieser Zeile
    default_text = ""
    for col in range(1, self.model_machine.columnCount()):
        idx = self.model_machine.index(row, col)
        if not (self.model_machine.flags(idx) & Qt.ItemIsEditable):
            continue
        val = self.model_machine.data(idx, Qt.DisplayRole)
        if val not in (None, ""):
            default_text = str(val)
            break

    # Real trial count (not column count which includes Ply expansions)
    _col_specs_tmp = getattr(self, "_machine_col_specs", None) or []
    if _col_specs_tmp:
        _unique_tids = []
        for _cs in _col_specs_tmp:
            if _cs.get("trial_id") not in _unique_tids:
                _unique_tids.append(_cs.get("trial_id"))
        n_trials = max(1, len(_unique_tids))
    else:
        n_trials = max(1, self.model_machine.columnCount() - 1)
    if n_trials <= 0:
        return

    housing_model_row = n_hdr + 0  # Housing ist data-row 0
    jet_model_row = n_hdr + 1  # Jet ist data-row 1

    if row == housing_model_row and self._housing_list:
        # Housing-Zeile: Dropdown
        default_housing_id = None
        try:
            for col in range(1, self.model_machine.columnCount()):
                internal = self.model_machine.get_cell_value(row - n_hdr, col - 1)
                if internal not in (None, "", " "):
                    default_housing_id = internal
                    break
        except Exception:
            default_housing_id = None

        dlgh = _FillRowRangeHousingDialog(
            self, title=title, n_trials=n_trials,
            housing_list=self._housing_list, default_housing_id=default_housing_id,
        )
        if dlgh.exec() != QDialog.Accepted:
            return
        start_trial, end_trial, housing_id = dlgh.get_values()
        value_to_set = housing_id

    elif row == jet_model_row and self._jets_list:
        # Jet-Zeile: Dropdown
        default_jet_id = None
        try:
            for col in range(1, self.model_machine.columnCount()):
                internal = self.model_machine.get_cell_value(row - n_hdr, col - 1)
                if internal not in (None, "", " "):
                    default_jet_id = internal
                    break
        except Exception:
            default_jet_id = None

        dlgj = _FillRowRangeJetDialog(
            self, title=title, n_trials=n_trials,
            jets_list=self._jets_list, default_jet_id=default_jet_id,
        )
        if dlgj.exec() != QDialog.Accepted:
            return
        start_trial, end_trial, jet_id = dlgj.get_values()
        value_to_set = jet_id

    elif (row - n_hdr) in getattr(self.model_machine, "_dropdown_rows", {}):
        # Generische Lookup-Zeile (z.B. DiscType): Dropdown
        data_row = row - n_hdr
        lk_map = self.model_machine._dropdown_rows[data_row]
        default_id = None
        try:
            for col in range(1, self.model_machine.columnCount()):
                internal = self.model_machine.get_cell_value(data_row, col - 1)
                if internal not in (None, "", " "):
                    default_id = internal
                    break
        except Exception:
            default_id = None

        # Determine ply_labels for this dropdown row (same logic as text rows)
        col_specs_dd = getattr(self, "_machine_col_specs", None) or []
        _seen_plies_dd: list = []
        _seen_set_dd: set = set()
        for cs in col_specs_dd:
            pl = str(cs.get("ply") or "")
            if pl and pl not in _seen_set_dd:
                _seen_set_dd.add(pl)
                _seen_plies_dd.append(pl)
        unique_trial_ids_dd = []
        for cs in col_specs_dd:
            if cs.get("trial_id") not in unique_trial_ids_dd:
                unique_trial_ids_dd.append(cs.get("trial_id"))
        has_multi_ply_dd = len(col_specs_dd) > len(unique_trial_ids_dd)
        ply_labels_dd = _seen_plies_dd if has_multi_ply_dd else []

        dlgd = _FillRowRangeDropdownDialog(
            self, title=title, n_trials=n_trials,
            lookup_map=lk_map, default_id=default_id,
            ply_labels=ply_labels_dd,
        )
        if dlgd.exec() != QDialog.Accepted:
            return
        start_trial, end_trial, value_to_set, selected_plies_dd = dlgd.get_values()

        # Apply: über col_specs iterieren, mit optionalem Ply-Filter
        col_specs = getattr(self, "_machine_col_specs", None) or []
        unique_trial_ids = []
        for cs in col_specs:
            if cs.get("trial_id") not in unique_trial_ids:
                unique_trial_ids.append(cs.get("trial_id"))
        trial_order = {tid: i + 1 for i, tid in enumerate(unique_trial_ids)}
        if col_specs:
            for c_idx, cs in enumerate(col_specs):
                ti = trial_order.get(cs.get("trial_id"), 0)
                if not (start_trial <= ti <= end_trial):
                    continue
                if selected_plies_dd is not None:
                    ply = str(cs.get("ply") or "")
                    if ply not in selected_plies_dd:
                        continue
                model_col = c_idx + 1  # col 0 = title
                idx = self.model_machine.index(row, model_col)
                if self.model_machine.flags(idx) & Qt.ItemIsEditable:
                    self.model_machine.setData(idx, value_to_set, Qt.EditRole)
        else:
            for col in range(start_trial, end_trial + 1):
                idx = self.model_machine.index(row, col)
                if self.model_machine.flags(idx) & Qt.ItemIsEditable:
                    self.model_machine.setData(idx, value_to_set, Qt.EditRole)
        return

    else:
        # Determine whether this is a tblTrialSettings row (Ply-specific)
        # or a tblTrial row (trial-wide) so we can show/hide Ply checkboxes.
        col_specs = getattr(self, "_machine_col_specs", None) or []
        n_hdr = getattr(self.model_machine, "_n_hdr", 0)
        if is_rd:
            titles_fixed_count = getattr(self, "_rd_machine_titles_fixed_count", 4)
        else:
            titles_fixed_count = getattr(self, "_machine_titles_fixed_count", 5)

        # Im Groups-Modus: Gruppen-Labels statt Ply-Labels für den Dialog
        use_groups = getattr(self._rb_groups, "isChecked", lambda: False)()

        # Collect distinct, ordered labels from col_specs
        _seen_plies: list = []
        _seen_set: set = set()
        for cs in col_specs:
            if use_groups:
                pl = str(cs.get("yarn_use_name") or cs.get("ply") or "")
            else:
                pl = str(cs.get("ply") or "")
            if pl and pl not in _seen_set:
                _seen_set.add(pl)
                _seen_plies.append(pl)

        # A row is Ply-specific if it maps to tblTrialSettings.
        # Fixed rows (Housing/Jet/Plate/Air) and tblTrial dynamic fields are trial-wide.
        data_row_idx = row - n_hdr  # 0-based into row_titles
        is_ply_row = False
        if data_row_idx >= titles_fixed_count and col_specs:
            # Dynamic field: check field_map (stored in model via row_titles)
            # Easiest: if any two adjacent col_specs for the same trial differ
            # in ply → the row lives in tblTrialSettings.
            # More reliable: check if multiple col_specs share a trial_id
            # (which only happens when tblTrialSettings is used).
            trial_ids_seen: list = []
            for cs in col_specs:
                tid = cs.get("trial_id")
                if tid not in trial_ids_seen:
                    trial_ids_seen.append(tid)
            # If we have more col_specs than unique trials → multi-ply → some rows are Ply-specific.
            # We determine whether *this specific row* is Ply-specific by checking whether
            # all col_specs in this row have different sr (settings row) per trial.
            has_multi_ply = len(col_specs) > len(trial_ids_seen)
            if has_multi_ply:
                # Check the model_machine row_titles for this row
                row_title_idx = self.model_machine.index(row, 0)
                rt = str(self.model_machine.data(row_title_idx, Qt.DisplayRole) or "")
                # Heuristic: if any col_spec has sr != None for this row,
                # the field is in tblTrialSettings.
                # We detect this via MachinePivotModel's binding list.
                # Simplest robust approach: check whether the binding of col 1 (first data col)
                # references tblTrialSettings.
                try:
                    b = self.model_machine.get_binding(data_row_idx, 0)
                    if b is not None and str(getattr(b, "table", "") or "").lower() == "tbltrialsettings":
                        is_ply_row = True
                except Exception:
                    pass

        ply_labels_for_dlg = _seen_plies if is_ply_row else []

        # n_trials = actual number of distinct trials (not column count)
        unique_trial_ids = []
        for cs in col_specs:
            if cs.get("trial_id") not in unique_trial_ids:
                unique_trial_ids.append(cs.get("trial_id"))
        n_trials_real = len(unique_trial_ids) if unique_trial_ids else n_trials

        dlg = _FillRowRangeDialog(
            self, title=title,
            n_trials=n_trials_real,
            default_value=default_text,
            ply_labels=ply_labels_for_dlg,
        )
        if dlg.exec() != QDialog.Accepted:
            return
        start_trial, end_trial, text, selected_plies = dlg.get_values()
        value_to_set = text

        # Apply: iterate col_specs to find matching (trial_index, ply) combinations
        if col_specs:
            # Map trial_id -> 1-based trial index (by order in unique_trial_ids)
            trial_order = {tid: i + 1 for i, tid in enumerate(unique_trial_ids)}
            for c_idx, cs in enumerate(col_specs):
                ti = trial_order.get(cs.get("trial_id"), 0)
                if not (start_trial <= ti <= end_trial):
                    continue
                if selected_plies is not None:
                    ply = str(cs.get("ply") or "")
                    if ply not in selected_plies:
                        continue
                model_col = c_idx + 1  # column 0 = title
                idx = self.model_machine.index(row, model_col)
                if not (self.model_machine.flags(idx) & Qt.ItemIsEditable):
                    continue
                self.model_machine.setData(idx, value_to_set, Qt.EditRole)
        else:
            for col in range(start_trial, end_trial + 1):
                idx = self.model_machine.index(row, col)
                if not (self.model_machine.flags(idx) & Qt.ItemIsEditable):
                    continue
                self.model_machine.setData(idx, value_to_set, Qt.EditRole)
        return  # early return — apply already done above

    # Apply for Housing / Jet (trial-wide, no Ply distinction needed)
    # These rows are always spanned across plies → only one col per trial group.
    if col_specs := getattr(self, "_machine_col_specs", None):
        unique_trial_ids2 = []
        for cs in col_specs:
            if cs.get("trial_id") not in unique_trial_ids2:
                unique_trial_ids2.append(cs.get("trial_id"))
        trial_order2 = {tid: i + 1 for i, tid in enumerate(unique_trial_ids2)}
        n_trials_real2 = len(unique_trial_ids2)
        for c_idx, cs in enumerate(col_specs):
            ti = trial_order2.get(cs.get("trial_id"), 0)
            if not (start_trial <= ti <= end_trial):
                continue
            model_col = c_idx + 1
            idx = self.model_machine.index(row, model_col)
            if not (self.model_machine.flags(idx) & Qt.ItemIsEditable):
                continue
            self.model_machine.setData(idx, value_to_set, Qt.EditRole)
    else:
        for col in range(start_trial, end_trial + 1):
            idx = self.model_machine.index(row, col)
            if not (self.model_machine.flags(idx) & Qt.ItemIsEditable):
                continue
            self.model_machine.setData(idx, value_to_set, Qt.EditRole)

