"""Tests for ConfluenceAgent — all HTTP calls mocked."""
import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass


@dataclass
class FakeSettings:
    confluence_base_url: str = "https://test.atlassian.net"
    confluence_username: str = "akshay@test.com"
    confluence_password: str = "conf-pass"


def fake_memory():
    m = MagicMock()
    m.get.return_value = None
    m.start_run.return_value = 1
    return m


def _make_agent(space_key="~akshay", page_resp=None):
    from agents.confluence_agent import ConfluenceAgent
    settings = FakeSettings()
    memory = fake_memory()
    agent = ConfluenceAgent.__new__(ConfluenceAgent)
    agent._base = settings.confluence_base_url.rstrip("/") + "/wiki/rest/api"
    agent._auth = (settings.confluence_username, settings.confluence_password)
    agent._memory = memory
    agent._space_key = space_key

    import requests
    session = MagicMock(spec=requests.Session)

    def mock_get(url, **kwargs):
        resp = MagicMock()
        resp.ok = True
        resp.raise_for_status.return_value = None
        if "/space" in url:
            resp.json.return_value = {"results": [{"key": space_key, "name": "Akshay Personal"}]}
        elif "/content" in url:
            resp.json.return_value = {"results": [
                {"id": "1001", "title": "My Notes", "_links": {"webui": "/wiki/spaces/~akshay/pages/1001"}},
            ]}
        return resp

    def mock_post(url, **kwargs):
        resp = MagicMock()
        resp.ok = True
        resp.raise_for_status.return_value = None
        resp.json.return_value = {
            "id": "9999",
            "title": kwargs.get("json", {}).get("title", "Untitled"),
            "_links": {"webui": f"/wiki/spaces/{space_key}/pages/9999"},
        }
        return resp

    session.get.side_effect = mock_get
    session.post.side_effect = mock_post
    agent._session = session
    return agent


class TestCreatePage:
    def test_creates_page_returns_id(self):
        agent = _make_agent()
        result = agent.create_page("Bug Report - PROJ-42", "## Summary\nLogin is broken")
        assert result["page_id"] == "9999"
        assert "title" in result
        assert "url" in result
        assert "space_key" in result

    def test_post_called_with_correct_structure(self):
        agent = _make_agent(space_key="~akshay")
        agent.create_page("My Page", "Content here")
        call_kwargs = agent._session.post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["type"] == "page"
        assert payload["space"]["key"] == "~akshay"
        assert "storage" in payload["body"]

    def test_saves_to_memory(self):
        agent = _make_agent()
        agent.create_page("Test Page", "body")
        agent._memory.set.assert_called()

    def test_graceful_on_http_error(self):
        agent = _make_agent()
        agent._session.post.side_effect = Exception("403 Forbidden")
        result = agent.create_page("Test", "body")
        assert "error" in result

    def test_markdown_to_storage_headers(self):
        from agents.confluence_agent import ConfluenceAgent
        agent = ConfluenceAgent.__new__(ConfluenceAgent)
        html = agent._markdown_to_storage("# Title\n## Sub\n### Sub-sub")
        assert "<h1>Title</h1>" in html
        assert "<h2>Sub</h2>" in html
        assert "<h3>Sub-sub</h3>" in html

    def test_markdown_to_storage_bold(self):
        from agents.confluence_agent import ConfluenceAgent
        agent = ConfluenceAgent.__new__(ConfluenceAgent)
        html = agent._markdown_to_storage("This is **important** text")
        assert "<strong>important</strong>" in html

    def test_markdown_to_storage_list(self):
        from agents.confluence_agent import ConfluenceAgent
        agent = ConfluenceAgent.__new__(ConfluenceAgent)
        html = agent._markdown_to_storage("- Item 1\n- Item 2")
        assert "<li>Item 1</li>" in html
        assert "<li>Item 2</li>" in html


class TestListPages:
    def test_returns_page_list(self):
        agent = _make_agent()
        result = agent.list_my_pages()
        assert "pages" in result
        assert isinstance(result["pages"], list)

    def test_page_shape(self):
        agent = _make_agent()
        result = agent.list_my_pages()
        if result["pages"]:
            page = result["pages"][0]
            assert "id" in page
            assert "title" in page
            assert "url" in page

    def test_graceful_on_error(self):
        agent = _make_agent()
        agent._session.get.side_effect = Exception("Connection timeout")
        result = agent.list_my_pages()
        assert "error" in result


class TestGetMySpace:
    def test_returns_space_key(self):
        from agents.confluence_agent import ConfluenceAgent
        settings = FakeSettings()
        memory = fake_memory()
        agent = ConfluenceAgent.__new__(ConfluenceAgent)
        agent._base = settings.confluence_base_url + "/wiki/rest/api"
        agent._auth = (settings.confluence_username, settings.confluence_password)
        agent._memory = memory
        agent._space_key = None

        import requests
        session = MagicMock(spec=requests.Session)
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"results": [{"key": "~akshay123"}]}
        session.get.return_value = resp
        agent._session = session

        key = agent.get_my_space()
        assert key == "~akshay123"
        agent._memory.set.assert_called_with("confluence.personal_space_key", "~akshay123", "confluence")

    def test_uses_cached_space_key(self):
        from agents.confluence_agent import ConfluenceAgent
        settings = FakeSettings()
        memory = fake_memory()
        memory.get.return_value = "~cached-key"
        agent = ConfluenceAgent.__new__(ConfluenceAgent)
        agent._base = settings.confluence_base_url + "/wiki/rest/api"
        agent._auth = (settings.confluence_username, settings.confluence_password)
        agent._memory = memory
        agent._space_key = None

        import requests
        session = MagicMock(spec=requests.Session)
        agent._session = session

        key = agent.get_my_space()
        assert key == "~cached-key"
        session.get.assert_not_called()
