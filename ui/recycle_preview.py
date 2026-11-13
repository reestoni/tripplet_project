"""recycle_preview.py - look into a deleted series before deciding,
Nutzerwunsch 2026-10-16.

Recycle Bin (ui/widgets/recycle_bin_dialog.py) -> double-click / "Open in
Show Experiment": the series is restored for the time being (db.recycle_bin.
restore, original IDs) and opens in a new Show Experiment tab, read only
(ShowExperimentScreen.set_recycle_preview -> _get_access_level() 1, models
read only). A banner on top offers:
    Restore for good      -> stays restored, preview ends
    Back to Recycle Bin   -> deleted again, with the ORIGINAL deletion date
                             and user (the 90 days don't start again), the
                             tab closes
    Delete permanently    -> deleted again and the bin entry removed
Closing the tab or the program without a decision = Back to Recycle Bin.
If the program crashes, the series simply stays restored - nothing is lost,
it can be deleted again.

While the tab is open, the series is visible to everybody (Backlog, All
Experiments) - accepted, it is usually only a few minutes.
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, Optional, Set

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton, QWidget

from db import recycle_bin
from ui.widgets.friendly_error import show_error

AMBER_BG, AMBER_BORDER, AMBER_TEXT = "#FFF4D6", "#E8C15A", "#5a4500"

_ACTIVE: Set["RecyclePreview"] = set()


def _log(name: str, detail: str) -> None:
    try:
        from db.usage_log import log_usage_event
        log_usage_event("feature", name, detail)
    except Exception:
        pass


def _when_text(v: Any) -> str:
    return v.strftime("%d.%m.%Y %H:%M") if hasattr(v, "strftime") else str(v or "")


class RecyclePreview:
    """One series taken out of the recycle bin for a look."""

    def __init__(self, entry: Dict[str, Any]):
        self.entry = dict(entry)          # row of recycle_bin.list_entries() (with UserName)
        self.bin_id = int(entry["ID"])
        self.info: Optional[Dict[str, Any]] = None
        self.screen = None
        self.active = False

    # ── start ──────────────────────────────────────────────────────────
    def start(self, parent: Optional[QWidget] = None) -> bool:
        """Restores the series and opens it. False if cancelled or failed."""
        import app_meta
        opener = getattr(app_meta, "open_show_experiment_preview", None)
        if not callable(opener):
            QMessageBox.information(parent, "Recycle Bin", "Show Experiment is not available here.")
            return False
        label = self.entry.get("Label") or self.entry.get("ObjectID")
        if QMessageBox.question(
                parent, "Open in Show Experiment",
                f"To show \"{label}\", it is taken out of the recycle bin for the time being "
                "and opens read only in a new tab.\n\n"
                "There you decide: restore it for good, put it back or delete it permanently. "
                "Closing the tab puts it back into the recycle bin.",
                QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok) != QMessageBox.Ok:
            return False
        try:
            self.info = recycle_bin.preview_start(self.bin_id)    # db/recycle_bin.py (shared with the web)
        except Exception as e:
            show_error(parent, "Open in Show Experiment", "The series could not be opened.", e, warning=True)
            return False
        self.active = True
        _ACTIVE.add(self)
        _log("recycle_bin_preview", str(self.info.get("ObjectID")))

        exp_pk = self.info.get("ExperimentPK")
        series_pk = int(self.info["ObjectID"])
        experiment_id = ""
        try:
            from db.connection import fetch_all
            rows = fetch_all("SELECT [Experiment ID] AS EID FROM tblExperimente WHERE ID = ?", [exp_pk])
            experiment_id = str(rows[0]["EID"]) if rows else ""
        except Exception:
            pass
        try:
            opener(int(exp_pk or 0), series_pk, experiment_id, self._attach)
        except Exception as e:
            self.back_to_bin(silent=True)
            show_error(parent, "Open in Show Experiment", "The series could not be opened - it is back in the recycle bin.", e, warning=True)
            return False
        self._refresh_lists()
        return True

    def _attach(self, screen) -> None:
        """Called by MainWindow with the fresh Show Experiment screen, before loading."""
        self.screen = screen
        screen.set_recycle_preview(self, self._banner())

    def _banner(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("RecyclePreviewBar")
        bar.setStyleSheet(
            f"QFrame#RecyclePreviewBar{{background:{AMBER_BG}; border:1px solid {AMBER_BORDER};"
            f"border-radius:4px;}} QFrame#RecyclePreviewBar QLabel{{color:{AMBER_TEXT}; border:none;}}")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 6, 8, 6)
        who = self.entry.get("UserName") or "unknown"
        when = _when_text((self.info or {}).get("DeletedAt") or self.entry.get("DeletedAt"))
        txt = QLabel(f"<b>From the Recycle Bin - read only.</b> Deleted {when} by {who}. "
                     "Closing this tab puts it back into the recycle bin.")
        txt.setWordWrap(True)
        lay.addWidget(txt, 1)
        for text, slot, tip in (
                ("Restore for good", self.keep, "The series stays and can be edited again"),
                ("Back to Recycle Bin", lambda: self.back_to_bin(), "Deleted again - same deletion date as before"),
                ("Delete permanently", self.delete_permanently, "Cannot be undone")):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            lay.addWidget(b)
        return bar

    # ── decisions ──────────────────────────────────────────────────────
    def _end(self) -> None:
        self.active = False
        _ACTIVE.discard(self)
        if self.screen is not None:
            try:
                self.screen.set_recycle_preview(None, None)
            except RuntimeError:
                pass  # screen already deleted

    def keep(self) -> None:
        if not self.active:
            return
        self._end()
        _log("recycle_bin_preview_keep", str((self.info or {}).get("ObjectID")))
        if self.screen is not None:
            QMessageBox.information(self.screen, "Restore for good", "The series is restored and can be edited again.")

    def back_to_bin(self, silent: bool = False, close_tab: bool = True) -> Optional[int]:
        """Deletes the series again with the original date/user. Returns
        the new recycle bin ID (None on error)."""
        if not self.active:
            return None
        info = self.info or {}
        try:
            new_id = recycle_bin.preview_back(info, self.bin_id)   # same date / user as before
        except Exception as e:
            if not silent or self.screen is not None:
                try:
                    show_error(self.screen, "Back to Recycle Bin", "The series could not be put back into the recycle bin - it stays restored.", e, warning=True)
                except Exception:
                    pass
            self._end()
            return None
        self._end()
        self._refresh_lists()
        if close_tab:
            self._close_tab()
        return new_id

    def delete_permanently(self) -> None:
        if not self.active:
            return
        label = (self.info or {}).get("Label") or (self.info or {}).get("ObjectID")
        if QMessageBox.warning(self.screen, "Delete permanently",
                               f"Delete \"{label}\" permanently?\nIt cannot be restored afterwards.",
                               QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel) != QMessageBox.Yes:
            return
        new_id = self.back_to_bin(close_tab=False)
        if new_id:
            try:
                recycle_bin.delete_permanently(new_id)
            except Exception as e:
                show_error(self.screen, "Delete permanently", "The series is back in the recycle bin, but could not be removed from there.", e, warning=True)
        self._close_tab()

    def tab_closed(self) -> None:
        """Tab closed without a decision -> back into the recycle bin."""
        self.back_to_bin(silent=True, close_tab=False)

    # ── helpers ────────────────────────────────────────────────────────
    def _close_tab(self) -> None:
        from ui.widgets.tab_container import TabbedNavigator
        w = self.screen
        try:
            stack = w.parentWidget() if w is not None else None
            nav = stack
            while nav is not None and not isinstance(nav, TabbedNavigator):
                nav = nav.parentWidget()
            if nav is not None:
                idx = nav.indexOf(stack)
                if idx >= 0:
                    nav._on_tab_close_requested(idx)
        except RuntimeError:
            pass

    @staticmethod
    def _refresh_lists() -> None:
        try:
            from ui.widgets.recycle_bin_dialog import refresh_series_lists
            refresh_series_lists()
        except Exception:
            pass


def finish_all() -> None:
    """Program closes: every open preview goes back into the recycle bin."""
    for p in list(_ACTIVE):
        p.back_to_bin(silent=True, close_tab=False)
