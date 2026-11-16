# ui/widgets/whats_new_texts.py
"""What's new (EN/DE/ES/ZH) - Sidebar -> Account -> "What's new" and once
after login (ui/whats_new.py): versions listed on the left, the new features
of the chosen version on the right as cards.

RELEASES, newest first. Each entry has
    "version": "current" -> the version being worked on = app_meta.APP_VERSION
               "4.6.3"   -> a compiled version (fixed)
    "date":    "" while current, the compile date ("2026-10-15") once fixed
    "texts":   {lang: [blocks]}
New features go into the "current" entry right away (all four languages).

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

Same block structure in all four languages. Button/menu names stay English.
"""

RELEASES = [
    {
        "version": "current",
        "date": "",
        "texts": {
            # ═══════════════════════════════ EN ═══════════════════════════════
            "en": [
                ("h", "Tools"),
                ("feature", 'Jet Advisor: which jet for my targets?',
                 'New under <b>Tools</b>, for DTY: give your targets (points/m, CV, stability 0.3 to 1.3, each min and/or max) and the yarn - an existing one or material, final titer and filaments. You get a ranking of the jets with the recommended <b>air pressure</b>, <b>overfeed</b> and <b>speed</b>, the window around it, the expected lab values and the chance that a new run reaches all targets. Filter by jet type (e.g. only <b>Standard</b>), maker, group or the titer range of the jet, limit the machine settings (e.g. a fixed speed) and prefer a safety margin or less air. It only uses our own trials of this yarn or similar ones and never goes beyond what we measured. Click a jet to see the trial series behind it or open it in the Process Playground.',
                 'Sidebar → Tools → <b>Jet Advisor</b>', None),
                ("feature", "Yarn Count Converter",
                 "New under <b>Tools</b>: convert yarn counts. Type a value and pick its unit - <b>dtex</b> and "
                 "<b>den</b> are shown large, plus tex, ktex, mtex, Nm, Ne, NeK, NeL, Run and grain/yd. Click a "
                 "result to use it as the new starting value. On the right, enter the filaments and plies to get "
                 "dtex and den per filament, the filament diameter, the totals and the ready-made designation (e.g. "
                 "<i>2 × dtex 167 f48</i>); or type a notation like <i>2x150D/48F</i> and press Enter to fill everything "
                 "in. Formulas &amp; definitions can be opened below. Every value has a <b>Copy</b> button, the last "
                 "input is remembered, and it works without a network connection.",
                 "Sidebar → Tools → <b>Yarn Count Converter</b>", "wn_yarn_count.svg"),
                ("feature", "Process Playground: what happens if I raise the air pressure?",
                 "New under <b>Tools</b>, for DTY: pick a yarn and a jet, type your start conditions (or take them "
                 "from a trial) and move <b>air pressure</b>, <b>overfeed</b> or <b>speed</b>. The table tells you what happens to "
                 "points/m, their CV, the stabilities 0.3 to 1.3 and the tension before and after the jet: "
                 "<i>more</i>, <i>fewer</i> or <i>about the same</i> - and how sure that is (clearly, probably, "
                 "tendency), with how many series show the same. It only uses our own trials of exactly this yarn "
                 "and jet, never goes beyond what we measured and says so when there are too few trials. Click a "
                 "lab value to see the trials behind the statement in a chart. The other way round: choose a main goal "
                 "(e.g. stability 1.0 higher) and further goals (e.g. CV keep, tension lower) and click "
                 "<b>Find settings</b> - you get up to 5 settings near what we really ran, with what they do to every "
                 "goal. In Show Experiment, right-click a DTY trial number → <i>Open in Process Playground…</i> to "
                 "start from that trial. F5 / <b>Reload</b> loads the latest trials.",
                 "Sidebar → Tools → <b>Process Playground</b>", "wn_process_playground.svg"),
                ("h", "Show Experiment"),
                ("feature", 'Conclusion per trial series',
                 'New tab <b>Conclusion</b> in Show Experiment: what came out of the series - the goal (from the experiment request, or your own goal if there is none), the outcome (achieved, partly, not achieved, open), a short summary, the best trials, findings and a recommendation (follow-up trial, release, discard). Not tied to "Done" - write it whenever the analysis is finished. The requester gets a bell notification. Backlog cards show the outcome as a dot (dashed ring = Done without conclusion), All Experiments has the columns Outcome and Conclusion with a filter, Quick Search a field Conclusion, the request popup the results of its series, and archiving without a conclusion asks first. In the <b>Report</b> the button <b>✅ Conclusion</b> shows it above the charts (for compared series too) and puts it into the PDF.',
                 'Show Experiment → tab <b>Conclusion</b> · Report → <b>✅ Conclusion</b>', None),
                ("feature", "DTY: choose the process and see the machine path",
                 "On DTY machines, Machine Data has a new row <b>DTY Process</b>: Standard, Elastane or one of the "
                 "cotton-like variants. Existing trials are already filled in (Elastane where an elastane yarn runs, "
                 "otherwise Standard). The rows for the pre-intermingling jet (LW 0 - LW 1) and for jet 3 (after the "
                 "set heater, before LW 3) now sit in Machine Data and only show up when a trial needs them. "
                 "Above the table, <b>Schema</b> draws the machine path of the trial you clicked: every ply on its "
                 "position, where they run together, elastane from its own source. <b>Click a station</b> (e.g. the "
                 "heater) and its rows light up in the table, a <b>double-click</b> jumps to the first value. Click a "
                 "cell and the schema marks its station. Values are still changed in the table only. With two or more "
                 "plies, three rows decide how they run together: <b>Route</b> (full path, bypass without heater and "
                 "friction, or a separate source like elastane), <b>Merge into ply</b> and <b>Merge point</b> - e.g. "
                 "ply 4 into ply 3 at LW 1, ply 3 into ply 1 at LW 2. The schema draws exactly that; left empty, "
                 "TrippleT assumes the usual path. Under every feed roll and the winder you see its <b>speed in m/min</b>, "
                 "calculated from the main speed at LW 2 (LW 1 = LW 2 / draw ratio, LW 0 = LW 1 / (1 - W0-W1 OF), LW 2.x, LW 3 and winder = LW 2 "
                 "minus their %).",
                 "Show Experiment → Machine Data → <b>Schema</b>", "wn_dty_schema.svg"),
                ("feature", "ATY: the machine path too",
                 "On ATY machines, <b>Schema</b> above Machine Data now draws the air-texturing path of the trial you "
                 "clicked - just like the Knowledge Base page: <b>core</b> (green) and <b>effect</b> (amber) each with their draw "
                 "zone and feed roll; only the core passes the wetting, the effect joins it dry just before the jet; then LW 2, stabilising zone, LW 3 and winder. Under every feed roll you "
                 "see its <b>speed</b> (LW 2 × (1 + OF %)). Core is always on top, no matter which ply number it has. "
                 "<b>Click a station</b> and its rows light up, a <b>double-click</b> jumps to the first value, "
                 "<b>right-click</b> opens the station in the Knowledge Base. Right-clicking a row title or value in Machine "
                 "Data now also works on ATY machines. Plies without a yarn use are shown grey with a note below the schema.",
                 "Show Experiment → Machine Data → <b>Schema</b>", "wn_aty_schema.svg"),
                ("feature", "Delete single trials - the numbers stay",
                 "Too many trials created, or some runs are not needed? In Machine Data, <b>right-click a trial number</b> "
                 "→ <b>Delete V23…</b>. For several trials, first select cells in their columns (drag, or <b>Ctrl+click</b> / "
                 "<b>Shift+click</b>), then right-click one of their numbers → <b>Delete 20 selected trials…</b>. Before "
                 "anything happens you see what goes with them (plies, Itemat, Statimat, notes …). The other trials keep their "
                 "numbers, nothing moves up, and new trials are always added after the highest remaining number - never "
                 "into a gap. "
                 "A superuser can bring deleted trials back from the <b>Recycle Bin</b> for 90 days. Allowed for whoever may "
                 "move the series in the Backlog.",
                 "Show Experiment → Machine Data → right-click a trial number → <b>Delete…</b>", "wn_trial_delete.svg"),
                ("feature", "Which trials meet your targets?",
                 "Click <b>vs Ref / Target</b> above Machine Data. One table shows every trial with the values of all lab "
                 "tabs side by side - compared with a <b>reference sample</b> (if the series has one) or with "
                 "<b>your own target values</b>: double-click the first row and type them in. Click a column header and "
                 "say what <b>better</b> means there: <b>higher</b>, <b>lower</b> or <b>close</b>, with a tolerance if "
                 "you like - e.g. intermingling points higher than 110, CV lower, stability lower than 80. Green = meets "
                 "it, red = not. <b>Result</b> counts the criteria per trial, the best trials are on top, and <b>Only "
                 "trials that meet all criteria</b> leaves just the winners. Save your criteria and targets under a name "
                 "(e.g. customer and article) - they are there for everyone and in every series. Double-click a trial to "
                 "jump to it in Machine Data.",
                 "Show Experiment → Machine Data → <b>vs Ref / Target</b>", "wn_ref_compare.svg"),
                ("feature", "Learn more without leaving your series",
                 "Not sure what a row means? <b>Right-click</b> a row title or a value in Machine Data or R&D Machine "
                 "Data (DTY machines), or in a lab tab (Statimat, EKB, shrinkage, Itemat, DTYoMat, ATYoMat, Rapid 600), "
                 "and choose <b>Learn more in Knowledge Base…</b> - in the DTY <b>Schema</b>, click a station and use the link below it (or right-click the station). The matching page opens in a window, already at the "
                 "right place - e.g. Overfeed shows the machine with feed roll 2.x selected, a DTY Process cell shows its "
                 "cotton-like variant. <b>Close</b> it (or press <b>Esc</b>) and you are back in your series, exactly where you were.",
                 "Show Experiment → right-click → <b>Learn more in Knowledge Base…</b>", "wn_onboarding.svg"),
                ("feature", "Fibres, yarn types and background in the help search",
                 "In <b>Manage Yarn</b> (and New/Edit Yarn), right-click a <b>Material</b> such as PES, PA 6.6 or WO, or a "
                 "<b>Garntyp</b> such as POY or DTY → <b>Learn more in Knowledge Base…</b>: the fibre portrait or the process "
                 "page opens in a window. The Knowledge Base now also has portraits of polyethylene, PLA and PVC, and acetate "
                 "includes triacetate. And the <b>help search (F1)</b> finds Knowledge Base pages too - search for e.g. "
                 "<i>friction</i>, <i>set heater</i> or <i>crimp</i>: below the help answers you get the matching pages, one click "
                 "opens them in a window and closing it brings you back to the search.",
                 "Manage Yarn → right-click · <b>Help (F1)</b>", "wn_onboarding.svg"),
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
                ("h", "Knowledge Base"),
                ("feature", "Knowledge Base - our work as short animations",
                 "New entry <b>Knowledge Base</b> below <b>Help (F1)</b>: short animated introductions to our work, "
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
                 "Sidebar → <b>Knowledge Base</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Heberlein company history and clearer chapters",
                 "The Knowledge Base list now has chapters: <b>Heberlein</b>, <b>Our technology</b> (spinning, DTY, ATY, "
                 "splicing, threading, <b>Our lab</b>) and later <b>Textile knowledge</b> (weaving, knitting …). New "
                 "under Heberlein: <b>Company history</b> - 190 years from the yarn dyeing works in Wattwil via Helanca "
                 "and machine building to today's air jets: timeline with five eras, owners, technology and where our "
                 "jets sit today. A click on POY, FDY, DTY or ATY opens the matching module.",
                 "Sidebar → <b>Knowledge Base</b> → Heberlein → <b>Company history</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Textile knowledge - weaving and knitting",
                 "New chapter <b>Textile knowledge</b> for what happens to our yarns later. <b>Weaving</b>: shaft weaving "
                 "(harness, drawing-in, lifting plan), weave structures (plain, twill, satin - and draw your own weave, "
                 "TrippleT tells you if it works), Jacquard weaving and Wilton carpet. <b>Knitting</b>: circular knitting "
                 "(loop formation, cam track, single/double jersey) and warp knitting (guide bars, lapping, point paper).",
                 "Sidebar → <b>Knowledge Base</b> → Textile knowledge", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Dyeing",
                 "New under <b>Textile knowledge</b>: <b>Dyeing</b> in eight scenes - how the dye gets into the fibre "
                 "(temperature slider), which dye class suits which fibre, when to dye (dope, stock, yarn, piece, garment), "
                 "dyeing curves for polyester, cotton and polyamide, the dyeing machines, continuous padding, indigo for "
                 "denim and why uneven texturing shows up as stripes after dyeing. With a quiz at the end.",
                 "Sidebar → <b>Knowledge Base</b> → Textile knowledge → <b>Dyeing</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: machines and manufacturers",
                 "New folder <b>Machines &amp; manufacturers</b> next to each process: POY and FDY spinning plants under "
                 "<b>Spinning</b>, DTY machines under <b>DTY</b>, ATY machines under <b>ATY</b>. Each shows the yarn path "
                 "(click the parts, switch the variants), a variant tree that filters the manufacturers, machine designs, "
                 "manufacturers and models with search and filters, a comparison and the market history.",
                 "Sidebar → <b>Knowledge Base</b> → Our technology → e.g. DTY → <b>Machines &amp; manufacturers</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Air covering",
                 "New area <b>AC</b> under Our technology: <b>Air covering (ACY)</b> - how elastane and DTY are bonded by air "
                 "knots, with sliders for draft, overfeed, jet pressure and speed that recalculate yarn count, elastane share "
                 "and air consumption live; a look inside the jet, the yarn structure when stretched and relaxed, ACY compared "
                 "with single and double covered yarn, uses, and the AC machines and their manufacturers.",
                 "Sidebar → <b>Knowledge Base</b> → Our technology → <b>AC</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Finishing",
                 "New under <b>Textile knowledge</b>: <b>Finishing</b> with two pages. <b>Chemical finishing</b>: the finishing "
                 "chain, an effect atlas (water repellent, flame retardant, antimicrobial ...), application methods, the PFAS "
                 "phase-out, regulation and suppliers. <b>Mechanical finishing</b>: goals, an atlas of processes from raising to "
                 "sanforising, machines in detail, key figures, sustainability and manufacturers.",
                 "Sidebar → <b>Knowledge Base</b> → Textile knowledge → <b>Finishing</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: weaving and finishing machines",
                 "Two more <b>Machines &amp; manufacturers</b> folders: <b>Weaving machines</b> under Weaving (shedding, the five "
                 "weft insertion systems with animation, dobby, Jacquard and Wilton machines, differences, manufacturer matrix) "
                 "and <b>Finishing machines</b> under Finishing (the finishing line, ten machines in detail with moving diagrams, "
                 "where manufacturers really differ, manufacturer matrix).",
                 "Sidebar → <b>Knowledge Base</b> → Textile knowledge → Weaving / Finishing → <b>Machines &amp; manufacturers</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: staple fibre spinning and weaving preparation",
                 "New under <b>Textile knowledge</b>: <b>Staple fibre spinning</b> - from the fibre tuft to the yarn, with animated "
                 "diagrams from blow room to roving frame, ring, compact, rotor and air-jet spinning, a twist and speed calculator "
                 "and a side trip to wool. And under Weaving: <b>Weaving preparation</b> - winding, warping, sizing, denim rope "
                 "dyeing, drawing-in and tying-in, with a calculator for the number of warper's beams.",
                 "Sidebar → <b>Knowledge Base</b> → Textile knowledge → <b>Staple fibre spinning</b> / Weaving", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: start page Textile chain",
                 "The Knowledge Base now opens with the <b>Textile chain</b>: a map from fibre to finished fabric - click a "
                 "station (spinning, texturing, weaving, finishing ...) to see its pages, green dots mark Heberlein technology. "
                 "Plus all pages at a glance, a manufacturer matrix along the whole chain (search, country, stage) and the "
                 "topics still missing.",
                 "Sidebar → <b>Knowledge Base</b> → <b>Textile chain</b> (top of the list)", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: fibres and nonwovens",
                 "Two new categories under <b>Textile knowledge</b>: <b>Fibres</b> with <b>Man-made fibres</b> (market shares, "
                 "13 fibre portraits with a molecule view, properties compared, where each fibre is used, recycled shares) and "
                 "<b>Nonwovens</b> (forming and bonding the web, ten animated processes from carding to meltblown and needle "
                 "punching, comparison, crosslapper and punch density calculator). Next to it, <b>Natural fibres</b>: market shares, "
                 "10 fibre portraits from cotton to cashmere, properties compared and where each fibre is used. All of them are "
                 "also on the Textile chain start page.",
                 "Sidebar → <b>Knowledge Base</b> → Textile knowledge → <b>Fibres</b> / <b>Nonwovens</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: pretreatment and textile printing",
                 "New under <b>Dyeing</b>: <b>Pretreatment</b> (singeing, desizing, scouring, bleaching, mercerising, heat "
                 "setting and the process routes) and <b>Textile printing</b>, each in eight animated scenes - print paste, pigment or dye, "
                 "direct, discharge and resist printing, flat screen, rotary screen, digital and transfer printing and how the "
                 "print is fixed. Both with a quiz at the end.",
                 "Sidebar → <b>Knowledge Base</b> → Textile knowledge → <b>Dyeing</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: from twisting to the finished product",
                 "Five more animated pages, each with a quiz: <b>Yarn twisting</b> (ring and two-for-one twisting, cabling, "
                 "fancy yarns), <b>Further fabric formation</b> (flat knitting, tufting, braiding), <b>Coating and laminating</b> "
                 "(knife coating, PVC tarpaulins, membranes), <b>Making-up</b> (cutting, stitch types, seam sealing, welding) and "
                 "<b>Fabric testing</b> (tensile and tear strength, Martindale, pilling, colour fastness, shrinkage). All of them "
                 "are on the Textile chain start page.",
                 "Sidebar → <b>Knowledge Base</b> → Textile knowledge", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: the friction unit in detail",
                 "New page <b>Friction unit</b> under DTY → Specialist knowledge: the disc stack as an animation - choose fibre, "
                 "D/Y, yarn speed, disc combination (e.g. 1-5-1), PU or ceramic and S or Z twist, and see the disc speed and how "
                 "T2/T1 moves. Plus disc types, which disc for which yarn, disc manufacturers, key figures and other twisters. "
                 "Double-click the friction unit in <b>DTY intermingling</b> (Machine, position 5) or the friction discs in <b>DTY machines</b> to jump there.",
                 "Sidebar → <b>Knowledge Base</b> → Our technology → DTY → Specialist knowledge → <b>Friction unit</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: jets in filament spinning",
                 "New page <b>Jets in filament spinning</b> under Spinning → Specialist knowledge: the spinning line with all jets "
                 "(click a station), what ends and pitch of a jet pack mean (with sliders), what happens in the yarn channel "
                 "(intermingling or migration, pressure slider, cross-section and side view as animation), how air consumption "
                 "follows channel, pressure and ends, and the key terms. Double-click the jets in <b>Filament yarn spinning</b> "
                 "(Plant, station 8) to jump there.",
                 "Sidebar → <b>Knowledge Base</b> → Our technology → Spinning → Specialist knowledge → <b>Jets in filament spinning</b>",
                 "wn_onboarding.svg"),
                ("feature", "Knowledge Base: spinning sun and spinning distance in air-jet spinning",
                 "<b>Air-jet spinning</b>, scene <i>Spinning jet</i>, is redrawn as a section like a real jet: the inclined air bores "
                 "aim exactly at the tip of the hollow spindle, and the free fibre ends spread over the conical tip and circle "
                 "around it as the <b>spinning sun</b> - in the section and in the view onto the spindle tip. New scene <i>Spinning distance</i>: the distance S from the last delivery roller to the spindle tip, with a slider - for natural fibres a chart shows how S shifts the shares of parallel fibres, wrapper fibres and blown-out waste; for synthetic staple fibres pick the fibre length and see the guide value S ≈ 0.55 × fibre length.",
                 "Sidebar → <b>Knowledge Base</b> → Our technology → Spinning → <b>Air-jet spinning</b> → Spinning jet / Spinning distance",
                 "wn_onboarding.svg"),
            ],
            # ═══════════════════════════════ DE ═══════════════════════════════
            "de": [
                ("h", "Tools"),
                ("feature", 'Jet Advisor: welche Düse für meine Ziele?',
                 'Neu unter <b>Tools</b>, für DTY: Ziele eingeben (Punkte/m, CV, Stabilität 0.3 bis 1.3, je min und/oder max) und das Garn - ein vorhandenes oder Material, Endtiter und Filamente. Du bekommst eine Rangliste der Düsen mit empfohlenem <b>Luftdruck</b>, <b>Overfeed</b> und <b>Geschwindigkeit</b>, dem Fenster darum, den erwarteten Laborwerten und der Chance, dass ein neuer Lauf alle Ziele erreicht. Filtern nach Düsentyp (z. B. nur <b>Standard</b>), Hersteller, Gruppe oder Titerbereich der Düse, Maschineneinstellungen begrenzen (z. B. feste Geschwindigkeit) und Sicherheitsabstand oder wenig Luft bevorzugen. Nur aus unseren eigenen Versuchen mit diesem oder ähnlichen Garnen, nie über das Gemessene hinaus. Eine Düse anklicken zeigt die Versuchsserien dahinter oder öffnet sie in der Process Playground.',
                 'Seitenleiste → Tools → <b>Jet Advisor</b>', None),
                ("feature", "Yarn Count Converter: Garnfeinheiten umrechnen",
                 "Neu unter <b>Tools</b>: Garnfeinheiten umrechnen. Wert eingeben und Einheit wählen - <b>dtex</b> und "
                 "<b>den</b> stehen gross, dazu tex, ktex, mtex, Nm, Ne, NeK, NeL, Run und grain/yd. Ein Klick auf ein "
                 "Ergebnis macht es zur neuen Ausgangsgrösse. Rechts Filamente und Fachung eingeben: dtex und den pro "
                 "Filament, Filamentdurchmesser, Gesamtwerte und die fertige Bezeichnung (z.&nbsp;B. <i>2 × dtex 167 "
                 "f48</i>); oder eine Schreibweise wie <i>2x150D/48F</i> eintippen und Enter drücken, dann wird alles "
                 "ausgefüllt. Formeln &amp; Definitionen lassen sich unten aufklappen. Jeder Wert hat einen Knopf "
                 "<b>Copy</b>, die letzte Eingabe wird gemerkt, und es geht auch ohne Netzwerk.",
                 "Sidebar → Tools → <b>Yarn Count Converter</b>", "wn_yarn_count.svg"),
                ("feature", "Process Playground: was passiert, wenn ich den Luftdruck erhöhe?",
                 "Neu unter <b>Tools</b>, für DTY: Garn und Düse wählen, deine Startbedingungen eintippen (oder von "
                 "einem Versuch übernehmen) und <b>Luftdruck</b>, <b>Overfeed</b> oder <b>Speed</b> verschieben. Die "
                 "Tabelle sagt, was mit Punkten/m, deren CV, den Stabilitäten 0.3 bis 1.3 und der Spannung vor und "
                 "nach der Düse passiert: <i>mehr</i>, <i>weniger</i> oder <i>etwa gleich</i> - und wie sicher das "
                 "ist (deutlich, wahrscheinlich, Tendenz), mit wie vielen Serien, die dasselbe zeigen. Verwendet "
                 "nur unsere eigenen Versuche mit genau diesem Garn und dieser Düse, geht nie über den gemessenen "
                 "Bereich hinaus und sagt es, wenn es zu wenige Versuche gibt. Klick auf einen Laborwert zeigt die "
                 "Versuche hinter der Aussage im Diagramm. Umgekehrt: Hauptziel wählen (z.&nbsp;B. Stabilität 1.0 "
                 "höher) und weitere Ziele (z.&nbsp;B. CV halten, Spannung tiefer), dann <b>Find settings</b> - du "
                 "bekommst bis zu 5 Einstellungen in der Nähe dessen, was wir wirklich gefahren haben, mit ihrer "
                 "Wirkung auf jedes Ziel. In Show Experiment Rechtsklick auf eine DTY-Versuchsnummer → <i>Open in "
                 "Process Playground…</i> startet bei diesem Versuch. F5 / <b>Reload</b> lädt die neuesten Versuche.",
                 "Sidebar → Tools → <b>Process Playground</b>", "wn_process_playground.svg"),
                ("h", "Show Experiment"),
                ("feature", 'Fazit pro Versuchsserie',
                 'Neuer Reiter <b>Conclusion</b> in Show Experiment: was bei der Serie herauskam - das Ziel (aus der Experiment-Anfrage oder ein eigenes Ziel, wenn es keine gibt), das Ergebnis (erreicht, teilweise, nicht erreicht, offen), ein Kurzfazit, die besten Versuche, Erkenntnisse und eine Empfehlung (Folgeversuch, freigeben, verwerfen). Nicht an "Done" gebunden - schreib es, sobald die Auswertung fertig ist. Wer die Anfrage gestellt hat, bekommt eine Glocken-Meldung. Backlog-Karten zeigen das Ergebnis als Punkt (gestrichelter Ring = Done ohne Fazit), All Experiments hat die Spalten Outcome und Conclusion mit Filter, die Schnellsuche ein Feld Conclusion, das Request-Popup die Ergebnisse seiner Serien, und Archivieren ohne Fazit fragt zuerst nach. Im <b>Report</b> zeigt der Knopf <b>✅ Conclusion</b> es über den Diagrammen (auch für verglichene Serien) und nimmt es ins PDF.',
                 'Show Experiment → Reiter <b>Conclusion</b> · Report → <b>✅ Conclusion</b>', None),
                ("feature", "DTY: Verfahren wählen und den Maschinenweg sehen",
                 "Bei DTY-Maschinen hat Machine Data eine neue Zeile <b>DTY Process</b>: Standard, Elastane oder eine "
                 "der Cotton-like-Varianten. Bestehende Versuche sind schon eingetragen (Elastane, wo ein Elastan-Garn "
                 "läuft, sonst Standard). Die Zeilen für die Vorverwirbelung (LW 0 - LW 1) und für die 3. Düse (nach dem "
                 "Set-Heizer, vor LW 3) stehen jetzt in Machine Data und erscheinen nur, wenn ein Versuch sie braucht. "
                 "Über der Tabelle zeichnet <b>Schema</b> den Maschinenweg des angeklickten Versuchs: jede Ply auf ihrer "
                 "Position, wo sie zusammenlaufen, Elastan aus der eigenen Quelle. <b>Station anklicken</b> (z.&nbsp;B. "
                 "den Heizer), und ihre Zeilen leuchten in der Tabelle auf; ein <b>Doppelklick</b> springt zum ersten "
                 "Wert. Klickt man eine Zelle an, markiert das Schema die passende Station. Werte ändert man weiterhin "
                 "nur in der Tabelle. Ab zwei Plies legen drei Zeilen fest, wie sie zusammenlaufen: <b>Route</b> "
                 "(ganzer Weg, Bypass ohne Heizer und Friktion oder eigene Quelle wie Elastan), <b>Merge into ply</b> "
                 "und <b>Merge point</b> - z.&nbsp;B. Ply 4 in Ply 3 an LW 1, Ply 3 in Ply 1 an LW 2. Das Schema "
                 "zeichnet genau das; leer gelassen, nimmt TrippleT den üblichen Weg an. Unter jedem Lieferwerk und der Aufwicklung steht "
                 "die <b>Geschwindigkeit in m/min</b>, berechnet aus der Hauptgeschwindigkeit an LW 2 (LW 1 = LW 2 / "
                 "Verstreckung, LW 0 = LW 1 / (1 - W0-W1 OF), LW 2.x, LW 3 und Winder = LW 2 minus ihre %).",
                 "Show Experiment → Machine Data → <b>Schema</b>", "wn_dty_schema.svg"),
                ("feature", "ATY: auch hier der Maschinenweg",
                 "Auf ATY-Maschinen zeichnet <b>Schema</b> über Machine Data jetzt den Weg durch die Lufttexturiermaschine - "
                 "wie auf der Seite in der Knowledge Base: <b>Kern</b> (grün) und <b>Effekt</b> (ocker) je mit Verstreckzone und "
                 "Lieferwerk; nur der Kern läuft durch die Benetzung, der Effekt kommt trocken erst vor der Düse dazu; dann LW 2, Stabilisierzone, LW 3 und Aufwicklung. Unter jedem Lieferwerk steht "
                 "seine <b>Geschwindigkeit</b> (LW 2 × (1 + OF %)). Der Kern steht immer oben, egal welche Ply-Nummer er hat. "
                 "<b>Station anklicken</b> markiert ihre Zeilen, <b>Doppelklick</b> springt zum ersten Wert, <b>Rechtsklick</b> "
                 "öffnet die Station in der Knowledge Base. Rechtsklick auf Zeilentitel oder Werte in Machine Data geht jetzt "
                 "auch auf ATY-Maschinen. Plies ohne Yarn Use erscheinen grau, mit Hinweis unter dem Schema.",
                 "Show Experiment → Machine Data → <b>Schema</b>", "wn_aty_schema.svg"),
                ("feature", "Einzelne Versuche löschen - die Nummern bleiben",
                 "Zu viele Versuche angelegt oder ein paar Läufe braucht es nicht? In Machine Data <b>Rechtsklick auf eine "
                 "Versuchsnummer</b> → <b>Delete V23…</b>. Für mehrere Versuche zuerst Zellen in ihren Spalten markieren "
                 "(ziehen, oder <b>Strg+Klick</b> / <b>Umschalt+Klick</b>), dann Rechtsklick auf eine ihrer Nummern → "
                 "<b>Delete 20 selected trials…</b>. Vorher siehst du, was alles mitgeht (Plies, Itemat, Statimat, Notizen …). "
                 "Die übrigen Versuche behalten ihre Nummern, nichts rutscht nach, und neue Versuche kommen immer nach der "
                 "höchsten verbliebenen Nummer - nie in eine Lücke. Ein Superuser kann gelöschte Versuche 90 Tage "
                 "lang aus dem <b>Recycle Bin</b> zurückholen. Erlaubt für alle, die die Serie im Backlog verschieben dürfen.",
                 "Show Experiment → Machine Data → Rechtsklick auf eine Versuchsnummer → <b>Delete…</b>", "wn_trial_delete.svg"),
                ("feature", "Welche Versuche erreichen deine Ziele?",
                 "Klick auf <b>vs Ref / Target</b> über Machine Data. Eine Tabelle zeigt alle Versuche mit den Werten "
                 "aller Labor-Reiter nebeneinander - verglichen mit einem <b>Referenzmuster</b> (wenn die Serie eines "
                 "hat) oder mit <b>eigenen Zielwerten</b>: Doppelklick in die erste Zeile und eintippen. Klick auf einen "
                 "Spaltenkopf und lege fest, was dort <b>besser</b> heisst: <b>höher</b>, <b>tiefer</b> oder <b>nah</b>, "
                 "auf Wunsch mit Toleranz - z.&nbsp;B. Knotenzahl höher als 110, CV tiefer, Stabilität tiefer als 80. "
                 "Grün = erfüllt, rot = nicht. <b>Result</b> zählt die erfüllten Kriterien pro Versuch, die besten stehen "
                 "oben, und <b>Only trials that meet all criteria</b> lässt nur die Gewinner stehen. Kriterien und "
                 "Zielwerte speicherst du unter einem Namen (z.&nbsp;B. Kunde und Artikel) - sie stehen allen und in jeder "
                 "Serie zur Verfügung. Doppelklick auf einen Versuch springt zu ihm in Machine Data.",
                 "Show Experiment → Machine Data → <b>vs Ref / Target</b>", "wn_ref_compare.svg"),
                ("feature", "Nachschlagen, ohne die Serie zu verlassen",
                 "Unsicher, was eine Zeile bedeutet? <b>Rechtsklick</b> auf einen Zeilentitel oder einen Wert in Machine Data "
                 "oder R&D Machine Data (DTY-Maschinen) oder in einem Labor-Reiter (Statimat, EKB, Schrumpf, Itemat, "
                 "DTYoMat, ATYoMat, Rapid 600) und <b>Learn more in Knowledge Base…</b> wählen - im DTY-<b>Schema</b> eine Station anklicken und den Link darunter nehmen (oder Rechtsklick auf die Station). Die passende Seite öffnet "
                 "sich in einem Fenster, gleich an der richtigen Stelle - z. B. zeigt Overfeed die Maschine mit Lieferwerk 2.x, "
                 "eine DTY-Process-Zelle ihre Cotton-like-Variante. <b>Close</b> (oder <b>Esc</b>) und du bist wieder in deiner "
                 "Serie, genau dort, wo du warst.",
                 "Show Experiment → Rechtsklick → <b>Learn more in Knowledge Base…</b>", "wn_onboarding.svg"),
                ("feature", "Fasern, Garntypen und Hintergrund in der Hilfe-Suche",
                 "In <b>Manage Yarn</b> (und New/Edit Yarn) Rechtsklick auf ein <b>Material</b> wie PES, PA 6.6 oder WO oder auf "
                 "einen <b>Garntyp</b> wie POY oder DTY → <b>Learn more in Knowledge Base…</b>: Das Faserporträt bzw. die Seite zum "
                 "Verfahren öffnet sich in einem Fenster. Die Knowledge Base hat dafür neu auch Porträts von Polyethylen, PLA und "
                 "PVC, und Acetat umfasst jetzt Triacetat. Und die <b>Hilfe-Suche (F1)</b> findet jetzt auch Knowledge-Base-Seiten - "
                 "z. B. <i>Friktion</i>, <i>Set-Heizer</i> oder <i>Kräuselung</i> suchen: Unter den Hilfe-Antworten stehen die "
                 "passenden Seiten, ein Klick öffnet sie in einem Fenster, schliessen bringt dich zurück zur Suche.",
                 "Manage Yarn → Rechtsklick · <b>Help (F1)</b>", "wn_onboarding.svg"),
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
                ("h", "Knowledge Base"),
                ("feature", "Knowledge Base - unsere Arbeit als kurze Animationen",
                 "Neuer Eintrag <b>Knowledge Base</b> unter <b>Help (F1)</b>: kurze animierte Einführungen in unsere "
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
                 "Sidebar → <b>Knowledge Base</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Heberlein-Firmengeschichte und übersichtlichere Kapitel",
                 "Die Liste der Knowledge Base hat jetzt Oberkapitel: <b>Heberlein</b>, <b>Unsere Technologie</b> (Spinnerei, "
                 "DTY, ATY, Spleissen, Einfädeln, <b>Unser Labor</b>) und später <b>Textiles Wissen</b> (Weben, "
                 "Stricken …). Neu unter Heberlein: <b>Firmengeschichte</b> - 190 Jahre von der Garnfärberei in "
                 "Wattwil über Helanca und den Maschinenbau zu den Luftdüsen von heute: Zeitleiste mit fünf Epochen, "
                 "Eigentümer, Technologie und wo unsere Düsen heute sitzen. Ein Klick auf POY, FDY, DTY oder ATY "
                 "öffnet das passende Modul.",
                 "Sidebar → <b>Knowledge Base</b> → Heberlein → <b>Firmengeschichte</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Textiles Wissen - Weben und Stricken",
                 "Neues Oberkapitel <b>Textiles Wissen</b> für das, was später mit unseren Garnen passiert. <b>Weben</b>: "
                 "Schaftweben (Webgeschirr, Einzug, Schaftprogramm), Bindungslehre (Leinwand, Köper, Atlas - und selbst "
                 "eine Bindung zeichnen, TrippleT sagt, ob sie funktioniert), Jacquardweben und Wilton-Teppich. "
                 "<b>Stricken / Wirken</b>: Rundstricken (Maschenbildung, Schlossbahn, Single/Double Jersey) und "
                 "Kettenwirken (Legeschienen, Legung, Punktpatrone).",
                 "Sidebar → <b>Knowledge Base</b> → Textiles Wissen", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Färben",
                 "Neu unter <b>Textiles Wissen</b>: <b>Färben</b> in acht Szenen - wie der Farbstoff in die Faser kommt "
                 "(Regler Temperatur), welche Farbstoffklasse zu welcher Faser passt, wann gefärbt wird (Spinn-, Flocke-, "
                 "Garn-, Stück-, Konfektionsfärbung), Färbekurven für Polyester, Baumwolle und Polyamid, die Färbemaschinen, "
                 "das Klotzen, Indigo für Denim und warum ungleiches Texturieren nach dem Färben als Streifen sichtbar wird. "
                 "Mit Quiz am Schluss.",
                 "Sidebar → <b>Knowledge Base</b> → Textiles Wissen → <b>Färben</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Maschinen und Hersteller",
                 "Neuer Ordner <b>Maschinen &amp; Hersteller</b> bei jedem Prozess: POY- und FDY-Spinnanlagen unter "
                 "<b>Spinnerei</b>, DTY-Maschinen unter <b>DTY</b>, ATY-Maschinen unter <b>ATY</b>. Jeweils mit Fadenlauf "
                 "(Teile anklicken, Varianten umschalten), Variantenschema, das die Hersteller filtert, Bauformen, Herstellern "
                 "und Modellen mit Suche und Filtern, einem Vergleich und der Marktentwicklung.",
                 "Sidebar → <b>Knowledge Base</b> → Unsere Technologie → z.&nbsp;B. DTY → <b>Maschinen &amp; Hersteller</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Air Covering",
                 "Neuer Bereich <b>AC</b> unter Unsere Technologie: <b>Air Covering (ACY)</b> - wie Elastan und DTY durch Luftknoten "
                 "verbunden werden, mit Reglern für Verzug, Überlieferung, Düsendruck und Geschwindigkeit, die Garntiter, "
                 "Elastananteil und Luftverbrauch live nachrechnen; ein Blick in die Düse, die Garnstruktur gedehnt und entspannt, "
                 "ACY im Vergleich mit einfach und doppelt umwundenem Garn, Einsatzgebiete sowie die AC-Maschinen und ihre Hersteller.",
                 "Sidebar → <b>Knowledge Base</b> → Unsere Technologie → <b>AC</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Veredlung",
                 "Neu unter <b>Textiles Wissen</b>: <b>Veredlung</b> mit zwei Seiten. <b>Chemische Textilausrüstung</b>: "
                 "Veredlungskette, Effekt-Atlas (wasserabweisend, flammhemmend, antimikrobiell ...), Auftragsverfahren, "
                 "PFAS-Ausstieg, Regulierung und Anbieter. <b>Mechanische Textilausrüstung</b>: Ziele, Verfahrens-Atlas vom "
                 "Rauen bis zum Sanforisieren, Maschinen im Detail, Kennzahlen, Nachhaltigkeit und Hersteller.",
                 "Sidebar → <b>Knowledge Base</b> → Textiles Wissen → <b>Veredlung</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Web- und Ausrüstungsmaschinen",
                 "Zwei weitere Ordner <b>Maschinen &amp; Hersteller</b>: <b>Webmaschinen</b> unter Weben (Fachbildung, die fünf "
                 "Schusseintragsarten mit Animation, Schaft-, Jacquard- und Wilton-Maschinen, Unterschiede, Hersteller-Matrix) "
                 "und <b>Ausrüstungsmaschinen</b> unter Veredlung (Ausrüstungslinie, zehn Maschinen im Detail mit bewegtem Schema, "
                 "wo sich die Hersteller wirklich unterscheiden, Hersteller-Matrix).",
                 "Sidebar → <b>Knowledge Base</b> → Textiles Wissen → Weben / Veredlung → <b>Maschinen &amp; Hersteller</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Stapelfaserspinnerei und Webereivorbereitung",
                 "Neu unter <b>Textiles Wissen</b>: <b>Stapelfaserspinnerei</b> - von der Faserflocke zum Garn, mit animierten "
                 "Schemata von der Putzerei bis zum Flyer, Ring-, Kompakt-, Rotor- und Luftspinnen, einem Rechner für Drehung und "
                 "Tempo und einem Exkurs zur Wolle. Und unter Weben: <b>Webereivorbereitung</b> - Spulen, Schären, Schlichten, "
                 "Denim-Strangfärben, Einziehen und Anknüpfen, mit einem Rechner für die Anzahl Zettelbäume.",
                 "Sidebar → <b>Knowledge Base</b> → Textiles Wissen → <b>Stapelfaserspinnerei</b> / Weben", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Startseite Textilkette",
                 "Die Knowledge Base beginnt jetzt mit der <b>Textilkette</b>: eine Landkarte von der Faser zum fertigen Stoff - "
                 "Klick auf eine Station (Spinnen, Texturieren, Weben, Veredlung ...) zeigt ihre Seiten, grüne Punkte markieren "
                 "Heberlein-Technologie. Dazu alle Seiten auf einen Blick, eine Herstellermatrix über die ganze Kette (Suche, "
                 "Land, Stufe) und die Themen, die noch fehlen.",
                 "Sidebar → <b>Knowledge Base</b> → <b>Textilkette</b> (ganz oben in der Liste)", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Fasern und Vliesstoffe",
                 "Zwei neue Kategorien unter <b>Textiles Wissen</b>: <b>Fasern</b> mit <b>Chemiefasern</b> (Marktanteile, 13 "
                 "Faserporträts mit Molekülbild, Kennwerte im Vergleich, Einsatzmatrix, Recyclinganteile) und <b>Vliesstoffe</b> "
                 "(Vlies bilden und verfestigen, zehn animierte Verfahren vom Krempeln über Meltblown bis zum Vernadeln, Vergleich, "
                 "Rechner für Kreuzleger und Einstichdichte). Dazu <b>Naturfasern</b>: Marktanteile, 10 Faserporträts von "
                 "Baumwolle bis Kaschmir, Kennwerte im Vergleich und Einsatzmatrix. Alle sind auch auf der Startseite Textilkette verlinkt.",
                 "Sidebar → <b>Knowledge Base</b> → Textiles Wissen → <b>Fasern</b> / <b>Vliesstoffe</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Vorbehandlung und Textildruck",
                 "Neu unter <b>Färben</b>: <b>Vorbehandlung</b> (Sengen, Entschlichten, Abkochen, Bleichen, Mercerisieren, "
                 "Thermofixieren und die Verfahrenswege) und <b>Textildruck</b>, je in acht animierten Szenen - Druckpaste, Pigment oder Farbstoff, "
                 "Direkt-, Ätz- und Reservedruck, Flachfilm-, Rotationsfilm-, Digital- und Transferdruck und wie der Druck "
                 "fixiert wird. Beide mit Quiz am Schluss.",
                 "Sidebar → <b>Knowledge Base</b> → Textiles Wissen → <b>Färben</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: vom Zwirn bis zum fertigen Produkt",
                 "Fünf weitere animierte Seiten, jede mit Quiz: <b>Zwirnen</b> (Ring- und Doppeldrahtzwirnen, Kordieren, "
                 "Effektzwirne), <b>Weitere Flächenbildung</b> (Flachstricken, Tuften, Flechten), <b>Beschichten und Kaschieren</b> "
                 "(Rakel, PVC-Planen, Membranen), <b>Konfektion</b> (Zuschnitt, Sticharten, Nahtabdichtung, Schweissen) und "
                 "<b>Stoffprüfung</b> (Zug- und Weiterreissfestigkeit, Martindale, Pilling, Farbechtheit, Massänderung). Alle sind "
                 "auf der Startseite Textilkette verlinkt.",
                 "Sidebar → <b>Knowledge Base</b> → Textiles Wissen", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: das Friktionsaggregat im Detail",
                 "Neue Seite <b>Friktionsaggregat</b> unter DTY → Spezialwissen: der Scheibenstapel als Animation - "
                 "Faserstoff, D/Y, Fadengeschwindigkeit, Scheibenkombination (z.&nbsp;B. 1-5-1), PU oder Keramik und S- oder Z-Drall "
                 "wählen und Scheibendrehzahl und T2/T1-Verlauf sehen. Dazu Scheibentypen, welche Scheibe für welches Garn, "
                 "Scheibenhersteller, Kennzahlen und andere Drallgeber. Doppelklick auf das Friktionsaggregat in <b>DTY-Verwirbelung</b> (Maschine, "
                 "Position 5) oder auf die Friktionsscheiben in <b>DTY-Maschinen</b> springt direkt dorthin.",
                 "Sidebar → <b>Knowledge Base</b> → Unsere Technologie → DTY → Spezialwissen → <b>Friktionsaggregat</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Düsen in der Filamentspinnerei",
                 "Neue Seite <b>Düsen in der Filamentspinnerei</b> unter Spinnerei → Spezialwissen: die Spinnlinie mit allen Düsen "
                 "(Station anklicken), was Fachung und Teilung eines Düsenpakets bedeuten (mit Reglern), was im Fadenkanal passiert "
                 "(Verwirbelung oder Migration, Regler für den Druck, Querschnitt und Seitenansicht als Animation), wie der "
                 "Luftverbrauch von Luftkanal, Druck und Fachung abhängt, und die wichtigsten Begriffe. Doppelklick auf die Düsen in "
                 "der <b>Filamentgarnspinnerei</b> (Anlage, Station 8) springt direkt dorthin.",
                 "Sidebar → <b>Knowledge Base</b> → Unsere Technologie → Spinnerei → Spezialwissen → <b>Düsen in der Filamentspinnerei</b>",
                 "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Spinnsonne und Spinnabstand beim Luftdüsenspinnen",
                 "<b>Luftdüsenspinnen</b>, Szene <i>Spinndüse</i>, ist neu als Schnitt wie eine echte Düse gezeichnet: Die geneigten "
                 "Luftbohrungen zielen genau auf die Spitze der Hohlspindel, und die freien Faserenden spreizen sich über die "
                 "kegelförmige Spitze und kreisen als <b>Spinnsonne</b> um sie - im Schnitt und im Blick auf die Spindelspitze. "
                 "Neue Szene <i>Spinnabstand</i>: der Abstand S von der letzten Lieferwalze zur Spindelspitze, mit Regler - bei "
                 "Naturfasern zeigt eine Grafik, wie S die Anteile von parallelen Fasern, Umwindefasern und ausgeblasenem "
                 "Abfall verschiebt; bei Synthese-Stapelfasern Faserlänge wählen und den Richtwert S ≈ 0,55 × Faserlänge sehen.",
                 "Sidebar → <b>Knowledge Base</b> → Unsere Technologie → Spinnerei → <b>Luftdüsenspinnen</b> → Spinndüse / Spinnabstand",
                 "wn_onboarding.svg"),
            ],
            # ═══════════════════════════════ ES ═══════════════════════════════
            "es": [
                ("h", "Tools"),
                ("feature", 'Jet Advisor: ¿qué tobera para mis objetivos?',
                 'Nuevo en <b>Tools</b>, para DTY: indica tus objetivos (puntos/m, CV, estabilidad 0.3 a 1.3, cada uno mín. y/o máx.) y el hilo - uno existente o material, título final y filamentos. Obtienes una clasificación de las toberas con la <b>presión de aire</b>, la <b>sobrealimentación</b> y la <b>velocidad</b> recomendadas, la ventana alrededor, los valores de laboratorio esperados y la probabilidad de que una nueva prueba cumpla todos los objetivos. Filtra por tipo de tobera (p. ej. solo <b>Standard</b>), fabricante, grupo o rango de título de la tobera, limita los ajustes de máquina (p. ej. velocidad fija) y prefiere margen de seguridad o menos aire. Solo usa nuestros propios ensayos con este hilo o hilos similares y nunca va más allá de lo medido. Haz clic en una tobera para ver las series de ensayos o abrirla en el Process Playground.',
                 'Barra lateral → Tools → <b>Jet Advisor</b>', None),
                ("feature", "Yarn Count Converter: convertir títulos de hilo",
                 "Nuevo en <b>Tools</b>: convertir títulos de hilo. Escriba un valor y elija la unidad - <b>dtex</b> y "
                 "<b>den</b> aparecen en grande, además tex, ktex, mtex, Nm, Ne, NeK, NeL, Run y grain/yd. Un clic en "
                 "un resultado lo convierte en el nuevo valor de partida. A la derecha, indique filamentos y cabos: "
                 "dtex y den por filamento, diámetro del filamento, totales y la designación lista (p.&nbsp;ej. "
                 "<i>2 × dtex 167 f48</i>); o escriba una notación como <i>2x150D/48F</i> y pulse Enter para rellenarlo "
                 "todo. Fórmulas y definiciones se despliegan abajo. Cada valor tiene un botón <b>Copy</b>, la última "
                 "entrada se recuerda y funciona sin conexión de red.",
                 "Sidebar → Tools → <b>Yarn Count Converter</b>", "wn_yarn_count.svg"),
                ("feature", "Process Playground: ¿qué pasa si subo la presión de aire?",
                 "Nuevo en <b>Tools</b>, para DTY: elija un hilo y una tobera, escriba sus condiciones de inicio (o "
                 "tómelas de un ensayo) y mueva la <b>presión de aire</b>, el <b>overfeed</b> o la <b>velocidad</b>. La tabla "
                 "dice qué pasa con los puntos/m, su CV, las estabilidades 0.3 a 1.3 y la tensión antes y después "
                 "de la tobera: <i>más</i>, <i>menos</i> o <i>más o menos igual</i> - y con qué seguridad "
                 "(claramente, probablemente, tendencia), con cuántas series muestran lo mismo. Solo usa nuestros "
                 "propios ensayos con exactamente este hilo y esta tobera, nunca va más allá de lo medido y lo dice "
                 "cuando hay pocos ensayos. Un clic en un valor muestra en un gráfico los ensayos detrás de la "
                 "afirmación. Al revés: elija un objetivo principal (p.&nbsp;ej. estabilidad 1.0 más alta) y otros "
                 "objetivos (p.&nbsp;ej. CV mantener, tensión más baja) y pulse <b>Find settings</b> - obtiene hasta 5 "
                 "ajustes cerca de lo que realmente hicimos, con su efecto en cada objetivo. En Show Experiment, clic "
                 "derecho en un número de ensayo DTY → <i>Open in Process Playground…</i> parte de ese ensayo. "
                 "F5 / <b>Reload</b> carga los ensayos más recientes.",
                 "Sidebar → Tools → <b>Process Playground</b>", "wn_process_playground.svg"),
                ("h", "Show Experiment"),
                ("feature", 'Conclusión por serie de ensayos',
                 'Nueva pestaña <b>Conclusion</b> en Show Experiment: qué resultó de la serie - el objetivo (de la solicitud de experimento, o uno propio si no hay), el resultado (logrado, parcialmente, no logrado, abierto), un resumen, los mejores ensayos, hallazgos y una recomendación (ensayo de seguimiento, liberar, descartar). No ligado a "Done" - escríbela cuando termine el análisis. Quien hizo la solicitud recibe un aviso en la campana. Las tarjetas del Backlog muestran el resultado como punto (anillo discontinuo = Done sin conclusión), All Experiments tiene las columnas Outcome y Conclusion con filtro, la búsqueda rápida un campo Conclusion, el popup de la solicitud los resultados de sus series, y archivar sin conclusión pregunta antes. En el <b>Report</b> el botón <b>✅ Conclusion</b> la muestra sobre los gráficos (también para series comparadas) y la incluye en el PDF.',
                 'Show Experiment → pestaña <b>Conclusion</b> · Report → <b>✅ Conclusion</b>', None),
                ("feature", "DTY: elegir el proceso y ver el recorrido en la máquina",
                 "En las máquinas DTY, Machine Data tiene una fila nueva <b>DTY Process</b>: Standard, Elastane o una "
                 "de las variantes cotton-like. Los ensayos existentes ya están rellenados (Elastane donde corre un "
                 "hilo de elastano, si no Standard). Las filas del chorro de pre-entrelazado (LW 0 - LW 1) y del 3.er "
                 "chorro (después del calentador de fijado, antes de LW 3) están ahora en Machine Data y solo aparecen "
                 "cuando un ensayo las necesita. Encima de la tabla, <b>Schema</b> dibuja el recorrido del ensayo en el "
                 "que hizo clic: cada ply en su posición, dónde se juntan, el elastano desde su propia fuente. "
                 "<b>Haga clic en una estación</b> (p.&nbsp;ej. el calentador) y sus filas se resaltan en la tabla; "
                 "un <b>doble clic</b> salta al primer valor. Al hacer clic en una celda, el esquema marca su estación. "
                 "Los valores se siguen cambiando solo en la tabla. Con dos o más plies, tres filas deciden cómo se "
                 "juntan: <b>Route</b> (recorrido completo, bypass sin calentador ni fricción, o fuente propia como el "
                 "elastano), <b>Merge into ply</b> y <b>Merge point</b> - p.&nbsp;ej. ply 4 en ply 3 en LW 1, ply 3 en "
                 "ply 1 en LW 2. El esquema dibuja exactamente eso; si se dejan vacías, TrippleT supone el recorrido "
                 "habitual. Debajo de cada rodillo de alimentación y del bobinador aparece su <b>velocidad en m/min</b>, "
                 "calculada a partir de la velocidad principal en LW 2 (LW 1 = LW 2 / estiraje; LW 0 = LW 1 / (1 - W0-W1 OF); LW 2.x, LW 3 y "
                 "bobinador = LW 2 menos su %).",
                 "Show Experiment → Machine Data → <b>Schema</b>", "wn_dty_schema.svg"),
                ("feature", "ATY: también el recorrido de la máquina",
                 "En las máquinas ATY, <b>Schema</b> encima de Machine Data dibuja ahora el recorrido por la máquina de "
                 "texturizado por aire del ensayo seleccionado, igual que la página de la Knowledge Base: <b>alma</b> (verde) y "
                 "<b>efecto</b> (ocre), cada uno con su zona de estirado y su rodillo de alimentación; solo el alma pasa por la "
                 "humectación, el efecto se une en seco justo antes de la tobera; después LW 2, zona de estabilización, LW 3 y bobinado. Debajo de cada rodillo de alimentación aparece su "
                 "<b>velocidad</b> (LW 2 × (1 + OF %)). El alma siempre está arriba, tenga el número de ply que tenga. "
                 "<b>Clic en una estación</b> resalta sus filas, <b>doble clic</b> salta al primer valor, <b>clic derecho</b> "
                 "abre la estación en la Knowledge Base. El clic derecho en títulos de fila o valores de Machine Data ahora "
                 "también funciona en máquinas ATY. Las plies sin Yarn Use aparecen en gris, con un aviso debajo del esquema.",
                 "Show Experiment → Machine Data → <b>Schema</b>", "wn_aty_schema.svg"),
                ("feature", "Borrar ensayos sueltos - los números se mantienen",
                 "¿Creaste demasiados ensayos o sobran algunas pruebas? En Machine Data, <b>clic derecho en un número de "
                 "ensayo</b> → <b>Delete V23…</b>. Para varios ensayos, primero selecciona celdas en sus columnas (arrastrando, "
                 "o con <b>Ctrl+clic</b> / <b>Mayús+clic</b>) y luego clic derecho en uno de sus números → <b>Delete 20 "
                 "selected trials…</b>. Antes ves todo lo que se borra con ellos (plies, Itemat, Statimat, notas …). Los demás "
                 "ensayos conservan su número, nada se desplaza, y los nuevos ensayos siempre van después del "
                 "número más alto que queda - nunca en un hueco. Un superusuario puede recuperar ensayos borrados desde la <b>Recycle Bin</b> "
                 "durante 90 días. Permitido a quien puede mover la serie en el Backlog.",
                 "Show Experiment → Machine Data → clic derecho en un número de ensayo → <b>Delete…</b>", "wn_trial_delete.svg"),
                ("feature", "¿Qué ensayos alcanzan tus objetivos?",
                 "Haz clic en <b>vs Ref / Target</b> encima de Machine Data. Una tabla muestra todos los ensayos con los "
                 "valores de todas las pestañas de laboratorio uno al lado del otro - comparados con una <b>muestra de "
                 "referencia</b> (si la serie tiene una) o con <b>tus propios valores objetivo</b>: doble clic en la "
                 "primera fila y escríbelos. Haz clic en el encabezado de una columna y decide qué significa <b>mejor</b> "
                 "allí: <b>mayor</b>, <b>menor</b> o <b>cercano</b>, con tolerancia si quieres - p.&nbsp;ej. puntos de "
                 "entrelazado mayor que 110, CV menor, estabilidad menor que 80. Verde = cumple, rojo = no. <b>Result</b> "
                 "cuenta los criterios cumplidos por ensayo, los mejores aparecen arriba y <b>Only trials that meet all "
                 "criteria</b> deja solo a los ganadores. Guarda criterios y objetivos con un nombre (p.&nbsp;ej. cliente "
                 "y artículo) - están disponibles para todos y en cada serie. Doble clic en un ensayo lo muestra en "
                 "Machine Data.",
                 "Show Experiment → Machine Data → <b>vs Ref / Target</b>", "wn_ref_compare.svg"),
                ("feature", "Consulta sin salir de tu serie",
                 "¿No sabes qué significa una fila? Haz <b>clic derecho</b> en el título de una fila o en un valor de Machine Data "
                 "o R&D Machine Data (máquinas DTY), o en una pestaña de laboratorio (Statimat, EKB, encogimiento, Itemat, "
                 "DTYoMat, ATYoMat, Rapid 600) y elige <b>Learn more in Knowledge Base…</b>; en el <b>Schema</b> DTY, haz clic en una estación y usa el enlace debajo (o clic derecho en la estación). La página correspondiente se abre "
                 "en una ventana, ya en el lugar correcto: p. ej. Overfeed muestra la máquina con el rodillo 2.x seleccionado, una "
                 "celda DTY Process muestra su variante cotton-like. <b>Close</b> (o <b>Esc</b>) y vuelves a tu serie, justo donde estabas.",
                 "Show Experiment → clic derecho → <b>Learn more in Knowledge Base…</b>", "wn_onboarding.svg"),
                ("feature", "Fibras, tipos de hilo y conocimiento de fondo en la búsqueda de ayuda",
                 "En <b>Manage Yarn</b> (y New/Edit Yarn), clic derecho en un <b>Material</b> como PES, PA 6.6 o WO, o en un "
                 "<b>Garntyp</b> como POY o DTY → <b>Learn more in Knowledge Base…</b>: el retrato de la fibra o la página del "
                 "proceso se abre en una ventana. La Knowledge Base tiene ahora también retratos de polietileno, PLA y PVC, y el "
                 "acetato incluye el triacetato. Y la <b>búsqueda de ayuda (F1)</b> encuentra también páginas de la Knowledge Base: "
                 "busca p. ej. <i>fricción</i>, <i>set heater</i> o <i>rizado</i>; debajo de las respuestas de la ayuda aparecen las "
                 "páginas, un clic las abre en una ventana y al cerrarla vuelves a la búsqueda.",
                 "Manage Yarn → clic derecho · <b>Help (F1)</b>", "wn_onboarding.svg"),
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
                ("h", "Knowledge Base"),
                ("feature", "Knowledge Base - nuestro trabajo en animaciones cortas",
                 "Nueva entrada <b>Knowledge Base</b> debajo de <b>Help (F1)</b>: introducciones animadas cortas a "
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
                 "Sidebar → <b>Knowledge Base</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: historia de Heberlein y capítulos más claros",
                 "La lista de la Knowledge Base tiene ahora capítulos: <b>Heberlein</b>, <b>Nuestra tecnología</b> (hilatura, "
                 "DTY, ATY, empalme, enhebrado, <b>Nuestro laboratorio</b>) y más adelante <b>Conocimiento textil</b> "
                 "(tejeduría, punto …). Nuevo en Heberlein: <b>Historia de la empresa</b> - 190 años desde la "
                 "tintorería de hilo en Wattwil, pasando por Helanca y la construcción de máquinas, hasta las toberas "
                 "de hoy: cronología con cinco épocas, propietarios, tecnología y dónde están hoy nuestras toberas. "
                 "Un clic en POY, FDY, DTY o ATY abre el módulo correspondiente.",
                 "Sidebar → <b>Knowledge Base</b> → Heberlein → <b>Historia de la empresa</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Conocimiento textil - tejeduría y punto",
                 "Nuevo capítulo <b>Conocimiento textil</b> para lo que pasa después con nuestros hilos. <b>Tejeduría</b>: "
                 "tejeduría con lizos (lizos, remetido, programa de lizos), ligamentos (tafetán, sarga, raso, y dibuje su "
                 "propio ligamento: TrippleT le dice si funciona), tejeduría Jacquard y alfombra Wilton. <b>Tejido de "
                 "punto</b>: tejido circular (formación de malla, levas, single/double jersey) y punto por urdimbre "
                 "(barras de guía, pasadas, papel de puntos).",
                 "Sidebar → <b>Knowledge Base</b> → Conocimiento textil", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Tintura",
                 "Nuevo en <b>Conocimiento textil</b>: <b>Tintura</b> en ocho escenas - cómo entra el colorante en la fibra "
                 "(regulador de temperatura), qué clase de colorante va con cada fibra, cuándo se tiñe (en masa, floca, hilo, "
                 "pieza, prenda), curvas de tintura para poliéster, algodón y poliamida, las máquinas, el fulardado, el índigo "
                 "para el denim y por qué un texturizado desigual se ve como rayas tras teñir. Con quiz al final.",
                 "Sidebar → <b>Knowledge Base</b> → Conocimiento textil → <b>Tintura</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: máquinas y fabricantes",
                 "Nueva carpeta <b>Máquinas y fabricantes</b> junto a cada proceso: plantas de hilatura POY y FDY en "
                 "<b>Hilatura</b>, máquinas DTY en <b>DTY</b>, máquinas ATY en <b>ATY</b>. Cada una con el recorrido del hilo "
                 "(clic en las piezas, cambiar variantes), un esquema de variantes que filtra los fabricantes, tipos de máquina, "
                 "fabricantes y modelos con búsqueda y filtros, una comparación y la evolución del mercado.",
                 "Sidebar → <b>Knowledge Base</b> → Nuestra tecnología → p.&nbsp;ej. DTY → <b>Máquinas y fabricantes</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Air covering",
                 "Nueva área <b>AC</b> en Nuestra tecnología: <b>Air covering (ACY)</b> - cómo se unen elastano y DTY con nudos "
                 "de aire, con reguladores de estiraje, sobrealimentación, presión y velocidad que recalculan en vivo el título, "
                 "la proporción de elastano y el consumo de aire; un vistazo dentro de la boquilla, la estructura del hilo estirado "
                 "y relajado, ACY frente a hilo de recubrimiento simple y doble, usos, y las máquinas AC y sus fabricantes.",
                 "Sidebar → <b>Knowledge Base</b> → Nuestra tecnología → <b>AC</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: Acabado",
                 "Nuevo en <b>Conocimiento textil</b>: <b>Acabado</b> con dos páginas. <b>Acabado químico</b>: la cadena de "
                 "acabado, un atlas de efectos (hidrófugo, ignífugo, antimicrobiano ...), métodos de aplicación, la salida de "
                 "los PFAS, normativa y proveedores. <b>Acabado mecánico</b>: objetivos, un atlas de procesos desde el perchado "
                 "hasta el sanforizado, máquinas en detalle, indicadores, sostenibilidad y fabricantes.",
                 "Sidebar → <b>Knowledge Base</b> → Conocimiento textil → <b>Acabado</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: telares y máquinas de acabado",
                 "Dos carpetas más de <b>Máquinas y fabricantes</b>: <b>Telares</b> en Tejeduría (formación de calada, los cinco "
                 "sistemas de inserción de trama con animación, telares de lizos, Jacquard y Wilton, diferencias, matriz de "
                 "fabricantes) y <b>Máquinas de acabado</b> en Acabado (la línea de acabado, diez máquinas en detalle con esquemas "
                 "animados, en qué se diferencian realmente los fabricantes, matriz de fabricantes).",
                 "Sidebar → <b>Knowledge Base</b> → Conocimiento textil → Tejeduría / Acabado → <b>Máquinas y fabricantes</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: hilatura de fibra corta y preparación de tejeduría",
                 "Nuevo en <b>Conocimiento textil</b>: <b>Hilatura de fibra corta</b> - del copo de fibra al hilo, con esquemas "
                 "animados desde la sala de apertura hasta la mechera, hilatura de anillo, compacta, de rotor y por chorro de aire, "
                 "una calculadora de torsión y velocidad y un excurso sobre la lana. Y en Tejeduría: <b>Preparación de tejeduría</b> - "
                 "bobinado, urdido, encolado, tintura en cuerda del denim, remetido y anudado, con una calculadora de plegadores.",
                 "Sidebar → <b>Knowledge Base</b> → Conocimiento textil → <b>Hilatura de fibra corta</b> / Tejeduría", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: página de inicio Cadena textil",
                 "La Knowledge Base empieza ahora con la <b>Cadena textil</b>: un mapa de la fibra al tejido acabado - clic en "
                 "una estación (hilatura, texturizado, tejeduría, acabado ...) muestra sus páginas, los puntos verdes marcan "
                 "tecnología Heberlein. Además todas las páginas de un vistazo, una matriz de fabricantes a lo largo de toda la "
                 "cadena (búsqueda, país, etapa) y los temas que aún faltan.",
                 "Sidebar → <b>Knowledge Base</b> → <b>Cadena textil</b> (arriba en la lista)", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: fibras y no tejidos",
                 "Dos categorías nuevas en <b>Conocimiento textil</b>: <b>Fibras</b> con <b>Fibras químicas</b> (cuotas de mercado, "
                 "13 retratos de fibras con molécula, propiedades comparadas, matriz de aplicaciones, cuotas de reciclado) y "
                 "<b>No tejidos</b> (formar y consolidar el velo, diez procesos animados del cardado al meltblown y el punzonado, "
                 "comparación, calculadora de plegador y densidad de punzonado). Además, <b>Fibras naturales</b>: cuotas de "
                 "mercado, 10 retratos de fibras del algodón al cachemir, propiedades comparadas y matriz de aplicaciones. Todas "
                 "también en la página de inicio Cadena textil.",
                 "Sidebar → <b>Knowledge Base</b> → Conocimiento textil → <b>Fibras</b> / <b>No tejidos</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: preparación y estampación textil",
                 "Nuevo en <b>Tintura</b>: <b>Preparación</b> (chamuscado, desencolado, descrudado, blanqueo, mercerizado, "
                 "termofijado y rutas de proceso) y <b>Estampación textil</b>, cada una en ocho escenas animadas: pasta de estampación, pigmento o "
                 "colorante, estampación directa, por corrosión y por reserva, lionesa, rotativa, digital y por transferencia, y "
                 "cómo se fija el estampado. Ambas con un quiz al final.",
                 "Sidebar → <b>Knowledge Base</b> → Conocimiento textil → <b>Tintura</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: del retorcido al producto terminado",
                 "Cinco páginas animadas más, cada una con quiz: <b>Retorcido</b> (retorcido de anillo y a doble torsión, "
                 "cableado, hilos de fantasía), <b>Otras formas de crear tejido</b> (tricotado plano, tufting, trenzado), "
                 "<b>Recubrimiento y laminado</b> (rasqueta, lonas de PVC, membranas), <b>Confección</b> (corte, tipos de puntada, "
                 "sellado de costuras, soldadura) y <b>Ensayos de tejidos</b> (tracción y desgarro, Martindale, pilling, solidez "
                 "del color, cambio dimensional). Todas están en la página de inicio Cadena textil.",
                 "Sidebar → <b>Knowledge Base</b> → Conocimiento textil", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: el grupo de fricción en detalle",
                 "Nueva página <b>Grupo de fricción</b> en DTY → Conocimiento especializado: la pila de discos como animación - elige "
                 "fibra, D/Y, velocidad del hilo, combinación de discos (p.&nbsp;ej. 1-5-1), PU o cerámica y torsión S o Z, y ve la "
                 "velocidad del disco y cómo cambia T2/T1. Además tipos de disco, qué disco para qué hilo, fabricantes de discos, "
                 "indicadores y otros torsionadores. Doble clic en el grupo de fricción en <b>Entrelazado DTY</b> (Máquina, posición 5) "
                 "o en los discos de fricción en <b>Máquinas DTY</b> para ir directamente.",
                 "Sidebar → <b>Knowledge Base</b> → Nuestra tecnología → DTY → Conocimiento especializado → <b>Grupo de fricción</b>", "wn_onboarding.svg"),
                ("feature", "Knowledge Base: toberas en la hilatura de filamento",
                 "Nueva página <b>Toberas en la hilatura de filamento</b> en Hilatura → Conocimiento especializado: la línea de "
                 "hilatura con todas las toberas (haz clic en una estación), qué significan número de cabos y paso de un paquete de "
                 "toberas (con reguladores), qué pasa en el canal del hilo (entrelazado o migración, regulador de presión, sección "
                 "y vista lateral animadas), cómo el consumo de aire depende del canal, la presión y los cabos, y los términos clave. "
                 "Doble clic en las toberas en <b>Hilatura de filamento</b> (Instalación, estación 8) para ir directamente.",
                 "Sidebar → <b>Knowledge Base</b> → Nuestra tecnología → Hilatura → Conocimiento especializado → <b>Toberas en la hilatura de filamento</b>",
                 "wn_onboarding.svg"),
                ("feature", "Knowledge Base: sol de hilatura y distancia de hilatura por chorro de aire",
                 "<b>Hilatura por chorro de aire</b>, escena <i>Tobera</i>, se ha redibujado como sección de una tobera real: los "
                 "orificios de aire inclinados apuntan exactamente a la punta del huso hueco, y los extremos libres de las fibras se "
                 "abren sobre la punta cónica y giran a su alrededor como <b>sol de hilatura</b>, en la sección y en la vista sobre "
                 "la punta del huso. Nueva escena <i>Distancia de hilatura</i>: la distancia S del último cilindro de salida a la "
                 "punta del huso, con regulador - para fibras naturales un gráfico muestra cómo S desplaza las proporciones de "
                 "fibras paralelas, envolventes y desperdicio; para fibras cortadas sintéticas se elige la longitud y se ve el "
                 "valor orientativo S ≈ 0,55 × longitud de fibra.",
                 "Sidebar → <b>Knowledge Base</b> → Nuestra tecnología → Hilatura → <b>Hilatura por chorro de aire</b> → Tobera / Distancia de hilatura",
                 "wn_onboarding.svg"),
            ],
            # ═══════════════════════════════ ZH ═══════════════════════════════
            "zh": [
                ("h", "Tools"),
                ("feature", 'Jet Advisor：哪个喷嘴能达到我的目标？',
                 '<b>Tools</b> 下新增，适用于 DTY：输入目标（网络点/m、CV、稳定性 0.3 至 1.3，每项可设最小和/或最大值）和纱线——已有纱线，或材料、终纤度和单丝数。你会得到喷嘴排名，包括推荐的<b>气压</b>、<b>超喂</b>和<b>速度</b>、其周围的窗口范围、预期实验室数值，以及新一次运行达到全部目标的概率。可按喷嘴类型（例如仅 <b>Standard</b>）、制造商、组或喷嘴纤度范围筛选，限制机器设置（例如固定速度），并优先考虑安全余量或耗气更少。仅使用我们自己针对该纱线或相似纱线的试验，绝不超出测量范围。单击某个喷嘴可查看其背后的试验系列，或在 Process Playground 中打开。',
                 '侧边栏 → Tools → <b>Jet Advisor</b>', None),
                ("feature", "Yarn Count Converter：纱线细度换算",
                 "<b>Tools</b> 下新增：换算纱线细度。输入数值并选择单位——<b>dtex</b> 和 <b>den</b> 以大字显示，"
                 "另外还有 tex、ktex、mtex、Nm、Ne、NeK、NeL、Run 和 grain/yd。单击某个结果即可将其作为新的起始值。"
                 "在右侧输入单丝数和股数，即可得到每根单丝的 dtex 和 den、单丝直径、总值以及现成的规格标记（例如 "
                 "<i>2 × dtex 167 f48</i>）；或者输入 <i>2x150D/48F</i> 这样的写法并按 Enter，所有字段都会自动填好。"
                 "下方可展开公式 &amp; 定义。每个数值都有 <b>Copy</b> 按钮，上次的输入会被记住，无需网络连接也能使用。",
                 "侧边栏 → Tools → <b>Yarn Count Converter</b>", "wn_yarn_count.svg"),
                ("feature", "Process Playground：提高气压会怎样？",
                 "<b>Tools</b> 下新增，适用于 DTY：选择纱线和喷嘴，输入起始条件（或从某个试验中采用），然后调整"
                 "<b>气压</b>、<b>超喂</b>或<b>速度</b>。表格会告诉你网络点/m 及其 CV、稳定性 0.3 至 1.3 以及喷嘴前后的张力"
                 "会如何变化：<i>更多</i>、<i>更少</i>或<i>基本不变</i>——以及把握有多大（明显、很可能、趋势），并注明有多少个"
                 "系列显示同样的结果。它只使用我们自己针对这一纱线和这一喷嘴的试验，绝不超出已测量的范围，试验太少时也会明确"
                 "说明。单击某个实验室数值，可在图表中查看该结论背后的试验。反过来也可以：选择一个主要目标（例如稳定性 1.0 "
                 "提高）和其他目标（例如 CV 保持、张力降低），然后单击 <b>Find settings</b>——你会得到最多 5 组接近我们实际"
                 "运行过的设定，并显示它们对每个目标的影响。在 Show Experiment 中右键单击某个 DTY 试验编号 → <i>Open in "
                 "Process Playground…</i>，即可从该试验开始。F5 / <b>Reload</b> 加载最新的试验。",
                 "侧边栏 → Tools → <b>Process Playground</b>", "wn_process_playground.svg"),
                ("h", "Show Experiment"),
                ("feature", '每个试验系列的结论',
                 'Show Experiment 中新增 <b>Conclusion</b> 选项卡：记录该系列的结果——目标（来自实验申请；没有申请时填写自己的目标）、结果（已达成、部分达成、未达成、待定）、简短摘要、最佳试验、发现以及建议（后续试验、发布、放弃）。不与 "Done" 绑定——分析完成后随时填写。申请人会收到铃铛通知。Backlog 卡片用圆点显示结果（虚线圆环 = Done 但尚无结论），All Experiments 有 Outcome 和 Conclusion 列及筛选，快速搜索有 Conclusion 字段，申请弹窗显示其系列的结果，没有结论就归档时会先询问。在 <b>Report</b> 中，按钮 <b>✅ Conclusion</b> 会在图表上方显示结论（对比系列也会显示），并将其写入 PDF。',
                 'Show Experiment → 选项卡 <b>Conclusion</b> · Report → <b>✅ Conclusion</b>', None),
                ("feature", "DTY：选择工艺并查看机器路径",
                 "在 DTY 机器上，Machine Data 新增一行 <b>DTY Process</b>：Standard、Elastane 或某种仿棉（cotton-like）"
                 "变体。现有试验已自动填好（运行氨纶纱线的为 Elastane，其余为 Standard）。预网络喷嘴（LW 0 - LW 1）和第 3 "
                 "喷嘴（定型热箱之后、LW 3 之前）的行现在位于 Machine Data 中，只在试验需要时才显示。表格上方的 "
                 "<b>Schema</b> 会绘制你所单击试验的机器路径：每一股在其位置上、各股在哪里汇合、氨纶来自单独的喂入源。"
                 "<b>单击某个工位</b>（例如热箱），其对应行会在表格中高亮；<b>双击</b>则跳到第一个数值。单击某个单元格，"
                 "Schema 会标出对应的工位。数值仍然只在表格中修改。有两股或以上时，由三行决定各股如何汇合：<b>Route</b>"
                 "（完整路径、不经热箱和假捻的旁路，或像氨纶那样的单独喂入源）、<b>Merge into ply</b> 和 <b>Merge point</b>"
                 "——例如第 4 股在 LW 1 并入第 3 股，第 3 股在 LW 2 并入第 1 股。Schema 会准确地画出这些；若留空，TrippleT "
                 "按常规路径处理。每个喂入罗拉和卷绕下方显示其<b>速度（m/min）</b>，由 LW 2 处的主速度计算得出（LW 1 = "
                 "LW 2 / 牵伸比，LW 0 = LW 1 / (1 - W0-W1 OF)，LW 2.x、LW 3 和卷绕 = LW 2 减去各自的 %）。",
                 "Show Experiment → Machine Data → <b>Schema</b>", "wn_dty_schema.svg"),
                ("feature", "ATY：同样显示机器路径",
                 "在 ATY 机器上，Machine Data 上方的 <b>Schema</b> 现在会绘制所单击试验的空气变形路径——与知识库中的页面"
                 "一样：<b>芯丝</b>（绿色）和<b>效果丝</b>（琥珀色）各有其牵伸区和喂入罗拉；只有芯丝经过加湿，效果丝在喷嘴前"
                 "才以干态加入；然后是 LW 2、稳定区、LW 3 和卷绕。每个喂入罗拉下方显示其<b>速度</b>（LW 2 × (1 + OF %)）。"
                 "无论芯丝是第几股，它总显示在最上方。<b>单击某个工位</b>会高亮其对应行，<b>双击</b>跳到第一个数值，"
                 "<b>右键单击</b>则在知识库中打开该工位。在 Machine Data 中右键单击行标题或数值现在也适用于 ATY 机器。"
                 "没有纱线用途（Yarn Use）的股以灰色显示，并在 Schema 下方给出提示。",
                 "Show Experiment → Machine Data → <b>Schema</b>", "wn_aty_schema.svg"),
                ("feature", "删除单个试验——编号保持不变",
                 "试验建多了，或者某些运行不需要了？在 Machine Data 中<b>右键单击试验编号</b> → <b>Delete V23…</b>。要删除"
                 "多个试验，先在它们的列中选择单元格（拖动，或 <b>Ctrl+单击</b> / <b>Shift+单击</b>），然后右键单击其中一个"
                 "编号 → <b>Delete 20 selected trials…</b>。执行之前，你会看到哪些内容会一并删除（股、Itemat、Statimat、"
                 "备注 …）。其余试验保留原编号，不会前移，新试验总是添加在剩余的最大编号之后——绝不会填入空缺。"
                 "超级用户可在 90 天内从 <b>Recycle Bin</b> 恢复已删除的试验。凡是有权在 Backlog 中移动该系列的人都可以"
                 "执行此操作。",
                 "Show Experiment → Machine Data → 右键单击试验编号 → <b>Delete…</b>", "wn_trial_delete.svg"),
                ("feature", "哪些试验达到了你的目标？",
                 "单击 Machine Data 上方的 <b>vs Ref / Target</b>。一张表并排显示每个试验及所有实验室选项卡的数值——与"
                 "<b>参考样</b>（如果该系列有）或<b>你自己的目标值</b>进行比较：双击第一行并输入目标值。单击列标题，指定该列"
                 "中<b>更好</b>的含义：<b>更高</b>、<b>更低</b>或<b>接近</b>，可选设定公差——例如网络点数高于 110、CV 更低、"
                 "稳定性低于 80。绿色 = 达标，红色 = 未达标。<b>Result</b> 统计每个试验满足的标准数，最好的试验排在最上面，"
                 "<b>Only trials that meet all criteria</b> 只保留全部达标的试验。可将标准和目标值以一个名称保存（例如客户"
                 "和品种）——所有人在每个系列中都能使用。双击某个试验即可跳到 Machine Data 中的该试验。",
                 "Show Experiment → Machine Data → <b>vs Ref / Target</b>", "wn_ref_compare.svg"),
                ("feature", "无需离开试验系列即可查阅",
                 "不确定某一行是什么意思？在 Machine Data 或 R&D Machine Data（DTY 机器）中，或在某个实验室选项卡（Statimat、"
                 "EKB、收缩、Itemat、DTYoMat、ATYoMat、Rapid 600）中<b>右键单击</b>行标题或数值，然后选择 <b>Learn more in "
                 "Knowledge Base…</b>——在 DTY 的 <b>Schema</b> 中，单击某个工位并使用其下方的链接（或右键单击该工位）。"
                 "对应页面会在窗口中打开，并直接定位到正确位置——例如 Overfeed 会显示选中喂入罗拉 2.x 的机器，DTY Process "
                 "单元格会显示其仿棉变体。<b>Close</b>（或按 <b>Esc</b>）后你就回到了原来的系列，正好在原来的位置。",
                 "Show Experiment → 右键单击 → <b>Learn more in Knowledge Base…</b>", "wn_onboarding.svg"),
                ("feature", "帮助搜索中的纤维、纱线类型和背景知识",
                 "在 <b>Manage Yarn</b>（以及 New/Edit Yarn）中，右键单击 PES、PA 6.6 或 WO 等 <b>Material</b>，或 POY、"
                 "DTY 等 <b>Garntyp</b> → <b>Learn more in Knowledge Base…</b>：纤维简介或工艺页面会在窗口中打开。知识库现在"
                 "还新增了聚乙烯、PLA 和 PVC 的简介，醋酯纤维也包含了三醋酯纤维。此外，<b>帮助搜索（F1）</b>现在也能找到"
                 "知识库页面（知识库为英文）——例如搜索 <i>friction</i>、<i>set heater</i>或<i>crimp</i>：在帮助答案下方会列出匹配的页面，单击即可在"
                 "窗口中打开，关闭后回到搜索。",
                 "Manage Yarn → 右键单击 · <b>Help (F1)</b>", "wn_onboarding.svg"),
                ("h", "Smart Chart"),
                ("feature", "有多少种不同的喷嘴？——Count (distinct)",
                 "Card 现在可以统计某个字段有多少个<b>不同</b>的值——例如运行过多少种不同的喷嘴、纱线或机器，始终在你的筛选、"
                 "切片器和点击范围内。选择聚合方式 <b>Count (distinct)</b>，并将字段（例如 <i>Jet</i>）拖到 <b>Value</b> 中。"
                 "空值不计入。在 Columns、Matrix 和 Pie 中也适用——例如每年使用的不同喷嘴数。",
                 "Smart Chart → Card → 聚合方式 <b>Count (distinct)</b>", "wn_distinct_count.svg"),
                ("feature", "是哪些喷嘴？——每个值一行",
                 "Table 现在可以把每个喷嘴（或纱线、机器 …）只列一次，而不是列出每个试验：勾选 <b>One row per value</b>。"
                 "名称旁边显示它在多少个试验和系列中使用过；像 FP/m 这样的数值字段显示其平均值。在相同筛选条件下，列表的行数"
                 "与使用 <b>Count (distinct)</b> 的 Card 统计的数目完全一致。单击标题即可排序。",
                 "Smart Chart → Table → Build → <b>One row per value</b>", "wn_value_table.svg"),
                ("h", "Create Experiment"),
                ("feature", "输入即可查找纱线和喷嘴",
                 "<b>Material</b> 和 <b>Jet</b> 选项卡的列表上方现在有一个搜索框。输入名称的一部分（例如 <i>pa6 44</i>）"
                 "——会同时在所有分组中搜索，只保留匹配的条目。对于喷嘴，也会搜索开发名称。<b>Enter</b> 选择第一个结果，"
                 "<b>Esc</b> 清除搜索。每种纱线后面还会显示 Show Experiment 中的筒子图标：绿色筒子 = 有库存（单击可查看筒子"
                 "存放的位置），划掉的纸管 = 无库存。",
                 "New Experiment → <b>Material</b> / <b>Jet</b> → 搜索框", "wn_create_search.svg"),
                ("h", "知识库"),
                ("feature", "知识库——用简短动画介绍我们的工作",
                 "<b>Help (F1)</b> 下方新增条目 <b>Knowledge Base</b>：以全屏简短动画介绍我们的工作。第一个主题展示 DTY 纱线"
                 "如何进行网络——穿过机器的路径以及喂入罗拉 2 和 2.x 之间的超喂（单击任意位置即可查看说明）、喷嘴中发生了"
                 "什么，以及网络点。每个主题都像 TrippleT 的其他部分一样带有选项卡。试试 <b>Overfeed</b> 和<b>气压</b>滑块。"
                 "用旗帜切换语言——现在也有中文。第二个主题：<b>ATY 空气变形</b>——芯丝和效果丝的超喂、变形喷嘴、圈结以及"
                 "各项设定的作用。在<b>纺丝</b>下：<b>长丝纺丝</b>——从切片到 POY 和 FDY，以及 Heberlein 喷嘴所在的位置。"
                 "同样在<b>纺丝</b>下：<b>BCF 地毯纱</b>——纺丝、牵伸、热空气变形和交缠一步完成，包括三色混合；以及"
                 "<b>喷气涡流纺</b>（短纤维）——从棉包到纱线，空心锭子周围的气流涡旋。在<b>捻接</b>下：<b>长丝空气捻接</b>"
                 "——无结连接两个纱端；单击某个步骤即可直接跳转。在<b>穿纱</b>下：<b>Lufan 吸枪</b>——在机器运行时穿纱、"
                 "喷射器原理、耗气量。在 <b>DTY</b> → <b>专业知识</b>下：<b>仿棉 DTY</b>（七种获得短纤纱外观的方法，可单击"
                 "任意机器位置）和<b>网络点硬，伸长更低？</b>（一个带实时拉伸试验模型的假设）。在 DTY 机器中，现在可以输入 "
                 "<b>FR 2</b> 的速度和<b>牵伸比</b>：FR 1 和 FR 2.x 随即以 m/min 显示。DTY 主题新增场景<b>均匀性</b>：网络点"
                 "数量相同还不够，它们必须分布均匀（间距的离散度、最长的开放段）。DTY 主题现在以 <b>Quiz</b> 选项卡结束："
                 "13 道题，每道都链接回对应的场景——答对 80 % 即通过该主题，并在列表中打勾。新文件夹<b>实验室</b>，包含"
                 "<b>用 ITEMAT 测量网络点</b>：结构（单击各工位）、机械和光学传感器、阈值设置错误的后果、负载下的稳定性测试"
                 "和评估；<b>细度、强度和伸长（STATIMAT DS）</b>：称重测细度、比较 POY、FDY 和 DTY 的 CRE 拉伸试验、每个"
                 "卷装的统计；<b>卷曲和收缩（TEXTURMAT ME）</b>：从绞纱经热处理到五个负载阶段（可单击），以及卷曲收缩率、"
                 "模量、稳定性和收缩率等关键指标；以及<b>用 RAPID 600 V 测试网络点</b>：针刺法在运行的纱线中计数网络点，并"
                 "区分好的和弱的网络点，带有触发力滑块。更多主题即将推出。",
                 "侧边栏 → <b>Knowledge Base</b>", "wn_onboarding.svg"),
                ("feature", "知识库：Heberlein 公司历史和更清晰的章节",
                 "知识库列表现在分为若干章节：<b>Heberlein</b>、<b>我们的技术</b>（纺丝、DTY、ATY、捻接、穿纱、"
                 "<b>我们的实验室</b>），以及后续的<b>纺织知识</b>（机织、针织 …）。Heberlein 下新增：<b>公司历史</b>——从 "
                 "Wattwil 的纱线染色厂，经 Helanca 和机械制造，到今天的空气喷嘴，190 年的历程：包含五个时代的时间轴、"
                 "所有者、技术，以及我们的喷嘴如今用在哪里。单击 POY、FDY、DTY 或 ATY 即可打开相应的模块。",
                 "侧边栏 → <b>Knowledge Base</b> → Heberlein → <b>公司历史</b>", "wn_onboarding.svg"),
                ("feature", "知识库：纺织知识——机织和针织",
                 "新章节<b>纺织知识</b>，介绍我们的纱线之后的去向。<b>机织</b>：综框织造（综框装置、穿综、提综图）、织物组织"
                 "（平纹、斜纹、缎纹——还可以自己画组织，TrippleT 会告诉你是否可行）、提花织造和威尔顿地毯。<b>针织</b>："
                 "圆机针织（成圈、三角轨道、单面/双面针织）和经编（梳栉、垫纱、意匠纸）。",
                 "侧边栏 → <b>Knowledge Base</b> → 纺织知识", "wn_onboarding.svg"),
                ("feature", "知识库：染色",
                 "<b>纺织知识</b>下新增：<b>染色</b>，共八个场景——染料如何进入纤维（温度滑块）、哪类染料适合哪种纤维、在哪个"
                 "阶段染色（原液、散纤维、纱线、匹染、成衣）、涤纶、棉和锦纶的染色曲线、染色设备、连续轧染、牛仔布的靛蓝"
                 "染色，以及为什么变形不匀会在染色后显现为条纹。最后附有测验。",
                 "侧边栏 → <b>Knowledge Base</b> → 纺织知识 → <b>染色</b>", "wn_onboarding.svg"),
                ("feature", "知识库：机器和制造商",
                 "每个工艺旁新增文件夹<b>机器 &amp; 制造商</b>：<b>纺丝</b>下的 POY 和 FDY 纺丝设备、<b>DTY</b> 下的 DTY 机器、"
                 "<b>ATY</b> 下的 ATY 机器。每个文件夹都展示纱线路径（单击部件、切换变体）、可筛选制造商的变体树、机器结构、"
                 "带搜索和筛选的制造商和型号、对比以及市场历史。",
                 "侧边栏 → <b>Knowledge Base</b> → 我们的技术 → 例如 DTY → <b>机器 &amp; 制造商</b>", "wn_onboarding.svg"),
                ("feature", "知识库：空气包覆",
                 "我们的技术下新增区域 <b>AC</b>：<b>空气包覆（ACY）</b>——氨纶与 DTY 如何通过空气网络点结合在一起，带有牵伸、"
                 "超喂、喷嘴压力和速度滑块，实时重新计算纱线细度、氨纶比例和耗气量；还可以看看喷嘴内部、拉伸和松弛状态下的"
                 "纱线结构、ACY 与单包覆和双包覆纱的对比、用途，以及 AC 机器及其制造商。",
                 "侧边栏 → <b>Knowledge Base</b> → 我们的技术 → <b>AC</b>", "wn_onboarding.svg"),
                ("feature", "知识库：后整理",
                 "<b>纺织知识</b>下新增：<b>后整理</b>，共两页。<b>化学整理</b>：整理流程、效果图谱（拒水、阻燃、抗菌 ...）、"
                 "施加方法、PFAS 淘汰、法规和供应商。<b>机械整理</b>：目标、从起毛到预缩的工艺图谱、设备详解、关键指标、"
                 "可持续性和制造商。",
                 "侧边栏 → <b>Knowledge Base</b> → 纺织知识 → <b>后整理</b>", "wn_onboarding.svg"),
                ("feature", "知识库：织机和后整理设备",
                 "又新增两个<b>机器 &amp; 制造商</b>文件夹：机织下的<b>织机</b>（开口、五种带动画的引纬系统、多臂机、提花机和"
                 "威尔顿织机、差异、制造商矩阵），以及后整理下的<b>后整理设备</b>（后整理生产线、十台设备的动态图详解、"
                 "制造商之间真正的差异、制造商矩阵）。",
                 "侧边栏 → <b>Knowledge Base</b> → 纺织知识 → 机织 / 后整理 → <b>机器 &amp; 制造商</b>", "wn_onboarding.svg"),
                ("feature", "知识库：短纤维纺纱和织前准备",
                 "<b>纺织知识</b>下新增：<b>短纤维纺纱</b>——从纤维束到纱线，配有从开清棉到粗纱机、环锭纺、紧密纺、转杯纺和"
                 "喷气涡流纺的动画图示、捻度和速度计算器，以及羊毛的延伸介绍。机织下新增：<b>织前准备</b>——络筒、整经、"
                 "浆纱、牛仔布绳状染色、穿经和接经，并附有经轴数计算器。",
                 "侧边栏 → <b>Knowledge Base</b> → 纺织知识 → <b>短纤维纺纱</b> / 机织", "wn_onboarding.svg"),
                ("feature", "知识库：起始页「纺织链」",
                 "知识库现在以<b>纺织链</b>开篇：一张从纤维到成品织物的地图——单击某个环节（纺丝、变形、机织、后整理 ...）"
                 "即可查看其页面，绿点表示 Heberlein 技术。此外还有所有页面一览、覆盖整个链条的制造商矩阵（搜索、国家、"
                 "环节）以及尚缺的主题。",
                 "侧边栏 → <b>Knowledge Base</b> → <b>纺织链</b>（列表最上方）", "wn_onboarding.svg"),
                ("feature", "知识库：纤维和非织造布",
                 "<b>纺织知识</b>下新增两个类别：<b>纤维</b>，包含<b>化学纤维</b>（市场份额、13 种纤维简介及分子视图、性能"
                 "对比、各纤维的用途、再生比例）；以及<b>非织造布</b>（纤网成形和固结、从梳理到熔喷和针刺的十种动画工艺、"
                 "对比、交叉铺网机和针刺密度计算器）。旁边还有<b>天然纤维</b>：市场份额、从棉到羊绒的 10 种纤维简介、性能"
                 "对比以及各纤维的用途。所有这些也都在纺织链起始页上。",
                 "侧边栏 → <b>Knowledge Base</b> → 纺织知识 → <b>纤维</b> / <b>非织造布</b>", "wn_onboarding.svg"),
                ("feature", "知识库：前处理和纺织印花",
                 "<b>染色</b>下新增：<b>前处理</b>（烧毛、退浆、精练、漂白、丝光、热定型和工艺路线）和<b>纺织印花</b>，各有"
                 "八个动画场景——印花色浆、涂料或染料、直接印花、拔染印花和防染印花、平网、圆网、数码和转移印花，以及印花"
                 "如何固色。两者最后都附有测验。",
                 "侧边栏 → <b>Knowledge Base</b> → 纺织知识 → <b>染色</b>", "wn_onboarding.svg"),
                ("feature", "知识库：从加捻到成品",
                 "又新增五个动画页面，每页都有测验：<b>纱线加捻</b>（环锭加捻和倍捻、合股、花式纱）、<b>其他织物成形方法</b>"
                 "（横机针织、簇绒、编织）、<b>涂层和层压</b>（刮刀涂层、PVC 篷布、薄膜）、<b>成衣制作</b>（裁剪、线迹类型、"
                 "接缝密封、焊接）以及<b>织物测试</b>（拉伸和撕破强力、Martindale 耐磨、起球、色牢度、收缩）。所有这些都在"
                 "纺织链起始页上。",
                 "侧边栏 → <b>Knowledge Base</b> → 纺织知识", "wn_onboarding.svg"),
                ("feature", "知识库：假捻器详解",
                 "DTY → 专业知识下新增页面<b>假捻器</b>：以动画展示摩擦盘组——选择纤维、D/Y、纱线速度、摩擦盘组合（例如 "
                 "1-5-1）、PU 或陶瓷以及 S 或 Z 捻，查看摩擦盘转速以及 T2/T1 如何变化。此外还有摩擦盘类型、哪种纱线用哪种"
                 "摩擦盘、摩擦盘制造商、关键指标及其他加捻装置。在 <b>DTY 网络</b>（机器，位置 5）中双击假捻器，或在 "
                 "<b>DTY 机器</b>中双击摩擦盘，即可跳转到此处。",
                 "侧边栏 → <b>Knowledge Base</b> → 我们的技术 → DTY → 专业知识 → <b>假捻器</b>", "wn_onboarding.svg"),
                ("feature", "知识库：长丝纺丝中的喷嘴",
                 "纺丝 → 专业知识下新增页面<b>长丝纺丝中的喷嘴</b>：带有所有喷嘴的纺丝线（单击某个工位）、喷嘴组的头数和间距"
                 "是什么意思（带滑块）、纱道中发生了什么（网络或迁移、压力滑块、截面和侧视动画）、耗气量如何随纱道、压力和"
                 "头数变化，以及关键术语。在<b>长丝纺丝</b>（设备，工位 8）中双击喷嘴即可跳转到此处。",
                 "侧边栏 → <b>Knowledge Base</b> → 我们的技术 → 纺丝 → 专业知识 → <b>长丝纺丝中的喷嘴</b>",
                 "wn_onboarding.svg"),
                ("feature", "知识库：喷气涡流纺中的「纺纱太阳」和纺纱距离",
                 "<b>喷气涡流纺</b>的<i>纺纱喷嘴</i>场景已重新绘制为与真实喷嘴一样的剖面：倾斜的气孔正对空心锭子的尖端，"
                 "自由纤维端在锥形尖端上散开并绕其旋转，形成<b>纺纱太阳</b>——在剖面图和锭子尖端的俯视图中都能看到。新场景"
                 "<i>纺纱距离</i>：最后一个输出罗拉到锭子尖端的距离 S，带滑块——对于天然纤维，图表显示 S 如何改变平行纤维、"
                 "包缠纤维和被吹走的落纤所占的比例；对于合成短纤维，选择纤维长度即可看到参考值 S ≈ 0.55 × 纤维长度。",
                 "侧边栏 → <b>Knowledge Base</b> → 我们的技术 → 纺丝 → <b>喷气涡流纺</b> → 纺纱喷嘴 / 纺纱距离",
                 "wn_onboarding.svg"),
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
            # ═══════════════════════════════ ZH ═══════════════════════════════
            "zh": [
                ("h", "Show Experiment"),
                ("feature", "一张表看全系列的纱线",
                 "<b>Yarns…</b> 显示该系列的每一股及其纱线和每个试验。单击某种纱线即可为整股更换纱线——输入名称的一部分即可"
                 "找到，例如 <i>167 dty</i>。单击某个单元格可为单个试验开启或关闭某一股，输入 1-9 表示头数。<b>+ Add ply</b> "
                 "为所有试验添加一股。已更改的单元格显示为黄色，在 <b>Apply</b> 之前不会保存任何内容。",
                 "Show Experiment → Machine Data → <b>Yarns…</b>（或右键单击 Ply 行）", "wn_series_yarns.svg"),
                ("feature", "我的筒子在哪里？",
                 "Material 行中每一股后面的小筒子图标让你一目了然：绿色筒子 = 该纱线有库存，划掉的纸管 = 无库存。单击纱线或"
                 "绿色筒子，即可按存放位置查看库存中的每个筒子，包括批次、重量和纸管颜色。分配给该系列的筒子以粗体显示。"
                 "<b>Open in Yarn Stock</b> 直接带你跳到该纱线。",
                 "Show Experiment → Material 行 → 纱线或筒子图标", "wn_spool_locations.svg"),
                ("feature", "数值备注",
                 "直接在数值所在处记下它为什么是这样：右键单击某个数值 → <b>Add note…</b>，例如 <i>筒子有结，已重新测量</i>。"
                 "单元格上会有一个紫色小三角标记，鼠标指向时显示备注及姓名和日期。右键单击试验编号可为整个试验添加备注。"
                 "<b>Notes</b> 选项卡列出该系列的所有备注，双击即可跳到对应数值。每个人都可以写备注。在系列的 <b>Report</b> "
                 "中，<b>Notes</b> 按钮将备注显示为紫色轮廓，并在提示框中显示备注内容；除非导出时勾选 <i>Include notes on "
                 "values</i>，否则备注不会打印到 PDF 中。在 Smart Chart 仪表板中，可在 Points 视觉对象上勾选 <i>Show notes on "
                 "values</i>。",
                 "Show Experiment → 右键单击数值 → <b>Add note…</b>", "wn_cell_notes.svg"),
                ("feature", "参考样",
                 "将客户的原始筒子作为基准加入。它显示为一个高亮的 <i>Ref</i> 列，并在报告中显示为一条水平线——且从不计为"
                 "试验。",
                 "Show Experiment → Machine Data → <b>+ Ref</b>", "wn_reference.svg"),
                ("feature", "复制试验——可同时修改",
                 "选择要复制哪些试验、复制几次以及按什么顺序，并在复制前修改数值（例如气压、喷嘴、OF Core/Effect）。备注和"
                 "喷嘴前后的张力不会被复制——副本中这些字段为空。",
                 "Show Experiment → Machine Data → <b>Copy trials</b>", "wn_copy_trials.svg"),
                ("feature", "D/Y Ratio (T2/T1)",
                 "由 T1 和 T2 自动计算，在 DTY 机器上显示在 T2 Tension 的正下方。",
                 "Show Experiment → Machine Data", "wn_dy_ratio.svg"),
                ("feature", "更快地录入数据——像在 Excel 中一样",
                 "输入数值后按 <b>Enter</b>：光标移到下方单元格，可以直接输入下一个值（<b>Shift+Enter</b> 向上）。单击一个"
                 "单元格（或选择多个）并按 <b>Delete</b> 即可清空——无需双击。用 <b>Save</b> 或 <b>Ctrl+S</b> 保存；不再弹出"
                 "需要点掉的“已保存”提示，而是黄色消失，中间短暂亮起一个绿色勾号——你可以马上继续输入。",
                 "Show Experiment → 任意表格", None),
                ("feature", "用 Ctrl+Z 撤销",
                 "输错了数值、粘贴到了错误位置或删多了？<b>Ctrl+Z</b> 逐步撤销，<b>Ctrl+Y</b> 重做——只要你还没有保存。",
                 "Show Experiment → 任意表格", None),
                ("feature", "回到你的选项卡",
                 "系列会在你上次为它使用的选项卡上打开，例如 <i>Statimat M</i>，而不总是 <i>Machine Data</i>。",
                 "Show Experiment", None),
                ("feature", "隐藏不需要的行",
                 "右键单击参数名称 → <b>Hide row</b>。一条蓝线标出隐藏行的位置；单击它或使用 <b>n rows hidden</b> 可重新显示。"
                 "按机器分别记住。",
                 "Show Experiment → Machine Data → 右键单击参数名称", "wn_hide_rows.svg"),
                ("feature", "查看哪些内容尚未保存",
                 "已更改的单元格在保存之前（<b>Save</b> 或 <b>Ctrl+S</b>）一直显示为黄色。按钮会显示数量，例如 "
                 "<b>Save (3)</b>，选项卡上也会出现一个圆点。现在，在有未保存更改时关闭选项卡或程序会先询问——以前这些更改会"
                 "悄无声息地丢失。",
                 "Show Experiment", "wn_unsaved.svg"),
                ("feature", "保存时检查输入错误",
                 "远超出该机器常规范围的机器设定（例如 35 bar 而不是 3.5 bar）会在保存前列出。你可以返回修改，也可以照样保存。",
                 "Show Experiment → <b>Save</b>", "wn_unusual.svg"),
                ("feature", "更改历史（超级用户）",
                 "查看谁在何时更改了某个数值，以及更改前是什么——可针对单个数值或整个系列。",
                 "Show Experiment → 右键单击数值 → <b>Change history…</b>", "wn_history.svg"),
                ("feature", '报告：X 轴上的两个层级',
                 '在系列的报告中，每个图表现在都可以在 X 轴上显示两个层级——例如 <b>Yarn</b>（简称），其下为 <b>Jets</b>，只显示实际测试过的组合。在 X 右侧的新列表中选择第二个层级。<b>Yarn</b> 和 <b>Jet</b> 也可以单独选作 X。',
                 'Show Experiment → <b>Report</b> → X … › …', None),
                ("h", "Smart Chart"),
                ("feature", "全新的 Smart Chart：按属性查找试验",
                 "按纱线、喷嘴几何参数、机器设定和实验室结果在<b>所有</b>系列中挑选试验——例如所有终端细度为 70–80 dtex、"
                 "单丝数为 30–40 的涤纶试验。<b>+ Add filter</b> 显示数值的分布以及每个筛选条件剩下多少个试验；数值筛选可以"
                 "只保留整数、每 0.5 一档或你勾选的数值。然后在仪表板中显示：任意字段对任意字段——以散点、带 R² 的趋势线、"
                 "均值线、柱形、箱线图、小提琴图、直方图或密度图显示——按喷嘴、机器或某个数值着色，每台机器一个小图。图表上的 "
                 "⤢ 可将其放大显示，下方列出其试验：单击某个点可找到对应试验，双击可打开。可保存为视图（也可共享），导出为 "
                 "PDF 或 Excel。",
                 "侧边栏 → <b>Smart Chart</b>", "wn_smart_chart.svg"),
                ("feature", '这个比较公平吗？',
                 '每个图表上都有一个彩色圆点，当你比较的各组在其他会影响结果的方面也存在差异时发出警告——例如喷嘴 A 大多在 PES、3.5 bar 下测试，喷嘴 B 在 PA、2 bar 下测试。绿色、黄色或红色，并用一句话说明原因。单击圆点可查看每个条件；<b>Make it fairer</b> 只保留所有组共有的部分。它还会对很小的组、仅来自单个系列的组以及 X 范围不同的组发出警告。',
                 'Smart Chart → 图表标题栏中的彩色圆点', "wn_fairness.svg"),
                ("feature", '仪表板：像 Power BI 一样搭建自己的页面',
                 'Smart Chart 现在是一个仪表板：一个页面上并排放置多个视觉对象。从 <b>Fields</b> 中拖动字段——每张表，从 Statimat、Itemat 到 DTYoMat、喷嘴和纱线——到视觉对象的字段槽中。新的视觉对象：<b>Matrix</b>（例如按喷嘴和气压显示 FP/m 并着色——空单元格显示哪里缺少试验）、<b>Card</b>（一个数字）和 <b>Table</b>。单击柱形、箱线或矩阵单元格，其他所有视觉对象都会将其突出显示。<b>Slicers</b> 为整个页面选择数值——可以是列表、下拉框、磁贴或范围滑块。视觉对象可以自由放置和调整大小，可以使用多个页面（底部的选项卡），并可为单个页面或单个视觉对象添加筛选。新增：用你自己的公式创建<b>计算字段</b>、<b>目标</b>（绿/红、目标线）、机器 → 喷嘴的<b>向下钻取</b>，以及<b>选择点</b>来筛选页面。此外还有：<b>模板</b>（Jet comparison、Yarn overview、Machine check、Lab overview）、单页或全部页面的 <b>PDF</b>、按视觉对象或页面导出 <b>Excel</b>、数值备注、用 <b>Ctrl+Z</b> 撤销，以及一次<b>对齐</b>多个视觉对象（Ctrl+单击，然后对齐、统一大小或均匀分布）。',
                 '侧边栏 → <b>Smart Chart</b>', "wn_dashboard.svg"),
                ("feature", '仪表板中的实验室统计',
                 '统计<b>实验、试验系列或试验</b>的数量——按月份、产品组、订单类型、项目、负责人或实验室机器（<i>Tested on</i>）。新的视觉对象 <b>Columns</b> 以堆积、并列或 100 % 的方式显示；月份和年份按顺序排列，空月份显示为 0。从 <b>New</b> → <b>Lab statistics</b> 开始。月份或年份上的筛选现在可以是随日历移动的时间段：<b>This year</b>、<b>Last 12 months</b>、<b>From – to</b> …… 还有切片器 <b>Year › Month</b>：年份可以展开，下面是 1–12 月。',
                 'Smart Chart → <b>New</b> → <b>Lab statistics</b>', "wn_dashboard_stats.svg"),
                ("feature", '堆积字段：各部分如何累加',
                 '新的仪表板视觉对象 <b>Stacked fields</b> 将多个数值字段放在同一根柱中，每个字段有自己的颜色——例如每个试验 DTYoMat 的 A、B、C 网络点，以 <b>100 %</b>（各部分所占比例）或数值显示。将新字段 <b>Trial</b> 放在 X 轴上，每个试验就有一根柱。作为<b>组合图</b>，右侧第二坐标轴上的折线可在其上叠加显示例如 FP/m。',
                 'Smart Chart → Visualizations → <b>Stacked fields</b>', "wn_stacked_fields.svg"),
                ("feature", '视觉对象格式：排序、Top N、颜色、坐标轴、表格',
                 '仪表板中的视觉对象现在在 <b>Build</b> 旁有第二个选项卡 <b>Format</b>。可按数值或名称对柱形和箱线排序，并只显示<b>前 10 名</b>（例如最好的喷嘴）；设置<b>小数位数</b>；把<b>数值显示在柱上</b>；为柱形和均值线选择<b>误差线</b>——标准差、<b>95 % 置信区间</b>（两个喷嘴真的不同吗？如果误差线几乎不重叠，很可能是）、<b>最小 – 最大</b>或关闭；自己编写<b>坐标轴标题</b>或将其隐藏；固定 <b>Y 轴</b>的起点和终点；把<b>图例</b>移到顶部、底部或去掉；选择<b>调色板</b>或为每个值设置<b>自己的颜色</b>；放大或缩小文字和 <b>Card</b>，并关闭网格线。<b>表格</b>单击列标题即可排序，并可设置<b>颜色规则</b>（例如 FP/m 高于 100 显示为绿色）。<b>仪表板主题</b>（不选中任何对象时打开 Format）可一次为所有视觉对象设置调色板、文字大小、小数位数 ……；页面顶部的 <b>Copy format</b> 可将同样的格式应用到另一个视觉对象（双击：可应用于多个，Esc 结束）。每次更改都会立即显示；绿点标出与标准不同的设置，<b>Reset</b> 可恢复。PDF 中的显示效果也相同。',
                 'Smart Chart → 单击视觉对象 → Visualizations → <b>Format</b>', "wn_dashboard_format.svg"),
                ("feature", '与页面外观一致的仪表板 PDF',
                 '仪表板的 PDF 现在带有 Heberlein 标志，使用整个页面，文字也不再超出其框的边缘。<b>Slicers</b> 按你看到的样子打印：复选框、磁贴、范围滑块或带月份的年份。图表在<b>没有互联网连接</b>时也能正常显示。',
                 'Smart Chart → <b>PDF</b>', None),
                ("feature", '新的视觉对象：饼图、环形图、控制图、雷达图、文本',
                 '仪表板中新增五种视觉对象：用于显示占比的 <b>Pie</b> 和 <b>Donut</b>（单击某一块即可筛选页面）；带均值和 ±3σ 控制限的 <b>Control chart</b>——超出的点显示为红色，连续多点位于一侧显示为琥珀色；用于同时在多个数值上比较喷嘴、纱线或机器的 <b>Radar</b>；以及用于标题和说明的 <b>Text</b>。所有视觉对象也都换上了更清晰的新图标。',
                 'Smart Chart → Visualizations', "wn_dashboard_visuals.svg"),
                ("feature", '仪表板：分析线和钻取',
                 'Build 和 Format 旁新增选项卡 <b>Analytics</b>：平均值、中位数、± 1/2/3 倍标准差、百分位数、最小/最大值、常数线或从 – 到的区间带（例如你的规格限）直接显示在图表中——根据其中的试验计算。还有像 Power BI 一样的<b>钻取</b>：将某个页面设为例如 <b>Machine</b> 的详细信息页（Filters → <b>Drill-through to this page</b>），然后在另一个页面上右键单击某台机器的柱形 → <b>Drill through</b>。详细信息页只显示该机器；<b>← Back</b> 带你返回。',
                 'Smart Chart → Visualizations → <b>Analytics</b> · 右键单击柱形', "wn_dashboard_analytics.svg"),
                ("feature", '单击即突出显示——其余变灰',
                 '在仪表板中单击某个柱形、某根柱、某个扇区或某个点：其他视觉对象不再只跳到该部分，而是保留所有试验并将其余部分变灰，这样你就能看到该部分在整体中的位置——例如每根柱中有多少来自机器 AFK。被单击的视觉对象也会将其其他柱形变灰。其他试验的点变灰，平均值柱形会在淡化的柱形上叠加显示突出试验的平均值。Card、矩阵、表格、雷达图、箱线图、小提琴图和直方图仍然执行筛选，切片器也一样。再次单击即可取消。更喜欢原来的方式？不选中任何对象时打开 Format → <b>Clicks</b> → <i>Filters the other visuals</i>。',
                 'Smart Chart、Dashboards → 单击柱形、扇区或点', "wn_click_highlight.svg"),
                ("feature", '聚焦：放大一个视觉对象并显示其试验',
                 '单击视觉对象标题栏中的 ⤢：它会占满页面，下方列出构成它的所有试验。单击某个点可找到对应的行，双击某行可在 Show Experiment 中打开该试验。单击彩色公平性圆点可查看详情，并可使用 <b>Make it fairer</b>。<b>Format</b> 中现在还提供对数坐标轴、按颜色区分的标记形状以及点的大小。',
                 'Smart Chart → 视觉对象上的 ⤢', None),
                ("feature", '模型：各表之间如何关联',
                 '单击仪表板左上角的 <b>Model</b>：试验位于中央，周围是纱线、喷嘴、实验、时间以及所有实验室表，并显示它们的关联方式（1 : n = 每个试验有多行，取平均）。单击某张表可查看其字段以及有多少试验有数值。只读——此处无法更改任何内容。',
                 'Smart Chart → <b>Model</b>', "wn_model_view.svg"),
                ("feature", '以 Heberlein 配色为标准',
                 '图表和仪表板现在默认使用 <b>Heberlein</b> 调色板：先是 Heberlein 绿和标志的深蓝色，然后是易于区分的颜色。原来的八种绿色仍以 <b>Heberlein green</b> 保留。',
                 'Smart Chart → 单击视觉对象 → <b>Format</b> → Colours（不选中任何对象：适用于所有视觉对象）', None),
                ("feature", '侧边窗格可调宽窄',
                 '在仪表板中，拖动 <b>Filters</b>、<b>Visualizations</b> 或 <b>Fields</b> 的左边缘可使其变宽或变窄——TrippleT 会记住。双击边缘可恢复标准宽度。',
                 '侧边栏 → <b>Smart Chart</b>', None),
                ("feature", '仪表板：查看和共享',
                 '新页面 <b>Dashboards</b> 显示你自己的仪表板以及同事与你共享的仪表板。这里只用于查看：切片器、单击柱形筛选、向下钻取、页面选项卡和 <b>PDF</b> 都可使用——不会意外更改任何内容。要共享你的仪表板，请在 Smart Chart 中打开它并单击 <b>Share…</b>：可与所有人、单个人员或用户组（read、write、admin、superuser）共享，每次可选择<b>查看</b>或<b>编辑</b>。只有你可以共享或删除它。',
                 '侧边栏 → Tools → <b>Dashboards</b> · Smart Chart → <b>Share…</b>', "wn_dashboards.svg"),
                ("feature", '由超级用户决定谁可以使用哪个工具',
                 '在 <b>Manage User → Access…</b> 中，超级用户可以开启或关闭每个工具和界面——针对某个用户组（read、write、admin）或单个人员，例如为某位同事开启 Smart Chart，或为某个用户组关闭 Backlog。针对个人的设置优先于用户组设置；没有设置时一切照旧。被禁用的工具从下次登录起不再出现在侧边栏中。',
                 '侧边栏 → Superuser → Manage User → <b>Access…</b>', "wn_feature_access.svg"),
                ("h", "Settings"),
                ("feature", '选择你的起始界面',
                 '决定登录后打开哪个界面——Backlog（与以前一样）、All Experiments、Dashboards、Yarn Stock 或你使用的其他工具。如果超级用户为你关闭了该工具，则改为打开 Backlog。',
                 '侧边栏 → Account → <b>Settings</b> → <b>Start screen</b>', "wn_start_screen.svg"),
                ("feature", "整个程序的文字大小",
                 "Normal、Large、Extra large 或 Huge——按钮、菜单、表格和对话框都会随之变大。重启后生效。欢迎语和强调色也在这里"
                 "设置。",
                 "侧边栏 → Account → <b>Settings</b>", "wn_text_size.svg"),
                ("feature", "表格更易阅读",
                 "高对比度、行列十字准线、以大字显示数值的阅读条、警告符号以及色盲友好的配色。用 Ctrl + 鼠标滚轮缩放表格。",
                 "侧边栏 → Account → <b>Settings</b> → Show Experiment tables", "wn_reading.svg"),
                ("h", "帮助"),
                ("feature", "三种语言的帮助",
                 "Show Experiment、Backlog、Report、Smart Chart、Dashboards、All Experiments、Create Experiment、Manage Yarn 和 "
                 "Manage Jets 现在都有各自的英语、德语和西班牙语帮助：针对“我该如何……？”的分步解答、界面示意图以及规则。"
                 "用旗帜切换语言。",
                 "这些界面上的圆形 <b>?</b> 按钮", "wn_help.svg"),
                ("feature", "帮助搜索——“我在哪里可以找到……？”",
                 "用你自己的话输入问题，即可获得匹配的帮助页面——支持英语、德语或西班牙语。<b>Take me there</b> 会打开对应界面。",
                 "侧边栏 → <b>Help (F1)</b> 或 F1 键", "wn_help_search.svg"),
                ("feature", "在 Fresh off the Spool 中搜索",
                 "知道有某个功能，但不记得是哪个版本推出的？在版本列表上方的搜索框中输入一个词——会同时用英语、德语和西班牙语"
                 "搜索所有版本。有结果的版本会显示数量；单击即可跳转。每个版本现在按领域分为多个选项卡，例如 "
                 "<i>Show Experiment (8)</i>。",
                 "侧边栏 → Account → <b>Fresh off the Spool</b> → 搜索框", "wn_whats_new_search.svg"),
                ("feature", "Fresh off the Spool 导出为 PDF",
                 "将某个版本的新功能保存为 PDF——用于打印或发给同事。每个主题都保持在同一页上。",
                 "侧边栏 → Account → <b>Fresh off the Spool</b> → <b>PDF</b>", "wn_whats_new_pdf.svg"),
                ("h", "Backlog 和 All Experiments"),
                ("feature", "一次移动多张卡片",
                 "按住 <b>Ctrl</b> 单击各张卡片（或用 <b>Shift+单击</b> 选择一整段），然后拖动其中一张——所有选中的卡片会一起"
                 "移动，例如从 <i>To Be Cleaned</i> 移到 <i>Archived</i>。TrippleT 只询问一次，并会告诉你哪张卡片不允许移动。",
                 "Backlog → <b>Ctrl+单击</b>卡片 → 拖动", "wn_backlog_multi_move.svg"),
                ("feature", "宽屏上的 Backlog",
                 "在大显示器上，四列全部并排显示并占满整个高度。",
                 "Backlog", "wn_wide_backlog.svg"),
                ("feature", "Recycle Bin",
                 "已删除的试验系列可在 90 天内恢复。有权在 Backlog 中移动某个系列的人也可以删除它（在 To Be Cleaned 中：仅限"
                 "超级用户）。",
                 "侧边栏 → Superuser → <b>Recycle Bin</b>", "wn_recycle_bin.svg"),
                ("feature", "查看 Recycle Bin 中的内容",
                 "不确定某个已删除的系列包含什么？双击它：它会在 Show Experiment 中以只读方式打开。一个黄色横条让你选择 "
                 "<b>Restore for good</b>、<b>Back to Recycle Bin</b> 或 <b>Delete permanently</b>。关闭选项卡会将其放回——并"
                 "保留原来的删除日期。",
                 "侧边栏 → Superuser → <b>Recycle Bin</b> → 双击某个系列", "wn_recycle_preview.svg"),
                ("feature", "All Experiments 占满整个窗口",
                 "列表占满窗口的整个宽度和高度——最后几列无需横向滚动即可看到——并在大屏幕上显示得更大。",
                 "All Experiments", "wn_all_experiments.svg"),
                ("h", "纱线"),
                ("feature", "查看纱线的颜色",
                 "纱线名称前的小方块显示其颜色——黑色、白色、米色、灰色、本色。将鼠标悬停在上面可读出颜色名称。也可以按颜色"
                 "搜索，例如 <i>black</i>。颜色来自纱线的 <i>Colour</i> 字段（<b>Manage Yarn</b>）。",
                 "Yarns… 对话框、Create Experiment、Yarn Stock、Manage Yarn、Reassign Yarn、Show Experiment "
                 "（Ply 行）", "wn_yarn_colour.svg"),
                ("h", "Yarn Stock"),
                ("feature", "按纱线显示库存状态",
                 "交通灯现在按纱线整体显示：该纱线所有批次的库存与其最低库存的对比。已用完的批次从概览中消失，通知每种纱线"
                 "只发一次。只有超级用户可以更改最低库存。",
                 "Yarn Stock → 概览", "wn_stock_status.svg"),
                ("feature", "新筒子——直接跳到新筒子并进入标签队列",
                 "<b>New spool(s)</b> 以空白选择开始，完成后直接跳到新筒子。它们会自动进入标签队列（对话框中的复选框）。",
                 "Yarn Stock → <b>New spool(s)</b>", "wn_new_spools.svg"),
                ("feature", "盘点——逐个库位进行",
                 "超级用户发起一轮盘点（可以排除单个库位）。每个库位是一个磁贴：灰色 = 未盘点，绿色 = 全部正确，橙色 = 有差异。"
                 "单击一个库位并扫描其中的筒子（没有标签？在列表中双击它）。<b>Results</b> 显示在哪里找到了什么，可导出为 "
                 "Excel。位于其他位置的筒子会立即移库，缺失的筒子只在你结束盘点时——经询问后——才出库。",
                 "Yarn Stock → Rack lookup → <b>Stock take…</b>", "wn_stock_take.svg"),
                ("feature", "筒子历史",
                 "筒子的每次变更都会被记录：创建、更改、移库、出库、盘点。未选择筒子时，可查看整个批次，包括已用完的筒子。",
                 "Yarn Stock → <b>History…</b>", "wn_spool_history.svg"),
                ("feature", "扫描标签，保留更改",
                 "在 <i>Go to spool #</i> 中，可以扫描筒子标签，而不必输入编号。Yarn Stock 现在还会在未保存的筒子更改丢失前"
                 "先询问。三种语言的帮助：右上角的圆形按钮。",
                 "Yarn Stock → <b>Go to spool #</b>", None),
                ("h", "通用"),
                ("feature", "Fresh off the Spool：TrippleT 的新功能",
                 "每个版本的所有新功能集中在一处：每个领域一个选项卡，可搜索，也可导出为 PDF。新版本发布后会自动打开一次——"
                 "也可随时在侧边栏中打开。",
                 "侧边栏 → Account → <b>Fresh off the Spool</b>", "fresh_off_the_spool.png"),
                ("feature", "最近的系列",
                 "你最近打开的系列只需一次单击：侧边栏中的 <b>Recent</b>（在底部，Account 上方）。单击即可打开，"
                 "<b>Ctrl+单击</b>在新选项卡中打开。该列表在每台 PC 上都跟随你。",
                 "侧边栏 → <b>Recent</b>", None),
                ("feature", "Athena 用你的语言回答",
                 "Athena 和 Lab Assistant 现在用你提问时使用的语言回答——英语、德语、西班牙语 …… 没有提问时（例如自动分析），"
                 "回答为英语。",
                 "Show Experiment → Athena、Lab Assistant", None),
                ("feature", "有帮助的错误信息",
                 "出现问题时，TrippleT 现在会用通俗的话说明什么没成功、为什么，以及你可以怎么做——例如“该文件已在另一个程序中"
                 "打开——请关闭它（例如在 Excel 中）后重试。”技术性文字在 <b>Show Details</b> 下，可发送给管理员。",
                 "整个程序", None),
                ("feature", "所有文字均为英语",
                 "仍为德语的消息、按钮、菜单和状态文字现在全部改为英语——例如 Backlog 中的右键菜单显示 <b>Reassign yarn…</b>。"
                 "Kurzhocker 或 Langwelle 等实验室术语保持不变。",
                 "整个程序", None),
            ],
        },
    },
]

# "Fresh off the Spool" = the name of the release notes magazine (2026-10-16,
# before: "What's new"); English in every language like the button names.
WINDOW_TITLE = {"en": "Fresh off the Spool", "de": "Fresh off the Spool", "es": "Fresh off the Spool",
                "zh": "Fresh off the Spool"}
SUBTITLE = {"en": "What's new in TrippleT", "de": "Neues in TrippleT", "es": "Novedades de TrippleT",
            "zh": "TrippleT 新功能"}
VERSIONS_TITLE = {"en": "Versions", "de": "Versionen", "es": "Versiones", "zh": "版本"}
NEW_BADGE = {"en": "NEW", "de": "NEU", "es": "NUEVO", "zh": "新"}
WHERE_LABEL = {"en": "Where:", "de": "Wo:", "es": "Dónde:", "zh": "位置："}
VERSION_LABEL = {"en": "Version", "de": "Version", "es": "Versión", "zh": "版本"}
CURRENT_LABEL = {"en": "in progress", "de": "in Arbeit", "es": "en curso", "zh": "进行中"}
CLOSE = {"en": "Close", "de": "Schliessen", "es": "Cerrar", "zh": "关闭"}
SEARCH_PLACEHOLDER = {"en": "Search all versions…", "de": "Alle Versionen durchsuchen…",
                      "es": "Buscar en todas las versiones…",
                      "zh": "搜索所有版本…"}
SEARCH_RESULTS = {"en": "{n} result(s) for \"{q}\"", "de": "{n} Treffer für \"{q}\"",
                  "es": "{n} resultado(s) para \"{q}\"",
                  "zh": "“{q}”共有 {n} 个结果"}
SEARCH_NONE = {"en": "Nothing found for \"{q}\". Try another word - English, German and Spanish all work.",
               "de": "Nichts gefunden für \"{q}\". Versuche ein anderes Wort - Englisch, Deutsch und Spanisch gehen.",
               "es": "No se encontró nada para \"{q}\". Prueba otra palabra - sirven inglés, alemán y español.",
               "zh": "未找到“{q}”的相关内容。请换个词试试——英语、德语、西班牙语和中文都可以。"}
HITS_LABEL = {"en": "hits", "de": "Treffer", "es": "resultados", "zh": "个结果"}
PDF_TOOLTIP = {"en": "Save the shown version as PDF (e.g. to print or send it)",
               "de": "Die angezeigte Version als PDF speichern (z. B. zum Drucken oder Verschicken)",
               "es": "Guardar la versión mostrada como PDF (p. ej. para imprimirla o enviarla)",
               "zh": "将当前显示的版本保存为 PDF（例如用于打印或发送）"}
