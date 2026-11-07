# ui/widgets/tree_search.py
"""Search field above a two-level group tree (Nutzerwunsch 2026-11-06).

Used by Create Experiment for the Material tree (groups -> yarns) and the
Jet tree (groups -> jets). Searches across ALL groups:

* every word of the query must appear (case-insensitive) in one of the
  searched columns of the child, or in the group label;
* groups without a match are hidden, groups with a match are expanded;
* a group whose label matches shows all its children;
* clearing the field restores the expansion the tree had before the search;
* Enter selects the first match.

    search = TreeSearch(self.treeJet, columns=(0, 5), placeholder="Search jets…")
    layout.addWidget(search.edit)
    ... after reloading the tree: search.reapply()
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit, QTreeWidget, QTreeWidgetItem


def _tokens(text: str) -> List[str]:
    return [t for t in (text or "").lower().split() if t]


def _matches(texts: Iterable[str], tokens: Sequence[str]) -> bool:
    hay = " ".join(t.lower() for t in texts if t)
    return all(tok in hay for tok in tokens)


def filter_tree(tree: QTreeWidget, text: str, columns: Sequence[int] = (0,)) -> int:
    """Hides non-matching children/groups. Returns the number of visible
    matching children. Empty text shows everything (expansion untouched)."""
    tokens = _tokens(text)
    total = 0
    for i in range(tree.topLevelItemCount()):
        top = tree.topLevelItem(i)
        if not tokens:
            top.setHidden(False)
            for j in range(top.childCount()):
                top.child(j).setHidden(False)
            continue
        group_hit = _matches([top.text(0)], tokens)
        shown = 0
        for j in range(top.childCount()):
            child = top.child(j)
            hit = group_hit or _matches([top.text(0)] + [child.text(c) for c in columns], tokens)
            child.setHidden(not hit)
            shown += int(hit)
        top.setHidden(shown == 0)
        if shown:
            top.setExpanded(True)
        total += shown
    return total


class TreeSearch:
    """QLineEdit wired to filter_tree() with expansion save/restore."""

    def __init__(self, tree: QTreeWidget, columns: Sequence[int] = (0,),
                 placeholder: str = "Search…", parent=None):
        self.tree = tree
        self.columns = tuple(columns)
        self.edit = QLineEdit(parent)
        self.edit.setPlaceholderText(placeholder)
        self.edit.setClearButtonEnabled(True)
        self.edit.setToolTip("Searches all groups. Several words: all must match. "
                             "Enter selects the first hit, Esc clears.")
        self._saved: Optional[Dict[str, bool]] = None
        self.edit.textChanged.connect(self._on_text)
        self.edit.returnPressed.connect(self.select_first)
        _orig_key = self.edit.keyPressEvent

        def _key(ev, _orig=_orig_key):
            if ev.key() == Qt.Key_Escape and self.edit.text():
                self.edit.clear()
                return
            _orig(ev)
        self.edit.keyPressEvent = _key

    # expansion state is keyed by group label (items are rebuilt on reload)
    def _snapshot(self) -> Dict[str, bool]:
        return {self.tree.topLevelItem(i).text(0): self.tree.topLevelItem(i).isExpanded()
                for i in range(self.tree.topLevelItemCount())}

    def _restore(self) -> None:
        if self._saved is None:
            return
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            if top.text(0) in self._saved:
                top.setExpanded(self._saved[top.text(0)])
        self._saved = None

    def _on_text(self, text: str) -> None:
        if _tokens(text):
            if self._saved is None:
                self._saved = self._snapshot()
            filter_tree(self.tree, text, self.columns)
            sel = self.tree.selectedItems()
            if sel and sel[0].isHidden():
                self.tree.clearSelection()
        else:
            filter_tree(self.tree, "", self.columns)
            self._restore()
            sel = self.tree.selectedItems()
            if sel:
                self.tree.scrollToItem(sel[0])

    def reapply(self) -> None:
        """Call after the tree was rebuilt (expansion of the new items is
        the default one, so it becomes the state to restore later)."""
        self._saved = None
        if _tokens(self.edit.text()):
            self._on_text(self.edit.text())

    def first_match(self) -> Optional[QTreeWidgetItem]:
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            if top.isHidden():
                continue
            for j in range(top.childCount()):
                if not top.child(j).isHidden():
                    return top.child(j)
        return None

    def select_first(self) -> None:
        item = self.first_match()
        if item is None:
            return
        self.tree.setCurrentItem(item)
        item.setSelected(True)
        self.tree.scrollToItem(item)
        self.tree.setFocus()

    def setEnabled(self, on: bool) -> None:
        self.edit.setEnabled(on)
