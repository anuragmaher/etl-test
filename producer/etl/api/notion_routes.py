"""Notion configuration and page browsing endpoints."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from etl.storage.store import load_notion_config, save_notion_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notion", tags=["notion"])


class NotionTokenRequest(BaseModel):
    token: str


class NotionPageSelection(BaseModel):
    page_ids: list[str]


@router.post("/token")
async def save_notion_token(request: NotionTokenRequest):
    """Save Notion integration token."""
    # Validate by trying to search
    try:
        from notion_client import Client
        client = Client(auth=request.token)
        client.search(page_size=1)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Notion token: {e}")

    save_notion_config({"token": request.token})
    logger.info("Notion token saved")
    return {"status": "ok"}


@router.get("/status")
async def notion_status():
    """Check if Notion is configured."""
    config = load_notion_config()
    return {"configured": bool(config.get("token"))}


@router.get("/pages")
async def list_notion_pages():
    """List all pages and databases the integration has access to."""
    config = load_notion_config()
    token = config.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Notion not configured. Save a token first.")

    try:
        from etl.sources.notion import NotionSource
        source = NotionSource(token=token)
        items = source.search_pages()
        return {"items": items}
    except Exception as e:
        logger.exception("Failed to list Notion pages")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pages")
async def save_notion_pages(selection: NotionPageSelection):
    """Save selected Notion page/database IDs."""
    config = load_notion_config()
    config["page_ids"] = selection.page_ids
    save_notion_config(config)
    logger.info("Saved %d Notion page IDs", len(selection.page_ids))
    return {"status": "ok", "count": len(selection.page_ids)}
