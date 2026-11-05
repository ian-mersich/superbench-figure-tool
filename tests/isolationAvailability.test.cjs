'use strict';
// Actual selection functions and bundled Canvas/Group/Path/Textbox ownership.
// DOM/text measurement and unrelated UI callbacks use existing test adapters.
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const fabric=require('../vendor/fabric/index.min.js');
const dom=require('./helpers/pdfDenseCanvasRestoreDom.cjs');fabric.setEnv(dom.environment);
const {extract}=require('./helpers/pdfDenseCanvasRestoreSource.cjs');
const source=fs.readFileSync(require.resolve('../app/app.js'),'utf8');

function fixture(){
  const blocked=new fabric.Path('M 0 0 L 30 0 L 12 18 Z',{left:4,top:8,fill:'#ff8800'});blocked.figureId='blocked-path';
  const branch=new fabric.Group([blocked],{left:40,top:30,angle:17,flipX:true});branch.figureId='branch';
  const label=new fabric.Textbox('Editable label',{left:200,top:90,width:90,fontSize:14});label.figureId='label';
  const root=new fabric.Group([branch,label],{left:80,top:60,angle:-9});root.figureId='root';
  const canvas=new fabric.Canvas(dom.element(),{renderOnAddRemove:false});canvas.add(root);
  const layer={id:'artwork',name:'Artwork',visible:true,locked:false};
  let overlayClears=0;
  const noop=()=>{};
  const c=vm.createContext({canvas,fabricRef:fabric,state:{tool:'select'},
    groupIsolation:{path:[root],selected:null,selectedObjects:[],guardingSelection:false},
    pathNodeEdit:{object:null,objects:[]},nativePathBodyDrag:null,
    uniqueObjects:items=>[...new Set(items)],isActiveSelectionObject:o=>o instanceof fabric.ActiveSelection,
    isFigureObject:o=>o instanceof fabric.FabricObject,objectLayerId:()=>layer.id,objectLayerById:()=>layer,
    layerTreeObjectLabel:o=>o.figureId||o.type,inheritedMasterMeta:()=>null,isReferenceObject:o=>Boolean(o.reference),
    isEditablePdfPanel:()=>false,isDenseSvgProxyObject:()=>false,
    ensureIsolationObjectIdentity:o=>o,selectionOverlayRenderOnly:false,
    window:{queueMicrotask:noop},canvasUiDeliveryOwner:()=>({}),canvasUiDeliveryIsCurrent:()=>true,
    requestSelectionOverlayRender:noop,syncSelectionStatusOnly:noop,syncInspector:noop,scheduleSelectionUiSync:noop,
    revealEditableSvgSelectionInLayers:noop,showToast:noop,hideToast:noop,
    isCanvasTextObject:o=>o instanceof fabric.Textbox,allCanvasObjectsDeep:()=>[root,branch,blocked,label],
    closePdfPointScreenPreview:noop,pathNodeEditObjects:()=>c.pathNodeEdit.objects,
    isLineVectorObject:()=>false,clearPathNodeOverlay:()=>{overlayClears++;},syncPathActionButtons:noop,els:{},
  });
  for(const name of ['isGroupIsolationActive','activeIsolationGroup','isolationRootGroup','groupChildren',
    'objectIsWithinGroup','topLevelLayerObject','layerTreeAncestors','layerTreeSelectionUnavailableReason',
    'selectableIsolationChildren','isolatedSelectedObjects','selectedTopLevelObjects','selectIsolatedObjects',
    'toggleIsolatedObjectSelection','stopPathNodeEdit','reconcileGroupIsolationSelection','reconcileCanvasSelectionState']){
    vm.runInContext(extract(source,name),c);
  }
  canvas.on('selection:cleared',()=>c.reconcileGroupIsolationSelection());
  const objects=[root,branch,blocked,label],poses=objects.map(o=>o.calcTransformMatrix().slice());
  function preserved(){
    assert.deepEqual(root.getObjects(),[branch,label]);assert.deepEqual(branch.getObjects(),[blocked]);
    assert.equal(branch.group,root);assert.equal(label.group,root);assert.equal(blocked.group,branch);
    objects.forEach((o,index)=>assert.deepEqual(o.calcTransformMatrix(),poses[index]));
    assert.equal(label.text,'Editable label');assert.ok(label instanceof fabric.Textbox);
    assert.equal(blocked.fill,'#ff8800');assert.deepEqual(blocked.path,[['M',0,0],['L',30,0],['L',12,18],['Z']]);
    assert.deepEqual(Array.from(c.groupIsolation.path),[root]);assert.equal(c.groupIsolation.guardingSelection,false);
  }
  return {c,canvas,root,branch,blocked,label,layer,preserved,clears:()=>overlayClears,close:()=>canvas.destroy()};
}

