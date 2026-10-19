/* Complete, bounded raw-source binding for the direct device-color/path/text
 * profile. It never infers cells or substitutes a rendered geometry. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.FigureStudioPdfDenseSourceNumbers=api;})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA='figureStudio.pdfDenseSourceNumbers.v1',MAX_CONTENT=33554432,MAX_DEPTH=48,issued=new WeakMap();
function refuse(message){const e=new Error(message);e.code='PDF_DENSE_SOURCE_UNSUPPORTED';throw e;}
function abort(signal){if(signal?.aborted){const e=new Error('Complete original PDF numeric binding was cancelled.');e.name='AbortError';throw e;}}
const equal=(a,b)=>a.length===b.length&&Array.from(a).every((v,i)=>Object.is(v,b[i]));
const clock=()=>performance.now();
const defaultYield=()=>new Promise(resolve=>setTimeout(resolve,0));
class Pool{constructor(Type){this.Type=Type;this.length=0;this.chunks=[];}add(v){const i=this.length++,c=i>>>12;if(!this.chunks[c])this.chunks[c]=new this.Type(4096);this.chunks[c][i&4095]=v;return i;}append(values){const start=this.length;for(const v of values)this.add(v);return start;}finish(){const result=new this.Type(this.length);for(let i=0;i<this.chunks.length;i++)result.set(this.chunks[i].subarray(0,Math.min(4096,this.length-i*4096)),i*4096);this.chunks=[];return result;}}
const table=fields=>Object.fromEntries(Object.entries(fields).map(([k,T])=>[k,new Pool(T)]));
const addRow=(t,r)=>{const i=Object.values(t)[0].length;for(const k of Object.keys(t))t[k].add(r[k]);return i;};
const finish=t=>Object.fromEntries(Object.entries(t).map(([k,p])=>[k,p.finish()]));
async function digest(bytes){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');}
function ws(c){return c===0||c===9||c===10||c===12||c===13||c===32;}
function delimiter(c){return c===undefined||ws(c)||[40,41,60,62,91,93,123,125,47,37].includes(c);}
class Lexer{
 constructor(bytes){this.bytes=bytes;this.offset=0;this.tokens=0;}
 next(depth=0){
  if(depth>MAX_DEPTH)refuse('Raw PDF operand depth exceeded.');const b=this.bytes;
  while(this.offset<b.length){const c=b[this.offset];if(ws(c)){this.offset++;continue;}if(c===37){while(this.offset<b.length&&![10,13].includes(b[this.offset]))this.offset++;continue;}break;}
  if(this.offset===b.length)return null;
  const start=this.offset,c=b[this.offset++];if(++this.tokens>10000000)refuse('Raw PDF token count exceeded.');
  if(c===91){const values=[];for(;;){const value=this.next(depth+1);if(!value)refuse('Unterminated raw PDF array.');if(value.kind==='endArray')break;if(!['number','bytes'].includes(value.kind)||values.length>65536)refuse('Unsupported raw text-array operand.');values.push(value);}return {kind:'array',value:values,start,end:this.offset};}
  if(c===93)return {kind:'endArray',start,end:this.offset};
  if(c===40){const values=[];let nested=1;while(this.offset<b.length){let v=b[this.offset++];if(v===92){if(this.offset===b.length)refuse('Truncated PDF string escape.');v=b[this.offset++];if(v===13||v===10){if(v===13&&b[this.offset]===10)this.offset++;continue;}const escaped={110:10,114:13,116:9,98:8,102:12};if(Object.hasOwn(escaped,v))v=escaped[v];else if(v>=48&&v<=55){let octal=v-48;for(let j=0;j<2&&b[this.offset]>=48&&b[this.offset]<=55;j++)octal=octal*8+b[this.offset++]-48;v=octal&255;}}else if(v===40){if(++nested>MAX_DEPTH)refuse('Raw string nesting exceeded.');}else if(v===41){if(--nested===0)return {kind:'bytes',value:new Uint8Array(values),start,end:this.offset};}else if(v===13){if(b[this.offset]===10)this.offset++;v=10;}values.push(v);if(values.length>1048576)refuse('Raw source text string exceeds its envelope.');}refuse('Unterminated original PDF string.');}
  if(c===47){let value='';while(this.offset<b.length&&!delimiter(b[this.offset])){let v=b[this.offset++];if(v===35){const hex=String.fromCharCode(b[this.offset++]||0,b[this.offset++]||0);if(!/^[a-fA-F0-9]{2}$/.test(hex))refuse('Malformed raw PDF name escape.');v=parseInt(hex,16);}value+=String.fromCharCode(v);if(value.length>256)refuse('Raw resource name exceeds its envelope.');}return {kind:'name',value,start,end:this.offset};}
  if(c===60){const values=[];let hex='';while(this.offset<b.length&&b[this.offset]!==62){const v=b[this.offset++];if(ws(v))continue;const ch=String.fromCharCode(v);if(!/[a-fA-F0-9]/.test(ch))refuse('Unsupported raw hex string.');hex+=ch;if(hex.length===2){values.push(parseInt(hex,16));hex='';}}if(b[this.offset++]!==62)refuse('Unterminated raw hex string.');if(hex)values.push(parseInt(hex+'0',16));return {kind:'bytes',value:new Uint8Array(values),start,end:this.offset};}
  let token=String.fromCharCode(c);while(this.offset<b.length&&!delimiter(b[this.offset])){token+=String.fromCharCode(b[this.offset++]);if(token.length>64)refuse('Raw PDF scalar/operator token exceeds its envelope.');}
  if(/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(token)){const value=Number(token);if(!Number.isFinite(value))refuse('Non-finite original source number.');return {kind:'number',value,token,start,end:this.offset};}
  if(!/^[A-Za-z][A-Za-z0-9*]*$/.test(token))refuse('Unsupported raw PDF lexical operand.');return {kind:'operator',value:token,start,end:this.offset};
 }
}
async function decodedContent(bytes,pdfLib,pageNumber,signal){
 if(!pdfLib?.PDFDocument||!(bytes instanceof Uint8Array)||!bytes.length||bytes.length>33554432)refuse('Original numeric binding requires bounded original PDF bytes and the bundled parser.');
 const document=await pdfLib.PDFDocument.load(bytes),page=document.getPages()[pageNumber-1];if(!page)refuse('Original source page is missing.');
 const name=pdfLib.PDFName.of,lookup=value=>document.context.lookup(value),raw=lookup(page.node.get(name('Contents')));
 if(!(raw instanceof pdfLib.PDFRawStream)||raw.dict.get(name('Filter'))?.asString?.()!=='/FlateDecode'||raw.dict.get(name('DecodeParms'))!==undefined)refuse('Dense source numbers require one direct Flate stream without decode parameters.');
 const resources=page.node.Resources();if(!(resources instanceof pdfLib.PDFDict)||resources.keys().some(k=>k.asString()!=='/Font'))refuse('Dense source resource/default color-space envelope is unsupported.');
 const fontDict=lookup(resources.get(name('Font'))),fonts={};if(!(fontDict instanceof pdfLib.PDFDict))refuse('Original native font resources are missing.');
 for(const[key,ref]of fontDict.entries()){const font=lookup(ref),subtype=font.get(name('Subtype'))?.asString?.(),encoding=font.get(name('Encoding'))?.asString?.();if(!['/TrueType','/Type1'].includes(subtype)||encoding!=='/WinAnsiEncoding'||font.get(name('ToUnicode'))!==undefined)refuse('Dense raw text requires the complete single-byte native font profile.');fonts[key.decodeText()]={resourceName:key.decodeText(),baseFont:font.get(name('BaseFont'))?.decodeText?.(),subtype,encoding};}
 const media=page.getMediaBox(),crop=page.getCropBox(),rotation=page.getRotation().angle,unit=lookup(page.node.get(name('UserUnit')))?.asNumber?.()??1;
 if(!equal([media.x,media.y,media.width,media.height],[crop.x,crop.y,crop.width,crop.height])||media.x!==0||media.y!==0||rotation!==0||unit!==1)refuse('Dense original numeric page frame is outside the direct point profile.');
 if(typeof DecompressionStream!=='function')refuse('Bounded native Flate decompression is unavailable.');
 const reader=new Blob([raw.getContents()]).stream().pipeThrough(new DecompressionStream('deflate')).getReader(),chunks=[];let length=0;
 try{for(;;){abort(signal);const result=await reader.read();if(result.done)break;length+=result.value.length;if(length>MAX_CONTENT)refuse('Decoded original source exceeds32MiB.');chunks.push(result.value);}}catch(error){await reader.cancel().catch(()=>{});throw error;}finally{reader.releaseLock();}
 const content=new Uint8Array(length);let offset=0;for(const chunk of chunks){content.set(chunk,offset);offset+=chunk.length;}
 return {content,fonts,frame:{width:media.width,height:media.height,transform:[1,0,0,-1,0,media.height]}};
}
function projectionMatches(raw,native){if(raw.length!==native.length)return false;const f32=native instanceof Float32Array;for(let i=0;i<raw.length;i++)if(!Object.is(f32?Math.fround(raw[i]):raw[i],native[i]))return false;return true;}
function colorProjection(values){if(values.some(v=>!Number.isFinite(v)||v<0||v>1))refuse('Original device color components are outside their exact envelope.');return Array.from(new Uint8ClampedArray((values.length===1?[values[0],values[0],values[0]]:values).map(v=>v*255)));}
function flattenedText(array){const result=[];for(const token of array){if(token.kind==='number')result.push(token.value);else if(token.kind==='bytes')for(const value of token.value)result.push({code:value});else refuse('Unsupported original text-array value.');}return result;}
function textMatches(raw,native){if(raw.length!==native.length)return false;for(let i=0;i<raw.length;i++){if(typeof raw[i]==='number'){if(!Object.is(raw[i],native[i]))return false;}else if(!native[i]||native[i].originalCharCode!==raw[i].code||typeof native[i].unicode!=='string'||typeof native[i].fontChar!=='string')return false;}return true;}
async function bind({bytes,pdfLib,pageNumber=1,native,owner,viewport,fonts,signal,onProgress,yieldControl=defaultYield}={}){
 if(!owner||typeof owner!=='object'||!native?.OPS||!Number.isInteger(native.count)||native.count>2000000||typeof native.operation!=='function'||typeof yieldControl!=='function')refuse('Complete native producer ownership is required.');
 const started=clock(),sourceSha256=await digest(bytes),loaded=await decodedContent(bytes,pdfLib,pageNumber,signal),content=loaded.content;
 if(!equal(loaded.frame.transform,viewport.transform)||loaded.frame.width!==viewport.width||loaded.frame.height!==viewport.height)refuse('Original source frame differs from the native page frame.');
 const lexer=new Lexer(content),values=new Pool(Float64Array),colorValues=new Pool(Float64Array),paths=table({nativeOperatorIndex:Uint32Array,numberStart:Uint32Array,numberCount:Uint32Array,byteStart:Uint32Array,byteEnd:Uint32Array,sourceInstructionStart:Uint32Array,sourceInstructionEnd:Uint32Array}),colors=table({nativeOperatorIndex:Uint32Array,operator:Uint8Array,numberStart:Uint32Array,numberCount:Uint8Array,byteStart:Uint32Array,byteEnd:Uint32Array}),paints=table({nativeOperatorIndex:Uint32Array,fillColor:Uint32Array,strokeColor:Uint32Array});
 const nativeFonts=new Map(fonts.map(f=>[f.id,f])),fontBindings=new Map(),textShows=[],operands=[],scope=[];let state={fill:0,stroke:0,font:null,sourceFont:null},nativeIndex=0,instructions=0,pathOps=[],pathNumbers=[],pathStart=0,pathEnd=0,pathInstructionStart=0,pathInstructionEnd=0,projectedDifferences=0,geometryOperands=0,yields=0,maxSliceMs=0,slice=clock(),clipCount=0,dependencyCount=0;
 addRow(colors,{nativeOperatorIndex:0xffffffff,operator:0,numberStart:colorValues.append([0]),numberCount:1,byteStart:0,byteEnd:0});
 const current=()=>native.operation(nativeIndex);
 function next(name){const row=current();if(row.name!==name)refuse(`Original/native operation differs at raw${instructions}/native${nativeIndex}: ${name} vs ${row.name}.`);nativeIndex++;return row;}
 function flushPath(){if(!pathOps.length)return;const row=next('constructPath');if(!equal(pathOps,row.args[0])||!projectionMatches(pathNumbers,row.args[1]))refuse('Original path commands/numbers differ from the exact native projection.');for(let i=0;i<pathNumbers.length;i++)if(!Object.is(pathNumbers[i],row.args[1][i]))projectedDifferences++;geometryOperands+=pathNumbers.length;addRow(paths,{nativeOperatorIndex:nativeIndex-1,numberStart:values.append(pathNumbers),numberCount:pathNumbers.length,byteStart:pathStart,byteEnd:pathEnd,sourceInstructionStart:pathInstructionStart,sourceInstructionEnd:pathInstructionEnd});pathOps=[];pathNumbers=[];}
 const numbers=(args,n)=>{if(args.length!==n||args.some(t=>t.kind!=='number'))refuse('Original numeric operation arity differs.');return args.map(t=>t.value);};
 const simple={q:['save',0],Q:['restore',0],W:['clip',0],'W*':['eoClip',0],n:['endPath',0],'f*':['eoFill',0],f:['fill',0],S:['stroke',0],s:['closeStroke',0],BT:['beginText',0],ET:['endText',0],Tr:['setTextRenderingMode',1],Tm:['setTextMatrix',6],w:['setLineWidth',1],M:['setMiterLimit',1]};
 for(;;){
  const token=lexer.next();if(!token)break;if(token.kind!=='operator'){operands.push(token);if(operands.length>65536)refuse('Original operand stack exceeds its envelope.');continue;}
  const args=operands.splice(0),op=token.value,start=args[0]?.start??token.start;instructions++;
  if(instructions%2048===0){abort(signal);maxSliceMs=Math.max(maxSliceMs,clock()-slice);onProgress?.({stage:'bind-original-numeric-stream',sourceBytes:lexer.offset,totalSourceBytes:content.length,sourceInstructions:instructions,nativeOperators:nativeIndex});await yieldControl();yields++;slice=clock();}
  if(op==='m'||op==='l'||op==='re'){
   const data=numbers(args,op==='re'?4:2);if(!pathOps.length){pathStart=start;pathInstructionStart=instructions-1;}pathOps.push(native.OPS[op==='m'?'moveTo':op==='l'?'lineTo':'rectangle']);pathNumbers.push(...data);pathEnd=token.end;pathInstructionEnd=instructions;continue;
  }
  flushPath();
  if(Object.hasOwn(simple,op)){
   const[name,n]=simple[op],data=numbers(args,n),row=next(name);if(!equal(data,row.args||[]))refuse('Original scalar/text-state operands differ from native values.');
   if(op==='q'){if(scope.length>=MAX_DEPTH)refuse('Original graphics nesting exceeds48.');scope.push({...state});}else if(op==='Q'){if(!scope.length)refuse('Original graphics scopes are unbalanced.');state=scope.pop();}
   if(op==='W'||op==='W*')clipCount++;
   if(['f*','f','S','s'].includes(op))addRow(paints,{nativeOperatorIndex:nativeIndex-1,fillColor:state.fill,strokeColor:state.stroke});
   continue;
  }
  if(['g','rg','G','RG'].includes(op)){
   const data=numbers(args,op==='g'||op==='G'?1:3),fill=op===op.toLowerCase(),row=next(fill?'setFillRGBColor':'setStrokeRGBColor');if(!equal(colorProjection(data),row.args))refuse('Original device color differs from native projected color.');
   const index=addRow(colors,{nativeOperatorIndex:nativeIndex-1,operator:{g:0,rg:1,G:2,RG:3}[op],numberStart:colorValues.append(data),numberCount:data.length,byteStart:start,byteEnd:token.end});state[fill?'fill':'stroke']=index;continue;
  }
  if(op==='Tf'){
   if(args.length!==2||args[0].kind!=='name'||args[1].kind!=='number')refuse('Original font operation is malformed.');
   const dependencies=[];while(nativeIndex<native.count&&current().name==='dependency'){const row=current();if(!Array.isArray(row.args)||row.args.some(id=>typeof id!=='string'))refuse('Unqualified native dependency.');dependencies.push(...row.args);nativeIndex++;dependencyCount++;}
   const row=next('setFont'),sourceFont=loaded.fonts[args[0].value],font=nativeFonts.get(row.args[0]);if(!sourceFont||!font||font.name!==sourceFont.baseFont||!Object.is(row.args[1],args[1].value)||dependencies.some(id=>id!==font.id)||fontBindings.has(args[0].value)&&fontBindings.get(args[0].value)!==font.id)refuse('Original/native source font identity or size differs.');fontBindings.set(args[0].value,font.id);state.font=font.id;state.sourceFont=args[0].value;continue;
  }
  if(op==='TJ'){
   if(args.length!==1||args[0].kind!=='array'||!state.font)refuse('Original text show has no qualified current font.');const raw=flattenedText(args[0].value),row=current();if(!['showText','showSpacedText'].includes(row.name)||!textMatches(raw,row.args?.[0]||[]))refuse('Original text bytes/adjustments differ from actual native glyph shows.');nativeIndex++;textShows.push({nativeOperatorIndex:nativeIndex-1,fontId:state.font,sourceFontName:state.sourceFont,byteStart:start,byteEnd:token.end,sourceInstruction:instructions-1,encoded:Array.from(raw,v=>typeof v==='number'?{adjustment:v}:{charCode:v.code})});addRow(paints,{nativeOperatorIndex:nativeIndex-1,fillColor:state.fill,strokeColor:state.stroke});continue;
  }
  refuse('Original source has unqualified operation '+op+'.');
 }
 flushPath();abort(signal);if(operands.length||scope.length||nativeIndex!==native.count)refuse('Original/native complete streams did not end together.');
 maxSliceMs=Math.max(maxSliceMs,clock()-slice);
 const originalNumbers=values.finish(),originalColorNumbers=colorValues.finish();
 const littleEndianBytes=numbers=>{if(new Uint8Array(new Uint16Array([1]).buffer)[0]===1)return new Uint8Array(numbers.buffer,numbers.byteOffset,numbers.byteLength);const bytes=new Uint8Array(numbers.length*8),view=new DataView(bytes.buffer);for(let i=0;i<numbers.length;i++)view.setFloat64(i*8,numbers[i],true);return bytes;};
 const data={schema:SCHEMA,sourceSha256,contentSha256:await digest(content),decodedByteLength:content.length,pageNumber,frame:loaded.frame,sourceFonts:loaded.fonts,fontBindings:Array.from(fontBindings),textShows,tables:{paths:finish(paths),colors:finish(colors),paints:finish(paints),numbers:originalNumbers,colorNumbers:originalColorNumbers},stats:{sourceInstructions:instructions,nativeOperators:nativeIndex,pathChunks:paths.nativeOperatorIndex.length,pathGeometryOperands:geometryOperands,geometryNumbersSha256:await digest(littleEndianBytes(originalNumbers)),colorNumbersSha256:await digest(littleEndianBytes(originalColorNumbers)),numericDigestEncoding:'IEEE754-Float64-little-endian; original instruction order; initial default Gray0 included in colors',clips:clipCount,paintCount:paints.nativeOperatorIndex.length,textShows:textShows.length,rawDeviceColorOperations:colors.nativeOperatorIndex.length-1,nativeDependencyOperations:dependencyCount,nativeProjectedCoordinateDifferences:projectedDifferences,originalCoordinateCoverage:'All original path and clip numeric operands; all native operation order, device colors, scalar/text states and source encoded text shows bound',complete:true,elapsedMs:clock()-started,maxSliceMs,uiYields:yields}};
 const token=Object.freeze({schema:SCHEMA,stats:Object.freeze({...data.stats})});issued.set(token,{owner,data});return token;
}
function take(token,owner){const proof=issued.get(token);if(!proof||proof.owner!==owner)refuse('Original numeric binding lacks its exact native producer owner.');issued.delete(token);return proof.data;}
return Object.freeze({SCHEMA,bind,take,projectionMatches});
});
