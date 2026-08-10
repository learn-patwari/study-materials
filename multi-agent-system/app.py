import sys
import os

# Ensure imports resolve from project root
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from utils.config import load_settings, ConfigError
from gui.mascot_widget import MascotWidget
from gui.chat_window import ChatWindow
from gui.tray_icon import TrayIcon


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Pattu")
    app.setOrganizationName("Akshay Patwari")

    try:
        settings = load_settings()
    except ConfigError as exc:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "Pattu — Config Error", str(exc))
        sys.exit(1)

    chat   = ChatWindow(settings)
    mascot = MascotWidget()
    tray   = TrayIcon(chat, app)

    mascot.clicked.connect(chat.toggle)
    tray.show()
    mascot.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
