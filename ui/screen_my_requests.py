from __future__ import annotations

# ui/screen_my_requests.py
"""Screen zur Anzeige eigener Experiment-Requests (MyRequestsScreen).

Zeigt alle ExperimentRequests des aktuell eingeloggten Benutzers in einer
Tabelle an. Unterstützt:
  - Filtern nach Status (offen, genehmigt, abgelehnt usw.)
  - Öffnen eines Requests (Doppelklick / Button) → navigiert zum Experiment
  - Statusänderung (z.B. Zurückziehen)
  - Anzeige der verknüpften Experiment-ID (aus tblExperimente via Join)

Datenbankbezug:
  - Haupttabelle: tblExperimentRequests
  - Status-Lookup: tblExperimentRequestStatus
  - Experiment-Verknüpfung: tblExperimente.ExperimentRequestID (oder umgekehrt)
"""

# ui/screen_my_requests.py

from typing import Any, Callable, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QSizePolicy,
    QSpacerItem,
    QMessageBox,
    QComboBox,
    QLineEdit,
    QMenu,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QInputDialog,
)

import app_meta
from db import experiment_request_changes as request_changes
from db import experiment_requests as er
from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from ui.widgets.experiment_request_help_dialog import show_experiment_request_help
from ui.widgets.friendly_error import show_error


class NoScrollComboBox(QComboBox):
    """QComboBox, die Mausrad-Events ignoriert.

    Verhindert, dass ein Scroll ueber der Tabelle (Cursor zufaellig ueber
    der Combo) versehentlich den RequestStatus aendert. Das Wheel-Event
    wird an das darunterliegende Widget (die Tabelle) weitergereicht,
    sodass normales Scrollen weiterhin funktioniert. Klick/Dropdown bleibt
    unveraendert bedienbar.
    """

    def wheelEvent(self, event):
        event.ignore()


