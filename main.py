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
import datetime
from typing import List, Dict, Tuple, Optional

# --- Crash-Log: als allererstes installiert, noch vor allen weiteren
# Imports/Modul-Top-Level-Code, damit auch Fehler beim Import selbst
# (z.B. fehlendes gebundeltes Modul/Asset in der .exe) sichtbar werden.
# In der gebauten .exe (console=False) geht sonst jede unbehandelte
# Exception spurlos verloren - kein Fenster, kein Fehler, nichts.
def _crash_log_path() -> str:
    try:
        base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, "crash_log.txt")
    except Exception:
        return "crash_log.txt"


def _log_crash(exc_type, exc_value, exc_tb) -> None:
    import traceback
    try:
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        with open(_crash_log_path(), "a", encoding="utf-8") as f:
            f.write(f"\n--- {datetime.datetime.now().isoformat()} ---\n")
            f.write(msg)
    except Exception:
        pass
    try:
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    except Exception:
        pass


sys.excepthook = _log_crash

from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QMessageBox, QVBoxLayout, QWidget, QInputDialog
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QTimer

# --- DB-Modus wählen (nur im Quellcode-Start, NICHT in der gebauten .exe) ---
# Muss vor jedem Import passieren, der db.connection lädt (u.a. ui.theme, ui.screen_login).
# In der gefrorenen .exe (PyInstaller) läuft TrippleT immer im prod-Modus, mit
# einer gezielten Ausnahme für TRIPPLET_MODE=offline (siehe db/connection.py) -
# ausgelöst über einen separaten Shortcut/Wrapper-Skript für die Superuser,
# die offline arbeiten dürfen (echte Zugriffskontrolle ist der AccessLevel-
# Check nach dem Login, siehe _on_login_success() unten, nicht dieser Trigger).
# offline_prod/offline_dev_local (dev/testing only, source-run only - see
# db/connection.py._offline_sqlite_path()) replace the plain "offline" entry
# here: each keeps its own persisted local snapshot (one sourced from prod,
# one from dev_local), so switching which backend you're testing offline
# against doesn't silently overwrite the other. The real, deployed field
# flow (TrippleT_Launcher_Offline.bat) still uses plain TRIPPLET_MODE=offline
# directly - unaffected, this dialog only runs for source starts.
if not getattr(sys, "frozen", False) and not os.environ.get("TRIPPLET_MODE"):
    _mode_app = QApplication.instance() or QApplication(sys.argv)
    _mode, _ok = QInputDialog.getItem(
        None,
        "TrippleT – DB-Modus",
        "Gegen welche Datenbank soll gestartet werden?",
        ["prod", "dev", "dev_local", "offline_prod", "offline_dev_local"],
        0,
        False,
    )
    if not _ok:
        sys.exit(0)
    os.environ["TRIPPLET_MODE"] = _mode

_OFFLINE_MODES = {"offline", "offline_prod", "offline_dev_local"}

# Welcher Modus tatsächlich aktiv sein wird - spiegelt db/connection.py's
# eigene frozen-Gate-Logik, damit der "Kopie vorbereitet?"-Check unten sowohl
# über den Source-Dialog oben als auch über eine gefrorene .exe greift, die
# via Offline-Shortcut mit TRIPPLET_MODE=offline gestartet wurde. Die Dev-
# Varianten (offline_prod/offline_dev_local) sind für die .exe nicht erlaubt
# (siehe db/connection.py) - fallen dort auf prod zurück wie jeder andere
# unerlaubte Wert auch.
_resolved_mode = os.environ.get("TRIPPLET_MODE", "prod")
if getattr(sys, "frozen", False) and _resolved_mode != "offline":
    _resolved_mode = "prod"

if _resolved_mode in _OFFLINE_MODES:
    # Offline braucht eine bereits vorbereitete Kopie (kann sich nicht selbst
    # erzeugen - dafür fehlt ja gerade die MySQL-Quelle). Siehe
    # ui/screen_offline_sync.py ("1. Prepare/refresh") für den Vorbereitungsschritt.
    _mode_app = QApplication.instance() or QApplication(sys.argv)
    from db.connection import get_offline_sqlite_path
    _offline_path = get_offline_sqlite_path()
    if not os.path.exists(_offline_path):
        # Which online mode actually fills THIS file (see
        # db/connection.py._offline_sqlite_path()) - "offline"/"offline_prod"
        # both read the prod-sourced file, so both point back at prod here.
        _prep_mode = "dev_local" if _resolved_mode == "offline_dev_local" else "prod"
        QMessageBox.critical(
            None,
            "TrippleT – Offline-Modus",
            "Es wurde noch keine Offline-Kopie vorbereitet.\n\n"
            f"Bitte zuerst online starten ({_prep_mode}) und unter "
            "Home → Offline Sync eine Kopie vorbereiten.\n\n"
            f"Erwarteter Pfad:\n{_offline_path}",
        )
        sys.exit(0)
    QMessageBox.information(
        None,
        "TrippleT – Offline-Modus",
        "Der Offline-Modus ist aktuell nur für einen Teil der App getestet:\n"
        "• Neues Trial anlegen\n"
        "• Neues Garn / neue Düse anlegen\n"
        "• Laborergebnisse anlegen/bearbeiten (ATY, Titer, Statimat, EKB, "
        "ITEMAT, DTYoMat, Rapid600, Jet Air Consumption, Schrumpf-Tabs, Waterbath)\n\n"
        "Andere Bereiche (Backlog, Notifications, Reports, Requirement Hub, "
        "Smart Chart, ...) sind noch nicht offline getestet und können "
        "Fehler zeigen, weil die zugehörigen Tabellen nicht Teil der "
        "Offline-Kopie sind.\n\n"
        "Offline-Modus ist aktuell nur für Superuser freigeschaltet - das "
        "wird nach dem Login geprüft.",
    )

from ui.theme import APP_QSS, build_qss, set_accent
from ui.widgets.tab_container import TabbedNavigator, _StackFacade
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
from ui.screen_usage_stats import UsageStatsScreen
from ui.screen_stats_suite import StatsSuiteScreen
from ui.screen_offline_sync import OfflineSyncScreen
from ui.screen_lab_assistant import LabAssistantScreen
from ui.screen_tdms_inspector import TdmsInspectorScreen
from ui.offline_autosnapshot import IdleSnapshotManager
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
    from ui.screen_label_generator import LabelGeneratorScreen
except Exception as _label_gen_err:
    print(f"[LabelGenerator] Import fehler: {_label_gen_err}")
    LabelGeneratorScreen = None

try:
    from ui.screen_air_supply import AirSupplyScreen
except Exception as _air_err:
    print(f"[AirSupply] Import fehler: {_air_err}")
    AirSupplyScreen = None

from ui.screen_quick_search import QuickSearchDialog
try:
    from ui.screen_manage_yarn import (
        ManageYarnScreen, load_garntyp_map, load_material_map, load_yarngroup_map, load_colour_map,
        quick_add_colour, find_duplicate_yarn, confirm_save_despite_duplicate,
    )
except Exception:
    ManageYarnScreen = None
    load_garntyp_map = load_material_map = load_yarngroup_map = load_colour_map = quick_add_colour = None
    find_duplicate_yarn = confirm_save_despite_duplicate = None
try:
    from ui.screen_new_yarn import NewYarnScreen
except Exception:
    NewYarnScreen = None
try:
    from ui.screen_yarn_stock import YarnStockScreen
except Exception:
    YarnStockScreen = None

from db.connection import fetch_all, execute, execute_insert, new_global_id, is_offline_mode
from ui.pathutil import resource_path
import app_meta


def _canon(s: str) -> str:
    """Normalisiert Spaltennamen für tolerante Vergleiche."""
    return str(s).strip().strip("[]`").replace(" ", "").lower()


