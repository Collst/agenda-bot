"""
tests/unit/test_state.py — Unit tests for Pydantic models in state.py

Run with: python3 -m tests.unit.test_state
"""

import pytest
from agent import state
from pydantic import ValidationError

def test_task_creation_valid():
    """Test that a valid Task object can be created."""
    task = state.Task(
        description="Testing Task model",
        assignee="Alice",
        status="in_progress",
        evidence="Found a note saying Alice started working on it."
    )

    assert task.description == "Testing Task model"
    assert task.assignee == "Alice"
    assert task.status == "in_progress"
    assert task.evidence == "Found a note saying Alice started working on it."

def test_task_creation_missing_status():
    """Test that Task raises an error if the required 'status' is missing."""
    
    # Pytest has a special 'context manager' for testing errors.
    # It says: "The code inside this block MUST raise a ValidationError."
    with pytest.raises(ValidationError):
        state.Task(
            description="No status here",
            assignee="Bob",
            evidence="Some evidence"
        )


def test_task_with_optional_assignee_none():
    """Test that a Task can be created with assignee=None (group task)."""
    task = state.Task(
        description="Group planning task",
        assignee=None,
        status="in_progress",
        evidence="Meeting notes indicate this is a team effort."
    )
    
    assert task.assignee is None
    assert task.description == "Group planning task"


# ── TaskList tests ────────────────────────────────────────────────────────────

def test_tasklist_creation_valid():
    """Test that a valid TaskList object can be created with multiple tasks."""
    tasks = [
        state.Task(
            description="First task",
            assignee="Alice",
            status="complete",
            evidence="Confirmed in email"
        ),
        state.Task(
            description="Second task",
            assignee="Bob",
            status="in_progress",
            evidence="Found in notes"
        ),
    ]
    
    task_list = state.TaskList(tasks=tasks)
    
    assert len(task_list.tasks) == 2
    assert task_list.tasks[0].description == "First task"
    assert task_list.tasks[1].assignee == "Bob"


def test_tasklist_empty():
    """Test that a TaskList can be created with an empty task list."""
    task_list = state.TaskList(tasks=[])
    
    assert len(task_list.tasks) == 0
    assert task_list.tasks == []


def test_tasklist_single_task():
    """Test that a TaskList works correctly with a single task."""
    task = state.Task(
        description="Only task",
        assignee="Charlie",
        status="unresolved",
        evidence="No mention in any source"
    )
    
    task_list = state.TaskList(tasks=[task])
    
    assert len(task_list.tasks) == 1
    assert task_list.tasks[0].description == "Only task"


def test_tasklist_invalid_missing_tasks():
    """Test that TaskList raises an error if the 'tasks' field is missing."""
    with pytest.raises(ValidationError):
        state.TaskList()


# ── ReviewResult tests ────────────────────────────────────────────────────────

def test_reviewresult_passed_no_issues():
    """Test that a ReviewResult can be created with passed=True and no issues."""
    review = state.ReviewResult(passed=True)
    
    assert review.passed is True
    assert review.issues == []


def test_reviewresult_passed_with_empty_issues_list():
    """Test that ReviewResult with passed=True can have an explicit empty issues list."""
    review = state.ReviewResult(passed=True, issues=[])
    
    assert review.passed is True
    assert review.issues == []


def test_reviewresult_failed_with_issues():
    """Test that a ReviewResult can report failures with specific issues."""
    issues = [
        "Agenda is missing a time for the morning sync.",
        "Action items section has incomplete assignee information."
    ]
    review = state.ReviewResult(passed=False, issues=issues)
    
    assert review.passed is False
    assert len(review.issues) == 2
    assert review.issues[0] == "Agenda is missing a time for the morning sync."
    assert review.issues[1] == "Action items section has incomplete assignee information."


def test_reviewresult_failed_no_issues():
    """Test that ReviewResult can be created with passed=False and no issues."""
    review = state.ReviewResult(passed=False)
    
    assert review.passed is False
    assert review.issues == []


