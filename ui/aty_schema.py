"""aty_schema.py - ATY machine path above Machine Data in Show Experiment
(Nutzerwunsch 2026-11-11, "wie DTY"). Panel, button, table highlighting and
Knowledge Base links are shared with DTY in ui/dty_schema_panel.py; this
module only builds the data of one trial and paints it.

One lane per ply (core, effect, elastane, plies without yarn use), each
with its draw zone and feed roll. Only the core is wetted (Nutzerangabe
2026-11-11): the wetting sits on the top lane (core), the other lanes pass
it dry and join just before the jet; then LW 2, stabilising zone, LW 3,
winder.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen

from ui import aty_stations as st

# lane colours: core green like DTY, effect amber like the Knowledge Base page
C_CORE = QColor("#2E7D32")
C_EFFECT = QColor("#C08A1E")
C_ELASTANE = QColor("#8E24AA")
C_OTHER = QColor("#7A847A")
C_WATER = QColor("#2386C8")
ROLE_COLOUR = {"core": C_CORE, "effect": C_EFFECT, "elastane": C_ELASTANE}


def _helpers():
    from ui import dty_schema_panel as dsp
    return dsp


def _summary(model, keys, station: str, c: int) -> Optional[str]:
    dsp = _helpers()
    parts = []
    for key, fmt in st.SUMMARY.get(station, []):
        if key in keys:
            v = dsp._display(model, keys.index(key), c)
            if st.filled(v):
                parts.append(fmt.format(v))
    return "\n".join(parts[:2]) or None


def _tip(model, keys, station: str, c: int) -> Optional[str]:
    dsp = _helpers()
    lines = []
    for r in st.rows_of_station(keys, station):
        v = dsp._display(model, r, c)
        if st.filled(v):
            lines.append(f"{model._row_titles[r]}: {v}")
    return "\n".join(lines) or None


def _add_line(tips: Dict[str, Any], station: str, line: str) -> None:
    tips[station] = (tips.get(station) + "\n" if tips.get(station) else "") + line


def build_path(screen, col: int) -> Dict[str, Any]:
    """Path data of the trial in model column `col` (0-based data column)."""
    dsp = _helpers()
    model = getattr(screen, "model_machine", None)
    specs = getattr(screen, "_machine_col_specs", None) or []
    keys = list(getattr(screen, "_machine_row_keys", None) or [])
    if model is None or not specs or not (0 <= col < len(specs)):
        return {}
    tid = specs[col]["trial_id"]
    cols = [i for i, cs in enumerate(specs) if cs["trial_id"] == tid]
    c0 = cols[0]

    lw2 = dsp._num(dsp._cell(model, keys, "shaft2speed", c0))
    plies: List[Dict[str, Any]] = []
    for i in cols:
        cs = specs[i]
        sr = cs.get("sr") or {}
        use = cs.get("yarn_use_id") if cs.get("is_group") else sr.get("YarnUseID")
        role = st.role_of(use)
        pos = dsp._display(model, keys.index("position"), i) if "position" in keys else ""
        values = {s: _summary(model, keys, s, i) for s in st.PER_PLY}
        tips = {s: _tip(model, keys, s, i) for s in st.PER_PLY}
        # feed roll: speed from LW 2 and the overfeed, draw-in speed from DR
        of = dsp._num(dsp._cell(model, keys, "of", i))
        dr = dsp._num(dsp._cell(model, keys, "dr", i))
        temps = [dsp._display(model, keys.index(k), i) for k in ("temp0", "temp1") if k in keys]
        temps = [t for t in temps if st.filled(t)]
        if dr is not None and st.filled(dr):
            values["draw"] = f"DR {dsp._short(dr)}" + (f"\n{' / '.join(temps)} °C" if temps else "")
        elif temps:
            values["draw"] = f"{' / '.join(temps)} °C"
        v_feed = st.feed_speed(lw2, of)
        if v_feed is not None:
            values["feed"] = dsp._speed_text(v_feed) + f"\nOF {dsp._short(of)} %"
            _add_line(tips, "feed", f"Speed (LW 2 x (1 + OF %)): {dsp._speed_text(v_feed)}")
            v0 = st.draw_in_speed(v_feed, dr)
            if v0 is not None and dr != 1:
                _add_line(tips, "draw", f"Draw-in speed (feed roll / DR): {dsp._speed_text(v0)}")
        elif of is not None:
            values["feed"] = f"OF {dsp._short(of)} %"
        label = st.ROLE_LABEL.get(role or "", "")
        plies.append({"idx": i, "label": label or (cs.get("ply") or ""), "ply": cs.get("ply") or "",
                      "pos": pos if st.filled(pos) else "", "yarn": cs.get("yarn_name") or "",
                      "role": role, "values": values, "tips": tips})

    values = {s: _summary(model, keys, s, c0) for s, _l, pp in st.STATIONS if not pp}
    tips = {s: _tip(model, keys, s, c0) for s, _l, pp in st.STATIONS if not pp}
    if lw2:
        values["lw2"] = dsp._speed_text(lw2) + "\ntake-off"
    show_draw = any(pl["values"].get("draw") for pl in plies) or \
        any(st.station_of(k) == "draw" for k in keys)
    stations = [s for s, _l, _pp in st.STATIONS if s != "draw" or show_draw]
    vno = specs[c0].get("vno")
    unset = [pl["ply"] for pl in plies if pl["role"] is None]
    warnings = []
    if unset and len(plies) > 1:
        warnings.append("no yarn use (core/effect) for " + ", ".join(str(u) for u in unset)
                        + " - set it in the Yarn Use row")
    return {
        "profile": "aty", "title": f"V{vno}" if vno is not None and int(vno) > 0 else "Ref",
        "trial_id": tid, "process": "Air texturing", "plies": plies,
        "order": st.lane_order([pl["role"] for pl in plies]),
        "stations": stations, "values": values, "tips": tips, "warnings": warnings,
    }


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
