# ui/widgets/help_texts_report.py
"""Hilfetexte Report / Smart Chart (EN/DE/ES) fuer ui/widgets/multilang_help.py.

Die eigentliche Oberflaeche ist HTML/JS in ui/report_html_template.py
(Werkzeugleiste #global-toolbar, Diagramm-Kacheln, Drill-down _drillDown(),
Speichern/Oeffnen/PDF/Layout-Templates). Seit 2026-10-30 nur noch der
Report einer Serie - der neue Smart Chart (ui/screen_smart_chart.py) hat
seine eigene Hilfe help_texts_smart_chart.py. Bei Aenderungen dort hier
(alle 3 Sprachen) und in assets/images/help_report.svg nachziehen.
"""

SVG = "assets/images/help_report.svg"
SVG_W, SVG_H = 940, 424


def B(name: str) -> str:
    return f"<b>[{name}]</b>"


CHART_TYPES = "Scatter, Bar, Stacked Bar, Line, Box Plot, Heatmap, 3D"

TEXTS = {
    # ═══════════════════════════════ EN ═══════════════════════════════
    "en": {
        "window_title": "How does the Report work?",
        "close": "Close",
        "tabs": [
            {"key": "tasks", "title": "How do I…?", "blocks": [
                ("p", "<b>Report</b> shows charts for one trial series (opened from Show Experiment or the Backlog). "
                      "To chart trials across many series, use <b>Smart Chart</b> in the sidebar - it has its own help. "
                      "Numbers (1)–(4) refer to the <i>Screen guide</i> tab."),
                ("h", "Building the charts"),
                ("task", "Choose what a chart shows",
                 ["At the top of a chart card (2), choose the value in the first list (Y axis).",
                  "Choose the X axis in the second list. <i>to all</i> applies this X axis to every chart.",
                  "<b>+</b> next to the Y list adds another value to the same chart."]),
                ("task", "Two levels on the X axis, e.g. Yarn and under it the Jets",
                 ["Choose the first level in the X list, e.g. <i>Yarn</i> (the short name of the yarn).",
                  "In the list right of it (after ›) choose the second level, e.g. <i>Jet</i>. The X axis then shows "
                  "each yarn with its jets below it - only the combinations that were really tested.",
                  "<i>— none —</i> goes back to one level."],
                 "Works with grouped and stacked bars, box plots and scatter. A double-click on a bar shows the "
                 "trials of exactly that yarn and jet. A trial with several yarns appears under all of them "
                 "together (\"A / B\")."),
                ("task", "Show more or fewer charts",
                 ["Change the number in <i>Charts:</i> in the toolbar (1)."]),
                ("task", "Show scatter and range",
                 [f"{B('± SD')} switches the standard deviation bars on/off, {B('↕ Min/Max')} the min/max markers."]),
                ("task", "Compare with other trial series",
                 [f"Click {B('+ Compare')}, search for the series and select it.",
                  "Each series appears as a coloured chip in the toolbar; remove it with the small x on the chip."],
                 f"{B('Legend')} sets order and colours of the series."),
                ("task", "Look at the individual trials behind a value",
                 ["Click a bar or point (3). All charts switch to the individual trials of that value.",
                  "The <i>DRILL</i> bar (4) shows the path; click an earlier step to go back."]),
                ("task", "Add notes and images",
                 ["Each chart has its own note field. " + B("Note") + " adds a note for the whole report.",
                  f"{B('+ Image')} inserts an image between the charts."],
                 "Gridlines: enter values such as <i>5, 10, 15</i> in the gridline field of a chart."),
                ("task", "Rearrange charts",
                 ["Drag a chart at its handle, or use ▲ ▼ to move it, [ ] to enlarge it and x to remove it."]),
                ("h", "Saving and sharing"),
                ("task", "Save a report",
                 [f"Click {B('Save')}, enter a title (and author, info box position, overall note).",
                  f"Click {B('Save Report')}. For an existing report, {B('Save as New')} keeps the old one."],
                 "Saved reports of a series can be opened in Show Experiment (list next to Report, then Go!) and "
                 "from the report icon in the Backlog."),
                ("task", "Open a saved report",
                 [f"Click {B('Open')}, search by title or author, select it and click {B('Open Selected')}."],
                 "The bin icon in the list deletes a report."),
                ("task", "See notes on values in the chart",
                 [f"Click {B('Notes')} in the toolbar. Bars and points with a note (written in Show Experiment) "
                  "get a purple outline; point at them to read the note."],
                 "Off by default. Notes on the whole trial appear in the tooltip of all its values, without outline."),
                ("task", "Export as PDF",
                 [f"Click {B('PDF')}, enter the title, choose a layout template and click {B('Export')}."],
                 "Notes on values are not printed, even if they are shown on screen. Only if you tick "
                 "<i>Include notes on values</i> in the export window does the PDF get the purple outlines and a "
                 "list of the notes below each chart - for in-house reports only."),
                ("task", "Reuse a layout",
                 [f"{B('Templates')}: save the current layout as a template, or apply/overwrite an existing one."]),
            ]},
            {"key": "screen", "title": "Screen guide", "blocks": [
                ("svg", SVG, {"drill_hint": "Click a bar or point to drill down to the individual trials (5 shows the path back)."},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Toolbar", "Number of charts, SD and Min/Max, Notes, legend, series chips with Series / + Compare / "
                                    "+ Image, report note, templates, Save, Open and PDF."),
                    ("(2) Chart cards", "One chart each: Y and X axis on top, note and gridlines below, buttons to "
                                        "move, enlarge and remove."),
                    ("(3) Click to drill down", "Shows the individual trials behind a bar or point."),
                    ("(4) Drill path", "The steps of the drill-down; click an earlier step to go back."),
                ]),
            ]},
        ],
    },

    # ═══════════════════════════════ DE ═══════════════════════════════
    "de": {
        "window_title": "Wie funktioniert der Report?",
        "close": "Schliessen",
        "tabs": [
            {"key": "tasks", "title": "Wie mache ich…?", "blocks": [
                ("p", "<b>Report</b> zeigt Diagramme zu einer Versuchsserie (geöffnet aus Show Experiment oder dem Backlog). "
                      "Für Versuche über viele Serien hinweg gibt es <b>Smart Chart</b> in der Sidebar - mit eigener Hilfe. "
                      "Die Nummern (1)–(4) verweisen auf den Tab <i>Bildschirm</i>."),
                ("h", "Diagramme zusammenstellen"),
                ("task", "Festlegen, was ein Diagramm zeigt",
                 ["Oben in einer Diagramm-Kachel (2) in der ersten Liste den Wert wählen (Y-Achse).",
                  "In der zweiten Liste die X-Achse wählen. <i>to all</i> übernimmt diese X-Achse für alle Diagramme.",
                  "<b>+</b> neben der Y-Liste fügt dem Diagramm einen weiteren Wert hinzu."]),
                ("task", "Zwei Ebenen auf der X-Achse, z.&nbsp;B. Garn und darunter die Jets",
                 ["In der X-Liste die erste Ebene wählen, z.&nbsp;B. <i>Yarn</i> (Kurzname des Garns).",
                  "In der Liste rechts daneben (nach ›) die zweite Ebene wählen, z.&nbsp;B. <i>Jet</i>. Die X-Achse "
                  "zeigt dann jedes Garn mit seinen Jets darunter - nur die Kombinationen, die wirklich getestet "
                  "wurden.",
                  "<i>— none —</i> geht zurück zu einer Ebene."],
                 "Geht mit gruppierten und gestapelten Balken, Boxplots und Punkten. Doppelklick auf einen Balken "
                 "zeigt die Versuche genau dieses Garns und Jets. Ein Versuch mit mehreren Garnen steht unter allen "
                 "zusammen (\"A / B\")."),
                ("task", "Mehr oder weniger Diagramme anzeigen",
                 ["In der Werkzeugleiste (1) die Zahl bei <i>Charts:</i> ändern."]),
                ("task", "Streuung und Bereich anzeigen",
                 [f"{B('± SD')} schaltet die Standardabweichung ein/aus, {B('↕ Min/Max')} die Min/Max-Markierungen."]),
                ("task", "Mit anderen Versuchsserien vergleichen",
                 [f"Auf {B('+ Compare')} klicken, die Serie suchen und auswählen.",
                  "Jede Serie erscheint als farbiges Kärtchen in der Werkzeugleiste; mit dem kleinen x darauf entfernen."],
                 f"{B('Legend')} legt Reihenfolge und Farben der Serien fest."),
                ("task", "Die einzelnen Versuche hinter einem Wert ansehen",
                 ["Auf einen Balken oder Punkt klicken (3). Alle Diagramme zeigen dann die einzelnen Versuche zu diesem Wert.",
                  "Die Leiste <i>DRILL</i> (4) zeigt den Weg; ein Klick auf einen früheren Schritt geht zurück."]),
                ("task", "Notizen und Bilder hinzufügen",
                 ["Jedes Diagramm hat ein eigenes Notizfeld. " + B("Note") + " fügt eine Notiz für den ganzen Report hinzu.",
                  f"{B('+ Image')} fügt ein Bild zwischen den Diagrammen ein."],
                 "Hilfslinien: im Hilfslinien-Feld eines Diagramms Werte wie <i>5, 10, 15</i> eingeben."),
                ("task", "Diagramme umordnen",
                 ["Ein Diagramm am Griff ziehen, oder mit ▲ ▼ verschieben, mit [ ] vergrössern und mit x entfernen."]),
                ("h", "Speichern und teilen"),
                ("task", "Einen Report speichern",
                 [f"Auf {B('Save')} klicken, einen Titel eingeben (dazu Autor, Position der Infobox, Gesamtnotiz).",
                  f"Auf {B('Save Report')} klicken. Bei einem bestehenden Report behält {B('Save as New')} den alten."],
                 "Gespeicherte Reports einer Serie lassen sich in Show Experiment (Liste neben Report, dann Go!) und "
                 "über das Report-Symbol im Backlog öffnen."),
                ("task", "Einen gespeicherten Report öffnen",
                 [f"Auf {B('Open')} klicken, nach Titel oder Autor suchen, auswählen und {B('Open Selected')} klicken."],
                 "Das Papierkorb-Symbol in der Liste löscht einen Report."),
                ("task", "Notizen an Werten im Diagramm sehen",
                 [f"In der Werkzeugleiste auf {B('Notes')} klicken. Balken und Punkte mit einer Notiz (geschrieben "
                  "in Show Experiment) bekommen einen violetten Rand; mit der Maus darauf zeigen, um sie zu lesen."],
                 "Standardmässig aus. Notizen zum ganzen Versuch stehen im Tooltip aller seiner Werte, ohne Rand."),
                ("task", "Als PDF exportieren",
                 [f"Auf {B('PDF')} klicken, den Titel eingeben, eine Layout-Vorlage wählen und {B('Export')} klicken."],
                 "Notizen an Werten werden nicht gedruckt, auch wenn sie am Bildschirm angezeigt werden. Nur mit "
                 "dem Häkchen <i>Include notes on values</i> im Export-Fenster bekommt das PDF die violetten Ränder "
                 "und unter jedem Diagramm eine Liste der Notizen - nur für interne Reports."),
                ("task", "Ein Layout wiederverwenden",
                 [f"{B('Templates')}: das aktuelle Layout als Vorlage speichern, oder eine bestehende anwenden/überschreiben."]),
            ]},
            {"key": "screen", "title": "Bildschirm", "blocks": [
                ("svg", SVG, {"drill_hint": "Klick auf Balken oder Punkt zeigt die einzelnen Versuche (5 zeigt den Weg zurück)."},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Werkzeugleiste", "Anzahl Diagramme, SD und Min/Max, Notes, Legende, Serien-Kärtchen mit Series / "
                                           "+ Compare / + Image, Report-Notiz, Vorlagen, Save, Open und PDF."),
                    ("(2) Diagramm-Kacheln", "Je ein Diagramm: Y- und X-Achse oben, Notiz und Hilfslinien unten, "
                                             "Knöpfe zum Verschieben, Vergrössern und Entfernen."),
                    ("(3) Klick zum Drill-down", "Zeigt die einzelnen Versuche hinter einem Balken oder Punkt."),
                    ("(4) Drill-Pfad", "Die Schritte des Drill-downs; Klick auf einen früheren Schritt geht zurück."),
                ]),
            ]},
        ],
    },

    # ═══════════════════════════════ ES ═══════════════════════════════
    "es": {
        "window_title": "¿Cómo funciona el Report?",
        "close": "Cerrar",
        "tabs": [
            {"key": "tasks", "title": "¿Cómo hago…?", "blocks": [
                ("p", "<b>Report</b> muestra gráficos de una serie de ensayos (se abre desde Show Experiment o el Backlog). "
                      "Para ensayos de muchas series está <b>Smart Chart</b> en la barra lateral, con su propia ayuda. "
                      "Los números (1)–(4) se refieren a la pestaña <i>Pantalla</i>."),
                ("h", "Montar los gráficos"),
                ("task", "Elegir qué muestra un gráfico",
                 ["Arriba en la tarjeta del gráfico (2), elige el valor en la primera lista (eje Y).",
                  "Elige el eje X en la segunda lista. <i>to all</i> aplica este eje X a todos los gráficos.",
                  "<b>+</b> junto a la lista Y añade otro valor al mismo gráfico."]),
                ("task", "Dos niveles en el eje X, p.&nbsp;ej. hilo y debajo los jets",
                 ["Elige el primer nivel en la lista X, p.&nbsp;ej. <i>Yarn</i> (el nombre corto del hilo).",
                  "En la lista de la derecha (tras ›) elige el segundo nivel, p.&nbsp;ej. <i>Jet</i>. El eje X muestra "
                  "entonces cada hilo con sus jets debajo, solo las combinaciones realmente ensayadas.",
                  "<i>— none —</i> vuelve a un solo nivel."],
                 "Funciona con barras agrupadas y apiladas, box plots y dispersión. Un doble clic en una barra muestra "
                 "los ensayos de ese hilo y jet. Un ensayo con varios hilos aparece bajo todos juntos (\"A / B\")."),
                ("task", "Mostrar más o menos gráficos",
                 ["Cambia el número en <i>Charts:</i> en la barra de herramientas (1)."]),
                ("task", "Mostrar dispersión y rango",
                 [f"{B('± SD')} activa/desactiva las barras de desviación estándar, {B('↕ Min/Max')} las marcas de mín./máx."]),
                ("task", "Comparar con otras series de ensayos",
                 [f"Haz clic en {B('+ Compare')}, busca la serie y selecciónala.",
                  "Cada serie aparece como una etiqueta de color en la barra de herramientas; se quita con la pequeña x que lleva."],
                 f"{B('Legend')} define el orden y los colores de las series."),
                ("task", "Ver los ensayos individuales detrás de un valor",
                 ["Haz clic en una barra o un punto (3). Todos los gráficos muestran entonces los ensayos individuales de ese valor.",
                  "La barra <i>DRILL</i> (4) muestra el camino; un clic en un paso anterior vuelve atrás."]),
                ("task", "Añadir notas e imágenes",
                 ["Cada gráfico tiene su propio campo de nota. " + B("Note") + " añade una nota para todo el informe.",
                  f"{B('+ Image')} inserta una imagen entre los gráficos."],
                 "Líneas guía: introduce valores como <i>5, 10, 15</i> en el campo de líneas guía de un gráfico."),
                ("task", "Reordenar los gráficos",
                 ["Arrastra un gráfico por su asa, o usa ▲ ▼ para moverlo, [ ] para ampliarlo y x para quitarlo."]),
                ("h", "Guardar y compartir"),
                ("task", "Guardar un informe",
                 [f"Haz clic en {B('Save')}, introduce un título (y autor, posición del recuadro de información, nota general).",
                  f"Haz clic en {B('Save Report')}. En un informe existente, {B('Save as New')} conserva el anterior."],
                 "Los informes guardados de una serie se abren en Show Experiment (lista junto a Report, luego Go!) y "
                 "desde el icono de informe en el Backlog."),
                ("task", "Abrir un informe guardado",
                 [f"Haz clic en {B('Open')}, busca por título o autor, selecciónalo y haz clic en {B('Open Selected')}."],
                 "El icono de papelera de la lista borra un informe."),
                ("task", "Ver las notas de los valores en el gráfico",
                 [f"Haz clic en {B('Notes')} en la barra de herramientas. Las barras y puntos con una nota (escrita "
                  "en Show Experiment) reciben un borde violeta; señálalos con el ratón para leer la nota."],
                 "Desactivado por defecto. Las notas sobre todo el ensayo aparecen en la descripción emergente de "
                 "todos sus valores, sin borde."),
                ("task", "Exportar como PDF",
                 [f"Haz clic en {B('PDF')}, introduce el título, elige una plantilla de diseño y haz clic en {B('Export')}."],
                 "Las notas de los valores no se imprimen, aunque se vean en pantalla. Solo si marcas "
                 "<i>Include notes on values</i> en la ventana de exportación, el PDF lleva los bordes violetas y "
                 "una lista de las notas bajo cada gráfico; solo para informes internos."),
                ("task", "Reutilizar un diseño",
                 [f"{B('Templates')}: guarda el diseño actual como plantilla, o aplica/sobrescribe una existente."]),
            ]},
            {"key": "screen", "title": "Pantalla", "blocks": [
                ("svg", SVG, {"drill_hint": "Clic en una barra o punto muestra los ensayos individuales (5 muestra el camino de vuelta)."},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Barra de herramientas", "Número de gráficos, SD y Min/Max, Notes, leyenda, etiquetas de series con "
                                                  "Series / + Compare / + Image, nota del informe, plantillas, Save, Open y PDF."),
                    ("(2) Tarjetas de gráfico", "Un gráfico cada una: ejes Y y X arriba, nota y líneas guía abajo, "
                                                "botones para mover, ampliar y quitar."),
                    ("(3) Clic para profundizar", "Muestra los ensayos individuales detrás de una barra o un punto."),
                    ("(4) Camino de profundización", "Los pasos del drill-down; clic en un paso anterior vuelve atrás."),
                ]),
            ]},
        ],
    },
}
