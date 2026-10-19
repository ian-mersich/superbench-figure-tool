(function(root,factory){const snapshots=typeof module==='object'&&module.exports?require('./pdf-current-native-operator-snapshots.js'):root.FigureStudioPdfCurrentNativeOperatorSnapshots;const api=factory(snapshots);if(typeof module==='object'&&module.exports)module.exports=api;else root.FigureStudioPdfCurrentNativeClipPlanes=api;})(typeof globalThis==='object'?globalThis:this,function(snapshots){
'use strict';
// Runtime-only current decoded operator proof. No poses are replayed into SVG
// or native artwork, and no geometry is attached to transport marker metadata.
const issued=new WeakMap(),I=[1,0,0,1,0,0];
const multiply=(a,b)=>[a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5]];
const point=(m,p)=>[m[0]*p[0]+m[2]*p[1]+m[4],m[1]*p[0]+m[3]*p[1]+m[5]];
function refuse(message){const e=new Error(message);e.code='PDF_LOGICAL_TEXT_UNSUPPORTED';throw e;}
function equal(a,b){if(Object.is(a,b))return true;if(!a||!b||typeof a!=='object'||typeof b!=='object')return false;const ak=Object.keys(a),bk=Object.keys(b);return ak.length===bk.length&&ak.every((k,i)=>k===bk[i]&&equal(a[k],b[k]));}
function freeze(value){if(value&&typeof value==='object'){for(const child of Object.values(value))freeze(child);Object.freeze(value);}return value;}
function captureOperators(operators){
 let count=0,bytes=0;
 function copy(value,depth=0){if(++count>200000||depth>48)refuse('Current native operator proof exceeds its bounded graph budget.');if(typeof value==='string'){bytes+=value.length;if(bytes>8000000)refuse('Current native operator proof exceeds its byte budget.');return value;}if(value===null||typeof value!=='object')return value;
  if(Array.isArray(value))return {kind:'Array',values:value.map(v=>copy(v,depth+1))};
  if(ArrayBuffer.isView(value)){if(value instanceof DataView)refuse('Unsupported current native operator byte view.');return {kind:value.constructor.name,values:Array.from(value,v=>copy(v,depth+1))};}
  const keys=Object.keys(value);return {kind:'Object',keys,values:keys.map(k=>copy(value[k],depth+1))};
 }
 if(!operators?.fnArray||!operators.argsArray||operators.fnArray.length!==operators.argsArray.length)refuse('Current native operator arrays are unavailable.');
 return freeze(copy({fnArray:operators.fnArray,argsArray:operators.argsArray}));
}
function sameOperators(operators,snapshot){try{return equal(captureOperators(operators),snapshot);}catch(_){return false;}}
function finiteMatrix(m){return Array.isArray(m)&&m.length===6&&m.every(Number.isFinite);}
function rectangle(ops,args,OPS){
 let cursor=0,points=[],supported=true;
 for(const id of ops){if(id===OPS.rectangle){const[x,y,w,h]=Array.from(args).slice(cursor,cursor+4);cursor+=4;points.push([x,y],[x+w,y],[x+w,y+h],[x,y+h]);}else if(id===OPS.moveTo||id===OPS.lineTo){points.push(Array.from(args).slice(cursor,cursor+2));cursor+=2;}else if(id===OPS.closePath){}else {supported=false;cursor+=id===OPS.curveTo?6:id===OPS.curveTo2||id===OPS.curveTo3?4:0;}}
 if(cursor!==args.length)return null;if(points.length===5&&equal(points[0],points[4]))points.pop();
 return supported&&points.length===4&&points.every(p=>p.length===2&&p.every(Number.isFinite))?points:null;
}
function* bindingSteps(operators,OPS,viewport,snapshot){
 if(!OPS||!finiteMatrix(viewport?.transform))refuse('Current native clip viewport is unavailable.');
 const names=new Map(Object.entries(OPS).map(([n,id])=>[id,n]));
 const forbidden=new Set(['beginGroup','endGroup','paintFormXObjectBegin','paintFormXObjectEnd','shadingFill','setFillColorN','setStrokeColorN','paintImageXObjectRepeat','paintInlineImageXObjectGroup','paintImageMaskXObject','paintImageMaskXObjectRepeat','paintImageMaskXObjectGroup']);
 const paints=new Set(['fill','eoFill','stroke','closeStroke','fillStroke','eoFillStroke','closeFillStroke','closeEOFillStroke']);
 let current={planes:[],clips:[],ctm:I.slice(),world:Array.from(viewport.transform)},pending=null,path=null;const stack=[],shows=[];
 function finishClip(){if(!pending)return;if(!path||!equal(path.planes,current.planes))refuse('Current native clip path/frame is outside the bounded local-plane profile.');if(current.clips.length>=16)refuse('Current native clip scope budget exceeded.');current={...current,clips:[...current.clips,freeze({sourceOperatorIndex:pending.index,rule:pending.rule,planes:path.planes.map(m=>m.slice()),points:path.points.map(p=>p.slice())})]};pending=null;}
 for(let index=0;index<operators.fnArray.length;index++){
  yield;
  const name=names.get(operators.fnArray[index]),args=operators.argsArray[index]||[];
  if(forbidden.has(name))refuse('Current native clip planes have not qualified '+name+'.');
  if(name==='save'){if(stack.length>=128||pending)refuse('Current native clip save scope is unqualified.');stack.push(current);continue;}
  if(name==='restore'){if(!stack.length||pending)refuse('Current native clip restore scope is unbalanced.');current=stack.pop();path=null;continue;}
  if(name==='transform'){const m=Array.from(args);if(!finiteMatrix(m)||current.planes.length>=256)refuse('Current native CM planes are malformed or over budget.');const ctm=multiply(current.ctm,m),world=multiply(current.world,m),neutral=equal(m,I)&&equal(ctm,current.ctm)&&equal(world,current.world);current={...current,ctm,world,planes:neutral?current.planes:[...current.planes,m]};continue;}
  if(name==='constructPath'){const points=rectangle(args[0],args[1],OPS);path=points?{points,planes:current.planes}:null;continue;}
  if(name==='clip'||name==='eoClip'){if(pending)refuse('Current native clip operation is incomplete.');pending={index,rule:name==='clip'?'nonzero':'evenodd'};continue;}
  if(name==='endPath'||paints.has(name)){finishClip();path=null;continue;}
  if(name==='showText'||name==='showSpacedText'){if(pending)refuse('Current native text precedes pending clip completion.');shows.push(freeze({sourceTextShowIndex:shows.length,clips:current.clips.slice()}));}
 }
 if(stack.length||pending)refuse('Current native clip plane scopes are incomplete.');
 return {operators,OPS,snapshot,viewport:Array.from(viewport.transform),shows:freeze(shows)};
}
function issue(record){const token=Object.freeze({schema:'figureStudio.currentNativeClipPlanes.v1'});issued.set(token,record);return token;}
function bindCurrentOperators(operators,OPS,viewport){
 const snapshot=captureOperators(operators),steps=bindingSteps(operators,OPS,viewport,snapshot);let step;do{step=steps.next();}while(!step.done);return issue(step.value);
}
async function runBatches(steps,{signal,yieldEvery=2048,yieldControl=snapshots?.yieldToUi||(()=>new Promise(resolve=>setTimeout(resolve,0)))}={}){
 if(!Number.isSafeInteger(yieldEvery)||yieldEvery<1||typeof yieldControl!=='function')refuse('Invalid current native proof batch controls.');
 const cancelled=()=>{if(signal?.aborted){const error=new Error('Current native clip proof was cancelled.');error.name='AbortError';throw error;}};
 let count=0;cancelled();while(true){const step=steps.next();if(step.done){cancelled();return step.value;}if(++count%yieldEvery===0){await yieldControl();cancelled();}}
}
async function bindCurrentOperatorsBatched(operators,OPS,viewport,snapshot,options={}){
 const view=Array.from(viewport?.transform||[]),width=viewport?.width,height=viewport?.height;
 const unchanged=()=>finiteMatrix(view)&&viewport.transform?.length===view.length&&view.every((value,index)=>Object.is(value,viewport.transform[index]))&&Object.is(width,viewport.width)&&Object.is(height,viewport.height);
 if(!unchanged())refuse('Current native clip batch viewport is unavailable.');
 if(!snapshots?.isIssued(snapshot)||!await snapshots.same(operators,snapshot,options))refuse('Current native clip batches require a completed unchanged operator snapshot.');
 if(!unchanged())refuse('Current native clip batch viewport changed during input proof.');
 const record=await runBatches(bindingSteps(operators,OPS,viewport,snapshot),options);
 if(!await snapshots.same(operators,snapshot,options))refuse('Current native operators changed during clip batch construction.');
 if(!unchanged())refuse('Current native clip batch viewport changed during construction.');
 record.batched=true;record.signal=options.signal;record.viewportOwner=viewport;record.viewportWidth=width;record.viewportHeight=height;return issue(record);
}
function authority(token,operators,OPS){const a=issued.get(token);if(!a||operators&&operators!==a.operators||OPS&&OPS!==a.OPS||!sameOperators(a.operators,a.snapshot))refuse('Current native clip authority is missing, foreign or changed.');return a;}
function currentShows(token,operators,OPS){return authority(token,operators,OPS).shows;}
function isBatchedAuthority(token){return issued.get(token)?.batched===true;}
function assertCurrentViewportBatched(token,viewport){const a=issued.get(token);if(!a?.batched||viewport!==a.viewportOwner||viewport.transform?.length!==6||!a.viewport.every((value,index)=>Object.is(value,viewport.transform[index]))||!Object.is(a.viewportWidth,viewport.width)||!Object.is(a.viewportHeight,viewport.height))refuse('Current native clip batch viewport ownership or values changed.');return true;}
async function currentShowsBatched(token,operators,OPS,snapshot,options={}){
 const a=issued.get(token);if(!a||!a.batched||operators&&operators!==a.operators||OPS&&OPS!==a.OPS||snapshot&&snapshot!==a.snapshot||!snapshots?.isIssued(a.snapshot))refuse('Current native clip batch authority is missing, foreign or changed.');assertCurrentViewportBatched(token,a.viewportOwner);if(!await snapshots.same(a.operators,a.snapshot,{...options,signal:a.signal||options.signal}))refuse('Current native clip batch operands changed.');assertCurrentViewportBatched(token,a.viewportOwner);return a.shows;
}
function transform(text=''){
 const tokens=[...text.matchAll(/(matrix|scale|translate)\(([^)]*)\)/g)];if(tokens.map(t=>t[0]).join('').replace(/\s/g,'')!==text.replace(/\s/g,''))refuse('Unknown current clip SVG transform.');
 return tokens.reduce((m,t)=>{const a=t[2].trim().split(/[ ,]+/).map(Number);if(!a.every(Number.isFinite))refuse('Nonfinite current clip SVG transform.');let local;
  if(t[1]==='matrix'){if(a.length!==6)refuse('Malformed current clip SVG matrix.');local=a;}else {if(![1,2].includes(a.length))refuse('Malformed current clip SVG transform.');local=t[1]==='scale'?[a[0],0,0,a[1]??a[0],0,0]:[1,0,0,1,a[0],a[1]??0];}return multiply(m,local);
 },I);
}
function ownerMatrix(element,root){const chain=[];for(let n=element;n&&n!==root;n=n.parentElement){if(n.hasAttribute('style')||n.hasAttribute('mask')||n.hasAttribute('filter'))refuse('Current native clip reference has an unqualified styled effect.');chain.unshift(n);}return chain.reduce((m,n)=>multiply(m,transform(n.getAttribute('transform')||'')),I);}
function clipDom(svg){
 const elements=[svg,...Array.from(svg.querySelectorAll('*'))];if(elements.length>20000)refuse('Current SVG declaration budget exceeded.');const ids=new Set();for(const element of elements){const id=element.getAttribute('id');if(id){if(ids.has(id))refuse('Current SVG global element IDs are ambiguous.');ids.add(id);}}
 const defs=Array.from(svg.querySelectorAll('clipPath'));if(defs.length>4096)refuse('Current SVG clip definition budget exceeded.');const byId=new Map();
 for(const d of defs){const id=d.getAttribute('id');if(!id||byId.has(id))refuse('Current SVG clip definitions are ambiguous.');byId.set(id,d);}
 return byId;
}
function matchClip(a,span,svg,index,rectangleFromElement,byId){
 const show=a.shows[index];if(!show||typeof rectangleFromElement!=='function')refuse('Current native clip show/parser is unavailable.');
 const owners=[];for(let n=span;n&&n!==svg;n=n.parentElement)if(n.hasAttribute('clip-path'))owners.unshift(n);
 const ordered=[],seen=new Set();let expansions=0;
 function expand(ref,owner,active=new Set()){
  const m=/^url\(#([^\s)]+)\)$/.exec(ref||''),d=byId.get(m?.[1]);if(!d||active.has(d)||active.size>=16||++expansions>256)refuse('Current SVG native clip reference is missing, cyclic or over budget.');active.add(d);
  if(d.hasAttribute('clip-path'))expand(d.getAttribute('clip-path'),owner,active);
  if(!seen.has(d)){seen.add(d);ordered.push({definition:d,owner});}active.delete(d);
 }
 for(const n of owners)expand(n.getAttribute('clip-path'),n);if(ordered.length!==show.clips.length)refuse('Current SVG native ordered clip count differs.');
 const scopes=ordered.map(({definition,owner},scopeIndex)=>{
  const native=show.clips[scopeIndex];if(definition.hasAttribute('transform')||definition.hasAttribute('style')||definition.hasAttribute('mask')||definition.hasAttribute('filter')||definition.hasAttribute('clipPathUnits')&&definition.getAttribute('clipPathUnits')!=='userSpaceOnUse'||definition.children.length!==1)refuse('Current SVG native clip declaring frame differs.');
  const reference=ownerMatrix(owner,svg);if(!equal(reference,a.viewport))refuse('Current SVG native clip reference context differs.');
  let node=definition.children[0],planes=[];
  while(node.localName.toLowerCase()==='g'){
   if(node.children.length!==1||!node.hasAttribute('transform')||Array.from(node.attributes).some(attribute=>attribute.name!=='transform')||planes.length>=256)refuse('Current SVG native clip plane is malformed.');
   const raw=node.getAttribute('transform'),m=/^matrix\(([^)]*)\)$/.exec(raw);if(!m)refuse('Current SVG native clip plane must retain its literal CM matrix.');const plane=m[1].trim().split(/[ ,]+/).map(Number);if(!finiteMatrix(plane))refuse('Current SVG native clip plane is nonfinite.');planes.push(plane);node=node.children[0];
  }
  if(node.hasAttribute('transform')||node.hasAttribute('clip-path')||node.hasAttribute('style')||node.hasAttribute('mask')||node.hasAttribute('filter')||node.children.length||!equal(planes,native.planes))refuse('Current SVG literal clip planes differ from actual decoded native CM operations.');
  const localPoints=rectangleFromElement(node),rule=node.getAttribute('clip-rule')||definition.getAttribute('clip-rule')||'nonzero';if(!equal(localPoints,native.points)||rule!==native.rule)refuse('Current SVG clip vertices/rule differ from actual decoded native path operation.');
  const world=planes.reduce(multiply,reference),points=localPoints.map(p=>point(world,p));
  const nativeWorld=native.planes.reduce(multiply,a.viewport),nativePoints=native.points.map(p=>point(nativeWorld,p));if(!equal(points,nativePoints))refuse('Current SVG local-plane clip world coordinates differ.');
  return {kind:'rect',points,rule,inverted:false,source:'decoded-pdf',sourceOperatorIndex:native.sourceOperatorIndex};
 });
 return {schema:'figureStudio.decodedEffectiveClip.v1',scopes};
}
function matchDecodedSvgClip(token,span,svg,index,rectangleFromElement){return matchClip(authority(token),span,svg,index,rectangleFromElement,clipDom(svg));}
async function matchDecodedSvgClipsBatched(token,spans,svg,rectangleFromElement,{svgText,signal,yieldControl}={}){
 if(!Array.isArray(spans)||spans.length>20000)refuse('Current native clip scalar input exceeds the original declaration budget.');
 const initialSpans=Object.freeze(spans.slice());
 const options={signal,yieldControl},cancelled=()=>{if(signal?.aborted){const error=new Error('Current native clip proof was cancelled.');error.name='AbortError';throw error;}};
 cancelled();let a;if(isBatchedAuthority(token)){await currentShowsBatched(token,undefined,undefined,undefined,options);a=issued.get(token);}else a=authority(token);cancelled();
 const serialize=()=>new XMLSerializer().serializeToString(svg);
 if(typeof svgText!=='string'||serialize()!==svgText||initialSpans.length!==a.shows.length)refuse('Current native clip DOM changed before batch traversal.');
 const elements=[svg,...Array.from(svg.querySelectorAll('*'))],member=()=>{
  const actual=[svg,...Array.from(svg.querySelectorAll('*'))],glyphs=Array.from(svg.querySelectorAll('tspan')).filter(span=>span.hasAttribute('data-figure-studio-native-logical-glyph'));
  return spans.length===initialSpans.length&&initialSpans.every((span,index)=>span===spans[index])&&actual.length===elements.length&&actual.every((element,index)=>element===elements[index])&&glyphs.length===initialSpans.length&&glyphs.every((span,index)=>span===initialSpans[index]&&span.getAttribute('data-figure-studio-native-logical-glyph')===String(index));
 };
 if(!member())refuse('Current native clip batch has stale scalar or DOM identity.');
 const definitions=clipDom(svg),results=[];
 function* steps(){for(let index=0;index<initialSpans.length;index++){results.push(matchClip(a,initialSpans[index],svg,index,rectangleFromElement,definitions));yield;}}
 await runBatches(steps(),{signal,yieldControl,yieldEvery:32});
 if(a.batched)await currentShowsBatched(token,undefined,undefined,undefined,options);else authority(token);cancelled();
 if(results.length!==initialSpans.length||results.length!==a.shows.length||!member()||serialize()!==svgText)refuse('Current native clip DOM changed during batch traversal.');cancelled();return results;
}
return Object.freeze({captureOperators,sameOperators,bindCurrentOperators,currentShows,matchDecodedSvgClip,bindCurrentOperatorsBatched,isBatchedAuthority,currentShowsBatched,assertCurrentViewportBatched,matchDecodedSvgClipsBatched});
});
