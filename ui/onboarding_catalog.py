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

CATEGORIES: Dict[str, Dict[str, str]] = {   # order = order in the list (spinning before texturing)
    "spinning": {"en": "Spinning", "de": "Spinnerei", "es": "Hilatura", "zh": "纺丝"},
    "dty": {"en": "DTY", "de": "DTY", "es": "DTY", "zh": "DTY"},
    "aty": {"en": "ATY", "de": "ATY", "es": "ATY", "zh": "ATY"},
    "splicing": {"en": "Splicing", "de": "Spleissen", "es": "Empalme", "zh": "捻接"},
    "threading": {"en": "Threading", "de": "Einfädeln", "es": "Enhebrado", "zh": "穿丝"},
    "lab": {"en": "Lab", "de": "Labor", "es": "Laboratorio", "zh": "实验室"},
    "tripplet": {"en": "Working with TrippleT", "de": "Arbeiten mit TrippleT",
                  "es": "Trabajar con TrippleT", "zh": "使用 TrippleT"},
}

# sub-folders inside a category (Module.group); order = order in the list, after the plain modules
GROUPS: Dict[str, Dict[str, str]] = {
    "special": {"en": "Specialist knowledge", "de": "Spezialwissen", "es": "Conocimiento especializado",
                "zh": "专业知识"},
}

# Quiz / Lernnachweis (assets/onboarding/quiz.js): last tab of a module, passed from QUIZ_PASS (same value as PASS in quiz.js)
QUIZ_PASS = 0.8
QUIZ_TAB = {"en": "Quiz", "de": "Quiz", "es": "Quiz", "zh": "测验"}

UI: Dict[str, Dict[str, str]] = {
    "kicker": {"en": "ONBOARDING", "de": "ONBOARDING", "es": "ONBOARDING", "zh": "入门"},
    "title": {"en": "Onboarding", "de": "Onboarding", "es": "Onboarding", "zh": "入门培训"},
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


def quiz_passed(right: int, total: int) -> bool:
    return total > 0 and right / total >= QUIZ_PASS - 1e-9


def text(d: Dict[str, str], lang: str) -> str:
    return d.get(lang) or d.get("en") or next(iter(d.values()), "")
