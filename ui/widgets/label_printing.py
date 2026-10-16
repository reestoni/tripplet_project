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

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None
try:
    import qrcode
except Exception:
    qrcode = None

MM = 72.0 / 25.4  # PDF-Punkte pro mm

LABEL_TEMPLATE_TABLE = "tblLabelTemplate"

TEMPLATE_FIELDS = [
    ("PageWidthMm", "Page width (mm)"), ("PageHeightMm", "Page height (mm)"),
    ("ColumnCount", "Columns"), ("RowCount", "Rows"),
    ("LabelWidthMm", "Label width (mm)"), ("LabelHeightMm", "Label height (mm)"),
    ("MarginTopMm", "Top margin (mm)"), ("MarginLeftMm", "Left margin (mm)"),
    ("HGapMm", "Horizontal gap (mm)"), ("VGapMm", "Vertical gap (mm)"),
]

DEFAULT_TEMPLATE = {
    "PageWidthMm": 210.0, "PageHeightMm": 297.0,
    "ColumnCount": 3, "RowCount": 8,
    "LabelWidthMm": 63.5, "LabelHeightMm": 33.9,
    "MarginTopMm": 13.0, "MarginLeftMm": 7.0,
    "HGapMm": 2.5, "VGapMm": 0.0,
}


def load_label_template(template_name: str = "Default") -> Dict:
    """Laedt das benannte Template. Existiert es nicht, werden Default-Werte
    zurueckgegeben (noch nicht gespeichert - erst bei save_label_template)."""
    if table_exists(LABEL_TEMPLATE_TABLE):
        rows = fetch_all(
            f"SELECT * FROM {LABEL_TEMPLATE_TABLE} WHERE [Name] = ? ORDER BY [ID] LIMIT 1",
            [template_name])
        if rows:
            return rows[0]
    return dict(DEFAULT_TEMPLATE, Name=template_name)


def save_label_template(template_name: str, values: Dict) -> None:
    """Speichert (Insert oder Update) das benannte Template."""
    if not table_exists(LABEL_TEMPLATE_TABLE):
        return
    existing = fetch_all(
        f"SELECT [ID] FROM {LABEL_TEMPLATE_TABLE} WHERE [Name] = ? LIMIT 1", [template_name])
    cols = [k for k, _ in TEMPLATE_FIELDS]
    if existing:
        sets = ", ".join(f"[{k}] = ?" for k in cols)
        execute(f"UPDATE {LABEL_TEMPLATE_TABLE} SET {sets} WHERE [ID] = ?",
                [values[k] for k in cols] + [existing[0]["ID"]])
    else:
        all_cols = ["Name"] + cols
        ph = ", ".join(["?"] * len(all_cols))
        execute(f"INSERT INTO {LABEL_TEMPLATE_TABLE} ({', '.join(f'[{c}]' for c in all_cols)}) "
                f"VALUES ({ph})",
                [template_name] + [values[k] for k in cols])


def fit_text(text: str, fontsize: float, max_width_mm: float, fontname: str = "helv") -> str:
    """Kuerzt `text` mit '…', falls er bei `fontsize` breiter als
    `max_width_mm` waere."""
    if fitz is None or not text:
        return text
    max_width_pt = max_width_mm * MM
    if fitz.get_text_length(text, fontname=fontname, fontsize=fontsize) <= max_width_pt:
        return text
    ell = "…"
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        candidate = text[:mid].rstrip() + ell
        if fitz.get_text_length(candidate, fontname=fontname, fontsize=fontsize) <= max_width_pt:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo].rstrip() + ell if lo > 0 else ell


