"""Finite compound-contour public geometry witness on clean beta25, with actual Library context."""
import argparse
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


i = load('compound_groups', 'scripts/check-direct-selection-label-interactions-browser.py')
s, m = i.s, i.m


def world(record):
    a, b, c, d, e, f = record['matrix']
    offset = record['offset']
    return {(index, j): (a*(cmd[j]-offset['x'])+c*(cmd[j+1]-offset['y'])+e,
                         b*(cmd[j]-offset['x'])+d*(cmd[j+1]-offset['y'])+f)
            for index, cmd in enumerate(record['path'] or []) for j in range(1, len(cmd)-1, 2)}


def material_point(record,index,t):
    commands=record['path'];command=commands[index];start=commands[index-1][-2:];kind=command[0]
    if kind=='Z':
        previous=index-1
        while commands[previous][0]!='M':previous-=1
        controls=[start,commands[previous][1:3]]
    elif kind=='C':controls=[start,command[1:3],command[3:5],command[5:7]]
    elif kind=='Q':controls=[start,command[1:3],command[3:5]]
    else:controls=[start,command[-2:]]
    while len(controls)>1:controls=[[(1-t)*a[j]+t*b[j] for j in range(2)] for a,b in zip(controls,controls[1:])]
    x,y=controls[0][0]-record['offset']['x'],controls[0][1]-record['offset']['y'];a,b,c,d,e,f=record['matrix']
    return a*x+c*y+e,b*x+d*y+f


def closest_material_t(record,index,point):
    def distance(t):
        at=material_point(record,index,t);return sum((at[j]-point[j])**2 for j in range(2))
    best=min(range(101),key=lambda j:distance(j/100));lo=max(0,(best-1)/100);hi=min(1,(best+1)/100)
    for _ in range(55):
        a=lo+(hi-lo)/3;b=hi-(hi-lo)/3
        if distance(a)<=distance(b):hi=b
        else:lo=a
    return min(.97,max(.03,(lo+hi)/2))


