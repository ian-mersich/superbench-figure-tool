'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync(require.resolve('../app/app.js'), 'utf8');
const selection = require('../app/group-object-selection.js');

function actual(name, context) {
  const start = source.search(new RegExp('^  (?:async )?function ' + name + '\\(', 'm'));
  const next = /\n  (?:async )?function /.exec(source.slice(start + 5));
  assert.ok(start > 0 && next, `source function ${name}`);
  vm.runInContext(source.slice(start, start + 5 + next.index), context);
  return context[name];
}

function group(children, properties = {}) {
  return { type: 'group', _objects: children, getObjects() { return this._objects; },
    calcTransformMatrix: () => [1, 0, 0, 1, 0, 0], ...properties };
}

function text(name, bounds, properties = {}) {
  return {
    type: 'textbox', figureType: 'text', figureId: name, text: name,
    left: bounds.left, top: bounds.top, width: bounds.width, height: bounds.height,
    fontFamily: 'Arial', fontSize: 12, pdfTextSource: { schema: 'retained-source', text: name },
    getBoundingRect() { return { ...bounds }; }, set(values) { Object.assign(this, values); },
    calcTransformMatrix: () => [1, 0, 0, 1, 0, 0],
    setCoords() { this.coordsUpdated = (this.coordsUpdated || 0) + 1; },
    ...properties,
  };
}

function marqueeContext(objects) {
  const context = vm.createContext({
    globalThis: null,
    canvas: { getObjects: () => objects },
    fabricRef: { util: { multiplyTransformMatrices: (a, b) => multiply(a, b) } },
    FigureStudioGroupObjectSelection: selection,
    groupIsolation: { path: [] },
    activeIsolationGroup: () => null,
    isGroupIsolationActive: () => false,
    groupChildren: object => Array.isArray(object?._objects) ? object._objects : [],
    isReferenceObject: object => Boolean(object?.reference),
    pdfGroupedDirectSelectionScope: ({ target }) => target?.admittedPdfScope ? target : null,
    importedVectorFigureType: object => object?.figureType || null,
  });
  context.globalThis = context;
  actual('isCanvasTextObject', context);
  actual('directSelectionMarqueeObjects', context);
  actual('directSelectionMarqueeTexts', context);
  return context;
}

function multiply(a, b) {
  return [a[0] * b[0] + a[2] * b[1], a[1] * b[0] + a[3] * b[1],
    a[0] * b[2] + a[2] * b[3], a[1] * b[2] + a[3] * b[3],
    a[0] * b[4] + a[2] * b[5] + a[4], a[1] * b[4] + a[3] * b[5] + a[5]];
}

test('marquee discovers nested admitted PDF text leaves but preserves their text and group boundaries', () => {
  const labelA = text('native-a', { left: 10, top: 10, width: 20, height: 10 });
  const labelB = text('native-b', { left: 40, top: 10, width: 20, height: 10 });
  const nested = group([labelB]);
  const outer = group([labelA, nested], { admittedPdfScope: true, importMeta: { mimeType: 'application/pdf' } });
  labelA.group = outer; labelB.group = nested; nested.group = outer;
  const ordinaryLabel = text('ordinary-child', { left: 10, top: 40, width: 20, height: 10 });
  const ordinary = group([ordinaryLabel]);
  ordinaryLabel.group = ordinary;
  const context = marqueeContext([outer, ordinary]);

  assert.deepEqual(Array.from(context.directSelectionMarqueeObjects()), [labelA, labelB, ordinary]);
  assert.deepEqual(Array.from(context.directSelectionMarqueeTexts({ left: 0, top: 0, right: 70, bottom: 30 })), [labelA, labelB]);
  assert.equal(labelA.text, 'native-a');
  assert.equal(labelB.text, 'native-b');
  assert.equal(labelA.group, outer);
  assert.equal(labelB.group, nested);
  assert.equal(ordinaryLabel.group, ordinary);
});

