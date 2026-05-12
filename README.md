# Committee Agenda Bot

This system reads Gmail and Google Docs to infer and generate an upcoming meeting agenda. It is designed with small organizations in mind and can be configured so that data stays completely local.

Community theaters and other lean non-profit organizations rely on a small number of people — often volunteer or low-paid staff — for their operations. A recurring responsibility for people in leadership roles is meeting preparation: reading emails, meeting notes, and past agendas to assess which tasks have been completed and which remain unresolved, then producing an agenda that reflects accurately the status of each task. This important task takes hours when done properly. When done by the same few people month after month, it can lead to the kind of burnout that can threaten the organization itself.

In order to address this problem, we have built an AI-powered meeting agenda generator. The workflow reads your Google Drive meeting notes, past agendas, and committee emails; it infers which tasks are done and which need discussion; drafts an agenda in your established format; reviews and revises it; then saves the result as a Google Doc.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  LangGraph Pipeline                                             │
│                                                                 │
│  fetch_sources → infer_tasks → draft_or_revise → review_draft  │
│                                       ▲               │         │
│                                       └── revise ─────┘         │
│                                               │ save             │
│                                         save_agenda             │
└─────────────────────────────────────────────────────────────────┘
         ▲                                      │
  FastAPI /agenda/generate              Google Drive (output doc)
         ▲
    n8n webhook (optional trigger)
```

**Tech stack:**
- **LangGraph** — graph orchestration (draft → review → conditional revise loop)
- **LangChain** — LLM abstraction layer (Anthropic, Gemini, or Ollama, switchable via `.env`)
- **FastAPI** — owned API with async job pattern
- **Google APIs** — Drive, Docs (tabs-aware), Gmail
- **Docker Compose** — one-command local deployment

---

## Prerequisites

- Python 3.12+
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Apple Silicon build available)
- A Google account with access to the committee Drive folder and Gmail
- An [Anthropic API key](https://console.anthropic.com/) (if using `LLM_BACKEND=anthropic`)
- [Ollama](https://ollama.com/) (if using `LLM_BACKEND=ollama` — see note below)

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/your-org/committee-agenda-bot.git
cd committee-agenda-bot
pip install -r requirements.txt
```

### 2. Google Cloud credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → create a project.
2. Enable: **Google Drive API**, **Google Docs API**, **Gmail API**.
3. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
4. Application type: **Desktop app**. Download the JSON and save as `credentials.json` in the project root.
5. Go to **OAuth consent screen → Test users** and add your Google account.

On first run a browser tab opens for authorisation. `token.json` is then saved automatically.

> `credentials.json` and `token.json` are in `.gitignore`. Never commit them.

### 3. Configure environment

```bash
cp .env.example .env
```

Fill in `.env`. Key values:

| Variable | How to find it |
|---|---|
| `NOTES_DOC_ID` | Open the notes Google Doc → copy the ID from the URL (`/d/<ID>/edit`) |
| `AGENDAS_DOC_ID` | Same, for the agendas doc |
| `OUTPUT_FOLDER_ID` | Open the output Drive folder → copy the ID from the URL (`/folders/<ID>`) |
| `GMAIL_LABEL` | The Gmail label you apply to committee threads |
| `COMMITTEE_EMAILS` | Comma-separated member addresses (supplement or fallback to label) |
| `LLM_BACKEND` | `anthropic` or `ollama` |

### 4. Install the Langfuse AI Skill

This repository already includes runtime Langfuse tracing using the `langfuse` Python SDK, `CallbackHandler`, and `@observe()` instrumentation.

The Langfuse AI skill from `github.com/langfuse/skills` is an agent skill for coding assistants and is installed outside the Python runtime. If you want your assistant to help manage Langfuse traces, prompts, and API usage, install it with one of these methods:

```bash
npx skills add langfuse/skills --skill "langfuse"
```

Or clone and symlink it into your agent skills directory:

```bash
git clone https://github.com/langfuse/skills.git /tmp/langfuse-skills
ln -s /tmp/langfuse-skills/skills/langfuse /path/to/your/agent/skills/langfuse
```

After that, make sure your application env contains your Langfuse project keys:

```env
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=http://localhost:3000
```

### 5. Ollama (local backend only)

For best performance on Apple Silicon, run Ollama natively rather than in Docker:

```bash
brew install ollama
ollama serve                  # in one terminal — keep it running
ollama pull qwen2.5:14b       # one-time model download (~9 GB)
```

Then in `.env`:
```
LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

And comment out the `ollama` service in `docker-compose.yml`.

---

## Running

### Option A — Docker Compose (recommended)

```bash
docker compose up --build
```

The API is available at `http://localhost:8000`.  
Interactive API docs: `http://localhost:8000/docs`

