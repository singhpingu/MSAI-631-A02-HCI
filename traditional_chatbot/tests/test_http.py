"""Real loopback HTTP tests; no third party server or external service is used."""

import http.client
import json
import threading
import unittest

from app import MAX_REQUEST_BYTES, create_server
from engine import ChatReply


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Port zero lets the operating system reserve a free port without races.
        cls.server = create_server(0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def post(self, payload, headers=None):
        request_headers = {"Content-Type": "application/json"}
        request_headers.update(headers or {})
        return self.request("POST", "/api/messages", json.dumps(payload), request_headers)

    def test_server_binds_only_to_loopback(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_page_and_static_assets_are_available(self):
        for path, expected_type in (("/", "text/html"), ("/static/app.js", "text/javascript"), ("/static/style.css", "text/css")):
            with self.subTest(path=path):
                status, headers, body = self.request("GET", path)
                self.assertEqual(status, 200)
                self.assertTrue(headers["Content-Type"].startswith(expected_type))
                self.assertGreater(len(body), 100)

    def test_successful_message_and_safety_headers(self):
        status, headers, body = self.post({"message": "hello"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["reply"]["intent"], "greeting")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])

    def test_malformed_json_is_handled(self):
        status, _, body = self.request("POST", "/api/messages", "{oops", {"Content-Type": "application/json"})
        self.assertEqual(status, 400)
        self.assertIn("valid UTF-8 JSON", json.loads(body)["error"])

    def test_invalid_utf8_is_handled(self):
        status, _, _ = self.request("POST", "/api/messages", b"\xff", {"Content-Type": "application/json"})
        self.assertEqual(status, 400)

    def test_lone_unicode_surrogate_is_handled(self):
        status, _, body = self.post({"message": "echo: \ud800"})
        self.assertEqual(status, 400)
        self.assertIn("Unicode", json.loads(body)["error"])

    def test_excessively_nested_json_is_handled(self):
        raw = "[" * 1500 + "0" + "]" * 1500
        status, _, _ = self.request("POST", "/api/messages", raw, {"Content-Type": "application/json"})
        self.assertEqual(status, 400)

    def test_invalid_payload_shapes_are_handled(self):
        for payload in ([], "hello", None, {}, {"message": "hello", "extra": 1}):
            with self.subTest(payload=payload):
                status, _, body = self.post(payload)
                self.assertEqual(status, 400)
                self.assertIn("message field", json.loads(body)["error"])

    def test_invalid_message_types_and_lengths_are_handled(self):
        for value in (None, 7, True, [], {}, "", "   ", "x" * 1001):
            with self.subTest(value=repr(value)[:30]):
                status, _, body = self.post({"message": value})
                self.assertEqual(status, 400)
                self.assertIn("error", json.loads(body))

    def test_wrong_content_type_is_rejected(self):
        status, _, _ = self.request("POST", "/api/messages", "hello", {"Content-Type": "text/plain"})
        self.assertEqual(status, 415)

    def test_oversized_body_is_rejected(self):
        status, _, _ = self.request("POST", "/api/messages", "x" * (MAX_REQUEST_BYTES + 1), {"Content-Type": "application/json"})
        self.assertEqual(status, 413)

    def test_unsupported_routes_and_traversal_are_rejected(self):
        for path in ("/missing", "/../engine.py", "/static/../engine.py"):
            with self.subTest(path=path):
                self.assertEqual(self.request("GET", path)[0], 404)
        self.assertEqual(self.request("POST", "/missing", "")[0], 404)

    def test_external_host_and_origin_are_rejected(self):
        self.assertEqual(self.post({"message": "hello"}, {"Host": "example.com"})[0], 403)
        for origin in ("https://example.com", "null", "http://[malformed", f"http://127.0.0.1:{self.port}/unexpected"):
            with self.subTest(origin=origin):
                self.assertEqual(self.post({"message": "hello"}, {"Origin": origin})[0], 403)

    def test_same_origin_browser_request_is_allowed(self):
        self.assertEqual(self.post({"message": "help"}, {"Origin": f"http://127.0.0.1:{self.port}"})[0], 200)

    def test_html_input_remains_json_text(self):
        status, _, body = self.post({"message": "echo: <img src=x onerror=alert(1)>"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["reply"]["text"], "<img src=x onerror=alert(1)>")

    def test_empty_body_is_rejected(self):
        self.assertEqual(self.request("POST", "/api/messages", "", {"Content-Type": "application/json"})[0], 400)


class AdapterBoundaryTests(unittest.TestCase):
    def test_server_can_use_an_injected_adapter(self):
        class FakeAdapter:
            def respond(self, message):
                return ChatReply("Adapter boundary works.", "fake")

        server = create_server(0, FakeAdapter())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        try:
            connection.request("POST", "/api/messages", json.dumps({"message": "hello"}), {"Content-Type": "application/json"})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read())["reply"]["intent"], "fake")
        finally:
            connection.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
