"""Serve the educational GUI on loopback using Python's standard library.

Run: python app.py
Credit: Python Software Foundation, http.server documentation,
https://docs.python.org/3/library/http.server.html
AI assistance: ChatGPT/Codex. Review and test before academic submission.
This is a local classroom application; its server is not production hosting.
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from engine import Recommender

ROOT = Path(__file__).resolve().parent
MAX_BODY_BYTES = 65_536
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


def make_server(port: int = 8765) -> ThreadingHTTPServer:
    engine = Recommender(ROOT / "data" / "activities.json")

    class Handler(BaseHTTPRequestHandler):
        """Explicit routes prevent serving source files or directory listings."""

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(10)

        def reply(self, status: int, data: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; script-src 'self'; style-src 'self'; "
                             "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(data)

        def json_reply(self, status: int, value: dict) -> None:
            data = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.reply(status, data, "application/json; charset=utf-8")

        def local_request(self) -> bool:
            actual_port = self.server.server_port
            hosts = {f"127.0.0.1:{actual_port}", f"localhost:{actual_port}"}
            if self.headers.get("Host", "") not in hosts:
                self.json_reply(403, {"error": "Use the local application address."})
                return False
            origin = self.headers.get("Origin")
            if origin and origin not in {f"http://{host}" for host in hosts}:
                self.json_reply(403, {"error": "Requests must come from this local app."})
                return False
            return True

        def do_GET(self) -> None:
            if not self.local_request():
                return
            route = urlsplit(self.path).path
            if route == "/api/catalogue":
                self.json_reply(200, engine.catalogue())
            elif route in STATIC_FILES:
                filename, content_type = STATIC_FILES[route]
                self.reply(200, (ROOT / "web" / filename).read_bytes(), content_type)
            else:
                self.json_reply(404, {"error": "Page not found."})

        def do_POST(self) -> None:
            if not self.local_request():
                return
            if urlsplit(self.path).path != "/api/recommend":
                self.json_reply(404, {"error": "Endpoint not found."})
                return
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                self.json_reply(415, {"error": "Send preferences as JSON."})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= MAX_BODY_BYTES:
                    self.json_reply(413, {"error": "The preference request is too large or empty."})
                    return
                payload = json.loads(self.rfile.read(size).decode("utf-8"))
                self.json_reply(200, engine.recommend(payload))
            except (ValueError, UnicodeDecodeError) as exc:
                self.json_reply(400, {"error": str(exc)})

        def log_message(self, message: str, *args: object) -> None:
            # Request bodies and personal interest text are never logged.
            print(message % args)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the local StudyPath recommender.")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        with make_server(args.port) as server:
            print(f"StudyPath is running at http://127.0.0.1:{server.server_port}")
            print("Press Control+C to stop. No cloud credentials are needed.")
            server.serve_forever()
    except KeyboardInterrupt:
        print("\nStudyPath stopped.")
    except OSError as exc:
        parser.exit(1, f"Cannot start the server: {exc}. Try --port 8766.\n")
