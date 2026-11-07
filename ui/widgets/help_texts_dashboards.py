# ui/widgets/help_texts_dashboards.py
"""Hilfetexte Dashboards (EN/DE/ES) fuer ui/widgets/multilang_help.py.

Spiegelt ui/screen_dashboards.py (Liste My dashboards / Shared with me mit
Suche, Dashboard schreibgeschuetzt: Slicer, Klick in Balken/Zellen,
Drill-down, Seiten, Tooltips; PDF; Edit in Smart Chart fuer Ersteller und
Personen mit Bearbeiten-Recht) und das Teilen in Smart Chart
(ui/smart_share_dialog.py). Bei Aenderungen dort hier (alle 3 Sprachen)
nachziehen.
"""


def B(name: str) -> str:
    return f"<b>[{name}]</b>"


TEXTS = {
    "en": {
        "window_title": "How do Dashboards work?",
        "close": "Close",
        "tabs": [
            {"key": "tasks", "title": "How do I…?", "blocks": [
                ("p", "Here you <b>look at</b> dashboards: your own and the ones colleagues shared with you. "
                      "Dashboards are built in <i>Smart Chart → Dashboard</i>."),
                ("h", "Looking"),
                ("task", "Open a dashboard",
                 ["Click it in the list on the left: <i>My dashboards</i> are yours, <i>Shared with me</i> come "
                  "from colleagues (with their name).",
                  "Type into <i>Search a dashboard or owner…</i> to find one quickly."],
                 "The page opens the dashboard you looked at last."),
                ("task", "Filter what you see",
                 ["Pick values in the <b>slicers</b> (lists, dropdowns, tiles, ranges).",
                  "Click a bar, a slice or a point: the other visuals grey out everything else (cards, tables and the matrix show only that value). Click it again to undo.",
                  "Double-click a bar to go one level deeper (drill-down), if the dashboard offers it.",
                  "The tabs at the bottom switch between the pages."],
                 "Nothing of this is saved - the next time the dashboard opens as its creator saved it. Open the "
                 "<i>Filters</i> strip on the right to see which filters the dashboard uses."),
                ("task", "Print or send a dashboard",
                 [f"Click {B('PDF')} and choose this page or all pages."]),
                ("task", "See the latest data",
                 [f"Click {B('Reload')} (F5) - it loads new trials and new or changed dashboards."]),
                ("h", "Changing and sharing"),
                ("task", "Change a dashboard",
                 [f"Click {B('Edit in Smart Chart')} - you see it only on your own dashboards and on those "
                  "shared with you <i>to edit</i>.",
                  f"Change it in Smart Chart and click {B('Save view')}."],
                 "Here on the Dashboards page nothing can be changed except the slicers."),
                ("task", "Share my dashboard with colleagues",
                 [f"Open it in Smart Chart and click {B('Share…')}.",
                  "Tick <i>Everybody can view it</i>, or add people and groups (read, write, admin, superuser), "
                  "each with <i>Can view</i> or <i>Can view and edit</i>.",
                  f"Click {B('Save')}."],
                 "Only the creator can share or delete a dashboard. People who may edit it can save their changes, "
                 "but not share it further."),
            ]},
        ],
    },
    "de": {
        "window_title": "Wie funktionieren Dashboards?",
        "close": "Schliessen",
        "tabs": [
            {"key": "tasks", "title": "Wie mache ich…?", "blocks": [
                ("p", "Hier <b>schaust</b> du Dashboards an: deine eigenen und die, die Kollegen für dich "
                      "freigegeben haben. Gebaut werden Dashboards in <i>Smart Chart → Dashboard</i>."),
                ("h", "Anschauen"),
                ("task", "Ein Dashboard öffnen",
                 ["Links in der Liste anklicken: <i>My dashboards</i> sind deine, <i>Shared with me</i> kommen von "
                  "Kollegen (mit deren Namen).",
                  "In <i>Search a dashboard or owner…</i> tippen, um eines schnell zu finden."],
                 "Die Seite öffnet das Dashboard, das du zuletzt angeschaut hast."),
                ("task", "Filtern, was du siehst",
                 ["In den <b>Slicern</b> Werte wählen (Listen, Dropdowns, Knöpfe, Bereiche).",
                  "Auf einen Balken, ein Kuchenstück oder einen Punkt klicken: die anderen Visuals grauen alles andere "
                  "aus (Cards, Tabellen und die Matrix zeigen nur noch diesen Wert). Nochmals klicken hebt es auf.",
                  "Doppelklick auf einen Balken geht eine Ebene tiefer (Drill-down), wenn das Dashboard es anbietet.",
                  "Die Reiter unten wechseln zwischen den Seiten."],
                 "Nichts davon wird gespeichert - beim nächsten Mal öffnet sich das Dashboard so, wie es der "
                 "Ersteller gespeichert hat. Den Streifen <i>Filters</i> rechts aufklappen, um zu sehen, welche "
                 "Filter das Dashboard verwendet."),
                ("task", "Ein Dashboard drucken oder verschicken",
                 [f"Auf {B('PDF')} klicken und diese Seite oder alle Seiten wählen."]),
                ("task", "Die neusten Daten sehen",
                 [f"Auf {B('Reload')} (F5) klicken - lädt neue Versuche und neue oder geänderte Dashboards."]),
                ("h", "Ändern und teilen"),
                ("task", "Ein Dashboard ändern",
                 [f"Auf {B('Edit in Smart Chart')} klicken - erscheint nur bei deinen eigenen Dashboards und bei "
                  "denen, die dir <i>zum Bearbeiten</i> freigegeben wurden.",
                  f"In Smart Chart ändern und {B('Save view')} klicken."],
                 "Hier auf der Seite Dashboards lässt sich ausser den Slicern nichts verändern."),
                ("task", "Mein Dashboard mit Kollegen teilen",
                 [f"In Smart Chart öffnen und auf {B('Share…')} klicken.",
                  "<i>Everybody can view it</i> ankreuzen oder Personen und Gruppen (read, write, admin, superuser) "
                  "hinzufügen, je mit <i>Can view</i> oder <i>Can view and edit</i>.",
                  f"{B('Save')} klicken."],
                 "Nur der Ersteller kann ein Dashboard teilen oder löschen. Wer es bearbeiten darf, kann Änderungen "
                 "speichern, es aber nicht weitergeben."),
            ]},
        ],
    },
    "es": {
        "window_title": "¿Cómo funcionan los Dashboards?",
        "close": "Cerrar",
        "tabs": [
            {"key": "tasks", "title": "¿Cómo hago…?", "blocks": [
                ("p", "Aquí <b>ves</b> dashboards: los tuyos y los que tus compañeros compartieron contigo. Los "
                      "dashboards se crean en <i>Smart Chart → Dashboard</i>."),
                ("h", "Ver"),
                ("task", "Abrir un dashboard",
                 ["Haz clic en él en la lista de la izquierda: <i>My dashboards</i> son los tuyos, <i>Shared with "
                  "me</i> vienen de compañeros (con su nombre).",
                  "Escribe en <i>Search a dashboard or owner…</i> para encontrar uno rápido."],
                 "La página abre el último dashboard que miraste."),
                ("task", "Filtrar lo que ves",
                 ["Elige valores en los <b>slicers</b> (listas, desplegables, botones, rangos).",
                  "Haz clic en una barra, un sector o un punto: los demás visuales ponen en gris todo lo demás "
                  "(tarjetas, tablas y la matriz muestran solo ese valor). Otro clic lo deshace.",
                  "Doble clic en una barra baja un nivel (drill-down), si el dashboard lo ofrece.",
                  "Las pestañas de abajo cambian de página."],
                 "Nada de esto se guarda: la próxima vez el dashboard se abre como lo guardó su creador. Abre la "
                 "franja <i>Filters</i> a la derecha para ver qué filtros usa el dashboard."),
                ("task", "Imprimir o enviar un dashboard",
                 [f"Haz clic en {B('PDF')} y elige esta página o todas."]),
                ("task", "Ver los datos más recientes",
                 [f"Haz clic en {B('Reload')} (F5): carga ensayos nuevos y dashboards nuevos o cambiados."]),
                ("h", "Cambiar y compartir"),
                ("task", "Cambiar un dashboard",
                 [f"Haz clic en {B('Edit in Smart Chart')}: solo aparece en tus dashboards y en los compartidos "
                  "contigo <i>para editar</i>.",
                  f"Cámbialo en Smart Chart y haz clic en {B('Save view')}."],
                 "Aquí en Dashboards no se puede cambiar nada salvo los slicers."),
                ("task", "Compartir mi dashboard con compañeros",
                 [f"Ábrelo en Smart Chart y haz clic en {B('Share…')}.",
                  "Marca <i>Everybody can view it</i> o añade personas y grupos (read, write, admin, superuser), "
                  "cada uno con <i>Can view</i> o <i>Can view and edit</i>.",
                  f"Haz clic en {B('Save')}."],
                 "Solo el creador puede compartir o borrar un dashboard. Quien puede editarlo guarda sus cambios, "
                 "pero no puede compartirlo."),
            ]},
        ],
    },
}
