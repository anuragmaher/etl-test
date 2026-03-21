"""Notion source adapter — list and fetch pages and databases."""

import logging
from typing import List

from notion_client import Client

from etl.sources.base import DocumentRecord, Source

logger = logging.getLogger(__name__)


class NotionSource(Source):
    def __init__(self, token: str, page_ids: list = None):
        self._client = Client(auth=token)
        self._page_ids = page_ids or []

    def search_pages(self) -> list:
        """Search all pages and databases the integration has access to.
        Returns a tree-friendly list of {id, title, type, icon}.
        """
        results = []
        start_cursor = None

        while True:
            params = {"page_size": 100}
            if start_cursor:
                params["start_cursor"] = start_cursor

            response = self._client.search(**params)

            for item in response.get("results", []):
                obj_type = item.get("object")  # "page" or "database"
                item_id = item["id"]

                # Extract title
                title = ""
                if obj_type == "page":
                    props = item.get("properties", {})
                    for prop in props.values():
                        if prop.get("type") == "title":
                            title_parts = prop.get("title", [])
                            title = "".join(t.get("plain_text", "") for t in title_parts)
                            break
                    if not title:
                        title = "Untitled"
                elif obj_type == "database":
                    title_parts = item.get("title", [])
                    title = "".join(t.get("plain_text", "") for t in title_parts)
                    if not title:
                        title = "Untitled Database"

                # Extract icon
                icon = ""
                icon_data = item.get("icon")
                if icon_data:
                    if icon_data.get("type") == "emoji":
                        icon = icon_data.get("emoji", "")

                results.append({
                    "id": item_id,
                    "title": title,
                    "type": obj_type,
                    "icon": icon,
                    "last_edited": item.get("last_edited_time", ""),
                    "url": item.get("url", ""),
                })

            if not response.get("has_more"):
                break
            start_cursor = response.get("next_cursor")

        logger.info("Found %d Notion items (%d pages, %d databases)",
                     len(results),
                     sum(1 for r in results if r["type"] == "page"),
                     sum(1 for r in results if r["type"] == "database"))
        return results

    def list_documents(self) -> List[DocumentRecord]:
        """List documents for configured page IDs."""
        documents = []
        for page_id in self._page_ids:
            try:
                page = self._client.pages.retrieve(page_id=page_id)
                title = self._extract_title(page)
                documents.append(DocumentRecord(
                    source_type="notion_page",
                    doc_id=page_id,
                    title=title,
                    modified_time=page.get("last_edited_time", ""),
                    url=page.get("url", ""),
                ))
            except Exception:
                # Could be a database
                try:
                    db = self._client.databases.retrieve(database_id=page_id)
                    title_parts = db.get("title", [])
                    title = "".join(t.get("plain_text", "") for t in title_parts) or "Untitled Database"
                    documents.append(DocumentRecord(
                        source_type="notion_database",
                        doc_id=page_id,
                        title=title,
                        modified_time=db.get("last_edited_time", ""),
                        url=db.get("url", ""),
                    ))
                except Exception:
                    logger.exception("Failed to retrieve Notion item %s", page_id)

        return documents

    def fetch_document(self, doc_id: str) -> DocumentRecord:
        """Fetch full content for a Notion page or database."""
        # Try as page first
        try:
            page = self._client.pages.retrieve(page_id=doc_id)
            title = self._extract_title(page)
            blocks = self._fetch_all_blocks(doc_id)
            return DocumentRecord(
                source_type="notion_page",
                doc_id=doc_id,
                title=title,
                modified_time=page.get("last_edited_time", ""),
                url=page.get("url", ""),
                raw_content={"type": "page", "blocks": blocks},
            )
        except Exception:
            pass

        # Try as database
        db = self._client.databases.retrieve(database_id=doc_id)
        title_parts = db.get("title", [])
        title = "".join(t.get("plain_text", "") for t in title_parts) or "Untitled Database"
        rows = self._fetch_database_rows(doc_id, db)
        return DocumentRecord(
            source_type="notion_database",
            doc_id=doc_id,
            title=title,
            modified_time=db.get("last_edited_time", ""),
            url=db.get("url", ""),
            raw_content={"type": "database", "rows": rows, "properties": db.get("properties", {})},
        )

    def _extract_title(self, page: dict) -> str:
        props = page.get("properties", {})
        for prop in props.values():
            if prop.get("type") == "title":
                title_parts = prop.get("title", [])
                return "".join(t.get("plain_text", "") for t in title_parts)
        return "Untitled"

    def _fetch_all_blocks(self, block_id: str) -> list:
        """Recursively fetch all blocks under a page/block."""
        blocks = []
        start_cursor = None

        while True:
            params = {"block_id": block_id, "page_size": 100}
            if start_cursor:
                params["start_cursor"] = start_cursor

            response = self._client.blocks.children.list(**params)

            for block in response.get("results", []):
                if block.get("has_children"):
                    block["children"] = self._fetch_all_blocks(block["id"])
                blocks.append(block)

            if not response.get("has_more"):
                break
            start_cursor = response.get("next_cursor")

        return blocks

    def _fetch_database_rows(self, db_id: str, db_meta: dict) -> list:
        """Fetch all rows from a database."""
        rows = []
        start_cursor = None

        while True:
            params = {"database_id": db_id, "page_size": 100}
            if start_cursor:
                params["start_cursor"] = start_cursor

            response = self._client.databases.query(**params)

            for page in response.get("results", []):
                row = {}
                for prop_name, prop_value in page.get("properties", {}).items():
                    row[prop_name] = self._extract_property_value(prop_value)
                rows.append(row)

            if not response.get("has_more"):
                break
            start_cursor = response.get("next_cursor")

        return rows

    def _extract_property_value(self, prop: dict) -> str:
        """Extract a readable string from a Notion property value."""
        ptype = prop.get("type", "")

        if ptype == "title":
            return "".join(t.get("plain_text", "") for t in prop.get("title", []))
        elif ptype == "rich_text":
            return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
        elif ptype == "number":
            val = prop.get("number")
            return str(val) if val is not None else ""
        elif ptype == "select":
            sel = prop.get("select")
            return sel.get("name", "") if sel else ""
        elif ptype == "multi_select":
            return ", ".join(s.get("name", "") for s in prop.get("multi_select", []))
        elif ptype == "date":
            date = prop.get("date")
            if date:
                start = date.get("start", "")
                end = date.get("end", "")
                return f"{start} → {end}" if end else start
            return ""
        elif ptype == "checkbox":
            return "Yes" if prop.get("checkbox") else "No"
        elif ptype == "url":
            return prop.get("url", "") or ""
        elif ptype == "email":
            return prop.get("email", "") or ""
        elif ptype == "phone_number":
            return prop.get("phone_number", "") or ""
        elif ptype == "status":
            status = prop.get("status")
            return status.get("name", "") if status else ""
        elif ptype == "people":
            return ", ".join(p.get("name", "") for p in prop.get("people", []))
        elif ptype == "relation":
            return ", ".join(r.get("id", "") for r in prop.get("relation", []))
        elif ptype == "formula":
            formula = prop.get("formula", {})
            ftype = formula.get("type", "")
            return str(formula.get(ftype, ""))
        elif ptype == "rollup":
            rollup = prop.get("rollup", {})
            rtype = rollup.get("type", "")
            return str(rollup.get(rtype, ""))
        else:
            return ""
