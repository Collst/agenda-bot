# Committee Agenda Bot — Learning Journey Summary

A record of concepts, decisions, and pointers covered in building this system,
written for a beginner entering the world of modern software development and
LLM-powered applications.

---

## What was built

An AI-powered meeting agenda generator for a community theatre committee. Given
Google Drive meeting notes, past agendas, and committee emails, it infers which
tasks are complete and which need discussion, drafts an agenda in your
established format, reviews and revises it in a loop, then saves the result as
a Google Doc.

The system is a working example of several modern software development practices
applied to a real, small-scale problem. The value of building something real —
rather than following a tutorial — is that every decision had a consequence you
could observe.

---

## The tech stack, and why each piece is there

| Tool | Role | Why this one |
|---|---|---|
| **Python** | Application language | Strong LLM/AI library ecosystem |
| **LangChain** | LLM abstraction layer | Standardised interface across model providers |
| **LangGraph** | Pipeline orchestration | Native support for conditional, stateful workflows |
| **FastAPI** | HTTP API framework | Modern, fast, auto-generates documentation |
| **Pydantic** | Data validation | Typed, validated data in and out of LLM calls |
| **Google APIs** | Data sources and output | Where your committee's data already lives |
| **Ollama** | Local LLM server | Runs models on your Mac without data leaving |
| **Docker Compose** | Multi-service deployment | One command starts the entire system |
| **n8n** | External trigger layer | Browser-accessible trigger without code |
| **LangSmith** | Observability | See exactly what goes into and out of every LLM call |
| **pytest** | Testing | Unit and integration test framework |
| **GitHub Actions** | CI | Runs tests automatically on every push |

---

## Software development concepts encountered

### Separation of concerns
Each directory has one job. `auth/` manages credentials. `services/` talks to
external systems. `agent/` contains AI pipeline logic. `tests/` contains
verification. When something breaks, you know where to look.

