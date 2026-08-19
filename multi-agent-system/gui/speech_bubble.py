"""The small text bubble that pops up next to Pattu when it reacts.

Purely cosmetic — decides nothing about *when* Pattu speaks (that's
``mascot_states.greeting_for``) or *what pose* it's in (``mascot_animator``).
This widget only knows how to show a line of text near another widget and
fade it back out.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QLabel, QWidget

from gui import theme

# How long a bubble stays up before it fades itself out.
BUBBLE_HOLD_MS = 2_400

BUBBLE_STYLE = (
    f"background:{theme.BG_BUBBLE_PATTU}; color:{theme.TEXT};"
    f"border:1px solid {theme.BORDER}; border-radius:{theme.RADIUS}px;"
    "padding:6px 12px; font-size:12px;"
)


class SpeechBubble(QLabel):
    """A frameless, always-on-top label anchored above whatever widget it follows."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(BUBBLE_STYLE)
        self.setWordWrap(True)
        self.hide()
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def say(self, text: str, anchor: QWidget) -> None:
        """Show ``text`` positioned just above ``anchor``, then auto-hide."""
        self.setText(text)
        self.adjustSize()

        anchor_pos = anchor.mapToGlobal(anchor.rect().topLeft())
        x = anchor_pos.x() + (anchor.width() - self.width()) // 2
        y = anchor_pos.y() - self.height() - 8
        self.move(x, y)

        self.show()
        self.raise_()
        self._hide_timer.start(BUBBLE_HOLD_MS)
