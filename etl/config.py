import os

import yaml


DEFAULTS = {
    "polling_interval_seconds": 300,
    "output_directory": "./output",
    "credentials_path": "./credentials.json",
    "token_path": "./token.json",
    "state_path": "./sync_state.json",
    "api_key": "",
    "log_level": "INFO",
    "sources": {
        "google_docs": {
            "enabled": True,
            "folder_ids": [],
        }
    },
}


def load_config(path: str = "config.yaml") -> dict:
    config = dict(DEFAULTS)

    if os.path.exists(path):
        with open(path) as f:
            user_config = yaml.safe_load(f) or {}
        # Merge top-level keys
        for key, value in user_config.items():
            if key == "sources" and isinstance(value, dict):
                config["sources"] = {**DEFAULTS["sources"], **value}
            else:
                config[key] = value

    # Resolve relative paths to absolute (relative to config file directory)
    config_dir = os.path.dirname(os.path.abspath(path))
    for key in ("output_directory", "credentials_path", "token_path", "state_path"):
        if not os.path.isabs(config[key]):
            config[key] = os.path.join(config_dir, config[key])

    return config
