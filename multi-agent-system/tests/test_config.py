"""Tests for config loading."""
import pytest
import os
from unittest.mock import patch
from utils.errors import ConfigError


class TestLoadSettings:
    def _env(self, **overrides):
        base = {
            "LLM_BASE_URL": "http://localhost:11434/v1",
            "LLM_API_KEY": "test-key",
            "LLM_MODEL": "llama3",
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_USER_EMAIL": "akshay@test.com",
            "JIRA_API_TOKEN": "jira-token",
            "JIRA_PROJECT_KEY": "PROJ",
            "BITBUCKET_USERNAME": "akshay",
            "BITBUCKET_APP_PASSWORD": "bb-pass",
            "BITBUCKET_WORKSPACE": "myteam",
            "BITBUCKET_REPOS": "auth-service,payment-api",
            "BUG_REPO_MAP": "auth-service:auth-api,payment:pay-svc",
            "CONFLUENCE_BASE_URL": "https://test.atlassian.net",
            "CONFLUENCE_USERNAME": "akshay@test.com",
            "CONFLUENCE_PASSWORD": "conf-pass",
        }
        base.update(overrides)
        return base

    def test_loads_all_settings(self):
        with patch.dict(os.environ, self._env(), clear=True):
            from importlib import reload
            import utils.config as cfg
            reload(cfg)
            s = cfg.load_settings()
        assert s.llm_base_url == "http://localhost:11434/v1"
        assert s.llm_model == "llama3"
        assert s.jira_base_url == "https://test.atlassian.net"
        assert s.bitbucket_repos == ["auth-service", "payment-api"]
        assert s.bug_repo_map == {"auth-service": "auth-api", "payment": "pay-svc"}

    def test_raises_config_error_missing_llm(self):
        env = {"LLM_BASE_URL": "", "LLM_API_KEY": "", "LLM_MODEL": ""}
        with patch.dict(os.environ, env, clear=True):
            from importlib import reload
            import utils.config as cfg
            reload(cfg)
            with pytest.raises(ConfigError):
                cfg.load_settings()

    def test_optional_agents_can_be_missing(self):
        minimal = {
            "LLM_BASE_URL": "http://localhost/v1",
            "LLM_API_KEY": "key",
            "LLM_MODEL": "model",
        }
        with patch.dict(os.environ, minimal, clear=True):
            from importlib import reload
            import utils.config as cfg
            reload(cfg)
            s = cfg.load_settings()
        assert s.jira_base_url is None
        assert s.bitbucket_username is None
        assert s.confluence_password is None

    def test_parse_bug_repo_map(self):
        from utils.config import _parse_bug_repo_map
        result = _parse_bug_repo_map("auth:auth-api,payment:pay-svc,frontend:web-app")
        assert result == {"auth": "auth-api", "payment": "pay-svc", "frontend": "web-app"}

    def test_parse_bug_repo_map_empty(self):
        from utils.config import _parse_bug_repo_map
        assert _parse_bug_repo_map("") == {}

    def test_parse_repos(self):
        from utils.config import _parse_repos
        result = _parse_repos("auth-service, payment-api , web-app")
        assert result == ["auth-service", "payment-api", "web-app"]

    def test_parse_repos_empty(self):
        from utils.config import _parse_repos
        assert _parse_repos("") == []

    def test_memory_db_path_expanded(self):
        env = self._env(MEMORY_DB_PATH="~/.pattu/memory.db")
        with patch.dict(os.environ, env, clear=True):
            from importlib import reload
            import utils.config as cfg
            reload(cfg)
            s = cfg.load_settings()
        assert not s.memory_db_path.startswith("~")
        assert "pattu" in s.memory_db_path