test('hidden, locked, transparent, reference, and PDF page-frame branches are excluded', () => {
  const visible = text('visible', { left: 0, top: 0, width: 10, height: 10 });
  const hidden = text('hidden', { left: 0, top: 0, width: 10, height: 10 }, { visible: false });
  const locked = text('locked', { left: 0, top: 0, width: 10, height: 10 }, { locked: true });
  const transparent = text('transparent', { left: 0, top: 0, width: 10, height: 10 }, { opacity: 0 });
  const reference = text('reference', { left: 0, top: 0, width: 10, height: 10 }, { reference: true });
  const frameChild = text('frame-child', { left: 0, top: 0, width: 10, height: 10 });
  const pageFrame = group([frameChild], { pdfPageFrame: true });
  visible.group = hidden.group = locked.group = transparent.group = reference.group = pageFrame.group = null;
  for (const child of [visible, hidden, locked, transparent, reference, pageFrame]) child.group = null;
  frameChild.group = pageFrame;
  const root = group([visible, hidden, locked, transparent, reference, pageFrame], { admittedPdfScope: true });
  for (const child of [visible, hidden, locked, transparent, reference, pageFrame]) child.group = root;
  const context = marqueeContext([root]);

  assert.deepEqual(Array.from(context.directSelectionMarqueeObjects()), [visible]);
  assert.deepEqual(Array.from(context.directSelectionMarqueeTexts({ left: -1, top: -1, right: 20, bottom: 20 })), [visible]);
});

test('text marquee uses the delivered rectangle exactly and honors supported clip intersections', () => {
  const clip = { type: 'rect', width: 20, height: 20, rx: 0, ry: 0,
    calcOwnMatrix: () => [1, 0, 0, 1, 0, 0] };
  const clipped = text('clipped', { left: -5, top: -3, width: 20, height: 10 });
  const justOutside = text('outside', { left: 10.01, top: 0, width: 5, height: 5 });
  const exactEdge = text('edge', { left: 10, top: 0, width: 5, height: 5 });
  const root = group([clipped, justOutside, exactEdge], { admittedPdfScope: true, clipPath: clip });
  // Preserve parent links as Fabric would provide them.
  clipped.group = root; justOutside.group = root; exactEdge.group = root;
  const context = marqueeContext([root]);

  const bounds = selection.bounds(clipped, context.fabricRef);
  assert.deepEqual(bounds, { left: -5, top: -3, width: 15, height: 10 });
  const selected = context.directSelectionMarqueeTexts({ left: 0, top: 0, right: 10, bottom: 5 });
  assert.deepEqual(Array.from(selected), [clipped, exactEdge]);
  assert.equal(selected.includes(justOutside), false);
});

test('direct-selection point hits use the exact delivered rectangle with inclusive edge membership', () => {
  const onRightBottomEdge = { figureId: 'edge-point' }, justOutside = { figureId: 'outside-point' };
  const objects = [onRightBottomEdge, justOutside];
  const context = vm.createContext({
    uniqueObjects: rows => [...new Set(rows)],
    directSelectionMarqueeObjects: () => objects,
    pathNodeEditObjects: () => [],
    isDirectSelectionEditableObject: () => true,
    isPrimitiveShapeDirectSelectable: () => false,
    pathHandleDescriptors: object => [{ commandIndex: 0, handleType: 'endpoint', object }],
    pathHandleCanvasPoint: object => object === onRightBottomEdge ? { x: 10, y: 10 } : { x: 10.0001, y: 10 },
    pdfDirectLeafSourceIdentity: () => null,
  });
  actual('directSelectionMarqueeHits', context);
  const hits = context.directSelectionMarqueeHits({ left: 0, top: 0, right: 10, bottom: 10 });
  assert.deepEqual(Array.from(hits, hit => hit.object), [onRightBottomEdge]);
  assert.deepEqual(Array.from(hits[0].handles, handle => [handle.commandIndex, handle.handleType]), [[0, 'endpoint']]);
});

