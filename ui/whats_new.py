"""whats_new.py - "What's new" per version, Nutzerwunsch 2026-10-15.

Window: versions on the left (number + date, NEW for versions the user has
not seen yet), the new features of the chosen version on the right as cards
with a small sketch (assets/images/whats_new/, tools/gen_whats_new_svgs.py).
Language flags and language choice shared with the help pages.

a) Seen once automatically: after login the window opens if the user has
   not seen the newest version yet; that version is then stored per user
   ("whats_new_seen" in the display settings, tblUser.DisplaySettings -
   follows the login to every PC; without that column QSettings on this PC).
b) Any time again: Sidebar -> Account -> "What's new".

Versions: the entry being worked on has "version": "current" and shows
app_meta.APP_VERSION; compiled versions carry their fixed number and date
(see ui/widgets/whats_new_texts.py). No version check.
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget,
)

from ui.widgets.whats_new_texts import (
    CLOSE, CURRENT_LABEL, NEW_BADGE, RELEASES, VERSION_LABEL, VERSIONS_TITLE, WHERE_LABEL, WINDOW_TITLE,
)

SKETCH_DIR = "assets/images/whats_new"
SKETCH_W, SKETCH_H = 300, 130


# ── versions ─────────────────────────────────────────────────────────────
def release_version(release: Dict[str, Any]) -> str:
    v = str(release.get("version") or "")
    if v == "current":
        import app_meta
        return str(app_meta.APP_VERSION)
    return v


def current_release_id() -> Optional[str]:
    return release_version(RELEASES[0]) if RELEASES else None


def _date_text(iso: str, lang: str) -> str:
    try:
        d = datetime.date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or ""
    return d.strftime("%d %b %Y") if lang == "en" else d.strftime("%d.%m.%Y" if lang == "de" else "%d/%m/%Y")


def _current_when(lang: str) -> str:
    """Date of the version being worked on: in the compiled exe the day the
    exe was built (the entry only gets its fixed date after the compile),
    from source "in progress"."""
    import os
    import sys
    if getattr(sys, "frozen", False):
        try:
            built = datetime.date.fromtimestamp(os.path.getmtime(sys.executable))
            return _date_text(built.isoformat(), lang)
        except OSError:
            return ""
    return CURRENT_LABEL[lang]


def release_when(release: Dict[str, Any], lang: str) -> str:
    return _date_text(release["date"], lang) if release.get("date") else _current_when(lang)


def unseen_versions() -> List[str]:
    """Versions newer than the one the user has seen (all if none seen)."""
    from ui import display_prefs
    seen = display_prefs.current().get("whats_new_seen") or ""
    versions = [release_version(r) for r in RELEASES]
    return versions[:versions.index(seen)] if seen in versions else versions


def has_unseen() -> bool:
    return bool(RELEASES) and bool(unseen_versions())


def mark_seen() -> None:
    from ui import display_prefs
    cur = current_release_id()
    if cur and display_prefs.current().get("whats_new_seen") != cur:
        display_prefs.update(whats_new_seen=cur)
        display_prefs.save_now()


# ── window ───────────────────────────────────────────────────────────────
def feature_card(title: str, text: str, where: str, sketch: Optional[str], lang: str) -> QFrame:
    from ui.theme import get_accent
    card = QFrame()
    card.setObjectName("WhatsNewCard")
    card.setStyleSheet(
        f"QFrame#WhatsNewCard{{background:#ffffff;border:1px solid #dcdcdc;"
        f"border-left:5px solid {get_accent()};border-radius:6px;}}"
        "QFrame#WhatsNewCard QLabel{border:none;background:transparent;}")
    lay = QHBoxLayout(card)
    lay.setContentsMargins(14, 10, 12, 10)
    lay.setSpacing(16)
    col = QVBoxLayout()
    col.setSpacing(4)
    t = QLabel(title)
    f = QFont(t.font())
    f.setPointSizeF(f.pointSizeF() * 1.25 if f.pointSizeF() > 0 else 12)
    f.setBold(True)
    t.setFont(f)
    t.setWordWrap(True)
    col.addWidget(t)
    body = QLabel(text)
    body.setWordWrap(True)
    body.setTextFormat(Qt.RichText)
    col.addWidget(body)
    w = QLabel(f"<span style='color:#565656'>{WHERE_LABEL[lang]}</span> {where}")
    w.setWordWrap(True)
    w.setTextFormat(Qt.RichText)
    w.setStyleSheet("color:#2b2b2b; padding-top:4px;")
    col.addWidget(w)
    col.addStretch(1)
    lay.addLayout(col, 1)
    if sketch:
        from ui.widgets.multilang_help import svg_widget
        try:
            lay.addWidget(svg_widget(f"{SKETCH_DIR}/{sketch}", {}, SKETCH_W, SKETCH_H), 0, Qt.AlignTop)
            # word-wrapped text next to a fixed sketch: Qt underestimates the
            # height, the card would be squeezed - at least sketch height
            card.setMinimumHeight(SKETCH_H + 22)
        except OSError:
            pass
    from PySide6.QtWidgets import QSizePolicy
    card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
    return card


class WhatsNewDialog(QDialog):
    def __init__(self, parent=None, language: Optional[str] = None):
        super().__init__(parent)
        from ui.widgets.multilang_help import build_flag_row, load_language, DEFAULT_LANGUAGE
        self._lang = language if language in WINDOW_TITLE else load_language()
        if self._lang not in WINDOW_TITLE:
            self._lang = DEFAULT_LANGUAGE
        self._unseen = set(unseen_versions())
        self.resize(1100, 820)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 12)
        top = QHBoxLayout()
        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet("font-size:20px; font-weight:700;")
        top.addWidget(self.lbl_title)
        flag_row, self._flag_buttons = build_flag_row(self.set_language, self)
        top.addLayout(flag_row, 1)
        outer.addLayout(top)

        body = QHBoxLayout()
        left = QVBoxLayout()
        self.lbl_versions = QLabel()
        self.lbl_versions.setStyleSheet("font-weight:700; color:#565656;")
        left.addWidget(self.lbl_versions)
        self.lst = QListWidget()
        self.lst.setFixedWidth(210)
        self.lst.setStyleSheet(
            "QListWidget::item{padding:8px 6px; border-bottom:1px solid #eeeeee; color:#1a1a1a;}"
            "QListWidget::item:selected{background:#d8e7fa; color:#1a1a1a;}")
        self.lst.currentRowChanged.connect(self._show_release)
        left.addWidget(self.lst, 1)
        body.addLayout(left)

        from ui.widgets.multilang_help import scroll_page
        self.scroll, self._page = scroll_page()
        body.addWidget(self.scroll, 1)
        outer.addLayout(body, 1)

        row = QHBoxLayout()
        row.addStretch(1)
        self.btn_close = QPushButton()
        self.btn_close.clicked.connect(self.accept)
        row.addWidget(self.btn_close)
        outer.addLayout(row)
        self._apply_language()

    def set_language(self, lang: str) -> None:
        from ui.widgets.multilang_help import save_language
        if lang not in WINDOW_TITLE:
            return
        if lang != self._lang:
            self._lang = lang
            save_language(lang)
            self._apply_language()
        self._flag_buttons[lang].setChecked(True)

    def _apply_language(self) -> None:
        lang = self._lang
        self.setWindowTitle(WINDOW_TITLE[lang])
        self.lbl_title.setText(WINDOW_TITLE[lang])
        self.lbl_versions.setText(VERSIONS_TITLE[lang])
        self.btn_close.setText(CLOSE[lang])
        self._flag_buttons[lang].setChecked(True)
        row = max(0, self.lst.currentRow())
        self.lst.blockSignals(True)
        self.lst.clear()
        for r in RELEASES:
            v = release_version(r)
            text = f"{VERSION_LABEL[lang]} {v}\n{release_when(r, lang)}"
            if v in self._unseen:
                text += f"   {NEW_BADGE[lang]}"
            it = QListWidgetItem(text)
            if v in self._unseen:
                f = it.font()
                f.setBold(True)
                it.setFont(f)
                it.setForeground(QColor("#1f6f33"))
            self.lst.addItem(it)
        self.lst.blockSignals(False)
        if self.lst.count():
            self.lst.blockSignals(True)
            self.lst.setCurrentRow(min(row, self.lst.count() - 1))
            self.lst.blockSignals(False)
            self._show_release(self.lst.currentRow())

    def _show_release(self, idx: int) -> None:
        from ui.widgets.multilang_help import heading, render_block
        while self._page.count():
            item = self._page.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()  # deleteLater() alone leaves it visible until the next event loop
                w.setParent(None)
                w.deleteLater()
        if not (0 <= idx < len(RELEASES)):
            return
        r, lang = RELEASES[idx], self._lang
        head = heading(f"{VERSION_LABEL[lang]} {release_version(r)}  ·  {release_when(r, lang)}")
        head.setStyleSheet(head.styleSheet() + "font-size:18px;")
        self._page.addWidget(head)
        for block in r["texts"][lang]:
            if block[0] == "feature":
                _, title, text, where, sketch = block
                self._page.addWidget(feature_card(title, text, where, sketch, lang))
            else:
                render_block(self._page, block)
        self._page.addStretch(1)
        self.scroll.verticalScrollBar().setValue(0)


def show_whats_new(parent=None) -> None:
    if not RELEASES:
        return
    WhatsNewDialog(parent).exec()
    mark_seen()


def show_if_unseen(parent=None) -> None:
    """Called once after login (screen_login.py)."""
    try:
        if has_unseen():
            show_whats_new(parent)
            try:
                from db.usage_log import log_usage_event
                log_usage_event("feature", "whats_new_auto", str(current_release_id()))
            except Exception:
                pass
    except Exception:
        pass
