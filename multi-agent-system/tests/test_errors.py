"""Tests for AgentError and @graceful decorator."""
import pytest
from utils.errors import AgentError, graceful


class TestGracefulDecorator:
    def test_passes_through_success(self):
        @graceful("TestAgent")
        def good_fn():
            return {"data": 42}

        result = good_fn()
        assert result == {"data": 42}

    def test_catches_exception_returns_error_dict(self):
        @graceful("TestAgent")
        def bad_fn():
            raise ConnectionError("refused")

        result = bad_fn()
        assert "error" in result
        assert "TestAgent" in result["error"]
        assert "refused" in result["error"]

    def test_catches_agent_error(self):
        @graceful("Jira")
        def misconfigured():
            raise AgentError("JIRA_API_TOKEN not set")

        result = misconfigured()
        assert "error" in result
        assert "Jira" in result["error"]

    def test_catches_any_exception_type(self):
        @graceful("Bitbucket")
        def raises_value_error():
            raise ValueError("bad input")

        result = raises_value_error()
        assert "error" in result

    def test_preserves_function_name(self):
        @graceful("X")
        def my_function():
            return {}

        assert my_function.__name__ == "my_function"

    def test_passes_args_through(self):
        @graceful("X")
        def fn_with_args(a, b, keyword=None):
            return {"a": a, "b": b, "kw": keyword}

        result = fn_with_args(1, 2, keyword="test")
        assert result == {"a": 1, "b": 2, "kw": "test"}

    def test_works_on_method(self):
        class MyAgent:
            @graceful("MyAgent")
            def fetch(self):
                raise RuntimeError("network error")

        agent = MyAgent()
        result = agent.fetch()
        assert "error" in result
        assert "MyAgent" in result["error"]
