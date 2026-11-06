"""Use the maintained passive observer with an independent path-interior oracle."""
import base64
from copy import deepcopy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OBSERVER = (ROOT / 'scripts/action-paint-observer.js').read_text(encoding='utf-8')
PROBES = r'''({before,expected})=>{
 const ctx=document.createElement('canvas').getContext('2d');
 const prepare=rows=>rows.map(o=>{
   const [a,b,c,d,e,f]=o.matrix,det=a*d-b*c;
   const inverse=[d/det,-b/det,-c/det,a/det,(c*f-d*e)/det,(b*e-a*f)/det];
   const path=new Path2D(o.path.map(c=>c.join(' ')).join(' '));
   const raw=o.paint.fill,rgba=raw.match(/^rgba?\(([^)]+)\)$/);
   const color=rgba?rgba[1].split(',').map(Number):/^#[0-9a-f]{6}$/i.test(raw)?[1,3,5].map(i=>parseInt(raw.slice(i,i+2),16)):null;
   if(!color)throw Error('Unsupported path-oracle fill '+raw);
   if(color.length===3)color.push(1);
   return {...o,inverse,shape:path,color,pad:5*Math.max(Math.hypot(...inverse.slice(0,2)),Math.hypot(...inverse.slice(2,4)))};
 });
 const old=prepare(before),next=prepare(expected),all=[...old,...next];
 const bounds=all.flatMap(o=>o.path.flatMap(c=>{const p=[];for(let i=1;i+1<c.length;i+=2){const x=c[i]-o.offset.x,y=c[i+1]-o.offset.y,m=o.matrix;p.push([m[0]*x+m[2]*y+m[4],m[1]*x+m[3]*y+m[5]]);}return p;}));
 const minX=Math.min(...bounds.map(p=>p[0]))-8,maxX=Math.max(...bounds.map(p=>p[0]))+8;
 const minY=Math.min(...bounds.map(p=>p[1]))-8,maxY=Math.max(...bounds.map(p=>p[1]))+8;
 const local=(o,x,y)=>[o.inverse[0]*x+o.inverse[2]*y+o.inverse[4]+o.offset.x,o.inverse[1]*x+o.inverse[3]*y+o.inverse[5]+o.offset.y];
 const probes=[];
 for(let y=minY;y<maxY;y+=5)for(let x=minX;x<maxX;x+=5){
   if(all.some(o=>{ctx.lineWidth=2*o.pad;return ctx.isPointInStroke(o.shape,...local(o,x,y));}))continue;
   let rgb=[255,255,255];
   for(const o of next)if(ctx.isPointInPath(o.shape,...local(o,x,y)))rgb=rgb.map((c,i)=>Math.round(c*(1-o.color[3])+o.color[i]*o.color[3]));
   probes.push({x,y,rgb});
 }
 // Establish that the current, untouched buffer is insufficient for the target.
 const lower=document.querySelector('canvas.lower-canvas'),canvas=FigureStudio.app.getObjectByIdForQa(before[0].id).canvas;
 const pixels=lower.getContext('2d').getImageData(0,0,lower.width,lower.height).data,m=canvas.viewportTransform;
 let staleMismatches=0;
 for(const p of probes){const x=Math.round((m[0]*p.x+m[2]*p.y+m[4])*lower.width/canvas.width),y=Math.round((m[1]*p.x+m[3]*p.y+m[5])*lower.height/canvas.height),i=(y*lower.width+x)*4;
   if(p.rgb.some((c,k)=>Math.abs(c-pixels[i+k])>2))staleMismatches++;
 }
 return {probes,staleMismatches,policy:'5-unit finite grid, exclude5 world units about both old/new path boundaries, ordinary source-over fill over white, native Path2D point queries only; no painting or rendered-image oracle.'};
}'''


def translated(records, object_index, operands, delta):
    result = deepcopy(records)
    target = result[object_index]
    a,b,c,d,_,_ = target['matrix']
    determinant = a*d-b*c
    dx,dy = (d*delta[0]-c*delta[1])/determinant, (-b*delta[0]+a*delta[1])/determinant
    for command, operand in operands:
        target['path'][command][operand] += dx
        target['path'][command][operand+1] += dy
    return result


def model(records):
    targets = []
    for row in records:
        a,b,c,d,e,f = row['matrix']
        points = []
        for index, command in enumerate(row['path']):
            for operand in range(1,len(command)-1,2):
                x,y=command[operand]-row['offset']['x'],command[operand+1]-row['offset']['y']
                points.append([index,operand,a*x+c*y+e,b*x+d*y+f])
        targets.append(dict(id=row['id'],points=points))
    return '''const expected=%s;return expected.every(t=>{const o=rows.find(o=>o?.id===t.id);if(!o)return false;const [a,b,c,d,e,f]=o.matrix;
 return t.points.every(([i,j,wx,wy])=>{const p=o.path?.[i];if(!p)return false;const x=p[j]-o.pathOffset.x,y=p[j+1]-o.pathOffset.y;return Math.abs(a*x+c*y+e-wx)<=.005&&Math.abs(b*x+d*y+f-wy)<=.005;});});''' % json.dumps(targets)


async def observe(case, name, before, expected, event, action, allow_unchanged=False):
    oracle = await case.paint_probes(before,expected) if hasattr(case,'paint_probes') else await case.surface.evaluate(PROBES, dict(before=before, expected=expected))
    case.check(name+' oracle distinguishes the requested artwork from a stale buffer', allow_unchanged or oracle['staleMismatches'] > 0,
               dict(probes=len(oracle['probes']), staleMismatches=oracle['staleMismatches']))
    await case.surface.evaluate(OBSERVER, dict(ids=[row['id'] for row in expected], model=model(expected), event=event,
        deadlineMs=250, diagnosticMs=1000, rectangles=False, probes=oracle['probes']))
    await action()
    result = await case.surface.evaluate('()=>window.__figureActionPaintObservation.done')
    for key in ['beforePng','afterPng']:
        path=case.out/(name+'-'+key+'.png')
        path.write_bytes(base64.b64decode(result[key].split(',',1)[1]))
        result[key]=str(path)
    result['oracle']=dict(probes=len(oracle['probes']), staleMismatches=oracle['staleMismatches'], policy=oracle['policy'])
    case.row.setdefault('actions',[]).append(dict(name=name,**result))
    case.save()
    case.check(name+' completes model and natural first paint within250ms and remains correct',result['passed'],
        {key:result[key] for key in ['classification','modelCompleteMs','firstCorrectPaintMs','sustainedCorrectPaintMs','stablePaintMs','observerError']})
    return result
