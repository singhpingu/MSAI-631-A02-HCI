/** Browser orchestration. Behavior stays in memory and never leaves this tab. */
import { LogisticModel } from './model.mjs';
import { AdaptiveController } from './adaptation.mjs';

const byId = id => document.getElementById(id);
const names = Object.freeze({ balanced: 'Balanced', guided: 'Guided', focused: 'Focused' });
let lessons, controller, index = 0, completed = 0, submitted = false, hintRequested = false;
let simulated = false, activeMs = 0, activeSince = null;
const percent = value => `${Math.round(value * 100)}%`;

function pauseTimer() {
  if (activeSince !== null) activeMs += performance.now() - activeSince;
  activeSince = null;
}
function resumeTimer() {
  if (controller?.enabled && !submitted && !document.hidden && document.hasFocus() && activeSince === null) activeSince = performance.now();
}
document.addEventListener('visibilitychange', () => document.hidden ? pauseTimer() : resumeTimer());
window.addEventListener('blur', pauseTimer);
window.addEventListener('focus', resumeTimer);

function validateLessons(data) {
  if (!Array.isArray(data) || data.length === 0) throw new TypeError('No study content.');
  const seen = new Set();
  for (const task of data) {
    if (typeof task.id !== 'string' || seen.has(task.id)
        || !['title', 'lesson', 'example', 'question', 'hint', 'explanation', 'source'].every(key => typeof task[key] === 'string')
        || !Array.isArray(task.options) || task.options.length < 2 || !task.options.every(text => typeof text === 'string')
        || !Number.isInteger(task.answer) || task.answer < 0 || task.answer >= task.options.length
        || !Number.isFinite(task.expectedMs) || task.expectedMs <= 0) throw new TypeError('Invalid study content.');
    seen.add(task.id);
  }
}

function renderStatus() {
  const { enabled, mode, history, score, features, pending } = controller;
  byId('ai-enabled').checked = enabled;
  byId('manual-mode').value = mode;
  byId('demo-guided').disabled = !enabled;
  byId('demo-focused').disabled = !enabled;
  byId('demo-label').hidden = !simulated;
  byId('signals').hidden = !enabled || !features;
  let status = 'AI adaptation is off. Your chosen view is active.';
  if (enabled && history.size < 3) status = `Learning the session pattern: ${history.size} of 3 observations collected.`;
  else if (enabled && pending) status = `${names[pending]} view is recommended for the next question.`;
  else if (enabled) status = `${names[mode]} view is active. Monitoring the last ${history.size} observations.`;
  byId('adaptation-status').textContent = status;
  byId('score-detail').textContent = enabled && score !== null
    ? `Synthetic demonstration score: ${percent(score)} for more guidance. This is not a validated estimate of your learning needs.`
    : 'Enabling AI begins a new observation window. No new observations are collected while it is off.';
  if (features) ['error-signal', 'hint-signal', 'slow-signal'].forEach((id, offset) => { byId(id).textContent = percent(features[offset]); });
}

function applyView() {
  document.body.dataset.mode = controller.mode;
  byId('view-badge').textContent = `${names[controller.mode]} view`;
  byId('lesson').open = controller.mode !== 'focused';
  byId('example-text').hidden = controller.mode !== 'guided';
  byId('hint-text').hidden = controller.mode !== 'guided';
  byId('hint-button').textContent = controller.mode === 'guided' ? 'Hide hint' : 'Show hint';
  byId('hint-button').setAttribute('aria-expanded', String(controller.mode === 'guided'));
  renderStatus();
}

