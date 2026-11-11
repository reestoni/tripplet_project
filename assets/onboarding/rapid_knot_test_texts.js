window.TEXTS = {
 "de": {
  "ui": {
   "eyebrow": "Knowledge Base · Labor",
   "h1": "Verwirbelungsknoten prüfen mit dem RAPID 600 V",
   "lead": "Das RAPID 600 V von Lenzing Instruments zählt die Verwirbelungsknoten im laufenden Garn und prüft, wie fest sie sind. Eine Nadel sticht zwischen die Filamente und läuft bis zum nächsten Knoten. Hält der Knoten die eingestellte Kraft, zählt er als guter Knoten. Fünf kurze Szenen zeigen, wie das funktioniert.",
   "note": "Schematische Darstellung. Gerätedaten aus Datenblatt und Produktseite von Lenzing Instruments. Garn, Knotenfestigkeiten und Auslösekraft sind Beispielwerte; die Nadelbewegung ist in Zeitlupe und vereinfacht dargestellt.",
   "pause": "⏸ Pause",
   "play": "▶ Abspielen",
   "scenes": "Szenen",
   "trig": "Auslösekraft",
   "newYarn": "↻ Neues Garn",
   "dec": ",",
   "clickHint": "Eine Station im Gerät anklicken: Sie wird hier erklärt."
  },
  "cv": {
   "yarnL": "verwirbeltes Filamentgarn: Knoten und offene Bereiche",
   "cards": [
    [
     "Wie viele?",
     "Knoten pro Meter"
    ],
    [
     "Wie regelmässig?",
     "Abstände zwischen den Knoten"
    ],
    [
     "Wie fest?",
     "hält der Knoten die Prüfkraft?"
    ]
   ],
   "needleNote": "Nadelmethode: eine Nadel prüft jeden Knoten mechanisch auf Festigkeit",
   "device": "RAPID 600 V, schematisch",
   "vertical": "senkrechter Fadenlauf",
   "pc": "PC: Live-Kraftverlauf, Statistik",
   "sensorSub": "Nadel + Kraftsensor 0–150 g",
   "sensor": "Kraftsensor",
   "run": "Garnlauf",
   "force": "Kraft",
   "counted": "gezählt: {n}",
   "weak": "schwach: {n}",
   "legOk": "guter Knoten, gezählt",
   "legWeak": "schwacher Knoten, öffnet sich",
   "trigEx": "Auslösekraft: {g} g (Beispiel)",
   "trigL": "Auslösekraft {g} g",
   "forceAx": "Kraft an der Nadel",
   "lenAx": "Garnlänge →",
   "msg": {
    "wait": "Nadel wartet auf einen offenen Bereich",
    "stab": "Nadel sticht zwischen die Filamente",
    "glide": "Nadel gleitet durch den offenen Bereich",
    "hit": "Nadel trifft auf einen Knoten, die Kraft steigt",
    "ok": "Auslösekraft {g} g erreicht: guter Knoten gezählt",
    "weak": "Knoten öffnet bei {g} g: schwacher Knoten, nicht gezählt"
   },
   "distAx": "Abstand zwischen gezählten Knoten",
   "countAx": "Anzahl",
   "rows": [
    "Knoten pro Meter",
    "mittlerer Abstand",
    "grösster Abstand",
    "schwache Knoten"
   ],
   "foot": "Auslösekraft {g} g · simuliertes Garn, 20 m",
   "hint": "Regler: Auslösekraft ändern"
  },
  "stations": [
   {
    "n": "Spule",
    "d": "Das Garn wird von der Spule abgezogen, optional aus dem Spulenwechsler SESS mit bis zu 24 Positionen."
   },
   {
    "n": "Einfädeln",
    "d": "Das Garn wird automatisch eingefädelt, auch die Probenentnahme läuft automatisch."
   },
   {
    "n": "Vorspannung",
    "s": "Vorspannung, servogeregelt",
    "d": "Eine servogeregelte Vorspannung hält die Fadenspannung konstant."
   },
   {
    "n": "Messeinheit",
    "d": "Eine senkrecht bewegte Nadel sticht ins Garn, ein Kraftsensor (0–150 g, ±0,1 g) misst die Kraft an der Nadel."
   },
   {
    "n": "Abzug und Absaugung",
    "d": "Das Garn wird mit Prüfgeschwindigkeit abgezogen und abgesaugt."
   }
  ],
  "scenes": [
   {
    "k": "Wozu",
    "title": "Warum Knoten gezählt und geprüft werden",
    "text": "Verwirbelte Filamentgarne haben in kurzen Abständen Knoten, die die Filamente zusammenhalten. Für die Weiterverarbeitung zählt nicht nur, wie viele Knoten es gibt, sondern auch, ob sie fest genug und gleichmässig verteilt sind. Ein schwacher Knoten geht unter Zug auf und hilft dann beim Weben oder Stricken nicht mehr.",
    "facts": [
     [
      "Knotenzahl",
      "Knoten pro Meter"
     ],
     [
      "Knotenabstand",
      "mittlerer und grösster Abstand"
     ],
     [
      "Knotenfestigkeit",
      "guter oder schwacher Knoten"
     ],
     [
      "Norm",
      "ASTM D4724"
     ]
    ]
   },
   {
    "k": "Aufbau",
    "title": "Aufbau: senkrechter Fadenlauf",
    "text": "Das Garn läuft senkrecht durch das Gerät. Es wird automatisch eingefädelt, eine servogeregelte Vorspannung hält die Fadenspannung konstant. In der Messeinheit sticht eine senkrecht bewegte Nadel ins Garn, ein Kraftsensor misst die Kraft an der Nadel. Danach wird das Garn abgezogen und abgesaugt.",
    "facts": [
     [
      "Einfädeln",
      "automatisch, auch die Probenentnahme"
     ],
     [
      "Vorspannung",
      "servogeregelt"
     ],
     [
      "Kraftsensor",
      "0–150 g, ±0,1 g"
     ],
     [
      "Spulenwechsler",
      "optional SESS, bis 24 Positionen"
     ],
     [
      "Stationen",
      "im Bild anklicken, um sie erklärt zu bekommen"
     ]
    ]
   },
   {
    "k": "Messprinzip",
    "title": "Die Nadel läuft bis zum nächsten Knoten",
    "text": "Die Nadel sticht in einem offenen Bereich zwischen die Filamente. Das Garn läuft weiter, die Nadel gleitet durch den offenen Bereich, bis sie auf den nächsten Knoten trifft. Der Knoten drückt gegen die Nadel, die Kraft steigt. Erreicht sie die eingestellte Auslösekraft, wird der Knoten gezählt und die Nadel zieht sich zurück. Das Garn muss dafür nicht anhalten.",
    "facts": [
     [
      "Nadel",
      "senkrecht bewegt, sticht periodisch ein"
     ],
     [
      "Messgrösse",
      "Kraft an der Nadel und Garnlänge"
     ],
     [
      "Prüfgeschwindigkeit",
      "bis 50 m/min"
     ],
     [
      "Darstellung",
      "Zeitlupe, Ausschnitt um 90° gedreht"
     ]
    ]
   },
   {
    "k": "Gut oder schwach",
    "title": "Gute und schwache Knoten",
    "text": "Ein schwacher Knoten öffnet sich, bevor die Kraft die Auslösekraft erreicht. Die Kraft fällt ab, die Nadel gleitet weiter bis zum nächsten Knoten. Dieser Knoten wird nicht gezählt, der gemessene Abstand wird grösser. Mit dem Regler lässt sich die Auslösekraft verändern.",
    "facts": [
     [
      "Guter Knoten",
      "hält die Auslösekraft"
     ],
     [
      "Schwacher Knoten",
      "öffnet vorher, wird nicht gezählt"
     ],
     [
      "Auslösekraft",
      "vom Bediener eingestellt"
     ],
     [
      "Live-Diagramm",
      "Kraftverlauf mit Markierungen"
     ]
    ]
   },
   {
    "k": "Auswertung",
    "title": "Ergebnis pro Spule",
    "text": "Nach etwa 30 Sekunden Prüfzeit liefert die Software die Statistik: Knoten pro Meter, mittlerer Abstand, grösster Abstand und die Verteilung der Abstände. Der grösste Abstand und die Breite der Verteilung zeigen, wie gleichmässig verwirbelt ist. Eine höhere Auslösekraft ist strenger: Es zählen weniger Knoten, die Abstände werden grösser.",
    "facts": [
     [
      "Messbereich",
      "0,5–180 Knoten/m"
     ],
     [
      "Prüfzeit",
      "etwa 30 s pro Probe"
     ],
     [
      "Gleichmässigkeit",
      "grösster Abstand und Verteilung der Abstände"
     ],
     [
      "Titerbereich",
      "15–4000 den"
     ],
     [
      "Garne",
      "POY, FDY, DTY, BCF"
     ]
    ]
   }
  ]
 },
 "en": {
  "ui": {
   "eyebrow": "Knowledge Base · Lab",
   "h1": "Testing intermingling nips with the RAPID 600 V",
   "lead": "The RAPID 600 V by Lenzing Instruments counts the intermingling nips in the running yarn and checks how firm they are. A needle pierces between the filaments and runs to the next nip. If the nip holds the set force, it counts as a good nip. Five short scenes show how it works.",
   "note": "Schematic representation. Device data from the data sheet and product page of Lenzing Instruments. Yarn, nip strengths and trigger force are example values; the needle movement is shown in slow motion and simplified.",
   "pause": "⏸ Pause",
   "play": "▶ Play",
   "scenes": "Scenes",
   "trig": "Trigger force",
   "newYarn": "↻ New yarn",
   "dec": ".",
   "clickHint": "Click a station of the device: it is explained here."
  },
  "cv": {
   "yarnL": "intermingled filament yarn: nips and open sections",
   "cards": [
    [
     "How many?",
     "nips per metre"
    ],
    [
     "How regular?",
     "distances between the nips"
    ],
    [
     "How firm?",
     "does the nip hold the test force?"
    ]
   ],
   "needleNote": "Needle method: a needle checks every nip mechanically for firmness",
   "device": "RAPID 600 V, schematic",
   "vertical": "vertical yarn path",
   "pc": "PC: live force curve, statistics",
   "sensorSub": "needle + force sensor 0–150 g",
   "sensor": "Force sensor",
   "run": "Yarn travel",
   "force": "Force",
   "counted": "counted: {n}",
   "weak": "weak: {n}",
   "legOk": "good nip, counted",
   "legWeak": "weak nip, opens",
   "trigEx": "Trigger force: {g} g (example)",
   "trigL": "Trigger force {g} g",
   "forceAx": "Force at the needle",
   "lenAx": "Yarn length →",
   "msg": {
    "wait": "Needle waits for an open section",
    "stab": "Needle pierces between the filaments",
    "glide": "Needle glides through the open section",
    "hit": "Needle meets a nip, the force rises",
    "ok": "Trigger force {g} g reached: good nip counted",
    "weak": "Nip opens at {g} g: weak nip, not counted"
   },
   "distAx": "Distance between counted nips",
   "countAx": "Count",
   "rows": [
    "Nips per metre",
    "mean distance",
    "largest distance",
    "weak nips"
   ],
   "foot": "Trigger force {g} g · simulated yarn, 20 m",
   "hint": "Slider: change the trigger force"
  },
  "stations": [
   {
    "n": "Package",
    "d": "The yarn is pulled off the package, optionally from the SESS package changer with up to 24 positions."
   },
   {
    "n": "Threading",
    "d": "The yarn is threaded in automatically; sampling is automatic too."
   },
   {
    "n": "Pretension",
    "s": "Pretension, servo-controlled",
    "d": "A servo-controlled pretension keeps the yarn tension constant."
   },
   {
    "n": "Measuring unit",
    "d": "A vertically moving needle pierces the yarn; a force sensor (0–150 g, ±0.1 g) measures the force at the needle."
   },
   {
    "n": "Take-off and suction",
    "d": "The yarn is taken off at test speed and sucked away."
   }
  ],
  "scenes": [
   {
    "k": "Purpose",
    "title": "Why nips are counted and tested",
    "text": "Intermingled filament yarns have nips at short distances that hold the filaments together. For further processing it matters not only how many nips there are, but also whether they are firm enough and evenly distributed. A weak nip opens under tension and then no longer helps in weaving or knitting.",
    "facts": [
     [
      "Nip count",
      "nips per metre"
     ],
     [
      "Nip distance",
      "mean and largest distance"
     ],
     [
      "Nip strength",
      "good or weak nip"
     ],
     [
      "Standard",
      "ASTM D4724"
     ]
    ]
   },
   {
    "k": "Set-up",
    "title": "Set-up: vertical yarn path",
    "text": "The yarn runs vertically through the device. It is threaded in automatically, a servo-controlled pretension keeps the yarn tension constant. In the measuring unit a vertically moving needle pierces the yarn, a force sensor measures the force at the needle. Then the yarn is taken off and sucked away.",
    "facts": [
     [
      "Threading",
      "automatic, including sampling"
     ],
     [
      "Pretension",
      "servo-controlled"
     ],
     [
      "Force sensor",
      "0–150 g, ±0.1 g"
     ],
     [
      "Package changer",
      "optional SESS, up to 24 positions"
     ],
     [
      "Stations",
      "click them in the picture to have them explained"
     ]
    ]
   },
   {
    "k": "Principle",
    "title": "The needle runs to the next nip",
    "text": "The needle pierces between the filaments in an open section. The yarn keeps running, the needle glides through the open section until it meets the next nip. The nip presses against the needle, the force rises. When it reaches the set trigger force, the nip is counted and the needle withdraws. The yarn does not have to stop for this.",
    "facts": [
     [
      "Needle",
      "moves vertically, pierces periodically"
     ],
     [
      "Measured",
      "force at the needle and yarn length"
     ],
     [
      "Test speed",
      "up to 50 m/min"
     ],
     [
      "Display",
      "slow motion, detail rotated by 90°"
     ]
    ]
   },
   {
    "k": "Good or weak",
    "title": "Good and weak nips",
    "text": "A weak nip opens before the force reaches the trigger force. The force drops, the needle glides on to the next nip. This nip is not counted, the measured distance becomes larger. Use the slider to change the trigger force.",
    "facts": [
     [
      "Good nip",
      "holds the trigger force"
     ],
     [
      "Weak nip",
      "opens before, not counted"
     ],
     [
      "Trigger force",
      "set by the operator"
     ],
     [
      "Live chart",
      "force curve with markers"
     ]
    ]
   },
   {
    "k": "Evaluation",
    "title": "Result per package",
    "text": "After about 30 seconds of testing the software provides the statistics: nips per metre, mean distance, largest distance and the distribution of distances. The largest distance and the width of the distribution show how evenly the yarn is intermingled. A higher trigger force is stricter: fewer nips count, the distances become larger.",
    "facts": [
     [
      "Range",
      "0.5–180 nips/m"
     ],
     [
      "Test time",
      "about 30 s per sample"
     ],
     [
      "Evenness",
      "largest distance and distribution of distances"
     ],
     [
      "Count range",
      "15–4000 den"
     ],
     [
      "Yarns",
      "POY, FDY, DTY, BCF"
     ]
    ]
   }
  ]
 },
 "es": {
  "ui": {
   "eyebrow": "Knowledge Base · Laboratorio",
   "h1": "Ensayo de nudos de entrelazado con el RAPID 600 V",
   "lead": "El RAPID 600 V de Lenzing Instruments cuenta los nudos de entrelazado en el hilo en marcha y comprueba lo firmes que son. Una aguja pincha entre los filamentos y avanza hasta el siguiente nudo. Si el nudo aguanta la fuerza ajustada, cuenta como nudo bueno. Cinco escenas cortas muestran cómo funciona.",
   "note": "Representación esquemática. Datos del equipo según la hoja técnica y la página de producto de Lenzing Instruments. El hilo, la resistencia de los nudos y la fuerza de disparo son valores de ejemplo; el movimiento de la aguja se muestra a cámara lenta y simplificado.",
   "pause": "⏸ Pausa",
   "play": "▶ Reproducir",
   "scenes": "Escenas",
   "trig": "Fuerza de disparo",
   "newYarn": "↻ Hilo nuevo",
   "dec": ",",
   "clickHint": "Haz clic en una estación del equipo: se explica aquí."
  },
  "cv": {
   "yarnL": "hilo de filamento entrelazado: nudos y tramos abiertos",
   "cards": [
    [
     "¿Cuántos?",
     "nudos por metro"
    ],
    [
     "¿Qué tan regulares?",
     "distancias entre los nudos"
    ],
    [
     "¿Qué tan firmes?",
     "¿aguanta el nudo la fuerza de ensayo?"
    ]
   ],
   "needleNote": "Método de aguja: una aguja comprueba mecánicamente la firmeza de cada nudo",
   "device": "RAPID 600 V, esquema",
   "vertical": "recorrido vertical del hilo",
   "pc": "PC: curva de fuerza en vivo, estadística",
   "sensorSub": "aguja + sensor de fuerza 0–150 g",
   "sensor": "Sensor de fuerza",
   "run": "Avance del hilo",
   "force": "Fuerza",
   "counted": "contados: {n}",
   "weak": "débiles: {n}",
   "legOk": "nudo bueno, contado",
   "legWeak": "nudo débil, se abre",
   "trigEx": "Fuerza de disparo: {g} g (ejemplo)",
   "trigL": "Fuerza de disparo {g} g",
   "forceAx": "Fuerza en la aguja",
   "lenAx": "Longitud del hilo →",
   "msg": {
    "wait": "La aguja espera un tramo abierto",
    "stab": "La aguja pincha entre los filamentos",
    "glide": "La aguja se desliza por el tramo abierto",
    "hit": "La aguja llega a un nudo, la fuerza sube",
    "ok": "Fuerza de disparo de {g} g alcanzada: nudo bueno contado",
    "weak": "El nudo se abre a {g} g: nudo débil, no se cuenta"
   },
   "distAx": "Distancia entre nudos contados",
   "countAx": "Cantidad",
   "rows": [
    "Nudos por metro",
    "distancia media",
    "distancia máxima",
    "nudos débiles"
   ],
   "foot": "Fuerza de disparo {g} g · hilo simulado, 20 m",
   "hint": "Regulador: cambiar la fuerza de disparo"
  },
  "stations": [
   {
    "n": "Bobina",
    "d": "El hilo se saca de la bobina, opcionalmente desde el cambiador SESS con hasta 24 posiciones."
   },
   {
    "n": "Enhebrado",
    "d": "El hilo se enhebra automáticamente; la toma de muestras también es automática."
   },
   {
    "n": "Pretensión",
    "s": "Pretensión servocontrolada",
    "d": "Una pretensión servocontrolada mantiene constante la tensión del hilo."
   },
   {
    "n": "Unidad de medición",
    "d": "Una aguja con movimiento vertical pincha el hilo; un sensor de fuerza (0–150 g, ±0,1 g) mide la fuerza en la aguja."
   },
   {
    "n": "Extracción y aspiración",
    "d": "El hilo se extrae a la velocidad de ensayo y se aspira."
   }
  ],
  "scenes": [
   {
    "k": "Para qué",
    "title": "Por qué se cuentan y ensayan los nudos",
    "text": "Los hilos de filamento entrelazados tienen nudos a cortas distancias que mantienen unidos los filamentos. Para el procesamiento posterior no solo importa cuántos nudos hay, sino también si son lo bastante firmes y están repartidos de forma regular. Un nudo débil se abre bajo tracción y ya no ayuda al tejer o tricotar.",
    "facts": [
     [
      "Número de nudos",
      "nudos por metro"
     ],
     [
      "Distancia entre nudos",
      "media y máxima"
     ],
     [
      "Firmeza",
      "nudo bueno o débil"
     ],
     [
      "Norma",
      "ASTM D4724"
     ]
    ]
   },
   {
    "k": "Montaje",
    "title": "Montaje: recorrido vertical del hilo",
    "text": "El hilo pasa verticalmente por el equipo. Se enhebra automáticamente y una pretensión servocontrolada mantiene constante la tensión. En la unidad de medición, una aguja con movimiento vertical pincha el hilo y un sensor mide la fuerza en la aguja. Después el hilo se extrae y se aspira.",
    "facts": [
     [
      "Enhebrado",
      "automático, incluida la toma de muestras"
     ],
     [
      "Pretensión",
      "servocontrolada"
     ],
     [
      "Sensor de fuerza",
      "0–150 g, ±0,1 g"
     ],
     [
      "Cambiador",
      "opcional SESS, hasta 24 posiciones"
     ],
     [
      "Estaciones",
      "haz clic en la imagen para ver la explicación"
     ]
    ]
   },
   {
    "k": "Principio",
    "title": "La aguja avanza hasta el siguiente nudo",
    "text": "La aguja pincha entre los filamentos en un tramo abierto. El hilo sigue avanzando y la aguja se desliza por el tramo abierto hasta que llega al siguiente nudo. El nudo presiona contra la aguja y la fuerza sube. Cuando alcanza la fuerza de disparo ajustada, el nudo se cuenta y la aguja se retira. El hilo no tiene que detenerse.",
    "facts": [
     [
      "Aguja",
      "movimiento vertical, pincha periódicamente"
     ],
     [
      "Medición",
      "fuerza en la aguja y longitud del hilo"
     ],
     [
      "Velocidad de ensayo",
      "hasta 50 m/min"
     ],
     [
      "Representación",
      "cámara lenta, detalle girado 90°"
     ]
    ]
   },
   {
    "k": "Bueno o débil",
    "title": "Nudos buenos y débiles",
    "text": "Un nudo débil se abre antes de que la fuerza alcance la fuerza de disparo. La fuerza cae y la aguja sigue deslizándose hasta el siguiente nudo. Ese nudo no se cuenta y la distancia medida aumenta. Con el regulador se cambia la fuerza de disparo.",
    "facts": [
     [
      "Nudo bueno",
      "aguanta la fuerza de disparo"
     ],
     [
      "Nudo débil",
      "se abre antes, no se cuenta"
     ],
     [
      "Fuerza de disparo",
      "la ajusta el operador"
     ],
     [
      "Gráfico en vivo",
      "curva de fuerza con marcas"
     ]
    ]
   },
   {
    "k": "Evaluación",
    "title": "Resultado por bobina",
    "text": "Tras unos 30 segundos de ensayo, el software da la estadística: nudos por metro, distancia media, distancia máxima y la distribución de distancias. La distancia máxima y la anchura de la distribución muestran lo regular que es el entrelazado. Una fuerza de disparo mayor es más estricta: cuentan menos nudos y las distancias aumentan.",
    "facts": [
     [
      "Rango",
      "0,5–180 nudos/m"
     ],
     [
      "Tiempo de ensayo",
      "unos 30 s por muestra"
     ],
     [
      "Regularidad",
      "distancia máxima y distribución de distancias"
     ],
     [
      "Rango de título",
      "15–4000 den"
     ],
     [
      "Hilos",
      "POY, FDY, DTY, BCF"
     ]
    ]
   }
  ]
 },
 "zh": {
  "ui": {
   "eyebrow": "知识库 · 实验室",
   "h1": "用 RAPID 600 V 检测网络点",
   "lead": "Lenzing Instruments 的 RAPID 600 V 在运行的丝上统计网络点，并检测其牢度。一根针刺入单丝之间，随丝移动到下一个网络点。如果网络点能承受设定的力，就计为好网络点。五个简短场景展示其工作原理。",
   "note": "示意图。设备数据来自 Lenzing Instruments 的数据表和产品页面。丝、网络点牢度和触发力为示例值；针的运动以慢动作简化显示。",
   "pause": "⏸ 暂停",
   "play": "▶ 播放",
   "scenes": "场景",
   "trig": "触发力",
   "newYarn": "↻ 换一根丝",
   "dec": ".",
   "clickHint": "点击设备中的工位，此处会显示说明。"
  },
  "cv": {
   "yarnL": "网络丝：网络点和开放段",
   "cards": [
    [
     "有多少？",
     "每米网络点数"
    ],
    [
     "有多规则？",
     "网络点之间的间距"
    ],
    [
     "有多牢？",
     "网络点能否承受测试力？"
    ]
   ],
   "needleNote": "针刺法：用针机械地检测每个网络点的牢度",
   "device": "RAPID 600 V 示意",
   "vertical": "竖直走丝",
   "pc": "电脑：实时力曲线、统计",
   "sensorSub": "针 + 力传感器 0–150 g",
   "sensor": "力传感器",
   "run": "走丝方向",
   "force": "力",
   "counted": "计数：{n}",
   "weak": "弱：{n}",
   "legOk": "好网络点，已计数",
   "legWeak": "弱网络点，被打开",
   "trigEx": "触发力：{g} g（示例）",
   "trigL": "触发力 {g} g",
   "forceAx": "针上的力",
   "lenAx": "丝长度 →",
   "msg": {
    "wait": "针等待开放段",
    "stab": "针刺入单丝之间",
    "glide": "针在开放段中滑动",
    "hit": "针碰到网络点，力上升",
    "ok": "达到触发力 {g} g：好网络点已计数",
    "weak": "网络点在 {g} g 时打开：弱网络点，不计数"
   },
   "distAx": "已计数网络点之间的间距",
   "countAx": "数量",
   "rows": [
    "每米网络点数",
    "平均间距",
    "最大间距",
    "弱网络点"
   ],
   "foot": "触发力 {g} g · 模拟丝，20 m",
   "hint": "滑块：改变触发力"
  },
  "stations": [
   {
    "n": "丝筒",
    "d": "丝从丝筒引出，可选配最多 24 个位置的 SESS 换筒装置。"
   },
   {
    "n": "穿丝",
    "d": "自动穿丝，取样也是自动的。"
   },
   {
    "n": "预张力",
    "s": "预张力（伺服控制）",
    "d": "伺服控制的预张力使丝的张力保持恒定。"
   },
   {
    "n": "测量单元",
    "d": "竖直运动的针刺入丝中，力传感器（0–150 g，±0.1 g）测量针上的力。"
   },
   {
    "n": "引出和吸丝",
    "d": "丝以测试速度引出并被吸走。"
   }
  ],
  "scenes": [
   {
    "k": "用途",
    "title": "为什么要统计和检测网络点",
    "text": "网络丝每隔一小段就有网络点把单丝束在一起。对后加工来说，不仅网络点数量重要，牢度和分布是否均匀也同样重要。弱网络点在拉力下会打开，在机织或针织时就不再起作用。",
    "facts": [
     [
      "网络点数",
      "每米网络点数"
     ],
     [
      "网络点间距",
      "平均间距和最大间距"
     ],
     [
      "网络点牢度",
      "好网络点或弱网络点"
     ],
     [
      "标准",
      "ASTM D4724"
     ]
    ]
   },
   {
    "k": "结构",
    "title": "结构：竖直走丝",
    "text": "丝竖直通过设备。自动穿丝，伺服控制的预张力使张力保持恒定。在测量单元中，竖直运动的针刺入丝中，力传感器测量针上的力。之后丝被引出并吸走。",
    "facts": [
     [
      "穿丝",
      "自动，含取样"
     ],
     [
      "预张力",
      "伺服控制"
     ],
     [
      "力传感器",
      "0–150 g，±0.1 g"
     ],
     [
      "换筒装置",
      "可选 SESS，最多 24 个位置"
     ],
     [
      "工位",
      "在图中点击即可查看说明"
     ]
    ]
   },
   {
    "k": "测量原理",
    "title": "针随丝移动到下一个网络点",
    "text": "针在开放段刺入单丝之间。丝继续运行，针在开放段中滑动，直到碰到下一个网络点。网络点压在针上，力上升。达到设定的触发力时，该网络点被计数，针退出。丝无需停下。",
    "facts": [
     [
      "针",
      "竖直运动，周期性刺入"
     ],
     [
      "测量量",
      "针上的力和丝长度"
     ],
     [
      "测试速度",
      "最高 50 m/min"
     ],
     [
      "显示",
      "慢动作，局部旋转 90°"
     ]
    ]
   },
   {
    "k": "好或弱",
    "title": "好网络点和弱网络点",
    "text": "弱网络点在力达到触发力之前就打开了。力下降，针继续滑到下一个网络点。这个网络点不计数，测得的间距变大。可用滑块改变触发力。",
    "facts": [
     [
      "好网络点",
      "能承受触发力"
     ],
     [
      "弱网络点",
      "提前打开，不计数"
     ],
     [
      "触发力",
      "由操作人员设定"
     ],
     [
      "实时曲线",
      "带标记的力曲线"
     ]
    ]
   },
   {
    "k": "评估",
    "title": "每个丝筒的结果",
    "text": "测试约 30 秒后，软件给出统计：每米网络点数、平均间距、最大间距和间距分布。最大间距和分布宽度显示网络的均匀程度。触发力越高越严格：计数的网络点越少，间距越大。",
    "facts": [
     [
      "测量范围",
      "0.5–180 个/米"
     ],
     [
      "测试时间",
      "每个样品约 30 秒"
     ],
     [
      "均匀性",
      "最大间距和间距分布"
     ],
     [
      "纤度范围",
      "15–4000 den"
     ],
     [
      "纱线",
      "POY、FDY、DTY、BCF"
     ]
    ]
   }
  ]
 }
};
