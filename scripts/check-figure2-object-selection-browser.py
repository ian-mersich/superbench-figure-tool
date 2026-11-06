"""Public Figure2 mixed-object selection, movement and actual saved-file continuity."""
import argparse,asyncio,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
g=load('mixed_genuine',ROOT/'scripts/check-figure2-point-continuation-browser.py');base=g.base
pdf=load('mixed_pdf',ROOT/'scripts/check-figure-pdf-editing-browser.py')
STATE='''()=>{const a=FigureStudio.app,s=a.getGroupIsolationStateForQa();delete s.hierarchy;return{selection:a.getSelectionStateForQa(),history:a.getHistoryStateForQa(),isolation:s,ownedMarquee:Boolean(document.querySelector('.isolation-object-marquee')),liveCandidates:document.querySelector('[data-selection-marquee-count]')?.textContent||null};}'''
# Window capture observes each original trusted event before App document/target handlers.
WITNESS='''()=>{window.mixedInput=[];const a=FigureStudio.app,c=a.getObjectByIdForQa(a.getCanvasObjectInventoryForQa().objects[0].id).canvas;for(const type of ['pointerdown','pointermove','pointerup'])window.addEventListener(type,e=>{const p=c.getScenePoint(e);window.mixedInput.push({type,trusted:e.isTrusted,pointerId:e.pointerId,x:p.x,y:p.y,timeStamp:e.timeStamp,observedAt:performance.now()});},true);}'''
def equivalent(a,b):return pdf.artwork_without_session_isolation(a)==pdf.artwork_without_session_isolation(b)
def expected_marquee(inventory,start,end,root):
    left,right=sorted([start[0],end[0]]);top,bottom=sorted([start[1],end[1]])
    return {o['id']for o in inventory['leaves']if o['parent']==root and o['bounds']['left']<=right and o['bounds']['left']+o['bounds']['width']>=left and o['bounds']['top']<=bottom and o['bounds']['top']+o['bounds']['height']>=top}
def rigid(before,after,selected,delta):
    old={o['id']:o for o in before['leaves']};errors=[]
    if set(old)!={o['id']for o in after['leaves']}:return ['leaf identity changed']
    for o in after['leaves']:
        previous=old[o['id']];expected=delta if o['id']in selected else(0,0)
        actual=(o['matrix'][4]-previous['matrix'][4],o['matrix'][5]-previous['matrix'][5])
        if any(abs(x-y)>1e-6 for x,y in zip(actual,expected)) or any(previous[k]!=o[k]for k in ['path','text','parent','fill','stroke','strokeWidth','offset']) or previous['matrix'][:4]!=o['matrix'][:4]:errors.append(dict(id=o['id'],actual=actual,expected=expected))
    return errors

