"""
agent/nodes/review.py — Review the draft for format and completeness.

Uses structured output (ReviewResult) so the routing decision is based on
a typed boolean, not string matching on LLM prose.
"""

from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage
from agent.state import AgendaState, ReviewResult
from services.llm import get_llm
from langchain_core.runnables import RunnableConfig
from langfuse import observe

_PROMPT = (
    Path(__file__).parent.parent / "prompts" / "review_draft.txt"
).read_text()

_PERSONA = (
    Path(__file__).parent.parent / "personas" / "chair_artistic_development.md"
).read_text()


def _format_tasks(tasks: list[dict]) -> str:
    lines = ["=== TASK LIST ===\n"]
    for t in tasks:
        assignee = t.get("assignee") or "Group"
        lines.append(
            f"• [{t['status'].upper()}] {t['description']} (Assignee: {assignee})\n"
        )
    return "".join(lines)


def _format_agendas(agendas: list[dict]) -> str:
    parts = ["=== FORMAT EXAMPLES ===\n"]
    for a in agendas:
        parts.append(f"--- {a['title']} ---\n{a['text']}\n\n")
    return "".join(parts)


@observe()
def review_draft(state: AgendaState, config: RunnableConfig) -> dict:
    """
    Review the current draft. Returns {"review_issues": list[str], "revision_count": int}.
    revision_count is incremented here (after review) rather than in the draft node,
    so the count accurately reflects completed review cycles.
    """
    llm = get_llm().with_structured_output(ReviewResult)

    user_content = (
        f"=== DRAFT AGENDA ===\n{state['draft']}\n\n"
        + _format_agendas(state["agendas"])
        + "\n"
        + _format_tasks(state["tasks"])
    )

    result: ReviewResult = llm.invoke(
        [
            SystemMessage(content=_PERSONA+"\n\n---\n\n"+_PROMPT), 
            HumanMessage(content=user_content)
        ], 
        config=config
    )

    if result.passed:
        print("  Review passed.")
    else:
        print(f"  Review found {len(result.issues)} issue(s).")

    return {
        "review_issues": result.issues if not result.passed else [],
        "revision_count": state.get("revision_count", 0) + 1,
    }
