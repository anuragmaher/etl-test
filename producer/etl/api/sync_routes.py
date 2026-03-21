"""Sync trigger, status, and document listing endpoints."""

import json
import logging
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from etl.api.dependencies import get_config, get_google_credentials, reload_config
from etl.api.models import DocumentResponse, SyncStatusResponse
from etl.pipeline import run_once, TRANSFORMER_REGISTRY
from etl.storage.store import is_pinecone_configured, load_pinecone_config

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sync"])

# In-memory sync status
_sync_status = {
    "status": "idle",
    "last_run": None,
    "docs_synced": 0,
    "docs_skipped": 0,
    "error": None,
    "warnings": [],
}
_sync_lock = threading.Lock()


def _run_sync_thread(config: dict):
    """Run sync in a background thread."""
    global _sync_status
    try:
        _sync_status["status"] = "running"
        _sync_status["error"] = None
        _sync_status["warnings"] = []

        # Build Pinecone writer if configured
        pinecone_writer = None
        if is_pinecone_configured():
            try:
                from etl.output.pinecone_writer import PineconeWriter
                pc_config = load_pinecone_config()
                pinecone_writer = PineconeWriter(
                    pinecone_api_key=pc_config["api_key"],
                    index_name=pc_config["index_name"],
                    openai_api_key=pc_config["openai_api_key"],
                )
            except Exception as e:
                warning = f"Pinecone error: {e}. Syncing files only."
                logger.warning(warning)
                _sync_status["warnings"].append(warning)

        stats = run_once(config, pinecone_writer=pinecone_writer)

        # Also sync Notion if configured
        from etl.storage.store import load_notion_config
        notion_config = load_notion_config()
        if notion_config.get("token") and notion_config.get("page_ids"):
            try:
                from etl.sources.notion import NotionSource
                from etl.state import SyncState
                from etl.output import markdown_writer

                notion_source = NotionSource(
                    token=notion_config["token"],
                    page_ids=notion_config["page_ids"],
                )
                state = SyncState(config["state_path"])
                output_dir = config["output_directory"]

                documents = notion_source.list_documents()
                for doc in documents:
                    if not state.needs_sync(doc.source_type, doc.doc_id, doc.modified_time):
                        stats["skipped"] = stats.get("skipped", 0) + 1
                        continue
                    try:
                        full_doc = notion_source.fetch_document(doc.doc_id)
                        transform = TRANSFORMER_REGISTRY.get(full_doc.source_type)
                        if not transform:
                            continue
                        markdown = transform(full_doc.raw_content)
                        markdown_writer.write(
                            output_dir=output_dir,
                            title=full_doc.title,
                            source_type=full_doc.source_type,
                            doc_id=full_doc.doc_id,
                            url=full_doc.url,
                            last_modified=full_doc.modified_time,
                            markdown_content=markdown,
                        )
                        if pinecone_writer:
                            try:
                                pinecone_writer.upsert_document(
                                    doc_id=full_doc.doc_id,
                                    title=full_doc.title,
                                    url=full_doc.url,
                                    source_type=full_doc.source_type,
                                    markdown=markdown,
                                )
                            except Exception:
                                logger.exception("Failed Pinecone upsert for Notion doc '%s'", full_doc.title)
                        state.mark_synced(full_doc.source_type, full_doc.doc_id, full_doc.title, full_doc.modified_time)
                        stats["synced"] = stats.get("synced", 0) + 1
                        logger.info("Synced Notion: %s", full_doc.title)
                    except Exception:
                        logger.exception("Failed to sync Notion doc '%s'", doc.title)
                state.save()
            except Exception as e:
                warning = f"Notion sync error: {e}"
                logger.warning(warning)
                _sync_status["warnings"].append(warning)

        _sync_status["docs_synced"] = stats.get("synced", 0)
        _sync_status["docs_skipped"] = stats.get("skipped", 0)
        _sync_status["last_run"] = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        logger.exception("Sync failed")
        _sync_status["error"] = str(e)
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
