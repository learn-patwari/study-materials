"""The floating Pattu character on the desktop.

Deliberately thin: window flags, drag-vs-click, and handing frames to the
screen. What pose to show is decided in ``mascot_states.py`` and drawn by
``mascot_animator.py``.
"""
from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel

from gui.mascot_animator import MascotAnimator
from gui.mascot_states import MascotState

# Moving further than this while the button is down counts as a drag, not a
# click — without it a slightly shaky click would open the chat unintentionally.
DRAG_THRESHOLD_PX = 5

# How long the launch wave holds before the idle drift takes over.
GREETING_MS = 3_000


class MascotWidget(QLabel):
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to open Pattu · Drag to move")

        self._drag_pos = QPoint()
        self._dragged = False
        self._bob_offset = 0
        self._base_y: int | None = None

        self._animator = MascotAnimator(self)
        if self._animator.has_frames:
            # Fixed size across every pose, so dragging stays steady while the
            # character animates.
            self.setFixedSize(*self._animator.frame_size)
        else:
            self._show_fallback()

        self._place_bottom_right()
        self._animator.start()

    def _show_fallback(self) -> None:
        """Shown only if the artwork is missing entirely."""
        self.setText("🧑‍💻")
        self.setFont(QFont("Segoe UI Emoji", 64))
        self.adjustSize()

    def _place_bottom_right(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - self.width() - 40, screen.height() - self.height() - 80)
        self._base_y = self.y()

    # ── Called by the animator ────────────────────────────────────────────────

    def set_frame(self, pixmap: QPixmap) -> None:
        self.setPixmap(pixmap)

    def set_bob_offset(self, dy: int) -> None:
        """Breathing motion — shift from the resting position, not the current one."""
        if self._base_y is None or dy == self._bob_offset:
            return
        self._bob_offset = dy
        super().move(self.x(), self._base_y + dy)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_state(self, state: MascotState) -> None:
        self._animator.set_state(state)

    def greet(self) -> None:
        """Wave on launch, then settle."""
        self.set_state(MascotState.GREETING)
        QTimer.singleShot(GREETING_MS, lambda: self.set_state(MascotState.IDLE))

    # ── Drag and click ────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._dragged = False

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            target = event.globalPosition().toPoint() - self._drag_pos
            if (target - self.frameGeometry().topLeft()).manhattanLength() > DRAG_THRESHOLD_PX:
                self._dragged = True
            self.move(target)
            # Re-anchor the bob to wherever it was dropped.
            self._base_y = target.y() - self._bob_offset

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self._dragged:
            self.clicked.emit()
        self._dragged = False
