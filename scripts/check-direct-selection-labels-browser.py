"""Public path-anchor and editable-label selection with real saved continuation."""
import argparse, asyncio, hashlib, importlib.util, json, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('label_public_import',ROOT/'scripts/check-figure2-whole-label-browser.py')
label=importlib.util.module_from_spec(spec);spec.loader.exec_module(label)
m=label.m
STATE='()=>({direct:FigureStudio.app.getDirectSelectionStateForQa(),selection:FigureStudio.app.getSelectionStateForQa(),history:FigureStudio.app.getHistoryStateForQa()})'

class Selection(label.Open):
    def phase(self,name):
        self.row.setdefault('phases',[]).append(dict(name=name,elapsedSeconds=time.perf_counter()-self.started));self.save()
    async def export_file(self,kind,name):
        self.phase('export-'+kind+'-start')
        result=await super().export_file(kind,name)
        self.phase('export-'+kind+'-finished');return result
    def require(self,name,condition,detail=None):
        self.check(name,condition,detail)
        if not condition:raise AssertionError(name)
    async def state(self,name):
        result=await self.surface.evaluate(STATE);self.row['states'][name]=result;self.save();return result
    async def open_surface(self,browser,project=None):
        context=await browser.new_context(viewport=dict(width=self.width,height=self.height),color_scheme=self.theme)
        await context.add_init_script('try{delete window.showSaveFilePicker;delete window.showOpenFilePicker;}catch(_){}')
        self.page=await context.new_page();self.page.set_default_timeout(30000);self.page.on('pageerror',lambda e:self.row['pageErrors'].append(str(e)))
        self.page.on('dialog',lambda d:d.accept(d.default_value or 'mixed-direct-selection.fsfigure'))
        await self.page.goto(self.entry_url(),wait_until='domcontentloaded');self.surface=await m.base.HELPERS.resolve_figure_surface(self.page);await m.base.HELPERS.dismiss_first_run_surface(self.surface)
        if project:
            async with self.page.expect_file_chooser()as chooser:await self.surface.locator('body').press('Control+o')
            await(await chooser.value).set_files(project);await self.surface.app_frame.wait_for_function("document.querySelector('#documentFileOperationStatus')?.dataset.state==='success'&&!FigureStudio.app.getBrowserSessionState().busy")
        else:
            await self.surface.locator('[data-menu="file"] > .menu-trigger').click();await self.surface.locator('[data-menu="file"] [data-command="new-project"]').click();await self.surface.locator('#newDocumentBackdrop').wait_for(state='visible')
            async with self.page.expect_file_chooser()as chooser:await self.surface.locator('#openArtworkDocumentBtn:visible').click()
            await(await chooser.value).set_files(ARGS.fixture);await self.surface.locator('#importPlacementReview:not([hidden])').wait_for()
            await self.surface.locator('#pdfEntryModeSelect:visible').select_option('editable');await self.surface.locator('#pdfPageModeSelect:visible').select_option('custom');await self.surface.locator('#pdfPageRangeInput:visible').fill('1');await self.surface.locator('#importPlacementCenterBtn:visible').click();await self.surface.locator('#importPlacementReview').wait_for(state='hidden')
            await self.surface.app_frame.wait_for_function('FigureStudio.app.getBrowserSessionState().ready&&!FigureStudio.app.getBrowserSessionState().busy')
        await self.settled();return context
    async def focus_plot(self,keep_scope=False):
        inventory=await self.surface.evaluate(m.g.INVENTORY)
        title=next(o for o in inventory['leaves']if 'Reactome pathways - genes up'in(o['text']or''))
        f=next(o for o in inventory['leaves']if o['text']=='F'and o['bounds']['left']<title['bounds']['left']and abs(o['bounds']['top']-title['bounds']['top'])<30)
        b=f['bounds'];t=title['bounds'];self.start=(b['left']-20,b['top']-10);self.end=(t['left']+t['width']-5,b['top']+110)
        await self.surface.locator('[data-menu="view"] > .menu-trigger').click()
        await self.surface.locator('[data-menu="view"] [data-command="fit-screen"]').click();await self.settled();await self.surface.locator('#viewport').focus()
        await self.page.keyboard.press('z');await m.base.HELPERS.drag_scene(self.surface,(b['left']-30,b['top']-20),(t['left']+t['width']+150,b['top']+300))
        await self.page.keyboard.press('v')
        if not keep_scope:await self.page.keyboard.press('Escape')
        await self.page.keyboard.press('a');await self.settled();await self.surface.evaluate(m.WITNESS)
    async def marquee(self,name):
        self.phase(name+'-start')
        before=await self.full_artwork(name+'-before');state=await self.state(name+'-before')
        first=await m.base.HELPERS.canvas_scene_point(self.surface,*self.start);last=await m.base.HELPERS.canvas_scene_point(self.surface,*self.end)
        await self.surface.evaluate('window.mixedInput=[]');await self.page.mouse.move(first['x'],first['y']);await self.page.mouse.down();await self.page.mouse.move(last['x'],last['y'],steps=8);await self.page.mouse.up();await self.settled()
        current=await self.state(name+'-selected');self.row.setdefault('inputs',{})[name]=await self.surface.evaluate('window.mixedInput')
        self.require(name+' includes whole editable labels',current['direct'].get('selectedTextCount',0)>0,current)
        self.require(name+' includes native path anchors',current['direct']['selectedHandleCount']>0)
        self.require(name+' retains Direct Selection',current['direct']['tool']=='directSelect')
        self.require(name+' changes no artwork or history',m.equivalent(before,await self.full_artwork(name+'-after'))and state['history']==current['history'])
        self.phase(name+'-finished')
        return current
    async def drag_points(self,name,delta,cancel=False,returned=False):
        before=await self.full_artwork(name+'-before');inventory=await self.surface.evaluate(m.g.INVENTORY);state=await self.state(name+'-before')
        handles=state['direct']['selectedHandles'];handle=next(h for h in handles if h['handleType']=='endpoint')
        button=self.surface.locator(f'.path-node-handle[data-object-id="{handle["objectId"]}"][data-command-index="{handle["commandIndex"]}"][data-handle-type="endpoint"]')
        first=await button.bounding_box();self.require(name+' has a visible selected anchor',bool(first))
        origin=(first['x']+first['width']/2,first['y']+first['height']/2)
        start=await m.base.HELPERS.canvas_scene_point(self.surface,handle['x'],handle['y']);end=await m.base.HELPERS.canvas_scene_point(self.surface,handle['x']+delta[0],handle['y']+delta[1])
        await self.surface.evaluate('window.mixedInput=[]');await self.page.keyboard.down('Control');await self.page.mouse.move(*origin);await self.page.mouse.down();await self.page.mouse.move(origin[0]+end['x']-start['x'],origin[1]+end['y']-start['y'],steps=8)
        held=await self.state(name+'-held');moved=await self.surface.evaluate(m.g.INVENTORY);inputs=await self.surface.evaluate('window.mixedInput');down=next(e for e in inputs if e['type']=='pointerdown');last=next(e for e in reversed(inputs)if e['type']=='pointermove');delivered=(last['x']-down['x'],last['y']-down['y'])
        self.row.setdefault('inputs',{})[name]=dict(events=inputs,delivered=delivered)
        self.require(name+' uses trusted original input',down['trusted']and last['trusted'])
        self.require(name+' retains every selected text object',held['direct']['selectedTextIds']==state['direct']['selectedTextIds'])
        selected_text=set(state['direct']['selectedTextIds']);old={o['id']:o for o in inventory['leaves']};errors=[]
        for o in moved['leaves']:
            prior=old[o['id']]
            if o['id']in selected_text:
                residual=max(abs(o['matrix'][i]-prior['matrix'][i]-(delivered[i-4]if i>=4 else 0))for i in range(6))
                if residual>1e-6 or any(o[k]!=prior[k]for k in ['text','parent','path','fill','stroke','strokeWidth']):errors.append(o['id'])
        self.require(name+' moves complete text rigidly without converting it',not errors,errors)
        selected_paths={h['objectId']for h in handles};errors=[]
        for o in moved['leaves']:
            prior=old[o['id']]
            if o['id']not in selected_text|selected_paths:
                if max(abs(a-b)for a,b in zip(o['matrix'],prior['matrix']))>1e-6 or any(o[k]!=prior[k]for k in ['text','parent','path','offset','fill','stroke','strokeWidth']):errors.append(o['id'])
        self.require(name+' leaves every unselected object unchanged',not errors,errors[:8])
        actual={(h['objectId'],h['commandIndex'],h['handleType']):h for h in held['direct']['selectedHandles']}
        errors=[h for h in handles if (h['objectId'],h['commandIndex'],h['handleType'])not in actual or max(abs(actual[(h['objectId'],h['commandIndex'],h['handleType'])][a]-h[a]-delivered[i])for i,a in enumerate(['x','y']))>1e-6]
        self.require(name+' moves every selected anchor with the labels',not errors,errors[:8])
        selected_keys={(h['objectId'],h['commandIndex'],h['handleType'])for h in handles};all_after={(h['objectId'],h['commandIndex'],h['handleType']):h for h in held['direct']['handles']}
        errors=[h for h in state['direct']['handles']if h['handleType']=='endpoint'and(h['objectId'],h['commandIndex'],h['handleType'])not in selected_keys and ((h['objectId'],h['commandIndex'],h['handleType'])not in all_after or max(abs(all_after[(h['objectId'],h['commandIndex'],h['handleType'])][a]-h[a])for a in ['x','y'])>1e-6)]
        self.require(name+' preserves unselected endpoints within the edited paths',not errors,errors[:8])
        if name=='joint-move':await self.capture('joint-move-held','Selected path anchors and readable editable labels have moved together; the selection feedback follows their current positions and neighboring scientific content is intact.')
        if returned:await self.page.mouse.move(*origin,steps=5)
        if cancel:await self.page.keyboard.press('Escape')
        await self.page.mouse.up();await self.page.keyboard.up('Control')
        if not cancel and not returned:await self.history(state['history']['undoDepth']+1)
        await self.settled();after=await self.state(name+'-released');art=await self.full_artwork(name+'-after')
        if cancel or returned:self.require(name+' restores full artwork and history',m.equivalent(before,art)and after['history']==state['history'])
        else:self.require(name+' creates one Undo step',after['history']['undoDepth']==state['history']['undoDepth']+1)
        return before,art,state,after
    async def blank(self):
        point=await m.base.HELPERS.canvas_scene_point(self.surface,*self.start);await self.page.mouse.click(point['x'],point['y']);await self.settled();state=await self.state('blank-cleared')
        self.require('Blank click clears anchors and labels without tool switching',state['direct']['tool']=='directSelect'and not state['direct']['active']and not state['selection']['selectedCount'],state)
        await self.capture('blank-cleared','All anchor and label selection feedback is cleared by a blank click; Direct Selection stays active and the complete artwork remains visible.')
    async def run(self):
        context=None;cold=None;self.started=time.perf_counter();self.phase('starting')
        try:
            self.report['fixture']=dict(path=str(ARGS.fixture),bytes=ARGS.fixture.stat().st_size,sha256=hashlib.sha256(ARGS.fixture.read_bytes()).hexdigest())
            context=await self.open_surface(self.browser);self.phase('import-finished');await self.focus_plot();selected=await self.marquee('warm-marquee')
            await self.capture('mixed-direct-selection','Direct Selection shows anchors on the selected paths and complete editable labels in the same marquee, with readable controls and preserved artwork.')
            await self.drag_points('cancel-move',(8,5),cancel=True);await self.drag_points('raw-return',(8,5),returned=True)
            before,moved,state,released=await self.drag_points('joint-move',(-8,0))
            self.phase('pointer-moves-finished')
            await self.page.keyboard.press('Control+z');await self.history(state['history']['undoDepth']);await self.settled();self.require('Undo restores complete pre-move artwork',m.equivalent(before,await self.full_artwork('undone')))
            await self.page.keyboard.press('Control+y');await self.history(released['history']['undoDepth']);await self.settled();redone=await self.full_artwork('redone');self.require('Redo restores the complete joint move',m.equivalent(moved,redone))
            await self.blank();await self.marquee('warm-reselected');warm=await self.full_artwork('warm-saved');project,saved=await self.save_file('direct-first',warm)
            self.phase('first-save-finished')
            await self.export_file('svg','direct-moved');await self.export_file('pdf','direct-moved')
            await context.close();context=None;browser_type=self.browser.browser_type;await self.browser.close();self.row['warmBrowserClosed']=not self.browser.is_connected()
            cold=await browser_type.launch(**self.report['browserLaunchOptions']);await m.base.record_browser_runtime(cold,self.report,'cold');context=await self.open_surface(cold,project)
            self.require('Fresh browser Open preserves complete saved artwork',m.equivalent(saved,await self.full_artwork('cold-open')))
            self.phase('cold-open-finished')
            await self.focus_plot();await self.marquee('cold-marquee');await self.drag_points('cold-joint-move',(-4,0));await self.capture('cold-continued','The actual saved file has reopened in a fresh browser; its path anchors and complete editable labels remain jointly selectable and movable.')
            continued=await self.full_artwork('cold-saved');await self.save_file('direct-second',continued);await self.blank()
            self.require('No browser page errors',not self.row['pageErrors'],self.row['pageErrors']);self.require('All declared checks pass',all(c['passed']for c in self.row['checks']));self.row['status']='passed'
        except BaseException as error:
            self.row['status']='failed';self.row['error']=str(error)
            if hasattr(self,'page')and not self.page.is_closed():await self.page.screenshot(path=str(self.out/'failure.png'))
            raise
        finally:
            if context:await context.close()
            if cold:await cold.close();self.row['coldBrowserClosed']=not cold.is_connected()
            self.row['contextClosed']=True;self.save()

def main():
    global ARGS
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--expected-app-sha256',required=True);p.add_argument('--viewport',default='1440x1000');p.add_argument('--theme',choices=['light','dark'],default='light');p.add_argument('--fixture',type=Path,default=m.g.SOURCE)
    ARGS=p.parse_args();ARGS.smoke=True;ARGS.url='';ARGS.browser_channel='chromium';label.ARGS=ARGS;m.ARGS=ARGS;m.base.Case=Selection;asyncio.run(m.base.run(ARGS))

if __name__=='__main__':main()