def test_reviewresult_default_factory_issues():
    """Test that the 'issues' field defaults to an empty list via default_factory."""
    review1 = state.ReviewResult(passed=True)
    review2 = state.ReviewResult(passed=True)
    
    # Both should have independent empty lists (not the same object)
    assert review1.issues is not review2.issues
    assert review1.issues == review2.issues == []


def test_reviewresult_single_issue():
    """Test ReviewResult with a single issue."""
    review = state.ReviewResult(
        passed=False,
        issues=["The draft is incomplete."]
    )
    
    assert review.passed is False
    assert len(review.issues) == 1
    assert review.issues[0] == "The draft is incomplete."


# ── AgendaState tests ─────────────────────────────────────────────────────────

def test_agendastate_creation_minimal():
    """Test that a minimal AgendaState can be created with required fields."""
    state_dict: state.AgendaState = {
        "meeting_date": "April 22, 2026",
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
    
    assert state_dict["meeting_date"] == "April 22, 2026"
    assert state_dict["revision_count"] == 0


def test_agendastate_creation_with_data():
    """Test that AgendaState can be created with populated fields."""
    state_dict: state.AgendaState = {
        "meeting_date": "April 25, 2026",
        "notes": [
            {
                "title": "Team sync",
                "date": "April 24, 2026",
                "text": "Discussed project timeline."
            }
        ],
        "agendas": [
            {
                "title": "Previous agenda",
                "date": "April 18, 2026",
                "text": "1. Project updates\n2. Team feedback"
            }
        ],
        "emails": [
            {
                "date": "April 24, 2026",
                "sender": "alice@example.com",
                "subject": "Re: Meeting",
                "body": "Looking forward to the sync."
            }
        ],
        "tasks": [
            {
                "description": "Update documentation",
                "assignee": "Alice",
                "status": "in_progress",
                "evidence": "Mentioned in email"
            }
        ],
        "draft": "# Meeting Agenda\n1. Review progress",
        "review_issues": [],
        "revision_count": 1,
        "doc_url": "https://docs.google.com/document/d/abc123",
        "error": None,
    }
    
    assert state_dict["meeting_date"] == "April 25, 2026"
    assert len(state_dict["notes"]) == 1
    assert len(state_dict["emails"]) == 1
    assert state_dict["revision_count"] == 1
    assert state_dict["doc_url"] is not None


def test_agendastate_with_error():
    """Test that AgendaState can store an error message."""
    state_dict: state.AgendaState = {
        "meeting_date": "April 22, 2026",
        "notes": [],
        "agendas": [],
        "emails": [],
        "tasks": [],
        "draft": "",
        "review_issues": [],
        "revision_count": 0,
        "doc_url": None,
        "error": "Failed to fetch emails from Gmail API.",
    }
    
    assert state_dict["error"] is not None
    assert "Gmail API" in state_dict["error"]


def test_agendastate_review_issues():
    """Test that AgendaState can store review issues."""
    state_dict: state.AgendaState = {
        "meeting_date": "April 22, 2026",
        "notes": [],
        "agendas": [],
        "emails": [],
        "tasks": [],
        "draft": "Draft agenda",
        "review_issues": [
            "Missing agenda time",
            "Incomplete task assignments"
        ],
        "revision_count": 0,
        "doc_url": None,
        "error": None,
    }
    
    assert len(state_dict["review_issues"]) == 2
    assert "Missing agenda time" in state_dict["review_issues"]


def test_agendastate_revision_count():
    """Test that AgendaState tracks revision count correctly."""
    state_dict: state.AgendaState = {
        "meeting_date": "April 22, 2026",
        "notes": [],
        "agendas": [],
        "emails": [],
        "tasks": [],
        "draft": "Revised agenda",
        "review_issues": [],
        "revision_count": 3,
        "doc_url": None,
        "error": None,
    }
    
    assert state_dict["revision_count"] == 3