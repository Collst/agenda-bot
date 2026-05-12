"""
services/google_docs.py — Fetch content from tabbed Google Docs and write output docs.

Your notes and agenda docs use Google's native tabs feature:
  - Top-level tabs:  one per year  (e.g. "2025", "2026")
  - Nested sub-tabs: one per meeting  (e.g. "09/23/26", "10/30/26")

This module:
  1. Fetches the full tabbed document with includeTabsContent=True
  2. Locates the year tab(s) covering the lookback window
  3. Extracts text from each meeting sub-tab, most-recent first
  4. Provides a helper to create a new Google Doc in a target folder
"""

import os
import re
from datetime import datetime
from typing import Optional
from googleapiclient.discovery import build
from dotenv import load_dotenv
from auth.google import get_credentials

load_dotenv()

# Date patterns we expect in sub-tab titles: "09/23/26", "09/23/2026", "2026-09-23"
_DATE_PATTERNS = [
    r"(\d{1,2})/(\d{1,2})/(\d{2,4})",   # MM/DD/YY or MM/DD/YYYY
    r"(\d{4})-(\d{1,2})-(\d{1,2})",       # YYYY-MM-DD
]


def _docs_service():
    return build("docs", "v1", credentials=get_credentials(), cache_discovery=False)


def _drive_service():
    return build("drive", "v3", credentials=get_credentials(), cache_discovery=False)


# ── Text extraction ────────────────────────────────────────────────────────────

def _extract_text_from_body(body: dict) -> str:
    """Walk a documentTab body and return plain text."""
    parts = []
    for element in body.get("content", []):
        para = element.get("paragraph")
        if not para:
            continue
        line = ""
        for run in para.get("elements", []):
            text_run = run.get("textRun")
            if text_run:
                line += text_run.get("content", "")
        parts.append(line)
    return "".join(parts).strip()


# ── Tab parsing ────────────────────────────────────────────────────────────────

def _parse_tab_date(title: str) -> Optional[datetime]:
    """Try to parse a meeting date from a sub-tab title. Returns None if unparseable."""
    for pattern in _DATE_PATTERNS:
        m = re.search(pattern, title)
        if not m:
            continue
        groups = m.groups()
        try:
            if "-" in pattern:
                # YYYY-MM-DD
                return datetime(int(groups[0]), int(groups[1]), int(groups[2]))
            else:
                # MM/DD/YY or MM/DD/YYYY
                year = int(groups[2])
                if year < 100:
                    year += 2000
                return datetime(year, int(groups[0]), int(groups[1]))
        except ValueError:
            continue
    return None


def _collect_meeting_tabs(tabs: list[dict]) -> list[dict]:
    """
    Recursively walk the tab tree and return all leaf tabs (meeting tabs)
    that have a parseable date in their title, sorted most-recent first.

    Each returned item: { "title": str, "date": datetime, "body": dict }
    """
    results = []

    for tab in tabs:
        props = tab.get("tabProperties", {})
        title = props.get("title", "")
        child_tabs = tab.get("childTabs", [])

        # Recurse into children first
        if child_tabs:
            results.extend(_collect_meeting_tabs(child_tabs))

        # A leaf tab with a parseable date is a meeting tab
        doc_tab = tab.get("documentTab")
        if doc_tab and not child_tabs:
            parsed_date = _parse_tab_date(title)
            if parsed_date:
                results.append(
                    {
                        "title": title,
                        "date": parsed_date,
                        "body": doc_tab.get("body", {}),
                    }
                )

    results.sort(key=lambda t: t["date"], reverse=True)
    return results


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_recent_tabs(doc_id: str, n: int) -> list[dict]:
    """
    Return the `n` most recent meeting tabs from a tabbed Google Doc.

    Each item: { "title": str, "date": datetime, "text": str }
    """
    service = _docs_service()
    doc = (
        service.documents()
        .get(documentId=doc_id, includeTabsContent=True)
        .execute()
    )

    all_tabs = doc.get("tabs", [])
    meeting_tabs = _collect_meeting_tabs(all_tabs)

    results = []
    for tab in meeting_tabs[:n]:
        text = _extract_text_from_body(tab["body"])
        if text:  # skip empty tabs
            results.append(
                {
                    "title": tab["title"],
                    "date": tab["date"].strftime("%Y-%m-%d"),
                    "text": text,
                }
            )
    return results


def fetch_meeting_notes(n: Optional[int] = None) -> list[dict]:
    """Return the n most recent meeting note tabs."""
    n = n or int(os.getenv("NOTES_TABS_TO_INCLUDE", 3))
    doc_id = os.getenv("NOTES_DOC_ID")
    if not doc_id:
        raise ValueError("NOTES_DOC_ID is not set in your .env file.")
    return fetch_recent_tabs(doc_id, n)


def fetch_agendas(n: Optional[int] = None) -> list[dict]:
    """Return the n most recent agenda tabs (used as format examples)."""
    n = n or int(os.getenv("AGENDA_TABS_TO_INCLUDE", 2))
    doc_id = os.getenv("AGENDAS_DOC_ID")
    if not doc_id:
        raise ValueError("AGENDAS_DOC_ID is not set in your .env file.")
    return fetch_recent_tabs(doc_id, n)


# ── Output doc creation ────────────────────────────────────────────────────────

def create_agenda_doc(agenda_text: str, meeting_date: str = "") -> str:
    """
    Create a new Google Doc containing the agenda text.
    Places it in OUTPUT_FOLDER_ID and returns the document URL.
    """
    output_folder = os.getenv("OUTPUT_FOLDER_ID")
    if not output_folder:
        raise ValueError("OUTPUT_FOLDER_ID is not set in your .env file.")

    date_label = meeting_date or datetime.now().strftime("%B %d, %Y")
    title = f"DRAFT Agenda – {date_label}"

    docs = _docs_service()
    drive = _drive_service()

    # Create empty doc
    doc = docs.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    # Insert agenda text at position 1 (after the implicit title element)
    docs.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {"insertText": {"location": {"index": 1}, "text": agenda_text}}
            ]
        },
    ).execute()

    # Move into the output folder
    file_meta = drive.files().get(fileId=doc_id, fields="parents").execute()
    current_parents = ",".join(file_meta.get("parents", []))
    drive.files().update(
        fileId=doc_id,
        addParents=output_folder,
        removeParents=current_parents,
        fields="id, parents",
    ).execute()

    return f"https://docs.google.com/document/d/{doc_id}/edit"
