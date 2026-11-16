# ui/widgets/help_texts_smart_chart.py
"""Hilfetexte Smart Chart (EN/DE/ES/ZH) fuer ui/widgets/multilang_help.py.

Spiegelt ui/screen_smart_chart.py: seit 2026-11-02 nur noch das Dashboard
(ui/smart_dashboard*.py); "1 Find trials" = Filter auf allen Seiten in der
Filters-Leiste ("+ Add filter" -> ui/smart_chart_filter_dialog.py). Bei
Aenderungen dort hier (alle 4 Sprachen) nachziehen.
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
                      "<b>all</b> trial series and shows them in a dashboard like Power BI: pages with charts, cards, "
                      "tables and slicers. The <b>filters on all pages</b> (Filters pane, right) decide which trials "
                      "take part."),
                ("h", "1 Find trials"),
                ("task", "Find e.g. all polyester trials with 70–80 dtex and 30–40 filaments",
                 [f"Click {B('+ Add filter')}, choose <i>Material</i>, tick <i>PES</i> and click {B('Add filter')}.",
                  f"Click {B('+ Add filter')} again, choose <i>End titer</i>, enter From 70 To 80 (or drag across the "
                  "bars) and add it.",
                  "Do the same with <i>Filaments</i> 30 to 40."],
                 "The green box at the top always shows how many trials match, in how many series. "
                 "Reference samples are never included."),
                ("task", "Change or remove a filter",
                 ["In the Filters pane under <i>On all pages</i>, click a filter to change it, or its <b>×</b> to "
                  "remove it."]),
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
                  "The <i>Fields</i> pane of the dashboard is grouped the same way and has its own search box."],
                 "The <i>Jet</i> group has the data of the jet used in the trial: air hole, yarn channel, swirl "
                 "chamber, cone, titer range, maker, material and more. All lab tables (Statimat, Itemat, DTYoMat, "
                 "shrinkage …) are in the <i>Lab</i> folder."),
                ("task", "Only whole numbers, or only 1, 1.5, 2 …",
                 ["Choose a number field, e.g. Overfeed, and enter From and To.",
                  "Below, choose <i>Only every</i> 1 (whole numbers only) or 0.5 (1, 1.5, 2 …) - or type your own step.",
                  "Or choose <i>Pick values</i>: every value that occurs in the range is listed with its number of "
                  "trials; tick the ones you want."],
                 "The filter card shows it, e.g. <i>Overfeed 1 – 5 % · every 0.5</i>."),
                ("h", "2 Read the charts"),
                ("task", "Compare machines (or materials) side by side",
                 ["Drag a field into <i>Small multiples</i>, e.g. Machine. You get one small chart per value, all "
                  "with the same axes."],
                 "At most 9 panels are shown (the most frequent values). Click a legend entry to hide it, "
                 "double-click to show only that one."),
                ("task", "Find out which trial a point is",
                 ["Point at it: the tooltip shows trial, series and yarn.",
                  "Click ⤢ in the title bar of the visual (Focus): below the chart is the list of its trials. "
                  "Click a point to find its line, double-click the line to open the series in Show Experiment."]),
                ("task", "Know whether a comparison is fair",
                 ["Look at the coloured dot in the title bar of a chart. It checks whether the groups you compare "
                  "(colours, panels or X categories - or the X range) also differ in other conditions that change "
                  "the Y value: material, titer, filaments, yarn type, machine, jet, air pressure, overfeed, speed.",
                  "<b>Green</b>: nothing conspicuous. <b>Yellow</b>: partly fair or few data. <b>Red</b>: the chart "
                  "may show the effect of those conditions rather than of what you compare.",
                  "Click the dot for the details: every condition, how differently it is spread over the groups and "
                  "how much it affects Y. <i>Make it fairer</i> adds a filter to this visual for the part all groups "
                  "share."],
                 "It also warns about groups with very few trials, groups that come from one single trial series, "
                 "and groups that lie in different X ranges. A warning light, not a proof: only conditions "
                 "recorded in TrippleT are checked."),
                ("h", "Dashboard"),
                ("task", "Build a page with several visuals (like Power BI)",
                 ["Smart Chart opens straight in the dashboard (<i>Report</i> at the top left).",
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
                ("task", "Add an average line, ± standard deviations or spec limits (Analytics)",
                 ["Select a chart and click <i>Analytics</i> in Visualizations (next to Build and Format).",
                  "Choose <i>+ Add a line…</i>: Average, Median, Mean ± 1/2/3 SD, Percentile, Min, Max, a "
                  "<i>Constant line</i> or a <i>Band</i> from - to (e.g. the spec limits).",
                  "Give it a label and a colour if you like; × removes it."],
                 "Average, median and the others are calculated from the single trials in the chart, in each small "
                 "multiple separately (for Columns from the columns). Works for bars, box, violin, line, points, "
                 "trend, histogram, columns and control charts. Copy format does not copy these lines."),
                ("task", "Jump to a detail page for one machine, jet … (drill-through)",
                 ["Make the detail page: open it, in <i>Filters</i> under <i>Drill-through to this page</i> "
                  "choose the field, e.g. <i>Machine</i>.",
                  "On another page, right-click a bar, box, matrix cell or pie slice of a visual that uses "
                  "Machine and choose the page under <i>Drill through</i>.",
                  "The detail page shows only that machine. <i>← Back to …</i> returns, <i>Clear</i> shows the "
                  "page without the drill-through filter."],
                 "With <i>Keep all filters of the clicked visual</i> (standard) the page, visual, click and slicer "
                 "filters of the clicked visual come along too. The drill-through is not saved with the dashboard. "
                 "Works on the Dashboards page as well."),
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
                ("task", "Count how many different jets, yarns … were run",
                 ["Add a <i>Card</i> and choose the aggregation <i>Count (distinct)</i>.",
                  "Drag the field into Value, e.g. <i>Jet</i>, <i>Yarn</i> or <i>Machine</i> - any field works "
                  "here, not only numbers.",
                  "The card counts the different values of the trials that are left after all filters, slicers "
                  "and clicks. With <i>Columns</i> or <i>Matrix</i> you get the number per category, e.g. "
                  "different jets per year."],
                 "Empty values (no jet recorded) do not count."),
                ("task", "List which jets, yarns … they are - one line each",
                 ["Add a <i>Table</i> and drag the field into Columns, e.g. <i>Jet</i>.",
                  "In Build, tick <i>One row per value (e.g. a list of the jets)</i>. The table now shows each jet "
                  "once, with the number of <i>Trials</i> and <i>Series</i>.",
                  "Add more fields if you like: a second text field (e.g. <i>Machine</i>) gives one line per "
                  "combination, a number field (e.g. FP/m) shows its average per line. Click a column heading "
                  "to sort."],
                 "Within the same filters, the table has as many lines as a Card with <i>Count (distinct)</i> "
                 "counts. Trials without a value are left out (a note below the table says how many)."),
                ("task", "Show how parts add up, e.g. A, B and C knots per trial",
                 ["Add the visual <i>Stacked fields</i> (columns with three colours in Visualizations).",
                  "Drag the number fields into <i>Values</i> - e.g. DTYoMat <i>AKnots</i>, <i>BKnots</i>, "
                  "<i>CKnots</i>. Each becomes one colour of the column.",
                  "Drag <i>Trial</i> (General) into <i>X axis</i> for one column per trial - or a series, machine, "
                  "jet … to compare groups. Without X you get one column for all trials.",
                  "Under <i>Bars</i>: <i>100 % stacked</i> (default, the share of each part), <i>Stacked</i> (the "
                  "values) or <i>Side by side</i>.",
                  "Combo chart: drag one or more number fields into <i>Line (right axis)</i> - e.g. <i>FP/m "
                  "DTYoMat</i>. They are drawn as lines with their own axis on the right."],
                 "Filter to one series first (Filters or a slicer), then the columns are labelled V1, V2 …"),
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
                ("task", "Format a visual: order, Top N, decimals, labels, colours, axes, legend",
                 ["Click the visual, then the tab <i>Format</i> at the top of Visualizations (<i>Build</i> brings "
                  "back the fields). Click the empty page or press Esc to select nothing.",
                  "<i>Sort and Top N</i>: order by value (high to low, low to high) or by name, and show only the "
                  "top 5, 10 … - e.g. the best 10 jets. The note under the chart says how many are left out.",
                  "<i>Numbers</i>: decimal places for the axis, the card, the matrix and the values on the chart. "
                  "<i>Data labels</i>: show the values on bars and lines, or switch them off. <i>Error bars</i> (Bars, Mean line): <i>Standard deviation</i> (how much the trials scatter), <i>95 % confidence</i> (where the true mean lies - if two bars hardly overlap, the difference is probably real; with few trials it gets wide, and with one trial there is none), <i>Min – Max</i> (worst and best trial) or <i>Off</i>.",
                  "<i>Axes</i>: your own title, or <i>hide</i>; fix where the Y axis starts and ends (one or both). "
                  "<i>Legend</i>: right, top, bottom or off.",
                  "<i>Colours</i>: another palette, or click the colour box next to a value to pick your own "
                  "(× goes back). Matrix: the colour scale. <i>Text and grid</i>: text size, grid lines on or off.",
                  "Card: size of the number, show or hide the unit and the line below. Table: click a column "
                  "heading to sort (again = the other way round); <i>+ Add colour rule</i> colours cells, e.g. "
                  "FP/m greater than 100 green, Machine is SSM red.",
                  "Every change shows at once. A green dot marks what differs from the standard; <i>Reset</i> sets "
                  "one section back, <i>Reset all</i> the whole visual.",
                  "<b>Dashboard theme</b>: click the empty page (nothing selected), then <i>Format</i>. Palette, "
                  "text size, grid lines, decimals, values on bars and legend there apply to every visual on every "
                  "page; a visual's own Format wins. In a visual, <i>Dashboard: …</i> shows what the theme gives.",
                  "<b>Copy a format</b>: click the visual with the right format, then <i>Copy format</i> at the top "
                  "of the page (next to + New visual), then the visual that should get it. A double-click on "
                  "<i>Copy format</i> keeps it on for several visuals - Esc ends it. Axis titles and ranges are not "
                  "copied - they belong to the fields.",
                  "<i>Points and lines</i>: a different shape per colour, the point size. <i>Axes</i>: also "
                  "logarithmic X / Y axes."],
                 "PDF and the Dashboards page show the visual the same way. Ctrl+Z undoes a change."),
                ("task", "Look at one visual big, with its trials (Focus)",
                 ["Point at a visual and click ⤢ in its title bar.",
                  "The visual fills the page; below it are all trials it is made of, with the fields you used. Click "
                  "a point to find its line, click a line to light up its point, double-click a line to open the "
                  "trial in Show Experiment.",
                  "<i>Back to the page</i> or Esc goes back. A click on the coloured dot in a title bar shows the "
                  "fairness details, with <i>Make it fairer</i>."],
                 "Works on the Dashboards page too."),
                ("task", "Pie, donut, control chart, radar, text",
                 ["<i>Pie / donut</i>: drag a field into Legend - it counts trials (or series, experiments), or "
                  "drag a number into Value and choose Sum. <i>Shape</i> in Build: Pie or Donut (the total stands "
                  "in the middle). Click a piece to filter the page.",
                  "<i>Control chart</i>: a number into Y axis. The trials run in order of series and trial number - "
                  "or of the field in X axis (e.g. Trial month). Lines: mean and the limits ±3σ; red = outside the "
                  "limits, amber = 7 or more in a row on one side of the mean.",
                  "<i>Radar</i>: three or more number fields into Values, a field into Legend (jet, yarn, machine …). "
                  "Each axis runs from the lowest group (inside) to the highest (outside); the real values are in "
                  "the tooltip.",
                  "<i>Text</i>: write in Build. A line starting with # is a heading, **text** is bold."],
                 "All of them are in the PDF too."),
                ("task", "See how the tables hang together (Model)",
                 ["Click <i>Model</i> at the top left of the dashboard (<i>Report</i> brings the pages back).",
                  "The trial is in the middle; on the left what it refers to (yarn, jet, experiment, time, machine), "
                  "on the right the lab tables. 1 : n = several rows per trial, averaged; n : 1 = many trials share "
                  "one row.",
                  "Click a table: what it holds, how a value per trial comes about, and per field how many trials "
                  "have a value."],
                 "Read only - nobody can change the links there."),
                ("task", "Make the side panes wider or narrower",
                 ["Drag the left edge of Filters, Visualizations or Fields. A double-click on the edge gives the "
                  "standard width back; › folds a pane away."],
                 "TrippleT remembers the widths for you."),
                ("task", "Undo a change, see notes",
                 ["Ctrl+Z undoes the last change of the page (layout, fields, filters …), Ctrl+Y redoes it. "
                  "Delete removes the selected visual.",
                  "In a points chart tick <i>Show notes on values</i>: values with a note get a purple ring, the "
                  "note is in the tooltip."]),
                ("task", "Highlight in all visuals by clicking one",
                 ["Click a bar, a column, a slice, a box or a matrix cell - a blue chip at the top says what was clicked.",
                  "Bars, columns, pies, points, mean lines and control charts keep all their trials and grey out the "
                  "rest (the clicked visual too). Columns show the highlighted part inside each column, bars of averages "
                  "the average of the highlighted trials on top of the faded bar.",
                  "Cards, matrix, table, radar, box, violin, histogram and slicers show only the clicked value.",
                  "Click the same place again, or the blue chip, to undo it.",
                  "To filter all visuals instead: Format with nothing selected → <i>Clicks</i> → "
                  "<i>Filters the other visuals</i>."]),
                ("h", "Keeping and sharing"),
                ("task", "Save a dashboard to open it again later",
                 [f"Click {B('Save view')}, enter a name, tick <i>Share with everybody</i> if others should see it.",
                  f"Open it again with {B('Open view')}.",
                  f"To share it with single people or groups (read, write, admin, superuser): {B('Share…')} - "
                  "each can <i>view</i> or <i>view and edit</i>. Shared dashboards appear on the page "
                  "<i>Dashboards</i>."],
                 "The filters are saved, not the list of trials - a view always shows today's data. "
                 "Only its creator can share it; change it: the creator, people with <i>edit</i> and superusers; "
                 "delete it: the creator or a superuser."),
                ("task", "Get the latest data",
                 [f"Click {B('Reload')} or press F5. Your filters and the dashboard stay."]),
            ]},
            {"key": "screen", "title": "Screen guide", "blocks": [
                ("areas", [
                    ("Top", "New (empty page, example or template), Open view, Save view, Share…, Excel, Reload (F5), "
                            "PDF and this help."),
                    ("Green box", "How many trials match the filters on all pages, in how many series, machines and jets."),
                    ("Page", "Report | Model, page name, + New visual, Copy format; the visuals; the page tabs at the "
                             "bottom."),
                    ("Filters", "On all pages (= find trials, Yarn filters apply to), on this page, on this visual, "
                                "clicks and slicers."),
                    ("Visualizations", "The visual types; Build (fields, options) and Format (sort, numbers, colours, "
                                       "axes …) of the selected visual - or the dashboard theme."),
                    ("Fields", "All fields of all tables in folders, with a search box and + New calculated field."),
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
                      "Laborwerte - über <b>alle</b> Versuchsserien hinweg und zeigt sie in einem Dashboard wie Power BI: "
                      "Seiten mit Diagrammen, Cards, Tabellen und Slicern. Die <b>Filter auf allen Seiten</b> "
                      "(Filters-Leiste rechts) bestimmen, welche Versuche dabei sind."),
                ("h", "1 Versuche finden"),
                ("task", "Z. B. alle Polyester-Versuche mit 70–80 dtex und 30–40 Filamenten finden",
                 [f"Auf {B('+ Add filter')} klicken, <i>Material</i> wählen, <i>PES</i> ankreuzen und {B('Add filter')} klicken.",
                  f"Nochmals {B('+ Add filter')}, <i>End titer</i> wählen, From 70 To 80 eingeben (oder über die "
                  "Balken ziehen) und hinzufügen.",
                  "Dasselbe mit <i>Filaments</i> 30 bis 40."],
                 "Das grüne Feld oben zeigt immer, wie viele Versuche passen und aus wie vielen Serien. "
                 "Referenzmuster sind nie dabei."),
                ("task", "Einen Filter ändern oder entfernen",
                 ["In der Filters-Leiste unter <i>On all pages</i> auf einen Filter klicken, um ihn zu ändern, oder "
                  "auf sein <b>×</b>, um ihn zu entfernen."]),
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
                  "Die <i>Fields</i>-Leiste des Dashboards ist gleich gruppiert und hat ein eigenes Suchfeld."],
                 "Die Gruppe <i>Jet</i> enthält die Daten des im Versuch verwendeten Jets: Luftbohrung, Garnkanal, "
                 "Wirbelkammer, Konus, Titerbereich, Hersteller, Werkstoff und mehr. Alle Labortabellen (Statimat, "
                 "Itemat, DTYoMat, Schrumpf …) liegen im Ordner <i>Lab</i>."),
                ("task", "Nur ganze Zahlen oder nur 1, 1.5, 2 …",
                 ["Ein Zahlenfeld wählen, z. B. Overfeed, und From und To eingeben.",
                  "Darunter <i>Only every</i> 1 (nur ganze Zahlen) oder 0.5 (1, 1.5, 2 …) wählen - oder einen eigenen Schritt tippen.",
                  "Oder <i>Pick values</i> wählen: Jeder Wert, der im Bereich vorkommt, steht mit seiner Anzahl "
                  "Versuche in einer Liste; die gewünschten ankreuzen."],
                 "Das Filter-Kärtchen zeigt es an, z. B. <i>Overfeed 1 – 5 % · every 0.5</i>."),
                ("h", "2 Diagramme lesen"),
                ("task", "Maschinen (oder Materialien) nebeneinander vergleichen",
                 ["Ein Feld in <i>Small multiples</i> ziehen, z.&nbsp;B. Machine. Es gibt ein kleines Diagramm pro "
                  "Wert, alle mit denselben Achsen."],
                 "Höchstens 9 Felder werden gezeigt (die häufigsten Werte). Klick auf einen Legendeneintrag blendet "
                 "ihn aus, Doppelklick zeigt nur diesen."),
                ("task", "Herausfinden, welcher Versuch ein Punkt ist",
                 ["Mit der Maus darauf zeigen: der Tooltip nennt Versuch, Serie und Garn.",
                  "In der Titelzeile des Visuals auf ⤢ klicken (Focus): unter dem Diagramm steht die Liste seiner "
                  "Versuche. Klick auf einen Punkt zeigt seine Zeile, Doppelklick auf die Zeile öffnet die Serie in "
                  "Show Experiment."]),
                ("task", "Erkennen, ob ein Vergleich fair ist",
                 ["Auf den farbigen Punkt in der Titelzeile eines Diagramms achten. Er prüft, ob sich die "
                  "verglichenen Gruppen (Farben, Felder oder X-Kategorien - oder der X-Bereich) auch in anderen "
                  "Bedingungen unterscheiden, die den Y-Wert verändern: Material, Titer, Filamente, Garntyp, "
                  "Maschine, Jet, Luftdruck, Voreilung, Geschwindigkeit.",
                  "<b>Grün</b>: nichts Auffälliges. <b>Gelb</b>: teilweise fair oder wenig Daten. <b>Rot</b>: das "
                  "Diagramm zeigt womöglich eher die Wirkung dieser Bedingungen als die des Verglichenen.",
                  "Klick auf den Punkt zeigt die Details: jede Bedingung, wie unterschiedlich sie auf die Gruppen "
                  "verteilt ist und wie stark sie Y beeinflusst. <i>Make it fairer</i> setzt einen Filter auf dieses "
                  "Visual für den Teil, den alle Gruppen gemeinsam haben."],
                 "Er warnt auch bei Gruppen mit sehr wenigen Versuchen, Gruppen aus einer einzigen Versuchsserie und "
                 "Gruppen in verschiedenen X-Bereichen. Eine Warnlampe, kein Beweis: geprüft wird nur, was in "
                 "TrippleT erfasst ist."),
                ("h", "Dashboard"),
                ("task", "Eine Seite mit mehreren Visuals bauen (wie Power BI)",
                 ["Smart Chart öffnet direkt das Dashboard (<i>Report</i> oben links).",
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
                ("task", "Mittelwertlinie, ± Standardabweichungen oder Spezifikationsgrenzen einzeichnen (Analytics)",
                 ["Ein Diagramm anklicken und in Visualizations <i>Analytics</i> wählen (neben Build und Format).",
                  "<i>+ Add a line…</i> wählen: Average, Median, Mittelwert ± 1/2/3 SD, Percentile, Min, Max, eine "
                  "<i>Constant line</i> oder ein <i>Band</i> von - bis (z.&nbsp;B. die Spezifikationsgrenzen).",
                  "Wer will, gibt eine Beschriftung und eine Farbe; × entfernt die Linie."],
                 "Mittelwert, Median usw. werden aus den einzelnen Versuchen im Diagramm berechnet, bei Small "
                 "multiples pro Feld getrennt (bei Columns aus den Säulen). Geht bei Balken, Box, Violin, Linie, "
                 "Punkten, Trend, Histogramm, Columns und Regelkarten. Copy format kopiert diese Linien nicht."),
                ("task", "Auf eine Detailseite für eine Maschine, einen Jet … springen (Drill-through)",
                 ["Detailseite einrichten: Seite öffnen, in <i>Filters</i> unter <i>Drill-through to this page</i> "
                  "das Feld wählen, z.&nbsp;B. <i>Machine</i>.",
                  "Auf einer anderen Seite mit der rechten Maustaste auf einen Balken, eine Box, eine Matrix-Zelle "
                  "oder ein Kuchenstück eines Visuals mit Machine klicken und unter <i>Drill through</i> die Seite "
                  "wählen.",
                  "Die Detailseite zeigt nur diese Maschine. <i>← Back to …</i> führt zurück, <i>Clear</i> zeigt "
                  "die Seite ohne den Drill-through-Filter."],
                 "Mit <i>Keep all filters of the clicked visual</i> (Standard) kommen auch die Seiten-, Visual-, "
                 "Klick- und Slicer-Filter des angeklickten Visuals mit. Der Drill-through wird nicht mit dem "
                 "Dashboard gespeichert. Geht auch auf der Seite Dashboards."),
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
                ("task", "Zählen, wie viele verschiedene Jets, Garne … gefahren wurden",
                 ["Eine <i>Card</i> hinzufügen und als Aggregation <i>Count (distinct)</i> wählen.",
                  "Das Feld in Value ziehen, z.&nbsp;B. <i>Jet</i>, <i>Yarn</i> oder <i>Machine</i> - hier geht "
                  "jedes Feld, nicht nur Zahlen.",
                  "Die Card zählt die verschiedenen Werte der Versuche, die nach allen Filtern, Slicern und "
                  "Klicks übrig sind. Mit <i>Columns</i> oder <i>Matrix</i> gibt es die Anzahl pro Kategorie, "
                  "z.&nbsp;B. verschiedene Jets pro Jahr."],
                 "Leere Werte (kein Jet erfasst) zählen nicht."),
                ("task", "Auflisten, welche Jets, Garne … es sind - je eine Zeile",
                 ["Eine <i>Table</i> hinzufügen und das Feld in Columns ziehen, z.&nbsp;B. <i>Jet</i>.",
                  "In Build <i>One row per value (e.g. a list of the jets)</i> ankreuzen. Die Tabelle zeigt jetzt "
                  "jeden Jet einmal, mit der Anzahl <i>Trials</i> und <i>Series</i>.",
                  "Nach Wunsch weitere Felder dazulegen: ein zweites Textfeld (z.&nbsp;B. <i>Machine</i>) ergibt "
                  "eine Zeile pro Kombination, ein Zahlenfeld (z.&nbsp;B. FP/m) zeigt seinen Mittelwert pro "
                  "Zeile. Klick auf eine Spaltenüberschrift sortiert."],
                 "Bei gleichen Filtern hat die Tabelle so viele Zeilen, wie eine Card mit <i>Count (distinct)</i> "
                 "zählt. Versuche ohne Wert fehlen (ein Hinweis unter der Tabelle nennt die Anzahl)."),
                ("task", "Zeigen, wie sich Teile zusammensetzen, z.&nbsp;B. A-, B- und C-Knoten pro Versuch",
                 ["Das Visual <i>Stacked fields</i> hinzufügen (Säulen mit drei Farben in Visualizations).",
                  "Die Zahlenfelder in <i>Values</i> ziehen - z.&nbsp;B. DTYoMat <i>AKnots</i>, <i>BKnots</i>, "
                  "<i>CKnots</i>. Jedes wird eine Farbe der Säule.",
                  "<i>Trial</i> (General) in <i>X axis</i> ziehen für eine Säule pro Versuch - oder Serie, "
                  "Maschine, Jet … um Gruppen zu vergleichen. Ohne X gibt es eine Säule für alle Versuche.",
                  "Unter <i>Bars</i>: <i>100 % stacked</i> (Standard, Anteil jedes Teils), <i>Stacked</i> (die "
                  "Werte) oder <i>Side by side</i>.",
                  "Kombi-Diagramm: ein oder mehrere Zahlenfelder in <i>Line (right axis)</i> ziehen - z.&nbsp;B. "
                  "<i>FP/m DTYoMat</i>. Sie erscheinen als Linien mit eigener Achse rechts."],
                 "Zuerst auf eine Serie filtern (Filters oder ein Slicer), dann heissen die Säulen V1, V2 …"),
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
                ("task", "Ein Visual formatieren: Reihenfolge, Top N, Dezimalstellen, Beschriftungen, Farben, Achsen, Legende",
                 ["Visual anklicken, dann oben in Visualizations den Reiter <i>Format</i> (<i>Build</i> zeigt "
                  "wieder die Felder). Klick auf die leere Seite oder Esc hebt die Auswahl auf.",
                  "<i>Sort and Top N</i>: nach Wert (hoch nach tief, tief nach hoch) oder nach Name ordnen und nur "
                  "die besten 5, 10 … zeigen - z.&nbsp;B. die 10 besten Jets. Unter dem Diagramm steht, wie viele "
                  "weggelassen sind.",
                  "<i>Numbers</i>: Dezimalstellen für Achse, Card, Matrix und die Werte im Diagramm. "
                  "<i>Data labels</i>: Werte an Balken und Linien zeigen oder ausschalten. <i>Error bars</i> (Bars, Mean line): <i>Standard deviation</i> (wie stark die Versuche streuen), <i>95 % confidence</i> (wo der wahre Mittelwert liegt - überlappen sich zwei Balken kaum, ist der Unterschied wohl echt; bei wenigen Versuchen wird er breit, bei einem Versuch gibt es keinen), <i>Min – Max</i> (schlechtester und bester Versuch) oder <i>Off</i>.",
                  "<i>Axes</i>: eigener Titel oder <i>hide</i> (ausblenden); festlegen, wo die Y-Achse anfängt und "
                  "endet (eines oder beides). <i>Legend</i>: rechts, oben, unten oder aus.",
                  "<i>Colours</i>: andere Palette, oder auf das Farbkästchen neben einem Wert klicken und eine "
                  "eigene Farbe wählen (× setzt zurück). Matrix: die Farbskala. <i>Text and grid</i>: Schriftgrösse, "
                  "Rasterlinien an oder aus.",
                  "Card: Grösse der Zahl, Einheit und Zeile darunter zeigen oder ausblenden. Tabelle: auf eine "
                  "Spaltenüberschrift klicken sortiert (nochmals = umgekehrt); <i>+ Add colour rule</i> färbt Zellen, "
                  "z.&nbsp;B. FP/m grösser als 100 grün, Maschine ist SSM rot.",
                  "Jede Änderung ist sofort sichtbar. Ein grüner Punkt zeigt, was vom Standard abweicht; "
                  "<i>Reset</i> setzt einen Abschnitt zurück, <i>Reset all</i> das ganze Visual.",
                  "<b>Dashboard-Thema</b>: auf die leere Seite klicken (nichts ausgewählt), dann <i>Format</i>. "
                  "Palette, Schriftgrösse, Rasterlinien, Dezimalstellen, Werte an Balken und Legende gelten dort für "
                  "alle Visuals auf allen Seiten; das eigene Format eines Visuals gewinnt. Im Visual zeigt "
                  "<i>Dashboard: …</i>, was das Thema vorgibt.",
                  "<b>Format übertragen</b>: das Visual mit dem richtigen Format anklicken, dann oben auf der Seite "
                  "<i>Copy format</i> (neben + New visual), dann das Visual, das es bekommen soll. Ein Doppelklick auf "
                  "<i>Copy format</i> lässt es für mehrere Visuals an - Esc beendet es. Achsentitel und -bereiche "
                  "werden nicht übertragen - sie gehören zu den Feldern.",
                  "<i>Points and lines</i>: eine eigene Form pro Farbe, die Punktgrösse. <i>Axes</i>: auch "
                  "logarithmische X-/Y-Achsen."],
                 "PDF und die Seite Dashboards zeigen das Visual genauso. Strg+Z macht eine Änderung rückgängig."),
                ("task", "Ein Visual gross ansehen, mit seinen Versuchen (Focus)",
                 ["Mit der Maus auf ein Visual zeigen und in seiner Titelzeile ⤢ klicken.",
                  "Das Visual füllt die Seite; darunter stehen alle Versuche, aus denen es besteht, mit den "
                  "verwendeten Feldern. Klick auf einen Punkt zeigt seine Zeile, Klick auf eine Zeile hebt ihren Punkt "
                  "hervor, Doppelklick auf eine Zeile öffnet den Versuch in Show Experiment.",
                  "<i>Back to the page</i> oder Esc geht zurück. Klick auf den farbigen Punkt in einer Titelzeile "
                  "zeigt die Fairness-Details, mit <i>Make it fairer</i>."],
                 "Geht auch auf der Seite Dashboards."),
                ("task", "Kuchen, Donut, Regelkarte, Radar, Text",
                 ["<i>Pie / donut</i>: ein Feld in Legend ziehen - es zählt Versuche (oder Serien, Experimente), "
                  "oder eine Zahl in Value und Sum wählen. <i>Shape</i> in Build: Kuchen oder Donut (in der Mitte "
                  "steht die Summe). Klick auf ein Stück filtert die Seite.",
                  "<i>Control chart</i> (Regelkarte): eine Zahl in Y axis. Die Versuche laufen in der Reihenfolge "
                  "von Serie und Versuchsnummer - oder nach dem Feld in X axis (z.&nbsp;B. Trial month). Linien: "
                  "Mittelwert und Grenzen ±3σ; rot = ausserhalb der Grenzen, gelb = 7 oder mehr in Folge auf einer "
                  "Seite des Mittelwerts.",
                  "<i>Radar</i>: drei oder mehr Zahlenfelder in Values, ein Feld in Legend (Jet, Garn, Maschine …). "
                  "Jede Achse läuft von der tiefsten Gruppe (innen) zur höchsten (aussen); die echten Werte stehen "
                  "im Tooltip.",
                  "<i>Text</i>: in Build schreiben. Eine Zeile mit # am Anfang ist eine Überschrift, **Text** ist fett."],
                 "Alle erscheinen auch im PDF."),
                ("task", "Sehen, wie die Tabellen zusammenhängen (Model)",
                 ["Oben links im Dashboard auf <i>Model</i> klicken (<i>Report</i> zeigt wieder die Seiten).",
                  "In der Mitte der Versuch; links, worauf er sich bezieht (Garn, Jet, Experiment, Zeit, Maschine), "
                  "rechts die Labortabellen. 1 : n = mehrere Zeilen pro Versuch, gemittelt; n : 1 = viele Versuche "
                  "teilen sich eine Zeile.",
                  "Auf eine Tabelle klicken: was sie enthält, wie ein Wert pro Versuch entsteht und pro Feld, wie "
                  "viele Versuche einen Wert haben."],
                 "Nur zum Lesen - dort kann niemand die Verknüpfungen ändern."),
                ("task", "Die Seitenleisten breiter oder schmaler machen",
                 ["Den linken Rand von Filters, Visualizations oder Fields ziehen. Ein Doppelklick auf den Rand gibt "
                  "die Standardbreite zurück; › klappt eine Leiste weg."],
                 "TrippleT merkt sich die Breiten für Sie."),
                ("task", "Rückgängig machen, Notizen sehen",
                 ["Strg+Z macht die letzte Änderung der Seite rückgängig (Layout, Felder, Filter …), Strg+Y stellt "
                  "sie wieder her. Entf löscht das ausgewählte Visual.",
                  "In einer Punktwolke <i>Show notes on values</i> ankreuzen: Werte mit Notiz bekommen einen "
                  "violetten Ring, die Notiz steht im Tooltip."]),
                ("task", "Durch Klick in einem Visual alle anderen hervorheben",
                 ["Auf einen Balken, eine Säule, ein Kuchenstück, eine Box oder eine Matrix-Zelle klicken - ein blaues "
                  "Kärtchen oben sagt, was angeklickt wurde.",
                  "Balken, Säulen, Kuchen, Punkte, Mittelwertlinien und Regelkarten behalten alle Versuche und grauen den "
                  "Rest aus (auch das angeklickte Visual). Säulen zeigen den hervorgehobenen Teil in jeder Säule, Balken "
                  "mit Mittelwerten den Mittelwert der hervorgehobenen Versuche über dem blassen Balken.",
                  "Cards, Matrix, Tabelle, Radar, Box, Violin, Histogramm und Slicer zeigen nur noch den angeklickten Wert.",
                  "Nochmals auf dieselbe Stelle oder auf das blaue Kärtchen klicken hebt es auf.",
                  "Lieber alle Visuals filtern: Format ohne Auswahl → <i>Clicks</i> → <i>Filters the other visuals</i>."]),
                ("h", "Behalten und teilen"),
                ("task", "Ein Dashboard speichern, um es später wieder zu öffnen",
                 [f"Auf {B('Save view')} klicken, einen Namen eingeben, <i>Share with everybody</i> ankreuzen, "
                  "wenn andere es sehen sollen.",
                  f"Mit {B('Open view')} wieder öffnen.",
                  f"Mit einzelnen Personen oder Gruppen (read, write, admin, superuser) teilen: {B('Share…')} - je "
                  "zum <i>Anschauen</i> oder <i>Anschauen und Bearbeiten</i>. Geteilte Dashboards erscheinen auf "
                  "der Seite <i>Dashboards</i>."],
                 "Gespeichert werden die Filter, nicht die Versuchsliste - eine View zeigt immer die aktuellen Daten. "
                 "Teilen kann nur, wer sie erstellt hat; ändern: Ersteller, Personen mit <i>edit</i> und Superuser; "
                 "löschen: Ersteller oder Superuser."),
                ("task", "Die neusten Daten holen",
                 [f"Auf {B('Reload')} klicken oder F5 drücken. Filter und Dashboard bleiben."]),
            ]},
            {"key": "screen", "title": "Bildschirm", "blocks": [
                ("areas", [
                    ("Oben", "New (leere Seite, Beispiel oder Vorlage), Open view, Save view, Share…, Excel, "
                             "Reload (F5), PDF und diese Hilfe."),
                    ("Grünes Feld", "Wie viele Versuche zu den Filtern auf allen Seiten passen, aus wie vielen Serien, "
                                    "Maschinen und Jets."),
                    ("Seite", "Report | Model, Seitenname, + New visual, Copy format; die Visuals; unten die "
                              "Seiten-Reiter."),
                    ("Filters", "On all pages (= Versuche finden, Yarn filters apply to), auf dieser Seite, auf diesem "
                                "Visual, Klicks und Slicer."),
                    ("Visualizations", "Die Visual-Typen; Build (Felder, Optionen) und Format (Reihenfolge, Zahlen, "
                                       "Farben, Achsen …) des gewählten Visuals - oder das Dashboard-Thema."),
                    ("Fields", "Alle Felder aller Tabellen in Ordnern, mit Suchfeld und + New calculated field."),
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
                      "laboratorio - en <b>todas</b> las series y los muestra en un dashboard como Power BI: páginas "
                      "con gráficos, tarjetas, tablas y slicers. Los <b>filtros en todas las páginas</b> (panel "
                      "Filters, a la derecha) deciden qué ensayos participan."),
                ("h", "1 Encontrar ensayos"),
                ("task", "Encontrar p. ej. todos los ensayos de poliéster con 70–80 dtex y 30–40 filamentos",
                 [f"Haz clic en {B('+ Add filter')}, elige <i>Material</i>, marca <i>PES</i> y haz clic en {B('Add filter')}.",
                  f"Otra vez {B('+ Add filter')}, elige <i>End titer</i>, escribe From 70 To 80 (o arrastra sobre "
                  "las barras) y añádelo.",
                  "Lo mismo con <i>Filaments</i> de 30 a 40."],
                 "El recuadro verde de arriba muestra siempre cuántos ensayos coinciden y de cuántas series. "
                 "Las muestras de referencia nunca se incluyen."),
                ("task", "Cambiar o quitar un filtro",
                 ["En el panel Filters, en <i>On all pages</i>, haz clic en un filtro para cambiarlo, o en su "
                  "<b>×</b> para quitarlo."]),
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
                  "El panel <i>Fields</i> del dashboard está agrupado igual y tiene su propio buscador."],
                 "El grupo <i>Jet</i> contiene los datos del jet usado en el ensayo: agujero de aire, canal de hilo, "
                 "cámara de turbulencia, cono, rango de título, fabricante, material y más. Todas las tablas de "
                 "laboratorio (Statimat, Itemat, DTYoMat, encogimiento …) están en la carpeta <i>Lab</i>."),
                ("task", "Solo números enteros, o solo 1, 1.5, 2 …",
                 ["Elige un campo numérico, p. ej. Overfeed, y escribe From y To.",
                  "Debajo elige <i>Only every</i> 1 (solo enteros) o 0.5 (1, 1.5, 2 …), o escribe tu propio paso.",
                  "O elige <i>Pick values</i>: cada valor que aparece en el rango se lista con su número de ensayos; "
                  "marca los que quieras."],
                 "La tarjeta del filtro lo muestra, p. ej. <i>Overfeed 1 – 5 % · every 0.5</i>."),
                ("h", "2 Leer los gráficos"),
                ("task", "Comparar máquinas (o materiales) lado a lado",
                 ["Arrastra un campo a <i>Small multiples</i>, p.&nbsp;ej. Machine. Obtienes un gráfico pequeño por "
                  "valor, todos con los mismos ejes."],
                 "Se muestran como máximo 9 paneles (los valores más frecuentes). Un clic en una entrada de la "
                 "leyenda la oculta, un doble clic muestra solo esa."),
                ("task", "Saber qué ensayo es un punto",
                 ["Señálalo con el ratón: la ayuda emergente muestra ensayo, serie e hilo.",
                  "Haz clic en ⤢ en la barra de título del visual (Focus): debajo del gráfico está la lista de sus "
                  "ensayos. Un clic en un punto muestra su fila, un doble clic en la fila abre la serie en Show "
                  "Experiment."]),
                ("task", "Saber si una comparación es justa",
                 ["Mira el punto de color en la barra de título de un gráfico. Comprueba si los grupos que comparas "
                  "(colores, paneles o categorías X, o el rango X) también difieren en otras condiciones que cambian "
                  "el valor Y: material, título, filamentos, tipo de hilo, máquina, jet, presión de aire, "
                  "sobrealimentación, velocidad.",
                  "<b>Verde</b>: nada llamativo. <b>Amarillo</b>: en parte justo o pocos datos. <b>Rojo</b>: el "
                  "gráfico puede mostrar el efecto de esas condiciones más que el de lo que comparas.",
                  "Haz clic en el punto para ver los detalles: cada condición, cuán distinta es su reparto entre los "
                  "grupos y cuánto influye en Y. <i>Make it fairer</i> añade a este visual un filtro para la parte "
                  "que comparten todos los grupos."],
                 "También avisa de grupos con muy pocos ensayos, grupos que vienen de una sola serie y grupos en "
                 "rangos X distintos. Es una luz de aviso, no una prueba: solo se comprueban las condiciones "
                 "registradas en TrippleT."),
                ("h", "Dashboard"),
                ("task", "Construir una página con varios visuales (como Power BI)",
                 ["Smart Chart abre directamente el dashboard (<i>Report</i> arriba a la izquierda).",
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
                ("task", "Añadir una línea de media, ± desviaciones estándar o límites de especificación (Analytics)",
                 ["Selecciona un gráfico y haz clic en <i>Analytics</i> en Visualizations (junto a Build y Format).",
                  "Elige <i>+ Add a line…</i>: Average, Median, media ± 1/2/3 SD, Percentile, Min, Max, una "
                  "<i>Constant line</i> o una <i>Band</i> de - a (p.&nbsp;ej. los límites de especificación).",
                  "Si quieres, ponle una etiqueta y un color; × la quita."],
                 "La media, la mediana, etc. se calculan con los ensayos individuales del gráfico, en cada small "
                 "multiple por separado (en Columns con las columnas). Funciona con barras, box, violín, línea, "
                 "puntos, tendencia, histograma, columnas y gráficos de control. Copy format no copia estas líneas."),
                ("task", "Saltar a una página de detalle de una máquina, un jet … (drill-through)",
                 ["Prepara la página de detalle: ábrela y en <i>Filters</i>, bajo <i>Drill-through to this page</i>, "
                  "elige el campo, p.&nbsp;ej. <i>Machine</i>.",
                  "En otra página, haz clic derecho en una barra, una caja, una celda de matriz o un trozo de "
                  "tarta de un visual con Machine y elige la página bajo <i>Drill through</i>.",
                  "La página de detalle muestra solo esa máquina. <i>← Back to …</i> vuelve, <i>Clear</i> muestra "
                  "la página sin el filtro de drill-through."],
                 "Con <i>Keep all filters of the clicked visual</i> (estándar) también pasan los filtros de página, "
                 "visual, clics y slicers del visual pulsado. El drill-through no se guarda con el dashboard. "
                 "También funciona en la página Dashboards."),
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
                ("task", "Contar cuántos jets, hilos … distintos se usaron",
                 ["Añade una <i>Card</i> y elige la agregación <i>Count (distinct)</i>.",
                  "Arrastra el campo a Value, p.&nbsp;ej. <i>Jet</i>, <i>Yarn</i> o <i>Machine</i>; aquí sirve "
                  "cualquier campo, no solo números.",
                  "La card cuenta los valores distintos de los ensayos que quedan tras todos los filtros, slicers "
                  "y clics. Con <i>Columns</i> o <i>Matrix</i> obtienes el número por categoría, p.&nbsp;ej. jets "
                  "distintos por año."],
                 "Los valores vacíos (sin jet registrado) no cuentan."),
                ("task", "Listar qué jets, hilos … son - una línea cada uno",
                 ["Añade una <i>Table</i> y arrastra el campo a Columns, p.&nbsp;ej. <i>Jet</i>.",
                  "En Build marca <i>One row per value (e.g. a list of the jets)</i>. La tabla muestra cada jet "
                  "una vez, con el número de <i>Trials</i> y <i>Series</i>.",
                  "Si quieres, añade más campos: un segundo campo de texto (p.&nbsp;ej. <i>Machine</i>) da una "
                  "línea por combinación, un campo numérico (p.&nbsp;ej. FP/m) muestra su media por línea. Clic "
                  "en un encabezado para ordenar."],
                 "Con los mismos filtros, la tabla tiene tantas líneas como cuenta una Card con <i>Count "
                 "(distinct)</i>. Los ensayos sin valor no aparecen (una nota debajo de la tabla dice cuántos)."),
                ("task", "Mostrar cómo se reparten las partes, p.&nbsp;ej. nudos A, B y C por ensayo",
                 ["Añade el visual <i>Stacked fields</i> (columnas de tres colores en Visualizations).",
                  "Arrastra los campos numéricos a <i>Values</i>, p.&nbsp;ej. DTYoMat <i>AKnots</i>, <i>BKnots</i>, "
                  "<i>CKnots</i>. Cada uno es un color de la columna.",
                  "Arrastra <i>Trial</i> (General) a <i>X axis</i> para una columna por ensayo, o una serie, "
                  "máquina, jet … para comparar grupos. Sin X hay una columna para todos los ensayos.",
                  "En <i>Bars</i>: <i>100 % stacked</i> (por defecto, la parte de cada uno), <i>Stacked</i> (los "
                  "valores) o <i>Side by side</i>.",
                  "Gráfico combinado: arrastra uno o más campos numéricos a <i>Line (right axis)</i>, p.&nbsp;ej. "
                  "<i>FP/m DTYoMat</i>. Se dibujan como líneas con su propio eje a la derecha."],
                 "Filtra primero a una serie (Filters o un slicer); así las columnas se llaman V1, V2 …"),
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
                ("task", "Dar formato a un visual: orden, Top N, decimales, etiquetas, colores, ejes, leyenda",
                 ["Haga clic en el visual y luego en la pestaña <i>Format</i> arriba en Visualizations (<i>Build</i> "
                  "vuelve a los campos). Un clic en la página vacía o Esc quita la selección.",
                  "<i>Sort and Top N</i>: ordenar por valor (de mayor a menor o al revés) o por nombre, y mostrar "
                  "solo los 5, 10 … mejores, p.&nbsp;ej. los 10 mejores jets. La nota bajo el gráfico dice cuántos "
                  "quedan fuera.",
                  "<i>Numbers</i>: decimales para el eje, la tarjeta, la matriz y los valores del gráfico. "
                  "<i>Data labels</i>: mostrar los valores en barras y líneas, o quitarlos. <i>Error bars</i> (Bars, Mean line): <i>Standard deviation</i> (cuánto se dispersan los ensayos), <i>95 % confidence</i> (dónde está la media real - si dos barras apenas se solapan, la diferencia probablemente es real; con pocos ensayos es ancho y con un solo ensayo no hay), <i>Min – Max</i> (peor y mejor ensayo) u <i>Off</i>.",
                  "<i>Axes</i>: título propio u ocultarlo (<i>hide</i>); fijar dónde empieza y termina el eje Y (uno "
                  "o los dos). <i>Legend</i>: derecha, arriba, abajo o sin leyenda.",
                  "<i>Colours</i>: otra paleta, o haga clic en el cuadro de color junto a un valor para elegir el "
                  "suyo (× lo restablece). Matriz: la escala de colores. <i>Text and grid</i>: tamaño del texto, "
                  "líneas de cuadrícula sí o no.",
                  "Tarjeta: tamaño del número, mostrar u ocultar la unidad y la línea de abajo. Tabla: un clic en el "
                  "título de una columna ordena (otro clic = al revés); <i>+ Add colour rule</i> colorea celdas, "
                  "p.&nbsp;ej. FP/m mayor que 100 en verde, Machine es SSM en rojo.",
                  "Cada cambio se ve enseguida. Un punto verde marca lo que difiere del estándar; <i>Reset</i> "
                  "restablece una sección, <i>Reset all</i> todo el visual.",
                  "<b>Tema del dashboard</b>: haga clic en la página vacía (nada seleccionado) y luego en "
                  "<i>Format</i>. Paleta, tamaño del texto, líneas de cuadrícula, decimales, valores en las barras y "
                  "leyenda valen allí para todos los visuales de todas las páginas; el formato propio de un visual "
                  "gana. En un visual, <i>Dashboard: …</i> muestra lo que da el tema.",
                  "<b>Copiar un formato</b>: haga clic en el visual con el formato bueno, luego en <i>Copy format</i> "
                  "arriba en la página (junto a + New visual) y después en el visual que debe recibirlo. Un doble clic "
                  "en <i>Copy format</i> lo deja activo para varios visuales; Esc lo termina. Los títulos y rangos de "
                  "los ejes no se copian: pertenecen a los campos.",
                  "<i>Points and lines</i>: una forma distinta por color, el tamaño de los puntos. <i>Axes</i>: "
                  "también ejes X / Y logarítmicos."],
                 "El PDF y la página Dashboards muestran el visual igual. Ctrl+Z deshace un cambio."),
                ("task", "Ver un visual en grande, con sus ensayos (Focus)",
                 ["Señale un visual con el ratón y haga clic en ⤢ en su barra de título.",
                  "El visual ocupa la página; debajo están todos los ensayos de los que se compone, con los campos "
                  "usados. Un clic en un punto muestra su fila, un clic en una fila resalta su punto, un doble clic en "
                  "una fila abre el ensayo en Show Experiment.",
                  "<i>Back to the page</i> o Esc vuelve. Un clic en el punto de color de una barra de título muestra "
                  "los detalles de equidad, con <i>Make it fairer</i>."],
                 "Funciona también en la página Dashboards."),
                ("task", "Tarta, dónut, gráfico de control, radar, texto",
                 ["<i>Pie / donut</i>: arrastre un campo a Legend - cuenta ensayos (o series, experimentos), o "
                  "arrastre un número a Value y elija Sum. <i>Shape</i> en Build: tarta o dónut (en el centro va "
                  "el total). Un clic en una porción filtra la página.",
                  "<i>Control chart</i>: un número en Y axis. Los ensayos van en el orden de serie y número de "
                  "ensayo, o según el campo en X axis (p.&nbsp;ej. Trial month). Líneas: media y límites ±3σ; rojo "
                  "= fuera de los límites, ámbar = 7 o más seguidos en un lado de la media.",
                  "<i>Radar</i>: tres o más campos numéricos en Values y un campo en Legend (jet, hilo, máquina …). "
                  "Cada eje va del grupo más bajo (dentro) al más alto (fuera); los valores reales están en la "
                  "ayuda emergente.",
                  "<i>Text</i>: escriba en Build. Una línea que empieza con # es un título, **texto** va en negrita."],
                 "Todos salen también en el PDF."),
                ("task", "Ver cómo se relacionan las tablas (Model)",
                 ["Haga clic en <i>Model</i> arriba a la izquierda del dashboard (<i>Report</i> vuelve a las páginas).",
                  "En el centro el ensayo; a la izquierda a qué se refiere (hilo, jet, experimento, tiempo, máquina), "
                  "a la derecha las tablas de laboratorio. 1 : n = varias filas por ensayo, promediadas; n : 1 = "
                  "muchos ensayos comparten una fila.",
                  "Haga clic en una tabla: qué contiene, cómo se obtiene un valor por ensayo y, por campo, cuántos "
                  "ensayos tienen un valor."],
                 "Solo lectura: allí nadie puede cambiar las relaciones."),
                ("task", "Hacer los paneles laterales más anchos o más estrechos",
                 ["Arrastre el borde izquierdo de Filters, Visualizations o Fields. Un doble clic en el borde vuelve "
                  "al ancho estándar; › pliega un panel."],
                 "TrippleT recuerda los anchos."),
                ("task", "Deshacer un cambio, ver notas",
                 ["Ctrl+Z deshace el último cambio de la página (diseño, campos, filtros …), Ctrl+Y lo rehace. "
                  "Supr borra el visual seleccionado.",
                  "En un gráfico de puntos marca <i>Show notes on values</i>: los valores con nota reciben un anillo "
                  "violeta y la nota aparece en la descripción."]),
                ("task", "Resaltar en todos los visuales haciendo clic en uno",
                 ["Haz clic en una barra, una columna, un sector, una caja o una celda de la matriz; una etiqueta azul "
                  "arriba indica lo que se pulsó.",
                  "Barras, columnas, tartas, puntos, líneas de medias y gráficos de control mantienen todos sus ensayos y "
                  "ponen el resto en gris (también el visual pulsado). Las columnas muestran la parte resaltada dentro de "
                  "cada columna, las barras de medias la media de los ensayos resaltados sobre la barra pálida.",
                  "Tarjetas, matriz, tabla, radar, caja, violín, histograma y slicers muestran solo el valor pulsado.",
                  "Otro clic en el mismo sitio o en la etiqueta azul lo deshace.",
                  "Para filtrar todos los visuales: Format sin nada seleccionado → <i>Clicks</i> → "
                  "<i>Filters the other visuals</i>."]),
                ("h", "Guardar y compartir"),
                ("task", "Guardar un dashboard para abrirlo más tarde",
                 [f"Haz clic en {B('Save view')}, escribe un nombre y marca <i>Share with everybody</i> si otros "
                  "deben verlo.",
                  f"Ábrelo de nuevo con {B('Open view')}.",
                  f"Para compartirlo con personas o grupos (read, write, admin, superuser): {B('Share…')}, cada uno "
                  "para <i>ver</i> o <i>ver y editar</i>. Los dashboards compartidos aparecen en la página "
                  "<i>Dashboards</i>."],
                 "Se guardan los filtros, no la lista de ensayos: una vista siempre muestra los datos actuales. "
                 "Solo el creador puede compartirla; cambiarla: el creador, quien tiene <i>edit</i> y los "
                 "superusuarios; borrarla: el creador o un superusuario."),
                ("task", "Obtener los datos más recientes",
                 [f"Haz clic en {B('Reload')} o pulsa F5. Los filtros y el dashboard se mantienen."]),
            ]},
            {"key": "screen", "title": "Pantalla", "blocks": [
                ("areas", [
                    ("Arriba", "New (página vacía, ejemplo o plantilla), Open view, Save view, Share…, Excel, "
                               "Reload (F5), PDF y esta ayuda."),
                    ("Recuadro verde", "Cuántos ensayos coinciden con los filtros en todas las páginas, de cuántas "
                                       "series, máquinas y jets."),
                    ("Página", "Report | Model, nombre de la página, + New visual, Copy format; los visuales; abajo las "
                               "pestañas de página."),
                    ("Filters", "On all pages (= encontrar ensayos, Yarn filters apply to), en esta página, en este "
                                "visual, clics y slicers."),
                    ("Visualizations", "Los tipos de visual; Build (campos, opciones) y Format (orden, números, colores, "
                                       "ejes …) del visual elegido, o el tema del dashboard."),
                    ("Fields", "Todos los campos de todas las tablas en carpetas, con buscador y + New calculated field."),
                ]),
            ]},
        ],
    },

    # ═══════════════════════════════ ZH ═══════════════════════════════
    "zh": {
        "window_title": "Smart Chart 如何使用？",
        "close": "关闭",
        "tabs": [
            {"key": "tasks", "title": "我该如何……？", "blocks": [
                ("p", "Smart Chart 按属性（纱线、机器设置、实验室结果）在<b>所有</b>试验系列中查找试验，并以类似 "
                      "Power BI 的仪表板显示：包含图表、卡片、表格和切片器的页面。<b>所有页面上的筛选</b>（右侧 "
                      "Filters 窗格）决定哪些试验参与。"),
                ("h", "1 查找试验"),
                ("task", "例如查找所有 70–80 dtex、30–40 根单丝的涤纶试验",
                 [f"点击 {B('+ Add filter')}，选择 <i>Material</i>，勾选 <i>PES</i>，再点击 {B('Add filter')}。",
                  f"再次点击 {B('+ Add filter')}，选择 <i>End titer</i>，输入 From 70 To 80（或在柱条上拖动），"
                  "然后添加。",
                  "对 <i>Filaments</i> 30 到 40 做同样操作。"],
                 "顶部绿色框始终显示有多少试验符合条件、分布在多少个系列中。参考样永远不包括在内。"),
                ("task", "修改或删除筛选",
                 ["在 Filters 窗格的 <i>On all pages</i> 下，点击筛选可修改，点击其 <b>×</b> 可删除。"]),
                ("task", "只看芯纱（或效果纱）",
                 ["在 <i>Yarn filters apply to</i> 下选择 <i>Core only</i> 或 <i>Effect only</i>。"],
                 "选择 <i>Any ply</i> 时，所有纱线筛选必须符合试验的<b>同一</b>股纱：PES + 70–80 dtex "
                 "表示同时满足两者的一根纱线，而不是一股 PES 加另一股 75 dtex。"),
                ("task", "理解“Add filter”中的直方图",
                 ["柱条显示数值在其他筛选剩余的试验中如何分布。绿色柱条在您设定的范围内。",
                  "下方一行告诉您新筛选会剩下多少试验，在添加之前就能看到。"]),
                ("task", "快速找到字段",
                 [f"在 {B('+ Add filter')} 中，字段已分组（Yarn、Jet、Machine、Lab、General）；点击分组可展开或折叠。",
                  "或在 <i>Search a field…</i> 中输入部分名称，匹配的分组会自动展开。",
                  "仪表板的 <i>Fields</i> 窗格分组方式相同，并有自己的搜索框。"],
                 "<i>Jet</i> 分组包含试验所用喷嘴的数据：气孔、纱道、涡流室、锥体、纤度范围、制造商、材料等。"
                 "所有实验室表（Statimat、Itemat、DTYoMat、收缩 …）都在 <i>Lab</i> 文件夹中。"),
                ("task", "只要整数，或只要 1、1.5、2 …",
                 ["选择数值字段，例如 Overfeed，输入 From 和 To。",
                  "在下方选择 <i>Only every</i> 1（仅整数）或 0.5（1、1.5、2 …），也可输入自定义步长。",
                  "或选择 <i>Pick values</i>：范围内出现的每个值都会列出并显示试验数；勾选所需的值。"],
                 "筛选卡片会显示出来，例如 <i>Overfeed 1 – 5 % · every 0.5</i>。"),
                ("h", "2 阅读图表"),
                ("task", "并排比较机器（或材料）",
                 ["将字段拖入 <i>Small multiples</i>，例如 Machine。每个值得到一个小图，坐标轴均相同。"],
                 "最多显示 9 个面板（出现最多的值）。单击图例项可隐藏，双击则只显示该项。"),
                ("task", "查出某个点是哪个试验",
                 ["将鼠标指向它：提示框显示试验、系列和纱线。",
                  "点击视觉对象标题栏中的 ⤢（Focus）：图表下方是其试验列表。"
                  "点击点可找到对应行，双击行可在 Show Experiment 中打开该系列。"]),
                ("task", "判断比较是否公平",
                 ["注意图表标题栏中的彩色圆点。它检查所比较的组（颜色、面板或 X 类别，或 X 范围）是否在其他会影响 "
                  "Y 值的条件上也不同：材料、纤度、单丝数、纱线类型、机器、喷嘴、气压、超喂、速度。",
                  "<b>绿色</b>：无明显问题。<b>黄色</b>：部分公平或数据较少。<b>红色</b>：图表可能显示的是这些条件的"
                  "影响，而不是所比较对象的影响。",
                  "点击圆点查看详情：每个条件、它在各组间分布的差异以及对 Y 的影响程度。<i>Make it fairer</i> "
                  "会为该视觉对象添加一个筛选，只保留所有组共有的部分。"],
                 "它还会对试验很少的组、只来自单个试验系列的组以及位于不同 X 范围的组发出警告。这只是警示灯，"
                 "不是证明：只检查 TrippleT 中记录的条件。"),
                ("h", "仪表板"),
                ("task", "搭建包含多个视觉对象的页面（类似 Power BI）",
                 ["Smart Chart 直接在仪表板中打开（左上角 <i>Report</i>）。",
                  "点击页面上的视觉对象可选中它，或点击 <i>Visualizations</i> 中的类型添加新的视觉对象"
                  f"（{B('+ New visual')} 添加空白视觉对象）。",
                  "将字段从 <i>Fields</i>（所有表，已分组、可折叠）拖入字段区"
                  "（X axis、Y axis、Legend、Small multiples、Rows、Columns、Value）。点击字段会将其放入所选视觉对象的"
                  "下一个空闲字段区。",
                  "拖动标题可移动视觉对象，拖动右下角可放大或缩小。鼠标悬停可进行<i>复制</i>和<i>删除</i>。",
                  "需要更多空间？<b>›</b> 按钮可将 <i>Visualizations</i> 或 <i>Fields</i> 折叠成窄条；"
                  "点击窄条可重新打开。TrippleT 会记住此设置。"],
                 "视觉对象类型：各种图表类型，以及 <i>Matrix</i>（每行每列一个值，着色，空白 = 尚无试验）、"
                 "<i>Card</i>（一个数字：计数、平均值、最小值、最大值 …）和 <i>Table</i>。左侧的筛选适用于所有视觉对象；"
                 "每个图表都有自己的公平性圆点。"),
                ("task", "添加切片器（选择值来筛选页面）",
                 ["点击 Visualizations 中的 <i>Slicer</i> 类型，并将字段拖入 <i>Field</i>。",
                  "选择 <i>Style</i>：<b>List</b>（带计数和搜索的勾选框）、<b>Dropdown</b>（同上，折叠）、"
                  "<b>Tiles</b>（按钮）、<b>Between</b>（带两个滑块的范围，仅限数值字段）或 <b>Year › Month</b>"
                  "（用于年/月字段：年份可展开，下方为 Jan–Dec 各月；点击年份选择其全部月份，或选择单个月份）。",
                  "如果只能选一个值，请关闭 <i>Multi-select</i>。<i>Clear selection</i> 或 <i>All</i> 可撤销选择。",
                  "<i>Applies to</i>：页面上所有视觉对象（默认）或仅勾选的视觉对象；选中切片器时，它们会显示虚线框。"],
                 "切片器筛选页面上所有其他视觉对象，包括其他切片器；它自己的列表始终显示其他筛选剩余的所有值及其试验数。"
                 "所选内容随视图一起保存。"),
                ("task", "使用多个页面",
                 ["底部的选项卡就是页面。<b>+</b> 添加页面，复制按钮复制当前页面，双击选项卡可重命名，"
                  "当前选项卡上的 <b>✕</b> 可删除它。"],
                 "点击和切片器只筛选其所在页面的视觉对象。所有页面都保存在视图中。"),
                ("task", "只筛选一个页面或一个视觉对象",
                 ["打开 <b>Filters</b> 窗格（在 Visualizations 旁边）。它分三部分：<i>On all pages</i>"
                  "（Find trials 的筛选，含 Yarn filters apply to）、<i>On this page</i> 和 <i>On this visual</i>"
                  "（针对所选视觉对象，该视觉对象会显示一个小的 <i>filter</i> 标记）。",
                  "在所需部分使用 " + B("+ Add filter") + "，窗口与 Find trials 中相同。",
                  "点击筛选标签可修改，点击其 × 可删除。"],
                 "三个层级，与 Power BI 相同：左侧 Find trials = 所有页面，然后是页面，再是视觉对象。"),
                ("task", "用公式创建自己的数值（计算字段）",
                 [f"在 <i>Fields</i> 中点击 {B('+ New calculated field')}，输入名称和单位。",
                  "构建公式：双击右侧列表中的字段（显示在 [方括号] 中），并使用 + − × ÷ ( ) ^ 以及 abs、sqrt、log10、"
                  "min、max，例如 [Intermingling Points (FP/m)] / [Air Consumption (m3/h)]。",
                  "预览显示多少试验得到数值以及最小值 / 平均值 / 最大值。点击 OK。"],
                 "该字段出现在 <i>Calculated</i> 文件夹中，可在任何地方使用：视觉对象、切片器和筛选。"
                 "点击旁边的 ✎ 可修改或删除。它随仪表板一起保存。"),
                ("task", "设置目标值",
                 ["选择卡片、图表或矩阵，在 Visualizations 中输入 <i>Target</i>，并选择 "
                  "<i>higher is better</i> 或 <i>lower is better</i>。"],
                 "卡片变为绿色或红色，图表显示虚线目标线，矩阵在目标的好的一侧着绿色、差的一侧着红色。"),
                ("task", "添加平均线、± 标准差或规格限（Analytics）",
                 ["选择图表，并点击 Visualizations 中的 <i>Analytics</i>（在 Build 和 Format 旁边）。",
                  "选择 <i>+ Add a line…</i>：Average、Median、Mean ± 1/2/3 SD、Percentile、Min、Max、"
                  "<i>Constant line</i> 或从 - 到的 <i>Band</i>（例如规格限）。",
                  "可以设置标签和颜色；× 可删除。"],
                 "平均值、中位数等根据图表中的单个试验计算，在每个 Small multiples 中分别计算（Columns 则根据各柱）。"
                 "适用于条形图、箱线图、小提琴图、折线图、散点图、趋势图、直方图、Columns 和控制图。Copy format 不会复制这些线。"),
                ("task", "跳转到某台机器、某个喷嘴 … 的详情页（Drill-through）",
                 ["创建详情页：打开该页面，在 <i>Filters</i> 中的 <i>Drill-through to this page</i> 下选择字段，"
                  "例如 <i>Machine</i>。",
                  "在另一页面上，右键单击使用 Machine 的视觉对象中的柱条、箱体、矩阵单元格或饼图扇区，"
                  "并在 <i>Drill through</i> 下选择该页面。",
                  "详情页只显示该机器。<i>← Back to …</i> 返回，<i>Clear</i> 显示不带 Drill-through 筛选的页面。"],
                 "勾选 <i>Keep all filters of the clicked visual</i>（默认）时，被点击视觉对象的页面、视觉对象、点击和切片器"
                 "筛选也会一起带过去。Drill-through 不随仪表板保存。在 Dashboards 页面上同样可用。"),
                ("task", "向下钻取（例如机器 → 喷嘴）",
                 ["在条形图、箱线图、小提琴图或折线图视觉对象中，将一个或多个字段拖入 <i>Drill down to</i>。",
                  "双击柱条：视觉对象显示该值的下一层级。路径显示在标题栏中，点击 ⤴ 返回上一层。"]),
                ("task", "选择点来筛选页面",
                 ["在散点图中，围绕点拖出一个矩形。所有其他视觉对象只显示这些试验（Filters 中显示 "
                  "<i>Selected n trials</i>）。",
                  "在图表中双击，或在 Filters 中删除，即可清除选择。"]),
                ("task", "从模板开始",
                 [f"在仪表板模式下点击 {B('New')}，选择 <i>Empty page</i>、<i>Example page</i> 或模板："
                  "Jet comparison、Yarn overview、Machine check 或 Lab overview。"],
                 "模板是普通页面，可随意修改并另存为自己的视图。"),
                ("task", "打印或共享仪表板（PDF、Excel）",
                 [f"{B('PDF')}：当前页面或所有页面，每页一张 A4，视觉对象位于原位置，并附筛选和公平性警告。",
                  f"{B('Excel')}：页面上每个视觉对象的数据，各占一个工作表。视觉对象上的 ⤓ 按钮只导出该视觉对象。"]),
                ("task", "让切片器跳过某个视觉对象（直接在页面上）",
                 ["选择切片器。其他每个视觉对象的标题栏会显示 <i>slicer: on</i> 或 <i>slicer: off</i>，点击即可切换。"],
                 "与 Visualizations 中的 <i>Applies to</i> 相同。"),
                ("task", "统计实验、系列或试验数量（统计）",
                 [f"点击 {B('New')} → <i>Lab statistics</i> 获取现成页面，或添加视觉对象 <i>Columns</i>"
                  "（或 Card、Matrix），并选择聚合方式 <i>Count of experiments</i>、<i>Count of trial series</i> 或 "
                  "<i>Count of trials</i>，无需 Value。",
                  "将字段放入 X axis：例如 <i>Experiment month</i>、<i>Product group</i>、<i>Order type</i>、"
                  "<i>Owner</i> 或 <i>Tested on (lab machine)</i>。Legend 中的字段会拆分柱子；在 Bars 下选择 "
                  "<i>Stacked</i>、<i>Side by side</i> 或 <i>100 % stacked</i>。",
                  "月份和年份按顺序排列，没有数据的月份显示为 0。"],
                 "没有试验的系列和没有系列的实验也会被计数。在两台实验室机器上测量的试验在每台机器上各计一次。"),
                ("task", "统计运行过多少种不同的喷嘴、纱线 …",
                 ["添加 <i>Card</i>，选择聚合方式 <i>Count (distinct)</i>。",
                  "将字段拖入 Value，例如 <i>Jet</i>、<i>Yarn</i> 或 <i>Machine</i>，这里任何字段都可以，不限于数值。",
                  "卡片统计经过所有筛选、切片器和点击后剩余试验中的不同值。使用 <i>Columns</i> 或 <i>Matrix</i> "
                  "可得到每个类别的数量，例如每年不同喷嘴的数量。"],
                 "空值（未记录喷嘴）不计数。"),
                ("task", "列出具体是哪些喷嘴、纱线 …（每项一行）",
                 ["添加 <i>Table</i>，将字段拖入 Columns，例如 <i>Jet</i>。",
                  "在 Build 中勾选 <i>One row per value (e.g. a list of the jets)</i>。表格现在每个喷嘴只显示一次，"
                  "并显示 <i>Trials</i> 和 <i>Series</i> 的数量。",
                  "可按需添加更多字段：第二个文本字段（例如 <i>Machine</i>）会每种组合一行，数值字段（例如 FP/m）"
                  "显示每行的平均值。点击列标题可排序。"],
                 "在相同筛选下，表格的行数与使用 <i>Count (distinct)</i> 的卡片计数相同。没有值的试验会被省略"
                 "（表格下方的提示说明数量）。"),
                ("task", "显示各部分如何构成总数，例如每个试验的 A、B、C 网络结",
                 ["添加视觉对象 <i>Stacked fields</i>（Visualizations 中三种颜色的柱子）。",
                  "将数值字段拖入 <i>Values</i>，例如 DTYoMat <i>AKnots</i>、<i>BKnots</i>、<i>CKnots</i>。"
                  "每个字段成为柱子的一种颜色。",
                  "将 <i>Trial</i>（General）拖入 <i>X axis</i>，每个试验一根柱子；或拖入系列、机器、喷嘴 … 来比较各组。"
                  "没有 X 时，所有试验合为一根柱子。",
                  "在 <i>Bars</i> 下：<i>100 % stacked</i>（默认，各部分所占比例）、<i>Stacked</i>（数值）或 "
                  "<i>Side by side</i>。",
                  "组合图：将一个或多个数值字段拖入 <i>Line (right axis)</i>，例如 <i>FP/m DTYoMat</i>。"
                  "它们以折线绘制，右侧有自己的坐标轴。"],
                 "先筛选到一个系列（Filters 或切片器），柱子就会标为 V1、V2 …"),
                ("task", "只显示今年、去年或最近 12 个月",
                 [f"在时间字段上添加筛选（{B('Add filter')}，或 Filters 窗格中的 <i>+ Add filter</i>）："
                  "<i>Month</i>、<i>Year</i>、<i>Trial month</i>、<i>Experiment month</i> …",
                  "在 <i>Period</i> 下选择 <i>This year</i>、<i>Last year</i>、<i>Last 12 months</i>、"
                  "<i>This month</i>、<i>Last month</i>，或用 <i>From – to</i> 指定起止月份。"],
                 "这些时间段随日历变化：到了一月，<i>This year</i> 就表示新的一年，无需修改仪表板。"
                 "选择单个值（例如 2026）则保持不变。"),
                ("task", "对齐多个视觉对象",
                 ["按住 Ctrl+单击（或 Shift+单击）所需的视觉对象，它们会显示绿色虚线框。Ctrl+A 选中页面上所有视觉对象，"
                  "Esc 结束选择。",
                  "页面上方会出现一个工具栏：左对齐、居中、右对齐、顶端、垂直居中或底端对齐；与最后点击的视觉对象同宽、"
                  "同高或同尺寸；水平或垂直等间距分布。",
                  "拖动其中一个选中视觉对象的标题栏，所有选中的会一起移动。方向键可将选中的视觉对象移动一步。"],
                 "Ctrl+Z 可撤销。"),
                ("task", "格式化视觉对象：排序、Top N、小数位、标签、颜色、坐标轴、图例",
                 ["点击视觉对象，然后点击 Visualizations 顶部的 <i>Format</i> 选项卡（<i>Build</i> 返回字段）。"
                  "点击空白页面或按 Esc 可取消选择。",
                  "<i>Sort and Top N</i>：按值（从高到低、从低到高）或按名称排序，并只显示前 5、10 …，"
                  "例如最好的 10 个喷嘴。图表下方的提示说明省略了多少。",
                  "<i>Numbers</i>：坐标轴、卡片、矩阵和图表数值的小数位。"
                  "<i>Data labels</i>：在柱条和折线上显示数值，或关闭。<i>Error bars</i>（Bars、Mean line）：<i>Standard deviation</i>（试验的离散程度）、<i>95 % confidence</i>（真实平均值所在范围：如果两根柱条几乎不重叠，差异很可能是真实的；试验少时范围会变宽，只有一个试验时则没有）、<i>Min – Max</i>（最差和最好的试验）或 <i>Off</i>。",
                  "<i>Axes</i>：自定义标题，或 <i>hide</i>（隐藏）；固定 Y 轴的起点和终点（一个或两个）。"
                  "<i>Legend</i>：右、上、下或关闭。",
                  "<i>Colours</i>：换一个调色板，或点击某个值旁的颜色框自选颜色（× 恢复）。矩阵：色阶。"
                  "<i>Text and grid</i>：文字大小、网格线开或关。",
                  "卡片：数字大小、显示或隐藏单位及下方一行。表格：点击列标题排序（再次点击 = 反向）；"
                  "<i>+ Add colour rule</i> 为单元格着色，例如 FP/m 大于 100 为绿色、Machine 为 SSM 时为红色。",
                  "每项修改立即可见。绿色圆点标出与默认不同的地方；<i>Reset</i> 恢复一个部分，<i>Reset all</i> "
                  "恢复整个视觉对象。",
                  "<b>仪表板主题</b>：点击空白页面（未选中任何对象），然后点击 <i>Format</i>。其中的调色板、文字大小、"
                  "网格线、小数位、柱条数值和图例适用于所有页面上的所有视觉对象；视觉对象自己的 Format 优先。"
                  "在视觉对象中，<i>Dashboard: …</i> 显示主题给出的设置。",
                  "<b>复制格式</b>：点击格式正确的视觉对象，然后点击页面顶部的 <i>Copy format</i>（在 + New visual "
                  "旁边），再点击要应用该格式的视觉对象。双击 <i>Copy format</i> 可对多个视觉对象连续使用，Esc 结束。"
                  "坐标轴标题和范围不会被复制，它们属于字段。",
                  "<i>Points and lines</i>：每种颜色使用不同形状、点的大小。<i>Axes</i>：也可使用对数 X / Y 轴。"],
                 "PDF 和 Dashboards 页面以相同方式显示视觉对象。Ctrl+Z 可撤销修改。"),
                ("task", "放大查看单个视觉对象及其试验（Focus）",
                 ["将鼠标指向视觉对象，点击其标题栏中的 ⤢。",
                  "视觉对象占满页面；下方列出构成它的所有试验及所用字段。点击点可找到对应行，点击行可高亮对应点，"
                  "双击行可在 Show Experiment 中打开该试验。",
                  "<i>Back to the page</i> 或 Esc 返回。点击标题栏中的彩色圆点可查看公平性详情，并可使用 "
                  "<i>Make it fairer</i>。"],
                 "在 Dashboards 页面上同样可用。"),
                ("task", "饼图、环形图、控制图、雷达图、文本",
                 ["<i>Pie / donut</i>：将字段拖入 Legend，统计试验（或系列、实验）数量；或将数值拖入 Value 并选择 Sum。"
                  "Build 中的 <i>Shape</i>：饼图或环形图（中间显示总数）。点击扇区可筛选页面。",
                  "<i>Control chart</i>：将数值放入 Y axis。试验按系列和试验编号排序，或按 X axis 中的字段排序"
                  "（例如 Trial month）。线条：平均值和 ±3σ 控制限；红色 = 超出控制限，琥珀色 = 连续 7 个或更多点位于"
                  "平均值同一侧。",
                  "<i>Radar</i>：将三个或更多数值字段放入 Values，一个字段放入 Legend（喷嘴、纱线、机器 …）。"
                  "每条轴从最低的组（内侧）到最高的组（外侧）；实际数值在提示框中。",
                  "<i>Text</i>：在 Build 中书写。以 # 开头的行是标题，**文字** 为粗体。"],
                 "所有这些也都会出现在 PDF 中。"),
                ("task", "查看各表之间的关系（Model）",
                 ["点击仪表板左上角的 <i>Model</i>（<i>Report</i> 返回页面）。",
                  "试验位于中间；左侧是它所引用的内容（纱线、喷嘴、实验、时间、机器），右侧是实验室表。"
                  "1 : n = 每个试验多行，取平均；n : 1 = 多个试验共用一行。",
                  "点击某个表：查看其内容、每个试验的值如何得出，以及每个字段有多少试验有值。"],
                 "只读，任何人都不能在此修改关联。"),
                ("task", "调宽或调窄侧边窗格",
                 ["拖动 Filters、Visualizations 或 Fields 的左边缘。双击边缘恢复默认宽度；› 可折叠窗格。"],
                 "TrippleT 会为您记住宽度。"),
                ("task", "撤销修改、查看备注",
                 ["Ctrl+Z 撤销页面的上一次修改（布局、字段、筛选 …），Ctrl+Y 重做。Delete 删除所选视觉对象。",
                  "在散点图中勾选 <i>Show notes on values</i>：带备注的值会显示紫色圆环，备注在提示框中。"]),
                ("task", "点击一个视觉对象，在所有视觉对象中高亮",
                 ["点击柱条、柱子、扇区、箱体或矩阵单元格，顶部的蓝色标签会说明点击了什么。",
                  "条形图、柱形图、饼图、散点图、平均线和控制图保留所有试验，其余部分变灰（被点击的视觉对象也是如此）。"
                  "柱形图在每根柱子内显示高亮部分，平均值条形图在淡化的柱条上方显示高亮试验的平均值。",
                  "卡片、矩阵、表格、雷达图、箱线图、小提琴图、直方图和切片器只显示被点击的值。",
                  "再次点击同一位置或蓝色标签即可撤销。",
                  "若要改为筛选所有视觉对象：在未选中任何对象时打开 Format → <i>Clicks</i> → "
                  "<i>Filters the other visuals</i>。"]),
                ("h", "保存与共享"),
                ("task", "保存仪表板以便以后再次打开",
                 [f"点击 {B('Save view')}，输入名称；如果其他人也应看到，请勾选 <i>Share with everybody</i>。",
                  f"用 {B('Open view')} 再次打开。",
                  f"要与个人或组（read、write、admin、superuser）共享：{B('Share…')}，每人可设为<i>查看</i>或"
                  "<i>查看和编辑</i>。共享的仪表板会出现在 <i>Dashboards</i> 页面上。"],
                 "保存的是筛选，而不是试验列表，因此视图始终显示当前数据。只有创建者可以共享；修改：创建者、拥有 "
                 "<i>edit</i> 权限的人和超级用户；删除：创建者或超级用户。"),
                ("task", "获取最新数据",
                 [f"点击 {B('Reload')} 或按 F5。您的筛选和仪表板保持不变。"]),
            ]},
            {"key": "screen", "title": "界面说明", "blocks": [
                ("areas", [
                    ("顶部", "New（空白页、示例或模板）、Open view、Save view、Share…、Excel、Reload (F5)、"
                             "PDF 以及本帮助。"),
                    ("绿色框", "有多少试验符合所有页面上的筛选，分布在多少个系列、机器和喷嘴中。"),
                    ("页面", "Report | Model、页面名称、+ New visual、Copy format；视觉对象；底部的页面选项卡。"),
                    ("Filters", "On all pages（= 查找试验，Yarn filters apply to）、本页面、本视觉对象、点击和切片器。"),
                    ("Visualizations", "视觉对象类型；所选视觉对象的 Build（字段、选项）和 Format（排序、数字、颜色、"
                                       "坐标轴 …），或仪表板主题。"),
                    ("Fields", "所有表的所有字段（按文件夹分组），带搜索框和 + New calculated field。"),
                ]),
            ]},
        ],
    },
}
