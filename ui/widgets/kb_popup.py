# ui/widgets/kb_popup.py
"""Knowledge Base page as a popup (Nutzerwunsch 2026-11-10): opened from a
right-click in the app (ui/kb_links.py) at the right scene and station.
Close (button or Esc) and the user is back in the original screen, nothing
there has changed. Same page, scene tabs, flags and quiz record as the
Knowledge Base screen (ui/screen_onboarding.py)."""
from __future__ import annotations

import json
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel, QPushButton, QTabBar,
                               QVBoxLayout)

from ui import onboarding_catalog as cat
from ui import screen_onboarding as so


_SCENE_BASE: dict = {}


def scene_param_base(key: str) -> int:
    """1 if the page reads ?scene= 1-based (go((+params.get('scene')||1)-1)),
    0 if 0-based (parseInt(params.get('scene')||'0')) - both styles exist."""
    if key not in _SCENE_BASE:
        mod = next((m for m in cat.MODULES if m.key == key), None)
        try:
            from ui.pathutil import resource_path
            src = open(resource_path(mod.file), encoding="utf-8").read() if mod else ""
        except Exception:
            src = ""
        _SCENE_BASE[key] = 1 if "(+params.get('scene')||1)-1" in src else 0
    return _SCENE_BASE[key]


class KBPopup(QDialog):
    def __init__(self, parent, key: str, scene: Optional[int] = None, station: Optional[int] = None,
                 params: Optional[dict] = None):
        super().__init__(parent)
        self.setObjectName("KBPopup")
        self.setStyleSheet(f"QDialog#KBPopup{{background:{so.PAGE_BG};}}")
        self._lang = so.load_language()
        self._module: Optional[cat.Module] = None
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)
        head = QHBoxLayout()
        tbox = QVBoxLayout()
        tbox.setSpacing(0)
        self.lbl_kicker = QLabel()
        self.lbl_kicker.setStyleSheet(f"color:{so.ACCENT}; font-size:11px; font-weight:700; letter-spacing:1px;")
        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet("font-size:18px; font-weight:700; color:#1C2321;")
        self.lbl_sub = QLabel()
        self.lbl_sub.setStyleSheet("color:#5A6460; font-size:12px;")
        self.lbl_sub.setWordWrap(True)
        for w in (self.lbl_kicker, self.lbl_title, self.lbl_sub):
            tbox.addWidget(w)
        head.addLayout(tbox, 1)
        from ui.widgets.multilang_help import build_flag_row
        flag_row, self._flags = build_flag_row(self.set_language, self, languages=cat.LANGUAGES)
        head.addLayout(flag_row)
        head.addSpacing(10)
        self.btn_close = QPushButton("Close")
        self.btn_close.setToolTip("Close and go back (Esc)")
        self.btn_close.clicked.connect(self.accept)
        head.addWidget(self.btn_close, 0, Qt.AlignTop)
        root.addLayout(head)

        self.scene_tabs = QTabBar()
        self.scene_tabs.setDrawBase(False)
        self.scene_tabs.setExpanding(False)
        try:
            from ui.theme import get_accent
            self.scene_tabs.setStyleSheet(so.TAB_QSS.replace("#39a650", get_accent()))
        except Exception:
            self.scene_tabs.setStyleSheet(so.TAB_QSS)
        self.scene_tabs.currentChanged.connect(self._on_tab)
        root.addWidget(self.scene_tabs)

        self.web = None
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
            self.web = QWebEngineView(self)
            self.web.page().setBackgroundColor(QColor(so.PAGE_BG))
            self.web.titleChanged.connect(self._on_page_title)
            root.addWidget(self.web, 1)
        except Exception:
            msg = QLabel("The Knowledge Base pages need Qt WebEngine, which is not available here.")
            msg.setAlignment(Qt.AlignCenter)
            root.addWidget(msg, 1)

        self._size_to_parent()
        self.open_module(key, scene, station, params)

    def _size_to_parent(self) -> None:
        win = self.parent().window() if self.parent() is not None else None
        geo = win.geometry() if win is not None else QApplication.primaryScreen().availableGeometry()
        w, h = max(900, int(geo.width() * 0.85)), max(600, int(geo.height() * 0.85))
        self.resize(w, h)
        self.move(geo.x() + (geo.width() - w) // 2, geo.y() + (geo.height() - h) // 2)

    # ── module ──────────────────────────────────────────────────────────
    def open_module(self, key: str, scene: Optional[int] = None, station: Optional[int] = None,
                    params: Optional[dict] = None) -> None:
        mod = next((m for m in cat.MODULES if m.key == key), None)
        if mod is None:
            return
        self._module = mod
        self._apply_texts()
        self._fill_tabs((scene or 1) - 1)
        if self.web is None:
            return
        url = so.module_url(mod, self._lang)
        query = url.query()
        if scene:
            # scene is 1-based here; some pages read ?scene= 0-based (scene_param_base)
            query += f"&scene={int(scene) - 1 + scene_param_base(mod.key)}"
        if station:
            query += f"&station={int(station)}"
        from urllib.parse import quote
        for k, v in (params or {}).items():
            query += f"&{quote(str(k))}={quote(str(v))}"
        url.setQuery(query)
        self.web.load(url)

    def set_language(self, lang: str) -> None:
        if lang not in cat.LANGS:
            return
        self._lang = lang
        so.save_language(lang)
        self._apply_texts()
        self._fill_tabs(self.scene_tabs.currentIndex())
        if self.web is not None:
            self.web.page().runJavaScript(f"window.setLang && window.setLang({json.dumps(lang)});")

    def _apply_texts(self) -> None:
        self.lbl_kicker.setText(cat.text(cat.UI["kicker"], self._lang))
        if self._module is not None:
            title = cat.text(self._module.title, self._lang)
            self.lbl_title.setText(title)
            self.lbl_sub.setText(cat.text(self._module.summary, self._lang))
            self.setWindowTitle(f"Knowledge Base – {title}")
        btn = self._flags.get(self._lang)
        if btn is not None:
            btn.setChecked(True)

    # ── scene tabs (same protocol as the Knowledge Base screen) ─────────
    def _fill_tabs(self, current: int = 0) -> None:
        names = cat.scene_names(self._module.key, self._lang) if self._module else []
        self.scene_tabs.blockSignals(True)
        while self.scene_tabs.count():
            self.scene_tabs.removeTab(0)
        for n in names:
            self.scene_tabs.addTab(n.replace("&", "&&"))
        if names:
            self.scene_tabs.setCurrentIndex(max(0, min(current, len(names) - 1)))
        self.scene_tabs.setVisible(bool(names))
        self.scene_tabs.blockSignals(False)

    def _on_tab(self, index: int) -> None:
        if self.web is not None and index >= 0:
            self.web.page().runJavaScript(f"window.goScene && window.goScene({int(index)});")

    def _on_page_title(self, title: str) -> None:
        if title.startswith("open:"):   # link to another module: stays in the popup
            key = title.split(":", 1)[1]
            if any(m.key == key for m in cat.MODULES):
                QTimer.singleShot(0, lambda: self.open_module(key))
            return
        if title.startswith("quiz:"):
            if self._module is not None:
                so.record_quiz_result(self._module.key, title, self._lang)
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


def show_kb_popup(parent, key: str, scene: Optional[int] = None, station: Optional[int] = None,
                  source: str = "", params: Optional[dict] = None) -> None:
    """Opens the popup modally; returns when the user closes it."""
    try:
        from db.usage_log import log_usage_event
        log_usage_event("feature", "kb_context_open", f"{source} -> {key}" if source else key)
    except Exception:
        pass
    try:
        dlg = KBPopup(parent, key, scene, station, params)
    except Exception as e:
        from ui.widgets.friendly_error import show_error
        show_error(parent, "Knowledge Base", "The Knowledge Base page could not be opened.", e)
        return
    dlg.exec()
    dlg.deleteLater()
