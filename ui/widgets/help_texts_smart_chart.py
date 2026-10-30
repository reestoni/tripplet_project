# ui/widgets/help_texts_smart_chart.py
"""Hilfetexte Smart Chart (EN/DE/ES) fuer ui/widgets/multilang_help.py.

Spiegelt ui/screen_smart_chart.py (neu seit 2026-10-30): links "1 Find
trials" mit Filter-Kaertchen, "+ Add filter" (ui/smart_chart_filter_dialog.py,
Histogramm/Ankreuzliste) und "Yarn filters apply to"; rechts Zaehler,
"2 Build the chart" (X, Y, Colour by, Split by, Chart, Colours, Options),
Diagramm und Trefferliste; oben New, Open view, Save view, Excel, Reload,
PDF. Bei Aenderungen dort hier (alle 3 Sprachen) nachziehen.
"""


def B(name: str) -> str:
    return f"<b>[{name}]</b>"


TEXTS = {
    # ═══════════════════════════════ EN ═══════════════════════════════
    "en": {
        "window_title": "How does Smart Chart work?",
        "close": "Close",
        "tabs": [
            {"key": "tasks", "title": "How do I…?", "blocks": [
                ("p", "Smart Chart finds trials by their properties - yarn, machine settings, lab results - across "
                      "<b>all</b> trial series, and charts any field against any other. Two steps: "
                      "<b>1 Find trials</b> (left) and <b>2 Build the chart</b> (right)."),
                ("h", "1 Find trials"),
                ("task", "Find e.g. all polyester trials with 70–80 dtex and 30–40 filaments",
                 [f"Click {B('+ Add filter')}, choose <i>Material</i>, tick <i>PES</i> and click {B('Add filter')}.",
                  f"Click {B('+ Add filter')} again, choose <i>End titer</i>, enter From 70 To 80 (or drag across the "
                  "bars) and add it.",
                  "Do the same with <i>Filaments</i> 30 to 40."],
                 "The green box at the top always shows how many trials match, in how many series. "
                 "Reference samples are never included."),
                ("task", "Change or remove a filter",
                 ["Click the filter card to change it, or its <b>×</b> to remove it."]),
                ("task", "Only look at the core (or effect) yarn",
                 ["Under <i>Yarn filters apply to</i> choose <i>Core only</i> or <i>Effect only</i>."],
                 "With <i>Any ply</i>, all yarn filters must fit the <b>same</b> ply of the trial - PES + 70–80 dtex "
                 "means one yarn that is both, not a PES ply and some other 75 dtex ply."),
                ("task", "Understand the histogram in “Add filter”",
                 ["The bars show how the values are spread over the trials your other filters leave. "
                  "Green bars are inside your range.",
                  "The line below tells you how many trials the new filter would leave - before you add it."]),
                ("task", "Find a field quickly",
                 [f"In {B('+ Add filter')} the fields are grouped (Yarn, Jet, Machine, Lab, General); click a group "
                  "to open or close it.",
                  "Or type part of the name into <i>Search a field…</i> - the matching groups open by themselves.",
                  "X axis, Y axis, Colour by and Split by work the same way: one sub-menu per group."],
                 "The <i>Jet</i> group has the data of the jet used in the trial: air hole, yarn channel, swirl "
                 "chamber, cone, titer range, maker, material and more. All lab tables (Statimat, Itemat, DTYoMat, "
                 "shrinkage …) are in the <i>Lab</i> folder."),
                ("task", "Only whole numbers, or only 1, 1.5, 2 …",
                 ["Choose a number field, e.g. Overfeed, and enter From and To.",
                  "Below, choose <i>Only every</i> 1 (whole numbers only) or 0.5 (1, 1.5, 2 …) - or type your own step.",
                  "Or choose <i>Pick values</i>: every value that occurs in the range is listed with its number of "
                  "trials; tick the ones you want."],
                 "The filter card shows it, e.g. <i>Overfeed 1 – 5 % · every 0.5</i>."),
                ("h", "2 Build the chart"),
                ("task", "Choose what the chart shows",
                 ["Choose the <i>X axis</i> and the <i>Y axis</i>.",
                  "Choose the kind of chart under <i>Chart</i>: <i>Points</i>, <i>Points + trend line</i> (straight "
                  "line per colour with R²), <i>Mean line</i>, <i>Bars</i>, <i>Box plot</i>, <i>Violin</i>, "
                  "<i>Histogram of Y</i> (how Y is spread, X is not used) or <i>Density map</i> (where most trials lie)."],
                 "Only trials with a value for both X and Y are drawn; the green box says how many."),
                ("task", "Play with the colours",
                 ["<i>Colour by</i> a list field (Jet, Machine, Material…) gives each value its own colour; a number "
                  "field (e.g. Speed) colours the points along a colour scale.",
                  "Choose a palette under <i>Colours</i>, e.g. <i>Heberlein green</i>, <i>Colour-blind safe</i> or "
                  "<i>Greyscale (print)</i>.",
                  f"{B('Colours…')} lets you pick your own colour for each value.",
                  f"{B('Options')}: different shapes per colour, logarithmic axes, point size, dark background."],
                 "Click a legend entry to hide it, double-click to show only that one. Your colours and options are "
                 "saved with the view."),
                ("task", "Compare machines (or materials) side by side",
                 ["Choose a field under <i>Split by</i>, e.g. Machine. You get one small chart per value, all with "
                  "the same axes."],
                 "At most 9 panels are shown (the most frequent values)."),
                ("task", "Find out which trial a point is",
                 ["Point at it: the tooltip shows trial, series and yarn.",
                  "Click it: the trial is selected in the list below the chart.",
                  "Double-click the line in the list to open the series in Show Experiment."]),
                ("task", "Know whether a comparison is fair",
                 ["Look at the coloured bar above the chart. It checks whether the groups you compare (colours, "
                  "panels or X categories - or the X range) also differ in other conditions that change the Y "
                  "value: material, titer, filaments, yarn type, machine, jet, air pressure, overfeed, speed.",
                  "<b>Green</b>: nothing conspicuous. <b>Yellow</b>: partly fair or few data. <b>Red</b>: the chart "
                  "may show the effect of those conditions rather than of what you compare.",
                  f"{B('Details')} shows every condition: how differently it is spread over the groups and how "
                  f"much it affects Y. {B('Make it fairer')} adds a filter for the part all groups share."],
                 "It also warns about groups with very few trials, groups that come from one single trial series, "
                 "and groups that lie in different X ranges. A warning light, not a proof: only conditions "
                 "recorded in TrippleT are checked."),
                ("h", "Dashboard"),
                ("task", "Build a page with several visuals (like Power BI)",
                 [f"Switch from {B('Chart')} to {B('Dashboard')} at the top.",
                  "Click a visual on the page to select it, or click a type in <i>Visualizations</i> to add a new one "
                  f"({B('+ New visual')} adds an empty one).",
                  "Drag fields from <i>Fields</i> - all tables, grouped and collapsible - into the wells "
                  "(X axis, Y axis, Legend, Small multiples, Rows, Columns, Value). Clicking a field puts it into the "
                  "next free well of the selected visual.",
                  "Drag a visual by its title to move it, drag its lower right corner to make it bigger or "
                  "smaller. Hover it for <i>duplicate</i> and <i>remove</i>.",
                  "Need more room? The <b>›</b> button folds <i>Visualizations</i> or <i>Fields</i> into a narrow strip; "
                  "click the strip to open it again. TrippleT remembers it."],
                 "Visual types: the chart types, plus <i>Matrix</i> (a value per row and column, coloured, gaps = no "
                 "trials yet), <i>Card</i> (one number: count, average, min, max …) and <i>Table</i>. The filters on "
                 "the left apply to every visual; each chart has its own fairness dot."),
                ("task", "Add a slicer (pick values that filter the page)",
                 ["Click the <i>Slicer</i> type in Visualizations and drag a field into <i>Field</i>.",
                  "Choose the <i>Style</i>: <b>List</b> (tick boxes with counts and a search), <b>Dropdown</b> "
                  "(the same, folded), <b>Tiles</b> (buttons), <b>Between</b> (a range with two handles - number "
                  "fields only) or <b>Year › Month</b> (for Year/Month fields: the years fold open, below them the "
                  "months Jan–Dec; click a year for all its months, or single months).",
                  "Switch <i>Multi-select</i> off if only one value may be chosen. <i>Clear selection</i> or "
                  "<i>All</i> takes the selection back.",
                  "<i>Applies to</i>: all visuals of the page (default) or only the ones you tick - they get a dashed "
                  "frame while the slicer is selected."],
                 "A slicer filters all other visuals of the page, other slicers too; its own list always shows "
                 "every value the other filters leave, with the number of trials. The selection is saved with the view."),
                ("task", "Work with several pages",
                 ["The tabs at the bottom are the pages. <b>+</b> adds a page, the copy button duplicates the open "
                  "one, a double-click on a tab renames it, the <b>✕</b> on the open tab deletes it."],
                 "Clicks and slicers only filter the visuals of their own page. All pages are saved in the view."),
                ("task", "Filter one page or one visual only",
                 ["Open the <b>Filters</b> pane (next to Visualizations). It has three parts: <i>On all pages</i> "
                  "(the Find trials filters, with Yarn filters apply to), <i>On this page</i> and <i>On this visual</i> "
                  "(for the selected visual - it then shows a small <i>filter</i> mark).",
                  "Use " + B("+ Add filter") + " in the part you want - same window as in Find trials.",
                  "Click a filter chip to change it, its × to remove it."],
                 "Three levels, like Power BI: Find trials on the left = all pages, then the page, then the visual."),
                ("task", "Make your own number with a formula (calculated field)",
                 [f"In <i>Fields</i> click {B('+ New calculated field')}, give it a name and a unit.",
                  "Build the formula: double-click fields in the list on the right (they appear in [square brackets]) "
                  "and use + − × ÷ ( ) ^ and abs, sqrt, log10, min, max - e.g. [Intermingling Points (FP/m)] / "
                  "[Air Consumption (m3/h)].",
                  "The preview shows how many trials get a value and min / average / max. Click OK."],
                 "The field appears in the <i>Calculated</i> folder and works everywhere: in visuals, slicers and "
                 "filters. Click ✎ next to it to change or delete it. It is saved with the dashboard."),
                ("task", "Set a target",
                 ["Select a card, chart or matrix and enter a <i>Target</i> in Visualizations, with "
                  "<i>higher is better</i> or <i>lower is better</i>."],
                 "Cards turn green or red, charts get a dashed target line, the matrix is coloured green on the "
                 "good side of the target and red on the bad side."),
                ("task", "Drill down (e.g. machine → jet)",
                 ["In a bar, box, violin or line visual, drag one or more fields into <i>Drill down to</i>.",
                  "Double-click a bar: the visual shows the next level for that value. The path is shown in the "
                  "title bar - click ⤴ to go back up."]),
                ("task", "Select points to filter the page",
                 ["In a points chart, drag a rectangle around points. All other visuals show only those trials "
                  "(<i>Selected n trials</i> in Filters).",
                  "Double-click in the chart or remove it in Filters to clear the selection."]),
                ("task", "Start from a template",
                 [f"In Dashboard mode click {B('New')} and choose <i>Empty page</i>, <i>Example page</i> or a "
                  "template: Jet comparison, Yarn overview, Machine check or Lab overview."],
                 "Templates are ordinary pages - change them as you like and save them as your own view."),
                ("task", "Print or share a dashboard (PDF, Excel)",
                 [f"{B('PDF')}: this page or all pages, each on one A4 page with the visuals at their place, the "
                  "filters and the fairness warnings.",
                  f"{B('Excel')}: the data of every visual of the page, one sheet each. The ⤓ button on a visual "
                  "exports only that visual."]),
                ("task", "Let a slicer skip a visual - right on the page",
                 ["Select the slicer. Every other visual shows <i>slicer: on</i> or <i>slicer: off</i> in its title "
                  "bar - click it to switch."],
                 "The same as <i>Applies to</i> in Visualizations."),
                ("task", "Count experiments, series or trials (statistics)",
                 [f"Click {B('New')} → <i>Lab statistics</i> for a ready page, or add the visual <i>Columns</i> "
                  "(or a Card or Matrix) and choose the aggregation <i>Count of experiments</i>, <i>Count of trial "
                  "series</i> or <i>Count of trials</i> - no Value needed.",
                  "Put a field into X axis: e.g. <i>Experiment month</i>, <i>Product group</i>, <i>Order type</i>, "
                  "<i>Owner</i> or <i>Tested on (lab machine)</i>. A field in Legend splits the columns; choose "
                  "<i>Stacked</i>, <i>Side by side</i> or <i>100 % stacked</i> under Bars.",
                  "Months and years run in order, months without anything show as 0."],
                 "Series without trials and experiments without series are counted too. A trial measured on two "
                 "lab machines counts once for each."),
                ("task", "Show only this year, last year or the last 12 months",
                 [f"Add a filter ({B('Add filter')}, or <i>+ Add filter</i> in the Filters pane) on a time field: "
                  "<i>Month</i>, <i>Year</i>, <i>Trial month</i>, <i>Experiment month</i> …",
                  "Under <i>Period</i> choose <i>This year</i>, <i>Last year</i>, <i>Last 12 months</i>, <i>This "
                  "month</i>, <i>Last month</i> - or <i>From – to</i> with a first and a last month."],
                 "These periods move with the calendar: in January <i>This year</i> means the new year, without "
                 "changing the dashboard. Picking single values (e.g. 2026) stays as it is."),
                ("task", "Line up several visuals",
                 ["Ctrl+click (or Shift+click) the visuals you want - they get a dashed green frame. Ctrl+A selects "
                  "all visuals of the page, Esc ends the selection.",
                  "A bar appears above the page: align left, centre, right, top, middle or bottom; same width, height "
                  "or size as the visual you clicked last; distribute horizontally or vertically with equal gaps.",
                  "Drag one of the selected visuals by its title bar and all of them move together. The arrow keys "
                  "move the selected visuals one step."],
                 "Ctrl+Z undoes it."),
                ("task", "Undo a change, see notes",
                 ["Ctrl+Z undoes the last change of the page (layout, fields, filters …), Ctrl+Y redoes it. "
                  "Delete removes the selected visual.",
                  "In a points chart tick <i>Show notes on values</i>: values with a note get a purple ring, the "
                  "note is in the tooltip."]),
                ("task", "Filter all visuals by clicking one",
                 ["Click a bar, a box or a matrix cell. All OTHER visuals of the page show only that value - a blue "
                  "chip at the top says what was clicked.",
                  "Click the same place again, or the blue chip, to undo it."]),
                ("h", "Keeping and sharing"),
                ("task", "Save a chart to open it again later",
                 [f"Click {B('Save view')}, enter a name, tick <i>Share with everybody</i> if others should see it.",
                  f"Open it again with {B('Open view')}.",
                  f"To share it with single people or groups (read, write, admin, superuser): {B('Share…')} - "
                  "each can <i>view</i> or <i>view and edit</i>. Shared dashboards appear on the page "
                  "<i>Dashboards</i>."],
                 "The filters are saved, not the list of trials - a view always shows today's data. "
                 "Only its creator can share it; change it: the creator, people with <i>edit</i> and superusers; "
                 "delete it: the creator or a superuser."),
                ("task", "Export the chart or the list",
                 [f"{B('PDF')}: title, filters, chart and the list of trials.",
                  f"{B('Excel')}: the list of trials in the chart, with a sheet listing the filters."]),
                ("task", "Get the latest data",
                 [f"Click {B('Reload')} or press F5. Your filters and chart settings stay."]),
            ]},
            {"key": "screen", "title": "Screen guide", "blocks": [
                ("areas", [
                    ("Top", "New (start again), Open view, Save view, Excel, Reload (F5), PDF and this help."),
                    ("1 Find trials", "Filter cards, + Add filter, Yarn filters apply to (Any ply / Core only / Effect only) "
                                      "and an overview of the fields you can filter by."),
                    ("Green box", "How many trials match, in how many series, machines and jets - and how many are in the chart."),
                    ("2 Build the chart", "X axis, Y axis, Colour by, Split by; Chart (kind), Colours (palette, Colours…), "
                                          "Options; below it the chart."),
                    ("Trials in the chart", "Every trial in the chart; click a column header to sort, double-click to open."),
                ]),
            ]},
        ],
    },

    # ═══════════════════════════════ DE ═══════════════════════════════
    "de": {
        "window_title": "Wie funktioniert Smart Chart?",
        "close": "Schliessen",
        "tabs": [
            {"key": "tasks", "title": "Wie mache ich…?", "blocks": [
                ("p", "Smart Chart findet Versuche über ihre Eigenschaften - Garn, Maschineneinstellungen, "
                      "Laborwerte - über <b>alle</b> Versuchsserien hinweg und stellt jedes Feld gegen jedes andere dar. "
                      "Zwei Schritte: <b>1 Find trials</b> (links) und <b>2 Build the chart</b> (rechts)."),
                ("h", "1 Versuche finden"),
                ("task", "Z. B. alle Polyester-Versuche mit 70–80 dtex und 30–40 Filamenten finden",
                 [f"Auf {B('+ Add filter')} klicken, <i>Material</i> wählen, <i>PES</i> ankreuzen und {B('Add filter')} klicken.",
                  f"Nochmals {B('+ Add filter')}, <i>End titer</i> wählen, From 70 To 80 eingeben (oder über die "
                  "Balken ziehen) und hinzufügen.",
                  "Dasselbe mit <i>Filaments</i> 30 bis 40."],
                 "Das grüne Feld oben zeigt immer, wie viele Versuche passen und aus wie vielen Serien. "
                 "Referenzmuster sind nie dabei."),
                ("task", "Einen Filter ändern oder entfernen",
                 ["Auf das Filter-Kärtchen klicken, um es zu ändern, oder auf sein <b>×</b>, um es zu entfernen."]),
                ("task", "Nur das Core- (oder Effekt-)Garn betrachten",
                 ["Unter <i>Yarn filters apply to</i> <i>Core only</i> oder <i>Effect only</i> wählen."],
                 "Bei <i>Any ply</i> müssen alle Garnfilter auf <b>dieselbe</b> Ply des Versuchs passen - PES + "
                 "70–80 dtex heisst ein Garn, das beides ist, nicht eine PES-Ply und irgendeine andere 75-dtex-Ply."),
                ("task", "Das Histogramm in „Add filter“ verstehen",
                 ["Die Balken zeigen, wie sich die Werte über die Versuche verteilen, die deine anderen Filter "
                  "übrig lassen. Grüne Balken liegen in deinem Bereich.",
                  "Die Zeile darunter sagt, wie viele Versuche der neue Filter übrig liesse - bevor du ihn hinzufügst."]),
                ("task", "Ein Feld schnell finden",
                 [f"In {B('+ Add filter')} sind die Felder gruppiert (Yarn, Jet, Machine, Lab, General); Klick auf "
                  "eine Gruppe klappt sie auf oder zu.",
                  "Oder einen Teil des Namens bei <i>Search a field…</i> tippen - die passenden Gruppen klappen von selbst auf.",
                  "X axis, Y axis, Colour by und Split by funktionieren gleich: ein Untermenü pro Gruppe."],
                 "Die Gruppe <i>Jet</i> enthält die Daten des im Versuch verwendeten Jets: Luftbohrung, Garnkanal, "
                 "Wirbelkammer, Konus, Titerbereich, Hersteller, Werkstoff und mehr. Alle Labortabellen (Statimat, "
                 "Itemat, DTYoMat, Schrumpf …) liegen im Ordner <i>Lab</i>."),
                ("task", "Nur ganze Zahlen oder nur 1, 1.5, 2 …",
                 ["Ein Zahlenfeld wählen, z. B. Overfeed, und From und To eingeben.",
                  "Darunter <i>Only every</i> 1 (nur ganze Zahlen) oder 0.5 (1, 1.5, 2 …) wählen - oder einen eigenen Schritt tippen.",
                  "Oder <i>Pick values</i> wählen: Jeder Wert, der im Bereich vorkommt, steht mit seiner Anzahl "
                  "Versuche in einer Liste; die gewünschten ankreuzen."],
                 "Das Filter-Kärtchen zeigt es an, z. B. <i>Overfeed 1 – 5 % · every 0.5</i>."),
                ("h", "2 Diagramm bauen"),
                ("task", "Festlegen, was das Diagramm zeigt",
                 ["<i>X axis</i> und <i>Y axis</i> wählen.",
                  "Unter <i>Chart</i> die Art wählen: <i>Points</i>, <i>Points + trend line</i> (gerade Linie pro "
                  "Farbe mit R²), <i>Mean line</i>, <i>Bars</i>, <i>Box plot</i>, <i>Violin</i>, <i>Histogram of Y</i> "
                  "(wie Y verteilt ist, X wird nicht gebraucht) oder <i>Density map</i> (wo die meisten Versuche liegen)."],
                 "Gezeichnet werden nur Versuche mit einem Wert für X und Y; das grüne Feld sagt, wie viele."),
                ("task", "Mit den Farben spielen",
                 ["<i>Colour by</i> mit einem Listenfeld (Jet, Maschine, Material…) gibt jedem Wert eine eigene Farbe; "
                  "ein Zahlenfeld (z. B. Speed) färbt die Punkte entlang einer Farbskala.",
                  "Unter <i>Colours</i> eine Palette wählen, z. B. <i>Heberlein green</i>, <i>Colour-blind safe</i> "
                  "oder <i>Greyscale (print)</i>.",
                  f"Mit {B('Colours…')} für jeden Wert eine eigene Farbe wählen.",
                  f"{B('Options')}: unterschiedliche Formen pro Farbe, logarithmische Achsen, Punktgrösse, dunkler Hintergrund."],
                 "Klick auf einen Legenden-Eintrag blendet ihn aus, Doppelklick zeigt nur diesen. Farben und "
                 "Optionen werden mit der View gespeichert."),
                ("task", "Maschinen (oder Materialien) nebeneinander vergleichen",
                 ["Unter <i>Split by</i> ein Feld wählen, z. B. Machine. Pro Wert entsteht ein kleines Diagramm, "
                  "alle mit denselben Achsen."],
                 "Höchstens 9 Felder werden gezeigt (die häufigsten Werte)."),
                ("task", "Herausfinden, welcher Versuch ein Punkt ist",
                 ["Mit der Maus darauf zeigen: Der Tooltip zeigt Versuch, Serie und Garn.",
                  "Anklicken: Der Versuch wird in der Liste unter dem Diagramm markiert.",
                  "Doppelklick auf die Zeile in der Liste öffnet die Serie in Show Experiment."]),
                ("task", "Erkennen, ob ein Vergleich fair ist",
                 ["Auf die farbige Leiste über dem Diagramm schauen. Sie prüft, ob sich die verglichenen Gruppen "
                  "(Farben, Felder oder X-Kategorien - oder der X-Bereich) auch in anderen Bedingungen "
                  "unterscheiden, die den Y-Wert verändern: Material, Titer, Filamente, Garntyp, Maschine, Jet, "
                  "Luftdruck, Overfeed, Speed.",
                  "<b>Grün</b>: nichts Auffälliges. <b>Gelb</b>: teilweise fair oder wenig Daten. <b>Rot</b>: Das "
                  "Diagramm zeigt womöglich die Wirkung dieser Bedingungen statt dessen, was du vergleichst.",
                  f"{B('Details')} zeigt jede Bedingung: wie ungleich sie auf die Gruppen verteilt ist und wie "
                  f"stark sie Y beeinflusst. {B('Make it fairer')} setzt einen Filter auf den Teil, den alle "
                  "Gruppen gemeinsam haben."],
                 "Gewarnt wird auch bei Gruppen mit sehr wenigen Versuchen, Gruppen aus einer einzigen "
                 "Versuchsserie und Gruppen in verschiedenen X-Bereichen. Eine Warnlampe, kein Beweis: geprüft "
                 "werden nur Bedingungen, die in TrippleT erfasst sind."),
                ("h", "Dashboard"),
                ("task", "Eine Seite mit mehreren Visuals bauen (wie Power BI)",
                 [f"Oben von {B('Chart')} auf {B('Dashboard')} umschalten.",
                  "Ein Visual auf der Seite anklicken, um es auszuwählen, oder in <i>Visualizations</i> auf einen Typ "
                  f"klicken, um ein neues hinzuzufügen ({B('+ New visual')} fügt ein leeres hinzu).",
                  "Felder aus <i>Fields</i> - alle Tabellen, gruppiert und einklappbar - in die Ablagen ziehen (X axis, "
                  "Y axis, Legend, Small multiples, Rows, Columns, Value). Klick auf ein Feld legt es in die nächste "
                  "freie Ablage des ausgewählten Visuals.",
                  "Ein Visual am Titel ziehen, um es zu verschieben, an der Ecke rechts unten ziehen, um es grösser "
                  "oder kleiner zu machen. Mit der Maus darauf zeigen für <i>duplizieren</i> und <i>entfernen</i>.",
                  "Mehr Platz nötig? Der Knopf <b>›</b> klappt <i>Visualizations</i> oder <i>Fields</i> zu einem schmalen "
                  "Streifen zusammen; Klick auf den Streifen öffnet es wieder. TrippleT merkt sich das."],
                 "Visual-Typen: die Diagrammarten, dazu <i>Matrix</i> (ein Wert pro Zeile und Spalte, eingefärbt, "
                 "Lücken = noch keine Versuche), <i>Card</i> (eine Zahl: Anzahl, Mittelwert, Min, Max …) und "
                 "<i>Table</i>. Die Filter links gelten für alle Visuals; jedes Diagramm hat seinen eigenen Fairness-Punkt."),
                ("task", "Einen Slicer (Datenschnitt) hinzufügen",
                 ["In Visualizations den Typ <i>Slicer</i> anklicken und ein Feld nach <i>Field</i> ziehen.",
                  "Den <i>Style</i> wählen: <b>List</b> (Ankreuzliste mit Anzahl und Suche), <b>Dropdown</b> "
                  "(dasselbe, zugeklappt), <b>Tiles</b> (Knöpfe), <b>Between</b> (Bereich mit zwei Griffen - "
                  "nur Zahlenfelder) oder <b>Year › Month</b> (für Jahr-/Monatsfelder: die Jahre klappen auf, "
                  "darunter die Monate Jan–Dec; Klick aufs Jahr wählt alle seine Monate, oder einzelne Monate).",
                  "<i>Multi-select</i> ausschalten, wenn nur ein Wert gewählt werden darf. <i>Clear selection</i> "
                  "oder <i>All</i> hebt die Auswahl auf.",
                  "<i>Applies to</i>: alle Visuals der Seite (Standard) oder nur die angekreuzten - sie bekommen einen "
                  "gestrichelten Rahmen, solange der Slicer ausgewählt ist."],
                 "Ein Slicer filtert alle anderen Visuals der Seite, auch andere Slicer; seine eigene Liste zeigt "
                 "immer alle Werte, die die übrigen Filter zulassen, mit Anzahl Versuche. Die Auswahl wird mit der "
                 "View gespeichert."),
                ("task", "Mit mehreren Seiten arbeiten",
                 ["Die Reiter unten sind die Seiten. <b>+</b> fügt eine Seite hinzu, der Kopier-Knopf dupliziert die "
                  "offene, Doppelklick auf einen Reiter benennt ihn um, das <b>✕</b> am offenen Reiter löscht ihn."],
                 "Klicks und Slicer filtern nur die Visuals ihrer eigenen Seite. Alle Seiten werden mit der View gespeichert."),
                ("task", "Nur eine Seite oder ein Visual filtern",
                 ["Das Pane <b>Filters</b> öffnen (neben Visualizations). Es hat drei Teile: <i>On all pages</i> "
                  "(die Filter aus Find trials, mit Yarn filters apply to), <i>On this page</i> und <i>On this "
                  "visual</i> (für das ausgewählte Visual - es zeigt dann eine kleine <i>filter</i>-Marke).",
                  B("+ Add filter") + " im gewünschten Teil benutzen - dasselbe Fenster wie bei Find trials.",
                  "Klick auf ein Filter-Kärtchen ändert es, sein × entfernt es."],
                 "Drei Ebenen wie in Power BI: Find trials links = alle Seiten, dann die Seite, dann das Visual."),
                ("task", "Eine eigene Kennzahl per Formel (berechnetes Feld)",
                 [f"In <i>Fields</i> auf {B('+ New calculated field')} klicken, Name und Einheit geben.",
                  "Formel bauen: Felder rechts doppelklicken (sie erscheinen in [eckigen Klammern]) und + − × ÷ ( ) ^ "
                  "sowie abs, sqrt, log10, min, max benutzen - z. B. [Intermingling Points (FP/m)] / "
                  "[Air Consumption (m3/h)].",
                  "Die Vorschau zeigt, wie viele Versuche einen Wert bekommen, und Min / Mittel / Max. OK klicken."],
                 "Das Feld erscheint im Ordner <i>Calculated</i> und funktioniert überall: in Visuals, Slicern und "
                 "Filtern. ✎ daneben ändert oder löscht es. Es wird mit dem Dashboard gespeichert."),
                ("task", "Einen Zielwert setzen",
                 ["Card, Diagramm oder Matrix auswählen und in Visualizations einen <i>Target</i> eingeben, mit "
                  "<i>higher is better</i> oder <i>lower is better</i>."],
                 "Cards werden grün oder rot, Diagramme bekommen eine gestrichelte Ziellinie, die Matrix wird auf "
                 "der guten Seite des Ziels grün und auf der schlechten rot eingefärbt."),
                ("task", "Drill-down (z. B. Maschine → Jet)",
                 ["Bei einem Balken-, Box-, Violin- oder Linien-Visual ein oder mehrere Felder nach "
                  "<i>Drill down to</i> ziehen.",
                  "Doppelklick auf einen Balken: Das Visual zeigt die nächste Ebene für diesen Wert. Der Weg steht "
                  "in der Titelzeile - ⤴ geht eine Ebene zurück."]),
                ("task", "Punkte auswählen, um die Seite zu filtern",
                 ["In einer Punktwolke ein Rechteck um Punkte ziehen. Alle anderen Visuals zeigen nur noch diese "
                  "Versuche (<i>Selected n trials</i> in Filters).",
                  "Doppelklick ins Diagramm oder in Filters entfernen hebt die Auswahl auf."]),
                ("task", "Mit einer Vorlage beginnen",
                 [f"Im Dashboard-Modus auf {B('New')} klicken und <i>Empty page</i>, <i>Example page</i> oder eine "
                  "Vorlage wählen: Jet comparison, Yarn overview, Machine check oder Lab overview."],
                 "Vorlagen sind normale Seiten - beliebig anpassen und als eigene View speichern."),
                ("task", "Ein Dashboard drucken oder weitergeben (PDF, Excel)",
                 [f"{B('PDF')}: diese Seite oder alle Seiten, je auf einer A4-Seite mit den Visuals an ihrem Platz, "
                  "den Filtern und den Fairness-Warnungen.",
                  f"{B('Excel')}: die Daten aller Visuals der Seite, je ein Blatt. Der Knopf ⤓ an einem Visual "
                  "exportiert nur dieses."]),
                ("task", "Einen Slicer für ein Visual ausschalten - direkt auf der Seite",
                 ["Den Slicer auswählen. Jedes andere Visual zeigt in seiner Titelzeile <i>slicer: on</i> oder "
                  "<i>slicer: off</i> - anklicken zum Umschalten."],
                 "Dasselbe wie <i>Applies to</i> in Visualizations."),
                ("task", "Experimente, Serien oder Versuche zählen (Statistik)",
                 [f"{B('New')} → <i>Lab statistics</i> für eine fertige Seite - oder das Visual <i>Columns</i> "
                  "(oder Card, Matrix) hinzufügen und als Aggregation <i>Count of experiments</i>, <i>Count of trial "
                  "series</i> oder <i>Count of trials</i> wählen - ohne Value.",
                  "Ein Feld in X axis legen: z.&nbsp;B. <i>Experiment month</i>, <i>Product group</i>, "
                  "<i>Order type</i>, <i>Owner</i> oder <i>Tested on (lab machine)</i>. Ein Feld in Legend teilt die "
                  "Säulen auf; unter Bars <i>Stacked</i>, <i>Side by side</i> oder <i>100 % stacked</i> wählen.",
                  "Monate und Jahre laufen in der richtigen Reihenfolge, Monate ohne Einträge erscheinen als 0."],
                 "Serien ohne Versuche und Experimente ohne Serien zählen mit. Ein Versuch, der auf zwei "
                 "Labormaschinen gemessen wurde, zählt bei beiden."),
                ("task", "Nur dieses Jahr, letztes Jahr oder die letzten 12 Monate zeigen",
                 [f"Einen Filter ({B('Add filter')} oder <i>+ Add filter</i> im Bereich Filters) auf ein Zeitfeld "
                  "setzen: <i>Month</i>, <i>Year</i>, <i>Trial month</i>, <i>Experiment month</i> …",
                  "Unter <i>Period</i> <i>This year</i>, <i>Last year</i>, <i>Last 12 months</i>, <i>This month</i>, "
                  "<i>Last month</i> wählen - oder <i>From – to</i> mit erstem und letztem Monat."],
                 "Diese Zeiträume wandern mit dem Kalender: im Januar heisst <i>This year</i> das neue Jahr, ohne "
                 "dass man das Dashboard ändern muss. Einzelne Werte ankreuzen (z.&nbsp;B. 2026) bleibt fest."),
                ("task", "Mehrere Visuals ausrichten",
                 ["Die gewünschten Visuals mit Strg+Klick (oder Umschalt+Klick) wählen - sie bekommen einen grün "
                  "gestrichelten Rahmen. Strg+A wählt alle Visuals der Seite, Esc beendet die Auswahl.",
                  "Über der Seite erscheint eine Leiste: links, mittig, rechts, oben, Mitte oder unten ausrichten; "
                  "gleiche Breite, Höhe oder Grösse wie das zuletzt angeklickte Visual; horizontal oder vertikal mit "
                  "gleichen Abständen verteilen.",
                  "Ein gewähltes Visual an der Titelzeile ziehen - alle gewählten wandern mit. Die Pfeiltasten "
                  "verschieben die gewählten Visuals um einen Schritt."],
                 "Strg+Z macht es rückgängig."),
                ("task", "Rückgängig machen, Notizen sehen",
                 ["Strg+Z macht die letzte Änderung der Seite rückgängig (Layout, Felder, Filter …), Strg+Y stellt "
                  "sie wieder her. Entf löscht das ausgewählte Visual.",
                  "In einer Punktwolke <i>Show notes on values</i> ankreuzen: Werte mit Notiz bekommen einen "
                  "violetten Ring, die Notiz steht im Tooltip."]),
                ("task", "Alle Visuals durch Klick in eines filtern",
                 ["Auf einen Balken, eine Box oder eine Matrix-Zelle klicken. Alle ANDEREN Visuals der Seite zeigen nur "
                  "noch diesen Wert - ein blaues Kärtchen oben sagt, was angeklickt wurde.",
                  "Nochmals auf dieselbe Stelle oder auf das blaue Kärtchen klicken hebt es auf."]),
                ("h", "Behalten und teilen"),
                ("task", "Ein Diagramm speichern, um es später wieder zu öffnen",
                 [f"Auf {B('Save view')} klicken, einen Namen eingeben, <i>Share with everybody</i> ankreuzen, "
                  "wenn andere es sehen sollen.",
                  f"Mit {B('Open view')} wieder öffnen.",
                  f"Mit einzelnen Personen oder Gruppen (read, write, admin, superuser) teilen: {B('Share…')} - je "
                  "zum <i>Anschauen</i> oder <i>Anschauen und Bearbeiten</i>. Geteilte Dashboards erscheinen auf "
                  "der Seite <i>Dashboards</i>."],
                 "Gespeichert werden die Filter, nicht die Versuchsliste - eine View zeigt immer die aktuellen Daten. "
                 "Teilen kann nur, wer sie erstellt hat; ändern: Ersteller, Personen mit <i>edit</i> und Superuser; "
                 "löschen: Ersteller oder Superuser."),
                ("task", "Diagramm oder Liste exportieren",
                 [f"{B('PDF')}: Titel, Filter, Diagramm und Versuchsliste.",
                  f"{B('Excel')}: die Versuche im Diagramm, mit einem Blatt, das die Filter auflistet."]),
                ("task", "Die neusten Daten holen",
                 [f"Auf {B('Reload')} klicken oder F5 drücken. Filter und Diagramm-Einstellungen bleiben."]),
            ]},
            {"key": "screen", "title": "Bildschirm", "blocks": [
                ("areas", [
                    ("Oben", "New (neu beginnen), Open view, Save view, Excel, Reload (F5), PDF und diese Hilfe."),
                    ("1 Find trials", "Filter-Kärtchen, + Add filter, Yarn filters apply to (Any ply / Core only / "
                                      "Effect only) und eine Übersicht, wonach man filtern kann."),
                    ("Grünes Feld", "Wie viele Versuche passen, aus wie vielen Serien, Maschinen und Jets - und wie "
                                    "viele im Diagramm sind."),
                    ("2 Build the chart", "X axis, Y axis, Colour by, Split by; Chart (Art), Colours (Palette, Colours…), "
                                          "Options; darunter das Diagramm."),
                    ("Trials in the chart", "Alle Versuche im Diagramm; Klick auf den Spaltenkopf sortiert, Doppelklick öffnet."),
                ]),
            ]},
        ],
    },

    # ═══════════════════════════════ ES ═══════════════════════════════
    "es": {
        "window_title": "¿Cómo funciona Smart Chart?",
        "close": "Cerrar",
        "tabs": [
            {"key": "tasks", "title": "¿Cómo hago…?", "blocks": [
                ("p", "Smart Chart encuentra ensayos por sus propiedades - hilo, ajustes de máquina, resultados de "
                      "laboratorio - en <b>todas</b> las series y representa cualquier campo frente a otro. Dos pasos: "
                      "<b>1 Find trials</b> (izquierda) y <b>2 Build the chart</b> (derecha)."),
                ("h", "1 Encontrar ensayos"),
                ("task", "Encontrar p. ej. todos los ensayos de poliéster con 70–80 dtex y 30–40 filamentos",
                 [f"Haz clic en {B('+ Add filter')}, elige <i>Material</i>, marca <i>PES</i> y haz clic en {B('Add filter')}.",
                  f"Otra vez {B('+ Add filter')}, elige <i>End titer</i>, escribe From 70 To 80 (o arrastra sobre "
                  "las barras) y añádelo.",
                  "Lo mismo con <i>Filaments</i> de 30 a 40."],
                 "El recuadro verde de arriba muestra siempre cuántos ensayos coinciden y de cuántas series. "
                 "Las muestras de referencia nunca se incluyen."),
                ("task", "Cambiar o quitar un filtro",
                 ["Haz clic en la tarjeta del filtro para cambiarlo, o en su <b>×</b> para quitarlo."]),
                ("task", "Ver solo el hilo core (o efecto)",
                 ["En <i>Yarn filters apply to</i> elige <i>Core only</i> o <i>Effect only</i>."],
                 "Con <i>Any ply</i>, todos los filtros de hilo deben cumplirse en el <b>mismo</b> ply del ensayo: "
                 "PES + 70–80 dtex significa un hilo que es ambas cosas, no un ply PES y otro ply de 75 dtex."),
                ("task", "Entender el histograma en «Add filter»",
                 ["Las barras muestran cómo se reparten los valores entre los ensayos que dejan tus otros filtros. "
                  "Las barras verdes están dentro de tu rango.",
                  "La línea de abajo indica cuántos ensayos dejaría el nuevo filtro, antes de añadirlo."]),
                ("task", "Encontrar un campo rápidamente",
                 [f"En {B('+ Add filter')} los campos están agrupados (Yarn, Jet, Machine, Lab, General); un clic en "
                  "un grupo lo abre o lo cierra.",
                  "O escribe parte del nombre en <i>Search a field…</i>: los grupos que coinciden se abren solos.",
                  "X axis, Y axis, Colour by y Split by funcionan igual: un submenú por grupo."],
                 "El grupo <i>Jet</i> contiene los datos del jet usado en el ensayo: agujero de aire, canal de hilo, "
                 "cámara de turbulencia, cono, rango de título, fabricante, material y más. Todas las tablas de "
                 "laboratorio (Statimat, Itemat, DTYoMat, encogimiento …) están en la carpeta <i>Lab</i>."),
                ("task", "Solo números enteros, o solo 1, 1.5, 2 …",
                 ["Elige un campo numérico, p. ej. Overfeed, y escribe From y To.",
                  "Debajo elige <i>Only every</i> 1 (solo enteros) o 0.5 (1, 1.5, 2 …), o escribe tu propio paso.",
                  "O elige <i>Pick values</i>: cada valor que aparece en el rango se lista con su número de ensayos; "
                  "marca los que quieras."],
                 "La tarjeta del filtro lo muestra, p. ej. <i>Overfeed 1 – 5 % · every 0.5</i>."),
                ("h", "2 Construir el gráfico"),
                ("task", "Elegir qué muestra el gráfico",
                 ["Elige el <i>X axis</i> y el <i>Y axis</i>.",
                  "Elige el tipo en <i>Chart</i>: <i>Points</i>, <i>Points + trend line</i> (recta por color con R²), "
                  "<i>Mean line</i>, <i>Bars</i>, <i>Box plot</i>, <i>Violin</i>, <i>Histogram of Y</i> (cómo se "
                  "reparte Y, X no se usa) o <i>Density map</i> (dónde están la mayoría de ensayos)."],
                 "Solo se dibujan ensayos con valor para X e Y; el recuadro verde indica cuántos."),
                ("task", "Jugar con los colores",
                 ["<i>Colour by</i> con un campo de lista (Jet, máquina, material…) da a cada valor su propio color; "
                  "un campo numérico (p. ej. Speed) colorea los puntos según una escala.",
                  "Elige una paleta en <i>Colours</i>, p. ej. <i>Heberlein green</i>, <i>Colour-blind safe</i> o "
                  "<i>Greyscale (print)</i>.",
                  f"Con {B('Colours…')} eliges tu propio color para cada valor.",
                  f"{B('Options')}: formas distintas por color, ejes logarítmicos, tamaño de punto, fondo oscuro."],
                 "Clic en una entrada de la leyenda la oculta, doble clic muestra solo esa. Los colores y opciones "
                 "se guardan con la vista."),
                ("task", "Comparar máquinas (o materiales) lado a lado",
                 ["Elige un campo en <i>Split by</i>, p. ej. Machine. Obtienes un gráfico pequeño por valor, todos "
                  "con los mismos ejes."],
                 "Se muestran como máximo 9 paneles (los valores más frecuentes)."),
                ("task", "Saber qué ensayo es un punto",
                 ["Señálalo con el ratón: la descripción muestra ensayo, serie e hilo.",
                  "Haz clic: el ensayo se marca en la lista bajo el gráfico.",
                  "Doble clic en la línea de la lista abre la serie en Show Experiment."]),
                ("task", "Saber si una comparación es justa",
                 ["Mira la barra de color sobre el gráfico. Comprueba si los grupos que comparas (colores, paneles "
                  "o categorías de X, o el rango de X) también se diferencian en otras condiciones que cambian el "
                  "valor Y: material, título, filamentos, tipo de hilo, máquina, jet, presión de aire, overfeed, "
                  "velocidad.",
                  "<b>Verde</b>: nada llamativo. <b>Amarillo</b>: parcialmente justa o pocos datos. <b>Rojo</b>: el "
                  "gráfico puede mostrar el efecto de esas condiciones en lugar de lo que comparas.",
                  f"{B('Details')} muestra cada condición: lo desigual que está repartida entre los grupos y cuánto "
                  f"influye en Y. {B('Make it fairer')} añade un filtro para la parte que comparten todos los grupos."],
                 "También avisa de grupos con muy pocos ensayos, grupos de una sola serie y grupos en rangos de X "
                 "distintos. Es una luz de aviso, no una prueba: solo se comprueban condiciones registradas en TrippleT."),
                ("h", "Dashboard"),
                ("task", "Construir una página con varios visuales (como Power BI)",
                 [f"Arriba cambia de {B('Chart')} a {B('Dashboard')}.",
                  "Haz clic en un visual de la página para seleccionarlo, o en un tipo en <i>Visualizations</i> para "
                  f"añadir uno nuevo ({B('+ New visual')} añade uno vacío).",
                  "Arrastra campos desde <i>Fields</i> (todas las tablas, agrupadas y plegables) a los huecos (X axis, "
                  "Y axis, Legend, Small multiples, Rows, Columns, Value). Un clic en un campo lo pone en el siguiente "
                  "hueco libre del visual seleccionado.",
                  "Arrastra un visual por su título para moverlo y por la esquina inferior derecha para cambiar su "
                  "tamaño. Pasa el ratón por encima para <i>duplicar</i> y <i>quitar</i>.",
                  "¿Necesitas más espacio? El botón <b>›</b> pliega <i>Visualizations</i> o <i>Fields</i> en una franja "
                  "estrecha; un clic en la franja lo vuelve a abrir. TrippleT lo recuerda."],
                 "Tipos: los tipos de gráfico, más <i>Matrix</i> (un valor por fila y columna, coloreado; huecos = aún "
                 "sin ensayos), <i>Card</i> (un número: cantidad, media, mín., máx. …) y <i>Table</i>. Los filtros de la "
                 "izquierda valen para todos los visuales; cada gráfico tiene su propio punto de equidad."),
                ("task", "Añadir un slicer (segmentación de datos)",
                 ["Haz clic en el tipo <i>Slicer</i> en Visualizations y arrastra un campo a <i>Field</i>.",
                  "Elige el <i>Style</i>: <b>List</b> (casillas con cantidades y búsqueda), <b>Dropdown</b> (lo "
                  "mismo, plegado), <b>Tiles</b> (botones), <b>Between</b> (un rango con dos tiradores, solo "
                  "campos numéricos) o <b>Year › Month</b> (para campos de año/mes: los años se despliegan y debajo "
                  "están los meses Jan–Dec; clic en un año elige todos sus meses, o meses sueltos).",
                  "Desactiva <i>Multi-select</i> si solo se puede elegir un valor. <i>Clear selection</i> o <i>All</i> "
                  "quita la selección.",
                  "<i>Applies to</i>: todos los visuales de la página (por defecto) o solo los que marques; se ven "
                  "con un marco discontinuo mientras el slicer está seleccionado."],
                 "Un slicer filtra todos los demás visuales de la página, también otros slicers; su propia lista "
                 "muestra siempre todos los valores que dejan los demás filtros, con el número de ensayos. La "
                 "selección se guarda con la vista."),
                ("task", "Trabajar con varias páginas",
                 ["Las pestañas de abajo son las páginas. <b>+</b> añade una página, el botón de copia duplica la "
                  "abierta, doble clic en una pestaña la renombra, la <b>✕</b> de la pestaña abierta la borra."],
                 "Los clics y slicers solo filtran los visuales de su propia página. Todas las páginas se guardan con la vista."),
                ("task", "Filtrar solo una página o un visual",
                 ["Abre el panel <b>Filters</b> (junto a Visualizations). Tiene tres partes: <i>On all pages</i> "
                  "(los filtros de Find trials, con Yarn filters apply to), <i>On this page</i> y <i>On this visual</i> "
                  "(para el visual seleccionado, que muestra una pequeña marca <i>filter</i>).",
                  "Usa " + B("+ Add filter") + " en la parte que quieras: la misma ventana que en Find trials.",
                  "Clic en una etiqueta de filtro para cambiarla, en su × para quitarla."],
                 "Tres niveles como en Power BI: Find trials a la izquierda = todas las páginas, luego la página, luego el visual."),
                ("task", "Crear un valor propio con una fórmula (campo calculado)",
                 [f"En <i>Fields</i> haz clic en {B('+ New calculated field')}, dale nombre y unidad.",
                  "Construye la fórmula: doble clic en los campos de la derecha (aparecen entre [corchetes]) y usa "
                  "+ − × ÷ ( ) ^ y abs, sqrt, log10, min, max, p. ej. [Intermingling Points (FP/m)] / "
                  "[Air Consumption (m3/h)].",
                  "La vista previa muestra cuántos ensayos obtienen un valor y mín. / media / máx. Haz clic en OK."],
                 "El campo aparece en la carpeta <i>Calculated</i> y funciona en todas partes: visuales, slicers y "
                 "filtros. ✎ al lado lo cambia o borra. Se guarda con el dashboard."),
                ("task", "Fijar un objetivo",
                 ["Selecciona una card, un gráfico o una matriz y escribe un <i>Target</i> en Visualizations, con "
                  "<i>higher is better</i> o <i>lower is better</i>."],
                 "Las cards se ponen verdes o rojas, los gráficos reciben una línea de objetivo discontinua y la "
                 "matriz se colorea en verde en el lado bueno del objetivo y en rojo en el malo."),
                ("task", "Profundizar (p. ej. máquina → jet)",
                 ["En un visual de barras, caja, violín o línea, arrastra uno o varios campos a <i>Drill down to</i>.",
                  "Doble clic en una barra: el visual muestra el siguiente nivel para ese valor. El camino aparece "
                  "en la barra de título; ⤴ vuelve un nivel."]),
                ("task", "Seleccionar puntos para filtrar la página",
                 ["En un gráfico de puntos, arrastra un rectángulo alrededor de puntos. Los demás visuales muestran "
                  "solo esos ensayos (<i>Selected n trials</i> en Filters).",
                  "Doble clic en el gráfico o quitarlo en Filters elimina la selección."]),
                ("task", "Empezar desde una plantilla",
                 [f"En modo Dashboard haz clic en {B('New')} y elige <i>Empty page</i>, <i>Example page</i> o una "
                  "plantilla: Jet comparison, Yarn overview, Machine check o Lab overview."],
                 "Las plantillas son páginas normales: cámbialas como quieras y guárdalas como tu propia vista."),
                ("task", "Imprimir o compartir un dashboard (PDF, Excel)",
                 [f"{B('PDF')}: esta página o todas, cada una en una página A4 con los visuales en su sitio, los "
                  "filtros y los avisos de equidad.",
                  f"{B('Excel')}: los datos de todos los visuales de la página, una hoja por visual. El botón ⤓ de "
                  "un visual exporta solo ese."]),
                ("task", "Hacer que un slicer no afecte a un visual, en la página",
                 ["Selecciona el slicer. Cada otro visual muestra <i>slicer: on</i> o <i>slicer: off</i> en su "
                  "barra de título; haz clic para cambiarlo."],
                 "Lo mismo que <i>Applies to</i> en Visualizations."),
                ("task", "Contar experimentos, series o ensayos (estadística)",
                 [f"{B('New')} → <i>Lab statistics</i> para una página lista, o añade el visual <i>Columns</i> "
                  "(o Card, Matrix) y elige la agregación <i>Count of experiments</i>, <i>Count of trial series</i> "
                  "o <i>Count of trials</i>; no hace falta Value.",
                  "Pon un campo en X axis: p.&nbsp;ej. <i>Experiment month</i>, <i>Product group</i>, "
                  "<i>Order type</i>, <i>Owner</i> o <i>Tested on (lab machine)</i>. Un campo en Legend divide las "
                  "columnas; en Bars elige <i>Stacked</i>, <i>Side by side</i> o <i>100 % stacked</i>.",
                  "Meses y años van en orden; los meses sin nada aparecen como 0."],
                 "También cuentan las series sin ensayos y los experimentos sin series. Un ensayo medido en dos "
                 "máquinas cuenta en ambas."),
                ("task", "Mostrar solo este año, el año pasado o los últimos 12 meses",
                 [f"Añade un filtro ({B('Add filter')} o <i>+ Add filter</i> en el panel Filters) sobre un campo de "
                  "tiempo: <i>Month</i>, <i>Year</i>, <i>Trial month</i>, <i>Experiment month</i> …",
                  "En <i>Period</i> elige <i>This year</i>, <i>Last year</i>, <i>Last 12 months</i>, <i>This "
                  "month</i>, <i>Last month</i>, o <i>From – to</i> con un primer y un último mes."],
                 "Estos periodos avanzan con el calendario: en enero <i>This year</i> es el año nuevo, sin cambiar el "
                 "dashboard. Marcar valores sueltos (p.&nbsp;ej. 2026) queda fijo."),
                ("task", "Alinear varios visuales",
                 ["Ctrl+clic (o Mayús+clic) en los visuales deseados: reciben un marco verde discontinuo. Ctrl+A "
                  "selecciona todos los visuales de la página, Esc termina la selección.",
                  "Aparece una barra encima de la página: alinear a la izquierda, centro, derecha, arriba, medio o "
                  "abajo; mismo ancho, alto o tamaño que el último visual pulsado; distribuir horizontal o "
                  "verticalmente con espacios iguales.",
                  "Arrastra uno de los visuales seleccionados por su barra de título y se mueven todos juntos. Las "
                  "flechas mueven los visuales seleccionados un paso."],
                 "Ctrl+Z lo deshace."),
                ("task", "Deshacer un cambio, ver notas",
                 ["Ctrl+Z deshace el último cambio de la página (diseño, campos, filtros …), Ctrl+Y lo rehace. "
                  "Supr borra el visual seleccionado.",
                  "En un gráfico de puntos marca <i>Show notes on values</i>: los valores con nota reciben un anillo "
                  "violeta y la nota aparece en la descripción."]),
                ("task", "Filtrar todos los visuales haciendo clic en uno",
                 ["Haz clic en una barra, una caja o una celda de la matriz. Todos los DEMÁS visuales muestran solo ese "
                  "valor; una etiqueta azul arriba indica lo que se pulsó.",
                  "Otro clic en el mismo sitio o en la etiqueta azul lo deshace."]),
                ("h", "Guardar y compartir"),
                ("task", "Guardar un gráfico para abrirlo más tarde",
                 [f"Haz clic en {B('Save view')}, escribe un nombre y marca <i>Share with everybody</i> si otros "
                  "deben verlo.",
                  f"Ábrelo de nuevo con {B('Open view')}.",
                  f"Para compartirlo con personas o grupos (read, write, admin, superuser): {B('Share…')}, cada uno "
                  "para <i>ver</i> o <i>ver y editar</i>. Los dashboards compartidos aparecen en la página "
                  "<i>Dashboards</i>."],
                 "Se guardan los filtros, no la lista de ensayos: una vista siempre muestra los datos actuales. "
                 "Solo el creador puede compartirla; cambiarla: el creador, quien tiene <i>edit</i> y los "
                 "superusuarios; borrarla: el creador o un superusuario."),
                ("task", "Exportar el gráfico o la lista",
                 [f"{B('PDF')}: título, filtros, gráfico y lista de ensayos.",
                  f"{B('Excel')}: los ensayos del gráfico, con una hoja que lista los filtros."]),
                ("task", "Obtener los datos más recientes",
                 [f"Haz clic en {B('Reload')} o pulsa F5. Los filtros y ajustes del gráfico se mantienen."]),
            ]},
            {"key": "screen", "title": "Pantalla", "blocks": [
                ("areas", [
                    ("Arriba", "New (empezar de nuevo), Open view, Save view, Excel, Reload (F5), PDF y esta ayuda."),
                    ("1 Find trials", "Tarjetas de filtro, + Add filter, Yarn filters apply to (Any ply / Core only / "
                                      "Effect only) y un resumen de los campos por los que se puede filtrar."),
                    ("Recuadro verde", "Cuántos ensayos coinciden, de cuántas series, máquinas y jets, y cuántos están "
                                       "en el gráfico."),
                    ("2 Build the chart", "X axis, Y axis, Colour by, Split by; Chart (tipo), Colours (paleta, Colours…), "
                                          "Options; debajo, el gráfico."),
                    ("Trials in the chart", "Todos los ensayos del gráfico; clic en la cabecera ordena, doble clic abre."),
                ]),
            ]},
        ],
    },
}
