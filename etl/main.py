import argparse
import json
import logging
import time

import yaml

from etl.config import load_config
from etl.pipeline import run_once
from etl.sources.google_docs import GoogleDocsSource
from etl.setup_server import run_picker_server


def setup_logging(level: str):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def run_setup(config: dict, config_path: str):
    """Interactive setup: authenticate via OAuth, then open Google Picker in browser."""
    print("\n=== ETL Pipeline Setup ===\n")

    # Validate API key
    api_key = config.get("api_key", "")
    if not api_key:
        print("ERROR: 'api_key' is required in config.yaml for the folder picker.")
        print("Create one at: Google Cloud Console → APIs & Services → Credentials → API Key")
        return

    # Authenticate to get an access token
    print("Authenticating with Google (a browser window will open)...\n")
    source = GoogleDocsSource(
        credentials_path=config["credentials_path"],
        token_path=config["token_path"],
    )
    source._ensure_authenticated()
    access_token = source._creds.token

    # Extract client ID from credentials.json
    with open(config["credentials_path"]) as f:
        creds_data = json.load(f)
    # Handle both "installed" and "web" credential types
    creds_info = creds_data.get("installed") or creds_data.get("web", {})
    client_id = creds_info.get("client_id", "")
    project_number = creds_info.get("project_id", "")

    print("Authentication successful!\n")
    print("Opening folder picker in your browser...\n")
    print("Select folders and click 'Save & Start Syncing'.\n")

    run_picker_server(
        config_path=config_path,
        access_token=access_token,
        api_key=api_key,
        client_id=client_id,
        app_id=project_number,
    )


def main():
    parser = argparse.ArgumentParser(description="ETL pipeline for document ingestion")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--setup", action="store_true", help="Interactive setup: authenticate and select folders")
    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config["log_level"])

    logger = logging.getLogger(__name__)

    if args.setup:
        run_setup(config, args.config)
    elif args.once:
        logger.info("Running single sync cycle")
        run_once(config)
        logger.info("Done")
    else:
        interval = config["polling_interval_seconds"]
        logger.info("Starting poll loop (interval: %ds)", interval)
        while True:
            run_once(config)
            logger.info("Sleeping %ds until next cycle", interval)
            time.sleep(interval)


if __name__ == "__main__":
    main()
