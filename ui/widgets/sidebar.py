from __future__ import annotations
# ui/widgets/sidebar.py
"""Wiederverwendbares linkes Navigations-Panel (SidebarPanel), analog zu
HeaderBar (siehe ui/widgets/header.py) - inzwischen der App-weite Ersatz für
die TopBar (siehe CLAUDE.md, Abschnitt "Home-Screen: Sidebar-Redesign" /
"TopBar entfernt", Stand 2026-08-26 ff.).

SidebarPanel baut nur das Chrome (feste Breite, dunkler Hintergrund,
Marken-Kopf mit echtem Logo, Ein-/Ausklappen, Scroll-Bereich, einklappbare
Sektionen); der Inhalt (Sektionen/Einträge) wird von aussen über
add_section_header()/add_row()/add_item()/add_spacing()/add_stretch()
befüllt - analog dazu, wie HeaderBar seine Buttons selbst baut, aber die
Verdrahtung (z.B. connect_search()) dem Aufrufer überlässt. Die eigentlichen
Navigation/Tools/Admin/Superuser/Account-Gruppen stehen in
ui/widgets/sidebar_nav.py (von allen Screens geteilt).

Ein-/Ausklappen der GANZEN Sidebar (Nutzerwunsch, 2026-08-26): Klick auf das
tricolour-Logo toggelt zwischen voller Breite und einer schmalen
Icon-only-Spalte - Text auf Buttons/Sektions-Überschriften und der
Marken-Schriftzug werden dabei versteckt (nicht die Icons), Original-Texte
wandern als Tooltip auf die Buttons, damit sie im eingeklappten Zustand
weiterhin erkennbar bleiben. Geteilter Zustand über alle Screens hinweg: ein
Modul-Level-Flag (_shared_collapsed) plus ein WeakSet aller aktuell
existierenden Panels (_all_panels) - ein Toggle auf irgendeinem Panel
schaltet alle anderen (auch aktuell nicht sichtbare, z.B. im
QStackedWidget dahinterliegende Screens) synchron mit. WeakSet statt einer
normalen Liste, damit ein bei Logout neu gebautes HomeScreen sein altes
SidebarPanel nicht künstlich am Leben hält. Bewusst NICHT auf Disk
persistiert (gilt nur für die laufende Session).

Einklappbare EINZEL-Sektionen (Nutzerwunsch, 2026-08-27): jede über
add_section_header()/add_row() begonnene Sektion ist per Klick auf ihre
Kopfzeile (nicht nur das Icon, aber das Icon eingeschlossen) unabhängig
von den anderen Sektionen und unabhängig vom Ganze-Sidebar-Collapse
ein-/ausklappbar - ein kleiner Chevron (Dreieck-Icon) am rechten Rand der
Kopfzeile zeigt den Zustand an. Default: nur die zuerst begonnene Sektion
(in der Praxis immer "Navigation") ist offen, alle folgenden Sektionen
starten eingeklappt - siehe `expanded=`-Parameter von add_section_header()/
add_row(). Anders als der Ganze-Sidebar-Collapse ist dieser Zustand NICHT
geteilt zwischen Screens (jede Sidebar-Instanz hat ihre eigenen
Sektionszustände) und startet bei jedem Neuaufbau (z.B. Access-Level-Wechsel
in _refresh_sidebar()) wieder bei den übergebenen Defaults.

Wechselwirkung der beiden Collapse-Arten: ist die GANZE Sidebar eingeklappt
(Icon-only), werden alle Sektionsinhalte unabhängig von ihrem individuellen
Zustand sichtbar erzwungen (sonst gäbe es bei "Sidebar eingeklappt UND alle
Sektionen eingeklappt" gar keine Icons mehr zu sehen) - der individuelle
Zustand bleibt dabei aber gespeichert und wird beim Wieder-Ausklappen der
ganzen Sidebar korrekt wiederhergestellt.

Scrollbar (Nutzerwunsch, 2026-08-27): der Marken-Kopf bleibt fest oben
stehen, der gesamte Sektionsinhalt darunter läuft durch eine vertikale
QScrollArea (kein horizontales Scrollen nötig, feste Breite).
"""

