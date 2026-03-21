from pydantic import BaseModel
from typing import Optional


class GoogleAuthRequest(BaseModel):
    code: str
    redirect_uri: str


class AuthStatusResponse(BaseModel):
    authenticated: bool
    email: Optional[str] = None


class FolderSelection(BaseModel):
    folder_ids: list[str]


class FileSelection(BaseModel):
    file_ids: list[str]


class PineconeConfig(BaseModel):
    api_key: str
    index_name: str
    openai_api_key: str


class ConfigResponse(BaseModel):
    folder_ids: list[str]
    file_ids: list[str]
    pinecone_configured: bool
    output_directory: str


class SyncStatusResponse(BaseModel):
    status: str  # "running" or "idle"
    last_run: Optional[str] = None
    docs_synced: int = 0
    docs_skipped: int = 0
    error: Optional[str] = None
    warnings: list[str] = []


class DocumentResponse(BaseModel):
    doc_id: str
    title: str
    source_type: str
    last_modified: str
    synced_at: str
