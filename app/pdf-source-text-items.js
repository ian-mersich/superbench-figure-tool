/* Source-linked text-item membership for fresh PDF imports. No saved JSON or
 * SVG marker grants membership, original-stream write or logical-export authority. */
(function(root,factory){
  const spacing=typeof module==='object'&&module.exports?require('./pdf-text-spacing.js'):root.FigureStudioPdfTextSpacing;
  const api=factory(spacing);if(typeof module==='object'&&module.exports)module.exports=api;
  else root.FigureStudioPdfSourceTextItems=api;
})(typeof globalThis==='object'?globalThis:this,function(spacing){
  'use strict';
  const captures=new WeakMap(),issued=new WeakMap();
  const nontext=new Set(['fill','eoFill','stroke','fillStroke','eoFillStroke','closeStroke','closeFillStroke','closeEOFillStroke','paintSolidColorImageMask','paintImageXObject','paintInlineImageXObject','shadingFill']);
  const caps={operators:100000,shows:50000,glyphs:100000,items:10000,work:5000000,characters:4096};
  const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
  const attrs=node=>Array.from(node.attributes||[],a=>[a.name,a.value]);
  const childElements=node=>Array.from(node.children||[]);
  const tag=node=>String(node.localName||node.nodeName||'').replace(/^.*:/,'').toLowerCase();
  const list=value=>String(value||'').trim().split(/[ ,]+/).filter(Boolean);
  const clone=value=>structuredClone(value);
  function freeze(value){if(value&&typeof value==='object'&&!Object.isFrozen(value)){for(const child of Object.values(value))freeze(child);Object.freeze(value);}return value;}
  function matrices(raw){
    const result=[];let covered='';
    for(const match of String(raw||'').matchAll(/(matrix|scale|translate)\(([^)]*)\)/g)){
      covered+=match[0];const n=list(match[2]).map(Number);let matrix;
      if(match[1]==='matrix'&&n.length===6)matrix=n;
      else if(match[1]==='scale'&&[1,2].includes(n.length))matrix=[n[0],0,0,n[1]??n[0],0,0];
      else if(match[1]==='translate'&&[1,2].includes(n.length))matrix=[1,0,0,1,n[0],n[1]??0];
      else throw Error('Unsupported source text matrix.');
      if(matrix.some(v=>!Number.isFinite(v)||Object.is(v,-0)||Math.abs(v)>1e8)||matrix[0]*matrix[3]-matrix[1]*matrix[2]===0)throw Error('Invalid source text matrix.');
      result.push(matrix);
    }
    if(covered.replace(/\s/g,'')!==String(raw||'').replace(/\s/g,''))throw Error('Unknown source text transform.');return result;
  }
  function begin(graphics,operators,items,pdfjs){
    if(!spacing||!operators||operators.fnArray.length>caps.operators||!Array.isArray(items)||items.length>caps.items)return false;
    if(operators.fnArray.some(fn=>[pdfjs.OPS.paintFormXObjectBegin,pdfjs.OPS.beginGroup,pdfjs.OPS.nextLineShowText,pdfjs.OPS.nextLineSetSpacingShowText].includes(fn)))return false;
    const indices=Array.from(operators.fnArray).flatMap((fn,index)=>[pdfjs.OPS.showText,pdfjs.OPS.showSpacedText].includes(fn)?[index]:[]);
    if(indices.length>caps.shows)return false;
    captures.set(graphics,{indices,items:items.flatMap((i,itemIndex)=>typeof i.str==='string'&&i.str&&i.str.length<=caps.characters&&i.dir==='ltr'?[{str:i.str,fontName:i.fontName,transform:Array.from(i.transform||[]),hasEOL:i.hasEOL,itemIndex}]:[]),rows:[],show:0,paint:0,glyphs:0});return true;
  }
  function recording(graphics){return captures.has(graphics);}
  function operation(graphics,op){const c=captures.get(graphics);if(c&&nontext.has(op.fn))c.paint++;}
  function beforeShow(graphics){
    const c=captures.get(graphics);if(!c)return null;const state=graphics.current,span=state.tspan;
    return{index:c.indices[c.show++],span,prefix:graphics.runGlyphs.get(span)?.length||0,plane:spacing.textTransform(state,graphics.transformMatrix),fontName:state.pdfSourceFontName,clip:state.activeClipUrl||null,paint:c.paint,state:{alpha:state.fillAlpha,rendering:state.textRenderingMode,fill:state.fillColor}};
  }
  function afterShow(graphics,row){
    const c=captures.get(graphics);if(!c||!row)return;
    const recovered=(graphics.runGlyphs.get(row.span)||[]).slice(row.prefix),xs=list(row.span.getAttribute('x')),ys=list(row.span.getAttribute('y'));
    if(!recovered.length)return;
    c.glyphs+=recovered.length;if(c.glyphs>caps.glyphs){captures.delete(graphics);return;}
    row.glyphs=recovered.map((g,i)=>({unicode:g.unicode,fontChar:g.fontChar,width:g.width,x:xs[row.prefix+i],y:ys[row.prefix+i]??ys[0]}));
    row.text=row.glyphs.map(g=>g.unicode).join('');row.textNode=row.span.parentElement;row.textTransform=row.textNode?.getAttribute('transform');c.rows.push(row);
  }
  function signatures(nodes,clipNodes){return nodes.map(node=>({node,parent:node.parentElement,attributes:attrs(node),text:tag(node)==='tspan'?node.textContent:null,children:clipNodes.has(node)?childElements(node):null}));}
  function unchanged(records){return records.every(r=>r.node.parentElement===r.parent&&same(attrs(r.node),r.attributes)&&(r.text===null||r.node.textContent===r.text)&&(r.children===null||childElements(r.node).length===r.children.length&&r.children.every((n,i)=>r.node.children[i]===n)));}
  function placeAxisAligned(object,matrix){
    if(!Array.isArray(matrix)||matrix.length!==6||!matrix.every(Number.isFinite)||matrix[0]<1e-8||Math.abs(matrix[3])<1e-8||matrix[0]>1e8||Math.abs(matrix[3])>1e8||matrix[1]!==0||matrix[2]!==0)return false;
    object.set({originX:'center',originY:'center',left:matrix[4],top:matrix[5],scaleX:matrix[0],scaleY:Math.abs(matrix[3]),angle:0,skewX:0,skewY:0,flipX:false,flipY:matrix[3]<0});
    return object.calcOwnMatrix().every((v,i)=>v===matrix[i]);
  }
  function opaque(node){
    const style=String(node.getAttribute('style')||'');
    return !['mask','filter'].some(k=>node.hasAttribute(k))&&!/mix-blend-mode|background|isolation\s*:/i.test(style)
      &&(!node.hasAttribute('opacity')||Number(node.getAttribute('opacity'))===1)
      &&!/(?:^|;)\s*opacity\s*:\s*(?!1(?:\.0*)?\s*(?:;|$))/i.test(style);
  }
  function modelFor(item,members,spanRows,svg,programs,source){
    const first=members[0],spans=[...new Set(members.map(r=>r.span))],text=spans[0].parentElement;
    if(spans.length<2)throw Error('One source span already has its native text owner.');
    if(tag(text)!=='text'||spans.some(span=>span.parentElement!==text||span.querySelector?.('tspan')))throw Error('Different source text owners.');
    const children=childElements(text),start=children.indexOf(spans[0]);
    const memberSet=new Set(members);
    if(start<0||!spans.every((span,i)=>children[start+i]===span)||spans.some(span=>spanRows.get(span).some(row=>!memberSet.has(row))))throw Error('Incomplete contiguous source span coverage.');
    if(members.some(row=>row.textNode!==text||row.textTransform!==text.getAttribute('transform')))throw Error('The source text plane changed after its actual show.');
    for(const span of spans){
      const rows=spanRows.get(span),glyphs=rows.flatMap(row=>row.glyphs),live=JSON.parse(span.getAttribute('data-pdf-glyph-map')||'null'),xs=list(span.getAttribute('x')),ys=list(span.getAttribute('y'));
      if(!Array.isArray(live)||live.length!==glyphs.length||xs.length!==glyphs.length||![1,glyphs.length].includes(ys.length)
          ||glyphs.some((g,i)=>g.unicode!==live[i].unicode||g.fontChar!==live[i].fontChar||g.x!==xs[i]||g.y!==(ys[i]??ys[0])))throw Error('The complete source glyph span changed.');
    }
    if(members.some(row=>!same(row.plane.slice(0,4),first.plane.slice(0,4))||row.paint!==first.paint||row.clip!==first.clip||!same(row.state,first.state)))throw Error('Different source paint/clip/linear scope.');
    if(first.state.alpha!==1||first.state.rendering!==0)throw Error('Unsupported source text compositing.');
    const ancestors=[];for(let n=text;n&&n!==svg;n=n.parentElement){if(n!==text&&tag(n)!=='g'||!opaque(n))throw Error('Unsupported source text ancestor.');ancestors.push(n);}
    if(!opaque(svg))throw Error('Unsupported source page effect.');
    for(const node of ancestors.slice(1).concat(svg))for(const m of matrices(node.getAttribute('transform'))){
      if(m[1]!==0||m[2]!==0||m[0]<=0||m[3]===0)throw Error('Source item parent requires its existing literal-plane constructor.');
    }
    const definitions=Array.from(svg.querySelectorAll?.('clipPath')||[]),clipNodes=[];
    for(const definition of definitions){clipNodes.push(definition,...Array.from(definition.querySelectorAll?.('*')||[]));}
    const glyphs=[],entries=[],styles={},declarations=[],fontSources={};let cursor=0;
    const firstX=Number(first.glyphs[0].x),firstY=Number(first.glyphs[0].y);
    for(const row of members){
      const span=row.span,declaration={fontFamily:span.getAttribute('font-family'),fontSize:parseFloat(span.getAttribute('font-size')),fontWeight:span.getAttribute('font-weight')||'normal',fontStyle:span.getAttribute('font-style')||'normal'};
      const program=programs.find(p=>p.family===declaration.fontFamily),key=JSON.stringify([declaration.fontFamily,declaration.fontWeight,declaration.fontStyle]);
      if(!program?.dataUrl||!(declaration.fontSize>0))throw Error('Missing complete source display font.');
      const font=fontSources[key]||={...declaration,sourceFontName:row.fontName,sourceEmbeddedProgram:true,map:{...(program.unicodeToFontChar||{})},unicodeAdvances:{...(program.unicodeAdvances||{})}};
      const own=[...matrices(text.getAttribute('transform')),...matrices(span.getAttribute('transform'))];
      if(!own.length||own.length>4)throw Error('Source text exceeds its native plane envelope.');
      for(const g of row.glyphs){
        if(!g.unicode||!g.fontChar||![Number(g.x),Number(g.y)].every(Number.isFinite))throw Error('Incomplete source glyph.');
        if(Object.hasOwn(font.map,g.unicode)&&font.map[g.unicode]!==g.fontChar)throw Error('Ambiguous source Unicode mapping.');
        Object.defineProperty(font.map,g.unicode,{value:g.fontChar,writable:true,enumerable:true,configurable:true});
        if(/^\s+$/u.test(g.unicode)&&Number.isFinite(g.width))Object.defineProperty(font.unicodeAdvances,g.unicode,{value:g.width/1000,writable:true,enumerable:true,configurable:true});
        const charCount=Array.from(g.unicode).length;
        for(let i=0;i<charCount;i++){styles[cursor+i]={...declaration,fill:first.state.fill,stroke:null,strokeWidth:0};declarations.push({...declaration});}
        glyphs.push({unicode:g.unicode,fontChar:g.fontChar,charIndex:cursor,charCount,x:Number(g.x)-firstX,y:Number(g.y)-firstY,sourceFontFamily:declaration.fontFamily,sourceFontKey:key});
        entries.push({matrices:own.map(m=>m.slice()),x:g.x,y:g.y,charIndex:cursor,charCount,sourceFontKey:key});cursor+=charCount;
      }
    }
    if(cursor>caps.characters||glyphs.map(g=>g.unicode).join('')!==item.str)throw Error('Incomplete source item glyph coverage.');
    const base=declarations[0],options={text:item.str,...base,styles:{0:styles},fill:first.state.fill,stroke:null,strokeWidth:0,opacity:1,charSpacing:0,textAlign:'left',lineHeight:1.16,direction:'ltr',originX:'center',originY:'center',objectCaching:false,editable:true};
    const data={schema:'figureStudio.pdfPositionedText.v2',text:item.str,anchor:'start',...base,glyphs,map:{},fontSources,fallbackFont:'Arial',capture:{styles:clone(options.styles),baseLayout:[0,'left',1.16],declarations},currentNativeGlyphPlanes:{schema:'figureStudio.currentNativeGlyphPlanes.v1',entries},sourceItemMembership:{schema:'figureStudio.sourceTextItem.v1',...source,itemIndex:item.itemIndex,sourceShowIndices:members.map(r=>r.index),sourceSpanCount:spans.length,originalPdfWriterAuthority:false}};
    return{spans,text,options:freeze(options),source:freeze(data),signature:signatures([...spans,...ancestors,svg,...clipNodes],new Set(clipNodes)),children:children.slice()};
  }
  function finish(graphics,svg,programs,source){
    const c=captures.get(graphics);captures.delete(graphics);
    if(!c||c.show!==c.indices.length||!source||!/^[a-f0-9]{64}$/.test(source.sourceSha256)||!Number.isSafeInteger(source.pageNumber))return null;
    const matches=[];let work=0;
    for(let itemIndex=0;itemIndex<c.items.length;itemIndex++){
      const item=c.items[itemIndex],candidates=[];
      if(item.transform.length!==6||!item.transform.every(Number.isFinite))continue;
      for(let start=0;start<c.rows.length;start++){
        if(++work>caps.work)return null;const first=c.rows[start];
        if(first.fontName!==item.fontName||first.plane.some((v,i)=>Math.abs(v-item.transform[i])>1e-5))continue;
        let str='';for(let end=start;end<Math.min(c.rows.length,start+256);end++){
          if(++work>caps.work)return null;const row=c.rows[end];if(row.fontName!==item.fontName||row.paint!==first.paint||row.clip!==first.clip)break;
          str+=row.text;if(!item.str.startsWith(str))break;if(str===item.str){candidates.push({start,end});break;}
        }
      }
      matches.push({item,candidates});
    }
    const uses=new Map();for(const m of matches.filter(m=>m.candidates.length===1)){const{start,end}=m.candidates[0];for(let i=start;i<=end;i++)uses.set(i,(uses.get(i)||0)+1);}
    const plans=[],refused=[],spanRows=new Map();for(const row of c.rows){if(!spanRows.has(row.span))spanRows.set(row.span,[]);spanRows.get(row.span).push(row);}
    for(const match of matches){
      if(match.candidates.length!==1)continue;const{start,end}=match.candidates[0];if(c.rows.slice(start,end+1).some((_,i)=>uses.get(start+i)!==1))continue;
      try{plans.push(modelFor(match.item,c.rows.slice(start,end+1),spanRows,svg,programs,source));}catch(error){refused.push({itemIndex:match.item.itemIndex,reason:String(error.message)});}
    }
    const fonts=programs.map(p=>({ref:p,family:p.family,data:p.dataUrl,map:JSON.stringify(p.unicodeToFontChar||{}),advances:JSON.stringify(p.unicodeAdvances||{})}));
    issued.set(svg,{plans,fonts,clips:Array.from(svg.querySelectorAll?.('clipPath')||[])});return{schema:'figureStudio.sourceTextItems.v1',joinedItems:plans.length,sourceSpans:plans.reduce((n,p)=>n+p.spans.length,0),refused};
  }
  function materialization(svg,programs,admit=()=>true){
    const record=issued.get(svg);if(!record)return null;issued.delete(svg);
    const clipsCurrent=()=>{const clips=Array.from(svg.querySelectorAll?.('clipPath')||[]);return clips.length===record.clips.length&&clips.every((n,i)=>n===record.clips[i]);};
    if(!clipsCurrent())throw Error('Source text clip definitions changed.');
    if(record.fonts.some(p=>!programs.includes(p.ref)||p.ref.family!==p.family||p.ref.dataUrl!==p.data||JSON.stringify(p.ref.unicodeToFontChar||{})!==p.map||JSON.stringify(p.ref.unicodeAdvances||{})!==p.advances))throw Error('Source text font ownership changed.');
    const first=new WeakMap(),covered=new WeakSet();
    let count=0;for(const plan of record.plans){
      if(!unchanged(plan.signature)||!same(childElements(plan.text).map(n=>plan.children.indexOf(n)),plan.children.map((_,i)=>i)))throw Error('Source text membership changed.');
      if(!admit(plan))continue;count++;
      first.set(plan.spans[0],plan);for(const span of plan.spans.slice(1))covered.add(span);
    }
    return Object.freeze({count,get(span){const plan=first.get(span);if(plan&&(!clipsCurrent()||!unchanged(plan.signature)||childElements(plan.text).length!==plan.children.length||plan.children.some((n,i)=>plan.text.children[i]!==n)))throw Error('Source text span changed during materialization.');return plan||null;},covered:span=>covered.has(span)});
  }
  return Object.freeze({begin,recording,operation,beforeShow,afterShow,finish,materialization,placeAxisAligned});
});
