# TrippleT – Provisorische TODO-Liste (Code-Review 2026-07-29)

Basierend auf einer Architektur-/Qualitätsdurchsicht der Codebasis. Priorisierung ist ein Vorschlag, keine feste Reihenfolge.

## Kritisch / vermutete Bugs
- [x] Fehlschlagende Tests behoben (299/299 grün): `TestFixStabValues` – Tests riefen `_fix_stab_values()` noch mit alter Signatur ohne den (sinnvoll ergänzten) Pflichtparameter `expected_count` auf, Tests angepasst. `TestJetsSearch` – Fixture baute den Proxy manuell als generisches `QSortFilterProxyModel` statt `MultiColumnFilterProxy` und rief `_configure_filter_column()` nie auf, wodurch die Suche in der Fixture wirkungslos blieb; Fixture repariert, Produktionscode war nicht betroffen.
- [x] `MODE`-Umschaltung in `db/connection.py` – erledigt: Quellcode-Start (PyCharm/`python main.py`) fragt jetzt per Dialog (`main.py`, vor den `ui`-Imports) nach `prod`/`dev`/`dev_local` und setzt `TRIPPLET_MODE`; die gebaute .exe (`sys.frozen`) läuft immer hart auf `prod`, unabhängig von jeder Umgebungsvariable.
- [ ] `TestLoginScreenSicherheit::test_erfolgreicher_login_ruft_callback` und `test_falsches_passwort_ruft_keinen_success_callback` (`tests/test_tripplet_ui.py`) brauchen ~21s pro Test (vorbestehend, reproduziert auch auf dem allerersten Commit vor jeglichem Refactoring). Vermutung: `LoginScreen`/`check_credentials`-Umfeld hängt an einem unreachable-Host-Timeout gegen die Prod-DB, wenn sie aus dieser Sandbox/diesem Netz nicht erreichbar ist. Noch nicht untersucht, wo genau der Timeout herkommt.

## Architektur / Wartbarkeit
- [x] `ShowExperimentScreen` (`ui/screen_show_experiment.py`) aufteilen – ursprünglich eine Klasse mit 120+ Methoden auf ~8.900 Zeilen. Jetzt 7.706 Zeilen in `screen_show_experiment.py`, fünf Extraktionen, alle reiner Code-Move ohne Verhaltensänderung, jeweils mit vollem Testlauf + headless `main.py`-Import verifiziert:
  - `_statimat_import`/`_itemat_import` (~625 Zeilen) → `ui/screen_show_experiment_pdf_import.py` (Commit `4b3ae1a`)
  - YarnScope-(DTY)-Tab (~1050 Zeilen, war schon als Monkey-Patch-Funktionen geschrieben) → `ui/dty_yarnscope_tab.py` (Commit `404bd3b`)
  - Advisor-(agentT/Athena)-Tab (~400 Zeilen, ebenfalls schon Monkey-Patch-Funktionen) → `ui/advisor_tab.py` (Commit `9343b99`)
  - `_build_machine_tab` (966 Zeilen, echte Klassenmethode, kein vorhandenes Monkey-Patch-Muster) → `ui/machine_tab.py`. Zusätzlich zu Testlauf + headless-Import verifiziert per Cell-für-Cell-Diff des `model_machine`/`model_rd_machine`-Grids gegen 3 reale dev_local-TrialSeries (u.a. die MachineID=4 YarnUse-Gruppierung) vor/nach der Extraktion – Ergebnis byte-identisch.
  - `_build_rd_machine_tab` (432 Zeilen) → ebenfalls nach `ui/machine_tab.py`. Gleiche Verifikation (Testlauf, headless-Import, Cell-für-Cell-Diff inkl. R&D-Grid gegen dieselben TrialSeries, alle mit echten RDSetting=1-Feldern) – byte-identisch.
  - `_fill_machine_row_from_title` (300 Zeilen) → ebenfalls nach `ui/machine_tab.py`. Da diese Methode Dialoge öffnet (Fill-Range-Feature), zusätzlich per Funktionstest mit gemockten Dialog-Klassen verifiziert (Housing-, Jet-, Dropdown- und Text-Zeile, je einmal für Machine- und R&D-Tab) – Grid-Ergebnis byte-identisch vor/nach der Extraktion. Dabei bestätigt: eine vorbestehende Eigenheit (bei `is_rd=True` schreibt die Methode fälschlich immer auf `model_machine` statt `model_rd_machine`) wurde unverändert mitgenommen, nicht "repariert".

  Damit ist die ShowExperimentScreen-Aufteilung aus dem Code-Review abgeschlossen. `screen_show_experiment.py` (7.706 Z.) + `ui/machine_tab.py` (1.748 Z.) zusammen sind etwas größer als die ursprüngliche Datei, weil jede Extraktion Header/Docstring/Lazy-Imports hinzufügt – aber deutlich besser navigierbar als eine einzelne 9.382-Zeilen-Datei.
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

## Feature-Idee (vom User, 2026-07-29)
- [ ] Neue Labormaschine (z.B. neues Prüfgerät) erfordert aktuell Code-Änderungen: neuer Tab in `ShowExperimentScreen` (`_build_XXX_tab`), neue DB-Tabelle, i.d.R. neuer PDF-Import-Parser. Idee: generischeres Setup, z.B. ein kleines Admin-Tool, mit dem eine neue Maschine ohne Code-Änderung angelegt werden kann.
  - Einschätzung: Der Tab-Teil (Tabelle/Pivot-Ansicht auf einer DB-Tabelle mit editierbaren Spalten) lässt sich vermutlich gut generisch/konfigurationsgetrieben lösen – die bestehenden Tabs folgen alle demselben Muster (Tabelle + Spalten-Mapping + Pivot-Editor). Ein Admin-Screen, der "Maschine anlegen: Zieltabelle X, Spalten Y, Labels Z" erlaubt, könnte einen guten Teil von `_build_XXX_tab` ersetzen.
  - Der PDF-Import-Teil ist vermutlich NICHT generisch lösbar: jedes Gerät/jeder Hersteller hat ein anderes Report-Layout (siehe `statimat_pdf_parser.py` vs. `itemat_pdf_parser.py` – strukturell komplett unterschiedlich). Ein neuer Parser pro Maschine bleibt wahrscheinlich Handarbeit, egal wie generisch der Rest wird.
  - Empfehlung: zweigeteilt angehen – Tab/DB-Anbindung generisch+admin-konfigurierbar, PDF-Parsing weiterhin als expliziter Code-Baustein pro Maschine (aber mit klarer Schnittstelle, damit er sich einfach andocken lässt).

## Bekannt, bewusst zurückgestellt
- DB-Secrets-Setup (Klartext-Fallback `db_secrets.json`, gebündelter Fernet-Key) – laut vorheriger Entscheidung unverändert lassen, kein Handlungsbedarf hier.
