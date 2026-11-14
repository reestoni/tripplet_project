"""user_settings_dialog.py - "Settings" in the sidebar's Account group
(replaces the former "Accent Colour" button), Nutzerwunsch 2026-10-15.

One place for the personal settings:
- Profile picture (optional, db/user_avatar.py - file on the share, same picture as the web app)
- Welcome message (tblUser.WelcomeMessage, shown on the Backlog screen)
- Accent colour (tblUser.AccentColour)
- Display of the Show Experiment tables (ui/display_prefs.py): text size,
  high contrast, crosshair, reading bar, warning symbols, colour-blind
  friendly colours - for colleagues with poor eyesight
- App size (whole program, applies after a restart)

Changes are shown immediately (live preview here and in open Show
Experiment tables); Cancel restores the previous state, Save stores it.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QColorDialog, QDialog, QDialogButtonBox,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

import app_meta
from ui import display_prefs
from ui.widgets.friendly_error import show_error

from db.user_account import WELCOME_MAX_LEN  # noqa: E402  (rules shared with the web app)
# chosen size clearly visible (the app stylesheet barely marks :checked)
_CHOICE_QSS = ("QPushButton:checked{background:#1F4E8C;color:#FFFFFF;font-weight:bold;"
               "border:2px solid #1F4E8C;}")


def _load_welcome_message() -> str:
    from db.user_account import load_welcome_message
    return load_welcome_message((app_meta.current_user or {}).get("id"))


def _save_welcome_message(text: str) -> None:
    from db.user_account import save_welcome_message
    save_welcome_message((app_meta.current_user or {}).get("id"), text)


def _refresh_welcome_labels() -> None:
    for w in QApplication.allWidgets():
        fn = getattr(w, "_refresh_welcome_message", None)
        if callable(fn):
            try:
                fn()
            except Exception:
                pass


def apply_accent(hex_val: str) -> None:
    from ui.theme import build_qss, set_accent
    set_accent(hex_val)
    QApplication.instance().setStyleSheet(build_qss())


def save_accent(hex_val: str) -> None:
    from db.user_account import save_accent as _save
    _save((app_meta.current_user or {}).get("username"), hex_val)
    app_meta.current_user["accent_colour"] = hex_val


def _preview_table(parent: QWidget):
    """Small sample of a Machine Data table that follows the settings."""
    from ui.screen_show_experiment import PivotEditModel
    from ui.widgets.frozen_first_column_table import FrozenFirstColumnTable
    hdr = [{"values": ["", "V1", "V2", "V3"], "bg": None, "fg": None}]
    model = PivotEditModel(["Air Pressure (bar)", "Speed Shaft 2 (m/min)", "T1 Tension (cN)"],
                           ["V1", "V2", "V3"], global_readonly=True, header_rows=hdr)
    for r, vals in enumerate([("6", "6", "5.5"), ("550", "600", "650"), ("22.1", "21.4", "23")]):
        for c, v in enumerate(vals):
            model.set_cell(r, c, v, None)
    # two highlighted values, so the warning colours/symbols can be judged
    model._cell_alerts[(2, 2)] = "red"
    model._cell_alerts[(1, 0)] = "orange"
    tbl = FrozenFirstColumnTable(parent)
    tbl.setModel(model)
    tbl.verticalHeader().setVisible(False)
    tbl.left.verticalHeader().setVisible(False)
    tbl.resizeColumnsToContents(fixed_data_column_width=70)
    tbl._preview_model = model
    tbl.setMinimumHeight(190)
    return tbl


class UserSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(560)
        from ui.theme import get_accent
        self._orig_prefs = display_prefs.current()
        self._orig_accent = get_accent()
        self._accent = self._orig_accent
        self._orig_welcome = _load_welcome_message()

        lay = QVBoxLayout(self)

        # ── Profile picture (optional; stored on Save) ───────────────────
        self._avatar_new = None        # normalised PNG bytes chosen in this dialog
        self._avatar_remove = False
        g_pic = QGroupBox("Profile picture")
        pl = QHBoxLayout(g_pic)
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(64, 64)
        self.lbl_avatar.setAlignment(Qt.AlignCenter)
        pl.addWidget(self.lbl_avatar)
        btn_pic = QPushButton("Choose picture…")
        btn_pic.clicked.connect(self._choose_avatar)
        pl.addWidget(btn_pic)
        self.btn_pic_remove = QPushButton("Remove")
        self.btn_pic_remove.clicked.connect(self._remove_avatar)
        pl.addWidget(self.btn_pic_remove)
        pic_hint = QLabel("Optional. Shown next to your name\n(also in the web version).")
        pic_hint.setStyleSheet("color:#666;")
        pl.addWidget(pic_hint)
        pl.addStretch(1)
        lay.addWidget(g_pic)
        self._show_avatar()

        # ── Welcome message ──────────────────────────────────────────────
        g_welcome = QGroupBox("Welcome message")
        gl = QVBoxLayout(g_welcome)
        self.ed_welcome = QLineEdit(self._orig_welcome)
        self.ed_welcome.setMaxLength(WELCOME_MAX_LEN)
        first = (app_meta.current_user or {}).get("first_name") or ""
        self.ed_welcome.setPlaceholderText(f"Welcome, {first}".strip())
        gl.addWidget(self.ed_welcome)
        hint = QLabel(f"Shown on the Backlog screen. Max. {WELCOME_MAX_LEN} characters, empty = default.")
        hint.setStyleSheet("color:#666;")
        gl.addWidget(hint)
        lay.addWidget(g_welcome)

        # ── Start screen (after the login) ───────────────────────────────
        from PySide6.QtWidgets import QComboBox
        from db import feature_access as fa
        g_start = QGroupBox("Start screen")
        stl = QHBoxLayout(g_start)
        stl.addWidget(QLabel("After the login open:"))
        self.cmb_start = QComboBox()
        for key in fa.START_SCREENS:
            if fa.can_use(key):
                self.cmb_start.addItem(fa.BY_KEY[key].label, key)
        cur = self._orig_prefs.get("start") or "backlog"
        idx = self.cmb_start.findData(cur)
        self.cmb_start.setCurrentIndex(idx if idx >= 0 else max(0, self.cmb_start.findData("backlog")))
        stl.addWidget(self.cmb_start, 1)
        lay.addWidget(g_start)

        # ── Accent colour ────────────────────────────────────────────────
        g_accent = QGroupBox("Accent colour")
        al = QHBoxLayout(g_accent)
        self.lbl_swatch = QLabel()
        self.lbl_swatch.setFixedSize(48, 24)
        al.addWidget(self.lbl_swatch)
        self.btn_accent = QPushButton("Change…")
        self.btn_accent.clicked.connect(self._pick_accent)
        al.addWidget(self.btn_accent)
        self.btn_accent_reset = QPushButton("Default green")
        self.btn_accent_reset.clicked.connect(lambda: self._set_accent("#39a650"))
        al.addWidget(self.btn_accent_reset)
        al.addStretch(1)
        lay.addWidget(g_accent)
        self._update_swatch()

        # ── Text size (whole program, Qt scale factor -> after a restart) ──
        g_size = QGroupBox("Text size (whole program)")
        sl = QVBoxLayout(g_size)
        row = QHBoxLayout()
        self._app_group = QButtonGroup(self)
        self._app_buttons = {}
        for pct, name in zip(display_prefs.APP_SCALE_CHOICES, ("Normal", "Large", "Extra large", "Huge")):
            b = QPushButton(f"{name}\n{pct} %")
            b.setCheckable(True)
            b.setStyleSheet(_CHOICE_QSS)
            b.setMinimumHeight(44)
            self._app_group.addButton(b, pct)
            self._app_buttons[pct] = b
            row.addWidget(b)
        row.addStretch(1)
        self._app_group.idClicked.connect(lambda pct: display_prefs.update(persist=False, app_scale=pct))
        sl.addLayout(row)
        self.lbl_app_hint = QLabel("")
        self.lbl_app_hint.setStyleSheet("color:#666;")
        self.lbl_app_hint.setWordWrap(True)
        sl.addWidget(self.lbl_app_hint)
        lay.addWidget(g_size)

        # ── Show Experiment tables ───────────────────────────────────────
        g_disp = QGroupBox("Show Experiment tables (easier reading)")
        dl = QVBoxLayout(g_disp)
        self.cb_contrast = QCheckBox("High contrast (black text, strong stripes and grid lines)")
        self.cb_contrast.toggled.connect(lambda on: display_prefs.update(persist=False, contrast=on))
        dl.addWidget(self.cb_contrast)
        self.cb_cross = QCheckBox("Crosshair: highlight row and column of the selected cell")
        self.cb_cross.toggled.connect(lambda on: display_prefs.update(persist=False, crosshair=on))
        dl.addWidget(self.cb_cross)
        self.cb_readbar = QCheckBox("Reading bar: show the selected value in large words below the table "
                                    "(e.g. \"V2 · Ply 1 · Air Pressure (bar) = 3.50\")")
        self.cb_readbar.toggled.connect(lambda on: display_prefs.update(persist=False, readbar=on))
        dl.addWidget(self.cb_readbar)
        self.cb_marks = QCheckBox("Mark warnings with a symbol, not only with colour "
                                  "(circle = out of tolerance, triangle = check)")
        self.cb_marks.toggled.connect(lambda on: display_prefs.update(persist=False, alert_marks=on))
        dl.addWidget(self.cb_marks)
        self.cb_cb = QCheckBox("Colour-blind friendly colours (no red/green; warnings orange/yellow "
                               "with symbols, blue crosshair)")
        self.cb_cb.toggled.connect(lambda on: display_prefs.update(persist=False, cb_colours=on))
        dl.addWidget(self.cb_cb)
        for cb in (self.cb_readbar, self.cb_marks, self.cb_cb):
            cb.setStyleSheet("QCheckBox{spacing:8px;}")
        tip = QLabel("Tip: in a table, Ctrl + mouse wheel (or Ctrl +/-) zooms the table right away, "
                     "Ctrl+0 resets it.")
        tip.setStyleSheet("color:#666;")
        tip.setWordWrap(True)
        dl.addWidget(tip)
        self.lbl_custom = QLabel("")
        self.lbl_custom.setStyleSheet("color:#666;")
        dl.addWidget(self.lbl_custom)
        dl.addWidget(QLabel("Preview - shows the chosen text size right away (click a value):"))
        self.preview = _preview_table(self)
        dl.addWidget(self.preview, 1)
        lay.addWidget(g_disp, 1)

        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

        display_prefs.add_listener(self._sync_controls)
        self._sync_controls()
        self.resize(700, 820)

    # ── controls ─────────────────────────────────────────────────────────
    def _sync_controls(self) -> None:
        p = display_prefs.current()
        self.lbl_custom.setText(f"Table zoom (Ctrl + mouse wheel): {p['scale']} %" if p["scale"] != 100 else "")
        ab = self._app_buttons.get(p["app_scale"])
        if ab is not None:
            ab.setChecked(True)
        # the preview shows the chosen text size right away (the program
        # itself only after the restart)
        factor = p["app_scale"] / float(display_prefs.running_app_scale() or 100)
        if abs(self.preview.preview_factor - factor) > 1e-6:
            self.preview.preview_factor = factor
            self.preview._apply_display()
        if display_prefs.app_scale_needs_restart():
            self.lbl_app_hint.setText(f"Applies after TrippleT restarts (now running at "
                                      f"{display_prefs.running_app_scale()} %). Buttons, menus, tables and "
                                      "dialogs all grow. Windows display scaling comes on top.")
        else:
            self.lbl_app_hint.setText("Buttons, menus, tables and dialogs all grow. Takes effect after a "
                                      "restart of TrippleT (offered when you save).")
        for cb, key in ((self.cb_contrast, "contrast"), (self.cb_cross, "crosshair"),
                        (self.cb_readbar, "readbar"), (self.cb_marks, "alert_marks"),
                        (self.cb_cb, "cb_colours")):
            if cb.isChecked() != p[key]:
                cb.blockSignals(True)
                cb.setChecked(p[key])
                cb.blockSignals(False)

    def _update_swatch(self) -> None:
        self.lbl_swatch.setStyleSheet(f"background:{self._accent}; border:1px solid #888; border-radius:4px;")

    def _pick_accent(self) -> None:
        colour = QColorDialog.getColor(QColor(self._accent), self, "Choose accent colour")
        if colour.isValid():
            self._set_accent(colour.name())

    def _set_accent(self, hex_val: str) -> None:
        self._accent = hex_val
        self._update_swatch()
        apply_accent(hex_val)

    # ── profile picture ──────────────────────────────────────────────────
    def _uid(self):
        return (app_meta.current_user or {}).get("id")

    def _show_avatar(self) -> None:
        from db import user_avatar
        from ui.widgets.avatar import round_pixmap, round_pixmap_from_bytes
        if self._avatar_new:
            pm = round_pixmap_from_bytes(self._avatar_new, 64)
        elif self._avatar_remove:
            pm = None
        else:
            pm = round_pixmap(self._uid(), 64)
        if pm is not None:
            self.lbl_avatar.setPixmap(pm)
            self.lbl_avatar.setStyleSheet("")
        else:
            fn = (app_meta.current_user or {}).get("first_name") or ""
            ln = (app_meta.current_user or {}).get("last_name") or ""
            self.lbl_avatar.clear()
            self.lbl_avatar.setText(((fn[:1] + ln[:1]) or "?").upper())
            from ui.theme import get_accent
            self.lbl_avatar.setStyleSheet(f"background:{self._accent if hasattr(self, '_accent') else get_accent()};"
                                          "color:white;font-weight:bold;font-size:18px;border-radius:32px;")
        has = bool(self._avatar_new) or (not self._avatar_remove and user_avatar.has_avatar(self._uid()))
        self.btn_pic_remove.setEnabled(has)

    def _choose_avatar(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        from db import user_avatar
        exts = " ".join("*" + e for e in user_avatar.EXTENSIONS)
        path, _ = QFileDialog.getOpenFileName(self, "Profile picture", "", f"Pictures ({exts})")
        if not path:
            return
        try:
            with open(path, "rb") as fh:
                self._avatar_new = user_avatar.normalise(fh.read())
            self._avatar_remove = False
        except (user_avatar.AvatarError, OSError) as e:
            show_error(self, "Profile picture", str(e), None, warning=True)
            return
        self._show_avatar()

    def _remove_avatar(self) -> None:
        self._avatar_new = None
        self._avatar_remove = True
        self._show_avatar()

    def _save_avatar(self) -> None:
        from db import user_avatar
        uid = self._uid()
        if uid is None:
            return
        if self._avatar_new:
            user_avatar.save(uid, self._avatar_new)
        elif self._avatar_remove:
            user_avatar.delete(uid)
        else:
            return
        # repaint the footers of the open screens
        from ui.widgets.footer import FooterBar
        for w in QApplication.allWidgets():
            if isinstance(w, FooterBar):
                try:
                    w.refresh()
                except Exception:
                    pass

    # ── save / cancel ────────────────────────────────────────────────────
    def _save(self) -> None:
        from PySide6.QtWidgets import QMessageBox
        try:
            self._save_avatar()
        except Exception as e:
            show_error(self, "Settings", "The profile picture could not be saved.", e, warning=True)
        try:
            if self.ed_welcome.text().strip() != self._orig_welcome.strip():
                _save_welcome_message(self.ed_welcome.text())
                _refresh_welcome_labels()
            if self._accent != self._orig_accent:
                save_accent(self._accent)
        except Exception as e:
            show_error(self, "Settings", "Not all settings could be saved.", e, warning=True)
        if self.cmb_start.currentData():
            display_prefs.update(persist=False, quiet=True, start=self.cmb_start.currentData())
        display_prefs.save_now()
        try:
            from db.usage_log import log_usage_event
            p = display_prefs.current()
            log_usage_event("feature", "user_settings",
                            " ".join(f"{k}={int(v)}" for k, v in sorted(p.items()) if isinstance(v, (bool, int)))
                            + f" start={p.get('start')}")
        except Exception:
            pass
        self.accept()
        if display_prefs.app_scale_needs_restart() \
                and display_prefs.current()["app_scale"] != self._orig_prefs.get("app_scale"):
            display_prefs.offer_restart(self.parent())

    def reject(self) -> None:
        # persist: Ctrl+mouse wheel in the preview may already have saved
        if display_prefs.current() != self._orig_prefs:
            display_prefs.update(persist=True, **self._orig_prefs)
        if self._accent != self._orig_accent:
            apply_accent(self._orig_accent)
        super().reject()


def open_user_settings(parent=None) -> None:
    UserSettingsDialog(parent).exec()
