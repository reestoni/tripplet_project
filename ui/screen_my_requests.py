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
    QMenu,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
)

import app_meta
import datetime
from db.connection import get_connection
from ui.widgets.header import HeaderBar
from ui.widgets.footer import FooterBar
from ui.screen_create_experiment import table_exists, get_columns_map, resolve_field


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

    def __init__(self, on_back_home=None, on_back_experiment_request=None,
                 on_open_request: Optional[Callable[[Any], None]] = None, on_open_experiment=None):
        super().__init__()
        self.on_back_home = on_back_home
        self.on_back_experiment_request = on_back_experiment_request
        self.on_open_request = on_open_request
        self.on_open_experiment = on_open_experiment

        self._table_name = "tblExperimentRequests"
        self._user_id: Optional[Any] = None

        self._tbl: Optional[QTableWidget] = None
        self._lbl_info: Optional[QLabel] = None

        # Dropdown-Choices fuer RequestStatus (tblRequestStatus)
        # Liste von (id, label)
        self._status_choices: List[Tuple[Any, str]] = []
        self._is_superuser: bool = False

        self._build_ui()

    # ---------------- Lookups ----------------

    def _load_status_choices(self) -> List[Tuple[Any, str]]:
        """Lädt alle möglichen Status-Werte aus tblExperimentRequestStatus.

        Returns:
            Liste von (StatusID, StatusName)-Tupeln.
        """
        """Lädt Status-Choices aus tblRequestStatus, sortiert nach RequestOrder."""
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

    def _update_request_status(self, request_id: Any, new_status_id: Any) -> bool:
        """Aktualisiert den Status eines Requests in der DB.

        Returns:
            True bei Erfolg, False bei Fehler.
        """
        """Schreibt tblRequestStatus.ID in tblExperimentRequests.RequestStatus."""
        try:
            with get_connection() as cn:
                cur = cn.cursor()
                cur.execute(
                    "UPDATE [tblExperimentRequests] SET [RequestStatus]=? WHERE [ID]=?",
                    [new_status_id, request_id],
                )
                try:
                    cn.commit()
                except Exception:
                    pass
            return True
        except Exception as e:
            QMessageBox.critical(self, "DB Error", str(e))
            return False

    def set_user(self, user_id: Optional[Any]):
        """Setzt die Benutzer-ID für die Filterung und lädt die Daten neu.

        Muss aufgerufen werden bevor der Screen angezeigt wird.
        """
        self._user_id = user_id

    def _resolve_experiment_request_field(self) -> Optional[str]:
        """Ermittelt den FK-Feldnamen in tblExperimente, der auf ExperimentRequests zeigt.

        Verschiedene DB-Versionen nutzen unterschiedliche Feldnamen.
        Gibt None zurück wenn kein passendes Feld gefunden wurde.
        """
        """Findet das Feld in tblExperimente, das auf einen Experiment Request (ID) verweist."""
        try:
            if not table_exists("tblExperimente"):
                return None
            cols = get_columns_map("tblExperimente")
            return resolve_field(
                ["ExperimentRequest", "Experiment Request", "ExperimentRequestID", "ExperimentRequestId"],
                cols,
            )
        except Exception:
            return None

    def _prefetch_experiment_ids_for_requests(self, request_ids: List[Any]) -> dict:
        """Lädt die zugehörigen Experiment-IDs für eine Liste von Request-IDs.

        Wird verwendet um in der Tabelle die lesbare Experiment-ID (z.B. "2024-PG-001")
        statt der internen DB-ID anzuzeigen.

        Returns:
            Dict {RequestID: ExperimentID-String}.
        """
        """Liefert {RequestID: ExperimentID} für gegebene RequestIDs.

        Robust gegen unterschiedliche Feldnamen (Migration Access/MySQL).
        """
        out: dict = {}
        if not request_ids:
            return out

        er_field = self._resolve_experiment_request_field()
        if not er_field:
            return out

        try:
            cols = get_columns_map("tblExperimente")
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
            self._lbl_info.setText("Kein User eingeloggt – keine Requests verfuegbar.")
            self._tbl.setRowCount(0)
            self._tbl.setColumnCount(0)
            return

        # Superuser: darf Status aendern UND sieht alle Requests.
        # Nicht-Superuser: sieht nur die eigenen Requests.
        self._is_superuser = bool(getattr(app_meta, "is_superuser_level", lambda: False)())

        # Status-Choices laden (auch fuer Nicht-Superuser, damit Combo den Text anzeigen kann)
        self._status_choices = self._load_status_choices()

        try:
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

                params: List[Any] = []
                if not self._is_superuser:
                    sql += "WHERE er.[CreatedBy]=? "
                    params.append(uid)

                sql += "ORDER BY er.[Timestamp] DESC"
                cur.execute(sql, params)
                rows = cur.fetchall()
                col_names = [d[0] for d in (cur.description or [])]
        except Exception as e:
            QMessageBox.critical(self, "DB Error", str(e))
            self._lbl_info.setText("Fehler beim Laden.")
            self._tbl.setRowCount(0)
            self._tbl.setColumnCount(0)
            return

        hidden_cols = {"CreatedBy", "Projekt", "ID", "Timestamp"}
        if not self._is_superuser:
            hidden_cols.add("CreatedByUser")

        visible_cols: List[Tuple[int, str]] = []
        for i, name in enumerate(col_names):
            if name in hidden_cols:
                continue
            visible_cols.append((i, name))

        self._tbl.setSortingEnabled(False)
        self._tbl.clear()
        # +1 für die zusätzliche UI-Spalte
        self._tbl.setColumnCount(len(visible_cols) + 1)

        header_labels: List[str] = []
        for _, name in visible_cols:
            if name == "ProjektText":
                header_labels.append("Projekt")
            elif name == "CreatedByUser":
                header_labels.append("Owner")
            else:
                header_labels.append(name)
        header_labels.append("Experiment ID")
        self._tbl.setHorizontalHeaderLabels(header_labels)
        self._tbl.setRowCount(len(rows))

        # Indizes ermitteln
        id_idx: Optional[int] = None
        rs_idx: Optional[int] = None
        for i, n in enumerate(col_names):
            ln = str(n).strip().lower()
            if ln == "id":
                id_idx = i
            elif ln == "requeststatus":
                rs_idx = i

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

        for r, row in enumerate(rows):
            req_id = row[id_idx] if id_idx is not None else None
            current_status_id = row[rs_idx] if rs_idx is not None else None

            for c_vis, (c_src, _col_name) in enumerate(visible_cols):
                # RequestStatus als Dropdown
                if rs_idx is not None and c_src == rs_idx:
                    item = QTableWidgetItem("")
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    if c_vis == 0:
                        item.setData(Qt.UserRole, req_id)
                    self._tbl.setItem(r, c_vis, item)

                    combo = NoScrollComboBox()
                    combo.setMinimumHeight(24)
                    combo.setStyleSheet(
                        "QComboBox { background: #ffffff; border: 1px solid #8fbf8f; padding: 2px 6px; }"
                        "QComboBox QAbstractItemView { background: #ffffff; }"
                    )
                    # Superuser soll Status ändern dürfen, aber nicht auf "leer" und nicht auf "Experiment".

                    # Nicht-Superuser: Combo bleibt deaktiviert, darf aber den aktuellen Text anzeigen.

                    if not self._is_superuser:
                        combo.addItem("", None)

                    for _id, label in self._status_choices:

                        lbl = "" if label is None else str(label)

                        # Für Superuser: "Experiment" und leere Werte NICHT als Option anbieten.

                        if self._is_superuser:

                            if lbl.strip() == "":
                                continue

                            if lbl.strip().lower() == "experiment":

                                # Falls der aktuelle Status aus historischen Gründen "Experiment" ist,

                                # darf er angezeigt werden, aber nicht auswählbar sein.

                                if _id == current_status_id:

                                    combo.addItem(lbl, _id)

                                    try:

                                        combo.model().item(combo.count() - 1).setEnabled(False)

                                    except Exception:

                                        pass

                                continue

                        combo.addItem(lbl, _id)

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
                            for _id, _label in self._status_choices:
                                if _id == _sid:
                                    return "" if _label is None else str(_label)
                            return ""

                        def _set_combo_to_status_id(_sid: Any, *, _cb: QComboBox) -> None:
                            _cb.blockSignals(True)
                            if _sid in (None, ""):
                                _cb.setCurrentIndex(0)
                            else:
                                _idx = _cb.findData(_sid)
                                _cb.setCurrentIndex(_idx if _idx >= 0 else 0)
                            _cb.blockSignals(False)

                        def _on_status_changed(_index: int, *, _req_id=req_id, _cb=combo):
                            new_id = _cb.currentData()

                            # Nicht erlaubt: leer / None
                            if new_id in (None, ""):
                                _set_combo_to_status_id(_state["old_id"], _cb=_cb)
                                return

                            # Nicht erlaubt: Status "Experiment"
                            if _label_for_status_id(new_id).strip().lower() == "experiment":
                                _set_combo_to_status_id(_state["old_id"], _cb=_cb)
                                return

                            if self._update_request_status(_req_id, new_id):
                                _state["old_id"] = new_id
                            else:
                                _set_combo_to_status_id(_state["old_id"], _cb=_cb)

                        combo.currentIndexChanged.connect(_on_status_changed)

                    self._tbl.setCellWidget(r, c_vis, combo)
                    continue

                val = row[c_src]
                # Format dates
                if _col_name == "Wunschtermin" and val not in (None, ""):
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
                item = QTableWidgetItem("" if val is None else str(val))

                # Titel-Spalte gruen + fett darstellen
                if str(_col_name).strip().lower() == "titel":
                    item.setData(Qt.ForegroundRole, QColor("#39A650"))

                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)

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
            self._lbl_info.setText(f"{len(rows)} Request(s) (Superuser-Ansicht: alle)")
        else:
            self._lbl_info.setText(f"{len(rows)} Request(s) fuer {uname}")

    # ---------------- UI ----------------

    def _build_ui(self):
        """Erstellt Header, Filter-Toolbar, Tabelle, Aktions-Buttons und Footer."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = HeaderBar(title="My Requests", show_home=True, show_back=True)
        header.connect_home(self._go_home)
        header.connect_back(self._go_experiment_request)
        root.addWidget(header, 0)

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
        top_row.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setObjectName("GreyBtn")
        btn_refresh.clicked.connect(self.refresh)
        top_row.addWidget(btn_refresh, 0, Qt.AlignRight)
        card_layout.addLayout(top_row)

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
        root.addWidget(center, 1)

        root.addWidget(FooterBar(), 0)

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
        """Zeigt Rechtsklick-Menü an – «Experiment zuordnen» nur für Superuser bei Status=3."""
        if self._tbl is None or not self._is_superuser:
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

        if current_status_id != 3:
            return

        menu = QMenu(self)
        action = menu.addAction("Experiment zuordnen…")
        chosen = menu.exec(self._tbl.viewport().mapToGlobal(pos))
        if chosen is action:
            self._assign_experiment_to_request(req_id)

    def _assign_experiment_to_request(self, req_id: Any):
        """Öffnet einen Dialog zur Auswahl eines Experiments (ohne bestehenden Request)
        und verknüpft dieses mit dem Request. Setzt den Request-Status anschliessend auf 4."""

        # --- Experimente ohne bestehende Request-Verknüpfung laden ---
        er_field = self._resolve_experiment_request_field()
        if not er_field:
            QMessageBox.warning(
                self,
                "Experiment zuordnen",
                "Das Feld 'ExperimentRequestID' wurde in tblExperimente nicht gefunden.\n"
                "Please check the database schema.",
            )
            return

        try:
            cols = get_columns_map("tblExperimente")
            exp_id_field = resolve_field(
                ["ExperimentID", "Experiment ID", "ExperimentId"], cols
            ) or "ExperimentID"
            pk_field = resolve_field(["ID"], cols) or "ID"
        except Exception as e:
            QMessageBox.critical(self, "Experiment zuordnen", f"Spaltenzugriff fehlgeschlagen:\n{e}")
            return

        try:
            with get_connection() as cn:
                cur = cn.cursor()
                cur.execute(
                    f"SELECT [{pk_field}] AS PK, [{exp_id_field}] AS ExpID "
                    f"FROM [tblExperimente] "
                    f"WHERE [{er_field}] IS NULL "
                    f"ORDER BY [{exp_id_field}] DESC",
                )
                exp_rows = cur.fetchall()
        except Exception as e:
            QMessageBox.critical(self, "Experiment zuordnen", f"Experimente konnten nicht geladen werden:\n{e}")
            return

        if not exp_rows:
            QMessageBox.information(
                self,
                "Experiment zuordnen",
                "No experiments without an existing request link found.",
            )
            return

        # --- Dialog aufbauen ---
        dlg = QDialog(self)
        dlg.setWindowTitle("Experiment zuordnen")
        dlg.setMinimumWidth(420)
        dlg.setModal(True)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        lbl_hint = QLabel(
            f"Request <b>#{req_id}</b> einem Experiment zuordnen.<br>"
            "<small>Es werden nur Experimente ohne bestehenden Request angezeigt.</small>"
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
            cmb.addItem(str(exp_id_val) if exp_id_val is not None else f"ID {pk}", pk)

        form.addRow("Experiment:", cmb)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, dlg
        )
        buttons.button(QDialogButtonBox.Ok).setText("Zuordnen")
        buttons.button(QDialogButtonBox.Cancel).setText("Abbrechen")
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
            f"Der Request-Status wird auf «Experiment» (4) gesetzt.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # --- DB schreiben ---
        try:
            with get_connection() as cn:
                cn.autocommit = False
                cur = cn.cursor()
                cur.execute(
                    f"UPDATE [tblExperimente] SET [{er_field}]=? WHERE [{pk_field}]=?",
                    [req_id, selected_pk],
                )
                cur.execute(
                    "UPDATE [tblExperimentRequests] SET [RequestStatus]=4 WHERE [ID]=?",
                    [req_id],
                )
                cn.commit()
        except Exception as e:
            try:
                cn.rollback()
            except Exception:
                pass
            QMessageBox.critical(self, "Fehler", f"Zuordnung fehlgeschlagen:\n{e}")
            return

        QMessageBox.information(
            self,
            "Zuordnung gespeichert",
            f"Experiment {selected_exp_label} wurde Request #{req_id} zugeordnet.",
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
                    QMessageBox.warning(self, "Navigation", "on_open_experiment nicht gesetzt.")

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
            QMessageBox.warning(self, "Fehler", str(e))

    def _go_experiment_request(self):
        """Navigiert zurück zum ExperimentRequest-Übersichts-Screen."""
        # Prefer explicit callback
        if callable(getattr(self, "on_back_experiment_request", None)):
            self.on_back_experiment_request()
            return

        # Fallback: try navigator on main window
        try:
            wnd = self.window()
            fn = getattr(wnd, "_go_experiment_request", None)
            if callable(fn):
                fn()
                return
        except Exception:
            pass

        # Last resort: home
        if callable(getattr(self, "on_back_home", None)):
            self.on_back_home()

    def _go_home(self):
        """Navigiert zurück zum Home-Screen."""
        if callable(getattr(self, "on_back_home", None)):
            self.on_back_home()