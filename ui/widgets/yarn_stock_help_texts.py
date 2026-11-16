# ui/widgets/yarn_stock_help_texts.py
"""Texte der Yarn-Stock-Hilfe (ui/widgets/yarn_stock_help_dialog.py) in
Englisch, Deutsch, Spanisch und Chinesisch (Nutzerwunsch 2026-10-13: Sprachumschaltung
per Flagge - bewusste Ausnahme von der "UI-Texte auf Englisch"-Regel).

Button-/Spaltennamen des Screens (New spool(s), Save Changes, Weight (kg) ...)
bleiben in allen Sprachen englisch, da sie im Screen genau so heissen.

Struktur pro Sprache identisch halten - der Dialog greift ueber dieselben
Keys zu. "svg_flow"/"svg_map" fuellen die {{key}}-Platzhalter in
assets/images/yarn_stock_spool_flow.svg bzw. yarn_stock_screen_map.svg
(Boxbreite im Flow-Diagramm ~150px -> Zeilen max. ~20 Zeichen).
"""

LANGUAGES = [("en", "English", "flag_gb.svg"),
             ("de", "Deutsch", "flag_de.svg"),
             ("es", "Español", "flag_es.svg"),
             ("zh", "中文", "flag_cn.svg")]
DEFAULT_LANGUAGE = "en"

# Bereichsmarkierungen (sprachneutral, verweisen auf die Skizze im Screen guide).
A = "<b>(A)</b>"
S1, S2, S3, S4 = "<b>(1)</b>", "<b>(2)</b>", "<b>(3)</b>", "<b>(4)</b>"

# Ampelfarben 1:1 wie in YarnStockScreen.reload_data().
OK_BG, LOW_BG, EMPTY_BG = "#EAF3DE", "#FAEEDA", "#FCEBEB"


def B(name: str) -> str:
    """Button-Name im Fliesstext (bleibt englisch wie im Screen)."""
    return f"<b>[{name}]</b>"


def _status_table(empty: str, low: str, ok: str) -> str:
    return ("<table cellspacing='4' cellpadding='6' style='margin-top:6px'>"
            f"<tr><td style='background:{EMPTY_BG}'><b>Empty</b></td><td>{empty}</td></tr>"
            f"<tr><td style='background:{LOW_BG}'><b>Low</b></td><td>{low}</td></tr>"
            f"<tr><td style='background:{OK_BG}'><b>OK</b></td><td>{ok}</td></tr>"
            "</table>")


def _ul(items) -> str:
    return "<ul style='margin-left:-20px'>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


