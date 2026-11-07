window.TEXTS = {
 "de": {
  "ui": {
   "eyebrow": "Onboarding · Labor",
   "h1": "Titer, Festigkeit und Dehnung mit dem STATIMAT DS",
   "lead": "Das STATIMAT DS prüft Garnspulen automatisch: Es bestimmt den Titer durch Wägen einer abgemessenen Garnlänge und zieht Garnabschnitte bis zum Bruch. Aus beidem ergeben sich Höchstzugkraft, Bruchdehnung und Festigkeit. Fünf kurze Szenen zeigen, wie das funktioniert.",
   "note": "Schematische Darstellung. Gerätedaten aus dem Textechno-Datenblatt zum STATIMAT DS. Garnwerte und Kraft-Dehnungs-Kurven sind Beispielwerte zur Veranschaulichung, keine Messergebnisse.",
   "pause": "⏸ Pause",
   "play": "▶ Abspielen",
   "scenes": "Szenen",
   "yarn": "Garn",
   "dec": ",",
   "clickHint": "Ein Prüfmodul im Gerät anklicken: Es wird hier erklärt."
  },
  "cv": {
   "cards": [
    [
     "Titer",
     "167 dtex",
     "1,67 g pro 1000 m"
    ],
    [
     "Höchstzugkraft",
     "600 cN",
     "grösste Kraft im Zugversuch"
    ],
    [
     "Bruchdehnung",
     "22 %",
     "Längenzunahme beim Bruch"
    ],
    [
     "Festigkeit",
     "3,6 cN/dtex",
     "600 cN / 167 dtex"
    ]
   ],
   "example": "Beispiel: DTY 167 dtex",
   "fStrength": "Festigkeit",
   "fForce": "Höchstzugkraft",
   "fTiter": "Titer",
   "fNote": "macht Garne unterschiedlicher Feinheit vergleichbar",
   "peakNote": "Höchstzugkraft und Bruchdehnung",
   "forceAx": "Kraft in cN",
   "elongAx": "Dehnung",
   "device": "STATIMAT DS, schematisch",
   "changerSub": "20 bis 40 Plätze",
   "scale": "Waage",
   "clampLen": "Einspannlänge",
   "clampsSub": "2 pneumatische Klemmen",
   "pc": "PC · TESTCONTROL",
   "delivery": "Liefereinrichtung",
   "measLen": "misst die Länge",
   "vac": "Vakuumförderer",
   "chamber": "Sammelkammer",
   "scaleRes": "Waage · 1 mg Auflösung",
   "len": "Länge",
   "mass": "Masse",
   "formula": "Titer = Masse / Länge × 10 000",
   "formula2": "= {m} g / {l} m × 10 000",
   "setLen": "Messlänge eingestellt: {l} m (Beispiel)",
   "tension": "Fadenspannung wird überwacht und bei Bedarf rechnerisch korrigiert",
   "running": "Garn wird abgemessen und in die Sammelkammer gefördert …",
   "result": "Ergebnis: {d} dtex",
   "fixed": "feste Klemme",
   "moving": "fährt mit konstanter Geschwindigkeit",
   "gauge": "Einspannlänge, z. B. 500 mm",
   "force": "Kraft",
   "elong": "Dehnung",
   "peakF": "Höchstzugkraft {f} cN",
   "peakE": "Bruchdehnung {e} %",
   "crimp": "zuerst wird die Kräuselung ausgezogen",
   "flow": "langer Fliessbereich: Ketten richten sich aus",
   "broke": "{n}: gerissen bei {f} cN und {e} % Dehnung (Beispielwerte)",
   "pulling": "Klemme fährt, Kraft und Weg werden laufend gemessen …",
   "forceAx2": "Höchstzugkraft in cN",
   "elongAx2": "Bruchdehnung",
   "ofN": "{n} von 20 Prüfungen",
   "rows": [
    "Höchstzugkraft",
    "Bruchdehnung",
    "Titer",
    "Festigkeit"
   ],
   "sameBobbin": "aus derselben Spule",
   "meanTiter": "Mittelwert / Titer",
   "sim": "Beispieldaten, simuliert"
  },
  "stations": [
   {
    "n": "Spulenwechsler",
    "s": "Spulen-|wechsler",
    "d": "Bringt die nächste Spule in Position: 20 Plätze, erweiterbar auf 40."
   },
   {
    "n": "Greifarm",
    "s": "Greifarm",
    "d": "Rotierender Greifarm: fädelt das Garn automatisch ein."
   },
   {
    "n": "Liefereinrichtung",
    "s": "Liefer-|einrichtung",
    "d": "Fördert das Garn mit gemessener Länge zu den Prüfmodulen: bis 500 m/min, Längenauflösung 0,3 mm."
   },
   {
    "n": "Titermessung",
    "s": "Titer",
    "d": "Eine abgemessene Garnlänge kommt in die Sammelkammer auf der Waage. Aus Masse und Länge ergibt sich der Titer."
   },
   {
    "n": "Gleichmässigkeitssensor",
    "s": "Gleich-|mässigkeit",
    "d": "Kapazitiver Sensor: misst die Masseschwankungen entlang des Garns."
   },
   {
    "n": "Verwirbelungssensor (optional)",
    "s": "Verwir-|belung",
    "d": "Optischer Sensor: zählt die Knoten eines verwirbelten Garns."
   },
   {
    "n": "Zugprüfung",
    "s": "Zug-|prüfung",
    "d": "Zwei pneumatische Klemmen: Das Garn wird nach dem CRE-Prinzip bis zum Bruch gezogen."
   }
  ],
  "scenes": [
   {
    "k": "Kennwerte",
    "title": "Vier Kennwerte, die jedes Labor braucht",
    "text": "Der Titer sagt, wie fein ein Garn ist: Er gibt die Masse pro Länge an. Im Zugversuch werden die Höchstzugkraft und die Dehnung beim Bruch gemessen. Teilt man die Höchstzugkraft durch den Titer, erhält man die Festigkeit. So lassen sich Garne unterschiedlicher Feinheit vergleichen.",
    "facts": [
     [
      "Titer",
      "dtex = Gramm pro 10 000 m"
     ],
     [
      "Höchstzugkraft",
      "in cN"
     ],
     [
      "Bruchdehnung",
      "in % der Einspannlänge"
     ],
     [
      "Festigkeit",
      "cN/dtex = Höchstzugkraft / Titer"
     ]
    ]
   },
   {
    "k": "Aufbau",
    "title": "Ein Gerät, mehrere Prüfungen",
    "text": "Ein Spulenwechsler bringt die Spulen nacheinander in Position. Ein Greifarm fädelt das Garn automatisch ein. Eine Liefereinrichtung führt es den Prüfmodulen zu: der Titermessung mit Waage, dem Gleichmässigkeitssensor, optional dem Verwirbelungssensor und dem Zugprüfteil mit zwei pneumatischen Klemmen. Gesteuert wird alles über einen PC.",
    "facts": [
     [
      "Spulenwechsler",
      "20 Plätze, erweiterbar auf 40"
     ],
     [
      "Einfädeln",
      "automatisch, rotierender Greifarm"
     ],
     [
      "Liefereinrichtung",
      "bis 500 m/min, Längenauflösung 0,3 mm"
     ],
     [
      "Software",
      "Textechno TESTCONTROL"
     ],
     [
      "Module",
      "im Bild anklicken, um sie erklärt zu bekommen"
     ]
    ]
   },
   {
    "k": "Titer",
    "title": "Titermessung: Länge abmessen und wägen",
    "text": "Die Liefereinrichtung fördert eine voreingestellte Garnlänge über einen Vakuumförderer in eine Sammelkammer. Die Kammer steht auf einer elektronischen Waage. Aus Masse und Länge ergibt sich der Titer. Die Fadenspannung wird dabei überwacht und bei Bedarf rechnerisch korrigiert.",
    "facts": [
     [
      "Messlänge",
      "1–1000 m, voreinstellbar"
     ],
     [
      "Waage",
      "300 g Bereich, 1 mg Auflösung"
     ],
     [
      "Formel",
      "dtex = Masse in g / Länge in m × 10 000"
     ],
     [
      "Normen",
      "ISO 2060, ASTM D6587"
     ]
    ]
   },
   {
    "k": "Zugversuch",
    "title": "Zugversuch nach dem CRE-Prinzip",
    "text": "Ein Garnabschnitt wird zwischen zwei pneumatische Klemmen gespannt. Die untere Klemme fährt mit konstanter Geschwindigkeit weg: Das ist das CRE-Prinzip (constant rate of extension). Gemessen werden laufend Kraft und Weg, bis das Garn reisst. Mit dem Regler lassen sich POY, FDY und DTY vergleichen.",
    "facts": [
     [
      "Prinzip",
      "CRE: konstante Dehngeschwindigkeit"
     ],
     [
      "Einspannlänge",
      "ab 80 mm, Klemmweg bis 1000 mm"
     ],
     [
      "Kraftmessung",
      "500 N, optional 1500 N"
     ],
     [
      "Normen",
      "ISO 2062, ASTM D2256, ASTM D885"
     ]
    ]
   },
   {
    "k": "Festigkeit",
    "title": "Von der Einzelprüfung zum Spulenergebnis",
    "text": "Ein einzelner Zugversuch streut. Deshalb werden pro Spule mehrere Abschnitte gezogen und statistisch ausgewertet: Mittelwert und Variationskoeffizient für Höchstzugkraft und Bruchdehnung. Mit dem Titer aus derselben Spule rechnet die Software die Festigkeit aus.",
    "facts": [
     [
      "Prüfungen",
      "mehrere Abschnitte pro Spule"
     ],
     [
      "Statistik",
      "Mittelwert, Variationskoeffizient"
     ],
     [
      "Festigkeit",
      "mittlere Höchstzugkraft / Titer"
     ],
     [
      "Vorteil",
      "Titer und Zugwerte aus derselben Spule"
     ]
    ]
   }
  ]
 },
 "en": {
  "ui": {
   "eyebrow": "Onboarding · Lab",
   "h1": "Count, tenacity and elongation with the STATIMAT DS",
   "lead": "The STATIMAT DS tests yarn packages automatically: it determines the count by weighing a measured yarn length and pulls yarn sections until they break. Both together give maximum force, elongation at break and tenacity. Five short scenes show how it works.",
   "note": "Schematic representation. Device data from the Textechno data sheet for the STATIMAT DS. Yarn values and force-elongation curves are example values for illustration, not measurement results.",
   "pause": "⏸ Pause",
   "play": "▶ Play",
   "scenes": "Scenes",
   "yarn": "Yarn",
   "dec": ".",
   "clickHint": "Click a test module of the device: it is explained here."
  },
  "cv": {
   "cards": [
    [
     "Count",
     "167 dtex",
     "1.67 g per 1000 m"
    ],
    [
     "Maximum force",
     "600 cN",
     "highest force in the tensile test"
    ],
    [
     "Elongation at break",
     "22 %",
     "increase in length at break"
    ],
    [
     "Tenacity",
     "3.6 cN/dtex",
     "600 cN / 167 dtex"
    ]
   ],
   "example": "Example: DTY 167 dtex",
   "fStrength": "Tenacity",
   "fForce": "Maximum force",
   "fTiter": "Count",
   "fNote": "makes yarns of different fineness comparable",
   "peakNote": "maximum force and elongation at break",
   "forceAx": "Force in cN",
   "elongAx": "Elongation",
   "device": "STATIMAT DS, schematic",
   "changerSub": "20 to 40 positions",
   "scale": "Balance",
   "clampLen": "Gauge length",
   "clampsSub": "2 pneumatic clamps",
   "pc": "PC · TESTCONTROL",
   "delivery": "Feed unit",
   "measLen": "measures the length",
   "vac": "Vacuum conveyor",
   "chamber": "Collecting chamber",
   "scaleRes": "Balance · 1 mg resolution",
   "len": "Length",
   "mass": "Mass",
   "formula": "Count = mass / length × 10,000",
   "formula2": "= {m} g / {l} m × 10,000",
   "setLen": "Test length set: {l} m (example)",
   "tension": "Yarn tension is monitored and corrected mathematically if needed",
   "running": "Yarn is measured and conveyed into the collecting chamber …",
   "result": "Result: {d} dtex",
   "fixed": "fixed clamp",
   "moving": "moves at constant speed",
   "gauge": "Gauge length, e.g. 500 mm",
   "force": "Force",
   "elong": "Elongation",
   "peakF": "Maximum force {f} cN",
   "peakE": "Elongation at break {e} %",
   "crimp": "first the crimp is pulled out",
   "flow": "long yield region: chains align",
   "broke": "{n}: broken at {f} cN and {e} % elongation (example values)",
   "pulling": "Clamp moves, force and displacement are measured continuously …",
   "forceAx2": "Maximum force in cN",
   "elongAx2": "Elongation at break",
   "ofN": "{n} of 20 tests",
   "rows": [
    "Maximum force",
    "Elongation at break",
    "Count",
    "Tenacity"
   ],
   "sameBobbin": "from the same package",
   "meanTiter": "mean / count",
   "sim": "Example data, simulated"
  },
  "stations": [
   {
    "n": "Package changer",
    "s": "Package|changer",
    "d": "Brings the next package into position: 20 positions, expandable to 40."
   },
   {
    "n": "Gripper arm",
    "s": "Gripper|arm",
    "d": "Rotating gripper arm: threads the yarn in automatically."
   },
   {
    "n": "Feed unit",
    "s": "Feed|unit",
    "d": "Feeds the yarn with measured length to the test modules: up to 500 m/min, length resolution 0.3 mm."
   },
   {
    "n": "Count measurement",
    "s": "Count",
    "d": "A measured yarn length goes into the collecting chamber on the balance. Mass and length give the count."
   },
   {
    "n": "Evenness sensor",
    "s": "Even-|ness",
    "d": "Capacitive sensor: measures the mass variations along the yarn."
   },
   {
    "n": "Intermingling sensor (optional)",
    "s": "Inter-|mingling",
    "d": "Optical sensor: counts the nips of an intermingled yarn."
   },
   {
    "n": "Tensile test",
    "s": "Tensile|test",
    "d": "Two pneumatic clamps: the yarn is pulled to break by the CRE principle."
   }
  ],
  "scenes": [
   {
    "k": "Key figures",
    "title": "Four key figures every lab needs",
    "text": "The count tells how fine a yarn is: it gives the mass per length. The tensile test measures the maximum force and the elongation at break. Dividing the maximum force by the count gives the tenacity. This makes yarns of different fineness comparable.",
    "facts": [
     [
      "Count",
      "dtex = grams per 10,000 m"
     ],
     [
      "Maximum force",
      "in cN"
     ],
     [
      "Elongation at break",
      "in % of the gauge length"
     ],
     [
      "Tenacity",
      "cN/dtex = maximum force / count"
     ]
    ]
   },
   {
    "k": "Set-up",
    "title": "One device, several tests",
    "text": "A package changer brings the packages into position one after another. A gripper arm threads the yarn in automatically. A feed unit leads it to the test modules: count measurement with balance, evenness sensor, optionally the intermingling sensor, and the tensile tester with two pneumatic clamps. Everything is controlled by a PC.",
    "facts": [
     [
      "Package changer",
      "20 positions, expandable to 40"
     ],
     [
      "Threading",
      "automatic, rotating gripper arm"
     ],
     [
      "Feed unit",
      "up to 500 m/min, length resolution 0.3 mm"
     ],
     [
      "Software",
      "Textechno TESTCONTROL"
     ],
     [
      "Modules",
      "click them in the picture to have them explained"
     ]
    ]
   },
   {
    "k": "Count",
    "title": "Count measurement: measure the length and weigh",
    "text": "The feed unit conveys a preset yarn length via a vacuum conveyor into a collecting chamber. The chamber stands on an electronic balance. Mass and length give the count. The yarn tension is monitored and corrected mathematically if needed.",
    "facts": [
     [
      "Test length",
      "1–1000 m, presettable"
     ],
     [
      "Balance",
      "300 g range, 1 mg resolution"
     ],
     [
      "Formula",
      "dtex = mass in g / length in m × 10,000"
     ],
     [
      "Standards",
      "ISO 2060, ASTM D6587"
     ]
    ]
   },
   {
    "k": "Tensile test",
    "title": "Tensile test by the CRE principle",
    "text": "A yarn section is clamped between two pneumatic clamps. The lower clamp moves away at constant speed: this is the CRE principle (constant rate of extension). Force and displacement are measured continuously until the yarn breaks. Use the slider to compare POY, FDY and DTY.",
    "facts": [
     [
      "Principle",
      "CRE: constant rate of extension"
     ],
     [
      "Gauge length",
      "from 80 mm, clamp travel up to 1000 mm"
     ],
     [
      "Force measurement",
      "500 N, optionally 1500 N"
     ],
     [
      "Standards",
      "ISO 2062, ASTM D2256, ASTM D885"
     ]
    ]
   },
   {
    "k": "Tenacity",
    "title": "From the single test to the package result",
    "text": "A single tensile test scatters. That is why several sections per package are pulled and evaluated statistically: mean and coefficient of variation for maximum force and elongation at break. With the count from the same package the software calculates the tenacity.",
    "facts": [
     [
      "Tests",
      "several sections per package"
     ],
     [
      "Statistics",
      "mean, coefficient of variation"
     ],
     [
      "Tenacity",
      "mean maximum force / count"
     ],
     [
      "Advantage",
      "count and tensile values from the same package"
     ]
    ]
   }
  ]
 },
 "es": {
  "ui": {
   "eyebrow": "Onboarding · Laboratorio",
   "h1": "Título, tenacidad y alargamiento con el STATIMAT DS",
   "lead": "El STATIMAT DS ensaya bobinas de hilo automáticamente: determina el título pesando una longitud de hilo medida y estira tramos de hilo hasta la rotura. De ambos resultan la fuerza máxima, el alargamiento a la rotura y la tenacidad. Cinco escenas cortas muestran cómo funciona.",
   "note": "Representación esquemática. Datos del equipo según la hoja técnica de Textechno del STATIMAT DS. Los valores del hilo y las curvas fuerza-alargamiento son valores de ejemplo, no resultados de medición.",
   "pause": "⏸ Pausa",
   "play": "▶ Reproducir",
   "scenes": "Escenas",
   "yarn": "Hilo",
   "dec": ",",
   "clickHint": "Haz clic en un módulo de ensayo del equipo: se explica aquí."
  },
  "cv": {
   "cards": [
    [
     "Título",
     "167 dtex",
     "1,67 g por 1000 m"
    ],
    [
     "Fuerza máxima",
     "600 cN",
     "mayor fuerza en el ensayo de tracción"
    ],
    [
     "Alargamiento a la rotura",
     "22 %",
     "aumento de longitud en la rotura"
    ],
    [
     "Tenacidad",
     "3,6 cN/dtex",
     "600 cN / 167 dtex"
    ]
   ],
   "example": "Ejemplo: DTY 167 dtex",
   "fStrength": "Tenacidad",
   "fForce": "Fuerza máxima",
   "fTiter": "Título",
   "fNote": "permite comparar hilos de distinta finura",
   "peakNote": "fuerza máxima y alargamiento a la rotura",
   "forceAx": "Fuerza en cN",
   "elongAx": "Alargamiento",
   "device": "STATIMAT DS, esquema",
   "changerSub": "de 20 a 40 posiciones",
   "scale": "Balanza",
   "clampLen": "Longitud de sujeción",
   "clampsSub": "2 pinzas neumáticas",
   "pc": "PC · TESTCONTROL",
   "delivery": "Unidad de alimentación",
   "measLen": "mide la longitud",
   "vac": "Transportador por vacío",
   "chamber": "Cámara colectora",
   "scaleRes": "Balanza · resolución 1 mg",
   "len": "Longitud",
   "mass": "Masa",
   "formula": "Título = masa / longitud × 10 000",
   "formula2": "= {m} g / {l} m × 10 000",
   "setLen": "Longitud de ensayo: {l} m (ejemplo)",
   "tension": "La tensión del hilo se vigila y, si hace falta, se corrige por cálculo",
   "running": "El hilo se mide y se transporta a la cámara colectora …",
   "result": "Resultado: {d} dtex",
   "fixed": "pinza fija",
   "moving": "se desplaza a velocidad constante",
   "gauge": "Longitud de sujeción, p. ej. 500 mm",
   "force": "Fuerza",
   "elong": "Alargamiento",
   "peakF": "Fuerza máxima {f} cN",
   "peakE": "Alargamiento a la rotura {e} %",
   "crimp": "primero se estira el rizado",
   "flow": "zona de fluencia larga: las cadenas se orientan",
   "broke": "{n}: roto a {f} cN y {e} % de alargamiento (valores de ejemplo)",
   "pulling": "La pinza se desplaza, fuerza y recorrido se miden continuamente …",
   "forceAx2": "Fuerza máxima en cN",
   "elongAx2": "Alargamiento a la rotura",
   "ofN": "{n} de 20 ensayos",
   "rows": [
    "Fuerza máxima",
    "Alargamiento a la rotura",
    "Título",
    "Tenacidad"
   ],
   "sameBobbin": "de la misma bobina",
   "meanTiter": "media / título",
   "sim": "Datos de ejemplo, simulados"
  },
  "stations": [
   {
    "n": "Cambiador de bobinas",
    "s": "Cambiador|de bobinas",
    "d": "Pone en posición la siguiente bobina: 20 posiciones, ampliable a 40."
   },
   {
    "n": "Brazo de agarre",
    "s": "Brazo de|agarre",
    "d": "Brazo de agarre giratorio: enhebra el hilo automáticamente."
   },
   {
    "n": "Unidad de alimentación",
    "s": "Alimen-|tación",
    "d": "Lleva el hilo con longitud medida a los módulos de ensayo: hasta 500 m/min, resolución de longitud 0,3 mm."
   },
   {
    "n": "Medición del título",
    "s": "Título",
    "d": "Una longitud de hilo medida va a la cámara colectora sobre la balanza. De la masa y la longitud resulta el título."
   },
   {
    "n": "Sensor de regularidad",
    "s": "Regula-|ridad",
    "d": "Sensor capacitivo: mide las variaciones de masa a lo largo del hilo."
   },
   {
    "n": "Sensor de entrelazado (opcional)",
    "s": "Entre-|lazado",
    "d": "Sensor óptico: cuenta los nudos de un hilo entrelazado."
   },
   {
    "n": "Ensayo de tracción",
    "s": "Tracción",
    "d": "Dos pinzas neumáticas: el hilo se estira hasta la rotura según el principio CRE."
   }
  ],
  "scenes": [
   {
    "k": "Indicadores",
    "title": "Cuatro indicadores que todo laboratorio necesita",
    "text": "El título indica lo fino que es un hilo: da la masa por longitud. En el ensayo de tracción se miden la fuerza máxima y el alargamiento en la rotura. Si se divide la fuerza máxima por el título, se obtiene la tenacidad. Así se pueden comparar hilos de distinta finura.",
    "facts": [
     [
      "Título",
      "dtex = gramos por 10 000 m"
     ],
     [
      "Fuerza máxima",
      "en cN"
     ],
     [
      "Alargamiento a la rotura",
      "en % de la longitud de sujeción"
     ],
     [
      "Tenacidad",
      "cN/dtex = fuerza máxima / título"
     ]
    ]
   },
   {
    "k": "Montaje",
    "title": "Un equipo, varios ensayos",
    "text": "Un cambiador de bobinas pone las bobinas en posición una tras otra. Un brazo de agarre enhebra el hilo automáticamente. Una unidad de alimentación lo lleva a los módulos de ensayo: medición del título con balanza, sensor de regularidad, opcionalmente el sensor de entrelazado y el módulo de tracción con dos pinzas neumáticas. Todo se controla desde un PC.",
    "facts": [
     [
      "Cambiador",
      "20 posiciones, ampliable a 40"
     ],
     [
      "Enhebrado",
      "automático, brazo de agarre giratorio"
     ],
     [
      "Alimentación",
      "hasta 500 m/min, resolución 0,3 mm"
     ],
     [
      "Software",
      "Textechno TESTCONTROL"
     ],
     [
      "Módulos",
      "haz clic en la imagen para ver la explicación"
     ]
    ]
   },
   {
    "k": "Título",
    "title": "Medición del título: medir la longitud y pesar",
    "text": "La unidad de alimentación lleva una longitud de hilo preajustada por un transportador por vacío a una cámara colectora. La cámara está sobre una balanza electrónica. De la masa y la longitud resulta el título. La tensión del hilo se vigila y, si hace falta, se corrige por cálculo.",
    "facts": [
     [
      "Longitud de ensayo",
      "1–1000 m, preajustable"
     ],
     [
      "Balanza",
      "rango 300 g, resolución 1 mg"
     ],
     [
      "Fórmula",
      "dtex = masa en g / longitud en m × 10 000"
     ],
     [
      "Normas",
      "ISO 2060, ASTM D6587"
     ]
    ]
   },
   {
    "k": "Tracción",
    "title": "Ensayo de tracción según el principio CRE",
    "text": "Un tramo de hilo se sujeta entre dos pinzas neumáticas. La pinza inferior se aleja a velocidad constante: es el principio CRE (constant rate of extension). Se miden continuamente la fuerza y el recorrido hasta que el hilo se rompe. Con el regulador se comparan POY, FDY y DTY.",
    "facts": [
     [
      "Principio",
      "CRE: velocidad de alargamiento constante"
     ],
     [
      "Longitud de sujeción",
      "desde 80 mm, recorrido hasta 1000 mm"
     ],
     [
      "Medición de fuerza",
      "500 N, opcional 1500 N"
     ],
     [
      "Normas",
      "ISO 2062, ASTM D2256, ASTM D885"
     ]
    ]
   },
   {
    "k": "Tenacidad",
    "title": "Del ensayo individual al resultado de la bobina",
    "text": "Un solo ensayo de tracción tiene dispersión. Por eso se estiran varios tramos por bobina y se evalúan estadísticamente: media y coeficiente de variación de la fuerza máxima y del alargamiento a la rotura. Con el título de la misma bobina, el software calcula la tenacidad.",
    "facts": [
     [
      "Ensayos",
      "varios tramos por bobina"
     ],
     [
      "Estadística",
      "media, coeficiente de variación"
     ],
     [
      "Tenacidad",
      "fuerza máxima media / título"
     ],
     [
      "Ventaja",
      "título y valores de tracción de la misma bobina"
     ]
    ]
   }
  ]
 },
 "zh": {
  "ui": {
   "eyebrow": "入门 · 实验室",
   "h1": "用 STATIMAT DS 测纤度、强度和伸长",
   "lead": "STATIMAT DS 自动测试丝筒：通过称量一段定长丝确定纤度，并把丝段拉伸至断裂。由两者得出最大拉力、断裂伸长和强度。五个简短场景展示其工作原理。",
   "note": "示意图。设备数据来自 Textechno STATIMAT DS 数据表。纱线数值和力-伸长曲线为示例值，不是测量结果。",
   "pause": "⏸ 暂停",
   "play": "▶ 播放",
   "scenes": "场景",
   "yarn": "丝",
   "dec": ".",
   "clickHint": "点击设备中的测试模块，此处会显示说明。"
  },
  "cv": {
   "cards": [
    [
     "纤度",
     "167 dtex",
     "每 1000 米 1.67 克"
    ],
    [
     "最大拉力",
     "600 cN",
     "拉伸试验中的最大力"
    ],
    [
     "断裂伸长",
     "22 %",
     "断裂时的长度增加"
    ],
    [
     "强度",
     "3.6 cN/dtex",
     "600 cN / 167 dtex"
    ]
   ],
   "example": "示例：DTY 167 dtex",
   "fStrength": "强度",
   "fForce": "最大拉力",
   "fTiter": "纤度",
   "fNote": "使不同细度的丝可以比较",
   "peakNote": "最大拉力和断裂伸长",
   "forceAx": "力（cN）",
   "elongAx": "伸长",
   "device": "STATIMAT DS 示意",
   "changerSub": "20 至 40 个位置",
   "scale": "天平",
   "clampLen": "夹持长度",
   "clampsSub": "2 个气动夹持器",
   "pc": "PC · TESTCONTROL",
   "delivery": "送丝装置",
   "measLen": "测量长度",
   "vac": "真空输送",
   "chamber": "收集室",
   "scaleRes": "天平 · 分辨率 1 mg",
   "len": "长度",
   "mass": "质量",
   "formula": "纤度 = 质量 / 长度 × 10 000",
   "formula2": "= {m} g / {l} m × 10 000",
   "setLen": "设定测量长度：{l} m（示例）",
   "tension": "丝的张力受到监控，必要时通过计算修正",
   "running": "丝被定长并送入收集室 …",
   "result": "结果：{d} dtex",
   "fixed": "固定夹持器",
   "moving": "以恒定速度移动",
   "gauge": "夹持长度，例如 500 mm",
   "force": "力",
   "elong": "伸长",
   "peakF": "最大拉力 {f} cN",
   "peakE": "断裂伸长 {e} %",
   "crimp": "先拉直卷曲",
   "flow": "较长的屈服区：分子链取向",
   "broke": "{n}：在 {f} cN、伸长 {e} % 时断裂（示例值）",
   "pulling": "夹持器移动，力和位移被连续测量 …",
   "forceAx2": "最大拉力（cN）",
   "elongAx2": "断裂伸长",
   "ofN": "已测 {n} / 20 次",
   "rows": [
    "最大拉力",
    "断裂伸长",
    "纤度",
    "强度"
   ],
   "sameBobbin": "来自同一丝筒",
   "meanTiter": "平均值 / 纤度",
   "sim": "示例数据，模拟"
  },
  "stations": [
   {
    "n": "换筒装置",
    "s": "换筒装置",
    "d": "把下一个丝筒送到位：20 个位置，可扩展到 40 个。"
   },
   {
    "n": "抓取臂",
    "s": "抓取臂",
    "d": "旋转抓取臂：自动穿丝。"
   },
   {
    "n": "送丝装置",
    "s": "送丝装置",
    "d": "以测得的长度把丝送到各测试模块：最高 500 m/min，长度分辨率 0.3 mm。"
   },
   {
    "n": "纤度测量",
    "s": "纤度",
    "d": "一段定长丝进入天平上的收集室。由质量和长度得出纤度。"
   },
   {
    "n": "条干传感器",
    "s": "条干",
    "d": "电容式传感器：测量沿丝长度的质量波动。"
   },
   {
    "n": "网络传感器（可选）",
    "s": "网络",
    "d": "光学传感器：统计网络丝的网络点数。"
   },
   {
    "n": "拉伸测试",
    "s": "拉伸测试",
    "d": "两个气动夹持器：按 CRE 原理把丝拉伸至断裂。"
   }
  ],
  "scenes": [
   {
    "k": "指标",
    "title": "每个实验室都需要的四个指标",
    "text": "纤度表示丝有多细：即单位长度的质量。拉伸试验测量最大拉力和断裂时的伸长。最大拉力除以纤度得到强度。这样就能比较不同细度的丝。",
    "facts": [
     [
      "纤度",
      "dtex = 每 10 000 米的克数"
     ],
     [
      "最大拉力",
      "单位 cN"
     ],
     [
      "断裂伸长",
      "占夹持长度的 %"
     ],
     [
      "强度",
      "cN/dtex = 最大拉力 / 纤度"
     ]
    ]
   },
   {
    "k": "结构",
    "title": "一台设备，多项测试",
    "text": "换筒装置依次把丝筒送到位。抓取臂自动穿丝。送丝装置把丝送到各测试模块：带天平的纤度测量、条干传感器、可选的网络传感器，以及带两个气动夹持器的拉伸测试部分。一切由电脑控制。",
    "facts": [
     [
      "换筒装置",
      "20 个位置，可扩展到 40 个"
     ],
     [
      "穿丝",
      "自动，旋转抓取臂"
     ],
     [
      "送丝装置",
      "最高 500 m/min，长度分辨率 0.3 mm"
     ],
     [
      "软件",
      "Textechno TESTCONTROL"
     ],
     [
      "模块",
      "在图中点击即可查看说明"
     ]
    ]
   },
   {
    "k": "纤度",
    "title": "纤度测量：定长并称重",
    "text": "送丝装置把预设长度的丝经真空输送送入收集室。收集室放在电子天平上。由质量和长度得出纤度。丝的张力受到监控，必要时通过计算修正。",
    "facts": [
     [
      "测量长度",
      "1–1000 m，可预设"
     ],
     [
      "天平",
      "量程 300 g，分辨率 1 mg"
     ],
     [
      "公式",
      "dtex = 质量（g）/ 长度（m）× 10 000"
     ],
     [
      "标准",
      "ISO 2060、ASTM D6587"
     ]
    ]
   },
   {
    "k": "拉伸试验",
    "title": "按 CRE 原理进行拉伸试验",
    "text": "一段丝被夹在两个气动夹持器之间。下夹持器以恒定速度移开：这就是 CRE 原理（等速伸长）。连续测量力和位移，直到丝断裂。可用滑块比较 POY、FDY 和 DTY。",
    "facts": [
     [
      "原理",
      "CRE：等速伸长"
     ],
     [
      "夹持长度",
      "80 mm 起，行程最长 1000 mm"
     ],
     [
      "测力",
      "500 N，可选 1500 N"
     ],
     [
      "标准",
      "ISO 2062、ASTM D2256、ASTM D885"
     ]
    ]
   },
   {
    "k": "强度",
    "title": "从单次测试到丝筒结果",
    "text": "单次拉伸试验存在离散。因此每个丝筒要拉伸多段并进行统计评估：最大拉力和断裂伸长的平均值及变异系数。软件用同一丝筒的纤度计算强度。",
    "facts": [
     [
      "测试",
      "每个丝筒多段"
     ],
     [
      "统计",
      "平均值、变异系数"
     ],
     [
      "强度",
      "平均最大拉力 / 纤度"
     ],
     [
      "优点",
      "纤度和拉伸值来自同一丝筒"
     ]
    ]
   }
  ]
 }
};
