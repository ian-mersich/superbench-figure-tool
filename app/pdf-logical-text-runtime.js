(function(root,factory){
  const protocol=typeof module==='object'&&module.exports?require('./pdf-logical-text-protocol.js'):root.FigureStudioPdfLogicalTextProtocol;
  const generatedNumbers=typeof module==='object'&&module.exports?require('./pdf-generated-number-tokens.js'):root.FigureStudioPdfGeneratedNumbers;
  const clipPlanes=typeof module==='object'&&module.exports?require('./pdf-current-native-clip-planes.js'):root.FigureStudioPdfCurrentNativeClipPlanes;
  const localSvg=typeof module==='object'&&module.exports?require('./pdf-current-native-local-svg.js'):root.FigureStudioPdfCurrentNativeLocalSvg;
  const nativePlanes=typeof module==='object'&&module.exports?require('./pdf-current-native-plane-materializer.js'):root.FigureStudioPdfCurrentNativePlaneMaterializer;
  const operatorSnapshots=typeof module==='object'&&module.exports?require('./pdf-current-native-operator-snapshots.js'):root.FigureStudioPdfCurrentNativeOperatorSnapshots;
  const api=factory(protocol,generatedNumbers,clipPlanes,localSvg,nativePlanes,operatorSnapshots);
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.FigureStudioPdfLogicalTextRuntime=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(protocol,generatedNumbers,clipPlanes,localSvg,nativePlanes,operatorSnapshots){
'use strict';
const ATTR='data-figure-studio-native-logical-glyph';
const sources=new WeakMap();
const sameCurrentOperators=(operators,snapshot,signal)=>operatorSnapshots?.isIssued(snapshot)?operatorSnapshots.same(operators,snapshot,{signal}):clipPlanes.sameOperators(operators,snapshot);
const clone=value=>JSON.parse(JSON.stringify(value));
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const multiply=(a,b)=>[a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5]];
function refuse(message){const error=new Error(message);error.code='PDF_LOGICAL_TEXT_UNSUPPORTED';throw error;}
async function digest(data){const value=new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256',data));return Array.from(value,byte=>byte.toString(16).padStart(2,'0')).join('');}
function ownExportObserver(pdf,svg){
  const owned=Number(svg?.getAttribute?.('data-pdf-source-count'))>0||svg?.getAttribute?.('data-figure-studio-svg-source-numeric-policy')==='figureStudio.svgSourcePageNumbers.v1';
  if(!owned)return null;
  let parents;
  try{parents=protocol.currentScalarParents(svg);}catch(error){if(error.code==='PDF_LOGICAL_TEXT_UNSUPPORTED')return null;throw error;}
  const capture=protocol.createEmissionCapture(parents,{pdf}),detach=protocol.installInstanceObserver(pdf,capture);
  return {capture,detach};
}
const PAINTS=['fill','eoFill','stroke','closeStroke','fillStroke','eoFillStroke','closeFillStroke','closeEOFillStroke','showText','showSpacedText','paintSolidColorImageMask','paintImageMaskXObject','paintImageMaskXObjectGroup','paintImageXObject','paintImageXObjectRepeat','paintInlineImageXObject','paintInlineImageXObjectGroup','shadingFill'];
// Native font/glyph/show/order only. Geometry is read later from the current
// decoded SVG/native object hierarchy. This never measures or renders text.
async function nativeShows(pdfjs,page,operators,{currentClipAuthority=null}={}){
  const currentPlaneShows=currentClipAuthority?(clipPlanes?.isBatchedAuthority(currentClipAuthority)?await clipPlanes.currentShowsBatched(currentClipAuthority,operators,pdfjs.OPS):clipPlanes?.currentShows(currentClipAuthority,operators,pdfjs.OPS)):null;
  if(currentClipAuthority&&!currentPlaneShows)refuse('Current native clip authority is unavailable.');
  const fonts=new Map(),names=new Map(Object.entries(pdfjs.OPS).map(([name,id])=>[id,name]));
  for(let i=0;i<operators.fnArray.length;i++)if(operators.fnArray[i]===pdfjs.OPS.setFont){const id=operators.argsArray[i][0];if(!fonts.has(id)){const font=await new Promise(resolve=>page.commonObjs.get(id,resolve));fonts.set(id,{font,programSha256:font.data?await digest(font.data):null});}}
  const viewport=page.getViewport({scale:1}).transform;
  let current={font:null,size:0,clips:[],clipSources:[],ctm:[1,0,0,1,0,0],groupDepth:0},pendingClip=null,pathPoints=null,paintOrdinal=0,index=0;const stack=[],shows=[];
  for(let operation=0;operation<operators.fnArray.length;operation++){
    const name=names.get(operators.fnArray[operation]),args=operators.argsArray[operation]||[];
    if(name==='save'){stack.push({...current,clips:current.clips.slice(),clipSources:clone(current.clipSources),ctm:current.ctm.slice()});continue;}
    if(name==='restore'){if(!stack.length)refuse('Decoded native graphics state is unbalanced.');current=stack.pop();continue;}
    if(name==='transform'){current.ctm=multiply(current.ctm,args);continue;}
    if(name==='paintFormXObjectBegin'){stack.push({...current,clips:current.clips.slice(),clipSources:clone(current.clipSources),ctm:current.ctm.slice()});current.groupDepth++;continue;}
    if(name==='paintFormXObjectEnd'){if(!stack.length)refuse('Decoded native Form scope is unbalanced.');current=stack.pop();continue;}
    if(name==='beginGroup'||name==='endGroup')refuse('Logical coalescing has not qualified native transparency groups.');
    if(name==='setFont'){current.font=fonts.get(args[0]);current.size=args[1];continue;}
    if(name==='constructPath'){
      let cursor=0,points=[],supported=true;
      for(const id of args[0]){if(id===pdfjs.OPS.rectangle){const [x,y,w,h]=args[1].slice(cursor,cursor+4);cursor+=4;points.push([x,y],[x+w,y],[x+w,y+h],[x,y+h]);}else if(id===pdfjs.OPS.moveTo||id===pdfjs.OPS.lineTo){points.push(args[1].slice(cursor,cursor+2));cursor+=2;}else if(id!==pdfjs.OPS.closePath){supported=false;break;}}
      if(points.length===5&&same(points[0],points[4]))points.pop();const world=multiply(viewport,current.ctm);
      pathPoints=supported&&points.length===4?points.map(point=>[world[0]*point[0]+world[2]*point[1]+world[4],world[1]*point[0]+world[3]*point[1]+world[5]]):null;continue;
    }
    if(name==='clip'||name==='eoClip'){pendingClip={operator:operation,source:{kind:pathPoints?'rect':'unknown',points:pathPoints?clone(pathPoints):null,rule:name==='clip'?'nonzero':'evenodd',inverted:false,source:'decoded-pdf',sourceOperatorIndex:operation}};continue;}
    if(name==='endPath'){if(pendingClip!==null){current.clips.push(pendingClip.operator);current.clipSources.push(pendingClip.source);pendingClip=null;}pathPoints=null;continue;}
    if(name==='showText'||name==='showSpacedText'){
      const glyphs=args[0]?.filter?.(glyph=>glyph&&typeof glyph==='object')||[],entry=current.font,font=entry?.font;
      if(!font||font.vertical||font.isType3Font||glyphs.length!==1||!Number.isFinite(current.size)||current.size<=0||current.groupDepth)refuse(`Own-export logical source requires scalar horizontal native text shows outside Forms (show ${index}, glyphs ${glyphs.length}, font ${font?.name||'missing'}, vertical ${Boolean(font?.vertical)}, Type3 ${Boolean(font?.isType3Font)}, size ${current.size}, Form depth ${current.groupDepth}).`);
      const glyph=glyphs[0];
      shows.push({unicode:glyph.unicode,fontChar:glyph.fontChar,sourceFontName:font.name,fontSize:current.size,fontWeight:font.bold?'bold':'normal',fontStyle:font.italic?'italic':'normal',sourceEmbeddedProgram:!font.missingFile,programSha256:entry.programSha256,sourceAdvance:glyph.width*(font.fontMatrix?.[0]||.001),sourceTextShowIndex:index++,nativeShowGlyphCount:1,sourceOperatorIndex:operation,paintOrdinal:paintOrdinal++,clipOperatorIndexes:current.clips.slice(),nativeClipSources:clone(current.clipSources)});continue;
    }
    if(PAINTS.includes(name)){paintOrdinal++;if(pendingClip!==null){current.clips.push(pendingClip.operator);current.clipSources.push(pendingClip.source);pendingClip=null;}pathPoints=null;}
  }
  if(stack.length||pendingClip!==null)refuse('Decoded native source scopes are incomplete.');
  if(currentPlaneShows){if(currentPlaneShows.length!==shows.length)refuse('Current native clip show count differs.');for(let index=0;index<shows.length;index++){const planeShow=currentPlaneShows[index];if(planeShow.sourceTextShowIndex!==index||!same(planeShow.clips.map(clip=>clip.sourceOperatorIndex),shows[index].clipOperatorIndexes))refuse('Current native clip operation order differs.');shows[index].nativeClipPlaneOperations=planeShow;}}
  return shows;
}
async function decodeShows(pdfjs,bytes){
  const handle=await pdfjs.getDocument({data:new Uint8Array(bytes).slice(),fontExtraProperties:true,isOffscreenCanvasSupported:false,useSystemFonts:true}).promise;
  try{if(handle.numPages!==1)refuse('Logical source emission supports one generated page.');const page=await handle.getPage(1);return await nativeShows(pdfjs,page,await page.getOperatorList());}finally{await handle.destroy();}
}
async function completeOwnExport(bytes,capture,{pdfjs,pdfLib}) {
  // Authenticate the actual writer's original rows before any numeric rewrite.
  const {document,content}=await protocol.readContent(bytes,pdfLib);
  let marker=await capture.finish(content),finalBytes=bytes,finalContent=content;
  if(!generatedNumbers?.rewriteOwnedContentBatched||!generatedNumbers?.auditedDecimal||!protocol.rebindOwnGeneratedContentBatched) refuse('Own generated number preservation is unavailable.');
  const rewritten=await generatedNumbers.rewriteOwnedContentBatched(content);
  const rebound=await protocol.rebindOwnGeneratedContentBatched(marker,content,rewritten.content,{decodeNumericToken:generatedNumbers.auditedDecimal});
  marker=rebound.marker;
  if(rewritten.content!==content){
    const page=document.getPages()[0],name=pdfLib.PDFName.of;
    const raw=page.node.get(name('Contents')),container=document.context.lookup(raw);
    const reference=container instanceof pdfLib.PDFArray?container.get(0):raw;
    if(!(reference instanceof pdfLib.PDFRef)) refuse('Own generated stream reference is unsupported.');
    document.context.assign(reference,document.context.flateStream(Uint8Array.from(rewritten.content,character=>character.charCodeAt(0))));
    finalBytes=await document.save({useObjectStreams:false});
    finalContent=(await protocol.readContent(finalBytes,pdfLib)).content;
    if(finalContent!==rewritten.content) refuse('Own generated content changed during final numeric serialization.');
  }
  // A rebound marker has no attachment authority until this actual final decode.
  const shows=await decodeShows(pdfjs,finalBytes);
  await protocol.validateNativeShows(marker,finalContent,shows);
  return protocol.attachMarker(finalBytes,marker,pdfLib);
}
async function sourceForPage({handle,page,operators,pdfjs,bytes,pageNumber,loadPdfLib,signal}){
  const info=(await handle.getMetadata()).info,raw=info?.Custom?.[protocol.INFO_KEY];
  if(raw===undefined)return null;
  if(typeof raw!=='string'||raw.length>2000000||pageNumber!==1||handle.numPages!==1||typeof loadPdfLib!=='function')refuse('Malformed or unsupported native logical source descriptor.');
  let marker;try{marker=JSON.parse(raw);}catch(_){refuse('Malformed native logical source descriptor.');}
  protocol.validateMarker(marker);
  const bytesSha256=clipPlanes?await digest(new Uint8Array(bytes)):null;
  const pdfLib=await loadPdfLib(),checked=await protocol.readMarker(bytes,pdfLib);
  if(!same(marker,checked))refuse('Logical source native information/content binding differs.');
  const {content}=await protocol.readContent(bytes,pdfLib),shows=await nativeShows(pdfjs,page,operators);
  await protocol.validateNativeShows(marker,content,shows);
  if(clipPlanes&&await digest(new Uint8Array(bytes))!==bytesSha256)refuse('Authenticated input bytes changed during current source validation.');
  const token=Object.freeze({schema:'figureStudio.currentPdfLogicalTextSource.v1',contentSha256:marker.contentSha256,nativeGlyphCount:shows.length});
  let operatorSnapshot=null;if(clipPlanes){try{operatorSnapshot=clipPlanes.captureOperators(operators);}catch(error){if(error.code!=='PDF_LOGICAL_TEXT_UNSUPPORTED')throw error;if(operatorSnapshots)operatorSnapshot=await operatorSnapshots.capture(operators,{signal});}}
  sources.set(token,{marker,content,shows,observed:0,spans:new WeakSet(),svgSha256:null,handle,pageNumber,bytesSha256,page,operators,pdfjs,operatorSnapshot,currentClipAuthority:null,signal});return token;
}
async function sourceForCanonicalReplayPage({handle,page,operators,pdfjs,bytes,pageNumber,loadPdfLib,signal}){
  // Fixed module lookup is lazy so the detached current owner does not create
  // an adapter/runtime/CommonJS initialization cycle.
  const info=(await handle.getMetadata()).info,raw=info?.Custom?.FigureStudioCurrentCanonicalReplayV1;
  if(raw===undefined)return null;
  const canonical=typeof module==='object'&&module.exports?require('./pdf-dense-current-canonical-transport.js'):globalThis.FigureStudioPdfDenseCurrentCanonicalTransport;
  if(!canonical?.sourceMarker||!canonical?.validateMarker)refuse('Canonical current source transport is unavailable.');
  if(info?.Custom?.[protocol.INFO_KEY]!==undefined||typeof raw!=='string'||raw.length>2000000||pageNumber!==1||handle.numPages!==1||typeof loadPdfLib!=='function')refuse('Conflicting, malformed or unsupported canonical replay source descriptor.');
  let descriptor;try{descriptor=JSON.parse(raw);}catch(_){refuse('Malformed canonical replay source descriptor.');}
  canonical.validateMarker(descriptor);
  const bytesSha256=await digest(new Uint8Array(bytes)),pdfLib=await loadPdfLib(),checked=await canonical.readMarker(bytes,pdfLib);
  if(!same(descriptor,checked))refuse('Canonical source native information/content binding differs.');
  const marker=await canonical.sourceMarker(bytes,pdfLib),{content}=await protocol.readContent(bytes,pdfLib),shows=await nativeShows(pdfjs,page,operators);
  await protocol.validateNativeShows(marker,content,shows);
  if(await digest(new Uint8Array(bytes))!==bytesSha256)refuse('Authenticated canonical input bytes changed during source validation.');
  const token=Object.freeze({schema:'figureStudio.currentCanonicalPdfLogicalTextSource.v1',contentSha256:marker.contentSha256,nativeGlyphCount:shows.length});
  let operatorSnapshot=null;try{operatorSnapshot=clipPlanes.captureOperators(operators);}catch(error){if(error.code!=='PDF_LOGICAL_TEXT_UNSUPPORTED')throw error;operatorSnapshot=await operatorSnapshots.capture(operators,{signal});}
  sources.set(token,{marker,content,shows,observed:0,spans:new WeakSet(),svgSha256:null,handle,pageNumber,bytesSha256,page,operators,pdfjs,operatorSnapshot,currentClipAuthority:null,signal});return token;
}
async function bindCurrentClipPlanes(token,{page,operators,pdfjs,viewport}){
  const source=sources.get(token);
  if(!source||source.page!==page||source.operators!==operators||source.pdfjs!==pdfjs||source.observed!==0||source.svgSha256!==null||source.currentClipAuthority||!clipPlanes||!source.operatorSnapshot||!await sameCurrentOperators(operators,source.operatorSnapshot,source.signal))refuse('Current clip plane route requires the unchanged private authenticated native source page/operators.');
  if(!source.handle||await source.handle.getPage(source.pageNumber)!==page||typeof source.handle.getData!=='function'||await digest(await source.handle.getData())!==source.bytesSha256)refuse('Current native page/operators must belong to the actual decoded handle for the authenticated source bytes.');
  const actualOperators=await page.getOperatorList(),view=page.view,expected=page.getViewport({scale:96/72});
  if(actualOperators!==operators||!Array.isArray(view)||view.length!==4||!view.every(Number.isFinite)||view[0]!==0||view[1]!==0||!(view[2]>0&&view[3]>0)||page.rotate!==0||page.userUnit!==1||!viewport||!viewport.transform||viewport.transform.length!==6||viewport.transform.some((value,index)=>!Object.is(value,expected.transform[index]))||!Object.is(viewport.width,expected.width)||!Object.is(viewport.height,expected.height))refuse('Current clip plane route requires the genuine native unrotated unit-one pixel viewport.');
  const currentClipAuthority=operatorSnapshots?.isIssued(source.operatorSnapshot)?await clipPlanes.bindCurrentOperatorsBatched(operators,pdfjs.OPS,viewport,source.operatorSnapshot,{signal:source.signal}):clipPlanes.bindCurrentOperators(operators,pdfjs.OPS,viewport),shows=await nativeShows(pdfjs,page,operators,{currentClipAuthority});
  await protocol.validateNativeShows(source.marker,source.content,shows);
  if(!await sameCurrentOperators(operators,source.operatorSnapshot,source.signal)||source.observed!==0||source.svgSha256!==null||source.currentClipAuthority)refuse('Current authenticated clip source changed during plane proof.');
  source.shows=shows;source.currentClipAuthority=currentClipAuthority;return currentClipAuthority;
}
function observeDecodedText(token,span,recovered,font,nativeSize){
  const source=sources.get(token),show=source?.shows[source.observed];
  if(!show||!span||source.spans.has(span)||recovered.length!==1||recovered[0].unicode!==show.unicode||recovered[0].fontChar!==show.fontChar||font.name!==show.sourceFontName||nativeSize!==show.fontSize)refuse('Current decoded SVG text is not the exact authenticated native source show.');
  span.setAttribute(ATTR,String(source.observed++));source.spans.add(span);
}
function svgMatrix(element,root,matrixApi){
  const chain=[];for(let current=element;current&&current!==root;current=current.parentElement)chain.unshift(current);
  let result=[1,0,0,1,0,0];for(const current of chain)result=matrixApi.multiply(result,matrixApi.transformMatrix(current.getAttribute('transform')||''));return result;
}
function svgRectangle(element){
  if(element.localName.toLowerCase()==='rect'){
    if(Number(element.getAttribute('rx'))||Number(element.getAttribute('ry')))refuse('Rounded current SVG source clipping is unsupported.');
    const x=Number(element.getAttribute('x')||0),y=Number(element.getAttribute('y')||0),w=Number(element.getAttribute('width')),h=Number(element.getAttribute('height'));
    if(![x,y,w,h].every(Number.isFinite)||w<=0||h<=0)refuse('Malformed current SVG source rectangle clip.');return [[x,y],[x+w,y],[x+w,y+h],[x,y+h]];
  }
  if(element.localName.toLowerCase()!=='path')refuse('Unknown current SVG source clip shape.');
  const text=element.getAttribute('d')||'',pattern=/[MLHVZmlhvz]|[+-]?(?:\d*\.\d+|\d+\.?\d*)(?:e[+-]?\d+)?/gi,tokens=text.match(pattern)||[];
  if(text.replace(pattern,'').replace(/[\s,]/g,''))refuse('Current SVG clip uses unsupported curve/path commands.');
  const points=[];let cursor=[0,0],i=0;
  while(i<tokens.length){const command=tokens[i++];if(command==='Z'||command==='z'){if(i!==tokens.length)refuse('Compound SVG clipping is unsupported.');break;}const relative=command===command.toLowerCase(),upper=command.toUpperCase();if(!['M','L','H','V'].includes(upper))refuse('Malformed rectangular SVG clipping.');
    const x=Number(tokens[i++]);if(!Number.isFinite(x))refuse('Nonfinite SVG clipping operand.');let next;
    if(upper==='H')next=[relative?cursor[0]+x:x,cursor[1]];else if(upper==='V')next=[cursor[0],relative?cursor[1]+x:x];else{const y=Number(tokens[i++]);if(!Number.isFinite(y))refuse('Incomplete SVG clipping operand.');next=[relative?cursor[0]+x:x,relative?cursor[1]+y:y];}cursor=next;points.push(cursor.slice());
  }
  if(points.length===5&&same(points[0],points[4]))points.pop();if(points.length!==4||!/[zZ]\s*$/.test(text))refuse('Current SVG clip is not a closed rectangular path.');return points;
}
function decodedSvgClip(span,svg,show,matrixApi){
  const owners=[];for(let current=span;current&&current!==svg;current=current.parentElement)if(current.hasAttribute('clip-path'))owners.unshift(current);
  const elements=Array.from(svg.querySelectorAll('clipPath'));
  if(elements.length>4096)refuse('Current decoded SVG clip definition budget exceeded.');
  const definitions=new Map();for(const element of elements){const id=element.getAttribute('id');if(!id||definitions.has(id))refuse('Ambiguous current decoded SVG clip definition identity.');definitions.set(id,element);}
  const ordered=[],seen=new Set();let expansions=0;
  function expand(reference,owner,active=new Set()){
    const ref=/^url\(#([^\s)]+)\)$/.exec(reference||''),definition=definitions.get(ref?.[1]);
    if(!definition||active.has(definition)||active.size>=16||ordered.length>=16||++expansions>256)refuse('Current decoded SVG clip definition chain is missing, cyclic or exceeds its budget.');
    active.add(definition);
    // Each importer definition carries its complete decoded PDF CTM. Earlier
    // activeClipUrl references share the paint owner's page coordinate space;
    // never multiply one complete definition CTM by another definition CTM.
    if(definition.hasAttribute('clip-path'))expand(definition.getAttribute('clip-path'),owner,active);
    if(definition.children[0]?.hasAttribute('clip-path'))expand(definition.children[0].getAttribute('clip-path'),owner,active);
    if(!seen.has(definition)){seen.add(definition);ordered.push({definition,owner});}
    active.delete(definition);
  }
  for(const owner of owners)expand(owner.getAttribute('clip-path'),owner);
  if(ordered.length!==show.clipOperatorIndexes.length)refuse('Current decoded SVG clipping does not retain every native source scope exactly once.');
  const scopes=ordered.map(({owner,definition},index)=>{
    if(!definition||definition.children.length!==1||definition.hasAttribute('clipPathUnits')&&definition.getAttribute('clipPathUnits')!=='userSpaceOnUse')refuse('Unknown or compound current source SVG clip.');
    const child=definition.children[0],transform=matrixApi.multiply(svgMatrix(owner,svg,matrixApi),matrixApi.multiply(matrixApi.transformMatrix(definition.getAttribute('transform')||''),matrixApi.transformMatrix(child.getAttribute('transform')||'')));
    const points=svgRectangle(child).map(point=>[transform[0]*point[0]+transform[2]*point[1]+transform[4],transform[1]*point[0]+transform[3]*point[1]+transform[5]]);
    const result={kind:'rect',points,rule:child.getAttribute('clip-rule')||definition.getAttribute('clip-rule')||'nonzero',inverted:false,source:'decoded-pdf',sourceOperatorIndex:show.clipOperatorIndexes[index]};
    if(!same(result,show.nativeClipSources[index]))refuse('Current decoded SVG clip geometry/rule/ordered source operation differs from exact native operands.');
    return result;
  });
  return {schema:'figureStudio.decodedEffectiveClip.v1',scopes};
}
async function finishDecodedSvg(token,svgText,svg){
  const source=sources.get(token);if(!source||source.observed!==source.shows.length||source.svgSha256!==null)refuse('Current decoded SVG lost or duplicated native text show ownership.');
  const matrixApi=typeof module==='object'&&module.exports?require('./pdf-svg-materializer.js'):globalThis.FigureStudioPdfSvgMaterializer;
  if(!svg||!matrixApi)refuse('Current native decoded SVG hierarchy is unavailable.');
  const spans=Array.from(svg.querySelectorAll('tspan')).filter(span=>span.hasAttribute(ATTR));
  if(spans.length!==source.shows.length)refuse('Current SVG source scalar text membership differs.');
  try{if(source.currentClipAuthority){
    spans.forEach((span,index)=>{if(span.getAttribute(ATTR)!==String(index))refuse('Current SVG scalar text order changed.');});
    source.svgGlyphs=(await clipPlanes.matchDecodedSvgClipsBatched(source.currentClipAuthority,spans,svg,svgRectangle,{svgText,signal:source.signal})).map(effectiveClip=>({effectiveClip}));
  }else source.svgGlyphs=spans.map((span,index)=>{if(span.getAttribute(ATTR)!==String(index))refuse('Current SVG scalar text order changed.');return {effectiveClip:source.currentClipAuthority?clipPlanes.matchDecodedSvgClip(source.currentClipAuthority,span,svg,index,svgRectangle):decodedSvgClip(span,svg,source.shows[index],matrixApi)};});}
  catch(error){if(error.code!=='PDF_LOGICAL_TEXT_UNSUPPORTED')throw error;source.unsupportedGeometry=String(error.message);}
  source.svgSha256=await digest(new TextEncoder().encode(svgText));
  if((source.currentClipAuthority||operatorSnapshots?.isIssued(source.operatorSnapshot))&&new XMLSerializer().serializeToString(svg)!==svgText)refuse('Current native SVG changed during completion hashing.');
  if(source.currentClipAuthority&&!source.unsupportedGeometry){source.svg=svg;source.domSnapshot=JSON.stringify(currentSvgDom(svg));}
  return token;
}
function currentSvgDom(svg) {
  let count = 0;
  function row(element, depth = 0) {
    if (!element || depth > 48 || ++count > 20000) refuse('Current native SVG constructor DOM exceeds its budget.');
    const attrs = Object.fromEntries(Array.from(element.attributes).map(attribute => [attribute.name, attribute.value]));
    const children = Array.from(element.children || []);
    return { tag: element.localName.replace(/^.*:/, ''), attrs, text: children.length ? '' : element.textContent, children: children.map(child => row(child, depth + 1)) };
  }
  return row(svg);
}
const constructedPlaneResults = new WeakMap();
function currentConstructedPlaneMethods(root) {
  const rows = [], seen = new Set(), names = ["_renderPathCommands", "_getOffsetTransform", "_renderChars", "_renderTextFill",
    "_toSVG", "drawObject", "_drawClipPath", "needsItsOwnCache", "calcACoords", "_currentNativePlaneClip", "getObjects",
    "toObject", "calcOwnMatrix", "calcTransformMatrix"];
  const numeric = ["left", "top", "width", "height", "scaleX", "scaleY", "angle", "skewX", "skewY", "strokeWidth",
    "strokeMiterLimit", "strokeDashOffset", "opacity", "fontSize", "charSpacing", "lineHeight"];
  function visit(object) {
    if (!object || seen.has(object)) refuse("Shared current native constructor ownership.");
    seen.add(object);
    const children = Array.from(object.getObjects?.() || []);
    rows.push({ object, constructor: object.constructor, group: object.group, parent: object.parent,
      clip: object.clipPath, children, methods: names.map(name => [name, object[name]]),
      numbers: numeric.map(name => [name, object[name]]), path: object.path ? object.path.map(command => command.slice()) : null });
    children.forEach(visit); if (object.clipPath) visit(object.clipPath);
  }
  visit(root); return rows;
}
function sameConstructedPlaneMethods(rows) {
  const exact = (left, right) => Object.is(left, right) || Boolean(Array.isArray(left) && Array.isArray(right)
    && left.length === right.length && left.every((value, index) => exact(value, right[index])));
  return rows.every(row => row.object.constructor === row.constructor && row.object.group === row.group
    && row.object.parent === row.parent && row.object.clipPath === row.clip
    && row.methods.every(([name, method]) => row.object[name] === method)
    && row.numbers.every(([name, value]) => Object.is(row.object[name], value)) && exact(row.path, row.object.path || null)
    && (row.object.getObjects?.() || []).length === row.children.length
    && row.children.every((child, index) => row.object.getObjects()[index] === child));
}
function currentConstructedPlaneSnapshot(root) {
  return JSON.stringify(root.toObject(['figureType', 'name', 'figureStudioSvgElementId', 'figureStudioSvgElementTag', 'figureStudioSvgGroupPath',
    'figureStudioSvgSourceOrder', 'figureStudioSvgTextMeta', 'figureStudioSvgGroupMeta', 'figureStudioPdfLogicalRun']));
}
function isConstructedCurrentPlaneObjects(result) {
  const receipt = result && typeof result === 'object' && constructedPlaneResults.get(result);
  if (!receipt || receipt.root !== result.root || receipt.report !== result.report || result.status !== 'constructed-current-native-planes'
      || result.runCount !== receipt.runCount || result.nativeGlyphCount !== receipt.nativeGlyphCount) return false;
  try { return sameConstructedPlaneMethods(receipt.methods) && currentConstructedPlaneSnapshot(result.root) === receipt.snapshot; } catch (_) { return false; }
}
async function currentNativeRenderer(token, { Base, page, operators, pdfjs, viewport }) {
  const source = sources.get(token);
  if (!source || source.page !== page || source.operators !== operators || source.pdfjs !== pdfjs
      || !source.currentClipAuthority || source.observed !== 0 || source.svgSha256 !== null || !localSvg
      || !await sameCurrentOperators(operators, source.operatorSnapshot,source.signal)) refuse('Current native SVG rendering requires the privately bound unchanged source page.');
  const options={ authority: source.currentClipAuthority, operators, pdfjs, viewport, signal: source.signal };
  return operatorSnapshots?.isIssued(source.operatorSnapshot)?localSvg.createGraphicsClassBatched(Base,options,source.operatorSnapshot):localSvg.createGraphicsClass(Base,options);
}
async function constructCurrentPlaneObjects({ token, svgText, svg, fabric, materializer }) {
  const source = sources.get(token);
  if (!source || !source.currentClipAuthority || source.svg !== svg || source.constructed || source.unsupportedGeometry
      || !source.svgSha256 || source.svgSha256 !== await digest(new TextEncoder().encode(svgText)) || !nativePlanes
      || !await sameCurrentOperators(source.operators, source.operatorSnapshot,source.signal)) refuse('Current native plane construction requires its completed privately authenticated SVG.');
  const dom = currentSvgDom(svg);
  if (JSON.stringify(dom) !== source.domSnapshot) refuse('Current decoded SVG changed after native clip validation.');
  const spans = Array.from(svg.querySelectorAll('tspan')).filter(span => source.spans.has(span));
  if (spans.length !== source.shows.length) refuse('Current native construction lost genuine scalar membership.');
  const glyphs = spans.map((span, index) => {
    if (span.getAttribute(ATTR) !== String(index) || span.parentElement?.localName.toLowerCase() !== 'text') refuse('Current native scalar order or declaring text plane changed.');
    const show = source.shows[index], attrs = {};
    for (const element of [span.parentElement, span]) for (const attribute of Array.from(element.attributes)) attrs[attribute.name] = attribute.value;
    const chain = [];
    for (let element = span; element && element !== svg; element = element.parentElement) chain.unshift({ tag: element.localName.replace(/^.*:/, ''), id: element.id || '', transform: element.getAttribute('transform') || '', clip: element.getAttribute('clip-path') || '' });
    const matrix = svgMatrix(span, svg, materializer), x = Number(attrs.x), y = Number(attrs.y), fontSize = parseFloat(attrs['font-size']);
    if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(fontSize) || fontSize <= 0 || !attrs['font-family']) refuse('Current native scalar coordinates/font declaration are unavailable.');
    const baseline = [matrix[0] * x + matrix[2] * y + matrix[4], matrix[1] * x + matrix[3] * y + matrix[5]];
    const packet = { ...show, nativeFontSize: show.fontSize, nativeFontWeight: show.fontWeight, nativeFontStyle: show.fontStyle,
      fontFamily: attrs['font-family'], fontSize, fontWeight: attrs['font-weight'] || 'normal', fontStyle: attrs['font-style'] || 'normal',
      matrix, baseline, fill: span.parentElement.getAttribute('fill') || 'black', stroke: null, opacity: 1, compositingScope: 'source-over',
      effectiveClip: source.svgGlyphs[index].effectiveClip };
    return { index, show, attrs, chain, world: baseline, packet };
  });
  const validated = await protocol.validatePackets(source.marker, source.content, glyphs.map(glyph => glyph.packet));
  const input = { schema: 'figureStudio.currentNativePdfPlaneHandoffInput.v1', dom,
    runs: validated.map(run => ({ run: source.marker.runs.find(row => row.id === run.id), shows: run.members.map(member => glyphs[member.sourceTextShowIndex]) })) };
  if (!await sameCurrentOperators(source.operators, source.operatorSnapshot,source.signal) || source.domSnapshot !== JSON.stringify(currentSvgDom(svg))) refuse('Current native construction inputs changed during validation.');
  const result = await nativePlanes.construct(fabric, materializer, input,{signal:source.signal});
  if (!await sameCurrentOperators(source.operators, source.operatorSnapshot,source.signal) || source.domSnapshot !== JSON.stringify(currentSvgDom(svg))) refuse('Current native construction inputs changed during native object creation.');
  source.constructed = true;
  const report = Object.freeze({ status: 'complete', unsupported: [], runCount: validated.length, nativeGlyphCount: glyphs.length,
    objectCount: result.paints.length, pathCount: result.paints.filter(row => row.kind === 'path' || row.kind === 'rect').length });
  const answer = { ...result, status: 'constructed-current-native-planes', runCount: validated.length, nativeGlyphCount: glyphs.length, report };
  constructedPlaneResults.set(answer, { root: answer.root, report, runCount: answer.runCount, nativeGlyphCount: answer.nativeGlyphCount,
    snapshot: currentConstructedPlaneSnapshot(answer.root), methods: currentConstructedPlaneMethods(answer.root) });
  return answer;
}

function rectanglePoints(clip,world,fabric){
  if(clip.inverted||clip.absolutePositioned||clip.getObjects||clip.stroke&&clip.strokeWidth||clip.opacity!==1)refuse('Unsupported current native rectangular clip representation.');
  let points;
  if(clip.constructor?.type==='Rect'){if(clip.rx||clip.ry)refuse('Rounded source clip is unsupported.');points=[[-clip.width/2,-clip.height/2],[clip.width/2,-clip.height/2],[clip.width/2,clip.height/2],[-clip.width/2,clip.height/2]];}
  else if(clip.path){
    const rows=clip.path;if(rows.at(-1)?.[0]!=='Z'||rows[0]?.[0]!=='M'||rows.slice(1,-1).some(row=>row[0]!=='L'))refuse('Current decoded clip is not a supported rectangular path.');
    points=rows.slice(0,-1).map(row=>[row[1]-clip.pathOffset.x,row[2]-clip.pathOffset.y]);if(points.length===5&&same(points[0],points[4]))points.pop();if(points.length!==4)refuse('Current decoded rectangular clip vertex count differs.');
  }else refuse('Unknown current native clip shape.');
  return points.map(point=>{const result=fabric.util.transformPoint({x:point[0],y:point[1]},world);return [result.x,result.y];});
}
function currentClip(object,show,fabric){
  const scopes=[];let clip=object.clipPath,world=object.calcTransformMatrix();
  while(clip){world=fabric.util.multiplyTransformMatrices(world,clip.calcOwnMatrix());scopes.push({kind:'rect',points:rectanglePoints(clip,world,fabric),rule:clip.fillRule||'nonzero',inverted:false,source:'decoded-pdf',sourceOperatorIndex:show.clipOperatorIndexes[scopes.length]});clip=clip.clipPath;if(scopes.length>16)refuse('Current decoded clip budget exceeded.');}
  if(scopes.length!==show.clipOperatorIndexes.length)refuse('Current SVG effective clipping differs from decoded native clip scopes.');
  return {schema:'figureStudio.decodedEffectiveClip.v1',scopes};
}
function commonPath(objects){const result=(objects[0].figureStudioSvgGroupPath||[]).slice();for(const object of objects.slice(1)){const path=object.figureStudioSvgGroupPath||[];let i=0;while(i<result.length&&result[i]===path[i])i++;result.length=i;}return result;}
async function coalesceCurrentObjects(objects,{token,svgText,fabric,TextClass,descriptors=[]}){
  if(!token)return {objects,status:'untagged',runCount:null};
  const source=sources.get(token);if(!source||!source.svgSha256||source.svgSha256!==await digest(new TextEncoder().encode(svgText)))refuse('Current SVG graph lacks the fresh authenticated native source binding.');
  if(source.unsupportedGeometry)refuse(source.unsupportedGeometry);
  const byIndex=new Map(),byGroup=new Map(descriptors.map(row=>[row.key,row]));
  objects.forEach((object,index)=>{if(object.figureStudioPdfLogicalGlyphIndex===undefined)return;const ordinal=object.figureStudioPdfLogicalGlyphIndex;if(!Number.isSafeInteger(ordinal)||byIndex.has(ordinal))refuse('Ambiguous current decoded glyph object identity.');byIndex.set(ordinal,{object,index});});
  if(byIndex.size!==source.shows.length)refuse('Current decoded glyph object membership is incomplete.');
  const packets=source.shows.map(show=>{
    const object=byIndex.get(show.sourceTextShowIndex)?.object,layout=object?._sourceLayout?.(),glyph=layout?.glyphs?.[0];
    if(!object||object.constructor!==TextClass||!layout||layout.glyphs.length!==1||object.text!==show.unicode||glyph.unicode!==show.unicode||glyph.fontChar!==show.fontChar&& !/^\s+$/u.test(show.unicode)||layout.sourceEmbeddedProgram!==show.sourceEmbeddedProgram)refuse('Current source text/font/display glyph differs from its exact native show.');
    for(const key of object.figureStudioSvgGroupPath||[]){const group=byGroup.get(key);if(!group||group.opacity!==1)refuse('Unknown or non-unit current decoded ancestor compositing.');}
    const own=object.calcTransformMatrix(),anchor=object._pdfAnchorPoint(),baseline=fabric.util.transformPoint({x:anchor.x+glyph.x,y:anchor.y+glyph.y},own);
    if(Boolean(object.clipPath)!==Boolean(source.svgGlyphs[show.sourceTextShowIndex].effectiveClip.scopes.length))refuse('Current native object lost its decoded source clipping.');
    return {...show,nativeFontSize:show.fontSize,nativeFontWeight:show.fontWeight,nativeFontStyle:show.fontStyle,fontFamily:object.fontFamily,fontSize:object.fontSize,fontWeight:object.fontWeight,fontStyle:object.fontStyle,fontChar:glyph.fontChar,matrix:own.slice(),baseline:[baseline.x,baseline.y],fill:object.fill,stroke:object.stroke,opacity:object.opacity,compositingScope:object.globalCompositeOperation,effectiveClip:source.svgGlyphs[show.sourceTextShowIndex].effectiveClip};
  });
  const runs=await protocol.validatePackets(source.marker,source.content,packets),replacements=new Map(),removed=new Set();
  // Read and construct every replacement before changing the original object
  // list. No native Group remove/refit or original source pose replay occurs.
  for(const run of runs){
    const members=run.members.map(packet=>byIndex.get(packet.sourceTextShowIndex));
    if(members.some((member,index)=>index&&member.index!==members[index-1].index+1))refuse('Current decoded non-text paint interrupts a logical run.');
    const model=protocol.combineNativeRun(run),joined=protocol.createNativeText(model,fabric,TextClass),first=members[0].object;
    const ancestorPath=commonPath(members.map(member=>member.object));
    joined.set({figureType:first.figureType,name:first.name,figureStudioSvgGroupPath:ancestorPath,figureStudioSvgSourceOrder:first.figureStudioSvgSourceOrder,figureStudioSvgTextMeta:{schema:'figureStudio.svgPositionedText.v2',sourceText:run.unicode,sourceGlyphCount:run.members.length},figureStudioPdfLogicalRun:{schema:protocol.SCHEMA,runId:run.id,nativeGlyphCount:run.members.length,originalPdfWriterAuthority:false}});
    joined.__pdfSvgClipRef=first.__pdfSvgClipRef;joined.setCoords();replacements.set(first,joined);members.slice(1).forEach(member=>removed.add(member.object));
  }
  return {objects:objects.filter(object=>!removed.has(object)).map(object=>replacements.get(object)||object),status:'coalesced-current-native-source',runCount:runs.length,nativeGlyphCount:packets.length};
}
return {ATTR,ownExportObserver,nativeShows,decodeShows,completeOwnExport,sourceForPage,sourceForCanonicalReplayPage,bindCurrentClipPlanes,currentNativeRenderer,constructCurrentPlaneObjects,isConstructedCurrentPlaneObjects,observeDecodedText,svgMatrix,svgRectangle,decodedSvgClip,finishDecodedSvg,rectanglePoints,currentClip,coalesceCurrentObjects};
});
