'use strict';
// Actual extracted App target finder, mouse-down selection and selection helper;
// actual bundled native Group/Path membership. Pointer delivery is an adapter;
// genuine public browser and saved-file continuation remain separate checks.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const fabric=require('../vendor/fabric/index.min.js');fabric.setEnv({document:{},window:{},dispose(){}});
const source=fs.readFileSync(process.env.FIGURE_APP_SOURCE || require.resolve('../app/app.js'),'utf8');
const {extract}=require('./helpers/pdfDenseCanvasRestoreSource.cjs');
const begin=source.indexOf('    const fabricFindTarget = canvas.findTarget?.bind(canvas);');
const end=source.indexOf('    const selectionEventCanvas = canvas;',begin);
assert.ok(begin>0&&end>begin);
function fixture(){
 const first=new fabric.Path('M 0 0 L 10 0 L 10 10 Z',{left:-20,top:-10}),second=new fabric.Path('M 0 0 L 10 0 L 10 10 Z',{left:15,top:10});
 first.figureId='first';second.figureId='second';
 const group=new fabric.Group([first,second]);group.figureId='group';
 let hit=first,control=false,stockCalls=0,childCalls=0,discarded=0,ended=0;
 const selectionUi=[];
 const canvas={active:first,_currentTransform:null,getActiveObject(){return this.active;},
  setActiveObject(object){this.active=object;},discardActiveObject(){discarded++;this.active=null;},
  findTarget(){stockCalls++;return {target:group,subTargets:[second],container:group};},
  getViewportPoint:event=>event.point,requestRenderAll(){},endCurrentTransform(){ended++;this._currentTransform=null;}};
 first.findControl=()=>control?{key:'br',control:{}}:null;second.findControl=()=>null;
 const noop=()=>{},context=vm.createContext({canvas,fabricRef:fabric,performance,console,
  state:{tool:'select'},groupIsolation:{path:[group],selected:first,selectedObjects:[first]},
  transientCanvasTransform:null,recentCanvasHitTestPerformanceAudits:[],lastCanvasHitTestPerformanceAudit:null,
  retainCanvasPerformanceAudit:(_rows,value)=>value,isLineVectorObject:()=>false,canvasPoint:event=>event.point,
  vectorPaintedHitTest:()=>true,usesNarrowVectorHitContract:()=>false,paintedVectorTargetAtPoint:()=>null,
  lineVectorSelectionTolerance:()=>3,lineVectorPaintedHitTest:()=>true,
  isolationChildAtScenePoint(){childCalls++;return hit;},
  isolatedSelectedObjects:()=>context.groupIsolation.selectedObjects.slice(),uniqueObjects:objects=>[...new Set(objects)],
  ensureIsolationObjectIdentity:object=>object,selectionOverlayRenderOnly:false,
  canvasUiDeliveryOwner:()=>({}),canvasUiDeliveryIsCurrent:()=>true,window:{queueMicrotask:noop},
  requestSelectionOverlayRender:noop,syncSelectionStatusOnly:noop,
  syncInspector(){selectionUi.push({kind:'inspector',ids:context.groupIsolation.selectedObjects.map(o=>o.figureId)});},
  scheduleSelectionUiSync(){selectionUi.push({kind:'deferred',ids:context.groupIsolation.selectedObjects.map(o=>o.figureId)});},
  revealEditableSvgSelectionInLayers:noop,showToast:noop,hideToast:noop,
  cancelSelectionUiSync:noop,isAnchorTool:()=>false,syncLineVectorSelectionChrome:noop,
  layerTreeSelectionUnavailableReason:object=>object?.locked?'locked':'',objectLayerId:()=> 'layer',
  objectLayerById:()=>({id:'layer',visible:true,locked:false}),activeObjectLayerState:()=>({}),isActiveSelectionObject:()=>false
 });
 const nativeBodyDragBinding=/^  let nativePathBodyDrag = null;$/m.exec(source);
 assert.ok(nativeBodyDragBinding,'actual private native body-drag initial state');
 vm.runInContext(nativeBodyDragBinding[0],context);
 context.pendingSingleObjectShiftClick=null;
 for(const name of ['isGroupIsolationActive','activeIsolationGroup','objectIsWithinGroup','selectIsolatedObjects','selectIsolatedObject','toggleIsolatedObjectSelection','selectLayerTreeObject','captureSingleObjectShiftClick','onCanvasMouseDown'])vm.runInContext(extract(source,name),context);
 vm.runInContext(source.slice(begin,end),context);
 const event=(extra={})=>({button:0,point:{x:0,y:0},...extra});
 const down=(extra={})=>context.onCanvasMouseDown({e:event(extra),target:canvas.active});
 return {first,second,group,canvas,c:context,event,down,selectionUi,
  hit(value){hit=value;},control(value){control=value;},
  counts:()=>({stockCalls,childCalls,discarded,ended}),close(){group.dispose();}};
}
test('Object Selection resolves the actual isolated native child before the enclosing group',()=>{
 const x=fixture();try{const target=x.canvas.findTarget(x.event());assert.equal(target.target,x.first);assert.equal(target.currentTarget,x.first);
  assert.deepEqual(Array.from(target.subTargets),[]);assert.equal(target.container,x.group);assert.equal(x.counts().stockCalls,0);
 }finally{x.close();}
});

