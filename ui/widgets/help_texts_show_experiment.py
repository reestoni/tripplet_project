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
                ("h", "Entering data"),
                ("task", "Enter or change a value",
                 ["Click the cell (7) and type the value, or double-click to edit it. Press Enter.",
                  f"Click {B('Save')} or press Ctrl+S."],
                 "If you leave the screen with unsaved changes, TrippleT asks whether to save them. "
                 "With access level 1 the screen is read-only."),
                ("task", "Set the same value for many trials",
                 ["In <i>Machine Data</i> or <i>R&amp;D Machine Data</i>, right-click the parameter name in the "
                  "first column (6) → " + M("Fill row") + ".",
                  "Choose the value and the range of trials, then OK.",
                  f"Click {B('Save')}."],
                 "Right-clicking a merged cell opens the same dialog."),
                ("task", "Copy and paste values",
                 ["Select cells and press Ctrl+C, then select the target cell and press Ctrl+V.",
                  f"Click {B('Save')}."],
                 "Works between tables and with Excel."),
                ("task", "Import a Statimat or Itemat report",
                 [f"Click {B('Statimat import')} or {B('Itemat import')} in the toolbar (1).",
                  "Choose the PDF report. The values are filled into the matching lab tab.",
                  f"Check the values, then click {B('Save')}."]),
                ("h", "Trials and plies"),
                ("task", "Add new trials",
                 ["Click the <b>+</b> icon (add trial) on the right of (2). Create Experiment opens in the mode for adding trials to this series."]),
                ("task", "Copy existing trials",
                 ["In <i>Machine Data</i>, right-click a trial number in the first row (4) → " + M("Copy trials…") + ".",
                  "In <i>Copy trials</i>, choose from/to trial and the number of copies per trial, then OK."],
                 "Machine settings and plies are copied. Lab values and the yarn tensions before/after the "
                 "jet of the copies stay empty. The new trials "
                 "are added at the end. Several copies of a range are added as repeated blocks "
                 "(e.g. V1–V6 copied 5 times: V7–V12 = V1–V6, V13–V18 = V1–V6, …). Reference samples are never copied."),
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
                              "keys_hint": "Ctrl+C / Ctrl+V copy and paste cells · Ctrl+S save · F5 reload"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Toolbar", "Experiment ID and series, attachments (upload and show images/PDFs), Statimat and "
                                    "Itemat import, report icon and saved reports (list + Go!), reload (↻), Save and this help."),
                    ("(2) Material line", "Material of the series, linked experiment request (ER), machine info, "
                                          "trial labels, <b>+T</b> (add trials) and <b>+ Ref</b> (add reference sample)."),
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
                                     "parameters, columns are trials and plies."),
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
                ("h", "Daten erfassen"),
                ("task", "Einen Wert eingeben oder ändern",
                 ["Die Zelle (7) anklicken und den Wert eintippen, oder doppelklicken zum Bearbeiten. Enter drücken.",
                  f"Auf {B('Save')} klicken oder Strg+S drücken."],
                 "Verlässt du den Bildschirm mit ungespeicherten Änderungen, fragt TrippleT, ob gespeichert werden soll. "
                 "Mit Access Level 1 ist der Bildschirm nur lesbar."),
                ("task", "Denselben Wert für viele Versuche setzen",
                 ["In <i>Machine Data</i> oder <i>R&amp;D Machine Data</i> mit Rechtsklick auf den Parameternamen in der "
                  "ersten Spalte (6) → " + M("Fill row") + ".",
                  "Wert und Versuchsbereich wählen, dann OK.",
                  f"Auf {B('Save')} klicken."],
                 "Rechtsklick auf eine zusammengefasste Zelle öffnet denselben Dialog."),
                ("task", "Werte kopieren und einfügen",
                 ["Zellen markieren und Strg+C drücken, dann die Zielzelle wählen und Strg+V drücken.",
                  f"Auf {B('Save')} klicken."],
                 "Funktioniert zwischen Tabellen und mit Excel."),
                ("task", "Einen Statimat- oder Itemat-Bericht importieren",
                 [f"In der Werkzeugleiste (1) auf {B('Statimat import')} oder {B('Itemat import')} klicken.",
                  "Den PDF-Bericht wählen. Die Werte werden in den passenden Labor-Tab eingetragen.",
                  f"Werte prüfen, dann auf {B('Save')} klicken."]),
                ("h", "Versuche und Plies"),
                ("task", "Neue Versuche hinzufügen",
                 ["Rechts in (2) auf das <b>+</b>-Symbol (Versuch hinzufügen) klicken. Create Experiment öffnet sich im Modus zum Hinzufügen von Versuchen zu dieser Serie."]),
                ("task", "Bestehende Versuche kopieren",
                 ["In <i>Machine Data</i> mit Rechtsklick auf eine Versuchsnummer in der ersten Zeile (4) → "
                  + M("Copy trials…") + ".",
                  "In <i>Copy trials</i> Von-/Bis-Versuch und Anzahl Kopien pro Versuch wählen, dann OK."],
                 "Maschineneinstellungen und Plies werden kopiert. Die Laborwerte und die Fadenspannungen vor/nach "
                 "Jet der Kopien bleiben leer. Die neuen "
                 "Versuche werden hinten angehängt. Mehrere Kopien eines Bereichs werden als wiederholte Blöcke "
                 "angehängt (z. B. V1–V6 fünfmal kopiert: V7–V12 = V1–V6, V13–V18 = V1–V6, …). "
                 "Referenzmuster werden nie mitkopiert."),
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
                              "keys_hint": "Strg+C / Strg+V Zellen kopieren und einfügen · Strg+S speichern · F5 neu laden"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Werkzeugleiste", "Experiment-ID und Serie, Anhänge (Bilder/PDFs hochladen und ansehen), Statimat- "
                                           "und Itemat-Import, Report-Symbol und gespeicherte Reports (Liste + Go!), neu laden (↻), Save und diese Hilfe."),
                    ("(2) Materialzeile", "Material der Serie, verknüpfter Experiment Request (ER), Maschineninfo, "
                                          "Versuchsetiketten, <b>+T</b> (Versuche hinzufügen) und <b>+ Ref</b> "
                                          "(Referenzmuster hinzufügen)."),
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
                                     "Zeilen sind Parameter, Spalten sind Versuche und Plies."),
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
                ("h", "Introducir datos"),
                ("task", "Introducir o cambiar un valor",
                 ["Haz clic en la celda (7) y escribe el valor, o haz doble clic para editarlo. Pulsa Enter.",
                  f"Haz clic en {B('Save')} o pulsa Ctrl+S."],
                 "Si sales de la pantalla con cambios sin guardar, TrippleT pregunta si quieres guardarlos. "
                 "Con nivel de acceso 1 la pantalla es de solo lectura."),
                ("task", "Poner el mismo valor en muchos ensayos",
                 ["En <i>Machine Data</i> o <i>R&amp;D Machine Data</i>, clic derecho en el nombre del parámetro en la "
                  "primera columna (6) → " + M("Fill row") + ".",
                  "Elige el valor y el rango de ensayos y haz clic en OK.",
                  f"Haz clic en {B('Save')}."],
                 "El clic derecho en una celda combinada abre el mismo diálogo."),
                ("task", "Copiar y pegar valores",
                 ["Selecciona celdas y pulsa Ctrl+C, luego elige la celda de destino y pulsa Ctrl+V.",
                  f"Haz clic en {B('Save')}."],
                 "Funciona entre tablas y con Excel."),
                ("task", "Importar un informe de Statimat o Itemat",
                 [f"Haz clic en {B('Statimat import')} o {B('Itemat import')} en la barra de herramientas (1).",
                  "Elige el informe en PDF. Los valores se introducen en la pestaña de laboratorio correspondiente.",
                  f"Revisa los valores y haz clic en {B('Save')}."]),
                ("h", "Ensayos y plies"),
                ("task", "Añadir ensayos nuevos",
                 ["Haz clic en el icono <b>+</b> (añadir ensayo) a la derecha de (2). Create Experiment se abre en el modo para añadir ensayos a esta serie."]),
                ("task", "Copiar ensayos existentes",
                 ["En <i>Machine Data</i>, clic derecho en un número de ensayo de la primera fila (4) → "
                  + M("Copy trials…") + ".",
                  "En <i>Copy trials</i>, elige el ensayo inicial y final y el número de copias por ensayo, y haz clic en OK."],
                 "Se copian los ajustes de máquina y los plies. Los valores de laboratorio y las tensiones del "
                 "hilo antes/después del jet de las copias quedan "
                 "vacíos. Los ensayos nuevos se añaden al final. Varias copias de un rango se añaden como "
                 "bloques repetidos (p. ej. V1–V6 copiado 5 veces: V7–V12 = V1–V6, V13–V18 = V1–V6, …). "
                 "Las muestras de referencia nunca se copian."),
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
                              "keys_hint": "Ctrl+C / Ctrl+V copiar y pegar celdas · Ctrl+S guardar · F5 recargar"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Barra de herramientas", "ID del experimento y serie, adjuntos (subir y ver imágenes/PDF), "
                                                  "importación de Statimat e Itemat, icono de informe e informes guardados (lista + Go!), "
                                                  "recargar (↻), Save y esta ayuda."),
                    ("(2) Línea de material", "Material de la serie, solicitud de experimento vinculada (ER), datos de "
                                              "la máquina, etiquetas de ensayos, <b>+T</b> (añadir ensayos) y "
                                              "<b>+ Ref</b> (añadir muestra de referencia)."),
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
                                     "tobera, …). Las filas son parámetros, las columnas ensayos y plies."),
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
