"""Local browser interface and JSON API for the traditional chatbot."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys

from engine import ChatAdapter, InvalidMessage, RuleBasedAdapter


MAX_REQUEST_BYTES = 8192
STATIC_ROOT = Path(__file__).resolve().parent / "static"
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/static/style.css": ("style.css", "text/css; charset=utf-8"),
    "/static/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


def make_handler(adapter: ChatAdapter) -> type[BaseHTTPRequestHandler]:
    """Inject an adapter so transport code does not depend on its algorithm."""

    class ChatRequestHandler(BaseHTTPRequestHandler):
        server_version = "TraditionalChatbot/1.0"
        sys_version = ""

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, format: str, *args: object) -> None:
            # HTTP access logs omit request bodies and thus omit chat messages.
            super().log_message(format, *args)

        def send_bytes(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, status: int, payload: dict[str, object]) -> None:
            encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_bytes(status, encoded, "application/json; charset=utf-8")

        def valid_local_host(self) -> bool:
            port = self.server.server_address[1]
            return self.headers.get("Host", "").lower() in {f"127.0.0.1:{port}", f"localhost:{port}"}

        def do_GET(self) -> None:
            if not self.valid_local_host():
                self.send_json(403, {"error": "Use the localhost URL printed by the server."})
                return
            # An allowlist avoids translating arbitrary URL paths into disk paths.
            route = STATIC_FILES.get(self.path)
            if route is None:
                self.send_json(404, {"error": "This address is not available."})
                return
            filename, content_type = route
            self.send_bytes(200, (STATIC_ROOT / filename).read_bytes(), content_type)

        def do_POST(self) -> None:
            if not self.valid_local_host():
                self.send_json(403, {"error": "Use the localhost URL printed by the server."})
                return
            if self.path != "/api/messages":
                self.send_json(404, {"error": "This address is not available."})
                return

            # A browser on another site must not send messages to this local API.
            origin = self.headers.get("Origin")
            if origin is not None:
                expected_host = self.headers.get("Host", "").lower()
                if origin.lower() != f"http://{expected_host}":
                    self.send_json(403, {"error": "The request must come from this chatbot page."})
                    return
            if self.headers.get_content_type() != "application/json":
                self.send_json(415, {"error": "Send the message as application/json."})
                return
            if self.headers.get("Transfer-Encoding") is not None:
                self.send_json(400, {"error": "Use a request with a Content-Length header."})
                return
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self.send_json(400, {"error": "A valid Content-Length header is required."})
                return
            if length <= 0:
                self.send_json(400, {"error": "The request body cannot be empty."})
                return
            if length > MAX_REQUEST_BYTES:
                self.send_json(413, {"error": "The request body is too large."})
                return
            try:
                raw_body = self.rfile.read(length)
                if len(raw_body) != length:
                    self.send_json(400, {"error": "The request body was incomplete."})
                    return
                payload = json.loads(raw_body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
                self.send_json(400, {"error": "The request must contain valid UTF-8 JSON."})
                return
            except TimeoutError:
                self.send_json(408, {"error": "The request took too long. Please try again."})
                return
            if not isinstance(payload, dict) or set(payload) != {"message"}:
                self.send_json(400, {"error": "Send a JSON object containing only a message field."})
                return
            try:
                reply = adapter.respond(payload["message"])
            except InvalidMessage as error:
                self.send_json(400, {"error": str(error)})
                return
            self.send_json(200, {"reply": asdict(reply)})

    return ChatRequestHandler


def create_server(port: int = 3978, adapter: ChatAdapter | None = None) -> ThreadingHTTPServer:
    """Always bind to the loopback interface; port zero supports isolated tests."""
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(adapter or RuleBasedAdapter()))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the traditional chatbot locally.")
    parser.add_argument("--port", type=int, default=3978, help="Local port, default 3978")
    arguments = parser.parse_args()
    if not 1 <= arguments.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    try:
        server = create_server(arguments.port)
    except OSError as error:
        print(f"Unable to start: {error}. Try a different port, such as --port 3979.", file=sys.stderr)
        return 1
    with server:
        print(f"Open http://127.0.0.1:{arguments.port} in your browser.", flush=True)
        print("Traditional rules only. No external AI service. Press Ctrl+C to stop.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nChatbot stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
