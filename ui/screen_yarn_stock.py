# ui/screen_yarn_stock.py
"""Yarn stock: simple spool registration (no booking ledger) + label printing.

Two levels:
- Overview: aggregated by yarn + batch (spool count, total weight, status)
- Detail: individual spools of the group selected in the overview
  (weight/location directly editable, checkbox + discard, create new spool(s))

Label printing: spools get added to a print queue instead of printing
immediately. The print dialog shows a clickable grid matching the physical
label sheet so printing can resume at the first free cell of a
partially-used sheet, instead of wasting a full sheet for a handful of
labels.

Write access (check in/out/adjust) only from app_meta.access_level() >= 2,
same convention as the rest of the app (see screen_show_experiment.py
_ctx_is_readonly / screen_all_experiments.py "Keine Schreibrechte").
"""
import re
from typing import List, Dict, Optional, Tuple, Any
from datetime import date, datetime

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer, QSize
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame, QPushButton,
    QSizePolicy, QTableView, QTableWidget, QTableWidgetItem, QMessageBox,
    QLineEdit, QAbstractItemView, QDialog, QFormLayout, QComboBox,
    QSpinBox, QDoubleSpinBox, QDialogButtonBox, QFileDialog, QStyledItemDelegate,
    QCheckBox,
)

from ui.theme import accent_tint, accent_gridline
from ui.widgets.footer import FooterBar
from ui.widgets.yarn_stock_help_dialog import show_yarn_stock_help
from ui.pathutil import resource_path
from ui.widgets import sidebar_nav
from ui.widgets.label_printing import (
    MM, fit_text, wrap_text_lines, draw_qr, generate_label_sheet_pdf,
    load_label_template, save_label_template, PrintLabelsDialog,
)
from db.connection import fetch_all, execute, execute_insert, new_global_id, get_columns_map, table_exists
from db import yarn_spool_log
from db.usage_log import log_usage_event
import app_meta

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None
try:
    import qrcode
except Exception:
    qrcode = None


# Flacher, runder Toggle-Button fuer ein-/ausklappbare Abschnitte (Spools,
# Label queue) - statt des Standard-System-Buttons.
_TOGGLE_BTN_QSS = """
    QPushButton {
        background: rgba(0, 0, 0, 0.05);
        border: none;
        border-radius: 12px;
        font-size: 12px;
        color: #444;
        padding: 0px;
    }
    QPushButton:hover {
        background: rgba(57, 166, 80, 0.18);
        color: #2b7a3d;
    }
    QPushButton:pressed {
        background: rgba(57, 166, 80, 0.30);
    }
"""


def _resolve_field(cands: List[str], cmap: Dict[str, str]) -> Optional[str]:
    for c in cands:
        key = c.strip().lower().replace(" ", "")
        if key in cmap:
            return cmap[key]
    return None


# Spulennummer am Ende des QR-Inhalts ("...;S:213", siehe _qr_content()).
# Bewusst tolerant beim Trennzeichen: Handscanner senden meist mit US-Layout,
# auf CH/DE-Tastaturen kommt ":" dann z.B. als anderes Zeichen an ("SÖ213").
_QR_SPOOL_RE = re.compile(r"[sS][^0-9A-Za-z]{1,3}#?(\d+)\s*$")


def parse_spool_input(text: str) -> Optional[int]:
    """Spulen-ID aus "Go to spool #"-Eingabe: "213", "#213" oder kompletter
    QR-Inhalt eines Etiketts ("Y:...;B:...;L:...;S:213", z.B. per Scanner).
    None, wenn nichts Brauchbares erkannt wird."""
    raw = (text or "").strip()
    plain = raw.lstrip("#").strip()
    if plain.isascii() and plain.isdigit():
        return int(plain)
    m = _QR_SPOOL_RE.search(raw)
    return int(m.group(1)) if m else None


def _qr_content(item: Dict) -> str:
    """Kompakter QR-Inhalt: Grossbuchstaben, kurze Kuerzel statt ausgeschriebener
    Woerter - haelt den Code trotz mehr Infos klein (siehe Chat: 25x25 statt
    37x37 Module). Gewicht bewusst NICHT drin, da es sich laufend aendert."""
    yarn = str(item.get("Yarn") or "").upper()
    batch = str(item.get("Batch") or "").upper()
    loc = str(item.get("Location") or "").upper()
    return f"Y:{yarn};B:{batch};L:{loc};S:{item['SpoolID']}"


def _draw_yarn_label_cell(page, x0: float, y0: float, lw: float, lh: float, item: Dict) -> None:
    """Zeichnet ein Spulen-Label (Garnname fett oben, QR + Location/Spule-ID
    gross + Batch dezent) - der Cell-Renderer fuer generate_label_sheet_pdf."""
    header_max_w = lw - 4
    HEADER_FS = 9.0
    yarn_lines = wrap_text_lines(str(item.get("Yarn") or ""), HEADER_FS, header_max_w, max_lines=2, fontname="hebo")
    ty = y0 + 5.0
    for yl in yarn_lines:
        page.insert_text(((x0 + 2) * MM, ty * MM), yl, fontsize=HEADER_FS, fontname="hebo")
        ty += HEADER_FS * 0.48

    divider_y = ty + 0.5
    page.draw_line(
        ((x0 + 2) * MM, divider_y * MM),
        ((x0 + lw - 2) * MM, divider_y * MM),
        color=(0.75, 0.75, 0.75), width=0.4)

    content_top = divider_y + 1.2
    content_h = (y0 + lh) - content_top - 1.5
    qr_size = min(content_h, lw * 0.42)
    draw_qr(page, x0 + 2, content_top, qr_size, _qr_content(item))

    rx = x0 + 2 + qr_size + 3
    r_max_w = max(4.0, (x0 + lw) - rx - 2)

    # Der Loc/ID/Batch-Textblock braucht bei voller Groesse ~20.5mm Hoehe.
    # Ist weniger Platz uebrig (z.B. 2-zeiliger Garnname), wird proportional
    # runterskaliert, damit der Block IMMER innerhalb der Zelle bleibt.
    IDEAL_BLOCK_H = 20.5
    scale = min(1.0, max(0.55, content_h / IDEAL_BLOCK_H)) if content_h > 0 else 0.55
    big_fs = max(8.0, 15.0 * scale)
    batch_fs = max(5.0, 8.0 * scale)
    off1, off2, off3 = 6.5 * scale, 7.5 * scale, 6.5 * scale

    loc_txt = fit_text(str(item.get("Location") or "-"), big_fs, r_max_w, fontname="hebo")
    id_txt = fit_text(f"#{item['SpoolID']}", big_fs, r_max_w, fontname="hebo")
    batch_txt = fit_text(str(item.get("Batch") or "-"), batch_fs, r_max_w)

    ry = content_top + off1
    page.insert_text((rx * MM, ry * MM), loc_txt, fontsize=big_fs, fontname="hebo")
    ry += off2
    page.insert_text((rx * MM, ry * MM), id_txt, fontsize=big_fs, fontname="hebo")
    ry += off3
    page.insert_text((rx * MM, ry * MM), batch_txt, fontsize=batch_fs, color=(0.45, 0.45, 0.45))


def _has_write_rights() -> bool:
    try:
        return int(app_meta.access_level() or 0) >= 2
    except Exception:
        return False


def _current_user_id() -> Optional[int]:
    try:
        user = getattr(app_meta, "current_user", {}) or {}
        if isinstance(user, dict):
            for k in ("ID", "Id", "id"):
                if k in user:
                    return user[k]
    except Exception:
        pass
    return None


def create_producer(name: str) -> Optional[int]:
    """Legt einen neuen Producer in tblYarnProducer an und gibt die neue ID zurück."""
    name = (name or "").strip()
    if not name or not table_exists("tblYarnProducer"):
        return None
    execute(
        "INSERT INTO tblYarnProducer ([Name],[GlobalID]) VALUES (?,?)",
        [name, new_global_id()],
    )
    rows = fetch_all("SELECT ID FROM tblYarnProducer WHERE [Name] = ? ORDER BY ID DESC LIMIT 1", [name])
    return int(rows[0]["ID"]) if rows else None


def populate_producer_combo(cb: QComboBox, current_id: Optional[int] = None) -> None:
    """Befüllt eine Producer-QComboBox mit '— none —' und allen Herstellern."""
    cb.clear()
    cb.addItem("— none —", None)
    if table_exists("tblYarnProducer"):
        try:
            for pr in fetch_all("SELECT ID, Name FROM tblYarnProducer ORDER BY Name"):
                cb.addItem(str(pr.get("Name") or ""), int(pr["ID"]))
        except Exception:
            pass
    if current_id is not None:
        i = cb.findData(current_id)
        if i >= 0:
            cb.setCurrentIndex(i)


def prompt_new_producer(cb: QComboBox, parent: QWidget) -> None:
    """Fuer den '+'-Button neben einer Producer-ComboBox: fragt per simplem
    modalem Dialog nach dem Namen, legt ihn an und waehlt ihn aus.

    Bewusst als eigenstaendiger Button-Click (statt Dropdown-Eintrag "+ New
    producer..."), da ein QInputDialog, das mitten aus dem
    currentIndexChanged-Event einer ComboBox heraus geoeffnet wird, bei
    verschachtelten Dialogen (New Spool ist selbst schon modal) zu einem
    Einfrieren ohne Fehlermeldung fuehren kann. Ein normaler Button-Klick hat
    dieses Timing-Problem nicht.
    """
    from PySide6.QtWidgets import QInputDialog
    name, ok = QInputDialog.getText(parent, "New producer", "Producer name:")
    if not (ok and name.strip()):
        return
    new_id = create_producer(name)
    populate_producer_combo(cb, current_id=new_id)


# ------------------------ Spool detail table ------------------------

