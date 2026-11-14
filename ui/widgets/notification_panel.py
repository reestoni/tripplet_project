from __future__ import annotations
# ui/widgets/notification_panel.py
"""Modernes Notification-Panel als schwebendes Popup."""

from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal

# ---------------------------------------------------------------------------
# Farben / Konstanten
# ---------------------------------------------------------------------------
_C_BG        = "#ffffff"
_C_HDR_BG    = "#1e293b"
_C_HDR_TXT   = "#f8fafc"
_C_UNREAD_BG = "#eff6ff"
_C_READ_BG   = "#ffffff"
_C_BORDER    = "#e2e8f0"
_C_DOT       = "#3b82f6"
_C_TITLE     = "#1e293b"
_C_SUB       = "#64748b"
_C_TIME      = "#94a3b8"
_C_HOVER_UN  = "#dbeafe"
_C_HOVER_RD  = "#f1f5f9"
_C_BADGE_UN  = "#3b82f6"
_C_BADGE_RD  = "#94a3b8"
_C_SEP       = "#e2e8f0"
_PANEL_W     = 460
_ITEM_H      = 84   # geschaetzte Itemhoehe fuer Scroll-Berechnung
_MAX_SCROLL_H = 560


def _fmt_time(created) -> str:
    if not created:
        return ""
    try:
        dt = datetime.fromisoformat(str(created)[:19].replace("T", " ")) \
            if isinstance(created, str) else created
        s = int((datetime.now() - dt).total_seconds())
        if s < 60:   return "Just now"
        if s < 3600: return f"{s // 60} min ago"
        if s < 86400: return f"{s // 3600} h ago"
        if s < 7 * 86400: return f"{s // 86400} day(s) ago"
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(created)[:16]


