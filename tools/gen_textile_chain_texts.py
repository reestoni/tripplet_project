"""Generate assets/onboarding/textile_chain_texts.js (module titles/summaries from ui/onboarding_catalog.py).

Run after adding a Knowledge Base module (and add its key to LINK_KEYS + a station in textile_chain.html):
    python tools/gen_textile_chain_texts.py
"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("TRIPPLET_MODE", "dev_local")
from ui import onboarding_catalog as cat

LANGS = ["de", "en", "es", "zh"]

def L(de, en, es, zh):
    return {"de": de, "en": en, "es": es, "zh": zh}

UI = {
    "eyebrow": L("Knowledge Base · Start", "Knowledge Base · Start", "Knowledge Base · Inicio", "Knowledge Base · 开始"),
    "h1": L("Von der Faser zum fertigen Stoff", "From fibre to finished fabric", "De la fibra al tejido acabado", "从纤维到成品面料"),
    "lead": L(
        "Alle Seiten der Knowledge Base entlang der textilen Prozesskette: Garnherstellung aus Stapelfasern und Filamenten, Texturieren, Flächenbildung, Veredlung, dazu Prüftechnik, Werkzeuge und Firmengeschichte. Dazu eine Herstellermatrix über die ganze Kette, gefüllt aus den Recherchen dieser Seiten.",
        "All pages of the Knowledge Base along the textile process chain: yarn production from staple fibres and filaments, texturing, fabric formation, finishing, plus testing, tools and company history. Also a manufacturer matrix across the whole chain, filled from the research behind these pages.",
        "Todas las páginas de la Knowledge Base a lo largo de la cadena textil: producción de hilo a partir de fibras cortadas y filamentos, texturizado, formación de tejido, acabado, además de ensayos, herramientas e historia de la empresa. Incluye una matriz de fabricantes de toda la cadena, elaborada a partir de la investigación de estas páginas.",
        "沿纺织工艺链排列的 Knowledge Base 全部页面：由短纤维和长丝生产纱线、变形加工、织物成形、整理，以及检测技术、工具和公司历史。另附覆盖整条产业链的制造商矩阵，数据来自这些页面背后的调研。"),
    "note": L(
        "Herstellerzuordnungen vereinfacht und nicht vollständig – Stand der Recherchen November 2026.",
        "Manufacturer assignments are simplified and not complete – research as of November 2026.",
        "Asignación de fabricantes simplificada e incompleta – estado de la investigación: noviembre de 2026.",
        "制造商归类已简化且并不完整——调研截至 2026 年 11 月。"),
    "sources": L("Quellen", "Sources", "Fuentes", "资料来源"),
    "srcIntro": L(
        "Die meisten Herstellerzuordnungen stammen aus den Quellenlisten der verlinkten Seiten. Zusätzlich für Spinnerei und Webereivorbereitung:",
        "Most manufacturer assignments come from the source lists of the linked pages. In addition, for spinning and weaving preparation:",
        "La mayoría de las asignaciones de fabricantes proceden de las listas de fuentes de las páginas enlazadas. Además, para hilatura y preparación de tejeduría:",
        "大多数制造商归类来自各链接页面的资料清单。纺纱和织造准备另参考了："),
    "open": L("Modul öffnen", "Open module", "Abrir módulo", "打开模块"),
    "openTool": L("Werkzeug öffnen", "Open tool", "Abrir herramienta", "打开工具"),
    "noPage": L("Noch keine eigene Seite.", "No page of its own yet.", "Todavía sin página propia.", "尚无独立页面。"),
    "pages": L("{n} Seiten", "{n} pages", "{n} páginas", "{n} 个页面"),
    "heb": L("Heberlein-Technologie", "Heberlein technology", "Tecnología Heberlein", "Heberlein 技术"),
    "lgHas": L("Station mit Seiten (Zahl = Anzahl)", "Station with pages (number = count)", "Estación con páginas (número = cantidad)", "有页面的工位（数字 = 页面数）"),
    "lgNone": L("noch keine eigene Seite", "no page of its own yet", "todavía sin página propia", "尚无独立页面"),
    "mapAria": L("Prozesslandkarte der Textilkette", "Process map of the textile chain", "Mapa del proceso de la cadena textil", "纺织产业链工艺地图"),
    "cols": [
        L("Rohstoff", "Raw material", "Materia prima", "原料"),
        L("Garnherstellung", "Yarn production", "Producción de hilo", "纱线生产"),
        L("Garnveredlung", "Yarn processing", "Transformación del hilo", "纱线加工"),
        L("Flächenbildung", "Fabric formation", "Formación de tejido", "织物成形"),
        L("Veredlung", "Finishing", "Acabado", "整理"),
        L("Produkt", "Product", "Producto", "产品"),
    ],
    "cross": L("Querschnittsthemen", "Cross-cutting topics", "Temas transversales", "跨领域主题"),
    "band": [
        L("Leinwand", "Plain", "Tafetán", "平纹"),
        L("Köper 2/2", "Twill 2/2", "Sarga 2/2", "斜纹 2/2"),
        L("Atlas 5", "Satin 5", "Raso 5", "缎纹 5"),
    ],
    "bandTip": L("Bindungslehre öffnen", "Open Weave structures", "Abrir Ligamentos", "打开织物组织"),
    "search": L("Firma suchen …", "Search company …", "Buscar empresa …", "搜索公司……"),
    "allCountries": L("Alle Länder", "All countries", "Todos los países", "所有国家"),
    "allStages": L("Alle Stufen", "All stages", "Todas las etapas", "所有环节"),
    "reset": L("Filter zurücksetzen", "Reset filters", "Restablecer filtros", "重置筛选"),
    "cnt": L("{n} von {m} Firmen", "{n} of {m} companies", "{n} de {m} empresas", "{m} 家公司中的 {n} 家"),
    "cntStage": L("{n} von {m} Firmen · Stufe: {s}", "{n} of {m} companies · stage: {s}", "{n} de {m} empresas · etapa: {s}", "{m} 家公司中的 {n} 家 · 环节：{s}"),
    "filterTip": L("Klick filtert auf diese Stufe", "Click to filter on this stage", "Clic para filtrar por esta etapa", "点击按此环节筛选"),
    "mxHead": [L("Firma", "Company", "Empresa", "公司"), L("Land", "Country", "País", "国家")],
    "mxNote": L(
        "Gruppen und Übernahmen sind vereinfacht: SSM gehört zur Rieter-Gruppe, Sperotto Rimar und SMIT zur Santex Rimar Group, Bonas zu Vandewiele, Schönherr zu Stäubli, Küsters und ramisch zu Andritz. Die Autoconer-Spulmaschinen (ursprünglich Schlafhorst/Saurer) erscheinen heute bei Rieter.",
        "Groups and takeovers are simplified: SSM belongs to the Rieter Group, Sperotto Rimar and SMIT to the Santex Rimar Group, Bonas to Vandewiele, Schönherr to Stäubli, Küsters and ramisch to Andritz. The Autoconer winding machines (originally Schlafhorst/Saurer) are now listed under Rieter.",
        "Grupos y adquisiciones simplificados: SSM pertenece al grupo Rieter, Sperotto Rimar y SMIT al Santex Rimar Group, Bonas a Vandewiele, Schönherr a Stäubli, Küsters y ramisch a Andritz. Las bobinadoras Autoconer (originalmente Schlafhorst/Saurer) figuran hoy en Rieter.",
        "集团与并购关系已简化：SSM 属于 Rieter 集团，Sperotto Rimar 和 SMIT 属于 Santex Rimar Group，Bonas 属于 Vandewiele，Schönherr 属于 Stäubli，Küsters 和 ramisch 属于 Andritz。Autoconer 络筒机（原属 Schlafhorst/Saurer）现归入 Rieter。"),
}

TAGS = {
    "o": L("Übersicht", "Overview", "Panorama", "概览"),
    "a": L("Animation", "Animation", "Animación", "动画"),
    "w": L("Werkzeug", "Tool", "Herramienta", "工具"),
}

TOOL = {
    "t": L("Yarn Count Converter", "Yarn Count Converter", "Yarn Count Converter", "Yarn Count Converter"),
    "d": L(
        "Feinheitssysteme umrechnen (dtex, den, Nm, Ne …) und den Filamentdurchmesser berechnen – Werkzeug in TrippleT.",
        "Convert count systems (dtex, den, Nm, Ne …) and compute the filament diameter – a TrippleT tool.",
        "Convertir sistemas de título (dtex, den, Nm, Ne …) y calcular el diámetro del filamento – herramienta de TrippleT.",
        "换算纤度单位（dtex、den、Nm、Ne……）并计算单丝直径——TrippleT 内置工具。"),
}

ST = {  # stations of the map
    "faser": (L("Naturfasern & Stapelfasern", "Natural & staple fibres", "Fibras naturales y cortadas", "天然纤维与短纤维"),
              L("Baumwolle, Wolle, geschnittene Chemiefasern", "Cotton, wool, cut man-made fibres", "Algodón, lana, fibras químicas cortadas", "棉、羊毛、切断的化学纤维")),
    "poly": (L("Polymer (PES, PA)", "Polymer (PES, PA)", "Polímero (PES, PA)", "聚合物（PES、PA）"),
             L("Granulat für das Schmelzspinnen", "Chips for melt spinning", "Granza para la hilatura por fusión", "用于熔融纺丝的切片")),
    "spin": (L("Stapelfaserspinnerei", "Staple fibre spinning", "Hilatura de fibra cortada", "短纤纺纱"), None),
    "mf": (L("Filamentspinnen POY / FDY", "Filament spinning POY / FDY", "Hilatura de filamento POY / FDY", "长丝纺丝 POY / FDY"), None),
    "tex": (L("Texturieren DTY · ATY · ACY", "Texturing DTY · ATY · ACY", "Texturizado DTY · ATY · ACY", "变形加工 DTY · ATY · ACY"), None),
    "prep": (L("Webereivorbereitung", "Weaving preparation", "Preparación de tejeduría", "织造准备"), None),
    "web": (L("Weben", "Weaving", "Tejeduría", "机织"), None),
    "masche": (L("Maschenware, Tuften & Flechten", "Knitting, tufting & braiding", "Punto, tufting y trenzado", "针织、簇绒与编织"), None),
    "vlies": (L("Vliesstoffe", "Nonwovens", "No tejidos", "非织造布"),
              L("Spunbond, Meltblown, Vernadeln, Wasserstrahlverfestigung", "Spunbond, meltblown, needle punching, hydroentanglement", "Spunbond, meltblown, punzonado, hidroligado", "纺粘、熔喷、针刺、水刺")),
    "farb": (L("Vorbehandeln, Färben & Drucken", "Pretreatment, dyeing & printing", "Preparación, tintura y estampación", "前处理、染色与印花"), None),
    "chem": (L("Chemische Ausrüstung & Beschichten", "Chemical finishing & coating", "Acabado químico y recubrimiento", "化学整理与涂层"), None),
    "mech": (L("Mechanische Ausrüstung & Maschinen", "Mechanical finishing & machines", "Acabado mecánico y máquinas", "机械整理与设备"), None),
    "stoff": (L("Konfektion", "Making-up", "Confección", "成衣加工"),
              L("Ziel der Kette", "End of the chain", "Final de la cadena", "产业链终点")),
    "pruef": (L("Garn- und Stoffprüfung", "Yarn & fabric testing", "Ensayos de hilo y tejido", "纱线与织物检测"), None),
    "tools": (L("Rechner & Werkzeuge", "Calculators & tools", "Calculadoras y herramientas", "计算器与工具"), None),
    "hist": (L("Firmengeschichte", "Company history", "Historia de la empresa", "公司历史"), None),
}

STAGES = {
    "sp": L("Kurzstapel-Spinnerei", "Short-staple spinning", "Hilatura de fibra corta", "短纤纺纱"),
    "wi": L("Spulen", "Winding", "Bobinado", "络筒"),
    "mf": L("Schmelzspinnen POY/FDY", "Melt spinning POY/FDY", "Hilatura por fusión POY/FDY", "熔融纺丝 POY/FDY"),
    "dt": L("Texturieren DTY", "Texturing DTY", "Texturizado DTY", "假捻变形 DTY"),
    "at": L("Lufttexturieren ATY", "Air texturing ATY", "Texturizado por aire ATY", "空气变形 ATY"),
    "ac": L("Air Covering", "Air covering", "Air covering", "空气包覆"),
    "wp": L("Webereivorbereitung", "Weaving preparation", "Preparación de tejeduría", "织造准备"),
    "wm": L("Webmaschinen", "Weaving machines", "Telares", "织机"),
    "fb": L("Fachbildung Schaft/Jacquard", "Shedding dobby/Jacquard", "Calada lizos/Jacquard", "开口 多臂/提花"),
    "tp": L("Teppichweben", "Carpet weaving", "Tejeduría de alfombras", "地毯织造"),
    "au": L("Ausrüstungsmaschinen", "Finishing machines", "Máquinas de acabado", "整理设备"),
    "be": L("Beschichtung", "Coating", "Recubrimiento", "涂层"),
    "ko": L("Düsen & Komponenten", "Jets & components", "Toberas y componentes", "喷嘴与部件"),
    "pr": L("Prüftechnik", "Testing", "Ensayos", "检测技术"),
    "ch": L("Textilchemie", "Textile chemicals", "Química textil", "纺织化学品"),
}

KPIS = [
    L("Seiten in der Knowledge Base", "pages in the Knowledge Base", "páginas en la Knowledge Base", "Knowledge Base 页面"),
    L("Stationen mit Inhalt", "stations with content", "estaciones con contenido", "有内容的工位"),
    L("Firmen in der Matrix", "companies in the matrix", "empresas en la matriz", "矩阵中的公司"),
    L("Prozessstufen in der Matrix", "process stages in the matrix", "etapas del proceso en la matriz", "矩阵中的工艺环节"),
    L("offene Stationen", "open stations", "estaciones pendientes", "待补充工位"),
]

SCENES = [
    (L("Prozesslandkarte", "Process map", "Mapa del proceso", "工艺地图"),
     L("Die Kette auf einen Blick", "The chain at a glance", "La cadena de un vistazo", "产业链一览"),
     L("Klick auf eine Station zeigt darunter ihre Seiten. Gestrichelte Stationen haben noch keine eigene Seite, die Zahl in der Ecke nennt die Anzahl Seiten, ein grüner Punkt markiert Heberlein-Technologie. Das Gewebeband oben öffnet die Bindungslehre.",
       "Click a station to see its pages below. Dashed stations have no page of their own yet, the number in the corner gives the number of pages, a green dot marks Heberlein technology. The weave band at the top opens Weave structures.",
       "Haga clic en una estación para ver sus páginas debajo. Las estaciones discontinuas aún no tienen página propia, el número de la esquina indica la cantidad de páginas y un punto verde marca tecnología Heberlein. La banda de tejido de arriba abre Ligamentos.",
       "点击工位即可在下方查看其页面。虚线框的工位尚无独立页面，角上的数字为页面数量，绿点表示 Heberlein 技术。顶部的织物条带可打开织物组织模块。")),
    (L("Alle Seiten", "All pages", "Todas las páginas", "全部页面"),
     L("Alle Seiten nach Prozessstufe", "All pages by process stage", "Todas las páginas por etapa", "按工艺环节排列的全部页面"),
     L("Jede Karte öffnet das Modul. {o} Hersteller, Bauformen, Vergleiche · {a} Funktionsweise, Lernanimation · {w} Rechner, Modell, Analyse",
       "Each card opens the module. {o} manufacturers, designs, comparisons · {a} how it works, learning animation · {w} calculator, model, analysis",
       "Cada tarjeta abre el módulo. {o} fabricantes, diseños, comparaciones · {a} funcionamiento, animación didáctica · {w} calculadora, modelo, análisis",
       "每张卡片都会打开对应模块。{o} 制造商、结构形式、对比 · {a} 工作原理、教学动画 · {w} 计算器、模型、分析")),
    (L("Herstellermatrix", "Manufacturer matrix", "Matriz de fabricantes", "制造商矩阵"),
     L("Wer ist wo in der Kette aktiv?", "Who is active where in the chain?", "¿Quién actúa en qué parte de la cadena?", "谁活跃在产业链的哪个环节？"),
     L("Zusammengetragen aus den Recherchen der verlinkten Seiten. {full} = belegt (Klick öffnet die passende Seite) · {hollow} = nur aus Markt- oder Gebrauchtmaschinenlisten. Leer heisst „hier nicht erfasst“, nicht „nicht im Programm“. Spaltenkopf anklicken filtert auf diese Stufe.",
       "Compiled from the research of the linked pages. {full} = documented (click opens the matching page) · {hollow} = only from market or used-machine lists. Empty means “not recorded here”, not “not in the range”. Click a column header to filter on that stage.",
       "Recopilado de la investigación de las páginas enlazadas. {full} = documentado (clic abre la página correspondiente) · {hollow} = solo de listas de mercado o de maquinaria usada. Vacío significa «no registrado aquí», no «no está en su gama». Haga clic en un encabezado de columna para filtrar por esa etapa.",
       "根据各链接页面的调研整理。{full} = 有据可查（点击打开对应页面）· {hollow} = 仅见于市场或二手设备清单。空白表示“此处未收录”，并非“不在产品范围内”。点击列标题可按该环节筛选。")),
    (L("Offene Themen", "Open topics", "Temas abiertos", "待补充主题"),
     L("Was noch fehlt", "What is still missing", "Lo que aún falta", "尚缺内容"),
     L("Stationen und Themen der Kette ohne eigene Seite – Kandidaten für die nächsten Ausbaustufen.",
       "Stations and topics of the chain without a page of their own – candidates for the next additions.",
       "Estaciones y temas de la cadena sin página propia – candidatos para las próximas ampliaciones.",
       "产业链中尚无独立页面的工位和主题——后续扩充的候选内容。")),
]

GAPS = [
    (L("Spulerei im Detail", "Winding in detail", "Bobinado en detalle", "络筒详解"),
     L("Kreuzspulautomaten und Spleissen – bisher nur als Teil der Webereivorbereitung (Zwirnen hat eine eigene Seite).",
       "Automatic cone winders and splicing – so far only as part of weaving preparation (twisting has its own page).",
       "Bobinadoras automáticas y empalme – hasta ahora solo como parte de la preparación de tejeduría (el retorcido tiene página propia).",
       "自动络筒机和捻接——目前仅作为织造准备的一部分出现（并捻已有独立页面）。")),
    (L("Maschenware: Maschinen & Hersteller", "Knitting: machines & manufacturers", "Punto: máquinas y fabricantes", "针织：设备与制造商"),
     L("Bisher Lernanimationen zu Rundstricken und Kettenwirken; keine Hersteller- und Verfahrensübersicht.",
       "So far learning animations on circular and warp knitting; no overview of manufacturers and processes.",
       "Hasta ahora animaciones didácticas de tricotado circular y por urdimbre; sin panorama de fabricantes y procesos.",
       "目前只有圆纬编和经编的教学动画，尚无制造商和工艺概览。")),
    (L("Hersteller Spinnerei", "Spinning manufacturers", "Fabricantes de hilatura", "纺纱设备制造商"),
     L("Die Spinnerei-Seite zeigt bewusst nur Verfahren; Maschinen und Hersteller fehlen noch.",
       "The spinning page deliberately shows only processes; machines and manufacturers are still missing.",
       "La página de hilatura muestra a propósito solo procesos; faltan aún máquinas y fabricantes.",
       "纺纱页面有意只介绍工艺，设备和制造商尚未收录。")),
    (L("Hersteller Webereivorbereitung", "Weaving preparation manufacturers", "Fabricantes de preparación de tejeduría", "织造准备设备制造商"),
     L("Die Webereivorbereitung zeigt bisher nur Verfahren; die Matrix enthält erste Hersteller aus der Recherche.",
       "Weaving preparation shows only processes so far; the matrix contains first manufacturers from the research.",
       "La preparación de tejeduría muestra hasta ahora solo procesos; la matriz incluye los primeros fabricantes de la investigación.",
       "织造准备页面目前只介绍工艺；矩阵中已收录调研得到的首批制造商。")),
]


def build(lang):
    ui = {}
    for k, v in UI.items():
        ui[k] = [x[lang] for x in v] if isinstance(v, list) else v[lang]
    mods = {m.key: {"t": m.title[lang], "d": m.summary[lang]} for m in cat.MODULES if m.key != cat.START_MODULE}
    return {
        "ui": ui,
        "scenes": [{"k": k[lang], "title": t[lang], "text": x[lang]} for k, t, x in SCENES],
        "kpis": [k[lang] for k in KPIS],
        "tags": {k: v[lang] for k, v in TAGS.items()},
        "tool": {"t": TOOL["t"][lang], "d": TOOL["d"][lang]},
        "st": {k: {"n": n[lang], "d": (d[lang] if d else "")} for k, (n, d) in ST.items()},
        "stages": {k: v[lang] for k, v in STAGES.items()},
        "gaps": [[t[lang], x[lang]] for t, x in GAPS],
        "mods": mods,
    }


out = {lang: build(lang) for lang in LANGS}
path = os.path.join(ROOT, "assets", "onboarding", "textile_chain_texts.js")
with open(path, "w", encoding="utf-8", newline="\n") as f:
    f.write("window.TEXTS = " + json.dumps(out, ensure_ascii=False, indent=1) + ";\n")
print("written", path)
