# ui/screen_new_yarn.py
"""Formular-Ansicht für einen einzelnen tblYarn-Datensatz.

Analog zu screen_new_jet.py/screen_new_top_plate.py (dynamisches Zwei-Spalten-
Formular aus den übergebenen Spalten + FK-Maps), aber ohne Files-Tab (Yarn hat
keine Datei-Anhänge) und ohne Namens-Eindeutigkeitsprüfung (an dieser Stelle
für Yarn bislang nicht verlangt/vorhanden).

Bedient sowohl "bestehenden Datensatz bearbeiten" (main.py's _go_edit_yarn_form,
UPDATE) als auch "neuen Datensatz anlegen" (main.py's _go_new_yarn_form, INSERT
- seit 2026-08-24, löst das frühere sofortige Blank-Insert in ManageYarnScreen
ab) - welcher Modus aktiv ist, entscheidet sich rein über den on_save/on_created-
Callback, den main.py bei jeder Navigation neu einhängt; dieser Screen selbst
kennt den Unterschied nicht.

MinStock ist separat sperrbar (set_minstock_locked) statt das ganze Formular
read-only zu machen: AdminBox=0-User dürfen laut Anforderung alles ausser
MinStock und Löschen bearbeiten - anders als bei Jets/Top Plates, wo Read-only
alles-oder-nichts ist. MinStock selbst ist seit 2026-10-13 nur fuer Superuser
editierbar (app_meta.can_edit_min_stock()).
"""

from typing import List, Dict, Optional, Callable, Set

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QScrollArea, QFormLayout, QLabel,
    QLineEdit, QComboBox, QHBoxLayout, QPushButton, QMessageBox,
    QSizePolicy,
)

from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from ui.text_normalize import canon_simple as _canon
from ui.widgets.friendly_error import show_error

_HIDDEN_COLS = {"globalid", "sourcetrialid"}  # SourceTrialID: Nutzerwunsch "verwirrt nur"
_AUDIT_COLS = {"createdby", "creationdate"}
# Nutzerwunsch: "benenn das feld doch bitte Colour und nicht ColourID in der
# ui" - der DB-Spaltenname bleibt ColourID (FK-Konvention wie Garntyp/
# Material/YarnGroupID), nur die Anzeige wird hier freundlicher.
_DISPLAY_LABEL_OVERRIDES = {"colourid": "Colour"}
_ADD_NEW_COLOUR_LABEL = "+ Add new colour…"


