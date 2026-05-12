"""
tests/unit/test_services.py — Unit tests for service layer and graph routing.

These tests use mocks and fixtures — no live Google APIs or LLM calls.
Run with: pytest tests/unit/ -v
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from tests.fixtures.data import SAMPLE_NOTES, SAMPLE_AGENDAS, SAMPLE_EMAILS


# ── google_docs: tab parsing ───────────────────────────────────────────────────

class TestTabParsing:
    """Test the _parse_tab_date and _collect_meeting_tabs helpers."""

    def test_parses_mm_dd_yy(self):
        from services.google_docs import _parse_tab_date
        result = _parse_tab_date("03/25/26")
        assert result == datetime(2026, 3, 25)

    def test_parses_mm_dd_yyyy(self):
        from services.google_docs import _parse_tab_date
        result = _parse_tab_date("03/25/2026")
        assert result == datetime(2026, 3, 25)

    def test_parses_iso_date(self):
        from services.google_docs import _parse_tab_date
        result = _parse_tab_date("2026-03-25")
        assert result == datetime(2026, 3, 25)

    def test_returns_none_for_unparseable(self):
        from services.google_docs import _parse_tab_date
        assert _parse_tab_date("Spring 2026") is None
        assert _parse_tab_date("") is None

    def test_collect_returns_most_recent_first(self):
        from services.google_docs import _collect_meeting_tabs

        def _make_tab(title: str) -> dict:
            return {
                "tabProperties": {"title": title},
                "childTabs": [],
                "documentTab": {"body": {"content": []}},
            }

        tabs = [_make_tab("01/28/26"), _make_tab("03/25/26"), _make_tab("02/24/26")]
        result = _collect_meeting_tabs(tabs)
        dates = [t["date"] for t in result]
        assert dates == sorted(dates, reverse=True)

    def test_skips_year_tabs_with_children(self):
        """Year-level tabs (which have children) should not appear as meeting tabs."""
        from services.google_docs import _collect_meeting_tabs

        year_tab = {
            "tabProperties": {"title": "2026"},
            "childTabs": [
                {
                    "tabProperties": {"title": "03/25/26"},
                    "childTabs": [],
                    "documentTab": {"body": {"content": []}},
                }
            ],
        }
        result = _collect_meeting_tabs([year_tab])
        titles = [t["title"] for t in result]
        assert "2026" not in titles
        assert "03/25/26" in titles


# ── llm factory ───────────────────────────────────────────────────────────────

class TestLLMFactory:

    def test_raises_on_unknown_backend(self, monkeypatch):
        monkeypatch.setenv("LLM_BACKEND", "gpt-99")
        from services import llm
        import importlib
        importlib.reload(llm)
        with pytest.raises(ValueError, match="Unknown LLM_BACKEND"):
            llm.get_llm()

    def test_returns_anthropic_model(self, monkeypatch):
        monkeypatch.setenv("LLM_BACKEND", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        from services import llm
        import importlib
        importlib.reload(llm)
        with patch("langchain_anthropic.ChatAnthropic.__init__", return_value=None):
            model = llm.get_llm()
            assert model is not None

    def test_returns_ollama_model(self, monkeypatch):
        monkeypatch.setenv("LLM_BACKEND", "ollama")
        from services import llm
        import importlib
        importlib.reload(llm)
        with patch("langchain_ollama.ChatOllama.__init__", return_value=None):
            model = llm.get_llm()
            assert model is not None


# ── graph routing ──────────────────────────────────────────────────────────────

class TestGraphRouting:
    """Test the _should_revise conditional edge without running the full graph."""

    def _state(self, issues, revision_count, max_revisions="3"):
        import os
        os.environ["MAX_REVISIONS"] = max_revisions
        return {
            "review_issues": issues,
            "revision_count": revision_count,
        }

    def test_routes_to_save_when_no_issues(self):
        from agent.graph import _should_revise
        assert _should_revise(self._state([], 1)) == "save"

    def test_routes_to_revise_when_issues_and_under_cap(self):
        from agent.graph import _should_revise
        assert _should_revise(self._state(["Fix heading"], 1)) == "revise"

    def test_routes_to_save_when_max_revisions_reached(self):
        from agent.graph import _should_revise
        assert _should_revise(self._state(["Fix heading"], 3, "3")) == "save"

    def test_routes_to_save_exactly_at_cap(self):
        from agent.graph import _should_revise
        assert _should_revise(self._state(["Still broken"], 3, "3")) == "save"


# ── gmail query builder ───────────────────────────────────────────────────────

class TestGmailQueryBuilder:

    def test_includes_label(self, monkeypatch):
        monkeypatch.setenv("GMAIL_LABEL", "committee")
        monkeypatch.setenv("COMMITTEE_EMAILS", "")
        from services import gmail
        import importlib
        importlib.reload(gmail)
        query = gmail._build_query("2026/03/01")
        assert "label:committee" in query
        assert "after:2026/03/01" in query

    def test_includes_participant_filter(self, monkeypatch):
        monkeypatch.setenv("GMAIL_LABEL", "")
        monkeypatch.setenv("COMMITTEE_EMAILS", "jane@example.com,alex@example.com")
        from services import gmail
        import importlib
        importlib.reload(gmail)
        query = gmail._build_query("2026/03/01")
        assert "from:jane@example.com" in query
        assert "from:alex@example.com" in query

    def test_combines_both_filters(self, monkeypatch):
        monkeypatch.setenv("GMAIL_LABEL", "committee")
        monkeypatch.setenv("COMMITTEE_EMAILS", "jane@example.com")
        from services import gmail
        import importlib
        importlib.reload(gmail)
        query = gmail._build_query("2026/03/01")
        assert "label:committee" in query
        assert "from:jane@example.com" in query


# ── FastAPI endpoints ─────────────────────────────────────────────────────────

class TestAPIEndpoints:

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from main import app
        return TestClient(app)

    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_generate_returns_job_id(self, client):
        with patch("main._run_pipeline"):
            response = client.post(
                "/agenda/generate",
                json={"meeting_date": "April 22, 2026"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"

    def test_status_404_for_unknown_job(self, client):
        response = client.get("/agenda/status/nonexistent-id")
        assert response.status_code == 404

    def test_status_returns_job_state(self, client):
        from main import _jobs
        fake_id = "test-job-123"
        _jobs[fake_id] = {"status": "complete", "doc_url": "https://docs.google.com/d/x", "error": None}
        response = client.get(f"/agenda/status/{fake_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "complete"
        assert data["doc_url"] is not None