function finishMixedSubset(objects, hits, labels) {
  const handles = objects.filter(o => o.type === 'path').map(object => ({ objectId: object.figureId, commandIndex: 0, handleType: 'endpoint' }));
  let isolation = false;
  const context = vm.createContext({
    globalThis: null, FigureStudioGroupObjectSelection: selection,
    pathNodeEdit: { object: objects[0], objects, selectedHandles: handles,
      marquee: { additive: true, pointerId: 1, start: { x: 0, y: 0 }, current: { x: 20, y: 20 } } },
    uniqueObjects: rows => [...new Set(rows)],
    directSelectionObjects: () => objects, selectedPathHandleRefs: () => handles,
    directSelectionMarqueeObjects: () => objects,
    directSelectionMarqueeHits: () => hits.map(object => ({ object, handles: [{ commandIndex: 0, handleType: 'endpoint' }] })),
    directSelectionMarqueeTexts: () => labels,
    isGroupIsolationActive: () => isolation,
    isActiveSelectionObject: object => object?.type === 'activeselection',
    pdfGroupedDirectSelectionScope: ({ target }) => target?.admittedPdfScope ? target : null,
    enterPdfDirectSelectionScope: root => { context.enteredRoot = root; isolation = true; return true; },
    activeIsolationGroup: () => context.enteredRoot,
    objectIsWithinGroup: (object, root) => { while (object && object !== root) object = object.group; return object === root; },
    isPrimitiveShapeDirectSelectable: () => false,
    ensureDirectSelectionPathObject: object => object,
    pathHandleDescriptors: () => [{ commandIndex: 0, handleType: 'endpoint' }],
    qualifyPathHandle: (object, handle) => ({ ...handle, objectId: object.figureId }),
    canUsePathPointEditing: object => object.type === 'path',
    isCanvasTextObject: object => object.type === 'textbox',
    startPathNodeEdit: object => { context.pathNodeEdit.object = object; },
    pathNodeEditObjects: () => context.pathNodeEdit.objects.filter(object => object.type === 'path'),
    samePathHandle: (a, b) => a.objectId === b.objectId && a.commandIndex === b.commandIndex && a.handleType === b.handleType,
    ensureDirectSelectionCanvasCollection: () => { context.collectionUpdated = true; },
    canvas: { upperCanvasEl: { releasePointerCapture() {} } },
    showToast: message => { context.message = message; },
    resetPaintedVectorDirectSelectionCycle() {}, renderPathNodeOverlay() {}, updatePathNodeStatus() {},
    cancelSelectionUiSync() {}, cancelSelectionEssentialsSync() {}, syncInspector() {},
  });
  context.globalThis = context;
  actual('normalizedPointRect', context); actual('finishPathHandleMarquee', context);
  context.finishPathHandleMarquee({ pointerId: 1 });
  return context;
}

test('Shift marquee toggles a mixed subset inside temporary multi-selection without treating it as a document group', () => {
  const temporary = group([], { type: 'activeselection' });
  const first = { type: 'path', figureId: 'first', group: temporary, set() {} };
  const retained = { type: 'path', figureId: 'retained', group: temporary, set() {} };
  const removedLabel = text('remove-label', { left: 1, top: 1, width: 8, height: 5 }, { group: temporary });
  const retainedLabel = text('retain-label', { left: 30, top: 1, width: 8, height: 5 }, { group: temporary });
  const context = finishMixedSubset([first, retained, removedLabel, retainedLabel], [first], [removedLabel]);
  assert.equal(context.collectionUpdated, true);
  assert.deepEqual(Array.from(context.pathNodeEdit.selectedHandles, h => h.objectId), ['retained']);
  assert.deepEqual(Array.from(context.pathNodeEdit.objects).filter(o => o.type === 'textbox'), [retainedLabel]);
  assert.equal(context.message, '1 point and 1 label selected');
  assert.equal(first.group, temporary); assert.equal(retainedLabel.group, temporary);
});

test('Shift marquee still refuses ordinary group descendants and children from different PDF pages', () => {
  for (const roots of [[group([]), group([])], [group([], { admittedPdfScope: true }), group([], { admittedPdfScope: true })]]) {
    const first = { type: 'path', figureId: 'first', group: roots[0], set() {} };
    const label = text('label', { left: 1, top: 1, width: 8, height: 5 }, { group: roots[1] });
    const context = finishMixedSubset([first, label], [first], [label]);
    assert.equal(context.collectionUpdated, undefined);
    assert.equal(context.message, 'Select within one PDF page to edit its points and labels');
    assert.equal(first.group, roots[0]); assert.equal(label.group, roots[1]);
  }
});

test('Shift marquee enters one genuine PDF page through a temporary selection without reparenting its children', () => {
  const temporary = group([], { type: 'activeselection' });
  const page = group([], { admittedPdfScope: true, group: temporary });
  const first = { type: 'path', figureId: 'first', group: page, set() {} };
  const label = text('label', { left: 1, top: 1, width: 8, height: 5 }, { group: page });
  const context = finishMixedSubset([first, label], [first], [label]);
  assert.equal(context.enteredRoot, page);
  assert.equal(context.collectionUpdated, true);
  assert.equal(first.group, page); assert.equal(label.group, page); assert.equal(page.group, temporary);
});

