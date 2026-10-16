from ui.theme import accent_tint, accent_gridline
# ui/screen_manage_yarn.py
from typing import List, Dict, Optional, Tuple, Callable
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QEvent
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QSizePolicy, QTableView, QMessageBox, QLineEdit, QAbstractItemView,
    QStyledItemDelegate, QComboBox, QDialog, QTreeWidget, QTreeWidgetItem,
    QInputDialog
)

from ui.widgets.footer import FooterBar
from ui.widgets import sidebar_nav
from ui.text_normalize import norm as _norm, canon_simple as _canon
from db.connection import fetch_all, execute, new_global_id, get_columns_map
from db.trial_reference import format_trial_number
import app_meta

# Wiederverwendet statt dupliziert (anders als bei Top Plates/Jets) - die vier
# Klassen sind vollstaendig generisch (kein Jets-spezifischer State), siehe
# ui/screen_manage_jets.py fuer die Implementierung.
from ui.screen_manage_jets import (
    MultiColumnFilterProxy, FilterableHeaderView, ColumnOrderDialog, ExpandableFilterProxy,
    SearchHighlightDelegate,
)


def _canon_noparen(s: str) -> str:
    c = _canon(s)
    return c.replace('(', '').replace(')', '')




# ---------- FK loaders (ohne Aliasse wegen Access-ODBC-Quirk) ----------------
def load_garntyp_map() -> Tuple[Dict[int, str], Dict[str, int]]:
    rows = fetch_all(
        'SELECT [ID], [Garntyp] FROM [tblGarntyp] ORDER BY [Garntyp]', [])
    id2name: Dict[int, str] = {}
    name2id: Dict[str, int] = {}
    for r in rows:
        i = r.get('ID')
        n = r.get('Garntyp')
        try:
            i = int(i)
        except Exception:
            pass
        id2name[i] = n
        name2id[str(n)] = i
    return id2name, name2id


def load_material_map() -> Tuple[Dict[int, str], Dict[str, int]]:
    rows = fetch_all(
        'SELECT [ID], [Material] FROM [tblMaterial] ORDER BY [Material]', [])
    id2name: Dict[int, str] = {}
    name2id: Dict[str, int] = {}
    for r in rows:
        i = r.get('ID')
        n = r.get('Material')
        try:
            i = int(i)
        except Exception:
            pass
        id2name[i] = n
        name2id[str(n)] = i
    return id2name, name2id


def load_colour_map() -> Tuple[Dict[int, str], Dict[str, int]]:
    rows = fetch_all(
        'SELECT [ID], [Colour] FROM [tblColour] ORDER BY [Colour]', [])
    id2name: Dict[int, str] = {}
    name2id: Dict[str, int] = {}
    for r in rows:
        i = r.get('ID')
        n = r.get('Colour')
        try:
            i = int(i)
        except Exception:
            pass
        id2name[i] = n
        name2id[str(n)] = i
    return id2name, name2id


_COLOUR_SIMILARITY_CUTOFF = 0.75  # siehe CLAUDE.md: an "blak"/"black", "grey"/"gray" kalibriert,
# löst bei genuinely unterschiedlichen kurzen Farbnamen (red/blue/green/...) nicht aus


def quick_add_colour(parent=None) -> Optional[Tuple[int, str]]:
    """Kleiner Eingabedialog für eine neue Farbe (Nutzerwunsch: "wie kann ich
    das schnell hinzufügen, ohne dass ich alles was ich bereits beim Garn
    eingegeben habe wieder löschen muss?") - es gibt (bewusst, siehe CLAUDE.md)
    keinen eigenen "Manage Colours"-Screen, tblColour wurde nur per Einweg-
    Skript befüllt. Legt die Farbe in tblColour an und gibt (ID, Colour)
    zurück, oder None bei Abbruch/leerer Eingabe. Wird sowohl aus dem
    NewYarnScreen-Formular als auch aus der Inline-Tabelle in ManageYarnScreen
    aufgerufen (siehe ComboMapDelegate add_new_callback) - reine DB-Logik
    hier, kein UI-State dieser Datei.

    Zwei Dublettenschutz-Stufen (Nutzerwunsch: "dass derselbe (oder ähnliche
    Name 'black' 'blak' etc.) nicht nochmal angelegt werden kann"):
    1. Exakter Treffer (case-insensitiv, z.B. "Blau"/"blau") -> gibt still die
       vorhandene ID zurück, kein Dialog.
    2. Ähnlicher, aber nicht identischer Name (`difflib.get_close_matches()`,
       `_COLOUR_SIMILARITY_CUTOFF` empirisch gegen echte Tippfehler-Paare
       kalibriert, nicht geraten - siehe CLAUDE.md) -> Rückfrage per
       QMessageBox mit drei echten Optionen (vorhandene Farbe verwenden / neue
       trotzdem anlegen / abbrechen), damit ein Tippfehler nicht stillschweigend
       eine Fast-Dublette erzeugt, aber ein bewusst gewollter ähnlicher Name
       (z.B. "grey" UND "gray" parallel) weiterhin möglich bleibt.

    Insert + ID-Ermittlung laufen bewusst auf EINER `get_connection()`-Session
    statt (wie an mehreren bestehenden Stellen im Projekt üblich, z.B.
    main.py's _create_top_plate()/_insert_top_plate_full()) über getrennte
    execute()/fetch_all()-Aufrufe mit abschliessendem `SELECT @@IDENTITY` –
    @@IDENTITY ist reine
    Session-State pro MySQL-Verbindung, und execute()/fetch_all() ziehen sich
    JEWEILS unabhängig eine (nicht notwendigerweise dieselbe) Verbindung aus
    dem Pool (siehe db/connection.py get_connection()). Empirisch geprüft statt
    angenommen: ein Testlauf mit mehreren schnell aufeinanderfolgenden
    execute()+fetch_all(@@IDENTITY)-Paaren lieferte dabei tatsächlich einmal 0
    zurück - der bestehende Pool-Mustercode ist also nicht zuverlässig, auch
    wenn er in der Praxis meist "funktioniert" (Einzelthread, wenig Kontention).
    Hier stattdessen `cur.lastrowid` auf demselben Cursor/derselben Connection
    wie der INSERT selbst - dadurch unabhängig vom Pool-Verhalten korrekt."""
    name, ok = QInputDialog.getText(parent, 'New Colour', 'Colour name:')
    name = (name or '').strip()
    if not ok or not name:
        return None

    existing_rows = fetch_all('SELECT ID, Colour FROM tblColour', [])
    name_lower = name.lower()
    for row in existing_rows:
        if (row.get('Colour') or '').strip().lower() == name_lower:
            return int(row['ID']), row['Colour']

    import difflib
    existing_names = [row['Colour'] for row in existing_rows if row.get('Colour')]
    close = difflib.get_close_matches(
        name_lower, [n.lower() for n in existing_names], n=1, cutoff=_COLOUR_SIMILARITY_CUTOFF)
    if close:
        match_name = next(n for n in existing_names if n.lower() == close[0])
        box = QMessageBox(parent)
        box.setWindowTitle('Similar colour exists')
        box.setText(
            f'"{name}" looks similar to the existing colour "{match_name}".\n\n'
            f'Use the existing colour, or create "{name}" as a new, separate one anyway?')
        btn_use = box.addButton(f'Use "{match_name}"', QMessageBox.AcceptRole)
        box.addButton(f'Create "{name}" anyway', QMessageBox.DestructiveRole)
        btn_cancel = box.addButton(QMessageBox.Cancel)
        box.setDefaultButton(btn_use)
        box.exec()
        clicked = box.clickedButton()
        if clicked is btn_cancel:
            return None
        if clicked is btn_use:
            match_row = next(r for r in existing_rows if r['Colour'] == match_name)
            return int(match_row['ID']), match_row['Colour']
        # sonst: "Create anyway" -> unten wie gewohnt anlegen

    from db.connection import get_connection
    with get_connection() as cn:
        cur = cn.cursor()
        gid = new_global_id()
        cur.execute('INSERT INTO tblColour (Colour, GlobalID) VALUES (?, ?)', [name, gid])
        cn.commit()
        new_id = cur.lastrowid
    if not new_id:
        return None
    return int(new_id), name


# ---------- Duplicate-Yarn-Check (Nutzerwunsch: "so gut wie möglich verhindern,
# dass zwei mal dasselbe garn aufgenommen wird") ------------------------------
# Felder auf Nutzeranweisung: "die wichtigen felder sind garntyp, material,
# titer, endtiter, numberoffilaments und colour". Titer/Endtiter/Garntyp/
# Material/NumberOfFilaments sind in der Praxis so gut wie immer befüllt (per
# echter dev_local-Zählung: 0 von 94 NULL ausser Titer mit 4/94) - Colour dagegen
# oft nicht (65 von 94 NULL, siehe tblColour-Rollout oben) und wird deshalb nur
# verglichen, wenn BEIDE Seiten einen Wert haben (sonst weder "gleich" noch
# "verschieden" - neutral ausgeklammert statt False-Positives durch zwei
# zufällig beide leere Colour-Felder).
_DUP_CHECK_CORE_FIELDS = ['Garntyp', 'Material', 'Titer', 'Endtiter', 'NumberOfFilaments']
_DUP_CHECK_COLOUR_FIELD = 'ColourID'
_DUP_FIELD_LABELS = {
    'Garntyp': 'Garntyp', 'Material': 'Material', 'Titer': 'Titer',
    'Endtiter': 'Endtiter', 'NumberOfFilaments': 'Number of Filaments',
    'ColourID': 'Colour',
}


def _values_equal(a, b) -> bool:
    """Robuster Vergleich für DB-Werte, die je nach Quelle als Decimal/int
    (frisch aus der DB) oder als str (aus einem QLineEdit/_collect_values())
    ankommen können."""
    if a in (None, '') or b in (None, ''):
        return a in (None, '') and b in (None, '')
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return str(a).strip() == str(b).strip()


