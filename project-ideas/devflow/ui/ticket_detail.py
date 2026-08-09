from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QPushButton, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from models import ticket as ticket_model
from models import task as task_model
from models import document as doc_model
from services import ai_service, code_reader, jira_client, confluence_client
from ui.requirement_chat import RequirementChat
from ui.task_panel import TaskPanel
from ui.diagram_panel import DiagramPanel
from ui.sdd_panel import SDDPanel
from ui.test_panel import TestPanel
from ui.style import status_pill_style
from db import database as db


class _GenerateThread(QThread):
    step_done = pyqtSignal(str)
    all_done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, ticket_id: int, history: list[dict]):
        super().__init__()
        self._ticket_id = ticket_id
        self._history = history

    def run(self):
        try:
            t = ticket_model.get_by_id(self._ticket_id)
            code = code_reader.ingest(t.source_type or "local", t.code_source or "")
            self.step_done.emit("Code ingested")

            template = db.get_setting("doc_template", "")
            desc = ai_service.generate_formatted_desc(t.srs_content, self._history, template, code)
            self.step_done.emit("Description generated")

            arch = ai_service.generate_architecture(t.srs_content, self._history, code)
            self.step_done.emit("Architecture generated")

            tasks = ai_service.generate_tasks(t.srs_content, self._history, code)
            self.step_done.emit("Tasks generated")

            sdd = ai_service.generate_sdd(t.srs_content, self._history, code)
            self.step_done.emit("SDD generated")

            tests = ai_service.generate_tests(t.srs_content, sdd)
            self.step_done.emit("Test stubs generated")

            self.all_done.emit({"desc": desc, "arch": arch, "tasks": tasks, "sdd": sdd, "tests": tests})
        except Exception as e:
            self.error.emit(str(e))


