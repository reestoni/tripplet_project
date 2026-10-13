# ui/widgets/help_texts_report.py
"""Hilfetexte Report / Smart Chart (EN/DE/ES) fuer ui/widgets/multilang_help.py.

Die eigentliche Oberflaeche ist HTML/JS in ui/report_html_template.py
(Werkzeugleiste #global-toolbar, Diagramm-Kacheln, Drill-down _drillDown(),
Speichern/Oeffnen/PDF/Layout-Templates; Smart Chart = IS_VISUAL mit
Visual SQL Builder "Trial Data"/"Free Query" und Query-Templates
Personal/Shared/Certified). Bei Aenderungen dort hier (alle 3 Sprachen) und
in assets/images/help_report.svg nachziehen.
"""

SVG = "assets/images/help_report.svg"
SVG_W, SVG_H = 940, 424


def B(name: str) -> str:
    return f"<b>[{name}]</b>"


CHART_TYPES = "Scatter, Bar, Stacked Bar, Line, Box Plot, Heatmap, 3D"

TEXTS = {
    # ═══════════════════════════════ EN ═══════════════════════════════
    "en": {
        "window_title": "How do Report and Smart Chart work?",
        "close": "Close",
        "tabs": [
            {"key": "tasks", "title": "How do I…?", "blocks": [
                ("p", "<b>Report</b> shows charts for one trial series (opened from Show Experiment or the Backlog). "
                      "<b>Smart Chart</b> (sidebar) charts data across many series with a query builder, see the "
                      "<i>Smart Chart</i> tab. Numbers (1)–(5) refer to the <i>Screen guide</i> tab."),
                ("h", "Building the charts"),
                ("task", "Choose what a chart shows",
                 ["At the top of a chart card (3), choose the value in the first list (Y axis).",
                  "Choose the X axis in the second list. <i>to all</i> applies this X axis to every chart.",
                  "<b>+</b> next to the Y list adds another value to the same chart."]),
                ("task", "Show more or fewer charts",
                 ["Change the number in <i>Charts:</i> in the toolbar (1)."]),
                ("task", "Show scatter and range",
                 [f"{B('± SD')} switches the standard deviation bars on/off, {B('↕ Min/Max')} the min/max markers."]),
                ("task", "Compare with other trial series",
                 [f"Click {B('+ Compare')}, search for the series and select it.",
                  "Each series appears as a coloured chip in the toolbar; remove it with the small x on the chip."],
                 f"{B('Legend')} sets order and colours of the series."),
                ("task", "Look at the individual trials behind a value",
                 ["Click a bar or point (4). All charts switch to the individual trials of that value.",
                  "The <i>DRILL</i> bar (5) shows the path; click an earlier step to go back."]),
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
                ("task", "Export as PDF",
                 [f"Click {B('PDF')}, enter the title, choose a layout template and click {B('Export')}."]),
                ("task", "Reuse a layout",
                 [f"{B('Templates')}: save the current layout as a template, or apply/overwrite an existing one."]),
            ]},
            {"key": "screen", "title": "Screen guide", "blocks": [
                ("svg", SVG, {"smart_only": "Smart Chart only",
                              "drill_hint": "Click a bar or point to drill down to the individual trials (5 shows the path back)."},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Toolbar", "Number of charts, SD and Min/Max, legend, series chips with Series / + Compare / "
                                    "+ Image, report note, templates, Save, Open and PDF."),
                    ("(2) Builder", "Only in Smart Chart: defines which data is loaded, see the <i>Smart Chart</i> tab. "
                                    "Can be collapsed with the arrow."),
                    ("(3) Chart cards", "One chart each: Y and X axis on top, note and gridlines below, buttons to "
                                        "move, enlarge and remove."),
                    ("(4) Click to drill down", "Shows the individual trials behind a bar or point."),
                    ("(5) Drill path", "The steps of the drill-down; click an earlier step to go back."),
                ]),
            ]},
            {"key": "smart", "title": "Smart Chart", "blocks": [
                ("p", "Smart Chart (in the sidebar) builds charts across many trial series. The builder (2) has two "
                      "modes."),
                ("h", "Trial Data"),
                ("task", "Chart trial data of several series",
                 ["Choose <i>Group by (Legend)</i>, e.g. Jet: each group gets its own colour.",
                  "Add filters: <i>Simple</i> with " + B("+ Add Filter") + " (field = value), or <i>Advanced</i> with "
                  + B("+ Add Condition") + " (conditions with operators such as &gt;, &lt;, LIKE or IS NULL, all combined with AND).",
                  "Select the trial series in the list (Ctrl for several).",
                  f"Click {B('▶ Run Query')}."]),
                ("h", "Free Query"),
                ("task", "Build a chart from any table",
                 ["Choose the chart in <i>Configure Chart</i> and give it a title.",
                  f"Choose the chart type ({CHART_TYPES}).",
                  "Choose the base table and, if needed, more tables with " + B("+ Join") + ".",
                  "Set the axes X, Y (and Z, Color, Label if needed), filters under <i>Where</i> and the legend grouping.",
                  f"Click {B('▶ Run Query')}."]),
                ("h", "Query templates"),
                ("task", "Save or reuse a query",
                 ["Click the templates button next to " + B("▶ Run Query") + ".",
                  "Save the current query as <i>Personal</i> (only you) or <i>Shared</i> (all users), or select a "
                  f"template and click {B('Apply Template')}."],
                 "<i>Certified</i> templates have been checked and released by a superuser."),
                ("note", "<b>Tip:</b> Start with a saved template and adjust it, rather than building a query from scratch."),
            ]},
        ],
    },

    # ═══════════════════════════════ DE ═══════════════════════════════
    "de": {
        "window_title": "Wie funktionieren Report und Smart Chart?",
        "close": "Schliessen",
        "tabs": [
            {"key": "tasks", "title": "Wie mache ich…?", "blocks": [
                ("p", "<b>Report</b> zeigt Diagramme zu einer Versuchsserie (geöffnet aus Show Experiment oder dem Backlog). "
                      "<b>Smart Chart</b> (Sidebar) stellt Daten über viele Serien mit einem Abfrage-Baukasten dar, siehe Tab "
                      "<i>Smart Chart</i>. Die Nummern (1)–(5) verweisen auf den Tab <i>Bildschirm</i>."),
                ("h", "Diagramme zusammenstellen"),
                ("task", "Festlegen, was ein Diagramm zeigt",
                 ["Oben in einer Diagramm-Kachel (3) in der ersten Liste den Wert wählen (Y-Achse).",
                  "In der zweiten Liste die X-Achse wählen. <i>to all</i> übernimmt diese X-Achse für alle Diagramme.",
                  "<b>+</b> neben der Y-Liste fügt dem Diagramm einen weiteren Wert hinzu."]),
                ("task", "Mehr oder weniger Diagramme anzeigen",
                 ["In der Werkzeugleiste (1) die Zahl bei <i>Charts:</i> ändern."]),
                ("task", "Streuung und Bereich anzeigen",
                 [f"{B('± SD')} schaltet die Standardabweichung ein/aus, {B('↕ Min/Max')} die Min/Max-Markierungen."]),
                ("task", "Mit anderen Versuchsserien vergleichen",
                 [f"Auf {B('+ Compare')} klicken, die Serie suchen und auswählen.",
                  "Jede Serie erscheint als farbiges Kärtchen in der Werkzeugleiste; mit dem kleinen x darauf entfernen."],
                 f"{B('Legend')} legt Reihenfolge und Farben der Serien fest."),
                ("task", "Die einzelnen Versuche hinter einem Wert ansehen",
                 ["Auf einen Balken oder Punkt klicken (4). Alle Diagramme zeigen dann die einzelnen Versuche zu diesem Wert.",
                  "Die Leiste <i>DRILL</i> (5) zeigt den Weg; ein Klick auf einen früheren Schritt geht zurück."]),
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
                ("task", "Als PDF exportieren",
                 [f"Auf {B('PDF')} klicken, den Titel eingeben, eine Layout-Vorlage wählen und {B('Export')} klicken."]),
                ("task", "Ein Layout wiederverwenden",
                 [f"{B('Templates')}: das aktuelle Layout als Vorlage speichern, oder eine bestehende anwenden/überschreiben."]),
            ]},
            {"key": "screen", "title": "Bildschirm", "blocks": [
                ("svg", SVG, {"smart_only": "nur Smart Chart",
                              "drill_hint": "Klick auf Balken oder Punkt zeigt die einzelnen Versuche (5 zeigt den Weg zurück)."},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Werkzeugleiste", "Anzahl Diagramme, SD und Min/Max, Legende, Serien-Kärtchen mit Series / "
                                           "+ Compare / + Image, Report-Notiz, Vorlagen, Save, Open und PDF."),
                    ("(2) Baukasten", "Nur in Smart Chart: legt fest, welche Daten geladen werden, siehe Tab "
                                      "<i>Smart Chart</i>. Mit dem Pfeil einklappbar."),
                    ("(3) Diagramm-Kacheln", "Je ein Diagramm: Y- und X-Achse oben, Notiz und Hilfslinien unten, "
                                             "Knöpfe zum Verschieben, Vergrössern und Entfernen."),
                    ("(4) Klick zum Drill-down", "Zeigt die einzelnen Versuche hinter einem Balken oder Punkt."),
                    ("(5) Drill-Pfad", "Die Schritte des Drill-downs; Klick auf einen früheren Schritt geht zurück."),
                ]),
            ]},
            {"key": "smart", "title": "Smart Chart", "blocks": [
                ("p", "Smart Chart (in der Sidebar) erstellt Diagramme über viele Versuchsserien. Der Baukasten (2) "
                      "hat zwei Modi."),
                ("h", "Trial Data"),
                ("task", "Versuchsdaten mehrerer Serien darstellen",
                 ["<i>Group by (Legend)</i> wählen, z.&nbsp;B. Jet: Jede Gruppe bekommt eine eigene Farbe.",
                  "Filter hinzufügen: <i>Simple</i> mit " + B("+ Add Filter") + " (Feld = Wert), oder <i>Advanced</i> mit "
                  + B("+ Add Condition") + " (Bedingungen mit Operatoren wie &gt;, &lt;, LIKE oder IS NULL, alle mit UND verknüpft).",
                  "Die Versuchsserien in der Liste wählen (Strg für mehrere).",
                  f"Auf {B('▶ Run Query')} klicken."]),
                ("h", "Free Query"),
                ("task", "Ein Diagramm aus einer beliebigen Tabelle erstellen",
                 ["Unter <i>Configure Chart</i> das Diagramm wählen und ihm einen Titel geben.",
                  f"Den Diagrammtyp wählen ({CHART_TYPES}).",
                  "Die Basistabelle wählen und bei Bedarf weitere Tabellen mit " + B("+ Join") + " hinzufügen.",
                  "Die Achsen X, Y (bei Bedarf Z, Color, Label), Filter unter <i>Where</i> und die Legenden-Gruppierung festlegen.",
                  f"Auf {B('▶ Run Query')} klicken."]),
                ("h", "Abfrage-Vorlagen"),
                ("task", "Eine Abfrage speichern oder wiederverwenden",
                 ["Auf den Vorlagen-Knopf neben " + B("▶ Run Query") + " klicken.",
                  "Die aktuelle Abfrage als <i>Personal</i> (nur für dich) oder <i>Shared</i> (für alle) speichern, oder eine "
                  f"Vorlage wählen und {B('Apply Template')} klicken."],
                 "<i>Certified</i>-Vorlagen wurden von einem Superuser geprüft und freigegeben."),
                ("note", "<b>Tipp:</b> Lieber mit einer gespeicherten Vorlage beginnen und sie anpassen, statt eine "
                         "Abfrage ganz neu zu bauen."),
            ]},
        ],
    },

    # ═══════════════════════════════ ES ═══════════════════════════════
    "es": {
        "window_title": "¿Cómo funcionan Report y Smart Chart?",
        "close": "Cerrar",
        "tabs": [
            {"key": "tasks", "title": "¿Cómo hago…?", "blocks": [
                ("p", "<b>Report</b> muestra gráficos de una serie de ensayos (se abre desde Show Experiment o el Backlog). "
                      "<b>Smart Chart</b> (barra lateral) representa datos de muchas series con un constructor de "
                      "consultas, ver la pestaña <i>Smart Chart</i>. Los números (1)–(5) se refieren a la pestaña <i>Pantalla</i>."),
                ("h", "Montar los gráficos"),
                ("task", "Elegir qué muestra un gráfico",
                 ["Arriba en la tarjeta del gráfico (3), elige el valor en la primera lista (eje Y).",
                  "Elige el eje X en la segunda lista. <i>to all</i> aplica este eje X a todos los gráficos.",
                  "<b>+</b> junto a la lista Y añade otro valor al mismo gráfico."]),
                ("task", "Mostrar más o menos gráficos",
                 ["Cambia el número en <i>Charts:</i> en la barra de herramientas (1)."]),
                ("task", "Mostrar dispersión y rango",
                 [f"{B('± SD')} activa/desactiva las barras de desviación estándar, {B('↕ Min/Max')} las marcas de mín./máx."]),
                ("task", "Comparar con otras series de ensayos",
                 [f"Haz clic en {B('+ Compare')}, busca la serie y selecciónala.",
                  "Cada serie aparece como una etiqueta de color en la barra de herramientas; se quita con la pequeña x que lleva."],
                 f"{B('Legend')} define el orden y los colores de las series."),
                ("task", "Ver los ensayos individuales detrás de un valor",
                 ["Haz clic en una barra o un punto (4). Todos los gráficos muestran entonces los ensayos individuales de ese valor.",
                  "La barra <i>DRILL</i> (5) muestra el camino; un clic en un paso anterior vuelve atrás."]),
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
                ("task", "Exportar como PDF",
                 [f"Haz clic en {B('PDF')}, introduce el título, elige una plantilla de diseño y haz clic en {B('Export')}."]),
                ("task", "Reutilizar un diseño",
                 [f"{B('Templates')}: guarda el diseño actual como plantilla, o aplica/sobrescribe una existente."]),
            ]},
            {"key": "screen", "title": "Pantalla", "blocks": [
                ("svg", SVG, {"smart_only": "solo Smart Chart",
                              "drill_hint": "Clic en una barra o punto muestra los ensayos individuales (5 muestra el camino de vuelta)."},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Barra de herramientas", "Número de gráficos, SD y Min/Max, leyenda, etiquetas de series con "
                                                  "Series / + Compare / + Image, nota del informe, plantillas, Save, Open y PDF."),
                    ("(2) Constructor", "Solo en Smart Chart: define qué datos se cargan, ver la pestaña <i>Smart Chart</i>. "
                                        "Se puede plegar con la flecha."),
                    ("(3) Tarjetas de gráfico", "Un gráfico cada una: ejes Y y X arriba, nota y líneas guía abajo, "
                                                "botones para mover, ampliar y quitar."),
                    ("(4) Clic para profundizar", "Muestra los ensayos individuales detrás de una barra o un punto."),
                    ("(5) Camino de profundización", "Los pasos del drill-down; clic en un paso anterior vuelve atrás."),
                ]),
            ]},
            {"key": "smart", "title": "Smart Chart", "blocks": [
                ("p", "Smart Chart (en la barra lateral) crea gráficos de muchas series de ensayos. El constructor (2) "
                      "tiene dos modos."),
                ("h", "Trial Data"),
                ("task", "Representar datos de ensayos de varias series",
                 ["Elige <i>Group by (Legend)</i>, p.&nbsp;ej. Jet: cada grupo recibe su propio color.",
                  "Añade filtros: <i>Simple</i> con " + B("+ Add Filter") + " (campo = valor), o <i>Advanced</i> con "
                  + B("+ Add Condition") + " (condiciones con operadores como &gt;, &lt;, LIKE o IS NULL, todas combinadas con Y).",
                  "Selecciona las series de ensayos en la lista (Ctrl para varias).",
                  f"Haz clic en {B('▶ Run Query')}."]),
                ("h", "Free Query"),
                ("task", "Crear un gráfico a partir de cualquier tabla",
                 ["En <i>Configure Chart</i>, elige el gráfico y dale un título.",
                  f"Elige el tipo de gráfico ({CHART_TYPES}).",
                  "Elige la tabla base y, si hace falta, más tablas con " + B("+ Join") + ".",
                  "Define los ejes X, Y (y Z, Color, Label si hace falta), los filtros en <i>Where</i> y la agrupación de la leyenda.",
                  f"Haz clic en {B('▶ Run Query')}."]),
                ("h", "Plantillas de consulta"),
                ("task", "Guardar o reutilizar una consulta",
                 ["Haz clic en el botón de plantillas junto a " + B("▶ Run Query") + ".",
                  "Guarda la consulta actual como <i>Personal</i> (solo tú) o <i>Shared</i> (todos), o elige una "
                  f"plantilla y haz clic en {B('Apply Template')}."],
                 "Las plantillas <i>Certified</i> han sido revisadas y aprobadas por un superusuario."),
                ("note", "<b>Consejo:</b> Mejor empezar con una plantilla guardada y adaptarla que construir una consulta desde cero."),
            ]},
        ],
    },
}