class MyRequestsScreen(QWidget):
    """Zeigt alle Experiment Requests des aktuell eingeloggten Users.

    Doppelklick auf eine Zeile soll auf den Create/Edit-Screen weiterleiten.
    Die Weiterleitung erfolgt ueber einen Callback (Navigator) oder – falls nicht
    uebergeben – ueber eine Methodensuche am Main Window.
    """

    # Lange Freitext-Spalten, die standardmaessig ausgeblendet sind (Toggle
    # "Show details", siehe _apply_detail_column_visibility()) - die Tabelle
    # zeigt initial nur die "Kernspalten" (Titel/Status/Projekt/Owner/
    # Wunschtermin/Experiment ID), Volltext bleibt weiterhin per Doppelklick
    # (Edit-Screen) einsehbar.
    _DETAIL_COLUMN_NAMES = er.LIST_DETAIL_COLUMNS

    def __init__(self, on_back_home=None,
                 on_open_request: Optional[Callable[[Any], None]] = None, on_open_experiment=None,
                 sidebar_callbacks: Optional[dict] = None):
        super().__init__()
        self.on_back_home = on_back_home
        self.on_open_request = on_open_request
        self.on_open_experiment = on_open_experiment
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None

        self._table_name = "tblExperimentRequests"
        self._user_id: Optional[Any] = None

        self._tbl: Optional[QTableWidget] = None
        self._lbl_info: Optional[QLabel] = None

        # Dropdown-Choices fuer RequestStatus (tblRequestStatus)
        # Liste von (id, label)
        self._status_choices: List[Tuple[Any, str]] = []
        self._is_superuser: bool = False
        # {OriginalRequestID: PendingCopyID} - siehe db/experiment_request_changes.py.
        # Kopie-Zeilen selbst tauchen nie als eigene Tabellenzeile auf (refresh()
        # filtert sie per ChangeOfRequestID IS NULL raus), sondern nur als
        # Markierung auf ihrem Original.
        self._pending_copy_map: dict = {}

        # Filter-Leiste (siehe _build_filter_row()/_apply_filters()) - reines
        # Client-Side-Filtern (setRowHidden) auf der bereits geladenen Tabelle,
        # kein erneuter DB-Roundtrip pro Filteränderung.
        self._filter_search: Optional[QLineEdit] = None
        self._filter_status: Optional[QComboBox] = None
        self._filter_project: Optional[QComboBox] = None
        self._filter_owner: Optional[QComboBox] = None

        # Detail-Spalten-Toggle (siehe _DETAIL_COLUMN_NAMES oben).
        self._show_detail_columns: bool = False
        self._detail_col_indices: List[int] = []
        self._btn_toggle_details: Optional[QPushButton] = None

        self._build_ui()

    # ---------------- Lookups ----------------

    def _load_status_choices(self) -> List[Tuple[Any, str]]:
        """Lädt Status-Choices aus tblRequestStatus, sortiert nach RequestOrder."""
        return er.load_status_choices()

    def _update_request_status(
        self, request_id: Any, new_status_id: Any, denial_reason: Optional[str] = None
    ) -> bool:
        """Aktualisiert den Status eines Requests in der DB
        (db/experiment_requests.update_request_status - ein Wechsel weg von
        "Denied" löscht einen alten Grund mit).

        Returns:
            True bei Erfolg, False bei Fehler.
        """
        try:
            er.update_request_status(request_id, new_status_id, denial_reason=denial_reason)
            return True
        except Exception as e:
            QMessageBox.critical(self, "DB Error", str(e))
            return False

    def _notify_owner(self, owner_id: Optional[Any], request_id: Any, message: str) -> None:
        """Benachrichtigt den Request-Besitzer (best-effort, keine Selbst-
        Benachrichtigung), siehe db/experiment_requests.notify_owner."""
        er.notify_owner(getattr(app_meta, "current_user", {}) or {}, owner_id, request_id, message)

    def _notify_owner_status_changed(
        self, owner_id: Optional[Any], request_id: Any, titel: str, new_status_label: str
    ) -> None:
        er.notify_owner_status_changed(getattr(app_meta, "current_user", {}) or {},
                                       owner_id, request_id, titel, new_status_label)

    def _notify_owner_of_request(self, request_id: Any, message: str) -> None:
        """Wie _notify_owner(), aber holt CreatedBy/Titel selbst per ID nach."""
        er.notify_owner_of_request(getattr(app_meta, "current_user", {}) or {}, request_id, message)

    def set_user(self, user_id: Optional[Any]):
        """Setzt die Benutzer-ID für die Filterung und lädt die Daten neu.

        Muss aufgerufen werden bevor der Screen angezeigt wird.
        """
        self._user_id = user_id

    def _resolve_experiment_request_field(self) -> Optional[str]:
        """Findet das Feld in tblExperimente, das auf einen Experiment Request (ID) verweist."""
        return er.resolve_experiment_request_field()

    def _prefetch_experiment_ids_for_requests(self, request_ids: List[Any]) -> dict:
        """Liefert {RequestID: ExperimentID} für gegebene RequestIDs."""
        return er.experiment_ids_for_requests(request_ids)

    # ---------------- Data ----------------

    def refresh(self):
        """Lädt alle eigenen Requests neu aus der DB und aktualisiert die Tabelle."""
        """Neu laden (fuer den aktuell gesetzten User)."""
        if self._tbl is None or self._lbl_info is None:
            return

        uid = self._user_id
        if uid in (None, ""):
            # Fallback: global current_user
            try:
                uid = (getattr(app_meta, "current_user", {}) or {}).get("id")
            except Exception:
                uid = None

        if uid in (None, ""):
            self._lbl_info.setText("No user logged in – no requests available.")
            self._tbl.setRowCount(0)
            self._tbl.setColumnCount(0)
            return

        # Superuser: darf Status aendern UND sieht alle Requests.
        # Nicht-Superuser: sieht nur die eigenen Requests.
        self._is_superuser = bool(getattr(app_meta, "is_superuser_level", lambda: False)())

        # Status-Choices laden (auch fuer Nicht-Superuser, damit Combo den Text anzeigen kann)
        self._status_choices = self._load_status_choices()

        try:
            # Query (copies/archived versions excluded, normal users only their
            # own rows): db/experiment_requests.fetch_request_rows()
            rows, col_names = er.fetch_request_rows(uid, self._is_superuser)
        except Exception as e:
            QMessageBox.critical(self, "DB Error", str(e))
            self._lbl_info.setText("Error while loading.")
            self._tbl.setRowCount(0)
            self._tbl.setColumnCount(0)
            return

        self._rebuild_filter_options(rows, col_names)

        # DenialReason wird nicht als eigene Spalte gezeigt (siehe Tooltip auf
        # der Status-Combo weiter unten) - er.list_columns().
        visible_cols: List[Tuple[int, str]] = er.list_columns(col_names, self._is_superuser)

        self._tbl.setSortingEnabled(False)
        self._tbl.clear()
        # +1 für die zusätzliche UI-Spalte
        self._tbl.setColumnCount(len(visible_cols) + 1)

        header_labels: List[str] = [er.list_header_label(name) for _, name in visible_cols]
        header_labels.append("Experiment ID")
        self._tbl.setHorizontalHeaderLabels(header_labels)

        self._detail_col_indices = [
            i for i, lbl in enumerate(header_labels) if lbl in self._DETAIL_COLUMN_NAMES
        ]
        self._apply_detail_column_visibility()
        self._tbl.setRowCount(len(rows))

        # Indizes ermitteln
        _ix = er.list_column_indices(col_names)
        id_idx: Optional[int] = _ix["id"]
        rs_idx: Optional[int] = _ix["requeststatus"]
        cb_idx: Optional[int] = _ix["createdby"]
        titel_idx: Optional[int] = _ix["titel"]
        dr_idx: Optional[int] = _ix["denialreason"]

        # ExperimentIDs für Status=4 vorladen
        exp_map: dict = {}
        if id_idx is not None and rs_idx is not None:
            try:
                completed_req_ids = [
                    row[id_idx] for row in rows
                    if row[rs_idx] == 4 and row[id_idx] not in (None, "")
                ]
                exp_map = self._prefetch_experiment_ids_for_requests(completed_req_ids)
            except Exception:
                exp_map = {}

        # Offene Aenderungs-Kopien vorladen (Original-ID -> Kopie-ID), damit
        # betroffene Zeilen unten markiert und im Kontextmenue akzeptiert/
        # abgelehnt werden koennen. Siehe db/experiment_request_changes.py.
        self._pending_copy_map = {}
        if id_idx is not None:
            try:
                all_req_ids = [row[id_idx] for row in rows if row[id_idx] not in (None, "")]
                self._pending_copy_map = request_changes.get_pending_change_ids(all_req_ids)
            except Exception:
                self._pending_copy_map = {}

        pending_bg = QColor("#fff3cd")
        # Brandneue, noch nie geprueften Requests (Status "Request", keine
        # Aenderungs-Kopie) bekommen ihre eigene Hervorhebung (Nutzerwunsch
        # 2026-09-08: sowohl neue Requests als auch offene Aenderungen sollen
        # im Badge zaehlen UND in der Tabelle sichtbar sein - mit
        # unterschiedlichem Symbol/Farbe, damit man beide Faelle auseinanderhalten
        # kann. "⏳" (Aenderung wartet) bleibt unveraendert, neue Requests
        # bekommen "🆕" + eigene Hintergrundfarbe).
        new_bg = QColor("#dceeff")

        for r, row in enumerate(rows):
            req_id = row[id_idx] if id_idx is not None else None
            current_status_id = row[rs_idx] if rs_idx is not None else None
            has_pending_change = req_id in self._pending_copy_map
            is_new_unreviewed = er.is_new_unreviewed(current_status_id, has_pending_change)
            owner_id = row[cb_idx] if cb_idx is not None else None
            titel_val = str(row[titel_idx] or "") if titel_idx is not None else ""
            denial_reason_val = row[dr_idx] if dr_idx is not None else None

            for c_vis, (c_src, _col_name) in enumerate(visible_cols):
                # RequestStatus als Dropdown
                if rs_idx is not None and c_src == rs_idx:
                    item = QTableWidgetItem("")
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    if has_pending_change:
                        item.setData(Qt.BackgroundRole, pending_bg)
                    elif is_new_unreviewed:
                        item.setData(Qt.BackgroundRole, new_bg)
                    if c_vis == 0:
                        item.setData(Qt.UserRole, req_id)
                    self._tbl.setItem(r, c_vis, item)

                    combo = NoScrollComboBox()
                    combo.setMinimumHeight(24)
                    combo_border = (
                        "#e0a800" if has_pending_change
                        else "#4a90d9" if is_new_unreviewed
                        else "#8fbf8f"
                    )
                    combo.setStyleSheet(
                        f"QComboBox {{ background: #ffffff; border: 1px solid {combo_border}; padding: 2px 6px; }}"
                        "QComboBox QAbstractItemView { background: #ffffff; }"
                    )
                    _tooltip = er.status_tooltip(current_status_id, has_pending_change,
                                                 is_new_unreviewed, denial_reason_val)
                    if _tooltip:
                        combo.setToolTip(_tooltip)
                    # Superuser soll Status ändern dürfen, aber nicht auf "leer" und nicht auf
                    # "Experiment" (nur angezeigt, wenn aktuell) - er.status_options().
                    # Nicht-Superuser: Combo bleibt deaktiviert, darf aber den aktuellen Text anzeigen.
                    for lbl, _id, _selectable in er.status_options(
                            self._status_choices, current_status_id, self._is_superuser):
                        combo.addItem(lbl, _id)
                        if not _selectable:
                            try:
                                combo.model().item(combo.count() - 1).setEnabled(False)
                            except Exception:
                                pass

                    combo.blockSignals(True)
                    if current_status_id is None:
                        combo.setCurrentIndex(0)
                    else:
                        idx = combo.findData(current_status_id)
                        combo.setCurrentIndex(idx if idx >= 0 else 0)
                    combo.blockSignals(False)

                    combo.setEnabled(bool(self._is_superuser))

                    if self._is_superuser:
                        _state = {"old_id": current_status_id}

                        def _label_for_status_id(_sid: Any) -> str:
                            return er.status_label(self._status_choices, _sid)

                        def _set_combo_to_status_id(_sid: Any, *, _cb: QComboBox) -> None:
                            _cb.blockSignals(True)
                            if _sid in (None, ""):
                                _cb.setCurrentIndex(0)
                            else:
                                _idx = _cb.findData(_sid)
                                _cb.setCurrentIndex(_idx if _idx >= 0 else 0)
                            _cb.blockSignals(False)

                        def _on_status_changed(
                            _index: int, *, _req_id=req_id, _cb=combo,
                            _owner_id=owner_id, _titel=titel_val,
                        ):
                            new_id = _cb.currentData()
                            old_id = _state["old_id"]

                            # Regel: db/experiment_requests.check_status_change() -
                            # nicht erlaubt: leer / None / "Experiment"; "Fehlklick"-
                            # Schutz (2026-08-27): Wechsel auf "Denied" braucht einen
                            # Grund, Approved/Experiment -> "Request" eine Bestaetigung.
                            verdict, new_label = er.check_status_change(self._status_choices, old_id, new_id)
                            if verdict == "invalid":
                                _set_combo_to_status_id(old_id, _cb=_cb)
                                return
                            if verdict == "same":
                                return

                            denial_reason = None
                            if verdict == "needs_reason":
                                text, ok = QInputDialog.getMultiLineText(
                                    self,
                                    "Deny request",
                                    f"Reason for denying request #{_req_id} "
                                    "(visible to the requester):",
                                )
                                if not ok or not text.strip():
                                    _set_combo_to_status_id(old_id, _cb=_cb)
                                    return
                                denial_reason = text.strip()
                            elif verdict == "needs_confirmation":
                                old_label = _label_for_status_id(old_id).strip()
                                reply = QMessageBox.question(
                                    self,
                                    "Confirm status change",
                                    er.confirm_back_to_request_text(_req_id, old_label),
                                    QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No,
                                )
                                if reply != QMessageBox.Yes:
                                    _set_combo_to_status_id(old_id, _cb=_cb)
                                    return

                            if self._update_request_status(_req_id, new_id, denial_reason=denial_reason):
                                _state["old_id"] = new_id
                                self._notify_owner_status_changed(_owner_id, _req_id, _titel, new_label)
                            else:
                                _set_combo_to_status_id(old_id, _cb=_cb)

                        combo.currentIndexChanged.connect(_on_status_changed)

                    self._tbl.setCellWidget(r, c_vis, combo)
                    continue

                val = er.format_list_value(_col_name, row[c_src])
                display_val = "" if val is None else str(val)
                if str(_col_name).strip().lower() == "titel":
                    display_val = er.title_marker(has_pending_change, is_new_unreviewed) + display_val
                item = QTableWidgetItem(display_val)

                # Titel-Spalte gruen + fett darstellen
                if str(_col_name).strip().lower() == "titel":
                    item.setData(Qt.ForegroundRole, QColor("#39A650"))

                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)

                if has_pending_change:
                    item.setData(Qt.BackgroundRole, pending_bg)
                    item.setToolTip(er.PENDING_TOOLTIP)
                elif is_new_unreviewed:
                    item.setData(Qt.BackgroundRole, new_bg)
                    item.setToolTip(er.NEW_TOOLTIP)

                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if c_vis == 0:
                    item.setData(Qt.UserRole, req_id)
                self._tbl.setItem(r, c_vis, item)

            # Zusätzliche Spalte: Experiment ID
            exp_id = ""
            if current_status_id == 4 and req_id not in (None, ""):
                exp_id = exp_map.get(req_id, "") or ""
            exp_item = QTableWidgetItem(str(exp_id))
            exp_item.setFlags(exp_item.flags() & ~Qt.ItemIsEditable)
            if exp_id:
                exp_item.setForeground(QColor("#1a6fc4"))
                exp_item.setData(Qt.UserRole, exp_id)
                font = exp_item.font()
                font.setUnderline(True)
                exp_item.setFont(font)
            self._tbl.setItem(r, len(visible_cols), exp_item)

        self._tbl.resizeColumnsToContents()
        self._tbl.resizeRowsToContents()
        self._tbl.setSortingEnabled(True)

        uname = (getattr(app_meta, "current_user", {}) or {}).get("username") or ""
        if self._is_superuser:
            self._lbl_info.setText(f"{len(rows)} request(s) (superuser view: all)")
        else:
            self._lbl_info.setText(f"{len(rows)} Request(s) fuer {uname}")

        self._apply_filters()

    # ---------------- Filter ----------------

    def _build_filter_row(self) -> QHBoxLayout:
        """Baut die Filter-Toolbar (Suche/Status/Projekt/Owner) über der Tabelle.

        Rein client-seitig (setRowHidden), siehe _apply_filters() - kein
        erneuter DB-Roundtrip pro Filteränderung."""
        row = QHBoxLayout()
        row.setSpacing(8)

        self._filter_search = QLineEdit()
        self._filter_search.setPlaceholderText("Search…")
        self._filter_search.setClearButtonEnabled(True)
        self._filter_search.setMinimumWidth(200)
        self._filter_search.textChanged.connect(self._apply_filters)
        row.addWidget(self._filter_search, 1)

        self._filter_status = NoScrollComboBox()
        self._filter_status.setMinimumWidth(140)
        self._filter_status.addItem("All statuses", None)
        self._filter_status.currentIndexChanged.connect(self._apply_filters)
        row.addWidget(self._filter_status, 0)

        self._filter_project = NoScrollComboBox()
        self._filter_project.setMinimumWidth(160)
        self._filter_project.addItem("All projects", None)
        self._filter_project.currentIndexChanged.connect(self._apply_filters)
        row.addWidget(self._filter_project, 0)

        self._filter_owner = NoScrollComboBox()
        self._filter_owner.setMinimumWidth(140)
        self._filter_owner.addItem("All owners", None)
        self._filter_owner.currentIndexChanged.connect(self._apply_filters)
        self._filter_owner.setVisible(False)  # nur fuer Superuser, siehe refresh()
        row.addWidget(self._filter_owner, 0)

        btn_reset = QPushButton("Reset filters")
        btn_reset.setObjectName("GreyBtn")
        btn_reset.clicked.connect(self._reset_filters)
        row.addWidget(btn_reset, 0)

        return row

    def _reset_filters(self) -> None:
        if self._filter_search is not None:
            self._filter_search.blockSignals(True)
            self._filter_search.clear()
            self._filter_search.blockSignals(False)
        for combo in (self._filter_status, self._filter_project, self._filter_owner):
            if combo is not None:
                combo.blockSignals(True)
                combo.setCurrentIndex(0)
                combo.blockSignals(False)
        self._apply_filters()

    def _rebuild_filter_options(self, rows: List[Any], col_names: List[str]) -> None:
        """Fuellt Status-/Projekt-/Owner-Filter mit den in `rows` tatsaechlich
        vorkommenden Werten, unter Beibehaltung der aktuellen Auswahl (falls
        der Wert nach dem Reload noch vorkommt)."""

        def _col_index(name: str) -> Optional[int]:
            try:
                return col_names.index(name)
            except ValueError:
                return None

        # --- Status ---
        if self._filter_status is not None:
            prev_data = self._filter_status.currentData()
            self._filter_status.blockSignals(True)
            self._filter_status.clear()
            self._filter_status.addItem("All statuses", None)
            for _id, label in self._status_choices:
                self._filter_status.addItem("" if label is None else str(label), _id)
            idx = self._filter_status.findData(prev_data) if prev_data is not None else 0
            self._filter_status.setCurrentIndex(idx if idx >= 0 else 0)
            self._filter_status.blockSignals(False)

        # --- Projekt ---
        proj_idx = _col_index("ProjektText")
        if self._filter_project is not None:
            prev_text = self._filter_project.currentText()
            values = set()
            if proj_idx is not None:
                for row in rows:
                    v = row[proj_idx]
                    if v not in (None, ""):
                        values.add(str(v))
            self._filter_project.blockSignals(True)
            self._filter_project.clear()
            self._filter_project.addItem("All projects", None)
            for v in sorted(values):
                self._filter_project.addItem(v, v)
            new_idx = self._filter_project.findText(prev_text)
            self._filter_project.setCurrentIndex(new_idx if new_idx >= 0 else 0)
            self._filter_project.blockSignals(False)

        # --- Owner (nur Superuser-Ansicht) ---
        owner_idx = _col_index("CreatedByUser")
        if self._filter_owner is not None:
            self._filter_owner.setVisible(self._is_superuser)
            prev_text = self._filter_owner.currentText()
            values = set()
            if owner_idx is not None:
                for row in rows:
                    v = row[owner_idx]
                    if v not in (None, ""):
                        values.add(str(v))
            self._filter_owner.blockSignals(True)
            self._filter_owner.clear()
            self._filter_owner.addItem("All owners", None)
            for v in sorted(values):
                self._filter_owner.addItem(v, v)
            new_idx = self._filter_owner.findText(prev_text)
            self._filter_owner.setCurrentIndex(new_idx if new_idx >= 0 else 0)
            self._filter_owner.blockSignals(False)

    def _toggle_detail_columns(self) -> None:
        self._show_detail_columns = not self._show_detail_columns
        if self._btn_toggle_details is not None:
            self._btn_toggle_details.setText(
                "Hide details" if self._show_detail_columns else "Show details"
            )
        self._apply_detail_column_visibility()

    def _apply_detail_column_visibility(self) -> None:
        """Blendet die langen Freitext-Spalten (_DETAIL_COLUMN_NAMES) je nach
        Toggle-Zustand ein/aus. Reine Spalten-Sichtbarkeit (setColumnHidden) -
        Filter/Suche arbeiten weiterhin ueber alle Spalten, auch versteckte."""
        if self._tbl is None:
            return
        for c in self._detail_col_indices:
            self._tbl.setColumnHidden(c, not self._show_detail_columns)

    def _apply_filters(self) -> None:
        """Blendet Tabellenzeilen ein/aus, ohne die DB erneut zu befragen."""
        if self._tbl is None:
            return

        search_text = self._filter_search.text().strip().lower() if self._filter_search else ""
        status_id = self._filter_status.currentData() if self._filter_status else None
        project_val = self._filter_project.currentData() if self._filter_project else None
        owner_val = (
            self._filter_owner.currentData()
            if (self._filter_owner is not None and self._is_superuser)
            else None
        )

        col_count = self._tbl.columnCount()
        headers = [
            self._tbl.horizontalHeaderItem(c).text() if self._tbl.horizontalHeaderItem(c) else ""
            for c in range(col_count)
        ]
        status_col = headers.index("RequestStatus") if "RequestStatus" in headers else None
        project_col = headers.index("Projekt") if "Projekt" in headers else None
        owner_col = headers.index("Owner") if "Owner" in headers else None

        for r in range(self._tbl.rowCount()):
            visible = True

            if search_text:
                parts = []
                for c in range(col_count):
                    item = self._tbl.item(r, c)
                    if item is not None and item.text():
                        parts.append(item.text())
                if search_text not in " ".join(parts).lower():
                    visible = False

            if visible and status_id is not None and status_col is not None:
                widget = self._tbl.cellWidget(r, status_col)
                current = widget.currentData() if isinstance(widget, QComboBox) else None
                if current != status_id:
                    visible = False

            if visible and project_val is not None and project_col is not None:
                item = self._tbl.item(r, project_col)
                if item is None or item.text() != project_val:
                    visible = False

            if visible and owner_val is not None and owner_col is not None:
                item = self._tbl.item(r, owner_col)
                if item is None or item.text() != owner_val:
                    visible = False

            self._tbl.setRowHidden(r, not visible)

    # ---------------- UI ----------------

    def _build_ui(self):
        """Erstellt Header, Filter-Toolbar, Tabelle, Aktions-Buttons und Footer."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring). Der frühere
        # Header-Back-Button lebt als kontextueller Back-Chip weiter (gleiches
        # Muster wie ShowExperimentScreen), siehe top_row weiter unten.
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        center = QFrame()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(18, 14, 18, 14)
        center_layout.setSpacing(12)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 18, 24, 18)
        card_layout.setSpacing(12)

        top_row = QHBoxLayout()

        title = QLabel("Meine Experiment Requests")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        top_row.addWidget(title, 0, Qt.AlignLeft)

        # Kontext-Hilfe (Lebenszyklus-Diagramm), Nutzerwunsch 2026-08-31:
        # nicht dauerhaft sichtbar, nur ein kleiner Trigger daneben.
        self.btn_help = QPushButton("?")
        self.btn_help.setCursor(Qt.PointingHandCursor)
        self.btn_help.setFixedSize(26, 26)
        self.btn_help.setToolTip("Wie funktionieren Experiment Requests?")
        self.btn_help.setStyleSheet(
            "QPushButton{background:transparent;color:#39a650;border:1px solid #39a650;"
            "border-radius:13px;padding:0;font-size:14px;font-weight:700;}"
            "QPushButton:hover{background:#e8f5e9;}"
        )
        self.btn_help.clicked.connect(lambda: show_experiment_request_help(self))
        top_row.addWidget(self.btn_help, 0, Qt.AlignLeft)

        top_row.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self._btn_toggle_details = QPushButton("Show details")
        self._btn_toggle_details.setObjectName("GreyBtn")
        self._btn_toggle_details.setToolTip(
            "Show/hide the long free-text columns (Versuchsgrund, Aufgabe, …)."
        )
        self._btn_toggle_details.clicked.connect(self._toggle_detail_columns)
        top_row.addWidget(self._btn_toggle_details, 0, Qt.AlignRight)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setObjectName("GreyBtn")
        btn_refresh.clicked.connect(self.refresh)
        top_row.addWidget(btn_refresh, 0, Qt.AlignRight)
        card_layout.addLayout(top_row)

        card_layout.addLayout(self._build_filter_row())

        self._lbl_info = QLabel("")
        self._lbl_info.setStyleSheet("color: #666;")
        card_layout.addWidget(self._lbl_info)

        self._tbl = QTableWidget()
        self._tbl.setAlternatingRowColors(True)
        self._tbl.setSortingEnabled(True)
        self._tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self._tbl.setSelectionMode(QTableWidget.SingleSelection)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.horizontalHeader().setStretchLastSection(True)

        # Tabellenkopf fett darstellen
        hdr_font = self._tbl.horizontalHeader().font()
        hdr_font.setBold(True)
        self._tbl.horizontalHeader().setFont(hdr_font)

        self._tbl.cellDoubleClicked.connect(self._open_selected_request)
        self._tbl.cellClicked.connect(self._on_cell_clicked)
        self._tbl.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tbl.customContextMenuRequested.connect(self._on_context_menu)
        self._tbl.setMouseTracking(True)
        self._tbl.viewport().setMouseTracking(True)
        self._tbl.viewport().installEventFilter(self)
        card_layout.addWidget(self._tbl, 1)

        center_layout.addWidget(card, 1)
        content_layout.addWidget(center, 1)

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

    # ---------------- Navigation ----------------

    def _open_selected_request(self, row: int, col: int):
        """Öffnet den in Zeile row selektierten Request via on_open_request-Callback."""
        """Handler fuer Doppelklick in der Tabelle."""
        if self._tbl is None:
            return

        item = self._tbl.item(row, 0)
        req_id = None if item is None else item.data(Qt.UserRole)
        if req_id in (None, ""):
            return

        # Normale Nutzer landen bei einer bereits offenen Aenderungs-Kopie
        # direkt auf dieser (weiter editieren), nicht auf dem eingefrorenen
        # Original - sonst wuerde ein zweites Speichern eine zweite Kopie
        # anlegen statt die bereits wartende zu aktualisieren.
        if not self._is_superuser:
            pending_id = self._pending_copy_map.get(req_id)
            if pending_id is not None:
                req_id = pending_id
        else:
            # A superuser double-clicking a row that has a pending change
            # goes straight to the side-by-side review instead of the plain
            # edit form (user request 2026-09-01: reviewing a change must
            # default to seeing old vs. new, not require an extra
            # right-click detour).
            pending_id = self._pending_copy_map.get(req_id)
            if pending_id is not None:
                self._review_pending_change(req_id, pending_id)
                return

        # 1) Preferred: expliziter Navigator-Callback
        if callable(self.on_open_request):
            self.on_open_request(req_id)
            return

        # 2) Fallback: Methodensuche in Parent-Chain und am Main Window (keine Popups)
        targets: List[Any] = []
        p = self.parentWidget()
        while p is not None:
            targets.append(p)
            p = p.parentWidget()

        wnd = self.window()
        if wnd is not None and wnd not in targets:
            targets.append(wnd)

        if not targets:
            return

        candidate_names = [
            # sehr wahrscheinlich
            "on_open_request",
            "open_request",
            "open_experiment_request",
            "open_experiment_requests",
            "show_create_experiment_request",
            "open_create_experiment_request",
            "goto_create_experiment_request",
            "go_to_create_experiment_request",
            "navigate_create_experiment_request",
            "navigate_to_create_experiment_request",
            # generische Navigator-Methoden
            "navigate",
            "navigate_to",
            "go_to",
            "show_screen",
            "set_screen",
            "open_screen",
            "push_screen",
        ]

        for target in targets:
            for name in candidate_names:
                fn = getattr(target, name, None)
                if not callable(fn):
                    continue

                # Versuche zuerst die einfachsten/haeufigsten Signaturen.
                try:
                    fn(req_id)
                    return
                except TypeError:
                    try:
                        fn(request_id=req_id)
                        return
                    except Exception:
                        pass
                except Exception:
                    pass

                # Versuche Varianten mit Screen-Name + ID (bei generischen Navigatoren)
                for screen_name in ("create_experiment_request", "experiment_request", "request"):
                    try:
                        fn(screen_name, req_id)
                        return
                    except TypeError:
                        try:
                            fn(screen_name=screen_name, request_id=req_id)
                            return
                        except Exception:
                            pass
                    except Exception:
                        pass

        # 3) Wenn nichts gefunden wurde: stillschweigend nichts tun
        # (kein QMessageBox, kein Dialog)

    # ---------------- Context Menu / Assign Experiment ----------------

    def _on_context_menu(self, pos):
        """Right-click menu - "Assign experiment"/accepting/rejecting a
        pending change stays superuser-only, "View version history" is
        available to EVERY user for their own requests (the table already
        only shows non-superusers their own rows, see refresh()) - user
        request 2026-09-01: version history should be traceable for the
        user, not just superusers."""
        if self._tbl is None:
            return

        index = self._tbl.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()

        # req_id und aktuellen Status aus der Zeile lesen
        first_item = self._tbl.item(row, 0)
        if first_item is None:
            return
        req_id = first_item.data(Qt.UserRole)
        if req_id in (None, ""):
            return

        # Status ermitteln: Status-Combo in der Zeile auslesen (robust über alle Spalten)
        current_status_id = None
        for col in range(self._tbl.columnCount()):
            widget = self._tbl.cellWidget(row, col)
            if isinstance(widget, QComboBox):
                current_status_id = widget.currentData()
                break

        pending_copy_id = self._pending_copy_map.get(req_id) if self._is_superuser else None
        has_history = request_changes.has_versions(req_id)

        if not self._is_superuser and not has_history:
            return
        if self._is_superuser and current_status_id != 3 and pending_copy_id is None and not has_history:
            return

        menu = QMenu(self)
        action_assign = None
        action_review = None
        action_view = None
        action_history = None

        if self._is_superuser and current_status_id == 3:
            action_assign = menu.addAction("Assign experiment…")

        if self._is_superuser and pending_copy_id is not None:
            if action_assign is not None:
                menu.addSeparator()
            action_review = menu.addAction("Review Changes…")
            action_view = menu.addAction("View/edit change proposal…")

        if has_history:
            if action_assign is not None or action_review is not None:
                menu.addSeparator()
            action_history = menu.addAction("View version history…")

        chosen = menu.exec(self._tbl.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen is action_assign:
            self._assign_experiment_to_request(req_id)
        elif chosen is action_review:
            self._review_pending_change(req_id, pending_copy_id)
        elif chosen is action_view:
            if callable(self.on_open_request):
                self.on_open_request(pending_copy_id)
        elif chosen is action_history:
            from ui.widgets.experiment_request_version_history import show_version_history
            show_version_history(self, req_id)

    def _review_pending_change(self, original_req_id: Any, copy_id: Any) -> None:
        """Opens the side-by-side diff dialog for a pending change (user
        request 2026-09-01: a superuser approving a change must see old vs.
        new by default, with the actual differences highlighted, to make a
        good decision) and applies whatever accept/reject decision was made
        there - see ui/widgets/experiment_request_diff_dialog.py, which
        performs the actual accept/reject itself; this only handles the
        screen-level follow-up (notify the owner, refresh the table)."""
        from ui.widgets.experiment_request_diff_dialog import review_pending_change
        outcome = review_pending_change(self, original_req_id, copy_id)
        if outcome == "accepted":
            self._notify_owner_of_request(original_req_id, "your proposed change was accepted")
            QMessageBox.information(self, "Accepted", "The proposed change has been applied.")
            self.refresh()
        elif outcome == "rejected":
            self._notify_owner_of_request(original_req_id, "your proposed change was rejected")
            QMessageBox.information(self, "Rejected", "The proposed change has been discarded.")
            self.refresh()

    def _assign_experiment_to_request(self, req_id: Any):
        """Öffnet einen Dialog zur Auswahl eines Experiments (ohne bestehenden Request)
        und verknüpft dieses mit dem Request. Setzt den Request-Status anschliessend auf 4."""

        # --- Experimente ohne bestehende Request-Verknüpfung laden ---
        er_field = self._resolve_experiment_request_field()
        if not er_field:
            QMessageBox.warning(
                self,
                "Assign experiment",
                "The field 'ExperimentRequestID' was not found in tblExperimente.\n"
                "Please check the database schema.",
            )
            return

        try:
            exp_id_field, pk_field = er.experiment_id_fields()
        except Exception as e:
            show_error(self, "Assign experiment", "The experiment requests could not be read.", e)
            return

        try:
            exp_rows = er.unlinked_experiments(er_field, exp_id_field, pk_field)
        except Exception as e:
            show_error(self, "Assign experiment", "The experiments could not be loaded.", e)
            return

        if not exp_rows:
            QMessageBox.information(
                self,
                "Assign experiment",
                "No experiments without an existing request link found.",
            )
            return

        # --- Dialog aufbauen ---
        dlg = QDialog(self)
        dlg.setWindowTitle("Assign experiment")
        dlg.setMinimumWidth(420)
        dlg.setModal(True)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        lbl_hint = QLabel(
            f"Link request <b>#{req_id}</b> to an experiment.<br>"
            "<small>Only experiments without a request are shown.</small>"
        )
        lbl_hint.setWordWrap(True)
        layout.addWidget(lbl_hint)

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        cmb = QComboBox()
        cmb.setMinimumHeight(28)
        cmb.setStyleSheet(
            "QComboBox { background: #ffffff; border: 1px solid #8fbf8f; padding: 2px 8px; }"
            "QComboBox QAbstractItemView { background: #ffffff; selection-background-color: #d7e3f4; }"
        )
        cmb.addItem("– Please select –", None)
        for pk, exp_id_val in exp_rows:
            cmb.addItem(er.experiment_choice_label(pk, exp_id_val), pk)

        form.addRow("Experiment:", cmb)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, dlg
        )
        buttons.button(QDialogButtonBox.Ok).setText("Zuordnen")
        buttons.button(QDialogButtonBox.Cancel).setText("Cancel")
        buttons.button(QDialogButtonBox.Ok).setEnabled(False)
        layout.addWidget(buttons)

        def _on_combo_changed():
            buttons.button(QDialogButtonBox.Ok).setEnabled(cmb.currentData() is not None)

        cmb.currentIndexChanged.connect(_on_combo_changed)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        if dlg.exec() != QDialog.Accepted:
            return

        selected_pk = cmb.currentData()
        if selected_pk is None:
            return

        selected_exp_label = cmb.currentText()

        # --- Bestätigung ---
        reply = QMessageBox.question(
            self,
            "Confirm assignment",
            f"Link experiment <b>{selected_exp_label}</b> with request <b>#{req_id}</b>?\n\n"
            f"The request status will be set to «Experiment» (4).",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # --- DB schreiben (Verknuepfung + Status 4) ---
        try:
            er.link_experiment(req_id, selected_pk, er_field, pk_field)
        except Exception as e:
            show_error(self, "Error", "The experiment could not be assigned.", e)
            return

        self._notify_owner_of_request(req_id, "status changed to Experiment")

        QMessageBox.information(
            self,
            "Link saved",
            f"Experiment {selected_exp_label} was linked to request #{req_id} zugeordnet.",
        )
        self.refresh()

    def _exp_id_col_index(self) -> int:
        """Gibt den Index der Experiment ID Spalte zurück."""
        return self._tbl.columnCount() - 1

    def eventFilter(self, obj, event):
        """Hand-Cursor wenn über Experiment ID Zelle mit Inhalt."""
        from PySide6.QtCore import QEvent
        if obj is self._tbl.viewport() and event.type() == QEvent.MouseMove:
            idx = self._tbl.indexAt(event.pos())
            if idx.isValid() and idx.column() == self._exp_id_col_index():
                item = self._tbl.item(idx.row(), idx.column())
                if item and item.data(Qt.UserRole):
                    self._tbl.viewport().setCursor(Qt.PointingHandCursor)
                    return False
            self._tbl.viewport().unsetCursor()
        return False

    def _on_cell_clicked(self, row: int, col: int):
        """Klick auf Experiment ID → Series-Auswahl-Popup → screen_show_experiment."""
        if col != self._exp_id_col_index():
            return
        item = self._tbl.item(row, col)
        if not item:
            return
        exp_id_txt = item.data(Qt.UserRole)
        if not exp_id_txt:
            return
        self._open_experiment_series(str(exp_id_txt))

    def _open_experiment_series(self, exp_id_txt: str):
        """Lädt Series des Experiments und navigiert direkt oder via Popup."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QLabel, QDialogButtonBox
        try:
            # Experiment PK laden
            from db.connection import fetch_all as _fa, get_columns_map as _gcm
            cols = _gcm("tblexperimente")
            f_id = None
            for cand in ("experimentid", "experiment id", "experimentid_txt"):
                if cand in cols:
                    f_id = cols[cand]
                    break
            if not f_id:
                return
            exp_rows = _fa(f"SELECT ID FROM tblExperimente WHERE `{f_id}` = %s", [exp_id_txt])
            if not exp_rows:
                return
            exp_pk = int(exp_rows[0]["ID"])

            # Series laden
            series_rows = _fa(
                "SELECT ID, SeriesName, "
                "(SELECT COUNT(*) FROM tblTrial WHERE TrialSeriesID = tblTrialSeries.ID) AS TrialCount "
                "FROM tblTrialSeries WHERE ExperimentID = %s ORDER BY ID",
                [exp_pk]
            )
            if not series_rows:
                return

            def _navigate(series_pk, series_name):
                if callable(getattr(self, "on_open_experiment", None)):
                    self.on_open_experiment(exp_pk, series_pk, exp_id_txt)
                else:
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Navigation", "on_open_experiment is not set.")

            if len(series_rows) == 1:
                # Direkt navigieren
                _navigate(int(series_rows[0]["ID"]), str(series_rows[0].get("SeriesName") or ""))
            else:
                # Popup mit Series-Auswahl
                dlg = QDialog(self)
                dlg.setWindowTitle(f"Experiment {exp_id_txt} – Select series")
                dlg.setMinimumWidth(380)
                lay = QVBoxLayout(dlg)
                lay.addWidget(QLabel(f"<b>{exp_id_txt}</b> hat mehrere Series:"))
                lst = QListWidget()
                lst.setAlternatingRowColors(True)
                for sr in series_rows:
                    name = str(sr.get("SeriesName") or f"Series {sr['ID']}")
                    count = sr.get("TrialCount") or 0
                    item = QListWidgetItem(f"{name}  ({count} Trials)")
                    item.setData(Qt.UserRole, (int(sr["ID"]), name))
                    lst.addItem(item)
                lst.setCurrentRow(0)
                lay.addWidget(lst)
                bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                bb.accepted.connect(dlg.accept)
                bb.rejected.connect(dlg.reject)
                lay.addWidget(bb)
                # Doppelklick = sofort öffnen
                lst.itemDoubleClicked.connect(lambda _: dlg.accept())
                if dlg.exec() == QDialog.Accepted and lst.currentItem():
                    series_pk, series_name = lst.currentItem().data(Qt.UserRole)
                    _navigate(series_pk, series_name)
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", str(e))

    def _go_home(self):
        """Navigiert zurück zum Home-Screen."""
        if callable(getattr(self, "on_back_home", None)):
            self.on_back_home()