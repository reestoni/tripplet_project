"""Knowledge Base links from the app (ui/kb_links.py): every target must be an
existing module with a valid scene and station, so links never lead nowhere."""
import json
import os

import pytest

from ui import kb_links
from ui import onboarding_catalog as cat
from ui.dty_stations import FIELD_STATION, STATIONS
from ui.pathutil import resource_path


def _texts(key):
    mod = next(m for m in cat.MODULES if m.key == key)
    path = resource_path(mod.file).replace(".html", "_texts.js")
    s = open(path, encoding="utf-8").read()
    return json.loads(s[s.index("{"):s.rindex("}") + 1])


ALL_TARGETS = (list(kb_links.DTY_STATION_TARGET.items()) + list(kb_links.ATY_STATION_TARGET.items()) + list(kb_links.DTY_PROCESS_TARGET.items())
               + list(kb_links.LAB_TABLE_TARGET.items()))


@pytest.mark.parametrize("name,target", ALL_TARGETS)
def test_target_exists(name, target):
    key, scene, station = target
    assert any(m.key == key for m in cat.MODULES), name
    mod = next(m for m in cat.MODULES if m.key == key)
    assert os.path.exists(resource_path(mod.file))
    en = _texts(key)["en"]
    if scene is not None:
        assert 1 <= scene <= len(en["scenes"]), name
    if station is not None:
        assert 1 <= station <= len(en["stations"]), name


def test_station_keys_are_schema_stations():
    codes = {k for k, _, _ in STATIONS}
    assert set(kb_links.DTY_STATION_TARGET) <= codes
    # every station that has machine fields leads somewhere (elastane: no page yet)
    used = set(FIELD_STATION.values()) - {"elastane"}
    assert used <= set(kb_links.DTY_STATION_TARGET)


def test_process_names_match_seed():
    from db.dty_process import SEED
    names = {str(row[2]).lower() for row in SEED}
    assert set(kb_links.DTY_PROCESS_TARGET) == names


def test_lab_tables_exist_on_screen():
    src = open(resource_path("ui/screen_show_experiment.py"), encoding="utf-8").read()
    for attr in kb_links.LAB_TABLE_TARGET:
        assert f"self.{attr} = FrozenFirstColumnTable" in src, attr


# ── Etappe 3: materials / yarn types, F1 search ──────────────────────────
import re


def _fids(key):
    mod = next(m for m in cat.MODULES if m.key == key)
    src = open(resource_path(mod.file), encoding="utf-8").read()
    return re.findall(r"'([a-z]+)'", re.search(r"const FIDS=\[([^\]]*)\]", src).group(1))


def test_material_targets_have_a_portrait():
    for code, target in kb_links.MATERIAL_TARGET.items():
        key, scene, _st, fibre = target
        en = _texts(key)["en"]
        assert en["scenes"][scene - 1]["k"] == "Fibre portraits", code
        assert fibre in _fids(key), (code, fibre)


def test_materials_cover_the_material_table_codes():
    # codes of tblMaterial (dev_local/prod, 2026-11-10); new materials need an entry
    codes = {"AR", "CA", "CO", "CTA", "CV", "EL", "MODAL", "PA 6", "PA 6.6", "PAN", "PES", "PE", "PLA",
             "PP", "PU", "PVC", "CLY", "FL", "WO", "SE"}
    assert codes <= set(kb_links.MATERIAL_TARGET)


def test_value_target():
    assert kb_links.value_target("Material", "pes")[3] == "pes"
    assert kb_links.value_target("Garntyp", "DTY")[0] == "dty_intermingling"
    assert kb_links.value_target("Titer", "84") is None
    for target in kb_links.YARN_TYPE_TARGET.values():
        assert any(m.key == target[0] for m in cat.MODULES)


def test_kb_search_keys_are_valid():
    from ui import kb_search
    for e in kb_search.get_index():
        key, scene, station = kb_search.parse_key(e.key)
        assert any(m.key == key for m in cat.MODULES)
        if scene:
            assert 1 <= scene <= len(cat.scene_names(key, "en"))


def test_help_search_kb_hits_come_after_help_answers():
    from ui.widgets.help_search import search
    hits = search("Friktion", with_kb=True)
    assert any(h.screen == "kb" and "dty_intermingling" in h.key for h in hits)
    hits = search("alle Aufträge einer Maschine", with_kb=True)
    assert hits[0].screen == "all_experiments"
    screens = [h.screen for h in hits]
    if "kb" in screens:
        assert all(s == "kb" for s in screens[screens.index("kb"):])
    assert sum(s == "kb" for s in screens) <= 5


def test_scene_param_base_known_for_every_page():
    # every page must read ?scene= in one of the two known styles, else the
    # popup would open the wrong scene
    from ui.widgets.kb_popup import scene_param_base
    for m in cat.MODULES:
        src = open(resource_path(m.file), encoding="utf-8").read()
        if "params.get('scene')" not in src:
            continue
        one = "(+params.get('scene')||1)-1" in src
        zero = "params.get('scene')||'0'" in src
        assert one != zero, m.key
        assert scene_param_base(m.key) == (1 if one else 0)
