# ui/widgets/help_texts_manage_yarn.py
"""Hilfetexte Manage Yarn (EN/DE/ES) fuer ui/widgets/multilang_help.py.

Spiegelt ui/screen_manage_yarn.py (Namensfilter, Spaltenfilter per Rechtsklick
auf den Kopf - FilterableHeaderView aus screen_manage_jets, Spalten
verschiebbar + Columns…-Dialog, UsedInTrial-Aufklappen, Formular New/Edit
Yarn mit Duplicate-Check, Rechte: Loeschen can_use_admin_box(), MinStock
app_meta.can_edit_min_stock()). Bei Aenderungen dort hier (alle 3 Sprachen)
und in assets/images/help_manage_yarn.svg nachziehen.
"""

SVG = "assets/images/help_manage_yarn.svg"
SVG_W, SVG_H = 940, 240


def B(name: str) -> str:
    return f"<b>[{name}]</b>"


TEXTS = {
    "en": {
        "window_title": "How does Manage Yarn work?",
        "close": "Close",
        "tabs": [
            {"key": "tasks", "title": "How do I…?", "blocks": [
                ("p", "Manage Yarn is the yarn catalogue: every yarn that can be used in trials. Numbers (1)–(3) refer "
                      "to the <i>Screen guide</i> tab."),
                ("h", "Finding"),
                ("task", "Find a yarn by name",
                 ["Type part of the name into <i>Filter by Name…</i> (1). Matches are highlighted."]),
                ("task", "Filter by a column (e.g. titer or material)",
                 ["Right-click the column header (2).",
                  "Enter text (<i>contains…</i>) or, for numbers, a range from/to.",
                  "A green ▼ marks filtered columns. Right-click again → <i>Clear this filter</i> or <i>Clear all filters</i>."],
                 "Several column filters work together (all must match)."),
                ("task", "See in which trial series a yarn was used",
                 ["Click the <i>UsedInTrial</i> cell of the yarn (3). The series appear below it.",
                  "Click a series to see the trial numbers, double-click it to open the series."]),
                ("h", "Changing"),
                ("task", "Add a new yarn",
                 [f"Click {B('New Yarn')}, fill in the form and save it."],
                 "TrippleT warns if a yarn with the same type, material, titer, filaments and colour already exists."),
                ("task", "Change a yarn",
                 [f"Double-click the row (or {B('Edit in Form')}) to edit it in a form, or",
                  f"edit cells directly in the table and click {B('Save Changes')}."]),
                ("task", "Set the minimum stock",
                 ["Edit the <i>MinStock</i> column (or the field in the form)."],
                 "Superusers only. It can also be set in Yarn Stock."),
                ("task", "Delete a yarn",
                 [f"Select the row(s), click {B('Delete')} and confirm."],
                 "Admins only."),
                ("task", "Rearrange the columns",
                 ["Drag a column header to another position, or",
                  f"click {B('Columns…')}, drag the columns into the order you want and click <i>Save layout</i> to keep it."]),
            ]},
            {"key": "screen", "title": "Screen guide", "blocks": [
                ("svg", SVG, {"hint_edit": "double-click a row: form · edit cells directly, then Save Changes",
                              "hint_filter": "right-click a column header to filter it (green ▼ = filter active)"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Name filter and buttons", "Filter by name; Reload, New Yarn, Edit in Form, Columns…, Delete, "
                                                    "Save Changes."),
                    ("(2) Column headers", "Click to sort, right-click to filter, drag to rearrange."),
                    ("(3) UsedInTrial", "Number of trial series using the yarn; click to expand them. <i>StockKg</i> "
                                        "shows the kilos currently in the yarn store."),
                ]),
            ]},
        ],
    },
    "de": {
        "window_title": "Wie funktioniert Manage Yarn?",
        "close": "Schliessen",
        "tabs": [
            {"key": "tasks", "title": "Wie mache ich…?", "blocks": [
                ("p", "Manage Yarn ist der Garnkatalog: jedes Garn, das in Versuchen verwendet werden kann. Die "
                      "Nummern (1)–(3) verweisen auf den Tab <i>Bildschirm</i>."),
                ("h", "Finden"),
                ("task", "Ein Garn über den Namen finden",
                 ["Einen Teil des Namens in <i>Filter by Name…</i> (1) eintippen. Treffer werden hervorgehoben."]),
                ("task", "Nach einer Spalte filtern (z.&nbsp;B. Titer oder Material)",
                 ["Rechtsklick auf den Spaltenkopf (2).",
                  "Text eingeben (<i>contains…</i>) oder bei Zahlen einen Bereich von/bis.",
                  "Ein grünes ▼ markiert gefilterte Spalten. Erneuter Rechtsklick → <i>Clear this filter</i> oder <i>Clear all filters</i>."],
                 "Mehrere Spaltenfilter wirken zusammen (alle müssen passen)."),
                ("task", "Sehen, in welchen Versuchsserien ein Garn verwendet wurde",
                 ["Auf die Zelle <i>UsedInTrial</i> des Garns klicken (3). Die Serien erscheinen darunter.",
                  "Klick auf eine Serie zeigt die Versuchsnummern, Doppelklick öffnet die Serie."]),
                ("h", "Ändern"),
                ("task", "Ein neues Garn anlegen",
                 [f"Auf {B('New Yarn')} klicken, das Formular ausfüllen und speichern."],
                 "TrippleT warnt, wenn es schon ein Garn mit gleichem Typ, Material, Titer, Filamenten und Farbe gibt."),
                ("task", "Ein Garn ändern",
                 [f"Doppelklick auf die Zeile (oder {B('Edit in Form')}) zum Bearbeiten im Formular, oder",
                  f"Zellen direkt in der Tabelle ändern und {B('Save Changes')} klicken."]),
                ("task", "Den Mindestbestand setzen",
                 ["Die Spalte <i>MinStock</i> (oder das Feld im Formular) bearbeiten."],
                 "Nur Superuser. Geht auch in Yarn Stock."),
                ("task", "Ein Garn löschen",
                 [f"Zeile(n) markieren, {B('Delete')} klicken und bestätigen."],
                 "Nur Admins."),
                ("task", "Die Spalten umordnen",
                 ["Einen Spaltenkopf an eine andere Position ziehen, oder",
                  f"auf {B('Columns…')} klicken, die Spalten in die gewünschte Reihenfolge ziehen und mit <i>Save layout</i> merken."]),
            ]},
            {"key": "screen", "title": "Bildschirm", "blocks": [
                ("svg", SVG, {"hint_edit": "Doppelklick auf eine Zeile: Formular · Zellen direkt ändern, dann Save Changes",
                              "hint_filter": "Rechtsklick auf einen Spaltenkopf filtert die Spalte (grünes ▼ = Filter aktiv)"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Namensfilter und Buttons", "Nach Namen filtern; Reload, New Yarn, Edit in Form, Columns…, "
                                                     "Delete, Save Changes."),
                    ("(2) Spaltenköpfe", "Klick sortiert, Rechtsklick filtert, Ziehen ordnet um."),
                    ("(3) UsedInTrial", "Anzahl Versuchsserien mit diesem Garn; Klick klappt sie auf. <i>StockKg</i> "
                                        "zeigt die Kilos, die aktuell im Garnlager sind."),
                ]),
            ]},
        ],
    },
    "es": {
        "window_title": "¿Cómo funciona Manage Yarn?",
        "close": "Cerrar",
        "tabs": [
            {"key": "tasks", "title": "¿Cómo hago…?", "blocks": [
                ("p", "Manage Yarn es el catálogo de hilos: todos los hilos que se pueden usar en ensayos. Los números "
                      "(1)–(3) se refieren a la pestaña <i>Pantalla</i>."),
                ("h", "Buscar"),
                ("task", "Encontrar un hilo por su nombre",
                 ["Escribe parte del nombre en <i>Filter by Name…</i> (1). Las coincidencias se resaltan."]),
                ("task", "Filtrar por una columna (p.&nbsp;ej. título o material)",
                 ["Clic derecho en el encabezado de la columna (2).",
                  "Introduce un texto (<i>contains…</i>) o, para números, un rango desde/hasta.",
                  "Un ▼ verde marca las columnas filtradas. Otro clic derecho → <i>Clear this filter</i> o <i>Clear all filters</i>."],
                 "Varios filtros de columna se combinan (deben cumplirse todos)."),
                ("task", "Ver en qué series de ensayos se usó un hilo",
                 ["Haz clic en la celda <i>UsedInTrial</i> del hilo (3). Las series aparecen debajo.",
                  "Un clic en una serie muestra los números de ensayo, un doble clic abre la serie."]),
                ("h", "Modificar"),
                ("task", "Crear un hilo nuevo",
                 [f"Haz clic en {B('New Yarn')}, rellena el formulario y guárdalo."],
                 "TrippleT avisa si ya existe un hilo con el mismo tipo, material, título, filamentos y color."),
                ("task", "Cambiar un hilo",
                 [f"Doble clic en la fila (o {B('Edit in Form')}) para editarlo en un formulario, o",
                  f"edita las celdas directamente en la tabla y haz clic en {B('Save Changes')}."]),
                ("task", "Definir el stock mínimo",
                 ["Edita la columna <i>MinStock</i> (o el campo del formulario)."],
                 "Solo superusuarios. También se puede hacer en Yarn Stock."),
                ("task", "Borrar un hilo",
                 [f"Selecciona la(s) fila(s), haz clic en {B('Delete')} y confirma."],
                 "Solo administradores."),
                ("task", "Reordenar las columnas",
                 ["Arrastra un encabezado de columna a otra posición, o",
                  f"haz clic en {B('Columns…')}, arrastra las columnas al orden deseado y haz clic en <i>Save layout</i> para conservarlo."]),
            ]},
            {"key": "screen", "title": "Pantalla", "blocks": [
                ("svg", SVG, {"hint_edit": "doble clic en una fila: formulario · editar celdas directamente y luego Save Changes",
                              "hint_filter": "clic derecho en un encabezado para filtrar la columna (▼ verde = filtro activo)"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Filtro de nombre y botones", "Filtrar por nombre; Reload, New Yarn, Edit in Form, Columns…, "
                                                       "Delete, Save Changes."),
                    ("(2) Encabezados", "Clic para ordenar, clic derecho para filtrar, arrastrar para reordenar."),
                    ("(3) UsedInTrial", "Número de series de ensayos que usan el hilo; un clic las despliega. "
                                        "<i>StockKg</i> muestra los kilos que hay ahora en el almacén de hilo."),
                ]),
            ]},
        ],
    },
}
