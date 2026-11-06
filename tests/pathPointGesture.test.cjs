'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const fabric = require('../vendor/fabric/index.min.js');
const source = fs.readFileSync(require.resolve('../app/app.js'), 'utf8');

function actual(name, context) {
  const normal = source.indexOf(`  function ${name}(`);
  const start = normal < 0 ? source.indexOf(`  async function ${name}(`) : normal;
  const end = source.indexOf('\n  function ', start + 1);
  assert.ok(start > 0 && end > start, name);
  vm.runInContext(source.slice(start, end), context);
  return context[name];
}
function world(object) {
  const [a,b,c,d,e,f] = object.calcTransformMatrix(), offset = object.pathOffset;
  return object.path.flatMap((command,index) => {
    const points=[];
    for(let i=1;i+1<command.length;i+=2) {
      const x=command[i]-offset.x,y=command[i+1]-offset.y;
      points.push({key:`${index}:${i}`,x:a*x+c*y+e,y:b*x+d*y+f});
    }
    return points;
  });
}
function fixture(pose) {
  const path = new fabric.Path([['M',-0,10],['C',18,-14,42,-14,60,10],['C',78,34,104,34,122,10]],
    {left:80,top:90,fill:null,stroke:'#7851a9',strokeWidth:2,figureId:'curve',objectCaching:true});
  const neighbor = new fabric.Path('M 0 0 L 40 0 L 40 30 L 0 30 Z',
    {left:260,top:160,fill:'#123456',figureId:'neighbor'});
  const inner = new fabric.Group([path],{angle:23,flipX:true,scaleX:.91,scaleY:1.06,objectCaching:true});
  const outer = new fabric.Group([inner,neighbor],{angle:-13,scaleX:.87,scaleY:.93,objectCaching:true});
  path.set(pose);
  path.figureStudioBezierNodeMeta={schema:'figureStudio.bezierNodes.v1',nodes:[],retainedExtension:{value:17}};
  const objects = new Map([['curve',path],['neighbor',neighbor]]);
  const context=vm.createContext({fabricRef:fabric,pdfPointScreenPreview:null,pdfPointScreenPreparation:null,startPdfPointScreenGesture(){},objectForPathHandleRef:row=>objects.get(row.objectId)});
  actual('copyPathCommands',context);
  const translate=actual('translatePathGestureOperands',context);
  const entry={objectId:'curve',wholePath:false,path:path.path.map(c=>c.slice()),
    operands:[{commandIndex:1,xIndex:3,yIndex:4},{commandIndex:1,xIndex:5,yIndex:6},{commandIndex:2,xIndex:1,yIndex:2}],
    inverseSceneMatrix:fabric.util.invertTransform(path.calcTransformMatrix())};
  path.dirty=inner.dirty=outer.dirty=neighbor.dirty=false;
  return {path,neighbor,inner,outer,context,entry,translate};
}

for (const pose of [{angle:0},{angle:17,scaleX:1.21,scaleY:.83},{angle:-31,skewX:11,flipY:true}]) {
  test(`actual cubic operand translator follows one scene vector through nested transforms ${JSON.stringify(pose)}`,()=>{
    const {path,neighbor,inner,outer,entry,translate}=fixture(pose);
    const before=world(path),neighborBefore=JSON.stringify({path:neighbor.path,matrix:neighbor.calcTransformMatrix()}),snapshot=JSON.stringify(entry.path);
    const targetKeys=new Set(['1:3','1:5','2:1']),delta=[17.5066964285714,-12.9397321428571];
    translate([entry],...delta);
    const after=world(path);
    for(let i=0;i<before.length;i++) {
      const [dx,dy]=targetKeys.has(before[i].key)?delta:[0,0];
      assert.ok(Math.abs(after[i].x-before[i].x-dx)<1e-10,before[i].key+' x');
      assert.ok(Math.abs(after[i].y-before[i].y-dy)<1e-10,before[i].key+' y');
    }
    assert.equal(JSON.stringify(entry.path),snapshot,'snapshot is immutable');
    assert.equal(JSON.stringify({path:neighbor.path,matrix:neighbor.calcTransformMatrix()}),neighborBefore,'neighbor is unchanged');
    assert.equal(neighbor.dirty,false);
    assert.equal(path.dirty,true);assert.equal(inner.dirty,true);assert.equal(outer.dirty,true);
    translate([entry],...delta);
    assert.deepEqual(world(path),after,'repeated samples derive from the original snapshot');
  });
}

test('whole-path zero displacement retains raw signed operands and metadata',()=>{
  const {path,entry,translate}=fixture({angle:17,skewX:9});
  assert.equal(Object.is(entry.path[0][1],-0),true);
  const original=JSON.stringify(entry.path),metadata=path.figureStudioBezierNodeMeta;
  entry.wholePath=true;
  translate([entry],17,-9);translate([entry],0,0);
  assert.equal(JSON.stringify(path.path),original);
  assert.equal(Object.is(path.path[0][1],-0),true);
  assert.equal(path.figureStudioBezierNodeMeta,metadata);
});

