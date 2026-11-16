# ui/widgets/help_texts_process_playground.py
"""Hilfetexte Process Playground (EN/DE/ES/ZH) fuer ui/widgets/multilang_help.py.

Spiegelt ui/screen_process_playground.py (1 Yarn and jet, 2 Start from,
3 Change, 4 What happens, Diagramm) und die Statistik in ui/dty_whatif.py.
Bei Aenderungen dort hier (alle 4 Sprachen) nachziehen.
"""


def B(name: str) -> str:
    return f"<b>[{name}]</b>"


TEXTS = {
    "en": {
        "window_title": "How does the Process Playground work?",
        "close": "Close",
        "tabs": [
            {"key": "tasks", "title": "How do I…?", "blocks": [
                ("p", "The Process Playground tells you what happens to the lab values of a <b>DTY</b> yarn when you "
                      "change <b>air pressure</b>, <b>overfeed</b> or <b>speed</b> - from our own trials of exactly "
                      "this yarn and jet. It says <i>more</i>, <i>fewer</i> or <i>about the same</i>, and how sure "
                      "that is. It does not predict exact values."),
                ("h", "Trying it"),
                ("task", "See what happens if I raise the air pressure",
                 ["Pick the yarn and jet on the left (<i>Search yarn or jet…</i> helps). Column <i>Varied</i> shows "
                  "what was changed in our trials: P = air pressure, OF = overfeed, S = speed.",
                  "Under <i>2 Start conditions</i> type your air pressure, overfeed and speed - or pick "
                  "<i>Take from a trial…</i> to use the settings of a trial we ran.",
                  "Under <i>3 Change</i> move the <i>Air pressure</i> slider or type a value.",
                  "Read the answer in <i>4 What happens</i>."],
                 f"{B('Back to start')} sets all sliders back to the start. F5 / {B('Reload')} loads the latest "
                 "trials. A red note under a start value means we never ran it with this yarn and jet - then "
                 "there is no statement."),
                ("task", "Start from a trial in Show Experiment",
                 ["In Show Experiment (DTY series), right-click the trial number in <i>Machine Data</i>.",
                  "Choose <i>Open V… in Process Playground…</i> - yarn, jet and start conditions are taken from "
                  "this trial."]),
                ("task", "Find settings that reach my goals",
                 ["Pick the <b>main goal</b> above the table, e.g. <i>Stability 1.0</i> + <i>higher</i>.",
                  "Set other goals in the column <i>Goal</i>: <i>higher</i>, <i>lower</i> or <i>keep</i> (about the "
                  "same), e.g. CV points/m = keep, Tension after jet = lower.",
                  f"Click {B('Find settings')}. The tab <i>Suggestions</i> lists up to 5 settings near what we really "
                  "ran - bold = changed, in brackets the change against your start.",
                  "Click a suggestion: the sliders move there and the table shows all lab values."],
                 "Every suggestion improves the main goal with a statement. For the other goals: <i>met</i> = shown "
                 "with a statement, <i>not proven</i> = no clear change, <i>can't tell</i> = too few trials, "
                 "<i>BROKEN</i> = goes the wrong way. The best suggestions break nothing and can check every goal; "
                 "if there is a way by turning only one knob, it is always among them."),
                ("task", "Understand a statement",
                 ["<i>clearly</i> = very sure (p &lt; 0.01), <i>probably</i> = sure (p &lt; 0.05), "
                  "<i>tendency</i> = weak hint (p &lt; 0.10).",
                  "<i>about the same</i> = the change is surely smaller than what repeating the same trial changes anyway.",
                  "<i>no clear effect</i> = neither clearly changed nor clearly equal; <i>unclear</i> = too few or too "
                  "scattered trials.",
                  "<i>Change</i> shows the estimated change with its 95 % range; <i>Based on</i> how many series "
                  "show the same direction."],
                 "More is not better or worse here - the colours only show how strong the statement is."),
                ("task", "See where a statement comes from",
                 ["Click a lab value in the table.",
                  "The chart below shows our trials against the setting (colour = series), the line the statement "
                  "uses and its 95 % band. Dashed = start, green = your new value.",
                  "Pick another setting under <i>Show against</i>."],
                 "The points are corrected for differences between series and for the other settings, so you see "
                 "only the effect of this one setting."),
                ("h", "Limits"),
                ("task", "Why a slider is greyed out or a value says 'no statement'",
                 ["A setting that was never varied with this yarn and jet cannot be judged - its slider is locked.",
                  "Sliders only go as far as we measured. Outside that range there is no statement.",
                  "A yellow note means this combination of settings was never run together: the statement combines "
                  "what we saw when the values were changed separately.",
                  "<i>only 1 series - check it</i>: everything we know comes from one series."],
                 "Only DTY. Lab values: points/m and CV (Itemat), stability 0.3 / 0.6 / 1.0 / 1.3, tension before "
                 "and after the jet (Machine Data). Reference samples are not used."),
            ]},
        ],
    },
    "de": {
        "window_title": "Wie funktioniert der Process Playground?",
        "close": "Schliessen",
        "tabs": [
            {"key": "tasks", "title": "Wie mache ich…?", "blocks": [
                ("p", "Der Process Playground sagt dir, was mit den Laborwerten eines <b>DTY</b>-Garns passiert, wenn "
                      "du <b>Luftdruck</b>, <b>Overfeed</b> oder <b>Speed</b> änderst - aus unseren eigenen Versuchen "
                      "mit genau diesem Garn und dieser Düse. Er sagt <i>mehr</i>, <i>weniger</i> oder <i>etwa "
                      "gleich</i> und wie sicher das ist. Genaue Werte sagt er nicht voraus."),
                ("h", "Ausprobieren"),
                ("task", "Sehen, was passiert, wenn ich den Luftdruck erhöhe",
                 ["Links Garn und Düse wählen (<i>Search yarn or jet…</i> hilft). Die Spalte <i>Varied</i> zeigt, "
                  "was in unseren Versuchen verändert wurde: P = Luftdruck, OF = Overfeed, S = Speed.",
                  "Unter <i>2 Start conditions</i> deinen Luftdruck, Overfeed und Speed eintippen - oder mit "
                  "<i>Take from a trial…</i> die Einstellungen eines gefahrenen Versuchs übernehmen.",
                  "Unter <i>3 Change</i> den Regler <i>Air pressure</i> verschieben oder einen Wert eintippen.",
                  "Die Antwort steht unter <i>4 What happens</i>."],
                 f"{B('Back to start')} setzt alle Regler auf den Start zurück. F5 / {B('Reload')} lädt die neuesten "
                 "Versuche. Ein roter Hinweis unter einem Startwert heisst: so haben wir mit diesem Garn und dieser "
                 "Düse nie gefahren - dann gibt es keine Aussage."),
                ("task", "Von einem Versuch in Show Experiment aus starten",
                 ["In Show Experiment (DTY-Serie) in <i>Machine Data</i> mit der rechten Maustaste auf die "
                  "Versuchsnummer klicken.",
                  "<i>Open V… in Process Playground…</i> wählen - Garn, Düse und Startbedingungen kommen von diesem "
                  "Versuch."]),
                ("task", "Einstellungen finden, die meine Ziele erreichen",
                 ["Über der Tabelle das <b>Hauptziel</b> wählen, z.&nbsp;B. <i>Stability 1.0</i> + <i>higher</i>.",
                  "Weitere Ziele in der Spalte <i>Goal</i> setzen: <i>higher</i>, <i>lower</i> oder <i>keep</i> (etwa "
                  "gleich), z.&nbsp;B. CV points/m = keep, Tension after jet = lower.",
                  f"{B('Find settings')} klicken. Der Reiter <i>Suggestions</i> zeigt bis zu 5 Einstellungen in der "
                  "Nähe dessen, was wir wirklich gefahren haben - fett = geändert, in Klammern die Änderung "
                  "gegenüber deinem Start.",
                  "Einen Vorschlag anklicken: die Regler springen dorthin und die Tabelle zeigt alle Laborwerte."],
                 "Jeder Vorschlag verbessert das Hauptziel mit einer Aussage. Für die anderen Ziele: <i>met</i> = mit "
                 "Aussage gezeigt, <i>not proven</i> = keine klare Änderung, <i>can't tell</i> = zu wenige "
                 "Versuche, <i>BROKEN</i> = geht in die falsche Richtung. Die besten Vorschläge verletzen nichts und "
                 "können jedes Ziel prüfen; gibt es einen Weg, bei dem man nur an einem Regler dreht, ist er immer "
                 "dabei."),
                ("task", "Eine Aussage verstehen",
                 ["<i>clearly</i> = sehr sicher (p &lt; 0.01), <i>probably</i> = sicher (p &lt; 0.05), "
                  "<i>tendency</i> = schwacher Hinweis (p &lt; 0.10).",
                  "<i>about the same</i> = die Änderung ist sicher kleiner als das, was eine Wiederholung desselben "
                  "Versuchs ohnehin ändert.",
                  "<i>no clear effect</i> = weder klar verändert noch klar gleich; <i>unclear</i> = zu wenige oder zu "
                  "stark streuende Versuche.",
                  "<i>Change</i> zeigt die geschätzte Änderung mit 95-%-Bereich, <i>Based on</i>, wie viele Serien "
                  "in dieselbe Richtung zeigen."],
                 "Mehr ist hier weder besser noch schlechter - die Farben zeigen nur, wie stark die Aussage ist."),
                ("task", "Sehen, woher eine Aussage kommt",
                 ["Einen Laborwert in der Tabelle anklicken.",
                  "Das Diagramm darunter zeigt unsere Versuche gegen die Einstellung (Farbe = Serie), die Linie, "
                  "auf der die Aussage beruht, und ihr 95-%-Band. Gestrichelt = Start, grün = dein neuer Wert.",
                  "Unter <i>Show against</i> eine andere Einstellung wählen."],
                 "Die Punkte sind um Unterschiede zwischen den Serien und um die anderen Einstellungen bereinigt - "
                 "du siehst nur den Effekt dieser einen Einstellung."),
                ("h", "Grenzen"),
                ("task", "Warum ein Regler grau ist oder ein Wert 'no statement' sagt",
                 ["Eine Einstellung, die mit diesem Garn und dieser Düse nie verändert wurde, lässt sich nicht "
                  "beurteilen - ihr Regler ist gesperrt.",
                  "Die Regler gehen nur so weit, wie wir gemessen haben. Ausserhalb gibt es keine Aussage.",
                  "Ein gelber Hinweis heisst: diese Kombination von Einstellungen wurde nie zusammen gefahren - die "
                  "Aussage kombiniert, was wir gesehen haben, als die Werte einzeln verändert wurden.",
                  "<i>only 1 series - check it</i>: alles, was wir wissen, stammt aus einer einzigen Serie."],
                 "Nur DTY. Laborwerte: Punkte/m und CV (Itemat), Stabilität 0.3 / 0.6 / 1.0 / 1.3, Spannung vor und "
                 "nach der Düse (Machine Data). Referenzmuster werden nicht verwendet."),
            ]},
        ],
    },
    "es": {
        "window_title": "¿Cómo funciona el Process Playground?",
        "close": "Cerrar",
        "tabs": [
            {"key": "tasks", "title": "¿Cómo…?", "blocks": [
                ("p", "El Process Playground te dice qué pasa con los valores de laboratorio de un hilo <b>DTY</b> si "
                      "cambias la <b>presión de aire</b>, el <b>overfeed</b> o la <b>velocidad</b> - a partir de "
                      "nuestros propios ensayos con exactamente este hilo y esta tobera. Dice <i>más</i>, <i>menos</i> "
                      "o <i>más o menos igual</i>, y con qué seguridad. No predice valores exactos."),
                ("h", "Probar"),
                ("task", "Ver qué pasa si subo la presión de aire",
                 ["Elige el hilo y la tobera a la izquierda (<i>Search yarn or jet…</i> ayuda). La columna "
                  "<i>Varied</i> muestra qué se cambió en nuestros ensayos: P = presión de aire, OF = overfeed, "
                  "S = velocidad.",
                  "En <i>2 Start conditions</i> escribe tu presión de aire, overfeed y velocidad - o usa "
                  "<i>Take from a trial…</i> para tomar los ajustes de un ensayo que hicimos.",
                  "En <i>3 Change</i> mueve el regulador <i>Air pressure</i> o escribe un valor.",
                  "La respuesta está en <i>4 What happens</i>."],
                 f"{B('Back to start')} vuelve todos los reguladores al inicio. F5 / {B('Reload')} carga los ensayos "
                 "más recientes. Una nota roja bajo un valor de inicio significa que nunca lo hicimos con este hilo "
                 "y esta tobera - entonces no hay afirmación."),
                ("task", "Empezar desde un ensayo en Show Experiment",
                 ["En Show Experiment (serie DTY), clic derecho en el número de ensayo en <i>Machine Data</i>.",
                  "Elige <i>Open V… in Process Playground…</i> - hilo, tobera y condiciones de inicio se toman de "
                  "este ensayo."]),
                ("task", "Encontrar ajustes que alcancen mis objetivos",
                 ["Elige el <b>objetivo principal</b> sobre la tabla, p.&nbsp;ej. <i>Stability 1.0</i> + <i>higher</i>.",
                  "Pon otros objetivos en la columna <i>Goal</i>: <i>higher</i>, <i>lower</i> o <i>keep</i> (más o "
                  "menos igual), p.&nbsp;ej. CV points/m = keep, Tension after jet = lower.",
                  f"Haz clic en {B('Find settings')}. La pestaña <i>Suggestions</i> muestra hasta 5 ajustes cerca de "
                  "lo que realmente hicimos - negrita = cambiado, entre paréntesis el cambio respecto a tu inicio.",
                  "Haz clic en una sugerencia: los reguladores van allí y la tabla muestra todos los valores."],
                 "Cada sugerencia mejora el objetivo principal con una afirmación. Para los otros objetivos: "
                 "<i>met</i> = mostrado con una afirmación, <i>not proven</i> = sin cambio claro, <i>can't tell</i> "
                 "= pocos ensayos, <i>BROKEN</i> = va en la dirección equivocada. Las mejores sugerencias no rompen "
                 "nada y pueden comprobar cada objetivo; si hay una forma girando un solo regulador, siempre está "
                 "entre ellas."),
                ("task", "Entender una afirmación",
                 ["<i>clearly</i> = muy seguro (p &lt; 0.01), <i>probably</i> = seguro (p &lt; 0.05), "
                  "<i>tendency</i> = indicio débil (p &lt; 0.10).",
                  "<i>about the same</i> = el cambio es con seguridad menor que lo que cambia repetir el mismo ensayo.",
                  "<i>no clear effect</i> = ni claramente distinto ni claramente igual; <i>unclear</i> = pocos ensayos "
                  "o demasiada dispersión.",
                  "<i>Change</i> muestra el cambio estimado con su rango del 95 %; <i>Based on</i>, cuántas series "
                  "van en la misma dirección."],
                 "Más no es mejor ni peor aquí - los colores solo muestran la fuerza de la afirmación."),
                ("task", "Ver de dónde viene una afirmación",
                 ["Haz clic en un valor de laboratorio de la tabla.",
                  "El gráfico de abajo muestra nuestros ensayos frente al ajuste (color = serie), la línea que usa la "
                  "afirmación y su banda del 95 %. Discontinua = inicio, verde = tu nuevo valor.",
                  "Elige otro ajuste en <i>Show against</i>."],
                 "Los puntos están corregidos por las diferencias entre series y por los otros ajustes, así ves solo "
                 "el efecto de este ajuste."),
                ("h", "Límites"),
                ("task", "Por qué un regulador está gris o un valor dice 'no statement'",
                 ["Un ajuste que nunca se varió con este hilo y esta tobera no se puede juzgar - su regulador está "
                  "bloqueado.",
                  "Los reguladores solo llegan hasta donde medimos. Fuera de ese rango no hay afirmación.",
                  "Una nota amarilla significa que esta combinación de ajustes nunca se hizo junta: la afirmación "
                  "combina lo que vimos cuando los valores se cambiaron por separado.",
                  "<i>only 1 series - check it</i>: todo lo que sabemos viene de una sola serie."],
                 "Solo DTY. Valores: puntos/m y CV (Itemat), estabilidad 0.3 / 0.6 / 1.0 / 1.3, tensión antes y "
                 "después de la tobera (Machine Data). No se usan muestras de referencia."),
            ]},
        ],
    },
    "zh": {
        "window_title": "Process Playground（工艺模拟）如何使用？",
        "close": "关闭",
        "tabs": [
            {"key": "tasks", "title": "我该如何……？", "blocks": [
                ("p", "Process Playground 告诉你：改变 <b>气压</b>、<b>超喂</b> 或 <b>速度</b> 时，一种 <b>DTY</b> "
                      "纱线的实验室数值会如何变化——依据是我们自己用正是这种纱线和喷嘴做过的试验。它给出 "
                      "<i>更多</i>、<i>更少</i> 或 <i>大致相同</i>，以及这一结论有多可靠。它不预测精确数值。"),
                ("h", "试一试"),
                ("task", "看看提高气压会发生什么",
                 ["在左侧选择纱线和喷嘴（<i>Search yarn or jet…</i> 可帮助查找）。<i>Varied</i> 列显示我们的试验中"
                  "改变过哪些参数：P = 气压，OF = 超喂，S = 速度。",
                  "在 <i>2 Start conditions</i> 下输入你的气压、超喂和速度——或选择 <i>Take from a trial…</i>，"
                  "采用我们做过的某个试验的设置。",
                  "在 <i>3 Change</i> 下拖动 <i>Air pressure</i> 滑块或输入数值。",
                  "在 <i>4 What happens</i> 中查看结果。"],
                 f"{B('Back to start')} 将所有滑块恢复到起始值。F5 / {B('Reload')} 加载最新试验。起始值下方的红色"
                 "提示表示：我们从未用这种纱线和喷嘴在该值下运行过——此时没有结论。"),
                ("task", "从 Show Experiment 中的某个试验开始",
                 ["在 Show Experiment（DTY 系列）的 <i>Machine Data</i> 中，右键单击试验编号。",
                  "选择 <i>Open V… in Process Playground…</i>——纱线、喷嘴和起始条件均取自该试验。"]),
                ("task", "找到能达到我目标的设置",
                 ["在表格上方选择 <b>主要目标</b>，例如 <i>Stability 1.0</i> + <i>higher</i>。",
                  "在 <i>Goal</i> 列设置其他目标：<i>higher</i>、<i>lower</i> 或 <i>keep</i>（大致不变），"
                  "例如 CV points/m = keep，Tension after jet = lower。",
                  f"单击 {B('Find settings')}。<i>Suggestions</i> 标签页列出最多 5 个接近我们实际运行过的设置——"
                  "粗体 = 已更改，括号内为相对于起始值的变化。",
                  "单击某条建议：滑块移到该位置，表格显示所有实验室数值。"],
                 "每条建议都能以有结论的方式改善主要目标。对其他目标：<i>met</i> = 有结论地达到，<i>not proven</i> "
                 "= 无明显变化，<i>can't tell</i> = 试验太少，<i>BROKEN</i> = 朝错误方向变化。最好的建议不破坏任何"
                 "目标，并能检验每个目标；如果只调一个旋钮就能实现，这种方案一定在其中。"),
                ("task", "理解一条结论",
                 ["<i>clearly</i> = 非常可靠（p &lt; 0.01），<i>probably</i> = 可靠（p &lt; 0.05），"
                  "<i>tendency</i> = 弱提示（p &lt; 0.10）。",
                  "<i>about the same</i> = 该变化肯定小于重复同一试验本身带来的变化。",
                  "<i>no clear effect</i> = 既不明显改变，也不明显相同；<i>unclear</i> = 试验太少或离散太大。",
                  "<i>Change</i> 显示估计的变化及其 95 % 范围；<i>Based on</i> 显示有多少系列指向同一方向。"],
                 "这里“更多”并不代表更好或更差——颜色只表示结论的强弱。"),
                ("task", "查看结论从何而来",
                 ["在表格中单击某个实验室数值。",
                  "下方图表显示我们的试验相对该设置的分布（颜色 = 系列）、结论所用的曲线及其 95 % 置信带。"
                  "虚线 = 起始值，绿色 = 你的新值。",
                  "在 <i>Show against</i> 下选择其他设置。"],
                 "这些点已校正系列之间的差异和其他设置的影响，因此你只看到这一个设置的作用。"),
                ("h", "限制"),
                ("task", "为什么滑块变灰或数值显示 'no statement'",
                 ["用这种纱线和喷嘴从未改变过的设置无法评估——其滑块被锁定。",
                  "滑块只能移动到我们测量过的范围。超出该范围没有结论。",
                  "黄色提示表示这组设置从未同时运行过：结论是把各数值分别改变时观察到的结果组合起来。",
                  "<i>only 1 series - check it</i>：我们所知的一切都来自同一个系列。"],
                 "仅限 DTY。实验室数值：网络点/m 和 CV（Itemat）、稳定性 0.3 / 0.6 / 1.0 / 1.3、喷嘴前/后张力"
                 "（Machine Data）。不使用参考样。"),
            ]},
        ],
    },
}