function inverse(matrix) {
  const [a, b, c, d, e, f] = matrix, det = a * d - b * c;
  return [d / det, -b / det, -c / det, a / det, (c * f - d * e) / det, (b * e - a * f) / det];
}

function transformPoint(matrix, point) {
  return { x: matrix[0] * point.x + matrix[2] * point.y + matrix[4], y: matrix[1] * point.x + matrix[3] * point.y + matrix[5] };
}

test('captured selected text moves in parent space under a rotated and scaled parent and raw return restores exact coordinates', () => {
  const grandparent = group([], { dirty: false });
  const parentMatrix = [0, 2, -2, 0, 100, 200];
  const parent = group([], { group: grandparent, dirty: false, calcTransformMatrix: () => parentMatrix });
  const source = { schema: 'retained-source', text: 'Beta', font: { name: 'Arial' } };
  const object = text('editable-label', { left: 7.25, top: -2.5, width: 15, height: 8 }, {
    group: parent, pdfTextSource: source, text: 'Beta', path: [['M', 1, 2]], pathOffset: { x: 3, y: 4 }, dirty: false,
  });
  parent._objects.push(object);
  const untouched = { text: object.text, source: structuredClone(object.pdfTextSource), fontFamily: object.fontFamily,
    fontSize: object.fontSize, path: structuredClone(object.path), pathOffset: structuredClone(object.pathOffset), parent: object.group };
  const original = { left: object.left, top: object.top };
  let overlayRefreshes = 0;
  const context = vm.createContext({
    globalThis: null, pathNodeEdit: { objects: [object] },
    fabricRef: { util: { invertTransform: inverse } },
    uniqueObjects: rows => [...new Set(rows)], isReferenceObject: item => Boolean(item?.reference),
    importedVectorFigureType: item => item?.figureType || null,
    renderIsolationSelectionOverlay: () => { overlayRefreshes++; },
  });
  context.globalThis = context;
  actual('isCanvasTextObject', context);
  actual('pathEditObjectId', context);
  actual('directSelectionTextObjects', context);
  actual('captureDirectSelectionTextPositions', context);
  actual('translatePathGestureOperands', context);

  const snapshot = context.captureDirectSelectionTextPositions();
  assert.equal(snapshot.length, 1);
  assert.equal(snapshot[0].object, object);
  assert.equal(snapshot[0].parent, parent);
  assert.deepEqual(Array.from(snapshot[0].inverseParentMatrix), inverse(parentMatrix));
  const startWorld = transformPoint(parentMatrix, { x: original.left, y: original.top });

  context.translatePathGestureOperands(snapshot.map(entry => ({ ...entry, textObject: entry.object })), 10, -6);
  assert.equal(object.left, original.left - 3);
  assert.equal(object.top, original.top - 5);
  const movedWorld = transformPoint(parentMatrix, { x: object.left, y: object.top });
  assert.deepEqual(movedWorld, { x: startWorld.x + 10, y: startWorld.y - 6 });
  assert.equal(object.group, parent);
  assert.equal(parent.dirty, true);
  assert.equal(grandparent.dirty, true);
  assert.ok(object.coordsUpdated > 0);
  assert.deepEqual({ text: object.text, source: object.pdfTextSource, fontFamily: object.fontFamily,
    fontSize: object.fontSize, path: object.path, pathOffset: object.pathOffset, parent: object.group }, untouched);

  context.translatePathGestureOperands(snapshot.map(entry => ({ ...entry, textObject: entry.object })), 0, 0);
  assert.ok(Object.is(object.left, original.left));
  assert.ok(Object.is(object.top, original.top));
  assert.equal(overlayRefreshes, 2, 'moving and restoring text both refresh its selection feedback');
  assert.equal(parent.dirty, true);
  assert.equal(grandparent.dirty, true);
  assert.deepEqual({ text: object.text, source: object.pdfTextSource, fontFamily: object.fontFamily,
    fontSize: object.fontSize, path: object.path, pathOffset: object.pathOffset, parent: object.group }, untouched);
});