def find_duplicate_yarn(fields: Dict[str, object], exclude_id: Optional[int] = None):
    """Sucht unter den bestehenden Katalog-Garnen (Shadow-Yarns/`SourceTrialID`
    ausgenommen, siehe Halbfabrikat-Feature) nach dem ähnlichsten Treffer zu
    `fields` (ein dict mit mind. den 5 Kernfeldern + optional ColourID - siehe
    _DUP_CHECK_CORE_FIELDS/_DUP_CHECK_COLOUR_FIELD). Läuft NICHT, solange nicht
    alle 5 Kernfelder gesetzt sind (bei einem frisch per "New Yarn" angelegten,
    noch leeren Datensatz z.B. sinnlos - kein False-Positive-Risiko, aber auch
    keine Aussage möglich).

    Rückgabe `None` (kein Treffer mit 0 oder 1 abweichendem Feld) oder
    `(row, diff_count, diff_fields, compared_fields)`:
      - diff_count == 0: exakte Dublette (alle verglichenen Felder identisch)
      - diff_count == 1: "sehr ähnlich" (genau ein Feld weicht ab)
    Bei mehreren Kandidaten wird der mit der geringsten Abweichung gewählt."""
    if any(fields.get(c) in (None, '') for c in _DUP_CHECK_CORE_FIELDS):
        return None
    candidate_colour = fields.get(_DUP_CHECK_COLOUR_FIELD)

    rows = fetch_all(
        'SELECT ID, Name, Garntyp, Material, Titer, Endtiter, NumberOfFilaments, ColourID '
        'FROM tblYarn WHERE SourceTrialID IS NULL', [])
    best = None
    for row in rows:
        rid = row.get('ID')
        if exclude_id is not None and _values_equal(rid, exclude_id):
            continue
        compared_fields = list(_DUP_CHECK_CORE_FIELDS)
        diff_fields = [c for c in _DUP_CHECK_CORE_FIELDS
                        if not _values_equal(fields.get(c), row.get(c))]
        colour_compared = (candidate_colour not in (None, '')
                            and row.get(_DUP_CHECK_COLOUR_FIELD) is not None)
        if colour_compared:
            compared_fields.append(_DUP_CHECK_COLOUR_FIELD)
            if not _values_equal(candidate_colour, row.get(_DUP_CHECK_COLOUR_FIELD)):
                diff_fields.append(_DUP_CHECK_COLOUR_FIELD)
        diff_count = len(diff_fields)
        if diff_count > 1:
            continue
        if best is None or diff_count < best[1]:
            best = (row, diff_count, diff_fields, compared_fields)
    return best


def confirm_save_despite_duplicate(parent, match_row: Dict, diff_count: int,
                                    diff_fields: List[str], compared_fields: List[str]) -> bool:
    """Warn-Dialog vor dem tatsächlichen Speichern (Nutzerwunsch: "sehr
    ähnliche Garne ... eine Warnung ala wirklich speichern? Garn xy ist sehr
    ähnlich"). Default-Button ist bewusst "No" - ein versehentlicher Enter-
    Druck legt keine Dublette an. Gibt True zurück, wenn der Nutzer trotzdem
    speichern will."""
    name = match_row.get('Name') or f"yarn ID {match_row.get('ID')}"
    rid = match_row.get('ID')
    same_fields = [c for c in compared_fields if c not in diff_fields]
    same_labels = ', '.join(_DUP_FIELD_LABELS.get(c, c) for c in same_fields)
    if diff_count == 0:
        text = (f'An identical yarn already exists: "{name}" (ID {rid}) - '
                f'same {same_labels}.\n\nSave anyway?')
    else:
        diff_label = _DUP_FIELD_LABELS.get(diff_fields[0], diff_fields[0])
        text = (f'This yarn is very similar to "{name}" (ID {rid}) - only '
                f'{diff_label} differs (rest matches: {same_labels}).\n\nSave anyway?')
    box = QMessageBox(parent)
    box.setWindowTitle('Possible duplicate yarn')
    box.setIcon(QMessageBox.Warning)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    box.setDefaultButton(QMessageBox.No)
    return box.exec() == QMessageBox.Yes


def _resolve_field(cands: List[str], cols_map: Dict[str, str]) -> Optional[str]:
    # exakter lowercase-match
    for cand in cands:
        lc = (cand or "").lower()
        if lc in cols_map:
            return cols_map[lc]
    # normalisierter match
    inv = {_norm(k): v for k, v in cols_map.items()}
    for cand in cands:
        nk = _norm(cand)
        if nk in inv:
            return inv[nk]
    return None


def _id_key_variants(v) -> List[object]:
    """Generiert Key-Varianten für Mapping-Lookups (int/str/original)."""
    out: List[object] = []
    if v is None:
        return out
    out.append(v)
    try:
        out.append(int(v))
    except Exception:
        pass
    try:
        out.append(str(v))
    except Exception:
        pass
    # dedupe, preserve order
    seen = set()
    uniq = []
    for x in out:
        if x in seen:
            continue
        seen.add(x)
        uniq.append(x)
    return uniq


def load_yarngroup_map() -> Tuple[Dict[object, str], Dict[str, object]]:
    """YarnGroup (tblyarngroup) mapping: ID -> DisplayName.

    Achtung: In deiner DB kann das Feld fuer den Namen auch z.B. GroupName heissen.
    Darum wird es ueber information_schema aufgeloest.
    """
    table = 'tblyarngroup'
    cols_map = get_columns_map(table)
    col_id = _resolve_field(['ID'], cols_map) or 'ID'
    col_name = _resolve_field(['Name', 'GroupName', 'GruppenName', 'Bezeichnung'], cols_map) or 'Name'
    col_no = _resolve_field(['GroupNumber', 'GroupNo', 'GruppenNummer', 'Number', 'Nummer'], cols_map)

    sel = [f'[{col_id}] AS ID', f'[{col_name}] AS Name']
    if col_no:
        sel.append(f'[{col_no}] AS GroupNo')

    order = f'ORDER BY [{col_no}]' if col_no else f'ORDER BY [{col_name}]'
    rows = fetch_all(f'SELECT {", ".join(sel)} FROM [{table}] {order}', [])

    id2name: Dict[object, str] = {}
    name2id: Dict[str, object] = {}

    for r in rows:
        raw_id = r.get('ID')
        raw_name = r.get('Name')
        raw_no = r.get('GroupNo') if 'GroupNo' in r else None

        # Display label: "<no> - <name>" oder nur name
        name = '' if raw_name is None else str(raw_name).strip()
        try:
            gno = int(str(raw_no).strip()) if raw_no not in (None, '') else None
        except Exception:
            gno = None
        label = f'{gno} - {name}' if (gno is not None and name) else (name or (str(gno) if gno is not None else ''))

        # Map: sowohl int als auch str keys ablegen (robust gegen Typenmix)
        for k in _id_key_variants(raw_id):
            id2name[k] = label
        if label:
            # letztes gewinnt (bei Duplikaten egal)
            name2id[label] = raw_id

    return id2name, name2id


# ---------- Delegates for FK columns -----------------------------------------
_ADD_NEW_SENTINEL = object()


class ComboMapDelegate(QStyledItemDelegate):
    """Generic combobox delegate that shows names but writes IDs.

    Optionaler `add_new_callback` (nur für Colour verdrahtet, siehe
    ManageYarnScreen.reload_data() - Garntyp/Material/YarnGroup haben eigene
    Manage-Screens dafür, Colour bisher nicht): hängt einen "+ Add new…"-
    Sentinel-Eintrag ans Ende der Liste. Der Dialog des Callbacks läuft
    SYNCHRON innerhalb des `activated`-Handlers, bevor Qt die Zelle committet/
    schliesst - dadurch steht editor.currentData() beim anschliessenden
    setModelData() garantiert schon auf dem neuen (oder bei Abbruch dem vorher
    aktiven) Eintrag, nie auf dem Sentinel selbst."""

    def __init__(self, id2name: Dict[object, str], parent=None,
                 add_new_callback: Optional[Callable[[QWidget], Optional[Tuple[object, str]]]] = None,
                 add_new_label: str = '+ Add new colour…'):
        super().__init__(parent)
        self.id2name = id2name
        self.add_new_callback = add_new_callback
        self.add_new_label = add_new_label
        # stable order by display name
        # NOTE: id2name kann mehrere Key-Varianten fuer denselben Datensatz enthalten
        # (z.B. 1 und "1"). Darum dedupen wir ueber den *Label*-Text.
        seen_label = set()
        opts = []
        for i, n in id2name.items():
            label = '' if n is None else str(n)
            if label in seen_label:
                continue
            seen_label.add(label)
            opts.append((i, label))
        self._options = sorted(opts, key=lambda t: (t[1].lower() if isinstance(t[1], str) else str(t[1]).lower()))

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        for i, n in self._options:
            combo.addItem(str(n), i)
        if self.add_new_callback:
            combo.addItem(self.add_new_label, _ADD_NEW_SENTINEL)
            state = {'last_good': combo.currentIndex()}

            def _on_activated(idx, combo=combo, state=state):
                if combo.itemData(idx) is not _ADD_NEW_SENTINEL:
                    state['last_good'] = idx
                    return
                result = self.add_new_callback(combo)
                if result:
                    new_id, new_name = result
                    insert_pos = combo.count() - 1  # vor dem Sentinel
                    combo.insertItem(insert_pos, str(new_name), new_id)
                    combo.setCurrentIndex(insert_pos)
                    state['last_good'] = insert_pos
                    # self.id2name ist dasselbe Dict-Objekt wie z.B.
                    # ManageYarnScreen._colour_id2name - Mutation hier hält
                    # künftige Zell-Renderings/Editor-Instanzen automatisch
                    # synchron, ohne reload_data() (das würde unsaved Edits
                    # in anderen Zellen verwerfen).
                    self.id2name[new_id] = new_name
                    self._options.append((new_id, str(new_name)))
                else:
                    combo.setCurrentIndex(state['last_good'])

            combo.activated.connect(_on_activated)
        combo.setEditable(False)
        return combo

    def setEditorData(self, editor, index):
        current_id = index.model().data(index, Qt.EditRole)
        for cand in _id_key_variants(current_id):
            for i in range(editor.count()):
                if editor.itemData(i) == cand:
                    editor.setCurrentIndex(i)
                    return

    def setModelData(self, editor, model, index):
        data = editor.currentData()
        if data is _ADD_NEW_SENTINEL:
            return
        model.setData(index, data, Qt.EditRole)


