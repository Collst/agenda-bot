"""
agent/nodes/fetch.py — Fetch all source material and populate state.

This is a single node (not parallel sub-nodes) for clarity. For a monthly
task the sequential IO latency is negligible. If you want true parallelism
later, LangGraph's Send API can fan out to sub-graphs.
"""

from agent.state import AgendaState
from services.google_docs import fetch_meeting_notes, fetch_agendas
from services.gmail import fetch_committee_emails


def fetch_sources(state: AgendaState) -> dict:
    """
    Fetch notes, agendas, and emails. Returns the fields to merge into state.
    Raises on any fetch failure so the graph routes to an error state.
    """
    notes = fetch_meeting_notes()
    agendas = fetch_agendas()
    emails = fetch_committee_emails()

    print(
        f"  Fetched: {len(notes)} note tab(s), "
        f"{len(agendas)} agenda tab(s), "
        f"{len(emails)} email(s)."
    )

    print("  Sample fetched note:", notes[0] if notes else "No notes")
    print("  Sample fetched agenda:", agendas[0] if agendas else "No agendas")
    print("  Sample fetched email:", emails[0] if emails else "No emails")
    
    return {
        "notes": notes,
        "agendas": agendas,
        "emails": emails,
    }
