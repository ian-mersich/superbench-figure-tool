'use strict';
const test = require('node:test'), assert = require('node:assert/strict');
const fs = require('node:fs'), vm = require('node:vm');
const fabric = require('../vendor/fabric/index.min.js');
fabric.setEnv({ document: {}, window: {}, dispose() {} });
const source = fs.readFileSync(require.resolve('../app/app.js'), 'utf8');
function fixture(multiple) {
  const part = new fabric.Path('M 0 0 L 20 0 L 10 20 Z', { left: 10, top: 10 });part.figureId = 'part';
  const first = new fabric.Group([part], { left: 80, top: 90, angle: 17 });
  first.figureId = 'asset';first.scientificAssetMeta = { assetId: 'real-native-asset', immutableSource: 'kept' };
  const second = new fabric.Rect({ left: 210, top: 110, width: 35, height: 25, flipX: true });second.figureId = 'shape';
  const roots = [first, second];
  const active = multiple ? new fabric.ActiveSelection(roots) : first;
  const canvas = Object.assign(Object.create(fabric.Canvas.prototype), { _objects: roots, _activeObject: active,
    includeDefaultValues: true, backgroundColor: '#ffffff' });
  const props = ['figureId', 'scientificAssetMeta'];
  const base = { fabric: canvas.toObject(props), document: { kind: 'figure' }, title: 'Mixed artwork' };
  active.set({ left: active.left + 31, top: active.top + 17 });
  const expected = canvas.toObject(props), matrices = roots.map(o => o.calcTransformMatrix().slice());
  let fullCaptures = 0;
  const context = vm.createContext({ canvas, fabricRef: fabric, CUSTOM_PROPS: props,
    undoStack: ['previous'], latestHistoryStateCache: { documentId: 'doc', snapshot: 'previous', stateObject: base },
    currentTransformDocumentId: () => 'doc', state: { document: { title: 'Mixed artwork' } },
    arrayFrom: value => Array.from(value || []), isActiveSelectionObject: o => o instanceof fabric.ActiveSelection,
    syncScientificTypographyRangesFromLiveStyles() {}, serializedDocumentDescriptor: () => ({ kind: 'figure' }),
    refreshCanvasArtifactRefs() {}, pdfHistoryNodeStore: null,
    compactReusableArtworkReferences: x => x, stripMasterInheritanceFromSnapshot: x => x,
    canonicalizeLiveBooleanFabricSnapshot: x => x,
    editorStateObject: () => { fullCaptures++;return { fabric: canvas.toObject(props), document: { kind: 'figure' }, title: 'Mixed artwork' }; },
    stringifyEditorStateForHistory: value => JSON.stringify(value),
    historySerializationResult: (_encoded, snapshot, _stats, cacheableState) => ({ snapshot, cacheableState }) });
  for (const name of ['incrementalHistoryRoots','incrementalHistoryObjectRecord','incrementalHistoryStateObject','serializeEditorStateForHistory']) {
    const start = source.search(new RegExp('^  function ' + name + '\\(', 'm'));
    const next = /\n  (?:async )?function /.exec(source.slice(start + 5));assert.ok(start > 0 && next);
    vm.runInContext(source.slice(start, start + 5 + next.index), context);
  }
  const result = context.serializeEditorStateForHistory({ incrementalObjects: [active] });
  return { roots, active, first, part, result: JSON.parse(result.snapshot), expected, matrices, fullCaptures };
}
test('mixed ActiveSelection history uses canonical native canvas world poses for Redo', () => {
  const f = fixture(true);assert.equal(f.fullCaptures, 1);
  assert.deepEqual(f.result.fabric, f.expected);
  assert.deepEqual(f.result.fabric.objects.map(o => o.figureId), ['asset', 'shape']);
  assert.deepEqual(f.result.fabric.objects[0].scientificAssetMeta, { assetId: 'real-native-asset', immutableSource: 'kept' });
  assert.equal(f.result.fabric.objects[0].objects[0].figureId, 'part');
});
test('canonical history capture leaves real native group membership and live scene matrices unchanged', () => {
  const f = fixture(true);
  f.roots.forEach((o, index) => { assert.equal(o.group, f.active);assert.deepEqual(o.calcTransformMatrix(), f.matrices[index]); });
  assert.equal(f.part.group, f.first);
});
test('an ordinary single root retains incremental history and its exact native payload', () => {
  const f = fixture(false);assert.equal(f.fullCaptures, 0);assert.deepEqual(f.result.fabric, f.expected);
});