test('arrow nudge applies one scene delta to the selected path handle and retained text labels', () => {
  const path = { figureId: 'path-a', dirty: false };
  const labelA = text('label-a', { left: 5, top: 8, width: 18, height: 8 });
  const labelB = text('label-b', { left: 35, top: 8, width: 18, height: 8 });
  const descriptor = { objectId: 'path-a', commandIndex: 2, handleType: 'endpoint' };
  const item = { object: path, descriptor, point: { x: 40, y: 50 } };
  const textSnapshots = [labelA, labelB].map(object => ({ object, objectId: object.figureId,
    left: object.left, top: object.top, parent: null, inverseParentMatrix: [1, 0, 0, 1, 0, 0] }));
  const calls = { pathPoint: null, translated: null, finalized: null };
  const context = vm.createContext({
    pathNodeEdit: { object: path },
    selectedPathHandleLayoutItems: () => [item],
    captureVectorEnginePathSnapshots: items => items.map(entry => entry.object),
    captureDirectSelectionTextPositions: () => textSnapshots,
    translatePathGestureOperands: (entries, dx, dy) => { calls.translated = { entries, dx, dy }; },
    setPathHandleCanvasPoint: (object, handle, point) => { calls.pathPoint = { object, handle, point }; },
    finalizeSelectedPathHandleEdit: (items, options) => { calls.finalized = { items, options }; return true; },
  });
  actual('nudgeSelectedPathHandle', context);

  assert.equal(context.nudgeSelectedPathHandle(1, -1), true);
  assert.equal(calls.pathPoint.object, path);
  assert.equal(calls.pathPoint.handle, descriptor);
  assert.equal(calls.pathPoint.point.x, 41);
  assert.equal(calls.pathPoint.point.y, 49);
  assert.deepEqual(calls.translated.entries.map(entry => entry.textObject), [labelA, labelB]);
  assert.equal(calls.translated.dx, 1);
  assert.equal(calls.translated.dy, -1);
  assert.equal(calls.finalized.options.action, 'nudge_path_handle');
  assert.deepEqual(calls.finalized.options.textObjects, [labelA, labelB]);
});

function pathEditCleanupStubs() {
  return {
    closePdfPointScreenPreview() {}, nativePathBodyDrag: null,
    pathNodeEditObjects: () => [], isLineVectorObject: () => false,
    clearPathNodeOverlay() {}, syncPathActionButtons() {},
    els: { editPathNodesBtn: null },
  };
}

test('leaving Direct Selection through activateTool retires hidden and locked tracked labels when the primary path is null', () => {
  const hidden = text('hidden-tracked', { left: 0, top: 0, width: 8, height: 5 }, { visible: false });
  const locked = text('locked-tracked', { left: 12, top: 0, width: 8, height: 5 }, { locked: true });
  const state = { tool: 'directSelect' };
  const context = vm.createContext({
    ...pathEditCleanupStubs(), state,
    pathNodeEdit: { object: null, objects: [hidden, locked] },
    linePickerPresetId: '', liveBooleanEdit: { active: false },
    appearanceGradientEdit: { active: false }, pdfGradientEdit: { active: false },
    appearancePatternEdit: { active: false }, strokeWidthEdit: { active: false },
    penToolState: { anchors: [] }, shapeBuilderState: {},
    isGroupIsolationActive: () => false, isPresentationDocument: () => false,
    cancelZoomToolInteraction() {}, cancelKnifeToolInteraction() {},
    resetPaintedVectorDirectSelectionCycle() {}, syncLineVectorSelectionChrome() {},
    syncToolMode() {}, renderSmartConnectorOverlay() {}, syncPrecisionToolStatus() {},
    cancelSelectionEssentialsSync() {}, syncInspector() {},
    getPrecisionToolStateForQa: () => ({ tool: state.tool }),
  });
  actual('stopPathNodeEdit', context);
  actual('activateTool', context);

  context.activateTool('select', { toast: false });

  assert.equal(context.state.tool, 'select');
  assert.equal(context.pathNodeEdit.object, null);
  assert.deepEqual(Array.from(context.pathNodeEdit.objects), [], 'all raw tracked text references are retired');
});

