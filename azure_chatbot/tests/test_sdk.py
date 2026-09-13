"""Exercise the installed official SDK over a fake transport; NO Azure traffic."""

import json
import unittest

from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from azure.core.pipeline.transport import HttpResponse, HttpTransport

from azure_service import AzureSentimentService, ServiceIssue


class SyntheticResponse(HttpResponse):
    def __init__(self, request, status, payload):
        super().__init__(request, None)
        self.status_code = status
        self.headers = {"Content-Type": "application/json", "Retry-After": "0"}
        self.content_type = "application/json"
        self.reason = "Synthetic offline fixture"
        self._body = json.dumps(payload).encode()

    def body(self):
        return self._body


class SyntheticTransport(HttpTransport):
    def __init__(self, status=200):
        self.status = status
        self.requests = []

    def open(self):
        pass

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def send(self, request, **kwargs):
        self.requests.append((request, kwargs))
        if self.status != 200:
            return SyntheticResponse(request, self.status, {"error": {"code": "TooManyRequests", "message": "SYNTHETIC private error"}})
        confidence = {"positive": 0.8, "neutral": 0.1, "negative": 0.1}
        payload = {"documents": [{"id": "0", "sentiment": "positive", "confidenceScores": confidence,
                    "sentences": [{"text": "Synthetic input.", "sentiment": "positive", "confidenceScores": confidence, "offset": 0, "length": 16}], "warnings": []}],
                   "errors": [], "modelVersion": "synthetic-offline-fixture"}
        return SyntheticResponse(request, 200, {"kind": "SentimentAnalysisResults", "results": payload})


class SDKContractTests(unittest.TestCase):
    def client(self, transport):
        return TextAnalyticsClient(
            endpoint="https://offline-fixture.cognitiveservices.azure.com",
            credential=AzureKeyCredential("offline-fixture-not-a-real-key"),
            api_version="2023-04-01", transport=transport, retry_total=0,
            connection_timeout=5, read_timeout=10, logging_enable=False,
        )

    def test_official_sdk_serializes_and_deserializes_with_fake_transport(self):
        transport = SyntheticTransport()
        result = AzureSentimentService(lambda: self.client(transport)).analyze("Synthetic input.")
        self.assertEqual(result.sentiment, "positive")
        self.assertEqual(result.sentences[0].text, "Synthetic input.")
        self.assertEqual(len(transport.requests), 1)
        request, options = transport.requests[0]
        payload = json.loads(request.body)
        self.assertEqual(payload["analysisInput"]["documents"][0]["text"], "Synthetic input.")
        self.assertEqual(payload["analysisInput"]["documents"][0]["language"], "en")
        self.assertTrue(payload["parameters"]["loggingOptOut"])
        self.assertEqual(options["connection_timeout"], 5)
        self.assertEqual(options["read_timeout"], 10)

    def test_sdk_429_is_not_retried_and_error_is_sanitized(self):
        transport = SyntheticTransport(429)
        with self.assertRaises(ServiceIssue) as context:
            AzureSentimentService(lambda: self.client(transport)).analyze("Synthetic input.")
        self.assertEqual(context.exception.code, "throttled")
        self.assertEqual(len(transport.requests), 1)
        self.assertNotIn("private error", str(context.exception))


if __name__ == "__main__":
    unittest.main()
