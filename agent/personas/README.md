# AI Personas

This directory contains persona definitions for each AI agent in the system.

## What a persona is

A persona defines *who is reasoning* — the role's domain of competence,
responsibilities, priorities, and boundaries. It is distinct from task prompts
(in `agent/prompts/`), which define *what to do*. A persona is loaded as the
opening section of a system prompt, followed by the relevant task prompt.

Analogy: the persona is the job description; the task prompt is the assignment.

## How personas are used in code

```python
from pathlib import Path

persona = (Path(__file__).parent.parent / "personas" / "chair_artistic_development.md").read_text()
task    = (Path(__file__).parent / "prompts" / "draft_agenda.txt").read_text()

system_prompt = persona + "\n\n---\n\n" + task
```

## How to write a new persona

Each persona file should answer four questions:

1. **Role** — what is this person's title and formal position?
2. **Domain** — what does this role know and care about?
3. **Responsibilities** — what decisions and outputs does this role own?
4. **Boundaries** — what is explicitly outside this role's remit?

Keep personas concise — two to four paragraphs. The goal is to shape the
model's reasoning stance, not to write an exhaustive job description. Avoid
listing every possible task; focus on the knowledge domain and priorities that
distinguish this role from others.

## Relationship to task prompts

| File location | Answers | Changes when |
|---|---|---|
| `agent/personas/*.md` | Who is reasoning? | The role's remit changes |
| `agent/prompts/*.txt` | What should be done? | The task or format changes |

A single persona can be combined with multiple task prompts. For example,
the treasurer persona might be paired with a budget-drafting task prompt
for one agent and a financial-summary task prompt for another.