class SpoolTableModel(QAbstractTableModel):
    """Editable model for the spools of one yarn/batch group.

    Column 0 = checkbox (multi-select for discarding), "Weight"/"Location"/
    "Colour" are directly editable text, "Producer" is edited via a combo
    delegate (see ProducerComboDelegate) since it's a lookup FK. Discarded
    spools (Status='discarded') stay visible, but greyed out and no longer
    editable.
    """
    HEADERS = ["", "Spool", "Weight (kg)", "Location", "Tube Colour", "Producer", "Received", "Status"]

    def __init__(self, rows: List[Dict], writable: bool, producer_map: Optional[Dict[int, str]] = None):
        super().__init__()
        self._rows = rows
        self._writable = writable
        self._producer_map = producer_map or {}
        self._checked: set = set()
        self._dirty_weights: Dict[int, float] = {}
        self._dirty_locations: Dict[int, str] = {}
        self._dirty_colours: Dict[int, str] = {}
        self._dirty_producers: Dict[int, Optional[int]] = {}

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.NoItemFlags
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        c = index.column()
        row = self._rows[index.row()]
        is_active = row.get("Status") == "in stock"
        # Checkbox-Toggle laeuft explizit ueber YarnStockScreen._on_detail_clicked
        # (klickzuverlaessiger als das eingebaute Qt-Indikator-Hit-Testing),
        # daher hier bewusst KEIN Qt.ItemIsUserCheckable mehr setzen.
        if c in (2, 3, 4, 5) and self._writable and is_active:
            base |= Qt.ItemIsEditable
        return base

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        r, c = index.row(), index.column()
        row = self._rows[r]
        discarded = row.get("Status") != "in stock"
        if role == Qt.CheckStateRole and c == 0:
            return Qt.Checked if r in self._checked else Qt.Unchecked
        if role in (Qt.DisplayRole, Qt.EditRole):
            if c == 1:
                return f"#{row.get('ID')}"
            if c == 2:
                w = self._dirty_weights.get(r, row.get("WeightKg"))
                return f"{float(w):.2f}" if w is not None else ""
            if c == 3:
                loc = self._dirty_locations.get(r, row.get("Location"))
                return loc or ""
            if c == 4:
                col = self._dirty_colours.get(r, row.get("Colour"))
                return col or ""
            if c == 5:
                pid = self._dirty_producers.get(r, row.get("ProducerID"))
                if role == Qt.EditRole:
                    return pid
                return self._producer_map.get(pid, "") if pid is not None else ""
            if c == 6:
                return str(row.get("ReceivedDate") or "")
            if c == 7:
                return row.get("Status") or ""
        if role == Qt.ForegroundRole and discarded:
            return QColor("#999999")
        if role == Qt.TextAlignmentRole and c == 2:
            return Qt.AlignRight | Qt.AlignVCenter
        return None

    def setData(self, index: QModelIndex, value, role=Qt.EditRole) -> bool:
        if not index.isValid():
            return False
        r, c = index.row(), index.column()
        if role == Qt.CheckStateRole and c == 0:
            if value == Qt.Checked:
                self._checked.add(r)
            else:
                self._checked.discard(r)
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True
        if role == Qt.EditRole and c == 2 and self._writable:
            try:
                w = float(str(value).replace(",", "."))
            except Exception:
                return False
            if w < 0:
                return False
            self._dirty_weights[r] = w
            self.dataChanged.emit(index, index, [Qt.DisplayRole])
            return True
        if role == Qt.EditRole and c == 3 and self._writable:
            self._dirty_locations[r] = str(value).strip()
            self.dataChanged.emit(index, index, [Qt.DisplayRole])
            return True
        if role == Qt.EditRole and c == 4 and self._writable:
            self._dirty_colours[r] = str(value).strip()
            self.dataChanged.emit(index, index, [Qt.DisplayRole])
            return True
        if role == Qt.EditRole and c == 5 and self._writable:
            pid = value if value in (None, "") else int(value)
            self._dirty_producers[r] = pid if pid != "" else None
            self.dataChanged.emit(index, index, [Qt.DisplayRole])
            return True
        return False

    def checked_spool_ids(self) -> List[int]:
        return [self._rows[r]["ID"] for r in self._checked]

    def active_row_indices(self) -> List[int]:
        return [r for r, row in enumerate(self._rows) if row.get("Status") == "in stock"]

    def all_active_checked(self) -> bool:
        active = self.active_row_indices()
        return bool(active) and all(r in self._checked for r in active)

    def set_all_checked(self, checked: bool) -> None:
        active = self.active_row_indices()
        if not active:
            return
        if checked:
            self._checked.update(active)
        else:
            self._checked.difference_update(active)
        top = self.index(0, 0)
        bottom = self.index(self.rowCount() - 1, 0)
        self.dataChanged.emit(top, bottom, [Qt.CheckStateRole])

    def dirty_weight_updates(self) -> Dict[int, float]:
        return {self._rows[r]["ID"]: w for r, w in self._dirty_weights.items()}

    def dirty_location_updates(self) -> Dict[int, str]:
        return {self._rows[r]["ID"]: loc for r, loc in self._dirty_locations.items()}

    def dirty_colour_updates(self) -> Dict[int, str]:
        return {self._rows[r]["ID"]: col for r, col in self._dirty_colours.items()}

    def dirty_producer_updates(self) -> Dict[int, Optional[int]]:
        return {self._rows[r]["ID"]: pid for r, pid in self._dirty_producers.items()}

    def has_pending_changes(self) -> bool:
        return bool(self._dirty_weights) or bool(self._dirty_locations) \
            or bool(self._dirty_colours) or bool(self._dirty_producers)

    def clear_pending_changes(self) -> None:
        self._dirty_weights.clear()
        self._dirty_locations.clear()
        self._dirty_colours.clear()
        self._dirty_producers.clear()


class ProducerComboDelegate(QStyledItemDelegate):
    """Dropdown-Editor fuer die Producer-Spalte (Lookup auf tblYarnProducer).
    Neue Producer werden ueber den '+'-Button im 'New spool(s)'-Dialog
    angelegt (siehe prompt_new_producer) - dort tauchen sie danach auch
    hier automatisch mit auf. Bewusst kein Inline-Anlegen aus dieser
    Zellen-Editor-ComboBox heraus, da ein modaler Dialog mitten aus einem
    Tabellen-Zell-Editor heraus zu Einfrieren fuehren kann."""

    def __init__(self, producer_choices: List[Tuple[int, str]], parent=None):
        super().__init__(parent)
        self._choices = producer_choices

    def createEditor(self, parent, option, index):
        cb = QComboBox(parent)
        cb.setEditable(False)
        populate_producer_combo(cb)
        return cb

    def setEditorData(self, editor, index):
        if not isinstance(editor, QComboBox):
            return
        current_id = index.data(Qt.EditRole)
        i = editor.findData(current_id)
        editor.setCurrentIndex(i if i >= 0 else 0)

    def setModelData(self, editor, model, index):
        if isinstance(editor, QComboBox):
            # EditRole = rohe ProducerID (fuer Wiedereditieren/Delegate),
            # DisplayRole = lesbarer Name - sonst zeigt die Zelle nach dem
            # Uebernehmen nur die ID an, da QTableWidgetItem ohne expliziten
            # DisplayRole sonst auf den EditRole-Wert zurueckfaellt.
            model.setData(index, editor.currentData(), Qt.EditRole)
            model.setData(index, editor.currentText(), Qt.DisplayRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


# ------------------------ New spool(s) dialog ------------------------

class UsedInDialog(QDialog):
    """Rueckverfolgung: zeigt, in welchen Trials die gewaehlten Spulen
    tatsaechlich verwendet wurden (tbltrialsettings.SpoolID)."""

    def __init__(self, spool_ids: List[int], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Used in")
        self.setMinimumSize(600, 350)
        root = QVBoxLayout(self)

        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["Spool", "Experiment", "Series", "Trial", "Ply"])
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        rows = []
        if spool_ids and table_exists("tbltrialsettings") and table_exists("tbltrial"):
            ph = ",".join(["?"] * len(spool_ids))
            try:
                rows = fetch_all(
                    f"SELECT ts.SpoolID, ts.Ply, t.Versuchsnummer, t.TrialSeriesID, "
                    f"e.ExperimentID AS ExperimentIDTxt "
                    f"FROM tbltrialsettings ts "
                    f"JOIN tbltrial t ON t.ID = ts.TrialID "
                    f"LEFT JOIN tbltrialseries s ON s.ID = t.TrialSeriesID "
                    f"LEFT JOIN tblexperimente e ON e.ID = s.ExperimentID "
                    f"WHERE ts.SpoolID IN ({ph}) "
                    f"ORDER BY ts.SpoolID, t.Versuchsnummer",
                    spool_ids,
                )
            except Exception:
                rows = []

        if not rows:
            root.addWidget(QLabel("No trials found using the selected spool(s)."))
        table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [
                f"#{r['SpoolID']}",
                str(r.get("ExperimentIDTxt") or "–"),
                str(r.get("TrialSeriesID") or "–"),
                f"V{r.get('Versuchsnummer')}" if r.get("Versuchsnummer") is not None else "–",
                str(r.get("Ply") or ""),
            ]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                table.setItem(i, c, it)
        table.resizeColumnsToContents()
        root.addWidget(table, 1)

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.accept)
        btns.button(QDialogButtonBox.Close).clicked.connect(self.accept)
        root.addWidget(btns)


class SpoolHistoryDialog(QDialog):
    """Aenderungsprotokoll (tblYarnSpoolLog) fuer eine Menge Spulen -
    wer hat wann was von welchem auf welchen Wert geaendert."""

    def __init__(self, spool_ids: List[int], title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Spool history")
        self.setMinimumSize(760, 400)
        root = QVBoxLayout(self)
        root.addWidget(QLabel(f"<b>{title}</b>"))

        if not yarn_spool_log.log_table_exists():
            root.addWidget(QLabel("The change history is not available in this database yet."))
            rows = []
        else:
            try:
                rows = yarn_spool_log.fetch_spool_history(spool_ids)
            except Exception:
                rows = []
            if not rows:
                root.addWidget(QLabel(
                    "No changes recorded for these spools. Changes are recorded since the "
                    "history feature was introduced; older changes are not available."))

        table = QTableWidget(len(rows), 4)
        table.setHorizontalHeaderLabels(["When", "User", "Spool", "Change"])
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QTableView.SelectRows)
        for i, r in enumerate(rows):
            when = r.get("ChangedAt")
            when_txt = when.strftime("%Y-%m-%d %H:%M") if hasattr(when, "strftime") else str(when or "")
            vals = [when_txt, str(r.get("Username") or "–"), f"#{r.get('SpoolID')}", self._describe(r)]
            for c, v in enumerate(vals):
                table.setItem(i, c, QTableWidgetItem(v))
        table.resizeColumnsToContents()
        root.addWidget(table, 1)

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.accept)
        btns.button(QDialogButtonBox.Close).clicked.connect(self.accept)
        root.addWidget(btns)

    @staticmethod
    def _describe(r: Dict) -> str:
        action = r.get("Action")
        if action == yarn_spool_log.CREATED:
            return f"Created: {r.get('NewValue') or ''}".rstrip(": ")
        if action == yarn_spool_log.DISCARDED:
            new = (r.get("NewValue") or "").strip()
            note = new[len("discarded"):].strip() if new.lower().startswith("discarded") else ""
            return f"Discarded {note}".strip()
        return f"{r.get('FieldName') or 'Value'}: {r.get('OldValue') or '–'} → {r.get('NewValue') or '–'}"


class NewSpoolDialog(QDialog):
    def __init__(self, yarn_choices: List[Tuple[int, str]], parent=None, preselect_yarn_id=None):
        super().__init__(parent)
        self.setWindowTitle("New spool(s)")
        self.setMinimumWidth(360)

        form = QFormLayout(self)

        self.cmb_yarn = QComboBox()
        for yid, yname in yarn_choices:
            self.cmb_yarn.addItem(yname, yid)
        if preselect_yarn_id is not None:
            idx = self.cmb_yarn.findData(preselect_yarn_id)
            if idx >= 0:
                self.cmb_yarn.setCurrentIndex(idx)
        form.addRow("Yarn", self.cmb_yarn)

        self.txt_charge = QLineEdit()
        form.addRow("Batch", self.txt_charge)

        self.spn_weight = QDoubleSpinBox()
        self.spn_weight.setRange(0.0, 999999.0)
        self.spn_weight.setDecimals(2)
        self.spn_weight.setSuffix(" kg")
        self.spn_weight.setValue(5.0)
        form.addRow("Weight per spool", self.spn_weight)

        self.spn_count = QSpinBox()
        self.spn_count.setRange(1, 500)
        self.spn_count.setValue(1)
        form.addRow("Number of spools", self.spn_count)

        self.txt_location = QLineEdit()
        form.addRow("Location", self.txt_location)

        self.txt_colour = QLineEdit()
        form.addRow("Tube Colour", self.txt_colour)

        self.cmb_producer = QComboBox()
        populate_producer_combo(self.cmb_producer)
        producer_row = QHBoxLayout()
        producer_row.addWidget(self.cmb_producer, 1)
        btn_new_producer = QPushButton("+ New")
        btn_new_producer.setMinimumWidth(70)
        btn_new_producer.setToolTip("Create a new producer")
        btn_new_producer.clicked.connect(lambda: prompt_new_producer(self.cmb_producer, self))
        producer_row.addWidget(btn_new_producer)
        form.addRow("Producer", producer_row)

        # Nach einer Lieferung druckt man praktisch immer Etiketten (Nutzerwunsch
        # 2026-10-13) - daher standardmaessig an, aber sichtbar abwaehlbar.
        self.chk_label_queue = QCheckBox("Add new spools to the label queue")
        self.chk_label_queue.setChecked(True)
        form.addRow("", self.chk_label_queue)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

    def values(self) -> Dict:
        return {
            "YarnID": self.cmb_yarn.currentData(),
            "Charge": self.txt_charge.text().strip() or None,
            "WeightKg": self.spn_weight.value(),
            "Count": self.spn_count.value(),
            "Location": self.txt_location.text().strip() or None,
            "Colour": self.txt_colour.text().strip() or None,
            "ProducerID": self.cmb_producer.currentData(),
            "AddToLabelQueue": self.chk_label_queue.isChecked(),
        }


