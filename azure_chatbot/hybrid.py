"""Keep ordinary rules local and route one explicit, authorized command to Azure.

Original source: Yasharth Singh's earlier traditional chatbot project,
https://github.com/singhpingu/MSAI-631-A02-HCI/tree/main/traditional_chatbot

The original rule engine, HTTP server, browser interface, and tests were copied
and adapted into a separate azure_chatbot folder to preserve the earlier
assignment and isolate the Azure dependency and cloud behavior. This adapter
and azure_service.py add the new sentiment integration.

AI disclosure: OpenAI ChatGPT/Codex assisted with planning, code generation,
review, tests, troubleshooting, and documentation. Azure AI Language performs
the explicitly requested sentiment analysis at runtime. The student must
review, run, verify, and revise this work before submitting it, disclose AI
assistance in the report, and accept responsibility for the final submission.
"""

from __future__ import annotations

import re
from threading import Lock

from azure_service import AzureSentimentService, SentimentService, ServiceIssue
from engine import ChatReply, HELP_TEXT, InvalidMessage, RuleBasedAdapter, validate_message


SENTIMENT_COMMAND = re.compile(r"^sentiment\s*:(.*)$", re.IGNORECASE | re.DOTALL)
HYBRID_HELP = (
    HELP_TEXT.replace("I am a traditional rule based course development helper. I use fixed rules, not an LLM.",
                      "I am a hybrid course development helper. Ordinary replies use fixed local rules.")
    + "\n\nCloud capability: sentiment: your English text. Select the Azure permission checkbox before sending. "
    "Only the text after the colon is sent to Azure AI Language for that request. "
    "The result includes document and sentence sentiment with confidence scores. "
    "I do not generate open ended answers or use an LLM."
)
LIMITATION = (
    "These scores describe Azure's classification of the wording, not certainty about a person's emotions. "
    "Context, sarcasm, and mixed wording can produce misleading results."
)


class HybridAdapter:
    """Reuse the original rule engine; keep the cloud service replaceable in tests."""

    def __init__(self, service: SentimentService | None = None):
        self.local = RuleBasedAdapter()
        self.service = service if service is not None else AzureSentimentService()
        self._cloud_lock = Lock()

    def respond(self, message: object, *, cloud_consent: bool = False) -> ChatReply:
        cleaned = validate_message(message)
        if type(cloud_consent) is not bool:
            raise InvalidMessage("cloud_consent must be true or false.")
        command = SENTIMENT_COMMAND.fullmatch(cleaned)
        if command is None:
            if re.fullmatch(r"sentiment[.!?\s]*", cleaned, re.IGNORECASE):
                return ChatReply("To analyze English text, enter 'sentiment: your text' and select the Azure permission checkbox for that request.", "sentiment_usage")
            local_reply = self.local.respond(cleaned)
            if local_reply.intent == "help":
                return ChatReply(HYBRID_HELP, "help")
            return local_reply

        text = command.group(1).strip()
        if not text:
            raise InvalidMessage("Add English text after 'sentiment:', for example 'sentiment: The instructions were helpful.'")
        if not cloud_consent:
            return ChatReply("This command sends the text after 'sentiment:' to Azure AI Language. Select the Azure permission checkbox and send again if you agree. Nothing was sent to Azure.", "consent_required")
        if not self._cloud_lock.acquire(blocking=False):
            return ChatReply("Another Azure request is still running. Wait for its result before sending again. This request was not sent to Azure.", "cloud_busy")
        try:
            try:
                result = self.service.analyze(text)
            except ServiceIssue as error:
                return ChatReply(str(error), f"azure_{error.code}")
            lines = [
                f"Azure document sentiment: {result.sentiment}",
                f"Confidence scores — positive: {result.scores.positive:.3f}; neutral: {result.scores.neutral:.3f}; negative: {result.scores.negative:.3f}.",
            ]
            for index, sentence in enumerate(result.sentences, start=1):
                lines.append(f"Sentence {index}: {sentence.text}\nSentiment: {sentence.sentiment}; positive: {sentence.scores.positive:.3f}; neutral: {sentence.scores.neutral:.3f}; negative: {sentence.scores.negative:.3f}.")
            lines.append(LIMITATION)
            return ChatReply("\n\n".join(lines), "sentiment", "azure", result.to_dict())
        finally:
            self._cloud_lock.release()
