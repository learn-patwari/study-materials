from pathlib import Path

from PyQt6.QtGui import QIcon, QPixmap, QColor
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


def _make_icon() -> QIcon:
    for candidate in ("assets/pattu.png", "assets/pattu.gif"):
        if Path(candidate).exists():
            return QIcon(candidate)
    # Generate a simple colored square icon as fallback
    px = QPixmap(32, 32)
    px.fill(QColor("#0078D4"))
    return QIcon(px)


class TrayIcon(QSystemTrayIcon):
    def __init__(self, chat_window, app: QApplication):
        super().__init__(_make_icon(), app)
        self._chat = chat_window
        self.setToolTip("Pattu — your personal assistant")

        menu = QMenu()
        menu.addAction("Open Chat", chat_window.toggle)
        menu.addAction("Daily Brief", chat_window._daily_brief)
        menu.addSeparator()
        menu.addAction("Quit", app.quit)
        self.setContextMenu(menu)

        self.activated.connect(self._on_activate)

    def _on_activate(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._chat.toggle()
