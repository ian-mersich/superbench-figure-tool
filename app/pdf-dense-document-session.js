/* Unwired main-thread handle. The canonical dense store never leaves its worker. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.FigureStudioPdfDenseDocumentSession=api;})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const protocol='figureStudio.pdfDenseDocument.v1',issued=new WeakMap(),moduleUrl=typeof document==='object'?(document.currentScript?.src||document.baseURI):null;
const mutation=new Set(['edit','group','move','release','undo','redo','goToState']);
function fail(message,code='PDF_DENSE_DOCUMENT_REFUSED'){const e=new Error(message);e.code=code;return e;}
function abortError(){const e=new Error('Dense document task was cancelled.');e.name='AbortError';return e;}
function rejectPending(d,error){for(const pending of d.pending.values()){pending.cleanup();pending.reject(error);}d.pending.clear();}
function terminate(transport,error){if(transport.closed)return;transport.closed=true;try{transport.worker.terminate();}finally{for(const d of transport.members.values()){d.closed=true;rejectPending(d,error);}transport.members.clear();}}
function releaseDocument(transport,session){if(transport.closed)return;try{transport.worker.postMessage({protocol,session,requestId:'release:'+crypto.randomUUID(),action:'close-document'});}catch(error){terminate(transport,error);}}
function close(d,error=fail('Dense document session was closed.')){if(d.closed)return;d.closed=true;rejectPending(d,error);const transport=d.transport;transport.members.delete(d.session);if(!transport.members.size)terminate(transport,error);else releaseDocument(transport,d.session);}
function dataFor(session){const d=issued.get(session);if(!d||d.closed)throw fail('Dense document session is closed or foreign.');return d;}
function sourceSame(a,b){return a?.sha256===b?.sha256&&a?.byteLength===b?.byteLength&&a?.pageNumber===b?.pageNumber;}
function closeBitmaps(result){for(const segment of result?.segments||[])try{segment.bitmap?.close();}catch{}}
function stateSame(d,state,revision,rows=d.textRecords||[]){const checkpoint=state?.checkpoint,statistics=state?.authoringStatistics,placements=state?.textPlacements,updates=state?.authoredTextUpdates||[];if(!Array.isArray(rows)||rows.some(row=>!row||typeof row.id!=='string'||!row.id)||checkpoint?.schema!=='figureStudio.pdfDenseCheckpoint.v1'||typeof checkpoint.stateId!=='string'||!checkpoint.stateId||!sourceSame(checkpoint.source,d.source)||checkpoint.documentRevision!==revision||!Number.isSafeInteger(checkpoint.leafRevision)||checkpoint.leafRevision<0||statistics?.revision!==revision||statistics.leafRevision!==checkpoint.leafRevision||!Array.isArray(placements)||placements.length!==rows.length||!Array.isArray(updates)||updates.length>rows.length)return false;const allIds=new Set(rows.map(row=>row.id)),ids=new Set(allIds),seen=new Set();if(allIds.size!==rows.length||!placements.every(row=>row&&ids.delete(row.id)&&row.placement?.documentRevision===revision&&row.placement.leafRevision===checkpoint.leafRevision)||ids.size)return false;return updates.every(row=>{if(!row||!allIds.has(row.id)||seen.has(row.id))return false;seen.add(row.id);const value=row.authoredText;return value===null||value?.schema==='figureStudio.pdfDenseTextState.v1'&&value.id===row.id&&value.base?.sourceSha256===d.source.sha256&&value.base.sourceByteLength===d.source.byteLength&&value.base.pageNumber===d.source.pageNumber;});}
function textView(d,row,fragment=false){const {authoredText,editedFields,...source}=row,current=d.textStates?.get(row.id)||{authoredText:authoredText||null,editedFields:editedFields||[]};return {...source,...(current.authoredText?{authoredText:current.authoredText}:{}),...(!fragment&&current.editedFields.length?{editedFields:current.editedFields}:{}),placement:d.textPlacements?.get(row.id)||row.placement};}
class DenseDocumentSession{
 constructor(){/* Only open/hydrate publish a completed document owner. */}
 get revision(){return dataFor(this).revision;}
 get source(){return structuredClone(dataFor(this).source);}
 get frame(){return structuredClone(dataFor(this).frame);}
 get operationNames(){return structuredClone(dataFor(this).operationNames);}
 get statistics(){const d=dataFor(this);return {...structuredClone(d.statistics),revision:d.revision};}
 get authoringStatistics(){return structuredClone(dataFor(this).authoringStatistics);}
 get currentCheckpoint(){return structuredClone(dataFor(this).currentCheckpoint);}
 get textRecords(){const d=dataFor(this);return structuredClone(d.textRecords.map(row=>textView(d,row)));}
 get nativeGlyphRecords(){return structuredClone(dataFor(this).nativeGlyphRecords);}
 get nativeGlyphSvgFragments(){const d=dataFor(this);return structuredClone(d.nativeGlyphSvgFragments?.map(row=>textView(d,row,true)));}
 get sourceFontRepertoires(){return structuredClone(dataFor(this).sourceFontRepertoires||[]);}
 get fontDescriptors(){return structuredClone(dataFor(this).fontDescriptors);}
 get closed(){return !issued.has(this)||issued.get(this).closed;}
 close(){const d=issued.get(this);if(d)close(d);}
 async fork(options={}){return fork(this,options);}
 async request(action,input={},options={}){const d=dataFor(this);if(['open','hydrate','cancel','fork','close-document'].includes(action)||typeof action!=='string')throw fail('Invalid live dense document operation.');return request(d,action,input,options);}
}
function request(d,action,input,{signal,onProgress,deadlineMs=115000}={},transfer=[]){
 if(d.closed)return Promise.reject(fail('Dense document is closed.'));if(signal?.aborted)return Promise.reject(abortError());if(!Number.isInteger(deadlineMs)||deadlineMs<100||deadlineMs>115000)return Promise.reject(fail('Dense document deadline exceeds the owned worker envelope.'));
 const requestId=String(++d.next),expectedRevision=d.revision;
 return new Promise((resolve,reject)=>{let cancelled=false;const cancel=()=>{cancelled=true;d.worker.postMessage({protocol,session:d.session,requestId,action:'cancel'});};
  // Once admitted, a bounded edit is atomic and returns its committed revision.
  // Read/render/export cancellation can end between cooperative batches.
  if(signal&&!mutation.has(action))signal.addEventListener('abort',cancel,{once:true});
  const timer=setTimeout(()=>terminate(d.transport,fail('Dense document worker exceeded its owned deadline.','PDF_DENSE_DEADLINE')),deadlineMs);
  const cleanup=()=>{clearTimeout(timer);signal?.removeEventListener('abort',cancel);};
  d.pending.set(requestId,{action,expectedRevision,onProgress,resolve:value=>{if(cancelled){closeBitmaps(value.result);reject(abortError());}else resolve(value);},reject,cleanup});
  try{d.worker.postMessage({protocol,session:d.session,requestId,action,expectedRevision,input},transfer);}catch(e){d.pending.delete(requestId);cleanup();reject(e);}
 });
}
function attachTransport(worker){const transport={worker,members:new Map(),reservations:new Set(),closed:false};
 worker.onmessage=event=>{const packet=event.data,d=transport.members.get(packet?.session);if(transport.closed||!d||d.closed||packet?.protocol!==protocol){closeBitmaps(packet?.result);return;}const pending=d.pending.get(packet.requestId);if(!pending){closeBitmaps(packet?.result);return;}
  if(packet.type==='progress'){pending.onProgress?.(packet.progress);return;}
  if(!['complete','error'].includes(packet.type))return;d.pending.delete(packet.requestId);pending.cleanup();
  if(packet.source&&!sourceSame(packet.source,d.source)){closeBitmaps(packet.result);terminate(transport,fail('Dense worker source ownership changed.'));pending.reject(fail('Dense worker source ownership changed.'));return;}
  if(packet.type==='error'){const error=fail(packet.message,packet.code);error.name=packet.name||'Error';pending.reject(error);return;}
  if(!sourceSame(packet.source,d.source)||!Number.isSafeInteger(packet.revision)||packet.revision<d.revision||(!mutation.has(pending.action)&&!['open','hydrate'].includes(pending.action)&&packet.revision!==pending.expectedRevision)){closeBitmaps(packet.result);terminate(transport,fail('Dense worker returned an incoherent document revision.'));pending.reject(fail('Dense worker returned an incoherent document revision.'));return;}
  const initial=['open','hydrate'].includes(pending.action),state=initial?initialState(packet.result):packet.documentState;
  if((initial||mutation.has(pending.action))&&!stateSame(d,state,packet.revision,initial?packet.result?.textRecords:undefined)){closeBitmaps(packet.result);terminate(transport,fail('Dense worker returned incoherent checkpoint ownership.'));pending.reject(fail('Dense worker returned incoherent checkpoint ownership.'));return;}
  d.revision=packet.revision;if(packet.documentState){d.currentCheckpoint=packet.documentState.checkpoint;d.authoringStatistics=packet.documentState.authoringStatistics;if(packet.documentState.leafStatistics)d.statistics=packet.documentState.leafStatistics;d.textPlacements=new Map(packet.documentState.textPlacements.map(row=>[row.id,row.placement]));for(const row of packet.documentState.authoredTextUpdates||[])d.textStates.set(row.id,{authoredText:row.authoredText,editedFields:row.editedFields||[]});}pending.resolve({result:packet.result,source:structuredClone(packet.source),revision:packet.revision,metrics:packet.metrics});
 };
 worker.onerror=event=>terminate(transport,fail(event.message||'Dense document worker failed.'));
 worker.onmessageerror=()=>terminate(transport,fail('Dense document worker transport failed.'));return transport;
}
function initialState(result){const rows=Array.isArray(result?.textRecords)?result.textRecords:null;return {checkpoint:result?.currentCheckpoint,authoringStatistics:result?.authoringStatistics,textPlacements:rows?.map(row=>({id:row?.id,placement:row?.placement})),authoredTextUpdates:rows?.filter(row=>row?.authoredText).map(row=>({id:row.id,authoredText:row.authoredText}))};}
function publish(d,opened){const result=opened.result,fields=['frame','operationNames','statistics','currentCheckpoint','authoringStatistics','textRecords','nativeGlyphRecords','nativeGlyphSvgFragments','fontDescriptors','sourceFontRepertoires'];if(!result||typeof result!=='object'||Object.keys(result).some(key=>!fields.includes(key))||!stateSame(d,initialState(result),opened.revision,result.textRecords))throw fail('Dense worker returned incoherent initial document ownership.');for(const field of fields)d[field]=structuredClone(result[field]);d.revision=opened.revision;d.textStates=new Map(d.textRecords.map(row=>[row.id,{authoredText:row.authoredText||null,editedFields:row.editedFields||[]}]));d.source=structuredClone(opened.source);const session=new DenseDocumentSession();issued.set(session,d);return session;}
async function create(action,{bytes,pageNumber=1,serializedPayload,payloadBlob,signal,onProgress,deadlineMs=115000}={}){
 if(!(bytes instanceof Uint8Array)||!bytes.length||bytes.length>33554432||!Number.isInteger(pageNumber)||pageNumber<1)throw fail('Invalid dense original source input.');if(signal?.aborted)throw abortError();if(typeof Worker!=='function'||!moduleUrl)throw fail('Dense document workers require the supported HTTP browser host.','PDF_DENSE_WORKER_UNAVAILABLE');
 const ownedBytes=bytes.slice(),digest=await crypto.subtle.digest('SHA-256',ownedBytes),sha256=Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,'0')).join('');if(signal?.aborted)throw abortError();
 const worker=new Worker(new URL('./pdf-dense-document-worker.js',moduleUrl)),transport=attachTransport(worker),d={worker,transport,session:crypto.randomUUID(),pending:new Map(),next:0,revision:0,source:{sha256,byteLength:ownedBytes.length,pageNumber},closed:false};transport.members.set(d.session,d);
 try{return publish(d,await request(d,action,{bytes:ownedBytes,pageNumber,serializedPayload,payloadBlob},{signal,onProgress,deadlineMs},[ownedBytes.buffer]));}catch(error){close(d,error);throw error;}
}
async function fork(session,options){const parent=dataFor(session),transport=parent.transport,version=parent.revision,checkpoint=parent.currentCheckpoint.stateId,childId=crypto.randomUUID();let child;
 if(transport.members.size+transport.reservations.size>=8)throw fail('A shared PDF source may have at most eight independent document owners.');transport.reservations.add(childId);
 try{const reply=await request(parent,'fork',{session:childId},options),result=reply.result;if(dataFor(session)!==parent||parent.revision!==version||parent.currentCheckpoint.stateId!==checkpoint)throw fail('The PDF source changed while preparing its independent copy.');
  if(result?.forkSession!==childId||!sourceSame(result.source,parent.source)||result.revision!==version||result.document?.currentCheckpoint?.stateId===checkpoint||result.document?.currentCheckpoint?.undoCount!==0||result.document?.currentCheckpoint?.redoCount!==0||result.document?.currentCheckpoint?.retainedStates!==1||result.document?.authoringStatistics?.undoCount!==0||result.document?.authoringStatistics?.redoCount!==0){const error=fail('Dense worker returned incoherent copied document ownership.');terminate(transport,error);throw error;}
  child={worker:parent.worker,transport,session:childId,pending:new Map(),next:0,revision:result.revision,source:structuredClone(parent.source),closed:false};transport.members.set(childId,child);
  try{return publish(child,{result:result.document,source:result.source,revision:result.revision});}catch(error){terminate(transport,error);throw error;}
 }catch(error){if(child)close(child,error);else releaseDocument(transport,childId);throw error;}finally{transport.reservations.delete(childId);}
}
return Object.freeze({open:options=>create('open',options),hydrate:options=>create('hydrate',options),isSession:value=>issued.has(value)&&!issued.get(value).closed,DenseDocumentSession});
});