test('Shift anchor drag keeps its off-center grab and constrains the scene displacement',()=>{
  const object={},descriptor={commandIndex:1,handleType:'endpoint'},samples=[];
  const start={x:73,y:91},pointerStart={x:76,y:89};
  const dragging={...descriptor,startPoint:start,pointerStartPoint:pointerStart,handles:[{...descriptor,objectId:'path'}],translations:[]};
  const context=vm.createContext({
    pdfPointScreenPreparation:null,startPdfPointScreenGesture(){},
    artboardToolInteraction:null,zoomToolInteraction:null,
    smartConnectorInteraction:{endpoint:null,bend:null},strokeWidthEdit:{},appearancePatternEdit:{},appearanceGradientEdit:{},pdfGradientEdit:{},nativePathEdit:{},
    pathNodeEdit:{object,dragging},canvas:{getScenePoint:e=>e.point,requestRenderAll(){}},
    objectForPathHandleRef:()=>object,pathHandleDescriptors:()=>[descriptor],samePathHandle:(a,b)=>a.commandIndex===b.commandIndex&&a.handleType===b.handleType,
    directSelectionObjects:()=>[object],
    pathNodeEditObjects:()=>[object],snapWorkspacePoint:p=>p,snappingBypassed:()=>true,isLineVectorObject:()=>false,
    isOrdinaryVectorEnginePathPreviewCandidate:()=>false,translatePathGestureOperands:(_entries,dx,dy)=>samples.push([dx,dy]),
    deferPdfPointNodeOverlay:()=>false,renderPathNodeOverlay(){},requestPdfPointArtworkRender(){}
  });
  actual('constrainStraightLineDragPoint',context);
  const move=actual('onPathNodePointerMove',context);
  move({point:{x:pointerStart.x+37,y:pointerStart.y+19},shiftKey:true,preventDefault(){}});
  const expected=Math.sqrt((37*37+19*19)/2);
  assert.ok(Math.abs(samples[0][0]-expected)<1e-12);
  assert.ok(Math.abs(samples[0][1]-expected)<1e-12);
  move({point:pointerStart,shiftKey:true,preventDefault(){}});
  assert.deepEqual(samples[1],[0,0],'returning to the grabbed point restores zero displacement');
});

test('quadratic anchors carry their shared control once and retain other contours through native transforms',()=>{
  const path=new fabric.Path([
    ['M',0,0],['Q',25,-20,50,0],['Q',75,20,100,0],
    ['M',150,0],['Q',175,-20,200,0],['Q',175,30,150,0],['Z']
  ],{angle:17,skewX:9,flipX:true,figureId:'quadratic',fill:null});
  const parent=new fabric.Group([path],{angle:-13,scaleX:1.2,scaleY:.8});
  const context=vm.createContext({fabricRef:fabric,isEditablePathObject:()=>true,isLineVectorObject:()=>false,
    pathNodeEditObjects:()=>[path],pathEditObjectId:o=>o.figureId,pathObjectSceneMatrix:o=>o.calcTransformMatrix(),
    qualifyPathHandle:(o,d)=>({...d,objectId:o.figureId}),objectForPathHandleRef:()=>path});
  context.captureDirectSelectionTextPositions=()=>[];
  for(const name of ['copyPathCommands','roundPathCoord','pathEndpointIndices','pathCommandEndpoint','pathPointsCoincide','pathContourDescriptors',
    'pathContourForCommand','pathNodeDescriptors','previousPathEndpointDescriptor','pathControlDescriptor','pathHandleDescriptors',
    'controlNodeDescriptor','samePathHandle','pathBodyDragTranslations','translatePathGestureOperands'])actual(name,context);
  const raw=path.path.map(c=>c.slice()),matrix=path.calcTransformMatrix().slice();
  const cases=[
    {anchors:[1],keys:['1:1','1:3','2:1']},
    {anchors:[0,1],keys:['0:1','1:1','1:3','2:1']},
    {anchors:[3],keys:['3:1','4:1','5:1','5:3']}
  ];
  for(const {anchors,keys} of cases){
    path.path=raw.map(c=>c.slice());
    const before=world(path),selected=anchors.map(commandIndex=>({objectId:'quadratic',commandIndex,handleType:'endpoint'}));
    const translations=context.pathBodyDragTranslations(selected),operands=translations[0].operands;
    assert.equal(new Set(operands.map(o=>`${o.commandIndex}:${o.xIndex}`)).size,operands.length,'shared Q control is not duplicated');
    assert.deepEqual(Array.from(operands,o=>`${o.commandIndex}:${o.xIndex}`).sort(),keys.slice().sort());
    context.translatePathGestureOperands(translations,17,-9);
    const after=world(path);
    before.forEach((p,i)=>{
      assert.ok(Math.abs(after[i].x-p.x-(keys.includes(p.key)?17:0))<1e-10,p.key+' x');
      assert.ok(Math.abs(after[i].y-p.y-(keys.includes(p.key)?-9:0))<1e-10,p.key+' y');
    });
    assert.deepEqual(path.calcTransformMatrix(),matrix);
    assert.equal(path.group,parent);
  }
});

