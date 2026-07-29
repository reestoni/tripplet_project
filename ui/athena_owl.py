# ui/athena_owl.py
"""Athena – animierte Eulen-Figur für den agentT Advisor.

AthenaOwl ist ein QLabel das absolut im Parent-Widget positioniert wird
und während der KI-Analyse über den Screen fliegt, Dokumente liest,
nachdenkt, jubelt und wegwirft.

Dreifach-Klick auf das Header-Label weckt Athena im Demo-Modus (kein API-Call).

Sprites unter assets/owl_sprites/:
    Set 1: owl_sleep, owl_fly1, owl_fly2, owl_read1, owl_read2, owl_toss
    Set 2: owl_think, owl_eureka, owl_tired, owl_nod, owl_shake, owl_celebrate
    Set 3: (kommt bald)
"""
from __future__ import annotations

import sys
import random
from pathlib import Path

from PySide6.QtWidgets import QLabel, QWidget
from PySide6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QColor


# ---------------------------------------------------------------------------
# Sprite-Pfade
# ---------------------------------------------------------------------------
def _sprite_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets" / "owl_sprites"
    return Path(__file__).parent.parent / "assets" / "owl_sprites"


_SPRITE_KEYS = (
    # Set 1 — Basis
    "sleep_1", "sleep_2", "sleep_3", "fly1", "fly2", "read1", "read2", "toss",
    # Set 2 — Emotionen
    "think", "eureka", "tired", "nod", "shake", "celebrate",
    # Set 3 — Easter Eggs
    "coffee", "sunglasses", "confused", "magnify", "facepalm", "point",
)


