# ETL Pipeline — Document Ingestion for RAG

Producer-consumer ETL pipeline that pulls documents from Google Drive and Notion, converts them to Markdown, generates embeddings, and upserts to Pinecone for RAG/AI ingestion.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  Consumer (React)          http://localhost:5173      │
│  - Google OAuth login                                │
│  - Google Drive file picker (Docs, Sheets, PDF, DOCX)│
│  - Notion integration (pages + databases)            │
│  - Pinecone config form                              │
│  - Dashboard: sync status, document list             │
└──────────────────┬───────────────────────────────────┘
                   │ REST API
┌──────────────────▼───────────────────────────────────┐
│  Producer (Python + FastAPI)  http://localhost:8000   │
│  - Google Drive API (list, download)                 │
│  - Notion API (pages, databases, blocks)             │
│  - Transform: Docs, DOCX, PDF, Sheets, Notion → MD  │
│  - Chunk + embed (OpenAI) + upsert (Pinecone)       │
│  - Sync state tracking (skip unchanged docs)         │
└──────────────────────────────────────────────────────┘
```

## Supported Sources & File Types

### Google Drive
| Type | Source | Conversion |
|------|--------|------------|
| Google Docs | Docs API (JSON) | Headings, lists, tables, inline formatting, multi-tab support |
| .docx | Drive download | python-docx: headings, bold/italic, lists, tables |
| PDF | Drive download | pdfplumber: text + table extraction (no duplication) |
| Google Sheets | Export as .xlsx | openpyxl: each sheet → markdown table |
| .xlsx | Drive download | openpyxl: each sheet → markdown table |

### Notion
| Type | Source | Conversion |
|------|--------|------------|
| Pages | Notion API (blocks) | Headings, paragraphs, lists, to-dos, code, quotes, callouts, toggles, tables, images, bookmarks |
| Databases | Notion API (query) | All rows → markdown table with all property types (text, number, select, date, checkbox, people, etc.) |

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

### 2. Notion Integration (Optional)

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Create a new internal integration
3. Copy the integration token
4. In Notion, share the pages/databases you want to sync with the integration (Share → invite the integration)
5. Paste the token in the Setup page of the consumer app

### 3. Install Producer

```bash
cd producer
pip install -r requirements.txt
cp config.example.yaml config.yaml
# Edit config.yaml and set your api_key
```

### 4. Install Consumer

```bash
cd consumer
npm install
cp .env.example .env
# Edit .env and set VITE_GOOGLE_CLIENT_ID
```

### 5. Run

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

### 6. CLI Mode (alternative)

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
│   │   │   ├── notion_routes.py      # Notion token, page browsing, selection
│   │   │   ├── models.py             # Pydantic schemas
│   │   │   └── dependencies.py       # Shared deps (config, credentials)
│   │   ├── sources/
│   │   │   ├── base.py               # Source ABC + DocumentRecord
│   │   │   ├── google_docs.py        # Google Drive/Docs/Sheets API
│   │   │   └── notion.py             # Notion API (pages, databases, blocks)
│   │   ├── transform/
│   │   │   ├── gdocs_to_markdown.py  # Google Docs JSON → Markdown
│   │   │   ├── docx_to_markdown.py   # .docx → Markdown
│   │   │   ├── pdf_to_markdown.py    # PDF → Markdown
│   │   │   ├── sheet_to_markdown.py  # .xlsx/Sheets → Markdown tables
│   │   │   └── notion_to_markdown.py # Notion blocks/databases → Markdown
│   │   ├── output/
│   │   │   ├── markdown_writer.py    # .md files with YAML frontmatter
│   │   │   ├── pinecone_writer.py    # Chunk → embed → upsert to Pinecone
│   │   │   └── sheet_store.py        # Store sheets as CSV + SQLite for querying
│   │   └── storage/
│   │       └── store.py              # Pinecone + Notion config file I/O
│   └── tests/
│
├── consumer/                         # React frontend
│   ├── src/
│   │   ├── App.tsx                   # Router: login, setup, dashboard
│   │   ├── api.ts                    # REST client for producer API
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx         # Google OAuth redirect
│   │   │   ├── SetupPage.tsx         # File picker + Notion + Pinecone config
│   │   │   └── DashboardPage.tsx     # Sync status + document list + Ask AI panel
│   │   └── components/
│   │       ├── GooglePickerButton.tsx # Google Picker file selection
│   │       ├── NotionSetup.tsx       # Notion connect/browse/select
│   │       ├── FileTreeView.tsx      # Recursive file tree with checkboxes
│   │       ├── PineconeConfigForm.tsx # Pinecone/OpenAI key form
│   │       ├── DocumentList.tsx      # Synced documents table
│   │       ├── SyncStatusBadge.tsx   # Status badge with errors/warnings
│   │       └── AskPanel.tsx          # Chat panel for RAG Q&A
│   └── .env                          # VITE_GOOGLE_CLIENT_ID (gitignored)
```

