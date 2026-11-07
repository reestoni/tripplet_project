# ui/widgets/whats_new_texts.py
"""What's new (EN/DE/ES) - Sidebar -> Account -> "What's new" and once
after login (ui/whats_new.py): versions listed on the left, the new features
of the chosen version on the right as cards.

RELEASES, newest first. Each entry has
    "version": "current" -> the version being worked on = app_meta.APP_VERSION
               "4.6.3"   -> a compiled version (fixed)
    "date":    "" while current, the compile date ("2026-10-15") once fixed
    "texts":   {lang: [blocks]}
New features go into the "current" entry right away (all three languages).

Blocks:
    ("h", "Section")                                      heading (screen/area)
    ("feature", title, text, where, sketch)               one card; sketch =
        file name in assets/images/whats_new/ (tools/gen_whats_new_svgs.py)
        or None. `where` = how to get there, e.g. "Show Experiment → + Ref".

Compiled before the user says so: the exe shows the "current" entry with its
own build date instead of "in progress".

When the user announces a compile ("ich habe kompiliert"): write the actual
version (app_meta.APP_VERSION at that moment) and the date into the current
entry. The user then raises APP_VERSION for the test environment; the next
new feature starts a new "current" entry at the top (an empty one must not
exist). No version check - when to compile stays with the user.

Same block structure in all three languages. Button/menu names stay English.
"""

