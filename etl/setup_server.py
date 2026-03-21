"""Local HTTP server that serves the Google Picker for folder selection."""

import json
import os
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

import yaml


class PickerHandler(BaseHTTPRequestHandler):
    """Handles serving the picker HTML and receiving the folder selection."""

    config_path = None
    access_token = None
    api_key = None
    client_id = None
    app_id = None
    server_ref = None

    def log_message(self, format, *args):
        # Suppress default request logging
        pass

    def do_GET(self):
        if self.path != "/":
            self.send_error(404)
            return

        template_path = os.path.join(
            os.path.dirname(__file__), "templates", "picker.html"
        )
        with open(template_path) as f:
            html = f.read()

        html = html.replace("{{ACCESS_TOKEN}}", self.access_token or "")
        html = html.replace("{{API_KEY}}", self.api_key or "")
        html = html.replace("{{CLIENT_ID}}", self.client_id or "")
        html = html.replace("{{APP_ID}}", self.app_id or "")

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def do_POST(self):
        if self.path != "/save":
            self.send_error(404)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        data = json.loads(body)

        folders = data.get("folders", [])

        # Save to config
        with open(self.config_path) as f:
            raw_config = yaml.safe_load(f) or {}

        if "sources" not in raw_config:
            raw_config["sources"] = {}
        if "google_docs" not in raw_config["sources"]:
            raw_config["sources"]["google_docs"] = {}

        raw_config["sources"]["google_docs"]["enabled"] = True
        raw_config["sources"]["google_docs"]["folder_ids"] = [
            f["id"] for f in folders
        ]

        with open(self.config_path, "w") as f:
            yaml.dump(raw_config, f, default_flow_style=False, sort_keys=False)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode())

        print("\n--- Configuration saved ---\n")
        if folders:
            print("Selected folders:")
            for folder in folders:
                print(f"  - {folder['name']}")
        else:
            print("No folders selected. Will sync ALL Google Docs.")

        print(f"\nRun 'python3 -m etl.main --once' to start syncing.\n")

        # Shut down the server after saving
        threading.Thread(target=self.server_ref.shutdown, daemon=True).start()


def run_picker_server(
    config_path: str,
    access_token: str,
    api_key: str,
    client_id: str,
    app_id: str,
    port: int = 8090,
):
    """Start local server, open browser to picker, wait for selection."""
    PickerHandler.config_path = config_path
    PickerHandler.access_token = access_token
    PickerHandler.api_key = api_key
    PickerHandler.client_id = client_id
    PickerHandler.app_id = app_id

    server = HTTPServer(("localhost", port), PickerHandler)
    PickerHandler.server_ref = server

    url = f"http://localhost:{port}"
    print(f"Opening folder picker at {url}")
    webbrowser.open(url)

    server.serve_forever()
    server.server_close()
