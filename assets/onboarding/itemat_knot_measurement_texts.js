window.TEXTS = {
 "de": {
  "ui": {
   "eyebrow": "Onboarding · Labor",
   "h1": "Knotenmessung mit dem ITEMAT",
   "lead": "Das ITEMAT zählt die Knoten eines verwirbelten Filamentgarns und prüft, wie stabil sie unter Last sind. Sechs kurze Szenen zeigen Aufbau, Messprinzip, Schwelle, Stabilitätstest und Auswertung.",
   "note": "Schematische Darstellung auf Basis des ITEMAT+ von Textechno (Nachfolger des ITEMAT von Enka Tecnica). Das Garn ist simuliert, die Zahlen im Bild sind Beispielwerte. Gerätedaten aus dem Textechno-Datenblatt; die Stabilitätsformel ist die übliche Definition, keine Herstellerangabe.",
   "pause": "⏸ Pause",
   "play": "▶ Abspielen",
   "scenes": "Szenen",
   "thr": "Schwelle",
   "load": "Belastung",
   "low": "gering",
   "mid": "mittel",
   "high": "hoch",
   "newYarn": "↻ Neues Garn",
   "dec": ",",
   "clickHint": "Eine Station im Gerät anklicken: Sie wird hier erklärt."
  },
  "cv": {
   "yarnCut": "verwirbeltes Garn, Ausschnitt",
   "knot": "Knoten",
   "open": "offener Abschnitt",
   "kpm": "Knoten pro Meter",
   "example": "Beispielgarn",
   "stab": "Stabilität",
   "stab1": "Knoten, die unter Zug halten, sichern den Fadenschluss",
   "stab2": "beim Spulen, Weben, Wirken und Färben.",
   "stab3": "Offene Knoten bedeuten: Filamente spleissen auf.",
   "pre": "0,5–100 cN",
   "outRoll": "Ausgangswalze",
   "tsiRange": "bis 1200 cN, bis 100 %",
   "sensorType": "mechanisch oder optisch",
   "ctrl": "Regelung: Ausgangswalze und Abzug, Ziel ≈ 0 cN vor dem Sensor",
   "waste": "Abfall",
   "pc": "PC-Auswertung",
   "force": "Andruckkraft",
   "movPin": "beweglicher Stift",
   "fixPin": "fester Stift",
   "openL": "offen: locker, Filamente nebeneinander",
   "pressed": "unter den Stiften flach gedrückt",
   "knotThick": "Knoten bleibt dick und hebt den Stift",
   "defl": "Auslenkung {v}",
   "thr": "Schwelle",
   "sig30": "Signal der letzten 30 cm",
   "counted": "gezählt {n} Knoten/m",
   "actual": "tatsächlich {n}",
   "real": "echter Knoten",
   "false": "Fehlzählung (Dickstelle, Rauschen)",
   "thrLow": "Schwelle zu tief: Dickstellen werden als Knoten gezählt",
   "thrHigh": "Schwelle zu hoch: schwache Knoten werden übersehen",
   "thrOk": "Schwelle passend",
   "light": "Lichtquelle",
   "recv": "Empfänger",
   "trans": "Lichtdurchlässigkeit",
   "run": "mitlaufende Schwelle",
   "dips": "Knoten lassen weniger Licht durch: Einbrüche im Signal",
   "noLoad": "ohne Belastung",
   "afterZone": "nach der Streckzone",
   "kNo": "Knoten/m ohne Last",
   "kLoad": "Knoten/m mit Last",
   "stabL": "Knotenstabilität",
   "formula": "= Knoten mit Last / Knoten ohne Last",
   "holds": "Knoten hält",
   "opened": "Knoten hat sich geöffnet",
   "profile": "Garnprofil, 1 m",
   "dist": "Verteilung der Knotenabstände",
   "mm": "mm",
   "rows": [
    "Knoten/m",
    "mittlerer Abstand",
    "Streuung der Abstände (CV)",
    "Stabilität (TSI)"
   ],
   "sample": "Beispielwerte aus dem simulierten Garn",
   "evenHint": "schmale Verteilung = gleichmässig verwirbelt"
  },
  "stations": [
   {
    "n": "Spule",
    "d": "Das Garn wird über Kopf von der Spule abgezogen."
   },
   {
    "n": "Aktiver Fadenspanner",
    "s": "Fadenspanner",
    "d": "Hält die Vorspannung konstant (0,5–100 cN), unabhängig davon, wie voll die Spule ist."
   },
   {
    "n": "Streckzone (nur TSI)",
    "s": "Streckzone (TSI)",
    "d": "Belastet das Garn für den Stabilitätstest: festes Verstreckverhältnis oder feste Zugkraft, bis 1200 cN und bis 100 % Verstreckung."
   },
   {
    "n": "Spannungsmessung",
    "d": "Misst die Fadenspannung direkt vor dem Sensor und regelt Ausgangswalze und Abzug so, dass sie möglichst 0 cN ist."
   },
   {
    "n": "Messsensor",
    "d": "Mechanisch mit zwei Keramikstiften oder optisch mit einer Lichtschranke. Misst das entspannte Garn."
   },
   {
    "n": "Abzug",
    "d": "Zieht das Garn mit Prüfgeschwindigkeit durch das Gerät und entsorgt es."
   }
  ],
  "scenes": [
   {
    "k": "Wozu",
    "title": "Was das ITEMAT misst",
    "text": "Ein verwirbeltes Filamentgarn wechselt zwischen Knoten und offenen Abschnitten. Für die Qualität zählen vor allem zwei Werte: wie viele Knoten pro Meter vorhanden sind und wie stabil sie sind, also ob sie unter Zug halten. Genau das misst das ITEMAT, für POY, FDY, DTY und BCF. Aus den Knotenpositionen ergibt sich zusätzlich, wie gleichmässig die Knoten verteilt sind.",
    "facts": [
     [
      "Knotenzahl",
      "Knoten pro Meter"
     ],
     [
      "Stabilität",
      "halten die Knoten unter Last?"
     ],
     [
      "Gleichmässigkeit",
      "Streuung der Knotenabstände"
     ],
     [
      "Garne",
      "POY, FDY, DTY, BCF"
     ],
     [
      "Titer",
      "30–5000 dtex"
     ]
    ]
   },
   {
    "k": "Aufbau",
    "title": "Der Weg des Garns durch das Gerät",
    "text": "Das Garn wird von der Spule abgezogen und läuft durch einen aktiven Fadenspanner, der eine konstante Vorspannung einstellt. Bei der TSI-Version folgt eine Streckzone für den Stabilitätstest. Direkt vor dem Messsensor misst ein Spannungssensor die Fadenspannung. Über die Geschwindigkeit der Ausgangswalze der Streckzone und des Abzugs wird sie geregelt, so dass das Garn möglichst ohne Spannung durch den Messsensor läuft. Danach wird es abgezogen. Bis zu fünf Spulen lassen sich im Mehrplatzschrank gleichzeitig prüfen.",
    "facts": [
     [
      "Vorspannung",
      "0,5–100 cN (Sensor 100 cN)"
     ],
     [
      "Geschwindigkeit",
      "bis 100 m/min mechanisch, 500 m/min optisch"
     ],
     [
      "TSI",
      "Streckzone bis 1200 cN, bis 100 % Verstreckung"
     ],
     [
      "Vor dem Sensor",
      "Spannung geregelt auf möglichst 0 cN"
     ],
     [
      "Automatik",
      "Spulenwechsler, bis 5 Prüfstellen"
     ],
     [
      "Stationen",
      "im Bild anklicken, um sie erklärt zu bekommen"
     ]
    ]
   },
   {
    "k": "Messprinzip",
    "title": "Mechanische Dickenabtastung",
    "text": "Zwei Keramikstifte drücken auf das Garn, einer fest, einer beweglich mit definierter Kraft. Im offenen Abschnitt liegen die Filamente nebeneinander und das Garn wird flach gedrückt. Ein Knoten bleibt dick und hebt den beweglichen Stift an. Diese Auslenkung wird als Signal aufgezeichnet. Jede Spitze über der Schwelle zählt als Knoten. Mit dem Regler lässt sich zeigen, was eine falsche Schwelle bewirkt.",
    "facts": [
     [
      "Sensor",
      "zwei Keramikstifte, einer beweglich"
     ],
     [
      "Offen",
      "Garn wird flach gedrückt"
     ],
     [
      "Knoten",
      "bleibt dick, Stift hebt sich"
     ],
     [
      "Schwelle",
      "fest empfohlen bei Dickenabtastung"
     ]
    ]
   },
   {
    "k": "Optisch",
    "title": "Optische Messung mit Lichtschranke",
    "text": "Alternativ läuft das Garn durch eine Lichtschranke. Offene Abschnitte und Knoten lassen unterschiedlich viel Licht durch. Das geht schneller, funktioniert aber nur zuverlässig, wenn die Knoten von Auge sichtbar sind, also bei DTY und BCF. Hier wird eine mitlaufende Schwelle empfohlen.",
    "facts": [
     [
      "Prinzip",
      "Lichtdurchlässigkeit"
     ],
     [
      "Geschwindigkeit",
      "bis 500 m/min"
     ],
     [
      "Eignung",
      "DTY und BCF"
     ],
     [
      "Schwelle",
      "mitlaufend empfohlen"
     ]
    ]
   },
   {
    "k": "Stabilität",
    "title": "Stabilitätstest unter Last (TSI)",
    "text": "Bei der TSI-Version läuft das Garn vor dem Sensor durch eine Streckzone. Dort wird es mit einem festen Verstreckverhältnis oder einer festen Zugkraft belastet. Schwache Knoten öffnen sich dabei. Gezählt wird, wie viele Knoten danach noch da sind. Das Verhältnis zur Knotenzahl ohne Last ist die Knotenstabilität.",
    "facts": [
     [
      "Belastung",
      "Verstreckung oder Zugkraft"
     ],
     [
      "Stabilität",
      "Knoten mit Last / Knoten ohne Last × 100 %"
     ],
     [
      "Aussage",
      "wie gut der Fadenschluss in der Weiterverarbeitung hält"
     ],
     [
      "Regler",
      "Belastung probieren"
     ]
    ]
   },
   {
    "k": "Auswertung",
    "title": "Was am Ende herauskommt",
    "text": "Die Software zeigt das Garnprofil mit den erkannten Knoten und der Schwelle und rechnet die Kennwerte aus. Aus den Positionen der Knoten lassen sich auch die Abstände zwischen den Knoten auswerten: Ein gleichmässiges Garn hat eine schmale Verteilung, ein unruhiges eine breite. Viele stabile Knoten nützen wenig, wenn sie ungleichmässig verteilt sind.",
    "facts": [
     [
      "Knoten/m",
      "Mittelwert über die Prüflänge"
     ],
     [
      "Abstände",
      "Verteilung, Mittelwert, Streuung (CV)"
     ],
     [
      "Stabilität",
      "in % bei TSI"
     ],
     [
      "Ausgabe",
      "Statistik, Profilgrafik, USB-Export"
     ],
     [
      "Neues Garn",
      "Knopf unten: anderes Beispielgarn"
     ]
    ]
   }
  ]
 },
 "en": {
  "ui": {
   "eyebrow": "Onboarding · Lab",
   "h1": "Nip measurement with the ITEMAT",
   "lead": "The ITEMAT counts the nips of an intermingled filament yarn and checks how stable they are under load. Six short scenes show set-up, measuring principle, threshold, stability test and evaluation.",
   "note": "Schematic representation based on the ITEMAT+ by Textechno (successor of the ITEMAT by Enka Tecnica). The yarn is simulated, the figures in the picture are example values. Device data from the Textechno data sheet; the stability formula is the usual definition, not a manufacturer statement.",
   "pause": "⏸ Pause",
   "play": "▶ Play",
   "scenes": "Scenes",
   "thr": "Threshold",
   "load": "Load",
   "low": "low",
   "mid": "medium",
   "high": "high",
   "newYarn": "↻ New yarn",
   "dec": ".",
   "clickHint": "Click a station of the device: it is explained here."
  },
  "cv": {
   "yarnCut": "intermingled yarn, detail",
   "knot": "Nip",
   "open": "open section",
   "kpm": "nips per metre",
   "example": "example yarn",
   "stab": "Stability",
   "stab1": "Nips that hold under tension keep the yarn together",
   "stab2": "during winding, weaving, knitting and dyeing.",
   "stab3": "Open nips mean: the filaments splay out.",
   "pre": "0.5–100 cN",
   "outRoll": "Output roll",
   "tsiRange": "up to 1200 cN, up to 100 %",
   "sensorType": "mechanical or optical",
   "ctrl": "Control: output roll and take-off, target ≈ 0 cN before the sensor",
   "waste": "Waste",
   "pc": "PC evaluation",
   "force": "Contact force",
   "movPin": "movable pin",
   "fixPin": "fixed pin",
   "openL": "open: loose, filaments side by side",
   "pressed": "pressed flat under the pins",
   "knotThick": "nip stays thick and lifts the pin",
   "defl": "Deflection {v}",
   "thr": "Threshold",
   "sig30": "Signal of the last 30 cm",
   "counted": "counted {n} nips/m",
   "actual": "actual {n}",
   "real": "real nip",
   "false": "false count (thick spot, noise)",
   "thrLow": "Threshold too low: thick spots are counted as nips",
   "thrHigh": "Threshold too high: weak nips are missed",
   "thrOk": "Threshold suitable",
   "light": "Light source",
   "recv": "Receiver",
   "trans": "Light transmission",
   "run": "floating threshold",
   "dips": "Nips let less light through: dips in the signal",
   "noLoad": "without load",
   "afterZone": "after the stretch zone",
   "kNo": "nips/m without load",
   "kLoad": "nips/m with load",
   "stabL": "Nip stability",
   "formula": "= nips with load / nips without load",
   "holds": "nip holds",
   "opened": "nip has opened",
   "profile": "Yarn profile, 1 m",
   "dist": "Distribution of nip distances",
   "mm": "mm",
   "rows": [
    "Nips/m",
    "mean distance",
    "spread of distances (CV)",
    "Stability (TSI)"
   ],
   "sample": "Example values from the simulated yarn",
   "evenHint": "narrow distribution = evenly intermingled"
  },
  "stations": [
   {
    "n": "Package",
    "d": "The yarn is pulled off the package overhead."
   },
   {
    "n": "Active yarn tensioner",
    "s": "Yarn tensioner",
    "d": "Keeps the pretension constant (0.5–100 cN), regardless of how full the package is."
   },
   {
    "n": "Stretch zone (TSI only)",
    "s": "Stretch zone (TSI)",
    "d": "Loads the yarn for the stability test: fixed draw ratio or fixed tensile force, up to 1200 cN and up to 100 % draw."
   },
   {
    "n": "Tension measurement",
    "d": "Measures the yarn tension right before the sensor and controls output roll and take-off so that it is as close to 0 cN as possible."
   },
   {
    "n": "Measuring sensor",
    "d": "Mechanical with two ceramic pins or optical with a light barrier. Measures the relaxed yarn."
   },
   {
    "n": "Take-off",
    "d": "Pulls the yarn through the device at test speed and disposes of it."
   }
  ],
  "scenes": [
   {
    "k": "Purpose",
    "title": "What the ITEMAT measures",
    "text": "An intermingled filament yarn alternates between nips and open sections. Two values matter most for quality: how many nips there are per metre and how stable they are, i.e. whether they hold under tension. That is exactly what the ITEMAT measures, for POY, FDY, DTY and BCF. The nip positions also show how evenly the nips are distributed.",
    "facts": [
     [
      "Nip count",
      "nips per metre"
     ],
     [
      "Stability",
      "do the nips hold under load?"
     ],
     [
      "Evenness",
      "spread of the nip distances"
     ],
     [
      "Yarns",
      "POY, FDY, DTY, BCF"
     ],
     [
      "Count",
      "30–5000 dtex"
     ]
    ]
   },
   {
    "k": "Set-up",
    "title": "The path of the yarn through the device",
    "text": "The yarn is pulled off the package and runs through an active yarn tensioner that sets a constant pretension. In the TSI version a stretch zone for the stability test follows. Right before the measuring sensor a tension sensor measures the yarn tension. It is controlled via the speed of the output roll of the stretch zone and the take-off, so that the yarn runs through the measuring sensor with as little tension as possible. Then it is taken off. Up to five packages can be tested at the same time in the multi-position cabinet.",
    "facts": [
     [
      "Pretension",
      "0.5–100 cN (sensor 100 cN)"
     ],
     [
      "Speed",
      "up to 100 m/min mechanical, 500 m/min optical"
     ],
     [
      "TSI",
      "stretch zone up to 1200 cN, up to 100 % draw"
     ],
     [
      "Before the sensor",
      "tension controlled to as close to 0 cN as possible"
     ],
     [
      "Automation",
      "package changer, up to 5 test positions"
     ],
     [
      "Stations",
      "click them in the picture to have them explained"
     ]
    ]
   },
   {
    "k": "Principle",
    "title": "Mechanical thickness scanning",
    "text": "Two ceramic pins press on the yarn, one fixed, one movable with a defined force. In the open section the filaments lie side by side and the yarn is pressed flat. A nip stays thick and lifts the movable pin. This deflection is recorded as a signal. Every peak above the threshold counts as a nip. Use the slider to see what a wrong threshold does.",
    "facts": [
     [
      "Sensor",
      "two ceramic pins, one movable"
     ],
     [
      "Open",
      "yarn is pressed flat"
     ],
     [
      "Nip",
      "stays thick, pin lifts"
     ],
     [
      "Threshold",
      "fixed threshold recommended for thickness scanning"
     ]
    ]
   },
   {
    "k": "Optical",
    "title": "Optical measurement with a light barrier",
    "text": "Alternatively the yarn runs through a light barrier. Open sections and nips let different amounts of light through. This is faster, but only works reliably if the nips are visible to the eye, i.e. for DTY and BCF. A floating threshold is recommended here.",
    "facts": [
     [
      "Principle",
      "light transmission"
     ],
     [
      "Speed",
      "up to 500 m/min"
     ],
     [
      "Suitable for",
      "DTY and BCF"
     ],
     [
      "Threshold",
      "floating recommended"
     ]
    ]
   },
   {
    "k": "Stability",
    "title": "Stability test under load (TSI)",
    "text": "In the TSI version the yarn runs through a stretch zone before the sensor. There it is loaded with a fixed draw ratio or a fixed tensile force. Weak nips open. What is counted is how many nips are still there afterwards. The ratio to the nip count without load is the nip stability.",
    "facts": [
     [
      "Load",
      "draw or tensile force"
     ],
     [
      "Stability",
      "nips with load / nips without load × 100 %"
     ],
     [
      "Meaning",
      "how well the yarn cohesion holds in further processing"
     ],
     [
      "Slider",
      "try the load"
     ]
    ]
   },
   {
    "k": "Evaluation",
    "title": "What comes out at the end",
    "text": "The software shows the yarn profile with the detected nips and the threshold and calculates the key figures. From the nip positions the distances between the nips can be evaluated too: an even yarn has a narrow distribution, an unsteady one a broad one. Many stable nips are of little use if they are unevenly distributed.",
    "facts": [
     [
      "Nips/m",
      "mean over the test length"
     ],
     [
      "Distances",
      "distribution, mean, spread (CV)"
     ],
     [
      "Stability",
      "in % with TSI"
     ],
     [
      "Output",
      "statistics, profile graph, USB export"
     ],
     [
      "New yarn",
      "button below: another example yarn"
     ]
    ]
   }
  ]
 },
 "es": {
  "ui": {
   "eyebrow": "Onboarding · Laboratorio",
   "h1": "Medición de nudos con el ITEMAT",
   "lead": "El ITEMAT cuenta los nudos de un hilo de filamento entrelazado y comprueba lo estables que son bajo carga. Seis escenas cortas muestran el montaje, el principio de medición, el umbral, el ensayo de estabilidad y la evaluación.",
   "note": "Representación esquemática basada en el ITEMAT+ de Textechno (sucesor del ITEMAT de Enka Tecnica). El hilo es simulado, las cifras de la imagen son valores de ejemplo. Datos del equipo según la hoja técnica de Textechno; la fórmula de estabilidad es la definición habitual, no un dato del fabricante.",
   "pause": "⏸ Pausa",
   "play": "▶ Reproducir",
   "scenes": "Escenas",
   "thr": "Umbral",
   "load": "Carga",
   "low": "baja",
   "mid": "media",
   "high": "alta",
   "newYarn": "↻ Hilo nuevo",
   "dec": ",",
   "clickHint": "Haz clic en una estación del equipo: se explica aquí."
  },
  "cv": {
   "yarnCut": "hilo entrelazado, detalle",
   "knot": "Nudo",
   "open": "tramo abierto",
   "kpm": "nudos por metro",
   "example": "hilo de ejemplo",
   "stab": "Estabilidad",
   "stab1": "Los nudos que aguantan bajo tracción mantienen unido el hilo",
   "stab2": "al bobinar, tejer, tricotar y teñir.",
   "stab3": "Nudos abiertos significan: los filamentos se separan.",
   "pre": "0,5–100 cN",
   "outRoll": "Rodillo de salida",
   "tsiRange": "hasta 1200 cN, hasta 100 %",
   "sensorType": "mecánico u óptico",
   "ctrl": "Regulación: rodillo de salida y extracción, objetivo ≈ 0 cN antes del sensor",
   "waste": "Residuo",
   "pc": "Evaluación PC",
   "force": "Fuerza de apriete",
   "movPin": "perno móvil",
   "fixPin": "perno fijo",
   "openL": "abierto: suelto, filamentos uno junto a otro",
   "pressed": "aplastado bajo los pernos",
   "knotThick": "el nudo sigue grueso y levanta el perno",
   "defl": "Desviación {v}",
   "thr": "Umbral",
   "sig30": "Señal de los últimos 30 cm",
   "counted": "contados {n} nudos/m",
   "actual": "reales {n}",
   "real": "nudo real",
   "false": "conteo falso (punto grueso, ruido)",
   "thrLow": "Umbral demasiado bajo: los puntos gruesos se cuentan como nudos",
   "thrHigh": "Umbral demasiado alto: se pasan por alto nudos débiles",
   "thrOk": "Umbral adecuado",
   "light": "Fuente de luz",
   "recv": "Receptor",
   "trans": "Transmisión de luz",
   "run": "umbral flotante",
   "dips": "Los nudos dejan pasar menos luz: caídas en la señal",
   "noLoad": "sin carga",
   "afterZone": "tras la zona de estirado",
   "kNo": "nudos/m sin carga",
   "kLoad": "nudos/m con carga",
   "stabL": "Estabilidad de los nudos",
   "formula": "= nudos con carga / nudos sin carga",
   "holds": "el nudo aguanta",
   "opened": "el nudo se ha abierto",
   "profile": "Perfil del hilo, 1 m",
   "dist": "Distribución de distancias entre nudos",
   "mm": "mm",
   "rows": [
    "Nudos/m",
    "distancia media",
    "dispersión de distancias (CV)",
    "Estabilidad (TSI)"
   ],
   "sample": "Valores de ejemplo del hilo simulado",
   "evenHint": "distribución estrecha = entrelazado regular"
  },
  "stations": [
   {
    "n": "Bobina",
    "d": "El hilo se saca de la bobina por encima del extremo."
   },
   {
    "n": "Tensor de hilo activo",
    "s": "Tensor",
    "d": "Mantiene constante la pretensión (0,5–100 cN), independientemente de lo llena que esté la bobina."
   },
   {
    "n": "Zona de estirado (solo TSI)",
    "s": "Zona de estirado (TSI)",
    "d": "Carga el hilo para el ensayo de estabilidad: relación de estirado fija o fuerza de tracción fija, hasta 1200 cN y hasta 100 % de estirado."
   },
   {
    "n": "Medición de tensión",
    "s": "Tensión",
    "d": "Mide la tensión del hilo justo antes del sensor y regula el rodillo de salida y la extracción para que sea lo más cercana posible a 0 cN."
   },
   {
    "n": "Sensor de medición",
    "s": "Sensor",
    "d": "Mecánico con dos pernos cerámicos u óptico con una barrera de luz. Mide el hilo relajado."
   },
   {
    "n": "Extracción",
    "d": "Tira del hilo a través del equipo a la velocidad de ensayo y lo desecha."
   }
  ],
  "scenes": [
   {
    "k": "Para qué",
    "title": "Qué mide el ITEMAT",
    "text": "Un hilo de filamento entrelazado alterna entre nudos y tramos abiertos. Para la calidad cuentan sobre todo dos valores: cuántos nudos hay por metro y lo estables que son, es decir, si aguantan bajo tracción. Eso es exactamente lo que mide el ITEMAT, para POY, FDY, DTY y BCF. Las posiciones de los nudos muestran además lo regular que es su reparto.",
    "facts": [
     [
      "Número de nudos",
      "nudos por metro"
     ],
     [
      "Estabilidad",
      "¿aguantan los nudos bajo carga?"
     ],
     [
      "Regularidad",
      "dispersión de las distancias entre nudos"
     ],
     [
      "Hilos",
      "POY, FDY, DTY, BCF"
     ],
     [
      "Título",
      "30–5000 dtex"
     ]
    ]
   },
   {
    "k": "Montaje",
    "title": "El recorrido del hilo por el equipo",
    "text": "El hilo se saca de la bobina y pasa por un tensor activo que ajusta una pretensión constante. En la versión TSI sigue una zona de estirado para el ensayo de estabilidad. Justo antes del sensor de medición, un sensor mide la tensión del hilo. Se regula mediante la velocidad del rodillo de salida de la zona de estirado y de la extracción, para que el hilo pase por el sensor con la menor tensión posible. Después se extrae. En el armario multipuesto se pueden ensayar hasta cinco bobinas a la vez.",
    "facts": [
     [
      "Pretensión",
      "0,5–100 cN (sensor 100 cN)"
     ],
     [
      "Velocidad",
      "hasta 100 m/min mecánico, 500 m/min óptico"
     ],
     [
      "TSI",
      "zona de estirado hasta 1200 cN, hasta 100 % de estirado"
     ],
     [
      "Antes del sensor",
      "tensión regulada lo más cerca posible de 0 cN"
     ],
     [
      "Automatización",
      "cambiador de bobinas, hasta 5 puestos"
     ],
     [
      "Estaciones",
      "haz clic en la imagen para ver la explicación"
     ]
    ]
   },
   {
    "k": "Principio",
    "title": "Exploración mecánica del espesor",
    "text": "Dos pernos cerámicos presionan el hilo, uno fijo y otro móvil con una fuerza definida. En el tramo abierto los filamentos están uno junto a otro y el hilo se aplasta. Un nudo sigue grueso y levanta el perno móvil. Esta desviación se registra como señal. Cada pico por encima del umbral cuenta como nudo. Con el regulador se ve qué provoca un umbral incorrecto.",
    "facts": [
     [
      "Sensor",
      "dos pernos cerámicos, uno móvil"
     ],
     [
      "Abierto",
      "el hilo se aplasta"
     ],
     [
      "Nudo",
      "sigue grueso, el perno se levanta"
     ],
     [
      "Umbral",
      "fijo recomendado en la exploración de espesor"
     ]
    ]
   },
   {
    "k": "Óptico",
    "title": "Medición óptica con barrera de luz",
    "text": "Como alternativa, el hilo pasa por una barrera de luz. Los tramos abiertos y los nudos dejan pasar distinta cantidad de luz. Es más rápido, pero solo funciona bien si los nudos se ven a simple vista, es decir, en DTY y BCF. Aquí se recomienda un umbral flotante.",
    "facts": [
     [
      "Principio",
      "transmisión de luz"
     ],
     [
      "Velocidad",
      "hasta 500 m/min"
     ],
     [
      "Apto para",
      "DTY y BCF"
     ],
     [
      "Umbral",
      "flotante recomendado"
     ]
    ]
   },
   {
    "k": "Estabilidad",
    "title": "Ensayo de estabilidad bajo carga (TSI)",
    "text": "En la versión TSI el hilo pasa antes del sensor por una zona de estirado. Allí se carga con una relación de estirado fija o una fuerza de tracción fija. Los nudos débiles se abren. Se cuenta cuántos nudos quedan después. La relación con el número de nudos sin carga es la estabilidad de los nudos.",
    "facts": [
     [
      "Carga",
      "estirado o fuerza de tracción"
     ],
     [
      "Estabilidad",
      "nudos con carga / nudos sin carga × 100 %"
     ],
     [
      "Significado",
      "lo bien que se mantiene la cohesión en el procesamiento posterior"
     ],
     [
      "Regulador",
      "prueba la carga"
     ]
    ]
   },
   {
    "k": "Evaluación",
    "title": "Qué sale al final",
    "text": "El software muestra el perfil del hilo con los nudos detectados y el umbral y calcula los indicadores. A partir de las posiciones de los nudos también se pueden evaluar las distancias entre ellos: un hilo regular tiene una distribución estrecha, uno irregular una ancha. Muchos nudos estables sirven de poco si están repartidos de forma irregular.",
    "facts": [
     [
      "Nudos/m",
      "media sobre la longitud de ensayo"
     ],
     [
      "Distancias",
      "distribución, media, dispersión (CV)"
     ],
     [
      "Estabilidad",
      "en % con TSI"
     ],
     [
      "Salida",
      "estadística, gráfico de perfil, exportación USB"
     ],
     [
      "Hilo nuevo",
      "botón abajo: otro hilo de ejemplo"
     ]
    ]
   }
  ]
 },
 "zh": {
  "ui": {
   "eyebrow": "入门 · 实验室",
   "h1": "用 ITEMAT 测量网络点",
   "lead": "ITEMAT 统计网络丝的网络点数量，并检测网络点在负荷下的牢度。六个简短场景展示结构、测量原理、阈值、牢度测试和评估。",
   "note": "基于 Textechno ITEMAT+（Enka Tecnica ITEMAT 的后继机型）的示意图。纱线为模拟，图中数字为示例值。设备数据来自 Textechno 数据表；牢度公式为通用定义，并非厂商数据。",
   "pause": "⏸ 暂停",
   "play": "▶ 播放",
   "scenes": "场景",
   "thr": "阈值",
   "load": "负荷",
   "low": "低",
   "mid": "中",
   "high": "高",
   "newYarn": "↻ 换一根丝",
   "dec": ".",
   "clickHint": "点击设备中的工位，此处会显示说明。"
  },
  "cv": {
   "yarnCut": "网络丝局部",
   "knot": "网络点",
   "open": "开放段",
   "kpm": "每米网络点数",
   "example": "示例丝",
   "stab": "牢度",
   "stab1": "在拉力下保持的网络点使丝抱合",
   "stab2": "适用于络筒、机织、针织和染色。",
   "stab3": "网络点打开意味着：单丝散开。",
   "pre": "0.5–100 cN",
   "outRoll": "输出辊",
   "tsiRange": "最高 1200 cN，最高 100 %",
   "sensorType": "机械式或光学式",
   "ctrl": "调节：输出辊和引出辊，目标是传感器前约 0 cN",
   "waste": "废丝",
   "pc": "电脑评估",
   "force": "压力",
   "movPin": "活动销",
   "fixPin": "固定销",
   "openL": "开放段：松散，单丝并排",
   "pressed": "在两销之间被压扁",
   "knotThick": "网络点保持厚度并顶起销",
   "defl": "位移 {v}",
   "thr": "阈值",
   "sig30": "最近 30 cm 的信号",
   "counted": "计数 {n} 个/米",
   "actual": "实际 {n}",
   "real": "真实网络点",
   "false": "误计数（粗节、噪声）",
   "thrLow": "阈值过低：粗节被计为网络点",
   "thrHigh": "阈值过高：弱网络点被漏计",
   "thrOk": "阈值合适",
   "light": "光源",
   "recv": "接收器",
   "trans": "透光率",
   "run": "浮动阈值",
   "dips": "网络点透光更少：信号出现下陷",
   "noLoad": "无负荷",
   "afterZone": "经过拉伸区后",
   "kNo": "无负荷时每米网络点数",
   "kLoad": "有负荷时每米网络点数",
   "stabL": "网络点牢度",
   "formula": "= 有负荷网络点数 / 无负荷网络点数",
   "holds": "网络点保持",
   "opened": "网络点已打开",
   "profile": "纱线轮廓，1 米",
   "dist": "网络点间距分布",
   "mm": "mm",
   "rows": [
    "每米网络点数",
    "平均间距",
    "间距离散（CV）",
    "牢度（TSI）"
   ],
   "sample": "模拟丝的示例值",
   "evenHint": "分布窄 = 网络均匀"
  },
  "stations": [
   {
    "n": "丝筒",
    "d": "丝从丝筒顶端退绕引出。"
   },
   {
    "n": "主动张力器",
    "s": "张力器",
    "d": "使预张力保持恒定（0.5–100 cN），与丝筒的满筒程度无关。"
   },
   {
    "n": "拉伸区（仅 TSI）",
    "s": "拉伸区（TSI）",
    "d": "为牢度测试对丝施加负荷：固定拉伸比或固定拉力，最高 1200 cN、最高 100 % 拉伸。"
   },
   {
    "n": "张力测量",
    "d": "在传感器前测量丝的张力，并调节输出辊和引出辊，使张力尽量接近 0 cN。"
   },
   {
    "n": "测量传感器",
    "s": "传感器",
    "d": "机械式（两个陶瓷销）或光学式（光栅）。测量松弛状态下的丝。"
   },
   {
    "n": "引出",
    "d": "以测试速度把丝拉过设备并作为废丝处理。"
   }
  ],
  "scenes": [
   {
    "k": "用途",
    "title": "ITEMAT 测量什么",
    "text": "网络丝由网络点和开放段交替组成。对质量最重要的是两个值：每米有多少网络点，以及它们有多牢，即在拉力下是否保持。ITEMAT 正是测量这些，适用于 POY、FDY、DTY 和 BCF。网络点的位置还能显示其分布是否均匀。",
    "facts": [
     [
      "网络点数",
      "每米网络点数"
     ],
     [
      "牢度",
      "网络点在负荷下是否保持？"
     ],
     [
      "均匀性",
      "网络点间距的离散"
     ],
     [
      "纱线",
      "POY、FDY、DTY、BCF"
     ],
     [
      "纤度",
      "30–5000 dtex"
     ]
    ]
   },
   {
    "k": "结构",
    "title": "丝在设备中的路径",
    "text": "丝从丝筒引出，经过设定恒定预张力的主动张力器。TSI 型号随后有一个用于牢度测试的拉伸区。在测量传感器前，张力传感器测量丝的张力，并通过拉伸区输出辊和引出辊的速度进行调节，使丝尽量无张力地通过测量传感器。之后丝被引出。多工位柜中最多可同时测试五个丝筒。",
    "facts": [
     [
      "预张力",
      "0.5–100 cN（传感器 100 cN）"
     ],
     [
      "速度",
      "机械式最高 100 m/min，光学式 500 m/min"
     ],
     [
      "TSI",
      "拉伸区最高 1200 cN，最高 100 % 拉伸"
     ],
     [
      "传感器前",
      "张力调节到尽量接近 0 cN"
     ],
     [
      "自动化",
      "换筒装置，最多 5 个测试位"
     ],
     [
      "工位",
      "在图中点击即可查看说明"
     ]
    ]
   },
   {
    "k": "测量原理",
    "title": "机械式厚度检测",
    "text": "两个陶瓷销压在丝上，一个固定，一个以规定压力活动。在开放段，单丝并排，丝被压扁。网络点保持厚度并顶起活动销。这一位移被记录为信号。每个超过阈值的峰都计为一个网络点。可用滑块观察阈值设置错误的后果。",
    "facts": [
     [
      "传感器",
      "两个陶瓷销，一个可动"
     ],
     [
      "开放段",
      "丝被压扁"
     ],
     [
      "网络点",
      "保持厚度，销被顶起"
     ],
     [
      "阈值",
      "厚度检测推荐固定阈值"
     ]
    ]
   },
   {
    "k": "光学",
    "title": "用光栅进行光学测量",
    "text": "另一种方式是让丝通过光栅。开放段和网络点透过的光量不同。这种方式更快，但只有在网络点肉眼可见时才可靠，即适用于 DTY 和 BCF。此时推荐使用浮动阈值。",
    "facts": [
     [
      "原理",
      "透光率"
     ],
     [
      "速度",
      "最高 500 m/min"
     ],
     [
      "适用",
      "DTY 和 BCF"
     ],
     [
      "阈值",
      "推荐浮动阈值"
     ]
    ]
   },
   {
    "k": "牢度",
    "title": "负荷下的牢度测试（TSI）",
    "text": "在 TSI 型号中，丝在传感器前经过拉伸区。在那里以固定拉伸比或固定拉力加载。弱的网络点会打开。统计之后仍然存在的网络点数量。与无负荷时网络点数之比即为网络点牢度。",
    "facts": [
     [
      "负荷",
      "拉伸或拉力"
     ],
     [
      "牢度",
      "有负荷网络点数 / 无负荷网络点数 × 100 %"
     ],
     [
      "意义",
      "后加工中抱合保持得如何"
     ],
     [
      "滑块",
      "试试改变负荷"
     ]
    ]
   },
   {
    "k": "评估",
    "title": "最终得到什么",
    "text": "软件显示带有识别出的网络点和阈值的纱线轮廓，并计算各项指标。根据网络点位置还可以评估网络点间距：均匀的丝分布窄，不均匀的丝分布宽。如果分布不均，再多再牢的网络点也用处不大。",
    "facts": [
     [
      "每米网络点数",
      "测试长度上的平均值"
     ],
     [
      "间距",
      "分布、平均值、离散（CV）"
     ],
     [
      "牢度",
      "TSI 时以 % 表示"
     ],
     [
      "输出",
      "统计、轮廓图、USB 导出"
     ],
     [
      "换一根丝",
      "下方按钮：换一个示例丝"
     ]
    ]
   }
  ]
 }
};
