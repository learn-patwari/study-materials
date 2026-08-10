from pathlib import Path

from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QFont, QMovie, QPixmap
from PyQt6.QtWidgets import QLabel


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
        self._movie: QMovie | None = None

        self._load_asset()
        self._restore_position()

    def _load_asset(self) -> None:
        for candidate in ("assets/pattu_transparent.png", "assets/pattu.gif", "assets/pattu_alt.gif", "assets/pattu.png", "assets/pattu.jpg"):
            p = Path(candidate)
            if p.exists():
                if p.suffix.lower() == ".gif":
                    self._movie = QMovie(str(p))
                    self.setMovie(self._movie)
                    self._movie.start()
                else:
                    px = QPixmap(str(p))
                    # Scale to 180px tall keeping aspect ratio — good desktop mascot size
                    self.setPixmap(px.scaledToHeight(180, Qt.TransformationMode.SmoothTransformation))
                self.adjustSize()
                return
        # Fallback: large emoji
        self.setText("🧑‍💻")
        self.setFont(QFont("Segoe UI Emoji", 64))
        self.adjustSize()

    def _restore_position(self) -> None:
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - self.width() - 40, screen.height() - self.height() - 80)

    # ── Drag ──────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._dragged = False

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            delta = (event.globalPosition().toPoint() - self._drag_pos - self.frameGeometry().topLeft()).manhattanLength()
            if delta > 5:
                self._dragged = True
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self._dragged:
            self.clicked.emit()
        self._dragged = False
