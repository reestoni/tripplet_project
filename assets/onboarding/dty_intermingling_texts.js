window.TEXTS = {
 "de": {
  "ui": {
   "eyebrow": "Knowledge Base · Texturierung",
   "h1": "Wie ein Multifilamentgarn verwirbelt wird",
   "lead": "Vom POY-Faden auf der DTY-Maschine bis zum verwirbelten Garn mit Knoten: fünf kurze Szenen, die man selbst durchklicken oder automatisch ablaufen lassen kann.",
   "pressure": "Luftdruck",
   "of": "Overfeed",
   "low": "niedrig",
   "mid": "mittel",
   "high": "hoch",
   "pause": "⏸ Pause",
   "play": "▶ Abspielen",
   "scenes": "Szenen",
   "clickHint": "Auf eine Position in der Maschine klicken - sie wird hier erklärt.",
   "fricHint": "(Doppelklick: Friktionsaggregat im Detail)",
   "note": "Schematische Darstellung. Abstände, Filamentzahl und Knotendichte sind zur Veranschaulichung vereinfacht; reale Werte hängen von Artikel, Maschine und Düse ab.",
   "v2": "LW 2 (m/min)",
   "dr": "Verstreckung",
   "spread": "Streuung (unten)"
  },
  "stations": [
   {
    "n": "POY-Vorlagespule",
    "d": "Teilorientiertes Polyestergarn (POY) aus der Spinnerei wird abgezogen."
   },
   {
    "n": "Lieferwerk 1",
    "d": "Zieht den Faden mit definierter Geschwindigkeit von der Spule ab."
   },
   {
    "n": "Primärheizer",
    "d": "Erwärmt den Faden, damit er sich verstrecken und kräuseln lässt."
   },
   {
    "n": "Kühlschiene",
    "d": "Kühlt den Faden ab und fixiert so die Kräuselung."
   },
   {
    "n": "Friktionsaggregat",
    "d": "Rotierende Scheiben erzeugen Falschdraht: der Faden wird texturiert und bauschig."
   },
   {
    "n": "Lieferwerk 2",
    "d": "Schneller als Lieferwerk 1: dazwischen wird der Faden verstreckt."
   },
   {
    "n": "Verwirbelungsdüse",
    "d": "Heberlein-Düse: Druckluft verschlingt die Filamente zu Knoten."
   },
   {
    "n": "Lieferwerk 2.x (OF)",
    "d": "Läuft 3–7 % langsamer als Lieferwerk 2. Dieser Overfeed (OF) gibt der Düse Extramaterial für ihre Arbeit."
   },
   {
    "n": "Set-Heizer",
    "d": "Zweiter Heizer zwischen Lieferwerk 2.x und Lieferwerk 3. Er stabilisiert das Garn: Restschrumpf und Elastizität sinken (Set-Garn). Ohne Set-Heizer bleibt das Garn hochelastisch (HE-Garn)."
   },
   {
    "n": "Lieferwerk 3",
    "d": "Zieht das Garn durch den Set-Heizer und führt es zur Aufwicklung.",
    "s": "LW 3"
   },
   {
    "n": "Aufwicklung",
    "d": "Das fertige DTY-Garn wird auf eine Kreuzspule gewickelt."
   }
  ],
  "scenes": [
   {
    "k": "Maschine",
    "title": "Der Weg durch die DTY-Maschine",
    "text": "DTY steht für Draw Textured Yarn. Auf der Maschine wird das POY in einem Durchgang verstreckt, texturiert und am Ende verwirbelt. Die Heberlein-Düse sitzt nach dem Friktionsaggregat zwischen Lieferwerk 2 und Lieferwerk 2.x. Weil Lieferwerk 2.x 3–7 % langsamer läuft als Lieferwerk 2, kommt mehr Garn in die Düse, als dahinter abgezogen wird: Dieser Overfeed (OF) ist das Material, mit dem die Düse arbeitet.",
    "facts": [
     [
      "Eingang",
      "POY, teilorientiertes Polyester-Multifilament"
     ],
     [
      "Prozess",
      "Verstrecken, Texturieren, Verwirbeln"
     ],
     [
      "Ausgang",
      "DTY auf Kreuzspule"
     ],
     [
      "Düse",
      "zwischen Lieferwerk 2 und 2.x"
     ],
     [
      "Overfeed",
      "LW 2.x 3–7 % langsamer als LW 2 → Extramaterial für die Düse"
     ],
     [
      "Positionen",
      "in der Maschine anklicken, um sie erklärt zu bekommen"
     ],
     [
      "Regler",
      "Geschwindigkeit LW 2, Verstreckung und Overfeed unten eingeben: LW 1 und LW 2.x werden in m/min berechnet"
     ]
    ]
   },
   {
    "k": "Faden",
    "title": "Ein Faden aus vielen Filamenten",
    "text": "Ein Multifilamentgarn besteht aus vielen endlosen Einzelfilamenten, die parallel nebeneinander liegen. Ohne weitere Behandlung halten sie kaum zusammen und können sich bei der Weiterverarbeitung aufspleissen.",
    "facts": [
     [
      "Beispiel",
      "167 dtex f48: 48 Filamente"
     ],
     [
      "dtex",
      "Masse in Gramm pro 10 000 m Garn"
     ],
     [
      "f-Zahl",
      "Anzahl Einzelfilamente"
     ],
     [
      "Problem",
      "loser Verbund, Filamente spreizen ab"
     ]
    ]
   },
   {
    "k": "Im Jet",
    "title": "Was in der Düse mit den Filamenten passiert",
    "text": "Der Faden läuft durch den Fadenkanal im Keramik-Düsenkern. Durch eine Bohrung trifft die Druckluft quer auf das Bündel. Im Kanalquerschnitt bilden sich zwei gegenläufige Wirbel: Die Filamente werden auseinandergerissen und auf Kreisbahnen herumgeschleudert. Weil der Faden dabei weiterläuft, verdrillen sich die Filamente vor und hinter der Bohrung in entgegengesetzter Richtung und verschlingen sich zu einem Knoten. Dann öffnet der Luftstrahl den nächsten Abschnitt, und der Zyklus beginnt von vorn. Öffnen kann sich das Bündel nur, weil es locker in die Düse kommt: dafür sorgt der Overfeed.",
    "facts": [
     [
      "Aufbau",
      "Metallgehäuse, Keramik-Düsenkern, Fadenkanal, Luftbohrung"
     ],
     [
      "Luft",
      "zwei gegenläufige Wirbel im Kanal"
     ],
     [
      "Filamente",
      "öffnen, kreisen, verschlingen"
     ],
     [
      "Overfeed",
      "hält die Fadenspannung in der Düse gering, damit sich das Bündel öffnet"
     ],
     [
      "Regler",
      "Luftdruck und Overfeed unten probieren"
     ]
    ]
   },
   {
    "k": "Knoten",
    "title": "Knoten und offene Abschnitte",
    "text": "Hinter der Düse wechseln sich feste Knoten und offene Abschnitte regelmässig ab. Die Knoten geben dem Garn Fadenschluss, die offenen Abschnitte erhalten Bausch und Griff. Gemessen wird das Ergebnis als Anzahl Knoten pro Meter und als Stabilität der Knoten. Wichtig ist auch, dass die Knoten gleichmässig verteilt sind: Darum geht es in der nächsten Szene.",
    "facts": [
     [
      "Kennzahlen",
      "Knoten pro Meter, Knotenstabilität, Gleichmässigkeit der Abstände"
     ],
     [
      "Qualität",
      "gleichmässige Abstände, stabile Knoten"
     ],
     [
      "Mehr Druck",
      "mehr und festere Knoten, bis zur Sättigung"
     ],
     [
      "Zu viel",
      "höherer Luftverbrauch, ggf. Filamentschäden"
     ],
     [
      "Overfeed",
      "zu wenig: Faden straff, weniger Knoten; zu viel: unruhiger Fadenlauf"
     ]
    ]
   },
   {
    "k": "Gleichmässigkeit",
    "title": "Viele Knoten reichen nicht: Sie müssen gleichmässig verteilt sein",
    "text": "Zwei Garne können gleich viele und gleich stabile Knoten haben und sich trotzdem ganz anders verhalten. Liegen die Knoten ungleichmässig, gibt es Häufungen und lange offene Stellen. Dort hält das Garn nicht zusammen: Die Filamente spreizen ab, bleiben an Fadenführern hängen und brechen. Für die Qualität zählt deshalb neben Knotenzahl und Stabilität auch die Streuung der Knotenabstände und die längste offene Stelle. Mit dem Regler lässt sich die Streuung im unteren Garn verändern.",
    "facts": [
     [
      "Gleiche Knoten/m",
      "sagt nichts über die Verteilung"
     ],
     [
      "Kennzahl",
      "Streuung der Knotenabstände (CV) und längste offene Stelle"
     ],
     [
      "Folge",
      "offene Stellen spleissen auf: Brüche, Flusen, Fehler im Gewebe"
     ],
     [
      "Ursachen",
      "schwankende Fadenspannung oder Overfeed, verschmutzte oder verschlissene Düse, schwankender Luftdruck"
     ],
     [
      "Merksatz",
      "Der Mittelwert allein reicht nicht"
     ]
    ]
   },
   {
    "k": "Vergleich",
    "title": "Warum verwirbelt wird",
    "text": "Ein verwirbeltes Garn verhält sich beim Weben, Stricken oder Spulen wie ein geschlossener Faden. Die Filamente bleiben zusammen, hängen weniger an Fadenführern fest und brechen seltener. Oft kann so auf Zwirnen oder Schlichten verzichtet werden.",
    "facts": [
     [
      "Fadenschluss",
      "Filamente bleiben gebündelt"
     ],
     [
      "Verarbeitung",
      "weniger Brüche und Flusen"
     ],
     [
      "Kosten",
      "Zwirnen oder Schlichten oft unnötig"
     ],
     [
      "Merksatz",
      "Kein Knoten, kein Fadenschluss"
     ]
    ]
   }
  ],
  "cv": {
   "machine": "Schema DTY-Maschine · eine Fadenposition",
   "drawZone": "Verstreckzone: Lieferwerk 2 schneller als Lieferwerk 1",
   "ofZone": "Overfeed −{of} %",
   "spd": [
    [
     "LW 1",
     "= LW 2 ÷ {dr}"
    ],
    [
     "LW 2",
     "Eingabe"
    ],
    [
     "LW 2.x",
     "= LW 2 − {of} % (Overfeed)"
    ]
   ],
   "xsec": "Querschnitt",
   "filaments": "{n} Filamente",
   "example": "Beispiel 167 dtex f48",
   "side": "Seitenansicht: Filamente liegen parallel",
   "loose": "lose Filamente spleissen ab",
   "long": "Längsschnitt",
   "pressure": "Druck",
   "yarnRun": "Fadenlauf",
   "crimped": "gekräuselt, geschlossen",
   "mingled": "verwirbelt",
   "leg": [
    [
     "Luftanschluss",
     "Druckluft aus dem Maschinennetz"
    ],
    [
     "Luftbohrung",
     "Luftstrahl trifft quer auf den Faden"
    ],
    [
     "Keramik-Düsenkern",
     "verschleissfest und glatt"
    ],
    [
     "Fadenkanal",
     "hier werden die Filamente verwirbelt"
    ],
    [
     "Luftaustritt",
     "Luft strömt zu beiden Seiten aus"
    ],
    [
     "Gehäuse",
     "hält den Kern, führt die Luft zu"
    ]
   ],
   "marked": "drei markierte Filamente zum Mitverfolgen",
   "aa": "Schnitt A–A: Blick in den Kanal",
   "steps": [
    "Knoten verlässt die Düse",
    "Luftstrahl öffnet das Bündel",
    "Filamente kreisen in zwei Wirbeln",
    "Filamente drehen sich zum Knoten"
   ],
   "tension": "Fadenspannung in der Düse",
   "knot": "Knoten",
   "open": "offener Abschnitt",
   "measure": "Messstrecke (schematisch)",
   "density": "Knotendichte",
   "strength": "Knotenfestigkeit",
   "tryP": "Regler \"Luftdruck\" verändern",
   "without": "ohne Verwirbelung",
   "withoutT": "Filamente lose, Schlingen können hängen bleiben",
   "with": "mit Verwirbelung",
   "withT": "Knoten halten das Bündel zusammen: Fadenschluss",
   "even": "Gleichmässig",
   "evenT": "Knoten in fast gleichen Abständen",
   "uneven": "Ungleichmässig",
   "unevenT": "gleich viele Knoten, aber Lücken und Häufungen",
   "gap": "lange offene Stelle",
   "distTitle": "Knotenabstände",
   "meanL": "Mittelwert",
   "twice": "2 × Mittel",
   "statKnots": "{n} Knoten/m",
   "statCv": "Streuung der Abstände (CV): {cv} %",
   "statGap": "längste offene Stelle: {g} mm",
   "sameN": "Gleiche Knotenzahl, gleich stabile Knoten - und trotzdem ein anderes Garn",
   "now": "Beide Garne haben 80 Knoten/m. Streuung der Abstände: oben {a} %, unten {b} %."
  },
  "quiz": [
   {
    "q": "Wo sitzt die Verwirbelungsdüse auf der DTY-Maschine?",
    "a": [
     "Zwischen Lieferwerk 2 und Lieferwerk 2.x",
     "Zwischen Lieferwerk 1 und dem Primärheizer",
     "Direkt vor der Aufwicklung, nach Lieferwerk 3",
     "Zwischen Kühlschiene und Friktionsaggregat"
    ],
    "c": 0,
    "e": "Die Düse sitzt nach dem Friktionsaggregat zwischen LW 2 und LW 2.x.",
    "sc": 0
   },
   {
    "q": "Was bedeutet der Overfeed (OF) an der Düse?",
    "a": [
     "Lieferwerk 2.x läuft 3–7 % langsamer als Lieferwerk 2",
     "Lieferwerk 2.x läuft 3–7 % schneller als Lieferwerk 2",
     "Lieferwerk 1 läuft schneller als Lieferwerk 2",
     "Die Düse bekommt mehr Druckluft als nötig"
    ],
    "c": 0,
    "e": "Weil LW 2.x langsamer abzieht, kommt mehr Garn in die Düse, als dahinter abgezogen wird.",
    "sc": 0
   },
   {
    "q": "Lieferwerk 2 läuft mit 800 m/min, der Overfeed ist 5 %. Wie schnell läuft Lieferwerk 2.x?",
    "a": [
     "760 m/min",
     "840 m/min",
     "800 m/min",
     "471 m/min"
    ],
    "c": 0,
    "e": "LW 2.x = LW 2 − 5 % = 800 × 0,95 = 760 m/min.",
    "sc": 0
   },
   {
    "q": "Lieferwerk 2 läuft mit 850 m/min, die Verstreckung ist 1,70. Wie schnell läuft Lieferwerk 1?",
    "a": [
     "500 m/min",
     "1445 m/min",
     "850 m/min",
     "808 m/min"
    ],
    "c": 0,
    "e": "LW 1 = LW 2 ÷ Verstreckung = 850 ÷ 1,70 = 500 m/min.",
    "sc": 0
   },
   {
    "q": "Was bedeutet die Angabe „167 dtex f48“?",
    "a": [
     "167 g pro 10 000 m Garn, aus 48 Einzelfilamenten",
     "167 Filamente mit je 48 dtex",
     "167 Knoten pro Meter bei 48 m/min",
     "48 g pro 167 m Garn"
    ],
    "c": 0,
    "e": "dtex ist die Masse in Gramm pro 10 000 m, die f-Zahl die Anzahl Einzelfilamente.",
    "sc": 1
   },
   {
    "q": "Was passiert im Fadenkanal der Düse?",
    "a": [
     "Querluft bildet zwei gegenläufige Wirbel, die Filamente verschlingen sich zu Knoten",
     "Die Luft dreht den ganzen Faden dauerhaft wie beim Zwirnen",
     "Die Luft kühlt den Faden nach dem Heizer ab",
     "Die Luft schneidet lose Filamente ab"
    ],
    "c": 0,
    "e": "Die Filamente werden auseinandergerissen, kreisen und verdrillen sich vor und hinter der Bohrung zu einem Knoten.",
    "sc": 2
   },
   {
    "q": "Warum braucht die Düse den Overfeed?",
    "a": [
     "Der Faden kommt locker an, so kann sich das Bündel öffnen",
     "Damit der Faden schneller läuft",
     "Damit das Garn in der Düse verstreckt wird",
     "Damit die Düse weniger Luft braucht"
    ],
    "c": 0,
    "e": "Ein straffer Faden öffnet sich kaum. Der Overfeed hält die Fadenspannung in der Düse gering.",
    "sc": 2
   },
   {
    "q": "Wie wird das Ergebnis der Verwirbelung gemessen?",
    "a": [
     "Knoten pro Meter, Knotenstabilität und Gleichmässigkeit der Abstände",
     "Garnfeinheit in dtex",
     "Luftverbrauch der Düse",
     "Anzahl Filamente"
    ],
    "c": 0,
    "e": "Kennzahlen sind die Knotendichte (Knoten pro Meter), die Knotenstabilität und die Gleichmässigkeit der Knotenabstände.",
    "sc": 3
   },
   {
    "q": "Was passiert, wenn man den Luftdruck stark erhöht?",
    "a": [
     "Mehr und festere Knoten bis zur Sättigung, aber mehr Luftverbrauch",
     "Es entstehen weniger Knoten",
     "Das Garn wird feiner",
     "Der Overfeed steigt automatisch"
    ],
    "c": 0,
    "e": "Mehr Druck gibt mehr und festere Knoten bis zu einer Sättigung. Zu viel Druck kostet Luft und kann Filamente schädigen.",
    "sc": 3
   },
   {
    "q": "Zwei Garne haben gleich viele und gleich stabile Knoten. Was kann das eine trotzdem schlechter machen?",
    "a": [
     "Die Knoten sind ungleichmässig verteilt, mit langen offenen Stellen",
     "Es hat mehr Filamente",
     "Es wurde mit Set-Heizer verarbeitet",
     "Die Knoten liegen in zu gleichen Abständen"
    ],
    "c": 0,
    "e": "An langen offenen Stellen hält das Garn nicht zusammen. Knotenzahl und Stabilität allein sagen nichts über die Verteilung.",
    "sc": 4
   },
   {
    "q": "Woran erkennt man eine ungleichmässige Verwirbelung bei der Messung?",
    "a": [
     "Grosse Streuung der Knotenabstände (hoher CV) und lange offene Stellen",
     "An einer hohen Knotenstabilität",
     "An einer tiefen Garnfeinheit",
     "An einem hohen Luftverbrauch"
    ],
    "c": 0,
    "e": "Neben dem Mittelwert (Knoten/m) zählen die Streuung der Abstände und die längste offene Stelle.",
    "sc": 4
   },
   {
    "q": "Was kann ungleichmässige Knotenabstände verursachen?",
    "a": [
     "Schwankende Fadenspannung oder Overfeed, verschmutzte oder verschlissene Düse, schwankender Luftdruck",
     "Die Farbe des POY",
     "Die Kreuzspule bei der Aufwicklung",
     "Eine zu tiefe Raumtemperatur im Labor"
    ],
    "c": 0,
    "e": "Alles, was den Fadenlauf oder die Luft in der Düse unruhig macht, macht auch die Knotenabstände unruhig.",
    "sc": 4
   },
   {
    "q": "Warum wird ein Multifilamentgarn überhaupt verwirbelt?",
    "a": [
     "Für Fadenschluss: die Filamente bleiben zusammen, Zwirnen oder Schlichten ist oft unnötig",
     "Damit das Garn durch Echtdraht reissfester wird",
     "Damit das Garn glänzender wird",
     "Damit es sich besser färben lässt"
    ],
    "c": 0,
    "e": "Ein verwirbeltes Garn verhält sich wie ein geschlossener Faden: weniger Brüche und Flusen.",
    "sc": 5
   }
  ]
 },
 "en": {
  "ui": {
   "eyebrow": "Knowledge Base · Texturing",
   "h1": "How a multifilament yarn is intermingled",
   "lead": "From the POY on the DTY machine to the intermingled yarn with its nips: five short scenes - click through them yourself or let them play.",
   "pressure": "Air pressure",
   "of": "Overfeed",
   "low": "low",
   "mid": "medium",
   "high": "high",
   "pause": "⏸ Pause",
   "play": "▶ Play",
   "scenes": "Scenes",
   "clickHint": "Click a position on the machine - it is explained here.",
   "fricHint": "(Double-click: friction unit in detail)",
   "note": "Schematic. Distances, number of filaments and nip density are simplified for illustration; real values depend on article, machine and jet.",
   "v2": "FR 2 (m/min)",
   "dr": "Draw ratio",
   "spread": "Spread (bottom)"
  },
  "stations": [
   {
    "n": "POY supply package",
    "d": "Partially oriented polyester yarn (POY) from spinning is unwound."
   },
   {
    "n": "Feed roll 1",
    "d": "Pulls the yarn off the package at a defined speed."
   },
   {
    "n": "Primary heater",
    "d": "Heats the yarn so it can be drawn and crimped."
   },
   {
    "n": "Cooling plate",
    "d": "Cools the yarn and so sets the crimp."
   },
   {
    "n": "Friction unit",
    "d": "Rotating discs create false twist: the yarn becomes textured and bulky."
   },
   {
    "n": "Feed roll 2",
    "d": "Faster than feed roll 1: the yarn is drawn in between."
   },
   {
    "n": "Intermingling jet",
    "d": "Heberlein jet: compressed air entangles the filaments into nips."
   },
   {
    "n": "Feed roll 2.x (OF)",
    "d": "Runs 3–7 % slower than feed roll 2. This overfeed (OF) gives the jet extra material to work with."
   },
   {
    "n": "Set heater",
    "d": "Second heater between feed roll 2.x and feed roll 3. It stabilises the yarn: residual shrinkage and elasticity drop (set yarn). Without the set heater the yarn stays highly elastic (HE yarn)."
   },
   {
    "n": "Feed roll 3",
    "d": "Pulls the yarn through the set heater and leads it to the take-up.",
    "s": "FR 3"
   },
   {
    "n": "Take-up",
    "d": "The finished DTY is wound onto a cross-wound package."
   }
  ],
  "scenes": [
   {
    "k": "Machine",
    "title": "The path through the DTY machine",
    "text": "DTY stands for Draw Textured Yarn. In one pass the machine draws the POY, textures it and finally intermingles it. The Heberlein jet sits after the friction unit, between feed roll 2 and feed roll 2.x. Because feed roll 2.x runs 3–7 % slower than feed roll 2, more yarn enters the jet than is taken off behind it: this overfeed (OF) is the material the jet works with.",
    "facts": [
     [
      "Input",
      "POY, partially oriented polyester multifilament"
     ],
     [
      "Process",
      "drawing, texturing, intermingling"
     ],
     [
      "Output",
      "DTY on a cross-wound package"
     ],
     [
      "Jet",
      "between feed roll 2 and 2.x"
     ],
     [
      "Overfeed",
      "FR 2.x 3–7 % slower than FR 2 → extra material for the jet"
     ],
     [
      "Positions",
      "click them on the machine to get them explained"
     ],
     [
      "Try it",
      "enter FR 2 speed, draw ratio and overfeed below: FR 1 and FR 2.x are calculated in m/min"
     ]
    ]
   },
   {
    "k": "Yarn",
    "title": "One yarn, many filaments",
    "text": "A multifilament yarn consists of many continuous single filaments lying side by side. Without further treatment they hardly hold together and can splay apart during further processing.",
    "facts": [
     [
      "Example",
      "167 dtex f48: 48 filaments"
     ],
     [
      "dtex",
      "mass in grams per 10,000 m of yarn"
     ],
     [
      "f number",
      "number of single filaments"
     ],
     [
      "Problem",
      "loose bundle, filaments splay out"
     ]
    ]
   },
   {
    "k": "In the jet",
    "title": "What happens to the filaments in the jet",
    "text": "The yarn runs through the yarn channel in the ceramic jet core. Through a bore the compressed air hits the bundle crosswise. Two counter-rotating vortices form in the channel cross-section: the filaments are torn apart and whirled around on circular paths. As the yarn keeps moving, the filaments twist in opposite directions before and after the bore and entangle into a nip. Then the air jet opens the next section and the cycle starts again. The bundle can only open because it enters the jet loosely: that is what the overfeed is for.",
    "facts": [
     [
      "Design",
      "metal housing, ceramic core, yarn channel, air bore"
     ],
     [
      "Air",
      "two counter-rotating vortices in the channel"
     ],
     [
      "Filaments",
      "open, circle, entangle"
     ],
     [
      "Overfeed",
      "keeps the yarn tension in the jet low so the bundle can open"
     ],
     [
      "Try it",
      "air pressure and overfeed below"
     ]
    ]
   },
   {
    "k": "Nips",
    "title": "Nips and open sections",
    "text": "Behind the jet, firm nips and open sections alternate regularly. The nips give the yarn cohesion, the open sections keep bulk and handle. The result is measured as nips per metre and as nip stability. It also matters that the nips are evenly distributed: that is the topic of the next scene.",
    "facts": [
     [
      "Key figures",
      "nips per metre, nip stability, evenness of the distances"
     ],
     [
      "Quality",
      "even spacing, stable nips"
     ],
     [
      "More pressure",
      "more and firmer nips, up to saturation"
     ],
     [
      "Too much",
      "higher air consumption, possibly filament damage"
     ],
     [
      "Overfeed",
      "too little: yarn tight, fewer nips; too much: unsteady yarn run"
     ]
    ]
   },
   {
    "k": "Evenness",
    "title": "Many nips are not enough: they have to be evenly distributed",
    "text": "Two yarns can have the same number of equally stable nips and still behave quite differently. If the nips are uneven, there are clusters and long open sections. There the yarn does not hold together: the filaments splay out, catch on yarn guides and break. Besides nip count and stability, quality therefore depends on the spread of the nip distances and the longest open section. Use the slider to change the spread in the bottom yarn.",
    "facts": [
     [
      "Same nips/m",
      "says nothing about the distribution"
     ],
     [
      "Key figure",
      "spread of nip distances (CV) and longest open section"
     ],
     [
      "Result",
      "open sections splay: breaks, fluff, faults in the fabric"
     ],
     [
      "Causes",
      "fluctuating yarn tension or overfeed, dirty or worn jet, fluctuating air pressure"
     ],
     [
      "Rule of thumb",
      "the mean alone is not enough"
     ]
    ]
   },
   {
    "k": "Comparison",
    "title": "Why yarn is intermingled",
    "text": "An intermingled yarn behaves like a closed thread in weaving, knitting or winding. The filaments stay together, catch less on yarn guides and break less often. Twisting or sizing can often be skipped.",
    "facts": [
     [
      "Cohesion",
      "filaments stay bundled"
     ],
     [
      "Processing",
      "fewer breaks and less fluff"
     ],
     [
      "Cost",
      "twisting or sizing often unnecessary"
     ],
     [
      "Rule of thumb",
      "No nip, no cohesion"
     ]
    ]
   }
  ],
  "cv": {
   "machine": "DTY machine schematic · one yarn position",
   "drawZone": "Draw zone: feed roll 2 faster than feed roll 1",
   "ofZone": "Overfeed −{of} %",
   "spd": [
    [
     "FR 1",
     "= FR 2 ÷ {dr}"
    ],
    [
     "FR 2",
     "input"
    ],
    [
     "FR 2.x",
     "= FR 2 − {of} % (overfeed)"
    ]
   ],
   "xsec": "Cross-section",
   "filaments": "{n} filaments",
   "example": "Example 167 dtex f48",
   "side": "Side view: filaments lie parallel",
   "loose": "loose filaments splay out",
   "long": "Longitudinal section",
   "pressure": "Pressure",
   "yarnRun": "Yarn path",
   "crimped": "crimped, closed",
   "mingled": "intermingled",
   "leg": [
    [
     "Air connection",
     "compressed air from the mill network"
    ],
    [
     "Air bore",
     "air jet hits the yarn crosswise"
    ],
    [
     "Ceramic jet core",
     "wear-resistant and smooth"
    ],
    [
     "Yarn channel",
     "the filaments are intermingled here"
    ],
    [
     "Air exit",
     "air flows out on both sides"
    ],
    [
     "Housing",
     "holds the core, supplies the air"
    ]
   ],
   "marked": "three marked filaments to follow",
   "aa": "Section A–A: looking into the channel",
   "steps": [
    "Nip leaves the jet",
    "Air jet opens the bundle",
    "Filaments circle in two vortices",
    "Filaments twist into a nip"
   ],
   "tension": "Yarn tension in the jet",
   "knot": "Nip",
   "open": "open section",
   "measure": "Measuring length (schematic)",
   "density": "Nip density",
   "strength": "Nip stability",
   "tryP": "Change the \"Air pressure\" slider",
   "without": "without intermingling",
   "withoutT": "loose filaments, loops can catch",
   "with": "with intermingling",
   "withT": "nips hold the bundle together: cohesion",
   "even": "Even",
   "evenT": "nips at almost equal distances",
   "uneven": "Uneven",
   "unevenT": "same number of nips, but gaps and clusters",
   "gap": "long open section",
   "distTitle": "Nip distances",
   "meanL": "mean",
   "twice": "2 × mean",
   "statKnots": "{n} nips/m",
   "statCv": "Spread of distances (CV): {cv} %",
   "statGap": "longest open section: {g} mm",
   "sameN": "Same number of nips, equally stable nips - and still a different yarn",
   "now": "Both yarns have 80 nips/m. Spread of distances: top {a} %, bottom {b} %."
  },
  "quiz": [
   {
    "q": "Where is the intermingling jet on the DTY machine?",
    "a": [
     "Between feed roll 2 and feed roll 2.x",
     "Between feed roll 1 and the primary heater",
     "Right before the take-up, after feed roll 3",
     "Between cooling plate and friction unit"
    ],
    "c": 0,
    "e": "The jet sits after the friction unit, between FR 2 and FR 2.x.",
    "sc": 0
   },
   {
    "q": "What does overfeed (OF) at the jet mean?",
    "a": [
     "Feed roll 2.x runs 3–7 % slower than feed roll 2",
     "Feed roll 2.x runs 3–7 % faster than feed roll 2",
     "Feed roll 1 runs faster than feed roll 2",
     "The jet gets more compressed air than needed"
    ],
    "c": 0,
    "e": "Because FR 2.x takes the yarn off more slowly, more yarn enters the jet than leaves it.",
    "sc": 0
   },
   {
    "q": "Feed roll 2 runs at 800 m/min, the overfeed is 5 %. How fast does feed roll 2.x run?",
    "a": [
     "760 m/min",
     "840 m/min",
     "800 m/min",
     "471 m/min"
    ],
    "c": 0,
    "e": "FR 2.x = FR 2 − 5 % = 800 × 0.95 = 760 m/min.",
    "sc": 0
   },
   {
    "q": "Feed roll 2 runs at 850 m/min, the draw ratio is 1.70. How fast does feed roll 1 run?",
    "a": [
     "500 m/min",
     "1445 m/min",
     "850 m/min",
     "808 m/min"
    ],
    "c": 0,
    "e": "FR 1 = FR 2 ÷ draw ratio = 850 ÷ 1.70 = 500 m/min.",
    "sc": 0
   },
   {
    "q": "What does “167 dtex f48” mean?",
    "a": [
     "167 g per 10,000 m of yarn, made of 48 single filaments",
     "167 filaments of 48 dtex each",
     "167 nips per metre at 48 m/min",
     "48 g per 167 m of yarn"
    ],
    "c": 0,
    "e": "dtex is the mass in grams per 10,000 m, the f number the count of single filaments.",
    "sc": 1
   },
   {
    "q": "What happens in the yarn channel of the jet?",
    "a": [
     "Cross air forms two counter-rotating vortices, the filaments entangle into nips",
     "The air twists the whole yarn permanently, like twisting",
     "The air cools the yarn after the heater",
     "The air cuts off loose filaments"
    ],
    "c": 0,
    "e": "The filaments are torn apart, circle and twist before and after the bore into a nip.",
    "sc": 2
   },
   {
    "q": "Why does the jet need the overfeed?",
    "a": [
     "The yarn arrives loose, so the bundle can open",
     "So that the yarn runs faster",
     "So that the yarn is drawn in the jet",
     "So that the jet needs less air"
    ],
    "c": 0,
    "e": "A taut yarn hardly opens. The overfeed keeps the yarn tension in the jet low.",
    "sc": 2
   },
   {
    "q": "How is the result of intermingling measured?",
    "a": [
     "Nips per metre, nip stability and evenness of the distances",
     "Yarn count in dtex",
     "Air consumption of the jet",
     "Number of filaments"
    ],
    "c": 0,
    "e": "The key figures are nip density (nips per metre), nip stability and the evenness of the nip distances.",
    "sc": 3
   },
   {
    "q": "What happens if the air pressure is raised a lot?",
    "a": [
     "More and harder nips up to saturation, but higher air consumption",
     "Fewer nips are formed",
     "The yarn becomes finer",
     "The overfeed rises automatically"
    ],
    "c": 0,
    "e": "More pressure gives more and harder nips up to saturation. Too much pressure costs air and can damage filaments.",
    "sc": 3
   },
   {
    "q": "Two yarns have the same number of equally stable nips. What can still make one of them worse?",
    "a": [
     "The nips are unevenly distributed, with long open sections",
     "It has more filaments",
     "It was processed with the set heater",
     "The nips are at too equal distances"
    ],
    "c": 0,
    "e": "In long open sections the yarn does not hold together. Nip count and stability alone say nothing about the distribution.",
    "sc": 4
   },
   {
    "q": "How do you recognise uneven intermingling in the measurement?",
    "a": [
     "Large spread of nip distances (high CV) and long open sections",
     "By a high nip stability",
     "By a low yarn count",
     "By a high air consumption"
    ],
    "c": 0,
    "e": "Besides the mean (nips/m), the spread of the distances and the longest open section matter.",
    "sc": 4
   },
   {
    "q": "What can cause uneven nip distances?",
    "a": [
     "Fluctuating yarn tension or overfeed, a dirty or worn jet, fluctuating air pressure",
     "The colour of the POY",
     "The cross-wound package at the take-up",
     "A too low room temperature in the lab"
    ],
    "c": 0,
    "e": "Anything that makes the yarn path or the air in the jet unsteady also makes the nip distances unsteady.",
    "sc": 4
   },
   {
    "q": "Why is a multifilament yarn intermingled at all?",
    "a": [
     "For cohesion: the filaments stay together, twisting or sizing is often unnecessary",
     "To make the yarn stronger by real twist",
     "To make the yarn shinier",
     "To make it easier to dye"
    ],
    "c": 0,
    "e": "An intermingled yarn behaves like a closed thread: fewer breaks and less fluff.",
    "sc": 5
   }
  ]
 },
 "es": {
  "ui": {
   "eyebrow": "Knowledge Base · Texturizado",
   "h1": "Cómo se entrelaza un hilo multifilamento",
   "lead": "Del hilo POY en la máquina DTY al hilo entrelazado con sus nudos: cinco escenas cortas que puedes recorrer tú mismo o dejar que se reproduzcan solas.",
   "pressure": "Presión de aire",
   "of": "Sobrealimentación",
   "low": "baja",
   "mid": "media",
   "high": "alta",
   "pause": "⏸ Pausa",
   "play": "▶ Reproducir",
   "scenes": "Escenas",
   "clickHint": "Haz clic en una posición de la máquina: aquí se explica.",
   "fricHint": "(Doble clic: grupo de fricción en detalle)",
   "note": "Representación esquemática. Distancias, número de filamentos y densidad de nudos están simplificados; los valores reales dependen del artículo, la máquina y la tobera.",
   "v2": "R 2 (m/min)",
   "dr": "Estirado",
   "spread": "Dispersión (abajo)"
  },
  "stations": [
   {
    "n": "Bobina de alimentación POY",
    "s": "Bobina POY",
    "d": "Se desenrolla el hilo de poliéster parcialmente orientado (POY) de la hilatura."
   },
   {
    "n": "Rodillo de entrega 1",
    "s": "Rodillo 1",
    "d": "Saca el hilo de la bobina a una velocidad definida."
   },
   {
    "n": "Calentador primario",
    "d": "Calienta el hilo para que pueda estirarse y rizarse."
   },
   {
    "n": "Placa de enfriamiento",
    "d": "Enfría el hilo y así fija el rizado."
   },
   {
    "n": "Unidad de fricción",
    "d": "Discos giratorios generan falsa torsión: el hilo se texturiza y gana volumen."
   },
   {
    "n": "Rodillo de entrega 2",
    "s": "Rodillo 2",
    "d": "Más rápido que el rodillo 1: entre ambos se estira el hilo."
   },
   {
    "n": "Tobera de entrelazado",
    "d": "Tobera Heberlein: el aire comprimido entrelaza los filamentos en nudos."
   },
   {
    "n": "Rodillo de entrega 2.x (OF)",
    "s": "Rodillo 2.x (OF)",
    "d": "Gira un 3–7 % más lento que el rodillo 2. Esta sobrealimentación (OF) da a la tobera material extra para trabajar."
   },
   {
    "n": "Calentador de fijado",
    "s": "Calentador set",
    "d": "Segundo calentador entre el rodillo 2.x y el rodillo 3. Estabiliza el hilo: bajan la contracción residual y la elasticidad (hilo fijado). Sin calentador de fijado el hilo queda muy elástico (hilo HE)."
   },
   {
    "n": "Rodillo de entrega 3",
    "s": "Rodillo 3",
    "d": "Tira del hilo a través del calentador de fijado y lo lleva al bobinado."
   },
   {
    "n": "Bobinado",
    "d": "El hilo DTY terminado se enrolla en una bobina cruzada."
   }
  ],
  "scenes": [
   {
    "k": "Máquina",
    "title": "El recorrido por la máquina DTY",
    "text": "DTY significa Draw Textured Yarn. En una sola pasada, la máquina estira el POY, lo texturiza y al final lo entrelaza. La tobera Heberlein está después de la unidad de fricción, entre el rodillo de entrega 2 y el rodillo 2.x. Como el rodillo 2.x gira un 3–7 % más lento que el rodillo 2, entra más hilo en la tobera del que se saca detrás: esta sobrealimentación (OF) es el material con el que trabaja la tobera.",
    "facts": [
     [
      "Entrada",
      "POY, multifilamento de poliéster parcialmente orientado"
     ],
     [
      "Proceso",
      "estirado, texturizado, entrelazado"
     ],
     [
      "Salida",
      "DTY en bobina cruzada"
     ],
     [
      "Tobera",
      "entre el rodillo 2 y el 2.x"
     ],
     [
      "Sobrealim.",
      "rodillo 2.x 3–7 % más lento que el 2 → material extra para la tobera"
     ],
     [
      "Posiciones",
      "haz clic en ellas en la máquina para ver la explicación"
     ],
     [
      "Prueba",
      "introduce abajo la velocidad de R 2, el estirado y la sobrealimentación: R 1 y R 2.x se calculan en m/min"
     ]
    ]
   },
   {
    "k": "Hilo",
    "title": "Un hilo, muchos filamentos",
    "text": "Un hilo multifilamento está formado por muchos filamentos continuos situados uno al lado del otro. Sin otro tratamiento apenas se mantienen unidos y pueden abrirse durante el procesamiento posterior.",
    "facts": [
     [
      "Ejemplo",
      "167 dtex f48: 48 filamentos"
     ],
     [
      "dtex",
      "masa en gramos por 10 000 m de hilo"
     ],
     [
      "Número f",
      "número de filamentos"
     ],
     [
      "Problema",
      "haz suelto, los filamentos se separan"
     ]
    ]
   },
   {
    "k": "En la tobera",
    "title": "Qué les pasa a los filamentos en la tobera",
    "text": "El hilo pasa por el canal de hilo del núcleo cerámico. A través de un orificio, el aire comprimido golpea el haz en sentido transversal. En la sección del canal se forman dos remolinos que giran en sentidos opuestos: los filamentos se separan y giran en trayectorias circulares. Como el hilo sigue avanzando, los filamentos se tuercen en sentidos opuestos delante y detrás del orificio y se entrelazan formando un nudo. Luego el chorro de aire abre el siguiente tramo y el ciclo vuelve a empezar. El haz solo puede abrirse porque entra suelto en la tobera: para eso sirve la sobrealimentación.",
    "facts": [
     [
      "Estructura",
      "carcasa metálica, núcleo cerámico, canal de hilo, orificio de aire"
     ],
     [
      "Aire",
      "dos remolinos opuestos en el canal"
     ],
     [
      "Filamentos",
      "se abren, giran, se entrelazan"
     ],
     [
      "Sobrealim.",
      "mantiene baja la tensión en la tobera para que el haz se abra"
     ],
     [
      "Prueba",
      "presión de aire y sobrealimentación abajo"
     ]
    ]
   },
   {
    "k": "Nudos",
    "title": "Nudos y tramos abiertos",
    "text": "Detrás de la tobera se alternan regularmente nudos firmes y tramos abiertos. Los nudos dan cohesión al hilo, los tramos abiertos conservan volumen y tacto. El resultado se mide como nudos por metro y estabilidad de los nudos. También importa que los nudos estén repartidos de forma regular: de eso trata la siguiente escena.",
    "facts": [
     [
      "Indicadores",
      "nudos por metro, estabilidad de los nudos, regularidad de las distancias"
     ],
     [
      "Calidad",
      "distancias regulares, nudos estables"
     ],
     [
      "Más presión",
      "más nudos y más firmes, hasta la saturación"
     ],
     [
      "Demasiada",
      "mayor consumo de aire, posibles daños en los filamentos"
     ],
     [
      "Sobrealim.",
      "poca: hilo tenso, menos nudos; mucha: marcha inestable del hilo"
     ]
    ]
   },
   {
    "k": "Regularidad",
    "title": "Muchos nudos no bastan: deben estar repartidos de forma regular",
    "text": "Dos hilos pueden tener el mismo número de nudos igual de estables y aun así comportarse de forma muy distinta. Si los nudos son irregulares, hay acumulaciones y tramos abiertos largos. Ahí el hilo no se mantiene unido: los filamentos se separan, se enganchan en los guiahilos y se rompen. Por eso la calidad depende, además del número y la estabilidad de los nudos, de la dispersión de las distancias entre nudos y del tramo abierto más largo. Con el regulador se cambia la dispersión en el hilo de abajo.",
    "facts": [
     [
      "Mismos nudos/m",
      "no dice nada sobre el reparto"
     ],
     [
      "Indicador",
      "dispersión de distancias entre nudos (CV) y tramo abierto más largo"
     ],
     [
      "Consecuencia",
      "los tramos abiertos se abren: roturas, pelusa, defectos en el tejido"
     ],
     [
      "Causas",
      "tensión del hilo o sobrealimentación variables, tobera sucia o desgastada, presión de aire variable"
     ],
     [
      "Regla",
      "la media sola no basta"
     ]
    ]
   },
   {
    "k": "Comparación",
    "title": "Por qué se entrelaza",
    "text": "Un hilo entrelazado se comporta como un hilo cerrado al tejer, tricotar o bobinar. Los filamentos permanecen juntos, se enganchan menos en las guías y se rompen con menos frecuencia. A menudo se puede prescindir del retorcido o del encolado.",
    "facts": [
     [
      "Cohesión",
      "los filamentos permanecen agrupados"
     ],
     [
      "Procesamiento",
      "menos roturas y pelusa"
     ],
     [
      "Costes",
      "retorcido o encolado a menudo innecesarios"
     ],
     [
      "Regla",
      "sin nudo no hay cohesión"
     ]
    ]
   }
  ],
  "cv": {
   "machine": "Esquema máquina DTY · una posición",
   "drawZone": "Zona de estirado: rodillo 2 más rápido que rodillo 1",
   "ofZone": "Sobrealim. −{of} %",
   "spd": [
    [
     "R 1",
     "= R 2 ÷ {dr}"
    ],
    [
     "R 2",
     "entrada"
    ],
    [
     "R 2.x",
     "= R 2 − {of} % (sobrealim.)"
    ]
   ],
   "xsec": "Sección transversal",
   "filaments": "{n} filamentos",
   "example": "Ejemplo 167 dtex f48",
   "side": "Vista lateral: filamentos paralelos",
   "loose": "filamentos sueltos se separan",
   "long": "Sección longitudinal",
   "pressure": "Presión",
   "yarnRun": "Recorrido del hilo",
   "crimped": "rizado, cerrado",
   "mingled": "entrelazado",
   "leg": [
    [
     "Conexión de aire",
     "aire comprimido de la red"
    ],
    [
     "Orificio de aire",
     "el chorro golpea el hilo en transversal"
    ],
    [
     "Núcleo cerámico",
     "resistente al desgaste y liso"
    ],
    [
     "Canal de hilo",
     "aquí se entrelazan los filamentos"
    ],
    [
     "Salida de aire",
     "el aire sale por ambos lados"
    ],
    [
     "Carcasa",
     "sujeta el núcleo, conduce el aire"
    ]
   ],
   "marked": "tres filamentos marcados para seguir",
   "aa": "Corte A–A: vista dentro del canal",
   "steps": [
    "El nudo sale de la tobera",
    "El chorro abre el haz",
    "Los filamentos giran en dos remolinos",
    "Los filamentos se tuercen en un nudo"
   ],
   "tension": "Tensión del hilo en la tobera",
   "knot": "Nudo",
   "open": "tramo abierto",
   "measure": "Longitud de medición (esquemática)",
   "density": "Densidad de nudos",
   "strength": "Estabilidad de nudos",
   "tryP": "Cambia el regulador \"Presión de aire\"",
   "without": "sin entrelazado",
   "withoutT": "filamentos sueltos, los bucles pueden engancharse",
   "with": "con entrelazado",
   "withT": "los nudos mantienen unido el haz: cohesión",
   "even": "Regular",
   "evenT": "nudos a distancias casi iguales",
   "uneven": "Irregular",
   "unevenT": "mismos nudos, pero huecos y acumulaciones",
   "gap": "tramo abierto largo",
   "distTitle": "Distancias entre nudos",
   "meanL": "media",
   "twice": "2 × media",
   "statKnots": "{n} nudos/m",
   "statCv": "Dispersión de distancias (CV): {cv} %",
   "statGap": "tramo abierto más largo: {g} mm",
   "sameN": "Mismo número de nudos, igual de estables, y aun así otro hilo",
   "now": "Ambos hilos tienen 80 nudos/m. Dispersión de distancias: arriba {a} %, abajo {b} %."
  },
  "quiz": [
   {
    "q": "¿Dónde está la tobera de entrelazado en la máquina DTY?",
    "a": [
     "Entre el rodillo 2 y el rodillo 2.x",
     "Entre el rodillo 1 y el calentador primario",
     "Justo antes del bobinado, después del rodillo 3",
     "Entre la placa de enfriamiento y la unidad de fricción"
    ],
    "c": 0,
    "e": "La tobera está después de la unidad de fricción, entre R 2 y R 2.x.",
    "sc": 0
   },
   {
    "q": "¿Qué significa la sobrealimentación (OF) en la tobera?",
    "a": [
     "El rodillo 2.x gira un 3–7 % más lento que el rodillo 2",
     "El rodillo 2.x gira un 3–7 % más rápido que el rodillo 2",
     "El rodillo 1 gira más rápido que el rodillo 2",
     "La tobera recibe más aire comprimido del necesario"
    ],
    "c": 0,
    "e": "Como R 2.x saca el hilo más despacio, entra más hilo en la tobera del que sale.",
    "sc": 0
   },
   {
    "q": "El rodillo 2 gira a 800 m/min y la sobrealimentación es del 5 %. ¿A qué velocidad gira el rodillo 2.x?",
    "a": [
     "760 m/min",
     "840 m/min",
     "800 m/min",
     "471 m/min"
    ],
    "c": 0,
    "e": "R 2.x = R 2 − 5 % = 800 × 0,95 = 760 m/min.",
    "sc": 0
   },
   {
    "q": "El rodillo 2 gira a 850 m/min y el estirado es 1,70. ¿A qué velocidad gira el rodillo 1?",
    "a": [
     "500 m/min",
     "1445 m/min",
     "850 m/min",
     "808 m/min"
    ],
    "c": 0,
    "e": "R 1 = R 2 ÷ estirado = 850 ÷ 1,70 = 500 m/min.",
    "sc": 0
   },
   {
    "q": "¿Qué significa «167 dtex f48»?",
    "a": [
     "167 g por 10 000 m de hilo, formado por 48 filamentos",
     "167 filamentos de 48 dtex cada uno",
     "167 nudos por metro a 48 m/min",
     "48 g por 167 m de hilo"
    ],
    "c": 0,
    "e": "dtex es la masa en gramos por 10 000 m, el número f la cantidad de filamentos.",
    "sc": 1
   },
   {
    "q": "¿Qué ocurre en el canal de hilo de la tobera?",
    "a": [
     "El aire transversal forma dos remolinos opuestos y los filamentos se entrelazan en nudos",
     "El aire tuerce todo el hilo de forma permanente, como al retorcer",
     "El aire enfría el hilo después del calentador",
     "El aire corta los filamentos sueltos"
    ],
    "c": 0,
    "e": "Los filamentos se separan, giran y se tuercen antes y después del orificio formando un nudo.",
    "sc": 2
   },
   {
    "q": "¿Por qué necesita la tobera la sobrealimentación?",
    "a": [
     "El hilo llega flojo y así el haz se puede abrir",
     "Para que el hilo vaya más rápido",
     "Para que el hilo se estire en la tobera",
     "Para que la tobera consuma menos aire"
    ],
    "c": 0,
    "e": "Un hilo tenso apenas se abre. La sobrealimentación mantiene baja la tensión en la tobera.",
    "sc": 2
   },
   {
    "q": "¿Cómo se mide el resultado del entrelazado?",
    "a": [
     "Nudos por metro, estabilidad de los nudos y regularidad de las distancias",
     "Título del hilo en dtex",
     "Consumo de aire de la tobera",
     "Número de filamentos"
    ],
    "c": 0,
    "e": "Los indicadores son la densidad de nudos (nudos por metro), su estabilidad y la regularidad de las distancias entre nudos.",
    "sc": 3
   },
   {
    "q": "¿Qué pasa si se aumenta mucho la presión de aire?",
    "a": [
     "Más nudos y más firmes hasta la saturación, pero más consumo de aire",
     "Se forman menos nudos",
     "El hilo se vuelve más fino",
     "La sobrealimentación sube automáticamente"
    ],
    "c": 0,
    "e": "Más presión da más nudos y más firmes hasta la saturación. Demasiada presión gasta aire y puede dañar filamentos.",
    "sc": 3
   },
   {
    "q": "Dos hilos tienen el mismo número de nudos igual de estables. ¿Qué puede hacer que uno sea peor?",
    "a": [
     "Los nudos están repartidos de forma irregular, con tramos abiertos largos",
     "Tiene más filamentos",
     "Se procesó con calentador de fijado",
     "Los nudos están a distancias demasiado iguales"
    ],
    "c": 0,
    "e": "En los tramos abiertos largos el hilo no se mantiene unido. El número y la estabilidad de los nudos no dicen nada sobre el reparto.",
    "sc": 4
   },
   {
    "q": "¿Cómo se reconoce un entrelazado irregular en la medición?",
    "a": [
     "Gran dispersión de las distancias entre nudos (CV alto) y tramos abiertos largos",
     "Por una alta estabilidad de los nudos",
     "Por un título bajo",
     "Por un alto consumo de aire"
    ],
    "c": 0,
    "e": "Además de la media (nudos/m), cuentan la dispersión de las distancias y el tramo abierto más largo.",
    "sc": 4
   },
   {
    "q": "¿Qué puede causar distancias irregulares entre nudos?",
    "a": [
     "Tensión del hilo o sobrealimentación variables, tobera sucia o desgastada, presión de aire variable",
     "El color del POY",
     "La bobina cruzada en el bobinado",
     "Una temperatura ambiente demasiado baja en el laboratorio"
    ],
    "c": 0,
    "e": "Todo lo que hace inestable el recorrido del hilo o el aire en la tobera hace también irregulares las distancias entre nudos.",
    "sc": 4
   },
   {
    "q": "¿Por qué se entrelaza un hilo multifilamento?",
    "a": [
     "Por cohesión: los filamentos se mantienen juntos y a menudo no hace falta retorcer ni encolar",
     "Para que sea más resistente por torsión real",
     "Para que sea más brillante",
     "Para que se tiña mejor"
    ],
    "c": 0,
    "e": "Un hilo entrelazado se comporta como un hilo cerrado: menos roturas y menos pelusa.",
    "sc": 5
   }
  ]
 },
 "zh": {
  "ui": {
   "eyebrow": "知识库 · 加弹",
   "h1": "复丝是如何被网络（交缠）的",
   "lead": "从加弹机上的 POY 原丝到带网络点的网络丝：五个短场景，可以自己点击浏览，也可以自动播放。",
   "pressure": "气压",
   "of": "超喂",
   "low": "低",
   "mid": "中",
   "high": "高",
   "pause": "⏸ 暂停",
   "play": "▶ 播放",
   "scenes": "场景",
   "clickHint": "点击机器上的某个位置，这里会显示说明。",
   "fricHint": "（双击：摩擦假捻器详解）",
   "note": "示意图。距离、单丝数量和网络点密度均为简化表示；实际数值取决于品种、机器和喷嘴。",
   "v2": "罗拉 2 (m/min)",
   "dr": "拉伸比",
   "spread": "离散度（下）"
  },
  "stations": [
   {
    "n": "POY 原丝筒",
    "d": "从纺丝厂来的预取向涤纶丝（POY）被退绕。"
   },
   {
    "n": "第一罗拉",
    "d": "以设定的速度将丝从丝筒上引出。"
   },
   {
    "n": "第一热箱",
    "d": "加热丝条，使其能够拉伸和卷曲。"
   },
   {
    "n": "冷却板",
    "d": "冷却丝条，从而定型卷曲。"
   },
   {
    "n": "摩擦假捻器",
    "d": "旋转的摩擦盘产生假捻：丝条被变形并变得蓬松。"
   },
   {
    "n": "第二罗拉",
    "d": "比第一罗拉快：两者之间丝条被拉伸。"
   },
   {
    "n": "网络喷嘴",
    "d": "Heberlein 喷嘴：压缩空气使单丝交缠，形成网络点。"
   },
   {
    "n": "罗拉 2.x（超喂）",
    "d": "比第二罗拉慢 3–7 %。这个超喂（OF）为喷嘴提供额外的丝量。"
   },
   {
    "n": "定型热箱",
    "d": "位于罗拉 2.x 和罗拉 3 之间的第二热箱。它使丝条稳定：残余收缩和弹性降低（定型丝）。没有定型热箱时丝保持高弹（高弹丝）。"
   },
   {
    "n": "第三罗拉",
    "d": "牵引丝条通过定型热箱，并送往卷绕。",
    "s": "罗拉 3"
   },
   {
    "n": "卷绕",
    "d": "加工好的 DTY 丝被卷绕成交叉卷绕筒子。"
   }
  ],
  "scenes": [
   {
    "k": "机器",
    "title": "丝在加弹机上的路径",
    "text": "DTY 是 Draw Textured Yarn（拉伸变形丝）的缩写。加弹机在一道工序中对 POY 进行拉伸、变形，最后进行网络。Heberlein 喷嘴位于摩擦假捻器之后、第二罗拉与罗拉 2.x 之间。由于罗拉 2.x 比第二罗拉慢 3–7 %，进入喷嘴的丝比后面引出的多：这个超喂（OF）就是喷嘴工作所需的丝量。",
    "facts": [
     [
      "输入",
      "POY，预取向涤纶复丝"
     ],
     [
      "工艺",
      "拉伸、变形、网络"
     ],
     [
      "输出",
      "交叉卷绕筒子上的 DTY"
     ],
     [
      "喷嘴",
      "位于第二罗拉和罗拉 2.x 之间"
     ],
     [
      "超喂",
      "罗拉 2.x 比第二罗拉慢 3–7 % → 喷嘴获得额外丝量"
     ],
     [
      "位置",
      "点击机器上的位置即可查看说明"
     ],
     [
      "试一试",
      "在下方输入罗拉 2 速度、拉伸比和超喂：自动计算罗拉 1 和罗拉 2.x 的速度（m/min）"
     ]
    ]
   },
   {
    "k": "丝条",
    "title": "一根丝，许多单丝",
    "text": "复丝由许多平行排列的连续单丝组成。如不经进一步处理，它们几乎不能抱合在一起，在后续加工中容易散开。",
    "facts": [
     [
      "示例",
      "167 dtex f48：48 根单丝"
     ],
     [
      "dtex",
      "每 10 000 米丝的克重"
     ],
     [
      "f 数",
      "单丝根数"
     ],
     [
      "问题",
      "丝束松散，单丝散开"
     ]
    ]
   },
   {
    "k": "喷嘴内",
    "title": "单丝在喷嘴里发生了什么",
    "text": "丝条穿过陶瓷喷嘴芯中的纱道。压缩空气通过进气孔横向冲击丝束。在纱道截面内形成两个方向相反的涡流：单丝被吹散，并沿圆形轨迹旋转。由于丝条持续前进，进气孔前后的单丝向相反方向加捻，并交缠成一个网络点。随后气流打开下一段，循环重新开始。丝束之所以能被打开，是因为它以松弛状态进入喷嘴：这正是超喂的作用。",
    "facts": [
     [
      "结构",
      "金属外壳、陶瓷喷嘴芯、纱道、进气孔"
     ],
     [
      "气流",
      "纱道内两个反向涡流"
     ],
     [
      "单丝",
      "打开、旋转、交缠"
     ],
     [
      "超喂",
      "使喷嘴内张力保持较低，丝束才能打开"
     ],
     [
      "试一试",
      "在下方调整气压和超喂"
     ]
    ]
   },
   {
    "k": "网络点",
    "title": "网络点和开放段",
    "text": "喷嘴之后，牢固的网络点与开放段有规律地交替出现。网络点使丝条抱合，开放段保持蓬松度和手感。结果以每米网络点数（网络度）和网络点牢度来衡量。网络点分布是否均匀同样重要：这是下一个场景的主题。",
    "facts": [
     [
      "指标",
      "每米网络点数、网络点牢度、间距均匀性"
     ],
     [
      "质量",
      "间距均匀，网络点牢固"
     ],
     [
      "气压更高",
      "网络点更多、更牢，直至饱和"
     ],
     [
      "过高",
      "耗气量增加，可能损伤单丝"
     ],
     [
      "超喂",
      "过小：丝条太紧，网络点少；过大：丝条运行不稳"
     ]
    ]
   },
   {
    "k": "均匀性",
    "title": "网络点多还不够：必须分布均匀",
    "text": "两种丝可以有相同数量、相同牢度的网络点，表现却截然不同。网络点分布不均时，会出现扎堆和很长的开放段。在那里丝抱合不住：单丝散开、挂在导丝器上并断裂。因此质量除了取决于网络点数和牢度，还取决于网络点间距的离散和最长的开放段。可用滑块改变下方丝的离散度。",
    "facts": [
     [
      "每米点数相同",
      "不说明分布情况"
     ],
     [
      "指标",
      "网络点间距离散（CV）和最长开放段"
     ],
     [
      "后果",
      "开放段散开：断头、毛丝、织物疵点"
     ],
     [
      "原因",
      "丝条张力或超喂波动、喷嘴脏污或磨损、气压波动"
     ],
     [
      "要点",
      "只看平均值不够"
     ]
    ]
   },
   {
    "k": "对比",
    "title": "为什么要网络",
    "text": "网络丝在织造、针织或络筒时表现得像一根抱合的丝。单丝保持在一起，较少挂在导丝器上，也较少断裂。因此常常可以省去加捻或上浆。",
    "facts": [
     [
      "抱合",
      "单丝保持成束"
     ],
     [
      "加工",
      "断头和毛丝更少"
     ],
     [
      "成本",
      "常可省去加捻或上浆"
     ],
     [
      "要点",
      "没有网络点，就没有抱合"
     ]
    ]
   }
  ],
  "cv": {
   "machine": "加弹机示意 · 一个锭位",
   "drawZone": "拉伸区：第二罗拉比第一罗拉快",
   "ofZone": "超喂 −{of} %",
   "spd": [
    [
     "罗拉 1",
     "= 罗拉 2 ÷ {dr}"
    ],
    [
     "罗拉 2",
     "输入"
    ],
    [
     "罗拉 2.x",
     "= 罗拉 2 − {of} %（超喂）"
    ]
   ],
   "xsec": "横截面",
   "filaments": "{n} 根单丝",
   "example": "示例 167 dtex f48",
   "side": "侧视：单丝平行排列",
   "loose": "松散的单丝散开",
   "long": "纵剖面",
   "pressure": "压力",
   "yarnRun": "走丝方向",
   "crimped": "卷曲、闭合",
   "mingled": "已网络",
   "leg": [
    [
     "进气接口",
     "来自车间管网的压缩空气"
    ],
    [
     "进气孔",
     "气流横向冲击丝条"
    ],
    [
     "陶瓷喷嘴芯",
     "耐磨且光滑"
    ],
    [
     "纱道",
     "单丝在这里被网络"
    ],
    [
     "排气",
     "空气从两侧排出"
    ],
    [
     "外壳",
     "固定喷嘴芯并导入空气"
    ]
   ],
   "marked": "三根标记的单丝，便于追踪",
   "aa": "A–A 剖面：看向纱道内部",
   "steps": [
    "网络点离开喷嘴",
    "气流打开丝束",
    "单丝在两个涡流中旋转",
    "单丝加捻形成网络点"
   ],
   "tension": "喷嘴内丝条张力",
   "knot": "网络点",
   "open": "开放段",
   "measure": "测量长度（示意）",
   "density": "网络点密度",
   "strength": "网络点牢度",
   "tryP": "调整“气压”滑块",
   "without": "未网络",
   "withoutT": "单丝松散，丝圈容易挂住",
   "with": "已网络",
   "withT": "网络点使丝束抱合在一起",
   "even": "均匀",
   "evenT": "网络点间距几乎相等",
   "uneven": "不均匀",
   "unevenT": "网络点数相同，但有空档和扎堆",
   "gap": "长的开放段",
   "distTitle": "网络点间距",
   "meanL": "平均值",
   "twice": "2 × 平均",
   "statKnots": "{n} 个网络点/米",
   "statCv": "间距离散（CV）：{cv} %",
   "statGap": "最长开放段：{g} mm",
   "sameN": "网络点数相同、牢度相同——却是不同的丝",
   "now": "两种丝都是每米 80 个网络点。间距离散：上 {a} %，下 {b} %。"
  },
  "quiz": [
   {
    "q": "网络喷嘴位于加弹机的什么位置？",
    "a": [
     "第二罗拉和罗拉 2.x 之间",
     "第一罗拉和第一热箱之间",
     "卷绕前、第三罗拉之后",
     "冷却板和摩擦假捻器之间"
    ],
    "c": 0,
    "e": "喷嘴位于摩擦假捻器之后，罗拉 2 和罗拉 2.x 之间。",
    "sc": 0
   },
   {
    "q": "喷嘴处的超喂（OF）是什么意思？",
    "a": [
     "罗拉 2.x 比第二罗拉慢 3–7 %",
     "罗拉 2.x 比第二罗拉快 3–7 %",
     "第一罗拉比第二罗拉快",
     "喷嘴获得的压缩空气多于所需"
    ],
    "c": 0,
    "e": "由于罗拉 2.x 引出较慢，进入喷嘴的丝比离开的多。",
    "sc": 0
   },
   {
    "q": "第二罗拉速度为 800 m/min，超喂为 5 %。罗拉 2.x 的速度是多少？",
    "a": [
     "760 m/min",
     "840 m/min",
     "800 m/min",
     "471 m/min"
    ],
    "c": 0,
    "e": "罗拉 2.x = 罗拉 2 − 5 % = 800 × 0.95 = 760 m/min。",
    "sc": 0
   },
   {
    "q": "第二罗拉速度为 850 m/min，拉伸比为 1.70。第一罗拉的速度是多少？",
    "a": [
     "500 m/min",
     "1445 m/min",
     "850 m/min",
     "808 m/min"
    ],
    "c": 0,
    "e": "罗拉 1 = 罗拉 2 ÷ 拉伸比 = 850 ÷ 1.70 = 500 m/min。",
    "sc": 0
   },
   {
    "q": "“167 dtex f48”是什么意思？",
    "a": [
     "每 10 000 米丝重 167 克，由 48 根单丝组成",
     "167 根单丝，每根 48 dtex",
     "每米 167 个网络点，速度 48 m/min",
     "每 167 米丝重 48 克"
    ],
    "c": 0,
    "e": "dtex 是每 10 000 米的克重，f 数是单丝根数。",
    "sc": 1
   },
   {
    "q": "喷嘴的纱道里发生了什么？",
    "a": [
     "横向气流形成两个反向涡流，单丝交缠成网络点",
     "空气像加捻一样使整根丝永久加捻",
     "空气在热箱后冷却丝条",
     "空气切断松散的单丝"
    ],
    "c": 0,
    "e": "单丝被分开、旋转，并在气孔前后扭结成一个网络点。",
    "sc": 2
   },
   {
    "q": "喷嘴为什么需要超喂？",
    "a": [
     "丝条松弛地进入，丝束才能打开",
     "让丝走得更快",
     "让丝在喷嘴中被拉伸",
     "让喷嘴耗气更少"
    ],
    "c": 0,
    "e": "绷紧的丝几乎打不开。超喂使喷嘴内的张力保持较低。",
    "sc": 2
   },
   {
    "q": "网络效果如何测量？",
    "a": [
     "每米网络点数、网络点牢度和间距均匀性",
     "以 dtex 表示的纤度",
     "喷嘴的耗气量",
     "单丝根数"
    ],
    "c": 0,
    "e": "指标是网络度（每米网络点数）、网络点牢度和网络点间距的均匀性。",
    "sc": 3
   },
   {
    "q": "大幅提高气压会怎样？",
    "a": [
     "网络点更多更牢，直至饱和，但耗气量增加",
     "网络点变少",
     "丝变细",
     "超喂自动增加"
    ],
    "c": 0,
    "e": "压力越高，网络点越多越牢，直至饱和。压力过高会浪费空气并可能损伤单丝。",
    "sc": 3
   },
   {
    "q": "两种丝的网络点数量和牢度都相同。什么仍可能使其中一种更差？",
    "a": [
     "网络点分布不均，有很长的开放段",
     "它的单丝更多",
     "它经过了定型热箱",
     "网络点间距过于相等"
    ],
    "c": 0,
    "e": "在长的开放段丝抱合不住。网络点数和牢度本身不能说明分布情况。",
    "sc": 4
   },
   {
    "q": "测量时如何识别网络不均匀？",
    "a": [
     "网络点间距离散大（CV 高）且有长的开放段",
     "网络点牢度高",
     "纤度低",
     "耗气量高"
    ],
    "c": 0,
    "e": "除了平均值（每米点数），间距离散和最长开放段同样重要。",
    "sc": 4
   },
   {
    "q": "什么会导致网络点间距不均匀？",
    "a": [
     "丝条张力或超喂波动、喷嘴脏污或磨损、气压波动",
     "POY 的颜色",
     "卷绕时的交叉卷绕筒子",
     "实验室室温过低"
    ],
    "c": 0,
    "e": "凡是使走丝或喷嘴内气流不稳定的因素，也会使网络点间距不稳定。",
    "sc": 4
   },
   {
    "q": "为什么要对复丝进行网络？",
    "a": [
     "为了抱合：单丝保持在一起，常可省去加捻或上浆",
     "通过真捻使丝更结实",
     "使丝更有光泽",
     "使丝更易染色"
    ],
    "c": 0,
    "e": "网络丝的表现像一根闭合的丝：断头和毛丝更少。",
    "sc": 5
   }
  ]
 }
};
