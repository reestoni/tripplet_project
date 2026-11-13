# ui/widgets/label_printing.py
"""Gemeinsame Infrastruktur fuer Label-Druck (PDF-Erzeugung auf Etikettenboegen).

Wird sowohl von screen_yarn_stock.py (Spulen-Labels) als auch von
screen_show_experiment.py (Trial-Labels) genutzt. Templates werden per
`Name` in tblLabelTemplate unterschieden (z.B. 'Default' fuer Spulen,
'TrialLabel' fuer Versuchsnummern) - unterschiedliche Bogenformate,
unabhaengig voneinander speicherbar.

Wichtige Lessons aus der Entwicklung (siehe Kommentare im Code):
- QR-Module IMMER ueber page.new_shape() batchen, nie einzelne draw_rect()-
  Aufrufe pro Modul (sonst Minuten statt Millisekunden fuer wenige Labels).
- Text IMMER an die tatsaechlich verfuegbare Zellenhoehe anpassen (skalieren),
  nie fixe mm-Offsets annehmen - sonst laeuft der Text bei manchen Inhalten
  (z.B. 2-zeiliger Titel) ueber die Zelle bzw. bei der letzten Zeile eines
  Bogens ueber die Seite hinaus.
- Bei zu vielen Items fuer einen Bogen: weitere Seiten anhaengen statt
  stillschweigend abzubrechen.
"""
from typing import List, Dict, Optional, Callable, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame, QPushButton,
    QSpinBox, QDoubleSpinBox, QFormLayout, QDialogButtonBox, QWidget, QMessageBox,
)

from db.connection import fetch_all, execute, table_exists
from ui.widgets.friendly_error import show_error

# Templates, text fitting, QR, sheet layout: db/label_sheets.py (Qt-free,
# shared with the web app) - re-exported here unchanged.
from db.label_sheets import (  # noqa: E402,F401
    DEFAULT_TEMPLATE, LABEL_TEMPLATE_TABLE, MM, TEMPLATE_FIELDS, draw_qr, fit_text, fitz,
    generate_label_sheet_pdf, label_sheet_pdf_bytes, load_label_template, qrcode, save_label_template,
    wrap_text_lines,
)