for(const curve of [['Q',31,-28,80,10],['C',17,-24,62,35,80,10]]){
  test(`segment ${curve[0]} material point follows scene displacement without cumulative rounding`,()=>{
    const path=new fabric.Path([['M',-0,10],curve,['L',120,20]],{angle:23,skewX:11,flipY:true});
    new fabric.Group([path],{angle:-17,scaleX:.87,scaleY:1.13});
    const raw=path.path.map(c=>c.slice()),context=vm.createContext({fabricRef:fabric});
    actual('copyPathCommands',context);
    const reshape=actual('pathSegmentDragCommands',context);
    const point=t=>{
      const command=path.path[1],u=1-t,p0=path.path[0].slice(1),p1=command.slice(1,3);
      const p2=command.slice(3,5),p3=command.slice(5,7);
      const native=curve[0]==='Q'
        ? p0.map((v,i)=>u*u*v+2*u*t*p1[i]+t*t*p2[i])
        : p0.map((v,i)=>u*u*u*v+3*u*u*t*p1[i]+3*u*t*t*p2[i]+t*t*t*p3[i]);
      const m=path.calcTransformMatrix(),x=native[0]-path.pathOffset.x,y=native[1]-path.pathOffset.y;
      return [m[0]*x+m[2]*y+m[4],m[1]*x+m[3]*y+m[5]];
    };
    for(const t of [.03,.2,5.5/12,.8,.97]){
      path.path=raw.map(c=>c.slice());
      const initial=point(t),drag={pathSnapshot:raw,segment:{endCommandIndex:1},t,inverseSceneMatrix:fabric.util.invertTransform(path.calcTransformMatrix())};
      for(const delta of [[.3,-.2],[17.123456,-9.876543],[-4,8],[17.123456,-9.876543]]){
        path.path=reshape(drag,...delta);
        const current=point(t);
        current.forEach((v,i)=>assert.ok(Math.abs(v-initial[i]-delta[i])<1e-10,`${t} coordinate ${i}`));
        assert.deepEqual(Array.from(path.path[0]),raw[0]);assert.deepEqual(Array.from(path.path[2]),raw[2]);
        assert.deepEqual(Array.from(path.path[1]).slice(-2),raw[1].slice(-2));
      }
      path.path=reshape(drag,0,0);
      assert.equal(JSON.stringify(path.path),JSON.stringify(raw));
      assert.equal(Object.is(path.path[0][1],-0),true);
      assert.deepEqual(point(t),initial);
    }
    assert.deepEqual(raw,[['M',-0,10],curve,['L',120,20]],'the gesture snapshot remains exact');
  });
}

test('segment Escape restores raw legacy metadata, prior selection and dirty ancestors',()=>{
  const parent={dirty:false},object={path:[['M',7,9]],group:parent,set(values){Object.assign(this,values);},setCoords(){}};
  const metadata={schema:'figureStudio.bezierNodes.v1',nodes:[],extension:{keep:true}},selected={commandIndex:0,handleType:'endpoint'};
  const drag={pathSnapshot:[['M',-0,10],['Q',20,-15,40,10]],bezierNodeMeta:metadata,selectedBefore:selected,selectionBefore:[selected],selectedSegmentBefore:{endCommandIndex:1}};
  const context=vm.createContext({pathNodeEdit:{segmentDrag:drag},objectForPathHandleRef:()=>object,
    cloneManifestValue:v=>JSON.parse(JSON.stringify(v)),resetPaintedVectorDirectSelectionCycle(){},els:{pathNodeOverlay:{}},
    renderPathNodeOverlay(){},renderIsolationSelectionOverlay(){},ensureDirectSelectionCanvasCollection(){},canvas:{requestRenderAll(){}},syncInspector(){},updatePathNodeStatus(){}});
  actual('copyPathCommands',context);actual('requestCanvasArtworkRender',context);actual('cancelPathSegmentDrag',context)({preventDefault(){}});
  assert.equal(context.pathNodeEdit.segmentDrag,null);assert.deepEqual(object.figureStudioBezierNodeMeta,metadata);
  assert.deepEqual(Array.from(object.path,c=>Array.from(c)),drag.pathSnapshot);assert.equal(Object.is(object.path[0][1],-0),true);
  assert.deepEqual(context.pathNodeEdit.selectedHandles,[selected]);assert.equal(context.pathNodeEdit.selected,selected);
  assert.equal(context.pathNodeEdit.selectedSegment,drag.selectedSegmentBefore);assert.equal(parent.dirty,true);
});

test('zero-return segment release does not record geometry or history',()=>{
  let paints=0;
  const context=vm.createContext({pathNodeEdit:{segmentDrag:{dirty:false}},objectForPathHandleRef:()=>({}),
    resetPaintedVectorDirectSelectionCycle(){},els:{pathNodeOverlay:{}},renderPathNodeOverlay(){paints++;},
    recordPathGeometryEdit(){throw Error('No-op must not record an edit');},commitHistory(){throw Error('No-op must not create history');}});
  actual('finishPathSegmentDrag',context)({preventDefault(){}});
  assert.equal(context.pathNodeEdit.segmentDrag,null);assert.equal(paints,1);
});

