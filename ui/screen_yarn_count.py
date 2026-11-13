"""screen_yarn_count.py - Yarn Count Converter (Sidebar Tools, Nutzerwunsch
2026-11-09, Umfang erweitert nach Vorlage des Nutzers "Garnfeinheit umrechnen").

Left: type a count and pick its unit - dtex and den large, below all other
systems (tex, ktex, mtex, Nm, Ne, NeK, NeL, Run, grain/yd) with description;
a click on a row makes it the new starting value. Right: filaments per end
and plies (n-fold) -> per filament, totals, filament diameter for the chosen
material and the yarn designation; a notation like 2x150D/48F fills
everything in. Below: formulas & definitions (collapsible). The last input is
remembered (QSettings TrippleT/YarnCount).

No database - works offline. Logic in ui/yarn_count.py. Wired like the
Dashboards: app_meta.open_yarn_count / sidebar_nav.trigger_yarn_count, feature
key "yarn_count" (db/feature_access.py).
"""
from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QScrollArea,
                               QToolButton, QVBoxLayout, QWidget)

from ui import yarn_count as yc
from ui.pathutil import resource_path
from ui.widgets import sidebar_nav

ACCENT = "#1F7A3A"
_SETTINGS = ("TrippleT", "YarnCount")
CARD_QSS = "QFrame#Card{background:#FFFFFF;border:1px solid #DADFD8;border-radius:8px;}"
INPUT_QSS = ("QLineEdit,QComboBox{border:1px solid #C9D1C8;border-radius:5px;padding:6px 8px;"
             "font-size:15px;background:#FFFFFF;} QLineEdit:focus,QComboBox:focus{border-color:#39A650;}")
SMALL = "color:#5A6460;font-size:12px;border:none;background:transparent;"


def _card(title: str, subtitle: str = ""):
    card = QFrame()
    card.setObjectName("Card")
    card.setStyleSheet(CARD_QSS)
    lay = QVBoxLayout(card)
    lay.setContentsMargins(18, 14, 18, 16)
    lay.setSpacing(10)
    t = QLabel(title)
    t.setStyleSheet("font-size:16px;font-weight:700;color:#1C2321;border:none;")
    lay.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setWordWrap(True)
        s.setStyleSheet(SMALL)
        lay.addWidget(s)
    return card, lay


def _copy_button(get_text) -> QToolButton:
    b = QToolButton()
    b.setText("Copy")
    b.setToolTip("Copy the value")
    b.setCursor(Qt.PointingHandCursor)
    b.setStyleSheet("QToolButton{border:1px solid #C9D1C8;border-radius:4px;padding:2px 8px;background:#FFFFFF;"
                    "color:#1F7A3A;font-size:11px;} QToolButton:hover{background:#E3F1E6;}")

    def _copy():
        txt = get_text()
        if txt and txt != "–":
            QGuiApplication.clipboard().setText(txt.replace("'", ""))
            b.setText("Copied")
            QTimer.singleShot(1200, lambda: b.setText("Copy"))
    b.clicked.connect(_copy)
    return b


class _BigTile(QFrame):
    """Large result for dtex / den; a click makes it the starting value."""

    def __init__(self, unit: str, on_pick, parent=None):
        super().__init__(parent)
        self.unit = unit
        self._on_pick = on_pick
        self.setObjectName("Tile")
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Click to use this value as the starting value")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(0)
        head = QLabel(f"{yc.UNIT[unit][1]} · {yc.UNIT[unit][4]}")
        head.setStyleSheet("color:#5A6460;font-size:12px;font-weight:700;border:none;background:transparent;")
        row = QHBoxLayout()
        self.lbl_value = QLabel("–")
        self.lbl_value.setStyleSheet("font-size:34px;font-weight:700;color:#1C2321;border:none;background:transparent;")
        row.addWidget(self.lbl_value, 1)
        row.addWidget(_copy_button(lambda: self.lbl_value.text()), 0, Qt.AlignBottom)
        lay.addWidget(head)
        lay.addLayout(row)
        self.set_active(False)

    def set_active(self, active: bool) -> None:
        border = "#39A650" if active else "#DADFD8"
        bg = "#F0F8F2" if active else "#FFFFFF"
        self.setStyleSheet(f"QFrame#Tile{{background:{bg};border:2px solid {border};border-radius:8px;}}")

    def mousePressEvent(self, ev):  # noqa: N802
        if ev.button() == Qt.LeftButton:
            self._on_pick(self.unit)
        super().mousePressEvent(ev)