test('exiting group isolation retires raw hidden and locked labels under the root without a primary path', () => {
  const root = group([]), nested = group([], { group: root });
  const hidden = text('hidden-in-root', { left: 0, top: 0, width: 8, height: 5 }, { visible: false, group: nested });
  const locked = text('locked-in-root', { left: 12, top: 0, width: 8, height: 5 }, { locked: true, group: root });
  nested._objects.push(hidden); root._objects.push(nested, locked);
  const context = vm.createContext({
    ...pathEditCleanupStubs(),
    pathNodeEdit: { object: null, objects: [hidden, locked] },
    groupIsolation: { path: [root, nested], selected: hidden, selectedObjects: [hidden, locked], guardingSelection: false },
    liveBooleanEdit: { active: false },
    canvas: { getObjects: () => [root], discardActiveObject() { this.discarded = true; } },
    restoreIsolationGroupSettings() {}, syncToolMode() {}, requestSelectionOverlayRender() {},
    renderGroupIsolationBar() {}, syncSelectionStatusOnly() {}, syncMenuState() {},
    scheduleSelectionUiSync() {}, showToast() {},
  });
  actual('isGroupIsolationActive', context);
  actual('isolationRootGroup', context);
  actual('objectIsWithinGroup', context);
  actual('stopPathNodeEdit', context);
  actual('exitGroupIsolation', context);

  assert.equal(context.exitGroupIsolation({ selectGroup: false, sync: false, toast: false }), true);

  assert.deepEqual(Array.from(context.groupIsolation.path), []);
  assert.deepEqual(Array.from(context.pathNodeEdit.objects), [], 'text references under the exited root are retired');
  assert.equal(context.pathNodeEdit.object, null);
  assert.equal(context.canvas.discarded, true);
});

function reconcileContext(roots, trackedTexts) {
  const context = vm.createContext({
    ...pathEditCleanupStubs(),
    pathNodeEdit: { object: null, objects: trackedTexts },
    canvas: { getObjects: () => roots, getActiveObject: () => null },
    isActiveSelectionObject: () => false,
    importedVectorFigureType: object => object?.figureType || null,
    isGroupIsolationActive: () => false,
  });
  actual('isCanvasTextObject', context);
  actual('groupChildren', context);
  actual('allCanvasObjectsDeep', context);
  actual('stopPathNodeEdit', context);
  actual('reconcileCanvasSelectionState', context);
  return context;
}

test('selection reconciliation keeps hidden and locked labels still present in the live canvas tree', () => {
  const hidden = text('live-hidden', { left: 0, top: 0, width: 8, height: 5 }, { visible: false });
  const locked = text('live-locked', { left: 12, top: 0, width: 8, height: 5 }, { locked: true });
  const nested = group([locked]);
  const root = group([hidden, nested]);
  hidden.group = root; nested.group = root; locked.group = nested;
  const context = reconcileContext([root], [hidden, locked]);

  const live = context.allCanvasObjectsDeep();
  assert.deepEqual(Array.from(live), [root, hidden, nested, locked]);
  context.reconcileCanvasSelectionState();

  assert.deepEqual(Array.from(context.pathNodeEdit.objects), [hidden, locked]);
  assert.equal(context.pathNodeEdit.object, null);
});

test('selection reconciliation retires a removed text identity despite stale canvas and group pointers', () => {
  const current = text('still-live', { left: 20, top: 0, width: 9, height: 5 });
  const removed = text('removed', { left: 0, top: 0, width: 8, height: 5 });
  const root = group([current]);
  current.group = root;
  removed.group = root;
  const canvas = { getObjects: () => [root], getActiveObject: () => null };
  removed.canvas = canvas; // Fabric may retain both pointers after removal.
  const context = reconcileContext([root], [removed]);
  context.canvas = canvas;

  assert.equal(context.allCanvasObjectsDeep().includes(removed), false);
  context.reconcileCanvasSelectionState();

  assert.deepEqual(Array.from(context.pathNodeEdit.objects), [], 'stale object ownership fields do not make removed text live');
  assert.equal(context.pathNodeEdit.object, null);
});

test('selection reconciliation retires the old identity when its figureId is reused by a replacement text object', () => {
  const old = text('reused-id', { left: 0, top: 0, width: 8, height: 5 });
  const replacement = text('reused-id', { left: 20, top: 0, width: 8, height: 5 });
  const root = group([replacement]);
  old.group = replacement.group = root;
  const canvas = { getObjects: () => [root], getActiveObject: () => null };
  old.canvas = canvas;
  const context = reconcileContext([root], [old]);
  context.canvas = canvas;

  const live = context.allCanvasObjectsDeep();
  assert.equal(live.includes(old), false);
  assert.equal(live.includes(replacement), true);
  assert.equal(old.figureId, replacement.figureId);
  assert.notEqual(old, replacement);
  context.reconcileCanvasSelectionState();

  assert.deepEqual(Array.from(context.pathNodeEdit.objects), [], 'reconciliation is based on object identity, not figureId');
  assert.equal(context.pathNodeEdit.object, null);
});