### Option B — Local Python (dev / dry run)

```bash
# First run — triggers Google OAuth browser flow
uvicorn main:app --reload --port 8000

# Trigger a job via curl
curl -X POST http://localhost:8000/agenda/generate \
  -H "Content-Type: application/json" \
  -d '{"meeting_date": "April 22, 2026"}'

# Poll for the result (use the job_id from the response above)
curl http://localhost:8000/agenda/status/<job_id>
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `POST` | `/agenda/generate` | Start a generation job → returns `job_id` |
| `GET` | `/agenda/status/{job_id}` | Poll job status → returns `status`, `doc_url` |

Full interactive docs at `/docs` when the server is running.

---

## Google Docs structure

The bot expects your notes and agendas to use **Google Docs native tabs**:

```
Notes Doc
├── Tab: "2025"
│   ├── Sub-tab: "09/23/25"
│   ├── Sub-tab: "10/28/25"
│   └── Sub-tab: "11/25/25"
└── Tab: "2026"
    ├── Sub-tab: "01/27/26"
    └── Sub-tab: "03/25/26"   ← most recent, fetched first
```

Sub-tab titles must contain a recognisable date in one of these formats:
`MM/DD/YY`, `MM/DD/YYYY`, or `YYYY-MM-DD`.

---

## Customising the prompts

All LLM instructions live in `agent/prompts/`. Edit these plain text files to tune behaviour without touching code:

| File | Controls |
|---|---|
| `infer_tasks.txt` | How tasks are identified and their status inferred |
| `draft_agenda.txt` | How the agenda is structured and how each task status maps to a section |
| `review_draft.txt` | What the reviewer checks — format and completeness criteria |
| `revise_draft.txt` | How the reviser is instructed to apply fixes |

---

## Testing

```bash
# Unit tests (no live services required)
pytest tests/unit/ -v

# Integration tests (requires .env with real credentials)
INTEGRATION_TESTS=1 pytest tests/integration/ -v -s
```

Unit tests run automatically on every push via GitHub Actions (`.github/workflows/ci.yml`).

Integration tests are intentionally manual — they read real Google data and should be run before releases, not on every commit.

---

## n8n integration (optional)

If you want a browser-accessible trigger rather than `curl`:

1. Start n8n via `docker compose up`.
2. Open `http://localhost:5678` (default credentials: `admin` / `changeme` — change these).
3. Go to **Settings → Import Workflow** and upload `n8n/workflow.json`.
4. Activate the workflow.
5. The webhook URL will be `http://localhost:5678/webhook/generate-agenda`.

---

## Project structure

```
committee-agenda-bot/
├── main.py                        # FastAPI app (owned API)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── pytest.ini
├── .env.example
├── .gitignore
├── auth/
│   └── google.py                  # OAuth2 credential management
├── services/
│   ├── llm.py                     # Switchable LLM factory (Anthropic / Ollama)
│   ├── google_docs.py             # Tabs-aware Doc fetcher + output writer
│   └── gmail.py                   # Committee email fetcher
├── agent/
│   ├── state.py                   # LangGraph state + Pydantic output schemas
│   ├── graph.py                   # Graph definition and routing logic
│   ├── prompts/
│   │   ├── infer_tasks.txt
│   │   ├── draft_agenda.txt
│   │   ├── review_draft.txt
│   │   └── revise_draft.txt
│   ├── skills/
│   ├── personas/
│   └── nodes/
│       ├── fetch.py
│       ├── infer_tasks.py
│       ├── draft.py
│       ├── review.py
│       └── save.py
├── scripts/
│   └── evaluate.py                # run workflow through a small sample of text
├── tests/
│   ├── fixtures/data.py           # Shared anonymised test data
│   ├── unit/test_services.py      # Unit tests (mocked, fast)
│   └── integration/test_pipeline.py  # Integration tests (live APIs)
├── n8n/
│   └── workflow.json
└── .github/
    └── workflows/ci.yml           # GitHub Actions CI
```

---

## Privacy

This tool processes internal committee emails and meeting notes. If using `LLM_BACKEND=anthropic`, data is sent to Anthropic's API. Anthropic does not use API inputs for model training by default — see [Anthropic's privacy policy](https://www.anthropic.com/privacy). Recommended: inform committee members that communications may be processed by this tool. Use `LLM_BACKEND=ollama` for fully local processing if required.

---

## Adding note-taking later

The modular design is intended to accommodate a transcription → summarisation pipeline later. The natural extension point is a new LangGraph node (or sub-graph) that accepts an audio file, produces structured meeting notes, and writes them into the Notes Google Doc. That sub-graph can be developed and tested independently, then wired into this pipeline without changing any existing nodes.