# ---------- Table Model -------------------------------------------------------
class YarnTableModel(QAbstractTableModel):
    """Editable model, with FK-display (Garntyp & Material), computed DPF, and light background."""

    def __init__(self, rows: List[Dict], headers: List[str], id_column: str = 'ID',
                 garntyp_col: Optional[str] = None, garntyp_map: Optional[Dict[int, str]] = None,
                 material_col: Optional[str] = None, material_map: Optional[Dict[int, str]] = None,
                 yarngroup_col: Optional[str] = None, yarngroup_map: Optional[Dict[object, str]] = None,
                 colour_col: Optional[str] = None, colour_map: Optional[Dict[int, str]] = None,
                 createdby_col: Optional[str] = None, createdby_map: Optional[Dict[object, str]] = None,
                 minstock_locked: bool = False):
        super().__init__()
        self._rows = rows[:]
        self._headers = headers[:]
        self._id_col = id_column
        self._dirty_cells = set()
        self._minstock_locked = minstock_locked
        self._garntyp_col = garntyp_col
        self._garntyp_map = garntyp_map or {}
        self._material_col = material_col
        self._material_map = material_map or {}
        self._yarngroup_col = yarngroup_col
        self._yarngroup_map: Dict[object, str] = yarngroup_map or {}
        self._colour_col = colour_col
        self._colour_map: Dict[int, str] = colour_map or {}
        self._createdby_col = createdby_col
        self._createdby_map: Dict[object, str] = createdby_map or {}

        # Detect column names for computed DPF and its inputs, MinStock
        # (separately lockable - AdminBox=0 users may edit everything else),
        # CreationDate (audit column, never editable) and UsedInTrial/StockKg
        # (rein berechnet, keine echten tblYarn-Felder - siehe
        # ManageYarnScreen._load_yarn).
        self._dpf_col = None
        self._endtiter_col = None
        self._filaments_col = None
        self._minstock_col = None
        self._creationdate_col = None
        self._usedintrial_col = None
        self._stockkg_col = None
        for h in self._headers:
            k = _canon_noparen(h)
            if self._dpf_col is None and k in {'dpfdtex', 'dpf'}:
                self._dpf_col = h
            if self._endtiter_col is None and k in {'endtiterdtex', 'endtiter'}:
                self._endtiter_col = h
            if self._filaments_col is None and k in {'numberoffilaments', 'filaments', 'nofilaments'}:
                self._filaments_col = h
            if self._minstock_col is None and k == 'minstock':
                self._minstock_col = h
            if self._creationdate_col is None and k == 'creationdate':
                self._creationdate_col = h
            if self._usedintrial_col is None and k == 'usedintrial':
                self._usedintrial_col = h
            if self._stockkg_col is None and k == 'stockkg':
                self._stockkg_col = h

        # Welche UsedInTrial-Zeilen (per Yarn-ID) gerade inline aufgeklappt
        # sind - steuert nur das Dreieck-Symbol auf der Yarn-Zeile selbst.
        # Das eigentliche Ein-/Ausblenden der TrialSeries-/Versuchs-Zeilen
        # (echte, eingefügte Model-Zeilen - siehe insert_detail_rows()) macht
        # ManageYarnScreen.
        self._expanded_ids: set = set()

        # Reservierter Row-Dict-Key für synthetische Detailzeilen (TrialSeries/
        # Versuchsnummer), die ManageYarnScreen per insert_detail_rows() unter
        # eine Yarn-Zeile einfügt - siehe row_kind()/anchor_row()/local_order().
        # Echte tblYarn-Zeilen haben diesen Key nie (row_kind() liefert dann
        # 'yarn' als Default).

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._headers)

    # Nutzerwunsch: "benenn das feld doch bitte Colour und nicht ColourID in
    # der ui" - der DB-Spaltenname bleibt ColourID (FK-Konvention wie
    # Garntyp/Material/YarnGroupID), nur die Anzeige wird hier freundlicher.
    _DISPLAY_LABEL_OVERRIDES = {'colourid': 'Colour'}

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            h = self._headers[section]
            return self._DISPLAY_LABEL_OVERRIDES.get(_canon(h), h)
        return None

    def _compute_dpf(self, row: int):
        if not self._dpf_col or not self._endtiter_col or not self._filaments_col:
            return None
        endt = self._rows[row].get(self._endtiter_col)
        fils = self._rows[row].get(self._filaments_col)
        try:
            if endt in (None, '') or fils in (None, '', 0, '0'):
                return None
            endt_f = float(str(endt).replace(',', '.'))
            fils_f = float(str(fils).replace(',', '.'))
            if fils_f == 0.0:
                return None
            return endt_f / fils_f
        except Exception:
            return None

    # ---- inline aufklappbare Detailzeilen (TrialSeries/Versuchsnummer) ------
    def row_kind(self, row: int) -> str:
        """'yarn' (echte tblYarn-Zeile, Default) | 'series' | 'trial'."""
        return self._rows[row].get('_row_kind', 'yarn')

    def anchor_row(self, row: int) -> int:
        """Zeilenindex der Yarn-Zeile, zu der diese Zeile gehört (sich selbst,
        falls sie schon eine Yarn-Zeile ist). Wird von ExpandableFilterProxy
        gebraucht, um Detailzeilen beim Sortieren am richtigen Platz (direkt
        unter ihrer Yarn-Zeile) zu halten."""
        rd = self._rows[row]
        if rd.get('_row_kind', 'yarn') == 'yarn':
            return row
        anchor_id = rd.get('_anchor_yarn_id')
        for i, r in enumerate(self._rows):
            if r.get('_row_kind', 'yarn') == 'yarn' and r.get(self._id_col) == anchor_id:
                return i
        return row  # sollte nicht vorkommen (Yarn-Zeile zwischenzeitlich entfernt)

    def local_order(self, row: int) -> float:
        """Feste Position innerhalb eines Yarn-Blocks (0 = die Yarn-Zeile
        selbst, dann Serien in Erfassungsreihenfolge, Versuche direkt hinter
        ihrer Serie) - siehe ManageYarnScreen._expand_yarn_row/_expand_series_row."""
        return self._rows[row].get('_order', 0.0)

    def insert_detail_rows(self, after_row: int, new_rows: List[Dict]):
        """Fügt echte Model-Zeilen direkt nach `after_row` ein (nicht nur
        Anzeige - siehe rowCount()). Bestehende dirty-Markierungen (die auf
        Positionsindizes zeigen) werden mitverschoben, sonst würde
        save_changes() nach dem Aufklappen die falsche Zeile treffen."""
        if not new_rows:
            return
        n = len(new_rows)
        insert_at = after_row + 1
        self.beginInsertRows(QModelIndex(), insert_at, insert_at + n - 1)
        self._rows[insert_at:insert_at] = new_rows
        self._dirty_cells = {(r + n if r >= insert_at else r, c) for (r, c) in self._dirty_cells}
        self.endInsertRows()

    def remove_rows_span(self, start_row: int, count: int):
        """Gegenstück zu insert_detail_rows() - entfernt einen zusammen-
        hängenden Block echter Model-Zeilen wieder."""
        if count <= 0:
            return
        self.beginRemoveRows(QModelIndex(), start_row, start_row + count - 1)
        del self._rows[start_row:start_row + count]
        self._dirty_cells = {
            (r - count if r >= start_row + count else r, c)
            for (r, c) in self._dirty_cells if not (start_row <= r < start_row + count)
        }
        self.endRemoveRows()

    def _detail_row_data(self, row: int, col: int, role):
        """data() für eine Serie-/Versuchs-Zeile: der komplette Datensatz ist
        nur ein Anzeige-Label in Spalte 0 (ManageYarnScreen spannt die ganze
        Zeile mit setSpan() über diese eine Zelle)."""
        if role == Qt.DisplayRole and col == 0:
            return self._rows[row].get('_label', '')
        if role == Qt.BackgroundRole:
            # Versuchs-Zeilen (tiefer verschachtelt, rein informativ) bekommen
            # einen helleren Ton als ihre TrialSeries-Zeile, damit die zwei
            # Ebenen optisch auseinanderfallen statt in einem Block zu wirken.
            if self._rows[row].get('_row_kind') == 'trial':
                return QBrush(QColor('#F1F8F1'))
            return QBrush(QColor('#E3EEE3'))
        if role == Qt.ForegroundRole:
            return QBrush(QColor('#2b2b2b'))
        if role == Qt.TextAlignmentRole:
            return Qt.AlignVCenter | Qt.AlignLeft
        if role == Qt.ToolTipRole and self._rows[row].get('_row_kind') == 'series':
            return 'Click to show/hide the trial numbers · double-click to open this trial series'
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        r, c = index.row(), index.column()
        if self._rows[r].get('_row_kind', 'yarn') != 'yarn':
            return self._detail_row_data(r, c, role)
        header = self._headers[c]
        val = self._rows[r].get(header, None)

        if role == Qt.BackgroundRole:
            return QBrush(QColor(accent_tint())) if (r % 2 == 0) else QBrush(QColor('#F5FFF5'))

        # Computed DPF field
        if self._dpf_col and header == self._dpf_col:
            if role in (Qt.DisplayRole, Qt.EditRole):
                v = self._compute_dpf(r)
                return '' if v is None else v
            if role == Qt.TextAlignmentRole:
                return Qt.AlignCenter
            return None

        # Computed "used in at least one trial" field (Yes/No). Deliberately no
        # custom delegate/color here (an earlier attempt fought the table's
        # stylesheet and made the cell unreadable) - clickability on "Yes" is
        # signalled via tooltip + hover cursor instead, see ManageYarnScreen.
        # The trailing triangle (▸/▾) mirrors the expand state that
        # ManageYarnScreen tracks when it inserts real "series" detail rows
        # directly below this row (insert_detail_rows()) - no popup anymore.
        if self._usedintrial_col and header == self._usedintrial_col:
            if role == Qt.DisplayRole:
                if val != 1:
                    return 'No'
                yid = self._rows[r].get(self._id_col)
                return 'Yes ▾' if yid in self._expanded_ids else 'Yes ▸'
            if role == Qt.TextAlignmentRole:
                return Qt.AlignCenter
            if role == Qt.ToolTipRole and val == 1:
                yid = self._rows[r].get(self._id_col)
                return ('Click to hide the trial series using this yarn' if yid in self._expanded_ids
                        else 'Click to show the trial series using this yarn')
            return None

        # Computed current stock (kg), summed server-side over tblYarnSpool
        # (Status='in stock') - see ManageYarnScreen._load_yarn().
        if self._stockkg_col and header == self._stockkg_col:
            if role == Qt.DisplayRole:
                try:
                    return f"{float(val or 0):.1f}"
                except (TypeError, ValueError):
                    return '' if val is None else str(val)
            if role == Qt.TextAlignmentRole:
                return Qt.AlignCenter
            return None

        if role == Qt.EditRole:
            return val

        # FK display: show names
        if role == Qt.DisplayRole:
            if self._garntyp_col and header == self._garntyp_col:
                try:
                    return self._garntyp_map.get(int(val), '') if val is not None else ''
                except Exception:
                    return self._garntyp_map.get(val, '')
            if self._material_col and header == self._material_col:
                try:
                    return self._material_map.get(int(val), '') if val is not None else ''
                except Exception:
                    return self._material_map.get(val, '')
            if self._colour_col and header == self._colour_col:
                try:
                    return self._colour_map.get(int(val), '') if val is not None else ''
                except Exception:
                    return self._colour_map.get(val, '')
            if self._yarngroup_col and header == self._yarngroup_col:
                # Wenn das Mapping nicht geladen werden konnte, zeige die rohe ID
                if not self._yarngroup_map:
                    return '' if val is None else str(val)
                for cand in _id_key_variants(val):
                    if cand in self._yarngroup_map:
                        return self._yarngroup_map.get(cand, '')
                # unbekannte ID -> ebenfalls roh anzeigen (hilft beim Debuggen)
                return '' if val is None else str(val)
            if self._createdby_col and header == self._createdby_col:
                for cand in _id_key_variants(val):
                    if cand in self._createdby_map:
                        return self._createdby_map.get(cand, '')
                return '' if val is None else str(val)
            return '' if val is None else str(val)

        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        return None

    def set_minstock_locked(self, locked: bool):
        """Sperrt/entsperrt nur die MinStock-Spalte (Ansicht muss danach neu
        gezeichnet werden). Der Rest der Tabelle bleibt editierbar - anders als
        bei Jets/Top Plates gibt es für Yarn kein alles-oder-nichts Read-only."""
        self._minstock_locked = locked

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemIsEnabled
        if self._rows[index.row()].get('_row_kind', 'yarn') != 'yarn':
            # Detailzeile: nicht selektierbar/editierbar - Klick-Handling läuft
            # über ManageYarnScreen._handle_table_click, nicht über Qt-Editing.
            return Qt.ItemIsEnabled
        header = self._headers[index.column()]
        if header in (self._dpf_col, self._usedintrial_col, self._stockkg_col):
            return Qt.ItemIsEnabled  # computed -> not editable
        if header in (self._createdby_col, self._creationdate_col):
            return Qt.ItemIsEnabled  # audit metadata -> never editable, by anyone
        if self._minstock_locked and self._minstock_col and header == self._minstock_col:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False
        if self._rows[index.row()].get('_row_kind', 'yarn') != 'yarn':
            return False  # Detailzeile - nie editierbar (flags() verhindert das ohnehin schon)
        header = self._headers[index.column()]
        if header in (self._createdby_col, self._creationdate_col):
            return False
        if self._minstock_locked and self._minstock_col and header == self._minstock_col:
            return False
        if header in (self._dpf_col, self._usedintrial_col, self._stockkg_col):
            return False  # computed
        if isinstance(value, str):
            value = value.strip()
        self._rows[index.row()][header] = value
        self._dirty_cells.add((index.row(), index.column()))
        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
        return True

    def dirty_rows(self) -> List[Dict]:
        if not self._dirty_cells:
            return []
        dirty_row_indices = sorted({r for (r, _) in self._dirty_cells})
        return [self._rows[i] for i in dirty_row_indices]

    def clear_dirty(self):
        self._dirty_cells.clear()

    def id_column(self) -> str:
        return self._id_col

    def headers(self) -> List[str]:
        return self._headers

    def rows(self) -> List[Dict]:
        return self._rows

    def dpf_column_name(self) -> Optional[str]:
        return self._dpf_col

    def minstock_column_name(self) -> Optional[str]:
        return self._minstock_col

    def usedintrial_column_name(self) -> Optional[str]:
        return self._usedintrial_col

    def set_expanded(self, yarn_id, expanded: bool):
        """Nur fürs Dreieck-Symbol auf der Yarn-Zeile - das Einfügen/Entfernen
        der TrialSeries-Zeilen selbst macht ManageYarnScreen (insert_detail_rows/
        remove_rows_span). Emittiert dataChanged nur für die betroffene Zelle."""
        if expanded:
            self._expanded_ids.add(yarn_id)
        else:
            self._expanded_ids.discard(yarn_id)
        if not self._usedintrial_col:
            return
        try:
            row = next(i for i, rw in enumerate(self._rows) if rw.get(self._id_col) == yarn_id)
        except StopIteration:
            return
        col = self._headers.index(self._usedintrial_col)
        idx = self.index(row, col)
        self.dataChanged.emit(idx, idx, [Qt.DisplayRole, Qt.ToolTipRole])

    def stockkg_column_name(self) -> Optional[str]:
        return self._stockkg_col