class PrintLabelsDialog(QDialog):
    """Bogen-Geometrie editieren (benanntes Template) + Start-Zelle auf dem
    (evtl. teilweise benutzten) Bogen anklicken, dann PDF erzeugen.

    `extra_widget`: optionales Zusatz-Widget (z.B. Von/Bis-Trial-Auswahl),
    wird zwischen Geometrie-Formular und Info-Zeile eingefuegt.
    `item_count`: Anzahl zu druckender Labels; kann sich per
    `set_item_count()` nachtraeglich aendern (z.B. wenn der Aufrufer die
    Von/Bis-Auswahl anpasst) - der Bogen-Picker aktualisiert sich dann live.
    """

    def __init__(self, template_name: str, template: Dict, item_count: int,
                 extra_widget: Optional[QWidget] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Print Labels")
        self.template_name = template_name
        self._start_index = 0
        self._grid_buttons: List[QPushButton] = []
        self._queue_count = item_count

        root = QVBoxLayout(self)

        form = QFormLayout()
        self._inputs: Dict[str, object] = {}
        for key, label in TEMPLATE_FIELDS:
            if key in ("ColumnCount", "RowCount"):
                w = QSpinBox()
                w.setRange(1, 30)
                w.setValue(int(template.get(key) or 1))
            else:
                w = QDoubleSpinBox()
                w.setRange(0.0, 1000.0)
                w.setDecimals(2)
                w.setValue(float(template.get(key) or 0.0))
            w.valueChanged.connect(self._rebuild_grid)
            self._inputs[key] = w
            form.addRow(label, w)
        root.addLayout(form)

        if extra_widget is not None:
            root.addWidget(extra_widget)

        self.lbl_info = QLabel()
        root.addWidget(self.lbl_info)

        self.lbl_geometry_warning = QLabel()
        self.lbl_geometry_warning.setWordWrap(True)
        self.lbl_geometry_warning.setStyleSheet(
            "background: #FFF3CD; color: #7A5B00; padding: 6px 10px; border-radius: 4px;")
        self.lbl_geometry_warning.setVisible(False)
        root.addWidget(self.lbl_geometry_warning)

        self.grid_frame = QFrame()
        self.grid_layout = QGridLayout(self.grid_frame)
        self.grid_layout.setSpacing(2)
        root.addWidget(self.grid_frame)

        self._rebuild_grid()

        btns = QDialogButtonBox()
        self.btn_save_template = QPushButton("Save template", objectName="GreyBtn")
        self.btn_save_template.clicked.connect(self._on_save_template)
        self.btn_print = QPushButton("Generate PDF", objectName="GreenBtn")
        self.btn_print.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel", objectName="GreyBtn")
        btn_cancel.clicked.connect(self.reject)
        btns.addButton(self.btn_save_template, QDialogButtonBox.ActionRole)
        btns.addButton(self.btn_print, QDialogButtonBox.AcceptRole)
        btns.addButton(btn_cancel, QDialogButtonBox.RejectRole)
        root.addWidget(btns)

    def set_item_count(self, n: int) -> None:
        self._queue_count = max(0, n)
        self._rebuild_grid()

    def _check_geometry(self):
        v = {k: w.value() for k, w in self._inputs.items()}
        needed_h = v["MarginTopMm"] + v["RowCount"] * v["LabelHeightMm"] + \
            max(0, v["RowCount"] - 1) * v["VGapMm"]
        needed_w = v["MarginLeftMm"] + v["ColumnCount"] * v["LabelWidthMm"] + \
            max(0, v["ColumnCount"] - 1) * v["HGapMm"]
        msgs = []
        if needed_h > v["PageHeightMm"]:
            over = needed_h - v["PageHeightMm"]
            msgs.append(
                f"⚠ Rows don't fit: needs {needed_h:.1f}mm height, page is only "
                f"{v['PageHeightMm']:.1f}mm ({over:.1f}mm too much) — the last row(s) "
                f"will be cut off when printed.")
        if needed_w > v["PageWidthMm"]:
            over = needed_w - v["PageWidthMm"]
            msgs.append(
                f"⚠ Columns don't fit: needs {needed_w:.1f}mm width, page is only "
                f"{v['PageWidthMm']:.1f}mm ({over:.1f}mm too much) — the last column(s) "
                f"will be cut off when printed.")
        if msgs:
            self.lbl_geometry_warning.setText("\n".join(msgs))
            self.lbl_geometry_warning.setVisible(True)
        else:
            self.lbl_geometry_warning.setVisible(False)

    def _rebuild_grid(self):
        self._check_geometry()
        self.lbl_info.setText(
            f"{self._queue_count} label(s) to print. Click the first free cell on the sheet "
            f"below (useful for partially-used sheets).")
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._grid_buttons = []

        cols = int(self._inputs["ColumnCount"].value())
        rows = int(self._inputs["RowCount"].value())
        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c
                btn = QPushButton(str(idx + 1))
                btn.setFixedSize(30, 30)
                btn.setCheckable(True)
                if idx == self._start_index:
                    btn.setChecked(True)
                btn.clicked.connect(lambda _checked, i=idx: self._set_start_index(i))
                self.grid_layout.addWidget(btn, r, c)
                self._grid_buttons.append(btn)
        self._update_grid_highlight()

    def _set_start_index(self, idx: int):
        self._start_index = idx
        self._update_grid_highlight()

    def _update_grid_highlight(self):
        will_be_used = set(range(self._start_index, self._start_index + self._queue_count))
        for i, btn in enumerate(self._grid_buttons):
            btn.blockSignals(True)
            btn.setChecked(i == self._start_index)
            btn.blockSignals(False)
            btn.setStyleSheet(
                "background-color: #9FE1CB;" if i in will_be_used else "")

    def _on_save_template(self):
        try:
            save_label_template(self.template_name, self.template_values())
        except Exception as e:
            show_error(self, "Save template", "The template could not be saved.", e)
            return
        QMessageBox.information(self, "Save template", "Template saved.")

    def template_values(self) -> Dict:
        return {k: w.value() for k, w in self._inputs.items()}

    def start_index(self) -> int:
        return self._start_index