"""Exercise real loopback HTTP routes without external requests."""

import http.client
import json
import threading
import unittest

from app import make_server


class ApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_gui_and_assets_are_available(self):
        for route, content_type in (("/", "text/html"), ("/app.js", "text/javascript"),
                                    ("/styles.css", "text/css")):
            with self.subTest(route=route):
                status, headers, data = self.request("GET", route)
                self.assertEqual(status, 200)
                self.assertIn(content_type, headers["Content-Type"])
                self.assertTrue(data)
                self.assertIn("default-src 'self'", headers["Content-Security-Policy"])

    def test_catalogue_endpoint(self):
        status, _, data = self.request("GET", "/api/catalogue")
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(data)["activities"]), 24)

    def test_real_recommendation_endpoint(self):
        status, _, data = self.request("POST", "/api/recommend",
                                      json.dumps({"query": "Python dictionaries"}),
                                      {"Content-Type": "application/json"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["results"][0]["id"], "P01")

    def test_invalid_json_and_invalid_preferences_return_helpful_errors(self):
        for body in ("{bad", json.dumps({"max_minutes": 0})):
            with self.subTest(body=body):
                status, _, data = self.request("POST", "/api/recommend", body,
                                              {"Content-Type": "application/json"})
                self.assertEqual(status, 400)
                self.assertTrue(json.loads(data)["error"])

    def test_server_never_serves_source_or_parent_paths(self):
        for path in ("/engine.py", "/data/activities.json", "/../app.py", "/.env"):
            with self.subTest(path=path):
                self.assertEqual(self.request("GET", path)[0], 404)

    def test_external_origin_is_rejected(self):
        status, _, _ = self.request("POST", "/api/recommend", "{}",
                                    {"Content-Type": "application/json", "Origin": "https://external.invalid"})
        self.assertEqual(status, 403)

    def test_external_host_is_rejected(self):
        self.assertEqual(self.request("GET", "/", headers={"Host": "external.invalid"})[0], 403)

    def test_wrong_content_type_and_oversized_body_are_rejected(self):
        self.assertEqual(self.request("POST", "/api/recommend", "{}",
                                     {"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request("POST", "/api/recommend", "x" * 65_537,
                                     {"Content-Type": "application/json"})[0], 413)


if __name__ == "__main__":
    unittest.main()
