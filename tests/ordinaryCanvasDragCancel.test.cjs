'use strict';
const test = require('node:test'), assert = require('node:assert/strict');
const fs = require('node:fs'), vm = require('node:vm');
const fabric = require('../vendor/fabric/index.min.js');
fabric.setEnv({ document: {}, window: {}, dispose() {} });
const source = fs.readFileSync(require.resolve('../app/app.js'), 'utf8');
const start = source.search(/^  function cancelOrdinaryCanvasDrag\(/m);
const next = /\n  function /.exec(source.slice(start + 5));assert.ok(start > 0 && next);
const method = source.slice(start, start + 5 + next.index);
function fixture() {
  const first = new fabric.Path('M 0 0 L 20 0 L 10 20 Z', { left: 30, top: 40, angle: 17 });
  const second = new fabric.Rect({ left: 130, top: 50, width: 40, height: 20, flipX: true });
  const target = new fabric.ActiveSelection([first, second]);
  const before = [first, second].map(o => o.calcTransformMatrix().slice());
  const original = { left: target.left, top: target.top, originX: 'right', originY: 'bottom' };
  const ownOrigins = [target.originX, target.originY];let modifications = 0, renders = 0, queued = true, ended = 0;
  const canvas = { _currentTransform: { target, action: 'drag', original, actionPerformed: true },
    getActiveObject: () => target, requestRenderAll: () => { renders++; },
    fire: name => { if (name === 'object:modified') modifications++; },
    _finalizeCurrentTransform: fabric.Canvas.prototype._finalizeCurrentTransform,
    endCurrentTransform(event) { ended++;fabric.Canvas.prototype.endCurrentTransform.call(this, event); } };
  target.canvas = canvas;target.setCoords = () => {};target.set({ left: target.left + 13, top: target.top + 7 });target.isMoving = true;
  const context = vm.createContext({ canvas, state: { tool: 'select' }, nativePathBodyDrag: null,
    isGroupIsolationActive: () => false, transformTargetObjects: () => [first, second],
    isSmartConnectorObject: () => false, transientTransformHasLiveDependents: () => false,
    pptxLabelTransformState: null, pendingRepeatTransform: {}, pendingSingleObjectShiftClick: {}, pendingObjectShiftMarquee: {}, scaleSnapLock: {},
    cancelObjectInteractionRefresh: () => { queued = false; }, finishTransientCanvasTransform: (_target, options) => { assert.equal(options.cancel, true); },
    hideGuideSnapCue() {}, hideSmartGuideCues() {}, syncSelectionEssentials() {}, scheduleSelectionUiSync() {} });
  vm.runInContext(method, context);
  return { first, second, target, canvas, context, before, ownOrigins,
    cancel: () => context.cancelOrdinaryCanvasDrag({ key: 'Escape' }),
    counts: () => ({ modifications, renders, queued, ended }) };
}
test('Escape restores real native ActiveSelection child poses before ending without object:modified', () => {
  const f = fixture();assert.equal(f.cancel(), true);
  for (const [index, object] of [f.first, f.second].entries()) {
    object.calcTransformMatrix().forEach((value, at) => assert.ok(Math.abs(value - f.before[index][at]) < 1e-10));
    assert.equal(object.group, f.target);
  }
  assert.deepEqual([f.target.originX, f.target.originY], f.ownOrigins);
  assert.deepEqual(f.counts(), { modifications: 0, renders: 1, queued: false, ended: 1 });
  assert.equal(f.canvas._currentTransform, null);assert.equal(f.target.isMoving, false);
  for (const key of ['pendingRepeatTransform','pendingSingleObjectShiftClick','pendingObjectShiftMarquee','scaleSnapLock']) assert.equal(f.context[key], null);
});
test('ordinary cancellation retires its transform once and preserves the selected native owner', () => {
  const f = fixture();f.cancel();assert.equal(f.canvas.getActiveObject(), f.target);
  assert.equal(f.cancel(), false);assert.equal(f.counts().ended, 1);
});
for (const kind of ['scale', 'direct', 'isolated', 'native-point', 'foreign-canvas', 'foreign-owner', 'dependent', 'connector', 'pptx-label', 'invalid-position']) {
  test(kind + ' keeps its existing editing or cancellation owner', () => {
    const f = fixture();
    if (kind === 'scale') f.canvas._currentTransform.action = 'scale';
    if (kind === 'direct') f.context.state.tool = 'directSelect';
    if (kind === 'isolated') f.context.isGroupIsolationActive = () => true;
    if (kind === 'native-point') f.context.nativePathBodyDrag = {};
    if (kind === 'foreign-canvas') f.target.canvas = {};
    if (kind === 'foreign-owner') f.canvas.getActiveObject = () => f.first;
    if (kind === 'dependent') f.context.transientTransformHasLiveDependents = () => true;
    if (kind === 'connector') f.context.isSmartConnectorObject = () => true;
    if (kind === 'pptx-label') f.context.pptxLabelTransformState = { labels: [{}] };
    if (kind === 'invalid-position') f.canvas._currentTransform.original.left = NaN;
    assert.equal(f.cancel(), false);assert.equal(f.counts().ended, 0);assert.equal(f.counts().queued, true);
  });
}
