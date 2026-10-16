# ui/widgets/help_texts_show_experiment.py
"""Hilfetexte Show Experiment (EN/DE/ES) fuer ui/widgets/multilang_help.py.

Spiegelt ui/screen_show_experiment.py (Werkzeugleiste in _build_ui, Kontext-
menues: _MachineContextMenuFilter -> Copy trials / Reference samples /
Manage plies / Fill row / Custom Group, Retest-Flag ueber den Spaltenkopf der Labor-Tabs, Shortcuts
Ctrl+S/F5/Ctrl+C/Ctrl+V, Read-only ab Level <= 1) und ui/machine_tab.py.
Bei Aenderungen dort hier (alle 3 Sprachen) und in
assets/images/help_show_experiment.svg nachziehen.
"""

SVG = "assets/images/help_show_experiment.svg"
SVG_W, SVG_H = 940, 384

LAB_TABS = ("Titer, Jet Air Consumption, Statimat M, Statimat DS, EKB, Hot Air Shrinkage, Hot Water Shrinkage, "
            "ATY Shrinkage, Waterbath, Itemat Lab, Itemat Plus, DTYoMat, ATYoMat, Rapid 600")


def B(name: str) -> str:
    return f"<b>[{name}]</b>"


def M(name: str) -> str:
    return f"<b>{name}</b>"


