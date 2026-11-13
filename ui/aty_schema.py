"""aty_schema.py - ATY machine path above Machine Data in Show Experiment
(Nutzerwunsch 2026-11-11, "wie DTY"). Panel, button, table highlighting and
Knowledge Base links are shared with DTY in ui/dty_schema_panel.py; this
module paints one trial; its data comes from db/machine_schema.build_aty_path.

One lane per ply (core, effect, elastane, plies without yarn use), each
with its draw zone and feed roll. Only the core is wetted (Nutzerangabe
2026-11-11): the wetting sits on the top lane (core), the other lanes pass
it dry and join just before the jet; then LW 2, stabilising zone, LW 3,
winder.
"""
from __future__ import annotations

from typing import Any, Dict

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen

from db import machine_schema as _ms
from ui import aty_stations as st

# lane colours: core green like DTY, effect amber like the Knowledge Base page
C_CORE = QColor("#2E7D32")
C_EFFECT = QColor("#C08A1E")
C_ELASTANE = QColor("#8E24AA")
C_OTHER = QColor("#7A847A")
C_WATER = QColor("#2386C8")
ROLE_COLOUR = {"core": C_CORE, "effect": C_EFFECT, "elastane": C_ELASTANE}


def build_path(screen, col: int) -> Dict[str, Any]:
    """Path data of the trial in model column `col` (0-based data column) -
    rules in db/machine_schema.build_aty_path (shared with the web app)."""
    from ui import dty_schema_panel as dsp
    src = dsp._ModelSource(screen)
    if src.model is None or not src.specs or not (0 <= col < len(src.specs)):
        return {}
    return _ms.build_aty_path(src, col)


def paint(w, p: QPainter, d: Dict[str, Any], f: QFont, fb: QFont, fs: QFont) -> None:
    """Paints the ATY path on the DTYSchemaWidget `w` (uses its _station /
    _draw_creel helpers and hit list)."""
    fm_s = QFontMetrics(fs)
    p.setFont(fb)
    p.setPen(QColor("#2B2B2B"))
    p.drawText(QRectF(8, 4, w.LEFT - 10, 18), Qt.AlignLeft | Qt.AlignVCenter, d.get("title", ""))
    p.setFont(fs)
    p.setPen(C_CORE)
    p.drawText(QRectF(8, 18, w.LEFT - 10, 14), Qt.AlignLeft | Qt.AlignVCenter, d.get("process", ""))

    xs = w._col_x()
    p.setFont(f)
    for s, x in xs.items():
        p.setPen(QColor("#7A847A"))
        p.drawText(QRectF(x - 45, 8, 90, 16), Qt.AlignCenter, st.SHORT.get(s, s))

    plies = d.get("plies") or [{"idx": -1, "label": "", "pos": "", "yarn": "", "role": None,
                                 "values": {}, "tips": {}}]
    order = d.get("order") or list(range(len(plies)))
    lane_y = {k: w.TOP + n * w.LANE_H + 14 for n, k in enumerate(order)}
    y_main = lane_y[order[0]]
    x_end = xs.get("winder", w.width() - 30)
    per_ply = [s for s in xs if s in st.PER_PLY]
    # only the core is wetted: the other lanes join between wetting and jet
    x_join = xs.get("jet", x_end)
    x_before = xs.get("wetting", max((xs[s] for s in per_ply), default=w.LEFT))
    x_rise = (x_before + x_join) / 2

    for k in order:
        pl = plies[k]
        y = lane_y[k]
        colour = ROLE_COLOUR.get(pl.get("role") or "", C_OTHER)
        p.setPen(QPen(colour, 2.4))
        p.setBrush(Qt.NoBrush)
        path = QPainterPath(QPointF(w.LEFT - 8, y))
        if y == y_main:
            path.lineTo(QPointF(x_end + 18, y))
        else:
            path.lineTo(QPointF(x_rise - 14, y))
            path.cubicTo(QPointF(x_rise + 6, y), QPointF(x_rise + 6, y_main), QPointF(x_join - 18, y_main))
        p.drawPath(path)
        r_creel = QRectF(8, y - 15, w.LEFT - 18, 30)
        shown = dict(pl)
        if pl.get("role") and pl.get("ply"):
            shown["label"] = f"{pl['label']} · {pl['ply']}"
        w._draw_creel(p, r_creel, shown, fb, fs, colour, selected=w._is_sel("creel", pl["idx"]))
        w._hits.append((r_creel, "creel", pl["idx"]))
        if pl["tips"].get("creel"):
            w._tips[("creel", pl["idx"])] = pl["tips"]["creel"]
        for s in per_ply:
            w._station(p, s, xs[s], y, pl["idx"], pl["values"].get(s), pl["tips"].get(s), fs, fm_s)

    # the plies run together into one yarn from the jet on
    p.setPen(QPen(C_CORE, 3.0))
    p.drawLine(QPointF(x_join - 18, y_main), QPointF(x_end + 18, y_main))
    for s in xs:
        if s in st.PER_PLY:
            continue
        w._station(p, s, xs[s], y_main, -1, d["values"].get(s), d["tips"].get(s), fs, fm_s)
