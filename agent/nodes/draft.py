"""
agent/nodes/draft.py — Generate or revise the agenda draft.

This single node handles two cases:
  1. Initial draft  (revision_count == 0): generates from scratch.
  2. Revision       (revision_count > 0):  rewrites based on review issues.

Keeping both in one node avoids duplicating the LLM call and the
prompt-assembly logic.
"""

from pathlib import Path
# from platform import system
from langchain_core.messages import SystemMessage, HumanMessage
from agent.state import AgendaState
from services.llm import get_llm
from langchain_core.runnables import RunnableConfig
from langfuse import observe

_DRAFT_PROMPT = (
    Path(__file__).parent.parent / "prompts" / "draft_agenda.txt"
).read_text()

_PERSONA = (
    Path(__file__).parent.parent / "personas" / "chair_artistic_development.md"
).read_text()

_REVISE_PROMPT = (
    Path(__file__).parent.parent / "prompts" / "revise_draft.txt"
).read_text()

_SKILL = (
    Path(__file__).parent.parent / "skills" / "agenda_format.md"
).read_text()


def _format_tasks(tasks: list[dict]) -> str:
    if not tasks:
        return "[No tasks found]\n"
    lines = ["=== TASK LIST ===\n"]
    for t in tasks:
        assignee = t.get("assignee") or "Group"
        lines.append(
            f"• [{t['status'].upper()}] {t['description']} "
            f"(Assignee: {assignee})\n"
            f"  Evidence: {t.get('evidence', '')}\n"
        )
    return "".join(lines)


def _format_agendas(agendas: list[dict]) -> str:
    parts = ["=== FORMAT EXAMPLES (past agendas) ===\n"]
    for a in agendas:
        parts.append(f"--- {a['title']} ---\n{a['text']}\n\n")
    return "".join(parts)


@observe()
def draft_or_revise(state: AgendaState, config: RunnableConfig) -> dict:
    """
    Generate the initial draft or revise based on review feedback.
    Returns {"draft": str, "revision_count": int}.
    """
    llm = get_llm()
    revision_count = state.get("revision_count", 0)
    agendas_block = _format_agendas(state["agendas"])
    tasks_block = _format_tasks(state["tasks"])
    meeting_date = state.get("meeting_date", "")

    if revision_count == 0:
        # ── Initial draft ──────────────────────────────────────────────────
        date_line = f"Upcoming meeting date: {meeting_date}\n\n" if meeting_date else ""
        user_content = date_line + agendas_block + "\n" + tasks_block
        system = _SKILL+"\n\n---\n\n"+ _PERSONA + "\n\n---\n\n" + _DRAFT_PROMPT
        print("  Drafting agenda…")
    else:
        # ── Revision ───────────────────────────────────────────────────────
        issues_block = "\n".join(f"- {issue}" for issue in state["review_issues"])
        user_content = (
            f"=== CURRENT DRAFT ===\n{state['draft']}\n\n"
            f"=== ISSUES TO FIX ===\n{issues_block}\n\n"
            f"{agendas_block}"
        )
        system = _PERSONA + "\n\n---\n\n" + _REVISE_PROMPT
        print(f"  Revising draft (pass {revision_count})…")

    response = llm.invoke(
        [SystemMessage(content=system), HumanMessage(content=user_content)], 
        config=config
    )

    return {
        "draft": response.content,
        "revision_count": revision_count,  # incremented by graph after review
    }