test('stationary modifier click removes the final selected point while retaining its editable owner and labels',()=>{
  const point={objectId:'path',commandIndex:0,handleType:'endpoint'};
  const path={figureId:'path',path:[['M',0,0],['L',20,10]]},label={figureId:'label',text:'Editable label'};
  const context=vm.createContext({pdfPointScreenPreview:null,pathNodeEdit:{object:path,objects:[path,label],selected:point,selectedHandles:[point]},
    samePathHandle:(a,b)=>a.objectId===b.objectId&&a.commandIndex===b.commandIndex&&a.handleType===b.handleType,
    renderPathNodeOverlay(){},updatePathNodeStatus(){},syncInspector(){},
    commitHistory(){throw Error('Selection alone cannot commit history');},recordPathGeometryEdit(){throw Error('Selection cannot write geometry');}});
  actual('finishPathHandleDrag',context)({dirty:false,body:false,selectionModifier:true,currentHandleSelected:true,
    objectId:'path',commandIndex:0,handleType:'endpoint',selectionBefore:[point],pathSnapshots:[],lineSnapshots:[],textSnapshots:[]});
  assert.deepEqual(Array.from(context.pathNodeEdit.selectedHandles),[]);assert.equal(context.pathNodeEdit.selected,null);
  assert.deepEqual(context.pathNodeEdit.objects,[path,label]);assert.equal(context.pathNodeEdit.object,path);
  assert.deepEqual(path.path,[['M',0,0],['L',20,10]]);assert.equal(label.text,'Editable label');
});

for(const kind of ['point','segment'])for(const cooperative of [false,true]){
  test(`completed ${kind} release queues its settled artwork before ${cooperative?'cooperative PDF':'ordinary'} history`,async()=>{
    const trace=[];let frame='last-pointer-preview',queued=null,historyCalls=0;
    const old=[['M',0,0],['L',10,10]],object={figureId:'curve',path:[['M',0,0],['L',10,20]],setCoords(){trace.push('coords');}};
    const handle={objectId:'curve',commandIndex:1,handleType:'endpoint'};
    const context=vm.createContext({pdfPointScreenPreview:null,selectionOverlayRenderOnly:true,suppressNextFullCanvasRender:true,
      closePdfPointScreenPreview(){trace.push('close-screen-preview');},
      pathNodeEdit:{object,segmentDrag:kind==='segment'?{dirty:true,pointerId:7,segment:{endCommandIndex:1}}:null},
      objectForPathHandleRef:()=>object,resetPaintedVectorDirectSelectionCycle(){},els:{pathNodeOverlay:{releasePointerCapture(){}}},
      tryRouteOrdinaryPathOperandEdit:()=>false,pdfSourceIdForObject:()=>cooperative?'source':'',isLineVectorObject:()=>false,
      setPathCommandsWithSceneStableFrame(){frame='settled-canonical-frame';trace.push('settle');},
      recordPathGeometryEdit(){trace.push('record');},syncInspector(){context.selectionOverlayRenderOnly=true;context.suppressNextFullCanvasRender=true;trace.push('inspector');},
      pdfIncrementalHistoryOptions:()=>cooperative?{incrementalObjects:[object]}:{},renderPathNodeOverlay(){trace.push('overlay');},updatePathNodeStatus(){},
      canvas:{requestRenderAll(){
        assert.equal(context.selectionOverlayRenderOnly,false,'artwork intent must bypass selection-only optimization');
        assert.equal(context.suppressNextFullCanvasRender,false,'artwork intent must clear the one-shot suppression');
        queued=frame;trace.push('queue-artwork');
      }},commitHistory(){publish();},commitPdfPointHistory(){publish();return Promise.resolve();}});
    function publish(){historyCalls++;trace.push('history');assert.equal(queued,'settled-canonical-frame','the committed frame must already have an artwork publication request');}
    actual('requestCanvasArtworkRender',context);
    if(kind==='point')actual('finishPathHandleDrag',context)({dirty:true,...handle,handles:[handle],pathSnapshots:[{objectId:'curve',path:old}]});
    else actual('finishPathSegmentDrag',context)({preventDefault(){}});
    await Promise.resolve();
    assert.equal(historyCalls,1);assert.equal(trace.filter(x=>x==='queue-artwork').length,1);
    assert.ok(trace.indexOf('settle')<trace.indexOf('inspector')&&trace.indexOf('inspector')<trace.indexOf('queue-artwork')&&trace.indexOf('queue-artwork')<trace.indexOf('history'));
  });
}

