# ui/widgets/help_texts_create_experiment.py
"""Hilfetexte Create Experiment (EN/DE/ES/ZH) fuer ui/widgets/multilang_help.py.

Spiegelt ui/screen_create_experiment.py: Tabs General / Material / Jet /
Machine / Lab Machines (gruener Punkt = Tab vollstaendig), vier Modi
(create / addseries / addtrials / addlabmachines, siehe _apply_mode_*),
Anzahl Versuche = Summe der Plaettchen aller Duesen-Zeilen, Material mit
Ends / Yarn Use / Spool-Picker und "+ Trial" (Halbfabrikat als Ply),
Experimentnummer automatisch aus Jahr-ProductGroup+OrderType-Nummer.
Bei Aenderungen dort hier (alle 3 Sprachen) und in
assets/images/help_create_experiment.svg nachziehen.
"""

SVG = "assets/images/help_create_experiment.svg"
SVG_W, SVG_H = 940, 372


def B(name: str) -> str:
    return f"<b>[{name}]</b>"


def M(name: str) -> str:
    return f"<b>{name}</b>"


TEXTS = {
    # ═══════════════════════════════ EN ═══════════════════════════════
    "en": {
        "window_title": "How does Create Experiment work?",
        "close": "Close",
        "tabs": [
            {"key": "tasks", "title": "How do I…?", "blocks": [
                ("p", "Create Experiment sets up new experiments, trial series, trials and lab machines. Work through "
                      "the tabs from left to right; a tab's dot turns green when it is complete. Numbers (1)–(4) "
                      "refer to the <i>Screen guide</i> tab, the four ways of opening this screen are explained in "
                      "the <i>Modes</i> tab."),
                ("h", "New experiment"),
                ("task", "Create a new experiment with its first trial series",
                 ["Click " + M("New Experiment") + " in the sidebar.",
                  "<i>General</i>: choose product group and order type (they form the experiment number), "
                  "optionally the experiment request and project; enter the series name, Backlog status and priority.",
                  "Fill in <i>Material</i>, <i>Jet</i>, <i>Machine</i> and, if needed, <i>Lab Machines</i> (see below).",
                  f"Click {B('Save')} (1)."],
                 "The experiment number (e.g. 2026-73-035) is assigned automatically. Choosing an experiment request "
                 "fills in matching fields."),
                ("h", "Filling in the tabs"),
                ("task", "Add a yarn as ply (Material)",
                 ["Select the yarn in the catalogue tree on the left (3) - or type part of its name into the search field above "
                  "the tree (searches all groups, Enter selects the first hit). Green spool behind a yarn = in stock "
                  "(click it to see where), crossed-out tube = nothing in stock.",
                  "Set <i>Ends</i> (how many times the yarn is used) and optionally <i>Yarn Use</i>.",
                  f"Click {B('+')}. Pick the spool from the yarn store if you like (optional).",
                  "The ply appears in the table (4) with its number."],
                 f"{B('+ Trial')} uses the output of an existing trial as input instead (e.g. a semi-finished yarn "
                 "from another machine)."),
                ("task", "Add jets (Jet)",
                 ["Choose housing and jet (the search field above the jet list searches name and development name in all "
                  "groups), enter the number of plates and the plate numbers, and the air pressure.",
                  f"Click {B('+')}. Repeat for further jets."],
                 "<b>Each plate becomes one trial.</b> Rows can be reordered with Up/Down or by dragging, and "
                 f"duplicated with {B('Copy selected')}."),
                ("task", "Set the machine settings (Machine)",
                 ["Choose the machine. Its fields appear; fill them in."]),
                ("task", "Plan lab tests (Lab Machines)",
                 ["Choose the lab machine and, if offered, the additional value (e.g. tensions for Itemat).",
                  f"Click {B('+')}."]),
                ("task", "Remove a row from a table",
                 ["Select the row and press the Delete key."]),
                ("h", "Extending an existing experiment"),
                ("task", "Add a trial series to an experiment",
                 ["Click " + M("Add Trial Series") + " in the sidebar (or " + B("Copy TrialSeries") + " in All "
                  "Experiments to start from an existing series).",
                  "Choose the existing experiment, enter the series name and fill in the tabs.",
                  f"Click {B('Save')}."]),
                ("task", "Add trials to a series",
                 ["In Show Experiment, click the <b>+</b> icon (add trial). This screen opens for that series.",
                  "Add the jets/plates for the new trials and check material and machine.",
                  f"Click {B('Save')}. The new trials are appended."]),
                ("task", "Add lab machines to existing trials",
                 ["Click " + M("Add Lab Machines") + " in the sidebar.",
                  "Choose experiment and series, tick the trials (or <i>Select all</i>), add the lab machines.",
                  f"Click {B('Save')}."]),
            ]},
            {"key": "screen", "title": "Screen guide", "blocks": [
                ("svg", SVG, {"tab_hint": "(dot turns green when the tab is complete)",
                              "hint_trials": "number of trials = plates of all jet rows added together",
                              "hint_delete": "select a row and press Delete to remove it"}, SVG_W, SVG_H),
                ("areas", [
                    ("(1) Title and Save", "What you are creating, and Save. In the add modes there is also "
                                           "<i>← Back to Experiment</i>."),
                    ("(2) Tabs", "General, Material, Jet, Machine, Lab Machines. Green dot = complete."),
                    ("(3) Yarn catalogue", "Yarns grouped by type; select one, set Ends/Yarn Use, then <b>+</b>. "
                                           "<b>+ Trial</b> uses an existing trial as input."),
                    ("(4) Ply table", "The plies of the series: material, ply number, yarn use and spool."),
                ]),
            ]},
            {"key": "modes", "title": "Modes", "blocks": [
                ("table", ["Mode", "Opened via", "What it does"], [
                    ["New Experiment", M("New Experiment") + " in the sidebar",
                     "New experiment with its first trial series and trials."],
                    ["Add Trial Series", M("Add Trial Series") + " in the sidebar, " + B("Copy TrialSeries") +
                     " in All Experiments", "New series in an existing experiment."],
                    ["Add Trials", "<b>+</b> icon in Show Experiment", "More trials in an existing series."],
                    ["Add Lab Machines", M("Add Lab Machines") + " in the sidebar",
                     "Lab machines for selected trials of an existing series."],
                ]),
                ("note", "<b>How many trials?</b> Every plate of every jet row becomes one trial. Two jets with "
                         "3 plates each give 6 trials."),
            ]},
        ],
    },

    # ═══════════════════════════════ DE ═══════════════════════════════
    "de": {
        "window_title": "Wie funktioniert Create Experiment?",
        "close": "Schliessen",
        "tabs": [
            {"key": "tasks", "title": "Wie mache ich…?", "blocks": [
                ("p", "Create Experiment legt neue Experimente, Versuchsserien, Versuche und Labormaschinen an. Die Tabs "
                      "von links nach rechts ausfüllen; der Punkt eines Tabs wird grün, sobald er vollständig ist. Die "
                      "Nummern (1)–(4) verweisen auf den Tab <i>Bildschirm</i>, die vier Arten, diesen Bildschirm zu "
                      "öffnen, erklärt der Tab <i>Modi</i>."),
                ("h", "Neues Experiment"),
                ("task", "Ein neues Experiment mit seiner ersten Versuchsserie anlegen",
                 ["In der Sidebar auf " + M("New Experiment") + " klicken.",
                  "<i>General</i>: Product Group und Order Type wählen (daraus entsteht die Experimentnummer), "
                  "optional Experiment Request und Projekt; Serienname, Backlog-Status und Priorität eingeben.",
                  "<i>Material</i>, <i>Jet</i>, <i>Machine</i> und bei Bedarf <i>Lab Machines</i> ausfüllen (siehe unten).",
                  f"Auf {B('Save')} (1) klicken."],
                 "Die Experimentnummer (z.&nbsp;B. 2026-73-035) wird automatisch vergeben. Wird ein Experiment "
                 "Request gewählt, füllt TrippleT passende Felder vor."),
                ("h", "Die Tabs ausfüllen"),
                ("task", "Ein Garn als Ply hinzufügen (Material)",
                 ["Das Garn links im Katalogbaum (3) auswählen - oder einen Teil des Namens ins Suchfeld über dem Baum tippen "
                  "(sucht in allen Gruppen, Enter wählt den ersten Treffer). Grüne Spule hinter dem Garn = am Lager "
                  "(anklicken zeigt, wo), durchgestrichene Hülse = nichts am Lager.",
                  "<i>Ends</i> (wie oft das Garn verwendet wird) und optional <i>Yarn Use</i> einstellen.",
                  f"Auf {B('+')} klicken. Auf Wunsch die Spule aus dem Garnlager wählen (optional).",
                  "Das Ply erscheint mit seiner Nummer in der Tabelle (4)."],
                 f"{B('+ Trial')} verwendet stattdessen das Ergebnis eines bestehenden Versuchs als Input (z.&nbsp;B. ein "
                 "Halbfabrikat von einer anderen Maschine)."),
                ("task", "Düsen hinzufügen (Jet)",
                 ["Gehäuse (Housing) und Düse (Jet) wählen (das Suchfeld über der Düsenliste sucht Name und Entwicklungsname "
                  "in allen Gruppen), Anzahl Plättchen und die Plättchennummern sowie den Luftdruck eingeben.",
                  f"Auf {B('+')} klicken. Für weitere Düsen wiederholen."],
                 "<b>Jedes Plättchen ergibt einen Versuch.</b> Zeilen lassen sich mit Up/Down oder per Ziehen umordnen "
                 f"und mit {B('Copy selected')} duplizieren."),
                ("task", "Die Maschineneinstellungen setzen (Machine)",
                 ["Die Maschine wählen. Ihre Felder erscheinen; ausfüllen."]),
                ("task", "Labortests planen (Lab Machines)",
                 ["Die Labormaschine wählen und, falls angeboten, den Zusatzwert (z.&nbsp;B. Spannungen bei Itemat).",
                  f"Auf {B('+')} klicken."]),
                ("task", "Eine Zeile aus einer Tabelle entfernen",
                 ["Die Zeile auswählen und die Entf-Taste drücken."]),
                ("h", "Ein bestehendes Experiment erweitern"),
                ("task", "Eine Versuchsserie zu einem Experiment hinzufügen",
                 ["In der Sidebar auf " + M("Add Trial Series") + " klicken (oder in All Experiments auf "
                  + B("Copy TrialSeries") + ", um von einer bestehenden Serie auszugehen).",
                  "Das bestehende Experiment wählen, den Seriennamen eingeben und die Tabs ausfüllen.",
                  f"Auf {B('Save')} klicken."]),
                ("task", "Versuche zu einer Serie hinzufügen",
                 ["In Show Experiment auf das <b>+</b>-Symbol (Versuch hinzufügen) klicken. Dieser Bildschirm öffnet sich für die Serie.",
                  "Die Düsen/Plättchen für die neuen Versuche hinzufügen, Material und Maschine prüfen.",
                  f"Auf {B('Save')} klicken. Die neuen Versuche werden angehängt."]),
                ("task", "Labormaschinen zu bestehenden Versuchen hinzufügen",
                 ["In der Sidebar auf " + M("Add Lab Machines") + " klicken.",
                  "Experiment und Serie wählen, die Versuche abhaken (oder <i>Select all</i>), Labormaschinen hinzufügen.",
                  f"Auf {B('Save')} klicken."]),
            ]},
            {"key": "screen", "title": "Bildschirm", "blocks": [
                ("svg", SVG, {"tab_hint": "(Punkt wird grün, sobald der Tab vollständig ist)",
                              "hint_trials": "Anzahl Versuche = Plättchen aller Düsen-Zeilen zusammen",
                              "hint_delete": "Zeile auswählen und Entf drücken, um sie zu entfernen"}, SVG_W, SVG_H),
                ("areas", [
                    ("(1) Titel und Save", "Was angelegt wird, und Save. In den Erweiterungs-Modi zusätzlich "
                                           "<i>← Back to Experiment</i>."),
                    ("(2) Tabs", "General, Material, Jet, Machine, Lab Machines. Grüner Punkt = vollständig."),
                    ("(3) Garnkatalog", "Garne nach Typ gruppiert; eines wählen, Ends/Yarn Use einstellen, dann <b>+</b>. "
                                        "<b>+ Trial</b> verwendet einen bestehenden Versuch als Input."),
                    ("(4) Ply-Tabelle", "Die Plies der Serie: Material, Ply-Nummer, Yarn Use und Spule."),
                ]),
            ]},
            {"key": "modes", "title": "Modi", "blocks": [
                ("table", ["Modus", "Geöffnet über", "Was er macht"], [
                    ["New Experiment", M("New Experiment") + " in der Sidebar",
                     "Neues Experiment mit erster Versuchsserie und Versuchen."],
                    ["Add Trial Series", M("Add Trial Series") + " in der Sidebar, " + B("Copy TrialSeries") +
                     " in All Experiments", "Neue Serie in einem bestehenden Experiment."],
                    ["Add Trials", "<b>+</b>-Symbol in Show Experiment", "Weitere Versuche in einer bestehenden Serie."],
                    ["Add Lab Machines", M("Add Lab Machines") + " in der Sidebar",
                     "Labormaschinen für ausgewählte Versuche einer bestehenden Serie."],
                ]),
                ("note", "<b>Wie viele Versuche?</b> Jedes Plättchen jeder Düsen-Zeile ergibt einen Versuch. Zwei Düsen "
                         "mit je 3 Plättchen ergeben 6 Versuche."),
            ]},
        ],
    },

    # ═══════════════════════════════ ES ═══════════════════════════════
    "es": {
        "window_title": "¿Cómo funciona Create Experiment?",
        "close": "Cerrar",
        "tabs": [
            {"key": "tasks", "title": "¿Cómo hago…?", "blocks": [
                ("p", "Create Experiment crea experimentos, series de ensayos, ensayos y máquinas de laboratorio nuevos. "
                      "Rellena las pestañas de izquierda a derecha; el punto de una pestaña se pone verde cuando está "
                      "completa. Los números (1)–(4) se refieren a la pestaña <i>Pantalla</i>; las cuatro formas de "
                      "abrir esta pantalla se explican en la pestaña <i>Modos</i>."),
                ("h", "Experimento nuevo"),
                ("task", "Crear un experimento nuevo con su primera serie de ensayos",
                 ["Haz clic en " + M("New Experiment") + " en la barra lateral.",
                  "<i>General</i>: elige product group y order type (forman el número de experimento), opcionalmente "
                  "la solicitud de experimento y el proyecto; introduce el nombre de la serie, el estado en el Backlog "
                  "y la prioridad.",
                  "Rellena <i>Material</i>, <i>Jet</i>, <i>Machine</i> y, si hace falta, <i>Lab Machines</i> (ver abajo).",
                  f"Haz clic en {B('Save')} (1)."],
                 "El número de experimento (p.&nbsp;ej. 2026-73-035) se asigna automáticamente. Al elegir una "
                 "solicitud de experimento se rellenan los campos correspondientes."),
                ("h", "Rellenar las pestañas"),
                ("task", "Añadir un hilo como ply (Material)",
                 ["Selecciona el hilo en el árbol del catálogo a la izquierda (3) - o escribe parte de su nombre en el campo de "
                  "búsqueda sobre el árbol (busca en todos los grupos, Enter elige el primer resultado). Bobina verde "
                  "detrás del hilo = en stock (clic para ver dónde), tubo tachado = nada en stock.",
                  "Ajusta <i>Ends</i> (cuántas veces se usa el hilo) y opcionalmente <i>Yarn Use</i>.",
                  f"Haz clic en {B('+')}. Si quieres, elige la bobina del almacén de hilo (opcional).",
                  "El ply aparece con su número en la tabla (4)."],
                 f"{B('+ Trial')} usa en su lugar el resultado de un ensayo existente como entrada (p.&nbsp;ej. un "
                 "semielaborado de otra máquina)."),
                ("task", "Añadir toberas (Jet)",
                 ["Elige carcasa (Housing) y tobera (Jet) (el campo de búsqueda sobre la lista busca nombre y nombre de "
                  "desarrollo en todos los grupos), introduce el número de plaquitas y sus números, y la presión de aire.",
                  f"Haz clic en {B('+')}. Repite para más toberas."],
                 "<b>Cada plaquita da un ensayo.</b> Las filas se reordenan con Up/Down o arrastrando, y se duplican "
                 f"con {B('Copy selected')}."),
                ("task", "Definir los ajustes de máquina (Machine)",
                 ["Elige la máquina. Aparecen sus campos; rellénalos."]),
                ("task", "Planificar ensayos de laboratorio (Lab Machines)",
                 ["Elige la máquina de laboratorio y, si se ofrece, el valor adicional (p.&nbsp;ej. tensiones en Itemat).",
                  f"Haz clic en {B('+')}."]),
                ("task", "Quitar una fila de una tabla",
                 ["Selecciona la fila y pulsa la tecla Supr."]),
                ("h", "Ampliar un experimento existente"),
                ("task", "Añadir una serie de ensayos a un experimento",
                 ["Haz clic en " + M("Add Trial Series") + " en la barra lateral (o en " + B("Copy TrialSeries") +
                  " en All Experiments para partir de una serie existente).",
                  "Elige el experimento existente, introduce el nombre de la serie y rellena las pestañas.",
                  f"Haz clic en {B('Save')}."]),
                ("task", "Añadir ensayos a una serie",
                 ["En Show Experiment, haz clic en el icono <b>+</b> (añadir ensayo). Esta pantalla se abre para esa serie.",
                  "Añade las toberas/plaquitas de los ensayos nuevos y revisa material y máquina.",
                  f"Haz clic en {B('Save')}. Los ensayos nuevos se añaden al final."]),
                ("task", "Añadir máquinas de laboratorio a ensayos existentes",
                 ["Haz clic en " + M("Add Lab Machines") + " en la barra lateral.",
                  "Elige experimento y serie, marca los ensayos (o <i>Select all</i>) y añade las máquinas de laboratorio.",
                  f"Haz clic en {B('Save')}."]),
            ]},
            {"key": "screen", "title": "Pantalla", "blocks": [
                ("svg", SVG, {"tab_hint": "(el punto se pone verde cuando la pestaña está completa)",
                              "hint_trials": "número de ensayos = plaquitas de todas las filas de toberas sumadas",
                              "hint_delete": "selecciona una fila y pulsa Supr para quitarla"}, SVG_W, SVG_H),
                ("areas", [
                    ("(1) Título y Save", "Qué se está creando, y Save. En los modos de ampliación también "
                                          "<i>← Back to Experiment</i>."),
                    ("(2) Pestañas", "General, Material, Jet, Machine, Lab Machines. Punto verde = completa."),
                    ("(3) Catálogo de hilos", "Hilos agrupados por tipo; elige uno, ajusta Ends/Yarn Use y luego <b>+</b>. "
                                              "<b>+ Trial</b> usa un ensayo existente como entrada."),
                    ("(4) Tabla de plies", "Los plies de la serie: material, número de ply, yarn use y bobina."),
                ]),
            ]},
            {"key": "modes", "title": "Modos", "blocks": [
                ("table", ["Modo", "Se abre con", "Qué hace"], [
                    ["New Experiment", M("New Experiment") + " en la barra lateral",
                     "Experimento nuevo con su primera serie y sus ensayos."],
                    ["Add Trial Series", M("Add Trial Series") + " en la barra lateral, " + B("Copy TrialSeries") +
                     " en All Experiments", "Serie nueva en un experimento existente."],
                    ["Add Trials", "Icono <b>+</b> en Show Experiment", "Más ensayos en una serie existente."],
                    ["Add Lab Machines", M("Add Lab Machines") + " en la barra lateral",
                     "Máquinas de laboratorio para ensayos seleccionados de una serie existente."],
                ]),
                ("note", "<b>¿Cuántos ensayos?</b> Cada plaquita de cada fila de toberas da un ensayo. Dos toberas con "
                         "3 plaquitas cada una dan 6 ensayos."),
            ]},
        ],
    },

    # ═══════════════════════════════ ZH ═══════════════════════════════
    "zh": {
        "window_title": "Create Experiment 如何使用？",
        "close": "关闭",
        "tabs": [
            {"key": "tasks", "title": "我该如何……？", "blocks": [
                ("p", "Create Experiment 用于新建实验、试验系列、试验和实验室设备。请从左到右依次填写"
                      "各选项卡；选项卡填写完整后，其圆点变为绿色。编号 (1)–(4) 对应 <i>界面说明</i> 选项卡，"
                      "打开本界面的四种方式见 <i>模式</i> 选项卡。"),
                ("h", "新建实验"),
                ("task", "新建实验及其第一个试验系列",
                 ["在侧边栏点击 " + M("New Experiment") + "。",
                  "<i>General</i>：选择 product group 和 order type（二者构成实验编号），"
                  "可选实验申请和项目；输入系列名称、Backlog 状态和优先级。",
                  "填写 <i>Material</i>、<i>Jet</i>、<i>Machine</i>，如有需要还有 <i>Lab Machines</i>（见下文）。",
                  f"点击 {B('Save')} (1)。"],
                 "实验编号（例如 2026-73-035）自动分配。选择实验申请后，"
                 "相应字段会自动填写。"),
                ("h", "填写选项卡"),
                ("task", "添加纱线作为股 (Material)",
                 ["在左侧的目录树 (3) 中选择纱线，或在目录树上方的搜索框中输入其名称的一部分"
                  "（搜索所有分组，按 Enter 选择第一个结果）。纱线后面的绿色筒子 = 有库存"
                  "（点击查看存放位置），带删除线的纸管 = 无库存。",
                  "设置 <i>Ends</i>（纱线使用的根数），可选设置 <i>Yarn Use</i>。",
                  f"点击 {B('+')}。如有需要，可从纱线库中选择筒子（可选）。",
                  "该股连同编号出现在表格 (4) 中。"],
                 f"{B('+ Trial')} 则把一个已有试验的产出作为输入（例如来自另一台机器的"
                 "半成品纱线）。"),
                ("task", "添加喷嘴 (Jet)",
                 ["选择喷嘴座 (Housing) 和喷嘴（喷嘴列表上方的搜索框在所有分组中搜索名称和开发名称），"
                  "输入喷嘴板数量、喷嘴板编号以及气压。",
                  f"点击 {B('+')}。如需更多喷嘴，重复此步骤。"],
                 "<b>每个喷嘴板对应一个试验。</b>可用 Up/Down 或拖动调整行的顺序，"
                 f"并可用 {B('Copy selected')} 复制。"),
                ("task", "设置机器参数 (Machine)",
                 ["选择机器。其字段随即出现，请逐一填写。"]),
                ("task", "规划实验室测试 (Lab Machines)",
                 ["选择实验室设备，如有提供，再选择附加值（例如 Itemat 的张力）。",
                  f"点击 {B('+')}。"]),
                ("task", "从表格中删除一行",
                 ["选中该行并按 Delete 键。"]),
                ("h", "扩展已有实验"),
                ("task", "向实验添加试验系列",
                 ["在侧边栏点击 " + M("Add Trial Series") + "（或在 All Experiments 中点击 " + B("Copy TrialSeries") +
                  "，以已有系列为基础）。",
                  "选择已有实验，输入系列名称并填写各选项卡。",
                  f"点击 {B('Save')}。"]),
                ("task", "向系列添加试验",
                 ["在 Show Experiment 中点击 <b>+</b> 图标（添加试验）。本界面会针对该系列打开。",
                  "为新试验添加喷嘴/喷嘴板，并检查材料和机器。",
                  f"点击 {B('Save')}。新试验会追加在末尾。"]),
                ("task", "为已有试验添加实验室设备",
                 ["在侧边栏点击 " + M("Add Lab Machines") + "。",
                  "选择实验和系列，勾选试验（或 <i>Select all</i>），添加实验室设备。",
                  f"点击 {B('Save')}。"]),
            ]},
            {"key": "screen", "title": "界面说明", "blocks": [
                ("svg", SVG, {"tab_hint": "（选项卡填写完整后圆点变绿）",
                              "hint_trials": "试验数量 = 所有喷嘴行的喷嘴板数之和",
                              "hint_delete": "选中一行并按 Delete 删除"}, SVG_W, SVG_H),
                ("areas", [
                    ("(1) 标题和 Save", "正在创建的内容，以及 Save。在添加模式下还有 "
                                        "<i>← Back to Experiment</i>。"),
                    ("(2) 选项卡", "General、Material、Jet、Machine、Lab Machines。绿点 = 已完整。"),
                    ("(3) 纱线目录", "纱线按类型分组；选择一种，设置 Ends/Yarn Use，然后点 <b>+</b>。"
                                     "<b>+ Trial</b> 将已有试验作为输入。"),
                    ("(4) 股表格", "该系列的各股：材料、股编号、yarn use 和筒子。"),
                ]),
            ]},
            {"key": "modes", "title": "模式", "blocks": [
                ("table", ["模式", "打开方式", "作用"], [
                    ["New Experiment", "侧边栏中的 " + M("New Experiment"),
                     "新实验及其第一个试验系列和试验。"],
                    ["Add Trial Series", "侧边栏中的 " + M("Add Trial Series") + "，All Experiments 中的 " +
                     B("Copy TrialSeries"), "在已有实验中新建系列。"],
                    ["Add Trials", "Show Experiment 中的 <b>+</b> 图标", "在已有系列中添加更多试验。"],
                    ["Add Lab Machines", "侧边栏中的 " + M("Add Lab Machines"),
                     "为已有系列中选定的试验添加实验室设备。"],
                ]),
                ("note", "<b>有多少个试验？</b>每个喷嘴行的每个喷嘴板对应一个试验。两个喷嘴"
                         "各 3 个喷嘴板，共 6 个试验。"),
            ]},
        ],
    },
}
