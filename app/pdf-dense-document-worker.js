/* Unwired, document-owned worker: canonical pools and source bytes stay here. */
'use strict';
importScripts('./pdf-generated-number-tokens.js','./pdf-text-spacing.js','./pdf-editable-import.js','./pdf-decoded-svg-number-precision.js','./pdf-native-glyph-records.js','./pdf-dense-source-numbers.js','./pdf-dense-font-repertoire.js','./pdf-dense-text-state.js','./pdf-dense-leaf-store.js','./pdf-dense-source-owner-profiles.js','./pdf-dense-group-history.js','./pdf-dense-document-checkpoints.js','./pdf-dense-native-canvas.js','./pdf-dense-vector-replay.js');
const protocol='figureStudio.pdfDenseDocument.v1',controllers=new Map(),contexts=new Map();
const legacySaveSchema='figureStudio.pdfDenseDocumentSave.v1',saveSchema='figureStudio.pdfDenseDocumentSave.v2',groupApi=FigureStudioPdfDenseGroupHistory,groupProto=groupApi.DenseGroupDocument.prototype,groupMethods=Object.fromEntries(['placement','serialize','statistics','children','node','serializeGraph','close'].map(name=>[name,groupProto[name]])),groupRevision=Object.getOwnPropertyDescriptor(groupProto,'revision').get,checkpointApi=FigureStudioPdfDenseDocumentCheckpoints,checkpointMethods=Object.fromEntries(['checkpoint','execute','_step','goToState','close'].map(name=>[name,checkpointApi.DenseDocumentCheckpoints.prototype[name]])),mutations=new Set(['edit','group','move','release','undo','redo','goToState']);
let owner=null,store=null,authoredDocument=null,journal=null,nativeFactory=null,sourceBytes=null,textIds=[],textRevisions=new Map(),queue=Promise.resolve(),sequence=0;
const storeFork=FigureStudioPdfDenseLeafStore.forkCurrent,sharesBase=FigureStudioPdfDenseLeafStore.sharesImmutableBase;
const requestKey=request=>JSON.stringify([request.session,request.requestId]);
function context(){return {owner,store,authoredDocument,journal,nativeFactory,sourceBytes,textIds,textRevisions};}
function selectContext(value){owner=value?.owner||null;store=value?.store||null;authoredDocument=value?.authoredDocument||null;journal=value?.journal||null;nativeFactory=value?.nativeFactory||null;sourceBytes=value?.sourceBytes||null;textIds=value?.textIds||[];textRevisions=value?.textRevisions||new Map();}
function retireContext(value){let failed=false,failure;for(const operation of [()=>value.journal&&Reflect.apply(checkpointMethods.close,value.journal,[]),()=>value.authoredDocument&&Reflect.apply(groupMethods.close,value.authoredDocument,[])])try{operation();}catch(error){if(!failed){failed=true;failure=error;}}if(failed)throw failure;}
const docCall=(name,...args)=>Reflect.apply(groupMethods[name],authoredDocument,args),revision=()=>authoredDocument?Reflect.apply(groupRevision,authoredDocument,[]):store?.revision;
const journalCall=(name,...args)=>Reflect.apply(checkpointMethods[name],journal,args);
function error(message,code='PDF_DENSE_DOCUMENT_REFUSED'){const e=new Error(message);e.code=code;return e;}
function packet(request,body,transfer=[]){self.postMessage({protocol,session:request.session,requestId:request.requestId,source:store?.source(),revision:revision(),...body},transfer);}
function check(request){if(!store||!groupApi.isDocumentFor(authoredDocument,store)||request.session!==owner)throw error('Dense document session is closed or foreign.');if(request.expectedRevision!==revision())throw error('Dense document revision changed.','PDF_DENSE_STALE_REVISION');}
function aborted(signal){if(signal.aborted){const e=new Error('Dense document task was cancelled.');e.name='AbortError';throw e;}}
const yieldControl=()=>typeof MessageChannel==='function'?new Promise(resolve=>{const channel=new MessageChannel();channel.port1.onmessage=()=>{channel.port1.close();channel.port2.close();resolve();};channel.port2.postMessage(null);}):new Promise(resolve=>setTimeout(resolve,0));
function withPathPlanes(row){return {...row,...(row.pathChunks?{pathPlaneChains:row.pathChunks.map(chunk=>store.plane(chunk.plane))}:{})};}
function proxyRecord(row){const clipChain=[];let index=row.clipIndex;while(index){const clip=store.clip(index);clipChain.push(withPathPlanes(clip));index=clip.parentClipIndex;}return {...withPathPlanes(row),clipChain:clipChain.reverse(),placement:docCall('placement',row.id)};}
function documentState(){const authoredTextUpdates=[];for(const id of textIds){const version=store.authoredTextRevision(id);if(textRevisions.get(id)!==version){const row=store.read(id);authoredTextUpdates.push({id,authoredText:row.authoredText||null,editedFields:row.editedFields||[]});textRevisions.set(id,version);}}return {checkpoint:journalCall('checkpoint'),authoringStatistics:docCall('statistics'),leafStatistics:store.statistics(),textPlacements:textIds.map(id=>({id,placement:docCall('placement',id)})),authoredTextUpdates};}
function initialMetadata(){const textRecords=store.textRecords().map(proxyRecord);textIds=textRecords.map(row=>row.id);textRevisions=new Map(textIds.map(id=>[id,store.authoredTextRevision(id)]));return {frame:store.frame(),operationNames:store.operationNames(),statistics:store.statistics(),currentCheckpoint:journalCall('checkpoint'),authoringStatistics:docCall('statistics'),textRecords,nativeGlyphRecords:store.nativeGlyphRecords(),nativeGlyphSvgFragments:textRecords.map(row=>FigureStudioPdfDenseVectorReplay.nativeGlyphSvg(store,row.id,{document:authoredDocument})),fontDescriptors:store.fonts(),sourceFontRepertoires:store.sourceFontRepertoires()};}
async function captureNativeFactory(signal){const source=store.source(),version=revision(),loading=pdfjsLib.getDocument({data:sourceBytes.slice(),fontExtraProperties:true,isOffscreenCanvasSupported:false,useSystemFonts:true});try{const handle=await loading.promise,page=await handle.getPage(source.pageNumber),viewport=page.getViewport({scale:1}),ownerKey={},token=await FigureStudioPdfDenseNativeCanvas.capture({page,pdfjs:pdfjsLib,viewport,ownerKey,signal,assertCurrentSource:()=>store?.source().sha256===source.sha256&&sourceBytes?.length===source.byteLength&&revision()===version});return FigureStudioPdfDenseNativeCanvas.consume(token,ownerKey);}finally{await loading.destroy();}}
async function run(request,controller){const signal=controller.signal,started=performance.now();let transfer=[],admittedRoot=false;selectContext(contexts.get(request.session));try{
 aborted(signal);let result,savedGraph=null;
 if(request.action==='close-document'){const closing=contexts.get(request.session);if(closing){contexts.delete(request.session);retireContext(closing);}return;}
 if(request.action==='open'||request.action==='hydrate'){
  if(contexts.size||owner||store)throw error('A dense worker may authenticate only one root source.');admittedRoot=true;owner=request.session;sourceBytes=new Uint8Array(request.input.bytes);
  if(sourceBytes.byteLength<1||sourceBytes.byteLength>FigureStudioPdfDenseLeafStore.LIMITS.sourceBytes)throw error('Invalid dense original source bytes.');
  importScripts('../vendor/pdfjs-legacy/pdf.worker.js','../vendor/pdfjs-legacy/pdf.js','../vendor/pdf-lib/pdf-lib.min.js');
  pdfjsLib.GlobalWorkerOptions.workerSrc=new URL('../vendor/pdfjs-legacy/pdf.worker.js',self.location.href).href;
  if(request.action==='open'){
   store=await FigureStudioPdfDenseLeafStore.open({bytes:sourceBytes,pageNumber:request.input.pageNumber,pdfjs:pdfjsLib,pdfLib:PDFLib,signal,yieldControl,onProgress:progress=>packet(request,{type:'progress',progress})});
  }else{
   if(request.input.payloadBlob&&request.input.payloadBlob.size>201326592)throw error('Dense saved payload exceeds the existing document payload envelope.');const serialized=request.input.payloadBlob?await request.input.payloadBlob.text():request.input.serializedPayload;if(typeof serialized!=='string'||serialized.length>201326592)throw error('Dense saved payload exceeds the existing document payload envelope.');
   const parsed=JSON.parse(serialized);let payload=parsed;if([legacySaveSchema,saveSchema].includes(parsed?.schema)){if(Object.keys(parsed).sort().join(',')!=='graph,schema,store')throw error('Unknown dense document save fields.');payload=parsed.store;savedGraph=parsed.graph;}else if(parsed?.schema!=='figureStudio.pdfDenseLeafStore.v1')throw error('Unsupported dense document save format.');
   if(parsed?.schema===saveSchema){store=await FigureStudioPdfDenseLeafStore.hydrateSparse(payload,{bytes:sourceBytes,pdfjs:pdfjsLib,pdfLib:PDFLib,signal,yieldControl,onProgress:progress=>packet(request,{type:'progress',progress:{...progress,coldBaseVerification:true}})});}
   else{
    store=await FigureStudioPdfDenseLeafStore.hydrate(payload,{signal,yieldControl});
    const digest=await crypto.subtle.digest('SHA-256',sourceBytes),sha=Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,'0')).join('');
    if(store.source().sha256!==sha||store.source().byteLength!==sourceBytes.length)throw error('Cold dense source bytes differ from the saved canonical owner.');
    const fresh=await FigureStudioPdfDenseLeafStore.open({bytes:sourceBytes,pageNumber:store.source().pageNumber,pdfjs:pdfjsLib,pdfLib:PDFLib,signal,yieldControl,onProgress:progress=>packet(request,{type:'progress',progress:{...progress,coldBaseVerification:true}})});
    store=await FigureStudioPdfDenseLeafStore.authenticateSavedBase(store,fresh,{signal,yieldControl});
   }
  }
  if(!store.source().originalDecimalProofComplete)throw error('Dense document requires complete original numeric proof.');
  authoredDocument=savedGraph?groupApi.hydrate({store,payload:savedGraph}):groupApi.create({store});
  journal=checkpointApi.create({document:authoredDocument,store});
  nativeFactory=await captureNativeFactory(signal);
  aborted(signal);result=initialMetadata();contexts.set(owner,context());
 }else{
  check(request);const input=request.input||{};
  if(request.action==='fork'){
   if(Object.keys(input).length!==1||typeof input.session!=='string'||input.session.length<1||input.session.length>200||contexts.has(input.session)||input.session===owner||contexts.size>=8)throw error('An independent PDF copy requires a new bounded private document owner.');
   const parent=context(),graph=docCall('serializeGraph');let child;
   try{const childStore=await storeFork(store,{expectedRevision:store.revision,signal,yieldControl});check(request);aborted(signal);if(!sharesBase(store,childStore))throw error('The PDF copy has no actual shared immutable source proof.');
    const document=groupApi.hydrate({store:childStore,payload:graph});child={owner:input.session,store:childStore,authoredDocument:document,journal:null,nativeFactory,sourceBytes,textIds:[],textRevisions:new Map()};child.journal=checkpointApi.create({document,store:childStore});
    selectContext(child);const documentMetadata=initialMetadata();child=context();result={forkSession:input.session,source:store.source(),revision:revision(),document:documentMetadata};selectContext(parent);check(request);aborted(signal);contexts.set(input.session,child);
   }catch(failure){if(child)try{retireContext(child);}catch{}throw failure;}finally{selectContext(parent);}
  }else if(request.action==='read'){
   if(!Array.isArray(input.ids)||input.ids.length>32)throw error('Read requests are bounded to 32 native proxies.');result=input.ids.map(id=>proxyRecord(store.read(id)));
  }else if(request.action==='inventory'){
   if(!Number.isInteger(input.start)||input.start<0||!Number.isInteger(input.count)||input.count<1||input.count>128)throw error('Inventory requires a bounded row window.');
   result=[];for(let i=input.start;i<Math.min(store.size,input.start+input.count);i++){const id=store.idAt(i),row=store.read(id);result.push({id,paintOrdinal:i,kind:row.kind,operatorIndex:row.operatorIndex,scopeIndex:row.scopeIndex,clipIndex:row.clipIndex,bounds:store.bounds(id),unicode:row.text?.unicode,placement:docCall('placement',id)});}
  }else if(request.action==='children'){
   result=docCall('children',input.id||'root',{start:input.start??0,count:input.count??128});
  }else if(request.action==='node'){
   result=docCall('node',input.id);
  }else if(request.action==='checkpoint'){
   result=journalCall('checkpoint');
  }else if(request.action==='goToState'){
   result=journalCall('goToState',{stateId:input.stateId,expectedRevision:request.expectedRevision,signal});
  }else if(request.action==='queryRect'){
   const ids=FigureStudioPdfDenseVectorReplay.queryRect(store,input.box,{document:authoredDocument});result={count:ids.length,ids:ids.slice(0,128),truncated:ids.length>128};
  }else if(request.action==='hitPath'){
   const canvas=new OffscreenCanvas(1,1);result=FigureStudioPdfDenseVectorReplay.hitPath(store,canvas.getContext('2d'),input.x,input.y,{tolerance:input.tolerance||0,limit:input.limit||1,document:authoredDocument}).map(proxyRecord);
  }else if(request.action==='renderTile'){
   result=await FigureStudioPdfDenseVectorReplay.renderTile(store,{...input,document:authoredDocument,nativeFactory,signal,yieldControl});for(const segment of result.segments)if(segment.kind==='nativePath')segment.record=proxyRecord(segment.record);transfer=result.segments.filter(segment=>segment.bitmap).map(segment=>segment.bitmap);
  }else if(['edit','group','move','release'].includes(request.action)){
   aborted(signal);const command=request.action==='edit'?{type:'leafEdit',changes:input.changes}:{...input,type:request.action};result=journalCall('execute',{expectedRevision:request.expectedRevision,command,signal});
  }else if(request.action==='undo'||request.action==='redo'){
   aborted(signal);result=journalCall('_step',request.action==='redo',request.expectedRevision,signal);
  }else if(request.action==='save'||request.action==='saveDraft'){
   if(request.action==='saveDraft'&&(Object.keys(input).length!==1||!Object.hasOwn(input,'changes')||!Array.isArray(input.changes)||!input.changes.length))throw error('A read-only text save requires its bounded draft changes.');
   const payload=await docCall('serialize',{signal,yieldControl,storage:'sparse',...(request.action==='saveDraft'?{authoredDrafts:input.changes}:{})});aborted(signal);check(request);result={blob:new Blob([JSON.stringify({schema:saveSchema,...payload})],{type:'application/json'}),source:store.source(),revision:revision()};
  }else if(request.action==='exportSvg'){
   const parts=[];const metadata=await FigureStudioPdfDenseVectorReplay.writeSvg(store,text=>parts.push(text),{signal,yieldControl,document:authoredDocument});aborted(signal);result={blob:new Blob(parts,{type:'image/svg+xml'}),metadata};
  }else if(request.action==='exportPdf'){
   if(!self.PDFLib)importScripts('../vendor/pdf-lib/pdf-lib.min.js');const exported=await FigureStudioPdfDenseVectorReplay.buildPdf(store,sourceBytes,PDFLib,{signal,yieldControl,document:authoredDocument});aborted(signal);result={bytes:exported.bytes,metadata:exported.metadata};transfer=[result.bytes.buffer];
  }else throw error('Unknown dense document operation.');
 }
 packet(request,{type:'complete',result,...(mutations.has(request.action)?{documentState:documentState()}:{}),metrics:{elapsedMs:performance.now()-started,sequence:++sequence}},transfer);
 }catch(e){for(const value of transfer)if(typeof value.close==='function')try{value.close();}catch{}packet(request,{type:'error',name:e?.name||'Error',code:e?.code||'',message:String(e?.message||e)});if(admittedRoot){try{retireContext(context());}catch{}contexts.delete(request.session);selectContext(null);}}
 finally{if(contexts.has(request.session))contexts.set(request.session,context());controllers.delete(requestKey(request));}}
self.onmessage=event=>{const request=event.data;if(request?.protocol!==protocol||typeof request.session!=='string'||typeof request.requestId!=='string')return;
 const key=requestKey(request);if(request.action==='cancel'){controllers.get(key)?.controller.abort();return;}
 if(request.action==='close-document')for(const pending of controllers.values())if(pending.session===request.session)pending.controller.abort();
 if(controllers.has(key))return;const controller=new AbortController();controllers.set(key,{controller,session:request.session});queue=queue.catch(()=>{}).then(()=>run(request,controller));
};
