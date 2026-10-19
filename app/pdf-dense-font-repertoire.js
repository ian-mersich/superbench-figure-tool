/* Complete single-byte source-font mappings captured from the actual native decoder. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.FigureStudioPdfDenseFontRepertoire=api;})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA='figureStudio.pdfDenseFontRepertoire.v1',issued=new WeakMap(),completed=new WeakSet();
const LIMITS=Object.freeze({codes:256,tableEntries:8192,depth:8,fontBytes:33554432});
const FIELDS=['name','loadedName','type','subtype','composite','missingFile','vertical','isType3Font','fallbackName','bold','black','italic','fontMatrix','mimetype','toUnicode','toFontChar','widths','defaultWidth','defaultEncoding','differences','seacMap','cMap','data'];
function refuse(message,stale=false){const error=new Error(message);error.code=stale?'PDF_DENSE_FONT_REPERTOIRE_STALE':'PDF_DENSE_FONT_REPERTOIRE_UNSUPPORTED';throw error;}
function abort(signal){if(signal?.aborted){const error=new Error('Native font repertoire capture was cancelled.');error.name='AbortError';throw error;}}
function data(object,key){for(let current=object;current;current=Object.getPrototypeOf(current)){const descriptor=Object.getOwnPropertyDescriptor(current,key);if(descriptor){if(!Object.hasOwn(descriptor,'value'))refuse('Native font fields must remain data properties.');return descriptor.value;}}}
function copy(value,state={count:0,seen:new Set()},depth=0){
 if(depth>LIMITS.depth||++state.count>LIMITS.tableEntries)refuse('Native font tables exceed their bounded profile.');
 if(value===null||value===undefined||typeof value==='boolean')return value;
 if(typeof value==='number'){if(!Number.isFinite(value))refuse('Native font tables contain a nonfinite value.');return value;}
 if(typeof value==='string'){if(value.length>65536)refuse('Native font text exceeds its bounded profile.');return value;}
 if(typeof value!=='object'||state.seen.has(value))refuse('Native font tables must be acyclic plain data.');
 if(value instanceof Uint8Array){if(value.byteLength>LIMITS.fontBytes)refuse('Native font program exceeds its bounded profile.');return value.slice();}
 const array=Array.isArray(value),prototype=Object.getPrototypeOf(value);if(array?prototype!==Array.prototype:prototype!==Object.prototype&&prototype!==null)refuse('Native font table type is unqualified.');
 state.seen.add(value);const result=array?new Array(value.length):Object.create(prototype===null?null:Object.prototype);
 if(array&&value.length>65536)refuse('Native font table length exceeds its bounded profile.');
 for(const key of Reflect.ownKeys(value)){if(array&&key==='length')continue;if(typeof key!=='string')refuse('Native font tables have unsupported symbol fields.');const entry=Object.getOwnPropertyDescriptor(value,key);if(!Object.hasOwn(entry,'value'))refuse('Native font tables must not contain accessors.');Object.defineProperty(result,key,{value:copy(entry.value,state,depth+1),enumerable:entry.enumerable,writable:true,configurable:true});}
 state.seen.delete(value);return result;
}
function same(a,b){
 if(Object.is(a,b))return true;if(!a||!b||typeof a!=='object'||typeof b!=='object'||Object.getPrototypeOf(a)!==Object.getPrototypeOf(b))return false;
 if(a instanceof Uint8Array){if(!(b instanceof Uint8Array)||a.length!==b.length)return false;for(let i=0;i<a.length;i++)if(a[i]!==b[i])return false;return true;}
 const ak=Reflect.ownKeys(a),bk=Reflect.ownKeys(b);return ak.length===bk.length&&ak.every((key,index)=>key===bk[index]&&Object.getOwnPropertyDescriptor(a,key)?.enumerable===Object.getOwnPropertyDescriptor(b,key)?.enumerable&&same(Object.getOwnPropertyDescriptor(a,key)?.value,Object.getOwnPropertyDescriptor(b,key)?.value));
}
function snapshotFont(font){const result={};for(const key of FIELDS)Object.defineProperty(result,key,{value:copy(data(font,key)),enumerable:true});return result;}
function sourceOf(source){const sha256=data(source,'sha256'),byteLength=data(source,'byteLength'),pageNumber=data(source,'pageNumber');if(typeof sha256!=='string'||!/^[a-f0-9]{64}$/.test(sha256)||!Number.isSafeInteger(byteLength)||byteLength<1||byteLength>33554432||!Number.isSafeInteger(pageNumber)||pageNumber<1)refuse('A complete original byte source identity is required.');return {sha256,byteLength,pageNumber};}
function resourceOf(sourceFont){const result={};for(const key of ['resourceName','baseFont','subtype','encoding'])result[key]=data(sourceFont,key);if(typeof result.resourceName!=='string'||!/^[A-Za-z0-9_.+-]+$/.test(result.resourceName)||typeof result.baseFont!=='string'||!result.baseFont||!['/Type1','/TrueType'].includes(result.subtype)||result.encoding!=='/WinAnsiEncoding')refuse('The original font resource is outside the single-byte WinAnsi profile.');return result;}
function tableAt(table,index){if(table===undefined||table===null)return undefined;const own=Object.getOwnPropertyDescriptor(table,String(index));if(own){if(!Object.hasOwn(own,'value'))refuse('Native font encoding entries must be data properties.');return own.value;}for(let prototype=Object.getPrototypeOf(table);prototype;prototype=Object.getPrototypeOf(prototype))if(Object.getOwnPropertyDescriptor(prototype,String(index)))refuse('Inherited native font encoding entries are unsupported.');}
// Exact bundled PDF.js missing-font display substitutions; all native codes
// are checked against the actual decoder in the independent module controls.
const SPECIAL=new Map([[63721,169],[63193,169],[63720,174],[63194,174],[63722,8482],[63195,8482],[63729,9127],[63730,9128],[63731,9129],[63740,9131],[63741,9132],[63742,9133],[63726,9121],[63727,9122],[63728,9123],[63737,9124],[63738,9125],[63739,9126],[63723,9115],[63724,9116],[63725,9117],[63734,9118],[63735,9119],[63736,9120]]);
function missingFontChar(code){return code>=0xfff0&&code<=0xffff?0:code>=0xf600&&code<=0xf8ff?SPECIAL.get(code)||code:code===0xad?0x2d:code;}
function nativeGlyph(font,code){
 const mapping=font.toUnicode&&data(font.toUnicode,'_map');if(!mapping||!font.toFontChar||!font.widths||!Number.isFinite(font.defaultWidth))refuse('Complete native Unicode, display and width tables are required.');
 const value=tableAt(mapping,code);if(value!==undefined&&typeof value!=='string')refuse('The native Unicode table has an unsupported value.');
 const unicode=value||String.fromCharCode(code),mapped=tableAt(font.toFontChar,code),isInFont=mapped!==undefined;let fontCharCode=mapped||code;
 if(!Number.isSafeInteger(fontCharCode)||fontCharCode<0||fontCharCode>0x10ffff)refuse('The native display character is outside its scalar profile.');
 if(font.missingFile){const glyphName=tableAt(font.differences,code)||tableAt(font.defaultEncoding,code);if((glyphName==='.notdef'||glyphName==='')&&font.type==='Type1')fontCharCode=32;fontCharCode=missingFontChar(fontCharCode);}
 const width=tableAt(font.widths,code);return {originalCharCode:code,unicode,fontChar:String.fromCodePoint(fontCharCode),width:typeof width==='number'?width:font.defaultWidth,isSpace:code===32,isInFont};
}
function freeze(value){if(value&&typeof value==='object'&&!Object.isFrozen(value)){for(const key of Object.keys(value))freeze(value[key]);Object.freeze(value);}return value;}
async function capture({font,fontId,source,sourceFont,ownerKey,assertCurrentSource,signal,yieldControl=()=>new Promise(resolve=>setTimeout(resolve,0))}={}){
 abort(signal);if(!ownerKey||typeof ownerKey!=='object'||typeof assertCurrentSource!=='function'||typeof yieldControl!=='function')refuse('Native font capture requires its private source owner and bounded yield callback.');
 const sourceCopy=sourceOf(source),resource=resourceOf(sourceFont),original=snapshotFont(font);
 if(typeof fontId!=='string'||!fontId||original.name!==resource.baseFont||original.vertical||original.isType3Font||original.composite||original.cMap!=null||original.seacMap&&Object.keys(original.seacMap).length)refuse('The actual native font is outside the horizontal simple-font profile.');
 if(original.data!==undefined&&!(original.data instanceof Uint8Array)||!original.data?.length&&!original.missingFile)refuse('The actual native font program is unavailable.');
 const verify=()=>{abort(signal);try{if(assertCurrentSource()===false||!same(sourceCopy,sourceOf(source))||!same(resource,resourceOf(sourceFont))||!same(original,snapshotFont(font)))refuse('Native font or original source changed during repertoire capture.',true);}catch(error){if(error.code==='PDF_DENSE_FONT_REPERTOIRE_UNSUPPORTED')refuse('Native font or original source changed during repertoire capture.',true);throw error;}};
 verify();let programSha256=null;if(original.data?.length){programSha256=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',original.data)),value=>value.toString(16).padStart(2,'0')).join('');verify();}
 const nativeGlyphs=[];for(let code=0;code<LIMITS.codes;code++){nativeGlyphs.push(nativeGlyph(original,code));if((code+1)%64===0){await yieldControl();verify();}}
 const scalar=glyph=>glyph.isInFont&&glyph.unicode.length===1&&Array.from(glyph.fontChar).length===1&&!/[\x00-\x1f\x7f\ud800-\udfff]/.test(glyph.unicode)&&!/^[\x00-\x1f\x7f\ud800-\udfff]$/.test(glyph.fontChar)&&glyph.width>=0;
 const groups=new Map();for(const glyph of nativeGlyphs.filter(scalar)){if(!groups.has(glyph.unicode))groups.set(glyph.unicode,[]);groups.get(glyph.unicode).push(glyph);}
 const ambiguousUnicode=Array.from(groups,([unicode,entries])=>entries.length>1?unicode:null).filter(value=>value!==null),glyphs=nativeGlyphs.filter(glyph=>scalar(glyph)&&groups.get(glyph.unicode).length===1);
 verify();const payload=freeze({schema:SCHEMA,source:sourceCopy,fontId,sourceFontName:resource.resourceName,baseFont:resource.baseFont,subtype:resource.subtype,encoding:resource.encoding,programSha256,nativeGlyphs,glyphs,ambiguousUnicode});
 const token=Object.freeze({});issued.set(token,{ownerKey,verify,payload});return token;
}
function take(token,ownerKey){const record=issued.get(token);if(!record||record.ownerKey!==ownerKey)refuse('The native font repertoire receipt is foreign or already consumed.');record.verify();issued.delete(token);completed.add(record.payload);return record.payload;}
return Object.freeze({SCHEMA,LIMITS,capture,take,isRepertoire:value=>completed.has(value)});
});
