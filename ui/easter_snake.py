"""
easter_snake.py  –  🐍 Easter Egg für TrippleT
================================================
Nicht-modales Fenster: läuft im Hintergrund weiter, auch wenn TrippleT
im Vordergrund ist. Wird automatisch geschlossen wenn das Parent-Fenster
(TrippleT) geschlossen wird.

Aufruf aus screen_home.py (Singleton):
    SnakeDialog.open_or_raise(parent=self)

Steuerung: Pfeiltasten / WASD  |  P oder Space = Pause  |  ESC = schliessen
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QRect
from PySide6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush, QKeyEvent, QCloseEvent
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QMessageBox
)

# ── Konfiguration ──────────────────────────────────────────────────────────────
CELL        = 22
COLS        = 24
ROWS        = 22
FPS         = 30
BASE_DELAY  = 220         # ms pro Schritt
MIN_DELAY   = 75

CANVAS_W    = COLS * CELL
CANVAS_H    = ROWS * CELL

# Farben
C_BG        = QColor("#1a1a2e")
C_GRID      = QColor("#1e2240")
C_HEAD      = QColor("#00ff88")
C_FOOD      = QColor("#ff4757")
C_FOOD2     = QColor("#ff6b81")
C_TEXT      = QColor("#e2e2e2")
C_GOLD      = QColor("#ffd700")
C_PAUSE_BG  = QColor(0, 0, 0, 160)

HIGHSCORE_FILE = Path.home() / ".tripplet_snake_hs.json"


def _load_hs() -> int:
    try:
        return json.loads(HIGHSCORE_FILE.read_text()).get("hs", 0)
    except Exception:
        return 0


def _save_hs(score: int):
    current = _load_hs()
    if score > current:
        HIGHSCORE_FILE.write_text(json.dumps({"hs": score}))


# ── Spiellogik ─────────────────────────────────────────────────────────────────

class SnakeGame:
    def __init__(self):
        self.highscore = _load_hs()
        self._reset()

    def _reset(self):
        mid_r, mid_c = ROWS // 2, COLS // 2
        self.snake       = [(mid_r, mid_c), (mid_r, mid_c - 1), (mid_r, mid_c - 2)]
        self.direction   = (0, 1)
        self.next_dir    = (0, 1)
        self.food        = self._place_food()
        self.score       = 0
        self.level       = 1
        self.paused      = False
        self.running     = True
        self.food_anim   = 0
        self._step_delay = BASE_DELAY
        self._last_step  = time.time()

    def new_game(self):
        self._reset()

    def _place_food(self):
        occupied = set(self.snake)
        while True:
            pos = (random.randint(0, ROWS - 1), random.randint(0, COLS - 1))
            if pos not in occupied:
                return pos

    def handle_key(self, event: QKeyEvent):
        k = event.key()
        if k in (Qt.Key.Key_P, Qt.Key.Key_Space):
            if self.running:
                self.paused = not self.paused
            return
        if self.paused or not self.running:
            return
        moves = {
            Qt.Key.Key_Up:    (-1,  0),
            Qt.Key.Key_W:     (-1,  0),
            Qt.Key.Key_Down:  ( 1,  0),
            Qt.Key.Key_S:     ( 1,  0),
            Qt.Key.Key_Left:  ( 0, -1),
            Qt.Key.Key_A:     ( 0, -1),
            Qt.Key.Key_Right: ( 0,  1),
            Qt.Key.Key_D:     ( 0,  1),
        }
        nd = moves.get(k)
        if nd and (nd[0] != -self.direction[0] or nd[1] != -self.direction[1]):
            self.next_dir = nd

    def tick(self) -> bool:
        """True = Game Over."""
        self.food_anim = (self.food_anim + 1) % FPS
        if not self.running or self.paused:
            return False
        now = time.time()
        if now - self._last_step < self._step_delay / 1000:
            return False
        self._last_step = now
        return self._step()

    def _step(self) -> bool:
        self.direction = self.next_dir
        head = (self.snake[0][0] + self.direction[0],
                self.snake[0][1] + self.direction[1])
        if (head[0] < 0 or head[0] >= ROWS or
                head[1] < 0 or head[1] >= COLS or
                head in self.snake):
            self.running = False
            _save_hs(self.score)
            if self.score > self.highscore:
                self.highscore = self.score
            return True
        self.snake.insert(0, head)
        if head == self.food:
            self.score += 10 + self.level
            self.level  = 1 + self.score // 80
            self._step_delay = max(MIN_DELAY, BASE_DELAY - (self.level - 1) * 18)
            if self.score > self.highscore:
                self.highscore = self.score
            self.food = self._place_food()
        else:
            self.snake.pop()
        return False


# ── Canvas-Widget ──────────────────────────────────────────────────────────────

class _SnakeCanvas(QWidget):
    def __init__(self, game: SnakeGame):
        super().__init__()
        self._g = game
        self.setFixedSize(CANVAS_W, CANVAS_H)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        g = self._g

        p.fillRect(self.rect(), C_BG)
        p.setPen(QPen(C_GRID, 1))
        for r in range(ROWS):
            for c in range(COLS):
                p.drawRect(c * CELL, r * CELL, CELL, CELL)

        # Food
        food_col = C_FOOD if g.food_anim < FPS // 2 else C_FOOD2
        fr, fc = g.food
        margin = 4
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(food_col))
        p.drawEllipse(fc * CELL + margin, fr * CELL + margin,
                      CELL - margin * 2, CELL - margin * 2)

        # Schlange
        for i, (r, c) in enumerate(g.snake):
            x1, y1 = c * CELL + 1, r * CELL + 1
            w = h = CELL - 2
            if i == 0:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(C_HEAD))
                p.drawRoundedRect(x1, y1, w, h, 4, 4)
                dr, dc = g.direction
                p.setBrush(QBrush(C_BG))
                eye_size = 5
                if   dc ==  1: eyes = [(x1+w-8, y1+4),  (x1+w-8, y1+h-9)]
                elif dc == -1: eyes = [(x1+3,   y1+4),  (x1+3,   y1+h-9)]
                elif dr == -1: eyes = [(x1+4,   y1+3),  (x1+w-9, y1+3)]
                else:          eyes = [(x1+4,   y1+h-8),(x1+w-9, y1+h-8)]
                for ex, ey in eyes:
                    p.drawEllipse(ex, ey, eye_size, eye_size)
            else:
                shade = max(50, 210 - i * 6)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor(0, shade, shade // 3)))
                p.drawRoundedRect(x1 + 1, y1 + 1, w - 2, h - 2, 3, 3)

        # Pause-Overlay
        if g.paused and g.running:
            p.fillRect(self.rect(), C_PAUSE_BG)
            p.setPen(QPen(C_GOLD))
            p.setFont(QFont("Consolas", 28, QFont.Weight.Bold))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "⏸  PAUSE")
            p.setPen(QPen(C_TEXT))
            p.setFont(QFont("Consolas", 11))
            hint_rect = QRect(0, CANVAS_H // 2 + 40, CANVAS_W, 30)
            p.drawText(hint_rect, Qt.AlignmentFlag.AlignCenter, "P / Space = weiter")

        p.end()

    def keyPressEvent(self, event: QKeyEvent):
        self._g.handle_key(event)
        self.update()


# ── Haupt-Fenster ──────────────────────────────────────────────────────────────

class SnakeDialog(QWidget):
    """
    Nicht-modales Snake-Fenster.

    Singleton via open_or_raise():
        SnakeDialog.open_or_raise(parent=self)

    - Läuft im Hintergrund weiter (Timer pausiert nicht bei Fokusverlust,
      ausser das Spiel ist in Pause).
    - Beim Fokusverlust wird das Spiel automatisch pausiert.
    - Schliesst sich automatisch wenn das Parent-Fenster geschlossen wird.
    """

    _instance: SnakeDialog | None = None

    @classmethod
    def open_or_raise(cls, parent: QWidget | None = None) -> "SnakeDialog":
        """Singleton: existierendes Fenster in den Vordergrund, sonst neu erstellen."""
        if cls._instance is not None and not cls._instance._destroyed:
            cls._instance.raise_()
            cls._instance.activateWindow()
            return cls._instance
        inst = cls(parent)
        cls._instance = inst
        inst.show()
        return inst

    def __init__(self, parent: QWidget | None = None):
        # Tool-Window: eigenes Fenster, erscheint aber nicht in der Taskbar
        # als separater Eintrag. Bleibt sichtbar auch wenn TrippleT den Fokus hat.
        # parent=None damit das Fenster wirklich unabhängig ist (kein "always on top" Verhalten).
        # Den echten parent merken wir uns nur für den CloseEvent-EventFilter.
        super().__init__(None, Qt.WindowType.Window)
        self._tt_parent = parent
        self._destroyed = False
        self.setWindowTitle("🐍  Snake")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self.setStyleSheet("""
            QWidget   { background: #1a1a2e; }
            QLabel    { color: #e2e2e2; font-family: Consolas, monospace; }
        """)

        self._game   = SnakeGame()
        self._canvas = _SnakeCanvas(self._game)

        # Score-Zeile
        self._lbl_score = QLabel("Score: 0")
        self._lbl_score.setFont(QFont("Consolas", 12, QFont.Weight.Bold))

        self._lbl_level = QLabel("Level 1")
        self._lbl_level.setFont(QFont("Consolas", 11))
        self._lbl_level.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_level.setStyleSheet("color: #aaaaaa;")

        self._lbl_hi = QLabel(f"Hi: {self._game.highscore}")
        self._lbl_hi.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self._lbl_hi.setStyleSheet("color: #ffd700;")
        self._lbl_hi.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        top_row = QHBoxLayout()
        top_row.addWidget(self._lbl_score)
        top_row.addWidget(self._lbl_level, 1)
        top_row.addWidget(self._lbl_hi)

        hint = QLabel("Pfeiltasten / WASD  •  P = Pause  •  ESC = schliessen")
        hint.setStyleSheet("color: #555577; font-size: 10px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Rahmen um Canvas
        border = QWidget()
        border.setStyleSheet("background: #0f3460; border-radius: 3px;")
        border_layout = QVBoxLayout(border)
        border_layout.setContentsMargins(2, 2, 2, 2)
        border_layout.addWidget(self._canvas)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        layout.addLayout(top_row)
        layout.addWidget(border)
        layout.addWidget(hint)

        self.setFixedSize(self.sizeHint())

        # Timer läuft immer — Pause-Logik ist im SnakeGame selbst
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000 // FPS)

        # Parent-Fenster überwachen: wenn TrippleT schliesst → Snake auch
        if self._tt_parent is not None:
            try:
                top = self._tt_parent.window()
                top.installEventFilter(self)
            except Exception:
                pass

        self._canvas.setFocus()

    # ── Fokusverlust → automatisch pausieren ──────────────────────────────────

    def changeEvent(self, event):
        """Wenn das Fenster den Fokus verliert → Spiel pausieren."""
        super().changeEvent(event)
        try:
            from PySide6.QtCore import QEvent
            if event.type() == QEvent.Type.ActivationChange:
                if not self.isActiveWindow() and self._game.running and not self._game.paused:
                    self._game.paused = True
                    self._canvas.update()
        except Exception:
            pass

    # ── Parent-Fenster schliessen → Snake schliessen ──────────────────────────

    def eventFilter(self, obj, event):
        """Überwacht das TrippleT-Hauptfenster auf CloseEvent."""
        try:
            from PySide6.QtCore import QEvent
            if event.type() == QEvent.Type.Close:
                self._timer.stop()
                self.close()
        except Exception:
            pass
        return False

    # ── Tick ──────────────────────────────────────────────────────────────────

    def _tick(self):
        game_over = self._game.tick()
        self._lbl_score.setText(f"Score: {self._game.score}")
        self._lbl_level.setText(f"Level {self._game.level}")
        self._lbl_hi.setText(f"Hi: {self._game.highscore}")
        self._canvas.update()
        if game_over:
            self._timer.stop()
            self._show_gameover()

    # ── Game-Over-Popup ───────────────────────────────────────────────────────

    def _show_gameover(self):
        g = self._game
        new_hi = g.score >= g.highscore and g.score > 0

        msg = QMessageBox(self)
        msg.setWindowTitle("Game Over")
        msg.setStyleSheet("""
            QMessageBox { background: #1a1a2e; }
            QLabel {
                color: #e2e2e2;
                font-family: Consolas, monospace;
                font-size: 13px;
            }
            QPushButton {
                background: #0f3460; color: #e2e2e2;
                border: 1px solid #2a4a80; border-radius: 4px;
                padding: 6px 20px; min-width: 80px;
                font-family: Consolas;
            }
            QPushButton:hover   { background: #1a4a80; }
            QPushButton:default { background: #00ff88; color: #1a1a2e; }
        """)
        hi_line = "⭐ Neuer Highscore!\n" if new_hi else ""
        msg.setText(
            f"{'🎉 ' if new_hi else ''}GAME OVER\n\n"
            f"{hi_line}"
            f"Score: {g.score}   |   Highscore: {g.highscore}\n\n"
            f"Nochmal spielen?"
        )
        btn_ja   = msg.addButton("✔  Ja",   QMessageBox.ButtonRole.AcceptRole)
        btn_nein = msg.addButton("✘  Nein", QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(btn_ja)
        msg.exec()

        if msg.clickedButton() == btn_ja:
            self._game.new_game()
            self._timer.start(1000 // FPS)
            self._canvas.setFocus()
        else:
            self.close()

    # ── Schliessen ────────────────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            self._game.handle_key(event)
            self._canvas.update()

    def closeEvent(self, event: QCloseEvent):
        self._timer.stop()
        self._destroyed = True
        SnakeDialog._instance = None
        super().closeEvent(event)


# ── Standalone-Test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dlg = SnakeDialog.open_or_raise()
    sys.exit(app.exec())