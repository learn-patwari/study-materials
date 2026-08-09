from PyQt6.QtCore import QTimer, QObject, pyqtSignal
from db import database as db
from models import task as task_model
from services import jira_client
from datetime import datetime


class Scheduler(QObject):
    task_overdue = pyqtSignal(list)   # list of Task
    task_due_today = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._timer.start(60_000)
        self._tick()  # run immediately on startup

    def _tick(self):
        close_time = db.get_setting("task_auto_close_time", "23:59")
        now = datetime.now()
        current_time = now.strftime("%H:%M")

        overdue = task_model.get_overdue()
        due_today = task_model.get_due_today()

        if overdue:
            self.task_overdue.emit(overdue)
            if current_time >= close_time:
                self._auto_close(overdue)

        if due_today:
            self.task_due_today.emit(due_today)

    def _auto_close(self, tasks):
        for t in tasks:
            try:
                if t.jira_task_key:
                    jira_client.transition_issue(t.jira_task_key, "Done")
                task_model.update_status(t.id, "done")
            except Exception:
                pass