class TicketDetailPanel(QWidget):
    def __init__(self, ticket_id: int, parent=None):
        super().__init__(parent)
        self._ticket_id = ticket_id
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        t = ticket_model.get_by_id(self._ticket_id)

        # Header
        header = QHBoxLayout()
        title_lbl = QLabel(f"{t.jira_key}  —  {t.title}")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold;")
        header.addWidget(title_lbl)
        header.addStretch()
        self._status_pill = QLabel(t.status)
        self._status_pill.setStyleSheet(status_pill_style(t.status))
        header.addWidget(self._status_pill)
        layout.addLayout(header)

        # Progress bar (hidden normally)
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.hide()
        self._progress_label = QLabel("")
        self._progress_label.hide()
        layout.addWidget(self._progress_label)
        layout.addWidget(self._progress)

        # Tabs
        self._tabs = QTabWidget()
        self._chat_tab = RequirementChat(self._ticket_id)
        self._chat_tab.connect_generate(self._start_generation)
        self._tabs.addTab(self._chat_tab, "Description")

        self._arch_tab = DiagramPanel(self._ticket_id)
        self._tabs.addTab(self._arch_tab, "Architecture")

        self._tasks_tab = TaskPanel(self._ticket_id)
        self._tabs.addTab(self._tasks_tab, "Tasks")

        self._sdd_tab = SDDPanel(self._ticket_id)
        self._tabs.addTab(self._sdd_tab, "SDD")

        self._tests_tab = TestPanel(self._ticket_id)
        self._tabs.addTab(self._tests_tab, "Tests")

        layout.addWidget(self._tabs)

        # Approve & Post bar
        approve_bar = QHBoxLayout()
        approve_bar.addStretch()
        self._approve_btn = QPushButton("✅ Approve & Post to Jira")
        self._approve_btn.setStyleSheet("background-color: #3ab06a; font-size: 13px; padding: 8px 20px;")
        self._approve_btn.clicked.connect(self._approve_and_post)
        approve_bar.addWidget(self._approve_btn)
        layout.addLayout(approve_bar)

    def _start_generation(self):
        history = self._chat_tab.get_history()
        self._progress.show()
        self._progress_label.show()
        self._gen_thread = _GenerateThread(self._ticket_id, history)
        self._gen_thread.step_done.connect(lambda s: self._progress_label.setText(s))
        self._gen_thread.all_done.connect(self._on_generated)
        self._gen_thread.error.connect(self._on_gen_error)
        self._gen_thread.start()

    def _on_generated(self, results: dict):
        self._progress.hide()
        self._progress_label.hide()

        # Save everything
        doc_model.save(doc_model.Document(None, self._ticket_id, "formatted_desc", results["desc"]))
        doc_model.save_diagram(self._ticket_id, results["arch"], _mermaid_to_drawio(results["arch"]))
        doc_model.save(doc_model.Document(None, self._ticket_id, "sdd", results["sdd"]))
        doc_model.save_test_files(self._ticket_id, results["tests"])

        t = ticket_model.get_by_id(self._ticket_id)
        for task_data in results["tasks"]:
            task = task_model.Task(
                id=None, ticket_id=self._ticket_id,
                title=task_data.get("title", ""),
                assignee=task_data.get("assignee_hint", ""),
                estimated_hrs=float(task_data.get("estimated_hrs", 0)),
            )
            task_model.save(task)

        ticket_model.update_status(self._ticket_id, "ready")
        self._status_pill.setText("ready")
        self._status_pill.setStyleSheet(status_pill_style("ready"))

        # Refresh tabs
        self._arch_tab.load()
        self._tasks_tab.load()
        self._sdd_tab.load()
        self._tests_tab.load()
        self._tabs.setCurrentIndex(1)

    def _on_gen_error(self, msg: str):
        self._progress.hide()
        self._progress_label.hide()
        QMessageBox.critical(self, "Generation Error", msg)

    def _approve_and_post(self):
        t = ticket_model.get_by_id(self._ticket_id)
        desc_doc = doc_model.get(self._ticket_id, "formatted_desc")
        if not desc_doc or not desc_doc.content:
            QMessageBox.warning(self, "Not Ready", "Generate content first.")
            return

        errors = []

        # Post description to Jira
        try:
            jira_client.update_description(t.jira_key, desc_doc.content)
        except Exception as e:
            errors.append(f"Jira description: {e}")

        # Create Confluence page with draw.io
        diagram = doc_model.get_diagram(self._ticket_id)
        if diagram and diagram["drawio_xml"]:
            try:
                html = confluence_client.build_drawio_page_html(f"{t.jira_key} Architecture", diagram["drawio_xml"])
                page = confluence_client.create_page(f"{t.jira_key} Architecture", html)
                doc_model.save_diagram(self._ticket_id, diagram["mermaid_src"], diagram["drawio_xml"], page["url"])
                jira_client.post_comment(t.jira_key, f"Architecture diagram: {page['url']}")
            except Exception as e:
                errors.append(f"Confluence: {e}")

        import datetime
        desc_doc.approved_at = datetime.datetime.now().isoformat()
        desc_doc.posted_at = desc_doc.approved_at
        doc_model.save(desc_doc)
        ticket_model.update_status(self._ticket_id, "posted")
        self._status_pill.setText("posted")
        self._status_pill.setStyleSheet(status_pill_style("posted"))

        if errors:
            QMessageBox.warning(self, "Partial Success", "Posted with errors:\n" + "\n".join(errors))
        else:
            QMessageBox.information(self, "Posted", f"✅ Posted {t.jira_key} to Jira and Confluence.")


def _mermaid_to_drawio(mermaid_src: str) -> str:
    """Wrap Mermaid source in a minimal draw.io XML envelope."""
    import xml.etree.ElementTree as ET
    root = ET.Element("mxGraphModel")
    root_cell = ET.SubElement(root, "root")
    ET.SubElement(root_cell, "mxCell", id="0")
    ET.SubElement(root_cell, "mxCell", id="1", parent="0")
    cell = ET.SubElement(root_cell, "mxCell", id="2", value=mermaid_src,
                         style="text;html=1;align=left;verticalAlign=top;", vertex="1", parent="1")
    ET.SubElement(cell, "mxGeometry", x="10", y="10", width="600", height="400", **{"as": "geometry"})
    return ET.tostring(root, encoding="unicode")
