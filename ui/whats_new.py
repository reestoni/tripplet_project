"""whats_new.py - "What's new" per version, Nutzerwunsch 2026-10-15. Shown to
the users as "Fresh off the Spool" (name since 2026-10-16, WINDOW_TITLE);
code, files and usage events keep the old internal name whats_new.

Window: versions on the left (number + date, NEW for versions the user has
not seen yet), the new features of the chosen version on the right as cards
with a small sketch (assets/images/whats_new/, tools/gen_whats_new_svgs.py).
Language flags and language choice shared with the help pages.

a) Seen once automatically: after login the window opens if the user has
   not seen the newest version yet; that version is then stored per user
   ("whats_new_seen" in the display settings, tblUser.DisplaySettings -
   follows the login to every PC; without that column QSettings on this PC).
b) Any time again: Sidebar -> Account -> "Fresh off the Spool". Button "PDF" saves
   the shown version as PDF (ui/whats_new_pdf.py, one section per page).
c) Search (field above the version list): finds feature cards across all
   versions, in all three languages and with the help-search synonyms
   (search_features()); results grouped by version, the version list shows
   the hit count per version and greys out versions without hits.
d) One tab per section heading (Show Experiment, Settings, …) with the
   number of features, e.g. "Show Experiment (8)" (release_sections());
   search results stay one list over all versions. The PDF export
   (ui/whats_new_pdf.py) is unchanged - one long document.

Versions: the entry being worked on has "version": "current" and shows
app_meta.APP_VERSION; compiled versions carry their fixed number and date
(see ui/widgets/whats_new_texts.py). No version check.
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QStackedWidget,
    QTabWidget, QVBoxLayout, QWidget,
)

from ui.widgets.whats_new_texts import (
    CLOSE, CURRENT_LABEL, HITS_LABEL, NEW_BADGE, PDF_TOOLTIP, RELEASES, SUBTITLE, SEARCH_NONE, SEARCH_PLACEHOLDER, SEARCH_RESULTS,
    VERSION_LABEL, VERSIONS_TITLE, WHERE_LABEL, WINDOW_TITLE,
)

SKETCH_DIR = "assets/images/whats_new"
SKETCH_W, SKETCH_H = 300, 130
# the magazine logo (window head, PDF masthead); a sketch may also be a .png
LOGO = f"{SKETCH_DIR}/fresh_off_the_spool.png"


def logo_pixmap(max_w: int, max_h: int, dpr: float = 1.0):
    """The logo scaled into max_w x max_h (sharp on high-DPI screens), None if missing."""
    from PySide6.QtGui import QPixmap
    from ui.widgets.multilang_help import resource_path
    return _fit(QPixmap(resource_path(LOGO)), max_w, max_h, dpr)


def _fit(pm, max_w: int, max_h: int, dpr: float):
    if pm.isNull():
        return None
    dpr = max(1.0, float(dpr or 1.0))
    pm = pm.scaled(int(max_w * dpr), int(max_h * dpr), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    pm.setDevicePixelRatio(dpr)
    return pm


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


def release_sections(release: Dict[str, Any], lang: str) -> List[Tuple[str, List[tuple]]]:
    """[(heading, blocks)] - one entry per ("h", …) heading; blocks before
    the first heading go into the first section (or an untitled one)."""
    sections: List[Tuple[str, List[tuple]]] = []
    lead: List[tuple] = []
    for block in release["texts"][lang]:
        if block[0] == "h":
            sections.append((str(block[1]), list(lead) if not sections else []))
            lead = []
        elif sections:
            sections[-1][1].append(block)
        else:
            lead.append(block)
    if lead:  # no heading at all
        sections.append(("", lead))
    return sections


# ── search ───────────────────────────────────────────────────────────────
def _search_index() -> List[Tuple[int, int, set, set]]:
    """(release idx, block idx, words, synonym concepts) per feature card;
    words of title, text and "where" in all languages together."""
    from ui.widgets.help_search import _phrase_concepts, concepts_of, normalize
    idx = []
    for ri, r in enumerate(RELEASES):
        for bi, block in enumerate(r["texts"]["en"]):
            if block[0] != "feature":
                continue
            norm = normalize(" ".join(" ".join(str(x) for x in blocks[bi][1:4])
                                      for blocks in r["texts"].values()))
            words = set(norm.split())
            concepts = set(_phrase_concepts(norm))
            for w in words:
                concepts |= concepts_of(w)
            idx.append((ri, bi, words, concepts))
    return idx


def search_features(query: str) -> List[Tuple[int, int]]:
    """Feature cards matching every search word, as (release idx, block idx),
    newest version first. A word matches literally (also as the start of a
    word, from 3 letters: "ref" -> "reference"), in any language, or via the
    synonyms of the help search."""
    from ui.widgets.help_search import _word_match, concepts_of, tokens
    toks = tokens(query)
    if not toks:
        return []
    terms = [(t, concepts_of(t)) for t in toks]
    hits = []
    for ri, bi, words, concepts in _search_index():
        if all(bool(cons & concepts) or any(_word_match(t, w) or (len(t) >= 3 and w.startswith(t)) for w in words)
               for t, cons in terms):
            hits.append((ri, bi))
    return hits


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
    if sketch and sketch.lower().endswith(".png"):
        from PySide6.QtGui import QPixmap
        from ui.widgets.multilang_help import resource_path
        pm = _fit(QPixmap(resource_path(f"{SKETCH_DIR}/{sketch}")), SKETCH_W, SKETCH_H, card.devicePixelRatioF())
        if pm is not None:
            img = QLabel()
            img.setPixmap(pm)
            img.setFixedSize(SKETCH_W, SKETCH_H)
            img.setAlignment(Qt.AlignCenter)
            lay.addWidget(img, 0, Qt.AlignTop)
            card.setMinimumHeight(SKETCH_H + 22)
    elif sketch:
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
        # left column: logo above search + versions; right column: subtitle +
        # flags in one slim row, the version with its tabs right below
        self.lbl_title = QLabel()  # the logo; plain text if the picture is missing
        self.lbl_title.setStyleSheet("font-size:20px; font-weight:700;")
        self._logo = logo_pixmap(210, 100, self.devicePixelRatioF())
        if self._logo is not None:
            self.lbl_title.setPixmap(self._logo)
        self.lbl_subtitle = QLabel()  # "What's new in TrippleT" next to the flags
        self.lbl_subtitle.setStyleSheet("font-size:13px; color:#666666; padding-left:20px;")
        top = QHBoxLayout()
        top.addWidget(self.lbl_subtitle, 0, Qt.AlignVCenter)
        flag_row, self._flag_buttons = build_flag_row(self.set_language, self)
        top.addLayout(flag_row, 1)

        body = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(self.lbl_title)
        self.lbl_versions = QLabel()
        self.lbl_versions.setStyleSheet("font-weight:700; color:#565656;")
        self.search = QLineEdit()
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(210)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self._apply_search)
        self.search.textChanged.connect(lambda _t: self._search_timer.start())
        left.addWidget(self.search)
        left.addWidget(self.lbl_versions)
        self._hits: List[Tuple[int, int]] = []
        self._group_heads: Dict[int, QWidget] = {}
        self._logged_query = ""
        self._row = 0
        self.lst = QListWidget()
        self.lst.setFixedWidth(210)
        self.lst.setStyleSheet(
            "QListWidget::item{padding:8px 6px; border-bottom:1px solid #eeeeee; color:#1a1a1a;}"
            "QListWidget::item:selected{background:#d8e7fa; color:#1a1a1a;}")
        self.lst.currentRowChanged.connect(self._on_row_changed)
        left.addWidget(self.lst, 1)
        body.addLayout(left)

        from ui.widgets.multilang_help import scroll_page
        self.scroll, self._page = scroll_page()  # search results (one list)
        self._release_view = QWidget()          # one version: title + a tab per section
        rv = QVBoxLayout(self._release_view)
        rv.setContentsMargins(20, 2, 8, 0)
        rv.setSpacing(8)
        from ui.widgets.multilang_help import heading
        self.lbl_release = heading("")
        self.lbl_release.setStyleSheet(self.lbl_release.styleSheet() + "font-size:18px;")
        rv.addWidget(self.lbl_release)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        from ui.theme import get_accent
        self.tabs.setStyleSheet(
            "QTabBar::tab{padding:6px 12px;}"
            f"QTabBar::tab:selected{{font-weight:700; border-bottom:3px solid {get_accent()};}}")
        rv.addWidget(self.tabs, 1)
        self.right = QStackedWidget()
        self.right.addWidget(self._release_view)
        self.right.addWidget(self.scroll)
        right_col = QVBoxLayout()
        right_col.addLayout(top)
        right_col.addWidget(self.right, 1)
        body.addLayout(right_col, 1)
        outer.addLayout(body, 1)

        row = QHBoxLayout()
        self.btn_pdf = QPushButton("PDF")
        self.btn_pdf.clicked.connect(self._save_pdf)
        row.addWidget(self.btn_pdf)
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
        if self._logo is None:
            self.lbl_title.setText(WINDOW_TITLE[lang])
        self.lbl_title.setToolTip(WINDOW_TITLE[lang])
        self.lbl_subtitle.setText(SUBTITLE[lang])
        self.lbl_versions.setText(VERSIONS_TITLE[lang])
        self.btn_close.setText(CLOSE[lang])
        self.btn_pdf.setToolTip(PDF_TOOLTIP[lang])
        self.search.setPlaceholderText(SEARCH_PLACEHOLDER[lang])
        self._flag_buttons[lang].setChecked(True)
        self._row = max(0, self.lst.currentRow())
        if self.search.text().strip():
            self._apply_search()
        else:
            self._fill_list()
            if self.lst.count():
                self._show_release(self.lst.currentRow(), keep_tab=True)

    def _fill_list(self) -> None:
        """Version list; while searching with hit count per version, versions
        without hits greyed out and not selectable."""
        lang = self._lang
        searching = bool(self.search.text().strip())
        counts: Dict[int, int] = {}
        for ri, _bi in self._hits:
            counts[ri] = counts.get(ri, 0) + 1
        self.lst.blockSignals(True)
        self.lst.clear()
        for ri, r in enumerate(RELEASES):
            v = release_version(r)
            text = f"{VERSION_LABEL[lang]} {v}\n{release_when(r, lang)}"
            if v in self._unseen:
                text += f"   {NEW_BADGE[lang]}"
            if searching and counts.get(ri):
                text += f"\n{counts[ri]} {HITS_LABEL[lang]}"
            it = QListWidgetItem(text)
            if v in self._unseen:
                f = it.font()
                f.setBold(True)
                it.setFont(f)
                it.setForeground(QColor("#1f6f33"))
            if searching and not counts.get(ri):
                it.setFlags(it.flags() & ~Qt.ItemIsEnabled & ~Qt.ItemIsSelectable)
                it.setForeground(QColor("#b0b0b0"))
            self.lst.addItem(it)
        if self.lst.count():
            self.lst.setCurrentRow(-1 if searching else min(self._row, self.lst.count() - 1))
        self.lst.blockSignals(False)
        self.btn_pdf.setEnabled(not searching and self.lst.currentRow() >= 0)

    def _save_pdf(self) -> None:
        from ui.whats_new_pdf import save_release_pdf_dialog
        if self.lst.currentRow() >= 0 and not self.search.text().strip():
            save_release_pdf_dialog(self, self.lst.currentRow(), self._lang)

    def _on_row_changed(self, idx: int) -> None:
        if self.search.text().strip():
            head = self._group_heads.get(idx)  # while searching: jump to that version's hits
            if head is not None:
                self.scroll.verticalScrollBar().setValue(head.y())
        elif idx >= 0:
            self._row = idx
            self._show_release(idx)

    def _clear_page(self) -> None:
        while self._page.count():
            item = self._page.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()  # deleteLater() alone leaves it visible until the next event loop
                w.setParent(None)
                w.deleteLater()
        self._group_heads = {}

    def _apply_search(self) -> None:
        import html
        from ui.widgets.multilang_help import heading, para
        q, lang = self.search.text().strip(), self._lang
        self._hits = search_features(q) if q else []
        self._fill_list()
        if not q:
            self._show_release(self.lst.currentRow())
            return
        self.right.setCurrentWidget(self.scroll)
        self._clear_page()
        if not self._hits:
            self._page.addWidget(para(SEARCH_NONE[lang].format(q=html.escape(q))))
        else:
            head = heading(SEARCH_RESULTS[lang].format(n=len(self._hits), q=html.escape(q)))
            head.setStyleSheet(head.styleSheet() + "font-size:18px;")
            self._page.addWidget(head)
            for ri, bi in self._hits:
                r = RELEASES[ri]
                if ri not in self._group_heads:
                    g = QLabel(f"{VERSION_LABEL[lang]} {release_version(r)}  ·  {release_when(r, lang)}")
                    g.setStyleSheet("font-weight:700; color:#565656; padding-top:10px;")
                    self._group_heads[ri] = g
                    self._page.addWidget(g)
                _, title, text, where, sketch = r["texts"][lang][bi]
                self._page.addWidget(feature_card(title, text, where, sketch, lang))
        self._page.addStretch(1)
        self.scroll.verticalScrollBar().setValue(0)
        self._logged_query = q

    def done(self, result: int) -> None:
        if self._logged_query:  # last search of this window, for Usage Stats -> Help
            try:
                from db.usage_log import log_usage_event
                log_usage_event("feature", "help_whatsnew_search" if self._hits else "help_whatsnew_noresult",
                                f"{self._logged_query[:200]} | hits={len(self._hits)}")
            except Exception:
                pass
        super().done(result)

    def _show_release(self, idx: int, keep_tab: bool = False) -> None:
        """One version: a tab per section (keep_tab: same tab position, e.g.
        after switching the language)."""
        from ui.widgets.multilang_help import render_block, scroll_page
        self.right.setCurrentWidget(self._release_view)
        tab = self.tabs.currentIndex() if keep_tab else 0
        while self.tabs.count():
            w = self.tabs.widget(0)
            self.tabs.removeTab(0)
            w.deleteLater()
        if not (0 <= idx < len(RELEASES)):
            self.lbl_release.setText("")
            return
        r, lang = RELEASES[idx], self._lang
        self.lbl_release.setText(f"{VERSION_LABEL[lang]} {release_version(r)}  ·  {release_when(r, lang)}")
        for title, blocks in release_sections(r, lang):
            scroll, page = scroll_page()
            page.setContentsMargins(4, 10, 16, 12)
            n = 0
            for block in blocks:
                if block[0] == "feature":
                    _, ftitle, text, where, sketch = block
                    page.addWidget(feature_card(ftitle, text, where, sketch, lang))
                    n += 1
                else:
                    render_block(page, block)
            page.addStretch(1)
            label = (title or VERSION_LABEL[lang]).replace("&", "&&")
            self.tabs.addTab(scroll, f"{label} ({n})" if n else label)
        self.tabs.tabBar().setVisible(self.tabs.count() > 1)
        if self.tabs.count():
            self.tabs.setCurrentIndex(min(max(tab, 0), self.tabs.count() - 1))


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
