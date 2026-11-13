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

from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QCheckBox, QTableView, QMessageBox, QDialog

import app_meta


# Data of the tab (rows, columns, cells, D/Y ratio, header rows) lives Qt-free in
# db/machine_data.py (shared with the web app); re-exported here under the old names.
from db.machine_data import (  # noqa: E402,F401
    DY_RATIO_TITLE,
    DY_RATIO_STORAGE as _DY_RATIO_STORAGE,
    dy_ratio_text,
    insert_dy_ratio_field as _insert_dy_ratio_field,
    ply_header_colour,
)


def _wire_dy_ratio_row(model, r_t1: int, r_t2: int, r_ratio: int) -> None:
    """Keeps the D/Y ratio row (filled by db/machine_data) current while
    T1/T2 are edited (typing, paste, fill range)."""
    from PySide6.QtCore import Qt as _Qt

    def _update(c: int) -> None:
        txt = dy_ratio_text(model.get_cell_value(r_t1, c), model.get_cell_value(r_t2, c))
        if model.get_cell_value(r_ratio, c) != txt:
            model._matrix[r_ratio][c] = txt
            idx = model.index(model._n_hdr + r_ratio, c + 1)
            model.dataChanged.emit(idx, idx, [_Qt.DisplayRole])

    def _on_changed(top_left, bottom_right, _roles=None) -> None:
        r0, r1 = top_left.row() - model._n_hdr, bottom_right.row() - model._n_hdr
        if not (r0 <= r_t1 <= r1 or r0 <= r_t2 <= r1):
            return
        for col in range(max(1, top_left.column()), bottom_right.column() + 1):
            _update(col - 1)

    model.dataChanged.connect(_on_changed)


def _trial_hdr_label(self, cs: Dict) -> str:
    """Trial header text for one column spec - "REF V<n>" for reference
    samples (see ShowExperimentScreen._load_trials), else "V<n>"."""
    from db.machine_data import trial_hdr_label
    return trial_hdr_label(cs, getattr(self, "_reference_names", {}))


def _set_trial_spans(table, trial_groups, rows) -> None:
    """One merged cell per trial (over all its ply columns) in the given rows.
    Set in the data part (right) AND the frozen header part (top_right) of the
    FrozenFirstColumnTable - the trial number row 0 is drawn up there, so
    without it "V3 | V3" showed twice for a trial with two plies."""
    views = [table.right]
    top = getattr(table, "top_right", None)
    if top is not None:
        views.append(top)
    for view in views:
        model = view.model()
        if model is None:
            continue
        for row in range(model.rowCount()):
            for col in range(1, model.columnCount()):
                if view.columnSpan(row, col) > 1 or view.rowSpan(row, col) > 1:
                    view.setSpan(row, col, 1, 1)
        for first_col, span in trial_groups:
            if span <= 1:
                continue
            for row_idx in rows:
                view.setSpan(row_idx, first_col, 1, span)


