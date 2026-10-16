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
                 "them - no double-click needed. Save with <b>Save</b> or <b>Ctrl+S</b>; there is no \"Saved\" "
                 "message any more - the yellow simply disappears.",
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
                ("h", "Settings"),
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
                 "eine \"Saved\"-Meldung gibt es nicht mehr - das Gelb verschwindet einfach.",
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
                ("h", "Settings"),
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
                 "vaciarlas, sin doble clic. Guarda con <b>Save</b> o <b>Ctrl+S</b>; ya no aparece el mensaje "
                 "\"Saved\": el amarillo simplemente desaparece.",
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
                ("h", "Settings"),
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
