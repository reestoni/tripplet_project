# TrippleT – Provisorische TODO-Liste (Code-Review 2026-07-29)

Basierend auf einer Architektur-/Qualitätsdurchsicht der Codebasis. Priorisierung ist ein Vorschlag, keine feste Reihenfolge.

## Kritisch / vermutete Bugs
- [x] Fehlschlagende Tests behoben (299/299 grün): `TestFixStabValues` – Tests riefen `_fix_stab_values()` noch mit alter Signatur ohne den (sinnvoll ergänzten) Pflichtparameter `expected_count` auf, Tests angepasst. `TestJetsSearch` – Fixture baute den Proxy manuell als generisches `QSortFilterProxyModel` statt `MultiColumnFilterProxy` und rief `_configure_filter_column()` nie auf, wodurch die Suche in der Fixture wirkungslos blieb; Fixture repariert, Produktionscode war nicht betroffen.
- [x] `MODE`-Umschaltung in `db/connection.py` – erledigt: Quellcode-Start (PyCharm/`python main.py`) fragt jetzt per Dialog (`main.py`, vor den `ui`-Imports) nach `prod`/`dev`/`dev_local` und setzt `TRIPPLET_MODE`; die gebaute .exe (`sys.frozen`) läuft immer hart auf `prod`, unabhängig von jeder Umgebungsvariable.
- [ ] `TestLoginScreenSicherheit::test_erfolgreicher_login_ruft_callback` und `test_falsches_passwort_ruft_keinen_success_callback` (`tests/test_tripplet_ui.py`) brauchen ~21s pro Test (vorbestehend, reproduziert auch auf dem allerersten Commit vor jeglichem Refactoring). Vermutung: `LoginScreen`/`check_credentials`-Umfeld hängt an einem unreachable-Host-Timeout gegen die Prod-DB, wenn sie aus dieser Sandbox/diesem Netz nicht erreichbar ist. Noch nicht untersucht, wo genau der Timeout herkommt.

## Architektur / Wartbarkeit
- [~] `ShowExperimentScreen` (`ui/screen_show_experiment.py`) aufteilen – ursprünglich eine Klasse mit 120+ Methoden auf ~8.900 Zeilen, jetzt 9.382 Gesamtzeilen in der Datei (Klasse selbst deutlich kleiner). **In Arbeit**, drei Extraktionen bisher, alle reiner Code-Move ohne Verhaltensänderung, jeweils mit vollem Testlauf + headless `main.py`-Import verifiziert:
  - `_statimat_import`/`_itemat_import` (~625 Zeilen) → `ui/screen_show_experiment_pdf_import.py` (Commit `4b3ae1a`)
  - YarnScope-(DTY)-Tab (~1050 Zeilen, war schon als Monkey-Patch-Funktionen geschrieben) → `ui/dty_yarnscope_tab.py` (Commit `404bd3b`)
  - Advisor-(agentT/Athena)-Tab (~400 Zeilen, ebenfalls schon Monkey-Patch-Funktionen) → `ui/advisor_tab.py` (Commit `9343b99`)

  Verbleibend: `_build_machine_tab` (967 Zeilen), `_f` (952 Zeilen) – beides echte Klassenmethoden (kein vorhandenes Monkey-Patch-Muster), daher voraussichtlich aufwändiger als die drei bisherigen Schritte.
- [ ] `screen_report.py`: ~5.200 Zeilen Modul-Level-Funktionen (Datenabfrage + PDF-Layout-Bausteine) in eigene Module trennen, z. B. `report_queries.py` / `report_pdf_layout.py`.
- [ ] Duplizierte Spalten-Normalisierungs-Helfer (`_canon`, `_resolve_field`, `_norm`) – aktuell in ~10 Screen-Dateien plus `db/connection.py` fast identisch reimplementiert – in ein gemeinsames Utility-Modul konsolidieren.
- [ ] Gemeinsame `BaseScreen`-Klasse einführen, um wiederkehrende Boilerplate zu reduzieren (aktuell erben alle ~30 Screens direkt von `QWidget`, geteilt wird nur `HeaderBar`/`FooterBar`).

## Fehlerbehandlung / Diagnose
- [ ] `logging`-Modul einführen (aktuell in `ui/`, `db/`, `main.py` nirgends verwendet) statt `print()` und stiller `except Exception: pass`-Blöcke (1.368 breite except-Blöcke repo-weit) – damit Fehler in Produktion überhaupt nachvollziehbar sind.
- [ ] Import-Guards in `main.py:48-104` (try/except um Screen-Importe, z. B. `ReportScreen`, `CanvasScreen`) mindestens loggen statt nur `print()`, damit ein stiller Feature-Ausfall auffällt.

## Aufräumen (niedrige Priorität)
- [ ] `pyodbc` aus `requirements.txt` entfernen, falls nach der Access→MySQL-Migration nicht mehr benötigt (parallel zu `mysql-connector-python` gelistet).
- [ ] Versionen in `requirements.txt` pinnen für reproduzierbare Builds (aktuell komplett ungepinnt).
- [ ] `ui/screen_new.py`: Platzhalter-Klasse heißt noch `ManageYarnScreen` statt eines neutralen Namens – Verwechslungsgefahr beim Copy-Paste für neue Screens.

## Bekannt, bewusst zurückgestellt
- DB-Secrets-Setup (Klartext-Fallback `db_secrets.json`, gebündelter Fernet-Key) – laut vorheriger Entscheidung unverändert lassen, kein Handlungsbedarf hier.
