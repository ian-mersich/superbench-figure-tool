/* Native editor view of a worker-owned PDF. View bitmaps and edit controls are
 * disposable; only an issued worker checkpoint is serialized into the scene. */
(function(root,factory){const cjs=typeof module==='object'&&module.exports,api=factory(
 cjs?require('./pdf-dense-document-session.js'):root.FigureStudioPdfDenseDocumentSession,
 cjs?require('./pdf-dense-native-text.js'):root.FigureStudioPdfDenseNativeText,
 cjs?require('./pdf-dense-native-proxies.js'):root.FigureStudioPdfDenseNativeProxies,
 cjs?require('../vendor/fabric/index.min.js'):root.fabric,
 cjs?require('./pdf-dense-svg-composer.js'):root.FigureStudioPdfDenseSvgComposer);
 if(cjs)module.exports=api;else root.FigureStudioPdfDensePage=api;
})(typeof globalThis==='object'?globalThis:this,function(sessions,texts,paths,fabric,svgComposer){
 'use strict';
 const SCHEMA='figureStudio.pdfDensePage.v1',registry=new Map(),pages=new WeakMap(),objectPages=new WeakMap(),sessionEntries=new WeakMap(),rasterReuseProofs=new WeakMap(),hydrations=new WeakMap();
 const replacements=new WeakMap(),replacementsBySignal=new WeakMap(),canvasRestores=new WeakMap(),canvasRestoreTargets=new WeakMap(),canvasCompletions=new WeakMap();
 const draftCaptures=new WeakMap(),assetCaptures=new WeakMap(),copies=new WeakMap(),copyHolds=new Set(),preparedCopies=new WeakMap();
 const svgPermits=new WeakMap(),composeSvg=svgComposer?.compose;
 const blobSize=Object.getOwnPropertyDescriptor(Blob.prototype,'size').get;
 const prototype=sessions?.DenseDocumentSession?.prototype,request=prototype?.request,closeSession=prototype?.close,forkSession=prototype?.fork;
 const enlivenObjects=fabric?.util?.enlivenObjects,enlivenOptions=fabric?.util?.enlivenObjectEnlivables,hasNativeClass=fabric?.classRegistry?.has,getNativeClass=fabric?.classRegistry?.getClass;
 const getters=Object.fromEntries(['source','frame','revision','statistics','currentCheckpoint','operationNames'].map(key=>[key,Object.getOwnPropertyDescriptor(prototype||{},key)?.get]));
 const supportsPointMapping=paths?.supportsPointMapping;
 const proxyPrototype=paths?.NativeProxySet?.prototype,proxySnapshot=Object.getOwnPropertyDescriptor(proxyPrototype||{},'snapshotPathEdit'),proxyCommit=Object.getOwnPropertyDescriptor(proxyPrototype||{},'commitPathEdits');
 const bitmapPrototype=typeof ImageBitmap==='function'?ImageBitmap.prototype:null,bitmapWidth=Object.getOwnPropertyDescriptor(bitmapPrototype||{},'width')?.get,
  bitmapHeight=Object.getOwnPropertyDescriptor(bitmapPrototype||{},'height')?.get,bitmapClose=Object.getOwnPropertyDescriptor(bitmapPrototype||{},'close')?.value,closedBitmaps=new WeakSet();
 const nativeEnterGroup=fabric?.Group?.prototype.enterGroup,nativeExitGroup=fabric?.Group?.prototype.exitGroup;
 const nativeSvgTransform=fabric?.FabricObject?.prototype.getSvgTransform;
 const nativeCanvasMethods=Object.fromEntries(['clear','add','remove','set','getObjects','_set','_onObjectAdded','_onObjectRemoved'].map(key=>[key,fabric?.StaticCanvas?.prototype[key]])),nativeInteractiveClear=fabric?.Canvas?.prototype.clear,
  nativeInteractiveObjectMethods=Object.fromEntries(['_onObjectAdded','_onObjectRemoved'].map(key=>[key,fabric?.Canvas?.prototype[key]]));
 const nativeConnectorText=fabric?.Text,nativeConnectorTextPrototype=fabric?.Text?.prototype,nativeGradientPrototype=fabric?.Gradient?.prototype,nativePatternPrototype=fabric?.Pattern?.prototype;
 const detachedClone=typeof structuredClone==='function'?structuredClone:null,nativeWeakRef=typeof WeakRef==='function'?WeakRef:null;
 const weakTarget=Object.getOwnPropertyDescriptor(nativeWeakRef?.prototype||{},'deref')?.value;
 const frameKeys=['backgroundImage','backgroundColor','overlayImage','overlayColor','clipPath'];
 const forbiddenCanvasKeys=new Set(['_objects','elements','__proto__','constructor','prototype','canvas','lowerCanvasEl','upperCanvasEl','contextContainer','contextTop','layoutManager','disposed','destroyed','nextRenderHandle','__eventListeners','_eventListeners','textEditingManager','_activeObject','_hoveredTarget','_hoveredTargets','_currentTransform','_groupSelector','_objectsToRender','_targetInfo','_dragSource','_draggedoverTarget','freeDrawingBrush']);
 for(let proto=fabric?.Canvas?.prototype||fabric?.StaticCanvas?.prototype;proto;proto=Object.getPrototypeOf(proto))for(const key of Object.getOwnPropertyNames(proto))if(typeof Object.getOwnPropertyDescriptor(proto,key)?.value==='function')forbiddenCanvasKeys.add(key);
 const value=(entry,key)=>Reflect.apply(getters[key],entry.session,[]),call=(entry,action,input={},options={})=>Reflect.apply(request,entry.session,[action,input,options]);
 const sameSource=(a,b)=>a?.sha256===b?.sha256&&a?.byteLength===b?.byteLength&&a?.pageNumber===b?.pageNumber;
 function fail(message){const error=new Error(message);error.code='PDF_DENSE_PAGE_REFUSED';throw error;}
 function abort(signal){if(signal?.aborted){const error=new Error('PDF page operation was cancelled.');error.name='AbortError';throw error;}}
 function cleanupAll(operations){let failed=false,failure;for(const operation of operations)try{operation();}catch(error){if(!failed){failed=true;failure=error;}}if(failed)throw failure;}
 function nativeOption(value){return value?.type&&typeof hasNativeClass==='function'&&Reflect.apply(hasNativeClass,fabric.classRegistry,[value.type]);}
 function nativeOptionKeys(records){
  const keys=new Set(['clipPath','mask','fill','stroke','shadow']),pending=records.slice(),seen=new Set();
  while(pending.length){const record=pending.pop();if(!record||typeof record!=='object'||seen.has(record))continue;seen.add(record);
   for(const key of Object.keys(record))if(key==='objects'&&Array.isArray(record[key]))pending.push(...record[key]);else if(nativeOption(record[key])){keys.add(key);pending.push(record[key]);}
  }return keys;
 }
 function verifyOptions(before,after,ownsPage=()=>true){
  const pending=[[before,after]];
  while(pending.length){const [serialized,native]=pending.pop();if(pages.has(native)){if(!ownsPage(native))fail('A serialized PDF view option could not be constructed.');continue;}
   for(const key of Object.keys(serialized)){
    if(key==='objects'&&Array.isArray(serialized[key])){
     const children=Object.getOwnPropertyDescriptor(native,'_objects')?.value;
     if(!Array.isArray(children)||children.length!==serialized[key].length)fail('A serialized PDF view option could not be constructed.');
     serialized[key].forEach((child,index)=>{if(!children[index]||children[index]===child)fail('A serialized PDF view option could not be constructed.');pending.push([child,children[index]]);});
    }else if(nativeOption(serialized[key])){if(!native[key]||native[key]===serialized[key])fail('A serialized PDF view option could not be constructed.');pending.push([serialized[key],native[key]]);}
   }
  }
 }
 function optionCleanup(values,ownsPage=()=>true,sidecarKeys=['clipPath','mask','fill','stroke','shadow'],allowsNative=()=>true,retired,disposers){
  const permitted=object=>(!pages.has(object)||ownsPage(object))&&allowsNative(object)&&!retired?.has(object),disposer=object=>disposers?disposers.get(object):object.dispose;
  const roots=[...new Set(values.filter(value=>value&&typeof disposer(value)==='function'&&permitted(value)))],owned=new Set(roots),seen=new Set(),pending=roots.slice();
  while(pending.length){const object=pending.pop();if(seen.has(object)||pages.has(object))continue;seen.add(object);
   // Native Group disposal owns painted descendants, but not their clips or
   // other enlivable sidecars. Keep those separate, never the live source view.
   for(const key of sidecarKeys){const value=Object.getOwnPropertyDescriptor(object,key)?.value;if(value&&typeof disposer(value)==='function'&&permitted(value)&&!owned.has(value)){owned.add(value);roots.push(value);pending.push(value);}}
   const children=Object.getOwnPropertyDescriptor(object,'_objects')?.value;if(Array.isArray(children))for(const child of children)if(child&&typeof disposer(child)==='function'&&permitted(child)&&!owned.has(child)){owned.add(child);roots.push(child);pending.push(child);}
  }
  const operations=roots.map(object=>({object,dispose:disposer(object)}));let closed=false;
  return()=>{
   if(closed)return;closed=true;let failed=false,failure;const installed=[],collections=[];
   const remember=error=>{if(!failed){failed=true;failure=error;}};
   for(const operation of operations)operation.once=()=>{if(operation.called)return;operation.called=true;if(!permitted(operation.object))return;retired?.add(operation.object);try{Reflect.apply(operation.dispose,operation.object,[]);}catch(error){remember(error);}};
   const active=operations.filter(operation=>{if(permitted(operation.object))return true;operation.called=true;return false;});
   try{
    // A foreign constructor must not gain disposal authority over a borrowed
    // private Page. Only newly owned containers are filtered during retirement;
    // the borrowed Page and its methods/parents are never changed here.
    for(const {object} of active){if(pages.has(object))continue;const children=Object.getOwnPropertyDescriptor(object,'_objects')?.value;if(Array.isArray(children)&&children.some(child=>!permitted(child))){collections.push({object,children});object._objects=children.filter(permitted);}}
    // Stock Group.dispose stops at a throwing painted child. Only during this
    // synchronous retirement of newly owned options, let each captured native
    // disposer run once and collect errors so siblings and sidecars also retire.
    for(const operation of active){const descriptor=Object.getOwnPropertyDescriptor(operation.object,'dispose');try{Object.defineProperty(operation.object,'dispose',{value:operation.once,writable:true,configurable:true});installed.push({object:operation.object,descriptor});}catch(error){remember(error);}}
    for(const operation of operations)operation.once();
   }finally{for(const {object,descriptor} of installed)try{if(descriptor)Object.defineProperty(object,'dispose',descriptor);else delete object.dispose;}catch(error){remember(error);}for(const {object,children} of collections)try{object._objects=children;}catch(error){remember(error);}}
   if(failed)throw failure;
  };
 }
 function entryFor(id){const entry=registry.get(id);if(!entry||!sessions.isSession(entry.session))fail('The PDF source owner is unavailable.');return entry;}
 function dataFor(page){const data=pages.get(page);if(!data||data.disposed||registry.get(data.entry.id)!==data.entry||!sessions.isSession(data.entry.session))fail('The PDF page view is closed or foreign.');return data;}
 function bitmapSize(bitmap){try{if(typeof bitmapWidth!=='function'||typeof bitmapHeight!=='function'||typeof bitmapClose!=='function')return null;return [Reflect.apply(bitmapWidth,bitmap,[]),Reflect.apply(bitmapHeight,bitmap,[])];}catch{return null;}}
 function closeBitmap(bitmap){if(!bitmap||closedBitmaps.has(bitmap))return;closedBitmaps.add(bitmap);const size=bitmapSize(bitmap);if(size){if(size[0]>0&&size[1]>0)Reflect.apply(bitmapClose,bitmap,[]);}else bitmap.close?.();}
 function sourceHost(frame){return texts.createSourceHost({frame});}
 function ownedBitmaps(data){return (data.renderBinding?.tile===data.tile?data.renderBinding.segments:data.tile?.segments||[]).map(segment=>segment.bitmap).filter(Boolean);}
 function liveNativeGraph(canvas,{excludeDisposedPageOptions=false,custody}={}){
  const result=new Set(),pending=(canvas._objects||[]).map(value=>({value,depth:0}));for(const key of frameKeys)pending.push({value:canvas[key],depth:0});
  while(pending.length){const {value:object,depth}=pending.pop();if(!object||typeof object!=='object'||result.has(object))continue;
   if(depth>48||result.size>=100000)fail('The native scene exceeds the document tree limit.');result.add(object);custody?.knownNative.add(object);
   if(!pages.has(object)){const children=Object.getOwnPropertyDescriptor(object,'_objects')?.value;if(Array.isArray(children))for(const child of children){rememberNativeOwner(custody,child,object,'_objects');pending.push({value:child,depth:depth+1});}}
   if(excludeDisposedPageOptions&&pages.get(object)?.disposed)continue;
   for(const key of Object.keys(object)){if(['canvas','group','parent','layoutManager','_objects'].includes(key))continue;const descriptor=Object.getOwnPropertyDescriptor(object,key);if(!descriptor||!Object.hasOwn(descriptor,'value'))continue;
    const child=descriptor.value;if(child&&typeof child==='object'&&(nativeOption(child)||['clipPath','mask'].includes(key))){rememberNativeOwner(custody,child,object,key);pending.push({value:child,depth:depth+1});}}
  }return result;
 }
 function nativeCustody(canvas){return nativeWeakRef&&typeof weakTarget==='function'?{targetRef:new nativeWeakRef(canvas),knownNative:new WeakSet(),owners:new WeakMap(),admissionClosed:true,unknownCustody:false}:null;}
 function rememberNativeOwner(custody,child,parent,key){
  if(!custody||!child||typeof child!=='object')return;
  let rows=custody.owners.get(child);if(!rows){rows=[];custody.owners.set(child,rows);}
  // Weak parents and literal current-edge checks retain no old scene snapshot.
  if(!rows.some(row=>row.key===key&&Reflect.apply(weakTarget,row.parent,[])===parent))rows.push({parent:new nativeWeakRef(parent),key});
 }
 function rememberInitialNativeParents(custody,objects){
  if(!custody)return;const pending=[...objects].map(object=>({object,depth:0})),seen=new Set();
  while(pending.length){const {object,depth}=pending.pop();if(seen.has(object))continue;
   if(depth>48||seen.size>=100000){custody.unknownCustody=true;return;}seen.add(object);
   for(const key of ['group','parent']){
    const descriptor=Object.getOwnPropertyDescriptor(object,key),parent=descriptor&&Object.hasOwn(descriptor,'value')?descriptor.value:null;
    if(!(parent instanceof fabric.Group))continue;const children=Object.getOwnPropertyDescriptor(parent,'_objects');
    if(!children||!Object.hasOwn(children,'value')||!Array.isArray(children.value)||!children.value.includes(object))continue;
    // Only begin's verified pre-existing ancestry becomes known. Later parents
    // still need the dynamic external-custody check and gain no old ownership.
    custody.knownNative.add(parent);rememberNativeOwner(custody,object,parent,'_objects');pending.push({object:parent,depth:depth+1});
   }
  }
 }
 function externallyOwnedNative(custody,object,live){
  if(!custody)return true;const canvas=Reflect.apply(weakTarget,custody.targetRef,[]);
  const unknown=()=>{custody.unknownCustody=true;return true;};if(!canvas)return unknown();
  try{
   live ||= liveNativeGraph(canvas,{excludeDisposedPageOptions:true});const active=new Set(),completed=new Map();let count=0;
   const visit=(value,depth)=>{
    if(!value||typeof value!=='object'||pages.get(value)?.disposed)return false;
    if(depth>48||++count>100000)return unknown();if(live.has(value))return true;
    if(active.has(value))return unknown();if(completed.has(value))return completed.get(value);active.add(value);
    let protectedOwner=false;
    const nativeCanvas=Object.getOwnPropertyDescriptor(value,'canvas');
    if(nativeCanvas&&!Object.hasOwn(nativeCanvas,'value'))protectedOwner=unknown();
    else if(nativeCanvas?.value&&nativeCanvas.value!==canvas)protectedOwner=unknown();
    const follow=(parent,key)=>{
     if(!parent||typeof parent!=='object'||pages.get(parent)?.disposed)return false;
     const descriptor=Object.getOwnPropertyDescriptor(parent,key);
     if(!descriptor)return false;if(!Object.hasOwn(descriptor,'value'))return unknown();
     const current=key==='_objects'?Array.isArray(descriptor.value)&&descriptor.value.includes(value):descriptor.value===value;
     if(!current)return false;
     // A detached outer constructor may not have returned yet. Its mere parent
     // pointer is not foreign ownership until complete native admission.
     if(custody.admissionClosed&&!custody.knownNative.has(parent)&&!live.has(parent))return unknown();
     return visit(parent,depth+1);
    };
    for(const key of ['group','parent']){
     const descriptor=Object.getOwnPropertyDescriptor(value,key);
     if(descriptor&&!Object.hasOwn(descriptor,'value'))protectedOwner=unknown();
     else if(descriptor?.value&&follow(descriptor.value,'_objects'))protectedOwner=true;
    }
    for(const row of custody.owners.get(value)||[]){const parent=Reflect.apply(weakTarget,row.parent,[]);if(follow(parent,row.key))protectedOwner=true;}
    active.delete(value);completed.set(value,protectedOwner);return protectedOwner;
   };
   return visit(object,0);
  }catch{return unknown();}
 }
 function scenePages(canvas){return new Set([...liveNativeGraph(canvas)].filter(object=>pages.has(object)));}
 function beginSceneReplacement(canvas){
  if(!(canvas instanceof fabric.StaticCanvas))fail('PDF scene replacement requires its actual native canvas.');
  const controller=new AbortController(),scope=Object.freeze({signal:controller.signal}),custody=nativeCustody(canvas),before=registry.size?liveNativeGraph(canvas,{custody}):new Set(),data={canvas,controller,custody,candidates:new Set([...before].filter(object=>pages.has(object))),createdCandidates:new Set()};
  rememberInitialNativeParents(custody,before);replacements.set(scope,data);replacementsBySignal.set(controller.signal,data);canvasRestoreTargets.set(canvas,data);return scope;
 }
 function finishSceneReplacement(scope){
  const data=replacements.get(scope);if(!data)fail('PDF scene replacement is foreign or already settled.');
  if(data.canvasRestore)fail('The prepared native canvas must be committed or discarded before settlement.');
  replacements.delete(scope);replacementsBySignal.delete(data.controller.signal);if(canvasRestoreTargets.get(data.canvas)===data)canvasRestoreTargets.delete(data.canvas);data.controller.abort();
  if(!data.candidates.size)return;
  const live=scenePages(data.canvas);cleanupAll(Array.from(data.candidates).filter(page=>!live.has(page)&&!pages.get(page)?.disposed).map(page=>()=>{if(!pages.get(page)?.disposed&&!externallyOwnedNative(data.custody,page))page.dispose();}));
 }
 function mapTree(page,object){objectPages.set(object,page);for(const child of object._objects||[])mapTree(page,child);if(object.clipPath)mapTree(page,object.clipPath);}
 function retire(page,data,{keepBitmaps=false}={}){
  let cleanupError,failed=false;const attempt=operation=>{try{operation();}catch(error){if(!failed){failed=true;cleanupError=error;}}};
  for(const child of page._objects.slice())attempt(()=>Reflect.apply(nativeExitGroup,page,[child,true]));page._objects=[];
  attempt(()=>texts.close(data.textOwner));data.textOwner=null;attempt(()=>data.proxies?.close());data.proxies=null;
  for(const host of data.hosts)attempt(()=>{host._objects=[];host.dispose();});data.hosts=[];
  for(const image of data.images)attempt(()=>image.dispose());data.images=[];
  if(!keepBitmaps){for(const bitmap of ownedBitmaps(data))attempt(()=>closeBitmap(bitmap));data.tile=null;data.renderBinding=null;}
  if(failed)throw cleanupError;
 }
 function serialDescriptor(entry){return {schema:SCHEMA,assetId:entry.id,source:value(entry,'source'),stateId:value(entry,'currentCheckpoint').stateId};}
 class PdfDensePage extends fabric.Group{
  static type='PdfDensePage';
  get type(){return 'group';}
  constructor(options={}){
   super([],{...options,strokeWidth:0,objectCaching:false,subTargetCheck:true,interactive:true,layoutManager:new fabric.LayoutManager(new fabric.FixedLayout())});
  }
  // Generic scene walks must never mistake cached pixels or temporary controls
  // for canonical document children. Semantic children are read from the worker.
  getObjects(){return [];}
  setCoords(){super.setCoords();for(const child of this._objects||[])child.setCoords();}
  toObject(properties=[]){
   // Cooperative scene capture realizes an ActiveSelection through a facade
   // inheriting from this exact owner. Only serialization accepts that facade.
   let owner=this;while(owner&&!pages.has(owner))owner=Object.getPrototypeOf(owner);const data=dataFor(owner);
   const result={...Reflect.apply(fabric.FabricObject.prototype.toObject,this,[properties]),type:PdfDensePage.type,densePdf:{...serialDescriptor(data.entry),viewPathIds:data.pathIds.slice()}};
   for(const key of ['left','top','width','height','strokeWidth','strokeDashOffset','strokeMiterLimit','scaleX','scaleY','angle','opacity','skewX','skewY'])if(Number.isFinite(this[key]))result[key]=this[key];
   return result;
  }
  _toSVG(){
   let owner=this,depth=0;while(owner&&!pages.has(owner)&&++depth<=48)owner=Object.getPrototypeOf(owner);
   const permit=svgPermits.get(owner);if(!permit||!canSerializeSvg(owner))fail('PDF artwork must be exported through its canonical vector writer scope.');
   if(++permit.emitted>1)fail('Repeated PDF appearance effects require a separately qualified SVG export.');
   return ['<g ','COMMON_PARTS','><g data-figure-dense-svg-slot="',permit.token,'"></g></g>'];
  }
  toClipPathSVG(){fail('PDF artwork cannot currently be used as an SVG clipping mask.');}
  async clone(properties=[]){const prepared=await prepareSceneCopy([this],{properties});try{commitSceneCopy(prepared);return prepared.objects[0];}catch(error){try{discardSceneCopy(prepared);}catch{}throw error;}}
  dispose(){const data=pages.get(this);let cleanupError,failed=false;if(data&&!data.disposed){data.disposed=true;data.refreshEpoch++;data.controller?.abort();const release=data.releaseOptions;data.releaseOptions=null;try{cleanupAll([()=>retire(this,data),()=>release?.()]);}catch(error){failed=true;cleanupError=error;}finally{data.entry.views.delete(this);}}let result;try{result=super.dispose();}catch(error){if(!failed){failed=true;cleanupError=error;}}if(failed)throw cleanupError;return result;}
  static async fromObject(object,{signal}={}){
   const descriptor=object?.densePdf;
   if(descriptor?.schema!==SCHEMA||typeof descriptor.assetId!=='string'||typeof descriptor.stateId!=='string')fail('The saved PDF view descriptor is incomplete.');
   const entry=entryFor(descriptor.assetId);if(!sameSource(descriptor.source,value(entry,'source')))fail('The saved PDF view refers to different source bytes.');
   const stateId=entry.coldAliases.get(descriptor.stateId)||descriptor.stateId;
   const restoring=replacementsBySignal.get(signal)?.canvasRestore;
    if(restoring){restoring.current();const pin=restoring.pins.get(entry);if(!pin||restoring.states.get(entry)!==stateId)fail('The saved PDF view has no private restoration join.');
     if(value(entry,'currentCheckpoint').stateId!==stateId){const acknowledged=await call(entry,'goToState',{stateId},{signal});restoring.current(entry);
      if(!sameCopyValue(acknowledged?.source,pin.source)||acknowledged?.revision!==value(entry,'revision')||!sameCopyValue(acknowledged?.result?.checkpoint,value(entry,'currentCheckpoint'))||acknowledged.result.checkpoint.stateId!==stateId)fail('The PDF history acknowledgement changed during restoration.');
      restoring.pins.set(entry,{...pin,revision:acknowledged.revision,checkpoint:canvasInputCopy(acknowledged.result.checkpoint)});restoring.current();}
    }else if(value(entry,'currentCheckpoint').stateId!==stateId)await call(entry,'goToState',{stateId},{signal});
   const {type,densePdf,objects,layoutManager,...options}=object;
   if(!Object.values(options).some(nativeOption))return build(entry,object,{signal});
   if(typeof enlivenOptions!=='function')fail('Native PDF view option construction is unavailable.');
   const revision=value(entry,'revision'),checkpoint=value(entry,'currentCheckpoint'),source=value(entry,'source'),session=entry.session;
   const optionScope=replacementsBySignal.get(signal),canvasCleanup=optionScope?.canvasRestore?.cleanupContext||optionScope?.copyRetirement?.context,optionPool=canvasCleanup?optionScope.createdCandidates:optionScope?.candidates,priorOptions=optionPool?new Set(optionPool):null;
   let ownsOptionPage=page=>!optionScope||(optionPool.has(page)&&!priorOptions.has(page));
   if(checkpoint.stateId!==stateId)fail('The PDF source changed before its native options could be constructed.');
   const current=()=>{abort(signal);if(registry.get(descriptor.assetId)!==entry||entry.session!==session||!sessions.isSession(session)||!sameSource(source,value(entry,'source'))
     ||value(entry,'revision')!==revision||value(entry,'currentCheckpoint').stateId!==checkpoint.stateId
     ||value(entry,'currentCheckpoint').documentRevision!==checkpoint.documentRevision||value(entry,'currentCheckpoint').leafRevision!==checkpoint.leafRevision)fail('The PDF source changed while its native options were being constructed.');};
   let page,release;
   try{
    const native=await Reflect.apply(enlivenOptions,fabric.util,[options,{signal}]),ownedValues=Object.keys(native).filter(key=>native[key]!==options[key]).map(key=>native[key]);
    if(canvasCleanup){const ownedOptions=new Set([...liveNativeGraph({_objects:ownedValues},{custody:canvasCleanup.custody})].filter(page=>pages.has(page)&&optionPool.has(page)&&!priorOptions.has(page)));ownsOptionPage=optionMembership(ownedOptions);}
    canvasCleanup?.retainCopyNative?.(ownedValues);
    release=optionCleanup(ownedValues,ownsOptionPage,nativeOptionKeys([options]),canvasCleanup?.allowsNative,canvasCleanup?.retired,canvasCleanup?.copyDisposers);
    current();verifyOptions(options,native,ownsOptionPage);
    page=await build(entry,{...native,densePdf},{signal});current();dataFor(page).releaseOptions=release;release=null;return page;
   }catch(error){try{page?.dispose();}catch{}try{release?.();}catch{}throw error;}
  }
 }
 const nativePageSvgWriter=PdfDensePage.prototype._toSVG,nativePageClipWriter=PdfDensePage.prototype.toClipPathSVG;
 const copyDisposeRows=[],copyDisposeMethods=new Set();
 for(const prototype of [fabric.FabricObject?.prototype,fabric.Group?.prototype,fabric.FabricImage?.prototype,fabric.Text?.prototype,fabric.IText?.prototype,fabric.Textbox?.prototype,PdfDensePage.prototype]){let current=prototype,depth=0;while(current&&++depth<=48){const descriptor=Object.getOwnPropertyDescriptor(current,'dispose');if(!copyDisposeRows.some(row=>row.prototype===current))copyDisposeRows.push({prototype:current,parent:Object.getPrototypeOf(current),descriptor});if(descriptor){if(Object.hasOwn(descriptor,'value')&&typeof descriptor.value==='function')copyDisposeMethods.add(descriptor.value);break;}current=Object.getPrototypeOf(current);}}
 function currentCopyDisposal(){for(const row of copyDisposeRows){const current=Object.getOwnPropertyDescriptor(row.prototype,'dispose'),before=row.descriptor;if(Object.getPrototypeOf(row.prototype)!==row.parent||(!before?current!==undefined:!current||!Object.hasOwn(before,'value')||typeof before.value!=='function'||Reflect.ownKeys(before).length!==Reflect.ownKeys(current).length||Reflect.ownKeys(before).some(key=>!Object.is(before[key],current[key]))))fail('Prepared view retirement requires unchanged synchronous native disposal.');}}
 function exactDataMethod(object,key,expected){let depth=0;while(object&&++depth<=48){const descriptor=Object.getOwnPropertyDescriptor(object,key);if(descriptor)return Object.hasOwn(descriptor,'value')&&descriptor.value===expected;object=Object.getPrototypeOf(object);}return false;}
 function currentProxyDispatch(owner){
  const unchanged=(key,before)=>{const now=Object.getOwnPropertyDescriptor(proxyPrototype||{},key);return before&&Object.hasOwn(before,'value')&&typeof before.value==='function'&&now&&Reflect.ownKeys(before).every(field=>Object.is(before[field],now[field]))&&exactDataMethod(owner,key,before.value);};
  if(!proxyPrototype||Object.getPrototypeOf(owner)!==proxyPrototype||!unchanged('snapshotPathEdit',proxySnapshot)||!unchanged('commitPathEdits',proxyCommit))fail('The native PDF point dispatcher changed.');
 }
 // These are detached plain records from captured Session getters, never a
 // saved scene or a caller-supplied proof. Preserve every numeric value.
 function copyRasterState(value){return Array.isArray(value)?value.map(copyRasterState):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).map(key=>[key,copyRasterState(value[key])])):value;}
 function rasterBinding(data,tile){
  return {entry:data.entry,session:data.entry.session,tile,source:copyRasterState(value(data.entry,'source')),checkpoint:copyRasterState(value(data.entry,'currentCheckpoint')),
   revision:value(data.entry,'revision'),frame:copyRasterState(value(data.entry,'frame')),scale:data.scale,ids:data.pathIds.slice(),
   segments:tile.segments.map(segment=>({segment,kind:segment.kind,startOrdinal:segment.startOrdinal,endOrdinal:segment.endOrdinal,record:segment.record,id:segment.record?.id,paintOrdinal:segment.record?.paintOrdinal,bitmap:segment.bitmap,size:segment.bitmap?bitmapSize(segment.bitmap):null})),count:tile.canonicalPaintCount};
 }
 function currentRasterBinding(data,binding,{head=true}={}){
  if(!binding||binding!==data.renderBinding||data.disposed||binding.entry!==data.entry||binding.session!==data.entry.session||binding.tile!==data.tile||binding.revision!==data.renderRevision
   ||binding.scale!==data.scale||!sameCopyValue(binding.frame,value(data.entry,'frame'))||!sameCopyValue(binding.source,value(data.entry,'source'))
   ||binding.ids.length!==data.pathIds.length||binding.ids.some((id,index)=>id!==data.pathIds[index])||!Array.isArray(data.tile?.segments)||binding.count!==data.tile.canonicalPaintCount||binding.segments.length!==data.tile.segments.length)return false;
  if(head&&(binding.revision!==value(data.entry,'revision')||!sameCopyValue(binding.checkpoint,value(data.entry,'currentCheckpoint'))))return false;
  const slots=new Set();
  for(let index=0;index<binding.segments.length;index++){
   const before=binding.segments[index],segment=data.tile.segments[index];
   if(!segment||before.segment!==segment||before.kind!==segment.kind||before.startOrdinal!==segment.startOrdinal||before.endOrdinal!==segment.endOrdinal||before.record!==segment.record
    ||before.id!==segment.record?.id||before.paintOrdinal!==segment.record?.paintOrdinal||before.bitmap!==segment.bitmap)return false;
   if(segment.kind==='nativePath'){if(slots.has(before.id)||!binding.ids.includes(before.id))return false;slots.add(before.id);}
   if(before.bitmap){const size=bitmapSize(before.bitmap);if(!size||!before.size||size[0]<=0||size[1]<=0||size.some((value,index)=>value!==before.size[index])||closedBitmaps.has(before.bitmap)
    ||Object.getPrototypeOf(before.bitmap)!==bitmapPrototype||Reflect.ownKeys(before.bitmap).length||Object.getOwnPropertyDescriptor(bitmapPrototype,'width')?.get!==bitmapWidth
    ||Object.getOwnPropertyDescriptor(bitmapPrototype,'height')?.get!==bitmapHeight||Object.getOwnPropertyDescriptor(bitmapPrototype,'close')?.value!==bitmapClose)return false;}
  }
  return slots.size===binding.ids.length;
 }
 function currentSvgWriters(object){return exactDataMethod(object,'_toSVG',nativePageSvgWriter)&&exactDataMethod(object,'toClipPathSVG',nativePageClipWriter)&&exactDataMethod(object,'getSvgTransform',nativeSvgTransform);}
 function canSerializeSvg(object){const data=pages.get(object);return Boolean(data&&!data.disposed&&registry.get(data.entry.id)===data.entry&&sessions.isSession(data.entry.session)&&svgPermits.has(object)&&currentSvgWriters(object));}
 async function exportSceneSvg(roots,buildShell,{signal,assertCurrent=()=>{}}={}){
  abort(signal);if(!Array.isArray(roots)||roots.length>10000||roots.some(object=>!(object instanceof fabric.FabricObject))||typeof buildShell!=='function'||typeof assertCurrent!=='function')fail('Canonical SVG export requires actual native artwork and a synchronous shell writer.');
  const sourceRows=[],guarded=new Map(),seen=new Set(),pending=roots.map(object=>({object,clip:false,depth:0}));
  const stateOf=object=>({group:object.group,parent:object.parent,matrix:Array.from(object.calcOwnMatrix()),width:object.width,height:object.height,opacity:object.opacity,visible:object.visible,excludeFromExport:object.excludeFromExport,clipPath:object.clipPath,mask:object.mask,fill:object.fill,stroke:object.stroke,strokeWidth:object.strokeWidth,shadow:object.shadow,globalCompositeOperation:object.globalCompositeOperation});
  const guardNode=object=>{if(!guarded.has(object))guarded.set(object,stateOf(object));};
  while(pending.length){const {object,clip,depth}=pending.pop();if(!object)continue;if(depth>48||seen.size>=100000)fail('The SVG scene exceeds its native ownership envelope.');
   if(pages.has(object)&&clip)fail('PDF artwork cannot currently be used as an SVG clipping mask.');
   if(seen.has(object))continue;seen.add(object);
   if(clip)guardNode(object);
   if(pages.has(object)){
    const data=dataFor(object),entry=data.entry,frame=value(entry,'frame');
    if(sourceRows.length>=8||svgPermits.has(object)||!currentSvgWriters(object))fail('A distinct current native PDF SVG writer is required.');
    if(!Number.isFinite(frame.width)||frame.width<=0||!Number.isFinite(frame.height)||frame.height<=0)fail('The canonical PDF source frame is invalid.');
    sourceRows.push({page:object,data,entry,revision:value(entry,'revision'),checkpoint:value(entry,'currentCheckpoint').stateId,frame:{width:frame.width,height:frame.height},token:crypto.randomUUID(),emitted:0});
    let ancestor=object,level=0;while(ancestor){if(++level>48)fail('The native PDF parent hierarchy exceeds its SVG envelope.');guardNode(ancestor);if(ancestor.clipPath)pending.push({object:ancestor.clipPath,clip:true,depth:level});if(ancestor.mask)pending.push({object:ancestor.mask,clip:true,depth:level});ancestor=ancestor.group;}
   }else{
    if(objectPages.has(object))fail('Export the PDF page rather than a disposable native editing control.');
    for(const child of object._objects||[])pending.push({object:child,clip,depth:depth+1});
   }
   if(object.clipPath)pending.push({object:object.clipPath,clip:true,depth:depth+1});if(object.mask)pending.push({object:object.mask,clip:true,depth:depth+1});
  }
  const drafts=captureDrafts(sourceRows.flatMap(row=>row.data.textOwner.entries.map(entry=>entry.object)),{signal});
  const current=()=>{
   abort(signal);assertCurrent();validateDraftCapture(drafts,{signal});
   for(const row of sourceRows){const frame=value(row.entry,'frame');if(dataFor(row.page)!==row.data||value(row.entry,'revision')!==row.revision||value(row.entry,'currentCheckpoint').stateId!==row.checkpoint||frame.width!==row.frame.width||frame.height!==row.frame.height||row.data.renderRevision!==row.revision||!currentSvgWriters(row.page))fail('The PDF artwork changed during SVG export.');}
   for(const [object,before]of guarded){const after=stateOf(object);if(!Object.keys(before).every(key=>key==='matrix'?sameCopyValue(before.matrix,after.matrix):Object.is(before[key],after[key])))fail('The artwork placement or clipping changed during SVG export.');}
  };
  current();let shell;
  try{for(const row of sourceRows)svgPermits.set(row.page,row);shell=buildShell();if(typeof shell!=='string'){if(shell&&typeof shell==='object')Promise.resolve(shell).catch(()=>{});fail('Canonical SVG export requires a synchronous small shell writer.');}}
  finally{for(const row of sourceRows)if(svgPermits.get(row.page)===row)svgPermits.delete(row.page);}
  current();let inputBytes=new TextEncoder().encode(shell).length;if(inputBytes>8388608)fail('The SVG shell exceeds its existing eight MiB composition limit.');
  const emitted=sourceRows.filter(row=>row.emitted),slots=[];
  if(!emitted.length)return new Blob([shell],{type:'image/svg+xml'});
  if(typeof composeSvg!=='function')fail('Canonical SVG file composition is unavailable.');
  for(const row of emitted){current();const exported=await call(row.entry,'exportSvg',{}, {signal});current();const svgBlob=exported.result.blob;let size;try{size=Reflect.apply(blobSize,svgBlob,[]);}catch{fail('The canonical PDF writer did not return an immutable SVG Blob.');}inputBytes+=size;if(!size||inputBytes>268435456)fail('Canonical SVG inputs exceed their existing cumulative composition limit.');slots.push({token:row.token,svgBlob,frame:row.frame});}
  const blob=await Reflect.apply(composeSvg,svgComposer,[{shellSvg:shell,slots},{signal}]);current();return blob;
 }
 fabric.classRegistry.setClass(PdfDensePage);
 async function refresh(page,{signal,rasterReuseProof}={}){
  const data=dataFor(page),entry=data.entry,revision=value(entry,'revision'),frame=value(entry,'frame');abort(signal);
  if(data.refreshing)fail('Finish updating the current PDF page first.');
  const reuse=rasterReuseProofs.get(rasterReuseProof),reusePathBitmaps=Boolean(reuse&&reuse.page===page&&reuse.tile===data.tile&&reuse.fromRevision===data.renderRevision&&reuse.toRevision===revision
   &&reuse.ids.length===data.pathIds.length&&reuse.ids.every((id,index)=>id===data.pathIds[index])
   &&(!reuse.binding||reuse.data===data&&reuse.entry===entry&&reuse.session===entry.session&&currentRasterBinding(data,reuse.binding,{head:false})&&sameCopyValue(reuse.toCheckpoint,value(entry,'currentCheckpoint'))));
  if(rasterReuseProof)rasterReuseProofs.delete(rasterReuseProof);
  data.refreshing=true;
  const epoch=++data.refreshEpoch,controller=new AbortController(),cancel=()=>controller.abort();data.controller=controller;
  signal?.addEventListener('abort',cancel,{once:true});if(signal?.aborted)controller.abort();
  const current=()=>{abort(controller.signal);if(dataFor(page)!==data||data.refreshEpoch!==epoch||value(entry,'revision')!==revision)fail('The PDF page changed or closed while its view was being built.');};
  let textOwner,tile,newTile=false;const hosts=[],images=[],children=[],previousBitmaps=new Set(ownedBitmaps(data));
  try{
   textOwner=await texts.create({session:entry.session,signal:controller.signal});current();
   tile=reusePathBitmaps&&data.tile&&(!reuse.binding||currentRasterBinding(data,reuse.binding,{head:false}))?data.tile:(await call(entry,'renderTile',{scale:data.scale,splitNativeText:true,splitIds:data.pathIds},{signal:controller.signal})).result;newTile=tile!==data.tile;current();
   if(newTile&&tile.segments.some(segment=>segment.bitmap&&previousBitmaps.has(segment.bitmap)))fail('A new PDF raster result cannot borrow the preceding view bitmap.');
   const entries=new Map(textOwner.entries.map(row=>[row.id,row])),proxies=paths.create({session:entry.session}),nativePaths=new Map();
   try{for(const id of data.pathIds){nativePaths.set(id,await proxies.acquirePath(id,{signal:controller.signal}));current();}}
   catch(error){try{proxies.close();}catch{}throw error;}
   // Prepare children under their final native parent without publishing them
   // in its drawing collection. This keeps adopted source parent identities
   // stable and leaves the preceding completed composition visible until ready.
   const prepare=object=>{children.push(object);Reflect.apply(nativeEnterGroup,page,[object,false]);};
   let cursor=0;
   try{
    if(reuse?.binding&&tile===data.tile&&!currentRasterBinding(data,reuse.binding,{head:false})){
     tile=(await call(entry,'renderTile',{scale:data.scale,splitNativeText:true,splitIds:data.pathIds},{signal:controller.signal})).result;newTile=tile!==data.tile;current();
     if(!newTile||tile.segments.some(segment=>segment.bitmap&&previousBitmaps.has(segment.bitmap)))fail('A new PDF raster result cannot borrow the preceding view bitmap.');
    }
    for(const segment of tile.segments){
     if(segment.kind==='paths'){
      if(segment.startOrdinal!==cursor||segment.endOrdinal<cursor)fail('The complete PDF paint order changed.');cursor=segment.endOrdinal;
      if(segment.bitmap){const image=new fabric.FabricImage(segment.bitmap,{left:-frame.width/2,top:-frame.height/2,originX:'left',originY:'top',scaleX:1/data.scale,scaleY:1/data.scale,
       objectCaching:false,selectable:false,evented:false,excludeFromExport:true});images.push(image);prepare(image);}
     }else{
      const row=segment.record;if(row.paintOrdinal!==cursor)fail('A native PDF control is out of source paint order.');cursor++;
      const host=sourceHost(frame);hosts.push(host);prepare(host);
      if(segment.kind==='nativeText'){
       if(!entries.has(row.id))fail('A source text paint has no complete native text owner.');texts.adopt(textOwner,row.id,host);entries.delete(row.id);
      }else if(segment.kind==='nativePath')proxies.adoptHost(nativePaths.get(row.id),host);
      else fail('An unknown disposable PDF view slot was returned.');
     }
    }
    if(cursor!==tile.canonicalPaintCount||entries.size)fail('The native page view omitted canonical source paints.');
    current();if(reuse?.binding&&tile===data.tile&&!currentRasterBinding(data,reuse.binding,{head:false}))fail('The retained PDF bitmap changed before view publication.');
    const nextBinding=rasterBinding(data,tile);
    retire(page,data,{keepBitmaps:!newTile});
    page._objects=children;for(const child of children)mapTree(page,child);
    data.textOwner=textOwner;textOwner=null;data.proxies=proxies;data.hosts=hosts;data.images=images;data.tile=tile;data.renderRevision=revision;
    page.dirty=true;page.setCoords();page.canvas?.requestRenderAll();data.renderBinding=nextBinding;return page;
   }catch(error){try{proxies.close();}catch{}throw error;}
  }catch(error){try{cleanupAll([()=>texts.close(textOwner),...children.map(child=>()=>Reflect.apply(nativeExitGroup,page,[child,true])),...hosts.map(host=>()=>{host._objects=[];host.dispose();}),...images.map(image=>()=>image.dispose()),...(newTile?(tile?.segments||[]).filter(segment=>!previousBitmaps.has(segment.bitmap)).map(segment=>()=>closeBitmap(segment.bitmap)):[])]);}catch{}throw error;}
  finally{signal?.removeEventListener('abort',cancel);if(data.controller===controller)data.controller=null;data.refreshing=false;}
 }
 async function build(entry,options={},control={}){
  const {type,densePdf,objects,layoutManager,...nativeOptions}=options;
  const frame=value(entry,'frame'),page=new PdfDensePage({...nativeOptions,width:frame.width,height:frame.height,
   left:options.left??0,top:options.top??0,originX:options.originX||'left',originY:options.originY||'top',name:options.name||'PDF page',figureType:'pdf'});
  const pathIds=options.densePdf?.viewPathIds||[];
  if(!Array.isArray(pathIds)||pathIds.length>paths.LIMIT||new Set(pathIds).size!==pathIds.length||pathIds.some(id=>typeof id!=='string'||id.length>256))fail('Saved PDF edit-control IDs exceed the native view envelope.');
  const data={entry,scale:2,pathIds:pathIds.slice(),textOwner:null,proxies:null,tile:null,hosts:[],images:[],disposed:false,refreshing:false,refreshEpoch:0,controller:null,renderRevision:null,renderBinding:null};pages.set(page,data);entry.views.add(page);objectPages.set(page,page);
  const replacement=replacementsBySignal.get(control.signal);replacement?.candidates.add(page);replacement?.createdCandidates?.add(page);
  try{return await refresh(page,control);}catch(error){try{page.dispose();}catch{}throw error;}
 }
 async function create({session,bytes,options={},signal,assetId}={}){
  if(!sessions.isSession(session)||!(bytes instanceof Uint8Array)||!bytes.length||bytes.length>33554432)fail('A native PDF page needs its completed actual-byte document owner.');
  const captured=bytes.slice(),sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',captured)),v=>v.toString(16).padStart(2,'0')).join('');abort(signal);
  const source=Reflect.apply(getters.source,session,[]);if(source.sha256!==sha||source.byteLength!==captured.length)fail('The native PDF page source differs from its worker owner.');
  const id=assetId||crypto.randomUUID();if(registry.has(id)||sessionEntries.has(session)||typeof id!=='string'||id.length>128)fail('The PDF source owner ID or session is duplicate or invalid.');
  const entry={id,session,bytes:captured,views:new Set(),coldAliases:new Map()};registry.set(id,entry);sessionEntries.set(session,entry);
  try{return await build(entry,options,{signal});}catch(error){registry.delete(id);sessionEntries.delete(session);try{Reflect.apply(closeSession,session,[]);}catch{}throw error;}
 }
 async function commitText(object,{signal}={}){
  const page=objectPages.get(object),data=dataFor(page);if(!data.textOwner?.entries.some(row=>row.object===object))fail('The edited text is not a current native PDF label.');
  const fromRevision=value(data.entry,'revision'),canReuse=data.tile&&data.renderRevision===fromRevision,ids=data.pathIds.slice(),tile=data.tile;
  const committed=await texts.commit(data.textOwner,texts.snapshot(data.textOwner,object.figureId),{signal});dataFor(page);
  let rasterReuseProof;if(canReuse&&committed.revision===value(data.entry,'revision')){rasterReuseProof={};rasterReuseProofs.set(rasterReuseProof,{page,tile,ids,fromRevision,toRevision:committed.revision});}
  return refresh(page,{signal,rasterReuseProof});
 }
 function prepareTextEditing(object){const page=objectPages.get(object),data=dataFor(page),row=data.textOwner?.entries.find(row=>row.object===object);if(!row)fail('Text editing requires its current privately owned PDF label.');return texts.prepareEditing(data.textOwner,row.id);}
 async function acquirePath(page,id,{signal,pointsOnly=false}={}){
  const data=dataFor(page),before=data.pathIds.slice();
  if(pointsOnly){
   abort(signal);const entry=data.entry,revision=value(entry,'revision'),proxies=data.proxies;
   const packet=await call(entry,'read',{ids:[id]},{signal});abort(signal);
   if(dataFor(page)!==data||data.entry!==entry||data.proxies!==proxies||data.refreshing||value(entry,'revision')!==revision
       ||packet.revision!==revision||before.length!==data.pathIds.length||before.some((value,index)=>value!==data.pathIds[index]))fail('The PDF point-selection source changed before its controls were prepared.');
   if(packet.result?.length!==1||packet.result[0].id!==id||packet.result[0].kind!=='path'||typeof supportsPointMapping!=='function'
       ||!supportsPointMapping(packet.result[0],value(entry,'operationNames')))fail('Point Selection cannot edit this PDF path. Its source artwork and existing edits are preserved.');
  }
  if(!data.pathIds.includes(id)){if(data.pathIds.length>=paths.LIMIT)fail('At most32 PDF paths can have native edit controls.');data.pathIds.push(id);}
  try{await refresh(page,{signal});return Array.from(objectPagesKeys(page)).find(object=>object.figureId===id&&Array.isArray(object.path));}catch(error){data.pathIds=before;throw error;}
 }
 function* objectPagesKeys(page){function* walk(object){yield object;for(const child of object._objects||[])yield* walk(child);}yield* walk(page);}
 async function commitPaths(objects,{signal}={}){
  if(!Array.isArray(objects)||!objects.length||objects.length>paths.LIMIT)fail('A bounded nonempty native path selection is required.');
  const page=objectPages.get(objects[0]),data=dataFor(page),entry=data.entry,owner=data.proxies;
  if(objects.some(object=>objectPages.get(object)!==page))fail('Native point edits require one canonical PDF page.');
  currentProxyDispatch(owner);abort(signal);
  const binding=data.renderBinding,canReuse=!data.refreshing&&currentRasterBinding(data,binding),candidates=objects.map(object=>Reflect.apply(proxySnapshot.value,owner,[object]));
  currentProxyDispatch(owner);
  const committed=await Reflect.apply(proxyCommit.value,owner,[candidates,{signal}]);dataFor(page);
  // Session validates and installs the mutation checkpoint before resolving its
  // source/revision acknowledgement. It intentionally exposes no documentState.
  const checkpoint=value(entry,'currentCheckpoint');let rasterReuseProof;
  if(canReuse&&data.proxies===owner&&currentRasterBinding(data,binding,{head:false})&&candidates.every(candidate=>binding.ids.includes(candidate.id))
   &&sameCopyValue(committed.source,binding.source)&&committed.revision===value(entry,'revision')&&checkpoint.documentRevision===committed.revision
   &&binding.checkpoint.documentRevision===binding.revision){
   rasterReuseProof={};rasterReuseProofs.set(rasterReuseProof,{page,data,entry,session:entry.session,tile:binding.tile,ids:binding.ids.slice(),binding,
    fromRevision:binding.revision,toRevision:committed.revision,toCheckpoint:copyRasterState(checkpoint)});
  }
  return refresh(page,{signal,rasterReuseProof});
 }
 async function commitPath(object,options){return commitPaths([object],options);}
 async function command(page,action,input={},options={}){const data=dataFor(page);if(!['group','move','release','undo','redo','goToState'].includes(action))fail('Unknown canonical PDF page command.');const result=await call(data.entry,action,input,options);await refresh(page,options);return result;}
 async function read(page,action,input={},options={}){if(!['inventory','children','node','queryRect','hitPath','read','checkpoint','exportSvg','exportPdf'].includes(action))fail('Unknown bounded PDF page read.');return call(dataFor(page).entry,action,input,options);}
 function captureDrafts(objects,{signal}={}){
  abort(signal);if(!Array.isArray(objects)||objects.length>256||new Set(objects).size!==objects.length)fail('A bounded distinct PDF text draft list is required.');
  const rows=objects.map(object=>{const page=objectPages.get(object),data=dataFor(page),row=data.textOwner?.entries.find(row=>row.object===object);if(!row)fail('A text draft needs its current privately owned native label.');return {page,data,owner:data.textOwner,id:row.id,receipt:texts.captureDraft(data.textOwner,row.id,{signal})};});
  const token=Object.freeze({});draftCaptures.set(token,rows);validateDraftCapture(token,{signal});return token;
 }
 function validateDraftCapture(token,{signal}={}){
  abort(signal);const rows=draftCaptures.get(token);if(!rows)fail('The PDF text draft capture is foreign.');
  for(const row of rows){if(dataFor(row.page)!==row.data||row.data.textOwner!==row.owner)fail('The PDF text view changed during read-only Save.');texts.readDraftCapture(row.owner,row.receipt,{signal});}return true;
 }
 function captureAssetStates(ids){if(!Array.isArray(ids)||ids.length>8||new Set(ids).size!==ids.length)fail('A bounded distinct PDF asset list is required.');const token=Object.freeze({});assetCaptures.set(token,ids.map(id=>{const entry=entryFor(id);return {entry,revision:value(entry,'revision'),checkpoint:value(entry,'currentCheckpoint').stateId};}));return token;}
 function validateAssetStates(token){const rows=assetCaptures.get(token);if(!rows)fail('The PDF asset state capture is foreign.');for(const row of rows)if(registry.get(row.entry.id)!==row.entry||value(row.entry,'revision')!==row.revision||value(row.entry,'currentCheckpoint').stateId!==row.checkpoint)fail('The PDF artwork changed during copy admission.');return true;}
 async function saveAssets(ids,{signal,draftCapture}={}){
  const assets=[],retained=new Set(ids),drafts=new Map();
  const validate=()=>{abort(signal);if(draftCapture)validateDraftCapture(draftCapture,{signal});};validate();
  if(draftCapture)for(const row of draftCaptures.get(draftCapture)){
   const id=row.data.entry.id;if(!retained.has(id))fail('A captured text draft has no matching saved PDF asset.');
   const changes=drafts.get(id)||[];if(changes.some(change=>change.id===row.id))fail('A text draft cannot replace the same source label twice.');
   changes.push({id:row.id,authoredText:texts.readDraftCapture(row.owner,row.receipt,{signal})});drafts.set(id,changes);
  }
  for(const id of retained){validate();const entry=entryFor(id),checkpoint=value(entry,'currentCheckpoint'),changes=drafts.get(id),saved=await call(entry,changes?'saveDraft':'save',changes?{changes}:{},{signal});validate();
   if(value(entry,'currentCheckpoint').stateId!==checkpoint.stateId)fail('The PDF changed during project Save.');
   const source=value(entry,'source');assets.push({assetId:id,pageNumber:source.pageNumber,savedStateId:checkpoint.stateId,source:{sha256:source.sha256,byteLength:source.byteLength},sourceBytes:entry.bytes.slice(),payloadBlob:saved.result.blob});
  }validate();return assets;
 }
 async function hydrateAssets(assets,{signal}={}){
  if(!Array.isArray(assets)||assets.length>8||new Set(assets.map(row=>row.assetId)).size!==assets.length)fail('A bounded distinct PDF asset list is required.');
  const captured=assets.map(asset=>{
   if(typeof asset.assetId!=='string'||asset.assetId.length>128||typeof asset.savedStateId!=='string'||asset.savedStateId.length>256
       ||!(asset.sourceBytes instanceof Uint8Array)||!asset.sourceBytes.length||asset.sourceBytes.length>33554432||!(asset.payloadBlob instanceof Blob)
       ||!Number.isSafeInteger(asset.pageNumber)||asset.pageNumber<1)fail('A saved PDF asset is incomplete.');
   return {assetId:asset.assetId,savedStateId:asset.savedStateId,pageNumber:asset.pageNumber,sourceBytes:asset.sourceBytes.slice(),payloadBlob:asset.payloadBlob};
  });
  const bindings=[],created=[];
  try{for(const asset of captured){
   abort(signal);const bytes=asset.sourceBytes,session=await sessions.hydrate({bytes,pageNumber:asset.pageNumber,payloadBlob:asset.payloadBlob,signal}),id=crypto.randomUUID();
   const entry={id,session,bytes,views:new Set(),pendingHydration:true,coldAliases:new Map([[asset.savedStateId,Reflect.apply(getters.currentCheckpoint,session,[]).stateId]])};registry.set(id,entry);sessionEntries.set(session,entry);created.push(entry);bindings.push({savedAssetId:asset.assetId,assetId:id});
  }hydrations.set(bindings,{entries:created,bindings:bindings.map(row=>({...row}))});return bindings;}
  catch(error){for(const entry of created){registry.delete(entry.id);sessionEntries.delete(entry.session);try{Reflect.apply(closeSession,entry.session,[]);}catch{}}throw error;}
 }
 function rebindAssets(shell,bindings){
  const issued=hydrations.get(bindings);if(!issued)fail('Fresh privately hydrated PDF asset bindings are required.');
  const map=new Map(issued.bindings.map(row=>[row.savedAssetId,entryFor(row.assetId)])),pending=[shell],seen=new WeakSet(),descriptors=new WeakSet();let count=0;
  const containers=['documents','payload','project','figure','presentation','tabs','fabric','scene','objects','clipPath','mask','deck','pages','masters','layouts','elements','components','fabricObject','userAssets','fabricObjects','deckTemplates'];
  while(pending.length){const row=pending.pop();if(!row||typeof row!=='object'||seen.has(row))continue;seen.add(row);if(++count>250000)fail('The document shell exceeds the bounded PDF view envelope.');
   if(row.densePdf?.schema===SCHEMA&&!descriptors.has(row.densePdf)){
    const descriptor=row.densePdf,entry=map.get(descriptor.assetId);
    if(!entry||!entry.coldAliases.has(descriptor.stateId)||!sameSource(descriptor.source,value(entry,'source')))fail('A saved PDF view has no matching authenticated source and saved current state.');
    descriptor.assetId=entry.id;descriptor.stateId=entry.coldAliases.get(descriptor.stateId);descriptors.add(descriptor);
   }
   if(Array.isArray(row)){for(const item of row)if(item&&typeof item==='object')pending.push(item);}
   else {for(const key of containers){const item=row[key];if(item&&typeof item==='object')pending.push(item);}}
  }return shell;
 }
 function discardHydratedAssets(bindings){const issued=hydrations.get(bindings);if(!issued)fail('Fresh privately hydrated PDF asset bindings are required.');hydrations.delete(bindings);for(const entry of issued.entries)entry.pendingHydration=false;cleanupAll(issued.entries.filter(entry=>!entry.views.size&&registry.get(entry.id)===entry).map(entry=>()=>{registry.delete(entry.id);sessionEntries.delete(entry.session);Reflect.apply(closeSession,entry.session,[]);}));}
 function commitHydratedAssets(bindings){const issued=hydrations.get(bindings);if(!issued)fail('Fresh privately hydrated PDF asset bindings are required.');for(const entry of issued.entries)entry.pendingHydration=false;hydrations.delete(bindings);}
 // Copy handles contain only a detached native scene and privately forked,
 // immutable current baselines. They never retain a disposable source view or
 // trust a caller's saved descriptor as authority to issue a new document.
 function copyScene(value){
  let count=0,characters=0;const active=new Set();
  const visit=(row,depth)=>{
   if(++count>100000||depth>48)fail('The copied artwork exceeds the document scene limit.');
   if(row===undefined)return undefined;
   if(row===null||typeof row==='boolean'||typeof row==='number'&&Number.isFinite(row))return row;
   if(typeof row==='string'){characters+=row.length;if(characters>8388608)fail('The copied artwork exceeds the document shell limit.');return row;}
   if(!row||typeof row!=='object'||active.has(row)||(!Array.isArray(row)&&Object.prototype.toString.call(row)!=='[object Object]'))fail('The copied scene must contain plain finite native records.');
   active.add(row);const result=Array.isArray(row)?new Array(row.length):{};
   for(const key of Reflect.ownKeys(row)){
    if(Array.isArray(row)&&key==='length')continue;
    const descriptor=Object.getOwnPropertyDescriptor(row,key);
    if(typeof key!=='string'||!Object.hasOwn(descriptor,'value'))fail('The copied scene must contain plain data properties.');
    characters+=key.length;if(characters>8388608)fail('The copied artwork exceeds the document shell limit.');
    const item=visit(descriptor.value,depth+1);if(item!==undefined)Object.defineProperty(result,key,{value:item,writable:true,configurable:true,enumerable:true});
   }
   active.delete(row);return result;
  };
  const result=visit(value,0);if(new TextEncoder().encode(JSON.stringify(result)).length>8388608)fail('The copied artwork exceeds the document shell limit.');return result;
 }
 function sameCopyValue(a,b){if(Object.is(a,b))return true;if(!a||!b||typeof a!=='object'||typeof b!=='object'||Array.isArray(a)!==Array.isArray(b)||Array.isArray(a)&&a.length!==b.length)return false;const keys=Object.keys(a),other=Object.keys(b);return keys.length===other.length&&keys.every((key,index)=>key===other[index]&&sameCopyValue(a[key],b[key]));}
 function copyDescriptors(scene){
  const result=[],pending=[scene],seen=new Set();let count=0;
  while(pending.length){const row=pending.pop();if(!row||typeof row!=='object'||seen.has(row))continue;seen.add(row);if(++count>100000)fail('The copied scene exceeds the document node limit.');
   if(row.densePdf){if(row.densePdf.schema!==SCHEMA)fail('The copied PDF descriptor is unsupported.');result.push(row.densePdf);}
   if(Array.isArray(row))pending.push(...row);else for(const key of ['objects','clipPath','mask'])if(row[key])pending.push(row[key]);
  }return result;
 }
 function validateRestoredScene(scene,objects,candidates){
  if(!Array.isArray(objects)||objects.length!==scene.length)fail('The copied native scene is incomplete.');
  const pending=scene.map((record,index)=>[record,objects[index]]);
  while(pending.length){const [record,object]=pending.pop();
   if(!object||typeof object!=='object'||object===record)fail('The copied native scene is incomplete.');
   if(record.densePdf||record.type===PdfDensePage.type){
    const descriptor=record.densePdf,data=dataFor(object),entry=data.entry,revision=value(entry,'revision'),checkpoint=value(entry,'currentCheckpoint');
    const ids=descriptor?.viewPathIds||[];
    if(!candidates.has(object)||descriptor?.schema!==SCHEMA||descriptor.assetId!==entry.id||!sameSource(descriptor.source,value(entry,'source'))
        ||(entry.coldAliases.get(descriptor.stateId)||descriptor.stateId)!==checkpoint.stateId||checkpoint.documentRevision!==revision
        ||data.refreshing||data.renderRevision!==revision||!sameCopyValue(ids,data.pathIds))fail('The copied PDF view has no matching current native source.');
   }else if(pages.has(object))fail('The copied native scene contains an unexpected PDF view.');
   for(const key of Object.keys(record)){
    if(key==='objects'&&Array.isArray(record[key])){
     // A private PDF Page's cached controls are not serialized document children.
     if(pages.has(object)){if(record[key].length)fail('The copied PDF view contains unexpected cached children.');continue;}
     const children=Object.getOwnPropertyDescriptor(object,'_objects')?.value;
     if(!Array.isArray(children)||children.length!==record[key].length)fail('The copied native scene is incomplete.');
     record[key].forEach((child,index)=>pending.push([child,children[index]]));
    }else if(nativeOption(record[key])||(['clipPath','mask'].includes(key)&&record[key]?.densePdf)){
     if(!object[key]||object[key]===record[key])fail('The copied native scene is incomplete.');pending.push([record[key],object[key]]);
    }
   }
  }
 }
 async function prepareRestoredScene(scene,{signal,assertCurrent,candidates,cleanupNative,validateNative}={}){
  const objects=[],sidecarKeys=nativeOptionKeys(scene),cleanup=cleanupNative|| (values=>optionCleanup(values,object=>candidates.has(object),sidecarKeys));
  try{
   for(const record of scene){
    let currentRoot,releaseCurrent;
    try{
     abort(signal);assertCurrent();
     const reviver=function(serialized,object,error){
      if(arguments.length>2)throw error;
      currentRoot=object;releaseCurrent=cleanup([object]);
      if(serialized!==record)fail('The native scene constructor changed its source record.');
      validateRestoredScene([record],[object],candidates);validateNative?.(object);abort(signal);assertCurrent();
     };
     // One root per native call gives this owner custody before another root
     // starts. A rejected current root has not entered native Xe's cleanup list.
     const result=await Reflect.apply(enlivenObjects,fabric.util,[[record],{signal,reviver}]);
     if(!Array.isArray(result)||result.length!==1)fail('The copied native scene is incomplete.');
     if(!currentRoot){currentRoot=result[0];releaseCurrent=cleanup([currentRoot]);}
     if(result[0]!==currentRoot)fail('The native scene constructor changed its completed root.');
     validateRestoredScene([record],result,candidates);validateNative?.(result[0]);objects.push(currentRoot);currentRoot=null;releaseCurrent=null;
     abort(signal);assertCurrent();
    }catch(error){try{releaseCurrent?.();}catch{}throw error;}
   }
   validateRestoredScene(scene,objects,candidates);abort(signal);assertCurrent();
   return {objects,release:cleanup(objects)};
  }catch(error){try{cleanup(objects)();}catch{}throw error;}
 }
 // HELD CANDIDATE: local native scene installation only. App intent, UI and
 // source-history rollback remain the caller's distinct responsibilities.
 function optionMembership(owned){return page=>owned.has(page);}
 function nativeCleanupPermission(context){return object=>{
  if(context.before.has(object))return false;if(context.nativeAdmissionClosed&&!context.createdNative.has(object)){context.unknownCustody=true;return false;}const canvas=Reflect.apply(weakTarget,context.targetRef,[]);
  if(!canvas){context.unknownCustody=true;return false;}
  try{const live=liveNativeGraph(canvas,{excludeDisposedPageOptions:true});if(live.has(object))return false;
   if(externallyOwnedNative(context.custody,object,live)){context.unknownCustody=true;return false;}
   return true;}catch{context.unknownCustody=true;return false;}
 };}
 function retireCanvasContext(data){
  data.cleanupContext.before.clear();data.cleanupContext.preparing=false;data.cleanupContext.custody.admissionClosed=true;
  data.pins.clear();data.states.clear();data.resources.length=0;data.roots.length=0;data.ownedResources.clear();
  data.membership?.rows.clear();data.membership?.records.clear();data.membership?.painted.clear();data.membership?.connectors.clear();data.membership?.labels.clear();data.membership?.paintPool.clear();data.membership?.newTexts.clear();data.membership?.removedTexts.clear();data.membership=null;data.completion=null;
  data.scene=null;data.prior=null;data.oldLive=null;data.target=null;data.scope=null;data.replacement=null;data.nativeFrame=null;
  data.assertCurrent=null;data.current=null;data.release=null;data.retainNative=null;data.validateFrame=null;data.validateNative=null;data.clear=null;data.signal=null;data.cancel=null;
 }
 function canvasInputCopy(input){
  // App supplies already admitted plain serialized input. Native structuredClone
  // retains opaque path/font/glyph/import metadata without re-parsing or applying
  // the native-container envelope to those unrelated payload forests.
  if(!detachedClone)fail('Detached native scene copying is unavailable.');return Reflect.apply(detachedClone,undefined,[input]);
 }
 function nativeCanvasRecords(record){
  const roots=Array.isArray(record?.objects)?record.objects:[],raw=record||{},frame={backgroundImage:raw.backgroundImage,backgroundColor:raw.background,overlayImage:raw.overlayImage,overlayColor:raw.overlay,clipPath:raw.clipPath};
  return {objects:roots,frame};
 }
 function denseNativeRecord(record){return record&&typeof record==='object'&&(record.densePdf||record.type===PdfDensePage.type);}
 function canvasNativeScan(record,{bounded=false}={}){
  const {objects,frame}=nativeCanvasRecords(record),pending=objects.map(row=>({row,depth:0})),seen=new Set(),active=new Set(),descriptors=[];let nativeCount=0;
  for(const [key,row] of Object.entries(frame))if(nativeOption(row)||denseNativeRecord(row))pending.push({row,depth:0});
  while(pending.length){const {row,depth,exit}=pending.pop();if(!row||typeof row!=='object')continue;if(exit){active.delete(row);continue;}
   if(bounded){if(active.has(row)||depth>48||++nativeCount>100000)fail('The native scene exceeds the document tree limit.');active.add(row);pending.push({row,exit:true});}else{if(seen.has(row))continue;seen.add(row);}
   if(denseNativeRecord(row)){if(bounded&&(!row.type||typeof getNativeClass!=='function'||Reflect.apply(getNativeClass,fabric.classRegistry,[row.type])!==PdfDensePage))fail('The native PDF view requires its registered native Page type.');descriptors.push(row.densePdf);}
   for(const key of Object.keys(row)){const descriptor=Object.getOwnPropertyDescriptor(row,key);if(!descriptor||!Object.hasOwn(descriptor,'value'))fail('The native scene contains unsupported input.');const child=descriptor.value;
    if(key==='objects'&&Array.isArray(child))for(const value of child)pending.push({row:value,depth:depth+1});
    else if(nativeOption(child)||['clipPath','mask'].includes(key)&&child?.densePdf)pending.push({row:child,depth:depth+1});}
  }return descriptors;
 }
 function hasDenseCanvasRestore(input){
  // Diagnostic only: ordinary-only scenes retain their native loader route and
  // acquire no dense tree/byte cap. Opaque metadata is never scanned for markers.
  const record=typeof input==='string'?JSON.parse(input):input;return canvasNativeScan(record).length>0;
 }
 function restoreInput(input){
  const original=typeof input==='string'?JSON.parse(input):input;if(!original||Array.isArray(original)||typeof original!=='object')fail('The native canvas record is invalid.');
  if(original.objects!==undefined&&!Array.isArray(original.objects))fail('The native canvas roots are invalid.');
  for(const key of Object.keys(original)){const d=Object.getOwnPropertyDescriptor(original,key);if(!d||!Object.hasOwn(d,'value'))fail('The native scene contains unsupported input.');if(key!=='objects'&&forbiddenCanvasKeys.has(key))fail('The native canvas record shadows native structural state: '+key);}
  const descriptorsBefore=canvasNativeScan(original,{bounded:true});if(!descriptorsBefore.length)fail('The native canvas adapter requires an actual saved PDF view.');
  const record=canvasInputCopy(original),{objects=[],...raw}=record,{frame}=nativeCanvasRecords(record),descriptors=canvasNativeScan(record,{bounded:true});
  return {objects,raw,frame,descriptors};
 }
 function nativeCanvasDispatch(canvas){
  for(const key of ['add','remove','set','getObjects','_set'])if(!exactDataMethod(canvas,key,nativeCanvasMethods[key]))fail('The native canvas dispatcher changed.');
  const interactive=typeof fabric.Canvas==='function'&&canvas instanceof fabric.Canvas,clear=interactive?nativeInteractiveClear:nativeCanvasMethods.clear;
  if(!exactDataMethod(canvas,'clear',clear))fail('The native canvas dispatcher changed.');
  for(const key of ['_onObjectAdded','_onObjectRemoved'])if(!exactDataMethod(canvas,key,(interactive?nativeInteractiveObjectMethods:nativeCanvasMethods)[key]))fail('The native canvas dispatcher changed.');return clear;
 }
 function nativeEdgeEntries(object){
  const entries=[];for(const key of Object.keys(object)){if(['canvas','group','parent','layoutManager','_objects'].includes(key))continue;const descriptor=Object.getOwnPropertyDescriptor(object,key);if(!descriptor||!Object.hasOwn(descriptor,'value'))continue;const child=descriptor.value;
   if(child&&typeof child==='object'&&(nativeOption(child)||['clipPath','mask'].includes(key)))entries.push([key,child]);}return entries;
 }
 function sameNativeArray(actual,expected){return Array.isArray(actual)&&actual.length===expected.length&&expected.every((object,index)=>actual[index]===object);}
 function ownValue(object,key){const descriptor=Object.getOwnPropertyDescriptor(object,key);return descriptor&&Object.hasOwn(descriptor,'value')?descriptor.value:undefined;}
 function stockConnectorText(object){return object&&Object.getPrototypeOf(object)===nativeConnectorTextPrototype&&!pages.has(object)&&!objectPages.has(object)&&(!Array.isArray(ownValue(object,'_objects'))||!ownValue(object,'_objects').length);}
 function connectorContext(object){const meta=ownValue(object,'smartConnectorMeta'),id=ownValue(object,'figureId');if(ownValue(object,'figureType')!=='smartConnector'||!meta||typeof id!=='string'||!id)return null;return {id,label:String(ownValue(meta,'label')||'').slice(0,80).trim()};}
 function labelContext(object){const meta=ownValue(object,'smartConnectorMeta');return stockConnectorText(object)&&ownValue(object,'figureType')==='connectorLabel'&&meta?{id:ownValue(meta,'connectorId')}:null;}
 function ordinaryPaintRow(object){return object instanceof fabric.FabricObject&&!pages.has(object)&&!objectPages.has(object);}
 function completionPaintRow(graph,object){return graph.painted.has(object)&&ordinaryPaintRow(object);}
 function capturedPaint(object){if(!object||typeof object!=='object')return null;const prototype=Object.getPrototypeOf(object);return prototype===nativeGradientPrototype||prototype===nativePatternPrototype?prototype:null;}
 function paintValues(object){return new Map(['fill','stroke'].map(key=>[key,ownValue(object,key)]));}
 function acceptedOrdinaryPaint(graph,value){if(value===null||typeof value!=='object')return typeof value!=='function';return graph.paintPool.has(value)&&Object.getPrototypeOf(value)===graph.paintPool.get(value);}
 function freezeCompletionPaints(data){
  const graph=data.membership;for(const row of graph.rows.values())if(completionPaintRow(graph,row.object)){
   const values=paintValues(row.object);for(const value of values.values())if(!acceptedOrdinaryPaint(graph,value))fail('Completion introduced an unowned ordinary paint.');
   const expected=new Map(row.edges.filter(([key])=>!['fill','stroke'].includes(key))),actualPaints=new Map(nativeEdgeEntries(row.object).filter(([key])=>['fill','stroke'].includes(key)));
   row.edges=[...row.edgeOrder,...actualPaints.keys()].filter((key,index,keys)=>keys.indexOf(key)===index).flatMap(key=>expected.has(key)?[[key,expected.get(key)]]:actualPaints.has(key)?[[key,actualPaints.get(key)]]:[]);row.paints=values;
  }graph.paintWindow=false;
 }
 function captureCanvasMembership(data){
  const graph={roots:data.roots.slice(),frames:new Map(frameKeys.map(key=>[key,data.nativeFrame[key]])),rows:new Map(),records:new Map(),painted:new Set(),connectors:new Map(),labels:new Map(),newTexts:new Map(),removedTexts:new Set(),paintPool:new Map(),paintWindow:false,pending:null};
  const pairs=data.scene.objects.map((record,index)=>[record,data.roots[index]]);for(const key of frameKeys)if(nativeOption(data.scene.frame[key])||denseNativeRecord(data.scene.frame[key]))pairs.push([data.scene.frame[key],data.nativeFrame[key]]);
  while(pairs.length){const [record,object]=pairs.pop();if(!object||typeof object!=='object'||graph.records.has(object))continue;graph.records.set(object,record);
   if(Array.isArray(record.objects)&&!pages.has(object))record.objects.forEach((child,index)=>pairs.push([child,ownValue(object,'_objects')[index]]));
   for(const key of Object.keys(record))if(nativeOption(record[key])||['clipPath','mask'].includes(key)&&record[key]?.densePdf)pairs.push([record[key],object[key]]);
  }
  for(const object of liveNativeGraph({_objects:data.roots,...data.nativeFrame})){const children=ownValue(object,'_objects'),record=graph.records.get(object);if(pages.has(object)&&(!record?.densePdf&&record?.type!==PdfDensePage.type))fail('A prepared PDF view has no declared native source join.');graph.rows.set(object,{object,children:!pages.has(object)&&Array.isArray(children)?children.slice():null,edges:nativeEdgeEntries(object),edgeOrder:Object.keys(object),paints:paintValues(object),record});}
  const oldPaints=new Set();for(const object of data.oldLive){for(const value of paintValues(object).values())if(capturedPaint(value))oldPaints.add(value);if(pages.has(object))for(const control of objectPagesKeys(object))for(const value of paintValues(control).values())if(capturedPaint(value))oldPaints.add(value);}
  const pending=data.roots.slice();while(pending.length){const object=pending.pop();if(graph.painted.has(object))continue;graph.painted.add(object);if(pages.has(object))continue;const row=graph.rows.get(object);for(const child of row?.children||[])pending.push(child);const connector=connectorContext(object),label=labelContext(object);if(connector)graph.connectors.set(object,connector);if(label)graph.labels.set(object,label);}
  for(const row of graph.rows.values())if(completionPaintRow(graph,row.object))for(const value of row.paints.values())if(capturedPaint(value)){if(oldPaints.has(value))fail('The prepared native scene borrowed an old ordinary paint.');graph.paintPool.set(value,Object.getPrototypeOf(value));}
  return graph;
 }
 function validateCanvasMembership(data,{installed=false,allowOmissions=false}={}){
  const graph=data.membership;
  const collection=(actual,expected)=>{if(!Array.isArray(actual))return false;if(!allowOmissions)return sameNativeArray(actual,expected);let index=0;return actual.every(object=>{while(index<expected.length&&expected[index]!==object)index++;return index++<expected.length;});};
  for(const row of graph.rows.values()){
   if(row.children&&!collection(ownValue(row.object,'_objects'),row.children))fail('The prepared native authored collection changed.');let actual=nativeEdgeEntries(row.object),edges=row.edges;
   if(graph.paintWindow&&completionPaintRow(graph,row.object)){for(const value of paintValues(row.object).values())if(!acceptedOrdinaryPaint(graph,value))fail('Completion introduced an unowned ordinary paint.');actual=actual.filter(([key])=>!['fill','stroke'].includes(key));edges=edges.filter(([key])=>!['fill','stroke'].includes(key));}
   else for(const [key,value]of row.paints)if(!Object.is(ownValue(row.object,key),value))fail('The accepted native paint binding changed.');
   if(allowOmissions){if(!actual.every(([key,object])=>edges.some(([name,expected])=>name===key&&expected===object)))fail('A foreign native option replaced the prepared scene.');}
   else if(actual.length!==edges.length||actual.some(([key,object],index)=>key!==edges[index][0]||object!==edges[index][1]))fail('The prepared native option membership changed.');
   if(!allowOmissions&&pages.has(row.object))validateRestoredScene([row.record],[row.object],data.replacement.createdCandidates);
  }
  if(installed){if(!collection(data.target._objects,graph.roots))fail('The prepared native authored root order was replaced.');for(const [key,value]of graph.frames){const actual=data.target[key],prior=data.prior.values.get(key);if(!Object.is(actual,value)&&!(allowOmissions&&(actual===null||typeof actual!=='object'&&typeof actual!=='function'||Object.is(actual,data.scene.frame[key])||Object.is(actual,data.scene.raw[key])||prior&&Object.hasOwn(prior,'value')&&Object.is(actual,prior.value))))fail('The actual native canvas frame binding changed.');}}
  for(const [text,context]of graph.newTexts)if(!stockConnectorText(text)||ownValue(text,'figureType')!=='connectorLabel'||ownValue(text,'figureId')!==context.figureId||ownValue(ownValue(text,'smartConnectorMeta')||{},'connectorId')!==context.id||text.text!==context.label)fail('The registered connector Text context changed.');
 }
 function completionCollection(data,parent){if(parent===data.target)return data.membership.roots;const row=data.membership.rows.get(parent);if(!data.membership.painted.has(parent)||!row?.children||pages.has(parent))fail('The connector Text parent is not a prepared native collection.');return row.children;}
 function settleCompletionDelta(data,{required=true}={}){
  const graph=data.membership,delta=graph.pending;if(!delta)return;
  if(sameNativeArray(ownValue(delta.parent,'_objects'),delta.after)){const expected=completionCollection(data,delta.parent);expected.splice(0,expected.length,...delta.after);if(delta.kind==='remove'&&!delta.noop)graph.removedTexts.add(delta.text);graph.pending=null;return;}
  if(!required&&sameNativeArray(ownValue(delta.parent,'_objects'),delta.before)){graph.pending=null;return;}fail('The audited connector Text mutation did not match its native slot.');
 }
 function completionData(scope){const binding=canvasCompletions.get(scope);if(!binding||!binding.active||binding.data.completion!==binding)fail('The native completion scope is foreign or expired.');const data=binding.data;data.current();settleCompletionDelta(data);validateCanvasMembership(data,{installed:true});canvasRestoreIntent(data,data.membership.roots);return data;}
 function registerCanvasRestoreConnectorText(scope,{connector,text}={}){
  const data=completionData(scope),graph=data.membership,context=graph.connectors.get(connector),current=connectorContext(connector),label=labelContext(text);
  if(!context||!context.label||!current||current.id!==context.id||current.label!==context.label||!stockConnectorText(text)||!label||label.id!==context.id||text.text!==context.label||ownValue(text,'canvas')||ownValue(text,'group')||ownValue(text,'parent')||data.oldLive.has(text)||graph.rows.has(text)||nativeEdgeEntries(text).some(([key])=>!['fill','stroke'].includes(key))||[...paintValues(text).values()].some(value=>!acceptedOrdinaryPaint(graph,value)))fail('The connector Text is not a fresh audited native label.');
  if([...graph.labels].some(([object,row])=>row.id===context.id&&!graph.removedTexts.has(object))||[...graph.newTexts.values()].some(row=>row.id===context.id))fail('The prepared connector already has its native label.');
  const figureId=ownValue(text,'figureId');if(typeof figureId!=='string'||!figureId||[...graph.painted].some(object=>ownValue(object,'figureId')===figureId)||graph.rows.size>=100000)fail('The connector Text has no distinct bounded native identity.');
  graph.rows.set(text,{object:text,children:null,edges:nativeEdgeEntries(text),edgeOrder:Object.keys(text),paints:paintValues(text),record:null});graph.painted.add(text);graph.newTexts.set(text,{...context,figureId});data.ownedResources.add(text);data.cleanupContext.createdNative.add(text);data.cleanupContext.completionTexts.add(text);
  graph.pending={kind:'add',parent:data.target,text,before:graph.roots.slice(),after:graph.roots.concat(text),noop:false};
 }
 function removeCanvasRestoreConnectorText(scope,{connector,text,parent,slot,reason}={}){
  const data=completionData(scope),graph=data.membership,label=graph.labels.get(text),current=labelContext(text),expected=completionCollection(data,parent);
  if(!label||!current||!Object.is(current.id,label.id)||!stockConnectorText(text)||data.oldLive.has(text)||!Object.is(slot,expected.indexOf(text)))fail('The connector Text removal has no exact prepared native slot.');
  if(reason==='empty'){const context=graph.connectors.get(connector),now=connectorContext(connector);if(!context||context.label||!now||now.id!==context.id||now.label||label.id!==context.id||parent!==data.target)fail('The empty connector Text context changed.');}
  else if(reason==='orphan'){if(connector!==undefined||slot<0||[...graph.connectors.values()].some(row=>row.id&&row.id===label.id))fail('The orphan connector Text context changed.');}
  else fail('The connector Text removal reason is unsupported.');
  data.cleanupContext.completionTexts.add(text);
  if(slot<0&&reason!=='empty')fail('The connector Text removal has no native slot.');const after=expected.slice();if(slot>=0)after.splice(slot,1);
  graph.pending={kind:'remove',parent,text,before:expected.slice(),after,noop:slot<0};
 }
 function completeCanvasRestore(data,complete){const scope=Object.freeze({}),binding={data,active:true};data.completion=binding;canvasCompletions.set(scope,binding);data.membership.paintWindow=true;
  try{const result=complete(data.target,scope);if(result&&typeof result.then==='function')fail('Native canvas completion must be synchronous.');data.current();settleCompletionDelta(data);freezeCompletionPaints(data);validateCanvasMembership(data,{installed:true});}
  catch(error){if(data.membership.paintWindow)try{freezeCompletionPaints(data);}catch{}throw error;}
  finally{data.membership.paintWindow=false;binding.active=false;canvasCompletions.delete(scope);data.completion=null;}
 }
 function retireRemovedConnectorTexts(data){if(!data.membership.removedTexts.size)return;optionCleanup([...data.membership.removedTexts],()=>false,[],data.cleanupContext.allowsNative,data.cleanupContext.retired)();}
 function nativeRootLinks(roots){
  const links=new Map(),pending=roots.slice();while(pending.length){const object=pending.pop();if(!object||links.has(object))continue;links.set(object,object.canvas);if(!pages.has(object))for(const child of object._objects||[])pending.push(child);}return links;
 }
 function canvasBoundary(canvas,keys){return {roots:canvas._objects.slice(),links:nativeRootLinks(canvas._objects),flag:canvas.renderOnAddRemove,values:new Map(keys.map(key=>[key,Object.getOwnPropertyDescriptor(canvas,key)]))};}
 function sameNativeRoots(canvas,roots){return Array.isArray(canvas._objects)&&canvas._objects.length===roots.length&&roots.every((root,index)=>canvas._objects[index]===root);}
 function sameBoundary(canvas,boundary){return sameNativeRoots(canvas,boundary.roots)&&Object.is(canvas.renderOnAddRemove,boundary.flag)&&[...boundary.values].every(([key,before])=>{const now=Object.getOwnPropertyDescriptor(canvas,key);return !before?!now:now&&Reflect.ownKeys(before).length===Reflect.ownKeys(now).length&&Reflect.ownKeys(before).every(field=>Object.is(before[field],now[field]));});}
 function canvasRestoreIntent(data,roots){
  const owner=()=>replacements.get(data.scope)===data.replacement&&data.replacement.canvasRestore===data&&canvasRestoreTargets.get(data.target)===data;
  if(!owner())fail('A newer native scene superseded rollback.');const result=data.assertCurrent();if(result&&typeof result.then==='function')fail('Native canvas intent checks must be synchronous.');
  if(!owner())fail('A newer native scene superseded rollback.');nativeCanvasDispatch(data.target);if(!sameNativeRoots(data.target,roots))fail('A newer native scene replaced this installation.');
 }
 function restoreBoundary(data,frontier,remember,rollbackUi){
  const {target,prior}=data;let expected=frontier.slice(),active=true;
  const current=()=>{if(!active)return false;try{canvasRestoreIntent(data,expected);return true;}catch(error){remember(error);active=false;return false;}};
  const step=(operation,next)=>{if(!current())return;try{operation();}catch(error){remember(error);}expected=next;if(!current())return;};
  // Native remove splices before events; single-root add links that root before
  // its events. Persistent returned event failures do not block later roots.
  if(current()){try{target.renderOnAddRemove=false;}catch(error){remember(error);}current();}
  for(const root of frontier){if(!active)break;const index=expected.indexOf(root),next=expected.slice();next.splice(index,1);step(()=>Reflect.apply(nativeCanvasMethods.remove,target,[root]),next);
   if(active&&root.canvas!==undefined&&root.canvas!==target){remember(new Error('A native root moved to another canvas during rollback.'));active=false;}}
  for(const root of prior.roots){if(!active)break;if(root.canvas!==undefined&&root.canvas!==target){remember(new Error('A native root moved to another canvas during rollback.'));active=false;break;}
   step(()=>Reflect.apply(nativeCanvasMethods.add,target,[root]),expected.concat(root));if(active&&root.canvas!==target){remember(new Error('The original native canvas linkage could not be restored.'));active=false;}}
  if(!active)return false;
  for(const [key,descriptor] of prior.values){if(!current())break;try{if(descriptor)Object.defineProperty(target,key,descriptor);else delete target[key];}catch(error){remember(error);}current();}
  if(current()){try{if(!Object.is(target.renderOnAddRemove,prior.flag))target.renderOnAddRemove=prior.flag;}catch(error){remember(error);}current();}
  const restored=active&&sameNativeRoots(target,prior.roots)&&[...prior.links].every(([object,canvas])=>Object.is(object.canvas,canvas));
  if(!restored){if(active)remember(new Error('The original native canvas linkage could not be restored.'));return false;}
  if(rollbackUi&&current()){try{const result=rollbackUi(target);if(result&&typeof result.then==='function')fail('Native canvas rollback UI must be synchronous.');}catch(error){remember(error);}current();}
  return active;
 }
 async function prepareCanvasRestore(scope,input,{signal,assertCurrent=()=>{}}={}){
  const replacement=replacements.get(scope);if(!replacement||replacement.canvasRestore)fail('The native canvas replacement scope is foreign, busy or settled.');
  if(!nativeWeakRef||typeof weakTarget!=='function')fail('Weak native canvas cleanup ownership is unavailable.');
  const scene=restoreInput(input),target=replacement.canvas,clear=nativeCanvasDispatch(target),keys=[...new Set([...Object.keys(scene.raw),...frameKeys,'renderOnAddRemove'])],prior=canvasBoundary(target,keys),oldLive=liveNativeGraph(target);
  const cleanupContext={custody:replacement.custody,targetRef:replacement.custody.targetRef,before:oldLive,retired:new WeakSet(),preparing:true,unknownCustody:false,completionTexts:new WeakSet(),createdNative:new WeakSet(),nativeAdmissionClosed:false};cleanupContext.custody.admissionClosed=false;cleanupContext.allowsNative=nativeCleanupPermission(cleanupContext);
  const data={cleanupContext,scope,replacement,target,scene,clear,prior,oldLive,pins:new Map(),states:new Map(),roots:[],nativeFrame:{},resources:[],ownedResources:new Set(),retired:cleanupContext.retired,settled:false,preparing:true,signal,assertCurrent,cancel:()=>replacement.controller.abort()};
  for(const descriptor of scene.descriptors){if(descriptor?.schema!==SCHEMA||typeof descriptor.assetId!=='string'||typeof descriptor.stateId!=='string')fail('The saved PDF view descriptor is incomplete.');const entry=entryFor(descriptor.assetId),source=value(entry,'source'),state=entry.coldAliases.get(descriptor.stateId)||descriptor.stateId;
   if(!sameSource(source,descriptor.source)||data.states.has(entry)&&data.states.get(entry)!==state)fail('The native canvas requests inconsistent PDF states.');data.states.set(entry,state);if(!data.pins.has(entry))data.pins.set(entry,{entry,session:entry.session,source,revision:value(entry,'revision'),checkpoint:value(entry,'currentCheckpoint')});}
  data.current=except=>{abort(replacement.controller.signal);abort(signal);if(replacements.get(scope)!==replacement||replacement.canvasRestore!==data||canvasRestoreTargets.get(target)!==data)fail('The native canvas replacement was superseded.');const intent=assertCurrent();if(intent&&typeof intent.then==='function')fail('Native canvas intent checks must be synchronous.');nativeCanvasDispatch(target);
   if(data.preparing&&!sameBoundary(target,prior))fail('The native canvas changed during preparation.');
   for(const [entry,pin] of data.pins)if(entry!==except&&(registry.get(entry.id)!==entry||entry.session!==pin.session||!sessions.isSession(pin.session)||!sameCopyValue(value(entry,'source'),pin.source)||value(entry,'revision')!==pin.revision||!sameCopyValue(value(entry,'currentCheckpoint'),pin.checkpoint)))fail('The PDF source changed during native canvas restoration.');
   if(except){const pin=data.pins.get(except);if(!pin||registry.get(except.id)!==except||except.session!==pin.session||!sessions.isSession(pin.session)||!sameCopyValue(value(except,'source'),pin.source))fail('The PDF source owner changed during native canvas restoration.');}
  };
  data.allowsNative=cleanupContext.allowsNative;
  const sidecarKeys=nativeOptionKeys([...scene.objects,...Object.values(scene.frame)]);
  data.retainNative=values=>{if(data.preparing)for(const object of liveNativeGraph({_objects:values},{custody:cleanupContext.custody}))if(!oldLive.has(object)){data.ownedResources.add(object);cleanupContext.createdNative.add(object);}};
  const cleanup=values=>{data.retainNative(values);return()=>optionCleanup([...data.ownedResources],object=>replacement.createdCandidates.has(object),sidecarKeys,cleanupContext.allowsNative,cleanupContext.retired)();};
  data.release=()=>cleanup([...data.resources,...replacement.createdCandidates].filter(object=>!pages.get(object)?.disposed))();
  const validateNative=object=>{const fake={_objects:[object]};for(const child of liveNativeGraph(fake))if(oldLive.has(child))fail('The native canvas constructor borrowed a live scene resource.');};data.validateNative=validateNative;
  data.validateFrame=()=>{for(const key of frameKeys){const record=scene.frame[key],native=data.nativeFrame[key];if(nativeOption(record)||denseNativeRecord(record)){validateRestoredScene([record],[native],replacement.createdCandidates);validateNative(native);}else if(!Object.is(native,record))fail('The native canvas frame changed its scalar binding.');}};
  replacement.canvasRestore=data;canvasRestoreTargets.set(target,data);signal?.addEventListener('abort',data.cancel,{once:true});
  try{
   data.current();const result=await prepareRestoredScene(scene.objects,{signal:replacement.controller.signal,assertCurrent:data.current,candidates:replacement.createdCandidates,cleanupNative:cleanup,validateNative});data.roots=result.objects;data.resources.push(...result.objects);data.current();
   for(const key of frameKeys){data.current();const record={[key]:scene.frame[key]},native=await Reflect.apply(enlivenOptions,fabric.util,[record,{signal:replacement.controller.signal}]);
    const value=native[key];if(value&&typeof value==='object'&&value!==record[key]){data.resources.push(value);data.retainNative([value]);}data.current();
    if(nativeOption(record[key])||denseNativeRecord(record[key])){validateRestoredScene([record[key]],[value],replacement.createdCandidates);validateNative(value);}else if(!Object.is(value,record[key]))fail('The native canvas frame changed its scalar binding.');data.nativeFrame[key]=value;
   }
   validateRestoredScene(scene.objects,data.roots,replacement.createdCandidates);for(const root of data.roots)validateNative(root);data.validateFrame();data.current();data.membership=captureCanvasMembership(data);cleanupContext.nativeAdmissionClosed=true;cleanupContext.custody.admissionClosed=true;data.preparing=false;const receipt=Object.freeze({});canvasRestores.set(receipt,data);return receipt;
  }catch(error){try{data.release();}catch{}settleCanvasRestore(data);throw error;}
 }
 function settleCanvasRestore(data){const {replacement,target,signal,cancel}=data;data.settled=true;replacement.canvasRestore=null;if(canvasRestoreTargets.get(target)===data)canvasRestoreTargets.delete(target);signal?.removeEventListener('abort',cancel);retireCanvasContext(data);}
 function discardCanvasRestore(receipt){const data=canvasRestores.get(receipt);if(!data||data.settled)fail('The prepared native canvas is foreign or settled.');data.settled=true;try{data.release();}finally{settleCanvasRestore(data);canvasRestores.delete(receipt);}}
 function commitCanvasRestore(receipt,{beforeInstall,complete,rollbackUi}={}){
  const data=canvasRestores.get(receipt);if(!data||data.settled)fail('The prepared native canvas is foreign or settled.');const {target,prior}=data;data.settled=true;
  let mutating=false,failed=false,failure,phase='original';const remember=error=>{if(!failed){failed=true;failure=error;}};
  const attempt=operation=>{try{return operation();}catch(error){remember(error);}};
  const current=roots=>{data.current();canvasRestoreIntent(data,roots);};
  const synchronous=(hook,label)=>{if(hook!==undefined&&typeof hook!=='function')fail('Native canvas '+label+' must be a synchronous function.');};
  const callHook=(hook,label)=>{const result=hook(target);if(result&&typeof result.then==='function')fail('Native canvas '+label+' must be synchronous.');};
  const frontier=()=>{
   if(phase==='complete')settleCompletionDelta(data,{required:false});
   if(!Array.isArray(target._objects))fail('A newer native scene replaced this installation.');const roots=target._objects.slice();
   if(phase==='clear'){const offset=prior.roots.length-roots.length;if(offset<0||!roots.every((root,index)=>prior.roots[offset+index]===root))fail('A newer native scene replaced this installation.');}
   else if(!sameNativeRoots(target,phase==='original'?prior.roots:phase==='complete'?data.membership.roots:data.roots))fail('A newer native scene replaced this installation.');
   if(phase!=='original'&&data.membership)validateCanvasMembership(data,{installed:phase==='frame'||phase==='complete',allowOmissions:true});canvasRestoreIntent(data,roots);return roots;
  };
  try{
   synchronous(beforeInstall,'preparation');synchronous(complete,'completion');synchronous(rollbackUi,'rollback UI');
   data.current();if(!sameBoundary(target,prior))fail('The native canvas changed before installation.');validateRestoredScene(data.scene.objects,data.roots,data.replacement.createdCandidates);for(const root of data.roots)data.validateNative(root);data.validateFrame();validateCanvasMembership(data);current(prior.roots);
   // Even a partially throwing App hook needs owned local recovery. App owns
   // physical dimensions/UI; Page owns roots/raw/frame and the native flag.
   mutating=true;target.renderOnAddRemove=false;current(prior.roots);
   if(beforeInstall){callHook(beforeInstall,'preparation');current(prior.roots);}
   phase='clear';Reflect.apply(data.clear,target,[]);current([]);validateCanvasMembership(data);
   phase='add';Reflect.apply(nativeCanvasMethods.add,target,data.roots);current(data.roots);validateCanvasMembership(data);
   phase='raw';Reflect.apply(nativeCanvasMethods.set,target,[data.scene.raw]);current(data.roots);validateCanvasMembership(data);
   phase='frame';Reflect.apply(nativeCanvasMethods.set,target,[data.nativeFrame]);current(data.roots);validateCanvasMembership(data,{installed:true});
   target.renderOnAddRemove=prior.flag;current(data.roots);
   phase='complete';if(complete){completeCanvasRestore(data,complete);current(data.membership.roots);}validateCanvasMembership(data,{installed:true});retireRemovedConnectorTexts(data);current(data.membership.roots);validateCanvasMembership(data,{installed:true});
   if(!Object.is(target.renderOnAddRemove,prior.flag)){target.renderOnAddRemove=prior.flag;current(data.membership.roots);validateCanvasMembership(data,{installed:true});}
  }catch(error){remember(error);if(mutating)attempt(()=>{if(restoreBoundary(data,frontier(),remember,rollbackUi))phase='original';});attempt(()=>data.release());}
  finally{
   // Never overwrite a first falsy failure with restoration or retirement.
   attempt(()=>settleCanvasRestore(data));attempt(()=>canvasRestores.delete(receipt));
  }
  if(failed)throw failure;return target;
 }

 function closeCopyEntries(entries){cleanupAll(entries.map(entry=>()=>Reflect.apply(closeSession,entry.session,[])));}
 function copyData(token){const data=copies.get(token);if(!data||data.released)fail('The copied artwork handle is foreign or released.');return data;}
 function releaseSceneCopy(token){const data=copyData(token);copies.delete(token);copyHolds.delete(data);data.released=true;closeCopyEntries(data.entries);}
 function sceneCopySnapshot(token){const data=copyData(token);return {scene:copyScene(data.scene),transforms:data.transforms.map(row=>row.slice()),hadParents:data.hadParents.slice()};}
 async function captureSceneCopy(objects,{properties=[],signal}={}){
  abort(signal);if(!Array.isArray(objects)||!objects.length||objects.length>10000||new Set(objects).size!==objects.length||objects.some(object=>!(object instanceof fabric.FabricObject)))fail('Copy requires distinct actual native artwork objects.');
  if(typeof forkSession!=='function')fail('Independent PDF copies require their native document fork.');
  const rows=new Map(),sourcePages=new Map(),pending=objects.slice(),seen=new Set();
  while(pending.length){const object=pending.pop();if(!object||seen.has(object))continue;seen.add(object);if(seen.size>100000)fail('The copied artwork exceeds the native scene limit.');
   if(pages.has(object)){const data=dataFor(object),entry=data.entry,checkpoint=value(entry,'currentCheckpoint').stateId,revision=value(entry,'revision');sourcePages.set(object,data);if(!rows.has(entry.id))rows.set(entry.id,{entry,checkpoint,revision});if(object.clipPath)pending.push(object.clipPath);if(object.mask)pending.push(object.mask);continue;}
   if(objectPages.has(object))fail('Copy the PDF page to preserve its editable paths and labels.');
   for(const child of object._objects||[])pending.push(child);if(object.clipPath)pending.push(object.clipPath);if(object.mask)pending.push(object.mask);
  }
  const scene=copyScene(objects.map(object=>object.toObject(properties))),transforms=objects.map(object=>Array.from(object.calcTransformMatrix())),hadParents=objects.map(object=>Boolean(object.group));
  if(transforms.some(matrix=>matrix.length!==6||matrix.some(number=>!Number.isFinite(number))))fail('Copied artwork requires its actual finite native placement.');
  for(const descriptor of copyDescriptors(scene)){const row=rows.get(descriptor.assetId);if(!row||descriptor.stateId!==row.checkpoint||!sameSource(descriptor.source,value(row.entry,'source')))fail('Copied PDF artwork has no matching current native source owner.');}
  if(rows.size>8)fail('A document may contain at most eight independent PDF assets.');
  const draftCapture=captureDrafts([...sourcePages.keys()].flatMap(page=>dataFor(page).textOwner.entries.map(row=>row.object)),{signal});
  const current=()=>{abort(signal);validateDraftCapture(draftCapture,{signal});for(const [page,data]of sourcePages)if(dataFor(page)!==data)fail('The source PDF view changed during Copy.');for(const row of rows.values())if(registry.get(row.entry.id)!==row.entry||value(row.entry,'revision')!==row.revision||value(row.entry,'currentCheckpoint').stateId!==row.checkpoint)fail('The PDF changed while Copy was being prepared.');
   if(!sameCopyValue(scene,copyScene(objects.map(object=>object.toObject(properties))))||!transforms.every((matrix,index)=>sameCopyValue(matrix,Array.from(objects[index].calcTransformMatrix()))))fail('The artwork changed while Copy was being prepared.');};
  const entries=[];
  try{for(const row of rows.values()){current();const session=await Reflect.apply(forkSession,row.entry.session,[{signal}]);entries.push({session,bytes:row.entry.bytes,savedAssetId:row.entry.id,savedStateId:row.checkpoint});current();}
   current();const token=Object.freeze({}),data={scene,transforms,hadParents,entries,released:false};copies.set(token,data);copyHolds.add(data);return token;
  }catch(error){try{closeCopyEntries(entries);}catch{}throw error;}
 }
 async function preflightSceneCopy(entries,retainedAssetIds,signal){
  if(!Array.isArray(retainedAssetIds)||retainedAssetIds.length>8||new Set(retainedAssetIds).size!==retainedAssetIds.length)fail('Copy requires the exact bounded destination PDF asset list.');
  const retained=retainedAssetIds.map(entryFor),all=[...retained,...entries];
  if(all.length>8||all.reduce((sum,entry)=>sum+entry.bytes.length,0)>67108864)fail('This copy would exceed the saved document PDF asset limit.');
  const states=all.map(entry=>({entry,revision:value(entry,'revision'),checkpoint:value(entry,'currentCheckpoint').stateId}));
  const current=()=>{abort(signal);for(const row of states)if(registry.get(row.entry.id)!==row.entry||value(row.entry,'revision')!==row.revision||value(row.entry,'currentCheckpoint').stateId!==row.checkpoint)fail('The artwork changed during copy admission.');};
  let payloadBytes=0;for(const entry of all){current();const saved=await call(entry,'save',{}, {signal});current();if(!(saved.result.blob instanceof Blob))fail('The copied artwork returned an invalid saved state.');payloadBytes+=saved.result.blob.size;if(saved.result.blob.size>201326592||payloadBytes>201326592)fail('This copy would exceed the saved document PDF state limit.');}current();
 }
 // Opt-in handoff custody: retire the unused native forest before entering
 // the project loader, while pendingHydration still pins its independent owners.
 function sceneCopyRetirement(canvas,candidates,scene){
  if(!(canvas instanceof fabric.StaticCanvas)||!nativeWeakRef||typeof weakTarget!=='function')fail('Prepared view retirement requires its actual native caller canvas.');
  currentCopyDisposal();nativeCanvasDispatch(canvas);const custody=nativeCustody(canvas),before=new WeakSet(liveNativeGraph(canvas,{custody})),resources=new Set(),rows=new WeakMap();
  const context={custody,targetRef:custody.targetRef,before,retired:new WeakSet(),createdNative:new WeakSet(),nativeAdmissionClosed:false,unknownCustody:false,copyDisposers:new WeakMap()};custody.admissionClosed=false;
  const allowed=nativeCleanupPermission(context),stock=copyDisposeMethods;
  const method=object=>{let current=object,depth=0;while(current&&++depth<=48){const d=Object.getOwnPropertyDescriptor(current,'dispose');if(d){if(!Object.hasOwn(d,'value')||typeof d.value!=='function'||!stock.has(d.value))fail('Prepared view retirement requires unchanged synchronous native disposal.');return d.value;}current=Object.getPrototypeOf(current);}return null;};
  const membership=object=>{const row=rows.get(object);if(!row)return !context.nativeAdmissionClosed;if(Object.getPrototypeOf(object)!==row.prototype)return false;
   const children=ownValue(object,'_objects');if(row.children&&(!Array.isArray(children)||!sameNativeArray(children,row.children)))return false;
   const edges=nativeEdgeEntries(object);return edges.length===row.edges.length&&edges.every(([key,value],index)=>key===row.edges[index][0]&&value===row.edges[index][1]);};
  context.allowsNative=object=>allowed(object)&&(!context.nativeAdmissionClosed||rows.has(object)&&membership(object));
  const retain=values=>{for(const object of liveNativeGraph({_objects:values},{custody}))if(!before.has(object)){resources.add(object);context.createdNative.add(object);if(!rows.has(object)){const children=ownValue(object,'_objects'),dispose=method(object);if(dispose)context.copyDisposers.set(object,dispose);rows.set(object,{object,dispose,prototype:Object.getPrototypeOf(object),children:!pages.has(object)&&Array.isArray(children)?children.slice():null,edges:nativeEdgeEntries(object)});}}};context.retainCopyNative=retain;
  const cleanup=values=>{retain([...values,...candidates]);return()=>optionCleanup([...resources],object=>candidates.has(object),nativeOptionKeys(scene),context.allowsNative,context.retired,context.copyDisposers)();};
  return {context,resources,rows,cleanup,phase:'preparing',finish(objects,current){retain(objects);
   context.nativeAdmissionClosed=true;custody.admissionClosed=true;this.objects=objects.slice();this.current=current;this.phase='prepared';},
   release(){return cleanup([...(this.objects||[]),...candidates])();},
   settle(){this.phase='settled';context.nativeAdmissionClosed=true;custody.admissionClosed=true;context.retainCopyNative=null;resources.clear();candidates.clear();this.objects=null;this.current=null;}};
 }
 function retireSceneCopyViews(prepared){
  const data=preparedCopies.get(prepared),retirement=data?.retirement;if(!retirement||retirement.directInstallation||retirement.phase!=='prepared')fail('Prepared view retirement is foreign, unsupported or already attempted.');
  retirement.current();for(const object of retirement.resources){const row=retirement.rows.get(object);if(!retirement.context.allowsNative(object)||row.dispose&&!exactDataMethod(object,'dispose',row.dispose))fail('The prepared native forest was adopted, changed or is no longer detached.');}
  retirement.phase='retiring';let failed=false,failure;try{retirement.release();}catch(error){failed=true;failure=error;}
  if(!failed)for(const object of retirement.resources)if(retirement.rows.get(object).dispose&&!retirement.context.retired.has(object)){failed=true;failure=new Error('The prepared native resource remains owned by another native scene.');break;}
  if(!failed)for(const page of data.candidates)if(!pages.get(page)?.disposed){failed=true;failure=new Error('The prepared PDF view remains owned by another native scene.');break;}
  retirement.phase=failed?'failed':'retired';if(failed)throw failure;
 }
 function commitRetiredSceneCopy(data){
  const retirement=data.retirement;if(!retirement)return;
  if(retirement.directInstallation){
   if(retirement.phase!=='prepared')fail('The prepared installation is no longer available.');retirement.current();
   const canvas=Reflect.apply(weakTarget,retirement.context.targetRef,[]);if(!canvas)fail('The copied artwork destination is unavailable.');nativeCanvasDispatch(canvas);
   const live=liveNativeGraph(canvas,{custody:retirement.context.custody});
   for(const object of data.objects)if(!live.has(object)||ownValue(object,'canvas')!==canvas||ownValue(object,'group'))fail('Every copied root must be installed on its actual destination canvas.');
   for(const page of data.candidates){const row=pages.get(page);if(!live.has(page)||!row||row.disposed||row.refreshing||row.renderRevision!==value(row.entry,'revision'))fail('Every copied PDF owner needs its installed destination view.');}
   return;
  }
  if(retirement.phase!=='retired')fail('Prepared native views must retire before this copy is committed.');retirement.current();
  const canvas=Reflect.apply(weakTarget,retirement.context.targetRef,[]);if(!canvas)fail('The copied artwork destination is unavailable.');const live=scenePages(canvas);
  for(const entry of data.entries)if(![...entry.views].some(page=>{const row=pages.get(page);return live.has(page)&&!data.candidates.has(page)&&row&&!row.disposed&&!row.refreshing&&row.renderRevision===value(entry,'revision');}))fail('Every copied PDF owner needs its reconstructed destination view.');
 }
 async function prepareCapturedSceneCopy(token,{signal,retainedAssetIds=[],consume=false,retirementCanvas,installationCanvas}={}){
  const source=copyData(token),entries=[],bindings=[],controller=new AbortController(),scope={candidates:new Set()},cancel=()=>controller.abort();let objects=[];
  signal?.addEventListener('abort',cancel,{once:true});if(signal?.aborted)controller.abort();replacementsBySignal.set(controller.signal,scope);
  let restoreStates,releaseObjects,retirement;
  const current=()=>{
   abort(controller.signal);if(!consume&&copyData(token)!==source)fail('Clipboard artwork was replaced during Paste.');
   if(restoreStates)for(const row of restoreStates)if(registry.get(row.entry.id)!==row.entry||row.entry.session!==row.session||!sessions.isSession(row.session)
       ||value(row.entry,'revision')!==row.revision||!sameCopyValue(value(row.entry,'source'),row.source)
       ||!sameCopyValue(value(row.entry,'currentCheckpoint'),row.checkpoint))fail('The copied PDF state changed during native construction.');
  };
  try{
   if(retirementCanvas!==undefined&&installationCanvas!==undefined)fail('Choose one native copy destination policy.');
   if(retirementCanvas!==undefined||installationCanvas!==undefined){if(!source.entries.length)fail('Native copy custody requires copied PDF owners.');retirement=sceneCopyRetirement(installationCanvas===undefined?retirementCanvas:installationCanvas,scope.candidates,source.scene);retirement.directInstallation=installationCanvas!==undefined;scope.copyRetirement=retirement;scope.createdCandidates=scope.candidates;}
   current();for(const saved of source.entries){current();const id=crypto.randomUUID(),session=consume?saved.session:await Reflect.apply(forkSession,saved.session,[{signal:controller.signal}]);
    const entry={id,session,bytes:saved.bytes,views:new Set(),pendingHydration:true,coldAliases:new Map()};entries.push(entry);
    entry.coldAliases.set(saved.savedStateId,Reflect.apply(getters.currentCheckpoint,session,[]).stateId);
    registry.set(id,entry);sessionEntries.set(session,entry);bindings.push({savedAssetId:saved.savedAssetId,assetId:id});current();
   }
   if(consume){copies.delete(token);copyHolds.delete(source);source.released=true;source.entries=[];}
   await preflightSceneCopy(entries,retainedAssetIds,controller.signal);current();
   hydrations.set(bindings,{entries,bindings:bindings.map(row=>({...row}))});const scene=rebindAssets(copyScene(source.scene),bindings);
   if(entries.length)restoreStates=entries.map(entry=>({entry,session:entry.session,source:value(entry,'source'),revision:value(entry,'revision'),checkpoint:value(entry,'currentCheckpoint')}));
   current();
   if(typeof enlivenObjects!=='function')fail('Native scene construction is unavailable.');
   if(copyDescriptors(scene).length){const restored=await prepareRestoredScene(scene,{signal:controller.signal,assertCurrent:current,candidates:scope.candidates,cleanupNative:retirement?.cleanup});objects=restored.objects;releaseObjects=restored.release;}
   else objects=await Reflect.apply(enlivenObjects,fabric.util,[scene,{signal:controller.signal}]);current();
   if(!Array.isArray(objects)||objects.length!==source.scene.length)fail('The copied native scene is incomplete.');
   if(retirement){retirement.finish(objects,()=>{abort(signal);current();});releaseObjects=()=>retirement.release();}
   const prepared=Object.freeze({objects:Object.freeze(objects.slice())});preparedCopies.set(prepared,{entries,bindings,objects,candidates:scope.candidates,releaseObjects,retirement});return prepared;
  }catch(error){
   controller.abort();if(retirement){
    try{retirement.release();}catch{}
    try{if(!hydrations.has(bindings))hydrations.set(bindings,{entries,bindings:bindings.map(row=>({...row}))});discardHydratedAssets(bindings);}catch{}
    retirement.settle();
   }else{
    try{disposeCopiedObjects(objects,scope.candidates,releaseObjects);}catch{}
    hydrations.delete(bindings);for(const entry of entries){registry.delete(entry.id);sessionEntries.delete(entry.session);try{Reflect.apply(closeSession,entry.session,[]);}catch{}}
   }
   if(consume&&!source.released){copies.delete(token);copyHolds.delete(source);source.released=true;const transferred=new Set(entries.map(entry=>entry.session));try{closeCopyEntries(source.entries.filter(entry=>!transferred.has(entry.session)));}catch{}source.entries=[];}
   throw error;
  }finally{replacementsBySignal.delete(controller.signal);signal?.removeEventListener('abort',cancel);}
 }
 function commitSceneCopy(prepared){const data=preparedCopies.get(prepared);if(!data)fail('The copied scene is foreign or already settled.');commitRetiredSceneCopy(data);commitHydratedAssets(data.bindings);preparedCopies.delete(prepared);data.retirement?.settle();}
 function disposeCopiedObjects(objects,candidates,release){let failed=false,failure;try{if(release)release();else cleanupAll(objects.map(object=>()=>object.dispose?.()));}catch(error){failed=true;failure=error;}try{cleanupAll([...candidates].filter(page=>!pages.get(page)?.disposed).map(page=>()=>page.dispose()));}catch(error){if(!failed){failed=true;failure=error;}}if(failed)throw failure;}
 function discardSceneCopy(prepared){const data=preparedCopies.get(prepared);if(!data)fail('The copied scene is foreign or already settled.');preparedCopies.delete(prepared);let failed=false,failure;try{if(data.retirement)data.retirement.release();else disposeCopiedObjects(data.objects,data.candidates,data.releaseObjects);}catch(error){failed=true;failure=error;}
  try{discardHydratedAssets(data.bindings);}catch(error){if(!failed){failed=true;failure=error;}}finally{data.retirement?.settle();}if(failed)throw failure;
 }
 async function prepareSceneCopy(objects,options={}){const token=await captureSceneCopy(objects,options);try{return await prepareCapturedSceneCopy(token,{...options,consume:true});}finally{if(copies.has(token))releaseSceneCopy(token);}}
 function collect(ids){const retained=new Set(ids);cleanupAll(Array.from(registry.values()).filter(entry=>!retained.has(entry.id)&&!entry.views.size&&!entry.pendingHydration).map(entry=>()=>{registry.delete(entry.id);sessionEntries.delete(entry.session);Reflect.apply(closeSession,entry.session,[]);}));}
 // Display-only scalars from the live private owner and its completed view.
 // Pending path IDs and saved import summaries do not describe published controls.
 function inspectionState(page){
  const data=dataFor(page),entry=data.entry,source=value(entry,'source'),stats=value(entry,'statistics'),revision=value(entry,'revision');
  const sourcePathCount=stats.pathCount,editableTextCount=data.textOwner?.entries.length,segments=data.tile?.segments;
  if(source.byteLength!==entry.bytes.length||typeof source.sha256!=='string'||!/^[a-f0-9]{64}$/.test(source.sha256)
   ||!Number.isSafeInteger(source.pageNumber)||source.pageNumber<1||!Number.isSafeInteger(sourcePathCount)||sourcePathCount<0
   ||!Number.isSafeInteger(editableTextCount)||editableTextCount<0||!Array.isArray(segments)
   ||!Number.isSafeInteger(revision)||revision<0||!Number.isSafeInteger(data.renderRevision)||data.renderRevision<0)fail('The current PDF artwork summary is unavailable.');
  return {schema:'figureStudio.pdfDenseInspection.v1',assetId:entry.id,sourceSha256:source.sha256,sourceByteLength:entry.bytes.length,pageNumber:source.pageNumber,
   sourcePathCount,editableTextCount,activePathControlCount:segments.filter(segment=>segment.kind==='nativePath').length,
   revision,renderRevision:data.renderRevision,updating:Boolean(data.refreshing||data.renderRevision!==revision)};
 }
 function statistics(){let views=0,bitmaps=0,nativeTexts=0;for(const entry of registry.values())for(const page of entry.views){const data=pages.get(page);views++;bitmaps+=(data?.tile?.segments||[]).filter(segment=>segment.bitmap).length;nativeTexts+=data?.textOwner?.entries.length||0;}return {sourceOwners:registry.size+Array.from(copyHolds).reduce((sum,data)=>sum+data.entries.length,0),views,bitmaps,nativeTexts};}
 return Object.freeze({SCHEMA,PdfDensePage,create,beginSceneReplacement,finishSceneReplacement,hasDenseCanvasRestore,prepareCanvasRestore,commitCanvasRestore,discardCanvasRestore,registerCanvasRestoreConnectorText,removeCanvasRestoreConnectorText,statistics,inspectionState,captureDrafts,validateDraftCapture,captureAssetStates,validateAssetStates,canSerializeSvg,exportSceneSvg,prepareTextEditing,refresh:(page,{signal}={})=>refresh(page,{signal}),commitText,acquirePath,commitPath,commitPaths,command,read,saveAssets,hydrateAssets,rebindAssets,discardHydratedAssets,commitHydratedAssets,collect,captureSceneCopy,releaseSceneCopy,sceneCopySnapshot,prepareCapturedSceneCopy,prepareSceneCopy,retireSceneCopyViews,commitSceneCopy,discardSceneCopy,
  objectById:(page,id)=>{dataFor(page);return Array.from(objectPagesKeys(page)).find(object=>object.figureId===id)||null;},
  textEntries:page=>dataFor(page).textOwner.entries.slice(),isPage:object=>pages.has(object)&&!pages.get(object).disposed,pageForObject:object=>objectPages.get(object)||null,descriptor:page=>serialDescriptor(dataFor(page).entry)});
});
