window.TEXTS = {
 "de": {
  "ui": {
   "eyebrow": "Knowledge Base · DTY · Spezialwissen · Hypothese",
   "h1": "Harte Knoten, weniger Dehnung?",
   "lead": "Eine Messstrecke mit mehreren Knoten wird gezogen. Zwischen den Knoten sind die Filamente nicht alle gleich lang. Das Modell zeigt, was passiert, wenn die Knoten halten, und was, wenn sie unter Zug öffnen.",
   "note": "Vereinfachtes Modell zur Veranschaulichung der These: 12 Filamente, linear-elastisch bis zum Bruch, 5 Segmente mit ungleichen Filamentlängen, Knoten mit Haltekraft, die beim Öffnen gebundene Länge freigeben. Kräuselung und Knotengeometrie sind nicht abgebildet. Alle Werte sind relativ und keine Messwerte.",
   "pause": "⏸ Pause",
   "play": "▶ Abspielen",
   "scenes": "Szenen",
   "stab": "Knotenstabilität",
   "again": "↻ Neu ziehen"
  },
  "cv": {
   "pull": "Zug",
   "gauge": "Messstrecke: 5 Segmente, 4 Knoten",
   "knots": "Knoten",
   "hold": "hält",
   "opening": "öffnet",
   "open": "offen",
   "strain": "Dehnung der Messstrecke →",
   "force": "Kraft",
   "shortest": "kürzestes Filament: trägt zuerst",
   "longest": "längstes: hängt durch",
   "knot1": "Knoten: verschlungene Filamente,",
   "knot2": "tragen erst nach dem Öffnen",
   "broken": "gerissen",
   "knotsOpen": "Knoten offen",
   "peak": "Höchstzugkraft",
   "msgDone": "Garn gerissen, im Segment {seg}",
   "msgChain": "Kettenreaktion im Segment {seg}: Die Last springt weiter",
   "msgOpening": "Knoten K{k} öffnet: Die verschlungenen Abschnitte werden gestreckt und tragen mit",
   "msgBroken": "Segment {seg}: Die übrigen Filamente übernehmen die Last",
   "msgSlack": "Filamente hängen noch durch, noch keine Last",
   "msgOpen": "{n} Knoten offen: Auch die früheren Knotenabschnitte tragen, die Filamente gleichen sich aus",
   "msgHold": "Knoten halten: In jedem Segment tragen die kürzesten Filamente",
   "curves": "Kraft-Dehnungs-Kurven (gleiche Messstrecke)",
   "soft": "weiche Knoten",
   "hard": "harte Knoten",
   "slider": "Reglerstellung",
   "mean": "Mittelwert über 6 Messstrecken",
   "rel": "relativ zu sehr weichen Knoten",
   "stabAxis": "Knotenstabilität →",
   "easy": "öffnet leicht",
   "computing": "wird berechnet … {p} %",
   "elong": "Bruchdehnung",
   "tenacity": "Höchstzugkraft",
   "summary": "Bei {k} % Knotenstabilität: Bruchdehnung {ru} %, Höchstzugkraft {rf} %",
   "disclaimer": "Trend des Modells, keine Messwerte. Ob Grössenordnung und Übergang stimmen, muss ein Versuch zeigen."
  },
  "steps": [
   {
    "a": "Harter Knoten hält",
    "b": "wirkt als Klemmstelle",
    "d": "Ein harter Knoten hält bis zum Bruch. Er klemmt die Filamente wie eine Klemme: Längenunterschiede bleiben in ihrem Segment eingesperrt."
   },
   {
    "a": "Kurze tragen zuerst",
    "b": "lange hängen noch durch",
    "d": "In jedem Segment werden zuerst die kürzesten Filamente gespannt. Die längeren hängen noch durch und tragen nichts."
   },
   {
    "a": "Kettenreaktion",
    "b": "im schwächsten Segment",
    "d": "Reisst im ungünstigsten Segment ein Filament, federn die anderen Segmente zurück und dehnen genau dieses Segment weiter. Szene Harte Knoten zeigt das live."
   },
   {
    "a": "Weicher Knoten öffnet",
    "b": "Länge wird frei, Filamente gleichen aus",
    "d": "Ein weicher Knoten öffnet unter Zug, gibt seine gebundene Länge frei, und die Filamente gleichen über mehrere Segmente aus. Szene Weiche Knoten zeigt das live."
   }
  ],
  "scenes": [
   {
    "k": "These",
    "title": "Ungleich lange Filamente zwischen festen Knoten",
    "text": "Die Messstrecke enthält mehrere Knoten. In jedem Segment zwischen zwei Knoten liegen die Filamente unterschiedlich lang. Ein harter Knoten wirkt wie eine Klemmstelle: Die Längenunterschiede bleiben in ihrem Segment eingesperrt. Ein weicher Knoten öffnet unter Zug, gibt seine gebundene Länge frei und lässt die Filamente über mehrere Segmente ausgleichen.",
    "facts": [
     [
      "Harter Knoten",
      "hält und wirkt als Klemmstelle"
     ],
     [
      "Weicher Knoten",
      "öffnet unter Zug"
     ],
     [
      "Kurze Filamente",
      "tragen in jedem Segment zuerst"
     ],
     [
      "Kette",
      "alle Segmente tragen dieselbe Kraft"
     ],
     [
      "Schritte",
      "unten anklicken, um sie zu erklären"
     ]
    ]
   },
   {
    "k": "Harte Knoten",
    "title": "Harte Knoten: Kettenreaktion im schwächsten Segment",
    "text": "Alle Knoten halten. In jedem Segment tragen zuerst die kürzesten Filamente. Das Segment mit der ungünstigsten Längenverteilung versagt zuerst: Reisst dort ein Filament, federn die anderen Segmente zurück und dehnen genau dieses Segment weiter. Die Filamente reissen dort eines nach dem anderen, während die übrigen Segmente kaum gedehnt sind.",
    "facts": [
     [
      "Knoten",
      "halten bis zum Bruch"
     ],
     [
      "Bruch",
      "lokal, in einem Segment"
     ],
     [
      "Kettenreaktion",
      "die übrigen Segmente federn zurück"
     ],
     [
      "Ergebnis",
      "tiefe Bruchdehnung und Höchstzugkraft"
     ]
    ]
   },
   {
    "k": "Weiche Knoten",
    "title": "Weiche Knoten: Öffnen und Ausgleichen",
    "text": "Sobald die Kraft die Haltekraft eines Knotens übersteigt, öffnet er. Die Filamentabschnitte, die im Knoten verschlungen und durch Reibung festgelegt waren, werden gestreckt und tragen ab jetzt selbst Kraft. Die tragende Länge wird grösser, die Kraft steigt kurz langsamer. Ist der Knoten offen, rutschen die Filamente durch, und die Nachbarsegmente verhalten sich wie ein langes Segment. Die Längenunterschiede mitteln sich aus, und die Filamente tragen fast gleichzeitig.",
    "facts": [
     [
      "Knoten",
      "öffnen nacheinander, der schwächste zuerst"
     ],
     [
      "Knotenabschnitte",
      "werden gestreckt und tragen mit"
     ],
     [
      "Ausgleich",
      "Filamente rutschen über mehrere Segmente"
     ],
     [
      "Ergebnis",
      "höhere Bruchdehnung und Höchstzugkraft"
     ]
    ]
   },
   {
    "k": "Vergleich",
    "title": "Je stabiler der Knoten, desto tiefer die Dehnung",
    "text": "Links die Kraft-Dehnungs-Kurven derselben Messstrecke, rechts der Mittelwert aus sechs zufälligen Messstrecken je Knotenstabilität. Im Modell sinken Bruchdehnung und Höchstzugkraft, sobald die Knoten unter der Bruchkraft nicht mehr öffnen. Mit dem Regler lässt sich die Knotenstabilität verändern.",
    "facts": [
     [
      "Bruchdehnung",
      "hier die Dehnung bei Höchstzugkraft"
     ],
     [
      "Übergang",
      "entscheidend ist, ob Knoten vor dem Bruch öffnen"
     ],
     [
      "Erkennbar an",
      "Plateaus beim Öffnen, Stufen vor dem Bruch"
     ],
     [
      "Fachbegriff",
      "Faserbündelmodell mit Schlupf"
     ]
    ]
   }
  ]
 },
 "en": {
  "ui": {
   "eyebrow": "Knowledge Base · DTY · Specialist knowledge · Hypothesis",
   "h1": "Hard nips, less elongation?",
   "lead": "A gauge length with several nips is pulled. Between the nips the filaments are not all equally long. The model shows what happens when the nips hold, and what happens when they open under tension.",
   "note": "Simplified model to illustrate the hypothesis: 12 filaments, linear-elastic up to break, 5 segments with unequal filament lengths, nips with a holding force that release bound length when they open. Crimp and nip geometry are not modelled. All values are relative, not measurements.",
   "pause": "⏸ Pause",
   "play": "▶ Play",
   "scenes": "Scenes",
   "stab": "Nip stability",
   "again": "↻ Pull again"
  },
  "cv": {
   "pull": "Pull",
   "gauge": "Gauge length: 5 segments, 4 nips",
   "knots": "Nips",
   "hold": "holds",
   "opening": "opening",
   "open": "open",
   "strain": "Elongation of the gauge length →",
   "force": "Force",
   "shortest": "shortest filament: carries first",
   "longest": "longest: still slack",
   "knot1": "Nip: entangled filaments,",
   "knot2": "carry only after opening",
   "broken": "broken",
   "knotsOpen": "nips open",
   "peak": "Maximum force",
   "msgDone": "Yarn broken, in segment {seg}",
   "msgChain": "Chain reaction in segment {seg}: the load jumps on",
   "msgOpening": "Nip K{k} opens: the entangled sections are straightened and carry too",
   "msgBroken": "Segment {seg}: the remaining filaments take over the load",
   "msgSlack": "Filaments still slack, no load yet",
   "msgOpen": "{n} nips open: the former nip sections carry too, the filaments even out",
   "msgHold": "Nips hold: in every segment the shortest filaments carry",
   "curves": "Force-elongation curves (same gauge length)",
   "soft": "soft nips",
   "hard": "hard nips",
   "slider": "slider setting",
   "mean": "Mean of 6 gauge lengths",
   "rel": "relative to very soft nips",
   "stabAxis": "Nip stability →",
   "easy": "opens easily",
   "computing": "calculating … {p} %",
   "elong": "Elongation at break",
   "tenacity": "Maximum force",
   "summary": "At {k} % nip stability: elongation at break {ru} %, maximum force {rf} %",
   "disclaimer": "Trend of the model, not measurements. Whether magnitude and transition are right has to be shown by a trial."
  },
  "steps": [
   {
    "a": "Hard nip holds",
    "b": "acts as a clamp",
    "d": "A hard nip holds until break. It clamps the filaments: length differences stay locked in their segment."
   },
   {
    "a": "Short ones carry first",
    "b": "long ones are still slack",
    "d": "In every segment the shortest filaments are tensioned first. The longer ones are still slack and carry nothing."
   },
   {
    "a": "Chain reaction",
    "b": "in the weakest segment",
    "d": "If a filament breaks in the least favourable segment, the other segments spring back and stretch exactly this segment further. Scene Hard nips shows it live."
   },
   {
    "a": "Soft nip opens",
    "b": "length is released, filaments even out",
    "d": "A soft nip opens under tension, releases its bound length, and the filaments even out over several segments. Scene Soft nips shows it live."
   }
  ],
  "scenes": [
   {
    "k": "Hypothesis",
    "title": "Unequal filament lengths between fixed nips",
    "text": "The gauge length contains several nips. In every segment between two nips the filaments have different lengths. A hard nip acts like a clamp: the length differences stay locked in their segment. A soft nip opens under tension, releases its bound length and lets the filaments even out over several segments.",
    "facts": [
     [
      "Hard nip",
      "holds and acts as a clamp"
     ],
     [
      "Soft nip",
      "opens under tension"
     ],
     [
      "Short filaments",
      "carry first in every segment"
     ],
     [
      "Chain",
      "all segments carry the same force"
     ],
     [
      "Steps",
      "click below to have them explained"
     ]
    ]
   },
   {
    "k": "Hard nips",
    "title": "Hard nips: chain reaction in the weakest segment",
    "text": "All nips hold. In every segment the shortest filaments carry first. The segment with the least favourable length distribution fails first: when a filament breaks there, the other segments spring back and stretch exactly this segment further. The filaments break there one after another while the other segments are hardly stretched.",
    "facts": [
     [
      "Nips",
      "hold until break"
     ],
     [
      "Break",
      "local, in one segment"
     ],
     [
      "Chain reaction",
      "the other segments spring back"
     ],
     [
      "Result",
      "low elongation at break and maximum force"
     ]
    ]
   },
   {
    "k": "Soft nips",
    "title": "Soft nips: opening and evening out",
    "text": "As soon as the force exceeds the holding force of a nip, it opens. The filament sections that were entangled in the nip and fixed by friction are straightened and from now on carry force themselves. The carrying length increases, the force rises more slowly for a moment. Once the nip is open, the filaments slip through and the neighbouring segments behave like one long segment. The length differences average out and the filaments carry almost at the same time.",
    "facts": [
     [
      "Nips",
      "open one after another, the weakest first"
     ],
     [
      "Nip sections",
      "are straightened and carry too"
     ],
     [
      "Evening out",
      "filaments slip over several segments"
     ],
     [
      "Result",
      "higher elongation at break and maximum force"
     ]
    ]
   },
   {
    "k": "Comparison",
    "title": "The more stable the nip, the lower the elongation",
    "text": "On the left the force-elongation curves of the same gauge length, on the right the mean of six random gauge lengths per nip stability. In the model, elongation at break and maximum force drop as soon as the nips no longer open below the breaking force. Use the slider to change the nip stability.",
    "facts": [
     [
      "Elongation at break",
      "here the elongation at maximum force"
     ],
     [
      "Transition",
      "what matters is whether nips open before the break"
     ],
     [
      "Recognisable by",
      "plateaus when opening, steps before the break"
     ],
     [
      "Technical term",
      "fibre bundle model with slip"
     ]
    ]
   }
  ]
 },
 "es": {
  "ui": {
   "eyebrow": "Knowledge Base · DTY · Conocimiento especializado · Hipótesis",
   "h1": "¿Nudos duros, menos alargamiento?",
   "lead": "Se estira una longitud de ensayo con varios nudos. Entre los nudos los filamentos no tienen todos la misma longitud. El modelo muestra qué pasa cuando los nudos aguantan y qué pasa cuando se abren bajo tracción.",
   "note": "Modelo simplificado para ilustrar la hipótesis: 12 filamentos, elástico-lineales hasta la rotura, 5 segmentos con longitudes de filamento desiguales, nudos con fuerza de retención que liberan longitud al abrirse. No se representan el rizado ni la geometría del nudo. Todos los valores son relativos, no son mediciones.",
   "pause": "⏸ Pausa",
   "play": "▶ Reproducir",
   "scenes": "Escenas",
   "stab": "Estabilidad del nudo",
   "again": "↻ Estirar de nuevo"
  },
  "cv": {
   "pull": "Tracción",
   "gauge": "Longitud de ensayo: 5 segmentos, 4 nudos",
   "knots": "Nudos",
   "hold": "aguanta",
   "opening": "se abre",
   "open": "abierto",
   "strain": "Alargamiento de la longitud de ensayo →",
   "force": "Fuerza",
   "shortest": "filamento más corto: carga primero",
   "longest": "más largo: aún flojo",
   "knot1": "Nudo: filamentos entrelazados,",
   "knot2": "cargan solo tras abrirse",
   "broken": "rotos",
   "knotsOpen": "nudos abiertos",
   "peak": "Fuerza máxima",
   "msgDone": "Hilo roto, en el segmento {seg}",
   "msgChain": "Reacción en cadena en el segmento {seg}: la carga salta",
   "msgOpening": "El nudo K{k} se abre: las secciones entrelazadas se estiran y también cargan",
   "msgBroken": "Segmento {seg}: los demás filamentos asumen la carga",
   "msgSlack": "Los filamentos aún están flojos, todavía sin carga",
   "msgOpen": "{n} nudos abiertos: también cargan las antiguas secciones de nudo, los filamentos se igualan",
   "msgHold": "Los nudos aguantan: en cada segmento cargan los filamentos más cortos",
   "curves": "Curvas fuerza-alargamiento (misma longitud de ensayo)",
   "soft": "nudos blandos",
   "hard": "nudos duros",
   "slider": "posición del regulador",
   "mean": "Media de 6 longitudes de ensayo",
   "rel": "relativo a nudos muy blandos",
   "stabAxis": "Estabilidad del nudo →",
   "easy": "se abre fácil",
   "computing": "calculando … {p} %",
   "elong": "Alargamiento a la rotura",
   "tenacity": "Fuerza máxima",
   "summary": "Con {k} % de estabilidad del nudo: alargamiento a la rotura {ru} %, fuerza máxima {rf} %",
   "disclaimer": "Tendencia del modelo, no son mediciones. Si el orden de magnitud y la transición son correctos lo debe mostrar un ensayo."
  },
  "steps": [
   {
    "a": "El nudo duro aguanta",
    "b": "actúa como pinza",
    "d": "Un nudo duro aguanta hasta la rotura. Sujeta los filamentos como una pinza: las diferencias de longitud quedan encerradas en su segmento."
   },
   {
    "a": "Los cortos cargan primero",
    "b": "los largos aún están flojos",
    "d": "En cada segmento se tensan primero los filamentos más cortos. Los más largos aún están flojos y no cargan nada."
   },
   {
    "a": "Reacción en cadena",
    "b": "en el segmento más débil",
    "d": "Si se rompe un filamento en el segmento más desfavorable, los demás segmentos se retraen y estiran aún más ese segmento. La escena Nudos duros lo muestra en vivo."
   },
   {
    "a": "El nudo blando se abre",
    "b": "se libera longitud, los filamentos se igualan",
    "d": "Un nudo blando se abre bajo tracción, libera su longitud y los filamentos se igualan a lo largo de varios segmentos. La escena Nudos blandos lo muestra en vivo."
   }
  ],
  "scenes": [
   {
    "k": "Hipótesis",
    "title": "Filamentos de distinta longitud entre nudos fijos",
    "text": "La longitud de ensayo contiene varios nudos. En cada segmento entre dos nudos los filamentos tienen longitudes distintas. Un nudo duro actúa como una pinza: las diferencias de longitud quedan encerradas en su segmento. Un nudo blando se abre bajo tracción, libera su longitud y deja que los filamentos se igualen a lo largo de varios segmentos.",
    "facts": [
     [
      "Nudo duro",
      "aguanta y actúa como pinza"
     ],
     [
      "Nudo blando",
      "se abre bajo tracción"
     ],
     [
      "Filamentos cortos",
      "cargan primero en cada segmento"
     ],
     [
      "Cadena",
      "todos los segmentos llevan la misma fuerza"
     ],
     [
      "Pasos",
      "haz clic abajo para ver la explicación"
     ]
    ]
   },
   {
    "k": "Nudos duros",
    "title": "Nudos duros: reacción en cadena en el segmento más débil",
    "text": "Todos los nudos aguantan. En cada segmento cargan primero los filamentos más cortos. El segmento con la distribución de longitudes más desfavorable falla primero: si allí se rompe un filamento, los demás segmentos se retraen y estiran aún más ese segmento. Los filamentos se rompen allí uno tras otro, mientras los demás segmentos apenas se estiran.",
    "facts": [
     [
      "Nudos",
      "aguantan hasta la rotura"
     ],
     [
      "Rotura",
      "local, en un segmento"
     ],
     [
      "Reacción en cadena",
      "los demás segmentos se retraen"
     ],
     [
      "Resultado",
      "bajo alargamiento a la rotura y baja fuerza máxima"
     ]
    ]
   },
   {
    "k": "Nudos blandos",
    "title": "Nudos blandos: abrirse e igualarse",
    "text": "En cuanto la fuerza supera la fuerza de retención de un nudo, este se abre. Las secciones de filamento entrelazadas en el nudo y fijadas por fricción se estiran y a partir de ahí cargan fuerza. La longitud portante aumenta y la fuerza sube un momento más despacio. Con el nudo abierto, los filamentos se deslizan y los segmentos vecinos se comportan como un solo segmento largo. Las diferencias de longitud se compensan y los filamentos cargan casi a la vez.",
    "facts": [
     [
      "Nudos",
      "se abren uno tras otro, el más débil primero"
     ],
     [
      "Secciones de nudo",
      "se estiran y también cargan"
     ],
     [
      "Igualación",
      "los filamentos se deslizan por varios segmentos"
     ],
     [
      "Resultado",
      "mayor alargamiento a la rotura y fuerza máxima"
     ]
    ]
   },
   {
    "k": "Comparación",
    "title": "Cuanto más estable el nudo, menor el alargamiento",
    "text": "A la izquierda, las curvas fuerza-alargamiento de la misma longitud de ensayo; a la derecha, la media de seis longitudes de ensayo aleatorias por estabilidad del nudo. En el modelo, el alargamiento a la rotura y la fuerza máxima bajan en cuanto los nudos dejan de abrirse por debajo de la fuerza de rotura. Con el regulador se cambia la estabilidad del nudo.",
    "facts": [
     [
      "Alargamiento a la rotura",
      "aquí, el alargamiento a la fuerza máxima"
     ],
     [
      "Transición",
      "lo decisivo es si los nudos se abren antes de la rotura"
     ],
     [
      "Se reconoce por",
      "mesetas al abrirse, escalones antes de la rotura"
     ],
     [
      "Término técnico",
      "modelo de haz de fibras con deslizamiento"
     ]
    ]
   }
  ]
 },
 "zh": {
  "ui": {
   "eyebrow": "知识库 · DTY · 专业知识 · 假设",
   "h1": "网络点越牢，伸长越低？",
   "lead": "拉伸一段含有多个网络点的试样。网络点之间的单丝长度并不完全相同。模型展示网络点保持不动时会发生什么，以及网络点在拉力下打开时会发生什么。",
   "note": "用于说明假设的简化模型：12 根单丝，断裂前线弹性，5 个单丝长度不等的段落，网络点有保持力，打开时释放束缚的长度。未模拟卷曲和网络点几何形状。所有数值均为相对值，不是测量值。",
   "pause": "⏸ 暂停",
   "play": "▶ 播放",
   "scenes": "场景",
   "stab": "网络点牢度",
   "again": "↻ 重新拉伸"
  },
  "cv": {
   "pull": "拉力",
   "gauge": "试样长度：5 段，4 个网络点",
   "knots": "网络点",
   "hold": "保持",
   "opening": "打开中",
   "open": "已打开",
   "strain": "试样伸长 →",
   "force": "力",
   "shortest": "最短单丝：最先受力",
   "longest": "最长单丝：仍松弛",
   "knot1": "网络点：交缠的单丝，",
   "knot2": "打开后才受力",
   "broken": "已断",
   "knotsOpen": "已打开的网络点",
   "peak": "最大拉力",
   "msgDone": "纱线断裂，位于第 {seg} 段",
   "msgChain": "第 {seg} 段发生连锁反应：负荷继续转移",
   "msgOpening": "网络点 K{k} 打开：交缠的部分被拉直并一起受力",
   "msgBroken": "第 {seg} 段：其余单丝承担负荷",
   "msgSlack": "单丝仍松弛，尚无负荷",
   "msgOpen": "{n} 个网络点已打开：原网络点部分也受力，单丝长度趋于均匀",
   "msgHold": "网络点保持：每段中最短的单丝受力",
   "curves": "力-伸长曲线（同一试样）",
   "soft": "软网络点",
   "hard": "硬网络点",
   "slider": "滑块位置",
   "mean": "6 个试样的平均值",
   "rel": "相对于很软的网络点",
   "stabAxis": "网络点牢度 →",
   "easy": "易打开",
   "computing": "计算中 … {p} %",
   "elong": "断裂伸长",
   "tenacity": "最大拉力",
   "summary": "网络点牢度 {k} % 时：断裂伸长 {ru} %，最大拉力 {rf} %",
   "disclaimer": "模型趋势，不是测量值。数量级和转变点是否正确需通过试验验证。"
  },
  "steps": [
   {
    "a": "硬网络点保持",
    "b": "起夹持作用",
    "d": "硬网络点一直保持到断裂。它像夹子一样夹住单丝：长度差异被锁在各自的段落中。"
   },
   {
    "a": "短丝先受力",
    "b": "长丝仍松弛",
    "d": "每段中最短的单丝最先被拉紧。较长的单丝仍松弛，不承受力。"
   },
   {
    "a": "连锁反应",
    "b": "发生在最弱的段落",
    "d": "如果在最不利的段落中一根单丝断裂，其他段落回弹，使这一段被进一步拉伸。场景“硬网络点”实时展示这一过程。"
   },
   {
    "a": "软网络点打开",
    "b": "释放长度，单丝趋于均匀",
    "d": "软网络点在拉力下打开，释放其束缚的长度，单丝在多个段落间均衡。场景“软网络点”实时展示这一过程。"
   }
  ],
  "scenes": [
   {
    "k": "假设",
    "title": "固定网络点之间长度不等的单丝",
    "text": "试样包含多个网络点。在两个网络点之间的每一段中，单丝长度各不相同。硬网络点像夹持点：长度差异被锁在各自的段落中。软网络点在拉力下打开，释放束缚的长度，让单丝在多个段落间均衡。",
    "facts": [
     [
      "硬网络点",
      "保持不动，起夹持作用"
     ],
     [
      "软网络点",
      "在拉力下打开"
     ],
     [
      "短单丝",
      "在每段中最先受力"
     ],
     [
      "串联",
      "所有段落承受相同的力"
     ],
     [
      "步骤",
      "点击下方查看说明"
     ]
    ]
   },
   {
    "k": "硬网络点",
    "title": "硬网络点：最弱段落中的连锁反应",
    "text": "所有网络点都保持。每段中最短的单丝最先受力。长度分布最不利的段落最先失效：那里一根单丝断裂后，其他段落回弹，使这一段被进一步拉伸。单丝在那里一根接一根断裂，而其他段落几乎没有伸长。",
    "facts": [
     [
      "网络点",
      "保持到断裂"
     ],
     [
      "断裂",
      "局部，发生在一个段落"
     ],
     [
      "连锁反应",
      "其他段落回弹"
     ],
     [
      "结果",
      "断裂伸长和最大拉力较低"
     ]
    ]
   },
   {
    "k": "软网络点",
    "title": "软网络点：打开与均衡",
    "text": "一旦拉力超过网络点的保持力，网络点就会打开。原本在网络点中交缠并被摩擦固定的单丝部分被拉直，从此也承受力。承力长度增加，拉力短暂上升变慢。网络点打开后，单丝滑移，相邻段落表现得像一个长段落。长度差异被平均，单丝几乎同时受力。",
    "facts": [
     [
      "网络点",
      "依次打开，最弱的先开"
     ],
     [
      "网络点部分",
      "被拉直并一起受力"
     ],
     [
      "均衡",
      "单丝在多个段落间滑移"
     ],
     [
      "结果",
      "断裂伸长和最大拉力较高"
     ]
    ]
   },
   {
    "k": "比较",
    "title": "网络点越牢，伸长越低",
    "text": "左侧是同一试样的力-伸长曲线，右侧是每种网络点牢度下六个随机试样的平均值。在模型中，一旦网络点在断裂力以下不再打开，断裂伸长和最大拉力就会下降。可用滑块改变网络点牢度。",
    "facts": [
     [
      "断裂伸长",
      "此处指最大拉力时的伸长"
     ],
     [
      "转变",
      "关键在于网络点是否在断裂前打开"
     ],
     [
      "识别特征",
      "打开时出现平台，断裂前出现台阶"
     ],
     [
      "术语",
      "带滑移的纤维束模型"
     ]
    ]
   }
  ]
 }
};
