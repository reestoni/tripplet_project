window.TEXTS = {
 "de": {
  "ui": {
   "eyebrow": "Grundkurs · Schmelzspinnen POY / FDY",
   "h1": "Düsen in der Filamentspinnerei",
   "lead": "Vom Loch in der Spinndüse bis zum Knoten im Faden: wo welche Düse sitzt, was Fachung und Teilung bedeuten und was die Druckluft im Fadenkanal mit den Filamenten anstellt.",
   "note": "Alle Angaben sind Richtwerte. Die Animationen zeigen das Prinzip, keine Konstruktion.",
   "sources": "Quellen der Zahlenwerte",
   "clickHint": "Eine Station in der Liste oder im Bild anklicken - sie wird markiert und erklärt.",
   "quench": "Anblasung",
   "linkBack": "Zur Filamentgarnspinnerei",
   "linkBackHint": "Die ganze Anlage vom Granulat bis zur Spule",
   "endsL": "Fachung",
   "pitchL": "Teilung",
   "ends": "{n}-fach",
   "rN": "Fäden pro Position",
   "rT": "Fadenabstand",
   "rW": "Breite über alle Fäden, (n − 1) · t",
   "jetPack": "Düsenpaket",
   "pitchDim": "Teilung t = {t} mm",
   "bobbins": "{n} Spulen auf der Spindel",
   "bobbin1": "1 Spule auf der Spindel",
   "packNote": "Die Stufen der Regler entsprechen einem realen Sortiment: Düsenpakete für 1 bis 32 Fäden und Teilungen von 4 bis 12 mm. Nicht jede Kombination gibt es für jeden Düsentyp.",
   "endsP": [
    "Fachung",
    "ist die Anzahl Fäden, die an einer Position parallel laufen und auf einer Wicklerspindel zu Spulen werden. Man sagt 12-fach oder 24-fach, englisch 12-end. Das Düsenpaket braucht genau so viele Fadenkanäle."
   ],
   "pitchP": [
    "Teilung",
    "ist der Abstand von Fadenmitte zu Fadenmitte im Düsenpaket, in Millimetern. Kleine Teilung heisst kompaktes Paket und kleine Umlenkwinkel, lässt aber weniger Platz für Luftkanal und Fadenführer."
   ],
   "jetType": "Düsentyp",
   "modeInt": "Verwirbelung",
   "modeMig": "Migration",
   "pressure": "Überdruck pe",
   "effectL": "Wirkung am Faden",
   "effInt": [
    "wenige, weiche Knoten",
    "mittlere Knotendichte",
    "viele, feste Knoten"
   ],
   "effMig": [
    "leichte Durchmischung",
    "kräftige Durchmischung, keine Knoten"
   ],
   "crossCap": "Querschnitt: Blick in Fadenlaufrichtung. Punkte = Filamente, Blau = Luft.",
   "sideCap": "Seitenansicht, schematisch. Abstände und Knotenform sind nicht massstäblich.",
   "channel": "Fadenkanal",
   "air": "Druckluft",
   "parallel": "Filamente parallel",
   "intOut": "offene Stelle und Knoten im Wechsel",
   "migOut": "durchmischt, ohne Knoten",
   "run": "Fadenlauf →",
   "intJet": "Verwirbelungsdüse",
   "migJet": "Migrationsdüse",
   "intP": [
    "Verwirbelung",
    "erzeugt Punkte mit Fadenschluss. Mehr Druck bringt mehr und festere Knoten, bis der Faden überfordert ist und die Gleichmässigkeit leidet. Höhere Geschwindigkeit und höhere Fadenspannung wirken dagegen: üblich sind 0,1 bis 0,25 cN/dtex hinter der Düse."
   ],
   "migP": [
    "Migration",
    "arbeitet mit wenig Druck. Die Filamente tauschen nur ihre Plätze im Bündel, das Öl gelangt von aussen nach innen, der Faden läuft ruhiger. Knoten sind hier nicht erwünscht."
   ],
   "formula": "q_vn = k · (pe + 1)   [m³/h pro Faden, Normbedingungen DIN 1343]",
   "airChannel": "Luftkanal",
   "kanal": "Ø {d} mm · bis ca. {t} dtex",
   "rK": "Faktor k",
   "rQ1": "Verbrauch pro Faden",
   "rQn": "Verbrauch pro Position",
   "atEnds": "bei {n}-fach",
   "airNote": "Die Faktoren und Titerbereiche sind Richtwerte aus dem Heberlein-Datenblatt PolyJet-SP-3 Migra. Für Verwirbelungsdüsen gelten bei gleichem Kanaldurchmesser dieselben Faktoren."
  },
  "scenes": [
   {
    "k": "Spinnlinie",
    "title": "Die Spinnlinie von oben nach unten",
    "text": "Ein Faden passiert auf dem Weg von der Schmelze zur Spule mehrere Düsen. Nur die erste formt ihn, alle anderen arbeiten mit Öl oder Luft."
   },
   {
    "k": "Fachung & Teilung",
    "title": "Fachung und Teilung",
    "text": "Eine Spinnposition verarbeitet nie nur einen Faden. Die Luftdüsen sitzen deshalb als Düsenpaket nebeneinander. Zwei Zahlen beschreiben dieses Paket."
   },
   {
    "k": "Fadenkanal",
    "title": "Was im Fadenkanal passiert",
    "text": "Die Luft tritt quer zum Faden in den Kanal, prallt auf die Gegenseite und teilt sich in zwei gegenläufige Wirbel. Die Filamente werden mitgerissen und verflechten sich. Vor und hinter der Düse bleibt der Faden kurz offen, dazwischen sitzt der Knoten."
   },
   {
    "k": "Luftverbrauch",
    "title": "Luftkanal, Druck und Verbrauch",
    "text": "Der Durchmesser des Luftkanals wird nach dem Titer gewählt: feiner Faden, kleine Bohrung. Der Verbrauch wächst linear mit dem Absolutdruck, und er fällt für jeden Faden der Fachung an."
   },
   {
    "k": "Begriffe",
    "title": "Die Begriffe auf einen Blick",
    "text": "Zum Nachschlagen: die wichtigsten Wörter rund um Düsen in der Filamentspinnerei."
   }
  ],
  "stations": [
   {
    "n": "Spinndüse",
    "d": "Die Spinnpumpe presst die Polymerschmelze unter hohem Druck durch feine Bohrungen. Jede Bohrung ergibt ein Filament: 72 Bohrungen liefern einen Faden f72. Die Anblasung kühlt die Filamente, bis sie fest sind."
   },
   {
    "n": "Präparationsdüse (Öler)",
    "d": "Hier laufen die Filamente zum Faden zusammen und erhalten die Spinnpräparation. Das Öl sitzt danach zuerst einseitig aussen auf dem Bündel."
   },
   {
    "n": "Migrationsdüse",
    "d": "Wenig Druckluft (0,5 bis 2,0 bar) verdichtet das Bündel leicht und treibt die Präparation bis in den Fadenkern. Es entstehen keine Verwirbelungspunkte."
   },
   {
    "n": "Galetten",
    "d": "Sie ziehen den Faden ab und stellen die Spannung ein. Bei POY bleibt der Faden vororientiert, bei FDY wird er zwischen den Galetten voll verstreckt."
   },
   {
    "n": "Verwirbelungsdüse",
    "d": "Druckluft (1,5 bis 6,0 bar) trifft quer auf den Faden und verschlingt die Filamente in regelmässigen Abständen zu Knoten. Der Faden bekommt Fadenschluss für Spule und Weiterverarbeitung."
   },
   {
    "n": "Wickler",
    "d": "Aufspulen mit mehreren tausend Metern pro Minute. Pro Position entstehen so viele Spulen, wie Fäden nebeneinander laufen. Diese Zahl ist die Fachung."
   }
  ],
  "gloss": [
   [
    "Fachung",
    "ends",
    "Anzahl Fäden pro Spinnposition und Wickler, etwa 12-fach. Bestimmt die Zahl der Fadenkanäle im Düsenpaket."
   ],
   [
    "Fachen",
    "doubling",
    "Zwei oder mehr Fäden zu einem zusammenführen, oft mit einer Luftdüse. Nicht mit der Fachung der Position verwechseln."
   ],
   [
    "Teilung",
    "pitch",
    "Abstand von Fadenmitte zu Fadenmitte im Düsenpaket, typisch 4 bis 12 mm."
   ],
   [
    "Titer",
    "dtex",
    "Feinheit des Fadens: Gramm pro 10 000 m. Massgebend ist der Titer in der Düse, nicht der Endtiter."
   ],
   [
    "Filamentzahl",
    "f",
    "Anzahl Einzelfilamente, gleich der Lochzahl der Spinndüse. 167f48 heisst 167 dtex aus 48 Filamenten."
   ],
   [
    "dpf",
    "dtex / f",
    "Titer pro Filament. Unter etwa 1 dpf spricht man von Mikrofilamenten. Sie verwirbeln leichter, sind aber empfindlicher."
   ],
   [
    "Düsenpaket",
    "jet pack",
    "Block mit allen Düsen einer Position, meist aus Keramik, auf einem Halter mit Luftanschluss."
   ],
   [
    "Fadenkanal",
    "",
    "Der Raum, durch den der Faden läuft und in dem die Luft wirkt. Ein seitlicher Einfädelschlitz erlaubt das Anlegen bei laufendem Faden."
   ],
   [
    "Luftkanal",
    "Ø mm",
    "Bohrung, durch die die Druckluft in den Fadenkanal tritt. Ihr Durchmesser legt Einsatzbereich und Verbrauch fest."
   ],
   [
    "Überdruck pe",
    "bar",
    "Druck über Umgebung an der Düse. Verwirbelung etwa 1,5 bis 6 bar, Migration 0,5 bis 2 bar."
   ],
   [
    "Verwirbelungspunkt",
    "Knoten",
    "Stelle, an der die Filamente verflochten sind. Gemessen als Anzahl pro Meter, dazu Gleichmässigkeit und Festigkeit."
   ],
   [
    "Präparation",
    "spin finish",
    "Öl-Wasser-Auftrag für Gleiten, Fadenschluss und Antistatik. Gleichmässige Verteilung ist die Aufgabe der Migrationsdüse."
   ],
   [
    "POY",
    "",
    "Pre-Oriented Yarn. Vororientiert, wird danach meist zu DTY texturiert."
   ],
   [
    "FDY",
    "",
    "Fully Drawn Yarn. In der Spinnlinie voll verstreckt und direkt weiterverarbeitbar."
   ],
   [
    "BCF / IDY",
    "",
    "Teppichgarn und technisches Garn. Grobe Titer, grössere Luftkanäle bis 4 mm."
   ],
   [
    "TopAir",
    "",
    "Bauart mit zusätzlichem Luftstrom von oben neben dem üblichen von unten, für gleichmässigere Verwirbelung."
   ]
  ],
  "sources": [
   "Heberlein Produktübersicht (heberlein.com): Fadenzahlen 1 bis 32, Teilungen 4 bis 12 mm, Düsentypen",
   "Heberlein Produktkatalog (heberlein.com): Druckbereiche, Fadenspannung, Luftverbrauchsformel",
   "Oerlikon Barmag WINGS (oerlikon.com): 12- und 24-fach Wickelkonzepte"
  ],
  "kanal": [
   {
    "k": 0.376,
    "d": "0.9",
    "t": "55"
   },
   {
    "k": 0.562,
    "d": "1.1",
    "t": "95"
   },
   {
    "k": 0.786,
    "d": "1.3",
    "t": "190"
   },
   {
    "k": 1.19,
    "d": "1.6",
    "t": "350"
   },
   {
    "k": 1.859,
    "d": "2.0",
    "t": "800"
   },
   {
    "k": 2.905,
    "d": "2.5",
    "t": "1200"
   }
  ]
 },
 "en": {
  "ui": {
   "eyebrow": "Basics · melt spinning POY / FDY",
   "h1": "Jets in filament spinning",
   "lead": "From the hole in the spinneret to the knot in the yarn: where each jet sits, what ends and pitch mean and what the compressed air in the yarn channel does to the filaments.",
   "note": "All figures are guide values. The animations show the principle, not a design.",
   "sources": "Sources of the figures",
   "clickHint": "Click a station in the list or in the picture - it is marked and explained.",
   "quench": "Quench air",
   "linkBack": "To filament yarn spinning",
   "linkBackHint": "The whole plant from chips to bobbin",
   "endsL": "Ends",
   "pitchL": "Pitch",
   "ends": "{n}-end",
   "rN": "Ends per position",
   "rT": "Yarn spacing",
   "rW": "Width over all ends, (n − 1) · t",
   "jetPack": "Jet pack",
   "pitchDim": "Pitch t = {t} mm",
   "bobbins": "{n} bobbins on the spindle",
   "bobbin1": "1 bobbin on the spindle",
   "packNote": "The slider steps follow a real range: jet packs for 1 to 32 ends and pitches from 4 to 12 mm. Not every combination exists for every jet type.",
   "endsP": [
    "Ends",
    "is the number of yarns running in parallel at one position and becoming bobbins on one winder spindle. One says 12-end or 24-end (German: 12-fach). The jet pack needs exactly as many yarn channels."
   ],
   "pitchP": [
    "Pitch",
    "is the distance from yarn centre to yarn centre in the jet pack, in millimetres. A small pitch means a compact pack and small deflection angles, but leaves less room for the air channel and the yarn guides."
   ],
   "jetType": "Jet type",
   "modeInt": "Intermingling",
   "modeMig": "Migration",
   "pressure": "Gauge pressure pe",
   "effectL": "Effect on the yarn",
   "effInt": [
    "few, soft knots",
    "medium knot density",
    "many, firm knots"
   ],
   "effMig": [
    "light mixing",
    "strong mixing, no knots"
   ],
   "crossCap": "Cross-section: looking along the yarn path. Dots = filaments, blue = air.",
   "sideCap": "Side view, schematic. Distances and knot shape are not to scale.",
   "channel": "Yarn channel",
   "air": "Compressed air",
   "parallel": "filaments parallel",
   "intOut": "open section and knot alternating",
   "migOut": "mixed, without knots",
   "run": "Yarn path →",
   "intJet": "Intermingling jet",
   "migJet": "Migration jet",
   "intP": [
    "Intermingling",
    "creates points with yarn cohesion. More pressure gives more and firmer knots, until the yarn is overstrained and the evenness suffers. Higher speed and higher yarn tension work against it: 0.1 to 0.25 cN/dtex after the jet are usual."
   ],
   "migP": [
    "Migration",
    "works with little pressure. The filaments only swap places in the bundle, the oil gets from the outside to the inside, the yarn runs more quietly. Knots are not wanted here."
   ],
   "formula": "q_vn = k · (pe + 1)   [m³/h per end, standard conditions DIN 1343]",
   "airChannel": "Air channel",
   "kanal": "Ø {d} mm · up to approx. {t} dtex",
   "rK": "Factor k",
   "rQ1": "Consumption per end",
   "rQn": "Consumption per position",
   "atEnds": "at {n}-end",
   "airNote": "Factors and count ranges are guide values from the Heberlein data sheet PolyJet-SP-3 Migra. For intermingling jets the same factors apply at the same channel diameter."
  },
  "scenes": [
   {
    "k": "Spinning line",
    "title": "The spinning line from top to bottom",
    "text": "On its way from the melt to the bobbin a yarn passes several jets. Only the first one forms it, all others work with oil or air."
   },
   {
    "k": "Ends & pitch",
    "title": "Ends and pitch",
    "text": "A spinning position never processes just one yarn. The air jets therefore sit side by side as a jet pack. Two numbers describe this pack."
   },
   {
    "k": "Yarn channel",
    "title": "What happens in the yarn channel",
    "text": "The air enters the channel across the yarn, hits the opposite side and splits into two counter-rotating vortices. The filaments are carried along and entangle. Before and after the jet the yarn stays open for a short length, in between sits the knot."
   },
   {
    "k": "Air consumption",
    "title": "Air channel, pressure and consumption",
    "text": "The diameter of the air channel is chosen by the yarn count: fine yarn, small bore. Consumption grows linearly with the absolute pressure, and it is needed for every end of the position."
   },
   {
    "k": "Terms",
    "title": "The terms at a glance",
    "text": "For looking up: the key words around jets in filament spinning."
   }
  ],
  "stations": [
   {
    "n": "Spinneret",
    "d": "The spin pump presses the polymer melt at high pressure through fine holes. Each hole gives one filament: 72 holes give an f72 yarn. The quench air cools the filaments until they are solid."
   },
   {
    "n": "Spin finish applicator (oiler)",
    "d": "Here the filaments come together to form the yarn and get the spin finish. At first the oil sits on one side, on the outside of the bundle."
   },
   {
    "n": "Migration jet",
    "d": "Little compressed air (0.5 to 2.0 bar) compacts the bundle slightly and drives the spin finish into the core of the yarn. No intermingling points are made."
   },
   {
    "n": "Godets",
    "d": "They pull the yarn off and set the tension. With POY the yarn stays pre-oriented, with FDY it is fully drawn between the godets."
   },
   {
    "n": "Intermingling jet",
    "d": "Compressed air (1.5 to 6.0 bar) hits the yarn across and entangles the filaments into knots at regular intervals. The yarn gets the cohesion it needs on the bobbin and in further processing."
   },
   {
    "n": "Winder",
    "d": "Winding at several thousand metres per minute. Each position makes as many bobbins as yarns run side by side. This number is the number of ends."
   }
  ],
  "gloss": [
   [
    "Ends",
    "Fachung",
    "Number of yarns per spinning position and winder, e.g. 12-end. Sets the number of yarn channels in the jet pack."
   ],
   [
    "Doubling",
    "Fachen",
    "Bringing two or more yarns together into one, often with an air jet. Not to be confused with the ends of a position."
   ],
   [
    "Pitch",
    "Teilung",
    "Distance from yarn centre to yarn centre in the jet pack, typically 4 to 12 mm."
   ],
   [
    "Yarn count",
    "dtex",
    "Fineness of the yarn: grams per 10 000 m. What counts is the count in the jet, not the final count."
   ],
   [
    "Number of filaments",
    "f",
    "Number of single filaments, equal to the number of holes of the spinneret. 167f48 means 167 dtex from 48 filaments."
   ],
   [
    "dpf",
    "dtex / f",
    "Count per filament. Below about 1 dpf one speaks of microfilaments. They intermingle more easily but are more sensitive."
   ],
   [
    "Jet pack",
    "Düsenpaket",
    "Block with all jets of a position, mostly ceramic, on a holder with the air connection."
   ],
   [
    "Yarn channel",
    "",
    "The space the yarn runs through and in which the air acts. A threading slot on the side allows threading while the yarn is running."
   ],
   [
    "Air channel",
    "Ø mm",
    "Bore through which the compressed air enters the yarn channel. Its diameter sets the field of use and the consumption."
   ],
   [
    "Gauge pressure pe",
    "bar",
    "Pressure above ambient at the jet. Intermingling about 1.5 to 6 bar, migration 0.5 to 2 bar."
   ],
   [
    "Intermingling point",
    "knot",
    "Place where the filaments are entangled. Measured as number per metre, plus evenness and strength."
   ],
   [
    "Spin finish",
    "Präparation",
    "Oil-water coating for gliding, yarn cohesion and antistatic. Spreading it evenly is the task of the migration jet."
   ],
   [
    "POY",
    "",
    "Pre-Oriented Yarn. Pre-oriented, mostly textured to DTY afterwards."
   ],
   [
    "FDY",
    "",
    "Fully Drawn Yarn. Fully drawn in the spinning line and ready for further processing."
   ],
   [
    "BCF / IDY",
    "",
    "Carpet yarn and industrial yarn. Coarse counts, larger air channels up to 4 mm."
   ],
   [
    "TopAir",
    "",
    "Design with an additional air stream from the top next to the usual one from below, for more even intermingling."
   ]
  ],
  "sources": [
   "Heberlein product overview (heberlein.com): 1 to 32 ends, pitches 4 to 12 mm, jet types",
   "Heberlein product catalogue (heberlein.com): pressure ranges, yarn tension, air consumption formula",
   "Oerlikon Barmag WINGS (oerlikon.com): 12- and 24-end winding concepts"
  ],
  "kanal": [
   {
    "k": 0.376,
    "d": "0.9",
    "t": "55"
   },
   {
    "k": 0.562,
    "d": "1.1",
    "t": "95"
   },
   {
    "k": 0.786,
    "d": "1.3",
    "t": "190"
   },
   {
    "k": 1.19,
    "d": "1.6",
    "t": "350"
   },
   {
    "k": 1.859,
    "d": "2.0",
    "t": "800"
   },
   {
    "k": 2.905,
    "d": "2.5",
    "t": "1200"
   }
  ]
 },
 "es": {
  "ui": {
   "eyebrow": "Curso básico · hilatura por fusión POY / FDY",
   "h1": "Toberas en la hilatura de filamento",
   "lead": "Del orificio de la hilera al nudo en el hilo: dónde está cada tobera, qué significan número de cabos y paso, y qué hace el aire comprimido en el canal del hilo con los filamentos.",
   "note": "Todos los datos son valores orientativos. Las animaciones muestran el principio, no un diseño.",
   "sources": "Fuentes de las cifras",
   "clickHint": "Haz clic en una estación de la lista o de la imagen: se marca y se explica.",
   "quench": "Soplado",
   "linkBack": "A la hilatura de filamento",
   "linkBackHint": "Toda la instalación, del granulado a la bobina",
   "endsL": "Cabos",
   "pitchL": "Paso",
   "ends": "{n} cabos",
   "rN": "Cabos por posición",
   "rT": "Distancia entre hilos",
   "rW": "Ancho sobre todos los cabos, (n − 1) · t",
   "jetPack": "Paquete de toberas",
   "pitchDim": "Paso t = {t} mm",
   "bobbins": "{n} bobinas en el husillo",
   "bobbin1": "1 bobina en el husillo",
   "packNote": "Los pasos de los reguladores siguen una gama real: paquetes de toberas para 1 a 32 cabos y pasos de 4 a 12 mm. No todas las combinaciones existen para cada tipo de tobera.",
   "endsP": [
    "Número de cabos",
    "es la cantidad de hilos que corren en paralelo en una posición y se convierten en bobinas en un husillo de la bobinadora. Se dice 12 o 24 cabos (en inglés 12-end). El paquete de toberas necesita exactamente tantos canales de hilo."
   ],
   "pitchP": [
    "El paso",
    "es la distancia de centro a centro de los hilos en el paquete de toberas, en milímetros. Un paso pequeño significa un paquete compacto y ángulos de desvío pequeños, pero deja menos espacio para el canal de aire y los guiahilos."
   ],
   "jetType": "Tipo de tobera",
   "modeInt": "Entrelazado",
   "modeMig": "Migración",
   "pressure": "Sobrepresión pe",
   "effectL": "Efecto en el hilo",
   "effInt": [
    "pocos nudos blandos",
    "densidad media de nudos",
    "muchos nudos firmes"
   ],
   "effMig": [
    "mezcla ligera",
    "mezcla fuerte, sin nudos"
   ],
   "crossCap": "Sección: vista en el sentido del hilo. Puntos = filamentos, azul = aire.",
   "sideCap": "Vista lateral, esquemática. Distancias y forma del nudo no están a escala.",
   "channel": "Canal del hilo",
   "air": "Aire comprimido",
   "parallel": "filamentos paralelos",
   "intOut": "zona abierta y nudo alternados",
   "migOut": "mezclado, sin nudos",
   "run": "Recorrido del hilo →",
   "intJet": "Tobera de entrelazado",
   "migJet": "Tobera de migración",
   "intP": [
    "El entrelazado",
    "crea puntos con cohesión del hilo. Más presión da más nudos y más firmes, hasta que el hilo se sobrecarga y la regularidad empeora. Más velocidad y más tensión del hilo actúan en contra: lo habitual son 0,1 a 0,25 cN/dtex después de la tobera."
   ],
   "migP": [
    "La migración",
    "trabaja con poca presión. Los filamentos solo cambian de sitio en el haz, el aceite pasa de fuera hacia dentro y el hilo corre más tranquilo. Aquí no se quieren nudos."
   ],
   "formula": "q_vn = k · (pe + 1)   [m³/h por cabo, condiciones normales DIN 1343]",
   "airChannel": "Canal de aire",
   "kanal": "Ø {d} mm · hasta aprox. {t} dtex",
   "rK": "Factor k",
   "rQ1": "Consumo por cabo",
   "rQn": "Consumo por posición",
   "atEnds": "con {n} cabos",
   "airNote": "Los factores y rangos de título son valores orientativos de la ficha técnica de Heberlein PolyJet-SP-3 Migra. Para toberas de entrelazado valen los mismos factores con el mismo diámetro de canal."
  },
  "scenes": [
   {
    "k": "Línea de hilatura",
    "title": "La línea de hilatura de arriba abajo",
    "text": "En su camino de la masa fundida a la bobina, un hilo pasa por varias toberas. Solo la primera le da forma; todas las demás trabajan con aceite o aire."
   },
   {
    "k": "Cabos y paso",
    "title": "Número de cabos y paso",
    "text": "Una posición de hilatura nunca procesa un solo hilo. Por eso las toberas de aire están una junto a otra en un paquete. Dos números describen este paquete."
   },
   {
    "k": "Canal del hilo",
    "title": "Qué pasa en el canal del hilo",
    "text": "El aire entra en el canal de forma transversal al hilo, choca con el lado opuesto y se divide en dos remolinos que giran en sentido contrario. Los filamentos son arrastrados y se entrelazan. Antes y después de la tobera el hilo queda abierto un tramo corto; entre medias está el nudo."
   },
   {
    "k": "Consumo de aire",
    "title": "Canal de aire, presión y consumo",
    "text": "El diámetro del canal de aire se elige según el título: hilo fino, orificio pequeño. El consumo crece de forma lineal con la presión absoluta y se produce para cada cabo de la posición."
   },
   {
    "k": "Términos",
    "title": "Los términos de un vistazo",
    "text": "Para consultar: las palabras clave sobre las toberas en la hilatura de filamento."
   }
  ],
  "stations": [
   {
    "n": "Hilera",
    "d": "La bomba de hilatura empuja la masa fundida a alta presión por orificios finos. Cada orificio da un filamento: 72 orificios dan un hilo f72. El soplado enfría los filamentos hasta que se solidifican."
   },
   {
    "n": "Aplicador de ensimaje (aceitador)",
    "d": "Aquí los filamentos se juntan para formar el hilo y reciben el ensimaje. Al principio el aceite queda en un lado, por fuera del haz."
   },
   {
    "n": "Tobera de migración",
    "d": "Poco aire comprimido (0,5 a 2,0 bar) compacta ligeramente el haz y lleva el ensimaje hasta el núcleo del hilo. No se forman puntos de entrelazado."
   },
   {
    "n": "Godets",
    "d": "Tiran del hilo y ajustan la tensión. En POY el hilo queda preorientado; en FDY se estira por completo entre los godets."
   },
   {
    "n": "Tobera de entrelazado",
    "d": "El aire comprimido (1,5 a 6,0 bar) incide transversalmente en el hilo y entrelaza los filamentos en nudos a intervalos regulares. El hilo obtiene la cohesión para la bobina y el proceso posterior."
   },
   {
    "n": "Bobinadora",
    "d": "Bobinado a varios miles de metros por minuto. En cada posición se forman tantas bobinas como hilos corren uno al lado del otro. Ese número es el número de cabos."
   }
  ],
  "gloss": [
   [
    "Número de cabos",
    "ends",
    "Hilos por posición de hilatura y bobinadora, p. ej. 12 cabos. Fija el número de canales de hilo del paquete de toberas."
   ],
   [
    "Doblado",
    "doubling",
    "Juntar dos o más hilos en uno, a menudo con una tobera de aire. No confundir con el número de cabos de la posición."
   ],
   [
    "Paso",
    "pitch",
    "Distancia de centro a centro de los hilos en el paquete de toberas, normalmente 4 a 12 mm."
   ],
   [
    "Título",
    "dtex",
    "Finura del hilo: gramos por 10 000 m. Cuenta el título en la tobera, no el título final."
   ],
   [
    "Número de filamentos",
    "f",
    "Cantidad de filamentos individuales, igual al número de orificios de la hilera. 167f48 significa 167 dtex de 48 filamentos."
   ],
   [
    "dpf",
    "dtex / f",
    "Título por filamento. Por debajo de aprox. 1 dpf se habla de microfilamentos. Se entrelazan con más facilidad, pero son más delicados."
   ],
   [
    "Paquete de toberas",
    "jet pack",
    "Bloque con todas las toberas de una posición, casi siempre de cerámica, sobre un soporte con la conexión de aire."
   ],
   [
    "Canal del hilo",
    "",
    "El espacio por el que pasa el hilo y en el que actúa el aire. Una ranura lateral permite enhebrar con el hilo en marcha."
   ],
   [
    "Canal de aire",
    "Ø mm",
    "Orificio por el que el aire comprimido entra en el canal del hilo. Su diámetro fija el campo de uso y el consumo."
   ],
   [
    "Sobrepresión pe",
    "bar",
    "Presión sobre la ambiente en la tobera. Entrelazado aprox. 1,5 a 6 bar, migración 0,5 a 2 bar."
   ],
   [
    "Punto de entrelazado",
    "nudo",
    "Lugar en el que los filamentos están entrelazados. Se mide como número por metro, además de regularidad y firmeza."
   ],
   [
    "Ensimaje",
    "spin finish",
    "Aplicación de aceite y agua para deslizamiento, cohesión y antiestática. Repartirlo de forma uniforme es la tarea de la tobera de migración."
   ],
   [
    "POY",
    "",
    "Pre-Oriented Yarn. Preorientado; después casi siempre se texturiza a DTY."
   ],
   [
    "FDY",
    "",
    "Fully Drawn Yarn. Totalmente estirado en la línea de hilatura y listo para el proceso posterior."
   ],
   [
    "BCF / IDY",
    "",
    "Hilo de alfombra e hilo técnico. Títulos gruesos, canales de aire mayores, hasta 4 mm."
   ],
   [
    "TopAir",
    "",
    "Diseño con un flujo de aire adicional desde arriba, junto al habitual desde abajo, para un entrelazado más uniforme."
   ]
  ],
  "sources": [
   "Resumen de productos Heberlein (heberlein.com): 1 a 32 cabos, pasos de 4 a 12 mm, tipos de tobera",
   "Catálogo de productos Heberlein (heberlein.com): rangos de presión, tensión del hilo, fórmula de consumo",
   "Oerlikon Barmag WINGS (oerlikon.com): conceptos de bobinado de 12 y 24 cabos"
  ],
  "kanal": [
   {
    "k": 0.376,
    "d": "0.9",
    "t": "55"
   },
   {
    "k": 0.562,
    "d": "1.1",
    "t": "95"
   },
   {
    "k": 0.786,
    "d": "1.3",
    "t": "190"
   },
   {
    "k": 1.19,
    "d": "1.6",
    "t": "350"
   },
   {
    "k": 1.859,
    "d": "2.0",
    "t": "800"
   },
   {
    "k": 2.905,
    "d": "2.5",
    "t": "1200"
   }
  ]
 },
 "zh": {
  "ui": {
   "eyebrow": "基础课程 · 熔融纺丝 POY / FDY",
   "h1": "长丝纺丝中的喷嘴",
   "lead": "从喷丝板上的小孔到丝线上的网络点：各种喷嘴装在哪里、头数和间距是什么意思，以及纱道中的压缩空气如何作用于单丝。",
   "note": "所有数据均为参考值。动画仅展示原理，并非具体结构。",
   "sources": "数据来源",
   "clickHint": "点击列表或图中的某个工位——它会被标出并加以说明。",
   "quench": "侧吹风",
   "linkBack": "前往长丝纺丝",
   "linkBackHint": "从切片到卷装的整条生产线",
   "endsL": "头数",
   "pitchL": "间距",
   "ends": "{n} 头",
   "rN": "每个纺位的丝线数",
   "rT": "丝线间距",
   "rW": "所有丝线的总宽度，(n − 1) · t",
   "jetPack": "喷嘴组",
   "pitchDim": "间距 t = {t} mm",
   "bobbins": "锭轴上 {n} 个卷装",
   "bobbin1": "锭轴上 1 个卷装",
   "packNote": "滑块的档位对应真实的产品系列：喷嘴组适用于 1 至 32 头，间距 4 至 12 mm。并非每种喷嘴都有所有组合。",
   "endsP": [
    "头数",
    "是指一个纺位上并行运行、在同一卷绕锭轴上形成卷装的丝线数量，例如 12 头或 24 头（英文 12-end）。喷嘴组需要同样数量的纱道。"
   ],
   "pitchP": [
    "间距",
    "是喷嘴组中相邻丝线中心之间的距离，单位为毫米。间距小意味着喷嘴组紧凑、导向角小，但留给气道和导丝器的空间也更少。"
   ],
   "jetType": "喷嘴类型",
   "modeInt": "网络",
   "modeMig": "迁移",
   "pressure": "表压 pe",
   "effectL": "对丝线的作用",
   "effInt": [
    "网络点少而软",
    "网络点密度中等",
    "网络点多而牢"
   ],
   "effMig": [
    "轻度混合",
    "强烈混合，无网络点"
   ],
   "crossCap": "截面：沿丝线运行方向观察。圆点 = 单丝，蓝色 = 空气。",
   "sideCap": "侧视图，示意。间距和网络点形状不按比例。",
   "channel": "纱道",
   "air": "压缩空气",
   "parallel": "单丝平行",
   "intOut": "开放段与网络点交替",
   "migOut": "已混合，无网络点",
   "run": "丝线运行 →",
   "intJet": "网络喷嘴",
   "migJet": "迁移喷嘴",
   "intP": [
    "网络",
    "形成使丝线抱合的网络点。压力越高，网络点越多越牢，直到丝线负荷过大、均匀性下降。更高的速度和更高的丝线张力会起反作用：喷嘴后通常为 0.1 至 0.25 cN/dtex。"
   ],
   "migP": [
    "迁移",
    "使用较低压力。单丝只在丝束中交换位置，油剂从外层进入内部，丝线运行更平稳。此处不希望形成网络点。"
   ],
   "formula": "q_vn = k · (pe + 1)   [每根丝 m³/h，标准状态 DIN 1343]",
   "airChannel": "气道",
   "kanal": "Ø {d} mm · 约至 {t} dtex",
   "rK": "系数 k",
   "rQ1": "每根丝耗气量",
   "rQn": "每个纺位耗气量",
   "atEnds": "{n} 头时",
   "airNote": "系数和纤度范围为 Heberlein 数据表 PolyJet-SP-3 Migra 中的参考值。网络喷嘴在相同气道直径下适用相同系数。"
  },
  "scenes": [
   {
    "k": "纺丝线",
    "title": "从上到下看纺丝线",
    "text": "丝线从熔体到卷装的途中要经过多个喷嘴。只有第一个喷嘴使其成形，其余都是用油剂或空气工作。"
   },
   {
    "k": "头数与间距",
    "title": "头数与间距",
    "text": "一个纺位从不只加工一根丝线。因此空气喷嘴以喷嘴组的形式并排安装。有两个数字描述这个喷嘴组。"
   },
   {
    "k": "纱道",
    "title": "纱道中发生了什么",
    "text": "空气横向于丝线进入纱道，撞到对面后分成两个反向旋转的涡流。单丝被带动并相互缠结。喷嘴前后丝线会短暂保持开放，中间形成网络点。"
   },
   {
    "k": "耗气量",
    "title": "气道、压力与耗气量",
    "text": "气道直径按纤度选择：细丝用小孔。耗气量随绝对压力线性增加，而且每一头丝线都要消耗。"
   },
   {
    "k": "术语",
    "title": "术语一览",
    "text": "供查阅：长丝纺丝中与喷嘴相关的重要术语。"
   }
  ],
  "stations": [
   {
    "n": "喷丝板",
    "d": "计量泵将聚合物熔体以高压压过细孔。每个孔形成一根单丝：72 个孔得到 f72 的丝线。侧吹风使单丝冷却固化。"
   },
   {
    "n": "上油嘴（油剂喷嘴）",
    "d": "单丝在这里汇集成丝线并上纺丝油剂。此时油剂首先只附着在丝束外侧的一边。"
   },
   {
    "n": "迁移喷嘴",
    "d": "少量压缩空气（0.5 至 2.0 bar）轻微压实丝束，并把油剂推入丝线内部。不形成网络点。"
   },
   {
    "n": "导丝辊",
    "d": "导丝辊牵引丝线并调节张力。POY 保持预取向，FDY 则在导丝辊之间被充分拉伸。"
   },
   {
    "n": "网络喷嘴",
    "d": "压缩空气（1.5 至 6.0 bar）横向冲击丝线，按规律间隔将单丝缠结成网络点。丝线由此获得卷装和后道加工所需的抱合性。"
   },
   {
    "n": "卷绕机",
    "d": "以每分钟数千米的速度卷绕。每个纺位形成的卷装数等于并排运行的丝线数，这个数就是头数。"
   }
  ],
  "gloss": [
   [
    "头数",
    "ends",
    "每个纺位和卷绕机上的丝线数，例如 12 头。决定喷嘴组中纱道的数量。"
   ],
   [
    "并丝",
    "doubling",
    "将两根或多根丝线合为一根，常用空气喷嘴。不要与纺位的头数混淆。"
   ],
   [
    "间距",
    "pitch",
    "喷嘴组中相邻丝线中心之间的距离，通常为 4 至 12 mm。"
   ],
   [
    "纤度",
    "dtex",
    "丝线细度：每 10 000 m 的克数。起决定作用的是喷嘴处的纤度，而不是最终纤度。"
   ],
   [
    "单丝数",
    "f",
    "单根丝的数量，等于喷丝板的孔数。167f48 表示由 48 根单丝组成的 167 dtex 丝线。"
   ],
   [
    "dpf",
    "dtex / f",
    "单丝纤度。低于约 1 dpf 称为超细纤维。它更容易网络，但也更敏感。"
   ],
   [
    "喷嘴组",
    "jet pack",
    "包含一个纺位全部喷嘴的模块，多为陶瓷，装在带气源接口的支架上。"
   ],
   [
    "纱道",
    "",
    "丝线通过、空气在其中起作用的空间。侧面的引丝槽可在丝线运行时穿丝。"
   ],
   [
    "气道",
    "Ø mm",
    "压缩空气进入纱道的孔。其直径决定适用范围和耗气量。"
   ],
   [
    "表压 pe",
    "bar",
    "喷嘴处高于环境的压力。网络约 1.5 至 6 bar，迁移 0.5 至 2 bar。"
   ],
   [
    "网络点",
    "knot",
    "单丝相互缠结的位置。以每米个数计量，另看均匀性和牢度。"
   ],
   [
    "纺丝油剂",
    "spin finish",
    "油水涂层，用于润滑、抱合和抗静电。迁移喷嘴的任务是使其均匀分布。"
   ],
   [
    "POY",
    "",
    "预取向丝（Pre-Oriented Yarn）。之后大多加弹成 DTY。"
   ],
   [
    "FDY",
    "",
    "全拉伸丝（Fully Drawn Yarn）。在纺丝线上充分拉伸，可直接用于后道加工。"
   ],
   [
    "BCF / IDY",
    "",
    "地毯丝和工业丝。纤度粗，气道更大，可达 4 mm。"
   ],
   [
    "TopAir",
    "",
    "除常规的下方进气外还从上方额外进气的结构，使网络更均匀。"
   ]
  ],
  "sources": [
   "Heberlein 产品概览（heberlein.com）：1 至 32 头，间距 4 至 12 mm，喷嘴类型",
   "Heberlein 产品目录（heberlein.com）：压力范围、丝线张力、耗气量公式",
   "Oerlikon Barmag WINGS（oerlikon.com）：12 头和 24 头卷绕方案"
  ],
  "kanal": [
   {
    "k": 0.376,
    "d": "0.9",
    "t": "55"
   },
   {
    "k": 0.562,
    "d": "1.1",
    "t": "95"
   },
   {
    "k": 0.786,
    "d": "1.3",
    "t": "190"
   },
   {
    "k": 1.19,
    "d": "1.6",
    "t": "350"
   },
   {
    "k": 1.859,
    "d": "2.0",
    "t": "800"
   },
   {
    "k": 2.905,
    "d": "2.5",
    "t": "1200"
   }
  ]
 }
};
