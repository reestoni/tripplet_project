# ui/kb_search.py
"""Knowledge Base pages in the F1 help search (Nutzerwunsch 2026-11-10).

Index: per module and language (EN/DE/ES like the help search) one entry
for the module (title + summary), one per scene (tab name + scene title,
the scene texts as body) and one per machine station (name + explanation).
Entries reuse help_search.HelpEntry with screen = "kb"; the key carries the
target: "kb:<module>:<scene>:<station>" (1-based, 0 = none). help_search
ranks them separately and shows them after the help answers; a click opens
the popup (ui/widgets/kb_popup.py).
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

from ui import onboarding_catalog as cat

SCREEN = "kb"
LANGS = ("en", "de", "es")

# scene (1-based) in which a module draws its clickable stations
STATION_SCENE = {
    "dty_intermingling": 1, "aty_air_texturing": 1, "air_jet_spinning": 1, "bcf_spinning": 1,
    "filament_spinning": 1, "cotton_like_dty": 1,
    "statimat_tensile": 2, "itemat_knot_measurement": 2, "rapid_knot_test": 2,
}
_BODY_MAX = 4000   # characters of scene text per entry (enough for the key words)

_INDEX = None


def _strings(obj: Any, out: List[str]) -> None:
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _strings(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _strings(v, out)


def _body(obj: Any) -> str:
    """All texts of a scene/station as distinct words (the search only needs
    each word once - keeps building the index fast)."""
    from ui.widgets.help_search import normalize
    parts: List[str] = []
    _strings(obj, parts)
    seen = dict.fromkeys(normalize(" ".join(parts)).split())
    return " ".join(seen)[:_BODY_MAX]


def make_key(module: str, scene: Optional[int] = None, station: Optional[int] = None) -> str:
    return f"kb:{module}:{scene or 0}:{station or 0}"


def parse_key(key: str) -> Optional[Tuple[str, Optional[int], Optional[int]]]:
    try:
        _, module, scene, station = key.split(":")
        return module, (int(scene) or None), (int(station) or None)
    except ValueError:
        return None


def build_index():
    from ui.widgets.help_search import HelpEntry
    entries = []
    for m in cat.MODULES:
        try:
            texts = cat.module_texts(m.key)
        except Exception:
            continue
        for lang in LANGS:
            t = texts.get(lang) or {}
            title = cat.text(m.title, lang)
            entries.append(HelpEntry(make_key(m.key), SCREEN, "", lang, title,
                                     [cat.text(m.summary, lang)], "").prepare())
            for i, sc in enumerate(t.get("scenes") or [], start=1):
                if not isinstance(sc, dict):
                    continue
                name = " – ".join(x for x in (str(sc.get("k") or ""), str(sc.get("title") or "")) if x)
                if not name:
                    continue
                entries.append(HelpEntry(make_key(m.key, i), SCREEN, "", lang, f"{title} › {name}",
                                         [_body(sc)], "").prepare())
            st_scene = STATION_SCENE.get(m.key)
            stations = t.get("stations") or []
            if st_scene and isinstance(stations, list):
                for j, st in enumerate(stations, start=1):
                    name = str(st.get("n") or "") if isinstance(st, dict) else str(st or "")
                    if not name:
                        continue
                    entries.append(HelpEntry(make_key(m.key, st_scene, j), SCREEN, "", lang,
                                             f"{title} › {name}", [_body(st)], "").prepare())
    return entries


def get_index():
    global _INDEX
    if _INDEX is None:
        _INDEX = build_index()
    return _INDEX


def summary(key: str, lang: str) -> str:
    """Module summary for the detail view."""
    target = parse_key(key)
    mod = next((m for m in cat.MODULES if target and m.key == target[0]), None)
    return cat.text(mod.summary, lang) if mod else ""
