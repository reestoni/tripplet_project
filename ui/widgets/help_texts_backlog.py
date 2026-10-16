# ui/widgets/help_texts_backlog.py
"""Hilfetexte Backlog (EN/DE/ES) fuer ui/widgets/multilang_help.py.

Spiegelt ui/screen_backlog.py (Kanban-Board, Drag-&-Drop-Regeln in
BacklogScreen._handle_dnd_move(), Kontextmenue/Rechte in
BacklogDnDTable._open_context_menu(), Karten-Darstellung CardRowDelegate,
Archiv ArchivedPanel). Bei Aenderungen dort hier (alle 3 Sprachen) und in
assets/images/help_backlog.svg nachziehen.
Button-/Menuenamen bleiben englisch wie im Screen.
"""

SVG = "assets/images/help_backlog.svg"
SVG_W, SVG_H = 940, 500


def B(name: str) -> str:
    return f"<b>[{name}]</b>"


def M(name: str) -> str:
    """Kontextmenue-Eintrag."""
    return f"<b>{name}</b>"


TEXTS = {
    # ═══════════════════════════════ EN ═══════════════════════════════
    "en": {
        "window_title": "How does the Backlog work?",
        "close": "Close",
        "tabs": [
            {"key": "tasks", "title": "How do I…?", "blocks": [
                ("p", "The Backlog is the board of all trial series, sorted by status. Find your question "
                      "below. (1)–(5) and A–F refer to the <i>Screen guide</i> tab."),
                ("h", "Finding and opening"),
                ("task", "Open a trial series",
                 ["Double-click its card."],
                 "Ctrl + double-click, or right-click → " + M("Open in New Tab") + ", opens it in a new tab. "
                 + M("Open in New Window") + " opens a separate window."),
                ("task", "See all cards of one area",
                 ["Click the expand icon on the right of the area header.",
                  f"{B('Close')} brings you back to the board."]),
                ("task", "Find an archived series",
                 ["In <i>Archived</i> (5), type part of the experiment ID or series name into <i>Search in Archived…</i>.",
                  "Open the year and experiment-number groups, then double-click the series."]),
                ("task", "Open the linked experiment request or the report",
                 ["Click the <b>ER</b> icon (F) on the card for the request.",
                  "Click the report icon (D) for the saved report. Ctrl + click opens it in a new tab."]),
                ("h", "Working with the board"),
                ("task", "Take a series into work",
                 ["Drag its card from <i>Backlog</i> (1) to <i>In Progress</i> (2)."],
                 "You become the owner of the series (coloured stripe A). If the series still has a placeholder "
                 "machine, TrippleT asks for the real machine first."),
                ("task", "Mark a series as done",
                 ["Drag the card to <i>Done</i> (3)."],
                 "Only the owner or a superuser may change the status, see the <i>Rules</i> tab."),
                ("task", "Move several cards at once",
                 ["Hold <b>Ctrl</b> and click each card (<b>Shift+click</b> selects a whole range).",
                  "Drag one of the selected cards to the new column - all of them move.",
                  "Confirm the question."],
                 "The same rules apply to every card; TrippleT lists the cards that were not allowed to move. "
                 "Handy for moving many series from <i>To Be Cleaned</i> to <i>Archived</i>."),
                ("task", "Change the status without dragging",
                 ["Right-click the card → " + M("Change status…") + " and choose the new status."]),
                ("task", "Change the priority",
                 ["Right-click the card → " + M("Change priority…") + ".",
                  "Enter a number (0–999) and click OK."],
                 "The priority is shown on the card as <i>Prio n</i>."),
                ("task", "Rename a trial series",
                 ["Right-click the card → " + M("Rename trial series…") + "."],
                 "Requires access level 2 or higher."),
                ("task", "Change machine or yarn, or delete a series",
                 ["Right-click the card → " + M("Change machine…") + ", " + M("Reassign yarn…")
                  + " or " + M("Delete trial series…") + "."],
                 "Machine and yarn: superusers only. Deleting: whoever may move the card (see <i>Rules</i>; in "
                 "To Be Cleaned superusers only). "
                 "A deleted series can be restored by a superuser for 90 days: Sidebar → <i>Superuser</i> → "
                 "<b>Recycle Bin</b>."),
                ("task", "Change my welcome message",
                 ["In the sidebar under <i>Account</i> click <b>Settings</b>.",
                  "Enter the new text under <i>Welcome message</i> (max. 45 characters, empty = default), then "
                  "click <b>Save</b>."],
                 "There you can also change the accent colour and the text size."),
            ]},
            {"key": "screen", "title": "Screen guide", "blocks": [
                ("svg", SVG, {"flow_title": "Status flow",
                              "flow_hint": "drag & drop a card into another area to change its status",
                              "card_title": "A card",
                              "archived_hint": "grouped by year and experiment number"}, SVG_W, SVG_H),
                ("areas", [
                    ("(1) Backlog", "Planned series that nobody has started yet. Everyone may take a card from here."),
                    ("(2) In Progress", "Series that are being worked on. The coloured stripe shows the owner."),
                    ("(3) Done", "Finished series."),
                    ("(4) To Be Cleaned", "Series that a superuser reviews and tidies up. Moving a series here "
                                          "closes its open retest flags."),
                    ("(5) Archived", "Completed series, grouped by year and experiment number, with a search field. "
                                     "Drag a row by its handle (the dotted grip on the left) back onto <i>Done</i> to reactivate it (superusers)."),
                ]),
                ("p", "On wide screens (from about 2200 pixels) the areas are shown side by side in four columns - each one then uses the full height."),
                ("h", "What a card shows"),
                ("areas", [
                    ("A", "Colour stripe of the owner (in In Progress and Done)."),
                    ("B", "Series name; below it experiment ID, machine, status, priority and owner."),
                    ("C", "<b>RETEST</b>: a lab value of this series was flagged for retesting. Hover over the "
                          "card to see which trial."),
                    ("D", "Report icon: a saved report exists (click to open). Next to it the notes icon: the "
                          "series has notes."),
                    ("E", "Attachment icon: images or PDFs are attached."),
                    ("F", "<b>ER</b>: linked experiment request (click to open it)."),
                ]),
            ]},
            {"key": "rules", "title": "Rules", "blocks": [
                ("p", "Who may move a card where:"),
                ("table", ["Move", "Who"], [
                    ["Backlog → any other area", "Everyone (you become the owner)"],
                    ["Any other status change", "Owner of the series or a superuser"],
                    ["→ To Be Cleaned, or back out of it", "Superusers only"],
                    ["To Be Cleaned → Archived", "Access level 2 or higher"],
                    ["Any other move into or out of Archived", "Superusers only"],
                ]),
                ("h", "Right-click menu"),
                ("table", ["Entry", "Who"], [
                    [M("Open in New Tab") + " / " + M("Open in New Window") + " / "
                     + M("Change priority…") + " / " + M("Change status…"), "Everyone (status rules above apply)"],
                    [M("Rename trial series…"), "Access level 2 or higher"],
                    [M("Reassign yarn…") + " / " + M("Change machine…"), "Superusers only"],
                    [M("Delete trial series…"), "Whoever may move the card (see above); in To Be Cleaned superusers only"],
                ]),
                ("h", "Retests"),
                ("p", "If a superuser flags a lab value for retesting (in Show Experiment), the series comes back "
                      "into <i>Backlog</i> with top priority and shows the <b>RETEST</b> badge. The flag is closed "
                      "when the series is moved to <i>To Be Cleaned</i>."),
            ]},
        ],
    },

    # ═══════════════════════════════ DE ═══════════════════════════════
    "de": {
        "window_title": "Wie funktioniert der Backlog?",
        "close": "Schliessen",
        "tabs": [
            {"key": "tasks", "title": "Wie mache ich…?", "blocks": [
                ("p", "Der Backlog ist die Übersicht aller Versuchsserien, sortiert nach Status. Such dir unten "
                      "deine Frage aus. (1)–(5) und A–F verweisen auf den Tab <i>Bildschirm</i>."),
                ("h", "Finden und öffnen"),
                ("task", "Eine Versuchsserie öffnen",
                 ["Doppelklick auf ihre Karte."],
                 "Strg + Doppelklick oder Rechtsklick → " + M("Open in New Tab") + " öffnet sie in einem neuen Tab. "
                 + M("Open in New Window") + " öffnet ein eigenes Fenster."),
                ("task", "Alle Karten eines Bereichs sehen",
                 ["Rechts im Kopf des Bereichs auf das Vergrössern-Symbol klicken.",
                  f"{B('Close')} führt zurück zur Übersicht."]),
                ("task", "Eine archivierte Serie finden",
                 ["Im Bereich <i>Archived</i> (5) einen Teil der Experiment-ID oder des Seriennamens in "
                  "<i>Search in Archived…</i> eintippen.",
                  "Die Gruppen nach Jahr und Experimentnummer aufklappen und die Serie doppelklicken."]),
                ("task", "Den verknüpften Experiment Request oder den Report öffnen",
                 ["Für den Request auf das <b>ER</b>-Symbol (F) der Karte klicken.",
                  "Für den gespeicherten Report auf das Report-Symbol (D) klicken. Strg + Klick öffnet ihn in einem neuen Tab."]),
                ("h", "Mit der Übersicht arbeiten"),
                ("task", "Eine Serie in Arbeit nehmen",
                 ["Ihre Karte von <i>Backlog</i> (1) nach <i>In Progress</i> (2) ziehen."],
                 "Du wirst damit Owner der Serie (farbiger Streifen A). Hat die Serie noch eine Platzhalter-Maschine, "
                 "fragt TrippleT zuerst nach der echten Maschine."),
                ("task", "Eine Serie als fertig markieren",
                 ["Die Karte nach <i>Done</i> (3) ziehen."],
                 "Den Status ändern dürfen nur der Owner oder ein Superuser, siehe Tab <i>Regeln</i>."),
                ("task", "Mehrere Karten auf einmal verschieben",
                 ["<b>Strg</b> gedrückt halten und jede Karte anklicken (<b>Umschalt+Klick</b> markiert einen ganzen Bereich).",
                  "Eine der markierten Karten in die neue Spalte ziehen - alle wandern mit.",
                  "Die Rückfrage bestätigen."],
                 "Für jede Karte gelten dieselben Regeln; TrippleT listet die Karten auf, die nicht verschoben werden "
                 "durften. Praktisch, um viele Serien von <i>To Be Cleaned</i> nach <i>Archived</i> zu schieben."),
                ("task", "Den Status ohne Ziehen ändern",
                 ["Rechtsklick auf die Karte → " + M("Change status…") + " und den neuen Status wählen."]),
                ("task", "Die Priorität ändern",
                 ["Rechtsklick auf die Karte → " + M("Change priority…") + ".",
                  "Eine Zahl (0–999) eingeben und OK klicken."],
                 "Die Priorität steht auf der Karte als <i>Prio n</i>."),
                ("task", "Eine Versuchsserie umbenennen",
                 ["Rechtsklick auf die Karte → " + M("Rename trial series…") + "."],
                 "Erfordert Access Level 2 oder höher."),
                ("task", "Maschine oder Garn ändern, oder eine Serie löschen",
                 ["Rechtsklick auf die Karte → " + M("Change machine…") + ", " + M("Reassign yarn…")
                  + " oder " + M("Delete trial series…") + "."],
                 "Maschine und Garn: nur Superuser. Löschen: wer die Karte verschieben darf (siehe <i>Regeln</i>; "
                 "in To Be Cleaned nur Superuser). "
                 "Eine gelöschte Serie kann ein Superuser 90 Tage lang wiederherstellen: Sidebar → "
                 "<i>Superuser</i> → <b>Recycle Bin</b>."),
                ("task", "Meine Begrüssung ändern",
                 ["In der Sidebar unter <i>Account</i> auf <b>Settings</b> klicken.",
                  "Unter <i>Welcome message</i> den neuen Text eingeben (max. 45 Zeichen, leer = Standard), dann "
                  "auf <b>Save</b> klicken."],
                 "Dort lassen sich auch Akzentfarbe und Textgrösse ändern."),
            ]},
            {"key": "screen", "title": "Bildschirm", "blocks": [
                ("svg", SVG, {"flow_title": "Status-Ablauf",
                              "flow_hint": "Karte per Drag & Drop in einen anderen Bereich ziehen, um den Status zu ändern",
                              "card_title": "Eine Karte",
                              "archived_hint": "gruppiert nach Jahr und Experimentnummer"}, SVG_W, SVG_H),
                ("areas", [
                    ("(1) Backlog", "Geplante Serien, die noch niemand begonnen hat. Jeder darf hier eine Karte übernehmen."),
                    ("(2) In Progress", "Serien in Arbeit. Der farbige Streifen zeigt den Owner."),
                    ("(3) Done", "Fertige Serien."),
                    ("(4) To Be Cleaned", "Serien, die ein Superuser prüft und aufräumt. Wird eine Serie hierher "
                                          "verschoben, werden ihre offenen Retest-Markierungen geschlossen."),
                    ("(5) Archived", "Abgeschlossene Serien, gruppiert nach Jahr und Experimentnummer, mit Suchfeld. "
                                     "Am Griff (gepunktetes Feld links) lässt sich eine Zeile zurück auf <i>Done</i> ziehen (Superuser)."),
                ]),
                ("p", "Auf breiten Bildschirmen (ab etwa 2200 Pixel) stehen die Bereiche in vier Spalten nebeneinander - jeder nutzt dann die volle Höhe."),
                ("h", "Was eine Karte zeigt"),
                ("areas", [
                    ("A", "Farbstreifen des Owners (in In Progress und Done)."),
                    ("B", "Serienname; darunter Experiment-ID, Maschine, Status, Priorität und Owner."),
                    ("C", "<b>RETEST</b>: Ein Laborwert dieser Serie wurde zum Nachmessen markiert. Mit der Maus über "
                          "die Karte fahren, um zu sehen, welcher Versuch."),
                    ("D", "Report-Symbol: Es gibt einen gespeicherten Report (Klick öffnet ihn). Daneben das "
                          "Notiz-Symbol: Die Serie hat Notizen."),
                    ("E", "Anhang-Symbol: Bilder oder PDFs sind angehängt."),
                    ("F", "<b>ER</b>: verknüpfter Experiment Request (Klick öffnet ihn)."),
                ]),
            ]},
            {"key": "rules", "title": "Regeln", "blocks": [
                ("p", "Wer eine Karte wohin verschieben darf:"),
                ("table", ["Verschieben", "Wer"], [
                    ["Backlog → jeder andere Bereich", "Alle (du wirst Owner)"],
                    ["Jeder andere Statuswechsel", "Owner der Serie oder ein Superuser"],
                    ["→ To Be Cleaned, oder wieder heraus", "Nur Superuser"],
                    ["To Be Cleaned → Archived", "Access Level 2 oder höher"],
                    ["Jede andere Verschiebung nach oder aus Archived", "Nur Superuser"],
                ]),
                ("h", "Rechtsklick-Menü"),
                ("table", ["Eintrag", "Wer"], [
                    [M("Open in New Tab") + " / " + M("Open in New Window") + " / "
                     + M("Change priority…") + " / " + M("Change status…"), "Alle (es gelten die Status-Regeln oben)"],
                    [M("Rename trial series…"), "Access Level 2 oder höher"],
                    [M("Reassign yarn…") + " / " + M("Change machine…"), "Nur Superuser"],
                    [M("Delete trial series…"), "Wer die Karte verschieben darf (siehe oben); in To Be Cleaned nur Superuser"],
                ]),
                ("h", "Nachmessungen (Retest)"),
                ("p", "Markiert ein Superuser einen Laborwert zum Nachmessen (in Show Experiment), kommt die Serie "
                      "mit höchster Priorität zurück in den <i>Backlog</i> und zeigt das <b>RETEST</b>-Abzeichen. "
                      "Die Markierung wird geschlossen, wenn die Serie nach <i>To Be Cleaned</i> verschoben wird."),
            ]},
        ],
    },

    # ═══════════════════════════════ ES ═══════════════════════════════
    "es": {
        "window_title": "¿Cómo funciona el Backlog?",
        "close": "Cerrar",
        "tabs": [
            {"key": "tasks", "title": "¿Cómo hago…?", "blocks": [
                ("p", "El Backlog es el tablero de todas las series de ensayos, ordenadas por estado. Busca tu "
                      "pregunta abajo. (1)–(5) y A–F se refieren a la pestaña <i>Pantalla</i>."),
                ("h", "Buscar y abrir"),
                ("task", "Abrir una serie de ensayos",
                 ["Haz doble clic en su tarjeta."],
                 "Ctrl + doble clic, o clic derecho → " + M("Open in New Tab") + ", la abre en una pestaña nueva. "
                 + M("Open in New Window") + " abre una ventana aparte."),
                ("task", "Ver todas las tarjetas de una zona",
                 ["Haz clic en el icono de ampliar a la derecha del encabezado de la zona.",
                  f"{B('Close')} vuelve al tablero."]),
                ("task", "Encontrar una serie archivada",
                 ["En <i>Archived</i> (5), escribe parte del ID del experimento o del nombre de la serie en "
                  "<i>Search in Archived…</i>.",
                  "Abre los grupos por año y número de experimento y haz doble clic en la serie."]),
                ("task", "Abrir la solicitud de experimento o el informe vinculados",
                 ["Para la solicitud, haz clic en el icono <b>ER</b> (F) de la tarjeta.",
                  "Para el informe guardado, haz clic en el icono de informe (D). Ctrl + clic lo abre en una pestaña nueva."]),
                ("h", "Trabajar con el tablero"),
                ("task", "Empezar a trabajar en una serie",
                 ["Arrastra su tarjeta de <i>Backlog</i> (1) a <i>In Progress</i> (2)."],
                 "Pasas a ser el responsable (owner) de la serie (franja de color A). Si la serie aún tiene una "
                 "máquina provisional, TrippleT pregunta primero por la máquina real."),
                ("task", "Marcar una serie como terminada",
                 ["Arrastra la tarjeta a <i>Done</i> (3)."],
                 "Solo el responsable o un superusuario puede cambiar el estado, ver la pestaña <i>Reglas</i>."),
                ("task", "Mover varias tarjetas a la vez",
                 ["Mantén <b>Ctrl</b> y haz clic en cada tarjeta (<b>Mayús+clic</b> marca un rango entero).",
                  "Arrastra una de las tarjetas marcadas a la nueva columna: se mueven todas.",
                  "Confirma la pregunta."],
                 "Las mismas reglas valen para cada tarjeta; TrippleT indica las que no se podían mover. "
                 "Útil para pasar muchas series de <i>To Be Cleaned</i> a <i>Archived</i>."),
                ("task", "Cambiar el estado sin arrastrar",
                 ["Clic derecho en la tarjeta → " + M("Change status…") + " y elige el nuevo estado."]),
                ("task", "Cambiar la prioridad",
                 ["Clic derecho en la tarjeta → " + M("Change priority…") + ".",
                  "Introduce un número (0–999) y haz clic en OK."],
                 "La prioridad aparece en la tarjeta como <i>Prio n</i>."),
                ("task", "Cambiar el nombre de una serie",
                 ["Clic derecho en la tarjeta → " + M("Rename trial series…") + "."],
                 "Requiere nivel de acceso 2 o superior."),
                ("task", "Cambiar máquina o hilo, o borrar una serie",
                 ["Clic derecho en la tarjeta → " + M("Change machine…") + ", " + M("Reassign yarn…")
                  + " o " + M("Delete trial series…") + "."],
                 "Máquina e hilo: solo superusuarios. Borrar: quien puede mover la tarjeta (ver <i>Reglas</i>; "
                 "en To Be Cleaned solo superusuarios). "
                 "Un superusuario puede recuperar una serie borrada durante 90 días: barra lateral → "
                 "<i>Superuser</i> → <b>Recycle Bin</b>."),
                ("task", "Cambiar mi mensaje de bienvenida",
                 ["En la barra lateral, en <i>Account</i>, haz clic en <b>Settings</b>.",
                  "Escribe el nuevo texto en <i>Welcome message</i> (máx. 45 caracteres, vacío = estándar) y haz "
                  "clic en <b>Save</b>."],
                 "Ahí también puedes cambiar el color de acento y el tamaño del texto."),
            ]},
            {"key": "screen", "title": "Pantalla", "blocks": [
                ("svg", SVG, {"flow_title": "Flujo de estados",
                              "flow_hint": "arrastra una tarjeta a otra zona para cambiar su estado",
                              "card_title": "Una tarjeta",
                              "archived_hint": "agrupado por año y número de experimento"}, SVG_W, SVG_H),
                ("areas", [
                    ("(1) Backlog", "Series planificadas que nadie ha empezado aún. Cualquiera puede tomar una tarjeta de aquí."),
                    ("(2) In Progress", "Series en curso. La franja de color muestra el responsable."),
                    ("(3) Done", "Series terminadas."),
                    ("(4) To Be Cleaned", "Series que un superusuario revisa y ordena. Al mover una serie aquí se "
                                          "cierran sus marcas de repetición abiertas."),
                    ("(5) Archived", "Series cerradas, agrupadas por año y número de experimento, con campo de búsqueda. "
                                     "Arrastrando una fila por su asa (el punteado de la izquierda) se puede devolver la serie a <i>Done</i> (superusuarios)."),
                ]),
                ("p", "En pantallas anchas (a partir de unos 2200 píxeles) las áreas se muestran una al lado de otra en cuatro columnas, cada una con toda la altura."),
                ("h", "Qué muestra una tarjeta"),
                ("areas", [
                    ("A", "Franja de color del responsable (en In Progress y Done)."),
                    ("B", "Nombre de la serie; debajo ID del experimento, máquina, estado, prioridad y responsable."),
                    ("C", "<b>RETEST</b>: un valor de laboratorio de esta serie está marcado para repetir la medición. "
                          "Pasa el ratón por la tarjeta para ver qué ensayo."),
                    ("D", "Icono de informe: hay un informe guardado (clic para abrirlo). Al lado, el icono de notas: "
                          "la serie tiene notas."),
                    ("E", "Icono de adjunto: hay imágenes o PDF adjuntos."),
                    ("F", "<b>ER</b>: solicitud de experimento vinculada (clic para abrirla)."),
                ]),
            ]},
            {"key": "rules", "title": "Reglas", "blocks": [
                ("p", "Quién puede mover una tarjeta y adónde:"),
                ("table", ["Movimiento", "Quién"], [
                    ["Backlog → cualquier otra zona", "Todos (pasas a ser el responsable)"],
                    ["Cualquier otro cambio de estado", "El responsable de la serie o un superusuario"],
                    ["→ To Be Cleaned, o sacarla de allí", "Solo superusuarios"],
                    ["To Be Cleaned → Archived", "Nivel de acceso 2 o superior"],
                    ["Cualquier otro movimiento hacia o desde Archived", "Solo superusuarios"],
                ]),
                ("h", "Menú del clic derecho"),
                ("table", ["Entrada", "Quién"], [
                    [M("Open in New Tab") + " / " + M("Open in New Window") + " / "
                     + M("Change priority…") + " / " + M("Change status…"), "Todos (se aplican las reglas de estado de arriba)"],
                    [M("Rename trial series…"), "Nivel de acceso 2 o superior"],
                    [M("Reassign yarn…") + " / " + M("Change machine…"), "Solo superusuarios"],
                    [M("Delete trial series…"), "Quien puede mover la tarjeta (ver arriba); en To Be Cleaned solo superusuarios"],
                ]),
                ("h", "Repeticiones (retest)"),
                ("p", "Si un superusuario marca un valor de laboratorio para repetir (en Show Experiment), la serie "
                      "vuelve al <i>Backlog</i> con máxima prioridad y muestra la etiqueta <b>RETEST</b>. La marca se "
                      "cierra cuando la serie se mueve a <i>To Be Cleaned</i>."),
            ]},
        ],
    },
}
