import json
import os
from datetime import datetime, timezone


class SyncState:
    def __init__(self, path: str):
        self._path = path
        self._state: dict = {}
        if os.path.exists(path):
            with open(path) as f:
                self._state = json.load(f)

    def _key(self, source_type: str, doc_id: str) -> str:
        return f"{source_type}::{doc_id}"

    def needs_sync(self, source_type: str, doc_id: str, modified_time: str) -> bool:
        key = self._key(source_type, doc_id)
        if key not in self._state:
            return True
        return modified_time > self._state[key]["last_modified"]

    def mark_synced(self, source_type: str, doc_id: str, title: str, modified_time: str):
        key = self._key(source_type, doc_id)
        self._state[key] = {
            "title": title,
            "last_modified": modified_time,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }

    def save(self):
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self._state, f, indent=2)
