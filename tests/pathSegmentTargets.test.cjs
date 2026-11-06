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
  return context[name];
}

function fixture(cssLength, zoom) {
  const path = new fabric.Path('M0 0 L100 0 L100 80 L0 80 Z M30 20 L70 20 L70 60 L30 60 Z',
    {figureId:'compound-1',fillRule:'evenodd'});
  const inner = new fabric.Group([path], {angle:23,flipX:true,scaleX:1.13,scaleY:.91});
  new fabric.Group([inner], {angle:-13,scaleX:1.18,scaleY:.87});
  const matrix = path.calcTransformMatrix();
  const height = cssLength/(zoom*Math.hypot(matrix[2],matrix[3]));
  // Independent second-contour closing edge with its real native affine chain.
  const segment = {type:'Z',endCommandIndex:9,contourIndex:1,
    start:{x:30,y:20+height},end:{x:30,y:20}};
  const hits = [];
  const context = vm.createContext({state:{view:{zoom}},pathNodeEdit:{selectedSegment:null},
    densePdfApi:()=>null,pathEditObjectId:o=>o.figureId,
    pathSegmentDescriptors:()=>[segment],
    segmentPointAt:(s,t)=>({x:s.start.x+(s.end.x-s.start.x)*t,y:s.start.y+(s.end.y-s.start.y)*t}),
    samplePathSegment:(s,count)=>Array.from({length:count+1},(_,i)=>({
      x:s.start.x+(s.end.x-s.start.x)*i/count,y:s.start.y+(s.end.y-s.start.y)*i/count})),
    pathLocalPointToCanvas:(o,p)=>fabric.util.transformPoint(new fabric.Point(p.x-o.pathOffset.x,p.y-o.pathOffset.y),o.calcTransformMatrix()),
    els:{pathNodeOverlay:{appendChild:hit=>hits.push(hit)}},
    document:{createElement:()=>({dataset:{},style:{},listeners:{},classList:{add(){}},setAttribute(){},addEventListener(name,handler){this.listeners[name]=handler;}})}});
  actual('appendPathSegmentHit',context);
  const render = actual('renderPathSegmentTargets',context);
  return {path,segment,context,hits,render,zoom};
}

for(const zoom of [.08, .25, 1, 4.56, 5]) for(const length of [32,40,48,150]) {
  test(`closing contour ${length} CSSpx has a native segment target at zoom ${zoom}`,()=>{
    const f = fixture(length,zoom), before = JSON.stringify(f.path.toObject());
    f.render(f.path);
    assert.ok(f.hits.length>0, 'a visible middle outside both endpoint margins remains grabbable');
    assert.equal(JSON.stringify(f.path.toObject()),before,'target generation never edits path or pose');
    for(const hit of f.hits) {
      assert.equal(hit.dataset.segmentEndCommand,'9');
      assert.equal(hit.dataset.contourIndex,'1');
      const width = parseFloat(hit.style.width)*zoom;
      assert.ok(width>=4-1e-8 && width<=length,'width follows a real projected chord, without min-width enlargement');
    }
  });
}

for(const length of [0,1,12,24]) test(`an edge only ${length} CSSpx long preserves endpoint-only targeting`,()=>{
  const f=fixture(length,1);f.render(f.path);assert.equal(f.hits.length,0);
});

for(const zoom of [.08,1,5]) for(const length of [32,40,48,150]) {
  test(`an unevenly parameterized cubic ${length} CSSpx wide retains its visible middle at zoom ${zoom}`,()=>{
    const f=fixture(length,zoom),segment=f.segment;
    Object.assign(segment,{type:'C',start:{x:-42.451,y:-5.553},end:{x:0,y:-5.553}});
    const pointAt=(_s,t)=>{
      const u=1-t;
      return{x:u*u*u*-42.451+3*u*u*t*-2.3436068499099676+3*u*t*t*-12.335942092503062,
        y:u*u*u*-5.553+3*u*u*t*11.1338955964866+3*u*t*t*-4.386819916609101+t*t*t*-5.553};
    };
    const project=f.context.pathLocalPointToCanvas;
    const from=project(f.path,segment.start),to=project(f.path,segment.end);
    const scale=length/(zoom*Math.hypot(to.x-from.x,to.y-from.y));
    f.context.pathLocalPointToCanvas=(o,p)=>{const q=project(o,p);return{x:q.x*scale,y:q.y*scale};};
    f.context.segmentPointAt=pointAt;
    f.context.samplePathSegment=(s,n)=>Array.from({length:n+1},(_,i)=>pointAt(s,i/n));
    f.render(f.path);
    assert.ok(f.hits.length>0,'uneven Bézier speed must not skip the eligible visible middle');
    assert.ok(f.hits.every(hit=>parseFloat(hit.style.width)*zoom>=4-1e-8));
  });
}

