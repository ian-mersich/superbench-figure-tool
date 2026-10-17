const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const test=require('node:test');
const source=fs.readFileSync(require('node:path').join(__dirname,'../app/app.js'),'utf8');
const start=source.indexOf('  async function prewarmScientificAsset(');
const end=source.indexOf('\n  function ',start);
const actual=source.slice(start,end);

test('an in-flight Style 4 prewarm retains its own paint bindings when the Library style changes',async()=>{
 let selectedStyle='style-4',releaseSource;
 const delayedSource=new Promise(resolve=>{releaseSource=resolve;});
 const bindings=[];
 const context={
  CUSTOM_PROPS:[],scientificAssetArtStyle:()=>selectedStyle,
  loadScientificAssetSvgSource:async(_asset,style)=>{assert.equal(style,'style-4');return delayedSource;},
  scientificAssetVectorPrototypeCacheSignature:()=>({key:'supplied-style-four',canonicalSvg:'<svg/>'}),
  cachedScientificAssetVectorPrototype:()=>null,
  scientificAssetVectorPrototypePromiseCache:new Map(),scientificAssetVectorPrototypeCache:new Map(),
  styledScientificAssetMetadata:(_asset,style)=>({editable_color_regions:[{id:'accent',paint:style==='style-4'?'stroke':'fill'}]}),
  loadScientificAssetSvg:async(_svg,regions)=>{bindings.push(regions);return{objects:[{}],options:{}};},
  fabricRef:{util:{groupSVGElements:()=>({clone:async()=>({})})}},
  originalSizeForObject:()=>({width:128,height:128}),fabricDataRegionAttributesPreserved:()=>true,
  trimScientificAssetCache:()=>{},SCIENTIFIC_ASSET_VECTOR_CACHE_LIMIT:24
 };
 vm.createContext(context);vm.runInContext(actual,context);
 const pending=context.prewarmScientificAsset({id:'core.cell.astrocyte_like'});
 selectedStyle='soft-color';releaseSource('<svg/>');await pending;
 assert.equal(bindings.length,1);assert.equal(bindings[0][0].paint,'stroke');
});
