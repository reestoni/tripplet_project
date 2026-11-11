# ui/screen_onboarding.py
"""Onboarding (Nutzerwunsch 2026-11-06): full screen (not a popup) with short
animated introductions to our work. Left the topics (ui/onboarding_catalog.py,
grouped by category), right the module page (QWebEngineView on
assets/onboarding/<key>.html). Language via flags as in the help dialogs,
plus Chinese; the choice is remembered (QSettings TrippleT/Onboarding/language,
first time = the help language). Switching the flag calls window.setLang() in
the page - the animation keeps running where it is.

Sidebar: pinned entry "Onboarding" below "Help (F1)" (like the help, for
everybody, not switchable in db/feature_access.py). main.py sets
app_meta.open_onboarding.
"""
from __future__ import annotations

import json
import os
from typing import Dict, Optional

from PySide6.QtCore import QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QSplitter, QStackedWidget, QStyle, QTabBar, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from ui import onboarding_catalog as cat
from ui.pathutil import resource_path
from ui.widgets import sidebar_nav

ACCENT = "#1F7A3A"
PAGE_BG = "#F4F6F3"
# same tabs as Show Experiment / Create Experiment (accent colour replaced at runtime)
TAB_QSS = """
    QTabBar::tab { background: #ffffff; color: #39a650; border: 1px solid #cfcfcf;
                   padding: 8px 14px; margin-right: 4px; border-bottom: none; }
    QTabBar::tab:hover { background: #e9e9e9; }
    QTabBar::tab:selected { background: #000000; color: #39a650; }
"""
_SETTINGS = ("TrippleT", "Onboarding", "language")
_LAST_MODULE = ("TrippleT", "Onboarding", "module")
_QUIZ = ("TrippleT", "Onboarding")   # key "quiz/<module>" = best result "right/total" (per Windows user)


def load_quiz_result(key: str):
    """Best quiz result of a module on this PC as (right, total), or None."""
    try:
        v = QSettings(*_QUIZ).value(f"quiz/{key}", None)
        r, t = (int(x) for x in str(v).split("/"))
        return (r, t) if t > 0 else None
    except Exception:
        return None


def save_quiz_result(key: str, right: int, total: int) -> None:
    """Keeps the best result (a passed quiz stays passed)."""
    old = load_quiz_result(key)
    if old and old[1] == total and old[0] >= right:
        return
    try:
        QSettings(*_QUIZ).setValue(f"quiz/{key}", f"{right}/{total}")
    except Exception:
        pass


def record_quiz_result(key: str, title: str, lang: str) -> bool:
    """Page reports "quiz:<right>:<total>" when all questions are answered (assets/onboarding/quiz.js).
    Lernnachweis: usage log (with user, also on prod) + best result on this PC for the tick in the list.
    Also used by the popup (ui/widgets/kb_popup.py). True if a valid result was recorded."""
    try:
        _, r, t = title.split(":")
        right, total = int(r), int(t)
    except ValueError:
        return False
    if total <= 0 or not 0 <= right <= total:
        return False
    passed = cat.quiz_passed(right, total)
    save_quiz_result(key, right, total)
    try:
        from db.usage_log import log_usage_event
        log_usage_event("feature", "onboarding_quiz",
                        f"{key} {right}/{total} {'passed' if passed else 'failed'} ({lang})")
    except Exception:
        pass
    return True


def load_language() -> str:
    try:
        org, app, key = _SETTINGS
        lang = QSettings(org, app).value(key, None)
        if lang in cat.LANGS:
            return lang
        from ui.widgets.multilang_help import load_language as help_lang
        lang = help_lang()
        return lang if lang in cat.LANGS else "en"
    except Exception:
        return "en"


def save_language(lang: str) -> None:
    try:
        org, app, key = _SETTINGS
        QSettings(org, app).setValue(key, lang)
    except Exception:
        pass


def module_url(module: cat.Module, lang: str) -> QUrl:
    url = QUrl.fromLocalFile(resource_path(module.file))
    url.setQuery(f"lang={lang}&embedded=1")
    return url


