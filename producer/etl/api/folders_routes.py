"""Google Drive folder listing endpoint."""

import logging

from fastapi import APIRouter, HTTPException

from etl.api.dependencies import get_config, get_google_credentials
from etl.sources.google_docs import GoogleDocsSource

logger = logging.getLogger(__name__)
router = APIRouter(tags=["folders"])


@router.get("/folders")
async def list_folders():
    """List all folders in the user's Google Drive."""
    try:
        config = get_config()
        creds = get_google_credentials(config)

        source = GoogleDocsSource(
            credentials_path=config["credentials_path"],
            token_path=config["token_path"],
            credentials=creds,
        )
        folders = source.list_folders()
        return {"folders": folders}
    except FileNotFoundError:
        raise HTTPException(status_code=401, detail="Not authenticated")
    except Exception as e:
        logger.exception("Failed to list folders")
        raise HTTPException(status_code=500, detail=str(e))
