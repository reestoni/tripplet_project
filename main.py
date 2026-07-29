# main.py
"""Einstiegspunkt und Hauptfenster von TrippleT (MainWindow).

Dieses Modul enthält:
  - ``MainWindow``: QMainWindow mit QStackedWidget für alle Screens
  - Screen-Navigation: alle ``_go_*``-Methoden wechseln den aktiven Screen
  - Jet-Datenbankoperationen: laden, speichern, erstellen, löschen
  - Login-Callback: ``_on_login_success()`` initialisiert den Benutzerkontext
    (QSS, Akzentfarbe, Quick-Search, Backlog-Zähler)

Screen-Stack (QStackedWidget):
  Login → Home → CreateExperiment / ShowExperiment / AllExperiments /
  Backlog / Canvas / ImageCompare / ManageJets / ManageUser / …

Navigationsfluss:
  Alle Screens bekommen Callbacks als Argumente (on_back_home usw.),
  die in MainWindow zu den ``_go_*``-Methoden verdrahtet sind.
  Es gibt KEINEN globalen Router – Screens kennen nur ihre eigenen Callbacks.

"""
import sys
import os
from typing import List, Dict, Tuple, Optional
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QMessageBox, QVBoxLayout, QWidget, QInputDialog
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

# --- DB-Modus wählen (nur im Quellcode-Start, NICHT in der gebauten .exe) ---
# Muss vor jedem Import passieren, der db.connection lädt (u.a. ui.theme, ui.screen_login).
# In der gefrorenen .exe (PyInstaller) läuft TrippleT immer im prod-Modus, siehe db/connection.py.
if not getattr(sys, "frozen", False) and not os.environ.get("TRIPPLET_MODE"):
    _mode_app = QApplication.instance() or QApplication(sys.argv)
    _mode, _ok = QInputDialog.getItem(
        None,
        "TrippleT – DB-Modus",
        "Gegen welche Datenbank soll gestartet werden?",
        ["prod", "dev", "dev_local"],
        0,
        False,
    )
    if not _ok:
        sys.exit(0)
    os.environ["TRIPPLET_MODE"] = _mode

from ui.theme import APP_QSS, build_qss, set_accent
from ui.screen_login import LoginScreen
from ui.screen_home import HomeScreen
from ui.screen_change_pw import ChangePasswordScreen
from ui.screen_all_experiments import AllExperimentsScreen
from ui.screen_create_experiment import CreateExperimentScreen
from ui.screen_show_experiment import ShowExperimentScreen
from ui.screen_manage_jets import ManageJetsScreen
from ui.screen_manage_top_plates import ManageTopPlatesScreen
from ui.screen_manage_user import ManageUserScreen
from ui.screen_manage_order_types import ManageOrderTypeScreen
from ui.screen_manage_product_groups import ManageProductGroupsScreen
from ui.screen_manage_material import ManageMaterialScreen
from ui.screen_my_requests import MyRequestsScreen
from ui.screen_new_jet import NewJetScreen
from ui.screen_new_top_plate import NewTopPlateScreen
from ui.screen_backlog import BacklogScreen
from ui.screen_experiment_request import ExperimentRequestScreen
from ui.screen_create_experiment_request import CreateExperimentRequestScreen
from ui.screen_image_compare import ImageCompareScreen
try:
    from ui.screen_report import ReportScreen
except Exception as _report_err:
    print(f"[Report] Import fehler: {_report_err}")
    ReportScreen = None

try:
    from ui.screen_canvas import CanvasScreen
except Exception as _canvas_err:
    print(f"[Canvas] Import fehler: {_canvas_err}")
    CanvasScreen = None

try:
    from ui.screen_requirement_hub import RequirementHubScreen
except Exception as _reqhub_err:
    print(f"[RequirementHub] Import fehler: {_reqhub_err}")
    RequirementHubScreen = None

try:
    from ui.screen_quick_scan import QuickScanScreen
except Exception as _qs_err:
    print(f"[QuickScan] Import fehler: {_qs_err}")
    QuickScanScreen = None

try:
    from ui.screen_tdms_batch import TDMSBatchScreen
except Exception as _tdms_err:
    print(f"[TDMSBatch] Import fehler: {_tdms_err}")
    TDMSBatchScreen = None

try:
    from ui.screen_aty_batch import ATYBatchScreen
except Exception as _aty_err:
    print(f"[ATYBatch] Import fehler: {_aty_err}")
    ATYBatchScreen = None

try:
    from ui.screen_nozzle_calculator import NozzleCalculatorScreen
except Exception as _nozzle_err:
    print(f"[JetCalculator] Import fehler: {_nozzle_err}")
    NozzleCalculatorScreen = None

try:
    from ui.screen_air_supply import AirSupplyScreen
except Exception as _air_err:
    print(f"[AirSupply] Import fehler: {_air_err}")
    AirSupplyScreen = None

from ui.screen_quick_search import QuickSearchDialog
try:
    from ui.screen_manage_yarn import ManageYarnScreen
except Exception:
    ManageYarnScreen = None
try:
    from ui.screen_yarn_stock import YarnStockScreen
except Exception:
    YarnStockScreen = None

from db.connection import fetch_all, execute, new_global_id
from ui.pathutil import resource_path
import app_meta


def _canon(s: str) -> str:
    """Normalisiert Spaltennamen für tolerante Vergleiche."""
    return str(s).strip().strip("[]`").replace(" ", "").lower()


def _infer_id_col(rows: List[Dict]) -> str:
    """Ermittelt den Namen der ID-Spalte aus einer Liste von Dicts (sucht nach "id")."""
    if not rows:
        return "ID"
    keys = list(rows[0].keys())
    for k in keys:
        if k.lower() == "id":
            return k
    return keys[0]


