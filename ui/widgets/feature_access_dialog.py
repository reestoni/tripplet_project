# ui/widgets/feature_access_dialog.py
"""Manage User -> "Access…" (superuser only, Nutzerwunsch 2026-10-30): which
tools and screens a group or a single person may use.

Rows = tools/screens (db/feature_access.FEATURES, by sidebar section),
columns = the groups (read, write, admin) and then every active user who is
not a superuser. A click on a cell cycles:
    group column:  default (grey, as before) -> Yes (allowed) -> No (blocked) -> default
    person column: as the group (grey)       -> allowed -> blocked -> as the group
Grey cells show what applies without a setting. Superusers always have
everything and are not listed.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QLabel, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from db import feature_access as fa

GREEN, RED, GREY, SECTION_BG = "#1F7A3A", "#C62828", "#9AA19C", "#EEF1ED"


class FeatureAccessDialog(QDialog):
    def __init__(self, parent=None, data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle("Access to tools and screens")
        self.resize(1100, 720)
        data = data if data is not None else fa.load_all()
        self.groups = [g for g in data["groups"] if int(g.get("Level") or 0) < fa.SUPERUSER_LEVEL]
        self.level_of = {int(g["ID"]): int(g.get("Level") or 0) for g in data["groups"]}
        self.users = [u for u in data["users"]
                      if self.level_of.get(int(u["GroupID"]) if u.get("GroupID") is not None else -1, 0)
                      < fa.SUPERUSER_LEVEL]
        self.group_rules: Dict[int, Dict[str, bool]] = {int(k): dict(v) for k, v in data["group_rules"].items()}
        self.user_rules: Dict[int, Dict[str, bool]] = {int(k): dict(v) for k, v in data["user_rules"].items()}
        self.columns: List[Dict[str, Any]] = (
            [{"kind": "g", "id": int(g["ID"]), "name": f"Group\n{g['Name']}"} for g in self.groups]
            + [{"kind": "u", "id": int(u["ID"]), "name": str(u["Name"]).replace(" ", "\n", 1),
                "group": int(u["GroupID"]) if u.get("GroupID") is not None else None} for u in self.users])
        self.rows: List[Optional[fa.Feature]] = []
        last = None
        for f in fa.FEATURES:
            if f.section != last:
                self.rows.append(None)          # section heading
                last = f.section
            self.rows.append(f)

        v = QVBoxLayout(self)
        intro = QLabel("Click a cell to switch: <b style='color:#1F7A3A'>Yes</b> = allowed · "
                       "<b style='color:#C62828'>No</b> = blocked · <span style='color:#9AA19C'>grey = no setting "
                       "(groups: as before, people: as their group)</span>. A setting for a person wins over the "
                       "group. Superusers always have everything. Blocked tools disappear from the sidebar - the "
                       "change applies from the next login.")
        intro.setWordWrap(True)
        v.addWidget(intro)
        self.tbl = QTableWidget(len(self.rows), len(self.columns))
        self.tbl.setHorizontalHeaderLabels([c["name"] for c in self.columns])
        self.tbl.setVerticalHeaderLabels([f.label if f else "" for f in self.rows])
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.setSelectionMode(QTableWidget.NoSelection)
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setMinimumSectionSize(64)
        self.tbl.verticalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.tbl.cellClicked.connect(self._cycle)
        v.addWidget(self.tbl, 1)
        row = QHBoxLayout()
        btn_reset = QPushButton("Reset all to default")
        btn_reset.setToolTip("Remove every setting - everybody gets what his group had before")
        btn_reset.clicked.connect(self._reset)
        row.addWidget(btn_reset)
        row.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        row.addWidget(bb)
        v.addLayout(row)
        self._render()

    # ── state ───────────────────────────────────────────────────────────
    def _rules(self, col: Dict[str, Any]) -> Dict[str, bool]:
        store = self.group_rules if col["kind"] == "g" else self.user_rules
        return store.setdefault(col["id"], {})

    def effective(self, col: Dict[str, Any], key: str) -> bool:
        """What applies in this cell (with the settings in the dialog)."""
        if col["kind"] == "g":
            return fa.decide(key, self.level_of.get(col["id"], 0), {}, self.group_rules.get(col["id"], {}))
        grp = col.get("group")
        return fa.decide(key, self.level_of.get(grp, 0) if grp is not None else 0,
                         self.user_rules.get(col["id"], {}), self.group_rules.get(grp, {}) if grp is not None else {})

    def _cycle(self, r: int, c: int) -> None:
        f = self.rows[r]
        if f is None:
            return
        rules = self._rules(self.columns[c])
        cur = rules.get(f.key)
        if cur is None:
            rules[f.key] = True
        elif cur:
            rules[f.key] = False
        else:
            rules.pop(f.key)
        self._render()

    def _reset(self) -> None:
        self.group_rules.clear()
        self.user_rules.clear()
        self._render()

    def _render(self) -> None:
        bold = QFont()
        bold.setBold(True)
        for r, f in enumerate(self.rows):
            for c, col in enumerate(self.columns):
                if f is None:
                    it = QTableWidgetItem("")
                    it.setBackground(QBrush(QColor(SECTION_BG)))
                    it.setFlags(Qt.NoItemFlags)
                    self.tbl.setItem(r, c, it)
                    continue
                setting = (self.group_rules if col["kind"] == "g" else self.user_rules).get(col["id"], {}).get(f.key)
                eff = self.effective(col, f.key)
                it = QTableWidgetItem(("Yes" if eff else "No") if setting is not None else ("yes" if eff else "–"))
                it.setTextAlignment(Qt.AlignCenter)
                if setting is None:
                    it.setForeground(QBrush(QColor(GREY)))
                    it.setToolTip(("Default: " if col["kind"] == "g" else "As the group: ")
                                  + ("allowed" if eff else "not allowed") + " - click to set")
                else:
                    it.setForeground(QBrush(QColor(GREEN if setting else RED)))
                    it.setFont(bold)
                    it.setToolTip(("Allowed" if setting else "Blocked") + " - click to change")
                self.tbl.setItem(r, c, it)
        for r, f in enumerate(self.rows):
            if f is None:
                head = QTableWidgetItem(self.rows[r + 1].section.upper())
                head.setFont(bold)
                head.setForeground(QBrush(QColor(GREEN)))
                self.tbl.setVerticalHeaderItem(r, head)

    def values(self):
        clean = lambda d: {k: {kk: vv for kk, vv in v.items() if vv is not None} for k, v in d.items() if v}
        return clean(self.group_rules), clean(self.user_rules)


def open_feature_access(parent=None) -> bool:
    from PySide6.QtWidgets import QMessageBox
    import app_meta
    if int(app_meta.access_level() or 0) < fa.SUPERUSER_LEVEL:
        QMessageBox.information(parent, "Access", "Only a superuser can change who may use which tools.")
        return False
    if not fa.available():
        QMessageBox.information(parent, "Access", "Switching tools on and off is not available in this "
                                                  "database yet.")
        return False
    try:
        dlg = FeatureAccessDialog(parent)
    except Exception as e:
        from ui.widgets.friendly_error import show_error
        show_error(parent, "Access", "The access settings could not be loaded.", e)
        return False
    if dlg.exec() != QDialog.Accepted:
        return False
    try:
        fa.save_all(*dlg.values())
    except Exception as e:
        from ui.widgets.friendly_error import show_error
        show_error(parent, "Access", "The access settings could not be saved.", e)
        return False
    try:
        from db.usage_log import log_usage_event
        log_usage_event("feature", "feature_access_save", "")
    except Exception:
        pass
    return True
