window.TEXTS = {
 "de": {
  "ui": {
   "eyebrow": "Knowledge Base · Stoffprüfung",
   "h1": "Stoffprüfung: messen, was ein Stoff aushält",
   "lead": "Bevor ein Stoff verkauft oder verarbeitet wird, prüft das Labor nach Normen, ob er hält, was er verspricht. Acht Szenen zeigen das Normklima, Höchstzugkraft und Weiterreissen, Scheuern nach Martindale, Pilling, Wasch- und Reibechtheit, Lichtechtheit und die Massänderung beim Waschen.",
   "note": "Schematische Darstellung. Prüfparameter stammen aus Normzusammenfassungen und Laborangaben (ISO 139, 13934, 13937, 12947, 12945, 105, 5077); Kurven, Farbverläufe und Einstufungen sind vereinfacht. Massgebend ist jeweils der Normtext.",
   "pause": "⏸ Pause",
   "play": "▶ Abspielen",
   "sl": {
    "rh": "Luftfeuchte",
    "meth": "Methode",
    "tear": "Verfahren",
    "cyc": "Touren",
    "grade": "Note",
    "fx": "Prüfung",
    "bw": "Lichtechtheit",
    "sh": "Massänderung"
   },
   "lkL": "Weiter in der Knowledge Base",
   "open": "Modul öffnen"
  },
  "scenes": [
   {
    "k": "Normklima",
    "title": "Erst konditionieren, dann prüfen",
    "text": "Textilfasern nehmen je nach Luftfeuchte unterschiedlich viel Wasser auf, und das verändert Masse, Festigkeit und Dehnung. Darum lagern die Proben vor jeder Prüfung im Normklima nach ISO 139, bis sich ihre Masse nicht mehr ändert, und werden im selben Klima geprüft. Mit dem Regler die Luftfeuchte ändern.",
    "facts": [
     [
      "Normklima",
      "20,0 °C und 65,0 % rF"
     ],
     [
      "Toleranz",
      "± 2 °C und ± 4 % rF"
     ],
     [
      "Alternativen",
      "23 °C / 50 % und 27 °C / 65 % (tropisch)"
     ],
     [
      "Gleichgewicht",
      "Wägen im Abstand von 2 h"
     ]
    ]
   },
   {
    "k": "Höchstzugkraft",
    "title": "Zugversuch: Streifen und Grab",
    "text": "Eine Zugprüfmaschine zieht die eingespannte Probe mit konstanter Geschwindigkeit auseinander, bis sie reisst. Aufgezeichnet wird die Kraft über der Dehnung. Beim Streifenversuch trägt die ganze Probenbreite, beim Grab-Versuch wird nur die Mitte einer breiteren Probe gefasst. Mit dem Regler die Methode wählen.",
    "facts": [
     [
      "Streifen",
      "ISO 13934-1"
     ],
     [
      "Grab",
      "ISO 13934-2"
     ],
     [
      "Ergebnis",
      "Höchstzugkraft in N"
     ],
     [
      "Richtungen",
      "Kette und Schuss getrennt"
     ]
    ]
   },
   {
    "k": "Weiterreissen",
    "title": "Wie leicht läuft ein Riss weiter?",
    "text": "Ein kleiner Schnitt oder Haken kann ein Kleidungsstück oder eine Plane ruinieren, wenn der Riss weiterläuft. Die Weiterreissprüfung startet darum an einem vorgegebenen Einschnitt. ISO 13937 kennt vier Verfahren: Pendel, Hose, Flügel und Zunge. Mit dem Regler das Verfahren wählen.",
    "facts": [
     [
      "Norm",
      "ISO 13937 Teile 1–4"
     ],
     [
      "Start",
      "vorgegebener Einschnitt"
     ],
     [
      "Ergebnis",
      "Weiterreisskraft in N"
     ],
     [
      "Achtung",
      "Verfahren nicht umrechenbar"
     ]
    ]
   },
   {
    "k": "Scheuern",
    "title": "Martindale: Touren bis zum Verschleiss",
    "text": "Im Martindale-Gerät reibt die runde Probe unter Last auf einem Standard-Wollgewebe. Die Bahn ist eine Lissajous-Figur, so wird jede Stelle aus allen Richtungen beansprucht. Gezählt werden die Touren, bis ein Endpunkt erreicht ist, etwa zwei gerissene Fäden. Mit dem Regler die erreichten Touren einstellen.",
    "facts": [
     [
      "Norm",
      "ISO 12947-2"
     ],
     [
      "Probe",
      "Ø etwa 38 mm"
     ],
     [
      "Last",
      "9 kPa oder 12 kPa"
     ],
     [
      "Ergebnis",
      "Touren bis zum Endpunkt"
     ]
    ]
   },
   {
    "k": "Pilling",
    "title": "Knötchen auf der Oberfläche",
    "text": "Durch Reibung lösen sich Faserenden aus dem Garn, verknäueln sich zu kleinen Knötchen und bleiben an der Oberfläche hängen. Nach einer genormten Beanspruchung wird die Probe mit Fotostandards verglichen und mit einer Note von 5 (keine Veränderung) bis 1 (sehr stark) bewertet. Mit dem Regler die Note ändern.",
    "facts": [
     [
      "Norm",
      "ISO 12945 Teile 1–4"
     ],
     [
      "Skala",
      "5 bis 1, halbe Noten"
     ],
     [
      "Beurteilung",
      "visuell mit Fotostandards"
     ],
     [
      "Häufig verlangt",
      "Maschenware ab Note 3–4"
     ]
    ]
   },
   {
    "k": "Farbechtheit",
    "title": "Waschen und Reiben",
    "text": "Farbechtheit beschreibt, wie gut eine Färbung oder ein Druck Gebrauch und Pflege übersteht. Bei der Waschechtheit verblasst die Probe und färbt auf mitgewaschene Begleitgewebe ab, bei der Reibechtheit färbt sie auf ein weisses Reibtuch ab. Bewertet wird mit dem Graumassstab von 5 bis 1. Mit dem Regler die Prüfung wählen.",
    "facts": [
     [
      "Waschen",
      "ISO 105-C06"
     ],
     [
      "Reiben",
      "ISO 105-X12"
     ],
     [
      "Graumassstab",
      "A02 Änderung · A03 Anbluten"
     ],
     [
      "Skala",
      "5 (keine) bis 1 (sehr stark)"
     ]
    ]
   },
   {
    "k": "Lichtechtheit",
    "title": "Xenonlicht und Blaumassstab",
    "text": "Probe und acht blaue Wollreferenzen werden gemeinsam mit Xenonlicht bestrahlt, das Tageslicht nachbildet. Ein Teil bleibt jeweils abgedeckt. Die Lichtechtheit ist die Nummer der Referenz, die ähnlich stark verblasst wie die Probe. Mit dem Regler die Lichtechtheit der Probe wählen.",
    "facts": [
     [
      "Norm",
      "ISO 105-B02"
     ],
     [
      "Lichtquelle",
      "Xenonbogen, Tageslicht D65"
     ],
     [
      "Skala",
      "Blaumassstab 1 bis 8"
     ],
     [
      "Stufen",
      "je etwa doppelt so lichtecht"
     ]
    ]
   },
   {
    "k": "Massänderung",
    "title": "Schrumpfen beim Waschen",
    "text": "Auf die konditionierte Probe werden Messmarken gesetzt. Nach dem Waschen und Trocknen nach ISO 6330 wird erneut gemessen, die Änderung wird in Prozent angegeben: minus für Schrumpfen, plus für Längung. Unten rechts stehen weitere häufige Prüfungen. Mit dem Regler die Massänderung einstellen.",
    "facts": [
     [
      "Normen",
      "ISO 5077, 3759, 6330"
     ],
     [
      "Marken",
      "mind. 350 mm Abstand"
     ],
     [
      "Ergebnis",
      "% Länge und Breite"
     ],
     [
      "Rundung",
      "auf 0,5 %"
     ]
    ]
   }
  ],
  "cv": {
   "rhN": "{n} % rF",
   "cycN": "{n} Touren",
   "gradeN": "Note {n}",
   "bwN": "Stufe {n}",
   "kl": {
    "chamber": "Klimaraum oder Klimaschrank",
    "temp": "20,0 °C",
    "rh": "Relative Luftfeuchte (% rF), grün: Toleranz 61–69 %",
    "ok": "im Normklima",
    "no": "ausserhalb des Normklimas",
    "regainT": "Feuchteaufnahme der Fasern (bezogen auf Trockenmasse)",
    "fibres": [
     "Wolle",
     "Viskose",
     "Baumwolle",
     "Polyamid",
     "Polyester"
    ],
    "regainN": "Richtwerte bei 65 % rF; der Verlauf bei anderer Luftfeuchte ist schematisch.",
    "alt": "ISO 139 erlaubt für besondere Fälle auch 23 °C / 50 % rF und für tropische Regionen 27 °C / 65 % rF. Konditioniert wird, bis sich die Masse bei Wägungen im Abstand von 2 Stunden kaum noch ändert.",
    "why": "Im Normklima sind die Ergebnisse vergleichbar, egal in welchem Labor geprüft wird. Wolle und Viskose nehmen viel Wasser auf, Polyester kaum. Viskose verliert im nassen Zustand deutlich an Festigkeit, Baumwolle wird nass eher fester.",
    "whyNo": "Ausserhalb der Toleranz sind die Messwerte nicht normgerecht: Masse, Festigkeit und Dehnung hygroskopischer Fasern weichen ab. Die Probe muss erneut im Normklima konditioniert werden."
   },
   "zg": {
    "cross": "Traverse fährt mit konstanter Geschwindigkeit (CRE)",
    "clamp25": "Klemmbacken nur 25 mm breit",
    "broke": "Probe gerissen",
    "eL": "Dehnung",
    "fL": "Kraft",
    "fmax": "Höchstzugkraft",
    "schem": "Kurve schematisch; Werte hängen von Material und Konstruktion ab.",
    "widthL": "PROBENBREITE",
    "gaugeL": "EINSPANNLÄNGE",
    "speedL": "GESCHWINDIGKEIT",
    "resL": "ERGEBNIS",
    "useL": "EINSATZ",
    "note": "Geprüft werden mehrere Proben je in Kett- und Schussrichtung. Beim Grab-Versuch hilft das seitliche, nicht eingespannte Gewebe mit; deshalb sind Streifen- und Grabwerte nicht direkt vergleichbar. Die amerikanische Grab-Norm ASTM D5034 arbeitet mit 300 mm/min statt 50 mm/min. Für Nähte gibt es mit ISO 13935 eigene Verfahren.",
    "nowF": "Kraft ≈ {f} N",
    "m": [
     {
      "n": "Streifen ISO 13934-1",
      "w": "50 mm",
      "l": "200 mm",
      "v": "100 mm/min",
      "r": "Höchstzugkraft in N und Höchstzugkraftdehnung in %",
      "u": "vor allem Gewebe"
     },
     {
      "n": "Grab ISO 13934-2",
      "w": "100 mm breite Probe",
      "l": "100 mm",
      "v": "50 mm/min",
      "r": "nur Höchstzugkraft in N",
      "u": "Gewebe; praxisnah, weil die Kraft wie im Gebrauch über einen Teil der Breite eingeleitet wird"
     }
    ]
   },
   "wr": {
    "pend": "Pendel",
    "fixed": "feste Klemme",
    "slit": "Einschnitt, Riss läuft nach oben",
    "tongue": "Zunge wird gegen den Rest gezogen",
    "wing": "abgewinkelte Flügel",
    "tipL": "Rissspitze",
    "pathL": "Weg",
    "forceL": "Kraft",
    "mean": "Mittel der Spitzen",
    "energyT": "Energieverlust des Pendels",
    "energy": "Je mehr Kraft das Weiterreissen braucht, desto mehr Energie verliert das fallende Pendel. Daraus wird die Weiterreisskraft berechnet.",
    "prL": "PRINZIP",
    "devL": "GERÄT",
    "hintL": "HINWEIS",
    "note": "Weiterreissen ist wichtig für Arbeitskleidung, Zelte, Planen und Ballonstoffe. Bei Geweben reissen die Fäden nacheinander, darum ist die Kraftkurve gezackt; ausgewertet werden die Spitzen. Die vier Verfahren liefern unterschiedliche Zahlen, ein Ergebnis gilt nur zusammen mit der Methode.",
    "m": [
     {
      "n": "Pendel nach Elmendorf (Teil 1)",
      "p": "Ein fallendes Pendel reisst eine eingeschnittene Probe schlagartig weiter (Einzelriss).",
      "d": "Ballistisches Pendelgerät",
      "h": "Schnell und weit verbreitet; misst die verbrauchte Energie."
     },
     {
      "n": "Hosenform (Teil 2)",
      "p": "Die Probe ist mittig eingeschnitten, die beiden «Hosenbeine» werden in Gegenrichtung gezogen (Einzelriss).",
      "d": "Zugprüfmaschine mit konstanter Dehngeschwindigkeit (CRE)",
      "h": "Nicht für Maschenware und elastische Gewebe geeignet."
     },
     {
      "n": "Flügelform (Teil 3)",
      "p": "Wie die Hosenform, aber mit abgewinkelten Schenkeln; der Riss läuft gezielter in der Mitte (Einzelriss).",
      "d": "Zugprüfmaschine (CRE)",
      "h": "Für Gewebe, bei denen der Riss bei der Hosenform seitlich ausweicht."
     },
     {
      "n": "Zungenform (Teil 4)",
      "p": "Zwei parallele Einschnitte bilden eine Zunge, die gegen den Rest der Probe gezogen wird; zwei Risse laufen zugleich (Doppelriss).",
      "d": "Zugprüfmaschine (CRE)",
      "h": "Ergibt höhere Werte als Einzelrissverfahren."
     }
    ]
   },
   "ms": {
    "abr": "Scheuermittel: Standard-Wollgewebe",
    "hold": "Probenhalter mit Probe (Ø 38 mm)",
    "lis": "Lissajous-Bahn (schematisch)",
    "classT": "Richtwerte für Möbelstoffe (Touren bis zum Endpunkt, 12 kPa)",
    "cl": [
     "dekorativ",
     "leicht",
     "Wohnbereich",
     "stark",
     "Objekt"
    ],
    "cld": [
     "Unter 10 000 Touren: Kissen, Dekoration, selten benutzte Möbel.",
     "10 000 bis 15 000 Touren: gelegentlich genutzte Sessel und Stühle.",
     "15 000 bis 25 000 Touren: normaler Wohngebrauch; manche Möbelhändler verlangen mindestens 20 000.",
     "25 000 bis 40 000 Touren: stark genutzte Sofas, Haushalte mit Kindern oder Haustieren.",
     "Ab 40 000 Touren: Büro, Gastronomie, Objektbereich; für Hotellobbys oft 50 000 und mehr."
    ],
    "panelT": "Martindale ISO 12947-2",
    "loadL": "LAST",
    "load": "9 kPa für Bekleidung und Heimtextilien, 12 kPa für Möbelstoffe, Arbeitskleidung und technische Textilien",
    "endL": "ENDPUNKT",
    "end": "zum Beispiel zwei gerissene Fäden bei Geweben, ein Loch bei Maschenware oder abgescheuerter Flor",
    "inspL": "ABLAUF",
    "insp": "Kontrolle in festgelegten Intervallen; Ergebnis ist die letzte Tourenzahl vor dem Endpunkt.",
    "req": "Ein Wert gilt nur zusammen mit der Last: 20 000 Touren bei 12 kPa sind anspruchsvoller als bei 9 kPa.",
    "note": "Die Einstufung stammt aus Hersteller- und Händlerangaben, nicht aus der Norm. In Nordamerika ist für Möbelstoffe zusätzlich der Wyzenbeek-Test verbreitet; seine «Double Rubs» lassen sich nicht in Martindale-Touren umrechnen."
   },
   "pi": {
    "light": "Darstellung schematisch; beurteilt wird die Oberfläche im Vergleich zu Fotostandards.",
    "scaleT": "Notenskala (ISO 12945)",
    "g": [
     "Keine Veränderung.",
     "Leichte Veränderung: Flaum oder erste Ansätze von Pills.",
     "Mässige Veränderung: deutliche Pills und Flaum.",
     "Deutliche Veränderung: viele Pills auf grosser Fläche.",
     "Sehr starke Veränderung: Pills auf der ganzen Fläche."
    ],
    "methT": "Verfahren",
    "meth": [
     [
      "Pillingbox: Proben auf Rohren taumeln in einem korkbelegten Kasten.",
      "TEIL 1"
     ],
     [
      "Modifizierter Martindale: Auswertung nach festen Stufen von 125 bis 7000 Touren.",
      "TEIL 2"
     ],
     [
      "Random Tumble: Proben wirbeln in einer Trommel mit Korkauskleidung.",
      "TEIL 3"
     ],
     [
      "Visuelle Beurteilung der Proben aller Verfahren.",
      "TEIL 4"
     ]
    ],
    "assess": "Beurteilt wird im Betrachtungsgerät mit flach einfallendem Licht (Blickwinkel 5–15°), die Probe neben unbehandeltem Stoff. Das Ergebnis wird auf eine halbe Note gerundet.",
    "note": "Bei Mischungen mit Polyester oder Polyacryl sind die Fasern so reissfest, dass die Knötchen nicht abfallen und sichtbar bleiben. Lange Fasern, mehr Garndrehung, Sengen und dichte Konstruktionen verringern Pilling. Viele Händler verlangen für Maschenware mindestens Note 3–4."
   },
   "fe": {
    "bath": "Behälter dreht im temperierten Wasserbad",
    "balls": "Stahlkugeln verstärken die Mechanik",
    "compT": "Verbundprobe 10 × 4 cm",
    "mf": [
     "Acetat",
     "Baumwolle",
     "Polyamid",
     "Polyester",
     "Polyacryl",
     "Wolle"
    ],
    "sewn": "an einer kurzen Kante mit dem Mehrfaserbegleitgewebe vernäht",
    "dyed": "Probe",
    "spec": "gefärbte Probe auf der Grundplatte",
    "finger": "Reibfinger mit weissem Baumwolltuch",
    "stroke": "Hub 104 mm · 10 Hübe in 10 s",
    "dry": "trocken",
    "wet": "nass",
    "clothT": "Reibtücher nach dem Test (Beispiel)",
    "gsC": "Graumassstab Farbänderung (A02)",
    "gsS": "Graumassstab Anbluten (A03)",
    "condL": "PRÜFBEDINGUNGEN",
    "evalL": "BEURTEILUNG",
    "note": "Note 5 bedeutet keine Veränderung bzw. kein Anbluten, Note 1 sehr starke; dazwischen gibt es halbe Noten. Viele Abnehmer akzeptieren ab Note 4, manche ab 3–4. Statt visuell kann auch farbmetrisch ausgewertet werden (ISO 105-A04/A05).",
    "m": [
     {
      "n": "Waschechtheit ISO 105-C06",
      "c": "Stahlbehälter mit Referenzwaschmittel, Temperatur je nach Prüfstufe; Einzel- (S) oder Mehrfachtest (M)",
      "e": "Farbänderung der Probe und Anbluten jedes Begleitstreifens",
      "d": "Ein Durchgang im Behälter ahmt eine oder mehrere Haushalts- bzw. Gewerbewäschen nach. Danach wird getrocknet: Wie stark ist die Probe verblasst, und welche Fasern im Begleitgewebe haben Farbe angenommen?"
     },
     {
      "n": "Reibechtheit ISO 105-X12",
      "c": "Reibfinger, 9 N Anpresskraft, 104 mm Hub, 10 Hübe in 10 s, trocken und nass",
      "e": "Anbluten des weissen Reibtuchs",
      "d": "Zeigt, ob unfixierter Farbstoff an der Oberfläche abfärbt, zum Beispiel dunkle Jeans auf einen hellen Sofabezug. Nass fällt das Ergebnis meist schlechter aus als trocken. Probe mindestens 50 × 140 mm."
     }
    ]
   },
   "li": {
    "lamp": "Xenonbogenlampe mit Filtern",
    "spec": "Probe",
    "exposed": "belichtet",
    "masked": "abgedeckt",
    "refT": "Blaumassstab 1–8 wird zusammen mit der Probe belichtet",
    "expo": "Belichtungsdauer",
    "result": "Lichtechtheit {n}",
    "sc": [
     "Die Probe verblasst wie Referenz 1: sehr gering.",
     "Die Probe verblasst wie Referenz 2: gering.",
     "Die Probe verblasst wie Referenz 3: mässig.",
     "Die Probe verblasst wie Referenz 4: ziemlich gut.",
     "Die Probe verblasst wie Referenz 5: gut.",
     "Die Probe verblasst wie Referenz 6: sehr gut.",
     "Die Probe verblasst wie Referenz 7: vorzüglich.",
     "Die Probe verblasst wie Referenz 8: hervorragend."
    ],
    "panelT": "ISO 105-B02",
    "srcL": "LICHTQUELLE",
    "src": "Xenonbogen, gefiltert auf ein Tageslichtspektrum (D65)",
    "ruleL": "BLAUMASSSTAB",
    "rule": "Acht blau gefärbte Wollgewebe von 1 (sehr geringe) bis 8 (sehr hohe Lichtechtheit); jede Stufe ist etwa doppelt so lichtecht wie die vorherige.",
    "methL": "AUSWERTUNG",
    "meth": "Der Kontrast zwischen belichtetem und abgedecktem Teil wird mit dem Graumassstab beurteilt und mit den Referenzen verglichen. In Amerika sind die Referenzen L2–L9 üblich; die Ergebnisse sind nicht austauschbar.",
    "note": "Lichtechtheit zählt bei Vorhängen, Markisen, Autositzen und Outdoor-Textilien. Weil hohe Stufen sehr lange Belichtung brauchen, genügt in der Qualitätskontrolle oft ein Bestanden/Nicht-bestanden-Test gegen eine einzelne Referenz. Die Wortbezeichnungen der Stufen sind übliche Umschreibungen."
   },
   "ma": {
    "before": "gestrichelt: Probe vor dem Waschen",
    "marks": "Rot: Messmarken, je Richtung 3 Paare, mind. 350 mm Abstand",
    "exag": "Massänderung zur Verdeutlichung dreifach überhöht",
    "lenL": "Länge",
    "calcT": "Berechnung nach ISO 5077",
    "formula": "(nachher − vorher) ÷ vorher × 100",
    "example": "({a} mm − {b} mm) ÷ {b} mm × 100",
    "shrink": "Schrumpfen (negativ)",
    "grow": "Längung (positiv)",
    "stable": "masshaltig",
    "width": "Breite in diesem Beispiel: {w} %",
    "panelT": "Ablauf",
    "specL": "PROBE",
    "spec": "mind. 500 × 500 mm, im Normklima konditioniert und markiert (ISO 3759)",
    "washL": "BEHANDLUNG",
    "wash": "Haushaltswäsche und Trocknung nach ISO 6330, Programm nach Vereinbarung; für Berufskleidung Industriewäsche nach ISO 15797",
    "resL": "ERGEBNIS",
    "res": "Mittelwert für Länge und Breite, auf 0,5 % gerundet; Grundlage für Pflegeetiketten",
    "furtherT": "Weitere Prüfungen",
    "further": [
     [
      "Berstdruck: Eine Membran wölbt die Probe bis zum Platzen. Für Maschenware, Vliese und Laminate; bis 800 kPa liefern hydraulische und pneumatische Geräte vergleichbare Werte.",
      "ISO 13938"
     ],
     [
      "Nahtfestigkeit: Höchstkraft beim Zug quer zur Naht.",
      "ISO 13935"
     ],
     [
      "Luftdurchlässigkeit: Luftstrom durch eine Fläche bei festgelegtem Druckunterschied.",
      "ISO 9237"
     ]
    ],
    "note": "Massänderung ist besonders bei Baumwolle, Viskose und Maschenware ein Thema. Thermofixieren bei Synthetics und mechanisches Krumpfen bei Baumwolle verringern das Schrumpfen. Welche Werte zulässig sind, legen Käufer und Lieferant fest."
   }
  },
  "quiz": [
   {
    "q": "Welches Normklima schreibt ISO 139 für die Textilprüfung vor?",
    "a": [
     "20 °C und 65 % rF",
     "23 °C und 30 % rF",
     "25 °C und 80 % rF",
     "18 °C und 50 % rF"
    ],
    "c": 0,
    "e": "Standard sind 20,0 °C und 65,0 % rF mit ± 2 °C und ± 4 % Toleranz; 23 °C/50 % und 27 °C/65 % sind Alternativen.",
    "sc": 0
   },
   {
    "q": "Warum müssen Proben vor der Prüfung konditioniert werden?",
    "a": [
     "Weil Feuchtigkeit Masse, Festigkeit und Dehnung verändert",
     "Weil die Farbe sonst nicht messbar ist",
     "Damit die Probe steriler wird",
     "Damit sie schneller reisst"
    ],
    "c": 0,
    "e": "Viele Fasern nehmen Wasser auf. Erst im Gleichgewicht mit dem Normklima sind Ergebnisse zwischen Labors vergleichbar.",
    "sc": 0
   },
   {
    "q": "Was unterscheidet den Grab-Versuch vom Streifenversuch?",
    "a": [
     "Nur die Mitte einer breiteren Probe wird eingespannt",
     "Die Probe wird nass geprüft",
     "Es wird gedrückt statt gezogen",
     "Die Probe wird vorher gewaschen"
    ],
    "c": 0,
    "e": "Beim Grab-Versuch (ISO 13934-2) fassen schmale Klemmbacken die Mitte einer 100 mm breiten Probe; das seitliche Gewebe trägt mit.",
    "sc": 1
   },
   {
    "q": "Welches Weiterreissverfahren erzeugt einen Doppelriss?",
    "a": [
     "Zungenform",
     "Hosenform",
     "Flügelform",
     "Elmendorf-Pendel"
    ],
    "c": 0,
    "e": "Bei der Zungenform (ISO 13937-4) bilden zwei Einschnitte eine Zunge, beim Ziehen laufen zwei Risse zugleich.",
    "sc": 2
   },
   {
    "q": "Was zählt der Martindale-Scheuertest?",
    "a": [
     "Touren bis zum Endpunkt, etwa zwei gerissene Fäden",
     "Die Zeit bis zum Ausbleichen",
     "Die Anzahl Pills pro cm²",
     "Den Wasserdruck bis zum Durchtritt"
    ],
    "c": 0,
    "e": "Die Probe reibt auf einer Lissajous-Bahn auf Wollgewebe, gezählt werden die Touren bis zum festgelegten Endpunkt.",
    "sc": 3
   },
   {
    "q": "Was bedeutet Pillingnote 5?",
    "a": [
     "Keine Veränderung",
     "Sehr starkes Pilling",
     "Mittleres Pilling",
     "Prüfung nicht bestanden"
    ],
    "c": 0,
    "e": "Die Skala reicht von 5 (keine Veränderung) bis 1 (sehr starke Veränderung), beurteilt mit Fotostandards.",
    "sc": 4
   },
   {
    "q": "Wozu dient das Mehrfaserbegleitgewebe bei der Waschechtheit?",
    "a": [
     "Es zeigt, auf welche Fasern die Farbe abfärbt",
     "Es schützt die Probe vor den Stahlkugeln",
     "Es misst die Temperatur",
     "Es verhindert das Schrumpfen"
    ],
    "c": 0,
    "e": "Die Streifen aus verschiedenen Fasern zeigen, wie stark jede Faserart mitgewaschen anblutet; bewertet mit dem Graumassstab für Anbluten.",
    "sc": 5
   },
   {
    "q": "Welche Skala nutzt die Lichtechtheit nach ISO 105-B02?",
    "a": [
     "Blaumassstab 1 bis 8",
     "Graumassstab 1 bis 5",
     "Prozent Massänderung",
     "Touren bis zum Loch"
    ],
    "c": 0,
    "e": "Acht blaue Wollreferenzen, jede etwa doppelt so lichtecht wie die vorherige; die Probe wird mit ihnen verglichen.",
    "sc": 6
   }
  ],
  "links": [
   [
    "Titer, Festigkeit und Dehnung",
    "Zugversuch am Garn: Höchstzugkraft und Dehnung nach dem CRE-Prinzip mit dem STATIMAT."
   ],
   [
    "Färben",
    "Woher die Farbe kommt: Farbstoffklassen und Verfahren, die die Echtheit bestimmen."
   ],
   [
    "Chemische Ausrüstung",
    "Pflegeleicht, schmutzabweisend, pillarm: Ausrüstungen, deren Wirkung hier geprüft wird."
   ],
   [
    "Mechanische Ausrüstung",
    "Kompaktieren, Rauen, Scheren: Verfahren, die Massänderung und Pilling beeinflussen."
   ],
   [
    "Bindungslehre",
    "Leinwand, Köper, Atlas: die Bindung prägt Festigkeit, Scheuern und Pilling."
   ]
  ]
 },
 "en": {
  "ui": {
   "eyebrow": "Knowledge Base · Fabric testing",
   "h1": "Fabric testing: measuring what a fabric can take",
   "lead": "Before a fabric is sold or made up, the laboratory checks against standards that it performs as promised. Eight scenes show the standard atmosphere, tensile and tear strength, Martindale abrasion, pilling, colour fastness to washing and rubbing, light fastness and dimensional change in washing.",
   "note": "Schematic illustration. Test parameters come from standard summaries and laboratory information (ISO 139, 13934, 13937, 12947, 12945, 105, 5077); curves, colour changes and classifications are simplified. The standard text is always authoritative.",
   "pause": "⏸ Pause",
   "play": "▶ Play",
   "sl": {
    "rh": "Humidity",
    "meth": "Method",
    "tear": "Method",
    "cyc": "Rubs",
    "grade": "Grade",
    "fx": "Test",
    "bw": "Light fastness",
    "sh": "Dimensional change"
   },
   "lkL": "More in the Knowledge Base",
   "open": "Open module"
  },
  "scenes": [
   {
    "k": "Atmosphere",
    "title": "Condition first, then test",
    "text": "Textile fibres absorb different amounts of water depending on humidity, which changes mass, strength and elongation. Specimens are therefore kept in the standard atmosphere of ISO 139 until their mass stops changing, and are tested in the same atmosphere. Use the slider to change the humidity.",
    "facts": [
     [
      "Standard",
      "20.0 °C and 65.0% RH"
     ],
     [
      "Tolerance",
      "± 2 °C and ± 4% RH"
     ],
     [
      "Alternatives",
      "23 °C / 50% and 27 °C / 65% (tropical)"
     ],
     [
      "Equilibrium",
      "weigh at 2 h intervals"
     ]
    ]
   },
   {
    "k": "Tensile",
    "title": "Tensile test: strip and grab",
    "text": "A tensile tester pulls the clamped specimen apart at constant speed until it breaks, recording force against elongation. In the strip test the full specimen width carries the load; in the grab test only the centre of a wider specimen is gripped. Use the slider to choose the method.",
    "facts": [
     [
      "Strip",
      "ISO 13934-1"
     ],
     [
      "Grab",
      "ISO 13934-2"
     ],
     [
      "Result",
      "maximum force in N"
     ],
     [
      "Directions",
      "warp and weft separately"
     ]
    ]
   },
   {
    "k": "Tearing",
    "title": "How easily does a tear run on?",
    "text": "A small cut or snag can ruin a garment or a tarpaulin if the tear keeps running. Tear tests therefore start from a defined cut. ISO 13937 has four methods: pendulum, trouser, wing and tongue. Use the slider to choose the method.",
    "facts": [
     [
      "Standard",
      "ISO 13937 parts 1–4"
     ],
     [
      "Start",
      "defined cut"
     ],
     [
      "Result",
      "tear force in N"
     ],
     [
      "Note",
      "methods not convertible"
     ]
    ]
   },
   {
    "k": "Abrasion",
    "title": "Martindale: rubs until worn",
    "text": "In the Martindale tester the round specimen rubs under load against a standard wool fabric. The path is a Lissajous figure, so every point is abraded from all directions. The rubs are counted until an end point is reached, such as two broken threads. Use the slider to set the rubs achieved.",
    "facts": [
     [
      "Standard",
      "ISO 12947-2"
     ],
     [
      "Specimen",
      "approx. 38 mm diameter"
     ],
     [
      "Load",
      "9 kPa or 12 kPa"
     ],
     [
      "Result",
      "rubs to end point"
     ]
    ]
   },
   {
    "k": "Pilling",
    "title": "Little balls on the surface",
    "text": "Rubbing pulls fibre ends out of the yarn; they tangle into small balls that stay on the surface. After a standardised treatment the specimen is compared with photographic standards and graded from 5 (no change) to 1 (very severe). Use the slider to change the grade.",
    "facts": [
     [
      "Standard",
      "ISO 12945 parts 1–4"
     ],
     [
      "Scale",
      "5 to 1, half grades"
     ],
     [
      "Assessment",
      "visual, photo standards"
     ],
     [
      "Often required",
      "knits grade 3–4 or better"
     ]
    ]
   },
   {
    "k": "Colour fastness",
    "title": "Washing and rubbing",
    "text": "Colour fastness describes how well a dyeing or print survives use and care. In wash fastness the specimen fades and stains adjacent fabrics washed with it; in rub fastness it stains a white rubbing cloth. Ratings use the grey scale from 5 to 1. Use the slider to choose the test.",
    "facts": [
     [
      "Washing",
      "ISO 105-C06"
     ],
     [
      "Rubbing",
      "ISO 105-X12"
     ],
     [
      "Grey scale",
      "A02 change · A03 staining"
     ],
     [
      "Scale",
      "5 (none) to 1 (severe)"
     ]
    ]
   },
   {
    "k": "Light fastness",
    "title": "Xenon light and blue wool",
    "text": "The specimen and eight blue wool references are exposed together to xenon light that simulates daylight, with part of each covered. The light fastness is the number of the reference that fades about as much as the specimen. Use the slider to choose the specimen's light fastness.",
    "facts": [
     [
      "Standard",
      "ISO 105-B02"
     ],
     [
      "Light source",
      "xenon arc, daylight D65"
     ],
     [
      "Scale",
      "blue wool 1 to 8"
     ],
     [
      "Steps",
      "each about twice as fast"
     ]
    ]
   },
   {
    "k": "Dimensional change",
    "title": "Shrinkage in washing",
    "text": "Reference marks are made on the conditioned specimen. After washing and drying to ISO 6330 it is measured again and the change is given in percent: minus for shrinkage, plus for extension. Further common tests are listed at the bottom right. Use the slider to set the dimensional change.",
    "facts": [
     [
      "Standards",
      "ISO 5077, 3759, 6330"
     ],
     [
      "Marks",
      "at least 350 mm apart"
     ],
     [
      "Result",
      "% length and width"
     ],
     [
      "Rounding",
      "to 0.5%"
     ]
    ]
   }
  ],
  "cv": {
   "rhN": "{n}% RH",
   "cycN": "{n} rubs",
   "gradeN": "Grade {n}",
   "bwN": "Level {n}",
   "kl": {
    "chamber": "Conditioning room or cabinet",
    "temp": "20.0 °C",
    "rh": "Relative humidity (% RH), green: tolerance 61–69%",
    "ok": "in standard atmosphere",
    "no": "outside standard atmosphere",
    "regainT": "Moisture regain of fibres (based on dry mass)",
    "fibres": [
     "Wool",
     "Viscose",
     "Cotton",
     "Polyamide",
     "Polyester"
    ],
    "regainN": "Guide values at 65% RH; the curve at other humidities is schematic.",
    "alt": "ISO 139 also allows 23 °C / 50% RH for special cases and 27 °C / 65% RH for tropical regions. Conditioning continues until the mass barely changes between weighings 2 hours apart.",
    "why": "In the standard atmosphere results are comparable whichever laboratory tests them. Wool and viscose absorb a lot of water, polyester hardly any. Viscose loses much of its strength when wet, while cotton tends to get stronger.",
    "whyNo": "Outside the tolerance, results do not comply with the standard: mass, strength and elongation of hygroscopic fibres deviate. The specimen must be reconditioned in the standard atmosphere."
   },
   "zg": {
    "cross": "Crosshead moves at constant rate (CRE)",
    "clamp25": "Jaw faces only 25 mm wide",
    "broke": "Specimen broken",
    "eL": "Elongation",
    "fL": "Force",
    "fmax": "Maximum force",
    "schem": "Schematic curve; values depend on material and construction.",
    "widthL": "SPECIMEN WIDTH",
    "gaugeL": "GAUGE LENGTH",
    "speedL": "SPEED",
    "resL": "RESULT",
    "useL": "USE",
    "note": "Several specimens are tested in both warp and weft directions. In the grab test the unclamped fabric at the sides helps carry the load, so strip and grab values are not directly comparable. The American grab standard ASTM D5034 runs at 300 mm/min instead of 50 mm/min. Seams have their own methods in ISO 13935.",
    "nowF": "Force ≈ {f} N",
    "m": [
     {
      "n": "Strip ISO 13934-1",
      "w": "50 mm",
      "l": "200 mm",
      "v": "100 mm/min",
      "r": "Maximum force in N and elongation at maximum force in %",
      "u": "mainly woven fabrics"
     },
     {
      "n": "Grab ISO 13934-2",
      "w": "100 mm wide specimen",
      "l": "100 mm",
      "v": "50 mm/min",
      "r": "maximum force in N only",
      "u": "woven fabrics; close to use because force enters over part of the width"
     }
    ]
   },
   "wr": {
    "pend": "Pendulum",
    "fixed": "fixed clamp",
    "slit": "Cut; the tear runs upwards",
    "tongue": "Tongue pulled against the rest",
    "wing": "angled wings",
    "tipL": "Tear tip",
    "pathL": "Travel",
    "forceL": "Force",
    "mean": "Mean of peaks",
    "energyT": "Energy lost by the pendulum",
    "energy": "The more force tearing needs, the more energy the falling pendulum loses. The tear force is calculated from this.",
    "prL": "PRINCIPLE",
    "devL": "APPARATUS",
    "hintL": "NOTE",
    "note": "Tear strength matters for workwear, tents, tarpaulins and balloon fabrics. In wovens the threads break one after another, giving a jagged force curve; the peaks are evaluated. The four methods give different numbers, so a result is only valid together with its method.",
    "m": [
     {
      "n": "Elmendorf pendulum (part 1)",
      "p": "A falling pendulum suddenly continues the tear in a cut specimen (single tear).",
      "d": "Ballistic pendulum apparatus",
      "h": "Quick and widely used; measures the energy consumed."
     },
     {
      "n": "Trouser (part 2)",
      "p": "The specimen is cut in the middle and the two 'legs' are pulled in opposite directions (single tear).",
      "d": "Tensile tester with constant rate of extension (CRE)",
      "h": "Not suitable for knitted or elastic woven fabrics."
     },
     {
      "n": "Wing (part 3)",
      "p": "Like the trouser, but with angled legs so the tear runs more reliably along the centre (single tear).",
      "d": "Tensile tester (CRE)",
      "h": "For fabrics in which the tear deviates sideways in the trouser test."
     },
     {
      "n": "Tongue (part 4)",
      "p": "Two parallel cuts form a tongue that is pulled against the rest of the specimen; two tears run at once (double tear).",
      "d": "Tensile tester (CRE)",
      "h": "Gives higher values than single-tear methods."
     }
    ]
   },
   "ms": {
    "abr": "Abradant: standard wool fabric",
    "hold": "Specimen holder with specimen (38 mm dia.)",
    "lis": "Lissajous path (schematic)",
    "classT": "Guide values for upholstery (rubs to end point, 12 kPa)",
    "cl": [
     "decorative",
     "light",
     "domestic",
     "heavy",
     "contract"
    ],
    "cld": [
     "Under 10,000 rubs: cushions, decoration, rarely used furniture.",
     "10,000 to 15,000 rubs: occasionally used chairs.",
     "15,000 to 25,000 rubs: normal domestic use; some furniture retailers require at least 20,000.",
     "25,000 to 40,000 rubs: heavily used sofas, homes with children or pets.",
     "40,000 rubs and above: offices, hospitality, contract; hotel lobbies often 50,000 or more."
    ],
    "panelT": "Martindale ISO 12947-2",
    "loadL": "LOAD",
    "load": "9 kPa for apparel and household textiles, 12 kPa for upholstery, workwear and technical textiles",
    "endL": "END POINT",
    "end": "for example two broken threads in wovens, a hole in knits or worn-off pile",
    "inspL": "PROCEDURE",
    "insp": "Inspection at set intervals; the result is the last rub count before the end point.",
    "req": "A value only counts with its load: 20,000 rubs at 12 kPa are tougher than at 9 kPa.",
    "note": "The classification comes from manufacturer and retailer information, not from the standard. In North America the Wyzenbeek test is also common for upholstery; its double rubs cannot be converted into Martindale rubs."
   },
   "pi": {
    "light": "Schematic; the surface is assessed against photographic standards.",
    "scaleT": "Grading scale (ISO 12945)",
    "g": [
     "No change.",
     "Slight change: fuzz or first signs of pills.",
     "Moderate change: distinct pills and fuzz.",
     "Significant change: many pills over a large area.",
     "Very severe change: pills over the whole surface."
    ],
    "methT": "Methods",
    "meth": [
     [
      "Pilling box: specimens on tubes tumble in a cork-lined box.",
      "PART 1"
     ],
     [
      "Modified Martindale: assessed at fixed stages from 125 to 7000 rubs.",
      "PART 2"
     ],
     [
      "Random tumble: specimens tumble in a cork-lined drum.",
      "PART 3"
     ],
     [
      "Visual assessment of specimens from all methods.",
      "PART 4"
     ]
    ],
    "assess": "Assessment takes place in a viewing cabinet with low-angle light (viewing angle 5–15°), with the specimen next to untreated fabric. The result is rounded to half a grade.",
    "note": "In blends with polyester or acrylic the fibres are so strong that the pills do not fall off and remain visible. Long fibres, more yarn twist, singeing and dense constructions reduce pilling. Many retailers require at least grade 3–4 for knits."
   },
   "fe": {
    "bath": "Container rotates in a heated water bath",
    "balls": "Steel balls add mechanical action",
    "compT": "Composite specimen 10 × 4 cm",
    "mf": [
     "Acetate",
     "Cotton",
     "Polyamide",
     "Polyester",
     "Acrylic",
     "Wool"
    ],
    "sewn": "sewn to the multifibre adjacent fabric along one short edge",
    "dyed": "Specimen",
    "spec": "dyed specimen on the base plate",
    "finger": "Rubbing finger with white cotton cloth",
    "stroke": "Stroke 104 mm · 10 strokes in 10 s",
    "dry": "dry",
    "wet": "wet",
    "clothT": "Rubbing cloths after the test (example)",
    "gsC": "Grey scale for change (A02)",
    "gsS": "Grey scale for staining (A03)",
    "condL": "TEST CONDITIONS",
    "evalL": "ASSESSMENT",
    "note": "Grade 5 means no change or no staining, grade 1 very severe; half grades lie in between. Many buyers accept grade 4 or better, some 3–4. Instead of visual assessment, instrumental evaluation is possible (ISO 105-A04/A05).",
    "m": [
     {
      "n": "Wash fastness ISO 105-C06",
      "c": "Steel container with reference detergent, temperature by test level; single (S) or multiple (M) test",
      "e": "Colour change of the specimen and staining of each adjacent strip",
      "d": "One run in the container simulates one or more domestic or commercial washes. After drying: how much has the specimen faded, and which fibres in the adjacent fabric have picked up colour?"
     },
     {
      "n": "Rub fastness ISO 105-X12",
      "c": "Rubbing finger, 9 N downward force, 104 mm stroke, 10 strokes in 10 s, dry and wet",
      "e": "Staining of the white rubbing cloth",
      "d": "Shows whether unfixed dye on the surface rubs off, for example dark jeans onto a light sofa cover. Wet results are usually worse than dry. Specimen at least 50 × 140 mm."
     }
    ]
   },
   "li": {
    "lamp": "Xenon arc lamp with filters",
    "spec": "Specimen",
    "exposed": "exposed",
    "masked": "covered",
    "refT": "Blue wool 1–8 is exposed together with the specimen",
    "expo": "Exposure time",
    "result": "Light fastness {n}",
    "sc": [
     "The specimen fades like reference 1: very low.",
     "The specimen fades like reference 2: low.",
     "The specimen fades like reference 3: moderate.",
     "The specimen fades like reference 4: fairly good.",
     "The specimen fades like reference 5: good.",
     "The specimen fades like reference 6: very good.",
     "The specimen fades like reference 7: excellent.",
     "The specimen fades like reference 8: outstanding."
    ],
    "panelT": "ISO 105-B02",
    "srcL": "LIGHT SOURCE",
    "src": "Xenon arc filtered to a daylight spectrum (D65)",
    "ruleL": "BLUE WOOL",
    "rule": "Eight blue-dyed wool fabrics from 1 (very low) to 8 (very high light fastness); each step is about twice as fast as the one before.",
    "methL": "ASSESSMENT",
    "meth": "The contrast between exposed and covered areas is rated with the grey scale and compared with the references. In America references L2–L9 are common; the results are not interchangeable.",
    "note": "Light fastness matters for curtains, awnings, car seats and outdoor textiles. As high levels need very long exposure, quality control often uses a pass/fail test against a single reference. The verbal labels of the levels are common descriptions."
   },
   "ma": {
    "before": "dashed: specimen before washing",
    "marks": "Red: reference marks, 3 pairs per direction, at least 350 mm apart",
    "exag": "Dimensional change exaggerated threefold for clarity",
    "lenL": "Length",
    "calcT": "Calculation to ISO 5077",
    "formula": "(after − before) ÷ before × 100",
    "example": "({a} mm − {b} mm) ÷ {b} mm × 100",
    "shrink": "Shrinkage (negative)",
    "grow": "Extension (positive)",
    "stable": "dimensionally stable",
    "width": "Width in this example: {w}%",
    "panelT": "Procedure",
    "specL": "SPECIMEN",
    "spec": "at least 500 × 500 mm, conditioned in the standard atmosphere and marked (ISO 3759)",
    "washL": "TREATMENT",
    "wash": "Domestic washing and drying to ISO 6330, programme as agreed; for workwear industrial laundering to ISO 15797",
    "resL": "RESULT",
    "res": "Mean for length and width, rounded to 0.5%; basis for care labels",
    "furtherT": "Further tests",
    "further": [
     [
      "Bursting strength: a diaphragm bulges the specimen until it bursts. For knits, nonwovens and laminates; up to 800 kPa hydraulic and pneumatic testers give comparable results.",
      "ISO 13938"
     ],
     [
      "Seam strength: maximum force pulling across the seam.",
      "ISO 13935"
     ],
     [
      "Air permeability: air flow through an area at a set pressure difference.",
      "ISO 9237"
     ]
    ],
    "note": "Dimensional change is a particular issue for cotton, viscose and knits. Heat setting of synthetics and compressive shrinking of cotton reduce shrinkage. Acceptable values are agreed between buyer and supplier."
   }
  },
  "quiz": [
   {
    "q": "Which standard atmosphere does ISO 139 specify for textile testing?",
    "a": [
     "20 °C and 65% RH",
     "23 °C and 30% RH",
     "25 °C and 80% RH",
     "18 °C and 50% RH"
    ],
    "c": 0,
    "e": "The standard is 20.0 °C and 65.0% RH with ± 2 °C and ± 4% tolerance; 23 °C/50% and 27 °C/65% are alternatives.",
    "sc": 0
   },
   {
    "q": "Why must specimens be conditioned before testing?",
    "a": [
     "Because moisture changes mass, strength and elongation",
     "Because otherwise the colour cannot be measured",
     "To make the specimen sterile",
     "So that it breaks faster"
    ],
    "c": 0,
    "e": "Many fibres absorb water. Only in equilibrium with the standard atmosphere are results comparable between laboratories.",
    "sc": 0
   },
   {
    "q": "What distinguishes the grab test from the strip test?",
    "a": [
     "Only the centre of a wider specimen is clamped",
     "The specimen is tested wet",
     "It pushes instead of pulls",
     "The specimen is washed first"
    ],
    "c": 0,
    "e": "In the grab test (ISO 13934-2) narrow jaws grip the centre of a 100 mm wide specimen; the fabric at the sides helps carry the load.",
    "sc": 1
   },
   {
    "q": "Which tear method produces a double tear?",
    "a": [
     "Tongue",
     "Trouser",
     "Wing",
     "Elmendorf pendulum"
    ],
    "c": 0,
    "e": "In the tongue method (ISO 13937-4) two cuts form a tongue; pulling it makes two tears run at once.",
    "sc": 2
   },
   {
    "q": "What does the Martindale abrasion test count?",
    "a": [
     "Rubs to an end point, such as two broken threads",
     "Time until fading",
     "Number of pills per cm²",
     "Water pressure until penetration"
    ],
    "c": 0,
    "e": "The specimen rubs on wool fabric along a Lissajous path; the rubs are counted until the defined end point.",
    "sc": 3
   },
   {
    "q": "What does pilling grade 5 mean?",
    "a": [
     "No change",
     "Very severe pilling",
     "Moderate pilling",
     "Test failed"
    ],
    "c": 0,
    "e": "The scale runs from 5 (no change) to 1 (very severe change), assessed with photographic standards.",
    "sc": 4
   },
   {
    "q": "What is the multifibre adjacent fabric for in wash fastness testing?",
    "a": [
     "It shows which fibres the colour stains",
     "It protects the specimen from the steel balls",
     "It measures the temperature",
     "It prevents shrinkage"
    ],
    "c": 0,
    "e": "The strips of different fibres show how much each fibre type is stained when washed together, rated with the grey scale for staining.",
    "sc": 5
   },
   {
    "q": "Which scale does light fastness to ISO 105-B02 use?",
    "a": [
     "Blue wool 1 to 8",
     "Grey scale 1 to 5",
     "Percent dimensional change",
     "Rubs until a hole"
    ],
    "c": 0,
    "e": "Eight blue wool references, each about twice as light-fast as the previous one; the specimen is compared with them.",
    "sc": 6
   }
  ],
  "links": [
   [
    "Count, tenacity and elongation",
    "Tensile test on yarn: maximum force and elongation by the CRE principle with the STATIMAT."
   ],
   [
    "Dyeing",
    "Where the colour comes from: dye classes and processes that decide the fastness."
   ],
   [
    "Chemical finishing",
    "Easy care, soil release, anti-pilling: finishes whose effect is tested here."
   ],
   [
    "Mechanical finishing",
    "Compacting, raising, shearing: processes that affect dimensional change and pilling."
   ],
   [
    "Weave structures",
    "Plain, twill, satin: the weave shapes strength, abrasion and pilling."
   ]
  ]
 },
 "es": {
  "ui": {
   "eyebrow": "Knowledge Base · Ensayos de tejidos",
   "h1": "Ensayos de tejidos: medir lo que aguanta un tejido",
   "lead": "Antes de vender o confeccionar un tejido, el laboratorio comprueba según normas que cumple lo prometido. Ocho escenas muestran la atmósfera normalizada, la resistencia a la tracción y al desgarro, la abrasión Martindale, el pilling, la solidez del color al lavado y al frote, la solidez a la luz y la variación dimensional en el lavado.",
   "note": "Representación esquemática. Los parámetros de ensayo proceden de resúmenes de normas e información de laboratorios (ISO 139, 13934, 13937, 12947, 12945, 105, 5077); curvas, cambios de color y clasificaciones están simplificados. Siempre prevalece el texto de la norma.",
   "pause": "⏸ Pausa",
   "play": "▶ Reproducir",
   "sl": {
    "rh": "Humedad",
    "meth": "Método",
    "tear": "Método",
    "cyc": "Ciclos",
    "grade": "Nota",
    "fx": "Ensayo",
    "bw": "Solidez a la luz",
    "sh": "Variación"
   },
   "lkL": "Más en la Knowledge Base",
   "open": "Abrir módulo"
  },
  "scenes": [
   {
    "k": "Atmósfera",
    "title": "Primero acondicionar, luego ensayar",
    "text": "Las fibras textiles absorben más o menos agua según la humedad, y eso cambia la masa, la resistencia y el alargamiento. Por eso las probetas se guardan en la atmósfera normalizada de la ISO 139 hasta que su masa deja de variar, y se ensayan en esa misma atmósfera. Con el control deslizante se cambia la humedad.",
    "facts": [
     [
      "Normalizada",
      "20,0 °C y 65,0 % HR"
     ],
     [
      "Tolerancia",
      "± 2 °C y ± 4 % HR"
     ],
     [
      "Alternativas",
      "23 °C / 50 % y 27 °C / 65 % (tropical)"
     ],
     [
      "Equilibrio",
      "pesar cada 2 h"
     ]
    ]
   },
   {
    "k": "Tracción",
    "title": "Ensayo de tracción: tira y grab",
    "text": "Una máquina de tracción estira la probeta sujeta a velocidad constante hasta que se rompe y registra la fuerza frente al alargamiento. En el método de la tira trabaja todo el ancho; en el método grab solo se sujeta el centro de una probeta más ancha. Con el control deslizante se elige el método.",
    "facts": [
     [
      "Tira",
      "ISO 13934-1"
     ],
     [
      "Grab",
      "ISO 13934-2"
     ],
     [
      "Resultado",
      "fuerza máxima en N"
     ],
     [
      "Direcciones",
      "urdimbre y trama por separado"
     ]
    ]
   },
   {
    "k": "Desgarro",
    "title": "¿Con qué facilidad sigue un desgarro?",
    "text": "Un pequeño corte o enganchón puede arruinar una prenda o una lona si el desgarro avanza. Por eso el ensayo parte de un corte definido. La ISO 13937 tiene cuatro métodos: péndulo, pantalón, ala y lengüeta. Con el control deslizante se elige el método.",
    "facts": [
     [
      "Norma",
      "ISO 13937 partes 1–4"
     ],
     [
      "Inicio",
      "corte definido"
     ],
     [
      "Resultado",
      "fuerza de desgarro en N"
     ],
     [
      "Atención",
      "métodos no convertibles"
     ]
    ]
   },
   {
    "k": "Abrasión",
    "title": "Martindale: ciclos hasta el desgaste",
    "text": "En el abrasímetro Martindale la probeta redonda frota bajo carga contra un tejido de lana normalizado. La trayectoria es una figura de Lissajous, así cada punto se desgasta desde todas las direcciones. Se cuentan los ciclos hasta un punto final, por ejemplo dos hilos rotos. Con el control deslizante se ajustan los ciclos alcanzados.",
    "facts": [
     [
      "Norma",
      "ISO 12947-2"
     ],
     [
      "Probeta",
      "aprox. 38 mm de diámetro"
     ],
     [
      "Carga",
      "9 kPa o 12 kPa"
     ],
     [
      "Resultado",
      "ciclos hasta el punto final"
     ]
    ]
   },
   {
    "k": "Pilling",
    "title": "Bolitas en la superficie",
    "text": "El roce saca extremos de fibra del hilo, que se enredan en pequeñas bolitas y quedan en la superficie. Tras un tratamiento normalizado, la probeta se compara con patrones fotográficos y se califica de 5 (sin cambio) a 1 (muy intenso). Con el control deslizante se cambia la nota.",
    "facts": [
     [
      "Norma",
      "ISO 12945 partes 1–4"
     ],
     [
      "Escala",
      "5 a 1, medias notas"
     ],
     [
      "Evaluación",
      "visual, patrones fotográficos"
     ],
     [
      "Exigencia frecuente",
      "punto: nota 3–4 o mejor"
     ]
    ]
   },
   {
    "k": "Solidez del color",
    "title": "Lavado y frote",
    "text": "La solidez del color describe lo bien que un teñido o estampado resiste el uso y el cuidado. En la solidez al lavado la probeta pierde color y mancha los tejidos testigo lavados con ella; en la solidez al frote mancha un paño blanco. Se califica con la escala de grises de 5 a 1. Con el control deslizante se elige el ensayo.",
    "facts": [
     [
      "Lavado",
      "ISO 105-C06"
     ],
     [
      "Frote",
      "ISO 105-X12"
     ],
     [
      "Escala de grises",
      "A02 cambio · A03 descarga"
     ],
     [
      "Escala",
      "5 (nada) a 1 (muy intenso)"
     ]
    ]
   },
   {
    "k": "Solidez a la luz",
    "title": "Luz de xenón y escala de azules",
    "text": "La probeta y ocho referencias de lana azul se exponen juntas a una luz de xenón que imita la luz del día; una parte de cada una queda tapada. La solidez a la luz es el número de la referencia que se decolora más o menos como la probeta. Con el control deslizante se elige la solidez de la probeta.",
    "facts": [
     [
      "Norma",
      "ISO 105-B02"
     ],
     [
      "Fuente",
      "arco de xenón, luz día D65"
     ],
     [
      "Escala",
      "lana azul 1 a 8"
     ],
     [
      "Niveles",
      "cada uno aprox. el doble de sólido"
     ]
    ]
   },
   {
    "k": "Variación dimensional",
    "title": "Encogimiento en el lavado",
    "text": "Sobre la probeta acondicionada se marcan referencias. Tras lavar y secar según la ISO 6330 se vuelve a medir y la variación se expresa en porcentaje: menos para encogimiento, más para alargamiento. Abajo a la derecha aparecen otros ensayos frecuentes. Con el control deslizante se ajusta la variación.",
    "facts": [
     [
      "Normas",
      "ISO 5077, 3759, 6330"
     ],
     [
      "Marcas",
      "al menos 350 mm de distancia"
     ],
     [
      "Resultado",
      "% largo y ancho"
     ],
     [
      "Redondeo",
      "a 0,5 %"
     ]
    ]
   }
  ],
  "cv": {
   "rhN": "{n} % HR",
   "cycN": "{n} ciclos",
   "gradeN": "Nota {n}",
   "bwN": "Nivel {n}",
   "kl": {
    "chamber": "Sala o cámara de acondicionamiento",
    "temp": "20,0 °C",
    "rh": "Humedad relativa (% HR), verde: tolerancia 61–69 %",
    "ok": "en atmósfera normalizada",
    "no": "fuera de la atmósfera normalizada",
    "regainT": "Absorción de humedad de las fibras (sobre masa seca)",
    "fibres": [
     "Lana",
     "Viscosa",
     "Algodón",
     "Poliamida",
     "Poliéster"
    ],
    "regainN": "Valores orientativos a 65 % HR; la curva a otras humedades es esquemática.",
    "alt": "La ISO 139 admite también 23 °C / 50 % HR para casos especiales y 27 °C / 65 % HR para regiones tropicales. Se acondiciona hasta que la masa apenas cambia entre pesadas separadas 2 horas.",
    "why": "En la atmósfera normalizada los resultados son comparables entre laboratorios. La lana y la viscosa absorben mucha agua, el poliéster casi nada. La viscosa pierde bastante resistencia en húmedo, mientras que el algodón tiende a ganarla.",
    "whyNo": "Fuera de la tolerancia los resultados no cumplen la norma: masa, resistencia y alargamiento de las fibras higroscópicas se desvían. La probeta debe acondicionarse de nuevo."
   },
   "zg": {
    "cross": "El travesaño avanza a velocidad constante (CRE)",
    "clamp25": "Mordazas de solo 25 mm de ancho",
    "broke": "Probeta rota",
    "eL": "Alargamiento",
    "fL": "Fuerza",
    "fmax": "Fuerza máxima",
    "schem": "Curva esquemática; los valores dependen del material y la construcción.",
    "widthL": "ANCHO DE PROBETA",
    "gaugeL": "DISTANCIA ENTRE MORDAZAS",
    "speedL": "VELOCIDAD",
    "resL": "RESULTADO",
    "useL": "USO",
    "note": "Se ensayan varias probetas en urdimbre y en trama. En el método grab el tejido lateral no sujeto ayuda a soportar la carga, por eso los valores de tira y grab no son directamente comparables. La norma estadounidense ASTM D5034 trabaja a 300 mm/min en lugar de 50 mm/min. Las costuras tienen métodos propios en la ISO 13935.",
    "nowF": "Fuerza ≈ {f} N",
    "m": [
     {
      "n": "Tira ISO 13934-1",
      "w": "50 mm",
      "l": "200 mm",
      "v": "100 mm/min",
      "r": "Fuerza máxima en N y alargamiento a la fuerza máxima en %",
      "u": "sobre todo tejidos de calada"
     },
     {
      "n": "Grab ISO 13934-2",
      "w": "probeta de 100 mm de ancho",
      "l": "100 mm",
      "v": "50 mm/min",
      "r": "solo fuerza máxima en N",
      "u": "tejidos de calada; cercano al uso porque la fuerza entra por parte del ancho"
     }
    ]
   },
   "wr": {
    "pend": "Péndulo",
    "fixed": "mordaza fija",
    "slit": "Corte; el desgarro sube",
    "tongue": "La lengüeta se tira contra el resto",
    "wing": "alas inclinadas",
    "tipL": "Punta del desgarro",
    "pathL": "Recorrido",
    "forceL": "Fuerza",
    "mean": "Media de los picos",
    "energyT": "Energía que pierde el péndulo",
    "energy": "Cuanta más fuerza requiere el desgarro, más energía pierde el péndulo al caer. A partir de ella se calcula la fuerza de desgarro.",
    "prL": "PRINCIPIO",
    "devL": "EQUIPO",
    "hintL": "NOTA",
    "note": "La resistencia al desgarro importa en ropa de trabajo, tiendas de campaña, lonas y tejidos para globos. En los tejidos de calada los hilos se rompen uno tras otro, por eso la curva es dentada; se evalúan los picos. Los cuatro métodos dan cifras distintas: un resultado solo vale junto con su método.",
    "m": [
     {
      "n": "Péndulo Elmendorf (parte 1)",
      "p": "Un péndulo que cae continúa de golpe el desgarro de una probeta cortada (desgarro simple).",
      "d": "Péndulo balístico",
      "h": "Rápido y muy extendido; mide la energía consumida."
     },
     {
      "n": "Pantalón (parte 2)",
      "p": "La probeta se corta por el centro y las dos «perneras» se tiran en sentidos opuestos (desgarro simple).",
      "d": "Máquina de tracción de velocidad de alargamiento constante (CRE)",
      "h": "No apto para tejidos de punto ni tejidos elásticos."
     },
     {
      "n": "Ala (parte 3)",
      "p": "Como el pantalón, pero con patas inclinadas para que el desgarro siga mejor por el centro (desgarro simple).",
      "d": "Máquina de tracción (CRE)",
      "h": "Para tejidos en los que el desgarro se desvía en el ensayo de pantalón."
     },
     {
      "n": "Lengüeta (parte 4)",
      "p": "Dos cortes paralelos forman una lengüeta que se tira contra el resto; avanzan dos desgarros a la vez (desgarro doble).",
      "d": "Máquina de tracción (CRE)",
      "h": "Da valores más altos que los métodos de desgarro simple."
     }
    ]
   },
   "ms": {
    "abr": "Abrasivo: tejido de lana normalizado",
    "hold": "Portaprobetas con probeta (Ø 38 mm)",
    "lis": "Trayectoria de Lissajous (esquemática)",
    "classT": "Valores orientativos para tapicería (ciclos hasta el punto final, 12 kPa)",
    "cl": [
     "decorativo",
     "ligero",
     "doméstico",
     "intenso",
     "contract"
    ],
    "cld": [
     "Menos de 10 000 ciclos: cojines, decoración, muebles poco usados.",
     "De 10 000 a 15 000 ciclos: sillones y sillas de uso ocasional.",
     "De 15 000 a 25 000 ciclos: uso doméstico normal; algunos vendedores de muebles exigen al menos 20 000.",
     "De 25 000 a 40 000 ciclos: sofás muy usados, hogares con niños o mascotas.",
     "Desde 40 000 ciclos: oficinas, hostelería, contract; en vestíbulos de hotel a menudo 50 000 o más."
    ],
    "panelT": "Martindale ISO 12947-2",
    "loadL": "CARGA",
    "load": "9 kPa para prendas y textiles del hogar, 12 kPa para tapicería, ropa de trabajo y textiles técnicos",
    "endL": "PUNTO FINAL",
    "end": "por ejemplo dos hilos rotos en tejidos de calada, un agujero en punto o pelo desgastado",
    "inspL": "PROCEDIMIENTO",
    "insp": "Control a intervalos fijos; el resultado es el último recuento de ciclos antes del punto final.",
    "req": "Un valor solo cuenta con su carga: 20 000 ciclos a 12 kPa son más exigentes que a 9 kPa.",
    "note": "La clasificación procede de fabricantes y comercios, no de la norma. En Norteamérica también se usa el ensayo Wyzenbeek para tapicería; sus «double rubs» no se pueden convertir en ciclos Martindale."
   },
   "pi": {
    "light": "Esquemático; la superficie se evalúa frente a patrones fotográficos.",
    "scaleT": "Escala de notas (ISO 12945)",
    "g": [
     "Sin cambio.",
     "Cambio leve: pelusa o primeros indicios de bolitas.",
     "Cambio moderado: bolitas y pelusa claras.",
     "Cambio notable: muchas bolitas en una zona amplia.",
     "Cambio muy intenso: bolitas en toda la superficie."
    ],
    "methT": "Métodos",
    "meth": [
     [
      "Caja de pilling: probetas sobre tubos giran en una caja forrada de corcho.",
      "PARTE 1"
     ],
     [
      "Martindale modificado: evaluación en etapas fijas de 125 a 7000 ciclos.",
      "PARTE 2"
     ],
     [
      "Random tumble: probetas giran en un tambor forrado de corcho.",
      "PARTE 3"
     ],
     [
      "Evaluación visual de probetas de todos los métodos.",
      "PARTE 4"
     ]
    ],
    "assess": "Se evalúa en una cabina con luz rasante (ángulo de observación 5–15°), con la probeta junto al tejido sin tratar. El resultado se redondea a media nota.",
    "note": "En mezclas con poliéster o acrílico las fibras son tan resistentes que las bolitas no se desprenden y siguen visibles. Fibras largas, más torsión, gaseado y construcciones densas reducen el pilling. Muchos comercios exigen al menos nota 3–4 para tejido de punto."
   },
   "fe": {
    "bath": "El recipiente gira en un baño de agua caliente",
    "balls": "Bolas de acero aumentan la acción mecánica",
    "compT": "Probeta compuesta 10 × 4 cm",
    "mf": [
     "Acetato",
     "Algodón",
     "Poliamida",
     "Poliéster",
     "Acrílico",
     "Lana"
    ],
    "sewn": "cosida al tejido testigo multifibra por un lado corto",
    "dyed": "Probeta",
    "spec": "probeta teñida sobre la placa base",
    "finger": "Dedo de frote con paño blanco de algodón",
    "stroke": "Carrera 104 mm · 10 pasadas en 10 s",
    "dry": "seco",
    "wet": "húmedo",
    "clothT": "Paños de frote tras el ensayo (ejemplo)",
    "gsC": "Escala de grises cambio (A02)",
    "gsS": "Escala de grises descarga (A03)",
    "condL": "CONDICIONES",
    "evalL": "EVALUACIÓN",
    "note": "La nota 5 significa sin cambio o sin descarga, la nota 1 muy intensa; entre ellas hay medias notas. Muchos compradores aceptan nota 4 o mejor, algunos 3–4. En lugar de la evaluación visual puede medirse instrumentalmente (ISO 105-A04/A05).",
    "m": [
     {
      "n": "Solidez al lavado ISO 105-C06",
      "c": "Recipiente de acero con detergente de referencia, temperatura según nivel; ensayo simple (S) o múltiple (M)",
      "e": "Cambio de color de la probeta y descarga en cada tira testigo",
      "d": "Un ciclo en el recipiente simula uno o varios lavados domésticos o comerciales. Tras secar: ¿cuánto ha perdido color la probeta y qué fibras del tejido testigo han tomado color?"
     },
     {
      "n": "Solidez al frote ISO 105-X12",
      "c": "Dedo de frote, 9 N, carrera 104 mm, 10 pasadas en 10 s, en seco y en húmedo",
      "e": "Descarga en el paño de frote blanco",
      "d": "Indica si el colorante no fijado se transfiere, por ejemplo vaqueros oscuros a un sofá claro. En húmedo el resultado suele ser peor que en seco. Probeta de al menos 50 × 140 mm."
     }
    ]
   },
   "li": {
    "lamp": "Lámpara de arco de xenón con filtros",
    "spec": "Probeta",
    "exposed": "expuesto",
    "masked": "tapado",
    "refT": "La escala de azules 1–8 se expone junto con la probeta",
    "expo": "Tiempo de exposición",
    "result": "Solidez a la luz {n}",
    "sc": [
     "La probeta se decolora como la referencia 1: muy baja.",
     "La probeta se decolora como la referencia 2: baja.",
     "La probeta se decolora como la referencia 3: moderada.",
     "La probeta se decolora como la referencia 4: bastante buena.",
     "La probeta se decolora como la referencia 5: buena.",
     "La probeta se decolora como la referencia 6: muy buena.",
     "La probeta se decolora como la referencia 7: excelente.",
     "La probeta se decolora como la referencia 8: sobresaliente."
    ],
    "panelT": "ISO 105-B02",
    "srcL": "FUENTE DE LUZ",
    "src": "Arco de xenón filtrado a un espectro de luz día (D65)",
    "ruleL": "ESCALA DE AZULES",
    "rule": "Ocho tejidos de lana teñidos de azul, de 1 (solidez muy baja) a 8 (muy alta); cada nivel es aproximadamente el doble de sólido que el anterior.",
    "methL": "EVALUACIÓN",
    "meth": "El contraste entre la zona expuesta y la tapada se valora con la escala de grises y se compara con las referencias. En América son habituales las referencias L2–L9; los resultados no son intercambiables.",
    "note": "La solidez a la luz importa en cortinas, toldos, asientos de coche y textiles de exterior. Como los niveles altos exigen exposiciones muy largas, el control de calidad suele usar un ensayo pasa/no pasa frente a una sola referencia. Las denominaciones verbales de los niveles son descripciones habituales."
   },
   "ma": {
    "before": "discontinuo: probeta antes del lavado",
    "marks": "Rojo: marcas de referencia, 3 pares por dirección, al menos 350 mm",
    "exag": "Variación exagerada tres veces para mayor claridad",
    "lenL": "Largo",
    "calcT": "Cálculo según ISO 5077",
    "formula": "(después − antes) ÷ antes × 100",
    "example": "({a} mm − {b} mm) ÷ {b} mm × 100",
    "shrink": "Encogimiento (negativo)",
    "grow": "Alargamiento (positivo)",
    "stable": "estable",
    "width": "Ancho en este ejemplo: {w} %",
    "panelT": "Procedimiento",
    "specL": "PROBETA",
    "spec": "al menos 500 × 500 mm, acondicionada en atmósfera normalizada y marcada (ISO 3759)",
    "washL": "TRATAMIENTO",
    "wash": "Lavado y secado doméstico según ISO 6330, programa acordado; para ropa de trabajo lavado industrial según ISO 15797",
    "resL": "RESULTADO",
    "res": "Media de largo y ancho, redondeada a 0,5 %; base de las etiquetas de cuidado",
    "furtherT": "Otros ensayos",
    "further": [
     [
      "Resistencia al reventamiento: una membrana abomba la probeta hasta que revienta. Para punto, no tejidos y laminados; hasta 800 kPa los equipos hidráulicos y neumáticos dan valores comparables.",
      "ISO 13938"
     ],
     [
      "Resistencia de costura: fuerza máxima tirando perpendicular a la costura.",
      "ISO 13935"
     ],
     [
      "Permeabilidad al aire: caudal de aire a través de una superficie con una diferencia de presión fija.",
      "ISO 9237"
     ]
    ],
    "note": "La variación dimensional es crítica sobre todo en algodón, viscosa y punto. El termofijado de sintéticos y el encogimiento mecánico del algodón la reducen. Los valores admisibles se acuerdan entre comprador y proveedor."
   }
  },
  "quiz": [
   {
    "q": "¿Qué atmósfera normalizada fija la ISO 139 para ensayos textiles?",
    "a": [
     "20 °C y 65 % HR",
     "23 °C y 30 % HR",
     "25 °C y 80 % HR",
     "18 °C y 50 % HR"
    ],
    "c": 0,
    "e": "Lo normal son 20,0 °C y 65,0 % HR con tolerancia de ± 2 °C y ± 4 %; 23 °C/50 % y 27 °C/65 % son alternativas.",
    "sc": 0
   },
   {
    "q": "¿Por qué hay que acondicionar las probetas antes del ensayo?",
    "a": [
     "Porque la humedad cambia masa, resistencia y alargamiento",
     "Porque si no el color no se puede medir",
     "Para esterilizar la probeta",
     "Para que se rompa antes"
    ],
    "c": 0,
    "e": "Muchas fibras absorben agua. Solo en equilibrio con la atmósfera normalizada los resultados son comparables entre laboratorios.",
    "sc": 0
   },
   {
    "q": "¿Qué distingue el método grab del método de la tira?",
    "a": [
     "Solo se sujeta el centro de una probeta más ancha",
     "La probeta se ensaya mojada",
     "Se empuja en lugar de tirar",
     "La probeta se lava antes"
    ],
    "c": 0,
    "e": "En el método grab (ISO 13934-2) mordazas estrechas sujetan el centro de una probeta de 100 mm; el tejido lateral ayuda a soportar la carga.",
    "sc": 1
   },
   {
    "q": "¿Qué método de desgarro produce un desgarro doble?",
    "a": [
     "Lengüeta",
     "Pantalón",
     "Ala",
     "Péndulo Elmendorf"
    ],
    "c": 0,
    "e": "En el método de la lengüeta (ISO 13937-4) dos cortes forman una lengüeta; al tirar avanzan dos desgarros a la vez.",
    "sc": 2
   },
   {
    "q": "¿Qué cuenta el ensayo de abrasión Martindale?",
    "a": [
     "Ciclos hasta un punto final, p. ej. dos hilos rotos",
     "El tiempo hasta decolorarse",
     "El número de bolitas por cm²",
     "La presión de agua hasta que pasa"
    ],
    "c": 0,
    "e": "La probeta frota sobre lana siguiendo una trayectoria de Lissajous; se cuentan los ciclos hasta el punto final definido.",
    "sc": 3
   },
   {
    "q": "¿Qué significa la nota de pilling 5?",
    "a": [
     "Sin cambio",
     "Pilling muy intenso",
     "Pilling moderado",
     "Ensayo no superado"
    ],
    "c": 0,
    "e": "La escala va de 5 (sin cambio) a 1 (cambio muy intenso), evaluada con patrones fotográficos.",
    "sc": 4
   },
   {
    "q": "¿Para qué sirve el tejido testigo multifibra en la solidez al lavado?",
    "a": [
     "Muestra qué fibras se manchan con el color",
     "Protege la probeta de las bolas de acero",
     "Mide la temperatura",
     "Evita el encogimiento"
    ],
    "c": 0,
    "e": "Las tiras de distintas fibras muestran cuánto se mancha cada tipo de fibra al lavarse juntas, valorado con la escala de grises para descarga.",
    "sc": 5
   },
   {
    "q": "¿Qué escala usa la solidez a la luz según ISO 105-B02?",
    "a": [
     "Escala de azules 1 a 8",
     "Escala de grises 1 a 5",
     "Porcentaje de variación",
     "Ciclos hasta un agujero"
    ],
    "c": 0,
    "e": "Ocho referencias de lana azul, cada una aproximadamente el doble de sólida que la anterior; la probeta se compara con ellas.",
    "sc": 6
   }
  ],
  "links": [
   [
    "Título, tenacidad y alargamiento",
    "Ensayo de tracción en hilo: fuerza máxima y alargamiento según el principio CRE con el STATIMAT."
   ],
   [
    "Tintura",
    "De dónde viene el color: clases de colorantes y procesos que deciden la solidez."
   ],
   [
    "Acabado químico",
    "Fácil cuidado, antimanchas, antipilling: acabados cuyo efecto se ensaya aquí."
   ],
   [
    "Acabado mecánico",
    "Compactado, perchado, tundido: procesos que influyen en el cambio dimensional y el pilling."
   ],
   [
    "Ligamentos",
    "Tafetán, sarga, raso: el ligamento marca la resistencia, la abrasión y el pilling."
   ]
  ]
 },
 "zh": {
  "ui": {
   "eyebrow": "知识库 · 织物检测",
   "h1": "织物检测：测量面料能承受什么",
   "lead": "面料在销售或加工之前，实验室会按照标准检验它是否达到承诺的性能。八个场景依次展示标准大气、断裂强力与撕破强力、马丁代尔耐磨、起球、耐洗与耐摩擦色牢度、耐光色牢度以及洗涤尺寸变化。",
   "note": "示意图。试验参数来自标准摘要和实验室资料（ISO 139、13934、13937、12947、12945、105、5077）；曲线、颜色变化和分级均有简化。一切以标准原文为准。",
   "pause": "⏸ 暂停",
   "play": "▶ 播放",
   "sl": {
    "rh": "湿度",
    "meth": "方法",
    "tear": "方法",
    "cyc": "摩擦次数",
    "grade": "级数",
    "fx": "试验",
    "bw": "耐光级数",
    "sh": "尺寸变化"
   },
   "lkL": "Knowledge Base 中的相关内容",
   "open": "打开模块"
  },
  "scenes": [
   {
    "k": "标准大气",
    "title": "先调湿，再测试",
    "text": "纺织纤维吸收的水分随空气湿度而变，这会改变质量、强力和伸长。因此试样在测试前要放在 ISO 139 规定的标准大气中，直到质量不再变化，并在同样的大气中测试。用滑块改变相对湿度。",
    "facts": [
     [
      "标准大气",
      "20.0 °C，65.0 % RH"
     ],
     [
      "允差",
      "± 2 °C，± 4 % RH"
     ],
     [
      "其他",
      "23 °C / 50 %，27 °C / 65 %（热带）"
     ],
     [
      "平衡",
      "每隔 2 小时称重"
     ]
    ]
   },
   {
    "k": "断裂强力",
    "title": "拉伸试验：条样法与抓样法",
    "text": "拉伸试验机以恒定速度拉伸夹持的试样直到断裂，并记录力与伸长的关系。条样法由整个试样宽度承受负荷；抓样法只夹住较宽试样的中间部分。用滑块选择方法。",
    "facts": [
     [
      "条样法",
      "ISO 13934-1"
     ],
     [
      "抓样法",
      "ISO 13934-2"
     ],
     [
      "结果",
      "最大力（N）"
     ],
     [
      "方向",
      "经向和纬向分别测试"
     ]
    ]
   },
   {
    "k": "撕破强力",
    "title": "裂口容易继续扩展吗？",
    "text": "一个小切口或勾丝如果继续撕裂，就可能毁掉一件衣服或一块篷布。因此撕破试验从规定的切口开始。ISO 13937 有四种方法：摆锤法、裤形法、翼形法和舌形法。用滑块选择方法。",
    "facts": [
     [
      "标准",
      "ISO 13937 第 1–4 部分"
     ],
     [
      "起点",
      "规定的切口"
     ],
     [
      "结果",
      "撕破强力（N）"
     ],
     [
      "注意",
      "不同方法不能换算"
     ]
    ]
   },
   {
    "k": "耐磨",
    "title": "马丁代尔：磨到损坏的次数",
    "text": "在马丁代尔仪上，圆形试样在负荷下与标准羊毛织物摩擦。运动轨迹是李萨如图形，使试样每一点都受到各个方向的摩擦。记录达到终点所需的摩擦次数，例如断两根纱线。用滑块设置达到的摩擦次数。",
    "facts": [
     [
      "标准",
      "ISO 12947-2"
     ],
     [
      "试样",
      "直径约 38 mm"
     ],
     [
      "负荷",
      "9 kPa 或 12 kPa"
     ],
     [
      "结果",
      "达到终点的摩擦次数"
     ]
    ]
   },
   {
    "k": "起球",
    "title": "表面的小球",
    "text": "摩擦使纤维端从纱线中被拉出，缠结成小球并留在表面。经过规定的处理后，把试样与标准照片对比，从 5 级（无变化）到 1 级（非常严重）评级。用滑块改变级数。",
    "facts": [
     [
      "标准",
      "ISO 12945 第 1–4 部分"
     ],
     [
      "级数",
      "5 至 1，可评半级"
     ],
     [
      "评定",
      "目测，对照标准照片"
     ],
     [
      "常见要求",
      "针织物 3–4 级以上"
     ]
    ]
   },
   {
    "k": "色牢度",
    "title": "耐洗与耐摩擦",
    "text": "色牢度描述染色或印花经受使用和护理的能力。耐洗色牢度中，试样褪色并沾污一起洗涤的贴衬织物；耐摩擦色牢度中，试样沾污白色摩擦布。用灰色样卡从 5 到 1 评级。用滑块选择试验。",
    "facts": [
     [
      "耐洗",
      "ISO 105-C06"
     ],
     [
      "耐摩擦",
      "ISO 105-X12"
     ],
     [
      "灰卡",
      "A02 变色 · A03 沾色"
     ],
     [
      "级数",
      "5（无）至 1（严重）"
     ]
    ]
   },
   {
    "k": "耐光色牢度",
    "title": "氙灯与蓝色羊毛标准",
    "text": "试样与八块蓝色羊毛标准样一起在模拟日光的氙灯下曝晒，每块都有一部分被遮盖。耐光色牢度就是褪色程度与试样相近的那块标准样的编号。用滑块选择试样的耐光级数。",
    "facts": [
     [
      "标准",
      "ISO 105-B02"
     ],
     [
      "光源",
      "氙弧灯，日光 D65"
     ],
     [
      "级数",
      "蓝色羊毛 1 至 8"
     ],
     [
      "级差",
      "每级约耐光一倍"
     ]
    ]
   },
   {
    "k": "尺寸变化",
    "title": "洗涤收缩",
    "text": "在调湿后的试样上做测量标记。按 ISO 6330 洗涤和干燥后再次测量，变化以百分比表示：负号表示收缩，正号表示伸长。右下方列出其他常见试验。用滑块设置尺寸变化。",
    "facts": [
     [
      "标准",
      "ISO 5077、3759、6330"
     ],
     [
      "标记",
      "间距至少 350 mm"
     ],
     [
      "结果",
      "长度和宽度 %"
     ],
     [
      "修约",
      "至 0.5 %"
     ]
    ]
   }
  ],
  "cv": {
   "rhN": "{n} % RH",
   "cycN": "{n} 次",
   "gradeN": "{n} 级",
   "bwN": "{n} 级",
   "kl": {
    "chamber": "恒温恒湿室或试验箱",
    "temp": "20.0 °C",
    "rh": "相对湿度（% RH），绿色：允差 61–69 %",
    "ok": "在标准大气内",
    "no": "超出标准大气",
    "regainT": "纤维回潮率（以干重计）",
    "fibres": [
     "羊毛",
     "粘胶",
     "棉",
     "锦纶",
     "涤纶"
    ],
    "regainN": "65 % RH 下的参考值；其他湿度下的曲线为示意。",
    "alt": "ISO 139 在特殊情况下也允许 23 °C / 50 % RH，热带地区可用 27 °C / 65 % RH。调湿持续到间隔 2 小时的两次称重之间质量几乎不再变化。",
    "why": "在标准大气中，无论哪个实验室测试，结果都可比较。羊毛和粘胶吸水多，涤纶几乎不吸水。粘胶湿态强力明显下降，而棉湿态强力反而略有提高。",
    "whyNo": "超出允差时结果不符合标准：吸湿纤维的质量、强力和伸长都会偏离。试样必须重新在标准大气中调湿。"
   },
   "zg": {
    "cross": "横梁以恒定速度移动（CRE）",
    "clamp25": "夹钳仅宽 25 mm",
    "broke": "试样断裂",
    "eL": "伸长",
    "fL": "力",
    "fmax": "最大力",
    "schem": "曲线为示意；数值取决于材料和结构。",
    "widthL": "试样宽度",
    "gaugeL": "隔距长度",
    "speedL": "速度",
    "resL": "结果",
    "useL": "适用",
    "note": "经向和纬向各测试多块试样。抓样法中未被夹持的两侧织物也分担负荷，因此条样法和抓样法的数值不能直接比较。美国抓样标准 ASTM D5034 的速度为 300 mm/min，而非 50 mm/min。缝口强力另有 ISO 13935 方法。",
    "nowF": "力 ≈ {f} N",
    "m": [
     {
      "n": "条样法 ISO 13934-1",
      "w": "50 mm",
      "l": "200 mm",
      "v": "100 mm/min",
      "r": "最大力（N）和最大力伸长率（%）",
      "u": "主要用于机织物"
     },
     {
      "n": "抓样法 ISO 13934-2",
      "w": "试样宽 100 mm",
      "l": "100 mm",
      "v": "50 mm/min",
      "r": "仅最大力（N）",
      "u": "机织物；力只从部分宽度传入，更接近实际使用"
     }
    ]
   },
   "wr": {
    "pend": "摆锤",
    "fixed": "固定夹钳",
    "slit": "切口，裂口向上扩展",
    "tongue": "舌片被拉向另一侧",
    "wing": "倾斜的翼",
    "tipL": "裂口尖端",
    "pathL": "位移",
    "forceL": "力",
    "mean": "峰值平均",
    "energyT": "摆锤损失的能量",
    "energy": "撕裂所需的力越大，下落摆锤损失的能量越多，由此计算撕破强力。",
    "prL": "原理",
    "devL": "仪器",
    "hintL": "说明",
    "note": "撕破强力对工作服、帐篷、篷布和气球织物很重要。机织物中纱线依次断裂，因此力曲线呈锯齿状，评定的是峰值。四种方法得出的数值不同，结果必须与方法一起给出。",
    "m": [
     {
      "n": "埃尔门多夫摆锤法（第 1 部分）",
      "p": "下落的摆锤使有切口的试样突然继续撕裂（单舌撕裂）。",
      "d": "冲击摆锤式仪器",
      "h": "快速、应用广泛；测量消耗的能量。"
     },
     {
      "n": "裤形法（第 2 部分）",
      "p": "试样中间切开，两条“裤腿”向相反方向拉伸（单缝撕裂）。",
      "d": "等速伸长（CRE）拉伸试验机",
      "h": "不适用于针织物和弹性机织物。"
     },
     {
      "n": "翼形法（第 3 部分）",
      "p": "与裤形类似，但两腿呈斜角，使裂口更稳定地沿中间扩展（单缝撕裂）。",
      "d": "拉伸试验机（CRE）",
      "h": "用于裤形法中裂口向侧面偏移的织物。"
     },
     {
      "n": "舌形法（第 4 部分）",
      "p": "两道平行切口形成舌片，舌片与其余部分反向拉伸，同时扩展两条裂口（双缝撕裂）。",
      "d": "拉伸试验机（CRE）",
      "h": "数值高于单缝撕裂方法。"
     }
    ]
   },
   "ms": {
    "abr": "磨料：标准羊毛织物",
    "hold": "试样夹持器（试样直径 38 mm）",
    "lis": "李萨如轨迹（示意）",
    "classT": "家具布参考值（达到终点的摩擦次数，12 kPa）",
    "cl": [
     "装饰",
     "轻度",
     "家用",
     "重度",
     "工程"
    ],
    "cld": [
     "低于 10 000 次：靠垫、装饰、很少使用的家具。",
     "10 000 至 15 000 次：偶尔使用的扶手椅和椅子。",
     "15 000 至 25 000 次：一般家用；部分家具零售商要求至少 20 000 次。",
     "25 000 至 40 000 次：使用频繁的沙发、有儿童或宠物的家庭。",
     "40 000 次以上：办公、餐饮、工程项目；酒店大堂常要求 50 000 次以上。"
    ],
    "panelT": "马丁代尔 ISO 12947-2",
    "loadL": "负荷",
    "load": "服装和家用纺织品 9 kPa；家具布、工作服和技术纺织品 12 kPa",
    "endL": "终点",
    "end": "例如机织物断两根纱线、针织物出现破洞或绒面磨损",
    "inspL": "程序",
    "insp": "按规定间隔检查；结果为达到终点前的最后摩擦次数。",
    "req": "数值必须与负荷一起给出：12 kPa 下的 20 000 次比 9 kPa 下要求更高。",
    "note": "此分级来自生产商和零售商资料，而非标准本身。北美家具布还常用 Wyzenbeek 试验，其“双次摩擦”不能换算为马丁代尔次数。"
   },
   "pi": {
    "light": "示意图；表面与标准照片对比评定。",
    "scaleT": "评级（ISO 12945）",
    "g": [
     "无变化。",
     "轻微变化：起毛或开始出现小球。",
     "中等变化：明显的小球和起毛。",
     "明显变化：大面积出现许多小球。",
     "非常严重：整个表面布满小球。"
    ],
    "methT": "方法",
    "meth": [
     [
      "起球箱：套在管上的试样在衬软木的箱中翻滚。",
      "第 1 部分"
     ],
     [
      "改型马丁代尔：在 125 至 7000 次的固定阶段评定。",
      "第 2 部分"
     ],
     [
      "随机翻滚：试样在衬软木的转筒中翻滚。",
      "第 3 部分"
     ],
     [
      "对各种方法处理后的试样进行目测评定。",
      "第 4 部分"
     ]
    ],
    "assess": "在评级箱中用低角度光照评定（观察角 5–15°），试样旁放未处理的织物。结果修约到半级。",
    "note": "涤纶或腈纶混纺中纤维强度高，小球不易脱落而一直可见。长纤维、较高捻度、烧毛和紧密结构可以减少起球。许多零售商要求针织物至少达到 3–4 级。"
   },
   "fe": {
    "bath": "容器在恒温水浴中旋转",
    "balls": "钢珠增强机械作用",
    "compT": "组合试样 10 × 4 cm",
    "mf": [
     "醋酯",
     "棉",
     "锦纶",
     "涤纶",
     "腈纶",
     "羊毛"
    ],
    "sewn": "沿一条短边与多纤维贴衬织物缝合",
    "dyed": "试样",
    "spec": "放在底板上的染色试样",
    "finger": "带白色棉摩擦布的摩擦头",
    "stroke": "动程 104 mm · 10 秒 10 次",
    "dry": "干",
    "wet": "湿",
    "clothT": "试验后的摩擦布（示例）",
    "gsC": "变色灰卡（A02）",
    "gsS": "沾色灰卡（A03）",
    "condL": "试验条件",
    "evalL": "评定",
    "note": "5 级表示无变色或无沾色，1 级表示非常严重，中间可评半级。许多买家接受 4 级以上，有的接受 3–4 级。除目测外也可用仪器评定（ISO 105-A04/A05）。",
    "m": [
     {
      "n": "耐洗色牢度 ISO 105-C06",
      "c": "钢制容器，标准洗涤剂，温度按试验等级；单次（S）或多次（M）试验",
      "e": "试样变色及各贴衬条的沾色",
      "d": "容器中运行一次相当于一次或多次家庭或商业洗涤。干燥后评定：试样褪色多少，贴衬织物中哪些纤维沾上了颜色？"
     },
     {
      "n": "耐摩擦色牢度 ISO 105-X12",
      "c": "摩擦头，压力 9 N，动程 104 mm，10 秒 10 次，干摩和湿摩",
      "e": "白色摩擦布的沾色",
      "d": "显示表面未固着的染料是否会转移，例如深色牛仔裤沾到浅色沙发上。湿摩结果通常比干摩差。试样至少 50 × 140 mm。"
     }
    ]
   },
   "li": {
    "lamp": "带滤光片的氙弧灯",
    "spec": "试样",
    "exposed": "曝晒",
    "masked": "遮盖",
    "refT": "蓝色羊毛标准 1–8 与试样一起曝晒",
    "expo": "曝晒时间",
    "result": "耐光色牢度 {n} 级",
    "sc": [
     "试样褪色与 1 号标准相近：很差。",
     "试样褪色与 2 号标准相近：差。",
     "试样褪色与 3 号标准相近：一般。",
     "试样褪色与 4 号标准相近：较好。",
     "试样褪色与 5 号标准相近：好。",
     "试样褪色与 6 号标准相近：很好。",
     "试样褪色与 7 号标准相近：优良。",
     "试样褪色与 8 号标准相近：极佳。"
    ],
    "panelT": "ISO 105-B02",
    "srcL": "光源",
    "src": "经滤光的氙弧灯，模拟日光光谱（D65）",
    "ruleL": "蓝色羊毛标准",
    "rule": "八块染成蓝色的羊毛织物，从 1（耐光性很低）到 8（很高）；每一级的耐光性约为前一级的两倍。",
    "methL": "评定",
    "meth": "用灰卡评定曝晒部分与遮盖部分的对比，并与标准样比较。美国常用 L2–L9 标准，两者结果不能互换。",
    "note": "耐光色牢度对窗帘、遮阳篷、汽车座椅和户外纺织品很重要。高级别需要很长的曝晒时间，因此质量控制中常只对单一标准样做合格/不合格试验。各级的文字描述为常用说法。"
   },
   "ma": {
    "before": "虚线：洗涤前的试样",
    "marks": "红色：测量标记，每个方向 3 对，间距至少 350 mm",
    "exag": "为便于观察，尺寸变化放大三倍",
    "lenL": "长度",
    "calcT": "按 ISO 5077 计算",
    "formula": "(洗后 − 洗前) ÷ 洗前 × 100",
    "example": "({a} mm − {b} mm) ÷ {b} mm × 100",
    "shrink": "收缩（负值）",
    "grow": "伸长（正值）",
    "stable": "尺寸稳定",
    "width": "本例宽度：{w} %",
    "panelT": "流程",
    "specL": "试样",
    "spec": "至少 500 × 500 mm，在标准大气中调湿并做标记（ISO 3759）",
    "washL": "处理",
    "wash": "按 ISO 6330 家庭洗涤和干燥，程序由双方商定；工作服按 ISO 15797 工业洗涤",
    "resL": "结果",
    "res": "长度和宽度的平均值，修约至 0.5 %；作为护理标签的依据",
    "furtherT": "其他试验",
    "further": [
     [
      "顶破强力：膜片将试样鼓起直到破裂。适用于针织物、非织造布和层压织物；800 kPa 以内液压式与气压式结果相当。",
      "ISO 13938"
     ],
     [
      "缝口强力：垂直于缝线拉伸时的最大力。",
      "ISO 13935"
     ],
     [
      "透气性：在规定压差下通过一定面积的空气流量。",
      "ISO 9237"
     ]
    ],
    "note": "棉、粘胶和针织物的尺寸变化尤其值得关注。合成纤维的热定形和棉的机械预缩可以减少收缩。允许的数值由买卖双方约定。"
   }
  },
  "quiz": [
   {
    "q": "ISO 139 规定的纺织品测试标准大气是什么？",
    "a": [
     "20 °C，65 % RH",
     "23 °C，30 % RH",
     "25 °C，80 % RH",
     "18 °C，50 % RH"
    ],
    "c": 0,
    "e": "标准为 20.0 °C、65.0 % RH，允差 ± 2 °C 和 ± 4 %；23 °C/50 % 和 27 °C/65 % 为替代条件。",
    "sc": 0
   },
   {
    "q": "为什么试样在测试前必须调湿？",
    "a": [
     "因为湿度会改变质量、强力和伸长",
     "否则无法测量颜色",
     "为了给试样消毒",
     "为了让它更快断裂"
    ],
    "c": 0,
    "e": "许多纤维会吸水。只有与标准大气达到平衡后，各实验室的结果才能比较。",
    "sc": 0
   },
   {
    "q": "抓样法与条样法有何不同？",
    "a": [
     "只夹住较宽试样的中间部分",
     "试样在湿态下测试",
     "是压而不是拉",
     "试样要先洗涤"
    ],
    "c": 0,
    "e": "抓样法（ISO 13934-2）用窄夹钳夹住 100 mm 宽试样的中间，两侧织物也分担负荷。",
    "sc": 1
   },
   {
    "q": "哪种撕破方法产生双缝撕裂？",
    "a": [
     "舌形法",
     "裤形法",
     "翼形法",
     "埃尔门多夫摆锤法"
    ],
    "c": 0,
    "e": "舌形法（ISO 13937-4）中两道切口形成舌片，拉伸时两条裂口同时扩展。",
    "sc": 2
   },
   {
    "q": "马丁代尔耐磨试验记录什么？",
    "a": [
     "达到终点（如断两根纱）的摩擦次数",
     "褪色所需的时间",
     "每平方厘米的小球数",
     "渗水时的水压"
    ],
    "c": 0,
    "e": "试样沿李萨如轨迹在羊毛织物上摩擦，记录达到规定终点的次数。",
    "sc": 3
   },
   {
    "q": "起球 5 级表示什么？",
    "a": [
     "无变化",
     "非常严重起球",
     "中等起球",
     "试验不合格"
    ],
    "c": 0,
    "e": "级数从 5 级（无变化）到 1 级（非常严重），对照标准照片评定。",
    "sc": 4
   },
   {
    "q": "耐洗色牢度试验中多纤维贴衬织物有什么作用？",
    "a": [
     "显示颜色会沾到哪些纤维上",
     "保护试样不被钢珠损伤",
     "测量温度",
     "防止收缩"
    ],
    "c": 0,
    "e": "不同纤维的条带显示一起洗涤时每种纤维的沾色程度，用沾色灰卡评定。",
    "sc": 5
   },
   {
    "q": "ISO 105-B02 耐光色牢度使用什么级数？",
    "a": [
     "蓝色羊毛标准 1 至 8",
     "灰卡 1 至 5",
     "尺寸变化百分比",
     "磨出破洞的次数"
    ],
    "c": 0,
    "e": "八块蓝色羊毛标准样，每一级耐光性约为前一级的两倍，试样与其比较。",
    "sc": 6
   }
  ],
  "links": [
   [
    "纤度、强度和伸长",
    "纱线拉伸试验：用 STATIMAT 按 CRE 原理测最大强力和伸长。"
   ],
   [
    "染色",
    "颜色从何而来：决定色牢度的染料类别和工艺。"
   ],
   [
    "化学后整理",
    "免烫、易去污、抗起球：此处检验的就是这些整理的效果。"
   ],
   [
    "机械后整理",
    "预缩、起绒、剪毛：影响尺寸变化和起球的工艺。"
   ],
   [
    "织物组织",
    "平纹、斜纹、缎纹：组织决定强力、耐磨和起球。"
   ]
  ]
 }
};
