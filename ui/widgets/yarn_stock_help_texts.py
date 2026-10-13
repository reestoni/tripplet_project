# ui/widgets/yarn_stock_help_texts.py
"""Texte der Yarn-Stock-Hilfe (ui/widgets/yarn_stock_help_dialog.py) in
Englisch, Deutsch und Spanisch (Nutzerwunsch 2026-10-13: Sprachumschaltung
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
             ("es", "Español", "flag_es.svg")]
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
              "Print labels for the new spools (next task)."],
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
            ("Do a stock take of a rack",
             [f"In <i>Rack lookup</i> {S4}, click {B('Start stock take…')}.",
              "Enter the rack or slot, scan every spool you find there, then click "
              f"{B('Finish stock take…')}."],
             "Full instructions: see the <i>Stock take</i> tab."),
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
             "<i>Start stock take…</i> opens the stock take for that rack (see the <i>Stock take</i> tab)."),
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
        "stocktake": [('Where to find it', 'Yarn Stock → <i>Rack lookup</i> <b>(4)</b> → <b>[Start stock take…]</b>. A separate window opens. You need access level 2 or higher. If you have unsaved changes in the spool list, TrippleT asks you to save them first.'), ('Before you start', "<ul style='margin-left:-20px'><li>Make sure every spool on the shelf has a label. Spools without a label can be checked by typing their number, if you know it.</li><li>Plan one rack, or for big racks one slot at a time (e.g. <i>E1</i> instead of <i>E</i>).</li><li>A QR code scanner is optional. Typing the number and pressing Enter works the same way.</li></ul>"), ('Step by step', "<ol style='margin-left:-20px'><li>Enter the rack (e.g. <i>E</i>) or slot (e.g. <i>E12</i>) and click <b>[Load]</b>. If you typed a rack in Rack lookup before, it is filled in already. TrippleT lists every spool that should be there according to the system (all locations starting with what you entered).</li><li>Click into the large field <i>Scan or type spool #</i> and scan the label of each spool you find, or type its number and press Enter. The field is cleared after each scan, so you can continue straight away.</li><li>Watch the coloured message under the field: it tells you what happened with the last scan (see table below). <i>Found X of Y</i> shows your progress.</li><li>When you have checked the whole shelf, click <b>[Finish stock take…]</b> and decide what to do with the spools that were not found.</li></ol>"), ('What happens when you scan', "<table cellspacing='0' cellpadding='6' border='1' style='border-color:#d0d0d0'><tr><th align='left' style='background:#e9f6e9'>Situation</th><th align='left' style='background:#e9f6e9'>What you see</th><th align='left' style='background:#e9f6e9'>What is saved</th></tr><tr><td valign='top'>Spool is expected here</td><td valign='top'>Marked as found and shown in green.</td><td valign='top'>Nothing is changed.</td></tr><tr><td valign='top'>Spool is registered at another location</td><td valign='top'>TrippleT asks where it really is (suggestion: the location you are checking).</td><td valign='top'><b>OK</b> moves it immediately. <b>Cancel</b> leaves it where it is registered.</td></tr><tr><td valign='top'>Spool is marked as discarded</td><td valign='top'>TrippleT asks whether to put it back in stock and where.</td><td valign='top'><b>OK</b> puts it back in stock immediately. Check its weight afterwards in the spool list.</td></tr><tr><td valign='top'>Number does not exist</td><td valign='top'>Shown in red under <i>Other scans</i>.</td><td valign='top'>Nothing is changed. Check the label.</td></tr><tr><td valign='top'>Spool was already scanned</td><td valign='top'>Short note only.</td><td valign='top'>Nothing is changed.</td></tr></table>"), ('Finishing', "After <b>[Finish stock take…]</b> TrippleT shows a summary: how many spools were found, which corrections were already saved, and which spools are missing. For the missing spools you choose:<ul style='margin-left:-20px'><li><b>Discard missing spools</b>: they are marked as discarded (history note: <i>stock take</i>).</li><li><b>Keep them (no change)</b>: nothing happens, e.g. if they are only in use at a machine right now.</li><li><b>Back to scanning</b>: continue the stock take.</li></ul>"), ('What is saved when', "<ul style='margin-left:-20px'><li>Moves and put-backs are saved <b>immediately</b> when you confirm them.</li><li>Missing spools are discarded <b>only</b> when you click <i>Discard missing spools</i> at the end.</li><li>If you close the window early (<b>Cancel</b>), TrippleT asks for confirmation. Corrections already confirmed stay saved, but nothing is discarded.</li><li>Loading a different location starts over. Scans so far are dropped, saved corrections stay.</li></ul>"), ('Good to know', "<ul style='margin-left:-20px'><li>Every correction is recorded in the spool history (<i>History…</i>) with your name and the note <i>stock take</i>.</li><li>The stock take checks presence and location only. Weights are not checked; correct them in the spool list afterwards if needed.</li><li>Spools that are in use at a machine are not on the shelf. Choose <i>Keep them</i> for those, or check them first.</li></ul>")],

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
              "Etiketten für die neuen Spulen drucken (nächste Aufgabe)."],
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
            ("Inventur eines Regals machen",
             [f"Im <i>Rack lookup</i> {S4} auf {B('Start stock take…')} klicken.",
              "Regal oder Platz eingeben, jede Spule scannen, die dort steht, dann auf "
              f"{B('Finish stock take…')} klicken."],
             "Ausführliche Anleitung: siehe Tab <i>Inventur</i>."),
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
             "exportierbar. <i>Start stock take…</i> startet die Inventur für dieses Regal (siehe Tab <i>Inventur</i>)."),
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
        "stocktake": [('Wo finde ich sie?', 'Yarn Stock → <i>Rack lookup</i> <b>(4)</b> → <b>[Start stock take…]</b>. Es öffnet sich ein eigenes Fenster. Dafür ist Access Level 2 oder höher nötig. Gibt es in der Spulenliste noch ungespeicherte Änderungen, fragt TrippleT zuerst, ob sie gespeichert werden sollen.'), ('Vor dem Start', "<ul style='margin-left:-20px'><li>Jede Spule im Regal sollte ein Etikett haben. Spulen ohne Etikett lassen sich prüfen, indem man ihre Nummer eintippt, sofern man sie kennt.</li><li>Ein Regal pro Durchgang, bei grossen Regalen besser Fach für Fach (z.&nbsp;B. <i>E1</i> statt <i>E</i>).</li><li>Ein QR-Code-Scanner ist nicht nötig. Nummer eintippen und Enter drücken funktioniert genauso.</li></ul>"), ('Schritt für Schritt', "<ol style='margin-left:-20px'><li>Regal (z.&nbsp;B. <i>E</i>) oder Platz (z.&nbsp;B. <i>E12</i>) eingeben und auf <b>[Load]</b> klicken. Stand im Rack lookup schon ein Regal, ist es bereits eingetragen. TrippleT listet alle Spulen, die laut System dort stehen müssten (alle Plätze, die mit der Eingabe beginnen).</li><li>In das grosse Feld <i>Scan or type spool #</i> klicken und das Etikett jeder gefundenen Spule scannen oder die Nummer eintippen und Enter drücken. Das Feld leert sich nach jedem Scan, man kann also direkt weitermachen.</li><li>Auf die farbige Meldung unter dem Feld achten: Sie zeigt, was beim letzten Scan passiert ist (siehe Tabelle unten). <i>Found X of Y</i> zeigt den Fortschritt.</li><li>Ist das ganze Regal geprüft, auf <b>[Finish stock take…]</b> klicken und entscheiden, was mit den nicht gefundenen Spulen passieren soll.</li></ol>"), ('Was beim Scannen passiert', "<table cellspacing='0' cellpadding='6' border='1' style='border-color:#d0d0d0'><tr><th align='left' style='background:#e9f6e9'>Situation</th><th align='left' style='background:#e9f6e9'>Was du siehst</th><th align='left' style='background:#e9f6e9'>Was gespeichert wird</th></tr><tr><td valign='top'>Spule wird hier erwartet</td><td valign='top'>Wird als gefunden markiert und grün angezeigt.</td><td valign='top'>Es wird nichts geändert.</td></tr><tr><td valign='top'>Spule ist an einem anderen Platz erfasst</td><td valign='top'>TrippleT fragt, wo sie wirklich steht (Vorschlag: der geprüfte Platz).</td><td valign='top'><b>OK</b> lagert sie sofort um. <b>Cancel</b> lässt den erfassten Platz unverändert.</td></tr><tr><td valign='top'>Spule ist als ausgebucht markiert</td><td valign='top'>TrippleT fragt, ob sie wieder eingelagert werden soll und wo.</td><td valign='top'><b>OK</b> lagert sie sofort wieder ein. Danach ihr Gewicht in der Spulenliste prüfen.</td></tr><tr><td valign='top'>Nummer existiert nicht</td><td valign='top'>Erscheint rot unter <i>Other scans</i>.</td><td valign='top'>Es wird nichts geändert. Etikett prüfen.</td></tr><tr><td valign='top'>Spule wurde schon gescannt</td><td valign='top'>Nur ein kurzer Hinweis.</td><td valign='top'>Es wird nichts geändert.</td></tr></table>"), ('Abschliessen', "Nach <b>[Finish stock take…]</b> zeigt TrippleT eine Zusammenfassung: wie viele Spulen gefunden wurden, welche Korrekturen schon gespeichert sind und welche Spulen fehlen. Für die fehlenden Spulen wählst du:<ul style='margin-left:-20px'><li><b>Discard missing spools</b>: Sie werden ausgebucht (Vermerk im Verlauf: <i>stock take</i>).</li><li><b>Keep them (no change)</b>: Es passiert nichts, z.&nbsp;B. wenn sie gerade an einer Maschine laufen.</li><li><b>Back to scanning</b>: Die Inventur geht weiter.</li></ul>"), ('Was wann gespeichert wird', "<ul style='margin-left:-20px'><li>Umlagern und Wieder-Einlagern werden <b>sofort</b> gespeichert, wenn du sie bestätigst.</li><li>Fehlende Spulen werden <b>nur</b> ausgebucht, wenn du am Ende auf <i>Discard missing spools</i> klickst.</li><li>Schliesst du das Fenster vorher (<b>Cancel</b>), fragt TrippleT nach. Bestätigte Korrekturen bleiben gespeichert, ausgebucht wird nichts.</li><li>Wird ein anderer Platz geladen, beginnt die Inventur neu. Die bisherigen Scans entfallen, gespeicherte Korrekturen bleiben.</li></ul>"), ('Gut zu wissen', "<ul style='margin-left:-20px'><li>Jede Korrektur steht im Spulen-Verlauf (<i>History…</i>), mit deinem Namen und dem Vermerk <i>stock take</i>.</li><li>Die Inventur prüft nur, ob eine Spule da ist und wo. Gewichte werden nicht geprüft; bei Bedarf danach in der Spulenliste korrigieren.</li><li>Spulen, die gerade an einer Maschine laufen, stehen nicht im Regal. Für sie <i>Keep them</i> wählen oder vorher nachsehen.</li></ul>")],

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
              "Imprime las etiquetas de las bobinas nuevas (siguiente tarea)."],
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
            ("Hacer el inventario de una estantería",
             [f"En <i>Rack lookup</i> {S4}, haz clic en {B('Start stock take…')}.",
              "Introduce la estantería o el hueco, escanea cada bobina que encuentres allí y haz clic en "
              f"{B('Finish stock take…')}."],
             "Instrucciones completas: ver la pestaña <i>Inventario</i>."),
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
             "Excel. <i>Start stock take…</i> abre el inventario de esa estantería (ver la pestaña <i>Inventario</i>)."),
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
        "stocktake": [('Dónde encontrarlo', 'Yarn Stock → <i>Rack lookup</i> <b>(4)</b> → <b>[Start stock take…]</b>. Se abre una ventana aparte. Hace falta nivel de acceso 2 o superior. Si hay cambios sin guardar en la lista de bobinas, TrippleT pregunta primero si se deben guardar.'), ('Antes de empezar', "<ul style='margin-left:-20px'><li>Cada bobina de la estantería debería tener etiqueta. Las bobinas sin etiqueta se pueden comprobar escribiendo su número, si se conoce.</li><li>Una estantería por vez; en estanterías grandes, mejor hueco por hueco (p.&nbsp;ej. <i>E1</i> en lugar de <i>E</i>).</li><li>Un lector de QR es opcional. Escribir el número y pulsar Enter funciona igual.</li></ul>"), ('Paso a paso', "<ol style='margin-left:-20px'><li>Introduce la estantería (p.&nbsp;ej. <i>E</i>) o el hueco (p.&nbsp;ej. <i>E12</i>) y haz clic en <b>[Load]</b>. Si antes escribiste una estantería en Rack lookup, ya está rellenada. TrippleT muestra todas las bobinas que deberían estar allí según el sistema (todas las ubicaciones que empiezan por lo introducido).</li><li>Haz clic en el campo grande <i>Scan or type spool #</i> y escanea la etiqueta de cada bobina que encuentres, o escribe su número y pulsa Enter. El campo se vacía tras cada escaneo, así que puedes seguir directamente.</li><li>Fíjate en el mensaje de color debajo del campo: indica qué pasó con el último escaneo (ver tabla). <i>Found X of Y</i> muestra el progreso.</li><li>Cuando hayas revisado toda la estantería, haz clic en <b>[Finish stock take…]</b> y decide qué hacer con las bobinas que no se encontraron.</li></ol>"), ('Qué pasa al escanear', "<table cellspacing='0' cellpadding='6' border='1' style='border-color:#d0d0d0'><tr><th align='left' style='background:#e9f6e9'>Situación</th><th align='left' style='background:#e9f6e9'>Qué ves</th><th align='left' style='background:#e9f6e9'>Qué se guarda</th></tr><tr><td valign='top'>La bobina se espera aquí</td><td valign='top'>Se marca como encontrada y se muestra en verde.</td><td valign='top'>No se cambia nada.</td></tr><tr><td valign='top'>La bobina está registrada en otra ubicación</td><td valign='top'>TrippleT pregunta dónde está realmente (propuesta: la ubicación que revisas).</td><td valign='top'><b>OK</b> la cambia de sitio al instante. <b>Cancel</b> deja la ubicación registrada.</td></tr><tr><td valign='top'>La bobina está dada de baja</td><td valign='top'>TrippleT pregunta si debe volver al stock y dónde.</td><td valign='top'><b>OK</b> la vuelve a poner en stock al instante. Después revisa su peso en la lista de bobinas.</td></tr><tr><td valign='top'>El número no existe</td><td valign='top'>Aparece en rojo en <i>Other scans</i>.</td><td valign='top'>No se cambia nada. Revisa la etiqueta.</td></tr><tr><td valign='top'>La bobina ya se escaneó</td><td valign='top'>Solo un aviso breve.</td><td valign='top'>No se cambia nada.</td></tr></table>"), ('Terminar', "Tras <b>[Finish stock take…]</b>, TrippleT muestra un resumen: cuántas bobinas se encontraron, qué correcciones ya están guardadas y qué bobinas faltan. Para las que faltan eliges:<ul style='margin-left:-20px'><li><b>Discard missing spools</b>: se dan de baja (nota en el historial: <i>stock take</i>).</li><li><b>Keep them (no change)</b>: no pasa nada, p.&nbsp;ej. si están en uso en una máquina.</li><li><b>Back to scanning</b>: se sigue con el inventario.</li></ul>"), ('Qué se guarda y cuándo', "<ul style='margin-left:-20px'><li>Los cambios de ubicación y las vueltas al stock se guardan <b>al instante</b> cuando los confirmas.</li><li>Las bobinas que faltan se dan de baja <b>solo</b> si al final haces clic en <i>Discard missing spools</i>.</li><li>Si cierras la ventana antes (<b>Cancel</b>), TrippleT pide confirmación. Las correcciones confirmadas quedan guardadas, pero no se da de baja nada.</li><li>Al cargar otra ubicación, el inventario empieza de nuevo. Los escaneos hechos se descartan, las correcciones guardadas se mantienen.</li></ul>"), ('Conviene saber', "<ul style='margin-left:-20px'><li>Cada corrección queda en el historial de la bobina (<i>History…</i>) con tu nombre y la nota <i>stock take</i>.</li><li>El inventario solo comprueba si la bobina está y dónde. Los pesos no se comprueban; corrígelos después en la lista de bobinas si hace falta.</li><li>Las bobinas que se están usando en una máquina no están en la estantería. Para ellas elige <i>Keep them</i>, o compruébalo antes.</li></ul>")],

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
}
