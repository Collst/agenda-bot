"""
agent/graph.py — LangGraph graph definition for the agenda pipeline.

Graph topology:

  fetch_sources
       │
  infer_tasks
       │
  draft_or_revise  ◄──────────────────────────────────────┐
       │                                                    │
  review_draft                                             │
       │                                                    │
       ├── passed OR max revisions reached → save_agenda   │
       │                                                    │
       └── failed AND revisions remaining ─────────────────┘

The review → revise loop runs at most MAX_REVISIONS times (default 3),
after which the best available draft is saved regardless.
"""

import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

from agent.state import AgendaState
from agent.nodes.fetch import fetch_sources
from agent.nodes.infer_tasks import infer_tasks
from agent.nodes.draft import draft_or_revise
from agent.nodes.review import review_draft
from agent.nodes.save import save_agenda

load_dotenv()


def _should_revise(state: AgendaState) -> str:
    """
    Routing function called after review_draft.

    Returns "revise" if there are issues AND we haven't hit the revision cap.
    Returns "save" otherwise.
    """
    max_revisions = int(os.getenv("MAX_REVISIONS", 3))
    issues = state.get("review_issues", [])
    revision_count = state.get("revision_count", 0)

    if issues and revision_count < max_revisions:
        return "revise"
    return "save"


def build_graph() -> StateGraph:
    """Construct and compile the agenda generation graph."""

    graph = StateGraph(AgendaState)

    # ── Register nodes ────────────────────────────────────────────────────────
    graph.add_node("fetch_sources", fetch_sources)
    graph.add_node("infer_tasks", infer_tasks)
    graph.add_node("draft_or_revise", draft_or_revise)
    graph.add_node("review_draft", review_draft)
    graph.add_node("save_agenda", save_agenda)

    # ── Linear edges ─────────────────────────────────────────────────────────
    graph.set_entry_point("fetch_sources")
    graph.add_edge("fetch_sources", "infer_tasks")
    graph.add_edge("infer_tasks", "draft_or_revise")
    graph.add_edge("draft_or_revise", "review_draft")

    # ── Conditional edge: review → revise or save ─────────────────────────────
    graph.add_conditional_edges(
        "review_draft",
        _should_revise,
        {
            "revise": "draft_or_revise",
            "save": "save_agenda",
        },
    )

    graph.add_edge("save_agenda", END)

    return graph.compile()


# Module-level compiled graph — imported by main.py and tests
agenda_graph = build_graph()