TEXTS = {
    # ═══════════════════════════════ EN ═══════════════════════════════
    "en": {
        "window_title": "How does Show Experiment work?",
        "close": "Close",
        "tabs": [
            {"key": "tasks", "title": "How do I…?", "blocks": [
                ("p", "Show Experiment shows one trial series: all trials side by side, with machine settings and "
                      "lab results. Numbers (1)–(7) refer to the <i>Screen guide</i> tab."),
                ("task", "Open a series I used recently",
                 ["In the sidebar, click <b>Recent</b> (at the bottom, above Account).",
                  "Click the series. Ctrl+click opens it in a new tab."],
                 "The last 8 series you opened, newest first - on every PC you log in."),
                ("h", "Entering data"),
                ("task", "Enter or change a value",
                 ["Click the cell (7) and type the value, or double-click to edit it. Press Enter - you land in the cell below for the next value (Shift+Enter goes up).",
                  f"Click {B('Save')} or press Ctrl+S."],
                 "Changed cells stay <b>yellow</b> until you save; the button shows how many, e.g. "
                 f"{B('Save (3)')}, and the tab gets a dot (●). If you leave the screen, close the tab or the "
                 "program with unsaved changes, TrippleT asks whether to save them. "
                 "With access level 1 the screen is read-only."),
                ("task", "Set the same value for many trials",
                 ["In <i>Machine Data</i> or <i>R&amp;D Machine Data</i>, right-click the parameter name in the "
                  "first column (6) → " + M("Fill row") + ".",
                  "Choose the value and the range of trials, then OK.",
                  f"Click {B('Save')}."],
                 "Right-clicking a merged cell offers " + M("Fill row…") + " as well."),
                ("task", "See who changed a value and when",
                 ["Right-click the value → " + M("Change history…") + ".",
                  "The list shows every change with date, person, old and new value, newest first. "
                  "Tick <i>Show all changes in this trial series</i> for the whole series."],
                 "Superusers only. Recorded are changes saved in Show Experiment and Statimat/Itemat PDF imports, "
                 "since October 2026."),
                ("task", "Warning \"Unusual values\" when saving",
                 ["TrippleT compares changed machine settings with all earlier trials of the same machine. "
                  "A value far outside the usual range (e.g. 35 instead of 3.5 bar) is listed.",
                  f"{B('Go back and check')} jumps to the first such value; {B('Save anyway')} saves as it is."],
                 "Only a hint - unusual values are allowed. Lab values are not checked (they depend on the yarn)."),
                ("task", "Copy and paste values",
                 ["Select cells and press Ctrl+C, then select the target cell and press Ctrl+V.",
                  f"Click {B('Save')}."],
                 "Works between tables and with Excel."),
                ("task", "Make the text bigger and the tables easier to read",
                 [f"In the sidebar under <i>Account</i>, click {B('Settings')}.",
                  "Under <i>Text size</i> choose Normal, Large, Extra large or Huge - for the whole program "
                  "(applies after a restart; TrippleT offers to restart right away). "
                  "Under <i>Show Experiment tables</i> switch on, if needed, <i>High contrast</i> and <i>Crosshair</i> (highlights the row and column of "
                  "the selected cell, so you can see which trial and parameter a value belongs to).",
                  "<i>Reading bar</i> shows the selected value in large words below the table, e.g. "
                  "\"V2 · Ply 1 · Air Pressure (bar) = 3.50\". <i>Mark warnings with a symbol</i> adds a circle "
                  "(out of tolerance) or triangle (check) to highlighted values. <i>Colour-blind friendly colours</i> "
                  "avoids red/green.",
                  "Check the preview, then click " + B("Save") + "."],
                 "Quick zoom in a table: Ctrl + mouse wheel or Ctrl +/-, Ctrl+0 resets to normal. The settings are "
                 "saved for your login and apply on every PC. The welcome message and the accent colour are also "
                 "set in Settings."),
                ("task", "Hide rows you don't need (Machine Data)",
                 ["Right-click the parameter name in the first column (6) → " + M("Hide row") + ". "
                  "To hide several rows at once, first select their names (Ctrl+click), then right-click one of them.",
                  "Where rows are hidden, a blue line is shown on the parameter name. Point at it to see which "
                  "rows are hidden there, click it to show them again.",
                  f"To show all rows again, click {B('n rows hidden')} in the toolbar above the table → "
                  + M("Show all rows") + ". There you can also show single rows."],
                 "Hidden rows are remembered per user and machine, i.e. for all series on this machine. Only the "
                 "view changes: the values stay saved. Copy and paste skip hidden rows. A red line means a hidden "
                 "row contains a highlighted value."),
                ("task", "Import a Statimat or Itemat report",
                 [f"Click {B('Statimat import')} or {B('Itemat import')} in the toolbar (1).",
                  "Choose the PDF report. The values are filled into the matching lab tab.",
                  f"Check the values, then click {B('Save')}."]),
                ("h", "Trials and plies"),
                ("task", "Add new trials",
                 ["Click the <b>+</b> icon (add trial) on the right of (2). Create Experiment opens in the mode for adding trials to this series."]),
                ("task", "Copy existing trials",
                 [f"Click {B('Copy trials')} on the right of (2), or right-click a trial number (4) → "
                  + M("Copy trials…") + ".",
                  "Tick the trials to copy (Shift+click ticks a whole range). Trials whose columns you selected "
                  "in the table are already ticked.",
                  "Choose how often and the order: <i>Repeat the block</i> (V1 V2 | V1 V2) or <i>Each trial in "
                  "a row</i> (V1 V1 | V2 V2).",
                  "Check the result table: if needed, change values of the copies there (e.g. another air "
                  "pressure or jet; on ATY also OF Core / OF Effect). Changed cells are highlighted. "
                  "<i>Show all fields</i> shows the other machine settings.",
                  f"Click {B('Copy n trials')}."],
                 "Machine settings and plies are copied. Lab values, comments and the yarn tensions before/after "
                 "the jet of the copies stay empty. The new trials are added at the end and highlighted in the "
                 "table. Values per ply (e.g. T1/T2 tension) are changed afterwards in the table or in "
                 "<i>Manage plies</i>. Reference samples are never copied."),
                ("task", "Add a reference sample (e.g. a customer's original spool)",
                 [f"Click {B('+ Ref')} on the right of (2), or right-click a trial number (4) → "
                  + M("Add reference sample…") + ".",
                  "Enter a name (e.g. customer, article, lot) and confirm.",
                  "Type in its lab values in the lab tabs (the Statimat/Itemat PDF imports only match trial "
                  "numbers, so they don't fill a reference sample). Machine data is optional, e.g. for hints "
                  "from the customer."],
                 "A reference sample is a benchmark, not a trial: it doesn't use up a trial number, is shown first "
                 "as <b>Ref</b> with an amber background (the name is in the tooltip), drawn as a horizontal line in "
                 "the report charts and left out of statistics, Smart Chart, Quick Scan, Athena and the jet data "
                 "export. Right-click the trial number of an existing trial to turn it into a reference sample "
                 "(it keeps its number) or back, or to rename it."),
                ("task", "Change the plies or yarns of a trial",
                 ["Right-click the ply row (5) of that trial → the <i>Manage plies</i> dialog opens."]),
                ("task", "Add another trial series or lab machines",
                 ["Use " + M("Add Trial Series") + " or " + M("Add Lab Machines") + " in the sidebar."],
                 "A lab tab (e.g. Statimat M) appears as soon as a lab machine is assigned to the series."),
                ("h", "Lab results and retests"),
                ("task", "Flag a lab value for retesting (superusers)",
                 ["Open the lab tab, right-click the column header of the trial → " + M("Flag Vn for retest…") + ".",
                  "Enter a note if you like (optional) and confirm."],
                 "The series goes back into the Backlog with top priority and shows <b>RETEST</b> there."),
                ("h", "Files, reports and labels"),
                ("task", "Attach images or PDFs",
                 [f"Click {B('Upload images')} or {B('Upload PDFs')} and choose the files.",
                  "As soon as something is attached, an image and a PDF icon appear next to these buttons. Click them to see the files."]),
                ("task", "Open a report of this series",
                 ["The report icon (chart symbol) in the toolbar (1) opens a new report with charts for this series.",
                  f"If saved reports exist, a list and {B('Go!')} appear next to it: choose the report and click Go!."],
                 "See the help in the Report screen for details."),
                ("task", "Print labels with the trial numbers",
                 ["Click the label icon in (2), choose the start position on the sheet, save the PDF and print it."]),
                ("task", "See the linked experiment request",
                 ["Click the <b>ER</b> icon in (2). It is shown when a request is linked."]),
                ("task", "Reload the screen",
                 [f"Click {B('↻')} or press F5. The open tab stays selected."]),
            ]},
            {"key": "screen", "title": "Screen guide", "blocks": [
                ("svg", SVG, {"lab_hint": "(lab tabs appear only if used)",
                              "keys_hint": "Enter next cell down · Ctrl+C / Ctrl+V copy and paste · Delete clears the selected cells · Ctrl+Z undo, Ctrl+Y redo · Ctrl+S save · F5 reload"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Toolbar", "Experiment ID and series, attachments (upload and show images/PDFs), Statimat and "
                                    "Itemat import, report icon and saved reports (list + Go!), reload (↻), Save and this help."),
                    ("(2) Material line", "Material of the series, linked experiment request (ER), machine info, "
                                          "trial labels, <b>+T</b> (add trials), <b>+ Ref</b> (add reference sample) and "
                                          "<b>Copy trials</b>."),
                    ("(3) Tabs", "One tab per kind of data, see the <i>Tabs</i> tab. Lab tabs only appear if the "
                                 "series uses that lab machine."),
                    ("(4) Trial row", "Trial numbers (V1, V2, …); reference samples come first as <b>Ref</b> "
                                      "(amber). Right-click: copy trials, reference samples."),
                    ("(5) Ply row", "Ply of each column (a trial can have several plies). Right-click: manage plies."),
                    ("(6) Parameter names", "One row per parameter. Right-click: fill row, show/hide the custom group."),
                    ("(7) Cells", "Values per trial. Editable where a value can be stored; changed cells wait for "
                                  "Save."),
                ]),
            ]},
            {"key": "tabs", "title": "Tabs", "blocks": [
                ("areas", [
                    ("Machine Data", "Machine settings per trial (speed, overfeed, air pressure, jet, …). Rows are "
                                     "parameters, columns are trials and plies. On DTY machines the row <i>D/Y Ratio (T2/T1)</i> "
                                     "below T2 Tension is calculated automatically from T1 and T2 and cannot be edited."),
                    ("R&amp;D Machine Data", "Additional development parameters, same operation as Machine Data."),
                    ("Lab tabs", f"{LAB_TABS}. Results of the lab devices per trial; each appears only if the "
                                 "series uses that device. Right-click a column header to flag a retest."),
                    ("YarnScope / YarnScope ATY", "Analysis of the yarn measurement files with their own sub-tabs "
                                                  "(e.g. signal, yarn profile, process comparison)."),
                    ("Athena", "AI assistant that analyses the series and suggests next steps. The last analysis is "
                               "kept; a new analysis takes a moment."),
                    ("Notes", "Free-text notes for the series."),
                ]),
                ("note", "<b>Tip:</b> Ctrl+click a series in the Backlog or All Experiments to open it in an "
                         "additional tab, e.g. to compare two series."),
            ]},
        ],
    },

    # ═══════════════════════════════ DE ═══════════════════════════════
    "de": {
        "window_title": "Wie funktioniert Show Experiment?",
        "close": "Schliessen",
        "tabs": [
            {"key": "tasks", "title": "Wie mache ich…?", "blocks": [
                ("p", "Show Experiment zeigt eine Versuchsserie: alle Versuche nebeneinander, mit Maschineneinstellungen "
                      "und Laborresultaten. Die Nummern (1)–(7) verweisen auf den Tab <i>Bildschirm</i>."),
                ("task", "Eine kürzlich geöffnete Serie wieder öffnen",
                 ["In der Sidebar auf <b>Recent</b> klicken (unten, über Account).",
                  "Die Serie anklicken. Strg+Klick öffnet sie in einem neuen Tab."],
                 "Die letzten 8 geöffneten Serien, neueste zuerst - auf jedem PC, an dem du dich anmeldest."),
                ("h", "Daten erfassen"),
                ("task", "Einen Wert eingeben oder ändern",
                 ["Die Zelle (7) anklicken und den Wert eintippen, oder doppelklicken zum Bearbeiten. Enter drücken - du landest in der Zelle darunter für den nächsten Wert (Umschalt+Enter geht nach oben).",
                  f"Auf {B('Save')} klicken oder Strg+S drücken."],
                 "Geänderte Zellen bleiben <b>gelb</b>, bis gespeichert ist; der Knopf zeigt die Anzahl, z.&nbsp;B. "
                 f"{B('Save (3)')}, und der Tab bekommt einen Punkt (●). Verlässt du den Bildschirm oder schliesst "
                 "den Tab oder das Programm mit ungespeicherten Änderungen, fragt TrippleT, ob gespeichert werden soll. "
                 "Mit Access Level 1 ist der Bildschirm nur lesbar."),
                ("task", "Denselben Wert für viele Versuche setzen",
                 ["In <i>Machine Data</i> oder <i>R&amp;D Machine Data</i> mit Rechtsklick auf den Parameternamen in der "
                  "ersten Spalte (6) → " + M("Fill row") + ".",
                  "Wert und Versuchsbereich wählen, dann OK.",
                  f"Auf {B('Save')} klicken."],
                 "Ein Rechtsklick auf eine zusammengefasste Zelle bietet ebenfalls " + M("Fill row…") + " an."),
                ("task", "Sehen, wer einen Wert wann geändert hat",
                 ["Rechtsklick auf den Wert → " + M("Change history…") + ".",
                  "Die Liste zeigt jede Änderung mit Datum, Person, altem und neuem Wert, die neueste zuoberst. "
                  "Mit <i>Show all changes in this trial series</i> sieht man die ganze Serie."],
                 "Nur für Superuser. Erfasst werden in Show Experiment gespeicherte Änderungen und "
                 "Statimat-/Itemat-PDF-Importe, seit Oktober 2026."),
                ("task", "Warnung \"Unusual values\" beim Speichern",
                 ["TrippleT vergleicht geänderte Maschineneinstellungen mit allen früheren Versuchen derselben "
                  "Maschine. Ein Wert weit ausserhalb des Üblichen (z.&nbsp;B. 35 statt 3.5 bar) wird aufgelistet.",
                  f"{B('Go back and check')} springt zum ersten solchen Wert, {B('Save anyway')} speichert trotzdem."],
                 "Nur ein Hinweis - ungewöhnliche Werte sind erlaubt. Laborwerte werden nicht geprüft (sie hängen "
                 "vom Garn ab)."),
                ("task", "Werte kopieren und einfügen",
                 ["Zellen markieren und Strg+C drücken, dann die Zielzelle wählen und Strg+V drücken.",
                  f"Auf {B('Save')} klicken."],
                 "Funktioniert zwischen Tabellen und mit Excel."),
                ("task", "Text grösser und Tabellen besser lesbar machen",
                 [f"In der Sidebar unter <i>Account</i> auf {B('Settings')} klicken.",
                  "Unter <i>Text size</i> Normal, Large, Extra large oder Huge wählen - gilt fürs ganze Programm "
                  "(nach einem Neustart; TrippleT bietet an, gleich neu zu starten). "
                  "Unter <i>Show Experiment tables</i> bei Bedarf <i>High contrast</i> und <i>Crosshair</i> einschalten (hebt Zeile und Spalte der "
                  "gewählten Zelle hervor, damit man sieht, zu welchem Versuch und Parameter ein Wert gehört).",
                  "<i>Reading bar</i> zeigt den gewählten Wert gross in Worten unter der Tabelle, z.&nbsp;B. "
                  "\"V2 · Ply 1 · Air Pressure (bar) = 3.50\". <i>Mark warnings with a symbol</i> setzt einen Kreis "
                  "(ausserhalb der Toleranz) oder ein Dreieck (prüfen) vor markierte Werte. <i>Colour-blind friendly "
                  "colours</i> verzichtet auf Rot/Grün.",
                  "Die Vorschau prüfen, dann auf " + B("Save") + " klicken."],
                 "Schnell zoomen in einer Tabelle: Strg + Mausrad oder Strg +/-, Strg+0 setzt auf normal zurück. Die "
                 "Einstellungen gelten für dein Login an jedem PC. Auch Willkommensnachricht und Akzentfarbe werden "
                 "unter Settings eingestellt."),
                ("task", "Nicht benötigte Zeilen ausblenden (Machine Data)",
                 ["Rechtsklick auf den Parameternamen in der ersten Spalte (6) → " + M("Hide row") + ". "
                  "Für mehrere Zeilen auf einmal zuerst ihre Namen markieren (Strg+Klick), dann auf einen davon "
                  "rechtsklicken.",
                  "Wo Zeilen ausgeblendet sind, steht eine blaue Linie am Parameternamen. Mit der Maus darauf "
                  "zeigen, um zu sehen, welche Zeilen dort fehlen; ein Klick darauf blendet sie wieder ein.",
                  f"Alle Zeilen wieder einblenden: in der Leiste über der Tabelle auf {B('n rows hidden')} → "
                  + M("Show all rows") + ". Dort lassen sich auch einzelne Zeilen einblenden."],
                 "Ausgeblendete Zeilen werden pro Benutzer und Maschine gemerkt, gelten also für alle Serien dieser "
                 "Maschine. Es ändert sich nur die Ansicht, die Werte bleiben gespeichert. Kopieren und Einfügen "
                 "überspringen ausgeblendete Zeilen. Eine rote Linie bedeutet, dass eine ausgeblendete Zeile einen "
                 "markierten Wert enthält."),
                ("task", "Einen Statimat- oder Itemat-Bericht importieren",
                 [f"In der Werkzeugleiste (1) auf {B('Statimat import')} oder {B('Itemat import')} klicken.",
                  "Den PDF-Bericht wählen. Die Werte werden in den passenden Labor-Tab eingetragen.",
                  f"Werte prüfen, dann auf {B('Save')} klicken."]),
                ("h", "Versuche und Plies"),
                ("task", "Neue Versuche hinzufügen",
                 ["Rechts in (2) auf das <b>+</b>-Symbol (Versuch hinzufügen) klicken. Create Experiment öffnet sich im Modus zum Hinzufügen von Versuchen zu dieser Serie."]),
                ("task", "Bestehende Versuche kopieren",
                 [f"Rechts in (2) auf {B('Copy trials')} klicken oder Rechtsklick auf eine Versuchsnummer (4) → "
                  + M("Copy trials…") + ".",
                  "Die zu kopierenden Versuche anhaken (Shift+Klick hakt einen ganzen Bereich an). Versuche, deren "
                  "Spalten in der Tabelle markiert sind, sind schon angehakt.",
                  "Anzahl und Reihenfolge wählen: <i>Repeat the block</i> (V1 V2 | V1 V2) oder <i>Each trial in "
                  "a row</i> (V1 V1 | V2 V2).",
                  "Die Ergebnistabelle prüfen: bei Bedarf dort Werte der Kopien ändern (z.&nbsp;B. anderer Luftdruck "
                  "oder Jet; bei ATY auch OF Core / OF Effect). Geänderte Zellen werden hervorgehoben. "
                  "<i>Show all fields</i> zeigt die übrigen Maschineneinstellungen.",
                  f"Auf {B('Copy n trials')} klicken."],
                 "Maschineneinstellungen und Plies werden kopiert. Die Laborwerte, Kommentare und die "
                 "Fadenspannungen vor/nach Jet der Kopien bleiben leer. Die neuen Versuche werden hinten angehängt und in der Tabelle "
                 "markiert. Werte pro Ply (z.&nbsp;B. T1/T2-Spannung) werden danach in der Tabelle oder in "
                 "<i>Manage plies</i> geändert. Referenzmuster werden nie mitkopiert."),
                ("task", "Ein Referenzmuster hinzufügen (z.&nbsp;B. Originalspule eines Kunden)",
                 [f"Rechts in (2) auf {B('+ Ref')} klicken oder Rechtsklick auf eine Versuchsnummer (4) → "
                  + M("Add reference sample…") + ".",
                  "Einen Namen eingeben (z.&nbsp;B. Kunde, Artikel, Los) und bestätigen.",
                  "Die Laborwerte in den Labor-Tabs von Hand eintragen (die Statimat-/Itemat-PDF-Importe ordnen "
                  "nur über Versuchsnummern zu und füllen ein Referenzmuster daher nicht). Maschinendaten sind "
                  "optional, z.&nbsp;B. für Hinweise des Kunden."],
                 "Ein Referenzmuster ist ein Benchmark, kein Versuch: Es verbraucht keine Versuchsnummer, steht ganz "
                 "links als <b>Ref</b> mit gelbem Hintergrund (der Name steht im Tooltip), erscheint in den "
                 "Report-Diagrammen als horizontale Linie und wird aus Statistiken, Smart Chart, Quick Scan, Athena "
                 "und dem Jet-Datenexport herausgehalten. Per Rechtsklick auf die Versuchsnummer lässt sich ein "
                 "bestehender Versuch zum Referenzmuster machen (er behält seine Nummer) und zurück, oder das "
                 "Referenzmuster umbenennen."),
                ("task", "Plies oder Garne eines Versuchs ändern",
                 ["Rechtsklick auf die Ply-Zeile (5) dieses Versuchs → der Dialog <i>Manage plies</i> öffnet sich."]),
                ("task", "Eine weitere Versuchsserie oder Labormaschinen hinzufügen",
                 [M("Add Trial Series") + " oder " + M("Add Lab Machines") + " in der Sidebar benutzen."],
                 "Ein Labor-Tab (z.&nbsp;B. Statimat M) erscheint, sobald der Serie eine Labormaschine zugewiesen ist."),
                ("h", "Laborresultate und Nachmessungen"),
                ("task", "Einen Laborwert zum Nachmessen markieren (Superuser)",
                 ["Den Labor-Tab öffnen, Rechtsklick auf den Spaltenkopf des Versuchs → " + M("Flag Vn for retest…") + ".",
                  "Bei Bedarf eine Notiz eingeben (optional) und bestätigen."],
                 "Die Serie kommt mit höchster Priorität zurück in den Backlog und zeigt dort <b>RETEST</b>."),
                ("h", "Dateien, Reports und Etiketten"),
                ("task", "Bilder oder PDFs anhängen",
                 [f"Auf {B('Upload images')} oder {B('Upload PDFs')} klicken und die Dateien wählen.",
                  "Sobald etwas angehängt ist, erscheinen neben diesen Buttons ein Bild- und ein PDF-Symbol. Ein Klick darauf zeigt die Dateien."]),
                ("task", "Einen Report zu dieser Serie öffnen",
                 ["Das Report-Symbol (Diagramm) in der Werkzeugleiste (1) öffnet einen neuen Report mit Diagrammen für diese Serie.",
                  f"Gibt es gespeicherte Reports, erscheinen daneben eine Liste und {B('Go!')}: Report wählen und auf Go! klicken."],
                 "Details stehen in der Hilfe im Report-Bildschirm."),
                ("task", "Etiketten mit den Versuchsnummern drucken",
                 ["In (2) auf das Etiketten-Symbol klicken, die Startposition auf dem Bogen wählen, das PDF speichern und drucken."]),
                ("task", "Den verknüpften Experiment Request ansehen",
                 ["In (2) auf das <b>ER</b>-Symbol klicken. Es erscheint, wenn ein Request verknüpft ist."]),
                ("task", "Den Bildschirm neu laden",
                 [f"Auf {B('↻')} klicken oder F5 drücken. Der offene Tab bleibt ausgewählt."]),
            ]},
            {"key": "screen", "title": "Bildschirm", "blocks": [
                ("svg", SVG, {"lab_hint": "(Labor-Tabs erscheinen nur bei Bedarf)",
                              "keys_hint": "Enter nächste Zelle unten · Strg+C / Strg+V kopieren und einfügen · Entf leert die markierten Zellen · Strg+Z rückgängig, Strg+Y wiederherstellen · Strg+S speichern · F5 neu laden"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Werkzeugleiste", "Experiment-ID und Serie, Anhänge (Bilder/PDFs hochladen und ansehen), Statimat- "
                                           "und Itemat-Import, Report-Symbol und gespeicherte Reports (Liste + Go!), neu laden (↻), Save und diese Hilfe."),
                    ("(2) Materialzeile", "Material der Serie, verknüpfter Experiment Request (ER), Maschineninfo, "
                                          "Versuchsetiketten, <b>+T</b> (Versuche hinzufügen), <b>+ Ref</b> "
                                          "(Referenzmuster hinzufügen) und <b>Copy trials</b>."),
                    ("(3) Tabs", "Ein Tab pro Datenart, siehe Tab <i>Tabs</i>. Labor-Tabs erscheinen nur, wenn die Serie "
                                 "diese Labormaschine verwendet."),
                    ("(4) Versuchszeile", "Versuchsnummern (V1, V2, …); Referenzmuster stehen zuerst als "
                                          "<b>Ref</b> (gelb). Rechtsklick: Versuche kopieren, Referenzmuster."),
                    ("(5) Ply-Zeile", "Ply jeder Spalte (ein Versuch kann mehrere Plies haben). Rechtsklick: Plies verwalten."),
                    ("(6) Parameternamen", "Eine Zeile pro Parameter. Rechtsklick: Zeile füllen, Custom Group ein-/ausblenden."),
                    ("(7) Zellen", "Werte pro Versuch. Bearbeitbar, wo ein Wert gespeichert werden kann; geänderte Zellen "
                                   "warten auf Save."),
                ]),
            ]},
            {"key": "tabs", "title": "Tabs", "blocks": [
                ("areas", [
                    ("Machine Data", "Maschineneinstellungen pro Versuch (Geschwindigkeit, Overfeed, Luftdruck, Düse, …). "
                                     "Zeilen sind Parameter, Spalten sind Versuche und Plies. Bei DTY-Maschinen wird die Zeile "
                                     "<i>D/Y Ratio (T2/T1)</i> unter T2 Tension automatisch aus T1 und T2 berechnet und ist "
                                     "nicht editierbar."),
                    ("R&amp;D Machine Data", "Zusätzliche Entwicklungsparameter, Bedienung wie Machine Data."),
                    ("Labor-Tabs", f"{LAB_TABS}. Resultate der Laborgeräte pro Versuch; jeder erscheint nur, wenn die "
                                   "Serie dieses Gerät verwendet. Rechtsklick auf einen Spaltenkopf markiert eine Nachmessung."),
                    ("YarnScope / YarnScope ATY", "Auswertung der Garn-Messdateien mit eigenen Unter-Tabs "
                                                  "(z.&nbsp;B. Signal, Garnspiegel, Prozessvergleich)."),
                    ("Athena", "KI-Assistent, der die Serie analysiert und nächste Schritte vorschlägt. Die letzte "
                               "Analyse bleibt erhalten; eine neue Analyse dauert einen Moment."),
                    ("Notes", "Freitext-Notizen zur Serie."),
                ]),
                ("note", "<b>Tipp:</b> Mit Strg+Klick auf eine Serie im Backlog oder in All Experiments öffnet sie "
                         "sich in einem zusätzlichen Tab, z.&nbsp;B. um zwei Serien zu vergleichen."),
            ]},
        ],
    },

    # ═══════════════════════════════ ES ═══════════════════════════════
    "es": {
        "window_title": "¿Cómo funciona Show Experiment?",
        "close": "Cerrar",
        "tabs": [
            {"key": "tasks", "title": "¿Cómo hago…?", "blocks": [
                ("p", "Show Experiment muestra una serie de ensayos: todos los ensayos uno al lado del otro, con los "
                      "ajustes de máquina y los resultados de laboratorio. Los números (1)–(7) se refieren a la "
                      "pestaña <i>Pantalla</i>."),
                ("task", "Abrir una serie usada hace poco",
                 ["En la barra lateral, haz clic en <b>Recent</b> (abajo, encima de Account).",
                  "Haz clic en la serie. Ctrl+clic la abre en una pestaña nueva."],
                 "Las últimas 8 series que abriste, la más reciente primero, en cualquier PC donde inicies sesión."),
                ("h", "Introducir datos"),
                ("task", "Introducir o cambiar un valor",
                 ["Haz clic en la celda (7) y escribe el valor, o haz doble clic para editarlo. Pulsa Enter: pasas a la celda de abajo para el siguiente valor (Mayús+Enter sube).",
                  f"Haz clic en {B('Save')} o pulsa Ctrl+S."],
                 "Las celdas cambiadas quedan en <b>amarillo</b> hasta que guardas; el botón muestra cuántas, p.&nbsp;ej. "
                 f"{B('Save (3)')}, y la pestaña recibe un punto (●). Si sales de la pantalla o cierras la pestaña o el "
                 "programa con cambios sin guardar, TrippleT pregunta si quieres guardarlos. "
                 "Con nivel de acceso 1 la pantalla es de solo lectura."),
                ("task", "Poner el mismo valor en muchos ensayos",
                 ["En <i>Machine Data</i> o <i>R&amp;D Machine Data</i>, clic derecho en el nombre del parámetro en la "
                  "primera columna (6) → " + M("Fill row") + ".",
                  "Elige el valor y el rango de ensayos y haz clic en OK.",
                  f"Haz clic en {B('Save')}."],
                 "El clic derecho en una celda combinada también ofrece " + M("Fill row…") + "."),
                ("task", "Ver quién cambió un valor y cuándo",
                 ["Clic derecho en el valor → " + M("Change history…") + ".",
                  "La lista muestra cada cambio con fecha, persona, valor anterior y nuevo, el más reciente arriba. "
                  "Con <i>Show all changes in this trial series</i> se ve toda la serie."],
                 "Solo superusuarios. Se registran los cambios guardados en Show Experiment y las importaciones "
                 "de PDF de Statimat/Itemat, desde octubre de 2026."),
                ("task", "Aviso \"Unusual values\" al guardar",
                 ["TrippleT compara los ajustes de máquina cambiados con todos los ensayos anteriores de la misma "
                  "máquina. Un valor muy fuera de lo habitual (p.&nbsp;ej. 35 en vez de 3.5 bar) aparece en la lista.",
                  f"{B('Go back and check')} salta al primer valor así; {B('Save anyway')} guarda igualmente."],
                 "Solo es un aviso: se permiten valores inusuales. Los valores de laboratorio no se comprueban "
                 "(dependen del hilo)."),
                ("task", "Copiar y pegar valores",
                 ["Selecciona celdas y pulsa Ctrl+C, luego elige la celda de destino y pulsa Ctrl+V.",
                  f"Haz clic en {B('Save')}."],
                 "Funciona entre tablas y con Excel."),
                ("task", "Agrandar el texto y hacer las tablas más fáciles de leer",
                 [f"En la barra lateral, en <i>Account</i>, haz clic en {B('Settings')}.",
                  "En <i>Text size</i> elige Normal, Large, Extra large o Huge - para todo el programa (se aplica "
                  "tras reiniciar; TrippleT ofrece reiniciar enseguida). "
                  "En <i>Show Experiment tables</i> activa, si hace falta, <i>High contrast</i> y <i>Crosshair</i> (resalta la fila y la columna de la "
                  "celda seleccionada, para ver a qué ensayo y parámetro pertenece un valor).",
                  "<i>Reading bar</i> muestra el valor seleccionado en letra grande debajo de la tabla, p.&nbsp;ej. "
                  "\"V2 · Ply 1 · Air Pressure (bar) = 3.50\". <i>Mark warnings with a symbol</i> añade un círculo "
                  "(fuera de tolerancia) o un triángulo (revisar) a los valores marcados. <i>Colour-blind friendly "
                  "colours</i> evita el rojo/verde.",
                  "Revisa la vista previa y haz clic en " + B("Save") + "."],
                 "Zoom rápido en una tabla: Ctrl + rueda del ratón o Ctrl +/-, Ctrl+0 vuelve al tamaño normal. Los "
                 "ajustes se guardan para tu usuario y valen en cualquier PC. El mensaje de bienvenida y el color de "
                 "acento también se ajustan en Settings."),
                ("task", "Ocultar filas que no necesitas (Machine Data)",
                 ["Clic derecho en el nombre del parámetro en la primera columna (6) → " + M("Hide row") + ". "
                  "Para ocultar varias filas a la vez, selecciona primero sus nombres (Ctrl+clic) y haz clic "
                  "derecho en uno de ellos.",
                  "Donde hay filas ocultas aparece una línea azul en el nombre del parámetro. Pasa el ratón por "
                  "encima para ver qué filas faltan ahí; un clic sobre ella las vuelve a mostrar.",
                  f"Para mostrar todas las filas otra vez: en la barra encima de la tabla, {B('n rows hidden')} → "
                  + M("Show all rows") + ". Ahí también puedes mostrar filas sueltas."],
                 "Las filas ocultas se recuerdan por usuario y máquina, es decir, para todas las series de esta "
                 "máquina. Solo cambia la vista: los valores siguen guardados. Copiar y pegar se saltan las filas "
                 "ocultas. Una línea roja indica que una fila oculta contiene un valor marcado."),
                ("task", "Importar un informe de Statimat o Itemat",
                 [f"Haz clic en {B('Statimat import')} o {B('Itemat import')} en la barra de herramientas (1).",
                  "Elige el informe en PDF. Los valores se introducen en la pestaña de laboratorio correspondiente.",
                  f"Revisa los valores y haz clic en {B('Save')}."]),
                ("h", "Ensayos y plies"),
                ("task", "Añadir ensayos nuevos",
                 ["Haz clic en el icono <b>+</b> (añadir ensayo) a la derecha de (2). Create Experiment se abre en el modo para añadir ensayos a esta serie."]),
                ("task", "Copiar ensayos existentes",
                 [f"Haz clic en {B('Copy trials')} a la derecha de (2), o clic derecho en un número de ensayo (4) → "
                  + M("Copy trials…") + ".",
                  "Marca los ensayos que quieres copiar (Shift+clic marca un rango entero). Los ensayos cuyas "
                  "columnas seleccionaste en la tabla ya están marcados.",
                  "Elige cuántas veces y el orden: <i>Repeat the block</i> (V1 V2 | V1 V2) o <i>Each trial in "
                  "a row</i> (V1 V1 | V2 V2).",
                  "Revisa la tabla de resultado: si hace falta, cambia ahí los valores de las copias (p.&nbsp;ej. "
                  "otra presión de aire u otro jet; en ATY también OF Core / OF Effect). Las celdas cambiadas se "
                  "resaltan. <i>Show all fields</i> muestra los demás ajustes de máquina.",
                  f"Haz clic en {B('Copy n trials')}."],
                 "Se copian los ajustes de máquina y los plies. Los valores de laboratorio, los comentarios y las "
                 "tensiones del hilo antes/después del jet de las copias quedan vacíos. Los ensayos nuevos se añaden al final y "
                 "se resaltan en la tabla. Los valores por ply (p.&nbsp;ej. tensión T1/T2) se cambian después en la "
                 "tabla o en <i>Manage plies</i>. Las muestras de referencia nunca se copian."),
                ("task", "Añadir una muestra de referencia (p.&nbsp;ej. la bobina original de un cliente)",
                 [f"Haz clic en {B('+ Ref')} a la derecha de (2), o clic derecho en un número de ensayo (4) → "
                  + M("Add reference sample…") + ".",
                  "Introduce un nombre (p.&nbsp;ej. cliente, artículo, lote) y confirma.",
                  "Introduce a mano sus valores de laboratorio en las pestañas de laboratorio (las importaciones "
                  "de PDF de Statimat/Itemat solo asignan por número de ensayo y no rellenan una muestra de "
                  "referencia). Los datos de máquina son opcionales, p.&nbsp;ej. para indicaciones del cliente."],
                 "Una muestra de referencia es un benchmark, no un ensayo: no gasta ningún número de ensayo, aparece "
                 "primero como <b>Ref</b> con fondo ámbar (el nombre está en el tooltip), se dibuja como línea "
                 "horizontal en los gráficos del informe y queda fuera de las estadísticas, Smart Chart, Quick Scan, "
                 "Athena y la exportación de datos de jets. Con clic derecho en el número de un ensayo existente se "
                 "puede convertir en muestra de referencia (conserva su número) y al revés, o cambiarle el nombre."),
                ("task", "Cambiar los plies o hilos de un ensayo",
                 ["Clic derecho en la fila de ply (5) de ese ensayo → se abre el diálogo <i>Manage plies</i>."]),
                ("task", "Añadir otra serie de ensayos o máquinas de laboratorio",
                 ["Usa " + M("Add Trial Series") + " o " + M("Add Lab Machines") + " en la barra lateral."],
                 "Una pestaña de laboratorio (p.&nbsp;ej. Statimat M) aparece en cuanto se asigna una máquina de "
                 "laboratorio a la serie."),
                ("h", "Resultados de laboratorio y repeticiones"),
                ("task", "Marcar un valor de laboratorio para repetir (superusuarios)",
                 ["Abre la pestaña de laboratorio, clic derecho en el encabezado de columna del ensayo → "
                  + M("Flag Vn for retest…") + ".",
                  "Escribe una nota si quieres (opcional) y confirma."],
                 "La serie vuelve al Backlog con máxima prioridad y allí muestra <b>RETEST</b>."),
                ("h", "Archivos, informes y etiquetas"),
                ("task", "Adjuntar imágenes o PDF",
                 [f"Haz clic en {B('Upload images')} o {B('Upload PDFs')} y elige los archivos.",
                  "En cuanto hay algo adjunto, aparecen un icono de imagen y uno de PDF junto a estos botones. Al hacer clic se ven los archivos."]),
                ("task", "Abrir un informe de esta serie",
                 ["El icono de informe (gráfico) en la barra de herramientas (1) abre un informe nuevo con gráficos para esta serie.",
                  f"Si hay informes guardados, aparecen al lado una lista y {B('Go!')}: elige el informe y haz clic en Go!."],
                 "Los detalles están en la ayuda de la pantalla Report."),
                ("task", "Imprimir etiquetas con los números de ensayo",
                 ["Haz clic en el icono de etiqueta en (2), elige la posición inicial en la hoja, guarda el PDF e imprímelo."]),
                ("task", "Ver la solicitud de experimento vinculada",
                 ["Haz clic en el icono <b>ER</b> en (2). Aparece cuando hay una solicitud vinculada."]),
                ("task", "Recargar la pantalla",
                 [f"Haz clic en {B('↻')} o pulsa F5. La pestaña abierta sigue seleccionada."]),
            ]},
            {"key": "screen", "title": "Pantalla", "blocks": [
                ("svg", SVG, {"lab_hint": "(las pestañas de laboratorio solo aparecen si se usan)",
                              "keys_hint": "Enter celda de abajo · Ctrl+C / Ctrl+V copiar y pegar · Supr vacía las celdas seleccionadas · Ctrl+Z deshacer, Ctrl+Y rehacer · Ctrl+S guardar · F5 recargar"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Barra de herramientas", "ID del experimento y serie, adjuntos (subir y ver imágenes/PDF), "
                                                  "importación de Statimat e Itemat, icono de informe e informes guardados (lista + Go!), "
                                                  "recargar (↻), Save y esta ayuda."),
                    ("(2) Línea de material", "Material de la serie, solicitud de experimento vinculada (ER), datos de "
                                              "la máquina, etiquetas de ensayos, <b>+T</b> (añadir ensayos), "
                                              "<b>+ Ref</b> (añadir muestra de referencia) y <b>Copy trials</b>."),
                    ("(3) Pestañas", "Una pestaña por tipo de datos, ver la pestaña <i>Pestañas</i>. Las pestañas de "
                                     "laboratorio solo aparecen si la serie usa esa máquina."),
                    ("(4) Fila de ensayos", "Números de ensayo (V1, V2, …); las muestras de referencia van primero "
                                            "como <b>Ref</b> (ámbar). Clic derecho: copiar ensayos, muestras de referencia."),
                    ("(5) Fila de ply", "Ply de cada columna (un ensayo puede tener varios plies). Clic derecho: gestionar plies."),
                    ("(6) Nombres de parámetros", "Una fila por parámetro. Clic derecho: rellenar fila, mostrar/ocultar el custom group."),
                    ("(7) Celdas", "Valores por ensayo. Editables donde se puede guardar un valor; las celdas cambiadas "
                                   "esperan a Save."),
                ]),
            ]},
            {"key": "tabs", "title": "Pestañas", "blocks": [
                ("areas", [
                    ("Machine Data", "Ajustes de máquina por ensayo (velocidad, sobrealimentación, presión de aire, "
                                     "tobera, …). Las filas son parámetros, las columnas ensayos y plies. En máquinas DTY, la "
                                     "fila <i>D/Y Ratio (T2/T1)</i> debajo de T2 Tension se calcula automáticamente a partir "
                                     "de T1 y T2 y no se puede editar."),
                    ("R&amp;D Machine Data", "Parámetros de desarrollo adicionales, se usa igual que Machine Data."),
                    ("Pestañas de laboratorio", f"{LAB_TABS}. Resultados de los equipos de laboratorio por ensayo; "
                                                "cada una aparece solo si la serie usa ese equipo. Clic derecho en un "
                                                "encabezado de columna marca una repetición."),
                    ("YarnScope / YarnScope ATY", "Análisis de los archivos de medición del hilo con sus propias "
                                                  "subpestañas (p.&nbsp;ej. señal, perfil del hilo, comparación de procesos)."),
                    ("Athena", "Asistente de IA que analiza la serie y propone próximos pasos. El último análisis se "
                               "conserva; un análisis nuevo tarda un momento."),
                    ("Notes", "Notas de texto libre de la serie."),
                ]),
                ("note", "<b>Consejo:</b> Con Ctrl+clic en una serie del Backlog o de All Experiments se abre en una "
                         "pestaña adicional, p.&nbsp;ej. para comparar dos series."),
            ]},
        ],
    },
}