def build_machine_tab_impl(self) -> None:
    """Machine Data tab. All data (rows, columns, cells, header rows, dropdowns,
    rows to hide, spans) comes from db/machine_data.build_machine_data; here only
    the Qt parts: model, view, delegates, spans, filter bar, radio buttons."""
    from ui.screen_show_experiment import (
        PivotEditModel, MachinePivotModel,
        HousingComboDelegate, JetComboDelegate, LookupComboDelegate,
        _HousingImageTooltipFilter,
    )
    from db import machine_data as _md

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

    md = _md.build_machine_data(self._series_trials_data(), self._last_view_mode, cache)
    if md.message:
        self.machine_info.setText(md.message)
        self.tbl_machine.setModel(PivotEditModel([], self._trial_labels))
        return

    # Von der Fill-Range-Logik (Kontextmenue) genutzt, um zu erkennen ob ein
    # Feld zu tblTrialSettings (Ply-spezifisch) gehoert (Single Plies: 6 Fixzeilen).
    self._machine_titles_fixed_count = len(md.titles_fixed)
    # Row keys for the DTY process schema (ui/dty_stations.py), aligned with the rows
    self._machine_row_keys = md.row_keys
    self._custom_group_row_idx = md.custom_group_row  # Modell-Zeilenindex (0-basiert, ohne Header-Zeilen)
    if md.spool_tooltips is not None:  # Single Plies only (Spool row)
        self._spool_tooltip_map: Dict[int, str] = md.spool_tooltips

    if not self._trial_ids:
        self.model_machine = MachinePivotModel(
            jets_map=self._jets_map,
            row_titles=md.row_titles,
            col_titles=self._trial_labels,
            read_only_rows=set(md.read_only_rows),
            row_validators=md.validators,
            jet_row_index=_md.JET_ROW,
            housing_map=self._housing_map,
            housing_row_index=_md.HOUSING_ROW,
            jets_tooltip_map=self._jets_tooltip_map,
            housing_image_map=getattr(self, "_housing_image_map", {}),
            dropdown_rows=md.dropdown_rows,
        )
        self._register_save_model("model_machine")
        self.tbl_machine.setModel(self.model_machine)
        # R&D Tab ebenfalls ausblenden
        if self.tab_rd_machine is not None:
            idx = self.tabs.indexOf(self.tab_rd_machine)
            if idx != -1:
                self.tabs.removeTab(idx)
        return

    col_specs = md.col_specs

    # ── Modell instanzieren ───────────────────────────────────────────
    # Spalten-Titel leer – Ply-Labels stehen bereits in header_rows[1]
    self.model_machine = MachinePivotModel(
        jets_map=self._jets_map,
        row_titles=md.row_titles,
        col_titles=["" for _ in col_specs],
        read_only_rows=set(md.read_only_rows),
        row_validators=md.validators,
        jet_row_index=_md.JET_ROW,
        header_rows=md.header_rows,
        housing_map=self._housing_map,
        housing_row_index=_md.HOUSING_ROW,
        jets_tooltip_map=self._jets_tooltip_map,
        housing_image_map=getattr(self, "_housing_image_map", {}),
        dropdown_rows=md.dropdown_rows,
    )
    self._register_save_model("model_machine")
    self._machine_col_specs = col_specs  # for multi-ply feature tracking
    self._apply_reference_columns(self.model_machine, [cs["trial_id"] for cs in col_specs])

    # ── Zellen befüllen ───────────────────────────────────────────────
    model = self.model_machine
    for r_idx, row in enumerate(md.cells):
        for c_idx, (value, binding) in enumerate(row):
            model.set_cell(r_idx, c_idx, value, binding)
    model._cell_tooltips.update(md.cell_tooltips)
    model._cell_alerts.update(md.cell_alerts)
    if md.dy_ratio is not None:
        _wire_dy_ratio_row(model, *md.dy_ratio)

    self.tbl_machine.setModel(self.model_machine)
    self.tbl_machine.resizeColumnsToContents(fixed_data_column_width=90)

    # Qt-Column-Header ausblenden – Ply/V-Labels stehen bereits in den Modell-Header-Zeilen
    self.tbl_machine.left.horizontalHeader().setVisible(False)
    self.tbl_machine.right.horizontalHeader().setVisible(False)

    # Custom-Group-Zeile + vom Nutzer ausgeblendete Zeilen (pro Maschine gemerkt)
    from ui import machine_row_visibility as _mrv
    from ui import dty_schema_panel as _dsp
    self._process_hidden_rows = set(md.process_hidden_rows)  # pre-jet / jet 3 rows only where needed
    _mrv.install(self)
    _mrv.apply(self)

    # ── setSpan für trial-weite Spalten ───────────────────────────────
    # Jede Trial-Gruppe über alle ihre Ply-Spalten gespannt (model_col =
    # 1-basiert, Spalte 0 = Zeilentitel), in Header-Zeile 0 (V-Nummer) und
    # allen trial-weiten Datenzeilen (md.trial_wide_rows).
    trial_groups: List[Tuple[int, int]] = [(first + 1, span) for first, span in md.trial_spans]
    n_hdr = self.model_machine._n_hdr  # = 2
    trial_wide_model_rows: List[int] = [0] + [n_hdr + r for r in md.trial_wide_rows]

    try:
        right_view = self.tbl_machine.right
        _set_trial_spans(self.tbl_machine, trial_groups, trial_wide_model_rows)
        try:
            right_view.viewport().update()
            self.tbl_machine.top_right.viewport().update()
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
        self.tbl_machine.setItemDelegateForRow(n_hdr + _md.HOUSING_ROW, self._housing_delegate)

    # Dropdown-Delegate für Jet-Zeile (Row n_hdr + 1)
    if self._jets_list:
        self._jet_delegate = JetComboDelegate(self._jets_list, self.tbl_machine)
        self.tbl_machine.setItemDelegateForRow(n_hdr + _md.JET_ROW, self._jet_delegate)

    # LookupComboDelegate für generische dropdown-Zeilen (z.B. DiscID) - Einträge aus md
    self._lookup_delegates = []
    for row_idx, lk_list in md.dropdown_lists.items():
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
    # Bestehende Checkboxen entfernen
    while self._mat_check_layout.count():
        item = self._mat_check_layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
    self._mat_filter_checks: list = []

    if md.has_multi_ply:
        # Zeige-Labels: im Groups-Modus Gruppen, sonst Plies (md.filter_labels)
        lbl_flt = QLabel("Show:")
        lbl_flt.setStyleSheet("color: #555; font-size: 11px;")
        self._mat_check_layout.addWidget(lbl_flt)
        for pl in md.filter_labels:
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
        fields_rd=md.fields_rd,
        machine_id=md.machine_id,
        col_specs=col_specs,
        settings_cols_map=md.settings_cols_map,
        trial_rows=md.trial_rows,
    )
    _dsp.refresh(self)  # DTY process schema above the table


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
    All data (rows, cells, dropdowns, header rows, spans, tooltip rows) comes from
    db/machine_data.rd_machine_data_from; here only the Qt parts: tab, model, view,
    delegates, spans, housing picture filter, live OF speed tooltip."""

    from ui.screen_show_experiment import (
        MachinePivotModel, HousingComboDelegate, JetComboDelegate,
        LookupComboDelegate, _RDHousingTooltipFilter,
    )
    from db import machine_data as _md
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

    rd = _md.rd_machine_data_from(fields_rd, col_specs, settings_cols_map, cache,
                                  getattr(self, "_reference_names", {}), machine_id=machine_id)
    self._rd_machine_titles_fixed_count = len(rd.titles_fixed)
    # row keys (DB column, lower case) for the Knowledge Base links (ui/kb_links.py)
    self._rd_machine_row_keys = rd.row_keys

    self.model_rd_machine = MachinePivotModel(
        jets_map=self._jets_map,
        row_titles=rd.row_titles,
        col_titles=["" for _ in col_specs],
        read_only_rows=set(rd.read_only_rows),
        row_validators=rd.validators,
        jet_row_index=_md.JET_ROW,
        header_rows=rd.header_rows,
        housing_map=self._housing_map,
        housing_row_index=_md.HOUSING_ROW,
        jets_tooltip_map=self._jets_tooltip_map,
        housing_image_map=getattr(self, "_housing_image_map", {}),
        dropdown_rows=rd.dropdown_rows,
    )
    self._register_save_model("model_rd_machine")
    self._apply_reference_columns(self.model_rd_machine, [cs["trial_id"] for cs in col_specs])

    # Zellen befüllen
    model = self.model_rd_machine
    for r_idx, row in enumerate(rd.cells):
        for c_idx, (value, binding) in enumerate(row):
            model.set_cell(r_idx, c_idx, value, binding)
    model._cell_tooltips.update(rd.cell_tooltips)
    model._cell_alerts.update(rd.cell_alerts)

    self.tbl_rd_machine.setModel(self.model_rd_machine)
    self.tbl_rd_machine.resizeColumnsToContents(fixed_data_column_width=90)
    self.tbl_rd_machine.left.horizontalHeader().setVisible(False)
    self.tbl_rd_machine.right.horizontalHeader().setVisible(False)

    # setSpan für trial-weite Spalten (model col = data col + 1, Spalte 0 = Zeilentitel)
    n_hdr = self.model_rd_machine._n_hdr
    trial_groups: List[Tuple[int, int]] = [(first + 1, span) for first, span in rd.trial_spans]
    trial_wide_model_rows: List[int] = [0] + [n_hdr + r for r in rd.trial_wide_rows]

    try:
        _set_trial_spans(self.tbl_rd_machine, trial_groups, trial_wide_model_rows)
    except Exception:
        pass

    # Row-Delegates zurücksetzen
    _total_rows = self.model_rd_machine.rowCount()
    for _r in range(_total_rows):
        self.tbl_rd_machine.right.setItemDelegateForRow(_r, None)

    # Housing-Delegate
    if self._housing_list:
        self._rd_housing_delegate = HousingComboDelegate(self._housing_list, self.tbl_rd_machine)
        self.tbl_rd_machine.setItemDelegateForRow(n_hdr + _md.HOUSING_ROW, self._rd_housing_delegate)

    # Jet-Delegate
    if self._jets_list:
        self._rd_jet_delegate = JetComboDelegate(self._jets_list, self.tbl_rd_machine)
        self.tbl_rd_machine.setItemDelegateForRow(n_hdr + _md.JET_ROW, self._rd_jet_delegate)

    # LookupComboDelegate - Einträge aus rd
    self._rd_lookup_delegates = []
    for row_idx, lk_list in rd.dropdown_lists.items():
        d = LookupComboDelegate(row_idx, lk_list, self.tbl_rd_machine.right)
        self.tbl_rd_machine.right.setItemDelegateForRow(n_hdr + row_idx, d)
        self._rd_lookup_delegates.append(d)

    # col_specs für _fill_machine_row_from_title
    self._rd_machine_col_specs = col_specs

    # ── Tooltips: Housing-Zeilen und Jet-Zeilen auf Model markieren ────
    self.model_rd_machine._all_housing_rows = set(rd.housing_rows)
    self.model_rd_machine._all_jet_rows = set(rd.jet_rows)

    # Install Housing Bild-Tooltip filter for R&D tab
    try:
        self._rd_housing_tooltip_filters = []
        for view in self.tbl_rd_machine.findChildren(QTableView):
            f = _RDHousingTooltipFilter(self, self.tbl_rd_machine, self)
            view.viewport().installEventFilter(f)
            self._rd_housing_tooltip_filters.append(f)
    except Exception:
        pass

    if rd.of_row is not None:
        _screen = self

        def _of_calc(col_0based, _screen=_screen):
            # live: reads the current (possibly edited) cells of both models
            model_rd = _screen.model_rd_machine
            model_m = _screen.model_machine
            if model_rd is None or model_m is None:
                return None
            return _md.of_speed_tooltip(
                getattr(model_m, "_row_titles", []), getattr(model_m, "_matrix", []),
                getattr(model_rd, "_row_titles", []), getattr(model_rd, "_matrix", []),
                col_0based)

        self.model_rd_machine._of_tooltip_row = rd.of_row
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
    if (row - n_hdr) in getattr(_model, "_readonly", set()) \
            and _model.data(_model.index(row, 0), Qt.DisplayRole) == DY_RATIO_TITLE:
        return

    # Enforce permissions (AccessLevel >= 2 required for bulk row set;
    # _get_access_level() also covers the recycle bin preview)
    lvl = self._get_access_level()
    if lvl < 2:
        QMessageBox.information(
            self,
            "Permission denied",
            "You do not have permission to change values.",
        )
        return

    # Titel der Zeile ermitteln
    title_index = _model.index(row, 0)
    title = str(_model.data(title_index, Qt.DisplayRole) or "")

    # Defaultwert: erstes nicht-leeres, editierbares Feld in dieser Zeile
    default_text = ""
    for col in range(1, _model.columnCount()):
        idx = _model.index(row, col)
        if not (_model.flags(idx) & Qt.ItemIsEditable):
            continue
        val = _model.data(idx, Qt.DisplayRole)
        if val not in (None, ""):
            default_text = str(val)
            break

    # Real trial count (not column count which includes Ply expansions)
    _col_specs_tmp = _col_specs or []
    if _col_specs_tmp:
        _unique_tids = []
        for _cs in _col_specs_tmp:
            if _cs.get("trial_id") not in _unique_tids:
                _unique_tids.append(_cs.get("trial_id"))
        n_trials = max(1, len(_unique_tids))
    else:
        n_trials = max(1, _model.columnCount() - 1)
    if n_trials <= 0:
        return

    housing_model_row = n_hdr + 0  # Housing ist data-row 0
    jet_model_row = n_hdr + 1  # Jet ist data-row 1

    if row == housing_model_row and self._housing_list:
        # Housing-Zeile: Dropdown
        default_housing_id = None
        try:
            for col in range(1, _model.columnCount()):
                internal = _model.get_cell_value(row - n_hdr, col - 1)
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
        from db.usage_log import log_usage_event
        log_usage_event("feature", "fill_range_bulk_edit", "housing")
        start_trial, end_trial, housing_id = dlgh.get_values()
        value_to_set = housing_id

    elif row == jet_model_row and self._jets_list:
        # Jet-Zeile: Dropdown
        default_jet_id = None
        try:
            for col in range(1, _model.columnCount()):
                internal = _model.get_cell_value(row - n_hdr, col - 1)
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
        from db.usage_log import log_usage_event
        log_usage_event("feature", "fill_range_bulk_edit", "jet")
        start_trial, end_trial, jet_id = dlgj.get_values()
        value_to_set = jet_id

    elif (row - n_hdr) in getattr(_model, "_dropdown_rows", {}):
        # Generische Lookup-Zeile (z.B. DiscType): Dropdown
        data_row = row - n_hdr
        lk_map = _model._dropdown_rows[data_row]
        default_id = None
        try:
            for col in range(1, _model.columnCount()):
                internal = _model.get_cell_value(data_row, col - 1)
                if internal not in (None, "", " "):
                    default_id = internal
                    break
        except Exception:
            default_id = None

        # Determine ply_labels for this dropdown row (same logic as text rows)
        col_specs_dd = _col_specs or []
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
        from db.usage_log import log_usage_event
        log_usage_event("feature", "fill_range_bulk_edit", "dropdown")
        start_trial, end_trial, value_to_set, selected_plies_dd = dlgd.get_values()

        # Apply: über col_specs iterieren, mit optionalem Ply-Filter
        col_specs = _col_specs or []
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
                idx = _model.index(row, model_col)
                if _model.flags(idx) & Qt.ItemIsEditable:
                    _model.setData(idx, value_to_set, Qt.EditRole)
        else:
            for col in range(start_trial, end_trial + 1):
                idx = _model.index(row, col)
                if _model.flags(idx) & Qt.ItemIsEditable:
                    _model.setData(idx, value_to_set, Qt.EditRole)
        return

    else:
        # Determine whether this is a tblTrialSettings row (Ply-specific)
        # or a tblTrial row (trial-wide) so we can show/hide Ply checkboxes.
        col_specs = _col_specs or []
        n_hdr = getattr(_model, "_n_hdr", 0)
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
                row_title_idx = _model.index(row, 0)
                rt = str(_model.data(row_title_idx, Qt.DisplayRole) or "")
                # Heuristic: if any col_spec has sr != None for this row,
                # the field is in tblTrialSettings.
                # We detect this via MachinePivotModel's binding list.
                # Simplest robust approach: check whether the binding of col 1 (first data col)
                # references tblTrialSettings.
                try:
                    b = _model.get_binding(data_row_idx, 0)
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
        from db.usage_log import log_usage_event
        log_usage_event("feature", "fill_range_bulk_edit", "text")
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
                idx = _model.index(row, model_col)
                if not (_model.flags(idx) & Qt.ItemIsEditable):
                    continue
                _model.setData(idx, value_to_set, Qt.EditRole)
        else:
            for col in range(start_trial, end_trial + 1):
                idx = _model.index(row, col)
                if not (_model.flags(idx) & Qt.ItemIsEditable):
                    continue
                _model.setData(idx, value_to_set, Qt.EditRole)
        return  # early return — apply already done above

    # Apply for Housing / Jet (trial-wide, no Ply distinction needed)
    # These rows are always spanned across plies → only one col per trial group.
    if col_specs := _col_specs:
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
            idx = _model.index(row, model_col)
            if not (_model.flags(idx) & Qt.ItemIsEditable):
                continue
            _model.setData(idx, value_to_set, Qt.EditRole)
    else:
        for col in range(start_trial, end_trial + 1):
            idx = _model.index(row, col)
            if not (_model.flags(idx) & Qt.ItemIsEditable):
                continue
            _model.setData(idx, value_to_set, Qt.EditRole)

