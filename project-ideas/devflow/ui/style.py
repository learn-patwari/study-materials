APP_STYLE = """
QWidget {
    background-color: #0f1420;
    color: #e8ecf0;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}
QMainWindow, QDialog {
    background-color: #0f1420;
}
QFrame#panel {
    background-color: #1a2133;
    border: 1px solid #2a3a55;
    border-radius: 4px;
}
QTabBar::tab {
    background: transparent;
    color: #8a9bb0;
    padding: 8px 18px;
    border: none;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    color: #e8ecf0;
    border-bottom: 2px solid #4a90d9;
}
QTabWidget::pane {
    border: none;
}
QPushButton {
    background-color: #4a90d9;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px 14px;
}
QPushButton:hover {
    background-color: #5aa0e9;
}
QPushButton:disabled {
    background-color: #2a3a55;
    color: #8a9bb0;
}
QPushButton#secondary {
    background-color: #2a3a55;
    color: #e8ecf0;
}
QPushButton#secondary:hover {
    background-color: #3a4a65;
}
QPushButton#danger {
    background-color: #8b2020;
    color: #ffffff;
}
QPushButton#danger:hover {
    background-color: #a03030;
}
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #1a2133;
    border: 1px solid #2a3a55;
    border-radius: 4px;
    padding: 6px 8px;
    color: #e8ecf0;
}
QLineEdit:focus, QTextEdit:focus {
    border-color: #4a90d9;
}
QComboBox {
    background-color: #1a2133;
    border: 1px solid #2a3a55;
    border-radius: 4px;
    padding: 5px 8px;
    color: #e8ecf0;
}
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView {
    background-color: #1a2133;
    border: 1px solid #2a3a55;
    selection-background-color: #4a90d9;
}
QListWidget, QTableWidget {
    background-color: #1a2133;
    border: 1px solid #2a3a55;
    border-radius: 4px;
    alternate-background-color: #1e2840;
}
QListWidget::item:selected, QTableWidget::item:selected {
    background-color: #2a4a7a;
}
QHeaderView::section {
    background-color: #0f1420;
    color: #8a9bb0;
    border: none;
    padding: 6px 8px;
    font-weight: bold;
}
QScrollBar:vertical {
    background: #0f1420;
    width: 8px;
}
QScrollBar::handle:vertical {
    background: #2a3a55;
    border-radius: 4px;
}
QLabel#section_title {
    color: #8a9bb0;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}
QLabel#alert_red {
    background-color: #3a0a0a;
    color: #ff6b6b;
    border: 1px solid #8b2020;
    border-radius: 4px;
    padding: 8px 12px;
}
QLabel#alert_amber {
    background-color: #2a1a00;
    color: #f0a030;
    border: 1px solid #7a5010;
    border-radius: 4px;
    padding: 8px 12px;
}
QSpinBox {
    background-color: #1a2133;
    border: 1px solid #2a3a55;
    border-radius: 4px;
    padding: 5px 8px;
    color: #e8ecf0;
}
QSplitter::handle {
    background-color: #2a3a55;
    width: 1px;
}
"""

STATUS_COLORS = {
    "new": ("#4a90d9", "#0d2040"),
    "open": ("#4a90d9", "#0d2040"),
    "in_progress": ("#f0a030", "#2a1a00"),
    "in progress": ("#f0a030", "#2a1a00"),
    "done": ("#3ab06a", "#0a2a1a"),
    "posted": ("#3ab06a", "#0a2a1a"),
    "approved": ("#3ab06a", "#0a2a1a"),
    "draft": ("#8a9bb0", "#1a2133"),
    "reviewing": ("#9b6abf", "#200a30"),
    "bug": ("#e05050", "#2a0a0a"),
    "may_fail": ("#f0a030", "#2a1a00"),
}


def status_pill_style(status: str) -> str:
    fg, bg = STATUS_COLORS.get(status.lower(), ("#8a9bb0", "#1a2133"))
    return f"color: {fg}; background-color: {bg}; border-radius: 10px; padding: 2px 10px; font-size: 11px; font-weight: bold;"
