"""
main.py — FastAPI application.

Endpoints:
  GET  /health              — liveness check
  POST /agenda/generate     — run the full pipeline, return doc URL
  GET  /agenda/status/{id}  — poll a running job (async pattern)

The generate endpoint is async: it starts a background job and returns
immediately with a job ID. The caller (n8n, curl, a future UI) polls
/agenda/status/{id} until the job is complete.

Run locally:
  uvicorn main:app --reload --port 8000

Via Docker:
  docker compose up
"""

import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from services.langfuse_client import get_langfuse_handler
from agent.graph import agenda_graph
from agent.state import AgendaState

load_dotenv(".env.local", override=True)
load_dotenv(".env")


# ── In-memory job store ───────────────────────────────────────────────────────
# For a single-user monthly tool this is sufficient.
# Swap for Redis if you ever need persistence across restarts.
_jobs: dict[str, dict] = {}


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    meeting_date: str = ""   # e.g. "April 22, 2026" — used in doc title and prompt


class JobResponse(BaseModel):
    job_id: str
    status: str              # "pending" | "running" | "complete" | "failed"
    doc_url: Optional[str] = None
    error: Optional[str] = None


# ── Background task ───────────────────────────────────────────────────────────

def _run_pipeline(job_id: str, meeting_date: str) -> None:
    """Execute the LangGraph pipeline in a background thread."""
    _jobs[job_id]["status"] = "running"
    try:
        langfuse_handler = get_langfuse_handler()

        initial_state: AgendaState = {
            "meeting_date": meeting_date,
            "notes": [],
            "agendas": [],
            "emails": [],
            "tasks": [],
            "draft": "",
            "review_issues": [],
            "revision_count": 0,
            "doc_url": None,
            "error": None,
        }
        result = agenda_graph.invoke(
            initial_state,
            config={"callbacks": [langfuse_handler]}
            )

        _jobs[job_id]["status"] = "complete"
        _jobs[job_id]["doc_url"] = result.get("doc_url")
    except Exception as exc:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(exc)


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Agenda Bot API ready.")
    yield

app = FastAPI(
    title="Committee Agenda Bot",
    description="AI-powered meeting agenda generator for theatre committees.",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["ops"])
def health():
    """Liveness check — returns 200 if the server is running."""
    return {"status": "ok"}


@app.post("/agenda/generate", response_model=JobResponse, tags=["agenda"])
def generate_agenda(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    Start an agenda generation job.

    Returns immediately with a job_id. Poll GET /agenda/status/{job_id}
    for the result.
    """
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending", "doc_url": None, "error": None}
    background_tasks.add_task(_run_pipeline, job_id, request.meeting_date)
    return JobResponse(job_id=job_id, status="pending")


@app.get("/agenda/status/{job_id}", response_model=JobResponse, tags=["agenda"])
def get_status(job_id: str):
    """Poll the status of a generation job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return JobResponse(
        job_id=job_id,
        status=job["status"],
        doc_url=job.get("doc_url"),
        error=job.get("error"),
    )
