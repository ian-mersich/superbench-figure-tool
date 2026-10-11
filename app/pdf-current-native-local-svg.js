/* A private authenticated generated-PDF route keeps each current native CM as
 * an SVG declaring plane. The bundled decoder owns all glyph/path/font output. */
(function(root,factory){const clips=typeof module==='object'&&module.exports?require('./pdf-current-native-clip-planes.js'):root.FigureStudioPdfCurrentNativeClipPlanes;const numbers=typeof module==='object'&&module.exports?require('./pdf-decoded-svg-number-precision.js'):root.FigureStudioPdfSvgNumberPrecision;const api=factory(clips,numbers);if(typeof module==='object'&&module.exports)module.exports=api;else root.FigureStudioPdfCurrentNativeLocalSvg=api;})(typeof globalThis==='object'?globalThis:this,function(clips,numbers){
 'use strict';
 function refuse(message){const error=new Error(message);error.code='PDF_LOGICAL_TEXT_UNSUPPORTED';throw error;}
 function createGraphicsClass(Base,{authority,pdfjs,operators,viewport}){
  if(typeof Base!=='function'||!(Base.prototype instanceof pdfjs.SVGGraphics)||!clips||!numbers||!authority)refuse('The current native local SVG route requires its authenticated bundled renderer.');
  clips.currentShows(authority);
  const snapshot=clips.captureOperators(operators),view=Array.from(viewport.transform),names=new Map(Object.entries(pdfjs.OPS).map(([name,id])=>[id,name]));
  const unsupported=new Set(['beginGroup','endGroup','paintFormXObjectBegin','paintFormXObjectEnd','shadingFill','setFillColorN','setStrokeColorN','paintImageXObject','paintImageXObjectRepeat','paintInlineImageXObject','paintInlineImageXObjectGroup','paintImageMaskXObject','paintImageMaskXObjectRepeat','paintImageMaskXObjectGroup']);
  return class CurrentOperatorLocalSvgGraphics extends Base {
   constructor(commonObjs,objs){super(commonObjs,objs);this.currentLocalPlanes=[];this.currentLocalPlaneStack=[];}
   async getSVG(actualOperators,actualViewport){
    if(actualOperators!==operators||actualViewport!==viewport||!clips.sameOperators(operators,snapshot)||!view.every((value,index)=>Object.is(value,viewport.transform[index])))refuse('Current native local SVG input identity or operators changed.');
    clips.currentShows(authority);for(const id of operators.fnArray)if(unsupported.has(names.get(id)))refuse('Unsupported current native local SVG paint '+names.get(id));
    const svg=await super.getSVG(actualOperators,actualViewport);
    if(!clips.sameOperators(operators,snapshot)||!view.every((value,index)=>Object.is(value,viewport.transform[index]))||this.currentLocalPlaneStack.length)refuse('Current native local SVG operands or state stack changed during decoding.');
    clips.currentShows(authority);return svg;
   }
   save(){this.currentLocalPlaneStack.push(this.currentLocalPlanes);return super.save();}
   restore(){if(!this.currentLocalPlaneStack.length)refuse('Unbalanced current native local SVG restore.');const result=super.restore();this.currentLocalPlanes=this.currentLocalPlaneStack.pop();return result;}
   transform(...values){if(values.length!==6||!values.every(Number.isFinite))refuse('Invalid current native CM plane.');const result=super.transform(...values);this.currentLocalPlanes=[...this.currentLocalPlanes,values.slice()];return result;}
   appendCurrentPlanes(parent,content){let next=parent;for(const matrix of this.currentLocalPlanes){const group=this.svgFactory.createElement('svg:g');group.setAttribute('transform',numbers.matrix(matrix));next.append(group);next=group;}if(content)next.append(content);return next;}
   _ensureTransformGroup(){if(!this.tgrp){const parent=this.current.activeClipUrl?this._ensureClipGroup():this.svg;this.tgrp=this.appendCurrentPlanes(parent);if(this.tgrp===parent){this.tgrp=this.svgFactory.createElement('svg:g');parent.append(this.tgrp);}}return this.tgrp;}
   endPath(){const clipped=Boolean(this.pendingClip&&this.current.element),result=super.endPath();if(clipped){const definition=this.defs.lastElementChild;if(definition?.localName.toLowerCase()!=='clippath')refuse('The bundled native clip declaration changed.');const children=Array.from(definition.children);definition.removeAttribute('transform');for(const child of children)this.appendCurrentPlanes(definition,child);}return result;}
  };
 }
 return Object.freeze({createGraphicsClass});
});