test('segment pointer routing retains the grab, permits cross-axis snapping and restores an exact return',()=>{
  const raw=[['M',-0,0],['Q',10,10,20,0]],parent={dirty:false};
  const object={path:raw.map(c=>c.slice()),group:parent,set(v){Object.assign(this,v);},setCoords(){}};
  const drag={pathSnapshot:raw,segment:{endCommandIndex:1},t:.5,inverseSceneMatrix:[1,0,0,1,0,0],
    startCanvasPoint:{x:10,y:5},pointerStartPoint:{x:12,y:7},dirty:false};
  const context=vm.createContext({pathNodeEdit:{segmentDrag:drag},objectForPathHandleRef:()=>object,
    canvas:{getScenePoint:e=>e.point,requestRenderAll(){}},snapWorkspacePoint:()=>({x:12,y:18}),
    snappingBypassed:()=>false,renderPathNodeOverlay(){}});
  for(const name of ['copyPathCommands','pathSegmentDragCommands','updatePathSegmentDrag'])actual(name,context);
  context.updatePathSegmentDrag({point:{x:12,y:20},preventDefault(){}});
  assert.deepEqual(Array.from(object.path[1]),['Q',14,36,20,0],'a vertical pointer can still snap across its other scene axis');
  assert.equal(drag.dirty,true);assert.equal(parent.dirty,true);
  context.updatePathSegmentDrag({point:drag.pointerStartPoint,preventDefault(){}});
  assert.equal(drag.dirty,false);assert.equal(JSON.stringify(object.path),JSON.stringify(raw));
  assert.equal(Object.is(object.path[0][1],-0),true);
});

for(const alreadyEdited of [false,true])for(const hasLabels of [false,true])for(const metadataKind of ['absent','null','object']){
  test(`actual segment begin/Escape restores source and paints prior selection (already edited: ${alreadyEdited}, labels: ${hasLabels}, metadata: ${metadataKind})`,()=>{
    const a={figureId:'a'},b={figureId:'b',path:[['M',0,0],['Q',20,-10,40,0]],
      set(v){Object.assign(this,v);if(Object.hasOwn(v,'figureStudioBezierNodeMeta')&&v.figureStudioBezierNodeMeta===undefined)this.figureStudioBezierNodeMeta=null;},setCoords(){},calcTransformMatrix:()=>[1,0,0,1,0,0]};
    if(metadataKind==='null')b.figureStudioBezierNodeMeta=null;
    if(metadataKind==='object')b.figureStudioBezierNodeMeta={schema:'figureStudio.bezierNodes.v1',nodes:[],extension:{keep:true}};
    const metadataBefore=structuredClone(b.figureStudioBezierNodeMeta);
    const label={figureId:'label',type:'textbox',text:'Editable label',left:11.25,top:-7.5,pdfTextSource:{schema:'retained-source',glyphs:[{unicode:'E'}]}};
    const labelBefore=structuredClone(label);
    const selected={objectId:'a',commandIndex:0,handleType:'endpoint'},priorObjects=alreadyEdited?[a,b]:[a];
    if(hasLabels)priorObjects.push(label);
    let canvasSelection=priorObjects.slice();
    let focused=0,paints=0,paintedPath;
    const context=vm.createContext({fabricRef:fabric,pathNodeEdit:{object:a,objects:priorObjects,selected,selectedHandles:[selected],selectedSegment:null},
      densePdfApi:()=>null,resetPaintedVectorDirectSelectionCycle(){},els:{viewport:{focus(){focused++;}},pathNodeOverlay:{}},
      selectionOverlayRenderOnly:false,suppressNextFullCanvasRender:false,
      canvas:{getScenePoint:()=>({x:21,y:4}),discardActiveObject(){},requestRenderAll(){if(context.selectionOverlayRenderOnly||context.suppressNextFullCanvasRender)return;paints++;paintedPath=structuredClone(b.path);}},closestSegmentT:()=>.5,
      pathLocalPointToCanvas:(_o,p)=>p,segmentPointAt:()=>({x:20,y:-5}),pathObjectSceneMatrix:o=>o.calcTransformMatrix(),
      qualifyPathSegment:(_o,s)=>s,pathEditObjectId:o=>o.figureId,cloneManifestValue:v=>v==null?null:JSON.parse(JSON.stringify(v)),
      objectForPathHandleRef:()=>b,syncInspector(){},updatePathNodeStatus(){},renderPathNodeOverlay(){context.selectionOverlayRenderOnly=true;context.suppressNextFullCanvasRender=true;},renderIsolationSelectionOverlay(){}});
    context.pathNodeEditObjects=()=>context.pathNodeEdit.objects.filter(object=>object!==label);
    context.directSelectionObjects=()=>context.pathNodeEdit.objects;
    context.ensureDirectSelectionCanvasCollection=()=>{canvasSelection=Array.from(context.pathNodeEdit.objects);};
    context.selectedPathHandleRefs=()=>context.pathNodeEdit.selectedHandles;
    for(const name of ['cloneManifestValue','copyPathCommands','requestCanvasArtworkRender','beginPathSegmentDrag','cancelPathSegmentDrag'])actual(name,context);
    context.beginPathSegmentDrag({preventDefault(){},stopPropagation(){},currentTarget:{},pointerId:7},b,{endCommandIndex:1,type:'Q'});
    assert.equal(focused,1);assert.equal(context.pathNodeEdit.object,b);
    assert.ok(context.pathNodeEdit.objects.includes(b));
    assert.ok(!context.pathNodeEdit.objects.includes(label),'starting a segment reshape selects paths rather than moving text');
    b.path[1][1]+=17;
    context.cancelPathSegmentDrag({preventDefault(){},pointerId:7});
    assert.equal(context.pathNodeEdit.object,a);
    assert.deepEqual(Array.from(context.pathNodeEdit.objects),priorObjects);
    assert.deepEqual(canvasSelection,priorObjects,'Escape restores the complete prior canvas collection including labels');
    assert.deepEqual(Array.from(context.pathNodeEdit.selectedHandles,x=>({...x})),[selected]);
    assert.deepEqual({...context.pathNodeEdit.selected},selected);
    assert.equal(b.path[1][1],20);
    assert.equal(paints,1,'cancellation bypasses overlay-only suppression to repaint the restored native path');
    assert.deepEqual(paintedPath,[['M',0,0],['Q',20,-10,40,0]]);
    assert.equal(Object.hasOwn(b,'figureStudioBezierNodeMeta'),metadataKind!=='absent','absence and explicit null must remain distinct');
    assert.deepEqual(structuredClone(b.figureStudioBezierNodeMeta),metadataBefore);
    assert.deepEqual(label,labelBefore,'segment editing and cancellation preserve label text, source and exact pose');
  });
}

