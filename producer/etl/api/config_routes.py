"""Configuration endpoints for folders and Pinecone."""

import logging

import yaml
from fastapi import APIRouter, HTTPException

from etl.api.dependencies import get_config, reload_config
from etl.api.models import ConfigResponse, FileSelection, FolderSelection, PineconeConfig
from etl.storage.store import is_pinecone_configured, load_pinecone_config, save_pinecone_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=ConfigResponse)
async def get_current_config():
    """Get current configuration (secrets redacted)."""
    config = get_config()
    source_config = config.get("sources", {}).get("google_docs", {})
    return ConfigResponse(
        folder_ids=source_config.get("folder_ids", []),
        file_ids=source_config.get("file_ids", []),
        pinecone_configured=is_pinecone_configured(),
        output_directory=config.get("output_directory", "./output"),
    )


@router.post("/folders")
async def save_folders(selection: FolderSelection):
    """Save selected Google Drive folder IDs to config."""
    config_path = "config.yaml"
    try:
        with open(config_path) as f:
            raw_config = yaml.safe_load(f) or {}
    except FileNotFoundError:
        raw_config = {}

    if "sources" not in raw_config:
        raw_config["sources"] = {}
    if "google_docs" not in raw_config["sources"]:
        raw_config["sources"]["google_docs"] = {}

    raw_config["sources"]["google_docs"]["enabled"] = True
    raw_config["sources"]["google_docs"]["folder_ids"] = selection.folder_ids

    with open(config_path, "w") as f:
        yaml.dump(raw_config, f, default_flow_style=False, sort_keys=False)

    reload_config()
    logger.info("Saved %d folder IDs to config", len(selection.folder_ids))
    return {"status": "ok", "folder_count": len(selection.folder_ids)}


@router.post("/files")
async def save_files(selection: FileSelection):
    """Save selected file IDs to sync."""
    config_path = "config.yaml"
    try:
        with open(config_path) as f:
            raw_config = yaml.safe_load(f) or {}
    except FileNotFoundError:
        raw_config = {}

    if "sources" not in raw_config:
        raw_config["sources"] = {}
    if "google_docs" not in raw_config["sources"]:
        raw_config["sources"]["google_docs"] = {}

    raw_config["sources"]["google_docs"]["enabled"] = True
    raw_config["sources"]["google_docs"]["file_ids"] = selection.file_ids

    with open(config_path, "w") as f:
        yaml.dump(raw_config, f, default_flow_style=False, sort_keys=False)

    reload_config()
    logger.info("Saved %d file IDs to config", len(selection.file_ids))
    return {"status": "ok", "file_count": len(selection.file_ids)}


@router.post("/pinecone")
async def save_pinecone(config: PineconeConfig):
    """Save Pinecone configuration."""
    try:
        save_pinecone_config({
            "api_key": config.api_key,
            "index_name": config.index_name,
            "openai_api_key": config.openai_api_key,
        })
        logger.info("Pinecone config saved (index: %s)", config.index_name)
        return {"status": "ok"}
    except Exception as e:
        logger.exception("Failed to save Pinecone config")
        raise HTTPException(status_code=500, detail=str(e))