for(const count of [0,1,2])test(`isolated ${count}-child selection refreshes its actual target before deferred UI`,()=>{
 const x=fixture();try{
  const selected=[x.first,x.second].slice(0,count),before=x.group.getObjects().map(o=>o.calcTransformMatrix().slice());
  assert.equal(x.c.selectIsolatedObjects(selected),count>0);
  assert.deepEqual(x.selectionUi,[{kind:'inspector',ids:selected.map(o=>o.figureId)},{kind:'deferred',ids:selected.map(o=>o.figureId)}]);
  assert.deepEqual(x.group.getObjects(),[x.first,x.second]);
  assert.deepEqual(x.group.getObjects().map(o=>o.calcTransformMatrix()),before);
 }finally{x.close();}
});

test('internal isolated selection with sync false leaves Inspector refresh to its command owner',()=>{
 const x=fixture();try{
  assert.equal(x.c.selectIsolatedObjects([x.second],{sync:false}),true);
  assert.deepEqual(x.selectionUi,[]);assert.equal(x.c.groupIsolation.selected,x.second);
 }finally{x.close();}
});

test('Layers forwards sync false for both single and additive nested selection',()=>{
 const x=fixture();try{
  assert.equal(x.c.selectLayerTreeObject(x.second,{sync:false,toast:false}),true);
  assert.equal(x.c.selectLayerTreeObject(x.first,{sync:false,additive:true,toast:false}),true);
  assert.deepEqual(x.selectionUi,[]);
  assert.deepEqual(Array.from(x.c.groupIsolation.selectedObjects),[x.second,x.first]);
 }finally{x.close();}
});

test('unavailable Layers target preserves native selection without refreshing controls',()=>{
 const x=fixture();try{
  x.second.locked=true;assert.equal(x.c.selectLayerTreeObject(x.second),false);
  assert.deepEqual(x.selectionUi,[]);assert.equal(x.c.groupIsolation.selected,x.first);
  assert.deepEqual(x.group.getObjects(),[x.first,x.second]);
 }finally{x.close();}
});

