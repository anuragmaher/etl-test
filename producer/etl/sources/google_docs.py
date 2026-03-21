import logging
import os
from typing import List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from googleapiclient.http import MediaIoBaseDownload

from etl.sources.base import DocumentRecord, Source

logger = logging.getLogger(__name__)

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
GDOC_MIME = "application/vnd.google-apps.document"
PDF_MIME = "application/pdf"

SCOPES = [
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


class GoogleDocsSource(Source):
    def __init__(self, credentials_path: str = "", token_path: str = "",
                 folder_ids: list = None, credentials: Credentials = None):
        self._credentials_path = credentials_path
        self._token_path = token_path
        self._folder_ids = folder_ids or []
        self._creds = credentials
        self._drive_service = None
        self._docs_service = None

    def _authenticate(self):
        creds = None
        if os.path.exists(self._token_path):
            creds = Credentials.from_authorized_user_file(self._token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self._credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(self._token_path, "w") as f:
                f.write(creds.to_json())

        self._creds = creds
        self._drive_service = build("drive", "v3", credentials=creds)
        self._docs_service = build("docs", "v1", credentials=creds)

    def _ensure_authenticated(self):
        if self._drive_service is None:
            if self._creds and self._creds.valid:
                self._drive_service = build("drive", "v3", credentials=self._creds)
                self._docs_service = build("docs", "v1", credentials=self._creds)
            else:
                self._authenticate()

    def list_folders(self) -> list:
        """List all folders in the user's Google Drive. Returns list of {id, name}."""
        self._ensure_authenticated()

        folders = []
        page_token = None

        while True:
            response = self._drive_service.files().list(
                q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields="nextPageToken, files(id, name)",
                pageSize=100,
                orderBy="name",
                pageToken=page_token,
            ).execute()

            for f in response.get("files", []):
                folders.append({"id": f["id"], "name": f["name"]})

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return folders

    def list_files_recursive(self, folder_id: str) -> list:
        """Recursively list all files and subfolders under a folder.
        Returns a tree structure: [{id, name, mimeType, type, children}]
        """
        self._ensure_authenticated()
        return self._list_children(folder_id)

    def _list_children(self, folder_id: str) -> list:
        """Fetch all children of a folder, recursing into subfolders."""
        items = []
        page_token = None

        while True:
            response = self._drive_service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="nextPageToken, files(id, name, mimeType, modifiedTime, webViewLink)",
                pageSize=100,
                orderBy="folder,name",
                pageToken=page_token,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            ).execute()

            for f in response.get("files", []):
                mime = f["mimeType"]
                if mime == "application/vnd.google-apps.folder":
                    children = self._list_children(f["id"])
                    items.append({
                        "id": f["id"],
                        "name": f["name"],
                        "type": "folder",
                        "mimeType": mime,
                        "children": children,
                    })
                elif mime in (GDOC_MIME, DOCX_MIME, PDF_MIME):
                    items.append({
                        "id": f["id"],
                        "name": f["name"],
                        "type": "file",
                        "mimeType": mime,
                        "modifiedTime": f.get("modifiedTime", ""),
                        "url": f.get("webViewLink", ""),
                    })

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return items

    def list_documents(self) -> List[DocumentRecord]:
        self._ensure_authenticated()

        # Query for both native Google Docs and uploaded .docx files
        mime_filter = (
            f"(mimeType='{GDOC_MIME}' or mimeType='{DOCX_MIME}' or mimeType='{PDF_MIME}') and trashed=false"
        )
        if self._folder_ids:
            folder_clauses = " or ".join(
                f"'{fid}' in parents" for fid in self._folder_ids
            )
            mime_filter += f" and ({folder_clauses})"

        documents = []
        page_token = None

        while True:
            response = self._drive_service.files().list(
                q=mime_filter,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime, webViewLink)",
                pageSize=100,
                pageToken=page_token,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            ).execute()

            for f in response.get("files", []):
                # Tag source_type based on mime so pipeline picks the right transformer
                mime = f["mimeType"]
                if mime == GDOC_MIME:
                    source_type = "google_docs"
                elif mime == PDF_MIME:
                    source_type = "google_pdf"
                else:
                    source_type = "google_docx"
                documents.append(
                    DocumentRecord(
                        source_type=source_type,
                        doc_id=f["id"],
                        title=f["name"],
                        modified_time=f["modifiedTime"],
                        url=f.get("webViewLink", ""),
                    )
                )

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        logger.info(
            "Listed %d documents (%d Google Docs, %d .docx, %d PDF)",
            len(documents),
            sum(1 for d in documents if d.source_type == "google_docs"),
            sum(1 for d in documents if d.source_type == "google_docx"),
            sum(1 for d in documents if d.source_type == "google_pdf"),
        )
        return documents

    def fetch_document(self, doc_id: str) -> DocumentRecord:
        self._ensure_authenticated()

        # Get metadata from Drive
        file_meta = self._drive_service.files().get(
            fileId=doc_id,
            fields="id, name, mimeType, modifiedTime, webViewLink",
            supportsAllDrives=True,
        ).execute()

        mime = file_meta.get("mimeType", "")

        if mime == GDOC_MIME:
            # Native Google Doc — use Docs API
            doc_json = self._docs_service.documents().get(
                documentId=doc_id,
                includeTabsContent=True,
            ).execute()
            raw_content = doc_json
            source_type = "google_docs"
        elif mime == PDF_MIME:
            # PDF — download raw bytes
            import io
            request = self._drive_service.files().get_media(fileId=doc_id, supportsAllDrives=True)
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            raw_content = buffer.getvalue()
            source_type = "google_pdf"
        else:
            # .docx file — download raw bytes
            import io
            request = self._drive_service.files().get_media(fileId=doc_id, supportsAllDrives=True)
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            raw_content = buffer.getvalue()
            source_type = "google_docx"

        return DocumentRecord(
            source_type=source_type,
            doc_id=file_meta["id"],
            title=file_meta["name"],
            modified_time=file_meta["modifiedTime"],
            url=file_meta.get("webViewLink", ""),
            raw_content=raw_content,
        )
