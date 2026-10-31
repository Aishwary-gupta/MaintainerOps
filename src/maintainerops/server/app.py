import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Any, Dict, List, Optional

from maintainerops import __version__
from maintainerops.config import Config, load_config
from maintainerops.engine import run_scan
from maintainerops.reporters.html_report import render_html
from maintainerops.reporters.json_report import render_json
from maintainerops.reporters.markdown import render_markdown

# Global in-memory audit log for triage actions taken during dashboard session
SESSION_ACTIONS: List[Dict[str, Any]] = []


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP server handling concurrent dashboard requests."""
    daemon_threads = True
    allow_reuse_address = True


class MaintainerOpsHandler(BaseHTTPRequestHandler):
    """REST API and Static Asset Handler for the MaintainerOps Dashboard."""

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default stdout access logs to keep terminal clean."""
        pass

    def _send_json(self, data: Any, status: int = 200) -> None:
        payload = json.dumps(data, indent=2, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(payload)

    def _send_html(self, html_content: str, status: int = 200) -> None:
        payload = html_content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _send_text(self, text_content: str, status: int = 200) -> None:
        payload = text_content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # 1. Root and static HTML
        if path in ["/", "/index.html", "/dashboard"]:
            static_dir = Path(__file__).parent / "static"
            dashboard_file = static_dir / "dashboard.html"
            if dashboard_file.exists():
                content = dashboard_file.read_text(encoding="utf-8")
                self._send_html(content)
            else:
                # Fallback if dashboard.html not placed yet
                default_target = query.get("target", ["tests/fixtures/sample_repo.json"])[0]
                try:
                    report = run_scan(default_target)
                    self._send_html(render_html(report))
                except Exception as e:
                    self._send_text(f"Error initializing dashboard: {e}", status=500)
            return

        # 2. API: Health Check
        if path == "/api/health":
            self._send_json({
                "status": "healthy",
                "version": __version__,
                "actions_recorded": len(SESSION_ACTIONS),
            })
            return

        # 3. API: Available Fixtures
        if path == "/api/fixtures":
            fixtures = []
            fixtures_dir = Path("tests/fixtures")
            if fixtures_dir.exists():
                for p in fixtures_dir.glob("*.json"):
                    fixtures.append({
                        "name": p.stem,
                        "path": str(p).replace("\\", "/"),
                        "filename": p.name,
                    })
            self._send_json({"fixtures": fixtures})
            return

        # 4. API: Config
        if path == "/api/config":
            cfg = load_config()
            self._send_json(cfg.model_dump())
            return

        # 5. API: Session Triage Actions
        if path == "/api/actions":
            self._send_json({"actions": SESSION_ACTIONS})
            return

        # 6. API: Get Scan Report
        if path == "/api/report":
            target = query.get("target", ["tests/fixtures/sample_repo.json"])[0]
            try:
                report = run_scan(target)
                self._send_json(report.model_dump(mode="python"))
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        # 7. API: Export Report (Markdown, JSON, HTML)
        if path == "/api/export":
            target = query.get("target", ["tests/fixtures/sample_repo.json"])[0]
            fmt = query.get("format", ["markdown"])[0].lower()
            try:
                report = run_scan(target)
                if fmt == "json":
                    self._send_text(render_json(report))
                elif fmt == "html":
                    self._send_html(render_html(report))
                else:
                    self._send_text(render_markdown(report))
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        # 404 Not Found
        self._send_json({"error": f"Path not found: {path}"}, status=404)

    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            body = {}

        # 1. API: Trigger Custom Scan with On-The-Fly Parameters
        if path == "/api/scan":
            target = body.get("target", "tests/fixtures/sample_repo.json")
            cfg_dict = body.get("config", {})
            try:
                cfg = Config(**cfg_dict) if cfg_dict else load_config()
                report = run_scan(target, cfg)
                self._send_json(report.model_dump(mode="python"))
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        # 2. API: Record Triage Action (Simulate Maintainer Triage Decision)
        if path == "/api/action":
            action_type = body.get("action", "custom_action")
            item_number = body.get("item_number")
            finding_id = body.get("finding_id")
            note = body.get("note", "")
            target_repo = body.get("repository", "")

            action_record = {
                "id": len(SESSION_ACTIONS) + 1,
                "action": action_type,
                "finding_id": finding_id,
                "item_number": item_number,
                "repository": target_repo,
                "note": note,
            }
            SESSION_ACTIONS.append(action_record)
            self._send_json({
                "status": "success",
                "message": f"Recorded triage action '{action_type}' for item #{item_number}",
                "record": action_record,
                "total_actions": len(SESSION_ACTIONS),
            })
            return

        self._send_json({"error": f"POST endpoint not found: {path}"}, status=404)


def start_server(host: str = "127.0.0.1", port: int = 8080) -> ThreadedHTTPServer:
    """Starts the Threaded MaintainerOps HTTP Server."""
    server_address = (host, port)
    httpd = ThreadedHTTPServer(server_address, MaintainerOpsHandler)
    return httpd
