"""Google OAuth web flow endpoints."""

import json
import logging
import os

import httpx
from fastapi import APIRouter, HTTPException

from etl.api.dependencies import get_config, get_google_credentials
from etl.api.models import AuthStatusResponse, GoogleAuthRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google")
async def exchange_google_code(request: GoogleAuthRequest):
    """Exchange authorization code for tokens and store server-side."""
    config = get_config()
    creds_path = config["credentials_path"]

    if not os.path.exists(creds_path):
        raise HTTPException(status_code=500, detail="credentials.json not found on server")

    with open(creds_path) as f:
        creds_data = json.load(f)

    creds_info = creds_data.get("web") or creds_data.get("installed", {})
    client_id = creds_info.get("client_id")
    client_secret = creds_info.get("client_secret")

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": request.code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": request.redirect_uri,
                "grant_type": "authorization_code",
            },
        )

    if response.status_code != 200:
        logger.error("Token exchange failed: %s", response.text)
        raise HTTPException(status_code=400, detail="Failed to exchange authorization code")

    token_data = response.json()

    # Save tokens in the format google-auth expects
    token_json = {
        "token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token"),
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": [
            "https://www.googleapis.com/auth/documents.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ],
    }

    token_path = config["token_path"]
    with open(token_path, "w") as f:
        json.dump(token_json, f, indent=2)

    logger.info("Google OAuth tokens saved")
    return {"status": "ok"}


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status():
    """Check if valid Google credentials exist."""
    try:
        creds = get_google_credentials()
        # Try to get user email from userinfo
        email = None
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {creds.token}"},
                )
                if resp.status_code == 200:
                    email = resp.json().get("email")
        except Exception:
            pass
        return AuthStatusResponse(authenticated=True, email=email)
    except Exception:
        return AuthStatusResponse(authenticated=False)


@router.get("/token")
async def get_access_token():
    """Return the current access token (for Google Picker in frontend)."""
    try:
        creds = get_google_credentials()
        config = get_config()

        # Also return API key and client ID for the picker
        with open(config["credentials_path"]) as f:
            creds_data = json.load(f)
        creds_info = creds_data.get("web") or creds_data.get("installed", {})

        return {
            "access_token": creds.token,
            "api_key": config.get("api_key", ""),
            "client_id": creds_info.get("client_id", ""),
            "app_id": creds_info.get("project_id", ""),
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
