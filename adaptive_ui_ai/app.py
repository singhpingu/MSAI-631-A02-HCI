"""Loopback-only development server for AdaptiveStudy AI (Python 3.11+)."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
# An allowlist prevents directory listing and exposure of source or training files.
RESOURCES = {
    "/": ("web/index.html", "text/html; charset=utf-8"),
    "/index.html": ("web/index.html", "text/html; charset=utf-8"),
    "/styles.css": ("web/styles.css", "text/css; charset=utf-8"),
    "/app.js": ("web/app.js", "text/javascript; charset=utf-8"),
    "/model.mjs": ("web/model.mjs", "text/javascript; charset=utf-8"),
    "/adaptation.mjs": ("web/adaptation.mjs", "text/javascript; charset=utf-8"),
    "/lessons.json": ("data/lessons.json", "application/json; charset=utf-8"),
    "/model.json": ("data/model.json", "application/json; charset=utf-8"),
}


class LocalHandler(BaseHTTPRequestHandler):
    """Serve only the resources needed by the app; never receive study records."""

    server_version = "AdaptiveStudy/1.0"
    sys_version = ""

    def log_message(self, format: str, *args: object) -> None:
        # Avoid retaining access logs and request contents for a classroom demo.
        return

    def _respond(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
        )
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self) -> None:
        port = self.server.server_address[1]
        if self.headers.get("Host") not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
            self._respond(403, b"Use the local app address.", "text/plain")
            return
        path = unquote(urlsplit(self.path).path)
        resource = RESOURCES.get(path)
        if resource is None:
            self._respond(404, b"Resource not found.", "text/plain")
            return
        relative_path, content_type = resource
        try:
            body = (ROOT / relative_path).read_bytes()
        except OSError:
            self._respond(500, b"Required app file is missing.", "text/plain")
            return
        self._respond(200, body, content_type)

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_POST(self) -> None:
        self._respond(405, b"This app does not accept uploaded data.", "text/plain")


def make_server(port: int = 8011) -> ThreadingHTTPServer:
    """Port zero is permitted for isolated integration tests."""
    return ThreadingHTTPServer(("127.0.0.1", port), LocalHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8011, help="Local port (default: 8011)")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a port between 1024 and 65535.")
    try:
        server = make_server(args.port)
    except OSError as error:
        parser.exit(1, f"Cannot start server: {error}. Try --port 8012.\n")
    print(f"AdaptiveStudy AI: http://127.0.0.1:{args.port}\nPress Control+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
