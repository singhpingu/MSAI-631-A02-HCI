"""Azure SDK boundary. No imports, credentials, or network work until requested."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import os
from typing import Callable, Protocol
from urllib.parse import urlsplit


class ServiceIssue(Exception):
    """An intentionally sanitized error suitable for the browser."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class Scores:
    positive: float
    neutral: float
    negative: float


@dataclass(frozen=True, slots=True)
class SentenceResult:
    text: str
    sentiment: str
    scores: Scores


@dataclass(frozen=True, slots=True)
class SentimentResult:
    sentiment: str
    scores: Scores
    sentences: tuple[SentenceResult, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class SentimentService(Protocol):
    def analyze(self, text: str) -> SentimentResult:
        """Return a service result or raise a sanitized ServiceIssue."""
        ...


def make_azure_client():
    """Read backend-only configuration and construct the official SDK client.

    Credentials are never accepted in an HTTP request, returned to the browser,
    placed in source files, or printed. No network request is made here.
    """
    endpoint = os.environ.get("AZURE_LANGUAGE_ENDPOINT", "").strip()
    key = os.environ.get("AZURE_LANGUAGE_KEY", "").strip()
    if not endpoint or not key:
        raise ServiceIssue("configuration", "Azure is not configured. Set AZURE_LANGUAGE_ENDPOINT and AZURE_LANGUAGE_KEY in the terminal that starts app.py. Local commands still work.")
    try:
        parsed = urlsplit(endpoint)
        valid_host = parsed.hostname is not None and (
            parsed.hostname.endswith(".cognitiveservices.azure.com")
            or parsed.hostname.endswith(".api.cognitive.microsoft.com")
        )
        valid = parsed.scheme == "https" and valid_host and parsed.port in (None, 443)
        valid = valid and not parsed.username and not parsed.password
        valid = valid and parsed.path in ("", "/") and not parsed.query and not parsed.fragment
    except ValueError:
        valid = False
    if not valid:
        raise ServiceIssue("configuration", "Use the HTTPS endpoint shown in your Azure Language resource's Keys and Endpoint page. Copy the root endpoint, without an API path, query, or credential.")
    try:
        from azure.ai.textanalytics import TextAnalyticsClient
        from azure.core.credentials import AzureKeyCredential
    except ImportError:
        raise ServiceIssue("dependency", "The Azure SDK is missing. Install requirements.txt using this project's virtual environment, then restart app.py.") from None
    return TextAnalyticsClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key),
        api_version="2023-04-01",
        retry_total=0,
        connection_timeout=5,
        read_timeout=10,
        logging_enable=False,
    )


def service_issue(error: Exception) -> ServiceIssue:
    """Do not include raw SDK exception strings, URLs, headers, or request text."""
    if isinstance(error, ServiceIssue):
        return error
    status = getattr(error, "status_code", None)
    if status in (401, 403):
        return ServiceIssue("authentication", "Azure rejected access. Check that the key and endpoint belong to the same Language resource and that key authentication and network access are allowed. Do not paste the key into chat or a screenshot.")
    if status == 429:
        return ServiceIssue("throttled", "Azure's request limit or free allowance may have been reached. Wait and check resource usage before submitting again. No automatic retry was made.")
    if status in (400, 404, 413, 422):
        return ServiceIssue("request", "Azure could not analyze this request. Check the Language resource endpoint and try a shorter English sentence. Local commands still work.")
    if isinstance(error, (TimeoutError, ConnectionError)) or type(error).__name__ in ("ServiceRequestError", "ServiceResponseError"):
        return ServiceIssue("network", "The Azure request timed out or could not connect. Check internet access and the endpoint. Azure may already have received the text; wait before manually retrying.")
    if isinstance(status, int) and status >= 500:
        return ServiceIssue("unavailable", "Azure is temporarily unavailable. Try later; local commands still work. No automatic retry was made.")
    return ServiceIssue("service", "The Azure request could not be completed. Check the resource configuration and SDK installation. No sentiment result is available; local commands still work.")


def _scores(value: object) -> Scores:
    values = [float(getattr(value, label)) for label in ("positive", "neutral", "negative")]
    if any(not math.isfinite(score) or not 0 <= score <= 1 for score in values):
        raise ValueError("Unexpected confidence score")
    return Scores(*values)


def _label(value: object, *, document: bool = False) -> str:
    labels = {"positive", "neutral", "negative"}
    if document:
        labels.add("mixed")
    if value not in labels:
        raise ValueError("Unexpected sentiment label")
    return str(value)


class AzureSentimentService:
    """Analyze one document once. Inject a fake factory only in offline tests."""

    def __init__(self, client_factory: Callable = make_azure_client):
        self._client_factory = client_factory

    def analyze(self, text: str) -> SentimentResult:
        client = None
        try:
            client = self._client_factory()
            results = client.analyze_sentiment(
                documents=[text],
                language="en",
                show_opinion_mining=False,
                disable_service_logs=True,
                logging_enable=False,
                retry_total=0,
                connection_timeout=5,
                read_timeout=10,
            )
            if len(results) != 1:
                raise ValueError("Unexpected result count")
            result = results[0]
            if result.is_error:
                raise ServiceIssue("document", "Azure returned a document error. Try a shorter English sentence without sensitive information. No sentiment result is available.")
            sentences = tuple(
                SentenceResult(str(sentence.text), _label(sentence.sentiment), _scores(sentence.confidence_scores))
                for sentence in result.sentences
            )
            return SentimentResult(_label(result.sentiment, document=True), _scores(result.confidence_scores), sentences)
        except Exception as error:
            raise service_issue(error) from None
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    # Cleanup must not replace a valid result or expose raw data.
                    pass
