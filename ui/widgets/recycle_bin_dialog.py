"""recycle_bin_dialog.py - Sidebar -> Superuser -> "Recycle Bin": deleted
trial series, restorable for db.recycle_bin.RETENTION_DAYS days."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from db import recycle_bin


class RecycleBinDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recycle Bin")
        self.resize(900, 480)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            f"Deleted trial series can be restored here for {recycle_bin.RETENTION_DAYS} days, "
            "with all trials, plies, lab values, images/PDF entries and notes."))
        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(["Deleted", "By", "What", "Name", "Contents"])
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl.verticalHeader().setVisible(False)
        hh = self.tbl.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        self.tbl.itemSelectionChanged.connect(self._update_buttons)
        lay.addWidget(self.tbl, 1)
        row = QHBoxLayout()
        self.btn_restore = QPushButton("Restore")
        self.btn_restore.clicked.connect(self._restore)
        row.addWidget(self.btn_restore)
        self.btn_delete = QPushButton("Delete permanently")
        self.btn_delete.clicked.connect(self._delete)
        row.addWidget(self.btn_delete)
        row.addStretch(1)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        row.addWidget(btn_close)
        lay.addLayout(row)
        self._entries = []
        self._reload()

    def _reload(self) -> None:
        if not recycle_bin.available():
            self.tbl.setRowCount(0)
            self.btn_restore.setEnabled(False)
            self.btn_delete.setEnabled(False)
            QMessageBox.information(self, "Recycle Bin",
                                    "The recycle bin is not set up in this database (or you are offline).")
            return
        try:
            recycle_bin.purge_expired()
        except Exception:
            pass
        self._entries = recycle_bin.list_entries()
        self.tbl.setRowCount(len(self._entries))
        for i, e in enumerate(self._entries):
            when = e.get("DeletedAt")
            vals = [when.strftime("%Y-%m-%d %H:%M") if hasattr(when, "strftime") else str(when or ""),
                    e.get("UserName") or "", e.get("ObjectType") or "", e.get("Label") or "",
                    e.get("Summary") or ""]
            for j, v in enumerate(vals):
                self.tbl.setItem(i, j, QTableWidgetItem(str(v)))
        self._update_buttons()

    def _current(self):
        r = self.tbl.currentRow()
        return self._entries[r] if 0 <= r < len(self._entries) and self.tbl.selectedItems() else None

    def _update_buttons(self) -> None:
        on = self._current() is not None
        self.btn_restore.setEnabled(on)
        self.btn_delete.setEnabled(on)

    def _restore(self) -> None:
        e = self._current()
        if e is None:
            return
        if QMessageBox.question(self, "Restore", f"Restore \"{e.get('Label') or e.get('ObjectID')}\"?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes) != QMessageBox.Yes:
            return
        try:
            label = recycle_bin.restore(int(e["ID"]))
        except Exception as ex:
            QMessageBox.warning(self, "Restore", f"Could not restore:\n\n{ex}")
            return
        refresh_series_lists()
        QMessageBox.information(self, "Restore", f"\"{label}\" is back.")
        self._reload()

    def _delete(self) -> None:
        e = self._current()
        if e is None:
            return
        if QMessageBox.warning(self, "Delete permanently",
                               f"Delete \"{e.get('Label') or e.get('ObjectID')}\" permanently?\n"
                               "It cannot be restored afterwards.",
                               QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel) != QMessageBox.Yes:
            return
        recycle_bin.delete_permanently(int(e["ID"]))
        self._reload()


def refresh_series_lists() -> int:
    """Reloads every open Backlog and All Experiments screen (also extra
    tabs), so a restored series shows up right away. Returns the number."""
    from PySide6.QtWidgets import QApplication
    from ui.screen_backlog import BacklogScreen
    from ui.screen_all_experiments import AllExperimentsScreen
    n = 0
    for w in QApplication.allWidgets():
        try:
            if isinstance(w, BacklogScreen):
                w.reload_all()
                n += 1
            elif isinstance(w, AllExperimentsScreen):
                w._load_data(w._filter_map.get(w._active_filter, None))
                n += 1
        except RuntimeError:
            continue  # widget already deleted
        except Exception:
            pass
    return n


def open_recycle_bin(parent=None) -> None:
    RecycleBinDialog(parent).exec()
