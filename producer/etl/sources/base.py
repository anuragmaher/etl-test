from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List


@dataclass
class DocumentRecord:
    source_type: str
    doc_id: str
    title: str
    modified_time: str  # ISO 8601
    url: str
    raw_content: Any = None


class Source(ABC):
    @abstractmethod
    def list_documents(self) -> List[DocumentRecord]:
        """Return metadata for all documents this source knows about."""
        ...

    @abstractmethod
    def fetch_document(self, doc_id: str) -> DocumentRecord:
        """Fetch full content for a single document."""
        ...
