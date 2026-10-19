/* Unwired dense candidate. Every paint comes from the complete canonical store.
 * Display bitmaps are disposable views; SVG/PDF never consume those bitmaps. */
(function(root,factory){const cjs=typeof module==='object'&&module.exports,numbers=cjs?require('./pdf-generated-number-tokens.js'):root.FigureStudioPdfGeneratedNumbers,dense=cjs?require('./pdf-dense-leaf-store.js'):root.FigureStudioPdfDenseLeafStore,groups=cjs?require('./pdf-dense-group-history.js'):root.FigureStudioPdfDenseGroupHistory,nativeCanvas=cjs?require('./pdf-dense-native-canvas.js'):root.FigureStudioPdfDenseNativeCanvas;const api=factory(numbers,dense,groups,nativeCanvas);if(cjs)module.exports=api;else root.FigureStudioPdfDenseVectorReplay=api;})(typeof globalThis==='object'?globalThis:this,function(numbers,dense,groups,nativeCanvas){
'use strict';
const I=[1,0,0,1,0,0],LIMITS=Object.freeze({outputBytes:268435456,tilePixels:16777216,segmentPixels:33554432,textShows:24,proxies:32});
const fillPaint=new Set(['fill','eoFill','fillStroke','eoFillStroke','closeFillStroke','closeEOFillStroke']);
const strokePaint=new Set(['stroke','closeStroke','fillStroke','eoFillStroke','closeFillStroke','closeEOFillStroke']);
const closePaint=new Set(['closeStroke','closeFillStroke','closeEOFillStroke']);
const evenPaint=new Set(['eoFill','eoFillStroke','closeEOFillStroke']);
const arity={moveTo:2,lineTo:2,curveTo:6,curveTo2:4,curveTo3:4,rectangle:4,closePath:0};
function refuse(message){const e=new Error(message);e.code='PDF_DENSE_REPLAY_UNSUPPORTED';throw e;}
function abort(signal){if(signal?.aborted){const e=new Error('Dense vector operation was cancelled.');e.name='AbortError';throw e;}}
function yieldTask(){return new Promise(resolve=>setTimeout(resolve,0));}
const mul=(a,b)=>[a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5]];
const same=(a,b)=>Array.isArray(a)&&Array.isArray(b)&&a.length===b.length&&a.every((v,i)=>Array.isArray(v)?same(v,b[i]):Object.is(v,b[i]));
const matrix=planes=>planes.reduce(mul,I);
const finite=a=>Array.isArray(a)&&a.every(Number.isFinite);
const n=value=>Object.is(value,-0)?'-0':String(value);
const xml=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
const matrixText=planes=>planes.map(m=>'matrix('+m.map(n).join(' ')+')').join(' ');
function checkStore(store){if(!dense?.hasByteProof(store)||!store.source().originalDecimalProofComplete)refuse('Dense rendering requires complete original numeric source proof from its private actual-byte factory.');if(store.statistics().textShowCount>LIMITS.textShows)refuse('Native text count exceeds the reviewed dense rendering envelope.');}
const groupProto=groups?.DenseGroupDocument.prototype,groupMethods=groupProto&&Object.fromEntries(['segments','placement'].map(name=>[name,groupProto[name]])),groupRevision=groupProto&&Object.getOwnPropertyDescriptor(groupProto,'revision').get;
const leafProto=dense.DenseLeafStore.prototype,leafWrite=leafProto.writeLeaves,authoredWriter=leafProto.authoredTextLocal,leafRevision=Object.getOwnPropertyDescriptor(leafProto,'revision').get;
function viewOf(store,document){checkStore(store);const version=Reflect.apply(leafRevision,store,[]);let revision=version,segments=null;
 if(document){if(!groups?.isDocumentFor(document,store))refuse('Authored rendering requires the exact private source coordinator.');revision=Reflect.apply(groupRevision,document,[]);segments=Array.from(Reflect.apply(groupMethods.segments,document,[]));}
 const assertCurrent=()=>{if(Reflect.apply(leafRevision,store,[])!==version||document&&(!groups.isDocumentFor(document,store)||Reflect.apply(groupRevision,document,[])!==revision))refuse('Dense source or authored document revision changed during rendering.');};
 const placement=ordinal=>{if(!segments)return {documentRevision:revision,leafRevision:version,semanticGroupPath:[],planePath:[]};let lo=0,hi=segments.length-1;while(lo<=hi){const mid=(lo+hi)>>1,s=segments[mid];if(ordinal<s.start)hi=mid-1;else if(ordinal>=s.end)lo=mid+1;else return {documentRevision:revision,leafRevision:version,semanticGroupPath:s.semanticGroupPath,planePath:s.planePath};}refuse('Authored coverage lost a canonical source paint.');};
 return {revision,leafRevision:version,segments,placement,assertCurrent,writeRows:async(write,options)=>{assertCurrent();await Reflect.apply(leafWrite,store,[async rows=>{assertCurrent();await write(rows);assertCurrent();},options]);assertCurrent();}};
}
function commands(chunks,names,visit){for(const chunk of chunks){const ops=chunk.args[0],values=chunk.args[1];let cursor=0;for(const op of ops){const name=names[op],count=arity[name];if(count===undefined||cursor+count>values.length)refuse('Incomplete canonical path command.');visit(name,Array.from(values.subarray?values.subarray(cursor,cursor+count):values.slice(cursor,cursor+count)),chunk);cursor+=count;}if(cursor!==values.length)refuse('Trailing canonical geometry operands.');}}
function color(row,key,format='css'){
 const raw=!row.editedFields?.includes('style')&&row.sourcePaint?.[key];
 // The shared initial DeviceGray0 record has a historical lowercase operator;
 // its use as stroke state still requires G, never a second fill operation.
 if(format==='pdf'&&raw)return raw.components.map(v=>v).concat(raw.components.length===1?(key==='fill'?'g':'G'):(key==='fill'?'rg':'RG'));
 const rgb=raw?(raw.components.length===1?Array(3).fill(raw.components[0]*255):raw.components.map(v=>v*255)):row.style[key];
 return format==='pdf'?rgb.map(v=>v/255).concat(key==='fill'?'rg':'RG'):'rgb('+rgb.map(n).join(',')+')';
}
function sourcePath(row,names,{rectangleAsLines=false}={}){
 if(row.pathChunks.some(c=>c.plane!==row.pathChunks[0].plane))refuse('SVG mixed native path planes require a separately qualified adapter.');
 // The native path plane is retained literally. No source vertex is flattened.
 let text='',x=0,y=0,sx=0,sy=0;
 commands(row.pathChunks,names,(name,a)=>{if(name==='moveTo'){text+='M'+a.map(n).join(' ');[x,y]=a;[sx,sy]=a;}
  else if(name==='lineTo'){text+='L'+a.map(n).join(' ');[x,y]=a;}
  else if(name==='curveTo'){text+='C'+a.map(n).join(' ');[x,y]=a.slice(4);}
  else if(name==='curveTo2'){text+='C'+[x,y,...a].map(n).join(' ');[x,y]=a.slice(2);}
  else if(name==='curveTo3'){text+='C'+[...a,...a.slice(2)].map(n).join(' ');[x,y]=a.slice(2);}
  else if(name==='closePath'){text+='Z';x=sx;y=sy;}
  else if(name==='rectangle'){const[rx,ry,w,h]=a;
   // Bounded native controls use the same four literal corner calculations as
   // bundled CanvasGraphics.constructPath. The canonical rectangle operands
   // remain unchanged in the source store and ordinary vector serialization.
   text+=rectangleAsLines?'M'+[rx,ry].map(n).join(' ')+'L'+[rx+w,ry].map(n).join(' ')+'L'+[rx+w,ry+h].map(n).join(' ')+'L'+[rx,ry+h].map(n).join(' ')+'Z':'M'+[rx,ry].map(n).join(' ')+'h'+n(w)+'v'+n(h)+'h'+n(-w)+'Z';x=sx=rx;y=sy=ry;}
 });if(closePaint.has(row.paintOperator))text+='Z';return text;
}
function clips(store,index){const result=[];while(index){const clip=store.clip(index);result.push(clip);index=clip.parentClipIndex;}return result.reverse();}
function checkPathPlanes(store,row){if(row.pathChunks.some(chunk=>!same(store.plane(chunk.plane),row.editedFields?.includes('transformPlanes')?store.plane(row.pathChunks[0].plane):row.transformPlanes)))refuse('Path construction and painting use different native planes; a per-chunk adapter is required.');}
function glyphLayout(row,font){
 const state=row.text.state,m=font.fontMatrix||[.001,0,0,.001,0,0];
 if(!same(m,[.001,0,0,.001,0,0])||state.hScale===0||state.textRenderingMode!==0)refuse('Native text needs the qualified horizontal standard font matrix and fill mode.');
 let x=0,charIndex=0;const glyphs=[];
 for(const glyph of row.text.glyphs){if(typeof glyph==='number'){x-=glyph*state.fontSize*.001;continue;}
  if([...glyph.fontChar].length!==1)refuse('Native multi-character font glyph needs the positioned text adapter.');
  glyphs.push({unicode:glyph.unicode,fontChar:glyph.fontChar,charIndex,charCount:glyph.unicode.length,x,y:0,width:glyph.width});
  x+=glyph.width*.001*state.fontSize+state.charSpacing+(glyph.isSpace?state.wordSpacing:0);charIndex+=glyph.unicode.length;
 }
 return {glyphs,width:x,state,font};
}
function fontFamily(font){return font.data?.length?'DenseNative_'+font.id:(font.name||font.fallbackName||'sans-serif');}
function nativeTextSvg(record){const attributes=rows=>rows.map(([key,value])=>' '+key+'="'+xml(value)+'"').join('');return '<g transform="'+matrixText(record.literalPlanes)+'"><text'+attributes(record.textAttributes)+'><tspan'+attributes(record.spanAttributes)+'>'+xml(record.renderedText)+'</tspan></text></g>';}
function nativeGlyphSvg(store,id,{document}={}){const view=viewOf(store,document),row=store.read(id);if(row.kind!=='text')refuse('Native glyph fragments require a text source leaf.');const proof=store.nativeGlyphRecords(),record=proof.records.find(value=>value.context.id===id);if(!record||record.operatorIndex!==row.operatorIndex||record.paintOrdinal!==row.paintOrdinal)refuse('Native glyph fragment has no actual writer record.');
 const frame=store.frame(),names=store.operationNames(),chain=clips(store,row.clipIndex),prefix='dense-text-'+row.operatorIndex+'-clip-';let defs='';for(const clip of chain){checkPathPlanes(store,clip);defs+='<clipPath id="'+prefix+clip.index+'" clipPathUnits="userSpaceOnUse"><path transform="'+matrixText(clip.transformPlanes)+'" d="'+sourcePath({...clip,paintOperator:'clip'},names)+'" clip-rule="'+clip.rule+'"/></clipPath>';}
 const svg='<svg xmlns="http://www.w3.org/2000/svg" width="'+n(frame.width)+'" height="'+n(frame.height)+'" viewBox="0 0 '+n(frame.width)+' '+n(frame.height)+'"><defs>'+defs+'</defs><g transform="matrix('+frame.transform.map(n).join(' ')+')">'+chain.map(clip=>'<g clip-path="url(#'+prefix+clip.index+')">').join('')+nativeTextSvg(record)+'</g>'.repeat(chain.length+1)+'</svg>';
 if(new TextEncoder().encode(svg).length>16777216)refuse('Native glyph fragment exceeds its bounded view envelope.');view.assertCurrent();return {id,operatorIndex:row.operatorIndex,paintOrdinal:row.paintOrdinal,source:store.source(),frame,svg,record,...(row.authoredText?{authoredText:row.authoredText}:{}),placement:view.placement(row.paintOrdinal),clipIndices:chain.map(clip=>clip.index),sourceFontId:record.sourceFontId,fontResource:proof.fonts.find(font=>font.id===record.sourceFontId),fontProgramsExternal:true};
}
function base64(bytes){if(typeof Buffer==='function')return Buffer.from(bytes).toString('base64');let text='';for(let i=0;i<bytes.length;i+=8192)text+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(text);}
function createSink(write){let bytes=0;return async text=>{bytes+=new TextEncoder().encode(text).length;if(bytes>LIMITS.outputBytes)refuse('Dense vector output exceeds its explicit byte envelope.');await write(text);};}
async function writeSvg(store,write,{signal,yieldControl=yieldTask,document}={}){
 const view=viewOf(store,document),source=store.source(),frame=store.frame(),names=store.operationNames(),fonts=store.fonts(),glyphRecords=store.nativeGlyphRecords(),glyphById=new Map(glyphRecords.records.map(record=>[record.context.id,record])),revision=view.revision,emit=createSink(write);
 await emit('<svg xmlns="http://www.w3.org/2000/svg" width="'+n(frame.width)+'" height="'+n(frame.height)+'" viewBox="0 0 '+n(frame.width)+' '+n(frame.height)+'" data-source-sha256="'+source.sha256+'" data-source-page="'+source.pageNumber+'"><defs>');
 for(const font of fonts)if(font.data?.length){const family=glyphRecords.records.find(record=>record.sourceFontId===font.id)?.fontFamily;if(!family)refuse('Native SVG font family is unavailable.');await emit('<style>@font-face{font-family:'+xml(family)+';src:url(data:'+(font.mimetype||'font/opentype')+';base64,'+base64(font.data)+')}</style>');}
 const clipCount=store.statistics().clipCount;
 for(let i=1;i<=clipCount;i++){abort(signal);const clip=store.clip(i);checkPathPlanes(store,clip);const path=sourcePath({...clip,paintOperator:'clip'},names);await emit('<clipPath id="dense-clip-'+i+'" clipPathUnits="userSpaceOnUse"><path transform="'+matrixText(clip.transformPlanes)+'" d="'+path+'" clip-rule="'+clip.rule+'"/></clipPath>');if(i%128===0)await yieldControl();}
 await emit('</defs><g transform="matrix('+frame.transform.map(n).join(' ')+')">');
 await view.writeRows(async rows=>{let text='';for(const row of rows){const chain=clips(store,row.clipIndex),placement=view.placement(row.paintOrdinal),authored=placement.planePath;text+='<g data-source-id="'+row.id+'" data-source-op="'+row.operatorIndex+'" data-paint-ordinal="'+row.paintOrdinal+'">'+authored.map(plane=>'<g data-authored-plane="'+plane.nodeId+'" transform="'+matrixText([plane.matrix])+'">').join('')+chain.map(c=>'<g clip-path="url(#dense-clip-'+c.index+')">').join('');
   if(row.kind==='text'){const record=glyphById.get(row.id);if(!record||record.operatorIndex!==row.operatorIndex||record.paintOrdinal!==row.paintOrdinal)refuse('Actual native glyph writer record disappeared.');text+=row.authoredText?'<g transform="'+matrixText(row.transformPlanes)+'">'+Reflect.apply(authoredWriter,store,[row.id,'svg'])+'</g>':nativeTextSvg(record);}
   else{checkPathPlanes(store,row);
    text+='<path transform="'+matrixText(row.transformPlanes)+'" d="'+sourcePath(row,names)+'" fill="'+(fillPaint.has(row.paintOperator)?color(row,'fill'):'none')+'" fill-rule="'+(evenPaint.has(row.paintOperator)?'evenodd':'nonzero')+'" stroke="'+(strokePaint.has(row.paintOperator)?color(row,'stroke'):'none')+'" stroke-width="'+n(row.style.lineWidth)+'" stroke-linecap="'+['butt','round','square'][row.style.lineCap]+'" stroke-linejoin="'+['miter','round','bevel'][row.style.lineJoin]+'" stroke-miterlimit="'+n(row.style.miter)+'"/>';}
   text+='</g>'.repeat(authored.length+chain.length+1);
  }await emit(text);},{signal,yieldControl,batchSize:128});
 view.assertCurrent();await emit('</g></svg>');view.assertCurrent();return {source,revision,leafRevision:view.leafRevision,paintCount:store.size,pathCount:store.statistics().pathCount,textCount:store.statistics().textShowCount,clipCount};
}
function canvasPath(ctx,chunks,names,base,planesForChunk){ctx.beginPath();commands(chunks,names,(name,a,chunk)=>{ctx.setTransform(...mul(base,matrix(planesForChunk(chunk))));if(name==='moveTo')ctx.moveTo(...a);else if(name==='lineTo')ctx.lineTo(...a);else if(name==='curveTo')ctx.bezierCurveTo(...a);else if(name==='curveTo2'){refuse('Canvas shorthand cubic requires a native current-point adapter.');}else if(name==='curveTo3'){ctx.bezierCurveTo(...a,...a.slice(2));}else if(name==='rectangle'){
 // Match the actual bundled CanvasGraphics.constructPath rectangle calls.
 // ctx.rect can add float-projected extents inside the graphics backend;
 // the native writer first adds the original Numbers in JavaScript.
 const[x,y,w,h]=a,xw=x+w,yh=y+h;ctx.moveTo(x,y);if(w===0||h===0)ctx.lineTo(xw,yh);else{ctx.lineTo(xw,y);ctx.lineTo(xw,yh);ctx.lineTo(x,yh);}ctx.closePath();
 }else ctx.closePath();});}
// All chunks in the complete reviewed source use the same plane as the leaf.
// Other native sources refuse here until an exact per-chunk plane adapter exists.
function leafCanvasPath(ctx,row,names,base){if(row.pathChunks.some(c=>c.plane!==row.pathChunks[0].plane))refuse('Canvas mixed-plane source path is outside this replay qualification.');canvasPath(ctx,row.pathChunks,names,base,()=>row.transformPlanes);if(closePaint.has(row.paintOperator))ctx.closePath();}
function strokeStyle(ctx,row){if(row.style.lineWidth===0)refuse('PDF hairline replay requires a separately qualified device-space policy.');ctx.lineWidth=row.style.lineWidth;ctx.lineCap=['butt','round','square'][row.style.lineCap];ctx.lineJoin=['miter','round','bevel'][row.style.lineJoin];ctx.miterLimit=row.style.miter;ctx.strokeStyle=color(row,'stroke');}
function applyClip(ctx,store,index,names,base){for(const clip of clips(store,index)){checkPathPlanes(store,clip);leafCanvasPath(ctx,{...clip,paintOperator:'clip'},names,base);ctx.clip(clip.rule);}}
function drawLeaf(ctx,store,row,names,base,fontById,placementPlanes=[]){base=mul(base,matrix(placementPlanes));ctx.save();try{applyClip(ctx,store,row.clipIndex,names,base);ctx.setTransform(...mul(base,matrix(row.transformPlanes)));ctx.fillStyle=color(row,'fill');
 if(row.kind==='path'){checkPathPlanes(store,row);leafCanvasPath(ctx,row,names,base);ctx.setTransform(...mul(base,matrix(row.transformPlanes)));if(fillPaint.has(row.paintOperator))ctx.fill(evenPaint.has(row.paintOperator)?'evenodd':'nonzero');if(strokePaint.has(row.paintOperator)){strokeStyle(ctx,row);ctx.stroke();}}
 else{const font=fontById.get(row.text.fontId);if(!font)refuse('Native glyph font is unavailable.');const layout=glyphLayout(row,font),s=layout.state;ctx.setTransform(...mul(mul(mul(base,matrix(row.transformPlanes)),s.textMatrix),[s.hScale/100,0,0,-1,0,s.rise]));ctx.font=(font.italic?'italic ':'')+(font.bold?'bold ':'')+s.fontSize+'px "'+fontFamily(font).replace(/["\\]/g,'')+'"';ctx.textBaseline='alphabetic';for(const glyph of layout.glyphs)ctx.fillText(glyph.fontChar,glyph.x,0);}
 }finally{ctx.restore();}}
async function loadFonts(store,fontSet=globalThis.fonts){const result=new Map();for(const font of store.fonts()){if(font.data?.length){if(typeof FontFace!=='function'||!fontSet?.add)refuse('Native embedded font installation is unavailable.');const face=new FontFace(fontFamily(font),font.data,{weight:font.bold?'bold':'normal',style:font.italic?'italic':'normal'});await face.load();fontSet.add(face);}result.set(font.id,font);}return result;}
async function renderTile(store,{x=0,y=0,width,height,scale=1,excludeIds=[],splitIds=[],splitNativeText=false,document,nativeFactory,signal,yieldControl=yieldTask,canvasFactory=(w,h)=>new OffscreenCanvas(w,h)}={}){
 const view=viewOf(store,document),frame=store.frame();width??=frame.width;height??=frame.height;if(!finite([x,y,width,height,scale])||width<=0||height<=0||scale<=0||Math.ceil(width*scale)*Math.ceil(height*scale)>LIMITS.tilePixels||!Array.isArray(excludeIds)||!Array.isArray(splitIds)||excludeIds.length>LIMITS.proxies||splitIds.length>LIMITS.proxies||new Set(splitIds).size!==splitIds.length)refuse('Display tile exceeds its explicit size/proxy envelope.');
 const slots=new Set(splitIds);for(const id of slots)if(store.read(id).kind!=='path')refuse('Native path slots require canonical path identities.');for(const id of excludeIds)store.read(id);
 const pixelWidth=Math.ceil(width*scale),pixelHeight=Math.ceil(height*scale),canvas=canvasFactory(pixelWidth,pixelHeight),ctx=canvas.getContext('2d'),base=mul([scale,0,0,scale,-x*scale,-y*scale],frame.transform),names=store.operationNames(),fontById=splitNativeText?new Map():await loadFonts(store),excluded=new Set(excludeIds),revision=view.revision,segments=[];let paints=0,startOrdinal=0,segmentPaints=0,allocatedPixels=0,painter;
 if(nativeFactory){if(!nativeCanvas?.isFactory(nativeFactory))refuse('Native Canvas rendering requires its privately issued constructor factory.');painter=nativeFactory.createPainter(ctx,{...frame,width:pixelWidth,height:pixelHeight,scale,transform:base});}
 const withPlanes=row=>({...row,pathPlaneChains:row.pathChunks.map(chunk=>store.plane(chunk.plane))});
 async function finish(endOrdinal){abort(signal);view.assertCurrent();let bitmap=null;if(segmentPaints){allocatedPixels+=pixelWidth*pixelHeight;if(allocatedPixels>LIMITS.segmentPixels)refuse('Ordered path/text display segments exceed the explicit cache pixel envelope.');bitmap=await createImageBitmap(canvas);segments.push({kind:'paths',startOrdinal,endOrdinal,bitmap});view.assertCurrent();if(painter)painter.clear();else{ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,pixelWidth,pixelHeight);}}else segments.push({kind:'paths',startOrdinal,endOrdinal,bitmap:null});segmentPaints=0;}
 try{await view.writeRows(async rows=>{for(const row of rows){abort(signal);const placement=view.placement(row.paintOrdinal);if(slots.has(row.id)||splitNativeText&&row.kind==='text'){await finish(row.paintOrdinal);segments.push({kind:row.kind==='text'?'nativeText':'nativePath',record:{...row,placement}});startOrdinal=row.paintOrdinal+1;}else if(!excluded.has(row.id)){if(row.authoredText)refuse('Authored labels require their native editable text slots.');const placementPlanes=placement.planePath.map(plane=>plane.matrix);if(painter&&row.kind==='path')painter.drawPath(withPlanes(row),clips(store,row.clipIndex).map(withPlanes),names,{placementPlanes});else drawLeaf(ctx,store,row,names,base,fontById,placementPlanes);paints++;segmentPaints++;}}},{signal,yieldControl,batchSize:128});await finish(store.size);view.assertCurrent();painter?.close();painter=null;return {source:store.source(),revision,leafRevision:view.leafRevision,rect:{x,y,width,height,scale},segments,renderedPaints:paints,canonicalPaintCount:store.size,allocatedPixels,pathRenderer:nativeFactory?'actual bundled CanvasGraphics':'candidate Canvas path policy'};
 }catch(error){for(const segment of segments)segment.bitmap?.close();try{painter?.close();}catch{}throw error;}
}
function queryRect(store,box,{document}={}){const view=viewOf(store,document);if(!finite(box)||box.length!==4||box[0]>box[2]||box[1]>box[3])refuse('Finite ordered query bounds required.');if(!view.segments)return store.queryRect(box);
 const frame=store.frame().transform,result=[],cache=new Map(),op=id=>Number(id.slice(id.lastIndexOf(':op')+3));
 for(const segment of view.segments){const authored=matrix(segment.planePath.map(plane=>plane.matrix));if(authored[0]!==1||authored[1]!==0||authored[2]!==0||authored[3]!==1)refuse('Authored spatial queries require literal translations.');const dx=frame[0]*authored[4]+frame[2]*authored[5],dy=frame[1]*authored[4]+frame[3]*authored[5],key=n(dx)+','+n(dy);let ids=cache.get(key);if(!ids){ids=store.queryRect([box[0]-dx,box[1]-dy,box[2]-dx,box[3]-dy]);cache.set(key,ids);}const first=op(store.idAt(segment.start)),last=segment.end===store.size?Infinity:op(store.idAt(segment.end));for(const id of ids){const index=op(id);if(index>=first&&index<last)result.push(id);}}
 view.assertCurrent();return result.sort((a,b)=>op(a)-op(b));
}
function hitPath(store,ctx,x,y,{tolerance=0,limit=1,document}={}){
 const view=viewOf(store,document);if(!finite([x,y,tolerance])||tolerance<0||!Number.isInteger(limit)||limit<1||limit>LIMITS.proxies)refuse('Invalid bounded exact path hit query.');const result=[],names=store.operationNames(),frame=store.frame().transform;
 for(const id of queryRect(store,[x-tolerance,y-tolerance,x+tolerance,y+tolerance],{document}).reverse()){const row=store.read(id);if(row.kind==='text')continue;const placement=view.placement(row.paintOrdinal),base=mul(frame,matrix(placement.planePath.map(plane=>plane.matrix)));ctx.save();try{let inside=true;for(const clip of clips(store,row.clipIndex)){checkPathPlanes(store,clip);leafCanvasPath(ctx,{...clip,paintOperator:'clip'},names,base);if(!ctx.isPointInPath(x,y,clip.rule)){inside=false;break;}}if(!inside)continue;checkPathPlanes(store,row);leafCanvasPath(ctx,row,names,base);ctx.setTransform(...mul(base,matrix(row.transformPlanes)));let hit=fillPaint.has(row.paintOperator)&&ctx.isPointInPath(x,y,evenPaint.has(row.paintOperator)?'evenodd':'nonzero');if(!hit&&strokePaint.has(row.paintOperator)){strokeStyle(ctx,row);if(tolerance)refuse('Stroke hit tolerance needs an exact device-space adapter.');hit=ctx.isPointInStroke(x,y);}if(hit){result.push({...row,placement});if(result.length===limit)break;}}finally{ctx.restore();}}
 view.assertCurrent();return result;
}
function pdfNumberWriter(){if(typeof numbers?.number!=='function')refuse('Qualified generated PDF decimal writer is unavailable.');const cache=new Map();return value=>{const key=Object.is(value,-0)?'-0':String(value);if(!cache.has(key)){if(cache.size>=4096)cache.clear();cache.set(key,numbers.number(value));}return cache.get(key);};}
function pdfPath(chunks,names,num){let result='';commands(chunks,names,(name,a)=>{const op={moveTo:'m',lineTo:'l',curveTo:'c',curveTo2:'v',curveTo3:'y',rectangle:'re',closePath:'h'}[name];result+=a.map(num).join(' ')+(a.length?' ':'')+op+'\n';});return result;}
async function writePdfContent(store,write,{signal,yieldControl=yieldTask,document}={}){
 const view=viewOf(store,document),names=store.operationNames(),num=pdfNumberWriter(),revision=view.revision,emit=createSink(write);let clipsWritten=0;
 const transforms=planes=>planes.map(plane=>plane.map(num).join(' ')+' cm\n').join('');
 await emit('% Complete canonical dense source '+store.source().sha256+' page '+store.source().pageNumber+'\n');
 await view.writeRows(async rows=>{let output='';for(const row of rows){output+='% source-op '+row.operatorIndex+' paint '+row.paintOrdinal+'\nq\n'+transforms(view.placement(row.paintOrdinal).planePath.map(plane=>plane.matrix));for(const clip of clips(store,row.clipIndex)){checkPathPlanes(store,clip);if(clip.transformPlanes.length)refuse('Native PDF clips with declaring transforms require a qualified path-state adapter.');output+=pdfPath(clip.pathChunks,names,num)+(clip.rule==='evenodd'?'W*':'W')+' n\n';clipsWritten++;}
   const s=row.style,fill=color(row,'fill','pdf'),stroke=color(row,'stroke','pdf');output+=fill.slice(0,-1).map(num).join(' ')+' '+fill.at(-1)+'\n'+stroke.slice(0,-1).map(num).join(' ')+' '+stroke.at(-1)+'\n'+[s.lineWidth,'w',s.lineCap,'J',s.lineJoin,'j',s.miter,'M'].map(v=>typeof v==='number'?num(v):v).join(' ')+'\n';
   if(row.kind==='path'){checkPathPlanes(store,row);output+=transforms(row.transformPlanes)+pdfPath(row.pathChunks,names,num)+({fill:'f',eoFill:'f*',stroke:'S',closeStroke:'s',fillStroke:'B',eoFillStroke:'B*',closeFillStroke:'b',closeEOFillStroke:'b*'}[row.paintOperator])+'\n';}
   else if(row.authoredText)output+=transforms(row.transformPlanes)+Reflect.apply(authoredWriter,store,[row.id,'pdf']);
   else{const source=store.sourceText(row.id),state=row.text.state;if(!/^[A-Za-z0-9_.+-]+$/.test(source.sourceFontName))refuse('Source PDF font resource name needs an escaped-name adapter.');output+=transforms(row.transformPlanes)+'BT\n/'+source.sourceFontName+' '+num(state.fontSize)+' Tf\n'+num(state.charSpacing)+' Tc '+num(state.wordSpacing)+' Tw '+num(state.hScale)+' Tz '+num(state.rise)+' Ts\n'+state.textMatrix.map(num).join(' ')+' Tm\n['+source.encoded.map(value=>value.charCode===undefined?num(value.adjustment):'<'+value.charCode.toString(16).padStart(2,'0')+'>').join(' ')+'] TJ\nET\n';}
   output+='Q\n';}await emit(output);},{signal,yieldControl,batchSize:128});view.assertCurrent();return {source:store.source(),revision,leafRevision:view.leafRevision,paintCount:store.size,pathCount:store.statistics().pathCount,textCount:store.statistics().textShowCount,clipApplications:clipsWritten};
}
async function buildPdf(store,sourceBytes,pdfLib,options={}){if(!pdfLib?.PDFDocument)refuse('Bundled native PDF writer is unavailable.');const view=viewOf(store,options.document),source=store.source(),digest=await crypto.subtle.digest('SHA-256',sourceBytes),sha=Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,'0')).join('');view.assertCurrent();if(sha!==source.sha256||sourceBytes.length!==source.byteLength)refuse('Native PDF export source bytes differ from the document owner.');const parts=[],metadata=await writePdfContent(store,text=>parts.push(text),options),document=await pdfLib.PDFDocument.load(sourceBytes),page=document.getPages()[source.pageNumber-1];view.assertCurrent();const text=parts.join(''),stream=document.context.flateStream(new TextEncoder().encode(text));page.node.set(pdfLib.PDFName.of('Contents'),document.context.register(stream));const result=await pdfLib.PDFDocument.create(),[copied]=await result.copyPages(document,[source.pageNumber-1]);result.addPage(copied);result.setSubject('Canonical dense vector source '+source.sha256+' page '+source.pageNumber);abort(options.signal);const bytes=await result.save();view.assertCurrent();abort(options.signal);return {bytes,metadata};}
return Object.freeze({LIMITS,writeSvg,writePdfContent,buildPdf,renderTile,queryRect,hitPath,nativeGlyphSvg,glyphLayout,loadFonts,drawLeaf,sourcePath});
});
