'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const fabric = require('../vendor/fabric/index.min.js');
const source = fs.readFileSync(require.resolve('../app/app.js'), 'utf8');

function actual(name, context) {
  const start = source.indexOf(`  function ${name}(`), end = source.indexOf('\n  function ', start + 1);
  assert.ok(start > 0 && end > start, name);
  vm.runInContext(source.slice(start, end), context);
  return context[name];
}
const clone = value => JSON.parse(JSON.stringify(value));
function world(object, commandIndex, xIndex) {
  const c = object.path[commandIndex], p = new fabric.Point(c[xIndex] - object.pathOffset.x, c[xIndex + 1] - object.pathOffset.y);
  return fabric.util.transformPoint(p, object.calcTransformMatrix());
}
function near(a, b, message) { assert.ok(Math.hypot(a.x-b.x, a.y-b.y) < .0005, message); }

function fixture(type, nested = false, bothSelected = false) {
  const object = new fabric.Path([['M',0,0],['C',15,-40,40,-30,60,0],['C',80,30,100,40,120,0]],
    {left:120,top:100,fill:null,stroke:'#7851a9',figureId:'curve'});
  const neighbor = new fabric.Path('M 0 0 L 40 0 L 40 30 Z', {left:350,top:160,fill:'#123456',figureId:'neighbor'});
  if (nested) new fabric.Group([new fabric.Group([object], {angle:23,flipX:true,scaleX:.91,scaleY:1.06}), neighbor], {angle:-13,scaleX:.87,scaleY:.93});
  object.figureStudioBezierNodeMeta = {schema:'figureStudio.bezierNodes.v1',nodes:[{id:'middle',type}],retainedExtension:{value:17}};
  const snapshot = {objectId:'curve',path:clone(object.path),bezierNodeMeta:clone(object.figureStudioBezierNodeMeta)};
  const descriptor = () => ({commandIndex:1,handleType:'control2',xIndex:3,yIndex:4,command:object.path[1]});
  const opposite = () => ({commandIndex:2,handleType:'control1',xIndex:1,yIndex:2,command:object.path[2]});
  const anchor = {commandIndex:1,handleType:'endpoint',xIndex:5,yIndex:6};
  const start = world(object,1,3), pointerStart = {x:start.x+3,y:start.y-2};
  const handles = [{...descriptor(),objectId:'curve'}];
  if (bothSelected) handles.push({...opposite(),objectId:'curve'});
  const dragging = {objectId:'curve',commandIndex:1,handleType:'control2',startPoint:{...start},pointerStartPoint:pointerStart,initialNodeType:type,
    handles,pathSnapshots:[snapshot],translations:[{objectId:'curve',path:clone(object.path),inverseSceneMatrix:fabric.util.invertTransform(object.calcTransformMatrix()),
      operands:[{commandIndex:1,xIndex:3,yIndex:4},...(bothSelected?[{commandIndex:2,xIndex:1,yIndex:2}]:[])]}]};
  const position = (o,d) => world(o,d.commandIndex,d.xIndex);
  const context = vm.createContext({fabricRef:fabric,BEZIER_NODE_TYPES:new Set(['corner','smooth','symmetric']),
    // This geometry fixture uses the ordinary native route, with no prepared
    // point preview; screen-preview behavior has its own focused tests.
    pdfPointScreenPreparation:null,pdfPointScreenPreview:null,startPdfPointScreenGesture(){},closePdfPointScreenPreview(){},deferPdfPointNodeOverlay:()=>false,
    requestPdfPointArtworkRender(){context.canvas.requestRenderAll();},directSelectionObjects:()=>[object],
    artboardToolInteraction:null,zoomToolInteraction:null,smartConnectorInteraction:{endpoint:null,bend:null},strokeWidthEdit:{},appearancePatternEdit:{},appearanceGradientEdit:{},pdfGradientEdit:{},nativePathEdit:{},
    pathNodeEdit:{object,dragging},canvas:{getScenePoint:e=>e.point,requestRenderAll(){}},
    objectForPathHandleRef:()=>object,pathEditObjectId:o=>o.figureId,pathHandleDescriptors:()=>[descriptor(),opposite()],
    samePathHandle:(a,b)=>a.commandIndex===b.commandIndex&&a.handleType===b.handleType,pathNodeEditObjects:()=>[object],
    snapWorkspacePoint:p=>p,snappingBypassed:()=>true,isLineVectorObject:()=>false,isOrdinaryVectorEnginePathPreviewCandidate:()=>false,
    controlNodeDescriptor:()=>anchor,oppositePathControlDescriptor:()=>opposite(),pathHandleCanvasPoint:position,
    setPathHandleCanvasPoint(o,d,p){const q=fabric.util.transformPoint(new fabric.Point(p.x,p.y),fabric.util.invertTransform(o.calcTransformMatrix()));d.command[d.xIndex]=q.x+o.pathOffset.x;d.command[d.yIndex]=q.y+o.pathOffset.y;},
    bezierNodeType:o=>o.figureStudioBezierNodeMeta.nodes[0].type,
    setBezierNodeType(o,d,t){o.figureStudioBezierNodeMeta=o.figureStudioBezierNodeMeta?clone(o.figureStudioBezierNodeMeta):{schema:'figureStudio.bezierNodes.v1',nodes:[{id:'middle',type:'corner'}]};o.figureStudioBezierNodeMeta.nodes[0].type=t;},
    cloneManifestValue:clone,renderPathNodeOverlay(){},resetPaintedVectorDirectSelectionCycle(){},
    els:{pathNodeOverlay:{releasePointerCapture(){}}},hideGuideSnapCue(){},hideSmartGuideCues(){},updatePathNodeStatus(){},syncInspector(){}});
  actual('copyPathCommands',context);actual('translatePathGestureOperands',context);
  actual('restorePathHandleDrag',context);const cancel=actual('cancelPathNodeDrag',context);
  const move = actual('onPathNodePointerMove',context);
  const before = clone({path:object.path,metadata:object.figureStudioBezierNodeMeta,neighbor:neighbor.toObject(),matrix:object.calcTransformMatrix()});
  return {object,neighbor,dragging,snapshot,before,start,pointerStart,opposite:()=>world(object,2,1),anchor:()=>world(object,1,5),
    move(dx,dy,altKey,shiftKey=false){move({point:{x:pointerStart.x+dx,y:pointerStart.y+dy},altKey,shiftKey,preventDefault(){}});},cancel};
}

