"""Public point gestures using maintained native selection fixture and recorder."""
import argparse
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('point_grab_base', ROOT / 'scripts/check-point-selection-body-drag-browser.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
paint_spec = importlib.util.spec_from_file_location('point_paint', Path(__file__).with_name('path_point_paint_qa.py'))
paint = importlib.util.module_from_spec(paint_spec)
paint_spec.loader.exec_module(paint)


class GrabCase(base.Case):
    def __init__(self,browser,url,out,width,height,theme,report):
        width,height,theme=getattr(self,'desktop_profile',(width,height,theme))
        report['schema']='figureStudio.pathPointGestureBrowser.v1'
        super().__init__(browser,url,out,width,height,theme,report)

    def entry_url(self):
        value=base.urlsplit(self.base);query=dict(base.parse_qsl(value.query))
        theme='dark-graphite' if self.theme=='dark' else 'light'
        query.update(bsd_theme=theme,bsd_effective_theme=theme)
        return base.urlunsplit((value.scheme,value.netloc,value.path,base.urlencode(query),value.fragment))

    async def snapshot(self,name,ids):
        if getattr(self,'paint_diagnostic',False):await self.surface.evaluate('name=>window.pointPaintPhase=name',name)
        return await super().snapshot(name,ids)

    async def bind_delivered_delta(self, name, before, after, object_index, operands):
        events = await self.surface.evaluate('window.grabEvents')
        down = next(e for e in events if e['type'] == 'pointerdown')
        moved = next(e for e in reversed(events) if e['type'] == 'pointermove')
        delta = [moved['x']-down['x'], moved['y']-down['y']]
        changes = base.deltas(before, after)
        self.row.setdefault('deliveredGestures', []).append(dict(name=name, events=events, delta=delta))
        self.check(name+' follows the actual delivered pointer delta', all(base.close(changes[object_index][key],delta,.005) for key in operands),dict(delta=delta,changes={str(k):v for k,v in changes[object_index].items()}))

    async def capture(self, name, intent):
        # Wait for the real status toast to expire; do not hide or restyle it.
        await self.surface.locator('#toast.show').wait_for(state='hidden', timeout=12000)
        await super().capture(name, intent)

    async def predicted_delta(self, target, start, delta=(23,-17)):
        return await self.surface.evaluate('''({target,start,delta})=>{
          const c=FigureStudio.app.getObjectByIdForQa(target).canvas;
          const a=c.getScenePoint(new MouseEvent('pointerdown',{clientX:start[0],clientY:start[1]}));
          const b=c.getScenePoint(new MouseEvent('pointermove',{clientX:start[0]+delta[0],clientY:start[1]+delta[1]}));
          return [b.x-a.x,b.y-a.y];
        }''',dict(target=target,start=start,delta=delta))

    async def client_delta_for_scene(self,target,start,delta):
        return await self.surface.evaluate('''({target,start,delta})=>{
          const c=FigureStudio.app.getObjectByIdForQa(target).canvas;
          const at=(x,y)=>c.getScenePoint(new MouseEvent('pointermove',{clientX:x,clientY:y}));
          const p=at(...start),x=at(start[0]+1,start[1]),y=at(start[0],start[1]+1);
          const a=x.x-p.x,b=x.y-p.y,d=y.y-p.y,e=y.x-p.x,q=a*d-b*e;
          return [Math.round((d*delta[0]-e*delta[1])/q),Math.round((-b*delta[0]+a*delta[1])/q)];
        }''',dict(target=target,start=start,delta=delta))

    def check(self, name, condition, detail=None):
        self.row['checks'].append(dict(name=name, passed=bool(condition), detail=detail))
        self.save()

    async def drag_selected(self, selector, ids, name):
        handle = self.surface.locator(selector)
        await handle.click()
        before = await self.snapshot(name + '-before', ids)
        box = await handle.bounding_box()
        start = (box['x'] + box['width']/2 + 3, box['y'] + box['height']/2 + 2)
        self.check(name+' pointerdown hits the actual visible handle',await self.surface.evaluate('p=>document.elementFromPoint(p.x,p.y)?.matches(p.selector)',dict(x=start[0],y=start[1],selector=selector)))
        await self.surface.evaluate('window.grabEvents=[]')
        screen_delta=await self.client_delta_for_scene(ids[1],start,(18,-14))
        delta = await self.predicted_delta(ids[1], start,screen_delta)
        expected = paint.translated(before['objects'], 1, {(1,3),(1,5),(2,1)}, delta)
        async def action():
            await self.page.keyboard.down('Control')
            await self.page.mouse.move(*start); await self.page.mouse.down()
            await self.page.mouse.move(start[0]+screen_delta[0], start[1]+screen_delta[1], steps=4)
            await self.page.mouse.up(); await self.page.keyboard.up('Control')
        await paint.observe(self, name, before['objects'], expected,
            dict(type='pointerdown',selector='.path-node-handle'), action)
        await self.history(before['history']['undoDepth']+1)
        after = await self.snapshot(name + '-after', ids)
        await self.bind_delivered_delta(name,before,after,1,{(1,3),(1,5),(2,1)})
        return before, after

    async def nested_curves(self, ids):
        await self.surface.locator('#viewport').focus()
        await self.page.keyboard.press('v')
        if getattr(self,'paint_diagnostic',False):
            await self.surface.evaluate('''id=>{
              const proto=fabric.Path.prototype,logs=window.pointPaintWitness=[],saved=[],c=FigureStudio.app.getObjectByIdForQa(id).canvas;
              const mainLower=c.lowerCanvasEl,requests=window.pointRenderWitness=[],canvasSaved=[];
              for(const name of ['requestRenderAll','renderAll','cancelRequestedRender']){
                const descriptor=Object.getOwnPropertyDescriptor(c,name),original=c[name];canvasSaved.push({name,descriptor});
                c[name]=function(...args){if(requests.length<300)requests.push({phase:window.pointPaintPhase||'fixture',method:name,at:performance.now(),pending:c.nextRenderHandle,stack:new Error().stack,groups:(()=>{const r=FigureStudio.app.getObjectByIdForQa(id);const a=[];for(let p=r?.group;p;p=p.group)a.push({id:p.figureId,cache:p.objectCaching});return a;})()});return original.apply(this,args);};
              }
              const read=(o,ctx,method,side)=>{if(o.figureId!==id||logs.length>=300)return;
                const t=ctx.getTransform();logs.push({phase:window.pointPaintPhase||'fixture',method,side,at:performance.now(),matrix:[t.a,t.b,t.c,t.d,t.e,t.f],lineWidth:ctx.lineWidth,cap:ctx.lineCap,join:ctx.lineJoin,dash:ctx.getLineDash(),strokeStyle:String(ctx.strokeStyle),fillStyle:String(ctx.fillStyle),alpha:ctx.globalAlpha,composite:ctx.globalCompositeOperation,filter:ctx.filter,lower:ctx.canvas===mainLower,ownerIsMain:o.canvas===c,canvasWidth:ctx.canvas.width,canvasHeight:ctx.canvas.height,ancestors:(()=>{const a=[];for(let p=o.group;p;p=p.group)a.push({id:p.figureId,done:p._transformDone,cache:p.ownCaching});return a;})()});};
              for(const name of ['_renderPathCommands','_setStrokeStyles']){
                const descriptor=Object.getOwnPropertyDescriptor(proto,name),original=proto[name];saved.push({name,descriptor});
                proto[name]=function(ctx,...rest){read(this,ctx,name,'before');const result=original.call(this,ctx,...rest);read(this,ctx,name,'after');return result;};
              }
              window.restorePointPaintWitness=()=>{for(const s of saved){if(s.descriptor)Object.defineProperty(proto,s.name,s.descriptor);else delete proto[s.name];}for(const s of canvasSaved){if(s.descriptor)Object.defineProperty(c,s.name,s.descriptor);else delete c[s.name];}};
            }''',ids[0])
        pose = await self.surface.evaluate('''ids=>{
          const app=FigureStudio.app,rect=app.getObjectByIdForQa(ids[0]),ellipse=app.getObjectByIdForQa(ids[1]),c=rect.canvas;
          c.discardActiveObject();c.remove(rect,ellipse);
          const inner=new fabric.Group([ellipse],{figureId:'qa-point-inner',figureType:'group',name:'Inner curve group',objectCaching:true});
          inner.set({angle:23,scaleX:.91,scaleY:1.06,flipX:true});
          const outer=new fabric.Group([rect,inner],{figureId:'qa-point-outer',figureType:'group',name:'Nested transformed curves',objectCaching:true});
          outer.set({angle:-13,scaleX:.87,scaleY:.93});
          ellipse.figureStudioBezierNodeMeta={schema:'figureStudio.bezierNodes.v1',nodes:[],retainedExtension:{label:'legacy sentinel',value:17}};
          c.add(outer);c.setActiveObject(outer);
          const coords=o=>{o.setCoords();for(const child of o.getObjects?.()||[])coords(child);};coords(outer);
          c.requestRenderAll();
          window.nestedDoubleClicks=[];
          c.on('mouse:dblclick',ev=>window.nestedDoubleClicks.push({targetId:ev.target?.figureId,subTargets:(ev.subTargets||[]).map(o=>o.figureId),scene:c.getScenePoint(ev.e),isolation:app.getGroupIsolationStateForQa().path}));
          app.commitHistoryForQa('Nested curve fixture prepared');
          return {outer:outer.figureId,inner:inner.figureId};
        }''',ids)
        self.row['nestedFixture'] = dict(**pose, policy='Fixture-only native Fabric nesting/pose/legacy metadata; all subsequent group entry and gestures use public input.')
        await self.surface.locator('[data-figure-layout-command="fit-screen"]:visible, #fitBtn:visible').first.click()
        entry_before = await self.snapshot('nested-entry-before',ids)
        await self.surface.locator('#viewport').focus(); await self.page.keyboard.press('a')
        entries = []
        selector=f'.path-node-handle[data-object-id="{ids[1]}"][data-command-index="1"][data-handle-type="endpoint"]'
        for level in range(3):
            if await self.surface.locator(selector).count(): break
            point=await self.surface.evaluate('id=>FigureStudio.app.getPathSegmentPointForQa(id,0,.5)',ids[1])
            client=await base.HELPERS.canvas_scene_point(self.surface,point['x'],point['y'])
            if level == 1: await self.page.mouse.dblclick(client['x'],client['y'])
            else: await self.page.mouse.click(client['x'],client['y'])
            entries.append(await self.surface.evaluate('FigureStudio.app.getGroupIsolationStateForQa()'))
        self.row['nestedEntries']=entries
        self.row['nestedDoubleClicks']=await self.surface.evaluate('window.nestedDoubleClicks')
        self.check('Public Direct Selection reaches the nested curve through its real group hierarchy',await self.surface.locator(selector).count()==1,entries)
        if not await self.surface.locator(selector).count(): raise AssertionError('Public nested curve entry failed')
        entered=await self.snapshot('nested-entry-after',ids)
        self.check('Entering nested artwork preserves every world operand',all(base.close(v,(0,0),.005) for row in base.deltas(entry_before,entered) for v in row.values()))
        first,second=await self.drag_selected(selector,ids,'nested-anchor')
        moves=base.deltas(first,second);delta=moves[1][(1,5)];attached={(1,3),(1,5),(2,1)}
        self.check('Nested reflected/rotated anchor carries both adjacent tangents within .005 world units',all(base.close(moves[1][key],delta,.005) for key in attached),{str(k):v for k,v in moves[1].items()})
        self.check('Nested anchor preserves all unrelated operands and its neighbor',all(base.close(v,(0,0),.005) for i,row in enumerate(moves) for k,v in row.items() if i==0 or k not in attached))
        await self.capture('nested-anchor','The selected curve is nested under reflected and rotated cached groups; its anchor and both tangents have moved together, with the neighboring rectangle intact.')
        async def undo(): await self.page.keyboard.press('Control+z')
        await paint.observe(self,'nested-undo',second['objects'],first['objects'],dict(type='keydown',selector='#viewport',key='z'),undo)
        await self.history(first['history']['undoDepth'])
        undone=await self.snapshot('nested-undone',ids)
        self.check('One public Undo restores every nested operand',all(base.close(v,(0,0),.005) for row in base.deltas(first,undone) for v in row.values()))
        async def redo(): await self.page.keyboard.press('Control+Shift+z')
        await paint.observe(self,'nested-redo',undone['objects'],second['objects'],dict(type='keydown',selector='#viewport',key='z'),redo)
        await self.history(second['history']['undoDepth'])
        redone=await self.snapshot('nested-redone',ids)
        self.check('One public Redo restores every nested operand',all(base.close(v,(0,0),.005) for row in base.deltas(second,redone) for v in row.values()))
        # An exact return must preserve authored paths, raw legacy metadata and history.
        handle=self.surface.locator(selector);await handle.click()
        noop_before=await self.snapshot('nested-noop-before',ids)
        metadata=await self.surface.evaluate('id=>JSON.stringify(FigureStudio.app.getObjectByIdForQa(id).figureStudioBezierNodeMeta)',ids[1])
        box=await handle.bounding_box();start=(box['x']+box['width']/2+3,box['y']+box['height']/2+2)
        await self.page.keyboard.down('Control');await self.page.mouse.move(*start);await self.page.mouse.down()
        await self.page.mouse.move(start[0]+24,start[1]-19,steps=4);await self.page.mouse.move(*start,steps=4)
        await self.page.mouse.up();await self.page.keyboard.up('Control')
        noop=await self.snapshot('nested-noop-after',ids)
        self.check('Out-and-back anchor gesture preserves exact paths and history',noop['history']==noop_before['history'] and [o['path'] for o in noop['objects']]==[o['path'] for o in noop_before['objects']])
        self.check('Out-and-back preserves the complete legacy node metadata',metadata==await self.surface.evaluate('id=>JSON.stringify(FigureStudio.app.getObjectByIdForQa(id).figureStudioBezierNodeMeta)',ids[1]))
        # Escape is the only completion action; the observer is armed on the held preview.
        box=await self.surface.locator(selector).bounding_box();start=(box['x']+box['width']/2+3,box['y']+box['height']/2+2)
        held_screen_delta=await self.client_delta_for_scene(ids[1],start,(50,30))
        held_delta=await self.predicted_delta(ids[1],start,held_screen_delta)
        held_expected=paint.translated(noop['objects'],1,{(1,3),(1,5),(2,1)},held_delta)
        async def preview():
            await self.page.keyboard.down('Control');await self.page.mouse.move(*start);await self.page.mouse.down()
            await self.page.mouse.move(start[0]+held_screen_delta[0],start[1]+held_screen_delta[1],steps=4)
        await paint.observe(self,'nested-held-preview',noop['objects'],held_expected,dict(type='pointerdown',selector='.path-node-handle'),preview)
        held=await self.snapshot('nested-held',ids)
        async def cancel():
            await self.page.keyboard.press('Escape');await self.page.mouse.up();await self.page.keyboard.up('Control')
        await paint.observe(self,'nested-cancel',held['objects'],noop['objects'],dict(type='keydown',selector='#viewport',key='Escape'),cancel)
        canceled=await self.snapshot('nested-canceled',ids)
        self.check('Escape restores nested geometry and history without leaving the group',canceled['history']==noop['history'] and all(base.close(v,(0,0),.005) for row in base.deltas(noop,canceled) for v in row.values()))
        self.check('Escape preserves complete raw legacy node metadata',metadata==await self.surface.evaluate('id=>JSON.stringify(FigureStudio.app.getObjectByIdForQa(id).figureStudioBezierNodeMeta)',ids[1]))
        await self.capture('nested-canceled','After Escape, the nested curve and both tangents return to their previous positions and remain editable inside the same group.')
        if getattr(self,'paint_diagnostic',False):
            observed=await self.surface.evaluate('()=>{const logs=window.pointPaintWitness,requests=window.pointRenderWitness;window.restorePointPaintWitness();return {logs,requests};}')
            self.row['diagnosticPaintWitness']=observed['logs']
            self.row['diagnosticRenderWitness']=observed['requests']
        await self.saved_continuation(ids, canceled)

    async def saved_continuation(self, ids, before):
        spec=importlib.util.spec_from_file_location('point_pdf_continuity',ROOT/'scripts/check-figure-pdf-editing-browser.py')
        pdf=importlib.util.module_from_spec(spec);spec.loader.exec_module(pdf)
        warm=json.loads(await self.surface.evaluate('()=>JSON.stringify(FigureStudio.app.buildProjectJsonForQa().fabric)'))
        (self.out/'warm-complete-fabric.json').write_text(json.dumps(warm,indent=2),encoding='utf-8')
        project=self.out/'nested-edited.fsfigure'
        async with self.page.expect_download() as download:
            await self.surface.locator('body').press('Control+s')
        await (await download.value).save_as(project)
        payload=json.loads(project.read_text(encoding='utf-8'))
        saved=payload.get('project',payload)['fabric']
        normalize=pdf.artwork_without_session_isolation
        self.check('Actual downloaded Save contains the complete warm artwork',pdf.equal_serialized_artwork(normalize(warm),normalize(saved)))
        self.row['actualSave']=dict(path=str(project),bytes=project.stat().st_size,sha256=hashlib.sha256(project.read_bytes()).hexdigest())
        await self.page.context.close()
        browser_type=self.browser.browser_type
        await self.browser.close()
        self.row['warmBrowserClosed']=not self.browser.is_connected()
        launch_options=self.report.get('browserLaunchOptions', {'headless':True})
        self.cold_browser=await browser_type.launch(**launch_options)
        await base.record_browser_runtime(self.cold_browser,self.report,'cold')
        context=await self.cold_browser.new_context(viewport=dict(width=self.width,height=self.height),color_scheme=self.theme)
        self.cold_context=context
        await context.add_init_script('try{delete window.showSaveFilePicker;delete window.showOpenFilePicker;}catch(_){}')
        self.page=await context.new_page()
        self.page.set_default_timeout(15000)
        self.page.on('pageerror',lambda e:self.row['pageErrors'].append(str(e)))
        self.page.on('dialog',lambda d:d.accept(d.default_value or 'point-continuation.fsfigure'))
        await self.page.goto(self.entry_url(),wait_until='domcontentloaded')
        self.surface=await base.HELPERS.resolve_figure_surface(self.page)
        await base.HELPERS.dismiss_first_run_surface(self.surface)
        async with self.page.expect_file_chooser() as chooser:
            await self.surface.locator('body').press('Control+o')
        await (await chooser.value).set_files(project)
        await self.surface.app_frame.wait_for_function("document.querySelector('#documentFileOperationStatus')?.dataset.state==='success' && !FigureStudio.app.getBrowserSessionState().busy")
        cold=json.loads(await self.surface.evaluate('()=>JSON.stringify(FigureStudio.app.buildProjectJsonForQa().fabric)'))
        (self.out/'cold-complete-fabric.json').write_text(json.dumps(cold,indent=2),encoding='utf-8')
        self.check('Fresh Chromium Open preserves the complete saved artwork',pdf.equal_serialized_artwork(normalize(saved),normalize(cold)))
        reopened=await self.snapshot('nested-cold-open',ids)
        self.check('Fresh Open preserves every nested world operand and parent',all(base.close(v,(0,0),.005) for row in base.deltas(before,reopened) for v in row.values()))
        if hasattr(self,'prepare_continued_view'):await self.prepare_continued_view(ids)
        else:await self.surface.locator('[data-figure-layout-command="fit-screen"]:visible, #fitBtn:visible').first.click()
        await self.surface.locator('#viewport').focus();await self.page.keyboard.press('a')
        selector=f'.path-node-handle[data-object-id="{ids[1]}"][data-command-index="1"][data-handle-type="endpoint"]'
        for level in range(3):
            if await self.surface.locator(selector).count():break
            point=await self.surface.evaluate('id=>FigureStudio.app.getPathSegmentPointForQa(id,0,.5)',ids[1])
            client=await base.HELPERS.canvas_scene_point(self.surface,point['x'],point['y'])
            if level==1:await self.page.mouse.dblclick(client['x'],client['y'])
            else:await self.page.mouse.click(client['x'],client['y'])
        self.check('Public selection reaches the same nested curve after fresh Open',await self.surface.locator(selector).count()==1)
        await self.surface.evaluate('''id=>{const c=FigureStudio.app.getObjectByIdForQa(id).canvas;window.grabEvents=[];for(const type of ['pointerdown','pointermove','pointerup'])window.addEventListener(type,e=>{const p=c.getScenePoint(e);window.grabEvents.push({type,x:p.x,y:p.y,clientX:e.clientX,clientY:e.clientY});},true);}''',ids[1])
        first,second=await self.drag_selected(selector,ids,'nested-cold-continued-anchor')
        self.check('Continued cold edit preserves the neighboring path',all(base.close(v,(0,0),.005) for v in base.deltas(first,second)[0].values()))
        await self.capture('nested-cold-continued','The actual saved file is open in a fresh Chromium process and the same nested anchor remains directly editable, with its neighbor intact.')

    async def run(self):
        context = await self.browser.new_context(viewport={'width': self.width, 'height': self.height})
        self.page = await context.new_page()
        self.page.set_default_timeout(12000)
        self.page.on('dialog',lambda d:d.accept(d.default_value or 'point-continuation.fsfigure'))
        self.page.on('pageerror', lambda error: self.row['pageErrors'].append(str(error)))
        self.report['entryControllerSHA256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self.report['pointPaintHelperSHA256'] = hashlib.sha256(Path(paint.__file__).read_bytes()).hexdigest()
        try:
            await self.page.goto(self.entry_url(), wait_until='domcontentloaded')
            self.surface = await base.HELPERS.resolve_figure_surface(self.page)
            await base.HELPERS.dismiss_first_run_surface(self.surface)
            self.check('Requested desktop theme is applied',await self.surface.evaluate('document.documentElement.dataset.theme')==('dark-graphite' if self.theme=='dark' else 'light'))
            ids = await self.all_shapes()
            target = ids[0]
            selector = f'.path-node-handle[data-object-id="{target}"][data-command-index="1"][data-handle-type="endpoint"]'
            handle = self.surface.locator(selector)
            await handle.click()
            before = await self.snapshot('grab-before', ids)
            self.check('Public anchor click selects exactly one endpoint', before['direct']['selectedHandleCount'] == 1)
            await self.surface.evaluate('''id=>{
              const canvas=FigureStudio.app.getObjectByIdForQa(id).canvas;
              window.grabEvents=[];
              for(const type of ['pointerdown','pointermove','pointerup'])window.addEventListener(type,e=>{
                const p=canvas.getScenePoint(e);window.grabEvents.push({type,x:p.x,y:p.y,clientX:e.clientX,clientY:e.clientY});
              },true);
            }''', target)
            box = await handle.bounding_box()
            start = (box['x'] + box['width']/2 + 3, box['y'] + box['height']/2 + 2)
            hit = await self.surface.evaluate('''({x,y,selector})=>document.elementFromPoint(x,y)?.matches(selector)''', dict(x=start[0], y=start[1], selector=selector))
            self.check('Off-center pointerdown still targets the actual visible handle', hit)
            predicted = await self.predicted_delta(target, start)
            desired = paint.translated(before['objects'], 0, {(1,1)}, predicted)
            async def action():
                await self.page.keyboard.down('Control')
                await self.page.mouse.move(*start); await self.page.mouse.down()
                await self.page.mouse.move(start[0]+23, start[1]-17, steps=4)
                await self.page.mouse.up(); await self.page.keyboard.up('Control')
            await paint.observe(self, 'off-center-anchor', before['objects'], desired,
                dict(type='pointerdown',selector='.path-node-handle'), action)
            await self.history(before['history']['undoDepth']+1)
            after = await self.snapshot('grab-after', ids)
            events = await self.surface.evaluate('window.grabEvents')
            down = next(e for e in events if e['type'] == 'pointerdown')
            moved = next(e for e in reversed(events) if e['type'] == 'pointermove')
            expected = [moved['x']-down['x'], moved['y']-down['y']]
            actual = base.deltas(before, after)
            self.row['grab'] = dict(events=events, expected=expected, actual=[{str(k):v for k,v in row.items()} for row in actual])
            await self.capture('off-center-anchor-drag', 'The rectangle endpoint has moved by the pointer delta from its off-center grab, with the neighboring ellipse unchanged and the selected endpoint visible.')
            self.check('Off-center anchor follows delivered pointer delta within .005 world units', base.close(actual[0][(1,1)], expected, .005), dict(expected=expected, actual=actual[0][(1,1)]))
            self.check('Other path operands and neighboring ellipse remain fixed', all(base.close(v,(0,0),.005) for i,row in enumerate(actual) for k,v in row.items() if i or k!=(1,1)))
            # A curve anchor carries the incoming/outgoing tangents, preserving
            # their vectors while all other nodes/controls remain fixed.
            await self.page.keyboard.press('Control+z')
            await self.history(before['history']['undoDepth'])
            ellipse = ids[1]
            selector = f'.path-node-handle[data-object-id="{ellipse}"][data-command-index="1"][data-handle-type="endpoint"]'
            first, second = await self.drag_selected(selector, ids, 'curve-anchor')
            moves = base.deltas(first, second)
            delta = moves[1][(1,5)]
            self.row['curveAnchor'] = {str(k):v for k,v in moves[1].items()}
            attached = {(1,3), (1,5), (2,1)}
            self.check('Curve endpoint carries both attached tangent controls by the same world delta', all(base.close(moves[1][key], delta, .005) for key in attached), self.row['curveAnchor'])
            self.check('Curve endpoint leaves other operands and rectangle fixed', all(base.close(value,(0,0),.005) for i,row in enumerate(moves) for key,value in row.items() if i==0 or key not in attached))
            await self.capture('curve-anchor-drag', 'The selected curve anchor and both attached tangents move together while the rest of the ellipse and neighboring rectangle stay fixed.')
            await self.nested_curves(ids)
            self.check('No browser error', not self.row['pageErrors'])
            self.row['status'] = 'passed' if all(row['passed'] for row in self.row['checks']) else 'failed'
            if self.row['status'] != 'passed': raise AssertionError('Point gesture checks failed')
        except BaseException as error:
            self.row['status'] = 'failed'
            self.row['error'] = str(error)
            if not self.page.is_closed():
                await self.page.screenshot(path=str(self.out/'failure.png'))
            raise
        finally:
            await context.close()
            if getattr(self,'cold_context',None):await self.cold_context.close()
            if getattr(self,'cold_browser',None):
                await self.cold_browser.close()
                self.row['coldBrowserClosed']=not self.cold_browser.is_connected()
            self.row['contextClosed'] = True
            self.save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--url', default='')
    parser.add_argument('--expected-app-sha256', default='')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--paint-diagnostic',action='store_true')
    parser.add_argument('--width',type=int,default=1440)
    parser.add_argument('--height',type=int,default=1000)
    parser.add_argument('--theme',choices=['light','dark'],default='light')
    args = parser.parse_args()
    args.smoke = True
    GrabCase.paint_diagnostic=args.paint_diagnostic
    GrabCase.desktop_profile=(args.width,args.height,args.theme)
    base.Case = GrabCase
    asyncio.run(base.run(args))
