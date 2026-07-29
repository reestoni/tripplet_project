# TrippleT – Hinweise für Claude Code

Desktop-App (PySide6) für Textil-/Garnlabor-Tests (Heberlein). MySQL-Backend, historisch aus Access/ODBC migriert.

## Setup & Ausführen

- **Python-Interpreter**: `C:\Users\soj\AppData\Local\Programs\Python\Python312\python.exe` (nicht `.venv/`, das ist eine andere/unvollständige Umgebung ohne `pytest`).
- **DB-Modus**: `db/connection.py` liest `TRIPPLET_MODE` (`prod`/`dev`/`dev_local`). Beim Start aus dem Quellcode (`python main.py`) fragt `main.py` per Dialog danach (Default `prod`). Für Skripte/Tests: `os.environ["TRIPPLET_MODE"] = "dev_local"` **vor** dem ersten Import von `db.connection` setzen.
- **dev_local** = lokale MySQL-Instanz (`tripplet_dev_local`, localhost) – hier darf frei getestet/geschrieben werden. `dev`/`prod` liegen auf einem Remote-Server (10.50.212.60) – **niemals** ungefragt Schreiboperationen dort ausführen.
- Headless-Test: `QT_QPA_PLATFORM=offscreen` setzen, dann normal `QApplication`/Screens instanziieren.
- Tests: `python -m pytest tests/` (299 Tests, ~8s, alle grün).

## Architektur

- **`db/connection.py`**: Einzige DB-Zugriffsschicht. `get_connection()` liefert eine Connection aus einem lazy erzeugten `mysql.connector.pooling.MySQLConnectionPool` (Größe 5, `connect_timeout=10s`) – **niemals** direkt `mysql.connector.connect()` aufrufen. `_to_mysql_sql()` übersetzt Access-Syntax (`[Spalte]`, `?`-Platzhalter, `True`/`False`) automatisch zu MySQL – dadurch kann viel altes Access-SQL unverändert bleiben. Bekannter Quirk: der Klammer-Regex übersetzt auch `[...]` **innerhalb von String-Literalen** fälschlich (z. B. `LIKE '%[Gen]%'` bricht) – bei sowas lieber in Python filtern statt SQL-Pattern mit literalen Klammern zu bauen.
- **Zwei `fetch_all`-Funktionen existieren**: `db.connection.fetch_all` (Basis) und eine eigene, lowercase-normalisierende Variante in `ui/screen_show_experiment.py` (dort auch `table_exists`/`get_columns_map`/`resolve_field`/`norm` lokal reimplementiert bzw. reexportiert). Extrahierte Module (`machine_tab.py`, `screen_show_experiment_pdf_import.py`, `dty_yarnscope_tab.py`, `advisor_tab.py`) importieren diese Helfer **lazy** (innerhalb der Funktion) aus `ui.screen_show_experiment`, nicht aus `db.connection` – beim Patchen/Testen darauf achten, welche der beiden Funktionen man mockt.
- **`ui/screen_show_experiment.py`** (ShowExperimentScreen) ist der zentralste, größte Screen (Pivot-Tabelle: Zeilen = Messfelder, Spalten = Trials/Plies). Wurde in mehreren Schritten in eigene Module ausgelagert – siehe `TODO.md` für die Historie. Neue Tab-Typen dort folgen dem Muster `_ensure_XXX_tab` / `_build_XXX_tab` / `_remove_XXX_tab_if_exists`.
- **`ui/machine_tab.py`**: Machine-Data- und R&D-Machine-Data-Tab (ausgelagert aus ShowExperimentScreen). `fill_machine_row_from_title_impl()` nimmt `is_rd: bool` und muss **konsequent** die is_rd-abhängige `_model`/`_col_specs`-Variable verwenden statt hart `self.model_machine` – das war lange ein Bug (siehe `TODO.md`, jetzt gefixt).
- **`ui/text_normalize.py`**: gemeinsame Spaltennamen-Normalisierer (`norm`, `resolve_field`, `canon_simple`, `canon_with_id_strip`). Vor dem Anlegen einer neuen `_canon`/`_norm`-Variante in einem Screen prüfen, ob hier schon was Passendes existiert.
- **Pivot-Tabellen** (`PivotEditModel`/`MachinePivotModel` in `screen_show_experiment.py`, gerendert über `ui/widgets/frozen_first_column_table.py`): Bei potenziell vielen Spalten (Spalten = Trials, kann in die Hunderte gehen) **niemals** `resizeColumnsToContents()` ohne `fixed_data_column_width` verwenden – das ist O(Zeilen×Spalten) in Qt und war der dominante Perf-Bottleneck bei großen TrialSeries.
- **Monkey-Patch-Extraktion**: Mehrere Große Methoden aus `ShowExperimentScreen` wurden nach dem Muster "Modul-Funktion `xxx_impl(self, ...)` + dünner Wrapper `self._xxx(...)` in der Klasse" ausgelagert (siehe `advisor_tab.py`, `dty_yarnscope_tab.py`, `machine_tab.py`). Neue Extraktionen sollten demselben Muster folgen.

## Arbeitsweise, die sich bewährt hat

- Bei reinen Code-Verschiebungen (keine Verhaltensänderung beabsichtigt): Extraktion **skriptbasiert** per exakter Zeilen-Slicing + Dedent durchführen (kein manuelles Abtippen), danach per AST-Vergleich (`ast.get_source_segment`/`ast.dump` ohne Docstring) gegen das Original auf Byte-/Verhaltens-Identität prüfen.
- Für UI-Model-Änderungen: Cell-für-Cell-Diff (`model.data(index, role)` für alle Rollen) vor/nach der Änderung auf echten dev_local-Daten vergleichen, nicht nur Testsuite laufen lassen.
- Bei Performance-Fragen: mit `cProfile` messen, nicht raten. Lokale (dev_local) Latenz ist nicht repräsentativ für den echten Remote-Server – bei Query-Anzahl-Optimierungen (Roundtrips) im Hinterkopf behalten, dass das über eine langsame Verbindung viel mehr zählt als lokal.
- `git stash` (nur die betroffenen Dateien, nie pauschal) ist der bewährte Weg für Vorher/Nachher-Vergleiche im selben Arbeitsverzeichnis.
- `TODO.md` im Projekt-Root wird laufend als Fortschritts-/Entscheidungsprotokoll gepflegt – vor neuer Arbeit dort nachschauen, was schon geprüft/entschieden wurde (inkl. bewusst abgelehnter Ideen).

## Bekannte, bewusst zurückgestellte Punkte

- DB-Secrets-Setup (Klartext-Fallback `db_secrets.json`) bleibt unverändert – auf expliziten Wunsch, nicht erneut vorschlagen.
- `BaseScreen`-Basisklasse wurde geprüft und verworfen (Konstruktor-Signaturen der ~30 Screens zu inkonsistent für einen sicheren Umbau).
- Generisches Labormaschinen-Setup (Admin-Tool statt Code pro neuer Maschine) wurde prototypisch gebaut, getestet und auf Wunsch komplett zurückgerollt (Code + DB) – Details in der Git-Historie, falls das Thema nochmal aufkommt.