class AthenaOwl(QLabel):
    """Athena – die fliegende Eule."""

    OWL_SIZE = 110

    # Schlaf-Animation: weiches Vor-und-Zurück (Atemrhythmus)
    _SLEEP_CYCLE = ("sleep_1", "sleep_2", "sleep_3", "sleep_2")   # → ping-pong
    _SLEEP_INTERVAL = 600   # ms pro Frame

    # Haupt-Sequenz während Analyse
    SEQUENCE = [
        ("fly",       1600),
        ("read",      2800),
        ("think",     1800),
        ("read",      2000),
        ("toss",      1000),
        ("fly",       1400),
        ("magnify",   1500),  # Lupe raus, genau hinschauen
        ("read",      3000),
        ("nod",        900),
        ("toss",       900),
        ("fly",       1800),
        ("read",      2500),
        ("think",     1400),
        ("toss",       800),
    ]

    # Seltene Überraschungs-Poses (8% Chance nach jedem toss)
    SURPRISE_POSES = [
        ("eureka",      1200),   # Geistesblitz!
        ("tired",       1500),   # Kurz gähnen
        ("shake",       1000),   # Kopfschütteln
        ("celebrate",   1400),   # Jubeln
        ("coffee",      1800),   # Kaffeepause
        ("sunglasses",  1200),   # Kurz cool sein
        ("confused",    1200),   # Verdutzt
        ("facepalm",    1000),   # Facepalm
        ("point",       1000),   # Zeigt auf dich
    ]

    # Demo-Sequenz (kein API-Call)
    DEMO_SEQUENCE = [
        ("fly",         1400),
        ("coffee",      1800),   # Erstmal Kaffee
        ("fly",         1200),
        ("magnify",     1500),   # Schaut genau hin
        ("think",       1200),
        ("eureka",      1000),   # Geistesblitz!
        ("fly",         1200),
        ("read",        1800),
        ("nod",          800),
        ("celebrate",   1400),   # Jubeln
        ("fly",         1000),
        ("sunglasses",  1200),   # Cool bleiben
        ("toss",         800),
    ]

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setFixedSize(self.OWL_SIZE, self.OWL_SIZE)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self.setScaledContents(True)

        # Sprites laden
        self._px: dict[str, QPixmap] = {}
        sd = _sprite_dir()
        for key in _SPRITE_KEYS:
            path = sd / f"owl_{key}.png"
            px   = QPixmap(str(path))
            if px.isNull():
                px = QPixmap(self.OWL_SIZE, self.OWL_SIZE)
                px.fill(QColor(0, 0, 0, 0))
            self._px[key] = px

        # Schlaf-Timer (Atemrhythmus 1→2→3→2→1→...)
        self._sleep_frame = 0
        self._sleep_timer = QTimer(self)
        self._sleep_timer.timeout.connect(self._breathe)
        self._sleep_timer.setInterval(self._SLEEP_INTERVAL)

        # Fly-Timer
        self._fly_frame = 0
        self._fly_timer = QTimer(self)
        self._fly_timer.timeout.connect(self._flap)
        self._fly_timer.setInterval(220)

        # Read-Timer
        self._read_frame = 0
        self._read_timer = QTimer(self)
        self._read_timer.timeout.connect(self._read_flap)
        self._read_timer.setInterval(700)

        # Sequenz-Timer
        self._seq_idx   = 0
        self._seq_timer = QTimer(self)
        self._seq_timer.setSingleShot(True)
        self._seq_timer.timeout.connect(self._next_action)

        self._move_anim: QPropertyAnimation | None = None
        self._working   = False
        self._demo_mode = False
        self._active_sequence = self.SEQUENCE

        self._sleep_timer.start()
        self._show("sleep_1")
        self.raise_()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def place_sleeping(self):
        self.move(self._sleep_pos())
        self._sleep_frame = 0
        self._sleep_timer.start()
        self._show("sleep_1")

    def start_working(self):
        """Weckt Athena für echte Analyse."""
        self._sleep_timer.stop()
        self._demo_mode       = False
        self._active_sequence = self.SEQUENCE
        self._working         = True
        self._seq_idx         = 0
        self._fly_timer.start()
        self._next_action()

    def start_demo(self):
        """Weckt Athena im Demo-Modus (kein API-Call)."""
        self._sleep_timer.stop()
        self._demo_mode       = True
        self._active_sequence = self.DEMO_SEQUENCE
        self._working         = True
        self._seq_idx         = 0
        self._fly_timer.start()
        self._next_action()

    def stop_working(self):
        """Stoppt Animation, Athena schläft wieder."""
        self._working = False
        self._fly_timer.stop()
        self._read_timer.stop()
        self._seq_timer.stop()
        if self._move_anim:
            self._move_anim.stop()
        self._fly_to(self._sleep_pos(), on_done=self._go_sleep, duration=1000)

    # ------------------------------------------------------------------
    # Interne Helfer
    # ------------------------------------------------------------------
    def _sleep_pos(self) -> QPoint:
        p = self.parent()
        if p:
            return QPoint(p.width() - self.OWL_SIZE - 12,
                          p.height() - self.OWL_SIZE - 12)
        return QPoint(10, 10)

    def _random_pos(self) -> QPoint:
        p = self.parent()
        if not p:
            return QPoint(50, 50)
        mx = max(10, p.width()  - self.OWL_SIZE - 20)
        my = max(10, p.height() - self.OWL_SIZE - 20)
        return QPoint(random.randint(10, mx), random.randint(10, my))

    def _fly_to(self, target: QPoint, on_done=None, duration: int = 800):
        if self._move_anim:
            self._move_anim.stop()
        anim = QPropertyAnimation(self, b"pos", self)
        anim.setDuration(duration)
        anim.setStartValue(self.pos())
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.InOutCubic)
        if on_done:
            anim.finished.connect(on_done)
        self._move_anim = anim
        anim.start()

    def _next_action(self):
        if not self._working:
            return

        # Überraschungs-Pose nach toss (8% Chance, nur im echten Modus)
        if not self._demo_mode and self._seq_idx > 0:
            last = self._active_sequence[(self._seq_idx - 1) % len(self._active_sequence)]
            if last[0] == "toss" and random.random() < 0.08:
                pose, dur = random.choice(self.SURPRISE_POSES)
                self._fly_timer.stop()
                self._read_timer.stop()
                self._show(pose)
                self._seq_timer.start(dur)
                return

        action, duration = self._active_sequence[self._seq_idx % len(self._active_sequence)]
        self._seq_idx += 1

        if action == "fly":
            self._read_timer.stop()
            self._fly_timer.start()
            self._fly_to(self._random_pos(), duration=duration)
            self._seq_timer.start(duration + 100)

        elif action == "read":
            self._fly_timer.stop()
            self._read_timer.start()
            self._show("read1")
            self._seq_timer.start(duration)

        elif action in ("think", "nod", "shake", "eureka", "tired", "celebrate",
                        "coffee", "sunglasses", "confused", "magnify", "facepalm", "point"):
            self._fly_timer.stop()
            self._read_timer.stop()
            self._show(action)
            self._seq_timer.start(duration)

        elif action == "toss":
            self._fly_timer.stop()
            self._read_timer.stop()
            self._show("toss")
            self._seq_timer.start(duration)

    def _go_sleep(self):
        self._sleep_frame = 0
        self._sleep_timer.start()
        self._show("sleep_1")

    def _breathe(self):
        """Schlaf-Animation: ping-pong durch sleep_1/2/3/2."""
        self._sleep_frame = (self._sleep_frame + 1) % len(self._SLEEP_CYCLE)
        self._show(self._SLEEP_CYCLE[self._sleep_frame])

    def _flap(self):
        self._fly_frame = (self._fly_frame + 1) % 2
        self._show("fly1" if self._fly_frame == 0 else "fly2")

    def _read_flap(self):
        self._read_frame = (self._read_frame + 1) % 2
        self._show("read1" if self._read_frame == 0 else "read2")

    def _show(self, key: str):
        px = self._px.get(key) or self._px.get("sleep")
        if px:
            self.setPixmap(px)


# ---------------------------------------------------------------------------
# Triple-Click Label — versteckter Demo-Button
# ---------------------------------------------------------------------------
class AthenaHeaderLabel(QLabel):
    """Header-Label mit verstecktem Dreifach-Klick zum Demo-Modus."""

    def __init__(self, text: str, owl: AthenaOwl, parent=None):
        super().__init__(text, parent)
        self._owl         = owl
        self._click_count = 0
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.setInterval(600)
        self._click_timer.timeout.connect(self._reset_clicks)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._click_count += 1
            self._click_timer.start()
            if self._click_count >= 3:
                self._click_count = 0
                self._click_timer.stop()
                self._toggle_demo()
        super().mousePressEvent(event)

    def _reset_clicks(self):
        self._click_count = 0

    def _toggle_demo(self):
        if not self._owl:
            return
        if self._owl._working:
            self._owl.stop_working()
        else:
            self._owl.start_demo()