"""
scripts/evaluate.py
"""

from unittest.mock import patch

from dotenv import load_dotenv
from agent.graph import agenda_graph
from agent.state import AgendaState
from services.langfuse_client import langfuse_client, get_langfuse_handler
from tests.fixtures.data import SAMPLE_NOTES, SAMPLE_AGENDAS, SAMPLE_EMAILS

load_dotenv(".env.local", override=True)
load_dotenv(".env")

langfuse = langfuse_client
langfuse_handler = get_langfuse_handler()

initial_state: AgendaState = {
    "meeting_date": "April 22, 2026",
    "notes": SAMPLE_NOTES,
    "agendas": SAMPLE_AGENDAS,
    "emails": SAMPLE_EMAILS,
    "tasks": [],
    "draft": "",
    "review_issues": [],
    "revision_count": 0,
    "doc_url": None,
    "error": None,
}

with patch("agent.nodes.fetch.fetch_meeting_notes", return_value=SAMPLE_NOTES), \
     patch("agent.nodes.fetch.fetch_agendas", return_value=SAMPLE_AGENDAS), \
     patch("agent.nodes.fetch.fetch_committee_emails", return_value=SAMPLE_EMAILS):
        result = agenda_graph.invoke(
        initial_state,
        config={"callbacks": [langfuse_handler]}
    )

print("=== INFERRED TASKS ===")
for task in result["tasks"]:
    print(f"  [{task['status'].upper()}] {task['description']}")

print("\n=== DRAFT AGENDA ===")
print(result["draft"])

print("\n=== REVISION COUNT ===")
print(result["revision_count"])

print("\n=== REVIEW ISSUES (final) ===")
print(result["review_issues"] or "None — review passed")