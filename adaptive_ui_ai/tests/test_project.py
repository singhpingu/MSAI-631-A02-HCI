"""Meaningful model, dataset, and HTTP integration checks using only stdlib."""

import http.client
import json
import math
import threading
import unittest

from app import ROOT, make_server
from machine_learning import build_model, generate_profiles, models_equivalent, predict, sigmoid, train


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = build_model()

    def test_reproducible_model_matches_shipped_artifact(self) -> None:
        shipped = json.loads((ROOT / "data/model.json").read_text())
        self.assertTrue(models_equivalent(shipped, self.model))
        rounding_noise = {**shipped, "weights": [value + 1e-12 for value in shipped["weights"]]}
        changed_model = {**shipped, "weights": [value + 1e-6 for value in shipped["weights"]]}
        self.assertTrue(models_equivalent(rounding_noise, self.model))
        self.assertFalse(models_equivalent(changed_model, self.model))
        self.assertFalse(models_equivalent({**shipped, "schema_version": True}, self.model))

    def test_train_and_test_ids_do_not_overlap(self) -> None:
        profiles = generate_profiles()
        train_ids = {row.identifier for row in profiles if row.split == "train"}
        test_ids = {row.identifier for row in profiles if row.split == "test"}
        self.assertEqual((len(train_ids), len(test_ids)), (240, 80))
        self.assertFalse(train_ids & test_ids)
        self.assertEqual(generate_profiles(), profiles)

    def test_training_rejects_evaluation_rows(self) -> None:
        with self.assertRaises(ValueError):
            train(generate_profiles())
        with self.assertRaises(ValueError):
            train([])

    def test_score_orders_clear_profiles(self) -> None:
        weights, bias = self.model["weights"], self.model["bias"]
        self.assertLess(predict(weights, bias, (0, 0, 0)), 0.3)
        self.assertGreater(predict(weights, bias, (1, 1, 1)), 0.7)

    def test_invalid_features_fail_instead_of_silent_prediction(self) -> None:
        for features in [(0, 0), (0, 0, -1), (0, 0, math.nan), (0, 0, math.inf)]:
            with self.assertRaises(ValueError):
                predict([1, 1, 1], 0, features)

    def test_sigmoid_handles_extreme_values(self) -> None:
        self.assertEqual(sigmoid(1000), 1)
        self.assertEqual(sigmoid(-1000), 0)
        self.assertEqual(sigmoid(0), 0.5)

    def test_reported_accuracy_is_calculated_from_heldout_rows(self) -> None:
        testing = [row for row in generate_profiles() if row.split == "test"]
        correct = sum(
            (predict(self.model["weights"], self.model["bias"], row.features) >= 0.5) == bool(row.label)
            for row in testing
        )
        self.assertEqual(self.model["evaluation"], {"test_rows": 80, "correct": correct, "accuracy": correct / 80})

    def test_lessons_have_valid_unique_answers(self) -> None:
        lessons = json.loads((ROOT / "data/lessons.json").read_text())
        self.assertEqual(len({row["id"] for row in lessons}), 6)
        for row in lessons:
            self.assertIn(row["answer"], range(len(row["options"])))
            self.assertGreater(row["expectedMs"], 0)
            self.assertTrue(row["source"])


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = make_server(0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, path: str, method: str = "GET", headers: dict | None = None) -> tuple:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_app_and_model_are_accessible(self) -> None:
        status, headers, content = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"AdaptiveStudy AI", content)
        self.assertIn("script-src 'self'", headers["Content-Security-Policy"])
        self.assertEqual(self.request("/model.json")[0], 200)

    def test_private_paths_and_traversal_are_not_served(self) -> None:
        for path in ["/../app.py", "/%2e%2e/app.py", "/data/", "/machine_learning.py", "/synthetic_profiles.csv"]:
            self.assertEqual(self.request(path)[0], 404)

    def test_foreign_host_is_rejected(self) -> None:
        self.assertEqual(self.request("/", headers={"Host": "other.example"})[0], 403)

    def test_head_matches_get_length_without_body(self) -> None:
        status, headers, content = self.request("/", method="HEAD")
        self.assertEqual(status, 200)
        self.assertGreater(int(headers["Content-Length"]), 0)
        self.assertEqual(content, b"")

    def test_records_cannot_be_uploaded(self) -> None:
        self.assertEqual(self.request("/", method="POST")[0], 405)


if __name__ == "__main__":
    unittest.main()
