from PyQt6.QtCore import QTimer, QObject, pyqtSignal
from db import database as db
from models import task as task_model
from services import jira_client
from datetime import datetime


class Scheduler(QObject):
    task_overdue = pyqtSignal(list)
    task_due_today = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._notified_overdue: set = set()   # task ids already notified this session
        self._notified_today: set = set()

    def start(self):
        self._timer.start(60_000)
        self._tick()

    def _notifications_enabled(self) -> bool:
        return db.get_setting("notifications_enabled", "1") == "1"

    def _tick(self):
        close_time = db.get_setting("task_auto_close_time", "23:59")
        now = datetime.now()
        current_time = now.strftime("%H:%M")

        overdue = task_model.get_overdue()
        due_today = task_model.get_due_today()

        if overdue:
            # only emit for tasks not yet notified this session
            new_overdue = [t for t in overdue if t.id not in self._notified_overdue]
            if new_overdue and self._notifications_enabled():
                self.task_overdue.emit(new_overdue)
                self._notified_overdue.update(t.id for t in new_overdue)
            elif overdue:
                # still refresh dashboard alerts even when notifications muted
                self.task_overdue.emit([])

            if current_time >= close_time:
                self._auto_close(overdue)

        if due_today:
            new_today = [t for t in due_today if t.id not in self._notified_today]
            if new_today and self._notifications_enabled():
                self.task_due_today.emit(new_today)
                self._notified_today.update(t.id for t in new_today)
            elif due_today:
                self.task_due_today.emit([])

    def _auto_close(self, tasks):
        for t in tasks:
            try:
                if t.jira_task_key:
                    jira_client.transition_issue(t.jira_task_key, "Done")
                task_model.update_status(t.id, "done")
                self._notified_overdue.discard(t.id)
            except Exception:
                pass
