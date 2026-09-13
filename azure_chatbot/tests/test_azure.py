"""OFFLINE fixtures only. Synthetic scores never establish a live Azure result."""

import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from azure_service import AzureSentimentService, ServiceIssue, make_azure_client


def fake_document():
    """A synthetic SDK-shaped fixture, not a saved Azure response."""
    return SimpleNamespace(
        is_error=False,
        sentiment="mixed",
        confidence_scores=SimpleNamespace(positive=0.50, neutral=0.05, negative=0.45),
        sentences=[SimpleNamespace(
            text="Synthetic sentence for an offline test.",
            sentiment="positive",
            confidence_scores=SimpleNamespace(positive=0.90, neutral=0.05, negative=0.05),
        )],
    )


class FakeClient:
    """Collect calls without making a network connection."""
    def __init__(self, results=None, error=None):
        self.results = results if results is not None else [fake_document()]
        self.error = error
        self.calls = []
        self.closed = False

    def analyze_sentiment(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.results

    def close(self):
        self.closed = True


class FakeHTTPError(Exception):
    def __init__(self, status):
        super().__init__("SENSITIVE_KEY_AND_TEXT_MUST_NOT_LEAK")
        self.status_code = status


class AzureBoundaryTests(unittest.TestCase):
    def test_single_document_options_scores_and_cleanup(self):
        client = FakeClient()
        result = AzureSentimentService(lambda: client).analyze("Only this text.")
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["documents"], ["Only this text."])
        self.assertEqual(client.calls[0]["language"], "en")
        self.assertEqual(client.calls[0]["retry_total"], 0)
        self.assertEqual(client.calls[0]["connection_timeout"], 5)
        self.assertEqual(client.calls[0]["read_timeout"], 10)
        self.assertTrue(client.calls[0]["disable_service_logs"])
        self.assertFalse(client.calls[0]["logging_enable"])
        self.assertFalse(client.calls[0]["show_opinion_mining"])
        self.assertEqual(result.sentiment, "mixed")
        self.assertEqual(result.to_dict()["scores"]["positive"], 0.5)
        self.assertEqual(result.sentences[0].sentiment, "positive")
        self.assertTrue(client.closed)

    def test_authentication_and_throttling_errors_are_sanitized(self):
        for status, code in ((401, "authentication"), (403, "authentication"), (429, "throttled")):
            with self.subTest(status=status):
                client = FakeClient(error=FakeHTTPError(status))
                with self.assertRaises(ServiceIssue) as context:
                    AzureSentimentService(lambda: client).analyze("text")
                self.assertEqual(context.exception.code, code)
                self.assertNotIn("SENSITIVE", str(context.exception))
                self.assertEqual(len(client.calls), 1)
                self.assertTrue(client.closed)

    def test_request_and_server_errors_are_sanitized(self):
        for status, code in ((400, "request"), (404, "request"), (413, "request"), (503, "unavailable")):
            with self.subTest(status=status):
                with self.assertRaises(ServiceIssue) as context:
                    AzureSentimentService(lambda: FakeClient(error=FakeHTTPError(status))).analyze("text")
                self.assertEqual(context.exception.code, code)
                self.assertNotIn("SENSITIVE", str(context.exception))

    def test_network_timeout_is_sanitized_without_retry(self):
        client = FakeClient(error=TimeoutError("SENSITIVE endpoint and key"))
        with self.assertRaises(ServiceIssue) as context:
            AzureSentimentService(lambda: client).analyze("text")
        self.assertEqual(context.exception.code, "network")
        self.assertNotIn("SENSITIVE", str(context.exception))
        self.assertEqual(len(client.calls), 1)

    def test_unexpected_error_is_sanitized(self):
        with self.assertRaises(ServiceIssue) as context:
            AzureSentimentService(lambda: FakeClient(error=RuntimeError("SENSITIVE"))).analyze("text")
        self.assertEqual(context.exception.code, "service")
        self.assertNotIn("SENSITIVE", str(context.exception))

    def test_document_error_never_becomes_a_sentiment_result(self):
        doc = SimpleNamespace(is_error=True, error=SimpleNamespace(message="SENSITIVE"))
        with self.assertRaises(ServiceIssue) as context:
            AzureSentimentService(lambda: FakeClient([doc])).analyze("text")
        self.assertEqual(context.exception.code, "document")
        self.assertNotIn("SENSITIVE", str(context.exception))

    def test_invalid_result_count_is_handled(self):
        for docs in ([], [fake_document(), fake_document()]):
            with self.subTest(count=len(docs)), self.assertRaises(ServiceIssue):
                AzureSentimentService(lambda: FakeClient(docs)).analyze("text")

    def test_invalid_scores_and_labels_are_rejected(self):
        for value in (float("nan"), float("inf"), -0.1, 1.1):
            doc = fake_document()
            doc.confidence_scores.positive = value
            with self.subTest(score=value), self.assertRaises(ServiceIssue):
                AzureSentimentService(lambda: FakeClient([doc])).analyze("text")
        doc = fake_document()
        doc.sentiment = "SENSITIVE"
        with self.assertRaises(ServiceIssue):
            AzureSentimentService(lambda: FakeClient([doc])).analyze("text")

    def test_missing_configuration_is_local_and_actionable(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ServiceIssue) as context:
            make_azure_client()
        self.assertEqual(context.exception.code, "configuration")
        self.assertIn("Local commands still work", str(context.exception))

    def test_non_azure_or_non_https_endpoints_are_rejected_before_sdk_load(self):
        endpoints = ["http://course.cognitiveservices.azure.com", "https://evil.example", "https://course.cognitiveservices.azure.com.evil.example", "https://key@course.cognitiveservices.azure.com", "https://course.cognitiveservices.azure.com/text/analytics", "https://course.cognitiveservices.azure.com?key=SENSITIVE", "https://[broken", "https://course.cognitiveservices.azure.com:9876"]
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint), patch.dict(os.environ, {"AZURE_LANGUAGE_ENDPOINT": endpoint, "AZURE_LANGUAGE_KEY": "fake-not-a-key"}, clear=True):
                with self.assertRaises(ServiceIssue) as context:
                    make_azure_client()
                self.assertEqual(context.exception.code, "configuration")
                self.assertNotIn("SENSITIVE", str(context.exception))

    def test_missing_sdk_is_reported_without_exposing_configuration(self):
        with patch.dict(os.environ, {"AZURE_LANGUAGE_ENDPOINT": "https://course.cognitiveservices.azure.com/", "AZURE_LANGUAGE_KEY": "fake-not-a-key"}, clear=True):
            with patch.dict("sys.modules", {"azure.ai.textanalytics": None}):
                with self.assertRaises(ServiceIssue) as context:
                    make_azure_client()
                self.assertEqual(context.exception.code, "dependency")


if __name__ == "__main__":
    unittest.main()