*Reference:* Dijkstra, E.W. (1974). *On the role of scientific thought.*
[EWD447](https://www.cs.utexas.edu/~EWD/ewd04xx/EWD447.PDF)

### Modular design and encapsulation
Modules expose a small, clean public interface and hide their internal
complexity. The tabs-parsing logic in `google_docs.py` is invisible to the
rest of the system — it just calls `fetch_meeting_notes()`. The leading
underscore convention (`_DRAFT_PROMPT`) signals internal implementation
details to human readers, though the real encapsulation comes from the module
structure itself.

*Reference:* Parnas, D.L. (1972). "On the criteria to be used in decomposing
systems into modules." *CACM*, 15(12).
[ACM](https://dl.acm.org/doi/10.1145/361598.361623)

### Containerisation
The `Dockerfile` and `docker-compose.yml` package the system so it runs
identically on any machine. The key word is *reproducible*. Important
distinction learned: develop in a virtual environment (`.venv`), deploy via
Docker. They coexist and serve different purposes.

*Reference:* [Docker documentation](https://docs.docker.com/get-started/docker-overview/)

Key gotcha encountered: Docker creates a directory placeholder for volume
mounts if the file doesn't exist yet. Always generate `token.json` before
running `docker compose up` for the first time.

### API ownership / service-oriented design
The system exposes a stable HTTP interface (`/health`, `/agenda/generate`,
`/agenda/status/{id}`). Any client can call it without knowing the internals.
This is what "owning an API" means in practice.

Auto-generated documentation at `http://localhost:8000/docs` is a concrete,
clickable manifestation of the concept.

*Reference:* Fielding, R.T. (2000). *Architectural Styles and the Design of
Network-based Software Architectures.* Chapter 5.
[UCI](https://ics.uci.edu/~fielding/pubs/dissertation/top.htm)

### Asynchronous job pattern
`POST /agenda/generate` returns a `job_id` immediately. The caller polls
`GET /agenda/status/{id}` for the result. This prevents HTTP timeouts on
long-running operations and decouples the trigger from the result. You
encountered this pattern directly: the pipeline takes 60–90 seconds but
the API responds in under a second.

*Reference:* [Microsoft Azure Architecture Center — Async Request-Reply](https://learn.microsoft.com/en-us/azure/architecture/patterns/async-request-reply)

### Graph-based orchestration
LangGraph represents the pipeline as a directed graph with typed state flowing
between nodes. The conditional edge (`review → revise or save`) is a
first-class architectural element. This is meaningfully different from a
linear script because it makes control flow visible, inspectable, and testable.

LangChain and LangGraph are not alternatives — LangGraph is built on LangChain.
LangChain components (chat models, prompt templates) are the building blocks
*inside* LangGraph nodes.

*Reference:* [LangGraph concepts](https://langchain-ai.github.io/langgraph/concepts/)

### Structured outputs as contracts
`infer_tasks` and `review_draft` use Pydantic models with `.with_structured_output()`.
The routing decision in the graph branches on a Python `bool`, not string-matching
on LLM prose. This is the difference between reliable and fragile pipeline logic.

*Reference:* [Pydantic documentation](https://docs.pydantic.dev/latest/concepts/models/)

### Environment-based configuration
Nothing sensitive is hardcoded. Everything is in `.env`, excluded from version
control via `.gitignore`. The `.env.example` documents the full configuration
surface. This is the Twelve-Factor App methodology.

Gotcha encountered: `host.docker.internal` (Docker's DNS name for the host Mac)
is not valid outside Docker. When running scripts locally, use `localhost:11434`.
Solution: prefix the command or maintain a `.env.local` override file.

*Reference:* [Twelve-Factor App — Config](https://12factor.net/config)

### Switchable backends (strategy pattern)
`get_llm()` in `services/llm.py` returns the appropriate model based on a
single environment variable. Switching between Anthropic and Ollama requires
no code changes. This is the strategy pattern: the algorithm is swapped at
runtime without changing the surrounding code.

*Reference:* Gamma et al. (1994). *Design Patterns.* Addison-Wesley. p. 315.

### Layered testing (test pyramid)
Unit tests (fast, mocked, no external services) run on every commit via CI.
Integration tests (live Google APIs) run manually before releases. The guard
`pytestmark = pytest.mark.skipif(not os.getenv("INTEGRATION_TESTS"), ...)`
enforces this separation. `INTEGRATION_TESTS` is deliberately not in `.env`
— if it were, the guard would be meaningless.

*Reference:* Fowler, M. (2012). [Test Pyramid](https://martinfowler.com/bliki/TestPyramid.html)

### Continuous integration
`.github/workflows/ci.yml` runs unit tests automatically on every push.
Failing fast means catching regressions before they reach a collaborator.

*Reference:* Fowler, M. (2006). [Continuous Integration](https://martinfowler.com/articles/continuousIntegration.html)

### Principle of least surprise
Code should behave and look the way a reader expects. Deviations from
established patterns in a codebase should be intentional and meaningful.
When working in an existing codebase, scan for conventions before introducing
new ones. Inconsistent conventions are more disorienting than either convention
applied uniformly.

### YAGNI (You Aren't Gonna Need It)
Don't add complexity in anticipation of problems you don't have yet. Applied
here to the database question: fetching fresh from Google on every monthly
run is simpler and more correct than caching, until there's a concrete reason
to cache.

---

## Prompt architecture concepts encountered

### Prompts as configuration
Task instructions live in `agent/prompts/*.txt` as plain text files, separate
from code. Non-developers can tune system behaviour without touching Python.

### AI personas
`agent/personas/*.md` define *who is reasoning* — role, domain,
responsibilities, boundaries. Task prompts define *what to do*.
The two are composed at runtime: `system = persona + "---" + task_prompt`.
Keeping them separate means you can change what an agent does without
changing who it is, and vice versa.

### Single responsibility in prompts
A prompt file should do one thing. The original `draft_agenda.txt` violated
this by defining both identity ("you are a secretary") and task instructions.
After the persona system was introduced, the identity claim was removed from
the task prompt. The concept is *tight coupling* — two concerns tangled in
one artifact.

### Few-shot prompting
Providing concrete examples of desired output in the prompt, rather than
describing the format abstractly. More effective than descriptions for
formatting tasks. The right placement: examples at the top of the user
message, before the actual data.

### Few-shot chain-of-thought
Showing the reasoning that produced an example output, not just the output
itself. Useful for inference tasks (like task status determination) where
the model needs to reason across multiple documents.

### Evaluation vs. testing
A software test checks that code does what it's supposed to do.
An *evaluation* checks that a model produces output of acceptable quality
given specific inputs. Both matter; they're different things. `scripts/evaluate.py`
exists for evaluations; `tests/` exists for software tests.

### Observability with LangSmith
LangSmith captures every LLM call: exact prompt sent, exact response received,
latency, token counts, position in the graph. The workflow for diagnosing
quality problems:
1. Open the run trace for `infer_tasks`
2. Read the **Input** tab — if the assembled prompt looks wrong, it's a code
   or data problem, not a model problem
3. Read the **Output** tab — if the input looks right but the output is wrong,
   it's a reasoning problem addressable with better prompts or examples
4. Compare runs before and after a prompt change side by side

---

## Data governance and model choice

The core tradeoff: Anthropic API (higher quality, data leaves your machine)
vs. Ollama (local, data stays on device, somewhat lower quality at equivalent
parameter counts).

The switchable backend design means this is a configuration decision, not
an architectural one. For a monthly task at your data volume, Anthropic costs
under $0.50/month. For organisations with stricter data governance requirements,
Ollama with `qwen2.5:14b` runs comfortably on 24GB unified memory.

Apple Silicon note: run Ollama natively via Homebrew, not inside Docker.
Docker containers on Mac don't access the Apple Neural Engine, which is where
most of the inference performance on M-series chips comes from.

`host.docker.internal` is the Docker DNS name that lets containers reach
natively-running services on the host Mac.

---

## Pointers for continuing the journey

**Read in this order if you want foundations:**
1. Dijkstra's EWD447 (separation of concerns) — short and worth reading in full
2. Parnas 1972 (modular design) — the most cited paper in software engineering
3. Fielding's dissertation Chapter 5 (REST) — explains why APIs are designed the way they are
4. The Twelve-Factor App (https://12factor.net) — twelve short pages, read all of them
5. Fowler's Test Pyramid and Continuous Integration articles — brief and practical

**Tools to get familiar with next:**
- LangSmith — you've set it up; use it actively during prompt iteration
- FastAPI interactive docs (`/docs`) — explore your own API as a user
- `ollama list`, `ollama rm`, `ollama pull` — model management is just inventory management
- `docker compose logs agenda-bot` — view container logs without attaching to the process

**Concepts to explore when ready:**
- LangGraph's `Send` API for parallel node execution
- Pydantic's `model_validator` for cross-field validation
- FastAPI's dependency injection for sharing resources across endpoints
- The supervisor architecture for multi-agent systems
- SQLite as a lightweight local cache (when you have a concrete reason to add it)

**The note-taking extension:**
The modular design anticipates this. The natural extension point is a new
sub-graph: audio file → Whisper transcription → local LLM summarisation →
structured meeting notes → written to the Notes Google Doc. Each step is
independently testable. Whisper.cpp and WhisperKit are the tools to look at
for Apple Silicon transcription.

---

## On continuity and sustainability

The system is only as durable as its documentation and the legibility of its
code. The README covers setup and usage. What it still lacks:
- An architecture diagram (Mermaid format renders in GitHub automatically)
- A "for developers" onboarding section explaining reading order
- Architecture Decision Records for the major choices made

The personas directory, the prompts-as-configuration pattern, and the modular
structure all reduce the bus factor — the risk that the system becomes
unmaintainable if one person leaves. The lower the barrier to understanding,
the more likely the system survives a transition.
