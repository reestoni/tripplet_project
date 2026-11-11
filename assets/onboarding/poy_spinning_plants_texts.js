window.TEXTS = {
 "de": {
  "ui": {
   "eyebrow": "Knowledge Base · Spinnerei",
   "h1": "POY-Spinnanlagen: Hersteller, Bauformen & Varianten",
   "lead": "Interaktive Übersicht über Anlagen für teilorientiertes Garn (POY) – das Vorlagematerial der DTY-Maschinen: vom Polymer über Spinnbalken, Anblasung und Galetten bis zum Hochgeschwindigkeitswickler. Alle Abbildungen sind schematische Visualisierungen, nicht massstäblich.",
   "note": "Stand der Recherche: November 2026. Herstellerangaben können je nach Ausführung abweichen.",
   "sources": "Quellen",
   "component": "Komponente",
   "tip": "Tipp: Die Schalter oben ändern Polymerzufuhr, Anblasung, Abzug und Changierung.",
   "openFil": "→ Filamentgarn-Spinnen",
   "openFilHint": "Modul der Knowledge Base öffnen",
   "examples": "Beispiele",
   "pros": "Vorteile",
   "cons": "Nachteile",
   "search": "Suche",
   "searchPh": "Modell, Hersteller, Merkmal …",
   "region": "Region",
   "regions": [
    "Alle",
    "Europa",
    "Japan",
    "China",
    "USA"
   ],
   "scope": "Umfang",
   "scopes": [
    "Alle",
    "Komplettanlage",
    "Wickler"
   ],
   "treeFilter": "Filter aus Variantenschema:",
   "reset": "zurücksetzen",
   "upTo": "bis {n} Fäden",
   "srcSite": "Quelle / Herstellerseite: {d}",
   "empty": "Keine Modelle für diese Filterkombination.",
   "sortEnds": "Fäden pro Wickler",
   "sortChuck": "Hülsenlänge (mm)",
   "legend": [
    "Europa",
    "Japan",
    "China"
   ],
   "barsNote": "Maximalwerte laut Herstellerangabe bzw. Inserat. Mehr Fäden pro Wickler heisst kleinere Spulen pro Faden – für die DTY-Weiterverarbeitung ist das Spulengewicht oft wichtiger als die Fadenzahl.",
   "assess": "Einordnung",
   "treeHint": "Klick auf eine Ausprägung: Die Szene „Hersteller & Modelle“ öffnet sich gefiltert. Nochmals klicken hebt den Filter auf."
  },
  "scenes": [
   {
    "k": "Prozess",
    "title": "Der Weg vom Polymer zur POY-Spule",
    "text": "Die Schmelze wird über Spinnpumpen durch Düsenpakete gepresst, die Filamente werden angeblasen, präpariert und mit 2 500–3 500 m/min (PES) abgezogen. Die hohe Abzugsgeschwindigkeit orientiert die Molekülketten teilweise – daher „partially oriented“. Klick auf eine Komponente; die Schalter zeigen die Hauptvarianten."
   },
   {
    "k": "Variantenschema",
    "title": "Variantenschema",
    "text": "POY-Anlagen unterscheiden sich entlang weniger Achsen. Klick auf eine Ausprägung, um die passenden Hersteller und Modelle zu filtern."
   },
   {
    "k": "Anlagenlayouts",
    "title": "Anlagenlayouts im Querschnitt",
    "text": "Spinnanlagen sind Gebäude: Die Anordnung von Spinnboden, Anblasung, Galetten und Wickelboden bestimmt Bauhöhe, Hallenfläche, Fadenweg und Bedienung."
   },
   {
    "k": "Hersteller & Modelle",
    "title": "Hersteller & Modelle",
    "text": "Komplettanlagen- und Wicklerhersteller. Kennzahlen aus Herstellerangaben, Fachpresse und Gebrauchtmaschinen-Inseraten (siehe Quellen)."
   },
   {
    "k": "Wickler im Vergleich",
    "title": "Wickler im Vergleich",
    "text": "Fäden pro Wickler und Hülsenlänge bestimmen, wie viele Spulen pro Spinnposition entstehen und wie viel Hallenfläche pro Faden nötig ist."
   },
   {
    "k": "Markt",
    "title": "Marktstruktur & Entwicklung",
    "text": "Wichtige Meilensteine der Anbieter und eine Einordnung des Marktes."
   }
  ],
  "ctrl": {
   "lbl": [
    "Polymerzufuhr",
    "Anblasung",
    "Abzug",
    "Changierung"
   ],
   "opt": [
    [
     "Direktspinnen (CP)",
     "Chips + Extruder"
    ],
    [
     "Querstrom",
     "Radial"
    ],
    [
     "Galetten separat",
     "Im Wickler (WINGS)",
     "galettenlos"
    ],
    [
     "Kehrgewinde",
     "Rotor/Flügel"
    ]
   ]
  },
  "proc": {
   "floorSpin": "Spinnboden",
   "floorShaft": "Fallschacht",
   "floorGodet": "Galettenbühne",
   "floorMid": "Zwischenboden",
   "floorWind": "Wickelboden",
   "cp": "CP-Reaktoren",
   "cpSub": "PTA + MEG → Schmelze",
   "chips": "Chips",
   "dryer": "Trockner",
   "extr": "Extruder + Schmelzefilter",
   "beam": "Spinnbalken (Dowtherm) · Pumpe · Düsenpakete",
   "cross": "Querstrom",
   "radial": "radial",
   "lessAir": "−60–80 % Luft",
   "quench": "Anblasung",
   "oil": "Präparation",
   "windW": "WINGS-Wickler (Galetten integriert)",
   "wind": "Wickler",
   "godets": "Galetten",
   "noGodet": "kein Galettenabzug",
   "jet": "Verwirbelung",
   "rotor": "Rotor-/Flügelchangierung",
   "cam": "Kehrgewinde-Changierung",
   "emptyTube": "leere Hülse",
   "pkgs": "Spulen (z. B. 12 × 15 kg)",
   "take": "Abzug",
   "pes": "PES-POY",
   "speed": "≈ 2 500–3 500 m/min"
  },
  "comp": {
   "src": {
    "t": "Polymerzufuhr",
    "tags": [
     "Schmelze"
    ],
    "cp": "Direktspinnen: Die Schmelze kommt direkt aus der kontinuierlichen Polykondensation (CP, aus PTA + MEG) über beheizte Leitungen, Booster-Pumpen und Wärmetauscher zu den Spinnbalken. Günstigste Route für grosse PES-Mengen; Hunderte Positionen hängen an einem Reaktor.",
    "chip": "Chipspinnen: Granulat wird getrocknet, im Extruder aufgeschmolzen und über einen kontinuierlichen Schmelzefilter (CPF) verteilt. Flexibler (Spinnfärbung, Bikomponente, PA, PP, Recycling-PET), aber mehr Energie pro kg.",
    "l": [
     "Direktspinnen: kaum Produktwechsel, sehr hohe Kapazität",
     "Chips: kleine Lose, Farben, Spezialpolymere"
    ]
   },
   "beam": {
    "t": "Spinnbalken, Spinnpumpe & Düsenpaket",
    "tags": [
     "Dowtherm-beheizt"
    ],
    "p": "Der Spinnbalken wird mit Dowtherm-Dampf beheizt und verteilt die Schmelze gleichmässig auf die Positionen. Zahnradspinnpumpen dosieren pro Faden; im Düsenpaket wird gefiltert (Sand/Metallvlies) und durch die Spinndüse gepresst.",
    "l": [
     "Barmag POY 2.0: kompakteres DIO-Paket, ⅓ weniger Filtersand, Balken bis −10 % Energie",
     "Pakete von oben oder unten montiert (Jwell u. a.)",
     "Mehrere Fäden pro Position: typ. 8, 10, 12, 16 (Zickzack-Anordnung bei 16)"
    ]
   },
   "quench": {
    "t": "Anblasung (Quench)",
    "tags": [
     "Erstarren der Filamente"
    ],
    "cross": "Querstrom: Kühlluft strömt von einer Seite durch die Filamentschar – einfach und robust, Standard bei vielen Anlagen.",
    "radial": "Radial: Luft strömt symmetrisch von aussen nach innen durch das Bündel; gleichmässiger, ideal für Mikrofasern (<1 dpf). Barmag EvoQuench braucht 60–80 % weniger Prozessluft als Querstrom.",
    "l": [
     "Kühlbedingungen bestimmen Uster-Werte und Orientierung",
     "Spinnfärbung: Sieblebensdauer bei Radialanblasung beachten"
    ]
   },
   "oil": {
    "t": "Präparation",
    "tags": [
     "Spinnfinish"
    ],
    "p": "Nach dem Erstarren wird über Präparationsdüsen oder -walzen Spinnfinish aufgetragen: Fadenschluss, Gleiteigenschaften, antistatisch. Danach läuft der Faden durch den Fallschacht zum Abzug.",
    "l": [
     "Dosierung über eigene Präparationspumpen"
    ]
   },
   "godet": {
    "t": "Galetten (Abzug)",
    "tags": [
     "Geschwindigkeit",
     "Spannung"
    ],
    "sep": "Klassisch: zwei Galetten (meist unbeheizt) auf einem Zwischengeschoss oder einer Bühne über dem Wickler. Sie stellen die Abzugsgeschwindigkeit ein und entkoppeln Spinn- und Wickelspannung.",
    "wings": "WINGS (Barmag): Galetten und Verwirbelungsdüse sind in den Wickler integriert – kurzer, gerader Fadenweg, über 30 % weniger Platz, einfacheres Anlegen. Seit 2007 Marktstandard.",
    "none": "Galettenlos: Der Wickler zieht direkt ab; günstig, aber die Wickelspannung hängt direkt am Spinnprozess. Eher bei einfachen Linien.",
    "l": []
   },
   "jet": {
    "t": "Verwirbelungsdüse (Pre-Interlacing)",
    "tags": [
     "Fadenschluss"
    ],
    "p": "Eine Luftdüse vor dem Wickler setzt Verwirbelungsknoten, damit das POY-Bündel beim Abziehen in der Texturierung zusammenhält und gleichmässig läuft.",
    "l": [
     "Bei WINGS als „tangle unit“ im Wickler integriert",
     "Knotenzahl und Stabilität über Druck und Düsengeometrie"
    ]
   },
   "wind": {
    "t": "Hochgeschwindigkeitswickler",
    "tags": [
     "Revolver",
     "Autodoff"
    ],
    "p": "Revolverwickler mit zwei Spulspindeln: Ist die Spule voll, schwenkt der Revolver, der Faden wird ohne Stopp auf die leere Hülse übergeben. Typisch 8–20 Spulen pro Spindel auf 1 200–1 800 mm Hülsenlänge.",
    "l": [
     "Spulengewicht POY häufig ~15 kg",
     "Automatisches Anlegen (WINGS POY 2.0) senkt Personalbedarf und Abfall",
     "Abtransport der Spulen zunehmend automatisiert (Doffing-Roboter, Spulenlogistik)"
    ]
   },
   "trav": {
    "t": "Changierung",
    "tags": [
     "Spulenaufbau"
    ],
    "cam": "Kehrgewinde/Nutwalze: Fadenführer läuft auf einer Kehrgewindewalze hin und her – robust, bewährt, mechanisch begrenzt bei sehr hohen Geschwindigkeiten.",
    "rotor": "Rotor/Flügel (Birotor): Gegenläufige Flügel übergeben den Faden – sehr hohe Geschwindigkeiten, typisch bei FDY und modernen POY-Wicklern.",
    "l": [
     "Barmag WinFors: Reversierwelle für besonders schonende Ablage (2 500–4 000 m/min)"
    ]
   }
  },
  "dims": [
   {
    "t": "Produkt / Prozess",
    "o": [
     {
      "b": "PES-POY (Standard)",
      "s": "Vorlage für DTY; Grossteil des Volumens."
     },
     {
      "b": "PA6/PA66-POY",
      "s": "Für Nylon-DTY (Strumpf, Sport, Wäsche)."
     },
     {
      "b": "HOY",
      "s": "Hochorientiertes PA-Garn, ~10 % schneller als PA-POY."
     },
     {
      "b": "Bikomponente",
      "s": "Kern/Mantel, Seite-an-Seite, Islands-in-the-Sea."
     },
     {
      "b": "Hochtiter",
      "s": "Über 300 den pro Faden (z. B. WINGS HD)."
     }
    ]
   },
   {
    "t": "Polymerzufuhr",
    "o": [
     {
      "b": "Direktspinnen aus CP",
      "s": "Schmelze direkt aus der Polykondensation."
     },
     {
      "b": "Chips + Extruder",
      "s": "Flexibel: Farben, PA, PP, rPET, Bico."
     }
    ]
   },
   {
    "t": "Anblasung",
    "o": [
     {
      "b": "Querstrom",
      "s": "Standard, einfach, robust."
     },
     {
      "b": "Radial",
      "s": "Gleichmässiger, weniger Luft, Mikrofasern."
     },
     {
      "b": "Mikrofaser-tauglich",
      "s": "< 1 dpf Filamenttiter."
     }
    ]
   },
   {
    "t": "Abzug",
    "o": [
     {
      "b": "Galetten im Wickler",
      "s": "WINGS-Prinzip: kurzer Fadenweg, weniger Fläche."
     },
     {
      "b": "Separate Galetten",
      "s": "Klassisch auf Bühne/Zwischengeschoss."
     },
     {
      "b": "Vertikales Modul",
      "s": "Streckwerk + Wickler direkt unter dem Spinnkopf (SML VERTEX)."
     }
    ]
   },
   {
    "t": "Wickler & Changierung",
    "o": [
     {
      "b": "Kehrgewinde / Nutwalze",
      "s": "Mechanisch, robust."
     },
     {
      "b": "Rotor / Birotor",
      "s": "Sehr hohe Geschwindigkeit."
     },
     {
      "b": "Reversierwelle",
      "s": "Besonders schonend (WinFors)."
     },
     {
      "b": "Automatisches Anlegen",
      "s": "Erstmals bei WINGS POY 2.0."
     }
    ]
   },
   {
    "t": "Einsatzfall",
    "o": [
     {
      "b": "Retrofit / Modernisierung",
      "s": "Neue Wickler unter alte Spinnbalken."
     },
     {
      "b": "Labor / Pilot",
      "s": "Polymer- und Produktentwicklung."
     },
     {
      "b": "Spezial (Elastan, Industrie)",
      "s": "Abweichende Wickler und Prozesse."
     }
    ]
   }
  ],
  "prof": {
   "conv": {
    "t": "Konventionell, mehrgeschossig",
    "ex": [
     "Ältere Barmag-Anlagen (SW/CW/ACW)",
     "TMT ATi mit Galetten",
     "Chonglee, Jwell, Hi-Tech"
    ],
    "d": "Spinnbalken und Anblasung auf dem obersten Boden, darunter Fallschacht durch die Decke, Galetten auf einer Zwischenbühne und Wickler auf dem untersten Boden. Bewährt und flexibel, aber hoch und mit längeren Fadenwegen.",
    "pro": [
     "Bewährt, viele Lieferanten",
     "Galetten unabhängig vom Wickler wählbar"
    ],
    "con": [
     "Grosse Bauhöhe, mehr Hallenvolumen",
     "Anlegen über mehrere Ebenen aufwendig"
    ]
   },
   "wings": {
    "t": "WINGS – Galetten im Wickler",
    "ex": [
     "Barmag WINGS POY 1800 / HD / 2.0",
     "WINGS XS als Retrofit"
    ],
    "d": "Galetten und Verwirbelungsdüse sind in den Wickler integriert. Der Faden läuft aus dem Fallschacht direkt in die Wicklereinheit; die Galettenbühne entfällt. Das spart über 30 % Platz und vereinfacht das Anlegen – bei POY 2.0 erstmals automatisch.",
    "pro": [
     "Kurzer, gerader Fadenweg",
     "Weniger Fläche und Personal"
    ],
    "con": [
     "Bindung an einen Anbieter (Barmag)",
     "Wickler wird komplexer"
    ]
   },
   "vertex": {
    "t": "Vertikales Linienmodul",
    "ex": [
     "SML Austrofil VERTEX 3×8 bis 8×8"
    ],
    "d": "Streck- und Wickeleinheit sitzen direkt unter Spinnkopf und Anblasung; jede Linie ist ein eigenständiges Modul. Kapazität wächst durch zusätzliche Spinneinheiten (24 → 32 → 48 → 64 Fäden).",
    "pro": [
     "30 % weniger Fläche als SML MT/HT 4×4",
     "Schrittweise erweiterbar"
    ],
    "con": [
     "Kleinere Linien als Grossanlagen",
     "Eher für Chips/Spezialitäten"
    ]
   },
   "lab": {
    "t": "Labor- und Pilotanlage",
    "ex": [
     "Fourné",
     "Hills (Bi-/Trikomponente)",
     "SML/andere Pilotlinien"
    ],
    "d": "Kleine Extruder (oft mehrere für Bikomponenten), ein bis wenige Spinnstellen, Galetten und ein kompakter Wickler auf einer Ebene. Für Polymer- und Additivversuche, neue Querschnitte und Kleinmengen.",
    "pro": [
     "Schnelle Versuche, wenig Material",
     "Viele Polymere und Querschnitte"
    ],
    "con": [
     "Nicht für Produktionsmengen",
     "Übertragbarkeit auf Grossanlage prüfen"
    ]
   }
  },
  "psvg": {
   "floorSpin": "Spinnboden",
   "floorGodet": "Galettenbühne",
   "beam": "Spinnbalken",
   "quench": "Anblasung",
   "godets": "Galetten",
   "wind": "Wickler",
   "wingsUnit": "WINGS-Einheit",
   "wingsA": "Galetten + Verwirbelung",
   "wingsB": "im Wickler integriert",
   "noStage": "keine Galettenbühne → niedriger",
   "module": "Modul {i} · 8 Fäden",
   "grows": "Linie wächst modular: 3×8 = 24 → bis 64 Fäden",
   "extr": "Extruder A + B",
   "bico": "Bico-Spinnkopf",
   "compact": "Kompaktwickler",
   "ss": "Seite an Seite",
   "cs": "Kern/Mantel"
  },
  "mfr": [
   {
    "name": "Barmag (Oerlikon Barmag)",
    "city": "Remscheid / Chemnitz",
    "owner": "seit 02/2026 Rieter-Konzern",
    "note": "Komplettanlagen von der Polykondensation (CP) bis zum Wickler. Erfinder des WINGS-Prinzips: Galetten und Verwirbelung sitzen direkt im Wickler.",
    "models": [
     {
      "n": "WINGS POY 2.0 (POY-2.0-Konzept)",
      "spec": "Vorgestellt an der ITMA Asia 2025: erstmals automatisches Anlegen am Wickler, grösserer Rotorhub (längere Parkzeit), aktive Umkehr der Changierung; dazu kompakteres DIO-Düsenpaket (rund ⅓ weniger Filtersand), überarbeiteter Spinnbalken (bis −10 % Energie) und EvoQuench 2.0."
     },
     {
      "n": "WINGS POY 1800",
      "spec": "Ab 2014: 1 800-mm-Hülse mit 12 Fäden (Standard, +20 % gegenüber 1500/10) oder 16 Fäden (Zickzack-Anordnung der Düsenpakete); PES 30–300 den final."
     },
     {
      "n": "WINGS POY HD",
      "spec": "Für Hochtiter: zusätzliche Galette im Fadeneinlauf, 12 Spulen bis 600d/576f; dreifach längere Parkzeit. Kombination mit eAFK Big V in der Texturierung."
     },
     {
      "n": "WINGS PA / HOY",
      "spec": "PA-POY 20–150 den final (PA66 bis 100 den); HOY 30–150 den bei bis 5 200 m/min."
     },
     {
      "n": "WINGS POY XS",
      "spec": "Retrofit-Reihe für ältere Anlagen mit SW-, CW- und ACW-Wicklern: fünf Modelle mit 8–12 Fäden und 1 200–1 800 mm Hülsenlänge."
     },
     {
      "n": "WinFors",
      "spec": "Wickler mit Reversierwelle für empfindliche Garne (Mikrofilamente, Muttergarn, Airbag); 2 500–4 000 m/min; von 4 auf 8 Fäden umrüstbar."
     },
     {
      "n": "EvoQuench (Radialanblasung)",
      "spec": "Luft strömt symmetrisch von aussen nach innen durchs Filamentbündel; 60–80 % weniger Prozessluft als Querstrom; 0,3–3 dpf; seit 2019 auch für PA."
     },
     {
      "n": "ACW / CW / SW (historisch)",
      "spec": "Klassische Wickler mit separaten Galetten; ACW gab es ab 2004 mit bis 1 600 mm Hülsenlänge."
     }
    ]
   },
   {
    "name": "TMT Machinery",
    "city": "Osaka / Kyoto",
    "owner": "JV von Toray Engineering, Murata und Teijin Seiki (2002)",
    "note": "Spinn- und Streckprozesse für POY/FDY/IDY sowie die ATi-Wicklerfamilie; Know-how aus Teijin Seiki, Toray Engineering und Murata.",
    "models": [
     {
      "n": "ATi-418R/12 „ORCA“",
      "spec": "POY-Wickler mit 12 Fäden und 15-kg-Spulen; Funktion zur Verbesserung der Garnqualität in der Spule."
     },
     {
      "n": "MANTA-618",
      "spec": "Neueres Modell mit 16 Fäden auf 1 800-mm-Hülse (Angabe aus Gebrauchtmarkt-Inserat)."
     },
     {
      "n": "ATi-Serie",
      "spec": "Automatische Hochgeschwindigkeitswickler, 1 200–1 520 mm Hülsenlänge, wahlweise Rotor- oder Kehrgewinde-Changierung."
     },
     {
      "n": "ATi-M",
      "spec": "Konzept mit hoher Fadenzahl und grossem Spulenvolumen."
     },
     {
      "n": "ATi-H / ATi-459α",
      "spec": "ATi-H für Industriegarn (600–1 350 mm, 2–6 Fäden); ATi-459α für Elastan (Spandex)."
     }
    ]
   },
   {
    "name": "SML Maschinengesellschaft",
    "city": "Redlham",
    "owner": "privat (Extrusionsspezialist)",
    "note": "Austrofil-Spinnlinien; die VERTEX-Reihe ordnet Streckwerk und Wickler direkt unter Spinnkopf und Anblasung an.",
    "models": [
     {
      "n": "Austrofil VERTEX POY/FDY",
      "spec": "Vertikales Modul: Grundausbau 3×8 = 24 Fäden, erweiterbar auf 32/48/64; 30 % weniger Fläche als MT/HT 4×4; 2 000–4 500 m/min; PET, PP, PA6, 75–800 den; PET 270 bzw. 540 kg/h; drei Wicklertypen (u. a. Nutwalze, Rotor)."
     }
    ]
   },
   {
    "name": "STC Spinnzwirn",
    "city": "Chemnitz",
    "owner": "privat",
    "note": "Wickler für Ersatz und Modernisierung sowie Abzugsmaschinen mit beheizten Galetten.",
    "models": [
     {
      "n": "RAPTOR CX1200",
      "spec": "Wickler für Ersatz/Modernisierung; Portfolio 800–5 000 m/min, 600- und 1 200-mm-Hülsen, bis 8 Fäden pro Wickler."
     },
     {
      "n": "babyASW604 / 906",
      "spec": "Kompakte Hochgeschwindigkeitswickler (600 mm Hülse) für kleinere Linien und Spezialgarne."
     }
    ]
   },
   {
    "name": "Beijing Chonglee Machinery Engineering",
    "city": "Peking",
    "owner": "China Textile Machinery (Gruppe)",
    "note": "Grosser chinesischer Anbieter von POY-, FDY- und Industriegarnanlagen sowie Hochgeschwindigkeitswicklern; auf dem Gebrauchtmarkt neben TMT und Barmag verbreitet.",
    "models": [
     {
      "n": "POY-Spinnanlage (manueller/autom. Wickler)",
      "spec": "Komplette POY-Anlagen, ebenso FDY, Industriegarn und Differenzialgarne. Technische Details kaum öffentlich (Website zurzeit offline)."
     },
     {
      "n": "BWA55T-1380",
      "spec": "Wickler (FDY), 8 oder 16 Fäden umschaltbar, 1 380 mm Hülse, 50–150 den (Inserat, Baujahr 2012)."
     }
    ]
   },
   {
    "name": "Jwell Fiber Machinery",
    "city": "Suzhou / Shanghai",
    "owner": "Jwell-Gruppe (Extrusion)",
    "note": "Komplettanlagen PET/PA6/Bikomponente, auch CP-Direktspinnen als Turnkey; eigene JW-Wickler.",
    "models": [
     {
      "n": "PET/PA6/Bico-POY-Anlage",
      "spec": "30–330 dtex PES-POY; Querstrom- oder Radialanblasung; Pakete von oben oder unten; Prozessgeschwindigkeit PET ca. 3 200 m/min, PA6 4 300 m/min; 6–12 Positionen je Linie (kundenspezifisch)."
     },
     {
      "n": "JW-Hochgeschwindigkeitswickler",
      "spec": "1 800 mm Hülse, 4 000 m/min, 12/18/20 Spulen (PET); Kehrgewinde- und Birotor-Ausführungen."
     }
    ]
   },
   {
    "name": "Jiangsu TITA Intelligent Technology",
    "city": "Jiangsu",
    "owner": "privat (seit 2018)",
    "note": "POY-, FDY- und BCF-Spinnanlagen, Wickler, Extruder, Filter und Anblasung.",
    "models": [
     {
      "n": "TWA-Wickler",
      "spec": "Baureihe TWA900G bis TWA1800T, Hülsenlängen 900–1 800 mm."
     }
    ]
   },
   {
    "name": "Hi-Tech Heavy Industry (über ATE)",
    "city": "China; Vertrieb ATE Indien",
    "owner": "–",
    "note": "POY/FDY-Linien für PES, PA und PP, in Indien von ATE vertrieben.",
    "models": [
     {
      "n": "ZWT-Wickler (Kehrgewinde)",
      "spec": "6–20 Fäden (POY bis 16), Hülse bis 1 680 mm (POY), bis 4 800 m/min, Vollspule bis 15 kg; POY 80–500 den."
     },
     {
      "n": "ZWB-Wickler (Birotor)",
      "spec": "10–20 Fäden, Hülse bis 1 500 mm (FDY)."
     }
    ]
   },
   {
    "name": "Fourné Polymertechnik",
    "city": "Alfter",
    "owner": "privat",
    "note": "Labor-, Pilot- und Spezialanlagen bis Produktionsgrösse, plus Reinigungsanlagen für Spinnteile.",
    "models": [
     {
      "n": "Labor- und Pilot-Spinnanlagen",
      "spec": "Kleine Extruder-Linien für Polymer- und Additivversuche, Mono- und Multifilament."
     }
    ]
   },
   {
    "name": "Hills Inc.",
    "city": "West Melbourne, FL",
    "owner": "privat",
    "note": "Spezialist für Bi- und Trikomponenten-Spinntechnik (Kern/Mantel, Seite-an-Seite, Islands-in-the-Sea) – vom Labor bis zur Produktionsanlage.",
    "models": [
     {
      "n": "Multikomponenten-Filamentanlagen",
      "spec": "POY/FOY/UOY sowie Spinnvlies; geätzte Spinnpaket-Platten für komplexe Querschnitte."
     }
    ]
   }
  ],
  "chips": {
   "wings": "WINGS",
   "radial": "radial",
   "legacy": "historisch",
   "retrofit": "Retrofit",
   "pa": "PA",
   "pes": "PES",
   "bico": "Bico",
   "lab": "Labor"
  },
  "tl": [
   "TMT Machinery entsteht aus Toray Engineering, Murata und Teijin Seiki.",
   "Barmag ACW mit bis 1 600 mm Hülsenlänge; Referenz: 576 Positionen / 4 320 POY-Fäden Direktspinnen in China.",
   "Barmag WINGS (ITMA München): Galetten und Verwirbelung im Wickler.",
   "WINGS auch für PA-POY (20–150 den).",
   "WINGS POY 1800 mit 12 bzw. 16 Fäden; WINGS HOY. Bis dahin ~14 000 WINGS-Wickler verkauft.",
   "WINGS POY XS (Retrofit) und WinFors (Reversierwelle) an der ITMA Mailand.",
   "WINGS POY HD für Hochtiter bis 600d/576f.",
   "EvoQuench-Radialanblasung erstmals für PA-POY (120 Positionen, China).",
   "Barmag POY 2.0 an der ITMA Asia; SML bringt VERTEX für PET.",
   "Rieter übernimmt Barmag (2. Feb.); WINGS POY 2.0 öffentlich an der ITM Istanbul."
  ],
  "assess": [
   [
    "Barmag dominiert das Premiumsegment:",
    "WINGS (Galetten im Wickler) hat sich seit 2007 als Standard etabliert; laut Barmag wurden bis 2013 rund 14 000 WINGS-Wickler verkauft. Seit Februar 2026 gehört Barmag zu Rieter."
   ],
   [
    "TMT",
    "ist mit der ATi-Wicklerfamilie (ORCA, MANTA) der zweite grosse Anbieter; beide Firmen nennen für sich je rund 40 % Anteil am Chemiefaser-Maschinenmarkt (Eigenangaben, nicht deckungsgleich abgegrenzt)."
   ],
   [
    "China:",
    "Beijing Chonglee, Jwell, TITA und Hi-Tech liefern Komplettanlagen und Wickler für den riesigen Inlandmarkt; Gebrauchtmarkt-Inserate nennen Chonglee regelmässig neben TMT und Barmag."
   ],
   [
    "Nischen:",
    "SML (AT) mit kompakten Vertikallinien, STC Spinnzwirn (DE) für Ersatz- und Spezialwickler, Fourné (DE) und Hills (US) für Labor-, Pilot- und Bikomponenten-Anlagen."
   ],
   [
    "Kunden:",
    "Die POY-Produktion ist stark auf chinesische Polyesterkonzerne konzentriert (u. a. Tongkun, Hengyi, Xin Feng Ming), daneben Reliance (IN) und Sasa (TR)."
   ],
   [
    "Trends:",
    "mehr Fäden pro Wickler, Radialanblasung für Mikrofasern, automatisches Anlegen (WINGS POY 2.0), weniger Energie im Spinnbalken, Spinnfärbung, Digitalisierung (atmos.io)."
   ]
  ],
  "sources": [
   "Textile World – Barmag POY 2.0 (März 2026)",
   "texdata – POY 2.0, Spinnbalken −10 % Energie",
   "Barmag – WINGS jetzt auch für PA-POY (2010)",
   "Textile World – WINGS POY 1800",
   "Barmag – WINGS-Familie wächst (1800/12 und 16, HOY)",
   "Fiber Journal – WINGS 1800, HD, XS, HOY",
   "Barmag – WINGS POY XS (Retrofit)",
   "Textination – WINGS HD 1800 (600d/576f)",
   "Textile World – WinFors",
   "texdata – ACW 1600 (2004)",
   "Fiber Journal – EvoQuench Radialanblasung",
   "Textile World – EvoQuench PA (120 Positionen)",
   "Barmag – FDY-Broschüre 2025 (EvoQuench −80 % Kühlluft)",
   "Barmag Engineering – Referenzanlagen",
   "Textile World – Rieter übernimmt Barmag",
   "DirectIndustry – TMT ATi-Serie",
   "DirectIndustry – TMT ATi-418R/12 ORCA",
   "DirectIndustry – TMT ATi-M",
   "DirectIndustry – TMT ATi-H",
   "Texmachines – TMT MANTA-618 (16 Fäden, 1 800 mm)",
   "Indian Textile Magazine – TMT-Hintergrund",
   "Texmachines – Chonglee BWA55T-1380",
   "Made-in-China – Gebrauchtmarkt TMT/Chonglee/Barmag",
   "Jwell – Katalog Chemiefaser-Spinnanlagen",
   "Jwell – Hochgeschwindigkeitswickler 1 800 mm",
   "TITA – TWA-Wickler",
   "ATE – POY/FDY-Linien (Hi-Tech Heavy Industry)",
   "SML – Austrofil VERTEX",
   "SML – VERTEX Datenblatt",
   "STC Spinnzwirn – Wickler (ITMA Asia 2025)",
   "Fourné – Labor- und Pilotanlagen",
   "Hills Inc. – Bikomponenten-Spinnanlagen",
   "US 4318676 – Fadenzahl pro Spinnposition",
   "EP 2184386 – TMT, mehrgeschossiges Spinnsystem",
   "DIResearch – POY-Produzenten"
  ]
 },
 "en": {
  "ui": {
   "eyebrow": "Knowledge Base · Spinning",
   "h1": "POY spinning plants: manufacturers, designs & variants",
   "lead": "Interactive overview of plants for partially oriented yarn (POY) – the feed yarn for DTY machines: from the polymer via spin beam, quench and godets to the high-speed winder. All drawings are schematic visualisations, not to scale.",
   "note": "Research status: November 2026. Manufacturer data may differ depending on the version.",
   "sources": "Sources",
   "component": "Component",
   "tip": "Tip: the switches above change polymer feed, quench, take-up and traverse.",
   "openFil": "→ Filament yarn spinning",
   "openFilHint": "Open Knowledge Base module",
   "examples": "Examples",
   "pros": "Advantages",
   "cons": "Disadvantages",
   "search": "Search",
   "searchPh": "Model, manufacturer, feature …",
   "region": "Region",
   "regions": [
    "All",
    "Europe",
    "Japan",
    "China",
    "USA"
   ],
   "scope": "Scope",
   "scopes": [
    "All",
    "Complete plant",
    "Winder"
   ],
   "treeFilter": "Filter from the variant scheme:",
   "reset": "reset",
   "upTo": "up to {n} ends",
   "srcSite": "Source / manufacturer site: {d}",
   "empty": "No models for this filter combination.",
   "sortEnds": "Ends per winder",
   "sortChuck": "Chuck length (mm)",
   "legend": [
    "Europe",
    "Japan",
    "China"
   ],
   "barsNote": "Maximum values as stated by the manufacturer or listing. More ends per winder means smaller packages per end – for DTY processing the package weight is often more important than the number of ends.",
   "assess": "Assessment",
   "treeHint": "Click an option: the \"Manufacturers & models\" scene opens filtered. Click again to clear the filter."
  },
  "scenes": [
   {
    "k": "Process",
    "title": "From polymer to POY package",
    "text": "Spin pumps press the melt through spin packs, the filaments are quenched, spin finish is applied and they are taken up at 2,500–3,500 m/min (PES). The high take-up speed partially orients the molecular chains – hence \"partially oriented\". Click a component; the switches show the main variants."
   },
   {
    "k": "Variant scheme",
    "title": "Variant scheme",
    "text": "POY plants differ along a few axes. Click an option to filter the matching manufacturers and models."
   },
   {
    "k": "Plant layouts",
    "title": "Plant layouts in cross-section",
    "text": "Spinning plants are buildings: the arrangement of spinning floor, quench, godets and winding floor determines building height, floor space, yarn path and operation."
   },
   {
    "k": "Manufacturers & models",
    "title": "Manufacturers & models",
    "text": "Makers of complete plants and winders. Figures from manufacturer data, trade press and used-machinery listings (see sources)."
   },
   {
    "k": "Winders compared",
    "title": "Winders compared",
    "text": "Ends per winder and chuck length determine how many packages each spinning position produces and how much floor space is needed per end."
   },
   {
    "k": "Market",
    "title": "Market structure & development",
    "text": "Key milestones of the suppliers and an assessment of the market."
   }
  ],
  "ctrl": {
   "lbl": [
    "Polymer feed",
    "Quench",
    "Take-up",
    "Traverse"
   ],
   "opt": [
    [
     "Direct spinning (CP)",
     "Chips + extruder"
    ],
    [
     "Cross-flow",
     "Radial"
    ],
    [
     "Separate godets",
     "In the winder (WINGS)",
     "Godetless"
    ],
    [
     "Cam traverse",
     "Rotary blade"
    ]
   ]
  },
  "proc": {
   "floorSpin": "Spinning floor",
   "floorShaft": "Spinning duct",
   "floorGodet": "Godet platform",
   "floorMid": "Intermediate floor",
   "floorWind": "Winding floor",
   "cp": "CP reactors",
   "cpSub": "PTA + MEG → melt",
   "chips": "Chips",
   "dryer": "Dryer",
   "extr": "Extruder + melt filter",
   "beam": "Spin beam (Dowtherm) · pump · spin packs",
   "cross": "Cross-flow",
   "radial": "radial",
   "lessAir": "−60–80 % air",
   "quench": "Quench",
   "oil": "Spin finish",
   "windW": "WINGS winder (godets integrated)",
   "wind": "Winder",
   "godets": "Godets",
   "noGodet": "no godet take-up",
   "jet": "Interlacing",
   "rotor": "Rotary blade traverse",
   "cam": "Cam traverse",
   "emptyTube": "empty tube",
   "pkgs": "Packages (e.g. 12 × 15 kg)",
   "take": "Take-up",
   "pes": "PES POY",
   "speed": "≈ 2,500–3,500 m/min"
  },
  "comp": {
   "src": {
    "t": "Polymer feed",
    "tags": [
     "Melt"
    ],
    "cp": "Direct spinning: the melt comes straight from continuous polycondensation (CP, from PTA + MEG) via heated transfer lines, booster pumps and heat exchangers to the spin beams. The cheapest route for large PES volumes; hundreds of positions are fed by one reactor.",
    "chip": "Chip spinning: chips are dried, melted in the extruder and distributed via a continuous polymer filter (CPF). More flexible (dope dyeing, bicomponent, PA, PP, recycled PET), but more energy per kg.",
    "l": [
     "Direct spinning: hardly any product changes, very high capacity",
     "Chips: small lots, colours, speciality polymers"
    ]
   },
   "beam": {
    "t": "Spin beam, spin pump & spin pack",
    "tags": [
     "Dowtherm-heated"
    ],
    "p": "The spin beam is heated with Dowtherm vapour and distributes the melt evenly to the positions. Gear-type spin pumps meter each end; in the spin pack the melt is filtered (sand/metal fleece) and pressed through the spinneret.",
    "l": [
     "Barmag POY 2.0: more compact DIO pack, ⅓ less filter sand, beam up to −10 % energy",
     "Packs mounted from above or below (Jwell and others)",
     "Several ends per position: typically 8, 10, 12, 16 (zigzag arrangement for 16)"
    ]
   },
   "quench": {
    "t": "Quench",
    "tags": [
     "Solidifying the filaments"
    ],
    "cross": "Cross-flow: cooling air flows through the filament curtain from one side – simple and robust, standard on many plants.",
    "radial": "Radial: air flows symmetrically from the outside inwards through the bundle; more uniform, ideal for microfibres (<1 dpf). Barmag EvoQuench needs 60–80 % less process air than cross-flow.",
    "l": [
     "Quench conditions determine Uster values and orientation",
     "Dope dyeing: watch screen life with radial quench"
    ]
   },
   "oil": {
    "t": "Spin finish application",
    "tags": [
     "Spin finish"
    ],
    "p": "After solidification, spin finish is applied via finish applicators (jets) or kiss rolls: cohesion, frictional properties, antistatic. The yarn then runs down the spinning duct to the take-up.",
    "l": [
     "Metered by dedicated finish pumps"
    ]
   },
   "godet": {
    "t": "Godets (take-up)",
    "tags": [
     "Speed",
     "Tension"
    ],
    "sep": "Classic: two godets (usually unheated) on an intermediate floor or a platform above the winder. They set the take-up speed and decouple spinning tension from winding tension.",
    "wings": "WINGS (Barmag): godets and interlacing jet are integrated into the winder – short, straight yarn path, more than 30 % less space, easier string-up. Market standard since 2007.",
    "none": "Godetless: the winder takes up directly; inexpensive, but the winding tension depends directly on the spinning process. Mostly on simple lines.",
    "l": []
   },
   "jet": {
    "t": "Interlacing jet (pre-interlacing)",
    "tags": [
     "Yarn cohesion"
    ],
    "p": "An air jet in front of the winder places interlacing nips so that the POY bundle holds together and runs evenly when it is unwound in texturing.",
    "l": [
     "Integrated into the winder as a \"tangle unit\" with WINGS",
     "Number and stability of nips set by pressure and jet geometry"
    ]
   },
   "wind": {
    "t": "High-speed winder",
    "tags": [
     "Turret",
     "Auto-doff"
    ],
    "p": "Turret winder with two chucks: when the package is full, the turret swivels and the yarn is transferred to the empty tube without stopping. Typically 8–20 packages per chuck on 1,200–1,800 mm chuck length.",
    "l": [
     "POY package weight often ~15 kg",
     "Automatic string-up (WINGS POY 2.0) reduces staffing and waste",
     "Package removal increasingly automated (doffing robots, package logistics)"
    ]
   },
   "trav": {
    "t": "Traverse",
    "tags": [
     "Package build"
    ],
    "cam": "Cam traverse / grooved roll: a yarn guide moves back and forth on a cam drum – robust, proven, mechanically limited at very high speeds.",
    "rotor": "Rotary blade (birotor): counter-rotating blades hand the yarn over – very high speeds, typical of FDY and modern POY winders.",
    "l": [
     "Barmag WinFors: reversing shaft for especially gentle laying (2,500–4,000 m/min)"
    ]
   }
  },
  "dims": [
   {
    "t": "Product / process",
    "o": [
     {
      "b": "PES POY (standard)",
      "s": "Feed yarn for DTY; the bulk of the volume."
     },
     {
      "b": "PA6/PA66 POY",
      "s": "For nylon DTY (hosiery, sports, lingerie)."
     },
     {
      "b": "HOY",
      "s": "Highly oriented PA yarn, ~10 % faster than PA POY."
     },
     {
      "b": "Bicomponent",
      "s": "Core/sheath, side-by-side, islands-in-the-sea."
     },
     {
      "b": "High titer",
      "s": "Over 300 den per end (e.g. WINGS HD)."
     }
    ]
   },
   {
    "t": "Polymer feed",
    "o": [
     {
      "b": "Direct spinning from CP",
      "s": "Melt straight from polycondensation."
     },
     {
      "b": "Chips + extruder",
      "s": "Flexible: colours, PA, PP, rPET, bico."
     }
    ]
   },
   {
    "t": "Quench",
    "o": [
     {
      "b": "Cross-flow",
      "s": "Standard, simple, robust."
     },
     {
      "b": "Radial",
      "s": "More uniform, less air, microfibres."
     },
     {
      "b": "Microfibre-capable",
      "s": "< 1 dpf filament titer."
     }
    ]
   },
   {
    "t": "Take-up",
    "o": [
     {
      "b": "Godets in the winder",
      "s": "WINGS principle: short yarn path, less floor space."
     },
     {
      "b": "Separate godets",
      "s": "Classic, on a platform/intermediate floor."
     },
     {
      "b": "Vertical module",
      "s": "Drawing unit + winder directly below the spin head (SML VERTEX)."
     }
    ]
   },
   {
    "t": "Winder & traverse",
    "o": [
     {
      "b": "Cam traverse / grooved roll",
      "s": "Mechanical, robust."
     },
     {
      "b": "Rotary blade / birotor",
      "s": "Very high speed."
     },
     {
      "b": "Reversing shaft",
      "s": "Especially gentle (WinFors)."
     },
     {
      "b": "Automatic string-up",
      "s": "First on WINGS POY 2.0."
     }
    ]
   },
   {
    "t": "Use case",
    "o": [
     {
      "b": "Retrofit / modernisation",
      "s": "New winders under old spin beams."
     },
     {
      "b": "Lab / pilot",
      "s": "Polymer and product development."
     },
     {
      "b": "Special (elastane, industrial)",
      "s": "Different winders and processes."
     }
    ]
   }
  ],
  "prof": {
   "conv": {
    "t": "Conventional, multi-storey",
    "ex": [
     "Older Barmag plants (SW/CW/ACW)",
     "TMT ATi with godets",
     "Chonglee, Jwell, Hi-Tech"
    ],
    "d": "Spin beam and quench on the top floor, below them the spinning duct through the ceiling, godets on an intermediate platform and winders on the bottom floor. Proven and flexible, but tall and with longer yarn paths.",
    "pro": [
     "Proven, many suppliers",
     "Godets can be chosen independently of the winder"
    ],
    "con": [
     "Large building height, more hall volume",
     "String-up across several levels is laborious"
    ]
   },
   "wings": {
    "t": "WINGS – godets in the winder",
    "ex": [
     "Barmag WINGS POY 1800 / HD / 2.0",
     "WINGS XS as retrofit"
    ],
    "d": "Godets and interlacing jet are integrated into the winder. The yarn runs from the spinning duct straight into the winder unit; the godet platform is no longer needed. This saves more than 30 % space and simplifies string-up – automatic for the first time with POY 2.0.",
    "pro": [
     "Short, straight yarn path",
     "Less floor space and staff"
    ],
    "con": [
     "Tied to one supplier (Barmag)",
     "The winder becomes more complex"
    ]
   },
   "vertex": {
    "t": "Vertical line module",
    "ex": [
     "SML Austrofil VERTEX 3×8 to 8×8"
    ],
    "d": "Drawing and winding unit sit directly below spin head and quench; each line is a self-contained module. Capacity grows with additional spinning units (24 → 32 → 48 → 64 ends).",
    "pro": [
     "30 % less floor space than SML MT/HT 4×4",
     "Can be expanded step by step"
    ],
    "con": [
     "Smaller lines than large plants",
     "Rather for chips/specialities"
    ]
   },
   "lab": {
    "t": "Lab and pilot plant",
    "ex": [
     "Fourné",
     "Hills (bi-/tricomponent)",
     "SML/other pilot lines"
    ],
    "d": "Small extruders (often several for bicomponents), one to a few spinning positions, godets and a compact winder on one level. For polymer and additive trials, new cross-sections and small quantities.",
    "pro": [
     "Fast trials, little material",
     "Many polymers and cross-sections"
    ],
    "con": [
     "Not for production volumes",
     "Check transferability to the large plant"
    ]
   }
  },
  "psvg": {
   "floorSpin": "Spinning floor",
   "floorGodet": "Godet platform",
   "beam": "Spin beam",
   "quench": "Quench",
   "godets": "Godets",
   "wind": "Winder",
   "wingsUnit": "WINGS unit",
   "wingsA": "Godets + interlacing",
   "wingsB": "integrated in the winder",
   "noStage": "no godet platform → lower",
   "module": "Module {i} · 8 ends",
   "grows": "Line grows modularly: 3×8 = 24 → up to 64 ends",
   "extr": "Extruders A + B",
   "bico": "Bico spin head",
   "compact": "Compact winder",
   "ss": "Side-by-side",
   "cs": "Core/sheath"
  },
  "mfr": [
   {
    "name": "Barmag (Oerlikon Barmag)",
    "city": "Remscheid / Chemnitz",
    "owner": "Rieter Group since 02/2026",
    "note": "Complete plants from polycondensation (CP) to the winder. Inventor of the WINGS principle: godets and interlacing sit directly in the winder.",
    "models": [
     {
      "n": "WINGS POY 2.0 (POY 2.0 concept)",
      "spec": "Presented at ITMA Asia 2025: automatic string-up at the winder for the first time, larger rotor stroke (longer parking time), active traverse reversal; plus a more compact DIO spin pack (about ⅓ less filter sand), a revised spin beam (up to −10 % energy) and EvoQuench 2.0."
     },
     {
      "n": "WINGS POY 1800",
      "spec": "From 2014: 1,800 mm chuck with 12 ends (standard, +20 % compared with 1500/10) or 16 ends (zigzag arrangement of the spin packs); PES 30–300 den final."
     },
     {
      "n": "WINGS POY HD",
      "spec": "For high titers: additional godet at the yarn inlet, 12 packages up to 600d/576f; three times longer parking time. Combined with eAFK Big V in texturing."
     },
     {
      "n": "WINGS PA / HOY",
      "spec": "PA POY 20–150 den final (PA66 up to 100 den); HOY 30–150 den at up to 5,200 m/min."
     },
     {
      "n": "WINGS POY XS",
      "spec": "Retrofit series for older plants with SW, CW and ACW winders: five models with 8–12 ends and 1,200–1,800 mm chuck length."
     },
     {
      "n": "WinFors",
      "spec": "Winder with reversing shaft for sensitive yarns (microfilaments, mother yarn, airbag); 2,500–4,000 m/min; convertible from 4 to 8 ends."
     },
     {
      "n": "EvoQuench (radial quench)",
      "spec": "Air flows symmetrically from the outside inwards through the filament bundle; 60–80 % less process air than cross-flow; 0.3–3 dpf; also for PA since 2019."
     },
     {
      "n": "ACW / CW / SW (historical)",
      "spec": "Classic winders with separate godets; ACW was available from 2004 with up to 1,600 mm chuck length."
     }
    ]
   },
   {
    "name": "TMT Machinery",
    "city": "Osaka / Kyoto",
    "owner": "JV of Toray Engineering, Murata and Teijin Seiki (2002)",
    "note": "Spinning and drawing processes for POY/FDY/IDY plus the ATi winder family; know-how from Teijin Seiki, Toray Engineering and Murata.",
    "models": [
     {
      "n": "ATi-418R/12 \"ORCA\"",
      "spec": "POY winder with 12 ends and 15 kg packages; function for improving yarn quality in the package."
     },
     {
      "n": "MANTA-618",
      "spec": "Newer model with 16 ends on a 1,800 mm chuck (figure from a used-machinery listing)."
     },
     {
      "n": "ATi series",
      "spec": "Automatic high-speed winders, 1,200–1,520 mm chuck length, rotary blade or cam traverse as an option."
     },
     {
      "n": "ATi-M",
      "spec": "Concept with a high number of ends and large package volume."
     },
     {
      "n": "ATi-H / ATi-459α",
      "spec": "ATi-H for industrial yarn (600–1,350 mm, 2–6 ends); ATi-459α for elastane (spandex)."
     }
    ]
   },
   {
    "name": "SML Maschinengesellschaft",
    "city": "Redlham",
    "owner": "private (extrusion specialist)",
    "note": "Austrofil spinning lines; the VERTEX series places drawing unit and winder directly below spin head and quench.",
    "models": [
     {
      "n": "Austrofil VERTEX POY/FDY",
      "spec": "Vertical module: basic set-up 3×8 = 24 ends, expandable to 32/48/64; 30 % less floor space than MT/HT 4×4; 2,000–4,500 m/min; PET, PP, PA6, 75–800 den; PET 270 or 540 kg/h; three winder types (including grooved roll, rotor)."
     }
    ]
   },
   {
    "name": "STC Spinnzwirn",
    "city": "Chemnitz",
    "owner": "private",
    "note": "Winders for replacement and modernisation, plus take-up machines with heated godets.",
    "models": [
     {
      "n": "RAPTOR CX1200",
      "spec": "Winder for replacement/modernisation; portfolio 800–5,000 m/min, 600 and 1,200 mm chucks, up to 8 ends per winder."
     },
     {
      "n": "babyASW604 / 906",
      "spec": "Compact high-speed winders (600 mm chuck) for smaller lines and speciality yarns."
     }
    ]
   },
   {
    "name": "Beijing Chonglee Machinery Engineering",
    "city": "Beijing",
    "owner": "China Textile Machinery (group)",
    "note": "Large Chinese supplier of POY, FDY and industrial-yarn plants and high-speed winders; widespread on the used market alongside TMT and Barmag.",
    "models": [
     {
      "n": "POY spinning plant (manual/automatic winder)",
      "spec": "Complete POY plants, as well as FDY, industrial yarn and differentiated yarns. Technical details hardly public (website currently offline)."
     },
     {
      "n": "BWA55T-1380",
      "spec": "Winder (FDY), switchable between 8 and 16 ends, 1,380 mm chuck, 50–150 den (listing, built 2012)."
     }
    ]
   },
   {
    "name": "Jwell Fiber Machinery",
    "city": "Suzhou / Shanghai",
    "owner": "Jwell Group (extrusion)",
    "note": "Complete PET/PA6/bicomponent plants, also CP direct spinning as turnkey; own JW winders.",
    "models": [
     {
      "n": "PET/PA6/bico POY plant",
      "spec": "30–330 dtex PES POY; cross-flow or radial quench; packs from above or below; process speed PET approx. 3,200 m/min, PA6 4,300 m/min; 6–12 positions per line (customer-specific)."
     },
     {
      "n": "JW high-speed winder",
      "spec": "1,800 mm chuck, 4,000 m/min, 12/18/20 packages (PET); cam and birotor versions."
     }
    ]
   },
   {
    "name": "Jiangsu TITA Intelligent Technology",
    "city": "Jiangsu",
    "owner": "private (since 2018)",
    "note": "POY, FDY and BCF spinning plants, winders, extruders, filters and quench.",
    "models": [
     {
      "n": "TWA winder",
      "spec": "Series TWA900G to TWA1800T, chuck lengths 900–1,800 mm."
     }
    ]
   },
   {
    "name": "Hi-Tech Heavy Industry (via ATE)",
    "city": "China; distribution ATE India",
    "owner": "–",
    "note": "POY/FDY lines for PES, PA and PP, distributed in India by ATE.",
    "models": [
     {
      "n": "ZWT winder (cam traverse)",
      "spec": "6–20 ends (POY up to 16), chuck up to 1,680 mm (POY), up to 4,800 m/min, full package up to 15 kg; POY 80–500 den."
     },
     {
      "n": "ZWB winder (birotor)",
      "spec": "10–20 ends, chuck up to 1,500 mm (FDY)."
     }
    ]
   },
   {
    "name": "Fourné Polymertechnik",
    "city": "Alfter",
    "owner": "private",
    "note": "Lab, pilot and special plants up to production size, plus cleaning systems for spinning parts.",
    "models": [
     {
      "n": "Lab and pilot spinning plants",
      "spec": "Small extruder lines for polymer and additive trials, mono- and multifilament."
     }
    ]
   },
   {
    "name": "Hills Inc.",
    "city": "West Melbourne, FL",
    "owner": "private",
    "note": "Specialist in bi- and tricomponent spinning technology (core/sheath, side-by-side, islands-in-the-sea) – from lab to production plant.",
    "models": [
     {
      "n": "Multicomponent filament plants",
      "spec": "POY/FOY/UOY as well as spunbond; etched spin pack plates for complex cross-sections."
     }
    ]
   }
  ],
  "chips": {
   "wings": "WINGS",
   "radial": "radial",
   "legacy": "historical",
   "retrofit": "Retrofit",
   "pa": "PA",
   "pes": "PES",
   "bico": "Bico",
   "lab": "Lab"
  },
  "tl": [
   "TMT Machinery is formed from Toray Engineering, Murata and Teijin Seiki.",
   "Barmag ACW with up to 1,600 mm chuck length; reference: 576 positions / 4,320 POY ends of direct spinning in China.",
   "Barmag WINGS (ITMA Munich): godets and interlacing in the winder.",
   "WINGS also for PA POY (20–150 den).",
   "WINGS POY 1800 with 12 or 16 ends; WINGS HOY. By then ~14,000 WINGS winders sold.",
   "WINGS POY XS (retrofit) and WinFors (reversing shaft) at ITMA Milan.",
   "WINGS POY HD for high titers up to 600d/576f.",
   "EvoQuench radial quench for PA POY for the first time (120 positions, China).",
   "Barmag POY 2.0 at ITMA Asia; SML launches VERTEX for PET.",
   "Rieter acquires Barmag (2 Feb.); WINGS POY 2.0 shown publicly at ITM Istanbul."
  ],
  "assess": [
   [
    "Barmag dominates the premium segment:",
    "WINGS (godets in the winder) has established itself as the standard since 2007; according to Barmag, around 14,000 WINGS winders had been sold by 2013. Barmag has belonged to Rieter since February 2026."
   ],
   [
    "TMT",
    "is the second major supplier with the ATi winder family (ORCA, MANTA); both companies each claim around 40 % share of the man-made-fibre machinery market (own figures, not defined on the same basis)."
   ],
   [
    "China:",
    "Beijing Chonglee, Jwell, TITA and Hi-Tech supply complete plants and winders for the huge domestic market; used-market listings regularly name Chonglee alongside TMT and Barmag."
   ],
   [
    "Niches:",
    "SML (AT) with compact vertical lines, STC Spinnzwirn (DE) for replacement and special winders, Fourné (DE) and Hills (US) for lab, pilot and bicomponent plants."
   ],
   [
    "Customers:",
    "POY production is highly concentrated in Chinese polyester groups (e.g. Tongkun, Hengyi, Xin Feng Ming), plus Reliance (IN) and Sasa (TR)."
   ],
   [
    "Trends:",
    "more ends per winder, radial quench for microfibres, automatic string-up (WINGS POY 2.0), less energy in the spin beam, dope dyeing, digitalisation (atmos.io)."
   ]
  ],
  "sources": [
   "Textile World – Barmag POY 2.0 (March 2026)",
   "texdata – POY 2.0, spin beam −10 % energy",
   "Barmag – WINGS now also for PA POY (2010)",
   "Textile World – WINGS POY 1800",
   "Barmag – WINGS family grows (1800/12 and 16, HOY)",
   "Fiber Journal – WINGS 1800, HD, XS, HOY",
   "Barmag – WINGS POY XS (retrofit)",
   "Textination – WINGS HD 1800 (600d/576f)",
   "Textile World – WinFors",
   "texdata – ACW 1600 (2004)",
   "Fiber Journal – EvoQuench radial quench",
   "Textile World – EvoQuench PA (120 positions)",
   "Barmag – FDY brochure 2025 (EvoQuench −80 % cooling air)",
   "Barmag Engineering – reference plants",
   "Textile World – Rieter acquires Barmag",
   "DirectIndustry – TMT ATi series",
   "DirectIndustry – TMT ATi-418R/12 ORCA",
   "DirectIndustry – TMT ATi-M",
   "DirectIndustry – TMT ATi-H",
   "Texmachines – TMT MANTA-618 (16 ends, 1,800 mm)",
   "Indian Textile Magazine – TMT background",
   "Texmachines – Chonglee BWA55T-1380",
   "Made-in-China – used market TMT/Chonglee/Barmag",
   "Jwell – catalogue of man-made-fibre spinning plants",
   "Jwell – high-speed winder 1,800 mm",
   "TITA – TWA winder",
   "ATE – POY/FDY lines (Hi-Tech Heavy Industry)",
   "SML – Austrofil VERTEX",
   "SML – VERTEX data sheet",
   "STC Spinnzwirn – winders (ITMA Asia 2025)",
   "Fourné – lab and pilot plants",
   "Hills Inc. – bicomponent spinning plants",
   "US 4318676 – number of ends per spinning position",
   "EP 2184386 – TMT, multi-storey spinning system",
   "DIResearch – POY producers"
  ]
 },
 "es": {
  "ui": {
   "eyebrow": "Knowledge Base · Hilatura",
   "h1": "Plantas de hilatura POY: fabricantes, diseños y variantes",
   "lead": "Vista interactiva de las plantas para hilo parcialmente orientado (POY), el hilo de alimentación de las máquinas DTY: desde el polímero, pasando por la viga de hilatura, el enfriamiento (quench) y los godets, hasta la bobinadora de alta velocidad. Todas las figuras son visualizaciones esquemáticas, no a escala.",
   "note": "Estado de la investigación: noviembre de 2026. Los datos de los fabricantes pueden variar según la versión.",
   "sources": "Fuentes",
   "component": "Componente",
   "tip": "Consejo: los interruptores de arriba cambian la alimentación de polímero, el enfriamiento, el estirado y la traversa.",
   "openFil": "→ Hilatura de filamento",
   "openFilHint": "Abrir módulo de la Knowledge Base",
   "examples": "Ejemplos",
   "pros": "Ventajas",
   "cons": "Desventajas",
   "search": "Buscar",
   "searchPh": "Modelo, fabricante, característica …",
   "region": "Región",
   "regions": [
    "Todas",
    "Europa",
    "Japón",
    "China",
    "EE. UU."
   ],
   "scope": "Alcance",
   "scopes": [
    "Todos",
    "Planta completa",
    "Bobinadora"
   ],
   "treeFilter": "Filtro del esquema de variantes:",
   "reset": "restablecer",
   "upTo": "hasta {n} cabos",
   "srcSite": "Fuente / web del fabricante: {d}",
   "empty": "No hay modelos para esta combinación de filtros.",
   "sortEnds": "Cabos por bobinadora",
   "sortChuck": "Longitud del portabobinas (mm)",
   "legend": [
    "Europa",
    "Japón",
    "China"
   ],
   "barsNote": "Valores máximos según el fabricante o el anuncio. Más cabos por bobinadora significa bobinas más pequeñas por cabo; para el procesamiento DTY, el peso de la bobina suele ser más importante que el número de cabos.",
   "assess": "Valoración",
   "treeHint": "Haga clic en una opción: la escena «Fabricantes y modelos» se abre filtrada. Otro clic quita el filtro."
  },
  "scenes": [
   {
    "k": "Proceso",
    "title": "Del polímero a la bobina POY",
    "text": "Las bombas de hilatura presionan el fundido a través de los paquetes de hilatura; los filamentos se enfrían, reciben el ensimaje y se recogen a 2 500–3 500 m/min (PES). La alta velocidad de recogida orienta parcialmente las cadenas moleculares; de ahí «partially oriented». Haga clic en un componente; los interruptores muestran las variantes principales."
   },
   {
    "k": "Esquema de variantes",
    "title": "Esquema de variantes",
    "text": "Las plantas POY se diferencian en pocos ejes. Haga clic en una opción para filtrar los fabricantes y modelos correspondientes."
   },
   {
    "k": "Disposiciones",
    "title": "Disposiciones de planta en sección",
    "text": "Las plantas de hilatura son edificios: la disposición de la planta de hilatura, el enfriamiento, los godets y la planta de bobinado determina la altura del edificio, la superficie de nave, el recorrido del hilo y el manejo."
   },
   {
    "k": "Fabricantes y modelos",
    "title": "Fabricantes y modelos",
    "text": "Fabricantes de plantas completas y de bobinadoras. Cifras de datos de fabricantes, prensa especializada y anuncios de maquinaria usada (véanse las fuentes)."
   },
   {
    "k": "Bobinadoras",
    "title": "Comparación de bobinadoras",
    "text": "Los cabos por bobinadora y la longitud del portabobinas determinan cuántas bobinas produce cada posición de hilatura y cuánta superficie de nave se necesita por cabo."
   },
   {
    "k": "Mercado",
    "title": "Estructura y evolución del mercado",
    "text": "Hitos importantes de los proveedores y una valoración del mercado."
   }
  ],
  "ctrl": {
   "lbl": [
    "Alimentación de polímero",
    "Enfriamiento",
    "Estirado / recogida",
    "Traversa"
   ],
   "opt": [
    [
     "Hilatura directa (CP)",
     "Chips + extrusora"
    ],
    [
     "Transversal",
     "Radial"
    ],
    [
     "Godets separados",
     "En la bobinadora (WINGS)",
     "Sin godets"
    ],
    [
     "Leva ranurada",
     "Rotor de aletas"
    ]
   ]
  },
  "proc": {
   "floorSpin": "Planta de hilatura",
   "floorShaft": "Conducto de caída",
   "floorGodet": "Plataforma de godets",
   "floorMid": "Entreplanta",
   "floorWind": "Planta de bobinado",
   "cp": "Reactores CP",
   "cpSub": "PTA + MEG → fundido",
   "chips": "Chips",
   "dryer": "Secador",
   "extr": "Extrusora + filtro de fundido",
   "beam": "Viga de hilatura (Dowtherm) · bomba · paquetes",
   "cross": "Transversal",
   "radial": "radial",
   "lessAir": "−60–80 % aire",
   "quench": "Enfriamiento",
   "oil": "Ensimaje",
   "windW": "Bobinadora WINGS (godets integrados)",
   "wind": "Bobinadora",
   "godets": "Godets",
   "noGodet": "sin recogida por godets",
   "jet": "Entrelazado",
   "rotor": "Traversa de rotor/aletas",
   "cam": "Traversa de leva ranurada",
   "emptyTube": "tubo vacío",
   "pkgs": "Bobinas (p. ej. 12 × 15 kg)",
   "take": "Recogida",
   "pes": "POY de PES",
   "speed": "≈ 2 500–3 500 m/min"
  },
  "comp": {
   "src": {
    "t": "Alimentación de polímero",
    "tags": [
     "Fundido"
    ],
    "cp": "Hilatura directa: el fundido llega directamente de la policondensación continua (CP, a partir de PTA + MEG) a las vigas de hilatura a través de tuberías calefactadas, bombas booster e intercambiadores de calor. La vía más económica para grandes volúmenes de PES; cientos de posiciones dependen de un solo reactor.",
    "chip": "Hilatura de chips: el granulado se seca, se funde en la extrusora y se distribuye mediante un filtro continuo de polímero (CPF). Más flexible (teñido en masa, bicomponente, PA, PP, PET reciclado), pero con más energía por kg.",
    "l": [
     "Hilatura directa: casi sin cambios de producto, capacidad muy alta",
     "Chips: lotes pequeños, colores, polímeros especiales"
    ]
   },
   "beam": {
    "t": "Viga de hilatura, bomba de hilatura y paquete de hilatura",
    "tags": [
     "Calefactada con Dowtherm"
    ],
    "p": "La viga de hilatura se calienta con vapor de Dowtherm y reparte el fundido de manera uniforme entre las posiciones. Bombas de engranajes dosifican cada cabo; en el paquete de hilatura el fundido se filtra (arena/velo metálico) y se presiona a través de la hilera.",
    "l": [
     "Barmag POY 2.0: paquete DIO más compacto, ⅓ menos arena filtrante, viga con hasta −10 % de energía",
     "Paquetes montados desde arriba o desde abajo (Jwell, entre otros)",
     "Varios cabos por posición: típicamente 8, 10, 12, 16 (disposición en zigzag con 16)"
    ]
   },
   "quench": {
    "t": "Enfriamiento (quench)",
    "tags": [
     "Solidificación de los filamentos"
    ],
    "cross": "Transversal: el aire de enfriamiento atraviesa la cortina de filamentos desde un lado; sencillo y robusto, estándar en muchas plantas.",
    "radial": "Radial: el aire fluye simétricamente de fuera hacia dentro a través del haz; más uniforme, ideal para microfibras (<1 dpf). Barmag EvoQuench necesita un 60–80 % menos de aire de proceso que el soplado transversal.",
    "l": [
     "Las condiciones de enfriamiento determinan los valores Uster y la orientación",
     "Teñido en masa: vigilar la vida útil del tamiz con enfriamiento radial"
    ]
   },
   "oil": {
    "t": "Ensimaje",
    "tags": [
     "Spin finish"
    ],
    "p": "Tras la solidificación se aplica el ensimaje mediante boquillas o rodillos de ensimaje: cohesión, propiedades de deslizamiento, antiestático. Después, el hilo baja por el conducto de caída hasta la recogida.",
    "l": [
     "Dosificación mediante bombas de ensimaje propias"
    ]
   },
   "godet": {
    "t": "Godets (recogida)",
    "tags": [
     "Velocidad",
     "Tensión"
    ],
    "sep": "Clásico: dos godets (normalmente sin calefacción) en una entreplanta o una plataforma sobre la bobinadora. Ajustan la velocidad de recogida y desacoplan la tensión de hilatura de la de bobinado.",
    "wings": "WINGS (Barmag): los godets y el chorro de entrelazado están integrados en la bobinadora; recorrido del hilo corto y recto, más de un 30 % menos de espacio, enhebrado más sencillo. Estándar del mercado desde 2007.",
    "none": "Sin godets: la bobinadora recoge directamente; económico, pero la tensión de bobinado depende directamente del proceso de hilatura. Más bien en líneas sencillas.",
    "l": []
   },
   "jet": {
    "t": "Chorro de entrelazado (preentrelazado)",
    "tags": [
     "Cohesión del hilo"
    ],
    "p": "Un chorro de aire delante de la bobinadora crea nudos de entrelazado para que el haz de POY se mantenga unido y corra de forma uniforme al desenrollarse en la texturización.",
    "l": [
     "En WINGS integrado en la bobinadora como «tangle unit»",
     "Número y estabilidad de los nudos mediante presión y geometría del chorro"
    ]
   },
   "wind": {
    "t": "Bobinadora de alta velocidad",
    "tags": [
     "Revólver",
     "Mudada automática"
    ],
    "p": "Bobinadora de revólver con dos portabobinas: cuando la bobina está llena, el revólver gira y el hilo pasa sin parar al tubo vacío. Típicamente 8–20 bobinas por portabobinas en 1 200–1 800 mm de longitud.",
    "l": [
     "Peso de bobina POY a menudo ~15 kg",
     "El enhebrado automático (WINGS POY 2.0) reduce el personal y los desperdicios",
     "Retirada de bobinas cada vez más automatizada (robots de mudada, logística de bobinas)"
    ]
   },
   "trav": {
    "t": "Traversa",
    "tags": [
     "Formación de la bobina"
    ],
    "cam": "Leva ranurada / rodillo ranurado: un guiahilos va y viene sobre un tambor de leva; robusto, probado, limitado mecánicamente a velocidades muy altas.",
    "rotor": "Rotor de aletas (birrotor): aletas que giran en sentido contrario se pasan el hilo; velocidades muy altas, típico en FDY y en bobinadoras POY modernas.",
    "l": [
     "Barmag WinFors: eje reversible para un depósito especialmente suave (2 500–4 000 m/min)"
    ]
   }
  },
  "dims": [
   {
    "t": "Producto / proceso",
    "o": [
     {
      "b": "POY de PES (estándar)",
      "s": "Alimentación para DTY; la mayor parte del volumen."
     },
     {
      "b": "POY de PA6/PA66",
      "s": "Para DTY de nailon (medias, deporte, lencería)."
     },
     {
      "b": "HOY",
      "s": "Hilo de PA altamente orientado, ~10 % más rápido que el POY de PA."
     },
     {
      "b": "Bicomponente",
      "s": "Núcleo/envoltura, lado a lado, islas en el mar."
     },
     {
      "b": "Título alto",
      "s": "Más de 300 den por cabo (p. ej. WINGS HD)."
     }
    ]
   },
   {
    "t": "Alimentación de polímero",
    "o": [
     {
      "b": "Hilatura directa desde CP",
      "s": "Fundido directamente de la policondensación."
     },
     {
      "b": "Chips + extrusora",
      "s": "Flexible: colores, PA, PP, rPET, bico."
     }
    ]
   },
   {
    "t": "Enfriamiento",
    "o": [
     {
      "b": "Transversal",
      "s": "Estándar, sencillo, robusto."
     },
     {
      "b": "Radial",
      "s": "Más uniforme, menos aire, microfibras."
     },
     {
      "b": "Apto para microfibra",
      "s": "Título de filamento < 1 dpf."
     }
    ]
   },
   {
    "t": "Recogida",
    "o": [
     {
      "b": "Godets en la bobinadora",
      "s": "Principio WINGS: recorrido corto, menos superficie."
     },
     {
      "b": "Godets separados",
      "s": "Clásico, en plataforma/entreplanta."
     },
     {
      "b": "Módulo vertical",
      "s": "Estiraje + bobinadora directamente bajo el cabezal de hilatura (SML VERTEX)."
     }
    ]
   },
   {
    "t": "Bobinadora y traversa",
    "o": [
     {
      "b": "Leva ranurada / rodillo ranurado",
      "s": "Mecánica, robusta."
     },
     {
      "b": "Rotor / birrotor",
      "s": "Velocidad muy alta."
     },
     {
      "b": "Eje reversible",
      "s": "Especialmente suave (WinFors)."
     },
     {
      "b": "Enhebrado automático",
      "s": "Por primera vez en WINGS POY 2.0."
     }
    ]
   },
   {
    "t": "Caso de uso",
    "o": [
     {
      "b": "Retrofit / modernización",
      "s": "Bobinadoras nuevas bajo vigas antiguas."
     },
     {
      "b": "Laboratorio / piloto",
      "s": "Desarrollo de polímeros y productos."
     },
     {
      "b": "Especial (elastano, industrial)",
      "s": "Bobinadoras y procesos distintos."
     }
    ]
   }
  ],
  "prof": {
   "conv": {
    "t": "Convencional, de varios pisos",
    "ex": [
     "Plantas Barmag antiguas (SW/CW/ACW)",
     "TMT ATi con godets",
     "Chonglee, Jwell, Hi-Tech"
    ],
    "d": "Viga de hilatura y enfriamiento en el piso superior; debajo, el conducto de caída a través del techo, los godets en una plataforma intermedia y las bobinadoras en el piso inferior. Probado y flexible, pero alto y con recorridos de hilo más largos.",
    "pro": [
     "Probado, muchos proveedores",
     "Godets elegibles independientemente de la bobinadora"
    ],
    "con": [
     "Gran altura de edificio, más volumen de nave",
     "Enhebrado laborioso a través de varios niveles"
    ]
   },
   "wings": {
    "t": "WINGS – godets en la bobinadora",
    "ex": [
     "Barmag WINGS POY 1800 / HD / 2.0",
     "WINGS XS como retrofit"
    ],
    "d": "Los godets y el chorro de entrelazado están integrados en la bobinadora. El hilo pasa del conducto de caída directamente a la unidad de bobinado; la plataforma de godets desaparece. Esto ahorra más de un 30 % de espacio y simplifica el enhebrado, automático por primera vez con POY 2.0.",
    "pro": [
     "Recorrido del hilo corto y recto",
     "Menos superficie y personal"
    ],
    "con": [
     "Dependencia de un proveedor (Barmag)",
     "La bobinadora se vuelve más compleja"
    ]
   },
   "vertex": {
    "t": "Módulo de línea vertical",
    "ex": [
     "SML Austrofil VERTEX 3×8 a 8×8"
    ],
    "d": "La unidad de estiraje y de bobinado se sitúa directamente bajo el cabezal de hilatura y el enfriamiento; cada línea es un módulo independiente. La capacidad crece con unidades de hilatura adicionales (24 → 32 → 48 → 64 cabos).",
    "pro": [
     "30 % menos superficie que SML MT/HT 4×4",
     "Ampliable paso a paso"
    ],
    "con": [
     "Líneas más pequeñas que las grandes plantas",
     "Más bien para chips/especialidades"
    ]
   },
   "lab": {
    "t": "Planta de laboratorio y piloto",
    "ex": [
     "Fourné",
     "Hills (bi-/tricomponente)",
     "SML/otras líneas piloto"
    ],
    "d": "Extrusoras pequeñas (a menudo varias para bicomponentes), una o pocas posiciones de hilatura, godets y una bobinadora compacta en un solo nivel. Para ensayos de polímeros y aditivos, nuevas secciones y pequeñas cantidades.",
    "pro": [
     "Ensayos rápidos, poco material",
     "Muchos polímeros y secciones"
    ],
    "con": [
     "No para volúmenes de producción",
     "Comprobar la transferibilidad a la planta grande"
    ]
   }
  },
  "psvg": {
   "floorSpin": "Planta de hilatura",
   "floorGodet": "Plataforma de godets",
   "beam": "Viga de hilatura",
   "quench": "Enfriamiento",
   "godets": "Godets",
   "wind": "Bobinadora",
   "wingsUnit": "Unidad WINGS",
   "wingsA": "Godets + entrelazado",
   "wingsB": "integrados en la bobinadora",
   "noStage": "sin plataforma de godets → más bajo",
   "module": "Módulo {i} · 8 cabos",
   "grows": "La línea crece por módulos: 3×8 = 24 → hasta 64 cabos",
   "extr": "Extrusoras A + B",
   "bico": "Cabezal bico",
   "compact": "Bobinadora compacta",
   "ss": "Lado a lado",
   "cs": "Núcleo/envoltura"
  },
  "mfr": [
   {
    "name": "Barmag (Oerlikon Barmag)",
    "city": "Remscheid / Chemnitz",
    "owner": "grupo Rieter desde 02/2026",
    "note": "Plantas completas desde la policondensación (CP) hasta la bobinadora. Inventor del principio WINGS: los godets y el entrelazado están directamente en la bobinadora.",
    "models": [
     {
      "n": "WINGS POY 2.0 (concepto POY 2.0)",
      "spec": "Presentada en ITMA Asia 2025: por primera vez enhebrado automático en la bobinadora, mayor carrera del rotor (tiempo de aparcamiento más largo), inversión activa de la traversa; además, paquete DIO más compacto (aprox. ⅓ menos arena filtrante), viga de hilatura revisada (hasta −10 % de energía) y EvoQuench 2.0."
     },
     {
      "n": "WINGS POY 1800",
      "spec": "Desde 2014: portabobinas de 1 800 mm con 12 cabos (estándar, +20 % frente a 1500/10) o 16 cabos (disposición en zigzag de los paquetes); PES 30–300 den final."
     },
     {
      "n": "WINGS POY HD",
      "spec": "Para títulos altos: godet adicional en la entrada del hilo, 12 bobinas hasta 600d/576f; tiempo de aparcamiento tres veces mayor. Combinación con eAFK Big V en la texturización."
     },
     {
      "n": "WINGS PA / HOY",
      "spec": "POY de PA 20–150 den final (PA66 hasta 100 den); HOY 30–150 den a hasta 5 200 m/min."
     },
     {
      "n": "WINGS POY XS",
      "spec": "Serie retrofit para plantas antiguas con bobinadoras SW, CW y ACW: cinco modelos con 8–12 cabos y 1 200–1 800 mm de longitud de portabobinas."
     },
     {
      "n": "WinFors",
      "spec": "Bobinadora con eje reversible para hilos delicados (microfilamentos, hilo madre, airbag); 2 500–4 000 m/min; convertible de 4 a 8 cabos."
     },
     {
      "n": "EvoQuench (enfriamiento radial)",
      "spec": "El aire fluye simétricamente de fuera hacia dentro a través del haz de filamentos; 60–80 % menos aire de proceso que el transversal; 0,3–3 dpf; desde 2019 también para PA."
     },
     {
      "n": "ACW / CW / SW (histórico)",
      "spec": "Bobinadoras clásicas con godets separados; ACW existía desde 2004 con hasta 1 600 mm de longitud de portabobinas."
     }
    ]
   },
   {
    "name": "TMT Machinery",
    "city": "Osaka / Kioto",
    "owner": "JV de Toray Engineering, Murata y Teijin Seiki (2002)",
    "note": "Procesos de hilatura y estirado para POY/FDY/IDY y la familia de bobinadoras ATi; know-how de Teijin Seiki, Toray Engineering y Murata.",
    "models": [
     {
      "n": "ATi-418R/12 «ORCA»",
      "spec": "Bobinadora POY con 12 cabos y bobinas de 15 kg; función para mejorar la calidad del hilo en la bobina."
     },
     {
      "n": "MANTA-618",
      "spec": "Modelo más reciente con 16 cabos en portabobinas de 1 800 mm (dato de un anuncio de maquinaria usada)."
     },
     {
      "n": "Serie ATi",
      "spec": "Bobinadoras automáticas de alta velocidad, 1 200–1 520 mm de longitud de portabobinas, traversa de rotor o de leva ranurada a elegir."
     },
     {
      "n": "ATi-M",
      "spec": "Concepto con gran número de cabos y gran volumen de bobina."
     },
     {
      "n": "ATi-H / ATi-459α",
      "spec": "ATi-H para hilo industrial (600–1 350 mm, 2–6 cabos); ATi-459α para elastano (spandex)."
     }
    ]
   },
   {
    "name": "SML Maschinengesellschaft",
    "city": "Redlham",
    "owner": "privada (especialista en extrusión)",
    "note": "Líneas de hilatura Austrofil; la serie VERTEX coloca el estiraje y la bobinadora directamente bajo el cabezal de hilatura y el enfriamiento.",
    "models": [
     {
      "n": "Austrofil VERTEX POY/FDY",
      "spec": "Módulo vertical: configuración básica 3×8 = 24 cabos, ampliable a 32/48/64; 30 % menos superficie que MT/HT 4×4; 2 000–4 500 m/min; PET, PP, PA6, 75–800 den; PET 270 o 540 kg/h; tres tipos de bobinadora (entre ellos rodillo ranurado y rotor)."
     }
    ]
   },
   {
    "name": "STC Spinnzwirn",
    "city": "Chemnitz",
    "owner": "privada",
    "note": "Bobinadoras para sustitución y modernización, además de máquinas de recogida con godets calefactados.",
    "models": [
     {
      "n": "RAPTOR CX1200",
      "spec": "Bobinadora para sustitución/modernización; gama 800–5 000 m/min, portabobinas de 600 y 1 200 mm, hasta 8 cabos por bobinadora."
     },
     {
      "n": "babyASW604 / 906",
      "spec": "Bobinadoras compactas de alta velocidad (portabobinas de 600 mm) para líneas pequeñas e hilos especiales."
     }
    ]
   },
   {
    "name": "Beijing Chonglee Machinery Engineering",
    "city": "Pekín",
    "owner": "China Textile Machinery (grupo)",
    "note": "Gran proveedor chino de plantas de POY, FDY e hilo industrial, así como de bobinadoras de alta velocidad; extendido en el mercado de segunda mano junto a TMT y Barmag.",
    "models": [
     {
      "n": "Planta de hilatura POY (bobinadora manual/automática)",
      "spec": "Plantas POY completas, así como FDY, hilo industrial e hilos diferenciados. Detalles técnicos apenas públicos (web actualmente fuera de línea)."
     },
     {
      "n": "BWA55T-1380",
      "spec": "Bobinadora (FDY), conmutable entre 8 y 16 cabos, portabobinas de 1 380 mm, 50–150 den (anuncio, fabricada en 2012)."
     }
    ]
   },
   {
    "name": "Jwell Fiber Machinery",
    "city": "Suzhou / Shanghái",
    "owner": "grupo Jwell (extrusión)",
    "note": "Plantas completas de PET/PA6/bicomponente, también hilatura directa CP llave en mano; bobinadoras JW propias.",
    "models": [
     {
      "n": "Planta POY PET/PA6/bico",
      "spec": "POY de PES 30–330 dtex; enfriamiento transversal o radial; paquetes desde arriba o desde abajo; velocidad de proceso PET aprox. 3 200 m/min, PA6 4 300 m/min; 6–12 posiciones por línea (según cliente)."
     },
     {
      "n": "Bobinadora de alta velocidad JW",
      "spec": "Portabobinas de 1 800 mm, 4 000 m/min, 12/18/20 bobinas (PET); versiones de leva ranurada y birrotor."
     }
    ]
   },
   {
    "name": "Jiangsu TITA Intelligent Technology",
    "city": "Jiangsu",
    "owner": "privada (desde 2018)",
    "note": "Plantas de hilatura POY, FDY y BCF, bobinadoras, extrusoras, filtros y enfriamiento.",
    "models": [
     {
      "n": "Bobinadora TWA",
      "spec": "Serie TWA900G a TWA1800T, longitudes de portabobinas de 900–1 800 mm."
     }
    ]
   },
   {
    "name": "Hi-Tech Heavy Industry (a través de ATE)",
    "city": "China; distribución ATE India",
    "owner": "–",
    "note": "Líneas POY/FDY para PES, PA y PP, distribuidas en la India por ATE.",
    "models": [
     {
      "n": "Bobinadora ZWT (leva ranurada)",
      "spec": "6–20 cabos (POY hasta 16), portabobinas hasta 1 680 mm (POY), hasta 4 800 m/min, bobina llena hasta 15 kg; POY 80–500 den."
     },
     {
      "n": "Bobinadora ZWB (birrotor)",
      "spec": "10–20 cabos, portabobinas hasta 1 500 mm (FDY)."
     }
    ]
   },
   {
    "name": "Fourné Polymertechnik",
    "city": "Alfter",
    "owner": "privada",
    "note": "Plantas de laboratorio, piloto y especiales hasta tamaño de producción, además de equipos de limpieza para piezas de hilatura.",
    "models": [
     {
      "n": "Plantas de hilatura de laboratorio y piloto",
      "spec": "Pequeñas líneas de extrusión para ensayos de polímeros y aditivos, mono- y multifilamento."
     }
    ]
   },
   {
    "name": "Hills Inc.",
    "city": "West Melbourne, FL",
    "owner": "privada",
    "note": "Especialista en tecnología de hilatura bi- y tricomponente (núcleo/envoltura, lado a lado, islas en el mar), del laboratorio a la planta de producción.",
    "models": [
     {
      "n": "Plantas de filamento multicomponente",
      "spec": "POY/FOY/UOY y spunbond; placas de paquete de hilatura grabadas para secciones complejas."
     }
    ]
   }
  ],
  "chips": {
   "wings": "WINGS",
   "radial": "radial",
   "legacy": "histórico",
   "retrofit": "Retrofit",
   "pa": "PA",
   "pes": "PES",
   "bico": "Bico",
   "lab": "Laboratorio"
  },
  "tl": [
   "Nace TMT Machinery a partir de Toray Engineering, Murata y Teijin Seiki.",
   "Barmag ACW con hasta 1 600 mm de longitud de portabobinas; referencia: 576 posiciones / 4 320 cabos POY de hilatura directa en China.",
   "Barmag WINGS (ITMA Múnich): godets y entrelazado en la bobinadora.",
   "WINGS también para POY de PA (20–150 den).",
   "WINGS POY 1800 con 12 o 16 cabos; WINGS HOY. Hasta entonces, ~14 000 bobinadoras WINGS vendidas.",
   "WINGS POY XS (retrofit) y WinFors (eje reversible) en ITMA Milán.",
   "WINGS POY HD para títulos altos hasta 600d/576f.",
   "Enfriamiento radial EvoQuench por primera vez para POY de PA (120 posiciones, China).",
   "Barmag POY 2.0 en ITMA Asia; SML lanza VERTEX para PET.",
   "Rieter adquiere Barmag (2 de feb.); WINGS POY 2.0 presentada públicamente en ITM Estambul."
  ],
  "assess": [
   [
    "Barmag domina el segmento premium:",
    "WINGS (godets en la bobinadora) se ha impuesto como estándar desde 2007; según Barmag, hasta 2013 se vendieron unas 14 000 bobinadoras WINGS. Desde febrero de 2026, Barmag pertenece a Rieter."
   ],
   [
    "TMT",
    "es el segundo gran proveedor con la familia de bobinadoras ATi (ORCA, MANTA); ambas empresas declaran cada una alrededor del 40 % del mercado de maquinaria para fibras químicas (datos propios, delimitados de forma distinta)."
   ],
   [
    "China:",
    "Beijing Chonglee, Jwell, TITA y Hi-Tech suministran plantas completas y bobinadoras para el enorme mercado interior; los anuncios de segunda mano mencionan con frecuencia Chonglee junto a TMT y Barmag."
   ],
   [
    "Nichos:",
    "SML (AT) con líneas verticales compactas, STC Spinnzwirn (DE) para bobinadoras de sustitución y especiales, Fourné (DE) y Hills (US) para plantas de laboratorio, piloto y bicomponente."
   ],
   [
    "Clientes:",
    "La producción de POY está muy concentrada en grupos chinos de poliéster (p. ej. Tongkun, Hengyi, Xin Feng Ming), además de Reliance (IN) y Sasa (TR)."
   ],
   [
    "Tendencias:",
    "más cabos por bobinadora, enfriamiento radial para microfibras, enhebrado automático (WINGS POY 2.0), menos energía en la viga de hilatura, teñido en masa, digitalización (atmos.io)."
   ]
  ],
  "sources": [
   "Textile World – Barmag POY 2.0 (marzo de 2026)",
   "texdata – POY 2.0, viga de hilatura −10 % de energía",
   "Barmag – WINGS ahora también para POY de PA (2010)",
   "Textile World – WINGS POY 1800",
   "Barmag – Crece la familia WINGS (1800/12 y 16, HOY)",
   "Fiber Journal – WINGS 1800, HD, XS, HOY",
   "Barmag – WINGS POY XS (retrofit)",
   "Textination – WINGS HD 1800 (600d/576f)",
   "Textile World – WinFors",
   "texdata – ACW 1600 (2004)",
   "Fiber Journal – Enfriamiento radial EvoQuench",
   "Textile World – EvoQuench PA (120 posiciones)",
   "Barmag – Folleto FDY 2025 (EvoQuench −80 % de aire de enfriamiento)",
   "Barmag Engineering – Plantas de referencia",
   "Textile World – Rieter adquiere Barmag",
   "DirectIndustry – Serie TMT ATi",
   "DirectIndustry – TMT ATi-418R/12 ORCA",
   "DirectIndustry – TMT ATi-M",
   "DirectIndustry – TMT ATi-H",
   "Texmachines – TMT MANTA-618 (16 cabos, 1 800 mm)",
   "Indian Textile Magazine – Antecedentes de TMT",
   "Texmachines – Chonglee BWA55T-1380",
   "Made-in-China – Mercado de segunda mano TMT/Chonglee/Barmag",
   "Jwell – Catálogo de plantas de hilatura de fibras químicas",
   "Jwell – Bobinadora de alta velocidad 1 800 mm",
   "TITA – Bobinadora TWA",
   "ATE – Líneas POY/FDY (Hi-Tech Heavy Industry)",
   "SML – Austrofil VERTEX",
   "SML – Ficha técnica VERTEX",
   "STC Spinnzwirn – Bobinadoras (ITMA Asia 2025)",
   "Fourné – Plantas de laboratorio y piloto",
   "Hills Inc. – Plantas de hilatura bicomponente",
   "US 4318676 – Número de cabos por posición de hilatura",
   "EP 2184386 – TMT, sistema de hilatura de varios pisos",
   "DIResearch – Productores de POY"
  ]
 },
 "zh": {
  "ui": {
   "eyebrow": "Knowledge Base · 纺丝",
   "h1": "POY 纺丝设备：制造商、结构形式与变型",
   "lead": "预取向丝（POY）设备的交互式概览——POY 是 DTY 加弹机的原丝：从聚合物经纺丝箱体、冷却吹风和导丝辊，一直到高速卷绕头。所有图示均为示意图，未按比例绘制。",
   "note": "资料截至 2026 年 11 月。制造商数据可能因配置不同而有所差异。",
   "sources": "资料来源",
   "component": "部件",
   "tip": "提示：上方的开关可切换聚合物供给、冷却吹风、牵伸卷取方式和横动方式。",
   "openFil": "→ 长丝纺丝",
   "openFilHint": "打开 Knowledge Base 模块",
   "examples": "示例",
   "pros": "优点",
   "cons": "缺点",
   "search": "搜索",
   "searchPh": "型号、制造商、特征 …",
   "region": "地区",
   "regions": [
    "全部",
    "欧洲",
    "日本",
    "中国",
    "美国"
   ],
   "scope": "范围",
   "scopes": [
    "全部",
    "整套设备",
    "卷绕头"
   ],
   "treeFilter": "来自变型图的筛选：",
   "reset": "重置",
   "upTo": "最多 {n} 头",
   "srcSite": "来源 / 制造商网站：{d}",
   "empty": "没有符合该筛选组合的型号。",
   "sortEnds": "每个卷绕头的头数",
   "sortChuck": "筒管长度（mm）",
   "legend": [
    "欧洲",
    "日本",
    "中国"
   ],
   "barsNote": "最大值依据制造商资料或广告。每个卷绕头的头数越多，每根丝的丝饼越小——对 DTY 后加工而言，丝饼重量往往比头数更重要。",
   "assess": "评述",
   "treeHint": "点击一个选项：“制造商与型号”场景将以筛选状态打开。再次点击即取消筛选。"
  },
  "scenes": [
   {
    "k": "工艺",
    "title": "从聚合物到 POY 丝饼",
    "text": "熔体经计量泵压过纺丝组件，长丝经冷却吹风、上油后以 2 500–3 500 m/min（涤纶）的速度卷取。高卷取速度使分子链部分取向——因此称为“partially oriented”（预取向）。点击一个部件；开关显示主要变型。"
   },
   {
    "k": "变型图",
    "title": "变型图",
    "text": "POY 设备的区别集中在少数几个维度上。点击一个选项，即可筛选相应的制造商和型号。"
   },
   {
    "k": "设备布局",
    "title": "设备布局剖面图",
    "text": "纺丝设备就是建筑物：纺丝层、冷却吹风、导丝辊和卷绕层的布置决定了厂房高度、厂房面积、丝路和操作方式。"
   },
   {
    "k": "制造商与型号",
    "title": "制造商与型号",
    "text": "整套设备和卷绕头制造商。数据来自制造商资料、专业媒体和二手设备广告（见资料来源）。"
   },
   {
    "k": "卷绕头比较",
    "title": "卷绕头比较",
    "text": "每个卷绕头的头数和筒管长度决定了每个纺丝位产出多少个丝饼，以及每根丝需要多少厂房面积。"
   },
   {
    "k": "市场",
    "title": "市场结构与发展",
    "text": "各供应商的重要里程碑以及对市场的评述。"
   }
  ],
  "ctrl": {
   "lbl": [
    "聚合物供给",
    "冷却吹风",
    "卷取",
    "横动"
   ],
   "opt": [
    [
     "熔体直纺（CP）",
     "切片 + 螺杆挤出机"
    ],
    [
     "侧吹风",
     "环吹风"
    ],
    [
     "独立导丝辊",
     "集成于卷绕头（WINGS）",
     "无导丝辊"
    ],
    [
     "凸轮槽筒",
     "拨叉/旋翼"
    ]
   ]
  },
  "proc": {
   "floorSpin": "纺丝层",
   "floorShaft": "甬道",
   "floorGodet": "导丝辊平台",
   "floorMid": "中间层",
   "floorWind": "卷绕层",
   "cp": "CP 反应釜",
   "cpSub": "PTA + MEG → 熔体",
   "chips": "切片",
   "dryer": "干燥机",
   "extr": "螺杆挤出机 + 熔体过滤器",
   "beam": "纺丝箱体（联苯）· 计量泵 · 组件",
   "cross": "侧吹风",
   "radial": "环吹风",
   "lessAir": "空气 −60–80 %",
   "quench": "冷却吹风",
   "oil": "上油",
   "windW": "WINGS 卷绕头（集成导丝辊）",
   "wind": "卷绕头",
   "godets": "导丝辊",
   "noGodet": "无导丝辊卷取",
   "jet": "网络",
   "rotor": "旋翼式横动",
   "cam": "槽筒横动",
   "emptyTube": "空筒管",
   "pkgs": "丝饼（如 12 × 15 kg）",
   "take": "卷取",
   "pes": "涤纶 POY",
   "speed": "≈ 2 500–3 500 m/min"
  },
  "comp": {
   "src": {
    "t": "聚合物供给",
    "tags": [
     "熔体"
    ],
    "cp": "熔体直纺：熔体直接来自连续缩聚（CP，由 PTA + MEG 制得），经保温管道、增压泵和换热器输送到纺丝箱体。这是大批量涤纶最经济的路线；数百个纺丝位由一个反应釜供料。",
    "chip": "切片纺：切片经干燥后在螺杆挤出机中熔融，并通过连续熔体过滤器（CPF）分配。更灵活（原液着色、双组分、锦纶、丙纶、再生涤纶），但每千克能耗更高。",
    "l": [
     "熔体直纺：几乎不换品种，产能极高",
     "切片纺：小批量、彩色、特种聚合物"
    ]
   },
   "beam": {
    "t": "纺丝箱体、计量泵与纺丝组件",
    "tags": [
     "联苯（Dowtherm）加热"
    ],
    "p": "纺丝箱体由联苯（Dowtherm）蒸汽加热，将熔体均匀分配到各纺丝位。齿轮计量泵为每根丝定量；熔体在纺丝组件中过滤（砂/金属毡）后从喷丝板挤出。",
    "l": [
     "Barmag POY 2.0：更紧凑的 DIO 组件，过滤砂减少 ⅓，箱体能耗最多降低 10 %",
     "组件从上方或下方安装（Jwell 等）",
     "每个纺丝位多根丝：通常 8、10、12、16（16 头时呈之字形排列）"
    ]
   },
   "quench": {
    "t": "冷却吹风（Quench）",
    "tags": [
     "长丝固化"
    ],
    "cross": "侧吹风：冷却空气从一侧吹过丝束——简单可靠，是许多设备的标准配置。",
    "radial": "环吹风：空气由外向内对称地穿过丝束；更均匀，非常适合超细纤维（<1 dpf）。Barmag EvoQuench 所需工艺空气比侧吹风少 60–80 %。",
    "l": [
     "冷却条件决定条干（Uster）值和取向",
     "原液着色：环吹风时注意滤网寿命"
    ]
   },
   "oil": {
    "t": "上油",
    "tags": [
     "纺丝油剂"
    ],
    "p": "固化后通过油嘴或油轮施加纺丝油剂：集束性、摩擦性能、抗静电。随后丝线经甬道向下到达卷取部分。",
    "l": [
     "由专用油剂泵计量"
    ]
   },
   "godet": {
    "t": "导丝辊（卷取）",
    "tags": [
     "速度",
     "张力"
    ],
    "sep": "传统方式：两个导丝辊（大多不加热）位于卷绕头上方的中间层或平台上。它们设定卷取速度，并使纺丝张力与卷绕张力分离。",
    "wings": "WINGS（Barmag）：导丝辊和网络喷嘴集成在卷绕头中——丝路短而直，节省 30 % 以上空间，生头更简单。2007 年起成为市场标准。",
    "none": "无导丝辊：由卷绕头直接卷取；成本低，但卷绕张力直接取决于纺丝过程。多用于简单生产线。",
    "l": []
   },
   "jet": {
    "t": "网络喷嘴（预网络）",
    "tags": [
     "丝束抱合"
    ],
    "p": "卷绕头前的空气喷嘴在丝上形成网络点，使 POY 丝束在加弹退绕时保持抱合并运行均匀。",
    "l": [
     "WINGS 中作为“tangle unit”集成在卷绕头内",
     "网络点数量和牢度由气压和喷嘴几何形状决定"
    ]
   },
   "wind": {
    "t": "高速卷绕头",
    "tags": [
     "转塔",
     "自动落筒"
    ],
    "p": "带两根卷绕夹头的转塔式卷绕头：丝饼卷满后转塔旋转，丝线不停机地切换到空筒管上。通常每根夹头 8–20 个丝饼，筒管长度 1 200–1 800 mm。",
    "l": [
     "POY 丝饼重量常为 ~15 kg",
     "自动生头（WINGS POY 2.0）减少人员需求和废丝",
     "丝饼运输日益自动化（落筒机器人、丝饼物流）"
    ]
   },
   "trav": {
    "t": "横动",
    "tags": [
     "卷装成形"
    ],
    "cam": "凸轮槽筒/槽辊：导丝器在槽筒上往复运动——坚固、成熟，但在极高速度下受机械限制。",
    "rotor": "拨叉/旋翼（双旋翼）：反向旋转的拨叶交替导丝——速度极高，常见于 FDY 和现代 POY 卷绕头。",
    "l": [
     "Barmag WinFors：往复轴实现特别轻柔的铺丝（2 500–4 000 m/min）"
    ]
   }
  },
  "dims": [
   {
    "t": "产品 / 工艺",
    "o": [
     {
      "b": "涤纶 POY（标准）",
      "s": "DTY 原丝；占产量的绝大部分。"
     },
     {
      "b": "PA6/PA66 POY",
      "s": "用于锦纶 DTY（袜类、运动、内衣）。"
     },
     {
      "b": "HOY",
      "s": "高取向锦纶丝，比锦纶 POY 快约 10 %。"
     },
     {
      "b": "双组分",
      "s": "皮芯型、并列型、海岛型。"
     },
     {
      "b": "高旦",
      "s": "每根丝 300 旦以上（如 WINGS HD）。"
     }
    ]
   },
   {
    "t": "聚合物供给",
    "o": [
     {
      "b": "CP 熔体直纺",
      "s": "熔体直接来自缩聚。"
     },
     {
      "b": "切片 + 螺杆挤出机",
      "s": "灵活：彩色、锦纶、丙纶、再生涤纶、双组分。"
     }
    ]
   },
   {
    "t": "冷却吹风",
    "o": [
     {
      "b": "侧吹风",
      "s": "标准、简单、可靠。"
     },
     {
      "b": "环吹风",
      "s": "更均匀、用气少、适合超细纤维。"
     },
     {
      "b": "可纺超细纤维",
      "s": "单丝纤度 < 1 dpf。"
     }
    ]
   },
   {
    "t": "卷取",
    "o": [
     {
      "b": "导丝辊集成于卷绕头",
      "s": "WINGS 原理：丝路短、占地少。"
     },
     {
      "b": "独立导丝辊",
      "s": "传统方式，位于平台/中间层。"
     },
     {
      "b": "垂直模块",
      "s": "牵伸单元 + 卷绕头直接位于纺丝头下方（SML VERTEX）。"
     }
    ]
   },
   {
    "t": "卷绕头与横动",
    "o": [
     {
      "b": "凸轮槽筒 / 槽辊",
      "s": "机械式、坚固。"
     },
     {
      "b": "旋翼 / 双旋翼",
      "s": "速度极高。"
     },
     {
      "b": "往复轴",
      "s": "特别轻柔（WinFors）。"
     },
     {
      "b": "自动生头",
      "s": "首次用于 WINGS POY 2.0。"
     }
    ]
   },
   {
    "t": "应用场景",
    "o": [
     {
      "b": "改造 / 现代化",
      "s": "在旧纺丝箱体下装新卷绕头。"
     },
     {
      "b": "实验室 / 中试",
      "s": "聚合物与产品开发。"
     },
     {
      "b": "特种（氨纶、工业丝）",
      "s": "不同的卷绕头和工艺。"
     }
    ]
   }
  ],
  "prof": {
   "conv": {
    "t": "传统多层式",
    "ex": [
     "较早的 Barmag 设备（SW/CW/ACW）",
     "带导丝辊的 TMT ATi",
     "Chonglee、Jwell、Hi-Tech"
    ],
    "d": "纺丝箱体和冷却吹风位于最高层，其下是穿过楼板的甬道，导丝辊位于中间平台，卷绕头位于最底层。成熟灵活，但厂房高、丝路较长。",
    "pro": [
     "成熟可靠，供应商众多",
     "导丝辊可独立于卷绕头选择"
    ],
    "con": [
     "厂房高，厂房体积大",
     "跨多层生头费事"
    ]
   },
   "wings": {
    "t": "WINGS——导丝辊集成于卷绕头",
    "ex": [
     "Barmag WINGS POY 1800 / HD / 2.0",
     "WINGS XS 改造方案"
    ],
    "d": "导丝辊和网络喷嘴集成在卷绕头中。丝线从甬道直接进入卷绕单元；不再需要导丝辊平台。这节省 30 % 以上空间并简化生头——POY 2.0 首次实现自动生头。",
    "pro": [
     "丝路短而直",
     "占地和人员更少"
    ],
    "con": [
     "绑定单一供应商（Barmag）",
     "卷绕头更复杂"
    ]
   },
   "vertex": {
    "t": "垂直生产线模块",
    "ex": [
     "SML Austrofil VERTEX 3×8 至 8×8"
    ],
    "d": "牵伸和卷绕单元直接位于纺丝头和冷却吹风下方；每条生产线都是独立模块。通过增加纺丝单元扩展产能（24 → 32 → 48 → 64 头）。",
    "pro": [
     "比 SML MT/HT 4×4 占地少 30 %",
     "可逐步扩展"
    ],
    "con": [
     "生产线规模小于大型设备",
     "更适合切片纺/特种产品"
    ]
   },
   "lab": {
    "t": "实验室与中试设备",
    "ex": [
     "Fourné",
     "Hills（双/三组分）",
     "SML/其他中试线"
    ],
    "d": "小型螺杆挤出机（双组分时常为多台）、一个到几个纺丝位、导丝辊和紧凑型卷绕头布置在同一层。用于聚合物和添加剂试验、新截面和小批量。",
    "pro": [
     "试验快、用料少",
     "可用多种聚合物和截面"
    ],
    "con": [
     "不适合量产",
     "需验证能否放大到大型设备"
    ]
   }
  },
  "psvg": {
   "floorSpin": "纺丝层",
   "floorGodet": "导丝辊平台",
   "beam": "纺丝箱体",
   "quench": "冷却吹风",
   "godets": "导丝辊",
   "wind": "卷绕头",
   "wingsUnit": "WINGS 单元",
   "wingsA": "导丝辊 + 网络",
   "wingsB": "集成在卷绕头内",
   "noStage": "无导丝辊平台 → 更低",
   "module": "模块 {i} · 8 头",
   "grows": "生产线模块化扩展：3×8 = 24 → 最多 64 头",
   "extr": "挤出机 A + B",
   "bico": "双组分纺丝头",
   "compact": "紧凑型卷绕头",
   "ss": "并列型",
   "cs": "皮芯型"
  },
  "mfr": [
   {
    "name": "Barmag (Oerlikon Barmag)",
    "city": "Remscheid / Chemnitz",
    "owner": "自 2026 年 2 月起属 Rieter 集团",
    "note": "从缩聚（CP）到卷绕头的整套设备。WINGS 原理的发明者：导丝辊和网络直接位于卷绕头内。",
    "models": [
     {
      "n": "WINGS POY 2.0（POY 2.0 概念）",
      "spec": "2025 年 ITMA Asia 首发：首次在卷绕头上实现自动生头，旋翼行程更大（停放时间更长），横动主动换向；此外还有更紧凑的 DIO 纺丝组件（过滤砂约减少 ⅓）、改进的纺丝箱体（能耗最多降低 10 %）和 EvoQuench 2.0。"
     },
     {
      "n": "WINGS POY 1800",
      "spec": "2014 年起：1 800 mm 筒管，12 头（标准，比 1500/10 多 20 %）或 16 头（纺丝组件之字形排列）；涤纶成品 30–300 旦。"
     },
     {
      "n": "WINGS POY HD",
      "spec": "用于高旦：丝线入口处增加一个导丝辊，12 个丝饼，最高 600d/576f；停放时间延长三倍。在加弹中与 eAFK Big V 配合使用。"
     },
     {
      "n": "WINGS PA / HOY",
      "spec": "锦纶 POY 成品 20–150 旦（PA66 最高 100 旦）；HOY 30–150 旦，速度最高 5 200 m/min。"
     },
     {
      "n": "WINGS POY XS",
      "spec": "针对配备 SW、CW 和 ACW 卷绕头的旧设备的改造系列：五种型号，8–12 头，筒管长度 1 200–1 800 mm。"
     },
     {
      "n": "WinFors",
      "spec": "带往复轴的卷绕头，用于敏感丝线（超细长丝、母丝、安全气囊丝）；2 500–4 000 m/min；可从 4 头改为 8 头。"
     },
     {
      "n": "EvoQuench（环吹风）",
      "spec": "空气由外向内对称地穿过丝束；工艺空气比侧吹风少 60–80 %；0.3–3 dpf；2019 年起也用于锦纶。"
     },
     {
      "n": "ACW / CW / SW（历史型号）",
      "spec": "带独立导丝辊的传统卷绕头；ACW 自 2004 年起提供，筒管长度最长 1 600 mm。"
     }
    ]
   },
   {
    "name": "TMT Machinery",
    "city": "大阪 / 京都",
    "owner": "Toray Engineering、Murata 与 Teijin Seiki 的合资企业（2002）",
    "note": "POY/FDY/IDY 纺丝与牵伸工艺以及 ATi 卷绕头系列；技术源自 Teijin Seiki、Toray Engineering 和 Murata。",
    "models": [
     {
      "n": "ATi-418R/12“ORCA”",
      "spec": "12 头 POY 卷绕头，丝饼 15 kg；具备改善丝饼内丝线质量的功能。"
     },
     {
      "n": "MANTA-618",
      "spec": "较新的型号，1 800 mm 筒管上 16 头（数据来自二手设备广告）。"
     },
     {
      "n": "ATi 系列",
      "spec": "自动高速卷绕头，筒管长度 1 200–1 520 mm，可选旋翼或槽筒横动。"
     },
     {
      "n": "ATi-M",
      "spec": "高头数、大卷装容量的概念。"
     },
     {
      "n": "ATi-H / ATi-459α",
      "spec": "ATi-H 用于工业丝（600–1 350 mm，2–6 头）；ATi-459α 用于氨纶（spandex）。"
     }
    ]
   },
   {
    "name": "SML Maschinengesellschaft",
    "city": "Redlham",
    "owner": "私营（挤出专家）",
    "note": "Austrofil 纺丝线；VERTEX 系列将牵伸单元和卷绕头直接布置在纺丝头和冷却吹风下方。",
    "models": [
     {
      "n": "Austrofil VERTEX POY/FDY",
      "spec": "垂直模块：基本配置 3×8 = 24 头，可扩展到 32/48/64；比 MT/HT 4×4 占地少 30 %；2 000–4 500 m/min；PET、PP、PA6，75–800 旦；PET 270 或 540 kg/h；三种卷绕头（包括槽辊式和旋翼式）。"
     }
    ]
   },
   {
    "name": "STC Spinnzwirn",
    "city": "Chemnitz",
    "owner": "私营",
    "note": "用于替换和现代化改造的卷绕头，以及带热辊的卷取机。",
    "models": [
     {
      "n": "RAPTOR CX1200",
      "spec": "用于替换/现代化改造的卷绕头；产品范围 800–5 000 m/min，600 和 1 200 mm 筒管，每个卷绕头最多 8 头。"
     },
     {
      "n": "babyASW604 / 906",
      "spec": "紧凑型高速卷绕头（600 mm 筒管），用于较小生产线和特种丝。"
     }
    ]
   },
   {
    "name": "Beijing Chonglee Machinery Engineering",
    "city": "北京",
    "owner": "China Textile Machinery（集团）",
    "note": "中国大型 POY、FDY 和工业丝设备以及高速卷绕头供应商；在二手市场上与 TMT 和 Barmag 一样常见。",
    "models": [
     {
      "n": "POY 纺丝设备（手动/自动卷绕头）",
      "spec": "整套 POY 设备，也包括 FDY、工业丝和差别化纤维。技术细节几乎不公开（网站目前无法访问）。"
     },
     {
      "n": "BWA55T-1380",
      "spec": "卷绕头（FDY），8 头或 16 头可切换，1 380 mm 筒管，50–150 旦（广告，2012 年制造）。"
     }
    ]
   },
   {
    "name": "Jwell Fiber Machinery",
    "city": "苏州 / 上海",
    "owner": "Jwell 集团（挤出）",
    "note": "PET/PA6/双组分整套设备，也提供交钥匙 CP 熔体直纺；自产 JW 卷绕头。",
    "models": [
     {
      "n": "PET/PA6/双组分 POY 设备",
      "spec": "30–330 dtex 涤纶 POY；侧吹风或环吹风；组件上装或下装；工艺速度 PET 约 3 200 m/min，PA6 4 300 m/min；每条线 6–12 个纺丝位（按客户定制）。"
     },
     {
      "n": "JW 高速卷绕头",
      "spec": "1 800 mm 筒管，4 000 m/min，12/18/20 个丝饼（PET）；有槽筒式和双旋翼式。"
     }
    ]
   },
   {
    "name": "Jiangsu TITA Intelligent Technology",
    "city": "江苏",
    "owner": "私营（2018 年起）",
    "note": "POY、FDY 和 BCF 纺丝设备、卷绕头、螺杆挤出机、过滤器和冷却吹风设备。",
    "models": [
     {
      "n": "TWA 卷绕头",
      "spec": "TWA900G 至 TWA1800T 系列，筒管长度 900–1 800 mm。"
     }
    ]
   },
   {
    "name": "Hi-Tech Heavy Industry（经 ATE）",
    "city": "中国；印度由 ATE 销售",
    "owner": "–",
    "note": "用于涤纶、锦纶和丙纶的 POY/FDY 生产线，在印度由 ATE 销售。",
    "models": [
     {
      "n": "ZWT 卷绕头（槽筒式）",
      "spec": "6–20 头（POY 最多 16 头），筒管最长 1 680 mm（POY），最高 4 800 m/min，满卷最重 15 kg；POY 80–500 旦。"
     },
     {
      "n": "ZWB 卷绕头（双旋翼）",
      "spec": "10–20 头，筒管最长 1 500 mm（FDY）。"
     }
    ]
   },
   {
    "name": "Fourné Polymertechnik",
    "city": "Alfter",
    "owner": "私营",
    "note": "从实验室、中试到生产规模的特种设备，以及纺丝部件清洗设备。",
    "models": [
     {
      "n": "实验室与中试纺丝设备",
      "spec": "用于聚合物和添加剂试验的小型挤出线，单丝和复丝。"
     }
    ]
   },
   {
    "name": "Hills Inc.",
    "city": "West Melbourne, FL",
    "owner": "私营",
    "note": "双组分和三组分纺丝技术专家（皮芯型、并列型、海岛型）——从实验室到生产设备。",
    "models": [
     {
      "n": "多组分长丝设备",
      "spec": "POY/FOY/UOY 以及纺粘；采用蚀刻纺丝组件板实现复杂截面。"
     }
    ]
   }
  ],
  "chips": {
   "wings": "WINGS",
   "radial": "环吹风",
   "legacy": "历史型号",
   "retrofit": "改造",
   "pa": "锦纶",
   "pes": "涤纶",
   "bico": "双组分",
   "lab": "实验室"
  },
  "tl": [
   "TMT Machinery 由 Toray Engineering、Murata 和 Teijin Seiki 合并成立。",
   "Barmag ACW 筒管长度最长 1 600 mm；参考项目：中国熔体直纺 576 个纺丝位 / 4 320 根 POY 丝。",
   "Barmag WINGS（慕尼黑 ITMA）：导丝辊和网络集成在卷绕头中。",
   "WINGS 也用于锦纶 POY（20–150 旦）。",
   "WINGS POY 1800，12 头或 16 头；WINGS HOY。截至当时已售出约 14 000 台 WINGS 卷绕头。",
   "WINGS POY XS（改造）和 WinFors（往复轴）亮相米兰 ITMA。",
   "WINGS POY HD 用于高旦，最高 600d/576f。",
   "EvoQuench 环吹风首次用于锦纶 POY（120 个纺丝位，中国）。",
   "Barmag POY 2.0 亮相 ITMA Asia；SML 推出用于 PET 的 VERTEX。",
   "Rieter 收购 Barmag（2 月 2 日）；WINGS POY 2.0 在伊斯坦布尔 ITM 公开展出。"
  ],
  "assess": [
   [
    "Barmag 主导高端市场：",
    "WINGS（导丝辊集成于卷绕头）自 2007 年起成为标准；据 Barmag 称，截至 2013 年已售出约 14 000 台 WINGS 卷绕头。自 2026 年 2 月起，Barmag 隶属 Rieter。"
   ],
   [
    "TMT",
    "凭借 ATi 卷绕头系列（ORCA、MANTA）成为第二大供应商；两家公司都声称各自约占化纤机械市场 40 % 的份额（自报数据，界定口径不同）。"
   ],
   [
    "中国：",
    "Beijing Chonglee、Jwell、TITA 和 Hi-Tech 为庞大的国内市场提供整套设备和卷绕头；二手市场广告中 Chonglee 常与 TMT 和 Barmag 并列出现。"
   ],
   [
    "细分市场：",
    "SML（奥地利）提供紧凑型垂直生产线，STC Spinnzwirn（德国）提供替换和特种卷绕头，Fourné（德国）和 Hills（美国）提供实验室、中试和双组分设备。"
   ],
   [
    "客户：",
    "POY 生产高度集中于中国涤纶企业（如桐昆、恒逸、新凤鸣），此外还有 Reliance（印度）和 Sasa（土耳其）。"
   ],
   [
    "趋势：",
    "每个卷绕头头数更多、超细纤维采用环吹风、自动生头（WINGS POY 2.0）、纺丝箱体能耗降低、原液着色、数字化（atmos.io）。"
   ]
  ],
  "sources": [
   "Textile World – Barmag POY 2.0（2026 年 3 月）",
   "texdata – POY 2.0，纺丝箱体能耗 −10 %",
   "Barmag – WINGS 现也用于锦纶 POY（2010）",
   "Textile World – WINGS POY 1800",
   "Barmag – WINGS 家族扩充（1800/12 和 16，HOY）",
   "Fiber Journal – WINGS 1800、HD、XS、HOY",
   "Barmag – WINGS POY XS（改造）",
   "Textination – WINGS HD 1800（600d/576f）",
   "Textile World – WinFors",
   "texdata – ACW 1600（2004）",
   "Fiber Journal – EvoQuench 环吹风",
   "Textile World – EvoQuench PA（120 个纺丝位）",
   "Barmag – FDY 手册 2025（EvoQuench 冷却空气 −80 %）",
   "Barmag Engineering – 参考项目",
   "Textile World – Rieter 收购 Barmag",
   "DirectIndustry – TMT ATi 系列",
   "DirectIndustry – TMT ATi-418R/12 ORCA",
   "DirectIndustry – TMT ATi-M",
   "DirectIndustry – TMT ATi-H",
   "Texmachines – TMT MANTA-618（16 头，1 800 mm）",
   "Indian Textile Magazine – TMT 背景",
   "Texmachines – Chonglee BWA55T-1380",
   "Made-in-China – 二手市场 TMT/Chonglee/Barmag",
   "Jwell – 化纤纺丝设备目录",
   "Jwell – 1 800 mm 高速卷绕头",
   "TITA – TWA 卷绕头",
   "ATE – POY/FDY 生产线（Hi-Tech Heavy Industry）",
   "SML – Austrofil VERTEX",
   "SML – VERTEX 数据表",
   "STC Spinnzwirn – 卷绕头（ITMA Asia 2025）",
   "Fourné – 实验室与中试设备",
   "Hills Inc. – 双组分纺丝设备",
   "US 4318676 – 每个纺丝位的头数",
   "EP 2184386 – TMT，多层纺丝系统",
   "DIResearch – POY 生产商"
  ]
 }
};
