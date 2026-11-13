# ui/widgets/spool_picker.py
"""Kleiner, wiederverwendbarer Dialog zur Auswahl einer physischen Spule
(tblYarnSpool) fuer ein Ply/Material in tbltrialsettings.

Nur Spulen desselben Garns UND mit Status='in stock' UND WeightKg>0 sind
waehlbar - ausser der aktuell zugewiesenen Spule (falls vorhanden), die
immer mit angezeigt wird, auch wenn sie inzwischen ausgebucht wurde (sonst
wuerde eine bestehende Zuordnung beim Bearbeiten "unsichtbar" werden).
"""
from typing import Optional, List, Dict

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QLabel, QDialogButtonBox,
)

# get_available_spools / spool_label: db/yarn_spools.py (Qt-free, shared with the web app)
from db.yarn_spools import get_available_spools, spool_label  # noqa: F401


class SpoolPickerDialog(QDialog):
    """Zeigt eine Dropdown-Auswahl der verfuegbaren Spulen fuer ein Garn.
    Ist keine Spule am Lager, wird ein gelber Hinweis angezeigt, die
    Auswahl bleibt aber optional (Skip moeglich)."""

    def __init__(self, yarn_id: int, yarn_name: str, current_spool_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select spool")
        self.setMinimumWidth(420)

        root = QVBoxLayout(self)
        form = QFormLayout()

        rows = get_available_spools(yarn_id, current_spool_id)
        self.cmb = QComboBox()
        self.cmb.addItem("— No spool assigned —", None)
        selected_idx = 0
        for i, r in enumerate(rows, start=1):
            self.cmb.addItem(spool_label(r), r["ID"])
            if current_spool_id is not None and r["ID"] == current_spool_id:
                selected_idx = i
        self.cmb.setCurrentIndex(selected_idx)
        form.addRow(f"Spool ({yarn_name})", self.cmb)
        root.addLayout(form)

        in_stock_rows = [r for r in rows if r.get("Status") == "in stock"]
        if not in_stock_rows:
            warn = QLabel("⚠ No spools currently in stock for this yarn.")
            warn.setStyleSheet(
                "background: #FFF3CD; color: #7A5B00; padding: 6px 10px; border-radius: 4px;")
            warn.setWordWrap(True)
            root.addWidget(warn)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def selected_spool_id(self) -> Optional[int]:
        return self.cmb.currentData()