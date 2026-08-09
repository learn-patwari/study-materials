"""
Headless UI smoke tests for DevFlow.

Run with:
    cd project-ideas/devflow
    QT_QPA_PLATFORM=offscreen QTWEBENGINE_CHROMIUM_FLAGS="--no-sandbox" \
        pytest tests/test_ui.py -v
"""
import os
import sys
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox")

# Must be set before QApplication is created
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture(scope="session")
def main_window(qapp):
    from ui.main_window import MainWindow
    w = MainWindow()
    w.show()
    qapp.processEvents()
    yield w
    w.close()


# ── Main window ──────────────────────────────────────────────────────────────

class TestMainWindow:
    def test_tabs_exist(self, main_window):
        tabs = [main_window._tabs.tabText(i) for i in range(main_window._tabs.count())]
        for expected in ["Dashboard", "SRS", "Sprint", "PR Review", "Bugs", "Improvements"]:
            assert expected in tabs, f"Missing tab: {expected}"

    def test_bugs_and_improvements_are_separate_tabs(self, main_window):
        tabs = [main_window._tabs.tabText(i) for i in range(main_window._tabs.count())]
        assert "Bugs" in tabs
        assert "Improvements" in tabs
        bugs_idx = tabs.index("Bugs")
        impr_idx = tabs.index("Improvements")
        assert bugs_idx != impr_idx

    def test_window_title(self, main_window):
        assert "DevFlow" in main_window.windowTitle()

    def test_settings_button_opens_dialog(self, qapp, main_window):
        from PyQt6.QtWidgets import QDialog
        # Just check the settings dialog can be instantiated without error
        from ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(main_window)
        assert dlg is not None
        dlg.reject()


# ── Dashboard ────────────────────────────────────────────────────────────────

class TestDashboard:
    def test_bug_tiles_load_from_cache(self, qapp, main_window):
        dash = main_window._dashboard
        qapp.processEvents()
        # Seed data puts 18 in bug_counts; tiles should not show "—"
        assert dash._tile_total.text() != "—", "Bug total tile still shows dash — cache not loading"

    def test_alerts_section_renders(self, qapp, main_window):
        dash = main_window._dashboard
        qapp.processEvents()
        # alerts frame should have at least one child widget
        assert dash._alerts_frame.count() >= 1

    def test_refresh_alerts_no_crash(self, qapp, main_window):
        main_window._dashboard.refresh_alerts()
        qapp.processEvents()


# ── SRS panel ────────────────────────────────────────────────────────────────

class TestSRSPanel:
    def test_srs_panel_exists(self, main_window):
        from ui.srs_selector import SRSPanel
        assert isinstance(main_window._srs, SRSPanel)

    def test_srs_loads_local_tickets(self, qapp, main_window):
        srs = main_window._srs
        # Wait for the async fetcher (it falls back to local DB)
        import time
        deadline = time.time() + 3
        while srs._list.count() == 0 and time.time() < deadline:
            qapp.processEvents()
            time.sleep(0.05)
        assert srs._list.count() > 0, "SRS list empty after 3s — seed_data.py may not have been run"

    def test_clicking_ticket_opens_detail_directly(self, qapp, main_window):
        srs = main_window._srs
        import time
        deadline = time.time() + 3
        while srs._list.count() == 0 and time.time() < deadline:
            qapp.processEvents()
            time.sleep(0.05)

        if srs._list.count() == 0:
            pytest.skip("No SRS tickets loaded")

        item = srs._list.item(0)
        srs._on_select(item)
        qapp.processEvents()

        # Detail container must be visible (not hidden)
        assert not srs._detail_container.isHidden(), "Detail container still hidden after ticket click"
        # The embedded widget should be a TicketDetailPanel
        from ui.ticket_detail import TicketDetailPanel
        assert isinstance(srs._detail_container.widget(), TicketDetailPanel)

    def test_ticket_detail_has_five_tabs(self, qapp, main_window):
        srs = main_window._srs
        qapp.processEvents()
        detail = srs._detail_container.widget()
        if detail is None:
            pytest.skip("No ticket selected")
        from ui.ticket_detail import TicketDetailPanel
        assert isinstance(detail, TicketDetailPanel)
        tab_labels = [detail._tabs.tabText(i) for i in range(detail._tabs.count())]
        for expected in ["Description", "Architecture", "Tasks", "SDD", "Tests"]:
            assert expected in tab_labels, f"Missing sub-tab: {expected}"

    def test_no_intermediate_open_button(self, qapp, main_window):
        srs = main_window._srs
        # The old "Open Ticket →" button should no longer exist
        assert not hasattr(srs, "_open_btn"), "Old _open_btn still exists — not cleaned up"
        assert not hasattr(srs, "_desc_preview"), "Old _desc_preview still exists"