class MixedCase(g.GenuineCase):
    def __init__(self,*values):
        values=list(values);values[3],values[4]=map(int,ARGS.viewport.lower().split('x'));values[5]=ARGS.theme
        super().__init__(*values)
    async def snap(self,name):
        s=await self.surface.evaluate(STATE);self.row['states'][name]=s;self.save();return s
    async def settled(self):
        await self.surface.app_frame.wait_for_function('!document.querySelector("#studioShell")?.inert&&!FigureStudio.app.getBrowserSessionState().busy')
        await self.surface.wait_for_visual_stability()
    async def check_badge(self,name):
        result=await self.surface.evaluate('''()=>{const b=document.querySelector('#isolationSelectionCount:not([hidden])'),v=document.querySelector('#viewport');if(!b)return{passed:false,reason:'No visible count'};const r=b.getBoundingClientRect(),p=v.getBoundingClientRect(),h=document.querySelector('#horizontalRuler'),w=document.querySelector('#verticalRuler');const top=h&&!h.hidden?h.getBoundingClientRect().bottom:p.top,left=w&&!w.hidden?w.getBoundingClientRect().right:p.left;return{passed:r.top>=top+4&&r.left>=left+4&&r.right<=p.right-8&&r.bottom<=p.bottom-8&&parseFloat(getComputedStyle(b).fontSize)>=12&&!b.closest('#canvasStage'),text:b.textContent,rect:{left:r.left,top:r.top,right:r.right,bottom:r.bottom},fontSize:getComputedStyle(b).fontSize};}''')
        self.check(name+' count is readable and stays inside the visible canvas',result['passed'],result)
    async def marquee(self,name,start,end,shift=False,cancel=False):
        first=await base.HELPERS.canvas_scene_point(self.surface,*start);last=await base.HELPERS.canvas_scene_point(self.surface,*end)
        before=await self.snap(name+'-before')
        inventory=await self.surface.evaluate(g.INVENTORY);await self.surface.evaluate('window.mixedInput=[]')
        if shift:await self.page.keyboard.down('Shift')
        await self.page.mouse.move(first['x'],first['y']);await self.page.mouse.down();await self.page.mouse.move(last['x'],last['y'],steps=8)
        await self.surface.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
        held=await self.snap(name+'-held')
        inputs=await self.surface.evaluate('window.mixedInput');down=next(e for e in inputs if e['type']=='pointerdown');move=next(e for e in reversed(inputs)if e['type']=='pointermove')
        expected=expected_marquee(inventory,(down['x'],down['y']),(move['x'],move['y']),inventory['roots'][0]['id'])
        self.row.setdefault('marqueeWitnesses',{})[name]=dict(inputs=inputs,expectedDirectLeafIds=sorted(expected),policy='Original window-capture trusted scene events and pre-gesture native bounds. Figure2 panelF contains direct native text/path leaves; no reconstruction or setter.')
        self.check(name+' shows live candidates before release',held['ownedMarquee']and bool(held['liveCandidates']))
        await self.check_badge(name)
        if name in ['partial-labels','expanded-labels-bars-axis']:await self.capture(name+'-held','The correct Figure2 panelF shows thin candidate outlines and an unclipped object count while native labels and bars remain readable.')
        if cancel:await self.page.keyboard.press('Escape')
        await self.page.mouse.up()
        if shift:await self.page.keyboard.up('Shift')
        await self.settled();after=await self.snap(name+'-released')
        self.check(name+' changes no history',before['history']==after['history'])
        if cancel:self.check(name+' Escape restores the original selected set',before['selection']['selectedIds']==after['selection']['selectedIds'])
        else:
            original=set(before['selection']['selectedIds']);expected=original.symmetric_difference(expected)if shift else expected
            self.check(name+' selects exactly the native objects intersecting the delivered rectangle',set(after['selection']['selectedIds'])==expected,dict(expected=sorted(expected),actual=after['selection']['selectedIds']))
        return after
    async def body(self,name,selected,target,delta,cancel=False,returned=False,reject=False):
        before=await self.surface.evaluate(g.INVENTORY);before_art=await self.full_artwork(name+'-before');state=await self.snap(name+'-before')
        o=next(o for o in before['leaves']if o['id']==target);b=o['bounds'];start=(b['left']+b['width']/2,b['top']+b['height']/2)
        first=await base.HELPERS.canvas_scene_point(self.surface,*start);last=await base.HELPERS.canvas_scene_point(self.surface,start[0]+delta[0],start[1]+delta[1])
        await self.surface.evaluate('window.mixedInput=[]')
        if reject:
            await self.surface.evaluate('''()=>{const p=FigureStudioPdfHistoryNodeStore.Store.prototype,old=p.compactImmutableAsync;window.mixedRejected=0;p.compactImmutableAsync=function(...args){if(!window.mixedRejected++){return Promise.reject(Error('QA mixed-object history failure'));}return old.apply(this,args);};window.restoreMixedStore=()=>{p.compactImmutableAsync=old;};}''')
        await self.page.mouse.move(first['x'],first['y']);await self.page.mouse.down();await self.page.mouse.move(last['x'],last['y'],steps=10)
        inputs=await self.surface.evaluate('window.mixedInput');down=next(e for e in inputs if e['type']=='pointerdown');move=next(e for e in reversed(inputs)if e['type']=='pointermove')
        delivered=(move['x']-down['x'],move['y']-down['y']);self.row.setdefault('inputWitnesses',{})[name]=dict(inputs=inputs,delivered=delivered,policy='Original trusted events at window capture before App handlers; functional geometry only, no latency acceptance.')
        self.check(name+' delivers trusted original pointer movement',down['trusted']and move['trusted']and abs(delivered[0]-delta[0])<.005 and abs(delivered[1]-delta[1])<.005)
        held=await self.snap(name+'-held');moved=await self.surface.evaluate(g.INVENTORY)
        await self.check_badge(name+'-held')
        self.check(name+' retains all selected objects',set(held['selection']['selectedIds'])==set(selected))
        errors=rigid(before,moved,selected,delivered);self.check(name+' moves only selected native leaves rigidly',not errors,errors[:12])
        if name=='mixed-body':await self.capture(name+'-held','The selected native labels, bars and axis move together with readable selection outlines; neighboring unselected artwork stays fixed.')
        if returned:await self.page.mouse.move(first['x'],first['y'],steps=5)
        if cancel:await self.page.keyboard.press('Escape')
        await self.page.mouse.up()
        if reject:
            await self.surface.app_frame.wait_for_function("window.mixedRejected>0&&!document.querySelector('#studioShell')?.inert&&document.querySelector('#toast')?.textContent.includes('previous editing state')")
            await self.surface.evaluate('window.restoreMixedStore()')
        elif not cancel and not returned:await self.history(state['history']['undoDepth']+1)
        await self.settled();after=await self.snap(name+'-released');art=await self.full_artwork(name+'-after')
        if cancel or returned or reject:
            self.check(name+' restores complete artwork',equivalent(before_art,art));self.check(name+' leaves Undo and Redo unchanged',state['history']==after['history'])
        else:
            self.check(name+' creates exactly one Undo step',after['history']['undoDepth']==state['history']['undoDepth']+1)
            errors=rigid(before,await self.surface.evaluate(g.INVENTORY),selected,delivered);self.check(name+' release preserves full native geometry and neighbors',not errors,errors[:12])
        return before_art,art,state,after
    async def save_file(self,name,warm):
        path=self.out/(name+'.fsfigure')
        async with self.page.expect_download()as download:await self.surface.locator('body').press('Control+s')
        await(await download.value).save_as(path);payload=json.loads(path.read_text(encoding='utf-8'));saved=payload.get('project',payload)['fabric']
        self.check(name+' actual Save preserves complete artwork',equivalent(warm,saved))
        self.row.setdefault('savedFiles',[]).append(dict(path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        return path,saved
    async def run(self):
        self.cold_browser=None;context=None
        try:
            context=await self.browser.new_context(viewport=dict(width=self.width,height=self.height),color_scheme=self.theme)
            await context.add_init_script('try{delete window.showSaveFilePicker;delete window.showOpenFilePicker;}catch(_){}')
            self.page=await context.new_page();self.page.set_default_timeout(25000)
            self.page.on('pageerror',lambda e:self.row['pageErrors'].append(str(e)));self.page.on('dialog',lambda d:d.accept(d.default_value or 'figure2-mixed.fsfigure'))
            await self.page.goto(self.entry_url(),wait_until='domcontentloaded');self.surface=await base.HELPERS.resolve_figure_surface(self.page);await base.HELPERS.dismiss_first_run_surface(self.surface)
            await self.surface.locator('[data-menu="file"] > .menu-trigger').click();await self.surface.locator('[data-menu="file"] [data-command="new-project"]').click();await self.surface.locator('#newDocumentBackdrop').wait_for(state='visible')
            async with self.page.expect_file_chooser()as chooser:await self.surface.locator('#openArtworkDocumentBtn:visible').click()
            await(await chooser.value).set_files(g.SOURCE);await self.surface.locator('#importPlacementReview:not([hidden])').wait_for()
            await self.surface.locator('#pdfEntryModeSelect:visible').select_option('editable');await self.surface.locator('#pdfPageModeSelect:visible').select_option('custom');await self.surface.locator('#pdfPageRangeInput:visible').fill('1');await self.surface.locator('#importPlacementCenterBtn:visible').click();await self.surface.locator('#importPlacementReview').wait_for(state='hidden')
            await self.surface.app_frame.wait_for_function('FigureStudio.app.getBrowserSessionState().ready&&!FigureStudio.app.getBrowserSessionState().busy')
            inventory=await self.surface.evaluate(g.INVENTORY);self.row['sourceInventory']=inventory
            self.check('Original Figure2 bytes are unchanged',hashlib.sha256(g.SOURCE.read_bytes()).hexdigest()=='5aea6513d86170d1ef11b0643dbdb104416f466444c8d2dd07791ea4df09a208')
            title=next(o for o in inventory['leaves']if 'Reactome pathways - genes up' in(o['text']or''));f=next(o for o in inventory['leaves']if o['text']=='F'and o['bounds']['left']<title['bounds']['left']and abs(o['bounds']['top']-title['bounds']['top'])<30)
            b=f['bounds'];t=title['bounds'];self.row['targets']=dict(panelF=f,title=title)
            await self.surface.locator('#viewport').focus();await self.page.keyboard.press('z');await base.HELPERS.drag_scene(self.surface,(b['left']-30,b['top']-20),(t['left']+t['width']+150,b['top']+300));await self.page.keyboard.press('v');await self.page.keyboard.press('Escape')
            await self.capture('before','The actual panelF letter and genes-up Reactome plot are visible at usable desktop scale before selection.')
            await self.surface.evaluate(WITNESS)
            start=(b['left']-20,b['top']-10);partial=(b['left']+36,b['top']+67);end=(t['left']+t['width']-5,b['top']+110)
            first=await self.marquee('partial-labels',start,partial);self.check('Partial-label marquee selects descendants',first['selection']['selectedCount']>0 and not set(first['selection']['selectedIds'])&{o['id']for o in inventory['roots']})
            after=await self.marquee('expanded-labels-bars-axis',start,end);selected=after['selection']['selectedIds'];members=[o for o in inventory['leaves']if o['id']in selected]
            self.check('Expanded marquee selects both native text and paths',len(selected)>first['selection']['selectedCount']and any(o['text']is not None for o in members)and any(o['path']for o in members))
            removed=await self.marquee('shift-remove',start,end,shift=True);self.check('Shift marquee removes its last selected objects',removed['selection']['selectedCount']==0)
            added=await self.marquee('shift-add',start,end,shift=True);self.check('Shift marquee adds the original objects',set(added['selection']['selectedIds'])==set(selected))
            await self.marquee('escape-marquee',start,partial,cancel=True)
            current=await self.surface.evaluate(g.INVENTORY);bar=next(o for o in current['leaves']if o['id']in selected and o['path']and o.get('fill')and o['bounds']['width']>10 and o['bounds']['height']>2);self.row['bodyTarget']=bar
            await self.body('escape-body',selected,bar['id'],(9,6),cancel=True)
            await self.body('return-to-grab',selected,bar['id'],(9,6),returned=True)
            before,moved,state,released=await self.body('mixed-body',selected,bar['id'],(-12,-18))
            await self.capture('mixed-body-released','The complete mixed-object move remains selected and fully painted after release, with neighboring scientific content intact.')
            await self.page.keyboard.press('Control+z');await self.history(state['history']['undoDepth']);await self.settled();undone=await self.full_artwork('mixed-undo');self.check('Undo restores complete pre-move artwork',equivalent(before,undone))
            await self.page.keyboard.press('Control+y');await self.history(released['history']['undoDepth']);await self.settled();redone=await self.full_artwork('mixed-redo');self.check('Redo restores the complete moved artwork',equivalent(moved,redone));await self.capture('mixed-redo','Redo paints the completed mixed-object move with the same selected region and intact neighbors.')
            await self.body('rejected-history',selected,bar['id'],(5,4),reject=True)
            warm=await self.full_artwork('warm-complete-fabric');project,saved=await self.save_file('mixed-first',warm)
            await context.close();context=None;browser_type=self.browser.browser_type;await self.browser.close();self.row['warmBrowserClosed']=not self.browser.is_connected()
            self.cold_browser=await browser_type.launch(**self.report['browserLaunchOptions']);await base.record_browser_runtime(self.cold_browser,self.report,'cold')
            context=await self.cold_browser.new_context(viewport=dict(width=self.width,height=self.height),color_scheme=self.theme);await context.add_init_script('try{delete window.showSaveFilePicker;delete window.showOpenFilePicker;}catch(_){}')
            self.page=await context.new_page();self.page.set_default_timeout(25000);self.page.on('pageerror',lambda e:self.row['pageErrors'].append(str(e)));self.page.on('dialog',lambda d:d.accept(d.default_value or 'figure2-mixed-continued.fsfigure'))
            await self.page.goto(self.entry_url(),wait_until='domcontentloaded');self.surface=await base.HELPERS.resolve_figure_surface(self.page);await base.HELPERS.dismiss_first_run_surface(self.surface)
            async with self.page.expect_file_chooser()as chooser:await self.surface.locator('body').press('Control+o')
            await(await chooser.value).set_files(project);await self.surface.app_frame.wait_for_function("document.querySelector('#documentFileOperationStatus')?.dataset.state==='success'&&!FigureStudio.app.getBrowserSessionState().busy")
            cold=await self.full_artwork('cold-complete-fabric');self.check('Fresh Chromium Open preserves complete saved artwork',equivalent(saved,cold))
            await self.surface.locator('#viewport').focus();await self.page.keyboard.press('v');await self.page.keyboard.press('Escape')
            # Locate the moved native plot in its own current scene, using only read-only geometry.
            cold_inventory=await self.surface.evaluate(g.INVENTORY);new_f=next(o for o in cold_inventory['leaves']if o['id']==f['id']);dx=new_f['bounds']['left']-b['left'];dy=new_f['bounds']['top']-b['top']
            await self.page.keyboard.press('z');await base.HELPERS.drag_scene(self.surface,(b['left']-30+dx,b['top']-20+dy),(t['left']+t['width']+150+dx,b['top']+300+dy));await self.page.keyboard.press('v');await self.page.keyboard.press('Escape');await self.surface.evaluate(WITNESS)
            cold_set=await self.marquee('cold-marquee',(start[0]+dx,start[1]+dy),(end[0]+dx,end[1]+dy));continued=cold_set['selection']['selectedIds']
            self.check('Cold public marquee reaches every original native mixed object',set(selected).issubset(continued),dict(originalCount=len(selected),coldCount=len(continued),explanation='The translated rectangle can also intersect previously unselected stationary neighbors; the independent delivered-rectangle check above requires its entire set exactly.'))
            await self.body('cold-continued-body',continued,bar['id'],(-6,-9));await self.capture('cold-continued','The saved file is open in a fresh Chromium process and its same native mixed objects remain selectable and draggable, with neighboring content fixed.')
            second=await self.full_artwork('cold-continued-complete-fabric');await self.save_file('mixed-second',second)
            self.check('No browser page errors',not self.row['pageErrors'],self.row['pageErrors'])
            if not all(check['passed']for check in self.row['checks']):raise AssertionError('At least one mixed-object selection or saved-file check failed')
            self.row['status']='passed';self.save()
        except BaseException as error:
            self.row['status']='failed';self.row['error']=str(error)
            if hasattr(self,'page')and not self.page.is_closed():await self.page.screenshot(path=str(self.out/'failure.png'))
            raise
        finally:
            if context:await context.close()
            if self.cold_browser:await self.cold_browser.close();self.row['coldBrowserClosed']=not self.cold_browser.is_connected()
            self.row['contextClosed']=True;self.save()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--expected-app-sha256',required=True);p.add_argument('--viewport',default='1440x1000');p.add_argument('--theme',choices=['light','dark'],default='light');ARGS=p.parse_args()
    ARGS.smoke=True;ARGS.url='';ARGS.browser_channel='chromium';base.Case=MixedCase;asyncio.run(base.run(ARGS))
