/** A deterministic safety policy around the learned model's score. */
import { RingBuffer, extractFeatures, validateObservation } from './model.mjs';

export const MODES = Object.freeze(['balanced', 'guided', 'focused']);

export class AdaptiveController {
  constructor(model) { this.model = model; this.history = new RingBuffer(5); this.reset(); }

  reset() {
    this.history.clear();
    this.enabled = false;
    this.mode = 'balanced';
    this.score = null;
    this.features = null;
    this.candidate = null;
    this.streak = 0;
    this.pending = null;
    this.cooldown = 0;
  }

  setEnabled(enabled) {
    if (typeof enabled !== 'boolean') throw new TypeError('Expected boolean.');
    this.enabled = enabled;
    this.pending = null;
    this.candidate = null;
    this.streak = 0;
  }

  setManual(mode) {
    if (!MODES.includes(mode)) throw new RangeError('Unknown view.');
    this.setEnabled(false);
    this.mode = mode;
  }

  observe(row) {
    validateObservation(row);
    // Off means no new behavior collection, not just no layout changes.
    if (!this.enabled) return;
    this.history.push(row);
    this.features = extractFeatures(this.history.values());
    this.score = this.model.predict(this.features);
    if (this.history.size < 3) return;
    if (this.cooldown > 0) { this.cooldown -= 1; return; }
    const next = this.score >= 0.7 ? 'guided' : this.score <= 0.3 ? 'focused' : null;
    if (!next || next === this.mode) { this.candidate = null; this.streak = 0; this.pending = null; return; }
    if (next !== this.candidate) this.pending = null;
    this.streak = next === this.candidate ? this.streak + 1 : 1;
    this.candidate = next;
    // Two consistent decisions, following the three-observation warmup.
    if (this.streak >= 2) this.pending = next;
  }

  applyAtBoundary() {
    if (!this.enabled || !this.pending) return false;
    this.mode = this.pending;
    this.pending = null;
    this.candidate = null;
    this.streak = 0;
    this.cooldown = 2;
    return true;
  }
}
