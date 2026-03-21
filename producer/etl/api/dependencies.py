"""Shared FastAPI dependencies."""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from etl.config import load_config

SCOPES = [
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

_config = None


def get_config() -> dict:
    global _config
    if _config is None:
        _config = load_config("config.yaml")
    return _config


def reload_config():
    global _config
    _config = load_config("config.yaml")
    return _config


def get_google_credentials(config: dict = None) -> Credentials:
    """Load and refresh Google credentials from token.json."""
    if config is None:
        config = get_config()

    token_path = config["token_path"]
    if not os.path.exists(token_path):
        raise FileNotFoundError("Not authenticated. Please sign in with Google first.")

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    if not creds or not creds.valid:
        raise ValueError("Google credentials are invalid. Please re-authenticate.")

    return creds
