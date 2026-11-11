window.TEXTS = {
 "de": {
  "ui": {
   "eyebrow": "Knowledge Base · Weben",
   "h1": "Schaft-, Jacquard- und Wilton-Weben: Maschinen, Hersteller, Schusseintrag",
   "lead": "Eine Webmaschine besteht im Kern aus zwei Systemen: der Fachbildung (Exzenter, Schaftmaschine oder Jacquardmaschine – sie entscheidet über die Musterfreiheit) und dem Schusseintrag (Schützen, Projektil, Greifer, Luft oder Wasser – er entscheidet über Tempo, Breite und Garnspektrum). Die Seite zeigt beide animiert, ordnet die Hersteller je Webart zu und erklärt, wo sich die Maschinen wirklich unterscheiden. Beim Wilton (Florteppich) kommen Ruten- und Doppelflortechnik dazu.",
   "note": "Stand der Recherche: November 2026. Herstellerangaben sind oft Werbe- oder Höchstwerte; Modellbezeichnungen und Kenndaten können sich ändern.",
   "sources": "Quellen",
   "open": "Modul öffnen",
   "loc": "de-CH",
   "prev": "◀ Schritt zurück",
   "next": "Schritt vor ▶",
   "play": "▶ Abspielen",
   "pause": "Pause",
   "st": {
    "h": "HERST.",
    "p": "PRESSE",
    "m": "LISTE"
   },
   "stLegend": "Beleg: HERST. = Herstellerangabe · PRESSE = Fachpresse/Lehrmaterial · LISTE = nur aus Marktstudien-Listen"
  },
  "scenes": [
   {
    "k": "Fachbildung",
    "title": "Schaft oder Jacquard: die Fachbildung bestimmt das Muster",
    "text": "Links sieht man, welche Kettfäden bei jedem Schuss gehoben werden, rechts das entstehende Gewebe. Mit Schäften hängen viele Kettfäden am selben Rahmen – das Muster wiederholt sich nach wenigen Fäden. Mit Jacquard wird jeder Kettfaden einzeln über eine Platine gesteuert."
   },
   {
    "k": "Schusseintrag",
    "title": "Die fünf Schusseintragsarten",
    "text": "Draufsicht auf das Webfach: Der Schuss (orange) wird quer durch die Kette (blau) eingetragen – vor dem zurückgeschwenkten Riet, also zwischen Riet und Warenkante. Danach schwingt das Riet nach vorne und schlägt den Schuss an die Warenkante an. Animation verlangsamt, Geschwindigkeiten nicht massstäblich – die Balken unten zeigen die realen Höchstwerte."
   },
   {
    "k": "Schaftweben",
    "title": "Schaftweben: Maschinen und Hersteller",
    "text": "Beim Schaftweben kombiniert der Weber eine Webmaschine (Greifer, Luft, Wasser oder Projektil) mit einer Fachbildung über Schäfte. Der Markt ist zweigeteilt: Webmaschinenbauer einerseits, Spezialisten für Schaftmaschinen und Exzenter andererseits – vor allem Stäubli."
   },
   {
    "k": "Jacquardweben",
    "title": "Jacquardweben: Maschinen und Hersteller",
    "text": "Die Jacquardmaschine sitzt über der Webmaschine; jede Platine hebt über ein Harnisch-Schnürchen einen oder mehrere Kettfäden. Die Platinenzahl bestimmt, wie viele Fäden pro Rapport individuell gesteuert werden. Die Webmaschine darunter ist meist eine Greifer- oder Luftdüsenmaschine."
   },
   {
    "k": "Wilton-Weben",
    "title": "Wilton-Weben: Rute, Doppelflor, Axminster",
    "text": "Wilton bezeichnet gewebte Florteppiche, bei denen der Polfaden durchgehend im Grundgewebe mitläuft und gesteuert an die Oberfläche geholt wird. Klassisch geschieht das über Ruten (Drähte), heute überwiegend im Doppelflor- (Face-to-Face-)Verfahren. Axminster ist zum Vergleich dabei."
   },
   {
    "k": "Unterschiede",
    "title": "Signifikante Unterschiede zwischen den Maschinen",
    "text": "Was die Hersteller technisch unterschiedlich lösen – und was das für Garn, Artikel und Kosten bedeutet."
   },
   {
    "k": "Hersteller-Matrix",
    "title": "Hersteller-Matrix",
    "text": "Welcher Hersteller welche Eintragsart, Fachbildung und Teppichtechnik anbietet – laut den Quellen dieser Seite."
   }
  ],
  "kpis": [
   [
    "1 350",
    "Schuss/min auf schmalen Picanol-OmniPlus-i-Luftdüsenmaschinen"
   ],
   [
    "31 104",
    "Platinen in einer einzigen Bonas-Si-Jacquardmaschine"
   ],
   [
    "1 570 m/min",
    "Schusseintragsleistung der Projektilmaschine P7300HP"
   ],
   [
    "5,3 m",
    "Webbreite der Stäubli-/Schönherr-Teppichwebmaschine ALPHA 500"
   ],
   [
    "bis 6×",
    "Ausstoss einer Doppelflor-Maschine (Van de Wiele UCL83) gegenüber Rutenwebmaschine"
   ]
  ],
  "fach": {
   "seg": {
    "ex": "Exzenter (4 Schäfte)",
    "sch": "Schaftmaschine (8 Schäfte)",
    "jac": "Jacquard (jeder Faden einzeln)"
   },
   "svg": {
    "weaveCap": "Gewebebild: blau = Kette oben, orange = Schuss oben",
    "shafts4": "4 Schäfte – Exzenter: feste Folge",
    "shafts8": "8 Schäfte – Schaftmaschine: frei programmierbar, aber Faden e hängt an Schaft e mod 8",
    "jacHead": "Jacquardmaschine – eine Platine pro Faden",
    "jacCap": "Harnisch-Schnürchen: gehoben (orange) oder unten (grau) – Schuss für Schuss frei",
    "pick": "Schuss {n} von {total}"
   },
   "cards": {
    "ex": [
     [
      "Prinzip",
      "Kurvenscheiben (Exzenter) bewegen wenige Schäfte in einer fest eingebauten Folge."
     ],
     [
      "Grenze",
      "Nur einfache, kurze Bindungen (Leinwand, Köper); ein Musterwechsel heisst Exzenter tauschen."
     ],
     [
      "Wo",
      "Massenartikel auf schnellen Luft- und Wasserdüsenmaschinen; Stäubli-Exzenter S1691/92, S1792."
     ]
    ],
    "sch": [
     [
      "Prinzip",
      "Eine Schaftmaschine hebt jeden Schaft frei programmierbar – heute elektronisch gesteuert."
     ],
     [
      "Grenze",
      "Alle Kettfäden eines Schafts machen dasselbe. Mehr als etwa 24 Schäfte werden zu tief gestaffelt; der Rapport bleibt klein."
     ],
     [
      "Wo",
      "Hemden, Bettwäsche, Denim, technische Gewebe; z. B. Stäubli S3000/S3200, Picanol SmartShed."
     ]
    ],
    "jac": [
     [
      "Prinzip",
      "Jede Platine steuert einen Kettfaden (oder wenige) einzeln – hunderte bis über 30 000 unabhängige Gruppen."
     ],
     [
      "Grenze",
      "Teurer, höher bauender Harnisch, mehr Einrichtzeit; dafür beliebige Figuren über die ganze Breite."
     ],
     [
      "Wo",
      "Möbelstoffe, Damast, Etiketten, Frottier mit Motiv, OPW-Airbags, Teppiche."
     ]
    ]
   }
  },
  "ins": {
   "lbl": {
    "how": "So funktioniert es",
    "figs": "Kennzahlen",
    "pro": "Vorteile",
    "con": "Nachteile",
    "when": "Wann wählen?",
    "mk": "Hersteller und Modelle",
    "zoom": "Lupe: Übergabe in der Fachmitte (stark vergrössert, verlangsamt)",
    "cmpT": "Vergleich auf einen Blick",
    "cmpN": "Qualitative Einordnung von 1 (schwach) bis 5 (stark), abgeleitet aus den Quellen dieser Seite – keine Messwerte. Bei „Energie“ und „Kante/Abfall“ heisst 5: wenig Verbrauch bzw. wenig Abfall. Zeile anklicken öffnet das System.",
    "ituL": "Lehrbuchwerte (ITU-Vorlesung, Stand 1980er-Jahre)",
    "ituN": "Ältere Werte, die die Grössenordnungen zeigen; heutige Maschinen sind schneller (siehe Balken unten).",
    "spL": "Höchstgeschwindigkeiten aus den Quellen (Schuss/min bzw. U/min)",
    "spN": "Werte stammen aus unterschiedlichen Quellen und Bedingungen (Werbe-Höchstwert, Industriegeschwindigkeit, Webbreite). Wasserdüse: nur aus einer Studentenpräsentation (Toyota LWT810) – nicht geprüft. Die Projektilmaschine wird üblicherweise in m/min angegeben; der Balken rechnet 1 570 m/min auf 3,9 m Breite um."
   },
   "head": [
    "Hersteller",
    "Land",
    "Modelle",
    "Merkmal",
    "Beleg"
   ],
   "sys": [
    {
     "n": "Schützen",
     "de": "Historisch: Ein Schiffchen mit Schussspule fliegt hin und her",
     "pro": [
      "Echte, geschlossene Webkante – der Faden läuft von der mitfliegenden Spule ab.",
      "Einfache, robuste Mechanik."
     ],
     "con": [
      "Schwerer Schützen (rund 450 g bei Baumwollschuss) – begrenzt Tempo und Breite.",
      "Schuss wird nur in einem Bruchteil des Maschinenzyklus eingetragen.",
      "Lärm bis etwa 110 dB.",
      "Ständiger Spulenwechsel, Garn muss auf Kopse umgespult werden."
     ],
     "when": "Nur noch Nischen, in denen die echte Schützenkante gewollt ist.",
     "how": [
      "Der Schützen trägt eine Schussspule (Kops) im Inneren.",
      "Ein Schlagmechanismus schlägt ihn durchs Fach; drüben wird er abgebremst und fürs nächste Mal zurückgeschlagen.",
      "Der Faden läuft von der mitfliegenden Spule ab – es entsteht eine echte, geschlossene Webkante.",
      "Grosse bewegte Masse begrenzt die Drehzahl; Spulen müssen ständig gewechselt werden."
     ],
     "figs": [
      [
       "≈ 140",
       "Schuss/min der ersten (Schützen-)Webmaschine laut Picanol"
      ],
      [
       "1924",
       "Toyoda Type G: Schützenwechsel ohne Anhalten"
      ]
     ],
     "mk": [
      [
       "(historisch) Toyoda, Picanol u. v. a.",
       "–",
       "Schützenwebmaschinen",
       "heute nur noch Nischen; im klassischen Wilton wurde der Schuss mit Schützen eingetragen"
      ]
     ],
     "note": "Alle heutigen Industrieverfahren sind „schützenlos“: Der Schuss wird von einer stehenden Vorratsspule abgezogen."
    },
    {
     "n": "Projektil",
     "de": "Greiferprojektil: kleiner Stahlgreifer, der den Faden durchs Fach schiesst",
     "pro": [
      "Niedriger Energiebedarf.",
      "Sehr breit (bis 655 cm) – auch mehrere Bahnen nebeneinander.",
      "Kleines Projektil, kleines Fach: weniger Kettfadenbrüche.",
      "Breites Garnspektrum von Baumwolle über Wolle und Jute bis Bändchen; 4–6 Schussfarben."
     ],
     "con": [
      "Einlegekante: beidseitig bleiben rund 15 mm Schussende, die eingelegt werden – Abfall und dickere Kante.",
      "Tiefere Drehzahl als Luftdüse (Lehrbuch 250–400 U/min).",
      "Aufwendige Mechanik mit Projektilrücklauf; nur noch ein Anbieter."
     ],
     "when": "Breite technische Gewebe, Bändchengarne, Geo-/Agrotextil, Teppichrücken.",
     "how": [
      "Ein kleines Projektil (Greiferschützen) klemmt das Fadenende von der stehenden Vorratsspule.",
      "Ein Torsionsstab-Schlag schiesst es durch eine Führungsbahn quer durchs Fach.",
      "Drüben wird es abgebremst, öffnet sich und gibt den Faden frei.",
      "Ein Förderband bringt mehrere Projektile unter der Kette zurück; mehrere Projektile sind gleichzeitig im Umlauf."
     ],
     "figs": [
      [
       "1 570 m/min",
       "max. Schusseintragsleistung P7300HP"
      ],
      [
       "655 cm",
       "max. Webbreite P7300HP V8"
      ],
      [
       "> 150 000",
       "verkaufte Sulzer-Projektilmaschinen (Herstellerangabe 2002)"
      ],
      [
       "tief",
       "Energiebedarf – Stärke bei breiten technischen Geweben"
      ]
     ],
     "mk": [
      [
       "Itema (ex Sulzer Textil)",
       "IT/CH",
       "P7300HP",
       "einziger Projektilhersteller; Produktion 2026 von Zuchwil nach Colzate verlegt"
      ]
     ],
     "note": "Für Bändchengarne (Agro-, Geotextil, Teppichrücken) sieht Itema das Projektil gegenüber allen anderen Eintragsarten vorne."
    },
    {
     "n": "Greifer",
     "de": "Rapier: Stangen oder Bänder bringen den Schuss mechanisch durchs Fach",
     "pro": [
      "Grösstes Artikelspektrum, laut Lehrmaterial von etwa 20 bis 850 g/m².",
      "Viele Schussfarben und Effektgarne; der Faden wird mechanisch geführt, unabhängig von seiner Oberfläche.",
      "Positive Übergabe schont Glas, Carbon, Aramid.",
      "Doppelschuss möglich."
     ],
     "con": [
      "Langsamer als Luft- und Wasserdüse.",
      "Starre Greifer brauchen seitlich mindestens die doppelte Gewebebreite an Platz; flexible Bänder reiben an Führungen und verschleissen.",
      "Bei negativer Übergabe kann der Schuss in der Fachmitte verloren gehen."
     ],
     "when": "Mode mit vielen Farben, Heimtextilien, Jacquard-Möbelstoffe, Frottier, schwere technische Gewebe.",
     "v": [
      "Doppelgreifer, negative Übergabe",
      "Doppelgreifer, positive Übergabe (Dornier)",
      "Einzelgreifer"
     ],
     "how": [
      "Der Bringergreifer fasst das Fadenende an der Webkante und fährt bis zur Fachmitte.",
      "Dort übernimmt der Nehmergreifer den Faden (Dewas: Spitze an Spitze; Gabler: Schlaufe) und zieht ihn zur Gegenseite.",
      "Negativ: Die Übergabe geschieht nur über Fadenspannung und Klemmkraft. Positiv: Klemmen werden mechanisch gesteuert geöffnet – schonend für heikle Garne.",
      "Flexible Bänder werden auf Räder gewickelt (wenig Platz), starre Stangen brauchen Platz neben der Maschine, führen aber ohne Kontakt zur Kette."
     ],
     "figs": [
      [
       "> 800",
       "Schuss/min industriell, Picanol Ultimax"
      ],
      [
       "> 130 000",
       "verkaufte Picanol-Greifermaschinen"
      ],
      [
       "bis 6 200 mm",
       "Webbreite Itema Hercules"
      ],
      [
       "320 / 1 085 m/min",
       "Dornier P2, Segeltuch bei 339 cm"
      ]
     ],
     "mk": [
      [
       "Picanol",
       "BE",
       "Ultimax, OptiMax-i Connect, GTMax, Supermax",
       "Hochleistung; OptiMax-i bis 540 cm für Technik"
      ],
      [
       "Itema",
       "IT",
       "R9500-2, Hercules, Galileo",
       "geführte SK-Greifer; Hercules positiv/negativ umrüstbar"
      ],
      [
       "Lindauer Dornier",
       "DE",
       "P2",
       "starre Greifer, positive Mittenübergabe; Glas, Carbon, Aramid"
      ],
      [
       "SMIT (Santex Rimar)",
       "IT",
       "GS980, 2FAST, ONE",
       "„Free Flight“: Greifer ohne Führungshaken im Fach; ONE mit nur einem Greifer"
      ],
      [
       "RIFA · Jingwei · Tongda · Huasense u. a.",
       "CN",
       "–",
       "in Marktstudien als Greifer-/Webmaschinenhersteller"
      ]
     ],
     "note": "Laut Picanol laufen Greifermaschinen für Sari-Gewebe in Surat bei rund 410 U/min – die „über 800“ sind ein Höchstwert für geeignete Artikel."
    },
    {
     "n": "Luftdüse",
     "de": "Air-Jet: Druckluft trägt den Schuss durch einen Kanal im Profilriet",
     "pro": [
      "Höchste Eintragsleistung, kaum bewegte Massen.",
      "Geringe Anschaffungskosten, wenig Platzbedarf.",
      "Einfache Bedienung."
     ],
     "con": [
      "Druckluft ist teuer; die Stafettendüsen brauchen bis 80 % davon.",
      "Verlangt gleichmässige, gute Garne. Typische Fehler: Fehlschuss, aufgestauchte Fadenspitze, Doppelschuss.",
      "Bei grosser Breite wird der Faden haarig, die Spitze dreht sich auf (v. a. OE-Garn).",
      "Gewebedeckung laut Lehrmaterial nicht ganz so gut wie bei Projektil und Greifer."
     ],
     "when": "Standardgewebe in grossen Mengen: Hemden, Bettwäsche, Denim, Frottier, Airbag.",
     "how": [
      "Eine Hauptdüse beschleunigt den Schuss vom Vorspeicher in den Kanal des Profilriets.",
      "Stafettendüsen entlang der Breite blasen gruppenweise nach – sie halten den Faden in Bewegung.",
      "Am Ende streckt eine Saug- oder Streckdüse den Faden; die Kante wird abgeschnitten.",
      "Sehr schnell und einfach, aber Druckluft ist teuer: die Stafettendüsen verbrauchen bis 80 % der Luft."
     ],
     "figs": [
      [
       "1 350",
       "U/min, schmale Picanol OmniPlus-i Connect"
      ],
      [
       "−20 %",
       "Luftverbrauch Toyota JAT910 gegenüber JAT810"
      ],
      [
       "bis 80 %",
       "Luftanteil der Stafettendüsen"
      ],
      [
       "−1,5 kW",
       "pro Maschine mit Picanol EcoBoost"
      ]
     ],
     "mk": [
      [
       "Picanol",
       "BE",
       "OmniPlus-i Connect, TerryPlus-i Connect",
       "AirStream (+100 U/min), EcoBoost, SmartShed"
      ],
      [
       "Toyota Industries",
       "JP",
       "JAT910",
       "i-SENSOR erkennt den Schuss im Fach, E-shed"
      ],
      [
       "Tsudakoma",
       "JP",
       "ZAX001neo, ZAX9200i",
       "Luft- und Wasserdüse aus einer Hand"
      ],
      [
       "Itema",
       "IT",
       "A9500-2",
       "für motorisierte Jacquard ohne Kardanwelle vorbereitet"
      ],
      [
       "Lindauer Dornier",
       "DE",
       "A2",
       "Luftdüse für Technik (Airbag, Fallschirm)"
      ],
      [
       "RIFA · Jingwei · Tianyi Red Flag u. a.",
       "CN",
       "–",
       "Marktstudien"
      ]
     ],
     "note": "China war 2025 grösster Käufer von Luft- und Wasserdüsenmaschinen; die Auslieferungen dorthin sanken um 32 % bzw. 57 % (ITMF)."
    },
    {
     "n": "Wasserdüse",
     "de": "Water-Jet: ein Wasserstrahl reisst den Schuss durchs Fach",
     "pro": [
      "Hohe Eintragsleistung bei Filamentgarnen.",
      "Geringer Energieverbrauch, leise, wenig Vibration, kaum Schussabfall.",
      "Schont die Kette – kein Metallteil reibt."
     ],
     "con": [
      "Nur wasserabweisende Filamente (PES, PA, Acetat, Glas) – keine Baumwolle, Wolle, Viskose.",
      "Die Ware kommt nass von der Maschine und muss getrocknet werden; das Abwasser muss aufbereitet werden.",
      "Nur bis zwei Schussfarben; geringere Breite.",
      "Hartes Wasser kann Rost verursachen."
     ],
     "when": "Synthetische Filamentgewebe in Masse, vor allem in Ostasien.",
     "how": [
      "Eine Pumpe stösst bei jedem Schuss eine kleine Wassermenge durch die Düse.",
      "Wasser hat mehr Reibung am Faden als Luft – eine Düse genügt, keine Stafettendüsen.",
      "Die Ware wird nass und muss getrocknet werden; das Wasser muss aufbereitet werden.",
      "Nur für nicht saugende Synthesegarne (PES, PA) – Baumwolle oder Viskose gehen nicht."
     ],
     "figs": [
      [
       "8–5 600 dtex",
       "Garnspektrum Tsudakoma Wasserdüse (PA bis PES)"
      ],
      [
       "≈ 1 200",
       "U/min Toyota LWT810 (nicht geprüft)"
      ],
      [
       "−57 %",
       "Auslieferungen nach China 2025 (ITMF)"
      ]
     ],
     "mk": [
      [
       "Tsudakoma",
       "JP",
       "ZW8100, ZW8200",
       "breites Garnspektrum, auch Doppelgewebe"
      ],
      [
       "Toyota Industries",
       "JP",
       "LWT810",
       "Wasserdüse für Synthetics"
      ],
      [
       "Chinesische Hersteller",
       "CN",
       "–",
       "grösster Teil des Weltmarkts (Marktstudien)"
      ]
     ],
     "note": "Eine Marktstudie nennt die Wasserdüse als häufigste Webmaschine nach Stückzahl (über 47 %) – eine Folge der chinesischen Synthetik-Weberei."
    }
   ],
   "svg": {
    "prestore": "Vorspeicher",
    "strike": "Schlag",
    "brake": "Bremse",
    "ret": "Rücktransport der Projektile unter der Kette",
    "single": "ein einzelner Greifer fährt leer hinüber und zieht den Faden zurück",
    "handPos": "Übergabe: Klemmen gesteuert geöffnet",
    "handNeg": "Übergabe: Faden wird herausgezogen",
    "bringer": "Bringer",
    "taker": "Nehmer",
    "mainJet": "Hauptdüse",
    "relay": "Stafettendüsen blasen gruppenweise, nur wo der Faden gerade ist",
    "waterJet": "Wasserdüse",
    "beat": "Anschlag: Riet schiebt den Schuss an die Warenkante",
    "insertion": "Schusseintrag",
    "fabric": "Gewebe",
    "reed": "Riet",
    "back": "↑ hinten:",
    "shafts": "Schäfte",
    "front": "↓ vorne:",
    "cloth": "Ware"
   },
   "steps": [
    "1 · Fach offen, Riet hinten – Eintrag beginnt",
    "2 · Schuss unterwegs",
    "3 · Fachmitte (Greifer: Übergabe)",
    "4 · Schuss unterwegs zur Gegenseite",
    "5 · Eintrag fertig",
    "6 · Riet schwingt nach vorne",
    "7 · Anschlag an der Warenkante",
    "8 · Riet zurück, Fachwechsel"
   ],
   "zoom": {
    "msg": [
     "1 · Bringer bringt den Faden, Nehmer kommt entgegen",
     "2 · Greiferköpfe überlappen, Nehmerklemme schliesst sich um den Faden",
     "3 · Positiv: Öffner hebt die Bringerklemme – der Faden wird freigegeben",
     "3 · Negativ: Bringerklemme bleibt zu – der Nehmer zieht den Faden gegen die Federkraft heraus",
     "4 · Nehmer trägt den Schuss zur Gegenseite, Bringer fährt leer zurück"
    ],
    "spring": "Feder",
    "opener": "Klemmenöffner",
    "pull": "Zug am Faden",
    "step": "Schritt {n} von 4",
    "pos": "Positiv (z. B. Dornier P2, starre Greifer): Die Klemmen werden zu festen Zeitpunkten mechanisch geöffnet und geschlossen. Der Faden wird nicht herausgezogen, sondern übergeben – schonend für Glas, Carbon, Aramid und Effektgarne.",
    "neg": "Negativ (fast alle flexiblen Bandgreifer): Es gibt keinen Öffner. Der Faden wird nur über Fadenspannung und Klemmkraft vom Bringer zum Nehmer gezogen – einfach und schnell, aber glatte, steife oder empfindliche Garne können verloren gehen oder reissen."
   },
   "heatHead": [
    "System",
    "Eintragsleistung",
    "Max. Breite",
    "Garnspektrum",
    "Schussfarben",
    "Energie (5 = wenig)",
    "Kante/Abfall (5 = wenig)"
   ],
   "ituHead": [
    "System",
    "Arbeitsbreite (m)",
    "Drehzahl (U/min)",
    "Eintragsleistung (m/min)"
   ],
   "itu": [
    [
     "Schützen",
     "1,88–4,14",
     "60–160",
     "357–525"
    ],
    [
     "Projektil",
     "1,90–5,45",
     "250–400",
     "600–1 250"
    ],
    [
     "Greifer starr",
     "1,60–4,00",
     "200–420",
     "bis 1 100–1 300 (Zweiphasen)"
    ],
    [
     "Greifer flexibel",
     "1,80–4,20",
     "200–500",
     "550–1 150"
    ],
    [
     "Luftdüse",
     "1,40–3,60",
     "400–700",
     "650–1 600"
    ],
    [
     "Wasserdüse",
     "1,50–2,30",
     "800",
     "1 000–1 700"
    ]
   ],
   "speeds": [
    "Schützen (erste Maschine)",
    "Projektil P7300HP (1 570 m/min ÷ 3,9 m)",
    "Greifer Picanol Ultimax (industriell)",
    "Wasserdüse Toyota LWT810 (ungeprüft)",
    "Luftdüse Picanol OmniPlus-i (schmal)"
   ]
  },
  "schaft": {
   "titles": [
    "Schaftmaschinen & Exzenter",
    "Integrierte, elektronische Fachbildung",
    "Webmaschinen (Auswahl)"
   ],
   "cards": [
    [
     [
      "Stäubli S3000 / S3200 (Rotationsschaftmaschine)",
      "Elektronisch gesteuert, unten oder oben an Wasser-, Luft- und Greifermaschinen; > 20 000 Stück im Einsatz (2017). Stäubli hat das Rotationsprinzip erfunden."
     ],
     [
      "Stäubli S3292",
      "Neue Hochgeschwindigkeits-Schaftmaschine, Vorstellung an der ITME India 2026."
     ],
     [
      "Stäubli S2688 / S4080",
      "Offenfach-Schaftmaschinen für schwere technische Gewebe und Teppichgrund."
     ],
     [
      "Stäubli Exzenter S1691/92, S1792",
      "Für einfache Bindungen auf Hochleistungsmaschinen."
     ]
    ],
    [
     [
      "Picanol SmartShed / SmartShed Pro",
      "Jeder Schaft hat einen eigenen Servomotor (8, 12 oder 16 Schäfte); 8–16 Servoachsen von Lenze, flüssigkeitsgekühlt. Bindungswechsel ohne Mechanikumbau."
     ],
     [
      "Toyota E-shed / C-shed",
      "Eigene elektronische Fachbildung seit 2000, an der JAT910 angeboten."
     ],
     [
      "Dornier SyncroDrive",
      "Fachbildung mit eigenem Motor (6–8 kW), elektronisch statt über Kardanwelle mit der Webmaschine gekoppelt – keine Anlaufstellen."
     ]
    ],
    [
     [
      "Greifer",
      "Picanol Ultimax/GTMax · Itema R9500-2/Hercules · Dornier P2 · SMIT GS980/2FAST · chinesische Anbieter"
     ],
     [
      "Luftdüse",
      "Picanol OmniPlus-i · Toyota JAT910 · Tsudakoma ZAX · Itema A9500-2 · Dornier A2"
     ],
     [
      "Wasserdüse",
      "Tsudakoma ZW · Toyota LWT810 · viele chinesische Anbieter"
     ],
     [
      "Projektil",
      "Itema P7300HP (einziger Anbieter)"
     ]
    ]
   ]
  },
  "jac": {
   "hkL": "Platinenzahl je Maschine (Herstellerangaben, logarithmische Skala)",
   "hk": [
    "Stäubli UNIVALETTE",
    "GITEC Grosse (EJP/EJT)",
    "Bonas Ji",
    "Bonas Si",
    "Stäubli SX (Beispiel)"
   ],
   "hkNote": "Bonas Ji: obere Grenze laut Vandewiele 17 280, laut Messebericht 5 760",
   "head": [
    "Hersteller",
    "Sitz",
    "Modelle",
    "Technik / Besonderheit",
    "Beleg"
   ],
   "rows": [
    [
     "Stäubli",
     "CH-Konzern, u. a. Stäubli Bayreuth (DE)",
     "LX PRO, LXL PRO, LXXL PRO, SX PRO, N4L, UNIVALETTE; Harnische",
     "MX-PRO-Wählmodule, Doppelhub-Offenfach; CX 860 (1987) laut Stäubli erste elektronische Jacquard; UNIVALETTE mit eigenem, elektronisch synchronisiertem Antrieb"
    ],
    [
     "Bonas (Vandewiele-Gruppe)",
     "BE (Marke/Kortrijk)",
     "Si, Ji, H3D, MDA02",
     "100 % elektronischer Mikro-Selektor mit Volldiagnose; Si ist sehr kompakt (12–36 Messer tief); H3D für 3D- und Mehrlagengewebe"
    ],
    [
     "GITEC Grosse (Hisun-Gruppe)",
     "DE (Ulm) / CN",
     "EJP-4, EJT-4 (Frottier), UniShed 2",
     "gegründet 1878 in Greiz; UniShed: harnischlos, je Kettfaden eine Blattfeder – für Airbags"
    ],
    [
     "Webmaschinen für Jacquard",
     "–",
     "Picanol (Kardan oder eigenständig), Itema A9500-2/R9500-2, Dornier P2/A2 mit SyncroDrive, SMIT GS980 (Jumbo-Jacquard), Vandewiele Samt (VSi)",
     "Jacquard entweder über Kardanwelle oder mit eigenem Motor angetrieben – siehe Unterschiede"
    ]
   ],
   "note": "Widerspruch in den Quellen: Bonas nennt die Lancierung der elektronischen Jacquardmaschine an der ITMA Mailand 1983; Stäubli bezeichnet seine CX 860 von 1987 als weltweit erste elektronisch gesteuerte Jacquardmaschine. Auch die Platinenzahl der Bonas Ji wird unterschiedlich angegeben (bis 5 760 bzw. bis 17 280)."
  },
  "wil": {
   "seg": [
    "Rutenwilton",
    "Doppelflor (Face-to-Face)",
    "Axminster"
   ],
   "cards": {
    "rute": [
     [
      "Prinzip",
      "Polfäden laufen über Stahlruten, die quer eingeschoben werden. Beim Herausziehen schneidet eine Klinge am Rutenende die Schlinge auf (Wilton, Schnittflor) – ohne Klinge bleibt Schlinge (Brüssel)."
     ],
     [
      "Farbe",
      "Nicht benötigte Polfarben liegen „tot“ im Grundgewebe – teurer, aber sehr dicht. Je Noppe meist 1 aus 5 Farben."
     ],
     [
      "Schuss",
      "Klassisch mit Schützen; die Rutenhöhe begrenzt die Florhöhe und die Geschwindigkeit."
     ]
    ],
    "f2f": [
     [
      "Prinzip",
      "Zwei Grundgewebe übereinander, der Polfaden pendelt dazwischen. Ein Messer trennt in der Mitte – zwei Teppiche auf einmal."
     ],
     [
      "Schuss",
      "Doppelgreifer (je ein Greifer pro Grundgewebe) oder Dreigreifer: Der mittlere trägt einen Hilfsschuss ein, um den sich Schlingen legen, und wird wieder entfernt."
     ],
     [
      "Leistung",
      "Bis 250 U/min (Vandewiele RCF), Breiten bis 5,2–5,3 m; gegenüber Ruten ein Mehrfaches an Ausstoss."
     ]
    ],
    "axm": [
     [
      "Prinzip",
      "Jede Noppe wird einzeln geschnitten und eingesetzt – Greifer (schnabelartig) oder Spulenkette."
     ],
     [
      "Farbe",
      "Der ganze Pol liegt an der Oberfläche; Spulen-Axminster erlaubt praktisch unbegrenzt viele Farben, Greifer-Axminster etwa 1 aus 8."
     ],
     [
      "Maschine",
      "Vandewiele MAX91: Hochgeschwindigkeit, 16 Farbrahmen."
     ]
    ]
   },
   "svg": {
    "ground": "Grundgewebe (Kette + Schuss)",
    "cutMsg": "Rute wird seitlich gezogen – Klinge schneidet die Schlingen",
    "cutPile": "← geschnittener Flor (Wilton)",
    "loops": "Schlingen über Ruten (Querschnitt) →",
    "knife": "Schneidmesser trennt die beiden Teppiche",
    "upper": "oberer Teppich (Rücken oben), Schuss vom oberen Greifer",
    "lower": "unterer Teppich, Schuss vom unteren Greifer",
    "twoCarpets": "← zwei fertige Florteppiche",
    "pendulum": "Polfaden pendelt zwischen den Grundgeweben →",
    "grip1": "Greifer setzt die geschnittene",
    "grip2": "Noppe in den Grund",
    "each": "jede Noppe einzeln, ganzer Pol an der Oberfläche – kein toter Pol im Rücken"
   },
   "step": "ein Schritt = ¼ Florreihe",
   "head": [
    "Hersteller",
    "Verfahren",
    "Modelle",
    "Kennwerte / Besonderheit",
    "Beleg"
   ],
   "rows": [
    [
     "Vandewiele (Van de Wiele)",
     "Doppelflor, Doppelgreifer",
     "RCF, RCE2+, SRE2+",
     "RCF bis 250 U/min, 3/4/5 m, Fast Creel mit stehenden Spulen; RCE2+ bis 5,2 m; SRE2+ Shaggy bis 2×70 mm, auch Kunstrasen"
    ],
    [
     "Vandewiele",
     "Doppelflor, Dreigreifer",
     "USF, UCE3+, HCE3+, RCE3+",
     "Schnitt-, Schlingen- und Flachgewebe-Effekte gleichzeitig; HCE3+ imitiert handgeknüpfte Teppiche, Flor ab 3,5 mm"
    ],
    [
     "Vandewiele",
     "Einfachflor, Doppelgreifer",
     "LCE2+",
     "kurze/lange Schlingen, Flachgewebe, Sisal-Optik"
    ],
    [
     "Vandewiele",
     "Rutenwilton",
     "AWE1+",
     "Schlinge und/oder Schnitt, 2,20 / 2,70 / 4 m"
    ],
    [
     "Vandewiele",
     "Axminster",
     "MAX91",
     "16 Farbrahmen, Hochgeschwindigkeit"
    ],
    [
     "Stäubli (Schönherr)",
     "Doppelflor",
     "ALPHA 500/560 UNIVERSAL, XHDC",
     "bis 5,3 m, echte 3-Positionen-Jacquard (Stäubli), Servo-Schneidvorrichtung, Flüssigkühlung; gebaut in Bayreuth und Chemnitz"
    ],
    [
     "Stäubli (Schönherr)",
     "Einfachflor Schlinge",
     "ALPHA 500 SINGLELOOP",
     "laut Stäubli dreimal produktiver als Rutenwebmaschine"
    ],
    [
     "Stäubli (Schönherr)",
     "Ein- oder Doppelgreifer",
     "ALPHA 500 LEANTEC",
     "Shaggy, Kunstrasen, Rohware für Druck"
    ],
    [
     "Picanol",
     "Flachteppich",
     "Ultimax (Flat carpet, ITMA 2023)",
     "Greifermaschine für flachgewebte Teppiche, kein Flor"
    ]
   ],
   "note": "Ein Hersteller-Vergleich der Produktivität ist mit Vorsicht zu lesen: Van de Wiele nennt für die Dreigreifer-Maschine UCL83 bis zum Sechsfachen einer Rutenwebmaschine, Stäubli für die ALPHA 500 SINGLELOOP das Dreifache – es sind unterschiedliche Maschinen und Artikel."
  },
  "diff": {
   "follow": "Folge:",
   "cards": [
    [
     "Greifer: positive vs. negative Übergabe",
     "Dornier übergibt mit starren Greifern positiv – die Klemmen werden mechanisch geöffnet. Fast alle anderen nutzen flexible Bänder mit negativer Übergabe. Itema (Hercules) kann zwischen beiden umgerüstet werden.",
     "Positiv: schonend für Glas, Carbon, Aramid, Effektgarne. Negativ: schneller, einfacher."
    ],
    [
     "Greifer: geführt vs. „Free Flight“",
     "Itema setzt auf geführte SK-Greifer mit Haken im Fach; SMIT wirbt mit dem schnellsten Free-Flight-Greifer, der ohne Führungshaken auskommt.",
     "Free Flight schont empfindliche Ketten (Seide, Kammgarn); Führung erlaubt höhere Sicherheit bei hohem Tempo."
    ],
    [
     "Luftdüse: Kampf um die Druckluft",
     "Stafettendüsen fressen bis 80 % der Luft. Toyota senkt beim JAT910 Druck um 10 % und Verbrauch um 20 %; Picanol bringt AirStream (+100 U/min) und EcoBoost (−1,5 kW).",
     "Bei Luftdüsen entscheiden die Energiekosten oft mehr als der Kaufpreis."
    ],
    [
     "Projektil: die Breitwebmaschine",
     "Nur Itema baut noch Projektilmaschinen. Sie sind breit (bis 655 cm), sparsam und robust für Bändchengarne.",
     "Für Geo-/Agrotextil und Teppichrücken; für Mode kaum noch relevant."
    ],
    [
     "Wasserdüse: nur Synthetics",
     "Wasser zieht den Faden wirksamer als Luft, aber nasse Ware und Wasseraufbereitung; Cellulosefasern scheiden aus.",
     "Asiatische PES/PA-Massenware – fast nur Japan und China als Hersteller."
    ],
    [
     "Fachbildung: mechanisch gekoppelt vs. eigener Antrieb",
     "Klassisch treibt die Webmaschine Schaft- oder Jacquardmaschine über eine Kardanwelle. Picanol SmartShed (Servo je Schaft), Dornier SyncroDrive, Itemas motorisierte Jacquard ohne Kardan und Stäubli UNIVALETTE entkoppeln das elektronisch.",
     "Weniger Anlaufstellen, schnellere Bindungswechsel, Jacquard kann sanft auslaufen."
    ],
    [
     "Jacquard: Wähltechnik",
     "Bonas wählt mit einem 100 % elektronischen Mikro-Selektor (Volldiagnose), Stäubli mit MX-PRO-Modulen. Grosse UniShed verzichtet auf den Harnisch ganz: je Kettfaden eine Blattfeder.",
     "UniShed für Airbag-Gewebe; Bonas Si für sehr hohe Platinenzahlen in kleinem Bauraum."
    ],
    [
     "Teppich: Rute vs. Doppelflor",
     "Rutenwilton macht einen Teppich, braucht Ruten und ist langsam. Doppelflor macht zwei Teppiche gleichzeitig mit zwei oder drei Greifern.",
     "Doppelflor dominiert heute; Rute bleibt für bestimmte Schlingen-/Schnitt-Qualitäten (Vandewiele AWE1+)."
    ]
   ]
  },
  "mx": {
   "legend": [
    "in den Quellen belegt",
    "nur aus Marktstudien-Listen",
    "Leere Felder bedeuten „hier nicht belegt“."
   ],
   "head": [
    "Hersteller",
    "Land"
   ],
   "cols": [
    "Greifer",
    "Luft",
    "Wasser",
    "Projektil",
    "Schaft/Exzenter",
    "Jacquardmaschine",
    "Teppich Doppelflor",
    "Rutenwilton",
    "Axminster"
   ],
   "firms": [
    "Picanol",
    "Itema",
    "Lindauer Dornier",
    "Toyota Industries",
    "Tsudakoma",
    "SMIT (Santex Rimar)",
    "Stäubli (inkl. Schönherr)",
    "Vandewiele / Bonas",
    "GITEC Grosse",
    "RIFA",
    "Jingwei · Haijia · Tongda · Huasense"
   ],
   "lkL": "Weiter in der Knowledge Base",
   "links": [
    [
     "Schaftweben",
     "Webgeschirr, Einzug und Schaftprogramm: wie die Schäfte die Bindung machen."
    ],
    [
     "Bindungslehre",
     "Patrone, Leinwand, Köper und Atlas – und selbst eine Bindung zeichnen."
    ],
    [
     "Jacquardweben",
     "Jeder Kettfaden einzeln gehoben: wie eine Jacquardmaschine Muster webt."
    ],
    [
     "Wilton-Teppich",
     "Gewebter Polteppich: Ruten, Schnitt- und Schlingenflor, Farbwahl per Jacquard."
    ]
   ]
  }
 },
 "en": {
  "ui": {
   "eyebrow": "Knowledge Base · Weaving",
   "h1": "Shaft, Jacquard and Wilton weaving: machines, manufacturers, weft insertion",
   "lead": "At its core a weaving machine consists of two systems: shed formation (cam, dobby or Jacquard machine – it decides the pattern freedom) and weft insertion (shuttle, projectile, rapier, air or water – it decides speed, width and yarn range). This page shows both animated, assigns the manufacturers to each type of weaving and explains where the machines really differ. For Wilton (pile carpet), wire and face-to-face technology are added.",
   "note": "Research status: November 2026. Manufacturer figures are often advertising or maximum values; model names and specifications may change.",
   "sources": "Sources",
   "open": "Open module",
   "loc": "en-US",
   "prev": "◀ Step back",
   "next": "Step forward ▶",
   "play": "▶ Play",
   "pause": "Pause",
   "st": {
    "h": "MFR.",
    "p": "PRESS",
    "m": "LIST"
   },
   "stLegend": "Evidence: MFR. = manufacturer information · PRESS = trade press/teaching material · LIST = from market study lists only"
  },
  "scenes": [
   {
    "k": "Shed formation",
    "title": "Shaft or Jacquard: shed formation decides the pattern",
    "text": "On the left you see which warp threads are lifted for each pick, on the right the resulting fabric. With shafts, many warp threads hang on the same frame – the pattern repeats after a few threads. With Jacquard, every warp thread is controlled individually by a hook."
   },
   {
    "k": "Weft insertion",
    "title": "The five weft insertion systems",
    "text": "Top view of the shed: the weft (orange) is inserted across the warp (blue) – in front of the reed swung back, i.e. between reed and fell. Then the reed swings forward and beats the weft up against the fell. Animation slowed down, speeds not to scale – the bars below show the real maximum values."
   },
   {
    "k": "Shaft weaving",
    "title": "Shaft weaving: machines and manufacturers",
    "text": "In shaft weaving the weaver combines a weaving machine (rapier, air, water or projectile) with shed formation by shafts. The market is split in two: weaving machine builders on one side, specialists for dobbies and cams on the other – above all Stäubli."
   },
   {
    "k": "Jacquard weaving",
    "title": "Jacquard weaving: machines and manufacturers",
    "text": "The Jacquard machine sits above the weaving machine; each hook lifts one or more warp threads via a harness cord. The number of hooks decides how many threads per repeat are controlled individually. The weaving machine below is usually a rapier or air-jet machine."
   },
   {
    "k": "Wilton weaving",
    "title": "Wilton weaving: wire, face-to-face, Axminster",
    "text": "Wilton means woven pile carpets in which the pile yarn runs continuously in the ground fabric and is brought to the surface in a controlled way. Classically this is done with wires (rods), today mostly in the face-to-face (double pile) process. Axminster is included for comparison."
   },
   {
    "k": "Differences",
    "title": "Significant differences between the machines",
    "text": "What the manufacturers solve differently in technical terms – and what that means for yarn, article and cost."
   },
   {
    "k": "Manufacturer matrix",
    "title": "Manufacturer matrix",
    "text": "Which manufacturer offers which insertion system, shed formation and carpet technology – according to the sources of this page."
   }
  ],
  "kpis": [
   [
    "1,350",
    "picks/min on narrow Picanol OmniPlus-i air-jet machines"
   ],
   [
    "31,104",
    "hooks in a single Bonas Si Jacquard machine"
   ],
   [
    "1,570 m/min",
    "weft insertion rate of the P7300HP projectile machine"
   ],
   [
    "5.3 m",
    "weaving width of the Stäubli/Schönherr ALPHA 500 carpet weaving machine"
   ],
   [
    "up to 6×",
    "output of a face-to-face machine (Van de Wiele UCL83) compared with a wire loom"
   ]
  ],
  "fach": {
   "seg": {
    "ex": "Cam (4 shafts)",
    "sch": "Dobby (8 shafts)",
    "jac": "Jacquard (every thread on its own)"
   },
   "svg": {
    "weaveCap": "Fabric: blue = warp on top, orange = weft on top",
    "shafts4": "4 shafts – cam: fixed sequence",
    "shafts8": "8 shafts – dobby: freely programmable, but thread e hangs on shaft e mod 8",
    "jacHead": "Jacquard machine – one hook per thread",
    "jacCap": "Harness cords: lifted (orange) or down (grey) – free pick by pick",
    "pick": "Pick {n} of {total}"
   },
   "cards": {
    "ex": [
     [
      "Principle",
      "Cam discs (tappets) move a few shafts in a fixed, built-in sequence."
     ],
     [
      "Limit",
      "Only simple, short weaves (plain, twill); changing the pattern means changing the cams."
     ],
     [
      "Where",
      "Mass articles on fast air-jet and water-jet machines; Stäubli cams S1691/92, S1792."
     ]
    ],
    "sch": [
     [
      "Principle",
      "A dobby lifts each shaft freely programmable – today electronically controlled."
     ],
     [
      "Limit",
      "All warp threads of one shaft do the same. More than about 24 shafts become too deeply staggered; the repeat stays small."
     ],
     [
      "Where",
      "Shirts, bed linen, denim, technical fabrics; e.g. Stäubli S3000/S3200, Picanol SmartShed."
     ]
    ],
    "jac": [
     [
      "Principle",
      "Each hook controls one warp thread (or a few) individually – hundreds up to more than 30,000 independent groups."
     ],
     [
      "Limit",
      "More expensive, taller harness, more set-up time; in return any figure across the full width."
     ],
     [
      "Where",
      "Upholstery fabrics, damask, labels, terry with motif, OPW airbags, carpets."
     ]
    ]
   }
  },
  "ins": {
   "lbl": {
    "how": "How it works",
    "figs": "Key figures",
    "pro": "Advantages",
    "con": "Disadvantages",
    "when": "When to choose?",
    "mk": "Manufacturers and models",
    "zoom": "Magnifier: transfer in the middle of the shed (strongly enlarged, slowed down)",
    "cmpT": "Comparison at a glance",
    "cmpN": "Qualitative rating from 1 (weak) to 5 (strong), derived from the sources of this page – not measured values. For “Energy” and “Selvedge/waste”, 5 means low consumption or little waste. Click a row to open the system.",
    "ituL": "Textbook values (ITU lecture, 1980s)",
    "ituN": "Older values that show the orders of magnitude; today's machines are faster (see bars below).",
    "spL": "Maximum speeds from the sources (picks/min or rpm)",
    "spN": "Values come from different sources and conditions (advertised maximum, industrial speed, weaving width). Water jet: only from a student presentation (Toyota LWT810) – not verified. The projectile machine is usually stated in m/min; the bar converts 1,570 m/min to a width of 3.9 m."
   },
   "head": [
    "Manufacturer",
    "Country",
    "Models",
    "Feature",
    "Evidence"
   ],
   "sys": [
    {
     "n": "Shuttle",
     "de": "Historical: a shuttle carrying a weft bobbin flies back and forth",
     "pro": [
      "Real, closed selvedge – the thread unwinds from the bobbin flying along.",
      "Simple, robust mechanics."
     ],
     "con": [
      "Heavy shuttle (around 450 g with cotton weft) – limits speed and width.",
      "The weft is inserted in only a fraction of the machine cycle.",
      "Noise up to about 110 dB.",
      "Constant bobbin changes; yarn must be rewound onto cops."
     ],
     "when": "Only niches where the real shuttle selvedge is wanted.",
     "how": [
      "The shuttle carries a weft bobbin (cop) inside.",
      "A picking mechanism throws it through the shed; on the other side it is braked and thrown back for the next pick.",
      "The thread unwinds from the bobbin flying along – a real, closed selvedge is formed.",
      "The large moving mass limits the speed; bobbins have to be changed constantly."
     ],
     "figs": [
      [
       "≈ 140",
       "picks/min of the first (shuttle) weaving machine according to Picanol"
      ],
      [
       "1924",
       "Toyoda Type G: shuttle change without stopping"
      ]
     ],
     "mk": [
      [
       "(historical) Toyoda, Picanol and many others",
       "–",
       "Shuttle looms",
       "today only niches; in classic Wilton the weft was inserted with shuttles"
      ]
     ],
     "note": "All of today's industrial processes are “shuttleless”: the weft is drawn off a stationary supply package."
    },
    {
     "n": "Projectile",
     "de": "Gripper projectile: a small steel gripper that shoots the thread through the shed",
     "pro": [
      "Low energy demand.",
      "Very wide (up to 655 cm) – also several fabric widths side by side.",
      "Small projectile, small shed: fewer warp breaks.",
      "Wide yarn range from cotton via wool and jute to tapes; 4–6 weft colours."
     ],
     "con": [
      "Tuck-in selvedge: about 15 mm of weft end remain on each side and are tucked in – waste and a thicker edge.",
      "Lower speed than air jet (textbook 250–400 rpm).",
      "Complex mechanics with projectile return; only one supplier left."
     ],
     "when": "Wide technical fabrics, tape yarns, geo/agro textiles, carpet backing.",
     "how": [
      "A small projectile (gripper shuttle) clamps the thread end from the stationary supply package.",
      "A torsion-bar pick shoots it through a guide track across the shed.",
      "On the other side it is braked, opens and releases the thread.",
      "A conveyor brings several projectiles back under the warp; several projectiles circulate at the same time."
     ],
     "figs": [
      [
       "1,570 m/min",
       "max. weft insertion rate P7300HP"
      ],
      [
       "655 cm",
       "max. weaving width P7300HP V8"
      ],
      [
       "> 150,000",
       "Sulzer projectile machines sold (manufacturer figure 2002)"
      ],
      [
       "low",
       "energy demand – a strength for wide technical fabrics"
      ]
     ],
     "mk": [
      [
       "Itema (formerly Sulzer Textil)",
       "IT/CH",
       "P7300HP",
       "only projectile manufacturer; production moved from Zuchwil to Colzate in 2026"
      ]
     ],
     "note": "For tape yarns (agro, geo textiles, carpet backing) Itema sees the projectile ahead of all other insertion systems."
    },
    {
     "n": "Rapier",
     "de": "Rapier: rods or tapes carry the weft mechanically through the shed",
     "pro": [
      "Widest article range, according to teaching material from about 20 to 850 g/m².",
      "Many weft colours and fancy yarns; the thread is guided mechanically, independent of its surface.",
      "Positive transfer is gentle on glass, carbon, aramid.",
      "Double pick possible."
     ],
     "con": [
      "Slower than air jet and water jet.",
      "Rigid rapiers need at least twice the fabric width of space at the side; flexible tapes rub on guides and wear.",
      "With negative transfer the weft can be lost in the middle of the shed."
     ],
     "when": "Fashion with many colours, home textiles, Jacquard upholstery, terry, heavy technical fabrics.",
     "v": [
      "Double rapier, negative transfer",
      "Double rapier, positive transfer (Dornier)",
      "Single rapier"
     ],
     "how": [
      "The giver rapier grips the thread end at the selvedge and travels to the middle of the shed.",
      "There the taker rapier takes over the thread (Dewas: tip to tip; Gabler: loop) and pulls it to the other side.",
      "Negative: the transfer happens only via thread tension and clamping force. Positive: clamps are opened mechanically under control – gentle on delicate yarns.",
      "Flexible tapes are wound onto wheels (little space); rigid rods need space beside the machine but run without touching the warp."
     ],
     "figs": [
      [
       "> 800",
       "picks/min industrial, Picanol Ultimax"
      ],
      [
       "> 130,000",
       "Picanol rapier machines sold"
      ],
      [
       "up to 6,200 mm",
       "weaving width Itema Hercules"
      ],
      [
       "320 / 1,085 m/min",
       "Dornier P2, sailcloth at 339 cm"
      ]
     ],
     "mk": [
      [
       "Picanol",
       "BE",
       "Ultimax, OptiMax-i Connect, GTMax, Supermax",
       "high performance; OptiMax-i up to 540 cm for technical fabrics"
      ],
      [
       "Itema",
       "IT",
       "R9500-2, Hercules, Galileo",
       "guided SK rapiers; Hercules convertible positive/negative"
      ],
      [
       "Lindauer Dornier",
       "DE",
       "P2",
       "rigid rapiers, positive centre transfer; glass, carbon, aramid"
      ],
      [
       "SMIT (Santex Rimar)",
       "IT",
       "GS980, 2FAST, ONE",
       "“Free Flight”: rapiers without guide hooks in the shed; ONE with only one rapier"
      ],
      [
       "RIFA · Jingwei · Tongda · Huasense and others",
       "CN",
       "–",
       "in market studies as rapier/weaving machine manufacturers"
      ]
     ],
     "note": "According to Picanol, rapier machines for sari fabrics in Surat run at around 410 rpm – the “over 800” is a maximum value for suitable articles."
    },
    {
     "n": "Air jet",
     "de": "Air jet: compressed air carries the weft through a channel in the profile reed",
     "pro": [
      "Highest insertion rate, hardly any moving masses.",
      "Low purchase cost, little floor space.",
      "Simple operation."
     ],
     "con": [
      "Compressed air is expensive; the relay nozzles need up to 80 % of it.",
      "Needs even, good yarns. Typical faults: mispick, compressed thread tip, double pick.",
      "With a large width the thread becomes hairy and the tip untwists (especially OE yarn).",
      "Fabric cover according to teaching material not quite as good as with projectile and rapier."
     ],
     "when": "Standard fabrics in large quantities: shirts, bed linen, denim, terry, airbag.",
     "how": [
      "A main nozzle accelerates the weft from the weft feeder into the channel of the profile reed.",
      "Relay nozzles along the width blow in groups – they keep the thread moving.",
      "At the end a suction or stretch nozzle straightens the thread; the edge is cut off.",
      "Very fast and simple, but compressed air is expensive: the relay nozzles use up to 80 % of the air."
     ],
     "figs": [
      [
       "1,350",
       "rpm, narrow Picanol OmniPlus-i Connect"
      ],
      [
       "−20 %",
       "air consumption Toyota JAT910 compared with JAT810"
      ],
      [
       "up to 80 %",
       "share of air used by the relay nozzles"
      ],
      [
       "−1.5 kW",
       "per machine with Picanol EcoBoost"
      ]
     ],
     "mk": [
      [
       "Picanol",
       "BE",
       "OmniPlus-i Connect, TerryPlus-i Connect",
       "AirStream (+100 rpm), EcoBoost, SmartShed"
      ],
      [
       "Toyota Industries",
       "JP",
       "JAT910",
       "i-SENSOR detects the weft in the shed, E-shed"
      ],
      [
       "Tsudakoma",
       "JP",
       "ZAX001neo, ZAX9200i",
       "air jet and water jet from one source"
      ],
      [
       "Itema",
       "IT",
       "A9500-2",
       "prepared for motorised Jacquard without cardan shaft"
      ],
      [
       "Lindauer Dornier",
       "DE",
       "A2",
       "air jet for technical fabrics (airbag, parachute)"
      ],
      [
       "RIFA · Jingwei · Tianyi Red Flag and others",
       "CN",
       "–",
       "market studies"
      ]
     ],
     "note": "In 2025 China was the largest buyer of air-jet and water-jet machines; shipments there fell by 32 % and 57 % respectively (ITMF)."
    },
    {
     "n": "Water jet",
     "de": "Water jet: a jet of water pulls the weft through the shed",
     "pro": [
      "High insertion rate with filament yarns.",
      "Low energy consumption, quiet, little vibration, hardly any weft waste.",
      "Gentle on the warp – no metal part rubs."
     ],
     "con": [
      "Only water-repellent filaments (PES, PA, acetate, glass) – no cotton, wool, viscose.",
      "The fabric leaves the machine wet and must be dried; the waste water must be treated.",
      "Only up to two weft colours; smaller width.",
      "Hard water can cause rust."
     ],
     "when": "Synthetic filament fabrics in bulk, above all in East Asia.",
     "how": [
      "For each pick a pump pushes a small amount of water through the nozzle.",
      "Water has more friction on the thread than air – one nozzle is enough, no relay nozzles.",
      "The fabric gets wet and must be dried; the water must be treated.",
      "Only for non-absorbent synthetic yarns (PES, PA) – cotton or viscose do not work."
     ],
     "figs": [
      [
       "8–5,600 dtex",
       "yarn range Tsudakoma water jet (PA to PES)"
      ],
      [
       "≈ 1,200",
       "rpm Toyota LWT810 (not verified)"
      ],
      [
       "−57 %",
       "shipments to China 2025 (ITMF)"
      ]
     ],
     "mk": [
      [
       "Tsudakoma",
       "JP",
       "ZW8100, ZW8200",
       "wide yarn range, also double fabrics"
      ],
      [
       "Toyota Industries",
       "JP",
       "LWT810",
       "water jet for synthetics"
      ],
      [
       "Chinese manufacturers",
       "CN",
       "–",
       "largest part of the world market (market studies)"
      ]
     ],
     "note": "One market study names the water jet as the most common weaving machine by units (over 47 %) – a result of Chinese synthetics weaving."
    }
   ],
   "svg": {
    "prestore": "Feeder",
    "strike": "Picking",
    "brake": "Brake",
    "ret": "Return of the projectiles under the warp",
    "single": "a single rapier travels across empty and pulls the thread back",
    "handPos": "Transfer: clamps opened under control",
    "handNeg": "Transfer: thread is pulled out",
    "bringer": "Giver",
    "taker": "Taker",
    "mainJet": "Main nozzle",
    "relay": "Relay nozzles blow in groups, only where the thread is at the moment",
    "waterJet": "Water nozzle",
    "beat": "Beat-up: the reed pushes the weft to the fell",
    "insertion": "Weft insertion",
    "fabric": "Fabric",
    "reed": "Reed",
    "back": "↑ back:",
    "shafts": "shafts",
    "front": "↓ front:",
    "cloth": "cloth"
   },
   "steps": [
    "1 · Shed open, reed back – insertion starts",
    "2 · Weft on its way",
    "3 · Middle of the shed (rapier: transfer)",
    "4 · Weft on its way to the other side",
    "5 · Insertion complete",
    "6 · Reed swings forward",
    "7 · Beat-up at the fell",
    "8 · Reed back, shed change"
   ],
   "zoom": {
    "msg": [
     "1 · Giver brings the thread, taker comes towards it",
     "2 · Rapier heads overlap, taker clamp closes around the thread",
     "3 · Positive: opener lifts the giver clamp – the thread is released",
     "3 · Negative: giver clamp stays closed – the taker pulls the thread out against the spring force",
     "4 · Taker carries the weft to the other side, giver travels back empty"
    ],
    "spring": "Spring",
    "opener": "Clamp opener",
    "pull": "Pull on the thread",
    "step": "Step {n} of 4",
    "pos": "Positive (e.g. Dornier P2, rigid rapiers): the clamps are opened and closed mechanically at fixed moments. The thread is not pulled out but handed over – gentle on glass, carbon, aramid and fancy yarns.",
    "neg": "Negative (almost all flexible tape rapiers): there is no opener. The thread is pulled from giver to taker only via thread tension and clamping force – simple and fast, but smooth, stiff or delicate yarns can be lost or break."
   },
   "heatHead": [
    "System",
    "Insertion rate",
    "Max. width",
    "Yarn range",
    "Weft colours",
    "Energy (5 = low)",
    "Selvedge/waste (5 = little)"
   ],
   "ituHead": [
    "System",
    "Working width (m)",
    "Speed (rpm)",
    "Insertion rate (m/min)"
   ],
   "itu": [
    [
     "Shuttle",
     "1.88–4.14",
     "60–160",
     "357–525"
    ],
    [
     "Projectile",
     "1.90–5.45",
     "250–400",
     "600–1,250"
    ],
    [
     "Rigid rapier",
     "1.60–4.00",
     "200–420",
     "up to 1,100–1,300 (two-phase)"
    ],
    [
     "Flexible rapier",
     "1.80–4.20",
     "200–500",
     "550–1,150"
    ],
    [
     "Air jet",
     "1.40–3.60",
     "400–700",
     "650–1,600"
    ],
    [
     "Water jet",
     "1.50–2.30",
     "800",
     "1,000–1,700"
    ]
   ],
   "speeds": [
    "Shuttle (first machine)",
    "Projectile P7300HP (1,570 m/min ÷ 3.9 m)",
    "Rapier Picanol Ultimax (industrial)",
    "Water jet Toyota LWT810 (not verified)",
    "Air jet Picanol OmniPlus-i (narrow)"
   ]
  },
  "schaft": {
   "titles": [
    "Dobbies & cams",
    "Integrated electronic shedding",
    "Weaving machines (selection)"
   ],
   "cards": [
    [
     [
      "Stäubli S3000 / S3200 (rotary dobby)",
      "Electronically controlled, mounted below or above on water-jet, air-jet and rapier machines; > 20,000 units in use (2017). Stäubli invented the rotary principle."
     ],
     [
      "Stäubli S3292",
      "New high-speed dobby, presented at ITME India 2026."
     ],
     [
      "Stäubli S2688 / S4080",
      "Open-shed dobbies for heavy technical fabrics and carpet ground."
     ],
     [
      "Stäubli cams S1691/92, S1792",
      "For simple weaves on high-performance machines."
     ]
    ],
    [
     [
      "Picanol SmartShed / SmartShed Pro",
      "Each shaft has its own servo motor (8, 12 or 16 shafts); 8–16 servo axes from Lenze, liquid-cooled. Weave change without mechanical conversion."
     ],
     [
      "Toyota E-shed / C-shed",
      "Own electronic shedding since 2000, offered on the JAT910."
     ],
     [
      "Dornier SyncroDrive",
      "Shedding with its own motor (6–8 kW), coupled electronically to the weaving machine instead of via a cardan shaft – no start-up marks."
     ]
    ],
    [
     [
      "Rapier",
      "Picanol Ultimax/GTMax · Itema R9500-2/Hercules · Dornier P2 · SMIT GS980/2FAST · Chinese suppliers"
     ],
     [
      "Air jet",
      "Picanol OmniPlus-i · Toyota JAT910 · Tsudakoma ZAX · Itema A9500-2 · Dornier A2"
     ],
     [
      "Water jet",
      "Tsudakoma ZW · Toyota LWT810 · many Chinese suppliers"
     ],
     [
      "Projectile",
      "Itema P7300HP (only supplier)"
     ]
    ]
   ]
  },
  "jac": {
   "hkL": "Number of hooks per machine (manufacturer data, logarithmic scale)",
   "hk": [
    "Stäubli UNIVALETTE",
    "GITEC Grosse (EJP/EJT)",
    "Bonas Ji",
    "Bonas Si",
    "Stäubli SX (example)"
   ],
   "hkNote": "Bonas Ji: upper limit 17,280 according to Vandewiele, 5,760 according to a trade fair report",
   "head": [
    "Manufacturer",
    "Location",
    "Models",
    "Technology / special feature",
    "Evidence"
   ],
   "rows": [
    [
     "Stäubli",
     "Swiss group, incl. Stäubli Bayreuth (DE)",
     "LX PRO, LXL PRO, LXXL PRO, SX PRO, N4L, UNIVALETTE; harnesses",
     "MX-PRO selection modules, double-lift open shed; CX 860 (1987) according to Stäubli the first electronic Jacquard; UNIVALETTE with its own, electronically synchronised drive"
    ],
    [
     "Bonas (Vandewiele group)",
     "BE (brand/Kortrijk)",
     "Si, Ji, H3D, MDA02",
     "100 % electronic micro-selector with full diagnostics; Si is very compact (12–36 knives deep); H3D for 3D and multi-layer fabrics"
    ],
    [
     "GITEC Grosse (Hisun group)",
     "DE (Ulm) / CN",
     "EJP-4, EJT-4 (terry), UniShed 2",
     "founded 1878 in Greiz; UniShed: harness-free, one leaf spring per warp thread – for airbags"
    ],
    [
     "Weaving machines for Jacquard",
     "–",
     "Picanol (cardan or independent), Itema A9500-2/R9500-2, Dornier P2/A2 with SyncroDrive, SMIT GS980 (jumbo Jacquard), Vandewiele velvet (VSi)",
     "Jacquard driven either via cardan shaft or by its own motor – see Differences"
    ]
   ],
   "note": "Contradiction in the sources: Bonas dates the launch of the electronic Jacquard machine to ITMA Milan 1983; Stäubli calls its CX 860 from 1987 the world's first electronically controlled Jacquard machine. The number of hooks of the Bonas Ji is also stated differently (up to 5,760 or up to 17,280)."
  },
  "wil": {
   "seg": [
    "Wire Wilton",
    "Face-to-face (double pile)",
    "Axminster"
   ],
   "cards": {
    "rute": [
     [
      "Principle",
      "Pile threads run over steel wires that are inserted across. When a wire is pulled out, a blade at its end cuts the loop open (Wilton, cut pile) – without a blade the loop remains (Brussels)."
     ],
     [
      "Colour",
      "Pile colours not needed lie “dead” in the ground fabric – more expensive, but very dense. Usually 1 of 5 colours per tuft."
     ],
     [
      "Weft",
      "Classically with shuttles; the wire height limits pile height and speed."
     ]
    ],
    "f2f": [
     [
      "Principle",
      "Two ground fabrics one above the other, the pile thread swings between them. A knife cuts in the middle – two carpets at once."
     ],
     [
      "Weft",
      "Double rapier (one rapier per ground fabric) or three rapiers: the middle one inserts an auxiliary weft around which loops form, and it is removed again."
     ],
     [
      "Output",
      "Up to 250 rpm (Vandewiele RCF), widths up to 5.2–5.3 m; several times the output of wire weaving."
     ]
    ],
    "axm": [
     [
      "Principle",
      "Each tuft is cut and inserted individually – grippers (beak-like) or a spool chain."
     ],
     [
      "Colour",
      "The entire pile lies on the surface; spool Axminster allows practically unlimited colours, gripper Axminster about 1 of 8."
     ],
     [
      "Machine",
      "Vandewiele MAX91: high speed, 16 colour frames."
     ]
    ]
   },
   "svg": {
    "ground": "Ground fabric (warp + weft)",
    "cutMsg": "Wire is pulled out sideways – blade cuts the loops",
    "cutPile": "← cut pile (Wilton)",
    "loops": "Loops over wires (cross-section) →",
    "knife": "Cutting knife separates the two carpets",
    "upper": "upper carpet (back on top), weft from the upper rapier",
    "lower": "lower carpet, weft from the lower rapier",
    "twoCarpets": "← two finished pile carpets",
    "pendulum": "Pile thread swings between the ground fabrics →",
    "grip1": "Gripper places the cut",
    "grip2": "tuft into the ground",
    "each": "each tuft individually, entire pile on the surface – no dead pile in the back"
   },
   "step": "one step = ¼ pile row",
   "head": [
    "Manufacturer",
    "Process",
    "Models",
    "Data / special feature",
    "Evidence"
   ],
   "rows": [
    [
     "Vandewiele (Van de Wiele)",
     "Face-to-face, double rapier",
     "RCF, RCE2+, SRE2+",
     "RCF up to 250 rpm, 3/4/5 m, Fast Creel with stationary bobbins; RCE2+ up to 5.2 m; SRE2+ shaggy up to 2×70 mm, also artificial turf"
    ],
    [
     "Vandewiele",
     "Face-to-face, three rapiers",
     "USF, UCE3+, HCE3+, RCE3+",
     "Cut, loop and flat-weave effects at the same time; HCE3+ imitates hand-knotted carpets, pile from 3.5 mm"
    ],
    [
     "Vandewiele",
     "Single pile, double rapier",
     "LCE2+",
     "short/long loops, flat weave, sisal look"
    ],
    [
     "Vandewiele",
     "Wire Wilton",
     "AWE1+",
     "Loop and/or cut, 2.20 / 2.70 / 4 m"
    ],
    [
     "Vandewiele",
     "Axminster",
     "MAX91",
     "16 colour frames, high speed"
    ],
    [
     "Stäubli (Schönherr)",
     "Face-to-face",
     "ALPHA 500/560 UNIVERSAL, XHDC",
     "up to 5.3 m, true 3-position Jacquard (Stäubli), servo cutting device, liquid cooling; built in Bayreuth and Chemnitz"
    ],
    [
     "Stäubli (Schönherr)",
     "Single pile loop",
     "ALPHA 500 SINGLELOOP",
     "according to Stäubli three times as productive as a wire loom"
    ],
    [
     "Stäubli (Schönherr)",
     "Single or double rapier",
     "ALPHA 500 LEANTEC",
     "Shaggy, artificial turf, greige goods for printing"
    ],
    [
     "Picanol",
     "Flat carpet",
     "Ultimax (Flat carpet, ITMA 2023)",
     "Rapier machine for flat-woven carpets, no pile"
    ]
   ],
   "note": "A manufacturer comparison of productivity should be read with caution: Van de Wiele states up to six times the output of a wire loom for the three-rapier machine UCL83, Stäubli three times for the ALPHA 500 SINGLELOOP – these are different machines and articles."
  },
  "diff": {
   "follow": "Consequence:",
   "cards": [
    [
     "Rapier: positive vs. negative transfer",
     "Dornier transfers positively with rigid rapiers – the clamps are opened mechanically. Almost all others use flexible tapes with negative transfer. Itema (Hercules) can be converted between both.",
     "Positive: gentle on glass, carbon, aramid, fancy yarns. Negative: faster, simpler."
    ],
    [
     "Rapier: guided vs. “Free Flight”",
     "Itema relies on guided SK rapiers with hooks in the shed; SMIT advertises the fastest free-flight rapier, which needs no guide hooks.",
     "Free flight is gentle on sensitive warps (silk, worsted); guidance allows more security at high speed."
    ],
    [
     "Air jet: the battle for compressed air",
     "Relay nozzles eat up to 80 % of the air. With the JAT910, Toyota lowers pressure by 10 % and consumption by 20 %; Picanol brings AirStream (+100 rpm) and EcoBoost (−1.5 kW).",
     "With air jets, energy costs often matter more than the purchase price."
    ],
    [
     "Projectile: the wide weaving machine",
     "Only Itema still builds projectile machines. They are wide (up to 655 cm), economical and robust for tape yarns.",
     "For geo/agro textiles and carpet backing; hardly relevant for fashion any more."
    ],
    [
     "Water jet: synthetics only",
     "Water pulls the thread more effectively than air, but wet fabric and water treatment; cellulosic fibres are ruled out.",
     "Asian PES/PA bulk goods – almost only Japan and China as manufacturers."
    ],
    [
     "Shedding: mechanically coupled vs. own drive",
     "Classically the weaving machine drives the dobby or Jacquard via a cardan shaft. Picanol SmartShed (servo per shaft), Dornier SyncroDrive, Itema's motorised Jacquard without cardan and Stäubli UNIVALETTE decouple this electronically.",
     "Fewer start-up marks, faster weave changes, the Jacquard can run down gently."
    ],
    [
     "Jacquard: selection technology",
     "Bonas selects with a 100 % electronic micro-selector (full diagnostics), Stäubli with MX-PRO modules. Grosse UniShed does without a harness entirely: one leaf spring per warp thread.",
     "UniShed for airbag fabrics; Bonas Si for very high hook counts in a small space."
    ],
    [
     "Carpet: wire vs. face-to-face",
     "Wire Wilton makes one carpet, needs wires and is slow. Face-to-face makes two carpets at the same time with two or three rapiers.",
     "Face-to-face dominates today; wire remains for certain loop/cut qualities (Vandewiele AWE1+)."
    ]
   ]
  },
  "mx": {
   "legend": [
    "documented in the sources",
    "from market study lists only",
    "Empty cells mean “not documented here”."
   ],
   "head": [
    "Manufacturer",
    "Country"
   ],
   "cols": [
    "Rapier",
    "Air",
    "Water",
    "Projectile",
    "Dobby/cam",
    "Jacquard machine",
    "Carpet face-to-face",
    "Wire Wilton",
    "Axminster"
   ],
   "firms": [
    "Picanol",
    "Itema",
    "Lindauer Dornier",
    "Toyota Industries",
    "Tsudakoma",
    "SMIT (Santex Rimar)",
    "Stäubli (incl. Schönherr)",
    "Vandewiele / Bonas",
    "GITEC Grosse",
    "RIFA",
    "Jingwei · Haijia · Tongda · Huasense"
   ],
   "lkL": "More in the Knowledge Base",
   "links": [
    [
     "Shaft weaving",
     "Harness, drawing-in and lifting plan: how shafts make the weave."
    ],
    [
     "Weave structures",
     "Point paper, plain, twill and satin – and draw your own weave."
    ],
    [
     "Jacquard weaving",
     "Every warp thread lifted on its own: how a Jacquard machine weaves patterns."
    ],
    [
     "Wilton carpet",
     "Woven pile carpet: wires, cut and loop pile, Jacquard colour choice."
    ]
   ]
  }
 },
 "es": {
  "ui": {
   "eyebrow": "Knowledge Base · Tejeduría",
   "h1": "Tejeduría con lizos, Jacquard y Wilton: máquinas, fabricantes, inserción de trama",
   "lead": "En esencia, un telar consta de dos sistemas: la formación de calada (excéntrica, maquinita de lizos o máquina Jacquard; decide la libertad de dibujo) y la inserción de trama (lanzadera, proyectil, pinza, aire o agua; decide la velocidad, el ancho y la gama de hilos). Esta página muestra ambos con animaciones, asigna los fabricantes a cada tipo de tejeduría y explica dónde se diferencian realmente las máquinas. En el Wilton (alfombra de pelo) se añaden la técnica de varillas y la de doble pieza.",
   "note": "Estado de la investigación: noviembre de 2026. Los datos de los fabricantes suelen ser valores publicitarios o máximos; las denominaciones de modelos y los datos técnicos pueden cambiar.",
   "sources": "Fuentes",
   "open": "Abrir módulo",
   "loc": "es-ES",
   "prev": "◀ Paso atrás",
   "next": "Paso adelante ▶",
   "play": "▶ Reproducir",
   "pause": "Pausa",
   "st": {
    "h": "FABR.",
    "p": "PRENSA",
    "m": "LISTA"
   },
   "stLegend": "Fuente: FABR. = dato del fabricante · PRENSA = prensa especializada/material didáctico · LISTA = solo de listas de estudios de mercado"
  },
  "scenes": [
   {
    "k": "Formación de calada",
    "title": "Lizos o Jacquard: la formación de calada decide el dibujo",
    "text": "A la izquierda se ve qué hilos de urdimbre se levantan en cada pasada; a la derecha, el tejido que se forma. Con lizos, muchos hilos cuelgan del mismo marco: el dibujo se repite tras pocos hilos. Con Jacquard, cada hilo de urdimbre se controla individualmente mediante un platino."
   },
   {
    "k": "Inserción de trama",
    "title": "Los cinco sistemas de inserción de trama",
    "text": "Vista superior de la calada: la trama (naranja) se inserta a través de la urdimbre (azul), delante del peine retirado, es decir, entre el peine y el borde del tejido. Después el peine avanza y bate la trama contra el borde del tejido. Animación ralentizada, velocidades no a escala: las barras de abajo muestran los valores máximos reales."
   },
   {
    "k": "Tejeduría con lizos",
    "title": "Tejeduría con lizos: máquinas y fabricantes",
    "text": "En la tejeduría con lizos, el tejedor combina un telar (pinza, aire, agua o proyectil) con una formación de calada por lizos. El mercado está dividido en dos: por un lado los fabricantes de telares, por otro los especialistas en maquinitas de lizos y excéntricas, sobre todo Stäubli."
   },
   {
    "k": "Tejeduría Jacquard",
    "title": "Tejeduría Jacquard: máquinas y fabricantes",
    "text": "La máquina Jacquard se sitúa encima del telar; cada platino levanta uno o varios hilos de urdimbre mediante un cordón de arcada. El número de platinos determina cuántos hilos por curso se controlan individualmente. El telar de debajo suele ser de pinzas o de chorro de aire."
   },
   {
    "k": "Tejeduría Wilton",
    "title": "Tejeduría Wilton: varillas, doble pieza, Axminster",
    "text": "Wilton designa alfombras de pelo tejidas en las que el hilo de pelo corre continuamente en el tejido de fondo y se lleva a la superficie de forma controlada. Clásicamente se hace con varillas (alambres); hoy, sobre todo con el procedimiento de doble pieza (face-to-face). Axminster se incluye como comparación."
   },
   {
    "k": "Diferencias",
    "title": "Diferencias significativas entre las máquinas",
    "text": "Lo que los fabricantes resuelven técnicamente de forma distinta, y lo que eso significa para el hilo, el artículo y los costes."
   },
   {
    "k": "Matriz de fabricantes",
    "title": "Matriz de fabricantes",
    "text": "Qué fabricante ofrece qué sistema de inserción, formación de calada y técnica de alfombra, según las fuentes de esta página."
   }
  ],
  "kpis": [
   [
    "1350",
    "pasadas/min en telares de chorro de aire Picanol OmniPlus-i estrechos"
   ],
   [
    "31 104",
    "platinos en una sola máquina Jacquard Bonas Si"
   ],
   [
    "1570 m/min",
    "rendimiento de inserción de trama del telar de proyectil P7300HP"
   ],
   [
    "5,3 m",
    "ancho de tejido del telar de alfombras Stäubli/Schönherr ALPHA 500"
   ],
   [
    "hasta 6×",
    "producción de un telar de doble pieza (Van de Wiele UCL83) frente a un telar de varillas"
   ]
  ],
  "fach": {
   "seg": {
    "ex": "Excéntrica (4 lizos)",
    "sch": "Maquinita de lizos (8 lizos)",
    "jac": "Jacquard (cada hilo por separado)"
   },
   "svg": {
    "weaveCap": "Tejido: azul = urdimbre arriba, naranja = trama arriba",
    "shafts4": "4 lizos – excéntrica: secuencia fija",
    "shafts8": "8 lizos – maquinita: programable libremente, pero el hilo e cuelga del lizo e mod 8",
    "jacHead": "Máquina Jacquard – un platino por hilo",
    "jacCap": "Cordones de arcada: levantados (naranja) o abajo (gris) – libre pasada a pasada",
    "pick": "Pasada {n} de {total}"
   },
   "cards": {
    "ex": [
     [
      "Principio",
      "Discos de leva (excéntricas) mueven pocos lizos en una secuencia fija incorporada."
     ],
     [
      "Límite",
      "Solo ligamentos sencillos y cortos (tafetán, sarga); cambiar el dibujo significa cambiar las excéntricas."
     ],
     [
      "Dónde",
      "Artículos de masa en telares rápidos de chorro de aire y de agua; excéntricas Stäubli S1691/92, S1792."
     ]
    ],
    "sch": [
     [
      "Principio",
      "Una maquinita de lizos levanta cada lizo de forma libremente programable; hoy con control electrónico."
     ],
     [
      "Límite",
      "Todos los hilos de un lizo hacen lo mismo. Más de unos 24 lizos quedan demasiado escalonados; el curso sigue siendo pequeño."
     ],
     [
      "Dónde",
      "Camisas, ropa de cama, denim, tejidos técnicos; p. ej. Stäubli S3000/S3200, Picanol SmartShed."
     ]
    ],
    "jac": [
     [
      "Principio",
      "Cada platino controla un hilo de urdimbre (o unos pocos) por separado: de cientos a más de 30 000 grupos independientes."
     ],
     [
      "Límite",
      "Arcada más cara y alta, más tiempo de preparación; a cambio, cualquier figura en todo el ancho."
     ],
     [
      "Dónde",
      "Tapicería, damasco, etiquetas, rizo con motivo, airbags OPW, alfombras."
     ]
    ]
   }
  },
  "ins": {
   "lbl": {
    "how": "Así funciona",
    "figs": "Cifras clave",
    "pro": "Ventajas",
    "con": "Desventajas",
    "when": "¿Cuándo elegirlo?",
    "mk": "Fabricantes y modelos",
    "zoom": "Lupa: entrega en el centro de la calada (muy ampliada, ralentizada)",
    "cmpT": "Comparación de un vistazo",
    "cmpN": "Valoración cualitativa de 1 (débil) a 5 (fuerte), derivada de las fuentes de esta página; no son valores medidos. En «Energía» y «Orillo/desperdicio», 5 significa poco consumo o poco desperdicio. Haga clic en una fila para abrir el sistema.",
    "ituL": "Valores de manual (curso de la ITU, años 80)",
    "ituN": "Valores antiguos que muestran los órdenes de magnitud; las máquinas actuales son más rápidas (ver barras abajo).",
    "spL": "Velocidades máximas según las fuentes (pasadas/min o rpm)",
    "spN": "Los valores proceden de fuentes y condiciones distintas (máximo publicitario, velocidad industrial, ancho de tejido). Chorro de agua: solo de una presentación de estudiantes (Toyota LWT810), sin verificar. El telar de proyectil suele indicarse en m/min; la barra convierte 1570 m/min a un ancho de 3,9 m."
   },
   "head": [
    "Fabricante",
    "País",
    "Modelos",
    "Característica",
    "Fuente"
   ],
   "sys": [
    {
     "n": "Lanzadera",
     "de": "Histórico: una lanzadera con canilla de trama va y viene",
     "pro": [
      "Orillo auténtico y cerrado: el hilo se desenrolla de la canilla que viaja con la lanzadera.",
      "Mecánica sencilla y robusta."
     ],
     "con": [
      "Lanzadera pesada (unos 450 g con trama de algodón): limita la velocidad y el ancho.",
      "La trama se inserta solo en una fracción del ciclo de la máquina.",
      "Ruido de hasta unos 110 dB.",
      "Cambio constante de canillas; el hilo debe rebobinarse en canillas."
     ],
     "when": "Solo nichos en los que se quiere el auténtico orillo de lanzadera.",
     "how": [
      "La lanzadera lleva dentro una canilla de trama.",
      "Un mecanismo de picada la lanza a través de la calada; al otro lado se frena y se devuelve para la siguiente pasada.",
      "El hilo se desenrolla de la canilla que viaja con ella: se forma un orillo auténtico y cerrado.",
      "La gran masa en movimiento limita la velocidad; las canillas deben cambiarse constantemente."
     ],
     "figs": [
      [
       "≈ 140",
       "pasadas/min del primer telar (de lanzadera) según Picanol"
      ],
      [
       "1924",
       "Toyoda Type G: cambio de lanzadera sin parar"
      ]
     ],
     "mk": [
      [
       "(histórico) Toyoda, Picanol y muchos otros",
       "–",
       "Telares de lanzadera",
       "hoy solo nichos; en el Wilton clásico la trama se insertaba con lanzadera"
      ]
     ],
     "note": "Todos los procesos industriales actuales son «sin lanzadera»: la trama se extrae de una bobina de alimentación fija."
    },
    {
     "n": "Proyectil",
     "de": "Proyectil de pinza: pequeña pinza de acero que dispara el hilo a través de la calada",
     "pro": [
      "Bajo consumo de energía.",
      "Muy ancho (hasta 655 cm), también varias piezas una junto a otra.",
      "Proyectil pequeño, calada pequeña: menos roturas de urdimbre.",
      "Amplia gama de hilos, desde algodón, lana y yute hasta cintas; 4–6 colores de trama."
     ],
     "con": [
      "Orillo remetido: a cada lado quedan unos 15 mm de cabo de trama que se remeten; desperdicio y orillo más grueso.",
      "Velocidad menor que el chorro de aire (manual: 250–400 rpm).",
      "Mecánica compleja con retorno de proyectiles; solo queda un proveedor."
     ],
     "when": "Tejidos técnicos anchos, hilos de cinta, geo/agrotextiles, dorso de alfombras.",
     "how": [
      "Un pequeño proyectil (lanzadera de pinza) sujeta el extremo del hilo de la bobina de alimentación fija.",
      "Una picada por barra de torsión lo dispara por una guía a través de la calada.",
      "Al otro lado se frena, se abre y suelta el hilo.",
      "Una cinta transportadora devuelve varios proyectiles bajo la urdimbre; varios proyectiles circulan a la vez."
     ],
     "figs": [
      [
       "1570 m/min",
       "máx. rendimiento de inserción P7300HP"
      ],
      [
       "655 cm",
       "máx. ancho de tejido P7300HP V8"
      ],
      [
       "> 150 000",
       "telares de proyectil Sulzer vendidos (dato del fabricante, 2002)"
      ],
      [
       "bajo",
       "consumo de energía: punto fuerte en tejidos técnicos anchos"
      ]
     ],
     "mk": [
      [
       "Itema (antes Sulzer Textil)",
       "IT/CH",
       "P7300HP",
       "único fabricante de proyectil; producción trasladada en 2026 de Zuchwil a Colzate"
      ]
     ],
     "note": "Para hilos de cinta (agro, geotextiles, dorso de alfombras), Itema considera el proyectil por delante de todos los demás sistemas de inserción."
    },
    {
     "n": "Pinza",
     "de": "Rapier: varillas o cintas llevan la trama mecánicamente a través de la calada",
     "pro": [
      "La mayor gama de artículos, según material didáctico de unos 20 a 850 g/m².",
      "Muchos colores de trama e hilos de fantasía; el hilo se guía mecánicamente, independientemente de su superficie.",
      "La entrega positiva cuida el vidrio, el carbono y la aramida.",
      "Doble pasada posible."
     ],
     "con": [
      "Más lento que el chorro de aire y de agua.",
      "Las pinzas rígidas necesitan al menos el doble del ancho del tejido como espacio lateral; las cintas flexibles rozan en las guías y se desgastan.",
      "Con entrega negativa la trama puede perderse en el centro de la calada."
     ],
     "when": "Moda con muchos colores, textiles para el hogar, tapicería Jacquard, rizo, tejidos técnicos pesados.",
     "v": [
      "Doble pinza, entrega negativa",
      "Doble pinza, entrega positiva (Dornier)",
      "Pinza única"
     ],
     "how": [
      "La pinza portadora agarra el extremo del hilo en el orillo y avanza hasta el centro de la calada.",
      "Allí la pinza receptora toma el hilo (Dewas: punta con punta; Gabler: bucle) y lo lleva al otro lado.",
      "Negativa: la entrega se produce solo por la tensión del hilo y la fuerza de sujeción. Positiva: las pinzas se abren con control mecánico, cuidando los hilos delicados.",
      "Las cintas flexibles se enrollan en ruedas (poco espacio); las varillas rígidas necesitan espacio junto a la máquina, pero se guían sin contacto con la urdimbre."
     ],
     "figs": [
      [
       "> 800",
       "pasadas/min industrial, Picanol Ultimax"
      ],
      [
       "> 130 000",
       "telares de pinzas Picanol vendidos"
      ],
      [
       "hasta 6200 mm",
       "ancho de tejido Itema Hercules"
      ],
      [
       "320 / 1085 m/min",
       "Dornier P2, lona a 339 cm"
      ]
     ],
     "mk": [
      [
       "Picanol",
       "BE",
       "Ultimax, OptiMax-i Connect, GTMax, Supermax",
       "alto rendimiento; OptiMax-i hasta 540 cm para técnicos"
      ],
      [
       "Itema",
       "IT",
       "R9500-2, Hercules, Galileo",
       "pinzas SK guiadas; Hercules convertible positiva/negativa"
      ],
      [
       "Lindauer Dornier",
       "DE",
       "P2",
       "pinzas rígidas, entrega positiva en el centro; vidrio, carbono, aramida"
      ],
      [
       "SMIT (Santex Rimar)",
       "IT",
       "GS980, 2FAST, ONE",
       "«Free Flight»: pinzas sin ganchos guía en la calada; ONE con una sola pinza"
      ],
      [
       "RIFA · Jingwei · Tongda · Huasense y otros",
       "CN",
       "–",
       "en estudios de mercado como fabricantes de telares de pinzas"
      ]
     ],
     "note": "Según Picanol, los telares de pinzas para tejidos de sari en Surat funcionan a unas 410 rpm; las «más de 800» son un valor máximo para artículos adecuados."
    },
    {
     "n": "Chorro de aire",
     "de": "Air-jet: el aire comprimido lleva la trama por un canal del peine perfilado",
     "pro": [
      "Máximo rendimiento de inserción, apenas masas en movimiento.",
      "Bajo coste de adquisición, poco espacio.",
      "Manejo sencillo."
     ],
     "con": [
      "El aire comprimido es caro; las toberas auxiliares consumen hasta el 80 %.",
      "Requiere hilos regulares y buenos. Fallos típicos: pasada fallida, punta del hilo recalcada, doble pasada.",
      "Con gran ancho el hilo se vuelve velloso y la punta se destuerce (sobre todo hilo OE).",
      "Según material didáctico, la cobertura del tejido no es tan buena como con proyectil y pinza."
     ],
     "when": "Tejidos estándar en grandes cantidades: camisas, ropa de cama, denim, rizo, airbag.",
     "how": [
      "Una tobera principal acelera la trama desde el acumulador hacia el canal del peine perfilado.",
      "Las toberas auxiliares a lo largo del ancho soplan por grupos: mantienen el hilo en movimiento.",
      "Al final, una tobera de aspiración o estiramiento estira el hilo; el orillo se corta.",
      "Muy rápido y sencillo, pero el aire comprimido es caro: las toberas auxiliares consumen hasta el 80 % del aire."
     ],
     "figs": [
      [
       "1350",
       "rpm, Picanol OmniPlus-i Connect estrecho"
      ],
      [
       "−20 %",
       "consumo de aire Toyota JAT910 frente a JAT810"
      ],
      [
       "hasta 80 %",
       "parte del aire de las toberas auxiliares"
      ],
      [
       "−1,5 kW",
       "por máquina con Picanol EcoBoost"
      ]
     ],
     "mk": [
      [
       "Picanol",
       "BE",
       "OmniPlus-i Connect, TerryPlus-i Connect",
       "AirStream (+100 rpm), EcoBoost, SmartShed"
      ],
      [
       "Toyota Industries",
       "JP",
       "JAT910",
       "i-SENSOR detecta la trama en la calada, E-shed"
      ],
      [
       "Tsudakoma",
       "JP",
       "ZAX001neo, ZAX9200i",
       "chorro de aire y de agua del mismo proveedor"
      ],
      [
       "Itema",
       "IT",
       "A9500-2",
       "preparado para Jacquard motorizado sin eje cardán"
      ],
      [
       "Lindauer Dornier",
       "DE",
       "A2",
       "chorro de aire para técnicos (airbag, paracaídas)"
      ],
      [
       "RIFA · Jingwei · Tianyi Red Flag y otros",
       "CN",
       "–",
       "estudios de mercado"
      ]
     ],
     "note": "En 2025 China fue el mayor comprador de telares de chorro de aire y de agua; los envíos allí cayeron un 32 % y un 57 % respectivamente (ITMF)."
    },
    {
     "n": "Chorro de agua",
     "de": "Water-jet: un chorro de agua arrastra la trama a través de la calada",
     "pro": [
      "Alto rendimiento de inserción con hilos de filamento.",
      "Bajo consumo de energía, silencioso, poca vibración, casi sin desperdicio de trama.",
      "Cuida la urdimbre: ninguna pieza metálica roza."
     ],
     "con": [
      "Solo filamentos hidrófobos (PES, PA, acetato, vidrio): ni algodón, ni lana, ni viscosa.",
      "El tejido sale mojado de la máquina y debe secarse; las aguas residuales deben tratarse.",
      "Solo hasta dos colores de trama; menor ancho.",
      "El agua dura puede causar óxido."
     ],
     "when": "Tejidos de filamento sintético en masa, sobre todo en Asia oriental.",
     "how": [
      "En cada pasada, una bomba impulsa una pequeña cantidad de agua por la tobera.",
      "El agua tiene más fricción con el hilo que el aire: basta una tobera, sin toberas auxiliares.",
      "El tejido se moja y debe secarse; el agua debe tratarse.",
      "Solo para hilos sintéticos no absorbentes (PES, PA); el algodón o la viscosa no sirven."
     ],
     "figs": [
      [
       "8–5600 dtex",
       "gama de hilos chorro de agua Tsudakoma (PA a PES)"
      ],
      [
       "≈ 1200",
       "rpm Toyota LWT810 (sin verificar)"
      ],
      [
       "−57 %",
       "envíos a China 2025 (ITMF)"
      ]
     ],
     "mk": [
      [
       "Tsudakoma",
       "JP",
       "ZW8100, ZW8200",
       "amplia gama de hilos, también tejidos dobles"
      ],
      [
       "Toyota Industries",
       "JP",
       "LWT810",
       "chorro de agua para sintéticos"
      ],
      [
       "Fabricantes chinos",
       "CN",
       "–",
       "la mayor parte del mercado mundial (estudios de mercado)"
      ]
     ],
     "note": "Un estudio de mercado cita el chorro de agua como el telar más frecuente por unidades (más del 47 %), consecuencia de la tejeduría china de sintéticos."
    }
   ],
   "svg": {
    "prestore": "Acumulador",
    "strike": "Picada",
    "brake": "Freno",
    "ret": "Retorno de los proyectiles bajo la urdimbre",
    "single": "una sola pinza cruza vacía y trae el hilo de vuelta",
    "handPos": "Entrega: pinzas abiertas con control",
    "handNeg": "Entrega: el hilo se extrae",
    "bringer": "Portadora",
    "taker": "Receptora",
    "mainJet": "Tobera principal",
    "relay": "Las toberas auxiliares soplan por grupos, solo donde está el hilo",
    "waterJet": "Tobera de agua",
    "beat": "Batido: el peine empuja la trama contra el borde del tejido",
    "insertion": "Inserción de trama",
    "fabric": "Tejido",
    "reed": "Peine",
    "back": "↑ atrás:",
    "shafts": "lizos",
    "front": "↓ delante:",
    "cloth": "tejido"
   },
   "steps": [
    "1 · Calada abierta, peine atrás: empieza la inserción",
    "2 · Trama en camino",
    "3 · Centro de la calada (pinza: entrega)",
    "4 · Trama en camino al otro lado",
    "5 · Inserción terminada",
    "6 · El peine avanza",
    "7 · Batido contra el borde del tejido",
    "8 · Peine atrás, cambio de calada"
   ],
   "zoom": {
    "msg": [
     "1 · La portadora trae el hilo, la receptora sale a su encuentro",
     "2 · Las cabezas se solapan, la pinza receptora se cierra sobre el hilo",
     "3 · Positiva: el abridor levanta la pinza portadora y el hilo queda libre",
     "3 · Negativa: la pinza portadora sigue cerrada y la receptora extrae el hilo contra la fuerza del muelle",
     "4 · La receptora lleva la trama al otro lado, la portadora vuelve vacía"
    ],
    "spring": "Muelle",
    "opener": "Abridor de pinza",
    "pull": "Tirón del hilo",
    "step": "Paso {n} de 4",
    "pos": "Positiva (p. ej. Dornier P2, pinzas rígidas): las pinzas se abren y cierran mecánicamente en momentos fijos. El hilo no se extrae, sino que se entrega, cuidando el vidrio, el carbono, la aramida y los hilos de fantasía.",
    "neg": "Negativa (casi todas las pinzas de cinta flexible): no hay abridor. El hilo pasa de la portadora a la receptora solo por la tensión del hilo y la fuerza de sujeción; sencillo y rápido, pero los hilos lisos, rígidos o delicados pueden perderse o romperse."
   },
   "heatHead": [
    "Sistema",
    "Rendimiento de inserción",
    "Ancho máx.",
    "Gama de hilos",
    "Colores de trama",
    "Energía (5 = poca)",
    "Orillo/desperdicio (5 = poco)"
   ],
   "ituHead": [
    "Sistema",
    "Ancho de trabajo (m)",
    "Velocidad (rpm)",
    "Rendimiento de inserción (m/min)"
   ],
   "itu": [
    [
     "Lanzadera",
     "1,88–4,14",
     "60–160",
     "357–525"
    ],
    [
     "Proyectil",
     "1,90–5,45",
     "250–400",
     "600–1250"
    ],
    [
     "Pinza rígida",
     "1,60–4,00",
     "200–420",
     "hasta 1100–1300 (dos fases)"
    ],
    [
     "Pinza flexible",
     "1,80–4,20",
     "200–500",
     "550–1150"
    ],
    [
     "Chorro de aire",
     "1,40–3,60",
     "400–700",
     "650–1600"
    ],
    [
     "Chorro de agua",
     "1,50–2,30",
     "800",
     "1000–1700"
    ]
   ],
   "speeds": [
    "Lanzadera (primera máquina)",
    "Proyectil P7300HP (1570 m/min ÷ 3,9 m)",
    "Pinza Picanol Ultimax (industrial)",
    "Chorro de agua Toyota LWT810 (sin verificar)",
    "Chorro de aire Picanol OmniPlus-i (estrecho)"
   ]
  },
  "schaft": {
   "titles": [
    "Maquinitas de lizos y excéntricas",
    "Formación de calada electrónica integrada",
    "Telares (selección)"
   ],
   "cards": [
    [
     [
      "Stäubli S3000 / S3200 (maquinita rotativa)",
      "Con control electrónico, montada abajo o arriba en telares de agua, aire y pinzas; > 20 000 unidades en uso (2017). Stäubli inventó el principio rotativo."
     ],
     [
      "Stäubli S3292",
      "Nueva maquinita de alta velocidad, presentada en ITME India 2026."
     ],
     [
      "Stäubli S2688 / S4080",
      "Maquinitas de calada abierta para tejidos técnicos pesados y fondo de alfombras."
     ],
     [
      "Excéntricas Stäubli S1691/92, S1792",
      "Para ligamentos sencillos en máquinas de alto rendimiento."
     ]
    ],
    [
     [
      "Picanol SmartShed / SmartShed Pro",
      "Cada lizo tiene su propio servomotor (8, 12 o 16 lizos); 8–16 servoejes de Lenze, refrigerados por líquido. Cambio de ligamento sin modificar la mecánica."
     ],
     [
      "Toyota E-shed / C-shed",
      "Formación de calada electrónica propia desde 2000, ofrecida en el JAT910."
     ],
     [
      "Dornier SyncroDrive",
      "Formación de calada con motor propio (6–8 kW), acoplada electrónicamente al telar en lugar de por eje cardán: sin marcas de arranque."
     ]
    ],
    [
     [
      "Pinza",
      "Picanol Ultimax/GTMax · Itema R9500-2/Hercules · Dornier P2 · SMIT GS980/2FAST · proveedores chinos"
     ],
     [
      "Chorro de aire",
      "Picanol OmniPlus-i · Toyota JAT910 · Tsudakoma ZAX · Itema A9500-2 · Dornier A2"
     ],
     [
      "Chorro de agua",
      "Tsudakoma ZW · Toyota LWT810 · muchos proveedores chinos"
     ],
     [
      "Proyectil",
      "Itema P7300HP (único proveedor)"
     ]
    ]
   ]
  },
  "jac": {
   "hkL": "Número de platinos por máquina (datos de fabricantes, escala logarítmica)",
   "hk": [
    "Stäubli UNIVALETTE",
    "GITEC Grosse (EJP/EJT)",
    "Bonas Ji",
    "Bonas Si",
    "Stäubli SX (ejemplo)"
   ],
   "hkNote": "Bonas Ji: límite superior 17 280 según Vandewiele, 5760 según un informe de feria",
   "head": [
    "Fabricante",
    "Sede",
    "Modelos",
    "Técnica / particularidad",
    "Fuente"
   ],
   "rows": [
    [
     "Stäubli",
     "Grupo suizo, entre otros Stäubli Bayreuth (DE)",
     "LX PRO, LXL PRO, LXXL PRO, SX PRO, N4L, UNIVALETTE; arcadas",
     "Módulos de selección MX-PRO, calada abierta de doble alza; CX 860 (1987) según Stäubli la primera Jacquard electrónica; UNIVALETTE con accionamiento propio sincronizado electrónicamente"
    ],
    [
     "Bonas (grupo Vandewiele)",
     "BE (marca/Kortrijk)",
     "Si, Ji, H3D, MDA02",
     "Microselector 100 % electrónico con diagnóstico completo; Si es muy compacta (12–36 cuchillas de profundidad); H3D para tejidos 3D y multicapa"
    ],
    [
     "GITEC Grosse (grupo Hisun)",
     "DE (Ulm) / CN",
     "EJP-4, EJT-4 (rizo), UniShed 2",
     "fundada en 1878 en Greiz; UniShed: sin arcada, un muelle de lámina por hilo de urdimbre, para airbags"
    ],
    [
     "Telares para Jacquard",
     "–",
     "Picanol (cardán o independiente), Itema A9500-2/R9500-2, Dornier P2/A2 con SyncroDrive, SMIT GS980 (Jacquard jumbo), Vandewiele terciopelo (VSi)",
     "Jacquard accionada por eje cardán o con motor propio; ver Diferencias"
    ]
   ],
   "note": "Contradicción en las fuentes: Bonas sitúa el lanzamiento de la máquina Jacquard electrónica en la ITMA de Milán de 1983; Stäubli califica su CX 860 de 1987 como la primera máquina Jacquard de control electrónico del mundo. También el número de platinos de la Bonas Ji se indica de forma distinta (hasta 5760 o hasta 17 280)."
  },
  "wil": {
   "seg": [
    "Wilton de varillas",
    "Doble pieza (face-to-face)",
    "Axminster"
   ],
   "cards": {
    "rute": [
     [
      "Principio",
      "Los hilos de pelo pasan sobre varillas de acero que se introducen transversalmente. Al retirarlas, una cuchilla en el extremo corta el bucle (Wilton, pelo cortado); sin cuchilla queda el bucle (Bruselas)."
     ],
     [
      "Color",
      "Los colores de pelo no necesarios quedan «muertos» en el tejido de fondo: más caro, pero muy denso. Normalmente 1 de 5 colores por mechón."
     ],
     [
      "Trama",
      "Clásicamente con lanzadera; la altura de la varilla limita la altura del pelo y la velocidad."
     ]
    ],
    "f2f": [
     [
      "Principio",
      "Dos tejidos de fondo superpuestos; el hilo de pelo oscila entre ambos. Una cuchilla corta en el centro: dos alfombras a la vez."
     ],
     [
      "Trama",
      "Doble pinza (una por tejido de fondo) o triple pinza: la del centro inserta una trama auxiliar alrededor de la cual se forman bucles, y se retira de nuevo."
     ],
     [
      "Rendimiento",
      "Hasta 250 rpm (Vandewiele RCF), anchos de hasta 5,2–5,3 m; varias veces la producción del telar de varillas."
     ]
    ],
    "axm": [
     [
      "Principio",
      "Cada mechón se corta e inserta por separado: pinzas (en forma de pico) o cadena de carretes."
     ],
     [
      "Color",
      "Todo el pelo está en la superficie; el Axminster de carretes permite prácticamente colores ilimitados, el de pinzas aprox. 1 de 8."
     ],
     [
      "Máquina",
      "Vandewiele MAX91: alta velocidad, 16 marcos de color."
     ]
    ]
   },
   "svg": {
    "ground": "Tejido de fondo (urdimbre + trama)",
    "cutMsg": "La varilla se retira lateralmente: la cuchilla corta los bucles",
    "cutPile": "← pelo cortado (Wilton)",
    "loops": "Bucles sobre varillas (sección) →",
    "knife": "La cuchilla separa las dos alfombras",
    "upper": "alfombra superior (dorso arriba), trama de la pinza superior",
    "lower": "alfombra inferior, trama de la pinza inferior",
    "twoCarpets": "← dos alfombras de pelo terminadas",
    "pendulum": "El hilo de pelo oscila entre los tejidos de fondo →",
    "grip1": "La pinza coloca el mechón",
    "grip2": "cortado en el fondo",
    "each": "cada mechón por separado, todo el pelo en la superficie, sin pelo muerto en el dorso"
   },
   "step": "un paso = ¼ de hilera de pelo",
   "head": [
    "Fabricante",
    "Procedimiento",
    "Modelos",
    "Datos / particularidad",
    "Fuente"
   ],
   "rows": [
    [
     "Vandewiele (Van de Wiele)",
     "Doble pieza, doble pinza",
     "RCF, RCE2+, SRE2+",
     "RCF hasta 250 rpm, 3/4/5 m, Fast Creel con bobinas fijas; RCE2+ hasta 5,2 m; SRE2+ shaggy hasta 2×70 mm, también césped artificial"
    ],
    [
     "Vandewiele",
     "Doble pieza, triple pinza",
     "USF, UCE3+, HCE3+, RCE3+",
     "Efectos de pelo cortado, bucle y tejido plano a la vez; HCE3+ imita alfombras anudadas a mano, pelo desde 3,5 mm"
    ],
    [
     "Vandewiele",
     "Pelo simple, doble pinza",
     "LCE2+",
     "bucles cortos/largos, tejido plano, aspecto sisal"
    ],
    [
     "Vandewiele",
     "Wilton de varillas",
     "AWE1+",
     "Bucle y/o corte, 2,20 / 2,70 / 4 m"
    ],
    [
     "Vandewiele",
     "Axminster",
     "MAX91",
     "16 marcos de color, alta velocidad"
    ],
    [
     "Stäubli (Schönherr)",
     "Doble pieza",
     "ALPHA 500/560 UNIVERSAL, XHDC",
     "hasta 5,3 m, auténtica Jacquard de 3 posiciones (Stäubli), dispositivo de corte servo, refrigeración líquida; fabricada en Bayreuth y Chemnitz"
    ],
    [
     "Stäubli (Schönherr)",
     "Pelo simple en bucle",
     "ALPHA 500 SINGLELOOP",
     "según Stäubli tres veces más productiva que un telar de varillas"
    ],
    [
     "Stäubli (Schönherr)",
     "Pinza simple o doble",
     "ALPHA 500 LEANTEC",
     "Shaggy, césped artificial, tejido crudo para estampar"
    ],
    [
     "Picanol",
     "Alfombra plana",
     "Ultimax (Flat carpet, ITMA 2023)",
     "Telar de pinzas para alfombras de tejido plano, sin pelo"
    ]
   ],
   "note": "Una comparación de productividad entre fabricantes debe leerse con cautela: Van de Wiele indica para el telar de triple pinza UCL83 hasta seis veces la producción de un telar de varillas, Stäubli tres veces para la ALPHA 500 SINGLELOOP; son máquinas y artículos distintos."
  },
  "diff": {
   "follow": "Consecuencia:",
   "cards": [
    [
     "Pinza: entrega positiva vs. negativa",
     "Dornier entrega de forma positiva con pinzas rígidas: las pinzas se abren mecánicamente. Casi todos los demás usan cintas flexibles con entrega negativa. Itema (Hercules) puede convertirse entre ambas.",
     "Positiva: cuida vidrio, carbono, aramida, hilos de fantasía. Negativa: más rápida y sencilla."
    ],
    [
     "Pinza: guiada vs. «Free Flight»",
     "Itema apuesta por pinzas SK guiadas con ganchos en la calada; SMIT promociona la pinza free flight más rápida, que no necesita ganchos guía.",
     "El free flight cuida urdimbres sensibles (seda, estambre); la guía da más seguridad a alta velocidad."
    ],
    [
     "Chorro de aire: la lucha por el aire comprimido",
     "Las toberas auxiliares consumen hasta el 80 % del aire. Con el JAT910, Toyota reduce la presión un 10 % y el consumo un 20 %; Picanol aporta AirStream (+100 rpm) y EcoBoost (−1,5 kW).",
     "En el chorro de aire, los costes de energía suelen pesar más que el precio de compra."
    ],
    [
     "Proyectil: el telar ancho",
     "Solo Itema sigue fabricando telares de proyectil. Son anchos (hasta 655 cm), económicos y robustos para hilos de cinta.",
     "Para geo/agrotextiles y dorso de alfombras; apenas relevante ya para la moda."
    ],
    [
     "Chorro de agua: solo sintéticos",
     "El agua arrastra el hilo con más eficacia que el aire, pero tejido mojado y tratamiento del agua; las fibras celulósicas quedan excluidas.",
     "Artículos de masa asiáticos en PES/PA; casi solo Japón y China como fabricantes."
    ],
    [
     "Formación de calada: acoplada mecánicamente vs. accionamiento propio",
     "Clásicamente el telar acciona la maquinita o la Jacquard mediante un eje cardán. Picanol SmartShed (servo por lizo), Dornier SyncroDrive, la Jacquard motorizada sin cardán de Itema y Stäubli UNIVALETTE lo desacoplan electrónicamente.",
     "Menos marcas de arranque, cambios de ligamento más rápidos, la Jacquard puede detenerse suavemente."
    ],
    [
     "Jacquard: técnica de selección",
     "Bonas selecciona con un microselector 100 % electrónico (diagnóstico completo), Stäubli con módulos MX-PRO. Grosse UniShed prescinde por completo de la arcada: un muelle de lámina por hilo de urdimbre.",
     "UniShed para tejidos de airbag; Bonas Si para números de platinos muy altos en poco espacio."
    ],
    [
     "Alfombra: varillas vs. doble pieza",
     "El Wilton de varillas hace una alfombra, necesita varillas y es lento. La doble pieza hace dos alfombras a la vez con dos o tres pinzas.",
     "Hoy domina la doble pieza; las varillas se mantienen para ciertas calidades de bucle/corte (Vandewiele AWE1+)."
    ]
   ]
  },
  "mx": {
   "legend": [
    "documentado en las fuentes",
    "solo de listas de estudios de mercado",
    "Las celdas vacías significan «aquí no documentado»."
   ],
   "head": [
    "Fabricante",
    "País"
   ],
   "cols": [
    "Pinza",
    "Aire",
    "Agua",
    "Proyectil",
    "Lizos/excéntrica",
    "Máquina Jacquard",
    "Alfombra doble pieza",
    "Wilton de varillas",
    "Axminster"
   ],
   "firms": [
    "Picanol",
    "Itema",
    "Lindauer Dornier",
    "Toyota Industries",
    "Tsudakoma",
    "SMIT (Santex Rimar)",
    "Stäubli (incl. Schönherr)",
    "Vandewiele / Bonas",
    "GITEC Grosse",
    "RIFA",
    "Jingwei · Haijia · Tongda · Huasense"
   ],
   "lkL": "Más en la Knowledge Base",
   "links": [
    [
     "Tejeduría con lizos",
     "Lizos, remetido y programa de lizos: cómo los lizos crean el ligamento."
    ],
    [
     "Ligamentos",
     "Patrón, tafetán, sarga y raso, y dibuje su propio ligamento."
    ],
    [
     "Tejeduría Jacquard",
     "Cada hilo de urdimbre levantado por separado: cómo teje dibujos una máquina Jacquard."
    ],
    [
     "Alfombra Wilton",
     "Alfombra de pelo tejida: varillas, pelo cortado y en bucle, elección de color Jacquard."
    ]
   ]
  }
 },
 "zh": {
  "ui": {
   "eyebrow": "Knowledge Base · 机织",
   "h1": "多臂、提花和威尔顿织造：机器、制造商、引纬",
   "lead": "织机的核心由两个系统组成：开口机构（踏盘、多臂机或提花机——决定花型自由度）和引纬（有梭、片梭、剑杆、喷气或喷水——决定速度、幅宽和适用纱线范围）。本页以动画展示这两部分，按织造类型列出制造商，并说明各机器真正的差别。威尔顿（绒头地毯）部分还介绍起绒杆和双层（面对面）技术。",
   "note": "调研时间：2026年11月。制造商数据多为宣传值或最高值；型号名称和技术参数可能变化。",
   "sources": "资料来源",
   "open": "打开模块",
   "loc": "none",
   "prev": "◀ 上一步",
   "next": "下一步 ▶",
   "play": "▶ 播放",
   "pause": "暂停",
   "st": {
    "h": "厂商",
    "p": "媒体",
    "m": "名录"
   },
   "stLegend": "依据：厂商 = 制造商资料 · 媒体 = 专业媒体/教学资料 · 名录 = 仅来自市场研究名单"
  },
  "scenes": [
   {
    "k": "开口",
    "title": "多臂还是提花：开口方式决定花型",
    "text": "左侧显示每次引纬时哪些经纱被提起，右侧是形成的织物。用综框时，许多经纱挂在同一个综框上——花型在少数几根纱后就重复。用提花时，每根经纱都由一根竖钩单独控制。"
   },
   {
    "k": "引纬",
    "title": "五种引纬方式",
    "text": "梭口俯视图：纬纱（橙色）横穿经纱（蓝色）引入——在后摆的钢筘前方，即钢筘与织口之间。随后钢筘向前摆动，把纬纱打向织口。动画已放慢，速度不按比例——下方条形图显示真实最高值。"
   },
   {
    "k": "多臂织造",
    "title": "多臂织造：机器和制造商",
    "text": "多臂织造中，织造厂把一台织机（剑杆、喷气、喷水或片梭）与综框开口机构组合使用。市场分为两部分：一边是织机制造商，另一边是多臂机和踏盘专业厂商——首先是史陶比尔（Stäubli）。"
   },
   {
    "k": "提花织造",
    "title": "提花织造：机器和制造商",
    "text": "提花机安装在织机上方；每根竖钩通过一根通丝提起一根或几根经纱。竖钩数决定每个花回中可单独控制的经纱数。下面的织机通常是剑杆织机或喷气织机。"
   },
   {
    "k": "威尔顿织造",
    "title": "威尔顿织造：起绒杆、双层、阿克明斯特",
    "text": "威尔顿指机织绒头地毯，其绒头纱始终在地组织中连续运行，并按控制被带到表面。传统上用起绒杆（钢丝）实现，如今主要采用双层（面对面）工艺。阿克明斯特作为对比一并介绍。"
   },
   {
    "k": "差异",
    "title": "各机器之间的显著差异",
    "text": "各制造商在技术上的不同解决方案——以及这对纱线、产品和成本意味着什么。"
   },
   {
    "k": "制造商矩阵",
    "title": "制造商矩阵",
    "text": "根据本页资料来源，哪家制造商提供哪种引纬方式、开口机构和地毯技术。"
   }
  ],
  "kpis": [
   [
    "1350",
    "纬/分钟：窄幅必佳乐 OmniPlus-i 喷气织机"
   ],
   [
    "31104",
    "竖钩：单台 Bonas Si 提花机"
   ],
   [
    "1570 m/min",
    "片梭织机 P7300HP 的引纬率"
   ],
   [
    "5.3 m",
    "史陶比尔/Schönherr ALPHA 500 地毯织机的幅宽"
   ],
   [
    "最高 6×",
    "双层地毯织机（Van de Wiele UCL83）相对起绒杆织机的产量"
   ]
  ],
  "fach": {
   "seg": {
    "ex": "踏盘（4 片综）",
    "sch": "多臂机（8 片综）",
    "jac": "提花（每根纱单独控制）"
   },
   "svg": {
    "weaveCap": "织物：蓝 = 经纱在上，橙 = 纬纱在上",
    "shafts4": "4 片综——踏盘：固定顺序",
    "shafts8": "8 片综——多臂机：可自由编程，但第 e 根纱挂在第 e mod 8 片综上",
    "jacHead": "提花机——每根纱一根竖钩",
    "jacCap": "通丝：提起（橙）或落下（灰）——每纬自由选择",
    "pick": "第 {n} 纬 / 共 {total} 纬"
   },
   "cards": {
    "ex": [
     [
      "原理",
      "凸轮（踏盘）按固定的内置顺序带动少数几片综框。"
     ],
     [
      "局限",
      "只能织简单、短循环的组织（平纹、斜纹）；换花型就要更换踏盘。"
     ],
     [
      "应用",
      "高速喷气和喷水织机上的大批量产品；史陶比尔踏盘 S1691/92、S1792。"
     ]
    ],
    "sch": [
     [
      "原理",
      "多臂机可自由编程地提起每片综框——如今为电子控制。"
     ],
     [
      "局限",
      "同一片综上的所有经纱动作相同。超过约 24 片综时前后排列过深；花回仍然较小。"
     ],
     [
      "应用",
      "衬衫、床品、牛仔布、产业用织物；例如史陶比尔 S3000/S3200、必佳乐 SmartShed。"
     ]
    ],
    "jac": [
     [
      "原理",
      "每根竖钩单独控制一根（或几根）经纱——从数百组到超过 30000 组独立单元。"
     ],
     [
      "局限",
      "通丝装置更贵、更高，准备时间更长；但可在全幅织出任意图案。"
     ],
     [
      "应用",
      "家具布、锦缎、商标、带图案毛巾、OPW 安全气囊、地毯。"
     ]
    ]
   }
  },
  "ins": {
   "lbl": {
    "how": "工作原理",
    "figs": "关键数据",
    "pro": "优点",
    "con": "缺点",
    "when": "何时选用？",
    "mk": "制造商和型号",
    "zoom": "放大镜：梭口中央的交接（大幅放大、放慢）",
    "cmpT": "一览对比",
    "cmpN": "1（弱）到 5（强）的定性评级，依据本页资料来源得出——不是测量值。“能耗”和“布边/废料”中 5 表示消耗少或废料少。点击某行可打开该系统。",
    "ituL": "教科书数值（ITU 讲义，1980 年代）",
    "ituN": "较旧的数值，用于说明数量级；如今的机器更快（见下方条形图）。",
    "spL": "资料中的最高速度（纬/分钟或转/分钟）",
    "spN": "数值来自不同来源和条件（宣传最高值、工业速度、幅宽）。喷水：仅来自一份学生报告（丰田 LWT810）——未经核实。片梭织机通常以 m/min 表示；条形图按 3.9 m 幅宽换算 1570 m/min。"
   },
   "head": [
    "制造商",
    "国家",
    "型号",
    "特点",
    "依据"
   ],
   "sys": [
    {
     "n": "有梭",
     "de": "历史方式：装有纬纱管的梭子来回飞行",
     "pro": [
      "真正的封闭布边——纬纱从随梭飞行的纱管上退绕。",
      "机构简单、坚固。"
     ],
     "con": [
      "梭子很重（棉纬时约 450 g）——限制速度和幅宽。",
      "纬纱只在机器周期的一小部分时间内引入。",
      "噪音高达约 110 dB。",
      "需不断换纱管，纱线须重新卷绕成纡子。"
     ],
     "when": "仅用于需要真正有梭布边的细分领域。",
     "how": [
      "梭子内装一个纬纱管（纡子）。",
      "投梭机构把梭子打过梭口；在另一侧制动，并为下一纬打回。",
      "纬纱从随梭飞行的纱管退绕——形成真正的封闭布边。",
      "运动质量大限制了转速；纱管须不断更换。"
     ],
     "figs": [
      [
       "≈ 140",
       "纬/分钟：据必佳乐，第一台（有梭）织机"
      ],
      [
       "1924",
       "丰田 G 型：不停车换梭"
      ]
     ],
     "mk": [
      [
       "（历史）丰田、必佳乐等众多厂商",
       "–",
       "有梭织机",
       "如今仅限细分领域；传统威尔顿用梭子引纬"
      ]
     ],
     "note": "当今所有工业织造方式都是“无梭”的：纬纱从固定的供纬筒子上退出。"
    },
    {
     "n": "片梭",
     "de": "片梭：小型钢制夹纱器把纬纱射过梭口",
     "pro": [
      "能耗低。",
      "幅宽很大（最高 655 cm）——也可多幅并织。",
      "片梭小、梭口小：经纱断头少。",
      "适用纱线范围广，从棉、毛、黄麻到扁丝；4–6 种纬纱颜色。"
     ],
     "con": [
      "折入边：两侧各留约 15 mm 纬纱头并折入——产生废料，布边较厚。",
      "转速低于喷气（教科书 250–400 转/分钟）。",
      "带片梭回送的复杂机构；只剩一家供应商。"
     ],
     "when": "宽幅产业用织物、扁丝、土工/农用织物、地毯底布。",
     "how": [
      "小片梭（夹纱器）夹住来自固定供纬筒子的纱头。",
      "扭杆投梭把它沿导梭片射过梭口。",
      "在另一侧被制动，打开钳口放出纬纱。",
      "输送带在经纱下方把多个片梭送回；多个片梭同时循环。"
     ],
     "figs": [
      [
       "1570 m/min",
       "P7300HP 最高引纬率"
      ],
      [
       "655 cm",
       "P7300HP V8 最大幅宽"
      ],
      [
       "> 150000",
       "已售苏尔寿片梭织机（制造商 2002 年数据）"
      ],
      [
       "低",
       "能耗——宽幅产业用织物的优势"
      ]
     ],
     "mk": [
      [
       "Itema（原苏尔寿纺织）",
       "IT/CH",
       "P7300HP",
       "唯一的片梭织机制造商；2026 年生产从 Zuchwil 迁至 Colzate"
      ]
     ],
     "note": "对于扁丝（农用、土工织物、地毯底布），Itema 认为片梭优于所有其他引纬方式。"
    },
    {
     "n": "剑杆",
     "de": "剑杆：刚性杆或挠性带以机械方式把纬纱送过梭口",
     "pro": [
      "产品范围最广，据教学资料约 20 至 850 g/m²。",
      "可用多种纬纱颜色和花式纱；纬纱受机械引导，与其表面无关。",
      "积极式交接对玻璃纤维、碳纤维、芳纶更温和。",
      "可双纬引入。"
     ],
     "con": [
      "比喷气和喷水慢。",
      "刚性剑杆在侧面至少需要两倍织物幅宽的空间；挠性剑带在导向件上摩擦并磨损。",
      "消极式交接时纬纱可能在梭口中央脱落。"
     ],
     "when": "多色时装面料、家纺、提花家具布、毛巾、厚重产业用织物。",
     "v": [
      "双剑杆，消极式交接",
      "双剑杆，积极式交接（多尼尔）",
      "单剑杆"
     ],
     "how": [
      "送纬剑在布边处夹住纱头，运行到梭口中央。",
      "在那里接纬剑接过纬纱（Dewas：头对头；Gabler：纱圈）并拉到另一侧。",
      "消极式：仅靠纱线张力和夹持力完成交接。积极式：钳口由机械控制打开——对娇贵纱线更温和。",
      "挠性剑带卷绕在剑带轮上（占地小）；刚性剑杆需要机旁空间，但运行时不接触经纱。"
     ],
     "figs": [
      [
       "> 800",
       "纬/分钟（工业）：必佳乐 Ultimax"
      ],
      [
       "> 130000",
       "已售必佳乐剑杆织机"
      ],
      [
       "最高 6200 mm",
       "Itema Hercules 幅宽"
      ],
      [
       "320 / 1085 m/min",
       "多尼尔 P2，帆布，幅宽 339 cm"
      ]
     ],
     "mk": [
      [
       "必佳乐（Picanol）",
       "BE",
       "Ultimax、OptiMax-i Connect、GTMax、Supermax",
       "高性能；OptiMax-i 最高 540 cm，用于产业用织物"
      ],
      [
       "Itema",
       "IT",
       "R9500-2、Hercules、Galileo",
       "导向式 SK 剑杆；Hercules 可在积极/消极之间改装"
      ],
      [
       "林道多尼尔（Lindauer Dornier）",
       "DE",
       "P2",
       "刚性剑杆，中央积极式交接；玻璃纤维、碳纤维、芳纶"
      ],
      [
       "SMIT（Santex Rimar）",
       "IT",
       "GS980、2FAST、ONE",
       "“自由飞行”：梭口内无导钩的剑杆；ONE 只有一根剑杆"
      ],
      [
       "RIFA · Jingwei · Tongda · Huasense 等",
       "CN",
       "–",
       "市场研究中列为剑杆/织机制造商"
      ]
     ],
     "note": "据必佳乐，苏拉特织纱丽面料的剑杆织机运行速度约 410 转/分钟——“超过 800”是适合品种的最高值。"
    },
    {
     "n": "喷气",
     "de": "喷气：压缩空气把纬纱沿异形筘的筘槽送过",
     "pro": [
      "引纬率最高，几乎没有运动质量。",
      "购置成本低，占地少。",
      "操作简单。"
     ],
     "con": [
      "压缩空气昂贵；辅助喷嘴耗用其中高达 80 %。",
      "要求纱线均匀、质量好。典型疵点：缺纬、纱头卷缩、双纬。",
      "幅宽大时纬纱起毛，纱头解捻（尤其是转杯纱）。",
      "据教学资料，织物覆盖性不如片梭和剑杆。"
     ],
     "when": "大批量标准织物：衬衫、床品、牛仔布、毛巾、安全气囊。",
     "how": [
      "主喷嘴把纬纱从储纬器加速送入异形筘的筘槽。",
      "沿幅宽分布的辅助喷嘴分组接力吹气——使纬纱保持运动。",
      "末端由吸引或拉伸喷嘴拉直纬纱；布边被剪掉。",
      "非常快速简单，但压缩空气昂贵：辅助喷嘴耗用高达 80 % 的空气。"
     ],
     "figs": [
      [
       "1350",
       "转/分钟，窄幅必佳乐 OmniPlus-i Connect"
      ],
      [
       "−20 %",
       "丰田 JAT910 相比 JAT810 的耗气量"
      ],
      [
       "最高 80 %",
       "辅助喷嘴的耗气份额"
      ],
      [
       "−1.5 kW",
       "每台机器（必佳乐 EcoBoost）"
      ]
     ],
     "mk": [
      [
       "必佳乐（Picanol）",
       "BE",
       "OmniPlus-i Connect、TerryPlus-i Connect",
       "AirStream（+100 转/分钟）、EcoBoost、SmartShed"
      ],
      [
       "丰田自动织机",
       "JP",
       "JAT910",
       "i-SENSOR 检测梭口中的纬纱，E-shed"
      ],
      [
       "津田驹（Tsudakoma）",
       "JP",
       "ZAX001neo、ZAX9200i",
       "喷气和喷水同一来源"
      ],
      [
       "Itema",
       "IT",
       "A9500-2",
       "可配无万向轴的电机驱动提花机"
      ],
      [
       "林道多尼尔（Lindauer Dornier）",
       "DE",
       "A2",
       "用于产业用织物的喷气织机（安全气囊、降落伞）"
      ],
      [
       "RIFA · Jingwei · Tianyi Red Flag 等",
       "CN",
       "–",
       "市场研究"
      ]
     ],
     "note": "2025 年中国是喷气和喷水织机的最大买家；对华交付量分别下降 32 % 和 57 %（ITMF）。"
    },
    {
     "n": "喷水",
     "de": "喷水：水射流把纬纱带过梭口",
     "pro": [
      "长丝纱引纬率高。",
      "能耗低、安静、振动小、几乎无纬纱废料。",
      "对经纱温和——没有金属件摩擦。"
     ],
     "con": [
      "仅适用于疏水长丝（涤纶、锦纶、醋酯、玻璃纤维）——不能用棉、毛、粘胶。",
      "织物离机时是湿的，须烘干；废水须处理。",
      "最多只能两种纬纱颜色；幅宽较小。",
      "硬水可能导致生锈。"
     ],
     "when": "大批量合成长丝织物，主要在东亚。",
     "how": [
      "每纬由水泵把少量水压过喷嘴。",
      "水对纱线的摩擦力大于空气——一个喷嘴就够，无需辅助喷嘴。",
      "织物变湿，须烘干；水须处理。",
      "仅适用于不吸水的合成纱（涤纶、锦纶）——棉或粘胶不行。"
     ],
     "figs": [
      [
       "8–5600 dtex",
       "津田驹喷水织机适用纱线范围（锦纶至涤纶）"
      ],
      [
       "≈ 1200",
       "转/分钟，丰田 LWT810（未经核实）"
      ],
      [
       "−57 %",
       "2025 年对华交付量（ITMF）"
      ]
     ],
     "mk": [
      [
       "津田驹（Tsudakoma）",
       "JP",
       "ZW8100、ZW8200",
       "适用纱线范围广，也可织双层织物"
      ],
      [
       "丰田自动织机",
       "JP",
       "LWT810",
       "用于合成纤维的喷水织机"
      ],
      [
       "中国制造商",
       "CN",
       "–",
       "占世界市场最大份额（市场研究）"
      ]
     ],
     "note": "一份市场研究称，按台数计喷水织机是最常见的织机（超过 47 %）——这是中国合成纤维织造的结果。"
    }
   ],
   "svg": {
    "prestore": "储纬器",
    "strike": "投梭",
    "brake": "制动",
    "ret": "片梭在经纱下方回送",
    "single": "单剑杆空程穿过梭口，再把纬纱拉回",
    "handPos": "交接：钳口受控打开",
    "handNeg": "交接：纬纱被拉出",
    "bringer": "送纬剑",
    "taker": "接纬剑",
    "mainJet": "主喷嘴",
    "relay": "辅助喷嘴分组吹气，只在纬纱所在位置吹",
    "waterJet": "喷水嘴",
    "beat": "打纬：钢筘把纬纱推向织口",
    "insertion": "引纬",
    "fabric": "织物",
    "reed": "钢筘",
    "back": "↑ 后方：",
    "shafts": "综框",
    "front": "↓ 前方：",
    "cloth": "布面"
   },
   "steps": [
    "1 · 梭口打开，钢筘在后——开始引纬",
    "2 · 纬纱行进中",
    "3 · 梭口中央（剑杆：交接）",
    "4 · 纬纱向另一侧行进",
    "5 · 引纬完成",
    "6 · 钢筘向前摆动",
    "7 · 在织口打纬",
    "8 · 钢筘后退，梭口变换"
   ],
   "zoom": {
    "msg": [
     "1 · 送纬剑带来纬纱，接纬剑迎面而来",
     "2 · 剑头重叠，接纬剑钳口夹住纬纱",
     "3 · 积极式：开夹器抬起送纬剑钳口——纬纱被放开",
     "3 · 消极式：送纬剑钳口保持关闭——接纬剑克服弹簧力把纬纱拉出",
     "4 · 接纬剑把纬纱带到另一侧，送纬剑空程返回"
    ],
    "spring": "弹簧",
    "opener": "开夹器",
    "pull": "拉纱",
    "step": "第 {n} 步 / 共 4 步",
    "pos": "积极式（例如多尼尔 P2，刚性剑杆）：钳口在固定时刻由机械打开和关闭。纬纱不是被拉出，而是被交出——对玻璃纤维、碳纤维、芳纶和花式纱更温和。",
    "neg": "消极式（几乎所有挠性剑带）：没有开夹器。纬纱仅靠纱线张力和夹持力从送纬剑拉到接纬剑——简单快速，但光滑、刚硬或娇贵的纱线可能脱落或断裂。"
   },
   "heatHead": [
    "系统",
    "引纬率",
    "最大幅宽",
    "纱线范围",
    "纬纱颜色",
    "能耗（5 = 少）",
    "布边/废料（5 = 少）"
   ],
   "ituHead": [
    "系统",
    "工作幅宽 (m)",
    "转速 (转/分钟)",
    "引纬率 (m/min)"
   ],
   "itu": [
    [
     "有梭",
     "1.88–4.14",
     "60–160",
     "357–525"
    ],
    [
     "片梭",
     "1.90–5.45",
     "250–400",
     "600–1250"
    ],
    [
     "刚性剑杆",
     "1.60–4.00",
     "200–420",
     "最高 1100–1300（两相）"
    ],
    [
     "挠性剑杆",
     "1.80–4.20",
     "200–500",
     "550–1150"
    ],
    [
     "喷气",
     "1.40–3.60",
     "400–700",
     "650–1600"
    ],
    [
     "喷水",
     "1.50–2.30",
     "800",
     "1000–1700"
    ]
   ],
   "speeds": [
    "有梭（第一台机器）",
    "片梭 P7300HP（1570 m/min ÷ 3.9 m）",
    "剑杆 必佳乐 Ultimax（工业）",
    "喷水 丰田 LWT810（未核实）",
    "喷气 必佳乐 OmniPlus-i（窄幅）"
   ]
  },
  "schaft": {
   "titles": [
    "多臂机和踏盘",
    "集成式电子开口",
    "织机（部分）"
   ],
   "cards": [
    [
     [
      "史陶比尔 S3000 / S3200（回转式多臂机）",
      "电子控制，下置或上置于喷水、喷气和剑杆织机；在用超过 20000 台（2017 年）。回转原理由史陶比尔发明。"
     ],
     [
      "史陶比尔 S3292",
      "新型高速多臂机，在 2026 年印度 ITME 展上发布。"
     ],
     [
      "史陶比尔 S2688 / S4080",
      "用于厚重产业用织物和地毯底布的全开梭口多臂机。"
     ],
     [
      "史陶比尔踏盘 S1691/92、S1792",
      "用于高性能织机上的简单组织。"
     ]
    ],
    [
     [
      "必佳乐 SmartShed / SmartShed Pro",
      "每片综框都有自己的伺服电机（8、12 或 16 片综）；Lenze 提供 8–16 个液冷伺服轴。更换组织无需改动机械。"
     ],
     [
      "丰田 E-shed / C-shed",
      "自 2000 年起的自有电子开口，配于 JAT910。"
     ],
     [
      "多尼尔 SyncroDrive",
      "开口机构有独立电机（6–8 kW），以电子方式而非万向轴与织机耦合——无开车痕。"
     ]
    ],
    [
     [
      "剑杆",
      "必佳乐 Ultimax/GTMax · Itema R9500-2/Hercules · 多尼尔 P2 · SMIT GS980/2FAST · 中国供应商"
     ],
     [
      "喷气",
      "必佳乐 OmniPlus-i · 丰田 JAT910 · 津田驹 ZAX · Itema A9500-2 · 多尼尔 A2"
     ],
     [
      "喷水",
      "津田驹 ZW · 丰田 LWT810 · 众多中国供应商"
     ],
     [
      "片梭",
      "Itema P7300HP（唯一供应商）"
     ]
    ]
   ]
  },
  "jac": {
   "hkL": "每台机器的竖钩数（制造商数据，对数刻度）",
   "hk": [
    "史陶比尔 UNIVALETTE",
    "GITEC Grosse（EJP/EJT）",
    "Bonas Ji",
    "Bonas Si",
    "史陶比尔 SX（示例）"
   ],
   "hkNote": "Bonas Ji：上限据 Vandewiele 为 17280，据展会报道为 5760",
   "head": [
    "制造商",
    "所在地",
    "型号",
    "技术/特点",
    "依据"
   ],
   "rows": [
    [
     "史陶比尔（Stäubli）",
     "瑞士集团，含史陶比尔拜罗伊特（德国）",
     "LX PRO、LXL PRO、LXXL PRO、SX PRO、N4L、UNIVALETTE；通丝装置",
     "MX-PRO 选针模块，复动式全开梭口；据史陶比尔，CX 860（1987）是第一台电子提花机；UNIVALETTE 带独立的电子同步驱动"
    ],
    [
     "Bonas（Vandewiele 集团）",
     "比利时（品牌/科特赖克）",
     "Si、Ji、H3D、MDA02",
     "100 % 电子微型选针器，全面诊断；Si 非常紧凑（刀深 12–36 把）；H3D 用于三维和多层织物"
    ],
    [
     "GITEC Grosse（Hisun 集团）",
     "德国（乌尔姆）/中国",
     "EJP-4、EJT-4（毛巾）、UniShed 2",
     "1878 年创立于格赖茨；UniShed：无通丝，每根经纱一片板簧——用于安全气囊"
    ],
    [
     "用于提花的织机",
     "–",
     "必佳乐（万向轴或独立驱动）、Itema A9500-2/R9500-2、多尼尔 P2/A2 配 SyncroDrive、SMIT GS980（大提花）、Vandewiele 丝绒（VSi）",
     "提花机由万向轴或独立电机驱动——见“差异”"
    ]
   ],
   "note": "资料来源存在矛盾：Bonas 称电子提花机于 1983 年米兰 ITMA 推出；史陶比尔则称其 1987 年的 CX 860 是世界上第一台电子控制提花机。Bonas Ji 的竖钩数说法也不一致（最高 5760 或最高 17280）。"
  },
  "wil": {
   "seg": [
    "起绒杆威尔顿",
    "双层（面对面）",
    "阿克明斯特"
   ],
   "cards": {
    "rute": [
     [
      "原理",
      "绒头纱绕过横向插入的钢制起绒杆。抽出时，杆端的刀片把纱圈割开（威尔顿，割绒）——没有刀片则保留纱圈（布鲁塞尔）。"
     ],
     [
      "颜色",
      "不需要的绒头颜色“沉”在地组织中——成本更高，但非常密实。每个绒簇通常从 5 种颜色中选 1 种。"
     ],
     [
      "引纬",
      "传统上用梭子；起绒杆高度限制绒头高度和速度。"
     ]
    ],
    "f2f": [
     [
      "原理",
      "上下两层地组织，绒头纱在其间往复。中间由刀片割开——一次织出两块地毯。"
     ],
     [
      "引纬",
      "双剑杆（每层地组织一根）或三剑杆：中间一根引入辅助纬，纱圈绕其形成，之后再抽出。"
     ],
     [
      "产量",
      "最高 250 转/分钟（Vandewiele RCF），幅宽最高 5.2–5.3 m；产量是起绒杆的数倍。"
     ]
    ],
    "axm": [
     [
      "原理",
      "每个绒簇单独剪切并植入——用夹持器（鸟嘴状）或纱管链。"
     ],
     [
      "颜色",
      "全部绒头都在表面；纱管式阿克明斯特几乎可用无限多种颜色，夹持式约 8 选 1。"
     ],
     [
      "机器",
      "Vandewiele MAX91：高速，16 个色架。"
     ]
    ]
   },
   "svg": {
    "ground": "地组织（经纱 + 纬纱）",
    "cutMsg": "起绒杆向侧面抽出——刀片割开纱圈",
    "cutPile": "← 割绒（威尔顿）",
    "loops": "绕在起绒杆上的纱圈（截面） →",
    "knife": "割刀把两块地毯分开",
    "upper": "上层地毯（背面朝上），纬纱来自上剑杆",
    "lower": "下层地毯，纬纱来自下剑杆",
    "twoCarpets": "← 两块成品绒头地毯",
    "pendulum": "绒头纱在两层地组织间往复 →",
    "grip1": "夹持器把剪好的绒簇",
    "grip2": "植入地组织",
    "each": "每个绒簇单独植入，全部绒头在表面——背面没有沉绒"
   },
   "step": "一步 = ¼ 绒头排",
   "head": [
    "制造商",
    "工艺",
    "型号",
    "参数/特点",
    "依据"
   ],
   "rows": [
    [
     "Vandewiele（Van de Wiele）",
     "双层，双剑杆",
     "RCF、RCE2+、SRE2+",
     "RCF 最高 250 转/分钟，3/4/5 m，Fast Creel 固定筒子纱架；RCE2+ 最高 5.2 m；SRE2+ 长毛绒最高 2×70 mm，也可织人造草坪"
    ],
    [
     "Vandewiele",
     "双层，三剑杆",
     "USF、UCE3+、HCE3+、RCE3+",
     "可同时织出割绒、圈绒和平织效果；HCE3+ 仿手工打结地毯，绒头 3.5 mm 起"
    ],
    [
     "Vandewiele",
     "单层绒，双剑杆",
     "LCE2+",
     "短/长纱圈、平织、剑麻外观"
    ],
    [
     "Vandewiele",
     "起绒杆威尔顿",
     "AWE1+",
     "圈绒和/或割绒，2.20 / 2.70 / 4 m"
    ],
    [
     "Vandewiele",
     "阿克明斯特",
     "MAX91",
     "16 个色架，高速"
    ],
    [
     "史陶比尔（Schönherr）",
     "双层",
     "ALPHA 500/560 UNIVERSAL、XHDC",
     "最高 5.3 m，真正的三位提花（史陶比尔），伺服割绒装置，液冷；在拜罗伊特和开姆尼茨制造"
    ],
    [
     "史陶比尔（Schönherr）",
     "单层圈绒",
     "ALPHA 500 SINGLELOOP",
     "据史陶比尔，生产率是起绒杆织机的三倍"
    ],
    [
     "史陶比尔（Schönherr）",
     "单剑杆或双剑杆",
     "ALPHA 500 LEANTEC",
     "长毛绒、人造草坪、印花用坯布"
    ],
    [
     "必佳乐（Picanol）",
     "平织地毯",
     "Ultimax（Flat carpet，ITMA 2023）",
     "用于平织地毯的剑杆织机，无绒头"
    ]
   ],
   "note": "制造商之间的生产率比较需谨慎看待：Van de Wiele 称三剑杆织机 UCL83 的产量最高可达起绒杆织机的六倍，史陶比尔称 ALPHA 500 SINGLELOOP 为三倍——这是不同的机器和产品。"
  },
  "diff": {
   "follow": "结果：",
   "cards": [
    [
     "剑杆：积极式与消极式交接",
     "多尼尔用刚性剑杆进行积极式交接——钳口由机械打开。几乎所有其他厂商用挠性剑带进行消极式交接。Itema（Hercules）可在两者之间改装。",
     "积极式：对玻璃纤维、碳纤维、芳纶、花式纱更温和。消极式：更快、更简单。"
    ],
    [
     "剑杆：导向式与“自由飞行”",
     "Itema 采用梭口内带导钩的导向式 SK 剑杆；SMIT 宣传其最快的自由飞行剑杆，无需导钩。",
     "自由飞行对敏感经纱（真丝、精纺毛纱）更温和；导向在高速下更安全。"
    ],
    [
     "喷气：压缩空气之争",
     "辅助喷嘴耗用高达 80 % 的空气。丰田 JAT910 将压力降低 10 %、耗气量降低 20 %；必佳乐推出 AirStream（+100 转/分钟）和 EcoBoost（−1.5 kW）。",
     "对喷气织机而言，能源成本往往比购置价更重要。"
    ],
    [
     "片梭：宽幅织机",
     "只有 Itema 仍在制造片梭织机。它们幅宽大（最高 655 cm）、节能，适合扁丝且坚固耐用。",
     "用于土工/农用织物和地毯底布；对时装已几乎无关。"
    ],
    [
     "喷水：仅限合成纤维",
     "水比空气更有效地牵引纬纱，但织物潮湿且需水处理；纤维素纤维无法使用。",
     "亚洲涤纶/锦纶大宗产品——制造商几乎只有日本和中国。"
    ],
    [
     "开口：机械耦合与独立驱动",
     "传统上由织机通过万向轴驱动多臂机或提花机。必佳乐 SmartShed（每片综一个伺服）、多尼尔 SyncroDrive、Itema 无万向轴的电机驱动提花机和史陶比尔 UNIVALETTE 以电子方式实现解耦。",
     "开车痕更少，更换组织更快，提花机可平稳停转。"
    ],
    [
     "提花：选针技术",
     "Bonas 用 100 % 电子微型选针器（全面诊断），史陶比尔用 MX-PRO 模块。Grosse UniShed 完全不用通丝：每根经纱一片板簧。",
     "UniShed 用于安全气囊织物；Bonas Si 用于小空间内极高的竖钩数。"
    ],
    [
     "地毯：起绒杆与双层",
     "起绒杆威尔顿一次织一块地毯，需要起绒杆，速度慢。双层工艺用两根或三根剑杆同时织两块地毯。",
     "如今双层工艺占主导；起绒杆仍用于某些圈绒/割绒品质（Vandewiele AWE1+）。"
    ]
   ]
  },
  "mx": {
   "legend": [
    "资料中有据可查",
    "仅来自市场研究名单",
    "空白表示“此处无据可查”。"
   ],
   "head": [
    "制造商",
    "国家"
   ],
   "cols": [
    "剑杆",
    "喷气",
    "喷水",
    "片梭",
    "多臂/踏盘",
    "提花机",
    "双层地毯",
    "起绒杆威尔顿",
    "阿克明斯特"
   ],
   "firms": [
    "必佳乐（Picanol）",
    "Itema",
    "林道多尼尔（Lindauer Dornier）",
    "丰田自动织机",
    "津田驹（Tsudakoma）",
    "SMIT（Santex Rimar）",
    "史陶比尔（含 Schönherr）",
    "Vandewiele / Bonas",
    "GITEC Grosse",
    "RIFA",
    "Jingwei · Haijia · Tongda · Huasense"
   ],
   "lkL": "Knowledge Base 中的相关内容",
   "links": [
    [
     "多臂/踏盘织造",
     "综框、穿综和提综程序：综框如何形成组织。"
    ],
    [
     "织物组织",
     "意匠图、平纹、斜纹和缎纹——还可以自己画组织。"
    ],
    [
     "提花织造",
     "每根经纱单独提升：提花机如何织出图案。"
    ],
    [
     "威尔顿地毯",
     "机织绒头地毯：起绒杆、割绒与圈绒、提花选色。"
    ]
   ]
  }
 }
};
