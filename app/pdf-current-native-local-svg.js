/* A private authenticated generated-PDF route keeps each current native CM as
 * an SVG declaring plane. The bundled decoder owns all glyph/path/font output. */
(function(root,factory){const clips=typeof module==='object'&&module.exports?require('./pdf-current-native-clip-planes.js'):root.FigureStudioPdfCurrentNativeClipPlanes;const numbers=typeof module==='object'&&module.exports?require('./pdf-decoded-svg-number-precision.js'):root.FigureStudioPdfSvgNumberPrecision;const api=factory(clips,numbers);if(typeof module==='object'&&module.exports)module.exports=api;else root.FigureStudioPdfCurrentNativeLocalSvg=api;})(typeof globalThis==='object'?globalThis:this,function(clips,numbers){
 'use strict';
 function refuse(message){const error=new Error(message);error.code='PDF_LOGICAL_TEXT_UNSUPPORTED';throw error;}
 const I=[1,0,0,1,0,0],multiply=(a,b)=>[a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5]],exact=(a,b)=>a.length===b.length&&a.every((value,index)=>Object.is(value,b[index]));
 // This pass owns only a fresh private generated-PDF DOM. It shares adjacent
 // wrappers without changing any paint or multiplying literal source planes.
 async function shareCurrentSvgGroups(svg,{signal,yieldControl}={}){
  const cancelled=()=>{if(signal?.aborted){const error=new Error('Current SVG group sharing was cancelled.');error.name='AbortError';throw error;}};
  const yieldUi=yieldControl||(()=>new Promise(resolve=>{const channel=new MessageChannel();channel.port1.onmessage=()=>{channel.port1.close();channel.port2.close();resolve();};channel.port2.postMessage(null);}));
  let started=performance.now();
  async function checkpoint(){cancelled();if(performance.now()-started>=8){await yieldUi();cancelled();started=performance.now();}}
  cancelled();const original=[svg,...svg.querySelectorAll('*')];
  if(original.length<=20000)return svg;
  // Additional raw-work guards, not larger final DOM/constructor allowances.
  if(original.length>200000)refuse('Current SVG group sharing exceeds its raw traversal budget.');
  const allowed=new Set(['svg','g','defs','style','clipPath','path','rect','text','tspan','image']);
  function read(node){return {name:node.localName,namespace:node.namespaceURI,parent:node.parentElement,attrs:Array.from(node.attributes,a=>[a.name,a.value]),text:Array.from(node.childNodes).filter(child=>child.nodeType!==1).map(child=>[child.nodeType,child.textContent])};}
  // Capture the initial bounded state coherently before the first yield. All
  // later baseline records use these immutable strings and original parents.
  const initial=new Map();let literalUnits=0;
  for(const node of original){
   const row=read(node);
   if(!allowed.has(row.name)||row.namespace!=='http://www.w3.org/2000/svg')refuse('Current SVG group sharing has an unqualified source element.');
   for(const [,value]of row.attrs)literalUnits+=value.length;
   for(const [,value]of row.text)literalUnits+=value.length;
   if(literalUnits>8000000)refuse('Current SVG group sharing exceeds its literal resource budget.');
   initial.set(node,row);
  }
  const stable=new Map(original.map((node,index)=>[node,index])),ids=new Set(),references=new Set();
  const attribute=(row,name)=>row.attrs.find(([key])=>key===name)?.[1];
  for(const node of original){
   await checkpoint();const row=initial.get(node),id=attribute(row,'id');
   if(row.name==='clipPath'&&attribute(row,'clipPathUnits')!==undefined&&attribute(row,'clipPathUnits')!=='userSpaceOnUse')refuse('Current SVG group sharing requires user-space clipping.');
   if(id){if(ids.has(id))refuse('Current SVG group sharing found duplicate source IDs.');ids.add(id);}
   for(const [name,value]of row.attrs){
    for(const match of value.matchAll(/url\(\s*['"]?#([^\s'"\)]+)/g))references.add(match[1]);
    if(value.startsWith('#'))references.add(value.slice(1));
    if(name!=='id')for(const match of value.matchAll(/pdf-scope-\d+/g))references.add(match[0]);
   }
   if(row.name==='style'){
    const text=row.text.map(([,value])=>value).join('');
    if(text.replace(/@font-face\s*\{[^}]*\}/gi,'').trim())refuse('Current SVG group sharing requires the native font-only stylesheet.');
    for(const match of text.matchAll(/pdf-scope-\d+/g))references.add(match[0]);
   }
  }
  const group=row=>row.name==='g',noText=row=>row.text.length===0;
  const neutral=row=>group(row)&&noText(row)&&(!row.attrs.length||row.attrs.length===2&&attribute(row,'data-pdf-scope')==='graphics-state'&&/^pdf-scope-\d+$/.test(attribute(row,'id'))&&!references.has(attribute(row,'id')));
  const structural=row=>group(row)&&noText(row)&&(neutral(row)||row.attrs.length>0&&row.attrs.every(([name])=>name==='transform'||name==='clip-path'));
  const same=(left,right)=>Object.is(left,right)||Array.isArray(left)&&Array.isArray(right)&&left.length===right.length&&left.every((value,index)=>same(value,right[index]));
  function witness(node,records){
   const row=records.get(node),chain=[];let depth=0;
   for(let parent=row.parent;parent;parent=records.get(parent)?.parent){
    const ancestor=records.get(parent);
    if(!ancestor||++depth>48)refuse('Current SVG group sharing exceeds the original depth/ownership limit.');
    const frame=ancestor.attrs.filter(([name])=>name==='transform'||name==='clip-path');
    if(frame.length)chain.unshift(['planes',frame]);
    if(!structural(ancestor))chain.unshift(['scope',stable.get(parent)]);
   }
   return [stable.get(node),row.name,row.namespace,row.attrs,row.text,chain];
  }
  const before=[];
  for(const node of original){await checkpoint();if(!structural(initial.get(node)))before.push(witness(node,initial));}
  function mergeable(left,right){
   const a=initial.get(left),b=initial.get(right);
   if(!a||!b||!group(a)||!group(b)||!noText(a)||!noText(b))return false;
   const actual=Array.from(left.attributes,attribute=>[attribute.name,attribute.value]),next=Array.from(right.attributes,attribute=>[attribute.name,attribute.value]);
   return actual.length>0&&actual.every(([name])=>name==='transform'||name==='clip-path')&&same(actual,next);
  }
  async function replace(parent,children){while(parent.firstChild)parent.removeChild(parent.firstChild);for(const child of children){await checkpoint();parent.appendChild(child);}}
  async function append(children,node){
   await checkpoint();const last=children.at(-1);
   if(mergeable(last,node)){
    const shared=Array.from(last.childNodes);
    for(const child of Array.from(node.childNodes))await append(shared,child);
    await replace(last,shared);node.remove();
   }else children.push(node);
  }
  for(const node of original.slice().reverse()){
   await checkpoint();if(!['svg','g','defs','clipPath'].includes(node.localName))continue;
   const children=[];
   for(const child of Array.from(node.childNodes)){
    if(child.nodeType===1&&neutral(read(child))){for(const descendant of Array.from(child.childNodes))await append(children,descendant);}
    else await append(children,child);
   }
   await replace(node,children);
  }
  // The complete final comparison is atomic with respect to UI task yields.
  cancelled();const after=[svg,...svg.querySelectorAll('*')],current=new Map();
  if(after.length>20000)refuse('Current SVG group sharing remains above the original declaration limit.');
  for(const node of after){
   if(!stable.has(node)||!allowed.has(node.localName))refuse('Current SVG group sharing lost original element ownership.');
   current.set(node,read(node));
  }
  let index=0;
  for(const node of after)if(!structural(current.get(node))&&!same(before[index++],witness(node,current)))refuse('Current SVG group sharing changed source paint, resource, plane or effect ownership.');
  if(index!==before.length)refuse('Current SVG group sharing lost original paint or resource membership.');
  cancelled();return svg;
 }

 function graphicsClass(Base,{authority,pdfjs,operators,viewport,signal},snapshot,batched=false){
  if(typeof Base!=='function'||!(Base.prototype instanceof pdfjs.SVGGraphics)||!clips||!numbers||!authority)refuse('The current native local SVG route requires its authenticated bundled renderer.');
  if(!batched)clips.currentShows(authority);
  const view=Array.from(viewport.transform),size=[viewport.width,viewport.height],sameViewport=()=>view.every((value,index)=>Object.is(value,viewport.transform[index]))&&Object.is(size[0],viewport.width)&&Object.is(size[1],viewport.height),names=new Map(Object.entries(pdfjs.OPS).map(([name,id])=>[id,name]));
  const unsupported=new Set(['beginGroup','endGroup','paintFormXObjectBegin','paintFormXObjectEnd','shadingFill','setFillColorN','setStrokeColorN','paintImageXObjectRepeat','paintInlineImageXObjectGroup','paintImageMaskXObject','paintImageMaskXObjectRepeat','paintImageMaskXObjectGroup']);
  return class CurrentOperatorLocalSvgGraphics extends Base {
   constructor(commonObjs,objs){super(commonObjs,objs);this.current.miterLimit=10;this.currentLocalPlanes=[];this.currentLocalWorld=view.slice();this.currentLocalPlaneStack=[];}
   async getSVG(actualOperators,actualViewport){
    if(actualOperators!==operators||actualViewport!==viewport||!sameViewport())refuse('Current native local SVG input identity or operators changed.');
    if(batched)await clips.currentShowsBatched(authority,operators,pdfjs.OPS,snapshot);else {if(!clips.sameOperators(operators,snapshot))refuse('Current native local SVG operators changed.');clips.currentShows(authority);}
    for(const id of operators.fnArray)if(unsupported.has(names.get(id)))refuse('Unsupported current native local SVG paint '+names.get(id));
    const svg=await super.getSVG(actualOperators,actualViewport);
    await shareCurrentSvgGroups(svg,{signal});
    if(!sameViewport()||this.currentLocalPlaneStack.length)refuse('Current native local SVG operands or state stack changed during decoding.');
    if(batched)await clips.currentShowsBatched(authority,operators,pdfjs.OPS,snapshot);else {if(!clips.sameOperators(operators,snapshot))refuse('Current native local SVG operands changed during decoding.');clips.currentShows(authority);}
    if(signal?.aborted){const error=new Error('Current native SVG rendering was cancelled.');error.name='AbortError';throw error;}
    return svg;
   }
   save(){this.currentLocalPlaneStack.push({planes:this.currentLocalPlanes,world:this.currentLocalWorld});return super.save();}
   restore(){if(!this.currentLocalPlaneStack.length)refuse('Unbalanced current native local SVG restore.');const result=super.restore(),saved=this.currentLocalPlaneStack.pop();this.currentLocalPlanes=saved.planes;this.currentLocalWorld=saved.world;return result;}
   transform(...values){if(values.length!==6||!values.every(Number.isFinite))refuse('Invalid current native CM plane.');const before=this.transformMatrix.slice(),world=multiply(this.currentLocalWorld,values),result=super.transform(...values);if(!exact(values,I)||!exact(before,this.transformMatrix)||!exact(world,this.currentLocalWorld))this.currentLocalPlanes=[...this.currentLocalPlanes,values.slice()];this.currentLocalWorld=world;return result;}
   moveText(x,y){const previous=this.current.tspan,parent=this.current.txtElement;const result=super.moveText(x,y);if(previous&&previous!==this.current.tspan&&previous.parentNode===parent&&!previous.textContent&&!previous.children.length)previous.remove();return result;}
   paintInlineImageXObject(data,mask){
    if(mask||this.current.fillAlpha!==1||!Number.isSafeInteger(data?.width)||!Number.isSafeInteger(data?.height)||data.width<=0||data.height<=0||data.interpolate!==undefined&&typeof data.interpolate!=='boolean')refuse('The current native image requires an ordinary image invocation and native interpolation flag.');
    const pending=this.pendingClip,element=this.current.element;
    const result=super.paintInlineImageXObject(data);
    const image=this.tgrp?.lastElementChild;
    if(image?.localName!=='image')refuse('The bundled native image declaration changed.');
    image.setAttribute('transform',numbers.matrix([1/data.width,0,0,-1/data.height,0,0]));
    // Keep the decoder's actual /Interpolate semantics. Its PNG may itself
    // retain alpha; the invocation alpha above remains a separate PDF state.
    image.setAttribute('image-rendering',data.interpolate===false?'pixelated':'auto');
    // An absent hint uses the bundled Canvas renderer's device-scale default.
    // Keep it separate from either explicit Boolean through native persistence.
    if(data.interpolate===undefined)image.setAttribute('data-native-image-interpolation','default');
    // The bundled renderer creates an unfinished intrinsic image clip. The
    // image's own rectangle supplies that boundary; only actual PDF clips may
    // become new source scopes for later paths or glyphs.
    this.pendingClip=pending;this.current.element=element;return result;
   }
   appendCurrentPlanes(parent,content){let next=parent;for(const matrix of this.currentLocalPlanes){const group=this.svgFactory.createElement('svg:g');group.setAttribute('transform',numbers.matrix(matrix));next.append(group);next=group;}if(content)next.append(content);return next;}
   _ensureTransformGroup(){if(!this.tgrp){const parent=this.current.activeClipUrl?this._ensureClipGroup():this.svg;this.tgrp=this.appendCurrentPlanes(parent);if(this.tgrp===parent){this.tgrp=this.svgFactory.createElement('svg:g');parent.append(this.tgrp);}}return this.tgrp;}
   endPath(){const clipped=Boolean(this.pendingClip&&this.current.element),result=super.endPath();if(clipped){const definition=this.defs.lastElementChild;if(definition?.localName.toLowerCase()!=='clippath')refuse('The bundled native clip declaration changed.');const children=Array.from(definition.children);definition.removeAttribute('transform');for(const child of children)this.appendCurrentPlanes(definition,child);}return result;}
  };
 }
 function createGraphicsClass(Base,options){return graphicsClass(Base,options,clips.captureOperators(options.operators));}
 async function createGraphicsClassBatched(Base,options,snapshot){clips.assertCurrentViewportBatched(options.authority,options.viewport);await clips.currentShowsBatched(options.authority,options.operators,options.pdfjs.OPS,snapshot);clips.assertCurrentViewportBatched(options.authority,options.viewport);return graphicsClass(Base,options,snapshot,true);}
 return Object.freeze({createGraphicsClass,createGraphicsClassBatched});
});
