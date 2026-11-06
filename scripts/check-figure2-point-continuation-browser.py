"""Actual same-source Figure 2 point editing, Save and fresh-process continuation."""
import argparse
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('point_grab',Path(__file__).with_name('check-path-point-gesture-browser.py'))
grab=importlib.util.module_from_spec(spec);spec.loader.exec_module(grab)
base,paint=grab.base,grab.paint
SOURCE=ROOT/'qa_artifacts/selection21/recovered-originals/5aea6513d86170d1ef11b0643dbdb104416f466444c8d2dd07791ea4df09a208/Figure 2.pdf'
INVENTORY=r'''()=>{
 const app=FigureStudio.app,leaves=[],roots=app.getCanvasObjectInventoryForQa().objects;
 function visit(o){if(!o)return;const children=o.getObjects?.()||[];if(children.length){for(const c of children)visit(c);return;}
 if(o.pdfPageFrame)return;
 leaves.push({id:o.figureId,type:o.type,className:o.constructor.name,path:o.path||null,fill:o.fill,stroke:o.stroke,strokeWidth:o.strokeWidth,
 text:typeof o.text==='string'?o.text:null,bounds:o.getBoundingRect(),matrix:o.calcTransformMatrix(),offset:o.pathOffset||{x:0,y:0},parent:o.group?.figureId});}
 for(const r of roots)visit(app.getObjectByIdForQa(r.id));return {roots,leaves};
}'''
GENUINE_PROBES=r'''({before,expected})=>{
 const app=FigureStudio.app,ctx=document.createElement('canvas').getContext('2d'),old=before[1],next=expected[1],target=app.getObjectByIdForQa(next.id);
 const inverse=m=>{const [a,b,c,d,e,f]=m,q=a*d-b*c;return [d/q,-b/q,-c/q,a/q,(c*f-d*e)/q,(b*e-a*f)/q];};
 const at=(m,x,y)=>[m[0]*x+m[2]*y+m[4],m[1]*x+m[3]*y+m[5]];
 const prep=o=>({...o,iv:inverse(o.matrix),shape:new Path2D(o.path.map(c=>c.join(' ')).join(' '))});
 const shapes=[prep(old),prep(next)],clips=[],guards=[];
 for(let owner=target;owner;owner=owner.group){
   if(owner.opacity!==1||owner.shadow||owner.mask||owner.filters?.length||owner.globalCompositeOperation&&!['source-over'].includes(owner.globalCompositeOperation))throw Error('Unsupported source paint owner');
   let clip=owner.clipPath,parent=owner.calcTransformMatrix();
   while(clip){
     if(clip.inverted||clip.getObjects?.().length)throw Error('Unsupported source clip compound');
     const matrix=clip.absolutePositioned?clip.calcOwnMatrix():fabric.util.multiplyTransformMatrices(parent,clip.calcOwnMatrix());
     const shape=clip.path?new Path2D(clip.path.map(c=>c.join(' ')).join(' ')):null;
     if(!shape&&String(clip.type).toLowerCase()!=='rect')throw Error('Unsupported source clip geometry');
     const path=shape||new Path2D();if(!shape)path.rect(-clip.width/2,-clip.height/2,clip.width,clip.height);
     clips.push({iv:inverse(matrix),shape:path,offset:clip.pathOffset||{x:0,y:0},rule:clip.fillRule||'nonzero'});
     parent=matrix;clip=clip.clipPath;
   }
 }
 const visit=o=>{const children=o.getObjects?.()||[];if(children.length){for(const c of children)visit(c);return;}
   if(o!==target&&!o.pdfPageFrame&&o.visible!==false)guards.push(o.getBoundingRect());};
 for(const r of app.getCanvasObjectInventoryForQa().objects)visit(app.getObjectByIdForQa(r.id));
 const points=shapes.flatMap(o=>o.path.flatMap(c=>{const out=[];for(let i=1;i+1<c.length;i+=2)out.push(at(o.matrix,c[i]-o.offset.x,c[i+1]-o.offset.y));return out;}));
 const minX=Math.min(...points.map(p=>p[0]))-4,maxX=Math.max(...points.map(p=>p[0]))+4,minY=Math.min(...points.map(p=>p[1]))-4,maxY=Math.max(...points.map(p=>p[1]))+4;
 const probes=[],rgb=[1,3,5].map(i=>parseInt(next.paint.fill.slice(i,i+2),16));
 for(let y=minY;y<maxY;y+=.5)for(let x=minX;x<maxX;x+=.5){
   if(guards.some(b=>x>=b.left-2&&x<=b.left+b.width+2&&y>=b.top-2&&y<=b.top+b.height+2))continue;
   if(shapes.some(o=>{const p=at(o.iv,x,y);ctx.lineWidth=4*Math.max(Math.hypot(o.iv[0],o.iv[1]),Math.hypot(o.iv[2],o.iv[3]));return ctx.isPointInStroke(o.shape,p[0]+o.offset.x,p[1]+o.offset.y);}))continue;
   let insideClip=true,boundary=false;
   for(const c of clips){const p=at(c.iv,x,y);p[0]+=c.offset.x;p[1]+=c.offset.y;ctx.lineWidth=4*Math.max(Math.hypot(c.iv[0],c.iv[1]),Math.hypot(c.iv[2],c.iv[3]));boundary ||= ctx.isPointInStroke(c.shape,...p);insideClip&&=ctx.isPointInPath(c.shape,...p,c.rule);}
   if(boundary)continue;
   const p=at(shapes[1].iv,x,y);const inside=insideClip&&ctx.isPointInPath(shapes[1].shape,p[0]+next.offset.x,p[1]+next.offset.y);
   probes.push({x,y,rgb:inside?rgb:[255,255,255]});
 }
 const lower=document.querySelector('canvas.lower-canvas'),canvas=target.canvas,m=canvas.viewportTransform,pixels=lower.getContext('2d').getImageData(0,0,lower.width,lower.height).data;
 let staleMismatches=0;
 for(const p of probes){const [vx,vy]=at(m,p.x,p.y),x=Math.round(vx*lower.width/canvas.width),y=Math.round(vy*lower.height/canvas.height),i=(y*lower.width+x)*4;if(p.rgb.some((c,k)=>Math.abs(c-pixels[i+k])>2))staleMismatches++;}
 return {probes,staleMismatches,policy:'Genuine opaque source path and actual ancestor clips; finite0.5-world-unit grid; exclude2world units about old/new boundaries, clips and all protected leaf bounds; source color/background oracle only, Path2D point queries, no painting.'};
}'''

