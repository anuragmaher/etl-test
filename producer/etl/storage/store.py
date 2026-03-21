"""Simple JSON file-based storage for server-side config and tokens."""

import json
import os


def _load_json(path: str) -> dict:
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _save_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_pinecone_config(path: str = "pinecone_config.json") -> dict:
    return _load_json(path)


def save_pinecone_config(config: dict, path: str = "pinecone_config.json"):
    _save_json(path, config)


def is_pinecone_configured(path: str = "pinecone_config.json") -> bool:
    config = load_pinecone_config(path)
    return bool(config.get("api_key") and config.get("index_name") and config.get("openai_api_key"))
