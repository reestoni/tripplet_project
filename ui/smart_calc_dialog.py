# ui/smart_calc_dialog.py
"""Smart Chart dashboard: create / change a calculated field (Nutzerwunsch
2026-10-30, "wie Power BI"). Formula in plain names, e.g.
    [Intermingling Points (FP/m)] / [Air Consumption (m3/h)]
Fields are inserted from a searchable list; the preview shows how many trials
get a value and min / average / max. Data and rules: db/formula.py.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout,
)

from db import formula as fm
from db import trial_explorer as te


class CalcFieldDialog(QDialog):
    def __init__(self, ds: te.TrialDataset, existing: Optional[Dict[str, Any]], key: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Change calculated field" if existing else "New calculated field")
        self.resize(760, 520)
        self.ds, self.key = ds, key
        self.result_def: Optional[Dict[str, Any]] = None
        self.deleted = False
        self._fields = [f for f in ds.fields.values() if f.kind == "num" and f.key != key]

        root = QHBoxLayout(self)
        left = QVBoxLayout()
        form = QFormLayout()
        self.txt_name = QLineEdit((existing or {}).get("name") or "")
        self.txt_name.setPlaceholderText("e.g. Efficiency")
        form.addRow("Name", self.txt_name)
        self.txt_unit = QLineEdit((existing or {}).get("unit") or "")
        self.txt_unit.setPlaceholderText("optional, e.g. FP/m per m³/h")
        form.addRow("Unit", self.txt_unit)
        left.addLayout(form)
        left.addWidget(QLabel("Formula"))
        self.txt = QPlainTextEdit(fm.to_display((existing or {}).get("formula") or "", ds.fields))
        self.txt.setPlaceholderText("[Intermingling Points (FP/m)] / [Air Consumption (m3/h)]")
        self.txt.setFixedHeight(90)
        self.txt.textChanged.connect(lambda: self._timer.start())
        left.addWidget(self.txt)
        ops = QGridLayout()
        for i, (lab, ins) in enumerate((("+", " + "), ("−", " - "), ("×", " * "), ("÷", " / "), ("(", "("), (")", ")"),
                                        ("^", "^"), ("abs", "abs("), ("sqrt", "sqrt("), ("log10", "log10("),
                                        ("min", "min("), ("max", "max("))):
            b = QPushButton(lab)
            b.setFixedHeight(28)
            b.clicked.connect(lambda _=False, t=ins: self._insert(t))
            ops.addWidget(b, i // 6, i % 6)
        left.addLayout(ops)
        self.lbl_preview = QLabel("")
        self.lbl_preview.setWordWrap(True)
        self.lbl_preview.setStyleSheet("background:#F3EFFA;border:1px solid #D6CCEB;border-radius:6px;padding:8px;")
        left.addWidget(self.lbl_preview)
        hint = QLabel("Fields in [square brackets]. Calculated per trial; trials where a used field has no "
                      "value get no result. Saved with this dashboard.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#5A6460;font-size:12px;")
        left.addWidget(hint)
        left.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.btn_ok = bb.button(QDialogButtonBox.Ok)
        if existing:
            b_del = bb.addButton("Delete", QDialogButtonBox.DestructiveRole)
            b_del.clicked.connect(self._delete)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        left.addWidget(bb)
        root.addLayout(left, 3)

        right = QVBoxLayout()
        right.addWidget(QLabel("<b>Insert a field</b> (double-click)"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search a number field…")
        self.txt_search.textChanged.connect(self._fill)
        right.addWidget(self.txt_search)
        self.lst = QListWidget()
        self.lst.itemDoubleClicked.connect(lambda it: self._insert(f"[{it.data(Qt.UserRole)}]"))
        right.addWidget(self.lst, 1)
        root.addLayout(right, 2)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._preview)
        self._fill()
        self._preview()

    def _fill(self) -> None:
        q = self.txt_search.text().strip().lower()
        self.lst.clear()
        names = fm.display_names(self.ds.fields.values())
        for f in self._fields:
            if q and q not in f.label.lower() and q not in f.group.lower():
                continue
            it = QListWidgetItem(f"{f.label}    · {f.group}")
            it.setData(Qt.UserRole, names.get(f.key, f.label))
            self.lst.addItem(it)

    def _insert(self, text: str) -> None:
        self.txt.insertPlainText(text)
        self.txt.setFocus()

    def _compile(self):
        stored = fm.from_display(self.txt.toPlainText(), self.ds.fields.values())
        compiled, keys = fm.compile_formula(stored, self.ds.fields, exclude=self.key)
        return stored, compiled, keys

    def _preview(self) -> None:
        try:
            stored, compiled, keys = self._compile()
        except fm.FormulaError as e:
            self.lbl_preview.setText(f"<span style='color:#C62828'>{e}</span>")
            self.btn_ok.setEnabled(False)
            return
        vals = []
        for t in self.ds.trials:
            r = fm.evaluate(compiled, {k: _num(self.ds.value(k, t.id)) for k in keys})
            if r is not None:
                vals.append(r)
        if not vals:
            self.lbl_preview.setText("The formula is fine, but no trial has values for all its fields.")
        else:
            avg = sum(vals) / len(vals)
            self.lbl_preview.setText(f"<b>{len(vals):,} trials</b> get a value · min {fmt(min(vals))} · "
                                     f"average {fmt(avg)} · max {fmt(max(vals))}".replace(",", "'"))
        self.btn_ok.setEnabled(True)

    def _accept(self) -> None:
        name = self.txt_name.text().strip()
        if not name:
            self.txt_name.setFocus()
            return
        try:
            stored, _c, _k = self._compile()
        except fm.FormulaError as e:
            QMessageBox.information(self, "Calculated field", str(e))
            return
        self.result_def = {"key": self.key, "name": name, "unit": self.txt_unit.text().strip(), "formula": stored}
        self.accept()

    def _delete(self) -> None:
        if QMessageBox.question(self, "Delete calculated field",
                                "Delete this calculated field? Visuals that use it show nothing for it any more.",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            self.deleted = True
            self.accept()


def _num(v):
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def fmt(x: float) -> str:
    from db.fairness import _fmt
    return _fmt(x)