import weakref

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QScrollArea, QFrame,
)

from ui.pathutil import resource_path

_all_panels: "weakref.WeakSet[SidebarPanel]" = weakref.WeakSet()
_shared_collapsed = False

# Ein-/Ausklapp-Zustand einzelner Sektionen, geteilt über ALLE Screens
# (Nutzerbugreport 2026-08-27: "experiment requests klackt immer wieder zu,
# wenn ich die seite ändere") - jeder Screen hat sein EIGENES, einmalig
# gebautes SidebarPanel (nicht bei jeder Navigation neu erstellt), der
# Sektions-Zustand war bisher rein lokal pro Panel-Instanz und startete bei
# jedem neu gebauten Screen wieder beim `expanded=`-Default aus
# add_section_header() - ein auf Screen A aufgeklappter Abschnitt erschien
# beim Wechsel zu Screen B (eigenes Panel) dadurch fälschlich wieder
# zugeklappt. Keyed by section title (z.B. "Experiment Requests") statt
# Objekt-Referenz, da jeder Screen sein Panel unabhängig neu aufbaut - Titel
# ist über alle Panels hinweg stabil und identisch. Analog zum bereits
# bestehenden `_shared_collapsed`/`_all_panels`-Muster fürs Ganze-Sidebar-
# Collapse, nur pro Sektion statt global.
_shared_section_expanded: dict[str, bool] = {}


def _propagate_section_state(section_key: str, expanded: bool):
    """Spiegelt einen Sektions-Toggle auf alle anderen aktuell existierenden
    Panels (auch aktuell nicht sichtbare) - macht das Verhalten für bereits
    gebaute Screens sofort sichtbar, nicht erst beim nächsten Neuaufbau."""
    for panel in list(_all_panels):
        for section in panel._sections:
            if section.get("section_key") == section_key and section["expanded"] != expanded:
                section["expanded"] = expanded
                if not panel._collapsed:
                    section["container"].setVisible(expanded)
                chevron = section.get("chevron")
                if chevron is not None:
                    fname = _CHEVRON_EXPANDED if expanded else _CHEVRON_COLLAPSED
                    pm = QPixmap(resource_path(f"assets/images/{fname}"))
                    if not pm.isNull():
                        chevron.setPixmap(pm.scaled(10, 10, Qt.KeepAspectRatio, Qt.SmoothTransformation))

_CHEVRON_EXPANDED = "triangle_down_16.png"
_CHEVRON_COLLAPSED = "triangle_right_16.png"


def _initials(text: str) -> str:
    """Leitet ein kurzes Kuerzel aus einem Button-Label ab (z.B. "Manage
    User" -> "MU", "Jets" -> "J") - fuer Buttons ohne Icon-Asset (Admin/
    Superuser-Gruppe, siehe green_btn() in ui/widgets/sidebar_nav.py), wenn
    die GANZE Sidebar eingeklappt ist (siehe apply_collapse_state()). Ohne
    das wuerde ein solcher Button beim Einklappen komplett leer (kein Icon,
    kein Text) und damit unbedienbar/unidentifizierbar."""
    words = [w for w in text.split() if w]
    letters = "".join(w[0].upper() for w in words[:3])
    return letters or "?"


