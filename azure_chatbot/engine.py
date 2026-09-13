"""Deterministic chatbot engine; the only knowledge is the text in this file."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, Protocol


MAX_MESSAGE_LENGTH = 1000
REPOSITORY_URL = "https://github.com/singhpingu/MSAI-631-A02-HCI.git"


class InvalidMessage(ValueError):
    """A user input validation error that can safely be shown in the interface."""


@dataclass(frozen=True, slots=True)
class ChatReply:
    """Stable response shape shared by the engine, API, and future adapters."""

    text: str
    intent: str
    source: str = "local"
    analysis: dict[str, object] | None = None


class ChatAdapter(Protocol):
    """Extension boundary: a future service must implement this same method.

    Implementations receive explicit consent separately from user text. The
    hybrid adapter routes only the sentiment command to a cloud service.
    """

    def respond(self, message: object, *, cloud_consent: bool = False) -> ChatReply:
        """Validate input and return a reply, or raise InvalidMessage."""
        ...


@dataclass(frozen=True, slots=True)
class Rule:
    """A named, compiled rule with a deterministic response function."""

    name: str
    pattern: re.Pattern[str]
    answer: Callable[[re.Match[str]], str]


def fixed_answer(text: str) -> Callable[[re.Match[str]], str]:
    """Keep rule definitions concise without capturing changing loop values."""
    return lambda match: text


CAPABILITIES = (
    "Greet you and respond to thanks.",
    "Explain Git cloning, repository privacy, Python, virtual environments, and tests.",
    "Explain how this traditional chatbot works.",
    "Echo or reverse text with 'echo: your text' or 'reverse: your text'.",
    "Ask for a clearer question when it cannot identify one supported topic.",
)

HELP_TEXT = (
    "I am a traditional rule based course development helper. I use fixed rules, "
    "not an LLM. My capabilities are:\n"
    + "\n".join(f"• {item}" for item in CAPABILITIES)
    + "\nTry: 'clone', 'repository', 'python', 'virtual environment', 'tests', "
    "'chatbot', 'echo: hello', or 'reverse: hello'. I do not run commands, "
    "access your files, or check GitHub."
)


def compile_pattern(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE | re.DOTALL)


# Commands and social phrases precede FAQ matching so quoted command text is
# treated as text, not as a second request to classify.
COMMAND_RULES: tuple[Rule, ...] = (
    Rule("help", compile_pattern(r"^(?:help|capabilities|what can you do)[.!?\s]*$"), fixed_answer(HELP_TEXT)),
    Rule("greeting", compile_pattern(r"^(?:hi|hello|hey|good morning|good afternoon|good evening)[.!?\s]*$"),
         fixed_answer("Hello! I can help with this course's local development setup. Type 'help' to see my capabilities.")),
    Rule("thanks", compile_pattern(r"^(?:thanks|thank you|thank you very much)[.!?\s]*$"),
         fixed_answer("You are welcome. What would you like to try next?")),
    Rule("goodbye", compile_pattern(r"^(?:bye|goodbye|exit|quit)[.!?\s]*$"),
         fixed_answer("Goodbye! You may close this tab. To stop the server, press Ctrl+C in the terminal.")),
    Rule("echo", compile_pattern(r"^echo\s*:\s*(.+)$"), lambda match: match.group(1).strip()),
    Rule("reverse", compile_pattern(r"^reverse\s*:\s*(.+)$"), lambda match: match.group(1).strip()[::-1]),
    Rule("command_usage", compile_pattern(r"^(?:echo|reverse)(?:\s*:)?\s*$"),
         fixed_answer("Include text after a colon, for example 'echo: hello' or 'reverse: hello'.")),
)


# These names are intentionally explicit. They are not learned categories.
FAQ_RULES: tuple[Rule, ...] = (
    Rule("clone", compile_pattern(r"\b(?:clone|cloning|download repository)\b"), fixed_answer(
        "In PowerShell, create C:\\Users\\ysingh\\Desktop\\UC, change to that folder, "
        f"and run: git clone {REPOSITORY_URL}\n"
        "If the repository is private, authenticate with the Git credential manager's browser sign in. "
        "Do not put a password or access token in the clone URL. Open the cloned folder in VS Code.")),
    Rule("repository", compile_pattern(r"\b(?:repository|repo|github|private|collaborator)\b"), fixed_answer(
        "This course repository is https://github.com/singhpingu/MSAI-631-A02-HCI. "
        "Keep it private and verify that AlanAtUC has the required access in GitHub Settings. "
        "I cannot inspect the repository, send invitations, or confirm permissions. "
        "Commit source files and documentation, and exclude .venv, secrets, and local logs.")),
    Rule("python", compile_pattern(r"\b(?:python|interpreter|pip)\b"), fixed_answer(
        "Use Python 3.12 for consistency with this course project. In PowerShell, run "
        "py -3.12 --version. The Python extension in VS Code helps select an interpreter; "
        "the extension does not install Python itself. Local replies use the standard library; cloud sentiment needs the Azure Text Analytics SDK.")),
    Rule("virtual_environment", compile_pattern(r"\b(?:venv|virtual environment|virtualenv|activate|activation)\b"), fixed_answer(
        "From the azure_chatbot folder, run: py -3.12 -m venv .venv\n"
        "Then run: .\\.venv\\Scripts\\python.exe app.py\n"
        "Activation is optional. Calling the interpreter directly also avoids PowerShell activation script policy issues.")),
    Rule("tests", compile_pattern(r"\b(?:test|tests|testing|unittest|validate|validation)\b"), fixed_answer(
        "From the azure_chatbot folder, run: .\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v\n"
        "The suite checks replies, malformed messages, fallback behavior, HTTP requests, and browser safety headers. "
        "Use manual browser checks too; automated tests do not establish usability.")),
    Rule("chatbot", compile_pattern(r"\b(?:chatbot|algorithm|rules|traditional|llm|model)\b"), fixed_answer(
        "This chatbot matches regular expressions against your message and returns predefined replies. "
        "The local rules do not train a model or remember previous messages. The hybrid adapter adds Azure sentiment only when explicitly requested and authorized. "
        "Its strengths are predictable behavior and inspectable rules; its limits include vocabulary gaps "
        "and an inability to reason about unfamiliar questions.")),
)


def validate_message(message: object) -> str:
    """Reject malformed input before invoking any adapter."""
    # Bound input before either local regex matching or cloud routing.
    if not isinstance(message, str):
        raise InvalidMessage("The message must be text.")
    if len(message) > MAX_MESSAGE_LENGTH:
        raise InvalidMessage(f"Keep the message to {MAX_MESSAGE_LENGTH} characters or fewer.")
    cleaned = message.strip()
    if not cleaned:
        raise InvalidMessage("Please enter a message before sending.")
    if any(ord(char) < 32 and char not in "\n\r\t" for char in cleaned):
        raise InvalidMessage("Remove control characters and try again.")
    if any(0xD800 <= ord(char) <= 0xDFFF for char in cleaned):
        raise InvalidMessage("The message contains invalid Unicode text. Please retype it.")

    return cleaned


class RuleBasedAdapter:
    """A local implementation of ChatAdapter using ordered, inspectable rules."""

    def respond(self, message: object, *, cloud_consent: bool = False) -> ChatReply:
        cleaned = validate_message(message)

        for rule in COMMAND_RULES:
            match = rule.pattern.search(cleaned)
            if match:
                return ChatReply(rule.answer(match), rule.name)

        matches = [(rule, rule.pattern.search(cleaned)) for rule in FAQ_RULES]
        matches = [(rule, match) for rule, match in matches if match is not None]

        # A clone question naturally mentions a repository. Likewise creating a
        # virtual environment naturally mentions Python. Treat these as one topic.
        names = {rule.name for rule, _ in matches}
        if "clone" in names:
            matches = [(rule, match) for rule, match in matches if rule.name != "repository"]
        if "virtual_environment" in names:
            matches = [(rule, match) for rule, match in matches if rule.name != "python"]

        if len(matches) > 1:
            topics = ", ".join(rule.name.replace("_", " ") for rule, _ in matches)
            return ChatReply(
                f"I found more than one supported topic: {topics}. Please ask about one topic at a time.",
                "clarification",
            )
        if matches:
            rule, match = matches[0]
            return ChatReply(rule.answer(match), rule.name)
        return ChatReply(
            "I do not have a rule for that question. Try 'help' for supported topics, "
            "or ask about clone, repository, Python, virtual environment, tests, or chatbot.",
            "fallback",
        )
