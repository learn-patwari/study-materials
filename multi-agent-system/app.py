import os
import sys

# Ensure imports resolve from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from gui.assets import asset_exists, asset_path
from gui.chat_window import ChatWindow
from gui.mascot_widget import MascotWidget
from gui.tray_icon import TrayIcon
from utils.config import ConfigError, load_settings

# Windows groups taskbar buttons by this ID. Without setting it the app is
# treated as generic Python and shows the Python icon instead of Pattu's.
APP_USER_MODEL_ID = "AkshayPatwari.Pattu.Assistant.1"


def _set_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        # Cosmetic only — never block startup over a taskbar icon.
        pass


def main():
    _set_windows_app_id()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Pattu")
    app.setOrganizationName("Akshay Patwari")
    if asset_exists("icons", "taskbar.png"):
        app.setWindowIcon(QIcon(asset_path("icons", "taskbar.png")))

    try:
        settings = load_settings()
    except ConfigError as exc:
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.critical(None, "Pattu — Config Error", str(exc))
        sys.exit(1)

    chat = ChatWindow(settings)
    mascot = MascotWidget()
    tray = TrayIcon(chat, app)

    mascot.clicked.connect(chat.toggle)
    chat.mascot_state.connect(mascot.set_state)

    tray.show()
    mascot.show()
    mascot.greet()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
