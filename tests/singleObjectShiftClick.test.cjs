'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require.resolve('../app/app.js'), 'utf8');

function fixture() {
  const target = { type: 'group', path: [['M', 0, 0], ['L', 5, 0]] };
  let active = target, discarded = 0, renders = 0;
  const canvas = { getActiveObject: () => active,
    discardActiveObject: () => { active = null; discarded++; }, requestRenderAll: () => { renders++; } };
  const context = vm.createContext({ canvas, state: { tool: 'select' }, pendingSingleObjectShiftClick: null,
    isGroupIsolationActive: () => false, isActiveSelectionObject: object => object.type === 'activeselection' });
  for (const name of ['captureSingleObjectShiftClick', 'finishSingleObjectShiftClick']) {
    const start = source.search(new RegExp('^  function ' + name + '\\(', 'm'));
    const end = /\n  function /.exec(source.slice(start + 5));
    assert.ok(start > 0 && end);
    vm.runInContext(source.slice(start, start + 5 + end.index), context);
  }
  const down = { e: { button: 0, shiftKey: true }, target, alreadySelected: true };
  return { target, canvas, context, down,
    setActive: object => { active = object; },
    counts: () => ({ discarded, renders }),
    release: (extra = {}) => context.finishSingleObjectShiftClick({ e: {}, target, isClick: true, ...extra }) };
}

test('stationary Shift click removes the last already-selected ordinary owner without changing artwork', () => {
  const f = fixture(), before = structuredClone(f.target);
  f.context.captureSingleObjectShiftClick(f.down);
  assert.equal(f.release(), true);
  assert.deepEqual(f.counts(), { discarded: 1, renders: 1 });
  assert.deepEqual(f.target, before);
  assert.equal(f.context.pendingSingleObjectShiftClick, null);
});

test('first Shift click and removal from a multi-selection preserve Fabric membership changes', () => {
  const f = fixture();
  f.context.captureSingleObjectShiftClick({ ...f.down, alreadySelected: false });
  assert.equal(f.release(), false);
  f.setActive({ type: 'group' });
  f.context.captureSingleObjectShiftClick(f.down);
  assert.equal(f.release(), false);
  assert.equal(f.counts().discarded, 0);
});

test('Shift-constrained dragging retains the selected owner and retires the pending click', () => {
  const f = fixture();
  f.context.captureSingleObjectShiftClick(f.down);
  assert.equal(f.release({ isClick: false }), false);
  assert.equal(f.release(), false);
  assert.equal(f.counts().discarded, 0);
});

for (const [name, patch] of [
  ['ordinary click', { e: { button: 0, shiftKey: false } }],
  ['right button', { e: { button: 2, shiftKey: true } }],
  ['pan modifier', { e: { button: 0, shiftKey: true, altKey: true } }],
  ['Ctrl modifier', { e: { button: 0, shiftKey: true, ctrlKey: true } }],
  ['Meta modifier', { e: { button: 0, shiftKey: true, metaKey: true } }],
  ['transform handle', { transform: { corner: 'se' } }],
]) test(name + ' cannot remove the last owner through Shift click', () => {
  const f = fixture();f.context.captureSingleObjectShiftClick({ ...f.down, ...patch });
  assert.equal(f.release(), false);assert.equal(f.counts().discarded, 0);
});

test('Direct Selection, isolation, text editing and a temporary multi-selection keep their own policies', () => {
  for (const kind of ['direct', 'isolation', 'text', 'multiple']) {
    const f = fixture();
    if (kind === 'direct') f.context.state.tool = 'directSelect';
    if (kind === 'isolation') f.context.isGroupIsolationActive = () => true;
    if (kind === 'text') f.target.isEditing = true;
    if (kind === 'multiple') f.target.type = 'activeselection';
    f.context.captureSingleObjectShiftClick(f.down);assert.equal(f.release(), false);
    assert.equal(f.counts().discarded, 0);
  }
});

test('a release on another target, canvas or editing mode cannot clear a stale selection', () => {
  for (const kind of ['target', 'canvas', 'tool', 'editing']) {
    const f = fixture();f.context.captureSingleObjectShiftClick(f.down);
    if (kind === 'canvas') f.context.canvas = { getActiveObject: () => f.target };
    if (kind === 'tool') f.context.state.tool = 'pan';
    if (kind === 'editing') f.target.isEditing = true;
    assert.equal(f.release(kind === 'target' ? { target: {} } : {}), false);
    assert.equal(f.context.pendingSingleObjectShiftClick, null);
  }
});
