/* Test-only read-only observer. It never asks the editor to paint.
 * Rectangle interiors/background/old locations use an analytic geometry oracle;
 * other fixtures supply explicit interior probes. PNGs precede page screenshots.
 */
(config) => {
  const app = FigureStudio.app, lower = document.querySelector("canvas.lower-canvas");
  const ctx = lower.getContext("2d"), owner = app.getObjectByIdForQa(config.ids[0]);
  const probeCanvas = document.createElement("canvas");
  const probeContext = probeCanvas.getContext("2d", { willReadFrequently: false,
    colorSpace: ctx.getContextAttributes?.().colorSpace || "srgb" });
  const canvas = owner.canvas, vpt = [...canvas.viewportTransform];
  const sx = lower.width / canvas.width, sy = lower.height / canvas.height;
  const read = () => config.ids.map(id => {
    const o = app.getObjectByIdForQa(id);
    if (!o) return null;
    let visible = o.visible !== false;
    for (let p = o.group; p; p = p.group) visible &&= p.visible !== false;
    return { id, type: o.type.toLowerCase(), width: o.width, height: o.height,
      fill: o.fill, stroke: o.stroke, strokeWidth: o.strokeWidth, visible,
      matrix: [...o.calcTransformMatrix()], path: o.path ? structuredClone(o.path) : null,
      pathOffset: o.pathOffset ? {x:o.pathOffset.x,y:o.pathOffset.y} : null,
      text: o.text,isEditing:Boolean(o.isEditing),fontSize:o.fontSize,fontFamily:o.fontFamily };
  });
  const inverse = m => {
    const d = m[0]*m[3]-m[1]*m[2];
    return [m[3]/d,-m[1]/d,-m[2]/d,m[0]/d,(m[2]*m[5]-m[3]*m[4])/d,(m[1]*m[4]-m[0]*m[5])/d];
  };
  const point = (m,x,y) => [m[0]*x+m[2]*y+m[4],m[1]*x+m[3]*y+m[5]];
  const rgb = c => /^#[0-9a-f]{6}$/i.test(c || "") ? [1,3,5].map(i=>parseInt(c.slice(i,i+2),16)) : null;
  const before = read(), beforePng = lower.toDataURL("image/png");
  const predicate = new Function("rows","before","app",config.model);
  const iv = inverse(vpt);
  let started = null, modelAt = null, firstPaint = null, stableAt = null, consecutive = 0, stableRunStart = null;
  let last = null, raf = null, ended = false, requestedEvent = null;
  const samples = [], longTasks = [];
  const performanceObserver = new PerformanceObserver(list => {
    for (const e of list.getEntries()) longTasks.push({startTime:e.startTime,duration:e.duration});
  });
  performanceObserver.observe({type:"longtask"});
  let resolve;
  const done = new Promise(r=>resolve=r);
  function assess(rows) {
    let checked = 0, mismatches = 0, example = null, missingInteriors = [];
    const interiors = {}, probes = [];
    function probe(x,y,color) {
      const [vx,vy] = point(vpt,x,y), px = Math.round(vx*sx), py = Math.round(vy*sy);
      if (px<1 || py<1 || px>=lower.width-1 || py>=lower.height-1) throw Error("Paint probe outside artboard.");
      probes.push({x,y,px,py,color});
    }
    if (config.probes) for(const p of config.probes) probe(p.x,p.y,p.rgb);
    if (config.rectangles !== false) {
      const shapes = config.expectedRects || rows.filter(o=>o?.visible && o.type==="rect");
      const all = [...before.filter(o=>o?.type==="rect"),...shapes];
      const bounds=all.flatMap(o=>[[-o.width/2,-o.height/2],[-o.width/2,o.height/2],
        [o.width/2,-o.height/2],[o.width/2,o.height/2]].map(p=>point(o.matrix,...p)));
      const minX=Math.min(...bounds.map(p=>p[0]))-12,maxX=Math.max(...bounds.map(p=>p[0]))+12;
      const minY=Math.min(...bounds.map(p=>p[1]))-12,maxY=Math.max(...bounds.map(p=>p[1]))+12;
      const prepared=shapes.map(o=>({...o,inverse:inverse(o.matrix),rgb:rgb(o.fill)}));
      if (prepared.some(o=>!o.rgb)) throw Error("Rectangle oracle needs opaque six-digit fill colors.");
      for(let y=minY;y<maxY;y+=13) for(let x=minX;x<maxX;x+=13) {
        let color=[255,255,255],boundary=false,paintedId=null;
        for(const o of prepared) {
          const [lx,ly]=point(o.inverse,x,y);
          const dx=Math.abs(lx)-o.width/2,dy=Math.abs(ly)-o.height/2;
          // Exclude both sides of edges/strokes; never relax solid interiors.
          const pad=8+Number(o.strokeWidth||0);
          if ((Math.abs(dx)<pad && dy<pad)||(Math.abs(dy)<pad && dx<pad)) boundary=true;
          if(dx<0 && dy<0){color=o.rgb;paintedId=o.id;}
        }
        if(!boundary) {
          probe(x,y,color);
          if(paintedId)interiors[paintedId]=(interiors[paintedId]||0)+1;
        }
      }
      missingInteriors=(config.requiredPaintIds||prepared.map(o=>o.id)).filter(id=>!interiors[id]);
    }
    // Copy every original 3x3 footprint, without scaling, into one small GPU
    // surface. Read it once instead of reading the entire display canvas.
    // Probe positions, RGBA comparisons, ordering and coverage stay unchanged.
    if (probes.length) {
      const columns=Math.min(1024,probes.length), rows=Math.ceil(probes.length/columns);
      if (probeCanvas.width!==columns*3) probeCanvas.width=columns*3;
      if (probeCanvas.height!==rows*3) probeCanvas.height=rows*3;
      probeContext.clearRect(0,0,probeCanvas.width,probeCanvas.height);
      probeContext.imageSmoothingEnabled=false;
      probes.forEach((p,index)=>probeContext.drawImage(lower,p.px-1,p.py-1,3,3,(index%columns)*3,Math.floor(index/columns)*3,3,3));
      const image=probeContext.getImageData(0,0,probeCanvas.width,probeCanvas.height).data;
      probes.forEach((p,index)=>{
        const x=(index%columns)*3,y=Math.floor(index/columns)*3;
        for(let dy=0;dy<3;dy++)for(let dx=0;dx<3;dx++){
          const offset=((y+dy)*probeCanvas.width+x+dx)*4;checked++;
          if(p.color.some((c,i)=>Math.abs(image[offset+i]-c)>2)||image[offset+3]!==255){
            mismatches++;example ||= {scene:[p.x,p.y],pixel:[p.px+dx-1,p.py+dy-1],expected:p.color,actual:[...image.slice(offset,offset+4)]};
          }
        }
      });
    }
    return {checked,mismatches,example,interiors,missingInteriors,passed:checked>=9 && mismatches===0 && missingInteriors.length===0};
  }
  function capturePng() {
    if(typeof lower.toBlob!=="function"||typeof FileReader!=="function"){
      try{return Promise.resolve(lower.toDataURL("image/png"));}catch(error){return Promise.reject(error);}
    }
    // toBlob snapshots the existing bitmap at this call; encoding is asynchronous.
    return new Promise((resolve,reject)=>lower.toBlob(blob=>{
      try {
        if(!blob){reject(Error("The existing lower-canvas PNG could not be captured."));return;}
        const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(reader.error||Error("PNG read failed"));
        reader.onabort=()=>reject(Error("PNG read aborted"));reader.readAsDataURL(blob);
      }catch(error){reject(error);}
    },"image/png"));
  }
  function finish(reason) {
    if(ended)return;ended=true;cancelAnimationFrame(raf);
    clearTimeout(armDeadline);
    document.removeEventListener(config.event.type,trigger,true);
    for(const e of performanceObserver.takeRecords())longTasks.push({startTime:e.startTime,duration:e.duration});
    performanceObserver.disconnect();
    const elapsed=started===null?null:performance.now()-started;
    const pass=firstPaint!==null && stableRunStart!==null && stableRunStart-started<=config.deadlineMs && stableAt!==null;
    const snapshot={passed:pass,reason,requestedAt:started,requestedEvent,modelCompleteMs:modelAt,
      firstCorrectPaintMs:firstPaint,stablePaintMs:stableAt,elapsedMs:elapsed,
      sustainedCorrectPaintMs:stableRunStart===null?null:stableRunStart-started,
      classification:pass?"PASS":modelAt===null?"MODEL_NOT_COMPLETED":modelAt>config.deadlineMs?"SLOW_COMPUTATION":firstPaint===null?"STALE_OR_WRONG_PAINT":"LATE_OR_UNSTABLE_PAINT",
      before,after:read(),beforePng,samples,
      longTasks:longTasks.filter(e=>started!==null && e.startTime+e.duration>=started),
      renderObservations:app.getCanvasInteractionPerformanceForQa(started||performance.now()),
      selection:app.getSelectionStateForQa(),last,observerError,
      policy:"Action event to first correct existing lower-canvas pixels; three successive correct observations and at least80ms stable. Every original3x3 footprint copied1:1 to a small readback surface; unchanged RGBA/geometry/coverage/time predicates. Original lower-canvas PNG snapshot before screenshots, encoded asynchronously. No render/Fit/Reset/grid/selection rescue."};
    capturePng().then(afterPng=>resolve({...snapshot,afterPng}),error=>resolve({...snapshot,passed:false,
      classification:"OBSERVER_ERROR",observerError:String(error?.stack||error),afterPng:null}));
  }
  let observerError=null;
  function tick() {
    try { sample(); }
    catch(error) { observerError=String(error?.stack||error);finish("observer-error"); }
  }
  function sample() {
    if(ended)return;
    const now=performance.now(),rows=read();
    const unchanged=(config.unchangedIds||[]).every(id=>{
      const index=config.ids.indexOf(id);
      if(index<0)throw Error("Protected object not observed.");
      return JSON.stringify(rows[index])===JSON.stringify(before[index]);
    });
    const complete=predicate(rows,before,app) && unchanged;
    if(complete && modelAt===null)modelAt=now-started;
    last=complete?assess(rows):null;
    const observedAt=performance.now();
    if(samples.length<120)samples.push({ms:observedAt-started,modelComplete:complete,pixels:last});
    if(complete && last.passed) {
      if(firstPaint===null)firstPaint=observedAt-started;
      if(stableRunStart===null)stableRunStart=observedAt;
      consecutive++;
      if(consecutive>=3 && observedAt-stableRunStart>=80){stableAt=observedAt-started;finish("stable");return;}
    } else {consecutive=0;stableRunStart=null;}
    if(observedAt-started>config.diagnosticMs){finish("diagnostic-deadline");return;}
    raf=requestAnimationFrame(tick);
  }
  function trigger(event) {
    if(started!==null || !event.target.closest(config.event.selector) || config.event.key && event.key!==config.event.key)return;
    requestedEvent={type:event.type,key:event.key||null,value:event.target.value??null,trusted:event.isTrusted};
    started=performance.now();raf=requestAnimationFrame(tick);
  }
  document.addEventListener(config.event.type,trigger,true);
  const armDeadline=setTimeout(()=>finish("action-event-missing"),5000);
  window.__figureActionPaintObservation={done,cancel:()=>finish("cancelled")};
  return {armed:true,before,beforePng};
}
