# ui/widgets/help_texts_all_experiments.py
"""Hilfetexte All Experiments (EN/DE/ES) fuer ui/widgets/multilang_help.py.

Spiegelt ui/screen_all_experiments.py (Maschinen-Filterknoepfe, Textfilter,
Sortierung per Spaltenkopf, Symbolspalten AM/ER/NT/RE, Kontextmenue mit
Rechten wie im Backlog, "Copy TrialSeries" -> Create Experiment im
Add-Series-Modus mit Vorbelegung). Bei Aenderungen dort hier (alle 3
Sprachen) und in assets/images/help_all_experiments.svg nachziehen.
"""

SVG = "assets/images/help_all_experiments.svg"
SVG_W, SVG_H = 940, 256


def B(name: str) -> str:
    return f"<b>[{name}]</b>"


def M(name: str) -> str:
    return f"<b>{name}</b>"


TEXTS = {
    "en": {
        "window_title": "How does All Experiments work?",
        "close": "Close",
        "tabs": [
            {"key": "tasks", "title": "How do I…?", "blocks": [
                ("p", "All Experiments lists every trial series in one table. Numbers (1)–(5) refer to the "
                      "<i>Screen guide</i> tab."),
                ("h", "Finding"),
                ("task", "Show all trial series (orders) of one machine",
                 ["Click the machine button (1), e.g. <i>AFK</i>. <i>All</i> shows everything again."]),
                ("task", "Find a series by number or name",
                 ["Type part of the experiment ID into <i>Filter Experiment ID…</i> or part of the name into "
                  "<i>Filter Trial Series Name…</i> (2)."],
                 "Both filters and the machine button work together."),
                ("task", "Sort the list",
                 ["Click a column header (4). Click it again to reverse the order."]),
                ("h", "Opening"),
                ("task", "Open a series",
                 ["Double-click the row."],
                 "Ctrl + double-click, or right-click → " + M("Open in New Tab") + ", opens it in an additional tab."),
                ("task", "Open the experiment request or the saved report",
                 ["Click the <b>ER</b> symbol in the ER column, or the report symbol in the RE column (5).",
                  "Ctrl + click on the report symbol opens it in a new tab."]),
                ("h", "Changing"),
                ("task", "Change the status of a series",
                 ["Choose the new status in the <i>Status</i> column of the row. It is saved immediately."],
                 "The same rules as in the Backlog apply: only the owner or a superuser may change it, "
                 "<i>To Be Cleaned</i> and <i>Archived</i> are for superusers (exception: To Be Cleaned → Archived "
                 "from access level 2)."),
                ("task", "Create a new series based on an existing one",
                 ["Select the row.",
                  f"Click {B('Copy TrialSeries')} (3)."],
                 "Create Experiment opens with the settings of that series filled in, as a new series of the same "
                 "experiment. Check and adjust the tabs, then Save."),
                ("task", "Rename, change machine or yarn, delete",
                 ["Right-click the row and choose " + M("Rename Trial Series…") + ", " + M("Change Machine…") + ", "
                  + M("Reassign Yarn…") + " or " + M("Delete Trial Series…") + "."],
                 "Renaming requires access level 2; machine, yarn and deleting are for superusers only."),
            ]},
            {"key": "screen", "title": "Screen guide", "blocks": [
                ("svg", SVG, {"hint_open": "double-click a row to open it · Ctrl + double-click opens a new tab",
                              "hint_sort": "click a column header to sort, click again to reverse"}, SVG_W, SVG_H),
                ("areas", [
                    ("(1) Machine buttons", "Show only the series of one machine; <i>All</i> shows all."),
                    ("(2) Text filters", "Filter by experiment ID and by series name."),
                    ("(3) Copy TrialSeries", "New series based on the selected one (opens Create Experiment)."),
                    ("(4) Table", "One row per trial series: experiment ID, name, machine, creation date, owner and "
                                  "Backlog status (can be changed directly in the Status column)."),
                    ("(5) Symbol columns", "<b>AM</b> attachments (images/PDFs), <b>ER</b> linked experiment request "
                                           "(click), <b>NT</b> notes, <b>RE</b> saved report (click)."),
                ]),
            ]},
        ],
    },
    "de": {
        "window_title": "Wie funktioniert All Experiments?",
        "close": "Schliessen",
        "tabs": [
            {"key": "tasks", "title": "Wie mache ich…?", "blocks": [
                ("p", "All Experiments zeigt alle Versuchsserien in einer Tabelle. Die Nummern (1)–(5) verweisen auf "
                      "den Tab <i>Bildschirm</i>."),
                ("h", "Finden"),
                ("task", "Alle Versuchsserien (Aufträge) einer Maschine anzeigen",
                 ["Auf den Maschinen-Knopf (1) klicken, z.&nbsp;B. <i>AFK</i>. <i>All</i> zeigt wieder alles."]),
                ("task", "Eine Serie über Nummer oder Namen finden",
                 ["Einen Teil der Experiment-ID in <i>Filter Experiment ID…</i> oder einen Teil des Namens in "
                  "<i>Filter Trial Series Name…</i> (2) eintippen."],
                 "Beide Filter und der Maschinen-Knopf wirken zusammen."),
                ("task", "Die Liste sortieren",
                 ["Auf einen Spaltenkopf (4) klicken. Ein weiterer Klick dreht die Reihenfolge um."]),
                ("h", "Öffnen"),
                ("task", "Eine Serie öffnen",
                 ["Doppelklick auf die Zeile."],
                 "Strg + Doppelklick oder Rechtsklick → " + M("Open in New Tab") + " öffnet sie in einem zusätzlichen Tab."),
                ("task", "Den Experiment Request oder den gespeicherten Report öffnen",
                 ["Auf das <b>ER</b>-Symbol in der Spalte ER oder das Report-Symbol in der Spalte RE (5) klicken.",
                  "Strg + Klick auf das Report-Symbol öffnet ihn in einem neuen Tab."]),
                ("h", "Ändern"),
                ("task", "Den Status einer Serie ändern",
                 ["In der Spalte <i>Status</i> der Zeile den neuen Status wählen. Er wird sofort gespeichert."],
                 "Es gelten dieselben Regeln wie im Backlog: Nur der Owner oder ein Superuser darf ihn ändern, "
                 "<i>To Be Cleaned</i> und <i>Archived</i> nur Superuser (Ausnahme: To Be Cleaned → Archived ab "
                 "Access Level 2)."),
                ("task", "Eine neue Serie auf Basis einer bestehenden anlegen",
                 ["Die Zeile auswählen.",
                  f"Auf {B('Copy TrialSeries')} (3) klicken."],
                 "Create Experiment öffnet sich mit den Einstellungen dieser Serie, als neue Serie desselben "
                 "Experiments. Tabs prüfen und anpassen, dann Save."),
                ("task", "Umbenennen, Maschine oder Garn ändern, löschen",
                 ["Rechtsklick auf die Zeile und " + M("Rename Trial Series…") + ", " + M("Change Machine…") + ", "
                  + M("Reassign Yarn…") + " oder " + M("Delete Trial Series…") + " wählen."],
                 "Umbenennen erfordert Access Level 2; Maschine, Garn und Löschen nur für Superuser."),
            ]},
            {"key": "screen", "title": "Bildschirm", "blocks": [
                ("svg", SVG, {"hint_open": "Doppelklick auf eine Zeile öffnet sie · Strg + Doppelklick öffnet einen neuen Tab",
                              "hint_sort": "Klick auf einen Spaltenkopf sortiert, erneuter Klick dreht um"}, SVG_W, SVG_H),
                ("areas", [
                    ("(1) Maschinen-Knöpfe", "Nur die Serien einer Maschine zeigen; <i>All</i> zeigt alle."),
                    ("(2) Textfilter", "Filtern nach Experiment-ID und nach Serienname."),
                    ("(3) Copy TrialSeries", "Neue Serie auf Basis der markierten (öffnet Create Experiment)."),
                    ("(4) Tabelle", "Eine Zeile pro Versuchsserie: Experiment-ID, Name, Maschine, Erstelldatum, "
                                    "Owner und Backlog-Status (direkt in der Spalte Status änderbar)."),
                    ("(5) Symbol-Spalten", "<b>AM</b> Anhänge (Bilder/PDFs), <b>ER</b> verknüpfter Experiment Request "
                                           "(Klick), <b>NT</b> Notizen, <b>RE</b> gespeicherter Report (Klick)."),
                ]),
            ]},
        ],
    },
    "es": {
        "window_title": "¿Cómo funciona All Experiments?",
        "close": "Cerrar",
        "tabs": [
            {"key": "tasks", "title": "¿Cómo hago…?", "blocks": [
                ("p", "All Experiments muestra todas las series de ensayos en una tabla. Los números (1)–(5) se "
                      "refieren a la pestaña <i>Pantalla</i>."),
                ("h", "Buscar"),
                ("task", "Mostrar todas las series (pedidos) de una máquina",
                 ["Haz clic en el botón de la máquina (1), p.&nbsp;ej. <i>AFK</i>. <i>All</i> vuelve a mostrar todo."]),
                ("task", "Encontrar una serie por número o nombre",
                 ["Escribe parte del ID del experimento en <i>Filter Experiment ID…</i> o parte del nombre en "
                  "<i>Filter Trial Series Name…</i> (2)."],
                 "Ambos filtros y el botón de máquina funcionan juntos."),
                ("task", "Ordenar la lista",
                 ["Haz clic en un encabezado de columna (4). Otro clic invierte el orden."]),
                ("h", "Abrir"),
                ("task", "Abrir una serie",
                 ["Haz doble clic en la fila."],
                 "Ctrl + doble clic, o clic derecho → " + M("Open in New Tab") + ", la abre en una pestaña adicional."),
                ("task", "Abrir la solicitud de experimento o el informe guardado",
                 ["Haz clic en el símbolo <b>ER</b> de la columna ER, o en el símbolo de informe de la columna RE (5).",
                  "Ctrl + clic en el símbolo de informe lo abre en una pestaña nueva."]),
                ("h", "Modificar"),
                ("task", "Cambiar el estado de una serie",
                 ["Elige el nuevo estado en la columna <i>Status</i> de la fila. Se guarda al instante."],
                 "Se aplican las mismas reglas que en el Backlog: solo el responsable o un superusuario puede "
                 "cambiarlo; <i>To Be Cleaned</i> y <i>Archived</i> solo superusuarios (excepción: To Be Cleaned → "
                 "Archived desde nivel de acceso 2)."),
                ("task", "Crear una serie nueva a partir de una existente",
                 ["Selecciona la fila.",
                  f"Haz clic en {B('Copy TrialSeries')} (3)."],
                 "Create Experiment se abre con los ajustes de esa serie, como serie nueva del mismo experimento. "
                 "Revisa y ajusta las pestañas y haz clic en Save."),
                ("task", "Renombrar, cambiar máquina o hilo, borrar",
                 ["Clic derecho en la fila y elige " + M("Rename Trial Series…") + ", " + M("Change Machine…") + ", "
                  + M("Reassign Yarn…") + " o " + M("Delete Trial Series…") + "."],
                 "Renombrar requiere nivel de acceso 2; máquina, hilo y borrar solo para superusuarios."),
            ]},
            {"key": "screen", "title": "Pantalla", "blocks": [
                ("svg", SVG, {"hint_open": "doble clic en una fila para abrirla · Ctrl + doble clic abre una pestaña nueva",
                              "hint_sort": "clic en un encabezado para ordenar, otro clic invierte el orden"}, SVG_W, SVG_H),
                ("areas", [
                    ("(1) Botones de máquina", "Mostrar solo las series de una máquina; <i>All</i> muestra todas."),
                    ("(2) Filtros de texto", "Filtrar por ID del experimento y por nombre de la serie."),
                    ("(3) Copy TrialSeries", "Serie nueva basada en la seleccionada (abre Create Experiment)."),
                    ("(4) Tabla", "Una fila por serie de ensayos: ID del experimento, nombre, máquina, fecha de "
                                  "creación, responsable y estado en el Backlog (se puede cambiar directamente en la columna Status)."),
                    ("(5) Columnas de símbolos", "<b>AM</b> adjuntos (imágenes/PDF), <b>ER</b> solicitud de experimento "
                                                 "vinculada (clic), <b>NT</b> notas, <b>RE</b> informe guardado (clic)."),
                ]),
            ]},
        ],
    },
}
