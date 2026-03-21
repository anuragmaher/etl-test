"""Google Drive folder and file listing endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from etl.api.dependencies import get_config, get_google_credentials
from etl.sources.google_docs import GoogleDocsSource

logger = logging.getLogger(__name__)
router = APIRouter(tags=["folders"])


def _get_source(config=None):
    if config is None:
        config = get_config()
    creds = get_google_credentials(config)
    return GoogleDocsSource(
        credentials_path=config["credentials_path"],
        token_path=config["token_path"],
        credentials=creds,
    )


@router.get("/folders")
async def list_folders():
    """List all folders in the user's Google Drive."""
    try:
        source = _get_source()
        folders = source.list_folders()
        return {"folders": folders}
    except FileNotFoundError:
        raise HTTPException(status_code=401, detail="Not authenticated")
    except Exception as e:
        logger.exception("Failed to list folders")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/folders/{folder_id}/files")
async def list_folder_files(folder_id: str):
    """Recursively list all files and subfolders under a folder."""
    try:
        source = _get_source()
        tree = source.list_files_recursive(folder_id)
        return {"files": tree}
    except FileNotFoundError:
        raise HTTPException(status_code=401, detail="Not authenticated")
    except Exception as e:
        logger.exception("Failed to list files for folder %s", folder_id)
        raise HTTPException(status_code=500, detail=str(e))
