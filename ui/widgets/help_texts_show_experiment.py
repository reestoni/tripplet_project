# ui/widgets/help_texts_show_experiment.py
"""Hilfetexte Show Experiment (EN/DE/ES/ZH) fuer ui/widgets/multilang_help.py.

Spiegelt ui/screen_show_experiment.py (Werkzeugleiste in _build_ui, Kontext-
menues: _MachineContextMenuFilter -> Copy trials / Reference samples /
Yarns… (Plies der Serie) / Fill row / Custom Group, Retest-Flag ueber den Spaltenkopf der Labor-Tabs, Shortcuts
Ctrl+S/F5/Ctrl+C/Ctrl+V, Read-only ab Level <= 1) und ui/machine_tab.py.
Bei Aenderungen dort hier (alle 4 Sprachen) und in
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
                 "Changed cells stay <b>yellow</b> until you save; a green tick in the middle confirms the save. The button shows how many, e.g. "
                 f"{B('Save (3)')}, and the tab gets a dot (●). If you leave the screen, close the tab or the "
                 "program with unsaved changes, TrippleT asks whether to save them. "
                 "With access level 1 the screen is read-only."),
                ("task", "Set the same value for many trials",
                 ["In <i>Machine Data</i> or <i>R&amp;D Machine Data</i>, right-click the parameter name in the "
                  "first column (6) → " + M("Fill row") + ".",
                  "Choose the value and the range of trials, then OK.",
                  f"Click {B('Save')}."],
                 "Right-clicking a merged cell offers " + M("Fill row…") + " as well."),
                ("task", "Find out what a row means (Knowledge Base)",
                 ["Right-click the row title or a value in <i>Machine Data</i> / <i>R&D Machine Data</i> (DTY machines) "
                  "or in a lab tab → " + M("Learn more in Knowledge Base…") + ". In the DTY <b>Schema</b>: click a station, "
                  "then the link below the schema (or right-click the station).",
                  "The matching page opens in a window at the right place, e.g. the machine with the station selected.",
                  "Click " + B("Close") + " or press Esc - you are back in your series."],
                 "Use the tabs at the top of the window to see the other scenes of the page, the flags change the language."),
                ("task", "Add a note to a value or a trial",
                 ["Right-click the value → " + M("Add note…") + ". For the whole trial, right-click the trial "
                  "number (V1, V2, …) in <i>Machine Data</i>.",
                  "Write the note and click " + B("Add note") + " (or Ctrl+Enter) - it is saved right away."],
                 "A small purple triangle in the corner marks a value with notes; point at it to read them. "
                 "The <i>Notes</i> tab lists all notes of the series - double-click a line to jump to the value. "
                 "Everybody can write notes; only the author can edit one, the author or a superuser can delete "
                 "it. In the Smart Chart, the <b>Notes</b> button shows them; the PDF only gets them if you tick "
                 "<i>Include notes on values</i> when exporting."),
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
                ("task", "Choose the DTY process and see the machine path",
                 ["In <i>Machine Data</i> (DTY machines only), set the row <b>DTY Process</b> per trial: Standard, "
                  "Elastane or a cotton-like variant. Click " + B("Save") + " (Ctrl+S).",
                  "Click " + B("Schema") + " in the toolbar above the table to show or hide the machine path. It "
                  "shows the trial of the cell you clicked: every ply on its position, where they run together, "
                  "elastane from its own source.",
                  "Click a station (e.g. the heater): its rows light up in the table. Click it again or an empty "
                  "spot to clear it. A double-click jumps to the first value of the station."],
                 "Rows of the pre-intermingling jet (LW 0 - LW 1) and of jet 3 (before LW 3) only show up when "
                 "a trial's process needs them or a value is entered. The schema only shows values - change them "
                 "in the table. With 2 or more plies, the rows <b>Route</b>, <b>Merge into ply</b> and <b>Merge "
                 "point</b> decide how the plies run together (e.g. Ply 4 into Ply 3 at LW 1); empty = the usual "
                 "path. Wrong entries (unknown ply, a circle) are named below the schema. On ATY machines the schema shows the air-texturing path: core and effect with draw zone and feed roll (speed = LW 2 x (1 + OF %)); only the core is wetted, the effect joins it just before the jet; then LW 2, stabilising zone, LW 3 and winder."),
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
                 "table. Values per ply (e.g. T1/T2 tension) are changed afterwards in the table, plies and "
                 "yarns with " + B("Yarns…") + ". Reference samples are never copied."),
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
                ("task", "Find the trials that meet your targets (or beat the reference sample)",
                 [f"Click {B('vs Ref / Target')} on the right of (2), or right-click the Ref column (4) → "
                  + M("Compare trials with this reference…") + ".",
                  "Under <i>Compare with</i> choose a reference sample of the series or <i>Own targets</i>. To use "
                  "your own target value, double-click the first row of a column and type it in (it is used instead "
                  "of the reference value; delete it to go back).",
                  "Click the header of a value you care about and choose " + M("Higher is better") + ", "
                  + M("Lower is better") + " or " + M("Close to Ref is better") + " (" + M("Tolerance…")
                  + " allows a margin). Repeat for every value that matters.",
                  "Green = meets the criterion, red = not. <b>Result</b> counts them per trial, the best trials "
                  "are on top. Tick <i>Only trials that meet all criteria</i> to see only the winners.",
                  f"To use criteria and targets again: {B('Save as…')} with a name (e.g. customer and article). "
                  "Later choose it under <i>Criteria</i> - in any series."],
                 "All lab tabs are compared at once. A missing value counts as not met; a criterion without a "
                 "target (and without a reference value) does not count. Criteria sets are shared by all users; "
                 "deleting: whoever made it or a superuser. Double-click a trial to see it in Machine Data. Nothing "
                 "in the series is changed."),
                ("task", "Delete trials",
                 ["One trial: right-click its trial number (4) → " + M("Delete V23…") + ".",
                  "Several trials: first select cells in their columns (drag, Ctrl+click or Shift+click), then "
                  "right-click the number of one of them → " + M("Delete n selected trials…") + ".",
                  "Check what is deleted with them (plies, lab values, notes) and click " + B("Delete") + "."],
                 "The other trials keep their numbers - nothing moves up. New trials are always added after the "
                 "highest remaining number, never into a gap. A superuser can restore deleted trials from the Recycle Bin for 90 "
                 "days. Allowed for whoever may move the series in the Backlog. Trials that yarns were made from "
                 "(half-finished products) can't be deleted."),
                ("task", "Change the yarn of a ply, or add / remove plies",
                 [f"Click {B('Yarns…')} on the right of (2) (or right-click the ply row (5)). A table shows every "
                  "ply of the series (rows) and every trial (columns).",
                  "<b>Change a yarn:</b> click the yarn of the ply, type a part of the name (e.g. <i>167 dty</i>) "
                  "and pick it - the whole ply gets the new yarn.",
                  "<b>Ply on/off for one trial:</b> click its cell. Number of ends: select cells and type 1–9 "
                  "(Delete = off), or right-click.",
                  f"<b>New ply:</b> {B('+ Add ply')} (catalog yarn) or {B('+ Trial output')} (output of another "
                  "trial) - it is on for every trial. A yarn always keeps its ply number in a series: added again (e.g. "
                  "once as <i>DTY</i>, once as <i>Effect</i>) it becomes a second row of the same ply - choose the "
                  "use in the <i>Use</i> column.",
                  f"Click {B('Apply')} - TrippleT shows a summary first."],
                 "Changed cells are yellow; nothing is saved before Apply (Cancel discards everything). A changed "
                 "yarn keeps the machine values of the ply; removing a ply deletes its values in that trial. Every "
                 "trial keeps at least one ply - reference samples may have no yarn at all. Needs write access."),
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
                                          "<b>Copy trials</b>. Behind every ply a small spool: green = yarn in stock "
                                          "(click the yarn or the spool to see the storage locations and tube colours), crossed-out tube "
                                          "= nothing in stock."),
                    ("(3) Tabs", "One tab per kind of data, see the <i>Tabs</i> tab. Lab tabs only appear if the "
                                 "series uses that lab machine."),
                    ("(4) Trial row", "Trial numbers (V1, V2, …); reference samples come first as <b>Ref</b> "
                                      "(amber). Right-click: copy trials, reference samples."),
                    ("(5) Ply row", "Ply of each column (a trial can have several plies). Right-click: Yarns of the series."),
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
                 "Geänderte Zellen bleiben <b>gelb</b>, bis gespeichert ist; ein grünes Häkchen in der Mitte bestätigt das Speichern. Der Knopf zeigt die Anzahl, z.&nbsp;B. "
                 f"{B('Save (3)')}, und der Tab bekommt einen Punkt (●). Verlässt du den Bildschirm oder schliesst "
                 "den Tab oder das Programm mit ungespeicherten Änderungen, fragt TrippleT, ob gespeichert werden soll. "
                 "Mit Access Level 1 ist der Bildschirm nur lesbar."),
                ("task", "Denselben Wert für viele Versuche setzen",
                 ["In <i>Machine Data</i> oder <i>R&amp;D Machine Data</i> mit Rechtsklick auf den Parameternamen in der "
                  "ersten Spalte (6) → " + M("Fill row") + ".",
                  "Wert und Versuchsbereich wählen, dann OK.",
                  f"Auf {B('Save')} klicken."],
                 "Ein Rechtsklick auf eine zusammengefasste Zelle bietet ebenfalls " + M("Fill row…") + " an."),
                ("task", "Nachschlagen, was eine Zeile bedeutet (Knowledge Base)",
                 ["Rechtsklick auf den Zeilentitel oder einen Wert in <i>Machine Data</i> / <i>R&D Machine Data</i> "
                  "(DTY-Maschinen) oder in einem Labor-Reiter → " + M("Learn more in Knowledge Base…") + ". Im DTY-<b>Schema</b>: Station "
                  "anklicken, dann den Link unter dem Schema (oder Rechtsklick auf die Station).",
                  "Die passende Seite öffnet sich in einem Fenster an der richtigen Stelle, z. B. die Maschine mit gewählter Station.",
                  B("Close") + " klicken oder Esc drücken - du bist wieder in deiner Serie."],
                 "Oben im Fenster zeigen die Reiter die anderen Szenen der Seite, die Flaggen wechseln die Sprache."),
                ("task", "Eine Notiz an einen Wert oder Versuch hängen",
                 ["Rechtsklick auf den Wert → " + M("Add note…") + ". Für den ganzen Versuch: Rechtsklick auf die "
                  "Versuchsnummer (V1, V2, …) in <i>Machine Data</i>.",
                  "Notiz schreiben und " + B("Add note") + " klicken (oder Strg+Enter) - sie ist sofort gespeichert."],
                 "Ein kleines violettes Dreieck in der Ecke zeigt einen Wert mit Notizen; mit der Maus darauf "
                 "zeigen, um sie zu lesen. Der Tab <i>Notes</i> listet alle Notizen der Serie - Doppelklick auf "
                 "eine Zeile springt zum Wert. Notizen schreiben darf jeder; ändern nur, wer sie geschrieben hat, "
                 "löschen der Verfasser oder ein Superuser. Im Smart Chart zeigt der Knopf <b>Notes</b> sie an; ins "
                 "PDF kommen sie nur mit dem Häkchen <i>Include notes on values</i> beim Export."),
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
                ("task", "DTY-Verfahren wählen und den Maschinenweg sehen",
                 ["In <i>Machine Data</i> (nur DTY-Maschinen) pro Versuch die Zeile <b>DTY Process</b> setzen: "
                  "Standard, Elastane oder eine Cotton-like-Variante. " + B("Save") + " klicken (Strg+S).",
                  B("Schema") + " in der Leiste über der Tabelle blendet den Maschinenweg ein und aus. Er zeigt den "
                  "Versuch der angeklickten Zelle: jede Ply auf ihrer Position, wo sie zusammenlaufen, Elastan aus "
                  "der eigenen Quelle.",
                  "Eine Station anklicken (z.&nbsp;B. den Heizer): ihre Zeilen leuchten in der Tabelle auf. Nochmals "
                  "klicken oder auf eine leere Stelle klicken hebt es auf. Doppelklick springt zum ersten Wert der Station."],
                 "Die Zeilen der Vorverwirbelung (LW 0 - LW 1) und der 3. Düse (vor LW 3) erscheinen nur, wenn das "
                 "Verfahren eines Versuchs sie braucht oder ein Wert eingetragen ist. Das Schema zeigt Werte nur an - "
                 "geändert werden sie in der Tabelle. Ab 2 Plies legen die Zeilen <b>Route</b>, <b>Merge into ply</b> "
                 "und <b>Merge point</b> fest, wie die Plies zusammenlaufen (z.&nbsp;B. Ply 4 in Ply 3 an LW 1); leer = "
                 "der übliche Weg. Fehler (unbekannte Ply, ein Kreis) stehen unter dem Schema. Auf ATY-Maschinen zeigt das Schema den Weg durch die Lufttexturiermaschine: Kern und Effekt mit Verstreckzone und Lieferwerk (Geschwindigkeit = LW 2 x (1 + OF %)); nur der Kern wird benetzt, der Effekt kommt erst vor der Düse dazu; dann LW 2, Stabilisierzone, LW 3 und Aufwicklung."),
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
                 "markiert. Werte pro Ply (z.&nbsp;B. T1/T2-Spannung) werden danach in der Tabelle geändert, "
                 "Plies und Garne mit " + B("Yarns…") + ". Referenzmuster werden nie mitkopiert."),
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
                ("task", "Die Versuche finden, die deine Ziele erreichen (oder das Referenzmuster schlagen)",
                 [f"{B('vs Ref / Target')} rechts von (2) klicken, oder Rechtsklick auf die Ref-Spalte (4) → "
                  + M("Compare trials with this reference…") + ".",
                  "Unter <i>Compare with</i> ein Referenzmuster der Serie oder <i>Own targets</i> wählen. Für einen "
                  "eigenen Zielwert in die erste Zeile einer Spalte doppelklicken und ihn eintippen (er gilt statt "
                  "des Referenzwerts; Wert löschen = wieder Referenz).",
                  "Auf den Kopf eines wichtigen Werts klicken und " + M("Higher is better") + ", "
                  + M("Lower is better") + " oder " + M("Close to Ref is better") + " wählen (" + M("Tolerance…")
                  + " erlaubt einen Spielraum). Für jeden wichtigen Wert wiederholen.",
                  "Grün = erfüllt, rot = nicht. <b>Result</b> zählt pro Versuch, die besten stehen oben. "
                  "<i>Only trials that meet all criteria</i> zeigt nur noch die Gewinner.",
                  f"Kriterien und Zielwerte wiederverwenden: {B('Save as…')} mit einem Namen (z.&nbsp;B. Kunde und "
                  "Artikel). Später unter <i>Criteria</i> auswählen - in jeder Serie."],
                 "Alle Labor-Reiter werden zusammen verglichen. Ein fehlender Wert zählt als nicht erfüllt; ein "
                 "Kriterium ohne Zielwert (und ohne Referenzwert) zählt nicht. Kriterien-Sets gelten für alle "
                 "Benutzer; löschen darf, wer es angelegt hat, oder ein Superuser. Doppelklick auf einen Versuch zeigt "
                 "ihn in Machine Data. An der Serie wird nichts geändert."),
                ("task", "Versuche löschen",
                 ["Ein Versuch: Rechtsklick auf seine Versuchsnummer (4) → " + M("Delete V23…") + ".",
                  "Mehrere Versuche: zuerst Zellen in ihren Spalten markieren (ziehen, Strg+Klick oder "
                  "Umschalt+Klick), dann Rechtsklick auf die Nummer eines davon → " + M("Delete n selected trials…") + ".",
                  "Prüfen, was mitgelöscht wird (Plies, Laborwerte, Notizen), und " + B("Delete") + " klicken."],
                 "Die übrigen Versuche behalten ihre Nummern - nichts rutscht nach. Neue Versuche kommen immer nach "
                 "der höchsten verbliebenen Nummer, nie in eine Lücke. Ein Superuser kann gelöschte Versuche 90 "
                 "Tage lang aus dem Recycle Bin zurückholen. Erlaubt für alle, die die Serie im Backlog verschieben "
                 "dürfen. Versuche, aus denen Garne gemacht wurden (Halbfabrikate), lassen sich nicht löschen."),
                ("task", "Das Garn einer Ply ändern oder Plies hinzufügen / entfernen",
                 [f"Rechts in (2) auf {B('Yarns…')} klicken (oder Rechtsklick auf die Ply-Zeile (5)). Eine Tabelle "
                  "zeigt alle Plies der Serie (Zeilen) und alle Versuche (Spalten).",
                  "<b>Garn ändern:</b> auf das Garn der Ply klicken, einen Teil des Namens tippen (z.&nbsp;B. "
                  "<i>167 dty</i>) und auswählen - die ganze Ply bekommt das neue Garn.",
                  "<b>Ply für einen Versuch ein/aus:</b> seine Zelle anklicken. Anzahl Enden: Zellen markieren und "
                  "1–9 tippen (Entf = aus), oder Rechtsklick.",
                  f"<b>Neue Ply:</b> {B('+ Add ply')} (Garn aus dem Katalog) oder {B('+ Trial output')} (Output "
                  "eines anderen Versuchs) - sie gilt zuerst für alle Versuche. Ein Garn behält in einer Serie immer seine "
                  "Ply-Nummer: nochmals hinzugefügt (z.&nbsp;B. einmal als <i>DTY</i>, einmal als <i>Effect</i>) wird "
                  "es eine zweite Zeile derselben Ply - die Verwendung in der Spalte <i>Use</i> wählen.",
                  f"Auf {B('Apply')} klicken - TrippleT zeigt vorher eine Zusammenfassung."],
                 "Geänderte Zellen sind gelb; vor Apply wird nichts gespeichert (Cancel verwirft alles). Ein "
                 "getauschtes Garn behält die Maschinenwerte der Ply; eine entfernte Ply verliert ihre Werte in "
                 "diesem Versuch. Jeder Versuch behält mindestens eine Ply - Referenzmuster dürfen ganz ohne Garn sein. Braucht Schreibrechte."),
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
                                          "(Referenzmuster hinzufügen) und <b>Copy trials</b>. Hinter jeder Ply eine "
                                          "kleine Spule: grün = Garn am Lager (Klick aufs Garn oder die Spule zeigt Lagerplätze und "
                                          "Hülsenfarben), durchgestrichene Hülse = nichts am Lager."),
                    ("(3) Tabs", "Ein Tab pro Datenart, siehe Tab <i>Tabs</i>. Labor-Tabs erscheinen nur, wenn die Serie "
                                 "diese Labormaschine verwendet."),
                    ("(4) Versuchszeile", "Versuchsnummern (V1, V2, …); Referenzmuster stehen zuerst als "
                                          "<b>Ref</b> (gelb). Rechtsklick: Versuche kopieren, Referenzmuster."),
                    ("(5) Ply-Zeile", "Ply jeder Spalte (ein Versuch kann mehrere Plies haben). Rechtsklick: Garne der Serie (Yarns)."),
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
                 "Las celdas cambiadas quedan en <b>amarillo</b> hasta que guardas; una marca verde en el centro confirma el guardado. El botón muestra cuántas, p.&nbsp;ej. "
                 f"{B('Save (3)')}, y la pestaña recibe un punto (●). Si sales de la pantalla o cierras la pestaña o el "
                 "programa con cambios sin guardar, TrippleT pregunta si quieres guardarlos. "
                 "Con nivel de acceso 1 la pantalla es de solo lectura."),
                ("task", "Poner el mismo valor en muchos ensayos",
                 ["En <i>Machine Data</i> o <i>R&amp;D Machine Data</i>, clic derecho en el nombre del parámetro en la "
                  "primera columna (6) → " + M("Fill row") + ".",
                  "Elige el valor y el rango de ensayos y haz clic en OK.",
                  f"Haz clic en {B('Save')}."],
                 "El clic derecho en una celda combinada también ofrece " + M("Fill row…") + "."),
                ("task", "Consultar qué significa una fila (Knowledge Base)",
                 ["Clic derecho en el título de la fila o en un valor de <i>Machine Data</i> / <i>R&D Machine Data</i> "
                  "(máquinas DTY) o de una pestaña de laboratorio → " + M("Learn more in Knowledge Base…") + ". En el <b>Schema</b> DTY: "
                  "clic en una estación y luego en el enlace debajo (o clic derecho en la estación).",
                  "La página correspondiente se abre en una ventana en el lugar correcto, p. ej. la máquina con la estación seleccionada.",
                  "Haz clic en " + B("Close") + " o pulsa Esc: vuelves a tu serie."],
                 "Las pestañas arriba en la ventana muestran las otras escenas de la página, las banderas cambian el idioma."),
                ("task", "Añadir una nota a un valor o a un ensayo",
                 ["Clic derecho en el valor → " + M("Add note…") + ". Para todo el ensayo: clic derecho en el "
                  "número de ensayo (V1, V2, …) en <i>Machine Data</i>.",
                  "Escribe la nota y haz clic en " + B("Add note") + " (o Ctrl+Enter); se guarda al instante."],
                 "Un pequeño triángulo violeta en la esquina marca un valor con notas; señálalo con el ratón para "
                 "leerlas. La pestaña <i>Notes</i> lista todas las notas de la serie; doble clic en una línea "
                 "salta al valor. Todos pueden escribir notas; solo el autor puede editarlas, el autor o un "
                 "superusuario puede borrarlas. En el Smart Chart, el botón <b>Notes</b> las muestra; en el PDF solo "
                 "aparecen si marcas <i>Include notes on values</i> al exportar."),
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
                ("task", "Elegir el proceso DTY y ver el recorrido en la máquina",
                 ["En <i>Machine Data</i> (solo máquinas DTY), ajuste la fila <b>DTY Process</b> de cada ensayo: "
                  "Standard, Elastane o una variante cotton-like. Haga clic en " + B("Save") + " (Ctrl+S).",
                  B("Schema") + " en la barra encima de la tabla muestra u oculta el recorrido. Muestra el ensayo de "
                  "la celda en la que hizo clic: cada ply en su posición, dónde se juntan, el elastano desde su "
                  "propia fuente.",
                  "Haga clic en una estación (p.&nbsp;ej. el calentador): sus filas se resaltan en la tabla. Otro clic "
                  "o un clic en un sitio vacío lo quita. Un doble clic salta al primer valor de la estación."],
                 "Las filas del chorro de pre-entrelazado (LW 0 - LW 1) y del 3.er chorro (antes de LW 3) solo "
                 "aparecen si el proceso de un ensayo las necesita o hay un valor. El esquema solo muestra los "
                 "valores - se cambian en la tabla. Con 2 o más plies, las filas <b>Route</b>, <b>Merge into ply</b> "
                 "y <b>Merge point</b> deciden cómo se juntan (p.&nbsp;ej. Ply 4 en Ply 3 en LW 1); vacío = el "
                 "recorrido habitual. Los errores (ply desconocida, un círculo) aparecen debajo del esquema. En las máquinas ATY el esquema muestra el recorrido de texturizado por aire: alma y efecto con zona de estirado y rodillo de alimentación (velocidad = LW 2 x (1 + OF %)); solo se humedece el alma, el efecto se une justo antes de la tobera; después LW 2, zona de estabilización, LW 3 y bobinado."),
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
                 "tabla, los plies y los hilos con " + B("Yarns…") + ". Las muestras de referencia nunca se copian."),
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
                ("task", "Encontrar los ensayos que alcanzan tus objetivos (o superan la muestra de referencia)",
                 [f"Haz clic en {B('vs Ref / Target')} a la derecha de (2), o clic derecho en la columna Ref (4) → "
                  + M("Compare trials with this reference…") + ".",
                  "En <i>Compare with</i> elige una muestra de referencia de la serie u <i>Own targets</i>. Para un "
                  "objetivo propio, haz doble clic en la primera fila de una columna y escríbelo (se usa en lugar del "
                  "valor de referencia; bórralo para volver).",
                  "Haz clic en el encabezado de un valor importante y elige " + M("Higher is better") + ", "
                  + M("Lower is better") + " o " + M("Close to Ref is better") + " (" + M("Tolerance…")
                  + " permite un margen). Repite para cada valor importante.",
                  "Verde = cumple, rojo = no. <b>Result</b> los cuenta por ensayo, los mejores aparecen arriba. "
                  "<i>Only trials that meet all criteria</i> muestra solo a los ganadores.",
                  f"Para reutilizar criterios y objetivos: {B('Save as…')} con un nombre (p.&nbsp;ej. cliente y "
                  "artículo). Después elígelo en <i>Criteria</i> - en cualquier serie."],
                 "Se comparan todas las pestañas de laboratorio a la vez. Un valor que falta cuenta como no cumplido; "
                 "un criterio sin objetivo (y sin valor de referencia) no cuenta. Los conjuntos de criterios son para "
                 "todos los usuarios; borrar: quien lo creó o un superusuario. Doble clic en un ensayo lo muestra en "
                 "Machine Data. No se cambia nada en la serie."),
                ("task", "Borrar ensayos",
                 ["Un ensayo: clic derecho en su número de ensayo (4) → " + M("Delete V23…") + ".",
                  "Varios ensayos: primero selecciona celdas en sus columnas (arrastrando, Ctrl+clic o Mayús+clic), "
                  "luego clic derecho en el número de uno de ellos → " + M("Delete n selected trials…") + ".",
                  "Revisa lo que se borra con ellos (plies, valores de laboratorio, notas) y haz clic en "
                  + B("Delete") + "."],
                 "Los demás ensayos conservan su número - nada se desplaza. Los nuevos ensayos siempre van después "
                 "del número más alto que queda, nunca en un hueco. Un superusuario puede recuperar ensayos borrados "
                 "desde la Recycle Bin durante 90 días. Permitido a quien puede mover la serie en el Backlog. Los "
                 "ensayos de los que se hicieron hilos (semielaborados) no se pueden borrar."),
                ("task", "Cambiar el hilo de un ply, o añadir / quitar plies",
                 [f"Haz clic en {B('Yarns…')} a la derecha de (2) (o clic derecho en la fila de ply (5)). Una tabla "
                  "muestra todos los plies de la serie (filas) y todos los ensayos (columnas).",
                  "<b>Cambiar un hilo:</b> haz clic en el hilo del ply, escribe parte del nombre (p.&nbsp;ej. "
                  "<i>167 dty</i>) y elígelo: todo el ply recibe el hilo nuevo.",
                  "<b>Ply sí/no para un ensayo:</b> haz clic en su celda. Número de cabos: marca celdas y escribe "
                  "1–9 (Supr = no), o clic derecho.",
                  f"<b>Ply nuevo:</b> {B('+ Add ply')} (hilo del catálogo) o {B('+ Trial output')} (salida de otro "
                  "ensayo): vale para todos los ensayos. Un hilo conserva siempre su número de ply en una "
                  "serie: si se añade otra vez (p.&nbsp;ej. una vez como <i>DTY</i> y otra como <i>Effect</i>) es una "
                  "segunda fila del mismo ply; elige el uso en la columna <i>Use</i>.",
                  f"Haz clic en {B('Apply')}: TrippleT muestra antes un resumen."],
                 "Las celdas cambiadas están en amarillo; nada se guarda antes de Apply (Cancel lo descarta todo). Un "
                 "hilo cambiado conserva los valores de máquina del ply; quitar un ply borra sus valores en ese "
                 "ensayo. Cada ensayo conserva al menos un ply; las muestras de referencia pueden no tener hilo. Requiere permiso de escritura."),
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
                                              "<b>+ Ref</b> (añadir muestra de referencia) y <b>Copy trials</b>. "
                                              "Detrás de cada ply una pequeña bobina: verde = hilo en almacén (clic en el "
                                              "hilo o la bobina para ver ubicaciones y colores del tubo), tubo tachado = nada en "
                                              "almacén."),
                    ("(3) Pestañas", "Una pestaña por tipo de datos, ver la pestaña <i>Pestañas</i>. Las pestañas de "
                                     "laboratorio solo aparecen si la serie usa esa máquina."),
                    ("(4) Fila de ensayos", "Números de ensayo (V1, V2, …); las muestras de referencia van primero "
                                            "como <b>Ref</b> (ámbar). Clic derecho: copiar ensayos, muestras de referencia."),
                    ("(5) Fila de ply", "Ply de cada columna (un ensayo puede tener varios plies). Clic derecho: hilos de la serie (Yarns)."),
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

    # ═══════════════════════════════ ZH ═══════════════════════════════
    "zh": {
        "window_title": "Show Experiment 如何使用？",
        "close": "关闭",
        "tabs": [
            {"key": "tasks", "title": "我该如何……？", "blocks": [
                ("p", "Show Experiment 显示一个试验系列：所有试验并排显示，包括机器设置和实验室结果。"
                      "编号 (1)–(7) 对应 <i>界面说明</i> 选项卡。"),
                ("task", "打开最近使用过的系列",
                 ["在侧边栏中点击 <b>Recent</b>（底部，Account 上方）。",
                  "点击该系列。Ctrl+点击会在新选项卡中打开。"],
                 "显示您最近打开的 8 个系列，最新的在前——在您登录的每台电脑上都一样。"),
                ("h", "录入数据"),
                ("task", "录入或修改数值",
                 ["点击单元格 (7) 并输入数值，或双击进行编辑。按 Enter 后会跳到下方单元格，继续录入下一个值（Shift+Enter 向上）。",
                  f"点击 {B('Save')} 或按 Ctrl+S。"],
                 "修改过的单元格在保存前保持<b>黄色</b>；中间出现绿色对勾表示已保存。按钮会显示修改数量，例如 "
                 f"{B('Save (3)')}，选项卡上也会出现一个圆点 (●)。如果有未保存的修改时离开界面、关闭选项卡或"
                 "退出程序，TrippleT 会询问是否保存。"
                 "访问级别为 1 时，此界面为只读。"),
                ("task", "为多个试验设置相同数值",
                 ["在 <i>Machine Data</i> 或 <i>R&amp;D Machine Data</i> 中，右键点击第一列 (6) 中的参数名 → "
                  + M("Fill row") + "。",
                  "选择数值和试验范围，然后点击 OK。",
                  f"点击 {B('Save')}。"],
                 "右键点击合并单元格时也会提供 " + M("Fill row…") + "。"),
                ("task", "查看某一行的含义（知识库）",
                 ["在 <i>Machine Data</i> / <i>R&D Machine Data</i>（DTY 机器）或实验室选项卡中，右键点击行标题或数值 → "
                  + M("Learn more in Knowledge Base…") + "。在 DTY <b>Schema</b> 中：点击一个工位，"
                  "再点击示意图下方的链接（或右键点击该工位）。",
                  "相应页面会在窗口中打开并定位到正确位置，例如已选中该工位的机器。",
                  "点击 " + B("Close") + " 或按 Esc，即可返回您的系列。"],
                 "用窗口顶部的选项卡查看该页面的其他场景，旗帜图标用于切换语言。"),
                ("task", "为数值或试验添加备注",
                 ["右键点击数值 → " + M("Add note…") + "。如需为整个试验添加备注，请在 <i>Machine Data</i> 中"
                  "右键点击试验编号（V1、V2、…）。",
                  "输入备注并点击 " + B("Add note") + "（或 Ctrl+Enter），备注会立即保存。"],
                 "角落里的紫色小三角表示该数值有备注；鼠标指向即可阅读。"
                 "<i>Notes</i> 选项卡列出该系列的所有备注，双击某一行可跳转到对应数值。"
                 "所有人都可以写备注；只有作者可以编辑，作者或超级用户可以删除。"
                 "在 Smart Chart 中，<b>Notes</b> 按钮会显示备注；只有导出时勾选 "
                 "<i>Include notes on values</i>，PDF 中才会包含备注。"),
                ("task", "查看谁在何时修改了数值",
                 ["右键点击数值 → " + M("Change history…") + "。",
                  "列表显示每次修改的日期、人员、旧值和新值，最新的在前。"
                  "勾选 <i>Show all changes in this trial series</i> 可查看整个系列。"],
                 "仅限超级用户。记录的内容包括在 Show Experiment 中保存的修改以及 Statimat/Itemat PDF 导入，"
                 "自 2026 年 10 月起。"),
                ("task", "保存时出现 \"Unusual values\" 警告",
                 ["TrippleT 会将修改后的机器设置与同一机器以往的所有试验进行比较。"
                  "明显超出常规范围的数值（例如 35 而不是 3.5 bar）会被列出。",
                  f"{B('Go back and check')} 跳转到第一个此类数值；{B('Save anyway')} 按原样保存。"],
                 "这只是提示——允许存在异常值。实验室数值不做检查（它们取决于纱线）。"),
                ("task", "复制和粘贴数值",
                 ["选中单元格并按 Ctrl+C，然后选中目标单元格并按 Ctrl+V。",
                  f"点击 {B('Save')}。"],
                 "可在表格之间以及与 Excel 之间使用。"),
                ("task", "放大文字，让表格更易读",
                 [f"在侧边栏 <i>Account</i> 下点击 {B('Settings')}。",
                  "在 <i>Text size</i> 中选择 Normal、Large、Extra large 或 Huge——适用于整个程序"
                  "（重启后生效；TrippleT 会提示立即重启）。"
                  "如有需要，在 <i>Show Experiment tables</i> 中打开 <i>High contrast</i> 和 <i>Crosshair</i>（高亮所选单元格的行和列，"
                  "便于看清某个数值属于哪个试验和参数）。",
                  "<i>Reading bar</i> 在表格下方以大字显示所选数值，例如 "
                  "\"V2 · Ply 1 · Air Pressure (bar) = 3.50\"。<i>Mark warnings with a symbol</i> 会为高亮数值添加圆圈"
                  "（超出公差）或三角形（需检查）。<i>Colour-blind friendly colours</i> "
                  "避免使用红/绿色。",
                  "查看预览，然后点击 " + B("Save") + "。"],
                 "表格快速缩放：Ctrl + 鼠标滚轮或 Ctrl +/-，Ctrl+0 恢复正常。设置按您的登录账户保存，"
                 "在每台电脑上都有效。欢迎语和强调色也在 Settings 中设置。"),
                ("task", "隐藏不需要的行（Machine Data）",
                 ["右键点击第一列 (6) 中的参数名 → " + M("Hide row") + "。"
                  "如需一次隐藏多行，先选中它们的名称（Ctrl+点击），再右键点击其中一个。",
                  "隐藏了行的位置，参数名上会显示一条蓝线。鼠标指向它可查看该处隐藏了哪些行，"
                  "点击它可重新显示。",
                  f"如需重新显示所有行，点击表格上方工具栏中的 {B('n rows hidden')} → "
                  + M("Show all rows") + "。在那里也可以单独显示某一行。"],
                 "隐藏的行按用户和机器记忆，即对该机器的所有系列有效。只改变视图：数值仍然保存。"
                 "复制和粘贴会跳过隐藏的行。红线表示隐藏的行中包含高亮数值。"),
                ("task", "选择 DTY 工艺并查看机器路径",
                 ["在 <i>Machine Data</i>（仅限 DTY 机器）中，为每个试验设置 <b>DTY Process</b> 行：Standard、"
                  "Elastane 或类棉变体。点击 " + B("Save") + "（Ctrl+S）。",
                  "点击表格上方工具栏中的 " + B("Schema") + " 显示或隐藏机器路径。"
                  "它显示您所点击单元格对应的试验：每一股在各自的位置、它们在哪里汇合、"
                  "氨纶来自其单独的来源。",
                  "点击一个工位（例如加热器）：其对应的行会在表格中高亮。再次点击或点击空白处"
                  "可取消。双击会跳转到该工位的第一个数值。"],
                 "预网络喷嘴（LW 0 - LW 1）和第 3 喷嘴（LW 3 之前）的行，只有在试验工艺需要或已录入数值时才会显示。"
                 "示意图只显示数值——请在表格中修改。有 2 股或以上时，<b>Route</b>、<b>Merge into ply</b> 和 <b>Merge "
                 "point</b> 行决定各股如何汇合（例如 Ply 4 在 LW 1 并入 Ply 3）；留空 = 常规路径。"
                 "错误的输入（未知的股、形成循环）会在示意图下方列出。在 ATY 机器上，示意图显示空气变形路径：芯丝和效果丝，包括牵伸区和喂入辊（速度 = LW 2 x (1 + OF %)）；只有芯丝被润湿，效果丝在喷嘴前才与之汇合；之后是 LW 2、稳定区、LW 3 和卷绕。"),
                ("task", "导入 Statimat 或 Itemat 报告",
                 [f"点击工具栏 (1) 中的 {B('Statimat import')} 或 {B('Itemat import')}。",
                  "选择 PDF 报告。数值会填入相应的实验室选项卡。",
                  f"检查数值，然后点击 {B('Save')}。"]),
                ("h", "试验和股"),
                ("task", "添加新试验",
                 ["点击 (2) 右侧的 <b>+</b> 图标（添加试验）。Create Experiment 会以向本系列添加试验的模式打开。"]),
                ("task", "复制现有试验",
                 [f"点击 (2) 右侧的 {B('Copy trials')}，或右键点击试验编号 (4) → "
                  + M("Copy trials…") + "。",
                  "勾选要复制的试验（Shift+点击可勾选整个范围）。在表格中已选中列的试验会自动勾选。",
                  "选择复制次数和顺序：<i>Repeat the block</i>（V1 V2 | V1 V2）或 <i>Each trial in "
                  "a row</i>（V1 V1 | V2 V2）。",
                  "检查结果表：如有需要，可在其中修改副本的数值（例如其他气压或喷嘴；ATY 上还有 "
                  "OF Core / OF Effect）。修改过的单元格会高亮显示。"
                  "<i>Show all fields</i> 显示其他机器设置。",
                  f"点击 {B('Copy n trials')}。"],
                 "会复制机器设置和股。副本的实验室数值、注释以及喷嘴前/后的纱线张力保持为空。"
                 "新试验添加在末尾，并在表格中高亮显示。每股的数值（例如 T1/T2 张力）之后在表格中修改，"
                 "股和纱线用 " + B("Yarns…") + " 修改。参考样永远不会被复制。"),
                ("task", "添加参考样（例如客户的原始筒子）",
                 [f"点击 (2) 右侧的 {B('+ Ref')}，或右键点击试验编号 (4) → "
                  + M("Add reference sample…") + "。",
                  "输入名称（例如客户、品号、批号）并确认。",
                  "在实验室选项卡中手动输入其实验室数值（Statimat/Itemat PDF 导入只按试验编号匹配，"
                  "因此不会填入参考样）。机器数据为可选项，例如用于记录客户提供的信息。"],
                 "参考样是基准，而不是试验：它不占用试验编号，以琥珀色背景的 <b>Ref</b> 显示在最前面"
                 "（名称在提示框中），在报告图表中以水平线绘制，并且不计入统计、Smart Chart、Quick Scan、Athena "
                 "和喷嘴数据导出。右键点击现有试验的编号，可将其转为参考样（保留其编号）或转回，"
                 "也可以重命名。"),
                ("task", "找出达到目标（或优于参考样）的试验",
                 [f"点击 (2) 右侧的 {B('vs Ref / Target')}，或右键点击 Ref 列 (4) → "
                  + M("Compare trials with this reference…") + "。",
                  "在 <i>Compare with</i> 中选择本系列的一个参考样或 <i>Own targets</i>。如需使用"
                  "自定义目标值，双击某列的第一行并输入（它会代替参考值使用；删除即可恢复）。",
                  "点击您关心的数值的列标题，选择 " + M("Higher is better") + "、"
                  + M("Lower is better") + " 或 " + M("Close to Ref is better") + "（" + M("Tolerance…")
                  + " 可设置允许偏差）。对每个重要数值重复此操作。",
                  "绿色 = 满足条件，红色 = 不满足。<b>Result</b> 按试验统计满足的数量，最好的试验"
                  "排在最上面。勾选 <i>Only trials that meet all criteria</i> 只显示优胜者。",
                  f"如需再次使用条件和目标：用 {B('Save as…')} 命名保存（例如客户和品号）。"
                  "之后在任何系列中都可在 <i>Criteria</i> 下选择。"],
                 "所有实验室选项卡同时比较。缺失的数值计为不满足；没有目标（也没有参考值）的条件不计入。"
                 "条件集供所有用户共享；删除：创建者或超级用户。双击某个试验可在 Machine Data 中查看。"
                 "系列中的任何内容都不会被修改。"),
                ("task", "删除试验",
                 ["单个试验：右键点击其试验编号 (4) → " + M("Delete V23…") + "。",
                  "多个试验：先在它们的列中选中单元格（拖动、Ctrl+点击或 Shift+点击），然后"
                  "右键点击其中一个的编号 → " + M("Delete n selected trials…") + "。",
                  "检查会一并删除的内容（股、实验室数值、备注），然后点击 " + B("Delete") + "。"],
                 "其他试验保留各自的编号——不会前移。新试验总是添加在剩余的最大编号之后，"
                 "不会填入空缺。超级用户可在 90 天内从 Recycle Bin 恢复已删除的试验。"
                 "允许在 Backlog 中移动该系列的人员执行删除。已用于制作纱线的试验"
                 "（半成品）不能删除。"),
                ("task", "更改某股的纱线，或添加/删除股",
                 [f"点击 (2) 右侧的 {B('Yarns…')}（或右键点击股行 (5)）。表格显示本系列的每一股（行）"
                  "和每个试验（列）。",
                  "<b>更改纱线：</b>点击该股的纱线，输入名称的一部分（例如 <i>167 dty</i>）"
                  "并选择——整股都会使用新纱线。",
                  "<b>为某个试验开/关某股：</b>点击其单元格。根数：选中单元格并输入 1–9"
                  "（Delete = 关），或右键点击。",
                  f"<b>新股：</b>{B('+ Add ply')}（目录中的纱线）或 {B('+ Trial output')}（另一个"
                  "试验的产出）——对所有试验生效。一种纱线在一个系列中始终保留其股号：再次添加时（例如"
                  "一次作为 <i>DTY</i>，一次作为 <i>Effect</i>）会成为同一股的第二行——在 <i>Use</i> 列中"
                  "选择用途。",
                  f"点击 {B('Apply')}——TrippleT 会先显示摘要。"],
                 "修改过的单元格为黄色；点击 Apply 之前不会保存任何内容（Cancel 放弃全部修改）。更换纱线后"
                 "保留该股的机器数值；删除某股会删除其在该试验中的数值。每个试验至少保留一股——"
                 "参考样可以完全没有纱线。需要写入权限。"),
                ("task", "添加另一个试验系列或实验室设备",
                 ["使用侧边栏中的 " + M("Add Trial Series") + " 或 " + M("Add Lab Machines") + "。"],
                 "一旦为系列分配了实验室设备，就会出现相应的实验室选项卡（例如 Statimat M）。"),
                ("h", "实验室结果和复测"),
                ("task", "标记实验室数值需要复测（超级用户）",
                 ["打开实验室选项卡，右键点击该试验的列标题 → " + M("Flag Vn for retest…") + "。",
                  "可输入备注（可选）并确认。"],
                 "该系列会以最高优先级回到 Backlog，并在那里显示 <b>RETEST</b>。"),
                ("h", "文件、报告和标签"),
                ("task", "附加图片或 PDF",
                 [f"点击 {B('Upload images')} 或 {B('Upload PDFs')} 并选择文件。",
                  "一旦有附件，这些按钮旁边就会出现图片和 PDF 图标。点击即可查看文件。"]),
                ("task", "打开本系列的报告",
                 ["工具栏 (1) 中的报告图标（图表符号）会为本系列打开一个带图表的新报告。",
                  f"如有已保存的报告，旁边会出现一个列表和 {B('Go!')}：选择报告并点击 Go!。"],
                 "详情请参见 Report 界面的帮助。"),
                ("task", "打印带试验编号的标签",
                 ["点击 (2) 中的标签图标，选择标签纸上的起始位置，保存 PDF 并打印。"]),
                ("task", "查看关联的实验申请",
                 ["点击 (2) 中的 <b>ER</b> 图标。关联了申请时才会显示。"]),
                ("task", "重新加载界面",
                 [f"点击 {B('↻')} 或按 F5。当前打开的选项卡保持选中。"]),
            ]},
            {"key": "screen", "title": "界面说明", "blocks": [
                ("svg", SVG, {"lab_hint": "（实验室选项卡仅在使用时显示）",
                              "keys_hint": "Enter 下一单元格 · Ctrl+C / Ctrl+V 复制和粘贴 · Delete 清空所选单元格 · Ctrl+Z 撤销，Ctrl+Y 重做 · Ctrl+S 保存 · F5 重新加载"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) 工具栏", "实验 ID 和系列、附件（上传和查看图片/PDF）、Statimat 和 "
                                 "Itemat 导入、报告图标和已保存的报告（列表 + Go!）、重新加载 (↻)、Save 和本帮助。"),
                    ("(2) 材料行", "系列的材料、关联的实验申请 (ER)、机器信息、"
                                 "试验标签、<b>+T</b>（添加试验）、<b>+ Ref</b>（添加参考样）和 "
                                 "<b>Copy trials</b>。每股后面有一个小筒子：绿色 = 纱线有库存"
                                 "（点击纱线或筒子可查看存放位置和纸管颜色），划掉的纸管"
                                 " = 无库存。"),
                    ("(3) 选项卡", "每类数据一个选项卡，见 <i>选项卡</i> 选项卡。实验室选项卡仅在"
                                 "系列使用该实验室设备时显示。"),
                    ("(4) 试验行", "试验编号（V1、V2、…）；参考样以 <b>Ref</b> 显示在最前面"
                                 "（琥珀色）。右键：复制试验、参考样。"),
                    ("(5) 股行", "每列对应的股（一个试验可以有多股）。右键：系列的纱线。"),
                    ("(6) 参数名", "每个参数一行。右键：填充行、显示/隐藏自定义组。"),
                    ("(7) 单元格", "每个试验的数值。可存储数值的地方可编辑；修改过的单元格等待 "
                                 "Save。"),
                ]),
            ]},
            {"key": "tabs", "title": "选项卡", "blocks": [
                ("areas", [
                    ("Machine Data", "每个试验的机器设置（速度、超喂、气压、喷嘴、…）。行是"
                                     "参数，列是试验和股。在 DTY 机器上，T2 Tension 下方的 <i>D/Y Ratio (T2/T1)</i> 行"
                                     "由 T1 和 T2 自动计算，不能编辑。"),
                    ("R&amp;D Machine Data", "附加的开发参数，操作方式与 Machine Data 相同。"),
                    ("实验室选项卡", f"{LAB_TABS}。每个试验的实验室设备结果；仅在"
                                 "系列使用该设备时显示。右键点击列标题可标记复测。"),
                    ("YarnScope / YarnScope ATY", "纱线测量文件的分析，带有各自的子选项卡"
                                                  "（例如信号、纱线外观、工艺比较）。"),
                    ("Athena", "AI 助手，分析系列并建议下一步。最近一次分析会被"
                               "保留；新的分析需要一点时间。"),
                    ("Notes", "系列的自由文本备注。"),
                ]),
                ("note", "<b>提示：</b>在 Backlog 或 All Experiments 中 Ctrl+点击一个系列，可在"
                         "另一个选项卡中打开，例如用于比较两个系列。"),
            ]},
        ],
    },
}
