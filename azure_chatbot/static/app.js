"use strict";

// Render untrusted message text as text nodes, never as executable HTML.
const elements = Object.freeze({
  form: document.querySelector("#chat-form"),
  message: document.querySelector("#message"),
  conversation: document.querySelector("#conversation"),
  status: document.querySelector("#status"),
  send: document.querySelector("#send"),
  clear: document.querySelector("#clear"),
  consent: document.querySelector("#cloud-consent"),
});
let requestInProgress = false;

function addMessage(speaker, text, intent = "", source = "local") {
  const entry = document.createElement("article");
  entry.className = speaker === "You" ? "message user" : "message bot";
  const label = document.createElement("strong");
  label.textContent = speaker;
  const content = document.createElement("p");
  content.textContent = text;
  entry.append(label, content);
  if (intent) {
    const metadata = document.createElement("small");
    metadata.textContent = `${source === "azure" ? "Azure AI Language result" : "Local reply"} · ${intent.replaceAll("_", " ")}`;
    entry.append(metadata);
  }
  elements.conversation.append(entry);
  elements.conversation.scrollTop = elements.conversation.scrollHeight;
}

function resetConversation() {
  elements.conversation.replaceChildren();
  addMessage("Helper", "Hello! Type 'help' to see what I can do. Ask one question at a time.");
  elements.status.textContent = "";
  elements.consent.checked = false;
  elements.message.focus();
}

elements.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (requestInProgress) return;
  const message = elements.message.value.trim();
  if (!message) {
    elements.status.textContent = "Enter a message before sending.";
    elements.message.focus();
    return;
  }
  requestInProgress = true;
  const cloudConsent = elements.consent.checked;
  const isSentiment = /^sentiment\s*:/i.test(message);
  elements.consent.checked = false;
  elements.consent.disabled = true;
  elements.send.disabled = true;
  elements.clear.disabled = true;
  elements.status.textContent = isSentiment && cloudConsent ? "Waiting for Azure sentiment analysis…" : "Preparing a local reply…";
  addMessage("You", message);
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 25000);
  try {
    const response = await fetch("/api/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, cloud_consent: cloudConsent }),
      signal: controller.signal,
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "The server could not process the message.");
    addMessage("Helper", payload.reply.text, payload.reply.intent, payload.reply.source);
    // Preserve text when permission or configuration needs attention.
    if (payload.reply.intent !== "consent_required" && !payload.reply.intent.startsWith("azure_") && payload.reply.intent !== "cloud_busy") elements.message.value = "";
    elements.status.textContent = "Reply ready.";
  } catch (error) {
    elements.status.textContent = error.name === "AbortError"
      ? "The request timed out. Azure may already have received it. Wait before manually retrying; check that app.py is still running."
      : `Unable to get a reply. ${error.message} Check that app.py is still running, then retry.`;
  } finally {
    window.clearTimeout(timeout);
    requestInProgress = false;
    elements.send.disabled = false;
    elements.clear.disabled = false;
    elements.consent.disabled = false;
    elements.message.focus();
  }
});

elements.message.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    elements.form.requestSubmit();
  }
});
document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    elements.message.value = button.dataset.prompt;
    elements.message.focus();
  });
});
elements.clear.addEventListener("click", resetConversation);
resetConversation();
