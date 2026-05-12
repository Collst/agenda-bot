"""
agent/nodes/infer_tasks.py — Cross-reference all sources and produce a task list.

Uses structured output so the result is a typed list of Task objects,
not free-form text. This gives the downstream draft node a clean, reliable
input rather than prose it has to re-parse.
"""

from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage
from agent.state import AgendaState, TaskList
from services.llm import get_llm
from langchain_core.runnables import RunnableConfig
from langfuse import observe

_TASK = (
    Path(__file__).parent.parent / "prompts" / "infer_tasks.txt"
    ).read_text()

_PERSONA = (
    Path(__file__).parent.parent / "personas" / "chair_artistic_development.md"
    ).read_text()

_SKILL = (
    Path(__file__).parent.parent / "skills" / "agenda_format.md"
    ).read_text()

_EXAMPLES = (
    Path(__file__).parent.parent / "skills" / "task_inference_example.md"
    ).read_text()



def _format_notes(notes: list[dict]) -> str:
    if not notes:
        return "[No meeting notes available]\n"
    parts = ["=== MEETING NOTES ===\n"]
    for n in notes:
        parts.append(f"--- {n['title']} ({n['date']}) ---\n{n['text']}\n\n")
    return "".join(parts)


def _format_agendas(agendas: list[dict]) -> str:
    if not agendas:
        return "[No past agendas available]\n"
    parts = ["=== PAST AGENDAS ===\n"]
    for a in agendas:
        parts.append(f"--- {a['title']} ({a['date']}) ---\n{a['text']}\n\n")
    return "".join(parts)


def _format_emails(emails: list[dict]) -> str:
    if not emails:
        return "[No committee emails for this period]\n"
    parts = ["=== COMMITTEE EMAILS ===\n"]
    for e in emails:
        parts.append(
            f"FROM: {e['sender']}\nDATE: {e['date']}\n"
            f"SUBJECT: {e['subject']}\n{e['body']}\n{'─'*40}\n"
        )
    return "".join(parts)

@observe()
def infer_tasks(state: AgendaState, config: RunnableConfig) -> dict:
    """
    Call the LLM with structured output to produce a typed TaskList.
    Returns {"tasks": [serialised Task dicts]}.
    """
    llm = get_llm().with_structured_output(TaskList)

    user_content = (_EXAMPLES
    + "\n\n---\n\n"
    + _format_notes(state["notes"])
    + "\n"
    + _format_agendas(state["agendas"])
    + "\n"
    + _format_emails(state["emails"])
    )

    result: TaskList = llm.invoke(
        [
            SystemMessage(content=_SKILL+"\n\n---\n\n"+_PERSONA+"\n\n---\n\n"+_TASK), 
            HumanMessage(content=user_content)
        ],
        config=config
    )

    tasks = [t.model_dump() for t in result.tasks]
    print(f"  Inferred {len(tasks)} task(s).")
    return {"tasks": tasks}