"""
tests/integration/test_pipeline.py — Integration tests against real Google APIs.

These tests require valid credentials and the env vars set in .env.
They are intentionally skipped in CI unless the INTEGRATION_TESTS env var is set.

Run locally with:
  INTEGRATION_TESTS=1 pytest tests/integration/ -v -s

IMPORTANT: These tests read real data but never write to Google Drive.
The save_agenda node is mocked out to prevent accidental doc creation.
"""

import os
import pytest
from unittest.mock import patch

#INTEGRATION_TESTS env var is intentionally a run-time flag to avoid accidentally running these against real APIs.
#the integration test can be run via >>INTEGRATION_TESTS=1 pytest tests/integration/ -v -s
pytestmark = pytest.mark.skipif(
    not os.getenv("INTEGRATION_TESTS"),
    reason="Set INTEGRATION_TESTS=1 to run integration tests",
)


class TestGoogleDocsFetching:

    def test_fetch_meeting_notes_returns_list(self):
        from services.google_docs import fetch_meeting_notes
        notes = fetch_meeting_notes(n=1)
        assert isinstance(notes, list)
        if notes:
            assert "title" in notes[0]
            assert "text" in notes[0]
            assert "date" in notes[0]
            assert len(notes[0]["text"]) > 0, "Fetched note has no text"

    def test_fetch_agendas_returns_list(self):
        from services.google_docs import fetch_agendas
        agendas = fetch_agendas(n=1)
        assert isinstance(agendas, list)
        if agendas:
            assert "title" in agendas[0]
            assert "text" in agendas[0]

    def test_notes_sorted_most_recent_first(self):
        from services.google_docs import fetch_meeting_notes
        from datetime import datetime
        notes = fetch_meeting_notes(n=3)
        if len(notes) >= 2:
            dates = [datetime.fromisoformat(n["date"]) for n in notes]
            assert dates == sorted(dates, reverse=True), "Notes are not sorted most-recent first"


class TestGmailFetching:

    def test_fetch_emails_returns_list(self):
        from services.gmail import fetch_committee_emails
        emails = fetch_committee_emails()
        assert isinstance(emails, list)
        if emails:
            assert "subject" in emails[0]
            assert "sender" in emails[0]
            assert "body" in emails[0]

    def test_emails_sorted_chronologically(self):
        from services.gmail import fetch_committee_emails
        emails = fetch_committee_emails()
        if len(emails) >= 2:
            dates = [e["date"] for e in emails]
            assert dates == sorted(dates), "Emails are not sorted chronologically"


class TestFullPipelineWithMockedSave:
    """
    Run the full LangGraph pipeline against real Google data,
    but mock the save step to avoid creating a document.
    """

    def test_pipeline_produces_draft(self):
        from agent.graph import agenda_graph
        from agent.state import AgendaState

        initial: AgendaState = {
            "meeting_date": "Test Run",
            "notes": [],
            "agendas": [],
            "emails": [],
            "tasks": [],
            "draft": "",
            "review_issues": [],
            "revision_count": 0,
            "doc_url": None,
            "error": None,
        }

        # Mock save to avoid writing to Drive
        with patch("agent.nodes.save.create_agenda_doc", return_value="https://mock-url"):
            result = agenda_graph.invoke(initial)

        assert result["draft"], "Pipeline produced an empty draft"
        assert result["tasks"], "Pipeline inferred no tasks"
        assert result["doc_url"] == "https://mock-url"

    def test_pipeline_infers_at_least_one_task(self):
        from agent.graph import agenda_graph
        from agent.state import AgendaState

        initial: AgendaState = {
            "meeting_date": "",
            "notes": [], "agendas": [], "emails": [],
            "tasks": [], "draft": "", "review_issues": [],
            "revision_count": 0, "doc_url": None, "error": None,
        }

        with patch("agent.nodes.save.create_agenda_doc", return_value="https://mock-url"):
            result = agenda_graph.invoke(initial)

        assert len(result["tasks"]) >= 1
