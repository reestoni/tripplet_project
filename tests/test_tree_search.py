"""Search field above the group trees in Create Experiment (ui/widgets/tree_search.py)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem

from ui.widgets.tree_search import TreeSearch, filter_tree

_app = QApplication.instance() or QApplication([])


def _tree():
    t = QTreeWidget()
    t.setColumnCount(2)
    for label, kids in (("1 | Standard Yarn", [("PES 167f48", ""), ("PA6 78f68", "")]),
                        ("2 | Non Standard Yarn", [("PA6 POY 52/44f36", ""), ("PP 300", "dev-x")]),
                        ("3 | Customer", [])):
        top = QTreeWidgetItem([label, ""])
        t.addTopLevelItem(top)
        for name, extra in kids:
            top.addChild(QTreeWidgetItem([name, extra]))
    t.topLevelItem(0).setExpanded(True)
    return t


def _visible(t):
    return [t.topLevelItem(i).child(j).text(0)
            for i in range(t.topLevelItemCount()) if not t.topLevelItem(i).isHidden()
            for j in range(t.topLevelItem(i).childCount()) if not t.topLevelItem(i).child(j).isHidden()]


def test_search_all_groups_and_words():
    t = _tree()
    assert filter_tree(t, "pa6") == 2
    assert _visible(t) == ["PA6 78f68", "PA6 POY 52/44f36"]
    assert t.topLevelItem(1).isExpanded() and t.topLevelItem(2).isHidden()
    assert filter_tree(t, "PA6  44") == 1          # all words, case-insensitive
    assert filter_tree(t, "nothing") == 0


def test_extra_columns_and_group_label():
    t = _tree()
    assert filter_tree(t, "dev-x", columns=(0,)) == 0
    assert filter_tree(t, "dev-x", columns=(0, 1)) == 1
    assert filter_tree(t, "non standard") == 2      # group label shows all its children


def test_clear_restores_expansion_and_enter_selects():
    t = _tree()
    s = TreeSearch(t, columns=(0,))
    s.edit.setText("pp")
    assert _visible(t) == ["PP 300"]
    s.edit.setText("")
    assert [t.topLevelItem(i).isExpanded() for i in range(3)] == [True, False, False]
    assert len(_visible(t)) == 4
    s.edit.setText("pes")
    s.select_first()
    assert t.selectedItems()[0].text(0) == "PES 167f48"
    s.edit.setText("pp")                            # selected item hidden -> selection cleared
    assert t.selectedItems() == []
