/* Unwired worker journal handles. Every state shares one immutable source owner;
 * handles never contain base pools or authorize a different/cold worker. */
(function(root,factory){const groups=typeof module==='object'&&module.exports?require('./pdf-dense-group-history.js'):root.FigureStudioPdfDenseGroupHistory;const api=factory(groups);if(typeof module==='object'&&module.exports)module.exports=api;else root.FigureStudioPdfDenseDocumentCheckpoints=api;})(typeof globalThis==='object'?globalThis:this,function(groups){
'use strict';
const issued=new WeakMap(),proto=groups.DenseGroupDocument.prototype,methods=Object.fromEntries(['statistics','prepare','commit','source','preflightHistory','_history'].map(name=>[name,proto[name]])),revisionOf=Object.getOwnPropertyDescriptor(proto,'revision').get,MAX_ACTIONS=groups.LIMITS.history;
const call=(s,name,...args)=>Reflect.apply(methods[name],s.document,args);
function refuse(message,code='PDF_DENSE_CHECKPOINT_REFUSED'){const e=new Error(message);e.code=code;throw e;}
function abort(signal){if(signal?.aborted){const e=new Error('Dense document action was cancelled before admission.');e.name='AbortError';throw e;}}
function state(owner){const s=issued.get(owner);if(!s||!groups.isDocumentFor(s.document,s.store)||Reflect.apply(revisionOf,s.document,[])!==s.revision)refuse('Dense checkpoint journal is closed, foreign, or changed outside its owner.','PDF_DENSE_CHECKPOINT_STALE');const stats=call(s,'statistics');if(stats.undoCount!==s.cursor||stats.redoCount!==s.ids.length-s.cursor-1)refuse('Dense checkpoint history lost its coordinator alignment.','PDF_DENSE_CHECKPOINT_STALE');return s;}
function expected(s,value){if(value!==s.revision)refuse('Dense checkpoint document revision changed.','PDF_DENSE_CHECKPOINT_STALE');}
function checkpoint(s){const stats=call(s,'statistics');return {schema:'figureStudio.pdfDenseCheckpoint.v1',stateId:s.ids[s.cursor],source:{...s.source},documentRevision:s.revision,leafRevision:stats.leafRevision,undoCount:s.cursor,redoCount:s.ids.length-s.cursor-1,retainedStates:s.ids.length};}
function sync(s){s.revision=Reflect.apply(revisionOf,s.document,[]);}
class DenseDocumentCheckpoints{
 checkpoint(){return checkpoint(state(this));}
 execute({expectedRevision,command,signal}={}){abort(signal);const s=state(this);expected(s,expectedRevision);if(!Number.isSafeInteger(s.next)||s.next>=Number.MAX_SAFE_INTEGER)refuse('Dense checkpoint state envelope exhausted.');const id=s.nonce+':'+s.next,after=s.ids.slice(0,s.cursor+1);after.push(id);if(after.length>MAX_ACTIONS+1)after.shift();const plan=call(s,'prepare',{expectedRevision,command});abort(signal);const changed=call(s,'commit',plan,{signal});s.ids=after;s.cursor=after.length-1;s.next++;sync(s);state(this);return {changed,checkpoint:checkpoint(s)};}
 undo({expectedRevision,signal}={}){return this._step(false,expectedRevision,signal);}
 redo({expectedRevision,signal}={}){return this._step(true,expectedRevision,signal);}
 _step(redo,expectedRevision,signal){abort(signal);const s=state(this);expected(s,expectedRevision);const changed=call(s,'_history',redo,expectedRevision,undefined);if(changed){s.cursor+=redo?1:-1;sync(s);}state(this);return {changed,checkpoint:checkpoint(s)};}
 goToState({stateId,expectedRevision,signal}={}){abort(signal);const s=state(this);expected(s,expectedRevision);if(typeof stateId!=='string')refuse('A retained issued checkpoint is required.');const target=s.ids.indexOf(stateId);if(target<0)refuse('Dense checkpoint is foreign, branched away, or pruned.');const distance=target-s.cursor,actions=Math.abs(distance),stats=call(s,'statistics');if(actions>MAX_ACTIONS||(distance<0?stats.undoCount:stats.redoCount)<actions)refuse('Dense checkpoint target is outside retained coordinator history.');
  call(s,'preflightHistory',{expectedRevision:s.revision,redo:distance>0,steps:actions});
  // Admission is complete. The bounded private history walk has no await or
  // cancellation point, so the host receives one completed document revision.
  for(let i=0;i<actions;i++){if(!call(s,'_history',distance>0,s.revision,undefined))refuse('Dense checkpoint coordinator history is incomplete.');s.cursor+=distance>0?1:-1;sync(s);}state(this);return {changed:actions>0,actions,checkpoint:checkpoint(s)};
 }
 close(){issued.delete(this);}
}
function create({document,store}={}){if(!groups.isDocumentFor(document,store))refuse('Dense checkpoints require the exact private source coordinator.');const stats=Reflect.apply(methods.statistics,document,[]);if(stats.undoCount||stats.redoCount)refuse('Dense checkpoint ownership begins at a fresh coordinator baseline.');if(typeof crypto?.randomUUID!=='function')refuse('Dense checkpoint state issuance is unavailable.');const nonce=crypto.randomUUID(),owner=new DenseDocumentCheckpoints();issued.set(owner,{document,store,source:Reflect.apply(methods.source,document,[]),revision:Reflect.apply(revisionOf,document,[]),nonce,next:1,ids:[nonce+':0'],cursor:0});return owner;}
return Object.freeze({DenseDocumentCheckpoints,create,isJournal:value=>issued.has(value),MAX_ACTIONS});
});
