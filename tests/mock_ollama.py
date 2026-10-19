"""Configurable mock Ollama HTTP server for integration and unit testing."""

import http.server
import json
import threading
import time
from typing import Any, Callable, Dict, Optional


class MockOllamaHandler(http.server.BaseHTTPRequestHandler):
    """HTTP Request handler for mock Ollama API endpoints."""

    def log_message(self, format: str, *args: Any):
        # Suppress standard logging to keep test output clean
        pass

    @property
    def server_instance(self) -> "MockOllamaServer":
        return getattr(self.server, "mock_instance")

    def do_GET(self):
        inst = self.server_instance
        inst.request_history.append({"method": "GET", "path": self.path})

        if inst.delay > 0:
            time.sleep(inst.delay)

        if inst.force_status_code != 200:
            self.send_response(inst.force_status_code)
            self.end_headers()
            self.wfile.write(b"Forced Error")
            return

        if self.path.startswith("/api/tags"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            body = json.dumps(inst.tags_response).encode("utf-8")
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                pass
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        inst = self.server_instance
        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length).decode("utf-8", errors="replace")

        inst.request_history.append({
            "method": "POST",
            "path": self.path,
            "body": post_body,
        })

        if inst.delay > 0:
            time.sleep(inst.delay)

        if inst.force_status_code != 200:
            self.send_response(inst.force_status_code)
            self.end_headers()
            try:
                self.wfile.write(b"Forced Error")
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                pass
            return

        if self.path.startswith("/api/generate"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            # Handle dynamic response callback if provided
            if inst.generate_callback:
                response_content = inst.generate_callback(post_body)
            else:
                response_content = inst.generate_response

            payload = {
                "model": "phi3",
                "created_at": "2026-10-19T00:00:00Z",
                "response": response_content,
                "done": True,
            }
            try:
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                pass
        else:
            self.send_response(404)
            self.end_headers()


class MockOllamaServer:
    """Thread-safe Mock Ollama server listening on a random open port."""

    def __init__(
        self,
        tags_models: Optional[list] = None,
        generate_response: str = "",
        delay: float = 0.0,
        force_status_code: int = 200,
    ):
        if tags_models is None:
            tags_models = [{"name": "phi3:latest"}, {"name": "llama3.2:3b"}]

        self.tags_response = {"models": tags_models}
        self.generate_response = generate_response
        self.delay = delay
        self.force_status_code = force_status_code
        self.generate_callback: Optional[Callable[[str], str]] = None
        self.request_history: list = []

        self.httpd = http.server.HTTPServer(("127.0.0.1", 0), MockOllamaHandler)
        self.httpd.mock_instance = self  # type: ignore
        self.port = self.httpd.server_port
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def host_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self):
        self.thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        if self.thread.is_alive():
            self.thread.join(timeout=2.0)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
