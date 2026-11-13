# ui/onboarding_catalog.py
"""Catalogue of the onboarding modules (Nutzerwunsch 2026-11-06).

Each module = ONE self-contained web page in assets/onboarding/ (animation +
texts, no external resources, runs offline) plus its entry here. The page
takes ?lang=de|en|es|zh&embedded=1 and offers window.setLang(code); its texts
live in a sibling <name>_texts.js as `window.TEXTS = {...}` (strict JSON,
same structure in all languages - tests/test_onboarding.py checks that).

New module:
  1. assets/onboarding/<key>.html + <key>_texts.js (copy dty_intermingling as template);
     optional quiz: TEXTS[lang].quiz + <script src="quiz.js"> after the main script
  2. add a Module(...) below (title/summary in all LANGS)
  3. run the tests
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

LANGS = ("en", "de", "es", "zh")

# flags shown in the onboarding screen (help languages + Chinese)
LANGUAGES = [("en", "English", "flag_gb.svg"),
             ("de", "Deutsch", "flag_de.svg"),
             ("es", "Español", "flag_es.svg"),
             ("zh", "中文", "flag_cn.svg")]

# Top-level chapters of the list (Nutzerwunsch 2026-11-08); order = order in the list.
# Shown as headings only, an area without modules is not shown (e.g. "Textile knowledge"
# until its first module: weaving, knitting, ...).
AREAS: Dict[str, Dict[str, str]] = {
    "heberlein": {"en": "Heberlein", "de": "Heberlein", "es": "Heberlein", "zh": "Heberlein"},
    "technology": {"en": "Our technology", "de": "Unsere Technologie", "es": "Nuestra tecnología",
                   "zh": "我们的技术"},
    "knowledge": {"en": "Textile knowledge", "de": "Textiles Wissen", "es": "Conocimiento textil",
                  "zh": "纺织知识"},
}

# Start page of the Knowledge Base (Nutzerwunsch 2026-11-09, "Textilkette"): shown as
# the first, stand-alone entry above the areas and opened the first time; its module has
# category START_CATEGORY, which is deliberately NOT in CATEGORIES. Its page links every
# other module (tests/test_onboarding.py checks that), so a new module also belongs there.
START_MODULE = "textile_chain"
START_CATEGORY = "start"

CATEGORIES: Dict[str, Dict[str, str]] = {   # order = order in the list (spinning before texturing)
    "company": {"en": "Company", "de": "Unternehmen", "es": "Empresa", "zh": "公司"},
    "spinning": {"en": "Spinning", "de": "Spinnerei", "es": "Hilatura", "zh": "纺丝"},
    "dty": {"en": "DTY", "de": "DTY", "es": "DTY", "zh": "DTY"},
    "aty": {"en": "ATY", "de": "ATY", "es": "ATY", "zh": "ATY"},
    "ac": {"en": "AC", "de": "AC", "es": "AC", "zh": "AC"},
    "splicing": {"en": "Splicing", "de": "Spleissen", "es": "Empalme", "zh": "捻接"},
    "threading": {"en": "Threading", "de": "Einfädeln", "es": "Enhebrado", "zh": "穿丝"},
    "lab": {"en": "Our lab", "de": "Unser Labor", "es": "Nuestro laboratorio", "zh": "我们的实验室"},
    "tripplet": {"en": "Working with TrippleT", "de": "Arbeiten mit TrippleT",
                  "es": "Trabajar con TrippleT", "zh": "使用 TrippleT"},
    "fibres": {"en": "Fibres", "de": "Fasern", "es": "Fibras", "zh": "纤维"},
    "staple_spinning": {"en": "Staple fibre spinning", "de": "Stapelfaserspinnerei",
                        "es": "Hilatura de fibra corta", "zh": "短纤纺纱"},
    "weaving": {"en": "Weaving", "de": "Weben", "es": "Tejeduría", "zh": "机织"},
    "knitting": {"en": "Knitting", "de": "Stricken / Wirken", "es": "Tejido de punto", "zh": "针织"},
    "nonwovens": {"en": "Nonwovens", "de": "Vliesstoffe", "es": "No tejidos", "zh": "非织造布"},
    "dyeing": {"en": "Dyeing", "de": "Färben", "es": "Tintura", "zh": "染色"},
    "finishing": {"en": "Finishing", "de": "Veredlung", "es": "Acabado", "zh": "后整理"},
    "making_up": {"en": "Making-up", "de": "Konfektion", "es": "Confección", "zh": "成衣加工"},
    "fabric_testing": {"en": "Fabric testing", "de": "Stoffprüfung", "es": "Ensayos de tejidos", "zh": "织物检测"},
}

# area (AREAS key) of every category
CATEGORY_AREA: Dict[str, str] = {
    "company": "heberlein",
    "spinning": "technology", "dty": "technology", "aty": "technology", "ac": "technology", "splicing": "technology",
    "threading": "technology", "lab": "technology", "tripplet": "technology",
    "fibres": "knowledge", "staple_spinning": "knowledge", "weaving": "knowledge", "knitting": "knowledge", "nonwovens": "knowledge", "dyeing": "knowledge", "finishing": "knowledge",
    "making_up": "knowledge", "fabric_testing": "knowledge",
}

# sub-folders inside a category (Module.group); order = order in the list, after the plain modules
GROUPS: Dict[str, Dict[str, str]] = {
    "special": {"en": "Specialist knowledge", "de": "Spezialwissen", "es": "Conocimiento especializado",
                "zh": "专业知识"},
    "machines": {"en": "Machines & manufacturers", "de": "Maschinen & Hersteller", "es": "Máquinas y fabricantes",
                 "zh": "设备与制造商"},
}

# Quiz / Lernnachweis (assets/onboarding/quiz.js): last tab of a module, passed from QUIZ_PASS (same value as PASS in quiz.js)
QUIZ_PASS = 0.8
QUIZ_TAB = {"en": "Quiz", "de": "Quiz", "es": "Quiz", "zh": "测验"}

UI: Dict[str, Dict[str, str]] = {
    "kicker": {"en": "KNOWLEDGE BASE", "de": "KNOWLEDGE BASE", "es": "KNOWLEDGE BASE", "zh": "知识库"},
    "title": {"en": "Knowledge Base", "de": "Knowledge Base", "es": "Knowledge Base", "zh": "知识库"},
    "subtitle": {"en": "Short animated introductions to our work - pick a topic on the left.",
                 "de": "Kurze animierte Einführungen in unsere Arbeit - links ein Thema wählen.",
                 "es": "Introducciones animadas cortas a nuestro trabajo: elige un tema a la izquierda.",
                 "zh": "关于我们工作的简短动画介绍——请在左侧选择一个主题。"},
    "quizPassed": {"en": "Quiz passed: {r} of {t}", "de": "Quiz bestanden: {r} von {t}",
                   "es": "Quiz aprobado: {r} de {t}", "zh": "测验已通过：{r} / {t}"},
    "quizOpen": {"en": "Quiz: {r} of {t} (not passed yet)", "de": "Quiz: {r} von {t} (noch nicht bestanden)",
                 "es": "Quiz: {r} de {t} (aún no aprobado)", "zh": "测验：{r} / {t}（尚未通过）"},
    "missing": {"en": "This module could not be found.", "de": "Dieses Modul wurde nicht gefunden.",
                "es": "No se encontró este módulo.", "zh": "未找到该模块。"},
}


@dataclass
class Module:
    key: str                       # = file name without .html in assets/onboarding/
    category: str                  # key of CATEGORIES
    title: Dict[str, str]
    summary: Dict[str, str] = field(default_factory=dict)
    minutes: int = 2
    group: str = ""                # key of GROUPS = sub-folder inside the category ("" = directly)

    @property
    def file(self) -> str:
        return f"assets/onboarding/{self.key}.html"


MODULES: List[Module] = [
    Module(
        key=START_MODULE,
        category=START_CATEGORY,
        title={"en": "Textile chain", "de": "Textilkette", "es": "Cadena textil", "zh": "纺织产业链"},
        summary={"en": "Start: from fibre to finished fabric - process map with all pages, manufacturer matrix along the chain, open topics.",
                 "de": "Start: von der Faser zum fertigen Stoff - Prozesslandkarte mit allen Seiten, Herstellermatrix über die ganze Kette, offene Themen.",
                 "es": "Inicio: de la fibra al tejido acabado - mapa del proceso con todas las páginas, matriz de fabricantes a lo largo de la cadena, temas abiertos.",
                 "zh": "开始：从纤维到成品面料——包含所有页面的工艺地图、全产业链制造商矩阵、待补充主题。"},
        minutes=3,
    ),
    Module(
        key="heberlein_history",
        category="company",
        title={"en": "Company history", "de": "Firmengeschichte", "es": "Historia de la empresa",
               "zh": "公司历史"},
        summary={"en": "190 years: from yarn dyeing to Helanca, machine building and today's air jets.",
                 "de": "190 Jahre: von der Garnfärberei über Helanca und den Maschinenbau zu den Luftdüsen von heute.",
                 "es": "190 años: de la tintorería de hilo a Helanca, la construcción de máquinas y las toberas de hoy.",
                 "zh": "190 年：从纱线染色到 Helanca、机器制造，再到今天的空气喷嘴。"},
        minutes=4,
    ),
    Module(
        key="filament_spinning",
        category="spinning",
        title={"en": "Filament yarn spinning", "de": "Filamentgarnspinnerei", "es": "Hilatura de filamento",
               "zh": "长丝纺丝"},
        summary={"en": "From chips to POY and FDY - and where the Heberlein jets sit.",
                 "de": "Vom Granulat zu POY und FDY - und wo die Heberlein-Düsen sitzen.",
                 "es": "Del granulado al POY y FDY, y dónde están las toberas Heberlein.",
                 "zh": "从切片到 POY 和 FDY——以及 Heberlein 喷嘴的位置。"},
        minutes=3,
    ),
    Module(
        key="bcf_spinning",
        category="spinning",
        title={"en": "BCF carpet yarn", "de": "BCF-Teppichgarn", "es": "Hilo BCF para alfombras", "zh": "BCF 地毯丝"},
        summary={"en": "Spinning, drawing, hot-air texturing and interlacing in one step - carpet yarn.",
                 "de": "Spinnen, Verstrecken, Heissluft-Texturieren und Verwirbeln in einem Schritt - Teppichgarn.",
                 "es": "Hilatura, estirado, texturizado por aire caliente y entrelazado en un paso: hilo de alfombra.",
                 "zh": "纺丝、拉伸、热空气变形和网络一步完成——地毯丝。"},
        minutes=3,
    ),
    Module(
        key="air_jet_spinning",
        category="spinning",
        title={"en": "Air-jet spinning", "de": "Luftdüsenspinnen", "es": "Hilatura por chorro de aire", "zh": "喷气涡流纺纱"},
        summary={"en": "Staple fibres: drafting, vortex in the spinning jet, core and wrapper fibres.",
                 "de": "Stapelfasern: Verzug, Luftwirbel in der Spinndüse, Kern- und Umwindefasern.",
                 "es": "Fibras cortas: estiraje, remolino en la tobera, fibras de núcleo y envolventes.",
                 "zh": "短纤维：牵伸、纺纱喷嘴中的涡流、芯纤维与包缠纤维。"},
        minutes=2,
    ),
    Module(
        key="dty_intermingling",
        category="dty",
        title={"en": "DTY intermingling", "de": "DTY-Verwirbelung", "es": "Entrelazado DTY", "zh": "DTY 网络"},
        summary={"en": "From the POY to the nip: machine, overfeed, jet, nips.",
                 "de": "Vom POY zum Knoten: Maschine, Overfeed, Düse, Knoten.",
                 "es": "Del POY al nudo: máquina, sobrealimentación, tobera, nudos.",
                 "zh": "从 POY 到网络点：机器、超喂、喷嘴、网络点。"},
        minutes=2,
    ),
    Module(
        key="cotton_like_dty",
        category="dty",
        group="special",
        title={"en": "Cotton-like DTY", "de": "Cotton-like DTY", "es": "DTY tipo algodón", "zh": "仿棉 DTY"},
        summary={"en": "Seven ways to give a DTY the bulk, loops or hairiness of a spun yarn.",
                 "de": "Sieben Wege, wie ein DTY Volumen, Bögen oder Haarigkeit wie ein Spinngarn bekommt.",
                 "es": "Siete maneras de dar a un DTY el volumen, los bucles o la vellosidad de un hilo hilado.",
                 "zh": "让 DTY 获得短纤纱般蓬松、丝圈或毛羽的七种方法。"},
        minutes=4,
    ),
    Module(
        key="knot_stability",
        category="dty",
        group="special",
        title={"en": "Hard nips, less elongation?", "de": "Harte Knoten, weniger Dehnung?",
               "es": "¿Nudos duros, menos alargamiento?", "zh": "网络点越牢，伸长越低？"},
        summary={"en": "Hypothesis with a model: nip stability versus elongation at break and tenacity.",
                 "de": "These mit Modell: Knotenstabilität gegen Bruchdehnung und Höchstzugkraft.",
                 "es": "Hipótesis con un modelo: estabilidad del nudo frente a alargamiento a la rotura y fuerza máxima.",
                 "zh": "模型演示的假设：网络点牢度与断裂伸长和最大拉力的关系。"},
        minutes=3,
    ),
    Module(
        key="aty_air_texturing",
        category="aty",
        title={"en": "ATY air texturing", "de": "ATY-Lufttexturierung", "es": "Texturizado ATY por aire",
               "zh": "ATY 空气变形"},
        summary={"en": "Overfeed, texturing jet, loops: how air makes a bulky yarn.",
                 "de": "Voreilung, Texturierdüse, Schlingen: wie Luft ein voluminöses Garn macht.",
                 "es": "Sobrealimentación, tobera, bucles: cómo el aire crea un hilo voluminoso.",
                 "zh": "超喂、空气变形喷嘴、丝圈：空气如何制成蓬松纱线。"},
        minutes=2,
    ),
    Module(
        key="air_splicing",
        category="splicing",
        title={"en": "Air splicing of filament yarns", "de": "Filamentgarn-Spleissen", "es": "Empalme neumático de filamento",
               "zh": "长丝空气捻接"},
        summary={"en": "Joining two yarn ends with air, knot-free - and why the creel needs it.",
                 "de": "Zwei Garnenden mit Luft knotenfrei verbinden - und warum das Gatter das braucht.",
                 "es": "Unir dos extremos de hilo con aire, sin nudo, y por qué lo necesita la fileta.",
                 "zh": "用空气无结连接两个纱头——以及纱架为什么需要它。"},
        minutes=2,
    ),
    Module(
        key="itemat_knot_measurement",
        category="lab",
        title={"en": "Nip measurement with the ITEMAT", "de": "Knotenmessung mit dem ITEMAT",
               "es": "Medición de nudos con el ITEMAT", "zh": "ITEMAT 网络点测量"},
        summary={"en": "Counting nips and testing their stability: set-up, sensor, threshold, TSI, evaluation.",
                 "de": "Knoten zählen und ihre Stabilität prüfen: Aufbau, Sensor, Schwelle, TSI, Auswertung.",
                 "es": "Contar nudos y comprobar su estabilidad: montaje, sensor, umbral, TSI, evaluación.",
                 "zh": "统计网络点并测试其牢度：结构、传感器、阈值、TSI、评估。"},
        minutes=3,
    ),
    Module(
        key="statimat_tensile",
        category="lab",
        title={"en": "Count, tenacity and elongation (STATIMAT DS)", "de": "Titer, Festigkeit und Dehnung (STATIMAT DS)",
               "es": "Título, tenacidad y alargamiento (STATIMAT DS)", "zh": "纤度、强度和伸长（STATIMAT DS）"},
        summary={"en": "Automatic yarn testing: weighing for the count, tensile test by CRE, statistics per package.",
                 "de": "Automatische Garnprüfung: Wägen für den Titer, Zugversuch nach CRE, Statistik pro Spule.",
                 "es": "Ensayo automático de hilos: pesaje para el título, tracción CRE, estadística por bobina.",
                 "zh": "自动纱线测试：称重测纤度、CRE 拉伸试验、按丝筒统计。"},
        minutes=3,
    ),
    Module(
        key="texturmat_crimp",
        category="lab",
        title={"en": "Crimp and shrinkage (TEXTURMAT ME)", "de": "Kräuselung und Schrumpf (TEXTURMAT ME)",
               "es": "Rizado y contracción (TEXTURMAT ME)", "zh": "卷曲和收缩（TEXTURMAT ME）"},
        summary={"en": "Hank, heat treatment, five load steps: crimp contraction, modulus, stability and shrinkage.",
                 "de": "Strang, Wärmebehandlung, fünf Laststufen: Kräuselkontraktion, -modul, -beständigkeit und Schrumpf.",
                 "es": "Madeja, tratamiento térmico, cinco escalones de carga: contracción, módulo y estabilidad del rizado, y contracción térmica.",
                 "zh": "丝绞、热处理、五级负荷：卷曲收缩率、模量、稳定度和收缩。"},
        minutes=3,
    ),
    Module(
        key="rapid_knot_test",
        category="lab",
        title={"en": "Testing nips with the RAPID 600 V", "de": "Knotenprüfung mit dem RAPID 600 V",
               "es": "Ensayo de nudos con el RAPID 600 V", "zh": "RAPID 600 V 网络点检测"},
        summary={"en": "Needle method: count nips in the running yarn and check their firmness, good or weak.",
                 "de": "Nadelmethode: Knoten im laufenden Garn zählen und auf Festigkeit prüfen, gut oder schwach.",
                 "es": "Método de aguja: contar los nudos en el hilo en marcha y comprobar su firmeza, bueno o débil.",
                 "zh": "针刺法：在运行的丝上统计网络点并检测牢度，好或弱。"},
        minutes=3,
    ),
    Module(
        key="lufan_suction_gun",
        category="threading",
        title={"en": "Lufan suction gun", "de": "Lufan-Absaugpistole", "es": "Pistola de aspiración Lufan", "zh": "Lufan 吸丝枪"},
        summary={"en": "Threading up with the machine running: use, injector principle, variants and air consumption.",
                 "de": "Einfädeln bei laufender Maschine: Einsatz, Injektorprinzip, Varianten und Luftverbrauch.",
                 "es": "Enhebrar con la máquina en marcha: uso, principio del inyector, variantes y consumo de aire.",
                 "zh": "机器运行中穿丝：用途、引射器原理、型号和耗气量。"},
        minutes=2,
    ),
    Module(
        key="natural_fibres",
        category="fibres",
        title={"en": "Natural fibres", "de": "Naturfasern", "es": "Fibras naturales", "zh": "天然纤维"},
        summary={"en": "Market shares, 10 fibre portraits (seed, bast, hard and animal fibres), properties compared, application matrix.",
                 "de": "Marktanteile, 10 Faserporträts (Samen-, Bast-, Hart- und Tierfasern), Kennwerte im Vergleich, Einsatzmatrix.",
                 "es": "Cuotas de mercado, 10 retratos de fibras (semilla, líber, duras y animales), propiedades comparadas, matriz de aplicaciones.",
                 "zh": "市场份额、10 种纤维简介（种子、韧皮、硬质和动物纤维）、性能对比、应用矩阵。"},
        minutes=5,
    ),
    Module(
        key="man_made_fibres",
        category="fibres",
        title={"en": "Man-made fibres", "de": "Chemiefasern", "es": "Fibras químicas", "zh": "化学纤维"},
        summary={"en": "Market shares, 16 fibre portraits with molecule view, properties compared, application matrix, recycled shares.",
                 "de": "Marktanteile, 16 Faserporträts mit Molekülbild, Kennwerte im Vergleich, Einsatzmatrix, Recyclinganteile.",
                 "es": "Cuotas de mercado, 16 retratos de fibras con molécula, propiedades comparadas, matriz de aplicaciones, cuotas de reciclado.",
                 "zh": "市场份额、16 种纤维简介（含分子结构）、性能对比、应用矩阵、再生原料比例。"},
        minutes=6,
    ),
    Module(
        key="staple_spinning",
        category="staple_spinning",
        title={"en": "Staple fibre spinning", "de": "Stapelfaserspinnerei",
               "es": "Hilatura de fibra corta", "zh": "短纤纺纱"},
        summary={"en": "From tuft to yarn: process lines, blow room to roving frame, ring, compact, rotor and air-jet spinning, twist and speed, wool.",
                 "de": "Von der Flocke zum Garn: Prozesslinien, Putzerei bis Flyer, Ring-, Kompakt-, Rotor- und Luftspinnen, Drehung und Tempo, Wolle.",
                 "es": "Del copo al hilo: líneas de proceso, de la sala de apertura a la mechera, hilatura de anillo, compacta, de rotor y por chorro de aire, torsión y velocidad, lana.",
                 "zh": "从棉束到纱线：工艺路线、清花到粗纱、环锭纺、紧密纺、转杯纺和喷气纺、捻度与速度、羊毛。"},
        minutes=5,
    ),
    Module(
        key="yarn_twisting",
        category="staple_spinning",
        title={"en": "Yarn twisting", "de": "Zwirnen", "es": "Retorcido", "zh": "并捻"},
        summary={"en": "From single yarn to ply yarn: assembly winding, twist balance, ring and two-for-one twisting, direct cabling, fancy yarns, twist and uses.",
                 "de": "Vom Einfachgarn zum Zwirn: Fachen, Drehungsausgleich, Ring- und Doppeldrahtzwirnen, Kordieren, Effektzwirne, Drehung und Einsatz.",
                 "es": "Del hilo simple al retorcido: reunido, equilibrio de torsión, retorcido de anillo y a doble torsión, cableado directo, hilos de fantasía, torsión y usos.",
                 "zh": "从单纱到股线：并纱、捻度平衡、环锭捻线与倍捻、直捻、花式线、捻度与用途。"},
        minutes=6,
    ),
    Module(
        key="weaving_preparation",
        category="weaving",
        title={"en": "Weaving preparation", "de": "Webereivorbereitung",
               "es": "Preparación de tejeduría", "zh": "织造准备"},
        summary={"en": "Winding, warping, sizing, denim rope dyeing, drawing-in and tying-in - from yarn to a warp ready for the loom, with a beam calculator.",
                 "de": "Spulen, Schären, Schlichten, Denim-Strangfärben, Einziehen und Anknüpfen - vom Garn zur webbereiten Kette, mit Zettelbaum-Rechner.",
                 "es": "Bobinado, urdido, encolado, tintura en cuerda del denim, remetido y anudado: del hilo a la urdimbre lista para tejer, con calculadora de plegadores.",
                 "zh": "络筒、整经、浆纱、牛仔布绳状染色、穿经和结经——从纱线到可上机的经纱，附整经轴计算器。"},
        minutes=5,
    ),
    Module(
        key="shaft_weaving",
        category="weaving",
        title={"en": "Shaft weaving", "de": "Schaftweben", "es": "Tejeduría con lizos", "zh": "多臂/踏盘织造"},
        summary={"en": "Harness, drawing-in and lifting plan: how shafts make the weave.",
                 "de": "Webgeschirr, Einzug und Schaftprogramm: wie die Schäfte die Bindung machen.",
                 "es": "Lizos, remetido y programa de lizos: cómo los lizos crean el ligamento.",
                 "zh": "综框、穿综和提综程序：综框如何形成组织。"},
        minutes=3,
    ),
    Module(
        key="weave_structures",
        category="weaving",
        title={"en": "Weave structures", "de": "Bindungslehre", "es": "Ligamentos", "zh": "织物组织"},
        summary={"en": "Point paper, plain, twill and satin - and draw your own weave.",
                 "de": "Patrone, Leinwand, Köper und Atlas - und selbst eine Bindung zeichnen.",
                 "es": "Patrón, tafetán, sarga y raso, y dibuje su propio ligamento.",
                 "zh": "意匠图、平纹、斜纹和缎纹——还可以自己画组织。"},
        minutes=4,
    ),
    Module(
        key="jacquard_weaving",
        category="weaving",
        title={"en": "Jacquard weaving", "de": "Jacquardweben", "es": "Tejeduría Jacquard", "zh": "提花织造"},
        summary={"en": "Every warp thread lifted on its own: how a Jacquard machine weaves patterns.",
                 "de": "Jeder Kettfaden einzeln gehoben: wie eine Jacquardmaschine Muster webt.",
                 "es": "Cada hilo de urdimbre levantado por separado: cómo teje dibujos una máquina Jacquard.",
                 "zh": "每根经纱单独提升：提花机如何织出图案。"},
        minutes=3,
    ),
    Module(
        key="wilton_weaving",
        category="weaving",
        title={"en": "Wilton carpet", "de": "Wilton-Teppich", "es": "Alfombra Wilton", "zh": "威尔顿地毯"},
        summary={"en": "Woven pile carpet: wires, cut and loop pile, Jacquard colour choice.",
                 "de": "Gewebter Polteppich: Ruten, Schnitt- und Schlingenflor, Farbwahl per Jacquard.",
                 "es": "Alfombra de pelo tejida: varillas, pelo cortado y en bucle, elección de color Jacquard.",
                 "zh": "机织绒头地毯：起绒杆、割绒与圈绒、提花选色。"},
        minutes=3,
    ),
    Module(
        key="weaving_machines",
        category="weaving",
        group="machines",
        title={"en": "Weaving machines", "de": "Webmaschinen", "es": "Telares", "zh": "织机"},
        summary={"en": "Shedding, the five weft insertion systems, dobby, Jacquard and Wilton machines, differences, manufacturer matrix.",
                 "de": "Fachbildung, die fünf Schusseintragsarten, Schaft-, Jacquard- und Wilton-Maschinen, Unterschiede, Hersteller-Matrix.",
                 "es": "Formación de calada, los cinco sistemas de inserción de trama, telares de lizos, Jacquard y Wilton, diferencias, matriz de fabricantes.",
                 "zh": "开口、五种引纬方式、多臂/提花/威尔顿织机、差异、制造商矩阵。"},
        minutes=7,
    ),
    Module(
        key="circular_knitting",
        category="knitting",
        title={"en": "Circular knitting", "de": "Rundstricken", "es": "Tejido circular", "zh": "圆机针织"},
        summary={"en": "From yarn to tube: loop formation, cam track, single and double jersey.",
                 "de": "Vom Faden zum Schlauch: Maschenbildung, Schlossbahn, Single und Double Jersey.",
                 "es": "Del hilo al tubo: formación de malla, levas, single y double jersey.",
                 "zh": "从纱线到筒状织物：成圈、三角轨道、单面与双面针织。"},
        minutes=3,
    ),
    Module(
        key="warp_knitting",
        category="knitting",
        title={"en": "Warp knitting", "de": "Kettenwirken", "es": "Tejido de punto por urdimbre", "zh": "经编"},
        summary={"en": "Every needle gets its own thread: guide bars, lapping, point paper.",
                 "de": "Jede Nadel bekommt ihren eigenen Faden: Legeschienen, Legung, Punktpatrone.",
                 "es": "Cada aguja recibe su propio hilo: barras de guía, pasadas, papel de puntos.",
                 "zh": "每根针都有自己的纱线：梳栉、垫纱、垫纱图。"},
        minutes=3,
    ),
    Module(
        key="fabric_formation",
        category="knitting",
        title={"en": "Further fabric formation", "de": "Weitere Flächenbildung", "es": "Otras formas de crear tejido", "zh": "其他成布方法"},
        summary={"en": "Flat knitting with stitches and shaped knitting, tufting with gauge and carpet backing, braiding with carriers and braid angle.",
                 "de": "Flachstricken mit Bindungen und Formstricken, Tuften mit Teilung und Teppichrücken, Flechten mit Klöppeln und Flechtwinkel.",
                 "es": "Tricotado plano con ligamentos y tejido menguado, tufting con galga y dorso de alfombra, trenzado con husos y ángulo de trenzado.",
                 "zh": "横机编织与组织、成形编织，簇绒的针距与地毯背衬，编织的锭子与编织角。"},
        minutes=6,
    ),
    Module(
        key="nonwovens",
        category="nonwovens",
        title={"en": "Nonwovens", "de": "Vliesstoffe", "es": "No tejidos", "zh": "非织造布"},
        summary={"en": "Forming and bonding the web: process lines, carding to meltblown, needle punching to chemical bonding, comparison, crosslapper and punch density calculator.",
                 "de": "Vlies bilden und verfestigen: Prozesslinien, Krempeln bis Meltblown, Vernadeln bis chemisch, Vergleich, Kreuzleger- und Einstichdichte-Rechner.",
                 "es": "Formar y consolidar el velo: líneas de proceso, del cardado al meltblown, del punzonado a la consolidación química, comparación, calculadora de plegador y densidad de punzonado.",
                 "zh": "成网与加固：工艺路线、从梳理到熔喷、从针刺到化学粘合、对比、交叉铺网与针刺密度计算器。"},
        minutes=5,
    ),
    Module(
        key="textile_pretreatment",
        category="dyeing",
        title={"en": "Pretreatment", "de": "Vorbehandlung", "es": "Preparación", "zh": "前处理"},
        summary={"en": "Impurities in greige goods, singeing, desizing, scouring, bleaching, mercerising, heat setting, process routes.",
                 "de": "Begleitstoffe der Rohware, Sengen, Entschlichten, Abkochen, Bleichen, Mercerisieren, Thermofixieren, Verfahrenswege.",
                 "es": "Impurezas del tejido crudo, chamuscado, desencolado, descrudado, blanqueo, mercerizado, termofijado, rutas de proceso.",
                 "zh": "坯布中的伴生物、烧毛、退浆、煮练、漂白、丝光、热定形、工艺路线。"},
        minutes=6,
    ),
    Module(
        key="textile_dyeing",
        category="dyeing",
        title={"en": "Dyeing", "de": "Färben", "es": "Tintura", "zh": "染色"},
        summary={"en": "Dye classes, dyeing stages, exhaust and continuous processes, machines, indigo, barré in DTY.",
                 "de": "Farbstoffklassen, Färbestufen, Auszieh- und Kontinueverfahren, Maschinen, Indigo, Barré bei DTY.",
                 "es": "Clases de colorantes, etapas de tintura, agotamiento y continuo, máquinas, índigo, barré en DTY.",
                 "zh": "染料类别、染色阶段、浸染与连续染色、设备、靛蓝、DTY 横档。"},
        minutes=6,
    ),
    Module(
        key="textile_printing",
        category="dyeing",
        title={"en": "Textile printing", "de": "Textildruck", "es": "Estampación textil", "zh": "纺织印花"},
        summary={"en": "Print paste, pigment or dye, direct/discharge/resist, flat screen, rotary, digital, transfer, fixation.",
                 "de": "Druckpaste, Pigment oder Farbstoff, Direkt-/Ätz-/Reservedruck, Flachfilm, Rotation, Digital, Transfer, Fixieren.",
                 "es": "Pasta de estampación, pigmento o colorante, directa/corrosión/reserva, lionesa, rotativa, digital, transferencia, fijación.",
                 "zh": "印花色浆、涂料或染料、直接/拔染/防染印花、平网、圆网、数码、转移印花、固色。"},
        minutes=6,
    ),
    Module(
        key="poy_spinning_plants",
        category="spinning",
        group="machines",
        title={"en": "POY spinning plants", "de": "POY-Spinnanlagen", "es": "Plantas de hilatura POY", "zh": "POY 纺丝设备"},
        summary={"en": "From polymer to POY package: variants, plant layouts, manufacturers and models, winders, market.",
                 "de": "Vom Polymer zur POY-Spule: Varianten, Anlagenlayouts, Hersteller und Modelle, Wickler, Markt.",
                 "es": "Del polímero a la bobina POY: variantes, layouts, fabricantes y modelos, bobinadoras, mercado.",
                 "zh": "从聚合物到 POY 丝筒：类型、设备布局、制造商与型号、卷绕机、市场。"},
        minutes=5,
    ),
    Module(
        key="fdy_spinning_plants",
        category="spinning",
        group="machines",
        title={"en": "FDY spinning plants", "de": "FDY-Spinnanlagen", "es": "Plantas de hilatura FDY", "zh": "FDY 纺丝设备"},
        summary={"en": "Spinning, drawing, setting and winding in one step: variants, layouts, manufacturers, comparison, market.",
                 "de": "Spinnen, Verstrecken, Fixieren und Wickeln in einem Schritt: Varianten, Layouts, Hersteller, Vergleich, Markt.",
                 "es": "Hilar, estirar, fijar y bobinar en un paso: variantes, layouts, fabricantes, comparación, mercado.",
                 "zh": "纺丝、拉伸、定型和卷绕一步完成：类型、布局、制造商、对比、市场。"},
        minutes=5,
    ),
    Module(
        key="filament_jets",
        category="spinning",
        group="special",
        title={"en": "Jets in filament spinning", "de": "Düsen in der Filamentspinnerei",
               "es": "Toberas en la hilatura de filamento", "zh": "长丝纺丝中的喷嘴"},
        summary={"en": "Basics: spinning line with all jets, ends and pitch, what happens in the yarn channel, air consumption, terms.",
                 "de": "Grundkurs: Spinnlinie mit allen Düsen, Fachung und Teilung, was im Fadenkanal passiert, Luftverbrauch, Begriffe.",
                 "es": "Curso básico: línea de hilatura con todas las toberas, cabos y paso, qué pasa en el canal del hilo, consumo de aire, términos.",
                 "zh": "基础课程：带全部喷嘴的纺丝线、头数与间距、纱道内的过程、耗气量、术语。"},
        minutes=4,
    ),
    Module(
        key="dty_machines",
        category="dty",
        group="machines",
        title={"en": "DTY machines", "de": "DTY-Maschinen", "es": "Máquinas DTY", "zh": "DTY 加弹机"},
        summary={"en": "Yarn path of a DTY position, variants, machine profiles, manufacturers and models, market.",
                 "de": "Fadenlauf einer DTY-Position, Varianten, Maschinenprofile, Hersteller und Modelle, Markt.",
                 "es": "Recorrido del hilo de una posición DTY, variantes, perfiles de máquina, fabricantes y modelos, mercado.",
                 "zh": "DTY 锭位的走纱路线、类型、机器剖面、制造商与型号、市场。"},
        minutes=5,
    ),
    Module(
        key="dty_friction_unit",
        category="dty",
        group="special",
        title={"en": "Friction unit", "de": "Friktionsaggregat", "es": "Grupo de fricción", "zh": "摩擦假捻器"},
        summary={"en": "Disc stack animation with D/Y and disc speed, PU vs. ceramic, choice per fibre, disc manufacturers, key figures and alternatives.",
                 "de": "Scheibenstapel als Animation mit D/Y und Drehzahl, PU gegen Keramik, Wahl je Faserstoff, Scheibenhersteller, Kennzahlen und Alternativen.",
                 "es": "Animación de la pila de discos con D/Y y velocidad, PU frente a cerámica, elección según la fibra, fabricantes de discos, indicadores y alternativas.",
                 "zh": "摩擦盘叠动画（含 D/Y 与转速）、PU 与陶瓷对比、按纤维选型、摩擦盘制造商、关键参数与替代方案。"},
        minutes=4,
    ),
    Module(
        key="aty_machines",
        category="aty",
        group="machines",
        title={"en": "ATY machines", "de": "ATY-Maschinen", "es": "Máquinas ATY", "zh": "ATY 空气变形机"},
        summary={"en": "Yarn path of an ATY position, variants, machine designs, manufacturers and models, market.",
                 "de": "Fadenlauf einer ATY-Position, Varianten, Bauformen, Hersteller und Modelle, Markt.",
                 "es": "Recorrido del hilo de una posición ATY, variantes, tipos de máquina, fabricantes y modelos, mercado.",
                 "zh": "ATY 锭位的走纱路线、类型、机型结构、制造商与型号、市场。"},
        minutes=5,
    ),
    Module(
        key="air_covering",
        category="ac",
        title={"en": "Air covering (ACY)", "de": "Air Covering (ACY)",
               "es": "Air covering (ACY)", "zh": "空气包覆纱 (ACY)"},
        summary={"en": "Elastane and DTY bonded by air: process with live calculation, inside the jet, yarn structure, ACY vs. SCY/DCY, uses.",
                 "de": "Elastan und DTY per Luft verbunden: Prozess mit Live-Rechnung, in der Düse, Garnstruktur, ACY vs. SCY/DCY, Einsatz.",
                 "es": "Elastano y DTY unidos por aire: proceso con cálculo en vivo, dentro de la boquilla, estructura, ACY vs. SCY/DCY, usos.",
                 "zh": "以空气结合氨纶与 DTY：带实时计算的工艺、喷嘴内部、纱线结构、ACY 与 SCY/DCY、应用。"},
        minutes=6,
    ),
    Module(
        key="ac_machines",
        category="ac",
        group="machines",
        title={"en": "AC machines", "de": "AC-Maschinen", "es": "Máquinas AC", "zh": "空气包覆机"},
        summary={"en": "Three machine variants, catalogue with filters, speed comparison, regions, milestones, jets.",
                 "de": "Drei Maschinenvarianten, Katalog mit Filtern, Geschwindigkeitsvergleich, Regionen, Meilensteine, Düsen.",
                 "es": "Tres variantes de máquina, catálogo con filtros, comparación de velocidad, regiones, hitos, boquillas.",
                 "zh": "三种机型、可筛选的设备目录、速度对比、地区、里程碑、喷嘴。"},
        minutes=5,
    ),
    Module(
        key="chemical_finishing",
        category="finishing",
        title={"en": "Chemical finishing", "de": "Chemische Textilausrüstung",
               "es": "Acabado químico", "zh": "化学后整理"},
        summary={"en": "Finishing chain, effect atlas, application methods, PFAS phase-out, regulation, suppliers.",
                 "de": "Veredlungskette, Effekt-Atlas, Auftragsverfahren, PFAS-Ausstieg, Regulierung, Anbieter.",
                 "es": "Cadena de acabado, atlas de efectos, métodos de aplicación, salida de PFAS, normativa, proveedores.",
                 "zh": "后整理流程、功能图谱、施加方法、PFAS 淘汰、法规、供应商。"},
        minutes=6,
    ),
    Module(
        key="mechanical_finishing",
        category="finishing",
        title={"en": "Mechanical finishing", "de": "Mechanische Textilausrüstung",
               "es": "Acabado mecánico", "zh": "机械后整理"},
        summary={"en": "Goals, process atlas, machines in detail, key figures, sustainability, manufacturers.",
                 "de": "Ziele, Verfahrens-Atlas, Maschinen im Detail, Kennzahlen, Nachhaltigkeit, Hersteller.",
                 "es": "Objetivos, atlas de procesos, máquinas en detalle, indicadores, sostenibilidad, fabricantes.",
                 "zh": "目标、工艺图谱、设备详解、关键指标、可持续性、制造商。"},
        minutes=6,
    ),
    Module(
        key="coating",
        category="finishing",
        title={"en": "Coating and laminating", "de": "Beschichten und Kaschieren", "es": "Recubrimiento y laminado", "zh": "涂层与复合"},
        summary={"en": "Coating or laminating, knife coating, transfer coating, PVC plastisol, polymers, membranes, laminating methods, layer build-up and test values.",
                 "de": "Beschichten oder Kaschieren, Rakelverfahren, Transferbeschichtung, PVC-Plastisol, Polymere, Membranen, Kaschierverfahren, Lagenaufbau und Prüfwerte.",
                 "es": "Recubrir o laminar, recubrimiento con rasqueta, recubrimiento por transferencia, plastisol de PVC, polímeros, membranas, métodos de laminado, estructura de capas y valores de ensayo.",
                 "zh": "涂层还是复合、刮刀涂层、转移涂层、PVC 增塑糊、聚合物、薄膜、复合方法、层结构与测试指标。"},
        minutes=6,
    ),
    Module(
        key="finishing_machines",
        category="finishing",
        group="machines",
        title={"en": "Finishing machines", "de": "Ausrüstungsmaschinen",
               "es": "Máquinas de acabado", "zh": "后整理设备"},
        summary={"en": "Finishing line, 10 machines in detail, where manufacturers differ, manufacturer matrix.",
                 "de": "Ausrüstungslinie, 10 Maschinen im Detail, wo sich Hersteller unterscheiden, Hersteller-Matrix.",
                 "es": "Línea de acabado, 10 máquinas en detalle, en qué difieren los fabricantes, matriz de fabricantes.",
                 "zh": "后整理生产线、10 种设备详解、制造商差异、制造商矩阵。"},
        minutes=6,
    ),
    Module(
        key="making_up",
        category="making_up",
        title={"en": "Making-up", "de": "Konfektion", "es": "Confección", "zh": "成衣加工"},
        summary={"en": "Spreading, marker and waste, cutting, lockstitch, ISO 4915 stitch types, seam sealing, welding, product examples.",
                 "de": "Legen, Schnittbild und Verschnitt, Zuschnitt, Doppelsteppstich, Sticharten nach ISO 4915, Nahtabdichtung, Schweissen, Produktbeispiele.",
                 "es": "Extendido, marcada y desperdicio, corte, pespunte, tipos de puntada ISO 4915, sellado de costuras, soldadura, ejemplos de productos.",
                 "zh": "铺布、排料与损耗、裁剪、锁式线迹、ISO 4915 线迹类型、接缝密封、焊接、产品示例。"},
        minutes=6,
    ),
    Module(
        key="fabric_testing",
        category="fabric_testing",
        title={"en": "Fabric testing", "de": "Stoffprüfung", "es": "Ensayos de tejidos", "zh": "织物检测"},
        summary={"en": "Standard atmosphere, tensile strength, tearing, Martindale, pilling, wash/rub and light fastness, dimensional change.",
                 "de": "Normklima, Höchstzugkraft, Weiterreissen, Martindale, Pilling, Wasch-/Reib- und Lichtechtheit, Massänderung.",
                 "es": "Atmósfera normal, tracción, desgarro, Martindale, pilling, solidez al lavado, al frote y a la luz, cambio dimensional.",
                 "zh": "标准大气、断裂强力、撕破强力、马丁代尔耐磨、起球、耐洗/耐摩擦及耐光色牢度、尺寸变化。"},
        minutes=6,
    ),
]


def module_texts(key: str) -> Dict[str, Any]:
    """TEXTS of a module page (assets/onboarding/<key>_texts.js, strict JSON
    after `window.TEXTS =`). {} if missing/broken."""
    from ui.pathutil import resource_path
    try:
        raw = open(resource_path(f"assets/onboarding/{key}_texts.js"), encoding="utf-8").read()
        return json.loads(re.sub(r"^\s*window\.TEXTS\s*=\s*", "", raw).rstrip().rstrip(";"))
    except Exception:
        return {}


def scene_names(key: str, lang: str) -> List[str]:
    """Scene names (tab labels in the onboarding screen) in this language.
    A module with a quiz (TEXTS[lang].quiz) gets the extra last tab "Quiz"."""
    texts = module_texts(key)
    t = texts.get(lang) or texts.get("en") or {}
    names = [str(sc.get("k") or "") for sc in t.get("scenes", [])]
    if t.get("quiz"):
        names.append(text(QUIZ_TAB, lang))
    return names


_SCENE_BASE: Dict[str, int] = {}


def scene_param_base(key: str) -> int:
    """1 if the page reads ?scene= 1-based (go((+params.get('scene')||1)-1)),
    0 if 0-based (parseInt(params.get('scene')||'0')) - both styles exist.
    Used by the KB popup (ui/widgets/kb_popup.py) and the web app."""
    if key not in _SCENE_BASE:
        mod = next((m for m in MODULES if m.key == key), None)
        try:
            from ui.pathutil import resource_path
            src = open(resource_path(mod.file), encoding="utf-8").read() if mod else ""
        except Exception:
            src = ""
        _SCENE_BASE[key] = 1 if "(+params.get('scene')||1)-1" in src else 0
    return _SCENE_BASE[key]


def quiz_passed(right: int, total: int) -> bool:
    return total > 0 and right / total >= QUIZ_PASS - 1e-9


def text(d: Dict[str, str], lang: str) -> str:
    return d.get(lang) or d.get("en") or next(iter(d.values()), "")
