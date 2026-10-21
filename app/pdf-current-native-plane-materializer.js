(function(root,factory){const protocol=typeof module==='object'&&module.exports?require('./pdf-logical-text-protocol.js'):root.FigureStudioPdfLogicalTextProtocol;const precision=typeof module==='object'&&module.exports?require('./pdf-scene-number-precision.js'):root.FigureStudioPdfSceneNumberPrecision;const materializer=typeof module==='object'&&module.exports?require('./pdf-svg-materializer.js'):root.FigureStudioPdfSvgMaterializer;const api=factory(protocol,precision,materializer);if(typeof module==='object'&&module.exports)module.exports=api;else root.FigureStudioPdfCurrentNativePlaneMaterializer=api;})(typeof globalThis==='object'?globalThis:this,function(protocol,numberPrecision,materializer){
'use strict';
const {multiply,transformMatrix:parseTransform}=materializer;
const bundledFabric=typeof module==='object'&&module.exports?require('../vendor/fabric/index.min.js'):globalThis.fabric;
const NativeGroup=bundledFabric?.Group,nativeFromObject=NativeGroup?.fromObject,nativeGroupInit=NativeGroup?.prototype.groupInit,nativeEnterGroup=NativeGroup?.prototype.enterGroup;
const noopLayouts=new WeakMap();
async function nativeNoopLayout(fabric,Group,Manager,Linear){
 if(fabric.Group!==NativeGroup||Group.fromObject!==nativeFromObject||NativeGroup.prototype.groupInit!==nativeGroupInit||NativeGroup.prototype.enterGroup!==nativeEnterGroup||Object.getPrototypeOf(Group.prototype).constructor!==materializer.registerGroupClass(fabric))refuse('Current native construction requires its audited bundled group initialization.');
 if(!noopLayouts.has(Group)){
  const pending=(async()=>{let Noop;
   class NativeInitializationProbe extends Group {constructor(objects,options){super(objects,options);Noop=options.layoutManager?.constructor;}}
   const probe=await Reflect.apply(nativeFromObject,NativeInitializationProbe,[{type:Group.type,objects:[],layoutManager:{type:Manager.type,strategy:Linear.type}}]);
   if(typeof Noop!=='function'||!(Noop.prototype instanceof fabric.LayoutManager)||probe.layoutManager.constructor!==Manager||probe.layoutManager.strategy.constructor!==Linear)refuse('Bundled native group initialization changed.');
   probe.dispose();return {Class:Noop,performLayout:Noop.prototype.performLayout};
  })();noopLayouts.set(Group,pending);
 }
 const record=await noopLayouts.get(Group);
 if(record.Class.prototype.performLayout!==record.performLayout)refuse('Bundled native no-layout initialization changed.');
 return record.Class;
}
const identity=[1,0,0,1,0,0],META=['figureType','name','figureStudioSvgElementId','figureStudioSvgElementTag','figureStudioSvgGroupPath','figureStudioSvgSourceOrder','figureStudioSvgTextMeta','figureStudioSvgGroupMeta','figureStudioPdfLogicalRun'];
const same=(a,b)=>Object.is(a,b)||Boolean(a&&b&&typeof a==='object'&&typeof b==='object'&&Object.keys(a).length===Object.keys(b).length&&Object.keys(a).every((k,i)=>k===Object.keys(b)[i]&&same(a[k],b[k])));
function refuse(reason){const e=new Error(reason);e.code='SVG_LOCAL_FULL_UNSUPPORTED';throw e;}
// Same singular-value scale calculation and Float32 threshold as the bundled
// PDF.js Canvas getImageSmoothingEnabled for an absent interpolation hint.
function defaultImageSmoothing(context){
 if(typeof context?.getTransform!=='function')return null;
 const t=context.getTransform(),m=[t.a,t.b,t.c,t.d];if(!m.every(Number.isFinite))return null;
 const transpose=[m[0],m[2],m[1],m[3]],a=m[0]*transpose[0]+m[1]*transpose[2],b=m[0]*transpose[1]+m[1]*transpose[3],c=m[2]*transpose[0]+m[3]*transpose[2],d=m[2]*transpose[1]+m[3]*transpose[3];
 const first=(a+d)/2,second=Math.sqrt((a+d)**2-4*(a*d-c*b))/2,sx=first+second||1,sy=first-second||1;
 const actualScale=Math.fround((globalThis.devicePixelRatio||1)*(96/72));
 return Math.fround(Math.sqrt(sx))<=actualScale||Math.fround(Math.sqrt(sy))<=actualScale;
}
const imageClasses=new WeakMap();
function registerImageClass(fabric){
 if(imageClasses.has(fabric))return imageClasses.get(fabric);
 const Image=fabric.FabricImage||fabric.Image;
 if(typeof Image!=='function')refuse('The native editable image class is unavailable.');
 class PdfCurrentPlaneImage extends Image {
  static type='PdfCurrentPlaneImage';
  get type(){return 'image';}
  _renderFill(context){
   if(this.pdfNativeImageInterpolationPolicy!=='native-scale-default-v1'||this.imageSmoothing!==true
      ||this.filters?.length||this.resizeFilter||this._filterScalingX!==1||this._filterScalingY!==1||this.cropX!==0||this.cropY!==0)return super._renderFill(context);
   const smooth=defaultImageSmoothing(context);if(smooth===null)return super._renderFill(context);
   const initial=context.imageSmoothingEnabled;context.imageSmoothingEnabled=smooth;
   try{return super._renderFill(context);}finally{context.imageSmoothingEnabled=initial;}
  }
  toObject(properties=[]){return super.toObject([...properties,'imageSmoothing','pdfNativeImageInterpolationPolicy',...META]);}
  _toSVG(){
   const markup=super._toSVG();
   if(typeof this.imageSmoothing!=='boolean'||this.pdfNativeImageInterpolationPolicy==='native-scale-default-v1')return markup;
   return markup.map(part=>part.replace('<image ',`<image data-pdf-image-interpolate="${this.imageSmoothing}" `));
  }
 }
 fabric.classRegistry.setClass(PdfCurrentPlaneImage);imageClasses.set(fabric,PdfCurrentPlaneImage);return PdfCurrentPlaneImage;
}
function retainImageInterpolation(fabric,object,value){
 const Image=fabric.FabricImage||fabric.Image;
 if(typeof value!=='boolean'||object?.constructor!==Image)refuse('The editable image cannot preserve its explicit interpolation setting.');
 Object.setPrototypeOf(object,registerImageClass(fabric).prototype);
 object.set('imageSmoothing',value);return object;
}
// The inherited general transform parser multiplies by identity, which can
// normalize signed zero. Refuse raw signed zero before inherited
// parsing in every current transform family, including the old axis cases.
function currentPlaneTransform(value){
 for(const match of String(value).matchAll(/(matrix|scale|translate)\(([^)]*)\)/g)){
  const values=match[2].trim().split(/[ ,\s]+/).map(Number);
  if(values.some(value=>Object.is(value,-0)))refuse('Signed-zero current transform declarations require exact parsing support.');
 }
 return parseTransform(value);
}
// Native two-skew poses can retain a literal affine plane that native QR
// decomposition cannot reconstruct exactly. These are candidate parameters,
// never a tolerance: both native composition and the constructed group must
// reproduce all six original operands with Object.is equality.
function exactAffinePose(m,base){
 const determinant=m[0]*m[3]-m[1]*m[2];
 if(!m.every(value=>Math.abs(value)<=1e8)||!Number.isFinite(determinant)||determinant===0)return null;
 const bits=new DataView(new ArrayBuffer(8));
 function adjacent(value,direction){
  if(!Number.isFinite(value))return value;
  if(value===0)return direction>0?Number.MIN_VALUE:-Number.MIN_VALUE;
  bits.setFloat64(0,value);const previous=bits.getBigUint64(0);
  bits.setBigUint64(0,previous+((value>0)===(direction>0)?1n:-1n));return bits.getFloat64(0);
 }
 function neighbors(value){const values=[value];let lower=value,upper=value;for(let i=0;i<8;i++){lower=adjacent(lower,-1);upper=adjacent(upper,1);values.push(lower,upper);}return values;}
 const [ma,mb,mc,md]=m;
 for(const angle of [0,90,180,270]){
  const [a,b,c,d]=angle===0?[ma,mb,mc,md]:angle===90?[mb,-ma,md,-mc]:angle===180?[-ma,-mb,-mc,-md]:[-mb,ma,-md,mc];
  if(d===0)continue;
  for(const skewY of neighbors(Math.atan(b/d)*180/Math.PI)){
   const y=Math.tan(skewY*Math.PI/180);if(d*y!==b)continue;
   for(const sx of neighbors(a-c*y)){
    if(!Number.isFinite(sx)||sx===0||Math.abs(sx)>1e8)continue;
    for(const skewX of neighbors(Math.atan(c/sx)*180/Math.PI)){
     if(sx*Math.tan(skewX*Math.PI/180)!==c)continue;
     const candidate={...base,angle,scaleX:Math.abs(sx),scaleY:Math.abs(d),flipX:sx<0,flipY:d<0,skewX,skewY};
     const actual=bundledFabric.util.composeMatrix({...candidate,translateX:m[4],translateY:m[5]});
     if(same(actual,m))return candidate;
    }
   }
  }
 }
 return null;
}
function exactObliquePose(m,base){
 const determinant=m[0]*m[3]-m[1]*m[2];
 if(!m.every(value=>Number.isFinite(value)&&Math.abs(value)<=1e8)||!Number.isFinite(determinant)||determinant===0)return null;
 const bits=new DataView(new ArrayBuffer(8));let work=0;
 function spend(){return ++work<=65536;}
 function adjacent(value,direction){if(value===0)return direction>0?Number.MIN_VALUE:-Number.MIN_VALUE;bits.setFloat64(0,value);bits.setBigUint64(0,bits.getBigUint64(0)+((value>0)===(direction>0)?1n:-1n));return bits.getFloat64(0);}
 function neighbors(value,radius=8){if(!Number.isFinite(value))return [];const values=[value];let lower=value,upper=value;for(let i=0;i<radius;i++)values.push(lower=adjacent(lower,-1),upper=adjacent(upper,1));return values;}
 for(const seed of [45,135,225,315])for(const angle of neighbors(seed,4)){
  if(!spend())return null;
  const rotation=bundledFabric.util.composeMatrix({angle}),local=bundledFabric.util.multiplyTransformMatrices(bundledFabric.util.invertTransform(rotation),m);
  for(const sy of neighbors(local[3])){
   if(!spend())return null;if(sy===0||Math.abs(sy)>1e8)continue;
   for(const c of neighbors(local[2])){
    if(!spend())return null;
    if(rotation[0]*c+rotation[2]*sy!==m[2]||rotation[1]*c+rotation[3]*sy!==m[3])continue;
    for(const skewY of neighbors(Math.atan(local[1]/sy)*180/Math.PI)){
     if(!spend())return null;const y=Math.tan(skewY*Math.PI/180),b=sy*y;
     for(const sx of neighbors(local[0]-c*y)){
      if(!spend())return null;if(sx===0||Math.abs(sx)>1e8)continue;
      const a=sx+c*y;if(rotation[0]*a+rotation[2]*b!==m[0]||rotation[1]*a+rotation[3]*b!==m[1])continue;
      for(const skewX of neighbors(Math.atan(c/sx)*180/Math.PI)){
       if(!spend())return null;
       const candidate={...base,angle,scaleX:Math.abs(sx),scaleY:Math.abs(sy),flipX:sx<0,flipY:sy<0,skewX,skewY};
       const actual=bundledFabric.util.composeMatrix({...candidate,translateX:m[4],translateY:m[5]});
       if(actual.every((value,index)=>Object.is(value,m[index])))return candidate;
      }
     }
    }
   }
  }
 }
 return null;
}
function pose(m){
 if(m.length!==6||!m.every(Number.isFinite))refuse('Invalid current literal affine plane.');
 const base={originX:'center',originY:'center',left:m[4],top:m[5],skewX:0,skewY:0};
 if(m[1]===0&&m[2]===0&&m[0]!==0&&m[3]!==0)return {...base,scaleX:Math.abs(m[0]),scaleY:Math.abs(m[3]),flipX:m[0]<0,flipY:m[3]<0,angle:0};
 if(m[0]===0&&m[3]===0&&m[1]!==0&&m[2]!==0){const candidate={...base,scaleX:Math.abs(m[1]),scaleY:Math.abs(m[2]),flipX:false,flipY:m[1]>0?m[2]>0:m[2]<0,angle:m[1]>0?90:270};if(same(bundledFabric.util.composeMatrix({...candidate,translateX:m[4],translateY:m[5]}),m))return candidate;}
 const exact=exactAffinePose(m,base)||exactObliquePose(m,base);if(exact)return exact;
 refuse('No exact bounded native pose represents this current affine plane.');
}
const PAINT=['fill','stroke','fill-opacity','stroke-opacity','stroke-width','stroke-linecap','stroke-linejoin','stroke-miterlimit','stroke-dasharray','stroke-dashoffset','fill-rule','opacity'];
const TEXT=['font-family','font-size','font-weight','font-style','text-anchor','text-decoration-thickness','white-space'];
function styles(attrs,inherited={}){
 const values={...inherited};for(const [k,v]of Object.entries(attrs))if([...PAINT,...TEXT].includes(k))values[k]=v;
 for(const d of (attrs.style||'').split(';')){if(!d.trim())continue;const p=d.indexOf(':');if(p<0)refuse('Invalid inline style.');const k=d.slice(0,p).trim(),v=d.slice(p+1).trim();if(![...PAINT,...TEXT].includes(k))refuse('Unsupported current style '+k);values[k]=v;}
 const numeric=(k,f)=>{if(values[k]===undefined)return f;if(!/^[-+]?\d*\.?\d+(?:e[-+]?\d+)?(?:px)?$/i.test(values[k]))refuse('Unsupported numeric style '+k);const n=Number(values[k].replace(/px$/i,''));if(!Number.isFinite(n))refuse('Nonfinite style '+k);return n;};
 for(const k of ['fill','stroke'])if(values[k]?.includes('url(')||values[k]!==undefined&&!/^(?:none|#[0-9a-f]{3}(?:[0-9a-f]{3})?|rgb\(\s*\d+(?:\.\d+)?\s*,\s*\d+(?:\.\d+)?\s*,\s*\d+(?:\.\d+)?\s*\)|black|white)$/i.test(values[k]))refuse('Unsupported current solid paint.');if(numeric('opacity',1)!==1)refuse('Independent opacity is unsupported.');
 if(values['stroke-linecap']&&!['butt','round','square'].includes(values['stroke-linecap'])||values['stroke-linejoin']&&!['miter','round','bevel'].includes(values['stroke-linejoin'])||values['fill-rule']&&!['nonzero','evenodd'].includes(values['fill-rule'])||values['text-anchor']&&!['start','middle','end'].includes(values['text-anchor']))refuse('Unknown current cap, join, fill rule or text anchor.');
 if(numeric('stroke-width',1)<0||numeric('stroke-miterlimit',4)<1||numeric('font-size',10)<=0)refuse('Invalid current width, miter limit or text size.');
 if(values['stroke-dasharray']&&values['stroke-dasharray']!=='none'){if(!/^\s*[-+]?\d*\.?\d+(?:e[-+]?\d+)?(?:[ ,]+[-+]?\d*\.?\d+(?:e[-+]?\d+)?)*\s*$/i.test(values['stroke-dasharray']))refuse('Malformed current dash array.');const dash=values['stroke-dasharray'].trim().split(/[ ,]+/).map(Number);if(dash.some(x=>!Number.isFinite(x)||x<0)||!dash.some(x=>x>0))refuse('Invalid current dash array.');}
 if(values['text-decoration-thickness']&&!/^(?:0|\d+(?:\.\d+)?%)$/.test(values['text-decoration-thickness'])||values['white-space']&&!['pre','normal'].includes(values['white-space']))refuse('Unsupported current decoration or whitespace.');
 const fill=values.fill==='none'?null:values.fill||'black',stroke=!values.stroke||values.stroke==='none'?null:values.stroke,fillAlpha=numeric('fill-opacity',1),strokeAlpha=numeric('stroke-opacity',1);
 if([fillAlpha,strokeAlpha].some(alpha=>alpha<0||alpha>1))refuse('Invalid current fill or stroke opacity.');
 if(fill&&stroke&&numeric('stroke-width',1)!==0&&fillAlpha!==strokeAlpha)refuse('Independent fill and stroke opacity requires the existing parser.');
 const opacity=fill?fillAlpha:stroke?strokeAlpha:1;
 return {values,options:{fill,stroke,strokeWidth:numeric('stroke-width',1),strokeLineCap:values['stroke-linecap']||'butt',strokeLineJoin:values['stroke-linejoin']||'miter',strokeMiterLimit:numeric('stroke-miterlimit',4),strokeDashArray:values['stroke-dasharray']&&values['stroke-dasharray']!=='none'?values['stroke-dasharray'].split(/[ ,]+/).map(Number):null,strokeDashOffset:numeric('stroke-dashoffset',0),fillRule:values['fill-rule']||'nonzero',opacity,objectCaching:false},numeric};
}
function exactRaw(object,properties=META){const raw=object.toObject(properties);for(const k of ['left','top','width','height','scaleX','scaleY','angle','skewX','skewY','strokeWidth','strokeMiterLimit','strokeDashOffset','opacity','fontSize','charSpacing','lineHeight'])if(Number.isFinite(object[k]))raw[k]=object[k];if(object.path)raw.path=object.path.map(c=>c.slice());return raw;}
const assert={ok:(condition,message)=>{if(!condition)refuse(message);}},parse=currentPlaneTransform, I=identity,point=(m,p)=>[m[0]*p[0]+m[2]*p[1]+m[4],m[1]*p[0]+m[3]*p[1]+m[5]];
function transformChain(glyph){return glyph.chain.filter(c=>c.transform).map(c=>parse(c.transform));}
function declaration(glyph){return {fontFamily:glyph.attrs['font-family'],fontSize:parseFloat(glyph.attrs['font-size']),fontWeight:glyph.attrs['font-weight']||'normal',fontStyle:glyph.attrs['font-style']||'normal'};}
function modelFor(run,basePaint){
 const first=run.shows[0],firstChain=transformChain(first),parentPlanes=firstChain.slice(0,-1),frame=firstChain.at(-1),det=frame[0]*frame[3]-frame[1]*frame[2],inv=[frame[3]/det,-frame[1]/det,-frame[2]/det,frame[0]/det],glyphs=[],styles={},fontSources={},declarations=[];let cursor=0;
 for(const current of run.shows){const chain=transformChain(current),m=chain.at(-1);assert.ok(same(chain.slice(0,-1),parentPlanes),'Common current literal parent CM chain');assert.ok(same(m.slice(0,4),frame.slice(0,4)),'Common current literal text linear');assert.ok(same(current.chain.filter(c=>c.clip).map(c=>c.clip),first.chain.filter(c=>c.clip).map(c=>c.clip)),'Common current literal clip declarations');const baseline=point(m,[Number(current.attrs.x),Number(current.attrs.y)]),origin=point(frame,[Number(first.attrs.x),Number(first.attrs.y)]),dx=baseline[0]-origin[0],dy=baseline[1]-origin[1],decl=declaration(current),paint=stylesForGlyph(current.attrs,basePaint),key=protocol.fontSourceKey(decl),font=fontSources[key]||={fontFamily:decl.fontFamily,fontWeight:decl.fontWeight,fontStyle:decl.fontStyle,sourceFontName:current.show.sourceFontName,sourceEmbeddedProgram:current.show.sourceEmbeddedProgram,programSha256:current.show.programSha256||null,map:{},unicodeAdvances:{}};font.map[current.show.unicode]=current.show.fontChar;if(/^\s+$/u.test(current.show.unicode))font.unicodeAdvances[current.show.unicode]=current.show.sourceAdvance;styles[cursor]={...decl,fill:paint.fill,stroke:null,strokeWidth:0};declarations.push({...decl});glyphs.push({unicode:current.show.unicode,fontChar:current.show.fontChar,charIndex:cursor,charCount:[...current.show.unicode].length,x:inv[0]*dx+inv[2]*dy,y:inv[1]*dx+inv[3]*dy,sourceFontFamily:decl.fontFamily,sourceFontKey:key});cursor+=[...current.show.unicode].length;}
 const base=declaration(first),options={text:run.run.unicode,...base,styles:{0:styles},fill:'#000000',stroke:null,strokeWidth:0,opacity:1,charSpacing:0,textAlign:'left',lineHeight:1.16};
 const source={schema:protocol.SOURCE_SCHEMA,text:run.run.unicode,anchor:'start',...base,glyphs,map:{},fontSources,fallbackFont:'Arial',logicalSourceMembership:{schema:protocol.SCHEMA,runId:run.run.id,nativeGlyphCount:glyphs.length,originalPdfWriterAuthority:false},capture:{styles:structuredClone(options.styles),baseLayout:[0,'left',1.16],declarations}};
 source.currentNativeGlyphPlanes={schema:'figureStudio.currentNativeGlyphPlanes.v1',entries:run.shows.map(glyph=>({matrices:[...glyph.chain.at(-2).transform.matchAll(/(matrix|scale|translate)\(([^)]*)\)/g)].map(match=>parse(match[0])),x:glyph.attrs.x,y:glyph.attrs.y,charIndex:glyph.index-run.run.firstGlyph,charCount:1,sourceFontKey:protocol.fontSourceKey(declaration(glyph))}))};
 return {options,source,frame:I,parentPlanes};
}
function stylesForGlyph(attrs,basePaint){const paint=styles(attrs,basePaint.values).options;if(paint.opacity!==1||paint.stroke&&paint.strokeWidth)refuse('Current native glyph opacity or stroke requires independent paint qualification.');return paint;}


// The runtime binder must supply a fresh privately authenticated current DOM and
// validated native emission rows. This bounded constructor itself never promotes
// document markers, retained JSON, IDs or original source records to authority.
async function constructInternal(fabric,materializer,input,{signal,yieldControl,now=()=>typeof performance==='object'?performance.now():Date.now()}={},nativeTextModel=null){
 const cancelled=()=>{if(signal?.aborted){const error=new Error('Current native plane construction was cancelled.');error.name='AbortError';throw error;}};cancelled();
 const yieldUi=yieldControl||(()=>typeof MessageChannel==='function'?new Promise(resolve=>{const channel=new MessageChannel();channel.port1.onmessage=()=>{channel.port1.close();channel.port2.close();resolve();};channel.port2.postMessage(null);}):new Promise(resolve=>setTimeout(resolve,0)));
 let sliceStarted=now();
 async function checkpoint(){cancelled();if(now()-sliceStarted>=8){await yieldUi();cancelled();sliceStarted=now();}}
 const defs=new Map(),ids=new Set(),paints=[],groupRows=[],clipRows=[],ownedObjects=new WeakSet();let count=0;
 function gather(n){if(++count>20000)refuse('Current decoded DOM budget exceeded.');const id=n.attrs?.id;if(id){if(ids.has(id))refuse('Current global ID alias.');ids.add(id);}if(n.tag.toLowerCase()==='clippath')defs.set(id,n);for(const c of n.children||[])gather(c);}gather(input.dom);
 const TextClass=materializer.registerTextClass(fabric),PathClass=materializer.registerCurrentPlanePathClass(fabric),Manager=materializer.registerAuthoringLayoutManager(fabric),Group=materializer.registerCurrentPlaneGroupClass(fabric),Linear=fabric.classRegistry.getClass('PdfLinearFitContentLayout'),precision=numberPrecision.createInstaller({fabric,additionalSerializers:[TextClass.prototype.toObject]});
 const runByFirst=new Map(input.runs.map(row=>[row.run.firstGlyph,row])),ownedGlyphs=new Set(input.runs.flatMap(row=>row.shows.map(glyph=>glyph.index)));
 const logicalIndex=n=>{const key=Object.keys(n.attrs).find(k=>k.includes('logical')&&k.includes('glyph'));return key?Number(n.attrs[key]):NaN;};
 function transform(n){return n.attrs.transform?[...n.attrs.transform.matchAll(/(matrix|scale|translate)\(([^)]*)\)/g)].map(m=>currentPlaneTransform(m[0])):[];}
 function walk(n,parents=[],clips=[],inherited={}){
  if(['defs','style','metadata','desc','clippath'].includes(n.tag.toLowerCase()))return;
  if(!['svg','g','path','rect','text','image'].includes(n.tag))refuse('Unsupported current paint '+n.tag);
  const own=transform(n),chain=[...parents,...own],paint=styles(n.attrs,inherited),scopes=n.attrs['clip-path']?[...clips,{reference:n.attrs['clip-path'],owner:chain}]:clips;
  if(n.tag==='text'){if(paint.options.opacity!==1)refuse('Current native text opacity requires independent glyph-paint qualification.');if(n.children.length!==1||n.children[0].tag!=='tspan')refuse('Current text must retain one authentic scalar show.');if(nativeTextModel){paints.push({kind:'text',node:n,nativeTextModel,planes:parents,clips:scopes,paint});return;}const ordinal=logicalIndex(n.children[0]);if(!ownedGlyphs.has(ordinal))refuse('Current native glyph is unowned.');const run=runByFirst.get(ordinal);if(run)paints.push({kind:'text',node:n,run,planes:parents,clips:scopes,paint});return;}
  if(n.tag==='path'||n.tag==='rect'||n.tag==='image'){paints.push({kind:n.tag,node:n,planes:chain,clips:scopes,paint});return;}
  for(const c of n.children||[])walk(c,chain,scopes,paint.values);
 }walk(input.dom);
 if(nativeTextModel&&(paints.length!==1||paints[0].kind!=='text'))refuse('A bounded native text view must contain exactly its one source show.');
 let order=0;
 async function group(children,matrix=identity,clip=null,name='Current PDF plane',deferInitialSeed=false){
  await checkpoint();
  if(new Set(children).size!==children.length||children.some(child=>!ownedObjects.has(child)||child.parent||child.group)||clip&&(!ownedObjects.has(clip)||children.includes(clip)))refuse('Current native construction requires separate already-owned children and clips.');
  let bx=1,by=1;for(const child of children)for(const p of Object.values(child.calcACoords())){bx=Math.max(bx,Math.abs(p.x));by=Math.max(by,Math.abs(p.y));}
  // Reproduce the bundled Group.fromObject initialization for these already
  // owned native objects, avoiding a complete serialize/re-enliven of every
  // descendant at each declaring plane and again at the page root.
  const Noop=await nativeNoopLayout(fabric,Group,Manager,Linear);cancelled();
  const width=2*bx+2,height=2*by+2,options={...pose(matrix),width,height,strokeWidth:0,objectCaching:false,subTargetCheck:true,interactive:true,figureType:'group',name,...(clip?{clipPath:clip}:{})};
  const value=new Group(children,{...options,layoutManager:new Noop()});
  value.layoutManager=new Manager(new Linear());
  // Paint wrappers are finalized together before this private constructor
  // returns. Clip-only wrappers are outside that traversal and stay eager.
  const context={type:'initialization',target:value,targets:value.getObjects()};
  if(deferInitialSeed&&children.length)fabric.LayoutManager.prototype.subscribeTargets.call(value.layoutManager,context);
  else value.layoutManager.subscribeTargets(context);
  if(!same(value.calcOwnMatrix(),matrix))refuse('Current literal group matrix changed.');value.setCoords();ownedObjects.add(value);groupRows.push({matrix,width,height});return value;
 }
 async function wrap(object,planes,deferInitialSeed=false){for(const matrix of planes.slice().reverse())object=await group([object],matrix,null,'Current PDF plane',deferInitialSeed);return object;}
 function leaf(n,paint){let value;if(n.tag==='path'){if(!n.attrs.d||!/^[MLCQZmlcqz\s\d.,+\-eE]+$/.test(n.attrs.d))refuse('Unsupported native current path.');value=new PathClass(n.attrs.d,{...paint.options,originX:'center',originY:'center'});value.set(pose(identity));}
  else {const [x,y,width,height]=['x','y','width','height'].map(k=>Number(n.attrs[k]??0));if(![x,y,width,height].every(Number.isFinite)||width<=0||height<=0||n.attrs.rx||n.attrs.ry)refuse('Unsupported current rectangle.');value=new fabric.Rect({...paint.options,...pose([1,0,0,1,x+width/2,y+height/2]),width,height});}
  value.set({figureType:'path',name:'Current PDF path '+order,figureStudioSvgSourceOrder:order++});value.setCoords();ownedObjects.add(value);return value;
 }
 async function imageLeaf(n){
  const refs=[n.attrs.href,n.attrs['xlink:href']].filter(value=>value!==undefined),source=refs[0];
  if(!source||refs.some(value=>value!==source)||!/^data:image\/(?:png|jpeg);base64,[A-Za-z0-9+/]+={0,2}$/.test(source)||source.length>32*1024*1024)refuse('Current image requires retained ordinary decoded PNG or JPEG bytes.');
  const length=(name,fallback=0)=>{const text=String(n.attrs[name]??fallback);if(!/^[+-]?(?:\d*\.\d+|\d+\.?\d*)(?:e[+-]?\d+)?(?:px)?$/i.test(text))refuse('Current image has unsupported geometry.');return Number(text.replace(/px$/i,''));};
  const x=length('x'),y=length('y'),width=length('width'),height=length('height');
  if(![x,y,width,height].every(Number.isFinite)||width<=0||height<=0||n.attrs.preserveAspectRatio&&n.attrs.preserveAspectRatio!=='none'||n.attrs.mask||n.attrs.filter||!['auto','pixelated'].includes(n.attrs['image-rendering']))refuse('Current image requires its exact ordinary pixel rectangle and native interpolation declaration.');
  const interpolation=n.attrs['data-native-image-interpolation'];
  if(interpolation!==undefined&&(interpolation!=='default'||n.attrs['image-rendering']!=='auto'))refuse('Invalid current default image interpolation declaration.');
  const Image=registerImageClass(fabric);
  if(typeof Image?.fromURL!=='function')refuse('Current native editable image loader is unavailable.');
  const image=await Image.fromURL(source);
  if(image.constructor!==Image||image.width!==width||image.height!==height||image.getSrc()!==source)refuse('Current decoded image dimensions or retained pixels changed.');
  image.set({...pose([1,0,0,1,x+width/2,y+height/2]),strokeWidth:0,imageSmoothing:n.attrs['image-rendering']==='auto',...(interpolation==='default'?{pdfNativeImageInterpolationPolicy:'native-scale-default-v1'}:{}),objectCaching:false,figureType:'image',name:'Current PDF image '+order,figureStudioSvgSourceOrder:order++,figureStudioSvgElementTag:'image'});image.setCoords();ownedObjects.add(image);return image;
 }
 async function clipObjects(scopes){const result=[],seen=new Set();
  async function expand(reference,owner,active=new Set()){
   const id=/^url\(#([^\s)]+)\)$/.exec(reference||'')?.[1],def=defs.get(id);if(!def||active.has(def)||active.size>=16)refuse('Missing/cyclic native current clip.');active.add(def);
   if(def.attrs['clip-path'])await expand(def.attrs['clip-path'],owner,active);
   if(!seen.has(def)){seen.add(def);let n=def,planes=[...owner,...transform(def)];while(n.children?.length===1&&n.children[0].tag==='g'){n=n.children[0];if(n.attrs['clip-path'])await expand(n.attrs['clip-path'],owner,active);planes.push(...transform(n));}
    if(n.children.length!==1||!['path','rect'].includes(n.children[0].tag))refuse('Unsupported current clip declaration.');const child=n.children[0],paint=styles(child.attrs);paint.options={...paint.options,fill:'black',stroke:null,strokeWidth:0,fillRule:child.attrs['clip-rule']||def.attrs['clip-rule']||'nonzero'};planes.push(...transform(child));const object=await wrap(leaf(child,paint),planes);result.push(object);clipRows.push({id,planes,path:child.attrs.d||null,rule:paint.options.fillRule});}
   active.delete(def);
  }
  for(const scope of scopes)await expand(scope.reference,scope.owner);return result;
 }
 const constructed=[];
 for(const row of paints){let object;
  await checkpoint();
  if(row.kind==='text'){const model=row.nativeTextModel||modelFor(row.run,row.paint);object=new TextClass(model.options.text,{...model.options,fill:row.paint.options.fill,strokeWidth:0,pdfTextSource:model.source,originX:'center',originY:'center',objectCaching:false});object.set({figureType:'text',name:model.options.text,figureStudioSvgSourceOrder:order++,...(!row.nativeTextModel?{figureStudioPdfLogicalRun:{schema:protocol.SCHEMA,runId:row.run.run.id,nativeGlyphCount:row.run.shows.length,originalPdfWriterAuthority:false}}:{})});if(!same(object.calcOwnMatrix(),identity)||!object._pdfCurrentNativePlane())refuse('Current native source plane failed exact class admission.');ownedObjects.add(object);object=await wrap(object,row.nativeTextModel?row.planes:model.parentPlanes,true);}
  else object=await wrap(row.kind==='image'?await imageLeaf(row.node):leaf(row.node,row.paint),row.planes,true);
  const clips=await clipObjects(row.clips);for(const clip of clips.slice().reverse())object=await group([object],identity,clip,'Current PDF clipping scope',true);constructed.push(object);
 }
 const root=await group(constructed,identity,null,'Current PDF page',true);precision.installScene([root],{isPdfObject:()=>true});await checkpoint();await materializer.finalizeImportedAuthoringLayoutAsync([root],{fabric,signal,yieldToUi:yieldUi});await checkpoint();return {root,paints,groupRows,clipRows};
}
function construct(fabric,materializer,input,options){return constructInternal(fabric,materializer,input,options);}
// This constructor grants no source authority. Its caller must own the actual
// byte-derived glyph record and validate the one-show model before construction.
// It shares the native identity text owner, literal parents and clip adoption
// used above, without introducing own-export logical membership for source PDFs.
function constructTextPlanes(fabric,materializer,{dom,model}={},options){
 if(!model?.source?.currentNativeGlyphPlanes||typeof model.options?.text!=='string'||model.options.text.length>4096||!Array.isArray(model.source.glyphs)||!model.source.glyphs.length||model.source.glyphs.length>4096)refuse('A bounded source glyph-plane model is required.');
 return constructInternal(fabric,materializer,{dom,runs:[]},options,model);
}
return Object.freeze({construct,constructTextPlanes,registerImageClass,retainImageInterpolation});
});