for (const type of ['corner','smooth','symmetric']) for (const nested of [false,true]) {
  test(`Alt controls only the grabbed side from ${type}, nested=${nested}`,()=>{
    const f=fixture(type,nested),opposite={...f.opposite()},anchor={...f.anchor()},snapshot=JSON.stringify(f.snapshot);
    for (const [dx,dy] of [[17,-11],[-13,23],[26,9]]) {
      f.move(dx,dy,true);
      near(world(f.object,1,3),{x:f.start.x+dx,y:f.start.y+dy},'off-center grabbed control follows delivered world displacement');
      near(f.opposite(),opposite,'initial opposite control must stay fixed');near(f.anchor(),anchor,'anchor must stay fixed');
      assert.equal(f.object.figureStudioBezierNodeMeta.nodes[0].type,'corner');
      assert.equal(JSON.stringify(f.snapshot),snapshot,'pointerdown snapshot remains immutable');
      assert.deepEqual(clone(f.neighbor.toObject()),f.before.neighbor,'neighbor remains literal');
    }
  });
  test(`exact out-and-back restores raw path and complete metadata from ${type}, nested=${nested}`,()=>{
    const f=fixture(type,nested);f.move(17,-11,true);f.move(0,0,true);
    assert.deepEqual(clone(f.object.path),f.before.path);
    assert.deepEqual(clone(f.object.figureStudioBezierNodeMeta),f.before.metadata);
    assert.equal(f.dragging.nodeTypeEdit,false);
  });
}
for (const type of ['smooth','symmetric']) {
  test(`modifier transitions derive both sides from the initial ${type} snapshot`,()=>{
    const f=fixture(type,true),opposite={...f.opposite()},anchor=f.anchor(),length=Math.hypot(opposite.x-anchor.x,opposite.y-anchor.y);
    f.move(23,-9,false);f.move(23,-9,true);near(f.opposite(),opposite,'pressing Alt restores the initial opposite, not the preceding coupled sample');
    f.move(-11,19,false);const moved=world(f.object,1,3),other=f.opposite(),a={x:moved.x-anchor.x,y:moved.y-anchor.y},b={x:other.x-anchor.x,y:other.y-anchor.y};
    assert.ok(Math.abs(a.x*b.y-a.y*b.x)<1e-7 && a.x*b.x+a.y*b.y<0,'releasing Alt restores the original coupled relationship');
    assert.ok(Math.abs(Math.hypot(b.x,b.y)-(type==='smooth'?length:Math.hypot(a.x,a.y)))<1e-8);
    f.move(0,0,false);assert.deepEqual(clone(f.object.path),f.before.path);assert.deepEqual(clone(f.object.figureStudioBezierNodeMeta),f.before.metadata);
  });
}
test('Alt overrides opposite-control membership without changing other operands',()=>{
  const f=fixture('corner',true,true),opposite={...f.opposite()};f.move(15,9,true);near(f.opposite(),opposite,'explicit opposite handle is preserved from initial snapshot');
  f.object.path.forEach((c,i)=>c.forEach((v,j)=>{if(i!==1||![3,4].includes(j))assert.equal(v,f.before.path[i][j]);}));
});
test('Alt plus Shift constrains the dragged handle about its fixed anchor',()=>{
  const f=fixture('smooth',true),opposite={...f.opposite()},anchor=f.anchor();f.move(23,17,true,true);
  const p=world(f.object,1,3),angle=Math.atan2(p.y-anchor.y,p.x-anchor.x)/(Math.PI/4);
  assert.ok(Math.abs(angle-Math.round(angle))<1e-8);near(f.opposite(),opposite,'Shift must not rotate the other side');
});

for(const nested of [false,true])for(const ending of ['return','cancel']){
  test(`absent authored node metadata stays omitted after Alt ${ending}, nested=${nested}`,()=>{
    const f=fixture('corner',nested);
    delete f.object.figureStudioBezierNodeMeta;f.snapshot.bezierNodeMeta=null;
    const authored=()=>clone(f.object.toObject(['figureStudioBezierNodeMeta']));
    const before=authored();assert.equal(Object.hasOwn(before,'figureStudioBezierNodeMeta'),false);
    f.move(17,-11,true);assert.ok(f.object.figureStudioBezierNodeMeta,'meaningful move reaches the conversion setter');
    if(ending==='return')f.move(0,0,true);else assert.equal(f.cancel({preventDefault(){}}),true);
    assert.deepEqual(clone(f.object.path),f.before.path);
    assert.equal(f.object.figureStudioBezierNodeMeta,undefined);
    assert.equal(Object.hasOwn(authored(),'figureStudioBezierNodeMeta'),false,'saved authored record must retain omission');
    assert.deepEqual(authored(),before,'complete native authored object remains literal after return/cancel');
  });
}
