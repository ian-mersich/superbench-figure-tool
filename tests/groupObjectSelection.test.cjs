'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const api=require('../app/group-object-selection.js');
test('crossing marquee and containment operate on whole objects without changing records',()=>{
  const a={},b={},c={},rows=[{object:a,bounds:{left:10,top:10,width:80,height:10}},{object:b,bounds:{left:30,top:30,width:10,height:10}},{object:c,bounds:null}];
  const before=JSON.stringify(rows),box=api.rectangle({x:40,y:45},{x:15,y:5});
  assert.deepEqual(api.collect(rows,box),[a,b]);assert.deepEqual(api.collect(rows,box,true),[b]);assert.equal(JSON.stringify(rows),before);
});
test('Shift marquee toggles a frozen starting set and can remove its last object',()=>{
  const a={},b={},c={};assert.deepEqual(api.mergedSelection([a,b],[b,c],true),[a,c]);
  assert.deepEqual(api.mergedSelection([a],[a],true),[]);assert.deepEqual(api.mergedSelection([a],[b],false),[b]);
});
for(const inverse of [[1,0,0,1,0,0],[0,-1,1,0,10,20],[-.5,0,.2,2,30,-10]])test('selected objects translate through fixed parent coordinates '+JSON.stringify(inverse),()=>{
  const a={},b={},rows=[{object:a,left:3,top:-0,inverse},{object:b,left:-9,top:12,inverse}],original=JSON.stringify(rows);
  for(const [x,y]of[[23,-17],[10,4],[0,0]]){
    const next=api.positions(rows,{x,y});assert.equal(next[0].left,3+inverse[0]*x+inverse[2]*y);assert.equal(next[1].top,12+inverse[1]*x+inverse[3]*y);
    assert.equal(JSON.stringify(rows),original);assert.equal(next[0].object,a);assert.equal(next[1].object,b);
  }
});
test('Shift movement constrains to horizontal vertical or45degrees',()=>{
  const row=[{object:{},left:0,top:0,inverse:[1,0,0,1,0,0]}];
  assert.deepEqual(api.positions(row,{x:20,y:2},true).map(x=>[x.left,x.top]),[[20,0]]);
  assert.deepEqual(api.positions(row,{x:2,y:-20},true).map(x=>[x.left,x.top]),[[0,-20]]);
  const d=api.positions(row,{x:20,y:-15},true)[0];assert.equal(d.left,-d.top);assert.ok(Math.abs(Math.hypot(d.left,d.top)-25)<1e-10);
});
function scene(){
  const multiply=(a,b)=>[a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5]];
  return {fabric:{util:{multiplyTransformMatrices:multiply}},object:{getBoundingRect:()=>({left:0,top:0,width:100,height:100}),calcTransformMatrix:()=>[1,0,0,1,0,0]}};
}
test('object marquee bounds honor positive axis-aligned ancestor clipping',()=>{
  const{object,fabric}=scene();object.group={calcTransformMatrix:()=>[1,0,0,1,0,0],clipPath:{type:'rect',width:20,height:30,calcOwnMatrix:()=>[1,0,0,1,50,40]}};
  assert.deepEqual(api.bounds(object,fabric),{left:40,top:25,width:20,height:30});
  assert.deepEqual(api.collect([{object,bounds:api.bounds(object,fabric)}],{left:0,top:0,width:10,height:10}),[]);
});
for(const property of ['visible','locked','opacity'])test('unavailable ancestor '+property+' prevents invisible selection candidates',()=>{
  const{object,fabric}=scene();object.group={calcTransformMatrix:()=>[1,0,0,1,0,0],[property]:property==='visible'?false:property==='locked'?true:0};assert.equal(api.bounds(object,fabric),null);
});
for(const clip of [{inverted:true},{type:'circle'},{getObjects:()=>[{}]}])test('unknown clip geometry stays outside bounded object selection '+JSON.stringify(clip),()=>{
  const{object,fabric}=scene();object.clipPath={calcOwnMatrix:()=>[1,0,0,1,0,0],...clip};assert.equal(api.bounds(object,fabric),null);
});
test('return to the original grab point preserves raw signed-zero coordinates',()=>{
  const rows=[{object:{},left:-0,top:-0,inverse:[-1,0,0,1,0,0]}];
  for(const constrain of [false,true])for(const delta of [{x:0,y:0},{x:-0,y:0}]){
    const [position]=api.positions(rows,delta,constrain);
    assert.ok(Object.is(position.left,-0));assert.ok(Object.is(position.top,-0));
  }
});
for(const clip of [
  {type:'rect',width:20,height:30,rx:4},
  {type:'rect',width:20,height:30,ry:4},
  {path:[['M',0,0],['L',20,30],['L',20,0],['L',0,30],['Z']],pathOffset:{x:0,y:0}},
  {path:[['M',0,0],['L',20,0],['L',20,30],['L',20,0],['Z']],pathOffset:{x:0,y:0}}
])test('rounded or non-perimeter rectangle clips are refused '+JSON.stringify(clip),()=>{
  const{object,fabric}=scene();object.clipPath={calcOwnMatrix:()=>[1,0,0,1,20,20],...clip};assert.equal(api.bounds(object,fabric),null);
});
test('an exact rectangular perimeter path remains admitted',()=>{
  const{object,fabric}=scene();object.clipPath={path:[['M',0,0],['L',20,0],['L',20,30],['L',0,30],['Z']],pathOffset:{x:0,y:0},calcOwnMatrix:()=>[1,0,0,1,20,20]};
  assert.deepEqual(api.bounds(object,fabric),{left:20,top:20,width:20,height:30});
});
test('adjacent native text shares display outlines without changing the selected source objects',()=>{
  const a={text:'Ex'},b={text:'tr'},c={text:'next row'},d={path:[]};
  const records=[{object:a,bounds:{left:10,top:20,width:15,height:8}},{object:b,bounds:{left:24,top:20,width:10,height:8}},{object:c,bounds:{left:10,top:30,width:40,height:8}},{object:d,bounds:{left:10,top:20,width:10,height:8}}];
  const before=JSON.stringify(records),rows=api.outlines(records);assert.equal(rows.length,3);assert.deepEqual(rows.find(r=>r.objects.includes(a)).objects,[a,b]);
  assert.equal(JSON.stringify(records),before);assert.deepEqual(rows.find(r=>r.objects.includes(a)).bounds,{left:10,top:20,width:24,height:8});
});