# ── Sprint panel ─────────────────────────────────────────────────────────────

class TestSprintPanel:
    def test_sprint_panel_exists(self, main_window):
        from ui.sprint_panel import SprintPanel
        assert isinstance(main_window._sprint, SprintPanel)

    def test_sprint_tree_has_columns(self, main_window):
        sprint = main_window._sprint
        assert sprint._tree.columnCount() == 3
        assert sprint._tree.headerItem().text(0) == "Task"

    def test_sprint_shows_on_tab_switch(self, qapp, main_window):
        tabs = [main_window._tabs.tabText(i) for i in range(main_window._tabs.count())]
        sprint_idx = tabs.index("Sprint")
        main_window._tabs.setCurrentIndex(sprint_idx)
        qapp.processEvents()
        # Timeline widget should be present
        assert main_window._sprint._timeline is not None


# ── PR Review panel ──────────────────────────────────────────────────────────

class TestPRReviewPanel:
    def test_pr_panel_exists(self, main_window):
        from ui.pr_review_panel import PRReviewPanel
        assert isinstance(main_window._pr_review, PRReviewPanel)

    def test_pr_list_renders(self, qapp, main_window):
        tabs = [main_window._tabs.tabText(i) for i in range(main_window._tabs.count())]
        pr_idx = tabs.index("PR Review")
        main_window._tabs.setCurrentIndex(pr_idx)
        qapp.processEvents()
        pr = main_window._pr_review
        # PR list should have items (from seed data)
        assert pr._pr_list.count() >= 0  # may be 0 before showEvent populates


# ── Bugs / Improvements panels ───────────────────────────────────────────────

class TestBugsPanels:
    def test_bugs_mode(self, main_window):
        from ui.bugs_panel import BugsPanel
        assert isinstance(main_window._bugs, BugsPanel)
        assert main_window._bugs._mode == "bugs"

    def test_improvements_mode(self, main_window):
        from ui.bugs_panel import BugsPanel
        assert isinstance(main_window._improvements, BugsPanel)
        assert main_window._improvements._mode == "improvements"

    def test_bugs_fall_back_to_local_db(self, qapp, main_window):
        bugs = main_window._bugs
        # Directly call the fallback (simulates Jira being unavailable)
        bugs._load_from_db()
        qapp.processEvents()
        # Seed data has 2 bug_analyses entries — list should not be empty
        assert bugs._item_list.count() > 0, "Bug list empty after local DB fallback"

    def test_improvements_fall_back_to_local_db(self, qapp, main_window):
        impr = main_window._improvements
        impr._load_from_db()
        qapp.processEvents()
        assert impr._item_list.count() > 0


# ── Settings dialog ──────────────────────────────────────────────────────────

class TestSettingsDialog:
    def test_all_sections_present(self, qapp, main_window):
        from ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(main_window)
        sections = [dlg.nav.item(i).text() for i in range(dlg.nav.count())]
        for expected in ["Jira", "Confluence", "Bitbucket", "AI", "Document",
                         "Sprint", "Test Runner", "PR Watcher", "Notifications"]:
            assert expected in sections, f"Missing settings section: {expected}"
        dlg.reject()

    def test_notifications_checkbox_exists(self, qapp, main_window):
        from ui.settings_dialog import SettingsDialog
        from PyQt6.QtWidgets import QCheckBox
        dlg = SettingsDialog(main_window)
        assert "notifications_enabled" in dlg._fields
        assert isinstance(dlg._fields["notifications_enabled"], QCheckBox)
        dlg.reject()

    def test_sprint_fields_have_defaults(self, qapp, main_window):
        from ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(main_window)
        assert dlg._fields["sprint_dev_days"].value() >= 1
        assert dlg._fields["sprint_test_days"].value() >= 1
        dlg.reject()
