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

from db.connection import fetch_all, table_exists


def get_available_spools(yarn_id: int, include_spool_id: Optional[int] = None) -> List[Dict]:
    """Spulen desselben Garns, die am Lager sind (Status='in stock', WeightKg>0).
    `include_spool_id` wird immer mit zurückgegeben, auch falls nicht mehr
    am Lager (z.B. bestehende Zuordnung, die man sich beim Bearbeiten
    weiterhin anschauen koennen soll)."""
    if not table_exists("tblYarnSpool") or not yarn_id:
        return []
    rows = fetch_all(
        "SELECT [ID], [Charge], [WeightKg], [Location], [Status] "
        "FROM tblYarnSpool WHERE [YarnID] = ? AND "
        "(([Status] = 'in stock' AND [WeightKg] > 0)" +
        (" OR [ID] = ?" if include_spool_id else "") + ") "
        "ORDER BY [Charge], [ID]",
        [yarn_id] + ([include_spool_id] if include_spool_id else []),
    )
    return rows


def spool_label(row: Dict) -> str:
    charge = row.get("Charge") or "–"
    weight = row.get("WeightKg")
    loc = row.get("Location") or "–"
    w_txt = f"{float(weight):.2f} kg" if weight is not None else "?"
    suffix = "" if row.get("Status") == "in stock" else "  (discarded)"
    return f"#{row['ID']} — Batch {charge} — {w_txt} — {loc}{suffix}"


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