class NewYarnScreen(QWidget):
    """Dynamisches Zwei-Spalten-Formular für einen einzelnen Yarn-Datensatz."""

    def __init__(
        self,
        columns: List[str],
        fk_maps: Dict[str, Dict],
        id_column: str = "ID",
        on_back_home: Optional[Callable[[], None]] = None,
        on_save: Optional[Callable[[Dict], int]] = None,
        on_created: Optional[Callable[[int], None]] = None,
        on_quick_add_colour: Optional[Callable[[QWidget], Optional[tuple]]] = None,
        sidebar_callbacks: Optional[dict] = None,
    ):
        super().__init__()
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None
        self.columns = columns or []
        self.fk_maps = fk_maps or {}
        self.id_column = id_column or "ID"
        self.on_back_home = on_back_home
        self._on_save = on_save
        self._on_created = on_created
        # Nur für die colourid-Spalte verdrahtet (siehe _create_editor_for_column)
        # - reine DB-Logik lebt in ui.screen_manage_yarn.quick_add_colour(),
        # dieser Screen bleibt bewusst business-logic-frei/dumb.
        self._on_quick_add_colour = on_quick_add_colour

        # Spaltenname -> Editor-Widget (dpf/createdby/creationdate sind NICHT
        # enthalten, siehe unten - reine Anzeige-Labels, nie im Save-Payload)
        self._editors: Dict[str, QWidget] = {}
        self._minstock_col: Optional[str] = None
        self._minstock_locked = False
        self._dpf_col: Optional[str] = None
        self._endtiter_col: Optional[str] = None
        self._filaments_col: Optional[str] = None
        self._dpf_label: Optional[QLabel] = None
        self._createdby_col: Optional[str] = None
        self._creationdate_col: Optional[str] = None
        self._createdby_label: Optional[QLabel] = None
        self._creationdate_label: Optional[QLabel] = None
        # (title_label, value_label) pairs, toggled together by set_audit_fields_visible()
        self._audit_rows: List[tuple] = []

        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring). Die frühere
        # "kein Home-Button"-Begründung betraf nur den TopBar-Home-Button -
        # Cancel/Save bleiben weiterhin der primäre Navigationsweg aus diesem
        # Formular heraus.
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        center = QWidget()

        main_layout = QHBoxLayout(center)
        main_layout.setContentsMargins(32, 24, 32, 24)
        main_layout.setSpacing(32)

        left_widget = QWidget()
        right_widget = QWidget()
        left_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        right_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        left_form = QFormLayout(left_widget)
        right_form = QFormLayout(right_widget)
        for frm in (left_form, right_form):
            frm.setContentsMargins(0, 0, 0, 0)
            frm.setHorizontalSpacing(24)
            frm.setVerticalSpacing(10)

        main_layout.addWidget(left_widget, 1)
        main_layout.addWidget(right_widget, 1)

        visible_cols = [col for col in self.columns if _canon(col) not in _HIDDEN_COLS]
        total = len(visible_cols)
        split = (total + 1) // 2

        # DPF-Zuträger-Spalten identifizieren (gleiche Heuristik wie YarnTableModel)
        for h in self.columns:
            k = _canon(h).replace('(', '').replace(')', '')
            if self._dpf_col is None and k in {'dpfdtex', 'dpf'}:
                self._dpf_col = h
            if self._endtiter_col is None and k in {'endtiterdtex', 'endtiter'}:
                self._endtiter_col = h
            if self._filaments_col is None and k in {'numberoffilaments', 'filaments', 'nofilaments'}:
                self._filaments_col = h
            if self._createdby_col is None and k == 'createdby':
                self._createdby_col = h
            if self._creationdate_col is None and k == 'creationdate':
                self._creationdate_col = h

        for i, col in enumerate(visible_cols):
            target_form = left_form if i < split else right_form
            label_text = _DISPLAY_LABEL_OVERRIDES.get(_canon(col), col)
            if col.lower() == self.id_column.lower():
                lbl = QLabel("Wird automatisch vergeben")
                lbl.setStyleSheet("color: #666666; font-style: italic;")
                target_form.addRow(QLabel(label_text + ":"), lbl)
                continue
            if self._dpf_col and col == self._dpf_col:
                # Rein berechnet (Endtiter/NumberOfFilaments) - nie editierbar,
                # nie zurückgeschrieben, siehe _collect_values().
                self._dpf_label = QLabel("")
                self._dpf_label.setStyleSheet("color: #666666; font-style: italic;")
                target_form.addRow(QLabel(label_text + ":"), self._dpf_label)
                continue
            if _canon(col) in _AUDIT_COLS:
                # Wer/wann angelegt wurde: reine Anzeige, nie editierbar, nie im
                # Save-Payload. Zeile nur für Superuser sichtbar (set_audit_fields_visible),
                # per Default versteckt, siehe __init__/_build_ui-Ende.
                value_lbl = QLabel("")
                value_lbl.setStyleSheet("color: #666666; font-style: italic;")
                title_lbl = QLabel(label_text + ":")
                target_form.addRow(title_lbl, value_lbl)
                self._audit_rows.append((title_lbl, value_lbl))
                if col == self._createdby_col:
                    self._createdby_label = value_lbl
                else:
                    self._creationdate_label = value_lbl
                continue
            widget = self._create_editor_for_column(col)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self._editors[col] = widget
            if _canon(col) == "minstock":
                self._minstock_col = col
            target_form.addRow(QLabel(label_text + ":"), widget)

        # DPF live nachführen, wenn Endtiter/NumberOfFilaments getippt werden
        if self._dpf_label is not None:
            for dep_col in (self._endtiter_col, self._filaments_col):
                dep_widget = self._editors.get(dep_col) if dep_col else None
                if isinstance(dep_widget, QLineEdit):
                    dep_widget.textChanged.connect(self._recompute_dpf_label)

        # Per Default versteckt - main.py blendet sie für Superuser gezielt
        # wieder ein (set_audit_fields_visible), siehe _go_edit_yarn_form.
        self.set_audit_fields_visible(False)

        scroll.setWidget(center)
        content_layout.addWidget(scroll, 1)

        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(32, 0, 32, 8)
        btn_layout.setSpacing(12)
        btn_layout.addStretch(1)
        self.btn_cancel = QPushButton("Cancel", objectName="GreyBtn")
        self.btn_cancel.clicked.connect(self._go_home)
        btn_layout.addWidget(self.btn_cancel)
        self.btn_save = QPushButton("Save Changes", objectName="GreenBtn")
        self.btn_save.clicked.connect(self._on_click_save)
        btn_layout.addWidget(self.btn_save)

        content_layout.addWidget(btn_frame, 0)
        root.addWidget(FooterBar(), 0)

    def _refresh_sidebar(self):
        """Baut die Sidebar-Navigation neu auf, falls sich der Access-Level
        seit dem letzten Aufbau geändert hat, sonst nur die Badges (siehe
        ui/widgets/sidebar_nav.py::refresh_lazy_sidebar())."""
        import app_meta
        try:
            level = int((app_meta.current_user or {}).get("access_level") or 0)
        except Exception:
            level = 0
        sidebar_nav.refresh_lazy_sidebar(self, level)

    def showEvent(self, event):
        try:
            self._refresh_sidebar()
        except Exception:
            pass
        super().showEvent(event)

    def _create_editor_for_column(self, col: str) -> QWidget:
        key = _canon(col)
        fk = self.fk_maps.get(key)
        if fk:
            combo = QComboBox()
            combo.addItem("")
            combo.addItems(list(fk.get("name_to_id", {}).keys()))
            combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            if key == "colourid" and self._on_quick_add_colour:
                self._wire_quick_add_colour(combo, fk)
            return combo

        edit = QLineEdit()
        edit.setClearButtonEnabled(True)
        edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return edit

    def _wire_quick_add_colour(self, combo: QComboBox, fk: Dict):
        """Hängt "+ Add new colour…" ans Ende der Colour-Combo (Nutzerwunsch:
        "wie kann ich das schnell hinzufügen, ohne dass ich alles was ich
        bereits beim Garn eingegeben habe wieder löschen muss?"). Der Dialog
        (self._on_quick_add_colour, verdrahtet auf
        ui.screen_manage_yarn.quick_add_colour über main.py) läuft SYNCHRON im
        `activated`-Handler - andere bereits ausgefüllte Felder dieses
        Formulars bleiben dabei komplett unangetastet, kein Navigieren weg
        von dieser Seite nötig."""
        combo.addItem(_ADD_NEW_COLOUR_LABEL)
        state = {"last_good": combo.currentIndex()}

        def _on_activated(idx, combo=combo, state=state):
            if combo.itemText(idx) != _ADD_NEW_COLOUR_LABEL:
                state["last_good"] = idx
                return
            result = self._on_quick_add_colour(combo)
            if not result:
                combo.setCurrentIndex(state["last_good"])
                return
            new_id, new_name = result
            name_to_id = fk.setdefault("name_to_id", {})
            fk.setdefault("id_to_name", {})[new_id] = new_name
            name_to_id[str(new_name)] = new_id
            existing_idx = combo.findText(str(new_name))
            if existing_idx >= 0 and existing_idx != combo.count() - 1:
                combo.setCurrentIndex(existing_idx)
                state["last_good"] = existing_idx
            else:
                insert_pos = combo.count() - 1  # vor dem Sentinel-Eintrag
                combo.insertItem(insert_pos, str(new_name))
                combo.setCurrentIndex(insert_pos)
                state["last_good"] = insert_pos

        combo.activated.connect(_on_activated)

    def _recompute_dpf_label(self, *_args):
        if self._dpf_label is None:
            return
        endt_widget = self._editors.get(self._endtiter_col) if self._endtiter_col else None
        fil_widget = self._editors.get(self._filaments_col) if self._filaments_col else None
        try:
            endt = float(endt_widget.text().strip().replace(",", ".")) if endt_widget else None
            fils = float(fil_widget.text().strip().replace(",", ".")) if fil_widget else None
            if not endt or not fils:
                self._dpf_label.setText("")
                return
            self._dpf_label.setText(f"{endt / fils:.3f}")
        except Exception:
            self._dpf_label.setText("")

    # --- Public helpers for MainWindow ---
    def load_from_row(self, row: Dict[str, object]):
        """Befüllt das Formular mit Werten aus row (ID/GlobalID werden ignoriert)."""
        for col, widget in self._editors.items():
            if col.lower() == self.id_column.lower():
                continue

            value = row.get(col)
            key = _canon(col)
            fk = self.fk_maps.get(key)

            if isinstance(widget, QComboBox):
                name = None
                if fk:
                    id_to_name = fk.get("id_to_name", {})
                    name = id_to_name.get(value)
                    if name is None and value is not None:
                        try:
                            iv = int(str(value))
                            name = id_to_name.get(iv) or id_to_name.get(str(iv))
                        except Exception:
                            name = id_to_name.get(str(value))
                if name is None:
                    name = ""
                idx = widget.findText(str(name))
                if idx < 0 and name:
                    widget.addItem(str(name))
                    idx = widget.count() - 1
                widget.setCurrentIndex(idx if idx >= 0 else (0 if widget.count() > 0 else -1))

            elif isinstance(widget, QLineEdit):
                widget.setText("" if value is None else str(value))

        self._recompute_dpf_label()

        if self._createdby_label is not None and self._createdby_col:
            val = row.get(self._createdby_col)
            fk = self.fk_maps.get("createdby", {})
            name = fk.get("id_to_name", {}).get(val)
            if name is None and val is not None:
                name = fk.get("id_to_name", {}).get(str(val))
            self._createdby_label.setText("" if name is None else str(name))
        if self._creationdate_label is not None and self._creationdate_col:
            val = row.get(self._creationdate_col)
            self._creationdate_label.setText("" if val is None else str(val))

    def set_audit_fields_visible(self, visible: bool):
        """Zeigt/versteckt die "Created by"/"Creation date"-Zeilen - nur für
        Superuser gedacht (per explizitem Nutzerwunsch), reine Anzeige, nie
        editierbar. Von main.py bei jeder Navigation zu diesem Screen mit dem
        aktuellen Permission-Stand aufgerufen."""
        for title_lbl, value_lbl in self._audit_rows:
            title_lbl.setVisible(visible)
            value_lbl.setVisible(visible)

    def set_minstock_locked(self, locked: bool):
        """Sperrt/entsperrt nur das MinStock-Feld - der Rest des Formulars bleibt
        editierbar. AdminBox=0-User dürfen laut Anforderung alles ausser MinStock
        (und Löschen, siehe ManageYarnScreen) bearbeiten."""
        self._minstock_locked = bool(locked)
        widget = self._editors.get(self._minstock_col) if self._minstock_col else None
        if widget is not None:
            widget.setEnabled(not self._minstock_locked)
            widget.setToolTip(
                "Read-only access – you don't have permission to edit MinStock."
                if self._minstock_locked else "")

    def _go_home(self):
        if callable(self.on_back_home):
            self.on_back_home()

    def _collect_values(self) -> Dict[str, object]:
        data: Dict[str, object] = {}
        for col, widget in self._editors.items():
            if col.lower() == self.id_column.lower():
                continue
            key = _canon(col)
            fk = self.fk_maps.get(key)

            if isinstance(widget, QComboBox):
                name = widget.currentText()
                data[col] = fk["name_to_id"].get(name) if fk else name
            elif isinstance(widget, QLineEdit):
                txt = widget.text().strip()
                data[col] = txt if txt != "" else None
            else:
                data[col] = None
        return data

    def _on_click_save(self):
        if not callable(self._on_save):
            QMessageBox.warning(self, "Yarn", "No save callback configured.")
            return

        data = self._collect_values()
        # MinStock nie mitsenden, wenn gesperrt - Defense-in-depth, das Feld ist
        # zwar schon deaktiviert (kein User-Edit möglich), aber so bleibt der
        # ursprüngliche DB-Wert garantiert unangetastet statt nur "unverändert
        # zurückgeschrieben".
        if self._minstock_locked and self._minstock_col:
            data.pop(self._minstock_col, None)

        try:
            new_id = self._on_save(data)
        except Exception as e:
            show_error(self, "Yarn", "The yarn could not be saved.", e)
            return

        if new_id is None:
            # on_save() signals "don't save, stay here" this way - z.B. wenn
            # der Nutzer eine Duplicate-Yarn-Warnung mit "No" abgelehnt hat
            # (siehe main.py._go_edit_yarn_form._update_save). Kein Fehler,
            # keine Navigation - das Formular bleibt einfach offen.
            return

        if callable(self._on_created):
            try:
                self._on_created(new_id)
                return
            except Exception:
                pass
