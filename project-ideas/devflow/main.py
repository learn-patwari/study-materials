import sys
import os

# Must be set before any Qt import — suppresses Chromium GPU noise
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter

# WebEngine must be imported (or AA_ShareOpenGLContexts set) before QApplication
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
import PyQt6.QtWebEngineWidgets  # noqa: F401 — triggers early init before QApp

from ui.main_window import MainWindow
from db import database as db


def _make_icon() -> QIcon:
    px = QPixmap(64, 64)
    px.fill(QColor(0, 0, 0, 0))
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#4a90d9"))
    p.setPen(QColor("#4a90d9"))
    p.drawRoundedRect(2, 2, 60, 60, 14, 14)
    p.setPen(QColor("#ffffff"))
    font = p.font()
    font.setBold(True)
    font.setPixelSize(42)
    p.setFont(font)
    p.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, "D")
    p.end()
    return QIcon(px)


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("DevFlow")
    app.setOrganizationName("DevFlow")
    app.setWindowIcon(_make_icon())

    db.get_connection()

    from ui.style import APP_STYLE
    app.setStyleSheet(APP_STYLE)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