function pathEditSelectionSyncContext(trackedTexts, selectedObjects) {
  const context = vm.createContext({
    ...pathEditCleanupStubs(),
    pathNodeEdit: { object: null, objects: trackedTexts, dragging: null, selected: null,
      selectedHandles: [], selectedSegment: null, segmentDrag: null, marquee: null },
    selectedTopLevelObjects: () => selectedObjects,
    importedVectorFigureType: object => object?.figureType || null,
    isReferenceObject: object => Boolean(object?.reference),
    uniqueObjects: rows => [...new Set(rows)],
    state: { tool: 'select' },
    strokeWidthEdit: { active: false }, appearancePatternEdit: { active: false },
    appearanceGradientEdit: { active: false }, pdfGradientEdit: { active: false },
    nativePathEdit: { active: false },
    renderPathNodeOverlay() {}, updatePathNodeStatus() {},
  });
  actual('isCanvasTextObject', context);
  actual('directSelectionTextObjects', context);
  actual('stopPathNodeEdit', context);
  actual('syncPathNodeEditForSelection', context);
  return context;
}

test('selection sync preserves the exact tracked text set when the canvas selection still contains both labels', () => {
  const first = text('sync-first', { left: 0, top: 0, width: 8, height: 5 });
  const second = text('sync-second', { left: 12, top: 0, width: 8, height: 5 });
  const context = pathEditSelectionSyncContext([first, second], [first, second]);

  context.syncPathNodeEditForSelection(null);

  assert.equal(context.pathNodeEdit.objects.length, 2);
  assert.equal(context.pathNodeEdit.objects[0], first);
  assert.equal(context.pathNodeEdit.objects[1], second);
});

test('selection sync preserves tracked text during an empty transient canvas selection', () => {
  const first = text('transient-first', { left: 0, top: 0, width: 8, height: 5 });
  const second = text('transient-second', { left: 12, top: 0, width: 8, height: 5 });
  const context = pathEditSelectionSyncContext([first, second], []);

  context.syncPathNodeEditForSelection(null);

  assert.equal(context.pathNodeEdit.objects.length, 2);
  assert.equal(context.pathNodeEdit.objects[0], first);
  assert.equal(context.pathNodeEdit.objects[1], second);
});

test('selection sync retires tracked text when a different live object reuses its figureId', () => {
  const old = text('sync-reused-id', { left: 0, top: 0, width: 8, height: 5 });
  const replacement = text('sync-reused-id', { left: 16, top: 0, width: 8, height: 5 });
  const context = pathEditSelectionSyncContext([old], [replacement]);
  assert.equal(old.figureId, replacement.figureId);
  assert.notEqual(old, replacement);

  context.syncPathNodeEditForSelection(null);

  assert.equal(context.pathNodeEdit.objects.length, 0);
  assert.equal(context.pathNodeEdit.object, null);
});

test('selection sync retires tracked text when a parent group becomes the live selection', () => {
  const label = text('sync-parent-label', { left: 0, top: 0, width: 8, height: 5 });
  const parent = group([label]);
  label.group = parent;
  const context = pathEditSelectionSyncContext([label], [parent]);

  context.syncPathNodeEditForSelection(null);

  assert.equal(context.pathNodeEdit.objects.length, 0);
  assert.equal(context.pathNodeEdit.object, null);
});

test('selection sync retires a cached subset when the live canvas selection is a larger text set', () => {
  const first = text('sync-subset-first', { left: 0, top: 0, width: 8, height: 5 });
  const second = text('sync-subset-second', { left: 12, top: 0, width: 8, height: 5 });
  const context = pathEditSelectionSyncContext([first], [first, second]);

  context.syncPathNodeEditForSelection(null);

  assert.equal(context.pathNodeEdit.objects.length, 0);
  assert.equal(context.pathNodeEdit.object, null);
});

test('text retirement does not require a deliberately edited clip path to be a group child', () => {
  const clip = { figureId: 'clip', type: 'path', path: [['M', 0, 0], ['L', 5, 0]] };
  const context = reconcileContext([], [clip]);
  context.pathNodeEdit.object = clip;
  context.allCanvasObjectsDeep = () => { throw Error('Path-only editing must not enter text retirement.'); };
  assert.equal(context.reconcileCanvasSelectionState(), false);
  assert.equal(context.pathNodeEdit.object, clip);
  assert.deepEqual(Array.from(context.pathNodeEdit.objects), [clip]);
});
