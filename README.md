# ETL Pipeline — Document Ingestion for RAG

Producer-consumer ETL pipeline that pulls documents from Google Drive, converts them to Markdown, generates embeddings, and upserts to Pinecone for RAG/AI ingestion.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  Consumer (React)          http://localhost:5173      │
│  - Google OAuth login                                │
│  - Folder picker + file tree with checkboxes         │
│  - Pinecone config form                              │
│  - Dashboard: sync status, document list             │
└──────────────────┬───────────────────────────────────┘
                   │ REST API
┌──────────────────▼───────────────────────────────────┐
│  Producer (Python + FastAPI)  http://localhost:8000   │
│  - Google Drive API (list, download)                 │
│  - Transform: Docs, DOCX, PDF, Sheets → Markdown    │
│  - Chunk + embed (OpenAI) + upsert (Pinecone)       │
│  - Sync state tracking (skip unchanged docs)         │
└──────────────────────────────────────────────────────┘
```

## Supported File Types

| Type | Source | Conversion |
|------|--------|------------|
| Google Docs | Docs API (JSON) | Headings, lists, tables, inline formatting, multi-tab support |
| .docx | Drive download | python-docx: headings, bold/italic, lists, tables |
| PDF | Drive download | pdfplumber: text + table extraction |
| Google Sheets | Export as .xlsx | openpyxl: each sheet → markdown table |
| .xlsx | Drive download | openpyxl: each sheet → markdown table |

## Setup

### 1. Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable these APIs:
   - Google Docs API
   - Google Drive API
   - Google Picker API
4. Create credentials:
   - **OAuth 2.0 Client ID** (Web application) → download as `credentials.json`, place in `producer/`
   - Add `http://localhost:5173/auth/callback` as an authorized redirect URI
   - **API Key** → add to `producer/config.yaml`

### 2. Install Producer

```bash
cd producer
pip install -r requirements.txt
cp config.example.yaml config.yaml
# Edit config.yaml and set your api_key
```

### 3. Install Consumer

```bash
cd consumer
npm install
cp .env.example .env
# Edit .env and set VITE_GOOGLE_CLIENT_ID
```

### 4. Run

**Terminal 1 — Producer:**
```bash
cd producer
python3 -m uvicorn etl.api.app:app --port 8000
```

**Terminal 2 — Consumer:**
```bash
cd consumer
npm run dev
```

Open http://localhost:5173 → Login → Setup → Dashboard → Sync

### 5. CLI Mode (alternative)

The producer also works as a standalone CLI:

```bash
cd producer
python -m etl.main --setup   # Interactive folder picker
python -m etl.main --once    # One-shot sync
python -m etl.main           # Continuous polling (every 5 minutes)
```

## Project Structure

```
├── producer/                         # Python ETL + FastAPI
│   ├── config.yaml                   # Runtime config (gitignored)
│   ├── config.example.yaml           # Config template
│   ├── credentials.json              # Google OAuth credentials (gitignored)
│   ├── requirements.txt
│   ├── etl/
│   │   ├── main.py                   # CLI entry point
│   │   ├── config.py                 # YAML config loader
│   │   ├── pipeline.py               # Orchestrator: list → filter → fetch → transform → write → embed
│   │   ├── state.py                  # Sync state tracker (sync_state.json)
│   │   ├── api/
│   │   │   ├── app.py                # FastAPI app with CORS
│   │   │   ├── auth.py               # Google OAuth web flow
│   │   │   ├── config_routes.py      # Folder/file/Pinecone config endpoints
│   │   │   ├── sync_routes.py        # Sync trigger, status, document list
│   │   │   ├── folders_routes.py     # Folder listing + recursive file tree
│   │   │   ├── models.py             # Pydantic schemas
│   │   │   └── dependencies.py       # Shared deps (config, credentials)
│   │   ├── sources/
│   │   │   ├── base.py               # Source ABC + DocumentRecord
│   │   │   └── google_docs.py        # Google Drive/Docs/Sheets API
│   │   ├── transform/
│   │   │   ├── gdocs_to_markdown.py  # Google Docs JSON → Markdown
│   │   │   ├── docx_to_markdown.py   # .docx → Markdown
│   │   │   ├── pdf_to_markdown.py    # PDF → Markdown
│   │   │   └── sheet_to_markdown.py  # .xlsx/Sheets → Markdown tables
│   │   ├── output/
│   │   │   ├── markdown_writer.py    # .md files with YAML frontmatter
│   │   │   └── pinecone_writer.py    # Chunk → embed → upsert to Pinecone
│   │   └── storage/
│   │       └── store.py              # Pinecone config file I/O
│   └── tests/
│
├── consumer/                         # React frontend
│   ├── src/
│   │   ├── App.tsx                   # Router: login, setup, dashboard
│   │   ├── api.ts                    # REST client for producer API
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx         # Google OAuth redirect
│   │   │   ├── SetupPage.tsx         # Folder picker + file tree + Pinecone config
│   │   │   └── DashboardPage.tsx     # Sync status + document list
│   │   └── components/
│   │       ├── GooglePickerButton.tsx # Google Picker integration
│   │       ├── FileTreeView.tsx      # Recursive file tree with checkboxes
│   │       ├── PineconeConfigForm.tsx # Pinecone/OpenAI key form
│   │       ├── DocumentList.tsx      # Synced documents table
│   │       └── SyncStatusBadge.tsx   # Status badge with errors/warnings
│   └── .env                          # VITE_GOOGLE_CLIENT_ID (gitignored)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /auth/google | Exchange OAuth code for tokens |
| GET | /auth/status | Check authentication status |
| GET | /auth/token | Get access token for Picker |
| GET | /folders | List Google Drive folders |
| GET | /folders/{id}/files | Recursively list files in a folder |
| POST | /config/folders | Save selected folder IDs |
| POST | /config/files | Save selected file IDs |
| POST | /config/pinecone | Save Pinecone + OpenAI config |
| GET | /config | Get current config (secrets redacted) |
| POST | /sync | Trigger sync in background |
| GET | /sync/status | Sync status, stats, errors, warnings |
| GET | /documents | List synced documents |

## Data Flow

```
Google Drive API → Download (Docs JSON / DOCX / PDF / XLSX bytes)
    → Transform to Markdown
    → Write .md file with YAML frontmatter
    → Chunk (~1000 tokens, 200 overlap)
    → Embed (OpenAI text-embedding-3-large, 3072 dims)
    → Upsert to Pinecone (metadata: doc_id, title, url, source_type, text)
```

## Storage

| File | Purpose |
|------|---------|
| `config.yaml` | Folder IDs, file IDs, polling interval, API key |
| `credentials.json` | Google OAuth client credentials |
| `token.json` | Google OAuth access/refresh tokens |
| `sync_state.json` | Per-document sync state (last modified, synced at) |
| `pinecone_config.json` | Pinecone API key, index name, OpenAI key |
| `output/*.md` | Converted markdown files with frontmatter |

## Tests

```bash
cd producer
pytest tests/ -v
```