class _ClickableLabel(QLabel):
    """QLabel, die per Linksklick ein Signal feuert - für den Logo-Klick."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class _ClickableRow(QWidget):
    """QWidget, die per Linksklick ein Signal feuert - für Sektions-
    Kopfzeilen (Toggle Ein-/Ausklappen). Andere Maustasten (z.B. Rechtsklick
    für HomeScreen's Snake/Athena/LFC-Ostereier auf dem inneren Label) werden
    unverändert an das jeweilige Kind-Widget durchgereicht, da hier nur auf
    QMouseEvent.LeftButton reagiert wird."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class SidebarPanel(QWidget):
    """Dunkles, fest breites linkes Navigations-Panel mit Marken-Kopf,
    scrollbarem Inhalt und einklappbaren Sektionen."""

    COLLAPSED_WIDTH = 76

    def __init__(self, width: int = 316, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("SidebarPanel")
        self._expanded_width = width
        # Neues Panel übernimmt den aktuell geteilten Ganze-Sidebar-Collapse-
        # Zustand, statt immer expanded zu starten - z.B. wenn HomeScreen
        # nach einem Logout neu gebaut wird, während der Zustand woanders
        # bereits "collapsed" ist.
        self._collapsed = _shared_collapsed
        self.setFixedWidth(self.COLLAPSED_WIDTH if self._collapsed else width)
        _all_panels.add(self)
        # Plain QWidget does not paint a QSS `background` by default (unlike
        # QFrame, which the old inline version used) - without this attribute
        # the stylesheet rule is simply ignored and the panel stays transparent.
        self.setAttribute(Qt.WA_StyledBackground, True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # --- Marken-Kopf: fest, nimmt nicht am Scrollen teil ---
        brand_wrap = QWidget()
        brand_wrap.setAttribute(Qt.WA_StyledBackground, True)
        brand_layout = QVBoxLayout(brand_wrap)
        brand_layout.setContentsMargins(16, 20, 16, 4)
        brand_layout.setSpacing(0)
        self._build_brand_block(brand_layout)
        outer.addWidget(brand_wrap)

        # --- Scrollbarer Sektionsinhalt ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # QAbstractScrollArea malt seinen Viewport standardmässig deckend
        # (eigene Palette, i.d.R. hell) - das überdeckt den dunklen
        # SidebarPanel-Hintergrund darunter, unabhängig von #SidebarPanel in
        # ui/theme.py (dessen Objektname nur auf `self`, nicht auf
        # Scrollbereich/Viewport/Inhalt zutrifft). Scroll-Area + Viewport
        # daher explizit transparent - der eigentliche Hintergrund kommt
        # weiterhin einzig von `self` (siehe WA_StyledBackground oben).
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.viewport().setStyleSheet("background: transparent;")
        content = QWidget()
        content.setAttribute(Qt.WA_StyledBackground, True)
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(16, 4, 16, 16)
        self._layout.setSpacing(3)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        # Sektionen (siehe _begin_section()) - jede hat eine Kopfzeile
        # (versteckt beim Ganze-Sidebar-Collapse) und einen Inhalts-Container
        # (individuell ein-/ausklappbar, siehe Moduldocstring).
        self._sections: list[dict] = []
        self._current_section: dict | None = None
        # Buttons/Badge-Wrapper (Text wird beim Ganze-Sidebar-Collapse geleert).
        self._items: list[QWidget] = []
        # 3D-Trennstriche (siehe add_separator()) - nur sichtbar, wenn die
        # ganze Sidebar eingeklappt ist (Nutzerwunsch, 2026-08-27: im
        # ausgeklappten Zustand übernehmen die Sektions-Namen/-Icons bereits
        # diese Rolle, ein zusätzlicher Strich wäre dort redundant).
        self._separators: list[QFrame] = []

    def _build_brand_block(self, brand_layout: QVBoxLayout):
        """Marken-Kopf: dasselbe tricolour-Logo wie im Header, plus Wordmark.
        Das Logo selbst ist der Klick-Schalter zum Ein-/Ausklappen der
        GANZEN Sidebar (nicht zu verwechseln mit den Sektions-Chevrons)."""
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)

        self._logo_icon = _ClickableLabel()
        self._logo_icon.setToolTip("Collapse/expand sidebar")
        tri_pm = QPixmap(resource_path("assets/images/tricolour.png"))
        if not tri_pm.isNull():
            self._logo_icon.setPixmap(tri_pm.scaledToHeight(30, Qt.SmoothTransformation))
        self._logo_icon.clicked.connect(self.toggle_collapsed)
        brand_row.addWidget(self._logo_icon, 0, Qt.AlignVCenter)

        self._brand_text = QWidget()
        brand_col = QVBoxLayout(self._brand_text)
        brand_col.setContentsMargins(0, 0, 0, 0)
        brand_col.setSpacing(1)
        brand_col.addWidget(QLabel("TrippleT", objectName="SidebarBrandLabel"))
        brand_col.addWidget(QLabel("HEBERLEIN", objectName="SidebarSubLabel"))
        brand_row.addWidget(self._brand_text)

        brand_row.addStretch()
        brand_layout.addLayout(brand_row)
        brand_layout.addSpacing(16)

    # ------------------------------------------------------------- Content API
    def _make_chevron(self, expanded: bool) -> QLabel:
        lbl = QLabel()
        lbl.setFixedSize(10, 10)
        fname = _CHEVRON_EXPANDED if expanded else _CHEVRON_COLLAPSED
        pm = QPixmap(resource_path(f"assets/images/{fname}"))
        if not pm.isNull():
            lbl.setPixmap(pm.scaled(10, 10, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        return lbl

    def _begin_section(
        self, header_row: QWidget, chevron: QLabel | None, *, expanded: bool,
        section_key: str | None = None,
    ) -> QWidget:
        """Registriert `header_row` als Kopfzeile einer neuen, einklappbaren
        Sektion und hängt Kopfzeile + einen leeren Inhalts-Container ans
        Layout an. Alle folgenden add_item()/add_row()-Aufrufe (bis zur
        nächsten add_section_header()/add_row()-Sektion) landen automatisch
        im Inhalts-Container dieser Sektion. Gibt den Container zurück.

        `section_key`: gemeinsamer Schlüssel für den über alle Screens
        geteilten Auf-/Zuklapp-Zustand (siehe _shared_section_expanded oben) -
        `None` (Default, von add_row() genutzt) lässt die Sektion rein lokal
        pro Panel-Instanz wie zuvor."""
        self._layout.addWidget(header_row)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(3)
        self._layout.addWidget(container)

        section = {
            "header": header_row,
            "container": container,
            "chevron": chevron,
            "expanded": expanded,
            "section_key": section_key,
        }
        self._sections.append(section)
        self._current_section = section

        header_row.setCursor(Qt.PointingHandCursor)
        if isinstance(header_row, _ClickableRow):
            header_row.clicked.connect(lambda: self._toggle_section(section))

        container.setVisible(expanded or self._collapsed)
        return container

    def add_section_header(self, icon_file: str, title: str, icon_size: int = 14, *, expanded: bool = False) -> QLabel:
        """Beginnt eine neue, einklappbare Sektion mit Standard-Kopfzeile
        (Icon + Label + Chevron rechts). `expanded` legt den Default-Zustand
        fest (Nutzerwunsch, 2026-08-27: alles ausser "Navigation" startet
        eingeklappt - siehe ui/widgets/sidebar_nav.py für die konkreten
        Aufrufer-Defaults) - NUR falls für diesen Titel noch kein Zustand
        über einen anderen Screen bekannt ist, siehe _shared_section_expanded
        oben. Gibt das Titel-Label zurück, falls ein Aufrufer es später
        braucht (z.B. für einen Sonderfall wie den geheimen Rechtsklick in
        HomeScreen - dafür eher add_row() mit einer selbstgebauten Zeile
        verwenden, siehe dort). Klick auf die Kopfzeile (Icon eingeschlossen)
        klappt die Sektion ein/aus."""
        initial_expanded = _shared_section_expanded.get(title, expanded)

        row = _ClickableRow()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        icon_path = resource_path(f"assets/images/{icon_file}")
        pm = QPixmap(icon_path)
        icon_lbl = QLabel()
        if not pm.isNull():
            icon_lbl.setPixmap(pm.scaled(
                icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        row_layout.addWidget(icon_lbl, 0, Qt.AlignVCenter)

        lbl = QLabel(title.upper(), objectName="SidebarSectionLabel")
        row_layout.addWidget(lbl, 0, Qt.AlignVCenter)
        row_layout.addStretch()

        chevron = self._make_chevron(initial_expanded)
        row_layout.addWidget(chevron, 0, Qt.AlignVCenter)

        self._begin_section(row, chevron, expanded=initial_expanded, section_key=title)
        return lbl

    def add_row(self, row_layout, *, expanded: bool = False):
        """Beginnt eine neue, einklappbare Sektion mit selbstgebauter
        Kopfzeile (z.B. HomeScreen's Navigation-Zeile mit dem
        LFC-Ostereier-Icon-Swap) - Escape-Hatch für Fälle, die
        add_section_header() nicht abdeckt. Ein Chevron wird automatisch
        rechts an `row_layout` angehängt, damit auch selbstgebaute
        Kopfzeilen dieselbe Klapp-Anzeige bekommen. Klick auf die Kopfzeile
        klappt die Sektion ein/aus - Kind-Widgets mit eigenem eventFilter
        (z.B. Rechtsklick-Handling) bleiben davon unberührt, da hier nur auf
        Linksklick reagiert wird (siehe _ClickableRow). Bewusst OHNE
        geteilten Zustand (kein section_key) - aktuell ungenutzter Escape-
        Hatch, siehe _begin_section()."""
        row = _ClickableRow()
        row.setLayout(row_layout)

        chevron = self._make_chevron(expanded)
        row_layout.addWidget(chevron, 0, Qt.AlignVCenter)

        self._begin_section(row, chevron, expanded=expanded)

    def _toggle_section(self, section: dict):
        section["expanded"] = not section["expanded"]
        if not self._collapsed:
            section["container"].setVisible(section["expanded"])
        chevron = section.get("chevron")
        if chevron is not None:
            fname = _CHEVRON_EXPANDED if section["expanded"] else _CHEVRON_COLLAPSED
            pm = QPixmap(resource_path(f"assets/images/{fname}"))
            if not pm.isNull():
                chevron.setPixmap(pm.scaled(10, 10, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        key = section.get("section_key")
        if key is not None:
            _shared_section_expanded[key] = section["expanded"]
            _propagate_section_state(key, section["expanded"])

    def add_item(self, widget: QWidget):
        """Hängt einen Sidebar-Eintrag (Button oder Badge-Wrapper) voll-breit
        an - in den Inhalts-Container der aktuell offenen Sektion (siehe
        add_section_header()/add_row()), oder direkt ans Hauptlayout, falls
        (untypisch) noch keine Sektion begonnen wurde."""
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if self._current_section is not None:
            self._current_section["container"].layout().addWidget(widget)
        else:
            self._layout.addWidget(widget)
        self._items.append(widget)

    def add_spacing(self, px: int):
        """Fügt einen Abstand auf oberster Ebene ein (zwischen Sektionen,
        nicht Teil einer Sektion - bleibt daher unabhängig vom Klapp-Zustand
        einzelner Sektionen sichtbar)."""
        self._layout.addSpacing(px)

    def add_stretch(self):
        self._layout.addStretch()

    def add_separator(self):
        """Fügt einen dünnen "3D"-Trennstrich zwischen zwei Blöcken ein
        (Nutzerwunsch, 2026-08-27) - Ersatz für die frühere reine
        add_spacing()-Lücke zwischen den Sidebar-Sektionen. Zwei
        übereinanderliegende 1px-Kanten (dunkel oben, hell unten) simulieren
        die klassische eingelassene "Sunken"-Optik von Hand statt über
        QFrame.Sunken - das palette-basierte Sunken-Frame verlässt sich auf
        Farbrollen, die gegen den eigenen dunklen SidebarPanel-Hintergrund
        (siehe ui/theme.py SIDEBAR_BG) sonst kaum sichtbar wären. Auf oberster
        Ebene wie add_spacing() (kein Teil einer Sektion, bleibt daher immer
        im Layout, unabhängig vom Sektions-Klappzustand).

        Nur sichtbar, wenn die GANZE Sidebar eingeklappt ist (Nutzerwunsch,
        2026-08-27: im ausgeklappten Zustand übernehmen die Sektions-Namen/
        -Icons bereits die Trenner-Rolle, ein zusätzlicher Strich wäre dort
        redundant) - siehe apply_collapse_state()."""
        self._layout.addSpacing(6)
        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet(
            "background: transparent;"
            "border-top: 1px solid #4a4a4a;"
            "border-bottom: 1px solid #8a8a8a;"
        )
        line.setVisible(self._collapsed)
        self._layout.addWidget(line)
        self._layout.addSpacing(6)
        self._separators.append(line)

    # --------------------------------------------------------- Collapse/Expand
    def is_collapsed(self) -> bool:
        return self._collapsed

    def toggle_collapsed(self):
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool, *, _propagate: bool = True):
        """Setzt den GANZE-Sidebar-Collapse-Zustand (Icon-only vs. volle
        Breite). `_propagate=True` (Default, für einen echten Nutzer-Klick)
        spiegelt die Änderung auf alle anderen aktuell existierenden
        SidebarPanel-Instanzen - siehe Moduldocstring. `_propagate=False` ist
        intern für genau diese Spiegelung selbst reserviert (verhindert
        Endlos-Rekursion zwischen den Panels)."""
        global _shared_collapsed
        if _propagate:
            _shared_collapsed = collapsed
        if collapsed == self._collapsed:
            return
        self._collapsed = collapsed
        self.setFixedWidth(self.COLLAPSED_WIDTH if collapsed else self._expanded_width)
        self.apply_collapse_state()
        if _propagate:
            for panel in list(_all_panels):
                if panel is not self:
                    panel.set_collapsed(collapsed, _propagate=False)

    def apply_collapse_state(self):
        """Wendet den aktuellen Ganze-Sidebar-Collapse-Zustand auf alle
        registrierten Sektionen/Items an. Öffentlich, damit ein Aufrufer, der
        Inhalte nach clear_content() neu aufbaut (z.B. bei jedem showEvent()
        mit geänderten Access-Level), den Zustand auf die frisch
        hinzugefügten Widgets anwenden kann, ohne den Zustand selbst
        umzuschalten.

        Ist die ganze Sidebar eingeklappt (Icon-only), werden alle
        Sektions-Container unabhängig von ihrem individuellen
        Ein-/Ausklapp-Zustand sichtbar erzwungen (sonst gäbe es bei
        gleichzeitig eingeklappter Sidebar UND eingeklappten Sektionen gar
        keine Icons mehr zu sehen) - der individuelle Zustand bleibt dabei
        gespeichert und wird beim Wieder-Ausklappen der Sidebar korrekt
        wiederhergestellt."""
        collapsed = self._collapsed
        self._brand_text.setVisible(not collapsed)

        for section in self._sections:
            section["header"].setVisible(not collapsed)
            section["container"].setVisible(True if collapsed else section["expanded"])

        for sep in self._separators:
            sep.setVisible(collapsed)

        for item in self._items:
            btn = item if isinstance(item, QPushButton) else item.findChild(QPushButton)
            if btn is None:
                continue
            if collapsed:
                if not hasattr(btn, "_sidebar_full_text"):
                    btn._sidebar_full_text = btn.text()
                    if not btn.toolTip():
                        btn.setToolTip(btn._sidebar_full_text)
                # Buttons ohne Icon (Admin/Superuser-Gruppe, siehe
                # green_btn() in ui/widgets/sidebar_nav.py) wuerden sonst
                # beim Einklappen komplett leer - Initialen als Ersatz-Text
                # (Nutzerwunsch, 2026-08-27: "bei Manage User MU").
                btn.setText(_initials(btn._sidebar_full_text) if btn.icon().isNull() else "")
            else:
                full_text = getattr(btn, "_sidebar_full_text", None)
                if full_text is not None:
                    btn.setText(full_text)

    # ------------------------------------------------------------ Rebuilding
    def clear_content(self):
        """Entfernt alle über add_section_header()/add_row()/add_item()/
        add_spacing()/add_stretch() hinzugefügten Inhalte (der Marken-Kopf
        lebt seit der Scroll-Umstellung in einem eigenen, hier unberührten
        Layout und muss daher nicht mehr extra geschont werden). Für
        Screens, die ihre Sidebar bei jedem Öffnen neu aufbauen müssen (z.B.
        BacklogScreen, dessen access_level erst nach dem Login bekannt ist,
        siehe screen_backlog.py::showEvent())."""
        while self._layout.count() > 0:
            item = self._layout.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._items.clear()
        self._sections.clear()
        self._current_section = None
        self._separators.clear()
