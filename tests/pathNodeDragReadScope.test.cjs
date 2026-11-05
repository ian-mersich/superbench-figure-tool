'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const fabric=require('../vendor/fabric/index.min.js');
const source=fs.readFileSync(require.resolve('../app/app.js'),'utf8');
// Literal beta23 App632 function: the negative control performs the original work.
const legacy=fs.readFileSync(require.resolve('./fixtures/path-node-drag-app632.js'),'utf8');
function actual(text,name,context){
  const start=text.indexOf('  function '+name+'('),next=text.indexOf('\n  function ',start+5);
  assert.ok(start>=0,name);vm.runInContext(text.slice(start,next<0?text.length:next),context);
}
const helpers=['isEditablePathObject','isLineVectorObject','roundPathCoord','pathPointsCoincide',
  'pathContourDescriptors','pathContourForCommand','pathCommandEndpoint','pathEndpointIndices',
  'pathNodeDescriptors','pathHandleDescriptors','pathControlDescriptor','previousPathEndpointDescriptor',
  'nextPathEndpointDescriptor','controlNodeDescriptor','normalizedBezierNodeMeta','inferredBezierNodeType',
  'incomingPathControlDescriptor','outgoingPathControlDescriptor','qualifyPathHandle','samePathHandle',
  'pathEditObjectId','selectedPathHandleRefs','objectForPathHandleRef','pathHandleCanvasPoint',
  'pathLocalPointToCanvas','pathRenderingOffset','lineVectorEndpointDescriptors','selectedPathHandleDescriptor',
  'copyPathCommands','pathBodyDragTranslations','captureDirectSelectionTextPositions','bezierNodeType'];
function fixture(old=false){
  const objects=Array.from({length:19},(_,i)=>new fabric.Path([
    ['M',0,0],['C',10,-5,20,5,30,0],['Q',20,15,0,0],['Z'],['M',50,50],['L',60,50]
  ],{figureId:'p'+i,figureType:'path',left:17+i*10,top:-9,angle:13,scaleX:1.2,scaleY:.8,objectCaching:false}));
  const group=new fabric.Group(objects,{angle:-21,scaleX:.91,scaleY:1.07,skewX:7});group.setCoords();
  const texts=[{figureId:'live-label',text:'Pathway β',left:31,top:42,group}];
  const state={object:objects[0],objects,selected:null,selectedHandles:[]};
  const context=vm.createContext({fabricRef:fabric,pathNodeEdit:state,
    isReferenceObject:o=>Boolean(o?.reference),
    BEZIER_NODE_TYPES:new Set(['corner','smooth','symmetric']),readStyle:o=>o.styleMeta||{},
    pathNodeEditObjects:()=>objects,directSelectionTextObjects:()=>texts,
    fabricPoint:(x,y)=>new fabric.Point(x,y),pathObjectSceneMatrix:o=>o.calcTransformMatrix(),
    lineVectorEndpoints:o=>o._figureStudioArrowBase,
    resetPaintedVectorDirectSelectionCycle(){},els:{viewport:{focus(){}},pathNodeOverlay:{setPointerCapture(){}}},
    canvas:{getScenePoint:()=>({x:11,y:23})},ensureDirectSelectionCanvasCollection(){},
    cloneManifestValue:(v,fallback)=>v==null?fallback:structuredClone(v),startPdfPointScreenGesture(){}});
  for(const name of helpers)actual(source,name,context);
  let normalizing=null,metadataWork=0;
  const descriptors=context.pathNodeDescriptors,normalize=context.normalizedBezierNodeMeta;
  context.pathNodeDescriptors=o=>{if(normalizing&&!normalizing.counted){metadataWork++;normalizing.counted=true;}return descriptors(o);};
  context.normalizedBezierNodeMeta=o=>{const previous=normalizing;normalizing={counted:false};try{return normalize(o);}finally{normalizing=previous;}};
  for(let i=0;i<objects.length;i++){
    const count=i<14?6:5;
    state.selectedHandles.push(...Array.from(context.pathHandleDescriptors(objects[i])).slice(0,count).map(d=>context.qualifyPathHandle(objects[i],d)));
  }
  assert.equal(state.selectedHandles.length,109);
  context.selectPathHandle=(o,index,type)=>{
    const d=context.pathHandleDescriptors(o).find(d=>d.commandIndex===index&&d.handleType===type);
    state.selected=context.qualifyPathHandle(o,d);
  };
  actual(old?legacy:source,'beginPathNodeDrag',context);
  const event={type:'pointerdown',pointerId:7,ctrlKey:true,preventDefault(){},stopPropagation(){}};
  const element={classList:{add(){}}};
  return {context,objects,state,texts,run(){metadataWork=0;context.beginPathNodeDrag(event,0,'endpoint',objects[0],element);return metadataWork;}};
}
function shape(f){
  const g=f.state.dragging;
  return JSON.parse(JSON.stringify(g,(key,value)=>['object','parent'].includes(key)?value?.figureId||null:value));
}
function authored(f){return JSON.stringify(f.objects.map(o=>({path:o.path,matrix:o.calcTransformMatrix(),meta:o.figureStudioBezierNodeMeta})));}

test('109-handle setup matches literal released geometry and bounds repeated metadata work',()=>{
  const current=fixture(),old=fixture(true),before=authored(current);
  const work=current.run(),oldWork=old.run();
  assert.deepEqual(shape(current),shape(old));
  assert.equal(authored(current),before,'setup leaves all authored geometry and metadata unchanged');
  assert.equal(current.texts[0].text,'Pathway β');
  assert.ok(work<=current.objects.length,'one metadata normalization per selected native path');
  assert.ok(oldWork>work*10,'literal old setup violates the same work bound');
  assert.equal(current.context.normalizedBezierNodeMeta.overlayReadCache,undefined);
});

test('new gestures see in-place geometry and node metadata edits, with no retained scope',()=>{
  const current=fixture(),old=fixture(true);current.run();old.run();
  for(const f of [current,old]){
    f.objects[0].path[1][1]+=7;
    f.objects[0].figureStudioBezierNodeMeta={nodes:[{id:'new-start',type:'smooth'}]};
    f.objects[0].set({left:93,angle:27});f.objects[0].setCoords();
  }
  current.run();old.run();assert.deepEqual(shape(current),shape(old));
  assert.equal(current.state.dragging.pathSnapshots[0].path[1][1],17);
  assert.equal(current.context.normalizedBezierNodeMeta.overlayReadCache,undefined);
});

test('nested scope and throwing setup restore the exact enclosing scope',()=>{
  const f=fixture(),enclosing=new WeakMap();f.context.normalizedBezierNodeMeta.overlayReadCache=enclosing;
  f.run();assert.equal(f.context.normalizedBezierNodeMeta.overlayReadCache,enclosing);
  assert.equal(enclosing.has(f.objects[0]),false,'gesture reads do not populate the enclosing scope');
  f.context.selectPathHandle=()=>{throw Error('setup rejected');};
  assert.throws(()=>f.run(),/setup rejected/);
  assert.equal(f.context.normalizedBezierNodeMeta.overlayReadCache,enclosing);
  f.context.beginPathNodeDrag({},0,'endpoint',null);
  assert.equal(f.context.normalizedBezierNodeMeta.overlayReadCache,enclosing,'empty target leaves scope alone');
});