class GenuineCase(grab.GrabCase):
    async def reject_point_history_control(self,selector,ids):
        await self.surface.locator(selector).click()
        if getattr(self,'reject_point_history_after_collect',False):
            # Create a real Redo branch through public editing and Undo before
            # exercising collection after publication has cleared that branch.
            seed=await self.snapshot('history-rejection-redo-seed',ids)
            box=await self.surface.locator(selector).bounding_box();start=(box['x']+box['width']/2,box['y']+box['height']/2)
            await self.page.keyboard.down('Control');await self.page.mouse.move(*start);await self.page.mouse.down()
            await self.page.mouse.move(start[0],start[1]+60);await self.page.mouse.up();await self.page.keyboard.up('Control')
            await self.history(seed['history']['undoDepth']+1)
            await self.page.keyboard.press('Control+z');await self.history(seed['history']['undoDepth'])
            await self.surface.locator(selector).click()
        before=await self.snapshot('history-rejection-before',ids)
        original=await self.full_artwork('history-rejection-before-complete-fabric')
        late=getattr(self,'reject_point_history_after_collect',False)
        if late:self.check('Late rejection starts with a real public Redo branch',before['history']['redoDepth']>0)
        await self.surface.evaluate('''late=>{
          const proto=FigureStudioPdfHistoryNodeStore.Store.prototype,key=late?'collect':'compactImmutableAsync',original=proto[key];
          window.pointHistoryRejectionCalls=0;window.pointHistoryInjectedRejections=0;
          proto[key]=function(...args){
            const first=!window.pointHistoryRejectionCalls++;
            if(late){const result=original.apply(this,args);if(first){window.pointHistoryInjectedRejections++;throw new Error('QA injected point history failure after actual collection');}return result;}
            if(first){window.pointHistoryInjectedRejections++;return Promise.reject(new Error('QA injected point history serialization failure'));}return original.apply(this,args);
          };
          window.restorePointHistoryRejection=()=>{proto[key]=original;};
        }''',late)
        try:
            box=await self.surface.locator(selector).bounding_box();start=(box['x']+box['width']/2,box['y']+box['height']/2)
            await self.page.keyboard.down('Control');await self.page.mouse.move(*start);await self.page.mouse.down()
            await self.page.mouse.move(start[0],start[1]+60);await self.page.mouse.up();await self.page.keyboard.up('Control')
            await self.surface.app_frame.wait_for_function("window.pointHistoryInjectedRejections===1&&!FigureStudio.app.getBrowserSessionState().busy&&document.querySelector('#toast')?.textContent.includes('previous editing state')",timeout=30000)
            recovered=await self.full_artwork('history-rejection-recovered-complete-fabric')
            normalize=grab_pdf.artwork_without_session_isolation
            self.check('Injected asynchronous history rejection restores complete previous artwork',grab_pdf.equal_serialized_artwork(normalize(original),normalize(recovered)))
            after=await self.snapshot('history-rejection-recovered',ids)
            self.check('Rejected point edit leaves Undo and Redo depths unchanged',before['history']==after['history'])
            self.check('Rejected point edit leaves every marker operand and neighbor in place',all(base.close(v,(0,0),.005) for row in base.deltas(before,after) for v in row.values()))
            self.row['rejectionControl']=dict(policy='One deliberate failure '+('after actual Store.collect publication' if late else 'in existing compactImmutableAsync')+' after a public point gesture; restored before normal continued editing. Fault runs do not qualify normal timing.',**await self.surface.evaluate('({callCount:window.pointHistoryRejectionCalls,injectedRejections:window.pointHistoryInjectedRejections})'))
        finally:
            await self.surface.evaluate('window.restorePointHistoryRejection()')
        if late:
            await self.page.keyboard.press('Control+Shift+z');await self.history(before['history']['undoDepth']+1)
            redone=await self.snapshot('history-rejection-retained-redo',ids)
            self.check('Retained Redo remains usable after actual collection failure',any(not base.close(v,(0,0),.005) for row in base.deltas(before,redone) for v in row.values()))
            await self.page.keyboard.press('Control+z');await self.history(before['history']['undoDepth'])
            await self.surface.locator(selector).click()

    async def actual_pdf_export(self):
        await self.surface.locator('[data-figure-layout-command="export-as"]:visible').first.click()
        await self.surface.locator('[data-export-as-format]').select_option('pdf')
        await self.surface.locator('[data-export-as-scope]').select_option('current')
        await self.surface.app_frame.wait_for_function("FigureStudio.app.getExportAsStateForQa().reviewStatus==='ready'&&!document.querySelector('[data-export-as-submit]').disabled")
        reviewed=await self.surface.evaluate('FigureStudio.app.getExportAsStateForQa()')
        request=reviewed['reviewedRequest']
        self.check('Actual PDF export reviews the current artboard and file destination',request['format']=='pdf' and request['scope']=='current' and request['delivery']=='file' and 'background' not in request)
        async with self.page.expect_download() as pending:
            await self.surface.locator('[data-export-as-submit]').click()
            await self.surface.app_frame.wait_for_function("['error','success'].includes(document.querySelector('[data-export-as-status]')?.dataset.tone)")
        outcome=await self.surface.evaluate("()=>{const e=document.querySelector('[data-export-as-status]');return {tone:e.dataset.tone,message:e.textContent}}")
        self.check('Actual public PDF export reports success',outcome['tone']=='success',outcome)
        pdf=self.out/'genuine-cold-continued-export.pdf'
        await (await pending.value).save_as(pdf)
        self.row['actualPdfExport']=dict(path=str(pdf),bytes=pdf.stat().st_size,sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),reviewed=reviewed,outcome=outcome)
        await self.surface.locator('[data-export-as-close]').click()
        grab_pdf.render_pdf(pdf.read_bytes(),self.out/'genuine-cold-continued-export-pdfium.png')

    async def paint_probes(self,before,expected):
        return await self.surface.evaluate(GENUINE_PROBES,dict(before=before,expected=expected))

    async def prepare_continued_view(self,ids):
        self.continued_gesture=True
        b=await self.surface.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id).getBoundingRect()',ids[1])
        await self.surface.locator('#viewport').focus();await self.page.keyboard.press('z')
        await base.HELPERS.drag_scene(self.surface,(b['left']-18,b['top']-18),(b['left']+b['width']+18,b['top']+b['height']+18))

    async def full_artwork(self,name):
        data=json.loads(await self.surface.evaluate('()=>JSON.stringify(FigureStudio.app.buildProjectJsonForQa().fabric)'))
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2),encoding='utf-8')
        return data

    async def drag_selected(self,selector,ids,name):
        handle=self.surface.locator(selector);await handle.click()
        before=await self.snapshot(name+'-before',ids)
        box=await handle.bounding_box();start=(box['x']+box['width']/2+2,box['y']+box['height']/2+1)
        self.check(name+' pointerdown hits the actual visible anchor',await self.surface.evaluate('p=>document.elementFromPoint(p.x,p.y)?.matches(p.selector)',dict(x=start[0],y=start[1],selector=selector)))
        await self.surface.evaluate('window.grabEvents=[]')
        screen_delta=(0,-60) if getattr(self,'continued_gesture',False) else (0,60)
        delta=await self.predicted_delta(ids[1],start,screen_delta)
        expected=paint.translated(before['objects'],1,{(1,3),(1,5),(2,1)},delta)
        async def action():
            await self.page.keyboard.down('Control');await self.page.mouse.move(*start);await self.page.mouse.down()
            await self.page.mouse.move(start[0]+screen_delta[0],start[1]+screen_delta[1]);await self.page.mouse.up();await self.page.keyboard.up('Control')
        session=None
        if getattr(self,'profile_gestures',False):
            session=await self.page.context.new_cdp_session(self.page)
            await session.send('Profiler.enable');await session.send('Profiler.start')
        try:
            await paint.observe(self,name,before['objects'],expected,dict(type='pointerdown',selector='.path-node-handle'),action)
        finally:
            if session:
                profile=(await session.send('Profiler.stop'))['profile']
                path=self.out/(name+'-cpu-profile.json');path.write_text(json.dumps(profile),encoding='utf-8')
                self.row.setdefault('diagnosticProfiles',[]).append(dict(name=name,path=str(path),summary=grab_pdf.summarize_cpu_profile(profile),policy='CPU instrumentation is diagnostic only; this run cannot qualify normal timing.'))
                await session.detach()
        await self.history(before['history']['undoDepth']+1)
        after=await self.snapshot(name+'-after',ids)
        attached={(1,3),(1,5),(2,1)}
        await self.bind_delivered_delta(name,before,after,1,attached)
        self.check(name+' leaves all other operands and the neighboring path fixed',all(base.close(v,(0,0),.005) for i,row in enumerate(base.deltas(before,after)) for k,v in row.items() if i==0 or k not in attached))
        return before,after

    async def run(self):
        context=await self.browser.new_context(viewport=dict(width=self.width,height=self.height),color_scheme=self.theme)
        await context.add_init_script('try{delete window.showSaveFilePicker;delete window.showOpenFilePicker;}catch(_){}')
        self.page=await context.new_page();self.page.set_default_timeout(15000)
        self.page.on('pageerror',lambda e:self.row['pageErrors'].append(str(e)))
        self.page.on('dialog',lambda d:d.accept(d.default_value or 'figure2-point.fsfigure'))
        try:
            self.check('Exact original Figure 2 source is unchanged',hashlib.sha256(SOURCE.read_bytes()).hexdigest()=='5aea6513d86170d1ef11b0643dbdb104416f466444c8d2dd07791ea4df09a208')
            await self.page.goto(self.entry_url(),wait_until='domcontentloaded')
            self.surface=await base.HELPERS.resolve_figure_surface(self.page)
            await base.HELPERS.dismiss_first_run_surface(self.surface)
            self.check('Requested desktop theme is applied',await self.surface.evaluate('document.documentElement.dataset.theme')==('dark-graphite' if self.theme=='dark' else 'light'))
            await self.surface.locator('[data-menu="file"] > .menu-trigger').click()
            await self.surface.locator('[data-menu="file"] [data-command="new-project"]').click()
            await self.surface.locator('#newDocumentBackdrop').wait_for(state='visible')
            async with self.page.expect_file_chooser() as chooser:
                await self.surface.locator('#openArtworkDocumentBtn:visible').click()
            selected=await chooser.value
            self.check('Public artwork chooser is the original-artwork input',await selected.element.get_attribute('id')=='openArtworkDocumentInput')
            await selected.set_files(SOURCE)
            await self.surface.locator('#importPlacementReview:not([hidden])').wait_for()
            await self.surface.locator('#pdfEntryModeSelect:visible').select_option('editable')
            await self.surface.locator('#pdfPageModeSelect:visible').select_option('custom')
            await self.surface.locator('#pdfPageRangeInput:visible').fill('1')
            await self.surface.locator('#importPlacementCenterBtn:visible').click()
            await self.surface.locator('#importPlacementReview').wait_for(state='hidden')
            await self.surface.app_frame.wait_for_function('FigureStudio.app.getBrowserSessionState().ready&&!FigureStudio.app.getBrowserSessionState().busy')
            inventory=await self.surface.evaluate(INVENTORY);self.row['sourceInventory']=inventory
            texts=[o for o in inventory['leaves'] if o['text'] is not None]
            paths=[o for o in inventory['leaves'] if o['path']]
            text_source=await self.surface.evaluate('''()=>{const a=FigureStudio.app,root=a.getObjectByIdForQa(a.getCanvasObjectInventoryForQa().objects[0].id);let glyphs=0;function visit(o){glyphs+=o.pdfTextSource?.glyphs?.length||0;for(const c of o.getObjects?.()||[])visit(c);}visit(root);return{glyphs,membership:root.importMeta.pdfEditableImport.sourceTextItems||null};}''')
            membership=text_source['membership'];expected_texts=960-(membership['sourceSpans']-membership['joinedItems'])if membership else 960
            self.check('Genuine Figure 2 retains343 paths,2817 source glyphs and exact admitted text ownership',len(paths)==343 and len(texts)==expected_texts and text_source['glyphs']==2817,dict(paths=len(paths),liveText=len(texts),expectedTextUnits=expected_texts,**text_source))
            candidates=[o for o in paths if len(o['path'])==5 and all(c[0]=='C' for c in o['path'][1:]) and o['fill']=='#ff0700']
            candidates.sort(key=lambda o:o['bounds']['width']*o['bounds']['height'],reverse=True)
            self.check('Source contains the unique Affinity-matched red four-cubic marker',len(candidates)==1)
            target=candidates[0]
            neighbor=next(o for o in paths if o['id']!=target['id'])
            ids=[neighbor['id'],target['id']]
            self.row['target']=dict(policy='Unique #ff0700 four-cubic source point, matched to independently parsed Affinity source paint203/operator3338; single delivered pointermove, verticalscreen delta0,+60 then0,-60 after fresh Open, predeclared before dispatch. Earlier diagonal gestures with empty changed-pixel coverage remain inconclusive; genuine2 four-move delay is retained separately.',record=target)
            self.check('The selected marker matches the actual Affinity comparator source geometry',base.close(base.points(target)[(0,1)],(461.2513*4/3,(792-329.728)*4/3),.001))
            self.check('Selected source point uses the ordinary native clipped path plane',target['className']=='PdfNativeRectClippedPath')
            original=await self.full_artwork('genuine-before-complete-fabric')
            # Public Zoom marquee establishes a usable edit scale before selection.
            b=target['bounds'];a=(b['left']-18,b['top']-18);z=(b['left']+b['width']+18,b['top']+b['height']+18)
            await self.surface.locator('#viewport').focus();await self.page.keyboard.press('z')
            await base.HELPERS.drag_scene(self.surface,a,z)
            await self.page.keyboard.press('a')
            point=await self.surface.evaluate('id=>FigureStudio.app.getPathSegmentPointForQa(id,0,.5)',target['id'])
            client=await base.HELPERS.canvas_scene_point(self.surface,point['x'],point['y'])
            await self.page.mouse.click(client['x'],client['y'])
            selector=f'.path-node-handle[data-object-id="{target["id"]}"][data-command-index="1"][data-handle-type="endpoint"]'
            self.check('Public Direct Selection reaches the genuine source point',await self.surface.locator(selector).count()==1)
            await self.surface.evaluate('''id=>{const c=FigureStudio.app.getObjectByIdForQa(id).canvas;window.grabEvents=[];for(const type of ['pointerdown','pointermove','pointerup'])window.addEventListener(type,e=>{const p=c.getScenePoint(e);window.grabEvents.push({type,x:p.x,y:p.y,clientX:e.clientX,clientY:e.clientY});},true);}''',target['id'])
            if getattr(self,'reject_point_history_once',False):await self.reject_point_history_control(selector,ids)
            before,after=await self.drag_selected(selector,ids,'genuine-anchor')
            await self.capture('genuine-anchor-moved','The same glycerophospholipid marker used in Affinity has one anchor and both attached tangents moved; surrounding live labels and other points remain intact.')
            await self.page.keyboard.press('Control+z');await self.history(before['history']['undoDepth'])
            undone=await self.snapshot('genuine-undone',ids)
            self.check('One public Undo restores every source operand',all(base.close(v,(0,0),.005) for row in base.deltas(before,undone) for v in row.values()))
            await self.page.keyboard.press('Control+Shift+z');await self.history(after['history']['undoDepth'])
            redone=await self.snapshot('genuine-redone',ids)
            self.check('One public Redo restores the genuine point edit',all(base.close(v,(0,0),.005) for row in base.deltas(after,redone) for v in row.values()))
            edited=await self.full_artwork('genuine-edited-complete-fabric')
            after_inventory=await self.surface.evaluate(INVENTORY);self.row['editedInventory']=after_inventory
            def leaves(value):
                result={}
                def visit(o):
                    if isinstance(o,dict):
                        children=o.get('objects',[])
                        if children:
                            for c in children:visit(c)
                        elif o.get('figureId'):result[o['figureId']]=o
                visit(value)
                return result
            initial,changed=leaves(original),leaves(edited)
            poses={o['id']:o['matrix'] for o in inventory['leaves']};new_poses={o['id']:o['matrix'] for o in after_inventory['leaves']}
            authored=lambda o:{k:v for k,v in o.items() if k not in ('left','top','figureStudioIsolationMeta')}
            self.check('All protected leaves retain their complete authored fields and world pose',initial.keys()==changed.keys() and all(authored(initial[k])==authored(changed[k]) and all(abs(a-b)<=.005 for a,b in zip(poses[k],new_poses[k])) for k in initial if k!=target['id']),dict(protectedLeaves=len(initial)-1,liveText=len(texts),policy='Only localleft/top rebase is permitted when the full worldmatrix stays within.005; all other saved leaf fields remain exact.'))
            await self.saved_continuation(ids,redone)
            self.check('Actual Save retains exact original PDF bytes',SOURCE.read_bytes() in grab_pdf.embedded_sources(json.loads(Path(self.row['actualSave']['path']).read_text(encoding='utf-8'))))
            await self.actual_pdf_export()
            continued=await self.full_artwork('genuine-cold-continued-complete-fabric')
            second_save=self.out/'genuine-cold-continued.fsfigure'
            async with self.page.expect_download() as pending:
                await self.surface.locator('body').press('Control+s')
            await (await pending.value).save_as(second_save)
            second=json.loads(second_save.read_text(encoding='utf-8')).get('project',{})
            self.check('Actual second Save contains the complete continued artwork',grab_pdf.equal_serialized_artwork(grab_pdf.artwork_without_session_isolation(continued),grab_pdf.artwork_without_session_isolation(second['fabric'])))
            self.check('Actual second Save retains the original PDF bytes',SOURCE.read_bytes() in grab_pdf.embedded_sources(second))
            self.row['actualSecondSave']=dict(path=str(second_save),bytes=second_save.stat().st_size,sha256=hashlib.sha256(second_save.read_bytes()).hexdigest())
            self.check('No browser errors',not self.row['pageErrors'])
            self.row['status']='passed' if all(c['passed'] for c in self.row['checks']) else 'failed'
            if self.row['status']!='passed':raise AssertionError('Genuine point journey failed')
        except BaseException as e:
            self.row['status']='failed';self.row['error']=str(e)
            if not self.page.is_closed():await self.page.screenshot(path=str(self.out/'failure.png'))
            raise
        finally:
            await context.close()
            if getattr(self,'cold_context',None):await self.cold_context.close()
            if getattr(self,'cold_browser',None):await self.cold_browser.close()
            self.row['contextClosed']=True;self.save()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--url',default='');p.add_argument('--expected-app-sha256',default='');p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--profile-gestures',action='store_true')
    p.add_argument('--reject-point-history-once',action='store_true')
    p.add_argument('--reject-point-history-after-collect',action='store_true')
    p.add_argument('--width',type=int,default=1440);p.add_argument('--height',type=int,default=1000);p.add_argument('--theme',choices=['light','dark'],default='light')
    args=p.parse_args();args.smoke=True
    GenuineCase.profile_gestures=args.profile_gestures
    GenuineCase.reject_point_history_once=args.reject_point_history_once or args.reject_point_history_after_collect
    GenuineCase.reject_point_history_after_collect=args.reject_point_history_after_collect
    GenuineCase.desktop_profile=(args.width,args.height,args.theme)
    s=importlib.util.spec_from_file_location('genuine_pdf',ROOT/'scripts/check-figure-pdf-editing-browser.py')
    grab_pdf=importlib.util.module_from_spec(s);s.loader.exec_module(grab_pdf)
    base.Case=GenuineCase
    asyncio.run(base.run(args))