test('cancel restores complete legacy node metadata and raw path operands without normalizing them',()=>{
  const {path,entry,context}=fixture({angle:17});
  const metadata=JSON.parse(JSON.stringify(path.figureStudioBezierNodeMeta));
  path.path=[['M',10,20],['L',30,40]];
  path.figureStudioBezierNodeMeta={schema:'figureStudio.bezierNodes.v2',nodes:[]};
  let renders=0;
  Object.assign(context,{cloneManifestValue:(value,fallback)=>value==null?fallback:JSON.parse(JSON.stringify(value)),
    resetPaintedVectorDirectSelectionCycle(){},els:{pathNodeOverlay:{}},hideGuideSnapCue(){},hideSmartGuideCues(){},
    closePdfPointScreenPreview(){},renderPathNodeOverlay(){},updatePathNodeStatus(){},pathNodeEdit:{object:path},canvas:{requestRenderAll(){renders++;}},syncInspector(){}});
  const restore=actual('restorePathHandleDrag',context);
  restore({pathSnapshots:[{objectId:'curve',path:entry.path,bezierNodeMeta:metadata}]});
  assert.deepEqual(path.figureStudioBezierNodeMeta,metadata);
  assert.equal(JSON.stringify(path.path),JSON.stringify(entry.path));
  assert.equal(Object.is(path.path[0][1],-0),true);
  assert.equal(renders,1,'the restored artwork requests its normal paint');
});

test('Direct Selection leaves native point gestures in control instead of constructing a bitmap transform preview',()=>{
  const context=vm.createContext({canvas:{},state:{tool:'directSelect'},lastTransientCanvasAudit:null,
    transientTransformHasLiveDependents(){throw new Error('Point editing must not enter whole-object preview setup');}});
  const begin=actual('beginTransientCanvasTransform',context);
  begin({figureId:'nested-group'},{action:'drag'});
  assert.equal(context.lastTransientCanvasAudit.reason,'point-editing');
  assert.equal(context.lastTransientCanvasAudit.activated,false);
});

test('the App admits only native or its issued inactive uniform-stroke painter',()=>{
  const issued=new WeakMap(),native=()=>{},context=vm.createContext({fabricRef:{Path:{prototype:{_render:native}}},issuedUniformPathRenderers:issued,
    isSmartConnectorObject:o=>o.smart,isLineVectorObject:o=>o.line,variableStrokeProfileActive:o=>o.variable});
  const eligible=actual('isNativeUniformPathPaint',context),object={_render:native};
  assert.equal(eligible(object),true);
  const wrapper=()=>{};object._render=wrapper;assert.equal(eligible(object),false);
  issued.set(object,wrapper);assert.equal(eligible(object),true);
  for(const key of ['smart','line','variable']){object[key]=true;assert.equal(eligible(object),false,key);delete object[key];}
  object._render=()=>{};assert.equal(eligible(object),false,'an attached flag cannot admit a replacement custom painter');
});

test('a retained point release delegates settlement to the pinned transaction before mutating its native frame',async()=>{
  let prepare,resolve;const path=[['M',1,2]],dragging={dirty:true},context=vm.createContext({
    pdfPointScreenPreview:{active:true,controller:{diagnostics:()=>({frames:120})}},
    commitPdfPointHistory(label,options,paint,callback){assert.equal(label,'Path edit');assert.equal(paint,null);prepare=callback;return new Promise(done=>{resolve=done;});},
    closePdfPointScreenPreview(){throw Error('settlement must wait for the pinned transaction');},console,showLongToast(){}});
  const finish=actual('finishPathHandleDrag',context),pending=finish(dragging);
  assert.equal(typeof prepare,'function');assert.equal(dragging.dirty,true);assert.deepEqual(path,[['M',1,2]]);
  resolve();await pending;
});

