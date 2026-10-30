# ui/widgets/whats_new_texts.py
"""What's new (EN/DE/ES) - Sidebar -> Account -> "What's new" and once
after login (ui/whats_new.py): versions listed on the left, the new features
of the chosen version on the right as cards.

RELEASES, newest first. Each entry has
    "version": "current" -> the version being worked on = app_meta.APP_VERSION
               "4.6.3"   -> a compiled version (fixed)
    "date":    "" while current, the compile date ("2026-10-15") once fixed
    "texts":   {lang: [blocks]}
New features go into the "current" entry right away (all three languages).

Blocks:
    ("h", "Section")                                      heading (screen/area)
    ("feature", title, text, where, sketch)               one card; sketch =
        file name in assets/images/whats_new/ (tools/gen_whats_new_svgs.py)
        or None. `where` = how to get there, e.g. "Show Experiment → + Ref".

Compiled before the user says so: the exe shows the "current" entry with its
own build date instead of "in progress".

When the user announces a compile ("ich habe kompiliert"): write the actual
version (app_meta.APP_VERSION at that moment) and the date into the current
entry. The user then raises APP_VERSION for the test environment; the next
new feature starts a new "current" entry at the top (an empty one must not
exist). No version check - when to compile stays with the user.

Same block structure in all three languages. Button/menu names stay English.
"""

