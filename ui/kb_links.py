# ui/kb_links.py
"""Links from the app into the Knowledge Base (Nutzerwunsch 2026-11-10):
right-click on a field -> "Learn more in Knowledge Base" -> popup with the
right module, scene and station (ui/widgets/kb_popup.py); closing it brings
the user back exactly where they were.

One table for all links. A target is (module key, scene, station), scene and
station 1-based as in the page parameters ?scene=&station= (None = page
default). tests/test_kb_links.py checks that every target exists.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

Target = tuple  # (module key, scene, station[, fibre id]) - fibre preselects a portrait

# ── DTY machines: station of the schema (ui/dty_stations.py) -> module page ──
# dty_intermingling scene 1 "Machine", stations 1-11 (see its _texts.js)
DTY_STATION_TARGET: Dict[str, Target] = {
    "creel": ("dty_intermingling", 1, 1),       # POY supply package
    "lw1": ("dty_intermingling", 1, 2),         # feed roll 1
    "heater1": ("dty_intermingling", 1, 3),     # primary heater
    "cooling": ("dty_intermingling", 1, 4),     # cooling plate
    "friction": ("dty_intermingling", 1, 5),    # friction unit
    "lw2": ("dty_intermingling", 1, 6),         # feed roll 2
    "mainjet": ("dty_intermingling", 1, 7),     # intermingling jet
    "lw2x": ("dty_intermingling", 1, 8),        # feed roll 2.x (overfeed)
    "setheater": ("dty_intermingling", 1, 9),   # set heater
    "lw3": ("dty_intermingling", 1, 10),        # feed roll 3
    "winder": ("dty_intermingling", 1, 11),     # take-up
    # cotton-like variants: pre-intermingling = variant D, jet 3 = variant E
    "lw0": ("cotton_like_dty", 4, None),
    "prejet": ("cotton_like_dty", 4, None),
    "jet3": ("cotton_like_dty", 5, None),
    "process": ("cotton_like_dty", 1, None),
}

# ── ATY machines: station of the schema (ui/aty_stations.py) -> module page ──
# aty_air_texturing scene 1 "Machine", stations 1-8 (see its _texts.js)
ATY_STATION_TARGET: Dict[str, Target] = {
    "creel": ("aty_air_texturing", 1, 1),       # creel, core + effect
    "draw": ("aty_air_texturing", 1, 2),        # feed rolls
    "feed": ("aty_air_texturing", 2, None),     # scene "Overfeed"
    "wetting": ("aty_air_texturing", 1, 3),
    "jet": ("aty_air_texturing", 3, None),      # scene "In the jet"
    "lw2": ("aty_air_texturing", 1, 5),
    "stabilise": ("aty_air_texturing", 1, 6),
    "lw3": ("aty_air_texturing", 1, 7),
    "winder": ("aty_air_texturing", 1, 8),
}

# DTY process (tbldtyprocess.Name, lower case) -> page; value cells only
DTY_PROCESS_TARGET: Dict[str, Target] = {
    "standard": ("dty_intermingling", 1, None),
    "elastane": ("dty_intermingling", 1, None),
    "cotton-like: effect at jet": ("cotton_like_dty", 1, None),
    "cotton-like: two jets": ("cotton_like_dty", 3, None),
    "cotton-like: before heater": ("cotton_like_dty", 4, None),
    "cotton-like: jet after set heater": ("cotton_like_dty", 5, None),
    "cotton-like: thick-thin": ("cotton_like_dty", 6, None),
    "cotton-like: filament breaking": ("cotton_like_dty", 7, None),
}

# ── lab tabs of Show Experiment: table attribute -> page ──────────────────
LAB_TABLE_TARGET: Dict[str, Target] = {
    "tbl_stat": ("statimat_tensile", 1, None),          # Statimat M: key figures
    "tbl_stat_ds": ("statimat_tensile", 1, None),       # Statimat DS
    "tbl_ekb": ("texturmat_crimp", 5, None),            # crimp key figures
    "tbl_hot_air_shrinkage": ("texturmat_crimp", 6, None),
    "tbl_hot_water_shrinkage": ("texturmat_crimp", 6, None),
    "tbl_itemat": ("itemat_knot_measurement", 6, None),  # evaluation
    "tbl_itemat_plus": ("itemat_knot_measurement", 6, None),
    "tbl_dtyomat": ("dty_intermingling", 4, None),      # nips and open sections
    "tbl_atyomat": ("aty_air_texturing", 4, None),      # yarn structure
    "tbl_rapid600": ("rapid_knot_test", 5, None),       # result per package
}

# ── materials (tblMaterial.Material, upper case) -> fibre portrait ──────
# scene 2 = "Fibre portraits"; the 4th element is the page parameter ?fibre=
_MMF, _NAT = "man_made_fibres", "natural_fibres"
MATERIAL_TARGET: Dict[str, Target] = {
    "PES": (_MMF, 2, None, "pes"),
    "PA 6": (_MMF, 2, None, "pa"),
    "PA 6.6": (_MMF, 2, None, "pa"),
    "PP": (_MMF, 2, None, "pp"),
    "PE": (_MMF, 2, None, "pe"),
    "PLA": (_MMF, 2, None, "pla"),
    "PVC": (_MMF, 2, None, "pvc"),
    "PAN": (_MMF, 2, None, "pan"),
    "EL": (_MMF, 2, None, "ela"),
    "PU": (_MMF, 2, None, "ela"),       # polyurethane = elastane fibre
    "CV": (_MMF, 2, None, "cv"),
    "MODAL": (_MMF, 2, None, "cv"),     # portrait "Viscose and modal"
    "CLY": (_MMF, 2, None, "cly"),
    "CA": (_MMF, 2, None, "ca"),
    "CTA": (_MMF, 2, None, "ca"),       # portrait "Acetate and triacetate"
    "AR": (_MMF, 2, None, "para"),
    "CO": (_NAT, 2, None, "bw"),
    "FL": (_NAT, 2, None, "fl"),
    "WO": (_NAT, 2, None, "wo"),
    "SE": (_NAT, 2, None, "se"),
}

# yarn types (tblGarntyp.Garntyp, upper case) -> process page
YARN_TYPE_TARGET: Dict[str, Target] = {
    "POY": ("filament_spinning", None, None),
    "FDY": ("filament_spinning", None, None),
    "FOY": ("filament_spinning", None, None),
    "HOY": ("filament_spinning", None, None),
    "IDY": ("filament_spinning", None, None),
    "BCF": ("bcf_spinning", None, None),
    "DTY": ("dty_intermingling", None, None),
    "SPUN": ("staple_spinning", None, None),
}

LABEL = "Learn more in Knowledge Base…"


def value_target(field: str, value) -> Optional[Target]:
    """Target for a material or yarn type value; field = column name or
    header (Material / Garntyp / Yarn type)."""
    f = str(field or "").strip().lower().replace(" ", "")
    v = str(value or "").strip().upper()
    if not v:
        return None
    if f in ("material", "materialid"):
        return MATERIAL_TARGET.get(v)
    if f in ("garntyp", "garntypid", "yarntype"):
        return YARN_TYPE_TARGET.get(v)
    return None


def install_table_menu(view, parent, source: str) -> None:
    """Right-click on a Material / Garntyp cell of a plain table view
    (Manage Yarn): "Learn more in Knowledge Base…"."""
    from PySide6.QtCore import Qt

    def _menu(pos):
        index = view.indexAt(pos)
        if not index.isValid():
            return
        model = view.model()
        header = model.headerData(index.column(), Qt.Horizontal, Qt.DisplayRole)
        target = value_target(header, model.data(index, Qt.DisplayRole))
        if not target:
            return
        from PySide6.QtWidgets import QMenu
        menu = QMenu(view)
        add_action(menu, parent, target, source)
        menu.exec(view.viewport().mapToGlobal(pos))

    view.setContextMenuPolicy(Qt.CustomContextMenu)
    view.customContextMenuRequested.connect(_menu)


def install_combo_menu(combo, parent, field: str, source: str) -> None:
    """Right-click on a Material / Garntyp drop-down (New/Edit Yarn)."""
    from PySide6.QtCore import Qt

    def _menu(pos):
        target = value_target(field, combo.currentText())
        if not target:
            return
        from PySide6.QtWidgets import QMenu
        menu = QMenu(combo)
        add_action(menu, parent, target, source)
        menu.exec(combo.mapToGlobal(pos))

    combo.setContextMenuPolicy(Qt.CustomContextMenu)
    combo.customContextMenuRequested.connect(_menu)
    combo.setToolTip("Right-click: learn more in the Knowledge Base")


def machine_row_target(screen, row: int, is_rd: bool = False) -> Optional[Target]:
    """Target for a data row of Machine Data / R&D Machine Data (DTY and ATY
    machines only, row = model row incl. header rows)."""
    if _is_dty(screen):
        from ui.dty_stations import station_of
        table = DTY_STATION_TARGET
    elif _is_aty(screen):
        from ui.aty_stations import station_of
        table = ATY_STATION_TARGET
    else:
        return None
    model = getattr(screen, "model_rd_machine" if is_rd else "model_machine", None)
    keys = getattr(screen, "_rd_machine_row_keys" if is_rd else "_machine_row_keys", None) or []
    dr = row - int(getattr(model, "_n_hdr", 0) or 0)
    if model is None or not 0 <= dr < len(keys):
        return None
    return table.get(station_of(keys[dr]) or "")


def machine_cell_target(screen, model, index, is_rd: bool = False) -> Optional[Target]:
    """Like machine_row_target(); a DTY Process cell leads to its own variant."""
    target = machine_row_target(screen, index.row(), is_rd)
    if target and target == DTY_STATION_TARGET["process"]:
        from PySide6.QtCore import Qt
        value = str(model.data(index, Qt.DisplayRole) or "").strip().lower()
        target = DTY_PROCESS_TARGET.get(value, target)
    return target


def table_target(screen, table) -> Optional[Target]:
    for attr, target in LAB_TABLE_TARGET.items():
        if getattr(screen, attr, None) is table:
            return target
    return None


def add_action(menu, parent, target: Optional[Target], source: str):
    """Adds "Learn more in Knowledge Base…" (with separator) to a menu."""
    if not target:
        return None
    if menu.actions():
        menu.addSeparator()
    act = menu.addAction(LABEL)
    # after the menu has closed: the popup runs its own event loop
    from PySide6.QtCore import QTimer
    act.triggered.connect(lambda: QTimer.singleShot(0, lambda: open_target(parent, target, source)))
    return act


def open_target(parent, target: Target, source: str = "") -> None:
    from ui.widgets.kb_popup import show_kb_popup
    key, scene, station = target[:3]
    params = {"fibre": target[3]} if len(target) > 3 and target[3] else None
    show_kb_popup(parent, key, scene, station, source=source, params=params)


def _is_dty(screen) -> bool:
    cache = getattr(screen, "_machine_cache", None)
    if cache is None:
        return False
    if "is_dty" not in cache:
        try:
            from db import dty_process
            # same expression as ui/dty_schema_panel._is_active() (shared cache key)
            cache["is_dty"] = dty_process.available() and dty_process.is_dty_machine(cache.get("machine_id"))
        except Exception:
            cache["is_dty"] = False
    return bool(cache.get("is_dty"))


def _is_aty(screen) -> bool:
    try:
        from ui.dty_schema_panel import _profile
        return _profile(screen) == "aty"
    except Exception:
        return False