# ---------------------------------------------------------------------------
# Einzelnes Notification-Item
# ---------------------------------------------------------------------------
class _NotifItem(QFrame):
    clicked   = Signal(int, str)   # series_id, exp_id_txt
    yarn_clicked = Signal(int, str)  # payload_yarn_id, payload_charge
    request_clicked = Signal(int)  # payload_experiment_request_id
    request_changed_clicked = Signal(int, int)  # payload_experiment_request_id, payload_archived_version_id
    read_toggled = Signal()

    _TYPE_ICON = {"yarn_stock": "🧵", "experiment_request": "📝", "experiment_request_changed": "🔄",
                  "series_conclusion": "✅"}
    _TYPE_TAG = {
        "yarn_stock": "YARN STOCK", "experiment_request": "EXPERIMENT REQUEST",
        "experiment_request_changed": "REQUEST CHANGED", "series_conclusion": "CONCLUSION",
    }

    def __init__(self, n: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self._series_id = int(n.get("TrialSeriesID") or 0)
        self._exp_id    = str(n.get("ExperimentIDTxt") or "")
        self._notif_id  = n.get("ID")
        self._is_unread = n.get("ReadAt") is None
        self._notif_type = str(n.get("NotificationType") or "series")
        self._payload_yarn_id = n.get("PayloadYarnID")
        self._payload_charge = n.get("PayloadCharge")
        self._payload_request_id = n.get("PayloadExperimentRequestID")
        self._payload_archived_version_id = n.get("PayloadArchivedVersionID")
        series_name     = str(n.get("SeriesName") or f"Series {self._series_id}")
        created         = n.get("CreatedAt")
        message         = str(n.get("Message") or "")
        # "Message"-basierte Typen (kein Series-Bezug) - zeigen den Message-
        # Text statt des Serien-Namens, siehe unten.
        _is_message_type = self._notif_type in ("yarn_stock", "experiment_request", "experiment_request_changed")

        self.setObjectName("NItem")
        self.setCursor(Qt.PointingHandCursor)
        self._apply_style()

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 13, 14, 13)
        root.setSpacing(11)

        # Ungelesen-Punkt
        dot = QLabel()
        dot.setFixedSize(9, 9)
        dot.setStyleSheet(
            f"background:{'#3b82f6' if self._is_unread else 'transparent'};"
            "border-radius:4px;"
        )
        root.addWidget(dot, 0, Qt.AlignTop | Qt.AlignHCenter)

        # Icon (je nach Notification-Typ)
        ico = QLabel(self._TYPE_ICON.get(self._notif_type, "📦"))
        ico.setStyleSheet("font-size:20px; background:transparent;")
        ico.setFixedWidth(28)
        root.addWidget(ico, 0, Qt.AlignTop)

        # Text
        col = QVBoxLayout()
        col.setSpacing(3)
        col.setContentsMargins(0, 0, 0, 0)

        tag = QLabel(self._TYPE_TAG.get(self._notif_type, "SERIES DONE"))
        tag.setStyleSheet(
            f"font-size:9px; font-weight:800; letter-spacing:0.8px;"
            f"color:{'#3b82f6' if self._is_unread else '#94a3b8'};"
            "background:transparent;"
        )
        col.addWidget(tag)

        name = QLabel(message if _is_message_type else series_name)
        name.setWordWrap(True)
        name.setStyleSheet(
            f"font-size:13px; font-weight:{'700' if self._is_unread else '400'};"
            f"color:{_C_TITLE}; background:transparent;"
        )
        col.addWidget(name)

        if self._exp_id and not _is_message_type:
            exp = QLabel(f"Experiment: {self._exp_id}")
            exp.setStyleSheet(f"font-size:11px; color:{_C_SUB}; background:transparent;")
            col.addWidget(exp)

        ts = QLabel(_fmt_time(created))
        ts.setStyleSheet(f"font-size:10px; color:{_C_TIME}; background:transparent;")
        col.addWidget(ts)

        root.addLayout(col, 1)

        # Als-gelesen-Button (nur ungelesen)
        if self._is_unread:
            self._btn_rd = QPushButton("✓")
            self._btn_rd.setToolTip("Als gelesen markieren")
            self._btn_rd.setCursor(Qt.PointingHandCursor)
            self._btn_rd.setFixedSize(28, 28)
            self._btn_rd.setStyleSheet(
                "QPushButton{"
                f"background:transparent;border:1.5px solid {_C_DOT};"
                "border-radius:14px;"
                f"color:{_C_DOT};font-size:14px;font-weight:700;}}"
                f"QPushButton:hover{{background:{_C_DOT};color:white;}}"
            )
            self._btn_rd.clicked.connect(self._mark_read)
            root.addWidget(self._btn_rd, 0, Qt.AlignVCenter)

    def _apply_style(self):
        bg    = _C_UNREAD_BG if self._is_unread else _C_READ_BG
        hover = _C_HOVER_UN  if self._is_unread else _C_HOVER_RD
        self.setStyleSheet(
            f"QFrame#NItem{{background:{bg};border:none;"
            f"border-bottom:1px solid {_C_SEP};}}"
            f"QFrame#NItem:hover{{background:{hover};}}"
        )

    def _mark_read(self):
        if self._notif_id:
            try:
                from ui.notifications import mark_as_read
                mark_as_read(self._notif_id)
            except Exception:
                pass
        self._is_unread = False
        self._apply_style()
        if hasattr(self, "_btn_rd"):
            self._btn_rd.setVisible(False)
        self.read_toggled.emit()
        try:
            import app_meta
            app_meta.refresh_bell()
        except Exception:
            pass

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._notif_type == "yarn_stock":
                self._mark_read()
                if self._payload_yarn_id is not None:
                    self.yarn_clicked.emit(int(self._payload_yarn_id), self._payload_charge or "")
            elif self._notif_type == "experiment_request":
                self._mark_read()
                self.request_clicked.emit(
                    int(self._payload_request_id) if self._payload_request_id is not None else 0
                )
            elif self._notif_type == "experiment_request_changed":
                self._mark_read()
                self.request_changed_clicked.emit(
                    int(self._payload_request_id) if self._payload_request_id is not None else 0,
                    int(self._payload_archived_version_id) if self._payload_archived_version_id is not None else 0,
                )
            else:
                self.clicked.emit(self._series_id, self._exp_id)


