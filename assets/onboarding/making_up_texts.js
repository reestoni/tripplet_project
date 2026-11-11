window.TEXTS = {
 "de": {
  "ui": {
   "eyebrow": "Knowledge Base · Konfektion",
   "h1": "Konfektion: vom Stoff zum Produkt",
   "lead": "Aus der Stoffbahn wird ein Hemd, eine Jacke oder eine Plane. Acht Szenen zeigen das Legen, das Schnittbild und seinen Verschnitt, die Zuschnittverfahren, wie der Doppelsteppstich entsteht, die wichtigsten Sticharten, das Abdichten von Nähten, die Schweissverfahren für technische Textilien und drei Produktbeispiele.",
   "note": "Schematische Darstellung. Ausnutzungsgrade, Fadenverbrauch, Geschwindigkeiten und Lagenhöhen sind typische Richtwerte aus Fachliteratur, Herstellerangaben und Praxisberichten; sie hängen stark von Material und Modell ab.",
   "pause": "⏸ Pause",
   "play": "▶ Abspielen",
   "sl": {
    "plies": "Lagen",
    "sizes": "Grössen",
    "cut": "Verfahren",
    "spm": "Drehzahl",
    "st": "Stichtyp",
    "seal": "Naht",
    "weld": "Verfahren",
    "prod": "Produkt"
   },
   "lkL": "Weiter in der Knowledge Base",
   "open": "Modul öffnen"
  },
  "scenes": [
   {
    "k": "Legen",
    "title": "Stoff in Lagen ausbreiten",
    "text": "Vor dem Zuschnitt wird der Stoff auf dem Zuschneidetisch in vielen Lagen übereinander gelegt, meist mit einer Legemaschine, die hin und her fährt. Die Lagen müssen spannungsfrei, bündig und in der richtigen Richtung liegen, Farbabweichungen werden sortiert und Stofffehler entfernt. So lassen sich viele Teile in einem Schnitt herstellen. Mit dem Regler die Anzahl Lagen ändern.",
    "facts": [
     [
      "Ziel",
      "viele Teile in einem Schnitt"
     ],
     [
      "Anforderungen",
      "spannungsfrei, bündig, richtig orientiert"
     ],
     [
      "Lagenhöhe",
      "CNC-Cutter ~6–9 cm komprimiert"
     ],
     [
      "Verlust",
      "Lagenenden ~1–3 %"
     ]
    ]
   },
   {
    "k": "Schnittbild",
    "title": "Teile möglichst dicht verschachteln",
    "text": "Das Schnittbild legt fest, wie die Schnittteile auf der Stoffbahn angeordnet werden. Der Ausnutzungsgrad ist die Fläche der Teile geteilt durch die Fläche des Schnittbilds. Mehrere Grössen in einem Schnittbild, gut gemischt aus kleinen und grossen, füllen die Lücken besser. Dazu kommen Verluste an Breite, Lagenenden und beim Schneiden. Mit dem Regler die Anzahl Grössen ändern.",
    "facts": [
     [
      "Ausnutzung",
      "Teilefläche ÷ Schnittbildfläche"
     ],
     [
      "Branchenmittel",
      "~78–85 %"
     ],
     [
      "Mehr Grössen",
      "meist bessere Ausnutzung"
     ],
     [
      "Software",
      "automatisches Verschachteln (Nesting)"
     ]
    ]
   },
   {
    "k": "Zuschnitt",
    "title": "Messer, CNC-Cutter, Laser, Ultraschall",
    "text": "Kleine Betriebe schneiden mit dem Stossmesser von Hand entlang des Schnittbilds. In der Serie fährt ein CNC-Cutter mit Schwingmesser die Konturen ab, während Vakuum den Lagenstapel zusammenpresst und festhält. Laser und Ultraschall schneiden meist einlagig und verschmelzen dabei die Kanten synthetischer Stoffe. Mit dem Regler das Verfahren wählen.",
    "facts": [
     [
      "Stossmesser",
      "von Hand, hoher Lagenstapel"
     ],
     [
      "CNC-Schwingmesser",
      "Vakuum, ~6–9 cm komprimiert"
     ],
     [
      "Laser",
      "einlagig, Kante versiegelt"
     ],
     [
      "Ultraschall",
      "schneidet und versiegelt"
     ]
    ]
   },
   {
    "k": "Steppstich",
    "title": "Wie Ober- und Unterfaden sich verschlingen",
    "text": "Beim Doppelsteppstich (Stichtyp 301) sticht die Nadel den Oberfaden durch den Stoff. Beim Hochgehen bildet sich eine Schlinge, die der umlaufende Greifer fängt und um die Spulenkapsel mit dem Unterfaden herumführt. Der Fadenhebel zieht die Schlinge wieder hoch, die Verschlingung liegt im Stoff. Der Greifer dreht doppelt so schnell wie die Nadel arbeitet. Mit dem Regler die Stichzahl ändern.",
    "facts": [
     [
      "Stichtyp",
      "301, Ober- und Unterfaden"
     ],
     [
      "Greifer",
      "2 Umdrehungen pro Stich"
     ],
     [
      "Industrie",
      "~4000–5000 Stiche/min"
     ],
     [
      "Greifer max.",
      "bis ~12 000 min⁻¹"
     ]
    ]
   },
   {
    "k": "Sticharten",
    "title": "301, 401, 504, 516, 406",
    "text": "Die ISO 4915 teilt Sticharten in Klassen ein: 300 Steppstiche, 400 Kettenstiche, 500 Überwendlichstiche, 600 Überdeckstiche. Sie unterscheiden sich in Festigkeit, Dehnbarkeit, Kantenversäuberung und Fadenverbrauch. Dehnbare Maschenware braucht dehnbare Stiche, Gewebe wird meist mit Stepp- oder Kettenstich genäht. Mit dem Regler den Stichtyp wählen.",
    "facts": [
     [
      "300",
      "Steppstiche, z. B. 301"
     ],
     [
      "400",
      "Kettenstiche, z. B. 401, 406"
     ],
     [
      "500",
      "Überwendlich, z. B. 504, 516"
     ],
     [
      "Verbrauch",
      "301: 2,5 cm Faden je cm Naht"
     ]
    ]
   },
   {
    "k": "Nahtabdichtung",
    "title": "Nadellöcher dicht machen",
    "text": "Jede Nadel hinterlässt Löcher, durch die Wasser dringen kann. Bei wasserdichter Bekleidung wird die genähte Naht deshalb innen mit einem Nahtband abgedeckt: Heissluft aktiviert den Schmelzkleber des Bandes, eine Walze drückt es an. Alternativ wird ganz ohne Nadel geschweisst. Mit dem Regler die Nahtart wählen.",
    "facts": [
     [
      "Problem",
      "Nadellöcher lassen Wasser durch"
     ],
     [
      "Nahtband",
      "Schmelzkleber, mit Heissluft aktiviert"
     ],
     [
      "Schweissen",
      "keine Löcher, thermoplastisch"
     ],
     [
      "Einsatz",
      "Membranjacken, Zelte, Schutzbekleidung"
     ]
    ]
   },
   {
    "k": "Schweissen",
    "title": "Heissluft, Heizkeil, Hochfrequenz, Ultraschall",
    "text": "Thermoplastisch beschichtete oder synthetische Stoffe lassen sich ohne Faden verbinden: Die Kunststoffschicht wird aufgeschmolzen und unter Druck zusammengefügt. Die Wärme kommt aus heisser Luft, einem beheizten Keil, einem Hochfrequenzfeld oder aus Ultraschallschwingungen. So entstehen wasser- und luftdichte Nähte für Planen, Boote oder Zelte. Mit dem Regler das Verfahren wählen.",
    "facts": [
     [
      "Heissluft",
      "schnell, ohne Werkzeug, auch 3D"
     ],
     [
      "Heizkeil",
      "Folien, lange gerade Nähte"
     ],
     [
      "Hochfrequenz",
      "27,12 MHz, polare Kunststoffe wie PVC"
     ],
     [
      "Ultraschall",
      "Schwingungen erzeugen Reibungswärme"
     ]
    ]
   },
   {
    "k": "Produkt",
    "title": "Hemd, Jacke, Plane",
    "text": "Welche Schritte ein Produkt durchläuft, hängt vom Material ab. Ein Hemd aus Gewebe wird in hohen Lagen geschnitten und genäht. Eine Membranjacke wird genäht und die Nähte werden getapet. Eine LKW-Plane aus PVC-beschichtetem Gewebe wird geschweisst statt genäht. Mit dem Regler das Produkt wählen.",
    "facts": [
     [
      "Hemd",
      "Legen, CNC-Zuschnitt, Nähen"
     ],
     [
      "Membranjacke",
      "Nähen und Nähte tapen"
     ],
     [
      "LKW-Plane",
      "Bahnen schweissen, Ösen setzen"
     ],
     [
      "Kette",
      "Faser bis Produkt"
     ]
    ]
   }
  ],
  "cv": {
   "pliesN": "{n} Lagen",
   "sizesN": "{n} Grössen",
   "spmU": "Stiche/min",
   "le": {
    "table": "Zuschneidetisch",
    "spreader": "Legemaschine",
    "lay": "Lagenhöhe ≈ {h} cm",
    "example": "Beispiel: 0,8 mm pro Lage",
    "reqT": "Anforderungen ans Legen",
    "req": [
     "Farbschattierungen sortieren",
     "Lagen bündig ausrichten",
     "ohne Spannung legen",
     "Stofffehler herausnehmen"
    ],
    "cnc": "Automatische Zuschneidesysteme schneiden je nach Modell etwa 6 bis 9 cm komprimierten Lagenstapel. Das Vakuum presst den Stapel zusammen und hält ihn beim Schneiden fest.",
    "tooHigh": "Der Stapel ist höher, als ein typischer CNC-Cutter schneiden kann: aufteilen oder mit dem Stossmesser schneiden."
   },
   "sb": {
    "marker": "Schnittbild mit {n} Grössen (schematisch)",
    "eff": "{e} %",
    "effL": "Ausnutzungsgrad (Beispiel)",
    "formula": "Teilefläche ÷ Schnittbildfläche",
    "avg": "Branchenmittel etwa 78–85 %, mit KI-gestütztem Verschachteln bis ~88–94 % (Herstellerangabe).",
    "lossT": "Weitere Verluste (Richtwerte)",
    "loss": [
     [
      "Schnittbild (1 − Ausnutzung)",
      15,
      25
     ],
     [
      "Breite nicht genutzt",
      2,
      8
     ],
     [
      "Lagenenden",
      1,
      3
     ],
     [
      "Legen: Spannung, Schrumpf",
      0.5,
      2
     ],
     [
      "Schneiden",
      0.5,
      1.5
     ]
    ]
   },
   "cu": {
    "vac": "Vakuum presst den Lagenstapel zusammen",
    "pliesL": "LAGEN",
    "edgeL": "SCHNITTKANTE",
    "m": [
     {
      "n": "Stossmesser",
      "p": "viele Lagen, von Hand geführt",
      "e": "offen, kann ausfransen",
      "d": "Ein senkrecht schwingendes Messer wird von Hand entlang des aufgezeichneten Schnittbilds geführt. Flexibel und günstig, die Genauigkeit hängt von der Person ab."
     },
     {
      "n": "CNC-Schwingmesser",
      "p": "Stapel bis ~6–9 cm komprimiert",
      "e": "sauber, mechanisch",
      "d": "Der Schneidkopf fährt die Konturen aus der CAD-Datei ab, ein schnell schwingendes Messer schneidet den unter Vakuum gepressten Stapel. Hohe Genauigkeit und Leistung in der Serie."
     },
     {
      "n": "Laser",
      "p": "meist einlagig",
      "e": "versiegelt bei Synthetics",
      "d": "Ein CO₂-Laser schmilzt bzw. verdampft das Material entlang der Kontur. Kanten synthetischer Stoffe schmelzen zu und fransen nicht; Naturfasern können verfärben, es entsteht Rauch."
     },
     {
      "n": "Ultraschall",
      "p": "meist einlagig",
      "e": "verschweisst",
      "d": "Ein schwingendes Messer erzeugt Reibungswärme und verschweisst die Schnittkante thermoplastischer Stoffe. Gut für technische Textilien und Bänder."
     }
    ]
   },
   "ls": {
    "fabric": "zwei Stofflagen",
    "bobbin": "Spule mit Unterfaden",
    "hook": "Greifer",
    "lock": "Verschlingung liegt im Stoff",
    "takeup": "Fadenhebel",
    "calc": "Drehzahl und Nähgeschwindigkeit",
    "spmL": "NADEL",
    "hookL": "GREIFER (2×)",
    "slL": "STICHLÄNGE",
    "vL": "NÄHGESCHWINDIGKEIT",
    "note": "Nähgeschwindigkeit = Stiche pro Minute × Stichlänge. Rechenbeispiel mit 3 mm Stichlänge; in der Praxis bremsen Anfang, Ende und Ecken.",
    "nowCap": "Greifer fängt die Schlinge und führt sie um die Spule",
    "nowSet": "Fadenhebel zieht den Stich fest"
   },
   "sa": {
    "top": "Oberseite",
    "bottom": "Unterseite",
    "edge": "Stoffkante",
    "consT": "Fadenverbrauch (cm Faden je cm Naht)",
    "useL": "EINSATZ",
    "propL": "EIGENSCHAFTEN",
    "s": [
     {
      "n": "301 Doppelsteppstich",
      "t": "1 Nadelfaden + 1 Unterfaden",
      "r": 2.5,
      "use": "Der häufigste Stich: Hemden, Hosen, Steppnähte auf Gewebe, technische Textilien.",
      "prop": "Sehr sicher, sieht beidseitig gleich aus, wenig Fadenverbrauch; wenig dehnbar, Unterfaden muss nachgefüllt werden."
     },
     {
      "n": "401 Doppelkettenstich",
      "t": "1 Nadelfaden + 1 Greiferfaden",
      "r": 5.5,
      "use": "Längsnähte an Jeans, Steppnähte, Bündchen.",
      "prop": "Dehnbarer und produktiver als 301, weniger Kräuseln; braucht mehr Faden."
     },
     {
      "n": "504 Überwendlich",
      "t": "1 Nadel- + 2 Greiferfäden",
      "r": 14,
      "use": "Maschenware: T-Shirt-Seitennähte, Kanten versäubern.",
      "prop": "Sehr dehnbar, umschlingt die Kante; hoher Fadenverbrauch."
     },
     {
      "n": "516 Sicherheitsstich",
      "t": "401 + 504 zugleich",
      "r": 19.5,
      "use": "Seitennähte und Schrittnähte an Geweben.",
      "prop": "Der Kettenstich trägt die Last, der Überwendlichstich versäubert die Kante."
     },
     {
      "n": "406 Überdeckstich",
      "t": "2 Nadelfäden + 1 Greiferfaden",
      "r": 18,
      "use": "Säume an T-Shirts, Ärmel und Saum von Maschenware.",
      "prop": "Parallele Nadelreihen oben, Greiferfaden unten; dehnbar und flach."
     }
    ]
   },
   "se": {
    "holes": "Nadellöcher",
    "fused": "verschmolzen",
    "tape": "Nahtband mit Schmelzkleber",
    "leak": "Wasser dringt durch die Nadellöcher",
    "dry": "Naht bleibt dicht",
    "hotair": "Heissluft + Andruckwalze",
    "note": "Für wasserdichte Bekleidung reicht ein dichter Stoff nicht: Erst getapte oder geschweisste Nähte machen das Produkt dicht. Das Nahtband muss zum Laminat passen, damit es auch nach vielen Wäschen hält.",
    "m": [
     {
      "n": "Genäht",
      "d": "Klassische Naht mit Nadel und Faden. Fest und günstig, aber jedes Nadelloch ist eine undichte Stelle."
     },
     {
      "n": "Genäht und getapt",
      "d": "Nach dem Nähen wird innen ein Nahtband mit Schmelzkleber aufgelegt. Heissluft aktiviert den Kleber, eine Walze drückt das Band an; beim Abkühlen dichtet es die Nadellöcher ab."
     },
     {
      "n": "Geschweisst",
      "d": "Die Lagen werden ohne Nadel thermisch verbunden. Es gibt keine Löcher; das Material muss aber thermoplastisch sein oder eine solche Schicht tragen."
     }
    ]
   },
   "we": {
    "nozzle": "Heissluftdüse",
    "wedge": "Heizkeil",
    "electrode": "Elektrode",
    "sono": "Sonotrode",
    "seam": "Schweissnaht",
    "forL": "GEEIGNET FÜR",
    "proL": "VORTEILE",
    "conL": "NACHTEILE",
    "m": [
     {
      "n": "Heissluft",
      "d": "Eine Düse bläst heisse Luft zwischen die beiden Lagen, Walzen pressen sie gleich danach zusammen.",
      "for": "Markisen, LKW-Planen, Schlauchboote; Kurven und 3D-Formen",
      "pro": "Schnell, ohne Werkzeuge, Start und Stopp unproblematisch.",
      "con": "Benötigt Abluft; Parameter je nach Material einstellen."
     },
     {
      "n": "Heizkeil",
      "d": "Ein beheizter Metallkeil gleitet zwischen die Lagen und schmilzt die Beschichtung, Walzen pressen nach.",
      "for": "Folien und dicke Stoffe, lange gerade Nähte, Behälter",
      "pro": "Präzise Wärme an der Nahtstelle, leiser Betrieb.",
      "con": "Keil speichert Wärme im Stillstand und kann am Nahtanfang überhitzen."
     },
     {
      "n": "Hochfrequenz",
      "d": "Ein elektromagnetisches Wechselfeld (27,12 MHz) erwärmt polare Kunststoffe von innen, Elektroden pressen die Lagen zusammen.",
      "for": "PVC und PU, Markisen und Planen; in Europa verbreitet",
      "pro": "Sehr feste Nähte, auch geformte Elektroden möglich.",
      "con": "Elektrodenlänge begrenzt, Anlagen teuer; nur für polare Kunststoffe."
     },
     {
      "n": "Ultraschall",
      "d": "Eine Sonotrode schwingt mit hoher Frequenz und erzeugt im Kontaktbereich Reibungswärme, die die Lagen verschweisst.",
      "for": "Synthetics, Vliese, Filter, Schutzbekleidung",
      "pro": "Keine Fremdwärme, schnell; dasselbe Prinzip kann auch schneiden.",
      "con": "Nur für thermoplastische Materialien geeignet; dicke Lagen schwierig."
     }
    ]
   },
   "pr": {
    "keyT": "Worauf es ankommt",
    "p": [
     {
      "n": "Hemd",
      "mat": "Baumwollgewebe",
      "steps": [
       [
        "Legen",
        "viele Lagen, Karos ausrichten"
       ],
       [
        "CNC-Zuschnitt",
        "Schwingmesser"
       ],
       [
        "Nähen",
        "Doppelsteppstich 301"
       ],
       [
        "Knöpfe",
        "Knopflöcher, Knöpfe"
       ],
       [
        "Bügeln",
        "Finish, Falten"
       ]
      ],
      "key": [
       "Ausnutzung des Schnittbilds bestimmt den Stoffverbrauch",
       "Steppstich ergibt saubere, beidseitig gleiche Nähte",
       "Gewebe ist formstabil und lässt sich in hohen Lagen schneiden"
      ]
     },
     {
      "n": "Membranjacke",
      "mat": "3-Lagen-Laminat",
      "steps": [
       [
        "Zuschnitt",
        "wenige Lagen, präzise"
       ],
       [
        "Nähen",
        "301, schmale Nahtzugabe"
       ],
       [
        "Tapen",
        "Nahtband mit Heissluft"
       ],
       [
        "Reissverschluss",
        "wasserdicht verklebt"
       ],
       [
        "Prüfen",
        "Dichtheit"
       ]
      ],
      "key": [
       "Jede Naht wird abgedichtet, sonst dringt Wasser durch die Nadellöcher",
       "Nahtband und Laminat müssen zueinander passen",
       "Weniger Nähte bedeuten weniger Risiko"
      ]
     },
     {
      "n": "LKW-Plane",
      "mat": "PVC-beschichtetes Polyestergewebe",
      "steps": [
       [
        "Zuschnitt",
        "Bahnen nach Mass"
       ],
       [
        "Schweissen",
        "Hochfrequenz oder Heissluft"
       ],
       [
        "Säume",
        "verstärkt, geschweisst"
       ],
       [
        "Ösen",
        "Ösen und Keder setzen"
       ],
       [
        "Bedrucken",
        "Logo, Werbung"
       ]
      ],
      "key": [
       "Geschweisste Nähte sind dicht und oft fester als genähte",
       "PVC als polarer Kunststoff eignet sich für Hochfrequenz",
       "Grosse Formate brauchen lange Schweissanlagen"
      ]
     }
    ]
   }
  },
  "quiz": [
   {
    "q": "Warum wird Stoff vor dem Zuschnitt in Lagen gelegt?",
    "a": [
     "Um viele Teile in einem Schnitt herzustellen",
     "Damit er trocknet",
     "Um ihn zu färben",
     "Damit er schrumpft"
    ],
    "c": 0,
    "e": "Mit einem Lagenstapel entstehen in einem Schnitt viele gleiche Teile.",
    "sc": 0
   },
   {
    "q": "Wie berechnet sich der Ausnutzungsgrad eines Schnittbilds?",
    "a": [
     "Teilefläche ÷ Schnittbildfläche",
     "Lagen × Breite",
     "Stofflänge ÷ Teilezahl",
     "Gewicht ÷ Fläche"
    ],
    "c": 0,
    "e": "Er ist der Anteil der Schnittbildfläche, der tatsächlich in Teilen landet.",
    "sc": 1
   },
   {
    "q": "Was hält beim CNC-Cutter den Lagenstapel fest?",
    "a": [
     "Vakuum",
     "Nadeln",
     "Klebstoff",
     "Gewichte"
    ],
    "c": 0,
    "e": "Das Vakuum presst den Stapel zusammen und fixiert ihn während des Schneidens.",
    "sc": 2
   },
   {
    "q": "Wie oft dreht sich der Greifer beim Doppelsteppstich pro Stich?",
    "a": [
     "Einmal",
     "Zweimal",
     "Dreimal",
     "Gar nicht"
    ],
    "c": 1,
    "e": "Der umlaufende Greifer dreht doppelt so schnell wie der Nadeltakt.",
    "sc": 3
   },
   {
    "q": "Welcher Stich eignet sich für dehnbare T-Shirt-Seitennähte?",
    "a": [
     "301 Doppelsteppstich",
     "504 Überwendlich",
     "101 Einfadenkettenstich",
     "Handstich"
    ],
    "c": 1,
    "e": "Der Überwendlichstich 504 ist sehr dehnbar und versäubert zugleich die Kante.",
    "sc": 4
   },
   {
    "q": "Warum werden Nähte an Membranjacken getapt?",
    "a": [
     "Um die Nadellöcher abzudichten",
     "Für die Optik",
     "Damit sie dehnbar werden",
     "Um Faden zu sparen"
    ],
    "c": 0,
    "e": "Durch die Nadellöcher dringt Wasser; das Nahtband mit Schmelzkleber dichtet sie ab.",
    "sc": 5
   },
   {
    "q": "Welches Schweissverfahren nutzt ein Wechselfeld von 27,12 MHz?",
    "a": [
     "Heizkeil",
     "Heissluft",
     "Hochfrequenz",
     "Ultraschall"
    ],
    "c": 2,
    "e": "Beim Hochfrequenzschweissen erwärmt ein elektromagnetisches Feld polare Kunststoffe wie PVC.",
    "sc": 6
   },
   {
    "q": "Wie werden die Bahnen einer PVC-LKW-Plane typisch verbunden?",
    "a": [
     "Geschweisst",
     "Nur genäht",
     "Gestrickt",
     "Gewebt"
    ],
    "c": 0,
    "e": "PVC-beschichtete Planen werden meist mit Hochfrequenz oder Heissluft geschweisst.",
    "sc": 7
   }
  ],
  "links": [
   [
    "Bindungslehre",
    "Leinwand, Köper, Atlas: wie das Gewebe aufgebaut ist, das hier zugeschnitten und genäht wird."
   ],
   [
    "Rundstricken",
    "Maschenware für T-Shirts und Sportbekleidung, die dehnbare Stiche braucht."
   ],
   [
    "Chemiefasern",
    "Polyester, Polyamid und Co.: die thermoplastischen Fasern, die sich schweissen und lasern lassen."
   ],
   [
    "Mechanische Textilausrüstung",
    "Sanforisieren, Kalandern und Co.: der Stoff vor dem Zuschnitt masshaltig gemacht."
   ],
   [
    "Textildruck",
    "Muster auf der Stoffbahn, bevor sie in die Konfektion geht."
   ]
  ]
 },
 "en": {
  "ui": {
   "eyebrow": "Knowledge Base · Making-up",
   "h1": "Making-up: from fabric to product",
   "lead": "The fabric roll becomes a shirt, a jacket or a tarpaulin. Eight scenes show spreading, the marker and its waste, cutting methods, how the lockstitch forms, the main stitch types, seam sealing, welding methods for technical textiles and three product examples.",
   "note": "Schematic illustration. Utilisation rates, thread consumption, speeds and lay heights are typical values from technical literature, manufacturer data and practice reports; they depend strongly on material and style.",
   "pause": "⏸ Pause",
   "play": "▶ Play",
   "sl": {
    "plies": "Plies",
    "sizes": "Sizes",
    "cut": "Method",
    "spm": "Speed",
    "st": "Stitch",
    "seal": "Seam",
    "weld": "Method",
    "prod": "Product"
   },
   "lkL": "More in the Knowledge Base",
   "open": "Open module"
  },
  "scenes": [
   {
    "k": "Spreading",
    "title": "Laying fabric in plies",
    "text": "Before cutting, the fabric is laid in many plies on the cutting table, usually by a spreading machine travelling back and forth. Plies must lie tension-free, aligned and in the right direction; shade variations are sorted and fabric faults removed. This way many pieces are made in one cut. Use the slider to change the number of plies.",
    "facts": [
     [
      "Goal",
      "many pieces in one cut"
     ],
     [
      "Requirements",
      "tension-free, aligned, correctly oriented"
     ],
     [
      "Lay height",
      "CNC cutter ~6–9 cm compressed"
     ],
     [
      "Loss",
      "ply ends ~1–3%"
     ]
    ]
   },
   {
    "k": "Marker",
    "title": "Nesting pieces as tightly as possible",
    "text": "The marker defines how the pattern pieces are arranged on the fabric. Marker efficiency is the area of the pieces divided by the marker area. Several sizes in one marker, well mixed small and large, fill the gaps better. On top come losses at the width, ply ends and in cutting. Use the slider to change the number of sizes.",
    "facts": [
     [
      "Efficiency",
      "piece area ÷ marker area"
     ],
     [
      "Industry average",
      "~78–85%"
     ],
     [
      "More sizes",
      "usually better efficiency"
     ],
     [
      "Software",
      "automatic nesting"
     ]
    ]
   },
   {
    "k": "Cutting",
    "title": "Knife, CNC cutter, laser, ultrasonic",
    "text": "Small workshops cut by hand with a straight knife along the marker. In series production a CNC cutter with an oscillating knife follows the contours while vacuum compresses and holds the lay. Laser and ultrasonic usually cut single plies and fuse the edges of synthetic fabrics. Use the slider to choose the method.",
    "facts": [
     [
      "Straight knife",
      "by hand, high lay"
     ],
     [
      "CNC oscillating knife",
      "vacuum, ~6–9 cm compressed"
     ],
     [
      "Laser",
      "single ply, sealed edge"
     ],
     [
      "Ultrasonic",
      "cuts and seals"
     ]
    ]
   },
   {
    "k": "Lockstitch",
    "title": "How needle and bobbin threads interlock",
    "text": "In the lockstitch (stitch type 301) the needle carries the upper thread through the fabric. As it rises, a loop forms, which the rotary hook catches and carries around the bobbin case with the lower thread. The take-up lever pulls the loop back up and the interlacing sits inside the fabric. The hook rotates twice per needle cycle. Use the slider to change the stitch rate.",
    "facts": [
     [
      "Stitch type",
      "301, needle and bobbin thread"
     ],
     [
      "Hook",
      "2 revolutions per stitch"
     ],
     [
      "Industry",
      "~4,000–5,000 stitches/min"
     ],
     [
      "Hook max.",
      "up to ~12,000 rpm"
     ]
    ]
   },
   {
    "k": "Stitch types",
    "title": "301, 401, 504, 516, 406",
    "text": "ISO 4915 groups stitches into classes: 300 lockstitches, 400 chainstitches, 500 overedge stitches, 600 covering stitches. They differ in strength, stretch, edge finishing and thread consumption. Stretchy knits need stretchy stitches; wovens are usually sewn with lockstitch or chainstitch. Use the slider to choose the stitch type.",
    "facts": [
     [
      "300",
      "lockstitches, e.g. 301"
     ],
     [
      "400",
      "chainstitches, e.g. 401, 406"
     ],
     [
      "500",
      "overedge, e.g. 504, 516"
     ],
     [
      "Consumption",
      "301: 2.5 cm thread per cm seam"
     ]
    ]
   },
   {
    "k": "Seam sealing",
    "title": "Sealing the needle holes",
    "text": "Every needle leaves holes through which water can pass. For waterproof garments the sewn seam is therefore covered inside with seam tape: hot air activates the tape's hot-melt adhesive and a roller presses it on. Alternatively the seam is welded without a needle at all. Use the slider to choose the seam type.",
    "facts": [
     [
      "Problem",
      "needle holes let water through"
     ],
     [
      "Seam tape",
      "hot-melt, activated by hot air"
     ],
     [
      "Welding",
      "no holes, thermoplastic"
     ],
     [
      "Use",
      "membrane jackets, tents, protective wear"
     ]
    ]
   },
   {
    "k": "Welding",
    "title": "Hot air, hot wedge, high frequency, ultrasonic",
    "text": "Thermoplastic-coated or synthetic fabrics can be joined without thread: the polymer layer is melted and pressed together. The heat comes from hot air, a heated wedge, a high-frequency field or ultrasonic vibration. This creates water- and airtight seams for tarpaulins, boats or tents. Use the slider to choose the method.",
    "facts": [
     [
      "Hot air",
      "fast, no tooling, also 3D"
     ],
     [
      "Hot wedge",
      "films, long straight seams"
     ],
     [
      "High frequency",
      "27.12 MHz, polar plastics like PVC"
     ],
     [
      "Ultrasonic",
      "vibration creates frictional heat"
     ]
    ]
   },
   {
    "k": "Product",
    "title": "Shirt, jacket, tarpaulin",
    "text": "Which steps a product goes through depends on the material. A woven shirt is cut in high lays and sewn. A membrane jacket is sewn and its seams taped. A truck tarpaulin of PVC-coated fabric is welded instead of sewn. Use the slider to choose the product.",
    "facts": [
     [
      "Shirt",
      "spreading, CNC cutting, sewing"
     ],
     [
      "Membrane jacket",
      "sewing and seam taping"
     ],
     [
      "Truck tarpaulin",
      "welding panels, setting eyelets"
     ],
     [
      "Chain",
      "fibre to product"
     ]
    ]
   }
  ],
  "cv": {
   "pliesN": "{n} plies",
   "sizesN": "{n} sizes",
   "spmU": "stitches/min",
   "le": {
    "table": "Cutting table",
    "spreader": "Spreading machine",
    "lay": "Lay height ≈ {h} cm",
    "example": "Example: 0.8 mm per ply",
    "reqT": "Spreading requirements",
    "req": [
     "Sort shades",
     "Align plies",
     "Lay without tension",
     "Remove fabric faults"
    ],
    "cnc": "Depending on the model, automatic cutting systems cut a compressed lay of about 6 to 9 cm. The vacuum compresses the lay and holds it during cutting.",
    "tooHigh": "The lay is higher than a typical CNC cutter can cut: split it or cut with a straight knife."
   },
   "sb": {
    "marker": "Marker with {n} sizes (schematic)",
    "eff": "{e}%",
    "effL": "Marker efficiency (example)",
    "formula": "piece area ÷ marker area",
    "avg": "Industry average about 78–85%, with AI-assisted nesting up to ~88–94% (vendor claim).",
    "lossT": "Further losses (guide values)",
    "loss": [
     [
      "Marker (1 − efficiency)",
      15,
      25
     ],
     [
      "Unused width",
      2,
      8
     ],
     [
      "Ply ends",
      1,
      3
     ],
     [
      "Spreading: tension, shrinkage",
      0.5,
      2
     ],
     [
      "Cutting",
      0.5,
      1.5
     ]
    ]
   },
   "cu": {
    "vac": "Vacuum compresses the lay",
    "pliesL": "PLIES",
    "edgeL": "CUT EDGE",
    "m": [
     {
      "n": "Straight knife",
      "p": "many plies, guided by hand",
      "e": "open, may fray",
      "d": "A vertically reciprocating knife is guided by hand along the drawn marker. Flexible and cheap; accuracy depends on the operator."
     },
     {
      "n": "CNC oscillating knife",
      "p": "lay up to ~6–9 cm compressed",
      "e": "clean, mechanical",
      "d": "The cutting head follows the contours from the CAD file; a fast-oscillating knife cuts the vacuum-compressed lay. High accuracy and output in series production."
     },
     {
      "n": "Laser",
      "p": "mostly single ply",
      "e": "sealed on synthetics",
      "d": "A CO₂ laser melts or vaporises the material along the contour. Edges of synthetics fuse and do not fray; natural fibres may discolour, and smoke is produced."
     },
     {
      "n": "Ultrasonic",
      "p": "mostly single ply",
      "e": "welded",
      "d": "A vibrating blade generates frictional heat and welds the cut edge of thermoplastic fabrics. Good for technical textiles and tapes."
     }
    ]
   },
   "ls": {
    "fabric": "two fabric plies",
    "bobbin": "Bobbin with lower thread",
    "hook": "Hook",
    "lock": "Interlacing sits inside the fabric",
    "takeup": "Take-up lever",
    "calc": "Speed and sewing rate",
    "spmL": "NEEDLE",
    "hookL": "HOOK (2×)",
    "slL": "STITCH LENGTH",
    "vL": "SEWING SPEED",
    "note": "Sewing speed = stitches per minute × stitch length. Example with 3 mm stitch length; in practice starts, ends and corners slow it down.",
    "nowCap": "Hook catches the loop and carries it around the bobbin",
    "nowSet": "Take-up lever sets the stitch"
   },
   "sa": {
    "top": "Top",
    "bottom": "Bottom",
    "edge": "Fabric edge",
    "consT": "Thread consumption (cm thread per cm seam)",
    "useL": "USE",
    "propL": "PROPERTIES",
    "s": [
     {
      "n": "301 lockstitch",
      "t": "1 needle thread + 1 bobbin thread",
      "r": 2.5,
      "use": "The most common stitch: shirts, trousers, topstitching on wovens, technical textiles.",
      "prop": "Very secure, same on both sides, low thread use; little stretch, bobbin must be refilled."
     },
     {
      "n": "401 chainstitch",
      "t": "1 needle thread + 1 looper thread",
      "r": 5.5,
      "use": "Long seams on jeans, topstitching, waistbands.",
      "prop": "More stretch and productivity than 301, less pucker; uses more thread."
     },
     {
      "n": "504 overedge",
      "t": "1 needle + 2 looper threads",
      "r": 14,
      "use": "Knits: T-shirt side seams, edge neatening.",
      "prop": "Very stretchy, wraps the edge; high thread consumption."
     },
     {
      "n": "516 safety stitch",
      "t": "401 + 504 together",
      "r": 19.5,
      "use": "Side seams and inseams on wovens.",
      "prop": "The chainstitch carries the load, the overedge neatens the edge."
     },
     {
      "n": "406 coverstitch",
      "t": "2 needle threads + 1 looper thread",
      "r": 18,
      "use": "T-shirt hems, sleeve and bottom hems of knits.",
      "prop": "Parallel needle rows on top, looper thread below; stretchy and flat."
     }
    ]
   },
   "se": {
    "holes": "Needle holes",
    "fused": "fused",
    "tape": "Seam tape with hot-melt",
    "leak": "Water penetrates through the needle holes",
    "dry": "Seam stays tight",
    "hotair": "Hot air + pressure roller",
    "note": "For waterproof garments a tight fabric is not enough: only taped or welded seams make the product waterproof. The seam tape must suit the laminate so it holds even after many washes.",
    "m": [
     {
      "n": "Sewn",
      "d": "Classic seam with needle and thread. Strong and economical, but every needle hole is a leak."
     },
     {
      "n": "Sewn and taped",
      "d": "After sewing, a seam tape with hot-melt is applied inside. Hot air activates the adhesive, a roller presses the tape on; on cooling it seals the needle holes."
     },
     {
      "n": "Welded",
      "d": "The plies are joined thermally without a needle. There are no holes, but the material must be thermoplastic or carry such a layer."
     }
    ]
   },
   "we": {
    "nozzle": "Hot-air nozzle",
    "wedge": "Hot wedge",
    "electrode": "Electrode",
    "sono": "Sonotrode",
    "seam": "Weld seam",
    "forL": "SUITED FOR",
    "proL": "ADVANTAGES",
    "conL": "DRAWBACKS",
    "m": [
     {
      "n": "Hot air",
      "d": "A nozzle blows hot air between the two plies; rollers press them together immediately after.",
      "for": "Awnings, truck tarpaulins, inflatable boats; curves and 3D shapes",
      "pro": "Fast, no tooling, frequent starts and stops are no problem.",
      "con": "Needs extraction; parameters must suit the material."
     },
     {
      "n": "Hot wedge",
      "d": "A heated metal wedge slides between the plies and melts the coating; rollers press after.",
      "for": "Films and thick fabrics, long straight seams, containers",
      "pro": "Precise heat at the seam, quiet operation.",
      "con": "Wedge stores heat when idle and can overheat at the start of a seam."
     },
     {
      "n": "High frequency",
      "d": "An alternating electromagnetic field (27.12 MHz) heats polar plastics from inside; electrodes press the plies together.",
      "for": "PVC and PU, awnings and tarpaulins; common in Europe",
      "pro": "Very strong seams, shaped electrodes possible.",
      "con": "Electrode length limited, expensive equipment; polar plastics only."
     },
     {
      "n": "Ultrasonic",
      "d": "A sonotrode vibrates at high frequency and creates frictional heat in the contact zone that welds the plies.",
      "for": "Synthetics, nonwovens, filters, protective wear",
      "pro": "No external heat, fast; the same principle can also cut.",
      "con": "Only for thermoplastic materials; thick plies are difficult."
     }
    ]
   },
   "pr": {
    "keyT": "What matters",
    "p": [
     {
      "n": "Shirt",
      "mat": "Cotton woven fabric",
      "steps": [
       [
        "Spreading",
        "many plies, match checks"
       ],
       [
        "CNC cutting",
        "oscillating knife"
       ],
       [
        "Sewing",
        "lockstitch 301"
       ],
       [
        "Buttons",
        "buttonholes, buttons"
       ],
       [
        "Pressing",
        "finish, folding"
       ]
      ],
      "key": [
       "Marker efficiency determines fabric consumption",
       "Lockstitch gives clean seams that look the same on both sides",
       "Woven fabric is stable and can be cut in high lays"
      ]
     },
     {
      "n": "Membrane jacket",
      "mat": "3-layer laminate",
      "steps": [
       [
        "Cutting",
        "few plies, precise"
       ],
       [
        "Sewing",
        "301, narrow seam allowance"
       ],
       [
        "Taping",
        "seam tape with hot air"
       ],
       [
        "Zip",
        "waterproof, bonded"
       ],
       [
        "Testing",
        "waterproofness"
       ]
      ],
      "key": [
       "Every seam is sealed, otherwise water enters through the needle holes",
       "Seam tape and laminate must be compatible",
       "Fewer seams mean less risk"
      ]
     },
     {
      "n": "Truck tarpaulin",
      "mat": "PVC-coated polyester fabric",
      "steps": [
       [
        "Cutting",
        "panels to size"
       ],
       [
        "Welding",
        "high frequency or hot air"
       ],
       [
        "Hems",
        "reinforced, welded"
       ],
       [
        "Eyelets",
        "eyelets and keders"
       ],
       [
        "Printing",
        "logo, advertising"
       ]
      ],
      "key": [
       "Welded seams are tight and often stronger than sewn ones",
       "PVC, a polar plastic, suits high-frequency welding",
       "Large formats need long welding lines"
      ]
     }
    ]
   }
  },
  "quiz": [
   {
    "q": "Why is fabric spread in plies before cutting?",
    "a": [
     "To make many pieces in one cut",
     "So it dries",
     "To dye it",
     "So it shrinks"
    ],
    "c": 0,
    "e": "A lay of plies produces many identical pieces in one cut.",
    "sc": 0
   },
   {
    "q": "How is marker efficiency calculated?",
    "a": [
     "Piece area ÷ marker area",
     "Plies × width",
     "Fabric length ÷ number of pieces",
     "Weight ÷ area"
    ],
    "c": 0,
    "e": "It is the share of the marker area that actually ends up in pieces.",
    "sc": 1
   },
   {
    "q": "What holds the lay in place on a CNC cutter?",
    "a": [
     "Vacuum",
     "Pins",
     "Adhesive",
     "Weights"
    ],
    "c": 0,
    "e": "The vacuum compresses the lay and fixes it during cutting.",
    "sc": 2
   },
   {
    "q": "How many times does the hook rotate per lockstitch?",
    "a": [
     "Once",
     "Twice",
     "Three times",
     "Not at all"
    ],
    "c": 1,
    "e": "The rotary hook turns twice as fast as the needle cycle.",
    "sc": 3
   },
   {
    "q": "Which stitch suits stretchy T-shirt side seams?",
    "a": [
     "301 lockstitch",
     "504 overedge",
     "101 single-thread chainstitch",
     "Hand stitch"
    ],
    "c": 1,
    "e": "The 504 overedge stitch is very stretchy and neatens the edge at the same time.",
    "sc": 4
   },
   {
    "q": "Why are seams on membrane jackets taped?",
    "a": [
     "To seal the needle holes",
     "For looks",
     "To make them stretchy",
     "To save thread"
    ],
    "c": 0,
    "e": "Water enters through needle holes; hot-melt seam tape seals them.",
    "sc": 5
   },
   {
    "q": "Which welding method uses a 27.12 MHz field?",
    "a": [
     "Hot wedge",
     "Hot air",
     "High frequency",
     "Ultrasonic"
    ],
    "c": 2,
    "e": "In high-frequency welding an electromagnetic field heats polar plastics such as PVC.",
    "sc": 6
   },
   {
    "q": "How are the panels of a PVC truck tarpaulin typically joined?",
    "a": [
     "Welded",
     "Sewn only",
     "Knitted",
     "Woven"
    ],
    "c": 0,
    "e": "PVC-coated tarpaulins are usually welded by high frequency or hot air.",
    "sc": 7
   }
  ],
  "links": [
   [
    "Weave structures",
    "Plain, twill, satin: how the woven fabric that is cut and sewn here is built."
   ],
   [
    "Circular knitting",
    "Knitted fabric for T-shirts and sportswear, which needs stretchable stitches."
   ],
   [
    "Man-made fibres",
    "Polyester, polyamide and more: the thermoplastic fibres that can be welded and laser cut."
   ],
   [
    "Mechanical finishing",
    "Sanforizing, calendering and more: making the fabric dimensionally stable before cutting."
   ],
   [
    "Textile printing",
    "Patterns on the fabric web before it goes to making-up."
   ]
  ]
 },
 "es": {
  "ui": {
   "eyebrow": "Knowledge Base · Confección",
   "h1": "Confección: del tejido al producto",
   "lead": "La pieza de tejido se convierte en una camisa, una chaqueta o una lona. Ocho escenas muestran el extendido, la marcada y su desperdicio, los métodos de corte, cómo se forma la puntada de pespunte, los tipos de puntada principales, el sellado de costuras, los métodos de soldadura para textiles técnicos y tres ejemplos de producto.",
   "note": "Representación esquemática. Aprovechamientos, consumo de hilo, velocidades y alturas de colchón son valores típicos de la literatura técnica, fabricantes e informes de práctica; dependen mucho del material y del modelo.",
   "pause": "⏸ Pausa",
   "play": "▶ Reproducir",
   "sl": {
    "plies": "Capas",
    "sizes": "Tallas",
    "cut": "Método",
    "spm": "Velocidad",
    "st": "Puntada",
    "seal": "Costura",
    "weld": "Método",
    "prod": "Producto"
   },
   "lkL": "Más en la Knowledge Base",
   "open": "Abrir módulo"
  },
  "scenes": [
   {
    "k": "Extendido",
    "title": "Extender el tejido en capas",
    "text": "Antes del corte, el tejido se extiende en muchas capas sobre la mesa de corte, casi siempre con una extendedora que va y viene. Las capas deben quedar sin tensión, alineadas y en la dirección correcta; se separan los tonos y se eliminan defectos. Así se cortan muchas piezas a la vez. Cambia el número de capas con el control.",
    "facts": [
     [
      "Objetivo",
      "muchas piezas en un corte"
     ],
     [
      "Requisitos",
      "sin tensión, alineadas, bien orientadas"
     ],
     [
      "Altura",
      "cortadora CNC ~6–9 cm comprimido"
     ],
     [
      "Pérdida",
      "extremos de capa ~1–3 %"
     ]
    ]
   },
   {
    "k": "Marcada",
    "title": "Encajar las piezas lo más juntas posible",
    "text": "La marcada define cómo se disponen los patrones sobre el tejido. El aprovechamiento es el área de las piezas dividida por el área de la marcada. Varias tallas en una marcada, bien mezcladas entre pequeñas y grandes, llenan mejor los huecos. Se añaden pérdidas de ancho, extremos de capa y corte. Cambia el número de tallas con el control.",
    "facts": [
     [
      "Aprovechamiento",
      "área de piezas ÷ área de marcada"
     ],
     [
      "Media del sector",
      "~78–85 %"
     ],
     [
      "Más tallas",
      "normalmente mejor aprovechamiento"
     ],
     [
      "Software",
      "encaje automático (nesting)"
     ]
    ]
   },
   {
    "k": "Corte",
    "title": "Cuchilla, cortadora CNC, láser, ultrasonido",
    "text": "Los talleres pequeños cortan a mano con una cortadora de cuchilla vertical siguiendo la marcada. En serie, una cortadora CNC con cuchilla oscilante sigue los contornos mientras el vacío comprime y sujeta el colchón. El láser y el ultrasonido cortan casi siempre una sola capa y sellan los bordes de los sintéticos. Elige el método con el control.",
    "facts": [
     [
      "Cuchilla vertical",
      "a mano, colchón alto"
     ],
     [
      "CNC oscilante",
      "vacío, ~6–9 cm comprimido"
     ],
     [
      "Láser",
      "una capa, borde sellado"
     ],
     [
      "Ultrasonido",
      "corta y sella"
     ]
    ]
   },
   {
    "k": "Pespunte",
    "title": "Cómo se entrelazan hilo superior e inferior",
    "text": "En el pespunte (tipo 301) la aguja lleva el hilo superior a través del tejido. Al subir se forma un bucle que el garfio rotativo atrapa y lleva alrededor de la cápsula con el hilo inferior. El tirahilos sube el bucle y el entrelazado queda dentro del tejido. El garfio gira dos veces por ciclo de aguja. Cambia la velocidad con el control.",
    "facts": [
     [
      "Puntada",
      "301, hilo de aguja y de bobina"
     ],
     [
      "Garfio",
      "2 vueltas por puntada"
     ],
     [
      "Industria",
      "~4000–5000 puntadas/min"
     ],
     [
      "Garfio máx.",
      "hasta ~12 000 rpm"
     ]
    ]
   },
   {
    "k": "Puntadas",
    "title": "301, 401, 504, 516, 406",
    "text": "La ISO 4915 agrupa las puntadas en clases: 300 pespuntes, 400 cadenetas, 500 sobrehilados, 600 recubridoras. Difieren en resistencia, elasticidad, remate del borde y consumo de hilo. El punto elástico necesita puntadas elásticas; el tejido plano suele coserse con pespunte o cadeneta. Elige el tipo con el control.",
    "facts": [
     [
      "300",
      "pespuntes, p. ej. 301"
     ],
     [
      "400",
      "cadenetas, p. ej. 401, 406"
     ],
     [
      "500",
      "sobrehilado, p. ej. 504, 516"
     ],
     [
      "Consumo",
      "301: 2,5 cm de hilo por cm"
     ]
    ]
   },
   {
    "k": "Sellado",
    "title": "Sellar los agujeros de aguja",
    "text": "Cada aguja deja agujeros por los que puede pasar el agua. En la ropa impermeable, la costura cosida se cubre por dentro con cinta: el aire caliente activa el adhesivo termofusible y un rodillo la presiona. También se puede soldar sin aguja. Elige el tipo de costura con el control.",
    "facts": [
     [
      "Problema",
      "los agujeros dejan pasar agua"
     ],
     [
      "Cinta",
      "termofusible, activada por aire caliente"
     ],
     [
      "Soldadura",
      "sin agujeros, termoplástico"
     ],
     [
      "Uso",
      "chaquetas con membrana, tiendas, ropa de protección"
     ]
    ]
   },
   {
    "k": "Soldadura",
    "title": "Aire caliente, cuña, alta frecuencia, ultrasonido",
    "text": "Los tejidos recubiertos termoplásticos o sintéticos se unen sin hilo: la capa de polímero se funde y se presiona. El calor procede de aire caliente, una cuña caliente, un campo de alta frecuencia o vibración ultrasónica. Así se obtienen costuras estancas para lonas, botes o tiendas. Elige el método con el control.",
    "facts": [
     [
      "Aire caliente",
      "rápido, sin útiles, también 3D"
     ],
     [
      "Cuña",
      "films, costuras rectas largas"
     ],
     [
      "Alta frecuencia",
      "27,12 MHz, plásticos polares como PVC"
     ],
     [
      "Ultrasonido",
      "la vibración genera calor por fricción"
     ]
    ]
   },
   {
    "k": "Producto",
    "title": "Camisa, chaqueta, lona",
    "text": "Los pasos dependen del material. Una camisa de tejido plano se corta en colchones altos y se cose. Una chaqueta con membrana se cose y se encintan las costuras. Una lona de camión de tejido recubierto de PVC se suelda en lugar de coserse. Elige el producto con el control.",
    "facts": [
     [
      "Camisa",
      "extendido, corte CNC, costura"
     ],
     [
      "Chaqueta",
      "costura y encintado"
     ],
     [
      "Lona",
      "soldar paños, poner ojales"
     ],
     [
      "Cadena",
      "de la fibra al producto"
     ]
    ]
   }
  ],
  "cv": {
   "pliesN": "{n} capas",
   "sizesN": "{n} tallas",
   "spmU": "puntadas/min",
   "le": {
    "table": "Mesa de corte",
    "spreader": "Extendedora",
    "lay": "Altura ≈ {h} cm",
    "example": "Ejemplo: 0,8 mm por capa",
    "reqT": "Requisitos del extendido",
    "req": [
     "Separar tonos",
     "Alinear las capas",
     "Extender sin tensión",
     "Eliminar defectos"
    ],
    "cnc": "Según el modelo, los sistemas automáticos cortan un colchón comprimido de unos 6 a 9 cm. El vacío comprime el colchón y lo sujeta durante el corte.",
    "tooHigh": "El colchón es más alto de lo que corta una CNC típica: dividirlo o cortar con cuchilla vertical."
   },
   "sb": {
    "marker": "Marcada con {n} tallas (esquemática)",
    "eff": "{e} %",
    "effL": "Aprovechamiento (ejemplo)",
    "formula": "área de piezas ÷ área de marcada",
    "avg": "Media del sector ~78–85 %; con encaje asistido por IA hasta ~88–94 % (dato de fabricante).",
    "lossT": "Otras pérdidas (orientativas)",
    "loss": [
     [
      "Marcada (1 − aprovechamiento)",
      15,
      25
     ],
     [
      "Ancho no usado",
      2,
      8
     ],
     [
      "Extremos de capa",
      1,
      3
     ],
     [
      "Extendido: tensión, encogimiento",
      0.5,
      2
     ],
     [
      "Corte",
      0.5,
      1.5
     ]
    ]
   },
   "cu": {
    "vac": "El vacío comprime el colchón",
    "pliesL": "CAPAS",
    "edgeL": "BORDE DE CORTE",
    "m": [
     {
      "n": "Cuchilla vertical",
      "p": "muchas capas, guiada a mano",
      "e": "abierto, puede deshilachar",
      "d": "Una cuchilla que sube y baja se guía a mano siguiendo la marcada. Flexible y barata; la precisión depende de la persona."
     },
     {
      "n": "CNC oscilante",
      "p": "colchón hasta ~6–9 cm comprimido",
      "e": "limpio, mecánico",
      "d": "El cabezal sigue los contornos del archivo CAD; una cuchilla oscilante corta el colchón comprimido por vacío. Alta precisión y rendimiento en serie."
     },
     {
      "n": "Láser",
      "p": "casi siempre una capa",
      "e": "sellado en sintéticos",
      "d": "Un láser de CO₂ funde o vaporiza el material siguiendo el contorno. Los bordes sintéticos se funden y no se deshilachan; las fibras naturales pueden amarillear y se produce humo."
     },
     {
      "n": "Ultrasonido",
      "p": "casi siempre una capa",
      "e": "soldado",
      "d": "Una cuchilla vibrante genera calor por fricción y suelda el borde de tejidos termoplásticos. Adecuado para textiles técnicos y cintas."
     }
    ]
   },
   "ls": {
    "fabric": "dos capas de tejido",
    "bobbin": "Bobina con hilo inferior",
    "hook": "Garfio",
    "lock": "El entrelazado queda dentro del tejido",
    "takeup": "Tirahilos",
    "calc": "Velocidad y avance de costura",
    "spmL": "AGUJA",
    "hookL": "GARFIO (2×)",
    "slL": "LARGO DE PUNTADA",
    "vL": "VELOCIDAD DE COSTURA",
    "note": "Velocidad = puntadas por minuto × largo de puntada. Ejemplo con 3 mm; en la práctica los inicios, finales y esquinas la reducen.",
    "nowCap": "El garfio atrapa el bucle y lo lleva alrededor de la bobina",
    "nowSet": "El tirahilos aprieta la puntada"
   },
   "sa": {
    "top": "Cara superior",
    "bottom": "Cara inferior",
    "edge": "Borde del tejido",
    "consT": "Consumo de hilo (cm de hilo por cm de costura)",
    "useL": "USO",
    "propL": "PROPIEDADES",
    "s": [
     {
      "n": "301 pespunte",
      "t": "1 hilo de aguja + 1 de bobina",
      "r": 2.5,
      "use": "La puntada más común: camisas, pantalones, pespuntes en tejido plano, textiles técnicos.",
      "prop": "Muy segura, igual por ambas caras, poco consumo; poco elástica, hay que reponer la bobina."
     },
     {
      "n": "401 cadeneta",
      "t": "1 hilo de aguja + 1 de áncora",
      "r": 5.5,
      "use": "Costuras largas en vaqueros, pespuntes, cinturillas.",
      "prop": "Más elástica y productiva que la 301, menos fruncido; consume más hilo."
     },
     {
      "n": "504 sobrehilado",
      "t": "1 hilo de aguja + 2 de áncora",
      "r": 14,
      "use": "Punto: costados de camisetas, remate de bordes.",
      "prop": "Muy elástica, envuelve el borde; alto consumo de hilo."
     },
     {
      "n": "516 puntada de seguridad",
      "t": "401 + 504 a la vez",
      "r": 19.5,
      "use": "Costados y entrepiernas en tejido plano.",
      "prop": "La cadeneta soporta la carga y el sobrehilado remata el borde."
     },
     {
      "n": "406 recubridora",
      "t": "2 hilos de aguja + 1 de áncora",
      "r": 18,
      "use": "Bajos de camisetas, mangas y bajos de punto.",
      "prop": "Filas paralelas arriba, hilo de áncora abajo; elástica y plana."
     }
    ]
   },
   "se": {
    "holes": "Agujeros de aguja",
    "fused": "fundido",
    "tape": "Cinta termofusible",
    "leak": "El agua entra por los agujeros",
    "dry": "La costura es estanca",
    "hotair": "Aire caliente + rodillo",
    "note": "En ropa impermeable no basta un tejido estanco: solo las costuras encintadas o soldadas hacen el producto impermeable. La cinta debe ser compatible con el laminado para resistir muchos lavados.",
    "m": [
     {
      "n": "Cosida",
      "d": "Costura clásica con aguja e hilo. Resistente y económica, pero cada agujero es una fuga."
     },
     {
      "n": "Cosida y encintada",
      "d": "Tras coser se aplica por dentro una cinta termofusible. El aire caliente activa el adhesivo, un rodillo la presiona y al enfriarse sella los agujeros."
     },
     {
      "n": "Soldada",
      "d": "Las capas se unen térmicamente sin aguja. No hay agujeros, pero el material debe ser termoplástico o llevar una capa así."
     }
    ]
   },
   "we": {
    "nozzle": "Boquilla de aire",
    "wedge": "Cuña caliente",
    "electrode": "Electrodo",
    "sono": "Sonotrodo",
    "seam": "Costura soldada",
    "forL": "ADECUADO PARA",
    "proL": "VENTAJAS",
    "conL": "INCONVENIENTES",
    "m": [
     {
      "n": "Aire caliente",
      "d": "Una boquilla sopla aire caliente entre las dos capas; unos rodillos las presionan justo después.",
      "for": "Toldos, lonas de camión, botes neumáticos; curvas y formas 3D",
      "pro": "Rápido, sin útiles, admite arranques y paradas frecuentes.",
      "con": "Requiere extracción; parámetros según el material."
     },
     {
      "n": "Cuña caliente",
      "d": "Una cuña metálica caliente se desliza entre las capas y funde el recubrimiento; los rodillos presionan.",
      "for": "Films y tejidos gruesos, costuras rectas largas, depósitos",
      "pro": "Calor preciso en la costura, funcionamiento silencioso.",
      "con": "La cuña acumula calor en reposo y puede sobrecalentar al inicio."
     },
     {
      "n": "Alta frecuencia",
      "d": "Un campo electromagnético alterno (27,12 MHz) calienta desde dentro los plásticos polares; los electrodos presionan las capas.",
      "for": "PVC y PU, toldos y lonas; extendido en Europa",
      "pro": "Costuras muy resistentes, electrodos con forma.",
      "con": "Longitud de electrodo limitada, equipos caros; solo plásticos polares."
     },
     {
      "n": "Ultrasonido",
      "d": "Un sonotrodo vibra a alta frecuencia y genera calor por fricción en la zona de contacto que suelda las capas.",
      "for": "Sintéticos, no tejidos, filtros, ropa de protección",
      "pro": "Sin calor externo, rápido; el mismo principio también corta.",
      "con": "Solo materiales termoplásticos; capas gruesas difíciles."
     }
    ]
   },
   "pr": {
    "keyT": "Lo importante",
    "p": [
     {
      "n": "Camisa",
      "mat": "Tejido plano de algodón",
      "steps": [
       [
        "Extendido",
        "muchas capas, casar cuadros"
       ],
       [
        "Corte CNC",
        "cuchilla oscilante"
       ],
       [
        "Costura",
        "pespunte 301"
       ],
       [
        "Botones",
        "ojales y botones"
       ],
       [
        "Planchado",
        "acabado, plegado"
       ]
      ],
      "key": [
       "El aprovechamiento de la marcada define el consumo de tejido",
       "El pespunte da costuras limpias iguales por ambas caras",
       "El tejido plano es estable y se corta en colchones altos"
      ]
     },
     {
      "n": "Chaqueta con membrana",
      "mat": "Laminado de 3 capas",
      "steps": [
       [
        "Corte",
        "pocas capas, preciso"
       ],
       [
        "Costura",
        "301, margen estrecho"
       ],
       [
        "Encintado",
        "cinta con aire caliente"
       ],
       [
        "Cremallera",
        "impermeable, pegada"
       ],
       [
        "Ensayo",
        "estanqueidad"
       ]
      ],
      "key": [
       "Cada costura se sella o el agua entra por los agujeros",
       "La cinta y el laminado deben ser compatibles",
       "Menos costuras, menos riesgo"
      ]
     },
     {
      "n": "Lona de camión",
      "mat": "Tejido de poliéster recubierto de PVC",
      "steps": [
       [
        "Corte",
        "paños a medida"
       ],
       [
        "Soldadura",
        "alta frecuencia o aire caliente"
       ],
       [
        "Dobladillos",
        "reforzados, soldados"
       ],
       [
        "Ojales",
        "ojales y vivos"
       ],
       [
        "Impresión",
        "logo, publicidad"
       ]
      ],
      "key": [
       "Las costuras soldadas son estancas y a menudo más fuertes que las cosidas",
       "El PVC, plástico polar, es apto para alta frecuencia",
       "Los formatos grandes requieren líneas de soldadura largas"
      ]
     }
    ]
   }
  },
  "quiz": [
   {
    "q": "¿Por qué se extiende el tejido en capas antes del corte?",
    "a": [
     "Para cortar muchas piezas a la vez",
     "Para secarlo",
     "Para teñirlo",
     "Para que encoja"
    ],
    "c": 0,
    "e": "Un colchón de capas produce muchas piezas iguales en un solo corte.",
    "sc": 0
   },
   {
    "q": "¿Cómo se calcula el aprovechamiento de una marcada?",
    "a": [
     "Área de piezas ÷ área de marcada",
     "Capas × ancho",
     "Largo ÷ número de piezas",
     "Peso ÷ área"
    ],
    "c": 0,
    "e": "Es la parte del área de la marcada que acaba en piezas.",
    "sc": 1
   },
   {
    "q": "¿Qué sujeta el colchón en una cortadora CNC?",
    "a": [
     "El vacío",
     "Alfileres",
     "Adhesivo",
     "Pesos"
    ],
    "c": 0,
    "e": "El vacío comprime el colchón y lo fija durante el corte.",
    "sc": 2
   },
   {
    "q": "¿Cuántas vueltas da el garfio por puntada de pespunte?",
    "a": [
     "Una",
     "Dos",
     "Tres",
     "Ninguna"
    ],
    "c": 1,
    "e": "El garfio rotativo gira el doble de rápido que el ciclo de aguja.",
    "sc": 3
   },
   {
    "q": "¿Qué puntada conviene para costados elásticos de camisetas?",
    "a": [
     "301 pespunte",
     "504 sobrehilado",
     "101 cadeneta de un hilo",
     "Puntada a mano"
    ],
    "c": 1,
    "e": "El sobrehilado 504 es muy elástico y remata el borde a la vez.",
    "sc": 4
   },
   {
    "q": "¿Por qué se encintan las costuras de chaquetas con membrana?",
    "a": [
     "Para sellar los agujeros de aguja",
     "Por estética",
     "Para hacerlas elásticas",
     "Para ahorrar hilo"
    ],
    "c": 0,
    "e": "El agua entra por los agujeros; la cinta termofusible los sella.",
    "sc": 5
   },
   {
    "q": "¿Qué método de soldadura usa un campo de 27,12 MHz?",
    "a": [
     "Cuña caliente",
     "Aire caliente",
     "Alta frecuencia",
     "Ultrasonido"
    ],
    "c": 2,
    "e": "En la soldadura de alta frecuencia un campo electromagnético calienta plásticos polares como el PVC.",
    "sc": 6
   },
   {
    "q": "¿Cómo se unen normalmente los paños de una lona de PVC?",
    "a": [
     "Soldados",
     "Solo cosidos",
     "Tejidos de punto",
     "Tejidos"
    ],
    "c": 0,
    "e": "Las lonas de PVC se sueldan normalmente por alta frecuencia o aire caliente.",
    "sc": 7
   }
  ],
  "links": [
   [
    "Ligamentos",
    "Tafetán, sarga, raso: cómo está construido el tejido que aquí se corta y se cose."
   ],
   [
    "Tejido circular",
    "Tejido de punto para camisetas y ropa deportiva, que necesita puntadas elásticas."
   ],
   [
    "Fibras químicas",
    "Poliéster, poliamida y más: las fibras termoplásticas que se pueden soldar y cortar con láser."
   ],
   [
    "Acabado mecánico",
    "Sanforizado, calandrado y más: el tejido estable en sus medidas antes del corte."
   ],
   [
    "Estampación textil",
    "Dibujos sobre la pieza de tejido antes de pasar a la confección."
   ]
  ]
 },
 "zh": {
  "ui": {
   "eyebrow": "知识库 · 成衣加工",
   "h1": "成衣加工：从面料到产品",
   "lead": "一卷面料变成衬衫、夹克或篷布。八个场景介绍铺布、排料图及其损耗、裁剪方法、锁式线迹的形成、主要线迹类型、接缝密封、产业用纺织品的焊接方法以及三个产品示例。",
   "note": "示意图。利用率、用线量、速度和铺布高度为技术文献、制造商资料和实践报告中的典型参考值，很大程度上取决于材料和款式。",
   "pause": "⏸ 暂停",
   "play": "▶ 播放",
   "sl": {
    "plies": "层数",
    "sizes": "尺码",
    "cut": "方法",
    "spm": "转速",
    "st": "线迹",
    "seal": "接缝",
    "weld": "方法",
    "prod": "产品"
   },
   "lkL": "Knowledge Base 中的相关内容",
   "open": "打开模块"
  },
  "scenes": [
   {
    "k": "铺布",
    "title": "把面料一层层铺开",
    "text": "裁剪前，面料在裁床上铺成多层，通常由往复运行的铺布机完成。各层须无张力、对齐、方向正确；要区分色差并剔除疵点。这样一刀可以裁出许多衣片。用滑块改变层数。",
    "facts": [
     [
      "目的",
      "一次裁出大量衣片"
     ],
     [
      "要求",
      "无张力、对齐、方向正确"
     ],
     [
      "铺布高度",
      "CNC 裁床压缩后约 6–9 cm"
     ],
     [
      "损耗",
      "布层两端约 1–3%"
     ]
    ]
   },
   {
    "k": "排料",
    "title": "让衣片尽量紧密排列",
    "text": "排料图规定衣片在面料上的排列方式。排料利用率等于衣片面积除以排料图面积。一张排料图包含多个尺码，大小搭配，能更好地填满空隙。此外还有幅宽、布层两端和裁剪的损耗。用滑块改变尺码数。",
    "facts": [
     [
      "利用率",
      "衣片面积 ÷ 排料面积"
     ],
     [
      "行业平均",
      "约 78–85%"
     ],
     [
      "尺码更多",
      "通常利用率更高"
     ],
     [
      "软件",
      "自动排料"
     ]
    ]
   },
   {
    "k": "裁剪",
    "title": "直刀、CNC 裁床、激光、超声波",
    "text": "小作坊用直刀电剪沿排料图手工裁剪。批量生产时，CNC 裁床的振动刀沿轮廓切割，同时真空压紧并固定布层。激光和超声波通常单层裁剪，并熔封合成面料的边缘。用滑块选择方法。",
    "facts": [
     [
      "直刀电剪",
      "手工，布层高"
     ],
     [
      "CNC 振动刀",
      "真空，压缩后约 6–9 cm"
     ],
     [
      "激光",
      "单层，边缘熔封"
     ],
     [
      "超声波",
      "裁切并封边"
     ]
    ]
   },
   {
    "k": "锁式线迹",
    "title": "面线和底线如何交锁",
    "text": "锁式线迹（301）中，机针把面线穿过面料。针上升时形成线环，旋梭钩住线环并绕过装有底线的梭壳。挑线杆把线环拉回，交锁点位于面料内部。旋梭每个针周期转两圈。用滑块改变转速。",
    "facts": [
     [
      "线迹",
      "301，面线和底线"
     ],
     [
      "旋梭",
      "每针转 2 圈"
     ],
     [
      "工业缝纫机",
      "约 4000–5000 针/分"
     ],
     [
      "旋梭最高",
      "约 12 000 r/min"
     ]
    ]
   },
   {
    "k": "线迹类型",
    "title": "301、401、504、516、406",
    "text": "ISO 4915 把线迹分为若干类：300 锁式线迹、400 链式线迹、500 包缝线迹、600 绷缝线迹。它们在强度、弹性、包边和用线量上各不相同。弹性针织物需要有弹性的线迹，机织物通常用锁式或链式线迹缝制。用滑块选择线迹类型。",
    "facts": [
     [
      "300",
      "锁式线迹，如 301"
     ],
     [
      "400",
      "链式线迹，如 401、406"
     ],
     [
      "500",
      "包缝，如 504、516"
     ],
     [
      "用线量",
      "301：每厘米缝线 2.5 厘米线"
     ]
    ]
   },
   {
    "k": "接缝密封",
    "title": "封住针孔",
    "text": "每一针都会留下针孔，水可以从中渗入。因此防水服装在缝合后要在内侧贴压胶条：热风激活胶条上的热熔胶，压辊将其压实。也可以完全不用针而直接焊接。用滑块选择接缝类型。",
    "facts": [
     [
      "问题",
      "针孔会漏水"
     ],
     [
      "压胶条",
      "热熔胶，热风激活"
     ],
     [
      "焊接",
      "无针孔，需热塑性"
     ],
     [
      "用途",
      "防水透湿夹克、帐篷、防护服"
     ]
    ]
   },
   {
    "k": "焊接",
    "title": "热风、热楔、高频、超声波",
    "text": "热塑性涂层或合成面料可以不用线连接：把聚合物层熔化并压合。热量来自热风、加热楔、高频电场或超声波振动。这样能得到防水气密的接缝，用于篷布、充气船或帐篷。用滑块选择方法。",
    "facts": [
     [
      "热风",
      "速度快，无需模具，可做 3D"
     ],
     [
      "热楔",
      "薄膜、长直缝"
     ],
     [
      "高频",
      "27.12 MHz，PVC 等极性塑料"
     ],
     [
      "超声波",
      "振动产生摩擦热"
     ]
    ]
   },
   {
    "k": "产品",
    "title": "衬衫、夹克、篷布",
    "text": "产品经过哪些工序取决于材料。机织衬衫多层铺布裁剪后缝制。防水透湿夹克缝制后接缝压胶。PVC 涂层布卡车篷布用焊接代替缝纫。用滑块选择产品。",
    "facts": [
     [
      "衬衫",
      "铺布、CNC 裁剪、缝纫"
     ],
     [
      "防水夹克",
      "缝纫加压胶"
     ],
     [
      "卡车篷布",
      "焊接拼幅、装扣眼"
     ],
     [
      "产业链",
      "从纤维到产品"
     ]
    ]
   }
  ],
  "cv": {
   "pliesN": "{n} 层",
   "sizesN": "{n} 个尺码",
   "spmU": "针/分",
   "le": {
    "table": "裁床",
    "spreader": "铺布机",
    "lay": "铺布高度 ≈ {h} cm",
    "example": "示例：每层 0.8 mm",
    "reqT": "铺布要求",
    "req": [
     "区分色差",
     "各层对齐",
     "无张力铺布",
     "剔除疵点"
    ],
    "cnc": "自动裁剪系统视型号可裁压缩后约 6 至 9 cm 的布层。真空压紧布层并在裁剪时固定。",
    "tooHigh": "布层高于常见 CNC 裁床的裁剪能力：需分开或用直刀电剪。"
   },
   "sb": {
    "marker": "{n} 个尺码的排料图（示意）",
    "eff": "{e}%",
    "effL": "排料利用率（示例）",
    "formula": "衣片面积 ÷ 排料面积",
    "avg": "行业平均约 78–85%，借助 AI 排料可达约 88–94%（厂商数据）。",
    "lossT": "其他损耗（参考值）",
    "loss": [
     [
      "排料（1 − 利用率）",
      15,
      25
     ],
     [
      "幅宽未利用",
      2,
      8
     ],
     [
      "布层两端",
      1,
      3
     ],
     [
      "铺布：张力、收缩",
      0.5,
      2
     ],
     [
      "裁剪",
      0.5,
      1.5
     ]
    ]
   },
   "cu": {
    "vac": "真空压紧布层",
    "pliesL": "层数",
    "edgeL": "切边",
    "m": [
     {
      "n": "直刀电剪",
      "p": "多层，手工引导",
      "e": "毛边，可能脱散",
      "d": "上下往复的直刀由人工沿排料线引导。灵活便宜，精度取决于操作者。"
     },
     {
      "n": "CNC 振动刀",
      "p": "压缩后约 6–9 cm",
      "e": "干净，机械切割",
      "d": "裁头按 CAD 文件沿轮廓运行，高速振动刀切割真空压紧的布层。批量生产精度高、效率高。"
     },
     {
      "n": "激光",
      "p": "多为单层",
      "e": "合成纤维封边",
      "d": "CO₂ 激光沿轮廓熔化或气化材料。合成面料边缘熔合不脱散；天然纤维可能变色，并产生烟雾。"
     },
     {
      "n": "超声波",
      "p": "多为单层",
      "e": "熔焊封边",
      "d": "振动刀产生摩擦热，熔封热塑性面料的切边。适用于产业用纺织品和带材。"
     }
    ]
   },
   "ls": {
    "fabric": "两层面料",
    "bobbin": "装底线的梭芯",
    "hook": "旋梭",
    "lock": "交锁点在面料内部",
    "takeup": "挑线杆",
    "calc": "转速与缝纫速度",
    "spmL": "机针",
    "hookL": "旋梭（2×）",
    "slL": "针距",
    "vL": "缝纫速度",
    "note": "缝纫速度 = 每分钟针数 × 针距。以 3 mm 针距为例；实际中起针、收针和转角会降低速度。",
    "nowCap": "旋梭钩住线环并绕过梭芯",
    "nowSet": "挑线杆收紧线迹"
   },
   "sa": {
    "top": "正面",
    "bottom": "反面",
    "edge": "布边",
    "consT": "用线量（每厘米缝线所需线长，厘米）",
    "useL": "用途",
    "propL": "特点",
    "s": [
     {
      "n": "301 锁式线迹",
      "t": "1 根面线 + 1 根底线",
      "r": 2.5,
      "use": "最常用线迹：衬衫、裤子、机织物明线、产业用纺织品。",
      "prop": "非常牢固，两面相同，用线少；弹性小，需更换梭芯。"
     },
     {
      "n": "401 双线链式",
      "t": "1 根针线 + 1 根弯针线",
      "r": 5.5,
      "use": "牛仔裤长缝、明线、腰头。",
      "prop": "比 301 更有弹性、效率更高，起皱少；用线更多。"
     },
     {
      "n": "504 三线包缝",
      "t": "1 根针线 + 2 根弯针线",
      "r": 14,
      "use": "针织物：T 恤侧缝、包边。",
      "prop": "弹性很好，包住布边；用线量大。"
     },
     {
      "n": "516 安全线迹",
      "t": "401 + 504 同时",
      "r": 19.5,
      "use": "机织物侧缝和裆缝。",
      "prop": "链式线迹承受负荷，包缝线迹包边。"
     },
     {
      "n": "406 绷缝",
      "t": "2 根针线 + 1 根弯针线",
      "r": 18,
      "use": "T 恤下摆、针织物袖口和底边。",
      "prop": "正面两行平行线，反面弯针线；有弹性且平整。"
     }
    ]
   },
   "se": {
    "holes": "针孔",
    "fused": "熔合",
    "tape": "热熔压胶条",
    "leak": "水从针孔渗入",
    "dry": "接缝保持防水",
    "hotair": "热风 + 压辊",
    "note": "防水服装仅有防水面料还不够：只有压胶或焊接的接缝才能使产品防水。压胶条须与复合面料匹配，才能经受多次洗涤。",
    "m": [
     {
      "n": "缝合",
      "d": "传统针线缝合。牢固经济，但每个针孔都是漏点。"
     },
     {
      "n": "缝合加压胶",
      "d": "缝合后在内侧贴热熔压胶条。热风激活胶层，压辊压实，冷却后封住针孔。"
     },
     {
      "n": "焊接",
      "d": "各层不用针，而是热熔连接。没有针孔，但材料须为热塑性或带有此类涂层。"
     }
    ]
   },
   "we": {
    "nozzle": "热风喷嘴",
    "wedge": "热楔",
    "electrode": "电极",
    "sono": "超声焊头",
    "seam": "焊缝",
    "forL": "适用于",
    "proL": "优点",
    "conL": "缺点",
    "m": [
     {
      "n": "热风焊",
      "d": "喷嘴向两层之间吹热风，随后压辊立即压合。",
      "for": "遮阳篷、卡车篷布、充气船；曲线和 3D 形状",
      "pro": "速度快，无需模具，频繁启停无问题。",
      "con": "需要排风；参数须按材料调整。"
     },
     {
      "n": "热楔焊",
      "d": "加热金属楔滑入两层之间熔化涂层，压辊随后压合。",
      "for": "薄膜和厚面料、长直缝、容器",
      "pro": "热量精确作用于接缝，运行安静。",
      "con": "停机时热楔积热，起焊处可能过热。"
     },
     {
      "n": "高频焊",
      "d": "交变电磁场（27.12 MHz）从内部加热极性塑料，电极压合各层。",
      "for": "PVC 和 PU、遮阳篷和篷布；在欧洲普遍",
      "pro": "焊缝非常牢固，可用成型电极。",
      "con": "电极长度受限，设备昂贵；仅适用于极性塑料。"
     },
     {
      "n": "超声波焊",
      "d": "焊头高频振动，在接触区产生摩擦热，将各层焊合。",
      "for": "合成纤维、非织造布、过滤材料、防护服",
      "pro": "无需外加热源，速度快；同一原理也可裁切。",
      "con": "仅适用于热塑性材料；厚层困难。"
     }
    ]
   },
   "pr": {
    "keyT": "关键点",
    "p": [
     {
      "n": "衬衫",
      "mat": "棉机织物",
      "steps": [
       [
        "铺布",
        "多层，对格"
       ],
       [
        "CNC 裁剪",
        "振动刀"
       ],
       [
        "缝纫",
        "锁式线迹 301"
       ],
       [
        "钉扣",
        "锁眼、钉扣"
       ],
       [
        "整烫",
        "整理、折叠"
       ]
      ],
      "key": [
       "排料利用率决定面料用量",
       "锁式线迹接缝整洁，两面一致",
       "机织物尺寸稳定，可多层裁剪"
      ]
     },
     {
      "n": "防水透湿夹克",
      "mat": "3 层复合面料",
      "steps": [
       [
        "裁剪",
        "层数少，精确"
       ],
       [
        "缝纫",
        "301，缝份窄"
       ],
       [
        "压胶",
        "热风压胶条"
       ],
       [
        "拉链",
        "防水粘合"
       ],
       [
        "检测",
        "防水性"
       ]
      ],
      "key": [
       "每条接缝都要密封，否则水会从针孔渗入",
       "压胶条与复合面料必须匹配",
       "接缝越少，风险越低"
      ]
     },
     {
      "n": "卡车篷布",
      "mat": "PVC 涂层涤纶布",
      "steps": [
       [
        "裁剪",
        "按尺寸裁幅"
       ],
       [
        "焊接",
        "高频或热风"
       ],
       [
        "卷边",
        "加强、焊接"
       ],
       [
        "扣眼",
        "装扣眼和嵌条"
       ],
       [
        "印刷",
        "标志、广告"
       ]
      ],
      "key": [
       "焊缝防水，往往比缝线接缝更牢",
       "PVC 属极性塑料，适合高频焊接",
       "大尺寸需要长焊接线"
      ]
     }
    ]
   }
  },
  "quiz": [
   {
    "q": "为什么裁剪前要把面料铺成多层？",
    "a": [
     "一次裁出大量衣片",
     "为了晾干",
     "为了染色",
     "为了收缩"
    ],
    "c": 0,
    "e": "多层布一刀可裁出许多相同衣片。",
    "sc": 0
   },
   {
    "q": "排料利用率如何计算？",
    "a": [
     "衣片面积 ÷ 排料面积",
     "层数 × 幅宽",
     "布长 ÷ 衣片数",
     "重量 ÷ 面积"
    ],
    "c": 0,
    "e": "即排料面积中真正成为衣片的比例。",
    "sc": 1
   },
   {
    "q": "CNC 裁床用什么固定布层？",
    "a": [
     "真空",
     "针",
     "胶",
     "重物"
    ],
    "c": 0,
    "e": "真空压紧布层并在裁剪时固定。",
    "sc": 2
   },
   {
    "q": "锁式线迹每针旋梭转几圈？",
    "a": [
     "一圈",
     "两圈",
     "三圈",
     "不转"
    ],
    "c": 1,
    "e": "旋梭转速是针周期的两倍。",
    "sc": 3
   },
   {
    "q": "哪种线迹适合弹性 T 恤侧缝？",
    "a": [
     "301 锁式",
     "504 包缝",
     "101 单线链式",
     "手缝"
    ],
    "c": 1,
    "e": "504 包缝弹性很好，同时包边。",
    "sc": 4
   },
   {
    "q": "为什么防水夹克的接缝要压胶？",
    "a": [
     "封住针孔",
     "为了美观",
     "增加弹性",
     "节省用线"
    ],
    "c": 0,
    "e": "水会从针孔渗入，热熔压胶条将其封住。",
    "sc": 5
   },
   {
    "q": "哪种焊接使用 27.12 MHz 电场？",
    "a": [
     "热楔焊",
     "热风焊",
     "高频焊",
     "超声波焊"
    ],
    "c": 2,
    "e": "高频焊用电磁场加热 PVC 等极性塑料。",
    "sc": 6
   },
   {
    "q": "PVC 卡车篷布的拼幅通常如何连接？",
    "a": [
     "焊接",
     "只缝合",
     "针织",
     "机织"
    ],
    "c": 0,
    "e": "PVC 涂层篷布通常用高频或热风焊接。",
    "sc": 7
   }
  ],
  "links": [
   [
    "织物组织",
    "平纹、斜纹、缎纹：这里被裁剪和缝制的机织物是如何构成的。"
   ],
   [
    "圆机针织",
    "用于 T 恤和运动服的针织物，需要有弹性的线迹。"
   ],
   [
    "化学纤维",
    "涤纶、锦纶等：可以焊接和激光切割的热塑性纤维。"
   ],
   [
    "机械后整理",
    "预缩、轧光等：在裁剪前使织物尺寸稳定。"
   ],
   [
    "纺织印花",
    "面料进入成衣制作之前在布面上印制图案。"
   ]
  ]
 }
};
