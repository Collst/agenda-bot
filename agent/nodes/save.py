"""
agent/nodes/save.py — Write the final draft to Google Drive.
"""

from agent.state import AgendaState
from services.google_docs import create_agenda_doc


def save_agenda(state: AgendaState) -> dict:
    """
    Save the current draft to Google Drive.
    Returns {"doc_url": str}.
    """
    print("  Saving agenda to Google Drive…")
    url = create_agenda_doc(
        agenda_text=state["draft"],
        meeting_date=state.get("meeting_date", ""),
    )
    print(f"  Saved: {url}")
    return {"doc_url": url}