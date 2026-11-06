'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const fabric = require('../vendor/fabric/index.min.js');
const source = fs.readFileSync(process.env.FIGURE_APP_SOURCE || require.resolve('../app/app.js'), 'utf8');

function actual(name, context) {
  const start = source.indexOf(`  function ${name}(`);
  const end = source.indexOf('\n  function ', start + 1);
  assert.ok(start > 0 && end > start, name);
  vm.runInContext(source.slice(start, end), context);
}
const plain = value => JSON.parse(JSON.stringify(value));
const left = [['M', 0, 0], ['L', 20, 0], ['L', 20, 30], ['L', 0, 30], ['Z']];
const right = [['M', 40, 0], ['L', 64, 3], ['L', 59, 30], ['L', 40, 26], ['Z']];
function record(id, commands) {
  return {id, closed:true, commands, nodes:commands.filter(c => c[0] !== 'Z').map((_, index) =>
    ({id:`${id}-node-${index}`, type:'corner', contourId:id, contourNodeIndex:index}))};
}

function fixture({nativeRectangle = false, locked = false} = {}) {
  const object = new fabric.Path([...left, ...right], {figureId:'placed-path', left:17, top:31,
    angle:23, scaleX:1.3, scaleY:.8, fill:'#8ec8ff', stroke:null, objectCaching:true});
  object.locked = locked;
  const trace = [];
  const world = (o, p) => fabric.util.transformPoint(new fabric.Point(p.x-o.pathOffset.x, p.y-o.pathOffset.y), o.calcTransformMatrix());
  const context = vm.createContext({fabricRef:fabric, BEZIER_NODE_TYPES:new Set(['corner','smooth','symmetric']),
    issuedUniformPathRenderers:new WeakMap(),
    FigureStudioPdfSvgMaterializer:{isNativeRectangleDisplayPath:() => nativeRectangle},
    isLineVectorObject:() => false, isReferenceObject:() => false,
    isEditablePathObject:o => o instanceof fabric.Path, canUseBezierNodeEditing:() => true,
    variableStrokeProfileActive:() => false, readStyle:() => ({}),
    groupChildren:() => [], attachLineVectorRenderer:() => {throw Error('Unexpected line renderer');},
    pathEditObjectId:o => o.figureId, makeId:prefix => prefix+'-generated',
    normalizeContourRecord:value => plain(value), copyPathCommands:commands => plain(commands),
    setBezierNodeMeta:(o, metadata) => {o.figureStudioBezierNodeMeta = plain(metadata);},
    pdfSourceIdForObject:() => '', pathLocalPointToCanvas:world,
    moveObjectBySceneDelta:(o, x, y) => {o.set({left:o.left+x, top:o.top+y}); o.setCoords();},
    refreshObjectHierarchy:o => {trace.push('refresh'); o.setCoords();}
  });
  for (const name of ['canUseVariableStroke','attachVariableStrokeRenderer','reconcileVariableStrokeRenderers',
    'setPathCommandsWithSceneStableFrame','setPathContourRecords']) actual(name, context);
  return {object, context, world, trace};
}

test('two-to-one contour forward mutation immediately matches actual restore renderer/cache policy', async () => {
  const {object, context, world} = fixture();
  const original = world(object, {x:40,y:0});
  assert.equal(context.setPathContourRecords(object, [record('surviving-contour', right)]), true);
  const changed = world(object, {x:40,y:0});
  assert.ok(Math.hypot(original.x-changed.x, original.y-changed.y) < 1e-9, 'world placement');
  assert.equal(object.objectCaching, false, 'forward edit adopts the existing single-contour renderer policy');
  assert.equal(object._figureStudioVariableStrokeRendererAttached, true);
  const forward = object.toObject(['figureId','figureStudioBezierNodeMeta']);
  const restored = await fabric.Path.fromObject(plain(forward));
  context.reconcileVariableStrokeRenderers([restored]);
  assert.deepEqual(plain(restored.toObject(['figureId','figureStudioBezierNodeMeta'])), plain(forward));
  assert.deepEqual(plain(object.path), right);
  assert.deepEqual(object.figureStudioBezierNodeMeta.contours, [{id:'surviving-contour',closed:true}]);
  assert.deepEqual(object.figureStudioBezierNodeMeta.nodes.map(n=>n.id), right.slice(0,-1).map((_,index)=>`surviving-contour-node-${index}`));
});

test('remaining multiple contours retain the existing stock renderer and cache choice', () => {
  const {object, context} = fixture();
  assert.equal(context.setPathContourRecords(object, [record('left', left), record('right', right)]), true);
  assert.equal(object.objectCaching, true);
  assert.equal(object._render, fabric.Path.prototype._render);
  assert.equal(object._figureStudioVariableStrokeRendererAttached, undefined);
});