# ---------------------------------------------------------------------------
# Haupt-Panel
# ---------------------------------------------------------------------------
class NotificationPanel(QWidget):
    """Modernes schwebendes Notification-Panel.

    Signals:
        notification_clicked(exp_pk, series_pk, experiment_id)
        all_read()
    """
    notification_clicked = Signal(int, int, str)
    yarn_stock_clicked = Signal(int, str)  # payload_yarn_id, payload_charge
    experiment_request_clicked = Signal(int)  # payload_experiment_request_id
    experiment_request_changed_clicked = Signal(int, int)  # payload_experiment_request_id, payload_archived_version_id
    all_read = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        # KEIN WA_TranslucentBackground + kein QGraphicsDropShadowEffect:
        # Die Kombination verhindert das korrekte Neuzeichnen beim zweiten Oeffnen.
        # Schatten wird via Border + Margin im Layout simuliert.
        self.setFixedWidth(_PANEL_W)
        self._build_ui()

    # ── Aufbau (einmalig) ─────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._card = QFrame(objectName="NCard")
        self._card.setStyleSheet(
            f"QFrame#NCard{{background:{_C_BG};border-radius:12px;"
            f"border:1px solid {_C_BORDER};}}"
        )
        card_lay = QVBoxLayout(self._card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        # Header ────────────────────────────────────────────────────────────
        hdr = QWidget()
        hdr.setStyleSheet(
            f"background:{_C_HDR_BG}; border-radius:14px 14px 0 0;"
        )
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(18, 14, 14, 14)
        hl.setSpacing(10)

        bell = QLabel("🔔")
        bell.setStyleSheet("font-size:17px; background:transparent;")
        hl.addWidget(bell)

        ttl = QLabel("Notifications")
        ttl.setStyleSheet(
            f"color:{_C_HDR_TXT};font-size:15px;font-weight:700;background:transparent;"
        )
        hl.addWidget(ttl)
        hl.addStretch()

        self._badge = QLabel()
        self._badge.setStyleSheet(
            f"background:{_C_BADGE_UN};color:white;font-size:10px;"
            "font-weight:700;border-radius:10px;padding:2px 9px;"
        )
        self._badge.setVisible(False)
        hl.addWidget(self._badge, 0, Qt.AlignVCenter)

        self._btn_all = QPushButton("All read")
        self._btn_all.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,0.13);"
            "border:1px solid rgba(255,255,255,0.28);border-radius:7px;"
            f"color:{_C_HDR_TXT};font-size:11px;padding:5px 12px;}}"
            "QPushButton:hover{background:rgba(255,255,255,0.23);}"
        )
        self._btn_all.setCursor(Qt.PointingHandCursor)
        self._btn_all.clicked.connect(self._on_mark_all)
        hl.addWidget(self._btn_all)
        card_lay.addWidget(hdr)

        # Scroll ────────────────────────────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            "QScrollArea{border:none;background:transparent;}"
            "QScrollBar:vertical{width:6px;background:transparent;margin:4px 2px;}"
            "QScrollBar::handle:vertical{background:#cbd5e1;border-radius:3px;min-height:20px;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )
        # Platzhalter – wird bei load_notifications ersetzt
        self._items_widget = QWidget()
        self._scroll.setWidget(self._items_widget)
        card_lay.addWidget(self._scroll, 1)

        # Footer ────────────────────────────────────────────────────────────
        self._footer = QWidget()
        self._footer.setStyleSheet(
            f"background:{_C_BG};border-top:1px solid {_C_SEP};"
            "border-radius:0 0 14px 14px;"
        )
        fl = QHBoxLayout(self._footer)
        fl.setContentsMargins(16, 9, 16, 9)
        self._footer_lbl = QLabel()
        self._footer_lbl.setStyleSheet(
            f"font-size:11px;color:{_C_SUB};background:transparent;"
        )
        fl.addWidget(self._footer_lbl)
        fl.addStretch()
        card_lay.addWidget(self._footer)

        outer.addWidget(self._card)

    # ── Public API ────────────────────────────────────────────────────────

    def load_notifications(self, notifications: list) -> None:
        """Ersetzt den gesamten Scroll-Inhalt frisch – kein Recycling."""

        # Altes Widget komplett wegwerfen und neu erstellen
        old = self._scroll.takeWidget()
        if old is not None:
            old.setParent(None)
            old.deleteLater()

        container = QWidget()
        container.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        unread = sum(1 for n in notifications if n.get("ReadAt") is None)

        # Header-Badge
        if unread > 0:
            self._badge.setText(f"{unread} new")
            self._badge.setVisible(True)
        else:
            self._badge.setVisible(False)
        self._btn_all.setVisible(unread > 0)

        if not notifications:
            lbl = QLabel("No notifications.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                f"color:{_C_SUB};font-size:13px;padding:36px 16px;"
                "background:transparent;"
            )
            lay.addWidget(lbl)
            lay.addStretch()
            self._footer_lbl.setText("")
            self._scroll.setFixedHeight(100)
        else:
            for n in notifications:
                item = _NotifItem(n)
                item.clicked.connect(self._on_item_clicked)
                item.yarn_clicked.connect(self._on_item_yarn_clicked)
                item.request_clicked.connect(self._on_item_request_clicked)
                item.request_changed_clicked.connect(self._on_item_request_changed_clicked)
                item.read_toggled.connect(lambda: self._refresh_footer(notifications))
                lay.addWidget(item)
            lay.addStretch()

            scroll_h = min(len(notifications) * _ITEM_H + 8, _MAX_SCROLL_H)
            self._scroll.setFixedHeight(scroll_h)
            self._footer_lbl.setText(f"{unread} ungelesen · {len(notifications)} total")

        self._items_widget = container
        self._scroll.setWidget(container)
        self.adjustSize()

    def _refresh_footer(self, notifications: list) -> None:
        """Aktualisiert Footer-Text nach Einzeln-gelesen."""
        try:
            # Widget-Kinder zaehlen die noch als ungelesen markiert sind
            unread = sum(
                1 for i in range(self._items_widget.layout().count())
                if (w := self._items_widget.layout().itemAt(i).widget())
                and isinstance(w, _NotifItem)
                and w._is_unread
            )
            total = sum(
                1 for i in range(self._items_widget.layout().count())
                if isinstance(
                    self._items_widget.layout().itemAt(i).widget(), _NotifItem)
            )
            self._footer_lbl.setText(f"{unread} ungelesen · {total} total")
            if unread == 0:
                self._badge.setVisible(False)
                self._btn_all.setVisible(False)
            else:
                self._badge.setText(f"{unread} new")
        except Exception:
            pass

    def _on_item_clicked(self, series_id: int, exp_id_txt: str):
        self.hide()
        try:
            from ui.notifications import get_series_nav_info
            info = get_series_nav_info(series_id)
            if info and info["exp_pk"]:
                self.notification_clicked.emit(
                    info["exp_pk"], info["series_pk"], info["experiment_id"])
                return
        except Exception as e:
            print(f"[NotifPanel] nav-lookup: {e}")
        self.notification_clicked.emit(0, series_id, exp_id_txt)

    def _on_item_yarn_clicked(self, yarn_id: int, charge: str):
        self.hide()
        self.yarn_stock_clicked.emit(yarn_id, charge)

    def _on_item_request_clicked(self, request_id: int):
        self.hide()
        self.experiment_request_clicked.emit(request_id)

    def _on_item_request_changed_clicked(self, request_id: int, archived_version_id: int):
        self.hide()
        self.experiment_request_changed_clicked.emit(request_id, archived_version_id)

    def _on_mark_all(self):
        self.all_read.emit()
        self._badge.setVisible(False)
        self._btn_all.setVisible(False)