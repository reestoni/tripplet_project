# TrippleT – Automatisierte Tests

Dieses Verzeichnis enthält die vollständige Test-Suite für TrippleT.
299 Tests auf drei Stufen stellen sicher, dass Refactorings, neue Features
und Bugfixes keine unbemerkte Regression einführen.

---

## Schnellstart

```bash
cd TrippleT_project
pytest tests/ -v
```

Alle 299 Tests laufen in unter 10 Sekunden.

---

## Teststruktur

| Datei | Stufe | Was wird getestet | Tests |
|---|---|---|---|
| `test_tripplet_complete.py` | **Unit** | Reine Logik ohne DB oder UI | 187 |
| `test_tripplet_ui.py` | **UI** | Screens, TableModels, Widget-Zustand | 70 |
| `test_tripplet_regression.py` | **Regression** | Echte TDMS- und PDF-Files | 35 |
| | | **Total** | **299** |

### Stufe 3 – Unit Tests
Kein Qt, kein DB-Zugriff nötig. Testet isolierte Python-Logik:

- **ITEMAT-Parser** – Zahlenparsing, OCR-Fehlerkorrektur, Versuchsnr.-Erkennung
- **Statimat-Parser** – Feinheit, Dehnung, Festigkeit, Geräte-Erkennung
- **DTY-Analyse** – Otsu-Schwelle, Hysterese-Labeling, Knoten-Klassifizierung,
  Statistik-Funktionen, `analyze_series`-Pipeline
- **Dickstellen-Analyse** – Erkennung, Feature-Berechnung, Histogramme, DB-Werte
- **DB-Layer** – SQL-Übersetzung (Access → MySQL), Passwort-Hashing, Hilfsfunktionen

### Stufe 4 – UI Tests
Braucht PySide6. Kein echter DB-Zugriff – alle DB-Calls werden gemockt:

- **LoginScreen** – Button-Logik, Passwort-Sicherheitsprüfung, Login-Callbacks
- **ManageJetsScreen** – Widget-Präsenz, Suche/Filter, `_to_bool`, `_to_int_like`
- **JetsTableModel** – Daten, Dirty-Tracking, Headers
- **ManageYarnScreen** – Widget-Präsenz, DPF-Berechnung, Read-only-Flags
- **NewJetScreen** – Editor-Typen (ComboBox/CheckBox/LineEdit), Pflichtfeld-Validierung

### Stufe 5 – Regressionstests
Läuft gegen echte Messdaten. Pinnt die Ausgabe der Analyse-Pipeline auf bekannte
Goldwerte – schlägt Alarm wenn ein Refactoring die Ergebnisse verändert:

- **DTY-Signal** `271_24_130426_1255.tdms` – Schwellwert, Knoten/m, ABC-Counts,
  Statistik-Felder, Hysterese-Grenzen (21 Tests, deterministisch)
- **Statimat-PDF** `419.pdf` – Header, Spulennummer, Feinheit, Dehnung, Festigkeit
  (14 Tests, exakte Werte)

---

## Voraussetzungen

```bash
pip install pytest pytest-qt pytest-mock nptdms pdfplumber
```

Für die Regressionstests müssen die Messdateien in `tests/fixtures/` liegen:

```
tests/fixtures/
├── 271_24_130426_1255.tdms   # nicht im Repo (proprietär)
├── 419.pdf                   # nicht im Repo (proprietär)
├── golden_dty_271_24.json    # im Repo – Golden Output DTY
└── golden_statimat_419.json  # im Repo – Golden Output Statimat
```

Fehlen die TDMS- oder PDF-Files, werden die entsprechenden Tests mit
`SKIPPED` übersprungen – kein Fehler, kein Abbruch.

---

## Nützliche Befehle

Nur eine Stufe laufen lassen:
```bash
pytest tests/test_tripplet_complete.py -v    # Unit (schnell, ~3s)
pytest tests/test_tripplet_ui.py -v          # UI
pytest tests/test_tripplet_regression.py -v  # Regression
```

Nur fehlgeschlagene Tests anzeigen:
```bash
pytest tests/ -v --tb=short -q
```

HTML-Report generieren:
```bash
pytest tests/ --html=tests/report.html --self-contained-html -q
```

---

## Golden Outputs aktualisieren

Wenn eine bewusste Änderung an der Analyse-Pipeline die Ausgabe verändert
(z.B. neuer Algorithmus), müssen die Golden-Output-JSONs neu generiert werden:

```bash
python tests/update_golden_outputs.py
```

> Dieses Skript existiert noch nicht – bei Bedarf anlegen.
> Vorher prüfen ob die neue Ausgabe fachlich korrekt ist!

---

## Konventionen

- Testklassen beginnen mit `Test`, Testmethoden mit `test_`
- Deutsch als Sprache für Testnamen (konsistent mit der Codebasis)
- Kein echter DB-Zugriff in Unit- und UI-Tests – immer mocken
- Neue Features → neuer Test in der passenden Stufe
