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
                 "OF Core/Effect) before copying. Tensions before/after the jet are no longer copied.",
                 "Show Experiment → Machine Data → <b>Copy trials</b>", "wn_copy_trials.svg"),
                ("feature", "D/Y Ratio (T2/T1)",
                 "Calculated automatically from T1 and T2 and shown right below T2 Tension on DTY machines.",
                 "Show Experiment → Machine Data", "wn_dy_ratio.svg"),
                ("feature", "Hide rows you don't need",
                 "Right-click a parameter name → <b>Hide row</b>. A blue line shows where rows are hidden; click "
                 "it, or use <b>n rows hidden</b>, to show them again. Remembered per machine.",
                 "Show Experiment → Machine Data → right-click a parameter name", "wn_hide_rows.svg"),
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
                 "Spanish. <b>Take me there</b> opens the screen. Users with AI access can also <b>Ask AI</b>.",
                 "Sidebar → <b>Help (F1)</b> or the F1 key", "wn_help_search.svg"),
                ("h", "Backlog and All Experiments"),
                ("feature", "Backlog on wide screens",
                 "On big monitors all four columns stand side by side and use the full height.",
                 "Backlog", "wn_wide_backlog.svg"),
                ("feature", "Recycle Bin",
                 "A deleted trial series can be restored for 90 days. Whoever may move a series in the Backlog may "
                 "delete it (in To Be Cleaned: superusers only).",
                 "Sidebar → Superuser → <b>Recycle Bin</b>", "wn_recycle_bin.svg"),
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
                ("feature", "Stock take",
                 "Check a rack spool by spool: scan each label. Spools in another place are moved right away, "
                 "missing ones are only booked out when you finish - after asking.",
                 "Yarn Stock → Rack lookup → <b>Start stock take…</b>", "wn_stock_take.svg"),
                ("feature", "Spool history",
                 "Every change of a spool is recorded: created, changed, moved, booked out, stock take. Without a "
                 "selection you see the whole batch, including used-up spools.",
                 "Yarn Stock → <b>History…</b>", "wn_spool_history.svg"),
                ("feature", "Scan labels, keep changes",
                 "In <i>Go to spool #</i> you can scan the spool label instead of typing the number. And Yarn Stock "
                 "now asks before unsaved spool changes are lost. Help in three languages: round button top right.",
                 "Yarn Stock → <b>Go to spool #</b>", None),
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
                 "Luftdruck, Düse, OF Core/Effect) vor dem Kopieren ändern. Fadenspannungen vor/nach Jet werden "
                 "nicht mehr mitkopiert.",
                 "Show Experiment → Machine Data → <b>Copy trials</b>", "wn_copy_trials.svg"),
                ("feature", "D/Y Ratio (T2/T1)",
                 "Wird bei DTY-Maschinen automatisch aus T1 und T2 berechnet und direkt unter T2 Tension angezeigt.",
                 "Show Experiment → Machine Data", "wn_dy_ratio.svg"),
                ("feature", "Nicht benötigte Zeilen ausblenden",
                 "Rechtsklick auf einen Parameternamen → <b>Hide row</b>. Eine blaue Linie zeigt, wo Zeilen fehlen; "
                 "ein Klick darauf oder <b>n rows hidden</b> holt sie zurück. Gemerkt pro Maschine.",
                 "Show Experiment → Machine Data → Rechtsklick auf Parameternamen", "wn_hide_rows.svg"),
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
                 "Deutsch oder Spanisch. <b>Take me there</b> öffnet den Screen. Benutzer mit KI-Zugang können "
                 "zusätzlich <b>Ask AI</b> nutzen.",
                 "Sidebar → <b>Help (F1)</b> oder Taste F1", "wn_help_search.svg"),
                ("h", "Backlog und All Experiments"),
                ("feature", "Backlog auf breiten Bildschirmen",
                 "Auf grossen Monitoren stehen alle vier Spalten nebeneinander und nutzen die volle Höhe.",
                 "Backlog", "wn_wide_backlog.svg"),
                ("feature", "Papierkorb",
                 "Eine gelöschte Versuchsserie lässt sich 90 Tage lang wiederherstellen. Löschen darf, wer die Serie "
                 "im Backlog verschieben darf (in To Be Cleaned nur Superuser).",
                 "Sidebar → Superuser → <b>Recycle Bin</b>", "wn_recycle_bin.svg"),
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
                ("feature", "Inventur",
                 "Ein Regal Spule für Spule prüfen: jedes Etikett scannen. Spulen an einem anderen Platz werden "
                 "sofort umgelagert, fehlende erst beim Abschluss ausgebucht - nach Rückfrage.",
                 "Yarn Stock → Rack lookup → <b>Start stock take…</b>", "wn_stock_take.svg"),
                ("feature", "Spulen-Verlauf",
                 "Jede Änderung an einer Spule wird festgehalten: angelegt, geändert, umgelagert, ausgebucht, "
                 "Inventur. Ohne Auswahl sieht man die ganze Batch, auch aufgebrauchte Spulen.",
                 "Yarn Stock → <b>History…</b>", "wn_spool_history.svg"),
                ("feature", "Etiketten scannen, Änderungen nicht verlieren",
                 "In <i>Go to spool #</i> lässt sich das Spulenetikett scannen statt die Nummer zu tippen. Und Yarn "
                 "Stock fragt jetzt nach, bevor ungespeicherte Spulen-Änderungen verloren gehen. Hilfe in drei "
                 "Sprachen: runder Knopf oben rechts.",
                 "Yarn Stock → <b>Go to spool #</b>", None),
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
                 "tobera, OF Core/Effect) antes de copiar. Las tensiones antes/después del jet ya no se copian.",
                 "Show Experiment → Machine Data → <b>Copy trials</b>", "wn_copy_trials.svg"),
                ("feature", "D/Y Ratio (T2/T1)",
                 "Se calcula automáticamente a partir de T1 y T2 y se muestra justo debajo de T2 Tension en "
                 "máquinas DTY.",
                 "Show Experiment → Machine Data", "wn_dy_ratio.svg"),
                ("feature", "Ocultar filas que no necesitas",
                 "Clic derecho en el nombre de un parámetro → <b>Hide row</b>. Una línea azul indica dónde faltan "
                 "filas; un clic en ella o <b>n rows hidden</b> las vuelve a mostrar. Se recuerda por máquina.",
                 "Show Experiment → Machine Data → clic derecho en el nombre del parámetro", "wn_hide_rows.svg"),
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
                 "o español. <b>Take me there</b> abre la pantalla. Los usuarios con acceso a IA también pueden usar "
                 "<b>Ask AI</b>.",
                 "Barra lateral → <b>Help (F1)</b> o la tecla F1", "wn_help_search.svg"),
                ("h", "Backlog y All Experiments"),
                ("feature", "Backlog en pantallas anchas",
                 "En monitores grandes las cuatro columnas se muestran una al lado de otra con toda la altura.",
                 "Backlog", "wn_wide_backlog.svg"),
                ("feature", "Papelera",
                 "Una serie de ensayos borrada se puede recuperar durante 90 días. Puede borrar quien puede mover la "
                 "serie en el Backlog (en To Be Cleaned solo superusuarios).",
                 "Barra lateral → Superuser → <b>Recycle Bin</b>", "wn_recycle_bin.svg"),
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
                ("feature", "Inventario",
                 "Revisa una estantería bobina por bobina escaneando cada etiqueta. Las bobinas en otro lugar se "
                 "reubican al momento; las que faltan solo se dan de baja al terminar, tras preguntar.",
                 "Yarn Stock → Rack lookup → <b>Start stock take…</b>", "wn_stock_take.svg"),
                ("feature", "Historial de bobinas",
                 "Se registra cada cambio de una bobina: creada, cambiada, reubicada, dada de baja, inventario. Sin "
                 "selección se ve todo el lote, incluidas las bobinas agotadas.",
                 "Yarn Stock → <b>History…</b>", "wn_spool_history.svg"),
                ("feature", "Escanear etiquetas, no perder cambios",
                 "En <i>Go to spool #</i> puedes escanear la etiqueta en vez de escribir el número. Y Yarn Stock "
                 "pregunta ahora antes de perder cambios no guardados. Ayuda en tres idiomas: botón redondo arriba "
                 "a la derecha.",
                 "Yarn Stock → <b>Go to spool #</b>", None),
            ],
        },
    },
]

WINDOW_TITLE = {"en": "What's new", "de": "Was ist neu", "es": "Novedades"}
VERSIONS_TITLE = {"en": "Versions", "de": "Versionen", "es": "Versiones"}
NEW_BADGE = {"en": "NEW", "de": "NEU", "es": "NUEVO"}
WHERE_LABEL = {"en": "Where:", "de": "Wo:", "es": "Dónde:"}
VERSION_LABEL = {"en": "Version", "de": "Version", "es": "Versión"}
CURRENT_LABEL = {"en": "in progress", "de": "in Arbeit", "es": "en curso"}
CLOSE = {"en": "Close", "de": "Schliessen", "es": "Cerrar"}