class Compound(i.GroupConsistency):
    same=staticmethod(i.real_asset_equivalent)
    seam=9
    anchor_command=8
    contour_start=5
    hole_point=[50,40]
    border_point=[10,40]
    async def observation(self, name):
        inventory = await self.surface.evaluate(m.g.INVENTORY)
        state = await self.state(name)
        target = await self.surface.evaluate('''({id,hole,border})=>{const o=FigureStudio.app.getObjectByIdForQa(id);
          const path=new Path2D(o.path.map(c=>c.join(' ')).join(' '));
          const ctx=document.createElement('canvas').getContext('2d');
          const active=o.canvas.getActiveObject();
          return {fillRule:o.fillRule,compound:o.figureStudioCompoundPathMeta,
            nativeActive:active?{id:active.figureId||'',type:active.type,selectable:active.selectable,evented:active.evented}:null,
            holeFilled:hole?ctx.isPointInPath(path,...hole,o.fillRule):null,borderFilled:border?ctx.isPointInPath(path,...border,o.fillRule):null,
            ancestors:(()=>{const rows=[];for(let p=o.group;p;p=p.group)rows.push({id:p.figureId,angle:p.angle,scaleX:p.scaleX,scaleY:p.scaleY,flipX:p.flipX,flipY:p.flipY});return rows;})()};}''', {'id':self.leaf_id,'hole':self.hole_point,'border':self.border_point})
        value = {'inventory': inventory, 'state': state, 'target': target, 'artwork': self.row.get('artwork', {})}
        self.row.setdefault('geometry', {})[name] = value
        self.save()
        return value

    def stationary(self, name, before, after):
        old = {o['id']: o for o in before['inventory']['leaves']}
        self.require(name+' preserves the complete native leaf inventory',set(old)=={o['id'] for o in after['inventory']['leaves']})
        errors = []
        for o in after['inventory']['leaves']:
            prior = old[o['id']]
            if o['id'] == self.leaf_id:
                continue
            if any(o.get(k) != prior.get(k) for k in ['path','text','parent','fill','stroke','strokeWidth']):
                errors.append({'id':o['id'],'reason':'native content'})
            left, right = world(prior), world(o)
            if left.keys()!=right.keys() or any(max(abs(a-b) for a,b in zip(left[k],right[k]))>1e-6 for k in left):
                errors.append({'id':o['id'],'reason':'world operands'})
            if not prior['path'] and any(abs(a-b)>1e-6 for a,b in zip(prior['matrix'],o['matrix'])):
                errors.append({'id':o['id'],'reason':'native pose'})
        self.require(name+' preserves all actual Library neighbors', not errors, errors)
        prior = old[self.leaf_id]
        current = next(o for o in after['inventory']['leaves'] if o['id']==self.leaf_id)
        left, right = world(prior), world(current)
        self.require(name+' preserves every outer-contour operand', {k for k in left if k[0]<5}=={k for k in right if k[0]<5} and all(max(abs(a-b) for a,b in zip(v,right[k]))<1e-6 for k,v in left.items() if k[0]<5))
        self.require(name+' preserves evenodd hole and border', after['target']['fillRule']=='evenodd' and not after['target']['holeFilled'] and after['target']['borderFilled'])

    async def prepare_compound(self):
        self.doc='assets'
        self.context=await self.open_surface(self.browser, self.asset_fixture)
        await self.capture('library-context','The retained eight actual Library assets, native editable label and ordinary shape are intact before geometry fixture setup.')
        test=ROOT/'tests/vectorEngine.test.mjs'
        source=test.read_text(encoding='utf-8')
        fixture=re.search(r'function figureSnapshot\(\) \{.*?\n\}',source,re.S).group(0)
        self.row['fixtureSource']={'path':str(test),'sha256':hashlib.sha256(test.read_bytes()).hexdigest(),'function':'figureSnapshot','object':'compound-1'}
        setup=await self.surface.evaluate('''code=>{
          const def=new Function('PDF_DATA_URL',code+';return figureSnapshot().objects[0].objects[1]')('data:application/pdf;base64,JVBERg==');
          const a=FigureStudio.app,c=a.getObjectByIdForQa(a.getCanvasObjectInventoryForQa().objects[0].id).canvas;
          const compound=new fabric.Path(def.path,{...def,fill:'#317c93',stroke:'#123947',strokeWidth:1,locked:false,objectCaching:false,figureStudioStructureRole:'compound-path'});
          const inner=new fabric.Group([compound],{figureId:'geometry-inner',name:'Reflected pore group',angle:23,flipX:true,scaleX:1.13,scaleY:.91,locked:false});
          const outer=new fabric.Group([inner],{figureId:'geometry-outer',name:'Nested membrane fixture',angle:-13,scaleX:1.18,scaleY:.87,left:592,top:300,locked:false});
          c.add(outer);c.setActiveObject(outer);const coords=o=>{o.setCoords();for(const p of o.getObjects?.()||[])coords(p);};coords(outer);c.requestRenderAll();
          a.commitHistoryForQa('Prepared nested compound fixture');return{compound:def,root:outer.figureId,inner:inner.figureId,policy:'Unchanged two-contour vectorEngine fixture; setup only before observed public gestures. Eight actual Library owners retained.'};
        }''',fixture)
        self.row['fixtureSetup']=setup
        self.leaf_id='compound-1';self.parents=['geometry-outer','geometry-inner'];self.root_id='geometry-outer'
        await self.surface.locator('[data-figure-layout-choice="advanced"]').click()
        row=await self.reveal(self.leaf_id)
        await self.action(row,'select-on-canvas').click()
        await self.settled()
        target=await self.surface.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id).getBoundingRect()',self.leaf_id)
        await self.surface.locator('#viewport').focus();await self.page.keyboard.press('z')
        await m.base.HELPERS.drag_scene(self.surface,(target['left']-45,target['top']-35),(target['left']+target['width']+45,target['top']+target['height']+35))
        await self.page.keyboard.press('a');await self.settled()
        selector=f'.path-node-handle[data-object-id="{self.leaf_id}"][data-command-index="5"][data-handle-type="endpoint"]'
        self.require('Public Layers and Direct Selection reach the inner contour',await self.surface.locator(selector).count()==1)
        await self.surface.locator(selector).click();await self.settled()
        await self.surface.evaluate(m.WITNESS)
        if hasattr(self,'ensure_target_frame'):await self.ensure_target_frame()
        await self.capture('compound-before','The transformed nested membrane fixture shows a clear evenodd pore and compact inner-contour anchors; surrounding context remains genuine Library artwork.')

    async def segment(self, name, cancel=False):
        # Closing Z of the second contour, chosen before any pointer movement.
        before_art=await self.art(name+'-before')
        before=await self.observation(name+'-before')
        selector=f'.path-segment-hit[data-object-id="{self.leaf_id}"][data-segment-end-command="{self.seam}"]'
        ledger=await self.surface.evaluate('''selector=>{
          const rows=[...document.querySelectorAll(selector)];
          const all=[...document.querySelectorAll('.path-segment-hit[data-object-id="compound-1"]')];
          const result={chosen:null,targetCount:rows.length,allTargets:all.map(e=>({end:e.dataset.segmentEndCommand,sample:e.dataset.segmentSample})),zoomLabel:document.getElementById('zoomLabel')?.textContent};
          for(const el of rows){const b=el.getBoundingClientRect(),x=b.left+b.width/2,y=b.top+b.height/2;
            if(document.elementFromPoint(x,y)===el){result.chosen={x,y,sample:el.dataset.segmentSample,selector};break;}}
          return result;
        }''',selector)
        self.row.setdefault('segmentAdmissions',{})[name]=ledger
        probe=ledger['chosen']
        if not probe:
            target=next(o for o in before['inventory']['leaves'] if o['id']==self.leaf_id)
            points=world(target);previous=self.seam-1;end=self.contour_start if target['path'][self.seam][0]=='Z' else self.seam
            a=points[(previous,len(target['path'][previous])-2)];b=points[(end,len(target['path'][end])-2)]
            ca=await m.base.HELPERS.canvas_scene_point(self.surface,*a);cb=await m.base.HELPERS.canvas_scene_point(self.surface,*b)
            center=((ca['x']+cb['x'])/2,(ca['y']+cb['y'])/2)
            ledger.update(sceneLength=((a[0]-b[0])**2+(a[1]-b[1])**2)**.5,cssLength=((ca['x']-cb['x'])**2+(ca['y']-cb['y'])**2)**.5,expectedClosingMidpointClient=center)
            await self.surface.evaluate('''()=>{window.missingSegmentEvents=[];for(const type of ['pointerdown','pointermove','pointerup'])window.addEventListener(type,e=>window.missingSegmentEvents.push({type,trusted:e.isTrusted,ctrl:e.ctrlKey,client:[e.clientX,e.clientY],tag:e.target.tagName,classes:e.target.className,segment:e.target.dataset?.segmentEndCommand}),true);}''')
            await self.page.keyboard.down('Control')
            try:
                await self.page.mouse.move(*center);await self.surface.evaluate('window.missingSegmentEvents=[]');await self.page.mouse.down()
                await self.page.mouse.move(center[0]+14,center[1]-9,steps=4)
                await self.capture(name+'-missing-target-held','A trusted pointer drag begins on the visibly long inner closing edge. Beta25 supplies no segment target there; the native pointer destination and resulting artwork are retained as the failure witness.')
                self.row['missingSegmentGesture']={'events':await self.surface.evaluate('window.missingSegmentEvents'),'held':await self.observation(name+'-missing-target-held')}
                await self.page.keyboard.press('Escape');await self.page.mouse.up()
            finally:await self.page.keyboard.up('Control')
        self.require(name+' has a hittable closing-segment target',bool(probe),ledger)
        await self.surface.evaluate('window.mixedInput=[]')
        await self.page.keyboard.down('Control')
        try:
            await self.page.mouse.move(probe['x'],probe['y']);await self.page.mouse.down()
            chosen=await self.surface.evaluate("()=>[...document.querySelectorAll('.path-segment-hit.selected')].map(e=>({id:e.dataset.objectId,end:Number(e.dataset.segmentEndCommand)}))")
            self.require(name+' original pointer starts the intended native segment',bool(chosen) and all(r['id']==self.leaf_id and r['end']==self.seam for r in chosen),chosen)
            await self.page.mouse.move(probe['x']+14,probe['y']-9,steps=4)
            await self.surface.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
            await self.capture(name+'-held','Dragging the inner contour closing segment reshapes that side alone; the outer border, transparent pore and compact controls remain readable.')
            held=await self.observation(name+'-held')
            self.stationary(name+' held',before,held)
            old=next(o for o in before['inventory']['leaves'] if o['id']==self.leaf_id)
            new=next(o for o in held['inventory']['leaves'] if o['id']==self.leaf_id)
            events=await self.surface.evaluate('window.mixedInput');down=next(e for e in events if e['type']=='pointerdown');move=next(e for e in reversed(events) if e['type']=='pointermove')
            delta=(move['x']-down['x'],move['y']-down['y']);t=closest_material_t(old,self.seam,(down['x'],down['y']))
            first=material_point(old,self.seam,t);last=material_point(new,self.seam,t)
            self.row.setdefault('segmentInputs',{})[name]={'events':events,'nativeSelected':chosen,'independentT':t,'beforePoint':first,'heldPoint':last,'deliveredDelta':delta}
            self.require(name+' grabbed native material point follows the trusted delivered delta',down['trusted'] and move['trusted'] and sum(v*v for v in delta)>1 and max(abs(last[j]-first[j]-delta[j]) for j in range(2))<.005,self.row['segmentInputs'][name])
            expected_length=len(old['path'])+(1 if old['path'][self.seam][0]=='Z' else 0)
            self.require(name+' really reshapes the second contour',old['path']!=new['path'] and len(new['path'])==expected_length)
            if cancel:
                await self.page.keyboard.press('Escape')
                await self.capture(name+'-escaped-held','Escape alone restores the original membrane and pore while the pointer remains held; no click, Fit or render rescue occurs.')
            await self.page.mouse.up()
        finally:
            await self.page.keyboard.up('Control')
        if not cancel:await self.history(before['state']['history']['undoDepth']+1)
        await self.settled()
        after=await self.observation(name+'-after')
        after_art=await self.art(name+'-after')
        if cancel:
            self.require(name+' Escape restores full artwork and history',self.same(before_art,after_art) and before['state']['history']==after['state']['history'])
            self.require(name+' Escape restores complete direct selection',before['state']['direct']==after['state']['direct'])
        else:
            self.stationary(name+' committed',before,after)
            await self.page.keyboard.press('Control+z');await self.history(before['state']['history']['undoDepth']);await self.settled()
            self.require(name+' completed Undo restores complete artwork',self.same(before_art,await self.art(name+'-undo')))
            await self.page.keyboard.press('Control+y');await self.history(after['state']['history']['undoDepth']);await self.settled()
            self.require(name+' completed Redo restores complete edited artwork',self.same(after_art,await self.art(name+'-redo')))
            self.stationary(name+' Redo',before,await self.observation(name+'-redo'))

    async def run(self):
        self.started=time.perf_counter();self.context=None
        try:
            self.asset_fixture=ARGS.asset_fixture
            await self.prepare_compound()
            await self.segment('inner-seam-cancel',cancel=True)
            await self.segment('inner-seam-commit')
            self.require('No page errors',not self.row['pageErrors'],self.row['pageErrors'])
            self.row['status']='passed'
        except BaseException as error:
            self.row.update(status='failed',error=str(error))
            if hasattr(self,'page') and not self.page.is_closed():await self.page.screenshot(path=str(self.out/'failure.png'))
            raise
        finally:
            if self.context:await self.context.close()
            await self.browser.close();self.row['contextClosed']=True;self.row['browserClosed']=not self.browser.is_connected();self.save()