## API Endpoints

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | /auth/google | Exchange OAuth code for tokens |
| GET | /auth/status | Check authentication status |
| GET | /auth/token | Get access token for Picker |

### Google Drive
| Method | Path | Description |
|--------|------|-------------|
| GET | /folders | List Google Drive folders |
| GET | /folders/{id}/files | Recursively list files in a folder |
| POST | /config/folders | Save selected folder IDs |
| POST | /config/files | Save selected file IDs |

### Notion
| Method | Path | Description |
|--------|------|-------------|
| POST | /notion/token | Save Notion integration token |
| GET | /notion/status | Check if Notion is configured |
| GET | /notion/pages | List all pages/databases shared with integration |
| POST | /notion/pages | Save selected page/database IDs |

### Config & Sync
| Method | Path | Description |
|--------|------|-------------|
| POST | /config/pinecone | Save Pinecone + OpenAI config |
| GET | /config | Get current config (secrets redacted) |
| POST | /sync | Trigger sync in background |
| GET | /sync/status | Sync status, stats, errors, warnings |
| GET | /documents | List synced documents |

### Ask AI
| Method | Path | Description |
|--------|------|-------------|
| POST | /ask | Two-pass Q&A with chat history support |

## Data Flow

### Ingestion
```
Google Drive API ──→ Download (Docs JSON / DOCX / PDF / XLSX)
                        ↓
Notion API ────────→ Fetch blocks / query database
                        ↓
                  Transform to Markdown
                        ↓
                  Write .md file with YAML frontmatter
                        ↓
              ┌─── Unstructured docs ───┐      ┌─── Spreadsheets ──────┐
              │ Chunk (~1000 tokens)    │      │ Store in SQLite       │
              │ Embed (OpenAI)          │      │ Store schema only     │
              │ Upsert full text        │      │ in Pinecone           │
              └─── to Pinecone ─────────┘      └───────────────────────┘
```

### Ask AI (Two-Pass Q&A)
```
User question
    ↓
Pass 0: Resolve follow-ups using chat history → standalone question  [LLM]
    ↓
Pass 1: Embed question → Pinecone search → find relevant source     [deterministic]
    ↓
    ├── Structured data (sheet)?                                     [deterministic routing]
    │     → Pass 2A: LLM generates SQL → execute against SQLite     [LLM + deterministic]
    │     → If SQL fails, retry with fixed query (1 attempt)         [LLM]
    │     → If retry fails, fall back to RAG                         [deterministic]
    │     → LLM generates natural language answer from SQL result    [LLM]
    │
    └── Unstructured data (doc/pdf)?                                 [deterministic routing]
          → Pass 2B: Standard RAG → LLM answers from chunks         [LLM]
```

### Architecture Notes

**The Q&A pipeline is deterministic with LLM-powered steps, not agentic.**

| Component | Type | Description |
|-----------|------|-------------|
| Follow-up resolution (Pass 0) | LLM | Rewrites follow-ups into standalone questions using chat history |
| Source routing (Pass 1) | Deterministic | Routes to SQL or RAG based on `source_type` metadata tag from Pinecone's top match |
| SQL generation (Pass 2A) | LLM | Generates SQLite query from schema + question |
| SQL execution | Deterministic | Runs query against SQLite, returns rows |
| SQL error retry | LLM | One retry — LLM fixes the failed query |
| RAG answer (Pass 2B) | LLM | Generates answer from retrieved text chunks |

The routing between structured (SQL) and unstructured (RAG) paths is a simple `if` check on metadata, not an LLM decision. An agentic approach would let the LLM decide the strategy, chain multiple steps, or combine data from both paths — this is not implemented yet.

## Storage

| File | Purpose |
|------|---------|
| `config.yaml` | Folder IDs, file IDs, polling interval, API key |
| `credentials.json` | Google OAuth client credentials |
| `token.json` | Google OAuth access/refresh tokens |
| `sync_state.json` | Per-document sync state (last modified, synced at) |
| `pinecone_config.json` | Pinecone API key, index name, OpenAI key |
| `notion_config.json` | Notion integration token, selected page IDs |
| `output/*.md` | Converted markdown files with frontmatter |
| `data/sheets.db` | SQLite database with sheet data for structured queries |
| `data/*.csv` | Sheet data exported as CSV files |

## Tests

```bash
cd producer
pytest tests/ -v
```
