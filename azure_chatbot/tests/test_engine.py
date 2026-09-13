"""Behavior tests for the inspectable traditional rules, including limitations."""

import unittest

from engine import InvalidMessage, MAX_MESSAGE_LENGTH, RuleBasedAdapter


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.bot = RuleBasedAdapter()

    def test_greeting_normalizes_case_and_whitespace(self):
        self.assertEqual(self.bot.respond("  HeLLo!  ").intent, "greeting")

    def test_capabilities_and_limitations_are_disclosed(self):
        reply = self.bot.respond("help")
        self.assertEqual(reply.intent, "help")
        for phrase in ("not an LLM", "Echo", "do not run commands", "virtual environment"):
            self.assertIn(phrase, reply.text)

    def test_each_supported_faq_topic(self):
        cases = {
            "How do I clone the repository?": "clone",
            "Who can see my private GitHub repository?": "repository",
            "Which Python interpreter should I use?": "python",
            "How do I create a Python virtual environment?": "virtual_environment",
            "How do I run tests?": "tests",
            "How does this chatbot work?": "chatbot",
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                self.assertEqual(self.bot.respond(message).intent, expected)

    def test_thanks_and_goodbye(self):
        self.assertEqual(self.bot.respond("thank you").intent, "thanks")
        self.assertIn("Ctrl+C", self.bot.respond("bye").text)

    def test_echo_preserves_case_and_markup_as_plain_text(self):
        self.assertEqual(self.bot.respond("echo: <script>Hello</script>").text, "<script>Hello</script>")

    def test_reverse_command(self):
        self.assertEqual(self.bot.respond("reverse: hello").text, "olleh")

    def test_command_without_payload_explains_usage(self):
        for message in ("echo", "echo:", "reverse:  "):
            with self.subTest(message=message):
                self.assertEqual(self.bot.respond(message).intent, "command_usage")

    def test_multiple_topics_request_clarification(self):
        self.assertEqual(self.bot.respond("Tell me about Python and repository privacy").intent, "clarification")

    def test_unknown_question_returns_useful_fallback(self):
        reply = self.bot.respond("What is the weather tomorrow?")
        self.assertEqual(reply.intent, "fallback")
        self.assertIn("help", reply.text)

    def test_word_boundaries_avoid_substring_matches(self):
        self.assertEqual(self.bot.respond("The latest report is ready").intent, "fallback")

    def test_empty_and_whitespace_messages_are_rejected(self):
        for value in ("", " ", "\n\t"):
            with self.subTest(value=value), self.assertRaises(InvalidMessage):
                self.bot.respond(value)

    def test_non_text_messages_are_rejected(self):
        for value in (None, 3, True, [], {}):
            with self.subTest(value=value), self.assertRaises(InvalidMessage):
                self.bot.respond(value)

    def test_length_boundary_is_enforced(self):
        self.assertEqual(self.bot.respond("x" * MAX_MESSAGE_LENGTH).intent, "fallback")
        with self.assertRaises(InvalidMessage):
            self.bot.respond("x" * (MAX_MESSAGE_LENGTH + 1))

    def test_control_characters_are_rejected(self):
        with self.assertRaises(InvalidMessage):
            self.bot.respond("hello\x00")

    def test_lone_unicode_surrogates_are_rejected(self):
        with self.assertRaises(InvalidMessage):
            self.bot.respond("echo: \ud800")

    def test_unicode_and_repeated_input_are_deterministic(self):
        self.assertEqual(self.bot.respond("echo: café"), self.bot.respond("echo: café"))
        self.assertEqual(self.bot.respond("echo: café").text, "café")


if __name__ == "__main__":
    unittest.main()