TEXTS = {
    # ───────────────────────────── English ─────────────────────────────
    "en": {
        "window_title": "How does Yarn Stock work?",
        "close": "Close",
        "tab_tasks": "How do I…?",
        "tab_screen": "Screen guide",
        "tab_background": "Background",

        "tasks_intro": (f"Find your question below and follow the steps. {A} and {S1}–{S4} refer "
                        "to the areas of the screen, see the <i>Screen guide</i> tab."),
        "h_find": "Finding information",
        "tasks_find": [
            ("How much of a yarn do we have?",
             [f"Type part of the yarn name or batch into <i>Search yarn / batch…</i> above the overview {S1}.",
              "Read <i>Total (kg)</i> and <i>Spools</i> for each batch, and <i>Yarn total (kg)</i> "
              "for all batches of the yarn together."],
             ""),
            ("Where is a yarn stored?",
             [f"Search for the yarn in {S1}. The <i>Locations</i> column lists every location of that batch.",
              f"Click the row. The Spools area {S2} then shows the exact location of each spool."],
             ""),
            ("I have a spool in my hand. What is it?",
             [f"Read the spool number on the label (e.g. <i>#213</i>) and type it into <i>Go to spool #</i> {A}.",
              f"Press Enter or {B('Go')}. The screen jumps to its batch and highlights the spool in {S2}."],
             "Discarded spools are not shown. A QR code scanner also works: scan the label into the field."),
            ("What is stored in a particular rack?",
             [f"Type the rack letter (e.g. <i>E</i>) into <i>Rack lookup</i> {S4}. All locations starting with it are listed.",
              f"For a printable list, click {B('Export to Excel')} next to it."],
             ""),
            ("What do we need to reorder?",
             [f"Set the status filter above the overview {S1} to <i>Low</i>."],
             "Yarns that are completely used up are no longer listed in Yarn Stock. Superusers get a "
             "<i>Low</i> or <i>Empty</i> message per yarn in the bell, and Manage Yarn shows 0 kg. "
             "<i>Low</i> only works for yarns with a minimum stock (column <i>Min. stock (kg)</i>)."),
            ("Which trials was a spool used in?",
             [f"Click the batch in {S1}.",
              f"In {S2}, tick the spool(s) or click their rows.",
              f"Click {B('Used in…')}. It lists experiment, series, trial and ply."],
             ""),
            ("Who changed a spool, and when?",
             [f"Click the batch in {S1}.",
              f"In {S2}, tick or select the spool(s). Select none to see the whole batch, including discarded spools.",
              f"Click {B('History…')}. It lists date, user and what changed from which value to which."],
             f"For a single discarded spool: type its number into <i>Go to spool #</i> {A} and choose "
             "<i>Show history</i>. Changes are recorded since this feature was introduced."),
            ("How do I get the stock into Excel?",
             [f"Filter the overview {S1} if needed (search / status).",
              f"Click {B('Export to Excel')}. Exactly the rows currently shown are exported."],
             ""),
            ("Why is a yarn missing from the list?",
             ["The overview only lists yarns that currently have spools in stock. A yarn that was "
              "never delivered, or whose spools have all been used up and discarded, has no row here.",
              "All yarns, including those without stock, are in <b>Manage Yarn</b>. "
              f"To add stock, register the delivery with {B('New spool(s)')} (see below)."],
             ""),
        ],
        "h_change": "Changing the stock",
        "change_note": "Requires access level 2 or higher. Without it, the screen shows \"View only\".",
        "tasks_change": [
            ("Register a new delivery",
             [f"If the yarn/batch already exists, click its row in {S1} first. Yarn and batch are then pre-filled.",
              f"Click {B('New spool(s)')} in {S2}.",
              "Fill in yarn, batch, weight per spool, number of spools and location "
              "(optionally tube colour and producer). Click OK.",
              "The new spools are added to the label queue automatically (checkbox in the dialog, on by "
              f"default). Print them with {B('Print Labels…')} in {S3}."],
             "Afterwards the new spools' batch is selected in the overview automatically. "
             "One entry is created per physical spool. If the producer is missing from the list, "
             f"add it with the {B('+ New')} button in the dialog or {B('New producer…')}."),
            ("Print labels",
             [f"In {S2}, tick the spools in the first column (or {B('Select all')}).",
              f"Click {B('Add to label queue')}. The spools appear in {S3}.",
              f"Click {B('Print Labels…')} in {S3}. On the sheet preview, click the first free label "
              "if the sheet is already partly used.",
              "Save the PDF and print it."],
             "Printed spools leave the queue automatically. Spools that didn't fit on the sheet stay in it."),
            ("Enter the remaining weight or move a spool",
             [f"Click the batch in {S1}.",
              f"In {S2}, double-click <i>Weight (kg)</i> or <i>Location</i> of the spool, type the new value, press Enter.",
              f"Click {B('Save Changes')}."],
             "If you click another row or button before saving, TrippleT asks whether to save the changes."),
            ("Take an empty or unusable spool out of stock",
             [f"In {S2}, tick the spool(s).",
              f"Click {B('Discard')} and confirm."],
             "The spool disappears from the list but stays in the database, so "
             "<i>Used in…</i> still works for trials it was used in."),
            ("Correct the batch name or producer of a whole batch",
             [f"In the overview {S1} (or the rack lookup {S4}), double-click the <i>Batch</i> or <i>Producer</i> cell.",
              "Type the new batch name or choose the producer, press Enter."],
             "This changes all spools of that batch at once (including discarded ones) and is saved immediately."),
            ("Do a stock take (all racks, location by location)",
             [f"In <i>Rack lookup</i> {S4}, click {B('Stock take…')}. The overview shows every location as a tile.",
              "Click a grey (open) location, scan every spool you find there, then click "
              f"{B('Finish stock take…')}.",
              "The tile turns green (all fine) or orange (differences). Continue with the next grey one."],
             "A superuser starts and closes the stock take round. Full instructions: see the <i>Stock take</i> tab."),
            ("Set or change the minimum stock (superusers only)",
             [f"In the overview {S1}, double-click the <i>Min. stock (kg)</i> cell of the yarn.",
              "Type the minimum in kg and press Enter. Leave it empty for no minimum."],
             "The minimum applies to the whole yarn (all batches together) and is saved immediately. "
             "It can also be set in Manage Yarn."),
        ],

        "screen_caption": "Sketch with example rows. The screen works top-down: pick a row in (1), work with its spools in (2).",
        "screen_areas": [
            ("(A) Go to spool #", "Jumps straight to one spool by its number, e.g. the one on a label. Scanning the label's QR code works too."),
            ("(1) Overview",
             "<b>The starting point.</b> One row per yarn + batch that still has spools in stock: producer, "
             "number of spools, kg of the batch, kg of the whole yarn, minimum stock, locations and status "
             "(green OK, yellow Low, red Empty; the status applies to the whole yarn). Search and status "
             "filter narrow the list; <i>Export to Excel</i> exports what is shown. Double-clicking "
             "<i>Batch</i> or <i>Producer</i> corrects it for the whole batch, <i>Min. stock (kg)</i> "
             "(superusers) for the whole yarn."),
            ("(2) Spools",
             "<b>The individual spools</b> of the row selected in (1), one line per physical spool. "
             "Tick boxes select spools for <i>Add to label queue</i> and <i>Discard</i>. Weight, location, "
             "tube colour and producer are edited by double-click and stored with <i>Save Changes</i>. "
             "<i>New spool(s)</i> registers a delivery, <i>Used in…</i> shows the trials and <i>History…</i> "
             "the change history of the ticked or selected spools. Collapse with the ▾ button."),
            ("(3) Label queue",
             "<b>Spools waiting for a label.</b> Collect them here, then print them together with "
             "<i>Print Labels…</i> so a label sheet is used efficiently. <i>Remove selected</i> takes "
             "spools out of the queue without printing."),
            ("(4) Rack lookup",
             "<b>Stock by shelf instead of by yarn.</b> Enter the start of a location (e.g. <i>E</i> or "
             "<i>E1</i>) to see every yarn/batch stored there; exportable to Excel. "
             "<i>Stock take…</i> opens the stock take overview with all locations (see the <i>Stock take</i> tab)."),
        ],
        "h_elsewhere": "Where else stock shows up",
        "elsewhere": _ul([
            "<b>Create Experiment</b>: when a yarn is added to a ply, you can pick the actual spool. "
            "Only spools of that yarn that are in stock and weigh more than 0 kg are offered.",
            "<b>Manage Yarn</b>: stock in kg per yarn (all batches), including yarns without stock, and the "
            "<i>MinStock</i> field.",
            "<b>Show Experiment</b>: hovering over a yarn shows where its spools are stored.",
            "<b>Bell</b>: one Low/Empty warning per yarn for superusers, with a jump to the yarn.",
        ]),

        "h_levels": "Three levels: yarn, batch, spool",
        "levels": ("The <b>yarn</b> comes from the yarn catalogue (Manage Yarn). Under it sit one or more "
                   "<b>batches</b> (production lots, e.g. <tt>989G</tt>). Each batch consists of individual "
                   "<b>spools</b> with their own number (e.g. <tt>#213</tt>), each with weight, location, "
                   "tube colour, producer and status. The overview shows one row per yarn + batch."),
        "h_life": "The life of a spool",
        "life_note": ("<b>Important:</b> using a spool in a trial does <b>not</b> reduce its weight "
                      "automatically. The stock figure is only correct once someone enters the remaining "
                      "weight in the Spools area or discards the empty spool."),
        "h_status": "Status: OK, Low, Empty",
        "status": ("For each <b>yarn</b>, the kilos of all its spools <i>in stock</i> are added up over all "
                   "batches (<i>Yarn total (kg)</i>) and compared with its minimum stock "
                   "(<i>Min. stock (kg)</i>). All batch rows of a yarn therefore show the same status."
                   + _status_table("Yarn total is 0 kg.",
                                   "Yarn total is below the minimum stock. Superusers get a notification.",
                                   "Yarn total is at or above the minimum stock, or no minimum is set.")),
        "h_good": "Good to know",
        "good": _ul([
            "The stock is not a booking ledger: each spool stores its current weight, location and status. "
            "Every change made in Yarn Stock is additionally recorded in the spool history (<i>History…</i>).",
            "Discarded spools are not deleted, only hidden. A batch with no spool left in stock is not "
            "shown; a yarn that is completely used up disappears from Yarn Stock (Manage Yarn still lists it).",
            "Everyone can view. Creating, editing and discarding spools requires access level 2 or higher. "
            "Only superusers can change the minimum stock. Yarn Stock is not available in offline mode.",
        ]),

        "tab_stocktake": 'Stock take',
        "st_intro": 'A stock take checks whether the spools that TrippleT lists for a rack or slot are really there, and lets you correct the differences on the spot.',
        "st_note": '<b>Tip:</b> For large racks, work slot by slot (E1, E2, …). The list stays short, and you can stop and continue later without losing the overview.',
        "stocktake": [('Where to find it', 'Yarn Stock → <i>Rack lookup</i> <b>(4)</b> → <b>[Stock take…]</b>. The stock take overview opens: one tile per storage location. You need access level 2 or higher. If you have unsaved changes in the spool list, TrippleT asks you to save them first.'), ('The stock take round', "A stock take round (e.g. <i>Stock take October 2026</i>) covers every storage location. It stays open over several days, and several people can work at the same time - click <b>[Refresh]</b> to see what colleagues have done.<ul style='margin-left:-20px'><li><b>Start</b> (superusers): <b>[Start new round…]</b>. All locations are ticked; untick the ones to leave out of this round (e.g. a cleared rack).</li><li><b>Tiles</b>: grey = still open, green = checked and all fine, orange = checked with differences, dashed = left out. The tile shows <i>found/expected</i> (and <i>+n</i> for other spools scanned there); open tiles show how many spools are registered there now.</li><li><b>Click</b> a grey tile to check that location. <b>Right-click</b> for <i>Check again</i>, <i>Show results</i> and (superusers) <i>Leave out of this round</i> / <i>Include in this round</i>.</li><li>New locations that appear during the round (a spool moved to a new slot) are added automatically.</li><li><b>Close</b> (superusers): <b>[Close round…]</b> lists the locations not checked yet. A closed round can only be viewed and exported; older rounds can be chosen at the top (<i>Round</i>).</li></ul>Without an open round you can still check a single rack or slot with <b>[Check a location without a round…]</b> - nothing is recorded in a round then."), ('Before you start', "<ul style='margin-left:-20px'><li>Make sure every spool on the shelf has a label. Spools without a label can be checked by typing their number, if you know it.</li><li>Work location by location - the overview shows what is still open, so you can stop and continue another day.</li><li>A QR code scanner is optional. Typing the number and pressing Enter works the same way.</li></ul>"), ('Step by step', "<ol style='margin-left:-20px'><li>In the overview, click the tile of the location (e.g. <i>E12</i>). The scan window opens for exactly this location and lists every spool that should be there according to the system. (Without a round: enter a rack or slot and click <b>[Load]</b>.)</li><li>Click into the large field <i>Scan or type spool #</i> and scan the label of each spool you find, or type its number and press Enter. The field is cleared after each scan, so you can continue straight away.</li><li>Watch the coloured message under the field: it tells you what happened with the last scan (see table below). <i>Found X of Y</i> shows your progress.</li><li>When you have checked the whole location, click <b>[Finish stock take…]</b> and decide what to do with the spools that were not found. The result is saved for this location and the tile turns green or orange.</li></ol>"), ('What happens when you scan', "<table cellspacing='0' cellpadding='6' border='1' style='border-color:#d0d0d0'><tr><th align='left' style='background:#e9f6e9'>Situation</th><th align='left' style='background:#e9f6e9'>What you see</th><th align='left' style='background:#e9f6e9'>What is saved</th></tr><tr><td valign='top'>Spool is expected here</td><td valign='top'>Marked as found and shown in green.</td><td valign='top'>Nothing is changed.</td></tr><tr><td valign='top'>Spool is registered at another location</td><td valign='top'>TrippleT asks where it really is (suggestion: the location you are checking).</td><td valign='top'><b>OK</b> moves it immediately. <b>Cancel</b> leaves it where it is registered.</td></tr><tr><td valign='top'>Spool is marked as discarded</td><td valign='top'>TrippleT asks whether to put it back in stock and where.</td><td valign='top'><b>OK</b> puts it back in stock immediately. Check its weight afterwards in the spool list.</td></tr><tr><td valign='top'>Number does not exist</td><td valign='top'>Shown in red under <i>Other scans</i>.</td><td valign='top'>Nothing is changed. Check the label.</td></tr><tr><td valign='top'>Spool was already scanned</td><td valign='top'>Short note only.</td><td valign='top'>Nothing is changed.</td></tr></table>"), ('Finishing', "After <b>[Finish stock take…]</b> TrippleT shows a summary: how many spools were found, which corrections were already saved, and which spools are missing. For the missing spools you choose:<ul style='margin-left:-20px'><li><b>Discard missing spools</b>: they are marked as discarded (history note: <i>stock take</i>).</li><li><b>Keep them (no change)</b>: nothing happens, e.g. if they are only in use at a machine right now.</li><li><b>Back to scanning</b>: continue the stock take.</li></ul>"), ('Results and export', "The <b>Results</b> tab lists what was found where, per spool: location, spool, yarn, batch, result, who and when. A summary line on top counts found, missing, moved, put back and unknown spools.<ul style='margin-left:-20px'><li><i>Only differences</i> (on by default) hides the spools that were exactly where expected. <i>Location</i> filters, e.g. <i>C</i> or <i>C21</i>.</li><li>A spool missing at one location but scanned at another in the same round is marked <i>seen at …</i> - it is not lost.</li><li><b>[Export to Excel…]</b> saves the round with three sheets: summary, locations (status, expected, found, who, when) and all results.</li></ul>"), ('What is saved when', "<ul style='margin-left:-20px'><li>Moves and put-backs are saved <b>immediately</b> when you confirm them.</li><li>Missing spools are discarded <b>only</b> when you click <i>Discard missing spools</i> at the end.</li><li>If you close the window early (<b>Cancel</b>), TrippleT asks for confirmation. Corrections already confirmed stay saved, but nothing is discarded.</li><li>Loading a different location starts over. Scans so far are dropped, saved corrections stay.</li><li>In a round, the result of a location is saved when you finish it. If you close the scan window early, the location stays open (grey). Checking a location again replaces its earlier result.</li></ul>"), ('Good to know', "<ul style='margin-left:-20px'><li>No label, or the scanner does not read it? <b>Double-click</b> the spool in the list to mark it as found by hand. It is shown in blue and noted as <i>marked by hand</i> in the results, so it is clear it was not scanned. <b>Right-click</b> → <i>Undo - not found</i> takes back a found mark (also after a wrong scan).</li><li>Every correction is recorded in the spool history (<i>History…</i>) with your name and the note <i>stock take</i>.</li><li>The stock take checks presence and location only. Weights are not checked; correct them in the spool list afterwards if needed.</li><li>Spools that are in use at a machine are not on the shelf. Choose <i>Keep them</i> for those, or check them first.</li></ul>")],

        "svg_flow": {
            "status": "Status",
            "t1": "1  Goods in", "t1b": "yarn, batch, kg,", "t1c": "count, location",
            "t2": "2  Label", "t2c": "stick on spool",
            "t3": "3  On the shelf", "t3a": "counts as stock,", "t3b": "shows up in the", "t3c": "overview",
            "t4": "4  In a trial", "t4a": "spool picked per", "t4b": "ply when creating", "t4c": "the trial",
            "t5": "5  Discard", "t5a": "empty or unusable,", "t5b": "hidden from the", "t5c": "spool list",
            "loop": "Update weight by hand",
            "trace": "Traceability:", "trace2": "\"Used in…\" lists every trial of a spool",
        },
        "svg_map": {
            "help": "this help",
            "hint": "click the box to tick a spool · double-click Weight / Location / Colour / Producer to edit",
        },
    },

    # ───────────────────────────── Deutsch ─────────────────────────────
    "de": {
        "window_title": "Wie funktioniert Yarn Stock?",
        "close": "Schliessen",
        "tab_tasks": "Wie mache ich…?",
        "tab_screen": "Bildschirm",
        "tab_background": "Hintergrund",

        "tasks_intro": (f"Such dir unten deine Frage aus und folge den Schritten. {A} und {S1}–{S4} "
                        "bezeichnen die Bereiche des Bildschirms, siehe Tab <i>Bildschirm</i>."),
        "h_find": "Informationen finden",
        "tasks_find": [
            ("Wie viel haben wir von einem Garn?",
             [f"Einen Teil des Garnnamens oder der Batch in <i>Search yarn / batch…</i> über der Übersicht {S1} eintippen.",
              "<i>Total (kg)</i> und <i>Spools</i> zeigen den Bestand pro Batch, <i>Yarn total (kg)</i> "
              "den Bestand aller Batches des Garns zusammen."],
             ""),
            ("Wo steht ein Garn?",
             [f"Das Garn in {S1} suchen. Die Spalte <i>Locations</i> listet alle Lagerplätze dieser Batch.",
              f"Die Zeile anklicken. Der Bereich Spools {S2} zeigt dann den genauen Platz jeder Spule."],
             ""),
            ("Ich habe eine Spule in der Hand. Was ist das?",
             [f"Die Spulennummer auf dem Etikett ablesen (z.&nbsp;B. <i>#213</i>) und in <i>Go to spool #</i> {A} eintippen.",
              f"Enter oder {B('Go')} drücken. Der Bildschirm springt zur Batch und markiert die Spule in {S2}."],
             "Ausgebuchte Spulen werden nicht angezeigt. Ein QR-Code-Scanner funktioniert auch: Etikett ins Feld scannen."),
            ("Was steht in einem bestimmten Regal?",
             [f"Den Regalbuchstaben (z.&nbsp;B. <i>E</i>) in <i>Rack lookup</i> {S4} eintippen. Alle Plätze, die damit beginnen, werden aufgelistet.",
              f"Für eine Liste zum Ausdrucken daneben auf {B('Export to Excel')} klicken."],
             ""),
            ("Was müssen wir nachbestellen?",
             [f"Den Statusfilter über der Übersicht {S1} auf <i>Low</i> stellen."],
             "Komplett aufgebrauchte Garne stehen nicht mehr in Yarn Stock. Superuser bekommen pro Garn eine "
             "<i>Low</i>- oder <i>Empty</i>-Meldung in der Glocke, und Manage Yarn zeigt 0 kg. "
             "<i>Low</i> funktioniert nur bei Garnen mit Mindestbestand (Spalte <i>Min. stock (kg)</i>)."),
            ("In welchen Versuchen wurde eine Spule verwendet?",
             [f"Die Batch in {S1} anklicken.",
              f"In {S2} die Spule(n) abhaken oder ihre Zeilen anklicken.",
              f"Auf {B('Used in…')} klicken. Angezeigt werden Experiment, Serie, Versuch und Ply."],
             ""),
            ("Wer hat eine Spule wann geändert?",
             [f"Die Batch in {S1} anklicken.",
              f"In {S2} die Spule(n) abhaken oder markieren. Ohne Auswahl wird die ganze Batch gezeigt, auch ausgebuchte Spulen.",
              f"Auf {B('History…')} klicken. Angezeigt werden Datum, Benutzer und was von welchem auf welchen Wert geändert wurde."],
             f"Für eine einzelne ausgebuchte Spule: Nummer in <i>Go to spool #</i> {A} eintippen und "
             "<i>Show history</i> wählen. Änderungen werden seit Einführung dieser Funktion aufgezeichnet."),
            ("Wie bekomme ich den Bestand nach Excel?",
             [f"Die Übersicht {S1} bei Bedarf filtern (Suche / Status).",
              f"Auf {B('Export to Excel')} klicken. Exportiert werden genau die angezeigten Zeilen."],
             ""),
            ("Warum fehlt ein Garn in der Liste?",
             ["Die Übersicht zeigt nur Garne, von denen aktuell Spulen am Lager sind. Ein Garn, das nie "
              "angeliefert wurde oder dessen Spulen alle aufgebraucht und ausgebucht sind, hat hier keine Zeile.",
              "Alle Garne, auch ohne Bestand, findest du in <b>Manage Yarn</b>. "
              f"Um Bestand anzulegen, die Lieferung mit {B('New spool(s)')} erfassen (siehe unten)."],
             ""),
        ],
        "h_change": "Bestand ändern",
        "change_note": "Erfordert Access Level 2 oder höher. Ohne Schreibrecht zeigt der Bildschirm „View only“.",
        "tasks_change": [
            ("Neue Lieferung erfassen",
             [f"Existiert das Garn / die Batch schon, zuerst die Zeile in {S1} anklicken. Garn und Batch sind dann vorausgefüllt.",
              f"In {S2} auf {B('New spool(s)')} klicken.",
              "Garn, Batch, Gewicht pro Spule, Anzahl Spulen und Lagerplatz ausfüllen "
              "(optional Hülsenfarbe und Hersteller). OK klicken.",
              "Die neuen Spulen landen automatisch in der Label queue (Checkbox im Dialog, standardmässig an). "
              f"Mit {B('Print Labels…')} in {S3} drucken."],
             "Danach ist die Batch der neuen Spulen in der Übersicht automatisch ausgewählt. "
             "Pro physischer Spule wird ein Eintrag angelegt. Fehlt der Hersteller in der Liste, "
             f"mit {B('+ New')} im Dialog oder mit {B('New producer…')} anlegen."),
            ("Etiketten drucken",
             [f"In {S2} die Spulen in der ersten Spalte abhaken (oder {B('Select all')}).",
              f"Auf {B('Add to label queue')} klicken. Die Spulen erscheinen in {S3}.",
              f"In {S3} auf {B('Print Labels…')} klicken. Ist der Etikettenbogen schon angebraucht, "
              "in der Vorschau das erste freie Feld anklicken.",
              "Das PDF speichern und ausdrucken."],
             "Gedruckte Spulen verschwinden automatisch aus der Warteschlange. Was nicht mehr auf den Bogen passte, bleibt drin."),
            ("Restgewicht eintragen oder Spule umlagern",
             [f"Die Batch in {S1} anklicken.",
              f"In {S2} bei der Spule auf <i>Weight (kg)</i> oder <i>Location</i> doppelklicken, neuen Wert eintippen, Enter.",
              f"Auf {B('Save Changes')} klicken."],
             "Klickst du vor dem Speichern eine andere Zeile oder einen Button an, fragt TrippleT, ob die Änderungen gespeichert werden sollen."),
            ("Leere oder unbrauchbare Spule ausbuchen",
             [f"In {S2} die Spule(n) abhaken.",
              f"Auf {B('Discard')} klicken und bestätigen."],
             "Die Spule verschwindet aus der Liste, bleibt aber in der Datenbank. "
             "<i>Used in…</i> funktioniert für ihre Versuche also weiterhin."),
            ("Batch-Name oder Hersteller für eine ganze Batch korrigieren",
             [f"In der Übersicht {S1} (oder im Rack lookup {S4}) auf die Zelle <i>Batch</i> oder <i>Producer</i> doppelklicken.",
              "Neuen Batch-Namen eintippen bzw. Hersteller wählen, Enter."],
             "Das ändert alle Spulen dieser Batch auf einmal (auch ausgebuchte) und wird sofort gespeichert."),
            ("Inventur machen (alle Regale, Platz für Platz)",
             [f"Im <i>Rack lookup</i> {S4} auf {B('Stock take…')} klicken. Die Übersicht zeigt jeden Lagerplatz als Kachel.",
              "Auf einen grauen (offenen) Platz klicken, jede Spule scannen, die dort steht, dann auf "
              f"{B('Finish stock take…')} klicken.",
              "Die Kachel wird grün (alles stimmt) oder orange (Abweichungen). Mit dem nächsten grauen Platz weitermachen."],
             "Die Inventur-Runde startet und schliesst ein Superuser. Ausführliche Anleitung: siehe Tab <i>Inventur</i>."),
            ("Mindestbestand setzen oder ändern (nur Superuser)",
             [f"In der Übersicht {S1} auf die Zelle <i>Min. stock (kg)</i> des Garns doppelklicken.",
              "Mindestbestand in kg eintippen, Enter. Leer lassen = kein Mindestbestand."],
             "Der Mindestbestand gilt für das ganze Garn (alle Batches zusammen) und wird sofort gespeichert. "
             "Er lässt sich auch in Manage Yarn setzen."),
        ],

        "screen_caption": "Skizze mit Beispielzeilen. Der Bildschirm arbeitet von oben nach unten: Zeile in (1) wählen, mit ihren Spulen in (2) arbeiten.",
        "screen_areas": [
            ("(A) Go to spool #", "Springt direkt zu einer Spule über ihre Nummer, z.&nbsp;B. die auf dem Etikett. Den QR-Code des Etiketts zu scannen funktioniert auch."),
            ("(1) Overview",
             "<b>Der Einstieg.</b> Eine Zeile pro Garn + Batch mit Spulen am Lager: Hersteller, Anzahl Spulen, "
             "kg der Batch, kg des ganzen Garns, Mindestbestand, Lagerplätze und Status (grün OK, gelb Low, "
             "rot Empty; der Status gilt für das ganze Garn). Suche und Statusfilter grenzen die Liste ein; "
             "<i>Export to Excel</i> exportiert das Angezeigte. Doppelklick auf <i>Batch</i> oder "
             "<i>Producer</i> korrigiert den Wert für die ganze Batch, auf <i>Min. stock (kg)</i> "
             "(Superuser) für das ganze Garn."),
            ("(2) Spools",
             "<b>Die einzelnen Spulen</b> der in (1) gewählten Zeile, eine Zeile pro physischer Spule. "
             "Häkchen wählen Spulen für <i>Add to label queue</i> und <i>Discard</i>. Gewicht, Platz, "
             "Hülsenfarbe und Hersteller per Doppelklick ändern und mit <i>Save Changes</i> speichern. "
             "<i>New spool(s)</i> erfasst eine Lieferung, <i>Used in…</i> zeigt die Versuche und <i>History…</i> "
             "den Änderungsverlauf der abgehakten oder markierten Spulen. Mit dem ▾-Knopf einklappbar."),
            ("(3) Label queue",
             "<b>Spulen, die auf ein Etikett warten.</b> Hier sammeln und dann gemeinsam mit "
             "<i>Print Labels…</i> drucken, damit der Etikettenbogen gut ausgenutzt wird. "
             "<i>Remove selected</i> nimmt Spulen ohne Druck wieder heraus."),
            ("(4) Rack lookup",
             "<b>Bestand nach Regal statt nach Garn.</b> Den Anfang eines Lagerplatzes eingeben "
             "(z.&nbsp;B. <i>E</i> oder <i>E1</i>), um alle dort gelagerten Garne/Batches zu sehen; nach Excel "
             "exportierbar. <i>Stock take…</i> öffnet die Inventur-Übersicht mit allen Lagerplätzen (siehe Tab <i>Inventur</i>)."),
        ],
        "h_elsewhere": "Wo der Bestand sonst noch auftaucht",
        "elsewhere": _ul([
            "<b>Create Experiment</b>: Wird einem Ply ein Garn zugewiesen, kann man die konkrete Spule wählen. "
            "Angeboten werden nur Spulen dieses Garns, die am Lager sind und mehr als 0 kg wiegen.",
            "<b>Manage Yarn</b>: Bestand in kg pro Garn (alle Batches), auch für Garne ohne Bestand, und das "
            "Feld <i>MinStock</i>.",
            "<b>Show Experiment</b>: Mit der Maus über ein Garn fahren zeigt, wo seine Spulen liegen.",
            "<b>Glocke</b>: eine Low/Empty-Warnung pro Garn für Superuser, mit Sprung zum Garn.",
        ]),

        "h_levels": "Drei Ebenen: Garn, Batch, Spule",
        "levels": ("Das <b>Garn</b> kommt aus dem Garnkatalog (Manage Yarn). Darunter gibt es eine oder "
                   "mehrere <b>Batches</b> (Chargen, z.&nbsp;B. <tt>989G</tt>). Jede Batch besteht aus "
                   "einzelnen <b>Spulen</b> mit eigener Nummer (z.&nbsp;B. <tt>#213</tt>), jeweils mit Gewicht, "
                   "Lagerplatz, Hülsenfarbe, Hersteller und Status. Die Übersicht zeigt eine Zeile pro Garn + Batch."),
        "h_life": "Der Lebenslauf einer Spule",
        "life_note": ("<b>Wichtig:</b> Wird eine Spule im Versuch verwendet, wird ihr Gewicht <b>nicht</b> "
                      "automatisch reduziert. Der Bestand stimmt erst, wenn jemand das Restgewicht im "
                      "Bereich Spools einträgt oder die leere Spule ausbucht."),
        "h_status": "Status: OK, Low, Empty",
        "status": ("Für jedes <b>Garn</b> werden die Kilos aller Spulen <i>in stock</i> über alle Batches addiert "
                   "(<i>Yarn total (kg)</i>) und mit seinem Mindestbestand verglichen (<i>Min. stock (kg)</i>). "
                   "Alle Batch-Zeilen eines Garns zeigen deshalb denselben Status."
                   + _status_table("Garn-Summe ist 0 kg.",
                                   "Garn-Summe liegt unter dem Mindestbestand. Superuser erhalten eine Benachrichtigung.",
                                   "Garn-Summe liegt auf oder über dem Mindestbestand, oder es ist keiner hinterlegt.")),
        "h_good": "Gut zu wissen",
        "good": _ul([
            "Der Bestand ist kein Buchungsjournal: Jede Spule speichert ihr aktuelles Gewicht, ihren Platz und ihren Status. "
            "Jede Änderung in Yarn Stock wird zusätzlich im Spulen-Verlauf festgehalten (<i>History…</i>).",
            "Ausgebuchte Spulen werden nicht gelöscht, nur ausgeblendet. Eine Batch ohne Spule am Lager wird "
            "nicht angezeigt; ein komplett aufgebrauchtes Garn verschwindet aus Yarn Stock (Manage Yarn zeigt es weiterhin).",
            "Ansehen kann jeder. Spulen anlegen, ändern und ausbuchen erfordert Access Level 2 oder höher. "
            "Den Mindestbestand ändern dürfen nur Superuser. Im Offline-Modus ist Yarn Stock nicht verfügbar.",
        ]),

        "tab_stocktake": 'Inventur',
        "st_intro": 'Eine Inventur prüft, ob die Spulen, die TrippleT für ein Regal oder einen Platz führt, wirklich dort stehen, und korrigiert Abweichungen direkt vor Ort.',
        "st_note": '<b>Tipp:</b> Grosse Regale Fach für Fach prüfen (E1, E2, …). Die Liste bleibt kurz, und man kann unterbrechen und später weitermachen, ohne den Überblick zu verlieren.',
        "stocktake": [('Wo finde ich sie?', 'Yarn Stock → <i>Rack lookup</i> <b>(4)</b> → <b>[Stock take…]</b>. Es öffnet sich die Inventur-Übersicht: eine Kachel pro Lagerplatz. Dafür ist Access Level 2 oder höher nötig. Gibt es in der Spulenliste noch ungespeicherte Änderungen, fragt TrippleT zuerst, ob sie gespeichert werden sollen.'), ('Die Inventur-Runde', "Eine Inventur-Runde (z.&nbsp;B. <i>Stock take October 2026</i>) umfasst alle Lagerplätze. Sie bleibt über mehrere Tage offen, und mehrere Personen können gleichzeitig arbeiten - <b>[Refresh]</b> zeigt, was Kollegen schon erledigt haben.<ul style='margin-left:-20px'><li><b>Starten</b> (Superuser): <b>[Start new round…]</b>. Alle Plätze sind angehakt; Plätze, die in dieser Runde nicht geprüft werden sollen (z.&nbsp;B. ein geräumtes Regal), abhaken.</li><li><b>Kacheln</b>: grau = noch offen, grün = geprüft und alles stimmt, orange = geprüft mit Abweichungen, gestrichelt = ausgelassen. Auf der Kachel steht <i>gefunden/erwartet</i> (und <i>+n</i> für andere dort gescannte Spulen); offene Kacheln zeigen, wie viele Spulen dort aktuell erfasst sind.</li><li><b>Klick</b> auf eine graue Kachel prüft diesen Platz. <b>Rechtsklick</b> für <i>Check again</i>, <i>Show results</i> und (Superuser) <i>Leave out of this round</i> / <i>Include in this round</i>.</li><li>Plätze, die während der Runde neu entstehen (Spule auf einen neuen Platz umgelagert), kommen automatisch dazu.</li><li><b>Abschliessen</b> (Superuser): <b>[Close round…]</b> listet die noch nicht geprüften Plätze. Eine abgeschlossene Runde lässt sich nur noch ansehen und exportieren; ältere Runden oben unter <i>Round</i> wählen.</li></ul>Ohne offene Runde lässt sich weiterhin ein einzelnes Regal oder ein Platz mit <b>[Check a location without a round…]</b> prüfen - dann wird nichts in einer Runde festgehalten."), ('Vor dem Start', "<ul style='margin-left:-20px'><li>Jede Spule im Regal sollte ein Etikett haben. Spulen ohne Etikett lassen sich prüfen, indem man ihre Nummer eintippt, sofern man sie kennt.</li><li>Platz für Platz vorgehen - die Übersicht zeigt, was noch offen ist; man kann also aufhören und an einem anderen Tag weitermachen.</li><li>Ein QR-Code-Scanner ist nicht nötig. Nummer eintippen und Enter drücken funktioniert genauso.</li></ul>"), ('Schritt für Schritt', "<ol style='margin-left:-20px'><li>In der Übersicht auf die Kachel des Platzes klicken (z.&nbsp;B. <i>E12</i>). Das Scan-Fenster öffnet sich für genau diesen Platz und listet alle Spulen, die laut System dort stehen müssten. (Ohne Runde: Regal oder Platz eingeben und auf <b>[Load]</b> klicken.)</li><li>In das grosse Feld <i>Scan or type spool #</i> klicken und das Etikett jeder gefundenen Spule scannen oder die Nummer eintippen und Enter drücken. Das Feld leert sich nach jedem Scan, man kann also direkt weitermachen.</li><li>Auf die farbige Meldung unter dem Feld achten: Sie zeigt, was beim letzten Scan passiert ist (siehe Tabelle unten). <i>Found X of Y</i> zeigt den Fortschritt.</li><li>Ist der ganze Platz geprüft, auf <b>[Finish stock take…]</b> klicken und entscheiden, was mit den nicht gefundenen Spulen passieren soll. Das Ergebnis wird für diesen Platz gespeichert, die Kachel wird grün oder orange.</li></ol>"), ('Was beim Scannen passiert', "<table cellspacing='0' cellpadding='6' border='1' style='border-color:#d0d0d0'><tr><th align='left' style='background:#e9f6e9'>Situation</th><th align='left' style='background:#e9f6e9'>Was du siehst</th><th align='left' style='background:#e9f6e9'>Was gespeichert wird</th></tr><tr><td valign='top'>Spule wird hier erwartet</td><td valign='top'>Wird als gefunden markiert und grün angezeigt.</td><td valign='top'>Es wird nichts geändert.</td></tr><tr><td valign='top'>Spule ist an einem anderen Platz erfasst</td><td valign='top'>TrippleT fragt, wo sie wirklich steht (Vorschlag: der geprüfte Platz).</td><td valign='top'><b>OK</b> lagert sie sofort um. <b>Cancel</b> lässt den erfassten Platz unverändert.</td></tr><tr><td valign='top'>Spule ist als ausgebucht markiert</td><td valign='top'>TrippleT fragt, ob sie wieder eingelagert werden soll und wo.</td><td valign='top'><b>OK</b> lagert sie sofort wieder ein. Danach ihr Gewicht in der Spulenliste prüfen.</td></tr><tr><td valign='top'>Nummer existiert nicht</td><td valign='top'>Erscheint rot unter <i>Other scans</i>.</td><td valign='top'>Es wird nichts geändert. Etikett prüfen.</td></tr><tr><td valign='top'>Spule wurde schon gescannt</td><td valign='top'>Nur ein kurzer Hinweis.</td><td valign='top'>Es wird nichts geändert.</td></tr></table>"), ('Abschliessen', "Nach <b>[Finish stock take…]</b> zeigt TrippleT eine Zusammenfassung: wie viele Spulen gefunden wurden, welche Korrekturen schon gespeichert sind und welche Spulen fehlen. Für die fehlenden Spulen wählst du:<ul style='margin-left:-20px'><li><b>Discard missing spools</b>: Sie werden ausgebucht (Vermerk im Verlauf: <i>stock take</i>).</li><li><b>Keep them (no change)</b>: Es passiert nichts, z.&nbsp;B. wenn sie gerade an einer Maschine laufen.</li><li><b>Back to scanning</b>: Die Inventur geht weiter.</li></ul>"), ('Ergebnisse und Export', "Der Tab <b>Results</b> zeigt pro Spule, was wo gefunden wurde: Platz, Spule, Garn, Batch, Ergebnis, wer und wann. Eine Zusammenfassung oben zählt gefundene, fehlende, umgelagerte, wieder eingelagerte und unbekannte Spulen.<ul style='margin-left:-20px'><li><i>Only differences</i> (standardmässig an) blendet die Spulen aus, die genau dort waren, wo erwartet. <i>Location</i> filtert, z.&nbsp;B. <i>C</i> oder <i>C21</i>.</li><li>Fehlt eine Spule an einem Platz, wurde aber in derselben Runde an einem anderen gescannt, steht <i>seen at …</i> dabei - sie ist also nicht verloren.</li><li><b>[Export to Excel…]</b> speichert die Runde mit drei Blättern: Zusammenfassung, Plätze (Status, erwartet, gefunden, wer, wann) und alle Ergebnisse.</li></ul>"), ('Was wann gespeichert wird', "<ul style='margin-left:-20px'><li>Umlagern und Wieder-Einlagern werden <b>sofort</b> gespeichert, wenn du sie bestätigst.</li><li>Fehlende Spulen werden <b>nur</b> ausgebucht, wenn du am Ende auf <i>Discard missing spools</i> klickst.</li><li>Schliesst du das Fenster vorher (<b>Cancel</b>), fragt TrippleT nach. Bestätigte Korrekturen bleiben gespeichert, ausgebucht wird nichts.</li><li>Wird ein anderer Platz geladen, beginnt die Inventur neu. Die bisherigen Scans entfallen, gespeicherte Korrekturen bleiben.</li><li>In einer Runde wird das Ergebnis eines Platzes beim Abschliessen gespeichert. Wird das Scan-Fenster vorher geschlossen, bleibt der Platz offen (grau). Wird ein Platz nochmals geprüft, ersetzt das neue Ergebnis das alte.</li></ul>"), ('Gut zu wissen', "<ul style='margin-left:-20px'><li>Kein Etikett, oder der Scanner liest es nicht? Die Spule in der Liste <b>doppelklicken</b>, um sie von Hand als gefunden zu markieren. Sie erscheint blau und in den Ergebnissen mit dem Vermerk <i>marked by hand</i>, damit klar ist, dass sie nicht gescannt wurde. <b>Rechtsklick</b> → <i>Undo - not found</i> nimmt ein Gefunden zurück (auch nach einem falschen Scan).</li><li>Jede Korrektur steht im Spulen-Verlauf (<i>History…</i>), mit deinem Namen und dem Vermerk <i>stock take</i>.</li><li>Die Inventur prüft nur, ob eine Spule da ist und wo. Gewichte werden nicht geprüft; bei Bedarf danach in der Spulenliste korrigieren.</li><li>Spulen, die gerade an einer Maschine laufen, stehen nicht im Regal. Für sie <i>Keep them</i> wählen oder vorher nachsehen.</li></ul>")],

        "svg_flow": {
            "status": "Status",
            "t1": "1  Wareneingang", "t1b": "Garn, Batch, kg,", "t1c": "Anzahl, Lagerplatz",
            "t2": "2  Etikett", "t2c": "auf Spule kleben",
            "t3": "3  Im Regal", "t3a": "zählt zum Bestand,", "t3b": "erscheint in der", "t3c": "Übersicht",
            "t4": "4  Im Versuch", "t4a": "Spule pro Ply beim", "t4b": "Anlegen des", "t4c": "Versuchs wählen",
            "t5": "5  Ausbuchen", "t5a": "leer/unbrauchbar,", "t5b": "aus der Spulen-", "t5c": "liste ausgeblendet",
            "loop": "Gewicht von Hand anpassen",
            "trace": "Rückverfolgung:", "trace2": "„Used in…“ zeigt alle Versuche einer Spule",
        },
        "svg_map": {
            "help": "diese Hilfe",
            "hint": "Kästchen anklicken zum Abhaken · Doppelklick auf Weight / Location / Colour / Producer zum Ändern",
        },
    },

    # ───────────────────────────── Español ─────────────────────────────
    "es": {
        "window_title": "¿Cómo funciona Yarn Stock?",
        "close": "Cerrar",
        "tab_tasks": "¿Cómo hago…?",
        "tab_screen": "Pantalla",
        "tab_background": "Conceptos",

        "tasks_intro": (f"Busca tu pregunta abajo y sigue los pasos. {A} y {S1}–{S4} indican las "
                        "zonas de la pantalla, ver la pestaña <i>Pantalla</i>."),
        "h_find": "Buscar información",
        "tasks_find": [
            ("¿Cuánto tenemos de un hilo?",
             [f"Escribe parte del nombre del hilo o del lote en <i>Search yarn / batch…</i> encima de la vista general {S1}.",
              "<i>Total (kg)</i> y <i>Spools</i> muestran el stock de cada lote, <i>Yarn total (kg)</i> "
              "el de todos los lotes del hilo juntos."],
             ""),
            ("¿Dónde está guardado un hilo?",
             [f"Busca el hilo en {S1}. La columna <i>Locations</i> muestra todas las ubicaciones de ese lote.",
              f"Haz clic en la fila. La zona Spools {S2} muestra entonces la ubicación exacta de cada bobina."],
             ""),
            ("Tengo una bobina en la mano. ¿Qué es?",
             [f"Lee el número de bobina en la etiqueta (p.&nbsp;ej. <i>#213</i>) y escríbelo en <i>Go to spool #</i> {A}.",
              f"Pulsa Enter o {B('Go')}. La pantalla salta a su lote y resalta la bobina en {S2}."],
             "Las bobinas dadas de baja no se muestran. También funciona un lector de QR: escanea la etiqueta en el campo."),
            ("¿Qué hay en una estantería concreta?",
             [f"Escribe la letra de la estantería (p.&nbsp;ej. <i>E</i>) en <i>Rack lookup</i> {S4}. Se listan todas las ubicaciones que empiezan por ella.",
              f"Para una lista imprimible, haz clic en {B('Export to Excel')} al lado."],
             ""),
            ("¿Qué tenemos que volver a pedir?",
             [f"Pon el filtro de estado encima de la vista general {S1} en <i>Low</i>."],
             "Los hilos agotados por completo ya no aparecen en Yarn Stock. Los superusuarios reciben un aviso "
             "<i>Low</i> o <i>Empty</i> por hilo en la campana, y Manage Yarn muestra 0 kg. "
             "<i>Low</i> solo funciona en hilos con stock mínimo (columna <i>Min. stock (kg)</i>)."),
            ("¿En qué ensayos se usó una bobina?",
             [f"Haz clic en el lote en {S1}.",
              f"En {S2}, marca la(s) bobina(s) o haz clic en sus filas.",
              f"Haz clic en {B('Used in…')}. Muestra experimento, serie, ensayo y ply."],
             ""),
            ("¿Quién cambió una bobina y cuándo?",
             [f"Haz clic en el lote en {S1}.",
              f"En {S2}, marca o selecciona la(s) bobina(s). Sin selección se muestra todo el lote, también las bobinas dadas de baja.",
              f"Haz clic en {B('History…')}. Muestra fecha, usuario y qué se cambió de qué valor a cuál."],
             f"Para una sola bobina dada de baja: escribe su número en <i>Go to spool #</i> {A} y elige "
             "<i>Show history</i>. Los cambios se registran desde que existe esta función."),
            ("¿Cómo paso el stock a Excel?",
             [f"Filtra la vista general {S1} si hace falta (búsqueda / estado).",
              f"Haz clic en {B('Export to Excel')}. Se exportan exactamente las filas visibles."],
             ""),
            ("¿Por qué falta un hilo en la lista?",
             ["La vista general solo muestra hilos que tienen bobinas en stock ahora. Un hilo que nunca se "
              "recibió, o cuyas bobinas se han gastado y dado de baja, no tiene fila aquí.",
              "Todos los hilos, también los que no tienen stock, están en <b>Manage Yarn</b>. "
              f"Para añadir stock, registra la entrega con {B('New spool(s)')} (ver abajo)."],
             ""),
        ],
        "h_change": "Modificar el stock",
        "change_note": "Requiere nivel de acceso 2 o superior. Sin permiso de escritura, la pantalla muestra «View only».",
        "tasks_change": [
            ("Registrar una entrega nueva",
             [f"Si el hilo/lote ya existe, haz clic primero en su fila en {S1}. Hilo y lote quedan rellenados.",
              f"Haz clic en {B('New spool(s)')} en {S2}.",
              "Rellena hilo, lote, peso por bobina, número de bobinas y ubicación "
              "(opcionalmente color del tubo y fabricante). Haz clic en OK.",
              "Las bobinas nuevas se añaden automáticamente a la cola de etiquetas (casilla en el diálogo, "
              f"activada por defecto). Imprímelas con {B('Print Labels…')} en {S3}."],
             "Después, el lote de las bobinas nuevas queda seleccionado automáticamente en la vista general. "
             "Se crea una entrada por cada bobina física. Si el fabricante no está en la lista, "
             f"añádelo con el botón {B('+ New')} del diálogo o con {B('New producer…')}."),
            ("Imprimir etiquetas",
             [f"En {S2}, marca las bobinas en la primera columna (o {B('Select all')}).",
              f"Haz clic en {B('Add to label queue')}. Las bobinas aparecen en {S3}.",
              f"Haz clic en {B('Print Labels…')} en {S3}. Si la hoja ya está empezada, haz clic en la "
              "primera etiqueta libre de la vista previa.",
              "Guarda el PDF e imprímelo."],
             "Las bobinas impresas salen de la cola automáticamente. Las que no cupieron en la hoja se quedan."),
            ("Anotar el peso restante o cambiar una bobina de sitio",
             [f"Haz clic en el lote en {S1}.",
              f"En {S2}, haz doble clic en <i>Weight (kg)</i> o <i>Location</i> de la bobina, escribe el valor nuevo y pulsa Enter.",
              f"Haz clic en {B('Save Changes')}."],
             "Si haces clic en otra fila o botón antes de guardar, TrippleT pregunta si quieres guardar los cambios."),
            ("Dar de baja una bobina vacía o inservible",
             [f"En {S2}, marca la(s) bobina(s).",
              f"Haz clic en {B('Discard')} y confirma."],
             "La bobina desaparece de la lista, pero sigue en la base de datos, así que "
             "<i>Used in…</i> sigue funcionando para sus ensayos."),
            ("Corregir el nombre del lote o el fabricante de todo un lote",
             [f"En la vista general {S1} (o en Rack lookup {S4}), haz doble clic en la celda <i>Batch</i> o <i>Producer</i>.",
              "Escribe el nombre nuevo del lote o elige el fabricante y pulsa Enter."],
             "Esto cambia todas las bobinas del lote a la vez (también las dadas de baja) y se guarda al instante."),
            ("Hacer el inventario (todas las estanterías, ubicación por ubicación)",
             [f"En <i>Rack lookup</i> {S4}, haz clic en {B('Stock take…')}. La vista general muestra cada ubicación como una casilla.",
              "Haz clic en una ubicación gris (pendiente), escanea cada bobina que encuentres allí y haz clic en "
              f"{B('Finish stock take…')}.",
              "La casilla se vuelve verde (todo correcto) o naranja (diferencias). Sigue con la siguiente gris."],
             "Un superusuario inicia y cierra la ronda de inventario. Instrucciones completas: ver la pestaña <i>Inventario</i>."),
            ("Definir o cambiar el stock mínimo (solo superusuarios)",
             [f"En la vista general {S1}, haz doble clic en la celda <i>Min. stock (kg)</i> del hilo.",
              "Escribe el mínimo en kg y pulsa Enter. Déjalo vacío para no tener mínimo."],
             "El mínimo vale para todo el hilo (todos los lotes juntos) y se guarda al instante. "
             "También se puede definir en Manage Yarn."),
        ],

        "screen_caption": "Esquema con filas de ejemplo. La pantalla funciona de arriba abajo: elige una fila en (1) y trabaja con sus bobinas en (2).",
        "screen_areas": [
            ("(A) Go to spool #", "Salta directamente a una bobina por su número, p.&nbsp;ej. el de la etiqueta. También se puede escanear el código QR de la etiqueta."),
            ("(1) Overview",
             "<b>El punto de partida.</b> Una fila por hilo + lote con bobinas en stock: fabricante, número de "
             "bobinas, kg del lote, kg de todo el hilo, stock mínimo, ubicaciones y estado (verde OK, amarillo "
             "Low, rojo Empty; el estado vale para todo el hilo). La búsqueda y el filtro de estado acotan la "
             "lista; <i>Export to Excel</i> exporta lo que se ve. Doble clic en <i>Batch</i> o <i>Producer</i> "
             "lo corrige para todo el lote, en <i>Min. stock (kg)</i> (superusuarios) para todo el hilo."),
            ("(2) Spools",
             "<b>Las bobinas individuales</b> de la fila elegida en (1), una línea por bobina física. "
             "Las casillas seleccionan bobinas para <i>Add to label queue</i> y <i>Discard</i>. Peso, ubicación, "
             "color del tubo y fabricante se editan con doble clic y se guardan con <i>Save Changes</i>. "
             "<i>New spool(s)</i> registra una entrega, <i>Used in…</i> muestra los ensayos e <i>History…</i> "
             "el historial de cambios de las bobinas marcadas o seleccionadas. Se pliega con el botón ▾."),
            ("(3) Label queue",
             "<b>Bobinas a la espera de etiqueta.</b> Se reúnen aquí y luego se imprimen juntas con "
             "<i>Print Labels…</i> para aprovechar bien la hoja de etiquetas. <i>Remove selected</i> las "
             "quita de la cola sin imprimir."),
            ("(4) Rack lookup",
             "<b>Stock por estantería en lugar de por hilo.</b> Introduce el comienzo de una ubicación "
             "(p.&nbsp;ej. <i>E</i> o <i>E1</i>) para ver todos los hilos/lotes guardados allí; exportable a "
             "Excel. <i>Stock take…</i> abre la vista general del inventario con todas las ubicaciones (ver la pestaña <i>Inventario</i>)."),
        ],
        "h_elsewhere": "Dónde más aparece el stock",
        "elsewhere": _ul([
            "<b>Create Experiment</b>: al asignar un hilo a un ply se puede elegir la bobina concreta. "
            "Solo se ofrecen bobinas de ese hilo que estén en stock y pesen más de 0 kg.",
            "<b>Manage Yarn</b>: stock en kg por hilo (todos los lotes), también de hilos sin stock, y el campo "
            "<i>MinStock</i>.",
            "<b>Show Experiment</b>: al pasar el ratón sobre un hilo se ve dónde están sus bobinas.",
            "<b>Campana</b>: un aviso Low/Empty por hilo para superusuarios, con salto al hilo.",
        ]),

        "h_levels": "Tres niveles: hilo, lote, bobina",
        "levels": ("El <b>hilo</b> viene del catálogo de hilos (Manage Yarn). Debajo hay uno o varios "
                   "<b>lotes</b> (batches, p.&nbsp;ej. <tt>989G</tt>). Cada lote está formado por <b>bobinas</b> "
                   "individuales con su propio número (p.&nbsp;ej. <tt>#213</tt>), cada una con peso, ubicación, "
                   "color del tubo, fabricante y estado. La vista general muestra una fila por hilo + lote."),
        "h_life": "La vida de una bobina",
        "life_note": ("<b>Importante:</b> usar una bobina en un ensayo <b>no</b> reduce su peso "
                      "automáticamente. El stock solo es correcto cuando alguien anota el peso restante "
                      "en la zona Spools o da de baja la bobina vacía."),
        "h_status": "Estado: OK, Low, Empty",
        "status": ("Para cada <b>hilo</b> se suman los kilos de todas sus bobinas <i>in stock</i> de todos los "
                   "lotes (<i>Yarn total (kg)</i>) y se comparan con su stock mínimo (<i>Min. stock (kg)</i>). "
                   "Por eso todas las filas de lote de un hilo muestran el mismo estado."
                   + _status_table("El total del hilo es 0 kg.",
                                   "El total del hilo está por debajo del stock mínimo. Los superusuarios reciben un aviso.",
                                   "El total del hilo alcanza o supera el stock mínimo, o no hay ninguno definido.")),
        "h_good": "Conviene saber",
        "good": _ul([
            "El stock no es un libro de movimientos: cada bobina guarda su peso, ubicación y estado actuales. "
            "Además, cada cambio hecho en Yarn Stock queda registrado en el historial de la bobina (<i>History…</i>).",
            "Las bobinas dadas de baja no se borran, solo se ocultan. Un lote sin bobinas en stock no se "
            "muestra; un hilo agotado por completo desaparece de Yarn Stock (Manage Yarn lo sigue mostrando).",
            "Todos pueden consultar. Crear, editar y dar de baja bobinas requiere nivel de acceso 2 o superior. "
            "Solo los superusuarios pueden cambiar el stock mínimo. Yarn Stock no está disponible en el modo sin conexión.",
        ]),

        "tab_stocktake": 'Inventario',
        "st_intro": 'Un inventario comprueba si las bobinas que TrippleT registra en una estantería o un hueco están realmente allí, y permite corregir las diferencias en el momento.',
        "st_note": '<b>Consejo:</b> En estanterías grandes, revisa hueco por hueco (E1, E2, …). La lista es corta y puedes interrumpir y seguir más tarde sin perder la visión de conjunto.',
        "stocktake": [('Dónde encontrarlo', 'Yarn Stock → <i>Rack lookup</i> <b>(4)</b> → <b>[Stock take…]</b>. Se abre la vista general del inventario: una casilla por ubicación. Hace falta nivel de acceso 2 o superior. Si hay cambios sin guardar en la lista de bobinas, TrippleT pregunta primero si se deben guardar.'), ('La ronda de inventario', "Una ronda de inventario (p.&nbsp;ej. <i>Stock take October 2026</i>) abarca todas las ubicaciones. Queda abierta varios días y varias personas pueden trabajar a la vez: <b>[Refresh]</b> muestra lo que ya han hecho los compañeros.<ul style='margin-left:-20px'><li><b>Iniciar</b> (superusuarios): <b>[Start new round…]</b>. Todas las ubicaciones están marcadas; desmarca las que no se revisan en esta ronda (p.&nbsp;ej. una estantería vaciada).</li><li><b>Casillas</b>: gris = pendiente, verde = revisada y todo correcto, naranja = revisada con diferencias, discontinua = excluida. La casilla muestra <i>encontradas/esperadas</i> (y <i>+n</i> para otras bobinas escaneadas allí); las pendientes muestran cuántas bobinas hay registradas allí ahora.</li><li><b>Clic</b> en una casilla gris para revisar esa ubicación. <b>Clic derecho</b> para <i>Check again</i>, <i>Show results</i> y (superusuarios) <i>Leave out of this round</i> / <i>Include in this round</i>.</li><li>Las ubicaciones nuevas que aparecen durante la ronda (bobina movida a un hueco nuevo) se añaden automáticamente.</li><li><b>Cerrar</b> (superusuarios): <b>[Close round…]</b> lista las ubicaciones aún sin revisar. Una ronda cerrada solo se puede ver y exportar; las rondas anteriores se eligen arriba en <i>Round</i>.</li></ul>Sin una ronda abierta se puede seguir revisando una estantería o un hueco con <b>[Check a location without a round…]</b>; en ese caso no se registra nada en una ronda."), ('Antes de empezar', "<ul style='margin-left:-20px'><li>Cada bobina de la estantería debería tener etiqueta. Las bobinas sin etiqueta se pueden comprobar escribiendo su número, si se conoce.</li><li>Trabaja ubicación por ubicación: la vista general muestra lo pendiente, así que puedes parar y seguir otro día.</li><li>Un lector de QR es opcional. Escribir el número y pulsar Enter funciona igual.</li></ul>"), ('Paso a paso', "<ol style='margin-left:-20px'><li>En la vista general, haz clic en la casilla de la ubicación (p.&nbsp;ej. <i>E12</i>). La ventana de escaneo se abre para esa ubicación exacta y muestra todas las bobinas que deberían estar allí según el sistema. (Sin ronda: introduce una estantería o un hueco y haz clic en <b>[Load]</b>.)</li><li>Haz clic en el campo grande <i>Scan or type spool #</i> y escanea la etiqueta de cada bobina que encuentres, o escribe su número y pulsa Enter. El campo se vacía tras cada escaneo, así que puedes seguir directamente.</li><li>Fíjate en el mensaje de color debajo del campo: indica qué pasó con el último escaneo (ver tabla). <i>Found X of Y</i> muestra el progreso.</li><li>Cuando hayas revisado toda la ubicación, haz clic en <b>[Finish stock take…]</b> y decide qué hacer con las bobinas que no se encontraron. El resultado se guarda para esa ubicación y la casilla se vuelve verde o naranja.</li></ol>"), ('Qué pasa al escanear', "<table cellspacing='0' cellpadding='6' border='1' style='border-color:#d0d0d0'><tr><th align='left' style='background:#e9f6e9'>Situación</th><th align='left' style='background:#e9f6e9'>Qué ves</th><th align='left' style='background:#e9f6e9'>Qué se guarda</th></tr><tr><td valign='top'>La bobina se espera aquí</td><td valign='top'>Se marca como encontrada y se muestra en verde.</td><td valign='top'>No se cambia nada.</td></tr><tr><td valign='top'>La bobina está registrada en otra ubicación</td><td valign='top'>TrippleT pregunta dónde está realmente (propuesta: la ubicación que revisas).</td><td valign='top'><b>OK</b> la cambia de sitio al instante. <b>Cancel</b> deja la ubicación registrada.</td></tr><tr><td valign='top'>La bobina está dada de baja</td><td valign='top'>TrippleT pregunta si debe volver al stock y dónde.</td><td valign='top'><b>OK</b> la vuelve a poner en stock al instante. Después revisa su peso en la lista de bobinas.</td></tr><tr><td valign='top'>El número no existe</td><td valign='top'>Aparece en rojo en <i>Other scans</i>.</td><td valign='top'>No se cambia nada. Revisa la etiqueta.</td></tr><tr><td valign='top'>La bobina ya se escaneó</td><td valign='top'>Solo un aviso breve.</td><td valign='top'>No se cambia nada.</td></tr></table>"), ('Terminar', "Tras <b>[Finish stock take…]</b>, TrippleT muestra un resumen: cuántas bobinas se encontraron, qué correcciones ya están guardadas y qué bobinas faltan. Para las que faltan eliges:<ul style='margin-left:-20px'><li><b>Discard missing spools</b>: se dan de baja (nota en el historial: <i>stock take</i>).</li><li><b>Keep them (no change)</b>: no pasa nada, p.&nbsp;ej. si están en uso en una máquina.</li><li><b>Back to scanning</b>: se sigue con el inventario.</li></ul>"), ('Resultados y exportación', "La pestaña <b>Results</b> muestra por bobina qué se encontró dónde: ubicación, bobina, hilo, lote, resultado, quién y cuándo. Un resumen arriba cuenta las bobinas encontradas, que faltan, movidas, devueltas al stock y desconocidas.<ul style='margin-left:-20px'><li><i>Only differences</i> (activado por defecto) oculta las bobinas que estaban justo donde se esperaba. <i>Location</i> filtra, p.&nbsp;ej. <i>C</i> o <i>C21</i>.</li><li>Si una bobina falta en una ubicación pero se escaneó en otra en la misma ronda, aparece <i>seen at …</i>: no está perdida.</li><li><b>[Export to Excel…]</b> guarda la ronda con tres hojas: resumen, ubicaciones (estado, esperadas, encontradas, quién, cuándo) y todos los resultados.</li></ul>"), ('Qué se guarda y cuándo', "<ul style='margin-left:-20px'><li>Los cambios de ubicación y las vueltas al stock se guardan <b>al instante</b> cuando los confirmas.</li><li>Las bobinas que faltan se dan de baja <b>solo</b> si al final haces clic en <i>Discard missing spools</i>.</li><li>Si cierras la ventana antes (<b>Cancel</b>), TrippleT pide confirmación. Las correcciones confirmadas quedan guardadas, pero no se da de baja nada.</li><li>Al cargar otra ubicación, el inventario empieza de nuevo. Los escaneos hechos se descartan, las correcciones guardadas se mantienen.</li><li>En una ronda, el resultado de una ubicación se guarda al terminarla. Si cierras antes la ventana de escaneo, la ubicación queda pendiente (gris). Si revisas una ubicación otra vez, el resultado nuevo sustituye al anterior.</li></ul>"), ('Conviene saber', "<ul style='margin-left:-20px'><li>¿Sin etiqueta, o el lector no la lee? Haz <b>doble clic</b> en la bobina de la lista para marcarla como encontrada a mano. Se muestra en azul y con la nota <i>marked by hand</i> en los resultados, para que quede claro que no se escaneó. <b>Clic derecho</b> → <i>Undo - not found</i> deshace una marca de encontrada (también tras un escaneo equivocado).</li><li>Cada corrección queda en el historial de la bobina (<i>History…</i>) con tu nombre y la nota <i>stock take</i>.</li><li>El inventario solo comprueba si la bobina está y dónde. Los pesos no se comprueban; corrígelos después en la lista de bobinas si hace falta.</li><li>Las bobinas que se están usando en una máquina no están en la estantería. Para ellas elige <i>Keep them</i>, o compruébalo antes.</li></ul>")],

        "svg_flow": {
            "status": "Estado",
            "t1": "1  Entrada", "t1b": "hilo, lote, kg,", "t1c": "cantidad, ubicación",
            "t2": "2  Etiqueta", "t2c": "pegar en bobina",
            "t3": "3  En estantería", "t3a": "cuenta como stock,", "t3b": "aparece en la", "t3c": "vista general",
            "t4": "4  En un ensayo", "t4a": "elegir la bobina", "t4b": "por ply al crear", "t4c": "el ensayo",
            "t5": "5  Dar de baja", "t5a": "vacía o inservible,", "t5b": "se oculta de la", "t5c": "lista de bobinas",
            "loop": "Actualizar peso a mano",
            "trace": "Trazabilidad:", "trace2": "«Used in…» muestra todos los ensayos de una bobina",
        },
        "svg_map": {
            "help": "esta ayuda",
            "hint": "clic en la casilla para marcar · doble clic en Weight / Location / Colour / Producer para editar",
        },
    },

    # ───────────────────────────── 中文 ─────────────────────────────
    "zh": {
        "window_title": "Yarn Stock 如何使用？",
        "close": "关闭",
        "tab_tasks": "我该如何……？",
        "tab_screen": "界面说明",
        "tab_background": "背景知识",

        "tasks_intro": (f"在下方找到你的问题，按步骤操作。{A} 和 {S1}–{S4} 指界面上的各个区域，"
                        "见<i>界面说明</i>选项卡。"),
        "h_find": "查找信息",
        "tasks_find": [
            ("某种纱线我们还有多少？",
             [f"在概览 {S1} 上方的 <i>Search yarn / batch…</i> 中输入纱线名称或批次的一部分。",
              "<i>Total (kg)</i> 和 <i>Spools</i> 显示每个批次的库存，<i>Yarn total (kg)</i> "
              "显示该纱线所有批次的合计。"],
             ""),
            ("某种纱线存放在哪里？",
             [f"在 {S1} 中搜索该纱线。<i>Locations</i> 列列出该批次的所有库位。",
              f"点击该行。Spools 区域 {S2} 随即显示每个筒子的确切库位。"],
             ""),
            ("我手里有一个筒子，它是什么？",
             [f"读取标签上的筒子编号（例如 <i>#213</i>），输入到 <i>Go to spool #</i> {A} 中。",
              f"按 Enter 或 {B('Go')}。界面会跳转到它的批次，并在 {S2} 中高亮该筒子。"],
             "已报废的筒子不会显示。也可以使用二维码扫描枪：将标签扫描到该输入框中。"),
            ("某个货架上放了什么？",
             [f"在 <i>Rack lookup</i> {S4} 中输入货架字母（例如 <i>E</i>），以该字母开头的所有库位都会列出。",
              f"如需可打印的清单，点击旁边的 {B('Export to Excel')}。"],
             ""),
            ("哪些需要补货？",
             [f"将概览 {S1} 上方的状态筛选设为 <i>Low</i>。"],
             "完全用完的纱线不再显示在 Yarn Stock 中。超级用户会在铃铛中收到每种纱线的 "
             "<i>Low</i> 或 <i>Empty</i> 提醒，Manage Yarn 中显示 0 kg。"
             "<i>Low</i> 仅对设有最低库存的纱线有效（<i>Min. stock (kg)</i> 列）。"),
            ("某个筒子用在了哪些试验中？",
             [f"在 {S1} 中点击该批次。",
              f"在 {S2} 中勾选筒子或点击其所在行。",
              f"点击 {B('Used in…')}。将列出实验、系列、试验和 ply。"],
             ""),
            ("谁在什么时候修改了某个筒子？",
             [f"在 {S1} 中点击该批次。",
              f"在 {S2} 中勾选或选中筒子。不选择则显示整个批次，包括已报废的筒子。",
              f"点击 {B('History…')}。将列出日期、用户以及哪个值从什么改成了什么。"],
             f"单个已报废的筒子：在 <i>Go to spool #</i> {A} 中输入其编号，然后选择 "
             "<i>Show history</i>。修改记录从该功能上线时开始保存。"),
            ("如何把库存导出到 Excel？",
             [f"如有需要，先筛选概览 {S1}（搜索 / 状态）。",
              f"点击 {B('Export to Excel')}。导出的正是当前显示的行。"],
             ""),
            ("为什么列表中缺少某种纱线？",
             ["概览只列出当前有筒子在库的纱线。从未到货的纱线，或其筒子已全部用完并报废的纱线，"
              "在这里没有对应行。",
              "所有纱线（包括无库存的）都在 <b>Manage Yarn</b> 中。"
              f"要添加库存，请用 {B('New spool(s)')} 登记到货（见下文）。"],
             ""),
        ],
        "h_change": "修改库存",
        "change_note": "需要访问级别 2 或以上。否则界面显示“View only”。",
        "tasks_change": [
            ("登记新到货",
             [f"如果该纱线/批次已存在，先在 {S1} 中点击其所在行，纱线和批次会自动填入。",
              f"在 {S2} 中点击 {B('New spool(s)')}。",
              "填写纱线、批次、每个筒子的重量、筒子数量和库位"
              "（可选：筒管颜色和生产商）。点击 OK。",
              "新筒子会自动加入标签打印队列（对话框中的复选框，默认勾选）。"
              f"用 {S3} 中的 {B('Print Labels…')} 打印。"],
             "之后概览中会自动选中新筒子所属的批次。"
             "每个实物筒子创建一条记录。如果列表中没有该生产商，"
             f"可用对话框中的 {B('+ New')} 按钮或 {B('New producer…')} 添加。"),
            ("打印标签",
             [f"在 {S2} 中勾选第一列的筒子（或 {B('Select all')}）。",
              f"点击 {B('Add to label queue')}。筒子会出现在 {S3} 中。",
              f"点击 {S3} 中的 {B('Print Labels…')}。如果标签纸已部分使用，"
              "在预览中点击第一个空白标签位。",
              "保存 PDF 并打印。"],
             "已打印的筒子会自动移出队列。未能排进本张标签纸的筒子保留在队列中。"),
            ("录入剩余重量或移动筒子",
             [f"在 {S1} 中点击该批次。",
              f"在 {S2} 中双击该筒子的 <i>Weight (kg)</i> 或 <i>Location</i>，输入新值，按 Enter。",
              f"点击 {B('Save Changes')}。"],
             "如果保存前点击了其他行或按钮，TrippleT 会询问是否保存修改。"),
            ("将空的或不可用的筒子出库",
             [f"在 {S2} 中勾选筒子。",
              f"点击 {B('Discard')} 并确认。"],
             "该筒子从列表中消失，但仍保留在数据库中，"
             "因此对其用过的试验，<i>Used in…</i> 依然有效。"),
            ("修改整个批次的批次名称或生产商",
             [f"在概览 {S1}（或货架查询 {S4}）中双击 <i>Batch</i> 或 <i>Producer</i> 单元格。",
              "输入新的批次名称或选择生产商，按 Enter。"],
             "这会一次性修改该批次的所有筒子（包括已报废的），并立即保存。"),
            ("进行盘点（所有货架，逐个库位）",
             [f"在 <i>Rack lookup</i> {S4} 中点击 {B('Stock take…')}。概览以磁贴形式显示每个库位。",
              "点击一个灰色（未盘点）的库位，扫描在那里找到的每个筒子，然后点击 "
              f"{B('Finish stock take…')}。",
              "磁贴变为绿色（全部正确）或橙色（有差异）。继续下一个灰色库位。"],
             "盘点轮次由超级用户开始和结束。详细说明见<i>盘点</i>选项卡。"),
            ("设置或修改最低库存（仅限超级用户）",
             [f"在概览 {S1} 中双击该纱线的 <i>Min. stock (kg)</i> 单元格。",
              "输入以 kg 为单位的最低值并按 Enter。留空表示不设最低库存。"],
             "最低库存适用于整种纱线（所有批次合计），并立即保存。"
             "也可以在 Manage Yarn 中设置。"),
        ],

        "screen_caption": "带示例行的草图。界面自上而下使用：在 (1) 中选择一行，在 (2) 中处理其筒子。",
        "screen_areas": [
            ("(A) Go to spool #", "按编号直接跳转到某个筒子，例如标签上的编号。也可以扫描标签上的二维码。"),
            ("(1) Overview",
             "<b>起点。</b>每个仍有筒子在库的纱线 + 批次占一行：生产商、筒子数量、该批次的 kg、"
             "整种纱线的 kg、最低库存、库位和状态（绿色 OK、黄色 Low、红色 Empty；状态针对整种纱线）。"
             "搜索和状态筛选可缩小列表范围；<i>Export to Excel</i> 导出当前显示的内容。双击 "
             "<i>Batch</i> 或 <i>Producer</i> 可修改整个批次的值，双击 <i>Min. stock (kg)</i> "
             "（超级用户）可修改整种纱线的值。"),
            ("(2) Spools",
             "<b>单个筒子：</b>(1) 中所选行的筒子，每个实物筒子一行。"
             "复选框用于为 <i>Add to label queue</i> 和 <i>Discard</i> 选择筒子。重量、库位、"
             "筒管颜色和生产商通过双击编辑，并用 <i>Save Changes</i> 保存。"
             "<i>New spool(s)</i> 登记到货，<i>Used in…</i> 显示试验，<i>History…</i> "
             "显示所勾选或选中筒子的修改历史。可用 ▾ 按钮折叠。"),
            ("(3) Label queue",
             "<b>等待打印标签的筒子。</b>先在这里收集，然后用 "
             "<i>Print Labels…</i> 一起打印，以充分利用标签纸。<i>Remove selected</i> "
             "将筒子移出队列而不打印。"),
            ("(4) Rack lookup",
             "<b>按货架而非按纱线查看库存。</b>输入库位的开头（例如 <i>E</i> 或 "
             "<i>E1</i>），即可看到存放在那里的所有纱线/批次；可导出到 Excel。"
             "<i>Stock take…</i> 打开包含所有库位的盘点概览（见<i>盘点</i>选项卡）。"),
        ],
        "h_elsewhere": "库存还会显示在哪里",
        "elsewhere": _ul([
            "<b>Create Experiment</b>：为某个 ply 添加纱线时，可以选择具体的筒子。"
            "只提供该纱线在库且重量大于 0 kg 的筒子。",
            "<b>Manage Yarn</b>：每种纱线的库存 kg（所有批次），包括无库存的纱线，以及 "
            "<i>MinStock</i> 字段。",
            "<b>Show Experiment</b>：鼠标悬停在纱线上会显示其筒子的存放位置。",
            "<b>铃铛</b>：为超级用户提供每种纱线一条 Low/Empty 警告，可跳转到该纱线。",
        ]),

        "h_levels": "三个层级：纱线、批次、筒子",
        "levels": ("<b>纱线</b>来自纱线目录（Manage Yarn）。其下有一个或多个"
                   "<b>批次</b>（生产批号，例如 <tt>989G</tt>）。每个批次由若干带有自己编号"
                   "（例如 <tt>#213</tt>）的<b>筒子</b>组成，每个筒子都有重量、库位、"
                   "筒管颜色、生产商和状态。概览中每个纱线 + 批次占一行。"),
        "h_life": "筒子的生命周期",
        "life_note": ("<b>重要：</b>在试验中使用筒子<b>不会</b>自动减少其重量。"
                      "只有当有人在 Spools 区域录入剩余重量或将空筒子出库后，库存数字才正确。"),
        "h_status": "状态：OK、Low、Empty",
        "status": ("对每种<b>纱线</b>，将其所有<i>在库</i>筒子的公斤数跨所有批次相加"
                   "（<i>Yarn total (kg)</i>），并与其最低库存"
                   "（<i>Min. stock (kg)</i>）比较。因此同一纱线的所有批次行显示相同的状态。"
                   + _status_table("纱线合计为 0 kg。",
                                   "纱线合计低于最低库存。超级用户会收到通知。",
                                   "纱线合计达到或高于最低库存，或未设置最低库存。")),
        "h_good": "须知",
        "good": _ul([
            "库存不是记账流水：每个筒子保存其当前重量、库位和状态。"
            "在 Yarn Stock 中所做的每次修改还会记录在筒子历史中（<i>History…</i>）。",
            "已报废的筒子不会被删除，只是被隐藏。没有在库筒子的批次不显示；"
            "完全用完的纱线会从 Yarn Stock 中消失（Manage Yarn 中仍会列出）。",
            "所有人都可以查看。创建、编辑和报废筒子需要访问级别 2 或以上。"
            "只有超级用户可以修改最低库存。离线模式下无法使用 Yarn Stock。",
        ]),

        "tab_stocktake": '盘点',
        "st_intro": '盘点用于核对 TrippleT 中某个货架或货位登记的筒子是否真的在那里，并可当场修正差异。',
        "st_note": '<b>提示：</b>大货架请逐个货位盘点（E1、E2、…）。这样列表较短，可以中途停下、稍后继续，而不会失去整体把握。',
        "stocktake": [('在哪里找到', 'Yarn Stock → <i>Rack lookup</i> <b>(4)</b> → <b>[Stock take…]</b>。将打开盘点概览：每个库位一个磁贴。需要访问级别 2 或以上。如果筒子列表中有未保存的修改，TrippleT 会先询问是否保存。'), ('盘点轮次', "一个盘点轮次（例如 <i>Stock take October 2026</i>）涵盖所有库位。它可以持续开放数天，多人可同时工作——点击 <b>[Refresh]</b> 查看同事已完成的部分。<ul style='margin-left:-20px'><li><b>开始</b>（超级用户）：<b>[Start new round…]</b>。所有库位默认勾选；取消勾选本轮不盘点的库位（例如已清空的货架）。</li><li><b>磁贴</b>：灰色 = 尚未盘点，绿色 = 已盘点且全部正确，橙色 = 已盘点且有差异，虚线 = 已排除。磁贴显示<i>找到/应有</i>（以及在那里扫描到的其他筒子 <i>+n</i>）；未盘点的磁贴显示当前登记在那里的筒子数量。</li><li><b>点击</b>灰色磁贴即可盘点该库位。<b>右键</b>可选 <i>Check again</i>、<i>Show results</i> 以及（超级用户）<i>Leave out of this round</i> / <i>Include in this round</i>。</li><li>轮次进行中新出现的库位（筒子被移到新货位）会自动加入。</li><li><b>结束</b>（超级用户）：<b>[Close round…]</b> 列出尚未盘点的库位。已结束的轮次只能查看和导出；可在顶部（<i>Round</i>）选择以前的轮次。</li></ul>没有开放的轮次时，仍可用 <b>[Check a location without a round…]</b> 盘点单个货架或货位——此时不会记录到任何轮次中。"), ('开始之前', "<ul style='margin-left:-20px'><li>确保货架上的每个筒子都贴有标签。没有标签的筒子，如果知道编号，可以手动输入编号来核对。</li><li>逐个库位进行——概览会显示哪些尚未盘点，因此可以停下来改天继续。</li><li>二维码扫描枪不是必需的。输入编号并按 Enter 效果相同。</li></ul>"), ('操作步骤', "<ol style='margin-left:-20px'><li>在概览中点击该库位的磁贴（例如 <i>E12</i>）。扫描窗口会针对该库位打开，并列出系统中应在那里的所有筒子。（无轮次时：输入货架或货位，然后点击 <b>[Load]</b>。）</li><li>点击大输入框 <i>Scan or type spool #</i>，扫描找到的每个筒子的标签，或输入编号并按 Enter。每次扫描后输入框会清空，可以直接继续。</li><li>注意输入框下方的彩色提示：它说明上一次扫描的结果（见下表）。<i>Found X of Y</i> 显示进度。</li><li>整个库位核对完毕后，点击 <b>[Finish stock take…]</b>，并决定如何处理未找到的筒子。结果将保存到该库位，磁贴变为绿色或橙色。</li></ol>"), ('扫描时会发生什么', "<table cellspacing='0' cellpadding='6' border='1' style='border-color:#d0d0d0'><tr><th align='left' style='background:#e9f6e9'>情况</th><th align='left' style='background:#e9f6e9'>你看到的</th><th align='left' style='background:#e9f6e9'>保存的内容</th></tr><tr><td valign='top'>筒子应在此处</td><td valign='top'>标记为已找到并显示为绿色。</td><td valign='top'>不做任何修改。</td></tr><tr><td valign='top'>筒子登记在其他库位</td><td valign='top'>TrippleT 询问它实际在哪里（建议：正在盘点的库位）。</td><td valign='top'><b>OK</b> 立即移动它。<b>Cancel</b> 保留其登记的库位。</td></tr><tr><td valign='top'>筒子标记为已报废</td><td valign='top'>TrippleT 询问是否将其重新入库以及放在哪里。</td><td valign='top'><b>OK</b> 立即将其重新入库。之后请在筒子列表中检查其重量。</td></tr><tr><td valign='top'>编号不存在</td><td valign='top'>以红色显示在 <i>Other scans</i> 下。</td><td valign='top'>不做任何修改。请检查标签。</td></tr><tr><td valign='top'>筒子已扫描过</td><td valign='top'>仅显示简短提示。</td><td valign='top'>不做任何修改。</td></tr></table>"), ('完成', "点击 <b>[Finish stock take…]</b> 后，TrippleT 显示汇总：找到多少个筒子、哪些修正已保存、哪些筒子缺失。对缺失的筒子，你可以选择：<ul style='margin-left:-20px'><li><b>Discard missing spools</b>：将其标记为已报废（历史备注：<i>stock take</i>）。</li><li><b>Keep them (no change)</b>：不做任何操作，例如它们此刻正在机器上使用。</li><li><b>Back to scanning</b>：继续盘点。</li></ul>"), ('结果与导出', "<b>Results</b> 选项卡按筒子列出在哪里找到了什么：库位、筒子、纱线、批次、结果、操作人和时间。顶部的汇总行统计已找到、缺失、已移动、已重新入库和未知的筒子数。<ul style='margin-left:-20px'><li><i>Only differences</i>（默认开启）隐藏恰好在预期位置的筒子。<i>Location</i> 用于筛选，例如 <i>C</i> 或 <i>C21</i>。</li><li>某个筒子在一个库位缺失、但在同一轮次中于另一个库位被扫描到时，会标记为 <i>seen at …</i>——它并没有丢失。</li><li><b>[Export to Excel…]</b> 将本轮保存为三个工作表：汇总、库位（状态、应有、找到、操作人、时间）和全部结果。</li></ul>"), ('何时保存什么', "<ul style='margin-left:-20px'><li>移动和重新入库在你确认时<b>立即</b>保存。</li><li>缺失的筒子<b>只有</b>在最后点击 <i>Discard missing spools</i> 时才会报废。</li><li>如果提前关闭窗口（<b>Cancel</b>），TrippleT 会要求确认。已确认的修正仍会保留，但不会报废任何筒子。</li><li>加载另一个库位会重新开始。之前的扫描将被丢弃，已保存的修正保留。</li><li>在轮次中，库位的结果在完成时保存。如果提前关闭扫描窗口，该库位保持未盘点（灰色）。再次盘点某个库位会替换其之前的结果。</li></ul>"), ('须知', "<ul style='margin-left:-20px'><li>没有标签，或扫描枪读不出来？在列表中<b>双击</b>该筒子即可手动标记为已找到。它会显示为蓝色，并在结果中注明 <i>marked by hand</i>，以表明它不是扫描的。<b>右键</b> → <i>Undo - not found</i> 可撤销已找到标记（扫错后也可用）。</li><li>每次修正都会以你的名字和备注 <i>stock take</i> 记录在筒子历史（<i>History…</i>）中。</li><li>盘点只检查筒子是否存在及其库位，不检查重量；如有需要，之后在筒子列表中修正。</li><li>正在机器上使用的筒子不在货架上。对这些筒子请选择 <i>Keep them</i>，或事先核实。</li></ul>")],

        "svg_flow": {
            "status": "状态",
            "t1": "1  到货入库", "t1b": "纱线、批次、kg、", "t1c": "数量、库位",
            "t2": "2  标签", "t2c": "贴在筒子上",
            "t3": "3  上架", "t3a": "计入库存，", "t3b": "显示在", "t3c": "概览中",
            "t4": "4  用于试验", "t4a": "创建试验时", "t4b": "按 ply", "t4c": "选择筒子",
            "t5": "5  报废出库", "t5a": "空的或不可用，", "t5b": "从筒子列表", "t5c": "中隐藏",
            "loop": "手动更新重量",
            "trace": "可追溯性：", "trace2": "“Used in…”列出筒子的所有试验",
        },
        "svg_map": {
            "help": "本帮助",
            "hint": "点击方框勾选筒子 · 双击 Weight / Location / Colour / Producer 进行编辑",
        },
    },
}
