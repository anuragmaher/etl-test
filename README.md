# ETL Pipeline — Document Ingestion for RAG

ETL pipeline that pulls documents from Google Drive (Google Docs and .docx files), converts them to Markdown, and stores them locally for RAG/AI ingestion.

## Features

- Google Docs and .docx file support
- Google Picker UI for folder selection
- Markdown conversion preserving headings, lists, tables, and inline formatting
- YAML frontmatter (title, source, doc ID, URL, timestamps)
- Sync state tracking — only re-fetches changed documents
- Polling mode or one-shot CLI mode
- Plugin architecture for adding more sources (Confluence, Notion, etc.)

## Setup

### 1. Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable these APIs:
   - Google Docs API
   - Google Drive API
   - Google Picker API
4. Create credentials:
   - **OAuth 2.0 Client ID** (Desktop app) → download as `credentials.json`
   - **API Key** → copy for config

### 2. Install

```bash
pip install -r requirements.txt
```

### 3. Configure

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` and add your API key:

```yaml
api_key: "your-google-api-key"
```

### 4. Run Setup

```bash
python -m etl.main --setup
```

This will:
1. Open your browser for Google OAuth consent (first time only)
2. Launch the Google Picker UI to select folders
3. Save your selection to `config.yaml`

### 5. Sync

```bash
# One-shot sync
python -m etl.main --once

# Continuous polling (default: every 5 minutes)
python -m etl.main
```

Output Markdown files appear in `./output/`.

## Project Structure

```
etl/
├── main.py                  # CLI entry point
├── config.py                # Config loader
├── pipeline.py              # Orchestrator
├── state.py                 # Sync state tracker
├── setup_server.py          # Local server for Google Picker
├── sources/
│   ├── base.py              # Source ABC + DocumentRecord
│   └── google_docs.py       # Google Drive/Docs API integration
├── transform/
│   ├── gdocs_to_markdown.py # Google Docs JSON → Markdown
│   └── docx_to_markdown.py  # .docx → Markdown
├── output/
│   └── markdown_writer.py   # File writer with frontmatter
└── templates/
    └── picker.html          # Google Picker UI
```

## Tests

```bash
pytest tests/
```
