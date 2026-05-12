"""
services/gmail.py — Fetch committee emails from Gmail.

Filtering strategy:
  1. Label-based  (GMAIL_LABEL env var) — threads tagged with a Gmail label
  2. Participant  (COMMITTEE_EMAILS env var) — threads from known addresses
Both can be active simultaneously; results are de-duplicated by thread ID.
"""

import os
import base64
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from dotenv import load_dotenv
from auth.google import get_credentials

load_dotenv()

MAX_BODY_CHARS = 2_000   # per message — trim long threads to keep prompt compact


def _gmail_service():
    return build("gmail", "v1", credentials=get_credentials(), cache_discovery=False)


def _decode_body(payload: dict) -> str:
    """Recursively extract plain-text body from a Gmail message payload."""
    mime = payload.get("mimeType", "")

    if mime == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

    if mime.startswith("multipart/"):
        for part in payload.get("parts", []):
            text = _decode_body(part)
            if text:
                return text

    return ""


def _build_query(since_date: str) -> str:
    """Build a Gmail search query from env config and a since-date string."""
    parts = [f"after:{since_date}"]

    label = os.getenv("GMAIL_LABEL", "").strip()
    if label:
        parts.append(f"label:{label}")

    raw_emails = os.getenv("COMMITTEE_EMAILS", "").strip()
    if raw_emails:
        addresses = [e.strip() for e in raw_emails.split(",") if e.strip()]
        if addresses:
            parts.append("(" + " OR ".join(f"from:{a}" for a in addresses) + ")")

    return " ".join(parts)


def fetch_committee_emails() -> list[dict]:
    """
    Return a list of email summaries for the configured lookback window,
    sorted oldest-first.

    Each item: { "date": str, "sender": str, "subject": str, "body": str }
    """
    lookback = int(os.getenv("EMAIL_LOOKBACK_DAYS", 35))
    since_dt = datetime.now(timezone.utc) - timedelta(days=lookback)
    since_str = since_dt.strftime("%Y/%m/%d")

    service = _gmail_service()
    query = _build_query(since_str)

    # Page through all matching threads
    thread_ids: set[str] = set()
    page_token = None
    while True:
        kwargs: dict = {"userId": "me", "q": query, "maxResults": 100}
        if page_token:
            kwargs["pageToken"] = page_token
        resp = service.users().threads().list(**kwargs).execute()
        for t in resp.get("threads", []):
            thread_ids.add(t["id"])
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    emails = []
    for tid in thread_ids:
        thread = (
            service.users()
            .threads()
            .get(userId="me", id=tid, format="full")
            .execute()
        )
        for msg in thread.get("messages", []):
            headers = {
                h["name"]: h["value"]
                for h in msg["payload"].get("headers", [])
            }
            body = _decode_body(msg["payload"])
            body_trimmed = (
                body[:MAX_BODY_CHARS] + "…" if len(body) > MAX_BODY_CHARS else body
            )
            emails.append(
                {
                    "date": headers.get("Date", ""),
                    "sender": headers.get("From", ""),
                    "subject": headers.get("Subject", "(no subject)"),
                    "body": body_trimmed.strip(),
                }
            )

    emails.sort(key=lambda e: e["date"])
    return emails
