"""Public compound segment, anchor and tangent continuation on the same native editor paths."""
import argparse
import asyncio
import importlib.util
import json
import math
from pathlib import Path
import time

AREA=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('geometry_probe',AREA/'probe.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
ROOT,i,m=probe.ROOT,probe.i,probe.m
STRICT_SAME=m.equivalent


def selection(state):
    d=state['direct']
    return {k:d[k] for k in ['tool','active','objectId','objectIds','selectedTextIds','selectedHandles','selectedBounds']}


class Geometry(probe.Compound):
    async def ensure_target_frame(self):
        # Setup/view actions precede each witness. A real middle-button pan keeps
        # the complete target in the viewport without a Fit or geometry setter.
        for _ in range(3):
            b=await self.surface.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id).getBoundingRect()',self.leaf_id)
            first=await m.base.HELPERS.canvas_scene_point(self.surface,b['left'],b['top'])
            last=await m.base.HELPERS.canvas_scene_point(self.surface,b['left']+b['width'],b['top']+b['height'])
            v=await self.surface.locator('#viewport').bounding_box();margin=26
            dx=max(0,v['x']+margin-first['x'])+min(0,v['x']+v['width']-margin-last['x'])
            dy=max(0,v['y']+margin-first['y'])+min(0,v['y']+v['height']-margin-last['y'])
            if abs(dx)<.5 and abs(dy)<.5:return
            start=await self.surface.evaluate('''v=>{
              for(const [x,y] of [[.5,.5],[.2,.3],[.8,.3],[.2,.7],[.8,.7]]){
                const p=[v.x+v.width*x,v.y+v.height*y];if(document.elementFromPoint(...p)?.matches('canvas.upper-canvas'))return p;}
              return null;
            }''',v)
            self.require('A public middle-button pan has a native canvas start',bool(start))
            dx=max(-v['width']/3,min(v['width']/3,dx));dy=max(-v['height']/3,min(v['height']/3,dy))
            await self.page.mouse.move(*start);await self.page.mouse.down(button='middle')
            await self.page.mouse.move(start[0]+dx,start[1]+dy,steps=4);await self.page.mouse.up(button='middle');await self.settled()
            self.row.setdefault('viewPans',[]).append({'start':start,'clientDelta':[dx,dy],'policy':'Public view setup before capture/gesture; no Fit or model mutation'})
        b=await self.surface.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id).getBoundingRect()',self.leaf_id)
        first=await m.base.HELPERS.canvas_scene_point(self.surface,b['left'],b['top']);last=await m.base.HELPERS.canvas_scene_point(self.surface,b['left']+b['width'],b['top']+b['height'])
        v=await self.surface.locator('#viewport').bounding_box()
        self.require('The complete target fits the viewport after public view setup',first['x']>=v['x']+20 and first['y']>=v['y']+20 and last['x']<=v['x']+v['width']-20 and last['y']<=v['y']+v['height']-20,{'first':first,'last':last,'viewport':v})

    async def zoom(self, desired):
        current=await self.surface.evaluate("()=>FigureStudio.app.getViewportStateForQa().zoom")
        target=await self.surface.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id).getBoundingRect()',self.leaf_id)
        at=await m.base.HELPERS.canvas_scene_point(self.surface,target['left']+target['width']/2,target['top']+target['height']/2)
        await self.page.mouse.move(at['x'],at['y'])
        await self.page.keyboard.down('Control')
        try:await self.page.mouse.wheel(0,math.log(current/desired)/.00135)
        finally:await self.page.keyboard.up('Control')
        await self.settled()
        await self.ensure_target_frame()

    async def zoom_controls(self,cohort=''):
        anchor=self.surface.locator(f'.path-node-handle[data-object-id="{self.leaf_id}"][data-command-index="{self.contour_start}"][data-handle-type="endpoint"]')
        box=await anchor.bounding_box();await self.page.mouse.click(box['x']+box['width']/2,box['y']+box['height']/2);await self.settled()
        before=await self.art(cohort+'zoom-before');state=await self.state(cohort+'zoom-before')
        native=await self.observation(cohort+'zoom-native')
        target=next(o for o in native['inventory']['leaves'] if o['id']==self.leaf_id)
        points=probe.world(target);previous=self.seam-1;end=self.contour_start if target['path'][self.seam][0]=='Z' else self.seam
        length=math.dist(points[(previous,len(target['path'][previous])-2)],points[(end,len(target['path'][end])-2)])
        controls=[('minimum',.08),('100percent',1),*[(str(n)+'px',n/length) for n in [32,40,48,150]],('maximum',5)]
        for tag,zoom in controls:
            name=(cohort+'-' if cohort else '')+tag
            await self.zoom(zoom)
            ledger=await self.surface.evaluate(r'''({id,seam})=>{
              const stage=document.getElementById('canvasStage'),z=new DOMMatrix(getComputedStyle(stage).transform).a;
              const hits=[...document.querySelectorAll('.path-segment-hit[data-object-id="'+id+'"][data-segment-end-command="'+seam+'"]')];
              const rows=hits.map(el=>{const b=el.getBoundingClientRect(),s=getComputedStyle(el),q=new DOMMatrix(s.transform),w=parseFloat(s.width)*z,h=parseFloat(s.height)*z;
                const center=[b.left+b.width/2,b.top+b.height/2],nativeWidth=parseFloat(el.style.width);
                const sceneCenter=[parseFloat(el.style.left)+q.a*nativeWidth/2,Number(el.style.top.match(/calc\(([-\d.e+]+)px/)[1])+q.b*nativeWidth/2];
                return{width:w,band:h,bounds:{x:b.x,y:b.y,width:b.width,height:b.height},center,sceneCenter,
                  expectedBounds:[Math.abs(q.a)*w+Math.abs(q.b)*h,Math.abs(q.b)*w+Math.abs(q.a)*h],
                  authoritative:document.elementFromPoint(...center)===el};});
              const nodes=[...document.querySelectorAll('.path-node-handle[data-object-id="'+id+'"]')].map(el=>{
                const b=el.getBoundingClientRect(),s=getComputedStyle(el),p=getComputedStyle(el,'::after'),q=new DOMMatrix(s.transform);
                return{command:Number(el.dataset.commandIndex),type:el.dataset.handleType,hit:[b.width,b.height],center:[b.x+b.width/2,b.y+b.height/2],
                  marker:(parseFloat(p.width)+2*parseFloat(p.borderLeftWidth))*Math.abs(q.a)*z,
                  centerAuthority:document.elementFromPoint(b.x+b.width/2,b.y+b.height/2)===el};});
              return{zoom:z,rows,nodes};
            }''',{'id':self.leaf_id,'seam':self.seam})
            if getattr(probe.ARGS,'part','compound')=='pdf':
                self.require(name+' keeps redundant Source badges off native point controls',await self.surface.locator('.object-status-overlay:not([hidden]) .object-status-badge.source').count()==0)
            ledger['expectedCssSeamLength']=length*zoom
            self.row.setdefault('zoomAdmissions',{})[name]=ledger;self.save()
            self.require(name+' uses the requested supported CSS zoom',abs(ledger['zoom']-zoom)<1e-5,ledger['zoom'])
            usable=length*zoom>28
            self.require(name+' admits a usable middle or keeps the tiny edge endpoint-only',bool(ledger['rows']) if usable else not ledger['rows'],ledger)
            # Layout quantizes this inverse-scaled box before the stage transform.
            # Retain the14CSSpx intent within one observed native1/64px layout step.
            quantum=ledger['zoom']/64
            self.require(name+' hit bands retain14CSSpx intent within native layout precision and exact chord bounds',all(14-quantum-.002<=r['band']<=14+.002 and r['width']>=4-quantum-.002 and max(abs(r['bounds'][k]-r['expectedBounds'][j]) for j,k in enumerate(['width','height']))<.06 for r in ledger['rows']))
            self.require(name+' point markers stay compact',all(r['marker']<=12.01 for r in ledger['nodes']),ledger['nodes'])
            after=await self.state('zoom-'+name)
            self.require(name+' zoom changes no selected anchors or history',selection(state)==selection(after) and state['history']==after['history'])
            if usable:
                # A curved strip approximates the native edge with a chord.
                # Place the trusted pointer on the actual visible curve, rather
                # than assuming that rectangle's center is painted geometry.
                t=probe.closest_material_t(target,self.seam,ledger['rows'][0]['sceneCenter'])
                curve=probe.material_point(target,self.seam,t)
                client=await m.base.HELPERS.canvas_scene_point(self.surface,*curve)
                center=[client['x'],client['y']]
                stack=await self.surface.evaluate('p=>document.elementsFromPoint(...p).map(e=>({object:String(e.dataset.objectId||""),end:Number(e.dataset.segmentEndCommand),kind:e.className}))',center)
                ledger['pointerTarget']={'independentT':t,'world':curve,'client':center,'stack':stack}
                self.require(name+' actual native curve lies inside its admitted hit strip',any(r['object']==self.leaf_id and r['end']==self.seam for r in stack),ledger['pointerTarget'])
                await self.surface.evaluate('''()=>{window.segmentAuthorityInputs=[];window.addEventListener('pointerdown',e=>window.segmentAuthorityInputs.push({trusted:e.isTrusted,ctrl:e.ctrlKey,client:[e.clientX,e.clientY],domSegment:e.target.dataset?.segmentEndCommand,domObject:e.target.dataset?.objectId}),{capture:true,once:true});}''')
                await self.page.keyboard.down('Control')
                try:
                    await self.page.mouse.move(*center);await self.page.mouse.down()
                    selected=await self.surface.evaluate("()=>[...document.querySelectorAll('.path-segment-hit.selected')].map(e=>({id:e.dataset.objectId,end:Number(e.dataset.segmentEndCommand)}))")
                    ledger['pointerAuthority']={'inputs':await self.surface.evaluate('window.segmentAuthorityInputs'),'nativeSelected':selected}
                    correct=bool(selected) and all(r['id']==self.leaf_id and r['end']==self.seam for r in selected)
                    if not correct:await self.capture('zoom-'+name+'-wrong-segment-held','A trusted pointer is on the intended visible edge; the selected segment highlight records the incorrect native target before Escape. This is a retained failure witness.')
                    await self.page.keyboard.press('Escape');await self.page.mouse.up()
                finally:await self.page.keyboard.up('Control')
                self.save()
                self.require(name+' original pointer selects the actual intended native segment',correct,ledger['pointerAuthority'])
                restored=await self.state('zoom-'+name+'-segment-cancel')
                self.require(name+' zero-motion segment cancellation preserves anchors and history',selection(state)==selection(restored) and state['history']==restored['history'])
                node=next(r for r in ledger['nodes'] if r['command']==self.contour_start and r['type']=='endpoint')
                await self.page.mouse.click(*node['center']);await self.settled()
                clicked=await self.state('zoom-'+name+'-endpoint-click');refs=clicked['direct']['selectedHandles']
                self.require(name+' original pointer resolves the intended endpoint ahead of segment hits',len(refs)==1 and refs[0]['objectId']==self.leaf_id and refs[0]['commandIndex']==self.contour_start and refs[0]['handleType']=='endpoint' and state['history']==clicked['history'],refs)
            if tag in ['32px','150px']:
                await self.capture('zoom-'+name,'The same transformed compound pore is shown at the declared edge size; small point markers and the actual visible seam supply the public editing targets without extra overlay enlargement.')
        self.require(cohort+' All zoom controls preserve complete authored artwork',self.same(before,await self.art(cohort+'zoom-after')))

    async def handle(self,name,command,kind,cancel=False,capture=False):
        anchor=f'.path-node-handle[data-object-id="{self.leaf_id}"][data-command-index="{self.anchor_command}"][data-handle-type="endpoint"]'
        await self.surface.locator(anchor).click();await self.settled()
        selector=f'.path-node-handle[data-object-id="{self.leaf_id}"][data-command-index="{command}"][data-handle-type="{kind}"]'
        box=await self.surface.locator(selector).bounding_box()
        self.require(name+' exposes the intended native handle',bool(box))
        await self.page.mouse.click(box['x']+box['width']/2,box['y']+box['height']/2)
        await self.settled()
        before_art=await self.art(name+'-before');before=await self.observation(name+'-before')
        refs=before['state']['direct']['selectedHandles']
        self.require(name+' public center click selects only the intended handle',len(refs)==1 and refs[0]['objectId']==self.leaf_id and refs[0]['commandIndex']==command and refs[0]['handleType']==kind,refs)
        box=await self.surface.locator(selector).bounding_box();start=(box['x']+box['width']/2+1,box['y']+box['height']/2+1)
        await self.page.keyboard.down('Control')
        if kind!='endpoint':await self.page.keyboard.down('Alt')
        try:
            await self.page.mouse.move(*start);await self.surface.evaluate('window.mixedInput=[]');await self.page.mouse.down()
            await self.page.mouse.move(start[0]+12,start[1]-7,steps=4)
            await self.surface.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
            if capture:await self.capture(name+'-held','The selected inner-contour anchor or tangent follows the actual pointer while the pore, outer contour and native Library neighbors remain intact; compact handles stay on the edited geometry.')
            held=await self.observation(name+'-held');self.stationary(name+' held',before,held)
            events=await self.surface.evaluate('window.mixedInput');down=next(e for e in events if e['type']=='pointerdown');move=next(e for e in reversed(events) if e['type']=='pointermove')
            delta=(move['x']-down['x'],move['y']-down['y']);self.row.setdefault('handleInputs',{})[name]=events
            self.require(name+' uses a meaningful trusted original pointer displacement',down['trusted'] and move['trusted'] and math.hypot(*delta)>1)
            old=next(o for o in before['inventory']['leaves'] if o['id']==self.leaf_id);new=next(o for o in held['inventory']['leaves'] if o['id']==self.leaf_id)
            self.require(name+' retains exact target command types and operand counts',[(c[0],len(c)) for c in old['path']]==[(c[0],len(c)) for c in new['path']])
            left,right=probe.world(old),probe.world(new);allowed={(self.anchor_command,1),(self.seam,1)} if kind=='endpoint' else {(self.seam,1)}
            errors=[{'operand':k,'actual':right.get(k),'expectedDelta':delta if k in allowed else (0,0)} for k,v in left.items() if k not in right or max(abs(right[k][j]-v[j]-(delta[j] if k in allowed else 0)) for j in range(2))>1e-5]
            self.require(name+' moves only the intended native operands by the delivered delta',left.keys()==right.keys() and not errors,errors)
            if cancel:await self.page.keyboard.press('Escape')
            await self.page.mouse.up()
        finally:
            if kind!='endpoint':await self.page.keyboard.up('Alt')
            await self.page.keyboard.up('Control')
        if not cancel:await self.history(before['state']['history']['undoDepth']+1)
        await self.settled();after=await self.observation(name+'-after');after_art=await self.art(name+'-after')
        if cancel:
            self.require(name+' Escape restores exact artwork, selection and history',self.same(before_art,after_art) and selection(before['state'])==selection(after['state']) and before['state']['history']==after['state']['history'])
        else:
            self.stationary(name+' released',before,after)
            await self.page.keyboard.press('Control+z');await self.history(before['state']['history']['undoDepth']);await self.settled()
            self.require(name+' completed Undo restores complete artwork',self.same(before_art,await self.art(name+'-undo')))
            await self.page.keyboard.press('Control+y');await self.history(after['state']['history']['undoDepth']);await self.settled()
            self.require(name+' completed Redo restores complete edited artwork',self.same(after_art,await self.art(name+'-redo')))
            self.stationary(name+' Redo',before,await self.observation(name+'-redo'))

    async def record_process(self,name):
        session=await self.browser.new_browser_cdp_session()
        try:
            data=await session.send('SystemInfo.getProcessInfo')
            self.row.setdefault('browserProcesses',{})[name]=[r for r in data['processInfo'] if r['type']=='browser']
        except Exception as error:self.row.setdefault('browserProcessUnavailable',{})[name]=str(error)
        finally:await session.detach()

    async def roundtrip_geometry(self):
        warm=await self.art('geometry-warm-save');path,saved=await self.save_file('geometry-first',warm)
        await self.context.close();self.context=None
        kind=self.browser.browser_type;await self.browser.close();self.row['warmBrowserClosed']=not self.browser.is_connected()
        self.browser=await kind.launch(**self.report['browserLaunchOptions']);await m.base.record_browser_runtime(self.browser,self.report,'geometry-cold')
        await self.record_process('cold')
        processes=self.row.get('browserProcesses',{})
        self.require('Both actual browser process identities are available',set(processes)=={'warm','cold'} and all(len(rows)==1 for rows in processes.values()),processes)
        self.require('Fresh-process Open uses a different actual browserPID',processes['warm'][0]['id']!=processes['cold'][0]['id'])
        self.context=await self.open_surface(self.browser,path)
        await self.capture('geometry-cold-open','A genuinely new Chromium process opens the actual saved compound scene before any navigation or Fit, retaining the edited pore, native Library owners and editable labels.')
        self.require('Fresh-process Open preserves complete actual saved artwork',self.same(saved,await self.art('geometry-cold-open')))
        await self.reach_target()
        await self.handle('cold-continued-anchor',self.anchor_command,'endpoint',capture=True)
        await self.save_file('geometry-second',await self.art('geometry-cold-save'))
        await self.capture('geometry-continued-redo','The reopened scene remains editable after a continued inner-contour anchor edit and completed Undo/Redo. The original pore, outer contour and nearby Library artwork remain visible.')

    async def reach_target(self):
        await self.surface.locator('[data-figure-layout-choice="advanced"]').click()
        row=await self.reveal(self.leaf_id);await self.action(row,'select-on-canvas').click();await self.settled()
        target=await self.surface.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id).getBoundingRect()',self.leaf_id)
        await self.surface.locator('#viewport').focus();await self.page.keyboard.press('z')
        await m.base.HELPERS.drag_scene(self.surface,(target['left']-45,target['top']-35),(target['left']+target['width']+45,target['top']+target['height']+35))
        await self.page.keyboard.press('a');await self.settled();await self.surface.evaluate(m.WITNESS)
        await self.ensure_target_frame()

    async def run(self):
        self.started=time.perf_counter();self.context=None;original=m.equivalent
        self.same=STRICT_SAME if getattr(probe.ARGS,'part','compound')=='pdf' else i.real_asset_equivalent;m.equivalent=self.same
        try:
            self.asset_fixture=probe.ARGS.asset_fixture
            await self.record_process('warm')
            await self.prepare_compound()
            await self.zoom_controls()
            await self.segment('inner-seam-cancel',cancel=True)
            await self.segment('inner-seam-commit')
            await self.segment('curved-seam-cancel',cancel=True)
            await self.segment('curved-seam-commit')
            await self.zoom_controls('curved')
            await self.handle('inner-anchor-cancel',self.anchor_command,'endpoint',cancel=True)
            await self.handle('inner-anchor-edit',self.anchor_command,'endpoint',capture=True)
            await self.handle('inner-tangent-cancel',self.seam,'control1',cancel=True)
            await self.handle('inner-tangent-edit',self.seam,'control1',capture=True)
            await self.capture('completed-redo','The completed native edits have been undone and redone through public keys. The membrane contour, clear pore and compact tangent controls match the final authored state.')
            await self.roundtrip_geometry()
            self.require('No page errors',not self.row['pageErrors'],self.row['pageErrors'])
            self.row['status']='passed'
        except BaseException as error:
            self.row.update(status='failed',error=str(error))
            if hasattr(self,'page') and not self.page.is_closed():await self.page.screenshot(path=str(self.out/'failure.png'))
            raise
        finally:
            if self.context:await self.context.close()
            await self.browser.close();self.row['contextClosed']=True;self.row['browserClosed']=not self.browser.is_connected();self.save();m.equivalent=original


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--expected-app-sha256',required=True)
    p.add_argument('--base-runtime',type=Path);p.add_argument('--viewport',default='1440x1000');p.add_argument('--theme',default='light')
    p.add_argument('--asset-fixture',type=Path,default=ROOT/'qa_artifacts/selection-reliability-20261105/assets-accepted/1440x1000-light/1440x1000-light/assets-second.fsfigure')
    probe.execute(p.parse_args(),Geometry)