RELEASES = [
    {
        "version": "current",
        "date": "",
        "texts": {
            # ═══════════════════════════════ EN ═══════════════════════════════
            "en": [
                ("h", "Show Experiment"),
                ("feature", "Yarns of the series in one table",
                 "<b>Yarns…</b> shows every ply of the series with its yarn and every trial. Click a yarn to change "
                 "it for the whole ply - type a part of the name to find it, e.g. <i>167 dty</i>. Click a cell to "
                 "switch a ply on or off for one trial, type 1-9 for the number of ends. <b>+ Add ply</b> adds a "
                 "ply for all trials. Changed cells are yellow, nothing is saved before <b>Apply</b>.",
                 "Show Experiment → Machine Data → <b>Yarns…</b> (or right-click the Ply row)", "wn_series_yarns.svg"),
                ("feature", "Where are my spools?",
                 "A small spool behind every ply in the Material line tells you at a glance: green spool = this yarn "
                 "is in stock, crossed-out tube = nothing in stock. Click the yarn or the green spool to see every spool in "
                 "stock by storage location, with batch, weight and tube colour. Spools assigned to this series "
                 "are bold. <b>Open in Yarn Stock</b> takes you straight to the yarn.",
                 "Show Experiment → Material line → yarn or spool symbol", "wn_spool_locations.svg"),
                ("feature", "Notes on values",
                 "Write down why a value looks the way it does - right where it is: right-click a value → "
                 "<b>Add note…</b>, e.g. <i>Spool had knots, measured again</i>. A small purple triangle marks the "
                 "cell, pointing at it shows the note with name and date. Right-click a trial number for a note on "
                 "the whole trial. The <b>Notes</b> tab lists all notes of the series, double-click jumps to the "
                 "value. Everybody can write notes. In the <b>Smart Chart</b>, the <b>Notes</b> button shows them as a "
                 "purple outline with the note in the tooltip. They are not printed in the PDF unless you tick "
                 "<i>Include notes on values</i> when exporting.",
                 "Show Experiment → right-click a value → <b>Add note…</b>", "wn_cell_notes.svg"),
                ("feature", "Reference samples",
                 "Add a customer's original spool as a benchmark. It appears as a highlighted <i>Ref</i> column "
                 "and as a horizontal line in the report - and is never counted as a trial.",
                 "Show Experiment → Machine Data → <b>+ Ref</b>", "wn_reference.svg"),
                ("feature", "Copy trials - with changes",
                 "Choose which trials, how often and in which order, and change values (e.g. air pressure, jet, "
                 "OF Core/Effect) before copying. Comments and the tensions before/after the jet are not copied - "
                 "the copies start with them empty.",
                 "Show Experiment → Machine Data → <b>Copy trials</b>", "wn_copy_trials.svg"),
                ("feature", "D/Y Ratio (T2/T1)",
                 "Calculated automatically from T1 and T2 and shown right below T2 Tension on DTY machines.",
                 "Show Experiment → Machine Data", "wn_dy_ratio.svg"),
                ("feature", "Faster data entry - like in Excel",
                 "Type a value and press <b>Enter</b>: you land in the cell below, ready for the next value "
                 "(<b>Shift+Enter</b> goes up). Click a cell (or select several) and press <b>Delete</b> to empty "
                 "them - no double-click needed. Save with <b>Save</b> or <b>Ctrl+S</b>; instead of a \"Saved\" "
                 "message to click away, the yellow disappears and a green tick lights up briefly in the middle - "
                 "you can keep typing right away.",
                 "Show Experiment → any table", None),
                ("feature", "Undo with Ctrl+Z",
                 "Typed the wrong value, pasted into the wrong place or deleted too much? <b>Ctrl+Z</b> takes it "
                 "back step by step, <b>Ctrl+Y</b> does it again - as long as you have not saved yet.",
                 "Show Experiment → any table", None),
                ("feature", "Back on your tab",
                 "A series opens on the tab you used last for it, e.g. <i>Statimat M</i> instead of always "
                 "<i>Machine Data</i>.",
                 "Show Experiment", None),
                ("feature", "Hide rows you don't need",
                 "Right-click a parameter name → <b>Hide row</b>. A blue line shows where rows are hidden; click "
                 "it, or use <b>n rows hidden</b>, to show them again. Remembered per machine.",
                 "Show Experiment → Machine Data → right-click a parameter name", "wn_hide_rows.svg"),
                ("feature", "See what is not saved yet",
                 "Changed cells stay yellow until you save (<b>Save</b> or <b>Ctrl+S</b>). The button shows how many, "
                 "e.g. <b>Save (3)</b>, and the "
                 "tab gets a dot. Closing a tab or the program with unsaved changes now asks first - before, they "
                 "were lost without a word.",
                 "Show Experiment", "wn_unsaved.svg"),
                ("feature", "Typo check when saving",
                 "Machine settings far outside the usual range of this machine (e.g. 35 instead of 3.5 bar) are "
                 "listed before saving. You can go back or save anyway.",
                 "Show Experiment → <b>Save</b>", "wn_unusual.svg"),
                ("feature", "Change history (superusers)",
                 "See who changed a value, when, and what it was before - for one value or the whole series.",
                 "Show Experiment → right-click a value → <b>Change history…</b>", "wn_history.svg"),
                ("h", "Smart Chart"),
                ("feature", "New Smart Chart: find trials by their properties",
                 "Pick trials across <b>all</b> series by yarn, jet geometry, machine settings and lab results - e.g. all polyester "
                 "trials with 70–80 dtex end titer and 30–40 filaments. <b>+ Add filter</b> shows how the values are "
                 "spread and how many trials each filter leaves; number filters can keep only whole numbers, every 0.5 or "
                 "values you tick. Then chart any field against any other - as points, "
                 "trend lines with R², mean lines, bars, box plots, violins, histograms or a density map - colour by "
                 "jet, machine or a number (colour scale), pick a palette or your own colours, split into one small "
                 "chart per machine. Click a point "
                 "to find the trial in the list, double-click to open it. Save your chart as a view (also shared), "
                 "export to PDF or Excel.",
                 "Sidebar → <b>Smart Chart</b>", "wn_smart_chart.svg"),
                ("feature", 'Is this comparison fair?',
                 'A coloured bar above the chart warns when the groups you compare also differ in other things that change the result - e.g. jet A was mostly tested on PES at 3.5 bar, jet B on PA at 2 bar. Green, yellow or red, with the reason in one sentence. <b>Details</b> shows every condition, <b>Make it fairer</b> keeps only what all groups have in common. It also warns about very small groups, groups from one single series and groups in different X ranges.',
                 'Smart Chart → bar above the chart', "wn_fairness.svg"),
                ("feature", 'Dashboard: build your own page, like Power BI',
                 'Switch Smart Chart to <b>Dashboard</b>: a page with several visuals side by side. Drag fields from <b>Fields</b> - every table, from Statimat and Itemat to DTYoMat, jet and yarn - into the wells of a visual. New visuals: <b>Matrix</b> (e.g. FP/m per jet and air pressure, coloured - empty cells show where trials are missing), <b>Card</b> (one number) and <b>Table</b>. Click a bar, box or matrix cell and all other visuals filter to it. <b>Slicers</b> pick values for the whole page - as a list, dropdown, tiles or a range slider. Place visuals freely and resize them, work with several pages (tabs at the bottom) and add filters to one page or one visual. New: <b>calculated fields</b> from your own formula, <b>targets</b> (green/red, target lines), <b>drill-down</b> machine → jet and <b>selecting points</b> to filter the page. Plus: <b>templates</b> (Jet comparison, Yarn overview, Machine check, Lab overview), <b>PDF</b> of one or all pages, <b>Excel</b> per visual or page, notes on values, undo with <b>Ctrl+Z</b>, and <b>lining up</b> several visuals at once (Ctrl+click, then align, same size or distribute).',
                 'Smart Chart → <b>Dashboard</b>', "wn_dashboard.svg"),
                ("feature", 'Lab statistics in the dashboard',
                 'Count <b>experiments, trial series or trials</b> - per month, product group, order type, project, owner or lab machine (<i>Tested on</i>). The new visual <b>Columns</b> shows them stacked, side by side or as 100 %; months and years run in order, empty months show as 0. Start with <b>New</b> → <b>Lab statistics</b>. The numbers are the same as on the Statistics page - now for everybody and with slicers.',
                 'Smart Chart → <b>Dashboard</b> → <b>New</b> → <b>Lab statistics</b>', "wn_dashboard_stats.svg"),
                ("feature", 'Dashboards: look at them, share them',
                 'The new page <b>Dashboards</b> shows your own dashboards and the ones colleagues shared with you. Here you only look: slicers, clicking bars to filter, drill-down, page tabs and <b>PDF</b> work - nothing gets changed by accident. To share your dashboard, open it in Smart Chart and click <b>Share…</b>: with everybody, with single people or with groups (read, write, admin, superuser), each to <b>view</b> or to <b>edit</b>. Only you can share or delete it.',
                 'Sidebar → Tools → <b>Dashboards</b> · Smart Chart → <b>Share…</b>', "wn_dashboards.svg"),
                ("feature", 'Superusers decide who may use which tool',
                 'In <b>Manage User → Access…</b> a superuser switches every tool and screen on or off - for a group (read, write, admin) or for a single person, e.g. Smart Chart for one colleague, or no Backlog for a group. A setting for a person wins over the group; without settings everything stays as before. Blocked tools disappear from the sidebar from the next login.',
                 'Sidebar → Superuser → Manage User → <b>Access…</b>', "wn_feature_access.svg"),
                ("h", "Settings"),
                ("feature", 'Choose your start screen',
                 'Decide which screen opens after the login - Backlog (as before), All Experiments, Dashboards, Yarn Stock or another tool you use. If a superuser switches that tool off for you, Backlog opens instead.',
                 'Sidebar → Account → <b>Settings</b> → <b>Start screen</b>', "wn_start_screen.svg"),
                ("feature", "Text size for the whole program",
                 "Normal, Large, Extra large or Huge - buttons, menus, tables and dialogs all grow. Applies after a "
                 "restart. Welcome message and accent colour are set here, too.",
                 "Sidebar → Account → <b>Settings</b>", "wn_text_size.svg"),
                ("feature", "Easier reading in tables",
                 "High contrast, a crosshair for row and column, a reading bar with the value in large words, "
                 "warning symbols and colour-blind friendly colours. Zoom a table with Ctrl + mouse wheel.",
                 "Sidebar → Account → <b>Settings</b> → Show Experiment tables", "wn_reading.svg"),
                ("h", "Help"),
                ("feature", "Help in three languages",
                 "Show Experiment, Backlog, Report, All Experiments, Create Experiment, Manage Yarn and Manage Jets "
                 "now have their own help in English, German and Spanish: step-by-step answers to \"How do I…?\", a "
                 "sketch of the screen and the rules. The flags switch the language.",
                 "Round <b>?</b> button on these screens", "wn_help.svg"),
                ("feature", "Help search - \"Where do I find…?\"",
                 "Type your question in your own words and get the matching help page - in English, German or "
                 "Spanish. <b>Take me there</b> opens the screen.",
                 "Sidebar → <b>Help (F1)</b> or the F1 key", "wn_help_search.svg"),
                ("feature", "Search in Fresh off the Spool",
                 "Know a feature exists but not when it came? Type a word in the search field above the version "
                 "list - all versions are searched at once, in English, German and Spanish. Versions with hits show "
                 "how many; click one to jump to it. Each version is now split into tabs by area, e.g. "
                 "<i>Show Experiment (8)</i>.",
                 "Sidebar → Account → <b>Fresh off the Spool</b> → search field", "wn_whats_new_search.svg"),
                ("feature", "Fresh off the Spool as PDF",
                 "Save a version's news as a PDF - to print it or send it to colleagues. Each topic stays together "
                 "on one page.",
                 "Sidebar → Account → <b>Fresh off the Spool</b> → <b>PDF</b>", "wn_whats_new_pdf.svg"),
                ("h", "Backlog and All Experiments"),
                ("feature", "Move several cards at once",
                 "Hold <b>Ctrl</b> and click the cards (or <b>Shift+click</b> for a whole range), then drag one of "
                 "them - all selected cards move together, e.g. from <i>To Be Cleaned</i> to <i>Archived</i>. "
                 "TrippleT asks once and tells you if a card was not allowed to move.",
                 "Backlog → <b>Ctrl+click</b> the cards → drag", "wn_backlog_multi_move.svg"),
                ("feature", "Backlog on wide screens",
                 "On big monitors all four columns stand side by side and use the full height.",
                 "Backlog", "wn_wide_backlog.svg"),
                ("feature", "Recycle Bin",
                 "A deleted trial series can be restored for 90 days. Whoever may move a series in the Backlog may "
                 "delete it (in To Be Cleaned: superusers only).",
                 "Sidebar → Superuser → <b>Recycle Bin</b>", "wn_recycle_bin.svg"),
                ("feature", "Look inside the Recycle Bin",
                 "Not sure what a deleted series contains? Double-click it: it opens read only in Show Experiment. "
                 "A yellow bar lets you <b>Restore for good</b>, put it <b>Back to Recycle Bin</b> or "
                 "<b>Delete permanently</b>. Closing the tab puts it back - with its original deletion date.",
                 "Sidebar → Superuser → <b>Recycle Bin</b> → double-click a series", "wn_recycle_preview.svg"),
                ("feature", "All Experiments uses the whole window",
                 "The list fills the full width and height of the window - the last columns are visible without "
                 "scrolling sideways - and is shown larger on big screens.",
                 "All Experiments", "wn_all_experiments.svg"),
                ("h", "Yarns"),
                ("feature", "See the colour of a yarn",
                 "A small square in front of the yarn name shows its colour - black, white, beige, grey, natural. "
                 "Hold the mouse over it to read the colour. You can also search by colour, e.g. <i>black</i>. The "
                 "colour comes from the <i>Colour</i> field of the yarn (<b>Manage Yarn</b>).",
                 "Yarns… dialog, Create Experiment, Yarn Stock, Manage Yarn, Reassign Yarn, Show Experiment "
                 "(Ply row)", "wn_yarn_colour.svg"),
                ("h", "Yarn Stock"),
                ("feature", "Stock status per yarn",
                 "The traffic light now shows each yarn as a whole: all its batches in stock against its minimum "
                 "stock. Used-up batches disappear from the overview, notifications come once per yarn. Only "
                 "superusers may change the minimum stock.",
                 "Yarn Stock → Overview", "wn_stock_status.svg"),
                ("feature", "New spools - straight to the new spools and the label queue",
                 "<b>New spool(s)</b> starts with an empty selection and afterwards jumps right to the new spools. "
                 "They go to the label queue automatically (tick box in the dialog).",
                 "Yarn Stock → <b>New spool(s)</b>", "wn_new_spools.svg"),
                ("feature", "Stock take - location by location",
                 "A superuser starts a stock take round (and can leave out single locations). Every location is a "
                 "tile: grey = open, green = all fine, orange = differences. Click one and scan its spools (no label? "
                 "double-click it in the list). "
                 "<b>Results</b> shows what was found where, exportable to Excel. Spools in another place are moved "
                 "right away, missing ones are only booked out when you finish - after asking.",
                 "Yarn Stock → Rack lookup → <b>Stock take…</b>", "wn_stock_take.svg"),
                ("feature", "Spool history",
                 "Every change of a spool is recorded: created, changed, moved, booked out, stock take. Without a "
                 "selection you see the whole batch, including used-up spools.",
                 "Yarn Stock → <b>History…</b>", "wn_spool_history.svg"),
                ("feature", "Scan labels, keep changes",
                 "In <i>Go to spool #</i> you can scan the spool label instead of typing the number. And Yarn Stock "
                 "now asks before unsaved spool changes are lost. Help in three languages: round button top right.",
                 "Yarn Stock → <b>Go to spool #</b>", None),
                ("h", "General"),
                ("feature", "Fresh off the Spool: what's new in TrippleT",
                 "All new features of every version in one place: one tab per area, searchable and as PDF. "
                 "It opens by itself once after a new version - and anytime in the sidebar.",
                 "Sidebar → Account → <b>Fresh off the Spool</b>", "fresh_off_the_spool.png"),
                ("feature", "Recent series",
                 "The series you opened last are one click away: <b>Recent</b> in the sidebar (at the bottom, above Account). "
                 "Click one to open it, <b>Ctrl+click</b> opens it in a new tab. The list follows you to every PC.",
                 "Sidebar → <b>Recent</b>", None),
                ("feature", "Athena answers in your language",
                 "Athena and the Lab Assistant now answer in the language you ask in - English, German, Spanish, "
                 "… Without a question (e.g. the automatic analysis) the answer is in English.",
                 "Show Experiment → Athena, Lab Assistant", None),
                ("feature", "Error messages that help",
                 "When something goes wrong, TrippleT now says in plain words what did not work, why, and what you "
                 "can do - e.g. \"The file is open in another program - close it (e.g. in Excel) and try again.\" "
                 "The technical text is under <b>Show Details</b>, to send to the admin.",
                 "Whole program", None),
                ("feature", "All texts in English",
                 "Messages, buttons, menus and status texts that were still in German are now in English everywhere - "
                 "e.g. the right-click menu in the Backlog says <b>Reassign yarn…</b>. Lab terms such as Kurzhocker or "
                 "Langwelle stay as they are.",
                 "Whole program", None),
            ],
            # ═══════════════════════════════ DE ═══════════════════════════════
            "de": [
                ("h", "Show Experiment"),
                ("feature", "Garne der Serie in einer Tabelle",
                 "<b>Yarns…</b> zeigt alle Plies der Serie mit ihrem Garn und alle Versuche. Ein Klick aufs Garn "
                 "tauscht es für die ganze Ply - zum Finden einen Teil des Namens tippen, z.&nbsp;B. <i>167 dty</i>. "
                 "Ein Klick in eine Zelle schaltet die Ply für diesen Versuch ein oder aus, 1-9 tippen setzt die "
                 "Anzahl Enden. <b>+ Add ply</b> fügt eine Ply für alle Versuche hinzu. Geänderte Zellen sind gelb, "
                 "gespeichert wird erst mit <b>Apply</b>.",
                 "Show Experiment → Machine Data → <b>Yarns…</b> (oder Rechtsklick auf die Ply-Zeile)",
                 "wn_series_yarns.svg"),
                ("feature", "Wo liegen meine Spulen?",
                 "Eine kleine Spule hinter jeder Ply in der Materialzeile zeigt auf einen Blick: grüne Spule = dieses "
                 "Garn ist am Lager, durchgestrichene Hülse = nichts am Lager. Ein Klick aufs Garn oder die grüne Spule zeigt "
                 "alle Spulen am Lager nach Lagerplatz, mit Batch, Gewicht und Hülsenfarbe. Spulen, die dieser Serie "
                 "zugewiesen sind, stehen fett. <b>Open in Yarn Stock</b> springt direkt zum Garn.",
                 "Show Experiment → Materialzeile → Garn oder Spulen-Symbol", "wn_spool_locations.svg"),
                ("feature", "Notizen an Werten",
                 "Festhalten, warum ein Wert so ist - direkt dort, wo er steht: Rechtsklick auf einen Wert → "
                 "<b>Add note…</b>, z.&nbsp;B. <i>Spule hatte Knoten, nachgemessen</i>. Ein kleines violettes "
                 "Dreieck markiert die Zelle, mit der Maus darauf zeigen zeigt die Notiz mit Name und Datum. "
                 "Rechtsklick auf eine Versuchsnummer für eine Notiz zum ganzen Versuch. Der Tab <b>Notes</b> "
                 "listet alle Notizen der Serie, Doppelklick springt zum Wert. Notizen schreiben darf jeder. Im "
                 "<b>Smart Chart</b> zeigt der Knopf <b>Notes</b> sie als violetten Rand mit der Notiz im Tooltip. "
                 "Ins PDF kommen sie nur, wenn man beim Export <i>Include notes on values</i> ankreuzt.",
                 "Show Experiment → Rechtsklick auf einen Wert → <b>Add note…</b>", "wn_cell_notes.svg"),
                ("feature", "Referenzmuster",
                 "Die Originalspule eines Kunden als Vergleich hinzufügen. Sie erscheint als hervorgehobene "
                 "<i>Ref</i>-Spalte und im Report als waagrechte Linie - und zählt nie als Versuch.",
                 "Show Experiment → Machine Data → <b>+ Ref</b>", "wn_reference.svg"),
                ("feature", "Versuche kopieren - mit Änderungen",
                 "Wählen, welche Versuche wie oft und in welcher Reihenfolge kopiert werden, und Werte (z.&nbsp;B. "
                 "Luftdruck, Düse, OF Core/Effect) vor dem Kopieren ändern. Kommentare und Fadenspannungen "
                 "vor/nach Jet werden nicht mitkopiert - die Kopien starten damit leer.",
                 "Show Experiment → Machine Data → <b>Copy trials</b>", "wn_copy_trials.svg"),
                ("feature", "D/Y Ratio (T2/T1)",
                 "Wird bei DTY-Maschinen automatisch aus T1 und T2 berechnet und direkt unter T2 Tension angezeigt.",
                 "Show Experiment → Machine Data", "wn_dy_ratio.svg"),
                ("feature", "Schneller erfassen - wie in Excel",
                 "Wert tippen und <b>Enter</b> drücken: Du landest in der Zelle darunter, bereit für den nächsten "
                 "Wert (<b>Umschalt+Enter</b> geht nach oben). Zelle anklicken (oder mehrere markieren) und "
                 "<b>Entf</b> drücken leert sie - ohne Doppelklick. Speichern mit <b>Save</b> oder <b>Strg+S</b>; "
                 "statt einer \"Saved\"-Meldung zum Wegklicken verschwindet das Gelb und in der Mitte leuchtet "
                 "kurz ein grünes Häkchen auf - du kannst sofort weitertippen.",
                 "Show Experiment → jede Tabelle", None),
                ("feature", "Rückgängig mit Strg+Z",
                 "Falschen Wert getippt, an der falschen Stelle eingefügt oder zu viel gelöscht? <b>Strg+Z</b> nimmt "
                 "es Schritt für Schritt zurück, <b>Strg+Y</b> stellt es wieder her - solange noch nicht gespeichert "
                 "ist.",
                 "Show Experiment → jede Tabelle", None),
                ("feature", "Zurück auf deinem Reiter",
                 "Eine Serie öffnet sich auf dem Reiter, den du zuletzt bei ihr benutzt hast, z.&nbsp;B. "
                 "<i>Statimat M</i> statt immer <i>Machine Data</i>.",
                 "Show Experiment", None),
                ("feature", "Nicht benötigte Zeilen ausblenden",
                 "Rechtsklick auf einen Parameternamen → <b>Hide row</b>. Eine blaue Linie zeigt, wo Zeilen fehlen; "
                 "ein Klick darauf oder <b>n rows hidden</b> holt sie zurück. Gemerkt pro Maschine.",
                 "Show Experiment → Machine Data → Rechtsklick auf Parameternamen", "wn_hide_rows.svg"),
                ("feature", "Sehen, was noch nicht gespeichert ist",
                 "Geänderte Zellen bleiben gelb, bis gespeichert ist (<b>Save</b> oder <b>Strg+S</b>). Der Knopf zeigt "
                 "die Anzahl, z.&nbsp;B. "
                 "<b>Save (3)</b>, und der Tab bekommt einen Punkt. Wer einen Tab oder das Programm mit "
                 "ungespeicherten Änderungen schliesst, wird jetzt gefragt - vorher gingen sie wortlos verloren.",
                 "Show Experiment", "wn_unsaved.svg"),
                ("feature", "Tippfehler-Prüfung beim Speichern",
                 "Maschineneinstellungen weit ausserhalb des Üblichen dieser Maschine (z.&nbsp;B. 35 statt 3.5 bar) "
                 "werden vor dem Speichern aufgelistet. Zurück zum Korrigieren oder trotzdem speichern.",
                 "Show Experiment → <b>Save</b>", "wn_unusual.svg"),
                ("feature", "Änderungsverlauf (Superuser)",
                 "Sehen, wer einen Wert wann geändert hat und was vorher drinstand - für einen Wert oder die ganze "
                 "Serie.",
                 "Show Experiment → Rechtsklick auf einen Wert → <b>Change history…</b>", "wn_history.svg"),
                ("h", "Smart Chart"),
                ("feature", "Neuer Smart Chart: Versuche über ihre Eigenschaften finden",
                 "Versuche über <b>alle</b> Serien nach Garn, Jet-Geometrie, Maschineneinstellungen und Laborwerten auswählen - "
                 "z.&nbsp;B. alle Polyester-Versuche mit 70–80 dtex Endtiter und 30–40 Filamenten. <b>+ Add filter</b> "
                 "zeigt, wie sich die Werte verteilen und wie viele Versuche jeder Filter übrig lässt; Zahlenfilter können "
                 "nur ganze Zahlen, alle 0.5 oder angekreuzte Werte behalten. Danach jedes "
                 "Feld gegen jedes andere darstellen - als Punkte, Trendlinien mit R², Mittelwert-Linien, Balken, "
                 "Boxplots, Violins, Histogramme oder Dichte-Karte -, nach Jet, Maschine oder einer Zahl (Farbskala) "
                 "einfärben, Palette oder eigene Farben wählen, pro Maschine ein kleines Diagramm. Klick auf einen "
                 "Punkt findet den Versuch in der "
                 "Liste, Doppelklick öffnet ihn. Diagramm als View speichern (auch geteilt), als PDF oder Excel exportieren.",
                 "Sidebar → <b>Smart Chart</b>", "wn_smart_chart.svg"),
                ("feature", 'Ist dieser Vergleich fair?',
                 'Eine farbige Leiste über dem Diagramm warnt, wenn sich die verglichenen Gruppen auch in anderen Dingen unterscheiden, die das Ergebnis verändern - z.&nbsp;B. Jet A wurde vor allem auf PES bei 3.5 bar getestet, Jet B auf PA bei 2 bar. Grün, gelb oder rot, mit dem Grund in einem Satz. <b>Details</b> zeigt jede Bedingung, <b>Make it fairer</b> behält nur, was alle Gruppen gemeinsam haben. Gewarnt wird auch bei sehr kleinen Gruppen, Gruppen aus einer einzigen Serie und Gruppen in verschiedenen X-Bereichen.',
                 'Smart Chart → Leiste über dem Diagramm', "wn_fairness.svg"),
                ("feature", 'Dashboard: eigene Seite bauen, wie in Power BI',
                 'Smart Chart auf <b>Dashboard</b> umschalten: eine Seite mit mehreren Visuals nebeneinander. Felder aus <b>Fields</b> - jede Tabelle, von Statimat und Itemat bis DTYoMat, Jet und Garn - in die Ablagen eines Visuals ziehen. Neue Visuals: <b>Matrix</b> (z.&nbsp;B. FP/m pro Jet und Luftdruck, eingefärbt - leere Zellen zeigen, wo Versuche fehlen), <b>Card</b> (eine Zahl) und <b>Table</b>. Klick auf einen Balken, eine Box oder eine Matrix-Zelle, und alle anderen Visuals filtern sich darauf. <b>Slicer</b> wählen Werte für die ganze Seite - als Liste, Dropdown, Knöpfe oder Bereichsregler. Visuals frei platzieren und in der Grösse ziehen, mehrere Seiten (Reiter unten) und Filter nur für eine Seite oder ein Visual. Neu: <b>berechnete Felder</b> per eigener Formel, <b>Zielwerte</b> (grün/rot, Ziellinien), <b>Drill-down</b> Maschine → Jet und <b>Punkte auswählen</b>, um die Seite zu filtern. Dazu: <b>Vorlagen</b> (Jet comparison, Yarn overview, Machine check, Lab overview), <b>PDF</b> einer oder aller Seiten, <b>Excel</b> pro Visual oder Seite, Notizen an Werten, Rückgängig mit <b>Strg+Z</b> und mehrere Visuals auf einmal <b>ausrichten</b> (Strg+Klick, dann ausrichten, gleich gross machen oder verteilen).',
                 'Smart Chart → <b>Dashboard</b>', "wn_dashboard.svg"),
                ("feature", 'Laborstatistik im Dashboard',
                 '<b>Experimente, Versuchsserien oder Versuche</b> zählen - pro Monat, Produktgruppe, Auftragsart, Projekt, Owner oder Labormaschine (<i>Tested on</i>). Das neue Visual <b>Columns</b> zeigt sie gestapelt, nebeneinander oder als 100 %; Monate und Jahre laufen in der richtigen Reihenfolge, leere Monate erscheinen als 0. Am einfachsten mit <b>New</b> → <b>Lab statistics</b> beginnen. Die Zahlen sind dieselben wie auf der Statistics-Seite - jetzt für alle und mit Slicern.',
                 'Smart Chart → <b>Dashboard</b> → <b>New</b> → <b>Lab statistics</b>', "wn_dashboard_stats.svg"),
                ("feature", 'Dashboards: anschauen und teilen',
                 'Die neue Seite <b>Dashboards</b> zeigt deine eigenen Dashboards und die, die Kollegen für dich freigegeben haben. Hier wird nur geschaut: Slicer, Klick auf Balken zum Filtern, Drill-down, Seiten-Reiter und <b>PDF</b> gehen - versehentlich verändern kann man nichts. Zum Teilen das Dashboard in Smart Chart öffnen und auf <b>Share…</b> klicken: für alle, für einzelne Personen oder für Gruppen (read, write, admin, superuser), je zum <b>Anschauen</b> oder zum <b>Bearbeiten</b>. Teilen oder löschen kannst nur du.',
                 'Sidebar → Tools → <b>Dashboards</b> · Smart Chart → <b>Share…</b>', "wn_dashboards.svg"),
                ("feature", 'Superuser bestimmen, wer welches Tool nutzen darf',
                 'In <b>Manage User → Access…</b> schaltet ein Superuser jedes Tool und jeden Screen ein oder aus - für eine Gruppe (read, write, admin) oder für eine einzelne Person, z.&nbsp;B. Smart Chart für einen Kollegen oder kein Backlog für eine Gruppe. Die Einstellung für eine Person gewinnt über die Gruppe; ohne Einstellung bleibt alles wie bisher. Gesperrte Tools verschwinden ab dem nächsten Login aus der Sidebar.',
                 'Sidebar → Superuser → Manage User → <b>Access…</b>', "wn_feature_access.svg"),
                ("h", "Settings"),
                ("feature", 'Eigene Startseite wählen',
                 'Bestimme, welcher Screen nach dem Login aufgeht - Backlog (wie bisher), All Experiments, Dashboards, Yarn Stock oder ein anderes Tool, das du nutzt. Schaltet ein Superuser dieses Tool für dich aus, öffnet sich stattdessen Backlog.',
                 'Sidebar → Account → <b>Settings</b> → <b>Start screen</b>', "wn_start_screen.svg"),
                ("feature", "Textgrösse fürs ganze Programm",
                 "Normal, Large, Extra large oder Huge - Knöpfe, Menüs, Tabellen und Dialoge wachsen alle mit. Gilt "
                 "nach einem Neustart. Auch Willkommensnachricht und Akzentfarbe werden hier eingestellt.",
                 "Sidebar → Account → <b>Settings</b>", "wn_text_size.svg"),
                ("feature", "Tabellen besser lesbar",
                 "Hoher Kontrast, Fadenkreuz für Zeile und Spalte, Lese-Leiste mit dem Wert in grosser Schrift, "
                 "Warnsymbole und farbenblind-freundliche Farben. Tabellen zoomen mit Strg + Mausrad.",
                 "Sidebar → Account → <b>Settings</b> → Show Experiment tables", "wn_reading.svg"),
                ("h", "Hilfe"),
                ("feature", "Hilfe in drei Sprachen",
                 "Show Experiment, Backlog, Report, All Experiments, Create Experiment, Manage Yarn und Manage Jets "
                 "haben jetzt eine eigene Hilfe auf Englisch, Deutsch und Spanisch: Schritt-für-Schritt-Antworten "
                 "auf \"Wie mache ich…?\", eine Skizze des Bildschirms und die Regeln. Die Flaggen wechseln die Sprache.",
                 "Runder <b>?</b>-Knopf in diesen Screens", "wn_help.svg"),
                ("feature", "Hilfe-Suche - \"Wo finde ich…?\"",
                 "Die Frage in eigenen Worten eintippen und die passende Hilfe-Seite bekommen - auf Englisch, "
                 "Deutsch oder Spanisch. <b>Take me there</b> öffnet den Screen.",
                 "Sidebar → <b>Help (F1)</b> oder Taste F1", "wn_help_search.svg"),
                ("feature", "Suche in Fresh off the Spool",
                 "Du weisst, dass es eine Funktion gibt, aber nicht seit wann? Ein Wort ins Suchfeld über der "
                 "Versionsliste tippen - gesucht wird in allen Versionen gleichzeitig, auf Englisch, Deutsch und "
                 "Spanisch. Versionen mit Treffern zeigen die Anzahl; ein Klick springt dorthin. Jede Version ist "
                 "jetzt in Reiter nach Bereich aufgeteilt, z.&nbsp;B. <i>Show Experiment (8)</i>.",
                 "Sidebar → Account → <b>Fresh off the Spool</b> → Suchfeld", "wn_whats_new_search.svg"),
                ("feature", "Fresh off the Spool als PDF",
                 "Die Neuheiten einer Version als PDF speichern - zum Ausdrucken oder um sie Kollegen zu schicken. "
                 "Jedes Thema bleibt zusammen auf einer Seite.",
                 "Sidebar → Account → <b>Fresh off the Spool</b> → <b>PDF</b>", "wn_whats_new_pdf.svg"),
                ("h", "Backlog und All Experiments"),
                ("feature", "Mehrere Karten auf einmal verschieben",
                 "<b>Strg</b> gedrückt halten und die Karten anklicken (oder <b>Umschalt+Klick</b> für einen ganzen "
                 "Bereich), dann eine davon ziehen - alle markierten Karten wandern mit, z. B. von <i>To Be "
                 "Cleaned</i> nach <i>Archived</i>. TrippleT fragt einmal nach und sagt, falls eine Karte nicht "
                 "verschoben werden durfte.",
                 "Backlog → Karten mit <b>Strg+Klick</b> markieren → ziehen", "wn_backlog_multi_move.svg"),
                ("feature", "Backlog auf breiten Bildschirmen",
                 "Auf grossen Monitoren stehen alle vier Spalten nebeneinander und nutzen die volle Höhe.",
                 "Backlog", "wn_wide_backlog.svg"),
                ("feature", "Papierkorb",
                 "Eine gelöschte Versuchsserie lässt sich 90 Tage lang wiederherstellen. Löschen darf, wer die Serie "
                 "im Backlog verschieben darf (in To Be Cleaned nur Superuser).",
                 "Sidebar → Superuser → <b>Recycle Bin</b>", "wn_recycle_bin.svg"),
                ("feature", "Im Papierkorb nachschauen",
                 "Unsicher, was in einer gelöschten Serie steckt? Doppelklick darauf: Sie öffnet sich schreibgeschützt "
                 "in Show Experiment. Im gelben Balken wählst du <b>Restore for good</b>, <b>Back to Recycle Bin</b> "
                 "oder <b>Delete permanently</b>. Tab schliessen legt sie zurück - mit dem ursprünglichen Löschdatum.",
                 "Sidebar → Superuser → <b>Recycle Bin</b> → Doppelklick auf eine Serie", "wn_recycle_preview.svg"),
                ("feature", "All Experiments nutzt das ganze Fenster",
                 "Die Liste füllt die volle Breite und Höhe des Fensters - die letzten Spalten sind ohne seitliches "
                 "Scrollen sichtbar - und wird auf grossen Bildschirmen grösser dargestellt.",
                 "All Experiments", "wn_all_experiments.svg"),
                ("h", "Garne"),
                ("feature", "Die Farbe eines Garns sehen",
                 "Ein kleines Kästchen vor dem Garnnamen zeigt seine Farbe - schwarz, weiss, beige, grau, natur. "
                 "Mit der Maus darüber steht die Farbe auch als Text. Man kann auch nach Farbe suchen, z. B. "
                 "<i>black</i>. Die Farbe kommt aus dem Feld <i>Colour</i> des Garns (<b>Manage Yarn</b>).",
                 "Dialog Yarns…, Create Experiment, Yarn Stock, Manage Yarn, Reassign Yarn, Show Experiment "
                 "(Zeile Ply)", "wn_yarn_colour.svg"),
                ("h", "Yarn Stock"),
                ("feature", "Lagerstatus pro Garn",
                 "Die Ampel zeigt jetzt jedes Garn als Ganzes: alle Batches am Lager zusammen gegen den "
                 "Mindestbestand. Aufgebrauchte Batches verschwinden aus der Übersicht, Meldungen kommen einmal pro "
                 "Garn. Den Mindestbestand ändern dürfen nur Superuser.",
                 "Yarn Stock → Übersicht", "wn_stock_status.svg"),
                ("feature", "Neue Spulen - direkt zu den neuen Spulen und in die Etiketten-Liste",
                 "<b>New spool(s)</b> beginnt mit leerer Auswahl und springt danach direkt zu den neuen Spulen. "
                 "Diese kommen automatisch in die Label queue (Häkchen im Dialog).",
                 "Yarn Stock → <b>New spool(s)</b>", "wn_new_spools.svg"),
                ("feature", "Inventur - Platz für Platz",
                 "Ein Superuser startet eine Inventur-Runde (und kann einzelne Plätze auslassen). Jeder Lagerplatz "
                 "ist eine Kachel: grau = offen, grün = alles stimmt, orange = Abweichungen. Draufklicken und die "
                 "Spulen scannen (kein Etikett? in der Liste doppelklicken). <b>Results</b> zeigt, was wo gefunden wurde, als Excel exportierbar. Spulen an einem "
                 "anderen Platz werden sofort umgelagert, fehlende erst beim Abschluss ausgebucht - nach Rückfrage.",
                 "Yarn Stock → Rack lookup → <b>Stock take…</b>", "wn_stock_take.svg"),
                ("feature", "Spulen-Verlauf",
                 "Jede Änderung an einer Spule wird festgehalten: angelegt, geändert, umgelagert, ausgebucht, "
                 "Inventur. Ohne Auswahl sieht man die ganze Batch, auch aufgebrauchte Spulen.",
                 "Yarn Stock → <b>History…</b>", "wn_spool_history.svg"),
                ("feature", "Etiketten scannen, Änderungen nicht verlieren",
                 "In <i>Go to spool #</i> lässt sich das Spulenetikett scannen statt die Nummer zu tippen. Und Yarn "
                 "Stock fragt jetzt nach, bevor ungespeicherte Spulen-Änderungen verloren gehen. Hilfe in drei "
                 "Sprachen: runder Knopf oben rechts.",
                 "Yarn Stock → <b>Go to spool #</b>", None),
                ("h", "Allgemein"),
                ("feature", "Fresh off the Spool: Neues in TrippleT",
                 "Alle Neuerungen jeder Version an einem Ort: ein Reiter pro Bereich, durchsuchbar und als PDF. "
                 "Öffnet sich nach einer neuen Version einmal von selbst - und jederzeit in der Sidebar.",
                 "Sidebar → Account → <b>Fresh off the Spool</b>", "fresh_off_the_spool.png"),
                ("feature", "Zuletzt geöffnete Serien",
                 "Die zuletzt geöffneten Serien sind einen Klick entfernt: <b>Recent</b> in der Sidebar (unten, über Account). "
                 "Klick öffnet sie, <b>Strg+Klick</b> in einem neuen Tab. Die Liste folgt dir auf jeden PC.",
                 "Sidebar → <b>Recent</b>", None),
                ("feature", "Athena antwortet in deiner Sprache",
                 "Athena und der Lab Assistant antworten jetzt in der Sprache, in der du fragst - Englisch, Deutsch, "
                 "Spanisch, … Ohne Frage (z.&nbsp;B. die automatische Analyse) kommt die Antwort auf Englisch.",
                 "Show Experiment → Athena, Lab Assistant", None),
                ("feature", "Fehlermeldungen, die weiterhelfen",
                 "Geht etwas schief, sagt TrippleT jetzt in Alltagssprache, was nicht geklappt hat, warum und was du "
                 "tun kannst - z.&nbsp;B. \"Die Datei ist in einem anderen Programm offen - schliessen (z.&nbsp;B. in "
                 "Excel) und nochmals versuchen.\" Der technische Text steht unter <b>Show Details</b>, zum "
                 "Weiterleiten an den Admin.",
                 "Ganzes Programm", None),
                ("feature", "Alle Texte auf Englisch",
                 "Meldungen, Knöpfe, Menüs und Statustexte, die noch deutsch waren, sind jetzt überall englisch - "
                 "z.&nbsp;B. heisst das Rechtsklick-Menü im Backlog <b>Reassign yarn…</b>. Laborbegriffe wie Kurzhocker "
                 "oder Langwelle bleiben, wie sie sind.",
                 "Ganzes Programm", None),
            ],
            # ═══════════════════════════════ ES ═══════════════════════════════
            "es": [
                ("h", "Show Experiment"),
                ("feature", "Los hilos de la serie en una tabla",
                 "<b>Yarns…</b> muestra todos los plies de la serie con su hilo y todos los ensayos. Un clic en el "
                 "hilo lo cambia para todo el ply; para encontrarlo escribe parte del nombre, p.&nbsp;ej. "
                 "<i>167 dty</i>. Un clic en una celda activa o quita el ply en ese ensayo; escribe 1-9 para el "
                 "número de cabos. <b>+ Add ply</b> añade un ply a todos los ensayos. Las celdas cambiadas están en "
                 "amarillo y nada se guarda antes de <b>Apply</b>.",
                 "Show Experiment → Machine Data → <b>Yarns…</b> (o clic derecho en la fila Ply)",
                 "wn_series_yarns.svg"),
                ("feature", "¿Dónde están mis bobinas?",
                 "Una pequeña bobina detrás de cada ply en la línea de material lo indica de un vistazo: bobina verde "
                 "= hay hilo en almacén, tubo tachado = no hay nada en almacén. Un clic en el hilo o en la bobina verde muestra "
                 "todas las bobinas en almacén por ubicación, con lote, peso y color del tubo. Las bobinas asignadas "
                 "a esta serie aparecen en negrita. <b>Open in Yarn Stock</b> lleva directamente al hilo.",
                 "Show Experiment → línea de material → hilo o símbolo de bobina", "wn_spool_locations.svg"),
                ("feature", "Notas en los valores",
                 "Anota por qué un valor es así, justo donde está: clic derecho en un valor → <b>Add note…</b>, "
                 "p.&nbsp;ej. <i>La bobina tenía nudos, medido de nuevo</i>. Un pequeño triángulo violeta marca "
                 "la celda; al señalarla se ve la nota con nombre y fecha. Clic derecho en un número de ensayo "
                 "para una nota sobre todo el ensayo. La pestaña <b>Notes</b> lista todas las notas de la serie; "
                 "doble clic salta al valor. Todos pueden escribir notas. En el <b>Smart Chart</b>, el botón "
                 "<b>Notes</b> las muestra como borde violeta con la nota en la descripción emergente. En el PDF "
                 "solo aparecen si al exportar marcas <i>Include notes on values</i>.",
                 "Show Experiment → clic derecho en un valor → <b>Add note…</b>", "wn_cell_notes.svg"),
                ("feature", "Muestras de referencia",
                 "Añade la bobina original de un cliente como comparación. Aparece como columna <i>Ref</i> "
                 "resaltada y como línea horizontal en el informe, y nunca cuenta como ensayo.",
                 "Show Experiment → Machine Data → <b>+ Ref</b>", "wn_reference.svg"),
                ("feature", "Copiar ensayos - con cambios",
                 "Elige qué ensayos, cuántas veces y en qué orden, y cambia valores (p.&nbsp;ej. presión de aire, "
                 "tobera, OF Core/Effect) antes de copiar. Los comentarios y las tensiones antes/después del jet no "
                 "se copian: las copias empiezan con ellos vacíos.",
                 "Show Experiment → Machine Data → <b>Copy trials</b>", "wn_copy_trials.svg"),
                ("feature", "D/Y Ratio (T2/T1)",
                 "Se calcula automáticamente a partir de T1 y T2 y se muestra justo debajo de T2 Tension en "
                 "máquinas DTY.",
                 "Show Experiment → Machine Data", "wn_dy_ratio.svg"),
                ("feature", "Introducir datos más rápido, como en Excel",
                 "Escribe un valor y pulsa <b>Enter</b>: pasas a la celda de abajo, listo para el siguiente valor "
                 "(<b>Mayús+Enter</b> sube). Haz clic en una celda (o selecciona varias) y pulsa <b>Supr</b> para "
                 "vaciarlas, sin doble clic. Guarda con <b>Save</b> o <b>Ctrl+S</b>; en lugar de un mensaje "
                 "\"Saved\" que cerrar, el amarillo desaparece y en el centro aparece un momento una marca verde; "
                 "puedes seguir escribiendo enseguida.",
                 "Show Experiment → cualquier tabla", None),
                ("feature", "Deshacer con Ctrl+Z",
                 "¿Valor equivocado, pegado en el sitio incorrecto o borrado de más? <b>Ctrl+Z</b> lo deshace paso a "
                 "paso y <b>Ctrl+Y</b> lo rehace, mientras no hayas guardado.",
                 "Show Experiment → cualquier tabla", None),
                ("feature", "De vuelta en tu pestaña",
                 "Una serie se abre en la pestaña que usaste la última vez con ella, p.&nbsp;ej. <i>Statimat M</i> "
                 "en lugar de siempre <i>Machine Data</i>.",
                 "Show Experiment", None),
                ("feature", "Ocultar filas que no necesitas",
                 "Clic derecho en el nombre de un parámetro → <b>Hide row</b>. Una línea azul indica dónde faltan "
                 "filas; un clic en ella o <b>n rows hidden</b> las vuelve a mostrar. Se recuerda por máquina.",
                 "Show Experiment → Machine Data → clic derecho en el nombre del parámetro", "wn_hide_rows.svg"),
                ("feature", "Ver lo que aún no está guardado",
                 "Las celdas cambiadas quedan en amarillo hasta que guardas (<b>Save</b> o <b>Ctrl+S</b>). El botón "
                 "muestra cuántas, p.&nbsp;ej. "
                 "<b>Save (3)</b>, y la pestaña recibe un punto. Al cerrar una pestaña o el programa con cambios sin "
                 "guardar, ahora se pregunta antes; hasta ahora se perdían sin aviso.",
                 "Show Experiment", "wn_unsaved.svg"),
                ("feature", "Control de errores al guardar",
                 "Los ajustes de máquina muy fuera de lo habitual para esta máquina (p.&nbsp;ej. 35 en vez de "
                 "3.5 bar) se muestran antes de guardar. Puedes volver a corregir o guardar igualmente.",
                 "Show Experiment → <b>Save</b>", "wn_unusual.svg"),
                ("feature", "Historial de cambios (superusuarios)",
                 "Ver quién cambió un valor, cuándo y qué había antes - para un valor o toda la serie.",
                 "Show Experiment → clic derecho en un valor → <b>Change history…</b>", "wn_history.svg"),
                ("h", "Smart Chart"),
                ("feature", "Nuevo Smart Chart: encontrar ensayos por sus propiedades",
                 "Elige ensayos de <b>todas</b> las series por hilo, geometría del jet, ajustes de máquina y resultados de laboratorio, "
                 "p.&nbsp;ej. todos los ensayos de poliéster con 70–80 dtex de título final y 30–40 filamentos. "
                 "<b>+ Add filter</b> muestra cómo se reparten los valores y cuántos ensayos deja cada filtro; los filtros "
                 "numéricos pueden quedarse solo con enteros, cada 0.5 o los valores marcados. Después "
                 "representa cualquier campo frente a otro (puntos, rectas de tendencia con R², líneas de media, "
                 "barras, box plots, violines, histogramas o mapa de densidad), colorea por jet, máquina o un número "
                 "(escala de color), elige paleta o tus propios colores, un gráfico pequeño por máquina. Clic en un "
                 "punto encuentra el ensayo en la lista, doble clic lo abre. Guarda "
                 "el gráfico como vista (también compartida), exporta a PDF o Excel.",
                 "Barra lateral → <b>Smart Chart</b>", "wn_smart_chart.svg"),
                ("feature", '¿Es justa esta comparación?',
                 'Una barra de color sobre el gráfico avisa cuando los grupos que comparas también se diferencian en otras cosas que cambian el resultado, p.&nbsp;ej. el jet A se probó sobre todo con PES a 3.5 bar y el jet B con PA a 2 bar. Verde, amarillo o rojo, con el motivo en una frase. <b>Details</b> muestra cada condición, <b>Make it fairer</b> deja solo lo que todos los grupos tienen en común. También avisa de grupos muy pequeños, grupos de una sola serie y grupos en rangos de X distintos.',
                 'Smart Chart → barra sobre el gráfico', "wn_fairness.svg"),
                ("feature", 'Dashboard: crea tu propia página, como en Power BI',
                 'Cambia Smart Chart a <b>Dashboard</b>: una página con varios visuales. Arrastra campos desde <b>Fields</b> (todas las tablas, de Statimat e Itemat a DTYoMat, jet e hilo) a los huecos de un visual. Visuales nuevos: <b>Matrix</b> (p.&nbsp;ej. FP/m por jet y presión, coloreado; las celdas vacías muestran dónde faltan ensayos), <b>Card</b> (un número) y <b>Table</b>. Haz clic en una barra, caja o celda y todos los demás visuales se filtran. Los <b>slicers</b> eligen valores para toda la página: lista, desplegable, botones o rango. Coloca y redimensiona los visuales libremente, usa varias páginas (pestañas abajo) y filtros solo para una página o un visual. Nuevo: <b>campos calculados</b> con tu propia fórmula, <b>objetivos</b> (verde/rojo, líneas de objetivo), <b>profundizar</b> máquina → jet y <b>seleccionar puntos</b> para filtrar la página. Además: <b>plantillas</b> (Jet comparison, Yarn overview, Machine check, Lab overview), <b>PDF</b> de una o todas las páginas, <b>Excel</b> por visual o página, notas en los valores, deshacer con <b>Ctrl+Z</b> y <b>alinear</b> varios visuales a la vez (Ctrl+clic, luego alinear, mismo tamaño o distribuir).',
                 'Smart Chart → <b>Dashboard</b>', "wn_dashboard.svg"),
                ("feature", 'Estadísticas del laboratorio en el dashboard',
                 'Cuenta <b>experimentos, series o ensayos</b> por mes, grupo de producto, tipo de pedido, proyecto, responsable o máquina de laboratorio (<i>Tested on</i>). El nuevo visual <b>Columns</b> los muestra apilados, lado a lado o al 100 %; meses y años van en orden y los meses vacíos aparecen como 0. Empieza con <b>New</b> → <b>Lab statistics</b>. Los números son los mismos que en la página Statistics, ahora para todos y con slicers.',
                 'Smart Chart → <b>Dashboard</b> → <b>New</b> → <b>Lab statistics</b>', "wn_dashboard_stats.svg"),
                ("feature", 'Dashboards: verlos y compartirlos',
                 'La nueva página <b>Dashboards</b> muestra tus dashboards y los que tus compañeros compartieron contigo. Aquí solo se mira: funcionan los slicers, el clic en barras para filtrar, el drill-down, las pestañas y el <b>PDF</b>; nada se cambia por error. Para compartir tu dashboard, ábrelo en Smart Chart y haz clic en <b>Share…</b>: con todos, con personas o con grupos (read, write, admin, superuser), cada uno para <b>ver</b> o para <b>editar</b>. Solo tú puedes compartirlo o borrarlo.',
                 'Sidebar → Tools → <b>Dashboards</b> · Smart Chart → <b>Share…</b>', "wn_dashboards.svg"),
                ("feature", 'Los superusuarios deciden quién usa qué herramienta',
                 'En <b>Manage User → Access…</b> un superusuario activa o desactiva cada herramienta y pantalla, para un grupo (read, write, admin) o para una persona, p.&nbsp;ej. Smart Chart para un compañero o sin Backlog para un grupo. El ajuste de una persona tiene prioridad sobre el del grupo; sin ajustes todo queda como antes. Las herramientas bloqueadas desaparecen del menú lateral desde el siguiente inicio de sesión.',
                 'Sidebar → Superuser → Manage User → <b>Access…</b>', "wn_feature_access.svg"),
                ("h", "Settings"),
                ("feature", 'Elige tu pantalla de inicio',
                 'Decide qué pantalla se abre tras iniciar sesión: Backlog (como antes), All Experiments, Dashboards, Yarn Stock u otra herramienta que uses. Si un superusuario te desactiva esa herramienta, se abre Backlog.',
                 'Sidebar → Account → <b>Settings</b> → <b>Start screen</b>', "wn_start_screen.svg"),
                ("feature", "Tamaño del texto para todo el programa",
                 "Normal, Large, Extra large o Huge - botones, menús, tablas y diálogos crecen. Se aplica tras "
                 "reiniciar. Aquí también se ajustan el mensaje de bienvenida y el color de acento.",
                 "Barra lateral → Account → <b>Settings</b>", "wn_text_size.svg"),
                ("feature", "Tablas más fáciles de leer",
                 "Alto contraste, cruz de lectura para fila y columna, barra de lectura con el valor en letra "
                 "grande, símbolos de aviso y colores aptos para daltónicos. Zoom de tablas con Ctrl + rueda.",
                 "Barra lateral → Account → <b>Settings</b> → Show Experiment tables", "wn_reading.svg"),
                ("h", "Ayuda"),
                ("feature", "Ayuda en tres idiomas",
                 "Show Experiment, Backlog, Report, All Experiments, Create Experiment, Manage Yarn y Manage Jets "
                 "tienen ahora su propia ayuda en inglés, alemán y español: respuestas paso a paso a \"¿Cómo hago…?\", "
                 "un esquema de la pantalla y las reglas. Las banderas cambian el idioma.",
                 "Botón redondo <b>?</b> en estas pantallas", "wn_help.svg"),
                ("feature", "Búsqueda en la ayuda - \"¿Dónde encuentro…?\"",
                 "Escribe tu pregunta con tus propias palabras y obtén la página de ayuda adecuada, en inglés, alemán "
                 "o español. <b>Take me there</b> abre la pantalla.",
                 "Barra lateral → <b>Help (F1)</b> o la tecla F1", "wn_help_search.svg"),
                ("feature", "Buscar en Fresh off the Spool",
                 "¿Sabes que existe una función pero no desde cuándo? Escribe una palabra en el campo de búsqueda "
                 "encima de la lista de versiones: se busca en todas las versiones a la vez, en inglés, alemán y "
                 "español. Las versiones con resultados muestran cuántos; un clic salta a ellos. Cada versión se "
                 "divide ahora en pestañas por área, p.&nbsp;ej. <i>Show Experiment (8)</i>.",
                 "Barra lateral → Account → <b>Fresh off the Spool</b> → campo de búsqueda", "wn_whats_new_search.svg"),
                ("feature", "Fresh off the Spool en PDF",
                 "Guarda las novedades de una versión como PDF, para imprimirlas o enviarlas a compañeros. Cada "
                 "tema queda junto en una sola página.",
                 "Barra lateral → Account → <b>Fresh off the Spool</b> → <b>PDF</b>", "wn_whats_new_pdf.svg"),
                ("h", "Backlog y All Experiments"),
                ("feature", "Mover varias tarjetas a la vez",
                 "Mantén <b>Ctrl</b> y haz clic en las tarjetas (o <b>Mayús+clic</b> para un rango), luego arrastra "
                 "una de ellas: todas las marcadas se mueven juntas, p. ej. de <i>To Be Cleaned</i> a "
                 "<i>Archived</i>. TrippleT pregunta una vez y avisa si alguna tarjeta no se podía mover.",
                 "Backlog → <b>Ctrl+clic</b> en las tarjetas → arrastrar", "wn_backlog_multi_move.svg"),
                ("feature", "Backlog en pantallas anchas",
                 "En monitores grandes las cuatro columnas se muestran una al lado de otra con toda la altura.",
                 "Backlog", "wn_wide_backlog.svg"),
                ("feature", "Papelera",
                 "Una serie de ensayos borrada se puede recuperar durante 90 días. Puede borrar quien puede mover la "
                 "serie en el Backlog (en To Be Cleaned solo superusuarios).",
                 "Barra lateral → Superuser → <b>Recycle Bin</b>", "wn_recycle_bin.svg"),
                ("feature", "Mirar dentro de la papelera",
                 "¿No sabes qué contiene una serie borrada? Haz doble clic: se abre en Show Experiment solo para "
                 "lectura. En la barra amarilla eliges <b>Restore for good</b>, <b>Back to Recycle Bin</b> o "
                 "<b>Delete permanently</b>. Cerrar la pestaña la devuelve a la papelera, con su fecha de borrado "
                 "original.",
                 "Barra lateral → Superuser → <b>Recycle Bin</b> → doble clic en una serie", "wn_recycle_preview.svg"),
                ("feature", "All Experiments usa toda la ventana",
                 "La lista ocupa todo el ancho y alto de la ventana - las últimas columnas se ven sin desplazarse "
                 "hacia los lados - y se muestra más grande en pantallas grandes.",
                 "All Experiments", "wn_all_experiments.svg"),
                ("h", "Hilos"),
                ("feature", "Ver el color de un hilo",
                 "Un pequeño cuadrado delante del nombre del hilo muestra su color - negro, blanco, beige, gris, "
                 "natural. Al pasar el ratón por encima se lee el color. También se puede buscar por color, p. ej. "
                 "<i>black</i>. El color viene del campo <i>Colour</i> del hilo (<b>Manage Yarn</b>).",
                 "Diálogo Yarns…, Create Experiment, Yarn Stock, Manage Yarn, Reassign Yarn, Show Experiment "
                 "(fila Ply)", "wn_yarn_colour.svg"),
                ("h", "Yarn Stock"),
                ("feature", "Estado del stock por hilo",
                 "El semáforo muestra ahora cada hilo en conjunto: todos sus lotes en stock frente al stock mínimo. "
                 "Los lotes agotados desaparecen de la vista general y los avisos llegan una vez por hilo. Solo los "
                 "superusuarios pueden cambiar el stock mínimo.",
                 "Yarn Stock → vista general", "wn_stock_status.svg"),
                ("feature", "Bobinas nuevas - directamente a las nuevas y a la cola de etiquetas",
                 "<b>New spool(s)</b> empieza sin selección y después salta directamente a las bobinas nuevas. "
                 "Estas pasan automáticamente a la cola de etiquetas (casilla en el diálogo).",
                 "Yarn Stock → <b>New spool(s)</b>", "wn_new_spools.svg"),
                ("feature", "Inventario - ubicación por ubicación",
                 "Un superusuario inicia una ronda de inventario (y puede excluir ubicaciones). Cada ubicación es una "
                 "casilla: gris = pendiente, verde = todo correcto, naranja = diferencias. Haz clic en una y escanea "
                 "sus bobinas (¿sin etiqueta? doble clic en la lista). <b>Results</b> muestra qué se encontró dónde, exportable a Excel. Las bobinas en otro "
                 "lugar se reubican al momento; las que faltan solo se dan de baja al terminar, tras preguntar.",
                 "Yarn Stock → Rack lookup → <b>Stock take…</b>", "wn_stock_take.svg"),
                ("feature", "Historial de bobinas",
                 "Se registra cada cambio de una bobina: creada, cambiada, reubicada, dada de baja, inventario. Sin "
                 "selección se ve todo el lote, incluidas las bobinas agotadas.",
                 "Yarn Stock → <b>History…</b>", "wn_spool_history.svg"),
                ("feature", "Escanear etiquetas, no perder cambios",
                 "En <i>Go to spool #</i> puedes escanear la etiqueta en vez de escribir el número. Y Yarn Stock "
                 "pregunta ahora antes de perder cambios no guardados. Ayuda en tres idiomas: botón redondo arriba "
                 "a la derecha.",
                 "Yarn Stock → <b>Go to spool #</b>", None),
                ("h", "General"),
                ("feature", "Fresh off the Spool: novedades de TrippleT",
                 "Todas las novedades de cada versión en un solo lugar: una pestaña por área, con búsqueda y en PDF. "
                 "Se abre sola una vez tras cada nueva versión, y en cualquier momento desde la barra lateral.",
                 "Barra lateral → Account → <b>Fresh off the Spool</b>", "fresh_off_the_spool.png"),
                ("feature", "Series recientes",
                 "Las últimas series que abriste están a un clic: <b>Recent</b> en la barra lateral (abajo, encima de Account). "
                 "Un clic la abre, <b>Ctrl+clic</b> en una pestaña nueva. La lista te acompaña en cualquier PC.",
                 "Barra lateral → <b>Recent</b>", None),
                ("feature", "Athena responde en tu idioma",
                 "Athena y el Lab Assistant responden ahora en el idioma en que preguntas: inglés, alemán, español… "
                 "Sin pregunta (p.&nbsp;ej. el análisis automático) la respuesta es en inglés.",
                 "Show Experiment → Athena, Lab Assistant", None),
                ("feature", "Mensajes de error que ayudan",
                 "Cuando algo falla, TrippleT dice ahora con palabras sencillas qué no funcionó, por qué y qué puedes "
                 "hacer - p.&nbsp;ej. \"El archivo está abierto en otro programa: ciérralo (p.&nbsp;ej. en Excel) y "
                 "vuelve a intentarlo.\" El texto técnico está en <b>Show Details</b>, para enviarlo al administrador.",
                 "Todo el programa", None),
                ("feature", "Todos los textos en inglés",
                 "Los mensajes, botones, menús y textos de estado que aún estaban en alemán ahora están en inglés en "
                 "todas partes - p.&nbsp;ej. el menú contextual del Backlog dice <b>Reassign yarn…</b>. Los términos de "
                 "laboratorio como Kurzhocker o Langwelle se mantienen.",
                 "Todo el programa", None),
            ],
        },
    },
]

