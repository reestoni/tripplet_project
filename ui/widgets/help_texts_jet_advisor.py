# ui/widgets/help_texts_jet_advisor.py
"""Hilfetexte Jet Advisor (EN/DE/ES) fuer ui/widgets/multilang_help.py (Desktop) und
/api/help/screen/jet_advisor (Web, tripplet_web/backend/app/help.py).

Spiegelt ui/screen_jet_advisor.py bzw. die Web-Seite /tools/jet-advisor (1 Yarn, 2 Targets,
3 Jets, 4 Machine settings, Ergebnis + Detail) und die Methode in ui/jet_advisor.py.
Skizze: assets/images/help_jet_advisor.svg (Platzhalter {{hint_*}} pro Sprache).
Knopfnamen bleiben die englischen des Desktops. Bei Aenderungen alle 3 Sprachen nachziehen.
"""

SVG = "assets/images/help_jet_advisor.svg"
SVG_W, SVG_H = 940, 400


def B(name: str) -> str:
    return f"<b>[{name}]</b>"


TEXTS = {
    "en": {
        "window_title": "How does the Jet Advisor work?",
        "close": "Close",
        "tabs": [
            {"key": "tasks", "title": "How do I…?", "blocks": [
                ("p", "The Jet Advisor answers the question <i>which jet, with which settings, reaches my targets "
                      "for this yarn?</i> - from our own <b>DTY</b> trials of this yarn or similar ones. It lists the "
                      "jets with the recommended <b>air pressure</b>, <b>overfeed</b> and <b>speed</b>, the expected "
                      "lab values and how likely a new run reaches the targets."),
                ("h", "Finding jets"),
                ("task", "Find the best jets for a yarn",
                 ["Under <i>1 Yarn</i> pick an existing yarn (type to search) - or choose <i>Own values</i> and give "
                  "material, final titer and filament count for a yarn we never ran.",
                  "Under <i>2 Targets</i> fill what matters, e.g. points/m min 90, stability 1.0 min 75, CV max 15. "
                  "Empty = no target.",
                  f"Click {B('Find jets')}."],
                 "The list is sorted by the chance to reach all targets. In the web version the form is kept "
                 "until you change it."),
                ("task", "Only standard jets (or another jet type)",
                 ["Under <i>3 Jets</i> tick <i>Standard</i> (several types possible).",
                  "Optionally tick makers or groups, or <i>Only jets whose titer range fits the final titer</i>.",
                  f"Click {B('Find jets')} again."],
                 "Nothing ticked = all jets. Jets without a type are listed as <i>(none)</i>."),
                ("task", "Fix the machine settings, e.g. a speed of 800 m/min",
                 ["Under <i>4 Machine settings</i> type 800 in <i>from</i> and <i>to</i> of <i>Speed</i>.",
                  "Limit the air pressure the same way, e.g. <i>to</i> 4 bar.",
                  f"Click {B('Find jets')}."],
                 "Only settings inside these limits are considered. If no trial lies in that range, no jet is shown - "
                 "the advisor never guesses beyond what we measured."),
                ("task", "Save air",
                 ["Set <i>When equally good, prefer</i> to <i>Less air</i>.",
                  f"Click {B('Find jets')}."],
                 "Among settings that are equally good, the one with less air consumption (lower pressure, smaller "
                 "bore) wins. The column <i>Air</i> shows Nm³/h per position, calculated like the Jet ROI Calculator."),
                ("task", "Check where a recommendation comes from",
                 ["Click a jet in the result.",
                  "Below you see why this setting was chosen, how many trials are behind it and the trial series "
                  "(double-click / click opens them; Ctrl = new tab on the desktop).",
                  f"{B('Open in Process Playground')} opens this yarn and jet there - to see what happens around "
                  "the recommended setting."]),
                ("h", "If nothing is found"),
                ("task", "No similar yarn / no jet found",
                 ["Set <i>Similar yarns</i> to <i>wide (±50 %)</i>.",
                  "Untick <i>Only the same material</i>.",
                  "Loosen the jet filters or the machine settings."],
                 "The line above the result shows which yarns were used and how far they are from yours."),
            ]},
            {"key": "method", "title": "How it decides", "blocks": [
                ("h", "1  Similar yarns"),
                ("p", "Our trials are searched for yarns like yours: same material (if ticked), final titer and "
                      "filament count close to yours. The <i>distance</i> is 0 for the same yarn and 1 for about "
                      "30 % more or less titer or 50 % more or less filaments. Multi-ply yarns count with their summed "
                      "titer and filaments."),
                ("h", "2  Per jet: measured and modelled settings"),
                ("p", "For every jet that ran with these yarns, every setting we really ran is a candidate "
                      "(<i>measured</i>). Where air pressure, overfeed or speed were varied, the model of the Process "
                      "Playground fills the gaps between them (<i>model</i>) - only close to settings we ran, never "
                      "beyond the measured range."),
                ("h", "3  Chance to reach the targets"),
                ("p", "For each candidate the expected value of every target and its spread for a new run are "
                      "estimated: the scatter of repeated trials, the uncertainty of the model and the differences "
                      "between series. From this follows the chance that a new run meets all targets."),
                ("h", "4  Ranking"),
                ("ul", ["Each jet shows its best setting; the <i>window</i> below the value is the range that is "
                        "almost as good (at least 90 % of the best chance).",
                        "Order: chance (a bit lower for less similar yarns), then how far the targets are missed, then "
                        "<i>safety margin</i> (distance to the nearest target limit in spreads) or <i>less air</i>.",
                        "If no jet reaches the targets, the closest ones are still listed - with ✗ at the missed "
                        "target."]),
                ("warn", "The chance is an estimate from our trials, not a guarantee. Always confirm the "
                         "recommendation with a trial - and keep an eye on <i>Source</i> and the number of trials."),
                ("p", "Only DTY. Lab values: points/m and CV (Itemat), stability 0.3 / 0.6 / 1.0 / 1.3. Reference "
                      "samples are not used; points/m = 0 counts as not measured."),
            ]},
            {"key": "screen", "title": "Screen guide", "blocks": [
                ("svg", SVG, {"hint_chance": "Chance: bar = how likely a new run meets all targets",
                              "hint_window": "Small grey numbers below a setting: the window that is almost as good",
                              "hint_source": "measured = run exactly like this · model = between measured settings",
                              "hint_click": "Click a jet: why, which trials, open in the Process Playground"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Yarn", "Existing yarn or own values (material, final titer, filaments); how similar the "
                                 "yarns used may be; same material only."),
                    ("(2) Targets", "min and/or max per lab value. Empty = no target."),
                    ("(3) Jets", "Jet type (e.g. Standard), maker, group, titer range of the jet. Nothing ticked = all."),
                    ("(4) Machine settings", "Limits for air pressure, overfeed and speed; what to prefer when two "
                                             "settings are equally good. Find jets / Reset."),
                    ("(5) Result", "One line per jet: chance, recommended setting with window, expected values "
                                   "± spread (✓ / ✗), air in Nm³/h, source, yarn and trials behind it."),
                    ("(6) Detail", "Why this setting, safety margin or miss, trial series, Process Playground."),
                ]),
            ]},
        ],
    },
    "de": {
        "window_title": "Wie funktioniert der Jet Advisor?",
        "close": "Schliessen",
        "tabs": [
            {"key": "tasks", "title": "Wie mache ich…?", "blocks": [
                ("p", "Der Jet Advisor beantwortet die Frage <i>welche Düse erreicht mit welchen Einstellungen meine "
                      "Ziele für dieses Garn?</i> - aus unseren eigenen <b>DTY</b>-Versuchen mit diesem oder ähnlichen "
                      "Garnen. Er listet die Düsen mit empfohlenem <b>Luftdruck</b>, <b>Overfeed</b> und "
                      "<b>Geschwindigkeit</b>, den erwarteten Laborwerten und wie wahrscheinlich ein neuer Lauf die "
                      "Ziele erreicht."),
                ("h", "Düsen finden"),
                ("task", "Die besten Düsen für ein Garn finden",
                 ["Unter <i>1 Yarn</i> ein vorhandenes Garn wählen (Tippen sucht) - oder <i>Own values</i> wählen und "
                  "Material, Endtiter und Filamentzahl für ein Garn angeben, das wir nie gefahren haben.",
                  "Unter <i>2 Targets</i> ausfüllen, was zählt, z. B. Punkte/m min 90, Stabilität 1.0 min 75, CV max 15. "
                  "Leer = kein Ziel.",
                  f"{B('Find jets')} klicken."],
                 "Die Liste ist nach der Chance sortiert, alle Ziele zu erreichen. In der Web-Version bleibt das "
                 "Formular stehen, bis du es änderst."),
                ("task", "Nur Standard-Düsen (oder ein anderer Düsentyp)",
                 ["Unter <i>3 Jets</i> <i>Standard</i> anhaken (mehrere Typen möglich).",
                  "Wahlweise Hersteller oder Gruppen anhaken oder <i>Only jets whose titer range fits the final "
                  "titer</i>.",
                  f"Erneut {B('Find jets')} klicken."],
                 "Nichts angehakt = alle Düsen. Düsen ohne Typ stehen als <i>(none)</i> in der Liste."),
                ("task", "Maschineneinstellungen festlegen, z. B. 800 m/min",
                 ["Unter <i>4 Machine settings</i> bei <i>Speed</i> in <i>from</i> und <i>to</i> 800 eintragen.",
                  "Den Luftdruck genauso begrenzen, z. B. <i>to</i> 4 bar.",
                  f"{B('Find jets')} klicken."],
                 "Nur Einstellungen innerhalb dieser Grenzen zählen. Liegt in diesem Bereich kein Versuch, wird keine "
                 "Düse gezeigt - der Advisor rät nie über das Gemessene hinaus."),
                ("task", "Luft sparen",
                 ["<i>When equally good, prefer</i> auf <i>Less air</i> stellen.",
                  f"{B('Find jets')} klicken."],
                 "Unter gleich guten Einstellungen gewinnt die mit weniger Luftverbrauch (tieferer Druck, kleinere "
                 "Bohrung). Die Spalte <i>Air</i> zeigt Nm³/h pro Position, gerechnet wie im Jet ROI Calculator."),
                ("task", "Prüfen, woher eine Empfehlung kommt",
                 ["Im Ergebnis eine Düse anklicken.",
                  "Darunter steht, warum diese Einstellung gewählt wurde, wie viele Versuche dahinterstehen und die "
                  "Versuchsserien (Doppelklick / Klick öffnet sie; im Desktop Ctrl = neuer Tab).",
                  f"{B('Open in Process Playground')} öffnet dieses Garn und diese Düse dort - um zu sehen, was rund "
                  "um die empfohlene Einstellung passiert."]),
                ("h", "Wenn nichts gefunden wird"),
                ("task", "Kein ähnliches Garn / keine Düse gefunden",
                 ["<i>Similar yarns</i> auf <i>wide (±50 %)</i> stellen.",
                  "<i>Only the same material</i> abhaken.",
                  "Düsenfilter oder Maschineneinstellungen lockern."],
                 "Die Zeile über dem Ergebnis zeigt, welche Garne verwendet wurden und wie weit sie von deinem "
                 "entfernt sind."),
            ]},
            {"key": "method", "title": "Wie entschieden wird", "blocks": [
                ("h", "1  Ähnliche Garne"),
                ("p", "In unseren Versuchen werden Garne wie deines gesucht: gleiches Material (wenn angehakt), Endtiter "
                      "und Filamentzahl nahe an deinen. Der <i>Abstand</i> ist 0 beim gleichen Garn und 1 bei etwa "
                      "30 % mehr oder weniger Titer oder 50 % mehr oder weniger Filamenten. Mehrfach gefachte Garne "
                      "zählen mit summiertem Titer und Filamenten."),
                ("h", "2  Pro Düse: gemessene und modellierte Einstellungen"),
                ("p", "Für jede Düse, die mit diesen Garnen gelaufen ist, ist jede wirklich gefahrene Einstellung ein "
                      "Kandidat (<i>measured</i>). Wo Luftdruck, Overfeed oder Geschwindigkeit variiert wurden, füllt "
                      "das Modell der Process Playground die Lücken dazwischen (<i>model</i>) - nur nahe an gefahrenen "
                      "Einstellungen, nie über den gemessenen Bereich hinaus."),
                ("h", "3  Chance, die Ziele zu erreichen"),
                ("p", "Pro Kandidat werden der erwartete Wert jedes Ziels und seine Streuung für einen neuen Lauf "
                      "geschätzt: die Streuung von Wiederholungen, die Unsicherheit des Modells und die Unterschiede "
                      "zwischen Serien. Daraus folgt die Chance, dass ein neuer Lauf alle Ziele erreicht."),
                ("h", "4  Rangfolge"),
                ("ul", ["Jede Düse zeigt ihre beste Einstellung; das <i>Fenster</i> unter dem Wert ist der Bereich, "
                        "der fast so gut ist (mindestens 90 % der besten Chance).",
                        "Reihenfolge: Chance (etwas tiefer bei weniger ähnlichen Garnen), dann wie weit die Ziele "
                        "verfehlt werden, dann <i>Sicherheitsabstand</i> (Abstand zur nächsten Zielgrenze in "
                        "Streuungen) oder <i>weniger Luft</i>.",
                        "Erreicht keine Düse die Ziele, werden trotzdem die nächsten gezeigt - mit ✗ beim verfehlten "
                        "Ziel."]),
                ("warn", "Die Chance ist eine Schätzung aus unseren Versuchen, keine Garantie. Die Empfehlung immer "
                         "mit einem Versuch bestätigen - und auf <i>Source</i> und die Anzahl Versuche achten."),
                ("p", "Nur DTY. Laborwerte: Punkte/m und CV (Itemat), Stabilität 0.3 / 0.6 / 1.0 / 1.3. Referenzmuster "
                      "werden nicht verwendet; Punkte/m = 0 gilt als nicht gemessen."),
            ]},
            {"key": "screen", "title": "Bildschirm", "blocks": [
                ("svg", SVG, {"hint_chance": "Chance: Balken = wie wahrscheinlich ein neuer Lauf alle Ziele erreicht",
                              "hint_window": "Kleine graue Zahlen unter einer Einstellung: das fast gleich gute Fenster",
                              "hint_source": "measured = genau so gefahren · model = zwischen gefahrenen Einstellungen",
                              "hint_click": "Düse anklicken: warum, welche Versuche, in der Process Playground öffnen"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Yarn", "Vorhandenes Garn oder eigene Angaben (Material, Endtiter, Filamente); wie ähnlich "
                                 "die verwendeten Garne sein dürfen; nur gleiches Material."),
                    ("(2) Targets", "min und/oder max pro Laborwert. Leer = kein Ziel."),
                    ("(3) Jets", "Düsentyp (z. B. Standard), Hersteller, Gruppe, Titerbereich der Düse. Nichts "
                                 "angehakt = alle."),
                    ("(4) Machine settings", "Grenzen für Luftdruck, Overfeed und Geschwindigkeit; was bei gleich "
                                             "guten Einstellungen bevorzugt wird. Find jets / Reset."),
                    ("(5) Ergebnis", "Eine Zeile pro Düse: Chance, empfohlene Einstellung mit Fenster, erwartete Werte "
                                     "± Streuung (✓ / ✗), Luft in Nm³/h, Quelle, Garn und Versuche dahinter."),
                    ("(6) Detail", "Warum diese Einstellung, Sicherheitsabstand oder Verfehlung, Versuchsserien, "
                                   "Process Playground."),
                ]),
            ]},
        ],
    },
    "es": {
        "window_title": "¿Cómo funciona el Jet Advisor?",
        "close": "Cerrar",
        "tabs": [
            {"key": "tasks", "title": "¿Cómo hago…?", "blocks": [
                ("p", "El Jet Advisor responde a la pregunta <i>¿qué tobera, con qué ajustes, alcanza mis objetivos "
                      "para este hilo?</i> - a partir de nuestros propios ensayos <b>DTY</b> con este hilo o hilos "
                      "similares. Muestra las toberas con la <b>presión de aire</b>, la <b>sobrealimentación</b> y la "
                      "<b>velocidad</b> recomendadas, los valores de laboratorio esperados y la probabilidad de que una "
                      "nueva prueba alcance los objetivos."),
                ("h", "Buscar toberas"),
                ("task", "Encontrar las mejores toberas para un hilo",
                 ["En <i>1 Yarn</i> elige un hilo existente (escribe para buscar) - o elige <i>Own values</i> e indica "
                  "material, título final y número de filamentos de un hilo que nunca hemos probado.",
                  "En <i>2 Targets</i> rellena lo que importa, p. ej. puntos/m mín. 90, estabilidad 1.0 mín. 75, "
                  "CV máx. 15. Vacío = sin objetivo.",
                  f"Haz clic en {B('Find jets')}."],
                 "La lista se ordena por la probabilidad de alcanzar todos los objetivos. En la versión web el "
                 "formulario se conserva hasta que lo cambies."),
                ("task", "Solo toberas estándar (u otro tipo)",
                 ["En <i>3 Jets</i> marca <i>Standard</i> (se pueden marcar varios tipos).",
                  "Opcionalmente marca fabricantes o grupos, o <i>Only jets whose titer range fits the final titer</i>.",
                  f"Vuelve a hacer clic en {B('Find jets')}."],
                 "Nada marcado = todas las toberas. Las toberas sin tipo aparecen como <i>(none)</i>."),
                ("task", "Fijar los ajustes de máquina, p. ej. 800 m/min",
                 ["En <i>4 Machine settings</i> escribe 800 en <i>from</i> y <i>to</i> de <i>Speed</i>.",
                  "Limita la presión de aire igual, p. ej. <i>to</i> 4 bar.",
                  f"Haz clic en {B('Find jets')}."],
                 "Solo cuentan los ajustes dentro de estos límites. Si ningún ensayo está en ese rango, no se muestra "
                 "ninguna tobera - el asesor nunca adivina más allá de lo medido."),
                ("task", "Ahorrar aire",
                 ["Pon <i>When equally good, prefer</i> en <i>Less air</i>.",
                  f"Haz clic en {B('Find jets')}."],
                 "Entre ajustes igual de buenos gana el de menor consumo de aire (presión más baja, orificio más "
                 "pequeño). La columna <i>Air</i> muestra Nm³/h por posición, calculado como en el Jet ROI Calculator."),
                ("task", "Comprobar de dónde viene una recomendación",
                 ["Haz clic en una tobera del resultado.",
                  "Debajo ves por qué se eligió ese ajuste, cuántos ensayos hay detrás y las series de ensayos "
                  "(doble clic / clic las abre; en el escritorio Ctrl = pestaña nueva).",
                  f"{B('Open in Process Playground')} abre este hilo y esta tobera allí - para ver qué pasa alrededor "
                  "del ajuste recomendado."]),
                ("h", "Si no se encuentra nada"),
                ("task", "Ningún hilo similar / ninguna tobera",
                 ["Pon <i>Similar yarns</i> en <i>wide (±50 %)</i>.",
                  "Desmarca <i>Only the same material</i>.",
                  "Afloja los filtros de toberas o los ajustes de máquina."],
                 "La línea encima del resultado muestra qué hilos se usaron y a qué distancia están del tuyo."),
            ]},
            {"key": "method", "title": "Cómo decide", "blocks": [
                ("h", "1  Hilos similares"),
                ("p", "Se buscan en nuestros ensayos hilos como el tuyo: mismo material (si está marcado), título final y "
                      "número de filamentos cercanos. La <i>distancia</i> es 0 para el mismo hilo y 1 para aprox. "
                      "30 % más o menos título o 50 % más o menos filamentos. Los hilos de varios cabos cuentan con la "
                      "suma de título y filamentos."),
                ("h", "2  Por tobera: ajustes medidos y modelados"),
                ("p", "Para cada tobera usada con esos hilos, cada ajuste realmente probado es un candidato "
                      "(<i>measured</i>). Donde se variaron presión, sobrealimentación o velocidad, el modelo del "
                      "Process Playground rellena los huecos entre ellos (<i>model</i>) - solo cerca de ajustes "
                      "probados, nunca más allá del rango medido."),
                ("h", "3  Probabilidad de alcanzar los objetivos"),
                ("p", "Para cada candidato se estiman el valor esperado de cada objetivo y su dispersión para una nueva "
                      "prueba: la dispersión de ensayos repetidos, la incertidumbre del modelo y las diferencias entre "
                      "series. De ahí sale la probabilidad de que una nueva prueba cumpla todos los objetivos."),
                ("h", "4  Orden"),
                ("ul", ["Cada tobera muestra su mejor ajuste; la <i>ventana</i> bajo el valor es el rango casi igual de "
                        "bueno (al menos el 90 % de la mejor probabilidad).",
                        "Orden: probabilidad (algo menor para hilos menos similares), luego cuánto se fallan los "
                        "objetivos, luego <i>margen de seguridad</i> (distancia al límite más cercano en dispersiones) "
                        "o <i>menos aire</i>.",
                        "Si ninguna tobera alcanza los objetivos, se muestran igualmente las más cercanas - con ✗ en el "
                        "objetivo fallado."]),
                ("warn", "La probabilidad es una estimación a partir de nuestros ensayos, no una garantía. Confirma "
                         "siempre la recomendación con un ensayo - y fíjate en <i>Source</i> y en el número de ensayos."),
                ("p", "Solo DTY. Valores de laboratorio: puntos/m y CV (Itemat), estabilidad 0.3 / 0.6 / 1.0 / 1.3. "
                      "No se usan muestras de referencia; puntos/m = 0 cuenta como no medido."),
            ]},
            {"key": "screen", "title": "Pantalla", "blocks": [
                ("svg", SVG, {"hint_chance": "Chance: barra = probabilidad de que una nueva prueba cumpla todo",
                              "hint_window": "Números grises bajo un ajuste: la ventana casi igual de buena",
                              "hint_source": "measured = probado así · model = entre ajustes probados",
                              "hint_click": "Clic en una tobera: por qué, qué ensayos, abrir en el Process Playground"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Yarn", "Hilo existente o valores propios (material, título final, filamentos); cuán "
                                 "similares pueden ser los hilos usados; solo el mismo material."),
                    ("(2) Targets", "mín. y/o máx. por valor de laboratorio. Vacío = sin objetivo."),
                    ("(3) Jets", "Tipo de tobera (p. ej. Standard), fabricante, grupo, rango de título de la tobera. "
                                 "Nada marcado = todas."),
                    ("(4) Machine settings", "Límites de presión, sobrealimentación y velocidad; qué preferir si dos "
                                             "ajustes son igual de buenos. Find jets / Reset."),
                    ("(5) Resultado", "Una línea por tobera: probabilidad, ajuste recomendado con ventana, valores "
                                      "esperados ± dispersión (✓ / ✗), aire en Nm³/h, fuente, hilo y ensayos detrás."),
                    ("(6) Detalle", "Por qué este ajuste, margen o fallo, series de ensayos, Process Playground."),
                ]),
            ]},
        ],
    },
}
