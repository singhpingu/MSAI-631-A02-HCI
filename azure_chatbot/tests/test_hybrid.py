"""OFFLINE hybrid routing tests: all cloud-like responses are synthetic fixtures."""

import threading
import unittest

from azure_service import Scores, SentenceResult, SentimentResult, ServiceIssue
from engine import InvalidMessage
from hybrid import HybridAdapter


class FakeService:
    def __init__(self):
        self.calls = []
        self.error = None

    def analyze(self, text):
        self.calls.append(text)
        if self.error:
            raise self.error
        scores = Scores(0.8, 0.1, 0.1)
        return SentimentResult("positive", scores, (SentenceResult(text, "positive", scores),))


class HybridTests(unittest.TestCase):
    def setUp(self):
        self.service = FakeService()
        self.adapter = HybridAdapter(self.service)

    def test_local_commands_never_call_azure_even_with_permission(self):
        for text in ("hello", "help", "clone", "python", "reverse: sentiment: hello", "echo: sentiment: hello", "What is the weather?", "Please run sentiment on this text"):
            with self.subTest(text=text):
                reply = self.adapter.respond(text, cloud_consent=True)
                self.assertEqual(reply.source, "local")
        self.assertEqual(self.service.calls, [])

    def test_help_explains_both_modes_and_consent(self):
        reply = self.adapter.respond("help")
        self.assertIn("sentiment:", reply.text)
        self.assertIn("permission checkbox", reply.text)
        self.assertIn("Azure AI Language", reply.text)

    def test_sentiment_requires_explicit_permission(self):
        for kwargs in ({}, {"cloud_consent": False}):
            reply = self.adapter.respond("sentiment: example", **kwargs)
            self.assertEqual(reply.intent, "consent_required")
            self.assertEqual(reply.source, "local")
        self.assertEqual(self.service.calls, [])

    def test_permission_is_not_remembered_for_next_request(self):
        self.adapter.respond("sentiment: first", cloud_consent=True)
        reply = self.adapter.respond("sentiment: second")
        self.assertEqual(reply.intent, "consent_required")
        self.assertEqual(self.service.calls, ["first"])

    def test_boolean_permission_is_validated_before_cloud_call(self):
        for consent in ("true", 1, None, [], {}):
            with self.subTest(consent=consent), self.assertRaises(InvalidMessage):
                self.adapter.respond("sentiment: text", cloud_consent=consent)
        self.assertEqual(self.service.calls, [])

    def test_only_stripped_command_payload_is_sent(self):
        reply = self.adapter.respond("  SeNtImEnT :  The interface works.  ", cloud_consent=True)
        self.assertEqual(self.service.calls, ["The interface works."])
        self.assertEqual(reply.source, "azure")
        self.assertEqual(reply.intent, "sentiment")
        self.assertIn("Sentence 1", reply.text)
        self.assertIn("not certainty about a person's emotions", reply.text)
        self.assertEqual(reply.analysis["scores"]["positive"], 0.8)

    def test_empty_command_is_rejected_without_cloud_call(self):
        self.assertEqual(self.adapter.respond("sentiment").intent, "sentiment_usage")
        with self.assertRaises(InvalidMessage):
            self.adapter.respond("sentiment:  ", cloud_consent=True)
        self.assertEqual(self.service.calls, [])

    def test_malformed_messages_are_rejected_before_cloud_call(self):
        for text in (None, 7, "", "sentiment: \ud800", "sentiment: \x00", "sentiment: " + "x" * 1000):
            with self.subTest(value=repr(text)[:30]), self.assertRaises(InvalidMessage):
                self.adapter.respond(text, cloud_consent=True)
        self.assertEqual(self.service.calls, [])

    def test_service_failure_retains_local_commands_and_allows_later_retry(self):
        self.service.error = ServiceIssue("throttled", "Wait before trying again.")
        reply = self.adapter.respond("sentiment: example", cloud_consent=True)
        self.assertEqual(reply.intent, "azure_throttled")
        self.assertIsNone(reply.analysis)
        self.assertEqual(self.adapter.respond("hello").intent, "greeting")
        self.service.error = None
        self.assertEqual(self.adapter.respond("sentiment: retry", cloud_consent=True).source, "azure")

    def test_second_concurrent_request_does_not_reach_cloud(self):
        started, release = threading.Event(), threading.Event()
        service = self.service
        original = service.analyze
        def blocking_analyze(text):
            started.set()
            release.wait(timeout=5)
            return original(text)
        service.analyze = blocking_analyze
        worker = threading.Thread(target=self.adapter.respond, args=("sentiment: first",), kwargs={"cloud_consent": True})
        worker.start()
        try:
            self.assertTrue(started.wait(timeout=2))
            reply = self.adapter.respond("sentiment: second", cloud_consent=True)
            self.assertEqual(reply.intent, "cloud_busy")
            self.assertEqual(self.adapter.respond("hello").intent, "greeting")
        finally:
            release.set()
            worker.join(timeout=5)
        self.assertEqual(service.calls, ["first"])


if __name__ == "__main__":
    unittest.main()