for(const mode of ['success','reject','restore-reject','owner-changed','owner-at-yield','yield-reject','prepare-success','prepare-reject','prepare-noop','prepare-owner-at-yield']) {
  test('cooperative point history preserves a published recovery authority: '+mode,async()=>{
    const tab={payload:{project:{title:'Prior figure'}}},owner={},calls=[],prior={fabric:{objects:[{figureId:'marker',path:[['M',1,2]]}]},import:{mode:'editable'}};
    let depth=0,resume,rejectYield,secondStarted;
    const secondYield=new Promise(resolve=>{secondStarted=resolve;});
    const context=vm.createContext({canvas:owner,activeDocumentTab:()=>tab,currentTransformDocumentId:()=> 'document-1',
      undoStack:['published-head'],redoStack:[],historySelectionState:new Map([['published-head',['marker']]]),historyDirectSelectionState:new Map(),historyUndoDirectSelectionState:new Map(),
      projectRevision:7,artifactStore:new Map(),missingExternalArtifactRefsById:new Map(),state:{view:{zoom:2},ui:{rail:'style'}},documentDirty:false,documentSaveStateLabel:'Saved',isApplyingHistory:false,
      documentRuntimeRestoreFailed:false,latestHistoryStateCache:{stateObject:'old'},captureVectorEngineHistoryState:()=>({revision:7,undoStack:['published-head'],redoStack:[]}),
      selectedTopLevelObjects:()=>[{figureId:'marker'}],captureDirectSelectionHistoryState:()=>({primaryObjectId:'marker'}),captureGroupIsolationHistoryState:()=>({pathIds:['group']}),
      cloneDocumentTabValue:(v)=>v==null?null:JSON.parse(JSON.stringify(v)),pinPdfHistorySnapshots:()=>()=>calls.push('release'),
      lockPdfHistoryMutations:()=>{depth++;return()=>{depth--;calls.push('unlock');}},
      yieldPdfHistoryToUi:()=>{assert.equal(depth,1);calls.push('yield');const wait=new Promise((resolve,reject)=>{resume=resolve;rejectYield=reject;});if(calls.filter(v=>v==='yield').length===2)secondStarted();return wait;},
      commitPdfHistory:async(label,options,paint)=>{assert.equal(depth,1);calls.push('commit');if(mode==='prepare-success'){assert.equal(label,'Prepared point');assert.equal(options.prepared,true);assert.equal(paint,screenPaint);}if(mode==='owner-changed')context.canvas={};if(!['success','prepare-success'].includes(mode))throw new Error('injected serializer rejection');},
      restoreVectorEngineHistoryState:()=>calls.push('restore-history'),restoreHistorySnapshot:async(snapshot)=>{assert.equal(depth,1);assert.equal(snapshot,'published-head');calls.push('restore-scene');if(mode==='restore-reject')throw new Error('injected restore rejection');},
      syncDocumentSaveState:()=>calls.push('save-state'),console:{error(){}},
      fileFormatApi:()=>({hydrateSharedGroupImportMetadata:v=>v}),pdfHistoryNodeStore:{parse:()=>JSON.parse(JSON.stringify(prior))},
      hydrateArtifactRefPlaceholders(){},normalizedProjectFromPayload:p=>p.project,buildProjectPayload:p=>({project:p})});
    actual('retainPublishedPdfHistoryRecovery',context);
    const commit=actual('commitPdfPointHistory',context);
    const screenPaint=Promise.resolve({passed:true});
    const prepare=mode.startsWith('prepare-')?async()=>{
      assert.equal(depth,1);calls.push('prepare');
      if(mode==='prepare-reject')throw new Error('injected settlement rejection');
      return mode==='prepare-noop'?null:{label:'Prepared point',options:{prepared:true},screenPaint};
    }:null;
    const pending=commit('Point edit',{},null,prepare);
    assert.equal(calls.includes('commit'),false,'history capture must not start before the UI task yield');assert.equal(depth,1);
    if(mode==='owner-at-yield')context.canvas={};
    if(mode==='yield-reject')rejectYield(new Error('injected UI yield rejection'));else resume();
    if(['prepare-success','prepare-owner-at-yield'].includes(mode)){
      await secondYield;
      assert.equal(calls.filter(v=>v==='yield').length,2,'settlement must yield again before capture');
      assert.equal(calls.includes('commit'),false);
      if(mode==='prepare-owner-at-yield')context.canvas={};resume();
    }
    if(['success','prepare-success','prepare-noop'].includes(mode))await pending;
    else await assert.rejects(pending,mode==='owner-at-yield'?/document changed before/:mode==='prepare-owner-at-yield'?/document changed while/:mode==='prepare-reject'?/injected settlement rejection/:mode==='yield-reject'?/injected UI yield rejection/:/injected serializer rejection/);
    if(mode==='prepare-noop')assert.equal(calls.includes('commit'),false);
    assert.equal(depth,0);assert.equal(context.isApplyingHistory,false);
    assert.deepEqual(calls.slice(-2),['release','unlock']);
    assert.equal(calls.includes('restore-scene'),mode==='reject'||mode==='restore-reject'||mode==='yield-reject'||mode==='prepare-reject');
    assert.equal(context.documentRuntimeRestoreFailed,mode==='restore-reject');
    if(mode==='restore-reject') {
      assert.equal(JSON.stringify(tab.payload.project.fabric),JSON.stringify(prior.fabric));
      assert.equal(tab.projectRevision,7);assert.equal(tab.dirty,false);assert.equal(tab.undoStack[0],'published-head');
      assert.equal(context.latestHistoryStateCache.stateObject,null);
    }
  });
}

