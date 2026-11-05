'use strict';
const test = require('node:test'), assert = require('node:assert/strict');
const fs = require('node:fs'), vm = require('node:vm');
const source = fs.readFileSync(require.resolve('../app/app.js'), 'utf8');
const policy = require('../app/group-object-selection.js');
function fixture() {
  const first = { figureId: 'first' }, retained = { figureId: 'retained' }, added = { figureId: 'added' };
  let active = [first, retained], renders = 0;
  const objects = [first, retained, added];
  const canvas = { getActiveObjects: () => active, getObjects: () => objects,
    _groupSelector: { x: 0, y: 0, deltaX: 20, deltaY: 20 }, requestRenderAll: () => { renders++; } };
  objects.forEach(object => { object.canvas = canvas; });
  const context = vm.createContext({ globalThis: null, canvas, state: { tool: 'select' },
    pendingObjectShiftMarquee: null, isGroupIsolationActive: () => false,
    FigureStudioGroupObjectSelection: policy, setActiveObjects: objects => { active = Array.from(objects); } });
  context.globalThis = context;
  for (const name of ['captureObjectShiftMarquee', 'prepareObjectShiftMarquee', 'finishObjectShiftMarquee']) {
    const start = source.search(new RegExp('^  function ' + name + '\\(', 'm'));
    const next = /\n  function /.exec(source.slice(start + 5));assert.ok(start > 0 && next);
    vm.runInContext(source.slice(start, start + 5 + next.index), context);
  }
  return { context, canvas, objects, first, retained, added, active: () => active, renders: () => renders,
    start: (extra = {}) => context.captureObjectShiftMarquee({ e: { button: 0, shiftKey: true }, target: null, ...extra }),
    hits: hits => { active = hits; }, finish: () => {
      context.prepareObjectShiftMarquee();
      // The real Fabric handleSelection consumes this before mouse:up.
      canvas._groupSelector = null;
      return context.finishObjectShiftMarquee({ isClick: false });
    } };
}
test('Shift marquee toggles native hit owners against the frozen pre-Fabric selection', () => {
  const f = fixture();f.start();f.hits([f.first, f.added]);assert.equal(f.finish(), true);
  assert.deepEqual(f.active(), [f.retained, f.added]);assert.equal(f.renders(), 1);
  assert.equal(f.canvas._groupSelector, null);
  assert.ok(f.objects.every(object => object.canvas === f.canvas));
});
test('empty Shift marquee retains the original set and hitting all can remove the last members', () => {
  const f = fixture();f.start();f.hits([]);f.finish();assert.deepEqual(f.active(), [f.first, f.retained]);
  f.canvas._groupSelector = { x: 0, y: 0, deltaX: 20, deltaY: 20 };
  f.start();f.hits([f.first, f.retained]);f.finish();assert.deepEqual(f.active(), []);
});
test('ordinary marquee, body targets, text editing and isolated selection keep native ownership', () => {
  for (const kind of ['ordinary', 'body', 'editing', 'isolated', 'direct']) {
    const f = fixture();if (kind === 'editing') f.first.isEditing = true;
    if (kind === 'isolated') f.context.isGroupIsolationActive = () => true;
    if (kind === 'direct') f.context.state.tool = 'directSelect';
    f.start(kind === 'ordinary' ? { e: { button: 0 } } : kind === 'body' ? { target: f.first } : {});
    f.hits([f.added]);assert.equal(f.finish(), false);assert.deepEqual(f.active(), [f.added]);
  }
});
test('ended marquee, changed canvas and removed or unavailable owners cannot resurrect stale selection', () => {
  for (const kind of ['ended', 'canvas', 'removed', 'hidden', 'unselectable']) {
    const f = fixture();f.start();f.hits([f.added]);
    if (kind === 'ended') f.canvas._groupSelector = null;
    if (kind === 'canvas') f.context.canvas = {};
    if (kind === 'removed') f.objects.splice(0, 1);
    if (kind === 'hidden') f.first.visible = false;
    if (kind === 'unselectable') f.first.selectable = false;
    assert.equal(f.finish(), false);assert.equal(f.context.pendingObjectShiftMarquee, null);
  }
});
