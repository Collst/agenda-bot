"""
auth/google.py — Google OAuth2 credential management.

Scopes:
  - Drive: read (fetch docs) + write (create output doc)
  - Gmail: read-only
  - Docs:  read + write
"""

import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def get_credentials() -> Credentials:
    """
    Return valid Google credentials.

    On first call: opens a browser tab for OAuth authorisation and saves
    token.json for future calls.  Subsequent calls reload and auto-refresh
    the saved token.
    """
    token_path = os.getenv("TOKEN_PATH", "token.json")
    secrets_path = os.getenv("CLIENT_SECRETS_PATH", "credentials.json")

    creds: Credentials | None = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(secrets_path):
                raise FileNotFoundError(
                    f"Google credentials file not found at '{secrets_path}'.\n"
                    "See README.md → Setup → Step 2."
                )
            flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return creds