# ------------------------ Print labels dialog ------------------------

LABEL_QUEUE_TABLE = "tblYarnLabelQueue"

class YarnStockScreen(QWidget):
    """Yarn stock: overview (yarn x batch) + spool detail."""

    # Overview-Spalten
    # Status bewusst VOR Locations: die Lagerplatz-Liste ist variabel lang,
    # Status soll ohne horizontales Scrollen sichtbar bleiben.
    OV_HEADERS = ["Yarn", "Batch", "Producer", "Spools", "Total (kg)",
                  "Yarn total (kg)", "Min. stock (kg)", "Status", "Locations"]
    OV_COL_BATCH, OV_COL_PRODUCER, OV_COL_MINSTOCK = 1, 2, 6
    OV_NUMERIC_COLS = (3, 4, 5, 6)

    YARN_TABLE = "tblYarn"
    SPOOL_TABLE = "tblYarnSpool"

    def __init__(self, on_back_home=None, sidebar_callbacks=None):
        super().__init__()
        self.on_back_home = on_back_home
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None
        self._writable = _has_write_rights()

        self._yarn_id_col = "ID"
        self._yarn_name_col = None
        self._yarn_minstock_col = None
        self._yarn_choices: List[Tuple[int, str]] = []

        self._overview: List[Dict] = []      # aggregierte Zeilen
        self._selected_group: Optional[Tuple[int, str]] = None  # (YarnID, Charge)

        self.tbl_overview: Optional[QTableWidget] = None
        self.tbl_detail: Optional[QTableView] = None
        self.model_detail: Optional[SpoolTableModel] = None
        self.lbl_detail_title: Optional[QLabel] = None
        self.btn_new_spool: Optional[QPushButton] = None
        self.btn_discard: Optional[QPushButton] = None
        self.btn_save: Optional[QPushButton] = None

        self._build_ui()
        self.reload_data()

    def _go_home(self):
        if callable(self.on_back_home):
            self.on_back_home()

    # ---------------- UI ----------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring).
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        _qss = """
            QTableView, QTableWidget { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView::item, QTableWidget::item { color: black; }
            QTableView::item:selected, QTableWidget::item:selected { background: #b7d6ff; color: black; }
        """.replace("#B5D7B5", accent_gridline()).replace("#E9F6E9", accent_tint())

        body = QFrame()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(24, 16, 24, 16)
        bl.setSpacing(16)

        # ── Quick "Go to spool #" ───────────────────────────────────────
        goto_hdr = QHBoxLayout()
        goto_hdr.addWidget(QLabel("Go to spool #:"))
        self.txt_goto_spool = QLineEdit()
        self.txt_goto_spool.setPlaceholderText("213 or scan label")
        self.txt_goto_spool.setToolTip("Type a spool number or scan the QR code on a spool label.")
        self.txt_goto_spool.setFixedWidth(130)
        self.txt_goto_spool.returnPressed.connect(self._on_goto_spool)
        goto_hdr.addWidget(self.txt_goto_spool)
        btn_goto_spool = QPushButton("Go", objectName="GreyBtn")
        btn_goto_spool.clicked.connect(self._on_goto_spool)
        goto_hdr.addWidget(btn_goto_spool)
        goto_hdr.addStretch(1)

        # Kontext-Hilfe (Nutzerwunsch 2026-10-13), gleiches Muster/Styling wie
        # der Hilfe-Button in screen_create_experiment_request.py.
        self.btn_help = QPushButton()
        self.btn_help.setCursor(Qt.PointingHandCursor)
        self.btn_help.setFixedSize(26, 26)
        self.btn_help.setToolTip("How does Yarn Stock work?")
        self.btn_help.setStyleSheet(
            "QPushButton{background:transparent;border:1px solid #39a650;"
            "border-radius:13px;padding:0;}"
            "QPushButton:hover{background:#e8f5e9;}"
        )
        help_icon = QIcon(resource_path("assets/images/help_tour.png"))
        if not help_icon.isNull():
            self.btn_help.setIcon(help_icon)
            self.btn_help.setIconSize(QSize(16, 16))
        else:
            self.btn_help.setText("?")
            self.btn_help.setStyleSheet(
                self.btn_help.styleSheet() + "QPushButton{color:#39a650;font-size:14px;font-weight:700;}"
            )
        self.btn_help.clicked.connect(lambda: show_yarn_stock_help(self))
        goto_hdr.addWidget(self.btn_help, 0, Qt.AlignVCenter)
        bl.addLayout(goto_hdr)

        # ── Overview ─────────────────────────────────────────────────
        ov_hdr = QHBoxLayout()
        ov_hdr.addWidget(QLabel("<b>Overview — yarn / batch</b>"))
        ov_hdr.addStretch(1)
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search yarn / batch…")
        self.txt_search.setFixedWidth(200)
        self.txt_search.textChanged.connect(self._apply_overview_filter)
        ov_hdr.addWidget(self.txt_search)
        self.cmb_status_filter = QComboBox()
        self.cmb_status_filter.addItems(["All statuses", "OK", "Low", "Empty"])
        self.cmb_status_filter.currentIndexChanged.connect(self._apply_overview_filter)
        ov_hdr.addWidget(self.cmb_status_filter)
        btn_reload = QPushButton("Reload", objectName="GreyBtn")
        btn_reload.clicked.connect(self._on_reload_clicked)
        ov_hdr.addWidget(btn_reload)
        btn_export = QPushButton("Export to Excel", objectName="GreyBtn")
        btn_export.clicked.connect(self._on_export_excel)
        ov_hdr.addWidget(btn_export)
        bl.addLayout(ov_hdr)

        self.tbl_overview = QTableWidget(0, len(self.OV_HEADERS))
        self.tbl_overview.setHorizontalHeaderLabels(self.OV_HEADERS)
        self.tbl_overview.horizontalHeaderItem(5).setToolTip(
            "Sum over all batches of this yarn. The status is based on this value.")
        self.tbl_overview.horizontalHeaderItem(self.OV_COL_MINSTOCK).setToolTip(
            "Minimum stock of the yarn (all batches together). Editable by superusers (double-click).")
        self.tbl_overview.horizontalHeader().setStretchLastSection(True)
        self.tbl_overview.verticalHeader().setVisible(False)
        self.tbl_overview.setSelectionBehavior(QTableView.SelectRows)
        self.tbl_overview.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_overview.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.tbl_overview.setItemDelegateForColumn(
            2, ProducerComboDelegate([], self.tbl_overview))
        self.tbl_overview.setStyleSheet(_qss)
        self.tbl_overview.setMinimumHeight(160)
        self.tbl_overview.itemSelectionChanged.connect(self._on_overview_selected)
        self.tbl_overview.itemChanged.connect(
            lambda item: self._on_group_item_changed(item, "_overview_filtered"))
        bl.addWidget(self.tbl_overview)

        # ── Detail ────────────────────────────────────────────────────
        det_section_hdr = QHBoxLayout()
        self.btn_toggle_detail = QPushButton("▾")
        self.btn_toggle_detail.setFixedSize(24, 24)
        self.btn_toggle_detail.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_detail.setStyleSheet(_TOGGLE_BTN_QSS)
        self.btn_toggle_detail.setToolTip("Collapse/expand spools section")
        self.btn_toggle_detail.clicked.connect(self._toggle_detail_section)
        det_section_hdr.addWidget(self.btn_toggle_detail)
        self.lbl_detail_title = QLabel("<b>Spools</b> — select yarn/batch above")
        det_section_hdr.addWidget(self.lbl_detail_title)
        self.lbl_readonly = QLabel("🔒 View only — no write access")
        self.lbl_readonly.setStyleSheet("color: #A32D2D; font-weight: 600;")
        self.lbl_readonly.setVisible(not self._writable)
        det_section_hdr.addWidget(self.lbl_readonly)
        det_section_hdr.addStretch(1)
        bl.addLayout(det_section_hdr)

        self.detail_content = QWidget()
        dc_layout = QVBoxLayout(self.detail_content)
        dc_layout.setContentsMargins(0, 0, 0, 0)
        dc_layout.setSpacing(8)

        det_hdr = QHBoxLayout()
        det_hdr.addStretch(1)
        self.btn_select_all = QPushButton("Select all", objectName="GreyBtn")
        self.btn_select_all.clicked.connect(self._on_toggle_select_all)
        self.btn_new_spool = QPushButton("New spool(s)", objectName="GreenBtn")
        self.btn_new_spool.clicked.connect(self._on_new_spool)
        self.btn_new_producer = QPushButton("New producer…", objectName="GreyBtn")
        self.btn_new_producer.clicked.connect(self._on_new_producer)
        self.btn_used_in = QPushButton("Used in…", objectName="GreyBtn")
        self.btn_used_in.clicked.connect(self._on_used_in)
        self.btn_history = QPushButton("History…", objectName="GreyBtn")
        self.btn_history.setToolTip(
            "Change history of the ticked/selected spools, or of the whole batch "
            "(including discarded spools) if none is ticked or selected.")
        self.btn_history.clicked.connect(self._on_history)
        self.btn_add_to_queue = QPushButton("Add to label queue", objectName="GreyBtn")
        self.btn_add_to_queue.clicked.connect(self._on_add_to_label_queue)
        self.btn_discard = QPushButton("Discard", objectName="GreyBtn")
        self.btn_discard.clicked.connect(self._on_discard)
        self.btn_save = QPushButton("Save Changes", objectName="PurpleBtn")
        self.btn_save.clicked.connect(self._on_save)
        det_hdr.addWidget(self.btn_select_all)
        det_hdr.addWidget(self.btn_new_spool)
        det_hdr.addWidget(self.btn_new_producer)
        det_hdr.addWidget(self.btn_used_in)
        det_hdr.addWidget(self.btn_history)
        det_hdr.addWidget(self.btn_add_to_queue)
        det_hdr.addWidget(self.btn_discard)
        det_hdr.addWidget(self.btn_save)
        dc_layout.addLayout(det_hdr)

        self.tbl_detail = QTableView()
        self.tbl_detail.verticalHeader().setVisible(False)
        self.tbl_detail.horizontalHeader().setStretchLastSection(True)
        self.tbl_detail.setSelectionBehavior(QTableView.SelectRows)
        self.tbl_detail.setStyleSheet(_qss)
        self.tbl_detail.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.tbl_detail.setMinimumHeight(220)
        self.tbl_detail.doubleClicked.connect(self._on_detail_double_clicked)
        self.tbl_detail.clicked.connect(self._on_detail_clicked)
        dc_layout.addWidget(self.tbl_detail, 1)

        bl.addWidget(self.detail_content, 1)

        # ── Label queue ──────────────────────────────────────────────
        lq_section_hdr = QHBoxLayout()
        self.btn_toggle_queue = QPushButton("▾")
        self.btn_toggle_queue.setFixedSize(24, 24)
        self.btn_toggle_queue.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_queue.setStyleSheet(_TOGGLE_BTN_QSS)
        self.btn_toggle_queue.setToolTip("Collapse/expand label queue section")
        self.btn_toggle_queue.clicked.connect(self._toggle_queue_section)
        lq_section_hdr.addWidget(self.btn_toggle_queue)
        lq_section_hdr.addWidget(QLabel("<b>Label queue</b>"))
        lq_section_hdr.addStretch(1)
        bl.addLayout(lq_section_hdr)

        self.queue_content = QWidget()
        qc_layout = QVBoxLayout(self.queue_content)
        qc_layout.setContentsMargins(0, 0, 0, 0)
        qc_layout.setSpacing(8)

        lq_hdr = QHBoxLayout()
        lq_hdr.addStretch(1)
        self.btn_remove_from_queue = QPushButton("Remove selected", objectName="GreyBtn")
        self.btn_remove_from_queue.clicked.connect(self._on_remove_from_label_queue)
        self.btn_print_labels = QPushButton("Print Labels…", objectName="GreenBtn")
        self.btn_print_labels.clicked.connect(self._on_print_labels)
        lq_hdr.addWidget(self.btn_remove_from_queue)
        lq_hdr.addWidget(self.btn_print_labels)
        qc_layout.addLayout(lq_hdr)

        self.tbl_queue = QTableWidget(0, 4)
        self.tbl_queue.setHorizontalHeaderLabels(["Spool", "Yarn", "Batch", "Weight (kg)"])
        self.tbl_queue.horizontalHeader().setStretchLastSection(True)
        self.tbl_queue.verticalHeader().setVisible(False)
        self.tbl_queue.setSelectionBehavior(QTableView.SelectRows)
        self.tbl_queue.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tbl_queue.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_queue.setStyleSheet(_qss)
        self.tbl_queue.setMinimumHeight(140)
        qc_layout.addWidget(self.tbl_queue)

        bl.addWidget(self.queue_content)

        # ── Rack lookup ──────────────────────────────────────────────
        rack_section_hdr = QHBoxLayout()
        self.btn_toggle_rack = QPushButton("▾")
        self.btn_toggle_rack.setFixedSize(24, 24)
        self.btn_toggle_rack.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_rack.setStyleSheet(_TOGGLE_BTN_QSS)
        self.btn_toggle_rack.setToolTip("Collapse/expand rack lookup section")
        self.btn_toggle_rack.clicked.connect(self._toggle_rack_section)
        rack_section_hdr.addWidget(self.btn_toggle_rack)
        rack_section_hdr.addWidget(QLabel("<b>Rack lookup</b>"))
        rack_section_hdr.addStretch(1)
        bl.addLayout(rack_section_hdr)

        self.rack_content = QWidget()
        rc_layout = QVBoxLayout(self.rack_content)
        rc_layout.setContentsMargins(0, 0, 0, 0)
        rc_layout.setSpacing(8)

        rack_hdr = QHBoxLayout()
        rack_hdr.addWidget(QLabel("Rack (e.g. \"C\"):"))
        self.txt_rack = QLineEdit()
        self.txt_rack.setPlaceholderText("C")
        self.txt_rack.setFixedWidth(60)
        self.txt_rack.textChanged.connect(self._apply_rack_filter)
        rack_hdr.addWidget(self.txt_rack)
        rack_hdr.addStretch(1)
        self.btn_stock_take = QPushButton("Stock take…", objectName="GreenBtn")
        self.btn_stock_take.setToolTip(
            "Stock take round: see which locations are checked and which are still open, "
            "scan the spools location by location, and get a summary of what was found where.")
        self.btn_stock_take.clicked.connect(self._on_stock_take)
        rack_hdr.addWidget(self.btn_stock_take)
        btn_rack_export = QPushButton("Export to Excel", objectName="GreyBtn")
        btn_rack_export.clicked.connect(self._on_export_rack_excel)
        rack_hdr.addWidget(btn_rack_export)
        rc_layout.addLayout(rack_hdr)

        self.tbl_rack = QTableWidget(0, 6)
        self.tbl_rack.setHorizontalHeaderLabels(
            ["Yarn", "Batch", "Producer", "Spools", "Total (kg)", "Locations"])
        self.tbl_rack.horizontalHeader().setStretchLastSection(True)
        self.tbl_rack.verticalHeader().setVisible(False)
        self.tbl_rack.setSelectionBehavior(QTableView.SelectRows)
        self.tbl_rack.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.tbl_rack.setItemDelegateForColumn(2, ProducerComboDelegate([], self.tbl_rack))
        self.tbl_rack.setStyleSheet(_qss)
        self.tbl_rack.setMinimumHeight(160)
        self.tbl_rack.itemChanged.connect(
            lambda item: self._on_group_item_changed(item, "_rack_filtered"))
        rc_layout.addWidget(self.tbl_rack)

        bl.addWidget(self.rack_content)

        content_layout.addWidget(body, 1)
        root.addWidget(FooterBar(), 0)

    def _refresh_sidebar(self):
        """Baut die Sidebar-Navigation neu auf, falls sich der Access-Level
        seit dem letzten Aufbau geändert hat, sonst nur die Badges (siehe
        ui/widgets/sidebar_nav.py::refresh_lazy_sidebar())."""
        import app_meta
        try:
            level = int((app_meta.current_user or {}).get("access_level") or 0)
        except Exception:
            level = 0
        sidebar_nav.refresh_lazy_sidebar(self, level)

    def showEvent(self, event):
        try:
            self._refresh_sidebar()
        except Exception:
            pass
        super().showEvent(event)

        if not self._writable:
            self.btn_select_all.setEnabled(False)
            self.btn_new_spool.setEnabled(False)
            self.btn_new_producer.setEnabled(False)
            self.btn_add_to_queue.setEnabled(False)
            self.btn_discard.setEnabled(False)
            self.btn_save.setEnabled(False)
            self.btn_remove_from_queue.setEnabled(False)
            self.btn_print_labels.setEnabled(False)
            self.btn_stock_take.setEnabled(False)
            self.btn_stock_take.setToolTip("No write access (read-only).")
            self.btn_new_spool.setToolTip("No write access (read-only).")
            self.btn_new_producer.setToolTip("No write access (read-only).")
            self.btn_add_to_queue.setToolTip("No write access (read-only).")
            self.btn_discard.setToolTip("No write access (read-only).")
            self.btn_save.setToolTip("No write access (read-only).")
            self.btn_remove_from_queue.setToolTip("No write access (read-only).")
            self.btn_print_labels.setToolTip("No write access (read-only).")

    def _toggle_detail_section(self):
        visible = not self.detail_content.isVisible()
        self.detail_content.setVisible(visible)
        self.btn_toggle_detail.setText("▾" if visible else "▸")

    def _toggle_queue_section(self):
        visible = not self.queue_content.isVisible()
        self.queue_content.setVisible(visible)
        self.btn_toggle_queue.setText("▾" if visible else "▸")

    def _toggle_rack_section(self):
        visible = not self.rack_content.isVisible()
        self.rack_content.setVisible(visible)
        self.btn_toggle_rack.setText("▾" if visible else "▸")

    def _on_toggle_select_all(self):
        if self.model_detail is None:
            return
        now_all_selected = self.model_detail.all_active_checked()
        self.model_detail.set_all_checked(not now_all_selected)
        self.btn_select_all.setText("Deselect all" if not now_all_selected else "Select all")

    # ---------------- Data ----------------

    def _resolve_yarn_cols(self):
        cmap = get_columns_map(self.YARN_TABLE)
        self._yarn_id_col = _resolve_field(["ID"], cmap) or "ID"
        self._yarn_name_col = _resolve_field(
            ["Name", "Bezeichnung", "YarnName", "Material"], cmap)
        self._yarn_minstock_col = _resolve_field(["MinStock"], cmap)
        self._yarn_source_trial_col = _resolve_field(["SourceTrialID"], cmap)

    def reload_data(self):
        if not table_exists(self.YARN_TABLE) or not table_exists(self.SPOOL_TABLE):
            QMessageBox.warning(
                self, "Yarn Stock",
                f"Table {self.YARN_TABLE} or {self.SPOOL_TABLE} is missing in the database.")
            return
        self._resolve_yarn_cols()
        if not self._yarn_name_col:
            QMessageBox.warning(self, "Yarn Stock", "Could not determine the name field of tblYarn.")
            return

        # Halbfabrikat-"Schatten"-Garne (Multimaschinen-Ply-Verknüpfung) sind
        # kein echter Lagerbestand und sollen hier nicht auftauchen.
        _where = f" WHERE [{self._yarn_source_trial_col}] IS NULL" if self._yarn_source_trial_col else ""
        yrows = fetch_all(
            f"SELECT [{self._yarn_id_col}] AS YarnID, [{self._yarn_name_col}] AS YarnName"
            + (f", [{self._yarn_minstock_col}] AS MinStock" if self._yarn_minstock_col else "")
            + f" FROM {self.YARN_TABLE}{_where} ORDER BY [{self._yarn_name_col}]"
        )
        yarn_name_map: Dict[int, str] = {}
        yarn_minstock_map: Dict[int, float] = {}
        self._yarn_choices = []
        for r in yrows:
            yid = int(r["YarnID"])
            yname = str(r.get("YarnName") or f"Yarn {yid}")
            yarn_name_map[yid] = yname
            self._yarn_choices.append((yid, yname))
            ms = r.get("MinStock")
            if ms is not None:
                try:
                    yarn_minstock_map[yid] = float(ms)
                except Exception:
                    pass

        self._producer_choices: List[Tuple[int, str]] = []
        self._producer_map: Dict[int, str] = {}
        if table_exists("tblYarnProducer"):
            try:
                for pr in fetch_all("SELECT ID, Name FROM tblYarnProducer ORDER BY Name"):
                    pid, pname = int(pr["ID"]), str(pr.get("Name") or "")
                    self._producer_choices.append((pid, pname))
                    self._producer_map[pid] = pname
            except Exception:
                pass

        spool_cmap = get_columns_map(self.SPOOL_TABLE)
        extra_cols = ""
        if "colour" in spool_cmap:
            extra_cols += ", [Colour]"
        if "producerid" in spool_cmap:
            extra_cols += ", [ProducerID]"
        srows = fetch_all(
            f"SELECT [ID], [YarnID], [Charge], [WeightKg], [Status], [Location], "
            f"[ReceivedDate], [DiscardedDate]{extra_cols} FROM {self.SPOOL_TABLE}"
        )

        groups: Dict[Tuple[int, str], List[Dict]] = {}
        for r in srows:
            yid = r.get("YarnID")
            if yid is None:
                continue
            yid = int(yid)
            charge = r.get("Charge") or ""
            groups.setdefault((yid, charge), []).append(r)

        self._all_spools = srows
        self._yarn_name_map = yarn_name_map
        self._yarn_minstock_map = yarn_minstock_map

        # Status gilt PRO GARN (Summe ueber alle Batches), nicht pro Batch
        # (Nutzerentscheid 2026-10-13, "muss global in TrippleT so sein").
        yarn_total_kg: Dict[int, float] = {}
        for (yid, _charge), spools in groups.items():
            yarn_total_kg[yid] = yarn_total_kg.get(yid, 0.0) + sum(
                float(s.get("WeightKg") or 0) for s in spools if s.get("Status") == "in stock")
        yarn_status: Dict[int, str] = {}
        for yid, ykg in yarn_total_kg.items():
            ms = yarn_minstock_map.get(yid)
            if ykg <= 0:
                yarn_status[yid] = "Empty"
            elif ms is not None and ykg < ms:
                yarn_status[yid] = "Low"
            else:
                yarn_status[yid] = "OK"
        status_color = {"Empty": "#FCEBEB", "Low": "#FAEEDA", "OK": "#EAF3DE"}
        self._yarn_status = yarn_status
        self._yarn_total_kg = yarn_total_kg

        self._overview = []
        for (yid, charge), spools in sorted(
                groups.items(), key=lambda kv: (yarn_name_map.get(kv[0][0], ""), kv[0][1])):
            active = [s for s in spools if s.get("Status") == "in stock"]
            if not active:
                # Aufgebrauchte Batch (keine Spule mehr am Lager) - nicht anzeigen
                # (Nutzerentscheid 2026-10-13). Ein komplett leeres Garn
                # verschwindet damit ganz aus der Uebersicht; Hinweis kommt dann
                # nur noch ueber die Glocke und Manage Yarn (0 kg).
                continue
            total_kg = sum(float(s.get("WeightKg") or 0) for s in active)
            locations = sorted({(s.get("Location") or "").strip() for s in active if s.get("Location")})
            locations_disp = " / ".join(locations) if locations else "–"
            producer_ids = sorted({int(s["ProducerID"]) for s in active if s.get("ProducerID")})
            producers_disp = " / ".join(
                self._producer_map.get(pid, f"#{pid}") for pid in producer_ids) if producer_ids else "–"
            status = yarn_status[yid]
            self._overview.append({
                "YarnID": yid, "Charge": charge,
                "YarnName": yarn_name_map.get(yid, f"Yarn {yid}"),
                "Count": len(active), "TotalKg": total_kg,
                "YarnTotalKg": yarn_total_kg[yid],
                "MinStock": yarn_minstock_map.get(yid),
                "Locations": locations_disp,
                "Producers": producers_disp,
                "ProducerIDs": set(producer_ids),
                "Status": status, "Color": status_color[status],
            })

        prev_selected = self._selected_group
        self._render_overview()

        restored = False
        if prev_selected is not None:
            prev_yarn_id, prev_charge = prev_selected
            row_idx = next(
                (i for i, g in enumerate(self._overview_filtered)
                 if g["YarnID"] == prev_yarn_id and (g["Charge"] or "") == (prev_charge or "")),
                None,
            )
            if row_idx is not None:
                self.tbl_overview.selectRow(row_idx)
                self.tbl_overview.scrollToItem(self.tbl_overview.item(row_idx, 0))
                # Nicht nur auf das itemSelectionChanged-Signal verlassen (das
                # feuert u.U. nicht zuverlaessig, wenn Qt die Zeile nach dem
                # Tabellen-Rebuild bereits intern als selektiert fuehrt) -
                # Detailtabelle explizit und garantiert mit den frisch
                # geladenen Spulen (inkl. gerade neu hinzugefuegter) fuellen.
                self._on_overview_selected()
                restored = True

        if not restored:
            self._selected_group = None
            # Auch die sichtbare Markierung aufheben - sonst bleibt die Zeile
            # optisch selektiert, ein spaeteres selectRow() auf dieselbe Zeile
            # loest kein itemSelectionChanged aus und der Spools-Bereich bliebe leer.
            self.tbl_overview.blockSignals(True)
            self.tbl_overview.clearSelection()
            self.tbl_overview.blockSignals(False)
            self._render_detail([])
            self.lbl_detail_title.setText("<b>Spools</b> — select yarn/batch above")

        self._reload_label_queue()
        self._apply_rack_filter()

        try:
            from ui.notifications import (
                create_yarn_stock_notifications,
                expire_yarn_stock_notifications_for_yarns,
                remove_legacy_batch_yarn_stock_notifications,
            )
            # Einmalige Umstellung: alte Meldungen pro Garn/Batch (vor
            # 2026-10-13) entfernen - ab jetzt gibt es eine Meldung pro Garn.
            remove_legacy_batch_yarn_stock_notifications()
            low_or_empty = [yid for yid, st in yarn_status.items() if st in ("Low", "Empty")]
            ok_now = [yid for yid, st in yarn_status.items() if st == "OK"]
            if low_or_empty:
                create_yarn_stock_notifications([
                    {"YarnID": yid, "YarnName": yarn_name_map.get(yid, f"Yarn {yid}"),
                     "Charge": None, "Status": yarn_status[yid]}
                    for yid in low_or_empty
                ])
            if ok_now:
                # Räumt Notifications für inzwischen wieder aufgefüllte Garne
                # weg, sonst würde ein erneuter Rückgang unter den Schwellwert
                # nie wieder benachrichtigen (Dedup über die Message, siehe
                # create_yarn_stock_notifications()).
                expire_yarn_stock_notifications_for_yarns(ok_now)
        except Exception:
            pass  # Notification-Feature ist optional, darf reload_data nie blockieren

    def _render_overview(self):
        search = getattr(self, "txt_search", None)
        search_txt = search.text().strip().lower() if search else ""
        status_cmb = getattr(self, "cmb_status_filter", None)
        status_filter = status_cmb.currentText() if status_cmb else "All statuses"

        self._overview_filtered = [
            g for g in self._overview
            if (not search_txt or search_txt in g["YarnName"].lower() or search_txt in (g["Charge"] or "").lower())
            and (status_filter == "All statuses" or g["Status"] == status_filter)
        ]

        self._render_guard = True
        self.tbl_overview.setRowCount(len(self._overview_filtered))
        for r, g in enumerate(self._overview_filtered):
            ms = g.get("MinStock")
            items = [
                g["YarnName"], g["Charge"] or "–", g["Producers"],
                str(g["Count"]), f"{g['TotalKg']:.2f}", f"{g['YarnTotalKg']:.2f}",
                f"{ms:g}" if ms is not None else "–",
                g["Status"], g["Locations"],
            ]
            pids = g.get("ProducerIDs") or set()
            single_pid = next(iter(pids)) if len(pids) == 1 else None
            can_edit_ms = bool(self._yarn_minstock_col) and app_meta.can_edit_min_stock()
            for c, txt in enumerate(items):
                it = QTableWidgetItem(txt)
                editable = ((c in (self.OV_COL_BATCH, self.OV_COL_PRODUCER) and self._writable)
                            or (c == self.OV_COL_MINSTOCK and can_edit_ms))
                if not editable:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                if c == self.OV_COL_PRODUCER:
                    it.setData(Qt.EditRole, single_pid)
                    it.setData(Qt.DisplayRole, txt)  # EditRole-Write ueberschreibt sonst den Anzeigetext
                if c in self.OV_NUMERIC_COLS:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it.setBackground(QColor(g["Color"]))
                self.tbl_overview.setItem(r, c, it)
        self.tbl_overview.resizeColumnsToContents()
        self._render_guard = False

    def _apply_overview_filter(self):
        self._render_overview()

    def _apply_rack_filter(self):
        prefix = self.txt_rack.text().strip().upper()
        self._rack_filtered: List[Dict] = []
        if prefix:
            groups: Dict[Tuple[int, str], Dict] = {}
            for s in getattr(self, "_all_spools", []):
                if s.get("Status") != "in stock":
                    continue
                loc = (s.get("Location") or "").strip().upper()
                if not loc.startswith(prefix):
                    continue
                yid = s.get("YarnID")
                if yid is None:
                    continue
                key = (int(yid), s.get("Charge") or "")
                g = groups.setdefault(key, {
                    "YarnID": int(yid),
                    "Yarn": self._yarn_name_map.get(int(yid), f"Yarn {yid}"),
                    "Batch": s.get("Charge") or "",
                    "Count": 0, "Weight": 0.0, "Locations": set(), "ProducerIDs": set(),
                })
                g["Count"] += 1
                g["Weight"] += float(s.get("WeightKg") or 0)
                if s.get("Location"):
                    g["Locations"].add(s["Location"].strip())
                if s.get("ProducerID"):
                    g["ProducerIDs"].add(int(s["ProducerID"]))

            for g in groups.values():
                g["LocationsDisp"] = " / ".join(sorted(g["Locations"]))
                g["ProducersDisp"] = " / ".join(
                    self._producer_map.get(pid, f"#{pid}") for pid in sorted(g["ProducerIDs"])) or "–"
            self._rack_filtered = sorted(groups.values(), key=lambda g: (g["Yarn"], g["Batch"]))

        self._render_guard = True
        self.tbl_rack.setRowCount(len(self._rack_filtered))
        for r, it in enumerate(self._rack_filtered):
            vals = [it["Yarn"], it["Batch"] or "–", it["ProducersDisp"], str(it["Count"]),
                    f"{it['Weight']:.2f}", it["LocationsDisp"]]
            pids = it.get("ProducerIDs") or set()
            single_pid = next(iter(pids)) if len(pids) == 1 else None
            for c, txt in enumerate(vals):
                item = QTableWidgetItem(txt)
                editable = c in (1, 2) and self._writable
                if not editable:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if c == 2:
                    item.setData(Qt.EditRole, single_pid)
                    item.setData(Qt.DisplayRole, txt)  # EditRole-Write ueberschreibt sonst den Anzeigetext
                if c in (3, 4):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl_rack.setItem(r, c, item)
        self.tbl_rack.resizeColumnsToContents()
        self._render_guard = False

    def _on_export_rack_excel(self):
        rows = getattr(self, "_rack_filtered", [])
        prefix = self.txt_rack.text().strip().upper()
        if not prefix:
            QMessageBox.information(self, "Export to Excel", "Please enter a rack letter first.")
            return
        if not rows:
            QMessageBox.information(self, "Export to Excel", f"No spools found in rack '{prefix}'.")
            return
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        except ImportError:
            QMessageBox.critical(
                self, "Export to Excel",
                "The 'openpyxl' package is not installed. Run:\npip install openpyxl")
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save rack overview", f"rack_{prefix}.xlsx", "Excel Files (*.xlsx)")
        if not out_path:
            return

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Rack {prefix}"
        headers = ["Yarn", "Batch", "Producer", "Spools", "Total (kg)", "Locations"]
        ws.append(headers)
        hdr_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = hdr_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        thin = Side(style="thin", color="CCCCCC")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        for it in rows:
            ws.append([it["Yarn"], it["Batch"] or "–", it["ProducersDisp"], it["Count"],
                       round(it["Weight"], 2), it["LocationsDisp"]])
            for c in range(1, len(headers) + 1):
                cell = ws.cell(row=ws.max_row, column=c)
                cell.border = border
                if c in (4, 5):
                    cell.alignment = Alignment(horizontal="right")

        widths = [30, 16, 20, 10, 12, 24]
        for c, w in enumerate(widths, start=1):
            ws.column_dimensions[chr(64 + c)].width = w
        ws.freeze_panes = "A2"
        ws.print_options.horizontalCentered = True
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True

        try:
            wb.save(out_path)
        except Exception as e:
            QMessageBox.critical(self, "Export to Excel", f"Failed to save: {e}")
            return
        log_usage_event("feature", "yarn_stock_export_excel", "rack")
        QMessageBox.information(self, "Export to Excel", f"Saved to:\n{out_path}")

    def _on_group_item_changed(self, item: QTableWidgetItem, filtered_attr: str) -> None:
        """Reagiert auf Inline-Edits in der Batch- oder Producer-Spalte von
        Overview/Rack-Tabelle. Aendert das Feld fuer ALLE Spulen dieses
        Garns mit diesem (alten) Batch - inklusive ausgebuchter, fuer
        konsistente Historie."""
        if getattr(self, "_render_guard", False):
            return
        if not self._writable:
            return
        col = item.column()
        if col == self.OV_COL_MINSTOCK and filtered_attr == "_overview_filtered":
            self._on_minstock_edited(item)
            return
        if col not in (1, 2):
            return
        row = item.row()
        rows = getattr(self, filtered_attr, [])
        if row >= len(rows):
            return
        g = rows[row]
        yarn_id = g.get("YarnID")
        old_charge = g.get("Batch") if g.get("Batch") is not None else g.get("Charge")
        old_charge = old_charge or ""
        if yarn_id is None:
            return

        # Guard setzen BEVOR wir irgendwas tun: der Delegate ruft setModelData
        # zweimal auf (EditRole fuer die ID, danach DisplayRole fuer den
        # Namen) - das zweite setData wuerde sonst denselben Handler nochmal
        # triggern. Ausserdem reload_data() erst verzoegert (QTimer) ausfuehren,
        # sonst wird die Tabelle noch waehrend der Delegate-Ausfuehrung neu
        # aufgebaut und der zweite setData-Aufruf (Anzeigetext) laeuft ins Leere.
        self._render_guard = True
        # Betroffene Spulen (inkl. ausgebuchter) fuers Protokoll VOR dem Update merken
        affected = [sp for sp in getattr(self, "_all_spools", [])
                    if int(sp.get("YarnID") or -1) == int(yarn_id) and (sp.get("Charge") or "") == old_charge]
        try:
            if col == 1:
                new_charge = item.text().strip()
                if new_charge == "–":
                    new_charge = ""
                execute(
                    f"UPDATE {self.SPOOL_TABLE} SET [Charge] = ? "
                    f"WHERE [YarnID] = ? AND ([Charge] = ? OR (? = '' AND ([Charge] IS NULL OR [Charge] = '')))",
                    [new_charge or None, yarn_id, old_charge, old_charge],
                )
                if new_charge != old_charge:
                    yarn_spool_log.log_spool_changes(
                        {"SpoolID": sp["ID"], "Action": yarn_spool_log.UPDATED, "Field": "Batch",
                         "Old": old_charge or None, "New": new_charge or None} for sp in affected)
            else:
                new_pid = item.data(Qt.EditRole)
                execute(
                    f"UPDATE {self.SPOOL_TABLE} SET [ProducerID] = ? "
                    f"WHERE [YarnID] = ? AND ([Charge] = ? OR (? = '' AND ([Charge] IS NULL OR [Charge] = '')))",
                    [new_pid, yarn_id, old_charge, old_charge],
                )
                pmap = getattr(self, "_producer_map", {})
                yarn_spool_log.log_spool_changes(
                    {"SpoolID": sp["ID"], "Action": yarn_spool_log.UPDATED, "Field": "Producer",
                     "Old": pmap.get(sp.get("ProducerID")) if sp.get("ProducerID") else None,
                     "New": pmap.get(new_pid) if new_pid else None}
                    for sp in affected if sp.get("ProducerID") != new_pid)
        except Exception as e:
            QMessageBox.critical(self, "Edit", f"Failed to update: {e}")
        QTimer.singleShot(0, self._finish_group_edit)

    def _on_minstock_edited(self, item: QTableWidgetItem) -> None:
        """Mindestbestand (tblYarn.MinStock) direkt in der Overview aendern -
        gilt fuer das ganze Garn (alle Batch-Zeilen). Nur Superuser
        (app_meta.can_edit_min_stock(), Live-Check statt nur Item-Flags)."""
        rows = getattr(self, "_overview_filtered", [])
        if item.row() >= len(rows) or not self._yarn_minstock_col:
            return
        g = rows[item.row()]
        if not app_meta.can_edit_min_stock():
            QMessageBox.information(self, "Min. stock", "Only superusers can change the minimum stock.")
            QTimer.singleShot(0, self.reload_data)
            return
        raw = (item.text() or "").strip().replace(",", ".")
        if raw in ("", "–", "-"):
            new_val = None
        else:
            try:
                new_val = float(raw)
            except ValueError:
                new_val = -1.0
            if new_val < 0:
                QMessageBox.warning(
                    self, "Min. stock",
                    "Please enter a number of kg (0 or more), or leave the field empty for no minimum.")
                QTimer.singleShot(0, self.reload_data)
                return
        if new_val == g.get("MinStock"):
            return
        self._render_guard = True
        try:
            execute(
                f"UPDATE {self.YARN_TABLE} SET [{self._yarn_minstock_col}] = ? "
                f"WHERE [{self._yarn_id_col}] = ?",
                [new_val, g["YarnID"]],
            )
            log_usage_event("feature", "yarn_stock_edit_min_stock")
        except Exception as e:
            QMessageBox.critical(self, "Min. stock", f"Failed to update: {e}")
        QTimer.singleShot(0, self._finish_group_edit)

    def _finish_group_edit(self) -> None:
        self._render_guard = False
        self.reload_data()

    def _on_export_excel(self):
        rows = getattr(self, "_overview_filtered", self._overview)
        if not rows:
            QMessageBox.information(self, "Export to Excel", "Nothing to export.")
            return
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        except ImportError:
            QMessageBox.critical(
                self, "Export to Excel",
                "The 'openpyxl' package is not installed. Run:\npip install openpyxl")
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save yarn stock overview", "yarn_stock_overview.xlsx", "Excel Files (*.xlsx)")
        if not out_path:
            return

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Yarn Stock"

        headers = list(self.OV_HEADERS)
        ws.append(headers)
        hdr_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        for c, cell in enumerate(ws[1], start=1):
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = hdr_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        status_fill = {
            "OK": PatternFill(start_color="EAF3DE", end_color="EAF3DE", fill_type="solid"),
            "Low": PatternFill(start_color="FAEEDA", end_color="FAEEDA", fill_type="solid"),
            "Empty": PatternFill(start_color="FCEBEB", end_color="FCEBEB", fill_type="solid"),
        }
        thin = Side(style="thin", color="CCCCCC")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        for g in rows:
            ws.append([
                g["YarnName"], g["Charge"] or "–", g["Producers"], g["Count"],
                round(g["TotalKg"], 2), round(g["YarnTotalKg"], 2), g.get("MinStock"),
                g["Status"], g["Locations"],
            ])
            r = ws.max_row
            fill = status_fill.get(g["Status"])
            for c in range(1, len(headers) + 1):
                cell = ws.cell(row=r, column=c)
                cell.border = border
                if fill:
                    cell.fill = fill
                if c in (4, 5, 6, 7):
                    cell.alignment = Alignment(horizontal="right")

        widths = [30, 16, 20, 10, 12, 14, 14, 10, 24]
        for c, w in enumerate(widths, start=1):
            ws.column_dimensions[chr(64 + c)].width = w
        ws.freeze_panes = "A2"
        ws.print_options.horizontalCentered = True
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True

        try:
            wb.save(out_path)
        except Exception as e:
            QMessageBox.critical(self, "Export to Excel", f"Failed to save: {e}")
            return
        log_usage_event("feature", "yarn_stock_export_excel", "overview")
        QMessageBox.information(self, "Export to Excel", f"Saved to:\n{out_path}")

    def _on_detail_clicked(self, index):
        """Togglet die Checkbox explizit bei jedem Klick in Spalte 0 - unabhaengig
        vom eingebauten Qt-Indikator-Hit-Test (der je nach Spaltenbreite/Style
        nicht zuverlaessig reagiert)."""
        if index.column() != 0 or self.model_detail is None or not self._writable:
            return
        row = self.model_detail._rows[index.row()]
        if row.get("Status") != "in stock":
            return
        current = self.model_detail.data(index, Qt.CheckStateRole)
        new_state = Qt.Unchecked if current == Qt.Checked else Qt.Checked
        self.model_detail.setData(index, new_state, Qt.CheckStateRole)

    def _on_detail_double_clicked(self, index):
        """Gives explicit feedback in read-only mode instead of silently doing nothing."""
        if self._writable or self.model_detail is None:
            return
        row = self.model_detail._rows[index.row()] if 0 <= index.row() < len(self.model_detail._rows) else None
        if row is not None and row.get("Status") != "in stock":
            return  # discarded spools are never editable anyway, no need for a hint
        QMessageBox.information(
            self, "View only",
            "You don't have write access to edit spools (read-only).")

    def goto_yarn_batch(self, yarn_id: int, charge: Optional[str]) -> bool:
        """Springt zur Garn/Batch-Zeile in der Übersicht und klappt Spools
        auf. Wiederverwendet von _on_goto_spool() und von aussen (z.B. beim
        Klick auf eine Low-Stock-Notification). Gibt True zurück, wenn die
        Gruppe gefunden und ausgewählt wurde."""
        charge = charge or ""

        # Filter zuruecksetzen, damit die Gruppe garantiert sichtbar ist
        self.txt_search.blockSignals(True)
        self.txt_search.clear()
        self.txt_search.blockSignals(False)
        self.cmb_status_filter.blockSignals(True)
        self.cmb_status_filter.setCurrentIndex(0)
        self.cmb_status_filter.blockSignals(False)
        self._render_overview()

        group_row = next(
            (i for i, g in enumerate(self._overview_filtered)
             if g["YarnID"] == yarn_id and (g["Charge"] or "") == charge), None)
        if group_row is None:
            # Meldungen gelten seit 2026-10-13 pro Garn (ohne Batch) - dann
            # zur ersten sichtbaren Batch-Zeile dieses Garns springen.
            group_row = next(
                (i for i, g in enumerate(self._overview_filtered) if g["YarnID"] == yarn_id), None)
        if group_row is None:
            return False

        self.tbl_overview.selectRow(group_row)
        self.tbl_overview.scrollToItem(self.tbl_overview.item(group_row, 0))
        g = self._overview_filtered[group_row]
        if self._selected_group != (g["YarnID"], g["Charge"]):
            # selectRow() feuert kein Signal, wenn die Zeile schon markiert war
            self._on_overview_selected()

        if not self.detail_content.isVisible():
            self._toggle_detail_section()
        return True

    def _on_goto_spool(self):
        if not self._confirm_pending_changes():
            return
        text = self.txt_goto_spool.text()
        spool_id = parse_spool_input(text)
        if spool_id is None:
            QMessageBox.information(
                self, "Go to spool", "Please enter a spool number (e.g. 213) or scan a spool label.")
            return
        spool = next((s for s in getattr(self, "_all_spools", []) if s.get("ID") == spool_id), None)
        if spool is None:
            QMessageBox.information(self, "Go to spool", f"Spool #{spool_id} not found.")
            return
        if spool.get("Status") != "in stock":
            box = QMessageBox(QMessageBox.Information, "Go to spool",
                              f"Spool #{spool_id} is discarded and no longer shown in the active list.",
                              parent=self)
            btn_hist = box.addButton("Show history", QMessageBox.ActionRole)
            box.addButton(QMessageBox.Close)
            box.exec()
            if box.clickedButton() is btn_hist:
                self._show_history_for(spool_id)
            return

        yarn_id = int(spool.get("YarnID") or -1)
        charge = spool.get("Charge") or ""
        if not self.goto_yarn_batch(yarn_id, charge):
            QMessageBox.information(self, "Go to spool", f"Could not locate the group for spool #{spool_id}.")
            return

        if self.model_detail is not None:
            spool_row = next(
                (i for i, r in enumerate(self.model_detail._rows) if r.get("ID") == spool_id), None)
            if spool_row is not None:
                idx = self.model_detail.index(spool_row, 1)
                self.tbl_detail.setCurrentIndex(idx)
                self.tbl_detail.selectRow(spool_row)
                self.tbl_detail.scrollTo(idx)
                self.tbl_detail.selectRow(spool_row)
                self.tbl_detail.scrollTo(idx)

        # Eingabe markiert lassen: der naechste Scan/Tippvorgang ersetzt sie,
        # statt an die alte Nummer angehaengt zu werden.
        self.txt_goto_spool.setFocus()
        self.txt_goto_spool.selectAll()
        log_usage_event("feature", "yarn_stock_goto_spool",
                        "number" if text.strip().lstrip("#").strip().isdigit() else "label_scan")

    def _ask_pending_changes(self) -> Optional[str]:
        """Fragt bei ungespeicherten Aenderungen im Spools-Bereich nach.
        Rueckgabe "save" / "discard" / "cancel", oder None wenn nichts offen ist."""
        m = self.model_detail
        if m is None or not self._writable or not m.has_pending_changes():
            return None
        resp = QMessageBox.question(
            self, "Unsaved changes",
            "You have unsaved changes in the spool list.\nSave them before continuing?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if resp == QMessageBox.Save:
            return "save"
        if resp == QMessageBox.Discard:
            return "discard"
        return "cancel"

    def _confirm_pending_changes(self) -> bool:
        """Guard fuer Aktionen, die den Spools-Bereich neu aufbauen (Reload,
        New spool(s), Discard, Go to spool). True = Aktion darf weiterlaufen."""
        choice = self._ask_pending_changes()
        if choice is None:
            return True
        if choice == "cancel":
            return False
        if choice == "save":
            if self._write_pending_changes() is None:
                return False
            self.reload_data()
        else:
            self.model_detail.clear_pending_changes()
        return True

    def _reselect_overview_group(self, group: Optional[Tuple[int, str]]) -> None:
        """Waehlt `group` in der Overview aus, OHNE _on_overview_selected
        auszuloesen (fuer "Cancel" bei ungespeicherten Aenderungen)."""
        self.tbl_overview.blockSignals(True)
        try:
            self.tbl_overview.clearSelection()
            if group is not None:
                row_idx = next(
                    (i for i, g in enumerate(getattr(self, "_overview_filtered", []))
                     if g["YarnID"] == group[0] and (g["Charge"] or "") == (group[1] or "")),
                    None)
                if row_idx is not None:
                    self.tbl_overview.selectRow(row_idx)
        finally:
            self.tbl_overview.blockSignals(False)

    def _on_reload_clicked(self):
        if self._confirm_pending_changes():
            self.reload_data()

    def _on_overview_selected(self):
        rows = self.tbl_overview.selectionModel().selectedRows()
        if not rows:
            return
        idx = rows[0].row()
        src = getattr(self, "_overview_filtered", self._overview)
        if idx < 0 or idx >= len(src):
            return
        g = src[idx]
        new_group = (g["YarnID"], g["Charge"])
        if new_group != self._selected_group:
            choice = self._ask_pending_changes()
            if choice == "cancel":
                self._reselect_overview_group(self._selected_group)
                return
            if choice == "save":
                if self._write_pending_changes() is None:
                    self._reselect_overview_group(self._selected_group)
                    return
                # Frisch laden (Summen/Gewichte), danach die neu gewaehlte
                # Gruppe wiederherstellen - verzoegert, da wir gerade mitten im
                # itemSelectionChanged-Handler der Tabelle stecken.
                self._selected_group = new_group
                QTimer.singleShot(0, self.reload_data)
                return
            if choice == "discard":
                self.model_detail.clear_pending_changes()
        self._selected_group = new_group
        spools = [s for s in self._all_spools
                  if int(s.get("YarnID") or -1) == g["YarnID"] and (s.get("Charge") or "") == g["Charge"]
                  and s.get("Status") == "in stock"]
        spools.sort(key=lambda s: s.get("ID"))
        self._render_detail(spools)
        charge_disp = g["Charge"] or "(no batch)"
        self.lbl_detail_title.setText(f"<b>Spools</b> — {g['YarnName']} / {charge_disp}")

    def _render_detail(self, spools: List[Dict]):
        self.model_detail = SpoolTableModel(spools, self._writable, producer_map=getattr(self, "_producer_map", {}))
        self.tbl_detail.setModel(self.model_detail)
        self._producer_delegate = ProducerComboDelegate(getattr(self, "_producer_choices", []), self.tbl_detail)
        self.tbl_detail.setItemDelegateForColumn(5, self._producer_delegate)
        self.btn_select_all.setText("Select all")
        self.tbl_detail.resizeColumnsToContents()
        # Checkbox-Spalte hat keinen Text-Inhalt -> resizeColumnsToContents()
        # schrumpft sie sonst auf nahezu 0px, wodurch das Kaestchen nicht mehr
        # anklickbar ist. Feste, ausreichend breite Spalte erzwingen.
        self.tbl_detail.setColumnWidth(0, 32)

    # ---------------- Actions ----------------

    def _on_used_in(self):
        if self.model_detail is None:
            return
        spool_ids = self._ticked_or_selected_spool_ids()
        if not spool_ids:
            QMessageBox.information(self, "Used in", "Please tick or select at least one spool.")
            return
        log_usage_event("feature", "yarn_stock_used_in", str(len(spool_ids)))
        dlg = UsedInDialog(spool_ids, parent=self)
        dlg.exec()

    def _ticked_or_selected_spool_ids(self) -> List[int]:
        """Angehakte UND markierte Spulen (Discard/Label queue arbeiten mit
        Haekchen - Used in/History sollen sich nicht anders verhalten)."""
        if self.model_detail is None:
            return []
        spool_ids = list(self.model_detail.checked_spool_ids())
        for idx in self.tbl_detail.selectionModel().selectedRows():
            r = idx.row()
            if 0 <= r < len(self.model_detail._rows):
                sid = self.model_detail._rows[r]["ID"]
                if sid not in spool_ids:
                    spool_ids.append(sid)
        return spool_ids

    def _on_history(self):
        spool_ids = self._ticked_or_selected_spool_ids()
        if spool_ids:
            title = "Spool(s) " + ", ".join(f"#{i}" for i in spool_ids)
        elif self._selected_group is not None:
            # Ganze Batch inkl. ausgebuchter Spulen - so laesst sich auch
            # "wer hat das ausgebucht?" beantworten.
            yid, charge = self._selected_group
            spool_ids = [int(s["ID"]) for s in getattr(self, "_all_spools", [])
                         if int(s.get("YarnID") or -1) == yid and (s.get("Charge") or "") == (charge or "")]
            title = (f"{self._yarn_name_map.get(yid, f'Yarn {yid}')} / {charge or '(no batch)'} "
                     f"— all spools incl. discarded")
        else:
            QMessageBox.information(self, "History", "Please select a yarn/batch or spools first.")
            return
        log_usage_event("feature", "yarn_stock_history", str(len(spool_ids)))
        SpoolHistoryDialog(spool_ids, title, parent=self).exec()

    def _on_stock_take(self):
        if not self._writable:
            return
        if not self._confirm_pending_changes():
            return
        # Inventur-Runde (Uebersicht pro Lagerplatz, ui/widgets/stock_take_round_dialog.py);
        # die Spulen werden vor jeder Platz-Pruefung frisch geladen (= Soll-Liste).
        from ui.widgets.stock_take_round_dialog import StockTakeRoundDialog

        def _fresh_spools():
            self.reload_data()
            return getattr(self, "_all_spools", []), getattr(self, "_yarn_name_map", {})
        dlg = StockTakeRoundDialog(_fresh_spools, writable=self._writable,
                                   single_location_prefix=self.txt_rack.text(), parent=self)
        dlg.exec()
        if dlg.changed:
            self.reload_data()

    def _show_history_for(self, spool_id: int) -> None:
        SpoolHistoryDialog([spool_id], f"Spool #{spool_id}", parent=self).exec()

    def _on_new_producer(self):
        if not self._writable:
            return
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New producer", "Producer name:")
        if not (ok and name.strip()):
            return
        new_id = create_producer(name)
        if new_id is None:
            QMessageBox.warning(
                self, "New producer",
                "Could not create producer — table tblYarnProducer might be missing.")
            return
        QMessageBox.information(self, "New producer", f"Producer '{name.strip()}' created.")
        self.reload_data()

    def _on_new_spool(self):
        if not self._writable:
            return
        if not self._confirm_pending_changes():
            return
        prev_group = self._selected_group
        preselect = prev_group[0] if prev_group else None
        dlg = NewSpoolDialog(self._yarn_choices, self, preselect_yarn_id=preselect)
        if prev_group and prev_group[1]:
            dlg.txt_charge.setText(prev_group[1])

        # Nutzerwunsch 2026-10-13: waehrend des Anlegens keine Overview-Auswahl,
        # Spools-Bereich leer - nach Erfolg springt die Auswahl auf das Garn/
        # die Batch der neuen Spulen (siehe unten). Vorbelegung oben nutzt
        # bewusst noch die alte Auswahl (prev_group).
        self._clear_overview_selection()

        if dlg.exec() != QDialog.Accepted:
            self._restore_overview_selection(prev_group)
            return
        vals = dlg.values()
        if vals["YarnID"] is None:
            self._restore_overview_selection(prev_group)
            return
        user_id = _current_user_id()
        today = date.today().isoformat()
        spool_cmap = get_columns_map(self.SPOOL_TABLE)
        cols = ["YarnID", "Charge", "WeightKg", "Status", "Location", "ReceivedDate", "UserID"]
        base_vals: List[Any] = [vals["YarnID"], vals["Charge"], vals["WeightKg"], "in stock",
                                 vals["Location"], today, user_id]
        if "colour" in spool_cmap:
            cols.append("Colour")
            base_vals.append(vals.get("Colour"))
        if "producerid" in spool_cmap:
            cols.append("ProducerID")
            base_vals.append(vals.get("ProducerID"))
        cols.append("GlobalID")
        ph = ",".join(["?"] * len(cols))
        inserted = 0
        new_ids: List[int] = []
        try:
            for _ in range(vals["Count"]):
                new_id = execute_insert(
                    f"INSERT INTO {self.SPOOL_TABLE} ({','.join('['+c+']' for c in cols)}) "
                    f"VALUES ({ph})",
                    base_vals + [new_global_id()],
                )
                inserted += 1
                if new_id:
                    new_ids.append(int(new_id))
        except Exception as e:
            QMessageBox.critical(self, "New spool(s)", f"Failed to create: {e}")
            if inserted == 0:
                self._restore_overview_selection(prev_group)
                return
            # Teilweise angelegt: trotzdem neu laden und zur Gruppe springen,
            # damit die bereits angelegten Spulen sichtbar sind.
        log_usage_event("feature", "yarn_stock_new_spools", str(inserted))
        summary = (f"{float(vals['WeightKg']):.2f} kg, location {vals['Location'] or '–'}, "
                   f"batch {vals['Charge'] or '–'}")
        yarn_spool_log.log_spool_changes(
            {"SpoolID": sid, "Action": yarn_spool_log.CREATED, "New": summary} for sid in new_ids)
        if vals.get("AddToLabelQueue") and new_ids:
            queued = self._queue_labels(new_ids, "New spool(s)")
            if queued:
                log_usage_event("feature", "yarn_stock_add_to_label_queue", f"{queued} (new spools)")
        self.reload_data()
        if self.goto_yarn_batch(int(vals["YarnID"]), vals["Charge"] or ""):
            # Detailtabelle explizit fuellen (Signal feuert nach dem Rebuild
            # nicht zuverlaessig, siehe reload_data()).
            self._on_overview_selected()
            self.tbl_overview.setFocus()

    def _clear_overview_selection(self) -> None:
        """Hebt die Auswahl in der Overview auf und leert den Spools-Bereich."""
        self.tbl_overview.clearSelection()
        self._selected_group = None
        self._render_detail([])
        self.lbl_detail_title.setText("<b>Spools</b> — select yarn/batch above")

    def _restore_overview_selection(self, group: Optional[Tuple[int, str]]) -> None:
        """Waehlt `group` (YarnID, Charge) in der Overview wieder aus, sofern es
        im aktuell gefilterten Stand sichtbar ist - Filter bleiben unangetastet."""
        if group is None:
            return
        yarn_id, charge = group
        row_idx = next(
            (i for i, g in enumerate(getattr(self, "_overview_filtered", []))
             if g["YarnID"] == yarn_id and (g["Charge"] or "") == (charge or "")),
            None,
        )
        if row_idx is None:
            return
        self.tbl_overview.selectRow(row_idx)
        self.tbl_overview.scrollToItem(self.tbl_overview.item(row_idx, 0))
        self._on_overview_selected()

    def _on_discard(self):
        if not self._writable or self.model_detail is None:
            return
        ids = self.model_detail.checked_spool_ids()
        if not ids:
            QMessageBox.information(self, "Discard", "Please check at least one spool.")
            return
        # ids vorher gemerkt: ein "Save" im Guard laedt neu und verwirft die Haekchen.
        if not self._confirm_pending_changes():
            return
        resp = QMessageBox.question(
            self, "Discard",
            f"Mark {len(ids)} spool(s) as discarded?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if resp != QMessageBox.Yes:
            return
        today = date.today().isoformat()
        n = 0
        try:
            for sid in ids:
                n += execute(
                    f"UPDATE {self.SPOOL_TABLE} SET [Status] = 'discarded', [DiscardedDate] = ? "
                    f"WHERE [ID] = ?",
                    [today, sid],
                )
        except Exception as e:
            QMessageBox.critical(self, "Discard", f"Failed to discard: {e}")
            return
        log_usage_event("feature", "yarn_stock_discard", str(n))
        yarn_spool_log.log_spool_changes(
            {"SpoolID": sid, "Action": yarn_spool_log.DISCARDED, "Field": "Status",
             "Old": "in stock", "New": "discarded"} for sid in ids)
        QMessageBox.information(self, "Discard", f"{n} spool(s) discarded.")
        self.reload_data()

    def _on_save(self):
        if not self._writable or self.model_detail is None:
            return
        if not self.model_detail.has_pending_changes():
            QMessageBox.information(self, "Save Changes", "No changes.")
            return
        n = self._write_pending_changes()
        if n is None:
            return
        QMessageBox.information(self, "Save Changes", f"{n} spool(s) updated.")
        self.reload_data()

    def _write_pending_changes(self) -> Optional[int]:
        """Schreibt die offenen Aenderungen des Spools-Bereichs in die DB.
        Anzahl geaenderter Felder, oder None bei Fehler (Meldung bereits gezeigt).
        Laedt NICHT neu - das entscheidet der Aufrufer."""
        weight_updates = self.model_detail.dirty_weight_updates()
        loc_updates = self.model_detail.dirty_location_updates()
        colour_updates = self.model_detail.dirty_colour_updates()
        producer_updates = self.model_detail.dirty_producer_updates()
        n = 0
        try:
            for sid, w in weight_updates.items():
                n += execute(
                    f"UPDATE {self.SPOOL_TABLE} SET [WeightKg] = ? WHERE [ID] = ?",
                    [w, sid],
                )
            for sid, loc in loc_updates.items():
                n += execute(
                    f"UPDATE {self.SPOOL_TABLE} SET [Location] = ? WHERE [ID] = ?",
                    [loc or None, sid],
                )
            for sid, col in colour_updates.items():
                n += execute(
                    f"UPDATE {self.SPOOL_TABLE} SET [Colour] = ? WHERE [ID] = ?",
                    [col or None, sid],
                )
            for sid, pid in producer_updates.items():
                n += execute(
                    f"UPDATE {self.SPOOL_TABLE} SET [ProducerID] = ? WHERE [ID] = ?",
                    [pid, sid],
                )
        except Exception as e:
            QMessageBox.critical(self, "Save Changes", f"Failed to save: {e}")
            return None
        self._log_pending_changes(weight_updates, loc_updates, colour_updates, producer_updates)
        self.model_detail.clear_pending_changes()
        log_usage_event("feature", "yarn_stock_save_changes", str(n))
        return n

    def _log_pending_changes(self, weight_updates, loc_updates, colour_updates, producer_updates) -> None:
        """Protokolliert gespeicherte Feldaenderungen (nur echte Aenderungen)."""
        rows_by_id = {r["ID"]: r for r in self.model_detail._rows}
        pmap = getattr(self, "_producer_map", {})
        entries = []

        def add(sid, field, old, new):
            if (old or None) == (new or None):
                return
            entries.append({"SpoolID": sid, "Action": yarn_spool_log.UPDATED,
                            "Field": field, "Old": old, "New": new})

        for sid, w in weight_updates.items():
            old = rows_by_id.get(sid, {}).get("WeightKg")
            old_f = float(old) if old is not None else None
            if old_f is None or abs(old_f - float(w)) > 1e-9:
                entries.append({"SpoolID": sid, "Action": yarn_spool_log.UPDATED,
                                "Field": "Weight (kg)", "Old": old_f, "New": float(w)})
        for sid, loc in loc_updates.items():
            add(sid, "Location", rows_by_id.get(sid, {}).get("Location"), loc)
        for sid, col in colour_updates.items():
            add(sid, "Tube Colour", rows_by_id.get(sid, {}).get("Colour"), col)
        for sid, pid in producer_updates.items():
            old_pid = rows_by_id.get(sid, {}).get("ProducerID")
            if old_pid != pid:
                entries.append({"SpoolID": sid, "Action": yarn_spool_log.UPDATED, "Field": "Producer",
                                "Old": pmap.get(old_pid) if old_pid else None,
                                "New": pmap.get(pid) if pid else None})
        yarn_spool_log.log_spool_changes(entries)

    # ---------------- Label queue ----------------

    def _reload_label_queue(self):
        self._queue_items: List[Dict] = []
        if not table_exists(LABEL_QUEUE_TABLE):
            self.tbl_queue.setRowCount(0)
            return
        rows = fetch_all(
            f"SELECT q.[ID] AS QueueID, q.[SpoolID], s.[YarnID], s.[Charge], s.[WeightKg], s.[Location] "
            f"FROM {LABEL_QUEUE_TABLE} q "
            f"JOIN {self.SPOOL_TABLE} s ON s.[ID] = q.[SpoolID] "
            f"WHERE q.[PrintedDate] IS NULL "
            f"ORDER BY q.[QueuedDate]"
        )
        for r in rows:
            yid = r.get("YarnID")
            self._queue_items.append({
                "QueueID": r["QueueID"], "SpoolID": r["SpoolID"],
                "Yarn": self._yarn_name_map.get(int(yid), f"Yarn {yid}") if yid is not None else "",
                "Batch": r.get("Charge") or "",
                "Weight": float(r.get("WeightKg") or 0),
                "Location": r.get("Location") or "",
            })
        self.tbl_queue.setRowCount(len(self._queue_items))
        for row, it in enumerate(self._queue_items):
            vals = [f"#{it['SpoolID']}", it["Yarn"], it["Batch"] or "–", f"{it['Weight']:.2f}"]
            for c, txt in enumerate(vals):
                item = QTableWidgetItem(txt)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setData(Qt.UserRole, it["QueueID"])
                self.tbl_queue.setItem(row, c, item)
        self.tbl_queue.resizeColumnsToContents()

    def _on_add_to_label_queue(self):
        if not self._writable or self.model_detail is None:
            return
        ids = self.model_detail.checked_spool_ids()
        if not ids:
            QMessageBox.information(self, "Add to label queue", "Please check at least one spool.")
            return
        added = self._queue_labels(ids, "Add to label queue")
        if added is None:
            return
        log_usage_event("feature", "yarn_stock_add_to_label_queue", str(added))
        QMessageBox.information(self, "Add to label queue", f"{added} spool(s) added to the queue.")

    def _queue_labels(self, ids: List[int], title: str) -> Optional[int]:
        """Legt Spulen in die Label queue (bereits wartende werden uebersprungen)
        und laedt die Queue-Anzeige neu. None bei Fehler (Meldung gezeigt)."""
        if not table_exists(LABEL_QUEUE_TABLE):
            return 0
        already_queued = {it["SpoolID"] for it in getattr(self, "_queue_items", [])}
        user_id = _current_user_id()
        now = datetime.now().isoformat(sep=" ", timespec="seconds")
        added = 0
        try:
            for sid in ids:
                if sid in already_queued:
                    continue
                execute(
                    f"INSERT INTO {LABEL_QUEUE_TABLE} ([SpoolID],[QueuedDate],[UserID],[GlobalID]) "
                    f"VALUES (?,?,?,?)",
                    [sid, now, user_id, new_global_id()],
                )
                added += 1
        except Exception as e:
            QMessageBox.critical(self, title, f"Failed to add to the label queue: {e}")
            self._reload_label_queue()
            return None
        self._reload_label_queue()
        return added

    def _on_remove_from_label_queue(self):
        if not self._writable:
            return
        rows = self.tbl_queue.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Remove selected", "Please select at least one row.")
            return
        queue_ids = [self.tbl_queue.item(r.row(), 0).data(Qt.UserRole) for r in rows]
        try:
            for qid in queue_ids:
                execute(f"DELETE FROM {LABEL_QUEUE_TABLE} WHERE [ID] = ?", [qid])
        except Exception as e:
            QMessageBox.critical(self, "Remove selected", f"Failed to remove: {e}")
            return
        self._reload_label_queue()

    def _on_print_labels(self):
        if not self._writable:
            return
        if fitz is None or qrcode is None:
            QMessageBox.critical(
                self, "Print Labels",
                "PyMuPDF and/or qrcode are not installed. Run:\n"
                "pip install pymupdf qrcode --break-system-packages")
            return
        if not getattr(self, "_queue_items", []):
            QMessageBox.information(self, "Print Labels", "The label queue is empty.")
            return
        template = load_label_template("Default")

        dlg = PrintLabelsDialog("Default", template, len(self._queue_items), parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        tpl = dlg.template_values()
        start_index = dlg.start_index()

        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save label PDF", "labels.pdf", "PDF Files (*.pdf)")
        if not out_path:
            return

        try:
            placed = generate_label_sheet_pdf(
                self._queue_items, tpl, start_index, out_path, draw_cell=_draw_yarn_label_cell)
        except Exception as e:
            QMessageBox.critical(self, "Print Labels", f"Failed to generate PDF: {e}")
            return

        printed_ids = [it["QueueID"] for it in self._queue_items[:placed]]
        now = datetime.now().isoformat(sep=" ", timespec="seconds")
        try:
            for qid in printed_ids:
                execute(f"UPDATE {LABEL_QUEUE_TABLE} SET [PrintedDate] = ? WHERE [ID] = ?", [now, qid])
        except Exception as e:
            QMessageBox.warning(
                self, "Print Labels",
                f"PDF was created, but marking items as printed failed: {e}")

        remaining = len(self._queue_items) - placed
        msg = f"{placed} label(s) written to:\n{out_path}"
        if remaining > 0:
            msg += f"\n\n{remaining} spool(s) didn't fit on the sheet and stay in the queue."
        log_usage_event("feature", "yarn_stock_print_labels", str(placed))
        QMessageBox.information(self, "Print Labels", msg)
        self._reload_label_queue()