for(const flag of ['locked','visible'])for(const ancestor of ['branch','root','layer']){
  test(`${flag} ${ancestor} retires unavailable native targets and point editing without moving artwork`,()=>{
    const x=fixture();try{
      x.c.selectIsolatedObjects([x.blocked]);x.c.pathNodeEdit={object:x.blocked,objects:[x.blocked]};
      x[ancestor][flag]=flag==='locked';
      assert.equal(x.c.reconcileCanvasSelectionState(),true);
      assert.deepEqual(Array.from(x.c.selectedTopLevelObjects()),[]);assert.equal(x.canvas.getActiveObject(),undefined);
      assert.equal(x.c.pathNodeEdit.object,null);assert.deepEqual(Array.from(x.c.pathNodeEdit.objects),[]);assert.equal(x.clears(),1);
      assert.deepEqual(Array.from(x.c.selectableIsolationChildren()),ancestor==='branch'?[x.label]:[]);
      x.preserved();
      x[ancestor][flag]=flag!=='locked';
      assert.equal(x.c.selectIsolatedObjects([x.blocked]),true);assert.deepEqual(Array.from(x.c.selectedTopLevelObjects()),[x.blocked]);
      x.preserved();
    }finally{x.close();}
  });
}

for(const flag of ['locked','visible'])test(`pruning a ${flag} branch retains its available editable label sibling`,()=>{
  const x=fixture();try{
    x.c.selectIsolatedObjects([x.label,x.blocked]);x.c.pathNodeEdit={object:x.blocked,objects:[x.blocked,x.label]};
    x.branch[flag]=flag==='locked';assert.equal(x.c.reconcileCanvasSelectionState(),true);
    assert.deepEqual(Array.from(x.c.selectedTopLevelObjects()),[x.label]);assert.equal(x.canvas.getActiveObject(),x.label);
    assert.equal(x.c.pathNodeEdit.object,null);x.preserved();
  }finally{x.close();}
});

test('both direct selection entry and modifier selection reject an unavailable ancestor',()=>{
  const x=fixture();try{
    x.branch.locked=true;
    assert.equal(x.c.selectIsolatedObjects([x.blocked]),false);
    assert.equal(x.c.toggleIsolatedObjectSelection(x.blocked),false);
    assert.deepEqual(Array.from(x.c.selectedTopLevelObjects()),[]);x.preserved();
  }finally{x.close();}
});

test('final isolated child toggles off and on without falling back to a stale native target',()=>{
  const x=fixture();try{
    x.c.selectIsolatedObjects([x.blocked]);assert.equal(x.c.toggleIsolatedObjectSelection(x.blocked),false);
    assert.deepEqual(Array.from(x.c.selectedTopLevelObjects()),[]);assert.equal(x.canvas.getActiveObject(),undefined);
    assert.equal(x.c.toggleIsolatedObjectSelection(x.blocked),true);
    assert.deepEqual(Array.from(x.c.selectedTopLevelObjects()),[x.blocked]);x.preserved();
  }finally{x.close();}
});

test('ordinary selection retains its native owner outside isolation',()=>{
  const x=fixture();try{
    x.c.groupIsolation.path=[];x.canvas.setActiveObject(x.root);
    assert.deepEqual(Array.from(x.c.selectedTopLevelObjects()),[x.root]);
  }finally{x.close();}
});

test('reselecting a restored nested owner supplies native controls before cursor lookup',()=>{
  const x=fixture();try{
    x.c.selectIsolatedObjects([x.branch]);delete x.branch.oCoords;
    x.c.selectIsolatedObjects([x.branch]);
    assert.doesNotThrow(()=>x.canvas._setCursorFromEvent({clientX:0,clientY:0},x.branch));
    assert.ok(x.branch.oCoords.tl);x.preserved();
  }finally{x.close();}
});

test('the actual isolated target finder prepares a restored inactive child before native hover',()=>{
  const x=fixture();try{
    x.c.selectIsolatedObjects([x.branch]);delete x.blocked.oCoords;
    Object.assign(x.c,{performance,transientCanvasTransform:null,recentCanvasHitTestPerformanceAudits:[],
      lastCanvasHitTestPerformanceAudit:null,retainCanvasPerformanceAudit:(_rows,value)=>value,
      isolationChildAtScenePoint:()=>x.blocked,canvasPoint:()=>new fabric.Point(0,0)});
    const begin=source.indexOf('    const fabricFindTarget = canvas.findTarget?.bind(canvas);');
    const end=source.indexOf('    const selectionEventCanvas = canvas;',begin);assert.ok(begin>0&&end>begin);
    vm.runInContext(source.slice(begin,end),x.c);
    const event={clientX:0,clientY:0,type:'mousemove'},found=x.canvas.findTarget(event);
    assert.equal(found.target,x.blocked);
    assert.doesNotThrow(()=>x.canvas._setCursorFromEvent(event,found.target));
    assert.ok(x.blocked.oCoords.tl);x.preserved();
  }finally{x.close();}
});