class MainWindow(QMainWindow):
    # -->-->-->- Multi-window "last window" close guard -->-->-->-
    def _open_window_count(self, exclude=None) -> int:
        """Counts currently visible top-level TrippleT windows (main window +
        detached windows), optionally excluding one specific window (the one
        that is currently being closed)."""
        count = 0
        if self.isVisible() and self is not exclude:
            count += 1
        for w in getattr(self, "_detached_windows", []):
            try:
                if w.isVisible() and w is not exclude:
                    count += 1
            except RuntimeError:
                # underlying C++ object already deleted
                continue
        return count

    def _confirm_quit_dialog(self, parent) -> bool:
        """Shows the 'last window' confirmation dialog. Returns True if the
        user confirmed they want to close (and thus quit TrippleT)."""
        reply = QMessageBox.question(
            parent,
            "Close TrippleT",
            "This is the last open TrippleT window.\n"
            "Closing it will exit the application.\n\n"
            "Do you really want to quit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def _make_detached_close_guard(self, win):
        """Builds a closeEvent handler for a detached (plain) QMainWindow
        instance that asks for confirmation if it is the last open window."""
        original_close_event = win.closeEvent

        def guarded_close_event(event):
            if self._open_window_count(exclude=win) == 0:
                if not self._confirm_quit_dialog(win):
                    event.ignore()
                    return
            try:
                original_close_event(event)
            except Exception:
                event.accept()

        return guarded_close_event

    def closeEvent(self, event):
        """Asks for confirmation before closing the main window if it is the
        last open TrippleT window (i.e. closing it would exit the app)."""
        if self._open_window_count(exclude=self) == 0:
            if not self._confirm_quit_dialog(self):
                event.ignore()
                return
        super().closeEvent(event)

    def _set_create_experiment_request_screen(self, request_id=None):
        """Erstellt oder ersetzt den CreateExperimentRequest-Screen (lazy init).

        Wird neu erstellt wenn der Screen noch nicht existiert oder request_id sich geändert hat.
        """
        """Create/replace the CreateExperimentRequestScreen.

        We recreate the widget so header/title and internal edit-state are
        always consistent (new vs. edit).
        """

        # Remove old instance from stack (if present)
        try:
            old = getattr(self, "create_experiment_request", None)
            if old is not None:
                self.stack.removeWidget(old)
                try:
                    old.deleteLater()
                except Exception:
                    pass
        except Exception:
            pass

        self.create_experiment_request = CreateExperimentRequestScreen(
            on_back_home=self._go_home,
            on_back_experiment_request=self._go_experiment_request,
            request_id=request_id,
        )
        self.stack.addWidget(self.create_experiment_request)

        # If the screen supports a user context, set it.
        try:
            uid = (self.current_user or {}).get("id")
        except Exception:
            uid = None
        try:
            if hasattr(self.create_experiment_request, "set_user"):
                self.create_experiment_request.set_user(uid)
        except Exception:
            pass

        return self.create_experiment_request

    def _go_edit_experiment_request(self, request_id):
        """Öffnet den Experiment-Request-Screen im Bearbeitungsmodus für eine bestehende Request-ID."""
        """Opens an existing Experiment Request for editing."""
        self._set_create_experiment_request_screen(request_id=request_id)
        self.setWindowTitle("TrippleT – Edit Experiment Request")
        self.stack.setCurrentWidget(self.create_experiment_request)

    def _go_create_experiment_request(self):
        """Öffnet den Experiment-Request-Screen im Neuanlage-Modus."""
        """Öffnet den Screen zum Erfassen eines neuen Experiment-Requests."""
        self._set_create_experiment_request_screen(request_id=None)
        self.setWindowTitle("TrippleT – Create Experiment Request")
        self.stack.setCurrentWidget(self.create_experiment_request)

    def _go_my_requests(self):
        """Öffnet den MyRequests-Screen mit den Requests des aktuellen Benutzers."""
        # User setzen + refreshen, dann Screen anzeigen
        try:
            uid = (self.current_user or {}).get("id")
        except Exception:
            uid = None
        try:
            self.my_requests.set_user(uid)
            self.my_requests.refresh()
        except Exception:
            pass

        self.setWindowTitle("TrippleT – My Requests")
        self.stack.setCurrentWidget(self.my_requests)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TrippleT – Log In")
        self.setMinimumSize(1100, 700)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.current_user = None
        self.home = None
        self.aty_batch = None

        self.change_pw = ChangePasswordScreen(on_dismiss=self._back_to_login)
        self.all_experiments = AllExperimentsScreen(
            on_back_home=self._go_home,
            on_open_experiment=self._open_experiment_from_all,
            on_open_in_new_window=self.open_experiment_in_new_window,
            on_copy_trialseries=self._go_copy_trialseries,
            can_review=False,
        )
        self.show_experiment = ShowExperimentScreen(
            on_back_home=self._go_home,
            on_back_all_experiments=self._go_all_experiments,
            on_add_trials=self._go_addtrials_from_experiment,
        )
        self.report_screen    = ReportScreen(on_back=self._go_back_to_show_experiment, mode="series") if ReportScreen else None
        self.smartchart_screen = ReportScreen(on_back=self._go_home, mode="visual") if ReportScreen else None

        # Prepare Manage Jets
        preview = self._load_jets_data(limit=1)
        self._jets_id_col = _infer_id_col(preview)

        self._fk_maps_cache = self._load_fk_maps_exact()

        # Columns und Metadaten für den "New Jet"-Screen ableiten
        if preview:
            jet_columns = list(preview[0].keys())
        else:
            # Fallback – ID und Jet als Minimum
            jet_columns = [self._jets_id_col, "Jet"]

        bool_columns = {"Gebogener Kanal"}

        # Screen für das Erfassen eines neuen Jets
        self.new_jet = NewJetScreen(
            columns=jet_columns,
            fk_maps=self._fk_maps_cache,
            bool_columns=bool_columns,
            id_column=self._jets_id_col,
            on_back_home=self._go_back_manage_jets,
            on_save=self._insert_jet_full,
            on_created=self._on_new_jet_created,
            check_jet_name=self._is_jet_name_available,
            on_quick_add_fk_value=self._quick_add_fk_value,
        )

        self.manage_jets = ManageJetsScreen(
            on_back_home=self._go_home,
            loader=self._load_jets_data,
            saver=self._save_jets_changes,
            id_column=self._jets_id_col,
            fk_maps=self._fk_maps_cache,
            creator=self._create_jet,
            deleter=self._delete_jets,
            on_open_new_jet=self._go_new_jet,
            on_copy_jet=self._go_copy_new_jet,
            on_edit_jet=self._go_edit_jet_form,
        )

        # Prepare Manage Top Plates
        top_plate_preview = self._load_top_plates_data(limit=1)
        self._top_plates_id_col = _infer_id_col(top_plate_preview)

        # Top Plates haben (vorerst) keine FK-Spalten – leere Map, aber
        # generisch durchgereicht, damit künftige FK-Felder ohne Codeänderung
        # funktionieren (gleiches Muster wie bei den Jets).
        self._top_plate_fk_maps_cache: Dict[str, Dict] = {}

        # Spalten für den "New Top Plate"-Screen ableiten
        if top_plate_preview:
            top_plate_columns = list(top_plate_preview[0].keys())
        else:
            # Fallback – ID und Name als Minimum
            top_plate_columns = [self._top_plates_id_col, "Name"]

        # Screen für das Erfassen einer neuen Top Plate
        self.new_top_plate = NewTopPlateScreen(
            columns=top_plate_columns,
            fk_maps=self._top_plate_fk_maps_cache,
            id_column=self._top_plates_id_col,
            on_back_home=self._go_back_manage_top_plates,
            on_save=self._insert_top_plate_full,
            on_created=self._on_new_top_plate_created,
            check_top_plate_name=self._is_top_plate_name_available,
        )

        self.manage_top_plates = ManageTopPlatesScreen(
            on_back_home=self._go_home,
            loader=self._load_top_plates_data,
            saver=self._save_top_plates_changes,
            id_column=self._top_plates_id_col,
            fk_maps=self._top_plate_fk_maps_cache,
            creator=self._create_top_plate,
            deleter=self._delete_top_plates,
            on_open_new_top_plate=self._go_new_top_plate,
            on_copy_top_plate=self._go_copy_new_top_plate,
            on_edit_top_plate=self._go_edit_top_plate_form,
        )

        # Screens ohne spezielle Loader
        self.manage_user = ManageUserScreen(on_back_home=self._go_home)
        self.manage_order_type = ManageOrderTypeScreen(
            on_back_home=self._go_home)
        self.manage_product_groups = ManageProductGroupsScreen(
            on_back_home=self._go_home)
        self.manage_material = ManageMaterialScreen(on_back_home=self._go_home)

        # Backlog-Screen
        self.backlog = BacklogScreen(
            on_back_home=self._go_home,
            on_open_experiment=self._open_experiment_from_backlog,
            on_open_in_new_window=self.open_experiment_in_new_window,
        )

        # Experiment Request
        self.create_experiment_request = CreateExperimentRequestScreen(
            on_back_home=self._go_home
        )
        self.my_requests = MyRequestsScreen(
            on_back_home=self._go_home,
            on_back_experiment_request=self._go_experiment_request,
            on_open_request=self._go_edit_experiment_request,
            on_open_experiment=self._go_show_experiment,
        )

        self.experiment_request = ExperimentRequestScreen(
            on_back_home=self._go_home,
            on_create_experiment_request=self._go_create_experiment_request,
            on_open_my_requests=self._go_my_requests,
        )

        self.login = LoginScreen(
            on_success=self._on_login_success,
            on_change_pw=self._go_change_pw
        )

        self.stack.addWidget(self.login)
        self.stack.addWidget(self.change_pw)
        self.stack.addWidget(self.all_experiments)
        self.stack.addWidget(self.show_experiment)
        if self.report_screen is not None:
            self.stack.addWidget(self.report_screen)
        if self.smartchart_screen is not None:
            self.stack.addWidget(self.smartchart_screen)
        self.stack.addWidget(self.manage_jets)
        self.stack.addWidget(self.manage_top_plates)
        self.stack.addWidget(self.manage_user)
        self.stack.addWidget(self.manage_order_type)
        self.stack.addWidget(self.manage_product_groups)
        self.stack.addWidget(self.manage_material)
        self.stack.addWidget(self.new_jet)
        self.stack.addWidget(self.new_top_plate)
        self.stack.addWidget(self.backlog)
        self.stack.addWidget(self.create_experiment_request)
        self.stack.addWidget(self.my_requests)
        self.stack.addWidget(self.experiment_request)

        self.image_compare: Optional[ImageCompareScreen] = None
        self.canvas: Optional[CanvasScreen] = None
        self.tdms_batch: Optional["TDMSBatchScreen"] = None
        self.requirement_hub: Optional["RequirementHubScreen"] = None
        self.quick_scan: Optional["QuickScanScreen"] = None
        self.nozzle_calculator: Optional["NozzleCalculatorScreen"] = None
        self.air_supply: Optional["AirSupplyScreen"] = None
        self._search_dlg: Optional[QuickSearchDialog] = None

        self._create_screen_ref: Optional[CreateExperimentScreen] = None
        self.stack.setCurrentWidget(self.login)

    # --- Data functions for Manage Jets --------------------------------------
    def _load_jets_data(self, limit: Optional[int] = None) -> List[Dict]:
        """Lädt Jet-Daten aus tblJet mit has_files-Flag (0/1)."""
        sql = """
            SELECT j.*,
                   CASE WHEN COUNT(f.ID) > 0 THEN 1 ELSE 0 END AS has_files
            FROM tblDTYJets j
            LEFT JOIN tblJetFile f ON f.JetID = j.ID
            GROUP BY j.ID
        """
        try:
            return fetch_all(sql, [])
        except Exception:
            # Fallback wenn tblJetFile noch nicht existiert
            return fetch_all("SELECT * FROM [tblDTYJets]", [])

    FK_DEF = [
        # FK-Key (kanonisch), FK-Spalte in tblDTYJets, Mastertabelle, ID-Feld, Anzeigefeld
        ("hersteller", "Hersteller", "tblJetHersteller", "ID", "Hersteller"),
        ("serie", "Serie", "tblDTYSeries", "ID", "DTY Series"),
        ("luftkanalform", "Luftkanalform",
         "tblAirChannelShape", "ID", "Air Channel Shape"),
        ("yarnchannelshape", "Yarn Channel Shape",
         "tblYarnChannelShape", "ID", "Shape"),
        ("wirbelkammer", "Wirbelkammer", "tblWirbelkammer", "ID", "Wirbelkammer"),
        ("werkstoff", "Werkstoff", "tblWerkstoff", "ID", "Name"),
        ("konusform", "Konus Form", "tblKonusForm", "ID", "KonusForm"),

        # tblJetGroup: Display soll "GroupNumber | GroupName" sein (wie Manage Yarn)
        ("jetgroup", "JetGroupID", "tblJetGroup", "ID", "GroupName"),

        ("rohling", "Rohling", "tblJetRohling", "ID", "Name"),
        ("jettype", "JetTypeID", "tblJetType", "ID", "Name"),
    ]

    def _load_fk_maps_exact(self) -> Dict[str, Dict]:
        """Lädt alle FK-Maps für Jet-Spalten (Garntyp, Material, Maschine usw.).

        Returns:
            Dict {Spaltenname: {'id2name': ..., 'name2id': ..., 'ordered_items': ...}}.
        """
        """Lädt alle FK-Werte ausschliesslich aus den Stammtabellen.

        Jede ComboBox (Hersteller, Serie, Werkstoff, Konus Form, ...)
        zeigt damit alle Einträge der jeweiligen Hilfstabelle, unabhängig
        davon, ob der Wert bereits in tblDTYJets verwendet wird.

        Zusätzlich werden Debug-Ausgaben geschrieben, damit sofort sichtbar ist,
        wie viele Zeilen je Stammtabelle gefunden wurden bzw. ob ein Fehler
        aufgetreten ist.
        """
        maps: Dict[str, Dict] = {}
        for key, jets_fk_col, table, idc, namec in self.FK_DEF:
            id_to_name: Dict = {}
            name_to_id: Dict = {}

            # Robustes SELECT mit sprechenden Alias-Namen
            # Sonderfall: tblJetGroup soll als Label "GroupNumber | GroupName" erscheinen
            # (und trotzdem die ID in tblDTYJets schreiben).
            if str(table).strip().lower() == "tbljetgroup":
                q = (
                    f"SELECT [{idc}] AS [fk_id], "
                    f"[GroupNumber] AS [fk_no], "
                    f"[{namec}] AS [fk_name] "
                    f"FROM [{table}] "
                    f"ORDER BY [GroupNumber], [{namec}]"
                )
            elif str(table).strip().lower() == "tbljetrohling":
                q = (
                    f"SELECT [{idc}] AS [fk_id], "
                    f"[Nummer] AS [fk_no], "
                    f"[{namec}] AS [fk_name] "
                    f"FROM [{table}] "
                    f"ORDER BY [Nummer], [{namec}]"
                )
            else:
                q = (
                    f"SELECT [{idc}] AS [fk_id], "
                    f"[{namec}] AS [fk_name] "
                    f"FROM [{table}] "
                    f"ORDER BY [{namec}]"
                )

            try:
                rows = fetch_all(q, [])
            except Exception as e:
                # Fehler nicht mehr verschlucken, sondern anzeigen
                print(f"[FK-LOAD] Fehler für {table}.{namec}: {e}")
                rows = []

                # Debug: wie viele Zeilen wurden geladen?
            try:
                row_count = len(rows)
            except Exception:
                row_count = -1
            # print(f"[FK-LOAD] {table}.{namec}: {row_count} Zeilen geladen.")

            for r in rows or []:
                i = r.get("fk_id")
                n = r.get("fk_name")

                # Sonderfall: tblJetGroup => "<GroupNumber> | <GroupName>"
                if str(table).strip().lower() == "tbljetgroup":
                    no = r.get("fk_no")
                    left = "" if no is None else str(no).strip()
                    right = "" if n is None else str(n).strip()
                    n = f"{left} | {right}".strip(" |")

                # Sonderfall: tblJetRohling => "<Nummer> - <Name>"
                elif str(table).strip().lower() == "tbljetrohling":
                    no = r.get("fk_no")
                    left = "" if no is None else str(no).strip()
                    right = "" if n is None else str(n).strip()
                    n = f"{left} - {right}".strip(" -")

                if i is None or n is None:
                    continue

                # Verschiedene Schlüsselvarianten für bequemen Zugriff
                id_to_name[i] = n
                id_to_name[str(i)] = n
                try:
                    id_to_name[int(i)] = n  # falls ID numerisch ist
                except Exception:
                    pass

                name_to_id[str(n)] = i

            maps[key] = {
                "id_to_name": id_to_name,
                "name_to_id": name_to_id,
            }
            # Auch unter _canon(jets_fk_col) speichern, da screen_new_jet
            # eine andere _canon-Implementierung verwendet (kein ID-stripping)
            alt_key = _canon(jets_fk_col)
            if alt_key != key:
                maps[alt_key] = maps[key]

        return maps

    def _quick_add_fk_value(self, col: str, name: str) -> Optional[int]:
        """Fuegt einen neuen Eintrag in die Stammtabelle einer FK-Spalte ein
        (z.B. neuer Jet-Hersteller direkt aus dem New-Jet-Formular, ueber den
        "+"-Button) und aktualisiert den FK-Cache. Gibt die neue ID zurueck."""
        name = (name or "").strip()
        if not name:
            return None
        entry = None
        for key, jets_fk_col, table, idc, namec in self.FK_DEF:
            if jets_fk_col == col or _canon(jets_fk_col) == _canon(col) or key == _canon(col):
                entry = (table, idc, namec)
                break
        if entry is None:
            return None
        table, idc, namec = entry
        try:
            execute(f"INSERT INTO [{table}] ([{namec}]) VALUES (?)", [name])
            rows = fetch_all(
                f"SELECT [{idc}] AS fk_id FROM [{table}] WHERE [{namec}] = ? ORDER BY [{idc}] DESC LIMIT 1",
                [name])
            new_id = rows[0]["fk_id"] if rows else None
        except Exception as e:
            QMessageBox.critical(self, "Add value", f"Failed to add: {e}")
            return None
        if new_id is not None:
            self._fk_maps_cache = self._load_fk_maps_exact()
        return new_id

    def _save_jets_changes(self, rows: List[Dict]) -> int:
        """Schreibt geänderte Jet-Zeilen via UPDATE in die DB.

        Returns:
            Anzahl erfolgreich aktualisierter Zeilen.
        """
        if not rows:
            return 0
        id_col = self._jets_id_col or "ID"
        total = 0
        _SYNTHETIC = {"__has_files__", "has_files"}
        for r in rows:
            if id_col not in r:
                raise ValueError(f"Row has no '{id_col}' field; cannot save.")
            row_id = r[id_col]
            cols = [c for c in r.keys() if c != id_col and c not in _SYNTHETIC]
            if not cols:
                continue
            set_access = ", ".join([f"[{c}] = ?" for c in cols])
            sql = f"UPDATE [tblDTYJets] SET {set_access} WHERE [{id_col}] = ?"
            params = [r[c] for c in cols] + [row_id]
            total += execute(sql, params) or 0
        return total

    # --- Create / Delete ------------------------------------------------------
    def _first_fk_default(self, fk_key_canon: str):
        """Gibt den ersten verfügbaren FK-Wert als Default zurück (für Neuanlage)."""
        m = self._fk_maps_cache.get(_canon(fk_key_canon), {})
        ids = []
        for k in m.get("id_to_name", {}).keys():
            try:
                if isinstance(k, int):
                    ids.append(k)
            except Exception:
                continue
        if not ids:
            for k in m.get("id_to_name", {}).keys():
                try:
                    ids.append(int(str(k)))
                except Exception:
                    continue
        return min(ids) if ids else None

    def _create_jet(self) -> int:
        """Legt einen neuen Jet mit Default-Werten in der DB an und gibt die neue ID zurück."""
        cols = ["Jet", "Gebogener Kanal", "GlobalID"]
        vals = ["Neuer Jet", 0, new_global_id()]
        fk_candidates = ["Hersteller", "Serie", "Luftkanalform",
                         "Yarn Channel Shape", "Wirbelkammer", "Werkstoff"]
        for c in fk_candidates:
            d = self._first_fk_default(c)
            if d is not None:
                cols.append(c)
                vals.append(d)

        placeholders = ",".join(["?"] * len(cols))
        cols_sql = ", ".join([f"[{c}]" for c in cols])
        sql = f"INSERT INTO [tblDTYJets] ({cols_sql}) VALUES ({placeholders})"
        execute(sql, vals)

        row = fetch_all("SELECT @@IDENTITY AS NewID", [])
        new_id = int(row[0]["NewID"]) if row and "NewID" in row[0] else None
        return new_id

    def _insert_jet_full(self, data: Dict) -> int:
        """Fügt einen neuen Jet mit vollständigen Daten (Kopie) in die DB ein.

        Returns:
            Neue Jet-ID (@@IDENTITY).
        """
        id_col = self._jets_id_col or "ID"
        _SYNTHETIC = {"__has_files__", "has_files"}

        if id_col in data:
            data = {k: v for k, v in data.items() if k.lower() !=
                    id_col.lower()}

        data = {k: v for k, v in data.items() if k not in _SYNTHETIC}

        has_global = False
        for k in data.keys():
            if k.lower() == "globalid":
                has_global = True
                break
        if not has_global:
            data["GlobalID"] = new_global_id()

        if not data:
            raise ValueError("Keine Daten zum Speichern übergeben.")

        cols = list(data.keys())
        vals = [data[c] for c in cols]
        cols_sql = ", ".join(f"[{c}]" for c in cols)
        placeholders = ", ".join("?" for _ in cols)
        sql = f"INSERT INTO [tblDTYJets] ({cols_sql}) VALUES ({placeholders})"
        execute(sql, vals)

        row = fetch_all("SELECT @@IDENTITY AS NewID", [])
        new_id = int(row[0]["NewID"]) if row and "NewID" in row[0] else None
        if new_id is None:
            raise RuntimeError("Konnte neue ID nach Insert nicht bestimmen.")
        return new_id

    def _delete_jets(self, ids: List[int]) -> int:
        """Löscht Jets mit den gegebenen IDs aus tblJet.

        Returns:
            Anzahl gelöschter Zeilen.
        """
        if not ids:
            return 0
        placeholders = ",".join(["?"] * len(ids))
        sql = f"DELETE FROM [tblDTYJets] WHERE [ID] IN ({placeholders})"
        return execute(sql, ids) or 0

    def _is_jet_name_available(self, jet_name: str) -> bool:
        """Prüft ob ein Jet-Name in tblJet noch nicht vergeben ist."""
        """Prüft, ob es den Jet-Namen in tblDTYJets bereits gibt."""
        if not jet_name:
            return False
        try:
            rows = fetch_all(
                "SELECT COUNT(*) AS n FROM [tblDTYJets] WHERE [Jet] = ?", [jet_name])
        except Exception:
            return True  # im Zweifel nicht blockieren
        if not rows:
            return True
        row = rows[0]
        count = row.get("n")
        if count is None:
            # Fallback, falls der Key anders heisst
            try:
                count = list(row.values())[0]
            except Exception:
                count = 0
        try:
            return int(count) == 0
        except Exception:
            return True

    # --- Data functions for Manage Top Plates ---------------------------------
    def _load_top_plates_data(self, limit: Optional[int] = None) -> List[Dict]:
        """Lädt Top-Plate-Daten aus tblTopPlates mit has_files-Flag (0/1)."""
        sql = """
            SELECT p.*,
                   CASE WHEN COUNT(f.ID) > 0 THEN 1 ELSE 0 END AS has_files
            FROM tblTopPlates p
            LEFT JOIN tblTopPlateFile f ON f.TopPlateID = p.ID
            GROUP BY p.ID
        """
        try:
            return fetch_all(sql, [])
        except Exception:
            # Fallback wenn tblTopPlateFile noch nicht existiert
            return fetch_all("SELECT * FROM [tblTopPlates]", [])

    def _save_top_plates_changes(self, rows: List[Dict]) -> int:
        """Schreibt geänderte Top-Plate-Zeilen via UPDATE in die DB.

        Returns:
            Anzahl erfolgreich aktualisierter Zeilen.
        """
        if not rows:
            return 0
        id_col = self._top_plates_id_col or "ID"
        total = 0
        _SYNTHETIC = {"__has_files__", "has_files"}
        for r in rows:
            if id_col not in r:
                raise ValueError(f"Row has no '{id_col}' field; cannot save.")
            row_id = r[id_col]
            cols = [c for c in r.keys() if c != id_col and c not in _SYNTHETIC]
            if not cols:
                continue
            set_access = ", ".join([f"[{c}] = ?" for c in cols])
            sql = f"UPDATE [tblTopPlates] SET {set_access} WHERE [{id_col}] = ?"
            params = [r[c] for c in cols] + [row_id]
            total += execute(sql, params) or 0
        return total

    def _create_top_plate(self) -> int:
        """Legt eine neue Top Plate mit Default-Werten in der DB an und gibt die neue ID zurück."""
        cols = ["Name", "GlobalID"]
        vals = ["New Top Plate", new_global_id()]

        placeholders = ",".join(["?"] * len(cols))
        cols_sql = ", ".join([f"[{c}]" for c in cols])
        sql = f"INSERT INTO [tblTopPlates] ({cols_sql}) VALUES ({placeholders})"
        execute(sql, vals)

        row = fetch_all("SELECT @@IDENTITY AS NewID", [])
        new_id = int(row[0]["NewID"]) if row and "NewID" in row[0] else None
        return new_id

    def _insert_top_plate_full(self, data: Dict) -> int:
        """Fügt eine neue Top Plate mit vollständigen Daten (Kopie) in die DB ein.

        Returns:
            Neue Top-Plate-ID (@@IDENTITY).
        """
        id_col = self._top_plates_id_col or "ID"
        _SYNTHETIC = {"__has_files__", "has_files"}

        if id_col in data:
            data = {k: v for k, v in data.items() if k.lower() !=
                    id_col.lower()}

        data = {k: v for k, v in data.items() if k not in _SYNTHETIC}

        has_global = False
        for k in data.keys():
            if k.lower() == "globalid":
                has_global = True
                break
        if not has_global:
            data["GlobalID"] = new_global_id()

        if not data:
            raise ValueError("Keine Daten zum Speichern übergeben.")

        cols = list(data.keys())
        vals = [data[c] for c in cols]
        cols_sql = ", ".join(f"[{c}]" for c in cols)
        placeholders = ", ".join("?" for _ in cols)
        sql = f"INSERT INTO [tblTopPlates] ({cols_sql}) VALUES ({placeholders})"
        execute(sql, vals)

        row = fetch_all("SELECT @@IDENTITY AS NewID", [])
        new_id = int(row[0]["NewID"]) if row and "NewID" in row[0] else None
        if new_id is None:
            raise RuntimeError("Konnte neue ID nach Insert nicht bestimmen.")
        return new_id

    def _delete_top_plates(self, ids: List[int]) -> int:
        """Löscht Top Plates mit den gegebenen IDs aus tblTopPlates.

        Returns:
            Anzahl gelöschter Zeilen.
        """
        if not ids:
            return 0
        placeholders = ",".join(["?"] * len(ids))
        sql = f"DELETE FROM [tblTopPlates] WHERE [ID] IN ({placeholders})"
        return execute(sql, ids) or 0

    def _is_top_plate_name_available(self, top_plate_name: str) -> bool:
        """Prüft, ob es den Top-Plate-Namen in tblTopPlates bereits gibt."""
        if not top_plate_name:
            return False
        try:
            rows = fetch_all(
                "SELECT COUNT(*) AS n FROM [tblTopPlates] WHERE [Name] = ?", [top_plate_name])
        except Exception:
            return True  # im Zweifel nicht blockieren
        if not rows:
            return True
        row = rows[0]
        count = row.get("n")
        if count is None:
            # Fallback, falls der Key anders heisst
            try:
                count = list(row.values())[0]
            except Exception:
                count = 0
        try:
            return int(count) == 0
        except Exception:
            return True

    # --- Navigation and existing flow ----------------------------------------
    def _on_login_success(self, user: dict):
        """Callback nach erfolgreichem Login.

        Setzt Akzentfarbe, QSS, Quick-Search-Callback, Backlog-Zähler und
        navigiert zum Home-Screen.

        Args:
            user: Dict mit id, username, first_name, last_name, access_level,
                  access_right, admin_box, accent_colour.
        """
        # Merge Login-Daten in das globale current_user-Objekt,
        # damit Flags wie is_superuser erhalten bleiben.
        try:
            app_meta.current_user.update(user)
        except Exception:
            app_meta.current_user = user
        # Ab hier immer mit dem globalen Objekt weiterarbeiten
        self.current_user = app_meta.current_user
        self.setWindowTitle("TrippleT – Home")

        # Akzentfarbe anwenden
        try:
            set_accent(user.get("accent_colour"))
            QApplication.instance().setStyleSheet(build_qss())
        except Exception:
            pass

        try:
            access_level = int(user.get("access_level") or 0)
        except Exception:
            access_level = 0
        # Zusätzliches Recht: AdminBox (tblUser.AdminBox)
        try:
            admin_box = bool(user.get("admin_box"))
        except Exception:
            admin_box = False
        username = user.get("username") or user.get(
            "Username") or user.get("user")

        # Review-Recht: AccessLevel >= 4
        can_review = access_level >= 4

        try:
            self.all_experiments.set_can_review(can_review)
        except Exception:
            pass

        self.home = HomeScreen(
            on_all_experiments=self._go_all_experiments,
            on_create_experiment=lambda: self._go_create_experiment("create"),
            on_preview_requests=self._show_request_preview_dialog,
            on_create_experiment_legacy=lambda: self._go_create_experiment("legacy"),
            on_add_series=lambda: self._go_create_experiment("addseries"),
            on_add_trials=lambda: self._go_create_experiment("addtrials"),
            on_open_backlog=self._go_backlog,
            on_open_experiment_request=self._go_experiment_request,
            on_image_compare=self._go_image_compare,
            on_canvas=self._go_canvas,
            # on_tdms_batch=self._go_tdms_batch,  # TODO: in screen_home.py eintragen
            on_search=self._open_quick_search,
            access_level=access_level,
            admin_box=admin_box,
            on_add_yarn=self._go_add_yarn,
            on_yarn_stock=self._go_yarn_stock,
            on_add_user=self._go_add_user,
            on_add_jet=self._go_add_jet,
            on_add_top_plate=self._go_add_top_plate,
            on_manage_order_type=self._go_manage_order_type,
            on_manage_product_groups=self._go_manage_product_groups,
            on_manage_material=self._go_manage_material,
            on_add_lab_machines=lambda: self._go_create_experiment(
                "addlabmachines"),
            on_logout=self._logout,
            on_smartchart=self._go_smartchart,
            on_requirement_hub=self._go_requirement_hub,
            on_nozzle_calculator=self._go_nozzle_calculator,
            on_air_supply=self._go_air_supply,
        )
        self.stack.addWidget(self.home)
        self.stack.setCurrentWidget(self.home)

        # ── Notification Bell einrichten ──────────────────────────────────
        try:
            from ui.notifications import get_unread_count, get_total_count, get_notifications, mark_all_as_read
            from ui.widgets.notification_panel import NotificationPanel
            import app_meta as _am

            if not hasattr(self, "_notif_panel") or self._notif_panel is None:
                self._notif_panel = NotificationPanel(self)
                # Signal ist jetzt (exp_pk: int, series_pk: int, experiment_id: str)
                self._notif_panel.notification_clicked.connect(self._go_show_experiment)
                self._notif_panel.yarn_stock_clicked.connect(self._go_yarn_stock_from_notification)
                self._notif_panel.all_read.connect(self._on_bell_mark_all_read)

            def _refresh_bell():
                uid = (app_meta.current_user or {}).get("id")
                if not uid:
                    return
                try:
                    unread = get_unread_count(int(uid))
                    total  = get_total_count(int(uid))
                    # Bell immer sichtbar sobald Eintraege vorhanden (gelesen oder ungelesen)
                    w = self.stack.currentWidget()
                    if w and hasattr(w, "_header") and hasattr(w._header, "set_bell_count"):
                        w._header.set_bell_count(unread, total)
                        if not hasattr(w._header, "_bell_connected") or not w._header._bell_connected:
                            w._header.connect_bell(self._on_bell_clicked)
                            w._header._bell_connected = True
                except Exception:
                    pass

            _am.refresh_bell = _refresh_bell

            # Timer: alle 60s pruefen
            from PySide6.QtCore import QTimer
            if not hasattr(self, "_bell_timer"):
                self._bell_timer = QTimer(self)
                self._bell_timer.timeout.connect(_refresh_bell)
            self._bell_timer.start(60_000)
            _refresh_bell()  # sofort beim Login

        except Exception:
            pass

        # Global Ctrl+F shortcut + app_meta registration
        try:
            from PySide6.QtGui import QShortcut
            self._sc_search = QShortcut(QKeySequence("Ctrl+F"), self)
            self._sc_search.setContext(Qt.ApplicationShortcut)
            self._sc_search.activated.connect(self._open_quick_search)
        except Exception:
            pass
        try:
            app_meta.open_quick_search = self._open_quick_search
        except Exception:
            pass

    def _go_home(self):
        """Navigiert zum Home-Screen."""
        if self.home is None:
            self.stack.setCurrentWidget(self.login)
            self.setWindowTitle("TrippleT – Log In")
            return
        self.setWindowTitle("TrippleT – Home")
        self.stack.setCurrentWidget(self.home)
        try:
            import app_meta
            app_meta.refresh_bell()
        except Exception:
            pass

    def _on_bell_clicked(self):
        """Bell-Button geklickt → NotificationPanel anzeigen."""
        try:
            from ui.notifications import get_notifications
            uid = (app_meta.current_user or {}).get("id")
            if not uid:
                return
            notifs = get_notifications(int(uid))
            self._notif_panel.load_notifications(notifs)
            # Panel unter dem Bell-Button positionieren
            w = self.stack.currentWidget()
            if w and hasattr(w, "_header"):
                bell = w._header._btn_bell
                pos = bell.mapToGlobal(bell.rect().bottomLeft())
                self._notif_panel.move(pos)
            self._notif_panel.show()
            self._notif_panel.raise_()
        except Exception:
            pass

    def _on_bell_mark_all_read(self):
        """Alle Notifications als gelesen markieren."""
        try:
            from ui.notifications import mark_all_as_read
            uid = (app_meta.current_user or {}).get("id")
            if uid:
                mark_all_as_read(int(uid))
            self._notif_panel.hide()
            app_meta.refresh_bell()
        except Exception:
            pass

    def _go_backlog(self):
        """Navigiert zum Backlog-Screen."""
        self.setWindowTitle("TrippleT – Backlog")
        self.stack.setCurrentWidget(self.backlog)

    def _go_experiment_request(self):
        """Navigiert zum ExperimentRequest-Übersichts-Screen."""
        self.setWindowTitle("TrippleT – Experiment Request")
        self.stack.setCurrentWidget(self.experiment_request)

    def _go_image_compare(self):
        """Navigiert zum ImageCompare-Screen."""
        if self.image_compare is None:
            self.image_compare = ImageCompareScreen(on_back_home=self._go_home)
            self.stack.addWidget(self.image_compare)
        self.setWindowTitle("TrippleT – Image Compare")
        self.stack.setCurrentWidget(self.image_compare)

    def _go_requirement_hub(self):
        """Navigiert zum Requirement Hub Screen."""
        if RequirementHubScreen is None:
            QMessageBox.warning(self, "Requirement Hub",
                                "Requirement Hub nicht verfügbar – Import fehlgeschlagen.")
            return
        if self.requirement_hub is None:
            self.requirement_hub = RequirementHubScreen(
                on_back_home=self._go_home,
                on_quick_scan=self._go_quick_scan,
            )
            self.stack.addWidget(self.requirement_hub)
        self.setWindowTitle("TrippleT – Requirement Hub")
        self.stack.setCurrentWidget(self.requirement_hub)

    def _go_quick_scan(self):
        """Navigiert zum Quick Scan Screen."""
        if QuickScanScreen is None:
            QMessageBox.warning(self, "Quick Scan",
                                "Quick Scan nicht verfügbar – Import fehlgeschlagen.")
            return
        if self.quick_scan is None:
            self.quick_scan = QuickScanScreen(
                on_back_hub=self._go_requirement_hub,
            )
            self.stack.addWidget(self.quick_scan)
        self.setWindowTitle("TrippleT – Quick Scan")
        self.stack.setCurrentWidget(self.quick_scan)

    def _go_canvas(self):
        """Navigiert zum Canvas-Screen."""
        if CanvasScreen is None:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Canvas", "Canvas nicht verfügbar – Import fehlgeschlagen.")
            return
        if self.canvas is None:
            self.canvas = CanvasScreen(on_back_home=self._go_home)
            self.stack.addWidget(self.canvas)
        self.setWindowTitle("TrippleT – Canvas")
        self.stack.setCurrentWidget(self.canvas)

    def _go_tdms_batch(self):
        """Navigiert zum TDMS-Batch-Screen."""
        if TDMSBatchScreen is None:
            QMessageBox.warning(self, "YarnScope Batch",
                                "YarnScope Batch nicht verfügbar – Import fehlgeschlagen.")
            return
        if self.tdms_batch is None:
            self.tdms_batch = TDMSBatchScreen(on_back_home=self._go_home)
            self.stack.addWidget(self.tdms_batch)
        self.setWindowTitle("TrippleT – YarnScope Batch")
        self.stack.setCurrentWidget(self.tdms_batch)

    def _go_nozzle_calculator(self):
        """Navigiert zum Nozzle ROI / Amortisations-Kalkulator."""
        if NozzleCalculatorScreen is None:
            QMessageBox.warning(self, "Jet Calculator",
                                "Jet Calculator nicht verfügbar – Import fehlgeschlagen.")
            return
        if self.nozzle_calculator is None:
            self.nozzle_calculator = NozzleCalculatorScreen(
                on_back_home=self._go_home,
                jets_loader=self._load_jets_data,
            )
            self.stack.addWidget(self.nozzle_calculator)
        self.setWindowTitle("TrippleT – Jet ROI Calculator")
        self.stack.setCurrentWidget(self.nozzle_calculator)

    def _go_air_supply(self):
        """Navigiert zum Air Supply Network Calculator."""
        if AirSupplyScreen is None:
            QMessageBox.warning(self, "Air Supply",
                                "Air Supply Calculator nicht verfügbar – Import fehlgeschlagen.")
            return
        if self.air_supply is None:
            username = ""
            if self.current_user:
                username = (self.current_user.get("username")
                            or self.current_user.get("Username") or "")
            self.air_supply = AirSupplyScreen(
                on_back_home=self._go_home,
                jets_loader=self._load_jets_data,
                username=username,
            )
            self.stack.addWidget(self.air_supply)
        self.setWindowTitle("TrippleT – Air Supply Network Calculator")
        self.stack.setCurrentWidget(self.air_supply)


    def _open_quick_search(self):
        """Öffnet den Quick-Search-Dialog (Ctrl+F / 🔍-Button)."""
        try:
            # Prevent double-open
            if getattr(self, "_qs_dlg", None) is not None:
                try:
                    if self._qs_dlg.isVisible():
                        self._qs_dlg.activateWindow()
                        return
                except Exception:
                    pass
            dlg = QuickSearchDialog(self)
            dlg.open_experiment.connect(self._go_show_experiment)
            dlg.finished.connect(lambda: setattr(self, "_qs_dlg", None))
            self._qs_dlg = dlg
            dlg.show()
        except Exception:
            pass



    def _go_change_pw(self, username: str):
        """Öffnet den Passwort-Änderungs-Screen für den gegebenen Benutzernamen."""
        self.change_pw.set_user(username)
        self.setWindowTitle("TrippleT – Change Password")
        self.stack.setCurrentWidget(self.change_pw)

    def _back_to_login(self):
        """Loggt den aktuellen Benutzer aus und navigiert zurück zum Login-Screen."""
        self.setWindowTitle("TrippleT – Log In")
        self.stack.setCurrentWidget(self.login)

    def _go_all_experiments(self):
        """Navigiert zum AllExperiments-Screen."""
        self.setWindowTitle("TrippleT – All Experiments")
        # Tabelle beim Öffnen immer mit aktuellem User-Kontext neu laden,
        # damit insbesondere die Status-Dropdowns den Superuser-Status beachten.
        try:
            maschine_id = self.all_experiments._filter_map.get(
                self.all_experiments._active_filter, None
            )
        except Exception:
            maschine_id = None
        try:
            self.all_experiments._load_data(maschine_id)
        except Exception:
            pass
        self.stack.setCurrentWidget(self.all_experiments)

    def _title_for_mode(self, mode: str) -> str:
        """Gibt den Fenstertitel für einen Experiment-Modus zurück (create/edit/copy)."""
        mode = (mode or "create").lower()
        if mode == "addseries":
            return "TrippleT – Add Trial Series"
        if mode == "addtrials":
            return "TrippleT – Add Trials"
        if mode == "addlabmachines":
            return "TrippleT – Add Lab Machines to Trials"
        return "TrippleT – Create Experiment"

    def _dispose_old_create_screen(self):
        """Entfernt und löscht den alten CreateExperiment-Screen aus dem Stack."""
        if self._create_screen_ref is not None:
            try:
                self.stack.removeWidget(self._create_screen_ref)
                self._create_screen_ref.deleteLater()
            except Exception:
                pass
            finally:
                self._create_screen_ref = None

    def _show_request_preview_dialog(self):
        """Öffnet den Request-Preview-Dialog mit Navigation und «Create Experiment»-Button."""
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                                        QPushButton, QLabel, QFrame, QScrollArea,
                                        QSizePolicy, QWidget)
        from PySide6.QtCore import Qt
        from db.connection import fetch_all

        # ── Lade alle genehmigten Requests ──────────────────────────────
        try:
            rows = fetch_all(
                "SELECT * FROM [tblExperimentRequests] WHERE [RequestStatus] = 3 ORDER BY [ID] DESC",
                []
            )
        except Exception:
            rows = []

        if not rows:
            self._go_create_experiment("create")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Pending Experiment Requests")
        dlg.setModal(True)
        dlg.setMinimumWidth(820)
        dlg.setMinimumHeight(440)
        root = QVBoxLayout(dlg)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 12)

        # ── Navigation header ────────────────────────────────────────────
        nav_row = QHBoxLayout()
        lbl_counter = QLabel()
        lbl_counter.setAlignment(Qt.AlignCenter)
        lbl_counter.setStyleSheet("font-weight:600; font-size:13px;")
        btn_prev = QPushButton("<")
        btn_next = QPushButton(">")
        for b in (btn_prev, btn_next):
            b.setFixedWidth(36)
            b.setFixedHeight(28)
            b.setObjectName("GreyBtn")
        nav_row.addWidget(btn_prev)
        nav_row.addWidget(lbl_counter, 1)
        nav_row.addWidget(btn_next)
        root.addLayout(nav_row)

        # ── Detail area ──────────────────────────────────────────────────
        # Left: fields  |  Right: image viewer
        body_row = QHBoxLayout()
        body_row.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setSpacing(6)
        detail_layout.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(detail_widget)
        body_row.addWidget(scroll, 1)

        # Image panel (right side)
        from PySide6.QtGui import QPixmap
        img_panel = QFrame()
        img_panel.setFrameShape(QFrame.StyledPanel)
        img_panel.setFixedWidth(220)
        img_lay = QVBoxLayout(img_panel)
        img_lay.setContentsMargins(4, 4, 4, 4)
        img_lay.setSpacing(4)

        img_lbl = QLabel()
        img_lbl.setFixedSize(212, 180)
        img_lbl.setAlignment(Qt.AlignCenter)
        img_lbl.setStyleSheet("background:#f0f0f0; border:1px solid #ddd; border-radius:4px;")
        img_lbl.setText("No images")

        img_nav = QHBoxLayout()
        btn_img_prev = QPushButton("<")
        btn_img_next = QPushButton(">")
        img_counter = QLabel()
        img_counter.setAlignment(Qt.AlignCenter)
        img_counter.setStyleSheet("font-size:10px; color:#666;")
        for b in (btn_img_prev, btn_img_next):
            b.setFixedSize(36, 28)
            b.setStyleSheet(
                "QPushButton { font-size:14px; font-weight:700; "
                "background:#e0e0e0; border:1px solid #bbb; border-radius:4px; }"
                "QPushButton:hover { background:#c8c8c8; }"
                "QPushButton:disabled { color:#bbb; }"
            )
        img_nav.addWidget(btn_img_prev)
        img_nav.addWidget(img_counter, 1)
        img_nav.addWidget(btn_img_next)

        img_orig_lbl = QLabel()
        img_orig_lbl.setWordWrap(True)
        img_orig_lbl.setStyleSheet("font-size:9px; color:#888;")
        img_orig_lbl.setAlignment(Qt.AlignCenter)

        img_lay.addWidget(img_lbl)
        img_lay.addLayout(img_nav)
        img_lay.addWidget(img_orig_lbl)
        img_lay.addStretch()

        body_row.addWidget(img_panel, 0)
        root.addLayout(body_row, 1)

        img_state = {"idx": 0, "images": []}

        # ── Buttons ──────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_create = QPushButton("Create Experiment")
        btn_create.setObjectName("PurpleBtn")
        btn_close = QPushButton("Close")
        btn_close.setObjectName("GreyBtn")
        btn_row.addStretch()
        btn_row.addWidget(btn_create)
        btn_row.addWidget(btn_close)
        root.addLayout(btn_row)
        btn_close.clicked.connect(dlg.reject)

        # ── State ────────────────────────────────────────────────────────
        state = {"idx": 0}

        EXCLUDE = {"ID", "Timestamp", "RequestStatus", "CreatedBy"}

        from db.connection import is_dev_mode as _is_dev
        IMAGE_BASE = (
            "C:\\ttt\\images\\ExperimentRequestImages"
            if _is_dev()
            else "H:\\Technik\\TrippleT\\ExperimentRequestImages"
        )

        def _show_image(i):
            images = img_state["images"]
            if not images:
                img_lbl.setText("No images")
                img_counter.setText("")
                img_orig_lbl.setText("")
                btn_img_prev.setEnabled(False)
                btn_img_next.setEnabled(False)
                return
            i = max(0, min(i, len(images) - 1))
            img_state["idx"] = i
            img_counter.setText(f"{i + 1} / {len(images)}")
            btn_img_prev.setEnabled(i > 0)
            btn_img_next.setEnabled(i < len(images) - 1)
            img = images[i]
            rel  = str(img.get("RelativePath") or "")
            stored = str(img.get("StoredFilename") or "")
            orig = str(img.get("OriginalFilename") or stored or "")
            img_orig_lbl.setText(orig)
            import os
            path = os.path.join(IMAGE_BASE, rel, stored) if rel else os.path.join(IMAGE_BASE, stored)
            px = QPixmap(path)
            if px.isNull():
                img_lbl.setText("Image not found")
                img_lbl.setStyleSheet("background:#f0f0f0; border:1px solid #ddd; border-radius:4px; color:#999;")
            else:
                img_lbl.setPixmap(px.scaled(212, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                img_lbl.setStyleSheet("background:#f0f0f0; border:1px solid #ddd; border-radius:4px;")

        btn_img_prev.clicked.connect(lambda: _show_image(img_state["idx"] - 1))
        btn_img_next.clicked.connect(lambda: _show_image(img_state["idx"] + 1))

        def _render(idx):
            # Clear previous
            while detail_layout.count():
                item = detail_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            row = rows[idx]
            lbl_counter.setText(f"Request {idx + 1} / {len(rows)}")
            btn_prev.setEnabled(idx > 0)
            btn_next.setEnabled(idx < len(rows) - 1)

            rid = row.get("ID") or row.get("id")

            # Load images for this request
            try:
                img_rows = fetch_all(
                    "SELECT [RelativePath],[StoredFilename],[OriginalFilename] "
                    "FROM [tblExperimentRequestImage] WHERE [ExperimentRequestID]=? "
                    "ORDER BY [ID]",
                    [rid]
                )
            except Exception:
                img_rows = []
            img_state["images"] = img_rows
            img_state["idx"] = 0
            _show_image(0)

            # Title row
            title_lbl = QLabel(f"Request ID: {rid}")
            title_lbl.setStyleSheet("font-weight:700; font-size:14px;")
            detail_layout.addWidget(title_lbl)

            sep = QFrame(); sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet("color:#ddd;")
            detail_layout.addWidget(sep)

            # All fields except excluded
            for key, val in row.items():
                if key in EXCLUDE or val in (None, ""):
                    continue
                row_w = QHBoxLayout()
                k_lbl = QLabel(str(key) + ":")
                k_lbl.setStyleSheet("color:#666; font-size:11px; min-width:160px;")
                k_lbl.setFixedWidth(160)
                v_lbl = QLabel(str(val))
                v_lbl.setWordWrap(True)
                v_lbl.setStyleSheet("font-size:11px;")
                row_w.addWidget(k_lbl)
                row_w.addWidget(v_lbl, 1)
                container = QWidget()
                container.setLayout(row_w)
                detail_layout.addWidget(container)

            detail_layout.addStretch()

            # Update create button
            try:
                btn_create.clicked.disconnect()
            except Exception:
                pass
            btn_create.clicked.connect(lambda _=False, r=rid: _on_create(r))

        def _on_create(rid):
            dlg.accept()
            self._go_create_experiment("create", preset_request_id=int(rid))

        def _go_prev():
            state["idx"] -= 1
            _render(state["idx"])

        def _go_next():
            state["idx"] += 1
            _render(state["idx"])

        btn_prev.clicked.connect(_go_prev)
        btn_next.clicked.connect(_go_next)

        _render(0)
        dlg.exec()

    def _go_create_experiment(self, mode: str = "create", existing_experiment_id: Optional[int] = None,
                               preset_request_id: Optional[int] = None):
        """Navigiert zum Experiment-Erstellen-Screen.

        Args:
            mode:                   "create", "edit" oder "copy".
            existing_experiment_id: Wird bei edit/copy gesetzt.
            preset_request_id:      Request-ID die im General-Tab vorselektiert werden soll.
        """
        self._dispose_old_create_screen()
        self.setWindowTitle(self._title_for_mode(mode))
        screen = CreateExperimentScreen(
            on_back_home=self._go_home,
            on_open_experiment=self._go_show_experiment,
            mode=mode,
            existing_experiment_id=existing_experiment_id,
        )
        self.stack.addWidget(screen)
        self.stack.setCurrentWidget(screen)
        self._create_screen_ref = screen
        if preset_request_id is not None:
            try:
                screen.preset_experiment_request(preset_request_id)
            except Exception:
                pass


    def _go_addtrials_from_experiment(self, exp_pk: int, series_pk: int, experiment_id: str):
        """Öffnet CreateExperimentScreen im addtrials-Modus mit Back → Show-Experiment."""
        self._dispose_old_create_screen()
        self.setWindowTitle("TrippleT – Add Trials")

        def _back_to_experiment():
            self._dispose_old_create_screen()
            self._go_show_experiment(exp_pk, series_pk, experiment_id)

        screen = CreateExperimentScreen(
            on_back_home=self._go_home,
            on_back_experiment=_back_to_experiment,
            on_open_experiment=self._go_show_experiment,
            mode="addtrials",
        )
        self.stack.addWidget(screen)
        self.stack.setCurrentWidget(screen)
        self._create_screen_ref = screen
        try:
            screen.open_addtrials_prefill(exp_pk, series_pk)
        except Exception:
            pass

    def _go_show_experiment(self, exp_pk: int, series_pk: int, experiment_id: str):
        """Navigiert zum ShowExperiment-Screen für ein bestimmtes Experiment.

        Args:
            exp_pk:        Primärschlüssel in tblExperimente.
            series_pk:     Primärschlüssel in tblTrialSeries.
            experiment_id: Lesbare ID (z.B. "2024-PG-001") für den Titel.
        """
        # Erst Screen aktivieren, dann laden – so bleibt Navigation auch bei Fehlern nachvollziehbar.
        self.setWindowTitle(f"TrippleT – Show Experiment {experiment_id}")
        self.stack.setCurrentWidget(self.show_experiment)

        # Report-Callback verdrahten
        self.show_experiment.on_open_report = self._go_report

        try:
            self.show_experiment.load_record(exp_pk, series_pk, experiment_id)
        except Exception as e:
            try:
                QMessageBox.critical(
                    self,
                    "Fehler beim Öffnen",
                    f"Experiment konnte nicht geöffnet werden.\n\n"
                    f"ExperimentID: {experiment_id}\n"
                    f"ExpPK: {exp_pk} / SeriesPK: {series_pk}\n\n"
                    f"{e}",
                )
            except Exception:
                pass

    def _go_report(self, series_pk: int) -> None:
        """Öffnet den Report-Screen für eine TrialSeries."""
        if self.report_screen is None:
            QMessageBox.warning(
                self, "Report",
                "Report nicht verfügbar – PySide6-WebEngine nicht installiert.\n\n"
                "Bitte ausführen: pip install PySide6-WebEngine"
            )
            return
        self.setWindowTitle("TrippleT – Smart Chart")
        self.report_screen.load_series(series_pk)
        self.stack.setCurrentWidget(self.report_screen)

    def _go_back_to_show_experiment(self) -> None:
        """Zurück von Report-Screen zu ShowExperiment."""
        self.setWindowTitle("TrippleT – Show Experiment")
        self.stack.setCurrentWidget(self.show_experiment)

    def _go_smartchart(self) -> None:
        """Öffnet Smart Chart im Visual SQL Modus (aus Home)."""
        if self.smartchart_screen is None:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Smart Chart",
                "Smart Chart nicht verfügbar – PySide6-WebEngine nicht installiert.")
            return
        self.setWindowTitle("TrippleT – Smart Chart")
        self.smartchart_screen.load_visual()
        self.stack.setCurrentWidget(self.smartchart_screen)

    def _open_experiment_from_all(self, exp_pk: int, series_pk: int, experiment_id: str):
        """Öffnet ein Experiment aus dem AllExperiments-Screen heraus."""
        """
        Öffnet ShowExperimentScreen aus dem AllExperiments-Screen.
        Der Zurück-Button geht danach wieder auf AllExperiments.
        """
        # Ziel für den Back-Button setzen
        try:
            self.show_experiment.on_back_all_experiments = self._go_all_experiments
        except Exception:
            pass
        self._go_show_experiment(exp_pk, series_pk, experiment_id)

    def _open_experiment_from_backlog(self, exp_pk: int, series_pk: int, experiment_id: str):
        """Öffnet ein Experiment aus dem Backlog-Screen heraus."""
        """
        Öffnet ShowExperimentScreen aus dem Backlog-Screen.
        Der Zurück-Button geht danach wieder auf den Backlog.
        """
        try:
            self.show_experiment.on_back_all_experiments = self._go_backlog
        except Exception:
            pass
        self._go_show_experiment(exp_pk, series_pk, experiment_id)

    def open_experiment_in_new_window(self, exp_pk: int, series_pk: int, experiment_id: str) -> None:
        """Öffnet ShowExperimentScreen in einem eigenständigen neuen Fenster (kein Stack)."""
        win = QMainWindow()
        win.setWindowTitle(f"TrippleT \u2013 {experiment_id}")
        win.setMinimumSize(1100, 700)

        screen_widget = ShowExperimentScreen(
            on_back_home=win.close,
            on_back_all_experiments=win.close,
        )
        screen_widget.on_open_report = lambda sp: self._go_report_in_new_window(sp, win)

        win.setCentralWidget(screen_widget)

        try:
            win.setStyleSheet(self.styleSheet())
        except Exception:
            pass

        try:
            geom = self.geometry()
            win.move(geom.x() + 40, geom.y() + 40)
        except Exception:
            pass

        win.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        win.showMaximized()

        try:
            screen_widget.load_record(exp_pk, series_pk, experiment_id)
        except Exception as e:
            QMessageBox.critical(win, "Error", f"Could not open experiment.\n\n{e}")

        if not hasattr(self, "_detached_windows"):
            self._detached_windows = []
        self._detached_windows.append(win)
        win.destroyed.connect(lambda: self._detached_windows.remove(win)
                              if win in self._detached_windows else None)
        win.closeEvent = self._make_detached_close_guard(win)

    def _go_report_in_new_window(self, series_pk: int, parent_win=None) -> None:
        """Öffnet den Report-Screen in einem neuen Fenster (aus detached ShowExperiment heraus)."""
        try:
            from ui.screen_report import ReportScreen as RS
        except ImportError:
            QMessageBox.warning(self, "Report",
                "Report nicht verfügbar – PySide6-WebEngine nicht installiert.")
            return
        win = QMainWindow()
        win.setWindowTitle("TrippleT \u2013 Smart Chart")
        win.setMinimumSize(1100, 700)
        try:
            win.setStyleSheet(self.styleSheet())
        except Exception:
            pass
        rscreen = RS(on_back=win.close, mode="series")
        win.setCentralWidget(rscreen)
        win.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        win.showMaximized()
        rscreen.load_series(series_pk)
        if not hasattr(self, "_detached_windows"):
            self._detached_windows = []
        self._detached_windows.append(win)
        win.destroyed.connect(lambda: self._detached_windows.remove(win)
                              if win in self._detached_windows else None)
        win.closeEvent = self._make_detached_close_guard(win)


    def _go_copy_trialseries(self, exp_pk: int, series_pk: int, experiment_id: str):
        """Öffnet den Erstellen-Screen im Copy-Modus für eine bestehende TrialSeries."""
        self._go_create_experiment(
            mode="addseries", existing_experiment_id=exp_pk)
        try:
            if hasattr(self, "_create_screen_ref") and self._create_screen_ref is not None:
                self._create_screen_ref.open_addseries_prefill(
                    exp_pk, series_pk)
        except Exception as e:
            QMessageBox.critical(self, "Copy TrialSeries",
                                 f"Vorbelegen fehlgeschlagen:\n{e}")
            return
        try:
            self.setWindowTitle(
                f"TrippleT – Copy TrialSeries from {experiment_id}")
        except Exception:
            pass
        self.stack.setCurrentWidget(self._create_screen_ref)

    def _go_add_yarn(self):
        """Navigiert zum ManageYarn-Screen."""
        try:
            Screen = ManageYarnScreen
        except NameError:
            Screen = None
        if Screen is None:
            QMessageBox.information(
                self, "Manage Yarn", "'Manage Yarn' ist derzeit nicht verfügbar."
            )
            return
        try:
            if not hasattr(self, 'manage_yarn') or self.manage_yarn is None:
                self.manage_yarn = Screen(on_back_home=self._go_home)
                self.stack.addWidget(self.manage_yarn)
            self.setWindowTitle("TrippleT – Manage Yarn")
            self.stack.setCurrentWidget(self.manage_yarn)
        except Exception as e:
            QMessageBox.critical(self, "Manage Yarn",
                                 f"Fehler beim Öffnen: {e}")

    def _go_yarn_stock(self):
        """Navigiert zum Yarn-Stock-Screen (Garnlager)."""
        try:
            Screen = YarnStockScreen
        except NameError:
            Screen = None
        if Screen is None:
            QMessageBox.information(
                self, "Yarn Stock", "'Yarn Stock' ist derzeit nicht verfügbar."
            )
            return
        try:
            if not hasattr(self, 'yarn_stock') or self.yarn_stock is None:
                self.yarn_stock = Screen(on_back_home=self._go_home)
                self.stack.addWidget(self.yarn_stock)
            else:
                self.yarn_stock.reload_data()
            self.setWindowTitle("TrippleT – Yarn Stock")
            self.stack.setCurrentWidget(self.yarn_stock)
        except Exception as e:
            QMessageBox.critical(self, "Yarn Stock",
                                 f"Fehler beim Öffnen: {e}")

    def _go_yarn_stock_from_notification(self, yarn_id: int, charge: str):
        """Von einer Low-Stock-Notification aus: zu Yarn Stock navigieren
        und direkt zur betroffenen Garn/Batch-Zeile springen."""
        self._go_yarn_stock()
        try:
            if hasattr(self, "yarn_stock") and self.yarn_stock is not None:
                found = self.yarn_stock.goto_yarn_batch(yarn_id, charge)
                if not found:
                    QMessageBox.information(
                        self, "Yarn Stock",
                        "Diese Garn/Batch-Kombination wurde nicht gefunden "
                        "(evtl. inzwischen aufgefüllt oder Batch geändert)."
                    )
        except Exception as e:
            QMessageBox.critical(self, "Yarn Stock", f"Fehler beim Springen: {e}")

    def _go_add_user(self):
        self.setWindowTitle("TrippleT – Manage User")
        self.stack.setCurrentWidget(self.manage_user)

    def _go_add_jet(self):
        self.setWindowTitle("TrippleT – Manage Jets")
        self.manage_jets.reload_data()
        self.stack.setCurrentWidget(self.manage_jets)

    def _go_add_top_plate(self):
        self.setWindowTitle("TrippleT – Manage Top Plates")
        self.manage_top_plates.reload_data()
        self.stack.setCurrentWidget(self.manage_top_plates)

    def _go_manage_order_type(self):
        self.setWindowTitle("TrippleT – Manage Order Type")
        self.stack.setCurrentWidget(self.manage_order_type)

    def _go_manage_product_groups(self):
        self.setWindowTitle("TrippleT – Manage Product Groups")
        self.stack.setCurrentWidget(self.manage_product_groups)

    def _go_manage_material(self):
        self.setWindowTitle("TrippleT – Manage Material")
        self.stack.setCurrentWidget(self.manage_material)

    def _go_back_manage_jets(self):
        self.setWindowTitle("TrippleT – Manage Jets")
        self.stack.setCurrentWidget(self.manage_jets)

    def _go_new_jet(self):
        try:
            # Falls vorher "Edit in Form" benutzt wurde, hängen dort noch
            # die Update-Callbacks für die alte Jet-ID -- zurücksetzen,
            # sonst überschreibt "Save" den zuletzt bearbeiteten Jet.
            self.new_jet._on_save = self._insert_jet_full
            self.new_jet._on_created = self._on_new_jet_created
            self.new_jet._check_jet_name = self._is_jet_name_available
            self.new_jet.btn_save.setText("Save Jet")
            self.new_jet.reset_form()
        except Exception:
            pass
        self.setWindowTitle("TrippleT – New Jet")
        self.stack.setCurrentWidget(self.new_jet)

    def _go_copy_new_jet(self, row: Dict):
        try:
            self.new_jet._on_save = self._insert_jet_full
            self.new_jet._on_created = self._on_new_jet_created
            self.new_jet._check_jet_name = self._is_jet_name_available
            self.new_jet.btn_save.setText("Save Jet")
            self.new_jet.load_from_row(row, clear_jet=True)
        except Exception:
            try:
                self.new_jet.reset_form()
            except Exception:
                pass
        self.setWindowTitle("TrippleT – New Jet")
        self.stack.setCurrentWidget(self.new_jet)

    def _go_edit_jet_form(self, row: Dict):
        """Öffnet den NewJetScreen zum Bearbeiten eines bestehenden Jets (wie Copy, aber clear_jet=False und UPDATE)."""
        id_col = self._jets_id_col or "ID"
        jet_id = row.get(id_col)

        def _update_save(data: Dict) -> int:
            data[id_col] = jet_id
            self._save_jets_changes([data])
            return jet_id

        def _on_saved(_new_id=None):
            try:
                self.manage_jets.reload_data(select_id=jet_id)
            except Exception:
                pass
            self._go_back_manage_jets()

        try:
            self.new_jet._on_save = _update_save
            self.new_jet._on_created = _on_saved
            self.new_jet._check_jet_name = None
            self.new_jet.load_from_row(row, clear_jet=False)
        except Exception:
            pass

        # Button-Text anpassen
        try:
            self.new_jet.btn_save.setText("Save Changes")
        except Exception:
            pass

        self.setWindowTitle(f"TrippleT – Edit Jet")
        self.stack.setCurrentWidget(self.new_jet)

    def _on_new_jet_created(self, new_id: int):
        try:
            self.manage_jets.reload_data(select_id=new_id)
        except Exception:
            pass
        self._go_back_manage_jets()

    def _go_back_manage_top_plates(self):
        self.setWindowTitle("TrippleT – Manage Top Plates")
        self.stack.setCurrentWidget(self.manage_top_plates)

    def _go_new_top_plate(self):
        try:
            # Falls vorher "Edit in Form" benutzt wurde, hängen dort noch
            # die Update-Callbacks für die alte Top-Plate-ID -- zurücksetzen,
            # sonst überschreibt "Save" die zuletzt bearbeitete Top Plate.
            self.new_top_plate._on_save = self._insert_top_plate_full
            self.new_top_plate._on_created = self._on_new_top_plate_created
            self.new_top_plate._check_top_plate_name = self._is_top_plate_name_available
            self.new_top_plate.btn_save.setText("Save Top Plate")
            self.new_top_plate.reset_form()
        except Exception:
            pass
        self.setWindowTitle("TrippleT – New Top Plate")
        self.stack.setCurrentWidget(self.new_top_plate)

    def _go_copy_new_top_plate(self, row: Dict):
        try:
            self.new_top_plate._on_save = self._insert_top_plate_full
            self.new_top_plate._on_created = self._on_new_top_plate_created
            self.new_top_plate._check_top_plate_name = self._is_top_plate_name_available
            self.new_top_plate.btn_save.setText("Save Top Plate")
            self.new_top_plate.load_from_row(row, clear_name=True)
        except Exception:
            try:
                self.new_top_plate.reset_form()
            except Exception:
                pass
        self.setWindowTitle("TrippleT – New Top Plate")
        self.stack.setCurrentWidget(self.new_top_plate)

    def _go_edit_top_plate_form(self, row: Dict):
        """Öffnet den NewTopPlateScreen zum Bearbeiten einer bestehenden Top Plate (wie Copy, aber clear_name=False und UPDATE)."""
        id_col = self._top_plates_id_col or "ID"
        top_plate_id = row.get(id_col)

        def _update_save(data: Dict) -> int:
            data[id_col] = top_plate_id
            self._save_top_plates_changes([data])
            return top_plate_id

        def _on_saved(_new_id=None):
            try:
                self.manage_top_plates.reload_data(select_id=top_plate_id)
            except Exception:
                pass
            self._go_back_manage_top_plates()

        try:
            self.new_top_plate._on_save = _update_save
            self.new_top_plate._on_created = _on_saved
            self.new_top_plate._check_top_plate_name = None
            self.new_top_plate.load_from_row(row, clear_name=False)
        except Exception:
            pass

        # Button-Text anpassen
        try:
            self.new_top_plate.btn_save.setText("Save Changes")
        except Exception:
            pass

        self.setWindowTitle(f"TrippleT – Edit Top Plate")
        self.stack.setCurrentWidget(self.new_top_plate)

    def _on_new_top_plate_created(self, new_id: int):
        try:
            self.manage_top_plates.reload_data(select_id=new_id)
        except Exception:
            pass
        self._go_back_manage_top_plates()

    def _logout(self):
        # Reset global user context
        app_meta.current_user = {
            "id": None,
            "username": None,
            "first_name": None,
            "last_name": None,
            "access_level": 0,
            "access_right": None,
            "admin_box": False,
        }
        try:
            self.current_user = None
            if hasattr(self, 'login') and self.login is not None:
                try:
                    self.login.reset_login_fields()
                except Exception:
                    pass
            if self.home is not None:
                try:
                    self.stack.removeWidget(self.home)
                    self.home.deleteLater()
                except Exception:
                    pass
                finally:
                    self.home = None
        finally:
            self._back_to_login()


def main():
    # Stab-Modelle im Hintergrund synchronisieren (H: → lokal, non-blocking)
    try:
        from ui.yarnscope.dty_analysis import sync_models_async
        sync_models_async()
    except Exception:
        pass

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)
    # App/Icon: Windows Taskbar zeigt oft nur dann ein Icon, wenn
    # (a) ein gültiges QIcon gesetzt ist UND
    # (b) das MainWindow ebenfalls ein Icon hat.
    # Zudem kann beim Packaging (PyInstaller) die .ico fehlen – darum Fallbacks.
    icon_candidates = [
        "assets/icons/tricolour_black_mini.ico",
        "assets/icons/tricolour_mini.ico",
        "assets/icons/t3_logo_mini.ico",
        "assets/icons/t3_logo_mini.png",
        "assets/icons/tricolour.png",
        "assets/tricolour.png",
        "tricolour.png",
    ]
    icon_obj = QIcon()
    for rel in icon_candidates:
        p = resource_path(rel)
        if p and os.path.exists(p):
            icon_obj = QIcon(p)
            break
    if not icon_obj.isNull():
        app.setWindowIcon(icon_obj)

    # Optional: explizite AppUserModelID hilft unter Windows, dass Taskbar-Icon/Grouping sauber ist.
    try:
        import ctypes  # type: ignore

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TrippleT")
    except Exception:
        pass
    win = MainWindow()
    # Windows Taskbar nimmt häufig das Window-Icon – darum nochmals setzen.
    try:
        if not app.windowIcon().isNull():
            win.setWindowIcon(app.windowIcon())
    except Exception:
        pass
    win.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()