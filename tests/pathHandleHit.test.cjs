'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(process.env.FIGURE_APP_SOURCE || require.resolve('../app/app.js'),'utf8');
const start=source.indexOf('  function pathHandleEventTarget('),end=source.indexOf('\n  function ',start+1);
assert.ok(start>0&&end>start);
function fixture({coincident=false,selected='control2',stack=['endpoint','control2']}={}){
  const object={figureId:'path'},descriptors=[{commandIndex:1,handleType:'endpoint'},{commandIndex:1,handleType:'control2'}],elements={};
  for(const descriptor of descriptors){const x=descriptor.handleType==='endpoint'?100:coincident?100:104;
    elements[descriptor.handleType]={dataset:{objectId:'path',commandIndex:'1',handleType:descriptor.handleType},disabled:false,
      matches:s=>s==='.path-node-handle',getBoundingClientRect:()=>({left:x-6,top:94,width:12,height:12})};}
  const context=vm.createContext({document:{elementsFromPoint:()=>stack.map(k=>elements[k]).filter(Boolean)},els:{pathNodeOverlay:{contains:e=>Object.values(elements).includes(e)}},
    objectForPathHandleRef:r=>r.objectId==='path'?object:null,pathNodeEditObjects:()=>[object],pathHandleDescriptors:()=>descriptors,
    qualifyPathHandle:(o,d)=>d,isPathHandleSelected:d=>d.handleType===selected});
  vm.runInContext(source.slice(start,end),context);
  return {elements,descriptors,context,resolve:(x,y=100,type='pointerdown',detail=1)=>context.pathHandleEventTarget({type,detail,clientX:x,clientY:y},elements.endpoint,object,descriptors[0])};
}
test('selected control center remains reachable beneath the later endpoint in browser hit order',()=>{
  const f=fixture();assert.equal(f.resolve(104).descriptor.handleType,'control2');
  assert.equal(f.resolve(103).descriptor.handleType,'control2','off-center nearer-control point');
});
test('nearby endpoint center stays reachable while control is selected',()=>{
  const f=fixture();assert.equal(f.resolve(100).descriptor.handleType,'endpoint');assert.equal(f.resolve(101).descriptor.handleType,'endpoint');
});
test('pointerdown and mouse click resolve the same nearest handle',()=>{
  const f=fixture();assert.equal(f.resolve(104).descriptor.handleType,f.resolve(104,100,'click').descriptor.handleType);
});
test('exact-center ties retain selected intent and permit an already-cycled endpoint',()=>{
  assert.equal(fixture({coincident:true}).resolve(100).descriptor.handleType,'control2');
  assert.equal(fixture({coincident:true,selected:'endpoint'}).resolve(100).descriptor.handleType,'endpoint');
});
test('unselected exact-center tie chooses endpoint independent of hit-stack order',()=>{
  for(const stack of [['endpoint','control2'],['control2','endpoint']])assert.equal(fixture({coincident:true,selected:null,stack}).resolve(100).descriptor.handleType,'endpoint');
});
test('native hit-stack admission wins over an overlapping bounding box',()=>{
  const f=fixture({stack:['endpoint']});assert.equal(f.resolve(104).descriptor.handleType,'endpoint','non-admitted control is not recovered from its bounding box');
});
test('disabled and detached handles cannot steal the existing target',()=>{
  const f=fixture();f.elements.control2.disabled=true;assert.equal(f.resolve(104).descriptor.handleType,'endpoint');
  f.elements.control2.disabled=false;f.context.pathNodeEditObjects=()=>[];assert.equal(f.resolve(104).descriptor.handleType,'endpoint');
});
test('keyboard click retains the focused descriptor regardless of coincident pointer coordinates',()=>{
  const f=fixture();assert.equal(f.resolve(104,100,'click',0).descriptor.handleType,'endpoint');
});

test('real transformed junction endpoint centers resolve consistently beneath the later sibling button',()=>{
  // Exact measured CSS rectangles from the retained topology-repro02 probe.
  const object={figureId:'path-mw4fyum6-24'},rows=[
    {commandIndex:2,left:819.5645751953125,top:492.583251953125},
    {commandIndex:16,left:821.962890625,top:500.31988525390625}
  ],descriptors=rows.map(row=>({commandIndex:row.commandIndex,handleType:'endpoint'}));
  const elements=rows.map(row=>({dataset:{objectId:object.figureId,commandIndex:String(row.commandIndex),handleType:'endpoint'},
    disabled:false,matches:s=>s==='.path-node-handle',getBoundingClientRect:()=>({...row,width:12,height:12})}));
  const context=vm.createContext({document:{elementsFromPoint:()=>[elements[1],elements[0]]},
    els:{pathNodeOverlay:{contains:element=>elements.includes(element)}},
    objectForPathHandleRef:ref=>ref.objectId===object.figureId?object:null,pathNodeEditObjects:()=>[object],
    pathHandleDescriptors:()=>descriptors,qualifyPathHandle:(_object,descriptor)=>descriptor,isPathHandleSelected:()=>false});
  vm.runInContext(source.slice(start,end),context);
  const x=rows[0].left+6,y=rows[0].top+6;
  assert.ok(Math.hypot(rows[1].left-rows[0].left,rows[1].top-rows[0].top)>0,'distinct centers');
  for(const type of ['pointerdown','click']){
    const result=context.pathHandleEventTarget({type,detail:1,clientX:x,clientY:y},elements[1],object,descriptors[1]);
    assert.equal(result.descriptor.commandIndex,2,type+' native target');
    assert.equal(result.element,elements[0],type+' drag element');
  }
});