test('invalid and zero-length chord samples never create targets',()=>{
  const f=fixture(150,1);
  for(const to of [{x:0,y:0},{x:NaN,y:1},{x:Infinity,y:1}]) {
    f.context.appendPathSegmentHit(f.path,f.segment,{x:0,y:0},to,0,1);
  }
  assert.equal(f.hits.length,0);
});

test('segment Escape restores the isolated native routing owner and current node status',()=>{
  const canvas={getActiveObject:()=>active,discardActiveObject(){active=null;},setActiveObject(o){active=o;}};
  const owner={canvas,selectable:false,evented:false,set(v){Object.assign(this,v);}},leaf={figureId:'compound-1',path:[['M',0,0],['L',2,3]],
    set(values){Object.assign(this,values);},setCoords(){}};
  let active=leaf,status='stale';
  const selected={objectId:leaf.figureId,commandIndex:0,handleType:'endpoint'};
  const drag={objectId:leaf.figureId,pathSnapshot:[['M',0,0],['L',1,1]],selectedBefore:selected,
    selectionBefore:[selected],objectBefore:leaf,objectsBefore:[leaf],canvasActiveBefore:owner,
    canvasActiveStateBefore:{selectable:false,evented:false,hasControls:false,hasBorders:false,lockMovementX:false,lockMovementY:false}};
  const context=vm.createContext({canvas,pathNodeEdit:{segmentDrag:drag},objectForPathHandleRef:()=>leaf,
    copyPathCommands:p=>p.map(c=>c.slice()),cloneManifestValue:v=>structuredClone(v),resetPaintedVectorDirectSelectionCycle(){},
    els:{pathNodeOverlay:{}},ensureDirectSelectionCanvasCollection(){active=leaf;},
    renderIsolationSelectionOverlay(){},renderPathNodeOverlay(){},requestCanvasArtworkRender(){},
    syncInspector(){status='Select a node';owner.set({selectable:true,evented:true});},updatePathNodeStatus(o){status=o.figureId+':'+context.pathNodeEdit.selected.commandIndex;}});
  actual('cancelPathSegmentDrag',context)();
  assert.equal(active,owner,'restoring native routing does not replace the original owner with the edited leaf');
  assert.equal(active.selectable,false);assert.equal(active.evented,false);
  assert.deepEqual(Array.from(context.pathNodeEdit.selectedHandles,r=>({...r})),[selected]);
  assert.equal(status,'compound-1:0','status is refreshed after collection and Inspector reconciliation');
});

test('segment Escape preserves point-only selection without leaving a new native active object',()=>{
  let active={figureId:'unexpected-leaf'};
  const context=vm.createContext({canvas:{getActiveObject:()=>active,discardActiveObject(){active=null;}},
    pathNodeEdit:{segmentDrag:{canvasActiveBefore:null,selectionBefore:[],objectsBefore:[]}},
    objectForPathHandleRef:()=>null,resetPaintedVectorDirectSelectionCycle(){},els:{pathNodeOverlay:{}},
    ensureDirectSelectionCanvasCollection(){active={figureId:'unexpected-leaf'};},renderIsolationSelectionOverlay(){},
    renderPathNodeOverlay(){},requestCanvasArtworkRender(){},syncInspector(){},updatePathNodeStatus(){}});
  actual('cancelPathSegmentDrag',context)();
  assert.equal(active,null);
});

for(const curved of [false,true]) test(`overlapping native hit bands resolve the closest ${curved?'curved':'straight'} edge instead of the top DOM band`,()=>{
  const f=fixture(32,1),owner=f.path;
  const top={endCommandIndex:4,start:{x:0,y:-5.553},end:{x:42.451,y:-5.553},bow:curved?-3:0};
  const bottom={endCommandIndex:6,start:{x:42.451,y:0},end:{x:0,y:0},bow:curved?-3:0};
  const pointAt=(s,t)=>({x:s.start.x+(s.end.x-s.start.x)*t,y:s.start.y+(s.end.y-s.start.y)*t+s.bow*4*t*(1-t)});
  const projected=p=>f.context.pathLocalPointToCanvas(owner,p);
  const pointer=projected(pointAt(top,.5));
  const element=s=>({dataset:{objectId:owner.figureId,segmentEndCommand:String(s.endCommandIndex)},matches:()=>true});
  const upperDom=element(bottom),lowerDom=element(top),elements=[upperDom,lowerDom];
  Object.assign(f.context,{canvas:{getScenePoint:()=>pointer},pathNodeEditObjects:()=>[owner],
    objectForPathHandleRef:()=>owner,pathSegmentDescriptors:()=>[top,bottom],segmentPointAt:pointAt,
    closestSegmentRawT:(_o,s,p)=>{
      let lo=0,hi=1;
      const d=t=>{const q=projected(pointAt(s,t));return(q.x-p.x)**2+(q.y-p.y)**2;};
      for(let j=0;j<60;j++){const a=lo+(hi-lo)/3,b=hi-(hi-lo)/3;if(d(a)<d(b))hi=b;else lo=a;}
      return(lo+hi)/2;
    }});
  f.context.document.elementsFromPoint=()=>elements;f.context.els.pathNodeOverlay.contains=e=>elements.includes(e);
  const pick=actual('pathSegmentEventTarget',f.context)({clientX:100,clientY:100},upperDom,owner,bottom);
  assert.equal(pick.object,owner);assert.equal(pick.segment,top);
});

