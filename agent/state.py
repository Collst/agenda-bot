"""
agent/state.py — LangGraph state and shared Pydantic models.

AgendaState is the single dict that flows through every node in the graph.
Each node reads from it, adds to it, and returns the fields it changed.

Pydantic models (TaskList, ReviewResult) are used with LangChain's
.with_structured_output() to get reliable, typed LLM responses.
"""

from typing import TypedDict, Optional
from pydantic import BaseModel, Field


# ── Pydantic models (structured LLM outputs) ──────────────────────────────────

class Task(BaseModel):
    description: str = Field(description="What the task is, in one sentence.")
    assignee: Optional[str] = Field(
        default=None,
        description="Name of the person responsible. None if it's a group task.",
    )
    status: str = Field(
        description=(
            "One of: 'complete' (done, needs to be reported), "
            "'in_progress' (partially done), "
            "'unresolved' (not started or no update found)."
        )
    )
    evidence: str = Field(
        description="Brief note on which source this status was inferred from."
    )


class TaskList(BaseModel):
    tasks: list[Task]


class ReviewResult(BaseModel):
    passed: bool = Field(
        description="True if the draft meets format and completeness requirements."
    )
    issues: list[str] = Field(
        default_factory=list,
        description=(
            "Specific, actionable issues found. Empty list if passed=True. "
            "Each issue should be one sentence describing exactly what needs fixing."
        ),
    )


# ── LangGraph state ────────────────────────────────────────────────────────────

class AgendaState(TypedDict):
    # ── pipeline inputs ──────────────────────────────────────────────────────
    meeting_date: str          # human-readable, e.g. "April 22, 2026"

    # ── fetched source material ───────────────────────────────────────────────
    notes: list[dict]          # [{title, date, text}, ...]  most-recent first
    agendas: list[dict]        # [{title, date, text}, ...]  format examples
    emails: list[dict]         # [{date, sender, subject, body}, ...]

    # ── task inference ────────────────────────────────────────────────────────
    tasks: list[dict]          # serialised Task objects

    # ── generation loop ───────────────────────────────────────────────────────
    draft: str                 # current draft agenda text
    review_issues: list[str]   # issues from the last review (empty = passed)
    revision_count: int        # number of revise cycles completed

    # ── output ────────────────────────────────────────────────────────────────
    doc_url: Optional[str]     # URL of the saved Google Doc
    error: Optional[str]       # set if the pipeline fails
