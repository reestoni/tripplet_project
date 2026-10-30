from __future__ import annotations
# ui/widgets/save_tick.py
"""Short "saved" confirmation: a large green tick in the middle of a widget
that shrinks and fades out (~0.9 s).

The overlay is transparent for mouse events and never takes focus, so the
table underneath stays fully usable while the animation runs.

Usage:  show_save_tick(self)   # self = the screen to centre the tick on
"""

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

TICK_GREEN = "#39a650"   # Heberlein brand accent (see ui/theme.py)
DURATION_MS = 900


class _SaveTick(QWidget):
    def __init__(self, host: QWidget):
        super().__init__(host)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.NoFocus)
        self._t = 0.0  # animation progress 0..1
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(DURATION_MS)
        self._anim.setEasingCurve(QEasingCurve.Linear)
        self._anim.valueChanged.connect(self._on_value)
        self._anim.finished.connect(self.hide)

    def play(self) -> None:
        host = self.parentWidget()
        if host is not None:
            self.setGeometry(host.rect())
        self._anim.stop()
        self._t = 0.0
        self.show()
        self.raise_()
        self._anim.start()

    def _on_value(self, v) -> None:
        self._t = float(v)
        self.update()

    def paintEvent(self, _event) -> None:
        t = self._t
        # Full size and opacity for the first 20 %, then shrink to 60 % and fade
        k = 0.0 if t < 0.2 else (t - 0.2) / 0.8
        ease = 1.0 - (1.0 - k) ** 2          # ease-out
        scale = 1.0 - 0.4 * ease
        opacity = 1.0 - ease

        d = max(80.0, min(self.width(), self.height()) * 0.28) * scale
        cx, cy = self.width() / 2.0, self.height() / 2.0

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setOpacity(opacity)

        circle = QColor(TICK_GREEN)
        circle.setAlpha(225)
        p.setPen(Qt.NoPen)
        p.setBrush(circle)
        p.drawEllipse(QRectF(cx - d / 2, cy - d / 2, d, d))

        pen = QPen(QColor("#ffffff"), d * 0.09)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        path = QPainterPath(QPointF(cx - d * 0.22, cy + d * 0.01))
        path.lineTo(QPointF(cx - d * 0.06, cy + d * 0.17))
        path.lineTo(QPointF(cx + d * 0.24, cy - d * 0.15))
        p.drawPath(path)
        p.end()


def show_save_tick(host: QWidget) -> None:
    """Play the tick centred on *host*. Never raises."""
    try:
        tick = getattr(host, "_save_tick_overlay", None)
        if tick is None:
            tick = _SaveTick(host)
            host._save_tick_overlay = tick
        tick.play()
    except Exception:
        pass