RELEASES = [
    {
        "version": "current",
        "date": "",
        "texts": {
            # ═══════════════════════════════ EN ═══════════════════════════════
            "en": [
                ("h", "Smart Chart"),
                ("feature", "How many different jets? - Count (distinct)",
                 "A Card can now count how many <b>different</b> values a field has - e.g. how many different jets, "
                 "yarns or machines were run, always within your filters, slicers and clicks. Choose the "
                 "aggregation <b>Count (distinct)</b> and drag the field (e.g. <i>Jet</i>) into <b>Value</b>. "
                 "Empty values do not count. It works in Columns, Matrix and Pie, too - e.g. different jets per year.",
                 "Smart Chart → Card → Aggregation <b>Count (distinct)</b>", "wn_distinct_count.svg"),
                ("feature", "Which jets are they? - one row per value",
                 "A Table can now list each jet (or yarn, machine …) once instead of every trial: tick <b>One row "
                 "per value</b>. Next to the name you see how many trials and series it was used in; a number field "
                 "such as FP/m shows its average. With the same filters, the list has exactly as many lines as "
                 "the Card with <b>Count (distinct)</b> counts. Click a heading to sort.",
                 "Smart Chart → Table → Build → <b>One row per value</b>", "wn_value_table.svg"),
                ("h", "Create Experiment"),
                ("feature", "Find yarns and jets by typing",
                 "The <b>Material</b> and <b>Jet</b> tabs now have a search field above the list. Type part of the "
                 "name (e.g. <i>pa6 44</i>) - all groups are searched at once, only matching entries stay visible. "
                 "For jets the development name is searched, too. <b>Enter</b> selects the first hit, <b>Esc</b> "
                 "clears the search. Behind every yarn you also see the spool symbol from Show Experiment: green "
                 "spool = in stock (click it to see where the spools are), crossed-out tube = nothing in stock.",
                 "New Experiment → <b>Material</b> / <b>Jet</b> → search field", "wn_create_search.svg"),
                ("h", "Onboarding"),
                ("feature", "Onboarding - our work as short animations",
                 "New entry <b>Onboarding</b> below <b>Help (F1)</b>: short animated introductions to our work, "
                 "full screen. The first topic shows how a DTY yarn is intermingled - the path through the machine "
                 "with the overfeed between feed roll 2 and 2.x (click any position to have it explained), what "
                 "happens in the jet, and the nips. Each topic has tabs like the rest of TrippleT. Try the "
                 "<b>Overfeed</b> and <b>Air pressure</b> sliders. Switch the language with the flags - now also "
                 "in Chinese. Second topic: <b>ATY air texturing</b> - overfeed of core and effect, the texturing jet, "
                 "loops and what the settings do. Under <b>Spinning</b>: <b>Filament yarn spinning</b> - from chips to POY "
                 "and FDY, and where the Heberlein jets sit. Also under <b>Spinning</b>: <b>BCF carpet yarn</b> - spinning, "
                 "drawing, hot-air texturing and interlacing in one step, incl. tricolour mixing, and <b>Air-jet spinning</b> (staple fibres) - from the bale to the yarn, vortex around the hollow spindle. Under <b>Splicing</b>: <b>Air splicing "
                 "of filament yarns</b> - joining two ends knot-free; click a step to jump to it. Under <b>Threading</b>: "
                 "<b>Lufan suction gun</b> - threading up with the machine running, injector principle, air consumption. Under <b>DTY</b> → <b>Specialist knowledge</b>: <b>Cotton-like DTY</b> (seven ways to a spun-yarn look, click any machine position) and <b>Hard nips, less elongation?</b> (a hypothesis with a live tensile-test model). In the DTY machine you can now enter the <b>FR 2</b> speed and the <b>draw ratio</b>: FR 1 and FR 2.x are shown in m/min. New scene <b>Evenness</b> in the DTY topic: the same number of nips is not enough, they have to be evenly spread (spread of the distances, longest open section). The DTY topic now ends with a <b>Quiz</b> tab: 13 questions, each with a link back to the matching scene - with 80 % correct the topic is passed and gets a tick in the list. New folder <b>Lab</b> with <b>Nip measurement with the ITEMAT</b>: set-up (click the stations), mechanical and optical sensor, what a wrong threshold does, stability test under load and evaluation, plus <b>Count, tenacity and elongation (STATIMAT DS)</b>: count by weighing, CRE tensile test comparing POY, FDY and DTY, statistics per package, and <b>Crimp and shrinkage (TEXTURMAT ME)</b>: from the hank via heat treatment to the five load steps (clickable) and the key figures crimp contraction, modulus, stability and shrinkage, and <b>Testing nips with the RAPID 600 V</b>: the needle method counts the nips in the running yarn and separates good from weak nips, with a slider for the trigger force. More topics will follow.",
                 "Sidebar → <b>Onboarding</b>", "wn_onboarding.svg"),
            ],
            # ═══════════════════════════════ DE ═══════════════════════════════
            "de": [
                ("h", "Smart Chart"),
                ("feature", "Wie viele verschiedene Jets? - Count (distinct)",
                 "Eine Card zählt jetzt, wie viele <b>verschiedene</b> Werte ein Feld hat - z.&nbsp;B. wie viele "
                 "verschiedene Jets, Garne oder Maschinen gefahren wurden, immer innerhalb der Filter, Slicer und "
                 "Klicks. Als Aggregation <b>Count (distinct)</b> wählen und das Feld (z.&nbsp;B. <i>Jet</i>) in "
                 "<b>Value</b> ziehen. Leere Werte zählen nicht. Geht auch in Columns, Matrix und Pie - z.&nbsp;B. "
                 "verschiedene Jets pro Jahr.",
                 "Smart Chart → Card → Aggregation <b>Count (distinct)</b>", "wn_distinct_count.svg"),
                ("feature", "Welche Jets sind es? - eine Zeile pro Wert",
                 "Eine Table listet jetzt jeden Jet (oder Garn, Maschine …) einmal statt jeden Versuch: "
                 "<b>One row per value</b> ankreuzen. Neben dem Namen steht, in wie vielen Versuchen und Serien er "
                 "vorkam; ein Zahlenfeld wie FP/m zeigt seinen Mittelwert. Bei gleichen Filtern hat die Liste genau "
                 "so viele Zeilen, wie die Card mit <b>Count (distinct)</b> zählt. Klick auf eine Überschrift "
                 "sortiert.",
                 "Smart Chart → Table → Build → <b>One row per value</b>", "wn_value_table.svg"),
                ("h", "Create Experiment"),
                ("feature", "Garne und Jets durch Tippen finden",
                 "Die Reiter <b>Material</b> und <b>Jet</b> haben jetzt ein Suchfeld über der Liste. Einen Teil des "
                 "Namens tippen (z.&nbsp;B. <i>pa6 44</i>) - es wird in allen Gruppen gleichzeitig gesucht, nur "
                 "Treffer bleiben sichtbar. Bei Jets wird auch der Entwicklungsname durchsucht. <b>Enter</b> wählt "
                 "den ersten Treffer, <b>Esc</b> leert die Suche. Hinter jedem Garn steht zudem das Spulen-Symbol "
                 "aus Show Experiment: grüne Spule = am Lager (anklicken zeigt, wo die Spulen liegen), "
                 "durchgestrichene Hülse = nichts am Lager.",
                 "New Experiment → <b>Material</b> / <b>Jet</b> → Suchfeld", "wn_create_search.svg"),
                ("h", "Onboarding"),
                ("feature", "Onboarding - unsere Arbeit als kurze Animationen",
                 "Neuer Eintrag <b>Onboarding</b> unter <b>Help (F1)</b>: kurze animierte Einführungen in unsere "
                 "Arbeit, im ganzen Fenster. Das erste Thema zeigt, wie ein DTY-Garn verwirbelt wird - der Weg "
                 "durch die Maschine mit dem Overfeed zwischen Lieferwerk 2 und 2.x (jede Position anklicken, sie wird "
                 "erklärt), was in der Düse passiert, und die Knoten. Jedes Thema hat Reiter wie der Rest von TrippleT. "
                 "Probier die Regler <b>Overfeed</b> und <b>Luftdruck</b>. Die Sprache wechselst "
                 "du über die Flaggen - jetzt auch Chinesisch. Zweites Thema: <b>ATY-Lufttexturierung</b> - Voreilung "
                 "von Kern und Effekt, die Texturierdüse, Schlingen und was die Einstellungen bewirken. Unter <b>Spinnerei</b>: "
                 "<b>Filamentgarnspinnerei</b> - vom Granulat zu POY und FDY, und wo die Heberlein-Düsen sitzen. Ebenfalls unter "
                 "<b>Spinnerei</b>: <b>BCF-Teppichgarn</b> - Spinnen, Verstrecken, Heissluft-Texturieren und Verwirbeln in einem Schritt, "
                 "inkl. Tricolor-Mischung, und <b>Luftdüsenspinnen</b> (Stapelfasern) - vom Ballen zum Garn, Luftwirbel um die Hohlspindel. Unter <b>Spleissen</b>: <b>Filamentgarn-Spleissen</b> - zwei Enden knotenfrei verbinden; "
                 "einen Schritt anklicken springt direkt dorthin. "
                 "Unter <b>Einfädeln</b>: <b>Lufan-Absaugpistole</b> - einfädeln bei "
                 "laufender Maschine, Injektorprinzip, Luftverbrauch. Unter <b>DTY</b> → <b>Spezialwissen</b>: <b>Cotton-like DTY</b> (sieben Wege zur Spinngarn-Optik, jede Maschinenposition anklickbar) und <b>Harte Knoten, weniger Dehnung?</b> (eine These mit einem Modell-Zugversuch zum Zuschauen). In der DTY-Maschine gibst du jetzt die Geschwindigkeit von <b>LW 2</b> und die <b>Verstreckung</b> ein: LW 1 und LW 2.x stehen dann in m/min da. Neue Szene <b>Gleichmässigkeit</b> im DTY-Thema: Gleich viele Knoten reichen nicht, sie müssen gleichmässig verteilt sein (Streuung der Abstände, längste offene Stelle). Das DTY-Thema hat jetzt am Schluss einen Reiter <b>Quiz</b>: 13 Fragen, zu jeder ein Link zurück zur passenden Szene - ab 80 % richtig ist das Thema bestanden und bekommt in der Liste ein Häkchen. Neuer Ordner <b>Labor</b> mit <b>Knotenmessung mit dem ITEMAT</b>: Aufbau (Stationen anklicken), mechanischer und optischer Sensor, was eine falsche Schwelle bewirkt, Stabilitätstest unter Last und Auswertung, sowie <b>Titer, Festigkeit und Dehnung (STATIMAT DS)</b>: Titer durch Wägen, Zugversuch nach CRE mit POY, FDY und DTY im Vergleich, Statistik pro Spule, und <b>Kräuselung und Schrumpf (TEXTURMAT ME)</b>: vom Strang über die Wärmebehandlung zu den fünf Laststufen (anklickbar) und den Kennwerten KK, KM, KB und Schrumpf, und <b>Knotenprüfung mit dem RAPID 600 V</b>: Die Nadelmethode zählt die Knoten im laufenden Garn und trennt gute von schwachen Knoten, mit Regler für die Auslösekraft. Weitere Themen folgen.",
                 "Sidebar → <b>Onboarding</b>", "wn_onboarding.svg"),
            ],
            # ═══════════════════════════════ ES ═══════════════════════════════
            "es": [
                ("h", "Smart Chart"),
                ("feature", "¿Cuántos jets distintos? - Count (distinct)",
                 "Una Card cuenta ahora cuántos valores <b>distintos</b> tiene un campo - p.&nbsp;ej. cuántos jets, "
                 "hilos o máquinas distintos se usaron, siempre dentro de tus filtros, slicers y clics. Elige la "
                 "agregación <b>Count (distinct)</b> y arrastra el campo (p.&nbsp;ej. <i>Jet</i>) a <b>Value</b>. "
                 "Los valores vacíos no cuentan. También funciona en Columns, Matrix y Pie - p.&nbsp;ej. jets "
                 "distintos por año.",
                 "Smart Chart → Card → agregación <b>Count (distinct)</b>", "wn_distinct_count.svg"),
                ("feature", "¿Qué jets son? - una fila por valor",
                 "Una Table puede listar ahora cada jet (o hilo, máquina …) una sola vez en lugar de cada ensayo: "
                 "marca <b>One row per value</b>. Junto al nombre ves en cuántos ensayos y series se usó; un campo "
                 "numérico como FP/m muestra su media. Con los mismos filtros, la lista tiene exactamente tantas "
                 "líneas como cuenta la Card con <b>Count (distinct)</b>. Clic en un encabezado para ordenar.",
                 "Smart Chart → Table → Build → <b>One row per value</b>", "wn_value_table.svg"),
                ("h", "Create Experiment"),
                ("feature", "Encontrar hilos y jets escribiendo",
                 "Las pestañas <b>Material</b> y <b>Jet</b> tienen ahora un campo de búsqueda sobre la lista. "
                 "Escribe parte del nombre (p.&nbsp;ej. <i>pa6 44</i>) - se busca en todos los grupos a la vez y "
                 "solo quedan visibles los resultados. En los jets también se busca el nombre de desarrollo. "
                 "<b>Enter</b> elige el primer resultado, <b>Esc</b> borra la búsqueda. Detrás de cada hilo ves "
                 "además el símbolo de bobina de Show Experiment: bobina verde = en stock (clic para ver dónde "
                 "están las bobinas), tubo tachado = nada en stock.",
                 "New Experiment → <b>Material</b> / <b>Jet</b> → campo de búsqueda", "wn_create_search.svg"),
                ("h", "Onboarding"),
                ("feature", "Onboarding - nuestro trabajo en animaciones cortas",
                 "Nueva entrada <b>Onboarding</b> debajo de <b>Help (F1)</b>: introducciones animadas cortas a "
                 "nuestro trabajo, a pantalla completa. El primer tema muestra cómo se entrelaza un hilo DTY: el "
                 "recorrido por la máquina con la sobrealimentación entre el rodillo 2 y el 2.x (haz clic en una posición "
                 "y se explica), lo que pasa en la "
                 "tobera y los nudos. Prueba los reguladores de <b>sobrealimentación</b> y <b>presión de aire</b>. "
                 "Cambia el idioma con las banderas - ahora también en chino. Segundo tema: <b>texturizado ATY por "
                 "aire</b> - sobrealimentación de núcleo y efecto, la tobera, los bucles y qué hacen los ajustes. En <b>Hilatura</b>: "
                 "<b>hilatura de filamento</b> - del granulado al POY y FDY, y dónde están las toberas Heberlein. También en "
                 "<b>Hilatura</b>: <b>hilo BCF para alfombras</b> - hilatura, estirado, texturizado por aire caliente y entrelazado "
                 "en un paso, incl. mezcla tricolor, y <b>hilatura por chorro de aire</b> (fibras cortas) - de la bala al hilo, remolino alrededor del huso hueco. En <b>Empalme</b>: <b>empalme neumático de filamento</b> - unir dos extremos "
                 "sin nudo; haz clic en un paso para saltar a él. "
                 "En <b>Enhebrado</b>: <b>pistola de aspiración Lufan</b> - "
                 "enhebrar con la máquina en marcha, principio del inyector, consumo de aire. En <b>DTY</b> → <b>Conocimiento especializado</b>: <b>DTY tipo algodón</b> (siete caminos al aspecto de hilo hilado, cada posición de la máquina se puede pulsar) y <b>¿Nudos duros, menos alargamiento?</b> (una hipótesis con un ensayo de tracción simulado). En la máquina DTY ahora introduces la velocidad de <b>R 2</b> y el <b>estirado</b>: R 1 y R 2.x aparecen en m/min. Nueva escena <b>Regularidad</b> en el tema DTY: no basta con el mismo número de nudos, deben estar repartidos de forma regular (dispersión de las distancias, tramo abierto más largo). El tema DTY termina ahora con una pestaña <b>Quiz</b>: 13 preguntas, cada una con un enlace a la escena correspondiente; con un 80 % de aciertos el tema queda aprobado y recibe una marca en la lista. Nueva carpeta <b>Laboratorio</b> con <b>Medición de nudos con el ITEMAT</b>: montaje (haz clic en las estaciones), sensor mecánico y óptico, qué provoca un umbral incorrecto, ensayo de estabilidad bajo carga y evaluación, y <b>Título, tenacidad y alargamiento (STATIMAT DS)</b>: título por pesaje, tracción CRE comparando POY, FDY y DTY, estadística por bobina, y <b>Rizado y contracción (TEXTURMAT ME)</b>: de la madeja al tratamiento térmico, los cinco escalones de carga (se pueden pulsar) y los indicadores de rizado y contracción, y <b>Ensayo de nudos con el RAPID 600 V</b>: el método de aguja cuenta los nudos en el hilo en marcha y separa los buenos de los débiles, con regulador de la fuerza de disparo. Habrá más temas.",
                 "Sidebar → <b>Onboarding</b>", "wn_onboarding.svg"),
            ],
        },
    },
    {
        "version": "4.6.3",
        "date": "2026-11-03",
        "texts": {
            # ═══════════════════════════════ EN ═══════════════════════════════
            "en": [
                ("h", "Show Experiment"),
                ("feature", "Yarns of the series in one table",
                 "<b>Yarns…</b> shows every ply of the series with its yarn and every trial. Click a yarn to change "
                 "it for the whole ply - type a part of the name to find it, e.g. <i>167 dty</i>. Click a cell to "
                 "switch a ply on or off for one trial, type 1-9 for the number of ends. <b>+ Add ply</b> adds a "
                 "ply for all trials. Changed cells are yellow, nothing is saved before <b>Apply</b>.",
                 "Show Experiment → Machine Data → <b>Yarns…</b> (or right-click the Ply row)", "wn_series_yarns.svg"),
                ("feature", "Where are my spools?",
                 "A small spool behind every ply in the Material line tells you at a glance: green spool = this yarn "
                 "is in stock, crossed-out tube = nothing in stock. Click the yarn or the green spool to see every spool in "
                 "stock by storage location, with batch, weight and tube colour. Spools assigned to this series "
                 "are bold. <b>Open in Yarn Stock</b> takes you straight to the yarn.",
                 "Show Experiment → Material line → yarn or spool symbol", "wn_spool_locations.svg"),
                ("feature", "Notes on values",
                 "Write down why a value looks the way it does - right where it is: right-click a value → "
                 "<b>Add note…</b>, e.g. <i>Spool had knots, measured again</i>. A small purple triangle marks the "
                 "cell, pointing at it shows the note with name and date. Right-click a trial number for a note on "
                 "the whole trial. The <b>Notes</b> tab lists all notes of the series, double-click jumps to the "
                 "value. Everybody can write notes. In the <b>Report</b> of a series, the <b>Notes</b> button shows them as a "
                 "purple outline with the note in the tooltip; they are not printed in the PDF unless you tick "
                 "<i>Include notes on values</i> when exporting. In the Smart Chart dashboard, tick <i>Show notes "
                 "on values</i> on a Points visual.",
                 "Show Experiment → right-click a value → <b>Add note…</b>", "wn_cell_notes.svg"),
                ("feature", "Reference samples",
                 "Add a customer's original spool as a benchmark. It appears as a highlighted <i>Ref</i> column "
                 "and as a horizontal line in the report - and is never counted as a trial.",
                 "Show Experiment → Machine Data → <b>+ Ref</b>", "wn_reference.svg"),
                ("feature", "Copy trials - with changes",
                 "Choose which trials, how often and in which order, and change values (e.g. air pressure, jet, "
                 "OF Core/Effect) before copying. Comments and the tensions before/after the jet are not copied - "
                 "the copies start with them empty.",
                 "Show Experiment → Machine Data → <b>Copy trials</b>", "wn_copy_trials.svg"),
                ("feature", "D/Y Ratio (T2/T1)",
                 "Calculated automatically from T1 and T2 and shown right below T2 Tension on DTY machines.",
                 "Show Experiment → Machine Data", "wn_dy_ratio.svg"),
                ("feature", "Faster data entry - like in Excel",
                 "Type a value and press <b>Enter</b>: you land in the cell below, ready for the next value "
                 "(<b>Shift+Enter</b> goes up). Click a cell (or select several) and press <b>Delete</b> to empty "
                 "them - no double-click needed. Save with <b>Save</b> or <b>Ctrl+S</b>; instead of a \"Saved\" "
                 "message to click away, the yellow disappears and a green tick lights up briefly in the middle - "
                 "you can keep typing right away.",
                 "Show Experiment → any table", None),
                ("feature", "Undo with Ctrl+Z",
                 "Typed the wrong value, pasted into the wrong place or deleted too much? <b>Ctrl+Z</b> takes it "
                 "back step by step, <b>Ctrl+Y</b> does it again - as long as you have not saved yet.",
                 "Show Experiment → any table", None),
                ("feature", "Back on your tab",
                 "A series opens on the tab you used last for it, e.g. <i>Statimat M</i> instead of always "
                 "<i>Machine Data</i>.",
                 "Show Experiment", None),
                ("feature", "Hide rows you don't need",
                 "Right-click a parameter name → <b>Hide row</b>. A blue line shows where rows are hidden; click "
                 "it, or use <b>n rows hidden</b>, to show them again. Remembered per machine.",
                 "Show Experiment → Machine Data → right-click a parameter name", "wn_hide_rows.svg"),
                ("feature", "See what is not saved yet",
                 "Changed cells stay yellow until you save (<b>Save</b> or <b>Ctrl+S</b>). The button shows how many, "
                 "e.g. <b>Save (3)</b>, and the "
                 "tab gets a dot. Closing a tab or the program with unsaved changes now asks first - before, they "
                 "were lost without a word.",
                 "Show Experiment", "wn_unsaved.svg"),
                ("feature", "Typo check when saving",
                 "Machine settings far outside the usual range of this machine (e.g. 35 instead of 3.5 bar) are "
                 "listed before saving. You can go back or save anyway.",
                 "Show Experiment → <b>Save</b>", "wn_unusual.svg"),
                ("feature", "Change history (superusers)",
                 "See who changed a value, when, and what it was before - for one value or the whole series.",
                 "Show Experiment → right-click a value → <b>Change history…</b>", "wn_history.svg"),
                ("feature", 'Report: two levels on the X axis',
                 'In the report of a series each chart can now show two levels on the X axis - e.g. <b>Yarn</b> (short name) and under it the <b>Jets</b>, only the combinations that were really tested. Choose the second level in the new list right of X. <b>Yarn</b> and <b>Jet</b> can also be chosen as X on their own.',
                 'Show Experiment → <b>Report</b> → X … › …', None),
                ("h", "Smart Chart"),
                ("feature", "New Smart Chart: find trials by their properties",
                 "Pick trials across <b>all</b> series by yarn, jet geometry, machine settings and lab results - e.g. all polyester "
                 "trials with 70–80 dtex end titer and 30–40 filaments. <b>+ Add filter</b> shows how the values are "
                 "spread and how many trials each filter leaves; number filters can keep only whole numbers, every 0.5 or "
                 "values you tick. Then show them in a dashboard: any field against any other - as points, "
                 "trend lines with R², mean lines, bars, box plots, violins, histograms or a density map - coloured "
                 "by jet, machine or a number, one small chart per machine. ⤢ on a chart shows it big with its "
                 "trials below: click a point to find the trial, double-click to open it. Save it as a view (also "
                 "shared), export to PDF or Excel.",
                 "Sidebar → <b>Smart Chart</b>", "wn_smart_chart.svg"),
                ("feature", 'Is this comparison fair?',
                 'A coloured dot on every chart warns when the groups you compare also differ in other things that change the result - e.g. jet A was mostly tested on PES at 3.5 bar, jet B on PA at 2 bar. Green, yellow or red, with the reason in one sentence. A click on the dot shows every condition; <b>Make it fairer</b> keeps only what all groups have in common. It also warns about very small groups, groups from one single series and groups in different X ranges.',
                 'Smart Chart → coloured dot in the title bar of a chart', "wn_fairness.svg"),
                ("feature", 'Dashboard: build your own page, like Power BI',
                 'Smart Chart is a dashboard now: a page with several visuals side by side. Drag fields from <b>Fields</b> - every table, from Statimat and Itemat to DTYoMat, jet and yarn - into the wells of a visual. New visuals: <b>Matrix</b> (e.g. FP/m per jet and air pressure, coloured - empty cells show where trials are missing), <b>Card</b> (one number) and <b>Table</b>. Click a bar, box or matrix cell and all other visuals highlight it. <b>Slicers</b> pick values for the whole page - as a list, dropdown, tiles or a range slider. Place visuals freely and resize them, work with several pages (tabs at the bottom) and add filters to one page or one visual. New: <b>calculated fields</b> from your own formula, <b>targets</b> (green/red, target lines), <b>drill-down</b> machine → jet and <b>selecting points</b> to filter the page. Plus: <b>templates</b> (Jet comparison, Yarn overview, Machine check, Lab overview), <b>PDF</b> of one or all pages, <b>Excel</b> per visual or page, notes on values, undo with <b>Ctrl+Z</b>, and <b>lining up</b> several visuals at once (Ctrl+click, then align, same size or distribute).',
                 'Sidebar → <b>Smart Chart</b>', "wn_dashboard.svg"),
                ("feature", 'Lab statistics in the dashboard',
                 'Count <b>experiments, trial series or trials</b> - per month, product group, order type, project, owner or lab machine (<i>Tested on</i>). The new visual <b>Columns</b> shows them stacked, side by side or as 100 %; months and years run in order, empty months show as 0. Start with <b>New</b> → <b>Lab statistics</b>. Filters on a month or year can now be a period that moves with the calendar: <b>This year</b>, <b>Last 12 months</b>, <b>From – to</b> … And the slicer <b>Year › Month</b>: years that fold open with the months Jan–Dec below.',
                 'Smart Chart → <b>New</b> → <b>Lab statistics</b>', "wn_dashboard_stats.svg"),
                ("feature", 'Stacked fields: how parts add up',
                 'The new dashboard visual <b>Stacked fields</b> puts several number fields into one column, each in its own colour - e.g. A, B and C knots of the DTYoMat per trial, as <b>100 %</b> (the share of each part) or as values. With the new field <b>Trial</b> on the X axis you get one column per trial. As a <b>combo chart</b>, lines on a second axis on the right show e.g. FP/m over it.',
                 'Smart Chart → Visualizations → <b>Stacked fields</b>', "wn_stacked_fields.svg"),
                ("feature", 'Format visuals: order, Top N, colours, axes, tables',
                 'A visual in the dashboard now has a second tab <b>Format</b> next to <b>Build</b>. Order bars and boxes by value or name and show only the <b>top 10</b> (e.g. the best jets), set the <b>decimal places</b>, put the <b>values on the bars</b>, choose the <b>error bars</b> on bars and mean lines - standard deviation, <b>95 % confidence</b> (do two jets really differ? if the bars hardly overlap, probably yes), <b>min – max</b> or off -, write your own <b>axis titles</b> or hide them, fix where the <b>Y axis</b> starts and ends, move the <b>legend</b> to the top, the bottom or away, choose a <b>palette</b> or your own <b>colour per value</b>, make text and <b>cards</b> bigger or smaller and switch grid lines off. <b>Tables</b> sort with a click on a column heading and get <b>colour rules</b> (e.g. FP/m above 100 in green). A <b>dashboard theme</b> (Format with nothing selected) sets palette, text size, decimals … for all visuals at once, and <b>Copy format</b> at the top of the page gives another visual the same format (double-click: several, Esc ends). Every change shows at once; a green dot marks what differs from the standard, <b>Reset</b> sets it back. The PDF shows it the same way.',
                 'Smart Chart → click a visual → Visualizations → <b>Format</b>', "wn_dashboard_format.svg"),
                ("feature", 'Dashboard PDF that looks like the page',
                 'The PDF of a dashboard now has the Heberlein logo, uses the whole page and no text runs over the edge of its box any more. <b>Slicers</b> are printed the way you see them: tick boxes, tiles, the range slider or years with their months. Charts also work <b>without an internet connection</b>.',
                 'Smart Chart → <b>PDF</b>', None),
                ("feature", 'New visuals: pie, donut, control chart, radar, text',
                 'Five new visuals in the dashboard: <b>Pie</b> and <b>Donut</b> for shares (click a piece to filter the page), the <b>Control chart</b> with mean and ±3σ limits - points outside in red, long runs on one side in amber -, the <b>Radar</b> to compare jets, yarns or machines over several values at once, and <b>Text</b> for headings and comments. All visuals also got new, clearer icons.',
                 'Smart Chart → Visualizations', "wn_dashboard_visuals.svg"),
                ("feature", 'Dashboard: analytics lines and drill-through',
                 'New tab <b>Analytics</b> next to Build and Format: average, median, ± 1/2/3 standard deviations, percentile, min/max, a constant line or a band from - to (e.g. your spec limits) right in the chart - calculated from the trials in it. And <b>drill-through</b> like in Power BI: make a page the detail page for e.g. <b>Machine</b> (Filters → <b>Drill-through to this page</b>), then right-click a bar of a machine on another page → <b>Drill through</b>. The detail page shows only that machine; <b>← Back</b> brings you back.',
                 'Smart Chart → Visualizations → <b>Analytics</b> · right-click a bar', "wn_dashboard_analytics.svg"),
                ("feature", 'Click to highlight - the rest turns grey',
                 'Click a bar, a column, a slice or a point in a dashboard: the other visuals no longer jump to only that part. They keep all their trials and grey out the rest, so you see the part within the whole - e.g. how much of every column comes from machine AFK. The clicked visual greys out its other bars, too. Points of other trials turn grey, bars of averages show the average of the highlighted trials on top of the faded one. Cards, matrix, table, radar, box, violin and histogram still filter, slicers too. Click again to undo. Prefer the old way? Format with nothing selected → <b>Clicks</b> → <i>Filters the other visuals</i>.',
                 'Smart Chart, Dashboards → click a bar, slice or point', "wn_click_highlight.svg"),
                ("feature", 'Focus: one visual big, with its trials',
                 'Click ⤢ in the title bar of a visual: it fills the page, and below it are all trials it is made of. Click a point to find its line, double-click a line to open the trial in Show Experiment. A click on the coloured fairness dot shows the details with <b>Make it fairer</b>. In <b>Format</b> there are now also logarithmic axes, a shape per colour and the point size.',
                 'Smart Chart → ⤢ on a visual', None),
                ("feature", 'Model: how the tables hang together',
                 'Click <b>Model</b> at the top left of the dashboard: the trial in the middle, around it yarn, jet, experiment, time and all lab tables, with how they are linked (1 : n = several rows per trial, averaged). Click a table to see its fields and how many trials have a value. Read only - nothing can be changed there.',
                 'Smart Chart → <b>Model</b>', "wn_model_view.svg"),
                ("feature", 'Heberlein colours as the standard',
                 'Charts and dashboards now start in the <b>Heberlein</b> palette: Heberlein green and the dark blue of the logo first, then colours that are easy to tell apart. The eight greens are still there as <b>Heberlein green</b>.',
                 'Smart Chart → click a visual → <b>Format</b> → Colours (nothing selected: for all visuals)', None),
                ("feature", 'Wider or narrower side panes',
                 'In the dashboard, drag the left edge of <b>Filters</b>, <b>Visualizations</b> or <b>Fields</b> to make it wider or narrower - TrippleT remembers it. A double-click on the edge gives the standard width back.',
                 'Sidebar → <b>Smart Chart</b>', None),
                ("feature", 'Dashboards: look at them, share them',
                 'The new page <b>Dashboards</b> shows your own dashboards and the ones colleagues shared with you. Here you only look: slicers, clicking bars to filter, drill-down, page tabs and <b>PDF</b> work - nothing gets changed by accident. To share your dashboard, open it in Smart Chart and click <b>Share…</b>: with everybody, with single people or with groups (read, write, admin, superuser), each to <b>view</b> or to <b>edit</b>. Only you can share or delete it.',
                 'Sidebar → Tools → <b>Dashboards</b> · Smart Chart → <b>Share…</b>', "wn_dashboards.svg"),
                ("feature", 'Superusers decide who may use which tool',
                 'In <b>Manage User → Access…</b> a superuser switches every tool and screen on or off - for a group (read, write, admin) or for a single person, e.g. Smart Chart for one colleague, or no Backlog for a group. A setting for a person wins over the group; without settings everything stays as before. Blocked tools disappear from the sidebar from the next login.',
                 'Sidebar → Superuser → Manage User → <b>Access…</b>', "wn_feature_access.svg"),
                ("h", "Settings"),
                ("feature", 'Choose your start screen',
                 'Decide which screen opens after the login - Backlog (as before), All Experiments, Dashboards, Yarn Stock or another tool you use. If a superuser switches that tool off for you, Backlog opens instead.',
                 'Sidebar → Account → <b>Settings</b> → <b>Start screen</b>', "wn_start_screen.svg"),
                ("feature", "Text size for the whole program",
                 "Normal, Large, Extra large or Huge - buttons, menus, tables and dialogs all grow. Applies after a "
                 "restart. Welcome message and accent colour are set here, too.",
                 "Sidebar → Account → <b>Settings</b>", "wn_text_size.svg"),
                ("feature", "Easier reading in tables",
                 "High contrast, a crosshair for row and column, a reading bar with the value in large words, "
                 "warning symbols and colour-blind friendly colours. Zoom a table with Ctrl + mouse wheel.",
                 "Sidebar → Account → <b>Settings</b> → Show Experiment tables", "wn_reading.svg"),
                ("h", "Help"),
                ("feature", "Help in three languages",
                 "Show Experiment, Backlog, Report, Smart Chart, Dashboards, All Experiments, Create Experiment, Manage Yarn and Manage Jets "
                 "now have their own help in English, German and Spanish: step-by-step answers to \"How do I…?\", a "
                 "sketch of the screen and the rules. The flags switch the language.",
                 "Round <b>?</b> button on these screens", "wn_help.svg"),
                ("feature", "Help search - \"Where do I find…?\"",
                 "Type your question in your own words and get the matching help page - in English, German or "
                 "Spanish. <b>Take me there</b> opens the screen.",
                 "Sidebar → <b>Help (F1)</b> or the F1 key", "wn_help_search.svg"),
                ("feature", "Search in Fresh off the Spool",
                 "Know a feature exists but not when it came? Type a word in the search field above the version "
                 "list - all versions are searched at once, in English, German and Spanish. Versions with hits show "
                 "how many; click one to jump to it. Each version is now split into tabs by area, e.g. "
                 "<i>Show Experiment (8)</i>.",
                 "Sidebar → Account → <b>Fresh off the Spool</b> → search field", "wn_whats_new_search.svg"),
                ("feature", "Fresh off the Spool as PDF",
                 "Save a version's news as a PDF - to print it or send it to colleagues. Each topic stays together "
                 "on one page.",
                 "Sidebar → Account → <b>Fresh off the Spool</b> → <b>PDF</b>", "wn_whats_new_pdf.svg"),
                ("h", "Backlog and All Experiments"),
                ("feature", "Move several cards at once",
                 "Hold <b>Ctrl</b> and click the cards (or <b>Shift+click</b> for a whole range), then drag one of "
                 "them - all selected cards move together, e.g. from <i>To Be Cleaned</i> to <i>Archived</i>. "
                 "TrippleT asks once and tells you if a card was not allowed to move.",
                 "Backlog → <b>Ctrl+click</b> the cards → drag", "wn_backlog_multi_move.svg"),
                ("feature", "Backlog on wide screens",
                 "On big monitors all four columns stand side by side and use the full height.",
                 "Backlog", "wn_wide_backlog.svg"),
                ("feature", "Recycle Bin",
                 "A deleted trial series can be restored for 90 days. Whoever may move a series in the Backlog may "
                 "delete it (in To Be Cleaned: superusers only).",
                 "Sidebar → Superuser → <b>Recycle Bin</b>", "wn_recycle_bin.svg"),
                ("feature", "Look inside the Recycle Bin",
                 "Not sure what a deleted series contains? Double-click it: it opens read only in Show Experiment. "
                 "A yellow bar lets you <b>Restore for good</b>, put it <b>Back to Recycle Bin</b> or "
                 "<b>Delete permanently</b>. Closing the tab puts it back - with its original deletion date.",
                 "Sidebar → Superuser → <b>Recycle Bin</b> → double-click a series", "wn_recycle_preview.svg"),
                ("feature", "All Experiments uses the whole window",
                 "The list fills the full width and height of the window - the last columns are visible without "
                 "scrolling sideways - and is shown larger on big screens.",
                 "All Experiments", "wn_all_experiments.svg"),
                ("h", "Yarns"),
                ("feature", "See the colour of a yarn",
                 "A small square in front of the yarn name shows its colour - black, white, beige, grey, natural. "
                 "Hold the mouse over it to read the colour. You can also search by colour, e.g. <i>black</i>. The "
                 "colour comes from the <i>Colour</i> field of the yarn (<b>Manage Yarn</b>).",
                 "Yarns… dialog, Create Experiment, Yarn Stock, Manage Yarn, Reassign Yarn, Show Experiment "
                 "(Ply row)", "wn_yarn_colour.svg"),
                ("h", "Yarn Stock"),
                ("feature", "Stock status per yarn",
                 "The traffic light now shows each yarn as a whole: all its batches in stock against its minimum "
                 "stock. Used-up batches disappear from the overview, notifications come once per yarn. Only "
                 "superusers may change the minimum stock.",
                 "Yarn Stock → Overview", "wn_stock_status.svg"),
                ("feature", "New spools - straight to the new spools and the label queue",
                 "<b>New spool(s)</b> starts with an empty selection and afterwards jumps right to the new spools. "
                 "They go to the label queue automatically (tick box in the dialog).",
                 "Yarn Stock → <b>New spool(s)</b>", "wn_new_spools.svg"),
                ("feature", "Stock take - location by location",
                 "A superuser starts a stock take round (and can leave out single locations). Every location is a "
                 "tile: grey = open, green = all fine, orange = differences. Click one and scan its spools (no label? "
                 "double-click it in the list). "
                 "<b>Results</b> shows what was found where, exportable to Excel. Spools in another place are moved "
                 "right away, missing ones are only booked out when you finish - after asking.",
                 "Yarn Stock → Rack lookup → <b>Stock take…</b>", "wn_stock_take.svg"),
                ("feature", "Spool history",
                 "Every change of a spool is recorded: created, changed, moved, booked out, stock take. Without a "
                 "selection you see the whole batch, including used-up spools.",
                 "Yarn Stock → <b>History…</b>", "wn_spool_history.svg"),
                ("feature", "Scan labels, keep changes",
                 "In <i>Go to spool #</i> you can scan the spool label instead of typing the number. And Yarn Stock "
                 "now asks before unsaved spool changes are lost. Help in three languages: round button top right.",
                 "Yarn Stock → <b>Go to spool #</b>", None),
                ("h", "General"),
                ("feature", "Fresh off the Spool: what's new in TrippleT",
                 "All new features of every version in one place: one tab per area, searchable and as PDF. "
                 "It opens by itself once after a new version - and anytime in the sidebar.",
                 "Sidebar → Account → <b>Fresh off the Spool</b>", "fresh_off_the_spool.png"),
                ("feature", "Recent series",
                 "The series you opened last are one click away: <b>Recent</b> in the sidebar (at the bottom, above Account). "
                 "Click one to open it, <b>Ctrl+click</b> opens it in a new tab. The list follows you to every PC.",
                 "Sidebar → <b>Recent</b>", None),
                ("feature", "Athena answers in your language",
                 "Athena and the Lab Assistant now answer in the language you ask in - English, German, Spanish, "
                 "… Without a question (e.g. the automatic analysis) the answer is in English.",
                 "Show Experiment → Athena, Lab Assistant", None),
                ("feature", "Error messages that help",
                 "When something goes wrong, TrippleT now says in plain words what did not work, why, and what you "
                 "can do - e.g. \"The file is open in another program - close it (e.g. in Excel) and try again.\" "
                 "The technical text is under <b>Show Details</b>, to send to the admin.",
                 "Whole program", None),
                ("feature", "All texts in English",
                 "Messages, buttons, menus and status texts that were still in German are now in English everywhere - "
                 "e.g. the right-click menu in the Backlog says <b>Reassign yarn…</b>. Lab terms such as Kurzhocker or "
                 "Langwelle stay as they are.",
                 "Whole program", None),
            ],
            # ═══════════════════════════════ DE ═══════════════════════════════
            "de": [
                ("h", "Show Experiment"),
                ("feature", "Garne der Serie in einer Tabelle",
                 "<b>Yarns…</b> zeigt alle Plies der Serie mit ihrem Garn und alle Versuche. Ein Klick aufs Garn "
                 "tauscht es für die ganze Ply - zum Finden einen Teil des Namens tippen, z.&nbsp;B. <i>167 dty</i>. "
                 "Ein Klick in eine Zelle schaltet die Ply für diesen Versuch ein oder aus, 1-9 tippen setzt die "
                 "Anzahl Enden. <b>+ Add ply</b> fügt eine Ply für alle Versuche hinzu. Geänderte Zellen sind gelb, "
                 "gespeichert wird erst mit <b>Apply</b>.",
                 "Show Experiment → Machine Data → <b>Yarns…</b> (oder Rechtsklick auf die Ply-Zeile)",
                 "wn_series_yarns.svg"),
                ("feature", "Wo liegen meine Spulen?",
                 "Eine kleine Spule hinter jeder Ply in der Materialzeile zeigt auf einen Blick: grüne Spule = dieses "
                 "Garn ist am Lager, durchgestrichene Hülse = nichts am Lager. Ein Klick aufs Garn oder die grüne Spule zeigt "
                 "alle Spulen am Lager nach Lagerplatz, mit Batch, Gewicht und Hülsenfarbe. Spulen, die dieser Serie "
                 "zugewiesen sind, stehen fett. <b>Open in Yarn Stock</b> springt direkt zum Garn.",
                 "Show Experiment → Materialzeile → Garn oder Spulen-Symbol", "wn_spool_locations.svg"),
                ("feature", "Notizen an Werten",
                 "Festhalten, warum ein Wert so ist - direkt dort, wo er steht: Rechtsklick auf einen Wert → "
                 "<b>Add note…</b>, z.&nbsp;B. <i>Spule hatte Knoten, nachgemessen</i>. Ein kleines violettes "
                 "Dreieck markiert die Zelle, mit der Maus darauf zeigen zeigt die Notiz mit Name und Datum. "
                 "Rechtsklick auf eine Versuchsnummer für eine Notiz zum ganzen Versuch. Der Tab <b>Notes</b> "
                 "listet alle Notizen der Serie, Doppelklick springt zum Wert. Notizen schreiben darf jeder. Im "
                 "<b>Report</b> einer Serie zeigt der Knopf <b>Notes</b> sie als violetten Rand mit der Notiz im Tooltip; "
                 "ins PDF kommen sie nur, wenn man beim Export <i>Include notes on values</i> ankreuzt. Im Dashboard "
                 "des Smart Chart bei einem Points-Visual <i>Show notes on values</i> ankreuzen.",
                 "Show Experiment → Rechtsklick auf einen Wert → <b>Add note…</b>", "wn_cell_notes.svg"),
                ("feature", "Referenzmuster",
                 "Die Originalspule eines Kunden als Vergleich hinzufügen. Sie erscheint als hervorgehobene "
                 "<i>Ref</i>-Spalte und im Report als waagrechte Linie - und zählt nie als Versuch.",
                 "Show Experiment → Machine Data → <b>+ Ref</b>", "wn_reference.svg"),
                ("feature", "Versuche kopieren - mit Änderungen",
                 "Wählen, welche Versuche wie oft und in welcher Reihenfolge kopiert werden, und Werte (z.&nbsp;B. "
                 "Luftdruck, Düse, OF Core/Effect) vor dem Kopieren ändern. Kommentare und Fadenspannungen "
                 "vor/nach Jet werden nicht mitkopiert - die Kopien starten damit leer.",
                 "Show Experiment → Machine Data → <b>Copy trials</b>", "wn_copy_trials.svg"),
                ("feature", "D/Y Ratio (T2/T1)",
                 "Wird bei DTY-Maschinen automatisch aus T1 und T2 berechnet und direkt unter T2 Tension angezeigt.",
                 "Show Experiment → Machine Data", "wn_dy_ratio.svg"),
                ("feature", "Schneller erfassen - wie in Excel",
                 "Wert tippen und <b>Enter</b> drücken: Du landest in der Zelle darunter, bereit für den nächsten "
                 "Wert (<b>Umschalt+Enter</b> geht nach oben). Zelle anklicken (oder mehrere markieren) und "
                 "<b>Entf</b> drücken leert sie - ohne Doppelklick. Speichern mit <b>Save</b> oder <b>Strg+S</b>; "
                 "statt einer \"Saved\"-Meldung zum Wegklicken verschwindet das Gelb und in der Mitte leuchtet "
                 "kurz ein grünes Häkchen auf - du kannst sofort weitertippen.",
                 "Show Experiment → jede Tabelle", None),
                ("feature", "Rückgängig mit Strg+Z",
                 "Falschen Wert getippt, an der falschen Stelle eingefügt oder zu viel gelöscht? <b>Strg+Z</b> nimmt "
                 "es Schritt für Schritt zurück, <b>Strg+Y</b> stellt es wieder her - solange noch nicht gespeichert "
                 "ist.",
                 "Show Experiment → jede Tabelle", None),
                ("feature", "Zurück auf deinem Reiter",
                 "Eine Serie öffnet sich auf dem Reiter, den du zuletzt bei ihr benutzt hast, z.&nbsp;B. "
                 "<i>Statimat M</i> statt immer <i>Machine Data</i>.",
                 "Show Experiment", None),
                ("feature", "Nicht benötigte Zeilen ausblenden",
                 "Rechtsklick auf einen Parameternamen → <b>Hide row</b>. Eine blaue Linie zeigt, wo Zeilen fehlen; "
                 "ein Klick darauf oder <b>n rows hidden</b> holt sie zurück. Gemerkt pro Maschine.",
                 "Show Experiment → Machine Data → Rechtsklick auf Parameternamen", "wn_hide_rows.svg"),
                ("feature", "Sehen, was noch nicht gespeichert ist",
                 "Geänderte Zellen bleiben gelb, bis gespeichert ist (<b>Save</b> oder <b>Strg+S</b>). Der Knopf zeigt "
                 "die Anzahl, z.&nbsp;B. "
                 "<b>Save (3)</b>, und der Tab bekommt einen Punkt. Wer einen Tab oder das Programm mit "
                 "ungespeicherten Änderungen schliesst, wird jetzt gefragt - vorher gingen sie wortlos verloren.",
                 "Show Experiment", "wn_unsaved.svg"),
                ("feature", "Tippfehler-Prüfung beim Speichern",
                 "Maschineneinstellungen weit ausserhalb des Üblichen dieser Maschine (z.&nbsp;B. 35 statt 3.5 bar) "
                 "werden vor dem Speichern aufgelistet. Zurück zum Korrigieren oder trotzdem speichern.",
                 "Show Experiment → <b>Save</b>", "wn_unusual.svg"),
                ("feature", "Änderungsverlauf (Superuser)",
                 "Sehen, wer einen Wert wann geändert hat und was vorher drinstand - für einen Wert oder die ganze "
                 "Serie.",
                 "Show Experiment → Rechtsklick auf einen Wert → <b>Change history…</b>", "wn_history.svg"),
                ("feature", 'Report: zwei Ebenen auf der X-Achse',
                 'Im Report einer Serie kann jedes Diagramm jetzt zwei Ebenen auf der X-Achse zeigen - z.&nbsp;B. <b>Garn</b> (Kurzname) und darunter die <b>Jets</b>, nur die Kombinationen, die wirklich getestet wurden. Die zweite Ebene wählt man in der neuen Liste rechts von X. <b>Yarn</b> und <b>Jet</b> lassen sich auch allein als X wählen.',
                 'Show Experiment → <b>Report</b> → X … › …', None),
                ("h", "Smart Chart"),
                ("feature", "Neuer Smart Chart: Versuche über ihre Eigenschaften finden",
                 "Versuche über <b>alle</b> Serien nach Garn, Jet-Geometrie, Maschineneinstellungen und Laborwerten auswählen - "
                 "z.&nbsp;B. alle Polyester-Versuche mit 70–80 dtex Endtiter und 30–40 Filamenten. <b>+ Add filter</b> "
                 "zeigt, wie sich die Werte verteilen und wie viele Versuche jeder Filter übrig lässt; Zahlenfilter können "
                 "nur ganze Zahlen, alle 0.5 oder angekreuzte Werte behalten. Danach in einem Dashboard zeigen: "
                 "jedes Feld gegen jedes andere - als Punkte, Trendlinien mit R², Mittelwert-Linien, Balken, "
                 "Boxplots, Violins, Histogramme oder Dichte-Karte -, eingefärbt nach Jet, Maschine oder einer Zahl, "
                 "pro Maschine ein kleines Diagramm. ⤢ an einem Diagramm zeigt es gross mit seinen Versuchen "
                 "darunter: Klick auf einen Punkt findet den Versuch, Doppelklick öffnet ihn. Als View speichern "
                 "(auch geteilt), als PDF oder Excel exportieren.",
                 "Sidebar → <b>Smart Chart</b>", "wn_smart_chart.svg"),
                ("feature", 'Ist dieser Vergleich fair?',
                 'Ein farbiger Punkt an jedem Diagramm warnt, wenn sich die verglichenen Gruppen auch in anderen Dingen unterscheiden, die das Ergebnis verändern - z.&nbsp;B. Jet A wurde vor allem auf PES bei 3.5 bar getestet, Jet B auf PA bei 2 bar. Grün, gelb oder rot, mit dem Grund in einem Satz. Klick auf den Punkt zeigt jede Bedingung; <b>Make it fairer</b> behält nur, was alle Gruppen gemeinsam haben. Gewarnt wird auch bei sehr kleinen Gruppen, Gruppen aus einer einzigen Serie und Gruppen in verschiedenen X-Bereichen.',
                 'Smart Chart → farbiger Punkt in der Titelzeile eines Diagramms', "wn_fairness.svg"),
                ("feature", 'Dashboard: eigene Seite bauen, wie in Power BI',
                 'Smart Chart ist jetzt ein Dashboard: eine Seite mit mehreren Visuals nebeneinander. Felder aus <b>Fields</b> - jede Tabelle, von Statimat und Itemat bis DTYoMat, Jet und Garn - in die Ablagen eines Visuals ziehen. Neue Visuals: <b>Matrix</b> (z.&nbsp;B. FP/m pro Jet und Luftdruck, eingefärbt - leere Zellen zeigen, wo Versuche fehlen), <b>Card</b> (eine Zahl) und <b>Table</b>. Klick auf einen Balken, eine Box oder eine Matrix-Zelle, und alle anderen Visuals heben ihn hervor. <b>Slicer</b> wählen Werte für die ganze Seite - als Liste, Dropdown, Knöpfe oder Bereichsregler. Visuals frei platzieren und in der Grösse ziehen, mehrere Seiten (Reiter unten) und Filter nur für eine Seite oder ein Visual. Neu: <b>berechnete Felder</b> per eigener Formel, <b>Zielwerte</b> (grün/rot, Ziellinien), <b>Drill-down</b> Maschine → Jet und <b>Punkte auswählen</b>, um die Seite zu filtern. Dazu: <b>Vorlagen</b> (Jet comparison, Yarn overview, Machine check, Lab overview), <b>PDF</b> einer oder aller Seiten, <b>Excel</b> pro Visual oder Seite, Notizen an Werten, Rückgängig mit <b>Strg+Z</b> und mehrere Visuals auf einmal <b>ausrichten</b> (Strg+Klick, dann ausrichten, gleich gross machen oder verteilen).',
                 'Sidebar → <b>Smart Chart</b>', "wn_dashboard.svg"),
                ("feature", 'Laborstatistik im Dashboard',
                 '<b>Experimente, Versuchsserien oder Versuche</b> zählen - pro Monat, Produktgruppe, Auftragsart, Projekt, Owner oder Labormaschine (<i>Tested on</i>). Das neue Visual <b>Columns</b> zeigt sie gestapelt, nebeneinander oder als 100 %; Monate und Jahre laufen in der richtigen Reihenfolge, leere Monate erscheinen als 0. Am einfachsten mit <b>New</b> → <b>Lab statistics</b> beginnen. Filter auf Monat oder Jahr können jetzt ein Zeitraum sein, der mit dem Kalender mitwandert: <b>This year</b>, <b>Last 12 months</b>, <b>From – to</b> … Dazu der Slicer <b>Year › Month</b>: Jahre zum Aufklappen, darunter die Monate Jan–Dec.',
                 'Smart Chart → <b>New</b> → <b>Lab statistics</b>', "wn_dashboard_stats.svg"),
                ("feature", 'Stacked fields: wie sich Teile zusammensetzen',
                 'Das neue Dashboard-Visual <b>Stacked fields</b> stellt mehrere Zahlenfelder in einer Säule dar, jedes in eigener Farbe - z.&nbsp;B. A-, B- und C-Knoten des DTYoMat pro Versuch, als <b>100 %</b> (Anteil jedes Teils) oder als Werte. Mit dem neuen Feld <b>Trial</b> auf der X-Achse gibt es eine Säule pro Versuch. Als <b>Kombi-Diagramm</b> zeigen Linien auf einer zweiten Achse rechts z.&nbsp;B. FP/m dazu.',
                 'Smart Chart → Visualizations → <b>Stacked fields</b>', "wn_stacked_fields.svg"),
                ("feature", 'Visuals formatieren: Reihenfolge, Top N, Farben, Achsen, Tabellen',
                 'Ein Visual im Dashboard hat jetzt neben <b>Build</b> einen zweiten Reiter <b>Format</b>. Balken und Boxen nach Wert oder Name ordnen und nur die <b>Top 10</b> zeigen (z.&nbsp;B. die besten Jets), <b>Dezimalstellen</b> festlegen, die <b>Werte an die Balken</b> schreiben, die <b>Fehlerbalken</b> an Balken und Mittelwertlinien wählen - Standardabweichung, <b>95 % Vertrauensbereich</b> (sind zwei Jets wirklich verschieden? Überlappen sich die Balken kaum, wohl ja), <b>Min – Max</b> oder aus -, eigene <b>Achsentitel</b> setzen oder ausblenden, festlegen, wo die <b>Y-Achse</b> anfängt und endet, die <b>Legende</b> nach oben, unten oder weg schieben, eine <b>Palette</b> oder eine eigene <b>Farbe pro Wert</b> wählen, Schrift und <b>Cards</b> grösser oder kleiner machen und Rasterlinien ausschalten. <b>Tabellen</b> sortieren per Klick auf die Spaltenüberschrift und bekommen <b>Farbregeln</b> (z.&nbsp;B. FP/m über 100 grün). Ein <b>Dashboard-Thema</b> (Format, wenn nichts ausgewählt ist) setzt Palette, Schriftgrösse, Dezimalstellen … für alle Visuals auf einmal, und <b>Copy format</b> oben auf der Seite gibt einem anderen Visual dasselbe Format (Doppelklick: mehrere, Esc beendet). Jede Änderung ist sofort sichtbar; ein grüner Punkt zeigt, was vom Standard abweicht, <b>Reset</b> stellt es zurück. Das PDF zeigt es genauso.',
                 'Smart Chart → Visual anklicken → Visualizations → <b>Format</b>', "wn_dashboard_format.svg"),
                ("feature", 'Dashboard-PDF, das aussieht wie die Seite',
                 'Das PDF eines Dashboards hat jetzt das Heberlein-Logo, nutzt die ganze Seite, und kein Text läuft mehr über den Rand seiner Box. <b>Slicer</b> werden gedruckt, wie man sie sieht: mit Häkchen, Kacheln, Schieberegler oder Jahren mit ihren Monaten. Diagramme funktionieren auch <b>ohne Internetverbindung</b>.',
                 'Smart Chart → <b>PDF</b>', None),
                ("feature", 'Neue Visuals: Kuchen, Donut, Regelkarte, Radar, Text',
                 'Fünf neue Visuals im Dashboard: <b>Pie</b> und <b>Donut</b> für Anteile (Klick auf ein Stück filtert die Seite), die <b>Regelkarte</b> (Control chart) mit Mittelwert und ±3σ-Grenzen - Punkte ausserhalb rot, lange Folgen auf einer Seite gelb -, das <b>Radar</b>, um Jets, Garne oder Maschinen über mehrere Werte gleichzeitig zu vergleichen, und <b>Text</b> für Überschriften und Kommentare. Alle Visuals haben zudem neue, klarere Symbole.',
                 'Smart Chart → Visualizations', "wn_dashboard_visuals.svg"),
                ("feature", 'Dashboard: Analytics-Linien und Drill-through',
                 'Neuer Reiter <b>Analytics</b> neben Build und Format: Mittelwert, Median, ± 1/2/3 Standardabweichungen, Perzentil, Min/Max, eine feste Linie oder ein Band von - bis (z.&nbsp;B. die Spezifikationsgrenzen) direkt im Diagramm - berechnet aus den Versuchen darin. Und <b>Drill-through</b> wie in Power BI: eine Seite zur Detailseite für z.&nbsp;B. <b>Machine</b> machen (Filters → <b>Drill-through to this page</b>), dann auf einer anderen Seite mit der rechten Maustaste auf den Balken einer Maschine → <b>Drill through</b>. Die Detailseite zeigt nur diese Maschine; <b>← Back</b> führt zurück.',
                 'Smart Chart → Visualizations → <b>Analytics</b> · Rechtsklick auf einen Balken', "wn_dashboard_analytics.svg"),
                ("feature", 'Klicken hebt hervor - der Rest wird grau',
                 'Ein Klick auf einen Balken, eine Säule, ein Kuchenstück oder einen Punkt im Dashboard lässt die anderen Visuals nicht mehr auf diesen Teil springen. Sie behalten alle Versuche und grauen den Rest aus - so sieht man den Teil im Ganzen, z.&nbsp;B. wie viel jeder Säule von Maschine AFK stammt. Auch das angeklickte Visual graut seine anderen Balken aus. Punkte anderer Versuche werden grau, Balken mit Mittelwerten zeigen den Mittelwert der hervorgehobenen Versuche über dem blassen. Cards, Matrix, Tabelle, Radar, Box, Violin und Histogramm filtern weiterhin, Slicer auch. Nochmals klicken hebt es auf. Lieber wie früher? Format ohne Auswahl → <b>Clicks</b> → <i>Filters the other visuals</i>.',
                 'Smart Chart, Dashboards → Balken, Stück oder Punkt anklicken', "wn_click_highlight.svg"),
                ("feature", 'Focus: ein Visual gross, mit seinen Versuchen',
                 'In der Titelzeile eines Visuals auf ⤢ klicken: es füllt die Seite, darunter stehen alle Versuche, aus denen es besteht. Klick auf einen Punkt zeigt seine Zeile, Doppelklick auf eine Zeile öffnet den Versuch in Show Experiment. Klick auf den farbigen Fairness-Punkt zeigt die Details mit <b>Make it fairer</b>. In <b>Format</b> gibt es jetzt auch logarithmische Achsen, eine Form pro Farbe und die Punktgrösse.',
                 'Smart Chart → ⤢ an einem Visual', None),
                ("feature", 'Model: wie die Tabellen zusammenhängen',
                 'Oben links im Dashboard auf <b>Model</b> klicken: in der Mitte der Versuch, rundherum Garn, Jet, Experiment, Zeit und alle Labortabellen, mit ihrer Verknüpfung (1 : n = mehrere Zeilen pro Versuch, gemittelt). Klick auf eine Tabelle zeigt ihre Felder und wie viele Versuche einen Wert haben. Nur zum Lesen - dort lässt sich nichts ändern.',
                 'Smart Chart → <b>Model</b>', "wn_model_view.svg"),
                ("feature", 'Heberlein-Farben als Standard',
                 'Diagramme und Dashboards starten jetzt mit der Palette <b>Heberlein</b>: zuerst Heberlein-Grün und das Dunkelblau aus dem Logo, dann gut unterscheidbare Farben. Die acht Grüntöne gibt es weiterhin als <b>Heberlein green</b>.',
                 'Smart Chart → Visual anklicken → <b>Format</b> → Colours (nichts ausgewählt: für alle Visuals)', None),
                ("feature", 'Seitenleisten breiter oder schmaler',
                 'Im Dashboard den linken Rand von <b>Filters</b>, <b>Visualizations</b> oder <b>Fields</b> ziehen, um sie breiter oder schmaler zu machen - TrippleT merkt es sich. Ein Doppelklick auf den Rand gibt die Standardbreite zurück.',
                 'Sidebar → <b>Smart Chart</b>', None),
                ("feature", 'Dashboards: anschauen und teilen',
                 'Die neue Seite <b>Dashboards</b> zeigt deine eigenen Dashboards und die, die Kollegen für dich freigegeben haben. Hier wird nur geschaut: Slicer, Klick auf Balken zum Filtern, Drill-down, Seiten-Reiter und <b>PDF</b> gehen - versehentlich verändern kann man nichts. Zum Teilen das Dashboard in Smart Chart öffnen und auf <b>Share…</b> klicken: für alle, für einzelne Personen oder für Gruppen (read, write, admin, superuser), je zum <b>Anschauen</b> oder zum <b>Bearbeiten</b>. Teilen oder löschen kannst nur du.',
                 'Sidebar → Tools → <b>Dashboards</b> · Smart Chart → <b>Share…</b>', "wn_dashboards.svg"),
                ("feature", 'Superuser bestimmen, wer welches Tool nutzen darf',
                 'In <b>Manage User → Access…</b> schaltet ein Superuser jedes Tool und jeden Screen ein oder aus - für eine Gruppe (read, write, admin) oder für eine einzelne Person, z.&nbsp;B. Smart Chart für einen Kollegen oder kein Backlog für eine Gruppe. Die Einstellung für eine Person gewinnt über die Gruppe; ohne Einstellung bleibt alles wie bisher. Gesperrte Tools verschwinden ab dem nächsten Login aus der Sidebar.',
                 'Sidebar → Superuser → Manage User → <b>Access…</b>', "wn_feature_access.svg"),
                ("h", "Settings"),
                ("feature", 'Eigene Startseite wählen',
                 'Bestimme, welcher Screen nach dem Login aufgeht - Backlog (wie bisher), All Experiments, Dashboards, Yarn Stock oder ein anderes Tool, das du nutzt. Schaltet ein Superuser dieses Tool für dich aus, öffnet sich stattdessen Backlog.',
                 'Sidebar → Account → <b>Settings</b> → <b>Start screen</b>', "wn_start_screen.svg"),
                ("feature", "Textgrösse fürs ganze Programm",
                 "Normal, Large, Extra large oder Huge - Knöpfe, Menüs, Tabellen und Dialoge wachsen alle mit. Gilt "
                 "nach einem Neustart. Auch Willkommensnachricht und Akzentfarbe werden hier eingestellt.",
                 "Sidebar → Account → <b>Settings</b>", "wn_text_size.svg"),
                ("feature", "Tabellen besser lesbar",
                 "Hoher Kontrast, Fadenkreuz für Zeile und Spalte, Lese-Leiste mit dem Wert in grosser Schrift, "
                 "Warnsymbole und farbenblind-freundliche Farben. Tabellen zoomen mit Strg + Mausrad.",
                 "Sidebar → Account → <b>Settings</b> → Show Experiment tables", "wn_reading.svg"),
                ("h", "Hilfe"),
                ("feature", "Hilfe in drei Sprachen",
                 "Show Experiment, Backlog, Report, Smart Chart, Dashboards, All Experiments, Create Experiment, Manage Yarn und Manage Jets "
                 "haben jetzt eine eigene Hilfe auf Englisch, Deutsch und Spanisch: Schritt-für-Schritt-Antworten "
                 "auf \"Wie mache ich…?\", eine Skizze des Bildschirms und die Regeln. Die Flaggen wechseln die Sprache.",
                 "Runder <b>?</b>-Knopf in diesen Screens", "wn_help.svg"),
                ("feature", "Hilfe-Suche - \"Wo finde ich…?\"",
                 "Die Frage in eigenen Worten eintippen und die passende Hilfe-Seite bekommen - auf Englisch, "
                 "Deutsch oder Spanisch. <b>Take me there</b> öffnet den Screen.",
                 "Sidebar → <b>Help (F1)</b> oder Taste F1", "wn_help_search.svg"),
                ("feature", "Suche in Fresh off the Spool",
                 "Du weisst, dass es eine Funktion gibt, aber nicht seit wann? Ein Wort ins Suchfeld über der "
                 "Versionsliste tippen - gesucht wird in allen Versionen gleichzeitig, auf Englisch, Deutsch und "
                 "Spanisch. Versionen mit Treffern zeigen die Anzahl; ein Klick springt dorthin. Jede Version ist "
                 "jetzt in Reiter nach Bereich aufgeteilt, z.&nbsp;B. <i>Show Experiment (8)</i>.",
                 "Sidebar → Account → <b>Fresh off the Spool</b> → Suchfeld", "wn_whats_new_search.svg"),
                ("feature", "Fresh off the Spool als PDF",
                 "Die Neuheiten einer Version als PDF speichern - zum Ausdrucken oder um sie Kollegen zu schicken. "
                 "Jedes Thema bleibt zusammen auf einer Seite.",
                 "Sidebar → Account → <b>Fresh off the Spool</b> → <b>PDF</b>", "wn_whats_new_pdf.svg"),
                ("h", "Backlog und All Experiments"),
                ("feature", "Mehrere Karten auf einmal verschieben",
                 "<b>Strg</b> gedrückt halten und die Karten anklicken (oder <b>Umschalt+Klick</b> für einen ganzen "
                 "Bereich), dann eine davon ziehen - alle markierten Karten wandern mit, z. B. von <i>To Be "
                 "Cleaned</i> nach <i>Archived</i>. TrippleT fragt einmal nach und sagt, falls eine Karte nicht "
                 "verschoben werden durfte.",
                 "Backlog → Karten mit <b>Strg+Klick</b> markieren → ziehen", "wn_backlog_multi_move.svg"),
                ("feature", "Backlog auf breiten Bildschirmen",
                 "Auf grossen Monitoren stehen alle vier Spalten nebeneinander und nutzen die volle Höhe.",
                 "Backlog", "wn_wide_backlog.svg"),
                ("feature", "Papierkorb",
                 "Eine gelöschte Versuchsserie lässt sich 90 Tage lang wiederherstellen. Löschen darf, wer die Serie "
                 "im Backlog verschieben darf (in To Be Cleaned nur Superuser).",
                 "Sidebar → Superuser → <b>Recycle Bin</b>", "wn_recycle_bin.svg"),
                ("feature", "Im Papierkorb nachschauen",
                 "Unsicher, was in einer gelöschten Serie steckt? Doppelklick darauf: Sie öffnet sich schreibgeschützt "
                 "in Show Experiment. Im gelben Balken wählst du <b>Restore for good</b>, <b>Back to Recycle Bin</b> "
                 "oder <b>Delete permanently</b>. Tab schliessen legt sie zurück - mit dem ursprünglichen Löschdatum.",
                 "Sidebar → Superuser → <b>Recycle Bin</b> → Doppelklick auf eine Serie", "wn_recycle_preview.svg"),
                ("feature", "All Experiments nutzt das ganze Fenster",
                 "Die Liste füllt die volle Breite und Höhe des Fensters - die letzten Spalten sind ohne seitliches "
                 "Scrollen sichtbar - und wird auf grossen Bildschirmen grösser dargestellt.",
                 "All Experiments", "wn_all_experiments.svg"),
                ("h", "Garne"),
                ("feature", "Die Farbe eines Garns sehen",
                 "Ein kleines Kästchen vor dem Garnnamen zeigt seine Farbe - schwarz, weiss, beige, grau, natur. "
                 "Mit der Maus darüber steht die Farbe auch als Text. Man kann auch nach Farbe suchen, z. B. "
                 "<i>black</i>. Die Farbe kommt aus dem Feld <i>Colour</i> des Garns (<b>Manage Yarn</b>).",
                 "Dialog Yarns…, Create Experiment, Yarn Stock, Manage Yarn, Reassign Yarn, Show Experiment "
                 "(Zeile Ply)", "wn_yarn_colour.svg"),
                ("h", "Yarn Stock"),
                ("feature", "Lagerstatus pro Garn",
                 "Die Ampel zeigt jetzt jedes Garn als Ganzes: alle Batches am Lager zusammen gegen den "
                 "Mindestbestand. Aufgebrauchte Batches verschwinden aus der Übersicht, Meldungen kommen einmal pro "
                 "Garn. Den Mindestbestand ändern dürfen nur Superuser.",
                 "Yarn Stock → Übersicht", "wn_stock_status.svg"),
                ("feature", "Neue Spulen - direkt zu den neuen Spulen und in die Etiketten-Liste",
                 "<b>New spool(s)</b> beginnt mit leerer Auswahl und springt danach direkt zu den neuen Spulen. "
                 "Diese kommen automatisch in die Label queue (Häkchen im Dialog).",
                 "Yarn Stock → <b>New spool(s)</b>", "wn_new_spools.svg"),
                ("feature", "Inventur - Platz für Platz",
                 "Ein Superuser startet eine Inventur-Runde (und kann einzelne Plätze auslassen). Jeder Lagerplatz "
                 "ist eine Kachel: grau = offen, grün = alles stimmt, orange = Abweichungen. Draufklicken und die "
                 "Spulen scannen (kein Etikett? in der Liste doppelklicken). <b>Results</b> zeigt, was wo gefunden wurde, als Excel exportierbar. Spulen an einem "
                 "anderen Platz werden sofort umgelagert, fehlende erst beim Abschluss ausgebucht - nach Rückfrage.",
                 "Yarn Stock → Rack lookup → <b>Stock take…</b>", "wn_stock_take.svg"),
                ("feature", "Spulen-Verlauf",
                 "Jede Änderung an einer Spule wird festgehalten: angelegt, geändert, umgelagert, ausgebucht, "
                 "Inventur. Ohne Auswahl sieht man die ganze Batch, auch aufgebrauchte Spulen.",
                 "Yarn Stock → <b>History…</b>", "wn_spool_history.svg"),
                ("feature", "Etiketten scannen, Änderungen nicht verlieren",
                 "In <i>Go to spool #</i> lässt sich das Spulenetikett scannen statt die Nummer zu tippen. Und Yarn "
                 "Stock fragt jetzt nach, bevor ungespeicherte Spulen-Änderungen verloren gehen. Hilfe in drei "
                 "Sprachen: runder Knopf oben rechts.",
                 "Yarn Stock → <b>Go to spool #</b>", None),
                ("h", "Allgemein"),
                ("feature", "Fresh off the Spool: Neues in TrippleT",
                 "Alle Neuerungen jeder Version an einem Ort: ein Reiter pro Bereich, durchsuchbar und als PDF. "
                 "Öffnet sich nach einer neuen Version einmal von selbst - und jederzeit in der Sidebar.",
                 "Sidebar → Account → <b>Fresh off the Spool</b>", "fresh_off_the_spool.png"),
                ("feature", "Zuletzt geöffnete Serien",
                 "Die zuletzt geöffneten Serien sind einen Klick entfernt: <b>Recent</b> in der Sidebar (unten, über Account). "
                 "Klick öffnet sie, <b>Strg+Klick</b> in einem neuen Tab. Die Liste folgt dir auf jeden PC.",
                 "Sidebar → <b>Recent</b>", None),
                ("feature", "Athena antwortet in deiner Sprache",
                 "Athena und der Lab Assistant antworten jetzt in der Sprache, in der du fragst - Englisch, Deutsch, "
                 "Spanisch, … Ohne Frage (z.&nbsp;B. die automatische Analyse) kommt die Antwort auf Englisch.",
                 "Show Experiment → Athena, Lab Assistant", None),
                ("feature", "Fehlermeldungen, die weiterhelfen",
                 "Geht etwas schief, sagt TrippleT jetzt in Alltagssprache, was nicht geklappt hat, warum und was du "
                 "tun kannst - z.&nbsp;B. \"Die Datei ist in einem anderen Programm offen - schliessen (z.&nbsp;B. in "
                 "Excel) und nochmals versuchen.\" Der technische Text steht unter <b>Show Details</b>, zum "
                 "Weiterleiten an den Admin.",
                 "Ganzes Programm", None),
                ("feature", "Alle Texte auf Englisch",
                 "Meldungen, Knöpfe, Menüs und Statustexte, die noch deutsch waren, sind jetzt überall englisch - "
                 "z.&nbsp;B. heisst das Rechtsklick-Menü im Backlog <b>Reassign yarn…</b>. Laborbegriffe wie Kurzhocker "
                 "oder Langwelle bleiben, wie sie sind.",
                 "Ganzes Programm", None),
            ],
            # ═══════════════════════════════ ES ═══════════════════════════════
            "es": [
                ("h", "Show Experiment"),
                ("feature", "Los hilos de la serie en una tabla",
                 "<b>Yarns…</b> muestra todos los plies de la serie con su hilo y todos los ensayos. Un clic en el "
                 "hilo lo cambia para todo el ply; para encontrarlo escribe parte del nombre, p.&nbsp;ej. "
                 "<i>167 dty</i>. Un clic en una celda activa o quita el ply en ese ensayo; escribe 1-9 para el "
                 "número de cabos. <b>+ Add ply</b> añade un ply a todos los ensayos. Las celdas cambiadas están en "
                 "amarillo y nada se guarda antes de <b>Apply</b>.",
                 "Show Experiment → Machine Data → <b>Yarns…</b> (o clic derecho en la fila Ply)",
                 "wn_series_yarns.svg"),
                ("feature", "¿Dónde están mis bobinas?",
                 "Una pequeña bobina detrás de cada ply en la línea de material lo indica de un vistazo: bobina verde "
                 "= hay hilo en almacén, tubo tachado = no hay nada en almacén. Un clic en el hilo o en la bobina verde muestra "
                 "todas las bobinas en almacén por ubicación, con lote, peso y color del tubo. Las bobinas asignadas "
                 "a esta serie aparecen en negrita. <b>Open in Yarn Stock</b> lleva directamente al hilo.",
                 "Show Experiment → línea de material → hilo o símbolo de bobina", "wn_spool_locations.svg"),
                ("feature", "Notas en los valores",
                 "Anota por qué un valor es así, justo donde está: clic derecho en un valor → <b>Add note…</b>, "
                 "p.&nbsp;ej. <i>La bobina tenía nudos, medido de nuevo</i>. Un pequeño triángulo violeta marca "
                 "la celda; al señalarla se ve la nota con nombre y fecha. Clic derecho en un número de ensayo "
                 "para una nota sobre todo el ensayo. La pestaña <b>Notes</b> lista todas las notas de la serie; "
                 "doble clic salta al valor. Todos pueden escribir notas. En el <b>Report</b> de una serie, el botón "
                 "<b>Notes</b> las muestra como borde violeta con la nota en la descripción emergente; en el PDF "
                 "solo aparecen si al exportar marcas <i>Include notes on values</i>. En el dashboard del Smart "
                 "Chart, marque <i>Show notes on values</i> en un visual Points.",
                 "Show Experiment → clic derecho en un valor → <b>Add note…</b>", "wn_cell_notes.svg"),
                ("feature", "Muestras de referencia",
                 "Añade la bobina original de un cliente como comparación. Aparece como columna <i>Ref</i> "
                 "resaltada y como línea horizontal en el informe, y nunca cuenta como ensayo.",
                 "Show Experiment → Machine Data → <b>+ Ref</b>", "wn_reference.svg"),
                ("feature", "Copiar ensayos - con cambios",
                 "Elige qué ensayos, cuántas veces y en qué orden, y cambia valores (p.&nbsp;ej. presión de aire, "
                 "tobera, OF Core/Effect) antes de copiar. Los comentarios y las tensiones antes/después del jet no "
                 "se copian: las copias empiezan con ellos vacíos.",
                 "Show Experiment → Machine Data → <b>Copy trials</b>", "wn_copy_trials.svg"),
                ("feature", "D/Y Ratio (T2/T1)",
                 "Se calcula automáticamente a partir de T1 y T2 y se muestra justo debajo de T2 Tension en "
                 "máquinas DTY.",
                 "Show Experiment → Machine Data", "wn_dy_ratio.svg"),
                ("feature", "Introducir datos más rápido, como en Excel",
                 "Escribe un valor y pulsa <b>Enter</b>: pasas a la celda de abajo, listo para el siguiente valor "
                 "(<b>Mayús+Enter</b> sube). Haz clic en una celda (o selecciona varias) y pulsa <b>Supr</b> para "
                 "vaciarlas, sin doble clic. Guarda con <b>Save</b> o <b>Ctrl+S</b>; en lugar de un mensaje "
                 "\"Saved\" que cerrar, el amarillo desaparece y en el centro aparece un momento una marca verde; "
                 "puedes seguir escribiendo enseguida.",
                 "Show Experiment → cualquier tabla", None),
                ("feature", "Deshacer con Ctrl+Z",
                 "¿Valor equivocado, pegado en el sitio incorrecto o borrado de más? <b>Ctrl+Z</b> lo deshace paso a "
                 "paso y <b>Ctrl+Y</b> lo rehace, mientras no hayas guardado.",
                 "Show Experiment → cualquier tabla", None),
                ("feature", "De vuelta en tu pestaña",
                 "Una serie se abre en la pestaña que usaste la última vez con ella, p.&nbsp;ej. <i>Statimat M</i> "
                 "en lugar de siempre <i>Machine Data</i>.",
                 "Show Experiment", None),
                ("feature", "Ocultar filas que no necesitas",
                 "Clic derecho en el nombre de un parámetro → <b>Hide row</b>. Una línea azul indica dónde faltan "
                 "filas; un clic en ella o <b>n rows hidden</b> las vuelve a mostrar. Se recuerda por máquina.",
                 "Show Experiment → Machine Data → clic derecho en el nombre del parámetro", "wn_hide_rows.svg"),
                ("feature", "Ver lo que aún no está guardado",
                 "Las celdas cambiadas quedan en amarillo hasta que guardas (<b>Save</b> o <b>Ctrl+S</b>). El botón "
                 "muestra cuántas, p.&nbsp;ej. "
                 "<b>Save (3)</b>, y la pestaña recibe un punto. Al cerrar una pestaña o el programa con cambios sin "
                 "guardar, ahora se pregunta antes; hasta ahora se perdían sin aviso.",
                 "Show Experiment", "wn_unsaved.svg"),
                ("feature", "Control de errores al guardar",
                 "Los ajustes de máquina muy fuera de lo habitual para esta máquina (p.&nbsp;ej. 35 en vez de "
                 "3.5 bar) se muestran antes de guardar. Puedes volver a corregir o guardar igualmente.",
                 "Show Experiment → <b>Save</b>", "wn_unusual.svg"),
                ("feature", "Historial de cambios (superusuarios)",
                 "Ver quién cambió un valor, cuándo y qué había antes - para un valor o toda la serie.",
                 "Show Experiment → clic derecho en un valor → <b>Change history…</b>", "wn_history.svg"),
                ("feature", 'Informe: dos niveles en el eje X',
                 'En el informe de una serie cada gráfico puede mostrar ahora dos niveles en el eje X, p.&nbsp;ej. el <b>hilo</b> (nombre corto) y debajo los <b>jets</b>, solo las combinaciones realmente ensayadas. El segundo nivel se elige en la nueva lista a la derecha de X. <b>Yarn</b> y <b>Jet</b> también se pueden elegir solos como X.',
                 'Show Experiment → <b>Report</b> → X … › …', None),
                ("h", "Smart Chart"),
                ("feature", "Nuevo Smart Chart: encontrar ensayos por sus propiedades",
                 "Elige ensayos de <b>todas</b> las series por hilo, geometría del jet, ajustes de máquina y resultados de laboratorio, "
                 "p.&nbsp;ej. todos los ensayos de poliéster con 70–80 dtex de título final y 30–40 filamentos. "
                 "<b>+ Add filter</b> muestra cómo se reparten los valores y cuántos ensayos deja cada filtro; los filtros "
                 "numéricos pueden quedarse solo con enteros, cada 0.5 o los valores marcados. Después muéstralos "
                 "en un dashboard: cualquier campo frente a otro (puntos, rectas de tendencia con R², líneas de "
                 "media, barras, box plots, violines, histogramas o mapa de densidad), coloreados por jet, máquina o "
                 "un número, un gráfico pequeño por máquina. ⤢ en un gráfico lo muestra en grande con sus ensayos "
                 "debajo: clic en un punto encuentra el ensayo, doble clic lo abre. Guárdalo como vista (también "
                 "compartida), exporta a PDF o Excel.",
                 "Barra lateral → <b>Smart Chart</b>", "wn_smart_chart.svg"),
                ("feature", '¿Es justa esta comparación?',
                 'Un punto de color en cada gráfico avisa cuando los grupos que comparas también se diferencian en otras cosas que cambian el resultado, p.&nbsp;ej. el jet A se probó sobre todo con PES a 3.5 bar y el jet B con PA a 2 bar. Verde, amarillo o rojo, con el motivo en una frase. Un clic en el punto muestra cada condición; <b>Make it fairer</b> deja solo lo que todos los grupos tienen en común. También avisa de grupos muy pequeños, grupos de una sola serie y grupos en rangos de X distintos.',
                 'Smart Chart → punto de color en la barra de título de un gráfico', "wn_fairness.svg"),
                ("feature", 'Dashboard: crea tu propia página, como en Power BI',
                 'Smart Chart es ahora un dashboard: una página con varios visuales. Arrastra campos desde <b>Fields</b> (todas las tablas, de Statimat e Itemat a DTYoMat, jet e hilo) a los huecos de un visual. Visuales nuevos: <b>Matrix</b> (p.&nbsp;ej. FP/m por jet y presión, coloreado; las celdas vacías muestran dónde faltan ensayos), <b>Card</b> (un número) y <b>Table</b>. Haz clic en una barra, caja o celda y todos los demás visuales la resaltan. Los <b>slicers</b> eligen valores para toda la página: lista, desplegable, botones o rango. Coloca y redimensiona los visuales libremente, usa varias páginas (pestañas abajo) y filtros solo para una página o un visual. Nuevo: <b>campos calculados</b> con tu propia fórmula, <b>objetivos</b> (verde/rojo, líneas de objetivo), <b>profundizar</b> máquina → jet y <b>seleccionar puntos</b> para filtrar la página. Además: <b>plantillas</b> (Jet comparison, Yarn overview, Machine check, Lab overview), <b>PDF</b> de una o todas las páginas, <b>Excel</b> por visual o página, notas en los valores, deshacer con <b>Ctrl+Z</b> y <b>alinear</b> varios visuales a la vez (Ctrl+clic, luego alinear, mismo tamaño o distribuir).',
                 'Sidebar → <b>Smart Chart</b>', "wn_dashboard.svg"),
                ("feature", 'Estadísticas del laboratorio en el dashboard',
                 'Cuenta <b>experimentos, series o ensayos</b> por mes, grupo de producto, tipo de pedido, proyecto, responsable o máquina de laboratorio (<i>Tested on</i>). El nuevo visual <b>Columns</b> los muestra apilados, lado a lado o al 100 %; meses y años van en orden y los meses vacíos aparecen como 0. Empieza con <b>New</b> → <b>Lab statistics</b>. Los filtros por mes o año pueden ser ahora un periodo que avanza con el calendario: <b>This year</b>, <b>Last 12 months</b>, <b>From – to</b> … Y el slicer <b>Year › Month</b>: años desplegables con los meses Jan–Dec debajo.',
                 'Smart Chart → <b>New</b> → <b>Lab statistics</b>', "wn_dashboard_stats.svg"),
                ("feature", 'Stacked fields: cómo se reparten las partes',
                 'El nuevo visual <b>Stacked fields</b> muestra varios campos numéricos en una columna, cada uno con su color, p.&nbsp;ej. nudos A, B y C del DTYoMat por ensayo, al <b>100 %</b> (la parte de cada uno) o como valores. Con el nuevo campo <b>Trial</b> en el eje X hay una columna por ensayo. Como <b>gráfico combinado</b>, unas líneas en un segundo eje a la derecha muestran p.&nbsp;ej. FP/m.',
                 'Smart Chart → Visualizations → <b>Stacked fields</b>', "wn_stacked_fields.svg"),
                ("feature", 'Formato de visuales: orden, Top N, colores, ejes, tablas',
                 'Un visual del dashboard tiene ahora junto a <b>Build</b> una segunda pestaña <b>Format</b>. Ordene barras y cajas por valor o por nombre y muestre solo el <b>top 10</b> (p.&nbsp;ej. los mejores jets), fije los <b>decimales</b>, ponga los <b>valores en las barras</b>, elija las <b>barras de error</b> en barras y líneas de medias - desviación estándar, <b>confianza del 95 %</b> (¿dos jets son realmente distintos? si las barras apenas se solapan, probablemente sí), <b>mín – máx</b> o ninguna -, escriba sus propios <b>títulos de eje</b> u ocúltelos, fije dónde empieza y termina el <b>eje Y</b>, mueva la <b>leyenda</b> arriba, abajo o quítela, elija una <b>paleta</b> o su propio <b>color por valor</b>, haga el texto y las <b>tarjetas</b> más grandes o pequeños y quite las líneas de cuadrícula. Las <b>tablas</b> se ordenan con un clic en el título de una columna y tienen <b>reglas de color</b> (p.&nbsp;ej. FP/m por encima de 100 en verde). Un <b>tema del dashboard</b> (Format sin nada seleccionado) fija paleta, tamaño del texto, decimales … para todos los visuales a la vez, y <b>Copy format</b> arriba en la página da a otro visual el mismo formato (doble clic: varios, Esc termina). Cada cambio se ve enseguida; un punto verde marca lo que difiere del estándar, <b>Reset</b> lo restablece. El PDF lo muestra igual.',
                 'Smart Chart → clic en un visual → Visualizations → <b>Format</b>', "wn_dashboard_format.svg"),
                ("feature", 'PDF del dashboard igual que la página',
                 'El PDF de un dashboard lleva ahora el logo de Heberlein, usa toda la página y ningún texto se sale de su recuadro. Los <b>slicers</b> se imprimen como se ven: con casillas, mosaicos, el control deslizante o los años con sus meses. Los gráficos funcionan también <b>sin conexión a internet</b>.',
                 'Smart Chart → <b>PDF</b>', None),
                ("feature", 'Nuevos visuales: tarta, dónut, gráfico de control, radar, texto',
                 'Cinco visuales nuevos en el dashboard: <b>Pie</b> y <b>Donut</b> para proporciones (un clic en una porción filtra la página), el <b>gráfico de control</b> con media y límites ±3σ - puntos fuera en rojo, rachas largas en un lado en ámbar -, el <b>Radar</b> para comparar jets, hilos o máquinas en varios valores a la vez, y <b>Text</b> para títulos y comentarios. Todos los visuales tienen además iconos nuevos y más claros.',
                 'Smart Chart → Visualizations', "wn_dashboard_visuals.svg"),
                ("feature", 'Dashboard: líneas de análisis y drill-through',
                 'Nueva pestaña <b>Analytics</b> junto a Build y Format: media, mediana, ± 1/2/3 desviaciones estándar, percentil, mín./máx., una línea fija o una banda de - a (p.&nbsp;ej. tus límites de especificación) directamente en el gráfico, calculadas con sus ensayos. Y <b>drill-through</b> como en Power BI: convierte una página en la página de detalle de p.&nbsp;ej. <b>Machine</b> (Filters → <b>Drill-through to this page</b>) y luego, en otra página, clic derecho en la barra de una máquina → <b>Drill through</b>. La página de detalle muestra solo esa máquina; <b>← Back</b> te devuelve.',
                 'Smart Chart → Visualizations → <b>Analytics</b> · clic derecho en una barra', "wn_dashboard_analytics.svg"),
                ("feature", 'Un clic resalta - el resto se vuelve gris',
                 'Un clic en una barra, una columna, un sector o un punto del dashboard ya no hace que los demás visuales muestren solo esa parte. Mantienen todos sus ensayos y ponen el resto en gris, así se ve la parte dentro del todo - p.&nbsp;ej. cuánto de cada columna viene de la máquina AFK. El visual pulsado también pone en gris sus otras barras. Los puntos de otros ensayos se vuelven grises, las barras de medias muestran la media de los ensayos resaltados sobre la pálida. Tarjetas, matriz, tabla, radar, caja, violín e histograma siguen filtrando, los slicers también. Otro clic lo deshace. ¿Prefiere lo de antes? Format sin nada seleccionado → <b>Clicks</b> → <i>Filters the other visuals</i>.',
                 'Smart Chart, Dashboards → clic en una barra, sector o punto', "wn_click_highlight.svg"),
                ("feature", 'Focus: un visual en grande, con sus ensayos',
                 'Haga clic en ⤢ en la barra de título de un visual: ocupa la página y debajo aparecen todos los ensayos de los que se compone. Un clic en un punto muestra su fila, un doble clic en una fila abre el ensayo en Show Experiment. Un clic en el punto de color de equidad muestra los detalles con <b>Make it fairer</b>. En <b>Format</b> hay ahora también ejes logarítmicos, una forma por color y el tamaño de los puntos.',
                 'Smart Chart → ⤢ en un visual', None),
                ("feature", 'Model: cómo se relacionan las tablas',
                 'Haga clic en <b>Model</b> arriba a la izquierda del dashboard: en el centro el ensayo, alrededor hilo, jet, experimento, tiempo y todas las tablas de laboratorio, con su relación (1 : n = varias filas por ensayo, promediadas). Un clic en una tabla muestra sus campos y cuántos ensayos tienen un valor. Solo lectura: allí no se puede cambiar nada.',
                 'Smart Chart → <b>Model</b>', "wn_model_view.svg"),
                ("feature", 'Colores Heberlein como estándar',
                 'Los gráficos y dashboards empiezan ahora con la paleta <b>Heberlein</b>: primero el verde Heberlein y el azul oscuro del logo, luego colores fáciles de distinguir. Los ocho verdes siguen disponibles como <b>Heberlein green</b>.',
                 'Smart Chart → clic en un visual → <b>Format</b> → Colours (nada seleccionado: para todos los visuales)', None),
                ("feature", 'Paneles laterales más anchos o estrechos',
                 'En el dashboard, arrastre el borde izquierdo de <b>Filters</b>, <b>Visualizations</b> o <b>Fields</b> para hacerlo más ancho o estrecho; TrippleT lo recuerda. Un doble clic en el borde vuelve al ancho estándar.',
                 'Sidebar → <b>Smart Chart</b>', None),
                ("feature", 'Dashboards: verlos y compartirlos',
                 'La nueva página <b>Dashboards</b> muestra tus dashboards y los que tus compañeros compartieron contigo. Aquí solo se mira: funcionan los slicers, el clic en barras para filtrar, el drill-down, las pestañas y el <b>PDF</b>; nada se cambia por error. Para compartir tu dashboard, ábrelo en Smart Chart y haz clic en <b>Share…</b>: con todos, con personas o con grupos (read, write, admin, superuser), cada uno para <b>ver</b> o para <b>editar</b>. Solo tú puedes compartirlo o borrarlo.',
                 'Sidebar → Tools → <b>Dashboards</b> · Smart Chart → <b>Share…</b>', "wn_dashboards.svg"),
                ("feature", 'Los superusuarios deciden quién usa qué herramienta',
                 'En <b>Manage User → Access…</b> un superusuario activa o desactiva cada herramienta y pantalla, para un grupo (read, write, admin) o para una persona, p.&nbsp;ej. Smart Chart para un compañero o sin Backlog para un grupo. El ajuste de una persona tiene prioridad sobre el del grupo; sin ajustes todo queda como antes. Las herramientas bloqueadas desaparecen del menú lateral desde el siguiente inicio de sesión.',
                 'Sidebar → Superuser → Manage User → <b>Access…</b>', "wn_feature_access.svg"),
                ("h", "Settings"),
                ("feature", 'Elige tu pantalla de inicio',
                 'Decide qué pantalla se abre tras iniciar sesión: Backlog (como antes), All Experiments, Dashboards, Yarn Stock u otra herramienta que uses. Si un superusuario te desactiva esa herramienta, se abre Backlog.',
                 'Sidebar → Account → <b>Settings</b> → <b>Start screen</b>', "wn_start_screen.svg"),
                ("feature", "Tamaño del texto para todo el programa",
                 "Normal, Large, Extra large o Huge - botones, menús, tablas y diálogos crecen. Se aplica tras "
                 "reiniciar. Aquí también se ajustan el mensaje de bienvenida y el color de acento.",
                 "Barra lateral → Account → <b>Settings</b>", "wn_text_size.svg"),
                ("feature", "Tablas más fáciles de leer",
                 "Alto contraste, cruz de lectura para fila y columna, barra de lectura con el valor en letra "
                 "grande, símbolos de aviso y colores aptos para daltónicos. Zoom de tablas con Ctrl + rueda.",
                 "Barra lateral → Account → <b>Settings</b> → Show Experiment tables", "wn_reading.svg"),
                ("h", "Ayuda"),
                ("feature", "Ayuda en tres idiomas",
                 "Show Experiment, Backlog, Report, Smart Chart, Dashboards, All Experiments, Create Experiment, Manage Yarn y Manage Jets "
                 "tienen ahora su propia ayuda en inglés, alemán y español: respuestas paso a paso a \"¿Cómo hago…?\", "
                 "un esquema de la pantalla y las reglas. Las banderas cambian el idioma.",
                 "Botón redondo <b>?</b> en estas pantallas", "wn_help.svg"),
                ("feature", "Búsqueda en la ayuda - \"¿Dónde encuentro…?\"",
                 "Escribe tu pregunta con tus propias palabras y obtén la página de ayuda adecuada, en inglés, alemán "
                 "o español. <b>Take me there</b> abre la pantalla.",
                 "Barra lateral → <b>Help (F1)</b> o la tecla F1", "wn_help_search.svg"),
                ("feature", "Buscar en Fresh off the Spool",
                 "¿Sabes que existe una función pero no desde cuándo? Escribe una palabra en el campo de búsqueda "
                 "encima de la lista de versiones: se busca en todas las versiones a la vez, en inglés, alemán y "
                 "español. Las versiones con resultados muestran cuántos; un clic salta a ellos. Cada versión se "
                 "divide ahora en pestañas por área, p.&nbsp;ej. <i>Show Experiment (8)</i>.",
                 "Barra lateral → Account → <b>Fresh off the Spool</b> → campo de búsqueda", "wn_whats_new_search.svg"),
                ("feature", "Fresh off the Spool en PDF",
                 "Guarda las novedades de una versión como PDF, para imprimirlas o enviarlas a compañeros. Cada "
                 "tema queda junto en una sola página.",
                 "Barra lateral → Account → <b>Fresh off the Spool</b> → <b>PDF</b>", "wn_whats_new_pdf.svg"),
                ("h", "Backlog y All Experiments"),
                ("feature", "Mover varias tarjetas a la vez",
                 "Mantén <b>Ctrl</b> y haz clic en las tarjetas (o <b>Mayús+clic</b> para un rango), luego arrastra "
                 "una de ellas: todas las marcadas se mueven juntas, p. ej. de <i>To Be Cleaned</i> a "
                 "<i>Archived</i>. TrippleT pregunta una vez y avisa si alguna tarjeta no se podía mover.",
                 "Backlog → <b>Ctrl+clic</b> en las tarjetas → arrastrar", "wn_backlog_multi_move.svg"),
                ("feature", "Backlog en pantallas anchas",
                 "En monitores grandes las cuatro columnas se muestran una al lado de otra con toda la altura.",
                 "Backlog", "wn_wide_backlog.svg"),
                ("feature", "Papelera",
                 "Una serie de ensayos borrada se puede recuperar durante 90 días. Puede borrar quien puede mover la "
                 "serie en el Backlog (en To Be Cleaned solo superusuarios).",
                 "Barra lateral → Superuser → <b>Recycle Bin</b>", "wn_recycle_bin.svg"),
                ("feature", "Mirar dentro de la papelera",
                 "¿No sabes qué contiene una serie borrada? Haz doble clic: se abre en Show Experiment solo para "
                 "lectura. En la barra amarilla eliges <b>Restore for good</b>, <b>Back to Recycle Bin</b> o "
                 "<b>Delete permanently</b>. Cerrar la pestaña la devuelve a la papelera, con su fecha de borrado "
                 "original.",
                 "Barra lateral → Superuser → <b>Recycle Bin</b> → doble clic en una serie", "wn_recycle_preview.svg"),
                ("feature", "All Experiments usa toda la ventana",
                 "La lista ocupa todo el ancho y alto de la ventana - las últimas columnas se ven sin desplazarse "
                 "hacia los lados - y se muestra más grande en pantallas grandes.",
                 "All Experiments", "wn_all_experiments.svg"),
                ("h", "Hilos"),
                ("feature", "Ver el color de un hilo",
                 "Un pequeño cuadrado delante del nombre del hilo muestra su color - negro, blanco, beige, gris, "
                 "natural. Al pasar el ratón por encima se lee el color. También se puede buscar por color, p. ej. "
                 "<i>black</i>. El color viene del campo <i>Colour</i> del hilo (<b>Manage Yarn</b>).",
                 "Diálogo Yarns…, Create Experiment, Yarn Stock, Manage Yarn, Reassign Yarn, Show Experiment "
                 "(fila Ply)", "wn_yarn_colour.svg"),
                ("h", "Yarn Stock"),
                ("feature", "Estado del stock por hilo",
                 "El semáforo muestra ahora cada hilo en conjunto: todos sus lotes en stock frente al stock mínimo. "
                 "Los lotes agotados desaparecen de la vista general y los avisos llegan una vez por hilo. Solo los "
                 "superusuarios pueden cambiar el stock mínimo.",
                 "Yarn Stock → vista general", "wn_stock_status.svg"),
                ("feature", "Bobinas nuevas - directamente a las nuevas y a la cola de etiquetas",
                 "<b>New spool(s)</b> empieza sin selección y después salta directamente a las bobinas nuevas. "
                 "Estas pasan automáticamente a la cola de etiquetas (casilla en el diálogo).",
                 "Yarn Stock → <b>New spool(s)</b>", "wn_new_spools.svg"),
                ("feature", "Inventario - ubicación por ubicación",
                 "Un superusuario inicia una ronda de inventario (y puede excluir ubicaciones). Cada ubicación es una "
                 "casilla: gris = pendiente, verde = todo correcto, naranja = diferencias. Haz clic en una y escanea "
                 "sus bobinas (¿sin etiqueta? doble clic en la lista). <b>Results</b> muestra qué se encontró dónde, exportable a Excel. Las bobinas en otro "
                 "lugar se reubican al momento; las que faltan solo se dan de baja al terminar, tras preguntar.",
                 "Yarn Stock → Rack lookup → <b>Stock take…</b>", "wn_stock_take.svg"),
                ("feature", "Historial de bobinas",
                 "Se registra cada cambio de una bobina: creada, cambiada, reubicada, dada de baja, inventario. Sin "
                 "selección se ve todo el lote, incluidas las bobinas agotadas.",
                 "Yarn Stock → <b>History…</b>", "wn_spool_history.svg"),
                ("feature", "Escanear etiquetas, no perder cambios",
                 "En <i>Go to spool #</i> puedes escanear la etiqueta en vez de escribir el número. Y Yarn Stock "
                 "pregunta ahora antes de perder cambios no guardados. Ayuda en tres idiomas: botón redondo arriba "
                 "a la derecha.",
                 "Yarn Stock → <b>Go to spool #</b>", None),
                ("h", "General"),
                ("feature", "Fresh off the Spool: novedades de TrippleT",
                 "Todas las novedades de cada versión en un solo lugar: una pestaña por área, con búsqueda y en PDF. "
                 "Se abre sola una vez tras cada nueva versión, y en cualquier momento desde la barra lateral.",
                 "Barra lateral → Account → <b>Fresh off the Spool</b>", "fresh_off_the_spool.png"),
                ("feature", "Series recientes",
                 "Las últimas series que abriste están a un clic: <b>Recent</b> en la barra lateral (abajo, encima de Account). "
                 "Un clic la abre, <b>Ctrl+clic</b> en una pestaña nueva. La lista te acompaña en cualquier PC.",
                 "Barra lateral → <b>Recent</b>", None),
                ("feature", "Athena responde en tu idioma",
                 "Athena y el Lab Assistant responden ahora en el idioma en que preguntas: inglés, alemán, español… "
                 "Sin pregunta (p.&nbsp;ej. el análisis automático) la respuesta es en inglés.",
                 "Show Experiment → Athena, Lab Assistant", None),
                ("feature", "Mensajes de error que ayudan",
                 "Cuando algo falla, TrippleT dice ahora con palabras sencillas qué no funcionó, por qué y qué puedes "
                 "hacer - p.&nbsp;ej. \"El archivo está abierto en otro programa: ciérralo (p.&nbsp;ej. en Excel) y "
                 "vuelve a intentarlo.\" El texto técnico está en <b>Show Details</b>, para enviarlo al administrador.",
                 "Todo el programa", None),
                ("feature", "Todos los textos en inglés",
                 "Los mensajes, botones, menús y textos de estado que aún estaban en alemán ahora están en inglés en "
                 "todas partes - p.&nbsp;ej. el menú contextual del Backlog dice <b>Reassign yarn…</b>. Los términos de "
                 "laboratorio como Kurzhocker o Langwelle se mantienen.",
                 "Todo el programa", None),
            ],
        },
    },
]

