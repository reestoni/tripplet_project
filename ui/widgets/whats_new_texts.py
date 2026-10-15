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
                ("h", "Backlog and All Experiments"),
                ("feature", "Backlog on wide screens",
                 "On big monitors all four columns stand side by side and use the full height.",
                 "Backlog", "wn_wide_backlog.svg"),
                ("feature", "Recycle Bin",
                 "A deleted trial series can be restored for 90 days. Whoever may move a series in the Backlog may "
                 "delete it (in To Be Cleaned: superusers only).",
                 "Sidebar → Superuser → <b>Recycle Bin</b>", "wn_recycle_bin.svg"),
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
                ("h", "Backlog und All Experiments"),
                ("feature", "Backlog auf breiten Bildschirmen",
                 "Auf grossen Monitoren stehen alle vier Spalten nebeneinander und nutzen die volle Höhe.",
                 "Backlog", "wn_wide_backlog.svg"),
                ("feature", "Papierkorb",
                 "Eine gelöschte Versuchsserie lässt sich 90 Tage lang wiederherstellen. Löschen darf, wer die Serie "
                 "im Backlog verschieben darf (in To Be Cleaned nur Superuser).",
                 "Sidebar → Superuser → <b>Recycle Bin</b>", "wn_recycle_bin.svg"),
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
                ("h", "Backlog y All Experiments"),
                ("feature", "Backlog en pantallas anchas",
                 "En monitores grandes las cuatro columnas se muestran una al lado de otra con toda la altura.",
                 "Backlog", "wn_wide_backlog.svg"),
                ("feature", "Papelera",
                 "Una serie de ensayos borrada se puede recuperar durante 90 días. Puede borrar quien puede mover la "
                 "serie en el Backlog (en To Be Cleaned solo superusuarios).",
                 "Barra lateral → Superuser → <b>Recycle Bin</b>", "wn_recycle_bin.svg"),
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
