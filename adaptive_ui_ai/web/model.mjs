/** Model inference and bounded session data. No storage, networking or DOM use. */
export const FEATURE_NAMES = Object.freeze(['error_rate', 'hint_rate', 'slow_rate']);

export class RingBuffer {
  #items;
  #next = 0;
  #size = 0;

  constructor(capacity = 5) {
    if (!Number.isInteger(capacity) || capacity < 1) throw new RangeError('Invalid capacity.');
    this.#items = new Array(capacity);
  }

  get size() { return this.#size; }

  push(observation) {
    this.#items[this.#next] = Object.freeze({ ...observation });
    this.#next = (this.#next + 1) % this.#items.length;
    this.#size = Math.min(this.#size + 1, this.#items.length);
  }

  values() {
    // Return oldest to newest; callers cannot mutate the stored array.
    const start = (this.#next - this.#size + this.#items.length) % this.#items.length;
    return Array.from({ length: this.#size }, (_, index) => this.#items[(start + index) % this.#items.length]);
  }

  clear() { this.#items.fill(undefined); this.#next = 0; this.#size = 0; }
}

export function validateObservation(row) {
  if (!row || typeof row.correct !== 'boolean' || typeof row.hintRequested !== 'boolean'
      || !Number.isFinite(row.activeMs) || row.activeMs < 0
      || !Number.isFinite(row.expectedMs) || row.expectedMs <= 0) {
    throw new TypeError('Invalid completed-task observation.');
  }
}

export function extractFeatures(observations) {
  if (!Array.isArray(observations) || observations.length === 0) throw new RangeError('No observations.');
  let errors = 0, hints = 0, slow = 0;
  for (const row of observations) {
    validateObservation(row);
    errors += Number(!row.correct);
    hints += Number(row.hintRequested);
    // Visible-page time only; timing is a weak demo signal, not an ability measure.
    slow += Number(row.activeMs > row.expectedMs);
  }
  return [errors, hints, slow].map(total => total / observations.length);
}

export class LogisticModel {
  #weights;
  #bias;

  constructor(model) {
    if (model?.schema_version !== 1 || model.algorithm !== 'logistic_regression'
        || JSON.stringify(model.feature_names) !== JSON.stringify(FEATURE_NAMES)
        || !Array.isArray(model.weights) || model.weights.length !== 3
        || !model.weights.every(Number.isFinite) || !Number.isFinite(model.bias)) {
      throw new TypeError('Unsupported or invalid model.');
    }
    this.#weights = Float64Array.from(model.weights);
    this.#bias = model.bias;
  }

  predict(features) {
    if (!Array.isArray(features) || features.length !== 3
        || !features.every(value => Number.isFinite(value) && value >= 0 && value <= 1)) {
      throw new TypeError('Expected three normalized features.');
    }
    const logit = features.reduce((total, value, index) => total + value * this.#weights[index], this.#bias);
    if (logit >= 0) return 1 / (1 + Math.exp(-logit));
    const exponential = Math.exp(logit);
    return exponential / (1 + exponential);
  }
}