def _require_admin_box_write():
    """Defense-in-depth guard for Admin-card write paths (Jets/Top Plates/Yarn/
    Order Type/Product Groups/Material). The screens themselves already disable
    their New/Copy/Delete/Save UI for read-only users (AdminBox=0, AccessLevel<3)
    — this catches any write call that reaches here despite that, e.g. via a
    stale/bypassed UI state."""
    if not app_meta.can_use_admin_box():
        raise PermissionError(
            "Read-only access: you don't have permission to modify this table.")


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
    def setWindowTitle(self, title: str) -> None:
        """Überschrieben, damit JEDER Titel-Aufruf synchron an die Tabs-
        Logik gemeldet wird (siehe ui/widgets/tab_container.py::
        TabbedNavigator.notify_title_set()) - das ist die Grundlage dafür,
        dass ein Tab-Titel korrekt zugeordnet wird, egal ob eine
        `_go_X()`-Methode setWindowTitle() vor oder nach dem Stack-/Tab-
        Wechsel aufruft (z.B. ShowExperimentScreen.load_record() setzt ihn
        NACH dem Wechsel). `getattr(..., None)`-Guard, da `self.setWindowTitle(...)`
        bereits vor `self._tabs`-Konstruktion aufgerufen wird (initialer
        Login-Titel)."""
        super().setWindowTitle(title)
        tabs = getattr(self, "_tabs", None)
        if tabs is not None:
            tabs.notify_title_set(title)

    # -->-->-->- Shared sidebar-navigation callback wiring -->-->-->-
    def _sidebar_nav_kwargs(self, include_all_experiments: bool = True, include_logout: bool = True,
                             include_open_backlog: bool = True) -> dict:
        """Baut das Callback-Kwargs-Dict für die Sidebar-Navigation
        (ui/widgets/sidebar_nav.py), identisch zu dem, was `self.backlog =
        BacklogScreen(...)` schon inline übergibt - als gemeinsamer Helper,
        damit jeder Sidebar-Screen (seit 2026-08-27 App-weit ausgerollt,
        siehe CLAUDE.md) dieselbe Verdrahtung nicht einzeln duplizieren muss.

        `include_all_experiments=False` für AllExperimentsScreen selbst -
        der Screen setzt seinen eigenen "All Experiments"-Sidebar-Eintrag
        intern fest auf None (kein Sprungziel auf sich selbst, siehe
        screen_all_experiments.py::_refresh_sidebar()) und nimmt daher gar
        keinen on_all_experiments-Konstruktorparameter entgegen.

        `include_open_backlog=False` analog für BacklogScreen selbst (auch
        dessen eigener "Backlog"-Sidebar-Eintrag wird intern per
        hide_self_link="backlog" unterdrückt statt über ein
        Konstruktor-Kwarg - BacklogScreen.__init__() kennt `on_open_backlog`
        daher gar nicht, siehe _open_backlog_in_new_tab()).

        `include_logout=False` für Fälle, in denen kein Log-Out-Zugriff
        gewollt ist.

        Für Screens mit exploded-benannten Konstruktor-Kwargs (Home/Backlog/
        AllExperiments/ShowExperiment, historisch zuerst gebaut) wird dieses
        Dict per `**` entpackt; neuere Screens nehmen es stattdessen direkt
        als ein einzelnes `sidebar_callbacks: dict`-Argument entgegen (siehe
        z.B. screen_manage_jets.py) - beide Konstruktor-Stile lesen letztlich
        dieselben Keys, nur der Übergabeweg unterscheidet sich.
        """
        kwargs = dict(
            on_create_experiment=lambda: self._go_create_experiment("create"),
            on_create_experiment_legacy=lambda: self._go_create_experiment("legacy"),
            on_add_series=lambda: self._go_create_experiment("addseries"),
            on_add_lab_machines=lambda: self._go_create_experiment("addlabmachines"),
            on_open_experiment_request=self._go_experiment_request,
            on_create_experiment_request=self._go_create_experiment_request,
            on_open_my_requests=self._go_my_requests,
            on_preview_requests=self._show_request_preview_dialog,
            on_preview_open_requests=lambda: self._show_request_preview_dialog(
                status=1, title="Open Experiment Requests"),
            on_image_compare=self._go_image_compare,
            on_canvas=self._go_canvas,
            on_nozzle_calculator=self._go_nozzle_calculator,
            on_air_supply=self._go_air_supply,
            on_requirement_hub=self._go_requirement_hub,
            on_smartchart=self._go_smartchart,
            on_yarn_stock=self._go_yarn_stock,
            on_label_generator=self._go_label_generator,
            on_tdms_inspector=self._go_tdms_inspector,
            on_add_jet=self._go_add_jet,
            on_add_top_plate=self._go_add_top_plate,
            on_add_yarn=self._go_add_yarn,
            on_manage_order_type=self._go_manage_order_type,
            on_manage_product_groups=self._go_manage_product_groups,
            on_manage_material=self._go_manage_material,
            on_add_user=self._go_add_user,
            on_usage_stats=self._go_usage_stats,
            on_statistics=self._go_statistics,
            on_offline_sync=self._go_offline_sync,
            on_lab_assistant=self._go_lab_assistant,
        )
        if include_all_experiments:
            kwargs["on_all_experiments"] = self._go_all_experiments
        if include_open_backlog:
            kwargs["on_open_backlog"] = self._go_backlog
        if include_logout:
            kwargs["on_logout"] = self._logout
        kwargs["open_in_new_tab"] = self._open_in_new_tab_dispatch
        return kwargs

    def _open_in_new_tab_dispatch(self, on_click):
        """Ctrl+Klick auf einen Sidebar-Eintrag (siehe ui/widgets/
        sidebar_nav.py::_wire_tab_capable_click()): für Backlog/All
        Experiments (die einzigen Sidebar-Ziele, die tatsächlich mehrfach
        unabhängig offen sein sollen, siehe _fresh_tab_targets) eine
        FRISCHE Instanz bauen statt der generischen Fokus-statt-Duplikat-
        Logik von TabbedNavigator.open_in_new_tab()."""
        fresh = self._fresh_tab_targets.get(on_click)
        if fresh is not None:
            fresh()
        else:
            self._tabs.open_in_new_tab(on_click)

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

    def _confirm_quit_dialog(self, parent, tab_count: int = 1) -> bool:
        """Shows the quit-confirmation dialog. Returns True if the user
        confirmed they want to close (and thus quit TrippleT). Tab-aware
        (Nutzervorgabe 2026-08-27: "wenn ich das tool schliesse und es sind
        mehr als eine registerkarte offen, bekomm ich eine warnung, sonst
        nicht mehr") - with more than one tab open, the message warns about
        losing those tabs; otherwise it falls back to the original "last
        window" wording (still relevant for detached windows, if any)."""
        if tab_count > 1:
            message = (
                f"You have {tab_count} tabs open.\n"
                "Closing this window will close all of them.\n\n"
                "Do you really want to quit?"
            )
        else:
            message = (
                "This is the last open TrippleT window.\n"
                "Closing it will exit the application.\n\n"
                "Do you really want to quit?"
            )
        reply = QMessageBox.question(
            parent,
            "Close TrippleT",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def closeEvent(self, event):
        """Fragt vor dem Schliessen des Hauptfensters nach Bestätigung, falls
        entweder mehr als ein Tab offen ist oder es das letzte offene
        TrippleT-Fenster wäre (beides würde beim Schliessen stillschweigend
        verloren gehen/die App beenden). Genau ein Tab und keine losgelösten
        Fenster → keine Nachfrage mehr."""
        tab_count = self._tabs.count() if getattr(self, "_tabs", None) is not None else 1
        other_windows_open = self._open_window_count(exclude=self) > 0
        if tab_count > 1 or other_windows_open:
            if not self._confirm_quit_dialog(self, tab_count=tab_count):
                event.ignore()
                return
        super().closeEvent(event)

    def _set_create_experiment_request_screen(self, request_id=None, on_back=None):
        """Erstellt oder ersetzt den CreateExperimentRequest-Screen (lazy init).

        Wird neu erstellt wenn der Screen noch nicht existiert oder request_id sich geändert hat.

        `on_back`: wohin der "←"-Chip zurückführt - Default ist der
        Experiment-Request-Hub (Neuanlage-Fall), `_go_edit_experiment_request()`
        übergibt hier `_go_my_requests` (Bearbeiten kommt immer von dort,
        siehe dortiger Aufrufer-Kommentar).
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
            on_back_experiment_request=on_back or self._go_experiment_request,
            request_id=request_id,
            sidebar_callbacks=self._sidebar_nav_kwargs(),
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
        # Bearbeiten wird ausschliesslich von "My Requests" aus geoeffnet
        # (siehe on_open_request=self._go_edit_experiment_request oben) - der
        # "←"-Chip soll deshalb dorthin zurueckfuehren, nicht auf den Hub
        # (Nutzerwunsch 2026-08-27: "sollte mich zurück zu my requests
        # bringen, nicht auf die neue übersicht").
        self._set_create_experiment_request_screen(request_id=request_id, on_back=self._go_my_requests)
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

        # Browser-artige Tabs (gebaut 2026-08-27, Nutzerwunsch: "wenn ich aus
        # dem sidepanel etwas anklicke mit gehaltener ctrl taste, wird eine
        # neue registerkarte mit dem screen geöffnet"; reaktiviert 2026-08-27
        # morgens, mit Backlog/All Experiments zusätzlich zu Show Experiment
        # als "echt mehrfach offen"-fähige Screens - siehe
        # _open_backlog_in_new_tab()/_open_all_experiments_in_new_tab()).
        # `self.stack` ist eine `_StackFacade`, die live auf den Stack des
        # jeweils AKTIVEN Tabs zeigt (siehe ui/widgets/tab_container.py) -
        # dadurch bleiben die ~100 bestehenden `self.stack.X(...)`-
        # Aufrufstellen unverändert.
        self._tabs = TabbedNavigator()
        self._tabs.set_title_provider(self.windowTitle, self.setWindowTitle)
        self.setCentralWidget(self._tabs)
        self.stack = _StackFacade(self._tabs)
        # Siehe ui/widgets/sidebar_nav.py::_wire_tab_capable_click() - liest
        # das beim normalen (nicht Strg-)Klick auf einen Sidebar-Eintrag, um
        # einen gepinnten Vergleichs-Tab (siehe TabbedNavigator.
        # is_current_tab_pinned()) vor versehentlichem Ueberschreiben zu
        # schuetzen. Gleiches Registrierungs-Muster wie app_meta.
        # open_quick_search/refresh_bell.
        app_meta.is_active_tab_pinned = self._tabs.is_current_tab_pinned

        self.current_user = None
        self.home = None
        self.aty_batch = None

        # Sidebar-Ziele, die beim Ctrl+Klick eine FRISCHE, unabhängige
        # Instanz statt der generischen Fokus-statt-Duplikat-Singleton-
        # Logik bekommen (siehe _open_in_new_tab_dispatch()). Bound methods
        # sind über __self__/__func__ vergleich- und hashbar, ein
        # Dict-Lookup über spätere `self._go_backlog`-Referenzen funktioniert
        # daher zuverlässig.
        self._fresh_tab_targets = {
            self._go_backlog: self._open_backlog_in_new_tab,
            self._go_all_experiments: self._open_all_experiments_in_new_tab,
        }

        self.change_pw = ChangePasswordScreen(on_dismiss=self._back_to_login)
        self.all_experiments = AllExperimentsScreen(
            on_back_home=self._go_home,
            on_open_experiment=self._open_experiment_from_all,
            on_open_in_new_window=self._open_experiment_from_all_in_new_tab,
            on_open_in_new_os_window=self.open_experiment_in_new_window,
            on_copy_trialseries=self._go_copy_trialseries,
            on_open_report=self._go_report,
            can_review=False,
            **self._sidebar_nav_kwargs(include_all_experiments=False),
        )
        self.show_experiment = ShowExperimentScreen(
            on_back_home=self._go_home,
            on_add_trials=self._go_addtrials_from_experiment,
            **self._sidebar_nav_kwargs(),
        )
        self.report_screen    = ReportScreen(on_back=self._go_back_to_show_experiment, mode="series", sidebar_callbacks=self._sidebar_nav_kwargs()) if ReportScreen else None
        self.smartchart_screen = ReportScreen(on_back=self._go_home, mode="visual", sidebar_callbacks=self._sidebar_nav_kwargs()) if ReportScreen else None

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
            sidebar_callbacks=self._sidebar_nav_kwargs(),
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
            on_open_experiment=self._open_experiment_from_jets,
            sidebar_callbacks=self._sidebar_nav_kwargs(),
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
            sidebar_callbacks=self._sidebar_nav_kwargs(),
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
            sidebar_callbacks=self._sidebar_nav_kwargs(),
        )

        # Screens ohne spezielle Loader
        self.manage_user = ManageUserScreen(on_back_home=self._go_home, sidebar_callbacks=self._sidebar_nav_kwargs())
        self.manage_order_type = ManageOrderTypeScreen(
            on_back_home=self._go_home, sidebar_callbacks=self._sidebar_nav_kwargs())
        self.manage_product_groups = ManageProductGroupsScreen(
            on_back_home=self._go_home, sidebar_callbacks=self._sidebar_nav_kwargs())
        self.manage_material = ManageMaterialScreen(on_back_home=self._go_home, sidebar_callbacks=self._sidebar_nav_kwargs())
        self.usage_stats = UsageStatsScreen(on_back_home=self._go_home, sidebar_callbacks=self._sidebar_nav_kwargs())
        # stats_suite/offline_sync: lazy (built on first navigation, not here).
        # Beide sind ohnehin nur fuer Superuser erreichbar (_go_statistics/
        # _go_offline_sync), und stats_suite baut eagerly ein QWebEngineView
        # (Chromium-Subprozess) - das eager in MainWindow.__init__ zu tun heisst,
        # JEDER Login zahlt diesen Startaufwand, nicht nur die paar Superuser,
        # die den Screen je oeffnen.
        self.stats_suite = None
        self.offline_sync = None
        self.lab_assistant = None
        # TDMS Inspector: lazy too - builds several matplotlib canvases
        # (DTY + ATY YarnScope tabs), no reason to pay that at every login.
        self.tdms_inspector = None

        # Backlog-Screen - seit 2026-08-26 der Post-Login-Landing-Screen
        # (siehe _on_login_success()), bekommt daher dieselbe volle
        # Sidebar-Navigation wie HomeScreen (siehe ui/widgets/sidebar_nav.py
        # und CLAUDE.md). Die _go_X-Callbacks existieren als Methoden bereits
        # jetzt (Python bindet sie unabhängig vom Login-Status), auch wenn
        # der Nutzer sich erst später einloggt - genau wie on_back_home
        # hier schon immer eager übergeben wurde.
        self.backlog = BacklogScreen(
            on_back_home=self._go_home,
            on_open_experiment=self._open_experiment_from_backlog,
            on_open_in_new_window=self._open_experiment_from_backlog_in_new_tab,
            on_open_in_new_os_window=self.open_experiment_in_new_window,
            on_open_report=self._go_report,
            open_in_new_tab=self._open_in_new_tab_dispatch,
            on_all_experiments=self._go_all_experiments,
            on_create_experiment=lambda: self._go_create_experiment("create"),
            on_create_experiment_legacy=lambda: self._go_create_experiment("legacy"),
            on_add_series=lambda: self._go_create_experiment("addseries"),
            on_add_lab_machines=lambda: self._go_create_experiment("addlabmachines"),
            on_open_experiment_request=self._go_experiment_request,
            on_create_experiment_request=self._go_create_experiment_request,
            on_open_my_requests=self._go_my_requests,
            on_preview_requests=self._show_request_preview_dialog,
            on_preview_open_requests=lambda: self._show_request_preview_dialog(
                status=1, title="Open Experiment Requests"),
            on_image_compare=self._go_image_compare,
            on_canvas=self._go_canvas,
            on_nozzle_calculator=self._go_nozzle_calculator,
            on_air_supply=self._go_air_supply,
            on_requirement_hub=self._go_requirement_hub,
            on_smartchart=self._go_smartchart,
            on_yarn_stock=self._go_yarn_stock,
            on_label_generator=self._go_label_generator,
            on_tdms_inspector=self._go_tdms_inspector,
            on_add_jet=self._go_add_jet,
            on_add_top_plate=self._go_add_top_plate,
            on_add_yarn=self._go_add_yarn,
            on_manage_order_type=self._go_manage_order_type,
            on_manage_product_groups=self._go_manage_product_groups,
            on_manage_material=self._go_manage_material,
            on_add_user=self._go_add_user,
            on_usage_stats=self._go_usage_stats,
            on_statistics=self._go_statistics,
            on_offline_sync=self._go_offline_sync,
            on_lab_assistant=self._go_lab_assistant,
            on_logout=self._logout,
        )

        # Experiment Request
        self.create_experiment_request = CreateExperimentRequestScreen(
            on_back_home=self._go_home,
            sidebar_callbacks=self._sidebar_nav_kwargs(),
        )
        self.my_requests = MyRequestsScreen(
            on_back_home=self._go_home,
            on_back_experiment_request=self._go_experiment_request,
            on_open_request=self._go_edit_experiment_request,
            on_open_experiment=lambda exp_pk, series_pk, experiment_id: self._go_show_experiment(
                exp_pk, series_pk, experiment_id,
                back_label="My Requests", back_callback=self._go_my_requests),
            sidebar_callbacks=self._sidebar_nav_kwargs(),
        )

        self.experiment_request = ExperimentRequestScreen(
            on_back_home=self._go_home,
            on_create_experiment_request=self._go_create_experiment_request,
            on_open_my_requests=self._go_my_requests,
            sidebar_callbacks=self._sidebar_nav_kwargs(),
        )

        self.login = LoginScreen(
            on_success=self._on_login_success,
            on_change_pw=self._go_change_pw
        )

        for _screen in (
            self.change_pw, self.all_experiments, self.show_experiment,
            self.report_screen, self.smartchart_screen, self.new_jet,
            self.manage_jets, self.new_top_plate, self.manage_top_plates,
            self.manage_user, self.manage_order_type, self.manage_product_groups,
            self.manage_material, self.usage_stats, self.backlog,
            self.create_experiment_request, self.my_requests,
            self.experiment_request, self.login,
        ):
            if _screen is not None:
                self.stack.addWidget(_screen)

        self.image_compare: Optional[ImageCompareScreen] = None
        self.canvas: Optional[CanvasScreen] = None
        self.tdms_batch: Optional["TDMSBatchScreen"] = None
        self.requirement_hub: Optional["RequirementHubScreen"] = None
        self.quick_scan: Optional["QuickScanScreen"] = None
        self.nozzle_calculator: Optional["NozzleCalculatorScreen"] = None
        self.air_supply: Optional["AirSupplyScreen"] = None
        self.label_generator: Optional["LabelGeneratorScreen"] = None
        self._search_dlg: Optional[QuickSearchDialog] = None

        self._create_screen_ref: Optional[CreateExperimentScreen] = None

        # Nutzungs-Tracking: jeder Screen-Wechsel im Stack wird geloggt
        # (best-effort, siehe db/usage_log.py). Ein einziger zentraler Hook
        # statt Instrumentierung jeder einzelnen _go_XXX()-Methode.
        # `_StackFacade` hat kein `currentChanged` mehr - `TabbedNavigator.
        # screenChanged` feuert stattdessen bei jedem sichtbaren Screen-
        # Wechsel, egal in welchem Tab (siehe ui/widgets/tab_container.py).
        self._tabs.screenChanged.connect(lambda: self._log_screen_open())

        # Idle-triggered offline-snapshot auto-refresh (superusers only for
        # now, see ui/offline_autosnapshot.py). One instance for the whole
        # process; eligibility is re-checked live on every tick, so it's a
        # no-op before login and adapts automatically to whoever is logged
        # in - best-effort, must never block startup.
        try:
            self._idle_snapshot_mgr = IdleSnapshotManager(QApplication.instance())
            self._idle_snapshot_mgr.start()
        except Exception:
            pass

        self.stack.setCurrentWidget(self.login)

    # --- Data functions for Manage Jets --------------------------------------
    def _load_jets_data(self, limit: Optional[int] = None) -> List[Dict]:
        """Lädt Jet-Daten aus tblJet mit has_files-Flag (0/1) und UsedInTrial
        (rein berechnet, kein echtes tblDTYJets-Feld - ob dieser Jet in
        mindestens einem Trial verwendet wurde, siehe tbltrial.JetID)."""
        sql = """
            SELECT j.*,
                   CASE WHEN COUNT(f.ID) > 0 THEN 1 ELSE 0 END AS has_files,
                   CASE WHEN EXISTS (SELECT 1 FROM tbltrial t WHERE t.JetID = j.ID)
                        THEN 1 ELSE 0 END AS UsedInTrial
            FROM tblDTYJets j
            LEFT JOIN tblJetFile f ON f.JetID = j.ID
            GROUP BY j.ID
        """
        try:
            return fetch_all(sql, [])
        except Exception:
            # Fallback wenn tblJetFile noch nicht existiert
            return fetch_all(
                "SELECT j.*, "
                "CASE WHEN EXISTS (SELECT 1 FROM tbltrial t WHERE t.JetID = j.ID) "
                "THEN 1 ELSE 0 END AS UsedInTrial "
                "FROM tblDTYJets j", [])

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

        # "Created by" - who/when a jet was added (superuser-only visibility,
        # never editable - see ManageJetsScreen/JetsTableModel's _AUDIT_COLS).
        try:
            from db.user_directory import load_user_id_to_name
            maps["createdby"] = {"id_to_name": load_user_id_to_name(), "name_to_id": {}}
        except Exception:
            pass

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
        _require_admin_box_write()
        if not rows:
            return 0
        id_col = self._jets_id_col or "ID"
        total = 0
        _SYNTHETIC = {"__has_files__", "has_files", "UsedInTrial"}
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
        _require_admin_box_write()
        # "GebogenerKanal"/"YarnChannelShape" (ohne Leerzeichen) sind die
        # echten Spaltennamen (SHOW COLUMNS gegen dev_local/prod verifiziert) -
        # die Leerzeichen hier waren ein eigenständiger, vom @@IDENTITY-Audit
        # unabhängiger Bug: `c` wird unten direkt als SQL-Identifier in `cols`
        # übernommen - `_first_fk_default(c)` normalisiert `c` zwar intern via
        # _canon() für den reinen dict-Lookup, das ändert aber nichts an `c`
        # selbst. Ein "New Jet"-Klick schlug dadurch bisher immer mit "Unknown
        # column" fehl, aufgedeckt beim End-to-End-Test des execute_insert()-
        # Umbaus (erst bei GebogenerKanal, nach dessen Fix hier bei
        # YarnChannelShape erneut).
        cols = ["Jet", "GebogenerKanal", "GlobalID", "CreatedBy", "CreationDate"]
        vals = ["Neuer Jet", 0, new_global_id(),
                (app_meta.current_user or {}).get("id"), datetime.datetime.now()]
        fk_candidates = ["Hersteller", "Serie", "Luftkanalform",
                         "YarnChannelShape", "Wirbelkammer", "Werkstoff"]
        for c in fk_candidates:
            d = self._first_fk_default(c)
            if d is not None:
                cols.append(c)
                vals.append(d)

        placeholders = ",".join(["?"] * len(cols))
        cols_sql = ", ".join([f"[{c}]" for c in cols])
        sql = f"INSERT INTO [tblDTYJets] ({cols_sql}) VALUES ({placeholders})"
        return execute_insert(sql, vals)

    def _insert_jet_full(self, data: Dict) -> int:
        """Fügt einen neuen Jet mit vollständigen Daten (Kopie) in die DB ein.

        Returns:
            Neue Jet-ID (execute_insert()/lastrowid).
        """
        _require_admin_box_write()
        id_col = self._jets_id_col or "ID"
        _SYNTHETIC = {"__has_files__", "has_files", "UsedInTrial"}

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

        # Wer/wann angelegt wurde - immer frisch gesetzt, nie aus einer Kopiervorlage
        # übernommen (NewJetScreen zeigt diese Felder gar nicht erst an, siehe
        # screen_new_jet._HIDDEN_COLS, data enthält sie deshalb ohnehin nicht).
        data["CreatedBy"] = (app_meta.current_user or {}).get("id")
        data["CreationDate"] = datetime.datetime.now()

        if not data:
            raise ValueError("Keine Daten zum Speichern übergeben.")

        cols = list(data.keys())
        vals = [data[c] for c in cols]
        cols_sql = ", ".join(f"[{c}]" for c in cols)
        placeholders = ", ".join("?" for _ in cols)
        sql = f"INSERT INTO [tblDTYJets] ({cols_sql}) VALUES ({placeholders})"
        new_id = execute_insert(sql, vals)
        if new_id is None:
            raise RuntimeError("Konnte neue ID nach Insert nicht bestimmen.")
        return new_id

    def _delete_jets(self, ids: List[int]) -> int:
        """Löscht Jets mit den gegebenen IDs aus tblJet.

        Returns:
            Anzahl gelöschter Zeilen.
        """
        _require_admin_box_write()
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
        _require_admin_box_write()
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
        _require_admin_box_write()
        cols = ["Name", "GlobalID"]
        vals = ["New Top Plate", new_global_id()]

        placeholders = ",".join(["?"] * len(cols))
        cols_sql = ", ".join([f"[{c}]" for c in cols])
        sql = f"INSERT INTO [tblTopPlates] ({cols_sql}) VALUES ({placeholders})"
        return execute_insert(sql, vals)

    def _insert_top_plate_full(self, data: Dict) -> int:
        """Fügt eine neue Top Plate mit vollständigen Daten (Kopie) in die DB ein.

        Returns:
            Neue Top-Plate-ID (execute_insert()/lastrowid).
        """
        _require_admin_box_write()
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
        new_id = execute_insert(sql, vals)
        if new_id is None:
            raise RuntimeError("Konnte neue ID nach Insert nicht bestimmen.")
        return new_id

    def _delete_top_plates(self, ids: List[int]) -> int:
        """Löscht Top Plates mit den gegebenen IDs aus tblTopPlates.

        Returns:
            Anzahl gelöschter Zeilen.
        """
        _require_admin_box_write()
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
        try:
            access_level = int(user.get("access_level") or 0)
        except Exception:
            access_level = 0

        # Offline-Modus ist vorerst nur für Superuser (AccessLevel >= 4)
        # freigeschaltet - das ist erst NACH dem Login bekannt (der Trigger,
        # ob offline überhaupt versucht wird, ist der separate Shortcut/
        # TRIPPLET_MODE=offline, siehe main.py-Kopf und db/connection.py).
        # Zurück zum Login statt zu Home, ohne current_user zu setzen.
        if is_offline_mode() and access_level < 4:
            QMessageBox.warning(
                self,
                "TrippleT – Offline-Modus",
                "Der Offline-Modus ist aktuell nur für Superuser freigeschaltet.",
            )
            self.login.reset_login_fields()
            self.stack.setCurrentWidget(self.login)
            self.setWindowTitle("TrippleT – Log In")
            return

        # Merge Login-Daten in das globale current_user-Objekt,
        # damit Flags wie is_superuser erhalten bleiben.
        try:
            app_meta.current_user.update(user)
        except Exception:
            app_meta.current_user = user
        # Ab hier immer mit dem globalen Objekt weiterarbeiten
        self.current_user = app_meta.current_user
        self.setWindowTitle("TrippleT – Backlog")

        # Akzentfarbe anwenden
        try:
            set_accent(user.get("accent_colour"))
            QApplication.instance().setStyleSheet(build_qss())
        except Exception:
            pass
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
            on_preview_open_requests=lambda: self._show_request_preview_dialog(
                status=1, title="Open Experiment Requests"),
            on_create_experiment_legacy=lambda: self._go_create_experiment("legacy"),
            on_add_series=lambda: self._go_create_experiment("addseries"),
            on_add_trials=lambda: self._go_create_experiment("addtrials"),
            on_open_backlog=self._go_backlog,
            on_open_experiment_request=self._go_experiment_request,
            on_create_experiment_request=self._go_create_experiment_request,
            on_open_my_requests=self._go_my_requests,
            on_image_compare=self._go_image_compare,
            on_canvas=self._go_canvas,
            # on_tdms_batch=self._go_tdms_batch,  # TODO: in screen_home.py eintragen
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
            on_usage_stats=self._go_usage_stats,
            on_statistics=self._go_statistics,
            on_label_generator=self._go_label_generator,
            on_offline_sync=self._go_offline_sync,
            on_lab_assistant=self._go_lab_assistant,
            on_tdms_inspector=self._go_tdms_inspector,
            open_in_new_tab=self._open_in_new_tab_dispatch,
        )
        self.stack.addWidget(self.home)
        # Post-Login-Landing: Backlog statt Home (Nutzerwunsch, 2026-08-26,
        # siehe CLAUDE.md) - Home bleibt über den Header-"Home"-Button
        # weiterhin erreichbar (_go_home()), ist aber nicht mehr der
        # Einstiegspunkt, da die Sidebar jetzt die Navigation übernimmt.
        self.stack.setCurrentWidget(self.backlog)

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
                self._notif_panel.experiment_request_clicked.connect(self._go_my_requests_from_notification)
                self._notif_panel.all_read.connect(self._on_bell_mark_all_read)

            def _refresh_bell():
                uid = (app_meta.current_user or {}).get("id")
                if not uid:
                    return
                try:
                    unread = get_unread_count(int(uid))
                    total  = get_total_count(int(uid))
                    w = self.stack.currentWidget()
                    if w and hasattr(w, "_header") and hasattr(w._header, "set_bell_count"):
                        # Screens mit klassischer TopBar (HeaderBar) - Bell
                        # immer sichtbar sobald Eintraege vorhanden (gelesen
                        # oder ungelesen).
                        w._header.set_bell_count(unread, total)
                        if not hasattr(w._header, "_bell_connected") or not w._header._bell_connected:
                            w._header.connect_bell(self._on_bell_clicked)
                            w._header._bell_connected = True
                    elif w and getattr(w, "_bell_button", None) is not None:
                        # Sidebar-Screens (Home/Backlog/AllExperiments/
                        # ShowExperiment, seit 2026-08-26 ohne TopBar) - Bell
                        # sitzt in der Sidebar-Account-Gruppe (siehe
                        # ui/widgets/sidebar_nav.py::build_utility_group()),
                        # dort immer sichtbar, Badge nur bei unread>0.
                        from ui.widgets import sidebar_nav as _sidebar_nav
                        _sidebar_nav.refresh_badge(getattr(w, "_bell_badge", None), unread)
                        bell_btn = w._bell_button
                        if not getattr(bell_btn, "_bell_connected", False):
                            bell_btn.clicked.connect(self._on_bell_clicked)
                            bell_btn._bell_connected = True
                except Exception:
                    pass

            _am.refresh_bell = _refresh_bell

            # Timer: alle 60s pruefen
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

    def _log_screen_open(self) -> None:
        """Loggt jeden sichtbaren Screen-Wechsel fuer den Admin-Stats-Screen
        (best-effort) - an TabbedNavigator.screenChanged gehängt (siehe
        __init__), das ohne Argumente feuert; der gerade sichtbare Screen
        wird daher frisch über self.stack.currentWidget() aufgelöst statt
        über einen Index (der hätte sich je nach Tab unterschiedlich
        auflösen müssen, siehe ui/widgets/tab_container.py)."""
        try:
            from db.usage_log import log_usage_event
            widget = self.stack.currentWidget()
            if widget is not None:
                log_usage_event("screen_open", type(widget).__name__)
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
            bell = None
            if w and hasattr(w, "_header"):
                bell = w._header._btn_bell
            elif w and getattr(w, "_bell_button", None) is not None:
                bell = w._bell_button
            if bell is not None:
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
            self.image_compare = ImageCompareScreen(on_back_home=self._go_home, sidebar_callbacks=self._sidebar_nav_kwargs())
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
                sidebar_callbacks=self._sidebar_nav_kwargs(),
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
                sidebar_callbacks=self._sidebar_nav_kwargs(),
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
            self.canvas = CanvasScreen(on_back_home=self._go_home, sidebar_callbacks=self._sidebar_nav_kwargs())
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
            self.tdms_batch = TDMSBatchScreen(on_back_home=self._go_home, sidebar_callbacks=self._sidebar_nav_kwargs())
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
                sidebar_callbacks=self._sidebar_nav_kwargs(),
            )
            self.stack.addWidget(self.nozzle_calculator)
        self.setWindowTitle("TrippleT – Jet ROI Calculator")
        self.stack.setCurrentWidget(self.nozzle_calculator)

    def _go_label_generator(self):
        """Navigiert zum Label Generator."""
        if LabelGeneratorScreen is None:
            QMessageBox.warning(self, "Label Generator",
                                "Label Generator nicht verfügbar – Import fehlgeschlagen.")
            return
        if self.label_generator is None:
            self.label_generator = LabelGeneratorScreen(on_back_home=self._go_home, sidebar_callbacks=self._sidebar_nav_kwargs())
            self.stack.addWidget(self.label_generator)
        self.setWindowTitle("TrippleT – Label Generator")
        self.stack.setCurrentWidget(self.label_generator)

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
                sidebar_callbacks=self._sidebar_nav_kwargs(),
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

    def _show_request_preview_dialog(self, status: int = 3, title: str = "Pending Experiment Requests"):
        """Öffnet den Request-Preview-Dialog mit Navigation und «Create Experiment»-Button.

        Ursprünglich fix auf genehmigte Requests (RequestStatus=3, der Badge auf
        "Create New Experiment"). Auf Nutzerwunsch ("wenn ich auf den roten
        Punkt bei Experiment Request klicke, will ich die offenen Requests so
        sehen wie wenn ich auf den roten Punkt bei Create New Experiment
        klicke") um `status`/`title` erweitert - der Badge auf "Experiment
        Request" (offene Requests, RequestStatus=1) nutzt jetzt denselben
        Dialog, nur mit anderem Filter/Titel statt einer eigenen Kopie. Der
        "Create Experiment"-Button bleibt bewusst für beide Status verfügbar -
        `_go_create_experiment(..., preset_request_id=...)` ist nicht an einen
        bestimmten RequestStatus gebunden, ein Superuser (einzige Zielgruppe
        dieses Badges) darf auch aus einem noch nicht offiziell genehmigten
        Request heraus direkt ein Experiment anlegen."""
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                                        QPushButton, QLabel, QFrame, QScrollArea,
                                        QSizePolicy, QWidget, QMessageBox)
        from PySide6.QtCore import Qt
        from db.connection import fetch_all

        try:
            rows = fetch_all(
                "SELECT * FROM [tblExperimentRequests] WHERE [RequestStatus] = ? ORDER BY [ID] DESC",
                [status]
            )
        except Exception:
            rows = []

        if not rows:
            if status == 3:
                # Bestehendes Verhalten für den "Create New Experiment"-Badge
                # unangetastet: keine genehmigten Requests -> direkt zum
                # normalen "Create Experiment"-Formular.
                self._go_create_experiment("create")
            else:
                QMessageBox.information(self, title, "No experiment requests found.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(title)
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
            sidebar_callbacks=self._sidebar_nav_kwargs(),
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
            sidebar_callbacks=self._sidebar_nav_kwargs(),
        )
        self.stack.addWidget(screen)
        self.stack.setCurrentWidget(screen)
        self._create_screen_ref = screen
        try:
            screen.open_addtrials_prefill(exp_pk, series_pk)
        except Exception:
            pass

    def _find_open_show_experiment_for_series(self, series_pk: int):
        """Sucht über ALLE Tabs (Singleton self.show_experiment UND per
        Ctrl+Klick geöffnete tab-lokale Instanzen, siehe
        _make_local_experiment_opener()/_open_show_experiment_in_new_tab())
        nach einer ShowExperimentScreen-Instanz, die GENAU diese TrialSeries
        bereits anzeigt. Von _go_show_experiment() genutzt, damit z.B. ein
        Klick aus Manage Yarn/Manage Jets' "Used in Trial"-Popup einen
        bereits offenen Tab fokussiert, statt ihn zu ignorieren und
        stattdessen den (ggf. in einem GANZ ANDEREN Tab sichtbaren)
        Singleton umzubiegen (Bugreport 2026-08-27: "wenn ich nun eine
        trialseries aus Manage Yarn ... öffne, öffnet es nicht in der
        existierenden tab, wenn es mehrere tabs gibt")."""
        tabs = getattr(self, "_tabs", None)
        if tabs is None:
            return None
        for i in range(tabs.count()):
            stack = tabs.widget(i)
            widget = stack.currentWidget() if isinstance(stack, QStackedWidget) else None
            if isinstance(widget, ShowExperimentScreen) and getattr(widget, "_series_pk", None) == series_pk:
                return widget
        return None

    def _go_show_experiment(self, exp_pk: int, series_pk: int, experiment_id: str,
                             back_label: Optional[str] = None, back_callback=None):
        """Navigiert zum ShowExperiment-Screen für ein bestimmtes Experiment.

        Args:
            exp_pk:        Primärschlüssel in tblExperimente.
            series_pk:     Primärschlüssel in tblTrialSeries.
            experiment_id: Lesbare ID (z.B. "2024-PG-001") für den Titel.
            back_label:    Beschriftung für den kontextuellen Back-Chip in der
                           Tools-Leiste (z.B. "Backlog", "All Experiments") -
                           siehe ShowExperimentScreen.set_back_target(). Ohne
                           Angabe bleibt der Chip unsichtbar (kein bekannter
                           Rücksprung-Kontext, z.B. beim Öffnen direkt nach
                           dem Anlegen eines neuen Experiments).
            back_callback: Zugehöriger Rücksprung-Callback.
        """
        # Ist diese TrialSeries bereits in irgendeinem Tab offen (Singleton
        # ODER ein per Ctrl+Klick geöffneter Vergleichs-Tab) - einfach dorthin
        # wechseln (Fokus statt Duplikat/Umbiegen), statt sie ggf. blind in
        # den Singleton woanders zu laden.
        existing = self._find_open_show_experiment_for_series(series_pk)
        if existing is not None:
            self.setWindowTitle(f"TrippleT – Show Experiment {experiment_id}")
            self.stack.setCurrentWidget(existing)
            existing.set_back_target(back_label, back_callback)
            existing.on_open_report = self._go_report
            return

        # Erst Screen aktivieren, dann laden – so bleibt Navigation auch bei Fehlern nachvollziehbar.
        self.setWindowTitle(f"TrippleT – Show Experiment {experiment_id}")
        self.stack.setCurrentWidget(self.show_experiment)
        self.show_experiment.set_back_target(back_label, back_callback)

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

    def _build_dedicated_show_experiment_screen(self, back_label: Optional[str] = None, back_callback=None):
        """Baut eine frische, eigenständige ShowExperimentScreen-Instanz mit
        voller Sidebar und eigener Add-Trials-Verdrahtung, die GENAU DIESE
        Instanz zum Ziel hat statt des geteilten Singletons
        (self.show_experiment) - gemeinsamer Baustein für alle Kontexte, in
        denen ein Experiment unabhängig vom Singleton betrachtet werden soll:
        ein per Ctrl+Klick geöffneter eigener Vergleichs-Tab (siehe
        _open_show_experiment_in_new_tab()) ODER ein normaler Doppelklick
        INNERHALB eines bereits unabhängigen (per Ctrl+Klick geöffneten)
        Backlog-/All-Experiments-Tabs (siehe _make_local_experiment_opener(),
        Bugreport 2026-08-27: "praktisch habe ich aber nur eine trialseries
        offen in show experiment und im anderen tab das backlog" - der
        normale Doppelklick in einem frischen Backlog-Tab delegierte bisher
        an den Singleton, der aber ggf. gerade in einem GANZ ANDEREN Tab
        sichtbar war und dadurch dessen Inhalt überschrieb)."""
        screen_ref: dict = {}

        def _on_add_trials(a_exp_pk: int, a_series_pk: int, a_experiment_id: str):
            self._dispose_old_create_screen()
            self.setWindowTitle("TrippleT – Add Trials")

            def _back_to_this_experiment():
                self._dispose_old_create_screen()
                self.setWindowTitle(f"TrippleT – Show Experiment {a_experiment_id}")
                self.stack.setCurrentWidget(screen_ref["screen"])

            create_screen = CreateExperimentScreen(
                on_back_home=self._go_home,
                on_back_experiment=_back_to_this_experiment,
                on_open_experiment=self._go_show_experiment,
                mode="addtrials",
                sidebar_callbacks=self._sidebar_nav_kwargs(),
            )
            self.stack.addWidget(create_screen)
            self.stack.setCurrentWidget(create_screen)
            self._create_screen_ref = create_screen
            try:
                create_screen.open_addtrials_prefill(a_exp_pk, a_series_pk)
            except Exception:
                pass

        screen = ShowExperimentScreen(
            on_back_home=self._go_home,
            on_add_trials=_on_add_trials,
            **self._sidebar_nav_kwargs(),
        )
        screen_ref["screen"] = screen
        screen.on_open_report = self._go_report
        screen.set_back_target(back_label, back_callback)
        return screen

    def _load_record_safely(self, screen, exp_pk: int, series_pk: int, experiment_id: str) -> None:
        try:
            screen.load_record(exp_pk, series_pk, experiment_id)
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

    def _open_show_experiment_in_new_tab(self, exp_pk: int, series_pk: int, experiment_id: str,
                                          back_label: Optional[str] = None, back_callback=None) -> None:
        """Öffnet ein Experiment in einer FRISCHEN, eigenständigen
        ShowExperimentScreen-Instanz in einem neuen Tab - im Gegensatz zu
        allen anderen Screens bleibt Show Experiment beim normalen Ctrl+Klick
        (self._go_show_experiment()) NICHT beim geteilten Singleton
        (self.show_experiment), weil zwei unterschiedliche Experimente
        gleichzeitig vergleichen zu können der eigentliche Sinn dieses Ctrl+
        Klick-Pfads ist. Gemeinsamer Kern für BEIDE Ctrl-Auslöser: sowohl
        _go_show_experiment() (Manage Yarn/Jets-Popups) als auch
        _open_experiment_from_backlog_in_new_tab()/_open_experiment_from_all_in_new_tab()
        (Backlog/All Experiments' eigene Ctrl-Erkennung) landen hier."""
        def _populate():
            screen = self._build_dedicated_show_experiment_screen(back_label, back_callback)
            self.setWindowTitle(f"TrippleT – Show Experiment {experiment_id}")
            self.stack.addWidget(screen)
            self.stack.setCurrentWidget(screen)
            self._load_record_safely(screen, exp_pk, series_pk, experiment_id)

        self._tabs.open_in_new_tab(_populate)

    def _make_local_experiment_opener(self, back_label: str, back_callback):
        """Baut einen on_open_experiment-Handler für eine FRISCHE (per
        Ctrl+Klick unabhängig geöffnete) Backlog-/All-Experiments-Instanz:
        ein normaler (nicht Ctrl-)Doppelklick auf eine TrialSeries dort soll
        INNERHALB DESSELBEN Tabs angezeigt werden (genau wie beim
        Original-Backlog in Tab 0, das dafür den globalen Singleton
        self.show_experiment wiederverwendet) - OHNE dabei versehentlich
        diesen globalen Singleton zu benutzen, der gerade in einem GANZ
        ANDEREN Tab sichtbar sein könnte (Bugreport 2026-08-27: "praktisch
        habe ich aber nur eine trialseries offen in show experiment und im
        anderen tab das backlog"). Baut dafür lazy GENAU EINE eigene,
        tab-lokale ShowExperimentScreen-Instanz beim ersten Aufruf und nutzt
        sie für alle weiteren Klicks innerhalb desselben Tabs wieder -
        Ctrl+Doppelklick (on_open_in_new_window) bleibt davon unberührt und
        öffnet weiterhin einen echten, zusätzlichen neuen Tab."""
        local: dict = {"screen": None}

        def _open(exp_pk: int, series_pk: int, experiment_id: str):
            if local["screen"] is None:
                local["screen"] = self._build_dedicated_show_experiment_screen(back_label, back_callback)
            screen = local["screen"]
            self.setWindowTitle(f"TrippleT – Show Experiment {experiment_id}")
            self.stack.addWidget(screen)
            self.stack.setCurrentWidget(screen)
            self._load_record_safely(screen, exp_pk, series_pk, experiment_id)

        return _open

    def _go_report(self, series_pk: int, report_id: Optional[int] = None) -> None:
        """Öffnet den Report-Screen für eine TrialSeries. `report_id` (siehe
        ShowExperimentScreen's "Saved Reports"-Dropdown+Go-Button) lädt
        direkt einen bestimmten gespeicherten Report, statt der leeren
        Standardansicht."""
        if self.report_screen is None:
            QMessageBox.warning(
                self, "Report",
                "Report nicht verfügbar – PySide6-WebEngine nicht installiert.\n\n"
                "Bitte ausführen: pip install PySide6-WebEngine"
            )
            return
        self.setWindowTitle("TrippleT – Smart Chart")
        self.report_screen.load_series(series_pk, initial_report_id=report_id)
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
        """Öffnet ShowExperimentScreen aus dem AllExperiments-Screen. Der
        Back-Chip zeigt danach wieder zurück auf All Experiments."""
        self._go_show_experiment(exp_pk, series_pk, experiment_id,
                                  back_label="All Experiments", back_callback=self._go_all_experiments)

    def _open_experiment_from_backlog(self, exp_pk: int, series_pk: int, experiment_id: str):
        """Öffnet ShowExperimentScreen aus dem Backlog-Screen. Der Back-Chip
        zeigt danach wieder zurück auf den Backlog."""
        self._go_show_experiment(exp_pk, series_pk, experiment_id,
                                  back_label="Backlog", back_callback=self._go_backlog)

    def _open_experiment_from_yarn(self, exp_pk: int, series_pk: int, experiment_id: str):
        """Öffnet ein Experiment aus dem "Used in Trial Series"-Popup in Manage
        Yarn heraus. Der Back-Chip zeigt danach wieder zurück auf Manage Yarn."""
        self._go_show_experiment(exp_pk, series_pk, experiment_id,
                                  back_label="Manage Yarn", back_callback=self._go_add_yarn)

    def _open_experiment_from_jets(self, exp_pk: int, series_pk: int, experiment_id: str):
        """Öffnet ein Experiment aus dem "Used in Trial Series"-Popup in Manage
        Jets heraus. Der Back-Chip zeigt danach wieder zurück auf Manage Jets."""
        self._go_show_experiment(exp_pk, series_pk, experiment_id,
                                  back_label="Manage Jets", back_callback=self._go_back_manage_jets)

    def open_experiment_in_new_window(self, exp_pk: int, series_pk: int, experiment_id: str) -> None:
        """Öffnet ShowExperimentScreen in einem eigenständigen neuen Fenster
        (kein Stack) - Ctrl+Doppelklick/Kontextmenü "Open in New Window" aus
        Backlog/All Experiments heraus."""
        win = QMainWindow()
        win.setWindowTitle(f"TrippleT – {experiment_id}")
        win.setMinimumSize(1100, 700)

        screen_widget = ShowExperimentScreen(
            on_back_home=win.close,
        )
        # Kein "on_logout"/keine Sidebar-Nav-Callbacks hier (dieses Fenster
        # ist vom Haupt-Stack losgelöst - siehe open_experiment_in_new_window()-
        # Docstring weiter oben zur Begründung, wieso die Nav-Gruppe hier
        # unverdrahtet/deaktiviert bleibt) - nur der Back-Chip bekommt ein
        # sinnvolles Ziel: dieses eigenständige Fenster schliessen.
        screen_widget.set_back_target("Close window", win.close)
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
        win.setWindowTitle("TrippleT – Smart Chart")
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

    # -->-->-->- Fresh-Instance-Tabs: Show Experiment / Backlog / All Experiments -->-->-->-
    # Die folgenden Methoden bauen eine frische, unabhängige Screen-Instanz
    # in einem eigenen Tab statt des geteilten Singletons - für diese drei
    # Screens ist "mehrfach gleichzeitig offen" ein echtes Bedürfnis
    # (Experimente vergleichen, zwei Backlog-/All-Experiments-Ansichten
    # nebeneinander), anders als bei allen übrigen Sidebar-Zielen (siehe
    # _fresh_tab_targets/_open_in_new_tab_dispatch()).
    def _open_experiment_from_all_in_new_tab(self, exp_pk: int, series_pk: int, experiment_id: str):
        """Öffnet ein Experiment in einer frischen ShowExperimentScreen-Instanz
        in einem neuen Tab, mit funktionierendem Back-Chip ("All Experiments")
        - Ctrl+Doppelklick/Kontextmenü "Open in New Tab" aus All Experiments
        heraus (abgelöst aus einem früheren "in neuem Fenster öffnen"-
        Feature, siehe _open_show_experiment_in_new_tab()). Ohne eigenen
        Back-Chip-Callback pro Aufrufer hätte der frische Tab keinen
        sinnvollen Rücksprung (beide Aufrufer teilen sich sonst denselben
        generischen Callback und könnten nicht zwischen "zurück zu Backlog"
        und "zurück zu All Experiments" unterscheiden)."""
        self._open_show_experiment_in_new_tab(
            exp_pk, series_pk, experiment_id,
            back_label="All Experiments", back_callback=self._go_all_experiments)

    def _open_experiment_from_backlog_in_new_tab(self, exp_pk: int, series_pk: int, experiment_id: str):
        """Wie _open_experiment_from_all_in_new_tab(), aber mit Back-Chip
        ("Backlog") - Ctrl+Doppelklick/Kontextmenü "Open in New Tab" aus
        Backlog heraus."""
        self._open_show_experiment_in_new_tab(
            exp_pk, series_pk, experiment_id,
            back_label="Backlog", back_callback=self._go_backlog)

    def _open_backlog_in_new_tab(self):
        """Ctrl+Klick auf den 'Backlog'-Sidebar-Eintrag: baut eine frische,
        unabhängige BacklogScreen-Instanz in einem neuen Tab (siehe
        _fresh_tab_targets/_open_in_new_tab_dispatch()) statt zum
        geteilten Singleton (self.backlog) zu wechseln - genau dasselbe
        Fresh-Instance-Muster wie _open_show_experiment_in_new_tab().

        `on_open_experiment` (normaler Doppelklick) nutzt einen tab-lokalen
        Experiment-Opener (siehe _make_local_experiment_opener()) statt
        _open_experiment_from_backlog() (welches den globalen Singleton
        self.show_experiment verwendet hätte) - sonst würde ein normaler
        Doppelklick in DIESEM frischen Tab den Singleton woanders (z.B. Tab 0)
        überschreiben statt innerhalb dieses Tabs zu öffnen."""
        backlog_ref: dict = {}

        def _back_to_this_backlog():
            self.setWindowTitle("TrippleT – Backlog")
            self.stack.setCurrentWidget(backlog_ref["screen"])

        open_experiment_locally = self._make_local_experiment_opener("Backlog", _back_to_this_backlog)

        def _populate():
            screen = BacklogScreen(
                on_back_home=self._go_home,
                on_open_experiment=open_experiment_locally,
                on_open_in_new_window=self._open_experiment_from_backlog_in_new_tab,
                on_open_in_new_os_window=self.open_experiment_in_new_window,
                on_open_report=self._go_report,
                **self._sidebar_nav_kwargs(include_open_backlog=False),
            )
            backlog_ref["screen"] = screen
            self.setWindowTitle("TrippleT – Backlog")
            self.stack.addWidget(screen)
            self.stack.setCurrentWidget(screen)
        self._tabs.open_in_new_tab(_populate)

    def _open_all_experiments_in_new_tab(self):
        """Wie _open_backlog_in_new_tab(), für 'All Experiments'. `can_review`
        wird hier - anders als beim Singleton self.all_experiments, dessen
        can_review erst nachträglich in _on_login_success() per
        set_can_review() gesetzt wird, weil access_level zum
        Konstruktionszeitpunkt in __init__ noch nicht bekannt ist - direkt
        korrekt aus dem inzwischen bekannten access_level abgeleitet (dieser
        Pfad ist nur nach erfolgtem Login über die Sidebar erreichbar)."""
        try:
            access_level = int((app_meta.current_user or {}).get("access_level") or 0)
        except Exception:
            access_level = 0
        can_review = access_level >= 4  # gleiche Regel wie _on_login_success()

        # Wie bei _open_backlog_in_new_tab(): normaler Doppelklick bleibt
        # innerhalb DIESES Tabs (tab-lokaler Experiment-Opener), statt den
        # globalen Singleton self.show_experiment zu benutzen.
        all_exp_ref: dict = {}

        def _back_to_this_all_experiments():
            self.setWindowTitle("TrippleT – All Experiments")
            self.stack.setCurrentWidget(all_exp_ref["screen"])

        open_experiment_locally = self._make_local_experiment_opener("All Experiments", _back_to_this_all_experiments)

        def _populate():
            screen = AllExperimentsScreen(
                on_back_home=self._go_home,
                on_open_experiment=open_experiment_locally,
                on_open_in_new_window=self._open_experiment_from_all_in_new_tab,
                on_open_in_new_os_window=self.open_experiment_in_new_window,
                on_copy_trialseries=self._go_copy_trialseries,
                on_open_report=self._go_report,
                can_review=can_review,
                **self._sidebar_nav_kwargs(include_all_experiments=False),
            )
            all_exp_ref["screen"] = screen
            self.setWindowTitle("TrippleT – All Experiments")
            self.stack.addWidget(screen)
            self.stack.setCurrentWidget(screen)
        self._tabs.open_in_new_tab(_populate)

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
                self.manage_yarn = Screen(on_back_home=self._go_home,
                                          on_edit_yarn=self._go_edit_yarn_form,
                                          on_new_yarn=self._go_new_yarn_form,
                                          on_open_experiment=self._open_experiment_from_yarn,
                                          sidebar_callbacks=self._sidebar_nav_kwargs())
                self.stack.addWidget(self.manage_yarn)
            self.setWindowTitle("TrippleT – Manage Yarn")
            full = app_meta.can_use_admin_box()
            self.manage_yarn.set_permissions(can_delete=full, can_edit_minstock=full)
            self.stack.setCurrentWidget(self.manage_yarn)
        except Exception as e:
            QMessageBox.critical(self, "Manage Yarn",
                                 f"Fehler beim Öffnen: {e}")

    def _go_back_manage_yarn(self):
        self.setWindowTitle("TrippleT – Manage Yarn")
        if hasattr(self, 'manage_yarn') and self.manage_yarn is not None:
            full = app_meta.can_use_admin_box()
            self.manage_yarn.set_permissions(can_delete=full, can_edit_minstock=full)
            self.stack.setCurrentWidget(self.manage_yarn)
        else:
            self._go_add_yarn()

    def _ensure_new_yarn_screen(self) -> bool:
        """Baut `self.new_yarn` (NewYarnScreen) lazy, genau einmal pro
        Prozesslaufzeit - wiederverwendet von `_go_edit_yarn_form()` (bestehenden
        Datensatz bearbeiten) UND `_go_new_yarn_form()` (neuen Datensatz
        anlegen, siehe dort). Gibt False zurück, falls NewYarnScreen nicht
        verfügbar ist (Import fehlgeschlagen)."""
        if NewYarnScreen is None:
            return False
        if hasattr(self, 'new_yarn') and self.new_yarn is not None:
            return True
        fk_maps = {}
        try:
            g_id2name, g_name2id = load_garntyp_map()
            fk_maps['garntyp'] = {'id_to_name': g_id2name, 'name_to_id': g_name2id}
            m_id2name, m_name2id = load_material_map()
            fk_maps['material'] = {'id_to_name': m_id2name, 'name_to_id': m_name2id}
            yg_id2name, yg_name2id = load_yarngroup_map()
            fk_maps['yarngroupid'] = {'id_to_name': yg_id2name, 'name_to_id': yg_name2id}
        except Exception:
            pass
        try:
            # eigener try/except: tblColour existiert (Stand 2026-08-24) nur auf
            # dev_local/prod, nicht auf dev - darf Garntyp/Material/YarnGroup
            # oben nicht mit reissen, falls die Tabelle hier fehlt.
            c_id2name, c_name2id = load_colour_map()
            fk_maps['colourid'] = {'id_to_name': c_id2name, 'name_to_id': c_name2id}
        except Exception:
            pass
        try:
            from db.user_directory import load_user_id_to_name
            fk_maps['createdby'] = {'id_to_name': load_user_id_to_name(), 'name_to_id': {}}
        except Exception:
            pass
        # IMMER die volle Spaltenliste (inkl. CreatedBy/CreationDate) nehmen -
        # der Screen wird nur einmal lazy gebaut und wiederverwendet; wäre der
        # erste Aufrufer kein Superuser, gäbe es diese Spalten sonst gar nicht
        # und ein späterer Superuser würde sie nie zu sehen bekommen
        # (set_audit_fields_visible steuert nur die Sichtbarkeit, nicht ob die
        # Felder überhaupt existieren).
        all_cols_sample = fetch_all('SELECT * FROM [tblYarn] LIMIT 1', [])
        all_columns = list(all_cols_sample[0].keys()) if all_cols_sample else ['ID', 'Name']
        self.new_yarn = NewYarnScreen(
            columns=all_columns, fk_maps=fk_maps, id_column='ID',
            on_back_home=self._go_back_manage_yarn,
            on_quick_add_colour=quick_add_colour,
            sidebar_callbacks=self._sidebar_nav_kwargs(),
        )
        self.stack.addWidget(self.new_yarn)
        return True

    def _go_new_yarn_form(self):
        """Öffnet den NewYarnScreen leer für einen NEUEN Yarn-Datensatz
        (Nutzerwunsch: "direkt das Formular öffnen und den Eintrag erst
        wirklich in die DB speichern, wenn ich da auf Speichern klicke" - löst
        das bisherige Verhalten von ManageYarnScreen.btn_new ab, das sofort
        einen leeren "New Yarn"-Datensatz einfügte, noch bevor irgendwelche
        Werte erfasst waren. Cancel schreibt jetzt dadurch strukturell nichts
        mehr - es gibt schlicht keinen halb angelegten Datensatz mehr
        aufzuräumen, siehe CLAUDE.md)."""
        if not self._ensure_new_yarn_screen():
            QMessageBox.information(
                self, "Yarn", "'New Yarn' ist derzeit nicht verfügbar.")
            return

        def _create_save(data: Dict) -> Optional[int]:
            if not app_meta.can_use_admin_box():
                data = {k: v for k, v in data.items() if k.lower() != "minstock"}
            # Gleicher Duplicate-Check wie beim Bearbeiten (exclude_id=None,
            # da der Datensatz noch gar nicht existiert).
            if find_duplicate_yarn is not None:
                match = find_duplicate_yarn(data, exclude_id=None)
                if match and not confirm_save_despite_duplicate(self.new_yarn, *match):
                    return None
            data = dict(data)
            if not data.get("Name"):
                data["Name"] = "New Yarn"
            data["GlobalID"] = new_global_id()
            data["CreatedBy"] = (app_meta.current_user or {}).get("id")
            data["CreationDate"] = datetime.datetime.now()
            cols = list(data.keys())
            cols_sql = ", ".join(f"[{c}]" for c in cols)
            placeholders = ", ".join(["?"] * len(cols))
            sql = f"INSERT INTO [tblYarn] ({cols_sql}) VALUES ({placeholders})"
            # EINE Connection für Insert + lastrowid statt execute()+fetch_all(
            # 'SELECT @@IDENTITY') - Letzteres ziehen sich unabhängig eine
            # (nicht notwendigerweise dieselbe) Verbindung aus dem Pool, siehe
            # quick_add_colour()'s Docstring in screen_manage_yarn.py für den
            # empirisch nachgewiesenen Bug dahinter.
            from db.connection import get_connection
            with get_connection() as cn:
                cur = cn.cursor()
                cur.execute(sql, [data[c] for c in cols])
                cn.commit()
                new_id = cur.lastrowid
            return int(new_id) if new_id else None

        def _on_created(new_id):
            try:
                if hasattr(self, 'manage_yarn') and self.manage_yarn is not None:
                    self.manage_yarn.reload_data()
                    if new_id is not None:
                        self.manage_yarn._select_row_by_id(new_id)
            except Exception:
                pass
            self._go_back_manage_yarn()

        try:
            self.new_yarn._on_save = _create_save
            self.new_yarn._on_created = _on_created
            self.new_yarn.load_from_row({})  # alle Felder auf blank/leer zuruecksetzen
            self.new_yarn.set_minstock_locked(not app_meta.can_use_admin_box())
            self.new_yarn.set_audit_fields_visible(app_meta.is_superuser_level())
        except Exception:
            pass

        self.setWindowTitle("TrippleT – New Yarn")
        self.stack.setCurrentWidget(self.new_yarn)

    def _go_edit_yarn_form(self, row: Dict):
        """Öffnet den NewYarnScreen für einen bestehenden Yarn-Datensatz (Formular-
        Ansicht statt Pivot-Tabelle). MinStock bleibt für AdminBox=0-User gesperrt,
        alles andere ist editierbar - siehe screen_new_yarn.NewYarnScreen."""
        if not self._ensure_new_yarn_screen():
            QMessageBox.information(
                self, "Yarn", "'Edit in Form' ist derzeit nicht verfügbar.")
            return
        id_col = 'ID'
        yarn_id = row.get(id_col)

        def _update_save(data: Dict) -> Optional[int]:
            # Defense-in-depth: NewYarnScreen already strips MinStock from data
            # when locked, but re-check live here too rather than trust the
            # form's cached lock state alone.
            if not app_meta.can_use_admin_box():
                data = {k: v for k, v in data.items() if k.lower() != "minstock"}
            # Duplicate-Check vor dem Schreiben (Nutzerwunsch: "bei jedem
            # speichern/aktualisieren geprüft werden") - None signalisiert
            # NewYarnScreen._on_click_save(), bei "No" auf dem Formular zu
            # bleiben statt (fälschlich) Erfolg/Navigation auszulösen.
            if find_duplicate_yarn is not None:
                match = find_duplicate_yarn(data, exclude_id=yarn_id)
                if match and not confirm_save_despite_duplicate(self.new_yarn, *match):
                    return None
            cols = list(data.keys())
            if not cols:
                return yarn_id
            set_sql = ", ".join(f"[{c}] = ?" for c in cols)
            sql = f"UPDATE [tblYarn] SET {set_sql} WHERE [ID] = ?"
            execute(sql, [data[c] for c in cols] + [yarn_id])
            return yarn_id

        def _on_saved(_new_id=None):
            try:
                self.manage_yarn.reload_data()
                self.manage_yarn._select_row_by_id(yarn_id)
            except Exception:
                pass
            self._go_back_manage_yarn()

        try:
            self.new_yarn._on_save = _update_save
            self.new_yarn._on_created = _on_saved
            self.new_yarn.load_from_row(row)
            self.new_yarn.set_minstock_locked(not app_meta.can_use_admin_box())
            self.new_yarn.set_audit_fields_visible(app_meta.is_superuser_level())
        except Exception:
            pass

        self.setWindowTitle("TrippleT – Edit Yarn")
        self.stack.setCurrentWidget(self.new_yarn)

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
                self.yarn_stock = Screen(on_back_home=self._go_home, sidebar_callbacks=self._sidebar_nav_kwargs())
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

    def _go_my_requests_from_notification(self, request_id: int):
        """Von einer Experiment-Request-Notification aus (Statuswechsel,
        Aenderung akzeptiert/abgelehnt) zu 'My Requests' navigieren.

        Springt bewusst nicht direkt in den Bearbeiten-Screen (request_id
        koennte inzwischen geloescht sein, z.B. eine bereits akzeptierte/
        abgelehnte Kopie) - die Liste ist immer ein gueltiges Ziel."""
        self._go_my_requests()

    def _go_add_user(self):
        self.setWindowTitle("TrippleT – Manage User")
        self.stack.setCurrentWidget(self.manage_user)

    def _go_add_jet(self):
        self.setWindowTitle("TrippleT – Manage Jets")
        self.manage_jets.reload_data()
        self.manage_jets.set_read_only(not app_meta.can_use_admin_box())
        self.stack.setCurrentWidget(self.manage_jets)

    def _go_add_top_plate(self):
        self.setWindowTitle("TrippleT – Manage Top Plates")
        self.manage_top_plates.reload_data()
        self.manage_top_plates.set_read_only(not app_meta.can_use_admin_box())
        self.stack.setCurrentWidget(self.manage_top_plates)

    def _go_manage_order_type(self):
        self.setWindowTitle("TrippleT – Manage Order Type")
        self.manage_order_type.set_read_only(not app_meta.can_use_admin_box())
        self.stack.setCurrentWidget(self.manage_order_type)

    def _go_usage_stats(self):
        if not app_meta.is_superuser_level():
            return
        self.setWindowTitle("TrippleT – Usage Stats")
        self.usage_stats.reload_data()
        self.stack.setCurrentWidget(self.usage_stats)

    def _go_statistics(self):
        if not app_meta.is_superuser_level():
            return
        if self.stats_suite is None:
            self.stats_suite = StatsSuiteScreen(on_back_home=self._go_home, sidebar_callbacks=self._sidebar_nav_kwargs())
            self.stack.addWidget(self.stats_suite)
        self.setWindowTitle("TrippleT – Statistics")
        self.stats_suite.reload_data()
        self.stack.setCurrentWidget(self.stats_suite)

    def _go_offline_sync(self):
        if not app_meta.is_superuser_level():
            return
        if self.offline_sync is None:
            self.offline_sync = OfflineSyncScreen(on_back_home=self._go_home, sidebar_callbacks=self._sidebar_nav_kwargs())
            self.stack.addWidget(self.offline_sync)
        self.setWindowTitle("TrippleT – Offline Sync")
        self.stack.setCurrentWidget(self.offline_sync)

    def _go_tdms_inspector(self):
        # No is_superuser_level()/offline gate on purpose: this screen never
        # touches the database (see ui/screen_tdms_inspector.py docstring),
        # so it works for every logged-in user, including in offline mode.
        if self.tdms_inspector is None:
            self.tdms_inspector = TdmsInspectorScreen(on_back_home=self._go_home, sidebar_callbacks=self._sidebar_nav_kwargs())
            self.stack.addWidget(self.tdms_inspector)
        self.setWindowTitle("TrippleT – TDMS Inspector")
        self.stack.setCurrentWidget(self.tdms_inspector)

    def _go_lab_assistant(self):
        if not app_meta.is_superuser_level():
            return
        if self.lab_assistant is None:
            self.lab_assistant = LabAssistantScreen(on_back_home=self._go_home, sidebar_callbacks=self._sidebar_nav_kwargs())
            self.stack.addWidget(self.lab_assistant)
        self.setWindowTitle("TrippleT – Lab Assistant")
        self.stack.setCurrentWidget(self.lab_assistant)

    def _go_manage_product_groups(self):
        self.setWindowTitle("TrippleT – Manage Product Groups")
        self.manage_product_groups.set_read_only(not app_meta.can_use_admin_box())
        self.stack.setCurrentWidget(self.manage_product_groups)

    def _go_manage_material(self):
        self.setWindowTitle("TrippleT – Manage Material")
        self.manage_material.set_read_only(not app_meta.can_use_admin_box())
        self.stack.setCurrentWidget(self.manage_material)

    def _go_back_manage_jets(self):
        self.setWindowTitle("TrippleT – Manage Jets")
        self.manage_jets.set_read_only(not app_meta.can_use_admin_box())
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
            # This screen instance is shared with the read-only "View in Form"
            # path below - a previous visit there may have left it disabled/
            # showing the audit fields (which make no sense for a not-yet-
            # existing record).
            self.new_jet.set_read_only(False)
            self.new_jet.set_audit_fields_visible(False)
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
            self.new_jet.set_read_only(False)
            self.new_jet.set_audit_fields_visible(False)
        except Exception:
            try:
                self.new_jet.reset_form()
            except Exception:
                pass
        self.setWindowTitle("TrippleT – New Jet")
        self.stack.setCurrentWidget(self.new_jet)

    def _go_edit_jet_form(self, row: Dict):
        """Öffnet den NewJetScreen für einen bestehenden Jet: Save/Copy-User
        bearbeiten (UPDATE), read-only User sehen dasselbe Formular nur zur
        Ansicht (übersichtlicher pro Datensatz als die Pivot-Tabelle) - siehe
        NewJetScreen.set_read_only()."""
        id_col = self._jets_id_col or "ID"
        jet_id = row.get(id_col)
        read_only = not app_meta.can_use_admin_box()

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
            self.new_jet.set_read_only(read_only)
            self.new_jet.set_audit_fields_visible(app_meta.is_superuser_level())
        except Exception:
            pass

        # Button-Text anpassen
        try:
            self.new_jet.btn_save.setText("Save Changes")
        except Exception:
            pass

        self.setWindowTitle("TrippleT – View Jet" if read_only else "TrippleT – Edit Jet")
        self.stack.setCurrentWidget(self.new_jet)

    def _on_new_jet_created(self, new_id: int):
        try:
            self.manage_jets.reload_data(select_id=new_id)
        except Exception:
            pass
        self._go_back_manage_jets()

    def _go_back_manage_top_plates(self):
        self.setWindowTitle("TrippleT – Manage Top Plates")
        self.manage_top_plates.set_read_only(not app_meta.can_use_admin_box())
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
            # This screen instance is shared with the read-only "View in Form"
            # path below - a previous visit there may have left it disabled.
            self.new_top_plate.set_read_only(False)
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
            self.new_top_plate.set_read_only(False)
        except Exception:
            try:
                self.new_top_plate.reset_form()
            except Exception:
                pass
        self.setWindowTitle("TrippleT – New Top Plate")
        self.stack.setCurrentWidget(self.new_top_plate)

    def _go_edit_top_plate_form(self, row: Dict):
        """Öffnet den NewTopPlateScreen für eine bestehende Top Plate: Save/Copy-
        User bearbeiten (UPDATE), read-only User sehen dasselbe Formular nur zur
        Ansicht - siehe NewTopPlateScreen.set_read_only()."""
        id_col = self._top_plates_id_col or "ID"
        top_plate_id = row.get(id_col)
        read_only = not app_meta.can_use_admin_box()

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
            self.new_top_plate.set_read_only(read_only)
        except Exception:
            pass

        # Button-Text anpassen
        try:
            self.new_top_plate.btn_save.setText("Save Changes")
        except Exception:
            pass

        self.setWindowTitle("TrippleT – View Top Plate" if read_only else "TrippleT – Edit Top Plate")
        self.stack.setCurrentWidget(self.new_top_plate)

    def _on_new_top_plate_created(self, new_id: int):
        try:
            self.manage_top_plates.reload_data(select_id=new_id)
        except Exception:
            pass
        self._go_back_manage_top_plates()

    def _logout(self):
        # Tabs der vorherigen Session einsammeln, damit die nächste Anmeldung
        # nicht mit fremden, stehengebliebenen Tabs startet (Nutzerwunsch-
        # Ableitung, siehe closeEvent()-Docstring zur Tabs-Warnung).
        if getattr(self, "_tabs", None) is not None:
            self._tabs.close_all_but_first()
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