def execute(args,case_class=Compound):
    global ARGS
    ARGS=args;ARGS.smoke=True;ARGS.url='';ARGS.browser_channel='chromium'
    ARGS.viewport=getattr(ARGS,'viewport','1440x1000');ARGS.theme=getattr(ARGS,'theme','light')
    s.ARGS=ARGS;s.label.ARGS=ARGS;m.ARGS=ARGS
    i.asset_library=load('compound_library','scripts/check-library-drawings-browser.py')
    case_class.desktop_profile=(*map(int,ARGS.viewport.split('x')),ARGS.theme)
    m.base.Case=case_class
    server=thread=None
    if ARGS.base_runtime:
        import functools
        import threading
        from http.server import ThreadingHTTPServer
        runtime=load('compound_overlay_server','scripts/figure-studio-server.py')
        class Overlay(runtime.FigureStudioHandler):
            def translate_path(self,path):
                relative=path.split('?',1)[0].lstrip('/')
                candidate=ARGS.root/relative
                return str(candidate) if relative in ['app/app.js','app/styles.css'] and candidate.is_file() else super().translate_path(path)
        server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Overlay,directory=str(ARGS.base_runtime)))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        ARGS.url=f'http://127.0.0.1:{server.server_port}/app/index.html'
    try:asyncio.run(m.base.run(ARGS))
    finally:
        if server:
            server.shutdown();server.server_close();thread.join(timeout=5)
            (ARGS.output_dir/'overlay-closure.json').write_text(json.dumps({'closed':not thread.is_alive(),'baseRuntime':str(ARGS.base_runtime)})+'\n',encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--expected-app-sha256',required=True)
    p.add_argument('--base-runtime',type=Path)
    p.add_argument('--asset-fixture',type=Path,default=ROOT/'qa_artifacts/selection-reliability-20261105/assets-accepted/1440x1000-light/1440x1000-light/assets-second.fsfigure')
    execute(p.parse_args())
