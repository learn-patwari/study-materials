"""Tests for JiraAgent — all HTTP calls mocked."""
import pytest
import json
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Optional


@dataclass
class FakeSettings:
    jira_base_url: str = "https://test.atlassian.net"
    jira_user_email: str = "akshay@test.com"
    jira_api_token: str = "token123"
    jira_project_key: str = "PROJ"


def fake_memory():
    m = MagicMock()
    m.start_run.return_value = 1
    return m


def _make_issue(key="PROJ-1", issue_type="Task", priority="Medium", summary="Do something",
                components=None, labels=None):
    return {
        "key": key,
        "fields": {
            "summary": summary,
            "issuetype": {"name": issue_type},
            "priority": {"name": priority},
            "status": {"name": "In Progress"},
            "updated": "2024-01-15T10:00:00.000+0000",
            "components": [{"name": c} for c in (components or [])],
            "labels": labels or [],
            "description": {
                "type": "doc",
                "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": "Fix the login bug"}]}
                ],
            },
        },
    }


class TestJiraAgent:
    def _make_agent(self, issues):
        from agents.jira_agent import JiraAgent
        settings = FakeSettings()
        memory = fake_memory()
        agent = JiraAgent.__new__(JiraAgent)
        agent._base = settings.jira_base_url
        agent._auth = (settings.jira_user_email, settings.jira_api_token)
        agent._project = settings.jira_project_key
        agent._memory = memory

        import requests
        session = MagicMock(spec=requests.Session)
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"issues": issues, "total": len(issues)}
        session.get.return_value = mock_resp
        agent._session = session
        return agent

    def test_fetch_returns_tasks(self):
        agent = self._make_agent([
            _make_issue("PROJ-1", "Task", "High", "Fix auth"),
            _make_issue("PROJ-2", "Bug",  "Critical", "Login broken"),
        ])
        result = agent.fetch_my_tickets()
        assert result["total"] == 2
        assert len(result["tasks"]) == 2

    def test_bugs_extracted_to_bug_tickets(self):
        agent = self._make_agent([
            _make_issue("PROJ-1", "Task", "Medium", "Regular task"),
            _make_issue("PROJ-2", "Bug",  "Critical", "Crash on load"),
            _make_issue("PROJ-3", "Bug",  "High",     "Memory leak"),
        ])
        result = agent.fetch_my_tickets()
        assert len(result["bug_tickets"]) == 2
        keys = [b["key"] for b in result["bug_tickets"]]
        assert "PROJ-2" in keys
        assert "PROJ-3" in keys

    def test_task_shape(self):
        agent = self._make_agent([
            _make_issue("PROJ-5", "SRS", "High", "Define requirements",
                        components=["auth-service"], labels=["sprint-12"])
        ])
        result = agent.fetch_my_tickets()
        task = result["tasks"][0]
        assert task["key"] == "PROJ-5"
        assert task["type"] == "SRS"
        assert task["priority"] == "High"
        assert task["components"] == ["auth-service"]
        assert task["labels"] == ["sprint-12"]
        assert task["url"] == "https://test.atlassian.net/browse/PROJ-5"
        assert "description_snippet" in task

    def test_no_tickets_returns_empty(self):
        agent = self._make_agent([])
        result = agent.fetch_my_tickets()
        assert result["total"] == 0
        assert result["tasks"] == []
        assert result["bug_tickets"] == []

    def test_description_extraction(self):
        from agents.jira_agent import JiraAgent
        agent = JiraAgent.__new__(JiraAgent)
        adf = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [
                    {"type": "text", "text": "Hello "},
                    {"type": "text", "text": "world"},
                ]}
            ],
        }
        result = agent._extract_description(adf)
        assert "Hello" in result
        assert "world" in result

    def test_description_handles_none(self):
        from agents.jira_agent import JiraAgent
        agent = JiraAgent.__new__(JiraAgent)
        assert agent._extract_description(None) == ""
        assert agent._extract_description({}) == ""

    def test_memory_saved_on_success(self):
        agent = self._make_agent([_make_issue()])
        agent.fetch_my_tickets()
        agent._memory.set.assert_called()
        call_args = agent._memory.end_run.call_args
        assert call_args[0][0] == 1
        assert call_args[0][1] == "done"
        assert isinstance(call_args[0][2], str) and len(call_args[0][2]) > 0

    def test_graceful_on_http_error(self):
        from agents.jira_agent import JiraAgent
        settings = FakeSettings()
        memory = fake_memory()
        agent = JiraAgent.__new__(JiraAgent)
        agent._base = settings.jira_base_url
        agent._auth = (settings.jira_user_email, settings.jira_api_token)
        agent._project = settings.jira_project_key
        agent._memory = memory

        import requests
        session = MagicMock(spec=requests.Session)
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("401 Unauthorized")
        session.get.return_value = mock_resp
        agent._session = session

        result = agent.fetch_my_tickets()
        assert "error" in result
        assert "Jira" in result["error"]

    def test_misconfigured_raises_graceful(self):
        from utils.errors import ConfigError
        from agents.jira_agent import JiraAgent
        from dataclasses import dataclass

        @dataclass
        class BadSettings:
            jira_base_url = None
            jira_user_email = None
            jira_api_token = None
            jira_project_key = ""

        with pytest.raises(Exception):
            JiraAgent(BadSettings(), fake_memory())
