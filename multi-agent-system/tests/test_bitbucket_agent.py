"""Tests for BitbucketAgent — all HTTP calls mocked."""
import pytest
import json
from unittest.mock import MagicMock, call
from dataclasses import dataclass


@dataclass
class FakeSettings:
    bitbucket_base_url: str = "https://api.bitbucket.org/2.0"
    bitbucket_username: str = "akshay"
    bitbucket_app_password: str = "app-pass"
    bitbucket_workspace: str = "myteam"
    bitbucket_repos: list = None

    def __post_init__(self):
        if self.bitbucket_repos is None:
            self.bitbucket_repos = ["auth-service", "payment-api"]


def fake_memory():
    m = MagicMock()
    m.start_run.return_value = 1
    return m


def _make_pr(pr_id, title, author_uuid, reviewer_uuids=None):
    return {
        "id": pr_id,
        "title": title,
        "state": "OPEN",
        "author": {"uuid": author_uuid, "display_name": "Akshay"},
        "source": {"branch": {"name": f"feature/pr-{pr_id}"}},
        "destination": {"branch": {"name": "main"}},
        "reviewers": [{"uuid": u, "display_name": f"reviewer-{u}"} for u in (reviewer_uuids or [])],
        "links": {"html": {"href": f"https://bitbucket.org/myteam/repo/pull-requests/{pr_id}"}},
        "updated_on": "2024-01-15T10:00:00+00:00",
    }


def _make_agent(pr_data_by_repo=None, my_uuid="{me-uuid}"):
    from agents.bitbucket_agent import BitbucketAgent
    settings = FakeSettings()
    memory = fake_memory()
    agent = BitbucketAgent.__new__(BitbucketAgent)
    agent._base = settings.bitbucket_base_url
    agent._auth = (settings.bitbucket_username, settings.bitbucket_app_password)
    agent._workspace = settings.bitbucket_workspace
    agent._repos = settings.bitbucket_repos
    agent._memory = memory

    import requests
    session = MagicMock(spec=requests.Session)

    def mock_get(url, **kwargs):
        resp = MagicMock()
        resp.ok = True
        resp.status_code = 200
        resp.raise_for_status.return_value = None

        if url.endswith("/user"):
            resp.json.return_value = {"uuid": my_uuid}
        elif "/pullrequests" in url and "/src/" not in url:
            repo_slug = url.split("/repositories/myteam/")[1].split("/")[0]
            prs = (pr_data_by_repo or {}).get(repo_slug, [])
            resp.json.return_value = {"values": prs}
        elif "/src/" in url:
            # Simulate directory listing
            resp.json.return_value = {
                "values": [
                    {"path": "src/auth/token_handler.py", "type": "commit_file"},
                    {"path": "src/auth/login.py", "type": "commit_file"},
                ]
            }
            resp.text = "def refresh_token():\n    pass\n" * 30
        return resp

    session.get.side_effect = mock_get
    agent._session = session
    return agent


class TestFetchOpenPRs:
    def test_authored_prs_captured(self):
        prs = {"auth-service": [_make_pr(1, "Fix login", "{me-uuid}")]}
        agent = _make_agent(prs)
        result = agent.fetch_open_prs()
        assert "auth-service" in result["by_repo"]
        assert len(result["by_repo"]["auth-service"]["authored"]) == 1

    def test_review_requested_captured(self):
        prs = {"auth-service": [_make_pr(2, "Review me", "{other-uuid}", reviewer_uuids=["{me-uuid}"])]}
        agent = _make_agent(prs)
        result = agent.fetch_open_prs()
        assert len(result["by_repo"]["auth-service"]["review_requested"]) == 1

    def test_pr_not_mine_excluded(self):
        prs = {"auth-service": [_make_pr(3, "Someone else's PR", "{other-uuid}")]}
        agent = _make_agent(prs)
        result = agent.fetch_open_prs()
        assert len(result["by_repo"]["auth-service"]["authored"]) == 0
        assert len(result["by_repo"]["auth-service"]["review_requested"]) == 0

    def test_multiple_repos(self):
        prs = {
            "auth-service": [_make_pr(1, "Auth fix", "{me-uuid}")],
            "payment-api":  [_make_pr(2, "Payment fix", "{me-uuid}")],
        }
        agent = _make_agent(prs)
        result = agent.fetch_open_prs()
        assert "auth-service" in result["by_repo"]
        assert "payment-api" in result["by_repo"]

    def test_pr_shape(self):
        prs = {"auth-service": [_make_pr(42, "Implement feature X", "{me-uuid}")]}
        agent = _make_agent(prs)
        result = agent.fetch_open_prs()
        pr = result["by_repo"]["auth-service"]["authored"][0]
        assert pr["id"] == 42
        assert pr["title"] == "Implement feature X"
        assert pr["repo"] == "auth-service"
        assert "branch" in pr
        assert "url" in pr

    def test_empty_repos_returns_empty_by_repo(self):
        agent = _make_agent({})
        result = agent.fetch_open_prs()
        assert result["by_repo"]["auth-service"]["authored"] == []
        assert result["by_repo"]["payment-api"]["authored"] == []

    def test_memory_saved(self):
        agent = _make_agent({})
        agent.fetch_open_prs()
        agent._memory.set.assert_called()

    def test_graceful_on_error(self):
        from agents.bitbucket_agent import BitbucketAgent
        settings = FakeSettings()
        memory = fake_memory()
        agent = BitbucketAgent.__new__(BitbucketAgent)
        agent._base = settings.bitbucket_base_url
        agent._auth = (settings.bitbucket_username, settings.bitbucket_app_password)
        agent._workspace = settings.bitbucket_workspace
        agent._repos = settings.bitbucket_repos
        agent._memory = memory

        import requests
        session = MagicMock(spec=requests.Session)
        session.get.side_effect = Exception("Network error")
        agent._session = session

        result = agent.fetch_open_prs()
        assert "error" in result


class TestInspectRepoForBug:
    def test_returns_found_files(self):
        agent = _make_agent()
        result = agent.inspect_repo_for_bug("auth-service", ["token", "login"])
        assert result["repo"] == "auth-service"
        assert isinstance(result["found_files"], list)

    def test_search_terms_used(self):
        agent = _make_agent()
        result = agent.inspect_repo_for_bug("auth-service", ["token"])
        # Files with "token" in their path should be found
        paths = [f["path"] for f in result["found_files"]]
        assert any("token" in p for p in paths)

    def test_max_3_files_returned(self):
        agent = _make_agent()
        result = agent.inspect_repo_for_bug("auth-service", ["auth", "login", "token"])
        assert len(result["found_files"]) <= 3

    def test_content_snippet_returned(self):
        agent = _make_agent()
        result = agent.inspect_repo_for_bug("auth-service", ["token"])
        if result["found_files"]:
            assert "content_snippet" in result["found_files"][0]

    def test_graceful_on_error(self):
        from agents.bitbucket_agent import BitbucketAgent
        settings = FakeSettings()
        memory = fake_memory()
        agent = BitbucketAgent.__new__(BitbucketAgent)
        agent._base = settings.bitbucket_base_url
        agent._auth = (settings.bitbucket_username, settings.bitbucket_app_password)
        agent._workspace = settings.bitbucket_workspace
        agent._repos = settings.bitbucket_repos
        agent._memory = memory

        import requests
        session = MagicMock(spec=requests.Session)
        session.get.side_effect = Exception("Timeout")
        agent._session = session

        result = agent.inspect_repo_for_bug("some-repo", ["token"])
        assert "error" in result
