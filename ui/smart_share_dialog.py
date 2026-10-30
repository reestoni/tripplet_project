# ui/smart_share_dialog.py
"""Share a saved Smart Chart view (Etappe 6, Nutzerentscheid 2026-10-30):
only its creator opens this. Everybody (view), single people and user groups
(tblAccessRight), each "Can view" or "Can edit". Rules and storage in
db/smart_chart_views.py."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView,
                               QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from db import smart_chart_views as views

RIGHTS = (("view", "Can view"), ("edit", "Can view and edit"))


class ShareDialog(QDialog):
    def __init__(self, view: Dict[str, Any], parent=None, targets: Optional[Dict[str, List[Dict[str, Any]]]] = None,
                 shares: Optional[List[Dict[str, Any]]] = None):
        super().__init__(parent)
        self.view = view
        self.setWindowTitle(f"Share “{view.get('Name') or 'view'}”")
        self.setMinimumWidth(520)
        self.targets = targets if targets is not None else views.share_targets()
        self.entries: List[Dict[str, Any]] = []
        for sh in (shares if shares is not None else views.get_shares(int(view["ID"]))):
            self.entries.append({"UserID": sh.get("UserID"), "AccessRightID": sh.get("AccessRightID"),
                                 "CanEdit": bool(int(sh.get("CanEdit") or 0)), "Name": sh.get("Name") or "?"})

        v = QVBoxLayout(self)
        self.chk_all = QCheckBox("Everybody can view it")
        self.chk_all.setChecked(bool(int(view.get("IsShared") or 0)))
        v.addWidget(self.chk_all)

        v.addWidget(QLabel("<b>People and groups</b>"))
        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(["Who", "Right", ""])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setSelectionMode(QTableWidget.NoSelection)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        hh = self.tbl.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        v.addWidget(self.tbl)

        add = QHBoxLayout()
        self.cmb_who = QComboBox()
        self.cmb_who.setMinimumWidth(240)
        add.addWidget(self.cmb_who, 1)
        self.cmb_right = QComboBox()
        for key, label in RIGHTS:
            self.cmb_right.addItem(label, key)
        add.addWidget(self.cmb_right)
        self.btn_add = QPushButton("Add")
        self.btn_add.clicked.connect(self._add)
        add.addWidget(self.btn_add)
        v.addLayout(add)

        hint = QLabel("Groups are the access rights (read, write, admin, superuser) - a group share holds for "
                      "everybody with exactly that right. <i>Can view and edit</i> lets them save changes in "
                      "Smart Chart; only you can share or delete it.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#5A6460; font-size:12px;")
        v.addWidget(hint)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self._render()

    # ── list ────────────────────────────────────────────────────────────
    @staticmethod
    def _key(e: Dict[str, Any]):
        return ("u", int(e["UserID"])) if e.get("UserID") is not None else ("g", int(e["AccessRightID"]))

    def _render(self) -> None:
        self.tbl.setRowCount(len(self.entries))
        for i, e in enumerate(self.entries):
            kind = "Person" if e.get("UserID") is not None else "Group"
            it = QTableWidgetItem(f"{e['Name']}  ·  {kind}")
            self.tbl.setItem(i, 0, it)
            cmb = QComboBox()
            for key, label in RIGHTS:
                cmb.addItem(label, key)
            cmb.setCurrentIndex(1 if e.get("CanEdit") else 0)
            cmb.currentIndexChanged.connect(lambda idx, e=e: e.__setitem__("CanEdit", idx == 1))
            self.tbl.setCellWidget(i, 1, cmb)
            rm = QPushButton("Remove")
            rm.clicked.connect(lambda _=False, e=e: self._remove(e))
            self.tbl.setCellWidget(i, 2, rm)
        taken = {self._key(e) for e in self.entries}
        self.cmb_who.clear()
        for g in self.targets.get("groups") or []:
            if ("g", int(g["ID"])) not in taken:
                self.cmb_who.addItem(f"Group: {g['Name']}", ("g", int(g["ID"]), g["Name"]))
        for p in self.targets.get("people") or []:
            if ("u", int(p["ID"])) not in taken:
                self.cmb_who.addItem(str(p["Name"]), ("u", int(p["ID"]), p["Name"]))
        self.btn_add.setEnabled(self.cmb_who.count() > 0)

    def _add(self) -> None:
        data = self.cmb_who.currentData()
        if not data:
            return
        kind, ident, name = data
        self.entries.append({"UserID": ident if kind == "u" else None, "AccessRightID": ident if kind == "g" else None,
                             "CanEdit": self.cmb_right.currentData() == "edit", "Name": name})
        self._render()

    def _remove(self, e: Dict[str, Any]) -> None:
        self.entries = [x for x in self.entries if x is not e]
        self._render()

    def values(self):
        return self.chk_all.isChecked(), [{"UserID": e.get("UserID"), "AccessRightID": e.get("AccessRightID"),
                                           "CanEdit": bool(e.get("CanEdit"))} for e in self.entries]


def share_view(view: Dict[str, Any], parent=None) -> bool:
    """Open the dialog and save. True when saved."""
    from PySide6.QtWidgets import QMessageBox
    if not views.can_share(view):
        QMessageBox.information(parent, "Share", "Only the person who created this view can share it.")
        return False
    if not views.shares_available():
        QMessageBox.information(parent, "Share", "Sharing with single people and groups is not available in this "
                                                 "database yet - only “Share with everybody” when saving.")
        return False
    dlg = ShareDialog(view, parent)
    if dlg.exec() != QDialog.Accepted:
        return False
    everybody, entries = dlg.values()
    try:
        views.set_shares(int(view["ID"]), everybody, entries)
    except Exception as e:
        from ui.widgets.friendly_error import show_error
        show_error(parent, "Share", "The sharing could not be saved.", e)
        return False
    view["IsShared"] = int(everybody)
    try:
        from db.usage_log import log_usage_event
        log_usage_event("feature", "smart_chart_share", f"{len(entries)} entries" + (" + all" if everybody else ""))
    except Exception:
        pass
    return True
