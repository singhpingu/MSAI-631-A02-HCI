import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { RingBuffer, LogisticModel, extractFeatures } from '../web/model.mjs';
import { AdaptiveController } from '../web/adaptation.mjs';

const modelData = JSON.parse(readFileSync(new URL('../data/model.json', import.meta.url), 'utf8'));
const high = Object.freeze({ correct: false, hintRequested: true, activeMs: 70000, expectedMs: 40000 });
const low = Object.freeze({ correct: true, hintRequested: false, activeMs: 8000, expectedMs: 40000 });
function controller() { const control = new AdaptiveController(new LogisticModel(modelData)); control.setEnabled(true); return control; }

test('ring buffer bounds memory, preserves order and copies records', () => {
  const buffer = new RingBuffer(2), original = { value: 1 };
  buffer.push(original); original.value = 99; buffer.push({ value: 2 });
  assert.equal(buffer.values()[0].value, 1);
  buffer.push({ value: 3 });
  assert.equal(buffer.size, 2); assert.deepEqual(buffer.values().map(row => row.value), [2, 3]);
  buffer.clear(); assert.equal(buffer.size, 0);
});
test('feature aggregation respects requested hints and timing threshold', () => {
  assert.deepEqual(extractFeatures([high, low]), [0.5, 0.5, 0.5]);
  assert.deepEqual(extractFeatures([{ ...low, activeMs: 40000 }]), [0, 0, 0]);
  assert.throws(() => extractFeatures([]));
  assert.throws(() => extractFeatures([{ ...low, expectedMs: 0 }]));
});
test('learned inference supports clear profiles and rejects malformed input', () => {
  const model = new LogisticModel(modelData);
  assert.ok(model.predict([1, 1, 1]) > 0.7); assert.ok(model.predict([0, 0, 0]) < 0.3);
  assert.throws(() => model.predict([0, NaN, 0]));
  assert.throws(() => new LogisticModel({ ...modelData, feature_names: ['wrong'] }));
});
test('adaptation starts off and does not collect observations while off', () => {
  const control = new AdaptiveController(new LogisticModel(modelData));
  control.observe(high); assert.equal(control.history.size, 0); assert.equal(control.mode, 'balanced');
});
test('warmup and two consistent decisions precede a boundary change', () => {
  const control = controller();
  for (let index = 0; index < 3; index += 1) control.observe(high);
  assert.equal(control.pending, null); control.observe(high);
  assert.equal(control.pending, 'guided'); assert.equal(control.mode, 'balanced');
  assert.equal(control.applyAtBoundary(), true); assert.equal(control.mode, 'guided');
});
test('focused view is learned from low-support observations', () => {
  const control = controller(); for (let index = 0; index < 4; index += 1) control.observe(low);
  control.applyAtBoundary(); assert.equal(control.mode, 'focused');
});
test('manual selection cancels a queued recommendation and stops collection', () => {
  const control = controller(); for (let index = 0; index < 4; index += 1) control.observe(high);
  control.setManual('focused'); control.observe(high);
  assert.equal(control.enabled, false); assert.equal(control.pending, null);
  assert.equal(control.history.size, 4); assert.equal(control.applyAtBoundary(), false);
  assert.equal(control.mode, 'focused'); assert.throws(() => control.setManual('unknown'));
});
test('cooldown prevents immediate switching and later observations can recover', () => {
  const control = controller(); for (let index = 0; index < 4; index += 1) control.observe(high);
  control.applyAtBoundary(); control.observe(low); control.observe(low);
  assert.equal(control.cooldown, 0); assert.equal(control.pending, null);
  for (let index = 0; index < 4; index += 1) control.observe(low);
  assert.equal(control.history.size, 5); control.applyAtBoundary(); assert.equal(control.mode, 'focused');
});
test('a contradictory decision cancels a pending recommendation', () => {
  const control = new AdaptiveController({ predict: features => features[0] > 0.8 ? 0.9 : 0.5 });
  control.setEnabled(true); for (let index = 0; index < 4; index += 1) control.observe(high);
  assert.equal(control.pending, 'guided'); control.observe(low); assert.equal(control.pending, null);
});
test('reset erases observations, scores, recommendations and consent', () => {
  const control = controller(); for (let index = 0; index < 4; index += 1) control.observe(high);
  control.applyAtBoundary(); control.reset();
  assert.equal(control.history.size, 0); assert.equal(control.score, null); assert.equal(control.features, null);
  assert.equal(control.mode, 'balanced'); assert.equal(control.enabled, false); assert.equal(control.cooldown, 0);
});