# ---------- "Used in Trial Series" popup (reused by screen_manage_jets.py) ---

class TrialUsageDialog(QDialog):
    """Zeigt, in welchen TrialSeries ein Garn/Jet bereits verwendet wurde - pro
    Serie aufklappbar (Pfeilchen) zu den einzelnen Versuchsnummern. Klick auf
    eine Serie (nicht auf eine Versuchsnummer) navigiert direkt zu
    ShowExperimentScreen für diese Serie und schliesst den Dialog.

    Vollständig generisch (kein Yarn-spezifischer State) - wird per Lazy-Import
    auch von screen_manage_jets.py wiederverwendet, um einen echten
    Zirkelimport zu vermeiden (dort importiert von hier, hier von dort)."""

    def __init__(self, series_list: List[Dict],
                 on_open_experiment: Optional[Callable[[int, int, str], None]] = None,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Used in Trial Series")
        self.resize(420, 480)
        self._on_open_experiment = on_open_experiment

        layout = QVBoxLayout(self)
        hint = QLabel("Click a series to open it. Expand a row (▸) to see which "
                       "trial numbers used this yarn.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.tree, 1)

        for s in series_list:
            top = QTreeWidgetItem([s["label"]])
            top.setData(0, Qt.UserRole, s)
            f = top.font(0)
            f.setUnderline(True)
            top.setFont(0, f)
            top.setForeground(0, QColor("#1a56db"))
            for vno in s["trial_numbers"]:
                top.addChild(QTreeWidgetItem([format_trial_number(vno)]))
            self.tree.addTopLevelItem(top)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("Close", objectName="GreyBtn")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _on_item_clicked(self, item: QTreeWidgetItem, _column: int):
        if item.parent() is not None:
            return  # Versuchsnummer-Zeile - nur informativ, nicht klickbar
        data = item.data(0, Qt.UserRole)
        if not data or not callable(self._on_open_experiment):
            return
        self.accept()
        self._on_open_experiment(data["exp_pk"], data["series_id"], data["experiment_id_text"])


# ---------- Screen ------------------------------------------------------------
class ManageYarnScreen(QWidget):
    def __init__(self, on_back_home=None, on_edit_yarn=None, on_open_experiment=None, on_new_yarn=None,
                 sidebar_callbacks: Optional[dict] = None):
        super().__init__()
        self.on_back_home = on_back_home
        self._on_edit_yarn = on_edit_yarn
        self._on_open_experiment = on_open_experiment
        self._on_new_yarn = on_new_yarn
        self._sidebar_nav_callbacks = sidebar_callbacks or {}
        self._sidebar_built_for_level = None
        # Inline aufgeklappte UsedInTrial-Zeilen: Sets der gerade aufgeklappten
        # Yarn-IDs bzw. TrialSeries-IDs. Die eigentlichen Zeilen sind echte,
        # eingefügte Model-Zeilen (siehe YarnTableModel.insert_detail_rows) -
        # kein Popup mehr (TrialUsageDialog bleibt als Klasse nur noch für
        # screen_manage_jets.py bestehen, wird hier nicht mehr benutzt).
        self._expanded_yarn_ids: set = set()
        self._expanded_series_ids: set = set()

        self.table: Optional[QTableView] = None
        self.model: Optional[YarnTableModel] = None
        self.proxy: Optional[ExpandableFilterProxy] = None
        self._header: Optional[FilterableHeaderView] = None
        self._column_order_dialog: Optional[ColumnOrderDialog] = None
        self._SCREEN_KEY = "manage_yarn"

        self.search_edit: Optional[QLineEdit] = None
        self.btn_reload: Optional[QPushButton] = None
        self.btn_new: Optional[QPushButton] = None
        self.btn_edit_form: Optional[QPushButton] = None
        self.btn_columns: Optional[QPushButton] = None
        self.btn_delete: Optional[QPushButton] = None
        self.btn_save: Optional[QPushButton] = None
        self.status_label: Optional[QLabel] = None
        self._name_search_col = -1

        self._id_col = 'ID'
        self._garntyp_col = None
        self._material_col = None
        self._yarngroup_col = None
        self._colour_col = None
        self._createdby_col = None
        self._garntyp_id2name: Dict[int, str] = {}
        self._material_id2name: Dict[int, str] = {}
        self._yarngroup_id2name: Dict[int, str] = {}
        self._colour_id2name: Dict[int, str] = {}
        self._createdby_id2name: Dict[object, str] = {}
        self._garntyp_delegate: Optional[ComboMapDelegate] = None
        self._material_delegate: Optional[ComboMapDelegate] = None
        self._yarngroup_delegate: Optional[ComboMapDelegate] = None
        self._colour_delegate: Optional[ComboMapDelegate] = None
        self._search_highlight_delegate: Optional[SearchHighlightDelegate] = None
        # Yarn hat kein alles-oder-nichts Read-only: AdminBox=0-User dürfen laut
        # Anforderung alles ausser MinStock bearbeiten und nicht löschen.
        self._can_delete = True
        self._can_edit_minstock = True

        self._build_ui()
        self.reload_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Keine TopBar (HeaderBar) mehr (2026-08-27, App-weiter Sidebar-
        # Rollout - siehe screen_home.py::_build_ui()-Docstring).
        self._sidebar, content_layout = sidebar_nav.wrap_body_with_sidebar(root)

        # Toolbar
        toolbar = QFrame()
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(24, 12, 24, 0)
        tl.setSpacing(8)

        self.search_edit = QLineEdit(placeholderText='Filter by Name…')
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._on_search_changed)

        self.btn_reload = QPushButton('Reload', objectName='GreyBtn')
        self.btn_reload.clicked.connect(self.reload_data)

        self.btn_new = QPushButton('New Yarn', objectName='GreenBtn')
        self.btn_new.clicked.connect(self._on_new)

        self.btn_edit_form = QPushButton('Edit in Form', objectName='GreyBtn')
        self.btn_edit_form.setToolTip('View/edit this yarn in a single-record form')
        self.btn_edit_form.clicked.connect(self._on_edit_form)

        self.btn_columns = QPushButton('Columns…', objectName='GreyBtn')
        self.btn_columns.setToolTip('Reorder columns via a drag & drop list')
        self.btn_columns.clicked.connect(self._on_columns_clicked)

        self.btn_delete = QPushButton('Delete', objectName='GreyBtn')
        self.btn_delete.clicked.connect(self._on_delete)

        self.btn_save = QPushButton('Save Changes', objectName='PurpleBtn')
        self.btn_save.clicked.connect(self.save_changes)

        self.status_label = QLabel('')

        tl.addWidget(self.search_edit, 1)
        tl.addWidget(self.btn_reload, 0)
        tl.addWidget(self.btn_new, 0)
        tl.addWidget(self.btn_edit_form, 0)
        tl.addWidget(self.btn_columns, 0)
        tl.addWidget(self.btn_delete, 0)
        tl.addWidget(self.btn_save, 0)
        tl.addWidget(self.status_label, 0, Qt.AlignVCenter)
        # Kontext-Hilfe EN/DE/ES (Nutzerwunsch 2026-10-13, ui/widgets/multilang_help.py)
        from ui.widgets.multilang_help import make_help_button
        tl.addWidget(make_help_button("How does Manage Yarn work?", self._open_help), 0)

        # Tabelle
        self.table = QTableView(objectName='YarnTable')
        # FilterableHeaderView (aus screen_manage_jets) statt Standard-Header:
        # Rechtsklick auf eine Spalte -> "contains"/"von-bis"-Filter, kombinierbar
        # mit der Suchleiste oben (die filtert nur die Name-Spalte, siehe
        # _on_search_changed). Sections movable fuer Drag&Drop-Umsortieren
        # (kein Freeze-Bereich hier, anders als bei Manage Jets).
        self._header = FilterableHeaderView(Qt.Horizontal, self.table)
        self._header.setSectionsMovable(True)
        self.table.setHorizontalHeader(self._header)
        self.table.setAlternatingRowColors(False)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setStyleSheet("""
            QTableView#YarnTable { gridline-color: #B5D7B5; }
            QHeaderView::section {
                background: #E9F6E9; color: #2b2b2b; font-weight: 600;
                border: 1px solid #B5D7B5; padding: 4px 6px;
            }
            QTableView#YarnTable::item { color: black; }
            QTableView#YarnTable::item:selected { background: #b7d6ff; color: black; }
        """
            .replace("#B5D7B5", accent_gridline())
            .replace("#E9F6E9", accent_tint()))
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        # 'clicked' (QModelIndex only, no pixel position) reicht nicht mehr aus,
        # seit eine TrialSeries-Zeile Dreieck (aufklappen) und restliche Zeile
        # (navigieren) unterschiedlich behandelt - siehe eventFilter/_handle_table_click.
        self.table.viewport().installEventFilter(self)
        # Pointing-hand cursor over "Yes" cells signals clickability without
        # touching item painting (which fought the stylesheet, see YarnTableModel).
        self.table.setMouseTracking(True)
        self.table.entered.connect(self._on_cell_hovered)
        # Sortieren/Filtern würde eine inline aufgeklappte Detailzeile vom
        # falschen Platz reißen - ExpandableFilterProxy klappt deshalb selbst
        # (vor jedem sort()/set_*_filter()) alles zu, siehe before_change dort.

        content_layout.addWidget(toolbar, 0)
        content_layout.addWidget(self.table, 1)

        # Footer ganz unten
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

    # --- Data layer ---
    def _load_yarn(self) -> List[Dict]:
        # Automatisch angelegte Halbfabrikat-"Schatten"-Garne (Multimaschinen-
        # Ply-Verknüpfung, siehe screen_create_experiment.get_or_create_shadow_yarn)
        # sollen den Katalog nicht zuschwemmen.
        src_col = _resolve_field(['SourceTrialID'], get_columns_map('tblYarn'))
        where = f' WHERE y.{src_col} IS NULL' if src_col else ''
        # UsedInTrial/StockKg sind reine Anzeige-Spalten (keine echten tblYarn-
        # Felder, analog zu has_files bei Jets): ob dieses Garn in mindestens
        # einer Ply-Zeile (tbltrialsettings.YarnID) verwendet wurde, und wie
        # viel kg aktuell auf Lager sind (Summe tblYarnSpool.WeightKg über alle
        # Spulen mit Status='in stock' - dieselbe Logik wie screen_yarn_stock.py,
        # nur serverseitig statt python-seitig aufsummiert).
        sql = (
            'SELECT y.*, '
            'CASE WHEN EXISTS (SELECT 1 FROM tbltrialsettings ts WHERE ts.YarnID = y.ID) '
            'THEN 1 ELSE 0 END AS UsedInTrial, '
            "COALESCE((SELECT SUM(sp.WeightKg) FROM tblYarnSpool sp "
            "WHERE sp.YarnID = y.ID AND sp.Status = 'in stock'), 0) AS StockKg "
            f'FROM tblYarn y{where}'
        )
        return fetch_all(sql, [])

    def reload_data(self):
        # Vor dem Modell-Austausch alle inline aufgeklappten Zeilen sauber
        # zuklappen (das eingebettete Widget hängt am alten Modell/Proxy).
        self._collapse_all_usage_rows()
        rows = self._load_yarn()
        headers = list(rows[0].keys()) if rows else [self._id_col]

        # SourceTrialID (Halbfabrikat-Shadow-Yarn-Verknüpfung) für NIEMANDEN
        # sichtbar - Nutzerwunsch: "den möchte ich in der tabelle und im
        # formular lieber nicht sehen. das verwirrt nur". Unconditional (nicht
        # nur für Nicht-Superuser wie CreatedBy/CreationDate unten), weil
        # _load_yarn() ohnehin schon `WHERE SourceTrialID IS NULL` filtert -
        # die Spalte wäre für jede hier angezeigte Zeile immer leer.
        headers = [h for h in headers if _canon(h) != 'sourcetrialid']

        # Wer dieses Garn angelegt hat & wann - versteckt für alle ausser
        # Superuser (nicht nur read-only, siehe YarnTableModel._createdby_col
        # etc. für die generelle Nicht-Editierbarkeit).
        if not app_meta.is_superuser_level():
            headers = [h for h in headers if _canon(h) not in ('createdby', 'creationdate')]

        # find ID column
        for h in headers:
            if h.lower() == 'id':
                self._id_col = h
                break

        # identify FK columns in tblYarn
        self._garntyp_col = None
        self._material_col = None
        self._yarngroup_col = None
        self._colour_col = None
        self._createdby_col = None
        for h in headers:
            k = _canon(h)
            if k == 'garntyp':
                self._garntyp_col = h
            if k == 'material':
                self._material_col = h
            if k in {'yarngroupid', 'yarngroup', 'groupid'}:
                # priorisiere das explizite YarnGroupID falls vorhanden
                if self._yarngroup_col is None or k == 'yarngroupid':
                    self._yarngroup_col = h
            if k in {'colourid', 'colour', 'color', 'colorid'}:
                self._colour_col = h
            if k == 'createdby':
                self._createdby_col = h

        # load FK maps
        self._garntyp_id2name, _ = load_garntyp_map()
        self._material_id2name, _ = load_material_map()
        self._createdby_id2name = {}
        if self._createdby_col:
            try:
                from db.user_directory import load_user_id_to_name
                self._createdby_id2name = load_user_id_to_name()
            except Exception:
                pass
        try:
            self._yarngroup_id2name, _ = load_yarngroup_map()
        except Exception:
            # YarnGroup ist optional; Screen funktioniert auch ohne
            self._yarngroup_id2name = {}
        try:
            self._colour_id2name, _ = load_colour_map()
        except Exception:
            # tblColour existiert (Stand 2026-08-24) nur auf dev_local/prod, nicht auf dev
            self._colour_id2name = {}

        # build model
        self.model = YarnTableModel(
            rows, headers,
            id_column=self._id_col,
            garntyp_col=self._garntyp_col, garntyp_map=self._garntyp_id2name,
            material_col=self._material_col, material_map=self._material_id2name,
            yarngroup_col=self._yarngroup_col, yarngroup_map=self._yarngroup_id2name,
            colour_col=self._colour_col, colour_map=self._colour_id2name,
            createdby_col=self._createdby_col, createdby_map=self._createdby_id2name,
            minstock_locked=not self._can_edit_minstock
        )

        # proxy (filter/sort)
        if not self.proxy:
            self.proxy = ExpandableFilterProxy(self)
            self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
            self.proxy.setDynamicSortFilter(True)
            self.proxy.before_change = self._collapse_all_usage_rows
            self._header.set_proxy(self.proxy)
        self.proxy.setSourceModel(self.model)
        self._configure_search_column(headers)
        self.proxy.setSortRole(Qt.EditRole)
        self.table.setModel(self.proxy)

        # delegates for FK columns
        if self._garntyp_col is not None:
            if not self._garntyp_delegate:
                self._garntyp_delegate = ComboMapDelegate(
                    self._garntyp_id2name, self.table)
            self.table.setItemDelegateForColumn(headers.index(
                self._garntyp_col), self._garntyp_delegate)

        if self._material_col is not None:
            if not self._material_delegate:
                self._material_delegate = ComboMapDelegate(
                    self._material_id2name, self.table)
            self.table.setItemDelegateForColumn(headers.index(
                self._material_col), self._material_delegate)

        if self._yarngroup_col is not None and self._yarngroup_id2name:
            if not self._yarngroup_delegate:
                self._yarngroup_delegate = ComboMapDelegate(
                    self._yarngroup_id2name, self.table)
            self.table.setItemDelegateForColumn(headers.index(
                self._yarngroup_col), self._yarngroup_delegate)

        if self._colour_col is not None:
            # Kein "and self._colour_id2name"-Guard wie bei den übrigen FK-
            # Spalten: der "+ Add new colour…"-Eintrag (siehe add_new_callback)
            # muss auch dann verfügbar sein, wenn noch gar keine Farbe existiert
            # (Bootstrap der allerersten Farbe).
            if not self._colour_delegate:
                self._colour_delegate = ComboMapDelegate(
                    self._colour_id2name, self.table,
                    add_new_callback=lambda w: quick_add_colour(w))
            self.table.setItemDelegateForColumn(headers.index(
                self._colour_col), self._colour_delegate)

        # Die Suchleiste durchsucht nur die Name-Spalte. Der wiederverwendete
        # Jets-Delegate hebt darin alle passenden Suchbegriffe farbig hervor.
        if self._name_search_col >= 0:
            if not self._search_highlight_delegate:
                self._search_highlight_delegate = SearchHighlightDelegate(
                    self.proxy, lambda: [self._name_search_col], parent=self.table)
            self.table.setItemDelegateForColumn(
                self._name_search_col, self._search_highlight_delegate)

        self.table.resizeColumnsToContents()
        # sort by ID ascending
        id_idx = 0
        for i, h in enumerate(headers):
            if h == self._id_col:
                id_idx = i
                break
        self.table.sortByColumn(id_idx, Qt.AscendingOrder)
        self._apply_permissions_ui()
        self._restore_column_order()

        self._set_status(f"{len(rows)} yarn(s) loaded.")
        self._on_search_changed(self.search_edit.text())

    def set_permissions(self, can_delete: bool, can_edit_minstock: bool):
        """Setzt die granularen Yarn-Rechte: anders als bei Jets/Top Plates gibt
        es hier kein alles-oder-nichts Read-only - AdminBox=0-User dürfen laut
        Anforderung New/Save/Zell-Editing nutzen, nur MinStock und Löschen
        bleiben Admin-Box/AccessLevel>=3 vorbehalten. Von main.py bei jeder
        Navigation zu diesem Screen mit dem aktuellen Permission-Stand
        aufgerufen (der eingeloggte User kann sich seit dem letzten Öffnen
        geändert haben)."""
        self._can_delete = bool(can_delete)
        self._can_edit_minstock = bool(can_edit_minstock)
        self._apply_permissions_ui()

    def _apply_permissions_ui(self):
        if self.model is not None:
            self.model.set_minstock_locked(not self._can_edit_minstock)
            # dataChanged statt layoutChanged: hier ändert sich nur, ob die
            # MinStock-Spalte enabled/disabled gerendert wird (reiner Repaint,
            # keine Zeilen/Spalten-Umordnung). layoutChanged ist für echte
            # Strukturänderungen gedacht und invalidiert dabei persistente
            # Model-Indizes/den Selection-State der View - bei jedem erneuten
            # Sichtbarwerden von ManageYarnScreen (z.B. Cancel im "Edit in
            # Form"-Formular, das jedes Mal set_permissions() aufruft) wieder-
            # holt aufgerufen, führte das reproduzierbar zu einem Absturz
            # (Windows access violation) im nächsten selectRow() - siehe
            # CLAUDE.md. Per gezielter Bisektion isoliert: reines
            # `model.layoutChanged.emit()` nach einer Zeilenauswahl reicht
            # bereits, komplett unabhängig von NewYarnScreen.
            rows = self.model.rowCount()
            cols = self.model.columnCount()
            if rows and cols:
                self.model.dataChanged.emit(
                    self.model.index(0, 0), self.model.index(rows - 1, cols - 1))
        if self.btn_delete is not None:
            self.btn_delete.setEnabled(self._can_delete)
            self.btn_delete.setToolTip(
                "" if self._can_delete else
                "Read-only access – you don't have permission to delete records.")

    def save_changes(self):
        if not self.model:
            return
        dirty_rows = self.model.dirty_rows()
        if not dirty_rows:
            self._set_status('No changes to save.')
            return
        id_col = self.model.id_column() or 'ID'
        dpf_col = self.model.dpf_column_name()
        minstock_col = self.model.minstock_column_name()
        usedintrial_col = self.model.usedintrial_column_name()
        stockkg_col = self.model.stockkg_column_name()

        # Duplicate-Check VOR jedem Schreiben (Nutzerwunsch: "es soll bei jedem
        # speichern/aktualisieren geprüft werden"). Bricht die GESAMTE
        # Save-Operation ab, falls der Nutzer bei irgendeiner geflaggten Zeile
        # "No" wählt - kein selektives Teil-Speichern, um den Dirty-State nicht
        # pro Zeile nachführen zu müssen (dirty_rows()/clear_dirty() kennen nur
        # "alles" oder "nichts"). Läuft vor dem eigentlichen Save-Loop, damit
        # bereits geschriebene Zeilen bei einem späteren Abbruch nicht
        # inkonsistent hinter noch nicht geschriebenen zurückbleiben.
        for r in dirty_rows:
            match = find_duplicate_yarn(r, exclude_id=r.get(id_col))
            if match and not confirm_save_despite_duplicate(self, *match):
                self._set_status('Save cancelled (possible duplicate yarn).', error=True)
                return

        # Defense-in-depth: der Model-Flag-Guard verhindert schon, dass
        # MinStock überhaupt dirty werden kann, aber ein frischer Live-Check
        # hier stellt sicher, dass nie ein MinStock-Wert geschrieben wird,
        # wenn der eingeloggte User dafuer (inzwischen) keine Rechte hat.
        can_edit_minstock = app_meta.can_edit_min_stock()
        total = 0
        try:
            for r in dirty_rows:
                if id_col not in r:
                    raise ValueError(
                        f"Row has no '{id_col}' field; cannot save.")
                rid = r[id_col]
                cols = [c for c in self.model.headers() if c !=
                        id_col and c in r]
                # exclude computed DPF column from updates
                if dpf_col and dpf_col in cols:
                    cols.remove(dpf_col)
                if minstock_col and not can_edit_minstock and minstock_col in cols:
                    cols.remove(minstock_col)
                # UsedInTrial/StockKg sind keine echten tblYarn-Felder (siehe
                # _load_yarn) - müssen zwingend raus, sonst schlägt das UPDATE
                # mit "Unknown column" fehl, sobald irgendeine Zelle der Zeile
                # dirty ist.
                if usedintrial_col and usedintrial_col in cols:
                    cols.remove(usedintrial_col)
                if stockkg_col and stockkg_col in cols:
                    cols.remove(stockkg_col)
                if not cols:
                    continue
                set_sql = ', '.join([f'[{c}] = ?' for c in cols])
                sql = f'UPDATE [tblYarn] SET {set_sql} WHERE [{id_col}] = ?'
                params = [r[c] for c in cols] + [rid]
                total += execute(sql, params) or 0
            self._set_status(f'Saved {total} update(s).')
            self.model.clear_dirty()
        except Exception as e:
            QMessageBox.critical(self, 'Save failed', str(e))
            self._set_status(f'Save failed: {e}', error=True)

    def _on_new(self):
        """Nutzerwunsch: "direkt das Formular öffnen und den Eintrag erst
        wirklich in die DB speichern, wenn ich da auf Speichern klicke" - löst
        das frühere Verhalten ab, das hier sofort einen leeren "New Yarn"-
        Datensatz per INSERT anlegte, noch bevor irgendwelche Werte erfasst
        waren (Cancel im "Edit in Form"-Umweg über diese Zeile musste dann
        einen halb angelegten Datensatz wieder aufräumen - strukturelle
        Ursache für den vom Nutzer gemeldeten Crash beim Abbrechen, auch wenn
        er sich in einer headless-Nachstellung nicht reproduzieren liess).
        Öffnet stattdessen direkt main.py's NewYarnScreen im Neuanlage-Modus
        (siehe on_new_yarn/main.py._go_new_yarn_form) - bei Cancel ist dadurch
        strukturell nichts in der DB, das aufgeräumt werden müsste."""
        if callable(self._on_new_yarn):
            self._on_new_yarn()
            return
        QMessageBox.information(
            self, 'New Yarn', "'New Yarn' is currently not available.")

    def _on_row_double_clicked(self, index):
        """Doppelklick: auf einer Detailzeile (Serie/Versuch) nichts - die
        Serien-Zeile navigiert bereits per Einfachklick (siehe
        _handle_table_click), ein Doppelklick soll dort nicht zusätzlich das
        Formular öffnen. Sonst wie bisher → Formular-Ansicht."""
        if self.model and self.proxy and index.isValid():
            kind, _src_row = self._row_kind_at(index)
            if kind in ('series', 'trial'):
                return
        self._on_edit_form()

    def _usedintrial_col_idx(self) -> int:
        """Logischer Spaltenindex von UsedInTrial, oder -1 falls nicht vorhanden."""
        if not self.model:
            return -1
        usedintrial_col = self.model.usedintrial_column_name()
        if not usedintrial_col:
            return -1
        try:
            return self.model.headers().index(usedintrial_col)
        except ValueError:
            return -1

    def _row_kind_at(self, index) -> Tuple[str, int]:
        """Source-Zeilenart + Source-Row-Index für einen (Proxy-)Index, oder
        ('yarn', -1) falls nicht auflösbar."""
        if not index.isValid() or not self.model or not self.proxy:
            return 'yarn', -1
        try:
            src_row = self.proxy.mapToSource(index).row()
            rows = self.model.rows()
            if src_row < 0 or src_row >= len(rows):
                return 'yarn', -1
            return rows[src_row].get('_row_kind', 'yarn'), src_row
        except Exception:
            return 'yarn', -1

    def _series_triangle_zone_width(self) -> int:
        """Breite (px) des Dreieck-Klickbereichs am Zeilenanfang einer
        TrialSeries-Detailzeile - deckt Einzug + Pfeilzeichen + etwas Puffer ab
        (siehe _series_label: '      ▸  <Label>...'). Alles rechts davon ist
        der "Text"-Teil der Zeile (navigiert statt aufzuklappen)."""
        fm = self.table.fontMetrics()
        return fm.horizontalAdvance('      ▸  ') + 8

    def _handle_table_click(self, pos):
        """Zentrale Klick-Logik (aus einem QEvent.MouseButtonRelease-Filter auf
        dem Viewport aufgerufen, nicht aus dem 'clicked'-Signal, weil wir die
        Pixel-Position brauchen): Klick auf eine "Yes ▸/▾"-Zelle klappt die
        Yarn-Zeile auf/zu. Auf einer TrialSeries-Zeile klappt ein Klick auf das
        Dreieck selbst die Versuchsnummern auf/zu, ein Klick auf den Rest der
        Zeile (nicht wie ein Link dargestellt, aber klickbar) navigiert direkt
        zum Experiment. Versuchsnummer-Zeilen sind nur informativ."""
        if not self.model or not self.proxy:
            return
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        kind, src_row = self._row_kind_at(index)
        if src_row < 0:
            return
        if kind == 'yarn':
            ui_idx = self._usedintrial_col_idx()
            disp = index.data(Qt.DisplayRole)
            if ui_idx < 0 or index.column() != ui_idx or not disp or not str(disp).startswith('Yes'):
                return
            yarn_id = self.model.rows()[src_row].get(self._id_col)
            if yarn_id in self._expanded_yarn_ids:
                self._collapse_yarn_row(yarn_id)
            else:
                self._expand_yarn_row(yarn_id, index)
        elif kind == 'series':
            row = self.model.rows()[src_row]
            payload = row['_series_payload']
            series_id = payload['series_id']
            rect = self.table.visualRect(index)
            on_triangle = (pos.x() - rect.x()) <= self._series_triangle_zone_width()
            if on_triangle:
                if series_id in self._expanded_series_ids:
                    self._collapse_series_row(series_id)
                else:
                    self._expand_series_row(series_id, index)
            elif callable(self._on_open_experiment):
                self._on_open_experiment(payload['exp_pk'], payload['series_id'], payload['experiment_id_text'])
        # 'trial'-Zeilen: nicht klickbar

    def eventFilter(self, obj, event):
        """Fängt Linksklicks auf dem Tabellen-Viewport ab, um die Klick-
        Position (für die Dreieck-vs-Text-Unterscheidung auf Serien-Zeilen) zu
        bekommen - das 'clicked'-Signal liefert nur den Index, keine Pixel."""
        if (obj is self.table.viewport() and event.type() == QEvent.MouseButtonRelease
                and event.button() == Qt.LeftButton):
            self._handle_table_click(event.pos())
        return super().eventFilter(obj, event)

    def _on_cell_hovered(self, index):
        """Zeigt einen Hand-Cursor über "Yes …"-Zellen sowie über kompletten
        TrialSeries-Detailzeilen (klickbar, aber ohne Link-Farbe/Unterstreichung
        - siehe YarnTableModel._detail_row_data)."""
        clickable = False
        if index.isValid():
            kind, src_row = self._row_kind_at(index)
            if src_row >= 0:
                if kind == 'series':
                    clickable = True
                elif kind == 'yarn':
                    ui_idx = self._usedintrial_col_idx()
                    disp = index.data(Qt.DisplayRole)
                    clickable = (ui_idx >= 0 and index.column() == ui_idx
                                 and bool(disp) and str(disp).startswith('Yes'))
        self.table.viewport().setCursor(Qt.PointingHandCursor if clickable else Qt.ArrowCursor)

    @staticmethod
    def _fmt_num(v) -> Optional[str]:
        """Kompakte Zahlendarstellung fürs Trial-Detail-Label (800.00 -> '800',
        3.50 -> '3.5') - dieselbe Trim-Idee wie an anderen Anzeige-Stellen im
        Projekt, nur lokal statt geteilt, weil hier nur zwei Aufrufstellen."""
        if v is None:
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        return f'{f:.0f}' if f == int(f) else f'{f:.1f}'

    def _fetch_yarn_usage(self, yarn_id) -> List[Dict]:
        """Alle TrialSeries (+ deren Versuchsnummern inkl. Jet/Overfeed/Speed),
        die dieses Garn über eine Ply-Zeile (tbltrialsettings.YarnID) verwenden.
        Jet/OF%/Speed sind die "primären" Prozessparameter, die auch der ATY-
        Advisor (advisor_worker.py) als Hauptvergleichsachse behandelt - aber
        ATY-Maschinen (tblmaschine.Maschinentyp -> tblmaschinentypen 'ATY',
        z.B. 'SSM DP2T') führen Overfeed getrennt nach Core/Effect-Schaft
        (`Shaft1,1Core_OF`/`Shaft1,2Effect_OF`) und die Geschwindigkeit unter
        `Shaft2Speed` statt `SpeedShaft2` - per Cross-Check gegen echte Daten
        verifiziert (dev_local: `SpeedShaft2` ist bei ATY-Trials zu 0% befüllt,
        `Shaft2Speed` zu 96%; umgekehrt bei DTY/AC). Für alle anderen
        Maschinentypen bleibt das bisherige `Shaft2x_OF`/`SpeedShaft2`-Paar
        unverändert massgeblich."""
        sql = (
            'SELECT s.ID AS SeriesID, s.ExperimentID AS ExpPK, '
            'e.ExperimentID AS ExperimentIdText, s.SeriesName, m.Maschine AS MachineName, '
            'mt.Maschinentyp AS MachineType, '
            't.Versuchsnummer, j.Jet AS JetName, t.Shaft2x_OF AS OverfeedPct, '
            't.SpeedShaft2 AS SpeedMMin, t.`Shaft1,1Core_OF` AS CoreOfPct, '
            't.`Shaft1,2Effect_OF` AS EffectOfPct, t.Shaft2Speed AS AtySpeedMMin '
            'FROM tbltrialsettings ts '
            'JOIN tbltrial t ON t.ID = ts.TrialID '
            'JOIN tbltrialseries s ON s.ID = t.TrialSeriesID '
            'JOIN tblexperimente e ON e.ID = s.ExperimentID '
            'LEFT JOIN tblmaschine m ON m.ID = s.MachineID '
            'LEFT JOIN tblmaschinentypen mt ON mt.ID = m.Maschinentyp '
            'LEFT JOIN tbljets j ON j.ID = t.JetID '
            'WHERE ts.YarnID = ? '
            'ORDER BY e.ExperimentID, s.SeriesName, t.Versuchsnummer'
        )
        rows = fetch_all(sql, [yarn_id])
        series_map: Dict[object, Dict] = {}
        for r in rows:
            sid = r.get('SeriesID')
            if sid not in series_map:
                exp_txt = r.get('ExperimentIdText') or ''
                series_name = r.get('SeriesName') or ''
                label = f"{exp_txt}.{series_name}" if exp_txt else series_name
                series_map[sid] = {
                    'series_id': sid,
                    'exp_pk': r.get('ExpPK'),
                    'experiment_id_text': exp_txt,
                    'label': label,
                    'machine_name': r.get('MachineName'),
                    'trial_numbers': [],
                }
            vno = r.get('Versuchsnummer')
            if vno is None:
                continue
            existing_vnos = {t['vno'] for t in series_map[sid]['trial_numbers']}
            if vno not in existing_vnos:
                is_aty = r.get('MachineType') == 'ATY'
                speed_val = r.get('AtySpeedMMin') if is_aty else r.get('SpeedMMin')
                series_map[sid]['trial_numbers'].append({
                    'vno': vno,
                    'jet': r.get('JetName'),
                    'is_aty': is_aty,
                    'of_pct': self._fmt_num(r.get('OverfeedPct')),
                    'core_of': self._fmt_num(r.get('CoreOfPct')),
                    'effect_of': self._fmt_num(r.get('EffectOfPct')),
                    'speed': self._fmt_num(speed_val),
                })
        return list(series_map.values())

    def _find_source_row_for_id(self, yarn_id) -> Optional[int]:
        if not self.model:
            return None
        for i, row in enumerate(self.model.rows()):
            if row.get('_row_kind', 'yarn') == 'yarn' and row.get(self._id_col) == yarn_id:
                return i
        return None

    def _find_source_row_for_series(self, series_id) -> Optional[int]:
        if not self.model:
            return None
        for i, row in enumerate(self.model.rows()):
            if row.get('_row_kind') == 'series' and row.get('_series_payload', {}).get('series_id') == series_id:
                return i
        return None

    def _apply_full_row_span(self, src_row: int):
        """Merged die ganze Zeile zu einer Zelle (Spalte 0 trägt das Label,
        siehe YarnTableModel._detail_row_data) - für neu eingefügte
        Detailzeilen direkt nach dem Insert aufgerufen."""
        if not self.model or not self.proxy:
            return
        proxy_index = self.proxy.mapFromSource(self.model.index(src_row, 0))
        if proxy_index.isValid():
            self.table.setSpan(proxy_index.row(), 0, 1, self.model.columnCount())

    def _clear_full_row_span(self, src_row: int):
        """Gegenstück zu _apply_full_row_span() - vor dem Entfernen einer
        Detailzeile aufgerufen, damit kein Span auf eine dann falsche Zeile
        zeigt."""
        if not self.model or not self.proxy:
            return
        proxy_index = self.proxy.mapFromSource(self.model.index(src_row, 0))
        if proxy_index.isValid():
            self.table.setSpan(proxy_index.row(), 0, 1, 1)

    @staticmethod
    def _series_label(payload: Dict, expanded: bool) -> str:
        arrow = '▾' if expanded else '▸'
        n = len(payload['trial_numbers'])
        base = f'      {arrow}  {payload["label"]}   ({n} trial{"s" if n != 1 else ""})'
        machine_name = payload.get('machine_name')
        return f'{base} - {machine_name}' if machine_name else base

    def _set_series_row_label(self, row_idx: int, payload: Dict, expanded: bool):
        self.model.rows()[row_idx]['_label'] = self._series_label(payload, expanded)
        idx0 = self.model.index(row_idx, 0)
        self.model.dataChanged.emit(idx0, idx0, [Qt.DisplayRole])

    def _expand_yarn_row(self, yarn_id, clicked_index):
        """Fügt für jede TrialSeries, die dieses Garn verwendet, eine echte
        Zeile direkt unter der Yarn-Zeile ein (nicht wie ein Link dargestellt,
        aber klickbar - Klick klappt die Versuchsnummern auf, siehe
        _expand_series_row; Doppelklick öffnet das Experiment)."""
        try:
            series_list = self._fetch_yarn_usage(yarn_id)
        except Exception as e:
            QMessageBox.critical(self, 'Used in Trial Series', f'Could not load usage: {e}')
            return
        if not series_list:
            QMessageBox.information(
                self, 'Used in Trial Series',
                'No trial series found for this yarn (data may have changed - try Reload).')
            return

        src_row = self.proxy.mapToSource(clicked_index).row()
        detail_rows = []
        for order, s in enumerate(series_list, start=1):
            detail_rows.append({
                '_row_kind': 'series',
                '_anchor_yarn_id': yarn_id,
                '_order': float(order),
                '_series_payload': s,
                '_label': self._series_label(s, expanded=False),
            })
        self.model.insert_detail_rows(src_row, detail_rows)
        for offset in range(1, len(detail_rows) + 1):
            self._apply_full_row_span(src_row + offset)

        self._expanded_yarn_ids.add(yarn_id)
        self.model.set_expanded(yarn_id, True)

    def _collapse_yarn_row(self, yarn_id):
        """Entfernt den kompletten Detail-Block unter der Yarn-Zeile wieder
        (die Serien-Zeilen UND alle evtl. noch offenen Versuchsnummer-Zeilen
        darunter - beides liegt lückenlos hintereinander, siehe
        YarnTableModel.local_order)."""
        if yarn_id not in self._expanded_yarn_ids:
            return
        src_row = self._find_source_row_for_id(yarn_id)
        self._expanded_yarn_ids.discard(yarn_id)
        self.model.set_expanded(yarn_id, False)
        if src_row is None:
            return
        rows = self.model.rows()
        i = src_row + 1
        removed_series_ids = []
        while i < len(rows) and rows[i].get('_row_kind', 'yarn') != 'yarn':
            if rows[i].get('_row_kind') == 'series':
                removed_series_ids.append(rows[i]['_series_payload']['series_id'])
            i += 1
        count = i - (src_row + 1)
        if count:
            for j in range(src_row + 1, src_row + 1 + count):
                self._clear_full_row_span(j)
            self.model.remove_rows_span(src_row + 1, count)
        for sid in removed_series_ids:
            self._expanded_series_ids.discard(sid)

    @staticmethod
    def _trial_label(t: Dict) -> str:
        """'V<n> - <Jet>, <OF>% OF, <Speed>m/min' (ATY: 'V<n> - <Jet>, <Core>%
        Core OF, <Effect>% Effect OF, <Speed>m/min', Core/Effect getrennt statt
        einer einzelnen OF-Zahl - siehe _fetch_yarn_usage). Jeder Teil ausser
        V<n> entfällt einzeln, wenn der Wert fehlt (z.B. Trial ohne
        zugewiesenen Jet, oder Prozessparameter, die für diesen Maschinentyp
        gar nicht erfasst werden)."""
        parts = []
        if t.get('jet'):
            parts.append(str(t['jet']))
        if t.get('is_aty'):
            if t.get('core_of') is not None:
                parts.append(f"{t['core_of']}% Core OF")
            if t.get('effect_of') is not None:
                parts.append(f"{t['effect_of']}% Effect OF")
        elif t.get('of_pct') is not None:
            parts.append(f"{t['of_pct']}% OF")
        if t.get('speed') is not None:
            parts.append(f"{t['speed']}m/min")
        suffix = f" - {', '.join(parts)}" if parts else ''
        return f"            •  V{t['vno']}{suffix}"

    def _expand_series_row(self, series_id, clicked_index):
        """Fügt für jede Versuchsnummer dieser TrialSeries eine (nicht
        klickbare, rein informative) Zeile direkt unter der Serien-Zeile ein."""
        src_row = self.proxy.mapToSource(clicked_index).row()
        row = self.model.rows()[src_row]
        payload = row['_series_payload']
        yarn_id = row['_anchor_yarn_id']
        base_order = row.get('_order', 0.0)
        trial_rows = [{
            '_row_kind': 'trial',
            '_anchor_yarn_id': yarn_id,
            '_order': base_order + i / 100000.0,
            '_label': self._trial_label(t),
        } for i, t in enumerate(payload['trial_numbers'], start=1)]
        self.model.insert_detail_rows(src_row, trial_rows)
        for offset in range(1, len(trial_rows) + 1):
            self._apply_full_row_span(src_row + offset)

        self._expanded_series_ids.add(series_id)
        self._set_series_row_label(src_row, payload, expanded=True)

    def _collapse_series_row(self, series_id):
        if series_id not in self._expanded_series_ids:
            return
        src_row = self._find_source_row_for_series(series_id)
        self._expanded_series_ids.discard(series_id)
        if src_row is None:
            return
        rows = self.model.rows()
        i = src_row + 1
        while i < len(rows) and rows[i].get('_row_kind') == 'trial':
            i += 1
        count = i - (src_row + 1)
        if count:
            for j in range(src_row + 1, src_row + 1 + count):
                self._clear_full_row_span(j)
            self.model.remove_rows_span(src_row + 1, count)
        payload = self.model.rows()[src_row]['_series_payload']
        self._set_series_row_label(src_row, payload, expanded=False)

    def _collapse_all_usage_rows(self):
        """Klappt alles zu - aufgerufen vor jedem Reload sowie (über
        ExpandableFilterProxy.before_change) vor jedem Sortieren/Filtern,
        weil Detailzeilen an einer festen Position relativ zu ihrer Eltern-
        Zeile hängen und sonst verstreut würden."""
        for yarn_id in list(self._expanded_yarn_ids):
            self._collapse_yarn_row(yarn_id)
        self._expanded_series_ids.clear()

    def _on_edit_form(self):
        """Öffnet den selektierten Yarn im Einzeldatensatz-Formular (NewYarnScreen).
        Übersichtlicher als die Pivot-Tabelle für einen einzelnen Datensatz –
        bleibt editierbar (MinStock-Sperre greift dort separat, siehe main.py)."""
        if not callable(self._on_edit_yarn):
            self._set_status('Edit in Form not available.', error=True)
            return
        src = self._source_selection_rows()
        if not src:
            self._set_status('No row selected.')
            return
        try:
            row_dict = dict(self.model.rows()[src[0]])
        except Exception:
            self._set_status('Could not read selected row.', error=True)
            return
        self._on_edit_yarn(row_dict)
        self._set_status('')

    def _on_delete(self):
        # Live-Check statt nur self._can_delete: echte Autorität für den
        # tatsächlichen DELETE, unabhängig davon ob die UI-Sperre (Button
        # disabled) irgendwie umgangen wurde.
        if not self.model or not app_meta.can_use_admin_box():
            return
        src = self._source_selection_rows()
        if not src:
            self._set_status('No rows selected.')
            return
        id_col = self.model.id_column() or 'ID'
        ids = []
        for r in src:
            try:
                rid = self.model.rows()[r].get(id_col)
                if rid is not None:
                    ids.append(rid)
            except Exception:
                pass
        if not ids:
            self._set_status('No valid IDs to delete.')
            return

        if QMessageBox.question(self, 'Confirm Delete', f'Delete {len(ids)} yarn(s)?') != QMessageBox.Yes:
            return
        try:
            placeholders = ','.join(['?'] * len(ids))
            sql = f'DELETE FROM [tblYarn] WHERE [{id_col}] IN ({placeholders})'
            execute(sql, ids)
            self.reload_data()
            self._set_status(f'Deleted {len(ids)} yarn(s).')
        except Exception as e:
            QMessageBox.critical(self, 'Delete failed', str(e))
            self._set_status(f'Delete failed: {e}', error=True)

    # --- helpers ---
    def _source_selection_rows(self) -> List[int]:
        if not self.table or not self.proxy:
            return []
        sel = self.table.selectionModel().selectedRows()
        rows = []
        for idx in sel:
            try:
                src_i = self.proxy.mapToSource(idx)
                rows.append(src_i.row())
            except Exception:
                pass
        rows.sort()
        return rows

    def _select_row_by_id(self, select_id: Optional[int]):
        if not self.model or select_id is None:
            return
        id_col = None
        headers = self.model.headers()
        for i, h in enumerate(headers):
            if h.lower() == self._id_col.lower():
                id_col = i
                break
        if id_col is None:
            return
        for r, row in enumerate(self.model.rows()):
            if row.get(self._id_col) == select_id:
                if self.proxy:
                    for pr in range(self.proxy.rowCount()):
                        src = self.proxy.mapToSource(
                            self.proxy.index(pr, id_col))
                        if src.row() == r:
                            self.table.selectRow(pr)
                            self.table.scrollTo(self.proxy.index(pr, 0))
                            return
                else:
                    self.table.selectRow(r)
                    self.table.scrollTo(self.model.index(r, 0))
                return

    def _configure_search_column(self, headers: List[str]):
        """Ermittelt die Name-Spalte für die Suchleiste (durchsucht nur diese,
        unabhängig von den per-Spalten-Filtern im Header-Rechtsklick-Menü)."""
        self._name_search_col = -1
        for i, h in enumerate(headers):
            if _canon(h) == 'name':
                self._name_search_col = i
                break

    def _open_help(self):
        from ui.widgets.multilang_help import show_help
        from ui.widgets.help_texts_manage_yarn import TEXTS
        show_help(TEXTS, self)

    def _on_search_changed(self, text: str):
        if not self.proxy:
            return
        self._collapse_all_usage_rows()
        col = self._name_search_col
        if col < 0:
            return
        self.proxy.set_search_filter([col], text)
        try:
            self._header.viewport().update()
            self.table.viewport().update()
        except Exception:
            pass

    def _on_columns_clicked(self):
        """Öffnet/hebt die Drag&Drop-Spaltenliste zum Umsortieren (wie Manage Jets)."""
        if not self.model:
            return
        if self._column_order_dialog is None or not self._column_order_dialog.isVisible():
            self._column_order_dialog = ColumnOrderDialog(
                self._header, self.model, 0, on_save=self._save_column_order_now, parent=self)
            self._column_order_dialog.show()
        else:
            self._column_order_dialog.raise_()
            self._column_order_dialog.activateWindow()

    def _save_column_order_now(self):
        """Persistiert die AKTUELLE Spaltenreihenfolge für den eingeloggten User.

        Nur explizit aufgerufen (Save-Button im Columns-Dialog) - Umsortieren
        allein speichert nicht automatisch, siehe Manage Jets für dieselbe
        Konvention/Begründung (User-Feedback: kann auch nur einmalig gemeint sein)."""
        if not self.model:
            return
        headers = self.model.headers()
        order = []
        for v in range(self._header.count()):
            logical = self._header.logicalIndex(v)
            if logical < len(headers) and not self._header.isSectionHidden(logical):
                order.append(headers[logical])
        from db.user_column_order import save_column_order
        save_column_order(self._SCREEN_KEY, order)

    def _restore_column_order(self):
        """Wendet die zuletzt für diesen User gespeicherte Spaltenreihenfolge an (falls vorhanden)."""
        if not self.model:
            return
        from db.user_column_order import load_column_order
        saved = load_column_order(self._SCREEN_KEY)
        if not saved:
            return
        name_to_logical = {h: i for i, h in enumerate(self.model.headers())}
        pos = 0
        for name in saved:
            logical = name_to_logical.get(name)
            if logical is None:
                continue
            current_visual = self._header.visualIndex(logical)
            if current_visual != pos:
                self._header.moveSection(current_visual, pos)
            pos += 1

    def _set_status(self, text: str, *, error: bool = False):
        self.status_label.setStyleSheet('color: #c62828;' if error else '')
        self.status_label.setText(text)

    def _go_home(self):
        if callable(self.on_back_home):
            self.on_back_home()