function renderTask(focus = false) {
  submitted = false; hintRequested = false; activeMs = 0; activeSince = null;
  const task = lessons[index];
  byId('task-progress').textContent = `Question ${index + 1} of ${lessons.length}`;
  byId('completed-count').textContent = `${completed} completed${simulated ? ' · simulated session' : ''}`;
  byId('progress').max = lessons.length; byId('progress').value = index + 1;
  for (const [id, key] of [['practice-heading', 'title'], ['lesson-text', 'lesson'], ['example-text', 'example'], ['question', 'question'], ['hint-text', 'hint']]) byId(id).textContent = task[key];
  byId('source-credit').textContent = `Concept source: ${task.source}`;
  byId('choices').replaceChildren();
  task.options.forEach((text, optionIndex) => {
    const label = document.createElement('label'); label.className = 'choice';
    const input = document.createElement('input'); input.type = 'radio'; input.name = 'answer'; input.value = String(optionIndex); input.required = true;
    const span = document.createElement('span'); span.textContent = text;
    label.append(input, span); byId('choices').append(label);
  });
  byId('answer-options').disabled = false; byId('submit-answer').disabled = false;
  byId('feedback').hidden = true; byId('next-task').hidden = true;
  applyView(); resumeTimer();
  if (focus) byId('practice').focus();
}

function resetSession() {
  pauseTimer(); controller.reset(); index = 0; completed = 0; simulated = false; renderTask();
}

byId('answer-form').addEventListener('submit', event => {
  event.preventDefault();
  if (submitted) return;
  const selected = new FormData(event.currentTarget).get('answer');
  if (selected === null) return;
  pauseTimer(); submitted = true; completed += 1;
  const task = lessons[index], correct = Number(selected) === task.answer;
  controller.observe({ correct, hintRequested, activeMs, expectedMs: task.expectedMs });
  byId('answer-options').disabled = true; byId('submit-answer').disabled = true;
  byId('feedback').hidden = false; byId('feedback').dataset.result = correct ? 'correct' : 'incorrect';
  byId('feedback').textContent = `${correct ? 'Correct.' : 'Review this idea.'} ${task.explanation}`;
  byId('next-task').hidden = false;
  byId('completed-count').textContent = `${completed} completed${simulated ? ' · simulated session' : ''}`;
  renderStatus();
});
byId('hint-button').addEventListener('click', () => {
  const show = byId('hint-text').hidden;
  byId('hint-text').hidden = !show; byId('hint-button').textContent = show ? 'Hide hint' : 'Show hint';
  byId('hint-button').setAttribute('aria-expanded', String(show));
  if (show && !submitted) hintRequested = true; // Automatically visible hints are not requests.
});
byId('next-task').addEventListener('click', () => {
  if (!submitted) return;
  controller.applyAtBoundary(); index = (index + 1) % lessons.length; renderTask(true);
});
byId('ai-enabled').addEventListener('change', event => {
  // New consent starts a fresh history; choosing off retains the current view.
  pauseTimer(); activeMs = 0;
  if (event.target.checked) { controller.history.clear(); controller.score = null; controller.features = null; controller.cooldown = 0; }
  controller.setEnabled(event.target.checked); resumeTimer(); renderStatus();
});
byId('manual-mode').addEventListener('change', event => { pauseTimer(); controller.setManual(event.target.value); applyView(); });
byId('reset').addEventListener('click', () => { resetSession(); byId('ai-enabled').focus(); });

function simulate(mode) {
  if (!controller.enabled) return;
  resetSession(); controller.setEnabled(true); simulated = true;
  for (let count = 0; count < 4; count += 1) controller.observe({ correct: mode === 'focused', hintRequested: mode === 'guided', activeMs: mode === 'guided' ? 70000 : 8000, expectedMs: 40000 });
  controller.applyAtBoundary(); renderTask();
}
byId('demo-guided').addEventListener('click', () => simulate('guided'));
byId('demo-focused').addEventListener('click', () => simulate('focused'));

async function loadJson(path) {
  const response = await fetch(path, { cache: 'no-store' });
  if (!response.ok) throw new Error(`Unable to load ${path}.`);
  return response.json();
}
try {
  const [content, model] = await Promise.all([loadJson('/lessons.json'), loadJson('/model.json')]);
  validateLessons(content); lessons = content; controller = new AdaptiveController(new LogisticModel(model));
  byId('loading').hidden = true; byId('workspace').hidden = false; renderTask();
} catch (error) {
  byId('loading').hidden = true; byId('fatal').hidden = false;
  byId('fatal').textContent = 'The app could not load. Run python3 app.py from the extracted project folder, then open its printed local address. Check that data/model.json and data/lessons.json are present.';
  console.error(error);
}
