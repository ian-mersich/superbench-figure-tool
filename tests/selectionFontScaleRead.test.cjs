'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const fabric=require('../vendor/fabric/index.min.js');
const source=fs.readFileSync(require.resolve('../app/app.js'),'utf8');
const legacy=fs.readFileSync(require.resolve('./fixtures/shared-selection-font-app716.js'),'utf8');
function actual(text,name,context){
  const a=text.indexOf('  function '+name+'('),b=text.indexOf('\n  function ',a+5);
  assert.ok(a>=0,name);vm.runInContext(text.slice(a,b<0?text.length:b),context);
}
function query(old=false){
  const context=vm.createContext({fabricRef:fabric,isCanvasTextObject:o=>typeof o.text==='string',
    isReferenceObject:o=>Boolean(o.reference),inheritedMasterMeta:o=>Boolean(o.master),supportsText:o=>typeof o.text==='string',
    inspectorCapabilities:o=>({font:typeof o.text==='string',fill:true,stroke:true,opacity:true}),readStyle:o=>o,
    numericTransformSelectionGuard:()=>({status:'ok'})});
  for(const name of ['selectionPropertyObjects','pdfTextFontSceneScale','displayedTextFontSize',
    'selectionPropertyValue','comparableSelectionValue','scientificTextGraphemes','scientificTypographyRawStyleAt','scientificTypographyValueAt'])actual(source,name,context);
  actual(old?legacy:source,'sharedSelectionProperty',context);
  return (objects,property='fontSize')=>JSON.parse(JSON.stringify(context.sharedSelectionProperty(objects,property)));
}
function text(value,options={}){
  const matrix=Object.hasOwn(options,'matrix')?options.matrix:[1,0,0,2,0,0];let reads=0;
  const object={text:value,fontSize:10,fontFamily:'Arial',fill:'#000000',styles:options.styles||[],
    get2DCursorLocation:index=>({lineIndex:0,charIndex:index}),
    getValueOfPropertyAt(_line,index,property){return this.styles[index]?.[property]??this[property];},
    _pdfCurrentNativePaintMatrix(){reads++;return matrix;},...options.object};
  return {object,matrix,reads:()=>reads};
}
function same(objects,property='fontSize'){
  return assert.deepEqual(query()(objects,property),query(true)(objects,property));
}

test('30 whole labels retain the literal result with one native measurement per object',()=>{
  const rows=Array.from({length:30},(_,i)=>text('Whole editable pathway label β '+i));
  const objects=rows.map(r=>r.object),before=JSON.stringify(objects);
  const current=query()(objects),work=rows.reduce((sum,r)=>sum+r.reads(),0);
  const old=query(true)(objects),oldWork=rows.reduce((sum,r)=>sum+r.reads(),0)-work;
  assert.deepEqual(current,old);assert.equal(current.value,20);
  assert.equal(work,30);assert.ok(oldWork>work*20,'literal old loop repeats whole-object plane measurement per grapheme');
  assert.throws(()=>assert.ok(oldWork<=objects.length),assert.AssertionError,'the same work bound rejects the literal old function');
  assert.equal(JSON.stringify(objects),before,'property reads change no authored state');
});

test('per-character sizes, Unicode, selected ranges and mixed/partial eligibility are unchanged',()=>{
  const a=text('Aβ😀\nB',{styles:[{fontSize:'8'},{fontSize:12},{fontSize:14},null,{fontSize:16}]}),b=text('xyz',{matrix:[1,0,0,3,0,0]});
  same([a.object,b.object]);assert.equal(query()([a.object,b.object]).mixed,true);
  a.object.isEditing=true;a.object.selectionStart=1;a.object.selectionEnd=2;
  const selected=query()([a.object]);assert.equal(selected.value,24);assert.equal(selected.mixed,false);same([a.object]);
  const partial=query()([a.object,{fill:'#ffffff'}]);assert.equal(partial.supportedCount,1);assert.equal(partial.totalCount,2);assert.equal(partial.partial,true);assert.equal(partial.mixed,true);same([a.object,{fill:'#ffffff'}]);
  const locked=text('ignored',{object:{locked:true}}),master=text('master',{object:{master:true}}),reference=text('reference',{object:{reference:true}});
  same([a.object,locked.object,master.object,reference.object]);assert.equal(locked.reads()+master.reads()+reference.reads(),0);
});

test('newline-only and empty ranges stay lazy; unrelated character properties never measure native scale',()=>{
  const row=text('\n\n');same([row.object]);assert.equal(row.reads(),0);
  row.object.text='A\nB';row.object.isEditing=true;row.object.selectionStart=1;row.object.selectionEnd=2;
  same([row.object]);assert.equal(row.reads(),0);
  const empty=text('');same([empty.object]);assert.equal(empty.reads(),2,'the unchanged non-character fallback measures an empty text object once per query');
  const ordinary=text('ABβ');for(const property of ['fill','fontFamily','fontWeight','fontStyle','underline','linethrough'])same([ordinary.object],property);
  assert.equal(ordinary.reads(),0);
});

test('native invalid scales and source-transform fallback preserve exact numeric results',()=>{
  for(const matrix of [[1,0,0,0,0,0],[1,0,0,Infinity,0,0],[1,0,NaN,1,0,0]]){
    const row=text('AB',{matrix});same([row.object]);assert.equal(query()([row.object]).value,10);
  }
  const fallback=text('AB',{matrix:null,object:{pdfTextSource:{schema:'figureStudio.pdfPositionedText.v1'},calcTransformMatrix:()=>[2,0,0,3,4,5]}});
  same([fallback.object]);assert.equal(query()([fallback.object]).value,30);
});

test('later calls observe in-place transform/style/range changes, with no retained measurement',()=>{
  const row=text('AB'),run=query();assert.equal(run([row.object]).value,20);assert.equal(row.reads(),1);
  row.matrix[3]=3;row.object.styles[0]={fontSize:12};row.object.isEditing=true;row.object.selectionStart=0;row.object.selectionEnd=1;
  assert.equal(run([row.object]).value,36);assert.equal(row.reads(),2);same([row.object]);
});

test('value and native-measurement failures preserve exception order and do not poison later calls',()=>{
  const value=text('A',{styles:[{fontSize:Symbol('invalid')}]});
  assert.throws(()=>query()([value.object]),{name:'TypeError',message:'Cannot convert a Symbol value to a number'});assert.equal(value.reads(),0);
  assert.throws(()=>query(true)([value.object]),{name:'TypeError',message:'Cannot convert a Symbol value to a number'});assert.equal(value.reads(),0);
  const row=text('AB',{object:{_pdfCurrentNativePaintMatrix(){throw Error('native read failed');}}}),run=query();
  assert.throws(()=>run([row.object]),/native read failed/);
  row.object._pdfCurrentNativePaintMatrix=()=>[1,0,0,4,0,0];assert.equal(run([row.object]).value,40);
});