test('existing admitted native uniform-rectangle dispatch remains unchanged', () => {
  // Native rectangle admission is an explicit host adapter here; genuine PDF
  // import/painting/persistence is checked separately in the browser.
  const {object, context} = fixture({nativeRectangle:true});
  assert.equal(context.setPathContourRecords(object, [record('native-rectangle', left)]), true);
  assert.equal(object._render, fabric.Path.prototype._render);
  assert.equal(object.objectCaching, true);
  assert.equal(object._figureStudioVariableStrokeRendererAttached, undefined);
});

test('locked path retains the existing eligibility guard without installing a renderer', () => {
  const {object, context} = fixture({locked:true});
  assert.equal(context.setPathContourRecords(object, [record('locked', right)]), true);
  assert.equal(object.objectCaching, true);
  assert.equal(object._figureStudioVariableStrokeRendererAttached, undefined);
});

test('public contour deletion publishes changed artwork after selection-only suppression and before history', () => {
  const {object, context} = fixture();
  context.setPathContourRecords(object, [record('left',left),record('right',right)]);
  const recordsFor = value => {
    const pieces=[];
    for(const command of value.path){if(command[0]==='M')pieces.push([]);pieces.at(-1).push(command);}
    return pieces.map((commands,index)=>{
      const id=value.figureStudioBezierNodeMeta.contours[index].id;
      return {id,closed:true,commands:plain(commands),nodes:value.figureStudioBezierNodeMeta.nodes.filter(node=>node.contourId===id)};
    });
  };
  const nodesFor = value => {
    const result=[];
    value.path.forEach((command,index)=>{if(command[0]!=='Z'){
      const contourId=value.figureStudioBezierNodeMeta.nodes[result.length].contourId;
      result.push({commandIndex:index,nodeIndex:result.length,contourIndex:value.figureStudioBezierNodeMeta.contours.findIndex(contour=>contour.id===contourId)});
    }});
    return result;
  };
  let artwork=0,overlay=0,history=0;
  const trace=[];
  const canvas={getObjects:()=>[object],discardActiveObject(){context.selectionOverlayRenderOnly=true;trace.push('discard');},
    requestRenderAll(){if(context.selectionOverlayRenderOnly||context.suppressNextFullCanvasRender)overlay++;else{artwork++;trace.push('artwork');}}};
  Object.assign(context,{canvas,selectionOverlayRenderOnly:false,suppressNextFullCanvasRender:false,
    pathTopologyActionState:()=>({enabled:true}),captureDirectSelectionHistoryState:()=>({objectId:object.figureId}),
    selectedPathEndpointItems:()=>nodesFor(object).slice(0,4).map(descriptor=>({object,descriptor})),
    qualifyPathHandle:(owner,descriptor)=>({...descriptor,object:owner,objectId:owner.figureId,nodeId:owner.figureStudioBezierNodeMeta.nodes[descriptor.nodeIndex].id}),
    canDeleteAuthoredLineEndpoints:()=>false,pathContourRecords:recordsFor,topologyParent:()=>null,collectionObjects:owner=>owner.getObjects(),
    normalizedBezierNodeMeta:value=>plain(value.figureStudioBezierNodeMeta),
    captureRemovedObjectConnectorEndpoints:()=>[],detachRemovedObjectConnectorEndpoints:()=>{},
    removeTopologyObject:()=>{throw Error('The retained path must not be removed');},
    pathNodeDescriptors:nodesFor,pathNodeEdit:{object,objects:[object]},
    ensureDirectSelectionCanvasCollection(){context.selectionOverlayRenderOnly=true;trace.push('selection');},
    recordPathGeometryEdit(){trace.push('record');},renderPathNodeOverlay(){context.selectionOverlayRenderOnly=true;trace.push('overlay');},
    syncUi(){context.selectionOverlayRenderOnly=true;trace.push('ui');},
    commitHistory(){history++;trace.push('history');},showToast:()=>{}});
  actual('requestCanvasArtworkRender',context);
  actual('deleteSelectedPathNode',context);
  assert.equal(context.deleteSelectedPathNode(),true);
  assert.deepEqual(plain(object.path),right);
  assert.equal(artwork,1,'changed document gets one ordinary full-paint request');
  assert.equal(overlay,0,'selection-only optimization cannot consume the mutation paint');
  assert.equal(history,1);
  assert.ok(trace.indexOf('artwork')>trace.indexOf('ui'));
  assert.ok(trace.indexOf('artwork')<trace.indexOf('history'));
});