# "Fresh off the Spool" = the name of the release notes magazine (2026-10-16,
# before: "What's new"); English in every language like the button names.
WINDOW_TITLE = {"en": "Fresh off the Spool", "de": "Fresh off the Spool", "es": "Fresh off the Spool"}
SUBTITLE = {"en": "What's new in TrippleT", "de": "Neues in TrippleT", "es": "Novedades de TrippleT"}
VERSIONS_TITLE = {"en": "Versions", "de": "Versionen", "es": "Versiones"}
NEW_BADGE = {"en": "NEW", "de": "NEU", "es": "NUEVO"}
WHERE_LABEL = {"en": "Where:", "de": "Wo:", "es": "Dónde:"}
VERSION_LABEL = {"en": "Version", "de": "Version", "es": "Versión"}
CURRENT_LABEL = {"en": "in progress", "de": "in Arbeit", "es": "en curso"}
CLOSE = {"en": "Close", "de": "Schliessen", "es": "Cerrar"}
SEARCH_PLACEHOLDER = {"en": "Search all versions…", "de": "Alle Versionen durchsuchen…",
                      "es": "Buscar en todas las versiones…"}
SEARCH_RESULTS = {"en": "{n} result(s) for \"{q}\"", "de": "{n} Treffer für \"{q}\"",
                  "es": "{n} resultado(s) para \"{q}\""}
SEARCH_NONE = {"en": "Nothing found for \"{q}\". Try another word - English, German and Spanish all work.",
               "de": "Nichts gefunden für \"{q}\". Versuche ein anderes Wort - Englisch, Deutsch und Spanisch gehen.",
               "es": "No se encontró nada para \"{q}\". Prueba otra palabra - sirven inglés, alemán y español."}
HITS_LABEL = {"en": "hits", "de": "Treffer", "es": "resultados"}
PDF_TOOLTIP = {"en": "Save the shown version as PDF (e.g. to print or send it)",
               "de": "Die angezeigte Version als PDF speichern (z. B. zum Drucken oder Verschicken)",
               "es": "Guardar la versión mostrada como PDF (p. ej. para imprimirla o enviarla)"}
