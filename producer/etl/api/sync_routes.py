"""Sync trigger, status, and document listing endpoints."""

import json
import logging
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from etl.api.dependencies import get_config, get_google_credentials, reload_config
from etl.api.models import DocumentResponse, SyncStatusResponse
from etl.pipeline import run_once
from etl.storage.store import is_pinecone_configured, load_pinecone_config

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sync"])

# In-memory sync status
_sync_status = {
    "status": "idle",
    "last_run": None,
    "docs_synced": 0,
    "docs_skipped": 0,
}
_sync_lock = threading.Lock()


def _run_sync_thread(config: dict):
    """Run sync in a background thread."""
    global _sync_status
    try:
        _sync_status["status"] = "running"

        # Build Pinecone writer if configured
        pinecone_writer = None
        if is_pinecone_configured():
            from etl.output.pinecone_writer import PineconeWriter
            pc_config = load_pinecone_config()
            pinecone_writer = PineconeWriter(
                pinecone_api_key=pc_config["api_key"],
                index_name=pc_config["index_name"],
                openai_api_key=pc_config["openai_api_key"],
            )

        stats = run_once(config, pinecone_writer=pinecone_writer)

        _sync_status["docs_synced"] = stats.get("synced", 0)
        _sync_status["docs_skipped"] = stats.get("skipped", 0)
        _sync_status["last_run"] = datetime.now(timezone.utc).isoformat()
    except Exception:
        logger.exception("Sync failed")
    finally:
        _sync_status["status"] = "idle"
        _sync_lock.release()


@router.post("/sync")
async def trigger_sync():
    """Trigger a sync cycle in the background."""
    if not _sync_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Sync already in progress")

    config = reload_config()

    thread = threading.Thread(target=_run_sync_thread, args=(config,), daemon=True)
    thread.start()

    return {"status": "started"}


@router.get("/sync/status", response_model=SyncStatusResponse)
async def sync_status():
    """Get current sync status."""
    return SyncStatusResponse(**_sync_status)


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents():
    """List all synced documents from sync state."""
    config = get_config()
    state_path = config["state_path"]

    try:
        with open(state_path) as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    documents = []
    for key, value in state.items():
        parts = key.split("::", 1)
        source_type = parts[0] if len(parts) > 1 else "unknown"
        doc_id = parts[1] if len(parts) > 1 else key

        documents.append(DocumentResponse(
            doc_id=doc_id,
            title=value.get("title", ""),
            source_type=source_type,
            last_modified=value.get("last_modified", ""),
            synced_at=value.get("synced_at", ""),
        ))

    return documents