test('a segment keyboard fallback and an empty native hit stack retain their focused target',()=>{
  const f=fixture(32,1),element={},segment={endCommandIndex:9};
  f.context.canvas={getScenePoint:()=>({x:0,y:0})};
  f.context.document.elementsFromPoint=()=>[];
  const pick=actual('pathSegmentEventTarget',f.context);
  assert.equal(pick({},element,f.path,segment).segment,segment);
  assert.equal(pick({clientX:1,clientY:2},element,f.path,segment).element,element);
});

test('keyboard point insertion resolves the actual focused chord after arc spacing',()=>{
  const f=fixture(40,1);let resolved=null,inserted=null;
  f.context.closestSegmentRawT=(owner,segment,point)=>{resolved={owner,segment,point};return .37;};
  f.context.segmentPointAt=(_segment,t)=>({x:t*100,y:20});
  f.context.insertPathPointOnSegment=(owner,segment,point)=>{inserted={owner,segment,point};};
  f.context.renderPathNodeOverlay=()=>{};
  f.context.appendPathSegmentHit(f.path,f.segment,{x:10,y:20},{x:30,y:40},1,3);
  f.hits[0].listeners.keydown({key:'Enter',preventDefault(){},stopPropagation(){}});
  assert.equal(resolved.owner,f.path);assert.equal(resolved.segment,f.segment);
  assert.deepEqual({...resolved.point},{x:20,y:30});
  const expected=f.context.pathLocalPointToCanvas(f.path,{x:37,y:20});
  assert.deepEqual({...inserted.point},{...expected});
});

test('PDF point editing keeps redundant Source detail off handles while retaining other warnings',()=>{
  const object={pdfSourceId:'original-pdf'},other={pdfSourceId:'original-pdf'};
  const context=vm.createContext({state:{tool:'directSelect'},isDenseSvgProxyObject:()=>false,
    isAreaTextObject:()=>false,objectMayHaveStatusBadges:()=>true,isGroupIsolationActive:()=>false,
    isPathNodeEditing:o=>o===object,pdfDirectLeafSourceIdentity:o=>o.pdfSourceId,
    appearanceInspectorStatus:()=>({sourceBacked:true}),appearanceInspectorFeatureSummary:()=>({featureTypes:['clip_path']})});
  const badges=actual('objectStatusBadgeItems',context);
  assert.deepEqual(Array.from(badges(object),b=>b.kind),['clip']);
  assert.deepEqual(Array.from(badges(other),b=>b.kind),['source','clip']);
  context.state.tool='select';
  assert.deepEqual(Array.from(badges(object),b=>b.kind),['source','clip']);
  assert.deepEqual(object,{pdfSourceId:'original-pdf'});
  object.pdfTextRepresentation='editable-positioned-text';
  assert.deepEqual(Array.from(badges(object),b=>b.kind),['clip'],'editable PDF label retains warnings without the duplicate Source badge');
  assert.deepEqual(Array.from(badges(other),b=>b.kind),['source','clip'],'ordinary source objects keep their badge');
  assert.deepEqual(object,{pdfSourceId:'original-pdf',pdfTextRepresentation:'editable-positioned-text'});
});

test('opening PDF point controls retires an already-rendered Source badge once',()=>{
  const stop=new Error('remaining node rendering'),object={};let refreshes=0,present=true;
  const context=vm.createContext({pathNodeEdit:{object},normalizedBezierNodeMeta:{},state:{tool:'directSelect'},
    els:{pathNodeOverlay:{},objectStatusOverlay:{querySelector:()=>present?{}:null}},
    isEditablePathObject:()=>true,pdfDirectLeafSourceIdentity:()=>true,
    renderObjectStatusOverlay(){refreshes++;present=false;},pathNodeEditObjects(){throw stop;}});
  const render=actual('renderPathNodeOverlay',context);
  assert.throws(()=>render(),error=>error===stop);
  assert.equal(refreshes,1,'the stale badge is reconciled on entry without waiting for another selection event');
  assert.throws(()=>render(),error=>error===stop);
  assert.equal(refreshes,1,'subsequent point renders do not rebuild the appearance graph');
});