def wrap_text_lines(text: str, fontsize: float, max_width_mm: float, max_lines: int = 2,
                     fontname: str = "helv") -> List[str]:
    """Bricht `text` auf bis zu `max_lines` Zeilen um (an Wortgrenzen)."""
    if fitz is None or not text:
        return [text] if text else []
    max_width_pt = max_width_mm * MM
    if fitz.get_text_length(text, fontname=fontname, fontsize=fontsize) <= max_width_pt:
        return [text]
    words = text.split(" ")
    lines: List[str] = []
    current = ""
    i = 0
    while i < len(words) and len(lines) < max_lines - 1:
        candidate = (current + " " + words[i]).strip()
        if fitz.get_text_length(candidate, fontname=fontname, fontsize=fontsize) <= max_width_pt:
            current = candidate
            i += 1
        elif current:
            lines.append(current)
            current = ""
        else:
            current = fit_text(words[i], fontsize, max_width_mm, fontname)
            i += 1
            lines.append(current)
            current = ""
    remainder = (current + " " + " ".join(words[i:])).strip()
    if remainder:
        lines.append(fit_text(remainder, fontsize, max_width_mm, fontname))
    return lines[:max_lines] if lines else [text]


def draw_qr(page, x_mm: float, y_mm: float, size_mm: float, text: str) -> None:
    """Zeichnet einen QR-Code als gefuellte Rechtecke, gebatcht in EINEM
    page.new_shape() (siehe Modul-Docstring - Performance-kritisch)."""
    from qrcode.constants import ERROR_CORRECT_L
    qr = qrcode.QRCode(border=0, box_size=1, error_correction=ERROR_CORRECT_L)
    qr.add_data(text)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    n = len(matrix)
    if n == 0:
        return
    cell = size_mm / n
    shape = page.new_shape()
    # Winziger Overlap (0.15pt) zwischen benachbarten Modulen, damit bei der
    # Rasterung/beim Druck keine Haarlinien-Luecken durch Rundungsfehler
    # entstehen - unsichtbar klein im Verhaeltnis zur Modulgroesse.
    overlap = 0.15
    for r, row in enumerate(matrix):
        for c, val in enumerate(row):
            if not val:
                continue
            x0 = (x_mm + c * cell) * MM
            y0 = (y_mm + r * cell) * MM
            rect = fitz.Rect(x0 - overlap, y0 - overlap, x0 + cell * MM + overlap, y0 + cell * MM + overlap)
            shape.draw_rect(rect)
    # width=0: kein Konturstrich - sonst bekommt jedes der u.U. hunderten
    # Module zusaetzlich eine Standard-Umrandung, was beim Druck koernig/
    # unsauber statt als glatte, klare Flaechen aussieht.
    shape.finish(color=(0, 0, 0), fill=(0, 0, 0), width=0)
    shape.commit()


def generate_label_sheet_pdf(items: List[Dict], template: Dict, start_index: int,
                              out_path: str,
                              draw_cell: Callable[..., None]) -> int:
    """Generischer Bogen-Layouter: platziert `items` zeilenweise ab
    `start_index` (0-basiert) auf einem/mehreren Boegen und ruft fuer jede
    Zelle `draw_cell(page, x0_mm, y0_mm, label_w_mm, label_h_mm, item)` auf.

    Passen nicht alle Items auf einen Bogen, werden automatisch weitere
    Seiten angehaengt (jeweils ab Zelle 0) - kein stilles Abschneiden mehr.
    Gibt zurueck, wie viele Items platziert wurden (immer len(items), da nie
    abgebrochen wird).
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed.")

    cols = int(template["ColumnCount"])
    rows = int(template["RowCount"])
    per_page = max(1, cols * rows)
    doc = fitz.open()

    placed = 0
    current_page_num = -1
    page = None
    for i, item in enumerate(items):
        absolute_slot = start_index + i
        page_num = absolute_slot // per_page
        slot_on_page = absolute_slot % per_page
        if page_num != current_page_num:
            page = doc.new_page(width=template["PageWidthMm"] * MM, height=template["PageHeightMm"] * MM)
            current_page_num = page_num

        col = slot_on_page % cols
        row = slot_on_page // cols
        x0 = template["MarginLeftMm"] + col * (template["LabelWidthMm"] + template["HGapMm"])
        y0 = template["MarginTopMm"] + row * (template["LabelHeightMm"] + template["VGapMm"])
        draw_cell(page, x0, y0, template["LabelWidthMm"], template["LabelHeightMm"], item)
        placed += 1

    doc.save(out_path)
    doc.close()
    return placed


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