class _UnitRow(QFrame):
    """One unit in the result list: name + description, value, Copy; click = pick."""

    def __init__(self, unit: str, on_pick, parent=None):
        super().__init__(parent)
        self.unit = unit
        self._on_pick = on_pick
        self.setObjectName("URow")
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Click to use this value as the starting value")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 5, 8, 5)
        names = QVBoxLayout()
        names.setSpacing(0)
        n = QLabel(yc.UNIT[unit][1])
        n.setStyleSheet("font-size:13px;font-weight:600;color:#1C2321;border:none;background:transparent;")
        d = QLabel(yc.UNIT[unit][4])
        d.setStyleSheet("font-size:11px;color:#5A6460;border:none;background:transparent;")
        names.addWidget(n)
        names.addWidget(d)
        lay.addLayout(names, 1)
        self.lbl_value = QLabel("–")
        self.lbl_value.setStyleSheet("font-size:16px;font-weight:600;color:#1C2321;border:none;background:transparent;")
        lay.addWidget(self.lbl_value, 0, Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(_copy_button(lambda: self.lbl_value.text()), 0, Qt.AlignVCenter)
        self.set_active(False)

    def set_active(self, active: bool) -> None:
        bg = "#FFF7E0" if active else "transparent"
        self.setStyleSheet(f"QFrame#URow{{background:{bg};border:none;border-bottom:1px solid #ECEFEA;}}"
                           "QFrame#URow:hover{background:#E6F2EA;}")

    def mousePressEvent(self, ev):  # noqa: N802
        if ev.button() == Qt.LeftButton:
            self._on_pick(self.unit)
        super().mousePressEvent(ev)


class YarnCountScreen(QWidget):
    def __init__(self, sidebar_callbacks: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None
        self._logged = True          # the start values are not a use
        self._tex: Optional[float] = None
        self._filling = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._sidebar, content = sidebar_nav.wrap_body_with_sidebar(root)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        page = QWidget()
        page.setObjectName("Page")
        page.setStyleSheet("QWidget#Page{background:#F4F6F3;}" + INPUT_QSS)
        scroll.setWidget(page)
        content.addWidget(scroll)
        pv = QVBoxLayout(page)
        pv.setContentsMargins(24, 16, 24, 20)
        pv.setSpacing(14)

        head = QHBoxLayout()
        icon = QLabel()
        pm = QPixmap(resource_path("assets/images/yarn_count_120.png"))
        if not pm.isNull():
            icon.setPixmap(pm.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        head.addWidget(icon, 0, Qt.AlignVCenter)
        head.addSpacing(8)
        tbox = QVBoxLayout()
        tbox.setSpacing(0)
        k = QLabel("TOOLS")
        k.setStyleSheet(f"color:{ACCENT};font-size:11px;font-weight:700;letter-spacing:1px;")
        t = QLabel("Yarn Count Converter")
        t.setStyleSheet("font-size:22px;font-weight:700;color:#1C2321;")
        s = QLabel("Type a value and choose its unit - all other systems update right away. "
                   "Click a result to use it as the new starting value.")
        s.setStyleSheet("color:#5A6460;font-size:12px;")
        for w in (k, t, s):
            tbox.addWidget(w)
        head.addLayout(tbox, 1)
        pv.addLayout(head)

        cols = QHBoxLayout()
        cols.setSpacing(14)
        cols.addWidget(self._build_convert(), 1)
        cols.addWidget(self._build_filament(), 1)
        pv.addLayout(cols)
        pv.addWidget(self._build_formulas())
        pv.addStretch(1)

        self._restore()
        self._convert()
        self._logged = False

    # ── convert card ───────────────────────────────────────────────────
    def _build_convert(self) -> QWidget:
        card, lay = _card("Convert")
        row = QHBoxLayout()
        self.ed_value = QLineEdit("167")
        self.ed_value.setPlaceholderText("Value, e.g. 167")
        self.cb_unit = QComboBox()
        for key, label, _kind, _k, desc in yc.UNITS:
            self.cb_unit.addItem(f"{label} – {desc}", key)
        row.addWidget(self.ed_value, 2)
        row.addWidget(self.cb_unit, 3)
        lay.addLayout(row)
        self.lbl_conv_msg = QLabel("")
        self.lbl_conv_msg.setStyleSheet("color:#B23B00;font-size:12px;border:none;")
        lay.addWidget(self.lbl_conv_msg)
        tiles = QHBoxLayout()
        self.tiles: Dict[str, _BigTile] = {u: _BigTile(u, self._pick) for u in ("dtex", "den")}
        for tile in self.tiles.values():
            tiles.addWidget(tile, 1)
        lay.addLayout(tiles)
        box = QVBoxLayout()
        box.setSpacing(0)
        self.rows: Dict[str, _UnitRow] = {}
        for key, *_ in yc.UNITS:
            if key in self.tiles:
                continue
            r = _UnitRow(key, self._pick)
            self.rows[key] = r
            box.addWidget(r)
        lay.addLayout(box)
        lay.addStretch(1)
        self.ed_value.textChanged.connect(self._convert)
        self.cb_unit.currentIndexChanged.connect(self._convert)
        return card

    def _pick(self, unit: str) -> None:
        """A result becomes the new starting value."""
        if self._tex is None or unit == self.cb_unit.currentData():
            return
        value = yc.from_tex(self._tex, unit)
        self._filling = True
        self.cb_unit.setCurrentIndex(self.cb_unit.findData(unit))
        self.ed_value.setText(yc.fmt(value).replace("'", ""))
        self._filling = False
        self._convert()

    def _convert(self) -> None:
        if self._filling:
            return
        unit = self.cb_unit.currentData()
        for key, tile in self.tiles.items():
            tile.set_active(key == unit)
        for key, row in self.rows.items():
            row.set_active(key == unit)
        txt = self.ed_value.text().strip().replace(",", ".").replace("'", "")
        try:
            self._tex = yc.to_tex(float(txt), unit)
            self.lbl_conv_msg.setText("")
        except (ValueError, ZeroDivisionError):
            self._tex = None
            self.lbl_conv_msg.setText("Enter a number greater than 0." if txt else "")
        for key, tile in self.tiles.items():
            tile.lbl_value.setText(yc.fmt(yc.from_tex(self._tex, key)) if self._tex else "–")
        for key, row in self.rows.items():
            row.lbl_value.setText(yc.fmt(yc.from_tex(self._tex, key)) if self._tex else "–")
        self._filament()
        if self._tex:
            self._save()
            self._log()

    # ── filament card ──────────────────────────────────────────────────
    def _build_filament(self) -> QWidget:
        card, lay = _card("Filaments & plies",
                          "The count on the left is per end. With the filaments and the number of plies you get "
                          "the values per filament and the total (n × single count, without twist take-up).")
        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(8)

        def lbl(t):
            w = QLabel(t)
            w.setStyleSheet(SMALL)
            return w
        self.ed_fil = QLineEdit("48")
        self.ed_fil.setPlaceholderText("e.g. 48")
        self.ed_ply = QLineEdit("1")
        self.ed_ply.setPlaceholderText("1")
        self.cb_material = QComboBox()
        for name, rho in yc.DENSITIES:
            self.cb_material.addItem(f"{name} – {rho:g} g/cm³", rho)
        g.addWidget(lbl("Filaments per end"), 0, 0)
        g.addWidget(self.ed_fil, 0, 1)
        g.addWidget(lbl("Plies (n-fold)"), 1, 0)
        g.addWidget(self.ed_ply, 1, 1)
        g.addWidget(lbl("Material (for the diameter)"), 2, 0)
        g.addWidget(self.cb_material, 2, 1)
        g.setColumnStretch(1, 1)
        lay.addLayout(g)

        rg = QGridLayout()
        rg.setHorizontalSpacing(12)
        rg.setVerticalSpacing(5)
        self.fil: Dict[str, QLabel] = {}
        items = [("dpf_dtex", "dtex per filament"), ("dpf_den", "den per filament (dpf)"),
                 ("diameter", "Filament diameter (µm)"), ("total_dtex", "Total dtex"), ("total_den", "Total den"),
                 ("total_Nm", "Total Nm"), ("total_Ne", "Total Ne"), ("total_fil", "Total filaments")]
        for r, (key, label) in enumerate(items):
            l = lbl(label)
            l.setStyleSheet("color:#5A6460;font-size:13px;border:none;")
            v = QLabel("–")
            big = key in ("total_dtex", "total_den")
            v.setStyleSheet(f"font-size:{19 if big else 16}px;font-weight:{700 if big else 600};"
                            "color:#1C2321;border:none;")
            rg.addWidget(l, r, 0)
            rg.addWidget(v, r, 1)
            rg.addWidget(_copy_button(lambda w=v: w.text()), r, 2)
            self.fil[key] = v
        rg.setColumnStretch(1, 1)
        lay.addLayout(rg)
        self.lbl_designation = QLabel("–")
        self.lbl_designation.setWordWrap(True)
        self.lbl_designation.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_designation.setStyleSheet("background:#E6F2EA;border-radius:6px;padding:8px 10px;font-size:15px;"
                                           "font-weight:700;color:#1C2321;")
        d_head = lbl("DESIGNATION")
        d_head.setStyleSheet("color:#5A6460;font-size:11px;font-weight:700;letter-spacing:1px;border:none;")
        lay.addWidget(d_head)
        drow = QHBoxLayout()
        drow.addWidget(self.lbl_designation, 1)
        drow.addWidget(_copy_button(lambda: self.lbl_designation.text()), 0, Qt.AlignVCenter)
        lay.addLayout(drow)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#ECEFEA;")
        lay.addWidget(sep)
        n_head = lbl("READ A YARN NOTATION")
        n_head.setStyleSheet("color:#5A6460;font-size:11px;font-weight:700;letter-spacing:1px;border:none;")
        lay.addWidget(n_head)
        nrow = QHBoxLayout()
        self.ed_notation = QLineEdit()
        self.ed_notation.setPlaceholderText("e.g. 167f48, 150D/48F, 2x167f48, 78f68x2 - press Enter")
        self.cb_default = QComboBox()
        for key in ("dtex", "den", "tex"):
            self.cb_default.addItem(f"bare numbers = {key}", key)
        nrow.addWidget(self.ed_notation, 3)
        nrow.addWidget(self.cb_default, 2)
        lay.addLayout(nrow)
        self.lbl_nota_msg = QLabel("Fills in value, unit, filaments and plies above.")
        self.lbl_nota_msg.setWordWrap(True)
        self.lbl_nota_msg.setStyleSheet(SMALL)
        lay.addWidget(self.lbl_nota_msg)
        lay.addStretch(1)

        self.ed_fil.textChanged.connect(self._filament_changed)
        self.ed_ply.textChanged.connect(self._filament_changed)
        self.cb_material.currentIndexChanged.connect(self._filament_changed)
        self.ed_notation.returnPressed.connect(self._read_notation)
        self.ed_notation.textChanged.connect(self._preview_notation)
        return card

    @staticmethod
    def _int(txt: str) -> Optional[int]:
        try:
            v = int(float(txt.strip().replace(",", ".").replace("'", "")))
            return v if v > 0 else None
        except ValueError:
            return None

    def _filament_changed(self) -> None:
        self._filament()
        if self._tex:
            self._save()
            self._log()

    def _filament(self) -> None:
        fil = self._int(self.ed_fil.text())
        plies = self._int(self.ed_ply.text()) or 1
        vals = yc.filament_values(self._tex, fil, plies, self.cb_material.currentData())   # ui/yarn_count.py
        for key, w in self.fil.items():
            v = vals.get(key)
            w.setText("–" if v is None else str(int(v)) if key == "total_fil" else yc.fmt(v))
        self.lbl_designation.setText(vals.get("designation") or "–")

    def _preview_notation(self) -> None:
        txt = self.ed_notation.text()
        if not txt.strip():
            self.lbl_nota_msg.setText("Fills in value, unit, filaments and plies above.")
            self.lbl_nota_msg.setStyleSheet(SMALL)
            return
        p = yc.parse_notation(txt, self.cb_default.currentData())
        if p:
            parts = [f"{yc.fmt(p['count'])} {yc.UNIT[p['unit']][1].split(' (')[0]}"]
            if p["filaments"]:
                parts.append(f"{p['filaments']} filaments")
            if p["plies"] > 1:
                parts.append(f"{p['plies']} plies")
            self.lbl_nota_msg.setText("Read as " + ", ".join(parts) + " - press Enter to use it.")
            self.lbl_nota_msg.setStyleSheet(SMALL)
        else:
            self.lbl_nota_msg.setText("Not understood - write it like 167f48, 150D/48F or 2x167f48.")
            self.lbl_nota_msg.setStyleSheet("color:#B23B00;font-size:12px;border:none;")

    def _read_notation(self) -> None:
        p = yc.parse_notation(self.ed_notation.text(), self.cb_default.currentData())
        if not p:
            self._preview_notation()
            return
        self._filling = True
        self.cb_unit.setCurrentIndex(self.cb_unit.findData(p["unit"]))
        self.ed_value.setText(yc.fmt(p["count"]).replace("'", ""))
        self.ed_fil.setText(str(p["filaments"]) if p["filaments"] else "")
        self.ed_ply.setText(str(p["plies"]))
        self._filling = False
        self._convert()
        self.lbl_nota_msg.setText("Taken over.")

    # ── formulas ───────────────────────────────────────────────────────
    def _build_formulas(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        card.setStyleSheet(CARD_QSS)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 10, 18, 12)
        self.btn_formulas = QToolButton()
        self.btn_formulas.setText("▸  Formulas && definitions")
        self.btn_formulas.setCheckable(True)
        self.btn_formulas.setStyleSheet("QToolButton{border:none;font-size:14px;font-weight:700;color:#1C2321;"
                                        "background:transparent;}")
        lay.addWidget(self.btn_formulas, 0, Qt.AlignLeft)
        body = QWidget()
        g = QGridLayout(body)
        g.setHorizontalSpacing(20)
        g.setVerticalSpacing(4)
        for r, (key, label, _kind, _k, desc) in enumerate(yc.UNITS):
            for c, (txt, st) in enumerate(((label, "font-weight:600;"), (desc, "color:#5A6460;"),
                                           (yc.formula(key), "font-family:Consolas;"))):
                w = QLabel(txt)
                w.setStyleSheet(st + "font-size:12px;border:none;")
                g.addWidget(w, r, c)
        n = QLabel("Direct systems (dtex, den, tex …) grow with the yarn thickness; length based systems (Nm, Ne …) "
                   "are indirect: a higher number means a finer yarn. 1 yd = 0.9144 m, 1 lb = 453.59237 g, "
                   "1 grain = 0.06479891 g. Filament diameter: d [µm] = 10 × √(4 × dtex per filament ÷ (π × density)), "
                   "assuming round, solid filaments.")
        n.setWordWrap(True)
        n.setStyleSheet(SMALL)
        g.addWidget(n, len(yc.UNITS), 0, 1, 3)
        g.setColumnStretch(2, 1)
        body.setVisible(False)
        lay.addWidget(body)

        def toggle(on):
            body.setVisible(on)
            self.btn_formulas.setText(("▾" if on else "▸") + "  Formulas && definitions")  # && = literal &
        self.btn_formulas.toggled.connect(toggle)
        return card

    # ── remember last input ────────────────────────────────────────────
    def _save(self) -> None:
        try:
            s = QSettings(*_SETTINGS)
            s.setValue("value", self.ed_value.text())
            s.setValue("unit", self.cb_unit.currentData())
            s.setValue("filaments", self.ed_fil.text())
            s.setValue("plies", self.ed_ply.text())
            s.setValue("material", self.cb_material.currentIndex())
        except Exception:
            pass

    def _restore(self) -> None:
        try:
            s = QSettings(*_SETTINGS)
            self._filling = True
            if s.value("value") is not None:
                self.ed_value.setText(str(s.value("value")))
            i = self.cb_unit.findData(s.value("unit", "dtex"))
            self.cb_unit.setCurrentIndex(i if i >= 0 else 0)
            if s.value("filaments") is not None:
                self.ed_fil.setText(str(s.value("filaments")))
            if s.value("plies") is not None:
                self.ed_ply.setText(str(s.value("plies")))
            m = int(s.value("material", 0) or 0)
            if 0 <= m < self.cb_material.count():
                self.cb_material.setCurrentIndex(m)
        except Exception:
            pass
        finally:
            self._filling = False

    def _log(self) -> None:
        if self._logged:
            return
        self._logged = True
        try:
            from db.usage_log import log_usage_event
            log_usage_event("feature", "yarn_count")
        except Exception:
            pass

    # ── lifecycle ──────────────────────────────────────────────────────
    def showEvent(self, event):  # noqa: N802
        try:
            import app_meta
            level = int((app_meta.current_user or {}).get("access_level") or 0)
            sidebar_nav.refresh_lazy_sidebar(self, level)
        except Exception:
            pass
        super().showEvent(event)
        self.ed_value.setFocus()
