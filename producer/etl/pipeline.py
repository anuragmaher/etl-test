import logging

from etl.output import markdown_writer
from etl.sources.base import Source
from etl.sources.google_docs import GoogleDocsSource
from etl.state import SyncState
from etl.transform import gdocs_to_markdown
from etl.transform import docx_to_markdown
from etl.transform import pdf_to_markdown
from etl.transform import sheet_to_markdown
from etl.transform import notion_to_markdown

logger = logging.getLogger(__name__)

SOURCE_REGISTRY = {
    "google_docs": GoogleDocsSource,
}

TRANSFORMER_REGISTRY = {
    "google_docs": gdocs_to_markdown.convert,
    "google_docx": docx_to_markdown.convert,
    "google_pdf": pdf_to_markdown.convert,
    "google_sheet": sheet_to_markdown.convert,
    "notion_page": notion_to_markdown.convert,
    "notion_database": notion_to_markdown.convert,
}


def _build_source(name: str, config: dict) -> tuple:
    """Returns (source, file_ids) where file_ids is a list if specific files are selected, else None."""
    cls = SOURCE_REGISTRY[name]
    if name == "google_docs":
        source_config = config["sources"].get("google_docs", {})
        source = cls(
            credentials_path=config["credentials_path"],
            token_path=config["token_path"],
            folder_ids=source_config.get("folder_ids", []),
        )
        file_ids = source_config.get("file_ids", []) or None
        return source, file_ids
    raise ValueError(f"Unknown source: {name}")


def run_once(config: dict, pinecone_writer=None) -> dict:
    """Run a single sync cycle. Returns stats dict with 'synced' and 'skipped' counts."""
    state = SyncState(config["state_path"])
    output_dir = config["output_directory"]
    total_synced = 0
    total_skipped = 0

    for source_name, source_config in config["sources"].items():
        if not source_config.get("enabled", False):
            continue

        if source_name not in SOURCE_REGISTRY:
            logger.warning("Unknown source '%s', skipping", source_name)
            continue

        logger.info("Processing source: %s", source_name)
        source, file_ids = _build_source(source_name, config)

        if file_ids:
            # Sync only specific selected files
            documents = []
            for fid in file_ids:
                try:
                    doc = source.fetch_document(fid)
                    documents.append(doc)
                except Exception:
                    logger.exception("Failed to fetch file %s", fid)
        else:
            documents = source.list_documents()
        synced = 0
        skipped = 0

        for doc in documents:
            if not state.needs_sync(doc.source_type, doc.doc_id, doc.modified_time):
                skipped += 1
                continue

            try:
                full_doc = doc if doc.raw_content is not None else source.fetch_document(doc.doc_id)
                transform = TRANSFORMER_REGISTRY.get(full_doc.source_type)
                if not transform:
                    logger.warning("No transformer for type '%s', skipping %s", full_doc.source_type, full_doc.title)
                    continue
                markdown = transform(full_doc.raw_content)
                filepath = markdown_writer.write(
                    output_dir=output_dir,
                    title=full_doc.title,
                    source_type=full_doc.source_type,
                    doc_id=full_doc.doc_id,
                    url=full_doc.url,
                    last_modified=full_doc.modified_time,
                    markdown_content=markdown,
                )
                # Upsert to Pinecone if configured
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
                        logger.exception("Failed to upsert to Pinecone: '%s'", full_doc.title)

                state.mark_synced(
                    full_doc.source_type,
                    full_doc.doc_id,
                    full_doc.title,
                    full_doc.modified_time,
                )
                synced += 1
                logger.info("Synced: %s -> %s", full_doc.title, filepath)
            except Exception:
                logger.exception("Failed to sync document '%s' (%s)", doc.title, doc.doc_id)

        total_synced += synced
        total_skipped += skipped
        logger.info(
            "Source '%s' complete: %d synced, %d skipped (unchanged)",
            source_name, synced, skipped,
        )

    state.save()
    return {"synced": total_synced, "skipped": total_skipped}