for(const headOnlyControl of [false,true]) {
  test('actual pooled history remains reachable after publication and collection reject'+(headOnlyControl?' (head-only negative control)':''),async()=>{
    const {Store}=require('../app/pdf-history-node-store.js'),store=new Store();
    const states=[0,1,2,3].map(n=>({fabric:{objects:[{type:'Path',figureId:'marker',nativePdfSourceObjectId:'pdf-source',
      path:[['M',n,2],['C',3,4,5,6,7,8]],sourcePayload:String(n).repeat(800)}]}}));
    const snapshots=states.map(s=>store.compact(JSON.stringify(s)).snapshot);
    const tab={undoStack:snapshots.slice(0,2),redoStack:[snapshots[2]]},owner={};
    let depth=0,collections=0;
    const context=vm.createContext({canvas:owner,activeDocumentTab:()=>tab,currentTransformDocumentId:()=> 'document-1',
      undoStack:[...tab.undoStack],redoStack:[...tab.redoStack],historySelectionState:new Map(snapshots.slice(0,3).map(s=>[s,['marker']])),
      historyDirectSelectionState:new Map(),historyUndoDirectSelectionState:new Map(),projectRevision:7,historyPrunedCount:0,lastHistoryPruneReason:'',lastHistoryPrunedAt:'',
      largestHistorySnapshotBytes:0,lastHistorySnapshotBytes:0,largestRawHistorySnapshotBytes:0,lastRawHistorySnapshotBytes:0,historyArtifactDedupAppliedCount:0,
      state:{view:{},ui:{}},documentDirty:false,documentSaveStateLabel:'Saved',isApplyingHistory:false,documentRuntimeRestoreFailed:false,
      selectedTopLevelObjects:()=>[{figureId:'marker'}],captureDirectSelectionHistoryState:()=>null,captureGroupIsolationHistoryState:()=>null,
      cloneDocumentTabValue:v=>JSON.parse(JSON.stringify(v)),pdfHistoryNodeStore:store,lockPdfHistoryMutations:()=>{depth++;return()=>depth--;},
      yieldPdfHistoryToUi:async()=>{assert.equal(depth,1);assert.equal(store.measure(snapshots.slice(0,3)).pinCount,1);},
      syncHistoryButtons(){},syncDocumentSaveState(){},mountOptions:{history:{maxUndoSteps:1,maxUndoApproxBytes:1e6}},
      documentWorkspaceState:{switching:false},allDocumentTabs:()=>[tab],densePdfApi:()=>null,browserDenseAssetReferences:()=>new Map(),
      denseFigureHandoffContext:()=>null,approxSerializedBytes:s=>Buffer.byteLength(s),emitProjectChanged(){throw Error('Must fail during collection first');},console});
    for(const name of ['captureVectorEngineHistoryState','restoreVectorEngineHistoryState','pinPdfHistorySnapshots','collectPdfHistoryNodes',
      'historyStackApproxBytes','noteHistoryPrune','planHistoryStackPrune','pruneHistoryStack','pruneHistoryStacks','commitSerializedHistory'])actual(name,context);
    const collect=store.collect.bind(store);
    store.collect=(roots)=>{collections++;const result=collect(roots);assert.equal(result.pinCount,1);throw Error('injected after actual collection');};
    context.commitPdfHistory=async()=>{
      assert.equal(depth,1);
      const serialized=await store.compactImmutableAsync(states[3]);
      context.commitSerializedHistory('Point edit',{},serialized);
    };
    context.restoreHistorySnapshot=async snapshot=>{
      assert.equal(depth,1);assert.deepEqual(store.parse(snapshot),states[1]);
    };
    const commit=actual('commitPdfPointHistory',context);
    if(headOnlyControl)context.pinPdfHistorySnapshots=()=>store.pin([snapshots[1]]);
    await assert.rejects(commit('Point edit',{}),/injected after actual collection/);
    assert.equal(collections,1);assert.equal(depth,0);
    assert.deepEqual(Array.from(context.undoStack),snapshots.slice(0,2));
    assert.deepEqual(Array.from(context.redoStack),[snapshots[2]]);
    assert.equal(context.projectRevision,7);assert.equal(context.historyPrunedCount,0);
    assert.equal(context.historySelectionState.size,3);
    assert.equal(store.measure([snapshots[1]]).pinCount,0,'release the temporary pin');
    for(const i of [0,1,2]) {
      if(headOnlyControl&&i!==1)assert.throws(()=>store.parse(snapshots[i]),/unavailable/,'negative control must expose collected old Undo/Redo nodes');
      else assert.deepEqual(store.parse(snapshots[i]),states[i],'complete prior Undo/Redo state remains usable');
    }
  });
}
