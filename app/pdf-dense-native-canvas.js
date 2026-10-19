/* Unwired view adapter. Capture the actual bundled CanvasGraphics constructor
 * from its exact native render task; never copy its clipping/paint policies.
 * A constructor token is rendering evidence, not canonical source authority. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.FigureStudioPdfDenseNativeCanvas=api;})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const issued=new WeakMap(),factories=new WeakSet(),VERSION='3.11.174',LIMITS=Object.freeze({pixels:16777216,captureMs:5000,depth:48});
const required=['beginDrawing','endDrawing','save','restore','transform','constructPath','clip','eoClip','endPath','setFillRGBColor','setStrokeRGBColor','setLineWidth','setLineCap','setLineJoin','setMiterLimit','fill','eoFill','stroke','closeStroke','fillStroke','eoFillStroke','closeFillStroke','closeEOFillStroke'];
function refuse(message){const e=new Error(message);e.code='PDF_DENSE_NATIVE_CANVAS_REFUSED';throw e;}
function abortError(){const e=new Error('Native Canvas constructor capture was cancelled.');e.name='AbortError';return e;}
const matrix=value=>Array.isArray(value)&&value.length===6&&value.every(Number.isFinite)&&value[0]*value[3]-value[1]*value[2]!==0;
const same=(a,b)=>a.length===b.length&&a.every((v,i)=>Array.isArray(v)?Array.isArray(b[i])&&same(v,b[i]):Object.is(v,b[i]));
async function capture({page,pdfjs,viewport,ownerKey,assertCurrentSource,signal}={}){
 const transform=Array.from(viewport?.transform||[]),width=viewport?.width,height=viewport?.height;
 if(pdfjs?.version!==VERSION||!page||typeof page.render!=='function'||!(page._intentStates instanceof Map)||!ownerKey||typeof ownerKey!=='object'||typeof assertCurrentSource!=='function'||!matrix(transform)||!Number.isFinite(width)||width<=0||!Number.isFinite(height)||height<=0||typeof OffscreenCanvas!=='function')refuse('Native Canvas capture requires the owned actual bundled page and worker canvas.');
 const checkViewport=()=>{if(!Object.is(viewport.width,width)||!Object.is(viewport.height,height)||!same(Array.from(viewport.transform||[]),transform))refuse('Native Canvas viewport changed during capture.');};
 const checkSource=async()=>{if(signal?.aborted)throw abortError();const current=await assertCurrentSource();if(current===false)refuse('Native Canvas source guard refused capture.');checkViewport();if(signal?.aborted)throw abortError();};
 await checkSource();
 // Native rendering receives our detached frame, while the caller's frame is
 // checked after every asynchronous boundary before evidence can be issued.
 const ownedViewport={...viewport,width,height,transform:transform.slice()},canvas=new OffscreenCanvas(1,1),context=canvas.getContext('2d'),task=page.render({canvasContext:context,viewport:ownedViewport,background:'rgba(0,0,0,0)'});
 let Constructor,failure,accepted=false,finished=false,cancelled=false,timer,abortHandler;
 const settlement=task.promise.then(()=>({ok:true}),error=>({ok:false,error}));
 const cancel=()=>{if(!cancelled){cancelled=true;task.cancel();}};
 try{
  Constructor=await new Promise((resolve,reject)=>{
   const finish=(error,value)=>{if(finished)return;finished=true;if(error)reject(error);else resolve(value);};
   abortHandler=()=>finish(abortError());signal?.addEventListener('abort',abortHandler,{once:true});
   timer=setTimeout(()=>finish(new Error('Actual native Canvas constructor was not ready within its bounded capture window.')),LIMITS.captureMs);
   task.onContinue=()=>{try{if(signal?.aborted)throw abortError();checkViewport();const matches=[];for(const state of page._intentStates.values())for(const current of state.renderTasks||[])if(current.task===task)matches.push(current);if(matches.length!==1||matches[0].params?.canvasContext!==context||!matches[0].gfx||matches[0].gfx.ctx!==context)refuse('Native Canvas render-task ownership changed.');const candidate=matches[0].gfx.constructor;if(typeof candidate!=='function'||required.some(name=>typeof candidate.prototype[name]!=='function'))refuse('Bundled native Canvas path methods are unavailable.');accepted=true;finish(null,candidate);}catch(e){finish(e);}};
   settlement.then(result=>{if(!finished)finish(result.ok?new Error('Native Canvas render completed before constructor capture.'):result.error);});
   if(signal?.aborted)abortHandler();
  });
  checkViewport();
 }catch(error){failure=error;}
 finally{
  clearTimeout(timer);signal?.removeEventListener('abort',abortHandler);task.onContinue=null;
  try{cancel();}catch(error){if(!failure)failure=error;}
  // Every exit owns and drains this exact task, including timeout, abort, and
  // ownership refusal. A cancellation error must not replace the first error.
  const result=await settlement;
  if(!failure&&(!accepted||result.ok||result.error?.name!=='RenderingCancelledException'))failure=result.ok?new Error('Native Canvas capture did not settle by owned cancellation.'):result.error;
  try{checkViewport();}catch(error){if(!failure)failure=error;}
 }
 if(failure)throw failure;
 await checkSource();
 const methods=Object.fromEntries(required.map(name=>[name,Constructor.prototype[name]])),token=Object.freeze({});issued.set(token,{ownerKey,Constructor,methods});return token;
}
function nativeBounds(chunk,names,original,edited){
 if(!edited&&original?.args?.[2]?.length===4)return original.args[2];
 let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity,cursor=0;const values=chunk.args[1];
 for(const code of chunk.args[0]){const name=names[code];if(name==='closePath')continue;
  if(name==='rectangle'){const[x,y,w,h]=Array.from(values).slice(cursor,cursor+4);minX=Math.min(minX,x,x+w);maxX=Math.max(maxX,x,x+w);minY=Math.min(minY,y,y+h);maxY=Math.max(maxY,y,y+h);cursor+=4;}
  else if(name==='moveTo'||name==='lineTo'){const x=values[cursor++],y=values[cursor++];minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);}
  else refuse('Changed curved paths require exact native bounds before Canvas replay.');
 }
 if(cursor!==values.length||![minX,maxX,minY,maxY].every(Number.isFinite))refuse('Native Canvas path bounds are incomplete.');return [minX,maxX,minY,maxY];
}
function consume(token,ownerKey){const entry=issued.get(token);if(!entry||entry.ownerKey!==ownerKey)refuse('Native Canvas view requires its exact hidden consumer.');issued.delete(token);
 const {Constructor,methods}=entry;
 const factory=Object.freeze({createPainter(context,viewport){
  if(!context?.canvas||!Number.isSafeInteger(context.canvas.width)||!Number.isSafeInteger(context.canvas.height)||context.canvas.width*context.canvas.height>LIMITS.pixels||!matrix(Array.from(viewport?.transform||[])))refuse('Native Canvas view exceeds its bounded context envelope.');
  const resources={get(){refuse('Path-only native Canvas views cannot request font/image resources.');}},factory={create(){refuse('Unqualified native Canvas intermediate resource.');},destroy(){}};
  const graphics=new Constructor(context,resources,resources,factory,null,{optionalContentConfig:null}),call=(name,...args)=>Reflect.apply(methods[name],graphics,args);let closed=false,paints=0,pathChunks=0,clipCount=0;
  call('beginDrawing',{viewport,background:'rgba(0,0,0,0)',transparency:false});
  function construct(row,names,edited){for(let i=0;i<row.pathChunks.length;i++){const chunk=row.pathChunks[i];if(!row.pathPlaneChains?.[i]||!same(row.pathPlaneChains[i],row.transformPlanes))refuse('Native Canvas path construction/paint planes differ.');call('constructPath',chunk.args[0],chunk.args[1],nativeBounds(chunk,names,row.nativePathChunks?.[i],edited));pathChunks++;}}
  return Object.freeze({drawPath(row,clipChain,names,{placementPlanes=[]}={}){
   if(closed||row?.kind!=='path'||!Array.isArray(clipChain)||clipChain.length>LIMITS.depth||placementPlanes.length>LIMITS.depth||placementPlanes.some(value=>!matrix(value)))refuse('Native Canvas path view is closed or outside its proven profile.');
   call('save');try{
    for(const plane of placementPlanes)call('transform',...plane);
    for(const clip of clipChain){if(clip.transformPlanes.length)refuse('Native Canvas declaring clip planes need the qualified graph adapter.');construct(clip,names,false);call(clip.rule==='evenodd'?'eoClip':'clip');call('endPath');clipCount++;}
    for(const plane of row.transformPlanes)call('transform',...plane);
    const style=row.style;call('setFillRGBColor',...style.fill);call('setStrokeRGBColor',...style.stroke);call('setLineWidth',style.lineWidth);call('setLineCap',style.lineCap);call('setLineJoin',style.lineJoin);call('setMiterLimit',style.miter);
    construct(row,names,row.editedFields?.includes('pathChunks')===true);if(!methods[row.paintOperator])refuse('Unknown native path painting operation.');call(row.paintOperator);paints++;
   }finally{call('restore');}
  },clear(){if(closed)refuse('Native Canvas view is closed.');context.save();try{context.setTransform(1,0,0,1,0,0);context.clearRect(0,0,context.canvas.width,context.canvas.height);}finally{context.restore();}},close(){if(!closed){closed=true;call('endDrawing');}},statistics(){return {paints,pathChunks,clips:clipCount,constructorOrigin:'actual bundled page render task',version:VERSION};}});
 }});factories.add(factory);return factory;
}
return Object.freeze({capture,consume,isIssued:token=>issued.has(token),isFactory:value=>factories.has(value),LIMITS});
});
