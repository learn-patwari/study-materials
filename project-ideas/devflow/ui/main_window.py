from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QSystemTrayIcon, QMenu, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
from ui.dashboard_panel import DashboardPanel
from ui.srs_selector import SRSPanel
from ui.sprint_panel import SprintPanel
from ui.pr_review_panel import PRReviewPanel
from ui.bugs_panel import BugsPanel
from ui.settings_dialog import SettingsDialog
from services.pr_watcher import PRWatcher
from services.scheduler import Scheduler


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DevFlow")
        self.setMinimumSize(1200, 800)
        self._build_ui()
        self._setup_tray()
        self._setup_services()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(12, 8, 12, 8)
        top_bar.addStretch()
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.setObjectName("secondary")
        settings_btn.clicked.connect(self._open_settings)
        top_bar.addWidget(settings_btn)
        layout.addLayout(top_bar)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        self._dashboard = DashboardPanel()
        self._tabs.addTab(self._dashboard, "Dashboard")

        self._srs = SRSPanel()
        self._tabs.addTab(self._srs, "SRS")

        self._sprint = SprintPanel()
        self._tabs.addTab(self._sprint, "Sprint")

        self._pr_review = PRReviewPanel()
        self._pr_review.badge_update.connect(self._update_pr_badge)
        self._tabs.addTab(self._pr_review, "PR Review")

        self._bugs = BugsPanel(mode="bugs")
        self._tabs.addTab(self._bugs, "Bugs")

        self._improvements = BugsPanel(mode="improvements")
        self._tabs.addTab(self._improvements, "Improvements")

        layout.addWidget(self._tabs)

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(self)
        self._tray.setToolTip("DevFlow")
        tray_menu = QMenu()
        tray_menu.addAction("Open", self.show)
        tray_menu.addAction("Quit", QApplication.quit)
        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(lambda _: self.show())
        self._tray.show()

    def _setup_services(self):
        self._pr_watcher = PRWatcher(self)
        self._pr_watcher.new_pr_detected.connect(self._on_new_pr)
        self._pr_watcher.start()

        self._scheduler = Scheduler(self)
        self._scheduler.task_overdue.connect(self._on_tasks_overdue)
        self._scheduler.task_due_today.connect(self._on_tasks_due_today)
        self._scheduler.start()

    def _on_new_pr(self, pr: dict):
        self._tray.showMessage(
            "New PR",
            f"PR #{pr.get('pr_id')}: {pr.get('title','')[:60]}\nin {pr.get('repo_slug','')}",
            QSystemTrayIcon.MessageIcon.Information,
            5000,
        )
        self._update_pr_badge(None)

    def _on_tasks_overdue(self, tasks: list):
        if tasks:
            self._tray.showMessage(
                "⚠ Overdue Tasks",
                f"{len(tasks)} task(s) are overdue.",
                QSystemTrayIcon.MessageIcon.Critical,
                8000,
            )
            self._dashboard.refresh_alerts()

    def _on_tasks_due_today(self, tasks: list):
        if tasks:
            self._dashboard.refresh_alerts()

    def _update_pr_badge(self, count):
        from models import pull_request as pr_model
        prs = pr_model.get_all()
        new_count = sum(1 for p in prs if p.status == "new")
        label = f"PR Review ({new_count} new)" if new_count else "PR Review"
        idx = self._tabs.indexOf(self._pr_review)
        self._tabs.setTabText(idx, label)

    def _open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()