class OnboardingScreen(QWidget):
    def __init__(self, sidebar_callbacks: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None
        self._lang = load_language()
        self._module: Optional[cat.Module] = None
        self._items: Dict[str, QTreeWidgetItem] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._sidebar, content = sidebar_nav.wrap_body_with_sidebar(root)
        page = QWidget()
        page.setObjectName("Page")
        page.setStyleSheet("QWidget#Page{background:#F4F6F3;}")
        content.addWidget(page)
        pv = QVBoxLayout(page)
        pv.setContentsMargins(20, 14, 20, 12)
        pv.setSpacing(10)

        head = QHBoxLayout()
        icon = QLabel()
        from PySide6.QtGui import QPixmap
        pm = QPixmap(resource_path("assets/images/onboarding_120.png"))
        if not pm.isNull():
            icon.setPixmap(pm.scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        head.addWidget(icon, 0, Qt.AlignVCenter)
        head.addSpacing(6)
        tbox = QVBoxLayout()
        tbox.setSpacing(0)
        self.lbl_kicker = QLabel()
        self.lbl_kicker.setStyleSheet(f"color:{ACCENT}; font-size:11px; font-weight:700; letter-spacing:1px;")
        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet("font-size:20px; font-weight:700; color:#1C2321;")
        self.lbl_sub = QLabel()
        self.lbl_sub.setStyleSheet("color:#5A6460; font-size:12px;")
        for w in (self.lbl_kicker, self.lbl_title, self.lbl_sub):
            tbox.addWidget(w)
        head.addLayout(tbox, 1)
        from ui.widgets.multilang_help import build_flag_row
        flag_row, self._flags = build_flag_row(self.set_language, self, languages=cat.LANGUAGES)
        head.addLayout(flag_row)
        pv.addLayout(head)

        split = QSplitter(Qt.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(200)
        self.tree.setStyleSheet("QTreeWidget{background:#FFFFFF;border:1px solid #DADFD8;border-radius:6px;}"
                                "QTreeWidget::item{padding:6px 2px;}"
                                "QTreeWidget::item:selected{background:#E3F1E6;color:#1C2321;}")
        self.tree.itemSelectionChanged.connect(self._on_pick)
        # chapters/categories open and close with a click on their name; the
        # open/closed state of the chapters is remembered (QSettings)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemExpanded.connect(lambda it: self._remember_area(it, True))
        self.tree.itemCollapsed.connect(lambda it: self._remember_area(it, False))
        split.addWidget(self.tree)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)
        # scenes of the module as standard TrippleT tabs; the page reports its
        # scene back via document.title "scene:<n>" (it also advances by itself)
        self.scene_tabs = QTabBar()
        self.scene_tabs.setDrawBase(False)
        self.scene_tabs.setExpanding(False)
        try:
            from ui.theme import get_accent
            self.scene_tabs.setStyleSheet(TAB_QSS.replace("#39a650", get_accent()))
        except Exception:
            self.scene_tabs.setStyleSheet(TAB_QSS)
        self.scene_tabs.currentChanged.connect(self._on_tab)
        rv.addWidget(self.scene_tabs)
        self.stack = QStackedWidget()
        rv.addWidget(self.stack, 1)
        self.lbl_empty = QLabel()
        self.lbl_empty.setAlignment(Qt.AlignCenter)
        self.lbl_empty.setStyleSheet("color:#5A6460; font-size:14px;")
        self.stack.addWidget(self.lbl_empty)
        self.web = None
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
            self.web = QWebEngineView()
            self.web.page().setBackgroundColor(QColor(PAGE_BG))
            self.web.titleChanged.connect(self._on_page_title)
            self.stack.addWidget(self.web)
        except Exception:  # WebEngine missing - list still works, page says why
            self.lbl_empty.setText("The Knowledge Base pages need Qt WebEngine, which is not available here.")
        split.addWidget(right)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([240, 1300])
        pv.addWidget(split, 1)

        self._fill_tree()
        self._apply_texts()

    # ── lifecycle ───────────────────────────────────────────────────────
    def showEvent(self, event):  # noqa: N802
        try:
            import app_meta
            level = int((app_meta.current_user or {}).get("access_level") or 0)
            sidebar_nav.refresh_lazy_sidebar(self, level)
        except Exception:
            pass
        super().showEvent(event)
        if self._module is None:
            QTimer.singleShot(0, self._open_first)

    def _open_first(self) -> None:
        if self._module is not None or not cat.MODULES:
            return
        try:
            last = QSettings(*_LAST_MODULE[:2]).value(_LAST_MODULE[2], None)
        except Exception:
            last = None
        first = cat.START_MODULE if cat.START_MODULE in self._items else cat.MODULES[0].key
        self.open_module(last if last in self._items else first)

    # ── list ────────────────────────────────────────────────────────────
    def _fill_tree(self) -> None:
        self.tree.blockSignals(True)
        self.tree.clear()
        self._items.clear()
        area_items: Dict[str, QTreeWidgetItem] = {}
        closed = self._closed_areas()
        start = next((m for m in cat.MODULES if m.key == cat.START_MODULE), None)
        if start is not None:   # start page (textile chain): stand-alone first entry above the areas
            it = QTreeWidgetItem([cat.text(start.title, self._lang)])
            it.setData(0, Qt.UserRole, start.key)
            it.setToolTip(0, cat.text(start.summary, self._lang))
            fs = it.font(0)
            fs.setBold(True)
            it.setFont(0, fs)
            self.tree.addTopLevelItem(it)
            self._items[start.key] = it
        for ckey, names in cat.CATEGORIES.items():
            mods = [m for m in cat.MODULES if m.category == ckey]
            if not mods:
                continue
            area = cat.CATEGORY_AREA.get(ckey)
            head = area_items.get(area) if area else None
            if area and head is None:   # chapter (Heberlein / Our technology / ...), can be closed
                head = QTreeWidgetItem([cat.text(cat.AREAS[area], self._lang).upper()])
                head.setFlags(Qt.ItemIsEnabled)
                fh = head.font(0)
                fh.setBold(True)
                fh.setPointSizeF(max(7.0, fh.pointSizeF() - 1))
                head.setFont(0, fh)
                head.setForeground(0, QColor("#39A650"))
                head.setData(0, Qt.UserRole + 1, area)
                self.tree.addTopLevelItem(head)
                area_items[area] = head
            top = QTreeWidgetItem([cat.text(names, self._lang)])
            top.setFlags(Qt.ItemIsEnabled)
            f = top.font(0)
            f.setBold(True)
            top.setFont(0, f)
            if head is not None:
                head.addChild(top)
            else:
                self.tree.addTopLevelItem(top)
            folders = {}
            for m in [m for m in mods if not m.group] + [m for m in mods if m.group]:
                parent = top
                if m.group:   # sub-folder inside the category (e.g. DTY > Specialist knowledge)
                    parent = folders.get(m.group)
                    if parent is None:
                        parent = QTreeWidgetItem([cat.text(cat.GROUPS.get(m.group, {"en": m.group}), self._lang)])
                        parent.setFlags(Qt.ItemIsEnabled)
                        fi = parent.font(0)
                        fi.setItalic(True)
                        fi.setBold(True)
                        parent.setFont(0, fi)
                        top.addChild(parent)
                        folders[m.group] = parent
                it = QTreeWidgetItem([cat.text(m.title, self._lang)])
                it.setData(0, Qt.UserRole, m.key)
                tip = f"{cat.text(m.summary, self._lang)}  (~{m.minutes} min)"
                res = load_quiz_result(m.key)
                if res:
                    ok = cat.quiz_passed(*res)
                    tip += "\n" + cat.text(cat.UI["quizPassed" if ok else "quizOpen"], self._lang).format(r=res[0], t=res[1])
                    if ok:
                        it.setIcon(0, self.style().standardIcon(QStyle.SP_DialogApplyButton))
                it.setToolTip(0, tip)
                parent.addChild(it)
                self._items[m.key] = it
            top.setExpanded(True)
            for f_item in folders.values():
                f_item.setExpanded(True)
        for area, head in area_items.items():
            head.setExpanded(area not in closed)
        if self._module is not None and self._module.key in self._items:
            self._items[self._module.key].setSelected(True)
        self.tree.blockSignals(False)

    # ── open / close chapters ──────────────────────────────────────────
    def _closed_areas(self) -> set:
        try:
            val = QSettings(*_QUIZ).value("closed_areas", [])
        except Exception:
            return set()
        if isinstance(val, str):
            val = [val] if val else []
        return {str(v) for v in (val or [])}

    def _remember_area(self, item, opened: bool) -> None:
        area = item.data(0, Qt.UserRole + 1)
        if not area:
            return
        closed = self._closed_areas()
        (closed.discard if opened else closed.add)(str(area))
        try:
            QSettings(*_QUIZ).setValue("closed_areas", sorted(closed))
        except Exception:
            pass

    def _on_item_clicked(self, item, _col=0) -> None:
        """A click on a chapter, category or folder name opens/closes it."""
        if item.data(0, Qt.UserRole) is None and item.childCount():
            item.setExpanded(not item.isExpanded())

    def _reveal(self, item) -> None:
        """Opens the chapter/category of a module that is opened from elsewhere."""
        p = item.parent()
        while p is not None:
            if not p.isExpanded():
                p.setExpanded(True)
            p = p.parent()

    def _on_pick(self) -> None:
        sel = self.tree.selectedItems()
        key = sel[0].data(0, Qt.UserRole) if sel else None
        if key and (self._module is None or key != self._module.key):
            self.open_module(key)

    # ── module / language ──────────────────────────────────────────────
    def open_module(self, key: str) -> None:
        mod = next((m for m in cat.MODULES if m.key == key), None)
        if mod is None:
            return
        self._module = mod
        it = self._items.get(key)
        if it is not None:
            self._reveal(it)
        if it is not None and not it.isSelected():
            self.tree.blockSignals(True)
            self.tree.clearSelection()
            it.setSelected(True)
            self.tree.blockSignals(False)
        try:
            QSettings(*_LAST_MODULE[:2]).setValue(_LAST_MODULE[2], key)
        except Exception:
            pass
        self._apply_texts()
        self._fill_tabs(0)
        if self.web is None:
            self.stack.setCurrentWidget(self.lbl_empty)
            return
        if not os.path.exists(resource_path(mod.file)):
            self.lbl_empty.setText(cat.text(cat.UI["missing"], self._lang))
            self.stack.setCurrentWidget(self.lbl_empty)
            return
        self.web.load(module_url(mod, self._lang))
        self.stack.setCurrentWidget(self.web)
        try:
            from db.usage_log import log_usage_event
            log_usage_event("feature", "onboarding_module", key)
        except Exception:
            pass

    def set_language(self, lang: str) -> None:
        if lang not in cat.LANGS:
            return
        self._lang = lang
        save_language(lang)
        self._fill_tree()
        self._apply_texts()
        self._fill_tabs(self.scene_tabs.currentIndex())
        if self.web is not None and self._module is not None:
            # in place: the animation keeps its scene and position
            self.web.page().runJavaScript(f"window.setLang && window.setLang({json.dumps(lang)});")

    # ── scene tabs ─────────────────────────────────────────────────────
    def _fill_tabs(self, current: int = 0) -> None:
        names = cat.scene_names(self._module.key, self._lang) if self._module else []
        self.scene_tabs.blockSignals(True)
        while self.scene_tabs.count():
            self.scene_tabs.removeTab(0)
        for n in names:
            self.scene_tabs.addTab(n.replace("&", "&&"))  # "&" would be eaten as a mnemonic marker
        if names:
            self.scene_tabs.setCurrentIndex(max(0, min(current, len(names) - 1)))
        self.scene_tabs.setVisible(bool(names))
        self.scene_tabs.blockSignals(False)

    def _on_tab(self, index: int) -> None:
        if self.web is not None and index >= 0:
            self.web.page().runJavaScript(f"window.goScene && window.goScene({int(index)});")

    def _on_page_title(self, title: str) -> None:
        if title.startswith("open:"):   # a page links to another module (e.g. history -> DTY)
            key = title.split(":", 1)[1]
            if any(m.key == key for m in cat.MODULES):
                QTimer.singleShot(0, lambda: self.open_module(key))
            return
        if title.startswith("tool:"):   # start page links an app tool (Yarn Count Converter)
            if title.split(":", 1)[1] == "yarn_count":
                try:
                    import app_meta
                    if callable(app_meta.open_yarn_count):
                        QTimer.singleShot(0, app_meta.open_yarn_count)
                except Exception:
                    pass
            return
        if title.startswith("quiz:"):
            self._on_quiz_result(title)
            return
        if not title.startswith("scene:"):
            return
        try:
            index = int(title.split(":", 1)[1])
        except ValueError:
            return
        if 0 <= index < self.scene_tabs.count() and index != self.scene_tabs.currentIndex():
            self.scene_tabs.blockSignals(True)
            self.scene_tabs.setCurrentIndex(index)
            self.scene_tabs.blockSignals(False)

    def _on_quiz_result(self, title: str) -> None:
        if self._module is not None and record_quiz_result(self._module.key, title, self._lang):
            self._fill_tree()

    @property
    def language(self) -> str:
        return self._lang

    def _apply_texts(self) -> None:
        self.lbl_kicker.setText(cat.text(cat.UI["kicker"], self._lang))
        self.lbl_title.setText(cat.text(self._module.title, self._lang) if self._module
                               else cat.text(cat.UI["title"], self._lang))
        self.lbl_sub.setText(cat.text(self._module.summary, self._lang) if self._module
                             else cat.text(cat.UI["subtitle"], self._lang))
        btn = self._flags.get(self._lang)
        if btn is not None:
            btn.setChecked(True)
