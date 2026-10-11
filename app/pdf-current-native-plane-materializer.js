(function(root,factory){const protocol=typeof module==='object'&&module.exports?require('./pdf-logical-text-protocol.js'):root.FigureStudioPdfLogicalTextProtocol;const precision=typeof module==='object'&&module.exports?require('./pdf-scene-number-precision.js'):root.FigureStudioPdfSceneNumberPrecision;const materializer=typeof module==='object'&&module.exports?require('./pdf-svg-materializer.js'):root.FigureStudioPdfSvgMaterializer;const api=factory(protocol,precision,materializer);if(typeof module==='object'&&module.exports)module.exports=api;else root.FigureStudioPdfCurrentNativePlaneMaterializer=api;})(typeof globalThis==='object'?globalThis:this,function(protocol,numberPrecision,materializer){
'use strict';
const {multiply,transformMatrix:parseTransform}=materializer;
const identity=[1,0,0,1,0,0],META=['figureType','name','figureStudioSvgElementId','figureStudioSvgElementTag','figureStudioSvgGroupPath','figureStudioSvgSourceOrder','figureStudioSvgTextMeta','figureStudioSvgGroupMeta','figureStudioPdfLogicalRun'];
const same=(a,b)=>Object.is(a,b)||Boolean(a&&b&&typeof a==='object'&&typeof b==='object'&&Object.keys(a).length===Object.keys(b).length&&Object.keys(a).every((k,i)=>k===Object.keys(b)[i]&&same(a[k],b[k])));
function refuse(reason){const e=new Error(reason);e.code='SVG_LOCAL_FULL_UNSUPPORTED';throw e;}
function pose(m){
 if(m.length!==6||!m.every(Number.isFinite))refuse('Invalid current literal affine plane.');
 const base={originX:'center',originY:'center',left:m[4],top:m[5],skewX:0,skewY:0};
 if(m[1]===0&&m[2]===0&&m[0]!==0&&m[3]!==0)return {...base,scaleX:Math.abs(m[0]),scaleY:Math.abs(m[3]),flipX:m[0]<0,flipY:m[3]<0,angle:0};
 if(m[0]===0&&m[3]===0&&m[1]!==0&&m[2]!==0)return {...base,scaleX:Math.abs(m[1]),scaleY:Math.abs(m[2]),flipX:false,flipY:m[1]>0?m[2]>0:m[2]<0,angle:m[1]>0?90:270};
 refuse('Only exact diagonal/reflected and quarter-axis current planes are admitted.');
}
const PAINT=['fill','stroke','stroke-width','stroke-linecap','stroke-linejoin','stroke-miterlimit','stroke-dasharray','stroke-dashoffset','fill-rule','opacity'];
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
 return {values,options:{fill:values.fill==='none'?null:values.fill||'black',stroke:!values.stroke||values.stroke==='none'?null:values.stroke,strokeWidth:numeric('stroke-width',1),strokeLineCap:values['stroke-linecap']||'butt',strokeLineJoin:values['stroke-linejoin']||'miter',strokeMiterLimit:numeric('stroke-miterlimit',4),strokeDashArray:values['stroke-dasharray']&&values['stroke-dasharray']!=='none'?values['stroke-dasharray'].split(/[ ,]+/).map(Number):null,strokeDashOffset:numeric('stroke-dashoffset',0),fillRule:values['fill-rule']||'nonzero',opacity:1,objectCaching:false},numeric};
}
function exactRaw(object,properties=META){const raw=object.toObject(properties);for(const k of ['left','top','width','height','scaleX','scaleY','angle','skewX','skewY','strokeWidth','strokeMiterLimit','strokeDashOffset','opacity','fontSize','charSpacing','lineHeight'])if(Number.isFinite(object[k]))raw[k]=object[k];if(object.path)raw.path=object.path.map(c=>c.slice());return raw;}
const assert={ok:(condition,message)=>{if(!condition)refuse(message);}},parse=parseTransform, I=identity,point=(m,p)=>[m[0]*p[0]+m[2]*p[1]+m[4],m[1]*p[0]+m[3]*p[1]+m[5]];
function transformChain(glyph){return glyph.chain.filter(c=>c.transform).map(c=>parse(c.transform));}
function declaration(glyph){return {fontFamily:glyph.attrs['font-family'],fontSize:parseFloat(glyph.attrs['font-size']),fontWeight:glyph.attrs['font-weight']||'normal',fontStyle:glyph.attrs['font-style']||'normal'};}
function modelFor(run){
 const first=run.shows[0],firstChain=transformChain(first),parentPlanes=firstChain.slice(0,-1),frame=firstChain.at(-1),det=frame[0]*frame[3]-frame[1]*frame[2],inv=[frame[3]/det,-frame[1]/det,-frame[2]/det,frame[0]/det],glyphs=[],styles={},fontSources={},declarations=[];let cursor=0;
 for(const current of run.shows){const chain=transformChain(current),m=chain.at(-1);assert.ok(same(chain.slice(0,-1),parentPlanes),'Common current literal parent CM chain');assert.ok(same(m.slice(0,4),frame.slice(0,4)),'Common current literal text linear');assert.ok(same(current.chain.filter(c=>c.clip).map(c=>c.clip),first.chain.filter(c=>c.clip).map(c=>c.clip)),'Common current literal clip declarations');const baseline=point(m,[Number(current.attrs.x),Number(current.attrs.y)]),origin=point(frame,[Number(first.attrs.x),Number(first.attrs.y)]),dx=baseline[0]-origin[0],dy=baseline[1]-origin[1],decl=declaration(current),key=protocol.fontSourceKey(decl),font=fontSources[key]||={fontFamily:decl.fontFamily,fontWeight:decl.fontWeight,fontStyle:decl.fontStyle,sourceFontName:current.show.sourceFontName,sourceEmbeddedProgram:current.show.sourceEmbeddedProgram,programSha256:current.show.programSha256||null,map:{},unicodeAdvances:{}};font.map[current.show.unicode]=current.show.fontChar;if(/^\s+$/u.test(current.show.unicode))font.unicodeAdvances[current.show.unicode]=current.show.sourceAdvance;styles[cursor]={...decl};declarations.push({...decl});glyphs.push({unicode:current.show.unicode,fontChar:current.show.fontChar,charIndex:cursor,charCount:[...current.show.unicode].length,x:inv[0]*dx+inv[2]*dy,y:inv[1]*dx+inv[3]*dy,sourceFontFamily:decl.fontFamily,sourceFontKey:key});cursor+=[...current.show.unicode].length;}
 const base=declaration(first),options={text:run.run.unicode,...base,styles:{0:styles},fill:'#000000',stroke:null,strokeWidth:0,opacity:1,charSpacing:0,textAlign:'left',lineHeight:1.16};
 const source={schema:protocol.SOURCE_SCHEMA,text:run.run.unicode,anchor:'start',...base,glyphs,map:{},fontSources,fallbackFont:'Arial',logicalSourceMembership:{schema:protocol.SCHEMA,runId:run.run.id,nativeGlyphCount:glyphs.length,originalPdfWriterAuthority:false},capture:{styles:structuredClone(options.styles),baseLayout:[0,'left',1.16],declarations}};
 source.currentNativeGlyphPlanes={schema:'figureStudio.currentNativeGlyphPlanes.v1',entries:run.shows.map(glyph=>({matrices:[...glyph.chain.at(-2).transform.matchAll(/(matrix|scale|translate)\(([^)]*)\)/g)].map(match=>parse(match[0])),x:glyph.attrs.x,y:glyph.attrs.y,charIndex:glyph.index-run.run.firstGlyph,charCount:1,sourceFontKey:protocol.fontSourceKey(declaration(glyph))}))};
 return {options,source,frame:I,parentPlanes};
}


