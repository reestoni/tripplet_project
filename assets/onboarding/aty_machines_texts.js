window.TEXTS = {
 "de": {
  "ui": {
   "eyebrow": "Knowledge Base · ATY",
   "h1": "ATY-Maschinen: Hersteller, Bauformen & Varianten",
   "lead": "Interaktive Übersicht über Lufttexturiermaschinen (Air Jet Texturing): Ein Überschall-Luftstrahl in der Texturierdüse verwirbelt überlieferte Filamente zu Schlingen und gibt dem glatten Filament einen spinngarnähnlichen Charakter. Alle Abbildungen sind schematische Visualisierungen, nicht massstäblich.",
   "note": "Stand der Recherche: November 2026. Herstellerangaben können je nach Ausführung abweichen.",
   "sources": "Quellen",
   "component": "Komponente",
   "tip": "Tipp: Die Schalter oben ändern Vorlage, Garnaufbau, Benetzung und Nachbehandlung.",
   "openAty": "→ ATY-Lufttexturierung",
   "openAtyHint": "Wie die Düse im Detail arbeitet, zeigt das Modul zur ATY-Lufttexturierung.",
   "examples": "Beispiele",
   "pros": "Vorteile",
   "cons": "Nachteile",
   "search": "Suche",
   "searchPh": "Modell, Hersteller, Merkmal …",
   "region": "Region",
   "operation": "Bedienung",
   "all": "Alle",
   "regions": [
    "Europa",
    "Japan",
    "China",
    "Indien"
   ],
   "autodoff": "Autodoff",
   "manual": "Manuell",
   "treeFilter": "Filter aus Variantenschema:",
   "reset": "zurücksetzen",
   "empty": "Keine Modelle für diese Filterkombination.",
   "upTo": "bis {n} Pos.",
   "source": "Quelle: {d}",
   "sortPos": "Positionen (max.)",
   "sortSpeed": "mech. Geschwindigkeit (m/min)",
   "barsNote": "Mechanische Maximalgeschwindigkeit laut Hersteller; die Prozessgeschwindigkeit hängt stark von Titer, Überlieferung und Düse ab und liegt typischerweise deutlich darunter (in Forschungsversuchen z. B. 200–600 m/min).",
   "classif": "Einordnung",
   "ariaProc": "Schematischer Fadenlauf einer ATY-Position",
   "ariaProf": "Maschinenbauform",
   "treeHint": "Klick auf eine Ausprägung: Das Kapitel Hersteller & Modelle öffnet sich gefiltert."
  },
  "scenes": [
   {
    "k": "Prozess",
    "title": "Der Fadenlauf einer ATY-Position",
    "text": "Die Lieferwerke führen der Düse mehr Garn zu, als dahinter abgezogen wird (Überlieferung). Im Luftstrahl bilden die überschüssigen Filamentlängen Schlingen, die im Garnkern verankert werden. Danach wird das Garn mechanisch stabilisiert und aufgewickelt. Klick auf eine Komponente; die Schalter zeigen die Varianten."
   },
   {
    "k": "Variantenschema",
    "title": "Variantenschema",
    "text": "Klick auf eine Ausprägung, um die passenden Hersteller und Modelle im Kapitel Hersteller & Modelle zu filtern."
   },
   {
    "k": "Bauformen",
    "title": "Maschinenbauformen",
    "text": "Lufttexturiermaschinen sind deutlich niedriger als DTY-Maschinen; die Bauformen unterscheiden sich vor allem darin, wie viele Positionen ein Antrieb versorgt und wie das Doffing gelöst ist."
   },
   {
    "k": "Hersteller & Modelle",
    "title": "Hersteller & Modelle",
    "text": "Kennzahlen aus Herstellerangaben, Fachpresse und Katalogen (siehe Quellen)."
   },
   {
    "k": "Vergleich",
    "title": "Vergleich",
    "text": "ATY-Maschinen sind viel kleiner als DTY-Maschinen: wenige Dutzend bis gut 200 Positionen, dafür ein sehr breiter Titerbereich bis in technische Garne."
   },
   {
    "k": "Markt",
    "title": "Marktstruktur & Entwicklung",
    "text": "Wichtige Ereignisse der Branche und eine Einordnung der Anbieter."
   }
  ],
  "ctl": [
   {
    "l": "Vorlage",
    "o": [
     "POY (mit Verstreckung)",
     "FDY"
    ]
   },
   {
    "l": "Garnaufbau",
    "o": [
     "Kern / Effekt",
     "Parallel"
    ]
   },
   {
    "l": "Benetzung",
    "o": [
     "nass",
     "trocken"
    ]
   },
   {
    "l": "Nachbehandlung",
    "o": [
     "mechanisch",
     "+ Heizer"
    ]
   }
  ],
  "comp": {
   "creel": {
    "t": "Gatter",
    "tags": [
     "Kern- und Effektfäden"
    ],
    "p": "Für Kern/Effekt-Garne laufen pro Position mehrere Vorlagespulen ein: Kernfäden (geringe Überlieferung, bilden die tragende Seele) und Effektfäden (hohe Überlieferung, bilden die Schlingen an der Oberfläche).",
    "l": [
     "SSM DP5-T: Rotationsgatter bis 6 Fäden plus Reserve",
     "Auch Glas-, Aramid- und Mischgarne möglich"
    ]
   },
   "feed": {
    "t": "Lieferwerke & Verstreckung",
    "tags": [
     "Überlieferung"
    ],
    "poy": "POY-Vorlage: Zwischen zwei Lieferwerken wird über einen Heizstift verstreckt, bevor das Garn in die Düse läuft (z. B. AIKI AT-501: 4 Lieferwerke + Heizstift). Der Heizstift erlaubt auch einfache Dick-Dünn-Effekte.",
    "fdy": "FDY-Vorlage: Das Garn ist bereits verstreckt; ein Lieferwerk pro Fadengruppe stellt nur die Überlieferung ein.",
    "l": [
     "Überlieferung = (v Lieferwerk – v Abzug) / v Abzug",
     "Kern typisch ~5–30 %, Effekt bis 200 % und mehr",
     "Kern- und Effektlieferwerk getrennt regelbar (Fadis: Kern- und Effekt-Galette)"
    ]
   },
   "wet": {
    "t": "Benetzung",
    "tags": [
     "Wasser"
    ],
    "wet": "Der Kernfaden wird vor der Düse durch ein Wasserbad, einen Benetzungskopf oder eine Tropfdüse geführt. Wasser reduziert die Reibung zwischen den Filamenten und verbessert Schlingenbildung und Stabilität – in der Praxis Standard.",
    "dry": "Trocken texturiert bilden sich weniger stabile Schlingen; trocken wird eher bei einfachen Verwirbelungsaufgaben oder speziellen Materialien gearbeitet.",
    "l": [
     "Effektfäden laufen meist trocken an der Benetzung vorbei"
    ]
   },
   "jet": {
    "t": "Texturierdüse",
    "tags": [
     "Herzstück",
     "Überschall"
    ],
    "p": "Druckluft (typ. 6–9 bar) expandiert in der Düse auf Überschallgeschwindigkeit; die Filamente werden aufgespreizt, die überlieferten Längen bilden Schlingen und werden im Garnkern verankert. Am Austritt sitzt oft ein Prallkörper (Baffle), der die Strömung beruhigt.",
    "l": [
     "Düsengeometrie bestimmt Garncharakter und Luftverbrauch",
     "Typischer Industriestandard und Forschungsreferenz: Heberlein HemaJet (u. a. in der Fadis Aquajet verbaut)",
     "Bei Kombimaschinen auch Luftumwinde-Düsen für Elastan"
    ]
   },
   "stab": {
    "t": "Stabilisierungszone",
    "tags": [
     "mechanisch"
    ],
    "p": "Zwischen zwei Lieferwerken wird das texturierte Garn leicht nachverstreckt (etwa 1–15 %). Lose, instabile Schlingen werden dabei herausgezogen; die Spannung in dieser Zone ist ein Mass dafür, wie gut die Düse arbeitet.",
    "l": []
   },
   "heat": {
    "t": "Heizer (thermische Nachbehandlung)",
    "tags": [
     "optional"
    ],
    "p": "Ein Heizrohr oder eine beheizte Galette nach der Düse fixiert das Garn thermisch, reduziert den Restschrumpf oder stellt die Schlingengrösse ein (AIKI: „ATY loop can be adjusted with the second heater“). SSM verwendet beheizte Galetten.",
    "l": [
     "Wichtig für Garne, die später gefärbt oder heissfixiert werden"
    ]
   },
   "wind": {
    "t": "Aufwicklung",
    "tags": [
     "Spule"
    ],
    "p": "Kreuzspulen mit wilder, Präzisions- oder Stufenpräzisionswicklung (SSM DIGICONE). ATY-Maschinen arbeiten mit deutlich langsameren Prozessgeschwindigkeiten als DTY und mit grossen Titern.",
    "l": [
     "Manuell, mit Frontal-Doffer (TG2-AT) oder Autodoff",
     "Optional Fancy-Einrichtungen für Slubs und Dick-Dünn"
    ]
   },
   "eff": {
    "t": "Effektfaden",
    "tags": [
     "hohe Überlieferung"
    ],
    "p": "Der Effektfaden wird stark überliefert und bildet die sichtbaren Schlingen; bei POY wird er ebenfalls über einen Heizstift verstreckt. Unterschiedliche Farben, Titer oder Materialien in Kern und Effekt ergeben Melange- und Strukturgarne.",
    "l": []
   }
  },
  "sv": {
   "core": "Kern",
   "effect": "Effekt",
   "creel": "Gatter",
   "heatPin": "Heizstift",
   "feedCore": "Lieferwerk Kern",
   "wetting": "Benetzung",
   "dry": "trocken",
   "coreOf": "Kern: geringe Überlieferung",
   "allOf": "alle Fäden: gleiche Überlieferung",
   "effOf": "Effekt: hohe Überlieferung (bis 200 %+)",
   "air": "Druckluft 6–9 bar",
   "jet": "Texturierdüse",
   "baffle": "+ Prallkörper",
   "stab": "Stabilisierung",
   "stabOf": "1–15 % Nachverzug",
   "heater": "Heizer",
   "wind": "Aufwicklung",
   "speed": "Prozess typ. 200–600 m/min"
  },
  "dims": [
   {
    "t": "Vorlagegarn",
    "o": [
     {
      "b": "POY (mit Verstreckung)",
      "d": "Heizstift oder Heizgalette vor der Düse."
     },
     {
      "b": "FDY / FOY",
      "d": "Bereits verstreckt, nur Überlieferung."
     }
    ]
   },
   {
    "t": "Garnaufbau",
    "o": [
     {
      "b": "Kern / Effekt",
      "d": "Unterschiedliche Überlieferung, Struktur- und Melangegarne."
     },
     {
      "b": "Effektgarne",
      "d": "Slubs, Dick-Dünn (T&T)."
     },
     {
      "b": "Kombiniert mit DTY / Elastan",
      "d": "Falschdraht + Luft oder Luftumwinden."
     }
    ]
   },
   {
    "t": "Prozess",
    "o": [
     {
      "b": "Nassbehandlung betont",
      "d": "Benetzungskopf / Nassbox."
     },
     {
      "b": "Thermische Nachbehandlung",
      "d": "Heizer oder Heizgalette nach der Düse."
     }
    ]
   },
   {
    "t": "Bauform",
    "o": [
     {
      "b": "Einzelposition",
      "d": "Jede Position eigene Antriebe (DP5-T)."
     },
     {
      "b": "Doppelseitig, Wellen",
      "d": "Viele Positionen, Frontal-Doffer (TG2-AT)."
     },
     {
      "b": "Klassische Wellenmaschine",
      "d": "Lieferwerke auf Frontplatte, Blöcke à 12/24."
     },
     {
      "b": "Auf Spulmaschinen-Basis",
      "d": "Präzisionswickler mit Düsenbox (Fadis, Kaicheng)."
     }
    ]
   },
   {
    "t": "Anwendung",
    "o": [
     {
      "b": "Technik / Grobtiter",
      "d": "Autositze, Innenausstattung, bis 4 000 dtex."
     },
     {
      "b": "Glas & Sondermaterialien",
      "d": "Z. B. SSM DP5-T."
     }
    ]
   }
  ],
  "prof": {
   "plate": {
    "t": "Klassische Wellenmaschine",
    "ex": [
     "AIKI AT-501",
     "Himson HSS-ATX",
     "Aalidhra ADT-800"
    ],
    "d": "Lieferwerke, Heizstifte und Düsen sitzen an einer Frontplatte; Wellen treiben ganze Blöcke von 12 oder 24 Positionen an. Das Gatter steht vor oder neben der Maschine, die Spulen werden in einer oder zwei Etagen gewickelt.",
    "pro": [
     "Günstig pro Position",
     "Gleichmässig dank gemeinsamer Wellen"
    ],
    "con": [
     "Produktwechsel nur blockweise",
     "Stillstand einer Position kostet Effizienz"
    ]
   },
   "double": {
    "t": "Doppelseitig mit Frontal-Doffer",
    "ex": [
     "SSM Giudici TG2-AT / TG1-AT"
    ],
    "d": "Zwei Maschinenseiten mit je eigenen, geregelten Wellen; der Frontal-Doffer hält eine volle Spule und eine leere Hülse gleichzeitig in der Wiege, sodass ohne Unterbruch gewechselt wird.",
    "pro": [
     "Kompakt, viele Positionen",
     "Zwei Produkte gleichzeitig (je Seite)"
    ],
    "con": [
     "Feine bis mittlere Titer",
     "Weniger flexibel als Einzelposition"
    ]
   },
   "single": {
    "t": "Einzelpositions-Maschine",
    "ex": [
     "SSM DP5-T (5–40 Positionen)"
    ],
    "d": "Jede Position hat eigene, programmierbare Antriebe und kann ein eigenes Rezept fahren; das Rotationsgatter nimmt bis zu 6 Fäden plus Reserve auf. Ideal für viele kleine Lose und technische Garne.",
    "pro": [
     "Hunderte Rezepte, schneller Wechsel",
     "Bis 4 000 dtex, Glas möglich"
    ],
    "con": [
     "Höhere Investition pro Position",
     "Wenig Positionen"
    ]
   },
   "winder": {
    "t": "Präzisions-Spulmaschine mit Düsenbox",
    "ex": [
     "Fadis Sincro Aquajet",
     "Kaicheng KC215C"
    ],
    "d": "Basis ist ein Präzisionswickler mit elektronischer Fadenführung; davor sitzen Kern- und Effekt-Galette, eine Nassbox mit Texturierdüse und eine Master-Galette. Online-Spannungsmessung regelt die Aufwickelspannung.",
    "pro": [
     "Exakter Spulenaufbau",
     "Gut für FDY-Effektgarne"
    ],
    "con": [
     "Eher ohne POY-Verstreckung",
     "Kleinere Linien"
    ]
   }
  },
  "psv": {
   "creel": "Gatter",
   "plate": "Frontplatte (Block à 12/24 Pos.)",
   "decks": "2 Etagen",
   "frame": "Mittelgestell / Wellen",
   "doffer": "Frontal-Doffer: volle Spule + leere Hülse",
   "sideB": "Seite B",
   "creelA": "Gatter A",
   "creelB": "Gatter B",
   "pos": "Pos. {i} · Rezept {r}",
   "single": "Rotationsgatter, Einzelantriebe, Heizgalette",
   "platform": "Präzisionswickler-Plattform",
   "core": "Kern",
   "effect": "Effekt",
   "wetbox": "Nassbox + Düse",
   "master": "Master",
   "sensor": "Spannungssensor"
  },
  "mfr": [
   {
    "name": "SSM (inkl. Stähle-Eltex & Giudici)",
    "city": "Wädenswil",
    "owner": "Rieter-Konzern",
    "note": "Marktführer bei Lufttexturiermaschinen: Stähle-Eltex (Reutlingen) kam 1999 zu SSM, Giudici später. Heute vom Einzelpositions-Konzept bis zur doppelseitigen Wellenmaschine.",
    "models": [
     {
      "n": "DP5-T (DP5-TF / DP5-TC)",
      "spec": "Einzelpositions-Maschine, 5–40 Positionen einseitig; Positionen und Lieferwerke einzeln angetrieben; PES, PA, PP, Glas; POY und FDY/FOY; TC bis 4 000 dtex PES/PP; Rotationsgatter bis 6 Fäden + Reserve; DIGICONE- oder Präzisionswicklung; optional fancyflex für Slubs und Dick-Dünn-Effekte."
     },
     {
      "n": "TG2-AT",
      "spec": "Doppelseitige Maschine mit individuellem Frontal-Doffer (volle Spule und leere Hülse gleichzeitig in der Wiege); POY/FDY aus PES, PA, PP, feine bis mittlere Titer; Wellen je Seite einzeln geregelt."
     },
     {
      "n": "TG1-AT",
      "spec": "Manuelle Variante für kostengünstige Produktion feiner bis mittlerer Titer; Changierhub 190 oder 245 mm."
     },
     {
      "n": "TG30-ETC",
      "spec": "Kombimaschine: Falschdraht- und Lufttexturierung in einem Schritt; ATY Kern/Effekt mit oder ohne Elastan, DTY+ATY, Slubs, DTTY (texturiert und gezwirnt)."
     },
     {
      "n": "DP2-T / RM3-T (Stähle-Eltex, historisch)",
      "spec": "DP2-T für Garne bis 900 dtex, RM3-T für Hochleistung bis 3 200 dtex (Stand 2004)."
     }
    ]
   },
   {
    "name": "AIKI Riotech",
    "city": "Inazawa, Aichi",
    "owner": "privat",
    "note": "AT-501-Familie: Lieferwerke mit Nip- oder Heizgaletten, Heizstift für die Verstreckung von POY, zweiter Heizer zum Einstellen der Schlingen; Wellenantrieb, modular in 12er- bzw. 24er-Blöcken.",
    "models": [
     {
      "n": "AT-501A",
      "spec": "4 Lieferwerke + Heizstift; POY wird verstreckt; einfache T&T-Garne (Dick-Dünn) über den Heizstift; Schlingengrösse über zweiten Heizer; 30–600 den; Lieferwerke 100–1 000 m/min, Wicklung bis 800 m/min."
     },
     {
      "n": "AT-501B / AT-501C2F",
      "spec": "Bis 216 Spindeln in 24er-Blöcken; B mit reduzierter Streuung der Effektabstände, C2F mit 2 Lieferwerken; Spulen 200 mm (optional 250 mm)."
     },
     {
      "n": "AT-501 EXII",
      "spec": "5 Lieferwerke + Heizstift + erster Heizer: T&T-Garne und Mischgarne mit unterschiedlichem Schrumpf; optional Autodoff mit 250-mm-Spulen."
     },
     {
      "n": "AT-501 HD III / HD 900",
      "spec": "Mit 4 beheizten Galetten pro Position; für Industrie- und Fahrzeuggarne (Autositze, Innenausstattung); Wicklung bis 1 000 m/min."
     }
    ]
   },
   {
    "name": "TMT Machinery",
    "city": "Osaka / Kyoto",
    "owner": "JV Toray Eng., Murata, Teijin Seiki",
    "note": "Die REIKA-Serie ergänzt die DTY-Maschinen um Nylon-, Luft- und PIN-Texturierung.",
    "models": [
     {
      "n": "REIKA-Serie (Luft / PIN)",
      "spec": "Maschinen für Luft- und PIN-Texturierung; technische Details nicht öffentlich."
     }
    ]
   },
   {
    "name": "Fadis",
    "city": "Solbiate Arno (VA)",
    "owner": "privat, gegründet 1960",
    "note": "Spezialist für Präzisions-Spul- und Luftumwindemaschinen (Air Covering seit 1987); die Lufttexturiermaschine baut auf derselben „Open Platform“ auf.",
    "models": [
     {
      "n": "Sincro (Multipla) Aquajet",
      "spec": "Präzisions-Lufttexturiermaschine mit elektronischer Fadenführung: Kern-Galette, Effekt-Galette, Box-Düse mit Benetzungskopf und Heberlein-Düse, Master-Galette; Kern und Effekt laufen ohne Umlenkwinkel in die Nassbox; Online-Fadenspannungssensor vor der Aufwicklung."
     }
    ]
   },
   {
    "name": "Himson Engineering",
    "city": "Surat",
    "owner": "Himson Bhogibhai Group",
    "note": "Indischer Hersteller von DTY- und ATY-Maschinen; ATY-Baureihe HSS-ATX.",
    "models": [
     {
      "n": "HSS-ATX-3N / -9G / -15G",
      "spec": "24 bis 120 Spindeln, automatisch oder halbautomatisch; HMI-Touchscreen; Einzelmotorantriebe (ATX-9G) für niedrigen Energieverbrauch und reproduzierbare Qualität."
     }
    ]
   },
   {
    "name": "Aalidhra",
    "city": "Surat / Navsari",
    "owner": "gegründet 1975",
    "note": "Kostengünstige Air-Draw-Texturiermaschinen für den indischen Markt.",
    "models": [
     {
      "n": "ADT-800/4SH & /2SH",
      "spec": "Einseitige Bauweise, 2-Deck-Aufwicklung, 4 Sektionen/32 bis 13 Sektionen/104 Positionen; Verstreckung von POY integriert."
     },
     {
      "n": "ADT 900-950",
      "spec": "Neuere Lufttexturier-Baureihe; Daten nicht öffentlich."
     }
    ]
   },
   {
    "name": "Zhejiang Kaicheng Intelligent Machinery",
    "city": "Xinchang, Shaoxing",
    "owner": "privat, gegründet 2003",
    "note": "Spul-, Zwirn- und Luftumwindemaschinen; die ATY-Maschine basiert auf der eigenen Präzisionswickler-Plattform.",
    "models": [
     {
      "n": "KC215C",
      "spec": "Lufttexturiermaschine für POY, als „SSM-Typ“ vermarktet, auf Präzisionswickler-Basis."
     },
     {
      "n": "KC215B (Luftumwinden, verwandt)",
      "spec": "Air-Covering-Maschine für Elastan-Garne: einseitig, 40 Spindeln pro Satz, bis 1 100 m/min."
     }
    ]
   },
   {
    "name": "Weitere chinesische Anbieter",
    "city": "Suzhou, Shanxi u. a.",
    "owner": "diverse",
    "note": "U. a. ein Anbieter aus Suzhou (Modell HLK-B) und Shanxi Jingwei Chemical Fiber Machinery mit ATY-Maschinen für PA und PES.",
    "models": [
     {
      "n": "HLK-B (Anbieter aus Suzhou)",
      "spec": "8 Sektionen à 16 = 128 Spindeln, 70–2 000 dtex, bis 600 m/min, Spulen 5 kg, Luftdruck 0,6–0,9 MPa; FDY wird benetzt, texturiert und präpariert – für Webgarne."
     },
     {
      "n": "Shanxi Jingwei ATY-Maschine",
      "spec": "Lufttexturiermaschine für Polyamid und Polyester; Daten kaum öffentlich."
     }
    ]
   }
  ],
  "chips": {
   "auto": "Autodoff",
   "man": "manuell",
   "legacy": "historisch",
   "poy": "POY",
   "fdy": "FDY",
   "ce": "Kern/Effekt",
   "tech": "Technik",
   "combo": "Kombi"
  },
  "tl": [
   "Fadis führt als erster Hersteller das Luftumwinden (Air Covering) ein.",
   "Schärer, Schweiter und Mettler fusionieren zu SSM.",
   "Stähle-Eltex (Reutlingen) und SSM schliessen sich zusammen – Bündelung der Lufttexturier-Kompetenz.",
   "SSM Stähle-Eltex: DP2-T (bis 900 dtex) und RM3-T (bis 3 200 dtex).",
   "SSM Giudici stellt die manuelle TG1-AT vor.",
   "SSM zeigt DP5-T mit fancyflex (Slubs, Dick-Dünn) und TG2-AT mit Frontal-Doffer.",
   "Fadis präsentiert die Sincro Multipla Aquajet an der ITMA Barcelona.",
   "Turktex (TR) investiert in DP5-T für PES- und PP-ATY.",
   "Rieter übernimmt Barmag – SSM und Barmag gehören nun zum selben Konzern."
  ],
  "classif": [
   [
    "SSM ist Marktführer:",
    "Mit der Fusion mit Stähle-Eltex (1999) und Giudici deckt SSM heute vom Einzelpositions-Konzept (DP5-T) bis zur doppelseitigen Wellenmaschine (TG2-AT) alles ab. SSM gehört zum Rieter-Konzern – wie seit 2026 auch Barmag."
   ],
   [
    "Japan:",
    "AIKI Riotech mit der AT-501-Familie (bis 216 Positionen, Heizstift-Verstreckung), TMT mit der REIKA-Serie für Luft- und PIN-Texturierung."
   ],
   [
    "Italien:",
    "Fadis baut die Sincro Aquajet auf Basis seiner Präzisions-Spulmaschinen (mit Heberlein-Düse)."
   ],
   [
    "Indien & China:",
    "Himson, Aalidhra, Kaicheng (KC215C) und weitere Anbieter liefern günstige Maschinen für Heimtextil- und Technikgarne."
   ],
   [
    "Die Düse ist das Herzstück:",
    "Maschinenhersteller verbauen meist Texturierdüsen von Spezialisten; die HemaJet-Düsen von Heberlein sind auch in der Forschung die Referenz."
   ],
   [
    "Anwendungen:",
    "Heimtextilien, Autositze und Innenausstattung, Nähgarne, Technik- und Glasgarne, Effektgarne (Slubs, Dick-Dünn)."
   ]
  ]
 },
 "en": {
  "ui": {
   "eyebrow": "Knowledge Base · ATY",
   "h1": "ATY machines: manufacturers, designs & variants",
   "lead": "Interactive overview of air-jet texturing machines: a supersonic air stream in the texturing jet entangles overfed filaments into loops and gives the smooth filament a spun-yarn-like character. All illustrations are schematic visualisations, not to scale.",
   "note": "Research status: November 2026. Manufacturer data may differ depending on the machine version.",
   "sources": "Sources",
   "component": "Component",
   "tip": "Tip: the switches above change feed yarn, yarn construction, wetting and post-treatment.",
   "openAty": "→ ATY air texturing",
   "openAtyHint": "How the jet works in detail is shown in the ATY air texturing module.",
   "examples": "Examples",
   "pros": "Advantages",
   "cons": "Disadvantages",
   "search": "Search",
   "searchPh": "Model, manufacturer, feature …",
   "region": "Region",
   "operation": "Operation",
   "all": "All",
   "regions": [
    "Europe",
    "Japan",
    "China",
    "India"
   ],
   "autodoff": "Autodoff",
   "manual": "Manual",
   "treeFilter": "Filter from variant tree:",
   "reset": "reset",
   "empty": "No models for this filter combination.",
   "upTo": "up to {n} pos.",
   "source": "Source: {d}",
   "sortPos": "Positions (max.)",
   "sortSpeed": "Mech. speed (m/min)",
   "barsNote": "Maximum mechanical speed according to the manufacturer; the process speed depends strongly on yarn count, overfeed and jet and is typically far lower (in research trials e.g. 200–600 m/min).",
   "classif": "Market overview",
   "ariaProc": "Schematic yarn path of one ATY position",
   "ariaProf": "Machine design",
   "treeHint": "Click an option: the Manufacturers & models chapter opens with that filter."
  },
  "scenes": [
   {
    "k": "Process",
    "title": "The yarn path of one ATY position",
    "text": "The feed rolls deliver more yarn to the jet than is taken off behind it (overfeed). In the air stream the surplus filament lengths form loops that are anchored in the yarn core. The yarn is then stabilised mechanically and wound up. Click a component; the switches show the variants."
   },
   {
    "k": "Variant tree",
    "title": "Variant tree",
    "text": "Click an option to filter the matching manufacturers and models in the Manufacturers & models chapter."
   },
   {
    "k": "Designs",
    "title": "Machine designs",
    "text": "Air-jet texturing machines are much lower than DTY machines; the designs differ mainly in how many positions one drive serves and how doffing is solved."
   },
   {
    "k": "Manufacturers & models",
    "title": "Manufacturers & models",
    "text": "Key figures from manufacturer data, trade press and catalogues (see sources)."
   },
   {
    "k": "Comparison",
    "title": "Comparison",
    "text": "ATY machines are much smaller than DTY machines: a few dozen to just over 200 positions, but with a very wide count range reaching into technical yarns."
   },
   {
    "k": "Market",
    "title": "Market structure & development",
    "text": "Key events in the industry and an overview of the suppliers."
   }
  ],
  "ctl": [
   {
    "l": "Feed yarn",
    "o": [
     "POY (with drawing)",
     "FDY"
    ]
   },
   {
    "l": "Yarn construction",
    "o": [
     "Core / effect",
     "Parallel"
    ]
   },
   {
    "l": "Wetting",
    "o": [
     "wet",
     "dry"
    ]
   },
   {
    "l": "Post-treatment",
    "o": [
     "mechanical",
     "+ heater"
    ]
   }
  ],
  "comp": {
   "creel": {
    "t": "Creel",
    "tags": [
     "Core and effect ends"
    ],
    "p": "For core/effect yarns, several supply packages run in per position: core ends (low overfeed, forming the load-bearing core) and effect ends (high overfeed, forming the loops on the surface).",
    "l": [
     "SSM DP5-T: rotating creel for up to 6 ends plus reserve",
     "Glass, aramid and blended yarns also possible"
    ]
   },
   "feed": {
    "t": "Feed rolls & drawing",
    "tags": [
     "Overfeed"
    ],
    "poy": "POY feed: the yarn is drawn over a heater pin between two feed rolls before it enters the jet (e.g. AIKI AT-501: 4 feed rolls + heater pin). The heater pin also allows simple thick-and-thin effects.",
    "fdy": "FDY feed: the yarn is already drawn; one feed roll per yarn group only sets the overfeed.",
    "l": [
     "Overfeed = (v feed roll – v take-off) / v take-off",
     "Core typically ~5–30 %, effect up to 200 % and more",
     "Core and effect feed rolls controlled separately (Fadis: core and effect godet)"
    ]
   },
   "wet": {
    "t": "Wetting",
    "tags": [
     "Water"
    ],
    "wet": "Before the jet, the core end is led through a water bath, a wetting head or a drip nozzle. Water reduces the friction between the filaments and improves loop formation and stability – standard practice in production.",
    "dry": "With dry texturing the loops formed are less stable; dry processing is used rather for simple entangling tasks or special materials.",
    "l": [
     "Effect ends usually bypass the wetting dry"
    ]
   },
   "jet": {
    "t": "Texturing jet",
    "tags": [
     "Core component",
     "Supersonic"
    ],
    "p": "Compressed air (typ. 6–9 bar) expands in the jet to supersonic speed; the filaments are spread apart, the overfed lengths form loops and are anchored in the yarn core. At the outlet there is often a baffle that calms the flow.",
    "l": [
     "Jet geometry determines yarn character and air consumption",
     "Typical industry standard and research reference: Heberlein HemaJet (fitted e.g. in the Fadis Aquajet)",
     "Combination machines also use air-covering jets for elastane"
    ]
   },
   "stab": {
    "t": "Stabilising zone",
    "tags": [
     "mechanical"
    ],
    "p": "Between two feed rolls the textured yarn is slightly redrawn (about 1–15 %). Loose, unstable loops are pulled out; the tension in this zone indicates how well the jet is working.",
    "l": []
   },
   "heat": {
    "t": "Heater (thermal post-treatment)",
    "tags": [
     "optional"
    ],
    "p": "A heater tube or a heated godet after the jet heat-sets the yarn, reduces residual shrinkage or adjusts the loop size (AIKI: “ATY loop can be adjusted with the second heater”). SSM uses heated godets.",
    "l": [
     "Important for yarns that are dyed or heat-set later"
    ]
   },
   "wind": {
    "t": "Take-up",
    "tags": [
     "Package"
    ],
    "p": "Cross-wound packages with random, precision or step-precision winding (SSM DIGICONE). ATY machines run at much lower process speeds than DTY and with coarse counts.",
    "l": [
     "Manual, with front doffer (TG2-AT) or autodoff",
     "Optional fancy devices for slubs and thick-and-thin"
    ]
   },
   "eff": {
    "t": "Effect end",
    "tags": [
     "high overfeed"
    ],
    "p": "The effect end is heavily overfed and forms the visible loops; with POY it is also drawn over a heater pin. Different colours, counts or materials in core and effect produce mélange and structured yarns.",
    "l": []
   }
  },
  "sv": {
   "core": "Core",
   "effect": "Effect",
   "creel": "Creel",
   "heatPin": "Heater pin",
   "feedCore": "Core feed roll",
   "wetting": "Wetting",
   "dry": "dry",
   "coreOf": "Core: low overfeed",
   "allOf": "all ends: same overfeed",
   "effOf": "Effect: high overfeed (up to 200 %+)",
   "air": "Compressed air 6–9 bar",
   "jet": "Texturing jet",
   "baffle": "+ baffle",
   "stab": "Stabilisation",
   "stabOf": "1–15 % redraw",
   "heater": "Heater",
   "wind": "Take-up",
   "speed": "Process typ. 200–600 m/min"
  },
  "dims": [
   {
    "t": "Feed yarn",
    "o": [
     {
      "b": "POY (with drawing)",
      "d": "Heater pin or heated godet before the jet."
     },
     {
      "b": "FDY / FOY",
      "d": "Already drawn, overfeed only."
     }
    ]
   },
   {
    "t": "Yarn construction",
    "o": [
     {
      "b": "Core / effect",
      "d": "Different overfeeds, structured and mélange yarns."
     },
     {
      "b": "Fancy yarns",
      "d": "Slubs, thick-and-thin (T&T)."
     },
     {
      "b": "Combined with DTY / elastane",
      "d": "False twist + air, or air covering."
     }
    ]
   },
   {
    "t": "Process",
    "o": [
     {
      "b": "Emphasis on wet treatment",
      "d": "Wetting head / water box."
     },
     {
      "b": "Thermal post-treatment",
      "d": "Heater or heated godet after the jet."
     }
    ]
   },
   {
    "t": "Design",
    "o": [
     {
      "b": "Single position",
      "d": "Each position has its own drives (DP5-T)."
     },
     {
      "b": "Double-sided, shafts",
      "d": "Many positions, front doffer (TG2-AT)."
     },
     {
      "b": "Classic shaft-driven machine",
      "d": "Feed rolls on a front plate, blocks of 12/24."
     },
     {
      "b": "Based on a winding machine",
      "d": "Precision winder with jet box (Fadis, Kaicheng)."
     }
    ]
   },
   {
    "t": "Application",
    "o": [
     {
      "b": "Technical / coarse counts",
      "d": "Car seats, interiors, up to 4 000 dtex."
     },
     {
      "b": "Glass & special materials",
      "d": "E.g. SSM DP5-T."
     }
    ]
   }
  ],
  "prof": {
   "plate": {
    "t": "Classic shaft-driven machine",
    "ex": [
     "AIKI AT-501",
     "Himson HSS-ATX",
     "Aalidhra ADT-800"
    ],
    "d": "Feed rolls, heater pins and jets sit on a front plate; shafts drive whole blocks of 12 or 24 positions. The creel stands in front of or beside the machine, and the packages are wound on one or two levels.",
    "pro": [
     "Low cost per position",
     "Uniform thanks to common shafts"
    ],
    "con": [
     "Product changes only block by block",
     "A stopped position costs efficiency"
    ]
   },
   "double": {
    "t": "Double-sided with front doffer",
    "ex": [
     "SSM Giudici TG2-AT / TG1-AT"
    ],
    "d": "Two machine sides, each with its own controlled shafts; the front doffer holds a full package and an empty tube in the cradle at the same time, so the change happens without interruption.",
    "pro": [
     "Compact, many positions",
     "Two products at once (one per side)"
    ],
    "con": [
     "Fine to medium counts",
     "Less flexible than single position"
    ]
   },
   "single": {
    "t": "Single-position machine",
    "ex": [
     "SSM DP5-T (5–40 positions)"
    ],
    "d": "Each position has its own programmable drives and can run its own recipe; the rotating creel takes up to 6 ends plus reserve. Ideal for many small lots and technical yarns.",
    "pro": [
     "Hundreds of recipes, fast changeover",
     "Up to 4 000 dtex, glass possible"
    ],
    "con": [
     "Higher investment per position",
     "Few positions"
    ]
   },
   "winder": {
    "t": "Precision winder with jet box",
    "ex": [
     "Fadis Sincro Aquajet",
     "Kaicheng KC215C"
    ],
    "d": "The base is a precision winder with electronic yarn guiding; upstream sit a core godet and an effect godet, a water box with texturing jet and a master godet. Online tension measurement controls the winding tension.",
    "pro": [
     "Exact package build",
     "Good for FDY fancy yarns"
    ],
    "con": [
     "Usually without POY drawing",
     "Smaller lines"
    ]
   }
  },
  "psv": {
   "creel": "Creel",
   "plate": "Front plate (block of 12/24 pos.)",
   "decks": "2 levels",
   "frame": "Centre frame / shafts",
   "doffer": "Front doffer: full package + empty tube",
   "sideB": "Side B",
   "creelA": "Creel A",
   "creelB": "Creel B",
   "pos": "Pos. {i} · recipe {r}",
   "single": "Rotating creel, individual drives, heated godet",
   "platform": "Precision winder platform",
   "core": "Core",
   "effect": "Effect",
   "wetbox": "Water box + jet",
   "master": "Master",
   "sensor": "Tension sensor"
  },
  "mfr": [
   {
    "name": "SSM (incl. Stähle-Eltex & Giudici)",
    "city": "Wädenswil",
    "owner": "Rieter Group",
    "note": "Market leader in air-jet texturing machines: Stähle-Eltex (Reutlingen) joined SSM in 1999, Giudici later. Today the range spans from the single-position concept to the double-sided shaft-driven machine.",
    "models": [
     {
      "n": "DP5-T (DP5-TF / DP5-TC)",
      "spec": "Single-position machine, 5–40 positions on one side; positions and feed rolls driven individually; PES, PA, PP, glass; POY and FDY/FOY; TC up to 4 000 dtex PES/PP; rotating creel for up to 6 ends + reserve; DIGICONE or precision winding; optional fancyflex for slubs and thick-and-thin effects."
     },
     {
      "n": "TG2-AT",
      "spec": "Double-sided machine with individual front doffer (full package and empty tube in the cradle at the same time); POY/FDY of PES, PA, PP, fine to medium counts; shafts controlled separately on each side."
     },
     {
      "n": "TG1-AT",
      "spec": "Manual version for low-cost production of fine to medium counts; traverse stroke 190 or 245 mm."
     },
     {
      "n": "TG30-ETC",
      "spec": "Combination machine: false-twist and air-jet texturing in one step; ATY core/effect with or without elastane, DTY+ATY, slubs, DTTY (textured and twisted)."
     },
     {
      "n": "DP2-T / RM3-T (Stähle-Eltex, historic)",
      "spec": "DP2-T for yarns up to 900 dtex, RM3-T for high performance up to 3 200 dtex (as of 2004)."
     }
    ]
   },
   {
    "name": "AIKI Riotech",
    "city": "Inazawa, Aichi",
    "owner": "private",
    "note": "AT-501 family: feed rolls with nip or heated godets, heater pin for drawing POY, second heater for adjusting the loops; shaft drive, modular in blocks of 12 or 24.",
    "models": [
     {
      "n": "AT-501A",
      "spec": "4 feed rolls + heater pin; POY is drawn; simple T&T yarns (thick-and-thin) via the heater pin; loop size via the second heater; 30–600 den; feed rolls 100–1 000 m/min, winding up to 800 m/min."
     },
     {
      "n": "AT-501B / AT-501C2F",
      "spec": "Up to 216 spindles in blocks of 24; B with reduced scatter of the effect spacing, C2F with 2 feed rolls; packages 200 mm (optionally 250 mm)."
     },
     {
      "n": "AT-501 EXII",
      "spec": "5 feed rolls + heater pin + first heater: T&T yarns and blended yarns with different shrinkage; optional autodoff with 250 mm packages."
     },
     {
      "n": "AT-501 HD III / HD 900",
      "spec": "With 4 heated godets per position; for industrial and automotive yarns (car seats, interiors); winding up to 1 000 m/min."
     }
    ]
   },
   {
    "name": "TMT Machinery",
    "city": "Osaka / Kyoto",
    "owner": "JV Toray Eng., Murata, Teijin Seiki",
    "note": "The REIKA series adds nylon, air and PIN texturing to the DTY machines.",
    "models": [
     {
      "n": "REIKA series (air / PIN)",
      "spec": "Machines for air and PIN texturing; technical details not public."
     }
    ]
   },
   {
    "name": "Fadis",
    "city": "Solbiate Arno (VA)",
    "owner": "private, founded 1960",
    "note": "Specialist in precision winding and air-covering machines (air covering since 1987); the air-jet texturing machine is built on the same “Open Platform”.",
    "models": [
     {
      "n": "Sincro (Multipla) Aquajet",
      "spec": "Precision air-jet texturing machine with electronic yarn guiding: core godet, effect godet, box jet with wetting head and Heberlein jet, master godet; core and effect run into the water box without deflection angle; online yarn tension sensor before take-up."
     }
    ]
   },
   {
    "name": "Himson Engineering",
    "city": "Surat",
    "owner": "Himson Bhogibhai Group",
    "note": "Indian manufacturer of DTY and ATY machines; ATY series HSS-ATX.",
    "models": [
     {
      "n": "HSS-ATX-3N / -9G / -15G",
      "spec": "24 to 120 spindles, automatic or semi-automatic; HMI touchscreen; individual motor drives (ATX-9G) for low energy consumption and reproducible quality."
     }
    ]
   },
   {
    "name": "Aalidhra",
    "city": "Surat / Navsari",
    "owner": "founded 1975",
    "note": "Low-cost air-draw texturing machines for the Indian market.",
    "models": [
     {
      "n": "ADT-800/4SH & /2SH",
      "spec": "Single-sided design, 2-deck take-up, 4 sections/32 to 13 sections/104 positions; POY drawing integrated."
     },
     {
      "n": "ADT 900-950",
      "spec": "Newer air-jet texturing series; data not public."
     }
    ]
   },
   {
    "name": "Zhejiang Kaicheng Intelligent Machinery",
    "city": "Xinchang, Shaoxing",
    "owner": "private, founded 2003",
    "note": "Winding, twisting and air-covering machines; the ATY machine is based on the company's own precision winder platform.",
    "models": [
     {
      "n": "KC215C",
      "spec": "Air-jet texturing machine for POY, marketed as “SSM type”, based on a precision winder."
     },
     {
      "n": "KC215B (air covering, related)",
      "spec": "Air-covering machine for elastane yarns: single-sided, 40 spindles per set, up to 1 100 m/min."
     }
    ]
   },
   {
    "name": "Other Chinese suppliers",
    "city": "Suzhou, Shanxi and others",
    "owner": "various",
    "note": "Including a supplier from Suzhou (model HLK-B) and Shanxi Jingwei Chemical Fiber Machinery with ATY machines for PA and PES.",
    "models": [
     {
      "n": "HLK-B (supplier from Suzhou)",
      "spec": "8 sections of 16 = 128 spindles, 70–2 000 dtex, up to 600 m/min, 5 kg packages, air pressure 0.6–0.9 MPa; FDY is wetted, textured and finished – for weaving yarns."
     },
     {
      "n": "Shanxi Jingwei ATY machine",
      "spec": "Air-jet texturing machine for polyamide and polyester; hardly any public data."
     }
    ]
   }
  ],
  "chips": {
   "auto": "Autodoff",
   "man": "manual",
   "legacy": "historic",
   "poy": "POY",
   "fdy": "FDY",
   "ce": "Core/effect",
   "tech": "Technical",
   "combo": "Combi"
  },
  "tl": [
   "Fadis is the first manufacturer to introduce air covering.",
   "Schärer, Schweiter and Mettler merge to form SSM.",
   "Stähle-Eltex (Reutlingen) and SSM join forces – pooling their air-jet texturing expertise.",
   "SSM Stähle-Eltex: DP2-T (up to 900 dtex) and RM3-T (up to 3 200 dtex).",
   "SSM Giudici presents the manual TG1-AT.",
   "SSM shows the DP5-T with fancyflex (slubs, thick-and-thin) and the TG2-AT with front doffer.",
   "Fadis presents the Sincro Multipla Aquajet at ITMA Barcelona.",
   "Turktex (TR) invests in DP5-T for PES and PP ATY.",
   "Rieter takes over Barmag – SSM and Barmag now belong to the same group."
  ],
  "classif": [
   [
    "SSM is the market leader:",
    "With the merger with Stähle-Eltex (1999) and Giudici, SSM today covers everything from the single-position concept (DP5-T) to the double-sided shaft-driven machine (TG2-AT). SSM belongs to the Rieter Group – as does Barmag since 2026."
   ],
   [
    "Japan:",
    "AIKI Riotech with the AT-501 family (up to 216 positions, heater-pin drawing), TMT with the REIKA series for air and PIN texturing."
   ],
   [
    "Italy:",
    "Fadis builds the Sincro Aquajet based on its precision winding machines (with Heberlein jet)."
   ],
   [
    "India & China:",
    "Himson, Aalidhra, Kaicheng (KC215C) and other suppliers deliver low-cost machines for home-textile and technical yarns."
   ],
   [
    "The jet is the core component:",
    "Machine builders usually fit texturing jets from specialists; Heberlein's HemaJet jets are also the reference in research."
   ],
   [
    "Applications:",
    "Home textiles, car seats and interiors, sewing threads, technical and glass yarns, fancy yarns (slubs, thick-and-thin)."
   ]
  ]
 },
 "es": {
  "ui": {
   "eyebrow": "Knowledge Base · ATY",
   "h1": "Máquinas ATY: fabricantes, diseños y variantes",
   "lead": "Vista general interactiva de las máquinas de texturizado por aire (Air Jet Texturing): un chorro de aire supersónico en la tobera de texturizado enreda los filamentos sobrealimentados formando bucles y da al filamento liso un carácter parecido al hilo de fibra. Todas las ilustraciones son esquemáticas y no están a escala.",
   "note": "Estado de la investigación: noviembre de 2026. Los datos de los fabricantes pueden variar según la versión de la máquina.",
   "sources": "Fuentes",
   "component": "Componente",
   "tip": "Consejo: los selectores de arriba cambian el hilo de alimentación, la estructura del hilo, la humectación y el tratamiento posterior.",
   "openAty": "→ Texturizado ATY por aire",
   "openAtyHint": "Cómo funciona la tobera en detalle se explica en el módulo de texturizado ATY por aire.",
   "examples": "Ejemplos",
   "pros": "Ventajas",
   "cons": "Desventajas",
   "search": "Buscar",
   "searchPh": "Modelo, fabricante, característica …",
   "region": "Región",
   "operation": "Manejo",
   "all": "Todos",
   "regions": [
    "Europa",
    "Japón",
    "China",
    "India"
   ],
   "autodoff": "Autodoff",
   "manual": "Manual",
   "treeFilter": "Filtro del esquema de variantes:",
   "reset": "restablecer",
   "empty": "No hay modelos para esta combinación de filtros.",
   "upTo": "hasta {n} pos.",
   "source": "Fuente: {d}",
   "sortPos": "Posiciones (máx.)",
   "sortSpeed": "Velocidad mecánica (m/min)",
   "barsNote": "Velocidad mecánica máxima según el fabricante; la velocidad de proceso depende mucho del título, la sobrealimentación y la tobera, y suele ser bastante menor (en ensayos de investigación, p. ej., 200–600 m/min).",
   "classif": "Panorama",
   "ariaProc": "Recorrido esquemático del hilo en una posición ATY",
   "ariaProf": "Diseño de máquina",
   "treeHint": "Haz clic en una opción: se abre el capítulo Fabricantes y modelos con ese filtro."
  },
  "scenes": [
   {
    "k": "Proceso",
    "title": "El recorrido del hilo en una posición ATY",
    "text": "Los rodillos de alimentación entregan a la tobera más hilo del que se retira detrás (sobrealimentación). En el chorro de aire, las longitudes sobrantes de filamento forman bucles que quedan anclados en el núcleo del hilo. Después, el hilo se estabiliza mecánicamente y se bobina. Haz clic en un componente; los selectores muestran las variantes."
   },
   {
    "k": "Esquema de variantes",
    "title": "Esquema de variantes",
    "text": "Haz clic en una opción para filtrar los fabricantes y modelos correspondientes en el capítulo Fabricantes y modelos."
   },
   {
    "k": "Diseños",
    "title": "Diseños de máquina",
    "text": "Las máquinas de texturizado por aire son bastante más bajas que las máquinas DTY; los diseños se diferencian sobre todo en cuántas posiciones alimenta un accionamiento y en cómo se resuelve la mudada."
   },
   {
    "k": "Fabricantes y modelos",
    "title": "Fabricantes y modelos",
    "text": "Cifras clave de datos de fabricantes, prensa especializada y catálogos (ver fuentes)."
   },
   {
    "k": "Comparación",
    "title": "Comparación",
    "text": "Las máquinas ATY son mucho más pequeñas que las DTY: desde unas pocas decenas hasta algo más de 200 posiciones, pero con un rango de títulos muy amplio que llega hasta los hilos técnicos."
   },
   {
    "k": "Mercado",
    "title": "Estructura del mercado y evolución",
    "text": "Acontecimientos importantes del sector y un panorama de los proveedores."
   }
  ],
  "ctl": [
   {
    "l": "Alimentación",
    "o": [
     "POY (con estirado)",
     "FDY"
    ]
   },
   {
    "l": "Estructura del hilo",
    "o": [
     "Núcleo / efecto",
     "Paralelo"
    ]
   },
   {
    "l": "Humectación",
    "o": [
     "húmedo",
     "seco"
    ]
   },
   {
    "l": "Tratamiento posterior",
    "o": [
     "mecánico",
     "+ calentador"
    ]
   }
  ],
  "comp": {
   "creel": {
    "t": "Fileta",
    "tags": [
     "Cabos de núcleo y de efecto"
    ],
    "p": "En los hilos núcleo/efecto entran varias bobinas de alimentación por posición: cabos de núcleo (baja sobrealimentación, forman el alma portante) y cabos de efecto (alta sobrealimentación, forman los bucles en la superficie).",
    "l": [
     "SSM DP5-T: fileta giratoria para hasta 6 cabos más reserva",
     "También son posibles hilos de vidrio, aramida y mezclas"
    ]
   },
   "feed": {
    "t": "Rodillos de alimentación y estirado",
    "tags": [
     "Sobrealimentación"
    ],
    "poy": "Alimentación POY: entre dos rodillos de alimentación el hilo se estira sobre un pin calefactor antes de entrar en la tobera (p. ej., AIKI AT-501: 4 rodillos de alimentación + pin calefactor). El pin calefactor también permite efectos sencillos de grueso-fino.",
    "fdy": "Alimentación FDY: el hilo ya está estirado; un rodillo de alimentación por grupo de cabos solo ajusta la sobrealimentación.",
    "l": [
     "Sobrealimentación = (v rodillo de alimentación – v retirada) / v retirada",
     "Núcleo típicamente ~5–30 %, efecto hasta 200 % y más",
     "Rodillos de núcleo y de efecto regulables por separado (Fadis: godet de núcleo y godet de efecto)"
    ]
   },
   "wet": {
    "t": "Humectación",
    "tags": [
     "Agua"
    ],
    "wet": "Antes de la tobera, el cabo de núcleo pasa por un baño de agua, un cabezal humectador o una boquilla de goteo. El agua reduce la fricción entre los filamentos y mejora la formación de bucles y la estabilidad: en la práctica es lo estándar.",
    "dry": "En el texturizado en seco se forman bucles menos estables; en seco se trabaja más bien en tareas sencillas de entrelazado o con materiales especiales.",
    "l": [
     "Los cabos de efecto suelen pasar en seco junto a la humectación"
    ]
   },
   "jet": {
    "t": "Tobera de texturizado",
    "tags": [
     "Pieza clave",
     "Supersónico"
    ],
    "p": "El aire comprimido (típ. 6–9 bar) se expande en la tobera hasta velocidad supersónica; los filamentos se abren, las longitudes sobrealimentadas forman bucles y quedan ancladas en el núcleo del hilo. A la salida suele haber un deflector (baffle) que calma el flujo.",
    "l": [
     "La geometría de la tobera determina el carácter del hilo y el consumo de aire",
     "Estándar industrial típico y referencia en investigación: Heberlein HemaJet (montada, entre otras, en la Fadis Aquajet)",
     "En máquinas combinadas también toberas de recubrimiento por aire para elastano"
    ]
   },
   "stab": {
    "t": "Zona de estabilización",
    "tags": [
     "mecánica"
    ],
    "p": "Entre dos rodillos de alimentación, el hilo texturizado se reestira ligeramente (aprox. 1–15 %). Los bucles sueltos e inestables se eliminan; la tensión en esta zona indica lo bien que trabaja la tobera.",
    "l": []
   },
   "heat": {
    "t": "Calentador (tratamiento térmico posterior)",
    "tags": [
     "opcional"
    ],
    "p": "Un tubo calefactor o un godet calentado después de la tobera termofija el hilo, reduce el encogimiento residual o ajusta el tamaño de los bucles (AIKI: «ATY loop can be adjusted with the second heater»). SSM utiliza godets calentados.",
    "l": [
     "Importante para hilos que después se tiñen o se termofijan"
    ]
   },
   "wind": {
    "t": "Bobinado",
    "tags": [
     "Bobina"
    ],
    "p": "Bobinas cruzadas con bobinado aleatorio, de precisión o de precisión escalonada (SSM DIGICONE). Las máquinas ATY trabajan a velocidades de proceso mucho menores que las DTY y con títulos gruesos.",
    "l": [
     "Manual, con mudador frontal (TG2-AT) o autodoff",
     "Dispositivos de fantasía opcionales para slubs y grueso-fino"
    ]
   },
   "eff": {
    "t": "Cabo de efecto",
    "tags": [
     "alta sobrealimentación"
    ],
    "p": "El cabo de efecto se sobrealimenta mucho y forma los bucles visibles; con POY también se estira sobre un pin calefactor. Distintos colores, títulos o materiales en núcleo y efecto dan hilos melange y de estructura.",
    "l": []
   }
  },
  "sv": {
   "core": "Núcleo",
   "effect": "Efecto",
   "creel": "Fileta",
   "heatPin": "Pin calefactor",
   "feedCore": "Rodillo núcleo",
   "wetting": "Humectación",
   "dry": "seco",
   "coreOf": "Núcleo: baja sobrealimentación",
   "allOf": "todos los cabos: misma sobrealim.",
   "effOf": "Efecto: alta sobrealim. (hasta 200 %+)",
   "air": "Aire comprimido 6–9 bar",
   "jet": "Tobera de texturizado",
   "baffle": "+ deflector",
   "stab": "Estabilización",
   "stabOf": "1–15 % de reestirado",
   "heater": "Calentador",
   "wind": "Bobinado",
   "speed": "Proceso típ. 200–600 m/min"
  },
  "dims": [
   {
    "t": "Hilo de alimentación",
    "o": [
     {
      "b": "POY (con estirado)",
      "d": "Pin calefactor o godet calentado antes de la tobera."
     },
     {
      "b": "FDY / FOY",
      "d": "Ya estirado, solo sobrealimentación."
     }
    ]
   },
   {
    "t": "Estructura del hilo",
    "o": [
     {
      "b": "Núcleo / efecto",
      "d": "Distinta sobrealimentación, hilos de estructura y melange."
     },
     {
      "b": "Hilos de fantasía",
      "d": "Slubs, grueso-fino (T&T)."
     },
     {
      "b": "Combinado con DTY / elastano",
      "d": "Falsa torsión + aire o recubrimiento por aire."
     }
    ]
   },
   {
    "t": "Proceso",
    "o": [
     {
      "b": "Tratamiento en húmedo destacado",
      "d": "Cabezal humectador / caja de agua."
     },
     {
      "b": "Tratamiento térmico posterior",
      "d": "Calentador o godet calentado después de la tobera."
     }
    ]
   },
   {
    "t": "Diseño",
    "o": [
     {
      "b": "Posición individual",
      "d": "Cada posición con accionamientos propios (DP5-T)."
     },
     {
      "b": "Doble cara, ejes",
      "d": "Muchas posiciones, mudador frontal (TG2-AT)."
     },
     {
      "b": "Máquina clásica de ejes",
      "d": "Rodillos en placa frontal, bloques de 12/24."
     },
     {
      "b": "Basada en bobinadora",
      "d": "Bobinadora de precisión con caja de tobera (Fadis, Kaicheng)."
     }
    ]
   },
   {
    "t": "Aplicación",
    "o": [
     {
      "b": "Técnico / títulos gruesos",
      "d": "Asientos de coche, interiores, hasta 4 000 dtex."
     },
     {
      "b": "Vidrio y materiales especiales",
      "d": "P. ej., SSM DP5-T."
     }
    ]
   }
  ],
  "prof": {
   "plate": {
    "t": "Máquina clásica de ejes",
    "ex": [
     "AIKI AT-501",
     "Himson HSS-ATX",
     "Aalidhra ADT-800"
    ],
    "d": "Rodillos de alimentación, pines calefactores y toberas están en una placa frontal; los ejes accionan bloques enteros de 12 o 24 posiciones. La fileta está delante o al lado de la máquina y las bobinas se forman en uno o dos niveles.",
    "pro": [
     "Económica por posición",
     "Uniforme gracias a ejes comunes"
    ],
    "con": [
     "Cambio de producto solo por bloques",
     "Una posición parada cuesta eficiencia"
    ]
   },
   "double": {
    "t": "Doble cara con mudador frontal",
    "ex": [
     "SSM Giudici TG2-AT / TG1-AT"
    ],
    "d": "Dos lados de máquina, cada uno con sus propios ejes regulados; el mudador frontal sostiene a la vez una bobina llena y un tubo vacío en la cuna, de modo que el cambio se hace sin interrupción.",
    "pro": [
     "Compacta, muchas posiciones",
     "Dos productos a la vez (uno por lado)"
    ],
    "con": [
     "Títulos finos a medios",
     "Menos flexible que la posición individual"
    ]
   },
   "single": {
    "t": "Máquina de posición individual",
    "ex": [
     "SSM DP5-T (5–40 posiciones)"
    ],
    "d": "Cada posición tiene accionamientos propios programables y puede trabajar con su propia receta; la fileta giratoria admite hasta 6 cabos más reserva. Ideal para muchos lotes pequeños e hilos técnicos.",
    "pro": [
     "Cientos de recetas, cambio rápido",
     "Hasta 4 000 dtex, vidrio posible"
    ],
    "con": [
     "Mayor inversión por posición",
     "Pocas posiciones"
    ]
   },
   "winder": {
    "t": "Bobinadora de precisión con caja de tobera",
    "ex": [
     "Fadis Sincro Aquajet",
     "Kaicheng KC215C"
    ],
    "d": "La base es una bobinadora de precisión con guiado electrónico del hilo; delante se sitúan el godet de núcleo y el de efecto, una caja de agua con tobera de texturizado y un godet maestro. La medición de tensión en línea regula la tensión de bobinado.",
    "pro": [
     "Formación exacta de la bobina",
     "Buena para hilos de fantasía FDY"
    ],
    "con": [
     "Por lo general sin estirado de POY",
     "Líneas más pequeñas"
    ]
   }
  },
  "psv": {
   "creel": "Fileta",
   "plate": "Placa frontal (bloque de 12/24 pos.)",
   "decks": "2 niveles",
   "frame": "Bastidor central / ejes",
   "doffer": "Mudador frontal: bobina llena + tubo vacío",
   "sideB": "Lado B",
   "creelA": "Fileta A",
   "creelB": "Fileta B",
   "pos": "Pos. {i} · receta {r}",
   "single": "Fileta giratoria, accionamientos individuales, godet calentado",
   "platform": "Plataforma de bobinadora de precisión",
   "core": "Núcleo",
   "effect": "Efecto",
   "wetbox": "Caja de agua + tobera",
   "master": "Maestro",
   "sensor": "Sensor de tensión"
  },
  "mfr": [
   {
    "name": "SSM (incl. Stähle-Eltex y Giudici)",
    "city": "Wädenswil",
    "owner": "Grupo Rieter",
    "note": "Líder del mercado en máquinas de texturizado por aire: Stähle-Eltex (Reutlingen) se unió a SSM en 1999 y Giudici después. Hoy la gama va desde el concepto de posición individual hasta la máquina de ejes de doble cara.",
    "models": [
     {
      "n": "DP5-T (DP5-TF / DP5-TC)",
      "spec": "Máquina de posición individual, 5–40 posiciones a un lado; posiciones y rodillos de alimentación con accionamiento individual; PES, PA, PP, vidrio; POY y FDY/FOY; TC hasta 4 000 dtex PES/PP; fileta giratoria para hasta 6 cabos + reserva; bobinado DIGICONE o de precisión; opcional fancyflex para slubs y efectos grueso-fino."
     },
     {
      "n": "TG2-AT",
      "spec": "Máquina de doble cara con mudador frontal individual (bobina llena y tubo vacío a la vez en la cuna); POY/FDY de PES, PA, PP, títulos finos a medios; ejes regulados por separado en cada lado."
     },
     {
      "n": "TG1-AT",
      "spec": "Versión manual para producción económica de títulos finos a medios; carrera de traslación de 190 o 245 mm."
     },
     {
      "n": "TG30-ETC",
      "spec": "Máquina combinada: texturizado por falsa torsión y por aire en un solo paso; ATY núcleo/efecto con o sin elastano, DTY+ATY, slubs, DTTY (texturizado y retorcido)."
     },
     {
      "n": "DP2-T / RM3-T (Stähle-Eltex, histórico)",
      "spec": "DP2-T para hilos de hasta 900 dtex, RM3-T para alto rendimiento hasta 3 200 dtex (estado 2004)."
     }
    ]
   },
   {
    "name": "AIKI Riotech",
    "city": "Inazawa, Aichi",
    "owner": "privada",
    "note": "Familia AT-501: rodillos de alimentación con godets de pinza o calentados, pin calefactor para estirar el POY, segundo calentador para ajustar los bucles; accionamiento por ejes, modular en bloques de 12 o 24.",
    "models": [
     {
      "n": "AT-501A",
      "spec": "4 rodillos de alimentación + pin calefactor; el POY se estira; hilos T&T sencillos (grueso-fino) mediante el pin calefactor; tamaño de bucle mediante el segundo calentador; 30–600 den; rodillos 100–1 000 m/min, bobinado hasta 800 m/min."
     },
     {
      "n": "AT-501B / AT-501C2F",
      "spec": "Hasta 216 husos en bloques de 24; B con menor dispersión de las distancias entre efectos, C2F con 2 rodillos de alimentación; bobinas de 200 mm (opcional 250 mm)."
     },
     {
      "n": "AT-501 EXII",
      "spec": "5 rodillos de alimentación + pin calefactor + primer calentador: hilos T&T e hilos mixtos con distinto encogimiento; autodoff opcional con bobinas de 250 mm."
     },
     {
      "n": "AT-501 HD III / HD 900",
      "spec": "Con 4 godets calentados por posición; para hilos industriales y de automoción (asientos de coche, interiores); bobinado hasta 1 000 m/min."
     }
    ]
   },
   {
    "name": "TMT Machinery",
    "city": "Osaka / Kioto",
    "owner": "JV Toray Eng., Murata, Teijin Seiki",
    "note": "La serie REIKA completa las máquinas DTY con texturizado de nailon, por aire y PIN.",
    "models": [
     {
      "n": "Serie REIKA (aire / PIN)",
      "spec": "Máquinas para texturizado por aire y PIN; detalles técnicos no públicos."
     }
    ]
   },
   {
    "name": "Fadis",
    "city": "Solbiate Arno (VA)",
    "owner": "privada, fundada en 1960",
    "note": "Especialista en bobinadoras de precisión y máquinas de recubrimiento por aire (air covering desde 1987); la máquina de texturizado por aire se basa en la misma «Open Platform».",
    "models": [
     {
      "n": "Sincro (Multipla) Aquajet",
      "spec": "Máquina de texturizado por aire de precisión con guiado electrónico del hilo: godet de núcleo, godet de efecto, tobera de caja con cabezal humectador y tobera Heberlein, godet maestro; núcleo y efecto entran en la caja de agua sin ángulo de desvío; sensor de tensión del hilo en línea antes del bobinado."
     }
    ]
   },
   {
    "name": "Himson Engineering",
    "city": "Surat",
    "owner": "Himson Bhogibhai Group",
    "note": "Fabricante indio de máquinas DTY y ATY; serie ATY HSS-ATX.",
    "models": [
     {
      "n": "HSS-ATX-3N / -9G / -15G",
      "spec": "De 24 a 120 husos, automática o semiautomática; pantalla táctil HMI; accionamientos por motor individual (ATX-9G) para bajo consumo de energía y calidad reproducible."
     }
    ]
   },
   {
    "name": "Aalidhra",
    "city": "Surat / Navsari",
    "owner": "fundada en 1975",
    "note": "Máquinas económicas de estirado-texturizado por aire para el mercado indio.",
    "models": [
     {
      "n": "ADT-800/4SH & /2SH",
      "spec": "Construcción de un solo lado, bobinado en 2 pisos, de 4 secciones/32 a 13 secciones/104 posiciones; estirado de POY integrado."
     },
     {
      "n": "ADT 900-950",
      "spec": "Serie más reciente de texturizado por aire; datos no públicos."
     }
    ]
   },
   {
    "name": "Zhejiang Kaicheng Intelligent Machinery",
    "city": "Xinchang, Shaoxing",
    "owner": "privada, fundada en 2003",
    "note": "Bobinadoras, retorcedoras y máquinas de recubrimiento por aire; la máquina ATY se basa en su propia plataforma de bobinadora de precisión.",
    "models": [
     {
      "n": "KC215C",
      "spec": "Máquina de texturizado por aire para POY, comercializada como «tipo SSM», basada en una bobinadora de precisión."
     },
     {
      "n": "KC215B (recubrimiento por aire, afín)",
      "spec": "Máquina de air covering para hilos de elastano: de un solo lado, 40 husos por juego, hasta 1 100 m/min."
     }
    ]
   },
   {
    "name": "Otros proveedores chinos",
    "city": "Suzhou, Shanxi y otros",
    "owner": "diversos",
    "note": "Entre otros, un proveedor de Suzhou (modelo HLK-B) y Shanxi Jingwei Chemical Fiber Machinery con máquinas ATY para PA y PES.",
    "models": [
     {
      "n": "HLK-B (proveedor de Suzhou)",
      "spec": "8 secciones de 16 = 128 husos, 70–2 000 dtex, hasta 600 m/min, bobinas de 5 kg, presión de aire 0,6–0,9 MPa; el FDY se humecta, texturiza y ensima, para hilos de tejeduría."
     },
     {
      "n": "Máquina ATY de Shanxi Jingwei",
      "spec": "Máquina de texturizado por aire para poliamida y poliéster; apenas hay datos públicos."
     }
    ]
   }
  ],
  "chips": {
   "auto": "Autodoff",
   "man": "manual",
   "legacy": "histórico",
   "poy": "POY",
   "fdy": "FDY",
   "ce": "Núcleo/efecto",
   "tech": "Técnico",
   "combo": "Combi"
  },
  "tl": [
   "Fadis es el primer fabricante en introducir el recubrimiento por aire (air covering).",
   "Schärer, Schweiter y Mettler se fusionan en SSM.",
   "Stähle-Eltex (Reutlingen) y SSM se unen: se concentra la experiencia en texturizado por aire.",
   "SSM Stähle-Eltex: DP2-T (hasta 900 dtex) y RM3-T (hasta 3 200 dtex).",
   "SSM Giudici presenta la TG1-AT manual.",
   "SSM muestra la DP5-T con fancyflex (slubs, grueso-fino) y la TG2-AT con mudador frontal.",
   "Fadis presenta la Sincro Multipla Aquajet en la ITMA de Barcelona.",
   "Turktex (TR) invierte en DP5-T para ATY de PES y PP.",
   "Rieter adquiere Barmag: SSM y Barmag pertenecen ahora al mismo grupo."
  ],
  "classif": [
   [
    "SSM es líder del mercado:",
    "Con la fusión con Stähle-Eltex (1999) y Giudici, SSM cubre hoy todo, desde el concepto de posición individual (DP5-T) hasta la máquina de ejes de doble cara (TG2-AT). SSM pertenece al Grupo Rieter, al igual que Barmag desde 2026."
   ],
   [
    "Japón:",
    "AIKI Riotech con la familia AT-501 (hasta 216 posiciones, estirado con pin calefactor), TMT con la serie REIKA para texturizado por aire y PIN."
   ],
   [
    "Italia:",
    "Fadis construye la Sincro Aquajet sobre la base de sus bobinadoras de precisión (con tobera Heberlein)."
   ],
   [
    "India y China:",
    "Himson, Aalidhra, Kaicheng (KC215C) y otros proveedores suministran máquinas económicas para hilos de textil hogar y técnicos."
   ],
   [
    "La tobera es la pieza clave:",
    "Los fabricantes de máquinas suelen montar toberas de texturizado de especialistas; las toberas HemaJet de Heberlein son también la referencia en la investigación."
   ],
   [
    "Aplicaciones:",
    "Textiles para el hogar, asientos de coche e interiores, hilos de coser, hilos técnicos y de vidrio, hilos de fantasía (slubs, grueso-fino)."
   ]
  ]
 },
 "zh": {
  "ui": {
   "eyebrow": "Knowledge Base · ATY",
   "h1": "ATY 设备：制造商、机型结构与变型",
   "lead": "空气变形机（Air Jet Texturing）互动概览：变形喷嘴中的超音速气流把超喂的单丝缠结成丝圈，使光滑的长丝具有类似短纤纱的特性。所有插图均为示意图，未按比例绘制。",
   "note": "资料截至 2026 年 11 月。制造商数据可能因机型配置而异。",
   "sources": "资料来源",
   "component": "部件",
   "tip": "提示：上方开关可切换原丝、纱线结构、给湿方式和后处理。",
   "openAty": "→ ATY 空气变形",
   "openAtyHint": "喷嘴的详细工作原理请见 ATY 空气变形模块。",
   "examples": "示例",
   "pros": "优点",
   "cons": "缺点",
   "search": "搜索",
   "searchPh": "机型、制造商、特征……",
   "region": "地区",
   "operation": "操作方式",
   "all": "全部",
   "regions": [
    "欧洲",
    "日本",
    "中国",
    "印度"
   ],
   "autodoff": "自动落筒",
   "manual": "手动",
   "treeFilter": "来自变型图的筛选：",
   "reset": "重置",
   "empty": "没有符合该筛选组合的机型。",
   "upTo": "最多 {n} 锭位",
   "source": "来源：{d}",
   "sortPos": "锭位数（最大）",
   "sortSpeed": "机械速度（米/分）",
   "barsNote": "制造商给出的最高机械速度；工艺速度在很大程度上取决于纤度、超喂和喷嘴，通常明显更低（研究试验中例如 200–600 米/分）。",
   "classif": "市场定位",
   "ariaProc": "ATY 锭位走丝路线示意图",
   "ariaProf": "机型结构",
   "treeHint": "点击一个选项：将打开已筛选的“制造商与机型”章节。"
  },
  "scenes": [
   {
    "k": "工艺",
    "title": "ATY 锭位的走丝路线",
    "text": "喂入罗拉向喷嘴输送的丝多于喷嘴后引出的丝（超喂）。在气流中，多余的单丝长度形成丝圈，并锚固在纱芯中。随后纱线经机械稳定后卷绕。点击一个部件；开关显示不同变型。"
   },
   {
    "k": "变型图",
    "title": "变型图",
    "text": "点击一个选项，即可在“制造商与机型”章节中筛选出相应的制造商和机型。"
   },
   {
    "k": "机型结构",
    "title": "机型结构",
    "text": "空气变形机比 DTY 机矮得多；各种结构的主要区别在于一个传动装置带动多少个锭位，以及落筒方式。"
   },
   {
    "k": "制造商与机型",
    "title": "制造商与机型",
    "text": "参数来自制造商资料、专业媒体和产品目录（见资料来源）。"
   },
   {
    "k": "比较",
    "title": "比较",
    "text": "ATY 机比 DTY 机小得多：从几十个到 200 多个锭位，但纤度范围非常宽，可覆盖产业用纱。"
   },
   {
    "k": "市场",
    "title": "市场结构与发展",
    "text": "行业重要事件以及各供应商的定位。"
   }
  ],
  "ctl": [
   {
    "l": "原丝",
    "o": [
     "POY（带拉伸）",
     "FDY"
    ]
   },
   {
    "l": "纱线结构",
    "o": [
     "芯丝 / 饰丝",
     "平行"
    ]
   },
   {
    "l": "给湿",
    "o": [
     "湿态",
     "干态"
    ]
   },
   {
    "l": "后处理",
    "o": [
     "机械",
     "+ 加热器"
    ]
   }
  ],
  "comp": {
   "creel": {
    "t": "纱架",
    "tags": [
     "芯丝和饰丝"
    ],
    "p": "对于芯丝/饰丝纱，每个锭位有多个原丝筒同时喂入：芯丝（超喂小，构成承力的纱芯）和饰丝（超喂大，在表面形成丝圈）。",
    "l": [
     "SSM DP5-T：旋转纱架，最多 6 根丝加备用",
     "也可加工玻璃纤维、芳纶和混纺纱"
    ]
   },
   "feed": {
    "t": "喂入罗拉与拉伸",
    "tags": [
     "超喂"
    ],
    "poy": "POY 原丝：在进入喷嘴前，丝条在两组喂入罗拉之间经热销拉伸（例如 AIKI AT-501：4 组喂入罗拉 + 热销）。热销还可以产生简单的粗细节效果。",
    "fdy": "FDY 原丝：丝条已经拉伸；每组丝只需一组喂入罗拉来设定超喂。",
    "l": [
     "超喂 =（喂入罗拉速度 − 引出速度）/ 引出速度",
     "芯丝通常约 5–30 %，饰丝可达 200 % 以上",
     "芯丝和饰丝喂入罗拉可分别调节（Fadis：芯丝导丝辊和饰丝导丝辊）"
    ]
   },
   "wet": {
    "t": "给湿",
    "tags": [
     "水"
    ],
    "wet": "芯丝在进入喷嘴前经过水槽、给湿头或滴水嘴。水能降低单丝之间的摩擦，改善丝圈的形成和稳定性——这是生产中的标准做法。",
    "dry": "干态变形形成的丝圈稳定性较差；干态加工多用于简单的网络任务或特殊材料。",
    "l": [
     "饰丝通常以干态从给湿装置旁经过"
    ]
   },
   "jet": {
    "t": "空气变形喷嘴",
    "tags": [
     "核心部件",
     "超音速"
    ],
    "p": "压缩空气（通常 6–9 bar）在喷嘴内膨胀至超音速；单丝被吹散，超喂的长度形成丝圈并锚固在纱芯中。出口处通常装有挡球（Baffle），使气流平稳。",
    "l": [
     "喷嘴几何形状决定纱线特性和耗气量",
     "典型的行业标准和研究参照：Heberlein HemaJet（例如装在 Fadis Aquajet 上）",
     "在复合机上还使用用于氨纶的空气包覆喷嘴"
    ]
   },
   "stab": {
    "t": "稳定区",
    "tags": [
     "机械"
    ],
    "p": "在两组罗拉之间，变形后的纱线被轻微再拉伸（约 1–15 %）。松散、不稳定的丝圈被拉出；该区域的张力可反映喷嘴的工作效果。",
    "l": []
   },
   "heat": {
    "t": "加热器（热后处理）",
    "tags": [
     "可选"
    ],
    "p": "喷嘴后的加热管或热辊对纱线进行热定型，降低残余收缩或调节丝圈大小（AIKI：“ATY loop can be adjusted with the second heater”）。SSM 使用热辊。",
    "l": [
     "对之后需要染色或热定型的纱线很重要"
    ]
   },
   "wind": {
    "t": "卷绕",
    "tags": [
     "筒子"
    ],
    "p": "交叉卷绕筒子，采用随机卷绕、精密卷绕或分级精密卷绕（SSM DIGICONE）。ATY 机的工艺速度远低于 DTY，并加工较粗的纤度。",
    "l": [
     "手动、前置落筒装置（TG2-AT）或自动落筒",
     "可选花式装置，用于竹节和粗细节"
    ]
   },
   "eff": {
    "t": "饰丝",
    "tags": [
     "超喂大"
    ],
    "p": "饰丝超喂很大，形成可见的丝圈；使用 POY 时它同样经热销拉伸。芯丝和饰丝采用不同颜色、纤度或材料，可得到混色纱和结构纱。",
    "l": []
   }
  },
  "sv": {
   "core": "芯丝",
   "effect": "饰丝",
   "creel": "纱架",
   "heatPin": "热销",
   "feedCore": "芯丝喂入罗拉",
   "wetting": "给湿",
   "dry": "干态",
   "coreOf": "芯丝：超喂小",
   "allOf": "所有丝：超喂相同",
   "effOf": "饰丝：超喂大（可达 200 %+）",
   "air": "压缩空气 6–9 bar",
   "jet": "变形喷嘴",
   "baffle": "+ 挡球",
   "stab": "稳定",
   "stabOf": "1–15 % 再拉伸",
   "heater": "加热器",
   "wind": "卷绕",
   "speed": "工艺速度通常 200–600 米/分"
  },
  "dims": [
   {
    "t": "原丝",
    "o": [
     {
      "b": "POY（带拉伸）",
      "d": "喷嘴前设热销或热辊。"
     },
     {
      "b": "FDY / FOY",
      "d": "已拉伸，只需超喂。"
     }
    ]
   },
   {
    "t": "纱线结构",
    "o": [
     {
      "b": "芯丝 / 饰丝",
      "d": "超喂不同，结构纱和混色纱。"
     },
     {
      "b": "花式纱",
      "d": "竹节、粗细节（T&T）。"
     },
     {
      "b": "与 DTY / 氨纶复合",
      "d": "假捻 + 空气，或空气包覆。"
     }
    ]
   },
   {
    "t": "工艺",
    "o": [
     {
      "b": "侧重湿处理",
      "d": "给湿头 / 水箱。"
     },
     {
      "b": "热后处理",
      "d": "喷嘴后设加热器或热辊。"
     }
    ]
   },
   {
    "t": "机型结构",
    "o": [
     {
      "b": "单锭位",
      "d": "每个锭位独立传动（DP5-T）。"
     },
     {
      "b": "双面，轴传动",
      "d": "锭位多，前置落筒装置（TG2-AT）。"
     },
     {
      "b": "传统轴传动机",
      "d": "罗拉装在前面板上，每块 12/24 锭。"
     },
     {
      "b": "基于络筒机",
      "d": "带喷嘴箱的精密络筒机（Fadis、Kaicheng）。"
     }
    ]
   },
   {
    "t": "应用",
    "o": [
     {
      "b": "产业用 / 粗纤度",
      "d": "汽车座椅、内饰，最高 4 000 dtex。"
     },
     {
      "b": "玻璃纤维与特种材料",
      "d": "例如 SSM DP5-T。"
     }
    ]
   }
  ],
  "prof": {
   "plate": {
    "t": "传统轴传动机",
    "ex": [
     "AIKI AT-501",
     "Himson HSS-ATX",
     "Aalidhra ADT-800"
    ],
    "d": "喂入罗拉、热销和喷嘴装在一块前面板上；长轴带动整块 12 或 24 个锭位。纱架位于机器前方或侧面，筒子在一层或两层上卷绕。",
    "pro": [
     "单锭位成本低",
     "共用长轴，一致性好"
    ],
    "con": [
     "只能按块换品种",
     "单个锭位停机会降低效率"
    ]
   },
   "double": {
    "t": "双面机，带前置落筒装置",
    "ex": [
     "SSM Giudici TG2-AT / TG1-AT"
    ],
    "d": "机器两面各有独立调节的长轴；前置落筒装置在筒子架中同时夹持一个满筒和一个空管，因此换筒不中断。",
    "pro": [
     "结构紧凑，锭位多",
     "可同时生产两种产品（每面一种）"
    ],
    "con": [
     "细至中等纤度",
     "灵活性不如单锭位机"
    ]
   },
   "single": {
    "t": "单锭位机",
    "ex": [
     "SSM DP5-T（5–40 锭位）"
    ],
    "d": "每个锭位都有可编程的独立传动，可运行各自的工艺配方；旋转纱架最多可放 6 根丝加备用。非常适合多品种小批量和产业用纱。",
    "pro": [
     "数百种配方，换品种快",
     "最高 4 000 dtex，可加工玻璃纤维"
    ],
    "con": [
     "单锭位投资较高",
     "锭位数少"
    ]
   },
   "winder": {
    "t": "带喷嘴箱的精密络筒机",
    "ex": [
     "Fadis Sincro Aquajet",
     "Kaicheng KC215C"
    ],
    "d": "以带电子导丝的精密络筒机为基础；前面依次是芯丝导丝辊和饰丝导丝辊、带变形喷嘴的水箱以及主导丝辊。在线张力测量控制卷绕张力。",
    "pro": [
     "筒子成形精确",
     "适合 FDY 花式纱"
    ],
    "con": [
     "通常不带 POY 拉伸",
     "生产线较小"
    ]
   }
  },
  "psv": {
   "creel": "纱架",
   "plate": "前面板（每块 12/24 锭）",
   "decks": "2 层",
   "frame": "中间机架 / 长轴",
   "doffer": "前置落筒：满筒 + 空管",
   "sideB": "B 面",
   "creelA": "纱架 A",
   "creelB": "纱架 B",
   "pos": "锭位 {i} · 配方 {r}",
   "single": "旋转纱架、独立传动、热辊",
   "platform": "精密络筒机平台",
   "core": "芯丝",
   "effect": "饰丝",
   "wetbox": "水箱 + 喷嘴",
   "master": "主辊",
   "sensor": "张力传感器"
  },
  "mfr": [
   {
    "name": "SSM（含 Stähle-Eltex 和 Giudici）",
    "city": "Wädenswil（韦登斯维尔）",
    "owner": "立达集团",
    "note": "空气变形机市场领导者：Stähle-Eltex（Reutlingen）于 1999 年并入 SSM，Giudici 随后加入。如今产品从单锭位概念一直覆盖到双面轴传动机。",
    "models": [
     {
      "n": "DP5-T (DP5-TF / DP5-TC)",
      "spec": "单锭位机，单面 5–40 个锭位；锭位和喂入罗拉独立驱动；PES、PA、PP、玻璃纤维；POY 和 FDY/FOY；TC 最高 4 000 dtex PES/PP；旋转纱架最多 6 根丝 + 备用；DIGICONE 或精密卷绕；可选 fancyflex，用于竹节和粗细节效果。"
     },
     {
      "n": "TG2-AT",
      "spec": "双面机，配独立前置落筒装置（满筒和空管同时位于筒子架中）；PES、PA、PP 的 POY/FDY，细至中等纤度；每面长轴单独调节。"
     },
     {
      "n": "TG1-AT",
      "spec": "手动型，用于低成本生产细至中等纤度；横动动程 190 或 245 mm。"
     },
     {
      "n": "TG30-ETC",
      "spec": "复合机：一步完成假捻变形和空气变形；ATY 芯丝/饰丝纱（含或不含氨纶）、DTY+ATY、竹节纱、DTTY（变形并加捻）。"
     },
     {
      "n": "DP2-T / RM3-T（Stähle-Eltex，历史机型）",
      "spec": "DP2-T 用于最高 900 dtex 的纱线，RM3-T 用于高性能，最高 3 200 dtex（2004 年数据）。"
     }
    ]
   },
   {
    "name": "AIKI Riotech",
    "city": "稻泽市，爱知县",
    "owner": "私营",
    "note": "AT-501 系列：喂入罗拉配夹持辊或热辊，热销用于拉伸 POY，第二加热器用于调节丝圈；轴传动，以 12 锭或 24 锭为模块。",
    "models": [
     {
      "n": "AT-501A",
      "spec": "4 组喂入罗拉 + 热销；POY 被拉伸；通过热销生产简单的 T&T 纱（粗细节）；通过第二加热器调节丝圈大小；30–600 旦；喂入罗拉 100–1 000 米/分，卷绕最高 800 米/分。"
     },
     {
      "n": "AT-501B / AT-501C2F",
      "spec": "最多 216 锭，每块 24 锭；B 型效果间距离散度更小，C2F 型配 2 组喂入罗拉；筒子 200 mm（可选 250 mm）。"
     },
     {
      "n": "AT-501 EXII",
      "spec": "5 组喂入罗拉 + 热销 + 第一加热器：T&T 纱和不同收缩率的混合纱；可选自动落筒，配 250 mm 筒子。"
     },
     {
      "n": "AT-501 HD III / HD 900",
      "spec": "每锭位 4 个热辊；用于产业用纱和汽车用纱（汽车座椅、内饰）；卷绕最高 1 000 米/分。"
     }
    ]
   },
   {
    "name": "TMT Machinery",
    "city": "大阪 / 京都",
    "owner": "合资：Toray Eng.、Murata、Teijin Seiki",
    "note": "REIKA 系列在 DTY 机之外，补充了锦纶变形、空气变形和 PIN 变形。",
    "models": [
     {
      "n": "REIKA 系列（空气 / PIN）",
      "spec": "用于空气变形和 PIN 变形的设备；技术细节未公开。"
     }
    ]
   },
   {
    "name": "Fadis",
    "city": "Solbiate Arno (VA)",
    "owner": "私营，成立于 1960 年",
    "note": "精密络筒机和空气包覆机专家（1987 年起做空气包覆）；空气变形机基于同一个“Open Platform”。",
    "models": [
     {
      "n": "Sincro (Multipla) Aquajet",
      "spec": "带电子导丝的精密空气变形机：芯丝导丝辊、饰丝导丝辊、带给湿头和 Heberlein 喷嘴的箱式喷嘴、主导丝辊；芯丝和饰丝无转向角地进入水箱；卷绕前设在线丝线张力传感器。"
     }
    ]
   },
   {
    "name": "Himson Engineering",
    "city": "苏拉特",
    "owner": "Himson Bhogibhai 集团",
    "note": "印度 DTY 和 ATY 设备制造商；ATY 系列为 HSS-ATX。",
    "models": [
     {
      "n": "HSS-ATX-3N / -9G / -15G",
      "spec": "24 至 120 锭，全自动或半自动；HMI 触摸屏；单电机驱动（ATX-9G），能耗低、质量可重复。"
     }
    ]
   },
   {
    "name": "Aalidhra",
    "city": "苏拉特 / 瑙萨里",
    "owner": "成立于 1975 年",
    "note": "面向印度市场的低成本空气拉伸变形机。",
    "models": [
     {
      "n": "ADT-800/4SH & /2SH",
      "spec": "单面结构，双层卷绕，从 4 节/32 锭到 13 节/104 锭；集成 POY 拉伸。"
     },
     {
      "n": "ADT 900-950",
      "spec": "较新的空气变形系列；数据未公开。"
     }
    ]
   },
   {
    "name": "浙江凯成智能机械（Kaicheng）",
    "city": "绍兴新昌",
    "owner": "私营，成立于 2003 年",
    "note": "络筒机、捻线机和空气包覆机；其 ATY 机基于自有的精密络筒机平台。",
    "models": [
     {
      "n": "KC215C",
      "spec": "用于 POY 的空气变形机，以“SSM 型”销售，基于精密络筒机。"
     },
     {
      "n": "KC215B（空气包覆，相关机型）",
      "spec": "用于氨纶纱的空气包覆机：单面，每套 40 锭，最高 1 100 米/分。"
     }
    ]
   },
   {
    "name": "其他中国供应商",
    "city": "苏州、山西等",
    "owner": "多家",
    "note": "其中包括一家苏州供应商（型号 HLK-B）以及山西经纬化纤机械，提供用于 PA 和 PES 的 ATY 设备。",
    "models": [
     {
      "n": "HLK-B（苏州供应商）",
      "spec": "8 节 × 16 = 128 锭，70–2 000 dtex，最高 600 米/分，筒子 5 kg，气压 0.6–0.9 MPa；FDY 经给湿、变形和上油——用于机织用纱。"
     },
     {
      "n": "山西经纬 ATY 机",
      "spec": "用于锦纶和涤纶的空气变形机；公开数据很少。"
     }
    ]
   }
  ],
  "chips": {
   "auto": "自动落筒",
   "man": "手动",
   "legacy": "历史机型",
   "poy": "POY",
   "fdy": "FDY",
   "ce": "芯丝/饰丝",
   "tech": "产业用",
   "combo": "复合"
  },
  "tl": [
   "Fadis 成为首家推出空气包覆（Air Covering）的制造商。",
   "Schärer、Schweiter 和 Mettler 合并为 SSM。",
   "Stähle-Eltex（Reutlingen）与 SSM 合并——集中了空气变形技术能力。",
   "SSM Stähle-Eltex：DP2-T（最高 900 dtex）和 RM3-T（最高 3 200 dtex）。",
   "SSM Giudici 推出手动型 TG1-AT。",
   "SSM 展出带 fancyflex（竹节、粗细节）的 DP5-T 和带前置落筒装置的 TG2-AT。",
   "Fadis 在巴塞罗那 ITMA 展会上展出 Sincro Multipla Aquajet。",
   "Turktex（土耳其）投资 DP5-T，用于生产 PES 和 PP ATY。",
   "立达收购 Barmag——SSM 和 Barmag 现属于同一集团。"
  ],
  "classif": [
   [
    "SSM 是市场领导者：",
    "通过与 Stähle-Eltex（1999 年）和 Giudici 的合并，SSM 如今覆盖从单锭位概念（DP5-T）到双面轴传动机（TG2-AT）的全部范围。SSM 隶属立达集团——自 2026 年起 Barmag 也属于该集团。"
   ],
   [
    "日本：",
    "AIKI Riotech 的 AT-501 系列（最多 216 锭位，热销拉伸），TMT 的 REIKA 系列用于空气变形和 PIN 变形。"
   ],
   [
    "意大利：",
    "Fadis 以其精密络筒机为基础制造 Sincro Aquajet（配 Heberlein 喷嘴）。"
   ],
   [
    "印度和中国：",
    "Himson、Aalidhra、凯成（KC215C）及其他供应商提供用于家纺纱和产业用纱的低价设备。"
   ],
   [
    "喷嘴是核心部件：",
    "设备制造商大多采用专业厂商的变形喷嘴；Heberlein 的 HemaJet 喷嘴也是研究中的参照标准。"
   ],
   [
    "应用：",
    "家用纺织品、汽车座椅和内饰、缝纫线、产业用纱和玻璃纤维纱、花式纱（竹节、粗细节）。"
   ]
  ]
 }
};