test('named recall suppresses per-sibling refresh within an already-entered nested selection',()=>{
 const x=fixture();try{
  const objects=new Map([[x.first.figureId,x.first],[x.second.figureId,x.second],[x.group.figureId,x.group]]);
  Object.assign(x.c,{activeSavedSelectionState:()=>({items:[{id:'saved',name:'Saved children',parentId:x.group.figureId,objectIds:[x.first.figureId,x.second.figureId]}]}),
   findNestedObjectByFigureId:id=>objects.get(id),inheritedMasterMeta:()=>null,topLevelLayerObject:()=>x.group,
   // Scope: sibling-loop sync forwarding after group entry. Real exit/re-entry
   // and its bounded per-depth Inspector refresh are outside this adapter.
   exitGroupIsolation(){},objectLayerRoots:()=>[x.group],
   syncUi(){x.selectionUi.push({kind:'final',ids:x.c.groupIsolation.selectedObjects.map(o=>o.figureId)});}});
  vm.runInContext(extract(source,'recallNamedSelection'),x.c);
  const result=x.c.recallNamedSelection('saved',{toast:false});
  assert.equal(result.status,'ok');assert.equal(result.count,2);
  assert.deepEqual(x.selectionUi,[{kind:'final',ids:[x.first.figureId,x.second.figureId]}]);
  assert.deepEqual(x.group.getObjects(),[x.first,x.second]);
 }finally{x.close();}
});
test('clicking a different child agrees with semantic selection and preserves the native drag already started',()=>{
 const x=fixture();try{x.hit(x.second);const target=x.canvas.findTarget(x.event());x.canvas.active=target.target;
  const transform=x.canvas._currentTransform={target:x.second,action:'drag',corner:''};x.down();
  assert.equal(x.c.groupIsolation.selected,x.second);assert.deepEqual(Array.from(x.c.groupIsolation.selectedObjects),[x.second]);
  assert.equal(x.canvas.active,x.second);assert.equal(x.canvas._currentTransform,transform);assert.equal(x.counts().discarded,0);
  assert.equal(x.second.group,x.group);assert.equal(x.first.group,x.group);
 }finally{x.close();}
});
for(const tool of ['select','freeTransform'])for(const shiftKey of [true,false])test(tool+' preserves an owned outside-paint control, shift='+shiftKey,()=>{
 const x=fixture();try{x.c.state.tool=tool;x.control(true);x.hit(null);
  const target=x.canvas.findTarget(x.event({shiftKey}));assert.equal(target.target,x.first);
  const before=x.counts().childCalls,transform=x.canvas._currentTransform={target:x.first,action:'scale',corner:'br'};
  x.down({shiftKey});assert.equal(x.counts().childCalls,before);assert.equal(x.counts().discarded,0);
  assert.equal(x.c.groupIsolation.selected,x.first);assert.equal(x.canvas._currentTransform,transform);
 }finally{x.close();}
});
test('Shift child selection keeps native group membership and uses the isolated multi-selection',()=>{
 const x=fixture();try{x.hit(x.second);x.canvas.active=x.second;x.down({shiftKey:true});
  assert.deepEqual(Array.from(x.c.groupIsolation.selectedObjects),[x.first,x.second]);assert.equal(x.c.groupIsolation.selected,x.second);
  assert.equal(x.first.group,x.group);assert.equal(x.second.group,x.group);assert.deepEqual(x.group.getObjects(),[x.first,x.second]);
 }finally{x.close();}
});
for(const modifier of ['shiftKey','ctrlKey','metaKey'])test(modifier+' child gesture changes selection without moving only the primary',()=>{
 const x=fixture();try{x.hit(x.second);x.canvas.active=x.second;
  x.canvas._currentTransform={target:x.second,action:'drag',corner:'',actionPerformed:false};x.down({[modifier]:true});
  assert.equal(x.canvas._currentTransform,null);assert.equal(x.counts().ended,1);
  assert.deepEqual(Array.from(x.c.groupIsolation.selectedObjects),[x.first,x.second]);
  assert.equal(x.first.group,x.group);assert.equal(x.second.group,x.group);
 }finally{x.close();}
});
test('empty isolated canvas returns a valid native miss and clears its semantic selection',()=>{
 const x=fixture();try{x.hit(null);const target=x.canvas.findTarget(x.event());assert.equal(target.target,undefined);assert.deepEqual(Array.from(target.subTargets),[]);
  x.canvas.active=null;x.down();assert.deepEqual(Array.from(x.c.groupIsolation.selectedObjects),[]);assert.equal(x.c.groupIsolation.selected,null);
 }finally{x.close();}
});
test('whole-group targeting outside isolation retains the exact ordinary native result',()=>{
 const x=fixture();try{x.c.groupIsolation.path=[];const target=x.canvas.findTarget(x.event());assert.equal(target.target,x.group);
  assert.deepEqual(target.subTargets,[x.second]);assert.equal(x.counts().stockCalls,1);assert.equal(x.counts().childCalls,0);
 }finally{x.close();}
});
test('Point Selection retains its existing target route and selected-point body handling',()=>{
 const x=fixture();try{x.c.state.tool='directSelect';const target=x.canvas.findTarget(x.event());assert.equal(target.target,x.group);
  assert.equal(x.counts().stockCalls,1);assert.equal(x.counts().childCalls,0);
 }finally{x.close();}
});
test('isolated PDF source detail stays off plotted marks while other status warnings and ordinary source badges remain',()=>{
 const x=fixture();try{
  Object.assign(x.first,{pdfSourceId:'source-pdf',pdfSourcePageNumber:1,
   importMeta:{mimeType:'application/pdf',importMode:'pdf-js-svg-vector',releasedForContentEditing:true}});
  Object.assign(x.c,{PDF_JS_SVG_VECTOR_IMPORT:'pdf-js-svg-vector',isDenseSvgProxyObject:()=>false,
   isAreaTextObject:()=>false,objectMayHaveStatusBadges:()=>true,
   appearanceInspectorStatus:()=>({sourceBacked:true}),appearanceInspectorFeatureSummary:()=>({featureTypes:['clip_path']})});
  for(const name of ['pdfDirectLeafSourceIdentity','objectStatusBadgeItems'])vm.runInContext(extract(source,name),x.c);
  const meta=x.first.importMeta;
  assert.deepEqual(Array.from(x.c.objectStatusBadgeItems(x.first),row=>row.kind),['clip']);
  assert.equal(x.first.importMeta,meta);assert.equal(x.first.pdfSourceId,'source-pdf');
  x.c.groupIsolation.path=[];
  assert.deepEqual(Array.from(x.c.objectStatusBadgeItems(x.first),row=>row.kind),['source','clip']);
 }finally{x.close();}
});
