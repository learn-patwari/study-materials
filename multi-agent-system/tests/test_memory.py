"""Tests for SQLiteMemory — runs fully in-memory, no external deps."""
import pytest
import tempfile
import os
from core.memory import SQLiteMemory


@pytest.fixture
def mem(tmp_path):
    db = str(tmp_path / "test.db")
    m = SQLiteMemory(db)
    yield m
    m.close()


class TestConversationHistory:
    def test_save_and_retrieve(self, mem):
        mem.save_message("sess1", "user", "Hello Pattu", "pattu")
        mem.save_message("sess1", "assistant", "Hi Akshay!", "pattu")
        history = mem.get_history("sess1")
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello Pattu"
        assert history[1]["role"] == "assistant"

    def test_session_isolation(self, mem):
        mem.save_message("sess1", "user", "From session 1", "pattu")
        mem.save_message("sess2", "user", "From session 2", "pattu")
        assert len(mem.get_history("sess1")) == 1
        assert len(mem.get_history("sess2")) == 1

    def test_limit_respected(self, mem):
        for i in range(20):
            mem.save_message("sess", "user", f"msg {i}", "pattu")
        history = mem.get_history("sess", limit=5)
        assert len(history) == 5
        # Should return the most recent 5
        assert history[-1]["content"] == "msg 19"

    def test_empty_session(self, mem):
        assert mem.get_history("nonexistent") == []

    def test_dict_content_serialized(self, mem):
        mem.save_message("sess", "tool", {"result": 42}, "jira")
        history = mem.get_history("sess")
        assert len(history) == 1


class TestKeyValueStore:
    def test_set_and_get(self, mem):
        mem.set("jira.last_fetch", "2024-01-01T10:00:00", "jira")
        val = mem.get("jira.last_fetch")
        assert val == "2024-01-01T10:00:00"

    def test_missing_key_returns_default(self, mem):
        assert mem.get("nonexistent") is None
        assert mem.get("nonexistent", "fallback") == "fallback"

    def test_overwrite(self, mem):
        mem.set("key", "old", "jira")
        mem.set("key", "new", "jira")
        assert mem.get("key") == "new"

    def test_complex_value(self, mem):
        tickets = [{"key": "PROJ-1", "summary": "Bug fix", "type": "Bug"}]
        mem.set("jira.last_tickets", tickets, "jira")
        result = mem.get("jira.last_tickets")
        assert isinstance(result, list)
        assert result[0]["key"] == "PROJ-1"

    def test_get_by_agent(self, mem):
        mem.set("jira.key1", "val1", "jira")
        mem.set("jira.key2", "val2", "jira")
        mem.set("bb.key1", "val3", "bitbucket")
        jira_data = mem.get_all_by_agent("jira")
        assert len(jira_data) == 2
        assert "jira.key1" in jira_data

    def test_updated_at_set(self, mem):
        mem.set("some.key", "value", "confluence")
        ts = mem.get_updated_at("some.key")
        assert ts is not None


class TestAgentRunLog:
    def test_start_and_end_run(self, mem):
        run_id = mem.start_run("jira")
        assert isinstance(run_id, int)
        mem.end_run(run_id, "done", "Fetched 5 tickets")
        runs = mem.recent_runs(limit=1)
        assert len(runs) == 1
        assert runs[0]["status"] == "done"
        assert runs[0]["summary"] == "Fetched 5 tickets"
        assert runs[0]["ended_at"] is not None

    def test_error_run(self, mem):
        run_id = mem.start_run("bitbucket")
        mem.end_run(run_id, "error", "Connection refused")
        runs = mem.recent_runs()
        assert runs[0]["status"] == "error"

    def test_recent_runs_order(self, mem):
        for agent in ("jira", "bitbucket", "confluence"):
            rid = mem.start_run(agent)
            mem.end_run(rid, "done", f"{agent} ok")
        runs = mem.recent_runs(limit=3)
        assert runs[0]["agent_name"] == "confluence"  # most recent first

    def test_multiple_agents_independent(self, mem):
        r1 = mem.start_run("jira")
        r2 = mem.start_run("bitbucket")
        mem.end_run(r1, "done", "jira done")
        mem.end_run(r2, "error", "bb error")
        runs = mem.recent_runs()
        statuses = {r["agent_name"]: r["status"] for r in runs}
        assert statuses["jira"] == "done"
        assert statuses["bitbucket"] == "error"
