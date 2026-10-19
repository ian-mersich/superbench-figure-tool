/* Bounded records from the actual bundled SVG text writer. A record token is
 * execution evidence only: its hidden consumer must separately own and prove
 * the complete byte-bound source. No serialized record grants source authority. */
(function(root,factory){const node=typeof module==='object'&&module.exports;const api=factory(node?require('./pdf-editable-import.js'):root.FigureStudioPdfEditableImport,node?require('./pdf-decoded-svg-number-precision.js'):root.FigureStudioPdfSvgNumberPrecision);if(node)module.exports=api;else root.FigureStudioPdfNativeGlyphRecords=api;})(typeof globalThis==='object'?globalThis:this,function(importer,numbers){
'use strict';
const issued=new WeakMap(),LIMITS=Object.freeze({operators:2000000,shows:250000,depth:48,retainedBytes:33554432});
const TEXT=new Set(['beginText','endText','setLeading','setLeadingMoveText','setFont','showText','showSpacedText','moveText','setCharSpacing','setWordSpacing','setHScale','setTextMatrix','setTextRise','setTextRenderingMode','nextLine']);
const STATE=new Set(['transform','setLineWidth','setLineJoin','setLineCap','setMiterLimit','setFillRGBColor','setStrokeRGBColor','setDash','setRenderingIntent','setFlatness','setGState']);
const PATH_PAINTS=new Set(['fill','eoFill','stroke','fillStroke','eoFillStroke','closeStroke','closeFillStroke','closeEOFillStroke']);
const IMAGE_PAINTS=new Set(['paintImageXObject','paintInlineImageXObject']);
const SKIP=new Set(['dependency','constructPath','closePath','endPath','clip','eoClip','beginMarkedContent','beginMarkedContentProps','endMarkedContent','markPoint','markPointProps']);
const FONT_FIELDS=['name','loadedName','fallbackName','missingFile','vertical','isType3Font','bold','black','italic','fontMatrix','mimetype'];
function refuse(message){const e=new Error(message);e.code='PDF_NATIVE_GLYPH_UNSUPPORTED';throw e;}
function abort(signal){if(signal?.aborted){const e=new Error('Native glyph recording was cancelled.');e.name='AbortError';throw e;}}
function yieldUi(){if(typeof MessageChannel==='function')return new Promise(resolve=>{const c=new MessageChannel();c.port1.onmessage=()=>{c.port1.close();c.port2.close();resolve();};c.port2.postMessage(null);});return new Promise(resolve=>setTimeout(resolve,0));}
function same(a,b,seen=new WeakMap(),depth=0){if(Object.is(a,b))return true;if(depth>LIMITS.depth||a===null||b===null||typeof a!=='object'||typeof b!=='object')return false;if(Array.isArray(a)!==Array.isArray(b)||ArrayBuffer.isView(a)!==ArrayBuffer.isView(b)||ArrayBuffer.isView(a)&&a.constructor!==b.constructor||(Array.isArray(a)||ArrayBuffer.isView(a))&&a.length!==b.length)return false;let pair=seen.get(a);if(pair?.has(b))return true;if(!pair){pair=new WeakSet();seen.set(a,pair);}pair.add(b);const ak=Object.keys(a),bk=Object.keys(b);return ak.length===bk.length&&ak.every((k,i)=>k===bk[i]&&same(a[k],b[k],seen,depth+1));}
function clone(value,state,depth=0){if(depth>LIMITS.depth)refuse('Native glyph record exceeds its depth envelope.');state.bytes+=8;if(state.bytes>LIMITS.retainedBytes)refuse('Native glyph records exceed their retained envelope.');if(value===null||typeof value==='undefined'||typeof value==='boolean')return value;if(typeof value==='number'){if(!Number.isFinite(value))refuse('Non-finite native glyph record.');return value;}if(typeof value==='string'){state.bytes+=value.length*2;if(state.bytes>LIMITS.retainedBytes)refuse('Native glyph records exceed their retained envelope.');return value;}if(Array.isArray(value))return Object.freeze(value.map(v=>clone(v,state,depth+1)));if(!value||typeof value!=='object'||Object.getPrototypeOf(value)!==Object.prototype)refuse('Unsupported native glyph record value.');const out={};for(const key of Object.keys(value))Object.defineProperty(out,key,{value:clone(value[key],state,depth+1),enumerable:true});return Object.freeze(out);}
class RecordNode{
 constructor(name){this.nodeName=name;this.localName=name.split(':').at(-1);this.namespaceURI='http://www.w3.org/2000/svg';this.nodeType=1;this.attrs=new Map();this.children=[];this.parentElement=null;this._text='';}
 get attributes(){return Array.from(this.attrs,([name,value])=>({name,value,namespaceURI:null}));}
 get parentNode(){return this.parentElement;}get childNodes(){return this.children;}get firstChild(){return this.children[0]||null;}get lastElementChild(){return this.children.at(-1)||null;}
 get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}set textContent(value){this._text=String(value);for(const c of this.children)c.parentElement=null;this.children=[];}
 setAttribute(name,value){this.attrs.set(name,String(value));}setAttributeNS(_ns,name,value){this.setAttribute(name,value);}getAttribute(name){return this.attrs.get(name)??null;}getAttributeNS(_ns,name){return this.getAttribute(name);}hasAttribute(name){return this.attrs.has(name);}removeAttribute(name){this.attrs.delete(name);}
 appendChild(child){child.remove();child.parentElement=this;this.children.push(child);return child;}append(...children){for(const child of children){if(typeof child==='string')this._text+=child;else this.appendChild(child);}}
 remove(){if(this.parentElement){const siblings=this.parentElement.children;siblings.splice(siblings.indexOf(this),1);this.parentElement=null;}}
 hasChildNodes(){return Boolean(this.children.length||this._text);}cloneNode(deep=false){const n=new RecordNode(this.nodeName);n.attrs=new Map(this.attrs);n._text=this._text;if(deep)for(const c of this.children)n.append(c.cloneNode(true));return n;}
}
const attrs=node=>Array.from(node.attributes,a=>[a.name,a.value]);
async function capture(options){
 const {handle,page,operators,pdfjs,viewport,source,ownerKey,assertCurrentSource,canonicalOperation,assertNativeFont,contextFor,logicalTextSource,signal,yieldControl=yieldUi,batchSize=2048}=options||{};
 if(pdfjs?.version!=='3.11.174'||typeof pdfjs.SVGGraphics!=='function'||!handle||typeof handle.getData!=='function'||!page||typeof page.getOperatorList!=='function'||!ownerKey||typeof ownerKey!=='object'||typeof assertCurrentSource!=='function'||typeof canonicalOperation!=='function'||typeof assertNativeFont!=='function'||typeof contextFor!=='function'||typeof yieldControl!=='function')refuse('Native glyph recording requires the owned actual source and bundled writer.');
 if(!Number.isSafeInteger(batchSize)||batchSize<1||batchSize>16384||!operators||!Array.isArray(operators.argsArray)||operators.fnArray?.length!==operators.argsArray.length||operators.fnArray.length>LIMITS.operators||!source||!/^[a-f0-9]{64}$/.test(source.sha256)||!Number.isSafeInteger(source.byteLength)||source.byteLength<1||source.byteLength>33554432||!Number.isSafeInteger(source.pageNumber)||source.pageNumber<1||!viewport||viewport.transform?.length!==6||!Array.from(viewport.transform).every(Number.isFinite)||![viewport.width,viewport.height].every(v=>Number.isFinite(v)&&v>0))refuse('Native glyph recording input exceeds its explicit envelope.');
 const sourceCopy=clone(source,{bytes:0}),view={width:viewport.width,height:viewport.height,transform:Array.from(viewport.transform)},names=new Map(Object.entries(pdfjs.OPS).map(([n,id])=>[id,n])),state={bytes:0},records=[],fonts=new Map(),fontRefs=new Map(),planeStack=[];let nodesCreated=0,selectedOperations=0,paintOrdinal=0,inText=false,stackDepth=0,fontId=null,yields=0,plane=null;
 const sameView=()=>Object.is(view.width,viewport.width)&&Object.is(view.height,viewport.height)&&view.transform.every((v,i)=>Object.is(v,viewport.transform[i]));
 abort(signal);if(await assertCurrentSource()===false)refuse('Complete native glyph source check failed.');abort(signal);
 if(await page.getOperatorList()!==operators||!sameView())refuse('Actual native page/operator or viewport identity changed.');
 const Base=numbers.createGraphicsClass(importer.rendererClass(pdfjs,{logicalTextSource}),pdfjs);
 class GlyphGraphics extends Base{_ensureTransformGroup(){return this.recordSink;}}
 const graphics=new GlyphGraphics(page.commonObjs,page.objs);graphics.embedFonts=false;graphics.svgFactory={createElement(name){nodesCreated++;return new RecordNode(name);}};graphics.recordSink=new RecordNode('svg:g');graphics.svg=new RecordNode('svg:g');graphics.defs=new RecordNode('svg:defs');graphics.viewport=viewport;
 graphics.recoveredTextItems=(await page.getTextContent({disableNormalization:true})).items;
 await graphics.loadDependencies(operators);abort(signal);
 function verifyFont(id,font){if(assertNativeFont(id,font)===false)refuse('Actual native font is not owned by the complete source.');const selected=Object.fromEntries(FONT_FIELDS.map(k=>[k,font[k]]));if(!fontRefs.has(id)){fontRefs.set(id,{font,selected:clone(selected,state)});}else if(fontRefs.get(id).font!==font||!same(selected,fontRefs.get(id).selected))refuse('Actual native font changed during glyph recording.');}
 for(let index=0;index<operators.fnArray.length;index++){
  if(index&&index%batchSize===0){await yieldControl();yields++;abort(signal);if(!sameView())refuse('Native glyph viewport changed during a yield.');}
  const code=operators.fnArray[index],name=names.get(code),args=operators.argsArray[index],text=TEXT.has(name),selected=text||STATE.has(name)||name==='save'||name==='restore';
  if(!selected&&!PATH_PAINTS.has(name)&&!IMAGE_PAINTS.has(name)&&!SKIP.has(name))refuse('Unqualified native glyph state operation '+name+'.');
  if(selected){const canonical=canonicalOperation(index);if(canonical?.code!==code||canonical?.name!==name||!same(args,canonical.args))refuse('Selected native glyph operation changed before execution.');selectedOperations++;}
  if((PATH_PAINTS.has(name)||IMAGE_PAINTS.has(name)||name==='constructPath'||name==='clip'||name==='eoClip')&&inText)refuse('Native path/image construction inside a text object is outside the bounded glyph profile.');
  if(name==='save'){if(++stackDepth>LIMITS.depth)refuse('Native glyph state stack exceeds its envelope.');planeStack.push(plane);graphics.save();continue;}
  if(name==='restore'){if(!stackDepth--)refuse('Unbalanced native glyph restore.');plane=planeStack.pop();graphics.restore();fontId=graphics.current.pdfSourceFontName||null;continue;}
  if(name==='transform'){if(args?.length!==6||!Array.from(args).every(Number.isFinite)||(plane?.depth||0)>=LIMITS.depth)refuse('Native glyph literal transform exceeds its envelope.');plane={parent:plane,depth:(plane?.depth||0)+1,values:Array.from(args)};}
  if(name==='beginText'){if(inText)refuse('Nested native text objects are unsupported.');inText=true;}
  if(text&&name!=='beginText'&&!inText)refuse('Native text operation has no open text object.');
  if(name==='setFont'){fontId=args[0];verifyFont(fontId,page.commonObjs.get(fontId));}
  if(name==='setGState')for(const [key,value]of args[0]){if(!['LW','LC','LJ','ML','D','RI','FL','Font','CA','ca'].includes(key))refuse('Unqualified native glyph graphics state '+key+'.');if(key==='Font'){fontId=value[0];verifyFont(fontId,page.commonObjs.get(fontId));}}
  const show=name==='showText'||name==='showSpacedText';
  if(show){if(records.length>=LIMITS.shows||graphics.current.textRenderingMode!==0||!graphics.current.font||graphics.current.fontSize===0)refuse('Native glyph show is outside the bounded fill-text profile.');verifyFont(fontId,graphics.current.font);}
  if(selected)graphics.executeOpTree([{fnId:code,fn:name,args}]);
  if(show){
   const current=graphics.current,span=current.tspan,element=current.txtElement,context=contextFor(index),literalPlanes=[];for(let p=plane;p;p=p.parent)literalPlanes.push(p.values);literalPlanes.reverse();if(!context||context.paintOrdinal!==paintOrdinal||context.transformPlanes&&!same(context.transformPlanes,literalPlanes)||!span?.getAttribute('data-pdf-glyph-map')||!element)refuse('Native glyph show does not match its complete canonical paint/planes.');
   const value={operatorIndex:index,paintOrdinal,sourceTextShowIndex:records.length,context,literalPlanes,sourceFontId:current.pdfSourceFontName,fontFamily:current.fontFamily,fontName:current.font.name||null,spanAttributes:attrs(span),textAttributes:attrs(element),renderedText:span.textContent,unicode:span.getAttribute('data-pdf-unicode'),glyphs:JSON.parse(span.getAttribute('data-pdf-glyph-map')),nativeTransform:Array.from(graphics.transformMatrix),textMatrix:Array.from(current.textMatrix),fontSize:current.fontSize,textRise:current.textRise,textHScale:current.textHScale,fontDirection:current.fontDirection,xcoords:Array.from(current.xcoords),ycoords:Array.from(current.ycoords)};
   records.push(clone(value,state));element.remove();if(graphics.recordSink.children.length)refuse('Native text output escaped its bounded record sink.');
  }
  if(name==='endText')inText=false;
  if(show||PATH_PAINTS.has(name)||IMAGE_PAINTS.has(name))paintOrdinal++;
 }
 if(stackDepth||inText||!sameView())refuse('Native glyph recording ended with incomplete state.');
 for(const [id,{font,selected}]of fontRefs){verifyFont(id,font);let programSha256=null,programBytes=0;if(font.data?.length){const data=font.data.slice();programBytes=data.byteLength;if(programBytes>LIMITS.retainedBytes)refuse('Native glyph font program exceeds its resource envelope.');programSha256=Array.from(new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256',data)),b=>b.toString(16).padStart(2,'0')).join('');verifyFont(id,font);abort(signal);}fonts.set(id,clone({id,...selected,programSha256,programBytes},state));}
 if(await page.getOperatorList()!==operators)refuse('Native glyph page identity changed before completion.');
 if(await assertCurrentSource()===false)refuse('Complete native glyph source check failed.');abort(signal);if(!sameView()||!same(source,sourceCopy))refuse('Native glyph source identity changed before completion.');
 for(const [id,{font}]of fontRefs)verifyFont(id,font);
 // The owner repeats its complete coherent check after every await above. The
 // returned token itself cannot authorize fresh SVG or a complete source store.
 if(!sameView())refuse('Native glyph viewport changed before issue.');
 const token=Object.freeze({});issued.set(token,{ownerKey,payload:Object.freeze({source:sourceCopy,frame:clone(view,state),records:Object.freeze(records),fonts:Object.freeze([...fonts.values()]),statistics:Object.freeze({operators:operators.fnArray.length,selectedOperations,paints:paintOrdinal,shows:records.length,nodesCreated,retainedBytes:state.bytes,yields})})});return token;
}
function consume(token,ownerKey){const entry=issued.get(token);if(!entry||entry.ownerKey!==ownerKey)refuse('Native glyph records require their exact hidden consumer.');issued.delete(token);return entry.payload;}
return Object.freeze({capture,consume,isIssued:token=>issued.has(token),LIMITS});
});
