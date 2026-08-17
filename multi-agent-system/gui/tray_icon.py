from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from gui.assets import asset_exists, asset_path


def _make_icon() -> QIcon:
    if asset_exists("icons", "tray.png"):
        return QIcon(asset_path("icons", "tray.png"))
    placeholder = QPixmap(32, 32)
    placeholder.fill(QColor("#0078D4"))
    return QIcon(placeholder)


class TrayIcon(QSystemTrayIcon):
    def __init__(self, chat_window, app: QApplication):
        super().__init__(_make_icon(), app)
        self._chat = chat_window
        self.setToolTip("Pattu — your personal assistant")

        menu = QMenu()
        menu.addAction("Open Chat", chat_window.toggle)
        menu.addAction("Daily Brief", chat_window.run_daily_brief)
        menu.addSeparator()
        menu.addAction("Quit", app.quit)
        self.setContextMenu(menu)

        self.activated.connect(self._on_activate)

    def _on_activate(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._chat.toggle()
