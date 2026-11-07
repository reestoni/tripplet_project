window.TEXTS = {
 "de": {
  "ui": {
   "eyebrow": "Onboarding · DTY · Spezialwissen",
   "h1": "Wege zum cotton-like DTY",
   "lead": "Sieben Varianten, wie ein DTY Volumen, Bögen oder Haarigkeit wie gesponnenes Garn bekommt. Die ersten fünf kombinieren zwei Komponenten mit Luft, die letzten beiden arbeiten mit einer einzigen Komponente.",
   "note": "Schematische Skizzen. Die Varianten lassen sich kombinieren, und Anlagen und Artikel unterscheiden sich in Führung, Düsentyp und Einstellungen. Bei den Varianten mit einer Komponente ist die Mechanik vereinfacht dargestellt.",
   "pause": "⏸ Pause",
   "play": "▶ Abspielen",
   "scenes": "Varianten",
   "clickHint": "Eine Position im Maschinenweg anklicken: Sie wird hier erklärt."
  },
  "cv": {
   "machine": "Maschinenweg",
   "heater": "Heizer",
   "cooling": "Kühlschiene",
   "friction": "Friktion",
   "overfeed": "mit Voreilung",
   "heater2": "Heizer 2",
   "heater2opt": "opt. Heizer 2",
   "winding": "Aufwicklung",
   "lw1": "LW 1",
   "lw2": "LW 2",
   "lw2x": "LW 2.x",
   "lw3": "LW 3",
   "lwfdy": "LW FDY",
   "int": "Verwirbelung",
   "pre": "Vorverwirbelung",
   "tex": "Texturierdüse",
   "lowDraw": "Verstreckverhältnis bewusst zu tief",
   "breakZone": "Brechzone",
   "proc": "Was passiert",
   "struct": "Garnstruktur",
   "xsec": "Querschnitt",
   "xsecs": "Querschnitte",
   "poyTex": "POY texturiert",
   "fdy": "FDY",
   "poy": "POY",
   "poy1": "POY 1",
   "poy2": "POY 2"
  },
  "stations": [
   {
    "n": "POY",
    "d": "Vororientiertes Garn aus der Spinnerei. Es wird im DTY-Prozess verstreckt und texturiert und bildet meist den Kern."
   },
   {
    "n": "FDY",
    "d": "Fertig verstrecktes Garn als Effektkomponente. Es umgeht Heizer und Friktion und wird erst an der Düse zugeführt."
   },
   {
    "n": "POY 2",
    "d": "Zweites POY mit anderer Schrumpfung, Feinheit oder Färbbarkeit. Es läuft zusammen mit POY 1 durch den ganzen Prozess."
   },
   {
    "n": "Lieferwerk 1",
    "d": "Zieht das POY von der Spule. Zwischen LW 1 und LW 2 wird verstreckt: LW 2 läuft um das Verstreckverhältnis schneller."
   },
   {
    "n": "Primärheizer",
    "d": "Erwärmt das Garn, damit es sich verstrecken lässt und der Drall aus der Friktion als Kräuselung fixiert wird."
   },
   {
    "n": "Kühlschiene",
    "d": "Das Garn kühlt vor der Friktion ab, damit die Kräuselung erhalten bleibt."
   },
   {
    "n": "Friktion",
    "d": "Die Friktionsscheiben drehen das Garn (Falschdraht). Im heissen Bereich davor wird der Drall als Kräuselung fixiert."
   },
   {
    "n": "Lieferwerk 2",
    "d": "Bestimmt zusammen mit LW 1 das Verstreckverhältnis. Direkt danach sitzt die Düse."
   },
   {
    "n": "Lieferwerk FDY",
    "d": "Eigenes Lieferwerk für das FDY. Es liefert mehr Garn, als der Kern verbraucht (Voreilung). Diese Überlänge bildet die Bögen oder Schlingen."
   },
   {
    "n": "Verwirbelungsdüse",
    "d": "Luft verwirbelt die Filamente und setzt Knoten. Die Knoten verbinden die Komponenten und halten die Struktur zusammen."
   },
   {
    "n": "Texturierdüse",
    "d": "Wie beim ATY: Ein Luftstrahl formt die überlieferte Komponente zu geschlossenen Schlingen, die sich mit dem Kern verhaken."
   },
   {
    "n": "Vorverwirbelung",
    "d": "Kleine Düse am Einlauf. Sie führt die zwei POY zusammen, damit sie gemeinsam verstreckt und texturiert werden."
   },
   {
    "n": "Lieferwerk 2.x (OF)",
    "d": "Läuft 3–7 % langsamer als LW 2. Dieser Overfeed gibt der Düse das Material, das sie für ihre Arbeit braucht."
   },
   {
    "n": "Heizer 2",
    "d": "Optionaler zweiter Heizer. Er stabilisiert das Garn und reduziert die Restkräuselung (Set-Garn)."
   },
   {
    "n": "Lieferwerk 3",
    "d": "Letztes Lieferwerk vor der Aufwicklung. Mit der Aufwicklung bestimmt es die Wickelspannung."
   },
   {
    "n": "Aufwicklung",
    "d": "Das fertige Garn wird auf die Spule gewickelt."
   },
   {
    "n": "Brechzone",
    "d": "Hier werden einzelne, meist sehr feine Filamente gezielt gebrochen, zum Beispiel durch Überverstrecken oder an einem Reibelement."
   }
  ],
  "scenes": [
   {
    "k": "Eine Verwirbelungsdüse",
    "s": "Eine Düse",
    "title": "Eine Verwirbelungsdüse nach der Texturierung",
    "text": "Das POY läuft den normalen DTY-Weg und wird verstreckt und texturiert. Das fertig verstreckte FDY umgeht Heizer und Friktion und läuft über ein eigenes Lieferwerk mit Voreilung zu. Beide treffen sich in der Verwirbelungsdüse, die sie über Knoten verbindet. Die Überlänge des FDY bleibt als flache Bögen an der Oberfläche.",
    "facts": [
     [
      "Kern",
      "texturiertes POY"
     ],
     [
      "Effekt",
      "FDY mit Voreilung, flache Bögen"
     ],
     [
      "Vorteil",
      "einfacher Aufbau, eine Düse"
     ],
     [
      "Grenze",
      "Volumen begrenzt, Bögen eher flach"
     ]
    ],
    "p": [
     "Knoten verbinden, Bögen bleiben"
    ],
    "st": [
     "flache Bögen",
     "Kern grob, Mantel fein"
    ]
   },
   {
    "k": "Texturierdüse",
    "title": "Lufttexturierdüse statt Verwirbelungsdüse",
    "text": "Anstelle der Verwirbelungsdüse sitzt eine Lufttexturierdüse wie beim ATY. Die stark überlieferte Effektkomponente wird darin zu echten, geschlossenen Schlingen geformt, die sich mit dem texturierten Kern verhaken. Je nach Düse wird das Garn vorher benetzt.",
    "facts": [
     [
      "Kern",
      "texturiertes POY"
     ],
     [
      "Effekt",
      "FDY bildet echte Schlingen"
     ],
     [
      "Vorteil",
      "viel Volumen, Griff nah an Spinngarn"
     ],
     [
      "Nachteil",
      "höherer Luftverbrauch, Schlingen ohne Knoten weniger fixiert"
     ]
    ],
    "p": [
     "Schlingen um den Kern"
    ],
    "st": [
     "geschlossene Schlingen",
     "Schlingen bis weit aussen"
    ]
   },
   {
    "k": "Zwei Düsen",
    "title": "Texturierdüse und Verwirbelungsdüse hintereinander",
    "text": "Die erste Düse formt die Schlingen, die zweite setzt Knoten und hält die Struktur zusammen. So lassen sich Volumen und Fadenschluss getrennt einstellen: Voreilung und Druck an der Texturierdüse bestimmen die Schlingen, der Druck an der Verwirbelungsdüse die Knoten.",
    "facts": [
     [
      "Düse 1",
      "Texturierdüse: Schlingen"
     ],
     [
      "Düse 2",
      "Verwirbelungsdüse: Knoten"
     ],
     [
      "Vorteil",
      "Volumen und Fadenschluss getrennt einstellbar"
     ],
     [
      "Nachteil",
      "mehr Luft, mehr Platz, mehr Einstellgrössen"
     ]
    ],
    "p": [
     "Schlingen",
     "Schlingen + Knoten"
    ],
    "st": [
     "Schlingen + Knoten",
     "Schlingen, durch Knoten fixiert"
    ]
   },
   {
    "k": "Vor dem Heizer",
    "title": "Zwei POY vor dem Heizer zusammenführen",
    "text": "Zwei POY-Typen werden am Einlauf zusammengeführt, meist mit einer Vorverwirbelungsdüse, und gemeinsam verstreckt und texturiert. Sie unterscheiden sich zum Beispiel in Schrumpfung, Filamentfeinheit oder Färbbarkeit. Der Effekt entsteht erst beim Fixieren oder Färben: Die stärker schrumpfende Komponente zieht sich in den Kern, die andere bauscht aussen auf.",
    "facts": [
     [
      "Komponenten",
      "zwei POY mit unterschiedlicher Schrumpfung"
     ],
     [
      "Effekt",
      "entsteht erst beim Fixieren oder Färben"
     ],
     [
      "Vorteil",
      "normaler DTY-Weg, Melange bei unterschiedlicher Färbbarkeit"
     ],
     [
      "Nachteil",
      "Ergebnis stark von der Rohstoffpaarung abhängig"
     ]
    ],
    "p": [
     "nach dem Texturieren: gemischt",
     "Fixieren / Färben: Schrumpfen",
     "POY 2 schrumpft in den Kern, POY 1 bauscht auf"
    ],
    "st": [
     "POY 1 bauscht aussen",
     "Melange bei unterschiedlicher Färbung",
     "POY 2 im Kern"
    ]
   },
   {
    "k": "Düse nach Heizer 2",
    "title": "Zusätzliche Verwirbelungsdüse nach Heizer 2",
    "text": "Nach der ersten Verwirbelung läuft das Garn durch den zweiten Heizer und wird dabei stabilisiert. Eine weitere Verwirbelungsdüse setzt danach zusätzliche Knoten. Die Struktur hält so beim Aufwickeln und in der Weiterverarbeitung besser zusammen.",
    "facts": [
     [
      "Ablauf",
      "verwirbeln, stabilisieren, nochmals verwirbeln"
     ],
     [
      "Vorteil",
      "stabile Struktur, weniger Trennen der Komponenten"
     ],
     [
      "Nachteil",
      "mehr und festere Knoten"
     ],
     [
      "Bezug",
      "nach der Knoten-These (Thema Harte Knoten) könnte das die Bruchdehnung senken"
     ]
    ],
    "p": [
     "zusätzliche Knoten nach Heizer 2"
    ],
    "st": [
     "mehr und festere Knoten",
     "kompakter, mehr Knoten"
    ]
   },
   {
    "k": "Dick-Dünn",
    "title": "Dick-Dünn-Effekt durch Unterverstreckung",
    "text": "Ein einzelnes POY wird mit einem Verstreckverhältnis unter dem natürlichen Verstreckverhältnis verarbeitet. Einzelne Abschnitte bleiben dadurch unverstreckt. Sie sind dicker, nehmen mehr Farbstoff auf und färben dunkler. Es entsteht ein unregelmässiges Garnbild ähnlich einem Flammgarn aus Baumwolle.",
    "facts": [
     [
      "Komponente",
      "ein POY"
     ],
     [
      "Effekt",
      "unverstreckte, dickere Abschnitte"
     ],
     [
      "Vorteil",
      "Optik wie Baumwolle, dunklere Stellen nach dem Färben"
     ],
     [
      "Nachteil",
      "tiefere Festigkeit, enges Prozessfenster"
     ]
    ],
    "p": [
     "unverstreckte Abschnitte: dicker, färben dunkler",
     "verstreckt"
    ],
    "st": [
     "dunklere, dickere Stellen",
     "dünn",
     "dick"
    ]
   },
   {
    "k": "Filamentbruch",
    "title": "Haarigkeit durch gezielten Filamentbruch",
    "text": "Einzelne, meist sehr feine Filamente werden gezielt gebrochen, zum Beispiel durch Überverstrecken einzelner Filamente oder an einem Reibelement. Die freien Enden stehen aus dem Garn ab wie die Faserenden bei einem gesponnenen Garn. Die Verwirbelung danach bindet die gebrochenen Filamente wieder ein.",
    "facts": [
     [
      "Komponente",
      "ein POY, oft mit sehr feinen Filamenten"
     ],
     [
      "Effekt",
      "abstehende Filamentenden, Haarigkeit"
     ],
     [
      "Vorteil",
      "Griff und Haarigkeit wie Spinngarn"
     ],
     [
      "Nachteil",
      "Festigkeitsverlust, Flusen, Bruchrate schwer zu steuern"
     ]
    ],
    "p": [
     "gebrochene Filamente stehen als Enden ab"
    ],
    "st": [
     "Haarigkeit wie Spinngarn",
     "abstehende Enden"
    ]
   }
  ]
 },
 "en": {
  "ui": {
   "eyebrow": "Onboarding · DTY · Specialist knowledge",
   "h1": "Routes to a cotton-like DTY",
   "lead": "Seven ways a DTY gets the bulk, loops or hairiness of a spun yarn. The first five combine two components with air, the last two work with a single component.",
   "note": "Schematic sketches. The variants can be combined, and machines and articles differ in threadline, jet type and settings. For the single-component variants the mechanics are simplified.",
   "pause": "⏸ Pause",
   "play": "▶ Play",
   "scenes": "Variants",
   "clickHint": "Click a position on the threadline: it is explained here."
  },
  "cv": {
   "machine": "Threadline",
   "heater": "Heater",
   "cooling": "Cooling plate",
   "friction": "Friction",
   "overfeed": "with overfeed",
   "heater2": "Heater 2",
   "heater2opt": "opt. heater 2",
   "winding": "Take-up",
   "lw1": "FR 1",
   "lw2": "FR 2",
   "lw2x": "FR 2.x",
   "lw3": "FR 3",
   "lwfdy": "FR FDY",
   "int": "Intermingling",
   "pre": "Pre-intermingling",
   "tex": "Texturing jet",
   "lowDraw": "draw ratio deliberately too low",
   "breakZone": "Breaking zone",
   "proc": "What happens",
   "struct": "Yarn structure",
   "xsec": "Cross-section",
   "xsecs": "Cross-sections",
   "poyTex": "POY textured",
   "fdy": "FDY",
   "poy": "POY",
   "poy1": "POY 1",
   "poy2": "POY 2"
  },
  "stations": [
   {
    "n": "POY",
    "d": "Partially oriented yarn from the spinning plant. It is drawn and textured in the DTY process and usually forms the core."
   },
   {
    "n": "FDY",
    "d": "Fully drawn yarn as the effect component. It bypasses heater and friction and is only fed in at the jet."
   },
   {
    "n": "POY 2",
    "d": "Second POY with different shrinkage, filament fineness or dyeability. It runs together with POY 1 through the whole process."
   },
   {
    "n": "Feed roll 1",
    "d": "Pulls the POY off the package. The yarn is drawn between FR 1 and FR 2: FR 2 runs faster by the draw ratio."
   },
   {
    "n": "Primary heater",
    "d": "Heats the yarn so that it can be drawn and the twist from the friction unit is set as crimp."
   },
   {
    "n": "Cooling plate",
    "d": "The yarn cools down before the friction unit so that the crimp is kept."
   },
   {
    "n": "Friction unit",
    "d": "The friction discs twist the yarn (false twist). In the hot zone before it the twist is set as crimp."
   },
   {
    "n": "Feed roll 2",
    "d": "Sets the draw ratio together with FR 1. The jet sits right after it."
   },
   {
    "n": "Feed roll FDY",
    "d": "Separate feed roll for the FDY. It delivers more yarn than the core uses (overfeed). This extra length forms the arcs or loops."
   },
   {
    "n": "Intermingling jet",
    "d": "Air entangles the filaments and sets nips. The nips join the components and hold the structure together."
   },
   {
    "n": "Texturing jet",
    "d": "As in ATY: an air jet forms the overfed component into closed loops that hook into the core."
   },
   {
    "n": "Pre-intermingling",
    "d": "Small jet at the inlet. It combines the two POY so that they are drawn and textured together."
   },
   {
    "n": "Feed roll 2.x (OF)",
    "d": "Runs 3–7 % slower than FR 2. This overfeed gives the jet the material it needs to work."
   },
   {
    "n": "Heater 2",
    "d": "Optional second heater. It stabilises the yarn and reduces the residual crimp (set yarn)."
   },
   {
    "n": "Feed roll 3",
    "d": "Last feed roll before the take-up. Together with the take-up it sets the winding tension."
   },
   {
    "n": "Take-up",
    "d": "The finished yarn is wound onto the package."
   },
   {
    "n": "Breaking zone",
    "d": "Single, usually very fine filaments are broken on purpose here, for example by overdrawing or on a friction element."
   }
  ],
  "scenes": [
   {
    "k": "One intermingling jet",
    "s": "One jet",
    "title": "One intermingling jet after texturing",
    "text": "The POY runs the normal DTY path and is drawn and textured. The fully drawn FDY bypasses heater and friction and is fed in via its own feed roll with overfeed. Both meet in the intermingling jet, which joins them with nips. The extra length of the FDY stays on the surface as flat arcs.",
    "facts": [
     [
      "Core",
      "textured POY"
     ],
     [
      "Effect",
      "FDY with overfeed, flat arcs"
     ],
     [
      "Advantage",
      "simple set-up, one jet"
     ],
     [
      "Limit",
      "limited bulk, rather flat arcs"
     ]
    ],
    "p": [
     "nips join, arcs remain"
    ],
    "st": [
     "flat arcs",
     "coarse core, fine sheath"
    ]
   },
   {
    "k": "Texturing jet",
    "title": "Air texturing jet instead of intermingling jet",
    "text": "Instead of the intermingling jet there is an air texturing jet as in ATY. It forms the strongly overfed effect component into real, closed loops that hook into the textured core. Depending on the jet, the yarn is wetted first.",
    "facts": [
     [
      "Core",
      "textured POY"
     ],
     [
      "Effect",
      "FDY forms real loops"
     ],
     [
      "Advantage",
      "high bulk, hand close to a spun yarn"
     ],
     [
      "Drawback",
      "higher air consumption, loops less fixed without nips"
     ]
    ],
    "p": [
     "loops around the core"
    ],
    "st": [
     "closed loops",
     "loops reach far out"
    ]
   },
   {
    "k": "Two jets",
    "title": "Texturing jet and intermingling jet in series",
    "text": "The first jet forms the loops, the second sets nips and holds the structure together. Bulk and yarn cohesion can thus be set separately: overfeed and pressure at the texturing jet determine the loops, the pressure at the intermingling jet the nips.",
    "facts": [
     [
      "Jet 1",
      "texturing jet: loops"
     ],
     [
      "Jet 2",
      "intermingling jet: nips"
     ],
     [
      "Advantage",
      "bulk and cohesion set separately"
     ],
     [
      "Drawback",
      "more air, more space, more settings"
     ]
    ],
    "p": [
     "loops",
     "loops + nips"
    ],
    "st": [
     "loops + nips",
     "loops fixed by nips"
    ]
   },
   {
    "k": "Before the heater",
    "title": "Combining two POY before the heater",
    "text": "Two POY types are combined at the inlet, usually with a pre-intermingling jet, and drawn and textured together. They differ for example in shrinkage, filament fineness or dyeability. The effect only appears during setting or dyeing: the component that shrinks more pulls into the core, the other one bulks up on the outside.",
    "facts": [
     [
      "Components",
      "two POY with different shrinkage"
     ],
     [
      "Effect",
      "appears only during setting or dyeing"
     ],
     [
      "Advantage",
      "normal DTY path, mélange with different dyeability"
     ],
     [
      "Drawback",
      "result depends strongly on the raw-material pairing"
     ]
    ],
    "p": [
     "after texturing: mixed",
     "setting / dyeing: shrinkage",
     "POY 2 shrinks into the core, POY 1 bulks up"
    ],
    "st": [
     "POY 1 bulks on the outside",
     "mélange with different dyeing",
     "POY 2 in the core"
    ]
   },
   {
    "k": "Jet after heater 2",
    "title": "Additional intermingling jet after heater 2",
    "text": "After the first intermingling the yarn runs through the second heater and is stabilised. A further intermingling jet then sets additional nips. The structure thus holds together better during winding and further processing.",
    "facts": [
     [
      "Sequence",
      "intermingle, stabilise, intermingle again"
     ],
     [
      "Advantage",
      "stable structure, components separate less"
     ],
     [
      "Drawback",
      "more and harder nips"
     ],
     [
      "Link",
      "according to the nip hypothesis (topic Hard nips) this could lower the elongation at break"
     ]
    ],
    "p": [
     "additional nips after heater 2"
    ],
    "st": [
     "more and harder nips",
     "more compact, more nips"
    ]
   },
   {
    "k": "Thick-thin",
    "title": "Thick-thin effect by underdrawing",
    "text": "A single POY is processed with a draw ratio below its natural draw ratio. Some sections therefore remain undrawn. They are thicker, take up more dye and dye darker. The result is an irregular yarn appearance similar to a cotton slub yarn.",
    "facts": [
     [
      "Component",
      "one POY"
     ],
     [
      "Effect",
      "undrawn, thicker sections"
     ],
     [
      "Advantage",
      "cotton-like look, darker spots after dyeing"
     ],
     [
      "Drawback",
      "lower tenacity, narrow process window"
     ]
    ],
    "p": [
     "undrawn sections: thicker, dye darker",
     "drawn"
    ],
    "st": [
     "darker, thicker spots",
     "thin",
     "thick"
    ]
   },
   {
    "k": "Filament breaking",
    "title": "Hairiness by controlled filament breaking",
    "text": "Single, usually very fine filaments are broken on purpose, for example by overdrawing single filaments or on a friction element. The free ends stick out of the yarn like the fibre ends of a spun yarn. The intermingling afterwards binds the broken filaments back in.",
    "facts": [
     [
      "Component",
      "one POY, often with very fine filaments"
     ],
     [
      "Effect",
      "protruding filament ends, hairiness"
     ],
     [
      "Advantage",
      "hand and hairiness like a spun yarn"
     ],
     [
      "Drawback",
      "loss of tenacity, fluff, breaking rate hard to control"
     ]
    ],
    "p": [
     "broken filaments stick out as ends"
    ],
    "st": [
     "hairiness like a spun yarn",
     "protruding ends"
    ]
   }
  ]
 },
 "es": {
  "ui": {
   "eyebrow": "Onboarding · DTY · Conocimiento especializado",
   "h1": "Caminos hacia un DTY tipo algodón",
   "lead": "Siete maneras de dar a un DTY el volumen, los arcos o la vellosidad de un hilo hilado. Las cinco primeras combinan dos componentes con aire, las dos últimas trabajan con un solo componente.",
   "note": "Esquemas simplificados. Las variantes se pueden combinar, y las máquinas y artículos difieren en el recorrido del hilo, el tipo de tobera y los ajustes. En las variantes de un componente la mecánica está simplificada.",
   "pause": "⏸ Pausa",
   "play": "▶ Reproducir",
   "scenes": "Variantes",
   "clickHint": "Haz clic en una posición del recorrido: se explica aquí."
  },
  "cv": {
   "machine": "Recorrido del hilo",
   "heater": "Calentador",
   "cooling": "Placa de enfriamiento",
   "friction": "Fricción",
   "overfeed": "con sobrealimentación",
   "heater2": "Calentador 2",
   "heater2opt": "calentador 2 opc.",
   "winding": "Bobinado",
   "lw1": "R 1",
   "lw2": "R 2",
   "lw2x": "R 2.x",
   "lw3": "R 3",
   "lwfdy": "R FDY",
   "int": "Entrelazado",
   "pre": "Preentrelazado",
   "tex": "Tobera de texturizado",
   "lowDraw": "relación de estirado demasiado baja a propósito",
   "breakZone": "Zona de rotura",
   "proc": "Qué ocurre",
   "struct": "Estructura del hilo",
   "xsec": "Sección",
   "xsecs": "Secciones",
   "poyTex": "POY texturizado",
   "fdy": "FDY",
   "poy": "POY",
   "poy1": "POY 1",
   "poy2": "POY 2"
  },
  "stations": [
   {
    "n": "POY",
    "d": "Hilo parcialmente orientado de la hilatura. En el proceso DTY se estira y texturiza y suele formar el núcleo."
   },
   {
    "n": "FDY",
    "d": "Hilo totalmente estirado como componente de efecto. Evita el calentador y la fricción y se alimenta solo en la tobera."
   },
   {
    "n": "POY 2",
    "d": "Segundo POY con otra contracción, finura de filamento o afinidad tintórea. Recorre todo el proceso junto con el POY 1."
   },
   {
    "n": "Rodillo de entrega 1",
    "d": "Saca el POY de la bobina. Entre R 1 y R 2 se estira: R 2 gira más rápido según la relación de estirado."
   },
   {
    "n": "Calentador primario",
    "d": "Calienta el hilo para que se pueda estirar y la torsión de la fricción se fije como rizado."
   },
   {
    "n": "Placa de enfriamiento",
    "d": "El hilo se enfría antes de la fricción para que se conserve el rizado."
   },
   {
    "n": "Unidad de fricción",
    "d": "Los discos de fricción tuercen el hilo (falsa torsión). En la zona caliente anterior la torsión se fija como rizado."
   },
   {
    "n": "Rodillo de entrega 2",
    "d": "Junto con R 1 define la relación de estirado. La tobera está justo después."
   },
   {
    "n": "Rodillo FDY",
    "d": "Rodillo propio para el FDY. Entrega más hilo del que consume el núcleo (sobrealimentación). Esta longitud extra forma los arcos o bucles."
   },
   {
    "n": "Tobera de entrelazado",
    "d": "El aire entrelaza los filamentos y forma nudos. Los nudos unen los componentes y mantienen la estructura."
   },
   {
    "n": "Tobera de texturizado",
    "d": "Como en el ATY: un chorro de aire convierte el componente sobrealimentado en bucles cerrados que se enganchan en el núcleo."
   },
   {
    "n": "Preentrelazado",
    "d": "Pequeña tobera a la entrada. Une los dos POY para que se estiren y texturicen juntos."
   },
   {
    "n": "Rodillo de entrega 2.x (OF)",
    "d": "Gira un 3–7 % más lento que R 2. Esta sobrealimentación da a la tobera el material que necesita."
   },
   {
    "n": "Calentador 2",
    "d": "Segundo calentador opcional. Estabiliza el hilo y reduce el rizado residual (hilo fijado)."
   },
   {
    "n": "Rodillo de entrega 3",
    "d": "Último rodillo antes del bobinado. Junto con el bobinado define la tensión de bobinado."
   },
   {
    "n": "Bobinado",
    "d": "El hilo terminado se enrolla en la bobina."
   },
   {
    "n": "Zona de rotura",
    "d": "Aquí se rompen a propósito filamentos sueltos, normalmente muy finos, por ejemplo por sobreestirado o en un elemento de fricción."
   }
  ],
  "scenes": [
   {
    "k": "Una tobera de entrelazado",
    "s": "Una tobera",
    "title": "Una tobera de entrelazado después del texturizado",
    "text": "El POY sigue el recorrido DTY normal y se estira y texturiza. El FDY totalmente estirado evita el calentador y la fricción y llega por su propio rodillo con sobrealimentación. Ambos se encuentran en la tobera de entrelazado, que los une con nudos. La longitud extra del FDY queda en la superficie como arcos planos.",
    "facts": [
     [
      "Núcleo",
      "POY texturizado"
     ],
     [
      "Efecto",
      "FDY con sobrealimentación, arcos planos"
     ],
     [
      "Ventaja",
      "montaje sencillo, una tobera"
     ],
     [
      "Límite",
      "volumen limitado, arcos más bien planos"
     ]
    ],
    "p": [
     "los nudos unen, los arcos quedan"
    ],
    "st": [
     "arcos planos",
     "núcleo grueso, envoltura fina"
    ]
   },
   {
    "k": "Tobera de texturizado",
    "title": "Tobera de texturizado por aire en vez de entrelazado",
    "text": "En lugar de la tobera de entrelazado hay una tobera de texturizado por aire como en el ATY. En ella el componente de efecto, muy sobrealimentado, forma bucles reales y cerrados que se enganchan en el núcleo texturizado. Según la tobera, el hilo se humedece antes.",
    "facts": [
     [
      "Núcleo",
      "POY texturizado"
     ],
     [
      "Efecto",
      "el FDY forma bucles reales"
     ],
     [
      "Ventaja",
      "mucho volumen, tacto cercano al hilo hilado"
     ],
     [
      "Inconveniente",
      "más consumo de aire, bucles menos fijados sin nudos"
     ]
    ],
    "p": [
     "bucles alrededor del núcleo"
    ],
    "st": [
     "bucles cerrados",
     "bucles hasta muy afuera"
    ]
   },
   {
    "k": "Dos toberas",
    "title": "Tobera de texturizado y de entrelazado en serie",
    "text": "La primera tobera forma los bucles, la segunda hace nudos y mantiene la estructura. Así el volumen y la cohesión se ajustan por separado: la sobrealimentación y la presión en la tobera de texturizado determinan los bucles, la presión en la tobera de entrelazado los nudos.",
    "facts": [
     [
      "Tobera 1",
      "texturizado: bucles"
     ],
     [
      "Tobera 2",
      "entrelazado: nudos"
     ],
     [
      "Ventaja",
      "volumen y cohesión ajustables por separado"
     ],
     [
      "Inconveniente",
      "más aire, más espacio, más ajustes"
     ]
    ],
    "p": [
     "bucles",
     "bucles + nudos"
    ],
    "st": [
     "bucles + nudos",
     "bucles fijados por nudos"
    ]
   },
   {
    "k": "Antes del calentador",
    "title": "Unir dos POY antes del calentador",
    "text": "Dos tipos de POY se unen a la entrada, normalmente con una tobera de preentrelazado, y se estiran y texturizan juntos. Se diferencian por ejemplo en contracción, finura de filamento o afinidad tintórea. El efecto aparece solo al fijar o teñir: el componente que más encoge se va al núcleo, el otro se abomba por fuera.",
    "facts": [
     [
      "Componentes",
      "dos POY con distinta contracción"
     ],
     [
      "Efecto",
      "aparece solo al fijar o teñir"
     ],
     [
      "Ventaja",
      "recorrido DTY normal, melange con distinta afinidad tintórea"
     ],
     [
      "Inconveniente",
      "resultado muy dependiente de la combinación de materias primas"
     ]
    ],
    "p": [
     "tras el texturizado: mezclado",
     "fijado / teñido: contracción",
     "el POY 2 encoge al núcleo, el POY 1 se abomba"
    ],
    "st": [
     "POY 1 abombado por fuera",
     "melange con distinto teñido",
     "POY 2 en el núcleo"
    ]
   },
   {
    "k": "Tobera tras calentador 2",
    "s": "Tras calentador 2",
    "title": "Tobera de entrelazado adicional tras el calentador 2",
    "text": "Tras el primer entrelazado el hilo pasa por el segundo calentador y se estabiliza. Otra tobera de entrelazado forma después nudos adicionales. Así la estructura se mantiene mejor en el bobinado y en los procesos posteriores.",
    "facts": [
     [
      "Secuencia",
      "entrelazar, estabilizar, volver a entrelazar"
     ],
     [
      "Ventaja",
      "estructura estable, los componentes se separan menos"
     ],
     [
      "Inconveniente",
      "más nudos y más duros"
     ],
     [
      "Relación",
      "según la hipótesis de los nudos (tema Nudos duros) podría reducir el alargamiento a la rotura"
     ]
    ],
    "p": [
     "nudos adicionales tras el calentador 2"
    ],
    "st": [
     "más nudos y más duros",
     "más compacto, más nudos"
    ]
   },
   {
    "k": "Grueso-fino",
    "title": "Efecto grueso-fino por subestirado",
    "text": "Un solo POY se procesa con una relación de estirado inferior a la natural. Por ello algunas secciones quedan sin estirar. Son más gruesas, absorben más colorante y se tiñen más oscuras. Resulta un aspecto irregular, parecido a un hilo flameado de algodón.",
    "facts": [
     [
      "Componente",
      "un POY"
     ],
     [
      "Efecto",
      "secciones sin estirar, más gruesas"
     ],
     [
      "Ventaja",
      "aspecto de algodón, zonas más oscuras tras teñir"
     ],
     [
      "Inconveniente",
      "menor tenacidad, ventana de proceso estrecha"
     ]
    ],
    "p": [
     "secciones sin estirar: más gruesas, más oscuras",
     "estirado"
    ],
    "st": [
     "zonas más oscuras y gruesas",
     "fino",
     "grueso"
    ]
   },
   {
    "k": "Rotura de filamentos",
    "s": "Rotura",
    "title": "Vellosidad por rotura controlada de filamentos",
    "text": "Se rompen a propósito filamentos sueltos, normalmente muy finos, por ejemplo sobreestirando filamentos individuales o en un elemento de fricción. Los extremos libres sobresalen del hilo como los extremos de fibra de un hilo hilado. El entrelazado posterior vuelve a integrar los filamentos rotos.",
    "facts": [
     [
      "Componente",
      "un POY, a menudo con filamentos muy finos"
     ],
     [
      "Efecto",
      "extremos de filamento salientes, vellosidad"
     ],
     [
      "Ventaja",
      "tacto y vellosidad de hilo hilado"
     ],
     [
      "Inconveniente",
      "pérdida de tenacidad, pelusa, tasa de rotura difícil de controlar"
     ]
    ],
    "p": [
     "los filamentos rotos sobresalen como extremos"
    ],
    "st": [
     "vellosidad como hilo hilado",
     "extremos salientes"
    ]
   }
  ]
 },
 "zh": {
  "ui": {
   "eyebrow": "入门 · DTY · 专业知识",
   "h1": "实现仿棉 DTY 的途径",
   "lead": "七种让 DTY 获得短纤纱般蓬松、丝弧或毛羽的方法。前五种用空气组合两种组分，后两种只用一种组分。",
   "note": "示意图。各种方法可以组合使用，设备和品种在走丝路线、喷嘴类型和设定上各不相同。单组分方法的机理作了简化。",
   "pause": "⏸ 暂停",
   "play": "▶ 播放",
   "scenes": "方法",
   "clickHint": "点击走丝路线上的位置，此处会显示说明。"
  },
  "cv": {
   "machine": "走丝路线",
   "heater": "热箱",
   "cooling": "冷却板",
   "friction": "假捻器",
   "overfeed": "超喂",
   "heater2": "第二热箱",
   "heater2opt": "可选第二热箱",
   "winding": "卷绕",
   "lw1": "罗拉 1",
   "lw2": "罗拉 2",
   "lw2x": "罗拉 2.x",
   "lw3": "罗拉 3",
   "lwfdy": "FDY 罗拉",
   "int": "网络",
   "pre": "预网络",
   "tex": "变形喷嘴",
   "lowDraw": "有意采用过低的拉伸比",
   "breakZone": "断丝区",
   "proc": "过程",
   "struct": "纱线结构",
   "xsec": "截面",
   "xsecs": "截面",
   "poyTex": "变形后的 POY",
   "fdy": "FDY",
   "poy": "POY",
   "poy1": "POY 1",
   "poy2": "POY 2"
  },
  "stations": [
   {
    "n": "POY",
    "d": "来自纺丝厂的预取向丝。在 DTY 工艺中被拉伸和变形，通常构成芯部。"
   },
   {
    "n": "FDY",
    "d": "全拉伸丝，作为效果组分。它绕过热箱和假捻器，只在喷嘴处喂入。"
   },
   {
    "n": "POY 2",
    "d": "第二种 POY，收缩、单丝细度或染色性不同。它与 POY 1 一起走完整个工艺。"
   },
   {
    "n": "第一罗拉",
    "d": "从丝筒上引出 POY。在罗拉 1 和罗拉 2 之间进行拉伸：罗拉 2 按拉伸比转得更快。"
   },
   {
    "n": "第一热箱",
    "d": "加热丝条，使其能够被拉伸，并使假捻器产生的捻度定型为卷曲。"
   },
   {
    "n": "冷却板",
    "d": "丝条在进入假捻器前冷却，使卷曲得以保持。"
   },
   {
    "n": "摩擦假捻器",
    "d": "摩擦盘使丝条加捻（假捻）。在其前面的热区中，捻度被定型为卷曲。"
   },
   {
    "n": "第二罗拉",
    "d": "与罗拉 1 一起决定拉伸比。喷嘴紧接在它后面。"
   },
   {
    "n": "FDY 罗拉",
    "d": "FDY 专用罗拉。它送出的丝比芯部消耗的多（超喂）。这段多余长度形成丝弧或丝圈。"
   },
   {
    "n": "网络喷嘴",
    "d": "空气使单丝交缠并形成网络点。网络点把各组分连接在一起并保持结构。"
   },
   {
    "n": "变形喷嘴",
    "d": "与 ATY 相同：空气射流把超喂的组分变成闭合的丝圈，并与芯部钩连。"
   },
   {
    "n": "预网络",
    "d": "入口处的小喷嘴。它把两种 POY 合并在一起，使其共同拉伸和变形。"
   },
   {
    "n": "罗拉 2.x（超喂）",
    "d": "比罗拉 2 慢 3–7 %。这个超喂为喷嘴提供工作所需的丝量。"
   },
   {
    "n": "第二热箱",
    "d": "可选的第二热箱。它使丝条稳定并降低残余卷曲（定型丝）。"
   },
   {
    "n": "第三罗拉",
    "d": "卷绕前的最后一个罗拉。它与卷绕一起决定卷绕张力。"
   },
   {
    "n": "卷绕",
    "d": "成品丝被卷绕到丝筒上。"
   },
   {
    "n": "断丝区",
    "d": "在这里有意使个别单丝（通常很细）断裂，例如通过过度拉伸或摩擦元件。"
   }
  ],
  "scenes": [
   {
    "k": "一个网络喷嘴",
    "title": "变形后接一个网络喷嘴",
    "text": "POY 走正常的 DTY 路线，被拉伸和变形。全拉伸的 FDY 绕过热箱和假捻器，经自己的罗拉以超喂方式喂入。两者在网络喷嘴中汇合，由网络点连接。FDY 的多余长度以扁平丝弧的形式留在表面。",
    "facts": [
     [
      "芯部",
      "变形后的 POY"
     ],
     [
      "效果",
      "超喂的 FDY，扁平丝弧"
     ],
     [
      "优点",
      "结构简单，一个喷嘴"
     ],
     [
      "局限",
      "蓬松度有限，丝弧较扁平"
     ]
    ],
    "p": [
     "网络点连接，丝弧保留"
    ],
    "st": [
     "扁平丝弧",
     "芯部粗，外层细"
    ]
   },
   {
    "k": "变形喷嘴",
    "title": "用空气变形喷嘴代替网络喷嘴",
    "text": "用一个与 ATY 相同的空气变形喷嘴代替网络喷嘴。高度超喂的效果组分在其中形成真正闭合的丝圈，并与变形后的芯部钩连。视喷嘴而定，丝条事先要加湿。",
    "facts": [
     [
      "芯部",
      "变形后的 POY"
     ],
     [
      "效果",
      "FDY 形成真正的丝圈"
     ],
     [
      "优点",
      "蓬松度高，手感接近短纤纱"
     ],
     [
      "缺点",
      "耗气量更高，没有网络点时丝圈固定较差"
     ]
    ],
    "p": [
     "丝圈包绕芯部"
    ],
    "st": [
     "闭合丝圈",
     "丝圈伸到很外面"
    ]
   },
   {
    "k": "两个喷嘴",
    "title": "变形喷嘴与网络喷嘴串联",
    "text": "第一个喷嘴形成丝圈，第二个形成网络点并保持结构。这样蓬松度和抱合力可以分别调节：变形喷嘴处的超喂和压力决定丝圈，网络喷嘴处的压力决定网络点。",
    "facts": [
     [
      "喷嘴 1",
      "变形喷嘴：丝圈"
     ],
     [
      "喷嘴 2",
      "网络喷嘴：网络点"
     ],
     [
      "优点",
      "蓬松度和抱合力可分别调节"
     ],
     [
      "缺点",
      "耗气更多、占地更大、设定更多"
     ]
    ],
    "p": [
     "丝圈",
     "丝圈 + 网络点"
    ],
    "st": [
     "丝圈 + 网络点",
     "丝圈由网络点固定"
    ]
   },
   {
    "k": "热箱前",
    "title": "在热箱前合并两种 POY",
    "text": "两种 POY 在入口处合并，通常借助预网络喷嘴，然后共同拉伸和变形。它们例如在收缩、单丝细度或染色性上不同。效果在定型或染色时才出现：收缩较大的组分缩入芯部，另一组分在外面膨松。",
    "facts": [
     [
      "组分",
      "两种收缩不同的 POY"
     ],
     [
      "效果",
      "在定型或染色时才出现"
     ],
     [
      "优点",
      "正常 DTY 路线，染色性不同时形成混色"
     ],
     [
      "缺点",
      "结果很大程度上取决于原料搭配"
     ]
    ],
    "p": [
     "变形后：混合",
     "定型 / 染色：收缩",
     "POY 2 缩入芯部，POY 1 膨松"
    ],
    "st": [
     "POY 1 在外膨松",
     "染色不同形成混色",
     "POY 2 在芯部"
    ]
   },
   {
    "k": "第二热箱后喷嘴",
    "title": "第二热箱后增加网络喷嘴",
    "text": "第一次网络后，丝条通过第二热箱并被稳定。之后另一个网络喷嘴形成额外的网络点。这样在卷绕和后加工中结构保持得更好。",
    "facts": [
     [
      "流程",
      "网络、稳定、再次网络"
     ],
     [
      "优点",
      "结构稳定，组分不易分离"
     ],
     [
      "缺点",
      "网络点更多、更牢"
     ],
     [
      "关联",
      "按照网络点假设（主题“网络点越牢”），这可能降低断裂伸长"
     ]
    ],
    "p": [
     "第二热箱后的额外网络点"
    ],
    "st": [
     "网络点更多更牢",
     "更紧密，网络点更多"
    ]
   },
   {
    "k": "粗细节",
    "title": "通过欠拉伸形成粗细节效果",
    "text": "单一 POY 以低于其自然拉伸比的拉伸比加工。因此个别段落未被拉伸。这些段落更粗、吸收更多染料、染色更深。由此形成类似棉竹节纱的不规则外观。",
    "facts": [
     [
      "组分",
      "一种 POY"
     ],
     [
      "效果",
      "未拉伸的较粗段落"
     ],
     [
      "优点",
      "棉般外观，染色后有深色点"
     ],
     [
      "缺点",
      "强度较低，工艺窗口窄"
     ]
    ],
    "p": [
     "未拉伸段落：更粗、染色更深",
     "已拉伸"
    ],
    "st": [
     "更深、更粗的段落",
     "细",
     "粗"
    ]
   },
   {
    "k": "单丝断裂",
    "title": "通过可控单丝断裂形成毛羽",
    "text": "有意使个别（通常很细的）单丝断裂，例如对个别单丝过度拉伸或通过摩擦元件。自由端像短纤纱的纤维端一样从纱线中伸出。随后的网络把断裂的单丝重新束缚在纱中。",
    "facts": [
     [
      "组分",
      "一种 POY，常含很细的单丝"
     ],
     [
      "效果",
      "伸出的单丝端，毛羽"
     ],
     [
      "优点",
      "手感和毛羽如短纤纱"
     ],
     [
      "缺点",
      "强度损失、飞毛、断丝率难以控制"
     ]
    ],
    "p": [
     "断裂的单丝以端头伸出"
    ],
    "st": [
     "毛羽如短纤纱",
     "伸出的端头"
    ]
   }
  ]
 }
};
