window.TEXTS = {
 "de": {
  "ui": {
   "eyebrow": "Knowledge Base · Stapelfaserspinnerei",
   "h1": "Stapelfaserspinnerei: von der Faserflocke zum Garn",
   "lead": "Baumwolle und andere Stapelfasern durchlaufen eine lange Kette, bevor sie Garn sind: öffnen, reinigen, mischen, kardieren, strecken, je nach Qualität kämmen, zu Vorgarn verziehen und schliesslich verspinnen. Diese Seite zeigt die Verfahren und ihre Technik als animierte Schemata mit Schritt-für-Schritt-Steuerung – von der Ballenöffnung bis zu Ring-, Kompakt-, Rotor- und Luftspinnen. Maschinen und Hersteller bleiben bewusst aussen vor.",
   "note": "Die Darstellungen sind stark vereinfacht. Werte aus Lehrunterlagen und Fachartikeln; sie streuen je nach Faser, Feinheit und Quelle.",
   "sources": "Quellen",
   "open": "Modul öffnen",
   "loc": "de-CH",
   "prev": "◀ Schritt zurück",
   "next": "Schritt vor ▶",
   "play": "▶ Abspielen",
   "pause": "Pause",
   "lkL": "Weiter in der Knowledge Base",
   "how": "Ziel und Ablauf",
   "figs": "Prozessgrössen",
   "pro": "Stärken",
   "con": "Grenzen",
   "when": "Wann?"
  },
  "kpis": [
   [
    "≈ 40 000",
    "Fasern im Querschnitt eines Kardenbandes"
   ],
   [
    "6–8",
    "Bänder werden an der Strecke doubliert"
   ],
   [
    "8–25 %",
    "Kämmling (ausgekämmte Kurzfasern), je nach Ziel"
   ],
   [
    "bis 150 000",
    "U/min eines Spinnrotors"
   ],
   [
    "15–27 vs. 450",
    "m/min Liefergeschwindigkeit Ring- vs. Luftspinnen"
   ]
  ],
  "scenes": [
   {
    "k": "Prozesslinien",
    "title": "Prozesslinien der Kurzstapelspinnerei",
    "text": "Welche Schritte ein Garn durchläuft, hängt vom Spinnverfahren und der gewünschten Qualität ab. Wähle eine Linie – die beteiligten Stufen werden hervorgehoben. Klick auf eine Stufe öffnet ihre Animation."
   },
   {
    "k": "Verfahren im Detail",
    "title": "Die Verfahren im Detail",
    "text": "Jedes Schema lässt sich abspielen oder schrittweise vor- und zurückschalten. Die Darstellungen sind stark vereinfacht."
   },
   {
    "k": "Spinnverfahren im Vergleich",
    "title": "Spinnverfahren im Vergleich",
    "text": "Vier Verfahren, vier Garnstrukturen. Die Skizzen zeigen schematisch, wie die Fasern im Garn liegen."
   },
   {
    "k": "Drehung und Tempo",
    "title": "Drehung und Tempo: warum Ringspinnen langsam ist",
    "text": "Bei Ring- und Rotorspinnen gilt dieselbe Grundbeziehung: Drehung (T/m) = Drehzahl (U/min) ÷ Liefergeschwindigkeit (m/min). Für eine gewünschte Drehung bestimmt also die Drehzahl des drehenden Organs das Tempo. Beim Ring begrenzt die Läufergeschwindigkeit die Spindeldrehzahl, beim Rotor dreht ein kleiner Becher ohne Kops."
   },
   {
    "k": "Exkurs Wolle",
    "title": "Exkurs Wolle: Kammgarn, Streichgarn, Halbkammgarn",
    "text": "Für Wolle gibt es eigene Linien, die sich vor allem in der Vorbereitung unterscheiden."
   }
  ],
  "route": {
   "seg": [
    "Ringgarn kardiert",
    "Ringgarn gekämmt",
    "Rotorgarn",
    "Luftspinngarn"
   ],
   "nodes": {
    "putzerei": "Putzerei",
    "karde": "Karde",
    "strecke1": "Vorstrecke",
    "kvor": "Kämmerei-Vorbereitung",
    "kaemmen": "Kämmen",
    "strecke": "Endstrecke",
    "flyer": "Flyer",
    "ring": "Ring / Kompakt",
    "rotor": "Rotorspinnen",
    "luft": "Luftspinnen"
   },
   "txt": [
    "Kardiertes Ringgarn: Putzerei, Karde, zwei Streckenpassagen, Flyer, Ringspinnen.",
    "Gekämmtes Ringgarn: nach der Karde Kämmereivorbereitung (Wickel) und Kämmen, dann Endstrecke, Flyer und Ringspinnen.",
    "Rotorgarn: kurze Linie – nach Karde und Strecke direkt ab Band auf die Rotorspinnmaschine, ohne Flyer.",
    "Luftspinngarn: Karde, meist zwei Streckenpassagen (bei Bedarf auch gekämmt), dann direkt ab Band auf die Luftspinnmaschine."
   ]
  },
  "proc": [
   {
    "n": "Putzerei",
    "de": "Ballen öffnen, reinigen, mischen, entstauben",
    "st": [
     "1 · Ballenabtragen: kleine Flocken von allen Ballen gleichzeitig",
     "2 · Pneumatischer Transport",
     "3 · Reinigen: Schlagwalze öffnet, Schmutz fällt durch den Rost",
     "4 · Mischen in versetzt befüllten Kammern",
     "5 · Entstauben, Speisung der Karden"
    ],
    "cap": [
     "Kleine Flocken von allen Ballen gleichzeitig",
     "Flocken fliegen im Luftstrom weiter",
     "Öffnen und Reinigen: Schmutz fällt durch den Rost",
     "Mischen: Kammern versetzt füllen, gemeinsam leeren",
     "Gleichmässige Watte für die Karde"
    ],
    "lab": {
     "bales": "Ballenreihe (verschiedene Herkünfte)",
     "pluck": "Ballenabtragen",
     "clean": "Reiniger: Schlagwalze + Rost",
     "mix": "Mischer: Kammern",
     "chute": "Schachtspeiser → Karde"
    },
    "how": [
     "Gepresste Ballen werden in kleine Flocken zerlegt – je kleiner die Flocke, desto grösser ihre Oberfläche und desto leichter fällt der Schmutz heraus.",
     "Schlag- und Stachelwalzen über Rosten öffnen die Flocken weiter; schwere Teilchen fallen durch, Staub geht mit dem Luftstrom.",
     "Mischer gleichen Herkunfts- und Qualitätsunterschiede der Ballen aus.",
     "Am Ende speist ein Schachtspeiser jede Karde mit einer gleichmässigen Watte."
    ],
    "figs": [
     [
      "200 kg → ~10 g",
      "Ballen → Flocke beim Ballenabtragen"
     ],
     [
      "100–200 mg",
      "angestrebte Flockengrösse nach dem Vorreinigen (Lehrbuchwert)"
     ],
     [
      "95–99 %",
      "Verunreinigungen, die Putzerei und Karde zusammen entfernen"
     ]
    ],
    "pro": [
     "Grundlage für Sauberkeit und gleichmässige Mischung",
     "Schonendes, stufenweises Öffnen"
    ],
    "con": [
     "Hoher Reinigungsgrad kostet fast immer Gutfasern",
     "Jeder Schlag beansprucht die Fasern und kann Nissen erzeugen"
    ],
    "when": "Immer bei Baumwolle; Chemiefasern brauchen kaum Reinigung, aber Öffnen und Mischen."
   },
   {
    "n": "Karde",
    "de": "Fasern vereinzeln, Nissen und Restschmutz entfernen, Band bilden",
    "st": [
     "1 · Watte zuführen und klemmen",
     "2 · Vorreisser öffnet, Schmutz wird abgeschieden",
     "3 · Kardieren zwischen Tambour und Deckeln",
     "4 · Abnehmer übernimmt den Flor",
     "5 · Band bilden und in die Kanne ablegen"
    ],
    "cap": [
     "Watte wird zugeführt und geklemmt",
     "Vorreisser: Flocken öffnen, Schmutz abscheiden",
     "Kardieren zwischen Tambour und Deckeln: Einzelfasern",
     "Abnehmer bildet einen feinen Flor",
     "Flor → Band → Kanne"
    ],
    "lab": {
     "chute": "Schacht",
     "flats": "Wanderdeckel",
     "cyl": "Tambour (Trommel)",
     "doffer": "Abnehmer",
     "can": "Kanne",
     "licker": "Vorreisser",
     "feed": "Speisewalze"
    },
    "how": [
     "Die Speisewalze klemmt die Watte, der Vorreisser öffnet sie zu kleinen Flocken.",
     "Zwischen Tambour und Wanderdeckeln stehen sich die Garniturspitzen gegenüber (Spitze gegen Spitze) – die Flocken werden zu Einzelfasern aufgelöst, Nissen und Schmutz bleiben in den Deckeln hängen.",
     "Der langsamere Abnehmer übernimmt die Fasern als dünnen Flor.",
     "Ein Trichter verdichtet den Flor zum unverdrehten Kardenband, das in eine Kanne abgelegt wird."
    ],
    "figs": [
     [
      "≈ 40 000",
      "Fasern im Bandquerschnitt"
     ],
     [
      "≈ 1 %",
      "Kurzfasern, die die Karde entfernt"
     ],
     [
      "80–116",
      "Deckelstäbe, davon 30–46 im Eingriff"
     ],
     [
      "„Gut kardiert …“",
      "… ist halb gesponnen (Spinnerweisheit)"
     ]
    ],
    "pro": [
     "Einzige Stufe, die Fasern wirklich vereinzelt",
     "Entfernt Nissen, Staub und einen Teil der Kurzfasern"
    ],
    "con": [
     "Fasern liegen noch kaum parallel, viele als Haken",
     "Bandgleichmässigkeit noch ungenügend"
    ],
    "when": "In jeder Kurzstapellinie."
   },
   {
    "n": "Strecke",
    "de": "Doublieren und Verziehen: gleichmässiger, paralleler",
    "st": [
     "1 · 6–8 Bänder vorlegen (Doublieren)",
     "2 · Dicke messen (Regulierung)",
     "3 · Verzug im Streckwerk",
     "4 · Parallelisieren, Ausgleichen",
     "5 · Band in die Kanne"
    ],
    "cap": [
     "Doublieren: mehrere Bänder zusammen vorlegen",
     "Dicke messen für die Regulierung",
     "Verzug: v1 < v2 < v3",
     "Fasern parallel, Schwankungen mitteln sich aus",
     "Ein gleichmässiges Band in die Kanne"
    ],
    "lab": {
     "cans": "6 Kannen = 6 Kardenbänder (Doublierung)",
     "meas": "Messung",
     "v3": "v3 (schnellste)",
     "can": "Kanne",
     "thickA": "Dicke je Einzelband: schwankt",
     "thickB": "Dicke Streckenband: ausgeglichen"
    },
    "how": [
     "Mehrere Bänder werden zusammen vorgelegt: Dick- und Dünnstellen mitteln sich aus (Doublierung). Dabei lassen sich auch Fasern mischen, z. B. Baumwolle/Polyester.",
     "Im Streckwerk läuft jedes Walzenpaar schneller als das vorherige – das Band wird verzogen, die Fasern gestreckt und parallel gelegt.",
     "Doublierung und Verzug sind meist etwa gleich gross, damit das Band ähnlich dick bleibt.",
     "Eine Regulierung misst die Banddicke und passt den Verzug laufend an."
    ],
    "figs": [
     [
      "6–8",
      "doublierte Bänder"
     ],
     [
      "4–8",
      "Verzug"
     ],
     [
      "350–800 m/min",
      "Liefergeschwindigkeit"
     ],
     [
      "CV 4–6 % → 1–2 %",
      "Bandungleichmässigkeit mit Regulierung"
     ]
    ],
    "pro": [
     "Wichtigste Stufe für die Gleichmässigkeit",
     "Ideal zum Mischen verschiedener Fasern"
    ],
    "con": [
     "Gleicht nur kurz- und mittelwellige Schwankungen gut aus",
     "Mehrere Passagen nötig (Vor- und Endstrecke)"
    ],
    "when": "In allen Linien – meist zweimal."
   },
   {
    "n": "Kämmerei",
    "de": "Kurzfasern und Nissen auskämmen – für feinere, glattere Garne",
    "st": [
     "1 · Zuführen, Zange klemmt",
     "2 · Rundkamm kämmt den Faserbart",
     "3 · Zange öffnet und fährt vor – Anlegen",
     "4 · Abreissen durch den Fixkamm",
     "5 · Zange zurück, neuer Zyklus"
    ],
    "cap": [
     "Zuführen: Zange klemmt den Wickel",
     "Rundkamm kämmt den Faserbart – Kurzfasern und Nissen raus",
     "Zange öffnet und fährt vor, Abreisswalzen laufen zurück: Anlegen",
     "Abreissen: Faserbart wird durch den Fixkamm gezogen",
     "Zange zurück – neuer Zyklus"
    ],
    "lab": {
     "lap": "Wickel",
     "open": "Zange offen",
     "closed": "Zange geschlossen",
     "circ": "Rundkamm",
     "top": "Fixkamm",
     "detach": "Abreisswalzen",
     "sliver": "gekämmtes Band",
     "noil": "Kämmling (Absaugung)"
    },
    "how": [
     "Vorbereitung: Kardenbänder werden zu einem Wickel gelegt, damit die Fasern geordnet zugeführt werden.",
     "Die Zange klemmt den Wickel, ein Rundkamm kämmt den vorstehenden Faserbart – was nicht geklemmt ist (Kurzfasern, Nissen), bleibt im Kamm.",
     "Die Zange fährt vor, der gekämmte Bart wird an das vorherige Vlies angelegt und von den Abreisswalzen durch einen Fixkamm gezogen, der das hintere Ende kämmt.",
     "Der Kämmling wird abgesaugt; die Vliese werden zu einem gekämmten Band zusammengeführt."
    ],
    "figs": [
     [
      "8–25 %",
      "Kämmling, je nach Ziel"
     ],
     [
      "Kämmling %",
      "= Kämmling ÷ zugeführte Masse × 100"
     ],
     [
      "taktweise",
      "Kämmzyklus statt kontinuierlich"
     ]
    ],
    "pro": [
     "Feinere, glattere, festere und gleichmässigere Garne",
     "Weniger Nissen, besserer Glanz"
    ],
    "con": [
     "Materialverlust (Kämmling)",
     "Zusätzliche Stufen und Kosten"
    ],
    "when": "Feine, hochwertige Baumwollgarne (Hemden, Feinstrick)."
   },
   {
    "n": "Flyer",
    "de": "Band zu Vorgarn verziehen und mit Schutzdrehung aufspulen",
    "st": [
     "1 · Band aus der Kanne",
     "2 · Verzug auf dünnes Vorgarn",
     "3 · Flügel gibt Schutzdrehung",
     "4 · Aufwinden auf die Spule"
    ],
    "cap": [
     "Band aus der Kanne",
     "Verzug auf ein dünnes Vorgarn",
     "Flügel gibt Schutzdrehung (25–70 T/m)",
     "Aufwinden auf die Flyerspule"
    ],
    "lab": {
     "can": "Streckenband",
     "draft": "Streckwerk (Verzug 5–20)",
     "flyer": "Flügel dreht",
     "rail": "Spulenwagen hebt/senkt"
    },
    "how": [
     "Das Streckenband ist zu dick für den Verzug der Ringspinnmaschine, und Kannen sind ein schlechtes Vorlageformat.",
     "Der Flyer verzieht das Band auf ein dünnes Vorgarn.",
     "Ein Flügel dreht um die Spule und gibt eine leichte Schutzdrehung – genug, damit das Vorgarn hält, aber so wenig, dass es sich später wieder verziehen lässt.",
     "Die Spule läuft etwas schneller als der Flügel; der Spulenwagen hebt und senkt sich für den Aufbau."
    ],
    "figs": [
     [
      "5–20",
      "Verzug am Flyer"
     ],
     [
      "25–70 T/m",
      "Schutzdrehung"
     ],
     [
      "T/m",
      "= Flügeldrehzahl ÷ Liefergeschwindigkeit"
     ],
     [
      "20–25 m/min",
      "übliche Lieferung (Patentangabe)"
     ]
    ],
    "pro": [
     "Passendes Vorlagematerial für die Ringspinnmaschine"
    ],
    "con": [
     "Aufwendiger Wickelmechanismus",
     "Zu viel Drehung stört den Verzug, zu wenig führt zu Fehlverzügen und Brüchen"
    ],
    "when": "Nur für Ring- und Kompaktspinnen – Rotor- und Luftspinnen arbeiten direkt ab Band."
   },
   {
    "n": "Ringspinnen",
    "de": "Verzug, Drehung über Spindel und Läufer, Aufwinden auf den Kops",
    "v": [
     "konventionell",
     "kompakt"
    ],
    "st": [
     "1 · Verzug im Streckwerk",
     "2 · Spinndreieck / Verdichtung",
     "3 · Drehung über Spindel und Läufer",
     "4 · Aufwinden auf den Kops"
    ],
    "cap": [
     "Verzug im Streckwerk",
     "Spinndreieck: Hier wird gedreht – Randfasern stehen ab",
     "Spindel dreht, Läufer läuft mit: Drehung",
     "Aufwinden auf den Kops"
    ],
    "capC": [
     "Verzug im Streckwerk",
     "Verdichtung: Spinndreieck fast verschwunden",
     "Spindel dreht, Läufer läuft mit: Drehung",
     "Aufwinden auf den Kops"
    ],
    "lab": {
     "bobbin": "Vorgarnspule",
     "draft": "Streckwerk (Verzug 15–40)",
     "cond": "Verdichtung (Unterdruck)",
     "tri": "Spinndreieck",
     "ring": "Ring + Läufer",
     "balloon": "Fadenballon",
     "rail": "Ringbank",
     "lupeC": "Garn unter der Lupe: kompakt",
     "lupeK": "Garn unter der Lupe: konventionell",
     "hairC": "wenig abstehende Fasern",
     "hairK": "abstehende Randfasern = Haarigkeit"
    },
    "how": [
     "Das Vorgarn wird im Streckwerk auf die Endfeinheit verzogen.",
     "Die Spindel dreht; der Läufer wird vom Garn auf dem Ring mitgeschleppt. Jede Umdrehung des Ballons erteilt eine Drehung, die bis kurz vor die Lieferwalze läuft.",
     "Dort bleibt ein ungedrehtes Spinndreieck – Randfasern werden schlecht eingebunden und stehen ab (Haarigkeit).",
     "Kompaktspinnen bündelt die Fasern nach dem Streckwerk mit Unterdruck: Das Spinndreieck verschwindet fast, das Garn wird glatter und fester."
    ],
    "figs": [
     [
      "15–40",
      "Verzug am Ring"
     ],
     [
      "15–27 m/min",
      "übliche Liefergeschwindigkeit"
     ],
     [
      "Ne 6–200",
      "Feinheitsbereich"
     ],
     [
      "seit 1828",
      "Prinzip praktisch unverändert"
     ]
    ],
    "pro": [
     "Universell, feinste Garne, hohe Festigkeit",
     "Kompakt: weniger Haarigkeit, weniger Drehung bei gleicher Festigkeit"
    ],
    "con": [
     "Langsam: Läufer-Ring-Reibung und Wärme begrenzen die Drehzahl",
     "Kleine Kopse – Umspulen nötig",
     "Zusätzlicher Flyer"
    ],
    "when": "Universalverfahren, vor allem für feine und hochwertige Garne."
   },
   {
    "n": "Rotorspinnen",
    "de": "Offenend: Fasern vereinzeln und in einem schnell drehenden Rotor neu sammeln",
    "st": [
     "1 · Band direkt vorgelegt",
     "2 · Auflösewalze vereinzelt",
     "3 · Transport im Luftstrom",
     "4 · Sammeln in der Rotorrille",
     "5 · Eindrehen und Abziehen"
    ],
    "cap": [
     "Band direkt vorgelegt – kein Flyer",
     "Auflösewalze kämmt Einzelfasern aus",
     "Luftstrom streckt und beschleunigt die Fasern",
     "Fasern sammeln sich in der Rotorrille",
     "Rotor dreht ein, Garn wird abgezogen"
    ],
    "lab": {
     "sliver": "Band (direkt)",
     "opener": "Auflösewalze",
     "channel": "Faserkanal (Luftstrom)",
     "rotor": "Rotor (Draufsicht) mit Rille, Mitte: Abzugsdüse",
     "pkg": "Kreuzspule"
    },
    "how": [
     "Das Faserband wird direkt vorgelegt – kein Flyer.",
     "Eine schnelle Auflösewalze kämmt Einzelfasern aus und scheidet Schmutz ab.",
     "Ein Luftstrom bringt die Fasern durch einen sich verjüngenden Kanal in den Rotor; sie gleiten in die Rotorrille und bilden dort ein Faserband (Rückdoublierung).",
     "Das Garnende dreht sich mit dem Rotor und bindet die Fasern ein; das Garn wird durch die Abzugsdüse abgezogen und direkt auf eine Kreuzspule gewickelt. Fasern, die quer über das Garn fallen, bilden Bauchbinden."
    ],
    "figs": [
     [
      "60 000–150 000",
      "U/min Rotor"
     ],
     [
      "6 000–9 000",
      "U/min Auflösewalze"
     ],
     [
      "Ne 5–40",
      "typischer Feinheitsbereich"
     ],
     [
      "80–85 %",
      "Festigkeit im Vergleich zu Ringgarn"
     ]
    ],
    "pro": [
     "Sehr produktiv, ohne Flyer und Umspulen",
     "Gleichmässiges, abriebfestes Garn"
    ],
    "con": [
     "Nur mittlere bis grobe Feinheiten",
     "Geringere Festigkeit, härterer Griff (Bauchbinden)"
    ],
    "when": "Denim, Frottier, Decken, Socken, T-Shirts – mittel bis grob."
   },
   {
    "n": "Luftspinnen",
    "de": "Ein Luftwirbel legt Fasern als Mantel um einen parallelen Kern",
    "st": [
     "1 · Hoher Verzug im Streckwerk",
     "2 · Eintritt in die Düse",
     "3 · Luftwirbel um die Spindelspitze",
     "4 · Abzug durch die Hohlspindel"
    ],
    "cap": [
     "Hoher Verzug im Streckwerk",
     "Faserband tritt in die Düse",
     "Luftwirbel: Freie Faserenden legen sich um die Spindelspitze",
     "Kern-Mantel-Garn wird durch die Hohlspindel abgezogen"
    ],
    "lab": {
     "sliver": "Streckenband",
     "draft": "Streckwerk (hoher Verzug)",
     "nozzle": "Düse mit Hohlspindel",
     "spindle": "Hohlspindel",
     "air": "Druckluft",
     "pkg": "Spule",
     "struct": "Struktur: paralleler Kern, umwundener Mantel"
    },
    "how": [
     "Ein Streckenband wird im Streckwerk direkt auf die Endfeinheit verzogen.",
     "Das Faserband tritt in eine Düse; Druckluft erzeugt einen Wirbel um die Spitze einer feststehenden Hohlspindel.",
     "Freie Faserenden werden vom Wirbel um den Kern gelegt – es entsteht ein Kern-Mantel-Garn mit parallelem Kern.",
     "Das Garn wird durch die Hohlspindel abgezogen und direkt auf eine Kreuzspule gewickelt."
    ],
    "figs": [
     [
      "bis 450 m/min",
      "Liefergeschwindigkeit"
     ],
     [
      "≈ 20×",
      "schneller als Ringspinnen (Quellenangabe)"
     ],
     [
      "Ne 12–40",
      "typischer Feinheitsbereich"
     ],
     [
      "sehr gering",
      "Haarigkeit"
     ]
    ],
    "pro": [
     "Höchste Liefergeschwindigkeit",
     "Sehr wenig Haarigkeit, wenig Abrieb und Faserflug in der Weiterverarbeitung"
    ],
    "con": [
     "Gröber als etwa Ne 12 nicht wirtschaftlich",
     "Härterer Griff; Faserlänge und -art beeinflussen stark"
    ],
    "when": "Mittlere Feinheiten, oft Mischungen mit Polyester oder Viskose, Strick und Webware."
   }
  ],
  "cmp": {
   "struct": [
    [
     "Ringgarn",
     "alle Fasern schraubenförmig, abstehende Randfasern"
    ],
    [
     "Kompaktgarn",
     "schraubenförmig, kaum abstehende Fasern"
    ],
    [
     "Rotorgarn",
     "Kern gedreht, Bauchbinden quer darüber"
    ],
    [
     "Luftspinngarn",
     "paralleler Kern, umwundener Mantel"
    ]
   ],
   "head": [
    "Merkmal",
    "Ring",
    "Kompakt",
    "Rotor",
    "Luft"
   ],
   "rows": [
    [
     "Vorlage",
     "Vorgarn (Flyer)",
     "Vorgarn (Flyer)",
     "Streckenband",
     "Streckenband"
    ],
    [
     "Drehung durch",
     "Spindel + Läufer (Ballon)",
     "wie Ring, Fasern vorher verdichtet",
     "drehenden Rotor",
     "Luftwirbel um Hohlspindel"
    ],
    [
     "Liefergeschwindigkeit",
     "15–27 m/min",
     "ähnlich Ring",
     "130–250 m/min",
     "bis 450 m/min"
    ],
    [
     "Feinheitsbereich",
     "Ne 6–200",
     "fein bis sehr fein",
     "Ne 5–40 (bis ~60)",
     "Ne 12–40"
    ],
    [
     "Garnstruktur",
     "echte Drehung, alle Fasern",
     "echte Drehung, glatt",
     "Kern + Bauchbinden",
     "Kern + Mantel"
    ],
    [
     "Typisch",
     "universell, fein, fest",
     "Premium, wenig Haarigkeit",
     "Denim, Frottier, Socken",
     "Strick, Mischungen, wenig Haarigkeit"
    ],
    [
     "Grösste Grenze",
     "Tempo (Läufer)",
     "Tempo (Läufer)",
     "Feinheit, Festigkeit",
     "grobe Garne, Griff"
    ]
   ],
   "note": "Werte aus Lehrunterlagen und Fachartikeln; sie streuen je nach Faser, Feinheit und Quelle. Für die Kompaktspinnerei nennen Quellen 10 % bzw. 20 % weniger Drehung bei gleicher Festigkeit."
  },
  "twist": {
   "tw": "Drehung",
   "sp": "Spindel (Ring)",
   "ro": "Rotor",
   "tpm": "T/m",
   "rpm": "U/min",
   "bars": [
    "Ringspinnen",
    "Rotorspinnen",
    "Luftspinnen (Quelle)"
   ],
   "why": [
    "(Spindel ÷ Drehung)",
    "(Rotor ÷ Drehung)",
    "(Herstellerangabe, andere Mechanik)"
   ],
   "note": "Nominelle Rechnung ohne Drehungsverlust, Schlupf und Stillstand. Beim Luftspinnen entsteht die Drehung durch einen Luftwirbel; die Formel gilt dort nicht direkt."
  },
  "wool": [
   [
    "Kammgarn",
    "Waschen → Karde → Nadelstrecken (Gillen) → Kämmen → Nadelstrecken → Kammzug → Vorgarn → Spinnen. Lange Fasern, sehr parallel – glattes, feines, festes Garn."
   ],
   [
    "Streichgarn",
    "Waschen → Karde → Spinnen. Kurze Route ohne Kämmen und mit wenig Verzug: Fasern liegen kreuz und quer – voluminöses, weiches, raueres Garn. Kämmling aus der Kammgarnspinnerei wird hier verwertet."
   ],
   [
    "Halbkammgarn",
    "Waschen → Karde → mehrere Nadelstrecken → Spinnen. Zwischen beiden: gestreckt, aber nicht gekämmt."
   ],
   [
    "Wolle auf Baumwollanlagen",
    "Kürzere Wollen, meist in Mischung mit Baumwolle oder Polyester, laufen auch über die Kurzstapellinie – gelegentlich auch rotorgesponnen."
   ]
  ],
  "links": [
   [
    "Luftdüsenspinnen",
    "Unsere Technologie: Verzug, Luftwirbel in der Spinndüse, Kern- und Umwindefasern im Detail."
   ],
   [
    "Filamentgarnspinnerei",
    "Der Gegenpol: Endlosfilamente aus der Schmelze statt Stapelfasern aus der Flocke."
   ],
   [
    "Webereivorbereitung",
    "Was nach dem Spinnen kommt: Spulen, Zetteln, Schlichten und Einziehen."
   ],
   [
    "Rundstricken",
    "Wohin viele Stapelfasergarne gehen: Maschenware auf der Rundstrickmaschine."
   ],
   [
    "Färben",
    "Farbstoffklassen, Färbestufen von der Flocke bis zum Stück, Auszieh- und Kontinueverfahren."
   ]
  ]
 },
 "en": {
  "ui": {
   "eyebrow": "Knowledge Base · Staple fibre spinning",
   "h1": "Staple fibre spinning: from fibre tuft to yarn",
   "lead": "Cotton and other staple fibres pass through a long chain before they become yarn: opening, cleaning, blending, carding, drawing, combing depending on the quality, drafting into roving and finally spinning. This page shows the processes and their technology as animated diagrams with step-by-step control – from bale opening to ring, compact, rotor and air-jet spinning. Machines and manufacturers are deliberately left out.",
   "note": "The diagrams are highly simplified. Values from teaching material and technical articles; they vary with fibre, count and source.",
   "sources": "Sources",
   "open": "Open module",
   "loc": "en-US",
   "prev": "◀ Step back",
   "next": "Step forward ▶",
   "play": "▶ Play",
   "pause": "Pause",
   "lkL": "More in the Knowledge Base",
   "how": "Purpose and sequence",
   "figs": "Process figures",
   "pro": "Strengths",
   "con": "Limits",
   "when": "When?"
  },
  "kpis": [
   [
    "≈ 40,000",
    "fibres in the cross-section of a card sliver"
   ],
   [
    "6–8",
    "slivers are doubled at the draw frame"
   ],
   [
    "8–25 %",
    "noil (combed-out short fibres), depending on the target"
   ],
   [
    "up to 150,000",
    "rpm of a spinning rotor"
   ],
   [
    "15–27 vs. 450",
    "m/min delivery speed, ring vs. air-jet spinning"
   ]
  ],
  "scenes": [
   {
    "k": "Process lines",
    "title": "Process lines of short-staple spinning",
    "text": "Which steps a yarn goes through depends on the spinning process and the required quality. Choose a line – the stages involved are highlighted. Click a stage to open its animation."
   },
   {
    "k": "Processes in detail",
    "title": "The processes in detail",
    "text": "Each diagram can be played or stepped forwards and backwards. The diagrams are highly simplified."
   },
   {
    "k": "Spinning systems compared",
    "title": "Spinning systems compared",
    "text": "Four processes, four yarn structures. The sketches show schematically how the fibres lie in the yarn."
   },
   {
    "k": "Twist and speed",
    "title": "Twist and speed: why ring spinning is slow",
    "text": "Ring and rotor spinning follow the same basic relationship: twist (T/m) = speed (rpm) ÷ delivery speed (m/min). For a given twist, the speed of the rotating element therefore sets the pace. On the ring frame, the traveller speed limits the spindle speed; in rotor spinning, a small cup turns without a cop."
   },
   {
    "k": "Wool excursus",
    "title": "Wool excursus: worsted, woollen, semi-worsted",
    "text": "Wool has its own process lines, which differ mainly in the preparation."
   }
  ],
  "route": {
   "seg": [
    "Carded ring yarn",
    "Combed ring yarn",
    "Rotor yarn",
    "Air-jet yarn"
   ],
   "nodes": {
    "putzerei": "Blow room",
    "karde": "Card",
    "strecke1": "Breaker drawing",
    "kvor": "Comber preparation",
    "kaemmen": "Combing",
    "strecke": "Finisher drawing",
    "flyer": "Roving frame",
    "ring": "Ring / compact",
    "rotor": "Rotor spinning",
    "luft": "Air-jet spinning"
   },
   "txt": [
    "Carded ring yarn: blow room, card, two drawing passages, roving frame, ring spinning.",
    "Combed ring yarn: after the card, comber preparation (lap) and combing, then finisher drawing, roving frame and ring spinning.",
    "Rotor yarn: a short line – after card and draw frame straight from sliver onto the rotor spinning machine, without roving frame.",
    "Air-jet yarn: card, usually two drawing passages (combed if required), then straight from sliver onto the air-jet spinning machine."
   ]
  },
  "proc": [
   {
    "n": "Blow room",
    "de": "Opening bales, cleaning, blending, dedusting",
    "st": [
     "1 · Bale plucking: small tufts from all bales at once",
     "2 · Pneumatic transport",
     "3 · Cleaning: the beater opens, trash falls through the grid",
     "4 · Blending in staggered-filled chambers",
     "5 · Dedusting, feeding the cards"
    ],
    "cap": [
     "Small tufts from all bales at once",
     "Tufts travel on in the air stream",
     "Opening and cleaning: trash falls through the grid",
     "Blending: fill chambers staggered, empty them together",
     "Even lap feed for the card"
    ],
    "lab": {
     "bales": "Row of bales (different origins)",
     "pluck": "Bale plucker",
     "clean": "Cleaner: beater + grid",
     "mix": "Mixer: chambers",
     "chute": "Chute feed → card"
    },
    "how": [
     "Pressed bales are broken into small tufts – the smaller the tuft, the larger its surface and the more easily trash falls out.",
     "Beaters and spiked rollers over grids open the tufts further; heavy particles fall through, dust leaves with the air stream.",
     "Mixers even out differences in origin and quality between the bales.",
     "At the end, a chute feed supplies each card with an even batt."
    ],
    "figs": [
     [
      "200 kg → ~10 g",
      "bale → tuft in bale plucking"
     ],
     [
      "100–200 mg",
      "target tuft size after pre-cleaning (textbook value)"
     ],
     [
      "95–99 %",
      "of impurities removed by blow room and card together"
     ]
    ],
    "pro": [
     "Basis for cleanliness and an even blend",
     "Gentle, gradual opening"
    ],
    "con": [
     "A high degree of cleaning almost always costs good fibres",
     "Every beat stresses the fibres and can create neps"
    ],
    "when": "Always for cotton; man-made fibres need hardly any cleaning, but do need opening and blending."
   },
   {
    "n": "Card",
    "de": "Individualising fibres, removing neps and residual trash, forming a sliver",
    "st": [
     "1 · Feeding and clamping the batt",
     "2 · Licker-in opens, trash is separated",
     "3 · Carding between cylinder and flats",
     "4 · Doffer takes over the web",
     "5 · Forming the sliver and coiling it into the can"
    ],
    "cap": [
     "The batt is fed and clamped",
     "Licker-in: open tufts, separate trash",
     "Carding between cylinder and flats: single fibres",
     "The doffer forms a fine web",
     "Web → sliver → can"
    ],
    "lab": {
     "chute": "Chute",
     "flats": "Revolving flats",
     "cyl": "Cylinder (drum)",
     "doffer": "Doffer",
     "can": "Can",
     "licker": "Licker-in",
     "feed": "Feed roller"
    },
    "how": [
     "The feed roller clamps the batt, the licker-in opens it into small tufts.",
     "Between cylinder and revolving flats, the wire points face each other (point against point) – the tufts are broken down into single fibres, neps and trash stay caught in the flats.",
     "The slower doffer takes over the fibres as a thin web.",
     "A trumpet condenses the web into the untwisted card sliver, which is coiled into a can."
    ],
    "figs": [
     [
      "≈ 40,000",
      "fibres in the sliver cross-section"
     ],
     [
      "≈ 1 %",
      "short fibres removed by the card"
     ],
     [
      "80–116",
      "flat bars, of which 30–46 are working"
     ],
     [
      "“Well carded …”",
      "… is half spun (spinners' saying)"
     ]
    ],
    "pro": [
     "The only stage that truly individualises the fibres",
     "Removes neps, dust and part of the short fibres"
    ],
    "con": [
     "Fibres are hardly parallel yet, many lie as hooks",
     "Sliver evenness still insufficient"
    ],
    "when": "In every short-staple line."
   },
   {
    "n": "Draw frame",
    "de": "Doubling and drafting: more even, more parallel",
    "st": [
     "1 · Feeding 6–8 slivers (doubling)",
     "2 · Measuring thickness (autolevelling)",
     "3 · Draft in the drafting system",
     "4 · Parallelising, evening out",
     "5 · Sliver into the can"
    ],
    "cap": [
     "Doubling: feed several slivers together",
     "Measure thickness for the autoleveller",
     "Draft: v1 < v2 < v3",
     "Fibres parallel, variations average out",
     "One even sliver into the can"
    ],
    "lab": {
     "cans": "6 cans = 6 card slivers (doubling)",
     "meas": "Measuring",
     "v3": "v3 (fastest)",
     "can": "Can",
     "thickA": "Thickness per single sliver: varies",
     "thickB": "Thickness of drawn sliver: evened out"
    },
    "how": [
     "Several slivers are fed together: thick and thin places average out (doubling). This is also where fibres can be blended, e.g. cotton/polyester.",
     "In the drafting system, each roller pair runs faster than the previous one – the sliver is drafted, the fibres are straightened and laid parallel.",
     "Doubling and draft are usually about the same, so the sliver keeps a similar thickness.",
     "An autoleveller measures the sliver thickness and continuously adjusts the draft."
    ],
    "figs": [
     [
      "6–8",
      "doubled slivers"
     ],
     [
      "4–8",
      "draft"
     ],
     [
      "350–800 m/min",
      "delivery speed"
     ],
     [
      "CV 4–6 % → 1–2 %",
      "sliver unevenness with autoleveller"
     ]
    ],
    "pro": [
     "The most important stage for evenness",
     "Ideal for blending different fibres"
    ],
    "con": [
     "Evens out only short- and medium-wave variations well",
     "Several passages needed (breaker and finisher drawing)"
    ],
    "when": "In all lines – usually twice."
   },
   {
    "n": "Combing",
    "de": "Combing out short fibres and neps – for finer, smoother yarns",
    "st": [
     "1 · Feeding, nipper clamps",
     "2 · Circular comb combs the fibre fringe",
     "3 · Nipper opens and moves forward – piecing",
     "4 · Detaching through the top comb",
     "5 · Nipper back, new cycle"
    ],
    "cap": [
     "Feeding: the nipper clamps the lap",
     "Circular comb combs the fringe – short fibres and neps out",
     "Nipper opens and moves forward, detaching rollers run back: piecing",
     "Detaching: the fringe is pulled through the top comb",
     "Nipper back – new cycle"
    ],
    "lab": {
     "lap": "Lap",
     "open": "Nipper open",
     "closed": "Nipper closed",
     "circ": "Circular comb",
     "top": "Top comb",
     "detach": "Detaching rollers",
     "sliver": "combed sliver",
     "noil": "Noil (suction)"
    },
    "how": [
     "Preparation: card slivers are formed into a lap so that the fibres are fed in an orderly way.",
     "The nipper clamps the lap, a circular comb combs the protruding fibre fringe – whatever is not clamped (short fibres, neps) stays in the comb.",
     "The nipper moves forward, the combed fringe is pieced to the previous web and pulled by the detaching rollers through a top comb, which combs the rear end.",
     "The noil is sucked away; the webs are combined into a combed sliver."
    ],
    "figs": [
     [
      "8–25 %",
      "noil, depending on the target"
     ],
     [
      "Noil %",
      "= noil ÷ fed mass × 100"
     ],
     [
      "intermittent",
      "combing cycle instead of continuous"
     ]
    ],
    "pro": [
     "Finer, smoother, stronger and more even yarns",
     "Fewer neps, better lustre"
    ],
    "con": [
     "Material loss (noil)",
     "Additional stages and costs"
    ],
    "when": "Fine, high-quality cotton yarns (shirts, fine knitwear)."
   },
   {
    "n": "Roving frame",
    "de": "Drafting the sliver into roving and winding it with protective twist",
    "st": [
     "1 · Sliver from the can",
     "2 · Draft into a thin roving",
     "3 · The flyer inserts protective twist",
     "4 · Winding onto the bobbin"
    ],
    "cap": [
     "Sliver from the can",
     "Draft into a thin roving",
     "The flyer inserts protective twist (25–70 T/m)",
     "Winding onto the roving bobbin"
    ],
    "lab": {
     "can": "Drawn sliver",
     "draft": "Drafting system (draft 5–20)",
     "flyer": "Flyer rotates",
     "rail": "Bobbin rail rises/falls"
    },
    "how": [
     "The drawn sliver is too thick for the draft of the ring spinning machine, and cans are a poor feed format.",
     "The roving frame drafts the sliver into a thin roving.",
     "A flyer rotates around the bobbin and inserts a slight protective twist – enough to hold the roving together, but little enough that it can be drafted again later.",
     "The bobbin runs slightly faster than the flyer; the bobbin rail rises and falls to build the package."
    ],
    "figs": [
     [
      "5–20",
      "draft at the roving frame"
     ],
     [
      "25–70 T/m",
      "protective twist"
     ],
     [
      "T/m",
      "= flyer speed ÷ delivery speed"
     ],
     [
      "20–25 m/min",
      "usual delivery (patent figure)"
     ]
    ],
    "pro": [
     "Suitable feed material for the ring spinning machine"
    ],
    "con": [
     "Complex winding mechanism",
     "Too much twist disturbs the draft, too little leads to false drafts and breaks"
    ],
    "when": "Only for ring and compact spinning – rotor and air-jet spinning work directly from sliver."
   },
   {
    "n": "Ring spinning",
    "de": "Draft, twist via spindle and traveller, winding onto the cop",
    "v": [
     "conventional",
     "compact"
    ],
    "st": [
     "1 · Draft in the drafting system",
     "2 · Spinning triangle / condensing",
     "3 · Twist via spindle and traveller",
     "4 · Winding onto the cop"
    ],
    "cap": [
     "Draft in the drafting system",
     "Spinning triangle: twist starts here – edge fibres stick out",
     "Spindle turns, traveller follows: twist",
     "Winding onto the cop"
    ],
    "capC": [
     "Draft in the drafting system",
     "Condensing: spinning triangle almost gone",
     "Spindle turns, traveller follows: twist",
     "Winding onto the cop"
    ],
    "lab": {
     "bobbin": "Roving bobbin",
     "draft": "Drafting system (draft 15–40)",
     "cond": "Condensing (suction)",
     "tri": "Spinning triangle",
     "ring": "Ring + traveller",
     "balloon": "Yarn balloon",
     "rail": "Ring rail",
     "lupeC": "Yarn under the magnifier: compact",
     "lupeK": "Yarn under the magnifier: conventional",
     "hairC": "few protruding fibres",
     "hairK": "protruding edge fibres = hairiness"
    },
    "how": [
     "The roving is drafted to the final count in the drafting system.",
     "The spindle turns; the traveller is dragged round the ring by the yarn. Every revolution of the balloon inserts one turn of twist, which runs up to just before the delivery roller.",
     "There, an untwisted spinning triangle remains – edge fibres are poorly bound in and stick out (hairiness).",
     "Compact spinning condenses the fibres with suction after the drafting system: the spinning triangle almost disappears, the yarn becomes smoother and stronger."
    ],
    "figs": [
     [
      "15–40",
      "draft at the ring frame"
     ],
     [
      "15–27 m/min",
      "usual delivery speed"
     ],
     [
      "Ne 6–200",
      "count range"
     ],
     [
      "since 1828",
      "principle practically unchanged"
     ]
    ],
    "pro": [
     "Universal, finest yarns, high strength",
     "Compact: less hairiness, less twist for the same strength"
    ],
    "con": [
     "Slow: traveller–ring friction and heat limit the speed",
     "Small cops – rewinding needed",
     "Additional roving frame"
    ],
    "when": "The universal process, above all for fine and high-quality yarns."
   },
   {
    "n": "Rotor spinning",
    "de": "Open-end: separating fibres and collecting them again in a fast-turning rotor",
    "st": [
     "1 · Sliver fed directly",
     "2 · Opening roller separates",
     "3 · Transport in the air stream",
     "4 · Collecting in the rotor groove",
     "5 · Twisting in and withdrawing"
    ],
    "cap": [
     "Sliver fed directly – no roving frame",
     "The opening roller combs out single fibres",
     "The air stream straightens and accelerates the fibres",
     "Fibres collect in the rotor groove",
     "The rotor twists, the yarn is withdrawn"
    ],
    "lab": {
     "sliver": "Sliver (direct)",
     "opener": "Opening roller",
     "channel": "Fibre channel (air stream)",
     "rotor": "Rotor (top view) with groove, centre: navel",
     "pkg": "Cross-wound package"
    },
    "how": [
     "The sliver is fed directly – no roving frame.",
     "A fast opening roller combs out single fibres and separates trash.",
     "An air stream carries the fibres through a tapering channel into the rotor; they slide into the rotor groove and form a fibre ring there (back-doubling).",
     "The yarn end turns with the rotor and binds the fibres in; the yarn is withdrawn through the navel and wound directly onto a cross-wound package. Fibres that fall across the yarn form wrapper fibres (belly bands)."
    ],
    "figs": [
     [
      "60,000–150,000",
      "rpm rotor"
     ],
     [
      "6,000–9,000",
      "rpm opening roller"
     ],
     [
      "Ne 5–40",
      "typical count range"
     ],
     [
      "80–85 %",
      "strength compared with ring yarn"
     ]
    ],
    "pro": [
     "Very productive, without roving frame and rewinding",
     "Even, abrasion-resistant yarn"
    ],
    "con": [
     "Only medium to coarse counts",
     "Lower strength, harsher handle (wrapper fibres)"
    ],
    "when": "Denim, terry, blankets, socks, T-shirts – medium to coarse."
   },
   {
    "n": "Air-jet spinning",
    "de": "An air vortex wraps fibres as a sheath around a parallel core",
    "st": [
     "1 · High draft in the drafting system",
     "2 · Entry into the nozzle",
     "3 · Air vortex around the spindle tip",
     "4 · Withdrawal through the hollow spindle"
    ],
    "cap": [
     "High draft in the drafting system",
     "The fibre strand enters the nozzle",
     "Air vortex: free fibre ends wrap around the spindle tip",
     "Core-sheath yarn is withdrawn through the hollow spindle"
    ],
    "lab": {
     "sliver": "Drawn sliver",
     "draft": "Drafting system (high draft)",
     "nozzle": "Nozzle with hollow spindle",
     "spindle": "Hollow spindle",
     "air": "Compressed air",
     "pkg": "Package",
     "struct": "Structure: parallel core, wrapped sheath"
    },
    "how": [
     "A drawn sliver is drafted directly to the final count in the drafting system.",
     "The fibre strand enters a nozzle; compressed air creates a vortex around the tip of a stationary hollow spindle.",
     "Free fibre ends are wrapped around the core by the vortex – the result is a core-sheath yarn with a parallel core.",
     "The yarn is withdrawn through the hollow spindle and wound directly onto a cross-wound package."
    ],
    "figs": [
     [
      "up to 450 m/min",
      "delivery speed"
     ],
     [
      "≈ 20×",
      "faster than ring spinning (source figure)"
     ],
     [
      "Ne 12–40",
      "typical count range"
     ],
     [
      "very low",
      "hairiness"
     ]
    ],
    "pro": [
     "Highest delivery speed",
     "Very little hairiness, little abrasion and fly in downstream processing"
    ],
    "con": [
     "Not economical coarser than about Ne 12",
     "Harsher handle; fibre length and type have a strong influence"
    ],
    "when": "Medium counts, often blends with polyester or viscose, knitted and woven fabrics."
   }
  ],
  "cmp": {
   "struct": [
    [
     "Ring yarn",
     "all fibres helical, protruding edge fibres"
    ],
    [
     "Compact yarn",
     "helical, hardly any protruding fibres"
    ],
    [
     "Rotor yarn",
     "twisted core, wrapper fibres across it"
    ],
    [
     "Air-jet yarn",
     "parallel core, wrapped sheath"
    ]
   ],
   "head": [
    "Feature",
    "Ring",
    "Compact",
    "Rotor",
    "Air-jet"
   ],
   "rows": [
    [
     "Feed",
     "roving (roving frame)",
     "roving (roving frame)",
     "drawn sliver",
     "drawn sliver"
    ],
    [
     "Twist from",
     "spindle + traveller (balloon)",
     "as ring, fibres condensed beforehand",
     "rotating rotor",
     "air vortex around hollow spindle"
    ],
    [
     "Delivery speed",
     "15–27 m/min",
     "similar to ring",
     "130–250 m/min",
     "up to 450 m/min"
    ],
    [
     "Count range",
     "Ne 6–200",
     "fine to very fine",
     "Ne 5–40 (up to ~60)",
     "Ne 12–40"
    ],
    [
     "Yarn structure",
     "real twist, all fibres",
     "real twist, smooth",
     "core + wrapper fibres",
     "core + sheath"
    ],
    [
     "Typical",
     "universal, fine, strong",
     "premium, low hairiness",
     "denim, terry, socks",
     "knitwear, blends, low hairiness"
    ],
    [
     "Biggest limit",
     "speed (traveller)",
     "speed (traveller)",
     "fineness, strength",
     "coarse yarns, handle"
    ]
   ],
   "note": "Values from teaching material and technical articles; they vary with fibre, count and source. For compact spinning, sources give 10 % or 20 % less twist for the same strength."
  },
  "twist": {
   "tw": "Twist",
   "sp": "Spindle (ring)",
   "ro": "Rotor",
   "tpm": "T/m",
   "rpm": "rpm",
   "bars": [
    "Ring spinning",
    "Rotor spinning",
    "Air-jet spinning (source)"
   ],
   "why": [
    "(spindle ÷ twist)",
    "(rotor ÷ twist)",
    "(manufacturer figure, different mechanism)"
   ],
   "note": "Nominal calculation without twist loss, slip and downtime. In air-jet spinning, the twist comes from an air vortex; the formula does not apply directly there."
  },
  "wool": [
   [
    "Worsted",
    "Scouring → card → gill boxes → combing → gill boxes → top → roving → spinning. Long fibres, very parallel – smooth, fine, strong yarn."
   ],
   [
    "Woollen",
    "Scouring → card → spinning. A short route without combing and with little draft: the fibres lie criss-cross – bulky, soft, rougher yarn. Noil from worsted spinning is used here."
   ],
   [
    "Semi-worsted",
    "Scouring → card → several gill boxes → spinning. In between: drawn, but not combed."
   ],
   [
    "Wool on cotton systems",
    "Shorter wools, usually blended with cotton or polyester, also run on the short-staple line – occasionally even rotor-spun."
   ]
  ],
  "links": [
   [
    "Air-jet spinning",
    "Our technology: drafting, the vortex in the spinning jet, core and wrapper fibres in detail."
   ],
   [
    "Filament yarn spinning",
    "The counterpart: continuous filaments from the melt instead of staple fibres from the tuft."
   ],
   [
    "Weaving preparation",
    "What comes after spinning: winding, warping, sizing and drawing-in."
   ],
   [
    "Circular knitting",
    "Where many staple yarns end up: knitted fabric on the circular knitting machine."
   ],
   [
    "Dyeing",
    "Dye classes, dyeing stages from loose fibre to fabric, exhaust and continuous processes."
   ]
  ]
 },
 "es": {
  "ui": {
   "eyebrow": "Knowledge Base · Hilatura de fibra corta",
   "h1": "Hilatura de fibra corta: del copo de fibra al hilo",
   "lead": "El algodón y otras fibras cortas recorren una larga cadena antes de convertirse en hilo: abrir, limpiar, mezclar, cardar, estirar, peinar según la calidad, estirar a mecha y, por último, hilar. Esta página muestra los procesos y su técnica como esquemas animados con control paso a paso, desde la apertura de balas hasta la hilatura de anillo, compacta, de rotor y por chorro de aire. Las máquinas y los fabricantes quedan deliberadamente fuera.",
   "note": "Los esquemas están muy simplificados. Valores de material didáctico y artículos técnicos; varían según la fibra, el título y la fuente.",
   "sources": "Fuentes",
   "open": "Abrir módulo",
   "loc": "es-ES",
   "prev": "◀ Paso atrás",
   "next": "Paso adelante ▶",
   "play": "▶ Reproducir",
   "pause": "Pausa",
   "lkL": "Más en la Knowledge Base",
   "how": "Objetivo y secuencia",
   "figs": "Parámetros del proceso",
   "pro": "Ventajas",
   "con": "Límites",
   "when": "¿Cuándo?"
  },
  "kpis": [
   [
    "≈ 40 000",
    "fibras en la sección de una cinta de carda"
   ],
   [
    "6–8",
    "cintas se doblan en el manuar"
   ],
   [
    "8–25 %",
    "borra de peinado (fibras cortas eliminadas), según el objetivo"
   ],
   [
    "hasta 150 000",
    "rpm de un rotor de hilatura"
   ],
   [
    "15–27 frente a 450",
    "m/min de velocidad de salida, anillo frente a chorro de aire"
   ]
  ],
  "scenes": [
   {
    "k": "Líneas de proceso",
    "title": "Líneas de proceso de la hilatura de fibra corta",
    "text": "Los pasos que recorre un hilo dependen del sistema de hilatura y de la calidad deseada. Elija una línea: se resaltan las etapas implicadas. Un clic en una etapa abre su animación."
   },
   {
    "k": "Procesos en detalle",
    "title": "Los procesos en detalle",
    "text": "Cada esquema se puede reproducir o avanzar y retroceder paso a paso. Los esquemas están muy simplificados."
   },
   {
    "k": "Sistemas de hilatura",
    "title": "Sistemas de hilatura comparados",
    "text": "Cuatro procesos, cuatro estructuras de hilo. Los bocetos muestran de forma esquemática cómo se disponen las fibras en el hilo."
   },
   {
    "k": "Torsión y velocidad",
    "title": "Torsión y velocidad: por qué la hilatura de anillo es lenta",
    "text": "En la hilatura de anillo y de rotor rige la misma relación básica: torsión (v/m) = velocidad de giro (rpm) ÷ velocidad de salida (m/min). Para una torsión deseada, la velocidad del órgano giratorio determina, por tanto, el ritmo. En el anillo, la velocidad del cursor limita la velocidad del huso; en el rotor gira una pequeña copa sin husada."
   },
   {
    "k": "Excurso: lana",
    "title": "Excurso lana: estambre, cardado, semipeinado",
    "text": "La lana tiene líneas propias, que se diferencian sobre todo en la preparación."
   }
  ],
  "route": {
   "seg": [
    "Hilo de anillo cardado",
    "Hilo de anillo peinado",
    "Hilo de rotor",
    "Hilo de chorro de aire"
   ],
   "nodes": {
    "putzerei": "Sala de apertura",
    "karde": "Carda",
    "strecke1": "Manuar 1.er paso",
    "kvor": "Preparación del peinado",
    "kaemmen": "Peinado",
    "strecke": "Manuar 2.º paso",
    "flyer": "Mechera",
    "ring": "Anillo / compacto",
    "rotor": "Hilatura de rotor",
    "luft": "Chorro de aire"
   },
   "txt": [
    "Hilo de anillo cardado: sala de apertura, carda, dos pasos de manuar, mechera, hilatura de anillo.",
    "Hilo de anillo peinado: tras la carda, preparación del peinado (napa) y peinado; después manuar de segundo paso, mechera e hilatura de anillo.",
    "Hilo de rotor: línea corta – tras carda y manuar, directamente de la cinta a la hiladora de rotor, sin mechera.",
    "Hilo de chorro de aire: carda, normalmente dos pasos de manuar (peinado si es necesario) y luego directamente de la cinta a la hiladora de chorro de aire."
   ]
  },
  "proc": [
   {
    "n": "Sala de apertura",
    "de": "Abrir balas, limpiar, mezclar, desempolvar",
    "st": [
     "1 · Desmontado de balas: copos pequeños de todas las balas a la vez",
     "2 · Transporte neumático",
     "3 · Limpieza: el batidor abre, la suciedad cae por la parrilla",
     "4 · Mezcla en cámaras llenadas de forma escalonada",
     "5 · Desempolvado, alimentación de las cardas"
    ],
    "cap": [
     "Copos pequeños de todas las balas a la vez",
     "Los copos siguen en la corriente de aire",
     "Abrir y limpiar: la suciedad cae por la parrilla",
     "Mezclar: llenar cámaras escalonadas, vaciarlas juntas",
     "Napa uniforme para la carda"
    ],
    "lab": {
     "bales": "Fila de balas (distintos orígenes)",
     "pluck": "Desmontado de balas",
     "clean": "Limpiadora: batidor + parrilla",
     "mix": "Mezcladora: cámaras",
     "chute": "Alimentador de chimenea → carda"
    },
    "how": [
     "Las balas prensadas se descomponen en copos pequeños: cuanto menor es el copo, mayor es su superficie y más fácilmente cae la suciedad.",
     "Batidores y cilindros de púas sobre parrillas siguen abriendo los copos; las partículas pesadas caen, el polvo se va con la corriente de aire.",
     "Las mezcladoras compensan las diferencias de origen y calidad entre las balas.",
     "Al final, un alimentador de chimenea suministra a cada carda una napa uniforme."
    ],
    "figs": [
     [
      "200 kg → ~10 g",
      "bala → copo en el desmontado de balas"
     ],
     [
      "100–200 mg",
      "tamaño de copo buscado tras la prelimpieza (valor de manual)"
     ],
     [
      "95–99 %",
      "de impurezas que eliminan juntas la sala de apertura y la carda"
     ]
    ],
    "pro": [
     "Base para la limpieza y una mezcla uniforme",
     "Apertura suave y escalonada"
    ],
    "con": [
     "Un alto grado de limpieza casi siempre cuesta fibras buenas",
     "Cada golpe solicita las fibras y puede crear neps"
    ],
    "when": "Siempre en algodón; las fibras químicas apenas necesitan limpieza, pero sí apertura y mezcla."
   },
   {
    "n": "Carda",
    "de": "Individualizar fibras, eliminar neps y suciedad residual, formar la cinta",
    "st": [
     "1 · Alimentar y pinzar la napa",
     "2 · El abridor (licker-in) abre, la suciedad se separa",
     "3 · Cardado entre gran tambor y chapones",
     "4 · El peinador (doffer) recoge el velo",
     "5 · Formar la cinta y depositarla en el bote"
    ],
    "cap": [
     "La napa se alimenta y se pinza",
     "Abridor: abrir copos, separar suciedad",
     "Cardado entre tambor y chapones: fibras individuales",
     "El peinador forma un velo fino",
     "Velo → cinta → bote"
    ],
    "lab": {
     "chute": "Chimenea",
     "flats": "Chapones móviles",
     "cyl": "Gran tambor",
     "doffer": "Peinador (doffer)",
     "can": "Bote",
     "licker": "Abridor (licker-in)",
     "feed": "Cilindro alimentador"
    },
    "how": [
     "El cilindro alimentador pinza la napa, el abridor la abre en copos pequeños.",
     "Entre el gran tambor y los chapones móviles, las puntas de las guarniciones se enfrentan (punta contra punta): los copos se deshacen en fibras individuales, los neps y la suciedad quedan atrapados en los chapones.",
     "El peinador, más lento, recoge las fibras como un velo fino.",
     "Una trompeta condensa el velo en la cinta de carda sin torsión, que se deposita en un bote."
    ],
    "figs": [
     [
      "≈ 40 000",
      "fibras en la sección de la cinta"
     ],
     [
      "≈ 1 %",
      "fibras cortas que elimina la carda"
     ],
     [
      "80–116",
      "chapones, de ellos 30–46 en acción"
     ],
     [
      "«Bien cardado…»",
      "… es medio hilado (dicho de hilanderos)"
     ]
    ],
    "pro": [
     "La única etapa que realmente individualiza las fibras",
     "Elimina neps, polvo y parte de las fibras cortas"
    ],
    "con": [
     "Las fibras apenas están paralelas, muchas en forma de gancho",
     "Regularidad de la cinta aún insuficiente"
    ],
    "when": "En toda línea de fibra corta."
   },
   {
    "n": "Manuar",
    "de": "Doblar y estirar: más uniforme, más paralelo",
    "st": [
     "1 · Alimentar 6–8 cintas (doblado)",
     "2 · Medir el grosor (autorregulación)",
     "3 · Estiraje en el tren de estiraje",
     "4 · Paralelizar, igualar",
     "5 · Cinta al bote"
    ],
    "cap": [
     "Doblado: alimentar varias cintas juntas",
     "Medir el grosor para el autorregulador",
     "Estiraje: v1 < v2 < v3",
     "Fibras paralelas, las variaciones se compensan",
     "Una cinta uniforme al bote"
    ],
    "lab": {
     "cans": "6 botes = 6 cintas de carda (doblado)",
     "meas": "Medición",
     "v3": "v3 (la más rápida)",
     "can": "Bote",
     "thickA": "Grosor de cada cinta: varía",
     "thickB": "Grosor de la cinta estirada: igualado"
    },
    "how": [
     "Se alimentan varias cintas juntas: los puntos gruesos y delgados se compensan (doblado). Aquí también pueden mezclarse fibras, p. ej. algodón/poliéster.",
     "En el tren de estiraje, cada par de cilindros gira más rápido que el anterior: la cinta se estira, las fibras se enderezan y se colocan en paralelo.",
     "Doblado y estiraje suelen ser aproximadamente iguales, para que la cinta conserve un grosor similar.",
     "Un autorregulador mide el grosor de la cinta y ajusta el estiraje de forma continua."
    ],
    "figs": [
     [
      "6–8",
      "cintas dobladas"
     ],
     [
      "4–8",
      "estiraje"
     ],
     [
      "350–800 m/min",
      "velocidad de salida"
     ],
     [
      "CV 4–6 % → 1–2 %",
      "irregularidad de la cinta con autorregulador"
     ]
    ],
    "pro": [
     "La etapa más importante para la regularidad",
     "Ideal para mezclar fibras distintas"
    ],
    "con": [
     "Solo compensa bien las variaciones de onda corta y media",
     "Se necesitan varios pasos (primer y segundo paso)"
    ],
    "when": "En todas las líneas, normalmente dos veces."
   },
   {
    "n": "Peinado",
    "de": "Eliminar fibras cortas y neps peinando – para hilos más finos y lisos",
    "st": [
     "1 · Alimentar, la pinza sujeta",
     "2 · El peine circular peina la barba de fibras",
     "3 · La pinza se abre y avanza – empalme",
     "4 · Arranque a través del peine fijo",
     "5 · Pinza atrás, nuevo ciclo"
    ],
    "cap": [
     "Alimentar: la pinza sujeta la napa",
     "El peine circular peina la barba: fuera fibras cortas y neps",
     "La pinza se abre y avanza, los arrancadores retroceden: empalme",
     "Arranque: la barba se tira a través del peine fijo",
     "Pinza atrás – nuevo ciclo"
    ],
    "lab": {
     "lap": "Napa",
     "open": "Pinza abierta",
     "closed": "Pinza cerrada",
     "circ": "Peine circular",
     "top": "Peine fijo",
     "detach": "Cilindros arrancadores",
     "sliver": "cinta peinada",
     "noil": "Borra (aspiración)"
    },
    "how": [
     "Preparación: las cintas de carda se forman en una napa para que las fibras se alimenten de forma ordenada.",
     "La pinza sujeta la napa y un peine circular peina la barba de fibras que sobresale; lo que no está sujeto (fibras cortas, neps) queda en el peine.",
     "La pinza avanza, la barba peinada se empalma con el velo anterior y los cilindros arrancadores la tiran a través de un peine fijo, que peina el extremo posterior.",
     "La borra se aspira; los velos se reúnen en una cinta peinada."
    ],
    "figs": [
     [
      "8–25 %",
      "borra, según el objetivo"
     ],
     [
      "Borra %",
      "= borra ÷ masa alimentada × 100"
     ],
     [
      "intermitente",
      "ciclo de peinado en lugar de continuo"
     ]
    ],
    "pro": [
     "Hilos más finos, lisos, resistentes y regulares",
     "Menos neps, mejor brillo"
    ],
    "con": [
     "Pérdida de material (borra)",
     "Etapas y costes adicionales"
    ],
    "when": "Hilos de algodón finos y de alta calidad (camisería, punto fino)."
   },
   {
    "n": "Mechera",
    "de": "Estirar la cinta a mecha y bobinarla con torsión de protección",
    "st": [
     "1 · Cinta del bote",
     "2 · Estiraje a una mecha fina",
     "3 · La aleta da torsión de protección",
     "4 · Bobinado en la bobina"
    ],
    "cap": [
     "Cinta del bote",
     "Estiraje a una mecha fina",
     "La aleta da torsión de protección (25–70 v/m)",
     "Bobinado en la bobina de mecha"
    ],
    "lab": {
     "can": "Cinta de manuar",
     "draft": "Tren de estiraje (estiraje 5–20)",
     "flyer": "La aleta gira",
     "rail": "El carro sube/baja"
    },
    "how": [
     "La cinta de manuar es demasiado gruesa para el estiraje de la continua de anillos, y los botes son un mal formato de alimentación.",
     "La mechera estira la cinta hasta una mecha fina.",
     "Una aleta gira alrededor de la bobina y da una ligera torsión de protección: suficiente para que la mecha se mantenga, pero tan poca que luego pueda volver a estirarse.",
     "La bobina gira algo más rápido que la aleta; el carro sube y baja para formar el paquete."
    ],
    "figs": [
     [
      "5–20",
      "estiraje en la mechera"
     ],
     [
      "25–70 v/m",
      "torsión de protección"
     ],
     [
      "v/m",
      "= velocidad de la aleta ÷ velocidad de salida"
     ],
     [
      "20–25 m/min",
      "salida habitual (dato de patente)"
     ]
    ],
    "pro": [
     "Material de alimentación adecuado para la continua de anillos"
    ],
    "con": [
     "Mecanismo de bobinado complejo",
     "Demasiada torsión perturba el estiraje; muy poca provoca estirajes falsos y roturas"
    ],
    "when": "Solo para hilatura de anillo y compacta: la hilatura de rotor y de chorro de aire trabajan directamente de la cinta."
   },
   {
    "n": "Hilatura de anillo",
    "de": "Estiraje, torsión mediante huso y cursor, bobinado en la husada",
    "v": [
     "convencional",
     "compacta"
    ],
    "st": [
     "1 · Estiraje en el tren de estiraje",
     "2 · Triángulo de hilatura / condensación",
     "3 · Torsión mediante huso y cursor",
     "4 · Bobinado en la husada"
    ],
    "cap": [
     "Estiraje en el tren de estiraje",
     "Triángulo de hilatura: aquí se tuerce – las fibras de borde sobresalen",
     "El huso gira, el cursor lo sigue: torsión",
     "Bobinado en la husada"
    ],
    "capC": [
     "Estiraje en el tren de estiraje",
     "Condensación: el triángulo de hilatura casi desaparece",
     "El huso gira, el cursor lo sigue: torsión",
     "Bobinado en la husada"
    ],
    "lab": {
     "bobbin": "Bobina de mecha",
     "draft": "Tren de estiraje (estiraje 15–40)",
     "cond": "Condensación (aspiración)",
     "tri": "Triángulo de hilatura",
     "ring": "Anillo + cursor",
     "balloon": "Balón del hilo",
     "rail": "Banco de anillos",
     "lupeC": "Hilo bajo la lupa: compacto",
     "lupeK": "Hilo bajo la lupa: convencional",
     "hairC": "pocas fibras sobresalientes",
     "hairK": "fibras de borde sobresalientes = vellosidad"
    },
    "how": [
     "La mecha se estira hasta el título final en el tren de estiraje.",
     "El huso gira; el hilo arrastra el cursor sobre el anillo. Cada vuelta del balón da una vuelta de torsión, que sube hasta justo antes del cilindro de salida.",
     "Allí queda un triángulo de hilatura sin torsión: las fibras de borde se integran mal y sobresalen (vellosidad).",
     "La hilatura compacta agrupa las fibras con aspiración tras el tren de estiraje: el triángulo casi desaparece y el hilo resulta más liso y resistente."
    ],
    "figs": [
     [
      "15–40",
      "estiraje en la continua de anillos"
     ],
     [
      "15–27 m/min",
      "velocidad de salida habitual"
     ],
     [
      "Ne 6–200",
      "gama de títulos"
     ],
     [
      "desde 1828",
      "principio prácticamente sin cambios"
     ]
    ],
    "pro": [
     "Universal, hilos finísimos, alta resistencia",
     "Compacta: menos vellosidad, menos torsión con la misma resistencia"
    ],
    "con": [
     "Lenta: la fricción cursor–anillo y el calor limitan la velocidad",
     "Husadas pequeñas: hace falta rebobinar",
     "Mechera adicional"
    ],
    "when": "Proceso universal, sobre todo para hilos finos y de alta calidad."
   },
   {
    "n": "Hilatura de rotor",
    "de": "Open-end: separar fibras y volver a reunirlas en un rotor que gira muy rápido",
    "st": [
     "1 · Cinta alimentada directamente",
     "2 · El cilindro disgregador separa",
     "3 · Transporte en la corriente de aire",
     "4 · Acumulación en la ranura del rotor",
     "5 · Torsión y extracción"
    ],
    "cap": [
     "Cinta alimentada directamente – sin mechera",
     "El cilindro disgregador peina fibras individuales",
     "La corriente de aire endereza y acelera las fibras",
     "Las fibras se acumulan en la ranura del rotor",
     "El rotor da torsión, el hilo se extrae"
    ],
    "lab": {
     "sliver": "Cinta (directa)",
     "opener": "Cilindro disgregador",
     "channel": "Canal de fibras (corriente de aire)",
     "rotor": "Rotor (vista superior) con ranura, centro: tobera de extracción",
     "pkg": "Bobina cruzada"
    },
    "how": [
     "La cinta se alimenta directamente, sin mechera.",
     "Un cilindro disgregador rápido peina fibras individuales y separa la suciedad.",
     "Una corriente de aire lleva las fibras por un canal que se estrecha hasta el rotor; se deslizan a la ranura del rotor y forman allí un anillo de fibras (doblado inverso).",
     "El extremo del hilo gira con el rotor e integra las fibras; el hilo se extrae por la tobera y se enrolla directamente en una bobina cruzada. Las fibras que caen atravesadas sobre el hilo forman fibras envolventes (cinturones)."
    ],
    "figs": [
     [
      "60 000–150 000",
      "rpm del rotor"
     ],
     [
      "6 000–9 000",
      "rpm del cilindro disgregador"
     ],
     [
      "Ne 5–40",
      "gama de títulos típica"
     ],
     [
      "80–85 %",
      "resistencia en comparación con el hilo de anillo"
     ]
    ],
    "pro": [
     "Muy productiva, sin mechera ni rebobinado",
     "Hilo uniforme y resistente a la abrasión"
    ],
    "con": [
     "Solo títulos medios a gruesos",
     "Menor resistencia, tacto más áspero (fibras envolventes)"
    ],
    "when": "Denim, rizo, mantas, calcetines, camisetas: medio a grueso."
   },
   {
    "n": "Chorro de aire",
    "de": "Un remolino de aire envuelve un núcleo paralelo con fibras como manto",
    "st": [
     "1 · Alto estiraje en el tren de estiraje",
     "2 · Entrada en la tobera",
     "3 · Remolino de aire alrededor de la punta del huso",
     "4 · Extracción por el huso hueco"
    ],
    "cap": [
     "Alto estiraje en el tren de estiraje",
     "La cinta de fibras entra en la tobera",
     "Remolino: los extremos libres se enrollan en la punta del huso",
     "El hilo núcleo-manto se extrae por el huso hueco"
    ],
    "lab": {
     "sliver": "Cinta de manuar",
     "draft": "Tren de estiraje (alto estiraje)",
     "nozzle": "Tobera con huso hueco",
     "spindle": "Huso hueco",
     "air": "Aire comprimido",
     "pkg": "Bobina",
     "struct": "Estructura: núcleo paralelo, manto envolvente"
    },
    "how": [
     "Una cinta de manuar se estira directamente hasta el título final en el tren de estiraje.",
     "La cinta de fibras entra en una tobera; el aire comprimido crea un remolino alrededor de la punta de un huso hueco fijo.",
     "El remolino enrolla los extremos libres de las fibras alrededor del núcleo: se forma un hilo núcleo-manto con núcleo paralelo.",
     "El hilo se extrae por el huso hueco y se enrolla directamente en una bobina cruzada."
    ],
    "figs": [
     [
      "hasta 450 m/min",
      "velocidad de salida"
     ],
     [
      "≈ 20×",
      "más rápido que la hilatura de anillo (dato de la fuente)"
     ],
     [
      "Ne 12–40",
      "gama de títulos típica"
     ],
     [
      "muy baja",
      "vellosidad"
     ]
    ],
    "pro": [
     "La mayor velocidad de salida",
     "Muy poca vellosidad, poca abrasión y poca borra volante en los procesos posteriores"
    ],
    "con": [
     "No rentable por debajo de aprox. Ne 12 (más grueso)",
     "Tacto más áspero; la longitud y el tipo de fibra influyen mucho"
    ],
    "when": "Títulos medios, a menudo mezclas con poliéster o viscosa, tejidos de punto y de calada."
   }
  ],
  "cmp": {
   "struct": [
    [
     "Hilo de anillo",
     "todas las fibras en hélice, fibras de borde sobresalientes"
    ],
    [
     "Hilo compacto",
     "en hélice, apenas fibras sobresalientes"
    ],
    [
     "Hilo de rotor",
     "núcleo torcido, fibras envolventes atravesadas"
    ],
    [
     "Hilo de chorro de aire",
     "núcleo paralelo, manto envolvente"
    ]
   ],
   "head": [
    "Característica",
    "Anillo",
    "Compacto",
    "Rotor",
    "Chorro de aire"
   ],
   "rows": [
    [
     "Alimentación",
     "mecha (mechera)",
     "mecha (mechera)",
     "cinta de manuar",
     "cinta de manuar"
    ],
    [
     "Torsión por",
     "huso + cursor (balón)",
     "como anillo, fibras condensadas antes",
     "rotor giratorio",
     "remolino de aire en el huso hueco"
    ],
    [
     "Velocidad de salida",
     "15–27 m/min",
     "similar al anillo",
     "130–250 m/min",
     "hasta 450 m/min"
    ],
    [
     "Gama de títulos",
     "Ne 6–200",
     "fino a muy fino",
     "Ne 5–40 (hasta ~60)",
     "Ne 12–40"
    ],
    [
     "Estructura del hilo",
     "torsión real, todas las fibras",
     "torsión real, liso",
     "núcleo + fibras envolventes",
     "núcleo + manto"
    ],
    [
     "Típico",
     "universal, fino, resistente",
     "premium, poca vellosidad",
     "denim, rizo, calcetines",
     "punto, mezclas, poca vellosidad"
    ],
    [
     "Mayor límite",
     "velocidad (cursor)",
     "velocidad (cursor)",
     "finura, resistencia",
     "hilos gruesos, tacto"
    ]
   ],
   "note": "Valores de material didáctico y artículos técnicos; varían según la fibra, el título y la fuente. Para la hilatura compacta, las fuentes indican un 10 % o un 20 % menos de torsión con la misma resistencia."
  },
  "twist": {
   "tw": "Torsión",
   "sp": "Huso (anillo)",
   "ro": "Rotor",
   "tpm": "v/m",
   "rpm": "rpm",
   "bars": [
    "Hilatura de anillo",
    "Hilatura de rotor",
    "Chorro de aire (fuente)"
   ],
   "why": [
    "(huso ÷ torsión)",
    "(rotor ÷ torsión)",
    "(dato del fabricante, otro mecanismo)"
   ],
   "note": "Cálculo nominal sin pérdida de torsión, deslizamiento ni paradas. En la hilatura por chorro de aire, la torsión la produce un remolino de aire; allí la fórmula no se aplica directamente."
  },
  "wool": [
   [
    "Estambre (peinado)",
    "Lavado → carda → gills (manuares de agujas) → peinado → gills → peinado en cinta (top) → mecha → hilatura. Fibras largas y muy paralelas: hilo liso, fino y resistente."
   ],
   [
    "Cardado",
    "Lavado → carda → hilatura. Ruta corta sin peinado y con poco estiraje: las fibras quedan entrecruzadas – hilo voluminoso, suave y más áspero. Aquí se aprovecha la borra de la hilatura de estambre."
   ],
   [
    "Semipeinado",
    "Lavado → carda → varios gills → hilatura. Intermedio: estirado, pero no peinado."
   ],
   [
    "Lana en instalaciones de algodón",
    "Las lanas más cortas, normalmente mezcladas con algodón o poliéster, también pasan por la línea de fibra corta; a veces incluso se hilan en rotor."
   ]
  ],
  "links": [
   [
    "Hilatura por chorro de aire",
    "Nuestra tecnología: estiraje, remolino en la tobera, fibras de núcleo y envolventes en detalle."
   ],
   [
    "Hilatura de filamento",
    "El polo opuesto: filamentos continuos de la masa fundida en lugar de fibras cortas del copo."
   ],
   [
    "Preparación de tejeduría",
    "Lo que viene después de hilar: bobinado, urdido, encolado y remetido."
   ],
   [
    "Tejido circular",
    "Adonde van muchos hilos de fibra corta: tejido de punto en la máquina circular."
   ],
   [
    "Tintura",
    "Clases de colorantes, etapas de tintura desde la fibra suelta hasta la pieza, procesos por agotamiento y continuos."
   ]
  ]
 },
 "zh": {
  "ui": {
   "eyebrow": "Knowledge Base · 短纤纺纱",
   "h1": "短纤纺纱：从纤维棉束到纱线",
   "lead": "棉花和其他短纤维在成纱之前要经过一条很长的工序链：开松、清理、混合、梳理、并条，视质量要求进行精梳，牵伸成粗纱，最后纺纱。本页以可逐步控制的动画示意图展示各道工艺及其技术——从开包到环锭纺、紧密纺、转杯纺和喷气纺。机器和制造商有意不在本页讨论范围内。",
   "note": "示意图经过大幅简化。数值来自教材和专业文章，随纤维、纱支和资料来源而有差异。",
   "sources": "资料来源",
   "open": "打开模块",
   "loc": "none",
   "prev": "◀ 上一步",
   "next": "下一步 ▶",
   "play": "▶ 播放",
   "pause": "暂停",
   "lkL": "Knowledge Base 中的相关内容",
   "how": "目的与流程",
   "figs": "工艺参数",
   "pro": "优点",
   "con": "局限",
   "when": "何时使用？"
  },
  "kpis": [
   [
    "约 40 000",
    "根纤维：一根生条截面中的纤维数"
   ],
   [
    "6–8",
    "根棉条在并条机上并合"
   ],
   [
    "8–25 %",
    "精梳落棉（梳出的短纤维），视目标而定"
   ],
   [
    "最高 150 000",
    "转/分：纺纱转杯的转速"
   ],
   [
    "15–27 对 450",
    "米/分：环锭纺与喷气纺的输出速度"
   ]
  ],
  "scenes": [
   {
    "k": "工艺路线",
    "title": "短纤纺纱的工艺路线",
    "text": "纱线要经过哪些工序，取决于纺纱方法和所需质量。选择一条路线，相关工序会高亮显示。点击某道工序即可打开它的动画。"
   },
   {
    "k": "工艺详解",
    "title": "各道工艺详解",
    "text": "每个示意图都可以播放，也可以逐步前进或后退。示意图经过大幅简化。"
   },
   {
    "k": "纺纱方法对比",
    "title": "纺纱方法对比",
    "text": "四种方法，四种纱线结构。示意图概略展示纤维在纱线中的排列方式。"
   },
   {
    "k": "捻度与速度",
    "title": "捻度与速度：为什么环锭纺很慢",
    "text": "环锭纺和转杯纺遵循同一基本关系：捻度（捻/米）= 转速（转/分）÷ 输出速度（米/分）。因此，在所需捻度一定时，加捻部件的转速决定了生产速度。环锭纺中钢丝圈速度限制了锭子转速；转杯纺中旋转的只是一个小杯，没有管纱。"
   },
   {
    "k": "羊毛专题",
    "title": "羊毛专题：精纺、粗纺、半精纺",
    "text": "羊毛有自己的工艺路线，主要区别在于前纺准备。"
   }
  ],
  "route": {
   "seg": [
    "普梳环锭纱",
    "精梳环锭纱",
    "转杯纱",
    "喷气纱"
   ],
   "nodes": {
    "putzerei": "清花",
    "karde": "梳棉",
    "strecke1": "头道并条",
    "kvor": "精梳准备",
    "kaemmen": "精梳",
    "strecke": "末道并条",
    "flyer": "粗纱",
    "ring": "环锭 / 紧密纺",
    "rotor": "转杯纺",
    "luft": "喷气纺"
   },
   "txt": [
    "普梳环锭纱：清花、梳棉、两道并条、粗纱、环锭细纱。",
    "精梳环锭纱：梳棉之后进行精梳准备（成卷）和精梳，然后末道并条、粗纱和环锭细纱。",
    "转杯纱：路线短——梳棉和并条之后直接以棉条喂入转杯纺纱机，无需粗纱。",
    "喷气纱：梳棉，通常两道并条（必要时也可精梳），然后直接以棉条喂入喷气纺纱机。"
   ]
  },
  "proc": [
   {
    "n": "清花",
    "de": "开包、清理、混合、除尘",
    "st": [
     "1 · 抓棉：同时从所有棉包抓取小棉束",
     "2 · 气流输送",
     "3 · 清理：打手开松，杂质从尘棒间落下",
     "4 · 在错位填充的棉仓中混合",
     "5 · 除尘，向梳棉机供棉"
    ],
    "cap": [
     "同时从所有棉包抓取小棉束",
     "棉束随气流继续输送",
     "开松与清理：杂质从尘棒间落下",
     "混合：棉仓错位填充，同时排出",
     "为梳棉机提供均匀的棉层"
    ],
    "lab": {
     "bales": "棉包排列（不同产地）",
     "pluck": "抓棉",
     "clean": "清棉机：打手 + 尘棒",
     "mix": "混棉机：棉仓",
     "chute": "棉箱给棉 → 梳棉"
    },
    "how": [
     "压紧的棉包被分解成小棉束——棉束越小，表面积越大，杂质越容易落出。",
     "尘棒上方的打手和角钉辊进一步开松棉束；重的杂质落下，粉尘随气流排出。",
     "混棉机平衡各棉包在产地和质量上的差异。",
     "最后由棉箱给棉机为每台梳棉机提供均匀的棉层。"
    ],
    "figs": [
     [
      "200 kg → 约 10 g",
      "抓棉时：棉包 → 棉束"
     ],
     [
      "100–200 mg",
      "预清理后的目标棉束大小（教材值）"
     ],
     [
      "95–99 %",
      "清花和梳棉合计去除的杂质比例"
     ]
    ],
    "pro": [
     "清洁度和均匀混合的基础",
     "温和、逐级开松"
    ],
    "con": [
     "高除杂率几乎总要损失好纤维",
     "每次打击都会损伤纤维，并可能产生棉结"
    ],
    "when": "棉花总是需要；化学纤维几乎不需要清理，但需要开松和混合。"
   },
   {
    "n": "梳棉",
    "de": "分离单纤维，去除棉结和残余杂质，形成棉条",
    "st": [
     "1 · 喂入并握持棉层",
     "2 · 刺辊开松，分离杂质",
     "3 · 锡林与盖板之间梳理",
     "4 · 道夫转移纤维网",
     "5 · 成条并圈放入条筒"
    ],
    "cap": [
     "棉层被喂入并握持",
     "刺辊：开松棉束，分离杂质",
     "锡林与盖板之间梳理：单纤维",
     "道夫形成细薄的纤维网",
     "纤维网 → 棉条 → 条筒"
    ],
    "lab": {
     "chute": "棉箱",
     "flats": "回转盖板",
     "cyl": "锡林（大滚筒）",
     "doffer": "道夫",
     "can": "条筒",
     "licker": "刺辊",
     "feed": "给棉罗拉"
    },
    "how": [
     "给棉罗拉握持棉层，刺辊将其开松成小棉束。",
     "锡林与回转盖板之间针齿相对（针尖对针尖）——棉束被分解为单纤维，棉结和杂质留在盖板中。",
     "速度较慢的道夫将纤维转移成薄纤维网。",
     "喇叭口把纤维网集束成无捻的生条，圈放入条筒。"
    ],
    "figs": [
     [
      "约 40 000",
      "棉条截面中的纤维数"
     ],
     [
      "约 1 %",
      "梳棉去除的短纤维"
     ],
     [
      "80–116",
      "盖板根数，其中 30–46 根参与梳理"
     ],
     [
      "“梳得好……”",
      "……纱就纺成了一半（纺纱谚语）"
     ]
    ],
    "pro": [
     "唯一真正将纤维分离成单纤维的工序",
     "去除棉结、粉尘和部分短纤维"
    ],
    "con": [
     "纤维尚未平行，很多呈弯钩状",
     "棉条均匀度仍不足"
    ],
    "when": "每条短纤纺纱路线都需要。"
   },
   {
    "n": "并条",
    "de": "并合与牵伸：更均匀、更平行",
    "st": [
     "1 · 喂入 6–8 根棉条（并合）",
     "2 · 测量粗细（自调匀整）",
     "3 · 牵伸装置中牵伸",
     "4 · 伸直平行，均匀化",
     "5 · 棉条进入条筒"
    ],
    "cap": [
     "并合：多根棉条一起喂入",
     "为自调匀整测量粗细",
     "牵伸：v1 < v2 < v3",
     "纤维平行，粗细波动相互抵消",
     "一根均匀的棉条进入条筒"
    ],
    "lab": {
     "cans": "6 个条筒 = 6 根生条（并合）",
     "meas": "检测",
     "v3": "v3（最快）",
     "can": "条筒",
     "thickA": "单根棉条粗细：波动",
     "thickB": "熟条粗细：已均匀"
    },
    "how": [
     "多根棉条一起喂入：粗节和细节相互抵消（并合）。这里也可以混合不同纤维，例如棉/涤纶。",
     "在牵伸装置中，每对罗拉都比前一对转得快——棉条被牵伸，纤维被拉直并平行排列。",
     "并合数与牵伸倍数通常大致相同，使棉条粗细保持相近。",
     "自调匀整装置测量棉条粗细并持续调整牵伸。"
    ],
    "figs": [
     [
      "6–8",
      "并合根数"
     ],
     [
      "4–8",
      "牵伸倍数"
     ],
     [
      "350–800 米/分",
      "输出速度"
     ],
     [
      "CV 4–6 % → 1–2 %",
      "带自调匀整时的棉条不匀率"
     ]
    ],
    "pro": [
     "对均匀度最重要的工序",
     "非常适合混合不同纤维"
    ],
    "con": [
     "只能较好地消除短波和中波不匀",
     "需要多道（头道和末道并条）"
    ],
    "when": "所有路线都需要，通常两道。"
   },
   {
    "n": "精梳",
    "de": "梳除短纤维和棉结——用于更细、更光洁的纱线",
    "st": [
     "1 · 喂给，钳板握持",
     "2 · 圆梳梳理须丛",
     "3 · 钳板张开并前移——搭接",
     "4 · 通过顶梳分离",
     "5 · 钳板后退，新周期"
    ],
    "cap": [
     "喂给：钳板握持小卷",
     "圆梳梳理须丛——去除短纤维和棉结",
     "钳板张开前移，分离罗拉倒转：搭接",
     "分离：须丛被拉过顶梳",
     "钳板后退——新周期"
    ],
    "lab": {
     "lap": "小卷",
     "open": "钳板张开",
     "closed": "钳板闭合",
     "circ": "圆梳",
     "top": "顶梳",
     "detach": "分离罗拉",
     "sliver": "精梳条",
     "noil": "落棉（吸走）"
    },
    "how": [
     "准备：把生条制成小卷，使纤维有序喂入。",
     "钳板握持小卷，圆梳梳理伸出的须丛——未被握持的部分（短纤维、棉结）留在梳针中。",
     "钳板前移，梳过的须丛与前一段棉网搭接，并由分离罗拉拉过顶梳，顶梳梳理须丛尾端。",
     "落棉被吸走；棉网汇合成精梳条。"
    ],
    "figs": [
     [
      "8–25 %",
      "落棉率，视目标而定"
     ],
     [
      "落棉率 %",
      "= 落棉 ÷ 喂入质量 × 100"
     ],
     [
      "间歇式",
      "按周期梳理，而非连续"
     ]
    ],
    "pro": [
     "纱线更细、更光洁、更强、更均匀",
     "棉结更少，光泽更好"
    ],
    "con": [
     "材料损失（落棉）",
     "额外的工序和成本"
    ],
    "when": "细支高档棉纱（衬衫、精细针织）。"
   },
   {
    "n": "粗纱",
    "de": "将棉条牵伸成粗纱，并加保护捻度卷绕",
    "st": [
     "1 · 棉条从条筒引出",
     "2 · 牵伸成细的粗纱",
     "3 · 锭翼加保护捻度",
     "4 · 卷绕到筒管上"
    ],
    "cap": [
     "棉条从条筒引出",
     "牵伸成细的粗纱",
     "锭翼加保护捻度（25–70 捻/米）",
     "卷绕到粗纱筒管上"
    ],
    "lab": {
     "can": "熟条",
     "draft": "牵伸装置（牵伸 5–20）",
     "flyer": "锭翼旋转",
     "rail": "龙筋升降"
    },
    "how": [
     "熟条对环锭细纱机的牵伸来说太粗，而且条筒不是好的喂入形式。",
     "粗纱机把棉条牵伸成细的粗纱。",
     "锭翼绕筒管旋转，加上少量保护捻度——足以让粗纱保持完整，又少到以后还能再次牵伸。",
     "筒管比锭翼转得稍快；龙筋上下升降以完成卷装成形。"
    ],
    "figs": [
     [
      "5–20",
      "粗纱机牵伸倍数"
     ],
     [
      "25–70 捻/米",
      "保护捻度"
     ],
     [
      "捻/米",
      "= 锭翼转速 ÷ 输出速度"
     ],
     [
      "20–25 米/分",
      "常见输出速度（专利数据）"
     ]
    ],
    "pro": [
     "为环锭细纱机提供合适的喂入材料"
    ],
    "con": [
     "卷绕机构复杂",
     "捻度过大妨碍牵伸，过小会导致意外牵伸和断头"
    ],
    "when": "仅用于环锭纺和紧密纺——转杯纺和喷气纺直接以棉条喂入。"
   },
   {
    "n": "环锭纺",
    "de": "牵伸，通过锭子和钢丝圈加捻，卷绕成管纱",
    "v": [
     "传统",
     "紧密"
    ],
    "st": [
     "1 · 牵伸装置中牵伸",
     "2 · 纺纱三角区 / 集聚",
     "3 · 通过锭子和钢丝圈加捻",
     "4 · 卷绕成管纱"
    ],
    "cap": [
     "牵伸装置中牵伸",
     "纺纱三角区：在此加捻——边缘纤维伸出",
     "锭子旋转，钢丝圈随行：加捻",
     "卷绕成管纱"
    ],
    "capC": [
     "牵伸装置中牵伸",
     "集聚：纺纱三角区几乎消失",
     "锭子旋转，钢丝圈随行：加捻",
     "卷绕成管纱"
    ],
    "lab": {
     "bobbin": "粗纱筒管",
     "draft": "牵伸装置（牵伸 15–40）",
     "cond": "集聚（负压）",
     "tri": "纺纱三角区",
     "ring": "钢领 + 钢丝圈",
     "balloon": "气圈",
     "rail": "钢领板",
     "lupeC": "放大镜下的纱线：紧密纺",
     "lupeK": "放大镜下的纱线：传统环锭纺",
     "hairC": "伸出的纤维很少",
     "hairK": "伸出的边缘纤维 = 毛羽"
    },
    "how": [
     "粗纱在牵伸装置中被牵伸到最终纱支。",
     "锭子旋转，纱线拖动钢丝圈沿钢领运行。气圈每转一圈就加上一个捻回，捻回一直传到前罗拉附近。",
     "那里留下一个无捻的纺纱三角区——边缘纤维难以捻入而伸出（毛羽）。",
     "紧密纺在牵伸装置之后用负压集聚纤维：纺纱三角区几乎消失，纱线更光洁、更强。"
    ],
    "figs": [
     [
      "15–40",
      "环锭细纱机牵伸倍数"
     ],
     [
      "15–27 米/分",
      "常见输出速度"
     ],
     [
      "Ne 6–200",
      "纱支范围"
     ],
     [
      "始于 1828 年",
      "原理几乎未变"
     ]
    ],
    "pro": [
     "通用，可纺最细的纱，强力高",
     "紧密纺：毛羽更少，同等强力下捻度更低"
    ],
    "con": [
     "慢：钢丝圈与钢领的摩擦和发热限制转速",
     "管纱小——需要络筒",
     "额外需要粗纱工序"
    ],
    "when": "通用工艺，尤其适合细支和高档纱线。"
   },
   {
    "n": "转杯纺",
    "de": "自由端纺纱：把纤维分离，再在高速旋转的转杯中重新凝聚",
    "st": [
     "1 · 棉条直接喂入",
     "2 · 分梳辊分离纤维",
     "3 · 气流输送",
     "4 · 在转杯凝聚槽中凝聚",
     "5 · 加捻并引出"
    ],
    "cap": [
     "棉条直接喂入——无需粗纱",
     "分梳辊梳出单纤维",
     "气流使纤维伸直并加速",
     "纤维在转杯凝聚槽中凝聚",
     "转杯加捻，纱线被引出"
    ],
    "lab": {
     "sliver": "棉条（直接）",
     "opener": "分梳辊",
     "channel": "输纤通道（气流）",
     "rotor": "转杯（俯视）带凝聚槽，中心：引纱罩",
     "pkg": "筒子"
    },
    "how": [
     "棉条直接喂入——无需粗纱。",
     "高速分梳辊梳出单纤维并排除杂质。",
     "气流把纤维经过渐缩的通道送入转杯；纤维滑入凝聚槽，在那里形成纤维环（并合效应）。",
     "纱尾随转杯旋转并把纤维捻入；纱线经引纱罩引出，直接卷绕成筒子。横跨纱线落下的纤维形成缠绕纤维（腰带纤维）。"
    ],
    "figs": [
     [
      "60 000–150 000",
      "转/分：转杯"
     ],
     [
      "6 000–9 000",
      "转/分：分梳辊"
     ],
     [
      "Ne 5–40",
      "典型纱支范围"
     ],
     [
      "80–85 %",
      "强力（与环锭纱相比）"
     ]
    ],
    "pro": [
     "产量很高，无需粗纱和络筒",
     "纱线均匀、耐磨"
    ],
    "con": [
     "只适合中粗纱支",
     "强力较低，手感较硬（缠绕纤维）"
    ],
    "when": "牛仔布、毛巾、毯子、袜子、T 恤——中粗支。"
   },
   {
    "n": "喷气纺",
    "de": "气流涡流把纤维作为外包层缠绕在平行的纱芯上",
    "st": [
     "1 · 牵伸装置中高倍牵伸",
     "2 · 进入喷嘴",
     "3 · 锭尖周围的气流涡流",
     "4 · 经空心锭子引出"
    ],
    "cap": [
     "牵伸装置中高倍牵伸",
     "纤维须条进入喷嘴",
     "气流涡流：自由纤维端缠绕在锭尖周围",
     "芯鞘结构纱经空心锭子引出"
    ],
    "lab": {
     "sliver": "熟条",
     "draft": "牵伸装置（高倍牵伸）",
     "nozzle": "带空心锭子的喷嘴",
     "spindle": "空心锭子",
     "air": "压缩空气",
     "pkg": "筒子",
     "struct": "结构：平行纱芯，缠绕外包层"
    },
    "how": [
     "熟条在牵伸装置中直接牵伸到最终纱支。",
     "纤维须条进入喷嘴；压缩空气在固定空心锭子的锭尖周围形成涡流。",
     "涡流把自由纤维端缠绕在纱芯上——形成纱芯平行的芯鞘结构纱。",
     "纱线经空心锭子引出，直接卷绕成筒子。"
    ],
    "figs": [
     [
      "最高 450 米/分",
      "输出速度"
     ],
     [
      "约 20 倍",
      "环锭纺的速度（资料数据）"
     ],
     [
      "Ne 12–40",
      "典型纱支范围"
     ],
     [
      "很低",
      "毛羽"
     ]
    ],
    "pro": [
     "输出速度最高",
     "毛羽很少，后道加工中磨损和飞花少"
    ],
    "con": [
     "比约 Ne 12 更粗的纱不经济",
     "手感较硬；纤维长度和种类影响很大"
    ],
    "when": "中等纱支，常与涤纶或粘胶混纺，用于针织和机织物。"
   }
  ],
  "cmp": {
   "struct": [
    [
     "环锭纱",
     "所有纤维呈螺旋状，边缘纤维伸出"
    ],
    [
     "紧密纱",
     "螺旋状，几乎没有伸出的纤维"
    ],
    [
     "转杯纱",
     "纱芯加捻，外有横向缠绕纤维"
    ],
    [
     "喷气纱",
     "平行纱芯，缠绕外包层"
    ]
   ],
   "head": [
    "特征",
    "环锭",
    "紧密",
    "转杯",
    "喷气"
   ],
   "rows": [
    [
     "喂入",
     "粗纱（粗纱机）",
     "粗纱（粗纱机）",
     "熟条",
     "熟条"
    ],
    [
     "加捻方式",
     "锭子 + 钢丝圈（气圈）",
     "同环锭，纤维先集聚",
     "旋转的转杯",
     "空心锭子周围的气流涡流"
    ],
    [
     "输出速度",
     "15–27 米/分",
     "与环锭相近",
     "130–250 米/分",
     "最高 450 米/分"
    ],
    [
     "纱支范围",
     "Ne 6–200",
     "细到很细",
     "Ne 5–40（最高约 60）",
     "Ne 12–40"
    ],
    [
     "纱线结构",
     "真捻，全部纤维",
     "真捻，光洁",
     "纱芯 + 缠绕纤维",
     "纱芯 + 外包层"
    ],
    [
     "典型用途",
     "通用、细、强",
     "高档、毛羽少",
     "牛仔布、毛巾、袜子",
     "针织、混纺、毛羽少"
    ],
    [
     "最大局限",
     "速度（钢丝圈）",
     "速度（钢丝圈）",
     "纱支、强力",
     "粗纱支、手感"
    ]
   ],
   "note": "数值来自教材和专业文章，随纤维、纱支和资料来源而有差异。对于紧密纺，资料给出在同等强力下捻度可降低 10 % 或 20 %。"
  },
  "twist": {
   "tw": "捻度",
   "sp": "锭子（环锭）",
   "ro": "转杯",
   "tpm": "捻/米",
   "rpm": "转/分",
   "bars": [
    "环锭纺",
    "转杯纺",
    "喷气纺（资料）"
   ],
   "why": [
    "（锭速 ÷ 捻度）",
    "（杯速 ÷ 捻度）",
    "（制造商数据，机理不同）"
   ],
   "note": "名义计算，未考虑捻度损失、滑移和停机。喷气纺的捻度来自气流涡流，此公式不能直接适用。"
  },
  "wool": [
   [
    "精纺毛纱",
    "洗毛 → 梳毛 → 针梳 → 精梳 → 针梳 → 毛条 → 粗纱 → 细纱。纤维长且高度平行——纱线光洁、细、强。"
   ],
   [
    "粗纺毛纱",
    "洗毛 → 梳毛 → 纺纱。路线短，无精梳且牵伸小：纤维纵横交错——纱线蓬松、柔软、较粗糙。精纺产生的精梳落毛在这里得到利用。"
   ],
   [
    "半精纺毛纱",
    "洗毛 → 梳毛 → 多道针梳 → 纺纱。介于两者之间：经过牵伸，但不精梳。"
   ],
   [
    "羊毛在棉纺设备上",
    "较短的羊毛通常与棉或涤纶混合，也可在短纤路线上加工——偶尔也用转杯纺。"
   ]
  ],
  "links": [
   [
    "喷气涡流纺纱",
    "我们的技术：牵伸、纺纱喷嘴中的涡流、芯纤维与包缠纤维详解。"
   ],
   [
    "长丝纺丝",
    "对照：从熔体纺出的连续长丝，而不是来自棉束的短纤维。"
   ],
   [
    "织造准备",
    "纺纱之后的工序：络筒、整经、浆纱和穿经。"
   ],
   [
    "圆机针织",
    "许多短纤纱的去处：在圆机上织成针织物。"
   ],
   [
    "染色",
    "染料类别、从散纤维到织物的染色阶段、浸染和连续工艺。"
   ]
  ]
 }
};
