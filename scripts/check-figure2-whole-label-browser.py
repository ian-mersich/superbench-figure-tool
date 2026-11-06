import argparse,asyncio,base64,hashlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('source_label_open',ROOT/'scripts/check-figure2-object-selection-browser.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Open(m.MixedCase):
    async def select_label(self,object_id):
        inventory=await self.surface.evaluate(m.g.INVENTORY);target=next(o for o in inventory['leaves']if o['id']==object_id);b=target['bounds']
        await self.surface.locator('[data-figure-layout-command="fit-screen"]:visible').click();await self.settled()
        await self.surface.locator('#viewport').focus();await self.page.keyboard.press('z');await m.base.HELPERS.drag_scene(self.surface,(b['left']-50,b['top']-80),(b['left']+b['width']+80,b['top']+b['height']+80))
        await self.surface.locator('#viewport').focus();await self.page.keyboard.press('v');await self.page.keyboard.press('Escape')
        point=await m.base.HELPERS.canvas_scene_point(self.surface,b['left']+b['width']/2,b['top']+b['height']/2);await self.page.mouse.click(point['x'],point['y'])
        await self.settled();selection=await self.surface.evaluate('()=>FigureStudio.app.getSelectionStateForQa()')
        self.check('Public click selects precisely the complete pathway label',selection['selectedIds']==[object_id],selection)
        button=self.surface.locator('[data-context-action="edit-text"]:visible').first;await button.click()
        await self.surface.app_frame.wait_for_function('id=>FigureStudio.app.getObjectByIdForQa(id).isEditing',arg=object_id)
    async def type_label(self,object_id,text):
        await self.select_label(object_id);await self.page.keyboard.press('Control+a');await self.page.keyboard.insert_text(text);await self.page.keyboard.press('Escape');await self.settled()
        result=await self.surface.evaluate('id=>{const o=FigureStudio.app.getObjectByIdForQa(id);return{text:o.text,editing:o.isEditing,source:Boolean(o._sourceLayout()),plane:Boolean(o._pdfCurrentNativePlane()),substitutions:o.getFontSubstitutions?.()||[],membership:o.pdfTextSource.sourceItemMembership};}',object_id)
        self.check('Actual keyboard editing changes the entire label including spaces and Unicode',result['text']==text and not result['editing'],result)
        return result
    async def export_file(self,kind,name):
        await self.surface.locator('[data-figure-layout-command="export-as"]:visible').first.click()
        await self.surface.locator('[data-export-as-format]').select_option(kind);await self.surface.locator('[data-export-as-scope]').select_option('current')
        await self.surface.app_frame.wait_for_function("FigureStudio.app.getExportAsStateForQa().reviewStatus==='ready'&&!document.querySelector('[data-export-as-submit]').disabled")
        path=self.out/(name+'.'+kind)
        async with self.page.expect_download()as download:await self.surface.locator('[data-export-as-submit]').click()
        await(await download.value).save_as(path);self.check('Actual '+kind+' export downloads vector artwork',path.stat().st_size>1000)
        await self.page.keyboard.press('Escape');return path
    async def journey(self,target):
        object_id=target['id'];before=await self.full_artwork('label-before');state=await self.snap('label-before');replacement='Extracellular Matrix Organization A \u03b2'
        await self.type_label(object_id,replacement);after=await self.full_artwork('label-typed');await self.capture('label-typed','The complete pathway label shows the replacement text including spaces and beta; neighboring scientific labels remain intact.')
        await self.page.keyboard.press('Control+z');await self.history(state['history']['undoDepth']);await self.settled();undone=await self.full_artwork('label-undo');self.check('One Undo restores complete imported artwork',m.equivalent(before,undone))
        await self.page.keyboard.press('Control+y');await self.history(state['history']['undoDepth']+1);await self.settled();redone=await self.full_artwork('label-redo');self.check('One Redo restores complete typed artwork',m.equivalent(after,redone))
        project,saved=await self.save_file('label-first',redone)
        await self.export_file('svg','label-typed');await self.export_file('pdf','label-typed')
        old_context=self.page.context;await old_context.close();browser_type=self.browser.browser_type;await self.browser.close();self.row['warmBrowserClosed']=not self.browser.is_connected()
        cold_browser=await browser_type.launch(**self.report['browserLaunchOptions']);await m.base.record_browser_runtime(cold_browser,self.report,'cold')
        cold_context=await cold_browser.new_context(viewport=dict(width=self.width,height=self.height),color_scheme=self.theme);await cold_context.add_init_script('try{delete window.showSaveFilePicker;delete window.showOpenFilePicker;}catch(_){}')
        try:
            self.page=await cold_context.new_page();self.page.set_default_timeout(30000);self.page.on('pageerror',lambda e:self.row['pageErrors'].append(str(e)));self.page.on('dialog',lambda d:d.accept(d.default_value or 'label-continued.fsfigure'))
            await self.page.goto(self.entry_url(),wait_until='domcontentloaded');self.surface=await m.base.HELPERS.resolve_figure_surface(self.page);await m.base.HELPERS.dismiss_first_run_surface(self.surface)
            async with self.page.expect_file_chooser()as chooser:await self.surface.locator('body').press('Control+o')
            await(await chooser.value).set_files(project);await self.surface.app_frame.wait_for_function("document.querySelector('#documentFileOperationStatus')?.dataset.state==='success'&&!FigureStudio.app.getBrowserSessionState().busy")
            cold=await self.full_artwork('label-cold');self.check('Fresh Chromium preserves the complete saved artwork',m.equivalent(saved,cold))
            await self.type_label(object_id,replacement+' A');continued=await self.full_artwork('label-continued');await self.save_file('label-second',continued)
            await self.capture('label-continued','The saved full pathway label remains editable after reopening in a fresh browser, including the continued text change.')
        finally:await cold_context.close();await cold_browser.close();self.row['coldBrowserClosed']=not cold_browser.is_connected()

    async def run(self):
        context=await self.browser.new_context(viewport=dict(width=self.width,height=self.height),color_scheme=self.theme)
        await context.add_init_script('try{delete window.showSaveFilePicker;delete window.showOpenFilePicker;}catch(_){}');self.page=await context.new_page();self.page.on('dialog',lambda d:d.accept(d.default_value or 'label.fsfigure'));self.page.set_default_timeout(30000);self.page.on('pageerror',lambda e:self.row['pageErrors'].append(str(e)))
        try:
            await self.page.goto(self.entry_url(),wait_until='domcontentloaded');self.surface=await m.base.HELPERS.resolve_figure_surface(self.page);await m.base.HELPERS.dismiss_first_run_surface(self.surface)
            await self.surface.locator('[data-menu="file"] > .menu-trigger').click();await self.surface.locator('[data-menu="file"] [data-command="new-project"]').click();await self.surface.locator('#newDocumentBackdrop').wait_for(state='visible')
            async with self.page.expect_file_chooser()as chooser:await self.surface.locator('#openArtworkDocumentBtn:visible').click()
            await(await chooser.value).set_files(m.g.SOURCE);await self.surface.locator('#importPlacementReview:not([hidden])').wait_for()
            await self.surface.locator('#pdfEntryModeSelect:visible').select_option('editable');await self.surface.locator('#pdfPageModeSelect:visible').select_option('custom');await self.surface.locator('#pdfPageRangeInput:visible').fill('1');await self.surface.locator('#importPlacementCenterBtn:visible').click();await self.surface.locator('#importPlacementReview').wait_for(state='hidden')
            await self.surface.app_frame.wait_for_function('FigureStudio.app.getBrowserSessionState().ready&&!FigureStudio.app.getBrowserSessionState().busy')
            await self.surface.locator('#viewport').focus();await self.page.keyboard.press('Escape');await self.page.keyboard.press('z');await m.base.HELPERS.drag_scene(self.surface,(40,40),(430,430));await self.page.keyboard.press('v');await self.page.keyboard.press('Escape');await self.surface.wait_for_visual_stability()
            inventory=await self.surface.evaluate(m.g.INVENTORY);self.row['sourceInventory']=inventory
            result=await self.surface.evaluate('''async()=>{const a=FigureStudio.app,root=a.getObjectByIdForQa(a.getCanvasObjectInventoryForQa().objects[0].id),c=root.canvas,lower=c.lowerCanvasEl;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));const bytes=c.contextContainer.getImageData(0,0,lower.width,lower.height).data,digest=await crypto.subtle.digest('SHA-256',bytes);const texts=[],glyphs=[];function visit(o){if(o.pdfTextSource){texts.push({id:o.figureId,text:o.text,sourceItem:o.pdfTextSource.sourceItemMembership||null,plane:Boolean(o._pdfCurrentNativePlane?.()),source:Boolean(o._sourceLayout?.())});for(const g of o.pdfTextSource.glyphs)glyphs.push([g.unicode,g.fontChar]);}for(const child of o.getObjects?.()||[])visit(child);}visit(root);return{width:lower.width,height:lower.height,rgbaSha256:Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join(''),png:lower.toDataURL('image/png'),textUnits:texts,glyphs,import:root.importMeta.pdfEditableImport};}''')
            (self.out/'native-full-page.png').write_bytes(base64.b64decode(result.pop('png').split(',')[1]));(self.out/'source-text.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');await self.full_artwork('initial-complete-fabric')
            self.check('Original Figure2 source remains exact',hashlib.sha256(m.g.SOURCE.read_bytes()).hexdigest()=='5aea6513d86170d1ef11b0643dbdb104416f466444c8d2dd07791ea4df09a208')
            target=[t for t in result['textUnits']if t['text']=='Extracellular Matrix Organization'];self.row['wholeLabelTarget']=target
            if ARGS.expect_joined:self.check('Whole pathway label is one native editable text with admitted source planes',len(target)==1 and target[0]['source']and target[0]['plane'])
            self.check('No browser errors',not self.row['pageErrors'],self.row['pageErrors']);await self.capture('source-open','The original Figure2 page is visible at source-preserving zoom after fresh import; this is an import diagnostic, not interaction acceptance.')
            if not all(c['passed']for c in self.row['checks']):raise AssertionError('Fresh whole-label import failed')
            await self.journey(target[0])
            if not all(c['passed']for c in self.row['checks']):raise AssertionError('Whole-label journey failed')
            self.row['status']='passed'
        except BaseException as e:
            self.row['status']='failed';self.row['error']=str(e)
            if not self.page.is_closed():await self.page.screenshot(path=str(self.out/'failure.png'))
            raise
        finally:await context.close();self.row['contextClosed']=True;self.save()
def main():
    global ARGS
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--expected-app-sha256',required=True)
    p.add_argument('--viewport',default='1440x1000');p.add_argument('--theme',choices=['light','dark'],default='light');ARGS=p.parse_args();ARGS.expect_joined=True;ARGS.smoke=True;ARGS.url='';ARGS.browser_channel='chromium';m.ARGS=ARGS;m.base.Case=Open;asyncio.run(m.base.run(ARGS))
if __name__=='__main__':main()
