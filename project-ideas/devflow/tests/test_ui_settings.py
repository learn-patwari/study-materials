import pytest
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication
from ui.settings_dialog import SettingsDialog
import db.database as database


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_settings_dialog_opens(qapp):
    dlg = SettingsDialog()
    assert dlg is not None
    dlg.close()


def test_settings_dialog_has_sections(qapp):
    dlg = SettingsDialog()
    sections = [dlg._nav.item(i).text() for i in range(dlg._nav.count())]
    assert "Jira" in sections
    assert "AI" in sections
    assert "Confluence" in sections
    dlg.close()


def test_settings_save_persists(qapp):
    dlg = SettingsDialog()
    # Navigate to AI section and set a value
    for i in range(dlg._nav.count()):
        if dlg._nav.item(i).text() == "AI":
            dlg._nav.setCurrentRow(i)
            break
    # Set model field
    dlg._ai_model.setText("gpt-4o")
    dlg._save()
    dlg.close()
    assert database.get_setting("ai_model") == "gpt-4o"


def test_settings_loads_saved_values(qapp):
    database.set_setting("ai_base_url", "https://api.example.com")
    dlg = SettingsDialog()
    for i in range(dlg._nav.count()):
        if dlg._nav.item(i).text() == "AI":
            dlg._nav.setCurrentRow(i)
            break
    assert dlg._ai_base_url.text() == "https://api.example.com"
    dlg.close()
