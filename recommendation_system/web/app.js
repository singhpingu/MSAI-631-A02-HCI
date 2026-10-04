/* Original browser controller prepared with AI assistance. No external scripts.
 * Sets avoid duplicate feedback; request cancellation prevents stale responses.
 */
"use strict";
const $ = (id) => document.getElementById(id);
const state = { liked: new Set(), hidden: new Set(), response: null,
  controller: null, sequence: 0, timer: null, ready: false, dirty: false };

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text; // Never interpolate user text as HTML.
  if (className) element.className = className;
  return element;
}

function status(text, error = false) {
  $("status").textContent = text;
  $("status").classList.toggle("error", error);
}

function preferences() {
  return { query: $("query").value,
    topics: [...document.querySelectorAll(".topic-option input:checked")].map((x) => x.value),
    max_minutes: Number($("minutes").value), level: $("level").value,
    format: $("format").value, count: Number($("count").value),
    diversity: Number($("diversity").value), liked_ids: [...state.liked], hidden_ids: [...state.hidden] };
}

function updateCounts() {
  $("feedback-count").textContent = `${state.liked.size} liked interests · ${state.hidden.size} hidden activities`;
}

function choicesChanged() {
  if (!state.ready) return;
  state.dirty = true;
  $("download").disabled = true;
  // Invalidate even a manual request when the profile changes while it is running.
  state.sequence += 1;
  state.controller?.abort();
  $("find-button").disabled = false;
  updateCounts();
  clearTimeout(state.timer);
  if ($("auto").checked) {
    status("Choices changed. Updating suggestions...");
    state.timer = setTimeout(recommend, 350);
  } else {
    status("Choices changed. Select Find activities to update the displayed suggestions.");
  }
}

function render(data) {
  $("cards").replaceChildren();
  for (const item of data.results) {
    const card = node("article", undefined, "card");
    const title = node("div", undefined, "card-title");
    title.append(node("span", String(item.rank), "rank"), node("h3", item.title));
    card.append(title, node("p", `${item.topic} · ${item.level} · ${item.duration_minutes} min · ${item.format}`, "meta"),
      node("p", item.description, "description"));
    for (const reason of item.reasons) card.append(node("p", reason, "reason"));
    card.append(node("p", item.similarity === null ? "Starter suggestion without a personalized similarity score"
      : `Text similarity ${item.similarity.toFixed(3)} · Variety adjustment ${item.diversity_penalty.toFixed(3)}`, "similarity"));
    const details = node("details");
    details.append(node("summary", "View the activity steps"));
    const steps = node("ol");
    for (const step of item.steps) steps.append(node("li", step));
    details.append(steps);
    card.append(details);
    const actions = node("div", undefined, "card-actions");
    const like = node("button", "More like this");
    like.type = "button";
    like.setAttribute("aria-label", `Use ${item.title} as an interest`);
    like.addEventListener("click", () => { state.liked.add(item.id); state.hidden.delete(item.id); choicesChanged(); });
    const hide = node("button", "Hide activity");
    hide.type = "button";
    hide.setAttribute("aria-label", `Hide ${item.title}`);
    hide.addEventListener("click", () => { state.hidden.add(item.id); state.liked.delete(item.id); choicesChanged(); });
    actions.append(like, hide);
    card.append(actions);
    $("cards").append(card);
  }
}

async function recommend() {
  clearTimeout(state.timer);
  state.controller?.abort();
  const sequence = ++state.sequence;
  state.controller = new AbortController();
  $("find-button").disabled = true;
  $("download").disabled = true;
  status("Finding activities that fit your choices...");
  try {
    const response = await fetch("/api/recommend", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify(preferences()),
      signal: state.controller.signal });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not load recommendations.");
    if (sequence !== state.sequence) return;
    state.response = data;
    state.dirty = false;
    render(data);
    status(`${data.notice} ${data.results.length} shown from ${data.candidate_count} eligible suggestions.`);
    $("download").disabled = false;
  } catch (error) {
    if (error.name !== "AbortError" && sequence === state.sequence) {
      status(`${error.message} Check that app.py is running, then try again.`, true);
    }
  } finally {
    if (sequence === state.sequence) $("find-button").disabled = false;
  }
}

$("preferences-form").addEventListener("submit", (event) => { event.preventDefault(); recommend(); });
$("preferences-form").addEventListener("input", (event) => {
  if (event.target.id !== "auto") choicesChanged();
});
$("auto").addEventListener("change", () => {
  clearTimeout(state.timer);
  if ($("auto").checked) recommend();
  else {
    // Turning the option off also cancels an update already in progress.
    state.sequence += 1;
    state.controller?.abort();
    $("find-button").disabled = false;
    status("Automatic updates are off. Select Find activities when you want new suggestions.");
  }
});
$("reset").addEventListener("click", () => {
  $("preferences-form").reset();
  state.liked.clear(); state.hidden.clear();
  updateCounts(); recommend();
});
$("add-seed").addEventListener("click", () => {
  const id = $("seed").value;
  if (id) { state.liked.add(id); state.hidden.delete(id); choicesChanged(); }
});
$("download").addEventListener("click", () => {
  if (!state.response || state.dirty) return;
  const file = new Blob([JSON.stringify({ captured_at: new Date().toISOString(),
    ...state.response }, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(file);
  const link = node("a"); link.href = url; link.download = "studypath_results.json";
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

async function start() {
  try {
    const response = await fetch("/api/catalogue");
    if (!response.ok) throw new Error("Could not load the activity catalogue.");
    const data = await response.json();
    const topics = node("div", undefined, "topic-list");
    for (const topic of data.topics) {
      const label = node("label", undefined, "topic-option");
      const input = node("input"); input.type = "checkbox"; input.value = topic;
      label.append(input, node("span", topic)); topics.append(label);
    }
    $("topic-options").append(topics);
    for (const item of data.activities) {
      const option = node("option", item.title); option.value = item.id; $("seed").append(option);
    }
    state.ready = true;
    await recommend();
  } catch (error) { status(`${error.message} Start app.py and reload the page.`, true); }
}
start();
