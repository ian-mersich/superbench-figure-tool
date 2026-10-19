/* Complete-only exact native-operator snapshots. Legacy whole-graph proofs
 * remain unchanged; this compositional route retains the original per-batch
 * graph/string/depth budgets and the importer operator/resource envelopes. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.FigureStudioPdfCurrentNativeOperatorSnapshots=api;})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const issued=new WeakMap(),limits=Object.freeze({batchNodes:200000,batchStringBytes:8000000,depth:48,operators:250000,retainedBytes:32*1024*1024});
function refuse(reason){const error=new Error(reason);error.code='PDF_LOGICAL_TEXT_UNSUPPORTED';throw error;}
const type=value=>Array.isArray(value)?'Array':ArrayBuffer.isView(value)&&!(value instanceof DataView)?value.constructor.name:null;
const clock=()=>typeof performance==='object'?performance.now():Date.now();
function defaultYield(){
 if(typeof MessageChannel==='function')return new Promise(resolve=>{const channel=new MessageChannel();channel.port1.onmessage=()=>{channel.port1.close();channel.port2.close();resolve();};channel.port2.postMessage(null);});
 if(typeof globalThis.scheduler?.yield==='function')return globalThis.scheduler.yield();
 return new Promise(resolve=>setTimeout(resolve,0));
}
function cancel(signal){if(signal?.aborted){const error=new Error('Current native operator proof was cancelled.');error.name='AbortError';throw error;}}
function arrays(operators){if(!operators||!type(operators.fnArray)||!Array.isArray(operators.argsArray)||operators.fnArray.length!==operators.argsArray.length||operators.fnArray.length>limits.operators)refuse('Current native operator arrays exceed their original operator envelope.');return {fn:operators.fnArray,args:operators.argsArray,length:operators.fnArray.length};}
async function run(steps,{yieldControl=defaultYield,signal}={}){if(typeof yieldControl!=='function')refuse('Current native proof requires a yield callback.');let count=0;cancel(signal);while(true){const step=steps.next();if(step.done){cancel(signal);return step.value;}if(++count%2048===0){cancel(signal);await yieldControl();cancel(signal);}}}
function* copyValue(value,depth,state,row){
 if(depth>limits.depth||++row.nodes>limits.batchNodes)refuse('Current native operator batch exceeds its original graph/depth budget.');
 state.nodes++;state.retainedBytes+=8;if(state.retainedBytes>limits.retainedBytes)refuse('Current native retained operator snapshot exceeds its resource envelope.');yield;
 if(typeof value==='string'){row.stringBytes+=value.length;if(row.stringBytes>limits.batchStringBytes)refuse('Current native operator batch exceeds its original string budget.');if(!state.strings.has(value)){state.retainedBytes+=value.length*2;if(state.retainedBytes>limits.retainedBytes)refuse('Current native retained operator snapshot exceeds its resource envelope.');state.strings.set(value,value);}return state.strings.get(value);}
 if(value===null||typeof value!=='object')return value;
 if(state.active.has(value))refuse('Cyclic current native operator arguments are unsupported.');
 if(state.copies.has(value))return state.copies.get(value);
 const kind=type(value);if(value instanceof DataView)refuse('Unsupported current native operator byte view.');
 const keys=kind?null:Object.keys(value),length=kind?value.length:keys.length;
 state.retainedBytes+=32+length*8+(keys?keys.reduce((sum,key)=>sum+key.length*2,0):0);
 if(state.retainedBytes>limits.retainedBytes)refuse('Current native retained operator snapshot exceeds its resource envelope.');
 const result={kind:kind||'Object',values:new Array(length),...(keys?{keys}:{} )};state.active.add(value);state.copies.set(value,result);
 if(kind){for(let index=0;index<length;index++)if(kind!=='Array'||Object.hasOwn(value,index))result.values[index]=yield* copyValue(value[index],depth+1,state,row);}
 else for(let index=0;index<length;index++)result.values[index]=yield* copyValue(value[keys[index]],depth+1,state,row);
 state.active.delete(value);if(keys)Object.freeze(keys);Object.freeze(result.values);return Object.freeze(result);
}
function* compareValue(actual,snapshot,depth,state){
 if(depth>limits.depth||++state.nodes>limits.retainedBytes/8)return false;yield;
 if(snapshot===null||typeof snapshot!=='object')return Object.is(actual,snapshot);
 if(actual===null||typeof actual!=='object')return false;
 let partners=state.seen.get(actual);if(partners?.has(snapshot))return true;if(!partners){partners=new Set();state.seen.set(actual,partners);}partners.add(snapshot);
 const kind=type(actual);if((kind||'Object')!==snapshot.kind||actual instanceof DataView)return false;
 if(kind){if(actual.length!==snapshot.values.length)return false;for(let index=0;index<actual.length;index++){if(kind==='Array'&&Object.hasOwn(actual,index)!==Object.hasOwn(snapshot.values,index))return false;if(Object.hasOwn(snapshot.values,index)&&!(yield* compareValue(actual[index],snapshot.values[index],depth+1,state)))return false;}}
 else {const keys=Object.keys(actual);if(keys.length!==snapshot.keys.length||keys.some((key,index)=>key!==snapshot.keys[index]))return false;for(let index=0;index<keys.length;index++)if(!(yield* compareValue(actual[keys[index]],snapshot.values[index],depth+1,state)))return false;}
 return true;
}
function* comparison(operators,record){
 const actual=arrays(operators);if(type(actual.fn)!==record.fnKind||actual.args.length!==record.rows.length)return false;
 const state={nodes:0,seen:new WeakMap()};
 for(let index=0;index<record.rows.length;index++){const row=record.rows[index];if(!(yield* compareValue(actual.fn[index],row.fn,2,state))||!(yield* compareValue(actual.args[index],row.args,2,state)))return false;}
 return true;
}
function compareValueNow(actual,snapshot,depth,state){
 if(depth>limits.depth||++state.nodes>limits.retainedBytes/8)return false;
 if(snapshot===null||typeof snapshot!=='object')return Object.is(actual,snapshot);
 if(actual===null||typeof actual!=='object')return false;
 let partners=state.seen.get(actual);if(partners?.has(snapshot))return true;if(!partners){partners=new Set();state.seen.set(actual,partners);}partners.add(snapshot);
 const kind=type(actual);if((kind||'Object')!==snapshot.kind||actual instanceof DataView)return false;
 if(kind){if(actual.length!==snapshot.values.length)return false;for(let index=0;index<actual.length;index++){if(kind==='Array'&&Object.hasOwn(actual,index)!==Object.hasOwn(snapshot.values,index))return false;if(Object.hasOwn(snapshot.values,index)&&!compareValueNow(actual[index],snapshot.values[index],depth+1,state))return false;}}
 else {const keys=Object.keys(actual);if(keys.length!==snapshot.keys.length)return false;for(let index=0;index<keys.length;index++)if(keys[index]!==snapshot.keys[index]||!compareValueNow(actual[keys[index]],snapshot.values[index],depth+1,state))return false;}
 return true;
}
function coherent(operators,record){
 const start=clock(),actual=arrays(operators),state={nodes:0,seen:new WeakMap()};let same=type(actual.fn)===record.fnKind&&actual.args.length===record.rows.length;
 for(let index=0;same&&index<record.rows.length;index++){const row=record.rows[index];same=compareValueNow(actual.fn[index],row.fn,2,state)&&compareValueNow(actual.args[index],row.args,2,state);}
 return {same,finalVerificationMs:clock()-start};
}
async function capture(operators,options={}){
 const actual=arrays(operators),state={copies:new WeakMap(),active:new WeakSet(),strings:new Map(),nodes:0,retainedBytes:0},rows=[],batches=[];
 let first=0,batchNodes=0,batchStringBytes=0;
 const flush=()=>{if(first<rows.length){batches.push(Object.freeze({first,last:rows.length,nodes:batchNodes,stringBytes:batchStringBytes}));first=rows.length;batchNodes=0;batchStringBytes=0;}};
 function* steps(){for(let index=0;index<actual.length;index++){
  if(actual.fn!==operators.fnArray||actual.args!==operators.argsArray||actual.args.length!==actual.length||actual.fn.length!==actual.length)refuse('Current native operator containers changed during snapshot construction.');
  const row={nodes:0,stringBytes:0},fn=yield* copyValue(actual.fn[index],2,state,row),args=yield* copyValue(actual.args[index],2,state,row);
  if(batchNodes+row.nodes>limits.batchNodes||batchStringBytes+row.stringBytes>limits.batchStringBytes||rows.length-first>=512)flush();
  rows.push(Object.freeze({fn,args}));batchNodes+=row.nodes;batchStringBytes+=row.stringBytes;yield;
 }flush();}
 await run(steps(),options);cancel(options.signal);Object.freeze(rows);Object.freeze(batches);
 const record={rows,batches,fnKind:type(actual.fn)},proof=coherent(operators,record);if(!proof.same)refuse('Current native operands changed during snapshot construction.');
 cancel(options.signal);const stats=Object.freeze({operators:rows.length,nodes:state.nodes,retainedBytes:state.retainedBytes,batches:batches.length,maxBatchNodes:Math.max(0,...batches.map(batch=>batch.nodes)),maxBatchStringBytes:Math.max(0,...batches.map(batch=>batch.stringBytes)),finalVerificationMs:proof.finalVerificationMs});
 const token=Object.freeze({schema:'figureStudio.currentNativeOperatorSnapshotBatches.v1',stats});issued.set(token,record);return token;
}
async function same(operators,snapshot,options={}){
 const record=issued.get(snapshot);if(!record)return false;
 let result;try{result=await run(comparison(operators,record),options);}catch(error){if(error.name==='AbortError')throw error;return false;}
 if(!result)return false;cancel(options.signal);
 // A later yield can mutate an earlier operand. A fresh no-yield traversal
 // establishes coherent current values immediately before publication/use.
 const proof=coherent(operators,record);cancel(options.signal);record.lastProof=Object.freeze(proof);return proof.same;
}
function sameNow(operators,snapshot){const record=issued.get(snapshot);if(!record)return false;try{return coherent(operators,record).same;}catch(_){return false;}}
function isIssued(snapshot){return issued.has(snapshot);}
function statistics(snapshot){const record=issued.get(snapshot);return record?Object.freeze({...snapshot.stats,lastMatchFinalVerificationMs:record.lastProof?.finalVerificationMs??null}):null;}
return Object.freeze({capture,same,sameNow,isIssued,statistics,limits,yieldToUi:defaultYield});
});
