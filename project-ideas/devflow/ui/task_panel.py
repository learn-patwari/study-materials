from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QHeaderView
)
from PyQt6.QtCore import Qt
from models import task as task_model
from models.task import Task


STATUS_OPTIONS = ["todo", "in_progress", "done"]


class TaskPanel(QWidget):
    def __init__(self, ticket_id: int, parent=None):
        super().__init__(parent)
        self._ticket_id = ticket_id
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        top = QHBoxLayout()
        self._total_lbl = QLabel("Total estimate: 0h")
        self._total_lbl.setStyleSheet("color: #8a9bb0;")
        top.addWidget(QLabel("Tasks"))
        top.addWidget(self._total_lbl)
        top.addStretch()
        add_btn = QPushButton("+ Add")
        add_btn.setObjectName("secondary")
        add_btn.clicked.connect(self._add_row)
        top.addWidget(add_btn)
        layout.addLayout(top)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Title", "Assignee", "Est (h)", "Type", "Status"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        del_btn = QPushButton("Delete Selected")
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(self._delete_selected)
        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self._save_all)
        bottom = QHBoxLayout()
        bottom.addWidget(del_btn); bottom.addStretch(); bottom.addWidget(save_btn)
        layout.addLayout(bottom)

    def load(self):
        tasks = task_model.get_by_ticket(self._ticket_id)
        self._table.setRowCount(0)
        for t in tasks:
            self._add_row_data(t)
        self._update_total()

    def showEvent(self, event):
        super().showEvent(event)
        self.load()

    def _add_row(self):
        self._add_row_data(Task(id=None, ticket_id=self._ticket_id, title="New task"))

    def _add_row_data(self, t: Task):
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(t.title))
        self._table.setItem(row, 1, QTableWidgetItem(t.assignee))
        self._table.setItem(row, 2, QTableWidgetItem(str(t.estimated_hrs)))
        self._table.setItem(row, 3, QTableWidgetItem(t.task_type))
        status_cb = QComboBox()
        for s in STATUS_OPTIONS:
            status_cb.addItem(s)
        status_cb.setCurrentText(t.status)
        self._table.setCellWidget(row, 4, status_cb)
        self._table.item(row, 0).setData(Qt.ItemDataRole.UserRole, t.id)

    def _update_total(self):
        total = 0.0
        for row in range(self._table.rowCount()):
            try:
                total += float(self._table.item(row, 2).text())
            except Exception:
                pass
        self._total_lbl.setText(f"Total estimate: {total:.1f}h")

    def _save_all(self):
        existing = {t.id: t for t in task_model.get_by_ticket(self._ticket_id)}
        for row in range(self._table.rowCount()):
            tid = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            status_cb: QComboBox = self._table.cellWidget(row, 4)
            t = Task(
                id=tid, ticket_id=self._ticket_id,
                title=self._table.item(row, 0).text(),
                assignee=self._table.item(row, 1).text() if self._table.item(row, 1) else "",
                estimated_hrs=float(self._table.item(row, 2).text()) if self._table.item(row, 2) else 0,
                task_type=self._table.item(row, 3).text() if self._table.item(row, 3) else "dev",
                status=status_cb.currentText() if status_cb else "todo",
            )
            task_model.save(t)
        self._update_total()

    def _delete_selected(self):
        rows = sorted({i.row() for i in self._table.selectedItems()}, reverse=True)
        for row in rows:
            tid = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if tid:
                task_model.delete(tid)
            self._table.removeRow(row)
        self._update_total()