# "Fresh off the Spool" = the name of the release notes magazine (2026-10-16,
# before: "What's new"); English in every language like the button names.
WINDOW_TITLE = {"en": "Fresh off the Spool", "de": "Fresh off the Spool", "es": "Fresh off the Spool"}
SUBTITLE = {"en": "What's new in TrippleT", "de": "Neues in TrippleT", "es": "Novedades de TrippleT"}
VERSIONS_TITLE = {"en": "Versions", "de": "Versionen", "es": "Versiones"}
NEW_BADGE = {"en": "NEW", "de": "NEU", "es": "NUEVO"}
WHERE_LABEL = {"en": "Where:", "de": "Wo:", "es": "Dónde:"}
VERSION_LABEL = {"en": "Version", "de": "Version", "es": "Versión"}
CURRENT_LABEL = {"en": "in progress", "de": "in Arbeit", "es": "en curso"}
CLOSE = {"en": "Close", "de": "Schliessen", "es": "Cerrar"}
SEARCH_PLACEHOLDER = {"en": "Search all versions…", "de": "Alle Versionen durchsuchen…",
                      "es": "Buscar en todas las versiones…"}
SEARCH_RESULTS = {"en": "{n} result(s) for \"{q}\"", "de": "{n} Treffer für \"{q}\"",
                  "es": "{n} resultado(s) para \"{q}\""}
SEARCH_NONE = {"en": "Nothing found for \"{q}\". Try another word - English, German and Spanish all work.",
               "de": "Nichts gefunden für \"{q}\". Versuche ein anderes Wort - Englisch, Deutsch und Spanisch gehen.",
               "es": "No se encontró nada para \"{q}\". Prueba otra palabra - sirven inglés, alemán y español."}
HITS_LABEL = {"en": "hits", "de": "Treffer", "es": "resultados"}
PDF_TOOLTIP = {"en": "Save the shown version as PDF (e.g. to print or send it)",
               "de": "Die angezeigte Version als PDF speichern (z. B. zum Drucken oder Verschicken)",
               "es": "Guardar la versión mostrada como PDF (p. ej. para imprimirla o enviarla)"}
