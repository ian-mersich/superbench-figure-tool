/* Derived display glyphs only. Text, layout, selection and history stay in IText. */
(function (root, factory) {
  const api = factory(root);
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.FigureStudioPdfiumTextRasterizer = api;
})(typeof globalThis === 'object' ? globalThis : this, function (root) {
  'use strict';
  const scriptUrl = root.document?.currentScript?.src;
  const NativeContext=root.CanvasRenderingContext2D,nativeContextPrototype=NativeContext?.prototype;
  const nativeContextMethods=['save','restore','setTransform','getTransform','drawImage']
    .map(name=>[name,nativeContextPrototype?.[name]]);
  const primitiveContextStateKeys=['font','fillStyle','globalAlpha','globalCompositeOperation','filter','shadowBlur','shadowOffsetX','shadowOffsetY','shadowColor',
    'textBaseline','textAlign','direction','fontVariantCaps','letterSpacing'];
  const preparationPainters=new WeakMap();
  function supportedPaintContext(context) {
    return context.globalAlpha===1 && context.globalCompositeOperation==='source-over' && (!context.filter || context.filter==='none')
      && !context.shadowBlur && !context.shadowOffsetX && !context.shadowOffsetY
      && (!context.shadowColor || ['transparent','rgba(0, 0, 0, 0)','rgba(0,0,0,0)','#00000000'].includes(context.shadowColor))
      && (!context.textBaseline || context.textBaseline==='alphabetic') && (!context.textAlign || ['left','start'].includes(context.textAlign))
      && context.direction!=='rtl' && (!context.fontVariantCaps || context.fontVariantCaps==='normal')
      && (!context.letterSpacing || ['0px','normal'].includes(context.letterSpacing));
  }
  const finite = values => values.every(Number.isFinite);
  const fontKey = font => JSON.stringify([font.family, String(font.weight || 'normal'), font.style || 'normal']);
  const product = (a,b) => [a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5]];
  const point = (m,x,y) => [m[0]*x+m[2]*y+m[4],m[1]*x+m[3]*y+m[5]];

  // These bounds are used only to allocate display tiles. Native PDFium owns
  // the glyph outline. Unsupported sfnt/cmap/loca data keeps Fabric's painter.
  function trueType(bytes) {
    try {
      const v = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength), tables = new Map();
      const range = (p,n) => Number.isInteger(p) && p >= 0 && n >= 0 && p+n <= bytes.length;
      if (!range(0,12) || v.getUint32(0) !== 0x00010000) return null;
      const count = v.getUint16(4);
      if (count > 256 || !range(12,count*16)) return null;
      for (let i=0;i<count;i++) {
        const p=12+i*16, tag=String.fromCharCode(...bytes.subarray(p,p+4)), offset=v.getUint32(p+8), size=v.getUint32(p+12);
        if (!range(offset,size)) return null;
        tables.set(tag,{offset,size});
      }
      if(['COLR','CPAL','SVG ','CBDT','CBLC','sbix','EBDT','EBLC','bdat','bloc','fvar','gvar','CFF ','CFF2'].some(tag=>tables.has(tag)))return null;
      const head=tables.get('head'), cmap=tables.get('cmap'), loca=tables.get('loca'), glyf=tables.get('glyf'), maxp=tables.get('maxp');
      if (!head || head.size<54 || !cmap || cmap.size<4 || !loca || !glyf || !maxp || maxp.size<6) return null;
      const units=v.getUint16(head.offset+18), glyphCount=v.getUint16(maxp.offset+4), longLoca=v.getInt16(head.offset+50);
      if (units<16 || units>16384 || ![0,1].includes(longLoca) || loca.size<(glyphCount+1)*(longLoca?4:2)) return null;
      const boxAt=p=>[0,1,2,3].map(i=>v.getInt16(p+i*2)/units), box=boxAt(head.offset+36);
      if (!finite(box) || box[0]>box[2] || box[1]>box[3] || box.some(n=>Math.abs(n)>64)) return null;
      const maps=[], records=v.getUint16(cmap.offset+2);
      if (4+records*8>cmap.size) return null;
      for (let i=0;i<records;i++) {
        const p=cmap.offset+4+i*8, platform=v.getUint16(p), encoding=v.getUint16(p+2), relative=v.getUint32(p+4);
        if (!(platform===0 || platform===3 && [1,10].includes(encoding)) || relative+2>cmap.size) continue;
        const start=cmap.offset+relative, format=v.getUint16(start);
        if (format===4 && relative+4<=cmap.size) {
          const length=v.getUint16(start+2);
          if (length>=16 && relative+length<=cmap.size) maps.push({start,end:start+length,format});
        } else if (format===12 && relative+16<=cmap.size) {
          const length=v.getUint32(start+4), groups=v.getUint32(start+12);
          if (length>=16 && relative+length<=cmap.size && groups<100000 && 16+groups*12<=length) maps.unshift({start,end:start+length,format,groups});
        }
      }
      function glyphId(code) {
        for (const m of maps) {
          const p=m.start;
          if (m.format===12) {
            for (let i=0;i<m.groups;i++) {
              const q=p+16+i*12, start=v.getUint32(q), end=v.getUint32(q+4);
              if (code>=start && code<=end) { const id=v.getUint32(q+8)+code-start;return id<glyphCount?id:0; }
            }
          } else if (code<=65535) {
            const n=v.getUint16(p+6)/2, ends=p+14, starts=ends+n*2+2, deltas=starts+n*2, offsets=deltas+n*2;
            if (!Number.isInteger(n) || offsets+n*2>m.end) continue;
            for (let i=0;i<n;i++) if (code>=v.getUint16(starts+i*2) && code<=v.getUint16(ends+i*2)) {
              const delta=v.getInt16(deltas+i*2), offset=v.getUint16(offsets+i*2);
              const q=offsets+i*2+offset+(code-v.getUint16(starts+i*2))*2;
              if (offset && (q<offsets+n*2 || q+2>m.end)) return 0;
              const raw=offset?v.getUint16(q):code, id=raw?(raw+delta)&65535:0;
              return id<glyphCount?id:0;
            }
          }
        }
        return 0;
      }
      return {box, glyphBounds(code) {
        const id=glyphId(code);if (!id) return null;
        const location=i=>longLoca?v.getUint32(loca.offset+i*4):v.getUint16(loca.offset+i*2)*2;
        const start=location(id), end=location(id+1);
        if (start===end) return {empty:true,box:[0,0,0,0]};
        if (start>end || end>glyf.size || end-start<10) return null;
        const bounds=boxAt(glyf.offset+start+2);
        return finite(bounds) && bounds[0]<=bounds[2] && bounds[1]<=bounds[3] ? {box:bounds} : null;
      }};
    } catch (_) { return null; }
  }

  function tileGeometry(transform, fontSize, x, y, bounds) {
    if (!finite([...transform,fontSize,x,y,...bounds]) || !(fontSize>0)) return null;
    const device=product(transform,[fontSize,0,0,-fontSize,x,y]);
    if (!finite(device) || device[0]*device[3]-device[1]*device[2]===0) return null;
    const corners=[[bounds[0],bounds[1]],[bounds[2],bounds[1]],[bounds[2],bounds[3]],[bounds[0],bounds[3]]].map(p=>point(device,...p));
    const left=Math.floor(Math.min(...corners.map(p=>p[0])))-3, top=Math.floor(Math.min(...corners.map(p=>p[1])))-3;
    const width=Math.ceil(Math.max(...corners.map(p=>p[0])))+3-left, height=Math.ceil(Math.max(...corners.map(p=>p[1])))+3-top;
    if (!(width>0 && height>0 && width<=2048 && height<=2048 && width*height<=1048576)) return null;
    return {left,top,width,height,matrix:[...device.slice(0,4),device[4]-left,device[5]-top]};
  }

  function createRenderer(native, options={}) {
    const makeCanvas=options.makeCanvas || ((width,height)=>{const c=root.document.createElement('canvas');c.width=width;c.height=height;return c;});
    const maximumBytes=options.maximumBytes || 64*1024*1024, fonts=new Map(), tiles=new Map();
    const stats={fonts:0,fontBytes:0,tiles:0,tileBytes:0,hits:0,misses:0,painted:0,prepared:0,primitivePainted:0,recipeHits:0,recipeMisses:0,recipeResets:0,emptyGlyphs:0,fallbacks:0,evictions:0,bitmapTransfers:0,bitmapCloses:0,errors:[],closed:false};
    // Weak source-glyph keys, two exact phases each, and a global ceiling.
    // A reset only loses derived work; the ordinary tile path remains valid.
    let recipes=new WeakMap(),recipeVariants=0,tileSerial=0;
    const tileIdentities=new WeakMap();
    const resetRecipes=()=>{recipes=new WeakMap();recipeVariants=0;stats.recipeResets++;};
    const tokenObject=token=>token!==null && typeof token==='object';
    function seedRecipe(token,request,transform,geometry,key,fontMapKey,record,tile) {
      if(!tokenObject(token) || !request.preparation || tiles.get(key)!==tile)return;
      const visible={...request,preparation:false};
      if(Reflect.ownKeys(visible).some(key=>typeof key!=='string' || visible[key]!==null && !['undefined','string','number','boolean'].includes(typeof visible[key])))return;
      let variants=recipes.get(token) || [];
      const keys=Object.keys(visible),matrix=[transform.a,transform.b,transform.c,transform.d,transform.e,transform.f];
      const existing=variants.findIndex(d=>keys.length===d.keys.length && keys.every(key=>Object.hasOwn(d.request,key) && Object.is(visible[key],d.request[key]))
        && matrix.every((value,index)=>Object.is(value,d.transform[index])));
      if(existing<0 && variants.length<2 && recipeVariants>=8192){resetRecipes();variants=[];}
      let tileId=tileIdentities.get(tile);
      if(tileId===undefined){tileId=++tileSerial;tileIdentities.set(tile,tileId);}
      // Values retain numbers/strings only: no owning reference to a font,
      // source glyph, tile, Canvas or bitmap survives a cache eviction.
      const descriptor={request:Object.freeze(visible),keys,transform:matrix,
        geometry:{left:geometry.left,top:geometry.top,width:geometry.width,height:geometry.height,matrix:[...geometry.matrix]},
        key,fontMapKey,fontId:record.id,tileId};
      if(existing<0 && variants.length<2)recipeVariants++;
      variants=[descriptor,...variants.filter((_,index)=>index!==existing)].slice(0,2);recipes.set(token,variants);
    }
    function preparedRecipe(token,request,context) {
      const variants=tokenObject(token) && recipes.get(token);
      if(!variants)return null;
      const t=context.getTransform(),matrix=[t.a,t.b,t.c,t.d,t.e,t.f],keys=Object.keys(request);
      for(const descriptor of variants) {
        // All six values (including translation and signed zero) must match:
        // sharing a tile key alone does not prove the same integer draw origin.
        if(keys.length!==descriptor.keys.length || !descriptor.keys.every(key=>Object.hasOwn(request,key) && Object.is(request[key],descriptor.request[key]))
            || !matrix.every((value,index)=>Object.is(value,descriptor.transform[index])))continue;
        const record=fonts.get(descriptor.fontMapKey),tile=tiles.get(descriptor.key);
        if(record?.id===descriptor.fontId && tile && tileIdentities.get(tile)===descriptor.tileId && !tile.closed)return {descriptor,record,tile};
      }
      return null;
    }
    const errorRecord=error=>{stats.errors.push(String(error));if(stats.errors.length>32)stats.errors.shift();};
    let serial=0, configPointer=0, scratch;
    const check=(ok,message)=>{if(!ok)throw Error(message);};
    const alloc=n=>{const p=native._malloc(n);check(p,'PDFium allocation failed');native.HEAPU8.fill(0,p,p+n);return p;};
    const free=p=>{if(p)native._free(p);};
    const data=()=>new DataView(native.HEAPU8.buffer);
    function temporary(n,fn){const p=alloc(n);try{return fn(p);}finally{free(p);}}
    function floats(values,fn){return temporary(values.length*4,p=>{values.forEach((v,i)=>data().setFloat32(p+i*4,v,true));return fn(p);});}
    const required=['FPDF_InitLibraryWithConfig','FPDF_DestroyLibrary','FPDF_CreateNewDocument','FPDF_CloseDocument','FPDFPage_New','FPDF_ClosePage',
      'FPDFText_LoadFont','FPDFFont_Close','FPDFPageObj_CreateTextObj','FPDFPageObj_Destroy','FPDFPageObj_SetMatrix','FPDFPageObj_SetFillColor','FPDFText_SetText',
      'FPDFPage_InsertObject','FPDFBitmap_CreateEx','FPDFBitmap_FillRect','FPDFBitmap_GetBuffer','FPDFBitmap_GetStride','FPDFBitmap_Destroy','FPDF_RenderPageBitmapWithMatrix'];
    required.forEach(name=>check(typeof native['_'+name]==='function','Missing PDFium text API: '+name));
    if (options.initialize!==false) {
      configPointer=alloc(32);data().setInt32(configPointer,2,true);
      try{native._FPDF_InitLibraryWithConfig(configPointer);}catch(error){free(configPointer);configPointer=0;throw error;}
    }
    function releaseTile(tile) {
      if(tile.imageBitmap && !tile.closed){
        tile.closed=true;
        try{tile.canvas.close();}catch(error){errorRecord(error);}finally{stats.bitmapCloses++;}
      }
    }
    function scratchSurface(width,height) {
      if(scratch===undefined){
        scratch=null;
        try{
          const canvas=options.makeScratch?options.makeScratch():typeof root.OffscreenCanvas==='function'?new root.OffscreenCanvas(1,1):null;
          if(canvas && typeof canvas.transferToImageBitmap==='function'){
            const context=canvas.getContext('2d',{willReadFrequently:true});if(context)scratch={canvas,context};
          }
        }catch(error){errorRecord(error);}
      }
      if(scratch){if(scratch.canvas.width!==width)scratch.canvas.width=width;if(scratch.canvas.height!==height)scratch.canvas.height=height;}
      return scratch;
    }
    function dropTiles(fontId) {
      for(const [key,tile] of tiles)if(fontId===undefined || tile.fontId===fontId){stats.tileBytes-=tile.bytes;tiles.delete(key);releaseTile(tile);}
      stats.tiles=tiles.size;
    }
    function closeFont(record) {
      resetRecipes();
      dropTiles(record.id);
      const errors=[];
      for(const [handle,close] of [[record.page,'_FPDF_ClosePage'],[record.font,'_FPDFFont_Close'],[record.doc,'_FPDF_CloseDocument']])
        if(handle)try{native[close](handle);}catch(error){errors.push(String(error));}
      errors.forEach(errorRecord);
    }
    function registerFont(font,bytes,metrics=trueType(bytes)) {
      const key=fontKey(font), prior=fonts.get(key);
      if(stats.closed)return false;
      if(prior?.dataUrl===font.dataUrl)return true;
      if(prior){closeFont(prior);fonts.delete(key);stats.fontBytes-=prior.bytes;stats.fonts=fonts.size;}
      if(!metrics || fonts.size>=128 || stats.fontBytes+bytes.length>32*1024*1024)return false;
      const record={id:++serial,dataUrl:font.dataUrl,metrics,bytes:bytes.length,painted:0,prepared:0,characters:new Set(),doc:0,font:0,page:0,object:0};
      let owned=false;
      try {
        record.doc=native._FPDF_CreateNewDocument();check(record.doc,'PDFium font document unavailable');
        record.font=temporary(bytes.length,p=>{native.HEAPU8.set(bytes,p);return native._FPDFText_LoadFont(record.doc,p,bytes.length,2,1);});
        check(record.font,'PDFium rejected the registered TrueType font');
        record.margin=Math.ceil(Math.max(4,...metrics.box.map(Math.abs)))+2;
        record.page=native._FPDFPage_New(record.doc,0,record.margin*2,record.margin*2);check(record.page,'PDFium glyph page unavailable');
        record.object=native._FPDFPageObj_CreateTextObj(record.doc,record.font,1);check(record.object,'PDFium glyph object unavailable');owned=true;
        check(native._FPDFPageObj_SetFillColor(record.object,0,0,0,255),'PDFium glyph fill unavailable');
        floats([1,0,0,1,record.margin,record.margin],p=>check(native._FPDFPageObj_SetMatrix(record.object,p),'PDFium glyph matrix unavailable'));
        const inserted=native._FPDFPage_InsertObject(record.page,record.object);owned=false;check(inserted,'PDFium consumed but rejected glyph object');
        fonts.set(key,record);stats.fonts=fonts.size;stats.fontBytes+=bytes.length;return true;
      } catch(error) {
        if(owned)try{native._FPDFPageObj_Destroy(record.object);}catch(cleanupError){errorRecord(cleanupError);}
        closeFont(record);errorRecord(error);return false;
      }
    }
    function raster(record,text,geometry) {
      temporary((text.length+1)*2,p=>{for(let i=0;i<text.length;i++)data().setUint16(p+i*2,text.charCodeAt(i),true);check(native._FPDFText_SetText(record.object,p),'PDFium glyph mapping failed');});
      const {width,height}=geometry, bitmap=native._FPDFBitmap_CreateEx(width,height,2,0,0);check(bitmap,'PDFium glyph bitmap unavailable');
      try {
        check(native._FPDFBitmap_FillRect(bitmap,0,0,width,height,0xffffffff),'PDFium glyph background unavailable');
        // WithMatrix applies the private page's default display matrix first:
        // [1,0,0,-1,0,pageHeight]. Cancel that y flip/height translation before
        // removing our object margin; geometry.matrix already owns device y.
        const m=product(geometry.matrix,[1,0,0,-1,-record.margin,record.margin]);
        floats(m,matrix=>floats([0,0,width,height],clip=>native._FPDF_RenderPageBitmapWithMatrix(bitmap,record.page,matrix,clip,1)));
        const pointer=native._FPDFBitmap_GetBuffer(bitmap),stride=native._FPDFBitmap_GetStride(bitmap);
        check(pointer && stride>=width*3,'PDFium glyph buffer unavailable');
        // These tiny surfaces receive CPU pixels once and are then copied at
        // 1:1. A software-backed surface avoids thousands of GPU allocations
        // and read/write synchronization stalls during the first real page.
        const reusable=scratchSurface(width,height),canvas=reusable?.canvas || makeCanvas(width,height);
        const context=reusable?.context || canvas.getContext('2d',{willReadFrequently:true}),image=context.createImageData(width,height);
        for(let y=0;y<height;y++)for(let x=0;x<width;x++){
          const source=pointer+y*stride+x*3,dest=(y*width+x)*4,gray=native.HEAPU8[source];
          check(gray===native.HEAPU8[source+1] && gray===native.HEAPU8[source+2],'Unsupported colored glyph coverage');
          image.data[dest+3]=255-gray;
        }
        context.putImageData(image,0,0);
        if(reusable){
          try{
            const bitmap=canvas.transferToImageBitmap();stats.bitmapTransfers++;
            return {canvas:bitmap,imageBitmap:true,fontId:record.id,bytes:width*height*4};
          }catch(error){
            errorRecord(error);scratch=null;canvas.width=0;canvas.height=0;
            const fallback=makeCanvas(width,height);fallback.getContext('2d',{willReadFrequently:true}).putImageData(image,0,0);
            return {canvas:fallback,fontId:record.id,bytes:width*height*4};
          }
        }
        return {canvas,fontId:record.id,bytes:width*height*4};
      } finally {native._FPDFBitmap_Destroy(bitmap);}
    }
    function drawTile(context,request,record,tile,geometry) {
      try {
        context.save();
        try {context.setTransform(1,0,0,1,0,0);context.drawImage(tile.canvas,geometry.left,geometry.top);}
        finally {context.restore();}
      }finally{if(!tile.cached)releaseTile(tile);}
      if(request.preparation){stats.prepared++;record.prepared++;}
      else{stats.painted++;record.painted++;record.characters.add(request.text.codePointAt(0));}
      return true;
    }
    function paint(context,request) {return paintCurrent(context,request);}
    function paintCurrent(context,request,admitted=false,seedToken) {
      const fontMapKey=fontKey({family:request.family,weight:request.weight,style:request.style}),record=fonts.get(fontMapKey);
      if(stats.closed || !record || Array.from(request.text || '').length!==1 || request.method!=='fillText'
          || !['#000000','#000','black','rgb(0, 0, 0)'].includes(request.fill)
          || !admitted && !supportedPaintContext(context)
          || request.unsupported){stats.fallbacks++;return false;}
      try {
        const bounds=record.metrics.glyphBounds(request.text.codePointAt(0));if(!bounds){stats.fallbacks++;return false;}
        if(bounds.empty){stats.emptyGlyphs++;return true;}
        const t=context.getTransform(),geometry=tileGeometry([t.a,t.b,t.c,t.d,t.e,t.f],request.fontSize,request.x,request.y,bounds.box);
        if(!geometry){stats.fallbacks++;return false;}
        const key=JSON.stringify([record.id,request.text,geometry.width,geometry.height,...geometry.matrix]);
        let tile=tiles.get(key);
        if(tile){tiles.delete(key);tiles.set(key,tile);stats.hits++;}
        else {
          stats.misses++;tile=raster(record,request.text,geometry);
          while(tiles.size && stats.tileBytes+tile.bytes>maximumBytes){const first=tiles.keys().next().value,old=tiles.get(first);stats.tileBytes-=old.bytes;tiles.delete(first);releaseTile(old);stats.evictions++;}
          stats.tiles=tiles.size;
          if(tile.bytes<=maximumBytes){tile.cached=true;tiles.set(key,tile);stats.tileBytes+=tile.bytes;stats.tiles=tiles.size;}
        }
        const painted=drawTile(context,request,record,tile,geometry);
        if(seedToken)try{seedRecipe(seedToken,request,t,geometry,key,fontMapKey,record,tile);}catch(_){resetRecipes();}
        return painted;
      }catch(error){errorRecord(error);stats.fallbacks++;return false;}
    }
    function retainFamilies(families) {
      const keep=new Set(families);
      for(const [key,record] of fonts)if(!keep.has(JSON.parse(key)[0])){closeFont(record);fonts.delete(key);stats.fontBytes-=record.bytes;}
      stats.fonts=fonts.size;
    }
    // null means that no native attempt occurred. false means paint() already
    // recorded one failed attempt: the caller must use the stock browser fill,
    // not retry through withFillPainter and count the same fallback twice.
    function paintPrimitiveFill(context,incoming,token) {
      // Finish all caller-controlled scalar reads before native state admission.
      const request={...incoming};
      if(Reflect.ownKeys(request).some(key=>typeof key!=='string' || request[key]!==null && !['undefined','string','number','boolean'].includes(typeof request[key]))
          || typeof NativeContext!=='function' || !(context instanceof NativeContext)
          || Object.getPrototypeOf(context)!==nativeContextPrototype
          || customPaintDepth || preparationContexts.has(context) || preparationRequests.has(context) || facades.get(context)?.request
          || request.method!=='fillText' || request.unsupported || request.preparation
          || !['#000000','#000','black','rgb(0, 0, 0)','rgb(0,0,0)'].includes(request.fill)
          || typeof request.text!=='string' || Array.from(request.text).length!==1
          || !finite([request.fontSize,request.x,request.y]) || !(request.fontSize>0)
          || nativeContextMethods.some(([name,method])=>typeof method!=='function' || context[name]!==method)
          || primitiveContextStateKeys.some(name=>Object.hasOwn(context,name)) || !supportedPaintContext(context))return null;
      // These finite CSS black spellings all read back as #000000 after the
      // stock Canvas.fillStyle setter. Keep paint()'s existing request contract.
      request.fill='#000000';
      let painted;
      try {
        const prepared=!stats.closed && preparedRecipe(token,request,context);
        if(prepared) {
          const {descriptor,record,tile}=prepared;
          tiles.delete(descriptor.key);tiles.set(descriptor.key,tile);stats.hits++;stats.recipeHits++;
          painted=drawTile(context,request,record,tile,descriptor.geometry);
        } else {
          if(tokenObject(token))stats.recipeMisses++;
          painted=paintCurrent(context,request,true);
        }
      }catch(error){errorRecord(error);stats.fallbacks++;painted=false;}
      if(painted)stats.primitivePainted++;
      return painted;
    }
    function forgetChangedFont(font) {
      const key=fontKey(font),record=fonts.get(key);
      if(record && record.dataUrl!==font.dataUrl){closeFont(record);fonts.delete(key);stats.fontBytes-=record.bytes;stats.fonts=fonts.size;}
    }
    function close() {
      if(stats.closed)return;
      resetRecipes();
      retainFamilies([]);stats.closed=true;
      if(scratch){scratch.canvas.width=0;scratch.canvas.height=0;scratch=null;}
      if(options.initialize!==false)try{native._FPDF_DestroyLibrary();}finally{free(configPointer);configPointer=0;}
    }
    const api={registerFont,paint,paintPrimitiveFill,retainFamilies,forgetChangedFont,close,diagnostics:()=>({...stats,recipeVariants,errors:stats.errors.slice(-12),
      fontPrograms:Array.from(fonts,([key,record])=>({key:JSON.parse(key),byteLength:record.bytes,painted:record.painted,prepared:record.prepared,characters:[...record.characters].sort((a,b)=>a-b)}))})};
    preparationPainters.set(api,(context,request,token)=>paintCurrent(context,request,false,token));
    return api;
  }

  let pending=null,renderer=null,runtimeEpoch=0,customPaintDepth=0;
  const defaultPainter=(context,request)=>renderer?.paint(context,request)===true;
  const startupErrors=[],facades=new WeakMap(),preparationContexts=new WeakSet(),preparationRequests=new WeakMap();
  function withPreparation(context,operation) {
    const nested=preparationContexts.has(context);preparationContexts.add(context);
    try{return operation();}finally{if(!nested)preparationContexts.delete(context);}
  }
  // Capture only the final native fill and every state value read by paint().
  // Warming runs after all Fabric/Canvas scopes unwind. It uses paint()'s
  // unchanged admission, Float64 geometry, native writes and existing cache;
  // the detached preparation target itself never publishes pixels.
  function preparationRequest(context,request,paint,token) {
    try {
      const transform=context.getTransform(),matrix=Object.freeze({a:transform.a,b:transform.b,c:transform.c,d:transform.d,e:transform.e,f:transform.f});
      if(!finite(Object.values(matrix)) || Object.values(request).some(value=>value!==null && !['undefined','string','number','boolean'].includes(typeof value)))return null;
      const saved={getTransform:()=>matrix,save(){},restore(){},setTransform(){},drawImage(){}};
      for(const name of ['font','fillStyle','globalAlpha','globalCompositeOperation','filter','shadowBlur','shadowOffsetX','shadowOffsetY','shadowColor',
        'textBaseline','textAlign','direction','fontVariantCaps','letterSpacing']) {
        const value=context[name];
        if(value!==null && !['undefined','string','number','boolean'].includes(typeof value))return null;
        saved[name]=value;
      }
      return Object.freeze({context:Object.freeze(saved),request:Object.freeze({...request}),paint,...(token?{token}:{})});
    }catch(_){return null;}
  }
  function collectPreparation(context,operation) {
    if(preparationRequests.has(context))throw Error('PDF text preparation collection is already active.');
    const requests=[],owner=renderer,epoch=runtimeEpoch;
    preparationRequests.set(context,requests);
    try {
      withPreparation(context,operation);
      return Object.freeze({requests:Object.freeze(requests),current:()=>renderer===owner && runtimeEpoch===epoch});
    }finally{preparationRequests.delete(context);}
  }
  async function prepareCollectedAsync(collection,options={}) {
    const now=()=>root.performance?.now?.() ?? Date.now(),maxSliceMs=Number.isFinite(options.maxSliceMs)?Math.max(0,options.maxSliceMs):8;
    const yieldToUi=options.yieldToUi || (()=>new Promise(resolve=>setTimeout(resolve,0)));
    const current=()=>{options.signal?.throwIfAborted();options.current?.();if(!collection.current())throw Error('PDF text preparation runtime was retired.');};
    let started=now(),preparedGlyphs=0,uiYieldCount=0;
    for(const entry of collection.requests) {
      current();
      const prepare=entry.paint===defaultPainter && entry.token && !customPaintDepth && preparationPainters.get(renderer);
      const custom=entry.paint!==defaultPainter;if(custom)customPaintDepth++;
      try{if((prepare?prepare(entry.context,entry.request,entry.token):entry.paint(entry.context,entry.request))===true)preparedGlyphs++;}
      finally{if(custom)customPaintDepth--;}
      if(now()-started>=maxSliceMs){current();await yieldToUi();current();uiYieldCount++;started=now();}
    }
    current();return {preparedGlyphs,uiYieldCount};
  }
  function withFillPainter(context,request,operation,paint=defaultPainter,token) {
    const custom=paint!==defaultPainter;if(custom)customPaintDepth++;
    try {
    if(request.method!=='fillText' || request.unsupported)return operation(context);
    let state=facades.get(context);
    if(!state){
      state={request:null,methods:new Map()};
      state.proxy=new Proxy(context,{
        get(target,key){
          if(key==='fillText')return (text,x,y,...rest)=>{
            const current=state.request;
            if(!rest.length && current) {
              const request={...current,text,x,y,fill:target.fillStyle,preparation:preparationContexts.has(target)};
              const pending=preparationRequests.get(target),entry=pending && preparationRequest(target,request,state.paint,state.token);
              if(entry){pending.push(entry);return;}
              if(state.paint(target,request)===true)return;
            }
            return target.fillText(text,x,y,...rest);
          };
          const value=Reflect.get(target,key,target);
          if(typeof value!=='function')return value;
          if(!state.methods.has(key) || state.methods.get(key).original!==value)state.methods.set(key,{original:value,bound:value.bind(target)});
          return state.methods.get(key).bound;
        },
        set(target,key,value){return Reflect.set(target,key,value,target);}
      });
      facades.set(context,state);
    }
    const previous=state.request,previousPainter=state.paint,previousToken=state.token;state.request=request;state.paint=paint;
    state.token=!customPaintDepth && paint===defaultPainter?token:null;
    try{return operation(state.proxy);}finally{state.request=previous;state.paint=previousPainter;state.token=previousToken;}
    }finally{if(custom)customPaintDepth--;}
  }
  async function engine() {
    if(renderer)return renderer;
    if(!pending){const issued=runtimeEpoch;pending=(async()=>{
      if(!scriptUrl)throw Error('PDFium text module has no local resource base');
      const url=new URL('../vendor/pdfium/pdfium.esm.js',scriptUrl),wasm=new URL('pdfium.wasm',url);
      const factory=(await import(url.href)).default;
      const native=await factory({locateFile:name=>{if(name!=='pdfium.esm.wasm')throw Error('Unexpected PDFium resource');return wasm.href;}});
      const current=createRenderer(native);
      if(issued!==runtimeEpoch){current.close();throw Error('PDFium text initialization was retired');}
      renderer=current;return renderer;
    })();}
    const attempt=pending;
    try{return await attempt;}finally{if(!renderer && pending===attempt)pending=null;}
  }
  // A retained active family must survive another tab's close while loading.
  // Each pending registration is cancelled only when its own family retires.
  function createFontRegistry(loadRenderer,peekRenderer=()=>null) {
    const registrations=new Set();let currentRenderer=null;
    async function registerFont(font,options={}) {
      options.current?.();
      const descriptor=Object.freeze({family:font?.family,weight:font?.weight,style:font?.style,dataUrl:font?.dataUrl});
      if(!descriptor.family || !/^data:[^,]+;base64,/i.test(descriptor.dataUrl || ''))return false;
      (currentRenderer || peekRenderer())?.forgetChangedFont(descriptor);
      const token={family:descriptor.family,cancelled:false};registrations.add(token);
      try {
        let bytes;
        try{const binary=root.atob(descriptor.dataUrl.slice(descriptor.dataUrl.indexOf(',')+1));bytes=Uint8Array.from(binary,c=>c.charCodeAt(0));}
        catch(_){return false;}
        const metrics=trueType(bytes);
        if(!metrics)return false;
        let loaded;
        try{loaded=await loadRenderer();}
        catch(error){startupErrors.push(String(error));if(startupErrors.length>12)startupErrors.shift();options.current?.();return false;}
        options.current?.();
        if(token.cancelled)return false;
        currentRenderer=loaded;
        return loaded.registerFont(descriptor,bytes,metrics);
      }finally{registrations.delete(token);}
    }
    function retainFamilies(families) {
      const keep=new Set(families);
      for(const token of registrations)if(!keep.has(token.family))token.cancelled=true;
      (currentRenderer || peekRenderer())?.retainFamilies(keep);
    }
    function cancelAll(){for(const token of registrations)token.cancelled=true;currentRenderer=null;}
    return {registerFont,retainFamilies,cancelAll};
  }
  const registry=createFontRegistry(engine,()=>renderer);
  function close(){registry.cancelAll();runtimeEpoch++;try{renderer?.close();}finally{renderer=null;pending=null;}}
  if(root.addEventListener)root.addEventListener('pagehide',event=>{if(!event.persisted)close();});
  return {trueType,tileGeometry,createRenderer,createFontRegistry,registerFont:registry.registerFont,withFillPainter,withPreparation,collectPreparation,prepareCollectedAsync,paint:(context,request)=>renderer?.paint(context,request)===true,
    paintPrimitiveFill:(context,request,token)=>renderer?.paintPrimitiveFill(context,request,token) ?? null,
    retainFamilies:registry.retainFamilies,close,diagnostics:()=>({...renderer?.diagnostics(),ready:Boolean(renderer),startupErrors:[...startupErrors]})};
});