// The runtime binder must supply a fresh privately authenticated current DOM and
// validated native emission rows. This bounded constructor itself never promotes
// document markers, retained JSON, IDs or original source records to authority.
async function construct(fabric,materializer,input){
 const defs=new Map(),ids=new Set(),paints=[],groupRows=[],clipRows=[];let count=0;
 function gather(n){if(++count>20000)refuse('Current decoded DOM budget exceeded.');const id=n.attrs?.id;if(id){if(ids.has(id))refuse('Current global ID alias.');ids.add(id);}if(n.tag.toLowerCase()==='clippath')defs.set(id,n);for(const c of n.children||[])gather(c);}gather(input.dom);
 const TextClass=materializer.registerTextClass(fabric),PathClass=materializer.registerCurrentPlanePathClass(fabric),Manager=materializer.registerAuthoringLayoutManager(fabric),precision=numberPrecision.createInstaller({fabric,additionalSerializers:[TextClass.prototype.toObject]});
 const runByFirst=new Map(input.runs.map(row=>[row.run.firstGlyph,row])),ownedGlyphs=new Set(input.runs.flatMap(row=>row.shows.map(glyph=>glyph.index)));
 const logicalIndex=n=>{const key=Object.keys(n.attrs).find(k=>k.includes('logical')&&k.includes('glyph'));return key?Number(n.attrs[key]):NaN;};
 function transform(n){return n.attrs.transform?[...n.attrs.transform.matchAll(/(matrix|scale|translate)\(([^)]*)\)/g)].map(m=>parseTransform(m[0])):[];}
 function walk(n,parents=[],clips=[],inherited={}){
  if(['defs','style','metadata','desc','clippath'].includes(n.tag.toLowerCase()))return;
  if(!['svg','g','path','rect','text'].includes(n.tag))refuse('Unsupported current paint '+n.tag);
  const own=transform(n),chain=[...parents,...own],paint=styles(n.attrs,inherited),scopes=n.attrs['clip-path']?[...clips,{reference:n.attrs['clip-path'],owner:chain}]:clips;
  if(n.tag==='text'){if(n.children.length!==1||n.children[0].tag!=='tspan')refuse('Current text must retain one authentic scalar show.');const ordinal=logicalIndex(n.children[0]);if(!ownedGlyphs.has(ordinal))refuse('Current native glyph is unowned.');const run=runByFirst.get(ordinal);if(run)paints.push({kind:'text',node:n,run,planes:parents,clips:scopes,paint});return;}
  if(n.tag==='path'||n.tag==='rect'){paints.push({kind:n.tag,node:n,planes:chain,clips:scopes,paint});return;}
  for(const c of n.children||[])walk(c,chain,scopes,paint.values);
 }walk(input.dom);
 let order=0;
 async function group(children,matrix=identity,clip=null,name='Current PDF plane'){
  let bx=1,by=1;for(const child of children)for(const p of Object.values(child.calcACoords())){bx=Math.max(bx,Math.abs(p.x));by=Math.max(by,Math.abs(p.y));}
  children.forEach(child=>precision.installScene([child],{isPdfObject:()=>true}));if(clip)precision.installScene([clip],{isPdfObject:()=>true});
  const Group=materializer.registerCurrentPlaneGroupClass?.(fabric)||(clip?materializer.registerGroupClass(fabric):fabric.Group);
  const width=2*bx+2,height=2*by+2,raw={type:Group.type,...pose(matrix),width,height,strokeWidth:0,objectCaching:false,subTargetCheck:true,interactive:true,figureType:'group',name,objects:children.map(child=>exactRaw(child)),layoutManager:{type:Manager.type,strategy:Group===fabric.Group?fabric.FitContentLayout.type:'PdfLinearFitContentLayout'},...(clip?{clipPath:exactRaw(clip)}:{})};
  const value=await Group.fromObject(raw);if(!same(value.calcOwnMatrix(),matrix))refuse('Current literal group matrix changed.');value.setCoords();groupRows.push({matrix,width,height});return value;
 }
 async function wrap(object,planes){for(const matrix of planes.slice().reverse())object=await group([object],matrix);return object;}
 function leaf(n,paint){let value;if(n.tag==='path'){if(!n.attrs.d||!/^[MLCQZmlcqz\s\d.,+\-eE]+$/.test(n.attrs.d))refuse('Unsupported native current path.');value=new PathClass(n.attrs.d,{...paint.options,originX:'center',originY:'center'});value.set(pose(identity));}
  else {const [x,y,width,height]=['x','y','width','height'].map(k=>Number(n.attrs[k]??0));if(![x,y,width,height].every(Number.isFinite)||width<=0||height<=0||n.attrs.rx||n.attrs.ry)refuse('Unsupported current rectangle.');value=new fabric.Rect({...paint.options,...pose([1,0,0,1,x+width/2,y+height/2]),width,height});}
  value.set({figureType:'path',name:'Current PDF path '+order,figureStudioSvgSourceOrder:order++});value.setCoords();return value;
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
  if(row.kind==='text'){const model=modelFor(row.run);object=new TextClass(model.options.text,{...model.options,fill:row.paint.options.fill,strokeWidth:0,pdfTextSource:model.source,originX:'center',originY:'center',objectCaching:false});object.set({figureType:'text',name:model.options.text,figureStudioSvgSourceOrder:order++,figureStudioPdfLogicalRun:{schema:protocol.SCHEMA,runId:row.run.run.id,nativeGlyphCount:row.run.shows.length,originalPdfWriterAuthority:false}});if(!same(object.calcOwnMatrix(),identity)||!object._pdfCurrentNativePlane())refuse('Current native source plane failed exact class admission.');object=await wrap(object,model.parentPlanes);}
  else object=await wrap(leaf(row.node,row.paint),row.planes);
  const clips=await clipObjects(row.clips);for(const clip of clips.slice().reverse())object=await group([object],identity,clip,'Current PDF clipping scope');constructed.push(object);
 }
 const root=await group(constructed,identity,null,'Current PDF page');precision.installScene([root],{isPdfObject:()=>true});materializer.finalizeImportedAuthoringLayout([root],{fabric});return {root,paints,groupRows,clipRows};
}
return Object.freeze({construct});
});
