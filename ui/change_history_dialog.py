"""change_history_dialog.py - "Change history…" for a value in Show
Experiment (right-click on a cell), plus the whole series at a click.
Data: db/change_log.py."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QHeaderView, QLabel, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
)

from db import change_log


def can_view_history() -> bool:
    """Only superusers (AccessLevel >= 4) may look at the change history."""
    try:
        import app_meta
        return int(app_meta.access_level() or 0) >= 4
    except Exception:
        return False


def _fmt_time(v: Any) -> str:
    try:
        return v.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(v or "")


class ChangeHistoryDialog(QDialog):
    """cell: (table, ids, field) of the clicked cell; display(field_key, raw)
    turns stored values into what the table shows (e.g. jet ID -> name);
    field_titles: {(table lower, field lower): row title} for the series view."""

    def __init__(self, parent, title: str, cell: Optional[Tuple[str, List[int], str]],
                 series_id: Any, display: Callable[[Tuple[str, str], Any], str],
                 field_titles: Dict[Tuple[str, str], str]):
        super().__init__(parent)
        self.setWindowTitle("Change history")
        self.resize(820, 520)
        self._cell, self._series_id = cell, series_id
        self._display, self._titles = display, field_titles
        lay = QVBoxLayout(self)
        import html as _html
        self.lbl = QLabel(f"<b>{_html.escape(title)}</b>")
        self.lbl.setTextFormat(Qt.RichText)
        lay.addWidget(self.lbl)
        self.cb_series = QCheckBox("Show all changes in this trial series")
        self.cb_series.toggled.connect(self._reload)
        self.cb_series.setEnabled(series_id not in (None, ""))
        lay.addWidget(self.cb_series)
        self.tbl = QTableWidget(0, 0)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        lay.addWidget(self.tbl, 1)
        self.lbl_info = QLabel("")
        self.lbl_info.setStyleSheet("color:#666;")
        self.lbl_info.setWordWrap(True)
        lay.addWidget(self.lbl_info)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        if cell is None:
            self.cb_series.setChecked(True)
        self._reload()

    def _reload(self) -> None:
        if not change_log.table_ready():
            self._fill(["Info"], [["The change history is not set up in this database yet."]])
            return
        if self.cb_series.isChecked():
            rows = change_log.history_for_series(self._series_id)
            data = []
            for r in rows:
                key = (str(r.get("TableName") or "").lower(), str(r.get("FieldName") or "").lower())
                vno = r.get("Versuchsnummer")
                trial = f"V{vno}" if vno not in (None, "") else ""
                data.append([_fmt_time(r.get("ChangedAt")), r.get("UserName") or "", trial,
                             self._titles.get(key, r.get("FieldName") or ""),
                             self._display(key, r.get("OldValue")), self._display(key, r.get("NewValue"))])
            self._fill(["When", "Who", "Trial", "Parameter", "Old value", "New value"], data)
        else:
            table, ids, field = self._cell
            key = (table.lower(), field.lower())
            rows = change_log.history_for_cell(table, ids, field)
            data = [[_fmt_time(r.get("ChangedAt")), r.get("UserName") or "",
                     self._display(key, r.get("OldValue")), self._display(key, r.get("NewValue"))]
                    for r in rows]
            self._fill(["When", "Who", "Old value", "New value"], data)
        n = self.tbl.rowCount()
        self.lbl_info.setText(
            "No changes recorded yet. Changes are recorded since the change history was introduced "
            "(October 2026); older edits are not known." if n == 0 else
            f"{n} change{'s' if n != 1 else ''}, newest first. Empty = no value.")

    def _fill(self, headers: List[str], data: List[List[Any]]) -> None:
        self.tbl.clear()
        self.tbl.setColumnCount(len(headers))
        self.tbl.setHorizontalHeaderLabels(headers)
        self.tbl.setRowCount(len(data))
        for i, row in enumerate(data):
            for j, v in enumerate(row):
                it = QTableWidgetItem("" if v is None else str(v))
                self.tbl.setItem(i, j, it)
        hh = self.tbl.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        hh.setStretchLastSection(True)


def _model_display(model) -> Callable[[Tuple[str, str], Any], str]:
    """Stored value -> shown text, using the dropdown maps of the Machine
    Data models (housing, jet, disc, ...)."""
    maps: Dict[Tuple[str, str], Dict[Any, str]] = {}
    try:
        from ui.screen_show_experiment import MachinePivotModel
        if isinstance(model, MachinePivotModel):
            row_maps = {model._housing_row_index: model._housing_map, model._jet_row_index: model._jets_map}
            row_maps.update(getattr(model, "_dropdown_rows", {}) or {})
            for dr, mp in row_maps.items():
                for b in (model._binding[dr] if 0 <= dr < len(model._binding) else []):
                    if b is not None:
                        maps[(str(b.table).lower(), str(b.field).lower())] = mp
                        break
    except Exception:
        pass

    def display(key, raw):
        if raw in (None, ""):
            return ""
        mp = maps.get(key)
        if mp:
            for k in (raw, str(raw)):
                if k in mp:
                    return str(mp[k])
            try:
                return str(mp.get(int(float(raw)), raw))
            except (TypeError, ValueError):
                return str(raw)
        return str(raw)
    return display


def field_titles_of(models) -> Dict[Tuple[str, str], str]:
    titles: Dict[Tuple[str, str], str] = {}
    for m in models:
        for dr, row in enumerate(getattr(m, "_binding", []) or []):
            for b in row:
                if b is not None:
                    titles.setdefault((str(b.table).lower(), str(b.field).lower()), m._row_titles[dr])
                    break
    return titles


def show_cell_history(screen, model, index) -> None:
    """Right-click "Change history…" on a value of a Show Experiment table."""
    if not can_view_history():
        return
    from ui.screen_show_experiment import GroupCellBinding
    n_hdr = getattr(model, "_n_hdr", 0)
    dr, c = index.row() - n_hdr, index.column() - 1
    b = model.get_binding(dr, c)
    if b is None:
        cell, where = None, ""
    else:
        ids = list(b.id_values) if isinstance(b, GroupCellBinding) else [b.id_value]
        cell = (str(b.table), ids, str(b.field))
        hdr = [str(model.data(model.index(h, index.column()), Qt.DisplayRole) or "").strip() for h in range(n_hdr)]
        where = " · ".join([h for i, h in enumerate(hdr) if h and h not in hdr[:i]] + [model._row_titles[dr]])
    models = [getattr(screen, n, None) for n in getattr(screen, "_save_model_names", [])]
    models = [m for m in models if m is not None]
    disp_fns = [_model_display(m) for m in models] or [_model_display(model)]

    def display(key, raw):
        for fn in [_model_display(model)] + disp_fns:
            out = fn(key, raw)
            if out != str(raw):
                return out
        return "" if raw in (None, "") else str(raw)

    dlg = ChangeHistoryDialog(screen, where or "Trial series", cell, getattr(screen, "_series_pk", None),
                              display, field_titles_of(models or [model]))
    dlg.exec()
